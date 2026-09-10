# -*- coding: utf-8 -*-
"""C76 模块 02 · 因果图与识别：后门准则、对撞偏差、中介。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（潜在结果、可忽略性、识别 vs 估计）；"
                 "有向图与路径的基本概念；"
                 "<em>C19 模块里出现过 d-分离，但那里用于分析网络的信息流，"
                 "本课用它决定「回归里该放哪些变量」</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_dag_backdoor.ipynb'
                       '（<strong>对撞偏差把 $X$ 对 $Y$ 的系数从 $+0.0006$ 变成 $-0.917$</strong>'
                       '（闭式解 $-1/(1+\\sigma^2)$ 预测 $-0.9174$，差 $4.5\\times10^{-4}$）/ '
                       '控制变量枚举表：$\\{X\\}$ 给 $2.899$（无偏），'
                       '<strong>$\\{X,C\\}$ 给 $0.304$——偏差从 $0.002$ 跳到 $-2.596$</strong> / '
                       '<strong>M-bias：控制一个<em>处理前</em>变量把偏差从 $+0.001$ 变成 $-0.312$</strong> / '
                       '程序化实现后门准则并枚举全部 $8$ 个子集，<strong>只有 $1$ 个合法</strong>）'),
    ("核心参考", "Pearl, <em>Causality</em>（2nd ed., 2009）第 1、3、11 章 · "
                 "Pearl, <em>Comment: Understanding Simpson's Paradox</em>（2014）· "
                 "Greenland, Pearl &amp; Robins, <em>Causal Diagrams for Epidemiologic "
                 "Research</em>（Epidemiology 1999）· "
                 "Shrier &amp; Platt, <em>Reducing bias through directed acyclic graphs</em>"
                 "（BMC Med Res Methodol 2008）· "
                 "Cinelli, Forney &amp; Pearl, <em>A Crash Course in Good and Bad Controls</em>"
                 "（Sociol Methods Res 2024）· "
                 "Shachter, <em>Bayes-Ball</em>（UAI 1998，d-分离的线性算法）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [

("why", "为什么需要图", "".join([
    P("模块 01 的可忽略性 $\\{Y(0),Y(1)\\} \\perp T \\mid X$ 里，$X$ 是什么？"
      "「所有相关的协变量」这个答案在实操中不可用，因为它没告诉我们"
      "<strong>怎么判断一个变量该不该放进去</strong>。"),
    P("工程上流行两条民间规则，本模块会用数值把两条都推翻："),
    TABLE(["民间规则", "听起来的道理", "本模块的反例", "代价"],
          [["控制得越多越好", "多控制总不会更坏", "对撞变量 $C$（处理与结果的共同后代）",
            "偏差从 $0$ 跳到 $\\mathbf{2.59}$"],
           ["只控制处理<em>前</em>的变量", "时间上在处理之前，不可能被处理影响",
            "M-bias（两个未观测混杂的共同后代）", "偏差从 $+0.001$ 变成 $\\mathbf{-0.312}$"]]),
    P("正确的判据来自图：把变量之间的因果假设画成有向无环图（DAG），"
      "然后用<strong>后门准则</strong>（back-door criterion）机械地判断哪些调整集合法。"
      "本模块把这个判据实现成代码，并在一个小 DAG 上<strong>枚举全部 $8$ 个子集</strong>——"
      "结果只有 $1$ 个合法。"),
    CALLOUT("intuition", "图不是画给人看的",
            "DAG 的价值不在于「让因果关系更直观」，而在于它把"
            "「该控制什么」变成一个<strong>可判定</strong>的问题。"
            "$8$ 个候选子集里恰好 $1$ 个合法，这个比例说明"
            "靠直觉挑选控制变量的成功率接近随机猜测。"),
])),

("dsep", "三种基本结构与 d-分离", "".join([
    P("路径上的信息能否流通，只取决于三种局部结构。"
      "记 $\\to$ 为因果方向，$\\perp$ 为独立，$Z$ 为被条件的变量集："),
    ASCII("""
  ① 链（chain）      A -> B -> C     不控制 B: A 与 C 相关
                                     控制 B:   A 与 C 独立   <- 阻断
  ② 叉（fork）       A <- B -> C     不控制 B: A 与 C 相关（混杂！）
                                     控制 B:   A 与 C 独立   <- 阻断
  ③ 对撞（collider） A -> B <- C     不控制 B: A 与 C 独立
                                     控制 B:   A 与 C **相关**  <- 打开！
""".strip("\n")),
    P("前两种是「控制它能阻断」，第三种<strong>反过来</strong>："
      "$B$ 是对撞时，不控制它路径本来是断的，<strong>控制它反而把路径打开</strong>。"
      "而且这个效应对 $B$ 的<em>后代</em>同样成立——控制对撞的任何后代都会部分打开路径。"),
    H3("对撞偏差：从无关到 $-0.917$"),
    P("notebook 里取两个独立变量 $X, Y \\sim N(0,1)$ 与 "
      "$Z = X + Y + \\varepsilon$，$\\varepsilon \\sim N(0, 0.3^2)$。"
      "$X$ 与 $Y$ 之间不存在任何因果关系，测出的边际相关是 $+0.00062$。"
      "而回归 $Y \\sim X + Z$ 给出 $X$ 的系数 <strong>$-0.91698$</strong>："),
    TABLE(["做法", "$X$ 的系数", "解读"],
          [["$Y \\sim X$", "$+0.00062$", "正确：$X$ 与 $Y$ 无关"],
           ["$Y \\sim X + Z$", "$\\mathbf{-0.91698}$", "控制对撞 $Z$ 后凭空出现强负关联"],
           ["限定在 $\\vert Z\\vert < 0.2$ 的 $66{,}106$ 个样本内", "$\\text{corr} = -0.90527$",
            "分层看同样出现——所以这不是回归的锅"],
           ["闭式解 $-1/(1+\\sigma^2)$", "$-0.91743$", "与回归系数差 $4.5\\times10^{-4}$"]]),
    DUAL("直觉：$Z$ 大意味着「$X$ 大或 $Y$ 大」。固定住 $Z$ 之后，"
         "知道 $X$ 大就意味着 $Y$ 必须小（否则 $Z$ 会更大）。"
         "于是「已知 $Z$」这个条件把两个无关变量绑在了一起。"
         "现实中的例子：只在<em>被录取的学生</em>里看「成绩」与「课外活动」的关系，"
         "会看到虚假的负相关，因为录取本身是两者的对撞。",
         "在联合正态下 $\\text{Cov}(X, Y \\mid Z) = "
         "\\text{Cov}(X,Y) - \\text{Cov}(X,Z)\\text{Cov}(Z,Y)/\\text{Var}(Z)$。"
         "取 $Z = X + Y + \\varepsilon$，$\\varepsilon \\sim N(0,\\sigma^2)$，"
         "则 $\\text{Cov}(X,Z) = \\text{Cov}(Y,Z) = 1$，$\\text{Var}(Z) = 2+\\sigma^2$，"
         "故 $\\text{Cov}(X,Y\\mid Z) = -1/(2+\\sigma^2)$。"
         "$\\sigma = 0.3$ 时为 $-0.4785$，条件相关为 $-1/(1+\\sigma^2) = -0.91743$，"
         "与实测的回归系数 $-0.91698$ 差 $4.5\\times10^{-4}$。"
         "所以对撞偏差的强度不是「可能有多大」，而是<strong>可以事先算出来</strong>："
         "$\\sigma = 0.1$ 给 $-0.9901$，$\\sigma = 1.0$ 给 $-0.5000$，$\\sigma = 3.0$ 给 $-0.1000$——"
         "$Z$ 越接近 $X$ 与 $Y$ 的确定性函数，控制它的破坏越大。"),
])),

("backdoor", "后门准则", "".join([
    P("给定 DAG、处理 $T$、结果 $Y$，集合 $Z$ 满足<strong>后门准则</strong>当且仅当："),
    OL(["$Z$ 中<strong>不含 $T$ 的任何后代</strong>；",
        "$Z$ 阻断了 $T$ 与 $Y$ 之间所有<strong>后门路径</strong>"
        "（即从 $T$ 出发第一步是<em>指向 $T$</em> 的箭头的路径）。"]),
    P("满足后门准则时，$E[\\tau]$ 由调整公式识别："),
    MATH("E[Y(t)] = \\sum_{z} E[Y \\mid T{=}t, Z{=}z]\\, P(Z{=}z)"),
    H3("在一个小 DAG 上枚举全部子集"),
    ASCII("""
                 X  (混杂: 影响 T 也影响 Y)
                / \\
               v   v
        T ---------> Y        直接效应 2.0
         \\    ^     /
          \\  /     /
           M      /           M 是中介: T -> M -> Y (贡献 0.9*1.0 = 0.9)
                 /
        T ------>C<------ Y    C 是对撞: T 和 Y 的共同后代

        总效应 = 2.0 (直接) + 0.9 (经 M) = 2.9
        可观测的候选调整变量: X, M, C
