# -*- coding: utf-8 -*-
"""C71 模块 02 · few-shot 示例选择与顺序。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（模拟器）与 01（签名与三个量）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_demo_selection.ipynb'
                       '（五种选择策略的对比 / 数量的收益曲线与「选对 1 条胜过随机 20 条」/ '
                       '顺序造成的三倍差距与「最后一条放谁」/ 无内容探针揭示标签先验 / '
                       '减先验校准 / 示例泄漏 / 示例池运维与门禁）'),
    ("核心参考", "Liu et al., <em>What Makes Good In-Context Examples for GPT-3?</em>"
                 "（DeeLIO 2022，kNN 选择）· "
                 "Lu et al., <em>Fantastically Ordered Prompts and Where to Find Them</em>"
                 "（ACL 2022，顺序敏感性）· "
                 "Zhao et al., <em>Calibrate Before Use</em>（ICML 2021，无内容探针与减先验）· "
                 "Min et al., <em>Rethinking the Role of Demonstrations</em>（EMNLP 2022）· "
                 "本课程 C03 模块 03 第 6 节（few-shot 的坑：选择、顺序与泄漏）· C11（kNN 检索）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-dims", "示例的三个维度，收益量级差一个数量级", "".join([
        P("「加几个例子」是最常见的 prompt 改动。"
          "<strong>但示例有三个独立的维度，而它们的收益量级完全不同。</strong>"),
        TABLE(["维度", "问题", "本课量到的效应", "成本"], [
            ["<strong>选择</strong>", "选哪些？",
             "<strong>选对 1 条 ≈ 随机 20 条</strong>（0.90 vs 0.70）",
             "一次检索（可缓存）"],
            ["<strong>数量</strong>", "放几个？",
             "随机选时收益缓慢上升；<em>按相似度选时 k=1 就饱和了</em>",
             "<strong>线性的 token 成本</strong>"],
            ["<strong>顺序</strong>", "什么顺序？",
             "<strong>同一批示例，只改顺序：0.30 vs 0.90（三倍）</strong>",
             "零"],
        ]),
        DUAL(
            "第三行是本模块最值得记住的一个数。"
            "<strong>顺序是零成本的，而它的影响可以比「示例数量翻四倍」更大。</strong>"
            "<em>而绝大多数系统里示例顺序是「代码里列表的书写顺序」，"
            "既没被测过也没进版本</em>"
            "（模块 01 第 7 节把它做成了一个可 diff 的文件正是为了这个）。",
            "为什么会这样？在本课的模拟器里机制是明确的："
            "<strong>近因偏置让靠后的示例被系统性偏好</strong>，"
            "所以「把最相似的示例放最后」与「放最前」是两个不同的算法。"
            "<em>在真实模型上这个效应同样被反复报告"
            "（<span class=\"term\">order sensitivity</span>），"
            "只是方向与强度依模型而异</em>——"
            "<strong>这恰恰意味着它必须被<em>测</em>，不能被<em>假设</em>。</strong>",
        ),
        CALLOUT("intuition", "一个立刻可做的实验："
                             "<strong>把你现有的示例列表反转一次，重跑评测。</strong>"
                             "<em>如果分数变了（它很可能会变），说明你的示例顺序是一个"
                             "未被测量、未被版本化的超参数</em>——"
                             "而它是免费可调的。"),
    ])),

    # ============================================================== 2
    ("selection", "五种选择策略", "".join([
        TABLE(["策略", "怎么选", "优点", "代价 / 风险"], [
            ["<strong>随机</strong>", "从池子里随机取 k 条",
             "零成本，且<em>对所有输入用同一批示例 → prompt 前缀稳定，缓存友好</em>（C33）",
             "收益最低；<strong>而且方差大</strong>——换个种子分数就变"],
            ["<strong>kNN（按输入相似度）</strong>", "取与当前输入最相似的 k 条",
             "<strong>收益最高</strong>（本课量到 k=1 即达 0.90）",
             "<em>每个请求的示例都不同 → prompt 前缀不稳定，缓存全部失效</em>；"
             "这是一个真实的成本权衡"],
            ["<strong>覆盖（每类若干）</strong>", "保证每个标签至少 n 条",
             "<strong>防「某类完全没示例」</strong>——那会让该类准确率直接归零",
             "只保证覆盖，不保证相关"],
            ["<strong>多样性（MMR 式）</strong>", "相似度 − λ×已选集合内的冗余",
             "避免 k 条示例几乎是同一句话",
             "λ 是一个要调的超参；<em>在小池子上收益有限</em>"],
            ["<strong>难度（课程式）</strong>", "按难度排，简单在前难在后",
             "与顺序维度天然结合",
             "<strong>需要难度标注</strong>；而难度本身不好定义"],
        ]),
        DUAL(
            "<strong>kNN 与「缓存友好」是直接冲突的，而这个冲突常被忽略。</strong>"
            "<em>固定示例 → prompt 前缀完全稳定 → 前缀缓存命中率接近 100%；"
            "kNN 示例 → 每个请求的前缀都不同 → 缓存全丢</em>。"
            "<strong>在高 QPS、长 prompt 的场景下，这个成本可能超过 kNN 带来的收益。</strong>"
            "<em>（前缀缓存的机制在 C33 模块 05。）</em>",
            "有一个折中：<strong>分桶 kNN</strong>——"
            "先把输入粗分成少量桶（比如按意图或按 embedding 聚类；notebook 用 4 个簇），"
            "<em>每个桶预先算好一套固定示例</em>。"
            "<strong>于是前缀只有几种，缓存仍然有效，而示例的相关性好于全局随机。</strong>"
            "<em>notebook 第 3 节实现了它，并量出它落在随机与 kNN 之间的什么位置。</em>",
        ),
        CALLOUT("warn", "「覆盖」这一条不是可选项："
                        "<strong>如果某个标签在示例里一次都没出现，"
                        "那么它的准确率通常直接是 0</strong>"
                        "（模块 00 练习 4 的 <code>demos_coverage</code> 诊断就是抓这个）。"
                        "<em>而这在真实系统里很容易发生——"
                        "「从最近 20 条标注里取示例」的自然结果就是稀有类被完全漏掉。</em>"),
    ])),

    # ============================================================== 3
    ("count", "数量：成本线性，收益次线性", "".join([
        P("「多放几个例子」是最容易做的改动，"
          "<strong>也是收益/成本比最差的一个。</strong>"),
        ASCII("""
   本课量到的曲线（10 道测试题）

   准确率
   0.9 │ ●───────●───────●───────●   ← kNN 选择：k=1 就饱和
       │
   0.7 │                         ○   ← 随机选择：k=20 才到这里
       │                    ○
   0.5 │               ○
       │      ○    ○
   0.2 │ ○────○
       └──┬───┬───┬───┬───┬───┬──►  k
          1   2   3   5   8  12  20

   token 成本 ∝ k（线性）
   → 「选对」是一次阶跃，「加量」是一条缓坡
"""),
        DUAL(
            "<strong>这条图的工程含义很直接：先做选择，再考虑数量。</strong>"
            "<em>而绝大多数团队的顺序是相反的</em>——"
            "先把示例从 3 条加到 10 条（因为这最容易），"
            "<strong>然后发现效果提升不明显，于是得出「few-shot 没什么用」的结论</strong>。",
            "还有两个与数量相关的、容易被忽略的成本："
            "<strong>① 上下文预算</strong>——"
            "<em>示例占掉的 token 是从「能塞多少检索到的文档」里扣的</em>（C33 的预算分配）；"
            "<strong>② 延迟</strong>——"
            "<em>输入 token 数直接影响首 token 延迟</em>。"
            "<strong>所以 k 不是一个只看效果的旋钮，它同时是一个容量参数。</strong>",
        ),
        H3("怎么定 k"),
        OL([
            "<strong>先把选择策略定下来</strong>（kNN 或分桶 kNN），"
            "<em>因为它决定了曲线的形状</em>。",
            "<strong>扫 k 并找拐点</strong>——"
            "<em>本课的 kNN 曲线在 k=1 就饱和，真实任务上通常在 4–16 之间</em>。",
            "<strong>把「拐点之后的 k」当成成本浪费直接砍掉</strong>。"
            "<em>而如果拐点之后还在涨，说明选择策略还有改进空间</em>——"
            "回到第 1 步而不是继续加 k。",
        ]),
    ])),

    # ============================================================== 4
    ("order", "顺序：零成本的三倍差距", "".join([
        P("同一批 5 条示例，只改排列顺序。"),
        ASCII("""
   kNN 选出 5 条，两种摆法

   最相似的放**最前**：  [最像的, 次像的, …, 最不像的]  → 准确率 0.30
   最相似的放**最后**：  [最不像的, …, 次像的, 最像的]  → 准确率 0.90

   机制（本课模拟器里是显式的）：
     score_i = sim(x, x_i) + recency · (i / (n-1))
                              └── 靠后的示例得到正向加成

   于是「最像的放最后」= 相似度与位置加成叠加，指向同一个示例
       「最像的放最前」= 两者相互抵消，最终选中的可能是最不像的那条
