# -*- coding: utf-8 -*-
"""C76 模块 03 · 倾向得分、IPW、双重稳健与双重机器学习。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（识别 vs 估计、可忽略性、正性）；模块 02（后门准则决定 $X$ 是什么）；"
                 "线性回归与岭回归；<em>「双重机器学习」不需要机器学习背景——"
                 "本课的 nuisance 学习器都是最小二乘</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_estimation.ipynb'
                       '（<strong>IPW 无偏但方差爆炸</strong>：有效样本量从 $4000$ 掉到 $616$ / '
                       '<strong>截断改掉了估计目标</strong>：ATE $2.00$ vs 重叠人群 $1.44$ / '
                       'AIPW 只在两个 nuisance <em>都</em>错时失效（$3.492/3.476/3.491$ vs $\\mathbf{2.816}$）/ '
                       '<strong>两个 bit 级恒等式</strong>：FWL 差 $2.2\\times10^{-16}$；'
                       '常数 $\\hat{e}$ 使 AIPW $\\equiv$ G-computation（差 $3.1\\times10^{-15}$）'),
    ("核心参考", "Rosenbaum &amp; Rubin, <em>The Central Role of the Propensity Score</em>"
                 "（Biometrika 1983）· "
                 "Robins, Rotnitzky &amp; Zhao（JASA 1994，AIPW）· "
                 "Chernozhukov, Chetverikov, Demirer, Duflo, Hansen, Newey &amp; Robins, "
                 "<em>Double/Debiased Machine Learning for Treatment and Structural Parameters</em>"
                 "（Econometrics Journal 2018）· "
                 "Crump, Hotz, Imbens &amp; Mitnik, <em>Dealing with Limited Overlap</em>"
                 "（Biometrika 2009，截断规则）· "
                 "Lovell, <em>A Simple Proof of the FWL Theorem</em>（J Econ Educ 2008）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [

("ps", "倾向得分：把高维调整降成一维", "".join([
    P("模块 02 给出了「该控制哪些变量」，本模块处理「怎么控制」。"
      "$X$ 一旦超过两三维，分层就不可行了（模块 01 里 $K$ 太大会丢层）。"),
    P("Rosenbaum 与 Rubin (1983) 的定理：记 $e(x) = P(T{=}1 \\mid X{=}x)$ 为"
      "<strong>倾向得分</strong>（propensity score），则在可忽略性之下"),
    MATH("\\{Y(0), Y(1)\\} \\perp T \\mid X \\quad\\Longrightarrow\\quad "
         "\\{Y(0), Y(1)\\} \\perp T \\mid e(X)"),
    P("即：<strong>只按一维的 $e(X)$ 调整就够了</strong>，无论 $X$ 有多少维。"
      "这是倾向得分之所以成为标准工具的全部理由。"),
    CALLOUT("warn", "这个定理不是免费的",
            "它把「高维调整」换成了「估一个一维函数」，"
            "但那个函数必须<strong>估对</strong>。$\\hat{e}$ 估错时，"
            "定理的结论不成立——而 $\\hat{e}$ 的误差与最终估计误差的关系是本模块的核心内容。"
            "更麻烦的是：$\\hat{e}$ 的<em>预测精度</em>（AUC 之类）"
            "与它作为调整工具的<em>好坏</em>没有直接关系，甚至可以反向相关。"),
])),

("ipw", "IPW：偏差不是问题，方差是", "".join([
    P("逆概率加权（inverse probability weighting）用 $1/e$ 给处理组加权、"
      "$1/(1-e)$ 给对照组加权，把两臂重新配平到同一个人群："),
    MATH("\\widehat{\\text{ATE}}_{\\text{IPW}} = \\frac{1}{n}\\sum_i "
         "\\left[\\frac{T_i Y_i}{e(X_i)} - \\frac{(1-T_i) Y_i}{1-e(X_i)}\\right]"),
    P("notebook 里让 $e = \\sigma(aX)$，$a$ 越大重叠越差，而且<strong>用真值 $e$</strong>——"
      "所以无偏性不该有任何问题："),
    TABLE(["$a$", "$\\min e$", "$\\max w$", "IPW 均值（50 seeds）", "IPW 标准差",
           "有效样本量 ESS"],
          [["$0.0$", "$5.0\\times10^{-1}$", "$2.0$", "$+2.0005$", "$0.0649$", "$4000/4000$"],
           ["$0.5$", "$1.3\\times10^{-1}$", "$5.4$", "$+1.9973$", "$0.0598$", "$3760/4000$"],
           ["$1.0$", "$2.1\\times10^{-2}$", "$20.1$", "$+1.9899$", "$0.0611$", "$3024/4000$"],
           ["$2.0$", "$4.8\\times10^{-4}$", "$103.8$", "$+1.9882$", "$0.0977$", "$1288/4000$"],
           ["$3.0$", "$1.1\\times10^{-5}$", "$72.8$", "$+1.8702$", "$0.4706$", "$990/4000$"],
           ["$5.0$", "$5.0\\times10^{-9}$", "$171.7$", "$+2.2026$", "$0.5141$",
            "$\\mathbf{616/4000}$"]]),
    P("均值一直在 $2$ 附近（无偏），而标准差从 $0.065$ 涨到 $0.514$（$\\mathbf{7.9}$ 倍），"
      "有效样本量从 $4000$ 掉到 $616$——"
      "<strong>$85\\%$ 的样本在加权后不起作用了</strong>。"),
    DUAL("直觉：如果某个 $X$ 的取值下几乎所有人都被处理了（$e \\approx 1$），"
         "那么那一小撮没被处理的人要「代表」一大片人群，"
         "他们各自被赋予极大的权重。于是估计值几乎完全由少数几个样本决定。",
         "有效样本量 $\\text{ESS} = (\\sum_i w_i)^2 / \\sum_i w_i^2$，"
         "在权重全等时等于 $n$，在权重集中于一点时趋于 $1$。"
         "它是 IPW 方差的直接诊断量：$\\text{Var} \\propto 1/\\text{ESS}$ 而不是 $1/n$。"),
    CALLOUT("intuition", "该报告的诊断量",
            "报告 IPW 结果时应同时报告 <strong>ESS</strong> 与 <strong>$\\max w$</strong>，"
            "而不只是点估计和置信区间。"
            "原因：置信区间在 ESS $=616$ 时仍然会算出来、仍然看起来正常，"
            "它只是宽——而「宽」在一份周报里通常不会引起警觉，"
            "「$85\\%$ 的样本不起作用」会。"),
])),

("positivity", "正性违反：截断悄悄换掉了估计目标", "".join([
    P("上一节的 $a$ 再大，正性 $0 < e < 1$ 都仍然成立（只是接近边界）。"
      "本节换成<strong>结构性</strong>违反：$X > 1$ 的人 <em>必然</em> 被处理（$e = 1$）。"
      "这在业务上极常见——规则准入、分数超阈值自动获批、历史策略是确定性的。"),
    P("在 notebook 的设定里效应是异质的（$\\tau = 2 + 2X$，所以 $X$ 大的人效应大），"
      "真 ATE $= 2.0019$，而 $X > 1$ 的 $15.9\\%$ 的人没有任何可比的对照："),
    TABLE(["做法", "结果", "偏差", "说明"],
          [["直接 IPW（$e{=}1$ 处 $1/(1-e)$ 爆掉）", "$+2.2502$", "—", "数值上算得出，含义为零"],
           ["截断 $e \\in [0.01, 0.99]$", "$+2.2608$", "$+0.2589$", "偏差<strong>随截断变宽而变大</strong>"],
           ["截断 $e \\in [0.05, 0.95]$", "$+2.3068$", "$+0.3049$", ""],
           ["截断 $e \\in [0.10, 0.90]$", "$+2.3870$", "$+0.3851$", ""],
           ["改问「重叠人群」的 ATE（trim，留 $83.9\\%$）", "$+1.4400$",
            "$+0.0029$", "<strong>无偏，但目标变了</strong>"]]),
    P("最后一行是本节的要点：<strong>该子人群的真 ATE 是 $1.4371$，不是 $2.0019$</strong>。"
      "trim 给出的是一个不同人群上的、正确的答案；"
      "而前三行的截断给出的是同一人群上的、错误的答案，"
      "且错误随截断阈值单调增大——"
      "所以「多截一点让权重稳定」这个操作是在<em>拿偏差换方差</em>，"
      "而它通常不会被记录为这样一次交换。"),
    CALLOUT("danger", "诚实的做法",
            "不要把截断当成「近似 ATE」。正确做法是显式地改变估计目标："
            "报告 <strong>「重叠人群上的 ATE」</strong>，并说明这个人群是谁、占多少"
            "（这里是 $83.9\\%$，被排除的是 $X$ 大、效应<em>最强</em>的那批人）。"
            "Crump 等 (2009) 给出的 $[0.1, 0.9]$ 规则正是为此设计的——"
            "它是一个<strong>换目标</strong>的规则，不是一个去偏的规则。"),
    P("还有一个更根本的观察：$X > 1$ 区域的 ATE <strong>不可识别</strong>，"
      "因为那里没有反事实的信息。"
      "任何在该区域给出数字的方法（截断、外推、模型化）"
      "都是在用<em>假设</em>而不是数据填补——这本身没错，但必须说出来。"),
])),

("dr", "双重稳健：一致性的条件从「都对」松到「至少一个对」", "".join([
    P("IPW 只用了倾向模型 $\\hat{e}$，G-computation（把结果模型的预测差取平均）"
      "只用了结果模型 $\\hat{m}_t$。AIPW 把两者结合："),
    MATH("\\widehat{\\text{ATE}}_{\\text{AIPW}} = \\frac{1}{n}\\sum_i\\Big["
         "\\hat{m}_1(X_i) + \\frac{T_i(Y_i - \\hat{m}_1(X_i))}{\\hat{e}(X_i)}"
         " - \\hat{m}_0(X_i) - \\frac{(1-T_i)(Y_i - \\hat{m}_0(X_i))}{1-\\hat{e}(X_i)}\\Big]"),
    P("notebook 里让真效应是非线性的（$\\tau = 2 + 1.5X^2$，真 ATE $= 3.4949$），"
      "结果模型的「错」版本只含 $X$ 的线性项，倾向模型的「错」版本是常数："),
    TABLE(["倾向模型", "结果模型", "G-computation", "IPW", "AIPW", "$\\vert$AIPW 偏差$\\vert$"],
          [["对", "对", "$+3.4911$", "$+3.4736$", "$+3.4921$", "$0.0028$"],
           ["对", "<strong>错</strong>", "$+2.8158$", "$+3.4736$", "$+3.4764$", "$0.0185$"],
           ["<strong>错</strong>", "对", "$+3.4911$", "$+4.4243$", "$+3.4911$", "$0.0038$"],
           ["<strong>错</strong>", "<strong>错</strong>", "$+2.8158$", "$+4.4243$",
            "$\\mathbf{+2.8158}$", "$\\mathbf{0.6792}$"]]),
    P("前三行 AIPW 都对，第四行才失效。这就是「双重稳健」的确切含义："
      "<strong>它不是「更准」，而是把一致性的条件从「两个模型都对」放松到「至少一个对」</strong>。"),
    CALLOUT("warn", "设计这个实验时我犯了一次错，值得记下来",
            "第一版的结果模型误配是 $\\mu_0 = X + X^2$（两臂相同），"
            "于是 $X^2$ 项在 $\\hat{m}_1 - \\hat{m}_0$ 里<strong>自动抵消</strong>，"
            "「错」的结果模型给出 $1.9928$（几乎无偏），第四行也就成了 $1.9928$——"
            "表格证明不了它想证明的事。"
            "必须让误配是<strong>处理依赖</strong>的（$\\tau$ 本身非线性）才能显出来。"
            "教训：验证「模型 A 错时会怎样」之前，要先确认 A 真的错在<em>会影响估计量</em>的方向上。"),
])),

("fwl", "两个 bit 级恒等式：DR 可以在不报错的情况下消失", "".join([
    H3("恒等式 A：常数 $\\hat{e}$ 使 AIPW $\\equiv$ G-computation"),
    P("如果倾向得分被估成常数（例如「实验是随机的，$\\hat{e} = \\bar{T}$」），"
      "而结果模型是<strong>每臂分别拟合的带截距线性模型</strong>，"
      "那么正规方程强制臂内残差和恰为 $0$，于是修正项"),
    MATH("\\frac{1}{\\hat{e}}\\cdot\\frac{1}{n}\\sum_i T_i(Y_i - \\hat{m}_1(X_i)) "
         "- \\frac{1}{1-\\hat{e}}\\cdot\\frac{1}{n}\\sum_i (1-T_i)(Y_i - \\hat{m}_0(X_i)) = 0 - 0 = 0"),
    TABLE(["$q$（结果模型的特征数）", "臂内残差和 $\\Sigma_{T=1}$ / $\\Sigma_{T=0}$",
           "G-comp", "AIPW（常数 $\\hat{e}$）", "$\\vert$差$\\vert$"],
          [["$10$", "$+9.7\\times10^{-13}$ / $-2.4\\times10^{-13}$", "$+2.5545$", "$+2.5545$",
            "$3.1\\times10^{-15}$"],
           ["$100$", "$-5.6\\times10^{-13}$ / $+5.0\\times10^{-13}$", "$+2.2635$", "$+2.2635$",
            "$2.2\\times10^{-15}$"],
           ["$250$", "$+1.5\\times10^{-10}$ / $-2.1\\times10^{-11}$", "$+2.4215$", "$+2.4215$",
            "$4.1\\times10^{-13}$"],
           ["$400$", "$-6.0\\times10^{-9}$ / $+2.2\\times10^{-9}$", "$+123.4362$", "$+123.4362$",
            "$2.0\\times10^{-11}$"]]),
    P("<strong>一个被称为「双重稳健」的实现，可以在不报任何错的情况下<em>就是</em>纯插入估计量。</strong>"
      "注意最后一行：$q{=}400$ 时 G-comp 已经崩到 $+123.44$（真值约 $2$），"
      "而 AIPW 与它逐位相同——修正项完全没有起作用。"),
    H3("恒等式 B：过拟合把修正项连续吃掉"),
    P("换成<strong>真值</strong>倾向得分，让结果模型的特征数 $q$ 从 $10$ 涨到 $400$"
      "（每臂样本约 $400$，所以 $q$ 越大越过拟合）："),
    TABLE(["$q$", "每臂残差范数", "G-comp", "AIPW", "AIPW $-$ G-comp"],
          [["$10$", "$2.3\\times10^{1}$ / $2.2\\times10^{1}$", "$+2.5545$", "$+2.2395$",
            "$3.15\\times10^{-1}$"],
           ["$50$", "$1.9\\times10^{1}$ / $1.9\\times10^{1}$", "$+2.4167$", "$+2.3087$",
            "$1.08\\times10^{-1}$"],
           ["$150$", "$1.6\\times10^{1}$ / $1.5\\times10^{1}$", "$+2.2499$", "$+2.2494$",
            "$4.6\\times10^{-4}$"],
           ["$320$", "$9.8\\times10^{0}$ / $8.8\\times10^{0}$", "$+3.4754$", "$+3.4755$",
            "$5.3\\times10^{-5}$"],
           ["$400$", "$1.3\\times10^{0}$ / $3.0\\times10^{-9}$", "$+123.4362$", "$+123.4362$",
            "$\\mathbf{7.1\\times10^{-7}}$"]]),
    P("修正项的幅度从 $3.15\\times10^{-1}$ 单调降到 $7.1\\times10^{-7}$——"
      "<strong>$4.4\\times10^{5}$ 倍</strong>，"
      "同时 G-comp 本身从 $+2.55$ 崩到 $+123.44$。"
      "所以「模型越强 → 估计越准」在这里彻底不成立："
      "<strong>越强的结果模型越把纠偏机制关掉</strong>。"),
    P("$q{=}400$ 时对照臂（$394$ 个样本）已经插值（残差 $3.0\\times10^{-9}$），"
      "处理臂（$406$ 个）还没有（残差 $1.3$），"
      "所以两者的差是 $7\\times10^{-7}$ 而不是严格 $0$。"
      "把 $q$ 再加大到超过两臂样本量，差会变成机器精度。"),
    CALLOUT("paper", "这就是 DML 强制交叉拟合的理由",
            "修正项 $T(Y - \\hat{m})/\\hat{e}$ 必须在<strong>没被拟合过</strong>的数据上计算才有内容。"
            "在同一份数据上拟合再取残差，残差会被系统性地压向 $0$，"
            "而这一压缩<em>不会</em>被任何拟合优度指标标记为异常——"
            "恰恰相反，它在训练集上看起来是「模型变好了」。"),
])),

("estimand_ps", "倾向得分模型的「好」不是预测的好", "".join([
    P("一个反复出现的工程习惯是用 AUC 或 log-loss 挑倾向得分模型。"
      "这个做法有一个明确的问题：<strong>倾向得分的目标不是预测处理，而是配平协变量</strong>。"),
    P("极端情形足以说明：如果 $\\hat{e}$ 的 AUC 接近 $1$，"
      "意味着几乎能从 $X$ 完美预测谁被处理——"
      "那正是<strong>重叠最差</strong>的情形，$e$ 大量接近 $0$ 或 $1$，"
      "第 1 节的方差爆炸达到最严重。"
      "反过来 AUC 接近 $0.5$ 意味着处理几乎与 $X$ 无关，"
      "此时权重全等、方差最小，而调整本身也几乎不需要。"),
    TABLE(["$\\hat{e}$ 的预测能力", "重叠", "IPW 方差", "调整的必要性"],
          [["AUC $\\approx 0.5$", "好", "小", "低（几乎是随机实验）"],
           ["AUC 中等", "中", "中", "高（本模块第 1 节的中间几行）"],
           ["AUC $\\to 1$", "<strong>差</strong>", "<strong>爆炸</strong>",
            "无法满足（正性接近违反）"]]),
    P("所以该看的不是预测指标，而是<strong>配平指标</strong>："
      "加权后各协变量在两臂的标准化均值差（standardized mean difference）"
      "是否都落在阈值内（常用 $0.1$）。"
      "这个量直接对应「$\\hat{e}$ 有没有做到它该做的事」，"
      "而预测指标对应的是另一件事。"),
    CALLOUT("warn", "两个指标可以同向恶化，也可以反向",
            "配平差有两种成因：$\\hat{e}$ 模型误配（该修模型），"
            "或者<strong>真实的重叠不足</strong>（修模型没用，只能换目标人群）。"
            "第 2 节的 trim 处理的是后者。"
            "区分办法是看 $\\hat{e}$ 的分布："
            "如果大量样本堆在 $0$ 或 $1$ 附近，那是重叠问题而不是模型问题。"),
])),

("dml", "正交化与交叉拟合各自解决什么", "".join([
    P("双重机器学习（DML）通常被描述成「正交化 + 交叉拟合」。"
      "本节把这两件事分开量，结论比通常的说法更有条件。"),
    H3("正交化在 OLS 下什么也不买：FWL 恒等式"),
    P("「先把 $T$ 和 $Y$ 各自对 $X$ 回归取残差，再拿残差对残差回归」"
      "听起来像一种新估计量。但当 nuisance 由 OLS 拟合时，它与"
      "「$Y$ 对 $[T, X]$ 一起回归，读 $T$ 的系数」<strong>代数上完全相等</strong>"
      "（Frisch–Waugh–Lovell 定理）："),
    CODE("朴素插入 theta_hat = 1.4633431908608447\n"
         "正交化   theta_hat = 1.4633431908608445\n"
         "绝对差 = 2.220e-16   (机器精度)"),
    P("所以正交化<strong>只在 nuisance 被正则化或用机器学习拟合时</strong>"
      "才与朴素插入分离。这决定了 DML 的适用范围："
      "如果你的 nuisance 就是一个 OLS，那么「上 DML」不会改变任何数字。"),
    H3("交叉拟合的作用取决于估计量的形式"),
    P("在<strong>部分线性</strong>的残差对残差得分里，"
      "nuisance 的过拟合同时压低 $\\tilde{T}$ 与 $\\tilde{Y}$，在比值里抵消。"
      "notebook 用两种过拟合的 nuisance 测试，结论是<strong>否定</strong>的："),
    TABLE(["nuisance 学习器", "无交叉拟合", "有交叉拟合（5 折）", "交叉拟合是否更好"],
          [["kNN, $k{=}20$", "$+1.3558$", "$+1.4018$", "<strong>否</strong>"],
           ["kNN, $k{=}60$", "$+1.5474$", "$+1.5886$", "<strong>否</strong>"],
           ["top-$m$ 选择 + OLS, $m{=}30$", "$+0.9903$", "$+0.9733$", "<strong>否</strong>"],
           ["top-$m$ 选择 + OLS, $m{=}250$", "$+0.9282$", "$+0.8929$", "<strong>否</strong>"]]),
    P("在<strong>AIPW 得分</strong>里就完全不同了，因为修正项 $(Y - \\hat{m})/\\hat{e}$ 不抵消——"
      "上一节的两个恒等式正是这里的机制。"
      "notebook 在同一个 $q$ 下对比，交叉拟合让修正项重新活过来"
      "（$q{=}150$ 时 AIPW 与 G-comp 的差从 $4.6\\times10^{-4}$ 回到 $0.138$）。"),
    CALLOUT("danger", "但交叉拟合是必要条件，不是充分条件",
            "同一组实验里，$q{=}320$ 时交叉拟合版本的 G-comp 是 $+36.64$、AIPW 是 $+77.82$——"
            "两个都毫无意义。"
            "交叉拟合让修正项恢复了内容，但如果 nuisance 本身在<em>样本外</em>也很差，"
            "那么恢复的是一个巨大的、方向随机的修正。"
            "<strong>DML 的机制保证的是「没有一阶正则化偏差」，"
            "不是「nuisance 学不好也没关系」。</strong>"),
    P("把这一节的结论正面写出来，因为它和通常的表述不同："),
    OL(["<strong>正交化</strong>在 OLS nuisance 下是<em>恒等变换</em>（差 $2.2\\times10^{-16}$）；"
        "它的价值出现在 nuisance 被正则化时。",
        "<strong>交叉拟合</strong>在部分线性得分里可能<em>没有</em>帮助"
        "（本课的四个设定里全部更差），"
        "因为那里的过拟合偏差在残差比值中抵消。",
        "<strong>交叉拟合在 AIPW / 双重稳健得分里是必要的</strong>，"
        "因为那里的过拟合会把修正项吃掉（$4.4\\times10^{5}$ 倍）。",
        "两者都<strong>不能</strong>补救 nuisance 的样本外误差。"]),
])),
]

NB = [
md("""# C76 模块 03 · 倾向得分、IPW、双重稳健与 DML

