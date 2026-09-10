# -*- coding: utf-8 -*-
"""C76 模块 04 · 准实验：DiD、工具变量、断点回归、合成控制。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（识别 vs 估计）；模块 02（后门准则）；模块 03（估计量的静默失效）；"
                 "线性回归；<em>本模块处理的正是「后门假设不成立」的情形，"
                 "所以模块 03 的全部工具在这里都<strong>不适用</strong></em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_quasi_experiment.ipynb'
                       '（<strong>pre-trend 检验通过（$\\vert t\\vert{=}0.77$）而 DiD 偏 $+1.50$</strong> / '
                       '<strong>弱工具下 2SLS 中位数 $1.8009$ 与 OLS 的 $1.7994$ 无法区分</strong>，'
                       '且恰好识别的 2SLS <em>没有有限矩</em> / '
                       '<strong>RDD 的偏差来自两侧曲率之<em>差</em></strong>：'
                       '对称时最优带宽是用满全部数据，不对称时 $h^{*}{=}0.2$ / '
                       '合成控制的 pre 期拟合优度对 post 期精度的预测力是<strong>掷硬币</strong>（$2/4$）'),
    ("核心参考", "Angrist &amp; Pischke (2009) 第 4–6 章 · "
                 "Card &amp; Krueger（AER 1994，DiD 的经典应用）· "
                 "Roth, <em>Pre-test with Caution</em>（AEJ: Applied 2022，pre-trend 检验的功效问题）· "
                 "Staiger &amp; Stock, <em>Instrumental Variables Regression with Weak "
                 "Instruments</em>（Econometrica 1997，$F{>}10$ 规则的来源）· "
                 "Gelman &amp; Imbens, <em>Why High-Order Polynomials Should Not Be Used in "
                 "RDD</em>（JBES 2019）· "
                 "Abadie, Diamond &amp; Hainmueller（JASA 2010，合成控制）· "
                 "Abadie, <em>Using Synthetic Controls</em>（JEL 2021）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [

("frame", "换设计，而不是换估计量", "".join([
    P("模块 03 的全部工具都建立在<strong>可忽略性</strong>之上："
      "存在一组可观测的 $X$ 使得条件独立成立。"
      "模块 01 已经量出，这个假设不成立时偏差<strong>不随样本量消失</strong>"
      "（$n$ 从 $2\\times10^3$ 到 $2\\times10^6$，偏差从 $+0.8644$ 到 $+0.8534$）。"),
    P("本模块处理的正是这种情形。共同思路：<strong>不再假设可观测变量足够，"
      "而是去找一个外生的变化来源</strong>——时间、规则阈值、工具、或者对照单位的组合。"),
    TABLE(["方法", "借用的外生性", "核心假设", "假设可检验吗"],
          [["DiD", "处理发生的<strong>时点</strong>", "平行趋势（处理组若未处理，趋势与对照组相同）",
            "<strong>不可</strong>（只能检验处理<em>前</em>的部分）"],
           ["工具变量 / 2SLS", "一个只经由 $T$ 影响 $Y$ 的变量 $Z$",
            "外生性 + 相关性 + 排他性", "相关性可检验；外生性与排他性<strong>不可</strong>"],
           ["断点回归 / RDD", "规则<strong>阈值</strong>两侧的准随机性",
            "结果函数在阈值处连续", "部分可（密度检验、协变量跳变）"],
           ["合成控制", "多个对照单位的<strong>加权组合</strong>",
            "因子结构在 pre/post 之间稳定", "<strong>不可</strong>（pre 期拟合优度不是它）"]]),
    CALLOUT("intuition", "本模块的统一结论",
            "四种方法的核心假设都<strong>无法从数据中检验</strong>。"
            "所以每一节都同时给出两样东西："
            "① 假设成立时的正确性；② 假设不成立时的偏差，"
            "以及<strong>常用的「检验」为什么挡不住它</strong>。"
            "这不是悲观：知道一个假设不可检验，比误以为它已被检验要安全得多。"),
])),

("did", "双重差分：平行趋势不可检验", "".join([
    P("DiD 用「处理组的前后变化」减去「对照组的前后变化」，"
      "从而消掉两组的<em>水平</em>差异："),
    MATH("\\widehat{\\tau}_{\\text{DiD}} = "
         "(\\bar{Y}^{\\text{post}}_{\\text{treat}} - \\bar{Y}^{\\text{pre}}_{\\text{treat}}) - "
         "(\\bar{Y}^{\\text{post}}_{\\text{ctrl}} - \\bar{Y}^{\\text{pre}}_{\\text{ctrl}})"),
    P("notebook 里两组的水平差是 $3.0$，真效应 $\\tau = 2.0$（只在 $t \\geq 4$ 生效）。"
      "标准做法是先跑一个 <strong>pre-trend 检验</strong>："
      "把处理前的期间一分为二做同样的 DiD，若 $\\vert t\\vert < 1.96$ 就认为平行趋势成立。"),
    TABLE(["情形", "DiD 估计", "偏差", "pre-trend $\\vert t\\vert$", "检验结论"],
          [["平行趋势成立", "$+2.0016$", "$+0.002$", "$0.77$", "通过 ✓"],
           ["处理前就分叉（$0.3t$）", "$+3.2016$", "$+1.202$", "$6.08$", "拒绝 ✓"],
           ["<strong>只在处理后分叉（$0.5$/期）</strong>", "$\\mathbf{+3.2516}$",
            "$\\mathbf{+1.252}$", "$\\mathbf{0.77}$", "<strong>通过 ✗</strong>"],
           ["<strong>只在处理后水平跳（$1.5$）</strong>", "$\\mathbf{+3.5016}$",
            "$\\mathbf{+1.502}$", "$\\mathbf{0.77}$", "<strong>通过 ✗</strong>"]]),
    P("后两行是本节的要点：pre-trend 检验的 $t$ 值与「平行趋势成立」那一行"
      "<strong>完全相同</strong>（$0.77$），而 DiD 偏了 $+1.25$ / $+1.50$。"
      "对应的 event-study 系数（相对 $t{=}3$）是"),
    CODE("[-0.099  0.126 -0.062  0.  |  2.454  2.955  3.576  3.838]\n"
         "  ^--- 处理前 4 期全部贴近 0 ---^     ^--- 处理后被污染 ---^"),
    P("处理前的四个点漂亮地贴在零线上——这正是论文里常见的那种 event-study 图。"
      "它<strong>没有说错</strong>任何事：处理前趋势确实平行。"
      "它只是没有、也不可能说出处理<em>后</em>本会不会平行。"),
    CALLOUT("danger", "pre-trend 检验只能证伪，不能证实",
            "而且它的<strong>功效</strong>还常常不足：Roth (2022) 指出，"
            "在典型样本量下，一个足以让 DiD 严重有偏的趋势差"
            "往往<em>不足以</em>被 pre-trend 检验拒绝。"
            "所以「pre-trend 通过」的信息量比通常假设的要低得多。"
            "DiD 的有效性最终依赖<strong>制度知识</strong>——"
            "「处理时点为什么与其他冲击无关」——而不是任何统计检验。"),
])),

("iv", "工具变量：弱工具悄悄退回 OLS", "".join([
    P("工具变量 $Z$ 需要三个条件：相关性（$Z$ 影响 $T$）、"
      "外生性（$Z$ 与误差项无关）、排他性（$Z$ 只经由 $T$ 影响 $Y$）。"
      "两阶段最小二乘（2SLS）先用 $Z$ 预测 $T$，再用预测值估效应。"),
    P("notebook 里内生性使 OLS 上偏到中位数 $1.7994$（真值 $1.0$）。"
      "把工具强度 $\\pi$ 从 $0.5$ 降到 $0.005$："),
    TABLE(["$\\pi$", "第一阶段 $F$ 中位数", "OLS 中位数", "2SLS 中位数",
           "2SLS 均值", "2SLS 四分位距"],
          [["$0.500$", "$250.09$", "$+1.6406$", "$+0.9980$", "$+0.996$", "$0.087$"],
           ["$0.200$", "$39.80$", "$+1.7687$", "$+0.9949$", "$+0.974$", "$0.222$"],
           ["$0.100$", "$9.88$", "$+1.7917$", "$+0.9911$", "$+0.862$", "$0.461$"],
           ["$0.050$", "$2.47$", "$+1.7979$", "$+1.0778$", "$-0.125$", "$0.838$"],
           ["$0.020$", "$0.68$", "$+1.7993$", "$+1.5135$", "$-0.599$", "$1.241$"],
           ["$0.005$", "$0.46$", "$+1.7994$", "$\\mathbf{+1.8009}$", "$+0.492$", "$1.207$"]]),
    P("最后一行：<strong>2SLS 的中位数 $1.8009$ 与 OLS 的 $1.7994$ 已经无法区分</strong>。"
      "弱工具不是「噪声大」，是<strong>悄悄退回它本该修掉的那个有偏估计</strong>。"
      "而 $F$ 中位数在 $\\pi{=}0.1$ 时是 $9.88$，恰好在 $10$ 附近——"
      "这就是「第一阶段 $F > 10$」这条经验规则的来源（Staiger &amp; Stock 1997）。"),
    CALLOUT("warn", "均值那一列不可读，而这本身是一个结论",
            "$\\pi$ 小时 2SLS 的<em>均值</em>在 $-0.599$ 与 $+0.492$ 之间乱跳，"
            "而中位数是平滑单调的。"
            "原因：<strong>恰好识别的 2SLS 没有有限矩</strong>"
            "（分母 $\\hat{\\pi}$ 可以任意接近 $0$）。"
            "所以「多跑几次取平均」不能救弱工具——"
            "<strong>报告均值本身就是错的</strong>，应报告中位数与分位距。"
            "notebook 量出 $\\pi{=}0.005$ 时 2SLS 的取值范围是 "
            "$[-1978.6, +804.9]$，且 $\\vert\\hat\\beta\\vert > 10$ 的比例是 $3.65\\%$。"),
    H3("2SLS 估的是 LATE，不是 ATE"),
    P("即使工具很强，2SLS 识别的也只是<strong>被工具推动的那部分人</strong>的效应"
      "（LATE，local average treatment effect）。"
      "模块 01 已经量出 ATT/ATC 可以相差 $2.09$ 倍；"
      "LATE 与 ATE 的差距同理，取决于「被工具推动的人」与全人群有多不同。"
      "把 2SLS 的结果写成「该功能的效应是 X」是一次<strong>无声的口径替换</strong>。"),
])),

("rdd", "断点回归：偏差来自两侧曲率之差", "".join([
    P("RDD 利用规则阈值：分数刚过线与刚没过线的人在其他方面几乎相同，"
      "所以阈值两侧的结果之差就是效应。实现上是在阈值附近的带宽 $h$ 内做局部线性拟合，"
      "取两侧在阈值处的截距之差。"),
    P("我最初的实验设计是错的，值得先讲。基线函数取 $f(x) = x + 2x^2$（关于断点<strong>对称</strong>），"
      "结果偏差几乎不随 $h$ 变化（$0.0057 \\to 0.0014$），"
      "最优带宽是<strong>用满全部数据</strong>："),
    TABLE(["$h$", "样本量", "对称曲率：估计", "$\\vert$偏差$\\vert$", "RMSE"],
          [["$0.05$", "$301$", "$+0.9943$", "$0.0057$", "$0.1067$"],
           ["$0.20$", "$1197$", "$+0.9936$", "$0.0064$", "$0.0599$"],
           ["$0.70$", "$4196$", "$+0.9969$", "$0.0031$", "$0.0289$"],
           ["$1.00$", "$6000$", "$+0.9986$", "$0.0014$", "$\\mathbf{0.0258}$"]]),
    P("原因：局部线性拟合在 $[0,h)$ 上因曲率产生的截距偏差，"
      "与在 $(-h,0]$ 上产生的偏差<strong>大小相同</strong>，在两侧之差里<strong>恰好抵消</strong>。"
      "所以要看到真正的偏差-方差权衡，曲率必须<strong>两侧不同</strong>："),
    TABLE(["$h$", "样本量", "不对称曲率：估计", "$\\vert$偏差$\\vert$", "RMSE"],
          [["$0.05$", "$301$", "$+0.9933$", "$0.0067$", "$0.1068$"],
           ["$0.10$", "$602$", "$+0.9764$", "$0.0236$", "$0.0833$"],
           ["$\\mathbf{0.20}$", "$1197$", "$+0.9769$", "$0.0231$", "$\\mathbf{0.0640}$"],
           ["$0.40$", "$2392$", "$+0.9313$", "$0.0687$", "$0.0791$"],
           ["$0.70$", "$4196$", "$+0.7934$", "$0.2066$", "$0.2085$"],
           ["$1.00$", "$6000$", "$+0.5825$", "$\\mathbf{0.4175}$", "$0.4181$"]]),
    P("现在有了内点最优 $h^{*} = 0.20$，而 $h{=}1.0$ 的偏差是 $0.4175$（真效应的 $42\\%$）。"),
    CALLOUT("intuition", "一条实践含义",
            "RDD 的偏差取决于两侧函数形状的<strong>差异</strong>，不是曲率本身的大小。"
            "这意味着「结果对分数是非线性的」并不自动意味着 RDD 有偏——"
            "而「两侧的非线性方式不同」才是危险信号。"
            "后者可以部分诊断：分别在两侧拟合并比较二阶项。"),
    H3("高次全局多项式：不改善偏差，只放大方差"),
    TABLE(["多项式次数", "估计（不对称数据，全样本）", "$\\vert$偏差$\\vert$", "标准差"],
          [["$1$", "$+0.5825$", "$0.4175$", "$0.0239$"],
           ["$2$", "$+0.9979$", "$0.0021$", "$0.0357$"],
           ["$3$", "$+0.9927$", "$0.0073$", "$0.0502$"],
           ["$5$", "$+0.9856$", "$0.0144$", "$0.0784$"],
           ["$7$", "$+0.9830$", "$0.0170$", "$0.1061$"],
           ["$9$", "$+0.9878$", "$0.0122$", "$\\mathbf{0.1204}$"]]),
    P("次数从 $1$ 升到 $2$ 把偏差从 $0.4175$ 降到 $0.0021$（真函数确实是二次的）。"
      "再往上就没有收益了：偏差在 $0.007$–$0.017$ 之间徘徊，"
      "而标准差从 $0.0357$ 涨到 $0.1204$（<strong>$3.4$ 倍</strong>）。"
      "这就是 Gelman &amp; Imbens (2019) 建议不要用高次全局多项式的量化版本。"),
])),

("sc", "合成控制：pre 期拟合优度是掷硬币", "".join([
    P("合成控制用多个对照单位的加权组合来构造处理单位的反事实，"
      "权重由 pre 期的拟合决定。经典做法把权重限制在<strong>单纯形</strong>上"
      "（$w \\geq 0$，$\\sum w = 1$），理由是避免外推。"),
    P("直觉上「pre 期拟合得越好，post 期的反事实越可信」。notebook 测了四种设定"
      "（$J{=}20$ 个捐赠者、$n_{\\text{pre}}{=}30$ 期、真 $\\tau{=}3.0$、$200$ seeds）："),
    TABLE(["情形", "权重", "pre 期 RMSE", "$\\sum\\vert w\\vert$",
           "post 均值", "post 标准差", "post RMSE"],
          [["凸包内 / 因子稳定", "单纯形", "$0.2670$", "$1.00$", "$+3.0124$", "$0.1128$",
            "$\\mathbf{0.1135}$"],
           ["凸包内 / 因子稳定", "无约束", "$\\mathbf{0.1764}$", "$5.29$", "$+3.0388$",
            "$0.1740$", "$0.1783$"],
           ["凸包外 / 因子稳定", "单纯形", "$1.7233$", "$1.00$", "$+2.9346$", "$0.7831$",
            "$0.7858$"],
           ["凸包外 / 因子稳定", "无约束", "$\\mathbf{0.2294}$", "$7.14$", "$+3.0339$",
            "$0.2210$", "$\\mathbf{0.2236}$"],
           ["凸包内 + post 新因子", "单纯形", "$0.2670$", "$1.00$", "$+3.0722$", "$0.3283$",
            "$\\mathbf{0.3362}$"],
           ["凸包内 + post 新因子", "无约束", "$\\mathbf{0.1764}$", "$5.29$", "$+3.1022$",
            "$0.5540$", "$0.5633$"],
           ["凸包外 + post 新因子", "单纯形", "$1.7233$", "$1.00$", "$+2.8861$", "$0.7880$",
            "$0.7962$"],
           ["凸包外 + post 新因子", "无约束", "$\\mathbf{0.2294}$", "$7.14$", "$+2.9016$",
            "$0.5944$", "$\\mathbf{0.6024}$"]]),
    P("<strong>无约束 OLS 在全部 $4$ 种设定里 pre 期拟合都更好</strong>（$0.1764$ vs $0.2670$，"
      "$0.2294$ vs $1.7233$），"
      "而 post 期 RMSE 只在 $2$ 种里更好——"
      "<strong>pre 期拟合优度对 post 期精度的预测力是 $2/4$，即掷硬币</strong>。"),
    P("而两种权重的优劣有明确的分界："),
    UL(["<strong>处理单位在捐赠者凸包内</strong>时，单纯形更好（$0.1135$ vs $0.1783$，"
        "优 $\\mathbf{1.57}$ 倍）——无约束的 $\\sum\\vert w\\vert = 5.29$ 是在做外推，付了方差的代价。",
        "<strong>处理单位在凸包外</strong>时，单纯形<em>更差</em>（$0.7858$ vs $0.2236$，"
        "劣 $\\mathbf{3.51}$ 倍）——它根本拟合不上（pre RMSE $1.7233$），"
        "约束此时是负担而不是保护。",
        "<strong>post 期出现新因子</strong>时两者都退化，"
        "而 pre 期拟合<em>完全没变</em>（$0.2670$ / $0.1764$，与无新因子那两行<strong>逐位相同</strong>）——"
        "所以这种失效在 pre 期<strong>无从察觉</strong>。"]),
    CALLOUT("danger", "该报告什么",
            "第三条是最重要的：pre 期 RMSE 在「因子稳定」与「post 出现新因子」两种情形下"
            "<strong>逐位相同</strong>（差 $0.00\\times10^{0}$），"
            "而 post RMSE 相差 $3.0$ 倍（$0.1135 \\to 0.3362$）。"
            "所以合成控制的可信度<strong>不能</strong>由 pre 期拟合来论证。"
            "应报告的是：$\\sum\\vert w\\vert$（外推程度）、"
            "处理单位是否在凸包内、以及 post 期是否有理由相信因子结构未变。"
            "最后一项是<em>制度知识</em>，与 DiD 的平行趋势一样不可检验。"),
])),

("rdd_extra", "RDD 的另外两个诊断，以及模糊断点", "".join([
    P("上一节只处理了带宽与多项式次数。RDD 还有两个<strong>可检验</strong>的部分，"
      "这也是它在四种方法里假设最接近可检验的原因。"),
    OL(["<strong>密度检验</strong>（McCrary）：分数在阈值处的密度应连续。"
        "如果有人能<em>操纵</em>分数刚好过线，密度会在阈值右侧堆积。"
        "这个检验直接针对「阈值两侧准随机」这个前提。",
        "<strong>协变量跳变检验</strong>：把 $Y$ 换成任何"
        "<em>不应该</em>被处理影响的基线协变量，重跑同一个 RDD。"
        "估计值应为 $0$。若某个基线协变量在阈值处跳变，"
        "说明阈值处还有别的规则同时生效。"]),
    P("这两个检验与模块 02 的关系值得点出："
      "第二个检验实际上是在问「阈值这个准工具是否满足<strong>排他性</strong>」——"
      "它只该通过 $T$ 影响 $Y$。这与工具变量的排他性是同一个条件，"
      "区别只在 RDD 里它有一部分能被检验。"),
    H3("模糊断点：RDD 与工具变量的交汇"),
    P("如果过线只是<em>提高</em>了被处理的概率而非必然被处理"
      "（模糊断点，fuzzy RDD），那么「是否过线」就成了一个工具变量，"
      "而估计变成阈值处的一次 2SLS："),
    MATH("\\hat{\\tau}_{\\text{fuzzy}} = "
         "\\frac{\\lim_{x\\downarrow 0} E[Y\\mid x] - \\lim_{x\\uparrow 0} E[Y\\mid x]}"
         "{\\lim_{x\\downarrow 0} E[T\\mid x] - \\lim_{x\\uparrow 0} E[T\\mid x]}"),
    P("分母就是第一阶段。于是<strong>本模块第 3 节的弱工具问题全部适用</strong>："
      "如果过线只把处理概率从 $0.40$ 提到 $0.45$，分母是 $0.05$，"
      "而弱工具的失效是静默的——它会朝 OLS 的方向漂移，"
      "而不是给出一个明显不对的数字。"),
    CALLOUT("danger", "一个容易被忽略的口径",
            "锐断点 RDD 估的是<strong>阈值处的 CATE</strong>，"
            "而模糊断点估的是<strong>阈值处、被阈值推动的那部分人</strong>的 LATE。"
            "两者都不是 ATE，也不是任何「整体人群」的效应。"
            "把 RDD 的结果写成「该规则的效应是 X」时，"
            "$X$ 只对分数恰好在阈值附近的人成立——"
            "而那通常恰好是<em>最不典型</em>的一批用户。"),
])),

("summary", "四种方法的对照与选择", "".join([
    TABLE(["方法", "最主要的失效模式", "本课量出的代价", "最有用的诊断"],
          [["DiD", "只在处理后才出现的趋势分叉",
            "pre-trend 通过，DiD 偏 $+1.50$", "event-study 图（但只能证伪）"],
           ["2SLS", "弱工具",
            "中位数从 $0.998$ 漂到 $1.801$（= OLS）", "第一阶段 $F$；报中位数不报均值"],
           ["RDD", "两侧曲率不同 + 带宽太宽",
            "$h{=}1.0$ 时偏 $0.4175$", "两侧分别拟合并比较二阶项"],
           ["合成控制", "post 期因子结构变化",
            "post RMSE 涨 $4.1$ 倍而 pre RMSE 不变", "$\\sum\\vert w\\vert$ 与凸包位置"]]),
    P("选择顺序上有一条经验：<strong>先问「有没有一个规则阈值」</strong>（RDD 的假设最接近可检验），"
      "再问「有没有一个明确的时点」（DiD），"
      "最后才考虑工具变量（外生性与排他性都不可检验，且弱工具的失效是静默的）。"),
    P("还有一条与本课范围有关的说明：本模块只处理<strong>单一处理时点</strong>的 DiD。"
      "现实中处理常常在不同单位、不同时间陆续发生（交错处理，staggered DiD），"
      "此时双向固定效应估计量会隐含地用「已处理单位」做对照，"
      "从而可能得到<em>与所有个体效应都反号</em>的加权平均。"
      "这是本模块最重要的延伸方向，参考文献里给出了入口。"),
    CALLOUT("paper", "本模块与模块 03 的关系",
            "模块 03 的四个诊断量（ESS、trim 比例、修正项、折内外残差比）"
            "在本模块<strong>全部失效</strong>——"
            "它们检测的是「估计有没有算好」，而本模块的失效在「识别有没有成立」这一层。"
            "所以准实验的质量保证必须是<strong>设计层面</strong>的："
            "事前登记假设、事前定好诊断、事后不换。"),
])),
]

NB = [
md("""# C76 模块 04 · 准实验

