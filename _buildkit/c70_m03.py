# -*- coding: utf-8 -*-
"""C70 模块 03 · 查询侧改写与路由。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（元数据是过滤的前提）与 02（父子块）；"
                 "C11 模块 01/03（BM25、混合检索、RRF）——本课直接用 RRF，不重新推导"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_query_side.ipynb'
                       '（路由：无关上下文对答案的实际伤害 / 三种改写的对比 / '
                       'HyDE 把查询搬到答案空间 / 多查询融合的方差缩减 / '
                       '过滤前置 vs 后置 / 向量检索对否定的失明 / '
                       '改写缓存的键设计 / 为什么不能用文档原句当评测查询）'),
    ("核心参考", "Gao et al., <em>Precise Zero-Shot Dense Retrieval without Relevance Labels</em>"
                 "（HyDE, ACL 2023）· "
                 "Cormack et al., <em>Reciprocal Rank Fusion</em>（SIGIR 2009）· "
                 "Ma et al., <em>Query Rewriting for Retrieval-Augmented LLMs</em>（EMNLP 2023）· "
                 "本课程 C11 模块 01/03 · C67（判分器：改写效果怎么评）· C68 模块 02（缓存键）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("four-actions", "查询侧的四个动作，顺序不能换", "".join([
        P("模块 01 和 02 决定了索引里有什么，而它们都是<strong>摄取时</strong>的决策——"
          "改一次要重建索引。"
          "<strong>查询是整条流水线里唯一可以在运行时、按请求、零成本回滚的东西。</strong>"
          "这让它成为迭代最快的一层。"),
        ASCII("""
   查询进来之后的四个动作（顺序不能换）

   用户查询
      │
      ├─① 路由 route ────► 这个查询该不该检索？该查哪个索引？
      │                    不该检索的直接放行，**不要注入噪声**
      ├─② 改写 rewrite ──► 补上下文（多轮）、消解指代、对齐文档用词
      │
      ├─③ 扩展 expand ───► 一个查询变多个（同义、子问题、HyDE），并行检索后融合
      │
      └─④ 过滤 filter ───► 元数据硬约束（租户、时效、章节、语言）
                            **必须在检索之前，不能在 top-k 之后**
      │
      ▼
   检索（C11 的地盘）
"""),
        DUAL(
            "为什么顺序不能换？<strong>因为每一步的输入是上一步的输出，"
            "而且它们的失败方式不同。</strong>"
            "<em>路由放在最前，因为「不该检索」的查询根本不需要后面三步；"
            "过滤放在最后但必须作用于检索之前</em>——"
            "它是一个作用在候选集上的硬约束，"
            "<strong>放到 top-k 之后就变成了「把已经算好的结果扔掉」，"
            "这是本模块第 5 节要量的一个具体错误。</strong>",
            "更准确地说，四个动作作用在不同的对象上："
            "① 作用在<span class=\"term\">请求</span>上（要不要走这条路）；"
            "② 作用在<span class=\"term\">查询文本</span>上（$q \\to q'$）；"
            "③ 作用在<span class=\"term\">查询集合</span>上（$q \\to \\{q_1, \\dots, q_m\\}$，"
            "然后需要一个融合算子把 $m$ 个排序合并成一个）；"
            "④ 作用在<span class=\"term\">候选集</span>上（$C \\to C \\cap F$）。"
            "<em>③ 与 ④ 的交换律不成立</em>——"
            "先融合再过滤和先过滤再融合会给出不同的 top-k，"
            "而<strong>正确的是后者</strong>（每一路都在同一个受约束的候选集上排序）。",
        ),
        CALLOUT("intuition", "有一条实用的判据可以决定「该不该在查询侧加东西」："
                             "<strong>如果这个改动可以只对 1% 的流量开启并在十分钟内关掉，"
                             "它就属于查询侧；否则它属于摄取侧。</strong>"
                             "<em>这也说明了为什么查询侧值得优先投入：它的实验成本最低。</em>"),
    ])),

    # ============================================================== 2
    ("routing", "路由：第一个问题是「该不该检索」", "".join([
        P("大多数 RAG 系统对所有查询都检索。"
          "<strong>这是一个默认值，不是一个决定</strong>，而它有真实的代价。"),
        TABLE(["查询类型", "例子", "检索的结果", "该怎么做"], [
            ["<strong>闲聊 / 元问题</strong>", "「你好」「你能做什么」",
             "召回一堆无关制度条款", "<strong>直接放行，不检索</strong>"],
            ["<strong>可自答的常识 / 计算</strong>", "「3000 除以 12 是多少」",
             "召回含数字的无关块，<em>反而可能把模型带偏</em>", "不检索"],
            ["<strong>需要外部知识</strong>", "「餐饮报销上限多少」",
             "正常工作", "检索"],
            ["<strong>多轮追问</strong>", "「那差旅呢」",
             "<strong>召回失败</strong>——「那差旅呢」几乎没有可匹配的信号",
             "<em>先改写成独立查询</em>（第 3 节），再检索"],
            ["<strong>跨库</strong>", "「上季度的销售数据」",
             "在文档库里找不到", "路由到结构化数据源"],
        ]),
        DUAL(
            "「不该检索却检索了」的伤害不是零。"
            "<strong>无关上下文会挤占预算，而且它带进来的具体数字与条款会成为干扰项。</strong>"
            "<em>notebook 第 1 节用一个「从上下文里取第一个数字」的规则型回答器把这件事量出来</em>——"
            "它是模型「被上下文带偏」这个真实行为的一个诚实的、可控的替身。",
            "路由本身是一个分类问题，而它的两类错误代价不对称："
            "<strong>漏检索（该查没查）的代价是答不上来；"
            "误检索（不该查却查了）的代价是注入噪声。</strong>"
            "<em>前者通常更严重</em>，所以路由器应当<strong>偏向检索</strong>——"
            "只在高置信度下才跳过。"
            "实现上最稳的一档是<span class=\"term\">规则 + 兜底</span>："
            "明确的闲聊/计算模式走规则跳过，其余全部检索；"
            "<em>不要一上来就用一个 LLM 分类器，它的误检索率你没有数据去估计</em>。",
        ),
    ])),

    # ============================================================== 3
    ("rewrite", "改写：三种做法与它们各自的边界", "".join([
        P("改写解决的是模块 00 里那个「词汇鸿沟」失败："
          "<strong>用户的问法和文档的写法不共享词</strong>。"),
        TABLE(["做法", "怎么做", "成本", "边界"], [
            ["<strong>同义词/别名表</strong>",
             "维护一张「用户词 → 文档词」的映射，字符串替换",
             "近零，可缓存",
             "<strong>只能覆盖你想到的词</strong>；但它对高频词的收益极高，"
             "<em>而且是唯一可以被审计和回滚到具体一行的做法</em>"],
            ["<strong>LLM 改写</strong>",
             "让模型把查询改成「文档里会怎么写」，或消解多轮指代",
             "一次额外调用，<em>必须缓存</em>",
             "<strong>会改变语义</strong>——「不含增值税」被改成「增值税」是真实发生的事故；"
             "所以改写结果要与原查询<em>并行检索后融合</em>，而不是替换"],
            ["<strong>HyDE</strong>（假设性文档嵌入）",
             "让模型先<em>编</em>一个答案，用这个假答案去检索",
             "一次额外调用",
             "把查询从「问句空间」搬到「答案空间」，"
             "<strong>对问答风格不匹配的语料收益最大</strong>；"
             "<em>但它会放大模型的知识偏见</em>——编出来的假答案含错误实体时会检索到错误的地方"],
        ]),
        DUAL(
            "HyDE 的机制值得单独说清楚，因为它常被误解成「让模型猜答案」。"
            "<strong>它真正做的是换一个嵌入的输入</strong>："
            "问句和陈述句在向量空间里的分布本来就不同"
            "（问句有疑问词、没有具体数值），"
            "<em>而文档全是陈述句</em>。"
            "<strong>用一个（可能错的）陈述句去检索，比用一个正确的问句更接近目标分布。</strong>",
            "notebook 第 3 节量了这件事："
            "原查询与目标文档的相似度只有 0.05，"
            "<strong>而一个「粗糙的、内容并不正确」的伪答案就把它拉到 0.87</strong>。"
            "<em>这正是 HyDE 的关键性质：伪答案不需要正确，只需要在正确的文体与词汇分布里。</em>"
            "<strong>推论：HyDE 的伪答案不该用高温度采样多个，也不该追求事实正确——"
            "它只需要像一段文档。</strong>",
        ),
        CALLOUT("warn", "改写的两条硬纪律："
                        "<strong>① 永远保留原查询作为并行的一路</strong>"
                        "（改写坏掉时还有兜底）；"
                        "<strong>② 改写器是 harness 的一部分，它的版本必须进指纹</strong>"
                        "（C68 模块 02）——"
                        "<em>换了改写 prompt 而指纹不变，两次评测就不可比而看起来可比。</em>"),
    ])),

    # ============================================================== 4
    ("multi-query", "多查询融合：为什么它降的是方差", "".join([
        P("一个改写有可能变好，也有可能变坏。"
          "<strong>多查询融合的价值不是「更好」，而是「更稳」</strong>——"
          "这个区别决定了怎么评估它。"),
        DUAL(
            "机制：$m$ 个改写各自检索，得到 $m$ 个排序，"
            "用 RRF 把它们合成一个。"
            "<strong>某一路改写偏了，它在融合里只占 $1/m$ 的权重；"
            "而所有路都同意的文档会被推到最前。</strong>"
            "<em>所以融合把「单次改写的运气」平均掉了。</em>",
            "RRF 的定义（C11 模块 03，此处只引用）："
            "$\\text{RRF}(d) = \\sum_{i=1}^{m} \\frac{1}{k_0 + \\text{rank}_i(d)}$，"
            "$k_0$ 常取 60。"
            "<strong>它只用排名不用分数</strong>，"
            "所以不同改写之间的分数尺度不需要对齐——"
            "<em>这正是它在多查询场景里比「分数加权平均」更实用的原因</em>。"
            "notebook 第 4 节量的是<strong>跨改写的召回率标准差</strong>："
            "单路的方差明显大于融合后的方差。",
        ),
        ASCII("""
   单路 vs 融合（示意）

   改写 A → recall 0.9  ┐
   改写 B → recall 0.5  ├─ RRF ─► recall 0.8，**但方差远小于单路**
   改写 C → recall 0.8  ┘

   单路: 均值 0.73，标准差 0.17   ← 你不知道线上会抽到哪一路
   融合: 0.80，标准差 ~0.03       ← 稳定

   注意: 融合后的均值**不一定**高于最好的那一路（0.9）。
        融合买的是「不会掉到 0.5」，不是「一定拿到 0.9」。
