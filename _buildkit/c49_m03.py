# -*- coding: utf-8 -*-
"""C49 模块 03 · 下游微调三范式。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–02、softmax 与交叉熵、动态规划（维特比会从零讲）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_finetuning.ipynb'),
    ("核心参考", "Devlin et al. 2019（BERT 的四种下游范式）、Rajpurkar et al. 2016（SQuAD）、Wang et al. 2019（GLUE）、Howard & Ruder 2018（ULMFiT 的判别式学习率）"),
    ("预计时长", "读 60 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("three", "三种任务范式：头怎么接决定了一切", "".join([
        P("预训练给了你一个东西：<strong>一个把 token 序列映射成上下文相关向量序列的函数</strong> <code>f: (x_1..x_n) → (h_1..h_n)</code>。微调要做的就是在它上面接一个「头」，把 <code>h</code> 变成任务需要的输出。"),
        P("绝大多数 NLU 任务落在三种范式里，它们的区别只在<strong>用哪些 <code>h</code>、输出什么形状</strong>："),
        ASCII("""                    [CLS] 这  家  店  的  服  务  很  好 [SEP]
                      h0  h1  h2  h3  h4  h5  h6  h7  h8  h9
                      │   │   │   │   │   │   │   │   │   │

① 序列分类 (sequence classification)
   用 h0（[CLS]）或所有 h 的平均 → 一个 C 类 softmax
        h0 ──▶ [Linear C] ──▶ P(正面/负面)          输出: 1 个标签
   任务: 情感、意图、NLI、句对匹配、内容审核

② token 分类 (token classification)
   每个 h_i 独立过同一个头 → 每个位置一个标签
        h1..h8 ──▶ [Linear K] ──▶ BIO 标签序列       输出: n 个标签
   任务: NER、词性标注、分块、槽位填充
   ⚠️ 关键约束: 标签序列有**语法**（I-PER 不能跟在 B-LOC 后面）→ 需要约束解码

③ span 抽取 (extractive QA)
   两个头，各自在序列上做一次 softmax，选出答案的起止位置
        h ──▶ [Linear 1] ──▶ start_logits ──softmax over positions──▶ 起点
        h ──▶ [Linear 1] ──▶ end_logits   ──softmax over positions──▶ 终点
   任务: SQuAD 式抽取问答、信息抽取
   ⚠️ 关键约束: end >= start，且长度有上限 → 需要联合搜索最优 span""")
        ,
        DUAL(
            "三种范式的<strong>参数量差异小到可以忽略</strong>——分类头就是一个 <code>768×C</code> 的矩阵，几万个参数，相比 110M 的主干微不足道。这带来一个重要认识：<em>微调的绝大部分工作发生在主干里，头只是把表示「翻译」成任务格式</em>。这也解释了为什么同一个预训练模型能在几十种任务上都表现良好——它学到的是通用表示，不是任务特定的技能。",
            "但三种范式的<strong>输出空间结构</strong>差异巨大，这才是设计的重点。① 输出空间是 <code>C</code> 个互斥类，无结构；② 输出空间是 <code>K^n</code>，但有<strong>硬性语法约束</strong>（BIO 的合法转移），朴素逐位置 argmax 会产生非法序列；③ 输出空间是 <code>O(n²)</code> 个 span，有<strong>顺序约束</strong>（end≥start），独立取两个 argmax 可能得到 end&lt;start 的无效答案。<em>后两者都需要在解码时施加约束，这是本模块最有实操价值的部分。</em>",
        ),
        CALLOUT("warn", "一个非常常见的实现错误：<strong>token 分类时忘记处理子词</strong>。tokenizer 会把「Washington」切成 <code>Wash ##ing ##ton</code> 三个 token，但标注数据里它只有一个标签 <code>B-LOC</code>。标准做法是：<em>只对每个词的第一个子词计损失，其余子词的标签设为 -100</em>（HF 的 <code>word_ids()</code> 就是为此存在的）。忘了这一步，模型会学到把同一个实体的后续子词标成 O，评估时 F1 莫名其妙地低。这个坑几乎每个人都踩过一次。"),
    ])),
    ("cls", "① 序列分类：[CLS] 还是平均池化", "".join([
        P("最简单的范式，但有一个值得较真的细节：<strong>句子的向量表示该怎么取</strong>？"),
        TABLE(["池化方式", "做法", "什么时候好", "注意"], [
            ["<strong>[CLS]</strong>", "取首位隐状态（BERT 还过一层 <code>tanh(W·h)</code> 的 pooler）", "<strong>微调时</strong>——梯度会教会 [CLS] 汇总信息", "<em>未微调时很差</em>，因为没有预训练目标在用它（RoBERTa 去掉 NSP 后尤甚）"],
            ["<strong>mean pooling</strong>", "对所有非 padding 位置的 <code>h</code> 求平均", "<strong>不微调直接取表示时</strong>（检索、相似度）", "必须用 attention mask 加权，否则 padding 会稀释"],
            ["<strong>max pooling</strong>", "逐维取最大", "关键词触发型任务（如毒性检测）", "对长文本不稳定"],
            ["<strong>attention pooling</strong>", "学一个查询向量对所有 <code>h</code> 做注意力加权", "任务需要「找重点」时", "多几千参数，通常小幅提升"],
        ]),
        DUAL(
            "实践经验：<strong>要微调就用 [CLS]，不微调就用 mean pooling</strong>。原因在模块 01 说过——<code>[CLS]</code> 之所以能代表整句，是因为有目标在训练它；如果你只是拿一个预训练模型直接抽向量（不训练），<code>[CLS]</code> 从未被任何梯度教过要汇总什么，效果常常显著差于简单平均。这个反直觉的事实在做检索时是致命的（模块 05 展开）。",
            "还有一个几何层面的问题：<strong>BERT 的句向量空间高度各向异性</strong>——所有向量挤在一个狭窄的锥体里，导致任意两个句子的余弦相似度都很高（0.7+），失去区分度。缓解手段有白化（whitening）、去除高频方向、或者用对比学习重新训练（SimCSE）。<em>直接把 BERT 的 [CLS] 当句向量做检索，是一个经典的、效果很差的做法</em>——但因为它「看起来合理」，被反复重新发明。",
        ),
        H3("句对任务：两种编码方式"),
        P("NLI、语义相似度、检索这类任务涉及<em>两个</em>句子，有两种截然不同的做法，它们的取舍在模块 05 会算成一笔账，这里先建立概念："),
        UL([
            "<strong>cross-encoder（交叉编码）</strong>：把两句拼成 <code>[CLS] A [SEP] B [SEP]</code> 一起过模型。两句的每个 token 之间都能互相注意 → <em>精度最高</em>。代价：无法预计算，<code>N</code> 个候选就要跑 <code>N</code> 次前向。",
            "<strong>bi-encoder（双塔）</strong>：两句<em>分别</em>编码成向量，用余弦相似度打分。可以离线预计算所有文档向量、在线只算查询 → <em>快几个数量级</em>。代价：两句之间没有交互，精度低一截。",
        ]),
        CALLOUT("intuition", "记住这个二分，它在整个 NLP 系统设计里反复出现：<strong>「交互带来精度，独立带来可预计算」</strong>。检索系统的标准架构就是这两者的组合——双塔做召回（从百万里选 100），交叉编码做精排（对 100 个重排）。<em>这不是妥协，是在成本-精度前沿上的正确取点</em>，模块 05 会把这个前沿画出来。"),
    ])),
    ("token", "② token 分类：BIO 标注与约束解码", "".join([
        P("NER 这类任务要给每个 token 一个标签。标签体系通常是 <span class=\"term\">BIO</span>（也叫 IOB2）："),
        ASCII("""句子:   张   三   在   北   京   工   作