四件事，每件都同时给出「假设成立时对」和「假设不成立时错，且常用检验挡不住」：

1. **DiD**：pre-trend 检验通过（$|t|=0.77$）而 DiD 偏 $+1.50$；
2. **2SLS**：弱工具下中位数 $1.8009$ 与 OLS 的 $1.7994$ 无法区分；均值不可读（无有限矩）；
3. **RDD**：偏差来自两侧曲率之*差*；对称时最优带宽是全数据，不对称时 $h^*=0.2$；
4. **合成控制**：pre 期拟合优度对 post 期精度的预测力是 $2/4$。

纯 numpy / CPU / 离线。"""),

code("""import numpy as np

def lstsq(A, y):
    return np.linalg.lstsq(A, y, rcond=None)[0]

print('本模块全部为最小二乘 + 二分/投影，无外部依赖。')"""),

md("""## 1. DiD：构造一个 pre-trend 通过而 DiD 有偏的情形"""),

code("""def panel(n_unit=400, n_pre=4, n_post=4, tau=2.0, kind='parallel',
          amp=0.0, seed=0, noise=1.0):
    '''生成面板数据。处理组从 t=n_pre 起接受处理（真效应 tau）。

    kind:
      'parallel'   两组趋势完全平行
      'pre_slope'  处理组从 t=0 起就有额外斜率 amp（pre-trend 会拒绝）
      'post_only'  处理组的额外斜率**只在处理后**出现（pre-trend 会通过）
      'level_jump' 处理组在处理后有一次额外水平跳变（pre-trend 会通过）
    '''
    r = np.random.default_rng(seed)
    Tn = n_pre + n_post
    treat = np.repeat([0, 1], n_unit // 2)
    ui = r.normal(0, 2, n_unit) + 3.0 * treat      # 两组水平差 3.0
    Y = np.zeros((n_unit, Tn))
    for t in range(Tn):
        if kind == 'parallel':
            extra = 0.0
        elif kind == 'pre_slope':
            extra = amp * t * treat
        elif kind == 'post_only':
            extra = amp * max(0, t - n_pre + 1) * treat
        elif kind == 'level_jump':
            extra = amp * (t >= n_pre) * treat
        Y[:, t] = (ui + 0.5 * t + extra
                   + tau * ((treat == 1) & (t >= n_pre)) + r.normal(0, noise, n_unit))
    return Y, treat, n_pre

def did(Y, tr, npre):
    d = Y[:, npre:].mean(1) - Y[:, :npre].mean(1)
    return float(d[tr == 1].mean() - d[tr == 0].mean())

def pretrend_t(Y, tr, npre):
    '''把处理前的期间一分为二做同样的 DiD，返回 t 统计量。'''
    h = npre // 2
    d = Y[:, h:npre].mean(1) - Y[:, :h].mean(1)
    a, b = d[tr == 1], d[tr == 0]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se)

def event_study(Y, tr, npre):
    '''逐期相对 t=npre-1 的组间差。'''
    base = Y[:, npre - 1]
    return np.array([float((Y[:, t] - base)[tr == 1].mean()
                           - (Y[:, t] - base)[tr == 0].mean())
                     for t in range(Y.shape[1])])

print('真 tau = 2.0（只在 t>=4 生效）；两组水平差 3.0；40 seeds')
print('  情形                          DiD 估计    偏差    pre-trend |t|   检验结论')
_did_res = {}
for tag, kw in [('平行趋势成立', dict(kind='parallel')),
                ('处理前就分叉 amp=0.3', dict(kind='pre_slope', amp=0.3)),
                ('只在处理后分叉 amp=0.5', dict(kind='post_only', amp=0.5)),
                ('只在处理后水平跳 amp=1.5', dict(kind='level_jump', amp=1.5))]:
    es, ts = [], []
    for s in range(40):
        Y, tr, npre = panel(seed=s, **kw)
        es.append(did(Y, tr, npre))
        ts.append(pretrend_t(Y, tr, npre))
    m, t = float(np.mean(es)), float(np.mean(np.abs(ts)))
    _did_res[tag] = (m, t)
    verdict = '通过' if t < 1.96 else '拒绝'
    flag = '  <- 检验没挡住' if (t < 1.96 and abs(m - 2.0) > 0.5) else ''
    print(f'  {tag:28s} {m:+8.4f} {m-2.0:+7.4f}     {t:7.2f}      {verdict}{flag}')

# 平行时无偏，处理前分叉被检验拒绝
assert abs(_did_res['平行趋势成立'][0] - 2.0) < 0.05
assert _did_res['平行趋势成立'][1] < 1.96
assert _did_res['处理前就分叉 amp=0.3'][1] > 1.96, 'pre-trend 应拒绝'
# 两个「只在处理后」的情形：检验通过但 DiD 有偏
for k in ('只在处理后分叉 amp=0.5', '只在处理后水平跳 amp=1.5'):
    assert _did_res[k][1] < 1.96, f'{k}: pre-trend 应通过'
    assert abs(_did_res[k][0] - 2.0) > 1.0, f'{k}: DiD 应明显有偏'
print()
print('✅ 后两行的 pre-trend |t| 与「平行趋势成立」那一行**完全相同**，')
print(f'   而 DiD 偏了 {_did_res["只在处理后分叉 amp=0.5"][0]-2.0:+.2f} / '
      f'{_did_res["只在处理后水平跳 amp=1.5"][0]-2.0:+.2f}')"""),