""".strip("\n")),
    P("notebook 实现了 Bayes-Ball 算法与后门准则，"
      "对 $\\{X, M, C\\}$ 的全部 $2^3 = 8$ 个子集逐一判定，并与回归系数对照："),
    TABLE(["子集", "后门准则", "回归系数", "与总效应 $2.9$ 之差"],
          [["$\\varnothing$", "✗ 不合法", "$+3.63131$", "$+0.731$"],
           ["$\\{X\\}$", "<strong>✓ 合法</strong>", "$\\mathbf{+2.90168}$", "$+0.002$"],
           ["$\\{M\\}$", "✗ 不合法", "$+2.73210$", "$-0.168$"],
           ["$\\{C\\}$", "✗ 不合法", "$+0.06546$", "$-2.835$"],
           ["$\\{X, M\\}$", "✗ 不合法", "$+2.00079$", "$-0.899$"],
           ["$\\{X, C\\}$", "✗ 不合法", "$+0.30406$", "$\\mathbf{-2.596}$"],
           ["$\\{M, C\\}$", "✗ 不合法", "$+0.11323$", "$-2.787$"],
           ["$\\{X, M, C\\}$", "✗ 不合法", "$+0.50375$", "$-2.396$"]]),
    P("三处值得停下来看。第一，<strong>只有 $\\{X\\}$ 合法</strong>，"
      "而它恰好是唯一无偏的（$+0.00168$）——准则与数值完全一致。"
      "第二，$\\{X\\} \\to \\{X,C\\}$ <strong>只多控制了一个变量，偏差从 $0.002$ 变成 $-2.596$</strong>。"
      "第三，$\\{X,M\\}$ 给出 $+2.00079$，看起来像个「不太准」的估计，"
      "实际上它<strong>精确地无偏地估出了直接效应 $2.0$</strong>——它答对了另一个问题。"),
    CALLOUT("warn", "「答对了另一个问题」是最难发现的错误",
            "$\\{X,M\\}$ 那一行没有任何异常信号：系数稳定、置信区间正常、"
            "换 seed 也复现。它错的地方在于<strong>控制中介变量把总效应换成了直接效应</strong>。"
            "如果决策关心的是「上线这个功能会带来多少提升」（总效应），"
            "而报告给出的是直接效应，那么经由 $M$ 的那 $0.9$ 就凭空消失了——"
            "$31\\%$ 的效应，不留痕迹。"),
])),

("mbias", "M-bias：连「只控制处理前变量」都不安全", "".join([
    P("上一节的 $C$ 是处理的<em>后代</em>，所以「不要控制处理后的变量」似乎能挡住它。"
      "这条规则在工程上非常流行，因为它只需要时间戳就能执行。"
      "但它是错的。"),
    ASCII("""
        U1              U2          U1, U2 都是**未观测**的
       /  \\            /  \\
      v    v          v    v
      T     Z <-------      Y       Z 是 U1 与 U2 的**对撞**
      |                     ^       Z 在**处理之前**就被测到
      +---------------------+       T -> Y 真效应 = 1.0

        注意: U1 不影响 Y，U2 不影响 T
        -> T 与 Y 之间**本来没有混杂**，不控制任何东西就是无偏的
""".strip("\n")),
    TABLE(["控制的变量集", "$T$ 的系数", "偏差"],
          [["$\\varnothing$（不控制）", "$+1.00128$", "$+0.001$（<strong>正确</strong>）"],
           ["$\\{Z\\}$（控制处理前变量）", "$\\mathbf{+0.68794}$", "$\\mathbf{-0.312}$"],
           ["$\\{Z, U_1\\}$", "$+1.00324$", "$+0.003$（补上 $U_1$ 又对了）"],
           ["$\\{Z, U_2\\}$", "$+1.00340$", "$+0.003$（补上 $U_2$ 也对了）"],
           ["$\\{U_1, U_2\\}$", "$+1.00332$", "$+0.003$"]]),
    P("$Z$ 在处理之前测到、与 $T$ 之间没有任何因果箭头，"
      "看起来像一个无害的基线协变量——而且它与 $T$ 的相关是 <strong>$+0.4889$</strong>，"
      "在任何「按相关性筛特征」的流程里都会被选进去。"
      "控制它把偏差从 $+0.00128$ 变成 <strong>$-0.31206$</strong>——真效应的 $31\\%$。"),
    P("而后两行给出了修补方式：只要把 $U_1$ <strong>或</strong> $U_2$ 中任意一个也控制上，"
      "偏差就消失了。但那两个变量按设定是<em>未观测</em>的——"
      "所以现实中的处境是：<strong>你能观测到造成问题的那个变量，"
      "却观测不到能修好它的那两个</strong>。"),
    CALLOUT("danger", "这条反例的实践含义",
            "「把处理前能拿到的特征都塞进倾向得分模型」是工业界的默认做法，"
            "而 M-bias 说明这个做法可以<strong>制造</strong>偏差。"
            "唯一的判据仍然是图：$Z$ 是不是某两个混杂的共同后代？"
            "这个问题<em>不能</em>从数据里学出来（$Z$ 与 $T$ 在数据上就是独立的），"
            "只能靠对业务机制的了解回答。"),
    P("公平地说，M-bias 的量级取决于图的参数，"
      "在很多现实情形下它比遗漏一个真混杂造成的偏差小得多。"
      "本节的论点不是「不要控制处理前变量」，"
      "而是<strong>「时间先后不是判据」</strong>——判据只能是图。"),
])),

("frontdoor", "后门走不通时：前门准则", "".join([
    P("后门准则要求「有一组可观测变量能阻断所有后门路径」。"
      "如果混杂完全不可观测，后门就走不通了——"
      "但还有一条<strong>前门</strong>（front-door）："
      "如果效应<em>全部</em>经由一个可观测的中介 $M$，且 $M$ 本身不被混杂影响，"
      "那么可以分两步走。"),
    ASCII("""
              U  (完全不可观测的混杂)
             / \\
            v   v
        T ------> Y        <- 后门 T <- U -> Y 无法阻断
         \\      ^
          v     /
            M          <- 但效应**全部**经由 M，且 U 不影响 M