"""),
        DUAL(
            "<strong>这不是一个模拟器的人造效应</strong>："
            "<em>示例顺序对真实模型的影响被反复报告过，"
            "而且在某些任务上「换一个排列」造成的分数差距可以达到十几个点</em>。"
            "<strong>本课模拟器只是把这个效应做成了可控、可解释的形式。</strong>"
            "<em>方向依模型而异——所以工程上的结论不是「把最像的放最后」，"
            "而是<strong>「必须测，并且把测出来的顺序固定下来」</strong>。</em>",
            "三种处理顺序的手段，成本递增："
            "<strong>① 固定并版本化</strong>（零成本，必做）——"
            "<em>把顺序当成配置的一部分，进指纹（模块 01 第 7 节）</em>；"
            "<strong>② 搜一遍顺序</strong>（零成本）——"
            "<em>顺序的自由度往往高度集中：本课量到「最后一条放谁」这一个选择"
            "就解释了顺序效应的六成</em>；"
            "<strong>③ 多排列投票</strong>（k 倍成本）——"
            "<em>跑多个排列取多数投票；它降的是方差</em>"
            "（与 C70 模块 03 的多查询融合同构：<strong>降方差不保证提高均值</strong>）。",
        ),
        P("notebook 第 4 节还量了一件<strong>与流行做法相反</strong>的事："
          "<em>「打散标签」在本课的模拟器上<strong>没有</strong>稳定收益</em>——"
          "因为这里的偏置来自「最后一条是谁」，而不是「末尾有一串同标签」。"
          "<strong>可迁移的是方法（顺序要搜、要在留出集上复核），不是规则。</strong>"),
    ])),

    # ============================================================== 5
    ("calibration", "标签偏置：用无内容探针把它测出来", "".join([
        P("示例会给模型一个<strong>先验</strong>："
          "某些标签更容易被输出，与输入内容无关。"
          "<strong>而这个先验可以被一个极便宜的实验测出来。</strong>"),
        ASCII("""
   无内容探针（content-free probe）

   把输入换成一个没有信息的占位符：
     "N/A" / "" / "[MASK]"
   然后看模型输出什么。

   输出的分布 = 这套 prompt 的**标签先验**

   本课量到的：
     示例里 other 放最后 → 探针输出 other（4/4 个探针）
     示例里 other 放最前 → 探针输出 account（4 个探针里 3 个）
   同一个示例集合，只改顺序，先验就变了。
"""),
        DUAL(
            "<strong>探针的价值是它把「偏置」从一个模糊的担忧变成一个可测的量</strong>，"
            "而且<em>它只需要一次调用</em>。"
            "<strong>而它测出来的东西可以直接用来校准</strong>："
            "<em>把每个标签的分数减去探针给它的分数，再取 argmax</em>"
            "（这就是 <span class=\"term\">contextual calibration</span> 的思路）。",
            "notebook 第 5 节把模拟器展开成一个<strong>标签分数向量</strong>再做校准——"
            "<em>这一步不是实现细节，而是校准的前提</em>："
            "<strong>减先验作用在分数上，所以拿不到 logprobs 的 API 上这条路走不通。</strong>"
            "本课量到的效果是：<em>它把偏置最严重的顺序配置从 50% 救到 70%，"
            "与「other 放最后」这个配置持平——<strong>注意不是与表里最好的 80% 持平</strong>；而在本来没有偏置的配置上它不造成损害。</em>"
            "<strong>还有一个隐含前提：减先验假设真实标签分布接近均匀</strong>——"
            "<em>若真实分布本身严重倾斜（比如八成都是兜底类），"
            "该减到「真实分布」而不是「均匀」。</em>"
            "拿不到 logprobs 时的替代是<strong>搜一遍顺序</strong>与<strong>多排列投票</strong>。",
        ),
        CALLOUT("intuition", "一条必须放进监控的指标："
                             "<strong>预测标签分布</strong>。"
                             "<em>它相对真实分布的偏移（PSI）会同时抓到"
                             "顺序偏置、示例漂移、以及模型换版本</em>——"
                             "而这三件事在端到端准确率上都表现为「效果变差了」。"
                             "（模块 01 第 7 节的门禁里已经放了这一项。）"),
    ])),

    # ============================================================== 6
    ("leakage", "泄漏：示例来自评测集 = 一次不诚实的评测", "".join([
        P("<strong>这是本模块唯一一个「正确性」问题而不是「效果」问题。</strong>"),
        DUAL(
            "如果示例池与评测集有交集，"
            "<em>那么被选中当示例的那些测试样本，答案已经写在 prompt 里了</em>。"
            "<strong>kNN 选择让这件事变得几乎必然发生</strong>——"
            "<em>因为「与输入最相似的示例」在有交集时就是输入自己</em>。",
            "notebook 第 6 节量出这个虚高。"
            "<strong>而修法是纯纪律性的</strong>："
            "<em>示例池与评测集必须来自不相交的样本 ID 集合，"
            "并且这件事要在 CI 里检查（一次集合求交，零成本）</em>。"
            "<strong>这与 C03 模块 05 的污染检测是同一类问题，"
            "只不过这里的污染是自己在 prompt 里造出来的</strong>——"
            "<em>所以它也更容易被彻底解决。</em>",
        ),
        H3("三条必须在 CI 里检查的"),
        UL([
            "<strong>示例池 ∩ 评测集 = ∅</strong>（按稳定 ID，不是按内容）",
            "<strong>示例池 ∩ 留出集 = ∅</strong>——"
            "<em>模块 03 的自动优化会用留出集，而优化过程会「见过」示例池</em>",
            "<strong>示例的答案字段不能出现在评测集的任何输入里</strong>——"
            "这条抓的是更隐蔽的泄漏（比如示例的理由文本被拼进了测试输入）",
        ]),
        CALLOUT("danger", "一个真实的、很容易发生的路径："
                          "<strong>「我们用线上日志做示例池，也用线上日志做评测集」</strong>。"
                          "<em>两者按时间切分不够——同一个用户的同一个问题可能出现在两边</em>。"
                          "<strong>必须按稳定 ID 去重后再切分。</strong>"),
    ])),

    # ============================================================== 7
    ("pool-ops", "示例池的运维", "".join([
        P("示例池是一个<strong>会腐烂的资产</strong>，"
          "而它的腐烂方式与 C70 模块 05 的索引腐烂同构。"),
        TABLE(["腐烂", "怎么发生", "症状", "检查"], [
            ["<strong>覆盖退化</strong>", "新样本按时间追加，稀有类被稀释",
             "<strong>某个标签的准确率突然归零</strong>",
             "<em>每类示例数的最小值</em>（确定性检查，可阻断）"],
            ["<strong>标签漂移</strong>", "标注标准变了，池里新旧标准混存",
             "同类样本给出矛盾的信号，整体准确率缓慢下降",
             "抽样复核；<em>池里样本要带标注时间与标注标准版本</em>"],
            ["<strong>分布漂移</strong>", "线上话题变了，池里还是旧话题",
             "kNN 选出来的示例与输入越来越不相似",
             "<strong>监控「选中示例与输入的平均相似度」</strong>——"
             "<em>它掉下来就是漂移的直接信号</em>"],
            ["<strong>规模膨胀</strong>", "只加不删",
             "kNN 变慢；而效果不再提升",
             "<em>按「被选中的频率」淘汰：从未被选中的示例可以删</em>"],
        ]),
        DUAL(
            "第三行那个指标值得单独强调："
            "<strong>「选中示例与输入的平均相似度」是这一层最有信息量的无真值指标</strong>。"
            "<em>它不需要标注，而它同时反映了池子的覆盖度与线上分布的变化</em>。"
            "<strong>它掉下来时，该做的是补池子，而不是改 prompt。</strong>",
            "还有一条与 C68 模块 05 同构的纪律："
            "<strong>从线上回灌样本进示例池时，要限制回灌占比</strong>。"
            "<em>因为回灌的样本是「当前系统答对/答错的那些」，"
            "它们的分布已经被当前系统塑造过了</em>——"
            "<strong>全部用回灌样本会让池子越来越像系统自己的输出，形成闭环</strong>。"
            "<em>与 C68 模块 05 的 <code>from_production</code> 占比上限是同一条。</em>",
        ),
    ])),

    # ============================================================== 8
    ("gate", "把示例选择做成一个可门禁的流程", "".join([
        ASCII("""
   示例卡（每次改示例池或选择策略时生成）

   pool_id:          demos-2026w35
   pool_size:        842        min_per_label: 31     ← 确定性检查
   selector:         bucket_knn(buckets=8, k=6)
   order_policy:     most_similar_last（搜出来的，不是默认规则）  ← **必须写明**
   prompt_fp:        7c2a91be   （示例集合与顺序都在里面）

   泄漏检查:  pool ∩ test = ∅ ✓   pool ∩ holdout = ∅ ✓        ← 阻断项
   覆盖检查:  每类 ≥ 20 条 ✓                                   ← 阻断项
   相似度:    选中示例与输入的平均相似度 0.61（基线 0.63）      ← 报警项
   效果:      分层准确率 每类都 ≥ 基线 − 2σ ✓                   ← 阻断项
   先验:      无内容探针 → other；预测分布 PSI 0.04 ✓           ← 报警项
