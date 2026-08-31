# -*- coding: utf-8 -*-
"""C66 模块 04 · 可靠性与统计（pass@k / pass^k / 方差分解 / 功效 / 胜者诅咒）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 03（轨迹指标）；C03 模块 02（评测统计）读过更好，"
                 "但本模块的自举、配对检验、功效分析都会从零推一遍"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_reliability_stats.ipynb'
                       '（方差分解：任务间 vs 任务内 / pass@k 与 pass^k 的无偏估计 / '
                       '任务数与重复数的预算最优分配 / 聚类自举 vs 朴素自举的覆盖率对比 / '
                       'McNemar 与配对自举 / 胜者诅咒模拟）'),
    ("核心参考", "Chen et al., <em>Evaluating LLMs Trained on Code</em>（2021，pass@k 无偏估计器）· "
                 "Yao et al., <em>τ-bench</em>（2024，pass^k）· "
                 "Efron &amp; Tibshirani, <em>An Introduction to the Bootstrap</em>（1993，聚类自举）· "
                 "Miller, <em>Adding Error Bars to Evals</em>（2024）· "
                 "本课程 C03 模块 02（统计显著性）· C10 模块 07（在线 A/B）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("variance-sources", "一个 agent 分数的方差从哪来：四个来源与它们的层级", "".join([
        P("模块 00 说过 agentic 评测有两个随机源。现在把它拆细——实际有四个，"
          "而且它们处在<strong>不同的层级</strong>，这决定了压方差的手段完全不同。"),
        ASCII("""
   ┌─ ① 任务间方差 σ²_between ────────────────────────────────────┐
   │   不同任务的难度不同。这是**最大**的方差来源，常占一半以上。   │
   │   压制手段：**配对设计**（同一批任务比较两个 agent）           │
   ├─ ② 任务内方差 σ²_within ─────────────────────────────────────┤
   │   同一任务重复跑，结果时对时错。来自采样温度 + 环境随机性。     │
   │   压制手段：**每个任务多跑几次**（k 次重复）                   │
   ├─ ③ 用户/环境模拟器方差 ──────────────────────────────────────┤
   │   模拟用户是另一个 LLM；页面加载时序、外部 API 抖动。          │
   │   压制手段：钉死模拟器模型与温度；录制回放                     │
   └─ ④ harness / 基础设施方差 ───────────────────────────────────┘
       超时阈值、并发度、重试策略、容器调度。**换个并发度分数就变**。
       压制手段：钉死配置并写进报告（05 模块）
"""),
        P("四者中，只有 ① 和 ② 能用统计手段处理，③ 和 ④ 必须靠工程手段消除——"
          "<strong>它们不是随机误差，是没被控制住的自变量。</strong>"),
        MATH(r"\operatorname{Var}(\bar{X}) = \frac{\sigma^2_{\text{between}}}{N} + \frac{\sigma^2_{\text{within}}}{N k}"),
        P("其中 $N$ 是任务数、$k$ 是每个任务的重复次数。这个式子有一个非常实用的推论："),
        CALLOUT("intuition", "<strong>加重复次数 $k$ 的收益有天花板，加任务数 $N$ 的收益没有。</strong>"
                             "把 $k$ 从 1 加到无穷，方差最多降到 $\\sigma^2_{\\text{between}}/N$——"
                             "换算成标准差，最多只能压到 $k=1$ 时的 $\\sqrt{\\rho}$ 倍"
                             "（$\\rho$ 是组内相关系数，见第 4 节）。"
                             "agent 评测的 $\\rho$ 常在 0.4–0.8，也就是说<strong>把重复次数加到无穷，"
                             "标准差最多只降三到四成</strong>。"
                             "<em>反过来，$N$ 翻倍两项一起减半。所以「先扩任务集，再加重复」几乎总是对的</em>"
                             "——除非你的目标是 pass^k 这种<strong>本身就定义在重复上</strong>的指标。"),
        DUAL(
            "但是——这里有个真实的成本约束把上面这条建议部分推翻了：<strong>agentic 任务的边际成本极高</strong>。"
            "加一道任务要写环境、写判分器、做人工审核；加一次重复只要多花一次 API 调用。"
            "所以现实里的最优解通常是「任务数被预算卡死在 $N$，然后在剩下的钱里选 $k$」。"
            "notebook 第 3 节会把这个取舍算成一道最优化题。",
            "形式化：在预算约束 $N c_{\\text{task}} + N k c_{\\text{run}} \\le B$ 下最小化 "
            "$\\frac{\\sigma^2_b}{N} + \\frac{\\sigma^2_w}{Nk}$，"
            "可以解出最优重复次数 $k^{*} = \\sqrt{\\dfrac{\\sigma^2_w}{\\sigma^2_b} \\cdot \\dfrac{c_{\\text{task}}}{c_{\\text{run}}}}$。"
            "<strong>这是经典的整群抽样最优分配公式</strong>：任务越贵（$c_{\\text{task}}$ 大）、"
            "任务内噪声越大（$\\sigma^2_w$ 大），就越该在每个任务上多跑几次。"
            "<em>它同时解释了为什么 SWE-bench 类基准（任务极贵）值得多跑几个 epoch，"
            "而合成任务集（任务几乎免费）应该直接扩任务数。</em>",
        ),
    ])),

    # ============================================================== 2
    ("passk", "pass@k 与 pass^k：两个指标，两种产品", "".join([
        P("这是本模块最需要被记住的一节。两个符号只差一个位置，含义完全相反。"),
        TABLE(["指标", "问的问题", "公式（$n$ 次采样中成功 $c$ 次的无偏估计）", "适用场景"], [
            ["<strong>pass@k</strong>", "试 $k$ 次，<strong>至少</strong>成功一次的概率", "$1 - \\dfrac{\\binom{n-c}{k}}{\\binom{n}{k}}$", "结果<strong>有人复核或有验证器</strong>：代码补全、候选生成、best-of-n"],
            ["<strong>pass^k</strong>", "试 $k$ 次，<strong>全部</strong>成功的概率", "$\\dfrac{\\binom{c}{k}}{\\binom{n}{k}}$", "结果<strong>直接执行、没人复核</strong>：自动退款、自动改配置、自动发邮件"],
        ]),
        P("为什么必须用无偏估计器而不是「跑 $k$ 次数一数」？因为后者只用了一次实验的信息，方差极大。"
          "无偏估计器的思路是：<strong>跑 $n \\gg k$ 次，然后计算「从这 $n$ 次里随机抽 $k$ 次会发生什么」的期望</strong>，"
          "这等价于对 $\\binom{n}{k}$ 种抽法求平均，方差大幅降低。"),
        ASCII("""
   单任务成功率 p = 0.7 时：

   k:        1      2      3      5      8
   pass@k  0.700  0.910  0.973  0.998  1.000   ← 随 k 单调**上升**，很快饱和到 1
   pass^k  0.700  0.490  0.343  0.168  0.058   ← 随 k 单调**下降**，指数衰减

   同一个 agent，报 pass@8 是"接近完美"，报 pass^8 是"基本不可用"。
   两个数字都没撒谎——它们回答的是两个不同的产品问题。