""".strip("\n")),
    P("前门准则的三个条件：① $M$ 拦截了 $T$ 到 $Y$ 的<strong>所有</strong>有向路径；"
      "② 没有从 $T$ 到 $M$ 的未被阻断的后门路径；"
      "③ 所有从 $M$ 到 $Y$ 的后门路径都被 $T$ 阻断。"
      "此时"),
    MATH("P(Y{=}y \\mid do(T{=}t)) = \\sum_m P(m \\mid t) \\sum_{t'} P(y \\mid m, t') P(t')"),
    P("两个求和分别对应两步：$T \\to M$ 用观测的条件分布（因为条件 ② 保证它无混杂），"
      "$M \\to Y$ 用<strong>以 $T$ 为调整集</strong>的后门调整（条件 ③）。"),
    CALLOUT("warn", "为什么前门在实践中很少能用",
            "条件 ① 要求<strong>没有任何绕过 $M$ 的通道</strong>——"
            "这与模块 05 的<em>替代性</em>假设是同一个条件，"
            "而那一节会量出它失效时的代价（<strong>符号反转</strong>）。"
            "所以前门准则与代理指标是同一枚硬币："
            "前者用「全部经由 $M$」来做识别，后者用它来做预测，"
            "两者对这个假设的依赖强度完全一样。"),
])),

("instrument_graph", "工具变量与「白拿」的控制变量在图上的位置", "".join([
    P("模块 04 会用工具变量做识别。这里先把它在图上的位置说清楚，"
      "因为它和上一节的表里两类变量容易混。"),
    ASCII("""
   工具 I:                     纯结果预测变量 P:
        I                              P
        |                              |
        v                              v
   U -> T -> Y <- U              U -> T -> Y <- P
                                      ^
        I 影响 T，不影响 Y            P 影响 Y，不影响 T
        控制 I 会**放大方差**          控制 P **降低方差**且无害
""".strip("\n")),
    TABLE(["变量", "对 $T$", "对 $Y$", "控制它的后果", "不控制它的后果"],
          [["工具 $I$", "有影响", "无直接影响", "<strong>放大方差</strong>（吸走了 $T$ 的外生变动）",
            "无偏，且可用于 IV 识别"],
           ["纯预测变量 $P$", "无影响", "有影响", "<strong>降低方差</strong>，无偏",
            "无偏，但方差更大"]]),
    P("两者在图上是<strong>镜像</strong>的，而控制它们的后果<em>相反</em>。"
      "这是「好控制 / 坏控制」清单里最容易记错的一对："
      "工具变量是<strong>识别资源</strong>，把它当协变量控制掉等于把资源浪费掉；"
      "纯预测变量是<strong>方差资源</strong>，不控制它等于把资源浪费掉。"),
    DUAL("直觉：控制工具变量之后，$T$ 剩下的变动就只有内生的那部分了——"
         "你恰好把干净的信号扣掉，留下了脏的。"
         "而控制纯预测变量只是把 $Y$ 里与处理无关的噪声解释掉，"
         "所以估计更精确而不改变期望。",
         "记 $T = \\pi I + v$，$Y = \\beta T + \\gamma P + u$，"
         "其中 $\\text{Cov}(v,u) \\neq 0$。"
         "控制 $I$ 后 $T$ 的残差方差从 $\\pi^2 + \\sigma_v^2$ 降到 $\\sigma_v^2$，"
         "而 OLS 的方差 $\\propto 1/\\text{Var}(T \\mid \\text{控制集})$，故上升。"
         "控制 $P$ 则使残差方差 $\\sigma_u^2$ 降低 $\\gamma^2\\text{Var}(P)$，故方差下降。"),
])),

("discovery", "为什么本课不覆盖因果发现", "".join([
    P("既然判据是图，一个自然的想法是：<strong>能不能从数据里把图学出来</strong>？"
      "这个方向叫因果发现（causal discovery），有 PC、GES、NOTEARS 等一系列算法。"
      "本课不覆盖它，理由有三条，而它们都不是「算法不好」。"),
    OL(["<strong>观测数据的上限是马尔可夫等价类</strong>。"
        "在只有观测数据、且不加额外假设时，$A \\to B$ 与 $A \\leftarrow B$ "
        "产生完全相同的联合分布。算法能识别的是一个<em>等价类</em>，"
        "而本课需要的方向信息恰恰在等价类内部无法区分。"
        "第 2 节的三种结构里只有<strong>对撞</strong>能被观测数据区分出来"
        "（因为它的条件独立模式独一无二）。",
        "<strong>在线业务里有更可靠的信息来源</strong>："
        "系统架构（谁调用谁）、埋点顺序（谁先发生）、"
        "以及「谁能改什么」（哪些量是可干预的）。"
        "这些信息的可靠性远高于从有限样本里做的独立性检验，"
        "而后者在高维下的假阳性率是众所周知的问题。",
        "<strong>发现出来的图仍然要被审查</strong>。"
        "即使算法给出一个正确的等价类，"
        "选择其中哪一个成员、以及怎么处理算法认为不存在而领域知识认为存在的边，"
        "最终都回到人的判断。"
        "所以因果发现改变的是「图从哪里来」，"
        "不改变本模块的结论——<em>该控制什么必须由图决定</em>。"]),
    CALLOUT("paper", "一个折中的做法",
            "把领域知识写成图（如本模块胶囊里的 <code>SPEC</code>），"
            "然后用因果发现算法去<strong>检验</strong>它："
            "算法认为该有而图里没有的边、以及图里有而数据强烈否定的边，"
            "都是值得复核的地方。"
            "这样用法的价值是<em>发现分歧</em>，而不是<em>替代判断</em>——"
            "与模块 04 的事前登记模板同一个思路。"),
])),

("mediator", "中介、代理与「好控制/坏控制」清单", "".join([
    P("把上面的结论整理成一张可以直接查的表。"
      "设目标是 $T \\to Y$ 的<strong>总效应</strong>："),
    TABLE(["变量的角色", "图上的位置", "控制它", "本课的数值"],
          [["混杂（confounder）", "$T \\leftarrow X \\rightarrow Y$", "<strong>必须控制</strong>",
            "不控制时偏 $+0.731$"],
           ["中介（mediator）", "$T \\rightarrow M \\rightarrow Y$",
            "<strong>不要控制</strong>（会变成直接效应）", "$2.90 \\to 2.00$"],
           ["对撞（collider）", "$T \\rightarrow C \\leftarrow Y$",
            "<strong>绝不控制</strong>", "$2.90 \\to 0.30$"],
           ["中介的后代", "$M \\rightarrow M'$", "不要控制（部分阻断）", "介于两者之间"],
           ["对撞的后代", "$C \\rightarrow C'$", "不要控制（部分打开）", "介于两者之间"],
           ["工具（instrument）", "$I \\rightarrow T$，$I \\not\\to Y$",
            "控制会<em>降低</em>精度（放大方差）", "模块 04 会用它做识别"],
           ["纯结果预测变量", "$P \\rightarrow Y$，$P \\not\\to T$",
            "控制无害且<strong>降低方差</strong>", "唯一「白拿」的一类"],
           ["M-bias 型", "$T \\leftarrow U_1 \\rightarrow Z \\leftarrow U_2 \\rightarrow Y$",
            "<strong>不要控制</strong>（即使它在处理前）", "$+0.001 \\to -0.312$"]]),
    P("这张表的结构值得注意：<strong>八类变量里只有一类（纯结果预测变量）是无条件安全的</strong>，"
      "而它恰好是唯一<em>不</em>影响处理的那一类。"
      "换句话说，「与处理相关的变量」几乎都需要图上的论证才能决定去留。"),
    H3("如果目标是直接效应呢"),
    P("那么控制中介 $M$ 就是<strong>对的</strong>——$\\{X,M\\}$ 给出的 $2.00079$ 精确无偏。"
      "所以上表的每一行都隐含「目标是总效应」这个前提。"
      "这不是术语细节：模块 05 会给出一个真实场景，"
      "决策关心总效应而监控指标只能反映直接效应。"),
    P("还有一类变量上表没列，因为它介于两者之间：<strong>混杂的代理</strong>。"
      "若真混杂 $U$ 不可观测，但有一个 $W$ 满足 $U \\to W$，"
      "那么控制 $W$ 会<em>部分</em>阻断后门路径——"
      "阻断的程度取决于 $W$ 对 $U$ 的信息量。"
      "notebook 的练习 2 里图 3 正是这种情形："
      "$X \\to W \\to Y$ 时控制 $X$ 或 $W$ 都合法（$3/4$ 个子集合法），"
      "此时应选<strong>方差最小</strong>的那个。"
      "但要注意：代理控制不完全时<em>残余混杂</em>仍在，"
      "而这个残余不会随样本量消失（模块 01 第 5 节的现象）。"),
    CALLOUT("paper", "为什么本节没有「自动选变量」的方法",
            "既然判据是图，而图是假设，那么变量选择就<strong>不能</strong>完全由数据驱动。"
            "有一类算法（因果发现 / causal discovery）尝试从数据里学图，"
            "但它们只能识别到<strong>马尔可夫等价类</strong>——"
            "在观测数据上，$A \\to B$ 与 $A \\leftarrow B$ 通常无法区分。"
            "本课不覆盖因果发现，因为在线业务里通常有更可靠的信息来源："
            "系统架构、埋点顺序、以及「谁能改什么」。"
            "下一节把这三条理由展开。"),
    P("最后回到本模块开头那两条民间规则。它们之所以流行，"
      "是因为都能<strong>不看图就执行</strong>："
      "「控制得越多越好」只需要一个特征列表，"
      "「只控制处理前变量」只需要时间戳。"
      "而正确的判据需要一个东西是这两者都不提供的——"
      "<strong>对因果方向的断言</strong>。"
      "这个断言不能从数据里学出来（下一节），"
      "所以它必须被人写下来、被 review、被版本管理。"
      "本模块的胶囊做的就是这件事。"),
])),
]

NB = [
md("""# C76 模块 02 · 因果图与识别