"""),
        CALLOUT("intuition", "这解释了一个常见的失望："
                             "<strong>「我加了多查询融合，最好情况下的效果反而降了」——"
                             "这是预期行为</strong>。"
                             "<em>如果你有办法可靠地挑出最好的那一路，就不需要融合；"
                             "而正因为挑不出来，融合才有价值。</em>"),
        P("<strong>成本</strong>：$m$ 路检索的延迟可以并行掉，但"
          "<em>嵌入调用与向量库查询的次数是 $m$ 倍</em>。"
          "实践中 $m = 3$（原查询 + 一个同义改写 + 一个 HyDE）是一个常见的甜点，"
          "<strong>而且这三路的失败模式互不相同</strong>——"
          "这比三个同类型改写更有价值。"),
    ])),

    # ============================================================== 5
    ("filter", "过滤：必须在检索之前", "".join([
        P("元数据过滤看起来是个实现细节，"
          "<strong>但「在检索之前过滤」和「在 top-k 之后过滤」是两个不同的算法，"
          "结果差别巨大。</strong>"),
        ASCII("""
   后置过滤（错）                     前置过滤（对）

   全库检索 top-10                    候选集 = 全库 ∩ 过滤条件
        │                                  │
        ▼                                  ▼
   在这 10 条里筛过滤条件              在受约束的候选集里检索 top-10
        │                                  │
        ▼                                  ▼
   **可能只剩 0-2 条**                 稳定拿到 10 条

   为什么: 如果满足过滤条件的文档只占全库 5%，
          那么全库 top-10 里期望只有 0.5 条满足条件。
"""),
        DUAL(
            "这个错误在小规模测试时常常不暴露，"
            "<strong>因为测试库里满足条件的文档占比很高</strong>。"
            "<em>上线后租户变多、时间窗变窄，占比一掉，top-k 就被清空了。</em>"
            "<strong>症状是「有些用户什么都搜不到」，而检索层没有任何报错。</strong>",
            "定量地说：设满足过滤条件的文档占比 $\\phi$，"
            "且相关性与是否满足条件独立，"
            "则后置过滤后剩下的条数近似 $\\text{Binomial}(k, \\phi)$，"
            "<strong>期望 $k\\phi$，而 $P(\\text{一条都不剩}) = (1-\\phi)^k$</strong>。"
            "$k = 10, \\phi = 0.05$ 时这个概率是 <strong>0.60</strong>——"
            "<em>六成的请求会返回空</em>。"
            "notebook 第 5 节把这条曲线量出来。",
        ),
        H3("两个必须报警的事件"),
        UL([
            "<strong>过滤后候选集为空或过小</strong>——"
            "<em>这通常意味着过滤条件写错了（模块 01 第 5 节：过滤是硬约束，没有中间状态）</em>。"
            "报警而不是静默返回空。",
            "<strong>过滤条件里出现了非预期的字段值</strong>——"
            "比如租户 ID 是 <code>None</code>。"
            "<em>这类值在「过滤」语义下会静默匹配到全部或全不匹配，"
            "而前者是一次跨租户泄漏</em>（模块 05）。",
        ]),
        CALLOUT("danger", "多租户场景下这一条是安全边界，不是性能优化："
                          "<strong>租户过滤必须在检索之前，且必须是不可绕过的默认值</strong>——"
                          "<em>由调用方「记得传 tenant」的设计，"
                          "等于把一次泄漏的距离缩短到一行漏写的代码</em>。"),
    ])),

    # ============================================================== 6
    ("negation", "向量检索对否定与数值约束几乎失明", "".join([
        P("这一节是一个能力边界，"
          "<strong>而认清它比试图修它更重要</strong>。"),
        P("「包含增值税的发票」与「<strong>不</strong>包含增值税的发票」"
          "在向量空间里几乎是同一个点。"
          "notebook 第 6 节量出来的相似度是 <strong>0.94</strong>——"
          "<em>一个「不」字改变了全部语义，却几乎不改变向量。</em>"),
        DUAL(
            "原因不难理解：<strong>嵌入是词的聚合，"
            "而否定词是一个短词，它对聚合结果的贡献很小</strong>。"
            "<em>本课的玩具嵌入把这个问题放大了，"
            "但真实的句嵌入模型在否定上确实也弱</em>——"
            "这是一个被反复报告的已知局限（Kassner &amp; Schütze, "
            "<em>Negated and Misprimed Probes</em>, ACL 2020 一线），不是实现问题。",
            "同样失明的还有<strong>数值与时间的比较</strong>："
            "「超过 5000 元的合同」与「不超过 5000 元的合同」、"
            "「2024 年之后生效」与「2024 年之前生效」。"
            "<em>向量空间没有序关系</em>。"
            "<strong>结论很直接：否定、数值区间、时间窗、集合成员——"
            "这四类约束必须走结构化过滤，不能指望嵌入。</strong>",
        ),
        TABLE(["约束类型", "向量检索", "正确做法"], [
            ["<strong>否定</strong>（「不含 X」）", "几乎失明（cos ≈ 0.94）",
             "把否定项抽出来，作为<em>排除过滤器</em>"],
            ["<strong>数值区间</strong>（「超过 5000」）", "无序关系",
             "抽成 <code>where amount > 5000</code>"],
            ["<strong>时间窗</strong>（「今年的」）", "无序关系",
             "抽成 <code>effective_date</code> 范围（模块 01 的元数据）"],
            ["<strong>集合成员</strong>（「只看 A 部门」）", "只能靠词共现，不可靠",
             "抽成 <code>where dept in (...)</code>"],
        ]),
        P("<strong>所以查询侧的第一步其实是一次「结构抽取」</strong>："
          "把查询里的硬约束抽出来变成过滤器，剩下的语义部分交给向量检索。"
          "<em>这也是为什么模块 01 的元数据必须抽全——"
          "抽不到的字段，这里就没有可用的过滤器。</em>"),
    ])),

    # ============================================================== 7
    ("cost-cache", "查询侧的成本与缓存键", "".join([
        P("改写与 HyDE 都要额外调用模型。"
          "<strong>查询侧的缓存命中率通常很高（用户的问法高度重复），"
          "所以缓存是这一层最划算的一件事。</strong>"),
        ASCII("""
   查询侧缓存的键（漏一项就会读到旧结果）

   key = sha256(
       原始查询,                    ← 显然
       路由决策版本,                ← 路由规则改了，结论可能变
       改写器标识 + prompt 哈希,     ← **最常被漏的一项**
       同义词表版本,
       模型 ID + 温度,              ← 温度 > 0 时改写结果不确定
       扩展路数 m,
   )

   注意: 温度 > 0 的改写**不该缓存单次结果**，
        要么固定温度为 0，要么缓存「一组」改写并整组复用。
"""),
        DUAL(
            "这与 C68 模块 02 的缓存键是同一条纪律，"
            "只是对象从「评测配置」换成了「查询处理配置」。"
            "<strong>失败症状也一样：改了 prompt 而分数一点不变，"
            "然后被误读成「这个改动没有效果」。</strong>",
            "还有一个查询侧特有的成本项："
            "<strong>扩展 $m$ 路会让向量库的 QPS 变成 $m$ 倍</strong>。"
            "<em>这在延迟上可以并行掉，但在容量上不能</em>——"
            "$m = 3$ 意味着向量库要按三倍流量做容量规划。"
            "<strong>所以 $m$ 是一个必须写进容量文档的参数，不只是一个效果旋钮。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("eval", "查询侧的评测：不能用文档原句当查询", "".join([
        P("这是本模块最容易被忽略、后果最严重的一条。"),
        DUAL(
            "构造评测集最省事的做法是：<strong>从文档里挑一句话，"
            "把它改成一个问题，作为查询。</strong>"
            "<em>这样构造出来的查询与目标文档共享大量词</em>，"
            "<strong>于是词汇鸿沟这个失败在你的评测集上根本不存在</strong>——"
            "而它在真实流量里是最常见的失败之一。",
            "后果是系统性的："
            "<strong>你会测出一个虚高的 recall，"
            "并且会得出「查询改写没有收益」这个错误结论</strong>"
            "（因为在你的评测集上确实没有）。"
            "<em>这是一个典型的评测集与目标分布不匹配</em>——"
            "与 C68 模块 05 的「离线-在线不匹配」是同一类问题，"
            "只不过这里的不匹配是<strong>构造方式带来的，一开始就在里面</strong>。",
        ),
        H3("三条构造纪律"),
        OL([
            "<strong>查询必须来自真实用户，或至少是「不看文档的人」写的</strong>。"
            "<em>看着文档写问题的人会不自觉地用文档的词。</em>",
            "<strong>每个问题准备 2–3 个改述</strong>（paraphrase），"
            "并<em>分别报分</em>。"
            "<strong>改述之间的分数差就是这个系统对表述的敏感度</strong>——"
            "它是查询侧改动最该关注的指标，比平均 recall 有信息量得多。",
            "<strong>专门留一个「跨词汇」子集</strong>："
            "问法与文档用词刻意不重叠。"
            "<em>查询侧的所有改动都应该在这个子集上看收益</em>；"
            "在整体集上看会被大量「本来就能答对」的样本冲淡。",
        ]),
        CALLOUT("intuition", "一个便宜的自检："
                             "<strong>算一下你的评测查询与目标块的词重叠率。</strong>"
                             "<em>如果它显著高于真实流量的重叠率，你的评测集偏乐观了</em>，"
                             "而偏乐观的方向恰好掩盖了查询侧的价值。"
                             "notebook 第 8 节把这个自检实现成一个函数。"),
    ])),

    # ============================================================== 9
    ("multiturn", "多轮对话：查询侧最大的单项收益", "".join([
        P("前面八节都假设查询是独立的。"
          "<strong>而真实系统里大部分查询是多轮里的追问，"
          "而它们在检索上几乎是不可用的。</strong>"),
        ASCII("""
   用户: 餐饮报销上限是多少？
   系统: 200 元。
   用户: 那差旅呢？          ← 这个查询单独拿去检索，几乎没有可匹配的信号
                              「那」「呢」是停用词，只剩「差旅」两个字

   ❌ 直接检索 「那差旅呢」
      → 相似度极低，可能召回任何含「差旅」的块，也可能什么都召不回

   ✅ 先改写成独立查询
      history: [Q: 餐饮报销上限是多少 / A: 200 元]
      → 「差旅报销的上限是多少」
      → 正常检索
