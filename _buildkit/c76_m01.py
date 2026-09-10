# -*- coding: utf-8 -*-
"""C76 模块 01 · 潜在结果框架：ATE/ATT/CATE、识别与估计。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的恒等式；概率（条件期望、全期望公式）；"
                 "线性回归的最小二乘解；<em>不需要任何计量经济学背景</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_potential_outcomes.ipynb'
                       '（<strong>分层估计：$K{=}5$ 消除 $89.7\\%$ 的偏差</strong>，'
                       '$K{=}50$ 时残余偏差 $5.3\\times10^{-5}$，而 $K{=}200$ 反弹到 $-0.0034$ / '
                       '<strong>未观测混杂的偏差在 $n$ 从 $2\\!\\times\\!10^3$ 到 '
                       '$2\\!\\times\\!10^6$ 之间稳定在 $+0.853$</strong>，完全不收敛 / '
                       'CATE 定向在异质性弱时是<strong>净亏</strong>（$0.702$ 倍），'
                       '而盈亏平衡噪声 $\\text{sd}^{*}\\!\\cdot\\!\\text{ATE}/\\text{sd}(\\tau)^2$ '
                       '在 $h$ 跨 $48$ 倍时稳定在 $0.779$–$1.130$——'
                       '<strong>二次</strong>律，不是线性）'),
    ("核心参考", "Rubin, <em>Estimating Causal Effects of Treatments in Randomized and "
                 "Nonrandomized Studies</em>（JEP 1974）· "
                 "Holland, <em>Statistics and Causal Inference</em>（JASA 1986）· "
                 "Imbens &amp; Rubin (2015) 第 1–3、17 章 · "
                 "Cochran, <em>The Effectiveness of Adjustment by Subclassification</em>"
                 "（Biometrics 1968，五层规则的来源）· "
                 "Hernán &amp; Robins, <em>Causal Inference: What If</em>（2020）第 1–3 章"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [

("po", "潜在结果：把「效应」写成一个能被讨论的对象", "".join([
    P("日常语言里的「这个改动带来了多少提升」是含混的：提升相对于<em>什么</em>？"
      "潜在结果框架（potential outcomes framework，又称 Neyman–Rubin 因果模型）"
      "先把这个「什么」固定下来。"),
    P("对每个个体 $i$ 和每个可能的处理值 $t$，假设存在一个<strong>确定的</strong>结果 $Y_i(t)$："
      "个体 $i$ 若接受处理 $t$ 会取到的结果。这里有两个不平凡的假设被悄悄用掉了："),
    OL(["<strong>$Y_i(t)$ 只依赖 $i$ 自己的处理</strong>，不依赖别人的处理。"
        "这是 <strong>SUTVA</strong>（Stable Unit Treatment Value Assumption）的第一半，"
        "也叫「无干扰」（no interference）。社交产品、拍卖市场、库存共享全都违反它——"
        "模块 05 会量出违反的代价。",
        "<strong>处理 $t$ 只有一个版本</strong>。"
        "「上线新推荐算法」若在不同机房、不同客户端版本上实际是不同的东西，"
        "$Y_i(1)$ 就不是一个函数值而是一族。这是 SUTVA 的第二半，"
        "也叫<strong>一致性</strong>（consistency）。"]),
    MATH("\\tau_i = Y_i(1) - Y_i(0), \\qquad "
         "Y_i^{\\text{obs}} = T_i Y_i(1) + (1-T_i) Y_i(0)"),
    CALLOUT("intuition", "根本问题：一半的数据永远缺失",
            "第二式说明每个个体只有<strong>一个</strong>潜在结果可见，另一个永远缺失。"
            "所以 $\\tau_i$ 不是「难估」，是<strong>不可观测</strong>。"
            "因果推断能做的只是估计 $\\tau_i$ 的某种<em>平均</em>——"
            "而「哪一种平均」是一个必须显式做出的建模选择，不是技术细节。"),
])),

("targets", "四个目标量：它们数值上不相等", "".join([
    TABLE(["记号", "定义", "回答的问题", "在合成人群上的值"],
          [["ATE", "$E[\\tau_i]$", "对全体人群平均，效应是多少", "$1.000105$"],
           ["ATT", "$E[\\tau_i \\mid T_i{=}1]$", "对<em>已经被处理</em>的人，效应是多少", "$1.375748$"],
           ["ATC", "$E[\\tau_i \\mid T_i{=}0]$", "如果把处理推给<em>还没有</em>的人，效应是多少", "$0.626013$"],
           ["CATE", "$E[\\tau_i \\mid X_i{=}x]$", "对特征为 $x$ 的人，效应是多少", "$1 - 0.75x$（构造已知）"]]),
    P("三个常数量由处理率 $\\pi = P(T{=}1)$ 线性联系："
      "$\\text{ATE} = \\pi\\,\\text{ATT} + (1-\\pi)\\,\\text{ATC}$，"
      "这只是全期望公式。notebook 里把它验证到浮点精度，并检查 $\\pi \\to 1$ 时退化为 ATT。"),
    DUAL("在这个人群上 ATT 是 ATC 的 2.20 倍。也就是说，"
         "「已经用上这个功能的人从它得到的收益」是「还没用上的人会得到的收益」的两倍多。"
         "如果一份周报写着「该功能带来 1.38 的提升」而决策是「推给剩下的人」，"
         "那么这份周报用错了目标量，真实预期是 0.63。",
         "当 $\\tau_i$ 与 $T_i$ 相关时 $\\text{ATT} \\neq \\text{ATC}$。"
         "此处 $\\tau_i = 1 - 0.75 x_i$ 而 $P(T_i{=}1) = \\sigma(1.2 x_i)$ 均随 $x_i$ 单调，"
         "但方向相反，故 $\\text{Cov}(\\tau_i, T_i) < 0$，"
         "由 $\\text{ATT} - \\text{ATC} = \\text{Cov}(\\tau, T)/[\\pi(1-\\pi)]$ 得二者之差为正。"),
    CALLOUT("warn", "先选目标量，再选估计量",
            "本课后面每个估计量都对应一个特定目标量："
            "IPW 默认估 ATE，倾向得分匹配常估 ATT，"
            "工具变量估的是 <strong>LATE</strong>（局部平均效应，只对「被工具推动的人」），"
            "断点回归估的是断点处的 CATE。"
            "<strong>把它们放在一张表里比较大小，通常是在比较四个不同的量。</strong>"),
])),

("cate", "CATE：从「效应有多大」到「该给谁」", "".join([
    P("ATE 是一个数，CATE 是一个函数。产品决策通常需要后者："
      "如果 $\\tau_i$ 对一部分人为负，那么<strong>全量投放的 ATE 正</strong>与"
      "<strong>存在受损人群</strong>可以同时为真。"),
    P("在 notebook 的人群里，ATE $=+0.9985$，而 <strong>$9.1\\%$ 的个体效应为负</strong>——"
      "ATE 完全看不出这一点。这是「平均」二字的代价。"),
    H3("定向投放的收益由异质性强度决定，不由 ATE 决定"),
    P("设 $\\tau_i = 1 - h x_i$，$h$ 越大异质性越强。若按 CATE 的<em>估计值</em>决定是否投放，"
      "而估计带噪声 $\\text{sd}$，notebook 测出的收益（相对全量投放）是："),
    TABLE(["$h$", "$\\text{sd}(\\tau)$", "负效应占比", "$\\text{sd}{=}0.25$", "$\\text{sd}{=}0.5$",
           "$\\text{sd}{=}1.0$", "$\\text{sd}{=}2.0$"],
          [["$0.25$", "$0.250$", "$0.0\\%$", "$0.999$", "$0.972$", "$0.850$", "$0.702$"],
           ["$0.75$", "$0.750$", "$9.1\\%$", "$1.024$", "$1.001$", "$0.918$", "$0.775$"],
           ["$1.50$", "$1.500$", "$25.3\\%$", "$1.221$", "$1.202$", "$1.138$", "$0.988$"],
           ["$3.00$", "$3.001$", "$37.0\\%$", "$1.765$", "$1.753$", "$1.710$", "$1.574$"],
           ["$6.00$", "$6.002$", "$43.5\\%$", "$2.952$", "$2.946$", "$2.921$", "$2.830$"]]),
    P("三处值得注意。第一，$h{=}0.25$（几乎无异质性）时定向在<strong>每一个</strong>噪声水平下都是净亏，"
      "最差降到 $0.702$ 倍——因为此时没有可利用的信号，噪声只制造错误的排除。"
      "第二，ATE 在这五行里几乎不变（$0.988$–$0.999$），"
      "所以<strong>光看 ATE 无法判断定向有没有价值</strong>。"
      "第三，盈亏平衡的噪声水平满足 $\\text{sd}^{*} \\approx 0.8\\text{--}1.0 \\cdot \\text{sd}(\\tau)^2/\\text{ATE}$——"
      "<strong>对异质性是二次的</strong>，所以异质性翻倍能容忍的 CATE 噪声涨约 $4$ 倍而不是 $2$ 倍。"),
    CALLOUT("danger", "一个常见的因果误用",
            "「按模型分数投放」在工程上很自然，但模型分数通常是 $\\hat{E}[Y \\mid X]$（<em>预测</em>），"
            "而决策需要 $\\hat{E}[\\tau \\mid X]$（<em>效应</em>）。"
            "这两者可以完全相反：最可能转化的人往往是<strong>不需要干预就会转化</strong>的人，"
            "对他们的效应恰恰最小。上表的 $h$ 越大，这个错误的代价越大。"),
])),

("identification", "识别 vs 估计：两类完全不同的失败", "".join([
    P("因果推断的两个阶段常被混为一谈，但它们的失败方式完全不同："),
    ASCII("""
   目标量           识别（identification）        估计（estimation）
   E[tau]     -->   能否写成可观测分布的函数  -->   给定有限样本，怎么算
                    "假设" 决定成败                "方差/正则/收敛" 决定成败
                            |                              |
                    失败: 偏差不随 n 消失          失败: 方差大，但 n 增大就好
                    补救: 换设计（模块 04）        补救: 加样本/换估计量（模块 03）