code("""Y, tr, npre = panel(kind='post_only', amp=0.5, seed=0)
ev = event_study(Y, tr, npre)
print('「只在处理后分叉」的 event-study 系数（相对 t=3）:')
print(' ', np.array2string(ev, precision=3, suppress_small=True))
print()
print('  处理前 4 期:', np.array2string(ev[:npre], precision=3, suppress_small=True),
      f'  最大绝对值 {np.abs(ev[:npre]).max():.3f}')
print('  处理后 4 期:', np.array2string(ev[npre:], precision=3, suppress_small=True))
assert np.abs(ev[:npre]).max() < 0.2, '处理前的 event-study 系数应贴近 0'
assert ev[npre:].min() > 2.0, '处理后被污染（真效应只有 2.0）'
print()
print('✅ 处理前四个点漂亮地贴在零线上 —— 这正是论文里常见的那种 event-study 图。')
print('   它没有说错任何事：处理前趋势确实平行。')
print('   它只是没有、也不可能说出处理**后**本会不会平行。')
print()
print('-> pre-trend / event-study 只能证伪，不能证实。')
print('   DiD 的有效性最终靠**制度知识**（处理时点为什么与其他冲击无关），')
print('   而不靠任何统计检验。')"""),

md("""## 2. 2SLS：弱工具悄悄退回 OLS"""),

