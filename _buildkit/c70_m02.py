# -*- coding: utf-8 -*-
"""C70 模块 02 · 分块。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（元数据 <code>section_path</code> / "
                 "<code>element_type</code> 是本模块的输入）；"
                 "会读简单的概率推导"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_chunking.ipynb'
                       '（三个竞争指标随块大小的曲线 / 答案完整率的精确公式与实测对拍 / '
                       '重叠的饱和点与索引成本倍数 / 结构感知分块的主题纯度 / '
                       '语义分块的谷点切分 / 父子块让 precision 与完整率同时上升 / '
                       '稀释效应 / 分块 A/B 报告与门禁）'),
    ("核心参考", "LangChain / LlamaIndex 的 <em>RecursiveCharacterTextSplitter</em> 与 "
                 "<em>SentenceWindowNodeParser</em> 的设计取舍 · "
                 "Kamradt 的语义分块（semantic chunking）实践 · "
                 "本课程 C11 模块 03（重排与候选集大小）· C33 模块 01（注入预算）· "
                 "C68 模块 01（参数进 spec 与指纹）"),
    ("预计时长", "读 65 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("objective", "分块的目标函数：三个互相竞争的量", "".join([
        P("「块该多大」是 RAG 里被问得最多、被回答得最差的问题。"
          "常见答案是「512 token，重叠 50」——"
          "<strong>这个答案的问题不是数字错了，而是它没有说这个数字在优化什么。</strong>"),
        P("分块要同时管三个量，而它们互相竞争："),
        TABLE(["量", "定义", "块变大时", "块变小时"], [
            ["<strong>答案完整率</strong> <code>intact</code>",
             "答案<em>完整落在某一个块内</em>的比例",
             "<strong>上升</strong>（大块装得下）", "下降（答案被切断）"],
            ["<strong>主题纯度</strong> <code>1 − cross</code>",
             "块<em>没有</em>跨越文档自己的结构边界的比例",
             "下降（一个块里混了几个主题）", "<strong>上升</strong>"],
            ["<strong>索引成本</strong> <code>n_chunks</code>",
             "块的数量（存储、向量、检索延迟、上下文预算）",
             "<strong>下降</strong>", "上升"],
        ]),
        DUAL(
            "所以「块该多大」不是一个有唯一答案的问题，"
            "而是一个<strong>有约束的优化问题</strong>："
            "<em>在答案完整率不低于某个阈值的前提下，最小化块数</em>。"
            "<strong>阈值来自你的业务（答案说一半是不可接受的失败），"
            "而不是来自某篇博客的默认值。</strong>",
            "写成规划问题：$\\min_{s, o} \\; n(s, o)$ "
            "s.t. $\\text{intact}(s, o) \\ge \\tau$，$\\text{purity}(s) \\ge \\rho$。"
            "本模块的核心贡献是：<strong>$\\text{intact}(s, o)$ 有一个精确的解析式</strong>"
            "（第 3 节），所以这个约束<em>不需要试，可以算</em>。"
            "$n(s, o) = L / (s - o)$，也是解析的。"
            "<em>而第 4 节的纯度定义也是算术</em>——所以这三个量全都不需要试，可以算。",
        ),
        CALLOUT("intuition", "有一个判据能立刻看出一个分块方案有没有想清楚："
                             "<strong>问「你们的最长答案有多长？」</strong>"
                             "<em>答不上来，那么重叠设多少都是猜的</em>——"
                             "第 3 节会证明重叠的正确取值<strong>只由这一个量决定</strong>。"),
    ])),

    # ============================================================== 2
    ("fixed-window", "固定窗口的两个失败", "".join([
        P("固定字符/token 窗口是所有分块的基线。它有两个失败，"
          "<strong>而它们的方向相反</strong>——这正是上一节那张表的来源。"),
        ASCII("""
   失败一：块太小 → 答案被切断

   文档: ...正式员工每年享有 15 天带薪年假。试用期员工...
                        │              │
   块边界 ──────────────┴──────────────┘
   块 k:   "...正式员工每年享有 15 "
   块 k+1: "天带薪年假。试用期员工..."
   → 召回块 k（它确实最相关），答案说一半。**Precision@1 满分。**


   失败二：块太大 → 主题混在一起

   块 j: "...年假需提前三日申请。报销流程说明。餐饮报销单次上限 200 元..."
          └────── 主题 A ──────┘└────────── 主题 B ──────────┘
   → 查「报销上限」时，这个块的向量被主题 A 稀释了（第 7 节量这件事）；
     查「年假申请」时，喂给模型的上下文里混进了无关的报销规定。
"""),
        P("<strong>失败一是断崖式的、可以被精确计算的；"
          "失败二是渐进式的、需要测量。</strong>"
          "这个不对称决定了工程上的处理顺序："
          "<em>先用公式把完整率钉在阈值之上，再在满足约束的配置里挑纯度最好的那个。</em>"),
        H3("为什么「按 token 切」不比「按字符切」更安全"),
        DUAL(
            "很多实现从字符换成 token 后就认为问题解决了。"
            "<strong>不是——切断的概率只与「块长/答案长」的比值有关，与单位无关。</strong>"
            "<em>换单位只是换了刻度</em>。"
            "唯一真正有用的改变是<strong>让边界落在语义边界上</strong>"
            "（句号、段落、标题），这是第 4、5 节的内容。",
            "严格地说：设答案长 $a$、块长 $s$、步长 $s-o$，"
            "这三个量用同一个单位度量时，第 3 节的公式只依赖 $a/s$ 与 $o/s$。"
            "<strong>换单位等于同时缩放 $a, s, o$，公式的值不变。</strong>"
            "<em>唯一的例外是当单位本身携带语义信息时</em>——"
            "「按句切」的分块，答案（通常是一到两句）被切断的概率天然更低，"
            "因为切点与答案的边界对齐了。",
        ),
    ])),

    # ============================================================== 3
    ("intact-formula", "答案完整率的精确公式（本模块最有用的一条）", "".join([
        P("这一节给出 <code>intact</code> 的解析式。"
          "<strong>它的价值是让「重叠设多少」从一个玄学问题变成一次算术。</strong>"),
        P("设文档长 $L$、块长 $s$、重叠 $o$、步长 $\\text{step} = s - o$，"
          "答案是一个长 $a$ 的连续片段，起点在文档里近似均匀分布。"
          "块的起点是 $0, \\text{step}, 2\\,\\text{step}, \\dots$"),
        DUAL(
            "答案能完整落进第 $i$ 个块，"
            "当且仅当它的起点 $p$ 满足"
            "$i \\cdot \\text{step} \\le p$ 且 $p + a \\le i \\cdot \\text{step} + s$。"
            "<strong>也就是说，每个块提供了一段长 $s - a + 1$ 的「安全区」</strong>，"
            "而相邻块的起点相差 $\\text{step}$。"
            "<em>安全区盖不满的那部分，就是答案必然被切断的位置。</em>",
            "把它写出来："
            "$$\\text{intact}(s, o, a) = "
            "\\begin{cases} 0, & s < a \\\\ "
            "\\min\\!\\left(1, \\dfrac{s - a + 1}{s - o}\\right), & s \\ge a \\end{cases}$$"
            "<strong>notebook 第 2 节把它与穷举实测对拍，误差在 $10^{-3}$ 量级</strong>"
            "（差异只来自文档两端的边界效应）。",
        ),
        H3("三个立刻可用的推论"),
        OL([
            "<strong>要让完整率达到 1，重叠必须满足 $o \\ge a - 1$。</strong>"
            "<em>把 $\\min$ 里的分式设为 $\\ge 1$ 解一下即可。</em>"
            "<strong>也就是说：重叠的正确取值只由最长答案的长度决定，和块大小无关。</strong>"
            "「重叠设块长的 10%」这个流行做法之所以经常不够，"
            "就是因为它把重叠绑在了错误的量上。",
            "<strong>达到完整率 1 的索引成本倍数是 $\\dfrac{s}{s - a + 1}$。</strong>"
            "<em>$s = 500, a = 50$ 时是 1.11 倍（很便宜）；"
            "$s = 100, a = 60$ 时是 2.44 倍；"
            "$s = 80, a = 70$ 时是 7.3 倍（这时候该换分块方式，而不是加重叠）。</em>",
            "<strong>$s < a$ 时完整率是 0，加多少重叠都没用。</strong>"
            "<em>这听起来显然，但它给出了块大小的硬下界：$s \\ge a$。</em>"
            "所以流程是先由最长答案定下界，再由纯度与成本定具体值。",
        ]),
        TABLE(["块长 s", "最长答案 a", "达到完整率 1 所需 o", "索引成本倍数 s/(s−a+1)"], [
            ["500", "50", "49", "<strong>1.11×</strong>（便宜，直接加）"],
            ["500", "200", "199", "1.66×"],
            ["200", "50", "49", "1.33×"],
            ["100", "60", "59", "2.44×"],
            ["80", "70", "69", "<strong>7.3×</strong>（别加重叠，换方案）"],
            ["40", "60", "—", "<strong>不可能</strong>（$s < a$）"],
        ]),
        CALLOUT("warn", "这张表的最后两行是重点。"
                        "<strong>当最长答案接近块长时，用重叠去救完整率的代价会爆炸。</strong>"
                        "<em>此时正确的动作是换分块方式（结构感知 / 父子块），"
                        "而不是继续调重叠。</em>"
                        "notebook 第 3 节把成本倍数画成曲线，拐点非常明显。"),
        H3("怎么知道 a"),
        P("$a$ 是<strong>可以测的</strong>，而且很便宜："
          "从你的评测集里取答案（或答案证据）的字符/token 长度，"
          "<em>取 95 分位数而不是最大值</em>——"
          "最大值通常是一个异常长的表格类答案，为它把重叠拉满不划算。"
          "<strong>把这个 P95 写进分块配置的注释里</strong>，"
          "它是整个配置唯一的自由输入。"),
    ])),

    # ============================================================== 4
    ("structure", "结构感知分块：用模块 01 拿到的东西", "".join([
        P("固定窗口的边界是任意的。"
          "而模块 01 已经把 <code>section_path</code> 与 <code>element_type</code> 拿到手了——"
          "<strong>用它们当边界，纯度会立刻改善，而且不花任何额外成本。</strong>"),
        ASCII("""
   结构感知分块的三条规则（按优先级）

   ① 绝不跨 element 边界切表格
      表格块 = 行转句（模块 01），一行一块或几行一块，永不与正文混合

   ② 优先在结构边界切：标题 > 段落 > 句子 > 字符
      这就是 RecursiveCharacterTextSplitter 的分隔符优先级列表在做的事

   ③ 每个块继承它所在的 section_path，并把它**拼进块的文本**
      块文本 = "第三章 / 报销制度\\n\\n餐饮报销的单次上限是 200 元。"
      ↑ 这一步让「章节名里的词」也参与检索——
        用户问「报销制度里餐饮怎么规定」时，章节名提供了关键的匹配信号
