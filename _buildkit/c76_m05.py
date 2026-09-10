# -*- coding: utf-8 -*-
"""C76 模块 05 · 线上归因：SUTVA 与干扰、集群随机化、多触点归因、代理指标。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（SUTVA、目标量的选择）；模块 00 第 4 节的四个预演；"
                 "<strong>C10 模块 07（A/B 统计工具箱）</strong>——"
                 "本模块处理的是「那套统计全都做对了，但测的不是你要的量」的情形"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_online_attribution.ipynb'
                       '（<strong>个体随机化测到 $1.00$，全局效应是 $2.00$</strong>——'
                       '漏掉一半且无任何统计告警 / '
                       '<strong>设计效应 $1+(m-1)\\text{ICC}$ 验证到 $1.6\\%$</strong>'
                       '（$m{=}50$, ICC$=0.2$ 时实测 $10.97$ vs 理论 $10.80$）/ '
                       '<strong>last-touch 把真实份额 $7.1\\%$ 的渠道记成 $38.0\\%$</strong>'
                       '（高估 $5.4$ 倍），而转化只取决于曝光<em>集合</em> / '
                       '代理指标在有直接通道时<strong>符号反转</strong>）'),
    ("核心参考", "Rubin, <em>Comment: Which Ifs Have Causal Answers</em>（JASA 1986，SUTVA）· "
                 "Ugander, Karrer, Backstrom &amp; Kleinberg, <em>Graph Cluster "
                 "Randomization</em>（KDD 2013）· "
                 "Bojinov, Simchi-Levi &amp; Zhao, <em>Design and Analysis of Switchback "
                 "Experiments</em>（Management Science 2023）· "
                 "Shapley, <em>A Value for n-Person Games</em>（1953）· "
                 "Athey, Chetty, Imbens &amp; Kang, <em>The Surrogate Index</em>"
                 "（NBER w26463, 2019）· "
                 "Kohavi, Tang &amp; Xu, <em>Trustworthy Online Controlled Experiments</em>（2020）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [

("frame", "实验有效，而测的不是你要的量", "".join([
    P("前四个模块都在处理「随机化不可得」。本模块回到<strong>随机化完全有效</strong>的情形，"
      "处理另一类失效：分桶正确、$p$ 值正确、功效充足、CUPED 也上了——"
      "而<strong>估计出来的量不是决策需要的那个量</strong>。"),
    TABLE(["失效", "被违反的假设", "本课量出的代价", "会不会报错"],
          [["干扰 / 溢出", "SUTVA 的无干扰部分", "测到 $1.00$，全局效应 $2.00$", "不会"],
           ["集群随机化的代价", "（没被违反，是主动付出的）",
            "$m{=}50$, ICC$=0.2$ 时方差涨 $10.97$ 倍", "不会"],
           ["归因规则", "规则本身没有因果目标",
            "真实份额 $7.1\\%$ 被记成 $38.0\\%$", "不会"],
           ["代理指标", "替代性（无绕过 $S$ 的直接通道）",
            "短期 $+1.005$，长期 $-0.999$（<strong>符号反转</strong>）", "不会"]]),
    CALLOUT("intuition", "为什么这一类最危险",
            "前四个模块的失效至少有<em>诊断量</em>可看（ESS、pre-trend、第一阶段 $F$）。"
            "本模块的四种失效都<strong>不产生任何异常统计量</strong>："
            "实验是干净的，统计是对的，数字是稳定的、可复现的、置信区间很窄的。"
            "唯一的防线是在设计阶段就问：<strong>「我测的这个量，"
            "和我要做的这个决策，是同一个量吗」</strong>。"),
])),

("interference", "干扰：个体随机化测的是直接效应", "".join([
    P("SUTVA 要求 $Y_i(t)$ 不依赖别人的处理。"
      "社交产品、共享库存、竞价市场、双边平台全都违反它。"),
    P("notebook 用一个环形图（每人 $10$ 个邻居），"
      "效用 $Y_i = 1.0 \\cdot T_i + 1.0 \\cdot (\\text{邻居处理比例}) + \\varepsilon$。"
      "决策关心的是<strong>全局效应</strong>：全开 vs 全关 $= 1.0 + 1.0 = 2.0$。"),
    TABLE(["设计", "A/B 估计", "与目标 $2.00$ 的偏差", "两臂的邻居暴露差"],
          [["个体随机化", "$\\mathbf{+1.0026}$", "$\\mathbf{-0.9974}$", "$+0.0016$"],
           ["集群随机化 $m{=}20$", "$+1.8485$", "$-0.1515$", "$+0.8490$"],
           ["集群随机化 $m{=}100$", "$+1.9674$", "$-0.0326$", "$+0.9691$"],
           ["集群随机化 $m{=}500$", "$+1.9965$", "$-0.0035$", "$+0.9936$"]]),
    P("个体随机化下两臂的邻居处理比例都约等于 $p = 0.5$，"
      "所以溢出项在相减时<strong>完全抵消</strong>——测到的恰好是直接效应 $1.0$。"
      "<strong>漏掉了 $50\\%$ 的效应，而没有任何统计告警</strong>。"),
    DUAL("直观地说：如果每个人的邻居里都有一半开了新功能，"
         "那么处理组和对照组的人「周围的世界」是一样的。"
         "两组之差只反映「自己有没有开」，"
         "而全量上线时「周围的世界」也会变——那部分完全测不到。",
         "记 $Y_i = \\alpha T_i + \\beta \\bar{T}_{N(i)} + \\varepsilon_i$。"
         "个体随机化下 $E[\\bar{T}_{N(i)} \\mid T_i{=}1] = "
         "E[\\bar{T}_{N(i)} \\mid T_i{=}0] = p$（因为邻居的指派与自己独立），"
         "故 $E[\\hat{\\tau}_{AB}] = \\alpha$。"
         "而全局效应是 $\\alpha + \\beta$。"
         "集群随机化让 $\\bar{T}_{N(i)}$ 与 $T_i$ 高度相关，"
         "暴露差趋于 $1$，估计趋于 $\\alpha + \\beta$。"),
    P("注意这里漏掉的比例恰好是 $\\beta/(\\alpha+\\beta)$，"
      "所以<strong>溢出越强，个体随机化漏得越多</strong>，"
      "而这个比例与样本量、检验方法、方差缩减技术全都无关。"),
])),

("cluster", "集群随机化的价格：设计效应", "".join([
    P("集群随机化把干扰的偏差换成方差。这个交换的价格有闭式解——"
      "<strong>设计效应</strong>（design effect）"),
    MATH("\\text{DE} = 1 + (m-1)\\,\\text{ICC}"),
    P("其中 $m$ 是集群大小，ICC（组内相关系数）是结果方差中<em>组间</em>成分的占比。"
      "notebook 在总方差固定为 $1$ 的合成数据上验证（$n{=}6000$，$4000$ seeds）："),
    TABLE(["$m$", "ICC", "个体随机化方差", "集群随机化方差", "实测比", "理论 DE", "相对误差"],
          [["$5$", "$0.20$", "$6.71\\times10^{-4}$", "$1.21\\times10^{-3}$", "$1.80$",
            "$1.80$", "$0.1\\%$"],
           ["$10$", "$0.20$", "$6.56\\times10^{-4}$", "$1.89\\times10^{-3}$", "$2.88$",
            "$2.80$", "$3.0\\%$"],
           ["$50$", "$0.05$", "$6.85\\times10^{-4}$", "$2.33\\times10^{-3}$", "$3.40$",
            "$3.45$", "$1.5\\%$"],
           ["$50$", "$0.20$", "$6.83\\times10^{-4}$", "$7.50\\times10^{-3}$",
            "$\\mathbf{10.97}$", "$\\mathbf{10.80}$", "$1.6\\%$"],
           ["$50$", "$0.50$", "$6.81\\times10^{-4}$", "$1.79\\times10^{-2}$", "$26.28$",
            "$25.50$", "$3.1\\%$"]]),
    P("$m{=}50$、ICC$=0.2$ 时方差涨约 $\\mathbf{11}$ 倍，"
      "等价于<strong>样本量缩小到 $1/11$</strong>。"
      "所以「用集群随机化解决干扰」不是一个免费的修正，"
      "而是一次必须显式做出的取舍：<strong>干扰的偏差 vs 集群的方差</strong>。"),
    H3("怎么选集群大小"),
    P("上一节的表给出了偏差侧：$m{=}20$ 时残余偏差 $-0.15$、$m{=}100$ 时 $-0.03$、"
      "$m{=}500$ 时 $-0.004$。本节给出方差侧：$\\text{DE} = 1 + (m-1)\\text{ICC}$。"
      "两者相乘就是 MSE，于是<strong>集群大小有内点最优</strong>。"
      "notebook 在 ICC$=0.2$、效应尺度 $2.0$ 下算出这条曲线，最优是 "
      "<strong>$m^{*} = 50$</strong>（MSE $0.0113$）："
      "$m{=}1$ 的 MSE 是 $0.9997$（偏差主导，漏掉 $50\\%$ 的效应），"
      "$m{=}1000$ 是 $0.1366$（方差主导，DE $= 201$）。"
      "练习 1 会验证<strong>最优集群大小随 ICC 增大而单调变小</strong>。"),
    CALLOUT("warn", "ICC 必须先估出来，而它常被低估",
            "ICC 是集群划分方式的函数，不是数据的固有属性。"
            "按地理分的集群、按社交社区分的集群、按时间片分的集群，ICC 完全不同。"
            "工程上常见的错误是用<em>历史 A/B 的方差</em>去做功效计算，"
            "而那个方差是<strong>个体随机化</strong>下的——"
            "直接用它规划集群实验会把所需样本量低估 $\\text{DE}$ 倍。"),
    H3("switchback：把集群建在时间上"),
    P("当干扰是通过<em>共享资源</em>（库存、司机、算力）发生时，"
      "空间上的集群化不管用——供给池是全局的。"
      "此时的办法是 <strong>switchback</strong>：把时间切成片，整片随机分配处理。"
      "它的设计效应形式相同，只是 ICC 变成<em>时间</em>自相关，"
      "而额外多了一个偏差来源：<strong>切换点附近的残留</strong>（carryover）。"
      "实践上的处理是丢弃切换后的一段（burn-in），代价是有效样本进一步减少。"),
])),

("attribution", "多触点归因：规则本身没有因果目标", "".join([
    P("归因（attribution）问的是「这次转化该记谁的功劳」。"
      "这个问题看起来像因果问题，但常用的规则——last-touch、first-touch、"
      "均分、时间衰减——<strong>全都不是因果估计量</strong>：它们是<em>会计规则</em>。"),
    P("notebook 构造一个真值明确的场景。转化概率<strong>只取决于曝光集合</strong>"
      "（次可加：$p = 1 - \\prod_{c \\in S}(1 - b_c)$），"
      "与曝光<em>顺序</em>完全无关。因果贡献用 Shapley 值定义"
      "（它满足有效性公理：各渠道之和 $=$ 全触点转化概率 $0.5212$）："),
    TABLE(["渠道", "单独效果 $b_c$", "Shapley 值", "Shapley 真实份额",
           "last-touch", "first-touch", "均分", "时间衰减"],
          [["搜索", "$0.30$", "$0.2509$", "$\\mathbf{48.1\\%}$", "$8.7\\%$", "$75.4\\%$",
            "$35.2\\%$", "$23.1\\%$"],
           ["社交", "$0.20$", "$0.1583$", "$30.4\\%$", "$13.7\\%$", "$18.7\\%$",
            "$24.3\\%$", "$21.3\\%$"],
           ["邮件", "$0.05$", "$0.0368$", "$\\mathbf{7.1\\%}$", "$\\mathbf{38.0\\%}$",
            "$4.6\\%$", "$25.2\\%$", "$31.4\\%$"],
           ["直达", "$0.10$", "$0.0753$", "$14.4\\%$", "$39.6\\%$", "$1.3\\%$",
            "$15.3\\%$", "$24.1\\%$"]]),
    P("<strong>邮件的真实份额是 $7.1\\%$，last-touch 记它 $38.0\\%$——高估 $5.4$ 倍</strong>。"
      "而搜索的真实份额 $48.1\\%$ 被 last-touch 记成 $8.7\\%$——低估 $5.6$ 倍。"
      "原因很简单：邮件在这个 DGP 里倾向于最后曝光（再营销）。"),
    TABLE(["规则", "相对 Shapley 真值的最大绝对份额误差"],
          [["last-touch", "$\\mathbf{39.5}$ pp"],
           ["first-touch", "$27.2$ pp"],
           ["均分", "$18.1$ pp"],
           ["时间衰减", "$25.0$ pp"]]),
    P("notebook 把这一点做成了一个直接的实验：只把渠道的曝光<strong>时序</strong>反转"
      "（曝光概率与转化机制一个字节都没改）——"),
    TABLE(["时序", "搜索的 last-touch 份额", "邮件的 last-touch 份额", "转化率"],
          [["原时序", "$8.7\\%$", "$38.0\\%$", "$30.88\\%$"],
           ["反转时序", "$\\mathbf{75.4\\%}$", "$\\mathbf{4.6\\%}$", "$\\mathbf{30.88\\%}$"]]),
    P("<strong>转化率一位有效数字都没变</strong>（真实贡献当然没变），"
      "而搜索的 last-touch 份额变了 <strong>$66.7$ 个百分点</strong>。"
      "反转后的数字恰好等于 first-touch 的那一列（$75.4\\%$ / $4.6\\%$）——"
      "这正说明这两个「规则」的差别只是<em>读哪一端</em>，与因果无关。"
      "Shapley 值则完全不变，因为它只依赖 $v(S)$。"),
    CALLOUT("danger", "这不是估计误差",
            "在这个 DGP 里转化概率<strong>可以被证明</strong>与顺序无关"
            "（notebook 里 $v(\\{\\text{搜索},\\text{邮件}\\})$ 与 "
            "$v(\\{\\text{邮件},\\text{搜索}\\})$ 逐位相同）。"
            "所以任何基于顺序的规则都是<em>无信息</em>的——"
            "它的输出完全由「渠道的曝光顺序分布」决定，"
            "而那是一个可以被运营策略改变的量。"
            "换句话说：<strong>调整投放时序就能改变账面归因，"
            "而真实的因果贡献一点没变</strong>。"),
    H3("那该怎么做"),
    OL(["<strong>能做实验就做实验</strong>：对某个渠道做增量实验（geo holdout、"
        "用户级 holdout），直接估它的增量效应。这是唯一无争议的做法。",
        "<strong>做不了实验时，用 Shapley 值而不是顺序规则</strong>："
        "Shapley 需要「去掉某个渠道后的转化率」，"
        "这可以从历史上的自然变动或分渠道的曝光缺失中估计。"
        "代价是 $2^k$ 的组合数与更强的建模假设。",
        "<strong>Markov 链归因</strong>（用移除效应 removal effect）是 Shapley 的一个"
        "近似实现，计算上便宜，但它把路径建成一阶马尔可夫链——"
        "这个假设本身需要检验。",
        "<strong>不要把顺序规则的输出当作预算分配依据</strong>。"
        "如果它已经是既有流程，至少同时报告 Shapley 版本的差距"
        "（本例是 $39.5$ 个百分点）。"]),
])),

("surrogate", "代理指标：可以在符号上骗你", "".join([
    P("长期指标（留存、LTV）要等几个月，而决策不能等。"
      "标准做法是找一个短期<strong>代理指标</strong> $S$，"
      "在历史实验里学 $h(S) = E[Y \\mid S]$，"
      "然后用 $h$ 把当期实验的 $\\Delta S$ 折算成 $\\Delta Y$ 的预测。"
      "这个做法要求<strong>替代性</strong>（surrogacy）："
      "$T$ 对 $Y$ 没有绕过 $S$ 的直接效应。"),
    ASCII("""
       替代性成立:                    替代性失效:
                                      +-------- d -------+
                                      |                  v
         T ----> S ----> Y             T ----> S ----> Y
                                       只有经过 S 的那部分
         代理指标能看见全部效应          能被代理指标看见
