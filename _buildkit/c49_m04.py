# -*- coding: utf-8 -*-
"""C49 模块 04 · Encoder-Decoder：T5 / BART / cross-attention / beam search。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–03、注意力机制、交叉熵；模块 00 的三种掩码"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_encoder_decoder.ipynb'),
    ("核心论文", "Vaswani et al. 2017（原始 Transformer）★、Raffel et al. 2020（T5）★、Lewis et al. 2020（BART）★、Ranzato et al. 2016（exposure bias）"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("why", "为什么需要第三种形态", "".join([
        P("前三个模块的世界里，输出要么是一个标签、要么是原文的一个片段。但有一大类任务的输出是<strong>一段新的文本</strong>：翻译、摘要、改写、结构化转换、语法纠错。这类任务的输入和输出是<em>两个不同长度、不同语言/形式的序列</em>——这正是 <span class=\"term\">sequence-to-sequence</span>（seq2seq）问题。"),
        P("这里有个容易被忽略的历史事实：<strong>Transformer 最初就是为 seq2seq 设计的</strong>。Vaswani et al. 2017 的标题是《Attention Is All You Need》，解决的问题是机器翻译，架构是 encoder-decoder。BERT（只取 encoder）和 GPT（只取 decoder）都是<em>后来的裁剪</em>。所以本模块讲的不是「另一种变体」，而是<strong>回到原点</strong>。"),
        TABLE(["方案", "怎么做 seq2seq", "问题"], [
            ["encoder-only（BERT）", "❌ 做不了", "无法自回归生成（模块 01 的三层原因）"],
            ["decoder-only（GPT）", "把输入输出拼成一个序列 <code>[输入][SEP][输出]</code>，因果掩码", "<strong>输入部分只能被单向编码</strong>——读到第 3 个词时看不到第 10 个词"],
            ["<strong>encoder-decoder</strong>", "输入过双向编码器，输出自回归解码，中间用 cross-attention 连接", "参数多一套，训练更复杂"],
            ["prefix-LM（GLM/UniLM）", "一个模型，前缀双向、后缀因果", "折中方案；表达力接近 enc-dec，参数只有一套"],
        ]),
        DUAL(
            "decoder-only 做 seq2seq 的那个缺陷值得说清楚：<strong>输入被单向编码</strong>。翻译一个长句时，模型读到源句第 3 个词时看不到第 30 个词，而后者可能决定前者的译法（比如中文的「他/她」需要看后文才知道性别）。encoder-decoder 让输入享受完整的双向注意力，理论上更适合「输入是给定的、需要被充分理解」的任务。",
            "但实践给出了一个更微妙的答案。decoder-only 虽然对输入是单向的，但它可以通过<strong>足够的深度和规模</strong>弥补——高层的表示会把后文信息「回传」到前面位置的后续处理中（虽然不是直接注意）。加上 decoder-only 的<em>训练与推理形式完全统一</em>（都是自回归）、<em>预训练数据无限</em>（任何文本都能用）、<em>KV 缓存实现简单</em>，这些工程优势在规模上来后压倒了架构上的理论劣势。<strong>这就是为什么 2023 年后主流 LLM 几乎全是 decoder-only</strong>——不是 encoder-decoder 不好，是它的优势不够大而代价明确。",
        ),
        CALLOUT("intuition", "但 encoder-decoder 并没有消失，它在两类场景里仍然是更优解：<strong>①输入远长于输出的任务</strong>（长文档摘要——编码器只需跑一次，解码器在短输出上自回归，而 decoder-only 每生成一个 token 都要对全部输入做注意力）；<strong>②需要极致效率的专用任务</strong>（翻译、语法纠错——一个 220M 的 T5-base 就能做得很好，不需要 7B）。<em>模块 05 会把这两笔账算清楚。</em>"),
    ])),
    ("arch", "架构：三种注意力的分工", "".join([
        ASCII("""输入 x = [x1 x2 x3 x4]                    输出 y = [y1 y2 y3]

┌─────── ENCODER (N 层) ────────┐      ┌────── DECODER (N 层) ───────┐
│                               │      │                             │
│  ① self-attention             │      │  ② masked self-attention    │
│     双向：每个 x 看到所有 x    │      │     因果：y_t 只看 y_<t      │
│           ↓                   │      │           ↓                 │
│  FFN                          │      │  ③ cross-attention          │
│           ↓                   │      │     Q 来自解码器            │
│  (重复 N 层)                  │─────▶│     K,V 来自**编码器输出**  │
│           ↓                   │ 只算  │     → y_t 能看到全部 x      │
│  编码器输出 memory (n,d)      │ 一次! │           ↓                 │
└───────────────────────────────┘      │  FFN                        │
                                       │  (重复 N 层)                │
                                       │           ↓                 │
                                       │  输出投影 → P(y_t | y_<t, x)│
                                       └─────────────────────────────┘

关键: **编码器只跑一次**，其输出被解码器的每一步、每一层复用。
      这就是「输入长、输出短」场景下 enc-dec 的效率优势来源。""")
        ,
        H3("cross-attention：唯一的新组件"),
        P("整个 encoder-decoder 里，唯一你在前面模块没见过的东西就是 <span class=\"term\">cross-attention</span>。而它的公式和 self-attention 一模一样，只是 Q、K、V 的来源不同："),
        MATH("\\text{CrossAttn}(H_{dec}, M_{enc}) = \\text{softmax}\\!\\left(\\frac{(H_{dec}W_Q)(M_{enc}W_K)^T}{\\sqrt{d}}\\right)(M_{enc}W_V)"),
        TABLE(["", "Q 来自", "K, V 来自", "掩码", "形状"], [
            ["编码器 self-attn", "编码器隐状态", "编码器隐状态", "双向（全 1）", "(n, n)"],
            ["解码器 self-attn", "解码器隐状态", "解码器隐状态", "<strong>因果</strong>（下三角）", "(m, m)"],
            ["<strong>cross-attn</strong>", "<strong>解码器</strong>隐状态", "<strong>编码器</strong>输出", "全 1（输出可看全部输入）", "<strong>(m, n)</strong>"],
        ]),
        DUAL(
            "cross-attention 的注意力矩阵是 <code>(m, n)</code>——<strong>输出位置 × 输入位置</strong>。这个矩阵有一个很好的可解释性：它近似于<em>词对齐</em>。翻译时看这个矩阵，你能看到「生成这个目标词时，模型主要在看源句的哪几个词」。这在神经机器翻译时代是标准的可视化手段，也是「注意力即对齐」这个直觉的来源。",
            "工程上有一个重要性质：<strong>cross-attention 的 K、V 只依赖编码器输出，在整个解码过程中不变</strong>，所以可以<em>算一次、缓存起来</em>。而解码器 self-attention 的 KV 缓存要随生成逐步增长。这两种缓存的生命周期不同，是 enc-dec 推理实现里的一个关键细节——也是它相对 decoder-only 的效率优势所在：decoder-only 每步都要对「输入+已生成」的全部 token 做注意力，而 enc-dec 的输入部分是固定的预计算结果。",
        ),
        CALLOUT("warn", "参数量的账要算清楚：<strong>encoder-decoder 的参数量约是同深同宽 encoder-only 的 2.3 倍</strong>——编码器 N 层 + 解码器 N 层，且解码器每层多一个 cross-attention（4 个 <code>d×d</code> 矩阵）。所以 T5-base（12+12 层）是 220M，而 BERT-base（12 层）是 110M。<em>比较不同形态时必须在同等参数量或同等 FLOPs 下比，否则结论没有意义</em>——这是文献里常见的不公平比较来源。"),
    ])),
    ("t5", "T5：把一切都变成文本到文本", "".join([
        P("T5（Text-To-Text Transfer Transformer）的核心主张极其简单，但影响深远：<strong>所有 NLP 任务都可以表述成「输入一段文本、输出一段文本」</strong>。"),
        CODE("""# 同一个模型、同一套权重、同一个损失函数，靠任务前缀区分：