"""),
        DUAL(
            "第三条常被忽略，但它的收益/成本比是本模块最高的。"
            "<strong>标题里的词往往正是用户查询里的词</strong>，"
            "而正文里可能一次都没出现。"
            "<em>把 section_path 拼进块文本，等于给每个块免费加了一组关键词。</em>"
            "代价是每个块多了十几个字符。",
            "形式化地看，这是一次<span class=\"term\">上下文增强</span>："
            "块的可检索表示从 $\\text{emb}(c)$ 变成 "
            "$\\text{emb}(\\text{path}(c) \\oplus c)$。"
            "<strong>注意它同时改变了两件事</strong>："
            "召回（好事，多了匹配信号）与"
            "<em>同章节块之间的相似度</em>（副作用——同一章的块彼此变得更像，"
            "可能挤占 top-k 的多样性）。"
            "<em>所以路径要短：只拼最近一两级，不要拼整棵树。</em>",
        ),
        H3("主题纯度怎么测：用文档自己的结构，不要用相似度"),
        P("纯度需要一个可计算的定义。一个看起来很自然的选择是"
          "<em>「块内句子两两相似度的平均值」</em>——"
          "<strong>但它在实践中不好用</strong>："
          "同一小节里的两句话（「餐饮报销上限 200 元」与「交通报销需提供发票」）"
          "共享的表层词很少，相似度并不比跨小节的两句高。"
          "<em>这个代理依赖嵌入模型的质量，而它本身正是我们要评估的东西之一。</em>"),
        P("本课用一个<strong>精确、不依赖任何模型</strong>的定义："),
        MATH(r"\text{cross}(C) = \frac{|\{c \in C : |\text{sections}(c)| > 1\}|}{|C|},"
             r"\qquad \text{purity} = 1 - \text{cross}(C)"),
        DUAL(
            "也就是<strong>「有多少比例的块跨越了文档自己的结构边界」</strong>。"
            "<em>文档作者已经把主题边界标出来了（标题、小节），"
            "跨越它就是把两个主题混进了一个块。</em>"
            "<strong>这个量是算术，不是测量——没有噪声，可以直接进门禁。</strong>",
            "它有一个明显的性质：<strong>结构感知分块的 cross 恒为 0</strong>（按构造）。"
            "<em>所以「结构感知比固定窗口纯」这个对比在这个指标下是同义反复</em>——"
            "这正好说明了结构感知分块的价值来源："
            "<strong>它不是「更聪明」，而是直接把这个指标设成了最优。</strong>"
            "有意义的对比是<span class=\"term\">语义分块</span>——"
            "它不知道小节在哪，只能从相似度谷点猜；"
            "notebook 第 5 节量出它猜得有多准（本例约 1/3 的块跨了小节）。",
        ),
    ])),

    # ============================================================== 5
    ("semantic", "语义分块：在相似度的谷点切", "".join([
        P("语义分块的想法很直接：<strong>逐句算与下一句的相似度，"
          "在相似度的「谷点」切开</strong>——那里大概就是话题转换的地方。"),
        ASCII("""
   相邻句相似度序列

   sim
    │      ●───●         ●───●───●
    │     ╱     ╲       ╱         ╲
    │    ●       ●     ●           ●
    │             ╲   ╱             ╲
    │              ● ●               ●
    └──────────────┬─────────────────┬────────► 句序
                  谷点              谷点
                 （切）             （切）

   实现：sim_i = cos(emb(句i), emb(句i+1))
        切点 = { i : sim_i < 分位数(sims, q) }      q 常取 0.1~0.2
"""),
        TABLE(["方案", "边界质量", "成本", "什么时候用"], [
            ["<strong>固定窗口</strong>", "任意", "$O(n)$，零额外开销",
             "<strong>默认起点</strong>；结构信息缺失时也只能用它"],
            ["<strong>结构感知</strong>", "好（跟着文档自己的结构）", "$O(n)$，只需要解析元数据",
             "<strong>只要模块 01 做对了就该用</strong>——几乎没有理由不用"],
            ["<strong>语义分块</strong>", "在无结构长文本上最好",
             "$O(n)$ 次嵌入调用（<em>摄取时一次性</em>）",
             "长篇无标题文本（访谈记录、会议转录、爬取的网页正文）"],
            ["<strong>LLM 分块</strong>", "最好", "<strong>贵，且不确定</strong>",
             "很少值得；<em>如果一定要用，缓存结果并把它当解析的一部分固化下来</em>"],
        ]),
        CALLOUT("danger", "语义分块有一个容易被忽略的问题："
                          "<strong>它产生的块大小方差很大。</strong>"
                          "<em>一段话题连续的长篇会被切成一个巨大的块</em>，"
                          "而这个块可能装不进上下文预算，"
                          "也会在检索时因为稀释效应（第 7 节）而分数偏低。"
                          "<strong>所以语义分块必须配一个硬上限：超过 $s_{\\max}$ 就在内部再切。</strong>"),
        P("<strong>一条实用的结论</strong>："
          "在有结构的文档上（绝大多数企业文档），"
          "<em>结构感知分块的收益已经拿到了大部分，语义分块的边际收益很小</em>。"
          "把预算花在把模块 01 的解析做对上，回报比换分块算法高得多。"),
    ])),

    # ============================================================== 6
    ("parent-child", "父子块：让 precision 与完整率同时上升", "".join([
        P("前面所有讨论都假设<strong>「被检索的单元」和「被喂给模型的单元」是同一个东西</strong>。"
          "<em>放弃这个假设，三个竞争的量里有两个可以同时改善。</em>"),
        ASCII("""
   父子块（small-to-big）

   父块（喂给模型）           子块（进索引，被检索）
   ┌─────────────────────┐   ┌──────────────────┐
   │ 第三章 报销制度       │──►│ 子1: 餐饮报销...  │  ← 小、主题纯、
   │                     │   ├──────────────────┤    向量不被稀释
   │ 餐饮报销的单次上限是  │──►│ 子2: 差旅报销...  │
   │ 200 元。差旅报销的    │   ├──────────────────┤
   │ 单次上限是 3000 元。  │──►│ 子3: 提交时限...  │
   │ 所有报销需在 30 天内  │   └──────────────────┘
   │ 提交。               │
   └─────────────────────┘
        ▲                          │
        └──── 命中子块 → 返回父块 ──┘

   索引里存子块的向量，返回时按 parent_id 换成父块。
"""),
        DUAL(
            "为什么这样能同时改善两个量？因为<strong>它把「检索粒度」和「上下文粒度」解耦了</strong>。"
            "检索要小块（纯、不被稀释、precision 高）；"
            "喂模型要大块（答案完整、有上下文）。"
            "<em>把它们绑在一起是固定窗口方案的一个隐含约束，而这个约束是不必要的。</em>",
            "代价有三个，都要清楚："
            "<strong>① 上下文预算</strong>——返回父块意味着 token 用量按父/子的大小比放大，"
            "去重（同一个父块被多个子块命中）是必须的；"
            "<strong>② 存储</strong>——父块要另存一份（或存偏移量）；"
            "<strong>③ 归因</strong>——引用要指向命中的<em>子块</em>而不是父块，"
            "否则用户拿到一大段话却不知道具体依据在哪一句。"
            "<em>notebook 第 6 节把去重和归因都实现了。</em>",
        ),
        H3("三个变体，成本递增"),
        UL([
            "<strong>句窗口</strong>（sentence-window）：子块 = 一句，父块 = 该句 ± k 句。"
            "<em>最轻，不需要额外存储（父块由偏移量算出来）</em>。",
            "<strong>段落父块</strong>：子块 = 句/小段，父块 = 所在段落或小节。"
            "<em>最常用的一档。</em>",
            "<strong>摘要索引</strong>：子块 = 父块的 LLM 摘要，父块 = 原文。"
            "<em>召回质量最好，但摘要要花钱、要缓存、要跟着文档版本失效</em>——"
            "<strong>它是一个派生资产，必须进摄取流水线并带版本，"
            "否则文档更新后摘要会静默过期</strong>（模块 05 的问题）。",
        ]),
    ])),

    # ============================================================== 7
    ("dilution", "稀释效应：为什么大块的检索分数会偏低", "".join([
        P("这一节解释第 2 节「失败二」的机制，"
          "<strong>并给出一个反直觉的推论：把块做大不只是降低纯度，它还会降低召回本身。</strong>"),
        DUAL(
            "机制：块的向量是块内所有词的聚合。"
            "<strong>相关的那一句被无关的内容按比例摊薄了。</strong>"
            "<em>一个块里只有 1/5 的内容与查询相关时，"
            "它的相似度明显低于「只有那一句」的块</em>——"
            "于是它可能排不进 top-k，"
            "<strong>哪怕它确实包含答案</strong>。",
            "在词袋型嵌入下这可以算出来。"
            "设相关句的词向量为 $r$、无关内容为 $z$（与查询近似正交），"
            "块的未归一化向量是 $r + z$，归一化后与查询 $q$ 的相似度是"
            "$$\\cos = \\frac{\\langle r, q\\rangle}{\\|r + z\\|} "
            "\\approx \\frac{\\langle r, q\\rangle}{\\sqrt{\\|r\\|^2 + \\|z\\|^2}}$$"
            "<strong>分子不变，分母随无关内容的量增长</strong>——"
            "所以相似度大致按 $1/\\sqrt{1 + \\|z\\|^2/\\|r\\|^2}$ 衰减。"
            "<em>notebook 第 7 节把这条曲线量出来，并验证它比线性衰减慢</em>"
            "（这也是为什么大块不是灾难，只是次优）。",
        ),
        CALLOUT("intuition", "稀释效应给出了一个很实用的直觉："
                             "<strong>「把 top-k 从 3 加到 10」和「把块从 200 加到 600」"
                             "不是同一件事</strong>。"
                             "<em>前者只是多看几个候选；后者改变了候选的分数本身</em>，"
                             "会让真正相关的块与不相关的块之间的差距变小。"),
        P("<strong>父子块正是对稀释效应的直接回应</strong>："
          "让进索引的单元保持小（分数不被稀释），"
          "让喂给模型的单元保持大（上下文完整）。"
          "<em>这就是上一节能同时改善两个量的物理原因。</em>"),
    ])),

    # ============================================================== 8
    ("ab-gate", "分块的 A/B 与门禁：四个必须一起报的数", "".join([
        P("分块参数是本课里最容易被随手改、也最容易改坏的东西。"
          "<strong>纪律：分块参数进 spec、进指纹；任何改动跑同一套离线集，报四个数。</strong>"),
        TABLE(["数", "怎么算", "怎么读"], [
            ["<strong>intact</strong>", "答案完整落在单块内的比例（或用公式算）",
             "<strong>硬约束</strong>。低于阈值直接否决，不看其它三个数"],
            ["<strong>recall@k</strong>", "C11 的定义，不重复",
             "改分块的主要收益应当体现在这里"],
            ["<strong>n_chunks / 索引体积</strong>", "块数与向量总量",
             "成本；与 recall 的提升一起看性价比"],
            ["<strong>context_tokens@k</strong>", "top-k 拼起来的 token 数（父子块下会放大）",
             "<strong>这一项最常被漏报</strong>——"
             "父子块把 recall 提上去的同时可能让上下文翻倍（C33 的预算）"],
        ]),
        ASCII("""
   分块 A/B 报告模板

   spec: chunker=structure_aware  s=400  o=80  parent=section
   fingerprint: 7c2a91be          （参数变了指纹就变——C68-01）
   answer_len P95 = 62 字符        （o=80 ≥ a-1 ✓）

                        baseline(固定400/0)   candidate(结构400/80)
   intact                    0.87                 1.00   ← 硬约束达标
   recall@5                  0.71                 0.83
   n_chunks                 1,240                1,510   (+22%)
   context_tokens@5         1,980                2,310   (+17%)
   cross(跨小节块比例)       0.86                 0.00

   判读: recall +12pp，成本 +22% 索引 / +17% 上下文 → 接受
        （若 intact 未达标，无论 recall 多高都否决）
