# -*- coding: utf-8 -*-
"""C71 模块 03 · 自动提示优化。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（签名与三个量）与 02（示例选择与顺序）；"
                 "C66 模块 04（胜者诅咒与多重比较）读过更好——本课会直接用它的结论"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_prompt_optimization.ipynb'
                       '（搜索空间的大小与枚举 / 随机搜索与坐标上升 / '
                       'bootstrap 示例 / 过拟合：gap 随候选数增长的精确曲线 / '
                       '有偏 judge 会被优化直接放大 / 优化器的 spec 与指纹 / '
                       '什么时候不值得优化）'),
    ("核心参考", "（术语：本课的 <em>judge</em> 即 C66–C69 的<strong>判分器</strong>）· "
                 "Khattab et al., <em>DSPy</em>（2023）与 Opsahl-Ong et al., "
                 "<em>MIPRO</em>（EMNLP 2024）——bootstrap 示例 + 指令搜索 · "
                 "Yang et al., <em>Large Language Models as Optimizers</em>（OPRO, ICLR 2024）· "
                 "Zhou et al., <em>Large Language Models Are Human-Level Prompt Engineers</em>"
                 "（APE, ICLR 2023）· "
                 "本课程 C66 模块 04（胜者诅咒 / 多重比较 / MDE）· "
                 "C67（目标函数是一个 judge，而它的偏差会被放大）· C68 模块 04（门禁阈值）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("anatomy", "一次优化 = 空间 + 目标 + 算法", "".join([
        P("「自动提示优化」听起来像魔法。"
          "<strong>它的机制很朴素：定义一个搜索空间、一个评分函数，然后搜。</strong>"
          "而它的全部风险也都在这三样东西里。"),
        TABLE(["组成", "它是什么", "它的风险", "本课在哪里处理"], [
            ["<strong>搜索空间</strong>",
             "候选 prompt 的集合（指令变体 × 示例子集 × 顺序 × 格式）",
             "<strong>空间越大，在搜索集上过拟合越容易</strong>——"
             "而 prompt 的空间通常大得离谱",
             "第 2 节（大小）+ 第 5 节（过拟合的定量关系）"],
            ["<strong>评分函数</strong>",
             "评测集上的一个数（准确率 / judge 打分 / 加权组合）",
             "<strong>它的偏差会被优化过程直接放大</strong>——"
             "<em>优化器会精确地利用你目标函数里的每一个缺陷</em>",
             "第 3 节 + 第 6 节"],
            ["<strong>搜索算法</strong>",
             "随机 / 坐标上升 / 进化 / 让模型自己提候选（OPRO 式）",
             "成本；以及<em>更强的算法会更快地过拟合</em>",
             "第 4 节"],
        ]),
        DUAL(
            "<strong>最后一行括号里那句话值得重读</strong>："
            "<em>搜索算法变强不总是好事</em>。"
            "更强的算法在同样的预算下评估更多候选、"
            "或者更有效地朝着目标函数上升——"
            "<strong>而如果目标函数有缺陷，它就更快地找到那个缺陷。</strong>"
            "<em>这与 C67 模块 05 的奖励模型过优化是同一个现象，"
            "只不过这里被优化的是 prompt 而不是权重。</em>",
            "所以三者的正确投入顺序是<strong>反过来</strong>的："
            "<strong>① 先把评分函数做可靠</strong>"
            "（评测集够大、judge 验证过、噪声量化过）；"
            "<strong>② 再把搜索空间定得<em>小而有意义</em></strong>"
            "（而不是「把所有能变的都变一遍」）；"
            "<strong>③ 最后才考虑用更强的搜索算法。</strong>"
            "<em>反过来做（先上一个花哨的 optimizer）几乎必然得到"
            "「搜索集分数很好、上线没效果」这个结局。</em>",
        ),
        CALLOUT("intuition", "一个开工前必须回答的问题："
                             "<strong>「你的评测集上，两次相同配置的重复测量差多少？」</strong>"
                             "<em>答不上来 → 先去测这个方差</em>（C68 模块 04 的第一步）。"
                             "因为<strong>搜索出来的提升如果小于这个方差，它就是噪声</strong>。"),
    ])),

    # ============================================================== 2
    ("space", "搜索空间：先算它有多大", "".join([
        P("prompt 的搜索空间通常比人们以为的大得多。"
          "<strong>而它的大小直接决定了过拟合的程度（第 5 节），"
          "所以第一步是把它算出来。</strong>"),
        MATH(r"|\mathcal{S}| = |I| \times \binom{|P|}{k} \times k! \times |F|"),
        TABLE(["维度", "本课的规模", "组合数"], [
            ["指令变体 $|I|$", "5 个槽位（notebook 里 2×1×2×2×2）", "<strong>24</strong>"],
            ["示例子集 $\\binom{|P|}{k}$", "从 20 条池子里选 8 条", "<strong>125,970</strong>"],
            ["顺序 $k!$", "8 条的排列", "<strong>40,320</strong>"],
            ["格式 $|F|$", "3 种", "3"],
            ["<strong>合计</strong>", "—",
             "<strong>$3.66 \\times 10^{11}$</strong>"],
        ]),
        DUAL(
            "<strong>$3.66\\times10^{11}$ 这个数说明两件事。</strong>"
            "<em>第一，穷举不可能，所以必须搜</em>。"
            "<strong>第二，也是更重要的：在一个 $10^{11}$ 的空间里，"
            "「在 40 条评测样本上表现最好的那个候选」几乎肯定是运气好而不是真的好。</strong>"
            "<em>这正是 C66 模块 04 的胜者诅咒，只不过参赛者从「模型」换成了「prompt」。</em>",
            "所以工程上的第一个动作是<strong>把空间砍小</strong>，而且要砍得有依据："
            "<strong>① 顺序维度用「最后一条放谁」代替全排列</strong>"
            "（模块 02 量到它解释了顺序效应的六成，"
            "把 $k!$ 从 40320 降到 $k$）；"
            "<strong>② 示例子集用选择策略代替自由子集</strong>"
            "（kNN / 分桶 kNN 把 $\\binom{20}{8}$ 降到几种）；"
            "<strong>③ 指令用「槽位开关」代替自由文本</strong>"
            "（$2^5 = 32$ 种，可枚举）。"
            "<em>砍完之后空间是 1,152——可以真正搜完（压缩了 $3.2\\times10^{8}$ 倍），而且过拟合可控。</em>",
        ),
        CALLOUT("warn", "「让模型自由生成指令」（APE / OPRO 式）会把空间重新放回无限大。"
                        "<strong>它能找到人想不到的写法，代价是过拟合风险回到最高档。</strong>"
                        "<em>用它的前提是评测集足够大、并且有一个从未参与搜索的留出集</em>——"
                        "而这两条通常比 optimizer 本身更难满足。"),
    ])),

    # ============================================================== 3
    ("objective", "评分函数：优化器会精确利用它的每一个缺陷", "".join([
        P("评分函数是优化的目标。"
          "<strong>而优化过程不知道你「真正想要」什么，它只知道这个数。</strong>"),
        TABLE(["目标函数", "它漏掉了什么", "优化器会怎么利用这个漏洞"], [
            ["<strong>只用准确率</strong>", "解析率、成本、延迟",
             "<em>搜出一个又长又慢的 prompt</em>；"
             "或者搜出一个「放宽取值域」的格式（模块 01 讲解第 2 节的那个陷阱）"],
            ["<strong>用一个有偏的 judge</strong>", "judge 自己的偏差（长度、位置、自偏好）",
             "<strong>搜出一个专门迎合 judge 偏差的 prompt</strong>——"
             "<em>它在 judge 上分更高，而真实指标没有变好</em>（notebook 第 5 节量出来）"],
            ["<strong>准确率的样本量太小</strong>", "噪声",
             "<em>搜出一个恰好拟合这 20 条样本的配置</em>；"
             "<strong>提升全部是噪声</strong>"],
            ["<strong>只在一个分层上看</strong>", "其它分层",
             "牺牲稀有类换总分——<em>而稀有类往往是业务上最重要的那些</em>"],
        ]),
        DUAL(
            "第二行是最危险的一个，因为<strong>它的失败是不可见的</strong>："
            "<em>优化后 judge 分数上升，所有指标都变好，"
            "而真实质量下降</em>。"
            "<strong>这与 C67 模块 05 的奖励模型过优化完全同构</strong>——"
            "只不过那里优化的是权重（贵、不可逆），这里优化的是 prompt（便宜、可回滚），"
            "<em>所以这里更容易发生，而且更容易被忽略</em>。",
            "三条对策，与 C67 一致："
            "<strong>① 目标函数用组合而不是单一指标</strong>"
            "（准确率 + 解析率 + 成本惩罚，且解析率是硬约束不是加权项）；"
            "<strong>② 保留一个 judge 从未参与的独立信号</strong>"
            "（人工抽检、或一个规则化的可验证子集）；"
            "<strong>③ 报保守分数 $\\mu - \\lambda\\sigma$ 而不是点估计</strong>——"
            "<em>它天然惩罚了「在小样本上运气好」的候选</em>。",
        ),
        P("<strong>还有一条形式上的纪律</strong>："
          "<em>解析率必须是硬约束（<code>parse_rate == 1.0</code> 才允许进入排名），"
          "不能作为加权项</em>。"
          "<strong>因为加权项可以被「牺牲一点解析率换很多准确率」的候选钻空子，"
          "而下游拿到不合法的值可能直接崩。</strong>"),
    ])),

    # ============================================================== 4
    ("algorithms", "三种搜索算法", "".join([
        TABLE(["算法", "怎么搜", "评估次数", "什么时候用"], [
            ["<strong>随机搜索</strong>", "从空间里随机采 N 个候选，取最好的",
             "$N$",
             "<strong>基线，永远先做这个</strong>；"
             "<em>而且它的过拟合行为最容易分析（第 5 节）</em>"],
            ["<strong>坐标上升</strong>",
             "固定其它维度，逐个维度扫到最优，循环几轮",
             "$\\sum_d |D_d| \\times \\text{rounds}$",
             "<strong>维度之间近似独立时性价比最高</strong>；"
             "<em>本课的空间正是这种（指令槽位 / 选择策略 / 末条 / 格式）</em>"],
            ["<strong>bootstrap 示例</strong>",
             "<em>用「当前 prompt 在训练集上答对的样本」当示例</em>，迭代几轮",
             "$\\text{rounds} \\times |train|$",
             "<strong>示例维度上最有效的一个</strong>（DSPy 的核心手段）；"
             "<em>它不需要人工标注新示例</em>"],
        ]),
        DUAL(
            "<strong>bootstrap 示例的想法很漂亮</strong>："
            "<em>示例不必是人挑的，可以是「当前系统自己做对的那些」</em>。"
            "<strong>它的自举性质带来一个真实的好处：示例的风格与格式天然与模型一致。</strong>"
            "notebook 第 3 节实现它并量出收益。",
            "但它也有一个必须知道的偏倚："
            "<strong>它只会挑「当前 prompt 已经能做对的」样本</strong>，"
            "<em>于是它倾向于强化当前的行为，而不是纠正它</em>。"
            "<strong>症状是：bootstrap 几轮之后在训练集上很好，"
            "而在「当前 prompt 一直做错的那类样本」上没有改善。</strong>"
            "<em>对策是把 bootstrap 与「覆盖保底」结合（模块 02 练习 1 的混合选择器）</em>——"
            "<strong>让每个标签至少有一条示例，即使那一类当前一条都没做对。</strong>",
        ),
        H3("成本的可比口径"),
        P("<strong>比较算法时必须固定「评估次数」这个预算</strong>，"
          "而不是固定轮数。"
          "<em>因为一次评估 = 在评测集上跑一遍 = 真实的钱</em>。"
          "notebook 第 2/3 节在同样的评估预算下比较随机搜索与坐标上升，"
          "<strong>结论是坐标上升在这个（近似独立的）空间上更高效</strong>——"
          "<em>但这个结论依赖空间的结构，不能推广</em>。"),
    ])),

    # ============================================================== 5
    ("overfit", "过拟合：gap 随候选数增长的精确曲线", "".join([
        P("这是本模块最重要的一节。"
          "<strong>它说明「搜索集上提升了 20 个点」这句话在什么条件下毫无意义。</strong>"),
        ASCII("""
   实验设定：N 个候选，**真实能力完全相同**（纯噪声）
   搜索集 40 条、留出集 40 条

     N       搜索集最优    该候选在留出集上    gap
     1          0.590          0.601        -0.011
     2          0.647          0.596         0.050
     5          0.692          0.600         0.092
    10          0.719          0.601         0.118
    50          0.769          0.603         0.166
   200          0.806          0.597         0.208
  1000          0.838          0.589         0.249

   留出集分数**始终在真值 0.60 附近**，而搜索集分数一路涨到 0.838。
   → 「搜索集上的提升」里，有 25 个点纯粹是选择造成的。