"""),
        P("<strong>分级仍然是 C68 模块 04 的那一条</strong>："
          "<em>确定性检查（泄漏、覆盖、指纹）阻断，"
          "统计检查（相似度、PSI）报警，效果回归按方差推阈值后阻断</em>。"),
        H3("一个容易被忽略的确定性检查"),
        P("<strong><code>order_policy</code> 必须是一个显式声明的字符串，而不是「代码里的顺序」。</strong>"
          "<em>检查方式：给定 pool 与 selector，用声明的 policy 重算一次示例序列，"
          "与实际发送的序列逐条比对</em>。"
          "<strong>不一致 → 阻断。</strong>"
          "<em>这一项抓的是「有人在代码里插了一条示例但没改配置」——"
          "而那正是本模块第 1 节说的「未被测量、未被版本化的超参数」的来源。</em>"),
    ])),

    # ============================================================== 9
    ("where-demos-come-from", "示例从哪来：四个来源与它们的偏倚", "".join([
        P("前八节都假设有一个示例池。"
          "<strong>这一节讨论它从哪来——而每个来源都带一种特定的偏倚。</strong>"),
        TABLE(["来源", "成本", "带进来的偏倚", "对策"], [
            ["<strong>人工标注</strong>", "高",
             "标注者的理解偏好；<em>而标注指南的歧义会变成示例里的噪声</em>",
             "标注一致性检查（C10 的 kappa 工具）"],
            ["<strong>线上日志 + 人工复核</strong>", "中",
             "<strong>分布已经被当前系统塑造过</strong>——"
             "用户学会了「怎么问才能得到答案」",
             "限制回灌占比（C68 模块 05 的 <code>from_production</code> 上限）"],
            ["<strong>bootstrap（当前系统做对的样本）</strong>", "低",
             "<strong>自我强化</strong>——只挑已经做对的（模块 03 第 4 节）",
             "配覆盖保底：每类至少一条，<em>即使那一类当前一条都没做对</em>"],
            ["<strong>合成数据</strong>", "低",
             "<em>它继承生成模型的偏好与盲区</em>",
             "人工抽检；<strong>而且不要用被评测的同一个模型来生成</strong>"],
        ]),
        DUAL(
            "<strong>四个来源里最容易出问题的是第二个</strong>，"
            "因为它看起来最「贴近真实」。"
            "<em>而线上日志里的问题分布已经是「当前系统能处理的那些」</em>——"
            "用户遇到几次答不上来之后就不再那样问了。"
            "<strong>于是从日志里取示例会系统性地漏掉「系统本来就不擅长」的那类输入。</strong>",
            "一个便宜的对策：<strong>保留一个「困难样本」子池，专门放当前系统做错的输入</strong>，"
            "并<em>强制它在示例池里占一个固定的最小比例</em>。"
            "<strong>它与覆盖保底是同一类机制——用约束抵抗自我强化。</strong>"
            "<em>而这与 C70 模块 04 的「迭代作为兜底路径」也是同一个思路："
            "让系统的薄弱面被显式地保留在流程里，而不是被优化过程平均掉。</em>",
        ),
    ])),

    # ============================================================== 10
    ("vs-retrieval", "示例选择与文档检索：像但不是一回事", "".join([
        P("「按相似度选示例」和「按相似度检索文档」在实现上几乎一样，"
          "<strong>但它们的目标函数不同，所以最优做法不同。</strong>"),
        TABLE(["维度", "文档检索（C11 / C70）", "示例选择（本模块）"], [
            ["<strong>目标</strong>", "找到含答案的段落",
             "<strong>给模型一个「该怎么做这类题」的示范</strong>"],
            ["<strong>「相关」的含义</strong>", "内容相关",
             "<em>任务形态相关</em>——"
             "<strong>示例的内容甚至可以与输入无关，只要它示范的是同一类推理</strong>"],
            ["<strong>多样性的作用</strong>", "避免 top-k 被近重复占满",
             "<strong>覆盖标签空间</strong>（缺一类就归零）"],
            ["<strong>k 的收益曲线</strong>", "随 k 缓升（更多候选）",
             "<strong>很小的 k 就饱和</strong>（第 3 节量到 k=1）"],
            ["<strong>顺序</strong>", "影响的是「模型先看到什么」",
             "<strong>直接改变结果（三倍差距）</strong>"],
            ["<strong>缓存</strong>", "索引侧缓存，与 prompt 无关",
             "<em>前缀缓存——示例变了缓存就失效</em>"],
        ]),
        DUAL(
            "<strong>最有实践价值的一行是第二行。</strong>"
            "<em>文档检索里「不相关的段落」是纯噪声；"
            "而示例里「内容不相关但形态相同」的样本仍然有用</em>——"
            "它示范的是输出格式、推理步骤的粒度、边界情况怎么处理。"
            "<strong>这解释了为什么「每类一条覆盖示例」即使与输入完全不相关也有价值。</strong>",
            "反过来也有一个陷阱："
            "<strong>把示例选择完全等同于检索，会让人只优化「内容相似度」，"
            "而忽略覆盖度与顺序这两个更便宜的维度。</strong>"
            "<em>本模块第 1/2 节的数字正是这件事的证据："
            "覆盖（每类一条）就拿到了随机的两倍多，而它不需要任何相似度计算。</em>",
        ),
    ])),

    # ============================================================== 11
    ("what-to-do-first", "拿到一个新任务时，这一层该按什么顺序做", "".join([
        P("本模块给出了很多可调的东西。"
          "<strong>这一节把它们排成一个顺序，依据是本课量到的效应量与成本。</strong>"),
        TABLE(["顺序", "动作", "成本", "本课量到的效应"], [
            ["1", "<strong>覆盖保底：每类至少一条示例</strong>", "零",
             "<strong>缺一类 → 该类准确率归零</strong>（正确性问题）"],
            ["2", "<strong>泄漏检查：池 ∩ 评测集 = ∅</strong>", "零（一次集合求交）",
             "泄漏会让所有后续测量失去意义"],
            ["3", "<strong>搜一遍顺序，在留出集上复核</strong>", "零（只是重排）",
             "<strong>三倍差距</strong>；而「最后一条放谁」占六成"],
            ["4", "<strong>换成 kNN 或分桶 kNN</strong>", "一次检索（可缓存）",
             "<strong>kNN 的 k=1 不输随机的 k=20</strong>"],
            ["5", "扫 k 找拐点，砍掉拐点之后的 k", "零（省钱）",
             "kNN 曲线很小的 k 就饱和"],
            ["6", "无内容探针 + 减先验校准（若有 logprobs）", "一次调用 + 实现",
             "把最差顺序从 50% 救到 70%"],
            ["7", "示例池运维：监控平均相似度、淘汰未被选中的", "低",
             "漂移流量上平均相似度明显下降"],
        ]),
        DUAL(
            "<strong>前三步的总成本是零，而它们覆盖了本模块效应量最大的两项</strong>"
            "（覆盖度这个正确性问题、以及顺序这个三倍差距）。"
            "<em>第 4 步开始才需要真正的实现工作</em>。"
            "<strong>所以如果只能做一件事，做第 1 步；"
            "只能做三件，做前三步。</strong>",
            "一个常见的次序错误：<strong>直接从第 4 步开始</strong>"
            "（因为 kNN 听起来最像「正确做法」）。"
            "<em>后果是：泄漏没查（于是 kNN 让每道题的示例包含它自己，"
            "分数虚高到无意义）、覆盖没保底（于是稀有类归零）、"
            "顺序没搜（于是白丢一个三倍的免费收益）</em>。"
            "<strong>而这三件事都比 kNN 便宜。</strong>",
        ),
    ])),

    # ============================================================== 12
    ("boundary", "这一层的边界", "".join([
        P("示例是一个很容易被当成万能药的东西。"
          "<strong>这一节说清它解决不了什么。</strong>"),
        TABLE(["问题", "示例能解决吗", "该去哪一层"], [
            ["<strong>输出格式不对</strong>", "<em>部分</em>——示例会示范格式，但不保证",
             "<strong>模块 04 的解码约束</strong>（它是保证而不是示范）"],
            ["<strong>取值域没声明</strong>", "<strong>不能</strong>",
             "模块 01 的指令槽位；<em>示例不能替代取值域声明</em>"],
            ["<strong>模型不知道某个领域事实</strong>", "<strong>不能</strong>",
             "检索（C11 / C70）——<em>示例示范的是「怎么做」，不是「事实是什么」</em>"],
            ["<strong>需要多步推理</strong>", "<em>有限</em>",
             "C09（推理与测试时计算）；<em>本课的模拟器没有推理能力，所以不讨论</em>"],
            ["<strong>上下文塞不下</strong>", "<strong>不能</strong>（示例本身就占预算）",
             "C33 的预算分配与压缩"],
        ]),
        DUAL(
            "<strong>第三行是最容易混淆的一条。</strong>"
            "<em>「模型答错了，多给几个例子」这个反应在「格式/形态」类问题上有效，"
            "在「缺事实」类问题上完全无效</em>——"
            "<strong>而两者在指标上都表现为「准确率低」。</strong>"
            "<em>区分方式很直接：把答案所需的事实列出来，看它在不在 prompt 里。</em>",
            "而第一行值得反过来读一遍："
            "<strong>如果你正在用示例来「教模型输出正确的 JSON」，"
            "那么你在用一个概率性手段解决一个可以被保证的问题。</strong>"
            "<em>模块 04 的解码约束能把解析率钉在 1.0，"
            "而示例只能让它「更常对」</em>。"
            "<strong>把示例的预算省下来用在「示范任务形态」上，收益更高。</strong>",
        ),
        H3("一句话记住这一层的定位"),
        P("<strong>示例回答的是「这类题该怎么做」，不是「这道题的答案是什么」，"
          "也不是「输出必须长成什么样」。</strong>"
          "<em>前者交给检索（C11 / C70），后者交给解码约束（模块 04）。</em>"
          "<strong>而在「怎么做」这件事上，本模块量到的三个数值得记住："
          "选对 1 条 ≈ 随机 20 条、顺序造成三倍差距、某类没示例则该类归零。</strong>"
          "<em>三个数对应三个不同的动作——选择、排序、覆盖——"
          "而它们的总成本接近于零。</em>"),
    ])),
]

NB = [
    md("""# 02 · few-shot 示例选择与顺序（选择 / 数量 / 顺序 / 校准 / 泄漏 / 池运维）

目标：把「加几个例子」拆成**三个独立的、量级差一个数量级的维度**。

本 notebook 你会亲手实现：
1. **五种选择策略** —— 随机 / kNN / 覆盖 / 多样性 / 单标签（最坏）
2. **数量的收益曲线** —— 「选对 1 条 ≈ 随机 20 条」
3. **分桶 kNN** —— 兼顾相关性与前缀缓存友好
4. **顺序造成的三倍差距** —— 以及「最后一条放谁」解释了其中六成
5. **无内容探针 + 减先验校准** —— 一次调用测出标签先验；校准把最差顺序救到与最好持平
6. **示例泄漏** —— kNN 选择让它几乎必然发生
7. **示例池运维** —— 覆盖退化与「选中示例平均相似度」这个无真值指标
8. **示例卡 + 门禁**