"""),
        H3("放进 CI 的三项检查"),
        OL([
            "<strong>确定性：<code>o >= answer_len_p95 - 1</code></strong>。"
            "<em>这一项是纯算术，误报率为零，可以直接阻断</em>"
            "（C68 模块 04 的分级）。",
            "<strong>确定性：块数与向量数一致，且每个块都有 "
            "<code>doc_id/version/chunk_index/section_path</code></strong>。"
            "<em>缺一项就阻断——模块 01 已经说过这些事后补不回来。</em>",
            "<strong>统计：recall@k 相对基线的变化超过阈值才算真的变了</strong>。"
            "阈值按 C68 模块 04 的三步走从方差推，<em>不要拍脑袋</em>。",
        ]),
        CALLOUT("warn", "最后一条纪律，也是最常被违反的："
                        "<strong>换分块方案必须重建全部索引，"
                        "而且不能与旧块混在一个索引里。</strong>"
                        "<em>混着的后果是同一份内容以两种粒度存在，"
                        "top-k 被同一段内容的两个版本占满</em>"
                        "（模块 01 第 5 节的近重复问题，只不过这次是自己造的）。"
                        "模块 05 会给出双索引 + 原子切换的做法。"),
    ])),

    # ============================================================== 9
    ("antipatterns", "分块的三个反模式", "".join([
        P("这三个都很常见，而且都会让前面八节的工作白做。"),
        TABLE(["反模式", "为什么有人这么做", "后果", "正确做法"], [
            ["<strong>把分块参数放在代码里而不是 spec 里</strong>",
             "「就一个数字，改起来方便」",
             "<em>指纹不变，两次评测看起来可比而实际不可比</em>；"
             "半年后没人知道当前索引是用什么参数建的",
             "参数进 spec、进指纹（C68 模块 01）；<strong>并把 <code>answer_len_p95</code> "
             "作为注释写在旁边</strong>——它是这组参数唯一的自由输入"],
            ["<strong>换了分块方案但复用旧索引</strong>",
             "「重建太慢，先增量迁移」",
             "<strong>同一份内容以两种粒度共存</strong>，"
             "top-k 被自己造的近重复占满（第 6 节的问题，只不过这次是自己造的）",
             "全量重建 + 双索引原子切换（模块 05 第 5 节）；"
             "<em>结构腐烂不能局部修</em>"],
            ["<strong>用 recall 的提升为分块改动辩护，但不报 intact</strong>",
             "recall 是大家都认的指标",
             "<em>intact 不达标时 recall 的提升可能来自「召回了更多碎片」</em>——"
             "而碎片拼不出完整答案",
             "<strong>intact 是硬约束，先看它；不达标就否决，不看 recall</strong>"],
        ]),
        CALLOUT("warn", "第三条值得展开，因为它是一个真实的指标误导："
                        "<strong>把块切小会让 recall@k 上升</strong>"
                        "（同样的 k，小块能覆盖更多不同的位置），"
                        "<em>但答案完整率同时下降</em>。"
                        "<strong>如果只报 recall，「把块切小」看起来是一次改进；"
                        "而端到端可能变差。</strong>"
                        "这就是为什么第 8 节要求四个数一起报，且 intact 排在第一位。"),
    ])),
]

NB = [
    md("""# 02 · 分块（三个竞争指标 / 完整率公式 / 结构感知 / 语义 / 父子块 / 稀释）

目标：把「块该多大」从口味问题变成**一次算术 + 一次测量**。

本 notebook 你会亲手实现：
1. **三个竞争指标随块大小的曲线** —— intact / purity / n_chunks
2. **答案完整率的精确公式** —— $\\min(1, (s-a+1)/(s-o))$，与穷举实测对拍
3. **重叠的饱和点与索引成本倍数** —— $o \\ge a-1$，成本 $s/(s-a+1)$
4. **结构感知分块** —— 主题纯度的改善，以及把 section_path 拼进块文本的收益
5. **语义分块** —— 相邻句相似度的谷点切分，以及它必须配硬上限的原因
6. **父子块** —— 让 precision 与完整率同时上升，含父块去重与子块级归因
7. **稀释效应** —— 相似度随无关内容量的 $1/\\sqrt{1+\\|z\\|^2/\\|r\\|^2}$ 衰减
8. **分块 A/B 报告与门禁**

> 心智模型：**分块要在「答案完整率 ≥ 阈值」这个硬约束下最小化成本。
> 而这个约束不需要试，可以算。**"""),

    md("""## 0 · 环境与语料

沿用模块 00/01 的玩具嵌入。语料换成一份有章节结构的长文档——
本模块需要「结构」这个输入。"""),

    code("""import os, re, json, math, hashlib
from collections import Counter, defaultdict

import numpy as np

DIM = 4096

def tokenize(text):
    text = text.lower()
    toks = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\\u4e00-\\u9fff]+', text):
        toks += list(run)
        toks += [run[i:i + 2] for i in range(len(run) - 1)]
    return toks

def embed(text, dim=DIM):
    v = np.zeros(dim)
    for tok in tokenize(text):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

def cos(a, b):
    return float(np.dot(a, b))

# 一份带章节结构的文档：(section_path, 句子列表)
DOC = [
    ('第一章 休假制度 / 年假', [
        '正式员工每年享有 15 天带薪年假。',
        '试用期员工每年享有 5 天带薪年假。',
        '年假需提前三个工作日申请。',
        '未使用的年假可结转至次年第一季度。',
        '年假申请由直属主管审批。']),
    ('第一章 休假制度 / 病假', [
        '病假每年累计不超过 15 天。',
        '连续病假超过三天需提供医疗证明。',
        '病假期间按基本工资的百分之八十发放。',
        '长期病假需提交劳动能力鉴定材料。']),
    ('第一章 休假制度 / 婚育假', [
        '婚假为 10 天，需在登记后一年内使用。',
        '产假按当地规定执行，最少 158 天。',
        '陪产假为 15 天。',
        '育儿假每年 10 天，子女三岁以内适用。']),
    ('第二章 报销制度 / 日常报销', [
        '餐饮报销的单次上限是 200 元。',
        '交通报销需提供正规发票。',
        '所有报销需在费用发生后 30 天内提交。',
        '单笔超过 500 元的报销需附说明。',
        '现金报销一律不予受理。']),
    ('第二章 报销制度 / 差旅报销', [
        '差旅报销的单次上限是 3000 元。',
        '跨省差旅需提前填写出行申请。',
        '住宿标准按城市分为三档。',
        '国际差旅需提前十个工作日报备。']),
    ('第二章 报销制度 / 报销审批', [
        '报销单由部门负责人一级审批。',
        '超过五千元的报销需财务复核。',
        '审批时限为三个工作日。',
        '被驳回的报销单可在补充材料后重新提交。']),
    ('第三章 设备管理 / 更换周期', [
        '笔记本电脑的更换周期是 36 个月。',
        '显示器的更换周期是 48 个月。',
        '移动设备的更换周期是 24 个月。',
        '外设不设固定更换周期，按损坏情况处理。']),
    ('第三章 设备管理 / 报修与借用', [
        '设备损坏需在两个工作日内报修。',
        '临时借用设备最长期限为 30 天。',
        '借用需填写设备借用单并由资产管理员登记。',
        '遗失设备需按残值赔偿。']),
    ('第四章 信息安全 / 账号与密码', [
        '密码长度不得少于 12 位。',
        '密码需每 90 天更换一次。',
        '账号不得共享给他人使用。',
        '离职时需交回所有权限凭证。']),
    ('第四章 信息安全 / 数据外发', [
        '外发文件必须经过审批。',
        '客户数据不得存放在个人设备上。',
        '涉密文件外发需加密并单独传递口令。',
        '数据外发记录保存两年。']),
    ('第五章 绩效与培训 / 绩效考核', [
        '考核周期为每半年一次。',
        '考核结果分为五档。',
        '申诉需在结果公布后 5 个工作日内提出。',
        '连续两次考核不合格将启动改进计划。']),
    ('第五章 绩效与培训 / 培训预算', [
        '每位员工每年有 2000 元培训预算。',
        '新员工入职培训为期 5 天。',
        '外部课程需部门负责人批准。',
        '培训预算不可跨年结转。']),
]

QA = {
    '正式员工每年享有多少天带薪年假':   '正式员工每年享有 15 天带薪年假。',
    '餐饮报销的单次上限是多少':         '餐饮报销的单次上限是 200 元。',
    '差旅报销的单次上限是多少':         '差旅报销的单次上限是 3000 元。',
    '笔记本电脑的更换周期是多久':       '笔记本电脑的更换周期是 36 个月。',
    '病假期间工资怎么发':               '病假期间按基本工资的百分之八十发放。',
    '密码最短多少位':                   '密码长度不得少于 12 位。',
    '培训预算每年多少钱':               '每位员工每年有 2000 元培训预算。',
    '绩效申诉的时限是多久':             '申诉需在结果公布后 5 个工作日内提出。',
    '临时借用设备最长多久':             '临时借用设备最长期限为 30 天。',
    '陪产假有多少天':                   '陪产假为 15 天。',
}

FLAT = ''.join(''.join(sents) for _, sents in DOC)

# 小节在 FLAT 里的字符区间 —— 第 1/4/5 节的「跨结构边界率」要用
SECTION_BOUNDS = []
_pos = 0
for _path, _sents in DOC:
    _n = len(''.join(_sents))
    SECTION_BOUNDS.append((_path, _pos, _pos + _n))
    _pos += _n

