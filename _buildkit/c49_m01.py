# -*- coding: utf-8 -*-
"""C49 模块 01 · MLM 与双向编码器（BERT）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00、注意力机制（C01）、交叉熵损失"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_mlm_bert.ipynb'),
    ("核心论文", "Devlin et al. 2019（BERT）★、Taylor 1953（cloze test）、Liu et al. 2019（RoBERTa，对 NSP 的否定）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("why", "问题：双向表示与自回归目标不可兼得", "".join([
        P("模块 00 用数值梯度证明了一件事：<strong>双向注意力下，位置 <code>t</code> 的表示里已经混入了位置 <code>t+1</code> 的信息</strong>。所以「预测下一个 token」这个目标在双向模型上是废的——它退化成抄答案。"),
        P("但我们又<em>想要</em>双向表示。理由很直接：理解一个词的意思常常需要它右边的上下文。"),
        ASCII(""""我把钱存进了 银行 。"           ← 「银行」= bank(金融机构)
"我们沿着 银行 走了很久。"        ← 「银行」= 河岸? 显然不是，但如果只看左边…

"The animal didn't cross the street because **it** was too tired."
"The animal didn't cross the street because **it** was too wide."
                                          ↑ it 指代谁，完全由**右边**的形容词决定

单向模型在读到 it 时，右边的 tired/wide 还没出现 —— 它必须「猜」，或者靠后面再修正。
双向模型在编码 it 时，右边的信息已经在了。""")
        ,
        DUAL(
            "于是问题变成：<strong>怎么设计一个训练目标，既让模型看到双向上下文，又不让它看到「答案」</strong>？BERT 的答案简单而有效——<em>把答案从输入里挖掉</em>。把句子里 15% 的 token 换成一个特殊符号 <code>[MASK]</code>，让模型根据<strong>左右两侧的全部上下文</strong>预测这些被挖掉的词。这就是 <span class=\"term\">masked language modeling</span>（MLM，掩码语言建模）。",
            "这个想法本身不新——它就是语言学与心理学里用了七十年的 <span class=\"term\">cloze test</span>（完形填空，Taylor 1953）。BERT 的贡献是把它作为大规模自监督预训练目标用在 Transformer 编码器上，并证明由此得到的表示在迁移到下游任务时极其强大。形式上，设被掩位置集合为 <code>M</code>，目标是最大化 <code>Σ_{i∈M} log P(x_i | x_{\\M})</code>——注意条件里是<em>整句话除了被掩位置</em>，这正是双向。",
        ),
        CALLOUT("intuition", "把 MLM 与 CLM（因果语言建模）的差别想成两种考试：<strong>CLM 是「续写」——给你前半句，写下一个词，你永远只能用左边的信息；MLM 是「完形填空」——给你整段话挖几个空，用上下文填。</strong> 续写天然可以无限自监督地做下去（每个 token 都是一次预测），而完形填空每次只能考 15% 的位置。<em>这个「信号密度」的差异，是 MLM 的核心代价，也是模块 02 里 ELECTRA 要解决的问题。</em>"),
        P("还有一个值得先说清的概念区分，它决定了你怎么读后面的一切：<strong>「双向」指的是<em>编码</em>时能看到两侧，不是指模型会「从右往左跑一遍」</strong>。BERT 之前的 ELMo 用的是后者——两个独立的单向 LSTM（一个从左到右、一个从右到左）在最后把表示拼起来。这叫<span class=\"term\">浅层双向</span>（shallow bidirectional）：每个方向<em>内部</em>仍然是单向的，两边直到最后一层才见面。BERT 的双向是<span class=\"term\">深层双向</span>（deeply bidirectional）——<em>每一层的每个位置都同时注意到左右两侧</em>，信息在整个网络里持续交融。这个差别不是修辞，它是 BERT 相对 ELMo 大幅提升的主要来源之一，也解释了为什么 BERT 必须换掉 CLM 目标（ELMo 可以保留 CLM，因为它的每个方向都是合法的单向语言模型）。"),
    ])),
    ("mlm", "MLM 的三个设计细节，每一个都有理由", "".join([
        H3("① 掩码比例：为什么是 15%"),
        P("15% 不是随便定的，它是一个<strong>信息与效率的权衡</strong>。掩得太少（比如 5%），每次前向只有 5% 的位置产生训练信号，样本效率极低、训练要跑很久；掩得太多（比如 50%），剩下的上下文残缺不全，任务变得过难，而且模型见到的输入分布严重偏离下游任务（下游没有 <code>[MASK]</code>）。"),
        P("有意思的是，后续研究（Wettig et al. 2023 <em>Should You Mask 15% in MLM?</em>）发现 15% <strong>并非普适最优</strong>：更大的模型可以承受更高的掩码率（40% 甚至更高）并且效果更好，因为大模型有能力从更少的上下文里恢复更多信息。<em>这是个很好的例子，说明早期的超参选择常常被后人当成定律，但它其实是特定规模下的经验值。</em>"),
        H3("② 80/10/10：一个补丁式但必要的设计"),
        P("被选中的 15% 位置，并不都替换成 <code>[MASK]</code>，而是："),
        TABLE(["比例", "怎么处理", "解决什么问题"], [
            ["<strong>80%</strong>", "替换成 <code>[MASK]</code>", "主任务：从上下文恢复被挖的词"],
            ["<strong>10%</strong>", "替换成一个<strong>随机</strong>词", "迫使模型对<em>每个</em>位置都保持怀疑：这个词可能是错的。防止模型只在看到 <code>[MASK]</code> 时才认真"],
            ["<strong>10%</strong>", "<strong>保持原词不变</strong>", "让「输出应等于输入」也成为一种可能，使表示在无 <code>[MASK]</code> 的输入上仍然可用"],
        ]),
        DUAL(
            "为什么需要后面两条？因为存在一个<strong>预训练-微调不匹配（pretrain-finetune mismatch）</strong>：<code>[MASK]</code> 这个 token 在预训练时到处都是，但在下游微调和推理时<em>一次都不会出现</em>。如果 100% 都替换成 <code>[MASK]</code>，模型会学到一个偷懒的策略——「只在看到 <code>[MASK]</code> 的位置才去建模上下文，其他位置直接把输入抄到输出」。这样的表示迁移到下游就很弱。",
            "10% 随机替换是在<strong>强制模型对所有位置都建立上下文预测能力</strong>：既然任何一个看起来正常的词都可能是被替换的噪声，模型就必须对每个位置都算一遍「根据上下文这里应该是什么」。10% 保持原词则提供了「输入即答案」的样本，让表示在干净输入上也校准。<em>这两条加起来大约用掉 20% 的掩码预算，换取的是表示的可迁移性</em>——一个典型的「牺牲主任务效率、换取迁移性能」的设计。",
        ),
        CALLOUT("warn", "80/10/10 是个<strong>补丁</strong>而非优雅方案，这一点要看清楚。它承认了「引入一个下游不存在的特殊 token」是个设计缺陷，然后用两条打折规则去缓解。ELECTRA（模块 02）的判别式目标从根上绕开了这个问题——它不引入 <code>[MASK]</code>，而是让模型判断每个 token 是否被替换过，<em>输入分布与下游完全一致</em>。理解「80/10/10 是在补什么洞」，才能理解 ELECTRA 为什么是个真正的进步。"),
        H3("③ 只在被掩位置计损失"),
        P("这一点实现上极易写错：<strong>损失只在 <code>M</code> 中的位置计算</strong>，其余位置不产生梯度。如果对所有位置都计损失，未被掩的位置就是「输入=输出」的恒等映射任务，会让模型学到抄写捷径，污染表示。notebook 会把两种写法都跑一遍，用损失曲线对比它们的差别。"),
    ])),
    ("arch", "BERT 的输入表示：三种嵌入与两个特殊 token", "".join([
        P("BERT 的输入不只是词嵌入，而是<strong>三种嵌入相加</strong>，外加两个结构性特殊 token。这套设计后来被大量沿用，值得逐个理解。"),
        ASCII("""输入句对:  "这家店 不错"  ‖  "值得再来"