""".strip("\n")),
    P("在<strong>可忽略性</strong>（ignorability，又称条件独立、无未观测混杂）"
      "$\\{Y(0), Y(1)\\} \\perp T \\mid X$ 之下，ATE 可识别："),
    MATH("E[\\tau] = E_X\\big[\\,E[Y \\mid T{=}1, X] - E[Y \\mid T{=}0, X]\\,\\big]"),
    P("这个公式右边全是可观测量，所以问题降级成了估计问题。"
      "notebook 用最朴素的估计量——<strong>分层</strong>（subclassification）——验证它："
      "把 $X$ 按分位数切成 $K$ 层，层内做差，再按层大小加权。"),
    TABLE(["层数 $K$", "分层估计", "偏差", "消除的偏差比例"],
          [["$1$（=朴素差）", "$+1.582183$", "$+0.582281$", "$0\\%$"],
           ["$2$", "$+1.214277$", "$+0.214375$", "$63.2\\%$"],
           ["$5$", "$+1.060040$", "$+0.060138$", "$\\mathbf{89.7\\%}$"],
           ["$10$", "$+1.021652$", "$+0.021750$", "$96.3\\%$"],
           ["$50$", "$+0.999955$", "$+5.3\\times10^{-5}$", "$\\approx 100\\%$"],
           ["$200$", "$+0.996530$", "$-0.003372$", "反弹（层内样本不足）"]]),
    P("$K{=}5$ 消除 $89.7\\%$ 的偏差，与 Cochran 1968 年那条「五层足以消除约 $90\\%$ 偏差」"
      "的经典结论一致。而 $K{=}200$ 的反弹说明分层也有偏差-方差权衡："
      "层数太多则层内样本不足，某些层甚至只有单臂。"),
    CALLOUT("danger", "缺一臂的层被静默丢掉，于是估计目标被换掉了",
            "上表的实现遇到「层内只有单臂」时会<strong>跳过该层</strong>——这是标准做法，"
            "但它意味着估计目标不再是全人群 ATE，而是「两臂齐全的层上的 ATE」。"
            "notebook 在 $n{=}4000$ 上量出了丢弃比例："
            "$K{=}50$ 丢 $0\\%$、$K{=}200$ 丢 $2.5\\%$、"
            "<strong>$K{=}400$ 丢 $8.3\\%$、$K{=}800$ 丢 $22.2\\%$</strong>。"
            "更值得注意的是 <strong>$K{=}400$ 的 RMSE（$0.01707$）反而<em>低于</em> "
            "$K{=}100$（$0.01851$）</strong>，"
            "而 RMSE 选出的最优 $K^{*}{=}200$ 本身已经在丢样本了——"
            "所以 <strong>RMSE 不是选层数的正确判据</strong>："
            "它相对的是一个已经被悄悄换掉的目标。"
            "这是本课反复出现的模式：<em>失效不报错，只换掉你在估的东西</em>。"),
])),

("nonidentified", "识别失败时，加样本没有用", "".join([
    P("上一节的可忽略性是<strong>假设</strong>，不是可检验的性质。"
      "notebook 里加入一个未观测混杂 $U$，它同时影响 $Y(0)$ 与处理概率，"
      "然后仍然按 $K{=}20$ 分层（即控制了<strong>全部可观测变量</strong>）："),
    TABLE(["情形", "$n{=}2\\!\\times\\!10^3$", "$n{=}2\\!\\times\\!10^4$",
           "$n{=}2\\!\\times\\!10^5$", "$n{=}2\\!\\times\\!10^6$", "随 $n$ 的走向"],
          [["无未观测混杂", "$+0.0441$", "$+0.0346$", "$+0.0091$", "$+0.0093$", "$\\to 0$"],
           ["未观测混杂 $u{=}1$", "$+0.8644$", "$+0.8337$", "$+0.8500$", "$+0.8534$",
            "$\\to +0.853$，<strong>不收敛到 0</strong>"],
           ["未观测混杂 $u{=}2$", "$+2.4400$", "$+2.4555$", "$+2.4715$", "$+2.4812$",
            "$\\to +2.481$，<strong>不收敛到 0</strong>"]]),
    P("样本量放大 $1000$ 倍，偏差<strong>一位有效数字都没动</strong>。"
      "这就是识别失败与估计困难的实操区别：前者的症状是"
      "「置信区间越来越窄，而窄区间的中心是错的」。"),
    CALLOUT("paper", "为什么这一节比看上去重要",
            "工程上遇到「结论不稳」时的第一反应通常是加数据、加特征、换模型。"
            "这三招全都只对<strong>估计</strong>问题有效。"
            "如果问题在识别，加数据会让错误的结论看起来更可信，"
            "而加特征甚至可能<em>制造</em>新的偏差——模块 02 会给出偏差从 $0$ 跳到 $2.59$ 的例子。"),
])),

("estimators", "同一个调整公式的三种实现", "".join([
    P("识别公式 $E[\\tau] = E_X[E[Y\\mid T{=}1,X] - E[Y\\mid T{=}0,X]]$ 只说了「要什么」，"
      "没说「怎么算」。工程上有三条常见路线，它们估的<strong>是同一个量</strong>，"
      "但在不同的地方会失效："),
    TABLE(["路线", "做法", "最容易失效的地方", "本课的位置"],
          [["分层 / 匹配", "把 $X$ 相近的人配成组，组内做差",
            "$X$ 维度高时组内配不上；缺一臂的层被<strong>静默丢弃</strong>", "本模块"],
           ["加权", "按 $1/e(X)$ 或 $1/(1-e(X))$ 重加权",
            "重叠退化时方差爆炸（ESS $4000 \\to 616$）", "模块 03"],
           ["回归 / 建模", "拟合 $E[Y\\mid T,X]$ 再取预测差",
            "模型误配；而<strong>模型越强越危险</strong>（修正项被吃掉）", "模块 03"]]),
    P("三者的差别不在「准不准」，而在<strong>把假设放在哪里</strong>："
      "分层几乎不假设函数形式，代价是维度；"
      "加权假设 $e(X)$ 估对，代价是方差；"
      "回归假设 $E[Y\\mid T,X]$ 的形式，代价是误配。"),
    H3("为什么本模块先讲分层"),
    P("因为它是唯一<strong>能把失效直接看见</strong>的实现。"
      "notebook 里 $K{=}400$ 时有 $8.3\\%$ 的样本落在缺一臂的层里、"
      "$K{=}800$ 时是 $22.2\\%$——这些样本被跳过，"
      "于是估计目标从「全人群 ATE」变成「两臂齐全的层上的 ATE」。"),
    P("加权和回归会把同一件事藏起来：加权把它变成一个巨大的权重，"
      "回归把它变成一次外推。<strong>两者都不会告诉你有多少样本实际上没有可比对象</strong>，"
      "而分层会——它把那些人明确地扔掉了。"),
    CALLOUT("intuition", "一条可以直接用的诊断",
            "无论最终用哪种实现，都先跑一次<strong>粗分层</strong>（$K{=}10$ 左右）"
            "并报告缺一臂的层占多少样本。"
            "这个数是重叠问题的下限估计，而且不依赖任何模型。"
            "如果它已经很大，那么加权与回归给出的漂亮数字都是外推。"),
])),

("sutva_practice", "SUTVA 的一致性部分：工程上的具体形态", "".join([
    P("第 1 节把 SUTVA 拆成两半：无干扰（模块 05 处理）和<strong>一致性</strong>"
      "——「处理只有一个版本」。后者在论文里几乎不被讨论，"
      "因为在临床试验里它基本自动成立；而在线上系统里它<strong>经常不成立</strong>。"),
    TABLE(["场景", "为什么违反一致性", "后果"],
          [["同一次「上线」打包了多个变更", "$T{=}1$ 实际是若干不同处理的混合",
            "估到的是混合效应；单独回滚任一项都无法预测"],
           ["不同客户端版本上行为不同", "$Y_i(1)$ 依赖于 $i$ 的版本",
            "效应随版本分布漂移，看起来像「效应在衰减」"],
           ["功能有降级路径（超时回退旧逻辑）", "处理组里一部分人实际收到的是对照",
            "这是<strong>不依从</strong>（non-compliance），估到的是 ITT"],
           ["模型每天重训", "处理在时间上不是同一个东西",
            "早期与晚期的效应不可加；分时段看会互相矛盾"]]),
    H3("ITT 与 ATT 的区别"),
    P("第三行值得单独说。当处理组里有一部分人实际没收到处理时，"
      "按<em>指派</em>比较得到的是 <strong>ITT</strong>（intention-to-treat，意图处理效应），"
      "而不是 ATT。两者的关系是"),
    MATH("\\text{ITT} = c \\cdot \\text{ATT}_{\\text{依从者}}"),
    P("其中 $c$ 是依从率（在只有单向不依从、且未依从者效应为零时）。"
      "所以 <strong>ITT 总是被依从率稀释</strong>。"
      "工程上常见的错误不是算错，而是<em>换算</em>："
      "看到 ITT $=0.5$、依从率 $=50\\%$，就报告「真效应是 $1.0$」——"
      "这个换算要求「未依从者的效应恰为零」，而那是一个<strong>额外的假设</strong>，"
      "不是算术。"),
    CALLOUT("warn", "一致性该怎么保证",
            "答案不在统计层：<strong>让「上线」在所有单元上是同一件事</strong>。"
            "具体做法是把处理定义写进实验配置（而不是写在文档里）："
            "一次实验只改一个开关、降级路径要么关掉要么记录、"
            "重训的模型要冻结到实验结束。"
            "这些是工程约束，而它们决定了统计结果有没有意义——"
            "这也是本课反复出现的模式：<em>识别层的问题必须在识别层解决</em>。"),
])),

("cate_estimation", "CATE 怎么估：三种做法与它们各自的偏向", "".join([
    P("第 3 节把 CATE 的<em>用途</em>说清了（定向投放），"
      "但没说怎么估。这里补上，因为三种常见做法的<strong>偏向方式不同</strong>，"
      "而选错会让第 3 节那张表里的噪声 $\\text{sd}$ 变大好几倍。"),
    TABLE(["做法", "怎么做", "偏向", "什么时候合适"],
          [["S-learner（单模型）", "把 $T$ 当一个特征，拟合 $\\hat{f}(X,T)$，"
            "取 $\\hat{f}(X,1)-\\hat{f}(X,0)$",
            "<strong>偏向零</strong>——正则化会把 $T$ 这一维压掉，因为它只解释一小部分方差",
            "效应相对结果的量级不太小"],
           ["T-learner（双模型）", "两臂各拟合一个 $\\hat{m}_t$，取差",
            "<strong>放大两个模型各自的偏差</strong>；小臂上的误差直接进入差",
            "两臂样本量相当、都足够大"],
           ["X-learner / DR-learner", "先估 $\\hat{m}_t$，再对<em>伪结果</em>"
            "（AIPW 型的单点得分）做回归",
            "继承模块 03 的双重稳健性；但需要 $\\hat{e}$",
            "两臂样本量不平衡，或效应量级很小"]]),
    P("第一行的偏向值得注意，因为它<strong>系统性地低估异质性</strong>："
      "S-learner 的正则化把 $T$ 与 $X$ 的交互项压掉，"
      "于是估出来的 CATE 曲线比真实的<em>平</em>。"
      "而第 3 节的表说明，定向的收益完全取决于 $\\text{sd}(\\tau)$——"
      "所以一个把曲线压平的估计器会同时让「定向看起来没价值」"
      "和「实际定向效果差」，两个错误方向一致，很难被发现。"),
    CALLOUT("warn", "评估 CATE 模型不能用预测误差",
            "$\\tau_i$ 不可观测，所以没有直接的「CATE 的 MSE」可算。"
            "常用替代是<strong>提升曲线</strong>（uplift curve）："
            "按 $\\hat{\\tau}$ 降序取前 $k\\%$ 的人，"
            "在<em>随机化的留出集</em>上算他们的实际处理效应。"
            "注意这个评估必须用留出的随机化数据——"
            "用训练数据评估会把过拟合读成异质性，"
            "而那正是第 3 节表里「噪声 $\\text{sd}$」变大的主要来源。"),
    P("最后一点连回本模块第 5 节：以上三种做法<strong>全都建立在可忽略性之上</strong>。"
      "如果存在未观测混杂，CATE 的估计不仅偏，"
      "而且<em>偏的方向随 $X$ 变化</em>——"
      "于是「按 $\\hat{\\tau}$ 定向」会系统性地把资源投给"
      "混杂最强的那部分人，而不是效应最大的那部分人。"),
])),

("assumptions", "把假设写在纸上", "".join([
    P("本模块的四个假设，以及每个假设在什么场景下最可能被违反："),
    TABLE(["假设", "形式", "最常见的违反场景", "本课的处理位置"],
          [["无干扰（SUTVA-1）", "$Y_i(t)$ 不依赖 $T_j, j\\neq i$",
            "社交图、共享库存、竞价市场、双边平台", "模块 05"],
           ["一致性（SUTVA-2）", "处理只有一个版本",
            "灰度里不同客户端版本行为不同；「上线」实际是多个变更的打包", "模块 05（口径）"],
           ["可忽略性", "$\\{Y(0),Y(1)\\} \\perp T \\mid X$",
            "有未观测的动机/资质变量（自选择）", "模块 02（图）/ 04（换设计）"],
           ["正性 / 重叠", "$0 < P(T{=}1\\mid X) < 1$",
            "规则准入（分数超过阈值必然获批）、历史策略是确定性的", "模块 03"]]),
    P("这张表是本课的骨架。<strong>每个后续模块要么放松一个假设，要么量化违反它的代价</strong>。"
      "注意四个假设里只有正性是<em>可以从数据里检查</em>的——"
      "其余三个都必须靠对业务机制的了解来论证。"),
    CALLOUT("intuition", "一句话总结",
            "潜在结果框架本身不解决任何问题，它的价值在于把"
            "「这个数字对不对」这个无法讨论的问题，"
            "换成了「这四个假设里哪一个不成立」这个<strong>可以讨论、可以查证、可以设计实验去检验</strong>的问题。"),
])),
]

NB = [
md("""# C76 模块 01 · 潜在结果框架