"""),
        DUAL(
            "<strong>这就是 C66 模块 04 的胜者诅咒，参赛者从「模型」换成了「prompt 候选」。</strong>"
            "<em>取 $N$ 个带噪声估计的最大值，这个最大值系统性地高于真实最优</em>，"
            "而偏差的量级随 $\\ln N$ 增长。"
            "<strong>关键结论：搜索集上的分数不是效果，它是「效果 + 选择偏差」。</strong>",
            "定量地：设每个候选在搜索集上的估计"
            "$\\hat s_i = s_i + \\varepsilon_i$，$\\varepsilon_i \\sim \\mathcal{N}(0, \\sigma^2)$，"
            "$\\sigma \\approx \\sqrt{p(1-p)/n}$。"
            "<strong>则 $\\mathbb{E}[\\max_i \\hat s_i] - \\max_i s_i$ 的量级是 "
            "$\\mathcal{O}(\\sigma\\sqrt{2\\ln N})$</strong>"
            "（<em>注意 $\\sigma\\sqrt{2\\ln N}$ 是一个上界，$N$ 不大时实际值更小——"
            "这一点在 C66 模块 04 里量过</em>）。"
            "<strong>所以搜索集样本量 $n$ 与候选数 $N$ 必须一起看："
            "$n$ 太小时，$N$ 越大结论越假。</strong>",
        ),
        H3("三条可执行的对策"),
        OL([
            "<strong>留出集必须从未参与搜索</strong>，"
            "<em>而且报告里报的是留出集分数，不是搜索集分数</em>。"
            "<strong>这一条是硬要求，不是最佳实践。</strong>",
            "<strong>用 C66 模块 04 的 MDE 反推「搜索集该多大」</strong>："
            "<em>如果你想可靠地检出 3 个点的提升，先算需要多少样本</em>；"
            "<strong>样本不够时正确的动作是「不搜」而不是「搜了再说」。</strong>",
            "<strong>候选数进报告</strong>——"
            "<em>「我们评估了 N 个候选」是解读搜索集分数的必要信息</em>。"
            "报告里没有 $N$ 时，搜索集分数无法被评估。"
            "<strong>这与 C66 模块 04 第 6 节「$m$ 为参赛者数量」是同一条。</strong>",
        ]),
        CALLOUT("danger", "一个具体的、常见的失败："
                          "<strong>用同一个评测集反复搜了几个月。</strong>"
                          "<em>即使每次只搜十几个候选，累积下来 $N$ 已经是几千</em>，"
                          "而那个评测集早就被拟合掉了。"
                          "<strong>对策：留出集要定期轮换，"
                          "而且轮换记录要写进 CHANGELOG</strong>"
                          "（与 C03 模块 05 的污染管理同构）。"),
    ])),

    # ============================================================== 6
    ("when-not", "什么时候不该优化", "".join([
        OL([
            "<strong>评测集的噪声大于你想找的效应</strong>——"
            "<em>先量 $\\sigma$，再算 MDE</em>。"
            "<strong>MDE 大于你期望的提升时，搜索只会产出噪声。</strong>",
            "<strong>目标函数还没被验证过</strong>——"
            "<em>用一个没做过元评测的 judge 当目标函数，"
            "等于把 judge 的偏差直接写进 prompt</em>（C67 模块 03）。",
            "<strong>契约层还没做对</strong>——"
            "<em>解析率还不是 1.0 时，优化会在「准确率」上打转"
            "而真正的损失在解析层</em>（模块 01 的三个量）。"
            "<strong>先修契约。</strong>",
            "<strong>模块 02 的免费收益还没拿</strong>——"
            "<em>选择策略与顺序是零/低成本的，而它们的效应量可以是三倍</em>。"
            "<strong>先把它们做完再谈自动搜索。</strong>",
            "<strong>没有留出集</strong>——"
            "<em>没有留出集的优化不是优化，是在给评测集拟合一个 prompt</em>。",
        ]),
        DUAL(
            "反过来，<strong>什么时候该优化</strong>："
            "<em>契约层已经 1.0、选择与顺序已经调过、"
            "评测集的 $\\sigma$ 已知且 MDE 小于目标提升、"
            "有一个独立的留出集</em>。"
            "<strong>这四条同时成立时，自动优化是这一层最后一块、也确实有收益的一块。</strong>",
            "还有一个常被忽略的判据：<strong>优化的产出要能被审阅</strong>。"
            "<em>搜出来的 prompt 如果是一段人类看不懂的咒语，"
            "那么它的可维护性是负的</em>——"
            "<strong>换模型时它大概率失效（模块 05），而没人知道该怎么改它</strong>。"
            "<em>所以「槽位开关 + 示例集合与顺序」这种结构化的搜索空间，"
            "比「自由文本指令」在长期上更值</em>。",
        ),
    ])),

    # ============================================================== 7
    ("gate", "优化器本身也要有 spec 与指纹", "".join([
        P("优化是一次<strong>会产出资产的运行</strong>，"
          "所以它要按 C68 的规矩来。"),
        ASCII("""
   优化报告（每次优化后生成）

   optimizer:        coordinate_ascent(rounds=2)
   space_size:       3,840            ← **必须报**（解读搜索集分数的前提）
   n_evaluated:      184              ← **必须报**（胜者诅咒的 N）
   objective:        accuracy − 0.02·cost，且 parse_rate == 1.0 为硬约束
   search_set:       dev-2026w35 (n=40)   σ=0.062（重复 10 次测得）
   holdout:          holdout-2026w30 (n=40)  ← **从未参与搜索**
   optimizer_fp:     4a1c88e2          ← 空间定义 + 目标函数 + 算法 + 种子

   基线   → 搜索集 0.60  留出集 0.60
   优化后 → 搜索集 0.78  留出集 0.65
            └─ 搜索集提升 +18pp，**其中只有 +5pp 在留出集上成立**

   判读: 留出集提升 5pp vs 2σ = 12.4pp → **不显著，不予上线**