# 句子在 FLAT 里的字符区间 —— 第 5 节语义分块要用
SENT_SPANS = []
_pos = 0
for _path, _sents in DOC:
    for _s in _sents:
        SENT_SPANS.append((_pos, _pos + len(_s), _s, _path))
        _pos += len(_s)

ANSWER_LENS = sorted(len(a) for a in QA.values())
A_P95 = ANSWER_LENS[int(0.95 * (len(ANSWER_LENS) - 1))]
print(f'文档 {len(FLAT)} 字符 · {len(DOC)} 个小节 · {len(SENT_SPANS)} 句 · {len(QA)} 个问答')
print(f'答案长度: {ANSWER_LENS}')
print(f'→ P95 = {A_P95}')
print()
print('A_P95 是本模块唯一的自由输入：重叠该设多少完全由它决定（第 3 节会证明）。')"""),

    md("""## 1 · 三个竞争指标随块大小的曲线

`intact` 上升、`purity` 下降、`n_chunks` 下降——**方向互相冲突，所以必须先定约束。**"""),

    code("""def fixed_chunks(text, size, overlap=0):
    step = max(1, size - overlap)
    return [text[i:i + size] for i in range(0, len(text), step)]

def fixed_spans(text, size, overlap=0):
    step = max(1, size - overlap)
    return [(i, min(i + size, len(text))) for i in range(0, len(text), step)]

def intact_rate(chunks, answers):
    return sum(1 for a in answers if any(a in c for c in chunks)) / len(answers)

def sections_touched(start, end, bounds=None):
    bounds = SECTION_BOUNDS if bounds is None else bounds
    return [p for p, a, b in bounds if start < b and end > a]

def cross_rate(spans):
    \"\"\"跨越文档自己的结构边界的块比例。纯算术，无噪声。\"\"\"
    return sum(1 for a, b in spans if len(sections_touched(a, b)) > 1) / len(spans)

print(f"{'块大小':>7}{'intact':>9}{'cross':>8}{'n_chunks':>10}")
rows = []
for size in [30, 60, 120, 240, 480]:
    ch = fixed_chunks(FLAT, size)
    sp = fixed_spans(FLAT, size)
    it, cr = intact_rate(ch, QA.values()), cross_rate(sp)
    rows.append((size, it, cr, len(ch)))
    print(f'{size:>7}{it:>9.2f}{cr:>8.2f}{len(ch):>10}')

intacts = [r[1] for r in rows]; crosses = [r[2] for r in rows]; ns = [r[3] for r in rows]
assert intacts[0] < intacts[-1], 'intact 应当随块变大而上升'
assert crosses[0] < crosses[-1], 'cross（越低越好）应当随块变大而恶化'
assert ns[0] > ns[-1], 'n_chunks 应当随块变大而下降'
assert all(intacts[i] <= intacts[i + 1] for i in range(len(intacts) - 1)), 'intact 应当单调'
print('\\n✅ 三个量的方向确实互相冲突：')
print(f'   块 30 → 480：intact {intacts[0]:.2f}→{intacts[-1]:.2f}（好），'
      f'cross {crosses[0]:.2f}→{crosses[-1]:.2f}（坏），n {ns[0]}→{ns[-1]}（好）')
print('   所以「块该多大」没有唯一答案，只有「在约束下的最优」。')
print()
print('   诚实说明：cross 在这份 761 字符的小语料上不是严格单调的')
print(f'   （size=240 时只有 {ns[3]} 个块，一个块的进出就让比例跳动 25 个点）。')
print('   趋势是清楚的，但小样本上的单点数值不要当结论——这本身也是一条评测纪律。')"""),

    md("""## 2 · 答案完整率的精确公式

$$\\text{intact}(s,o,a)=\\begin{cases}0,&s<a\\\\ \\min\\left(1,\\dfrac{s-a+1}{s-o}\\right),&s\\ge a\\end{cases}$$

与穷举实测对拍。**误差只来自文档两端的边界效应。**"""),

    code("""def intact_formula(s, o, a):
    if s < a:
        return 0.0
    return min(1.0, (s - a + 1) / (s - o))

def intact_exhaustive(s, o, a, doclen=20000):
    \"\"\"穷举答案的每个可能起点，看有没有块能完整装下它。\"\"\"
    step = max(1, s - o)
    starts = list(range(0, doclen, step))
    ok = tot = 0
    for p in range(doclen - a + 1):
        tot += 1
        ok += any(b <= p and p + a <= b + s for b in starts)
    return ok / tot

print(f"{'s':>5}{'o':>5}{'a':>4}{'公式':>9}{'穷举':>9}{'差':>9}")
worst = 0.0
for s, o, a in [(24, 0, 8), (24, 12, 8), (120, 0, 15), (120, 0, 40),
                (50, 10, 20), (50, 25, 20), (30, 0, 30), (20, 0, 30)]:
    f = intact_formula(s, o, a); e = intact_exhaustive(s, o, a)
    worst = max(worst, abs(f - e))
    print(f'{s:>5}{o:>5}{a:>4}{f:>9.4f}{e:>9.4f}{abs(f - e):>9.4f}')

assert worst < 5e-3, f'公式与穷举的最大偏差 {worst}'
assert intact_formula(20, 0, 30) == 0.0, 's < a 时完整率是 0'
assert intact_formula(24, 12, 8) == 1.0, 'o >= a-1 时完整率是 1'
print(f'\\n✅ 公式与穷举最大偏差 {worst:.5f}（只来自文档两端）。')
print('   有了它，「重叠设多少」不需要试——可以算。')"""),

    md("""## 3 · 饱和点与索引成本倍数

两个推论：
- 完整率达到 1 ⟺ $o \\ge a-1$（**只由最长答案决定，与块大小无关**）
- 达到 1 的索引成本倍数 = $s/(s-a+1)$（**a 接近 s 时爆炸**）"""),

    code("""# --- 3a. 饱和点 ---
a = 20
print(f'最长答案 a={a}，块长 s=100，扫重叠：')
print(f"{'o':>5}{'intact 公式':>13}{'达到 1?':>9}")
sat = None
for o in range(0, 40, 4):
    v = intact_formula(100, o, a)
    if v >= 1.0 and sat is None:
        sat = o
    print(f'{o:>5}{v:>13.4f}{"是" if v >= 1 else "":>9}')
print(f'\\n首次达到 1 的 o = {sat}（理论 a-1 = {a - 1}，步长 4 → 落在 {sat}）')
assert intact_formula(100, a - 1, a) >= 1.0
assert intact_formula(100, a - 2, a) < 1.0
# 与块大小无关
for s in [60, 100, 200, 500]:
    assert intact_formula(s, a - 1, a) >= 1.0 and intact_formula(s, a - 2, a) < 1.0
print(f'✅ 饱和点恒为 o = a-1 = {a - 1}，在 s=60/100/200/500 上都成立——与块大小无关。')
print('   所以「重叠设块长的 10%」这个流行做法把重叠绑在了错误的量上。')"""),

    code("""# --- 3b. 索引成本倍数 ---
def cost_multiplier(s, a):
    \"\"\"达到完整率 1 所需的块数相对于无重叠时的倍数 = s / (s-a+1)。\"\"\"
    if s < a:
        return float('inf')
    return s / (s - a + 1)

print(f"{'块长 s':>8}{'答案 a':>8}{'需要 o':>8}{'成本倍数':>10}{'判读':>22}")
for s, a_ in [(500, 50), (500, 200), (200, 50), (100, 60), (80, 70), (40, 60)]:
    m = cost_multiplier(s, a_)
    o_need = a_ - 1 if s >= a_ else None
    tag = ('不可能（s<a）' if m == float('inf') else
           ('便宜，直接加' if m < 1.5 else
            ('可接受' if m < 3 else '别加重叠，换方案')))
    ms = '∞' if m == float('inf') else f'{m:.2f}×'
    print(f'{s:>8}{a_:>8}{str(o_need):>8}{ms:>10}{tag:>22}')

# 验证成本倍数与实际块数一致
L = 20000
for s, a_ in [(500, 50), (200, 50), (100, 60)]:
    n_base = len(range(0, L, s))
    n_full = len(range(0, L, s - (a_ - 1)))
    ratio = n_full / n_base
    assert abs(ratio - cost_multiplier(s, a_)) / cost_multiplier(s, a_) < 0.02, (s, a_, ratio)
print('\\n✅ 成本倍数公式与实际块数吻合（误差 < 2%）。')
print('   注意 s=80/a=70 那一行：7.3 倍。此时正确动作是换分块方式，而不是继续调重叠。')"""),

    md("""## 4 · 结构感知分块

两件事：
1. 按 `section_path` 切 → 主题纯度改善
2. **把 section_path 拼进块文本** → 章节名里的词也参与检索"""),

    code("""def structure_chunks(doc, max_size=240, with_path=True):
    \"\"\"按小节切；小节超长则在句边界继续切。返回 [(text, section_path, start, end)]。\"\"\"
    out = []
    pos = 0
    for path, sents in doc:
        buf, buf_start = '', pos
        for s_ in sents:
            if buf and len(buf) + len(s_) > max_size:
                out.append((buf, path, buf_start, buf_start + len(buf)))
                buf_start += len(buf); buf = ''
            buf += s_
        if buf:
            out.append((buf, path, buf_start, buf_start + len(buf)))
        pos += len(''.join(sents))
    if with_path:
        out = [(f'{p}\\n{t}', p, a, b) for t, p, a, b in out]
    return out

struct4 = structure_chunks(DOC, 240, with_path=False)
struct_texts = [t for t, _, _, _ in struct4]
struct_spans = [(a, b) for _, _, a, b in struct4]
fixed_240 = fixed_chunks(FLAT, 240)
fixed_240_spans = fixed_spans(FLAT, 240)

print(f"{'方案':<18}{'块数':>6}{'cross':>8}{'intact':>9}")
for label, texts, spans in [('固定窗口 240', fixed_240, fixed_240_spans),
                            ('结构感知 240', struct_texts, struct_spans)]:
    print(f'{label:<18}{len(texts):>6}{cross_rate(spans):>8.2f}'
          f'{intact_rate(texts, QA.values()):>9.2f}')

# 每个块的原文都能被 span 还原 —— provenance 自检
for t, _, a, b in struct4:
    assert FLAT[a:b] == t, (a, b)
assert cross_rate(struct_spans) == 0.0, '结构感知分块的 cross 恒为 0（按构造）'
assert cross_rate(fixed_240_spans) > 0.0, '固定窗口必然跨小节'
print(f'\\n✅ cross: 固定窗口 {cross_rate(fixed_240_spans):.2f} → 结构感知 0.00。')
print('   注意这个对比在这个指标下是**同义反复**——结构感知分块直接把它设成了最优。')
print('   这不是缺陷，恰恰是它的价值来源：它不需要「更聪明」，只需要用文档已有的结构。')
print('   有意义的对比在第 5 节：语义分块不知道小节在哪，只能猜，看它猜得多准。')"""),

    code("""# --- section_path 拼进块文本的收益 ---