三条主线：

1. **四个目标量**（ATE / ATT / ATC / CATE）数值上不相等，先选再估；
2. **识别 vs 估计**：分层估计在可忽略性成立时收敛，未观测混杂下偏差不随 $n$ 消失；
3. **CATE 定向**的收益由异质性强度决定，异质性弱时定向是净亏。

纯 numpy / CPU / 离线。"""),

code("""import numpy as np
np.set_printoptions(precision=4, suppress=True)

def make(n=200_000, seed=0, uconf=0.0, h=0.75):
    '''构造潜在结果全部已知的人群。

    x     : 可观测协变量
    U     : **未观测**混杂（uconf=0 时不起作用）
    tau   : 个体效应 = 1 - h*x（h 控制异质性强度）
    T     : 处理概率随 x 和 U 递增
    '''
    r = np.random.default_rng(seed)
    x  = r.normal(0.0, 1.0, n)
    U  = r.normal(0.0, 1.0, n)
    Y0 = 1.0 * x + uconf * U + r.normal(0.0, 0.5, n)
    tau = 1.0 - h * x
    Y1 = Y0 + tau
    p  = 1.0 / (1.0 + np.exp(-(1.2 * x + uconf * U)))
    T  = (r.random(n) < p).astype(float)
    Y  = np.where(T == 1, Y1, Y0)
    return dict(x=x, U=U, Y0=Y0, Y1=Y1, tau=tau, T=T, Y=Y, p=p)