"""),
        CALLOUT("danger", "<strong>用错指标是 agent 评测里最常见、也最有实际后果的错误。</strong>"
                          "一个客服 agent 的 pass@8 有 99%，听起来可以上线；"
                          "但它每次处理一个真实工单只有<em>一次</em>机会，没人会帮它挑八个候选里最好的那个——"
                          "真正决定产品体验的是 pass^1（即单次成功率）和它在重复运行下的稳定性。"
                          "<strong>判断标准只有一条：<em>结果被执行之前，有没有人（或验证器）能挑一挑？</em></strong>"
                          "有 → pass@k；没有 → pass^k。"),
        H3("pass^k 的另一层含义：它在测「一致性」而不只是「能力」"),
        P("如果一个 agent 的行为完全确定（同一输入永远同一输出），"
          "那么 $\\text{pass}^k = \\text{pass}^1$ 对所有 $k$ 成立——曲线是水平的。"
          "<strong>pass^k 随 $k$ 下降得越快，说明这个 agent 的行为越不稳定。</strong>"
          "所以 $\\text{pass}^1 - \\text{pass}^k$ 这个差值本身就是一个有用的<em>不一致性指标</em>，"
          "它把「能力」和「可靠性」分开了：<em>能力决定曲线的起点，可靠性决定曲线的斜率</em>。"),
    ])),

    # ============================================================== 3
    ("paired", "配对设计：把最大的方差源直接消掉", "".join([
        P("回到第 1 节的结论：任务间方差占大头。配对设计的全部思想就是<strong>不去估计它</strong>。"),
        DUAL(
            "独立设计问的是「A 的平均分是多少？B 的平均分是多少？两者差多少？」——"
            "这里面「任务有难有易」的波动被算了两遍。"
            "配对设计问的是「<strong>在同一道题上</strong>，A 和 B 谁赢？」——"
            "题目难度对两者是同一个数，做差的时候直接消掉了。",
            "形式化：设任务 $i$ 上 A 与 B 的得分为 $X_i, Y_i$，差值 $D_i = X_i - Y_i$。"
            "则 $\\operatorname{Var}(D_i) = \\operatorname{Var}(X_i) + \\operatorname{Var}(Y_i) - 2\\operatorname{Cov}(X_i, Y_i)$。"
            "<strong>由于两个 agent 在同一批任务上的得分高度正相关（难题对谁都难），"
            "$\\operatorname{Cov}$ 项很大，$\\operatorname{Var}(D_i)$ 远小于 $\\operatorname{Var}(X_i) + \\operatorname{Var}(Y_i)$。</strong>"
            "在二值结果的情形下，这直接退化为 <span class=\"term\">McNemar 检验</span>："
            "只有「一个对一个错」的<em>不一致对</em>携带信息，一致对（都对/都错）对差值的检验完全无贡献。",
        ),
        MATH(r"\chi^2_{\text{McNemar}} = \frac{(|b - c| - 1)^2}{b + c}, \quad b, c \text{ 是两类不一致对的计数}"),
        TABLE(["设计", "需要的任务数（区分 3 个点）", "前提条件", "什么时候不能用"], [
            ["独立设计", "每组约 4000+", "无", "—"],
            ["<strong>配对设计</strong>", "约 1500–2000（不一致率 20% 时）", "<strong>两个 agent 必须跑同一批任务、同一套 harness</strong>", "任务集在两次运行之间变过；harness 版本变过"],
            ["配对 + 多次重复", "更少（用任务内均值代替 0/1，进一步降方差）", "同上 + 记录了 <code>attempt</code> 字段", "预算不允许"],
        ]),
        CALLOUT("warn", "配对设计有一个必须遵守的纪律：<strong>两个 agent 的运行必须在同一次评测运行里完成，"
                        "或者至少共享完全相同的环境快照</strong>。"
                        "如果你今天跑 A、下周跑 B，中间容器镜像更新过、外部 API 改过、任务集补过题，"
                        "那么这就<em>不是</em>配对设计——你以为消掉了任务难度，实际上引入了一个更大的时间混杂因素。"),
    ])),

    # ============================================================== 4
    ("clustered-ci", "置信区间：把 $Nk$ 次 rollout 当独立样本是错的", "".join([
        P("一个极其常见的错误：跑了 500 道任务 × 每题 5 次 = 2500 条轨迹，"
          "然后按 $n = 2500$ 算置信区间。<strong>这会把区间宽度低估到只有真实值的一半左右。</strong>"),
        P("原因是同一任务的 5 次重复<strong>不独立</strong>——它们共享同一个任务难度。"
          "统计学上这叫<span class=\"term\">整群结构</span>（clustered data），"
          "有效样本量不是 $Nk$，而是"),
        MATH(r"n_{\text{eff}} = \frac{Nk}{1 + (k-1)\rho}"),
        P("其中 $\\rho$ 是<strong>组内相关系数</strong>（intra-cluster correlation）。"
          "在 agent 评测里 $\\rho$ 通常很高（0.4–0.8），因为任务难度主导一切。"
          "取 $\\rho = 0.7$、$k = 5$：$n_{\\text{eff}} = 2500 / (1 + 4 \\times 0.7) = 658$——"
          "<strong>不到名义样本量的三成。</strong>"),
        H3("正确做法：按任务重采样的聚类自举"),
        CODE("""# 错误：把每条轨迹当独立样本
boot = rng.choice(all_2500_rollouts, size=2500)          # ✗ 区间会窄一半