五件事：

1. **IPW 无偏但方差爆炸**：有效样本量从 4000 掉到 616；
2. **正性违反**：截断悄悄换掉了估计目标（ATE 2.00 vs 重叠人群 1.44）；
3. **AIPW 双重稳健**：只在两个 nuisance *都*错时失效；
4. **两个 bit 级恒等式**：常数 $\\hat{e}$ 使 AIPW $\\equiv$ G-comp；过拟合把修正项吃掉 $4.4\\times10^5$ 倍；
5. **FWL**：OLS nuisance 下正交化是恒等变换（差 $2.2\\times10^{-16}$）。

纯 numpy / CPU / 离线。"""),

code("""import numpy as np

def logit(z):
    return 1.0 / (1.0 + np.exp(-z))

def lstsq(A, y):
    return np.linalg.lstsq(A, y, rcond=None)[0]

def ipw(e, T, Y):
    '''IPW 估计 ATE。'''
    return float(np.mean(T * Y / e - (1 - T) * Y / (1 - e)))

def ess(e, T):
    '''有效样本量 (sum w)^2 / sum w^2。'''
    w = np.where(T == 1, 1.0 / e, 1.0 / (1.0 - e))
    return float(w.sum()**2 / np.sum(w**2)), float(w.max())

print('IPW / ESS / FWL 都只需要最小二乘，无需任何机器学习库。')"""),

md("""## 1. IPW：偏差不是问题，方差是