四件事：

1. **对撞偏差**：把 $X$ 对 $Y$ 的系数从 $+0.0006$ 变成 $-0.917$；
2. **控制变量枚举表**：$\\{X\\}$ 无偏，$\\{X,C\\}$ 偏差 $-2.596$；
3. **M-bias**：控制一个*处理前*变量把偏差从 $+0.001$ 变成 $-0.312$；
4. 把 **Bayes-Ball 与后门准则实现成代码**，枚举 8 个子集，只有 1 个合法。

纯 numpy / CPU / 离线。"""),

code("""import numpy as np
import itertools

def ols(y, ctrl):
    '''回归 y ~ 1 + ctrl[0] + ctrl[1] + ...，返回系数向量（含截距）。'''
    A = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in ctrl])
    return np.linalg.lstsq(A, y, rcond=None)[0]

N = 600_000
print(f'样本量 N = {N:,}（够大，让偏差与噪声可区分）')"""),

md("""## 1. 三种基本结构

```
① 链    A -> B -> C      控制 B 阻断
② 叉    A <- B -> C      控制 B 阻断
③ 对撞  A -> B <- C      控制 B **打开**
```

前两种符合「控制掉就干净了」的直觉，第三种反过来。"""),

code("""r = np.random.default_rng(0)

# ① 链 A -> B -> C
A1 = r.normal(0, 1, N); B1 = A1 + r.normal(0, 1, N); C1 = B1 + r.normal(0, 1, N)
# ② 叉 A <- B -> C
B2 = r.normal(0, 1, N); A2 = B2 + r.normal(0, 1, N); C2 = B2 + r.normal(0, 1, N)
# ③ 对撞 A -> B <- C
A3 = r.normal(0, 1, N); C3 = r.normal(0, 1, N); B3 = A3 + C3 + r.normal(0, 0.3, N)

def rel(a, c, b=None):
    '''a 与 c 的关系强度：不控制 b 时用相关，控制 b 时用偏回归系数。'''
    if b is None:
        return float(np.corrcoef(a, c)[0, 1])
    return float(ols(c, [a, b])[1])

print('结构        不控制 B          控制 B')
print(f'① 链       {rel(A1,C1):+.5f}          {rel(A1,C1,B1):+.5f}   <- 阻断')
print(f'② 叉       {rel(A2,C2):+.5f}          {rel(A2,C2,B2):+.5f}   <- 阻断')
print(f'③ 对撞     {rel(A3,C3):+.5f}          {rel(A3,C3,B3):+.5f}   <- 打开！')

assert abs(rel(A1, C1)) > 0.4 and abs(rel(A1, C1, B1)) < 0.01
assert abs(rel(A2, C2)) > 0.4 and abs(rel(A2, C2, B2)) < 0.01
assert abs(rel(A3, C3)) < 0.01 and abs(rel(A3, C3, B3)) > 0.8
print()
print('-> 前两种「控制掉就干净了」，第三种「控制掉才脏」。')"""),

md("""## 2. 对撞偏差的定量：条件相关有闭式解

在联合正态下

$$\\text{Cov}(X, Y \\mid Z) = \\text{Cov}(X,Y) - \\frac{\\text{Cov}(X,Z)\\,\\text{Cov}(Z,Y)}{\\text{Var}(Z)}$$

取 $Z = X + Y + \\varepsilon$，$\\varepsilon \\sim N(0,\\sigma^2)$，则条件相关 $= -1/(1+\\sigma^2)$。"""),

code("""r = np.random.default_rng(1)
X = r.normal(0, 1, N)
Y = r.normal(0, 1, N)
sigma = 0.3
Z = X + Y + r.normal(0, sigma, N)

print(f'X 与 Y 在构造上完全独立（无任何因果关系）')
print(f'  边际 corr(X, Y)        = {np.corrcoef(X, Y)[0,1]:+.5f}')
print(f'  回归 Y ~ X 的系数      = {ols(Y, [X])[1]:+.5f}')
print(f'  回归 Y ~ X + Z 的系数  = {ols(Y, [X, Z])[1]:+.5f}   <- 凭空出现')
print()
band = np.abs(Z) < 0.2
print(f'  限定在 |Z| < 0.2 的 {band.sum():,} 个样本内:')
print(f'    corr(X, Y | 该带内)  = {np.corrcoef(X[band], Y[band])[0,1]:+.5f}')
print('    -> 分层看同样出现，所以这不是回归模型的锅，是条件化本身的效果。')
print()
theory = -1.0 / (1.0 + sigma**2)
emp = float(np.corrcoef(X[band], Y[band])[0, 1])
print(f'  闭式解 -1/(1+sigma^2) = {theory:+.5f}')
print(f'  实测（|Z|<0.2 带内）  = {emp:+.5f}')
print(f'  差 {abs(theory-emp):.4f}')
assert abs(ols(Y, [X])[1]) < 0.01, '边际上应无关'
assert ols(Y, [X, Z])[1] < -0.8, '控制对撞后应出现强负关联'
assert abs(theory - emp) < 0.02, '闭式解应与实测一致'
print()
print('-> 强度可以精确预测：sigma 越小（Z 越接近 X+Y），负关联越强。')
for s in (0.1, 0.3, 1.0, 3.0):
    print(f'   sigma={s:4.1f} -> 理论条件相关 {-1/(1+s**2):+.4f}')"""),

md("""## 3. 把 Bayes-Ball 与后门准则实现成代码