BIO :  B-PER I-PER  O  B-LOC I-LOC  O   O
        │     │     │    │     │
        │     │     │    │     └─ Inside-LOC: 「北京」的后续 token
        │     │     │    └─────── Begin-LOC:  一个地点实体的开始
        │     │     └──────────── Outside:    不属于任何实体
        │     └────────────────── Inside-PER
        └──────────────────────── Begin-PER

**合法性约束（这是关键）**：
  ✓ O      → B-X 或 O            ✗ O     → I-X   （实体不能凭空「继续」）
  ✓ B-X    → I-X 或 B-Y 或 O     ✗ B-PER → I-LOC （类型不能中途变）
  ✓ I-X    → I-X 或 B-Y 或 O     ✗ I-LOC → I-PER

朴素逐位置 argmax **不知道这些约束**，会产出 O → I-PER 这种非法序列。""")
        ,
        DUAL(
            "为什么非法序列是个真问题？因为下游要把标签序列<em>解析成实体列表</em>。遇到 <code>O I-PER I-PER</code>，解析器要么报错、要么用启发式补救（当作 <code>B-PER</code>？丢弃？），无论哪种都会让评估指标失真、让产品行为不可预测。<strong>而且这不是罕见情况——朴素解码在真实数据上产生非法转移的比例通常在百分之几，足以影响实体级 F1。</strong>",
            "解决办法是<strong>约束解码</strong>：把「找最优标签序列」建模成在一个带非法转移屏蔽的图上找最高分路径，用 <span class=\"term\">Viterbi</span> 动态规划求解。复杂度 <code>O(n·K²)</code>，<code>K</code> 是标签数（通常几十），完全可以接受。<em>更进一步，可以把转移分数也变成可学习参数——那就是 CRF 层（C17 讲过 CRF 本身，这里是把它接在 BERT 上）</em>。BERT+CRF 是 NER 的经典组合，虽然近年发现在强预训练模型上 CRF 的增益变小了（表示已经足够好），但<strong>约束解码本身仍然必要</strong>——它保证输出合法，这是零成本的正确性保证。",
        ),
        H3("Viterbi：三行递推"),
        P("设 <code>e[i][k]</code> 是位置 <code>i</code> 标签 <code>k</code> 的发射分数（模型输出的 logit），<code>T[j][k]</code> 是从标签 <code>j</code> 转移到 <code>k</code> 的分数（非法转移设为 <code>−∞</code>）。定义 <code>δ[i][k]</code> = 以位置 <code>i</code> 标签 <code>k</code> 结尾的最优路径分数："),
        MATH("\\delta[0][k] = e[0][k], \\qquad \\delta[i][k] = e[i][k] + \\max_j \\big(\\delta[i-1][j] + T[j][k]\\big)"),
        P("回溯指针记录每步的 <code>argmax j</code>，最后从 <code>argmax_k δ[n-1][k]</code> 倒推出整条路径。notebook 会把它实现出来，并<strong>与暴力枚举所有 <code>K^n</code> 条路径对拍</strong>——在小规模下两者必须给出完全相同的最优路径。"),
        CALLOUT("warn", "评估 NER 时的另一个坑：<strong>token 级 F1 与实体级 F1 不是一回事，而且前者会系统性地高估</strong>。「北京」被标成 <code>B-LOC O</code>（第二个 token 错了），token 级 F1 = 50%，但实体级 F1 = 0（这个实体根本没被正确抽出来）。<em>产品关心的是实体级</em>——用户要的是「北京」这个实体，不是「一半正确」。<code>seqeval</code> 库算的就是实体级，notebook 会把两种指标都实现并展示它们的差距。"),
    ])),
    ("span", "③ span 抽取：两个 softmax 与联合搜索", "".join([
        P("抽取式问答（SQuAD 范式）的输出是原文中的一个连续片段。做法是<strong>两个独立的位置分类器</strong>："),
        CODE("""start_logits = h @ W_start   # (n,) —— 每个位置作为「答案起点」的分数
end_logits   = h @ W_end     # (n,) —— 每个位置作为「答案终点」的分数