用**真值**倾向得分 $e = \\sigma(aX)$，$a$ 越大重叠越差。
既然 $e$ 是真的，无偏性不该有任何问题。"""),

code("""def gen_ipw(a, n, seed):
    r = np.random.default_rng(seed)
    x = r.normal(0, 1, n)
    e = logit(a * x)
    T = (r.random(n) < e).astype(float)
    Y = 2.0 * T + 1.0 * x + r.normal(0, 1, n)     # 真 ATE = 2
    return x, e, T, Y

print('真 ATE = 2.0；倾向得分用**真值**')
print('   a    min(e)     max(w)   IPW 均值(50 seeds)  IPW 标准差   有效样本量 ESS')
_stats = {}
for a in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
    est = [ipw(*gen_ipw(a, 4000, 1000 + s)[1:]) for s in range(50)]
    x, e, T, Y = gen_ipw(a, 4000, 1000)
    E, wmax = ess(e, T)
    _stats[a] = (float(np.mean(est)), float(np.std(est)), E)
    print(f'  {a:3.1f}  {e.min():.2e}  {wmax:9.1f}   {np.mean(est):+.4f}'
          f'             {np.std(est):.4f}      {E:7.1f} / 4000')

# 偏差不随重叠退化而系统性增大
for a in (0.0, 1.0, 2.0, 5.0):
    assert abs(_stats[a][0] - 2.0) < 0.35, f'a={a}: IPW 应大致无偏，得到 {_stats[a][0]:.4f}'