code("""def iv_sim(n=1000, pi=0.2, seed=0, beta=1.0, rho=0.8):
    '''工具 Z，内生性由 corr(u, v)=rho 制造。

    T = pi*Z + v,  Y = beta*T + u,  corr(u,v)=rho -> OLS 上偏
    '''
    r = np.random.default_rng(seed)
    Z = r.normal(0, 1, n)
    u = r.normal(0, 1, n)
    v = rho * u + np.sqrt(1 - rho**2) * r.normal(0, 1, n)
    T = pi * Z + v
    Y = beta * T + u
    ols = float(lstsq(np.column_stack([np.ones(n), T]), Y)[1])
    A1 = np.column_stack([np.ones(n), Z])
    b1 = lstsq(A1, T)
    That = A1 @ b1
    tsls = float(lstsq(np.column_stack([np.ones(n), That]), Y)[1])
    res = T - That
    s2 = res @ res / (n - 2)
    F = float((b1[1] / np.sqrt(s2 / np.sum((Z - Z.mean())**2)))**2)
    return ols, tsls, F

print('真 beta = 1.0，内生性 rho=0.8 使 OLS 上偏到约 1.80。n=1000，2000 seeds')
print('   pi     第一阶段 F 中位数   OLS 中位数   2SLS 中位数   2SLS 均值   2SLS 四分位距')
_iv = {}
for pi in (0.5, 0.2, 0.1, 0.05, 0.02, 0.005):
    rr = np.array([iv_sim(pi=pi, seed=s) for s in range(2000)])
    q1, q3 = np.percentile(rr[:, 1], [25, 75])
    _iv[pi] = (float(np.median(rr[:, 2])), float(np.median(rr[:, 0])),
               float(np.median(rr[:, 1])), float(rr[:, 1].mean()), float(q3 - q1))
    print(f'  {pi:5.3f}  {_iv[pi][0]:14.2f}  {_iv[pi][1]:+11.4f}  {_iv[pi][2]:+11.4f}'
          f'  {_iv[pi][3]:+10.3f}  {_iv[pi][4]:12.3f}')

# 强工具时 2SLS 无偏
assert abs(_iv[0.5][2] - 1.0) < 0.02, '强工具时 2SLS 中位数应约 1.0'
# 弱工具时 2SLS 中位数漂到 OLS
assert abs(_iv[0.005][2] - _iv[0.005][1]) < 0.02, \\
    f'弱工具时 2SLS 应与 OLS 无法区分：{_iv[0.005][2]:.4f} vs {_iv[0.005][1]:.4f}'
# F>10 大致是分界
assert _iv[0.1][0] > 5 and abs(_iv[0.1][2] - 1.0) < 0.05, 'F≈10 时 2SLS 应基本可用'
assert _iv[0.05][0] < 5 and abs(_iv[0.05][2] - 1.0) > 0.05, 'F<5 时应开始偏'

print()
print(f'✅ pi=0.005: 2SLS 中位数 {_iv[0.005][2]:.4f} vs OLS 中位数 {_iv[0.005][1]:.4f}'
      f' —— 差 {abs(_iv[0.005][2]-_iv[0.005][1]):.4f}')
print('   弱工具不是「噪声大」，是**悄悄退回它本该修掉的那个有偏估计**。')
print(f'✅ F 中位数 {_iv[0.1][0]:.2f}（pi=0.1）是分界 —— 「第一阶段 F>10」规则的来源')"""),

code("""# 均值那一列不可读，而这本身是一个结论
print('2SLS 的均值 vs 中位数（同一批 2000 次模拟）:')
print('   pi      均值        中位数      |均值-中位数|')
for pi in (0.5, 0.1, 0.02, 0.005):
    print(f'  {pi:5.3f}  {_iv[pi][3]:+10.3f}  {_iv[pi][2]:+10.4f}   {abs(_iv[pi][3]-_iv[pi][2]):.3f}')

# 均值不单调，中位数单调
_means = [_iv[p][3] for p in (0.5, 0.2, 0.1, 0.05, 0.02, 0.005)]
_meds  = [_iv[p][2] for p in (0.5, 0.2, 0.1, 0.05, 0.02, 0.005)]
_mono_med = all(_meds[i] >= _meds[i-1] - 0.02 for i in range(1, len(_meds)))
_mono_mean = all(_means[i] >= _means[i-1] - 0.02 for i in range(1, len(_means)))
assert _mono_med, f'中位数应单调朝 OLS 漂移：{[round(v,4) for v in _meds]}'
assert not _mono_mean, f'均值不该单调（无有限矩）：{[round(v,3) for v in _means]}'

print()
print(f'中位数单调朝 OLS 漂移: {[round(v,3) for v in _meds]}')
print(f'均值在正负之间乱跳:    {[round(v,3) for v in _means]}')
print()
print('✅ 原因：**恰好识别的 2SLS 没有有限矩**（分母 pi_hat 可以任意接近 0）。')
print('   所以「多跑几次取平均」不能救弱工具 —— 报告均值本身就是错的。')
print('   应报告中位数与分位距。')

# 极端尾部有多重
_tail = np.array([iv_sim(pi=0.005, seed=s)[1] for s in range(2000)])
print()
print(f'pi=0.005 时 2SLS 的极端值: min {_tail.min():+.1f}, max {_tail.max():+.1f}, '
      f'|值|>10 的比例 {np.mean(np.abs(_tail)>10)*100:.2f}%')
assert np.abs(_tail).max() > 10, '弱工具下应存在极端值'"""),

md("""## 3. RDD：偏差来自两侧曲率之差

先证明「对称曲率」为什么会骗人。"""),

code("""def rdd_data(n=6000, tau=1.0, seed=0, noise=0.5, mode='asym'):
    '''断点在 x=0。

    mode='sym'  : f = x + 2x^2          （关于断点对称的曲率）
    mode='asym' : f = x + 2x^2|右 - 0.5x^2|左  （两侧曲率不同）
    '''
    r = np.random.default_rng(seed)
    x = r.uniform(-1, 1, n)
    if mode == 'sym':
        f = 1.0 * x + 2.0 * x**2
    else:
        f = 1.0 * x + 2.0 * x**2 * (x >= 0) - 0.5 * x**2 * (x < 0)
    Y = f + tau * (x >= 0) + r.normal(0, noise, n)
    return x, Y

def rdd_local(x, Y, h, deg=1):
    '''带宽 h 内的局部多项式拟合，返回两侧截距之差与带内样本量。'''
    out = []
    for sel in ((x >= 0) & (x < h), (x < 0) & (x > -h)):
        xs, ys = x[sel], Y[sel]
        A = np.column_stack([xs**k for k in range(deg + 1)])
        out.append(float(lstsq(A, ys)[0]))
    return out[0] - out[1], int(((x > -h) & (x < h)).sum())

for mode, tag in [('sym', '对称曲率 2x²（两侧相同）'),
                  ('asym', '不对称 2x²|右 / -0.5x²|左')]:
    print(f'{tag}   真 tau=1.0，60 seeds')
    print('    h     样本量    局部线性 均值±标准差     |偏差|     RMSE')
    best = None
    for h in (0.05, 0.1, 0.2, 0.4, 0.7, 1.0):
        es, ns = [], []
        for s in range(60):
            x, Y = rdd_data(seed=s, mode=mode)
            e, nn = rdd_local(x, Y, h)
            es.append(e); ns.append(nn)
        es = np.array(es)
        bias = abs(es.mean() - 1.0)
        rmse = float(np.sqrt(((es - 1.0)**2).mean()))
        if best is None or rmse < best[1]:
            best = (h, rmse)
        print(f'  {h:5.2f}  {int(np.mean(ns)):6d}    {es.mean():+.4f} ± {es.std():.4f}'
              f'     {bias:.4f}   {rmse:.4f}')
    print(f'    最优带宽 h* = {best[0]}, RMSE = {best[1]:.4f}')
    print()
    if mode == 'sym':
        _sym_best = best
    else:
        _asym_best = best

assert _sym_best[0] == 1.0, f'对称曲率下最优带宽应是用满全部数据，得到 {_sym_best[0]}'
assert 0.1 <= _asym_best[0] <= 0.4, f'不对称曲率下应有内点最优，得到 {_asym_best[0]}'
print('✅ 对称曲率下偏差在左右之差里**恰好抵消**，于是「带宽越大越好」；')
print('   只有两侧曲率不同时才出现真正的偏差-方差权衡与内点最优。')
print()
print('   实践含义：RDD 的偏差取决于两侧函数形状的**差异**，不是曲率本身的大小。')
print('   「结果对分数是非线性的」并不自动意味着 RDD 有偏；')
print('   「两侧的非线性方式不同」才是危险信号 —— 而后者可以部分诊断。')"""),