d-分离的判定用 Shachter (1998) 的 Bayes-Ball 算法：
从 $X$ 出发做 BFS，状态是「节点 + 来向」，按三种结构决定能否继续传播。"""),

code("""class DAG:
    '''最小 DAG：d-分离（Bayes-Ball）与后门准则。'''

    def __init__(self, edges):
        self.nodes = sorted({v for e in edges for v in e})
        self.par = {v: set() for v in self.nodes}
        self.ch  = {v: set() for v in self.nodes}
        for a, b in edges:
            self.par[b].add(a)
            self.ch[a].add(b)

    def ancestors(self, S):
        out, stack = set(S), list(S)
        while stack:
            v = stack.pop()
            for p in self.par.get(v, ()):
                if p not in out:
                    out.add(p); stack.append(p)
        return out

    def descendants(self, v):
        out, stack = set(), [v]
        while stack:
            u = stack.pop()
            for c in self.ch.get(u, ()):
                if c not in out:
                    out.add(c); stack.append(c)
        return out

    def d_sep(self, Xs, Ys, Zs):
        '''Z 是否 d-分离 X 与 Y。'''
        Xs, Ys, Zs = set(Xs), set(Ys), set(Zs)
        anc_Z = self.ancestors(Zs)
        seen, frontier = set(), [(x, 'up') for x in Xs]
        while frontier:
            v, d = frontier.pop()
            if (v, d) in seen:
                continue
            seen.add((v, d))
            if v in Ys:
                return False                  # 找到一条活跃路径
            if d == 'up':                     # 从子节点传上来
                if v not in Zs:
                    frontier += [(p, 'up') for p in self.par.get(v, ())]
                    frontier += [(c, 'down') for c in self.ch.get(v, ())]
            else:                             # 从父节点传下来
                if v not in Zs:
                    frontier += [(c, 'down') for c in self.ch.get(v, ())]
                if v in anc_Z:                # 对撞（或其祖先在 Z 里）-> 打开
                    frontier += [(p, 'up') for p in self.par.get(v, ())]
        return True

    def backdoor_ok(self, T, Y, Zs):
        '''后门准则：① Z 不含 T 的后代；② 删掉 T 的出边后 T ⊥ Y | Z。'''
        if set(Zs) & self.descendants(T):
            return False
        edges2 = [(a, b) for a in self.nodes for b in self.ch[a] if a != T]
        g2 = DAG(edges2) if edges2 else None
        if g2 is None:
            return True
        for v in self.nodes:                  # 补上被删成孤立的节点
            if v not in g2.par:
                g2.nodes.append(v); g2.par[v] = set(); g2.ch[v] = set()
        return g2.d_sep({T}, {Y}, set(Zs))

# 先在三种基本结构上验证 d_sep
g_chain = DAG([('A','B'), ('B','C')])
g_fork  = DAG([('B','A'), ('B','C')])
g_coll  = DAG([('A','B'), ('C','B')])
assert not g_chain.d_sep({'A'}, {'C'}, set())   and g_chain.d_sep({'A'}, {'C'}, {'B'})
assert not g_fork.d_sep({'A'}, {'C'}, set())    and g_fork.d_sep({'A'}, {'C'}, {'B'})
assert g_coll.d_sep({'A'}, {'C'}, set())    and not g_coll.d_sep({'A'}, {'C'}, {'B'})
print('✅ Bayes-Ball 在三种基本结构上与第 1 节的数值一致')

# 对撞的后代也会部分打开
g_cd = DAG([('A','B'), ('C','B'), ('B','D')])
assert g_cd.d_sep({'A'}, {'C'}, set())
assert not g_cd.d_sep({'A'}, {'C'}, {'D'})
print('✅ 控制对撞的**后代** D 同样打开路径（这是准则第 ① 条的由来）')"""),

md("""## 4. 枚举全部子集：只有一个合法

```
        X -> T, X -> Y      X 是混杂
        T -> Y              直接效应 2.0
        T -> M, M -> Y      M 是中介，经它的效应 0.9
        T -> C, Y -> C      C 是对撞
        总效应 = 2.9
```"""),

code("""EDGES = [('X','T'), ('X','Y'), ('T','Y'), ('T','M'), ('M','Y'), ('T','C'), ('Y','C')]
g = DAG(EDGES)
OBS = ['X', 'M', 'C']

def gen_dag_data(n=N, seed=1):
    r = np.random.default_rng(seed)
    Xv = r.normal(0, 1, n)
    Tv = 0.8 * Xv + r.normal(0, 1, n)
    Mv = 0.9 * Tv + r.normal(0, 1, n)
    Yv = 2.0 * Tv + 1.0 * Mv + 1.5 * Xv + r.normal(0, 1, n)
    Cv = 1.0 * Tv + 1.0 * Yv + r.normal(0, 1, n)
    return dict(X=Xv, T=Tv, M=Mv, Y=Yv, C=Cv)

D = gen_dag_data()
TOTAL, DIRECT = 2.9, 2.0
print(f'真总效应 = {TOTAL}（直接 {DIRECT} + 经 M 的 0.9*1.0 = 0.9）')
print()
print('  子集           后门准则     回归系数      与总效应之差')
results = {}
for k in range(len(OBS) + 1):
    for sub in itertools.combinations(OBS, k):
        ok = g.backdoor_ok('T', 'Y', set(sub))
        coef = float(ols(D['Y'], [D['T']] + [D[v] for v in sub])[1])
        results[sub] = (ok, coef)
        name = '{' + ', '.join(sub) + '}' if sub else '{}'
        print(f'  {name:14s} {"✓ 合法" if ok else "✗ 不合法":10s}  '
              f'{coef:+9.5f}    {coef-TOTAL:+8.5f}')

legal = [s for s, (ok, _) in results.items() if ok]
print()
print(f'✅ {len(results)} 个子集中，后门准则判定合法的只有 {len(legal)} 个：{legal}')
assert legal == [('X',)], f'应只有 {{X}} 合法，得到 {legal}'
assert abs(results[('X',)][1] - TOTAL) < 0.01, '{X} 应无偏估计总效应'

# 准则与数值一致性：合法 <=> 无偏
for sub, (ok, coef) in results.items():
    unbiased = abs(coef - TOTAL) < 0.05
    assert ok == unbiased, f'{sub}: 准则说 {ok}，数值说无偏={unbiased}'