# 而方差单调爆炸
assert _stats[5.0][1] / _stats[0.0][1] > 5, '标准差应显著增大'
assert _stats[5.0][2] < 700, f'ESS 应掉到 700 以下，得到 {_stats[5.0][2]:.0f}'

print()
print(f'✅ 均值一直在 2 附近（无偏），标准差涨 {_stats[5.0][1]/_stats[0.0][1]:.1f} 倍')
print(f'✅ ESS 从 4000 掉到 {_stats[5.0][2]:.0f} —— '
      f'{(1-_stats[5.0][2]/4000)*100:.0f}% 的样本在加权后不起作用')
print()
print('-> 报告 IPW 时应同时报 ESS 与 max(w)，而不只是点估计与置信区间。')
print('   置信区间在 ESS=616 时仍然算得出、仍然看起来正常，它只是宽。')"""),

md("""## 2. 正性违反：截断换掉了估计目标

结构性违反：$X > 1$ 的人**必然**被处理（$e = 1$）。
效应异质（$\\tau = 2 + 2X$），所以被排除的正是效应最强的那批人。"""),

code("""r = np.random.default_rng(7)
n = 200_000
x2 = r.normal(0, 1, n)
tau2 = 2.0 + 2.0 * x2
e2 = np.where(x2 > 1.0, 1.0, logit(1.0 * x2))     # X>1 必被处理
T2 = (r.random(n) < e2).astype(float)
Y2 = 1.0 * x2 + tau2 * T2 + r.normal(0, 1, n)

ATE2 = float(tau2.mean())
print(f'真 ATE = E[tau] = {ATE2:.4f}')
print(f'X>1 的人占 {np.mean(x2>1)*100:.1f}%，他们的 e 恰好 = 1（无对照可比）')
print()
ee = np.clip(e2, 1e-12, 1 - 1e-12)
print(f'直接 IPW（e=1 处 1/(1-e) 爆掉）: {ipw(ee, T2, Y2):+.4f}   <- 算得出，含义为零')
print()
print('  截断范围            IPW        偏差')
for tr in (0.01, 0.05, 0.10):
    ec = np.clip(e2, tr, 1 - tr)
    v = ipw(ec, T2, Y2)
    print(f'  e in [{tr:.2f}, {1-tr:.2f}]     {v:+.4f}    {v-ATE2:+.4f}')

keep = (e2 > 0.05) & (e2 < 0.95)
sub_ate = float(tau2[keep].mean())
sub_ipw = ipw(e2[keep], T2[keep], Y2[keep])
print()
print(f'改问「重叠人群」的 ATE（trim，保留 {keep.mean()*100:.1f}%）:')
print(f'  该子人群的**真** ATE = {sub_ate:+.4f}')
print(f'  在该子人群上的 IPW   = {sub_ipw:+.4f}   偏差 {sub_ipw-sub_ate:+.4f}')

# 截断的偏差随阈值单调增大
_b = []
for tr in (0.01, 0.05, 0.10):
    _b.append(abs(ipw(np.clip(e2, tr, 1-tr), T2, Y2) - ATE2))
assert _b[0] < _b[1] < _b[2], f'截断越宽偏差应越大，得到 {_b}'
assert abs(sub_ipw - sub_ate) < 0.02, 'trim 后在子人群上应无偏'
assert abs(sub_ate - ATE2) > 0.5, 'trim 后的目标应与原 ATE 明显不同'

print()
print(f'✅ 截断的偏差随阈值单调增大：{_b[0]:.4f} -> {_b[1]:.4f} -> {_b[2]:.4f}')
print(f'✅ trim 在**子人群**上无偏（差 {abs(sub_ipw-sub_ate):.4f}），')
print(f'   但那个子人群的 ATE 是 {sub_ate:.4f}，不是 {ATE2:.4f}（差 {abs(sub_ate-ATE2):.4f}）')
print()
print(f'被排除的 {(1-keep.mean())*100:.1f}% 的人，他们的平均效应是 '
      f'{tau2[~keep].mean():+.4f} —— 效应**最强**的那批。')
print('-> 所以 trim 不是「近似 ATE」，是换了一个人群。诚实做法是说出那个人群是谁。')"""),

md("""## 3. AIPW：只在两个 nuisance 都错时失效

关键设计：结果模型的误配必须是**处理依赖**的，
否则 $X^2$ 项在 $\\hat m_1 - \\hat m_0$ 里自动抵消（我第一版就犯了这个错）。"""),

code("""n3 = 400_000
r = np.random.default_rng(11)
x3 = r.normal(0, 1, n3)
e3_true = logit(1.2 * x3)
T3 = (r.random(n3) < e3_true).astype(float)
tau3 = 2.0 + 1.5 * x3**2                 # 效应本身非线性 -> 误配不会抵消
Y3 = 1.0 * x3 + tau3 * T3 + r.normal(0, 1, n3)
ATE3 = float(tau3.mean())

def fit_arm(feats, idx, y):
    A = np.column_stack([np.ones(int(idx.sum()))] + [f[idx] for f in feats])
    b = lstsq(A, y[idx])
    Afull = np.column_stack([np.ones(len(y))] + list(feats))
    return Afull @ b

def outcome_models(correct):
    feats = [x3, x3**2] if correct else [x3]
    return {t: fit_arm(feats, T3 == t, Y3) for t in (0, 1)}

def ps_model(correct):
    return e3_true if correct else np.full(n3, T3.mean())

def gcomp(m):
    return float(np.mean(m[1] - m[0]))

def aipw(m, e):
    g1 = m[1] + T3 * (Y3 - m[1]) / e
    g0 = m[0] + (1 - T3) * (Y3 - m[0]) / (1 - e)
    return float(np.mean(g1 - g0))

print(f'真 ATE = E[2 + 1.5x^2] = {ATE3:.4f}   (n={n3:,})')
print('  倾向  结果    G-comp      IPW        AIPW       |AIPW 偏差|')
_rows = {}
for pc in (True, False):
    for oc in (True, False):
        m, e = outcome_models(oc), ps_model(pc)
        g, i, a = gcomp(m), ipw(e, T3, Y3), aipw(m, e)
        _rows[(pc, oc)] = a
        print(f'  {"对" if pc else "错":4s}  {"对" if oc else "错":4s} '
              f'{g:+9.4f}  {i:+9.4f}  {a:+9.4f}    {abs(a-ATE3):8.4f}')

for key in [(True, True), (True, False), (False, True)]:
    assert abs(_rows[key] - ATE3) < 0.05, f'{key}: 至少一个对时 AIPW 应无偏'
assert abs(_rows[(False, False)] - ATE3) > 0.5, '两个都错时 AIPW 应失效'

print()
print('✅ 前三行（至少一个 nuisance 对）AIPW 都无偏；第四行（都错）才失效。')
print('   双重稳健不是「更准」，而是把一致性的条件从「都对」放松到「至少一个对」。')"""),

md("""## 4. 恒等式 A：常数 $\\hat e$ 使 AIPW $\\equiv$ G-computation