code("""def rdd_global(x, Y, deg):
    '''全局多项式：Y ~ 1{x>=0} + poly(x) + 1{x>=0}*poly(x)。'''
    A = np.column_stack([(x >= 0).astype(float)]
                        + [x**k for k in range(deg + 1)]
                        + [(x >= 0) * x**k for k in range(1, deg + 1)])
    return float(lstsq(A, Y)[0])

print('全局多项式（不对称数据，用全部样本），60 seeds:')
print('    次数    估计 均值±标准差       |偏差|     标准差')
_gp = {}
for deg in (1, 2, 3, 5, 7, 9):
    es = np.array([rdd_global(*rdd_data(seed=s, mode='asym'), deg) for s in range(60)])
    _gp[deg] = (float(es.mean()), float(es.std()))
    print(f'  {deg:5d}    {es.mean():+.4f} ± {es.std():.4f}      '
          f'{abs(es.mean()-1.0):.4f}     {es.std():.4f}')

assert abs(_gp[1][0] - 1.0) > 0.3, 'deg=1 在不对称曲率下应明显有偏'
assert abs(_gp[2][0] - 1.0) < 0.02, 'deg=2 应基本无偏（真函数是二次的）'
for d in (3, 5, 7, 9):
    assert _gp[d][1] > _gp[2][1], f'deg={d} 的标准差应大于 deg=2'
assert _gp[9][1] / _gp[2][1] > 3, '标准差应涨 3 倍以上'

print()
print(f'✅ 次数 1 -> 2 把偏差从 {abs(_gp[1][0]-1.0):.4f} 降到 {abs(_gp[2][0]-1.0):.4f}')
print(f'❌ 再往上偏差在 0.007-0.017 徘徊，而标准差从 {_gp[2][1]:.4f} 涨到 {_gp[9][1]:.4f}'
      f'（{_gp[9][1]/_gp[2][1]:.1f} 倍）')
print('   这就是 Gelman & Imbens (2019) 建议不用高次全局多项式的量化版本。')"""),

md("""## 4. 合成控制：pre 期拟合优度是掷硬币"""),

code("""def proj_simplex(v):
    '''欧氏投影到单纯形 {w>=0, sum w = 1}（Duchi et al. 的排序算法）。'''
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho = np.nonzero(u * np.arange(1, len(v) + 1) > (css - 1))[0][-1]
    theta = (css[rho] - 1) / (rho + 1.0)
    return np.maximum(v - theta, 0)

def sc_data(J=20, n_pre=30, n_post=10, tau=3.0, seed=0, nfac=3, noise=0.3,
            extra_factor=0.0, in_hull=True):
    '''单位 0 是处理单位。extra_factor>0 时 post 期出现一个 pre 期看不见的因子。'''
    r = np.random.default_rng(seed)
    Tn = n_pre + n_post
    F = r.normal(0, 1, (Tn, nfac))
    L = r.normal(0, 1, (J, nfac))
    if in_hull:
        w0 = np.zeros(J)
        w0[:5] = r.dirichlet(np.ones(5))
        l0 = w0 @ L
    else:
        l0 = r.normal(0, 1, nfac) * 2.0
    Y = np.vstack([l0, L]) @ F.T + r.normal(0, noise, (J + 1, Tn))
    if extra_factor > 0:
        f3 = np.concatenate([np.zeros(n_pre), r.normal(0, 1, n_post)])
        l3 = extra_factor * r.normal(0, 1, J + 1)
        Y = Y + np.outer(l3, f3)
    Y[0, n_pre:] += tau
    return Y, n_pre

def sc_fit(Y, n_pre, mode='simplex'):
    '''返回 (post 期效应估计, pre 期 RMSE, sum|w|)。'''
    y0 = Y[0, :n_pre]
    Xd = Y[1:, :n_pre].T
    J = Xd.shape[1]
    if mode == 'ols':
        w = lstsq(Xd, y0)
    else:
        w = np.full(J, 1.0 / J)
        H = Xd.T @ Xd / n_pre
        g0 = Xd.T @ y0 / n_pre
        lr = 1.0 / np.linalg.eigvalsh(H).max()
        for _ in range(20000):
            w = proj_simplex(w - lr * (H @ w - g0))
    pre = float(np.sqrt(np.mean((Xd @ w - y0)**2)))
    est = float(np.mean(Y[0, n_pre:] - Y[1:, n_pre:].T @ w))
    return est, pre, float(np.abs(w).sum())

print('J=20 捐赠者, n_pre=30 期, 真 tau=3.0, 60 seeds')
print('  情形                    权重     pre RMSE  Σ|w|   post 均值   post 标准差  post RMSE')
_sc = {}
for tag, kw in [('凸包内 / 因子稳定', dict(in_hull=True)),
                ('凸包外 / 因子稳定', dict(in_hull=False)),
                ('凸包内 + post 新因子', dict(in_hull=True, extra_factor=1.0)),
                ('凸包外 + post 新因子', dict(in_hull=False, extra_factor=1.0))]:
    for mode, mt in [('simplex', '单纯形'), ('ols', '无约束')]:
        rr = np.array([sc_fit(*sc_data(seed=s, **kw), mode=mode) for s in range(60)])
        m, sd = float(rr[:, 0].mean()), float(rr[:, 0].std())
        rmse = float(np.sqrt(((rr[:, 0] - 3.0)**2).mean()))
        _sc[(tag, mode)] = (float(rr[:, 1].mean()), float(rr[:, 2].mean()), m, sd, rmse)
        print(f'  {tag:22s} {mt:7s} {rr[:,1].mean():8.4f} {rr[:,2].mean():5.2f} '
              f'{m:+9.4f}   {sd:9.4f}   {rmse:8.4f}')

# 无约束在**每一种**设定里 pre 期拟合都更好
_pre_better = sum(1 for tag in ['凸包内 / 因子稳定', '凸包外 / 因子稳定',
                                '凸包内 + post 新因子', '凸包外 + post 新因子']
                  if _sc[(tag, 'ols')][0] < _sc[(tag, 'simplex')][0])
# 但 post 期只在一部分里更好
_post_better = sum(1 for tag in ['凸包内 / 因子稳定', '凸包外 / 因子稳定',
                                 '凸包内 + post 新因子', '凸包外 + post 新因子']
                   if _sc[(tag, 'ols')][4] < _sc[(tag, 'simplex')][4])
print()
print(f'无约束 OLS 的 pre 期拟合更好的设定数: {_pre_better}/4')
print(f'无约束 OLS 的 post 期 RMSE 更好的设定数: {_post_better}/4')
assert _pre_better == 4, 'OLS 应在每一种设定里 pre 期都拟合更好'
assert _post_better == 2, f'但 post 期只在一半里更好，得到 {_post_better}/4'
print()
print('✅ pre 期拟合优度对 post 期精度的预测力是 2/4 —— 掷硬币。')"""),