d = make()
print(f"n = {len(d['T']):,}，处理率 = {d['T'].mean():.4f}")
print()
print('四个目标量：')
print(f"  ATE  = {d['tau'].mean():+.6f}")
print(f"  ATT  = {d['tau'][d['T']==1].mean():+.6f}")
print(f"  ATC  = {d['tau'][d['T']==0].mean():+.6f}")
print(f"  ATT/ATC = {d['tau'][d['T']==1].mean()/d['tau'][d['T']==0].mean():.3f} 倍")
print()
print('CATE 是一个函数，不是一个数：')
for xv in (-2.0, -1.0, 0.0, 1.0, 2.0):
    print(f'  CATE(x={xv:+.1f}) = {1.0 - 0.75*xv:+.4f}')"""),

md("""## 1. 全期望公式：三个常数量的线性关系

$$\\text{ATE} = \\pi\\,\\text{ATT} + (1-\\pi)\\,\\text{ATC}, \\qquad \\pi = P(T{=}1)$$"""),

code("""att = d['tau'][d['T'] == 1].mean()
atc = d['tau'][d['T'] == 0].mean()
pi  = d['T'].mean()
ate = d['tau'].mean()

print(f'{pi:.6f} * {att:.6f} + {1-pi:.6f} * {atc:.6f} = {pi*att + (1-pi)*atc:.6f}')
print(f'真 ATE                                            = {ate:.6f}')
print(f'差                                                = {abs(pi*att+(1-pi)*atc - ate):.3e}')
assert abs(pi*att + (1-pi)*atc - ate) < 1e-12