# 正确：重采样「任务」，每个被抽中的任务连同它的全部 k 次重复一起进来
task_ids = rng.choice(unique_tasks, size=N, replace=True) # ✓
boot = concat(rollouts_of(t) for t in task_ids)"""),
        CALLOUT("intuition", "记忆口诀：<strong>自举要重采样「最外层的独立单位」</strong>。"
                             "在 agent 评测里，独立单位是<em>任务</em>，不是 rollout，也不是步骤。"
                             "同理，如果你的任务集里同一个仓库贡献了 30 道题，"
                             "严格来说独立单位是<em>仓库</em>而不是任务——这会让区间进一步变宽。"
                             "<em>要不要做到这一层，取决于你的结论是想推广到「这些任务」还是「这类仓库」。</em>"),
        P("notebook 第 4 节会用模拟验证这件事：构造一个已知真值的场景，"
          "分别用朴素自举和聚类自举算 95% 区间，统计<strong>覆盖率</strong>"
          "（真值落在区间内的比例）。朴素自举的覆盖率会显著低于 95%——"
          "<em>这是评测报告里「误差棒画得太窄」的直接来源</em>。"),
    ])),

    # ============================================================== 5
    ("power", "功效分析：要跑多少才够，以及预算该怎么切", "".join([
        P("把前四节合起来，就能回答那个每次都会被问到的问题：<strong>「我要跑多少才够？」</strong>"),
        H3("三个必须先回答的前置问题"),
        OL([
            "<strong>你要检测多大的差异？</strong>（最小实际重要差异 MDE）"
            "「任何差异都想检测」等价于「需要无穷样本」。先想清楚：差 1 个点会改变你的决策吗？"
            "如果不会，就别把它设成 MDE。",
            "<strong>你能接受多大的假阳性率与假阴性率？</strong>"
            "研究场景常用 $\\alpha = 0.05, \\text{power} = 0.8$；"
            "<em>但 CI 门禁场景（C68-04）应该用完全不同的取值</em>——"
            "误报会让整个团队开始忽略告警，所以 $\\alpha$ 要设得很低。",
            "<strong>你的预算是多少？</strong>如果算出来需要 4000 道任务而你只有 500 道，"
            "正确的反应不是「凑合跑」，而是<strong>改变结论的形式</strong>："
            "从「A 比 B 强」改成「在 500 道任务上没有观察到显著差异，检测下限是 8 个点」。",
        ]),
        CALLOUT("danger", "第 3 条值得特别强调，因为它是这门课里最容易被跳过、也最影响诚信的一步。"
                          "<strong>「没有观察到显著差异」和「两者相同」不是一回事</strong>。"
                          "一份负责任的报告必须给出<em>检测下限</em>："
                          "「本次评测能以 80% 的功效检出 ≥8 个百分点的差异；实测差异 3 个点，不显著」——"
                          "这句话既诚实又有信息量，而「A 和 B 差不多」这句话两样都不是。"),
        H3("预算分配的实用结论"),
        TABLE(["场景", "$\\sigma^2_w / \\sigma^2_b$", "任务边际成本", "推荐 $k$", "理由"], [
            ["合成任务集、判分确定性高", "低（0.1–0.3）", "极低", "<strong>1–2</strong>", "把钱全花在扩任务数上"],
            ["公开基准（SWE-bench 类）", "中（0.3–0.6）", "高（任务是别人建好的，但每次跑很贵）", "<strong>3–5</strong>", "常见的 <code>--epochs 5</code> 就是这么来的"],
            ["自建高保真环境（客服/GUI）", "高（0.6–1.0）", "极高（每道题要写环境+判分器）", "<strong>5–10</strong>", "任务贵、噪声大，多跑几次比多写一道题便宜"],
            ["要报 pass^k", "—", "—", "<strong>$n \\ge 2k$</strong>", "无偏估计器需要 $n > k$，实践上取 $n \\ge 2k$ 才够稳"],
        ]),
    ])),

    # ============================================================== 6
    ("winner-curse", "排行榜上的胜者诅咒：为什么第一名的分数总是虚高", "".join([
        P("最后一个统计陷阱，它解释了一个反复出现的现象：<strong>榜单第一名的成绩，"
          "在独立复现时往往会掉几个点。</strong>这不需要任何人作弊就会发生。"),
        DUAL(
            "机制很简单：如果 20 个模型的<em>真实</em>能力都差不多，"
            "那么榜首那个只是<strong>运气最好的那个</strong>——它的观测分数 = 真实能力 + 一个恰好为正的噪声。"
            "换一批任务重跑，噪声重新掷骰子，它就掉下来了。"
            "<strong>「取最大值」这个操作本身就是有偏的。</strong>",
            "形式化：设 $\\hat{\\theta}_i = \\theta_i + \\varepsilon_i$，$\\varepsilon_i \\sim \\mathcal{N}(0, \\sigma^2)$。"
            "则 $\\mathbb{E}[\\max_i \\hat{\\theta}_i] > \\max_i \\theta_i$，"
            "且当所有 $\\theta_i$ 相等时，偏差约为 $\\sigma \\sqrt{2 \\ln m}$（$m$ 为参赛者数量）。"
            "<em>$m = 20$、$\\sigma = 2$ 个点时，榜首的期望虚高约 $2\\sqrt{2\\ln 20} \\approx 4.9$ 个点</em>——"
            "这个量级完全足以解释「排行榜前几名挤在几个点内」的现象，"
            "也解释了为什么复现时会系统性地掉分。",
        ),
        TABLE(["缓解手段", "怎么做", "代价"], [
            ["<strong>报置信区间而不是点估计</strong>", "榜单每一行都带误差棒；重叠的名次视为并列", "榜单不再有唯一的第一名（这是好事）"],
            ["<strong>留出集</strong>", "榜单用公开集排名，最终结论用从未被优化过的留出集复核", "需要额外维护一套任务"],
            ["<strong>收缩估计</strong>", "把各模型的分数向总体均值收缩（James–Stein / 经验贝叶斯）", "单个模型的分数不再是「它自己的成绩」"],
            ["<strong>多重比较校正</strong>", "比较 $m$ 个模型时对 $\\alpha$ 做 Bonferroni/BH 校正", "更保守，可能漏掉真实差异"],
        ]),
        CALLOUT("intuition", "对读榜单的人，一条极其实用的经验法则：<strong>看排名前，先看误差棒宽度和任务数。</strong>"
                             "500 道任务的基准，95% 区间大约是 ±4 个点——"
                             "<em>这意味着榜单上相差 4 个点以内的名次，本质上是并列</em>。"
                             "把它们读成「A 优于 B」是过度解读。"),
    ])),

    # ============================================================== 7
    ("reporting", "报告规范：一行不误导人的结果长什么样", "".join([
        P("把本模块的全部内容压缩成一个可以照抄的模板："),
        CODE("""resolve_rate (pass^1, micro):  34.2%  [30.1%, 38.4%]   N=500 tasks × k=5 attempts
  ├─ 置信区间方法:              按任务聚类自举, 2000 次重采样
  ├─ 有效样本量 n_eff:          658  (ρ=0.70, 名义 2500)
  ├─ pass@5:                    58.1%     ← 有验证器/人复核时才看这个
  ├─ pass^5:                    12.7%     ← 直接执行、无复核时看这个
  └─ 最小可检测差异 (MDE):      8.1 个百分点 (α=0.05, power=0.8, 配对设计)