code("""# 单纯形 vs 无约束的优劣有明确分界：处理单位是否在凸包内
_in  = (_sc[('凸包内 / 因子稳定', 'simplex')][4], _sc[('凸包内 / 因子稳定', 'ols')][4])
_out = (_sc[('凸包外 / 因子稳定', 'simplex')][4], _sc[('凸包外 / 因子稳定', 'ols')][4])
print('因子稳定时:')
print(f'  凸包**内**: 单纯形 {_in[0]:.4f}  vs 无约束 {_in[1]:.4f}  '
      f'-> 单纯形优 {_in[1]/_in[0]:.2f} 倍')
print(f'  凸包**外**: 单纯形 {_out[0]:.4f}  vs 无约束 {_out[1]:.4f}  '
      f'-> 单纯形劣 {_out[0]/_out[1]:.2f} 倍')
assert _in[0] < _in[1], '凸包内单纯形应更好'
assert _out[0] > _out[1], '凸包外单纯形应更差'

print()
print('post 期出现新因子时，pre 期拟合**完全没变**:')
for tag_a, tag_b in [('凸包内 / 因子稳定', '凸包内 + post 新因子'),
                     ('凸包外 / 因子稳定', '凸包外 + post 新因子')]:
    for mode, mt in [('simplex', '单纯形'), ('ols', '无约束')]:
        pa, pb = _sc[(tag_a, mode)][0], _sc[(tag_b, mode)][0]
        ra, rb = _sc[(tag_a, mode)][4], _sc[(tag_b, mode)][4]
        print(f'  {tag_a[:4]} {mt}: pre {pa:.4f} -> {pb:.4f}（差 {abs(pa-pb):.2e}）,  '
              f'post RMSE {ra:.4f} -> {rb:.4f}（涨 {rb/ra:.1f} 倍）')
        assert abs(pa - pb) < 1e-9, f'pre 期 RMSE 应逐位相同（新因子在 pre 期为 0）'

_r_a = _sc[('凸包内 / 因子稳定', 'simplex')][4]
_r_b = _sc[('凸包内 + post 新因子', 'simplex')][4]
assert _r_b / _r_a > 2, f'post RMSE 应显著变差，实测 {_r_b/_r_a:.1f} 倍'

print()
print(f'✅ pre 期 RMSE 在两种情形下**逐位相同**，而 post RMSE 相差 {_r_b/_r_a:.1f} 倍。')
print('   所以这种失效在 pre 期**无从察觉**。')
print()
print('该报告什么：')
print('  · Σ|w|（外推程度）—— 无约束的 5.09/6.87 说明它在做大幅外推')
print('  · 处理单位是否在捐赠者凸包内 —— 这决定该用哪种权重')
print('  · post 期是否有理由相信因子结构未变 —— 这是**制度知识**，与 DiD 的')
print('    平行趋势一样不可检验')"""),

md("""## ✏️ 练习 1：pre-trend 检验的功效

pre-trend 检验通过不代表平行趋势成立，部分原因是它的**功效不足**。
实现 `pretrend_power(amp, n_unit, seeds, alpha)`：给定处理前的趋势差 `amp`，
返回 pre-trend 检验拒绝的比例（即功效），以及此时 DiD 的平均偏差。"""),

code("""def pretrend_power(amp, n_unit=400, seeds=200, alpha=1.96):
    '''pre-trend 检验的功效 + 对应的 DiD 偏差。

    参数
    ----
    amp     : 处理组从 t=0 起的额外斜率（kind='pre_slope'）
    n_unit  : 单位数
    seeds   : 重复次数
    alpha   : |t| 的临界值（1.96 对应 5% 双侧）

    返回
    ----
    (power, did_bias) : 拒绝比例, DiD 平均偏差（相对真 tau=2.0）
    '''
    # TODO: 对 seed in range(seeds)，用
    #       panel(n_unit=n_unit, kind='pre_slope', amp=amp, seed=seed)
    #       算 pretrend_t 与 did；返回 (|t|>alpha 的比例, did 均值 - 2.0)
    raise NotImplementedError"""),

code("""# 自测
print('   amp    pre-trend 功效    DiD 偏差    偏差/功效 的处境')
_rows = []
for _amp in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5):
    _pw, _bs = pretrend_power(_amp)
    _rows.append((_amp, _pw, _bs))
    _note = ''
    if _pw < 0.5 and abs(_bs) > 0.15:
        _note = '  <- 偏差可观，但检验大概率放过'
    print(f'  {_amp:5.2f}      {_pw*100:6.1f}%       {_bs:+8.4f}   {_note}')

# amp=0 时功效 = 假阳性率，应接近 alpha 对应的 5%
_p0 = _rows[0][1]
assert _p0 < 0.12, f'amp=0 时拒绝率应接近 5%，得到 {_p0*100:.1f}%'
# 功效随 amp 单调上升
for _i in range(1, len(_rows)):
    assert _rows[_i][1] >= _rows[_i-1][1] - 0.02, f'功效应单调上升：{[r[1] for r in _rows]}'
# 存在「偏差明显但功效不足」的区间
_gap = [(a, p, b) for a, p, b in _rows if p < 0.6 and abs(b) > 0.15]
assert _gap, f'应存在偏差明显但功效不足的 amp，得到 {_rows}'

print()
print(f'✅ amp=0 时拒绝率 {_p0*100:.1f}%（≈ 名义 5%，检验校准正确）')
print(f'✅ 存在 {len(_gap)} 个 amp 值，DiD 偏差 > 0.15 而检验功效 < 60%:')
for _a, _p, _b in _gap:
    print(f'     amp={_a}: 偏差 {_b:+.4f}，检验只有 {_p*100:.0f}% 的概率拒绝')
print()
print('   -> 这是 Roth (2022) 的论点：在典型样本量下，一个足以让 DiD 严重有偏的')
print('      趋势差往往**不足以**被 pre-trend 检验拒绝。')
print('      所以「pre-trend 通过」的信息量比通常假设的低得多。')"""),

md("""## ✏️ 练习 2：从第一阶段 $F$ 预测 2SLS 的偏差

弱工具的偏差有一个经典近似：2SLS 相对 OLS 的偏差比例约为 $1/(F+1)$。
实现 `weak_iv_bias_ratio(pi, seeds)`，返回实测的偏差比例
$(\\text{med}_{2SLS} - \\beta)/(\\text{med}_{OLS} - \\beta)$ 与第一阶段 $F$ 中位数。"""),

code("""def weak_iv_bias_ratio(pi, seeds=2000, beta=1.0):
    '''2SLS 相对 OLS 的偏差比例 + 第一阶段 F 中位数。

    参数
    ----
    pi    : 工具强度
    seeds : 模拟次数
    beta  : 真效应

    返回
    ----
    (ratio, F_med) :
      ratio = (2SLS 中位数 - beta) / (OLS 中位数 - beta)
      F_med = 第一阶段 F 的中位数
    '''
    # TODO: 用 iv_sim(pi=pi, seed=s) 收集 (ols, tsls, F)；
    #       返回 ((median(tsls)-beta)/(median(ols)-beta), median(F))
    raise NotImplementedError"""),

code("""# 自测
print('    pi      F 中位数    实测偏差比例    1/(F+1) 近似    差')
_pairs = []
for _pi in (0.5, 0.2, 0.1, 0.05, 0.02, 0.005):
    _ratio, _F = weak_iv_bias_ratio(_pi)
    _approx = 1.0 / (_F + 1.0)
    _pairs.append((_pi, _F, _ratio, _approx))
    print(f'  {_pi:6.3f}   {_F:9.2f}      {_ratio:9.4f}      {_approx:9.4f}   '
          f'{abs(_ratio-_approx):.4f}')

# 强工具 -> 比例接近 0；弱工具 -> 比例接近 1
assert _pairs[0][2] < 0.05, f'F=250 时偏差比例应接近 0，得到 {_pairs[0][2]:.4f}'
assert _pairs[-1][2] > 0.9, f'F=0.5 时偏差比例应接近 1，得到 {_pairs[-1][2]:.4f}'
# 单调
for _i in range(1, len(_pairs)):
    assert _pairs[_i][2] > _pairs[_i-1][2] - 0.02, \\
        f'偏差比例应随 F 下降而单调上升：{[round(p[2],4) for p in _pairs]}'
# 1/(F+1) 在两端的量级正确
assert abs(_pairs[0][3] - _pairs[0][2]) < 0.05, '强工具端近似应吻合'
assert _pairs[-1][3] > 0.5, '弱工具端 1/(F+1) 应给出「接近 OLS」的预警'

print()
print(f'✅ 偏差比例从 {_pairs[0][2]:.4f}（F={_pairs[0][1]:.0f}）单调升到 '
      f'{_pairs[-1][2]:.4f}（F={_pairs[-1][1]:.2f}）')
print('✅ 1/(F+1) 在两端都给出正确的量级 —— 这就是 F>10 规则的定量依据：')
print(f'   F=10 时 1/(F+1) ≈ {1/11:.3f}，即 2SLS 仍带有 OLS 偏差的约 9%')
print()
print('   注意中间几档的吻合度不高（差最大 '
      f'{max(abs(p[2]-p[3]) for p in _pairs):.3f}）：')
print('   1/(F+1) 是一个量级近似，不是精确公式。它的用途是**报警**，不是**校正**。')"""),

md("""## ✏️ 练习 3：RDD 的两侧曲率诊断

正文说「两侧的非线性方式不同才是危险信号，而后者可以部分诊断」。
实现 `curvature_asymmetry(x, Y, h)`：分别在阈值两侧拟合二次多项式，
返回两侧二阶项系数的差、以及这个差相对其标准误的 $t$ 值。"""),

code("""def curvature_asymmetry(x, Y, h=0.5):
    '''两侧二阶项系数之差与它的 t 值。

    分别在 [0, h) 与 (-h, 0] 上拟合 y = a + b*x + c*x^2，
    返回 (c_right - c_left, t 值)。

    t 值用两侧 OLS 的系数标准误合成：se = sqrt(se_r^2 + se_l^2)。

    参数
    ----
    x, Y : 数据
    h    : 用于诊断的带宽

    返回
    ----
    (diff, t) : 二阶项之差，以及它的 t 值
    '''
    # TODO: 两侧各做一次二次 OLS。系数协方差用
    #       sigma^2 * inv(A.T @ A)，sigma^2 = RSS/(n-3)。
    #       取第 3 个对角元的平方根为该侧的 se。
    raise NotImplementedError"""),