# 训练：两个交叉熵之和
loss = CE(start_logits, gold_start) + CE(end_logits, gold_end)"""),
        P("训练很直接，<strong>推理才是重点</strong>。天真的做法是分别取两个 argmax，但这会产生三类无效答案："),
        TABLE(["问题", "例子", "为什么发生"], [
            ["<code>end &lt; start</code>", "start=8, end=3", "两个分类器<strong>独立</strong>，没有任何机制保证顺序"],
            ["跨越 [SEP] 或落进问题区", "答案片段包含了问题的 token", "位置分类器在整个序列上做 softmax，包括问题部分"],
            ["答案过长", "抽出 200 个 token 作为答案", "没有长度约束；通常真实答案 &lt; 30 token"],
        ]),
        P("正确做法是<strong>联合搜索</strong>：在满足约束的 <code>(i,j)</code> 对里最大化 <code>start_logit[i] + end_logit[j]</code>："),
        MATH("(\\hat{i}, \\hat{j}) = \\arg\\max_{\\substack{i \\le j \\le i + L_{max} \\\\ i, j \\in \\text{context}}} \\big( s_i + e_j \\big)"),
        DUAL(
            "朴素实现是双重循环 <code>O(n²)</code>，对 <code>n=384</code> 是 15 万次比较，还能接受。但有个 <code>O(n·L_max)</code> 的写法：对每个 <code>i</code>，只看窗口 <code>[i, i+L_max]</code> 内的 <code>j</code>。更巧的是可以用<strong>后缀最大值</strong>做到 <code>O(n)</code>：预计算 <code>suffix_max[i] = max_{j≥i} e_j</code> 及其 argmax，然后对每个 <code>i</code> 直接查表。notebook 会实现这三种并对拍。",
            "还有一个实践中必须处理的问题：<strong>不可回答的问题</strong>（SQuAD 2.0 引入）。做法是把 <code>[CLS]</code> 位置当作「无答案」的特殊 span，即 <code>(0,0)</code>。推理时比较「最优有答案 span 的分数」与「<code>s_0 + e_0</code>」，后者更高就输出「无法回答」。<em>这个设计很优雅——不需要额外的分类头，复用同一套 logits</em>。阈值需要在验证集上调（因为两类分数的尺度不同）。",
        ),
        H3("长文档：滑窗与跨窗合并"),
        P("BERT 只能吃 512 token，但很多文档更长。标准解法是<strong>滑动窗口</strong>：用 <code>stride</code>（如 128）切成重叠的多个片段，每段独立预测，最后合并。合并时的关键是<em>分数要可比</em>——不同窗口的 softmax 是各自归一化的，直接比概率不对，应该比<strong>未归一化的 logit 之和</strong>。这是个很容易写错的细节。"),
        CALLOUT("intuition", "span 抽取范式的一个重要优点，在 LLM 时代反而更明显了：<strong>它的输出天然是「原文中的片段」，不可能编造</strong>。生成式 QA 会幻觉，抽取式不会——答案要么在原文里，要么模型说不知道。<em>在合规、法律、医疗等对可溯源性要求高的场景，这个性质本身就是选择抽取式的充分理由</em>，即使生成式的「灵活性」看起来更强。"),
    ])),
    ("recipe", "微调配方：那些让分数差 3 分的细节", "".join([
        P("微调看起来简单（加个头、跑几个 epoch），但配方不对会显著掉分，而且失败模式很隐蔽。"),
        TABLE(["细节", "推荐做法", "不这么做会怎样"], [
            ["<strong>学习率</strong>", "2e-5 ~ 5e-5（比从头训练小 100 倍）", "太大（1e-3）会<strong>灾难性遗忘</strong>，几步就把预训练知识冲掉；太小则学不动"],
            ["<strong>warmup</strong>", "前 6~10% 步数线性升温", "开头的大梯度会破坏预训练权重"],
            ["<strong>epoch 数</strong>", "2~4（小数据集 3~5）", "超过 5 个 epoch 在小数据上必过拟合"],
            ["<strong>判别式学习率</strong>", "底层学习率更小（如逐层 ×0.95 衰减）", "底层学的是通用特征，改动它们收益小、破坏大"],
            ["<strong>随机种子</strong>", "<strong>跑多个种子取均值±方差</strong>", "小数据集上 BERT 微调的种子方差可达 2~3 分——单次结果不可信"],
            ["<strong>最大长度</strong>", "按任务的实际长度分布设，不要无脑 512", "attention 是 O(L²)，无脑 512 可能浪费 10 倍算力"],
            ["<strong>类别不平衡</strong>", "加权损失或重采样；用 macro-F1 而非 accuracy", "99:1 的数据上，全预测多数类就有 99% accuracy"],
        ]),
        DUAL(
            "<strong>种子方差这一条特别值得强调</strong>，因为它直接影响你能不能相信自己的实验结论。Dodge et al. 2020 系统研究发现：在 GLUE 的小数据集（如 RTE、MRPC）上，仅改变随机种子，BERT 微调的最终分数波动可达 2–3 个点，甚至有些种子会「训崩」（退化到多数类基线）。<em>这意味着「我的方法比 baseline 高 1 分」这种结论，如果只跑了一个种子，很可能纯属噪声</em>。",
            "工程上的做法：<strong>至少 3–5 个种子，报告均值与标准差，用配对检验判断显著性</strong>（C03/C10 有完整的统计方法）。这不是学术洁癖——在工业界，一个「涨了 1 分」的模型上线后没有效果，浪费的是真实的时间与信任。C40（研究方法论）把这件事作为实验设计的核心纪律。",
        ),
        H3("灾难性遗忘：为什么学习率要这么小"),
        P("预训练权重是在数十亿 token 上学到的，而微调数据可能只有几千条。如果学习率太大，几个 batch 的梯度就足以把权重推离预训练的「好区域」，模型退化成一个在小数据上过拟合的随机初始化网络。<strong>判别式学习率</strong>（discriminative fine-tuning，Howard &amp; Ruder 2018）的思路是：底层学的是词法/句法等通用特征，应该几乎不动；顶层学的是语义/任务相关特征，可以多动。"),
        MATH("\\eta_{\\ell} = \\eta_{top} \\cdot \\gamma^{(L - \\ell)}, \\qquad \\gamma \\approx 0.95"),
        CALLOUT("intuition", "更极端的做法是<strong>只训练头、冻结主干</strong>（linear probing）。它极快、极省显存、不可能遗忘，但通常比全量微调低几个点。<em>这两者之间有一整条谱系</em>：冻结主干 → 只解冻顶部几层 → 判别式学习率全量微调 → 均一学习率全量微调。数据越少，越应该往「冻结」那端靠。<strong>而 LoRA 等参数高效方法（C02/C50）本质上是在这条谱系上开的一条新路——让全部层都能更新，但只更新一个低秩子空间</strong>。"),
    ])),
    ("metrics", "评估：选错指标比模型差更糟", "".join([
        TABLE(["任务", "常用指标", "为什么不用 accuracy", "陷阱"], [
            ["情感二分类（均衡）", "accuracy / F1", "—", "—"],
            ["毒性检测（1% 正例）", "<strong>PR-AUC / macro-F1</strong>", "全预测「无毒」就有 99% accuracy", "ROC-AUC 在极度不平衡时也会虚高"],
            ["CoLA（语法可接受性）", "<strong>MCC</strong>（马修斯相关系数）", "类别不平衡且两类都重要", "MCC 在 [-1,1]，0 表示随机"],
            ["NER", "<strong>实体级 micro-F1</strong>", "token 级会系统性高估", "必须用 seqeval 式的实体匹配"],
            ["抽取式 QA", "<strong>EM + F1</strong>（token 重叠）", "EM 太严（差一个标点就 0 分）", "要做答案归一化（去冠词、标点、大小写）"],
            ["语义相似度（STS）", "<strong>Spearman 相关</strong>", "这是回归不是分类", "Pearson 对非线性单调关系不敏感"],
        ]),
        P("其中 <strong>MCC</strong> 值得单独说，因为它是 GLUE 里 CoLA 任务的指标，很多人第一次见。它综合了混淆矩阵的全部四个格子："),
        MATH("\\text{MCC} = \\frac{TP \\cdot TN - FP \\cdot FN}{\\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}"),
        P("它的好处是<strong>对类别不平衡鲁棒</strong>：只有当模型在两个类上都做得好时 MCC 才高，而 accuracy 和单一 F1 都可以被多数类刷高。notebook 会用一个不平衡数据集对比这几个指标的表现，你会看到 accuracy 0.95 而 MCC 0.0 的情况——<em>模型什么也没学到，但 accuracy 看起来很棒</em>。"),
        CALLOUT("danger", "<p>QA 评估的一个具体陷阱：<strong>EM（exact match）对答案归一化极其敏感</strong>。金标答案是「the White House」，模型输出「White House」——不归一化的话 EM = 0。SQuAD 的官方评估脚本会做四步归一化：转小写、去标点、去冠词（a/an/the）、压缩空格。<em>自己实现评估时忘了这一步，会低估模型 5–10 个点</em>，然后你会以为模型很差，去做一堆无用的优化。notebook 会把归一化函数实现出来，量化它的影响。</p>", "先归一化，再算 EM"),
    ])),
    ("ledger", "算一笔账：三种范式的成本与选型", "".join([
        P("把三种范式的计算特征放在一起。假设 <code>n=128</code>、<code>d=768</code>、12 层。"),
        TABLE(["范式", "头的参数量", "推理前向次数", "解码复杂度", "输出空间大小"], [
            ["序列分类（C 类）", "<code>768×C</code> ≈ 1.5k（C=2）", "1", "<code>O(C)</code>", "<code>C</code>"],
            ["token 分类（K 标签）", "<code>768×K</code> ≈ 7k（K=9）", "1", "<strong><code>O(nK²)</code></strong>（Viterbi）", "<code>K^n</code>（受约束）"],
            ["span 抽取", "<code>768×2</code> ≈ 1.5k", "1（长文档要 ⌈L/stride⌉ 次）", "<strong><code>O(n·L_max)</code></strong> 或 <code>O(n)</code>", "<code>O(n²)</code>"],
        ]),
        P("三点观察："),
        UL([
            "<strong>头的参数量都可以忽略</strong>（几千 vs 主干 110M）。微调的成本几乎完全由主干决定，与任务类型无关。",
            "<strong>推理都只要一次前向</strong>——这是 encoder 范式相对生成式的核心优势。生成式做同样的任务要自回归解码几十到几百步（模块 05 会算这笔账）。",
            "<strong>解码复杂度虽然不同，但都远小于前向</strong>。Viterbi 的 <code>O(nK²)</code> = 128×81 ≈ 1 万次操作，而一次 BERT 前向是 ~10¹⁰ FLOPs。<em>所以约束解码是「免费」的正确性保证，没有理由不做。</em>",
        ]),
        P("最后给一个选型的决策树，它比任何模型对比表都实用："),
        ASCII("""任务的输出是什么？