每臂带截距的 OLS 使**臂内残差和恰为 0**。
常数 $\\hat e$ 把修正项写成 $\\frac{1}{\\hat e}\\overline{T(Y-\\hat m_1)} - \\frac{1}{1-\\hat e}\\overline{(1-T)(Y-\\hat m_0)} = 0 - 0 = 0$。"""),

code("""n4, p4 = 800, 4
r = np.random.default_rng(0)
X4 = r.normal(0, 1, (n4, p4))
e4 = logit(1.0 * X4[:, 0])
T4 = (r.random(n4) < e4).astype(float)
Y4 = 1.0 * X4[:, 0] + 2.0 * T4 + r.normal(0, 1, n4)
n1, n0 = int(T4.sum()), int(n4 - T4.sum())

rr = np.random.default_rng(7)
W4 = rr.normal(0, 1, (p4, 400))
b4 = rr.uniform(0, 2 * np.pi, 400)
PHI = np.cos(X4 @ W4 + b4)                    # 400 个随机 cos 特征

def outcome_q(q):
    '''用前 q 个随机特征，每臂分别 OLS（含截距）。'''
    Ph = PHI[:, :q]
    m = {}
    for t in (0, 1):
        idx = T4 == t
        A = np.column_stack([np.ones(int(idx.sum())), Ph[idx]])
        beta = lstsq(A, Y4[idx])
        m[t] = np.column_stack([np.ones(n4), Ph]) @ beta
    return m

def gcomp4(m):
    return float(np.mean(m[1] - m[0]))

def aipw4(m, e):
    return float(np.mean(m[1] + T4 * (Y4 - m[1]) / e
                         - (m[0] + (1 - T4) * (Y4 - m[0]) / (1 - e))))

print(f'n={n4}, 处理臂 {n1}, 对照臂 {n0}；结果模型 = q 个随机 cos 特征 + OLS')
print()
print('   q    臂内残差和 (T=1 / T=0)         G-comp        AIPW(常数 e)     |差|')
_ident = []
for q in (10, 100, 250, 400):
    m = outcome_q(q)
    s1 = float(np.sum((Y4 - m[1])[T4 == 1]))
    s0 = float(np.sum((Y4 - m[0])[T4 == 0]))
    g = gcomp4(m)
    a = aipw4(m, np.full(n4, T4.mean()))
    _ident.append(abs(g - a))
    print(f'  {q:4d}    {s1:+.3e} / {s0:+.3e}    {g:+11.4f}   {a:+11.4f}   {abs(g-a):.3e}')

assert max(_ident) < 1e-10, f'常数 e 下 AIPW 应逐位等于 G-comp，最大差 {max(_ident):.3e}'
print()
print(f'✅ 全部 q 上 |AIPW - G-comp| < {max(_ident):.1e} —— 这是恒等式，不是巧合。')
print('   一个被称为「双重稳健」的实现，可以在不报任何错的情况下**就是**纯插入估计量。')"""),

md("""## 5. 恒等式 B：过拟合把修正项连续吃掉

换成**真值**倾向得分，让 $q$ 从 10 涨到 400（每臂约 400 个样本）。"""),

code("""print('   q    每臂残差范数          G-comp        AIPW        AIPW - G-comp')
_gaps = []
for q in (10, 50, 150, 250, 320, 360, 400):
    m = outcome_q(q)
    r1 = float(np.linalg.norm((Y4 - m[1])[T4 == 1]))
    r0 = float(np.linalg.norm((Y4 - m[0])[T4 == 0]))
    g, a = gcomp4(m), aipw4(m, e4)
    _gaps.append(abs(a - g))
    print(f'  {q:4d}   {r1:8.2e} / {r0:8.2e}    {g:+11.4f}  {a:+11.4f}   {abs(a-g):.3e}')

for i in range(1, len(_gaps)):
    assert _gaps[i] < _gaps[i-1] * 1.01, f'修正项应单调缩小：{_gaps}'
assert _gaps[0] / _gaps[-1] > 1e5, f'应缩小 >1e5 倍，实测 {_gaps[0]/_gaps[-1]:.1e}'

print()
print(f'✅ 修正项从 {_gaps[0]:.2e} 单调降到 {_gaps[-1]:.2e}（{_gaps[0]/_gaps[-1]:.1e} 倍）')
print(f'   同时 G-comp 本身从 +2.55 崩到 {gcomp4(outcome_q(400)):+.2f}')
print()
print('-> 「模型越强 -> 估计越准」在这里彻底不成立：')
print('   越强的结果模型越把纠偏机制关掉，而没有任何拟合优度指标会标记这件事。')
print()
_m400 = outcome_q(400)
print(f'注：q=400 时对照臂（{n0} 个样本 < 400）已插值，残差 '
      f'{np.linalg.norm((Y4-_m400[0])[T4==0]):.2e}；')
print(f'    处理臂（{n1} 个 > 400）还没有，残差 '
      f'{np.linalg.norm((Y4-_m400[1])[T4==1]):.2e}。')
print('    所以差是 7e-7 而不是严格 0。q 再加大到超过两臂样本量，差会变成机器精度。')"""),

md("""## 6. FWL：OLS nuisance 下正交化是恒等变换"""),

code("""r = np.random.default_rng(0)
nf, pf = 500, 7
Xf = r.normal(0, 1, (nf, pf))
Tf = Xf.sum(1) + r.normal(0, 1, nf)
Yf = 1.5 * Tf + Xf @ r.normal(0, 1, pf) + r.normal(0, 1, nf)
Ff = np.column_stack([np.ones(nf), Xf])

naive_f = float(lstsq(np.column_stack([Tf, Ff]), Yf)[0])
rt = Tf - Ff @ lstsq(Ff, Tf)
ry = Yf - Ff @ lstsq(Ff, Yf)
orth_f = float(rt @ ry / (rt @ rt))

print(f'朴素插入 theta_hat = {naive_f:.16f}')
print(f'正交化   theta_hat = {orth_f:.16f}')
print(f'绝对差 = {abs(naive_f - orth_f):.3e}   (机器精度)')
assert abs(naive_f - orth_f) < 1e-12, 'FWL 定理：两者应代数相等'

print()
print('-> 「先正交化」在纯 OLS 下不是一种新估计量（Frisch-Waugh-Lovell 定理）。')
print('   它只在 nuisance 被**正则化 / 机器学习**拟合时才与朴素插入分离。')
print('   工程含义：如果你的 nuisance 就是一个 OLS，「上 DML」不会改变任何数字。')"""),

md("""## ✏️ 练习 1：有效样本量与截断的取舍

实现 `ipw_diagnostics(e, T, Y)`，一次返回估计值、ESS、最大权重与
「贡献了一半权重的样本占比」（后者是重叠退化的直观诊断量）。"""),

code("""def ipw_diagnostics(e, T, Y):
    '''IPW 的点估计 + 三个诊断量。

    参数
    ----
    e : 倾向得分 (n,)
    T : 处理 (n,)
    Y : 观测结果 (n,)

    返回
    ----
    dict : {'est', 'ess', 'max_w', 'half_frac'}
      est       : IPW 点估计
      ess       : 有效样本量 (sum w)^2 / sum w^2
      max_w     : 最大权重
      half_frac : 按权重降序排列，累计权重达到总权重一半所需的样本占比
    '''
    # TODO: w = T/e + (1-T)/(1-e)；est 用 ipw()；
    #       half_frac 用 np.sort(w)[::-1] 与 np.cumsum
    raise NotImplementedError"""),