""".strip("\n")),
    TABLE(["当期实验参数", "短期 $\\Delta S$", "代理指标预测 $\\Delta Y$",
           "真实长期 $\\Delta Y$", "预测误差"],
          [["$d{=}0$（替代性成立）", "$+1.005$", "$+1.005$", "$+1.001$", "$+0.004$"],
           ["$d{=}+1$（有直接通道）", "$+1.005$", "$+1.005$", "$+2.001$", "$-0.995$"],
           ["<strong>$d{=}-2$（反向直接通道）</strong>", "$+1.005$", "$+1.005$",
            "$\\mathbf{-0.999}$", "$\\mathbf{+2.005}$"],
           ["$a{=}2$（代理放大 $2\\times$）", "$+2.005$", "$+2.005$", "$+2.001$", "$+0.004$"],
           ["$a{=}0, d{=}+1$（代理毫无变化）", "$-0.002$", "$-0.002$", "$+1.001$", "$-1.003$"]]),
    P("第三行是最危险的：短期代理<strong>上涨</strong> $+1.005$，"
      "代理指标据此预测长期 $+1.005$，而<strong>真实长期效应是 $-0.999$</strong>——"
      "符号完全反了，而且没有任何告警。"),
    P("第五行是另一种失效方向：代理指标毫无变化（预测 $-0.002$），"
      "而真实长期效应是 $+1.001$。"
      "<strong>代理指标只能看见「经过 $S$ 的那部分」</strong>，"
      "绕过 $S$ 的通道它完全看不见。"),
    H3("替代性可以被部分检验"),
    P("在<strong>已经有长期结果</strong>的历史实验里，回归 $Y \\sim T + S$："
      "若替代性成立，$T$ 在控制 $S$ 后的系数应为 $0$。notebook 验证它能精确恢复 $d$："),
    CODE("真 d= 0.0   控制 S 后 T 的系数 = -0.0005   -> 替代性通过\n"
         "真 d=+1.0   控制 S 后 T 的系数 = +0.9995   -> 拒绝替代性\n"
         "真 d=-2.0   控制 S 后 T 的系数 = -2.0005   -> 拒绝替代性"),
    CALLOUT("paper", "代理指标省的是未来的等待，不是过去的等待",
            "这个检验需要<strong>已经有</strong>长期结果的历史实验。"
            "所以代理指标体系的前提是「你曾经等过」——"
            "而且它只对<em>当时那批实验所覆盖的干预类型</em>有效。"
            "一个全新机制的干预（例如第一次做通知类功能）"
            "很可能引入历史实验里不存在的直接通道，"
            "此时替代性的历史证据<strong>不适用</strong>，而这一点不会被任何指标反映。"),
    P("还有一个更细的点：模块 02 已经证明<strong>控制中介会把总效应换成直接效应</strong>。"
      "代理指标做的恰好是相反的操作——它只保留<em>经由</em>中介的那部分。"
      "所以「代理指标预测」与「控制中介的回归」是同一枚硬币的两面，"
      "各自丢掉效应的另一半。"),
])),

("designs", "干扰下的其他设计，以及它们各自的代价", "".join([
    P("集群随机化和 switchback 不是唯一选择。"
      "把可选项摆在一起，因为它们的<strong>代价形式不同</strong>，"
      "而选择应该由「哪种代价你付得起」决定。"),
    TABLE(["设计", "怎么做", "能测到什么", "代价"],
          [["个体随机化", "用户级抛硬币", "<strong>直接效应</strong>",
            "漏掉溢出（本例 $50\\%$），无告警"],
           ["集群随机化", "整个社区 / 地理区同处理", "接近全局效应",
            "设计效应 $1+(m-1)\\text{ICC}$（本例 $\\times 10.97$）"],
           ["switchback", "时间片整片同处理", "共享资源型干扰下的全局效应",
            "时间自相关 $+$ carryover $+$ burn-in 丢样本"],
           ["双侧随机化", "供需两侧分别随机化", "分离供给侧与需求侧效应",
            "分析复杂；两侧的集群单元通常不一致"],
           ["暴露饱和度设计", "把集群随机分配到不同处理<em>比例</em>",
            "<strong>剂量-反应曲线</strong>（$\\alpha$ 与 $\\beta$ 分开）",
            "需要更多集群；每个饱和度下的样本更少"],
           ["随机化之上再随机化", "先随机选设计，再随机分配", "<strong>直接检测干扰是否存在</strong>",
            "样本需求最大；但它回答的是「要不要担心」"]]),
    H3("暴露饱和度设计为什么值得单独提"),
    P("本模块第 1 节把 $\\alpha$（直接效应）与 $\\beta$（溢出）当成未知的。"
      "个体随机化给出 $\\alpha$，大集群给出 $\\alpha + \\beta$——"
      "所以<strong>两个设计合起来就能把两者分开</strong>。"),
    P("暴露饱和度设计把这个想法推广：给不同集群分配不同的处理比例 $p_j$，"
      "然后在集群层面回归结果对 $p_j$。"
      "斜率就是 $\\beta$，截距附近的部分给出 $\\alpha$。"
      "练习 3 验证的关系 $\\hat{\\tau}_{AB} = \\alpha + \\beta \\cdot g$ "
      "正是这个设计的一维版本——"
      "而它说明<strong>「邻居暴露差 $g$」这个可测量的量是把两者分开的钩子</strong>。"),
    CALLOUT("intuition", "为什么剂量-反应曲线比单个数字有用",
            "全量上线对应 $p = 1$，而实验通常在 $p = 0.5$ 附近做。"
            "如果溢出对 $p$ 是<strong>非线性</strong>的"
            "（网络效应常常有阈值：达到某个渗透率才起飞），"
            "那么从 $p{=}0.5$ 外推到 $p{=}1$ 就是错的，"
            "而单个集群随机化实验<em>无法发现</em>这一点——"
            "它只给出一个点，而任何一个点都落在无穷多条曲线上。"),
])),

("checklist", "线上归因的口径检查单", "".join([
    P("把本模块四节压成一张在设计阶段就该走一遍的表："),
    TABLE(["问题", "如果答案是「有」", "本课的量化"],
          [["用户之间会互相影响吗（社交、共享供给、竞价）",
            "个体随机化测的是直接效应；考虑集群化或 switchback",
            "漏掉 $\\beta/(\\alpha+\\beta)$，本例 $50\\%$"],
           ["集群化了吗？ICC 估了吗",
            "样本量需求乘 $1+(m-1)\\text{ICC}$",
            "$m{=}50$, ICC$=0.2$ 时 $\\times 10.97$"],
           ["结论会被用来分配跨渠道预算吗",
            "顺序规则的输出不能作为依据",
            "last-touch 最大误差 $39.5$ pp"],
           ["用了短期代理指标吗",
            "在历史实验里检验 $Y \\sim T + S$ 中 $T$ 的系数",
            "有直接通道时可<strong>符号反转</strong>"],
           ["决策关心总效应还是直接效应",
            "两者可以相差很多；模块 02 的 $\\{X,M\\}$ 行是同一个错误",
            "本课例中总 $2.9$ vs 直接 $2.0$"]]),
    CALLOUT("intuition", "本课的最后一句",
            "六个模块下来，反复出现的是同一件事："
            "<strong>因果推断的失效几乎从不表现为错误，而是表现为「答对了另一个问题」</strong>。"
            "选择偏差、对撞、中介、弱工具、平行趋势、干扰、归因规则、代理指标——"
            "每一个都会给出格式正确、置信区间漂亮、可复现的数字。"
            "所以唯一有效的做法是在<em>看到数字之前</em>"
            "把「我要的是哪个量、它靠什么假设可识别、假设不成立会怎样」写下来。"),
])),
]

NB = [
md("""# C76 模块 05 · 线上归因