def search(cands, query, k=3):
    mat = np.stack([embed(t) for t in cands])
    s = mat @ embed(query)
    order = np.argsort(-s)[:k]
    return [(int(i), float(s[i])) for i in order]

# 一个只有章节名里才有关键词的查询
PATH_Q = '报销制度里餐饮怎么规定'
GOLD_SENT = '餐饮报销的单次上限是 200 元。'

no_path = [t for t, _, _, _ in structure_chunks(DOC, 240, with_path=False)]
with_path = [t for t, _, _, _ in structure_chunks(DOC, 240, with_path=True)]

for label, cands in [('不拼 path', no_path), ('拼 path', with_path)]:
    hits = search(cands, PATH_Q, k=1)
    idx, sc = hits[0]
    got = GOLD_SENT in cands[idx]
    print(f'{label:<10} top1 相似度 {sc:.3f} | 命中含答案的块 {got}')

s_no = search(no_path, PATH_Q, k=1)[0][1]
s_wi = search(with_path, PATH_Q, k=1)[0][1]
assert s_wi > s_no, '拼 path 应当提升相似度'

# 副作用：同章节的块彼此更像 —— 用「同章节块对的平均相似度」量
def intra_section_sim(chunks, paths):
    tot, cnt = 0.0, 0
    E = [embed(c) for c in chunks]
    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            if paths[i].split(' / ')[0] == paths[j].split(' / ')[0]:
                tot += cos(E[i], E[j]); cnt += 1
    return tot / cnt

paths = [p for _, p, _, _ in structure_chunks(DOC, 240, with_path=False)]
iss_no = intra_section_sim(no_path, paths)
iss_wi = intra_section_sim(with_path, paths)
print(f'\\n同章节块对的平均相似度: 不拼 {iss_no:.3f} → 拼 {iss_wi:.3f}')
assert iss_wi > iss_no, '拼 path 会让同章节的块彼此更像（这是副作用）'
print('✅ 拼 path 提升了召回，但也让同章节的块彼此更像——')
print('   这会挤占 top-k 的多样性。所以 path 要短：只拼最近一两级，不要拼整棵树。')"""),

    md("""## 5 · 语义分块：谷点切分

逐句算与下一句的相似度，在低分位处切。
**必须配硬上限**——否则话题连续的长篇会变成一个巨大的块。"""),

    code("""def semantic_chunks_quantile(sent_spans, q=0.25, max_size=240):
    \"\"\"教科书版本：在相邻句相似度的低分位处切。返回 [(text, start, end)]。\"\"\"
    if len(sent_spans) < 2:
        a, b, t, _ = sent_spans[0]
        return [(t, a, b)]
    E = [embed(t) for _, _, t, _ in sent_spans]
    sims = [cos(E[i], E[i + 1]) for i in range(len(sent_spans) - 1)]
    thr = float(np.quantile(sims, q))
    out = []
    cs, ce, buf = sent_spans[0][0], sent_spans[0][1], sent_spans[0][2]
    for i, (a, b, t, _) in enumerate(sent_spans[1:]):
        if sims[i] <= thr or (b - cs) > max_size:
            out.append((buf, cs, ce)); cs, ce, buf = a, b, t
        else:
            ce, buf = b, buf + t
    out.append((buf, cs, ce))
    return out

# --- 退化情形 A：相似度大量为 0 → 分位数阈值恒为 0，q 这个旋钮完全失效 ---
E = [embed(t) for _, _, t, _ in SENT_SPANS]
sims = [cos(E[i], E[i + 1]) for i in range(len(SENT_SPANS) - 1)]
zero_frac = sum(1 for x in sims if x < 1e-9) / len(sims)
print(f'相邻句相似度里恰好为 0 的比例: {zero_frac:.1%}')
print('分位数阈值:', {q: round(float(np.quantile(sims, q)), 3)
                     for q in (0.02, 0.05, 0.10, 0.25, 0.50)})
counts = {q: len(semantic_chunks_quantile(SENT_SPANS, q=q, max_size=10 ** 9))
          for q in (0.02, 0.05, 0.10, 0.25)}
print('不同 q 下的块数:', counts)
assert zero_frac > 0.2, '词袋型嵌入下大量相邻句相似度恰好为 0'
assert len(set(counts.values())) == 1, 'q 在 [0.02, 0.25] 上完全没有效果'
print(f'\\n⚠️ 退化 A：{zero_frac:.0%} 的相邻句相似度恰好为 0，'
      f'于是 q ∈ [0.02, 0.25] 的阈值全是 0，块数恒为 {list(counts.values())[0]}。')
print('   **q 这个旋钮在这份语料上完全失效**——它调的是分位数，而分位数被 0 占满了。')

# --- 退化情形 B：相似度全相等 → 分位数阈值 = 那个常数 → 处处切 ---
TEMPLATE_RUN, _pos = [], 0
for i in range(12):
    _t = f'第 {i} 条：报销需在 30 天内提交并附发票。'
    TEMPLATE_RUN.append((_pos, _pos + len(_t), _t, '模板条款'))
    _pos += len(_t)
run_sims = [cos(embed(TEMPLATE_RUN[i][2]), embed(TEMPLATE_RUN[i + 1][2]))
            for i in range(len(TEMPLATE_RUN) - 1)]
print(f'\\n高度模板化的连续条款，相邻句相似度: {round(run_sims[0], 3)} '
      f'(全部相等: {len(set(round(x, 6) for x in run_sims)) == 1})')
run_chunks = semantic_chunks_quantile(TEMPLATE_RUN, q=0.25, max_size=10 ** 9)
print(f'分位数版本切出 {len(run_chunks)} 块，最大 {max(len(t) for t, _, _ in run_chunks)} 字符')
assert len(set(round(x, 6) for x in run_sims)) == 1, '模板条款的相邻相似度应当全相等'
assert len(run_chunks) == len(TEMPLATE_RUN), '常数序列上分位数阈值让它处处切'
print('⚠️ 退化 B：相似度全相等时，分位数阈值就等于那个常数，')
print('   而判定用的是 <=，于是**每一句之间都被切开**——')
print('   本该是一整组条款的内容被切成了 12 个碎片。')
print('\\n   两个退化都不是实现 bug，是分位数阈值这个设计本身的性质：')
print('   **它假设相似度分布是连续且有区分度的，而真实文本经常不满足。**')"""),

    md("""### 修法：绝对阈值 + 双向硬约束

两个退化都源于「用分位数定阈值」。换成**绝对阈值**，再加 `min_size` / `max_size` 双向约束：

- `sim < thr_abs` 才算主题边界（不再依赖分布形状）
- `len(buf) >= min_size` 才允许切（防退化 B 的碎片化）
- `len(buf) > max_size` 强制切（防话题连续的长篇变成一个巨块）"""),

    code("""def semantic_chunks(sent_spans, thr_abs=0.05, min_size=30, max_size=240):
    \"\"\"绝对阈值 + 双向硬约束。返回 [(text, start, end)]。\"\"\"
    E = [embed(t) for _, _, t, _ in sent_spans]
    out = []
    cs, ce, buf = sent_spans[0][0], sent_spans[0][1], sent_spans[0][2]
    for i, (a, b, t, _) in enumerate(sent_spans[1:]):
        sim = cos(E[i], E[i + 1])
        force = (b - cs) > max_size
        boundary = sim < thr_abs and len(buf) >= min_size
        if force or boundary:
            out.append((buf, cs, ce)); cs, ce, buf = a, b, t
        else:
            ce, buf = b, buf + t
    out.append((buf, cs, ce))
    return out

sem = semantic_chunks(SENT_SPANS)
struct_as_spans = [(t, a, b) for t, _, a, b in struct4]
fixed_as_spans = [(FLAT[a:b], a, b) for a, b in fixed_240_spans]

print(f"{'方案':<22}{'块数':>6}{'大小 min/中位/max':>20}{'cross':>8}{'intact':>9}{'cv':>7}")
for label, ch in [('语义 v2（绝对阈值）', sem),
                  ('结构感知 240', struct_as_spans),
                  ('固定 240', fixed_as_spans)]:
    sizes = [len(t) for t, _, _ in ch]
    print(f'{label:<22}{len(ch):>6}'
          f'{f"{min(sizes)}/{int(np.median(sizes))}/{max(sizes)}":>20}'
          f'{cross_rate([(a, b) for _, a, b in ch]):>8.2f}'
          f'{intact_rate([t for t, _, _ in ch], QA.values()):>9.2f}'
          f'{np.std(sizes) / np.mean(sizes):>7.2f}')

# 模板条款上：v2 不再碎片化；无上限时会形成巨块，上限把它压住
run_nocap = semantic_chunks(TEMPLATE_RUN, max_size=10 ** 9)
run_capped = semantic_chunks(TEMPLATE_RUN, max_size=60)
print(f'\\n模板条款（12 句）: v2 无上限 → {len(run_nocap)} 块 '
      f'(最大 {max(len(t) for t, _, _ in run_nocap)} 字符)；'
      f'上限 60 → {len(run_capped)} 块 '
      f'(最大 {max(len(t) for t, _, _ in run_capped)} 字符)')

cv_sem = float(np.std([len(t) for t, _, _ in sem]) / np.mean([len(t) for t, _, _ in sem]))
cv_fix = float(np.std([len(t) for t, _, _ in fixed_as_spans]) /
               np.mean([len(t) for t, _, _ in fixed_as_spans]))
cross_sem = cross_rate([(a, b) for _, a, b in sem])

assert len(run_nocap) == 1, 'v2 在常数相似度上不再碎片化'
assert max(len(t) for t, _, _ in run_nocap) > 240, '无上限时会形成超大块'
assert max(len(t) for t, _, _ in run_capped) <= 60, '上限必须被遵守'
assert cv_sem > cv_fix, '语义分块的块大小方差仍然更大'
assert 0.0 < cross_sem < 1.0, '语义分块猜小节边界：既不全对也不全错'
print(f'\\n✅ 三个结论：')
print(f'   ① 绝对阈值修掉了两个退化：模板条款从 12 个碎片变回 1 块。')
print(f'   ② **max_size 不是可选项**：无上限时那 1 块有 '
      f'{max(len(t) for t, _, _ in run_nocap)} 字符，装不进预算，')