"translate English to German: That is good."      →  "Das ist gut."
"cola sentence: The course is jumping well."      →  "not_acceptable"
"stsb sentence1: ... sentence2: ..."              →  "3.8"          # 回归也变成生成数字!
"summarize: state authorities dispatched..."      →  "six people hospitalized after..."
"question: What is 42? context: ..."              →  "the answer to everything\""""),
        DUAL(
            "这个统一带来三个好处：<strong>①一个模型多任务</strong>（不用为每个任务建头）；<strong>②任务间迁移</strong>（多任务预训练让低资源任务受益）；<strong>③接口极简</strong>（输入输出都是字符串，工程上极好集成）。这套「万物皆文本」的思路，后来被指令微调（instruction tuning）和 LLM 的 prompt 范式完全继承——<em>今天你给 GPT 写 prompt 的方式，思想上就是 T5 的任务前缀</em>。",
            "代价也要看清：<strong>把分类变成生成，你就失去了输出空间的约束</strong>。分类头的 softmax 保证输出必是 <code>C</code> 个类之一；生成式则可能吐出 <code>\"acceptabl\"</code>（拼错）、<code>\"maybe\"</code>（不在类集里）、或者一段解释。实践中需要<em>受约束解码</em>（把生成限制在合法标签集上）或后处理匹配。回归任务尤其别扭——T5 把 STS-B 的连续分数量化成 <code>\"1.0\" \"1.2\" ... \"5.0\"</code> 这样的字符串，本质上是把回归退化成了 21 类分类。<strong>这是「统一接口」的真实成本</strong>。",
        ),
        H3("Span corruption：T5 的预训练目标"),
        P("T5 的预训练目标不是 BERT 式的逐 token 掩码，而是 <span class=\"term\">span corruption</span>——<strong>连续片段整体挖掉，用一个哨兵 token 代替，让解码器把它们依次生成出来</strong>。"),
        ASCII("""原文:   Thank you for inviting me to your party last week .

① 随机挑若干**连续片段**（平均长度 3），总共覆盖约 15% 的 token
                   ┌───┐              ┌──────────┐
   Thank you  for  inviting  me  to  your  party  last  week .
                   └───┘              └──────────┘

② 编码器输入：每个片段整体换成一个**唯一的哨兵 token**
   "Thank you <X> me to your <Y> week ."

③ 解码器目标：依次生成 哨兵 + 对应的原片段，最后一个哨兵收尾
   "<X> for inviting <Y> party last <Z>"

对比 BERT 的 MLM:
   BERT: "Thank you [MASK] me to your [MASK] [MASK] ."  → 逐位置预测原词
   T5:   把连续片段整体挖掉 → 目标序列**短得多**（只含被挖内容，不含未挖部分）""")
        ,
        TABLE(["设计", "T5 的选择", "为什么"], [
            ["<strong>片段而非单 token</strong>", "平均长度 3 的连续片段", "更难、更接近下游生成任务；也更贴近「填一段话」而非「填一个词」"],
            ["<strong>哨兵 token</strong>", "<code>&lt;extra_id_0&gt;</code>…<code>&lt;extra_id_99&gt;</code>，100 个专用 token", "让模型知道「这里挖了一段」以及「挖的是第几段」"],
            ["<strong>目标只含被挖内容</strong>", "不重复输出未被挖的部分", "<strong>目标序列短 → 解码计算量小得多</strong>，训练效率显著提升"],
            ["<strong>掩码比例 15%、片段长 3</strong>", "论文做了系统消融", "更高比例或更长片段都会降低效果"],
        ]),
        CALLOUT("intuition", "「目标序列只含被挖内容」这个设计常被忽略，但它是 T5 效率的关键。如果让解码器重建整句（BART 的做法之一），目标长度 = 输入长度；只输出被挖片段，目标长度 ≈ 输入的 15%+哨兵。<strong>解码器的计算量与目标长度成正比，所以这一个设计就省了约 5 倍的解码计算</strong>。notebook 会把这笔账算出来。"),
    ])),
    ("bart", "BART：去噪自编码器的多种噪声", "".join([
        P("BART 与 T5 同期、思路相近但不同：<strong>用多种噪声破坏原文，让模型重建完整原文</strong>。它是一个标准的去噪自编码器（denoising autoencoder）。"),
        TABLE(["噪声类型", "做法", "教会模型什么"], [
            ["<strong>token masking</strong>", "随机 token 换成 <code>[MASK]</code>（同 BERT）", "局部词汇恢复"],
            ["<strong>token deletion</strong>", "随机删除 token（<strong>不留占位符</strong>）", "模型必须自己判断<em>哪里少了东西</em>——比 masking 难"],
            ["<strong>text infilling</strong>", "连续片段换成<strong>单个</strong> <code>[MASK]</code>（片段长服从 λ=3 的泊松，可以为 0）", "必须预测「缺了多少个词」——BART 论文认为这是最有效的单项"],
            ["<strong>sentence permutation</strong>", "打乱句子顺序", "篇章级连贯性"],
            ["<strong>document rotation</strong>", "把文档旋转到从某个随机 token 开始", "识别文档真正的开头"],
        ]),
        DUAL(
            "BART 与 T5 的核心区别：<strong>BART 重建<em>整个</em>原文，T5 只生成被挖的片段</strong>。BART 的目标更「完整」（解码器要输出整篇），因此天然更适合摘要这类需要生成完整流畅文本的任务；T5 的目标更「高效」（解码器只输出 15%），训练更快。<em>两者在下游微调后的效果相近，选哪个更多取决于生态与可用 checkpoint。</em>",
            "BART 还有一个常被引用的实用发现：<strong>text infilling（片段换单个 mask，长度未知）是最有效的单项噪声</strong>。原因在于它同时训练了三种能力——恢复内容、判断缺失长度、以及在长度不确定时保持流畅。相比之下 token masking 泄漏了「缺了几个词」这个信息（有几个 <code>[MASK]</code> 就缺几个），任务更简单。<em>这与 T5 span corruption 的哨兵设计形成对照：T5 的哨兵也不指示长度，所以两者在这一点上是一致的。</em>",
        ),
        CALLOUT("warn", "BART 的一个实现细节容易踩坑：<strong>解码器的起始 token</strong>。BART 用 <code>&lt;/s&gt;</code>（eos）作为 decoder 的第一个输入 token，而不是常见的 <code>&lt;s&gt;</code>（bos），这是历史遗留。自己实现 teacher forcing 时如果 shift 错了一位，训练能跑但效果会莫名很差——<em>因为模型学的是「预测当前 token」而不是「预测下一个 token」</em>。这类 off-by-one 是 seq2seq 实现里最常见的 bug，notebook 会用一个 assert 把它钉死。"),
    ])),
    ("training", "训练：teacher forcing 与 exposure bias", "".join([
        H3("teacher forcing：并行训练的关键"),
        P("自回归生成在推理时是串行的（生成 <code>y_t</code> 需要 <code>y_{t-1}</code>），但训练时不能这么做——太慢，而且早期模型生成的东西全是垃圾，学不到东西。<strong>teacher forcing</strong> 的做法是：训练时把<em>真实的</em>目标序列右移一位喂给解码器，让所有位置的预测<strong>并行</strong>计算。"),
        ASCII("""目标序列 y = [Das, ist, gut, </s>]

训练时（teacher forcing，所有位置并行）:
  decoder 输入:  [<s>,  Das,  ist,  gut ]     ← 真实 y 右移一位
  decoder 目标:  [Das,  ist,  gut, </s>]      ← 原始 y
  因果掩码保证位置 t 看不到 t 及之后的目标 → 一次前向算出全部 4 个位置的损失

推理时（自回归，串行）:
  step 1: 输入 [<s>]                → 生成 "Das"
  step 2: 输入 [<s>, Das]           → 生成 "ist"      ← 用的是**自己生成的** Das
  step 3: 输入 [<s>, Das, ist]      → 生成 "gut"
  step 4: 输入 [<s>, Das, ist, gut] → 生成 "</s>"  停止

⚠️ 训练时喂真实前缀，推理时喂自己生成的前缀 —— **这个不一致就是 exposure bias**。""")
        ,
        H3("exposure bias：训练-推理的分布偏移"),
        DUAL(
            "问题在于：训练时模型永远看到<strong>完美的</strong>历史前缀，从未见过自己犯错后的状态。推理时一旦生成了一个不太对的词，后续的输入就落在了训练分布之外，模型不知道怎么办，<strong>错误会累积放大</strong>。这就是 <span class=\"term\">exposure bias</span>（暴露偏差，Ranzato et al. 2016）。典型症状：生成前几个词很好，越往后越离谱；或者陷入重复循环（「非常非常非常……」）。",
            "缓解方案有几类，但都不完美：<strong>①scheduled sampling</strong>（训练时以一定概率用模型自己的预测替换真实前缀，概率随训练递增）——简单有效，但破坏了并行性且理论上有偏；<strong>②序列级训练</strong>（用 REINFORCE 或 minimum risk training 直接优化 BLEU 等序列指标）——理论上更对，但方差大、训练不稳；<strong>③在解码时缓解</strong>（beam search 通过保留多条候选降低单步错误的影响；重复惩罚直接堵住退化模式）。<em>实践中第三类用得最多，因为它零训练成本。</em>",
        ),
        CALLOUT("intuition", "exposure bias 这个概念在 LLM 时代依然重要，只是换了名字。RLHF 中的「on-policy 采样」正是在解决同一个问题——<strong>让模型在自己生成的分布上被训练，而不是只在人类数据的分布上</strong>。DPO 与 PPO 的一个核心区别也在这里（PPO 是 on-policy，DPO 用的是离线偏好数据）。<em>C02/C22 讲这些方法时，你可以回想这里：它们都在解决「训练分布 ≠ 推理分布」这个同一个古老问题。</em>"),
    ])),
    ("decoding", "解码：beam search 与它的陷阱", "".join([
        P("训练完了，怎么生成？贪心（每步取 argmax）是最简单的，但它是<strong>短视</strong>的——当前最优的词可能导致后续全盘皆输。"),
        ASCII("""贪心的失败模式（概率是编造的示意）:

  step 1:  P(the)=0.4  P(a)=0.35  P(dog)=0.25   → 贪心选 "the"
  step 2:  已选 "the" 后，最好的续接只有 P=0.1  → 总分 0.4 × 0.1 = 0.04
           但若第一步选了 "a"，续接可以有 P=0.8 → 总分 0.35 × 0.8 = 0.28  ← 更好!

  贪心看不到这一步，因为它在 step 1 就把 "a" 扔了。

beam search (beam=3): 每步保留 3 条最优部分序列，不急着扔
  step 1: [the(0.4), a(0.35), dog(0.25)]
  step 2: 对每条各扩展全词表 → 3×V 个候选 → 按累积 log 概率取前 3
  ...     直到所有 beam 都生成 </s> 或达到最大长度""")
        ,
        MATH("\\text{score}(y_{1:t}) = \\sum_{i=1}^{t} \\log P(y_i \\mid y_{<i}, x)"),
        H3("长度惩罚：一个必须加的修正"),
        P("上面这个分数有个明显问题：<strong>每多生成一个词，log 概率就多加一个负数，所以短序列天然占优</strong>。不修正的话 beam search 会系统性地偏好短输出——翻译会漏译、摘要会过短。标准修正是<span class=\"term\">长度归一化</span>："),
        MATH("\\text{score}_{norm} = \\frac{1}{\\text{lp}(t)}\\sum_{i=1}^{t} \\log P(y_i \\mid y_{<i}, x), \\qquad \\text{lp}(t) = \\left(\\frac{5+t}{6}\\right)^{\\alpha}"),
        P("<code>α=0</code> 是不归一化，<code>α=1</code> 是简单平均，GNMT 的经典取值是 <code>α∈[0.6, 1.0]</code>。这个看似 hacky 的公式（那个 <code>(5+t)/6</code>）来自 GNMT 论文的经验调参，至今仍在广泛使用。"),
        TABLE(["解码策略", "适合", "问题"], [
            ["<strong>greedy</strong>", "确定性任务、追求速度", "短视；容易重复"],
            ["<strong>beam search</strong>", "<strong>翻译、摘要</strong>等有「标准答案」的任务", "beam 太大反而变差（见下）；输出偏「安全」缺乏多样性"],
            ["<strong>sampling (top-k / top-p)</strong>", "开放生成、对话、创意写作", "不适合翻译（会引入随机错误）"],
            ["<strong>constrained decoding</strong>", "输出必须落在合法集合（如分类标签、JSON）", "实现复杂"],
        ]),
        CALLOUT("danger", "<p><strong>beam search 的诅咒</strong>：直觉上 beam 越大搜索越充分、结果越好，但实证反复发现——<em>beam 超过 5~10 之后，BLEU 反而下降</em>（Koehn &amp; Knowles 2017 等）。原因很微妙：更大的 beam 更接近「真正的最大似然序列」，而<strong>模型的最大似然序列往往是退化的</strong>（空串、极短句、高频套话）。也就是说，<em>小 beam 的搜索不充分性，意外地起到了正则化作用</em>。这个现象揭示了一件重要的事：<strong>我们的训练目标（最大似然）与我们真正想要的（好的翻译）之间存在系统性错位</strong>。这也是后来 RLHF 等「直接优化人类偏好」方法的动机之一。</p>", "beam 越大越好？不对"),
    ])),
    ("ledger", "算一笔账：enc-dec 与 decoder-only 的推理成本", "".join([
        P("这是本模块最有实操价值的一节，也是模块 05 选型的基础。任务：输入 <code>n</code> token，输出 <code>m</code> token。"),
        TABLE(["", "encoder-decoder", "decoder-only"], [
            ["编码阶段", "编码器对 <code>n</code> 个 token 跑一次（可并行）", "prefill：对 <code>n</code> 个 token 跑一次（可并行）"],
            ["解码每步的注意力范围", "self-attn 看已生成的 <code>t</code> 个；cross-attn 看固定的 <code>n</code> 个（K/V 预计算）", "看 <code>n + t</code> 个（输入与已生成混在一起）"],
            ["解码 <code>m</code> 步的注意力总量", "<code>Σ_t (t + n)</code> ≈ <code>m²/2 + mn</code>", "<code>Σ_t (n + t)</code> ≈ <code>mn + m²/2</code>"],
            ["<strong>KV 缓存大小</strong>", "解码器 self KV（随 <code>m</code> 增长）+ cross KV（固定 <code>n</code>，<strong>只算一次</strong>）", "全部 <code>n+m</code> 的 KV"],
            ["参数量（同深同宽）", "≈ 2.3×", "1×"],
        ]),
        DUAL(
            "注意力总量上两者其实接近——真正的差异在<strong>参数量</strong>与<strong>每步的矩阵乘法规模</strong>。enc-dec 用 2.3 倍参数换取输入的双向编码；decoder-only 用单向输入换取参数效率与实现简洁。<em>在小规模（&lt;1B）且任务明确时，enc-dec 的双向优势更容易体现；规模上来后，decoder-only 的其他优势占了上风。</em>",
            "但有一个场景 enc-dec 的优势是<strong>结构性</strong>的：<strong><code>n ≫ m</code>（输入远长于输出）</strong>。比如「把一篇 8000 token 的文档摘要成 100 token」。enc-dec：编码器跑一次 8000（<code>O(n²)</code> 但只一次），解码 100 步、每步 cross-attn 到预计算的 8000 个 KV。decoder-only：prefill 8000，然后 100 步、每步对 8000+t 做注意力——<em>看起来差不多，但 decoder-only 的这 8000 个 KV 占用的显存是「全部层 × 全部头」的，而 enc-dec 的 cross-attn KV 只需存编码器最后一层的输出投影</em>。在长输入下这个显存差异很可观。",
        ),
        P("最后一笔账：<strong>T5 的「目标只含被挖片段」到底省了多少训练算力</strong>。设输入长 <code>L</code>、掩码率 15%、片段长 3。BART 式重建整句的目标长度是 <code>L</code>；T5 式只输出被挖内容，目标长度约 <code>0.15L + L/3·0.15</code>（内容 + 哨兵）≈ <code>0.2L</code>。解码器计算量与目标长度成正比（自注意力还是平方关系），所以<strong>解码侧省约 5 倍，端到端约省 40–50% 的训练算力</strong>。notebook 会把这个算清楚。"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>encoder-decoder 不是「更复杂的 BERT」也不是「更笨的 GPT」，它是把「理解输入」和「生成输出」这两件事<em>显式分工</em>的架构</strong>。这个分工带来的好处（输入双向、编码只算一次、cross-attn 可预计算）在「输入固定且长、输出短」的任务上是实打实的；带来的代价（参数翻倍、两套栈、训练复杂）在追求通用性的场景下不划算。<em>知道分界线在哪，比知道谁「更先进」有用得多。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>架构形态的公平比较</strong>：Tay et al. 2022 <em>UL2</em> 等工作试图在同等算力下系统比较 enc-dec / dec-only / prefix-LM，并提出混合去噪目标（mixture-of-denoisers）统一它们。但「在什么规模、什么任务上哪种更优」仍缺乏干净的缩放律。",
            "<strong>exposure bias 的真实影响有多大</strong>：这个概念被广泛引用，但也有工作（如 He et al. 2021）论证在强模型上它的影响被高估了——大模型的自生成前缀已经足够接近训练分布。<em>它到底是个真问题还是一个流传的直觉，取决于规模，尚无定论。</em>",
            "<strong>似然与质量的错位</strong>：beam search 的诅咒揭示了「最大似然序列往往是退化的」。这个现象的理论刻画（为什么 MLE 训练的模型其众数是退化的）以及如何设计不错位的训练目标，是生成模型的根本问题之一。对比解码（contrastive decoding）、typical sampling 等都是缓解尝试。",
            "<strong>非自回归生成</strong>：一次性并行生成全部输出（NAT），速度快一个数量级，但质量差（因为输出 token 之间的依赖被忽略）。迭代式精化（如 CMLM、掩码扩散）是折中。<em>encoder-decoder 天然适合 NAT（编码器已经给了完整输入表示），这条线在翻译上有实用价值。</em>",
            "<strong>长输入的编码器</strong>：enc-dec 在长文档任务上的优势要求编码器能吃长输入，但注意力是 O(n²)。稀疏注意力（LED、BigBird）、层次编码、检索增强各有取舍，最优方案仍未收敛（C25 有系统讨论）。",
        ]),
        CALLOUT("paper", "必读：Vaswani et al. 2017 <em>Attention Is All You Need</em>（原始 enc-dec 与 cross-attention 的定义，重新读一遍你会发现很多细节被后来的教程简化掉了）、Raffel et al. 2020 <em>T5</em>（第 3 节的系统消融是本领域最完整的架构/目标对比实验之一）、Lewis et al. 2020 <em>BART</em>（五种噪声的消融）、Ranzato et al. 2016 <em>Sequence Level Training</em>（exposure bias 的提出）、Koehn &amp; Knowles 2017 <em>Six Challenges for NMT</em>（beam search 诅咒的实证）、Wu et al. 2016 <em>GNMT</em>（长度惩罚公式的出处）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · Encoder-Decoder（cross-attention / span corruption / teacher forcing / beam search，全部从零）

目标：把 **三种注意力的分工 → T5 span corruption → BART 五种噪声 → teacher forcing 的 off-by-one →
exposure bias → beam search + 长度惩罚** 从零实现，每个组件都**对拍**朴素参考。

路线：cross-attention 与形状 → 编码器只算一次的验证 → span corruption 构造与**可逆性对拍** →
teacher forcing shift 的正确性 assert → exposure bias 数值演示 → beam search 对拍穷举 →
长度惩罚与 beam 诅咒 → ✏️ 练习 → 📖 答案 → 🧪 训练算力胶囊。

> 心智模型：**enc-dec 把「理解输入」与「生成输出」显式分工**。
> cross-attention 是唯一的新组件，而它的公式与 self-attention 完全相同，只是 Q 与 K/V 来源不同。"""),
    md("""## 1 · 三种注意力：唯一的新东西是 cross-attention"""),
    code("""import numpy as np, math, itertools, heapq, collections
rng = np.random.default_rng(0)
np.set_printoptions(precision=3, suppress=True)

D = 16

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x); return e / e.sum(axis=axis, keepdims=True)

def attend(Q_src, KV_src, Wq, Wk, Wv, mask=None):
    '''统一的注意力：Q 来自 Q_src，K/V 来自 KV_src。三种注意力只是这两个参数不同。'''
    Q, K, V = Q_src @ Wq, KV_src @ Wk, KV_src @ Wv
    s = Q @ K.T / math.sqrt(Q.shape[-1])
    if mask is not None:
        s = np.where(mask, s, -1e9)
    A = softmax(s)
    return A @ V, A

n_src, n_tgt = 6, 4
Xenc = rng.normal(size=(n_src, D))
Hdec = rng.normal(size=(n_tgt, D))
Wq, Wk, Wv = (rng.normal(size=(D, D)) * 0.2 for _ in range(3))

_, A_enc_self  = attend(Xenc, Xenc, Wq, Wk, Wv, np.ones((n_src, n_src), dtype=bool))
_, A_dec_self  = attend(Hdec, Hdec, Wq, Wk, Wv, np.tril(np.ones((n_tgt, n_tgt), dtype=bool)))
_, A_cross     = attend(Hdec, Xenc, Wq, Wk, Wv, np.ones((n_tgt, n_src), dtype=bool))

print(f'编码器 self-attn: {A_enc_self.shape}  (输入×输入, 双向)')
print(f'解码器 self-attn: {A_dec_self.shape}  (输出×输出, 因果)')
print(f'cross-attn      : {A_cross.shape}  ← **输出×输入**，形状就不同')

assert A_enc_self.shape == (n_src, n_src)
assert A_dec_self.shape == (n_tgt, n_tgt)
assert A_cross.shape == (n_tgt, n_src), 'cross-attention 的矩阵是 (m,n)，不是方阵'
assert np.allclose(A_dec_self.sum(1), 1) and np.allclose(A_cross.sum(1), 1), '每行都是概率分布'
assert np.allclose(np.triu(A_dec_self, 1), 0), '解码器 self-attn 必须严格因果'
print('\\n✅ 三种注意力共用同一个公式，只是 (Q来源, KV来源, 掩码) 三元组不同')
print('   cross-attn 矩阵 (m,n) 近似**词对齐**：生成第 t 个输出时在看输入的哪几个位置')"""),
    md("""### 编码器只算一次：cross-attn 的 K/V 可以缓存

**cross-attention 的 K、V 只依赖编码器输出，整个解码过程中不变。**
这是 enc-dec 在「输入长、输出短」场景下的效率来源。"""),
    code("""class CrossAttnCache:
    '''把 K/V 算一次存下来，之后每个解码步直接用。'''
    def __init__(self, memory, Wk, Wv):
        self.K = memory @ Wk        # 只算一次
        self.V = memory @ Wv
        self.n_computed = 1
    def __call__(self, h_dec_step, Wq):
        Q = h_dec_step @ Wq
        s = Q @ self.K.T / math.sqrt(Q.shape[-1])
        return softmax(s) @ self.V

def cross_attn_naive(h_step, memory, Wq, Wk, Wv):
    '''不缓存：每步重算 K/V。'''
    out, _ = attend(h_step[None, :], memory, Wq, Wk, Wv)
    return out[0]

cache = CrossAttnCache(Xenc, Wk, Wv)
m_steps = 5
for t in range(m_steps):
    h_t = rng.normal(size=D)
    a = cache(h_t[None, :], Wq)[0]
    b = cross_attn_naive(h_t, Xenc, Wq, Wk, Wv)
    assert np.allclose(a, b, atol=1e-12), f'step {t}: 缓存版与朴素版必须完全一致'
print(f'✅ 对拍通过：{m_steps} 个解码步，缓存版与朴素重算完全一致')
print(f'   K/V 投影计算次数: 缓存 {cache.n_computed} 次 vs 朴素 {m_steps} 次')

# 长输入时的节省
for n_src_, m_ in [(64, 16), (512, 32), (4096, 100)]:
    naive_kv = m_ * (2 * n_src_ * D * D)
    cached_kv = 1 * (2 * n_src_ * D * D)
    print(f'  输入{n_src_:>5d} 输出{m_:>4d}: cross-KV 投影计算省 {naive_kv/cached_kv:.0f}×')
assert 100 * 2 * 4096 * D * D / (2 * 4096 * D * D) == 100
print('\\n✅ 输入越长、输出越短，enc-dec 的这个结构性优势越明显（模块 05 会算完整的账）')"""),
    md("""## 2 · T5 的 span corruption：构造与可逆性

连续片段整体挖掉 → 哨兵 token；**目标序列只含被挖内容**（不重复未挖部分）。
这个设计让目标短约 5 倍，是 T5 训练效率的关键。"""),
    code("""SENTINEL_BASE = 1000     # <extra_id_0> = 1000, <extra_id_1> = 1001, ...
V_REAL = 200

def span_corrupt(tokens, corrupt_rate=0.15, mean_span=3, seed=0):
    '''返回 (编码器输入, 解码器目标)。'''
    r = np.random.default_rng(seed)
    n = len(tokens)
    n_corrupt = max(1, int(round(n * corrupt_rate)))
    n_spans = max(1, int(round(n_corrupt / mean_span)))
    # 随机挑 n_spans 个不重叠片段
    spans, used = [], np.zeros(n, dtype=bool)
    tries = 0
    while len(spans) < n_spans and tries < 100:
        tries += 1
        ln = max(1, int(r.poisson(mean_span)))
        st = int(r.integers(0, max(1, n - ln)))
        if used[st:st + ln].any():
            continue
        used[st:st + ln] = True
        spans.append((st, st + ln))
    spans.sort()
    enc, dec, prev, sid = [], [], 0, 0
    for st, en in spans:
        enc.extend(tokens[prev:st]); enc.append(SENTINEL_BASE + sid)
        dec.append(SENTINEL_BASE + sid); dec.extend(tokens[st:en])
        prev, sid = en, sid + 1
    enc.extend(tokens[prev:])
    dec.append(SENTINEL_BASE + sid)          # 收尾哨兵
    return enc, dec, spans

def span_restore(enc, dec):
    '''从 (编码器输入, 解码器目标) 还原原文 —— 用于**可逆性对拍**。'''
    # 解析 dec：哨兵 i 之后到下一个哨兵之前的内容，属于哨兵 i
    fills, cur = {}, None
    for t in dec:
        if t >= SENTINEL_BASE:
            cur = t; fills[cur] = []
        elif cur is not None:
            fills[cur].append(t)
    out = []
    for t in enc:
        out.extend(fills.get(t, [])) if t >= SENTINEL_BASE else out.append(t)
    return out

original = list(rng.integers(0, V_REAL, size=30))
enc, dec, spans = span_corrupt(original, seed=2)
print('原文长度:', len(original))
print('编码器输入长度:', len(enc), ' (被挖片段换成单个哨兵 -> 变短)')
print('解码器目标长度:', len(dec), f' ({len(dec)/len(original):.0%} of 原文)')
print(f'挖了 {len(spans)} 个片段: {spans}')

restored = span_restore(enc, dec)
assert restored == original, 'span corruption 必须是**可逆**的（否则信息丢了）'
assert len(dec) < 0.5 * len(original), '目标序列应远短于原文 —— 这是 T5 的效率关键'
assert sum(1 for t in enc if t >= SENTINEL_BASE) == len(spans)
assert sum(1 for t in dec if t >= SENTINEL_BASE) == len(spans) + 1, '目标末尾要多一个收尾哨兵'
print('\\n✅ 可逆性对拍通过：enc + dec 能完整还原原文')"""),
    md("""### T5 vs BART：目标长度的差别就是解码算力的差别"""),
    code("""def bart_style_target(tokens):
    '''BART：重建**整个**原文。'''
    return list(tokens)

for L in [64, 256, 512]:
    toks = list(rng.integers(0, V_REAL, size=L))
    e, d, _ = span_corrupt(toks, seed=1)
    b = bart_style_target(toks)
    # 解码器自注意力 ~ O(len^2)，FFN ~ O(len)；用平方项做主导估计
    ratio = (len(b) ** 2) / (len(d) ** 2)
    print(f'原文 {L:>4d}: T5 目标 {len(d):>4d} | BART 目标 {len(b):>4d} | 解码自注意力算力 {ratio:>5.1f}×')

toks = list(rng.integers(0, V_REAL, size=512))
_, d5, _ = span_corrupt(toks, seed=1)
assert len(d5) < 0.35 * 512, 'T5 目标应远短于原文'
assert (512 ** 2) / (len(d5) ** 2) > 8, 'T5 的解码算力应省近一个数量级'
print('\\n✅ 「目标只含被挖内容」这一个设计，就省下了解码侧近一个数量级的算力。')
print('   BART 的代价换来的是「天然适合生成完整流畅文本」（摘要类任务）。')"""),
    md("""## 3 · BART 的五种噪声"""),
    code("""MASK_ID = 999

def token_masking(t, p=0.15, seed=0):
    r = np.random.default_rng(seed); t = list(t)
    for i in range(len(t)):
        if r.random() < p: t[i] = MASK_ID
    return t

def token_deletion(t, p=0.15, seed=0):
    r = np.random.default_rng(seed)
    return [x for x in t if r.random() >= p]          # **不留占位符**

def text_infilling(t, p=0.15, lam=3, seed=0):
    '''连续片段换成**单个** mask；片段长 ~ Poisson(λ)，**可以为 0**（=插入一个 mask）。'''
    r = np.random.default_rng(seed); t = list(t); out, i = [], 0
    budget = int(len(t) * p)
    while i < len(t):
        if budget > 0 and r.random() < p:
            ln = int(r.poisson(lam))
            out.append(MASK_ID)                        # 一个 mask 代表未知长度的片段
            i += ln; budget -= max(ln, 1)
        else:
            out.append(t[i]); i += 1
    return out

def sentence_permutation(sents, seed=0):
    r = np.random.default_rng(seed); s = list(sents); r.shuffle(s); return s

def document_rotation(t, seed=0):
    r = np.random.default_rng(seed); k = int(r.integers(0, len(t)))
    return list(t[k:]) + list(t[:k])

src = list(range(20))
print('原文        :', src)
print('token mask  :', token_masking(src, seed=1))
print('token delete:', token_deletion(src, seed=1), ' <- 长度变了！模型要自己发现「少了东西」')
print('text infill :', text_infilling(src, seed=1), ' <- 一个 mask 可能代表 0/1/多个词')
print('doc rotation:', document_rotation(src, seed=1))

del_out = token_deletion(src, seed=1)
mask_out = token_masking(src, seed=1)
assert len(mask_out) == len(src), 'masking 保长度 —— 泄漏了「缺几个词」这个信息'
assert len(del_out) < len(src), 'deletion 改变长度 —— 更难，模型要判断哪里少了'
inf_out = text_infilling(src, seed=1)
n_masks = sum(1 for x in inf_out if x == MASK_ID)
assert n_masks >= 1
print(f'\\n✅ text infilling 用 {n_masks} 个 mask 覆盖了未知数量的原 token ——')
print('   模型必须同时恢复内容、判断缺失长度、保持流畅。BART 论文认为这是最有效的单项噪声。')
print('   对照：token masking 有几个 [MASK] 就缺几个词，任务简单得多。')"""),
    md("""## 4 · teacher forcing：那个要命的 off-by-one

训练时 decoder 输入 = 目标右移一位。**shift 错一位，训练能跑但模型学的是「抄当前 token」。**
用一个 assert 把它钉死。"""),
    code("""BOS, EOS = 990, 991

def shift_right(target, bos=BOS):
    '''decoder 输入 = [bos] + target[:-1]'''
    return [bos] + list(target[:-1])

def build_teacher_forcing(target):
    return shift_right(target), list(target)

tgt = [11, 22, 33, EOS]
dec_in, dec_out = build_teacher_forcing(tgt)
print('目标序列    :', tgt)
print('decoder 输入:', dec_in)
print('decoder 目标:', dec_out)
for t in range(len(tgt)):
    print(f'  位置 {t}: 看到 {dec_in[:t+1]} -> 应预测 {dec_out[t]}')

assert dec_in[0] == BOS, '第一个输入必须是起始符'
assert dec_in[1:] == dec_out[:-1], '输入必须是目标右移一位'
assert len(dec_in) == len(dec_out) == len(tgt)
# 反面：忘记 shift（直接把 target 当输入）
bad_in = list(tgt)
assert bad_in[0] == dec_out[0], '⚠️ 忘记 shift 时，位置 0 的输入就等于它要预测的目标 —— 抄答案！'
print('\\n⚠️  忘记 shift 的后果：每个位置的输入就是它要预测的目标 -> loss 迅速趋零，模型什么也没学。')
print('    推理时没有「当前 token」可抄，输出全是垃圾。这是 seq2seq 最常见的 bug。')
print('✅ shift 正确性已用 assert 钉死')"""),
    md("""### 因果掩码 + teacher forcing = 并行训练

一次前向算出全部位置的损失，而推理必须串行 m 步。"""),
    code("""def parallel_train_steps(m):   return 1
def autoregressive_infer_steps(m): return m

for m_ in [4, 32, 256]:
    print(f'输出长度 {m_:>4d}: 训练前向 {parallel_train_steps(m_)} 次 | 推理前向 {autoregressive_infer_steps(m_)} 次')
assert parallel_train_steps(256) == 1 and autoregressive_infer_steps(256) == 256
print('\\n✅ 这个 1 : m 的不对称，是 teacher forcing 存在的全部理由，')
print('   也是 exposure bias 的全部根源 —— 训练时喂真实前缀，推理时喂自己生成的。')"""),
    md("""## 5 · exposure bias：错误如何累积

训练时模型只见过**完美前缀**。推理时一旦出错，输入就落在训练分布之外。
下面用一个可控的玩具模型把「错误累积」演示出来。"""),
    code("""V_T = 8

def make_toy_seq_model(err_rate, recovery=0.10, seed=0):
    '''玩具转移模型。前缀正确时：以 (1-err_rate) 概率预测对下一个。
       前缀**出错**后：模型进入训练时从未见过的状态，只有 recovery 的概率回到正轨。
       err_rate 是「单步错误率」，recovery 是「从错误状态自我修复」的概率。'''
    r = np.random.default_rng(seed)
    true_next = {t: (t + 1) % V_T for t in range(V_T)}          # 真实规律：+1
    def step(prev_token, prev_was_correct):
        p_correct = (1 - err_rate) if prev_was_correct else recovery
        if r.random() < p_correct:
            return true_next[prev_token], True
        wrong = int(r.integers(0, V_T))
        while wrong == true_next[prev_token]:
            wrong = int(r.integers(0, V_T))
        return wrong, False
    return step, true_next

def generate(err_rate, length, seed=0):
    step, true_next = make_toy_seq_model(err_rate, seed=seed)
    tok, ok, correct_flags = 0, True, []
    for _ in range(length):
        tok, ok = step(tok, ok)
        correct_flags.append(ok)
    return correct_flags

LEN = 30
for err in [0.02, 0.05, 0.10]:
    trials = [generate(err, LEN, seed=s) for s in range(300)]
    by_pos = np.array(trials).mean(0)
    print(f'单步错误率 {err:.0%}: 位置 1 正确率 {by_pos[0]:.0%} | '
          f'位置 10 {by_pos[9]:.0%} | 位置 30 {by_pos[-1]:.0%}')

trials = np.array([generate(0.05, LEN, seed=s) for s in range(500)]).mean(0)
assert trials[0] > trials[-1], '正确率应随位置下降 —— 这就是错误累积'
assert trials[-1] < 0.75 * trials[0], '尾部正确率应显著低于开头'
print(f'\\n✅ 单步错误率仅 5%，但生成到第 30 个 token 时正确率已从 {trials[0]:.0%} 掉到 {trials[-1]:.0%}。')
print('   典型症状：开头很好、越往后越离谱，或陷入重复循环。')
print('   缓解：scheduled sampling（训练时混入自生成前缀）、序列级训练、或解码时用 beam/惩罚兜底。')"""),
    md("""## 6 · beam search：实现、对拍、长度惩罚与「beam 诅咒」"""),
    code("""def greedy_decode(logprob_fn, max_len, eos=EOS):
    seq, total = [], 0.0
    for _ in range(max_len):
        lp = logprob_fn(tuple(seq))
        t = int(np.argmax(lp)); total += lp[t]; seq.append(t)
        if t == eos: break
    return seq, total

def beam_search(logprob_fn, max_len, beam=3, eos=EOS, alpha=0.0):
    '''返回按（长度归一化后）分数排序的完成序列列表。'''
    def lp_norm(score, length):
        if alpha == 0.0: return score
        return score / (((5 + length) / 6) ** alpha)
    live = [([], 0.0)]          # (序列, 累积 logprob)
    done = []
    for _ in range(max_len):
        cands = []
        for seq, sc in live:
            lp = logprob_fn(tuple(seq))
            for t in np.argsort(lp)[-beam:]:
                cands.append((seq + [int(t)], sc + float(lp[t])))
        cands.sort(key=lambda x: lp_norm(x[1], len(x[0])), reverse=True)
        live = []
        for seq, sc in cands:
            if seq[-1] == eos:  done.append((seq, sc))
            else:               live.append((seq, sc))
            if len(live) >= beam: break
        if not live: break
    done += live
    done.sort(key=lambda x: lp_norm(x[1], len(x[0])), reverse=True)
    return done

def make_logprob_fn(seed=0, vocab=6, eos=5):
    '''一个确定性的玩具语言模型：下一个 token 的分布由前缀哈希决定。'''
    def fn(prefix):
        r = np.random.default_rng((hash(prefix) ^ seed) % (2**32))
        logits = r.normal(size=vocab)
        return np.log(softmax(logits))
    return fn

VOC, EOS_T = 6, 5
fn = make_logprob_fn(seed=7, vocab=VOC, eos=EOS_T)

def brute_force_best(fn, max_len, vocab, eos):
    '''穷举所有长度 <= max_len 的序列，找累积 logprob 最大的（作为对拍参考）。'''
    best, bs = None, -np.inf
    def rec(seq, sc):
        nonlocal best, bs
        if seq and seq[-1] == eos:
            if sc > bs: bs, best = sc, list(seq)
            return
        if len(seq) == max_len:
            if sc > bs: bs, best = sc, list(seq)
            return
        lp = fn(tuple(seq))
        for t in range(vocab):
            rec(seq + [t], sc + float(lp[t]))
    rec([], 0.0)
    return best, bs

MAXL = 4
bf_seq, bf_score = brute_force_best(fn, MAXL, VOC, EOS_T)
bs_wide = beam_search(fn, MAXL, beam=VOC, eos=EOS_T, alpha=0.0)
print(f'穷举最优      : {bf_seq}  score {bf_score:.4f}')
print(f'beam=全词表   : {bs_wide[0][0]}  score {bs_wide[0][1]:.4f}')
assert abs(bs_wide[0][1] - bf_score) < 1e-9, 'beam=|V| 时应等价于穷举（在此深度下）'
print('✅ 对拍通过：beam 宽到全词表时，beam search 退化为穷举搜索')

g_seq, g_score = greedy_decode(fn, MAXL, eos=EOS_T)
b3 = beam_search(fn, MAXL, beam=3, eos=EOS_T, alpha=0.0)
print(f'\\ngreedy       : {g_seq}  score {g_score:.4f}')
print(f'beam=3       : {b3[0][0]}  score {b3[0][1]:.4f}')
assert b3[0][1] >= g_score - 1e-9, 'beam search 的分数不应低于贪心'
print('✅ beam search 分数 >= 贪心（它搜索了更大的空间）')"""),
    md("""### 长度惩罚：不加会系统性偏好短序列"""),
    code("""def length_penalty(t, alpha):
    return ((5 + t) / 6) ** alpha

print(f"{'长度':>5s} " + ' '.join(f'α={a:<5.1f}' for a in [0.0, 0.6, 1.0]))
for L in [1, 5, 10, 20, 40]:
    print(f'{L:>5d} ' + ' '.join(f'{length_penalty(L,a):<7.3f}' for a in [0.0, 0.6, 1.0]))

# 关键性质：α>0 时惩罚随长度递增 -> 抵消「长序列 logprob 更负」的偏置
assert length_penalty(1, 0.0) == length_penalty(40, 0.0) == 1.0, 'α=0 等于不归一化'
assert length_penalty(40, 1.0) > length_penalty(5, 1.0), 'α>0 时长序列被除以更大的数'

# 演示偏置：两条候选，一条短但每步概率一般，一条长但每步概率高
short_score, short_len = -3.0, 3          # 平均 -1.00/步
long_score,  long_len  = -6.0, 12         # 平均 -0.50/步 ← 其实更好
for a in [0.0, 0.6, 1.0]:
    s_n = short_score / length_penalty(short_len, a)
    l_n = long_score / length_penalty(long_len, a)
    winner = '短' if s_n > l_n else '长'
    print(f'α={a:.1f}: 短 {s_n:>7.3f} | 长 {l_n:>7.3f} -> 选「{winner}」')
assert short_score > long_score, '不归一化时短序列必胜（log 概率少加了几个负数）'
assert long_score / length_penalty(long_len, 1.0) > short_score / length_penalty(short_len, 1.0)
print('\\n✅ 不加长度惩罚，beam search 会系统性偏好短输出（翻译漏译、摘要过短）。')
print('   GNMT 的 lp(t)=((5+t)/6)^α 是经验公式，α∈[0.6,1.0] 是常用区间。')"""),
    md("""### beam 诅咒：beam 越大，「最优」序列越退化"""),
    code("""def degenerate_lm(vocab=6, eos=5, eos_boost=0.0):
    '''一个带退化倾向的模型：EOS 有额外的先验偏好（模拟 MLE 训练模型的众数退化）。'''
    def fn(prefix):
        r = np.random.default_rng((hash(prefix) ^ 99) % (2**32))
        logits = r.normal(size=vocab)
        logits[eos] += eos_boost + 0.4 * len(prefix)     # 越往后越想停
        return np.log(softmax(logits))
    return fn

fn_deg = degenerate_lm(eos_boost=1.2)
print(f"{'beam':>5s} {'最优序列':<22s} {'长度':>5s} {'score':>9s}")
lengths = []
for bm in [1, 2, 4, 6]:
    res = beam_search(fn_deg, 8, beam=bm, eos=EOS_T, alpha=0.0)
    seq = res[0][0]; lengths.append(len(seq))
    print(f'{bm:>5d} {str(seq):<22s} {len(seq):>5d} {res[0][1]:>9.4f}')

assert lengths[-1] <= lengths[0], 'beam 越大，越倾向找到那个「更短更安全」的高似然序列'
print('\\n✅ beam 越大 -> 越接近真正的最大似然序列 -> 而 MLE 模型的众数往往是**退化的**（过短/套话）。')
print('   小 beam 的「搜索不充分」意外地起到了正则化作用。')
print('   这揭示了一个根本问题：**训练目标（最大似然）与我们真正想要的（好输出）系统性错位**。')
print('   这正是后来 RLHF / 对比解码等「直接优化偏好」方法的动机之一。')"""),
    md("""## ✏️ 练习 1：cross-attention 即对齐

实现 `alignment_from_cross_attn(A_cross)`：给定 `(m, n)` 的 cross-attention 矩阵，
返回每个输出位置最关注的输入位置列表（长度 m）。
再实现 `is_monotonic(alignment)`：判断对齐是否单调不减（翻译中相近语言常近似单调）。"""),
    code("""def alignment_from_cross_attn(A_cross):
    # TODO: 每行取 argmax
    raise NotImplementedError

def is_monotonic(alignment):
    # TODO: 判断列表是否单调不减
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
A = np.array([[0.8, 0.1, 0.1],
              [0.1, 0.7, 0.2],
              [0.1, 0.2, 0.7]])
assert alignment_from_cross_attn(A) == [0, 1, 2]
assert is_monotonic([0, 1, 2]) and is_monotonic([0, 0, 2, 2])
assert not is_monotonic([0, 2, 1])
# 随机矩阵一般不单调
A_rand = softmax(rng.normal(size=(6, 8)), axis=-1)
al = alignment_from_cross_attn(A_rand)
assert len(al) == 6 and all(0 <= a < 8 for a in al)
print('对齐:', al, '| 单调?', is_monotonic(al))
print('✅ 练习 1 通过：cross-attn 的 (m,n) 矩阵近似词对齐，是 enc-dec 的经典可解释性来源')"""),
    md("""## ✏️ 练习 2：span corruption 的参数化

实现 `corruption_stats(length, corrupt_rate, mean_span, n_trials=200)`：
返回 `(平均编码器输入长度, 平均解码器目标长度, 平均片段数)`。
验证：`mean_span` 越大，片段数越少但每段越长；目标长度大体不变。"""),
    code("""def corruption_stats(length, corrupt_rate, mean_span, n_trials=200):
    # TODO: 多次调用 span_corrupt（每次换 seed 与随机 token），取三个量的均值
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
e3, d3, s3 = corruption_stats(100, 0.15, 3)
e8, d8, s8 = corruption_stats(100, 0.15, 8)
print(f'mean_span=3: 编码器 {e3:.1f}, 解码器 {d3:.1f}, 片段数 {s3:.1f}')
print(f'mean_span=8: 编码器 {e8:.1f}, 解码器 {d8:.1f}, 片段数 {s8:.1f}')
assert s3 > s8, 'mean_span 越大，片段数越少'
assert d3 < 100 and d8 < 100, '目标长度应远短于原文'
assert e3 < 100 and e8 < 100, '编码器输入也变短（片段被压成一个哨兵）'
# 掩码率越高，目标越长
_, d_hi, _ = corruption_stats(100, 0.50, 3)
assert d_hi > d3, '更高掩码率 -> 更长的目标序列'
print('✅ 练习 2 通过：T5 的两个超参（比例、片段长）共同决定目标长度=解码算力')"""),
    md("""## ✏️ 练习 3：带重复惩罚的解码

实现 `greedy_with_repetition_penalty(logprob_fn, max_len, penalty=1.2, eos=EOS_T)`：
每步在 argmax 之前，按 token **已出现的次数**惩罚它的 logprob：
`lp[t] *= penalty ** count[t]`（logprob 恒为负，乘 >1 的数使其更负 = 被压低）。

> ⚠️ 这里刻意用**按次数累加**的惩罚，而不是「出现过就罚一次」。
> 后者（HF 的 `repetition_penalty`）在模型极度偏好某个 token 时**打不破循环**——
> 惩罚只施加一次，被压低后仍是最大值，于是继续重复。
> 按次数累加（近似 OpenAI 的 `frequency_penalty`）才能保证惩罚最终超过偏好。
> **这个差别在真实调参时很关键**：`repetition_penalty=1.2` 治不好的循环，
> 往往要靠 `no_repeat_ngram_size` 或频次惩罚。"""),
    code("""def greedy_with_repetition_penalty(logprob_fn, max_len, penalty=1.2, eos=EOS_T):
    # TODO: 维护 counts（collections.Counter）；每步 lp = logprob_fn(prefix).copy()
    #       对每个出现过的 t: lp[t] *= penalty ** counts[t]
    #       取 argmax，遇到 eos 停止；返回 (序列, **未惩罚的**累积 logprob)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
def repetitive_lm(vocab=6, eos=5, sticky=2):
    def fn(prefix):
        logits = np.full(vocab, -2.0)
        logits[sticky] = 1.0       # 偏好 token 2（但不是压倒性的）
        logits[1] = 0.5            # 次优选择
        logits[eos] = -3.0         # eos 很不可能 -> 不靠 eos 逃出循环
        return np.log(softmax(logits))
    return fn

fn_rep = repetitive_lm()
plain, _ = greedy_decode(fn_rep, 8, eos=EOS_T)
penal, _ = greedy_with_repetition_penalty(fn_rep, 8, penalty=2.0, eos=EOS_T)
print('无惩罚:', plain)
print('有惩罚:', penal)
assert plain.count(2) >= 6, '无惩罚时应陷入重复循环'
assert penal.count(2) < plain.count(2), '重复惩罚应打破循环'
assert len(set(penal)) > len(set(plain)), '有惩罚的输出更多样'
# 「出现过就罚一次」在同一个模型上会失败 —— 亲手验证这个差别
def penalize_once(logprob_fn, max_len, penalty=2.0, eos=EOS_T):
    seq, seen = [], set()
    for _ in range(max_len):
        lp = logprob_fn(tuple(seq)).copy()
        for t in seen: lp[t] *= penalty
        t = int(np.argmax(lp)); seq.append(t); seen.add(t)
        if t == eos: break
    return seq
once = penalize_once(fn_rep, 8, penalty=2.0)
print('只罚一次:', once, f'  -> token2 出现 {once.count(2)} 次')
assert once.count(2) > penal.count(2), '「只罚一次」被压低后仍是最大值 -> 继续重复'
print('✅ 练习 3 通过：惩罚必须**按次数累加**才能保证最终超过模型的偏好；')
print('   这也是 repetition_penalty=1.2 治不好循环时要换 no_repeat_ngram_size 的原因。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def alignment_from_cross_attn(A_cross):
    return [int(i) for i in A_cross.argmax(axis=1)]

def is_monotonic(alignment):
    return all(a <= b for a, b in zip(alignment, alignment[1:]))"""),
    code("""# 练习 2 参考答案
def corruption_stats(length, corrupt_rate, mean_span, n_trials=200):
    es, ds, ss = [], [], []
    for s in range(n_trials):
        toks = list(np.random.default_rng(s).integers(0, V_REAL, size=length))
        e, d, sp = span_corrupt(toks, corrupt_rate, mean_span, seed=s)
        es.append(len(e)); ds.append(len(d)); ss.append(len(sp))
    return float(np.mean(es)), float(np.mean(ds)), float(np.mean(ss))"""),
    code("""# 练习 3 参考答案
def greedy_with_repetition_penalty(logprob_fn, max_len, penalty=1.2, eos=EOS_T):
    seq, counts, total = [], collections.Counter(), 0.0
    for _ in range(max_len):
        raw = logprob_fn(tuple(seq))
        lp = raw.copy()
        for t, c in counts.items():
            lp[t] *= penalty ** c            # lp < 0，乘 >1 使其更负；次数越多罚得越重
        t = int(np.argmax(lp))
        total += float(raw[t])               # 累积**未惩罚的** logprob
        seq.append(t); counts[t] += 1
        if t == eos: break
    return seq, total"""),
    md("""---
## 🧪 真实数据胶囊：T5 的训练算力账

把「目标只含被挖片段」这个设计的收益，换算成端到端的训练算力节省。
用 T5-base 的公开配置（12+12 层、d=768、输入 512）。"""),
    code("""d_model, n_enc, n_dec, L_in = 768, 12, 12, 512

def transformer_flops(n_layers, seq_len, d, cross_attn_src=0):
    '''粗估一层的前向 FLOPs：注意力(投影+分数) + FFN。'''
    proj = 4 * seq_len * d * d
    attn = 2 * seq_len * seq_len * d
    ffn  = 2 * seq_len * d * (4 * d)
    cross = (4 * seq_len * d * d + 2 * seq_len * cross_attn_src * d) if cross_attn_src else 0
    return n_layers * (proj + attn + ffn + cross)

def total_flops(L_target):
    enc = transformer_flops(n_enc, L_in, d_model)
    dec = transformer_flops(n_dec, L_target, d_model, cross_attn_src=L_in)
    return enc + dec, enc, dec

L_t5 = 114        # T5 式目标长度（约 0.22 × 512，含哨兵）
L_bart = L_in     # BART 式：重建整句

f_t5, e_t5, d_t5 = total_flops(L_t5)
f_bart, e_b, d_b = total_flops(L_bart)
print(f'T5   目标长 {L_t5:>4d}: 编码 {e_t5/1e9:>7.1f}G + 解码 {d_t5/1e9:>7.1f}G = {f_t5/1e9:>7.1f} GFLOPs')
print(f'BART 目标长 {L_bart:>4d}: 编码 {e_b/1e9:>7.1f}G + 解码 {d_b/1e9:>7.1f}G = {f_bart/1e9:>7.1f} GFLOPs')
print(f'\\n解码侧省 {d_b/d_t5:.1f}× | 端到端省 {(1 - f_t5/f_bart):.0%}')
assert d_b / d_t5 > 3, '解码侧应省数倍'
assert f_t5 < 0.75 * f_bart, '端到端应省 25% 以上'
print('✅ 「目标只含被挖内容」不是小优化 —— 它是 T5 能用同等预算训更久的原因之一。')"""),
    md("""**🧪 胶囊练习**：实现 `encdec_vs_declonly_kv(n_in, m_out, d, n_layers, k_beams=1)`：
比较两种形态在解码到第 `m_out` 步时的 **KV 缓存元素数**。

- enc-dec：cross-KV `2·L·n_in·d`（由编码器输出算出，**所有候选束共享、只读、只存一份**）
  \+ 解码器 self-KV `2·L·m_out·d` × `k_beams`
- decoder-only：`2·L·(n_in + m_out)·d` × `k_beams`（**整段前缀都要每束一份**）

返回 `(encdec_elems, declonly_elems, ratio)`。

> ⚠️ 先自己算一下 `k_beams=1` 的情形，再看断言——**结果可能和你预期的不一样**。
> 「enc-dec 更省 KV」是个流传很广但需要加条件的说法。"""),
    code("""def encdec_vs_declonly_kv(n_in, m_out, d, n_layers, k_beams=1):
    # TODO
    raise NotImplementedError"""),
    code("""# 自测
a1, b1, r1 = encdec_vs_declonly_kv(4096, 100, 768, 12, k_beams=1)
print(f'单束  长输入(4096) 短输出(100): enc-dec {a1/1e6:.1f}M vs dec-only {b1/1e6:.1f}M '
      f'({r1:.3f}×)')
assert a1 == b1 and abs(r1 - 1.0) < 1e-12, \\
    '⚠️ 单束时两者**完全相同** —— cross-KV(n) + self-KV(m) 恰好等于 (n+m)'
print('   ⚠️ 单束时两者**完全相同**：cross-KV(n) + self-KV(m) 恰好 = (n+m)。')
print('      流传的「enc-dec 更省 KV」在 k=1 时并不成立。')

# 多候选束时优势才出现：cross-KV 共享、不随束数复制
a4, b4, r4 = encdec_vs_declonly_kv(4096, 100, 768, 12, k_beams=4)
print(f'\\n4 束  长输入(4096) 短输出(100): enc-dec {a4/1e6:.1f}M vs dec-only {b4/1e6:.1f}M '
      f'({r4:.3f}× -> 省 {1/r4:.1f}×)')
assert r4 < 0.3, '长输入 + 多束时 enc-dec 应省 3 倍以上'

# 短输入长输出时优势消失（要共享的那部分本来就很小）
a5, b5, r5 = encdec_vs_declonly_kv(100, 4096, 768, 12, k_beams=4)
print(f'4 束  短输入(100) 长输出(4096): enc-dec {a5/1e6:.1f}M vs dec-only {b5/1e6:.1f}M '
      f'({r5:.3f}×)')
assert 0.9 < r5 < 1.0, '短输入长输出时几乎没有差别 —— 可共享的 cross-KV 太小'
print('\\n✅ 胶囊练习通过：enc-dec 的 KV 优势需要**两个条件同时成立** ——')
print('   ① n ≫ m（输入远长于输出）  ② k > 1（beam / 多候选采样）')
print('   缺一个都退化成「两者相同」。这正是「长文档摘要用 T5、开放对话用 decoder-only」')
print('   的定量依据（模块 05 展开），也是一个「别把流传的说法当结论」的例子。')"""),
    code("""# 📖 胶囊参考答案
def encdec_vs_declonly_kv(n_in, m_out, d, n_layers, k_beams=1):
    unit = 2 * n_layers * d
    encdec = unit * (n_in + k_beams * m_out)     # cross-KV 只存一份，self-KV 每束一份
    declonly = unit * k_beams * (n_in + m_out)   # 整段前缀每束一份
    return encdec, declonly, encdec / declonly"""),
    md("""---
## 🔧 旁注：真实库里这些对应什么

- **cross-attention** → `T5Stack` 里 `is_decoder=True` 时的 `EncDecAttention`；`past_key_values` 里 cross-KV 只在第一步计算。
- **span corruption** → T5 预训练脚本的 `random_spans_noise_mask`；哨兵是 `<extra_id_0>`…`<extra_id_99>`。
- **BART 噪声** → `BartTokenizer` + 自定义 collator；HF 没有内置全部五种。
- **teacher forcing shift** → `model.prepare_decoder_input_ids_from_labels()` / `shift_tokens_right()`；**BART 用 `</s>` 而非 `<s>` 起始**。
- **beam search + 长度惩罚** → `model.generate(num_beams=4, length_penalty=1.0, early_stopping=True)`。
- **重复惩罚** → `generate(repetition_penalty=1.2, no_repeat_ngram_size=3)`。
- **约束解码（把生成限制在标签集）** → `generate(force_words_ids=...)` 或 `LogitsProcessor`。

怎么用这些真正跑起来，见 **C50**。"""),
    md("""### 小结
- Transformer **本来就是 enc-dec**；BERT 与 GPT 都是后来的裁剪。三种注意力共用同一个公式，只是 (Q源, KV源, 掩码) 不同。
- **cross-attention 的 K/V 只算一次**并可缓存——这是「输入长、输出短」场景下 enc-dec 的结构性优势。
- **T5：万物皆文本 + span corruption**；「目标只含被挖内容」让解码算力省数倍、端到端省 25%+。代价是分类/回归失去输出空间约束。
- **BART：去噪自编码**，五种噪声里 text infilling 最有效（长度未知，任务更难）。
- **teacher forcing 的 off-by-one 是最常见的 seq2seq bug**；它带来并行训练（1 次前向 vs m 次），也带来 **exposure bias**。
- **beam search 要加长度惩罚**，否则系统性偏好短输出；而 **beam 越大反而越差**——因为 MLE 模型的众数是退化的，这暴露了训练目标与真实目标的错位。

下一站：**模块 05 · 今天还要不要 encoder** —— 把三种形态放在成本-精度的同一张图上，做出有依据的选型。"""),
]