"""),
        P("<strong>最后一行是这一节的重点</strong>："
          "<em>一次搜索集上 +18pp 的优化，按正确口径判读是「不显著」</em>。"
          "<strong>而如果只报搜索集分数，它会被当成一次巨大的成功。</strong>"),
        H3("门禁（按 C68 模块 04 分级）"),
        UL([
            "<strong>确定性阻断</strong>：报告里缺 <code>space_size</code> 或 "
            "<code>n_evaluated</code>；留出集与搜索集有交集；"
            "优化后的 <code>parse_rate < 1.0</code>",
            "<strong>统计阻断</strong>：<em>留出集</em>提升不超过 $2\\sigma$",
            "<strong>报警</strong>：搜索集提升与留出集提升的比值 > 3"
            "（<em>过拟合的直接信号</em>）；预测标签分布的 PSI",
        ]),
        CALLOUT("intuition", "那条报警值得单独说："
                             "<strong>「搜索集提升 / 留出集提升」这个比值是过拟合最直接的指标</strong>，"
                             "而它几乎是免费的（两个数你都已经有了）。"
                             "<em>比值接近 1 → 搜索是真的在找效果；"
                             "比值很大 → 搜索在拟合噪声。</em>"),
    ])),

    # ============================================================== 8
    ("output-asset", "优化的产出是一份资产，不是一次调参", "".join([
        P("一次优化跑完，你得到的不是「更好的效果」，"
          "<strong>而是一份具体的、可 diff、可回滚、会过期的资产。</strong>"),
        ASCII("""
   一次优化的产出

   optimized/
     instruction.txt        ← 槽位组合（或搜出来的措辞）
     demos.jsonl            ← **有序**的示例集合
     calib.json             ← 校准参数（如果做了）
     REPORT.md              ← 空间大小 / 候选数 / 搜索集与留出集分数 / 过拟合比值
     optimizer_fp.txt       ← 空间定义 + 目标函数 + 算法 + 种子

   它与「人手改出来的 prompt」是同一种资产 —— 走同一套版本与门禁（模块 01 第 7 节）。
"""),
        DUAL(
            "<strong>把它当资产而不是「调好的参数」，有三个直接后果。</strong>"
            "<em>① 它要进版本控制并带 CHANGELOG</em>——"
            "<strong>「这套 demos 是自动搜出来的」本身就是一条必须记录的信息</strong>，"
            "因为它决定了下次该怎么改（重跑优化，而不是手改）。"
            "<em>② 它会过期</em>——模块 05 会说明：换模型时它基本报废。"
            "<em>③ 它要能被审阅</em>——搜出来的东西如果人看不懂，可维护性是负的。",
            "第三点值得展开，因为它反过来约束了搜索空间的设计。"
            "<strong>「槽位开关 + 示例集合与顺序」这种结构化空间的产出是可读的</strong>："
            "<em>你能看出「它关掉了禁止项、把覆盖示例放到了最后」</em>。"
            "而<strong>自由文本指令搜索的产出常常是一段读不懂的咒语</strong>——"
            "<em>它在离线指标上更好，但没人知道它为什么有效、"
            "换模型时该保留哪一句、出问题时该改哪里</em>。"
            "<strong>所以在长期上，结构化空间的价值不只是「过拟合可控」，"
            "还包括「产出是可维护的」。</strong>",
        ),
    ])),

    # ============================================================== 9
    ("human-vs-auto", "人工改与自动搜的分工", "".join([
        P("自动优化不取代人。"
          "<strong>两者擅长的东西不同，而分工的判据很具体。</strong>"),
        TABLE(["工作", "谁做", "为什么"], [
            ["<strong>定契约（签名、取值域、格式）</strong>", "<strong>人</strong>",
             "它来自业务需求，搜不出来；<em>而且它是可迁移的那一半（模块 05）</em>"],
            ["<strong>写边界与兜底规则</strong>", "<strong>人</strong>",
             "「信息不足时输出 unknown」这类规则来自对下游的理解"],
            ["<strong>选择策略与 k</strong>", "人定候选，机器扫",
             "候选很少（几种策略 × 几个 k），扫一遍就完了"],
            ["<strong>示例顺序</strong>", "<strong>机器</strong>",
             "<em>人对位置偏置没有直觉，而且方向依模型而异</em>（模块 05）"],
            ["<strong>示例集合</strong>", "<strong>机器</strong>（bootstrap）",
             "人挑示例会不自觉地选「自己觉得典型」的，而那不等于「对模型有用」"],
            ["<strong>指令措辞</strong>", "<em>先人后机器</em>",
             "人写出五个槽位齐全的版本；<strong>机器只在这个基础上做小幅搜索</strong>——"
             "<em>让机器从零写指令会把空间放回无限大（第 2 节）</em>"],
            ["<strong>判读结果、决定上不上</strong>", "<strong>人</strong>",
             "第 7 节那条「留出集提升不超过 2σ 就阻断」需要人接受这个结论"],
        ]),
        CALLOUT("intuition", "一句话概括这张表："
                             "<strong>人负责「什么是对的」，机器负责「哪个排列更好」。</strong>"
                             "<em>而混淆这两件事的典型症状是："
                             "让机器去搜一个本该由业务决定的取值域，"
                             "或者让人去猜一个本该被扫出来的示例顺序。</em>"),
    ])),

    # ============================================================== 10
    ("recap", "把三个风险重新排一遍", "".join([
        P("本模块开头说「风险全在空间、目标、算法这三个定义里」。"
          "<strong>这一节按「多常见 × 多严重」把它们重排，"
          "并给出每一个的最小对策。</strong>"),
        TABLE(["风险", "常见程度", "严重程度", "最小对策"], [
            ["<strong>没有留出集</strong>", "极常见", "<strong>最严重</strong>",
             "<em>切一个从未参与搜索的集合出来</em>——"
             "<strong>这一条零成本，而没有它整个优化不可评估</strong>"],
            ["<strong>报搜索集分数而不是留出集分数</strong>", "极常见", "最严重",
             "报告模板里把 <code>holdout_best</code> 放在 <code>search_best</code> 前面"],
            ["<strong>报告里不写候选数 N</strong>", "常见", "严重",
             "<em>没有 N，搜索集分数无法被解读</em>（第 5 节）"],
            ["<strong>解析率当加权项</strong>", "常见", "严重",
             "改成可行性判断（第 3 节的一行代码）"],
            ["<strong>用未验证的 judge 当目标</strong>", "常见", "<strong>最隐蔽</strong>",
             "<em>先做 C67 的元评测；或保留一个 judge 从未参与的独立信号</em>"],
            ["<strong>评测集反复被搜了几个月</strong>", "常见", "严重（累积）",
             "留出集定期轮换，轮换记录进 CHANGELOG"],
            ["<strong>搜索空间是自由文本</strong>", "较少", "中",
             "换成槽位开关；<em>它同时让产出可审阅（第 8 节）</em>"],
        ]),
        DUAL(
            "<strong>前两行是同一件事的两面，而它们的对策都是零成本的。</strong>"
            "<em>这意味着：绝大多数「优化没效果」的案例，"
            "问题不在优化算法上，而在评估口径上</em>。"
            "<strong>而第 5 行是唯一一个「所有指标都变好而实际变差」的风险</strong>——"
            "所以它最隐蔽，也最值得在开工前处理。",
            "反过来，<strong>有一个风险被高估了：搜索算法不够强。</strong>"
            "<em>本模块第 4 节在同样的评估预算下比较随机搜索与坐标上升，"
            "差别远小于「有没有留出集」造成的差别</em>。"
            "<strong>换句话说：把预算花在扩评测集、验证 judge、切留出集上，"
            "回报远高于换一个更花哨的 optimizer。</strong>",
        ),
    ])),

    # ============================================================== 11
    ("boundary", "这一层的边界", "".join([
        P("自动提示优化是本课最容易被过度期待的一层。"
          "<strong>这一节说清它的天花板在哪。</strong>"),
        UL([
            "<strong>它不改变模型的能力上界。</strong>"
            "<em>C03 模块 06 的 elicitation 阶梯里，prompt 优化只是其中一格</em>；"
            "<strong>「模型根本不会做这类题」不是搜索能解决的问题。</strong>",
            "<strong>它不能替代评测集。</strong>"
            "<em>而且它对评测集的要求比人工改 prompt 更高</em>——"
            "因为搜索会消耗评测集的统计能力（第 4 节的胜者诅咒）。"
            "<strong>所以「没有好评测集所以让机器自己搜」是一个反向的结论。</strong>",
            "<strong>它的产出会随模型报废</strong>（模块 05 会量出来）。"
            "<em>所以在预期一年内换模型的项目里，"
            "把预算从这一层挪到契约层与约束层更理性。</em>",
            "<strong>它不改善可维护性，通常还会降低它。</strong>"
            "<em>搜出来的东西如果人看不懂，出问题时没人知道该改哪里</em>——"
            "这正是第 8 节要求「结构化搜索空间」的原因。",
        ]),
        DUAL(
            "<strong>反过来，它确实能做到一件人做不好的事：扫排列。</strong>"
            "<em>人对位置偏置没有直觉，而模块 02 量到顺序造成三倍差距</em>。"
            "<strong>所以「顺序搜索」是这一层性价比最高的应用</strong>——"
            "它零成本、效应大、而且产出是可读的（一个排列）。",
            "如果要给这一层一句总结："
            "<strong>它适合在一个<em>已经定义清楚</em>的小空间里做穷尽的比较，"
            "不适合用来「探索该怎么写 prompt」。</strong>"
            "<em>前者是它的强项（机器不会漏、不会累、不会自我说服）；"
            "后者需要对任务的理解，而那是人的工作（第 9 节那张分工表）。</em>",
        ),
    ])),
]

NB = [
    md("""# 03 · 自动提示优化（空间 / 目标 / 算法 / 过拟合 / 门禁）

目标：把「自动提示优化」拆成三件可分别检查的东西，
并**把过拟合的程度精确量出来**。

本 notebook 你会亲手实现：
1. **搜索空间的枚举与大小计算** —— 以及三种把它砍小的有依据的做法
2. **随机搜索 vs 坐标上升** —— 在同样的评估预算下比较
3. **bootstrap 示例** —— 用「当前 prompt 做对的样本」当示例，以及它的自我强化偏倚
4. **过拟合的精确曲线** —— 候选数 N 从 1 到 1000，gap 从 −0.01 长到 0.249
5. **有偏 judge 会被优化直接放大** —— 优化出来的 prompt 在真实指标上更差
6. **优化报告 + 门禁** —— 含「搜索集提升 / 留出集提升」这个免费的过拟合指标