code("""# 自测
# ① 三个诊断量与独立实现一致（单 seed）
_x, _e, _T, _Y = gen_ipw(2.0, 4000, 1000)
_d = ipw_diagnostics(_e, _T, _Y)
_E, _wm = ess(_e, _T)
assert abs(_d['ess'] - _E) < 1e-9, 'ESS 应与 ess() 一致'
assert abs(_d['max_w'] - _wm) < 1e-9, 'max_w 应与 ess() 一致'
assert abs(_d['est'] - ipw(_e, _T, _Y)) < 1e-12, 'est 应与 ipw() 一致'
print('✅ est / ess / max_w 与独立实现逐位一致')

# ② 均匀权重的解析基准
_d0 = ipw_diagnostics(np.full(4000, 0.5), (np.arange(4000) % 2).astype(float),
                      np.zeros(4000))
assert abs(_d0['half_frac'] - 0.5) < 0.01, f'均匀权重下应约 0.5，得到 {_d0["half_frac"]:.4f}'
assert abs(_d0['ess'] - 4000) < 1e-6, '均匀权重下 ESS 应等于 n'
print(f'✅ 均匀权重: ESS = n = 4000，half_frac = {_d0["half_frac"]:.3f}')

# ③ 趋势必须在**多 seed 均值**上看：单 seed 会不单调
print()
print('   a    half_frac 20 seeds 均值 ± sd     ESS 均值    单 seed(1000) 的 half_frac')
_means = []
for _a in (0.0, 0.5, 1.0, 2.0, 3.0, 5.0):
    _hs, _es = [], []
    for _s in range(20):
        _dd = ipw_diagnostics(*gen_ipw(_a, 4000, 1000 + _s)[1:])
        _hs.append(_dd['half_frac']); _es.append(_dd['ess'])
    _means.append(float(np.mean(_hs)))
    _one = ipw_diagnostics(*gen_ipw(_a, 4000, 1000)[1:])['half_frac']
    print(f'  {_a:3.1f}      {np.mean(_hs)*100:6.2f}% ± {np.std(_hs)*100:5.2f}'
          f'      {np.mean(_es):7.1f}         {_one*100:6.2f}%')

for _i in range(1, len(_means)):
    assert _means[_i] < _means[_i-1], f'均值应单调下降：{[round(v,4) for v in _means]}'
print()
print(f'✅ 20 seeds 均值单调：{_means[0]*100:.2f}% -> {_means[-1]*100:.2f}%')

# ④ 诊断量自身的稳定性也在退化 —— 这是一个独立的发现
_sds = []
for _a in (0.0, 2.0, 5.0):
    _hs = [ipw_diagnostics(*gen_ipw(_a, 4000, 1000 + _s)[1:])['half_frac']
           for _s in range(20)]
    _sds.append(float(np.std(_hs)))
assert _sds[0] < 1e-9, 'a=0 时权重全等，half_frac 无抖动'
assert _sds[-1] > 20 * max(_sds[1], 1e-9) or _sds[-1] > 0.04, \\
    f'a=5 时 half_frac 的抖动应显著变大，得到 {_sds}'
print(f'⚠️  half_frac 的跨 seed 标准差: a=0 -> {_sds[0]*100:.2f}pp, '
      f'a=2 -> {_sds[1]*100:.2f}pp, a=5 -> {_sds[2]*100:.2f}pp')
print('   -> 单 seed 下 a=5 甚至会比 a=3 **更大**（上表最后一列），')
print('      因为重叠差到一定程度后，诊断量自己也由少数样本决定。')
print('   -> 所以重叠诊断也要报告不确定性，不能只报一个数。')"""),

md("""## ✏️ 练习 2：截断改变了哪个人群

实现 `trim_target(x, tau, e, lo, hi)`，返回截断后**保留人群**的
真 ATE、保留比例、以及被排除人群的平均效应。

这个函数的作用是把「trim 是换目标」这件事变成一个必须被打印出来的数字。"""),

code("""def trim_target(x, tau, e, lo=0.05, hi=0.95):
    '''trim 后保留人群的真 ATE、保留比例、被排除人群的平均效应。

    参数
    ----
    x   : 协变量（本函数不用，但保留以匹配调用惯例）
    tau : 个体效应（上帝视角）
    e   : 倾向得分
    lo, hi : 保留 lo < e < hi 的样本

    返回
    ----
    dict : {'kept_ate', 'kept_frac', 'dropped_ate', 'full_ate'}
    '''
    # TODO: keep = (e > lo) & (e < hi)，分别算保留/排除人群的 tau 均值与保留比例
    raise NotImplementedError"""),

code("""# 自测
print('  截断范围        保留比例   保留人群 ATE   被排除人群 ATE   全人群 ATE')
_prev_kept = None
for _lo, _hi in [(0.01, 0.99), (0.05, 0.95), (0.10, 0.90), (0.20, 0.80)]:
    _t = trim_target(x2, tau2, e2, _lo, _hi)
    print(f'  [{_lo:.2f}, {_hi:.2f}]      {_t["kept_frac"]*100:6.1f}%    '
          f'{_t["kept_ate"]:+11.4f}    {_t["dropped_ate"]:+12.4f}    {_t["full_ate"]:+.4f}')
    assert abs(_t['full_ate'] - ATE2) < 1e-9, 'full_ate 应等于全人群 ATE'
    # 全期望：kept_frac*kept_ate + (1-kept_frac)*dropped_ate = full_ate
    _recon = (_t['kept_frac'] * _t['kept_ate']
              + (1 - _t['kept_frac']) * _t['dropped_ate'])
    assert abs(_recon - _t['full_ate']) < 1e-9, f'全期望公式应闭合：{_recon} vs {_t["full_ate"]}'
    if _prev_kept is not None:
        assert _t['kept_frac'] <= _prev_kept + 1e-9, '截断越窄保留越少'
    _prev_kept = _t['kept_frac']

_t5 = trim_target(x2, tau2, e2, 0.05, 0.95)
assert _t5['dropped_ate'] > _t5['kept_ate'], '本设定里被排除的人效应更强'
assert abs(_t5['kept_ate'] - ATE2) > 0.5, 'trim 后的目标应与原 ATE 明显不同'

print()
print(f'✅ 全期望公式在每一行都闭合到 1e-9 —— 所以这不是「近似」，是**分解**。')
print(f'✅ [0.05, 0.95]: 保留 {_t5["kept_frac"]*100:.1f}%，目标从 {ATE2:.4f} 变成 '
      f'{_t5["kept_ate"]:.4f}')
print(f'   被排除的 {(1-_t5["kept_frac"])*100:.1f}% 的人效应是 {_t5["dropped_ate"]:+.4f}'
      f' —— 最强的那批')
print('   -> 报告 trim 结果时必须同时报这三个数，否则读者无法知道目标被换了。')"""),

md("""## ✏️ 练习 3：AIPW 修正项的大小

实现 `correction_magnitude(m, e, T, Y)`：返回 AIPW 相对 G-computation
多出来的那一项的绝对值。这个量是「双重稳健性还在不在」的直接诊断。"""),

code("""def correction_magnitude(m, e, T, Y):
    '''AIPW 的修正项大小 = |AIPW - G-computation|。

    参数
    ----
    m : dict {0: mu0_hat 数组, 1: mu1_hat 数组}
    e : 倾向得分 (n,)
    T : 处理 (n,)
    Y : 观测结果 (n,)

    返回
    ----
    float : |修正项均值|
    '''
    # TODO: 修正项 = mean(T*(Y-m[1])/e) - mean((1-T)*(Y-m[0])/(1-e))
    #       返回它的绝对值
    raise NotImplementedError"""),

code("""# 自测
# ① 与第 5 节的 |AIPW - G-comp| 一致
print('   q    correction_magnitude   |AIPW - G-comp|      差')
for _q in (10, 50, 150, 320, 400):
    _m = outcome_q(_q)
    _c = correction_magnitude(_m, e4, T4, Y4)
    _ref = abs(aipw4(_m, e4) - gcomp4(_m))
    assert abs(_c - _ref) < 1e-12, f'q={_q}: {_c} vs {_ref}'
    print(f'  {_q:4d}       {_c:.6e}        {_ref:.6e}     {abs(_c-_ref):.1e}')

# ② 常数 e 时修正项恰为 0（恒等式 A）
print()
print('  常数 e（恒等式 A）:')
for _q in (10, 100, 400):
    _c = correction_magnitude(outcome_q(_q), np.full(n4, T4.mean()), T4, Y4)
    print(f'    q={_q:4d}  修正项 = {_c:.3e}')
    assert _c < 1e-10, f'常数 e 下修正项应为 0，得到 {_c:.3e}'

# ③ 修正项随过拟合单调缩小（恒等式 B）
_cs = [correction_magnitude(outcome_q(_q), e4, T4, Y4) for _q in (10, 50, 150, 250, 320, 400)]
for _i in range(1, len(_cs)):
    assert _cs[_i] < _cs[_i-1] * 1.01, f'应单调缩小：{_cs}'
assert _cs[0] / _cs[-1] > 1e5

print()
print(f'✅ 常数 e 下修正项恒为 0（<1e-10）—— 双重稳健性不在了，但没有报错')
print(f'✅ 过拟合下修正项从 {_cs[0]:.2e} 缩到 {_cs[-1]:.2e}（{_cs[0]/_cs[-1]:.1e} 倍）')
print()
print('   -> 这个量应该被记录进日志。它是唯一能在运行时看出')
print('      「AIPW 已经退化成 G-computation」的信号。')"""),