"""),
        DUAL(
            "<strong>指代消解是查询改写里收益最大的一项</strong>，"
            "而且它的收益与「同义词映射」是叠加的（两者解决不同的问题）。"
            "<em>它也是唯一一个「不做就完全不工作」的改写</em>——"
            "同义词缺失只是效果差一点，而指代不消解是直接失败。",
            "三个实现要点："
            "<strong>① 只用最近 2–3 轮</strong>——"
            "<em>历史越长，改写器越容易把早前的话题带进来</em>；"
            "<strong>② 改写后必须过第 3 节的安全检查</strong>"
            "（否定词、数字、长度），"
            "不过就退回「原查询 + 上一轮的问题」这个更笨但更安全的拼接；"
            "<strong>③ 缓存键要含历史的哈希</strong>——"
            "<em>同一句「那差旅呢」在不同历史下应当改写成不同的查询</em>，"
            "而这正是第 7 节缓存键最容易漏的一项。",
        ),
        H3("一个便宜的判别器"),
        P("不是所有追问都需要改写。"
          "<strong>判据：查询里的实词（去掉停用词后）少于两个，"
          "或者含明显的指代词（那、这、它、上面、刚才），就走改写。</strong>"
          "<em>其余直接检索</em>。"
          "这条规则的价值是把改写调用量压到一小部分请求上——"
          "而改写是查询侧唯一需要额外模型调用的动作。"),
    ])),

    # ============================================================== 10
    ("rollout", "查询侧的上线顺序", "".join([
        P("查询侧有五六个可以加的东西。"
          "<strong>顺序很重要，因为它们的收益/成本比差一个量级。</strong>"),
        TABLE(["顺序", "动作", "成本", "为什么排在这个位置"], [
            ["1", "<strong>多轮指代消解</strong>", "一次调用（只对追问）",
             "<strong>不做就完全不工作</strong>；而且它的收益不依赖其它任何一项"],
            ["2", "<strong>元数据过滤前置 + 空候选报警</strong>", "近零",
             "<em>它修的是正确性问题（含跨租户泄漏），不是效果问题</em>"],
            ["3", "<strong>同义词/别名表</strong>", "近零，可缓存",
             "可审计、可回滚到具体一行；<em>对高频词收益极高</em>"],
            ["4", "<strong>路由（只加 skip 规则）</strong>", "近零",
             "先只加规则并统计命中率，<strong>确认漏检索为 0 之后</strong>再考虑更复杂的"],
            ["5", "<strong>HyDE 或多查询融合</strong>", "m 倍调用与 QPS",
             "<em>放在最后，因为它们最贵</em>，而且收益要在「跨词汇子集」上才看得出来"],
            ["—", "<strong>LLM 路由分类器</strong>", "一次调用/请求",
             "<strong>通常不值得</strong>：它的误检索率你没有数据去估计，"
             "而规则路由已经拿到了大部分收益"],
        ]),
        CALLOUT("intuition", "这个顺序背后是一条通用判据："
                             "<strong>先做「不做就不工作」的，"
                             "再做「近零成本」的，最后做「按倍数花钱」的。</strong>"
                             "<em>而每一步都要在第 8 节的「跨词汇子集」上单独看收益</em>——"
                             "在整体集上看会被大量「本来就能答对」的样本冲淡。"),
    ])),

    # ============================================================== 11
    ("failures", "查询侧的五个失败模式与它们的信号", "".join([
        P("查询侧的失败几乎都不会报错。"
          "<strong>这一节给每一个配一个可观测的信号。</strong>"),
        TABLE(["失败", "用户看到的", "可观测信号", "在哪一节"], [
            ["<strong>改写把语义改了</strong>",
             "答案与问题无关，但读起来自信",
             "<em>改写前后的否定词/数字/长度差异</em>（这是确定性检查，零误报）",
             "第 3 节"],
            ["<strong>过滤条件写错</strong>",
             "「什么都搜不到」",
             "<strong>过滤后候选集大小</strong>；分租户看零结果率",
             "第 5 节"],
            ["<strong>路由误判</strong>",
             "问常识却答出制度条款",
             "<em>skip 与 retrieve 两条路径的分流比例</em>；"
             "<strong>它突然变化通常意味着有人改了规则</strong>",
             "第 2 节"],
            ["<strong>缓存读到旧结果</strong>",
             "「我改了 prompt 但一点变化都没有」",
             "<strong>缓存命中率</strong>——"
             "<em>改了改写器之后命中率没掉，就说明键里漏了它</em>",
             "第 7 节"],
            ["<strong>评测集偏乐观</strong>",
             "线上效果远差于离线",
             "<strong>评测查询与目标块的词重叠率</strong> vs 线上流量的重叠率",
             "第 8 节"],
        ]),
        DUAL(
            "第四行那个信号值得单独记住，因为它把一个难以察觉的 bug 变成了一次简单的对照："
            "<strong>改了改写器之后，缓存命中率必须掉下来。</strong>"
            "<em>没掉 → 键里漏了改写器标识 → 你读到的全是旧结果</em>。"
            "这比「检查代码写对了没有」可靠得多。",
            "第五行是本模块最难修的一个，因为<strong>它在你的指标里表现为「一切正常」</strong>。"
            "<em>唯一的办法是拿线上真实查询做对照</em>："
            "抽样 200 条线上查询，算它们与被召回块的词重叠率分布，"
            "与评测集的同一个分布比。"
            "<strong>两个分布差很远就说明评测集不代表线上</strong>——"
            "而这与 C68 模块 05 的「离线-在线不匹配」是同一类问题，"
            "只不过这里的不匹配是<em>构造方式带进来的，一开始就在里面</em>。",
        ),
    ])),

    # ============================================================== 12
    ("boundary", "查询侧的边界：什么不属于这一层", "".join([
        P("查询侧很容易变成一个什么都往里塞的地方。"
          "<strong>这一节划清它的边界。</strong>"),
        TABLE(["动作", "属不属于查询侧", "为什么"], [
            ["改写、扩展、路由、结构抽取", "<strong>属于</strong>",
             "它们只改变「送进检索的东西」，不改变索引，"
             "<em>可以按请求生效、十分钟内回滚</em>"],
            ["重排（cross-encoder / ColBERT）", "<strong>不属于</strong>",
             "它作用在<em>召回结果</em>上，属于检索层（C11 模块 03）；"
             "本课不重复"],
            ["上下文预算分配、截断、压缩", "<strong>不属于</strong>",
             "它作用在<em>组装阶段</em>，属于 C33；"
             "<strong>本课到「拿到 top-k」为止</strong>"],
            ["答案生成的 prompt 设计", "<strong>不属于</strong>",
             "它在检索之后；<em>把它和检索问题混在一起会让归因失效</em>"],
            ["同义词表的<em>维护流程</em>", "<strong>属于，但它是数据不是代码</strong>",
             "<strong>它应当有版本、有 owner、进缓存键</strong>（第 7 节）；"
             "<em>把它硬编码在代码里是一个常见的退化</em>"],
        ]),
        CALLOUT("warn", "第四行是一个真实的归因陷阱："
                        "<strong>「效果不好」时同时改检索和改生成 prompt，"
                        "然后效果变好了——你不知道是哪个起了作用。</strong>"
                        "<em>而下一次其中一个失效时，你也不知道该动哪个。</em>"
                        "这与 C68 模块 00 的可归因性是同一条："
                        "<strong>一次只动一层，并且每层都有自己的指标。</strong>"),
        P("<strong>本课在这条链上的位置</strong>："
          "模块 01/02 决定索引里有什么，"
          "模块 03（本模块）决定送进检索的查询长什么样，"
          "C11 决定怎么在索引里找，"
          "模块 04 决定要不要再查一轮，"
          "C33 决定召回的东西怎么装进窗口，"
          "模块 05 决定这一切在一年后还成不成立。"
          "<em>每一格都有自己的指标与门禁——这是本课全部八节的组织原则。</em>"),
    ])),
]

NB = [
    md("""# 03 · 查询侧改写与路由（路由 / 改写 / HyDE / 融合 / 过滤 / 否定 / 缓存 / 评测）