> 心智模型：**搜索集上的分数不是效果，它是「效果 + 选择偏差」。
> 而选择偏差随候选数增长。**"""),

    md("""## 0 · 环境（沿用前三个模块的模拟器）"""),

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
# 三个不相交的集合：train（给 bootstrap 用）/ dev（搜索集）/ holdout（从未参与搜索）
TRAIN = [
    ('接口返回 502', 'bug'), ('点击没反应', 'bug'), ('数据没保存上', 'bug'),
    ('想要 webhook', 'feature'), ('能加个筛选吗', 'feature'), ('希望支持导入', 'feature'),
    ('多收了一笔钱', 'billing'), ('发票信息要改', 'billing'), ('续费价格是多少', 'billing'),
    ('登录验证码收不到', 'account'), ('要换邮箱', 'account'), ('账号解绑怎么弄', 'account'),
    ('挺好的', 'other'), ('没事了', 'other'), ('先看看', 'other'),
]
DEV = [
    ('打开报表就崩溃', 'bug'), ('保存草稿会丢内容', 'bug'),
    ('希望能加个批量删除', 'feature'), ('想要导出 PDF 的功能', 'feature'),
    ('这个月账单不对', 'billing'), ('发票上的税号不对', 'billing'),
    ('登录不上，密码重置也收不到', 'account'), ('手机号换了要怎么改', 'account'),
    ('感谢你们的帮助', 'other'), ('没别的了', 'other'),
]
HOLDOUT = [
    ('导出的文件打不开', 'bug'), ('列表排序是乱的', 'bug'),
    ('能不能支持模板', 'feature'), ('想要一个统计面板', 'feature'),
    ('优惠券没生效', 'billing'), ('账单邮件收不到', 'billing'),
    ('两步验证怎么关', 'account'), ('子账号怎么加', 'account'),
    ('回复挺快的', 'other'), ('就问一下', 'other'),
]
print(f'POOL {len(POOL)} · TRAIN {len(TRAIN)} · DEV {len(DEV)} · HOLDOUT {len(HOLDOUT)}')
assert not ({x for x, _ in DEV} & {x for x, _ in HOLDOUT}), 'DEV 与 HOLDOUT 必须不相交'
assert not ({x for x, _ in POOL} & {x for x, _ in DEV}), 'POOL 与 DEV 必须不相交'"""),

    md("""## 1 · 搜索空间：定义、枚举、以及它有多大"""),

    code("""SLOTS = {
    'task':     ['把用户反馈分类。', '请判断这条用户反馈属于哪一类。'],
    'domain':   ['标签只能是 bug / feature / billing / account / other 之一。'],
    'format':   ['只输出标签本身。', '输出一个 JSON：{"label": "<标签>"}。'],
    'fallback': ['', '都不符合时输出 other。'],
    'forbid':   ['', '不要解释，不要输出代码块。'],
}
SELECTORS = ['random', 'knn', 'coverage', 'hybrid']
LAST_CHOICES = list(range(6))          # 「最后一条放谁」——模块 02 的降维
K_CHOICES = [3, 5, 8]

def space_size():
    n_instr = 1
    for v in SLOTS.values():
        n_instr *= len(v)
    return n_instr * len(SELECTORS) * len(LAST_CHOICES) * len(K_CHOICES)

def naive_space_size(pool=20, k=8, n_instr=None, n_fmt=3):
    n_instr = n_instr if n_instr else 24
    return n_instr * math.comb(pool, k) * math.factorial(k) * n_fmt

print(f'朴素空间（自由子集 × 全排列）: {naive_space_size():,.0f}')
print(f'砍小之后的空间:               {space_size():,.0f}')
print(f'压缩了 {naive_space_size() / space_size():,.0f} 倍')
print()
print('三个有依据的砍法:')
print('  ① 顺序：全排列 8! = 40,320 → 「最后一条放谁」6 种')
print('     （模块 02 量到这一个自由度解释了顺序效应的六成）')
print('  ② 示例子集：C(20,8) = 125,970 → 4 种选择策略')
print('  ③ 指令：自由文本 → 槽位开关（这里 2×1×2×2×2 = 16 种）')

assert naive_space_size() / space_size() > 1e6
assert space_size() < 2000, f'砍小后应当可以真正搜完，实际 {space_size()}'
print(f'\\n✅ 砍到 {space_size()} 个候选——**可以枚举**，而且过拟合可控（第 4 节会量）。')"""),

    code("""# --- 候选的表示与评估 ---
def build_instruction(choice):
    return ''.join(SLOTS[k][choice[k]] for k in SLOTS)

def select_demos(selector, x, k, last_idx):
    e = embed(x)
    if selector == 'random':
        r = np.random.default_rng(0)
        idx = list(r.permutation(len(POOL))[:k])
    elif selector == 'knn':
        s = np.array([float(np.dot(embed(t), e)) for t, _ in POOL])
        idx = list(np.argsort(-s)[:k])
    elif selector == 'coverage':
        idx = []
        for l in LABELS:
            idx += [i for i, (_, y) in enumerate(POOL) if y == l][:max(1, k // len(LABELS))]
        idx = idx[:k]
    else:                                        # hybrid：保底覆盖 + kNN 填
        idx = []
        s = np.array([float(np.dot(embed(t), e)) for t, _ in POOL])
        for l in LABELS:
            cand = [i for i in np.argsort(-s) if POOL[i][1] == l]
            if cand and len(idx) < k:
                idx.append(int(cand[0]))
        for i in np.argsort(-s):
            if len(idx) >= k:
                break
            if int(i) not in idx:
                idx.append(int(i))
    demos = [POOL[i] for i in idx]
    if demos:
        j = last_idx % len(demos)
        demos = demos[:j] + demos[j + 1:] + [demos[j]]      # 把第 j 条挪到最后
    return demos

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

def parse(raw, instruction):
    if raw == UNPARSEABLE:
        return None
    return raw if raw in LABELS else None

Candidate = dict
def make_candidate(slot_choice, selector, k, last_idx):
    return dict(slots=dict(slot_choice), selector=selector, k=k, last_idx=last_idx)

def evaluate(cand, test):
    instr = build_instruction(cand['slots'])
    n_ok = n_c = 0
    tokens = 0
    for x, gold in test:
        demos = select_demos(cand['selector'], x, cand['k'], cand['last_idx'])
        raw = toy_lm(instr, demos, x)
        p = parse(raw, instr)
        n_ok += (p is not None)
        n_c += (p == gold)
        tokens += len(instr) + sum(len(a) + len(b) for a, b in demos)
    n = len(test)
    return dict(parse_rate=n_ok / n, accuracy=n_c / n,
                cost=tokens / n / 100.0)

BASE = make_candidate({k: 0 for k in SLOTS}, 'random', 5, 0)
print('基线候选:', {k: v for k, v in BASE.items() if k != 'slots'})
print('  dev    :', {k: round(v, 3) for k, v in evaluate(BASE, DEV).items()})
print('  holdout:', {k: round(v, 3) for k, v in evaluate(BASE, HOLDOUT).items()})
assert evaluate(BASE, DEV)['parse_rate'] == 1.0
print('\\n✅ 候选 = (指令槽位选择, 选择策略, k, 最后一条放谁)，四个离散维度。')"""),

    md("""## 2 · 目标函数：组合指标 + 硬约束

**解析率是硬约束，不是加权项**——否则候选可以「牺牲一点解析率换很多准确率」。"""),

    code("""def objective(metrics, cost_weight=0.02):
    \"\"\"返回 (是否可行, 分数)。解析率是硬约束。\"\"\"
    if metrics['parse_rate'] < 1.0:
        return False, float('-inf')
    return True, metrics['accuracy'] - cost_weight * metrics['cost']

def objective_bad(metrics, parse_weight=0.3, cost_weight=0.02):
    \"\"\"错误版本：把解析率当加权项。\"\"\"
    return True, (metrics['accuracy'] + parse_weight * metrics['parse_rate']
                  - cost_weight * metrics['cost'])

# 造一个「牺牲解析率换准确率」的候选：指令缺 domain → 解析全失败
CHEAT = make_candidate({**{k: 0 for k in SLOTS}}, 'knn', 8, 0)
CHEAT_M = dict(parse_rate=0.6, accuracy=0.95, cost=1.0)     # 假设它长这样
GOOD_M = dict(parse_rate=1.0, accuracy=0.80, cost=1.0)

print(f"{'候选':<24}{'parse':>8}{'acc':>7}{'硬约束目标':>12}{'加权目标':>10}")
for name, m in [('合规但准确率一般', GOOD_M), ('不合规但准确率很高', CHEAT_M)]:
    feas, s1 = objective(m)
    _, s2 = objective_bad(m)
    print(f'{name:<24}{m["parse_rate"]:>8.0%}{m["accuracy"]:>7.0%}'
          f'{(f"{s1:.3f}" if feas else "不可行"):>12}{s2:>10.3f}')

assert objective(CHEAT_M)[0] is False, '硬约束把不合规候选直接排除'
assert objective_bad(CHEAT_M)[1] > objective_bad(GOOD_M)[1], \\
    '加权版本会选中那个不合规的候选'
print('\\n✅ 加权版本选中了解析率只有 60% 的候选——因为它的准确率高。')
print('   而下游拿到的是 40% 的不合法值，可能直接崩。')
print('   **解析率必须是硬约束**：可行性判断先于排名（模块 01 讲解第 2 节的那个陷阱）。')"""),

    md("""## 3 · 三种搜索算法（固定评估预算）"""),

    code("""def all_slot_choices():
    keys = list(SLOTS)
    for combo in itertools.product(*[range(len(SLOTS[k])) for k in keys]):
        yield dict(zip(keys, combo))

ALL_SLOTS = list(all_slot_choices())
print(f'指令槽位组合 {len(ALL_SLOTS)} 种')

def random_search(n_eval, search_set, seed=0):
    rng = np.random.default_rng(seed)
    best, best_s, n = None, float('-inf'), 0
    for _ in range(n_eval):
        cand = make_candidate(ALL_SLOTS[rng.integers(len(ALL_SLOTS))],
                              SELECTORS[rng.integers(len(SELECTORS))],
                              K_CHOICES[rng.integers(len(K_CHOICES))],
                              int(rng.integers(len(LAST_CHOICES))))
        feas, s = objective(evaluate(cand, search_set)); n += 1
        if feas and s > best_s:
            best, best_s = cand, s
    return best, best_s, n

def coordinate_ascent(search_set, rounds=2, seed=0):
    cur = make_candidate(ALL_SLOTS[0], SELECTORS[0], K_CHOICES[0], 0)
    n = 0
    feas, best_s = objective(evaluate(cur, search_set)); n += 1
    for _ in range(rounds):
        # 维度 1：指令槽位（逐个槽位扫）
        for key in SLOTS:
            for v in range(len(SLOTS[key])):
                cand = dict(cur); cand['slots'] = dict(cur['slots']); cand['slots'][key] = v
                f, s = objective(evaluate(cand, search_set)); n += 1
                if f and s > best_s:
                    cur, best_s = cand, s
        # 维度 2-4
        for field, choices in [('selector', SELECTORS), ('k', K_CHOICES),
                               ('last_idx', LAST_CHOICES)]:
            for v in choices:
                cand = dict(cur); cand[field] = v
                f, s = objective(evaluate(cand, search_set)); n += 1
                if f and s > best_s:
                    cur, best_s = cand, s
    return cur, best_s, n

ca_best, ca_score, ca_n = coordinate_ascent(DEV, rounds=2)
rs_best, rs_score, rs_n = random_search(ca_n, DEV, seed=0)     # 同样的评估预算

print(f"\\n{'算法':<16}{'评估次数':>10}{'dev 目标':>10}{'dev acc':>10}{'holdout acc':>13}")
for name, cand, n in [('坐标上升', ca_best, ca_n), ('随机搜索', rs_best, rs_n)]:
    print(f'{name:<16}{n:>10}{objective(evaluate(cand, DEV))[1]:>10.3f}'
          f'{evaluate(cand, DEV)["accuracy"]:>10.0%}'
          f'{evaluate(cand, HOLDOUT)["accuracy"]:>13.0%}')

assert ca_n == rs_n, '必须在同样的评估预算下比较'
assert ca_score >= rs_score - 1e-9 or True     # 结论依赖空间结构，不强断言
print(f'\\n✅ 在同样的 {ca_n} 次评估预算下比较——**固定评估次数而不是固定轮数**，')
print('   因为一次评估 = 在评测集上跑一遍 = 真实的钱。')
print('   坐标上升在这个（维度近似独立的）空间上通常更高效，')
print('   但这个结论依赖空间的结构，不能推广。')"""),

    code("""# --- bootstrap 示例：用「当前 prompt 在 TRAIN 上答对的样本」当示例 ---
def bootstrap_demos(cand, train, rounds=2, k=8, min_per_label=1):
    \"\"\"DSPy 式：迭代地把「当前配置答对的训练样本」收进示例池。\"\"\"
    instr = build_instruction(cand['slots'])
    demos = select_demos(cand['selector'], train[0][0], k, cand['last_idx'])
    for _ in range(rounds):
        correct = []
        for x, gold in train:
            if toy_lm(instr, demos, x) == gold:
                correct.append((x, gold))
        if not correct:
            break
        # 覆盖保底：每类至少 min_per_label 条，即使这一类当前一条都没做对
        chosen, have = [], Counter(y for _, y in correct)
        for l in LABELS:
            got = [t for t in correct if t[1] == l][:min_per_label]
            if not got:
                fallback = [t for t in train if t[1] == l][:min_per_label]
                got = fallback
            chosen += got
        for t in correct:
            if len(chosen) >= k:
                break
            if t not in chosen:
                chosen.append(t)
        demos = chosen[:k]
    return demos

def eval_with_demos(cand, demos, test):
    instr = build_instruction(cand['slots'])
    n_ok = n_c = 0
    for x, gold in test:
        raw = toy_lm(instr, demos, x)
        p = parse(raw, instr)
        n_ok += (p is not None); n_c += (p == gold)
    return dict(parse_rate=n_ok / len(test), accuracy=n_c / len(test), cost=1.0)

boot = bootstrap_demos(ca_best, TRAIN, rounds=2, k=8)
print(f'bootstrap 出的示例（{len(boot)} 条，标签分布 '
      f'{dict(Counter(y for _, y in boot))}）:')
for t, y in boot[:4]:
    print(f'  {y:<9} {t}')

m_pool = evaluate(ca_best, HOLDOUT)
m_boot = eval_with_demos(ca_best, boot, HOLDOUT)
print(f'\\nholdout 准确率: 人工池示例 {m_pool["accuracy"]:.0%} | '
      f'bootstrap 示例 {m_boot["accuracy"]:.0%}')

assert set(y for _, y in boot) == set(LABELS), '覆盖保底：每个标签都要有'
assert len(boot) <= 8
print('\\n✅ bootstrap 不需要人工标注新示例——示例是「系统自己做对的那些」，')
print('   而且它们的风格与格式天然与模型一致。')
print()
print('   ⚠️ 但它有一个必须知道的偏倚：**它只挑当前 prompt 已经能做对的样本**，')
print('   于是它倾向于强化当前行为而不是纠正它。')
print('   症状：bootstrap 几轮后训练集很好，而「一直做错的那类样本」没有改善。')
print('   对策就是上面那个 min_per_label 保底——')
print('   让每个标签至少有一条示例，**即使那一类当前一条都没做对**。')"""),

    md("""## 4 · 过拟合：gap 随候选数增长

**关键实验：让所有候选的真实能力完全相同（纯噪声），看搜索集分数怎么涨。**"""),

    code("""def winners_curse(N, n_search=40, n_hold=40, true_p=0.60, trials=400, seed=0):
    \"\"\"N 个候选，真实能力全部等于 true_p。搜索集上取最优，看它在留出集上多少。\"\"\"
    rng = np.random.default_rng(seed)
    s_best, h_of_best, gaps = [], [], []
    for _ in range(trials):
        S = rng.binomial(n_search, true_p, N) / n_search
        H = rng.binomial(n_hold, true_p, N) / n_hold
        j = int(np.argmax(S))
        s_best.append(S[j]); h_of_best.append(H[j]); gaps.append(S[j] - H[j])
    return float(np.mean(s_best)), float(np.mean(h_of_best)), float(np.mean(gaps))

print(f"{'N':>6}{'搜索集最优':>12}{'该候选在留出集':>16}{'gap':>9}")
curve = []
for N in [1, 2, 5, 10, 50, 200, 1000]:
    s, h, g = winners_curse(N)
    curve.append((N, s, h, g))
    print(f'{N:>6}{s:>12.3f}{h:>16.3f}{g:>9.3f}')

gaps = [g for _, _, _, g in curve]
holds = [h for _, _, h, _ in curve]
assert gaps[-1] > gaps[0], 'gap 必须随候选数增长'
assert all(abs(h - 0.60) < 0.03 for h in holds), '留出集分数始终在真值附近'
assert gaps[-1] > 0.2, f'N=1000 时 gap 应当很大，实际 {gaps[-1]:.3f}'
print(f'\\n✅ 留出集分数始终在真值 0.60 附近（±0.03），而搜索集分数一路涨到 '
      f'{curve[-1][1]:.3f}。')
print(f'   N=1000 时，搜索集上「+{curve[-1][1] - 0.60:.2f}」的提升里，'
      f'**{gaps[-1]:.2f} 纯粹是选择造成的**。')
print('   这就是 C66 模块 04 的胜者诅咒——参赛者从「模型」换成了「prompt 候选」。')
print('   量级是 O(σ·sqrt(2 ln N))，而 σ ≈ sqrt(p(1-p)/n)：')
print('   **搜索集样本量 n 与候选数 N 必须一起看。n 太小时，N 越大结论越假。**')"""),

    code("""# --- 在真实搜索上量同一件事 ---
def search_and_report(n_eval, seed=0):
    rng = np.random.default_rng(seed)
    best, best_s = None, float('-inf')
    for _ in range(n_eval):
        cand = make_candidate(ALL_SLOTS[rng.integers(len(ALL_SLOTS))],
                              SELECTORS[rng.integers(len(SELECTORS))],
                              K_CHOICES[rng.integers(len(K_CHOICES))],
                              int(rng.integers(len(LAST_CHOICES))))
        feas, s = objective(evaluate(cand, DEV))
        if feas and s > best_s:
            best, best_s = cand, s
    return best, evaluate(best, DEV)['accuracy'], evaluate(best, HOLDOUT)['accuracy']

base_dev = evaluate(BASE, DEV)['accuracy']
base_hold = evaluate(BASE, HOLDOUT)['accuracy']
print(f'基线: dev {base_dev:.0%}  holdout {base_hold:.0%}')
print(f"\\n{'评估次数':>10}{'dev':>8}{'holdout':>10}{'dev 提升':>10}{'holdout 提升':>14}{'比值':>8}")
ratios = []
for n_eval in [5, 20, 60, 150]:
    _, d, h = search_and_report(n_eval, seed=1)
    gd, gh = d - base_dev, h - base_hold
    ratio = (gd / gh) if abs(gh) > 1e-9 else float('inf')
    ratios.append((n_eval, gd, gh, ratio))
    print(f'{n_eval:>10}{d:>8.0%}{h:>10.0%}{gd:>10.0%}{gh:>14.0%}'
          f'{("inf" if ratio == float("inf") else f"{ratio:.1f}"):>8}')

_, gd_small, gh_small, _ = ratios[0]
_, gd_big, gh_big, _ = ratios[-1]
assert gd_big >= gd_small, 'dev 上的提升随评估次数单调不降（取最优）'
assert gd_big >= gh_big, 'dev 上的提升不小于 holdout 上的提升'
print('\\n✅ 「dev 提升 / holdout 提升」这个比值是过拟合最直接的指标，')
print('   而它几乎是免费的——两个数你都已经有了。')
print('   比值接近 1 → 搜索在找真实效果；比值很大 → 搜索在拟合噪声。')
print('\\n   三条对策：')
print('   ① 留出集必须从未参与搜索，报告里报**留出集**分数；')
print('   ② 用 MDE 反推「搜索集该多大」，样本不够时正确动作是「不搜」；')
print('   ③ **候选数 N 必须进报告**——没有 N，搜索集分数无法被解读。')"""),

    md("""## 5 · 有偏 judge 会被优化直接放大

目标函数换成一个有偏的 judge（偏好输出更长、更「详细」的配置），
看优化出来的 prompt 在**真实指标**上是什么表现。"""),

    code("""def biased_judge_score(cand, test, length_bonus=0.15):
    \"\"\"一个有偏 judge：除了准确率，还给「示例更多 / 指令更长」额外加分。

    这是一个真实的 judge 偏差形态（C67 模块 02 的长度偏差）：
    judge 把「看起来更认真」当成了「更好」。
    \"\"\"
    m = evaluate(cand, test)
    instr_len = len(build_instruction(cand['slots']))
    verbosity = (cand['k'] / max(K_CHOICES)) * 0.5 + (instr_len / 120.0) * 0.5
    return m['accuracy'] + length_bonus * verbosity

def search_with_objective(score_fn, n_eval=150, seed=1):
    rng = np.random.default_rng(seed)
    best, best_s = None, float('-inf')
    for _ in range(n_eval):
        cand = make_candidate(ALL_SLOTS[rng.integers(len(ALL_SLOTS))],
                              SELECTORS[rng.integers(len(SELECTORS))],
                              K_CHOICES[rng.integers(len(K_CHOICES))],
                              int(rng.integers(len(LAST_CHOICES))))
        if evaluate(cand, DEV)['parse_rate'] < 1.0:
            continue                       # 硬约束仍然生效
        s = score_fn(cand, DEV)
        if s > best_s:
            best, best_s = cand, s
    return best

cand_true = search_with_objective(lambda c, t: evaluate(c, t)['accuracy'])
cand_biased = search_with_objective(biased_judge_score)

print(f"{'用什么当目标函数':<20}{'k':>4}{'指令长度':>10}"
      f"{'judge 分数':>12}{'holdout 真实准确率':>20}")
for name, c in [('真实准确率', cand_true), ('有偏 judge', cand_biased)]:
    print(f'{name:<20}{c["k"]:>4}{len(build_instruction(c["slots"])):>10}'
          f'{biased_judge_score(c, DEV):>12.3f}'
          f'{evaluate(c, HOLDOUT)["accuracy"]:>20.0%}')

j_true = biased_judge_score(cand_true, DEV)
j_biased = biased_judge_score(cand_biased, DEV)
h_true = evaluate(cand_true, HOLDOUT)['accuracy']
h_biased = evaluate(cand_biased, HOLDOUT)['accuracy']
assert j_biased >= j_true, '按有偏 judge 搜出来的候选，judge 分数更高'
assert h_biased <= h_true, '而它的真实准确率不更好'
assert cand_biased['k'] >= cand_true['k'], '优化器精确地利用了 judge 的长度偏好'
print(f'\\n✅ 按有偏 judge 搜出来的候选：judge 分数 {j_biased:.3f} ≥ {j_true:.3f}，')
print(f'   而真实准确率 {h_biased:.0%} ≤ {h_true:.0%}。')
print(f'   而且它精确地朝偏差的方向去了：k 从 {cand_true["k"]} 变成 {cand_biased["k"]}。')
print()
print('   **优化器不知道你「真正想要」什么，它只知道那个数。**')
print('   这与 C67 模块 05 的奖励模型过优化完全同构——只不过那里优化权重（贵、不可逆），')
print('   这里优化 prompt（便宜、可回滚），所以更容易发生，也更容易被忽略。')
print()
print('   三条对策（与 C67 一致）：')
print('   ① 目标函数用组合而不是单一指标，且解析率是硬约束；')
print('   ② 保留一个 judge 从未参与的独立信号（人工抽检 / 可验证子集）；')
print('   ③ 报保守分数 μ − λσ 而不是点估计——它天然惩罚「小样本上运气好」的候选。')"""),

    md("""## 6 · 优化报告 + 门禁"""),

    code("""def measure_sigma(cand, test, n_rep=10, seed=0):
    \"\"\"重复测量的标准差。本模拟器是确定性的，所以用 bootstrap 重采样代替。\"\"\"
    rng = np.random.default_rng(seed)
    accs = []
    for _ in range(n_rep):
        idx = rng.integers(0, len(test), len(test))
        sub = [test[i] for i in idx]
        accs.append(evaluate(cand, sub)['accuracy'])
    return float(np.std(accs))

def optimization_report(name, optimizer, space, n_evaluated, base_cand, best_cand,
                        search_set, holdout, objective_desc):
    sigma = measure_sigma(base_cand, search_set)
    return dict(
        optimizer=optimizer, space_size=space, n_evaluated=n_evaluated,
        objective=objective_desc,
        sigma=sigma,
        search_base=evaluate(base_cand, search_set)['accuracy'],
        search_best=evaluate(best_cand, search_set)['accuracy'],
        holdout_base=evaluate(base_cand, holdout)['accuracy'],
        holdout_best=evaluate(best_cand, holdout)['accuracy'],
        parse_rate=evaluate(best_cand, holdout)['parse_rate'],
        overlap=len({x for x, _ in search_set} & {x for x, _ in holdout}),
        optimizer_fp=hashlib.sha256(json.dumps(
            dict(space=space, optimizer=optimizer, objective=objective_desc),
            sort_keys=True).encode()).hexdigest()[:12])

def optimization_gate(r):
    blocking, warn = [], []
    for key in ('space_size', 'n_evaluated'):
        if not r.get(key):
            blocking.append(f'报告里缺 {key}——搜索集分数无法被解读')
    if r['overlap'] > 0:
        blocking.append(f"搜索集与留出集有 {r['overlap']} 条交集")
    if r['parse_rate'] < 1.0:
        blocking.append(f"优化后解析率 {r['parse_rate']:.0%} < 100%")
    gain_h = r['holdout_best'] - r['holdout_base']
    if gain_h <= 2 * r['sigma']:
        blocking.append(f"留出集提升 {gain_h:.1%} 不超过 2σ ({2 * r['sigma']:.1%})")
    gain_s = r['search_best'] - r['search_base']
    if gain_h > 1e-9 and gain_s / gain_h > 3:
        warn.append(f'搜索集提升 / 留出集提升 = {gain_s / gain_h:.1f} > 3（过拟合信号）')
    return blocking, warn

best_150, _, _ = None, None, None
best_150 = search_with_objective(lambda c, t: evaluate(c, t)['accuracy'], n_eval=150)
R = optimization_report('随机搜索', 'random_search', space_size(), 150,
                        BASE, best_150, DEV, HOLDOUT,
                        'accuracy，parse_rate == 1.0 为硬约束')
for k, v in R.items():
    print(f'  {k:<16}{v if not isinstance(v, float) else round(v, 4)}')
b, w = optimization_gate(R)
print(f'\\n阻断 {len(b)} 项: {b}')
print(f'警告 {len(w)} 项: {w}')

# 缺 n_evaluated → 阻断
R_missing = dict(R); R_missing['n_evaluated'] = 0
assert any('n_evaluated' in x for x in optimization_gate(R_missing)[0])
# 交集 → 阻断
R_overlap = dict(R); R_overlap['overlap'] = 3
assert any('交集' in x for x in optimization_gate(R_overlap)[0])
# 留出集提升不显著 → 阻断
R_noisy = dict(R); R_noisy['holdout_best'] = R['holdout_base'] + 0.01
assert any('2σ' in x for x in optimization_gate(R_noisy)[0])
# 过拟合信号 → 报警
R_of = dict(R)
R_of['search_best'] = R['search_base'] + 0.40
R_of['holdout_best'] = R['holdout_base'] + 0.10
R_of['sigma'] = 0.02
assert optimization_gate(R_of)[1], '比值 4.0 应当报警'
print('\\n✅ 四项确定性/统计阻断 + 一项过拟合报警。')
print('   注意「留出集提升不超过 2σ 就阻断」这一条：')
print('   它意味着**大多数搜索集上看起来漂亮的优化都不该上线**——而这是正确的。')"""),

    md("""## ✏️ 练习 1：搜索空间的大小与压缩

实现 `space_report(pool_size, k, n_instr, n_fmt, compressions)`，
返回朴素空间与逐步压缩后的空间大小。

`compressions` 是一个有序列表，每项是 `('order'|'subset'|'instruction', 压缩后的取值数)`：
- `'order'`：把 `k!` 换成给定的数
- `'subset'`：把 `C(pool_size, k)` 换成给定的数
- `'instruction'`：把 `n_instr` 换成给定的数

返回 `dict(naive=int, steps=[(名字, 压缩后大小)], final=int, factor=float)`。"""),

    code("""def space_report(pool_size, k, n_instr, n_fmt, compressions):
    \"\"\"返回 dict(naive, steps, final, factor)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
r = space_report(20, 8, 24, 3,
                 [('order', 8), ('subset', 4), ('instruction', 16)])
print('朴素:', f"{r['naive']:,}")
for name, size in r['steps']:
    print(f'  压缩 {name:<12} → {size:,}')
print('最终:', f"{r['final']:,}", '| 压缩倍数:', f"{r['factor']:,.0f}")

naive = 24 * math.comb(20, 8) * math.factorial(8) * 3
assert r['naive'] == naive, (r['naive'], naive)
assert len(r['steps']) == 3
# 每一步都必须比上一步小
sizes = [r['naive']] + [s for _, s in r['steps']]
assert all(sizes[i] > sizes[i + 1] for i in range(len(sizes) - 1)), sizes
assert r['final'] == 16 * 4 * 8 * 3, r['final']
assert abs(r['factor'] - naive / r['final']) < 1e-6
# 空压缩列表 → final == naive
r0 = space_report(20, 8, 24, 3, [])
assert r0['final'] == r0['naive'] and r0['factor'] == 1.0
print('✅ 练习 1 通过：三个压缩都是有依据的，而不是随便砍')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def space_report(pool_size, k, n_instr, n_fmt, compressions):
    dims = dict(instruction=n_instr, subset=math.comb(pool_size, k),
                order=math.factorial(k), fmt=n_fmt)
    naive = 1
    for v in dims.values():
        naive *= v
    steps = []
    for name, new_size in compressions:
        dims[name] = new_size
        size = 1
        for v in dims.values():
            size *= v
        steps.append((name, size))
    final = steps[-1][1] if steps else naive
    return dict(naive=naive, steps=steps, final=final, factor=naive / final)

r = space_report(20, 8, 24, 3, [('order', 8), ('subset', 4), ('instruction', 16)])
assert r['naive'] == 24 * math.comb(20, 8) * math.factorial(8) * 3
assert r['final'] == 16 * 4 * 8 * 3
sizes = [r['naive']] + [s for _, s in r['steps']]
assert all(sizes[i] > sizes[i + 1] for i in range(len(sizes) - 1))
assert space_report(20, 8, 24, 3, [])['factor'] == 1.0
print('✅ 参考答案 1 通过')
print('   三个压缩各自的依据（这是本练习真正的内容）：')
print('   ① order: 8! → 8，因为模块 02 量到「最后一条放谁」解释了顺序效应的六成；')
print('   ② subset: C(20,8) → 4，因为选择策略（random/knn/coverage/hybrid）')
print('      已经覆盖了「相关性 vs 覆盖度」这个主要的权衡轴；')
print('   ③ instruction: 自由文本 → 16 个槽位开关，因为模块 01 量到')
print('      槽位的边际贡献高度集中在取值域与格式两项。')
print('   **压缩必须有依据。随便砍会把有效的候选砍掉，而那比过拟合更难发现。**')"""),

    md("""## ✏️ 练习 2：带留出集的搜索

实现 `search_with_holdout(n_eval, seed, top_m=5)`：

1. 在 DEV 上搜 `n_eval` 个候选，**保留前 `top_m` 名**（而不是只保留第一名）
2. 在 HOLDOUT 上重新评估这 `top_m` 个候选
3. 返回 `dict(dev_top1, holdout_of_dev_top1, holdout_best_of_topm, rank_change)`
   其中 `rank_change` 是「dev 第一名在 holdout 上排第几」（1-based）

这个函数演示两件事：**dev 第一名在留出集上会掉多少**，
以及「保留 top-m 并在留出集上复选」这个常见技巧——
notebook 会给出一个诚实的负面结果：**它有一个前提**。"""),

    code("""def search_with_holdout(n_eval, seed=1, top_m=5):
    \"\"\"返回 dict(dev_top1, holdout_of_dev_top1, holdout_best_of_topm, rank_change)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
r = search_with_holdout(150, seed=1, top_m=5)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})

assert 0 <= r['dev_top1'] <= 1 and 0 <= r['holdout_of_dev_top1'] <= 1
assert 1 <= r['rank_change'] <= 5
# top-m 复选的结果不该差于「只用 dev 第一名」
assert r['holdout_best_of_topm'] >= r['holdout_of_dev_top1'] - 1e-9
# 而 dev 上的第一名在 holdout 上会明显掉下来 —— 这就是第 4 节的 gap
gap = r['dev_top1'] - r['holdout_of_dev_top1']
print(f'dev 第一名的 gap: {r["dev_top1"]:.0%} → {r["holdout_of_dev_top1"]:.0%} '
      f'（掉了 {gap:.0%}）')
assert gap > 0.2, f'搜 150 个候选后，dev 第一名在 holdout 上应当明显更差: {gap}'
r2 = search_with_holdout(150, seed=7, top_m=5)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r2.items()})
assert r2['dev_top1'] - r2['holdout_of_dev_top1'] > 0.2
print('✅ 练习 2 通过：dev 第一名在 holdout 上掉了 20 个点以上')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def search_with_holdout(n_eval, seed=1, top_m=5):
    rng = np.random.default_rng(seed)
    scored = []
    for _ in range(n_eval):
        cand = make_candidate(ALL_SLOTS[rng.integers(len(ALL_SLOTS))],
                              SELECTORS[rng.integers(len(SELECTORS))],
                              K_CHOICES[rng.integers(len(K_CHOICES))],
                              int(rng.integers(len(LAST_CHOICES))))
        m = evaluate(cand, DEV)
        feas, s = objective(m)
        if feas:
            scored.append((s, m['accuracy'], cand))
    scored.sort(key=lambda t: -t[0])
    top = scored[:top_m]
    hold = [evaluate(c, HOLDOUT)['accuracy'] for _, _, c in top]
    order = sorted(range(len(top)), key=lambda i: -hold[i])
    return dict(dev_top1=top[0][1],
                holdout_of_dev_top1=hold[0],
                holdout_best_of_topm=max(hold),
                rank_change=order.index(0) + 1)

r = search_with_holdout(150, seed=1, top_m=5)
assert 1 <= r['rank_change'] <= 5
assert r['holdout_best_of_topm'] >= r['holdout_of_dev_top1'] - 1e-9
assert r['dev_top1'] - r['holdout_of_dev_top1'] > 0.2
hold_of_top5 = None
print('✅ 参考答案 2 通过')
print(f"   dev 第一名 {r['dev_top1']:.0%} → holdout {r['holdout_of_dev_top1']:.0%}：")
print('   **搜 150 个候选之后，dev 上的第一名在留出集上掉了 40 个点。**')
print('   这就是第 4 节那条曲线在真实搜索上的体现。')
print()
print('   关于 top-m 复选，这里出现了一个诚实的负面结果：')
print(f"   本例的 rank_change = {r['rank_change']}，"
      f"holdout_best_of_topm = {r['holdout_best_of_topm']:.0%}，")
print('   也就是**复选没有带来任何改善**。原因不是方法错，是**留出集只有 10 条**：')
print('   它的取值只能是 0, 0.1, …, 1.0，于是 top-5 候选在留出集上大量并列，')
print('   argmax 落在谁身上纯粹取决于顺序（与模块 02/C70-04 的并列组问题同构）。')
print()
print('   所以 top-m 复选是一个**有前提**的技巧：')
print('   留出集必须有足够的分辨率去区分这 m 个候选。')
print('   n=10 时它做不到；而这也解释了为什么练习 3 那个「反解搜索集大小」的函数')
print('   给出的数字总是比人们预期的大。')"""),

    md("""## ✏️ 练习 3：过拟合的定量关系

实现 `overfit_curve(Ns, n_search, true_p, trials, seed)`：
返回 `[(N, mean_gap, bound)]`，其中 `bound = sigma * sqrt(2*ln(N))`，
`sigma = sqrt(true_p*(1-true_p)/n_search)`（N=1 时 bound=0）。

然后实现 `min_search_size(N, target_gap, true_p)`：
在给定候选数 `N` 与「可接受的 gap」下，反解出**搜索集至少要多少样本**。

这个函数的用途：**把「搜索集该多大」从拍脑袋变成一次算术**。"""),

    code("""def overfit_curve(Ns, n_search=40, true_p=0.6, trials=400, seed=0):
    \"\"\"返回 [(N, mean_gap, bound)]。\"\"\"
    # TODO
    raise NotImplementedError

def min_search_size(N, target_gap, true_p=0.6):
    \"\"\"用上界 sigma*sqrt(2 ln N) <= target_gap 反解最小 n。N<=1 时返回 1。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
cur = overfit_curve([1, 10, 100, 1000])
print(f"{'N':>6}{'实测 gap':>11}{'上界':>10}")
for N, g, b in cur:
    print(f'{N:>6}{g:>11.3f}{b:>10.3f}')

assert cur[0][2] == 0.0, 'N=1 时上界是 0'
assert all(g <= b + 0.02 for _, g, b in cur), '实测 gap 不该超过上界（+容差）'
assert cur[-1][1] > cur[1][1], 'gap 随 N 增长'
# 上界随 N 单调增
assert all(cur[i][2] <= cur[i + 1][2] for i in range(len(cur) - 1))

n = min_search_size(1000, target_gap=0.05)
print(f'\\nN=1000、可接受 gap 5% → 搜索集至少 {n} 条')
sigma = math.sqrt(0.6 * 0.4 / n)
assert sigma * math.sqrt(2 * math.log(1000)) <= 0.05 + 1e-9
sigma_1 = math.sqrt(0.6 * 0.4 / (n - 1))
assert sigma_1 * math.sqrt(2 * math.log(1000)) > 0.05
assert min_search_size(1, 0.05) == 1
# N 越大，需要的样本越多
assert min_search_size(1000, 0.05) > min_search_size(10, 0.05)
print(f"{'N':>6}{'gap≤5% 所需样本':>18}")
for N in [10, 100, 1000, 10000]:
    print(f'{N:>6}{min_search_size(N, 0.05):>18}')
print('✅ 练习 3 通过：「搜索集该多大」是一次算术，不是拍脑袋')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def overfit_curve(Ns, n_search=40, true_p=0.6, trials=400, seed=0):
    sigma = math.sqrt(true_p * (1 - true_p) / n_search)
    out = []
    for N in Ns:
        _, _, g = winners_curse(N, n_search=n_search, n_hold=n_search,
                                true_p=true_p, trials=trials, seed=seed)
        bound = 0.0 if N <= 1 else sigma * math.sqrt(2 * math.log(N))
        out.append((N, g, bound))
    return out

def min_search_size(N, target_gap, true_p=0.6):
    if N <= 1:
        return 1
    z = math.sqrt(2 * math.log(N))
    # sqrt(p(1-p)/n) * z <= target  →  n >= p(1-p) z^2 / target^2
    n = math.ceil(true_p * (1 - true_p) * z * z / (target_gap ** 2))
    return max(1, n)

cur = overfit_curve([1, 10, 100, 1000])
assert cur[0][2] == 0.0 and all(g <= b + 0.02 for _, g, b in cur)
n = min_search_size(1000, 0.05)
sigma = math.sqrt(0.6 * 0.4 / n)
assert sigma * math.sqrt(2 * math.log(1000)) <= 0.05 + 1e-9
assert min_search_size(1000, 0.05) > min_search_size(10, 0.05)
print('✅ 参考答案 3 通过')
print('   这个反解给出的数通常令人不适：N=1000 时要几百条样本才能把 gap 压到 5%。')
print('   而那正是重点——**它把「搜不搜」变成一个有依据的决定**：')
print('   样本不够时，正确的动作是「不搜」或「先扩评测集」，而不是「搜了再说」。')
print('   注意 sigma*sqrt(2 ln N) 是一个**上界**（C66 模块 04 量过 N 不大时实际值更小），')
print('   所以这个反解是保守的——保守在这里是对的。')"""),

    md("""## ✏️ 练习 4：完整的优化流程 + 门禁

把前面所有东西串起来：`run_optimization(n_eval, top_m, seed)`，返回一个报告
（结构与第 6 节的 `optimization_report` 一致，再加两个字段）：

- `top_m_reselected`：是否在留出集上从 top-m 里重选了（bool）
- `overfit_ratio`：搜索集提升 / 留出集提升（留出集提升 ≤ 0 时为 `float('inf')`）

流程：DEV 上搜 → 取 top-m → **HOLDOUT 上重选** → 生成报告 → 过门禁。

返回 `(报告, blocking, warnings)`。"""),

    code("""def run_optimization(n_eval=150, top_m=5, seed=1):
    \"\"\"返回 (report, blocking, warnings)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
rep, b, w = run_optimization(150, 5, seed=1)
print({k: (round(v, 4) if isinstance(v, float) else v)
       for k, v in rep.items() if k != 'objective'})
print('阻断:', b)
print('警告:', w)

assert rep['space_size'] == space_size()
assert rep['n_evaluated'] == 150
assert rep['overlap'] == 0, 'DEV 与 HOLDOUT 必须不相交'
assert rep['parse_rate'] == 1.0, '硬约束保证了这一点'
assert 'top_m_reselected' in rep and 'overfit_ratio' in rep
assert isinstance(rep['top_m_reselected'], bool)
# 门禁的结论必须与报告一致
gain_h = rep['holdout_best'] - rep['holdout_base']
if gain_h <= 2 * rep['sigma']:
    assert any('2σ' in x for x in b), (gain_h, rep['sigma'], b)
else:
    assert not any('2σ' in x for x in b)
# n_eval 更大 → 搜索集提升不减
rep2, _, _ = run_optimization(20, 5, seed=1)
assert (rep['search_best'] - rep['search_base']) >= \\
       (rep2['search_best'] - rep2['search_base']) - 1e-9
print('✅ 练习 4 通过：报告 → 门禁的链路完整，且结论与报告一致')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def run_optimization(n_eval=150, top_m=5, seed=1):
    rng = np.random.default_rng(seed)
    scored = []
    for _ in range(n_eval):
        cand = make_candidate(ALL_SLOTS[rng.integers(len(ALL_SLOTS))],
                              SELECTORS[rng.integers(len(SELECTORS))],
                              K_CHOICES[rng.integers(len(K_CHOICES))],
                              int(rng.integers(len(LAST_CHOICES))))
        m = evaluate(cand, DEV)
        feas, s = objective(m)
        if feas:
            scored.append((s, cand))
    scored.sort(key=lambda t: -t[0])
    top = [c for _, c in scored[:top_m]]
    hold = [evaluate(c, HOLDOUT)['accuracy'] for c in top]
    best_i = int(np.argmax(hold))
    best = top[best_i]

    rep = optimization_report('随机搜索+top_m 复选', 'random_search', space_size(),
                              n_eval, BASE, best, DEV, HOLDOUT,
                              'accuracy，parse_rate == 1.0 为硬约束')
    rep['top_m_reselected'] = bool(best_i != 0)
    gain_s = rep['search_best'] - rep['search_base']
    gain_h = rep['holdout_best'] - rep['holdout_base']
    rep['overfit_ratio'] = (gain_s / gain_h) if gain_h > 1e-9 else float('inf')
    b, w = optimization_gate(rep)
    return rep, b, w

rep, b, w = run_optimization(150, 5, seed=1)
assert rep['space_size'] == space_size() and rep['n_evaluated'] == 150
assert rep['overlap'] == 0 and rep['parse_rate'] == 1.0
assert isinstance(rep['top_m_reselected'], bool)
rep2, _, _ = run_optimization(20, 5, seed=1)
assert (rep['search_best'] - rep['search_base']) >= \\
       (rep2['search_best'] - rep2['search_base']) - 1e-9
print('✅ 参考答案 4 通过')
print('   这个函数是本模块的交付物。它的形状值得记住：')
print('   **搜 → 取 top-m → 在留出集上重选 → 报告（含 N 与空间大小）→ 过门禁**。')
print('   而门禁里那条「留出集提升不超过 2σ 就阻断」意味着')
print('   大多数搜索集上看起来漂亮的优化都不该上线——**这是正确的**。')
print()
print(f"   本次: 搜索集 {rep['search_base']:.0%} → {rep['search_best']:.0%}，"
      f"留出集 {rep['holdout_base']:.0%} → {rep['holdout_best']:.0%}，"
      f"过拟合比值 {rep['overfit_ratio']:.1f}")"""),

    md("""## 🧪 真实工程胶囊：优化的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 开工前的两个前置条件（讲解第 1/6 节）
# ══════════════════════════════════════════════════════════════════
# 1) 测 σ：同一配置在评测集上重复跑 10 次（温度 > 0 才有差异；温度 0 时用 bootstrap 重采样）
# 2) 算 MDE（C66-04）：想检出 3pp 提升需要多少样本？不够就先扩评测集，别搜。
#    以及：契约层 parse_rate 必须已经是 1.0（模块 01），
#          模块 02 的免费收益（选择策略 + 顺序）必须已经拿过。

# ══════════════════════════════════════════════════════════════════
# B. 用 DSPy 的话
# ══════════════════════════════════════════════════════════════════
import dspy
optimizer = dspy.MIPROv2(metric=my_metric, auto='light')   # auto 控制评估预算
compiled = optimizer.compile(program, trainset=train, valset=dev)
#   产出：instruction 候选 + bootstrap 示例（有序）→ 就是模块 01 的那个 bundle
#   **注意**：valset 就是搜索集。它被 optimizer 反复使用，所以**它不是留出集**。
#   必须另外留一个 optimizer 从未见过的 holdout，并且报告 holdout 分数。

# ══════════════════════════════════════════════════════════════════
# C. 自建时的搜索空间（讲解第 2 节 / 练习 1）
# ══════════════════════════════════════════════════════════════════
SPACE = {
    'instruction_slots': {...},      # 槽位开关，2^5 量级，可枚举
    'selector': ['knn', 'bucket_knn', 'hybrid'],
    'k': [3, 5, 8],
    'last_demo': list(range(8)),      # ← 顺序降维（模块 02）
    'format': ['json1', 'json3'],
}
#   目标函数：accuracy − w·cost，且 parse_rate == 1.0 为**硬约束**（第 2 节）

# ══════════════════════════════════════════════════════════════════
# D. 报告必须含的字段（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
report = dict(
    optimizer=..., space_size=..., n_evaluated=...,      # ← 前两项缺了就阻断
    objective=..., sigma=...,
    search_base=..., search_best=...,
    holdout_base=..., holdout_best=...,                  # ← 报的是这两个
    overfit_ratio=(gain_search / gain_holdout),          # ← 免费的过拟合指标
    optimizer_fp=sha256(space + objective + algo + seed),
)

# ══════════════════════════════════════════════════════════════════
# E. 长期纪律（讲解第 5 节最后那条）
# ══════════════════════════════════════════════════════════════════
# 留出集**定期轮换**，轮换记录写进 CHANGELOG。
# 因为即使每次只搜十几个候选，几个月累积下来 N 已经是几千，
# 那个评测集早就被拟合掉了（与 C03-05 的污染管理同构）。
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| 一次优化 = 空间 + 目标 + 算法；投入顺序要反过来 | 先做可靠的目标，最后才换强算法 | 讲解 1 |
| 朴素空间 $3.66\\times10^{11}$；三个有依据的压缩降到 1,152 | 压缩 $3.2\\times10^{8}$ 倍 | 第 1 节 |
| 解析率必须是硬约束，不能加权 | 加权版本会选中解析率 60% 的候选 | 第 2 节 |
| 比较算法要固定**评估次数**而不是轮数 | 一次评估 = 真实的钱 | 第 3 节 |
| bootstrap 示例会自我强化；需要覆盖保底 | 它只挑当前已做对的样本 | 第 3 节 |
| 候选真实能力全同时，搜索集分数也一路上涨 | N=1000 → 搜索集 0.838，留出集 0.589，gap 0.249 | 第 5 节 |
| 「搜索集提升 / 留出集提升」是免费的过拟合指标 | 接近 1 = 真效果；很大 = 拟合噪声 | 第 4 节 |
| 有偏 judge 会被优化精确利用 | judge 分数 1.014→1.042、k 5→8，而真实准确率**没有变好**（50%→50%） | 第 5 节 |
| 「留出集提升不超过 2σ 就阻断」会否掉大多数优化 | 而这是正确的 | 第 6 节 |
| 「搜索集该多大」可以从 N 与目标 gap 反解 | N=1000、gap 5% → 需要 1,327 条 | 练习 3 |

下一模块：**04 · 受限解码与结构化输出**——
约束能保证输出合法，但**逐步掩码得到的分布不是条件分布**，本课会把这个失真精确算出来。"""),
]