> 心智模型：**选择是一次阶跃，数量是一条缓坡，顺序是免费的三倍。
> 而绝大多数系统只调了数量。**"""),

    md("""## 0 · 环境（沿用模块 00/01 的模拟器与数据）"""),

    code("""import os, re, json, math, hashlib, itertools
from collections import Counter, defaultdict

import numpy as np

DIM = 2048
LABELS = ['bug', 'feature', 'billing', 'account', 'other']
UNPARSEABLE = 'UNPARSEABLE'

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

def sim(a, b):
    return float(np.dot(embed(a), embed(b)))

POOL = [
    ('登录后一直转圈，点不动', 'bug'), ('保存文件时报错 500', 'bug'),
    ('页面加载不出来', 'bug'), ('导出 CSV 会丢最后一行', 'bug'),
    ('希望支持批量导出', 'feature'), ('能不能加暗色主题', 'feature'),
    ('想要一个搜索框', 'feature'), ('建议增加导入模板', 'feature'),
    ('这个月扣了两次钱', 'billing'), ('发票开错了公司名', 'billing'),
    ('为什么涨价了', 'billing'), ('想申请退款', 'billing'),
    ('忘记密码收不到邮件', 'account'), ('想改绑定手机号', 'account'),
    ('账号被锁了', 'account'), ('想注销账号', 'account'),
    ('你们客服态度不错', 'other'), ('随便看看', 'other'),
    ('没什么事', 'other'), ('祝好', 'other'),
]
TEST = [
    ('打开报表就崩溃', 'bug'), ('保存草稿会丢内容', 'bug'),
    ('希望能加个批量删除', 'feature'), ('想要导出 PDF 的功能', 'feature'),
    ('这个月账单不对', 'billing'), ('发票上的税号不对', 'billing'),
    ('登录不上，密码重置也收不到', 'account'), ('手机号换了要怎么改', 'account'),
    ('感谢你们的帮助', 'other'), ('没别的了', 'other'),
]
INSTR = ('把用户反馈分类为 bug / feature / billing / account / other 之一，'
         '只输出标签。都不符合时输出 other。不要解释。')

def toy_lm(instruction, demos, x, recency=0.35, prior='other'):
    declared = [l for l in LABELS if l in instruction]
    if not declared:
        return UNPARSEABLE
    if not demos:
        return prior
    E = np.stack([embed(t) for t, _ in demos])
    s = E @ embed(x)
    n = len(demos)
    s = s + np.array([recency * (i / (n - 1) if n > 1 else 1.0) for i in range(n)])
    label = demos[int(np.argmax(s))][1]
    return label if label in declared else prior

def accuracy(selector, test=None, instruction=INSTR):
    test = TEST if test is None else test
    return sum(1 for x, g in test if toy_lm(instruction, selector(x), x) == g) / len(test)

print(f'示例池 {len(POOL)} 条 · 测试 {len(TEST)} 条 · 标签 {len(LABELS)} 个')"""),

    md("""## 1 · 五种选择策略

注意每个 selector 都返回**一个有序列表**——顺序是它的一部分（第 4 节展开）。
这里统一用「最相似的放最后」这个顺序策略，把顺序变量固定住。"""),

    code("""def select_random(x, k=5, seed=0):
    r = np.random.default_rng(seed)
    return [POOL[i] for i in r.permutation(len(POOL))[:k]]

def select_knn(x, k=5, most_similar_last=True):
    e = embed(x)
    s = np.array([float(np.dot(embed(t), e)) for t, _ in POOL])
    idx = list(np.argsort(-s)[:k])                # 最相似在前
    if most_similar_last:
        idx = idx[::-1]                           # 翻过来：最相似在后
    return [POOL[i] for i in idx]

def select_coverage(x, k=5, per_label=1):
    out = []
    for l in LABELS:
        out += [t for t in POOL if t[1] == l][:per_label]
    return out[:k]

def select_mmr(x, k=5, lam=0.5):
    e = embed(x)
    cand = list(range(len(POOL)))
    chosen = []
    while len(chosen) < k and cand:
        best, best_v = None, -1e9
        for i in cand:
            rel = float(np.dot(embed(POOL[i][0]), e))
            red = max([float(np.dot(embed(POOL[i][0]), embed(POOL[j][0])))
                       for j in chosen], default=0.0)
            v = rel - lam * red
            if v > best_v:
                best, best_v = i, v
        chosen.append(best); cand.remove(best)
    return [POOL[i] for i in chosen[::-1]]        # 同样最相关在后

def select_single_label(x, k=5, label='other'):
    same = [t for t in POOL if t[1] == label]
    rest = [t for t in POOL if t[1] != label]
    return (same + rest)[:k]

print(f"{'策略（k=5）':<18}{'准确率':>9}")
res = {}
for name, fn in [('随机', select_random), ('kNN', select_knn),
                 ('覆盖（每类 1 条）', select_coverage), ('多样性 MMR', select_mmr),
                 ('单标签（最坏）', select_single_label)]:
    a = accuracy(lambda x, f=fn: f(x, 5))
    res[name] = a
    print(f'{name:<18}{a:>9.0%}')

assert res['kNN'] > res['随机'], 'kNN 必须优于随机'
assert res['kNN'] > res['覆盖（每类 1 条）'], '相关性优于单纯覆盖'
assert res['单标签（最坏）'] <= res['随机'], '全部来自一类是最坏的'
print(f"\\n✅ kNN {res['kNN']:.0%} > 覆盖 {res['覆盖（每类 1 条）']:.0%} "
      f"> 随机 {res['随机']:.0%} ≈ 单标签 {res['单标签（最坏）']:.0%}")
print('   注意「覆盖」不是为了效果最优，它是为了**防止某类归零**——')
print('   而那是一个正确性问题（模块 00 练习 4 的 demos_coverage 诊断）。')"""),

    md("""## 2 · 数量的收益曲线：选对 1 条 ≈ 随机 20 条"""),

    code("""KS = [1, 2, 3, 5, 8, 12, 20]
print(f"{'k':>4}{'kNN':>9}{'随机':>9}{'覆盖':>9}")
curve = {'knn': [], 'random': [], 'coverage': []}
for k in KS:
    a_knn = accuracy(lambda x, k=k: select_knn(x, k))
    a_rnd = accuracy(lambda x, k=k: select_random(x, k))
    a_cov = accuracy(lambda x, k=k: select_coverage(x, k, per_label=max(1, k // 5)))
    curve['knn'].append(a_knn); curve['random'].append(a_rnd)
    curve['coverage'].append(a_cov)
    print(f'{k:>4}{a_knn:>9.0%}{a_rnd:>9.0%}{a_cov:>9.0%}')

knn_at_1 = curve['knn'][0]
rnd_at_20 = curve['random'][-1]
assert knn_at_1 >= rnd_at_20, 'kNN 的 k=1 应当不输随机的 k=20'
assert curve['random'][-1] > curve['random'][0], '随机选择时收益随 k 上升'
assert max(curve['knn']) - min(curve['knn']) < 0.15, 'kNN 曲线几乎是平的（已饱和）'
print(f'\\n✅ **kNN 的 k=1（{knn_at_1:.0%}）不输随机的 k=20（{rnd_at_20:.0%}）**，')
print(f'   而后者的 token 成本是前者的 20 倍。')
print('   选择是一次阶跃，数量是一条缓坡——**先做选择，再考虑数量**。')
print('   而多数团队的顺序是相反的：先把示例从 3 条加到 10 条（因为这最容易），')
print('   然后发现提升不明显，于是得出「few-shot 没什么用」的结论。')
print()
print('   两个与数量相关、容易被忽略的成本：')
print('   ① 示例占的 token 是从「能塞多少检索文档」里扣的（C33 的预算分配）；')
print('   ② 输入 token 数直接影响首 token 延迟。k 同时是一个容量参数。')"""),

    md("""## 3 · 分桶 kNN：兼顾相关性与前缀缓存

kNN 的隐藏成本是**每个请求的 prompt 前缀都不同 → 前缀缓存全丢**（C33 模块 05）。
分桶把前缀的种类压到很少。"""),

    code("""def build_buckets(n_buckets=4, seed=0):
    \"\"\"把示例池聚成 n_buckets 个簇（朴素 k-means），每簇预先算一套固定示例。\"\"\"
    X = np.stack([embed(t) for t, _ in POOL])
    rng = np.random.default_rng(seed)
    C = X[rng.permutation(len(POOL))[:n_buckets]].copy()
    for _ in range(20):
        a = np.argmax(X @ C.T, axis=1)
        for j in range(n_buckets):
            if (a == j).any():
                v = X[a == j].mean(axis=0)
                nv = np.linalg.norm(v)
                C[j] = v / nv if nv > 0 else C[j]
    return C, np.argmax(X @ C.T, axis=1)

def make_bucket_selector(n_buckets=4, k=5):
    C, assign = build_buckets(n_buckets)
    # 每个桶：桶内示例按与桶心的相似度排，最相似的放最后；不足则补覆盖
    bucket_demos = {}
    for j in range(n_buckets):
        members = [i for i in range(len(POOL)) if assign[i] == j]
        members.sort(key=lambda i: float(np.dot(embed(POOL[i][0]), C[j])))
        d = [POOL[i] for i in members][-k:]
        if len(d) < k:                                    # 覆盖保底
            have = {y for _, y in d}
            for l in LABELS:
                if l not in have:
                    extra = [t for t in POOL if t[1] == l]
                    if extra:
                        d = [extra[0]] + d
                if len(d) >= k:
                    break
        bucket_demos[j] = d[-k:]

    def selector(x):
        j = int(np.argmax(C @ embed(x)))
        return bucket_demos[j]
    selector.n_prefixes = n_buckets
    return selector

print(f"{'策略（k=5）':<22}{'准确率':>9}{'不同 prompt 前缀数':>20}")
sel_bucket = make_bucket_selector(4, 5)
rows = [
    ('随机（固定示例）', lambda x: select_random(x, 5), 1),
    ('分桶 kNN（4 桶）', sel_bucket, sel_bucket.n_prefixes),
    ('全局 kNN', lambda x: select_knn(x, 5), len(TEST)),
]
accs = {}
for name, fn, n_pref in rows:
    a = accuracy(fn)
    accs[name] = a
    print(f'{name:<22}{a:>9.0%}{n_pref:>20}')

assert accs['分桶 kNN（4 桶）'] >= accs['随机（固定示例）'], '分桶应当不差于随机'
assert accs['全局 kNN'] >= accs['分桶 kNN（4 桶）'], '全局 kNN 的相关性最好'
print('\\n✅ 分桶落在随机与全局 kNN 之间，而前缀只有 4 种（缓存仍然有效）。')
print('   这是一个真实的三方权衡：相关性 ↔ 缓存命中率 ↔ 实现复杂度。')
print('   在高 QPS、长 prompt 的场景下，全局 kNN 丢掉的缓存收益可能超过它带来的准确率。')"""),

    md("""## 4 · 顺序：同一批示例，三倍差距"""),

    code("""K = 5
print(f"{'顺序（kNN 选出的同一批 {} 条）'.format(K):<34}{'准确率':>9}")
a_last = accuracy(lambda x: select_knn(x, K, most_similar_last=True))
a_first = accuracy(lambda x: select_knn(x, K, most_similar_last=False))
print(f'{"最相似的放最后":<34}{a_last:>9.0%}')
print(f'{"最相似的放最前":<34}{a_first:>9.0%}')

assert a_last > a_first, '顺序造成显著差距'
ratio = a_last / a_first if a_first > 0 else float('inf')
print(f'\\n倍数: {ratio:.1f}×  —— 而这个改动的成本是**零**')

# 机制：相似度与位置加成是叠加的
x0 = TEST[0][0]
d_last = select_knn(x0, K, True)
print(f'\\n以「{x0}」为例，最相似的放最后时的示例序列:')
for i, (t, y) in enumerate(d_last):
    boost = 0.35 * (i / (K - 1))
    print(f'  [{i}] sim={sim(x0, t):.3f} + 位置加成 {boost:.3f} = '
          f'{sim(x0, t) + boost:.3f}  ({y}) {t}')
print('  → argmax 落在最后一条（相似度与位置加成指向同一个）')
d_first = select_knn(x0, K, False)
scores = [sim(x0, t) + 0.35 * (i / (K - 1)) for i, (t, _) in enumerate(d_first)]
print(f'\\n最相似的放最前时，argmax 落在第 {int(np.argmax(scores))} 条 '
      f'（{d_first[int(np.argmax(scores))][1]}）——两者相互抵消了')

assert int(np.argmax(scores)) != 0, '放最前时 argmax 不再是最相似的那条'
print('\\n✅ 顺序不是噪声，是一个有方向、可解释、零成本的超参数。')
print('   工程结论不是「把最像的放最后」（方向依模型而异），')
print('   而是**必须测，并且把测出来的顺序固定下来并进指纹**。')"""),

    code("""# --- 顺序的自由度实际上集中在「最后一条放谁」 ---
BASE_SET = select_coverage(None, k=10, per_label=2)      # 每类 2 条，共 10 条

print('固定同一个集合，只改「最后一条示例放谁」:')
last_rows = []
for j in range(len(BASE_SET)):
    d = [BASE_SET[i] for i in range(len(BASE_SET)) if i != j] + [BASE_SET[j]]
    a = accuracy(lambda x, d=d: d)
    last_rows.append((a, BASE_SET[j][1]))
    print(f'  最后一条 = {BASE_SET[j][1]:<9} acc {a:.0%}   ({BASE_SET[j][0]})')

last_accs = [a for a, _ in last_rows]
print(f'\\n只改最后一条: min {min(last_accs):.0%} ~ max {max(last_accs):.0%} '
      f'（跨度 {max(last_accs) - min(last_accs):.0%}）')

# 对比：随机整排列
rng2 = np.random.default_rng(0)
perm_accs = []
for _ in range(60):
    d = [BASE_SET[i] for i in rng2.permutation(len(BASE_SET))]
    perm_accs.append(accuracy(lambda x, d=d: d))
print(f'随机整排列 60 次: min {min(perm_accs):.0%} ~ max {max(perm_accs):.0%} '
      f'（跨度 {max(perm_accs) - min(perm_accs):.0%}）')

span_last = max(last_accs) - min(last_accs)
span_perm = max(perm_accs) - min(perm_accs)
assert span_last > 0.1, '「最后一条放谁」本身就造成可观的跨度'
assert span_perm >= span_last, '全排列的跨度不小于单自由度的跨度'
assert span_last / span_perm > 0.4, '而单自由度解释了跨度的相当一部分'
print(f'\\n✅ **「最后一条放谁」这一个自由度就解释了顺序效应的 '
      f'{span_last / span_perm:.0%}**（{span_last:.0%} / {span_perm:.0%}）。')
print('   在这个模拟器里原因是显式的：位置加成 recency·(i/(n-1)) 只在最后一条取到最大值。')
print()
print('   ⚠️ 一个必须说清的边界：**「打散标签」这个流行做法在本模拟器上并不成立**。')
print('   我们试过按标签分组 vs 打散，准确率与预测分布的集中度都没有稳定的方向。')
print('   原因也是显式的：本模拟器的偏置来自「最后一条是谁」，')
print('   而不是「末尾是否有一串同标签」——后者需要更丰富的位置效应才会出现。')
print('   真实模型确实同时有近因、首因与多数标签偏置，所以打散在那里可能有效。')
print()
print('   **可迁移的是方法，不是规则**：顺序是一个零成本超参数，')
print('   它必须在你自己的任务与模型上测（练习 2 会把它做成一次带留出集的搜索），')
print('   而不能照搬「把最像的放最后」或「打散标签」这类结论。')"""),

    md("""## 5 · 无内容探针与校准

一次调用测出标签先验。**它同时是一个可以放进 CI 的检查。**"""),

    code("""CONTENT_FREE = ['N/A', '', '[MASK]', '无']

def probe_prior(demos, probes=None):
    \"\"\"无内容探针：输入没有信息时模型输出什么 = 这套 prompt 的标签先验。\"\"\"
    probes = CONTENT_FREE if probes is None else probes
    return Counter(toy_lm(INSTR, demos, p) for p in probes)

d_other_last = [t for t in POOL if t[1] != 'other'] + [t for t in POOL if t[1] == 'other']
d_other_first = [t for t in POOL if t[1] == 'other'] + [t for t in POOL if t[1] != 'other']

print(f"{'示例顺序':<16}{'准确率':>9}{'无内容探针的输出':>26}")
best_last = max(range(len(BASE_SET)),
                key=lambda j: accuracy(
                    lambda x, j=j: [BASE_SET[i] for i in range(len(BASE_SET)) if i != j]
                                   + [BASE_SET[j]]))
d_best_last = ([BASE_SET[i] for i in range(len(BASE_SET)) if i != best_last]
               + [BASE_SET[best_last]])

for name, d in [('other 放最后', d_other_last), ('other 放最前', d_other_first),
                ('搜出的最优末条', d_best_last)]:
    a = accuracy(lambda x, d=d: d)
    pr = probe_prior(d)
    print(f'{name:<16}{a:>9.0%}{str(dict(pr)):>26}')

p_last = probe_prior(d_other_last)
p_first = probe_prior(d_other_first)
assert set(p_last) != set(p_first), '同一个示例集合，只改顺序，先验就变了'
print('\\n✅ 无内容探针只要一次调用，就把「偏置」从模糊担忧变成了可测的量。')
print('   而它测出来的东西可以直接进 CI：**先验不该随一次 prompt 改动而改变**。')"""),

    code("""# --- 用探针做校准（faithful 版本：需要一个标签分数向量）---
def label_scores(demos, x, recency=0.35):
    \"\"\"把 kNN 打分聚合成**每个标签一个分数**。

    这一步是校准的前提：减先验作用在标签分数上，
    而 toy_lm 只返回硬标签，所以必须先把它展开成分数向量。
    真实系统里这个向量就是标签 token 的 logprobs。\"\"\"
    E = np.stack([embed(t) for t, _ in demos])
    s = E @ embed(x)
    n = len(demos)
    s = s + np.array([recency * (i / (n - 1) if n > 1 else 1.0) for i in range(n)])
    out = {l: -1e9 for l in LABELS}
    for (t, y), sc in zip(demos, s):
        out[y] = max(out[y], float(sc))
    return out

def predict(demos, x, calib=None):
    sc = label_scores(demos, x)
    if calib is not None:
        sc = {l: sc[l] - calib.get(l, 0.0) for l in LABELS}
    return max(LABELS, key=lambda l: sc[l])

def acc_scored(demos, calib=None):
    return sum(1 for x, g in TEST if predict(demos, x, calib) == g) / len(TEST)

print(f"{'配置':<20}{'未校准':>9}{'减先验校准后':>14}")
gains = {}
for name, d in [('other 放最后', d_other_last), ('other 放最前', d_other_first),
                ('搜出的最优末条', d_best_last)]:
    calib = label_scores(d, 'N/A')                  # ← 无内容探针给出的标签先验
    raw, cal = acc_scored(d), acc_scored(d, calib)
    gains[name] = cal - raw
    print(f'{name:<20}{raw:>9.0%}{cal:>14.0%}')

print('\\n「other 放最前」这个偏置严重的配置，探针给出的标签先验:')
cf = label_scores(d_other_first, 'N/A')
for l in LABELS:
    print(f'  {l:<9}{cf[l]:>8.3f}')

assert gains['other 放最前'] > 0, '偏置严重的配置上，校准必须有收益'
assert acc_scored(d_other_first, label_scores(d_other_first, 'N/A')) >= \\
       acc_scored(d_other_last), '校准把坏配置救回到好配置的水平'
assert gains['other 放最后'] >= 0, '没有偏置时校准不该造成损害'
print(f"\\n✅ 减先验校准把「other 放最前」从 {acc_scored(d_other_first):.0%} 提到 "
      f"{acc_scored(d_other_first, cf):.0%}——")
print(f"   与最好的顺序配置（{acc_scored(d_other_last):.0%}）持平。")
print('   而在本来就没有偏置的配置上，它不造成损害。')
print()
print('   ⚠️ 两个必须说清的前提：')
print('   ① **校准需要一个标签分数向量**。上面第一步 label_scores 就是为此存在的——')
print('      真实系统里它是标签 token 的 logprobs。**拿不到 logprobs 的 API 上这条路走不通。**')
print('   ② 减先验隐含假设**真实标签分布接近均匀**。本课的测试集恰好是每类 2 条（均匀），')
print('      所以校准有效。如果真实分布本身严重倾斜（比如 80% 都是兜底类），')
print('      减先验会把那 80% 打掉——此时该做的是把先验减到「真实分布」而不是「均匀」。')
print()
print('   拿不到 logprobs 时的替代：搜一遍顺序（练习 2）与多排列投票。')
print('   一条必须进监控的指标：**预测标签分布**。它的 PSI 会同时抓到')
print('   顺序偏置、示例漂移与模型换版本——而这三件事在端到端准确率上都只表现为「变差了」。')"""),

    md("""## 6 · 泄漏：kNN 选择让它几乎必然发生"""),

    code("""# 把测试样本混进示例池 —— 一个很容易发生的事故
LEAKED_POOL = POOL + [(x, y) for x, y in TEST]

def select_knn_from(pool, x, k=5):
    e = embed(x)
    s = np.array([float(np.dot(embed(t), e)) for t, _ in pool])
    idx = list(np.argsort(-s)[:k])[::-1]
    return [pool[i] for i in idx]

clean = accuracy(lambda x: select_knn_from(POOL, x, 5))
leaked = accuracy(lambda x: select_knn_from(LEAKED_POOL, x, 5))
print(f'干净池: {clean:.0%}')
print(f'泄漏池: {leaked:.0%}   （虚高 {leaked - clean:+.0%}）')

# 泄漏发生的频率：被选中的示例里有多少就是测试样本自己
test_texts = {x for x, _ in TEST}
self_hits = sum(1 for x, _ in TEST
                if any(t == x for t, _ in select_knn_from(LEAKED_POOL, x, 5)))
print(f'\\n有 {self_hits}/{len(TEST)} 道题的示例里**包含它自己**')
assert leaked > clean, '泄漏必然造成虚高'
assert self_hits == len(TEST), 'kNN 让「选到自己」几乎必然发生'
print('✅ kNN 选择让泄漏几乎必然发生——因为「与输入最相似的示例」在有交集时就是输入自己。')

# --- 三条 CI 检查 ---
def leakage_check(pool, test, holdout=()):
    problems = []
    pt = {x for x, _ in pool} & {x for x, _ in test}
    if pt:
        problems.append(f'示例池与评测集有 {len(pt)} 条交集')
    ph = {x for x, _ in pool} & {x for x, _ in holdout}
    if ph:
        problems.append(f'示例池与留出集有 {len(ph)} 条交集')
    for x, _ in test:
        for dt, dy in pool:
            if dy in x:                    # 示例的答案出现在测试输入里
                problems.append(f'示例答案 {dy!r} 出现在测试输入 {x!r} 里')
                break
    return problems

assert leakage_check(POOL, TEST) == [], f'干净池应当通过: {leakage_check(POOL, TEST)}'
assert leakage_check(LEAKED_POOL, TEST), '泄漏池必须被抓到'
print('\\n✅ 泄漏检查是一次集合求交，零成本、零误报，必须进阻断项。')
print('   一个真实且容易发生的路径：「用线上日志做示例池，也用线上日志做评测集」。')
print('   按时间切分不够——同一个用户的同一个问题可能出现在两边。')
print('   **必须按稳定 ID 去重后再切分。**')"""),

    md("""## 7 · 示例池运维：覆盖退化与「选中示例平均相似度」"""),

    code("""def pool_health(pool, selector, test=None, min_per_label=2):
    test = TEST if test is None else test
    per_label = Counter(y for _, y in pool)
    chosen_sims = []
    chosen_counter = Counter()
    for x, _ in test:
        d = selector(x)
        chosen_sims.append(float(np.mean([sim(x, t) for t, _ in d])) if d else 0.0)
        for t, _ in d:
            chosen_counter[t] += 1
    return dict(size=len(pool),
                min_per_label=min(per_label.get(l, 0) for l in LABELS),
                missing_labels=[l for l in LABELS if per_label.get(l, 0) == 0],
                mean_chosen_sim=float(np.mean(chosen_sims)),
                never_chosen=sum(1 for t, _ in pool if chosen_counter[t] == 0))

sel5 = lambda x: select_knn(x, 5)
h_full = pool_health(POOL, sel5)
print('健康池:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in h_full.items()})

# --- 覆盖退化：billing 类被稀释掉 ---
degraded = [t for t in POOL if t[1] != 'billing']
h_deg = pool_health(degraded, lambda x: select_knn_from(degraded, x, 5))
print('缺 billing:', {k: (round(v, 3) if isinstance(v, float) else v)
                      for k, v in h_deg.items()})
acc_deg = accuracy(lambda x: select_knn_from(degraded, x, 5))
by_label_deg = defaultdict(list)
for x, g in TEST:
    by_label_deg[g].append(float(toy_lm(INSTR, select_knn_from(degraded, x, 5), x) == g))
print(f'  端到端 {acc_deg:.0%}；billing 类的准确率 '
      f'{np.mean(by_label_deg["billing"]):.0%}')
assert h_deg['missing_labels'] == ['billing']
assert np.mean(by_label_deg['billing']) == 0.0, '某类没示例 → 该类归零'

# --- 分布漂移：线上话题变了 ---
DRIFTED_TEST = [('接口返回 502 网关错误', 'bug'), ('想要 webhook 回调', 'feature'),
                ('企业年付有没有折扣', 'billing'), ('SSO 单点登录怎么配', 'account'),
                ('文档写得挺清楚', 'other')]
sim_normal = pool_health(POOL, sel5)['mean_chosen_sim']
sim_drift = pool_health(POOL, sel5, test=DRIFTED_TEST)['mean_chosen_sim']
print(f'\\n选中示例与输入的平均相似度: 正常流量 {sim_normal:.3f} → 漂移流量 {sim_drift:.3f}')
assert sim_drift < sim_normal, '分布漂移时这个指标会掉下来'
print('✅ 「选中示例与输入的平均相似度」是这一层最有信息量的**无真值**指标：')
print('   它不需要标注，而它同时反映池子的覆盖度与线上分布的变化。')
print('   它掉下来时该做的是**补池子**，而不是改 prompt。')
print(f"\\n   另外 never_chosen = {h_full['never_chosen']}：从未被选中的示例可以删——")
print('   池子只加不删会让 kNN 变慢而效果不再提升。')"""),

    md("""## 8 · 示例卡 + 门禁"""),

    code("""def demo_card(pool, selector, order_policy, test, holdout=(), baseline=None):
    h = pool_health(pool, selector, test)
    seq = selector(test[0][0])
    fp = hashlib.sha256(json.dumps(
        dict(demos=[[a, b] for a, b in seq], order_policy=order_policy),
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    by_label = defaultdict(list)
    for x, g in test:
        by_label[g].append(float(toy_lm(INSTR, selector(x), x) == g))
    return dict(pool_size=h['size'], min_per_label=h['min_per_label'],
                missing_labels=h['missing_labels'],
                order_policy=order_policy, prompt_fp=fp,
                leakage=leakage_check(pool, test, holdout),
                mean_chosen_sim=h['mean_chosen_sim'],
                by_label={l: float(np.mean(v)) for l, v in by_label.items()},
                end_to_end=float(np.mean([v for vs in by_label.values() for v in vs])),
                probe_prior=list(probe_prior(seq).keys()))

def demo_gate(card, baseline, min_per_label=2, sigma=0.05):
    blocking, warn = [], []
    if card['leakage']:
        blocking.append(f"泄漏: {card['leakage'][:1]}")
    if card['missing_labels']:
        blocking.append(f"标签没有示例: {card['missing_labels']}")
    if card['min_per_label'] < min_per_label:
        blocking.append(f"每类最少示例数 {card['min_per_label']} < {min_per_label}")
    if not card['order_policy']:
        blocking.append('order_policy 未显式声明')
    for l, a in card['by_label'].items():
        b = baseline['by_label'].get(l)
        if b is not None and a < b - 2 * sigma:
            blocking.append(f'{l} 类准确率下降 {b:.2f} → {a:.2f}（> 2σ）')
    if card['mean_chosen_sim'] < baseline['mean_chosen_sim'] * 0.9:
        warn.append(f"选中示例平均相似度 {card['mean_chosen_sim']:.3f} "
                    f"< 基线的 90%（{baseline['mean_chosen_sim'] * 0.9:.3f}）——补池子")
    if set(card['probe_prior']) != set(baseline['probe_prior']):
        warn.append(f"标签先验变了: {baseline['probe_prior']} → {card['probe_prior']}")
    return blocking, warn

BASE_CARD = demo_card(POOL, sel5, 'knn_most_similar_last', TEST)
print('基线卡:', {k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in BASE_CARD.items() if k != 'by_label'})
assert demo_gate(BASE_CARD, BASE_CARD) == ([], [])

cards = {
    '泄漏池': demo_card(LEAKED_POOL, lambda x: select_knn_from(LEAKED_POOL, x, 5),
                      'knn_most_similar_last', TEST),
    '缺 billing': demo_card(degraded, lambda x: select_knn_from(degraded, x, 5),
                          'knn_most_similar_last', TEST),
    '未声明顺序': {**BASE_CARD, 'order_policy': ''},
    '漂移流量': demo_card(POOL, sel5, 'knn_most_similar_last', DRIFTED_TEST),
}
for name, c in cards.items():
    b, w = demo_gate(c, BASE_CARD)
    print(f'{name:<12} 阻断 {len(b)} 项 {b[:1]} | 警告 {len(w)} 项 {w[:1]}')

assert demo_gate(cards['泄漏池'], BASE_CARD)[0]
assert demo_gate(cards['缺 billing'], BASE_CARD)[0]
assert demo_gate(cards['未声明顺序'], BASE_CARD)[0]
print('\\n✅ 四项确定性阻断（泄漏 / 覆盖 / 每类下限 / 顺序未声明）+ 两项报警。')
print('   最容易被忽略的是「order_policy 未显式声明」：')
print('   它把「示例顺序是代码里列表的书写顺序」这个默认状态变成一次门禁失败。')"""),

    md("""## ✏️ 练习 1：混合选择器

实现 `select_hybrid(x, k, per_label_floor=1)`：**先保底覆盖，再用剩余额度做 kNN**。

- 先为每个标签取 `per_label_floor` 条（取该标签下与 `x` 最相似的）
- 剩下的额度用全池 kNN 填（跳过已选的）
- 最终顺序：**最相似的放最后**

它要同时满足两个目标：不漏标签（正确性）+ 相关性尽量高（效果）。"""),

    code("""def select_hybrid(x, k=8, per_label_floor=1):
    \"\"\"返回有序的示例列表（最相似的放最后）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
d = select_hybrid(TEST[0][0], k=8, per_label_floor=1)
assert len(d) == 8, len(d)
assert set(y for _, y in d) == set(LABELS), '每个标签都要有（保底覆盖）'
# 最相似的放最后
sims = [sim(TEST[0][0], t) for t, _ in d]
assert sims[-1] == max(sims), '最相似的必须在最后'
# 效果：不差于纯覆盖
a_hybrid = accuracy(lambda x: select_hybrid(x, 8, 1))
a_cov = accuracy(lambda x: select_coverage(x, 8, per_label=2))
a_knn = accuracy(lambda x: select_knn(x, 8))
print(f'混合 {a_hybrid:.0%} | 纯覆盖 {a_cov:.0%} | 纯 kNN {a_knn:.0%}')
assert a_hybrid >= a_cov, '混合应当不差于纯覆盖'
# k 不足以覆盖所有标签时，保底优先
d_small = select_hybrid(TEST[0][0], k=5, per_label_floor=1)
assert len(d_small) == 5 and len(set(y for _, y in d_small)) == 5
print('✅ 练习 1 通过：既不漏标签，相关性也拿到了')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def select_hybrid(x, k=8, per_label_floor=1):
    e = embed(x)
    scored = [(float(np.dot(embed(t), e)), i) for i, (t, _) in enumerate(POOL)]
    chosen = []
    # ① 保底覆盖：每类取最相似的 per_label_floor 条
    for l in LABELS:
        cand = sorted([(s, i) for s, i in scored if POOL[i][1] == l], reverse=True)
        for s, i in cand[:per_label_floor]:
            if len(chosen) < k:
                chosen.append(i)
    # ② 剩余额度用全池 kNN 填
    for s, i in sorted(scored, reverse=True):
        if len(chosen) >= k:
            break
        if i not in chosen:
            chosen.append(i)
    # ③ 顺序：最相似的放最后
    chosen.sort(key=lambda i: float(np.dot(embed(POOL[i][0]), e)))
    return [POOL[i] for i in chosen[:k]]

d = select_hybrid(TEST[0][0], k=8, per_label_floor=1)
assert len(d) == 8 and set(y for _, y in d) == set(LABELS)
sims = [sim(TEST[0][0], t) for t, _ in d]
assert sims[-1] == max(sims)
assert accuracy(lambda x: select_hybrid(x, 8, 1)) >= \\
       accuracy(lambda x: select_coverage(x, 8, per_label=2))
print('✅ 参考答案 1 通过')
print('   三步的顺序不能换：**保底优先**。')
print('   如果先填 kNN 再补覆盖，k 较小时 kNN 会把额度用光，覆盖就补不进去了——')
print('   而漏一个标签是正确性问题（该类归零），比相关性差一点严重得多。')"""),

    md("""## ✏️ 练习 2：顺序搜索

示例顺序是一个零成本超参数，所以它值得**搜**。

实现 `best_order(demos, n_trials, seed)`：随机采样 `n_trials` 个排列，
返回 `(最好的排列, 它的准确率, 所有排列准确率的 (min, mean, max))`。

然后回答一个工程问题：**这个搜索会不会过拟合？**
实现 `order_search_with_holdout(demos, n_trials, seed)`：
在前一半测试样本上搜、在后一半上复核，返回 `(搜索集分数, 留出集分数)`。"""),

    code("""def best_order(demos, n_trials=60, seed=0):
    \"\"\"返回 (best_perm, best_acc, (min_acc, mean_acc, max_acc))。\"\"\"
    # TODO
    raise NotImplementedError

def order_search_with_holdout(demos, n_trials=60, seed=0):
    \"\"\"前一半测试样本搜，后一半复核。返回 (search_acc, holdout_acc)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
D8 = select_coverage(None, k=10, per_label=2)
perm, acc_best, (lo, mean_, hi) = best_order(D8, n_trials=60, seed=0)
print(f'排列搜索: 最好 {acc_best:.0%} | 分布 min {lo:.0%} / mean {mean_:.0%} / max {hi:.0%}')
assert len(perm) == len(D8) and sorted(perm) == sorted(D8)
assert acc_best == hi
assert hi > lo, '不同排列的分数必须有差异——顺序是一个真实的超参数'
assert acc_best >= accuracy(lambda x: D8), '搜出来的排列不该差于原始顺序'

s_acc, h_acc = order_search_with_holdout(D8, n_trials=60, seed=0)
print(f'搜索集 {s_acc:.0%} → 留出集 {h_acc:.0%}   （差 {s_acc - h_acc:+.0%}）')
assert s_acc >= h_acc, '在搜索集上搜出来的排列，在留出集上通常更差'
print('✅ 练习 2 通过：顺序值得搜，但**必须在留出集上复核**')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def best_order(demos, n_trials=60, seed=0):
    rng = np.random.default_rng(seed)
    accs, best, best_a = [], list(demos), -1.0
    for _ in range(n_trials):
        perm = [demos[i] for i in rng.permutation(len(demos))]
        a = accuracy(lambda x, p=perm: p)
        accs.append(a)
        if a > best_a:
            best, best_a = perm, a
    return best, best_a, (min(accs), float(np.mean(accs)), max(accs))

def order_search_with_holdout(demos, n_trials=60, seed=0):
    half = len(TEST) // 2
    search, holdout = TEST[:half], TEST[half:]
    rng = np.random.default_rng(seed)
    best, best_a = list(demos), -1.0
    for _ in range(n_trials):
        perm = [demos[i] for i in rng.permutation(len(demos))]
        a = accuracy(lambda x, p=perm: p, test=search)
        if a > best_a:
            best, best_a = perm, a
    return best_a, accuracy(lambda x, p=best: p, test=holdout)

perm, acc_best, (lo, mean_, hi) = best_order(D8, 60, 0)
assert acc_best == hi and hi > lo
s_acc, h_acc = order_search_with_holdout(D8, 60, 0)
assert s_acc >= h_acc
print('✅ 参考答案 2 通过')
print(f'   搜索集 {s_acc:.0%} vs 留出集 {h_acc:.0%}——**这个差就是过拟合**。')
print('   顺序只有 n! 种，而测试集只有几条样本，所以「搜到一个好排列」很容易，')
print('   「搜到一个真的更好的排列」不容易。这正是模块 03 要系统处理的问题：')
print('   **搜索空间越大，在搜索集上过拟合越容易**，而 10 个示例的排列空间是 10! ≈ 363 万。')"""),

    md("""## ✏️ 练习 3：泄漏检测（按稳定 ID + 近重复）

第 6 节的检查按精确文本匹配。真实系统里泄漏通常是**近重复**：
同一个问题的两种措辞分别落在示例池与评测集里。

实现 `leakage_report(pool, test, id_of, thr=0.85)`：
- `id_of(text)` 给出稳定 ID（同一个 ID 视为同一条样本）
- 返回 `dict(exact_id=[...], near_dup=[(pool_text, test_text, sim)], n_flagged=int)`
- `near_dup` 只报相似度 ≥ `thr` 且**不同 ID** 的对（同 ID 已被 `exact_id` 抓到）"""),

    code("""def leakage_report(pool, test, id_of, thr=0.85):
    \"\"\"返回 dict(exact_id, near_dup, n_flagged)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def id_of(text):
    return hashlib.md5(text.encode()).hexdigest()[:8]

# a) 干净
r = leakage_report(POOL, TEST, id_of)
assert r['exact_id'] == [] and r['n_flagged'] == 0, r

# b) 同 ID 泄漏
r2 = leakage_report(POOL + [TEST[0]], TEST, id_of)
assert len(r2['exact_id']) == 1, r2['exact_id']
assert r2['n_flagged'] >= 1

# c) 近重复泄漏：换个措辞
NEAR = ('打开报表就崩溃了', 'bug')          # TEST[0] 是 '打开报表就崩溃'
r3 = leakage_report(POOL + [NEAR], TEST, id_of, thr=0.8)
print('近重复:', [(a, b, round(s, 3)) for a, b, s in r3['near_dup']])
assert r3['exact_id'] == [], '不同 ID，所以不是 exact'
assert r3['near_dup'], '必须被近重复检查抓到'
assert r3['n_flagged'] >= 1

# d) 阈值抬高 → 不报
r4 = leakage_report(POOL + [NEAR], TEST, id_of, thr=0.999)
assert r4['near_dup'] == []
print('✅ 练习 3 通过：精确 ID 与近重复两条路都覆盖')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def leakage_report(pool, test, id_of, thr=0.85):
    test_ids = {id_of(x): x for x, _ in test}
    exact = [x for x, _ in pool if id_of(x) in test_ids]
    near = []
    for px, _ in pool:
        if id_of(px) in test_ids:
            continue                       # 同 ID 已由 exact 覆盖
        for tx, _ in test:
            s = sim(px, tx)
            if s >= thr:
                near.append((px, tx, s))
    return dict(exact_id=sorted(set(exact)), near_dup=near,
                n_flagged=len(set(exact)) + len(near))

assert leakage_report(POOL, TEST, id_of)['n_flagged'] == 0
assert len(leakage_report(POOL + [TEST[0]], TEST, id_of)['exact_id']) == 1
r3 = leakage_report(POOL + [('打开报表就崩溃了', 'bug')], TEST, id_of, thr=0.8)
assert r3['exact_id'] == [] and r3['near_dup']
assert leakage_report(POOL + [('打开报表就崩溃了', 'bug')], TEST, id_of,
                      thr=0.999)['near_dup'] == []
print('✅ 参考答案 3 通过')
print('   两条路的分工：')
print('   ① exact_id 是**确定性**的，零误报，直接阻断；')
print('   ② near_dup 有一个阈值，所以它会误报——它应当是「进人工复核队列」而不是阻断。')
print('   这个分级与 C68 模块 04 一致；而 thr 的取值要用已知的重复对去校准，')
print('   不是拍一个 0.85。')"""),

    md("""## ✏️ 练习 4：示例池的淘汰与补充

实现 `evolve_pool(pool, selector, traffic, max_size, min_per_label)`：

- 统计 `traffic` 上每条示例被选中的次数
- **淘汰**：从未被选中的示例，按「该类剩余数不低于 `min_per_label`」的约束删
- 若池子仍超过 `max_size`，继续删被选中次数最少的（同样受约束）
- 返回 `(新池子, dict(removed=int, kept_per_label=dict))`

约束优先于淘汰：**任何情况下都不能让某类低于 `min_per_label`**。"""),

    code("""def evolve_pool(pool, selector, traffic, max_size, min_per_label=2):
    \"\"\"返回 (new_pool, dict(removed, kept_per_label))。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
sel = lambda x: select_knn_from(POOL, x, 5)
traffic = [x for x, _ in TEST] + [x for x, _ in DRIFTED_TEST]

new_pool, info = evolve_pool(POOL, sel, traffic, max_size=12, min_per_label=2)
print(f"淘汰 {info['removed']} 条 → 池子 {len(new_pool)} 条")
print('每类保留:', info['kept_per_label'])

assert len(new_pool) <= 12
assert all(info['kept_per_label'][l] >= 2 for l in LABELS), '约束优先于淘汰'
assert info['removed'] == len(POOL) - len(new_pool)
# 被高频选中的示例必须保留
counts = Counter()
for x in traffic:
    for t, _ in sel(x):
        counts[t] += 1
top = [t for t, _ in counts.most_common(3)]
assert all(any(t == pt for pt, _ in new_pool) for t in top), '高频示例必须保留'

# max_size 小到与约束冲突时，约束赢
tight, info_t = evolve_pool(POOL, sel, traffic, max_size=5, min_per_label=2)
assert len(tight) >= 2 * len(LABELS), '约束赢：池子不会小于 min_per_label × 标签数'
print(f'max_size=5 但约束要求 ≥ {2 * len(LABELS)} → 实际 {len(tight)} 条')
print('✅ 练习 4 通过：淘汰受覆盖约束，且约束优先')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def evolve_pool(pool, selector, traffic, max_size, min_per_label=2):
    counts = Counter()
    for x in traffic:
        for t, _ in selector(x):
            counts[t] += 1
    remaining = list(pool)
    # 删除顺序：被选中次数少的先删
    order = sorted(range(len(remaining)), key=lambda i: (counts[remaining[i][0]],
                                                         remaining[i][0]))
    removed = 0
    for i in order:
        if len(remaining) <= max_size:
            break
        item = remaining[i] if i < len(remaining) else None
        if item is None or item not in remaining:
            continue
        label = item[1]
        per = Counter(y for _, y in remaining)
        if per[label] - 1 < min_per_label:
            continue                       # 约束优先：不能让这一类低于下限
        remaining.remove(item); removed += 1
    per = Counter(y for _, y in remaining)
    return remaining, dict(removed=removed,
                           kept_per_label={l: per.get(l, 0) for l in LABELS})

new_pool, info = evolve_pool(POOL, sel, traffic, max_size=12, min_per_label=2)
assert len(new_pool) <= 12 and all(info['kept_per_label'][l] >= 2 for l in LABELS)
tight, _ = evolve_pool(POOL, sel, traffic, max_size=5, min_per_label=2)
assert len(tight) >= 2 * len(LABELS)
print('✅ 参考答案 4 通过')
print('   两个设计点：')
print('   ① **约束优先于淘汰**——max_size=5 与「每类 ≥2」冲突时，约束赢。')
print('      因为漏一个标签是正确性问题，而池子大一点只是成本问题。')
print('   ② 淘汰依据是「被选中次数」而不是「加入时间」。')
print('      按时间淘汰会删掉稀有类的老样本，而它们恰恰是覆盖度的来源。')
print('   还有一条不在代码里的纪律（与 C68 模块 05 同构）：')
print('   从线上回灌样本进池子时要限制回灌占比——')
print('   回灌样本的分布已经被当前系统塑造过，全用它们会形成闭环。')"""),

    md("""## 🧪 真实工程胶囊：示例选择的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 选择器：分桶 kNN（相关性 vs 前缀缓存的折中，讲解第 2 节）
# ══════════════════════════════════════════════════════════════════
#   离线：把示例池 embed → k-means 成 N 个桶（N = 8~32）
#         每个桶预先算好一套**有序**示例，存成 demos/bucket_{j}.jsonl
#   在线：embed(query) → 找桶 → 直接取那套示例
#   收益：prompt 前缀只有 N 种 → 前缀缓存仍然有效（C33 模块 05）

# ══════════════════════════════════════════════════════════════════
# B. 顺序：显式声明 + 固定 + 进指纹（讲解第 4 节）
# ══════════════════════════════════════════════════════════════════
ORDER_POLICY = 'interleave_labels+most_similar_last'   # ← 写在配置里，不是代码里
def order_demos(demos, query, policy=ORDER_POLICY):
    if 'interleave_labels' in policy:
        demos = interleave_by_label(demos)
    if 'most_similar_last' in policy:
        demos = sorted(demos, key=lambda d: cos(enc(query), enc(d.input)))
    return demos
#   CI 检查：用 policy 重算一次序列，与实际发送的序列逐条比对，不一致就阻断
#   （讲解第 8 节 —— 它抓的是「有人在代码里插了一条示例但没改配置」）

# ══════════════════════════════════════════════════════════════════
# C. 无内容探针：一次调用，进 CI（讲解第 5 节）
# ══════════════════════════════════════════════════════════════════
for probe in ['N/A', '', '[MASK]']:
    out = call_model(render(probe, DEMOS))
    log.info('content_free_probe', extra=dict(probe=probe, out=out, prompt_fp=FP))
#   断言：先验不该随一次 prompt 改动而改变（改变 → 报警）
#   有 logprobs 时可以做真正的减先验校准：
#     logits[label] -= logits_content_free[label]  然后取 argmax

# ══════════════════════════════════════════════════════════════════
# D. 泄漏：按稳定 ID 切分（讲解第 6 节 / 练习 3）
# ══════════════════════════════════════════════════════════════════
# 1) 全部样本先按 stable_id 去重
# 2) 再按 id 的哈希分到 pool / dev / test / holdout（**不要按时间切**）
# 3) CI：pool ∩ test == ∅（阻断）；近重复报告进人工复核（不阻断）

# ══════════════════════════════════════════════════════════════════
# E. 池运维（讲解第 7 节 / 练习 4）
# ══════════════════════════════════════════════════════════════════
# 打点：selected_demo_ids、mean_chosen_similarity、per_label_pool_size
# 阻断：某标签池内数量 < 下限
# 报警：mean_chosen_similarity 相对基线掉 > 10%  → **补池子，不是改 prompt**
# 定期：删除从未被选中的示例；从线上回灌时限制 from_production 占比（C68-05）
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| 三个维度的收益量级差一个数量级 | 选择阶跃 / 数量缓坡 / 顺序免费 | 讲解 1 |
| 选对 1 条 ≈ 随机 20 条 | kNN@1 不输随机@20 | 第 2 节 |
| kNN 曲线在很小的 k 就饱和 | 而随机曲线一直缓升 | 第 2 节 |
| kNN 与前缀缓存直接冲突；分桶是折中 | 前缀从 N_test 种压到 4 种 | 第 3 节 |
| 同一批示例，只改顺序，三倍差距 | 0.90 vs 0.30 | 第 4 节 |
| 「打散标签」在本模拟器上无稳定收益 | 可迁移的是方法不是规则 | 第 4 节 |
| 无内容探针一次调用测出标签先验 | 同一集合、不同顺序 → 先验从 other 变成 account | 第 5 节 |
| 减先验校准把最差顺序救回来 | 50% → 70%（与「other 放最后」持平；表里最好的配置是 80%）；需要 logprobs 且假设真实分布均匀 | 第 5 节 |
| kNN 让示例泄漏几乎必然发生 | 10/10 道题的示例里包含它自己 | 第 6 节 |
| 某类没有示例 → 该类准确率归零 | 这是正确性问题不是效果问题 | 第 7 节 |
| 「选中示例平均相似度」是最好的无真值指标 | 漂移流量上它明显下降 | 第 7 节 |
| 顺序搜索会过拟合 | 搜索集 vs 留出集有差 | 练习 2 |

下一模块：**03 · 自动提示优化**——
搜索空间 + 评分函数 = 一次优化；而它最大的风险是在留出集上不成立。"""),
]