code("""# 自测
print('  数据         二阶项之差    t 值      结论')
_diag = {}
for _mode, _tag in [('sym', '对称曲率'), ('asym', '不对称曲率')]:
    _ds, _ts = [], []
    for _s in range(30):
        _x, _Y = rdd_data(seed=_s, mode=_mode)
        _d, _t = curvature_asymmetry(_x, _Y, h=0.5)
        _ds.append(_d); _ts.append(_t)
    _diag[_mode] = (float(np.mean(_ds)), float(np.mean(_ts)))
    _verdict = '两侧曲率相同' if abs(np.mean(_ts)) < 1.96 else '两侧曲率**不同** -> RDD 有偏风险'
    print(f'  {_tag:12s}  {np.mean(_ds):+10.4f}   {np.mean(_ts):+7.2f}   {_verdict}')

# 对称数据：二阶项之差应接近 0
assert abs(_diag['sym'][0]) < 0.15, f'对称时二阶项之差应接近 0，得到 {_diag["sym"][0]:.4f}'
assert abs(_diag['sym'][1]) < 1.96, f'对称时 t 值应不显著，得到 {_diag["sym"][1]:.2f}'
# 不对称数据：真差是 2.0 - (-0.5) = 2.5
assert abs(_diag['asym'][0] - 2.5) < 0.4, \\
    f'不对称时二阶项之差应约 2.5，得到 {_diag["asym"][0]:.4f}'
assert abs(_diag['asym'][1]) > 1.96, f'不对称时 t 值应显著，得到 {_diag["asym"][1]:.2f}'

print()
print(f'✅ 对称数据: 差 {_diag["sym"][0]:+.4f}, t={_diag["sym"][1]:+.2f} -> 检验不拒绝（正确）')
print(f'✅ 不对称数据: 差 {_diag["asym"][0]:+.4f}（真值 2.0-(-0.5)=2.5）, '
      f't={_diag["asym"][1]:+.2f} -> 检验拒绝（正确）')
print()
print('   -> 这个诊断能区分「RDD 有偏」与「结果只是非线性」，')
print('      而单看「结果对分数非线性」两种情形都会告警。')
print('   -> 但它仍然是一个**统计检验**，所以和 pre-trend 一样只能证伪：')
print('      不拒绝不等于两侧形状相同（练习 1 已经量过这类检验的功效问题）。')"""),

md("""## ✏️ 练习 4：合成控制该报告哪些量

实现 `sc_report(Y, n_pre, mode)`，返回一份包含四个量的报告：
`est`（效应估计）、`pre_rmse`、`sum_abs_w`（外推程度）、
`in_hull`（处理单位的 pre 期轨迹是否在捐赠者凸包内）。

`in_hull` 用一个可判定的代理：单纯形拟合的 pre 期 RMSE 是否与
无约束拟合的 pre 期 RMSE 处于同一量级（比值 $< 3$）。"""),

code("""def sc_report(Y, n_pre, mode='simplex', hull_ratio=3.0):
    '''合成控制的四量报告。

    参数
    ----
    Y          : (J+1, T) 面板，第 0 行是处理单位
    n_pre      : pre 期长度
    mode       : 'simplex' 或 'ols'
    hull_ratio : 判定 in_hull 的比值阈值

    返回
    ----
    dict : {'est', 'pre_rmse', 'sum_abs_w', 'in_hull', 'hull_ratio_obs'}
      in_hull = (单纯形 pre RMSE / 无约束 pre RMSE) < hull_ratio
    '''
    # TODO: 分别用 sc_fit(Y, n_pre, 'simplex') 与 sc_fit(Y, n_pre, 'ols')；
    #       用 mode 对应的那组填 est/pre_rmse/sum_abs_w；
    #       用两者的 pre RMSE 比值判 in_hull
    raise NotImplementedError"""),

code("""# 自测
# ① 比值在两类上的分布 —— 先看它们是否可分
_IN, _OUT = [], []
for _s in range(60):
    for _kw, _box in [(dict(in_hull=True), _IN), (dict(in_hull=False), _OUT)]:
        _Y, _np_ = sc_data(seed=_s, **_kw)
        _box.append(sc_report(_Y, _np_)['hull_ratio_obs'])
_IN, _OUT = np.array(_IN), np.array(_OUT)
print(f'真凸包内的比值: 中位 {np.median(_IN):5.2f}  区间 [{_IN.min():.2f}, {_IN.max():.2f}]')
print(f'真凸包外的比值: 中位 {np.median(_OUT):5.2f}  区间 [{_OUT.min():.2f}, {_OUT.max():.2f}]')
_overlap = float(np.mean((_OUT >= _IN.min()) & (_OUT <= _IN.max())))
print(f'-> 两个区间**重叠**：{_overlap*100:.0f}% 的真凸包外样本落在真凸包内的取值区间里')
assert np.median(_OUT) > 3 * np.median(_IN), '中位数应差 3 倍以上（信号是有的）'
assert _overlap > 0.1, '但分布确实重叠'

# ② 扫阈值：有没有一个阈值能两头都干净
print()
print(' 阈值   真凸包内被判内(TPR)   真凸包外被误判内(FPR)   总错误率')
_best = None
for _thr in (1.5, 1.8, 2.0, 2.2, 2.5, 3.0, 4.0, 5.0, 8.0):
    _tpr, _fpr = float(np.mean(_IN < _thr)), float(np.mean(_OUT < _thr))
    _err = (1 - _tpr) + _fpr
    if _best is None or _err < _best[1]:
        _best = (_thr, _err, _tpr, _fpr)
    print(f' {_thr:4.1f}       {_tpr*100:6.1f}%              {_fpr*100:6.1f}%          {_err:.3f}')

print()
print(f'最优阈值 {_best[0]}: TPR {_best[2]*100:.1f}%, FPR {_best[3]*100:.1f}%, '
      f'总错误率 {_best[1]:.3f}')
assert _best[3] > 0.05, f'最优阈值下 FPR 仍 > 5%，得到 {_best[3]*100:.1f}%'
assert not any(np.mean(_IN < t) > 0.95 and np.mean(_OUT < t) < 0.05
               for t in np.linspace(1.0, 10.0, 91)), \\
    '不应存在同时满足 TPR>95% 与 FPR<5% 的阈值'

print()
print('✅ 没有任何阈值能同时做到 TPR>95% 与 FPR<5%。')
print('   原因不是判据不好，是**「在凸包内」本身是程度问题，不是二元的**：')
print('   本设定里「凸包外」的载荷是 N(0,1)*2 随机抽的，有时会碰巧落在凸包附近。')

# ③ 但它作为**排序**信号是可用的：报告比值本身而不是布尔值
print()
print('  情形                  比值中位   Σ|w|(单纯形/无约束)   该用哪种权重')
for _tag, _kw, _use in [('凸包内 / 因子稳定', dict(in_hull=True), '单纯形'),
                        ('凸包外 / 因子稳定', dict(in_hull=False), '无约束'),
                        ('凸包内 + post 新因子', dict(in_hull=True, extra_factor=1.0), '单纯形'),
                        ('凸包外 + post 新因子', dict(in_hull=False, extra_factor=1.0), '无约束')]:
    _rs, _ws, _wo = [], None, None
    for _s in range(20):
        _Y, _np_ = sc_data(seed=_s, **_kw)
        _r = sc_report(_Y, _np_, 'simplex'); _ro = sc_report(_Y, _np_, 'ols')
        _rs.append(_r['hull_ratio_obs']); _ws, _wo = _r['sum_abs_w'], _ro['sum_abs_w']
    print(f'  {_tag:22s} {np.median(_rs):8.2f}   {_ws:.2f} / {_wo:.2f}'
          f'              {_use}')

print()
print('⚠️  注意比值与「因子结构是否稳定」是**独立**的两件事：')
print('   第 1、3 行的比值中位数几乎相同，而它们的 post RMSE 相差 4 倍。')
print('   四量报告能给出外推程度和凸包位置的**程度**，**不能**告诉你因子会不会变。')
print('   后者只能靠制度知识 —— 与 DiD 的平行趋势同性质。')
print()
print('工程含义：报告 hull_ratio_obs 这个**连续量**，不要报 in_hull 这个布尔值。')
print('  把一个程度问题二值化，只是把不确定性藏进了一个看起来确定的字段里。')"""),

md("""## 📖 参考答案"""),