print()
print('ATT - ATC 的来源是 Cov(tau, T)：')
cov = np.cov(d['tau'], d['T'], ddof=0)[0, 1]
print(f'  Cov(tau, T)              = {cov:+.6f}')
print(f'  Cov/(pi*(1-pi))          = {cov/(pi*(1-pi)):+.6f}')
print(f'  ATT - ATC                = {att-atc:+.6f}')
assert abs(cov/(pi*(1-pi)) - (att-atc)) < 1e-9
print()
print('-> tau 与 T 不相关时三者相等；相关时必须先说清报告哪一个。')"""),

md("""## 2. 分层估计：可忽略性成立时它收敛

把 $X$ 按分位数切成 $K$ 层，层内做差，按层大小加权。
这是最朴素的、也是最透明的后门调整估计量。"""),

code("""def strat_ate(x, T, Y, K, return_dropped=False):
    '''分层（subclassification）估计 ATE。

    参数
    ----
    x : 分层用的协变量 (n,)
    T : 处理 (n,)
    Y : 观测结果 (n,)
    K : 层数
    return_dropped : 是否额外返回被丢弃样本的比例

    返回
    ----
    float : 按层大小加权的层内差
    （return_dropped=True 时返回 (估计, 丢弃比例)）
    '''
    qs = np.quantile(x, np.linspace(0, 1, K + 1))
    qs[0] -= 1e-9
    qs[-1] += 1e-9
    b = np.digitize(x, qs[1:-1])
    num, den, dropped = 0.0, 0, 0
    for k in range(K):
        m = (b == k)
        if m.sum() == 0:
            continue
        t1, t0 = m & (T == 1), m & (T == 0)
        if t1.sum() == 0 or t0.sum() == 0:
            dropped += int(m.sum())       # 该层缺一臂 -> 无法比较，静默跳过
            continue
        num += m.sum() * (Y[t1].mean() - Y[t0].mean())
        den += m.sum()
    if return_dropped:
        return float(num / den), dropped / len(x)
    return float(num / den)

naive = d['Y'][d['T'] == 1].mean() - d['Y'][d['T'] == 0].mean()
b1 = naive - ate
print(f'真 ATE = {ate:.6f}，朴素差 = {naive:.6f}（偏差 {b1:+.6f}）')
print()
print('  层数 K    分层估计      偏差         消除的偏差比例')
for K in (1, 2, 3, 5, 8, 10, 20, 50, 200):
    e = strat_ate(d['x'], d['T'], d['Y'], K)
    frac = (1 - abs(e - ate) / abs(b1)) * 100
    tag = '  <- Cochran 的五层规则' if K == 5 else ('  <- 反弹（层内样本不足）' if K == 200 else '')
    print(f'  {K:6d}   {e:+.6f}   {e-ate:+.6f}      {frac:6.1f}%{tag}')

_e5 = strat_ate(d['x'], d['T'], d['Y'], 5)
assert 0.85 < (1 - abs(_e5-ate)/abs(b1)) < 0.95, 'K=5 应消除约 90% 的偏差'
_e50 = strat_ate(d['x'], d['T'], d['Y'], 50)
_e200 = strat_ate(d['x'], d['T'], d['Y'], 200)
assert abs(_e200-ate) > abs(_e50-ate), 'K=200 的偏差应比 K=50 更大（反弹）'
print()
print('-> 分层也有偏差-方差权衡：K 太小残余混杂，K 太大层内样本不足。')"""),

md("""## 3. 识别失败：偏差不随 $n$ 消失

加入一个未观测混杂 $U$，然后**仍然控制全部可观测变量**（$K{=}20$ 分层）。"""),

code("""print('  情形            n=2e3      n=2e4      n=2e5      n=2e6      走向')
rows = {}
for tag, uc in [('u=0（无混杂）', 0.0), ('u=1（有混杂）', 1.0), ('u=2（强混杂）', 2.0)]:
    row = []
    for n in (2_000, 20_000, 200_000, 2_000_000):
        dd = make(n=n, seed=1, uconf=uc)
        row.append(strat_ate(dd['x'], dd['T'], dd['Y'], 20) - dd['tau'].mean())
    rows[uc] = row
    trend = '-> 0' if abs(row[-1]) < 0.02 else f'-> {row[-1]:+.3f} 不收敛'
    print(f'  {tag:14s} ' + '  '.join(f'{v:+.4f}' for v in row) + f'   {trend}')

assert abs(rows[0.0][-1]) < 0.02, '无混杂时偏差应趋于 0'
assert abs(rows[1.0][-1]) > 0.5, '有混杂时偏差不应消失'
assert abs(rows[2.0][-1]) > abs(rows[1.0][-1]), '混杂越强偏差越大'

print()
print(f'样本量放大 1000 倍，u=1 的偏差从 {rows[1.0][0]:+.4f} 变到 {rows[1.0][-1]:+.4f}')
print('-> 一位有效数字都没动。这是识别问题，不是估计问题。')
print('   症状：置信区间越来越窄，而窄区间的中心是错的。')"""),

md("""## 4. CATE 定向：收益由异质性强度决定"""),