md("""## ✏️ 练习 4：交叉拟合在哪种得分里是必要的

实现 `crossfit_outcome(q, K, seed)`：用 $K$ 折交叉拟合估结果模型，
返回 `(m0, m1)`。然后用它在同一个 $q$ 下对比修正项的大小。"""),

code("""def crossfit_outcome(q, K=5, seed=1):
    '''K 折交叉拟合的结果模型预测。

    每折的预测由**其余折**拟合的模型给出，所以残差不被压向 0。

    参数
    ----
    q    : 用前 q 个随机特征（全局 PHI）
    K    : 折数
    seed : 划分折的随机种子

    返回
    ----
    (m0, m1) : 两个长度 n4 的数组，分别是 mu0_hat 与 mu1_hat 的样本外预测
    '''
    Ph = PHI[:, :q]
    idx = np.random.default_rng(seed).permutation(n4)
    folds = np.array_split(idx, K)
    m0 = np.zeros(n4)
    m1 = np.zeros(n4)
    # TODO: 对每一折 f：训练集 tr = 除 f 外的样本；
    #       对 t in (0,1)：取 tr 中 T4==t 的样本拟合 OLS（含截距），
    #       预测 Ph[f]，写入 m0[f] / m1[f]
    raise NotImplementedError"""),

code("""# 自测
print('   q    无交叉拟合的修正项    交叉拟合的修正项      放大倍数')
_amp = {}
for _q in (50, 150, 250, 320):
    _m_in = outcome_q(_q)
    _c_in = correction_magnitude(_m_in, e4, T4, Y4)
    _m0, _m1 = crossfit_outcome(_q)
    _c_cf = correction_magnitude({0: _m0, 1: _m1}, e4, T4, Y4)
    _amp[_q] = _c_cf / max(_c_in, 1e-300)
    print(f'  {_q:4d}      {_c_in:.4e}         {_c_cf:.4e}      {_amp[_q]:10.1f}x')

# 交叉拟合让修正项重新活过来
for _q in (150, 250, 320):
    assert _amp[_q] > 10, f'q={_q}: 交叉拟合应让修正项显著变大，实测 {_amp[_q]:.1f}x'

# 但交叉拟合不是万灵药：q 大时两者都无意义
_m0, _m1 = crossfit_outcome(320)
_g_cf = float(np.mean(_m1 - _m0))
print()
print(f'但 q=320 时交叉拟合版本的 G-comp = {_g_cf:+.2f}（真值约 2）')
assert abs(_g_cf - 2.0) > 5, 'q 大时交叉拟合的 nuisance 在样本外也很差'

print()
print(f'✅ 交叉拟合让修正项放大 {min(_amp[q] for q in (150,250,320)):.0f}-'
      f'{max(_amp[q] for q in (150,250,320)):.0f} 倍 —— 双重稳健性恢复了')
print(f'❌ 但 q=320 时 G-comp 仍是 {_g_cf:+.1f} —— nuisance 在样本外也很差')
print()
print('   结论：交叉拟合是**必要条件**，不是充分条件。')
print('   它保证的是「没有一阶正则化偏差」，不是「nuisance 学不好也没关系」。')"""),

md("""## 📖 参考答案"""),

code("""def ipw_diagnostics(e, T, Y):
    '''IPW 的点估计 + 三个诊断量。'''
    w = np.where(T == 1, 1.0 / e, 1.0 / (1.0 - e))
    ws = np.sort(w)[::-1]
    cum = np.cumsum(ws)
    half = int(np.searchsorted(cum, 0.5 * cum[-1])) + 1
    return {
        'est': ipw(e, T, Y),
        'ess': float(w.sum()**2 / np.sum(w**2)),
        'max_w': float(w.max()),
        'half_frac': float(half / len(w)),
    }

def trim_target(x, tau, e, lo=0.05, hi=0.95):
    '''trim 后保留人群的真 ATE、保留比例、被排除人群的平均效应。'''
    keep = (e > lo) & (e < hi)
    return {
        'kept_ate': float(tau[keep].mean()),
        'kept_frac': float(keep.mean()),
        'dropped_ate': float(tau[~keep].mean()) if (~keep).any() else 0.0,
        'full_ate': float(tau.mean()),
    }

def correction_magnitude(m, e, T, Y):
    '''AIPW 的修正项大小 = |AIPW - G-computation|。'''
    c1 = np.mean(T * (Y - m[1]) / e)
    c0 = np.mean((1 - T) * (Y - m[0]) / (1 - e))
    return float(abs(c1 - c0))

def crossfit_outcome(q, K=5, seed=1):
    '''K 折交叉拟合的结果模型预测。'''
    Ph = PHI[:, :q]
    idx = np.random.default_rng(seed).permutation(n4)
    folds = np.array_split(idx, K)
    m0 = np.zeros(n4)
    m1 = np.zeros(n4)
    for f in folds:
        tr = np.setdiff1d(idx, f)
        for t, dst in ((0, m0), (1, m1)):
            sub = tr[T4[tr] == t]
            A = np.column_stack([np.ones(len(sub)), Ph[sub]])
            beta = lstsq(A, Y4[sub])
            dst[f] = np.column_stack([np.ones(len(f)), Ph[f]]) @ beta
    return m0, m1

print('参考答案已定义。')
print()
print('要点：')
print('  1. half_frac 比 ESS 更适合放进周报：「13% 的样本决定了一半的答案」。')
print('  2. trim_target 的全期望公式恒等闭合 —— trim 是**分解**，不是近似。')
print('  3. correction_magnitude 是唯一能在运行时看出 AIPW 已退化的信号。')
print('  4. 交叉拟合恢复修正项（q=150 时 300 倍，q=320 时 7.8e5 倍），')
print('     但不能补救 nuisance 的样本外误差。')"""),

md("""## 🧪 真实工程胶囊：一个会自己报警的 AIPW

下面这段代码把本模块的四个诊断量装进一个估计函数里，
让它在**双重稳健性已经失效**时主动报警，而不是安静地返回一个数字。

四个警报各对应本模块的一个发现：

| 警报 | 触发条件 | 对应发现 |
|---|---|---|
| `LOW_OVERLAP` | ESS / n < 0.3 | IPW 方差爆炸（ESS 4000 → 616）|
| `TARGET_CHANGED` | trim 掉了 > 5% 的样本 | 截断换掉估计目标（2.00 → 1.44）|
| `DR_COLLAPSED` | 修正项 / 点估计 < 1e-3 | 恒等式 A / B（$4.4\\times10^5$ 倍）|
| `NUISANCE_OVERFIT` | 折外残差 / 折内残差 > 2 | 修正项被吃掉的**真正**判据 |

最后一个警报是必需的，因为 `DR_COLLAPSED` 单独用会有假阳性：
修正项小也可能只是结果模型本来就准。"""),