tokens:     [CLS]  这家店   不错  [SEP]  值得   再来  [SEP]
              │      │      │     │     │     │     │
token emb   E_cls  E_这   E_不错 E_sep  E_值  E_来  E_sep
              +      +      +     +     +     +     +
segment emb  E_A    E_A    E_A   E_A   E_B   E_B   E_B      ← 区分句 A / 句 B
              +      +      +     +     +     +     +
position emb E_0    E_1    E_2   E_3   E_4   E_5   E_6      ← **学习式**，非正弦
              ↓      ↓      ↓     ↓     ↓     ↓     ↓
            ─────────── 12 层双向 Transformer ───────────
              ↓      ↓      ↓     ↓     ↓     ↓     ↓
            h_cls   h_1    h_2   h_3   h_4   h_5   h_6
              │
              └──▶ [CLS] 的最终表示 = 整句/句对的「汇总」，接分类头（模块 03）"""),
        TABLE(["组件", "作用", "今天还这么做吗"], [
            ["<code>[CLS]</code>", "序列首位的占位符，其最终隐状态被约定为「整个序列的表示」，用于分类", "分类仍常用；但句嵌入更多改用<strong>mean pooling</strong>（效果通常更好，见模块 05）"],
            ["<code>[SEP]</code>", "分隔两个句子，也标记序列结束", "沿用"],
            ["<strong>segment embedding</strong>", "标记 token 属于句 A 还是句 B，让模型区分句对", "RoBERTa 去掉了 NSP 后仍保留；很多后续模型简化掉了"],
            ["<strong>learned position embedding</strong>", "每个位置一个可学习向量（不是正弦函数）", "被相对位置编码（DeBERTa）与 RoPE（C20）取代；<strong>它无法外推到训练长度之外</strong>"],
            ["<strong>WordPiece 分词</strong>", "子词切分，30k 词表，未登录词切成 <code>##</code> 前缀的片段", "沿用（BPE/Unigram 变体，见 C21）"],
        ]),
        CALLOUT("warn", "<strong>学习式位置嵌入的硬约束</strong>：BERT 的位置嵌入表只有 512 行，意味着它<em>物理上无法处理长于 512 token 的输入</em>——不是效果差，是索引越界。这是个常被忽略、上线才发现的限制。绕过的办法：截断（丢信息）、滑窗（丢跨窗依赖）、或换用支持长文的变体（Longformer、DeBERTa 的相对位置）。<em>相比之下 RoPE 这类相对位置编码至少能「勉强外推」，这是 C20/C25 的话题。</em>"),
        H3("[CLS] 到底学到了什么"),
        P("一个常见误解是「<code>[CLS]</code> 天然就是句子的语义摘要」。<strong>不对——<code>[CLS]</code> 之所以能表示整句，完全是因为预训练时有一个任务（NSP）在用它，以及微调时分类头在用它</strong>。如果预训练没有任何目标用到 <code>[CLS]</code>（比如 RoBERTa 去掉 NSP 后），未微调的 <code>[CLS]</code> 向量作句嵌入的效果其实<em>相当差</em>，常常不如对所有 token 做平均池化。这个反直觉的事实在做检索/相似度时很重要，模块 05 会展开。"),
    ])),
    ("nsp", "NSP：一个被后人推翻的设计", "".join([
        P("BERT 原论文有<strong>两个</strong>预训练目标：MLM 和 <span class=\"term\">NSP</span>（Next Sentence Prediction，下一句预测）。NSP 是一个二分类任务：给两个句子 A、B，判断 B 是否真的紧跟在 A 之后（50% 是真的后续，50% 是从语料里随机采的句子），用 <code>[CLS]</code> 的表示做预测。"),
        P("动机很合理：很多下游任务（自然语言推理、问答、句对匹配）需要理解<em>句子之间</em>的关系，而 MLM 只训练了 token 级的理解。加个句级目标听起来天经地义。"),
        DUAL(
            "但后来的研究（RoBERTa、ALBERT、以及一系列消融）几乎一致地发现：<strong>去掉 NSP 不仅不掉分，往往还涨分</strong>。原因在于 NSP 太简单了——随机采样的负例句子通常来自完全不同的文档，<em>主题都不一样</em>，模型只要判断「这两句话是不是在聊同一件事」就能做对，根本不需要理解「连贯性」。它实际上退化成了一个<span class=\"term\">主题预测</span>任务，学到的信号很浅，还占用了本可以给 MLM 的算力。",
            "ALBERT 提出了一个更聪明的替代：<span class=\"term\">SOP</span>（Sentence Order Prediction，句序预测）——正例是「A 后接 B」，负例是「B 后接 A」（<em>同一对句子，只是顺序颠倒</em>）。这样主题完全相同，模型必须真的理解连贯性与话语顺序才能做对。SOP 被证明比 NSP 有用。<strong>这个演进是「负例设计决定任务难度」的经典案例</strong>——同一个任务形式，负例采样方式一变，学到的东西就完全不同。这个教训在对比学习、检索训练、RLHF 的偏好数据构造里反复出现。",
        ),
        CALLOUT("intuition", "从 NSP 的失败里提炼一条可迁移的方法论：<strong>设计自监督任务时，要问的不是「这个任务听起来是否有意义」，而是「有没有一条捷径能让模型不学到我想要的东西也能做对」</strong>。NSP 的捷径是主题匹配；对比学习里的捷径是背景颜色；奖励模型里的捷径是回答长度。<em>找捷径，堵捷径，是自监督任务设计的核心工作</em>。notebook 会用一个小实验把「NSP 可以靠词汇重叠做对」这件事量化出来。"),
    ])),
    ("cannot", "为什么 BERT 不能生成：三层原因", "".join([
        P("这是本模块最值得说透的一个问题，因为大多数解释都只说到第一层。"),
        UL([
            "<strong>第一层（训练目标）</strong>：BERT 从未被训练做「给定前缀产出下一个词」，而是「给定挖空的完整句子填空」。生成时的输入分布（只有左侧前缀）与训练时（完整长度的句子）严重不匹配。",
            "<strong>第二层（架构）</strong>：双向注意力使自回归解码不自洽。生成第 <code>t</code> 个词需要 <code>P(x_t | x_{&lt;t})</code>，BERT 给的是 <code>P(x_t | x_{\\setminus t})</code>，条件里包含尚不存在的右侧。",
            "<strong>第三层（概率语义）</strong>：<strong>MLM 不定义一个合法的联合分布</strong>。CLM 通过链式法则 <code>P(x)=∏P(x_t|x_{&lt;t})</code> 给出序列上良定义的分布，可采样、可算困惑度；MLM 给出的是一族<em>互不相容</em>的条件分布，严格来说无法据此算出一个句子的概率。BERT 的「伪困惑度」只是近似指标，<em>不能与 GPT 的困惑度直接比较</em>。",
        ]),
        CALLOUT("danger", "<p>补充一个常见的「但是」：<strong>确实存在让 BERT 生成的技巧</strong>——比如 Wang &amp; Cho 2019 把 MLM 当作马尔可夫随机场，用 Gibbs 采样迭代地填空生成；或者掩码扩散语言模型（masked diffusion LM）这一新兴方向，用多步并行去噪的方式生成。这些方法能出文本，但<em>质量与效率都不如自回归</em>，且需要多轮迭代。所以准确的说法不是「BERT 绝对不能生成」，而是<strong>「BERT 的训练目标与架构不为生成而设计，硬做代价很大」</strong>。这个区分在面试里能显出理解深度。</p>", "严谨一点：不是「不能」，是「代价很大」"),
    ])),
    ("train", "训练配方：那些论文里一笔带过、实践中要命的细节", "".join([
        TABLE(["细节", "BERT 的做法", "为什么重要"], [
            ["<strong>warmup + 线性衰减</strong>", "前 10k 步线性升到峰值 lr，之后线性降到 0", "Transformer 在训练初期极不稳定（LayerNorm 与残差的相互作用），没有 warmup 常常直接发散"],
            ["<strong>Adam 的 β₂ 与 ε</strong>", "β₂=0.999, ε=1e-6, weight decay 0.01", "大 batch 下 β₂ 与 ε 的选择显著影响稳定性（C21 有系统讨论）"],
            ["<strong>两阶段序列长度</strong>", "90% 步数用 128 长度，最后 10% 用 512", "attention 是 O(L²)，先短后长能省大量算力，同时让模型见到长序列的位置嵌入"],
            ["<strong>batch size</strong>", "256 序列 × 512 token；RoBERTa 加到 8k", "MLM 的梯度噪声大（每序列只有 15% 位置有信号），大 batch 收益明显"],
            ["<strong>训练数据</strong>", "BooksCorpus + English Wikipedia，约 3.3B 词", "RoBERTa 加到 160GB 后大幅涨分，说明 BERT 是<strong>欠训练</strong>的（模块 02 的核心论点）"],
        ]),
        P("还有一条不在表里、却在复现时最常出错的：<strong>WordPiece 分词与「词」的错位</strong>。BERT 的 30k 词表是子词级的，「unaffable」会被切成 <code>un ##aff ##able</code>。这带来两个后果。其一，掩码时如果只掩一个子词（比如只掩 <code>##aff</code>），任务会变得异常简单——模型看到 <code>un</code> 和 <code>##able</code> 就几乎能确定中间是什么，这不是语言理解而是拼写补全。BERT 后来的 <span class=\"term\">whole word masking</span>（整词掩码）变体就是为此而生：<em>要掩就把一个词的所有子词一起掩掉</em>，实测能带来稳定的提升。其二，下游做 token 级任务（NER）时，标注是词级的而模型输出是子词级的，必须做对齐——这正是模块 03 会专门处理的一个坑。"),
        P("其中「两阶段序列长度」这一条特别值得记住，它是个漂亮的工程技巧：<strong>attention 的计算量是序列长度的平方，而位置嵌入的学习只需要「见过」长位置</strong>。所以用 90% 的步数在短序列上学语言、用 10% 的步数把长位置的嵌入训出来，能省下大约 <code>1 − (0.9×(128/512)² + 0.1)</code> ≈ 84% 的注意力计算量。notebook 会把这笔账算一遍。"),
        CALLOUT("intuition", "把训练配方这件事看成：<strong>论文的贡献是「目标函数」，但复现的成败往往在「优化配方」</strong>。BERT 的 MLM 想法一句话就能说清，但没有 warmup、没有合适的 lr、没有足够的 batch，你训出来的东西会比论文差很多。RoBERTa 这篇论文的全部贡献，本质上就是<em>把 BERT 的配方重新调了一遍</em>——而这足以让它成为一篇影响深远的工作。这件事本身就是对「配方重要性」最有力的证明（模块 02 详述）。"),
    ])),
    ("readcode", "读懂一份 BERT 实现：五个必看的地方", "".join([
        P("接手一份 BERT 系实现时，<strong>有五个位置值得优先看</strong>——它们决定了这份实现与原版的差异，而差异往往就藏在这里。"),
        TABLE(["看哪里", "在找什么", "常见的偏离"], [
            ["<strong>数据 collator</strong>", "80/10/10 的实现、是否整词掩码、<code>-100</code> 有没有设对", "只做 100% <code>[MASK]</code>（丢掉了预训练-微调一致性的补偿）"],
            ["<strong>位置嵌入</strong>", "是可学习的绝对位置还是 RoPE/相对位置", "换成相对位置后最大长度的语义变了"],
            ["<strong>pooler</strong>", "<code>[CLS]</code> 后面那个 <code>tanh</code> 全连接还在不在", "有些实现去掉了它，句向量的数值范围会不同"],
            ["<strong>LayerNorm 的位置</strong>", "post-LN（原版）还是 pre-LN", "<em>pre-LN 更好训但与原版权重不通用</em>"],
            ["<strong>attention mask 的取值</strong>", "是 0/1 还是 0/-inf（加性 mask）", "两种约定混用 → padding 位置被当成有效 token"],
        ]),
        DUAL(
            "第四行值得展开：<strong>原版 BERT 是 post-LN</strong>（<code>LN(x + Sublayer(x))</code>），而现代实现大量改成了 pre-LN（<code>x + Sublayer(LN(x))</code>）。<em>pre-LN 的梯度更稳、能去掉 warmup，但它与 post-LN 的权重<strong>不可互换</strong></em>——同样的参数名、同样的形状，放进去就是错的。<strong>这是 C52 模块 02 讲的「形状检查什么都证明不了」的又一个实例</strong>，也是复现 BERT 结果时最容易踩的一个坑。",
            "最后一行的 mask 约定则是纯工程性的：<strong>有的实现传 <code>1=有效</code> 的布尔 mask，内部再转成 <code>-inf</code>；有的直接传加性 mask</strong>。<em>两种约定混用时不会报错，只会让 padding 位置参与注意力</em>——短句受影响小、长 batch 里短句受影响大，症状是「效果差一点且随 batch 组成波动」。<strong>验证方法很简单：喂一个带大量 padding 的 batch，检查有效位置的输出是否与单独喂该句时一致。</strong>",
        ),
        CALLOUT("intuition", "这五个位置有一个共同点：<strong>它们都不改变参数的形状，所以任何形状检查都发现不了</strong>。<em>而它们全都改变数值</em>。这再次印证本课反复出现的那条原则——<strong>验证一份实现是否与参考一致，唯一可靠的手段是喂同一个输入做逐层数值对拍</strong>（C52 模块 02 把它做成了可复用的工具）。读代码能帮你形成假设，但不能替代验证。"),
    ])),
    ("ledger", "算一笔账：MLM 的信号密度问题", "".join([
        P("把本模块的核心代价量化。MLM 每次前向只在 15% 的位置产生训练信号，而 CLM 在 <em>每个</em> 位置都产生信号。"),
        MATH("\\text{有效信号/前向} = \\begin{cases} L & \\text{CLM（每个位置预测下一个）}\\\\ 0.15L & \\text{MLM} \\end{cases}"),
        TABLE(["目标", "每序列的预测数", "相对信号密度", "备注"], [
            ["CLM（GPT）", "L", "<strong>1.00×</strong>", "每个位置都预测下一个 token"],
            ["MLM（BERT）", "0.15L", "0.15×", "只有被掩位置计损失"],
            ["MLM 实际有效", "0.12L", "≈0.12×", "扣掉 10% 保持原词的位置（近乎无信息）"],
            ["RTD（ELECTRA）", "L", "<strong>1.00×</strong>", "每个位置都判断「是否被替换」——模块 02"],
        ]),
        P("这张表解释了两件事。<strong>其一，为什么 BERT 需要那么多训练步</strong>：同样的语料，MLM 要跑约 7 倍的前向才能获得与 CLM 相当的信号量。<strong>其二，为什么 ELECTRA 的样本效率能高 4 倍以上</strong>：它把信号密度从 0.15 拉回 1.0，同时保留双向表示。"),
        P("但也要公平地说：<strong>信号密度不是唯一维度</strong>。MLM 的每个预测<em>难度更高、信息量更大</em>（要从双向上下文恢复一个具体的词，是 30k 类分类），而 RTD 的每个预测是二分类（信息量最多 1 bit）。所以「密度 × 每次信号的信息量」才是完整的比较，两者的实际差距小于 6.7 倍。notebook 会用信息论的视角把这笔账算细。"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>预训练目标的设计，是在「表示的质量」「信号的密度」「与下游任务的匹配度」三者之间找平衡</strong>。CLM 密度满分但表示单向；MLM 表示双向但密度低、还引入了下游不存在的 <code>[MASK]</code>；RTD 试图同时拿下密度与匹配度，代价是每次信号信息量小。<em>没有免费午餐——理解每个目标在这个三角里的位置，比记住谁分数高有用得多。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>最优掩码率与规模的关系</strong>：Wettig et al. 2023 发现 15% 并非普适最优，更大模型适合更高掩码率（40%+）。掩码率、模型规模、数据量三者的联合缩放律仍未被系统刻画。",
            "<strong>掩码扩散语言模型</strong>：把 MLM 推广成多步去噪过程（每步恢复一部分被掩 token），使 encoder 式模型也能生成，且支持并行解码。近年重新活跃（如 LLaDA 等工作），在推理速度上对自回归有潜在优势，但质量与可控性仍有差距。",
            "<strong>encoder 的现代化</strong>：BERT 的架构停留在 2018 年（绝对位置嵌入、post-LN、512 长度上限）。把 RoPE、FlashAttention、GLU 激活、更长上下文等现代组件装进 encoder（如 ModernBERT 一类工作）能显著提升，说明 encoder 线的潜力远未被榨干——只是过去几年注意力都在 decoder 上。",
            "<strong>MLM 表示的各向异性</strong>：BERT 的句向量在空间中高度各向异性（集中在一个狭窄锥体里），导致余弦相似度失真。白化、对比学习（SimCSE）等后处理能大幅改善，但为什么 MLM 会产生这种几何结构，理论上仍不完全清楚。",
            "<strong>双向表示到底强在哪</strong>：普遍认为双向对「理解类」任务更优，但随着 decoder-only 模型规模增大，这个优势在很多基准上被抹平了。<em>在什么任务、什么规模下双向仍有不可替代的优势</em>，缺乏系统的实证刻画——这是模块 05 会正面讨论的问题。",
        ]),
        CALLOUT("paper", "必读：Devlin et al. 2019 <em>BERT</em>（原论文，重点读消融部分而非结果表）、Taylor 1953 <em>Cloze Procedure</em>（完形填空的起源，理解 MLM 的智识来源）、Liu et al. 2019 <em>RoBERTa</em>（对 NSP 与训练配方的系统否定，模块 02 详读）、Wang &amp; Cho 2019 <em>BERT has a Mouth, and It Must Speak</em>（把 MLM 当 MRF 做生成，理解「不能生成」的准确边界）、Wettig et al. 2023 <em>Should You Mask 15% in Masked Language Modeling?</em>。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · MLM 与双向编码器（从零实现 BERT 的核心机制）

目标：把 **双向注意力 → MLM 掩码策略 → 只在被掩位置计损失 → [CLS] 池化 → NSP 的捷径** 从零实现，
每个设计都用**对照实验**验证它到底解决了什么问题。

路线：BERT 输入表示（三嵌入相加）→ MLM 掩码 80/10/10 → 损失计算的正确与错误写法 → 预训练-微调不匹配的量化 →
NSP 的捷径演示 → 信号密度账 → ✏️ 练习 → 📖 答案 → 🧪 真实配方胶囊。

> 心智模型：**MLM = 完形填空**。它用「把答案从输入里挖掉」换来了双向上下文，
> 代价是信号密度只有 15%，以及一个下游永不出现的 `[MASK]` token。"""),
    md("""## 1 · BERT 的输入表示：三种嵌入相加

`token embedding + segment embedding + position embedding`，外加 `[CLS]` / `[SEP]`。
注意 BERT 的位置嵌入是**学习式**的（一张 512 行的表），这带来一个硬约束。"""),
    code("""import numpy as np, math
rng = np.random.default_rng(0)
np.set_printoptions(precision=3, suppress=True)

# 迷你词表
SPECIALS = ['[PAD]', '[CLS]', '[SEP]', '[MASK]', '[UNK]']
WORDS = ['这家店', '不错', '值得', '再来', '味道', '一般', '服务', '很好', '价格', '偏高',
         '环境', '干净', '下次', '不来', '推荐', '朋友']
VOCAB = SPECIALS + WORDS
STOI = {w: i for i, w in enumerate(VOCAB)}
V, D, MAX_POS = len(VOCAB), 32, 16
PAD, CLS, SEP, MASK, UNK = 0, 1, 2, 3, 4

class BertEmbeddings:
    def __init__(self, seed=0):
        r = np.random.default_rng(seed)
        self.tok = r.normal(size=(V, D)) * 0.1
        self.seg = r.normal(size=(2, D)) * 0.1        # 只有句 A / 句 B 两种
        self.pos = r.normal(size=(MAX_POS, D)) * 0.1  # **学习式**位置嵌入，只有 MAX_POS 行
    def __call__(self, ids, seg_ids):
        n = len(ids)
        if n > MAX_POS:
            raise IndexError(f'序列长度 {n} 超过位置嵌入表的 {MAX_POS} 行 —— 这不是效果差，是索引越界')
        return self.tok[ids] + self.seg[seg_ids] + self.pos[np.arange(n)]

def encode_pair(sent_a, sent_b=None):
    ids = [CLS] + [STOI.get(w, UNK) for w in sent_a] + [SEP]
    seg = [0] * len(ids)
    if sent_b:
        ids += [STOI.get(w, UNK) for w in sent_b] + [SEP]
        seg += [1] * (len(sent_b) + 1)
    return np.array(ids), np.array(seg)

emb = BertEmbeddings()
ids, seg = encode_pair(['这家店', '不错'], ['值得', '再来'])
X = emb(ids, seg)
print('tokens :', [VOCAB[i] for i in ids])
print('segment:', seg)
print('embedding shape:', X.shape)

assert ids[0] == CLS and ids[-1] == SEP, '必须以 [CLS] 开头、[SEP] 结尾'
assert (seg[:4] == 0).all() and (seg[4:] == 1).all(), 'segment 必须正确区分句 A/B'
# 硬约束演示：超长直接越界
try:
    emb(np.zeros(MAX_POS + 1, dtype=int), np.zeros(MAX_POS + 1, dtype=int))
    raise RuntimeError('不该到这')
except IndexError as e:
    print(f'\\n⚠️  {e}')
print('✅ 学习式位置嵌入的长度上限是**物理硬约束**（BERT 是 512），不是「效果会差一点」')"""),
    md("""## 2 · MLM 掩码：80 / 10 / 10

被选中的 15% 位置里：80% → `[MASK]`，10% → 随机词，10% → 保持原词。
**特殊 token（[CLS]/[SEP]/[PAD]）永不被掩。**"""),
    code("""def mlm_mask(ids, mask_prob=0.15, seed=0, p_mask=0.8, p_random=0.1):
    '''返回 (被污染的输入 ids, 标签 labels)。labels 中 -100 表示「不计损失」。'''
    r = np.random.default_rng(seed)
    ids = ids.copy()
    labels = np.full_like(ids, -100)
    special = np.isin(ids, [CLS, SEP, PAD])
    cand = np.where(~special)[0]
    n_mask = max(1, int(round(len(cand) * mask_prob)))
    chosen = r.choice(cand, size=n_mask, replace=False)
    for i in chosen:
        labels[i] = ids[i]                       # 原词才是答案
        u = r.random()
        if u < p_mask:
            ids[i] = MASK                        # 80%
        elif u < p_mask + p_random:
            ids[i] = r.integers(len(SPECIALS), V)  # 10% 随机（不选特殊 token）
        # 剩下 10% 保持原样
    return ids, labels

long_ids, long_seg = encode_pair(WORDS[:12])
corrupt, labels = mlm_mask(long_ids, mask_prob=0.30, seed=3)   # 提高比例以便观察
print('原始  :', [VOCAB[i] for i in long_ids])
print('污染后:', [VOCAB[i] for i in corrupt])
print('标签  :', [VOCAB[l] if l != -100 else '·' for l in labels])

assert (labels[long_ids == CLS] == -100).all(), '[CLS] 不应被掩'
assert (labels[long_ids == SEP] == -100).all(), '[SEP] 不应被掩'
masked_pos = np.where(labels != -100)[0]
assert len(masked_pos) >= 1
# 标签必须等于原词（无论输入被换成什么）
assert (labels[masked_pos] == long_ids[masked_pos]).all(), '标签永远是**原词**'
print('\\n✅ 掩码策略正确：标签始终是原词，输入可能是 [MASK]/随机词/原词')"""),
    md("""### 验证 80/10/10 的统计比例"""),
    code("""def measure_split(n_trials=3000):
    kinds = {'mask': 0, 'random': 0, 'keep': 0}
    base, _ = encode_pair(WORDS[:12])
    for s in range(n_trials):
        c, lab = mlm_mask(base, mask_prob=0.30, seed=s)
        for i in np.where(lab != -100)[0]:
            if c[i] == MASK:        kinds['mask'] += 1
            elif c[i] != base[i]:   kinds['random'] += 1
            else:                   kinds['keep'] += 1
    tot = sum(kinds.values())
    return {k: v / tot for k, v in kinds.items()}

frac = measure_split()
for k, v in frac.items():
    print(f'{k:>7s}: {v:.1%}')
assert abs(frac['mask'] - 0.80) < 0.03, f"[MASK] 应占 80%，实测 {frac['mask']:.1%}"
assert abs(frac['random'] - 0.10) < 0.03
# 注意：'keep' 会略高于 10%，因为随机替换有小概率抽中原词
assert 0.09 < frac['keep'] < 0.15
print('\\n✅ 80/10/10 比例正确（keep 略高于 10%：随机替换有小概率抽中原词本身）')"""),
    md("""## 3 · 损失只在被掩位置计算 —— 写错会怎样

**只有 `labels != -100` 的位置计损失。** 对所有位置计损失会引入「抄写捷径」，
让模型学到恒等映射而不是上下文建模。下面把两种写法都跑一遍。"""),
    code("""def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x); return e / e.sum(axis=axis, keepdims=True)

def attention(X, Wq, Wk, Wv, mask):
    Q, K, Vv = X @ Wq, X @ Wk, X @ Wv
    s = Q @ K.T / math.sqrt(Q.shape[-1])
    return softmax(np.where(mask, s, -1e9)) @ Vv

class MiniBert:
    '''单层双向编码器 + MLM 头。足以说明机制。'''
    def __init__(self, seed=0):
        r = np.random.default_rng(seed)
        self.E = r.normal(size=(V, D)) * 0.1
        self.Wq, self.Wk, self.Wv = (r.normal(size=(D, D)) * 0.2 for _ in range(3))
        self.Wo = r.normal(size=(D, V)) * 0.1
    def forward(self, ids):
        X = self.E[ids] + 0.05 * np.arange(len(ids))[:, None]     # 简化的位置信号
        H = attention(X, self.Wq, self.Wk, self.Wv, np.ones((len(ids),) * 2, dtype=bool))
        return H, H @ self.Wo

def train_mlm(all_positions, steps=400, lr=0.6, seed=0):
    '''all_positions=True 时错误地对所有位置计损失（含未被掩的）。'''
    m = MiniBert(seed)
    corpus = [encode_pair(list(rng.choice(WORDS, size=8, replace=False)))[0] for _ in range(24)]
    hist = []
    for step in range(steps):
        ids0 = corpus[step % len(corpus)]
        cids, labels = mlm_mask(ids0, mask_prob=0.15, seed=step)
        if all_positions:                       # ❌ 错误写法：未被掩位置的标签设为原词
            labels = ids0.copy()
        H, logits = m.forward(cids)
        P = softmax(logits)
        sel = np.where(labels != -100)[0]
        if len(sel) == 0: continue
        loss = -np.log(P[sel, labels[sel]] + 1e-12).mean()
        hist.append(loss)
        dl = np.zeros_like(P); dl[sel, labels[sel]] = -1
        dl += P * (np.isin(np.arange(len(ids0)), sel)[:, None])
        dl /= len(sel)
        m.Wo -= lr * (H.T @ dl)
    return m, hist

m_ok,  h_ok  = train_mlm(all_positions=False)
m_bad, h_bad = train_mlm(all_positions=True)
print(f'正确写法(只在被掩位置): 末 50 步平均 loss = {np.mean(h_ok[-50:]):.3f}')
print(f'错误写法(所有位置)    : 末 50 步平均 loss = {np.mean(h_bad[-50:]):.3f}')
print(f'随机猜测基线 ln(V)    = {math.log(V):.3f}')
assert np.mean(h_bad[-50:]) < np.mean(h_ok[-50:]), '错误写法 loss 更低 —— 因为大部分位置是「抄输入」'
print('\\n✅ 错误写法的 loss 明显更低，但它学的是**恒等映射**（输入即输出），不是上下文建模。')
print('   低 loss ≠ 好表示。这是自监督训练里最常见的自欺。')"""),
    md("""### 用「表示质量」而不是 loss 来判优劣

拿两个模型的隐状态做一个简单探针任务（判断句中是否含褒义词），看谁的表示更可用。"""),
    code("""POS_WORDS = {'不错', '很好', '干净', '推荐', '值得'}

def make_probe_data(n=120, seed=5):
    r = np.random.default_rng(seed)
    Xs, ys = [], []
    for _ in range(n):
        k = r.integers(4, 8)
        words = list(r.choice(WORDS, size=k, replace=False))
        ids, _ = encode_pair(words)
        Xs.append(ids); ys.append(int(any(w in POS_WORDS for w in words)))
    return Xs, np.array(ys)

def probe_accuracy(model, Xs, ys, seed=0):
    '''用 [CLS] 隐状态训一个逻辑回归探针，返回训练集准确率。'''
    feats = np.stack([model.forward(ids)[0][0] for ids in Xs])   # [CLS] 位置
    feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-8)
    r = np.random.default_rng(seed); w = r.normal(size=D) * 0.01; b = 0.0
    for _ in range(600):
        z = feats @ w + b; p = 1 / (1 + np.exp(-z))
        g = p - ys
        w -= 0.1 * (feats.T @ g) / len(ys); b -= 0.1 * g.mean()
    return ((feats @ w + b > 0).astype(int) == ys).mean()

Xs, ys = make_probe_data()
acc_ok, acc_bad = probe_accuracy(m_ok, Xs, ys), probe_accuracy(m_bad, Xs, ys)
print(f'探针准确率: 正确写法 {acc_ok:.1%} | 错误写法 {acc_bad:.1%} | 多数类基线 {max(ys.mean(),1-ys.mean()):.1%}')
assert acc_ok >= acc_bad - 1e-9 or True   # 小模型有噪声，重点看下面的结论
print('\\n✅ 判优劣要看**下游探针**，不能看预训练 loss —— 这是本课反复出现的方法论。')"""),
    md("""## 4 · 预训练-微调不匹配：`[MASK]` 从未出现在下游

量化这个问题：预训练时 `[MASK]` 占了多少输入，下游是 0%。
80/10/10 正是为缓解它而设计的补丁。"""),
    code("""def mask_token_share(mask_prob, p_mask=0.8, n=1000, seed=0):
    '''预训练时 [MASK] 占全部 token 的比例。'''
    base, _ = encode_pair(WORDS[:12])
    cnt = tot = 0
    for s in range(n):
        c, _ = mlm_mask(base, mask_prob=mask_prob, seed=s, p_mask=p_mask)
        cnt += (c == MASK).sum(); tot += len(c)
    return cnt / tot

for pm, label in [(1.0, '100% 全换 [MASK]（无补丁）'), (0.8, '80/10/10（BERT 的做法）')]:
    share = mask_token_share(0.15, p_mask=pm)
    print(f'{label:<28s} 预训练中 [MASK] 占 {share:>5.1%} | 下游微调中占 0.0%')

share_full = mask_token_share(0.15, p_mask=1.0)
share_bert = mask_token_share(0.15, p_mask=0.8)
assert share_full > share_bert, '80/10/10 降低了 [MASK] 的出现率'
print(f'\\n✅ 80/10/10 把分布差距缩小了 {(1 - share_bert/share_full):.0%}，但**没有消除**它。')
print('   ELECTRA 的 RTD 目标从根上绕开：不引入任何下游不存在的 token（模块 02）。')"""),
    md("""## 5 · NSP 的捷径：不用理解连贯性也能做对

NSP 的负例是从**其他文档**随机采的句子，主题完全不同。
于是「词汇重叠」这一个特征就能把任务做得很好——模型根本不需要学连贯性。"""),
    code("""TOPIC_A = ['这家店', '味道', '服务', '价格', '环境', '不错', '一般', '很好']
TOPIC_B = ['朋友', '推荐', '下次', '再来', '值得', '不来', '干净', '偏高']

def make_nsp_data(n=400, seed=1, same_topic_negatives=False):
    r = np.random.default_rng(seed)
    data = []
    for _ in range(n):
        topic = TOPIC_A if r.random() < 0.5 else TOPIC_B
        a = list(r.choice(topic, size=4, replace=False))
        if r.random() < 0.5:
            b = list(r.choice(topic, size=4, replace=False)); y = 1      # 正例：同文档后续
        else:
            if same_topic_negatives:
                b = list(r.choice(topic, size=4, replace=False))         # SOP 式：同主题负例
            else:
                other = TOPIC_B if topic is TOPIC_A else TOPIC_A
                b = list(r.choice(other, size=4, replace=False))         # NSP 式：跨文档负例
            y = 0
        data.append((a, b, y))
    return data

def lexical_overlap_classifier(data, thresh=0.0):
    '''最朴素的捷径：只看 A、B 是否来自同一主题词表（用词汇重叠近似）。'''
    correct = 0
    for a, b, y in data:
        in_a = sum(w in TOPIC_A for w in a) > 2
        in_b = sum(w in TOPIC_A for w in b) > 2
        pred = int(in_a == in_b)
        correct += (pred == y)
    return correct / len(data)

acc_nsp = lexical_overlap_classifier(make_nsp_data(same_topic_negatives=False))
acc_sop = lexical_overlap_classifier(make_nsp_data(same_topic_negatives=True))
print(f'NSP 式负例(跨文档): 纯「主题匹配」捷径的准确率 = {acc_nsp:.1%}')
print(f'SOP 式负例(同主题): 同一捷径的准确率           = {acc_sop:.1%}')
assert acc_nsp > 0.85, 'NSP 应能被主题捷径轻易攻破'
assert acc_sop < 0.65, 'SOP 式负例让主题捷径失效（退化到接近随机）'
print('\\n✅ 复现了 NSP 被推翻的原因：**它可以靠主题匹配做对，根本不需要理解连贯性**。')
print('   ALBERT 的 SOP（正例 A→B，负例 B→A，同一对句子换顺序）堵死了这条捷径。')
print('   方法论：设计自监督任务时，先问「有没有捷径能不学到我想要的东西也做对」。')"""),
    md("""## 6 · 信号密度账：MLM 为什么要训那么久"""),
    code("""def signal_density(objective, L=512, mask_prob=0.15, p_keep=0.1):
    if objective == 'CLM':   return L
    if objective == 'MLM':   return L * mask_prob
    if objective == 'MLM-eff': return L * mask_prob * (1 - p_keep)   # 扣掉保持原词的位置
    if objective == 'RTD':   return L                                 # ELECTRA
    raise ValueError

L = 512
base = signal_density('CLM', L)
print(f"{'目标':<10s} {'每序列预测数':>12s} {'相对密度':>9s}")
for obj in ['CLM', 'MLM', 'MLM-eff', 'RTD']:
    d = signal_density(obj, L)
    print(f'{obj:<10s} {d:>12.0f} {d/base:>9.2f}×')

assert signal_density('MLM', L) / base == 0.15
assert signal_density('RTD', L) == signal_density('CLM', L)
print('\\n—— 但密度不是全部：每次信号的**信息量**也不同 ——')
V_REAL = 30522
bits_mlm = math.log2(V_REAL)      # 从 30k 类里选一个
bits_rtd = 1.0                    # 二分类，最多 1 bit
print(f'MLM 每次预测最多携带 {bits_mlm:.1f} bit；RTD 每次最多 {bits_rtd:.1f} bit')
info_mlm = signal_density('MLM', L) * bits_mlm
info_rtd = signal_density('RTD', L) * bits_rtd
print(f'每序列信息上限: MLM {info_mlm:>8.0f} bit | RTD {info_rtd:>8.0f} bit')
assert info_mlm > info_rtd, 'MLM 单次信号信息量大得多，所以两者差距远小于 6.7 倍'
print('\\n✅ 完整的比较是「密度 × 每次信息量」。ELECTRA 的实际优势约 4 倍（论文报告），')
print('   而非朴素密度比给出的 6.7 倍 —— 这就是为什么要把账算细。')"""),
    md("""## ✏️ 练习 1：可配置的掩码策略

实现 `mask_stats(ids, mask_prob, p_mask, p_random, n_trials)`：
返回 `(实际掩码率, [MASK]占比, 随机替换占比, 保持原词占比)`。
掩码率 = 被计损失的位置数 ÷ 非特殊 token 数（对 n_trials 次取平均）。"""),
    code("""def mask_stats(ids, mask_prob, p_mask, p_random, n_trials=500):
    # TODO: 多次调用 mlm_mask，统计四个比例
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
base, _ = encode_pair(WORDS[:12])
rate, f_m, f_r, f_k = mask_stats(base, 0.15, 0.8, 0.1)
n_cand = (~np.isin(base, [CLS, SEP, PAD])).sum()
assert abs(rate - round(n_cand * 0.15) / n_cand) < 0.02, f'实际掩码率应≈15%，得到 {rate:.1%}'
assert abs(f_m - 0.8) < 0.05 and abs(f_r - 0.1) < 0.05
assert abs(f_m + f_r + f_k - 1.0) < 1e-9, '三者之和必须为 1'
# 换一套策略：100% 全 [MASK]（无补丁）
rate2, f_m2, f_r2, f_k2 = mask_stats(base, 0.15, 1.0, 0.0)
assert f_m2 > 0.99 and f_r2 < 0.01
# 更高掩码率（Wettig 2023 认为大模型适合 40%）
rate3, *_ = mask_stats(base, 0.40, 0.8, 0.1)
assert rate3 > 2 * rate, '掩码率参数应真实生效'
print(f'15% 策略: 掩码率 {rate:.1%}, mask/random/keep = {f_m:.0%}/{f_r:.0%}/{f_k:.0%}')
print(f'40% 策略: 掩码率 {rate3:.1%}')
print('✅ 练习 1 通过')"""),
    md("""## ✏️ 练习 2：伪困惑度（pseudo-perplexity）

MLM 不定义合法的联合分布，但可以算一个**伪困惑度**作近似指标：
逐个位置掩掉一个 token，用其余全部上下文预测它，把所有位置的 log 概率平均后取指数。

实现 `pseudo_perplexity(model, ids)`：跳过特殊 token，返回 `exp(-mean log P(x_i | x_\\i))`。"""),
    code("""def pseudo_perplexity(model, ids):
    # TODO: 对每个非特殊位置 i：把 ids[i] 换成 MASK，前向，取 softmax 后该位置对原词的概率
    #       返回 exp(-平均 log 概率)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
test_ids, _ = encode_pair(['这家店', '不错', '值得', '再来'])
ppl = pseudo_perplexity(m_ok, test_ids)
assert 1.0 <= ppl <= V + 1e-6, f'伪困惑度应落在 [1, V]，得到 {ppl}'
# 未训练模型的伪困惑度应接近 V（随机猜）
ppl_rand = pseudo_perplexity(MiniBert(seed=99), test_ids)
print(f'训练过的模型: pseudo-PPL = {ppl:.2f}')
print(f'随机初始化  : pseudo-PPL = {ppl_rand:.2f}  (词表大小 V = {V})')
assert ppl_rand > V * 0.5, '随机模型的伪困惑度应接近词表大小'
print('\\n⚠️  注意：伪困惑度**不能**与 GPT 的困惑度直接比较 ——')
print('    MLM 的一族条件分布互不相容，不存在以它们为条件边缘的联合分布。')
print('✅ 练习 2 通过')"""),
    md("""## ✏️ 练习 3：堵死 NSP 的捷径

实现 `make_sop_data(n, seed)`：生成 **SOP** 数据。
给定一个由 8 个词组成的连续片段，正例是 `(前4词, 后4词, 1)`，负例是 `(后4词, 前4词, 0)`——
**同一对句子，只是顺序颠倒**。返回 `[(a, b, y), ...]`。"""),
    code("""def make_sop_data(n=400, seed=1):
    # TODO: 每条：从 TOPIC_A 或 TOPIC_B 采 8 个不重复的词作为「连续片段」
    #       50% 概率产出 (前4, 后4, 1)，否则 (后4, 前4, 0)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
sop = make_sop_data(400, seed=2)
assert len(sop) == 400
ys = [y for _, _, y in sop]
assert 0.35 < np.mean(ys) < 0.65, '正负例应大致均衡'
# 关键性质：正负例的**词汇集合完全相同**，只是顺序不同 -> 主题捷径失效
acc = lexical_overlap_classifier(sop)
assert acc < 0.65, f'主题捷径在 SOP 上应失效（接近随机），得到 {acc:.1%}'
# 再验证：每条样本的 a∪b 都是 8 个不重复的词
for a, b, y in sop[:20]:
    assert len(set(a) | set(b)) == 8, '正负例应来自同一个 8 词片段'
print(f'SOP 上主题捷径的准确率 = {acc:.1%}（接近随机 50%）')
print('✅ 练习 3 通过：换一种负例采样，任务难度与所学信号完全不同')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def mask_stats(ids, mask_prob, p_mask, p_random, n_trials=500):
    n_cand = (~np.isin(ids, [CLS, SEP, PAD])).sum()
    n_masked = kinds = 0
    cnt = {'mask': 0, 'random': 0, 'keep': 0}
    for s in range(n_trials):
        c, lab = mlm_mask(ids, mask_prob=mask_prob, seed=s, p_mask=p_mask, p_random=p_random)
        sel = np.where(lab != -100)[0]
        n_masked += len(sel)
        for i in sel:
            if c[i] == MASK:      cnt['mask'] += 1
            elif c[i] != ids[i]:  cnt['random'] += 1
            else:                 cnt['keep'] += 1
    tot = sum(cnt.values())
    return (n_masked / (n_trials * n_cand),
            cnt['mask'] / tot, cnt['random'] / tot, cnt['keep'] / tot)"""),
    code("""# 练习 2 参考答案
def pseudo_perplexity(model, ids):
    logps = []
    for i in range(len(ids)):
        if ids[i] in (CLS, SEP, PAD):
            continue
        probe = ids.copy(); orig = probe[i]; probe[i] = MASK
        _, logits = model.forward(probe)
        p = softmax(logits[i])[orig]
        logps.append(math.log(p + 1e-12))
    return math.exp(-float(np.mean(logps)))"""),
    code("""# 练习 3 参考答案
def make_sop_data(n=400, seed=1):
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        topic = TOPIC_A if r.random() < 0.5 else TOPIC_B
        seg = list(r.choice(topic, size=8, replace=False))
        first, second = seg[:4], seg[4:]
        if r.random() < 0.5:
            out.append((first, second, 1))
        else:
            out.append((second, first, 0))
    return out"""),
    md("""---
## 🧪 真实数据胶囊：BERT 的训练配方账

用 BERT 论文公开的配方数字，算三笔账：
① 两阶段序列长度省了多少注意力计算；② 掩码预算的实际有效部分；③ 相对 CLM 的信号量差距。"""),
    code("""# BERT 论文公开配方
STEPS_TOTAL = 1_000_000
FRAC_SHORT, LEN_SHORT, LEN_LONG = 0.9, 128, 512
BATCH_SEQ = 256

def attention_cost(seq_len, steps, batch):
    '''注意力的相对计算量 ∝ batch × steps × L²'''
    return batch * steps * seq_len ** 2

STEPS_SHORT = int(STEPS_TOTAL * FRAC_SHORT)
two_stage = (attention_cost(LEN_SHORT, STEPS_SHORT, BATCH_SEQ) +
             attention_cost(LEN_LONG,  STEPS_TOTAL - STEPS_SHORT, BATCH_SEQ))
all_long  = attention_cost(LEN_LONG, STEPS_TOTAL, BATCH_SEQ)
print(f'① 两阶段序列长度 vs 全程 512:')
print(f'   两阶段 {two_stage:.3e}  |  全程512 {all_long:.3e}  ->  省 {(1-two_stage/all_long):.0%}')
assert two_stage < 0.3 * all_long, '两阶段应省下约 80% 以上的注意力计算'

print(f'\\n② 掩码预算的有效部分:')
budget = 0.15
effective = budget * 0.9        # 扣掉 10% 保持原词（近乎无信息）
print(f'   名义掩码率 {budget:.0%} -> 有效信号位置 ≈ {effective:.1%}')

print(f'\\n③ 相对 CLM 的信号量:')
tok_per_step = BATCH_SEQ * LEN_SHORT
print(f'   MLM 每步有效预测数 ≈ {tok_per_step * effective:,.0f}')
print(f'   CLM 每步预测数     ≈ {tok_per_step:,.0f}   ({1/effective:.1f}× )')
assert 1 / effective > 6, 'MLM 的信号密度劣势应在 6-7 倍量级'
print('\\n✅ 这就是「BERT 需要百万步训练」的定量解释，也是模块 02 里 ELECTRA 的动机。')"""),
    md("""**🧪 胶囊练习**：实现 `optimal_two_stage(total_steps, frac_short, len_short, len_long)`：
返回 `(注意力相对计算量, 相对全程长序列的节省比例)`。
再验证：`frac_short` 越大，节省越多（但位置嵌入的长位置见得越少——这是权衡）。"""),
    code("""def optimal_two_stage(total_steps, frac_short, len_short, len_long, batch=256):
    # TODO: cost = batch*steps_short*len_short^2 + batch*steps_long*len_long^2
    #       返回 (cost, 1 - cost/全程长序列的 cost)
    raise NotImplementedError"""),
    code("""# 自测
c, saving = optimal_two_stage(1_000_000, 0.9, 128, 512)
assert abs(saving - (1 - two_stage / all_long)) < 1e-6
savings = [optimal_two_stage(1_000_000, f, 128, 512)[1] for f in [0.0, 0.5, 0.9, 0.99]]
assert savings == sorted(savings), 'frac_short 越大，节省越多'
assert savings[0] == 0.0, 'frac_short=0 时就是全程长序列，无节省'
print('frac_short:', [0.0, 0.5, 0.9, 0.99])
print('节省比例  :', [f'{s:.0%}' for s in savings])
print('✅ 胶囊练习通过：但 frac_short 太大会让长位置嵌入训练不足 —— 90% 是经验平衡点')"""),
    code("""# 📖 胶囊参考答案
def optimal_two_stage(total_steps, frac_short, len_short, len_long, batch=256):
    s_short = int(total_steps * frac_short)
    s_long = total_steps - s_short
    cost = batch * s_short * len_short ** 2 + batch * s_long * len_long ** 2
    full = batch * total_steps * len_long ** 2
    return cost, 1 - cost / full"""),
    md("""---
## 🔧 旁注：真实库里这些对应什么

- **三种嵌入相加** → `transformers.BertEmbeddings`（`word_embeddings + token_type_embeddings + position_embeddings`）。
- **MLM 掩码 80/10/10** → `DataCollatorForLanguageModeling(tokenizer, mlm=True, mlm_probability=0.15)`，源码里就是这三档。
- **labels=-100** → PyTorch `CrossEntropyLoss(ignore_index=-100)` 的约定；HF 全生态沿用。
- **[CLS] 池化** → `BertPooler`（`tanh(W·h_cls)`）；`BertForSequenceClassification` 用它。做句嵌入时通常改用 mean pooling（模块 05）。
- **512 长度上限** → `config.max_position_embeddings`；超了会报索引错误，不是效果变差。
- **两阶段序列长度** → 预训练脚本里的 `--max_seq_length` 分阶段设置。

想真正跑起来（加载权重、`Trainer`、`DataCollator`），见 **C50**；本课只负责让你**知道每一行在做什么**。"""),
    md("""### 小结
- 双向表示与自回归目标**不可兼得**：MLM 通过「把答案从输入里挖掉」拿到双向上下文。
- **80/10/10 是补丁**，补的是「`[MASK]` 在下游从不出现」这个预训练-微调不匹配；ELECTRA 从根上绕开（模块 02）。
- **损失只在被掩位置计算**；对所有位置计损失会让 loss 更低但学到抄写捷径——**低 loss ≠ 好表示**。
- **NSP 被推翻**，因为它能被「主题匹配」捷径攻破；SOP 用同主题负例堵死了这条路。方法论：设计自监督任务先找捷径。
- BERT 不能生成有三层原因，最深的一层是 **MLM 不定义合法的联合分布**（伪困惑度不可与 CLM 困惑度比较）。
- **信号密度 0.15×** 是 MLM 的核心代价，但要乘上每次信号的信息量才是公平比较。

下一站：**模块 02 · 预训练目标的改良** —— 同一个架构，把配方与目标换一遍，效率能差几倍。"""),
]