code("""def targeting_gain(h, noise_sd, n=400_000, seed=2):
    '''按带噪声的 CATE 估计决定是否投放，返回相对全量投放的收益倍数。'''
    r = np.random.default_rng(seed)
    x = r.normal(0, 1, n)
    tau = 1.0 - h * x
    base = tau.mean()                                  # 全量投放的人均收益
    rn = np.random.default_rng(9)
    tau_hat = tau + rn.normal(0, noise_sd, n)           # CATE 估计（带噪声）
    gain = tau[tau_hat > 0].sum() / n                   # 只对估计为正的人投放
    return float(gain / base), float(base), float(tau.std()), float((tau < 0).mean())

print('   h    sd(tau)  负效应占比   ATE      sd=0.25  sd=0.5   sd=1.0   sd=2.0')
for h in (0.25, 0.75, 1.5, 3.0, 6.0):
    vals = [targeting_gain(h, sd)[0] for sd in (0.25, 0.5, 1.0, 2.0)]
    _, base, sdt, negf = targeting_gain(h, 0.25)
    flag = '   <- 每档都净亏' if all(v < 1.0 for v in vals) else ''
    print(f'  {h:4.2f}   {sdt:6.3f}   {negf*100:6.1f}%   {base:.4f}   '
          + '  '.join(f'{v:6.3f}' for v in vals) + flag)

_v = [targeting_gain(0.25, sd)[0] for sd in (0.25, 0.5, 1.0, 2.0)]
assert all(v < 1.0 for v in _v), 'h=0.25（无异质性）时定向应全部净亏'
_v6 = [targeting_gain(6.0, sd)[0] for sd in (0.25, 0.5, 1.0, 2.0)]
assert all(v > 2.5 for v in _v6), 'h=6.0 时定向应有数倍收益'

print()
print('三点：')
print('  1. ATE 在这五行里几乎不变（0.988-0.999），所以看 ATE 判断不了定向有没有价值。')
print('  2. h=0.25 时没有可用信号，噪声只制造错误排除 -> 每档都亏，最差 0.702 倍。')
print('  3. 盈亏平衡的噪声水平 sd* ∝ sd(tau)^2 / ATE（练习 4 会把这条律测出来）。')"""),

md("""## ✏️ 练习 1：ATT 的「反事实」写法

ATT 可以写成

$$\\text{ATT} = E[Y \\mid T{=}1] - E[Y(0) \\mid T{=}1]$$

第二项是**处理组的反事实均值**，真实数据里不可见。
实现 `att_from_counterfactual(Y, T, Y0_treated_mean)`。"""),

code("""def att_from_counterfactual(Y, T, Y0_treated_mean):
    '''由处理组的反事实均值算 ATT。

    参数
    ----
    Y                : 观测结果 (n,)
    T                : 处理 (n,)
    Y0_treated_mean  : E[Y(0) | T=1]，处理组若未被处理的均值

    返回
    ----
    float : ATT
    '''
    # TODO: ATT = E[Y|T=1] - E[Y(0)|T=1]
    raise NotImplementedError"""),

code("""# 自测
_d = make(n=80_000, seed=4)
_T, _Y, _Y0, _tau = _d['T'], _d['Y'], _d['Y0'], _d['tau']
_cf = _Y0[_T == 1].mean()                       # 上帝视角
_true_att = _tau[_T == 1].mean()

_got = att_from_counterfactual(_Y, _T, _cf)
assert abs(_got - _true_att) < 1e-12, f'应精确等于 ATT：{_got} vs {_true_att}'

# 若错误地用对照组均值代替反事实均值，就退化成朴素差
_wrong = att_from_counterfactual(_Y, _T, _Y0[_T == 0].mean())
_naive = _Y[_T == 1].mean() - _Y[_T == 0].mean()
assert abs(_wrong - _naive) < 1e-12, '用对照组均值代替反事实均值应得到朴素差'

print(f'✅ 用真实反事实均值 {_cf:+.6f} -> ATT = {_got:+.6f}（真值 {_true_att:+.6f}）')
print(f'✅ 误用对照组均值 {_Y0[_T==0].mean():+.6f} -> {_wrong:+.6f} = 朴素差 {_naive:+.6f}')
print(f'   两者相差 {abs(_got-_wrong):.6f} = 选择偏差')"""),

md("""## ✏️ 练习 2：分层数的偏差-方差权衡

实现 `strat_rmse(K, seeds)`：在固定 $n$ 下，对多个 seed 跑 $K$ 层分层估计，
返回相对真 ATE 的 RMSE。用它找出 RMSE 最小的 $K$。"""),

code("""def strat_rmse(K, seeds=20, n=4_000):
    '''K 层分层估计的 RMSE 与被丢弃样本比例（跨 seed）。

    参数
    ----
    K     : 层数
    seeds : 重复次数
    n     : 每次的样本量（故意取小，让方差可见）

    返回
    ----
    (float, float) : (sqrt(mean((估计 - 真 ATE)^2)), 平均被丢弃样本比例)
    '''
    # TODO: 对 seed in range(seeds)，用 make(n=n, seed=100+seed) 生成数据，
    #       用 strat_ate(..., K, return_dropped=True) 估计，
    #       与该次的 tau.mean() 比较，返回 (RMSE, 平均丢弃比例)
    raise NotImplementedError"""),

code("""# 自测
_res, _drop = {}, {}
print('   K     RMSE      被丢弃的样本')
for _K in (1, 2, 5, 10, 25, 50, 100, 200, 400, 800):
    _res[_K], _drop[_K] = strat_rmse(_K)
    print(f'  {_K:4d}   {_res[_K]:.5f}      {_drop[_K]*100:5.1f}%')

_best = min(_res, key=_res.get)
assert _res[1] > _res[_best], 'K=1（朴素差）不该是最优'
assert 5 <= _best <= 400, f'最优层数应在中间，得到 {_best}'
assert _res[1] > 0.3, f'n=4000 时朴素差的 RMSE 应由偏差主导（>0.3），得到 {_res[1]:.4f}'
assert _drop[50] == 0.0, 'K=50 时不该有层缺臂'
assert _drop[400] > 0.05, f'K=400 应丢弃 >5% 的样本，实测 {_drop[400]*100:.1f}%'
assert _drop[800] > 0.15, f'K=800 应丢弃 >15% 的样本，实测 {_drop[800]*100:.1f}%'

print()
print(f'✅ RMSE 最小的层数 K* = {_best}（RMSE {_res[_best]:.5f}）')
print(f'   K=1 的 RMSE {_res[1]:.5f} 由**偏差**主导（n=4000 下偏差 ~0.58）')
print(f'   而 RMSE 选出的 K*={_best} 已经丢弃了 {_drop[_best]*100:.1f}% 的样本 ——')
print('   所以 RMSE 本身不是选层数的正确判据（它相对的是一个已被换掉的目标）。')
print()
print('⚠️  注意 K=400 的 RMSE 反而比 K=100 更**低**：')
print(f'   K=100 RMSE {_res[100]:.5f}（丢弃 {_drop[100]*100:.1f}%）')
print(f'   K=400 RMSE {_res[400]:.5f}（丢弃 {_drop[400]*100:.1f}%）')
print(f'   K=800 RMSE {_res[800]:.5f}（丢弃 {_drop[800]*100:.1f}%）')
print('   原因不是估计变好了，而是缺一臂的层被**静默跳过**：')
print('   估计目标从「全人群 ATE」悄悄变成了「两臂齐全的层上的 ATE」。')
print('   RMSE 之所以还低，是因为它是相对**原来那个真值**算的，而目标已经换了。')
print('   -> 这是本课反复出现的模式：失效不报错，只换掉你在估的东西。')"""),