四件事，全都发生在**随机化完全有效**的前提下：

1. **干扰**：个体随机化测到 $1.00$，全局效应是 $2.00$；
2. **集群随机化的价格**：设计效应 $1+(m-1)\\text{ICC}$，验证到 $1.6\\%$；
3. **归因规则**：last-touch 把真实份额 $7.1\\%$ 记成 $38.0\\%$；
4. **代理指标**：有直接通道时**符号反转**。

四种失效**都不产生任何异常统计量**。

纯 numpy / CPU / 离线。"""),

code("""import numpy as np
import itertools
import math

def lstsq(A, y):
    return np.linalg.lstsq(A, y, rcond=None)[0]

print('本模块前提：分桶正确、p 值正确、功效充足。失效全在**口径**层。')"""),

md("""## 1. 干扰：个体随机化测的是直接效应

环形图，每人 $k$ 个左邻 + $k$ 个右邻。
$Y_i = \\alpha T_i + \\beta \\bar T_{N(i)} + \\varepsilon$，全局效应 $= \\alpha + \\beta$。"""),

code("""def ring_neighbors(n, k):
    '''环形图：每个节点连左右各 k 个邻居。'''
    return [[(i + d) % n for d in list(range(-k, 0)) + list(range(1, k + 1))]
            for i in range(n)]

NB_CACHE = {}

def neighbors(n, k):
    if (n, k) not in NB_CACHE:
        NB_CACHE[(n, k)] = ring_neighbors(n, k)
    return NB_CACHE[(n, k)]