print('✅ 「后门准则合法」与「回归无偏」在全部 8 个子集上完全一致')"""),

code("""# {X, M} 那一行不是「不太准」，它精确地估出了**直接效应**
c_xm = results[('X', 'M')][1]
print(f'{{X, M}} 的系数 = {c_xm:+.5f}')
print(f'真直接效应      = {DIRECT}')
print(f'差              = {abs(c_xm - DIRECT):.5f}')
assert abs(c_xm - DIRECT) < 0.01, '控制中介应无偏估计直接效应'
print()
print('-> 它答对了**另一个问题**。经由 M 的 0.9 凭空消失了，')
print(f'   占总效应的 {0.9/TOTAL*100:.0f}%，而没有任何统计信号提示出错：')
print('   系数稳定、置信区间正常、换 seed 也复现。')
print()
print('换 seed 复现:')
for s in (2, 3, 4):
    Ds = gen_dag_data(seed=s)
    print(f'  seed={s}: {{X}} -> {ols(Ds["Y"], [Ds["T"], Ds["X"]])[1]:+.5f}   '
          f'{{X,M}} -> {ols(Ds["Y"], [Ds["T"], Ds["X"], Ds["M"]])[1]:+.5f}')"""),

md("""## 5. M-bias：控制一个「处理前」变量制造偏差

```
    U1 -> T,  U1 -> Z,  U2 -> Z,  U2 -> Y,  T -> Y (真效应 1.0)

    U1, U2 未观测；Z 在处理**之前**测到
    U1 不影响 Y、U2 不影响 T -> T 与 Y 之间本来没有混杂
```"""),

code("""r = np.random.default_rng(3)
U1 = r.normal(0, 1, N)
U2 = r.normal(0, 1, N)
Zm = 1.0 * U1 + 1.0 * U2 + r.normal(0, 0.3, N)   # 对撞，且在处理前
Tm = 1.0 * U1 + r.normal(0, 1, N)
Ym = 1.0 * Tm + 1.0 * U2 + r.normal(0, 1, N)

print(f'Z 与 T 的相关 = {np.corrcoef(Zm, Tm)[0,1]:+.4f}')
print('  -> Z 与 T 明显相关，看起来完全像一个该控制的基线协变量')
print()
print('  控制的变量集              T 的系数      偏差')
mb = {}
for tag, ctrl in [('{} 不控制', []), ('{Z} 处理前变量', [Zm]),
                  ('{Z, U1}', [Zm, U1]), ('{Z, U2}', [Zm, U2]),
                  ('{U1, U2}', [U1, U2])]:
    c = float(ols(Ym, [Tm] + ctrl)[1])
    mb[tag] = c
    print(f'  {tag:24s} {c:+9.5f}   {c-1.0:+.5f}')

assert abs(mb['{} 不控制'] - 1.0) < 0.01, '不控制时应无偏'
assert mb['{Z} 处理前变量'] < 0.75, 'M-bias 应使系数明显下偏'
assert abs(mb['{Z, U1}'] - 1.0) < 0.01, '补上 U1 应修好'
assert abs(mb['{Z, U2}'] - 1.0) < 0.01, '补上 U2 应修好'

print()
print(f'✅ 不控制时无偏（{mb["{} 不控制"]:.5f}），')
print(f'   而控制这个**处理前**变量后偏差是 {mb["{Z} 处理前变量"]-1.0:+.5f}'
      f'（真效应的 {abs(mb["{Z} 处理前变量"]-1.0)*100:.0f}%）')
print()
print('   后两行给出修补方式：补上 U1 或 U2 任意一个即可。')
print('   但它们按设定是**未观测**的 —— 你能看见制造问题的那个，')
print('   看不见能修好它的那两个。')
print()
print('   后门准则怎么判：')
g_m = DAG([('U1','T'), ('U1','Z'), ('U2','Z'), ('U2','Y'), ('T','Y')])
for zs in [set(), {'Z'}, {'Z','U1'}, {'Z','U2'}, {'U1','U2'}]:
    ok = g_m.backdoor_ok('T', 'Y', zs)
    print(f'     Z={str(sorted(zs)) if zs else "[]":16s} -> {"✓ 合法" if ok else "✗ 不合法"}')
assert g_m.backdoor_ok('T', 'Y', set()), '空集应合法（本来无混杂）'
assert not g_m.backdoor_ok('T', 'Y', {'Z'}), '{Z} 应不合法'"""),

md("""## ✏️ 练习 1：判断一个变量是好控制还是坏控制

给定 DAG、处理 $T$、结果 $Y$ 和单个变量 $v$，
实现 `classify_control(g, T, Y, v)`，返回下列之一：

- `'confounder'`：$\\{v\\}$ 满足后门准则（该控制）
- `'collider'`：$v$ 同时是 $T$ 和 $Y$ 的后代（绝不控制）
- `'mediator'`：$v$ 是 $T$ 的后代且是 $Y$ 的祖先（控制会改成直接效应）
- `'other'`：其余"""),

code("""def classify_control(g, T, Y, v):
    '''把单个变量 v 分类为 confounder / collider / mediator / other。

    判定顺序很重要：先判 collider（它也可能同时是 mediator 的后代），
    再判 mediator，最后用后门准则判 confounder。

    参数
    ----
    g : DAG 实例
    T : 处理节点名
    Y : 结果节点名
    v : 待分类的节点名

    返回
    ----
    str : 'confounder' | 'collider' | 'mediator' | 'other'
    '''
    # TODO: 用 g.descendants / g.ancestors / g.backdoor_ok 实现上述四类判定
    raise NotImplementedError"""),

code("""# 自测
_g = DAG(EDGES)          # X->T, X->Y, T->Y, T->M, M->Y, T->C, Y->C
_expect = {'X': 'confounder', 'M': 'mediator', 'C': 'collider'}
for _v, _e in _expect.items():
    _got = classify_control(_g, 'T', 'Y', _v)
    assert _got == _e, f'{_v}: 期望 {_e}，得到 {_got}'
    print(f'  {_v} -> {_got}')

# M-bias 图里 Z 既不是混杂也不是对撞（对 T,Y 而言），应归入 other
_gm = DAG([('U1','T'), ('U1','Z'), ('U2','Z'), ('U2','Y'), ('T','Y')])
_gz = classify_control(_gm, 'T', 'Y', 'Z')
assert _gz == 'other', f'M-bias 的 Z 应为 other，得到 {_gz}'
print(f'  M-bias 的 Z -> {_gz}   <- 注意它**不是**对撞（对 T,Y 而言），却依然不该控制')

# 纯结果预测变量：P -> Y，与 T 无关
_gp = DAG([('T','Y'), ('P','Y')])
assert classify_control(_gp, 'T', 'Y', 'P') == 'other'
print(f'  纯结果预测变量 P -> other')

print()
print('✅ 分类器与第 4、5 节的数值一致。')
print('   注意 other 类里同时包含「无害且降方差」（P）与「有害」（M-bias 的 Z）——')
print('   所以单变量分类**不足以**决定去留，必须看整个调整集。')"""),

md("""## ✏️ 练习 2：枚举全部合法调整集

实现 `all_valid_sets(g, T, Y, candidates)`，返回 `candidates` 的
全部满足后门准则的子集（按大小、再按字典序排序）。"""),

code("""def all_valid_sets(g, T, Y, candidates):
    '''枚举 candidates 的全部合法调整集。

    参数
    ----
    g          : DAG 实例
    T, Y       : 处理与结果节点名
    candidates : 可观测的候选变量列表

    返回
    ----
    list[tuple] : 全部满足后门准则的子集，按 (大小, 字典序) 排序
    '''
    # TODO: 用 itertools.combinations 枚举全部子集，用 g.backdoor_ok 筛选
    raise NotImplementedError"""),

code("""# 自测
_v1 = all_valid_sets(DAG(EDGES), 'T', 'Y', ['X', 'M', 'C'])
assert _v1 == [('X',)], f'该图应只有 {{X}} 合法，得到 {_v1}'
print(f'  图 1（X 混杂 / M 中介 / C 对撞）: {_v1}   ({len(_v1)}/8)')