md("""## ✏️ 练习 3：未观测混杂的敏感性

给定一个未观测混杂强度 $u$，实现 `residual_bias(u, n)` 返回
「控制全部可观测变量后」的残余偏差。用它画出偏差随 $u$ 的曲线。

这是**敏感性分析**（sensitivity analysis）的最简形式：
既然不能检验可忽略性，就问「$U$ 要多强，才能把结论翻过来」。"""),

code("""def residual_bias(u, n=100_000, K=20, seed=1):
    '''控制全部可观测变量后的残余偏差。

    参数
    ----
    u : 未观测混杂强度（make 的 uconf 参数）
    n : 样本量
    K : 分层数

    返回
    ----
    float : 分层估计 - 真 ATE
    '''
    # TODO: 用 make(n=n, seed=seed, uconf=u) 生成数据，
    #       用 strat_ate(..., K) 估计，减去真 ATE
    raise NotImplementedError"""),

code("""# 自测
print('   u      残余偏差    估计值 / 真 ATE')
_prev = None
for _u in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
    _b = residual_bias(_u)
    _ratio = (1.0 + _b) / 1.0
    print(f'  {_u:4.2f}   {_b:+9.4f}      {_ratio:.3f}')
    if _prev is not None:
        assert _b > _prev - 1e-6, f'偏差应随 u 单调不减：u={_u} 时 {_b:.4f} < 前一档 {_prev:.4f}'
    _prev = _b

assert abs(residual_bias(0.0)) < 0.02, 'u=0 时残余偏差应接近 0'
assert residual_bias(1.0) > 0.5, 'u=1 时残余偏差应显著'

# 找出让估计值翻倍的 u（敏感性分析的典型问法）
_us = np.linspace(0, 4, 17)
_bs = np.array([residual_bias(_u) for _u in _us])
_idx = int(np.argmax(_bs >= 1.0))
print()
print(f'✅ 让估计值翻倍（偏差 >= 真 ATE = 1.0）所需的 u ≈ {_us[_idx]:.2f}')
print('   敏感性分析的用法：如果业务上「存在这么强的未观测混杂」不可信，')
print('   结论就相对稳健；如果可信，结论就必须带上这个限定条件。')"""),

md("""## ✏️ 练习 4：定向投放的盈亏平衡

实现 `targeting_breakeven(h)`：给定异质性强度 $h$，用**二分**找出使定向投放
收益恰好等于全量投放（比值 $=1$）的 CATE 估计噪声 $\\text{sd}^*$。
超过这个噪声水平，定向就是净亏。

自测会检验一条标度律：$\\text{sd}^* \\propto \\text{sd}(\\tau)^2$，
即**异质性翻倍，能容忍的 CATE 噪声涨约 4 倍**。
（用网格搜索会因为分辨率不够而测不出这条律 —— 必须用二分。）"""),

code("""def targeting_breakeven(h, lo=1e-4, hi=4000.0, iters=40):
    '''二分找出定向投放的盈亏平衡噪声水平 sd*。

    targeting_gain(h, sd)[0] 随 sd 单调递减，所以可以二分：
    维持不变式 gain(lo) >= 1.0 > gain(hi)。

    参数
    ----
    h     : 异质性强度
    lo,hi : 二分区间
    iters : 迭代次数

    返回
    ----
    float : sd*，使 targeting_gain(h, sd*)[0] ≈ 1.0
    '''
    # TODO: 二分。每步取 mid=(lo+hi)/2，若 targeting_gain(h, mid)[0] >= 1.0
    #       则 lo=mid，否则 hi=mid。迭代 iters 次后返回 lo。
    raise NotImplementedError"""),

code("""# 自测
print('   h    sd(tau)   盈亏平衡 sd*    sd*/sd(tau)   sd*·ATE/sd(tau)²')
_hs = (0.25, 0.5, 0.75, 1.5, 3.0, 6.0, 12.0)
_sd_star, _law = {}, []
for _h in _hs:
    _sd_star[_h] = targeting_breakeven(_h)
    _sdt = targeting_gain(_h, 0.25)[2]
    _ate = targeting_gain(_h, 0.25)[1]
    _law.append(_sd_star[_h] * _ate / _sdt**2)
    print(f'  {_h:5.2f}   {_sdt:6.3f}   {_sd_star[_h]:11.3f}    {_sd_star[_h]/_sdt:9.3f}'
          f'       {_law[-1]:11.3f}')

# ① 单调：h 越大能容忍的噪声越大
for _i in range(1, len(_hs)):
    assert _sd_star[_hs[_i]] > _sd_star[_hs[_i-1]], f'应单调递增：{_sd_star}'

# ② sd*/sd(tau) **不是**常数 —— 先证伪线性猜想
_lin = [_sd_star[_h] / _h for _h in _hs]
assert max(_lin) / min(_lin) > 20, \\
    f'若 sd* ∝ sd(tau)，该比值应稳定；实测跨度 {max(_lin)/min(_lin):.1f} 倍 -> 线性猜想被证伪'

# ③ sd*·ATE/sd(tau)² 才是稳定的量（二次律）
assert max(_law) / min(_law) < 1.6, \\
    f'sd*·ATE/sd(tau)² 应大致稳定，得到 {[round(v,3) for v in _law]}'

# ④ h 翻倍 -> sd* 涨约 4 倍
for _h in (1.5, 3.0, 6.0):
    _r = _sd_star[_h] / _sd_star[_h / 2]
    assert 3.4 < _r < 4.4, f'h 从 {_h/2} 到 {_h}，sd* 应涨约 4 倍，实测 {_r:.2f}'
    print(f'  h {_h/2:5.2f} -> {_h:5.2f}:  sd* 涨 {_r:.2f} 倍')

print()
print(f'✅ sd*/sd(tau) 跨 {min(_lin):.2f}-{max(_lin):.2f}（{max(_lin)/min(_lin):.0f} 倍跨度）—— 不是线性关系')
print(f'✅ sd*·ATE/sd(tau)² 稳定在 {min(_law):.3f}-{max(_law):.3f} —— **二次**律')
print()
print('   工程含义：能容忍的 CATE 估计噪声 ≈ sd(tau)² / ATE。')
print('   所以判据不是「模型误差小于效应离散度」，而是：')
print('     模型的 CATE 误差 sd 是否小于 sd(tau) × (sd(tau)/ATE)。')
print('   效应离散度只有 ATE 的一半时（sd(tau)/ATE = 0.5），')
print('   容忍的噪声只有 sd(tau) 的一半 —— 定向对模型精度的要求比直觉严得多。')"""),