code("""def pretrend_power(amp, n_unit=400, seeds=200, alpha=1.96):
    '''pre-trend 检验的功效 + 对应的 DiD 偏差。'''
    rej, bias = [], []
    for s in range(seeds):
        Y, tr, npre = panel(n_unit=n_unit, kind='pre_slope', amp=amp, seed=s)
        rej.append(abs(pretrend_t(Y, tr, npre)) > alpha)
        bias.append(did(Y, tr, npre))
    return float(np.mean(rej)), float(np.mean(bias) - 2.0)

def weak_iv_bias_ratio(pi, seeds=2000, beta=1.0):
    '''2SLS 相对 OLS 的偏差比例 + 第一阶段 F 中位数。'''
    rr = np.array([iv_sim(pi=pi, seed=s) for s in range(seeds)])
    med_ols = float(np.median(rr[:, 0]))
    med_tsls = float(np.median(rr[:, 1]))
    return (med_tsls - beta) / (med_ols - beta), float(np.median(rr[:, 2]))

def curvature_asymmetry(x, Y, h=0.5):
    '''两侧二阶项系数之差与它的 t 值。'''
    out = []
    for sel in ((x >= 0) & (x < h), (x < 0) & (x > -h)):
        xs, ys = x[sel], Y[sel]
        A = np.column_stack([np.ones(len(xs)), xs, xs**2])
        beta = lstsq(A, ys)
        rss = float(np.sum((A @ beta - ys)**2))
        s2 = rss / (len(xs) - 3)
        cov = s2 * np.linalg.inv(A.T @ A)
        out.append((float(beta[2]), float(np.sqrt(cov[2, 2]))))
    diff = out[0][0] - out[1][0]
    se = float(np.sqrt(out[0][1]**2 + out[1][1]**2))
    return diff, diff / se

def sc_report(Y, n_pre, mode='simplex', hull_ratio=3.0):
    '''合成控制的四量报告。'''
    e_s, p_s, w_s = sc_fit(Y, n_pre, 'simplex')
    e_o, p_o, w_o = sc_fit(Y, n_pre, 'ols')
    ratio = p_s / max(p_o, 1e-12)
    est, pre, sw = (e_s, p_s, w_s) if mode == 'simplex' else (e_o, p_o, w_o)
    return {'est': est, 'pre_rmse': pre, 'sum_abs_w': sw,
            'in_hull': bool(ratio < hull_ratio), 'hull_ratio_obs': float(ratio)}

print('参考答案已定义。')
print()
print('要点：')
print('  1. pre-trend 检验在 amp=0 时校准正确（拒绝率≈5%），')
print('     但在「偏差已经可观」的区间功效不足 —— 通过不等于成立。')
print('  2. 1/(F+1) 是弱工具偏差的量级近似：用途是报警，不是校正。')
print('  3. 两侧曲率的 t 检验能区分「RDD 有偏」与「结果只是非线性」，')
print('     但它和 pre-trend 一样只能证伪。')
print('  4. 合成控制的四量报告覆盖外推程度与凸包位置，')
print('     **不覆盖**因子结构是否稳定 —— 后者不可检验。')"""),

md("""## 🧪 真实工程胶囊：准实验的事前登记模板

模块 03 的四个诊断量在本模块全部失效——它们检测「估计有没有算好」，
而本模块的失效在「识别有没有成立」这一层。

所以准实验的质量保证必须是**设计层面**的。下面这段代码把它做成一个
可执行的事前登记（pre-registration）：在看到结果之前就把
方法、假设、诊断、以及**诊断失败时怎么办**写下来，然后由代码检查
事后的分析是否偏离了登记。

关键是最后一条：`on_fail` 必须在事前填写。
如果一个诊断失败后的处理方式是事后决定的，那么这个诊断
就退化成了一次搜索——而搜索出来的显著性没有意义。"""),

code("""REGISTRY = {
    'did': {
        'assumption': '平行趋势：处理组若未处理，趋势与对照组相同',
        'testable': '仅处理前的部分',
        'diagnostics': ['pretrend_t', 'event_study_pre_max'],
        'thresholds': {'pretrend_t': 1.96, 'event_study_pre_max': 0.2},
        'on_fail': '不改方法、不改窗口；改为报告「趋势差无法排除」并给出敏感性区间',
        'not_testable': '处理后本会不会平行 —— 靠制度知识论证处理时点的外生性',
    },
    'iv': {
        'assumption': '外生性 + 排他性 + 相关性',
        'testable': '仅相关性（第一阶段 F）',
        'diagnostics': ['first_stage_F', 'bias_ratio_approx'],
        'thresholds': {'first_stage_F': 10.0, 'bias_ratio_approx': 0.1},
        'on_fail': '放弃 2SLS；不做「换个工具再试」（那是搜索）',
        'not_testable': '外生性与排他性 —— 且弱工具的失效是静默的（退回 OLS）',
    },
    'rdd': {
        'assumption': '结果函数在阈值处连续',
        'testable': '密度检验、协变量跳变、两侧曲率对称性',
        'diagnostics': ['curvature_t', 'bandwidth_sensitivity'],
        'thresholds': {'curvature_t': 1.96, 'bandwidth_sensitivity': 0.15},
        'on_fail': '缩小带宽至诊断通过；带宽选择规则**事前**写定，不事后调',
        'not_testable': '阈值处是否有其他规则同时生效',
    },
    'sc': {
        'assumption': '因子结构在 pre/post 之间稳定',
        'testable': '外推程度 Σ|w|、凸包位置',
        'diagnostics': ['sum_abs_w', 'in_hull'],
        'thresholds': {'sum_abs_w': 2.0},
        'on_fail': '换权重方案（凸包外用无约束），并报告 Σ|w|',
        'not_testable': '因子结构是否稳定 —— pre 期拟合优度**不是**它的证据',
    },
}

def check_registration(method, observed):
    '''对照事前登记检查一次分析。返回 (是否可作为主结论, 说明列表)。'''
    reg = REGISTRY[method]
    notes, failed = [], []
    print(f'方法: {method}')
    print(f'  核心假设:   {reg["assumption"]}')
    print(f'  可检验部分: {reg["testable"]}')
    print(f'  不可检验:   {reg["not_testable"]}')
    print('  诊断:')
    for d in reg['diagnostics']:
        if d not in observed:
            notes.append(f'{d}: 未提供 -> 视为未通过')
            failed.append(d)
            print(f'    [MISS] {d:26s} 未提供')
            continue
        v = observed[d]
        thr = reg['thresholds'].get(d)
        if thr is None:
            print(f'    [INFO] {d:26s} {v}')
            continue
        # first_stage_F 是「越大越好」，其余是「越小越好」
        ok = (v >= thr) if d == 'first_stage_F' else (abs(v) <= thr)
        print(f'    [{"OK  " if ok else "FAIL"}] {d:26s} {v:>10} (阈值 {thr})')
        if not ok:
            failed.append(d)
    print(f'  诊断失败时的处理（事前登记）: {reg["on_fail"]}')
    primary = not failed
    print(f'  -> {"可作为主结论" if primary else "不可作为主结论；按登记的 on_fail 处理"}')
    print()
    return primary, failed

print('=== 用本模块的实际数值走一遍 ===')
print()

# DiD：「只在处理后分叉」那个情形 —— 诊断全部通过，而 DiD 偏 +1.25
_Yp, _trp, _npp = panel(kind='post_only', amp=0.5, seed=0)
_ok_did, _f_did = check_registration('did', {
    'pretrend_t': round(pretrend_t(_Yp, _trp, _npp), 3),
    'event_study_pre_max': round(float(np.abs(event_study(_Yp, _trp, _npp)[:_npp]).max()), 3),
})
assert _ok_did, '这个情形的诊断确实全部通过 —— 这正是要展示的问题'
print(f'  ⚠️  但这个情形的 DiD 估计是 {did(_Yp, _trp, _npp):+.4f}，真值 2.0。')
print('      诊断全部通过，结论仍然错 —— 因为不可检验的那一半不成立。')
print('      这不是登记模板的失败：模板已经把「不可检验」写在纸上了。')
print()

# IV：弱工具
_rr = np.array([iv_sim(pi=0.02, seed=s) for s in range(500)])
_Fmed = float(np.median(_rr[:, 2]))
_ok_iv, _f_iv = check_registration('iv', {
    'first_stage_F': round(_Fmed, 2),
    'bias_ratio_approx': round(1.0 / (_Fmed + 1.0), 3),
})
assert not _ok_iv and 'first_stage_F' in _f_iv, '弱工具应被登记模板拦住'

# RDD：不对称曲率
_x, _Y = rdd_data(seed=0, mode='asym')
_d, _t = curvature_asymmetry(_x, _Y, h=0.5)
_h_sens = abs(rdd_local(_x, _Y, 0.2)[0] - rdd_local(_x, _Y, 0.7)[0])
_ok_rdd, _f_rdd = check_registration('rdd', {
    'curvature_t': round(_t, 2),
    'bandwidth_sensitivity': round(_h_sens, 3),
})
assert not _ok_rdd, '不对称曲率应被拦住'

# 合成控制：凸包外
_Ys, _nps = sc_data(seed=0, in_hull=False)
_rep = sc_report(_Ys, _nps, 'ols')
_ok_sc, _f_sc = check_registration('sc', {
    'sum_abs_w': round(_rep['sum_abs_w'], 2),
    'in_hull': _rep['in_hull'],
})
assert not _ok_sc, '凸包外的大幅外推应被拦住'

print('=== 四次检查的结果 ===')
print(f'  DiD  可作主结论: {_ok_did}   （诊断通过，但结论仍错 —— 见上）')
print(f'  IV   可作主结论: {_ok_iv}   失败项: {_f_iv}')
print(f'  RDD  可作主结论: {_ok_rdd}   失败项: {_f_rdd}')
print(f'  SC   可作主结论: {_ok_sc}   失败项: {_f_sc}')
print()
print('工程含义：')
print('  · 模板拦住了 3/4 个已知有问题的分析，而 DiD 那个它拦不住 ——')
print('    因为那个问题在不可检验的那一半里。模板的价值是把这件事**写在纸上**，')
print('    让结论的措辞必须带上限定，而不是假装诊断通过就等于识别成立。')
print('  · on_fail 必须事前填写。诊断失败后的处理方式如果是事后决定的，')
print('    这个诊断就退化成一次搜索 —— 搜索出来的显著性没有意义。')
print('  · 这份登记本身应该进版本库，和模块 02 的 DAG 一样接受 review。')"""),
]