目标：把查询侧的四个动作变成**八个可测量的结论**。

本 notebook 你会亲手实现：
1. **路由** —— 无关上下文对答案的实际伤害，以及两类错误的不对称代价
2. **三种改写** —— 同义词表 / LLM 改写替身 / 语义漂移的事故
3. **HyDE** —— 伪答案**不需要正确**，只需要像一段文档
4. **多查询融合** —— 它降的是方差不是均值，用 RRF 量出来
5. **过滤前置 vs 后置** —— $(1-\\phi)^k$ 的空结果概率曲线
6. **否定与数值约束** —— 向量检索对它们几乎失明，必须走结构化
7. **查询侧缓存键** —— 漏一项就会读到旧结果
8. **评测集自检** —— 用文档原句当查询会让词汇鸿沟这个失败消失

> 心智模型：**查询是流水线里唯一能在运行时改写、按请求生效、十分钟内回滚的东西。
> 所以它的实验成本最低，值得优先投入。**"""),

    md("""## 0 · 环境与语料"""),

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

# 块 = (chunk_id, text, metadata)。metadata 是模块 01 抽出来的东西。
CHUNKS = [
    ('c01', '餐饮报销的单次上限是 200 元。',
     dict(section='报销', tenant='acme', year=2024, dept='all')),
    ('c02', '差旅报销的单次上限是 3000 元。',
     dict(section='报销', tenant='acme', year=2024, dept='all')),
    ('c03', '所有报销需在费用发生后 30 天内提交。',
     dict(section='报销', tenant='acme', year=2024, dept='all')),
    ('c04', '餐饮报销的单次上限是 150 元。',
     dict(section='报销', tenant='acme', year=2022, dept='all')),      # 旧版本
    ('c05', '正式员工每年享有 15 天带薪年假。',
     dict(section='休假', tenant='acme', year=2024, dept='all')),
    ('c06', '试用期员工每年享有 5 天带薪年假。',
     dict(section='休假', tenant='acme', year=2024, dept='all')),
    ('c07', '笔记本电脑的更换周期是 36 个月。',
     dict(section='设备', tenant='acme', year=2024, dept='it')),
    ('c08', '密码长度不得少于 12 位。',
     dict(section='安全', tenant='acme', year=2024, dept='it')),
    ('c09', '单笔金额超过 50 万元的合同需总经理签批。',
     dict(section='合同', tenant='acme', year=2024, dept='legal')),
    ('c10', '合同归档保存 10 年。',
     dict(section='合同', tenant='acme', year=2024, dept='legal')),
    ('c11', '外发文件必须经过审批。',
     dict(section='安全', tenant='acme', year=2024, dept='all')),
    ('c12', '每位员工每年有 2000 元培训预算。',
     dict(section='培训', tenant='acme', year=2024, dept='all')),
    # 另一个租户 —— 第 5 节的多租户过滤要用
    ('x01', '餐饮报销的单次上限是 80 元。',
     dict(section='报销', tenant='globex', year=2024, dept='all')),
    ('x02', '正式员工每年享有 10 天带薪年假。',
     dict(section='休假', tenant='globex', year=2024, dept='all')),
]

MAT = np.stack([embed(t) for _, t, _ in CHUNKS])
ID2I = {cid: i for i, (cid, _, _) in enumerate(CHUNKS)}

def retrieve(query, k=3, candidates=None):
    \"\"\"candidates: chunk_id 的集合；None 表示全库。返回 [(chunk_id, score)]。\"\"\"
    idx = ([ID2I[c] for c in candidates] if candidates is not None
           else list(range(len(CHUNKS))))
    if not idx:
        return []
    s = MAT[idx] @ embed(query)
    order = np.argsort(-s)[:k]
    return [(CHUNKS[idx[o]][0], float(s[o])) for o in order]

print(f'{len(CHUNKS)} 个块 · {len({m["tenant"] for _, _, m in CHUNKS})} 个租户')
print('检索「餐饮报销上限」:', retrieve('餐饮报销的上限是多少', k=3))"""),

    md("""## 1 · 路由：无关上下文的实际伤害

回答器是一个规则替身：**从上下文里取第一个数字**。
这是「模型被上下文带偏」这个真实行为的一个可控、可观测的模型。"""),

    code("""def answer_first_number(context):
    m = re.search(r'\\d+', context)
    return m.group(0) if m else None

# 三个不需要检索的查询 —— 答案与语料无关
NO_RETRIEVAL = {
    '3000 除以 12 等于多少': '250',
    '一年有多少个月':         '12',
    '一天有多少小时':         '24',
}

def answer_without_retrieval(q):
    \"\"\"不检索：直接算（这里用查表替身）。\"\"\"
    return NO_RETRIEVAL[q]

def answer_with_retrieval(q, k=3):
    \"\"\"检索后把 top-k 拼成上下文，再取第一个数字。\"\"\"
    hits = retrieve(q, k=k)
    ctx = ''.join(dict(zip([c for c, _, _ in CHUNKS],
                          [t for _, t, _ in CHUNKS]))[cid] for cid, _ in hits)
    return answer_first_number(ctx)

print(f"{'查询':<20}{'不检索':>8}{'检索后':>8}{'正确答案':>10}")
n_ok_no, n_ok_yes = 0, 0
for q, gold in NO_RETRIEVAL.items():
    a_no = answer_without_retrieval(q)
    a_yes = answer_with_retrieval(q)
    n_ok_no += (a_no == gold); n_ok_yes += (a_yes == gold)
    print(f'{q:<20}{str(a_no):>8}{str(a_yes):>8}{gold:>10}')

print(f'\\n不检索正确率 {n_ok_no / len(NO_RETRIEVAL):.0%} | '
      f'一律检索正确率 {n_ok_yes / len(NO_RETRIEVAL):.0%}')
assert n_ok_no == len(NO_RETRIEVAL), '这些查询本来就答得对'
assert n_ok_yes < n_ok_no, '对不该检索的查询做检索会把答案带偏'
print('✅ 「一律检索」这个默认值对这类查询是净损害——它注入了具体但无关的数字。')"""),

    code("""# --- 路由器：规则 + 兜底，且刻意偏向检索 ---
SKIP_PATTERNS = [
    r'^\\s*(你好|您好|hi|hello)\\s*[。！!？?]*\\s*$',      # 闲聊
    r'[\\d]+\\s*(加|减|乘|除以|\\+|-|\\*|/)\\s*[\\d]+',      # 算术
    r'^(一年有多少个月|一天有多少小时)$',                  # 明确的常识
]

def route(query):
    \"\"\"返回 'skip' 或 'retrieve'。偏向 retrieve —— 漏检索比误检索更贵。\"\"\"
    for pat in SKIP_PATTERNS:
        if re.search(pat, query):
            return 'skip'
    return 'retrieve'

NEED_RETRIEVAL = ['餐饮报销的单次上限是多少', '正式员工年假多少天',
                  '密码最短多少位', '合同归档保存多久']
cases = [(q, 'skip') for q in NO_RETRIEVAL] + [(q, 'retrieve') for q in NEED_RETRIEVAL]
cases.append(('你好', 'skip'))

wrong_skip = wrong_retrieve = 0
for q, want in cases:
    got = route(q)
    if got != want:
        (globals().__setitem__('wrong_skip', wrong_skip + 1) if want == 'retrieve'
         else globals().__setitem__('wrong_retrieve', wrong_retrieve + 1))
    print(f'{q:<22} 期望 {want:<9} 实际 {got:<9} {"✓" if got == want else "✗"}')

miss = sum(1 for q, want in cases if want == 'retrieve' and route(q) == 'skip')
over = sum(1 for q, want in cases if want == 'skip' and route(q) == 'retrieve')
print(f'\\n漏检索（该查没查）{miss} 个 | 误检索（不该查却查了）{over} 个')
assert miss == 0, '漏检索的代价更高，路由器必须先保证这一项为 0'
print('✅ 规则路由器的正确设计目标是「漏检索为 0」，而不是「总准确率最高」。')
print('   两类错误的代价不对称：漏检索 → 答不上来；误检索 → 注入噪声。')
print('   所以先用规则覆盖明确的跳过模式，其余全部检索——')
print('   不要一上来就用 LLM 分类器，它的误检索率你没有数据去估计。')"""),

    md("""## 2 · 改写（一）：同义词表与语义漂移事故

同义词表便宜、可审计、可回滚到具体一行。
但**任何改写都可能改变语义**——这一节把那个事故做出来。"""),

    code("""SYNONYM = {'吃饭': '餐饮', '最多能花': '单次上限是', '休假': '年假',
           '出差': '差旅', '电脑': '笔记本电脑'}

def rewrite_synonym(q, table=SYNONYM):
    out = q
    for user_word, doc_word in table.items():
        out = out.replace(user_word, doc_word)
    return out

GAP_CASES = {
    '吃饭最多能花多少钱':   'c01',
    '出差最多能花多少钱':   'c02',
    '电脑多久换一次':       'c07',
}
print(f"{'原查询':<20}{'改写后':<26}{'原 top1':>10}{'改写 top1':>11}")
before = after = 0
for q, gold in GAP_CASES.items():
    q2 = rewrite_synonym(q)
    t1 = retrieve(q, k=1)[0][0]
    t2 = retrieve(q2, k=1)[0][0]
    before += (t1 == gold); after += (t2 == gold)
    print(f'{q:<20}{q2:<26}{t1:>10}{t2:>11}')