md("""## 📖 参考答案"""),

code("""def att_from_counterfactual(Y, T, Y0_treated_mean):
    '''ATT = E[Y|T=1] - E[Y(0)|T=1]。'''
    return float(Y[T == 1].mean() - Y0_treated_mean)

def strat_rmse(K, seeds=20, n=4_000):
    '''K 层分层估计的 RMSE 与被丢弃样本比例（跨 seed）。'''
    errs, drops = [], []
    for s in range(seeds):
        dd = make(n=n, seed=100 + s)
        est, dr = strat_ate(dd['x'], dd['T'], dd['Y'], K, return_dropped=True)
        errs.append(est - dd['tau'].mean())
        drops.append(dr)
    return float(np.sqrt(np.mean(np.square(errs)))), float(np.mean(drops))

def residual_bias(u, n=100_000, K=20, seed=1):
    '''控制全部可观测变量后的残余偏差。'''
    dd = make(n=n, seed=seed, uconf=u)
    return float(strat_ate(dd['x'], dd['T'], dd['Y'], K) - dd['tau'].mean())

def targeting_breakeven(h, lo=1e-4, hi=4000.0, iters=40):
    '''二分找出盈亏平衡噪声水平 sd*。'''
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if targeting_gain(h, mid)[0] >= 1.0:
            lo = mid
        else:
            hi = mid
    return float(lo)

print('参考答案已定义。')
print()
print('要点：')
print('  1. ATT 的两种写法完全等价；把反事实均值换成对照组均值就退化成朴素差，')
print('     两者之差正是选择偏差 —— 所以「估 ATT」= 「估处理组的反事实均值」。')
print('  2. 分层数 K 有内点最优：小 K 偏差主导，大 K 层内样本不足。')
print('     而 K 过大时 RMSE 可能**回落**，因为缺一臂的层被静默跳过，估计目标被换掉了。')
print('  3. 敏感性分析把不可检验的假设变成可讨论的量：')
print('     不问「有没有未观测混杂」，问「要多强才能翻掉结论」。')
print('  4. 定向的盈亏平衡噪声 sd* ∝ sd(tau)^2 / ATE —— 对异质性是**二次**的。')
print('     所以「模型误差小于效应离散度」这条直觉判据太松：真正的判据还要')
print('     再乘一个 sd(tau)/ATE 的因子。')"""),

md("""## 🧪 真实工程胶囊：报告哪一个目标量

下面这段代码把「决策问题 → 目标量」的映射固化成一张表，
并在给定数据上把四个目标量一起算出来，让口径错配无法被忽略。

实际项目里最常见的错配是：**用 ATT 的估计支持 ATC 的决策**。
在这份数据上 ATT = 0.648、ATC = 1.351：
「已经在用的人从中获益 0.65」被当成「推给还没用的人也能获益 0.65」，
而真实值是 1.35（**低估 2.09 倍**）。
错配的方向取决于 $\\text{Cov}(\\tau, T)$ 的符号，高估和低估都会发生。"""),

code("""DECISION_TO_TARGET = {
    '要不要全量上线（对全体）':          'ATE',
    '要不要给已经在用的人保留':          'ATT',
    '要不要推给还没用的人':              'ATC',
    '该给哪些人（分人群决策）':          'CATE',
    '要不要对被工具/规则推动的人上线':    'LATE（模块 04）',
}

def report_all_targets(d):
    '''把四个目标量一起算出来，避免口径错配。'''
    T, tau, x = d['T'], d['tau'], d['x']
    out = {
        'ATE': float(tau.mean()),
        'ATT': float(tau[T == 1].mean()),
        'ATC': float(tau[T == 0].mean()),
    }
    print('目标量        值        含义')
    print('-' * 62)
    for k, v in out.items():
        print(f'  {k:6s}   {v:+8.4f}   ' + {
            'ATE': '全人群平均', 'ATT': '已被处理者', 'ATC': '未被处理者'}[k])
    print()
    print('CATE 分位（按 x 十分位）:')
    qs = np.quantile(x, np.linspace(0, 1, 11))
    for i in range(10):
        m = (x >= qs[i]) & (x < qs[i+1] + (1e-9 if i == 9 else 0))
        print(f'  第 {i+1:2d} 十分位  CATE = {tau[m].mean():+8.4f}'
              + ('   <- 效应为负' if tau[m].mean() < 0 else ''))
    out['CATE_min'] = float(min(tau[(x >= qs[i]) & (x < qs[i+1] + 1e-9)].mean()
                                for i in range(10)))
    out['CATE_max'] = float(max(tau[(x >= qs[i]) & (x < qs[i+1] + 1e-9)].mean()
                                for i in range(10)))
    return out

res = report_all_targets(d)
print()
print('决策 -> 目标量 的映射:')
for k, v in DECISION_TO_TARGET.items():
    print(f'  {k:26s} -> {v}')
print()
print(f"最常见的错配：用 ATT {res['ATT']:+.4f} 支持「推给还没用的人」，")
print(f"而该决策的目标量是 ATC {res['ATC']:+.4f} —— 相差 {res['ATC']/res['ATT']:.2f} 倍。")
print('这里 ATT < ATC：自选择进来的人本来就会做得不错，处理对他们的边际价值更小。')
print('所以用 ATT 支持推广决策会**低估**收益 —— 错配的方向取决于 Cov(tau, T) 的符号，')
print('两个方向都会发生，而两者的共同点是：报告的量与决策的量不是同一个。')
print()
print(f"CATE 跨十分位从 {res['CATE_min']:+.4f} 到 {res['CATE_max']:+.4f}，")
print(f"而 ATE 是 {res['ATE']:+.4f}。ATE 是这条曲线的一个加权平均，")
print('不是它的代表值 —— 决策若是分人群的，就必须看曲线。')

assert res['ATC'] > res['ATE'] > res['ATT']
assert res['CATE_min'] < 0 < res['CATE_max']"""),
]