def simulate(n=4000, k=5, alpha=1.0, beta=1.0, p=0.5, seed=0, cluster=None, noise=0.5):
    '''cluster=None 为个体随机化；否则把环切成 cluster 大小的块整块分配。'''
    r = np.random.default_rng(seed)
    nb = neighbors(n, k)
    if cluster is None:
        T = (r.random(n) < p).astype(float)
    else:
        z = (r.random(n // cluster) < p).astype(float)
        T = np.repeat(z, cluster)
    frac = np.array([T[v].mean() for v in nb])
    Y = alpha * T + beta * frac + r.normal(0, noise, n)
    return T, Y, frac

def ab_estimate(T, Y):
    return float(Y[T == 1].mean() - Y[T == 0].mean())

GLOBAL = 2.0     # alpha + beta
print('Y = 1.0*T_i + 1.0*(邻居处理比例) + noise；每人 10 个邻居')
print(f'决策关心的**全局效应**（全开 vs 全关）= 1.0 + 1.0 = {GLOBAL}')
print()
print('  设计                 A/B 估计     与目标之差    两臂的邻居暴露差')
_res = {}
for tag, cl in [('个体随机化', None), ('集群随机化 m=20', 20),
                ('集群随机化 m=100', 100), ('集群随机化 m=500', 500)]:
    es, fd = [], []
    for s in range(40):
        T, Y, frac = simulate(seed=s, cluster=cl)
        es.append(ab_estimate(T, Y))
        fd.append(float(frac[T == 1].mean() - frac[T == 0].mean()))
    _res[tag] = (float(np.mean(es)), float(np.mean(fd)))
    print(f'  {tag:20s} {np.mean(es):+9.4f}    {np.mean(es)-GLOBAL:+9.4f}      {np.mean(fd):+.4f}')

assert abs(_res['个体随机化'][0] - 1.0) < 0.05, '个体随机化应只测到直接效应 1.0'
assert abs(_res['个体随机化'][1]) < 0.01, '个体随机化的邻居暴露差应约为 0'
assert abs(_res['集群随机化 m=500'][0] - GLOBAL) < 0.05, 'm=500 应接近全局效应'
assert _res['集群随机化 m=500'][1] > 0.95, 'm=500 的邻居暴露差应接近 1'

print()
print(f'✅ 个体随机化测到 {_res["个体随机化"][0]:.4f}，漏掉了 '
      f'{(GLOBAL-_res["个体随机化"][0])/GLOBAL*100:.0f}% 的效应')
print('   原因：两臂的邻居处理比例都约等于 p=0.5，溢出项在相减时**完全抵消**。')
print('   而这不产生任何统计异常 —— 实验是干净的，p 值是对的。')"""),

code("""# 漏掉的比例恰好是 beta/(alpha+beta)，与样本量无关
print('漏掉的比例 = beta/(alpha+beta)：')
print('  alpha  beta   预测漏掉   实测 A/B     实测漏掉')
for a, b in [(1.0, 0.0), (1.0, 0.5), (1.0, 1.0), (1.0, 3.0), (2.0, 0.5)]:
    pred = b / (a + b)
    meas = float(np.mean([ab_estimate(*simulate(alpha=a, beta=b, seed=s)[:2])
                          for s in range(20)]))
    emp = (a + b - meas) / (a + b)
    print(f'  {a:5.1f}  {b:4.1f}   {pred*100:7.1f}%   {meas:+9.4f}   {emp*100:9.1f}%')
    assert abs(pred - emp) < 0.03, f'alpha={a}, beta={b}: 预测 {pred:.4f} vs 实测 {emp:.4f}'

print()
print('与样本量无关（beta=1, alpha=1，漏掉应恒为 50%）:')
for n in (1000, 4000, 16000):
    meas = float(np.mean([ab_estimate(*simulate(n=n, seed=s)[:2]) for s in range(20)]))
    print(f'  n={n:6d}: A/B = {meas:+.4f}, 漏掉 {(GLOBAL-meas)/GLOBAL*100:.1f}%')
    assert abs((GLOBAL - meas) / GLOBAL - 0.5) < 0.03

print()
print('✅ 加样本、换检验、上 CUPED 都不会改变这个 50% —— 它是口径问题，不是精度问题。')"""),

md("""## 2. 集群随机化的价格：设计效应 $1+(m-1)\\text{ICC}$"""),

code("""def cluster_var(n=6000, m=10, icc=0.2, S=4000):
    '''在给定 ICC 下比较个体随机化与集群随机化的估计量方差。总方差固定为 1。'''
    nblk = n // m
    vb, vw = icc, 1.0 - icc
    ind, clu = [], []
    for s in range(S):
        r = np.random.default_rng(s)
        Y0 = np.repeat(r.normal(0, np.sqrt(vb), nblk), m) + r.normal(0, np.sqrt(vw), n)
        Ti = (r.random(n) < 0.5).astype(float)
        ind.append(Y0[Ti == 1].mean() - Y0[Ti == 0].mean())
        z = (r.random(nblk) < 0.5).astype(float)
        if 0 < z.sum() < nblk:
            Tc = np.repeat(z, m)
            clu.append(Y0[Tc == 1].mean() - Y0[Tc == 0].mean())
    return float(np.var(ind, ddof=1)), float(np.var(clu, ddof=1))

print('n=6000（总方差 1），4000 seeds')
print('    m    ICC    个体方差     集群方差     实测比    理论 DE   相对误差')
_errs = []
for m in (5, 10, 50):
    for icc in (0.0, 0.05, 0.2, 0.5):
        vi, vc = cluster_var(m=m, icc=icc)
        de = 1 + (m - 1) * icc
        obs = vc / vi
        rel = abs(obs - de) / de
        _errs.append(rel)
        print(f'  {m:3d}   {icc:.2f}   {vi:.6f}   {vc:.6f}  {obs:8.2f}  {de:8.2f}   {rel*100:6.1f}%')

assert max(_errs) < 0.08, f'设计效应公式的最大相对误差应 <8%，得到 {max(_errs)*100:.1f}%'
_vi, _vc = cluster_var(m=50, icc=0.2)
assert 10.0 < _vc / _vi < 12.0, f'm=50, ICC=0.2 应约 10.8 倍，得到 {_vc/_vi:.2f}'

print()
print(f'✅ 公式 1+(m-1)ICC 的最大相对误差 {max(_errs)*100:.1f}%')
print(f'✅ m=50, ICC=0.2: 方差涨 {_vc/_vi:.2f} 倍 -> 等价样本量缩小到 1/{_vc/_vi:.0f}')
print()
print('-> 「用集群随机化解决干扰」不是免费的修正，是一次显式取舍：')
print('   干扰的偏差 vs 集群的方差。')"""),

code("""# 两侧相乘 -> 集群大小有内点最优
def bias_of_cluster(m, seeds=20, n=6000):
    '''给定集群大小的残余偏差（相对全局效应）。'''
    if m is None:
        est = np.mean([ab_estimate(*simulate(n=n, seed=s)[:2]) for s in range(seeds)])
    else:
        est = np.mean([ab_estimate(*simulate(n=n, cluster=m, seed=s)[:2])
                       for s in range(seeds)])
    return float(est - GLOBAL)

print('集群大小的 MSE 权衡（n=6000, ICC=0.2, 效应尺度 2.0）')
print('    m      偏差      偏差²     设计效应   方差(∝DE)    MSE')
ICC = 0.2
VAR_UNIT = 6.8e-4          # 个体随机化下的方差（上表实测）
_mse = {}
for m in (1, 5, 10, 20, 50, 100, 250, 500, 1000):
    b = bias_of_cluster(None if m == 1 else m)
    de = 1 + (m - 1) * ICC
    v = VAR_UNIT * de
    _mse[m] = b**2 + v
    print(f'  {m:5d}  {b:+8.4f}  {b**2:8.4f}   {de:8.1f}  {v:10.5f}  {_mse[m]:8.4f}')

_best = min(_mse, key=_mse.get)
print()
print(f'✅ MSE 最小的集群大小 m* = {_best}（MSE {_mse[_best]:.4f}）')
assert _best not in (1, 1000), f'应有内点最优，得到 {_best}'
assert _mse[1] > _mse[_best] and _mse[1000] > _mse[_best]
print(f'   m=1（个体随机化）MSE {_mse[1]:.4f} 由**偏差**主导（漏掉 50% 的效应）')
print(f'   m=1000 MSE {_mse[1000]:.4f} 由**方差**主导（DE = {1+999*ICC:.0f}）')
print()
print('⚠️  这条曲线依赖 ICC 与效应尺度，两者都必须先估。')
print('   工程上常见的错误是用**个体随机化**的历史方差做集群实验的功效计算 ——')
print(f'   那会把所需样本量低估 DE 倍（本例 m=50 时 {1+49*ICC:.1f} 倍）。')"""),

md("""## 3. 多触点归因：转化只取决于曝光集合

关键设计：`conv_prob(S)` 只接受一个**集合**，
所以「顺序影响转化」在这个 DGP 里是**可以被证伪**的。"""),

code("""CH = ['搜索', '社交', '邮件', '直达']
BASE = {'搜索': 0.30, '社交': 0.20, '邮件': 0.05, '直达': 0.10}

def conv_prob(S):
    '''次可加：p = 1 - prod(1 - b_c)。只取决于集合，与顺序无关。'''
    p = 1.0
    for c in S:
        p *= (1 - BASE[c])
    return 1 - p

def shapley_values():
    '''对全部到达顺序取平均的边际贡献。'''
    phi = {c: 0.0 for c in CH}
    for perm in itertools.permutations(CH):
        cur, prev = set(), conv_prob(set())
        for c in perm:
            cur.add(c)
            now = conv_prob(cur)
            phi[c] += now - prev
            prev = now
    return {c: v / math.factorial(len(CH)) for c, v in phi.items()}

SH = shapley_values()
FULL = conv_prob(set(CH))
print(f'全触点转化概率 = {FULL:.4f}')
print(f'Shapley 值之和 = {sum(SH.values()):.4f}   <- 有效性公理')
assert abs(sum(SH.values()) - FULL) < 1e-12

print()
print('  渠道    单独效果 b_c   Shapley 值   Shapley 真实份额')
for c in CH:
    print(f'  {c}      {BASE[c]:.2f}          {SH[c]:.4f}       {SH[c]/FULL*100:5.1f}%')

# 证明顺序无关：同一集合的两种顺序转化概率完全相同
print()
print('顺序无关性（同一集合、不同顺序）:')
_S = {'搜索', '邮件'}
for _perm in [('搜索', '邮件'), ('邮件', '搜索')]:
    print(f'  {_perm} -> {conv_prob(set(_perm)):.6f}')
assert conv_prob({'搜索', '邮件'}) == conv_prob({'邮件', '搜索'})
print('  -> 所以任何基于顺序的归因规则在这个 DGP 里都可以被证明是**无信息**的。')"""),

code("""def gen_paths(n=400_000, seed=0):
    '''生成路径数据。邮件与直达倾向于最后曝光（再营销）。'''
    r = np.random.default_rng(seed)
    expose = {'搜索': 0.55, '社交': 0.45, '邮件': 0.60, '直达': 0.35}
    ORDER_BIAS = {'搜索': 0, '社交': 1, '邮件': 2, '直达': 3}
    paths, ys = [], []
    for _ in range(n):
        S = [c for c in CH if r.random() < expose[c]]
        if not S:
            continue
        order = sorted(S, key=lambda c: ORDER_BIAS[c] + r.normal(0, 0.4))
        ys.append(1 if r.random() < conv_prob(set(S)) else 0)
        paths.append(order)
    return paths, np.array(ys)

PATHS, YS = gen_paths()
NCONV = int(YS.sum())

def attribute(rule):
    cred = {c: 0.0 for c in CH}
    for pth, y in zip(PATHS, YS):
        if not y:
            continue
        if rule == 'last':
            cred[pth[-1]] += 1
        elif rule == 'first':
            cred[pth[0]] += 1
        elif rule == 'even':
            for c in pth:
                cred[c] += 1 / len(pth)
        elif rule == 'timedecay':
            wts = np.array([0.5**(len(pth) - 1 - i) for i in range(len(pth))])
            wts /= wts.sum()
            for c, w in zip(pth, wts):
                cred[c] += w
    return {c: v / NCONV for c, v in cred.items()}

ROWS = {r_: attribute(r_) for r_ in ('last', 'first', 'even', 'timedecay')}
print(f'{NCONV:,} 次转化。各规则给出的**份额**（%）:')
print('  渠道     Shapley真值   last-touch   first-touch   均分    时间衰减')
for c in CH:
    print(f'  {c}      {SH[c]/FULL*100:8.1f}   {ROWS["last"][c]*100:10.1f}  '
          f'{ROWS["first"][c]*100:11.1f}  {ROWS["even"][c]*100:7.1f}  '
          f'{ROWS["timedecay"][c]*100:8.1f}')

print()
print('各规则相对 Shapley 真值的最大绝对份额误差（百分点）:')
_maxerr = {}
for r_, tag in [('last', 'last-touch'), ('first', 'first-touch'),
                ('even', '均分'), ('timedecay', '时间衰减')]:
    _maxerr[r_] = max(abs(ROWS[r_][c] * 100 - SH[c] / FULL * 100) for c in CH)
    print(f'    {tag:12s} {_maxerr[r_]:6.1f} pp')

_email_ratio = ROWS['last']['邮件'] / (SH['邮件'] / FULL)
_search_ratio = (SH['搜索'] / FULL) / ROWS['last']['搜索']
assert _maxerr['last'] > 30, 'last-touch 的误差应超过 30 个百分点'
assert _email_ratio > 4, f'邮件应被 last-touch 高估 >4 倍，实测 {_email_ratio:.1f}'
assert _search_ratio > 4, f'搜索应被 last-touch 低估 >4 倍，实测 {_search_ratio:.1f}'

print()
print(f'✅ 邮件真实份额 {SH["邮件"]/FULL*100:.1f}%，last-touch 记它 '
      f'{ROWS["last"]["邮件"]*100:.1f}% —— 高估 {_email_ratio:.1f} 倍')
print(f'✅ 搜索真实份额 {SH["搜索"]/FULL*100:.1f}%，last-touch 记它 '
      f'{ROWS["last"]["搜索"]*100:.1f}% —— 低估 {_search_ratio:.1f} 倍')
print()
print('-> 这不是估计误差。规则的输出完全由「渠道的曝光顺序分布」决定，')
print('   而那是一个可以被运营策略改变的量。')"""),

code("""# 证明「调整投放时序就能改变账面归因，而真实贡献一点没变」
def gen_paths_reordered(n=400_000, seed=0, order_bias=None):
    r = np.random.default_rng(seed)
    expose = {'搜索': 0.55, '社交': 0.45, '邮件': 0.60, '直达': 0.35}
    ob = order_bias or {'搜索': 0, '社交': 1, '邮件': 2, '直达': 3}
    paths, ys = [], []
    for _ in range(n):
        S = [c for c in CH if r.random() < expose[c]]
        if not S:
            continue
        order = sorted(S, key=lambda c: ob[c] + r.normal(0, 0.4))
        ys.append(1 if r.random() < conv_prob(set(S)) else 0)
        paths.append(order)
    return paths, np.array(ys)

_orig = {'搜索': 0, '社交': 1, '邮件': 2, '直达': 3}
_flip = {'搜索': 3, '社交': 2, '邮件': 1, '直达': 0}      # 只改时序，不改曝光概率
print('只改变渠道的曝光**时序**（曝光概率与转化机制完全不变）:')
print('  时序           搜索 last-touch 份额   邮件 last-touch 份额   转化率')
for _tag, _ob in [('原时序', _orig), ('反转时序', _flip)]:
    _p, _y = gen_paths_reordered(seed=0, order_bias=_ob)
    _nc = int(_y.sum())
    _cred = {c: 0.0 for c in CH}
    for _pth, _yy in zip(_p, _y):
        if _yy:
            _cred[_pth[-1]] += 1
    print(f'  {_tag:12s}   {_cred["搜索"]/_nc*100:16.1f}%   '
          f'{_cred["邮件"]/_nc*100:16.1f}%   {_y.mean()*100:6.2f}%')
    if _tag == '原时序':
        _c_orig = dict(_cred); _n_orig = _nc; _r_orig = _y.mean()
    else:
        _c_flip = dict(_cred); _n_flip = _nc; _r_flip = _y.mean()

assert abs(_r_orig - _r_flip) < 0.002, '转化率应几乎不变（机制没变）'
_shift = abs(_c_flip['搜索'] / _n_flip - _c_orig['搜索'] / _n_orig) * 100
assert _shift > 20, f'搜索的 last-touch 份额应大幅变化，实测 {_shift:.1f} pp'

print()
print(f'✅ 转化率几乎不变（{_r_orig*100:.2f}% vs {_r_flip*100:.2f}%）—— 真实贡献没变')
print(f'✅ 搜索的 last-touch 份额变了 {_shift:.1f} 个百分点 —— 账面归因大幅改变')
print()
print('   Shapley 值当然完全不变（它只依赖 conv_prob）:')
for c in CH:
    print(f'     {c}: {SH[c]/FULL*100:.1f}%')
print()
print('-> 所以不要把顺序规则的输出当作预算分配依据。')"""),

md("""## 4. 代理指标：符号反转"""),

code("""def surrogate_sim(a=1.0, b=1.0, d=0.0, n=200_000, seed=7):
    '''T -> S (系数 a), S -> Y (系数 b), T -> Y 直接通道 (系数 d)。

    替代性要求 d = 0。
    '''
    r = np.random.default_rng(seed)
    T = (r.random(n) < 0.5).astype(float)
    S = a * T + r.normal(0, 1, n)
    Y = b * S + d * T + r.normal(0, 1, n)
    return T, S, Y

# 历史实验（替代性成立 d=0）里学 h(S) = E[Y|S]
Th, Sh, Yh = surrogate_sim(d=0.0, seed=99)
BETA_H = lstsq(np.column_stack([np.ones(len(Sh)), Sh]), Yh)

def surrogate_predict(S, T):
    yhat = np.column_stack([np.ones(len(S)), S]) @ BETA_H
    return float(yhat[T == 1].mean() - yhat[T == 0].mean())

print(f'历史实验学到 h(S) = {BETA_H[0]:+.4f} + {BETA_H[1]:+.4f}*S')
print()
print('  当期实验参数              短期 ΔS   代理指标预测 ΔY   真实长期 ΔY   预测误差')
_sur = {}
for tag, kw in [('d=0（替代性成立）', dict(d=0.0)),
                ('d=+1（有直接通道）', dict(d=1.0)),
                ('d=-2（反向直接通道）', dict(d=-2.0)),
                ('a=2（代理放大 2x）', dict(a=2.0, d=0.0)),
                ('a=0, d=+1（代理无变化）', dict(a=0.0, d=1.0))]:
    T, S, Y = surrogate_sim(seed=7, **kw)
    ds = float(S[T == 1].mean() - S[T == 0].mean())
    si = surrogate_predict(S, T)
    dy = float(Y[T == 1].mean() - Y[T == 0].mean())
    _sur[tag] = (ds, si, dy)
    flag = '   <- 符号反转' if si * dy < 0 else ''
    print(f'  {tag:26s} {ds:+8.4f}  {si:+14.4f}  {dy:+12.4f}  {si-dy:+9.4f}{flag}')

assert abs(_sur['d=0（替代性成立）'][1] - _sur['d=0（替代性成立）'][2]) < 0.02, 'd=0 时应准确'
_rev = _sur['d=-2（反向直接通道）']
assert _rev[1] * _rev[2] < 0, f'd=-2 时应符号反转：预测 {_rev[1]:+.4f}, 真实 {_rev[2]:+.4f}'
_blind = _sur['a=0, d=+1（代理无变化）']
assert abs(_blind[1]) < 0.05 and _blind[2] > 0.9, '代理无变化时应完全看不见真实效应'

print()
print(f'✅ d=-2: 短期代理**上涨** {_rev[0]:+.4f}，代理指标预测 {_rev[1]:+.4f}，')
print(f'   而真实长期效应是 {_rev[2]:+.4f} —— **符号完全反了**，且没有任何告警')
print(f'✅ a=0, d=+1: 代理毫无变化（预测 {_blind[1]:+.4f}），真实长期效应 {_blind[2]:+.4f}')
print('   代理指标只能看见「经过 S 的那部分」，绕过 S 的通道它完全看不见。')"""),

code("""# 替代性可以在**有长期数据的**历史实验里部分检验
print('检验：在历史实验里回归 Y ~ 1 + T + S，若替代性成立 T 的系数应为 0')
print('  真 d      控制 S 后 T 的系数     结论')
for d in (0.0, 1.0, -2.0):
    T, S, Y = surrogate_sim(d=d, n=200_000, seed=5)
    c = float(lstsq(np.column_stack([np.ones(len(Y)), T, S]), Y)[1])
    verdict = '替代性通过' if abs(c) < 0.05 else '拒绝替代性'
    print(f'  {d:+5.1f}     {c:+16.4f}     {verdict}')
    assert abs(c - d) < 0.02, f'系数应恢复真实 d={d}，得到 {c:.4f}'

print()
print('✅ 检验能精确恢复直接效应强度 d。')
print()
print('⚠️  但这个检验需要**已经有**长期结果的历史实验。')
print('   所以代理指标体系的前提是「你曾经等过」——')
print('   而且它只对**当时那批实验所覆盖的干预类型**有效。')
print('   一个全新机制的干预很可能引入历史实验里不存在的直接通道，')
print('   此时替代性的历史证据不适用，而这一点不会被任何指标反映。')
print()
print('与模块 02 的关系：')
print('  控制中介 -> 只保留**不经过**中介的效应（直接效应）')
print('  代理指标 -> 只保留**经过**中介的效应')
print('  两者是同一枚硬币的两面，各自丢掉效应的另一半。')"""),

md("""## ✏️ 练习 1：集群大小的 MSE 最优

实现 `cluster_mse(m, icc, var_unit, seeds)`：返回给定集群大小的
偏差²、方差、MSE。用它在不同 ICC 下找最优集群大小。"""),

code("""def cluster_mse(m, icc=0.2, var_unit=6.8e-4, seeds=20, n=6000):
    '''集群大小 m 的 MSE 分解。

    偏差来自干扰（m 越大越小），方差来自设计效应（m 越大越大）。

    参数
    ----
    m        : 集群大小；m=1 表示个体随机化
    icc      : 组内相关系数
    var_unit : 个体随机化下估计量的方差
    seeds    : 估偏差用的重复次数
    n        : 样本量

    返回
    ----
    dict : {'bias', 'bias_sq', 'de', 'var', 'mse'}
    '''
    # TODO: bias 用 bias_of_cluster(None if m==1 else m, seeds=seeds, n=n)
    #       de = 1 + (m-1)*icc；var = var_unit * de；mse = bias^2 + var
    raise NotImplementedError"""),

code("""# 自测
_MS = (1, 5, 10, 20, 50, 100, 250, 500, 1000)
print('  ICC     最优 m*    MSE(m*)     MSE(m=1)/MSE(m*)   MSE(m=1000)/MSE(m*)')
_bests = {}
for _icc in (0.02, 0.05, 0.2, 0.5):
    _d = {m: cluster_mse(m, icc=_icc) for m in _MS}
    _b = min(_d, key=lambda m: _d[m]['mse'])
    _bests[_icc] = _b
    print(f'  {_icc:.2f}    {_b:7d}   {_d[_b]["mse"]:.5f}        '
          f'{_d[1]["mse"]/_d[_b]["mse"]:10.1f}x        '
          f'{_d[_MS[-1]]["mse"]/_d[_b]["mse"]:10.1f}x')
    assert _b not in (1, _MS[-1]), f'ICC={_icc}: 应有内点最优，得到 {_b}'

# ICC 越大，最优集群越小
_seq = [_bests[i] for i in (0.02, 0.05, 0.2, 0.5)]
for _i in range(1, len(_seq)):
    assert _seq[_i] <= _seq[_i-1], f'ICC 越大最优集群应越小：{_seq}'

# 分解自洽
_chk = cluster_mse(50, icc=0.2)
assert abs(_chk['mse'] - (_chk['bias_sq'] + _chk['var'])) < 1e-15, 'MSE 分解应闭合'
assert abs(_chk['de'] - (1 + 49 * 0.2)) < 1e-12, '设计效应公式'
assert abs(_chk['bias_sq'] - _chk['bias']**2) < 1e-15

print()
print(f'✅ 最优集群大小随 ICC 从 {_seq[0]} 单调降到 {_seq[-1]}')
print('   ICC 越大，集群的方差代价越高，就越应该容忍一点干扰偏差。')
print()
print('⚠️  这条曲线依赖 ICC **和**效应尺度，两者都必须先估。')
print('   而 ICC 是集群划分方式的函数，不是数据的固有属性：')
print('   按地理分、按社交社区分、按时间片分，ICC 完全不同。')"""),

md("""## ✏️ 练习 2：Shapley 值的公理验证

Shapley 值由四条公理唯一确定。实现 `verify_shapley_axioms(base)`，
在给定的 `base` 字典（各渠道的单独效果）上验证其中三条：

- **有效性**（efficiency）：$\\sum_c \\phi_c = v(\\text{全集})$
- **对称性**（symmetry）：$b_c$ 相同的渠道 $\\phi$ 也相同
- **虚拟性**（null player）：$b_c = 0$ 的渠道 $\\phi_c = 0$"""),

code("""def verify_shapley_axioms(base):
    '''在给定 base 上计算 Shapley 值并验证三条公理。

    参数
    ----
    base : dict，渠道 -> 单独效果 b_c

    返回
    ----
    dict : {'phi', 'efficiency_gap', 'symmetric_pairs_ok', 'null_players_ok'}
      phi                : 各渠道的 Shapley 值
      efficiency_gap     : |sum(phi) - v(全集)|
      symmetric_pairs_ok : 所有 b_c 相同的渠道对，phi 之差都 < 1e-12
      null_players_ok    : 所有 b_c == 0 的渠道，|phi| < 1e-12
    '''
    chans = sorted(base)

    def v(S):
        p = 1.0
        for c in S:
            p *= (1 - base[c])
        return 1 - p

    # TODO: 对 itertools.permutations(chans) 累加边际贡献，除以 len(chans)!
    #       然后按上面三条公理算出三个返回值
    raise NotImplementedError"""),

code("""# 自测
print('  场景                              有效性差    对称性   虚拟性')
_cases = [
    ('原始 base', BASE),
    ('两个相同渠道', {'a': 0.3, 'b': 0.3, 'c': 0.1}),
    ('含一个零效果渠道', {'a': 0.3, 'b': 0.2, 'z': 0.0}),
    ('全部相同', {'a': 0.2, 'b': 0.2, 'c': 0.2, 'd': 0.2}),
    ('全部为零', {'a': 0.0, 'b': 0.0}),
]
for _tag, _b in _cases:
    _r = verify_shapley_axioms(_b)
    print(f'  {_tag:32s}  {_r["efficiency_gap"]:.2e}   '
          f'{str(_r["symmetric_pairs_ok"]):7s}  {_r["null_players_ok"]}')
    assert _r['efficiency_gap'] < 1e-12, f'{_tag}: 有效性应精确成立'
    assert _r['symmetric_pairs_ok'], f'{_tag}: 对称性应成立'
    assert _r['null_players_ok'], f'{_tag}: 虚拟性应成立'

# 与第 3 节的 SH 一致
_r0 = verify_shapley_axioms(BASE)
for _c in CH:
    assert abs(_r0['phi'][_c] - SH[_c]) < 1e-12, f'{_c}: 应与第 3 节一致'
print()
print('✅ 三条公理在五个场景上都精确成立（差 < 1e-12）')

# 对比：顺序规则违反哪些公理
print()
print('对比 —— last-touch 违反的公理:')
print(f'  有效性: 满足（份额之和 = {sum(ROWS["last"].values()):.4f}，按定义归一）')
_z = {'a': 0.3, 'b': 0.2, 'z': 0.0}
print('  虚拟性: **违反** —— 一个 b_c=0 的渠道只要出现在路径末尾就会拿到功劳')
print('  对称性: **违反** —— 两个 b_c 相同的渠道，曝光时序不同则份额不同')
print(f'          本课第 3 节的证明：只改时序，搜索的份额变了 {_shift:.1f} 个百分点')
print()
print('   -> 所以「用哪个归因规则」不是口味问题，是**它满足哪些公理**的问题。')"""),

md("""## ✏️ 练习 3：干扰下的偏差与暴露差的关系

正文说集群化之所以有效，是因为它拉开了两臂的**邻居暴露差**。
实现 `exposure_vs_bias(cluster_sizes, seeds)`：对每个集群大小返回
（邻居暴露差，A/B 估计），并验证

$$\\hat\\tau_{AB} \\approx \\alpha + \\beta \\cdot (\\text{暴露差})$$"""),

code("""def exposure_vs_bias(cluster_sizes, seeds=30, alpha=1.0, beta=1.0, n=4000):
    '''每个集群大小的（邻居暴露差, A/B 估计）。

    参数
    ----
    cluster_sizes : 集群大小列表，None 表示个体随机化
    seeds         : 重复次数
    alpha, beta   : 直接效应与溢出系数
    n             : 样本量

    返回
    ----
    list[tuple] : [(cluster, 暴露差, A/B 估计), ...]
    '''
    # TODO: 对每个 cl，用 simulate(n=n, alpha=alpha, beta=beta, cluster=cl, seed=s)
    #       收集 frac[T==1].mean() - frac[T==0].mean() 与 ab_estimate(T, Y)，取均值
    raise NotImplementedError"""),

code("""# 自测
_rows = exposure_vs_bias([None, 10, 20, 50, 100, 250, 500])
print('  集群大小    邻居暴露差 g    A/B 估计    alpha + beta*g    差')
for _cl, _g, _e in _rows:
    _pred = 1.0 + 1.0 * _g
    print(f'  {str(_cl):>9s}    {_g:11.4f}   {_e:+9.4f}   {_pred:+13.4f}   {abs(_e-_pred):.4f}')
    assert abs(_e - _pred) < 0.06, f'cluster={_cl}: 线性关系应成立（{_e:.4f} vs {_pred:.4f}）'

# 暴露差随集群增大而单调增加
_gs = [g for _, g, _ in _rows]
for _i in range(1, len(_gs)):
    assert _gs[_i] > _gs[_i-1] - 0.01, f'暴露差应单调增加：{[round(g,3) for g in _gs]}'

# 换 beta 验证系数确实是 beta
print()
print('  换 beta（alpha 固定 1.0）验证斜率就是 beta:')
for _beta in (0.5, 2.0, 3.0):
    _r = exposure_vs_bias([None, 50, 500], beta=_beta)
    _g0, _e0 = _r[0][1], _r[0][2]
    _g2, _e2 = _r[-1][1], _r[-1][2]
    _slope = (_e2 - _e0) / (_g2 - _g0)
    print(f'    beta={_beta:.1f}: 实测斜率 {_slope:.4f}')
    assert abs(_slope - _beta) < 0.08, f'斜率应等于 beta={_beta}，得到 {_slope:.4f}'

print()
print(f'✅ A/B 估计 = alpha + beta * 暴露差，在 7 个集群大小上都成立（最大差 '
      f'{max(abs(_e - 1.0 - _g) for _, _g, _e in _rows):.4f}）')
print('✅ 斜率就是 beta（用三个不同的 beta 验证）')
print()
print('   -> 这给出一个**可测量**的诊断：')
print('      在集群实验里报告两臂的邻居暴露差 g。')
print('      g 接近 0 说明集群没起作用（相当于个体随机化）；')
print('      g 接近 1 说明估的已经接近全局效应。')
print('      这个量不需要知道 beta 就能算 —— 它只依赖分桶与图结构。')"""),

md("""## ✏️ 练习 4：代理指标的可用范围

实现 `surrogate_error_bound(a, b, d)`：给定结构参数，
**解析地**给出代理指标预测的误差，并说明它何时会符号反转。

推导：$\\Delta S = a$，历史实验（$d{=}0$）学到的 $h$ 斜率是
$\\text{Cov}(S,Y)/\\text{Var}(S) = b \\cdot \\text{Var}(S_h)/\\text{Var}(S_h) = b$
（当 $a_h{=}1$ 时 $\\text{Var}(S_h)=2$，$\\text{Cov}=b\\cdot 2$，故斜率 $=b$）。
于是预测 $= a b$，真实 $= a b + d$，误差 $= -d$。"""),

code("""def surrogate_error_bound(a, b, d, b_hat=None):
    '''代理指标预测的解析误差。

    参数
    ----
    a     : T -> S
    b     : S -> Y
    d     : T -> Y 直接通道
    b_hat : 历史实验学到的 h 斜率（默认等于 b，即历史实验的 b 与当期相同）

    返回
    ----
    dict : {'delta_s', 'predicted', 'truth', 'error', 'sign_flip'}
      delta_s   : a
      predicted : a * b_hat
      truth     : a * b + d
      error     : predicted - truth
      sign_flip : predicted 与 truth 符号相反（且都非零）
    '''
    # TODO
    raise NotImplementedError"""),

code("""# 自测：解析式必须与模拟一致
print('   a     b     d     解析预测   解析真值   模拟预测   模拟真值   符号反转')
for _a, _b, _d in [(1.0, 1.0, 0.0), (1.0, 1.0, 1.0), (1.0, 1.0, -2.0),
                   (2.0, 1.0, 0.0), (0.0, 1.0, 1.0), (1.0, 2.0, -3.0),
                   (1.0, 0.5, -0.6)]:
    _r = surrogate_error_bound(_a, _b, _d)
    _T, _S, _Y = surrogate_sim(a=_a, b=_b, d=_d, n=400_000, seed=13)
    # 用当期数据自己学 h（等价于 b_hat = b）
    _bh = lstsq(np.column_stack([np.ones(len(_S)), _S]), _Y)[1]
    _sim_pred = float(_bh * (_S[_T == 1].mean() - _S[_T == 0].mean()))
    _sim_truth = float(_Y[_T == 1].mean() - _Y[_T == 0].mean())
    print(f'  {_a:4.1f}  {_b:4.1f}  {_d:+5.1f}   {_r["predicted"]:+9.4f}  '
          f'{_r["truth"]:+9.4f}  {_sim_pred:+9.4f}  {_sim_truth:+9.4f}   {_r["sign_flip"]}')
    assert abs(_r['truth'] - _sim_truth) < 0.02, f'解析真值应与模拟一致'
    assert abs(_r['error'] + _d) < 1e-12, f'误差应恰为 -d，得到 {_r["error"]:.6f}'

print()
print('✅ 误差恒等于 -d —— 与 a、b 完全无关。')
print('   所以代理指标的误差**不会**因为「代理指标选得更好」（a 更大）而减小。')

# 符号反转的精确条件
print()
print('符号反转的条件：predicted 与 truth 异号，即 a*b 与 a*b+d 异号')
print('  -> |d| > |a*b| 且 d 与 a*b 异号')
print()
print('   a*b     使符号反转的 d 范围        举例 d      是否反转')
for _a, _b in [(1.0, 1.0), (2.0, 1.0), (1.0, 0.5), (0.5, 0.5)]:
    _ab = _a * _b
    for _d in (-_ab * 0.5, -_ab * 1.5):
        _r = surrogate_error_bound(_a, _b, _d)
        print(f'  {_ab:5.2f}    d < {-_ab:+.2f}                {_d:+6.2f}      {_r["sign_flip"]}')
        assert _r['sign_flip'] == (_d < -_ab), f'反转条件：a*b={_ab}, d={_d}'

print()
print('✅ 反转条件恰为 d < -a*b（当 a*b > 0）')
print()
print('   工程含义：代理指标的安全性取决于 |d|/|a*b| 这个比值，')
print('   而 d 是**不可观测**的，除非有长期数据。')
print('   所以「代理指标准不准」这个问题在没有长期数据时是无法回答的 ——')
print('   能回答的只有「在历史上那批干预里它准不准」。')"""),

md("""## 📖 参考答案"""),

code("""def cluster_mse(m, icc=0.2, var_unit=6.8e-4, seeds=20, n=6000):
    '''集群大小 m 的 MSE 分解。'''
    bias = bias_of_cluster(None if m == 1 else m, seeds=seeds, n=n)
    de = 1.0 + (m - 1) * icc
    var = var_unit * de
    return {'bias': bias, 'bias_sq': bias**2, 'de': de,
            'var': var, 'mse': bias**2 + var}

def verify_shapley_axioms(base):
    '''计算 Shapley 值并验证三条公理。'''
    chans = sorted(base)

    def v(S):
        p = 1.0
        for c in S:
            p *= (1 - base[c])
        return 1 - p

    phi = {c: 0.0 for c in chans}
    for perm in itertools.permutations(chans):
        cur, prev = set(), v(set())
        for c in perm:
            cur.add(c)
            now = v(cur)
            phi[c] += now - prev
            prev = now
    nf = math.factorial(len(chans))
    phi = {c: val / nf for c, val in phi.items()}

    eff = abs(sum(phi.values()) - v(set(chans)))
    sym = all(abs(phi[c1] - phi[c2]) < 1e-12
              for c1 in chans for c2 in chans if base[c1] == base[c2])
    null = all(abs(phi[c]) < 1e-12 for c in chans if base[c] == 0.0)
    return {'phi': phi, 'efficiency_gap': float(eff),
            'symmetric_pairs_ok': bool(sym), 'null_players_ok': bool(null)}

def exposure_vs_bias(cluster_sizes, seeds=30, alpha=1.0, beta=1.0, n=4000):
    '''每个集群大小的（邻居暴露差, A/B 估计）。'''
    out = []
    for cl in cluster_sizes:
        gs, es = [], []
        for s in range(seeds):
            T, Y, frac = simulate(n=n, alpha=alpha, beta=beta, cluster=cl, seed=s)
            gs.append(float(frac[T == 1].mean() - frac[T == 0].mean()))
            es.append(ab_estimate(T, Y))
        out.append((cl, float(np.mean(gs)), float(np.mean(es))))
    return out

def surrogate_error_bound(a, b, d, b_hat=None):
    '''代理指标预测的解析误差。'''
    bh = b if b_hat is None else b_hat
    pred = a * bh
    truth = a * b + d
    return {'delta_s': float(a), 'predicted': float(pred), 'truth': float(truth),
            'error': float(pred - truth),
            'sign_flip': bool(pred * truth < 0)}

print('参考答案已定义。')
print()
print('要点：')
print('  1. 集群大小的 MSE 有内点最优，最优点随 ICC 增大而变小。')
print('  2. Shapley 满足有效性/对称性/虚拟性；last-touch 违反后两条 ——')
print('     所以选归因规则不是口味问题，是「它满足哪些公理」的问题。')
print('  3. A/B 估计 = alpha + beta * 邻居暴露差。暴露差是一个**可测量**的诊断，')
print('     不需要知道 beta 就能算。')
print('  4. 代理指标的误差恒等于 -d，与代理指标选得多好（a）完全无关。')"""),

md("""## 🧪 真实工程胶囊：实验设计的口径审计

本模块四种失效都不产生任何异常统计量。所以审计必须在**设计阶段**做，
而且必须问出那个唯一有用的问题：

> 我测的这个量，和我要做的这个决策，是同一个量吗？

下面这段代码把它做成一个审计器。它接受一份实验设计的声明，
输出**估计目标与决策目标的差距**，并对每一处差距给出本课量化过的代价。"""),

code("""def audit_design(design):
    '''审计一份实验设计的口径。返回 (差距列表, 估计目标描述)。

    design 字段:
      decision      : 决策要回答的问题
      unit          : 'user' | 'cluster' | 'time_slice'
      interference  : 是否存在用户间影响
      icc           : 若集群化，组内相关系数
      cluster_size  : 若集群化，集群大小
      outcome       : 'long_term' | 'surrogate'
      surrogacy_tested : 替代性是否已在历史实验里检验
      attribution   : None | 'last_touch' | 'shapley' | 'experiment'
      target        : 'total_effect' | 'direct_effect'
    '''
    gaps = []
    est = []

    # ① 干扰
    if design['interference'] and design['unit'] == 'user':
        gaps.append(('SUTVA', '个体随机化在有干扰时估的是**直接效应**，不是全局效应',
                     '本课量化：漏掉 beta/(alpha+beta)，示例中为 50%'))
        est.append('直接效应（不含溢出）')
    elif design['unit'] in ('cluster', 'time_slice'):
        m, icc = design.get('cluster_size', 1), design.get('icc')
        if icc is None:
            gaps.append(('ICC 未估', '集群实验的样本量需求乘 1+(m-1)ICC，而 ICC 未提供',
                         f'm={m} 时若 ICC=0.2，需求乘 {1+(m-1)*0.2:.1f} 倍'))
        else:
            de = 1 + (m - 1) * icc
            est.append(f'全局效应（设计效应 {de:.2f}，等价样本量 1/{de:.1f}）')
            if de > 5:
                gaps.append(('设计效应偏大', f'DE = {de:.2f}，等价样本量缩小到 1/{de:.1f}',
                             '考虑更小的集群 + 接受一点干扰偏差（练习 1 的 MSE 曲线）'))
    else:
        est.append('全局效应')

    # ② 结果指标口径
    if design['outcome'] == 'surrogate':
        if not design.get('surrogacy_tested'):
            gaps.append(('替代性未检验', '代理指标只能看见经过 S 的那部分效应',
                         '本课量化：有反向直接通道时**符号反转**（+1.005 vs -0.999）'))
        else:
            gaps.append(('替代性仅历史成立',
                         '检验只覆盖历史实验的干预类型；新机制可能引入新的直接通道',
                         '误差恒等于 -d，与代理指标选得多好无关（练习 4）'))
        est.append('长期效应中**经由代理指标**的部分')
    else:
        est.append('长期效应')

    # ③ 归因
    if design.get('attribution') == 'last_touch':
        gaps.append(('归因规则', 'last-touch 违反 Shapley 的对称性与虚拟性公理',
                     '本课量化：最大份额误差 39.5 pp；只改时序即可改变账面归因'))
        est.append('按曝光顺序分配的会计份额（**非**因果贡献）')
    elif design.get('attribution') == 'shapley':
        est.append('Shapley 因果贡献')
    elif design.get('attribution') == 'experiment':
        est.append('渠道的增量效应（实验直接测得）')

    # ④ 总效应 vs 直接效应
    if design['target'] == 'direct_effect' and 'total' in design['decision']:
        gaps.append(('总/直接效应错配', '决策关心总效应而设计估的是直接效应',
                     '本课量化：模块 02 的 {X,M} 行，2.90 -> 2.00（丢掉 31%）'))

    print(f"决策: {design['decision']}")
    print(f"单元: {design['unit']}   结果: {design['outcome']}   "
          f"目标: {design['target']}")
    print(f"估计目标实际是: {' + '.join(est) if est else '（未确定）'}")
    print('-' * 76)
    if not gaps:
        print('  ✅ 未发现口径差距')
    for name, what, cost in gaps:
        print(f'  ⚠️  [{name}]')
        print(f'      {what}')
        print(f'      {cost}')
    print('-' * 76)
    print(f'  {len(gaps)} 处口径差距')
    print()
    return gaps, est

print('=== 设计 A：一个典型的「看起来没问题」的社交产品实验 ===')
_gA, _eA = audit_design({
    'decision': '要不要全量上线新的关注推荐（total effect）',
    'unit': 'user',
    'interference': True,
    'outcome': 'surrogate',
    'surrogacy_tested': False,
    'attribution': None,
    'target': 'total_effect',
})
assert len(_gA) == 2, f'应发现 2 处差距，得到 {len(_gA)}'

print('=== 设计 B：修掉两处之后 ===')
_gB, _eB = audit_design({
    'decision': '要不要全量上线新的关注推荐（total effect）',
    'unit': 'cluster',
    'interference': True,
    'icc': 0.2,
    'cluster_size': 50,
    'outcome': 'long_term',
    'attribution': None,
    'target': 'total_effect',
})
assert len(_gB) == 1, f'应只剩设计效应那一处，得到 {len(_gB)}'

print('=== 设计 C：更小的集群 —— 用偏差换回方差 ===')
_gC, _eC = audit_design({
    'decision': '要不要全量上线新的关注推荐（total effect）',
    'unit': 'cluster',
    'interference': True,
    'icc': 0.2,
    'cluster_size': 10,
    'outcome': 'long_term',
    'attribution': None,
    'target': 'total_effect',
})
assert len(_gC) == 0, f'DE = {1+9*0.2:.1f} < 5，应无警报'

print('=== 设计 D：跨渠道预算分配用 last-touch ===')
_gD, _eD = audit_design({
    'decision': '各渠道的预算怎么分（total effect）',
    'unit': 'user',
    'interference': False,
    'outcome': 'long_term',
    'attribution': 'last_touch',
    'target': 'total_effect',
})
assert len(_gD) == 1 and _gD[0][0] == '归因规则'

print('审计器的用法与局限：')
print('  · 它的输出不是「通过/不通过」，而是**估计目标的准确描述**。')
print(f'    设计 A 估的其实是：「{" + ".join(_eA)}」')
print(f'    设计 B 估的是：「{" + ".join(_eB)}」')
print('    两者都是有意义的量 —— 问题只在于它们不是决策需要的那个量。')
print('  · 设计 C 无警报，但它有约 -0.15 的干扰偏差（正文第 2 节表）。')
print('    审计器看不见这个，因为它只检查声明，不看数据。')
print('    偏差侧要靠练习 1 的 MSE 曲线来选 m。')
print()
print('本课的最后一句：')
print('  因果推断的失效几乎从不表现为错误，而是表现为**答对了另一个问题**。')
print('  所以唯一有效的做法是在看到数字之前，把')
print('  「我要的是哪个量、它靠什么假设可识别、假设不成立会怎样」写下来。')"""),
]