print(f'\\ntop1 命中: 改写前 {before}/{len(GAP_CASES)} → 改写后 {after}/{len(GAP_CASES)}')
assert after > before, '同义词改写应当提升命中'

# --- 语义漂移事故 ---
DRIFT_TABLE = {'不含增值税': '增值税'}      # 一个真实会发生的坏映射
bad_q = '不含增值税的发票怎么处理'
print(f'\\n语义漂移: 「{bad_q}」 → 「{rewrite_synonym(bad_q, DRIFT_TABLE)}」')
print('   「不含」被吃掉了——改写把否定丢了，语义反转。')
assert '不含' not in rewrite_synonym(bad_q, DRIFT_TABLE)
print('✅ 所以纪律是：**改写永远不替换原查询，而是作为并行的一路**（第 4 节融合）。')"""),

    md("""## 3 · 改写（二）：HyDE —— 伪答案不需要正确

HyDE 换的不是「问对问题」，而是**换一个更接近文档分布的嵌入输入**。
关键实验：一个**内容并不正确**的粗糙伪答案，也能把相似度拉起来。"""),

    code("""TARGET = '餐饮报销的单次上限是 200 元。'
Q = '吃饭最多能花多少钱'

VARIANTS = [
    ('原查询（问句）',       Q),
    ('同义词改写（仍是问句）', rewrite_synonym(Q)),
    ('粗糙伪答案（内容错）',  '餐饮报销的单次上限是若干元。'),
    ('更差的伪答案（数字错）', '餐饮报销的单次上限是 500 元。'),
    ('理想伪答案（内容对）',  TARGET),
]
print(f"{'嵌入输入':<24}{'与目标块的相似度':>18}{'top1':>8}")
sims = {}
for label, text in VARIANTS:
    s = cos(embed(text), embed(TARGET))
    sims[label] = s
    print(f'{label:<24}{s:>18.3f}{retrieve(text, k=1)[0][0]:>8}')

s_q = sims['原查询（问句）']
s_rough = sims['粗糙伪答案（内容错）']
s_wrongnum = sims['更差的伪答案（数字错）']
assert s_rough > 5 * s_q, f'粗糙伪答案应当远好于原查询: {s_rough:.3f} vs {s_q:.3f}'
assert s_wrongnum > 5 * s_q, '连数字都写错的伪答案也一样有效'
print(f'\\n✅ 原查询 {s_q:.3f} → 粗糙伪答案 {s_rough:.3f}（{s_rough / s_q:.0f} 倍）。')
print(f'   连数字写错的伪答案也有 {s_wrongnum:.3f}——**伪答案不需要正确**。')
print('   它只需要在正确的文体与词汇分布里（陈述句、有单位、用文档的词）。')
print()
print('   两个推论：')
print('   ① HyDE 的伪答案不必用高温度采样多个，也不必追求事实正确；')
print('   ② 但它会放大模型的知识偏见——伪答案里出现错误**实体**时')
print('      （不是错误数字），会把检索带到错误的地方。所以仍然要保留原查询那一路。')"""),

    md("""## 4 · 多查询融合：它降的是方差

RRF 定义见 C11 模块 03，这里只用。
关键测量：**跨改写的召回率标准差**，单路 vs 融合。"""),

    code("""def rrf(rankings, k0=60, k=3):
    \"\"\"rankings: [[chunk_id, ...], ...]。返回融合后的 top-k。\"\"\"
    score = defaultdict(float)
    for r in rankings:
        for rank, cid in enumerate(r, start=1):
            score[cid] += 1.0 / (k0 + rank)
    return [cid for cid, _ in sorted(score.items(), key=lambda kv: -kv[1])[:k]]

# 一组「好坏不一」的改写器 —— 真实系统里你事先不知道哪个好
REWRITERS = {
    '原查询':          lambda q: q,
    '同义词':          lambda q: rewrite_synonym(q),
    'HyDE(粗糙)':      lambda q: rewrite_synonym(q).replace('多少钱', '若干元。'),
    '坏改写(丢主题词)':  lambda q: re.sub(r'吃饭|出差|电脑|休假|密码|合同', '', q),
}
EVAL = {'吃饭最多能花多少钱': 'c01', '出差最多能花多少钱': 'c02',
        '电脑多久换一次': 'c07', '休假有几天': 'c05',
        '密码要多长': 'c08', '合同要存多久': 'c10'}

# 用 k=1 而不是 k=3：这个语料只有 14 个块，k=3 时几乎所有方案都饱和到 1.0，
# 看不出任何差别。**指标饱和时的对比是没有信息量的**（C66-01 的老问题）。
K_FUSE = 1

def recall_at_k(rewriter, k=K_FUSE):
    hit = 0
    for q, gold in EVAL.items():
        got = [cid for cid, _ in retrieve(rewriter(q), k=k)]
        hit += gold in got
    return hit / len(EVAL)

singles = {name: recall_at_k(fn) for name, fn in REWRITERS.items()}
for name, r in singles.items():
    print(f'{name:<18} recall@{K_FUSE} = {r:.2f}')

def recall_fused(k=K_FUSE):
    hit = 0
    for q, gold in EVAL.items():
        rankings = [[cid for cid, _ in retrieve(fn(q), k=k * 3)]
                    for fn in REWRITERS.values()]
        hit += gold in rrf(rankings, k=k)
    return hit / len(EVAL)

fused = recall_fused()
vals = list(singles.values())
print(f'\\n单路: 均值 {np.mean(vals):.2f}  标准差 {np.std(vals):.3f}  '
      f'最好 {max(vals):.2f}  最差 {min(vals):.2f}')
print(f'融合: {fused:.2f}')

assert fused > min(vals), '融合必须明显好于最差的那一路'
assert fused >= np.mean(vals), '融合应当不低于单路均值'
assert fused < max(vals), '而且它**不保证**超过最好的那一路——本例就没有'
print(f'\\n✅ 融合 {fused:.2f}：高于均值 {np.mean(vals):.2f}、'
      f'远高于最差 {min(vals):.2f}，但**低于最好的单路 {max(vals):.2f}**。')
print('   这就是融合的真实性质：它买的是「不会掉到最差」，不是「拿到最好」。')
print('   而你事先并不知道线上会抽到哪一路——如果知道，就不需要融合了。')
print('   这也解释了一个常见的失望：「加了融合，最好情况反而降了」。这是预期行为。')
print()
print('   实践中 m=3（原查询 + 同义改写 + HyDE）是常见甜点，')
print('   关键不是路数多，而是**这三路的失败模式互不相同**：')
print('   原查询败于词汇鸿沟，同义改写败于表外词，HyDE 败于错误实体。')"""),

    md("""## 5 · 过滤：前置 vs 后置

后置过滤返回空的概率是 $(1-\\phi)^k$。
$k=10, \\phi=0.05$ 时是 **0.60**——六成请求返回空，而检索层不报错。"""),

    code("""def filter_ids(pred):
    return {cid for cid, _, m in CHUNKS if pred(m)}

def retrieve_prefilter(query, pred, k=3):
    return retrieve(query, k=k, candidates=filter_ids(pred))

def retrieve_postfilter(query, pred, k=3):
    hits = retrieve(query, k=k)                       # 先全库 top-k
    keep = filter_ids(pred)
    return [(cid, s) for cid, s in hits if cid in keep]

# 场景：这个用户只被授权看 legal 部门的文档（φ = 2/14）
IS_LEGAL = lambda m: m['dept'] == 'legal'
phi = len(filter_ids(IS_LEGAL)) / len(CHUNKS)
print(f'legal 部门的文档占全库 φ = {phi:.1%}')
Q5 = '餐饮报销的单次上限是多少'
print('全库 top3      :', [c for c, _ in retrieve(Q5, k=3)], '← 里面一条 legal 的都没有')
print('前置过滤 top3   :', retrieve_prefilter(Q5, IS_LEGAL, k=3))
print('后置过滤 top3   :', retrieve_postfilter(Q5, IS_LEGAL, k=3))
assert len(retrieve_prefilter(Q5, IS_LEGAL, k=3)) > 0, '前置过滤必须拿到结果'
assert len(retrieve_postfilter(Q5, IS_LEGAL, k=3)) == 0, '后置过滤在这里返回空'
print()
print('两者的区别不是「效果差一点」：')
print('  前置 → 「在你有权看的文档里，与这个问题最相关的是这两条」（哪怕相关性不高）')
print('  后置 → 「什么都没有」，而检索层不报错。')

# --- 空结果概率曲线 ---
print(f"\\n{'φ':>7}{'k=5 空结果概率':>16}{'k=10':>10}{'k=20':>10}")
for ph in [0.5, 0.2, 0.1, 0.05, 0.01]:
    row = [(1 - ph) ** k for k in (5, 10, 20)]
    print(f'{ph:>7.2f}{row[0]:>16.3f}{row[1]:>10.3f}{row[2]:>10.3f}')
assert abs((1 - 0.05) ** 10 - 0.5987) < 1e-3
print('\\n✅ φ=5%、k=10 时后置过滤有 60% 的请求返回空。')
print('   这个错误在测试库上常常不暴露——测试库里满足条件的占比很高。')
print('   上线后租户变多、时间窗变窄，φ 一掉，top-k 就被清空了。')"""),

    code("""# --- 两个必须报警的事件 ---
def retrieve_guarded(query, pred, k=3, min_candidates=3):
    cands = filter_ids(pred)
    alerts = []
    if len(cands) == 0:
        alerts.append('过滤后候选集为空——过滤条件很可能写错了')
    elif len(cands) < min_candidates:
        alerts.append(f'过滤后候选集只有 {len(cands)} 条（< {min_candidates}）')
    return retrieve(query, k=k, candidates=cands), alerts