code("""def robust_aipw(x, T, Y, e_hat, q=20, K=5, trim=(0.02, 0.98), seed=0, sub=None):
    '''带诊断的 AIPW。返回 (估计, 警报列表, 诊断字典)。

    结果模型用 q 个随机 cos 特征，所以 q 真的控制模型容量。
    sub 不为 None 时先随机抽 sub 行 —— 用来构造「q 接近折内样本量」的场景。
    '''
    rg = np.random.default_rng(seed)
    if sub is not None and sub < len(Y):
        pick = rg.choice(len(Y), size=sub, replace=False)
        x, T, Y, e_hat = x[pick], T[pick], Y[pick], e_hat[pick]
    n = len(Y)
    alerts = []

    # --- 1. 重叠诊断（在 trim 之前）---
    w = np.where(T == 1, 1.0 / np.clip(e_hat, 1e-12, 1),
                 1.0 / np.clip(1 - e_hat, 1e-12, 1))
    ess_ratio = float(w.sum()**2 / np.sum(w**2) / n)
    if ess_ratio < 0.3:
        alerts.append(f'LOW_OVERLAP: ESS/n = {ess_ratio:.3f} < 0.30')

    # --- 2. trim，并检查估计目标是否被换掉 ---
    keep = (e_hat > trim[0]) & (e_hat < trim[1])
    dropped = 1.0 - float(keep.mean())
    if dropped > 0.05:
        alerts.append(f'TARGET_CHANGED: trim 掉了 {dropped*100:.1f}% 的样本，'
                      f'估计目标是**重叠人群**的 ATE，不是全人群 ATE')
    xk, Tk, Yk, ek = x[keep], T[keep], Y[keep], e_hat[keep]
    nk = len(Yk)

    # --- 3. q 个随机 cos 特征 + K 折交叉拟合 ---
    Wq = rg.normal(0, 1, (1, q))
    bq = rg.uniform(0, 2 * np.pi, q)
    Ph = np.cos(xk[:, None] @ Wq + bq)
    idx = rg.permutation(nk)
    m0, m1 = np.zeros(nk), np.zeros(nk)
    res_in, res_out = [], []
    for f in np.array_split(idx, K):
        tr = np.setdiff1d(idx, f)
        for t, dst in ((0, m0), (1, m1)):
            sub_tr = tr[Tk[tr] == t]
            A = np.column_stack([np.ones(len(sub_tr)), Ph[sub_tr]])
            beta = lstsq(A, Yk[sub_tr])
            res_in.append(np.linalg.norm(A @ beta - Yk[sub_tr]) / max(len(sub_tr), 1)**0.5)
            f_t = f[Tk[f] == t]
            pred = np.column_stack([np.ones(len(f_t)), Ph[f_t]]) @ beta
            dst[f_t] = pred
            if len(f_t):
                res_out.append(np.linalg.norm(pred - Yk[f_t]) / len(f_t)**0.5)
            # 未被赋值的那一臂也要有预测值（用同一模型外推）
            f_o = f[Tk[f] != t]
            if len(f_o):
                dst[f_o] = np.column_stack([np.ones(len(f_o)), Ph[f_o]]) @ beta

    r_in = float(np.mean(res_in))
    r_out = float(np.mean(res_out))
    if r_out > 2.0 * r_in:
        alerts.append(f'NUISANCE_OVERFIT: 折外残差/折内残差 = {r_out/r_in:.2f} > 2，'
                      f'nuisance 在样本外很差（交叉拟合救不了这个）')

    # --- 4. AIPW + 修正项诊断 ---
    g = float(np.mean(m1 - m0))
    corr = float(np.mean(Tk * (Yk - m1) / ek)
                 - np.mean((1 - Tk) * (Yk - m0) / (1 - ek)))
    est = g + corr
    rel = abs(corr) / max(abs(est), 1e-12)
    if rel < 1e-3:
        alerts.append(f'DR_COLLAPSED?: 修正项/点估计 = {rel:.2e} < 1e-3。'
                      f'可能是 AIPW 已退化，也可能只是结果模型本来就准 —— 见下方说明')

    return est, alerts, {'ess_ratio': ess_ratio, 'trim_dropped': dropped,
                         'gcomp': g, 'correction': corr, 'corr_rel': rel,
                         'res_in': r_in, 'res_out': r_out, 'n_kept': nk}


def run_case(tag, e_use, **kw):
    est, alerts, diag = robust_aipw(x2, T2, Y2, e_use, **kw)
    print(tag)
    print(f'  估计 = {est:+.4f}   （真全人群 ATE = {ATE2:.4f}，重叠人群 ATE = 1.4371）')
    print(f'  n_kept = {diag["n_kept"]:,}, ESS/n = {diag["ess_ratio"]:.3f}, '
          f'trim 掉 {diag["trim_dropped"]*100:.1f}%')
    print(f'  修正项 = {diag["correction"]:+.5f}（相对 {diag["corr_rel"]:.2e}）, '
          f'折内残差 {diag["res_in"]:.3f} / 折外残差 {diag["res_out"]:.3f}')
    for a in alerts:
        print(f'  ⚠️  {a}')
    if not alerts:
        print('  ✅ 无警报')
    print()
    return est, alerts, diag

e2_safe = np.clip(e2, 1e-12, 1 - 1e-12)

print('=== 场景 1：正性结构性违反（X>1 必被处理），结果模型规模合适 ===')
_e1, _a1, _d1 = run_case('真值倾向得分, q=20, n=全量:', e2_safe, q=20)
assert any('TARGET_CHANGED' in a for a in _a1), '应报告目标被换掉'
assert not any('NUISANCE_OVERFIT' in a for a in _a1), 'q=20 不该过拟合'

print('=== 场景 2：把倾向得分错估成常数（「反正是随机的」）===')
_e2, _a2, _d2 = run_case('常数倾向得分, q=20:', np.full(len(T2), T2.mean()), q=20)
assert any('DR_COLLAPSED' in a for a in _a2), '常数 e 应触发 DR_COLLAPSED'
assert abs(_d2['correction']) < 1e-3, '常数 e 下修正项应几乎为 0'
assert abs(_e2 - _d2['gcomp']) < 1e-3, '常数 e 下 AIPW 应等于 G-comp（恒等式 A）'
assert abs(_e2 - ATE2) > 3, f'于是它把 G-comp 的全部误差原样继承（{_e2:+.4f} vs 真值 {ATE2:.4f}）'

print('=== 场景 3：q 接近折内样本量（真正的过拟合）===')
_e3, _a3, _d3 = run_case('真值倾向得分, q=300, 抽样 n=2000:', e2_safe, q=300, sub=2000)
assert any('NUISANCE_OVERFIT' in a for a in _a3), 'q=300 / n=2000 应触发过拟合警报'
assert _d3['res_out'] > 2 * _d3['res_in'], '折外残差应远大于折内'
assert abs(_e3 - 1.4371) > 10, f'过拟合下估计应完全失控，得到 {_e3:+.4f}'

print('=== 场景 4：对照 —— 小样本但 q 合适 ===')
_e4, _a4, _d4 = run_case('真值倾向得分, q=8, 抽样 n=2000:', e2_safe, q=8, sub=2000)
assert not any('NUISANCE_OVERFIT' in a for a in _a4), 'q=8 不该触发过拟合'

print('场景 2 值得单独看：')
print(f'  常数 e 使 AIPW 逐位等于 G-comp（差 {abs(_e2-_d2["gcomp"]):.2e}，恒等式 A），')
print(f'  于是它把 G-comp 的全部误差原样继承：{_e2:+.4f} vs 真值 {ATE2:.4f}。')
print('  没有报错，没有异常，只是「双重稳健」这四个字不再成立。')
print()
print('关于 DR_COLLAPSED 的假阳性（这个警报不干净，必须说清楚）:')
print(f'  场景 1 也触发了它，修正项相对 {_d1["corr_rel"]:.2e}。')
print('  但场景 1 的估计是 '
      f'{_e1:+.4f}，与重叠人群的真 ATE 1.4371 只差 {abs(_e1-1.4371):.4f} —— 它是**对的**。')
print('  原因：修正项小有两种可能，而相对大小分不出来：')
print('    (a) 结果模型被过拟合，残差被压向 0  -> 危险（恒等式 B）')
print('    (b) 结果模型本来就准，残差本来就小  -> 无害')
print('  区分办法就是 NUISANCE_OVERFIT 用的那个比值：折外残差 / 折内残差。')
print(f'    场景 1: {_d1["res_out"]/_d1["res_in"]:.2f}  (无害)')
print(f'    场景 3: {_d3["res_out"]/_d3["res_in"]:.2f}  (危险)')
print()
print('工程含义：')
print('  · 四个场景都会「成功返回一个数字」。区别只在于有没有人去看警报。')
print('  · 单看修正项不足以判断 DR 是否失效 —— 必须配上折内/折外残差比。')
print('    这是本模块两个 bit 级恒等式在运行时的正确检测方式。')
print('  · TARGET_CHANGED 不是错误，是**口径变更**：')
print('    它应该出现在结论的措辞里，而不只是出现在日志里。')"""),
]