vs baseline (配对):             +3.1 个百分点  [-1.2, +7.5]   McNemar p = 0.14
  └─ 结论: 未观察到显著差异；本次评测的检测下限是 8.1 个点，
           实测差异 3.1 点落在检测能力之下——**不能得出「A 更强」的结论**。"""),
        UL([
            "<strong>指标名要写全</strong>：<code>pass^1</code> 而不是「成功率」，"
            "<code>micro</code> 而不是「平均」——模块 02 已经证明了这些词各自对应不同的数字。",
            "<strong>$N$ 和 $k$ 必须分开写</strong>：写成「2500 次运行」是在误导读者，"
            "因为它们不是 2500 个独立样本。",
            "<strong>MDE 必须出现</strong>：没有 MDE 的「不显著」是没有信息量的。",
            "<strong>置信区间的计算方法必须写明</strong>：朴素自举和聚类自举给出的区间可以差一倍。",
        ]),
        CALLOUT("warn", "最后一条容易被忽略的提醒：<strong>本模块所有的统计工具，"
                        "都建立在「判分器是准确的」这个前提上。</strong>"
                        "如果判分器有 5% 的假阳率（模块 02），那么再漂亮的置信区间也只是"
                        "「对一个有偏的量的精确估计」。<em>顺序永远是：先量 bias，再压 var，最后写区间。</em>"),
    ])),
    # ============================================================== 8
    ("sequential", "序贯评测：跑到一半能不能停", "".join([
        P("agentic 评测很贵，所以一个很自然的想法是：<strong>边跑边看，差距明显了就提前停。</strong>"
          "这个想法是对的，但<em>朴素地执行会让假阳性率暴涨</em>——它是评测里最常见的统计错误之一。"),
        H3("为什么「边跑边看」会作弊"),
        P("如果你每跑 50 道题就看一次 $p$ 值，一旦 $p &lt; 0.05$ 就停下来宣布显著，"
          "那么即使两个 agent 完全相同，你也<strong>迟早会碰到一次 $p &lt; 0.05$</strong>。"
          "检查 10 次的话，实际假阳性率会从 5% 涨到 20% 以上——"
          "这叫<span class=\"term\">窥视问题</span>（peeking / optional stopping）。"),
        CALLOUT("danger", "这个错误在 agent 评测里特别容易犯，因为评测是<strong>逐任务流式产出结果</strong>的，"
                          "人天然会在跑的过程中盯着看。<strong>「跑到 300 题的时候看起来 A 明显更好，"
                          "我们就停了」——这句话描述的是一次无效的实验。</strong>"),
        H3("三种正确做法"),
        TABLE(["方法", "怎么做", "适用场景", "代价"], [
            ["<strong>固定样本量</strong>", "事先按 MDE 算出 $N$，跑完再看", "最简单、最不容易出错，<strong>默认选它</strong>", "不能提前停，跑满才有结论"],
            ["<strong>alpha spending</strong>", "把总的 $\\alpha=0.05$ 按检查次数分配（如 O'Brien–Fleming 边界：早期极严、后期放宽）", "评测很贵、希望有机会早停", "需要事先声明检查时点与边界"],
            ["<strong>始终有效的推断</strong>", "用序贯置信序列（anytime-valid CI），它在任何时刻都成立", "持续监控型评测（C68 的线上门禁）", "区间比固定样本量的宽（这是随时可看的代价）"],
        ]),
        P("三者的共同点是：<strong>「什么时候可以停」这件事必须在开始之前就定好</strong>，"
          "而不是看着数据决定。这一条纪律，和模块 05 的「harness 要事先钉死」是同一种性质的要求——"
          "<em>都是在防止一个自由度被事后利用</em>。"),
        DUAL(
            "反过来说，有一种「提前停」是完全合法的，而且应该多用："
            "<strong>停掉那些明显没救的单条轨迹</strong>（模块 03 的循环检测）。"
            "这不是统计上的提前停止——它不改变任务的判定结果，只是省下了本来也要浪费的预算，"
            "然后把这些预算投到别的任务上。<strong>省下的钱直接变成更大的 $N$，这是纯赚。</strong>",
            "区别在于停止规则作用的层级：<span class=\"term\">序贯检验</span>的停止规则作用在"
            "<em>推断</em>层面（决定何时下结论），因此会影响第一类错误率；"
            "循环检测的停止规则作用在<em>单个样本的生成过程</em>上，"
            "只要它<strong>与该样本的最终标签独立</strong>（检出循环的轨迹本来就会失败），"
            "就不引入偏倚。<em>但这个「独立」必须被验证</em>——"
            "如果你的循环检测器偶尔会误杀本来能成功的轨迹，它就变成了一个有偏的截断，"
            "此时被终止的轨迹必须单独统计而不能简单记成失败。",
        ),
    ])),
]

NB = [
    md("""# 04 · 可靠性与统计（方差分解 / pass@k 与 pass^k / 预算分配 / 聚类自举 / 配对检验 / 胜者诅咒）

目标：把「跑几次够不够」「差 3 个点算不算差」这些每天都要回答的问题，变成**可以算的数**。

本 notebook 你会亲手实现：
1. **方差分解** —— 把总方差拆成任务间与任务内，看清楚钱该花在 N 还是 k 上
2. **pass@k 与 pass^k 的无偏估计器** —— 组合数公式，以及为什么不能"跑 k 次数一数"
3. **预算最优分配** —— 给定预算，解出最优的 (任务数 N, 重复数 k)
4. **聚类自举 vs 朴素自举** —— 用覆盖率实验证明朴素自举的区间窄了近一半
5. **McNemar 与配对自举** —— 同一批任务上比较两个 agent
6. **胜者诅咒模拟** —— 20 个能力完全相同的模型，榜首会虚高多少