print('      而且会因为稀释效应（第 7 节）在检索时分数偏低。')
print(f'   ③ 块大小方差仍然更大（cv {cv_sem:.2f} vs 固定 {cv_fix:.2f}）——这是语义分块的固有性质。')
print()
print(f'   而 cross = {cross_sem:.2f}：语义分块靠相似度猜小节边界，猜对了约 {1 - cross_sem:.0%}。')
print('   结构感知直接读文档的结构，cross = 0。**这是本模块的实用结论**：')
print('   在有结构的文档上（绝大多数企业文档），把预算花在把模块 01 的解析做对上，')
print('   回报比换分块算法高得多。语义分块的位置是「无结构长文本」——')
print('   访谈记录、会议转录、爬取的网页正文。')"""),

    md("""## 6 · 父子块：precision 与完整率同时上升

子块进索引（小、不被稀释），父块喂模型（答案完整）。
含**父块去重**与**子块级归因**——两个必须做但常被漏掉的细节。"""),

    code("""def build_parent_child(doc, child_max=60, parent_max=240):
    \"\"\"返回 (children, parents)。
    children: [dict(text, parent_id, section_path, child_id)]
    parents:  {parent_id: dict(text, section_path)}\"\"\"
    parents, children = {}, []
    for path, sents in doc:
        buf, group = '', []
        def flush():
            nonlocal buf, group
            if not group:
                return
            pid = f'p{len(parents)}'
            parents[pid] = dict(text=buf, section_path=path)
            for j, s in enumerate(group):
                children.append(dict(text=s, parent_id=pid, section_path=path,
                                     child_id=f'{pid}c{j}'))
            buf, group = '', []
        for s in sents:
            if buf and len(buf) + len(s) > parent_max:
                flush()
            buf += s; group.append(s)
        flush()
    # 子块超长再切（本例句子都短，保留这条以示完整）
    out = []
    for c in children:
        if len(c['text']) <= child_max:
            out.append(c)
        else:
            for j in range(0, len(c['text']), child_max):
                d = dict(c); d['text'] = c['text'][j:j + child_max]
                d['child_id'] = f"{c['child_id']}s{j}"
                out.append(d)
    return out, parents

children, parents = build_parent_child(DOC)
print(f'{len(children)} 个子块 · {len(parents)} 个父块')

def retrieve_parent_child(children, parents, query, k=3):
    \"\"\"检索子块 → 换成父块 → 去重（保留最高分）→ 归因指向子块。\"\"\"
    mat = np.stack([embed(c['text']) for c in children])
    s = mat @ embed(query)
    order = np.argsort(-s)
    seen, out = set(), []
    for i in order:
        c = children[i]
        if c['parent_id'] in seen:
            continue                                  # 父块去重
        seen.add(c['parent_id'])
        out.append(dict(parent_text=parents[c['parent_id']]['text'],
                        cite_child=c['text'],          # 归因指向子块
                        score=float(s[i])))
        if len(out) == k:
            break
    return out

def retrieve_flat(chunks, query, k=3):
    mat = np.stack([embed(c) for c in chunks])
    s = mat @ embed(query)
    order = np.argsort(-s)[:k]
    return [dict(parent_text=chunks[i], cite_child=chunks[i], score=float(s[i]))
            for i in order]

def evaluate(retriever, k=3):
    \"\"\"返回 (答案命中率, 平均上下文字符数, 引用精确度)。
    引用精确度 = 被引用的那一小段里就含答案的比例。\"\"\"
    hit = cite_ok = 0
    ctx = []
    for q, gold in QA.items():
        res = retriever(q, k=k)
        ctx.append(sum(len(r['parent_text']) for r in res))
        if any(gold in r['parent_text'] for r in res):
            hit += 1
        if any(gold in r['cite_child'] for r in res):
            cite_ok += 1
    return hit / len(QA), float(np.mean(ctx)), cite_ok / len(QA)

flat_240 = fixed_chunks(FLAT, 240)
flat_60 = fixed_chunks(FLAT, 60)
print(f"\\n{'方案':<22}{'答案命中':>10}{'上下文字符':>12}{'引用精确度':>12}")
for label, r in [('固定 240（大块）', lambda q, k=3: retrieve_flat(flat_240, q, k)),
                 ('固定 60（小块）', lambda q, k=3: retrieve_flat(flat_60, q, k)),
                 ('父子块 60→240', lambda q, k=3: retrieve_parent_child(children, parents, q, k))]:
    h, c, ci = evaluate(r)
    print(f'{label:<22}{h:>10.0%}{c:>12.0f}{ci:>12.0%}')

h_big, c_big, ci_big = evaluate(lambda q, k=3: retrieve_flat(flat_240, q, k))
h_small, c_small, ci_small = evaluate(lambda q, k=3: retrieve_flat(flat_60, q, k))
h_pc, c_pc, ci_pc = evaluate(lambda q, k=3: retrieve_parent_child(children, parents, q, k))
h_pc5, c_pc5, _ = evaluate(lambda q, k=5: retrieve_parent_child(children, parents, q, k), k=5)
h_big5, c_big5, _ = evaluate(lambda q, k=5: retrieve_flat(flat_240, q, k), k=5)

assert h_pc >= h_big, '父子块的命中率不该低于大块方案'
assert h_pc > h_small, '父子块的命中率必须高于小块方案'
assert c_pc < c_big / 2, '父子块的上下文成本应当远低于大块方案'
assert ci_pc == h_pc, '每一次命中都应当带一个精确指向答案句的引用'
assert h_pc5 > h_big5 and c_pc5 < c_big5, 'k=5 时父子块同时更准更省'

print(f'\\n✅ 父子块的收益不是「命中率更高」，而是**同时拿到两边的好处**：')
print(f'   命中率 {h_pc:.0%}（= 大块的 {h_big:.0%}，远高于小块的 {h_small:.0%}）')
print(f'   上下文 {c_pc:.0f} 字符（≈ 小块的 {c_small:.0f}，只有大块 {c_big:.0f} 的 '
      f'{c_pc / c_big:.0%}）')
print(f'   引用精确度 {ci_pc:.0%}——每次命中都能指到具体那一句')
print(f'\\n   k=5 时差距更明显：父子块 {h_pc5:.0%} 命中 / {c_pc5:.0f} 字符，'
      f'大块 {h_big5:.0%} / {c_big5:.0f} 字符。')
print('\\n   两个必须做的细节（漏掉任一个收益就没了）：')
print('   ① **父块去重**——不同子块命中同一个父块时只返回一次，')
print('      否则上下文被同一段内容重复占满（模块 01 第 5 节的近重复，这次是自己造的）。')
print('   ② **归因指向子块**——引用给用户看的是那一句，不是一大段。')
print('      如果引用指向父块，用户拿到一整节却不知道依据在哪一句，等于没有引用。')"""),

    md("""## 7 · 稀释效应

块的向量 = 相关内容 + 无关内容的聚合。相似度按 $1/\\sqrt{1+\\|z\\|^2/\\|r\\|^2}$ 衰减——
**比线性慢，所以大块不是灾难，只是次优。**"""),

    code("""TARGET = '餐饮报销的单次上限是 200 元。'
FILLER = ['住宿标准按城市分为三档。', '跨省差旅需提前填写出行申请。',
          '设备损坏需在两个工作日内报修。', '年假需提前三个工作日申请。',
          '连续病假超过三天需提供医疗证明。', '交通报销需提供正规发票。',
          '显示器的更换周期是 48 个月。', '工位调整需提前一周申请。']
Q = '餐饮报销单次最多能报多少'

print(f"{'块内无关句数':>13}{'块长':>7}{'相似度':>9}{'相对基线':>10}{'1/sqrt 预测':>13}")
base = None
sims, preds = [], []
for n_filler in range(0, 9):
    text = TARGET + ''.join(FILLER[:n_filler])
    s = cos(embed(text), embed(Q))
    if base is None:
        base = s
    # 预测：||r||^2 与 ||z||^2 用「词数」近似（词袋嵌入下未归一化范数的平方 ≈ 词数）
    nr = len(tokenize(TARGET))
    nz = len(tokenize(''.join(FILLER[:n_filler])))
    pred = 1 / math.sqrt(1 + nz / nr)
    sims.append(s); preds.append(pred)
    print(f'{n_filler:>13}{len(text):>7}{s:>9.3f}{s / base:>10.3f}{pred:>13.3f}')

assert sims[-1] < sims[0], '无关内容越多，相似度越低'
rel = [s / base for s in sims]
# 衰减比线性慢：8 个 filler 时，相对值应当明显高于「线性摊薄」的预测
linear_pred = len(tokenize(TARGET)) / len(tokenize(TARGET + ''.join(FILLER)))
assert rel[-1] > linear_pred * 1.3, f'衰减应当比线性慢: {rel[-1]:.3f} vs 线性 {linear_pred:.3f}'
# 与 1/sqrt 预测的相关性
corr = float(np.corrcoef(rel, preds)[0, 1])
print(f'\\n相对相似度与 1/sqrt(1+nz/nr) 的相关系数 = {corr:.3f}')
assert corr > 0.95, '1/sqrt 模型应当很好地解释衰减'
print(f'✅ 稀释是 1/sqrt 型的（相关 {corr:.3f}），比线性摊薄（{linear_pred:.3f}）慢得多。')
print('   所以大块不会让相关块「掉出候选」，只是压缩了它与不相关块的差距。')
print('   父子块正是对这件事的直接回应：进索引的单元保持小，喂模型的单元保持大。')"""),

    md("""## ✏️ 练习 1：从约束反解分块参数

给定最长答案 `a`、目标完整率 `tau`、可接受的索引成本倍数上限 `max_cost`，
在候选块长里选出**成本最低的可行配置**。

实现 `solve_chunk_params(a, tau, max_cost, sizes)`，返回 `(s, o, cost)` 或 `None`。
规则：
- 对每个 `s`，取**最小**的 `o`（整数，`0 <= o < s`）使 `intact_formula(s,o,a) >= tau`
- 成本倍数定义为 `s / (s - o)`（相对无重叠时的块数倍数）
- 在 `cost <= max_cost` 的可行配置里选 `cost` 最小的；平局取 `s` 最大的"""),

    code("""def solve_chunk_params(a, tau, max_cost, sizes):
    \"\"\"返回 (s, o, cost) 或 None。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# a=20, tau=1.0 → 需要 o >= 19；s 越大成本越低
r = solve_chunk_params(20, 1.0, max_cost=2.0, sizes=[40, 100, 200, 500])
assert r is not None
s_, o_, c_ = r
assert o_ == 19, f'完整率 1 时应当恰好取 o=a-1=19，得到 {o_}'
assert s_ == 500, f'成本最低应当取最大的块，得到 {s_}'
assert abs(c_ - 500 / 481) < 1e-9

# 放松 tau → 需要的重叠更小
r2 = solve_chunk_params(20, 0.9, max_cost=2.0, sizes=[100])
assert r2[1] < 19, f'tau=0.9 时重叠应当更小，得到 {r2[1]}'
assert intact_formula(100, r2[1], 20) >= 0.9
assert intact_formula(100, r2[1] - 1, 20) < 0.9, '必须是最小可行的 o'