# 两个混杂：X1, X2 各自不够，需要同时控制
_g2 = DAG([('X1','T'), ('X1','Y'), ('X2','T'), ('X2','Y'), ('T','Y')])
_v2 = all_valid_sets(_g2, 'T', 'Y', ['X1', 'X2'])
assert _v2 == [('X1', 'X2')], f'两个混杂需同时控制，得到 {_v2}'
print(f'  图 2（两个独立混杂）:              {_v2}   ({len(_v2)}/4)')

# 混杂经由一个可观测代理：控制 X 或 W 都行
_g3 = DAG([('X','T'), ('X','W'), ('W','Y'), ('T','Y')])
_v3 = all_valid_sets(_g3, 'T', 'Y', ['X', 'W'])
assert {frozenset(x) for x in _v3} == {frozenset(('X',)), frozenset(('W',)),
                                        frozenset(('X', 'W'))}, f'三个都该合法，得到 {_v3}'
print(f'  图 3（混杂经代理 W 影响 Y）:        {_v3}   ({len(_v3)}/4)')

# 无混杂：空集合法，加变量也可能合法
_g4 = DAG([('T','Y'), ('P','Y')])
_v4 = all_valid_sets(_g4, 'T', 'Y', ['P'])
assert () in _v4 and ('P',) in _v4
print(f'  图 4（无混杂 + 纯预测变量 P）:      {_v4}   ({len(_v4)}/2)')

print()
print('✅ 合法集的个数在四个图上分别是 1/8, 1/4, 3/4, 2/2 —— 差异极大。')
print('   图 3 说明合法集可以有多个：此时应选**方差最小**的那个（模块 03）。')
print('   图 1 说明也可以几乎没有：此时靠猜的成功率是 1/8 = 12.5%。')"""),

md("""## ✏️ 练习 3：量化控制中介造成的效应损失

实现 `mediated_share(direct, a_tm, b_my)`：给定直接效应、$T\\to M$ 与
$M\\to Y$ 的系数，返回**经由中介的效应占总效应的比例**。

控制中介会让这个比例的效应从报告里消失。"""),

code("""def mediated_share(direct, a_tm, b_my):
    '''经由中介的效应占总效应的比例。

    总效应 = direct + a_tm * b_my

    参数
    ----
    direct : T -> Y 的直接效应
    a_tm   : T -> M 的系数
    b_my   : M -> Y 的系数

    返回
    ----
    float : (a_tm * b_my) / 总效应
    '''
    # TODO
    raise NotImplementedError"""),

code("""# 自测：先用第 4 节的参数验证，再用模拟交叉验证
_share = mediated_share(2.0, 0.9, 1.0)
assert abs(_share - 0.9/2.9) < 1e-12, f'应为 0.9/2.9，得到 {_share}'
print(f'  第 4 节的参数: 经中介的份额 = {_share*100:.1f}%')

def _sim(direct, a_tm, b_my, n=400_000, seed=1):
    '''模拟并返回 (总效应估计, 直接效应估计)。'''
    r = np.random.default_rng(seed)
    Xv = r.normal(0, 1, n)
    Tv = 0.8 * Xv + r.normal(0, 1, n)
    Mv = a_tm * Tv + r.normal(0, 1, n)
    Yv = direct * Tv + b_my * Mv + 1.5 * Xv + r.normal(0, 1, n)
    tot = float(ols(Yv, [Tv, Xv])[1])
    dir_ = float(ols(Yv, [Tv, Xv, Mv])[1])
    return tot, dir_

print()
print('  direct  a_tm  b_my   预测份额   模拟 (总-直接)/总   差')
for _d, _a, _b in [(2.0, 0.9, 1.0), (1.0, 2.0, 1.0), (0.5, 1.0, 3.0), (3.0, 0.2, 0.5)]:
    _pred = mediated_share(_d, _a, _b)
    _tot, _dir = _sim(_d, _a, _b)
    _emp = (_tot - _dir) / _tot
    assert abs(_pred - _emp) < 0.01, f'预测 {_pred:.4f} vs 模拟 {_emp:.4f}'
    print(f'  {_d:5.1f}  {_a:4.1f}  {_b:4.1f}   {_pred*100:7.1f}%   {_emp*100:14.1f}%   {abs(_pred-_emp):.4f}')

assert mediated_share(1.0, 0.0, 5.0) == 0.0, '无 T->M 时份额为 0'
assert mediated_share(0.0, 1.0, 1.0) == 1.0, '无直接效应时份额为 1'
print()
print('✅ 预测与模拟一致。极端情形：a_tm=0 时份额 0，direct=0 时份额 100%')
print('   -> 若效应**全部**经由中介，控制中介会把报告的效应变成 0，')
print('      而这在数值上表现为「该功能没有效果」，不会表现为任何错误。')"""),

md("""## ✏️ 练习 4：M-bias 的强度取决于什么

M-bias 的大小由图上的四个系数决定。
实现 `mbias_magnitude(a1, a2, b1, b2, sz)`，用**模拟**返回控制 $Z$ 后的偏差：

```
U1 -> T (系数 a1),  U1 -> Z (b1)
U2 -> Z (b2),       U2 -> Y (a2)
T  -> Y (真效应 1.0),  Z 的噪声 sd = sz
```

用它找出偏差最大与最小的参数组合。"""),

code("""def mbias_magnitude(a1, a2, b1, b2, sz=0.3, n=300_000, seed=3):
    '''控制 Z 后 T 系数的偏差（相对真效应 1.0）。

    参数
    ----
    a1 : U1 -> T
    a2 : U2 -> Y
    b1 : U1 -> Z
    b2 : U2 -> Z
    sz : Z 的噪声标准差
    n, seed : 模拟规模与随机种子

    返回
    ----
    float : ols(Y, [T, Z]) 的 T 系数 - 1.0
    '''
    # TODO: 按上面的 DAG 生成 U1, U2, Z, T, Y（T->Y 真效应 1.0），
    #       返回 ols(Y, [T, Z])[1] - 1.0
    raise NotImplementedError"""),

code("""# 自测
# ① 基准：复现第 5 节的数值
_b0 = mbias_magnitude(1.0, 1.0, 1.0, 1.0, sz=0.3)
print(f'  基准 (a1=a2=b1=b2=1, sz=0.3): 偏差 = {_b0:+.5f}')
assert -0.40 < _b0 < -0.25, f'应约为 -0.31，得到 {_b0:.5f}'

# ② 断开任一条边，M-bias 消失
print()
print('  断开一条边:')
for _tag, _kw in [('a1=0 (U1 不影响 T)', dict(a1=0.0)),
                  ('a2=0 (U2 不影响 Y)', dict(a2=0.0)),
                  ('b1=0 (U1 不影响 Z)', dict(b1=0.0)),
                  ('b2=0 (U2 不影响 Z)', dict(b2=0.0))]:
    _kwargs = dict(a1=1.0, a2=1.0, b1=1.0, b2=1.0)
    _kwargs.update(_kw)
    _b = mbias_magnitude(**_kwargs)
    print(f'    {_tag:22s} 偏差 = {_b:+.5f}')
    assert abs(_b) < 0.02, f'{_tag}: 断开后 M-bias 应消失，得到 {_b:.5f}'