> 心智模型：**先量 bias（判分器），再压 var（多跑），最后写区间（聚类自举）。
> 顺序反了，你会得到一个对错误的量的精确估计。**"""),

    md("""## 1 · 方差分解：任务间 vs 任务内"""),

    code("""import math, itertools
from collections import defaultdict
import numpy as np

def simulate_runs(N, k, mu=0.4, sd_task=0.35, seed=0):
    \"\"\"生成 N 个任务 × k 次重复的 0/1 结果。
    每个任务有自己的成功率 p_i ~ Beta(由 mu, sd_task 反推)，任务内是伯努利采样。\"\"\"
    rng = np.random.default_rng(seed)
    # 由均值与标准差反推 Beta 参数
    v = sd_task ** 2
    common = mu * (1 - mu) / v - 1
    a, b = max(mu * common, 0.05), max((1 - mu) * common, 0.05)
    p = rng.beta(a, b, size=N)
    X = (rng.random((N, k)) < p[:, None]).astype(float)
    return X, p

X, p_true = simulate_runs(N=400, k=8, seed=1)
task_means = X.mean(axis=1)
grand = X.mean()

# 方差分解：between = 任务真实难度的方差；within = 同一任务重复之间的方差
var_between = float(np.var(p_true, ddof=1))
var_within = float(np.mean(p_true * (1 - p_true)))
print(f'总体成功率        {grand:.3f}')
print(f'任务间方差 σ²_b   {var_between:.4f}')
print(f'任务内方差 σ²_w   {var_within:.4f}')
print(f'σ²_w / σ²_b       {var_within/var_between:.2f}')

rho = var_between / (var_between + var_within)          # 组内相关系数
print(f'组内相关 ρ        {rho:.3f}')
assert 0 < rho < 1
print('\\n✅ ρ 就是「同一任务的两次重复有多像」。ρ 越高，重复的边际价值越低。')"""),

    code("""def var_of_mean(N, k, var_b, var_w):
    return var_b / N + var_w / (N * k)

print(f"{'k':>4}{'Var(mean)':>14}{'标准差':>12}{'相对 k=1 的降幅':>18}")
base = var_of_mean(400, 1, var_between, var_within)
for k in [1, 2, 5, 10, 50, 1000]:
    v = var_of_mean(400, k, var_between, var_within)
    print(f'{k:>4}{v:>14.6f}{math.sqrt(v):>12.4f}{1 - math.sqrt(v/base):>17.1%}')

floor = var_between / 400
print(f'\\nk → ∞ 的方差下限: {floor:.6f}（标准差 {math.sqrt(floor):.4f}）')
assert var_of_mean(400, 1000, var_between, var_within) > floor
print('✅ 无论跑多少次重复，方差都降不到任务间方差以下——')
print('   而把 N 翻倍，两项一起减半。这就是「先扩任务集，再加重复」的定量依据。')"""),

    md("""## 2 · pass@k 与 pass^k 的无偏估计

给定同一任务跑了 $n$ 次、成功 $c$ 次：

$$\\text{pass@}k = 1 - \\frac{\\binom{n-c}{k}}{\\binom{n}{k}}, \\qquad
\\text{pass}^k = \\frac{\\binom{c}{k}}{\\binom{n}{k}}$$"""),

    code("""def pass_at_k(n, c, k):
    \"\"\"n 次采样中成功 c 次，随机抽 k 次「至少一次成功」的概率（无偏）。\"\"\"
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)

def pass_pow_k(n, c, k):
    \"\"\"随机抽 k 次「全部成功」的概率（无偏）。\"\"\"
    if c < k:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)

n = 20
print(f"{'c/n':>8}{'p̂':>8}", end='')
for k in [1, 2, 3, 5, 8]:
    print(f'{"@"+str(k):>9}', end='')
for k in [1, 2, 3, 5, 8]:
    print(f'{"^"+str(k):>9}', end='')
print()
for c in [4, 10, 14, 18, 20]:
    print(f'{c:>3}/{n:<4}{c/n:>8.2f}', end='')
    for k in [1, 2, 3, 5, 8]:
        print(f'{pass_at_k(n, c, k):>9.3f}', end='')
    for k in [1, 2, 3, 5, 8]:
        print(f'{pass_pow_k(n, c, k):>9.3f}', end='')
    print()

assert abs(pass_at_k(20, 14, 1) - 0.7) < 1e-12
assert abs(pass_pow_k(20, 14, 1) - 0.7) < 1e-12
assert pass_at_k(20, 14, 8) > 0.99 and pass_pow_k(20, 14, 8) < 0.06
print('\\n✅ 看 c=14 那一行：pass@8 是 99.9%（"接近完美"），pass^8 是 5.7%（"基本不可用"）。')
print('   同一个 agent，两个数字都没撒谎——判断标准只有一条：结果被执行前有没有人挑一挑。')"""),

    code("""# 为什么要用无偏估计器：跟「跑 k 次数一数」比方差
def naive_pass_pow_k(p, k, n_trials, rng):
    \"\"\"朴素做法：直接跑 k 次看是否全对，重复 n_trials 次取平均。\"\"\"
    return float(np.mean([(rng.random(k) < p).all() for _ in range(n_trials)]))

rng = np.random.default_rng(7)
P_TRUE, K, N_SAMPLES = 0.7, 3, 20
truth = P_TRUE ** K

naive_est, unbiased_est = [], []
for _ in range(2000):
    draws = rng.random(N_SAMPLES) < P_TRUE
    c = int(draws.sum())
    unbiased_est.append(pass_pow_k(N_SAMPLES, c, K))
    # 朴素：只用前 K 次采样，看是否全对；再用剩下的样本重复几组
    groups = N_SAMPLES // K
    naive_est.append(float(np.mean([draws[g*K:(g+1)*K].all() for g in range(groups)])))

print(f'真值 pass^{K} = {truth:.4f}')
print(f'无偏估计器  均值 {np.mean(unbiased_est):.4f}  标准差 {np.std(unbiased_est):.4f}')
print(f'朴素分组法  均值 {np.mean(naive_est):.4f}  标准差 {np.std(naive_est):.4f}')
assert abs(np.mean(unbiased_est) - truth) < 0.02
assert np.std(unbiased_est) < np.std(naive_est)
print('\\n✅ 两者都无偏，但无偏估计器的方差明显更小——')
print('   因为它用上了「从 n 次里抽 k 次」的全部组合信息，而不是把样本切成互不重叠的几组。')"""),

    md("""## 3 · 预算最优分配：N 和 k 该怎么切

在预算 $B = N(c_{task} + k \\cdot c_{run})$ 下最小化 $\\frac{\\sigma_b^2}{N} + \\frac{\\sigma_w^2}{Nk}$。
理论解 $k^* = \\sqrt{\\frac{\\sigma_w^2}{\\sigma_b^2}\\cdot\\frac{c_{task}}{c_{run}}}$，下面用网格搜索验证。"""),

    code("""def optimal_k(var_b, var_w, c_task, c_run, budget, k_max=40):
    \"\"\"网格搜索最优 (N, k)。N 由预算与 k 决定：N = budget / (c_task + k*c_run)。\"\"\"
    best = None
    for k in range(1, k_max + 1):
        N = budget / (c_task + k * c_run)
        if N < 20:                       # 任务数太少，估计不可靠，直接排除
            continue
        v = var_b / N + var_w / (N * k)
        if best is None or v < best[2]:
            best = (int(N), k, v)
    return best

def theoretical_k(var_b, var_w, c_task, c_run):
    return math.sqrt((var_w / var_b) * (c_task / c_run))

SCENARIOS = [
    ('合成任务集（任务几乎免费）', 0.05, 0.20, 1.0, 1.0),
    ('公开基准（任务贵、跑一次也贵）', 0.05, 0.20, 20.0, 1.0),
    ('自建高保真环境（任务极贵）', 0.05, 0.20, 200.0, 1.0),
]
BUDGET = 20000
print(f"{'场景':<32}{'最优 N':>8}{'最优 k':>8}{'理论 k*':>10}")
for name, vb, vw, ct, cr in SCENARIOS:
    N_opt, k_opt, v = optimal_k(vb, vw, ct, cr, BUDGET)
    print(f'{name:<32}{N_opt:>8}{k_opt:>8}{theoretical_k(vb, vw, ct, cr):>10.1f}')

_, k_cheap, _ = optimal_k(0.05, 0.20, 1.0, 1.0, BUDGET)
_, k_expensive, _ = optimal_k(0.05, 0.20, 200.0, 1.0, BUDGET)
assert k_expensive > k_cheap
print('\\n✅ 任务越贵，最优重复次数越高——因为「多跑一次」相对「多写一道题」变便宜了。')
print('   这解释了为什么 SWE-bench 类基准常见 --epochs 5，而合成任务集应该直接扩任务数。')"""),

    md("""## 4 · 聚类自举 vs 朴素自举：覆盖率实验

构造一个已知真值的场景，两种自举各算 95% 区间，统计真值落在区间内的比例。
名义覆盖率应当是 95%——朴素自举会显著低于它。"""),

    code("""def naive_bootstrap_ci(X, n_boot=400, seed=0):
    \"\"\"错误做法：把 N*k 条 rollout 当独立样本重采样。\"\"\"
    rng = np.random.default_rng(seed)
    flat = X.ravel()
    n = flat.size
    boots = [flat[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    return np.percentile(boots, [2.5, 97.5])

def clustered_bootstrap_ci(X, n_boot=400, seed=0):
    \"\"\"正确做法：重采样「任务」，被抽中的任务连同它全部 k 次重复一起进来。\"\"\"
    rng = np.random.default_rng(seed)
    N = X.shape[0]
    boots = [X[rng.integers(0, N, N)].mean() for _ in range(n_boot)]
    return np.percentile(boots, [2.5, 97.5])

def coverage_experiment(n_rep=120, N=150, k=6, mu=0.4, sd_task=0.35):
    hit_naive = hit_clust = 0
    w_naive, w_clust = [], []
    for r in range(n_rep):
        X, p = simulate_runs(N, k, mu=mu, sd_task=sd_task, seed=1000 + r)
        truth = mu                                 # 推断目标：这类任务上的总体成功率
        lo1, hi1 = naive_bootstrap_ci(X, n_boot=300, seed=r)
        lo2, hi2 = clustered_bootstrap_ci(X, n_boot=300, seed=r)
        hit_naive += (lo1 <= truth <= hi1)
        hit_clust += (lo2 <= truth <= hi2)
        w_naive.append(hi1 - lo1)
        w_clust.append(hi2 - lo2)
    return (hit_naive / n_rep, hit_clust / n_rep, np.mean(w_naive), np.mean(w_clust))

cn, cc, wn, wc = coverage_experiment()
print(f'名义覆盖率 95%')
print(f'  朴素自举  实际覆盖 {cn:.1%}   平均区间宽度 {wn:.4f}')
print(f'  聚类自举  实际覆盖 {cc:.1%}   平均区间宽度 {wc:.4f}')
print(f'  区间宽度比: 聚类 / 朴素 = {wc/wn:.2f}x')
assert cc > cn, '聚类自举的覆盖率应当更接近名义值'
assert wc > wn, '聚类自举的区间必然更宽'
print('\\n✅ 朴素自举的区间窄了一大截，覆盖率因此低于名义的 95%——')
print('   这就是评测报告里「误差棒画得太窄」的直接来源。')"""),

    code("""# 有效样本量：n_eff = Nk / (1 + (k-1)ρ)
def n_eff(N, k, rho):
    return N * k / (1 + (k - 1) * rho)

print(f"{'ρ':>6}{'名义 Nk':>10}{'n_eff':>10}{'占比':>8}")
for rho_ in [0.0, 0.3, 0.5, 0.7, 0.9]:
    ne = n_eff(500, 5, rho_)
    print(f'{rho_:>6.1f}{2500:>10}{ne:>10.0f}{ne/2500:>8.0%}')

assert abs(n_eff(500, 5, 0.0) - 2500) < 1e-9
assert n_eff(500, 5, 1.0) == 500
print('\\n✅ ρ=0 时 n_eff = Nk（重复完全独立）；ρ=1 时 n_eff = N（重复毫无新信息）。')
print('   agent 评测的 ρ 通常在 0.5-0.8，所以名义样本量要打三折左右看。')"""),

    md("""## 5 · 配对检验：McNemar 与配对自举"""),

    code("""def mcnemar(x, y, continuity=True):
    \"\"\"x, y: 同一批任务上两个 agent 的 0/1 结果。返回 (b, c, chi2, p 近似)。
    b = x 对 y 错的任务数; c = x 错 y 对的任务数。一致对不携带信息。\"\"\"
    x, y = np.asarray(x, dtype=bool), np.asarray(y, dtype=bool)
    b = int((x & ~y).sum())
    c = int((~x & y).sum())
    if b + c == 0:
        return b, c, 0.0, 1.0
    num = abs(b - c) - (1 if continuity else 0)
    chi2 = max(num, 0) ** 2 / (b + c)
    # 卡方(1) 的上尾概率：p = erfc(sqrt(chi2/2))
    p = math.erfc(math.sqrt(chi2 / 2))
    return b, c, chi2, p

def paired_bootstrap(x, y, n_boot=4000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    n = len(d)
    boots = [d[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    return float(d.mean()), tuple(np.percentile(boots, [2.5, 97.5]))

rng = np.random.default_rng(5)
N = 500
task_diff = rng.beta(2, 3, size=N)                 # 任务难度（两个 agent 共享）
A = (rng.random(N) < task_diff + 0.03).astype(int)  # A 真实略强 3 个点
B = (rng.random(N) < task_diff).astype(int)

b, c, chi2, p = mcnemar(A, B)
diff, (lo, hi) = paired_bootstrap(A, B, seed=2)
print(f'A 成功率 {A.mean():.1%} | B 成功率 {B.mean():.1%}')
print(f'不一致对: b={b} (A对B错), c={c} (A错B对) | 一致对 {N-b-c} 条完全不携带信息')
print(f'McNemar chi2={chi2:.2f}, p={p:.3f}')
print(f'配对自举: 差值 {diff:+.1%}  95% CI [{lo:+.1%}, {hi:+.1%}]')
assert b + c < N, '一致对占了大多数——这正是配对设计省样本的原因'
print(f'\\n✅ {N} 道任务里只有 {b+c} 条携带信息（{(b+c)/N:.0%}）。')
print('   配对设计的全部威力，就是把「估计两个绝对值」变成「只看不一致对」。')"""),

    code("""# 独立设计 vs 配对设计的样本量对比
def required_n_independent(p1, p2, alpha=0.05, power=0.8):
    z_a, z_b = 1.959963985, 0.8416212336
    pb = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pb * (1 - pb)) + z_b * math.sqrt(p1*(1-p1) + p2*(1-p2))) ** 2
    return math.ceil(num / (p1 - p2) ** 2)

def required_n_paired(p_disc, delta, alpha=0.05, power=0.8):
    z_a, z_b = 1.959963985, 0.8416212336
    return math.ceil(((z_a + z_b) ** 2 * p_disc) / (delta ** 2))

p_disc = (b + c) / N
print(f"{'要检出的差异':>14}{'独立设计':>12}{'配对设计':>12}{'节省':>10}")
for delta in [0.10, 0.05, 0.03]:
    ni = required_n_independent(0.40, 0.40 + delta)
    npd = required_n_paired(p_disc, delta)
    print(f'{delta:>14.0%}{ni:>12,}{npd:>12,}{ni/npd:>9.1f}x')

mde_paired = math.sqrt(((1.959963985 + 0.8416212336) ** 2 * p_disc) / N)
print(f'\\n本次评测（N={N}, 不一致率 {p_disc:.0%}）的最小可检测差异 MDE = {mde_paired:.1%}')
assert mde_paired > 0
print(f'实测差异 {diff:+.1%} —— 是否超过 MDE: {abs(diff) > mde_paired}')
print('✅ 这一行就是报告里必须写的那句话：「本次评测能检出 ≥X 个点的差异」。')
print('   没有它，「不显著」这三个字没有任何信息量。')"""),

    md("""## 6 · 胜者诅咒：20 个能力完全相同的模型，榜首虚高多少"""),

    code("""def winner_curse(m_models=20, N=500, true_p=0.40, n_rep=2000, seed=0):
    \"\"\"所有模型真实能力完全相同，看观测榜首的平均分数与真值的差距。\"\"\"
    rng = np.random.default_rng(seed)
    gaps, reversal = [], 0
    for _ in range(n_rep):
        obs = rng.binomial(N, true_p, size=m_models) / N
        winner = int(np.argmax(obs))
        gaps.append(obs.max() - true_p)
        # 复现实验：换一批任务重跑，原榜首还是第一吗
        obs2 = rng.binomial(N, true_p, size=m_models) / N
        reversal += (int(np.argmax(obs2)) != winner)
    return float(np.mean(gaps)), reversal / n_rep

sigma = math.sqrt(0.40 * 0.60 / 500)
for m in [2, 5, 20, 100]:
    gap, rev = winner_curse(m_models=m)
    theory = sigma * math.sqrt(2 * math.log(m)) if m > 1 else 0.0
    print(f'm={m:>4} 模型 | 榜首平均虚高 {gap:+.2%} (理论 ≈ {theory:+.2%}) | 复现时榜首易主 {rev:.0%}')

gap20, rev20 = winner_curse(m_models=20)
gap2, _ = winner_curse(m_models=2)
assert gap20 > gap2, '参赛者越多，榜首虚高越严重'
assert rev20 > 0.8, '能力相同时，复现实验的榜首几乎必然易主'
print(f'\\n✅ 20 个能力完全相同的模型，榜首平均虚高 {gap20:.1%}，')
print(f'   而且复现时有 {rev20:.0%} 的概率换人当第一——没有任何人作弊。')
print('   读榜单的经验法则：500 道任务的基准，相差 4 个点以内的名次本质上是并列。')"""),

    md("""## ✏️ 练习 1：pass^k 的一致性缺口

实现 `consistency_gap(n, c, k)`：返回 `pass_pow_k(n,c,1) - pass_pow_k(n,c,k)`，
即「能力」与「可靠性」的分离量。行为完全确定的 agent 这个值应为 0。"""),

    code("""def consistency_gap(n, c, k):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(consistency_gap(20, 20, 5)) < 1e-12      # 20/20 全对 → 完全确定 → 缺口 0
assert abs(consistency_gap(20, 0, 5)) < 1e-12       # 0/20 全错 → 也完全确定 → 缺口 0
g = consistency_gap(20, 10, 5)
assert g > 0.4                                       # 一半一半 → 最不稳定
for c in [2, 6, 10, 14, 18]:
    print(f'c={c:>3}/20  pass^1={pass_pow_k(20,c,1):.2f}  pass^5={pass_pow_k(20,c,5):.3f}  '
          f'缺口={consistency_gap(20,c,5):.3f}')
print('✅ 练习 1 通过：缺口在 c/n≈0.5 附近最大——')
print('   能力决定 pass^k 曲线的起点，一致性决定它下降的斜率。')"""),

    md("""## ✏️ 练习 2：给定预算求最小可检测差异

实现 `mde_paired(N, p_discordant, alpha=0.05, power=0.8)`：
由 `required_n_paired` 的公式反解，返回在 N 道任务上能检出的最小差异
$\\delta = \\sqrt{\\frac{(z_\\alpha + z_\\beta)^2 p_{disc}}{N}}$。"""),

    code("""def mde_paired(N, p_discordant, alpha=0.05, power=0.8):
    # TODO（alpha/power 固定用 z_a=1.959963985, z_b=0.8416212336）
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
m1 = mde_paired(500, 0.20)
assert required_n_paired(0.20, m1) <= 501            # 反解自洽
assert mde_paired(2000, 0.20) < m1                   # 任务多 → 能检出更小的差异
assert mde_paired(500, 0.40) > m1                    # 不一致率高 → 噪声大 → MDE 变大
for N_ in [200, 500, 1000, 4000]:
    print(f'N={N_:>5}  不一致率20%  MDE = {mde_paired(N_, 0.20):.2%}')
print('✅ 练习 2 通过：这一行数字应当在你决定「跑多少」之前就算出来——')
print('   而不是等实验跑完发现「不显著」再回头算。')"""),

    md("""## ✏️ 练习 3：有效样本量与「该不该再加重复」

实现 `marginal_value_of_k(N, k, rho)`：返回把重复数从 `k` 加到 `k+1` 带来的
有效样本量增量占比，即 `(n_eff(N,k+1,rho) - n_eff(N,k,rho)) / n_eff(N,k,rho)`。"""),

    code("""def marginal_value_of_k(N, k, rho):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
v1 = marginal_value_of_k(500, 1, 0.7)
v5 = marginal_value_of_k(500, 5, 0.7)
assert v1 > v5 > 0, '边际收益必须递减且为正'
assert marginal_value_of_k(500, 1, 0.0) > marginal_value_of_k(500, 1, 0.9)
print(f"{'k→k+1':>8}{'ρ=0.3':>10}{'ρ=0.7':>10}{'ρ=0.9':>10}")
for k in [1, 2, 5, 10]:
    print(f'{f"{k}→{k+1}":>8}', end='')
    for r in [0.3, 0.7, 0.9]:
        print(f'{marginal_value_of_k(500, k, r):>10.1%}', end='')
    print()
print('✅ 练习 3 通过：ρ=0.7 时从 5 次加到 6 次只买到几个百分点的有效样本量——')
print('   这个数字就是「该停手了」的信号。')"""),

    md("""## ✏️ 练习 4：把报告模板写成代码

实现 `eval_report(X, X_base=None, rho=None)`：输入 N×k 的 0/1 结果矩阵，
返回一个字典，含 `pass1`、`ci`（聚类自举 95% 区间）、`n_eff`、
`pass_at_k`、`pass_pow_k`（都取 k = 矩阵的列数）、以及在给了 `X_base` 时的
`paired_diff` 与 `mde`。ρ 未给时用 `var_between/(var_between+var_within)` 从数据估计。"""),

    code("""def eval_report(X, X_base=None, rho=None):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
Xa, _ = simulate_runs(N=300, k=5, mu=0.42, seed=11)
Xb, _ = simulate_runs(N=300, k=5, mu=0.38, seed=12)
rep = eval_report(Xa, Xb)
need = {'pass1', 'ci', 'n_eff', 'pass_at_k', 'pass_pow_k', 'paired_diff', 'mde'}
assert need <= set(rep)
assert rep['ci'][0] <= rep['pass1'] <= rep['ci'][1]
assert rep['n_eff'] <= 300 * 5
assert rep['pass_at_k'] >= rep['pass1'] >= rep['pass_pow_k']
for k_, v in rep.items():
    print(f'  {k_:<14} {v}')
print('\\n✅ 练习 4 通过：这个字典直接对应讲解第 7 节的报告模板——')
print('   把它接进你的评测流水线，报告就再也不会漏掉 n_eff 和 MDE 这两行。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def consistency_gap(n, c, k):
    return pass_pow_k(n, c, 1) - pass_pow_k(n, c, k)"""),

    code("""# 练习 2 参考答案
def mde_paired(N, p_discordant, alpha=0.05, power=0.8):
    z_a, z_b = 1.959963985, 0.8416212336
    return math.sqrt(((z_a + z_b) ** 2 * p_discordant) / N)"""),

    code("""# 练习 3 参考答案
def marginal_value_of_k(N, k, rho):
    a = n_eff(N, k, rho)
    b = n_eff(N, k + 1, rho)
    return (b - a) / a"""),

    code("""# 练习 4 参考答案
def eval_report(X, X_base=None, rho=None):
    X = np.asarray(X, dtype=float)
    N, k = X.shape
    task_means = X.mean(axis=1)
    if rho is None:
        vb = float(np.var(task_means, ddof=1))
        vw = float(np.mean(task_means * (1 - task_means)))
        rho = vb / (vb + vw) if (vb + vw) > 0 else 0.0
    lo, hi = clustered_bootstrap_ci(X, seed=0)
    c_total = int(X.sum())
    out = {
        'pass1': round(float(X.mean()), 4),
        'ci': (round(float(lo), 4), round(float(hi), 4)),
        'n_eff': round(n_eff(N, k, rho), 1),
        'pass_at_k': round(float(np.mean([pass_at_k(k, int(r.sum()), k) for r in X])), 4),
        'pass_pow_k': round(float(np.mean([pass_pow_k(k, int(r.sum()), k) for r in X])), 4),
    }
    if X_base is not None:
        B = np.asarray(X_base, dtype=float)
        a1 = (X.mean(axis=1) > 0.5).astype(int)
        b1 = (B.mean(axis=1) > 0.5).astype(int)
        bb, cc_, _, _ = mcnemar(a1, b1)
        p_disc = (bb + cc_) / len(a1)
        out['paired_diff'] = round(float(X.mean() - B.mean()), 4)
        out['mde'] = round(mde_paired(len(a1), max(p_disc, 1e-6)), 4)
    return out"""),

    md("""---
## 🧪 真实工程胶囊：把统计接进评测流水线"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 跑评测时必须落盘的三个字段（否则统计全做不了）
# ══════════════════════════════════════════════════════════════════
# task_id, attempt, score  —— 三列就够了，其余都能从它们算出来
# inspect-ai: --epochs 5 会自动为每个样本产出 5 条带 epoch 编号的记录
#   inspect eval mytask.py --model anthropic/claude-sonnet-5 --epochs 5
#   inspect view    # 结果里每条 sample 都有 epoch 字段 = 我们的 attempt

# ══════════════════════════════════════════════════════════════════
# B. 从结果文件到报告的一段脚本（照抄改路径即可）
# ══════════════════════════════════════════════════════════════════
import pandas as pd, numpy as np
df = pd.read_json("results.jsonl", lines=True)          # task_id, attempt, score
piv = df.pivot_table(index="task_id", columns="attempt", values="score")
X = piv.to_numpy()                                       # N × k 矩阵，正是本 notebook 的输入
rep = eval_report(X)
print(rep)

# ══════════════════════════════════════════════════════════════════
# C. 两个模型对比：必须同一次运行、同一 harness、同一任务集
# ══════════════════════════════════════════════════════════════════
# 错误做法：上周跑 A，这周跑 B（中间镜像更新过 → 不是配对设计）
# 正确做法：
#   for model in [A, B]:
#       run_eval(model, tasks=TASKS_V12, harness="harness@1.7.2", epochs=5, seed=0)
#   然后用 mcnemar(a_scores, b_scores) + paired_bootstrap 出结论

# ══════════════════════════════════════════════════════════════════
# D. 报告里必须有的六行（缺一行就会被误读）
# ══════════════════════════════════════════════════════════════════
# 1. 指标全名        pass^1 (micro)，不是"成功率"
# 2. N 和 k 分开写   N=500 tasks × k=5 attempts，不是"2500 次运行"
# 3. 区间与方法      [30.1%, 38.4%] 按任务聚类自举, 2000 次
# 4. n_eff 与 ρ      658 (ρ=0.70)
# 5. MDE             8.1 个百分点 (α=0.05, power=0.8, 配对)
# 6. harness 指纹    harness@1.7.2, image sha256:..., concurrency=8
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 四个方差源 | 任务间 / 任务内可用统计处理；模拟器与 harness 必须用工程消除 | 设计实验 |
| $k$ 有天花板，$N$ 没有 | 重复只能把方差压到 $\\sigma_b^2/N$；先扩任务集再加重复 | 预算分配 |
| pass@k vs pass^k | 结果被执行前有没有人挑一挑，决定用哪个 | 选指标 |
| 配对设计 | 只有不一致对携带信息，样本量省一半以上 | 模型对比 |
| 聚类自举 | 独立单位是任务不是 rollout；朴素自举区间窄近一半 | 算区间 |
| MDE | 「不显著」必须配着检测下限一起报 | 写结论 |
| 胜者诅咒 | 20 个同水平模型，榜首虚高约 5 个点且复现必易主 | 读榜单 |

下一模块：**05 · 成本感知评测与 harness 可复现性**——
把「谁更强」这个问题改写成「给定预算谁更强」，并把 harness 钉死到可以被别人复现。""")
]