# 成本上限过紧 → 无解
assert solve_chunk_params(60, 1.0, max_cost=1.05, sizes=[80]) is None
# s < a 的块长必须被排除
r3 = solve_chunk_params(60, 1.0, max_cost=10.0, sizes=[40, 80])
assert r3[0] == 80, '块长小于答案长度的候选必须被排除'
print(f'✅ 练习 1 通过：a=20 tau=1.0 → s={s_} o={o_} 成本 {c_:.3f}×')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def solve_chunk_params(a, tau, max_cost, sizes):
    best = None
    for s in sizes:
        if s < a:
            continue                       # 硬下界：s >= a
        o_ok = None
        for o in range(0, s):
            if intact_formula(s, o, a) >= tau - 1e-12:
                o_ok = o; break           # 最小可行 o
        if o_ok is None:
            continue
        cost = s / (s - o_ok)
        if cost <= max_cost + 1e-12:
            cand = (cost, -s, s, o_ok)
            if best is None or cand < best:
                best = cand
    return None if best is None else (best[2], best[3], best[0])

r = solve_chunk_params(20, 1.0, max_cost=2.0, sizes=[40, 100, 200, 500])
assert r == (500, 19, 500 / 481) or (r[0] == 500 and r[1] == 19)
assert solve_chunk_params(20, 0.9, max_cost=2.0, sizes=[100])[1] < 19
assert solve_chunk_params(60, 1.0, max_cost=1.05, sizes=[80]) is None
assert solve_chunk_params(60, 1.0, max_cost=10.0, sizes=[40, 80])[0] == 80
print('✅ 参考答案 1 通过')
print('   这个函数是本模块的交付物：分块参数不再是拍出来的，而是从三个输入解出来的。')
print('   三个输入分别来自：评测集（a）、业务（tau）、预算（max_cost）。')"""),

    md("""## ✏️ 练习 2：结构感知分块 + 硬上限 + 完整 provenance

实现 `chunk_structured(doc, max_size, overlap)`：
- 按小节切；小节内超过 `max_size` 时**在句边界**继续切，并在续块之间保留 `overlap` 个字符
- 每个块必须带 `section_path` / `chunk_index` / `start` / `end`
- 返回 `[dict(text, section_path, chunk_index, start, end)]`，`start/end` 是**在 FLAT 里**的偏移"""),

    code("""def chunk_structured(doc, max_size=40, overlap=20):
    \"\"\"返回带完整 provenance 的块列表（start/end 是 FLAT 偏移）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
ch = chunk_structured(DOC, max_size=40, overlap=20)
assert all(set(c) >= {'text', 'section_path', 'chunk_index', 'start', 'end'} for c in ch)
assert all(len(c['text']) <= 40 for c in ch), '必须遵守硬上限'
# 绝不跨小节
paths = {c['section_path'] for c in ch}
assert paths == {p for p, _ in DOC}, paths
# 每个小节内 chunk_index 从 0 连续
for p in paths:
    idxs = sorted(c['chunk_index'] for c in ch if c['section_path'] == p)
    assert idxs == list(range(len(idxs))), (p, idxs)
# start/end 与 FLAT 原文一致
for c in ch:
    assert FLAT[c['start']:c['end']] == c['text'], c
# 有重叠：某小节被切成多块时，相邻块必须有交集
multi = [p for p in paths if sum(1 for c in ch if c['section_path'] == p) > 1]
assert multi, '至少有一个小节应当被切成多块'
for p in multi:
    cs = sorted((c for c in ch if c['section_path'] == p), key=lambda c: c['chunk_index'])
    assert cs[1]['start'] < cs[0]['end'], f'{p} 的相邻块应当有重叠'
print(f'✅ 练习 2 通过：{len(ch)} 个块，全部带完整 provenance，绝不跨小节')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def chunk_structured(doc, max_size=40, overlap=20):
    out = []
    base = 0                                  # 该小节在 FLAT 里的起点
    for path, sents in doc:
        full = ''.join(sents)
        bounds, pos = [], 0                   # 句边界（小节内偏移）
        for s_ in sents:
            pos += len(s_); bounds.append(pos)
        start, idx = 0, 0
        while start < len(full):
            limit = start + max_size
            cand = [b for b in bounds if start < b <= limit]
            end = max(cand) if cand else min(limit, len(full))
            out.append(dict(text=full[start:end], section_path=path,
                            chunk_index=idx,
                            start=base + start, end=base + end))
            idx += 1
            if end >= len(full):
                break
            start = max(start + 1, end - overlap)
        base += len(full)
    return out

ch = chunk_structured(DOC, max_size=40, overlap=20)
assert all(len(c['text']) <= 40 for c in ch)
assert {c['section_path'] for c in ch} == {p for p, _ in DOC}
for c in ch:
    assert FLAT[c['start']:c['end']] == c['text']
multi = [p for p in {c['section_path'] for c in ch}
         if sum(1 for c in ch if c['section_path'] == p) > 1]
for p in multi:
    cs = sorted((c for c in ch if c['section_path'] == p), key=lambda c: c['chunk_index'])
    assert cs[1]['start'] < cs[0]['end']
print('✅ 参考答案 2 通过')
print('   两个容易写错的地方：')
print('   ① 切点要在句边界，但**不能超过 max_size**——所以是「不超过上限的最大句边界」；')
print('   ② start = end - overlap 时要防止不前进（start+1 的保护），否则超长句会死循环。')"""),

    md("""## ✏️ 练习 3：父块去重与上下文预算

实现 `assemble_context(children, parents, query, k, budget)`：
- 检索子块，按父块去重（保留最高分的那个子块作为引用）
- 按分数从高到低往上下文里加**父块**，直到再加一个就超过 `budget` 字符为止
- 返回 `dict(context, citations, used_chars, dropped)`：
  `citations` 是被采纳的子块文本列表，`dropped` 是因预算被丢掉的父块数"""),

    code("""def assemble_context(children, parents, query, k=5, budget=300):
    \"\"\"返回 dict(context, citations, used_chars, dropped)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
r = assemble_context(children, parents, '餐饮报销的单次上限是多少', k=5, budget=300)
assert r['used_chars'] <= 300, r['used_chars']
assert len(r['citations']) == r['context'].count('\\n\\n') + 1 or r['citations']
assert '200 元' in r['context'], '预算内应当装进答案'
# 引用必须是子块（短），不是父块
assert all(len(c) <= 60 for c in r['citations']), '引用应当指向子块'
# 父块不重复
segs = r['context'].split('\\n\\n')
assert len(segs) == len(set(segs)), '父块必须去重'
# 预算收紧 → dropped 增加
r_tight = assemble_context(children, parents, '餐饮报销的单次上限是多少', k=5, budget=80)
r_loose = assemble_context(children, parents, '餐饮报销的单次上限是多少', k=5, budget=10000)
assert r_tight['dropped'] > r_loose['dropped'], (r_tight['dropped'], r_loose['dropped'])
assert r_loose['dropped'] == 0
print(f"✅ 练习 3 通过：预算 300 装了 {len(r['citations'])} 个父块 "
      f"({r['used_chars']} 字符)，丢了 {r['dropped']} 个")"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def assemble_context(children, parents, query, k=5, budget=300):
    mat = np.stack([embed(c['text']) for c in children])
    sc = mat @ embed(query)
    order = np.argsort(-sc)
    seen, ranked = set(), []
    for i in order:
        c = children[i]
        if c['parent_id'] in seen:
            continue
        seen.add(c['parent_id'])
        ranked.append((float(sc[i]), c))
        if len(ranked) == k:
            break
    picked, cites, used, dropped = [], [], 0, 0
    for _, c in ranked:
        ptext = parents[c['parent_id']]['text']
        if used + len(ptext) > budget:
            dropped += 1
            continue
        picked.append(ptext); cites.append(c['text']); used += len(ptext)
    return dict(context='\\n\\n'.join(picked), citations=cites,
                used_chars=used, dropped=dropped)

r = assemble_context(children, parents, '餐饮报销的单次上限是多少', k=5, budget=300)
assert r['used_chars'] <= 300 and '200 元' in r['context']
assert all(len(c) <= 60 for c in r['citations'])
segs = r['context'].split('\\n\\n')
assert len(segs) == len(set(segs))
assert assemble_context(children, parents, '餐饮报销的单次上限是多少', k=5,
                        budget=10000)['dropped'] == 0
print('✅ 参考答案 3 通过')
print('   注意 dropped 的语义：**跳过但继续尝试后面的**，而不是遇到超预算就停。')
print('   因为后面可能有更短的父块还装得下——停下来会浪费预算。')
print('   （真实系统里这一步之后交给 C33 的预算分配与截断。）')"""),

    md("""## ✏️ 练习 4：分块 A/B 报告 + 门禁（含一个适用条件的坑）

实现 `chunking_report(name, chunks, overlap, chunker)`，返回讲解第 8 节的四个数
（`intact` / `recall_at_5` / `n_chunks` / `context_chars_at_5`）+ `missing_provenance` + `cross`。

再实现 `chunking_gate(report, baseline, answer_len_p95, tau=1.0)`：
- **确定性阻断**：`intact < tau`；任一块缺 provenance 字段
- **确定性阻断，但只对 `chunker == 'fixed'` 生效**：`overlap < answer_len_p95 - 1`
- **统计报警**：`recall@5` 相对基线下降超过 3 个百分点

最后那个「只对 fixed 生效」是这道题的重点。**为什么？**
因为第 3 节的公式假设切点与答案边界无关。而结构感知分块切在**句边界**上，
如果答案本身就是完整句子，它的 intact 恒为 1——重叠对它毫无作用。
<strong>把一条有适用条件的规则写成无条件的，会让门禁在正确的配置上误报。</strong>"""),

    code("""def chunking_report(name, chunks, overlap, chunker):
    \"\"\"chunks: [dict(text, section_path, chunk_index, start, end)]（start/end 是 FLAT 偏移）。
    返回报告 dict，必须含 chunker 字段。\"\"\"
    # TODO
    raise NotImplementedError

def chunking_gate(report, baseline, answer_len_p95, tau=1.0):
    \"\"\"返回 (blocking, warnings)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def as_chunks(spans, chunker):
    \"\"\"把 (start, end) 列表包成带 provenance 的块（FLAT 坐标）。\"\"\"
    out = []
    for i, (a, b) in enumerate(spans):
        secs = sections_touched(a, b)
        out.append(dict(text=FLAT[a:b], section_path=' | '.join(secs),
                        chunk_index=i, start=a, end=b))
    return out

fixed_bad = as_chunks(fixed_spans(FLAT, 240, 0), 'fixed')          # o=0，不达标
fixed_ok = as_chunks(fixed_spans(FLAT, 240, A_P95 - 1), 'fixed')   # o=18，达标
struct_ok = as_chunks(struct_spans, 'structure')                   # 句边界，o 无关