├─ 一个标签（整段/整对）
│    └─▶ ① 序列分类。微调用 [CLS]；不微调抽向量用 mean pooling。
│         句对任务：要精度用 cross-encoder，要速度用 bi-encoder。
│
├─ 每个 token 一个标签
│    └─▶ ② token 分类 + **约束解码**（Viterbi/CRF）。
│         子词只在首片计损失；评估用**实体级** F1。
│
├─ 原文中的一个片段
│    └─▶ ③ span 抽取（双 softmax + 联合搜索）。
│         长文档滑窗；不可回答用 [CLS] 作为 (0,0) span。
│
└─ 自由文本（改写、摘要、翻译）
     └─▶ 不是本模块的范式 —— 需要生成，见模块 04（encoder-decoder）
         或 decoder-only LLM（模块 05 会算成本账）。""")
        ,
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>微调的技术含量不在「接个头」，而在「输出空间的结构约束怎么在解码时被强制执行」以及「评估指标是否真的度量了你关心的东西」</strong>。头的代码十行就写完了，但忘记 Viterbi 会让你输出非法序列、忘记归一化会让 EM 低估十个点、忘记跑多种子会让你相信一个不存在的改进。<em>这些细节不体现在论文的方法章节里，但决定了你的模型能不能上线。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>CRF 层在强预训练模型上还有没有用</strong>：早期 BiLSTM-CRF 时代 CRF 增益明显，但 BERT+CRF 相对 BERT+softmax 的增益已经很小（部分数据集上甚至为负）。<em>约束解码</em>（保证合法性）与<em>学习转移分数</em>（CRF）是两件事，前者仍必要，后者的价值在缩小——这个边界尚未被系统刻画。",
            "<strong>指令化的 NLU</strong>：把分类/NER/QA 全部转成「文本到文本」的生成任务（T5 的路线，模块 04），或者用 LLM 的 few-shot / 结构化输出来做。它牺牲效率换取零样本能力与统一接口，但在有标注数据的场景下精度通常不如专门微调。<em>这个取舍点随模型能力提升在移动</em>，模块 05 会正面讨论。",
            "<strong>微调的稳定性</strong>：小数据集上的种子方差问题（Dodge et al. 2020）至今没有彻底解决。重初始化顶层、更长 warmup、混合精度的数值问题、以及 Adam 的 bias correction 都被提出过，但缺乏统一理论。",
            "<strong>参数高效微调的边界</strong>：LoRA/adapter/prefix-tuning 在多大程度上能匹配全量微调，取决于任务与数据量，尚无可靠的先验判据。对 encoder 的 NLU 任务，这方面的系统研究比对 decoder 少得多。",
            "<strong>结构化预测的现代化</strong>：嵌套实体、重叠 span、篇章级关系抽取这些超出 BIO 表达力的任务，需要更丰富的输出结构（span-based、图结构、seq2seq 生成）。哪种表示在什么条件下最优，仍是活跃方向。",
        ]),
        CALLOUT("paper", "必读：Devlin et al. 2019 <em>BERT</em> 第 4 节（四种下游范式的原始定义）、Rajpurkar et al. 2016/2018 <em>SQuAD 1.1/2.0</em>（span 抽取范式与「不可回答」的设计）、Wang et al. 2019 <em>GLUE</em>（多任务基准与各任务的指标选择理由）、Howard &amp; Ruder 2018 <em>ULMFiT</em>（判别式学习率与逐层解冻）、Dodge et al. 2020 <em>Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping</em>（种子方差的系统研究，做实验前必读）、Lample et al. 2016 <em>Neural Architectures for NER</em>（BiLSTM-CRF 与 BIO 约束）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · 下游微调三范式（分类头 / BIO 约束解码 / span 联合搜索，全部从零）

目标：把 **序列分类 → token 分类 + Viterbi 约束解码 → span 抽取 + 联合搜索** 从零实现，
每个解码器都**对拍暴力枚举**、每个指标都**手写并暴露它的陷阱**。

路线：三种头 → 池化方式对比 → BIO 合法性与 Viterbi（对拍暴力）→ token级 vs 实体级 F1 →
span 联合搜索三种实现对拍 → EM 归一化的影响 → MCC vs accuracy → ✏️ 练习 → 📖 答案 → 🧪 种子方差胶囊。

> 心智模型：**头很简单，难的是输出空间的结构约束怎么在解码时被强制执行，以及指标是否真的度量了你关心的东西。**"""),
    md("""## 1 · 三种头：参数量都可以忽略

预训练主干给你 `h: (n, d)`。三种范式只是用不同的方式把 `h` 变成任务输出。"""),
    code("""import numpy as np, math, re, string, itertools
rng = np.random.default_rng(0)

D, N = 32, 12          # 隐维度、序列长度

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x); return e / e.sum(axis=axis, keepdims=True)

class SequenceClassificationHead:
    def __init__(self, d, n_classes, seed=0):
        r = np.random.default_rng(seed); self.W = r.normal(size=(d, n_classes)) * 0.1
    def __call__(self, h, pooling='cls', attn_mask=None):
        if pooling == 'cls':
            pooled = h[0]
        elif pooling == 'mean':
            m = np.ones(len(h)) if attn_mask is None else attn_mask
            pooled = (h * m[:, None]).sum(0) / m.sum()
        elif pooling == 'max':
            pooled = h.max(0)
        else:
            raise ValueError(pooling)
        return pooled @ self.W

class TokenClassificationHead:
    def __init__(self, d, n_labels, seed=0):
        r = np.random.default_rng(seed); self.W = r.normal(size=(d, n_labels)) * 0.1
    def __call__(self, h):
        return h @ self.W                        # (n, K) 每个位置一组 logits

class SpanHead:
    def __init__(self, d, seed=0):
        r = np.random.default_rng(seed); self.W = r.normal(size=(d, 2)) * 0.1
    def __call__(self, h):
        logits = h @ self.W
        return logits[:, 0], logits[:, 1]        # start_logits, end_logits

h = rng.normal(size=(N, D))
cls_head, tok_head, span_head = SequenceClassificationHead(D, 3), TokenClassificationHead(D, 9), SpanHead(D)
print('序列分类输出:', cls_head(h).shape, '(3 类)')
print('token 分类输出:', tok_head(h).shape, '(每位置 9 标签)')
s_log, e_log = span_head(h)
print('span 输出:', s_log.shape, e_log.shape)

BACKBONE = 110e6
for name, head in [('序列分类(3类)', cls_head.W), ('token分类(9标签)', tok_head.W), ('span抽取', span_head.W)]:
    print(f'{name:<18s} 头参数 {head.size:>6d}  (主干 110M 的 {head.size/BACKBONE*768/D:.5%})')
assert cls_head(h).shape == (3,) and tok_head(h).shape == (N, 9)
print('\\n✅ 三种头的参数量都可忽略 —— 微调成本几乎完全由主干决定，与任务类型无关')"""),
    md("""### 池化方式：[CLS] 还是 mean？

**要微调就用 [CLS]（梯度会教它汇总），不微调直接抽向量就用 mean pooling。**
下面用一个「未微调」的模拟场景展示差别。"""),
    code("""def make_sentences(n=200, seed=3):
    '''每句由若干「词向量」构成；标签 = 是否含有「关键词」（用一个特定方向表示）。'''
    r = np.random.default_rng(seed)
    key = r.normal(size=D); key /= np.linalg.norm(key)
    Hs, ys = [], []
    for _ in range(n):
        L = r.integers(6, 12)
        hh = r.normal(size=(L, D)) * 0.5
        y = int(r.random() < 0.5)
        if y:
            hh[r.integers(1, L)] += key * 3.0          # 在某个**中间**位置埋入关键信号
        hh = np.vstack([r.normal(size=D) * 0.5, hh])   # 位置 0 是 [CLS]，**未被训练过**
        Hs.append(hh); ys.append(y)
    return Hs, np.array(ys)

def probe(Hs, ys, pooling, seed=0):
    '''用池化向量训一个线性探针，返回准确率。'''
    feats = []
    for hh in Hs:
        if pooling == 'cls':  feats.append(hh[0])
        elif pooling == 'mean': feats.append(hh.mean(0))
        else: feats.append(hh.max(0))
    Xf = np.stack(feats); Xf = (Xf - Xf.mean(0)) / (Xf.std(0) + 1e-8)
    r = np.random.default_rng(seed); w = r.normal(size=D) * 0.01; b = 0.0
    for _ in range(1500):
        p = 1 / (1 + np.exp(-(Xf @ w + b)))
        g = p - ys
        w -= 0.5 * (Xf.T @ g) / len(ys); b -= 0.5 * g.mean()
    return ((Xf @ w + b > 0).astype(int) == ys).mean()

Hs, ys = make_sentences()
for pool in ['cls', 'mean', 'max']:
    print(f'{pool:>5s} pooling 探针准确率: {probe(Hs, ys, pool):.1%}')
acc_cls, acc_mean = probe(Hs, ys, 'cls'), probe(Hs, ys, 'mean')
assert acc_mean > acc_cls + 0.10, '未微调时，mean pooling 应显著优于 [CLS]'
print(f'\\n✅ 未微调场景下 mean({acc_mean:.0%}) 远好于 [CLS]({acc_cls:.0%})：')
print('   [CLS] 之所以能代表整句，是因为**有目标在训练它**；没训练过的 [CLS] 什么也不是。')
print('   直接拿预训练 BERT 的 [CLS] 当句向量做检索，是个经典的、效果很差的做法。')"""),
    md("""## 2 · BIO 标注：合法性约束与 Viterbi

BIO 标签序列有**语法**：`O → I-X` 非法，`B-PER → I-LOC` 非法。
朴素逐位置 argmax 不知道这些，会产出非法序列。"""),
    code("""ENTITY_TYPES = ['PER', 'LOC', 'ORG']
LABELS = ['O'] + [f'{p}-{t}' for t in ENTITY_TYPES for p in ('B', 'I')]
L2I = {l: i for i, l in enumerate(LABELS)}
K = len(LABELS)
print('标签集:', LABELS)

def legal_transition(prev, cur):
    '''prev -> cur 是否合法（IOB2 规则）。'''
    if cur == 'O' or cur.startswith('B-'):
        return True                                   # O 与 B-X 永远可以开始
    # cur 是 I-X：只能跟在 B-X 或 I-X 之后（同类型）
    t = cur[2:]
    return prev in (f'B-{t}', f'I-{t}')

def transition_matrix():
    T = np.zeros((K, K))
    for i, p in enumerate(LABELS):
        for j, c in enumerate(LABELS):
            if not legal_transition(p, c):
                T[i, j] = -1e9                        # 屏蔽非法转移
    return T

def start_mask():
    '''序列开头不能是 I-X。'''
    m = np.zeros(K)
    for i, l in enumerate(LABELS):
        if l.startswith('I-'): m[i] = -1e9
    return m

T, S0 = transition_matrix(), start_mask()
assert legal_transition('B-PER', 'I-PER') and not legal_transition('B-PER', 'I-LOC')
assert not legal_transition('O', 'I-LOC')
assert legal_transition('I-LOC', 'B-PER')
n_legal = (T > -1).sum()
print(f'\\n{K}×{K} = {K*K} 种转移中，合法的有 {n_legal} 种（{n_legal/K/K:.0%}）')
print('✅ 转移矩阵正确：非法转移被屏蔽为 -1e9')"""),
    code("""def naive_decode(emissions):
    '''逐位置 argmax —— 不管约束。'''
    return [LABELS[i] for i in emissions.argmax(1)]

def viterbi_decode(emissions, T, S0):
    '''O(n·K²) 动态规划，返回最优合法路径。'''
    n = len(emissions)
    delta = emissions[0] + S0
    back = np.zeros((n, K), dtype=int)
    for i in range(1, n):
        scores = delta[:, None] + T                  # (K_prev, K_cur)
        back[i] = scores.argmax(0)
        delta = emissions[i] + scores.max(0)
    path = [int(delta.argmax())]
    for i in range(n - 1, 0, -1):
        path.append(int(back[i][path[-1]]))
    return [LABELS[i] for i in reversed(path)]

def brute_force_decode(emissions, T, S0):
    '''暴力枚举所有 K^n 条路径（只在极小 n 下用，作为对拍参考）。'''
    n = len(emissions)
    best, best_score = None, -np.inf
    for path in itertools.product(range(K), repeat=n):
        sc = emissions[0][path[0]] + S0[path[0]]
        for i in range(1, n):
            sc += T[path[i-1], path[i]] + emissions[i][path[i]]
        if sc > best_score:
            best, best_score = path, sc
    return [LABELS[i] for i in best]

# 对拍：小规模下 Viterbi 必须与暴力枚举给出相同的最优路径
for trial in range(20):
    em = np.random.default_rng(trial).normal(size=(4, K))
    v, b = viterbi_decode(em, T, S0), brute_force_decode(em, T, S0)
    assert v == b, f'trial {trial}: Viterbi {v} != 暴力 {b}'
print(f'✅ 对拍通过：20 组随机发射分数下，Viterbi(O(nK²)) 与暴力枚举(O(K^n)) 结果完全一致')
print(f'   规模对比 n=4: Viterbi {4*K*K} 次操作 vs 暴力 {K**4:,} 条路径')"""),
    code("""def count_illegal(labels):
    bad = 0
    if labels and labels[0].startswith('I-'): bad += 1
    for a, b in zip(labels, labels[1:]):
        if not legal_transition(a, b): bad += 1
    return bad

n_seq, tot_naive, tot_vit = 300, 0, 0
for s in range(n_seq):
    em = np.random.default_rng(s).normal(size=(15, K)) * 1.2
    tot_naive += count_illegal(naive_decode(em))
    tot_vit   += count_illegal(viterbi_decode(em, T, S0))
print(f'{n_seq} 条序列（各 15 token）:')
print(f'  朴素 argmax : {tot_naive} 处非法转移')
print(f'  Viterbi     : {tot_vit} 处非法转移')
assert tot_naive > 0, '朴素解码必然产生非法转移'
assert tot_vit == 0, 'Viterbi 必须保证零非法转移'
print('\\n✅ 约束解码是**零成本的正确性保证**：O(nK²)=15×81≈1200 次操作，')
print('   相比一次 BERT 前向的 ~1e10 FLOPs 完全可以忽略。没有理由不做。')"""),
    md("""### token 级 F1 会系统性高估：必须用实体级"""),
    code("""def extract_entities(labels):
    '''从 BIO 序列抽出实体集合 {(类型, 起, 止)}。'''
    ents, start, typ = set(), None, None
    for i, l in enumerate(labels + ['O']):
        if l.startswith('B-') or l == 'O' or (l.startswith('I-') and typ != l[2:]):
            if start is not None:
                ents.add((typ, start, i - 1)); start, typ = None, None
        if l.startswith('B-'):
            start, typ = i, l[2:]
        elif l.startswith('I-') and start is None:
            start, typ = i, l[2:]        # 容错：非法的 I-X 开头当作 B-X
    return ents

def token_f1(gold, pred):
    tp = sum(g == p != 'O' for g, p in zip(gold, pred))
    n_g = sum(g != 'O' for g in gold); n_p = sum(p != 'O' for p in pred)
    prec = tp / n_p if n_p else 0.0; rec = tp / n_g if n_g else 0.0
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)

def entity_f1(gold, pred):
    g, p = extract_entities(gold), extract_entities(pred)
    tp = len(g & p)
    prec = tp / len(p) if p else 0.0; rec = tp / len(g) if g else 0.0
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)

gold = ['B-PER', 'I-PER', 'O', 'B-LOC', 'I-LOC', 'O']
pred = ['B-PER', 'I-PER', 'O', 'B-LOC', 'O',     'O']    # 「北京」的第二个 token 标错
print('金标:', gold)
print('预测:', pred)
print(f'token 级 F1 : {token_f1(gold, pred):.1%}')
print(f'实体级 F1   : {entity_f1(gold, pred):.1%}')
print(f'金标实体: {sorted(extract_entities(gold))}')
print(f'预测实体: {sorted(extract_entities(pred))}')
assert token_f1(gold, pred) > entity_f1(gold, pred), 'token 级会高估'
assert entity_f1(gold, pred) < 0.7, '一个实体边界错 -> 该实体完全不算对'
print('\\n✅ 「一半正确」在实体级评估里等于**完全错误** —— 用户要的是「北京」，不是半个。')"""),
    md("""## 3 · span 抽取：联合搜索的三种实现

分别取两个 argmax 会产生 `end < start`、跨越 [SEP]、答案过长三类无效答案。
**必须联合搜索。** 三种实现，两两对拍。"""),
    code("""def naive_argmax_span(s_log, e_log):
    return int(s_log.argmax()), int(e_log.argmax())

def joint_search_quadratic(s_log, e_log, ctx_start, ctx_end, max_len=10):
    '''O(n²) 暴力：枚举所有合法 (i,j)。'''
    best, bs = (ctx_start, ctx_start), -np.inf
    for i in range(ctx_start, ctx_end + 1):
        for j in range(i, min(i + max_len, ctx_end) + 1):
            sc = s_log[i] + e_log[j]
            if sc > bs: bs, best = sc, (i, j)
    return best

def joint_search_window(s_log, e_log, ctx_start, ctx_end, max_len=10):
    '''O(n·max_len)：对每个 i 只看长度窗口内的 j。'''
    best, bs = (ctx_start, ctx_start), -np.inf
    for i in range(ctx_start, ctx_end + 1):
        hi = min(i + max_len, ctx_end)
        j = i + int(np.argmax(e_log[i:hi + 1]))
        sc = s_log[i] + e_log[j]
        if sc > bs: bs, best = sc, (i, j)
    return best

n_tok, CTX_S, CTX_E = 24, 6, 22       # 0..5 是问题+[SEP]，6..22 是上下文
bad_cases = 0
for trial in range(200):
    r = np.random.default_rng(trial)
    s_log, e_log = r.normal(size=n_tok), r.normal(size=n_tok)
    i0, j0 = naive_argmax_span(s_log, e_log)
    if j0 < i0 or not (CTX_S <= i0 <= CTX_E) or not (CTX_S <= j0 <= CTX_E) or j0 - i0 > 10:
        bad_cases += 1
    a = joint_search_quadratic(s_log, e_log, CTX_S, CTX_E)
    b = joint_search_window(s_log, e_log, CTX_S, CTX_E)
    assert a == b, f'trial {trial}: 两种联合搜索应给出相同结果 {a} vs {b}'
    assert CTX_S <= a[0] <= a[1] <= CTX_E and a[1] - a[0] <= 10, '联合搜索必须满足全部约束'
print(f'✅ 两种联合搜索实现对拍通过（200 组随机 logits）')
print(f'⚠️  朴素双 argmax 在 {bad_cases}/200 = {bad_cases/200:.0%} 的情况下产生**无效答案**')
assert bad_cases > 100, '朴素做法应频繁违反约束'
print('   （end<start、落进问题区、或答案过长）')"""),
    md("""### 不可回答（SQuAD 2.0）：用 [CLS] 作为 (0,0) span"""),
    code("""def predict_with_null(s_log, e_log, ctx_start, ctx_end, max_len=10, null_threshold=0.0):
    '''返回 (span 或 None, 差值分数)。'''
    i, j = joint_search_window(s_log, e_log, ctx_start, ctx_end, max_len)
    best_span_score = s_log[i] + e_log[j]
    null_score = s_log[0] + e_log[0]              # [CLS] 位置
    diff = best_span_score - null_score
    return ((i, j) if diff > null_threshold else None), diff

r = np.random.default_rng(7)
s_log, e_log = r.normal(size=n_tok), r.normal(size=n_tok)
s_log[10] += 4; e_log[12] += 4                    # 制造一个明显的答案
span, diff = predict_with_null(s_log, e_log, CTX_S, CTX_E)
print(f'有明显答案时: span={span}, diff={diff:.2f}')
assert span == (10, 12), f'应抽出 (10,12)，得到 {span}'

s2, e2 = r.normal(size=n_tok) * 0.3, r.normal(size=n_tok) * 0.3
s2[0] += 5; e2[0] += 5                            # [CLS] 分数最高 = 无法回答
span2, diff2 = predict_with_null(s2, e2, CTX_S, CTX_E)
print(f'无答案时:     span={span2}, diff={diff2:.2f}')
assert span2 is None, '应判定为不可回答'
print('\\n✅ 不需要额外的分类头 —— 复用同一套 logits，把 [CLS] 当作「无答案」span。')
print('   阈值 null_threshold 需要在验证集上调（两类分数尺度不同）。')"""),
    md("""### EM 归一化：忘了它会低估 5-10 个点"""),
    code("""def normalize_answer(s):
    '''SQuAD 官方归一化：小写 -> 去标点 -> 去冠词 -> 压空格。'''
    s = s.lower()
    s = ''.join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r'\\b(a|an|the)\\b', ' ', s)
    return ' '.join(s.split())

def exact_match(pred, gold, normalize=True):
    f = normalize_answer if normalize else (lambda x: x)
    return int(f(pred) == f(gold))

def token_overlap_f1(pred, gold):
    p, g = normalize_answer(pred).split(), normalize_answer(gold).split()
    common = {}
    for t in p:
        if t in g: common[t] = min(p.count(t), g.count(t))
    tp = sum(common.values())
    if tp == 0: return 0.0
    prec, rec = tp / len(p), tp / len(g)
    return 2 * prec * rec / (prec + rec)

pairs = [('the White House', 'White House'),
         ('Barack Obama.', 'Barack Obama'),
         ('An apple', 'apple'),
         ('New  York', 'New York'),
         ('Paris', 'London')]
print(f"{'预测':<20s} {'金标':<16s} {'EM(无归一)':>11s} {'EM(归一)':>9s} {'F1':>6s}")
em_raw = em_norm = 0
for p, g in pairs:
    a, b = exact_match(p, g, False), exact_match(p, g, True)
    em_raw += a; em_norm += b
    print(f'{p:<20s} {g:<16s} {a:>11d} {b:>9d} {token_overlap_f1(p,g):>6.2f}')
print(f'\\nEM 无归一化 {em_raw}/{len(pairs)} = {em_raw/len(pairs):.0%}')
print(f'EM 有归一化 {em_norm}/{len(pairs)} = {em_norm/len(pairs):.0%}')
assert em_norm > em_raw, '归一化会显著提高 EM'
assert exact_match('Paris', 'London') == 0, '真错的仍然是 0'
print(f'\\n✅ 忘记归一化会让你低估 {(em_norm-em_raw)/len(pairs):.0%} —— 然后去做一堆无用的优化。')"""),
    md("""## 4 · 指标陷阱：accuracy 0.95 而 MCC 0.00"""),
    code("""def confusion(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum()); tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum()); fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return tp, tn, fp, fn

def mcc(y_true, y_pred):
    tp, tn, fp, fn = confusion(y_true, y_pred)
    num = tp * tn - fp * fn
    den = math.sqrt((tp+fp) * (tp+fn) * (tn+fp) * (tn+fn))
    return 0.0 if den == 0 else num / den

def macro_f1(y_true, y_pred):
    fs = []
    for c in (0, 1):
        tp = int(((y_true == c) & (y_pred == c)).sum())
        fp = int(((y_true != c) & (y_pred == c)).sum())
        fn = int(((y_true == c) & (y_pred != c)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        fs.append(0.0 if p + r == 0 else 2 * p * r / (p + r))
    return float(np.mean(fs))

r = np.random.default_rng(0)
y = (r.random(2000) < 0.05).astype(int)       # 5% 正例（毒性检测的典型分布）
pred_majority = np.zeros_like(y)              # 「全预测多数类」的退化模型
pred_decent   = y.copy()
flip = r.choice(len(y), size=60, replace=False); pred_decent[flip] ^= 1   # 一个真的还行的模型

print(f"{'模型':<16s} {'accuracy':>9s} {'macro-F1':>9s} {'MCC':>7s}")
for name, p in [('全预测多数类', pred_majority), ('真的还行的模型', pred_decent)]:
    acc = (p == y).mean()
    print(f'{name:<16s} {acc:>9.1%} {macro_f1(y,p):>9.3f} {mcc(y,p):>7.3f}')

assert (pred_majority == y).mean() > 0.94, '全预测多数类的 accuracy 高达 95%'
assert mcc(y, pred_majority) == 0.0, 'MCC 正确识别出「什么也没学到」'
assert macro_f1(y, pred_majority) < 0.5, 'macro-F1 也能识别'
assert mcc(y, pred_decent) > 0.5, '真正有用的模型 MCC 显著为正'
print('\\n✅ accuracy 95% 而 MCC 0.00 —— 模型什么也没学到，但指标看起来很棒。')
print('   不平衡任务必须看 MCC 或 macro-F1（GLUE 的 CoLA 用 MCC 正是这个理由）。')"""),
    md("""## ✏️ 练习 1：判别式学习率

实现 `layerwise_lr(base_lr, n_layers, gamma=0.95)`：返回长度 `n_layers+1` 的列表
（索引 0 = 嵌入层，索引 n_layers = 顶层），顶层为 `base_lr`，每往下一层乘 `gamma`。"""),
    code("""def layerwise_lr(base_lr, n_layers, gamma=0.95):
    # TODO: lr[l] = base_lr * gamma^(n_layers - l)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
lrs = layerwise_lr(3e-5, 12, gamma=0.95)
assert len(lrs) == 13
assert abs(lrs[-1] - 3e-5) < 1e-12, '顶层应等于 base_lr'
assert lrs == sorted(lrs), '越往下学习率越小'
assert abs(lrs[0] - 3e-5 * 0.95 ** 12) < 1e-12
print(f'顶层 lr {lrs[-1]:.2e} | 嵌入层 lr {lrs[0]:.2e} | 比值 {lrs[0]/lrs[-1]:.2f}')
# gamma=1.0 退化为均一学习率
assert all(abs(x - 3e-5) < 1e-12 for x in layerwise_lr(3e-5, 12, gamma=1.0))
# 极端：gamma=0 等价于冻结除顶层外的全部层
frozen = layerwise_lr(3e-5, 12, gamma=0.0)
assert frozen[-1] == 3e-5 and all(x == 0 for x in frozen[:-1])
print('✅ 练习 1 通过：gamma=1 是均一微调，gamma=0 是只训顶层，中间是一整条谱系')"""),
    md("""## ✏️ 练习 2：子词标签对齐

tokenizer 把「Washington」切成 `['Wash','##ing','##ton']`，但标注只有一个 `B-LOC`。
实现 `align_labels(word_ids, word_labels)`：
`word_ids` 是每个 token 对应的**词索引**（`None` 表示特殊 token）。
规则：每个词的**第一个**子词取该词的标签，其余子词与特殊 token 都设为 `-100`。"""),
    code("""def align_labels(word_ids, word_labels):
    # TODO: 遍历 word_ids，记录上一个 word_id；首次出现取标签，重复出现或 None -> -100
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
#  [CLS]  Wash  ##ing  ##ton   is    nice  [SEP]
wids = [None,   0,     0,     0,     1,    2,    None]
wlabs = [L2I['B-LOC'], L2I['O'], L2I['O']]
out = align_labels(wids, wlabs)
assert out == [-100, L2I['B-LOC'], -100, -100, L2I['O'], L2I['O'], -100], out
assert out.count(-100) == 4, '2 个特殊 token + 2 个后续子词'
# 边界：全是特殊 token
assert align_labels([None, None], []) == [-100, -100]
# 每个词恰好一个非 -100
non_ignored = [i for i, v in enumerate(out) if v != -100]
assert len(non_ignored) == len(wlabs), '每个词只贡献一个训练信号'
print('对齐结果:', out)
print('✅ 练习 2 通过：忘了这一步，模型会学到把实体的后续子词标成 O，实体级 F1 莫名很低')"""),
    md("""## ✏️ 练习 3：O(n) 的 span 联合搜索

用**后缀最大值**把联合搜索从 O(n·max_len) 降到 O(n)：
预计算 `suf_val[i] = max_{j>=i} e_log[j]` 与对应的 `suf_idx[i]`，
然后对每个 `i` 直接查 `suf_idx[i]`（不带长度上限的版本）。

实现 `joint_search_linear(s_log, e_log, ctx_start, ctx_end)`，返回 `(i, j)`。"""),
    code("""def joint_search_linear(s_log, e_log, ctx_start, ctx_end):
    # TODO: 从右往左算后缀最大值及其索引；再从左往右对每个 i 取 s_log[i] + suf_val[i]
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测：与不带长度上限的 O(n²) 版本对拍 ——
def joint_search_quadratic_nolimit(s_log, e_log, cs, ce):
    best, bs = (cs, cs), -np.inf
    for i in range(cs, ce + 1):
        for j in range(i, ce + 1):
            if s_log[i] + e_log[j] > bs:
                bs, best = s_log[i] + e_log[j], (i, j)
    return best

for trial in range(200):
    r = np.random.default_rng(1000 + trial)
    s_, e_ = r.normal(size=n_tok), r.normal(size=n_tok)
    a = joint_search_linear(s_, e_, CTX_S, CTX_E)
    b = joint_search_quadratic_nolimit(s_, e_, CTX_S, CTX_E)
    assert a == b, f'trial {trial}: 线性 {a} != 二次 {b}'
    assert CTX_S <= a[0] <= a[1] <= CTX_E
print('✅ 练习 3 通过：200 组对拍一致，复杂度从 O(n²) 降到 O(n)')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def layerwise_lr(base_lr, n_layers, gamma=0.95):
    return [base_lr * (gamma ** (n_layers - l)) for l in range(n_layers + 1)]"""),
    code("""# 练习 2 参考答案
def align_labels(word_ids, word_labels):
    out, prev = [], None
    for wid in word_ids:
        if wid is None:        out.append(-100)
        elif wid != prev:      out.append(word_labels[wid])
        else:                  out.append(-100)
        prev = wid
    return out"""),
    code("""# 练习 3 参考答案
def joint_search_linear(s_log, e_log, ctx_start, ctx_end):
    n = ctx_end - ctx_start + 1
    suf_val = np.empty(n); suf_idx = np.empty(n, dtype=int)
    suf_val[-1], suf_idx[-1] = e_log[ctx_end], ctx_end
    for k in range(n - 2, -1, -1):
        pos = ctx_start + k
        if e_log[pos] >= suf_val[k + 1]:
            suf_val[k], suf_idx[k] = e_log[pos], pos
        else:
            suf_val[k], suf_idx[k] = suf_val[k + 1], suf_idx[k + 1]
    best, bs = (ctx_start, ctx_start), -np.inf
    for k in range(n):
        i = ctx_start + k
        sc = s_log[i] + suf_val[k]
        if sc > bs:
            bs, best = sc, (i, int(suf_idx[k]))
    return best"""),
    md("""---
## 🧪 真实数据胶囊：种子方差 —— 你的「涨了 1 分」可能是噪声

Dodge et al. 2020 发现：GLUE 小数据集上，**仅改随机种子**，BERT 微调分数波动可达 2–3 分，
甚至有些种子会训崩。下面模拟这个现象，并计算「要多少种子才能可靠地检测出 1 分的提升」。"""),
    code("""def simulate_finetune(true_score, seed, n_train=2500, collapse_prob=0.06):
    '''模拟一次微调：真实能力 true_score，加上种子噪声，小概率训崩。'''
    r = np.random.default_rng(seed)
    if r.random() < collapse_prob:
        return 52.0 + r.normal(0, 0.5)            # 训崩：退化到多数类基线
    noise_sd = 30.0 / math.sqrt(n_train)          # 小数据集噪声更大
    return true_score + r.normal(0, noise_sd)

BASE_TRUE, NEW_TRUE = 78.0, 79.0                  # 新方法真实高 1 分
runs_base = [simulate_finetune(BASE_TRUE, s) for s in range(20)]
runs_new  = [simulate_finetune(NEW_TRUE, 1000 + s) for s in range(20)]
print(f'baseline 20 个种子: 均值 {np.mean(runs_base):.2f} ± {np.std(runs_base):.2f}, '
      f'范围 [{min(runs_base):.1f}, {max(runs_base):.1f}]')
print(f'新方法  20 个种子: 均值 {np.mean(runs_new):.2f} ± {np.std(runs_new):.2f}, '
      f'范围 [{min(runs_new):.1f}, {max(runs_new):.1f}]')

# 单次实验有多大概率给出**错误**的结论？
wrong = sum(1 for a, b in zip(runs_base, runs_new) if a > b)
print(f'\\n单种子对比: {wrong}/20 = {wrong/20:.0%} 的情况下 baseline 反而「赢了」')
assert wrong > 0, '单次实验必然有相当概率给出错误结论'
assert np.std(runs_base) > 0.5, '种子方差应显著'
print('⚠️  也就是说，只跑一个种子，你有相当概率得出完全相反的结论。')"""),
    md("""**🧪 胶囊练习**：实现 `seeds_needed(effect_size, noise_sd, power=0.8, alpha=0.05)`：
用双样本 t 检验的经典近似 `n ≈ 2(z_{α/2} + z_β)² σ² / Δ²`，
返回**每组需要的种子数**（向上取整，至少 2）。取 `z_{0.025}=1.96`, `z_{0.2}=0.84`。"""),
    code("""def seeds_needed(effect_size, noise_sd, power=0.8, alpha=0.05):
    # TODO: n = ceil(2 * (1.96 + 0.84)^2 * noise_sd^2 / effect_size^2)，下限 2
    raise NotImplementedError"""),
    code("""# 自测
sd = float(np.std(runs_base))
n1 = seeds_needed(1.0, sd)
n3 = seeds_needed(3.0, sd)
assert n1 >= 2 and n3 >= 2
assert n1 > n3, '效应越小，需要的种子越多'
assert abs(n1 - math.ceil(2 * (1.96 + 0.84) ** 2 * sd ** 2 / 1.0)) <= 1
print(f'噪声标准差 {sd:.2f} 分:')
for eff in [0.5, 1.0, 2.0, 3.0]:
    print(f'  要可靠检测 {eff:.1f} 分的提升 -> 每组需要 {seeds_needed(eff, sd):>3d} 个种子')
print('\\n✅ 胶囊练习通过：**「涨了 1 分」通常需要十几个种子才能站得住**。')
print('   工程建议：至少 3-5 个种子，报告均值±标准差，用配对检验判显著性（C03/C10）。')"""),
    code("""# 📖 胶囊参考答案
def seeds_needed(effect_size, noise_sd, power=0.8, alpha=0.05):
    z_a, z_b = 1.96, 0.84
    n = 2 * (z_a + z_b) ** 2 * noise_sd ** 2 / (effect_size ** 2)
    return max(2, math.ceil(n))"""),
    md("""---
## 🔧 旁注：真实库里这些对应什么

- **三种头** → `BertForSequenceClassification` / `BertForTokenClassification` / `BertForQuestionAnswering`。
- **子词对齐** → `tokenizer(..., is_split_into_words=True)` + `encoding.word_ids()`；这正是练习 2 的输入。
- **约束解码** → `torchcrf` / `pytorch-crf` 的 `CRF.decode()`；或自己写 Viterbi（就是本 notebook 这段）。
- **实体级 F1** → `seqeval.metrics.f1_score`（**不要**用 sklearn 的 token 级 F1）。
- **span 联合搜索 + 归一化 EM** → HF 的 `squad_v2` metric 与 `postprocess_qa_predictions`（含滑窗合并）。
- **判别式学习率** → 给 optimizer 传 `param_groups`，按层名分组设不同 `lr`。
- **多种子** → `Trainer(args=TrainingArguments(seed=...))`，跑 N 次取均值；`transformers` 的 `set_seed()`。

怎么用这些库真正跑起来，见 **C50**。"""),
    md("""### 小结
- 三种范式的**头都可忽略不计**；难的是**输出空间的结构约束**：BIO 的合法转移、span 的 `end≥start`。
- **要微调用 [CLS]，不微调抽向量用 mean pooling**——[CLS] 只有被训练过才有意义。
- **Viterbi 约束解码是零成本的正确性保证**（O(nK²) 对比一次前向的 1e10 FLOPs），且已与暴力枚举对拍。
- **实体级 F1 才是产品指标**；token 级会系统性高估。**EM 必须先归一化**，否则低估 5-10 个点。
- **不平衡任务看 MCC / macro-F1**：accuracy 95% 而 MCC 0.00 的模型什么也没学到。
- **子词只在首片计损失**（-100 忽略其余），忘了这步 F1 会莫名很低。
- **种子方差 2-3 分**：单次实验有相当概率给出相反结论；「涨 1 分」需要十几个种子才站得住。

下一站：**模块 04 · Encoder-Decoder** —— 输出不再是标签或片段，而是要**生成**一段新文本。"""),
]