# ③ Z 的噪声越大，M-bias 越弱（Z 对两个 U 的信息越少）
print()
print('  Z 的噪声 sz 的影响:')
_prev = None
for _sz in (0.1, 0.3, 1.0, 3.0, 10.0):
    _b = mbias_magnitude(1.0, 1.0, 1.0, 1.0, sz=_sz)
    print(f'    sz={_sz:5.1f}  偏差 = {_b:+.5f}')
    if _prev is not None:
        assert _b > _prev - 1e-6, f'噪声越大偏差应越接近 0：sz={_sz}'
    _prev = _b
assert abs(mbias_magnitude(1.0, 1.0, 1.0, 1.0, sz=10.0)) < 0.05, \\
    'Z 噪声极大时 Z 几乎不含 U 的信息，M-bias 应消失'

print()
print('✅ M-bias 需要**四条边同时存在**，断任一条即消失。')
print('   这解释了为什么它在实践中的量级常常很小：')
print('   它要求 Z 同时是两个混杂的强后代，而这四个系数的乘积很容易接近 0。')
print('   -> 本节的论点不是「不要控制处理前变量」，')
print('      而是「时间先后不是判据」—— 判据只能是图。')"""),

md("""## 📖 参考答案"""),

code("""def classify_control(g, T, Y, v):
    '''把单个变量 v 分类为 confounder / collider / mediator / other。'''
    desc_T = g.descendants(T)
    desc_Y = g.descendants(Y)
    if v in desc_T and v in desc_Y:
        return 'collider'
    if v in desc_T and Y in g.descendants(v):
        return 'mediator'
    if g.backdoor_ok(T, Y, {v}) and not g.backdoor_ok(T, Y, set()):
        return 'confounder'
    return 'other'

def all_valid_sets(g, T, Y, candidates):
    '''枚举 candidates 的全部合法调整集。'''
    out = []
    for k in range(len(candidates) + 1):
        for sub in itertools.combinations(sorted(candidates), k):
            if g.backdoor_ok(T, Y, set(sub)):
                out.append(sub)
    return sorted(out, key=lambda s: (len(s), s))

def mediated_share(direct, a_tm, b_my):
    '''经由中介的效应占总效应的比例。'''
    med = a_tm * b_my
    total = direct + med
    if total == 0:
        return 0.0
    return float(med / total)

def mbias_magnitude(a1, a2, b1, b2, sz=0.3, n=300_000, seed=3):
    '''控制 Z 后 T 系数的偏差。'''
    r = np.random.default_rng(seed)
    u1 = r.normal(0, 1, n)
    u2 = r.normal(0, 1, n)
    z  = b1 * u1 + b2 * u2 + r.normal(0, sz, n)
    t  = a1 * u1 + r.normal(0, 1, n)
    y  = 1.0 * t + a2 * u2 + r.normal(0, 1, n)
    return float(ols(y, [t, z])[1] - 1.0)

print('参考答案已定义。')
print()
print('要点：')
print('  1. classify_control 里判定**顺序**是必要的：collider 先于 mediator，')
print('     因为一个节点可以同时是某条中介链的后代和某个对撞。')
print('  2. 「合法调整集」的个数在不同图上从 1/8 到 2/2 —— 靠直觉挑的成功率不可预期。')
print('  3. 控制中介损失的效应份额 = a_tm*b_my/总效应，可以精确预测。')
print('  4. M-bias 需要四条边同时存在；它的实践意义不是禁令，而是「时间不是判据」。')"""),

md("""## 🧪 真实工程胶囊：把 DAG 写进代码仓库

下面这段代码把「该控制哪些变量」从一次性的讨论变成一个**可执行的断言**：
DAG 用一个显式的边列表声明在代码里，特征工程从它推导，
而 CI 可以在图变化时提醒相关的估计代码需要复核。

关键设计：`adjustment_set()` **不接受**手工指定的变量列表——
它只接受图和可观测变量集，然后自己算。
这样「往模型里多加一个特征」就不再是一行改动，
而必须先在图里说明这个特征的位置。"""),

code("""SPEC = {
    # 一个简化的推荐位实验的因果假设（真实项目里这段应该有注释说明每条边的依据）
    'edges': [
        ('user_tenure',   'exposure'),      # 老用户更可能进灰度（分桶按注册时间）
        ('user_tenure',   'engagement'),    # 老用户本身更活跃
        ('exposure',      'ctr'),           # 曝光 -> 点击率（中介）
        ('ctr',           'engagement'),    # 点击 -> 参与度
        ('exposure',      'engagement'),    # 直接效应
        ('engagement',    'support_ticket'),# 参与度 -> 客服工单
        ('exposure',      'support_ticket'),# 曝光 -> 客服工单（对撞的一半）
        ('device_tier',   'engagement'),    # 纯结果预测变量
    ],
    'treatment': 'exposure',
    'outcome':   'engagement',
    'observable': ['user_tenure', 'ctr', 'support_ticket', 'device_tier'],
}

def adjustment_set(spec, prefer='min_size'):
    '''从图推导调整集。不接受手工指定的变量列表。'''
    gg = DAG(spec['edges'])
    valid = all_valid_sets(gg, spec['treatment'], spec['outcome'], spec['observable'])
    if not valid:
        raise ValueError('该图下不存在合法调整集：必须换设计（模块 04）或补数据')
    chosen = valid[0] if prefer == 'min_size' else valid[-1]
    return gg, valid, chosen

gg, valid, chosen = adjustment_set(SPEC)
print(f'候选可观测变量: {SPEC["observable"]}')
print(f'合法调整集共 {len(valid)} 个（候选子集共 {2**len(SPEC["observable"])} 个）:')
for v in valid:
    print(f'    {v}')
print()
print(f'选用（最小）: {chosen}')
print()
print('每个候选变量的角色:')
for v in SPEC['observable']:
    role = classify_control(gg, SPEC['treatment'], SPEC['outcome'], v)
    verdict = {'confounder': '必须控制', 'mediator': '不要控制（会变成直接效应）',
               'collider': '绝不控制', 'other': '看整个调整集'}[role]
    print(f'  {v:16s} {role:11s} {verdict}')

print()
print('CI 断言（图变化时这些会失败，提示复核）:')
assert 'user_tenure' in chosen, 'user_tenure 是混杂，必须在调整集里'
assert 'ctr' not in chosen, 'ctr 是中介，控制它会把总效应换成直接效应'
assert 'support_ticket' not in chosen, 'support_ticket 是对撞，绝不能控制'
print('  ✅ 混杂在集内；中介、对撞都不在集内')

print()
print('注意 device_tier：它是纯结果预测变量。')
print(f'  在合法集里出现的次数: {sum(1 for v in valid if "device_tier" in v)}/{len(valid)}')
print('  它加不加都合法 —— 加上它不改变识别，但会**降低方差**。')
print('  这是八类变量里唯一「白拿」的一类（见正文的好控制/坏控制表）。')
print()
print('工程含义：')
print('  · 图是代码的一部分，改图需要 review，和改模型一样。')
print('  · 「多加一个特征」不再是一行改动 —— 必须先说明它在图里的位置。')
print('  · 图错了这套机制也会给出错的答案；它保证的是**假设可见**，不是假设正确。')"""),
]