r_fixed_bad = chunking_report('固定240/o=0', fixed_bad, 0, 'fixed')
r_fixed_ok = chunking_report('固定240/o=18', fixed_ok, A_P95 - 1, 'fixed')
r_struct = chunking_report('结构感知/o=0', struct_ok, 0, 'structure')

for r in (r_fixed_bad, r_fixed_ok, r_struct):
    print(f"{r['name']:<16} intact {r['intact']:.2f} | recall@5 {r['recall_at_5']:.2f} "
          f"| n {r['n_chunks']:>3} | ctx {r['context_chars_at_5']:>6.0f} "
          f"| cross {r['cross']:.2f}")

assert r_fixed_bad['intact'] < 1.0, '固定窗口 o=0 时答案会被切断'
assert r_fixed_ok['intact'] == 1.0, 'o >= a-1 时完整率必须是 1'
assert r_struct['intact'] == 1.0, '句边界分块下句子级答案恒完整'
assert r_struct['cross'] == 0.0 and r_fixed_bad['cross'] > 0.0

# 固定窗口 + 重叠不足 → 两项阻断（intact 与 overlap）
b1, w1 = chunking_gate(r_fixed_bad, r_fixed_ok, A_P95)
assert len(b1) == 2, f'应当同时命中 intact 与 overlap 两项: {b1}'
assert any('重叠' in x for x in b1) and any('完整率' in x for x in b1)

# 结构感知 + o=0 → **不该被 overlap 规则误报**
b2, w2 = chunking_gate(r_struct, r_fixed_ok, A_P95)
assert b2 == [], f'结构感知分块 o=0 不该被阻断: {b2}'

# 基线自比全绿
assert chunking_gate(r_fixed_ok, r_fixed_ok, A_P95) == ([], [])

# 缺 provenance → 阻断
broken = [dict(c) for c in fixed_ok]; del broken[0]['section_path']
b3, _ = chunking_gate(chunking_report('broken', broken, A_P95 - 1, 'fixed'),
                      r_fixed_ok, A_P95)
assert any('provenance' in x for x in b3), b3

# recall 下降 → 只报警
r_drop = dict(r_fixed_ok); r_drop['recall_at_5'] -= 0.10
b4, w4 = chunking_gate(r_drop, r_fixed_ok, A_P95)
assert b4 == [] and any('recall' in x for x in w4), (b4, w4)
print('\\n✅ 练习 4 通过：确定性项阻断、统计项报警，'
      '且 overlap 规则不会在句边界分块上误报')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
PROV_FIELDS = ('text', 'section_path', 'chunk_index', 'start', 'end')

def chunking_report(name, chunks, overlap, chunker):
    texts = [c['text'] for c in chunks]
    it = intact_rate(texts, QA.values())
    mat = np.stack([embed(t) for t in texts])
    hit, ctx = 0, []
    for q, gold in QA.items():
        order = np.argsort(-(mat @ embed(q)))[:5]
        top = [texts[i] for i in order]
        hit += any(gold in t for t in top)
        ctx.append(sum(len(t) for t in top))
    missing = sum(1 for c in chunks if not set(PROV_FIELDS) <= set(c))
    cross = sum(1 for c in chunks
                if 'start' in c and len(sections_touched(c['start'], c['end'])) > 1)
    return dict(name=name, chunker=chunker, intact=it, recall_at_5=hit / len(QA),
                n_chunks=len(chunks), context_chars_at_5=float(np.mean(ctx)),
                cross=cross / len(chunks), overlap=overlap,
                missing_provenance=missing)

def chunking_gate(report, baseline, answer_len_p95, tau=1.0):
    blocking, warn = [], []
    if report['intact'] < tau:
        blocking.append(f"答案完整率 {report['intact']:.2f} < {tau}")
    if report['missing_provenance']:
        blocking.append(f"{report['missing_provenance']} 个块缺 provenance 字段")
    # 只对与答案边界无关的切法生效 —— 这条规则有适用条件
    if report['chunker'] == 'fixed' and report['overlap'] < answer_len_p95 - 1:
        blocking.append(f"重叠 {report['overlap']} < 最长答案-1 "
                        f"({answer_len_p95 - 1})，完整率无法达到 1")
    drop = baseline['recall_at_5'] - report['recall_at_5']
    if drop > 0.03:
        warn.append(f"recall@5 下降 {drop:.1%}（> 3pp）")
    return blocking, warn

r_fixed_bad = chunking_report('固定240/o=0', fixed_bad, 0, 'fixed')
r_fixed_ok = chunking_report('固定240/o=18', fixed_ok, A_P95 - 1, 'fixed')
r_struct = chunking_report('结构感知/o=0', struct_ok, 0, 'structure')
assert r_fixed_bad['intact'] < 1.0 and r_fixed_ok['intact'] == 1.0
assert r_struct['intact'] == 1.0
assert len(chunking_gate(r_fixed_bad, r_fixed_ok, A_P95)[0]) == 2
assert chunking_gate(r_struct, r_fixed_ok, A_P95)[0] == []
assert chunking_gate(r_fixed_ok, r_fixed_ok, A_P95) == ([], [])
r_drop = dict(r_fixed_ok); r_drop['recall_at_5'] -= 0.10
assert chunking_gate(r_drop, r_fixed_ok, A_P95)[0] == []
print('✅ 参考答案 4 通过')
print('   这道题真正的内容是最后那个 if 里的 chunker 条件。')
print('   第 3 节的公式假设切点与答案边界无关——这个假设对固定窗口成立，')
print('   对句边界分块不成立（句子级答案永远完整）。')
print('   **把有适用条件的规则写成无条件的，门禁就会在正确的配置上误报，**')
print('   而误报是「门禁被关掉」这一结局最常见的起点（C68-04）。')"""),

    md("""## 🧪 真实工程胶囊：分块的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 参数从约束解出来，不是拍出来（讲解第 3 节）
# ══════════════════════════════════════════════════════════════════
#   1) 从评测集算 answer_len 的 P95（用 token 而不是字符，与 embedding 一致）
#   2) o = a_p95 - 1
#   3) s 由成本倍数 s/(s-a+1) <= max_cost 反解下界，再按 purity 挑
#   4) 三个数进 spec，进指纹（C68-01）

CHUNK_SPEC = {
    'chunker': 'structure_aware',
    'max_tokens': 400,
    'overlap_tokens': 62,          # = answer_len_p95 - 1，注释里写清来源
    'answer_len_p95': 63,          # ← 唯一的自由输入，来自评测集
    'parent': 'section',
    'child_max_tokens': 80,
}

# ══════════════════════════════════════════════════════════════════
# B. 结构感知：分隔符优先级 + 硬上限（讲解第 4/5 节）
# ══════════════════════════════════════════════════════════════════
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(
    separators=['\\n## ', '\\n### ', '\\n\\n', '\\n', '。', '，', ''],   # 从粗到细
    chunk_size=400, chunk_overlap=62,
    length_function=lambda t: len(tokenizer.encode(t)),   # ← 用 token 计长
)
# 表格不要走这里：模块 01 已经把它行转句了，一行一块

# ══════════════════════════════════════════════════════════════════
# C. section_path 拼进块文本（讲解第 4 节）—— 只拼最近一两级
# ══════════════════════════════════════════════════════════════════
chunk_text_for_embedding = f"{short_path(el['section_path'])}\\n{el['text']}"
#   注意：喂给模型的文本可以不含 path，但**进 embedding 的文本必须含**；
#   两者不同时，metadata 里要分别存。

# ══════════════════════════════════════════════════════════════════
# D. 父子块的存储布局（讲解第 6 节）
# ══════════════════════════════════════════════════════════════════
#   向量库里只存子块；父块存原文库（或只存 (doc_id, start, end) 偏移，按需取）
col.upsert(ids=[c['child_id'] for c in children],
           embeddings=model.encode([c['embed_text'] for c in children]).tolist(),
           metadatas=[{'parent_id': c['parent_id'], 'doc_id': c['doc_id'],
                       'version': c['version'], 'section_path': c['section_path'],
                       'start': c['start'], 'end': c['end']} for c in children])

def retrieve(q, k):
    hits = col.query(query_embeddings=[model.encode(q).tolist()], n_results=k * 4)
    seen, out = set(), []
    for h in zip(hits['ids'][0], hits['metadatas'][0], hits['distances'][0]):
        cid, meta, dist = h
        if meta['parent_id'] in seen:      # ① 父块去重
            continue
        seen.add(meta['parent_id'])
        out.append({'context': load_parent(meta),
                    'citation': load_span(meta),   # ② 归因指向子块
                    'score': 1 - dist})
        if len(out) == k:
            break
    return out

# ══════════════════════════════════════════════════════════════════
# E. CI（讲解第 8 节）
# ══════════════════════════════════════════════════════════════════
# 阻断（确定性）: overlap >= answer_len_p95 - 1
#                每个块都有 doc_id/version/chunk_index/section_path/start/end
#                向量数 == 块数
# 报警（统计）  : recall@k 相对基线的变化超过按方差推出的阈值
# 强制          : 换分块方案 → 重建全部索引，不与旧块共存（模块 05 的原子切换）
```

---

## 小结

| 结论 | 数字 / 公式 | 在哪一节 |
|---|---|---|
| 分块是有约束的优化，不是找一个「好」数字 | $\\min n$ s.t. $\\text{intact} \\ge \\tau$ | 讲解 1 |
| 答案完整率有精确解析式 | $\\min(1, (s-a+1)/(s-o))$，与穷举差 $10^{-4}$ | 第 2 节 |
| 重叠的正确取值只由最长答案决定 | $o \\ge a-1$，在 s=60…500 上都成立 | 第 3 节 |
| a 接近 s 时用重叠救完整率的代价爆炸 | $s/(s-a+1)$：s=80,a=70 → 7.3× | 第 3 节 |
| 结构感知分块几乎免费地改善纯度 | purity 提升，块数几乎不变 | 第 4 节 |
| section_path 拼进块文本提升召回，但压低多样性 | 同章节块对相似度上升 | 第 4 节 |
| 语义分块必须配硬上限 | 无上限时块大小变异系数远大于固定窗口 | 第 5 节 |
| 父子块让命中率与引用精确度同时达标 | 100% 命中 + 100% 引用精确 | 第 6 节 |
| 稀释是 $1/\\sqrt{\\cdot}$ 型的，比线性慢 | 与 $1/\\sqrt{1+n_z/n_r}$ 相关 > 0.95 | 第 7 节 |

下一模块：**03 · 查询侧改写与路由**——查询是流水线里唯一能在运行时改写的东西，
而第一个该问的问题是「这个查询到底该不该检索」。"""),
]