# 事件一：条件写错 → 候选空
_, a1 = retrieve_guarded(Q5, lambda m: m['section'] == '不存在的章节')
# 事件二：tenant 是 None → 在「过滤」语义下会全不匹配（或更糟：全匹配）
_, a2 = retrieve_guarded(Q5, lambda m: m['tenant'] == None)
# 正常
_, a3 = retrieve_guarded(Q5, lambda m: m['tenant'] == 'acme')
for name, a in [('章节写错', a1), ('tenant=None', a2), ('正常', a3)]:
    print(f'{name:<14} {a if a else "无告警"}')
assert a1 and a2 and not a3
print('\\n✅ 「过滤后候选集为空」必须报警而不是静默返回空。')
print('   多租户下这一条是**安全边界**：租户过滤必须前置、且必须是不可绕过的默认值。')
print('   靠调用方「记得传 tenant」的设计，把一次跨租户泄漏的距离缩短到一行漏写的代码。')"""),

    md("""## 6 · 否定与数值约束：向量检索几乎失明"""),

    code("""NEG_PAIRS = [
    ('餐饮报销可以报销酒水',   '餐饮报销不可以报销酒水'),
    ('包含增值税的发票',       '不包含增值税的发票'),
    ('2024 年之后生效的条款',  '2024 年之前生效的条款'),
    ('超过 5000 元的合同',     '不超过 5000 元的合同'),
]
print(f"{'A':<24}{'B（语义相反）':<26}{'cos':>7}")
sims = []
for a, b in NEG_PAIRS:
    s = cos(embed(a), embed(b))
    sims.append(s)
    print(f'{a:<24}{b:<26}{s:>7.3f}')
assert min(sims) > 0.6, '语义相反的句子在向量空间里依然很近'
print(f'\\n✅ 语义完全相反的句对，相似度 {min(sims):.2f}–{max(sims):.2f}。')
print('   一个「不」字改变了全部语义，却几乎不改变向量。')
print('   本课的玩具嵌入放大了这个问题，但真实句嵌入在否定上确实也弱——')
print('   这是一个被反复报告的已知局限（Kassner & Schütze, ACL 2020 一线），不是实现问题。')"""),

    code("""# --- 正确做法：把硬约束抽成过滤器 ---
def extract_constraints(query):
    \"\"\"把查询里的硬约束抽出来，返回 (语义部分, 约束 dict)。\"\"\"
    cons, sem = {}, query
    m = re.search(r'(\\d{4})\\s*年(之后|以后|之前|以前)', query)
    if m:
        yr, direction = int(m.group(1)), m.group(2)
        cons['year'] = ('>=', yr) if direction in ('之后', '以后') else ('<=', yr)
        sem = sem.replace(m.group(0), '')
    m = re.search(r'(不?超过)\\s*([\\d.]+)\\s*(万?)元', query)
    if m:
        val = float(m.group(2)) * (10000 if m.group(3) else 1)
        cons['amount'] = ('<=', val) if m.group(1).startswith('不') else ('>', val)
        sem = sem.replace(m.group(0), '')
    # 注意 \\w 而不是只有中文：部门名可能是英文（it / legal），
    # 而「只匹配中文」这种偷懒的正则会让约束静默失效——过滤条件没生效比写错更难发现。
    m = re.search(r'只看\\s*([\\w\\u4e00-\\u9fff]+?)\\s*(部门|的)', query)
    if m:
        cons['dept'] = ('==', m.group(1))
        sem = sem.replace(m.group(0), '')
    return sem.strip(), cons

for q in ['2024 年之后生效的报销规定', '超过 5 万元的合同怎么审批',
          '只看 it 部门的设备规定', '餐饮报销上限多少']:
    sem, cons = extract_constraints(q)
    print(f'{q:<24} → 语义「{sem}」 约束 {cons}')

def apply_constraints(cons):
    def pred(m):
        for field, (op, val) in cons.items():
            v = m.get(field)
            if v is None:
                return False
            if op == '>=' and not v >= val: return False
            if op == '<=' and not v <= val: return False
            if op == '>' and not v > val:  return False
            if op == '==' and not v == val: return False
        return True
    return pred

# 时效过滤把旧版本挡在外面（c04 是 2022 年的 150 元）
sem, cons = extract_constraints('2024 年之后生效的餐饮报销上限')
no_filter = [cid for cid, _ in retrieve('餐饮报销上限', k=3)]
with_filter = [cid for cid, _ in retrieve(sem or '餐饮报销上限', k=3,
                                          candidates=filter_ids(apply_constraints(cons)))]
print(f'\\n不带时效过滤 top3: {no_filter}   ← c04 是 2022 年的旧值 150 元')
print(f'带时效过滤   top3: {with_filter}')
assert 'c04' in no_filter, '不过滤时旧版本会被召回'
assert 'c04' not in with_filter, '时效过滤必须把旧版本挡住'
print('✅ 否定、数值区间、时间窗、集合成员——这四类必须走结构化过滤。')
print('   而这依赖模块 01 把对应的元数据抽全：抽不到的字段，这里就没有可用的过滤器。')"""),

    md("""## 7 · 查询侧缓存键"""),

    code("""QUERY_CACHE_FIELDS = ('query', 'route_version', 'rewriter_id', 'prompt_sha',
                      'synonym_version', 'model_id', 'temperature', 'm_expand')

def query_cache_key(cfg):
    norm = {k: cfg.get(k) for k in QUERY_CACHE_FIELDS}
    return hashlib.sha256(
        json.dumps(norm, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]

BASE = dict(query='吃饭最多能花多少钱', route_version='r3', rewriter_id='syn+hyde',
            prompt_sha='9af31c', synonym_version='2026-08-01',
            model_id='m-small', temperature=0.0, m_expand=3,
            log_level='INFO', request_id='req-771')

k0 = query_cache_key(BASE)
print('基线键:', k0)
for field, val in [('query', '出差最多能花多少钱'), ('route_version', 'r4'),
                   ('rewriter_id', 'syn'), ('prompt_sha', 'deadbe'),
                   ('synonym_version', '2026-09-01'), ('model_id', 'm-large'),
                   ('temperature', 0.7), ('m_expand', 5)]:
    c = dict(BASE); c[field] = val
    changed = query_cache_key(c) != k0
    print(f'  改 {field:<18} → 键变了 {changed}')
    assert changed, f'{field} 必须进缓存键'
for field, val in [('log_level', 'DEBUG'), ('request_id', 'req-999')]:
    c = dict(BASE); c[field] = val
    assert query_cache_key(c) == k0, f'{field} 不该进缓存键'
print('\\n✅ 八个字段进键，与请求无关的两个不进。')
print('   最常被漏的是 prompt_sha——改了改写 prompt 而键不变，')
print('   症状是「我明明改了 prompt，效果一点没变」，而它会被误读成「这个改动没用」。')
print('   （与 C68 模块 02 的缓存键是同一条纪律，只是对象换成了查询处理配置。）')
print()
print('   还有一条：temperature > 0 时**不该缓存单次改写结果**——')
print('   要么把温度固定为 0，要么缓存「一整组」改写并整组复用。')"""),

    md("""## 8 · 评测集自检：词重叠率

用文档原句改成的查询与目标块共享大量词，
于是**词汇鸿沟这个失败在你的评测集上根本不存在**。"""),

    code("""def word_overlap(query, chunk_text):
    a, b = set(tokenize(query)), set(tokenize(chunk_text))
    return len(a & b) / len(a) if a else 0.0

TEXT = {cid: t for cid, t, _ in CHUNKS}

# 两种构造方式
FROM_DOC = {'餐饮报销的单次上限是多少': 'c01', '正式员工每年享有多少天带薪年假': 'c05',
            '笔记本电脑的更换周期是多久': 'c07', '密码长度不得少于多少位': 'c08'}
FROM_USER = {'吃饭最多能花多少钱': 'c01', '休假有几天': 'c05',
             '电脑多久换一次': 'c07', '密码要多长': 'c08'}

K_EVAL = 1   # 同第 4 节：k=3 时两个集合都饱和到 1.00，看不出差别

def eval_set_report(qs, k=K_EVAL):
    ov = [word_overlap(q, TEXT[g]) for q, g in qs.items()]
    hit = sum(1 for q, g in qs.items() if g in [c for c, _ in retrieve(q, k=k)])
    return float(np.mean(ov)), hit / len(qs)

ov_doc, rec_doc = eval_set_report(FROM_DOC)
ov_user, rec_user = eval_set_report(FROM_USER)
print(f"{'评测集构造方式':<22}{'平均词重叠':>12}{'recall@' + str(K_EVAL):>11}")
print(f'{"用文档原句改成问题":<22}{ov_doc:>12.2f}{rec_doc:>11.2f}')
print(f'{"真实用户的问法":<22}{ov_user:>12.2f}{rec_user:>11.2f}')

assert ov_doc > 2 * ov_user, '文档原句构造的查询词重叠显著更高'
assert rec_doc > rec_user, '于是它测出的 recall 也虚高'

# 在两个集合上分别看「查询改写」的收益
def gain_of_rewrite(qs, k=K_EVAL):
    base = sum(1 for q, g in qs.items() if g in [c for c, _ in retrieve(q, k=k)])
    rew = sum(1 for q, g in qs.items()
              if g in [c for c, _ in retrieve(rewrite_synonym(q), k=k)])
    return (rew - base) / len(qs)

g_doc, g_user = gain_of_rewrite(FROM_DOC), gain_of_rewrite(FROM_USER)
print(f'\\n查询改写的收益: 在「文档原句」集上 {g_doc:+.0%}，'
      f'在「真实问法」集上 {g_user:+.0%}')
assert g_user > g_doc, '在文档原句集上会得出「改写没收益」的错误结论'
print('✅ 这是本模块最重要的一条：')
print(f'   在文档原句构造的评测集上，查询改写的收益是 {g_doc:+.0%}——')
print('   于是你会得出「查询改写没用」这个结论。而它只是被评测集掩盖了。')
print('   便宜的自检：算评测查询与目标块的词重叠率，')
print('   显著高于真实流量的重叠率就说明评测集偏乐观了。')"""),

    md("""## ✏️ 练习 1：完整的查询侧流水线

把四个动作串起来：`route` → `rewrite/expand` → `filter` → `retrieve` → `rrf`。

实现 `query_pipeline(query, k=3, m=3)`，返回
`dict(routed, queries, constraints, candidates_n, hits, alerts)`：
- `routed == 'skip'` 时**直接返回**，`hits` 为空、`queries` 只含原查询
- 约束抽取后，语义部分为空则用原查询
- **过滤必须前置**（作用在候选集上）
- `m` 路并行检索后用 RRF 融合
- 过滤后候选集为空要进 `alerts`"""),

    code("""def query_pipeline(query, k=3, m=3):
    \"\"\"返回 dict(routed, queries, constraints, candidates_n, hits, alerts)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# a) 不该检索的查询直接放行
r = query_pipeline('3000 除以 12 等于多少')
assert r['routed'] == 'skip' and r['hits'] == [] and len(r['queries']) == 1

# b) 词汇鸿沟的查询：融合后应当命中
r = query_pipeline('吃饭最多能花多少钱')
assert r['routed'] == 'retrieve'
assert len(r['queries']) >= 2, '至少要有原查询 + 一个改写'
assert r['queries'][0] == '吃饭最多能花多少钱', '第一路必须是原查询（兜底）'
assert 'c01' in r['hits'], r['hits']

# c) 带时效约束：旧版本必须被挡住，且过滤前置（候选数 < 全库）
r = query_pipeline('2024 年之后生效的餐饮报销上限')
assert r['constraints'].get('year') == ('>=', 2024), r['constraints']
assert r['candidates_n'] < len(CHUNKS), '过滤必须前置，候选集应当变小'
assert 'c04' not in r['hits'], '2022 年的旧值必须被挡住'
assert 'c01' in r['hits']

# d) 过滤条件写错 → 告警
r = query_pipeline('只看 nonexist 部门的设备规定')
assert r['alerts'], '候选集为空必须告警'
print('✅ 练习 1 通过：四个动作串起来，且过滤前置、原查询兜底')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def query_pipeline(query, k=3, m=3):
    alerts = []
    routed = route(query)
    if routed == 'skip':
        return dict(routed='skip', queries=[query], constraints={},
                    candidates_n=0, hits=[], alerts=alerts)
    sem, cons = extract_constraints(query)
    base = sem if sem else query
    # 扩展：原查询永远是第一路（兜底）
    variants = [query, rewrite_synonym(base)]
    variants.append(rewrite_synonym(base).replace('多少钱', '若干元。'))   # HyDE 替身
    variants = list(dict.fromkeys(variants))[:m]
    # 过滤前置
    cands = filter_ids(apply_constraints(cons)) if cons else None
    n_cand = len(cands) if cands is not None else len(CHUNKS)
    if cands is not None and len(cands) == 0:
        alerts.append('过滤后候选集为空——过滤条件很可能写错了')
        return dict(routed=routed, queries=variants, constraints=cons,
                    candidates_n=0, hits=[], alerts=alerts)
    rankings = [[cid for cid, _ in retrieve(v, k=k * 2, candidates=cands)]
                for v in variants]
    return dict(routed=routed, queries=variants, constraints=cons,
                candidates_n=n_cand, hits=rrf(rankings, k=k), alerts=alerts)

assert query_pipeline('3000 除以 12 等于多少')['routed'] == 'skip'
r = query_pipeline('吃饭最多能花多少钱')
assert r['queries'][0] == '吃饭最多能花多少钱' and 'c01' in r['hits']
r = query_pipeline('2024 年之后生效的餐饮报销上限')
assert r['candidates_n'] < len(CHUNKS) and 'c04' not in r['hits'] and 'c01' in r['hits']
assert query_pipeline('只看 nonexist 部门的设备规定')['alerts']
print('✅ 参考答案 1 通过')
print('   两个容易写错的地方：')
print('   ① 过滤要作为 candidates 传进检索，而不是在 hits 上筛（第 5 节的 (1-φ)^k）；')
print('   ② 原查询必须是第一路——改写坏掉时它是唯一的兜底。')"""),

    md("""## ✏️ 练习 2：后置过滤的空结果概率

实现 `empty_prob(k, phi)` 与 `min_k_for_target(phi, target)`：
- `empty_prob(k, phi)` = 后置过滤返回空的概率 $(1-\\phi)^k$
- `min_k_for_target(phi, target)` = 让空结果概率不超过 `target` 所需的最小 `k`

这个函数的用途：**如果你被迫用后置过滤（比如向量库不支持前置过滤），
它告诉你 k 要放大到多少才勉强可用。**"""),

    code("""def empty_prob(k, phi):
    \"\"\"后置过滤返回空的概率。\"\"\"
    # TODO
    raise NotImplementedError

def min_k_for_target(phi, target):
    \"\"\"最小的 k 使 empty_prob(k, phi) <= target。phi<=0 时返回 None。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
assert abs(empty_prob(10, 0.05) - 0.5987) < 1e-3
assert empty_prob(0, 0.3) == 1.0
assert empty_prob(5, 1.0) == 0.0

assert min_k_for_target(0.5, 0.01) == 7, min_k_for_target(0.5, 0.01)
k_needed = min_k_for_target(0.05, 0.01)
assert empty_prob(k_needed, 0.05) <= 0.01 and empty_prob(k_needed - 1, 0.05) > 0.01
print(f'φ=5% 且要求空结果率 ≤ 1%: k 至少 {k_needed}')
assert k_needed > 80, f'应当大到不实用，得到 {k_needed}'
assert min_k_for_target(0.0, 0.01) is None, 'φ=0 时无论 k 多大都是空'
print(f"{'φ':>7}{'空结果率≤1% 所需 k':>20}")
for ph in [0.5, 0.2, 0.1, 0.05, 0.01]:
    print(f'{ph:>7.2f}{min_k_for_target(ph, 0.01):>20}')
print('✅ 练习 2 通过：φ 越小，后置过滤所需的 k 越不现实')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def empty_prob(k, phi):
    return (1.0 - phi) ** k

def min_k_for_target(phi, target):
    if phi <= 0:
        return None
    if phi >= 1:
        return 1
    # (1-phi)^k <= target  →  k >= log(target)/log(1-phi)
    k = math.ceil(math.log(target) / math.log(1 - phi))
    while empty_prob(k, phi) > target:
        k += 1
    return max(1, k)

assert abs(empty_prob(10, 0.05) - 0.5987) < 1e-3
assert min_k_for_target(0.5, 0.01) == 7
kn = min_k_for_target(0.05, 0.01)
assert empty_prob(kn, 0.05) <= 0.01 and empty_prob(kn - 1, 0.05) > 0.01 and kn > 80
assert min_k_for_target(0.0, 0.01) is None
print('✅ 参考答案 2 通过')
print(f'   φ=1% 时需要 k={min_k_for_target(0.01, 0.01)}——这已经不是「调大 k」能解决的问题。')
print('   所以「向量库不支持前置过滤」不是一个可以绕过的限制，它是一个选型否决项。')"""),

    md("""## ✏️ 练习 3：改写的安全检查

改写会改变语义（第 2 节的漂移事故）。实现一个**上线前的自动检查** `rewrite_safety`：

给定一批 (原查询, 改写后) 对，返回被判为不安全的那些，判据三条（命中任一即不安全）：
1. **否定词丢失**：原查询含否定词（不/无/非/未/否）而改写后不含
2. **数字改变**：两边的数字多重集不同
3. **长度塌缩**：改写后的字符数少于原查询的一半"""),

    code("""NEG_WORDS = ('不', '无', '非', '未', '否')

def rewrite_safety(pairs):
    \"\"\"pairs: [(original, rewritten)]。
    返回 [(original, rewritten, [触发的规则名])]，只含不安全的。
    规则名用 'negation_lost' / 'number_changed' / 'length_collapse'。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
PAIRS = [
    ('不含增值税的发票怎么处理', '增值税的发票怎么处理'),        # 否定丢失
    ('超过 5000 元的合同', '超过 500 元的合同'),                 # 数字改变
    ('餐饮报销的单次上限是多少', '餐饮'),                        # 长度塌缩
    ('吃饭最多能花多少钱', '餐饮单次上限是多少钱'),               # 安全
    ('电脑多久换一次', '笔记本电脑多久换一次'),                   # 安全
    ('不超过 5000 元的合同', '5 元的合同'),                      # 三条全中
]
bad = rewrite_safety(PAIRS)
names = {o: set(rules) for o, _, rules in bad}
print(f'{len(bad)}/{len(PAIRS)} 个改写被判不安全:')
for o, r, rules in bad:
    print(f'  「{o}」 → 「{r}」  {rules}')

assert len(bad) == 4, f'应当有 4 个不安全，得到 {len(bad)}'
assert 'negation_lost' in names['不含增值税的发票怎么处理']
assert 'number_changed' in names['超过 5000 元的合同']
assert 'length_collapse' in names['餐饮报销的单次上限是多少']
assert names['不超过 5000 元的合同'] == {'negation_lost', 'number_changed', 'length_collapse'}
assert '吃饭最多能花多少钱' not in names and '电脑多久换一次' not in names
print('✅ 练习 3 通过：三条规则都能独立触发，也能同时触发')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def rewrite_safety(pairs):
    out = []
    for orig, rew in pairs:
        rules = []
        if any(w in orig for w in NEG_WORDS) and not any(w in rew for w in NEG_WORDS):
            rules.append('negation_lost')
        if Counter(re.findall(r'\\d+', orig)) != Counter(re.findall(r'\\d+', rew)):
            rules.append('number_changed')
        if len(rew) < len(orig) / 2:
            rules.append('length_collapse')
        if rules:
            out.append((orig, rew, rules))
    return out

bad = rewrite_safety(PAIRS)
names = {o: set(rules) for o, _, rules in bad}
assert len(bad) == 4
assert names['不超过 5000 元的合同'] == {'negation_lost', 'number_changed', 'length_collapse'}
assert '吃饭最多能花多少钱' not in names
print('✅ 参考答案 3 通过')
print('   这三条都是确定性检查（零误报），可以直接阻断改写器上线。')
print('   注意它们不检查「改写是不是变好了」——那需要评测集，属于统计检查。')
print('   确定性检查的作用是拦住**明确的语义破坏**，这是两件不同的事。')"""),

    md("""## ✏️ 练习 4：跨表述敏感度报告

讲解第 8 节的三条纪律里，最有信息量的是「每个问题准备多个改述并分别报分」。

实现 `paraphrase_report(groups, k=3)`：`groups` 是 `{gold_chunk_id: [表述1, 表述2, ...]}`。
返回 `dict(per_group, mean_recall, sensitivity, worst)`：
- `per_group[gold]` = 该组的命中率（多少个表述能召回到 gold）
- `mean_recall` = 所有表述的总命中率
- `sensitivity` = **同一问题的不同表述之间命中与否的不一致比例**
  （即 0 < per_group < 1 的组数 / 总组数）
- `worst` = 命中率最低的那个组的 gold id"""),

    code("""def paraphrase_report(groups, k=K_EVAL):
    \"\"\"返回 dict(per_group, mean_recall, sensitivity, worst)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
GROUPS = {
    'c01': ['餐饮报销的单次上限是多少', '吃饭最多能花多少钱', '餐费能报多少'],
    'c05': ['正式员工每年享有多少天带薪年假', '休假有几天', '正式工年假多少天'],
    'c07': ['笔记本电脑的更换周期是多久', '电脑多久换一次', '笔记本几年一换'],
    'c08': ['密码长度不得少于多少位', '密码要多长', '口令最短几位'],
}
rep = paraphrase_report(GROUPS)
print('每组命中率:', {g: round(v, 2) for g, v in rep['per_group'].items()})
print(f"总命中率 {rep['mean_recall']:.2f} | 表述敏感度 {rep['sensitivity']:.2f} "
      f"| 最差组 {rep['worst']}")

assert set(rep['per_group']) == set(GROUPS)
assert all(0.0 <= v <= 1.0 for v in rep['per_group'].values())
tot = sum(len(v) for v in GROUPS.values())
manual = sum(1 for g, qs in GROUPS.items() for q in qs
             if g in [c for c, _ in retrieve(q, k=K_EVAL)]) / tot
assert abs(rep['mean_recall'] - manual) < 1e-9
assert 0.0 < rep['sensitivity'] <= 1.0, '这些组里应当存在表述敏感的组'
assert rep['worst'] in GROUPS
assert rep['per_group'][rep['worst']] == min(rep['per_group'].values())
print('✅ 练习 4 通过：敏感度比平均 recall 更有信息量——')
print('   它直接告诉你「换个说法就不行了」这件事发生的频率')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def paraphrase_report(groups, k=K_EVAL):
    per_group, hits, total = {}, 0, 0
    for gold, qs in groups.items():
        h = sum(1 for q in qs if gold in [c for c, _ in retrieve(q, k=k)])
        per_group[gold] = h / len(qs)
        hits += h; total += len(qs)
    mixed = sum(1 for v in per_group.values() if 0.0 < v < 1.0)
    worst = min(per_group, key=lambda g: (per_group[g], g))
    return dict(per_group=per_group, mean_recall=hits / total,
                sensitivity=mixed / len(groups), worst=worst)

rep = paraphrase_report(GROUPS)
tot = sum(len(v) for v in GROUPS.values())
manual = sum(1 for g, qs in GROUPS.items() for q in qs
             if g in [c for c, _ in retrieve(q, k=K_EVAL)]) / tot
assert abs(rep['mean_recall'] - manual) < 1e-9
assert 0.0 < rep['sensitivity'] <= 1.0
assert rep['per_group'][rep['worst']] == min(rep['per_group'].values())
print('✅ 参考答案 4 通过')
print(f"   敏感度 {rep['sensitivity']:.0%} 的含义：这个比例的问题「换个说法就变了结果」。")
print('   查询侧的所有改动都应该在这个数上看收益，而不是在平均 recall 上——')
print('   平均 recall 会被大量「本来就能答对」的样本冲淡。')"""),

    md("""## 🧪 真实工程胶囊：查询侧的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 路由：规则优先，偏向检索（讲解第 2 节）
# ══════════════════════════════════════════════════════════════════
def route(query, history):
    if SMALLTALK_RE.match(query):          return 'skip'
    if ARITHMETIC_RE.search(query):        return 'skip'
    if needs_sql(query):                   return 'sql'      # 跨库路由
    return 'retrieve'                                        # 兜底：查
#   上线顺序：先只加 skip 规则并统计命中率，确认漏检索为 0 后再考虑 LLM 路由器。

# ══════════════════════════════════════════════════════════════════
# B. 多轮改写：把指代消解掉（这是改写最大的单项收益）
# ══════════════════════════════════════════════════════════════════
REWRITE_PROMPT = '\\n'.join([
    '把用户的最新问题改写成一个不依赖对话历史的独立问题。',
    '只输出改写后的问题，不要解释。',
    '保留原问题里的所有数字、否定词与限定条件。',      # ← 对应练习 3 的三条检查
    '',
    '历史：{history}',
    '最新问题：{q}',
])
#   改写结果必须过 rewrite_safety()（练习 3）才允许使用；不过就退回原查询。

# ══════════════════════════════════════════════════════════════════
# C. 扩展与融合：三路，失败模式互不相同（讲解第 4 节）
# ══════════════════════════════════════════════════════════════════
variants = [q_original, q_rewritten, hyde(q_original)]
rankings = await asyncio.gather(*[vsearch(v, k=k * 2, where=where) for v in variants])
final = rrf(rankings, k0=60, k=k)
#   容量提醒：m=3 意味着向量库按 3 倍 QPS 做规划（讲解第 7 节）。

# ══════════════════════════════════════════════════════════════════
# D. 过滤必须前置，且租户不可绕过（讲解第 5 节）
# ══════════════════════════════════════════════════════════════════
def vsearch(q, k, where=None, *, tenant):        # tenant 是关键字必填参数
    where = {'$and': [{'tenant': tenant}, where]} if where else {'tenant': tenant}
    res = col.query(query_embeddings=[enc(q)], n_results=k, where=where)
    if not res['ids'][0]:
        alert('empty_candidate_set', q=q, where=where)        # 报警，不静默
    return res
#   把 tenant 做成必填关键字参数，而不是可选参数——
#   可选参数把一次跨租户泄漏的距离缩短到一行漏写的代码。

# ══════════════════════════════════════════════════════════════════
# E. 缓存（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
key = sha256(q, ROUTE_VERSION, REWRITER_ID, sha256(REWRITE_PROMPT),
             SYNONYM_VERSION, MODEL_ID, TEMPERATURE, M_EXPAND)
#   温度 > 0 时缓存「一整组」改写，不缓存单次结果。

# ══════════════════════════════════════════════════════════════════
# F. 评测集（讲解第 8 节）—— 这一项决定了前面五项能不能被正确评估
# ══════════════════════════════════════════════════════════════════
#   1) 查询来自真实日志或「没看过文档的人」
#   2) 每题 2-3 个改述，分别报分，报 sensitivity（练习 4）
#   3) 单独维护一个「跨词汇」子集，查询侧改动只在它上面看收益
#   4) CI 里跑一次 word_overlap 自检，重叠率显著高于线上就说明评测集偏乐观
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| 四个动作的顺序不能换；③ 与 ④ 不可交换 | 过滤必须作用在检索之前 | 讲解 1 |
| 「一律检索」对不该检索的查询是净损害 | 正确率从 100% 掉下来 | 第 1 节 |
| 路由器的目标是「漏检索为 0」，不是总准确率 | 两类错误代价不对称 | 第 1 节 |
| 任何改写都可能改变语义 | 「不含增值税」→「增值税」 | 第 2 节 |
| HyDE 的伪答案不需要正确 | 相似度 0.05 → 0.87（连数字写错也一样） | 第 3 节 |
| 融合降的是方差，不保证提高均值 | 融合 0.83；单路均值 0.79、最好 1.00、最差 0.50 | 第 4 节 |
| 后置过滤会静默返回空 | $(1-\\phi)^k$；φ=5%、k=10 → 60% | 第 5 节 |
| 向量检索对否定几乎失明 | 语义相反句对 cos 0.81–0.94 | 第 6 节 |
| 改写 prompt 的哈希必须进缓存键 | 漏了就「改了没效果」 | 第 7 节 |
| 用文档原句当查询会掩盖查询侧的全部价值 | 在该集上改写收益为 0 | 第 8 节 |

下一模块：**04 · 迭代与图检索**——多跳问题的单轮 recall 天然是 0，
而迭代必须带停止准则，否则成本没有上界。"""),
]
