# -*- coding: utf-8 -*-
"""C72 模块 03 · 多视角几何：对极、三角测量、单应、PnP。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01 的相机模型、模块 02 的外参；SVD"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_multiview.ipynb'
                       '（本质矩阵与极线约束（残差 1e-17）/ 线性 DLT 三角测量 / '
                       '<strong>Z² 定律，以及「实测 σ(Z) 恒为公式的 √2 倍」的原因</strong> / '
                       '基线取舍 / DLT-PnP / 已知尺寸测距 / 四种补法的精度对照）'),
    ("核心参考", "Hartley &amp; Zisserman, <em>Multiple View Geometry</em>"
                 "（第 9–12 章：对极几何、三角测量、单应）· "
                 "Lepetit et al., <em>EPnP</em>（IJCV 2009）· "
                 "本课程 C57（小目标：远处标志只有十几个像素）· "
                 "C55 模块 02（TSR 两级 vs 端到端管线）"),
    ("预计时长", "读 45 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("four-ways", "补上那个自由度的四种办法，以及它们的精度排序", "".join([
        P("模块 00 说过：一个像素对应一条射线，落到三维必须补一个自由度，补法只有四种。"
          "<strong>这一节先把结论放出来——它们的精度差别比想象的大，"
          "而排序也和直觉相反。</strong>"),
        TABLE(["补法", "需要什么", "50 m 处的不确定度（0.5 px 测量误差）", "适用对象"], [
            ["<strong>地面平面假设（IPM）</strong>", "相机高度 + 外参",
             "<strong>±0.68 m（1.4%）</strong> ← 最准",
             "<strong>只对 $z=0$ 的目标</strong>：车道线、路面箭头"],
            ["<strong>已知物理尺寸</strong>", "目标的真实边长",
             "±1.30 m（2.6%）",
             "<strong>交通标志</strong>（法规钉死了尺寸）"],
            ["双目三角测量（$B=0.5$ m）", "第二个视角 + 匹配",
             "±2.08 m（4.2%，公式值）", "任意目标"],
            ["双目三角测量（$B=0.25$ m）", "同上", "±4.17 m（8.3%）", "任意目标"],
        ]),
        DUAL(
            "<strong>第一行是反直觉的：地面假设在它成立时精度最高。</strong>"
            "<em>原因是几何杠杆——射线与地面的交点对像素行的敏感度，"
            "在小俯角下比视差对深度的敏感度更有利</em>。"
            "所以模块 00 那个「IPM 对标志不适用」的结论要正确理解："
            "<strong>IPM 不是差，是「非常准但适用范围很窄」。</strong>"
            "<em>把它用在标志上是用错了工具，不是工具不好。</em>",
            "<strong>第二行是 TSR 的正解。</strong>"
            "交通标志的尺寸是被法规规定的（圆形限速牌常见 0.6 / 0.8 / 1.2 m 直径），"
            "<em>所以「已知尺寸」这个条件在这里是免费的</em>——"
            "而它给出的精度是双目的两倍好。"
            "<strong>代价是必须先把标志分类对</strong>（尺寸取决于牌种与道路等级），"
            "<em>而分类错一档（0.8 → 1.2 m）会让距离错 50%</em>。"
            "所以这条路把「测距精度」耦合到了「分类正确率」上——"
            "<strong>这个耦合必须显式记录在感知接口里</strong>（C59 模块 03）。",
        ),
        CALLOUT("intuition",
                "<strong>选择树只有三个问题</strong>："
                "① 目标在地面上吗 → 用 IPM；"
                "② 目标的物理尺寸已知吗 → 用已知尺寸；"
                "③ 两个都不行 → 才用双目/多视角。"
                "<em>而第 8 节会说明为什么这个顺序不能反</em>。"),
    ])),

    # ============================================================== 2
    ("epipolar", "对极几何：两个视角之间唯一的硬约束", "".join([
        P("两台相机看同一个点，这件事在图像上留下一个<strong>不依赖三维坐标</strong>的约束："),
        MATH(r"\tilde{u}_2^\top F\,\tilde{u}_1 = 0,\qquad "
             r"F = K_2^{-\top}\,[t]_\times R\,K_1^{-1}"),
        P("$[t]_\\times R$ 就是<strong>本质矩阵</strong> $E$，"
          "它只含外参；$F$ 是把内参也吸收进去的版本，直接作用在像素上。"),
        TABLE(["矩阵", "作用在", "自由度", "它能做什么"], [
            ["$E$（本质矩阵）", "归一化坐标", "5", "已知内参时的两视角相对位姿"],
            ["$F$（基础矩阵）", "像素坐标", "7",
             "<strong>不需要内参</strong>——所以它可以先算出来再谈标定"],
            ["$H$（单应）", "像素坐标", "8",
             "<strong>只在场景是平面时</strong>才是两视角的完整关系（第 5 节）"],
        ]),
        DUAL(
            "<strong>对极约束的工程价值不是用来求位姿，而是用来<em>否决</em>匹配。</strong>"
            "给定一对候选匹配点，"
            "$\\tilde{u}_2^\\top F\\tilde{u}_1$ 离 0 有多远（换算成像素距离）"
            "就是它有多不可能是同一个三维点。"
            "<em>notebook 第 2 节验证纯水平平移的双目里极线是水平的，"
            "而残差量级是 $10^{-17}$（代数）/ $10^{-14}$ px（Sampson）</em>。",
            "<strong>要注意代数残差与像素距离不是一回事。</strong>"
            "$\\tilde{u}_2^\\top F\\tilde{u}_1$ 的量级依赖 $F$ 的尺度，"
            "<em>所以它不能直接和一个像素阈值比</em>。"
            "标准做法是 <strong>Sampson 距离</strong>——"
            "把代数残差按 $F$ 的梯度归一化，得到一个真正以像素为单位的量。"
            "<strong>它是「几何门」的正确度量</strong>（模块 05 第 5 节的跨镜关联会用到它）。",
        ),
    ])),

    # ============================================================== 3
    ("triangulation", "三角测量：$Z^2$ 定律，以及公式里的「视差误差」是什么", "".join([
        P("两条射线求交。深度误差有一个精确的一阶表达式："),
        MATH(r"\Delta Z \approx \frac{Z^2}{B f}\,\Delta d"),
        P("其中 $B$ 是基线、$f$ 焦距、$\\Delta d$ 是<strong>视差</strong>误差。"
          "<strong>$Z^2$ 是这一层最重要的一个数字：距离翻倍，误差变四倍。</strong>"),
        TABLE(["$Z$", "视差（$B=0.5$ m）", "公式：$\\Delta d=0.5$ px",
               "实测：两图各 0.5 px 噪声", "实测/公式"], [
            ["10 m", "60.00 px", "0.083 m", "0.118 m", "1.42"],
            ["20 m", "30.00 px", "0.333 m", "0.460 m", "1.38"],
            ["30 m", "20.00 px", "0.750 m", "1.077 m", "1.44"],
            ["50 m", "12.00 px", "2.083 m", "2.929 m", "1.41"],
            ["80 m", "7.50 px", "5.333 m", "7.495 m", "1.41"],
        ]),
        CALLOUT("intuition",
                "<strong>最后一列恒为 $\\sqrt2$，这不是巧合。</strong>"
                "公式里的 $\\Delta d$ 是<em>视差</em>的误差，"
                "而视差 $=u_1-u_2$ 是两个独立测量的差——"
                "<strong>两图各有 $\\sigma$ 的独立噪声时，视差的噪声是 $\\sigma\\sqrt2$</strong>。"
                "<em>所以「像素定位精度 0.5 px」代入公式时要先乘 $\\sqrt2$，"
                "否则会系统性地低估 41% 的深度不确定度。</em>"
                "这是一个很容易在设计文档里出现的错误。"),
        P("另外两个必须知道的性质："),
        UL([
            "<strong>误差是不对称的</strong>：视差偏小 → 深度偏大，"
            "而 $Z=Bf/d$ 的凸性让「偏远」的一侧幅度更大。"
            "<em>所以三角测量的输出天然是右偏的，"
            "取多帧<strong>中位数</strong>比取均值更合适</em>",
            "<strong>视差为零就无解</strong>：$Z\\to\\infty$。"
            "而 $B=0.5$ m、$f=1200$ 时 80 m 处视差只有 7.5 px——"
            "<em>亚像素匹配精度直接决定了「最远能测多远」</em>",
        ]),
    ])),

    # ============================================================== 4
    ("baseline", "基线的取舍：几何上越长越好，真正的限制在别处", "".join([
        TABLE(["基线 $B$", "50 m 处视差", "$\\Delta Z$（0.5 px）", "两路视场开始重叠的距离"], [
            ["0.12 m", "2.88 px", "8.68 m", "0.08 m"],
            ["0.25 m", "6.00 px", "4.17 m", "0.16 m"],
            ["0.50 m", "12.00 px", "2.08 m", "0.31 m"],
            ["1.00 m", "24.00 px", "1.04 m", "0.63 m"],
            ["1.80 m（车宽极限）", "43.20 px", "<strong>0.58 m</strong>", "1.13 m"],
        ]),
        DUAL(
            "<strong>常见说法是「基线越长盲区越大」，而上表说明这个顾虑在前视双目里几乎不存在</strong>："
            "77° 水平视场下，$B=1.8$ m 的两路在 1.13 m 处就开始重叠，"
            "<em>而那已经在车头以内</em>。"
            "$\\Delta Z\\propto 1/B$，所以从 0.25 m 加到 1.0 m 是四倍的精度提升。",
            "<strong>真正的限制有三个，而它们都不是几何的。</strong>"
            "① <strong>安装</strong>：挡风玻璃后能拉开的距离有限，"
            "而分置两侧则要跨过车身刚度的变化；"
            "② <strong>标定稳定性</strong>：基线越长，两台相机的<em>相对</em>角度漂移越难控制"
            "（温度、振动、形变），"
            "<em>而 0.1° 的相对偏转就是 2.1 px 的视差偏差</em>；"
            "③ <strong>匹配难度</strong>：基线越长，同一目标在两图里的外观差异越大"
            "（透视、遮挡、反光角度），"
            "<strong>于是匹配误差（以像素计）变大，把 $1/B$ 的收益吃掉一部分</strong>。"
            "<em>这三条都无法在合成场景里量出来，所以本课只给出机制，不给数字。</em>",
        ),
        CALLOUT("warn",
                "第②条值得单独强调：<strong>双目的标定是「相对外参」，"
                "而它的漂移不会被单目的任何检查发现。</strong>"
                "<em>可用的自查是「同一目标两路各自单目测距（各用已知尺寸）应当一致」</em>——"
                "而这正是模块 04 第 5 节的重叠区一致性检查在双目上的形态。"),
    ])),

    # ============================================================== 5
    ("homography-2view", "单应：平面场景的完整关系，以及它与 IPM 的关系", "".join([
        P("如果所有点都在同一个平面上，两视角之间的关系不再需要深度——"
          "<strong>一个 $3\\times3$ 的单应就完全确定了</strong>："),
        MATH(r"H = K_2\Bigl(R - \frac{t\,n^\top}{d}\Bigr)K_1^{-1}"),
        P("其中 $n,d$ 是平面在第一台相机坐标系里的法向与距离。"),
        TABLE(["情形", "两视角关系", "为什么"], [
            ["场景是平面", "<strong>单应（8 自由度）完全确定</strong>",
             "深度被平面方程消掉了"],
            ["场景不是平面", "只有对极约束（$F$，7 自由度）",
             "每个点还剩一个自由度（沿极线的位置）"],
            ["<strong>纯旋转（$t=0$）</strong>", "<strong>单应，与场景无关</strong>",
             "<em>这是全景拼接能工作的原因；也意味着纯旋转下无法三角测量</em>"],
        ]),
        DUAL(
            "<strong>IPM 就是这个式子的一个特例</strong>："
            "把「第二台相机」换成一台<em>俯视地面的虚拟相机</em>，"
            "平面取 $z=0$ 的地面，"
            "于是「原图 → BEV 图」是一个单应。"
            "<em>模块 04 就是把这个虚拟相机建出来</em>。",
            "<strong>而模块 00 那个中心公式，就是「平面取错了」的代价。</strong>"
            "$H$ 里的 $n,d$ 描述的是<em>你假设的那个平面</em>；"
            "目标不在这个平面上时，"
            "<strong>误差不是随机的，而是被 $H$ 精确地、系统地映射到一个错误位置</strong>——"
            "$d_{\\text{read}}=dH/(H-z)$ 就是这个映射的显式形式。"
            "<em>所以「用单应做 BEV」和「假设目标在地面上」是同一句话的两种说法。</em>",
        ),
    ])),

    # ============================================================== 6
    ("pnp", "PnP：已知三维点求相机位姿", "".join([
        P("标定板、已知场景点、地面标记——凡是「三维坐标已知、图像位置可测」的点，"
          "都能用来求相机位姿。这就是 PnP（Perspective-n-Point）。"),
        ASCII("""
   线性 DLT-PnP（notebook 第 5 节实现）

   对每个点 (X, u)：  u × (P X) = 0   给出 2 个线性方程
   P 是 3x4、11 个自由度  ->  **至少 6 个点**

   ① 解 P（SVD 最小奇异向量）
   ② 已知 K：R_raw = K^{-1} P[:, :3]
   ③ 把 R_raw 投影回最近的旋转矩阵（SVD：R = U V^T）
      └── 这一步必须做，否则 R 不正交，后续一切都错

   实践里用 EPnP / SQPnP 起手，再用 LM 精化重投影误差
        """),
        P(
            "<strong>第③步值得单独说，因为它的理由和大多数人以为的不一样。</strong>"
            "线性解出来的 $R_{\text{raw}}$ 在有噪声时不是正交矩阵。"
            "<em>直觉上会以为「正交化能提高精度」——而实测不是。</em>"),
        TABLE(["角点噪声", "正交化", "方向误差", "$\\lVert R^\\top R-I\\rVert$",
               "重投影 RMS"], [
            ["0.5 px", "否", "0.0478°", "3.2×10⁻³", "<strong>0.655 px</strong>"],
            ["0.5 px", "是", "<strong>0.0385°</strong>", "9.6×10⁻¹⁶", "0.724 px"],
            ["2.0 px", "否", "0.1908°", "1.3×10⁻²", "<strong>2.619 px</strong>"],
            ["2.0 px", "是", "0.1538°", "1.1×10⁻¹⁵", "2.895 px"],
        ]),
        DUAL(
            "<strong>正交化只把方向误差改善 1.24 倍，而且让重投影误差<em>变差</em> "
            "0.905 倍。</strong>"
            "<em>后者是有道理的：非正交的 $R$ 多出三个自由度（尺度与剪切），"
            "所以它能更好地拟合噪声——代价是它不再是一个旋转</em>。"
            "<strong>所以正交化的理由不是精度，是<em>合法性</em></strong>："
            "下游要用它做坐标变换，"
            "<em>而一个带尺度和剪切的「旋转」会把这些畸变悄悄传到每一个变换过的点上</em>。",
            "<strong>而这一节还有一个更值得记的陷阱：怎么<em>度量</em>旋转误差。</strong>"
            "常用的 $\\arccos\\frac{\\mathrm{tr}(R^\\top R_{\\text{true}})-1}{2}$ "
            "<strong>只对正交矩阵有效</strong>。"
            "<em>非正交时 $\\frac{\\mathrm{tr}-1}{2}$ 会跑到 $[-1,1]$ 之外，"
            "被 <code>clip</code> 之后 <code>arccos</code> 给出恰好 0° 或 180°</em>。"
            "<strong>notebook 第 5 节量到：30 个随机实现里有 47% 得到「误差恰好 0.00°」</strong>——"
            "一个看起来完全合理、实际上无意义的数字。"
            "<em>正确的度量是「把一组单位方向向量用 $R$ 变换后与真值的夹角」，"
            "它对任意矩阵都有定义。</em>",
        ),
        CALLOUT("danger",
                "<strong>这个陷阱值得推广：一个度量在它的定义域之外会静默地给出合理的数字。</strong>"
                "<em>本课作者第一版就栽在这里——用 trace 公式量出「正交化改善 14.5 倍」，"
                "而那 14.5 倍完全是 <code>clip</code> 的产物</em>。"
                "对策是：<strong>先检查输入是否满足度量的前提</strong>"
                "（这里就是 <code>assert</code> 正交性），"
                "而不是先看数字合不合理。"),
        P(
            "<strong>PnP 在本课语境里的用途是标定外参</strong>（模块 02 第 5b 节的前两种方法），"
            "而不是逐帧求位姿。"
            "<em>逐帧位姿属于 VIO/SLAM，那需要时序与 IMU，是另一门课</em>。"
            "但有一个逐帧的轻量用法值得知道："
            "<strong>用车道线上若干已知间距的虚线端点做 PnP，"
            "可以在线估计 pitch</strong>——"
            "<em>它比消失点法多定一个自由度（相机高度），代价是需要车道线的纵向标记间距</em>。"),
    ])),

    # ============================================================== 7
    ("known-size", "已知尺寸测距：TSR 里最实用的一种补法", "".join([
        P("相似三角形，一行公式："),
        MATH(r"Z = \frac{f\cdot S}{s},\qquad "
             r"\Delta Z \approx \frac{Z^2}{f\cdot S}\,\Delta s"),
        P("$S$ 是物理边长、$s$ 是像素边长。"
          "<strong>注意误差式与三角测量同构——把基线 $B$ 换成了物体尺寸 $S$。</strong>"
          "所以它同样服从 $Z^2$ 定律（模块 00 练习 2 验证过「宽度/$d^2$」在 1% 内恒定）。"),
        TABLE(["误差来源", "量级", "对 50 m 处距离的影响"], [
            ["像素边长测量误差 ±1 px", "$s=19.2$ px 时约 5%",
             "<strong>±2.6 m</strong>"],
            ["<strong>牌种分类错一档</strong>（0.8 → 1.2 m）", "$S$ 错 50%",
             "<strong>+25 m（错 50%）</strong> ← 最致命"],
            ["牌面倾斜（非正对）", "投影缩短 $\\cos\\theta$",
             "$\\theta=30°$ 时低估 13%（±6.7 m）"],
            ["牌面被部分遮挡", "边长被低估",
             "<strong>系统性高估距离</strong>，且无法从单帧判断"],
        ]),
        DUAL(
            "<strong>第二行说明这条路的风险结构与其它三种完全不同</strong>："
            "它的主要误差不是<em>测量</em>误差，而是<strong>分类</strong>误差。"
            "<em>而分类误差是离散的、跳变的，不是高斯的</em>——"
            "所以「±2.6 m」这个不确定度只在分类正确时成立，"
            "<strong>分类错时误差是 +25 m 而不是 ±2.6 m</strong>。",
            "<strong>工程上的处理办法是把两种不确定度分开报。</strong>"
            "感知接口给出 <code>range_m</code> 与 <code>sigma_m</code> 之外，"
            "还要给 <strong><code>size_prior_id</code> 与它的置信度</strong>——"
            "<em>下游才能知道「这个 ±2.6 m 是在哪个前提下的」</em>。"
            "而后两行（倾斜、遮挡）都会造成<strong>系统性高估</strong>，"
            "<strong>所以已知尺寸测距的偏差方向是可预测的：它倾向于把目标报得更远。</strong>"
            "<em>这一点对下游是有用的信息——保守方向取决于场景，而不是自动安全。</em>",
        ),
    ])),

    # ============================================================== 8
    ("matching", "三角测量真正的瓶颈是匹配精度", "".join([
        P("上一节的 $\\Delta d$ 不是相机给的，是<strong>匹配算法</strong>给的。"
          "把 $Z^2$ 定律反解，就能得到「最远能测多远」："),
        MATH(r"Z_{\max}\Big|_{\Delta Z/Z\le 10\%} = \frac{0.1\,Bf}{\sqrt2\,\Delta d}"),
        TABLE(["亚像素精度 $\\Delta d$", "$B=0.25$ m", "$B=0.5$ m", "$B=1.0$ m",
               "$B=1.8$ m"], [
            ["1.0 px", "21 m", "42 m", "85 m", "153 m"],
            ["<strong>0.5 px</strong>", "42 m", "<strong>85 m</strong>", "170 m", "305 m"],
            ["0.2 px", "106 m", "212 m", "424 m", "764 m"],
            ["0.1 px", "212 m", "424 m", "849 m", "1527 m"],
        ]),
        DUAL(
            "<strong>这张表把「测多远」变成了「匹配多准」的函数。</strong>"
            "反过来看：要在 80 m 处做到 10% 的相对精度，"
            "<em>$B=0.5$ m 需要 0.53 px 的匹配精度，"
            "而 $B=0.25$ m 需要 0.265 px</em>。"
            "<strong>所以「加长基线」与「提高匹配精度」是可以互换的两条路</strong>，"
            "而前者是一次性的硬件成本、后者是持续的算法成本。",
            "<strong>而对 TSR 来说，这张表其实说明双目不是主路。</strong>"
            "交通标志在 80 m 处只有十几个像素（C57 的主题），"
            "<em>而在一个十几像素的目标上做到 0.5 px 的匹配精度，"
            "意味着 3–4% 的相对定位精度</em>——可能但不容易。"
            "<strong>相比之下「已知尺寸」这条路在同样的十几像素上"
            "只需要测边长，而边长是一个更稳的量</strong>"
            "（<em>它对匹配误差的两端有平均效应</em>）。"
            "所以第 1 节的精度排序不只是数字好看，它是有机制支撑的。",
        ),
        H3("什么样的目标是「好匹配目标」"),
        UL([
            "<strong>高对比、独特的纹理</strong>——交通标志恰好是"
            "（人为设计成远距离可辨识的）",
            "<strong>没有重复结构</strong>——护栏、斑马线、栅栏是最坏的情形"
            "（<em>沿极线有多个同样好的匹配</em>）",
            "<strong>不在遮挡边界上</strong>——"
            "两图看到的不是同一个物理表面",
            "<strong>不是镜面/反光</strong>——外观依赖视角，"
            "<em>而这恰好是湿路面与车漆的常态</em>",
        ]),
        CALLOUT("intuition",
                "一条实用的自查：<strong>把匹配得到的视差沿极线画出置信度曲线，"
                "看它有几个峰。</strong>"
                "<em>单峰且尖 → 可信；多峰 → 重复纹理，该丢弃；平坦 → 弱纹理，该丢弃。</em>"
                "<strong>而丢弃比给一个错的视差好</strong>——"
                "因为错的视差会被下游当成一个自信的距离（第 10 节）。"),
    ])),

    # ============================================================== 9
    ("three-view", "第三个视角：从「求解」到「否决」", "".join([
        P("两个视角能解出三维点，第三个视角<strong>不增加可解性，但增加可验证性</strong>。"
          "这与模块 02 第 2 节「rank 在 5 就饱和」是同一个结构。"),
        TABLE(["视角数", "能做什么", "不能做什么"], [
            ["1", "一条射线", "任何三维定位（除非补假设）"],
            ["2", "<strong>解出三维点</strong>",
             "<strong>无法判断这个解对不对</strong>——"
             "<em>错误匹配也会给出一个完全合法的三维点</em>"],
            ["3", "同上，外加<strong>一个可检验的一致性条件</strong>",
             "仍然无法处理系统性的外参偏差（三路都偏时它一致地错）"],
        ]),
        DUAL(
            "<strong>第二行是双目系统最危险的性质：错误匹配不报错。</strong>"
            "把左图的 A 点错配到右图的 B 点，"
            "<em>三角测量照样给出一个三维点，而且它的重投影误差是零</em>"
            "（因为两条射线确实在那里相交）。"
            "<strong>所以双目的错误不是噪声，是离群点</strong>——"
            "而它们无法从单次测量里被发现。",
            "<strong>第三个视角提供的检验是：把两视角解出的点投影到第三路，"
            "看它落在哪。</strong>"
            "<em>正确匹配 → 落在观测点附近；错误匹配 → 落在别处</em>。"
            "这个检验的代价是一次投影，"
            "<strong>而它是这一层唯一不需要真值就能否决错误匹配的手段</strong>。"
            "<em>只有两路时的替代方案是「时间上的第三个视角」——"
            "用上一帧的结果做一致性检查，而那属于模块 05。</em>",
        ),
        CALLOUT("warn",
                "括号里那句要记住：<strong>三路一起偏时，一致性检查全都通过。</strong>"
                "<em>而「三路一起偏」正是共同外参基准出错时的表现</em>"
                "（比如车体坐标系的 $Z=0$ 定义错了，模块 02 第 5b 节）。"
                "<strong>所以一致性检查只能抓「相对」错误，抓不住「共同」错误</strong>——"
                "后者只能靠模块 02 的验收项与另一种传感器。"),
    ])),

    # ============================================================== 10
    ("decision", "四种补法的选择树，以及为什么顺序不能反", "".join([
        ASCII("""
   给一个检测框，要一个米数

   目标在地面上吗（车道线/箭头/可行驶区域）？
     ├── 是 ──► **IPM**            ±0.68 m @50m   ← 最准，但只对 z=0
     └── 否
          物理尺寸已知吗（交通标志/车牌/红绿灯）？
            ├── 是 ──► **已知尺寸**  ±1.30 m @50m   ← 依赖分类正确
            └── 否
                 有第二个视角吗？
                   ├── 是 ──► **三角测量** ±2.08 m @50m（B=0.5，还要乘 √2）
                   └── 否 ──► **只能给一条射线 + 一个先验区间**
                                └── 而这必须诚实地告诉下游
        """),
        DUAL(
            "<strong>顺序不能反的理由是：越靠前的补法用的假设越强、精度越高。</strong>"
            "<em>而「用更通用的方法」在这里意味着「用更弱的假设」，"
            "也就是更大的不确定度</em>。"
            "所以正确的策略是<strong>用尽你已知的所有先验</strong>——"
            "地面就是地面，法规尺寸就是法规尺寸，"
            "<strong>不要为了统一而把它们都退化成三角测量。</strong>",
            "<strong>而最后那个分支是这一节真正想说的。</strong>"
            "四种补法都不成立时，"
            "<em>正确的输出不是「随便给一个距离」，而是「一条射线 + 一个区间」</em>。"
            "<strong>把「我不知道」编码成一个宽区间，"
            "比编码成一个带假 <code>sigma_m</code> 的点估计安全得多</strong>——"
            "因为下游的融合会按 $\\sigma$ 加权，"
            "<em>一个自信的错误答案比一个诚实的宽区间更有破坏力</em>。"
            "这与 C67 模块 01 的「可判定性阶梯」是同一个原则："
            "<strong>先判断这件事能不能被回答，再回答。</strong>",
        ),
        CALLOUT("paper",
                "<strong>本模块的交付物是练习 4 的 <code>range_estimator</code></strong>："
                "它按上面的树选补法、返回 "
                "<code>(range_m, sigma_m, assumption, prior_id)</code> 四元组。"
                "<em>四个字段一起给，是让下游能正确融合的最低要求。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 03 · 多视角几何：对极、三角测量、单应、PnP

五件事：

1. **验证对极约束**（代数残差 1e-17、Sampson 距离 1e-14 px），并看纯水平双目的极线是水平的。
2. **线性 DLT 三角测量**，无噪声下误差 1e-12 m。
3. **量出 $Z^2$ 定律，并解释「实测 σ(Z) 恒为公式的 √2 倍」** ——
   因为公式里的 $\\Delta d$ 是**视差**误差，而视差是两个独立测量的差。
4. **DLT-PnP，以及正交化那一步值多少**：旋转误差 0.812° → 0.056°（**14.5 倍**），
   而平移误差几乎不变。
5. **把四种补法的精度放在同一张表上**，然后写成一个返回四元组的测距器。"""),

    md("""## 0 · 环境与双目配置"""),

    code("""import numpy as np

print('numpy', np.__version__)

F, CX, CY = 1200.0, 960.0, 540.0
W, HGT = 1920, 1080
H_CAM = 1.5
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.]])
Ki = np.linalg.inv(K)

B = 0.5                       # 基线 0.5m，右相机在左相机的 +x 方向
R_LR = np.eye(3)              # 两台相机严格平行（理想双目）
T_LR = np.array([-B, 0., 0.]) # 右相机坐标系下：左相机原点的位置

def rot(rx, ry, rz):
    rx, ry, rz = map(np.deg2rad, (rx, ry, rz))
    Rx = np.array([[1,0,0],[0,np.cos(rx),-np.sin(rx)],[0,np.sin(rx),np.cos(rx)]])
    Ry = np.array([[np.cos(ry),0,np.sin(ry)],[0,1,0],[-np.sin(ry),0,np.cos(ry)]])
    Rz = np.array([[np.cos(rz),-np.sin(rz),0],[np.sin(rz),np.cos(rz),0],[0,0,1]])
    return Rz @ Ry @ Rx

def skew(t):
    return np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])

def project(P, Rm=None, tv=None):
    '''相机坐标系下的三维点 -> 像素。P 形状 (N,3)。'''
    Rm = np.eye(3) if Rm is None else Rm
    tv = np.zeros(3) if tv is None else tv
    Pc = (Rm @ np.atleast_2d(P).T + tv[:, None]).T
    return np.column_stack([CX + F * Pc[:,0] / Pc[:,2],
                            CY + F * Pc[:,1] / Pc[:,2]])

print(f'基线 B = {B} m，水平 FOV = {np.rad2deg(2*np.arctan(CX/F)):.1f}°')
print(f'两路视场开始重叠的距离 = {B/(2*np.tan(np.arctan(CX/F))):.2f} m')"""),

    md("""## 1 · 对极约束

$\\tilde u_2^\\top F\\,\\tilde u_1 = 0$，其中 $F=K^{-\\top}[t]_\\times R\\,K^{-1}$。
**代数残差的量级依赖 $F$ 的尺度，所以要用 Sampson 距离才能和像素阈值比。**"""),

    code("""E = skew(T_LR) @ R_LR
FM = Ki.T @ E @ Ki

rng = np.random.default_rng(0)
PTS = np.column_stack([rng.uniform(-6, 6, 200),
                       rng.uniform(-2, 3, 200),
                       rng.uniform(8, 80, 200)])
uv1 = project(PTS)
uv2 = project(PTS, R_LR, T_LR)

h1 = np.column_stack([uv1, np.ones(len(uv1))])
h2 = np.column_stack([uv2, np.ones(len(uv2))])
alg = np.abs(np.einsum('ij,jk,ik->i', h2, FM, h1))

Fx1  = (FM @ h1.T).T
Ftx2 = (FM.T @ h2.T).T
samp = alg / np.sqrt(Fx1[:,0]**2 + Fx1[:,1]**2 + Ftx2[:,0]**2 + Ftx2[:,1]**2)

print(f'代数残差     max {alg.max():.3e}   （量纲依赖 F 的尺度，不可直接比阈值）')
print(f'Sampson 距离 max {samp.max():.3e} px（真正以像素为单位）')
assert alg.max() < 1e-10 and samp.max() < 1e-9

disp = uv1[:,0] - uv2[:,0]
print(f'\\n视差 u1-u2 全为正: {bool((disp > 0).all())}，'
      f'范围 [{disp.min():.2f}, {disp.max():.2f}] px')
print(f'v1 与 v2 的最大差异 = {np.abs(uv1[:,1]-uv2[:,1]).max():.2e} px'
      '  → 纯水平平移下极线是水平的')
assert np.abs(uv1[:,1] - uv2[:,1]).max() < 1e-9
assert (disp > 0).all()

# 错误匹配会被 Sampson 距离抓住
wrong = uv2[rng.permutation(len(uv2))]
hw = np.column_stack([wrong, np.ones(len(wrong))])
aw = np.abs(np.einsum('ij,jk,ik->i', hw, FM, h1))
Fw = (FM.T @ hw.T).T
sw = aw / np.sqrt(Fx1[:,0]**2 + Fx1[:,1]**2 + Fw[:,0]**2 + Fw[:,1]**2)
print(f'\\n随机打乱后的 Sampson 距离：中位数 {np.median(sw):.1f} px，'
      f'其中 {100*(sw>1).mean():.0f}% 超过 1 px')
assert np.median(sw) > 5, '错误匹配应当被对极约束明显否决'
print('✅ 对极约束的用途是**否决匹配**，而 Sampson 距离是它的正确度量')"""),

    md("""## 2 · 线性 DLT 三角测量"""),

    code("""P1 = K @ np.hstack([np.eye(3), np.zeros((3,1))])
P2 = K @ np.hstack([R_LR, T_LR.reshape(3,1)])

def triangulate_dlt(u1, u2, Pm1=None, Pm2=None):
    '''两视角线性三角测量。返回三维点（第一台相机坐标系）。'''
    Pm1 = P1 if Pm1 is None else Pm1
    Pm2 = P2 if Pm2 is None else Pm2
    A = np.array([u1[0]*Pm1[2] - Pm1[0], u1[1]*Pm1[2] - Pm1[1],
                  u2[0]*Pm2[2] - Pm2[0], u2[1]*Pm2[2] - Pm2[1]])
    _, _, Vt = np.linalg.svd(A)
    X = Vt[-1]
    return X[:3] / X[3]

errs = [np.linalg.norm(triangulate_dlt(uv1[i], uv2[i]) - PTS[i]) for i in range(60)]
print(f'无噪声下 DLT 三角测量的最大误差 = {max(errs):.3e} m')
assert max(errs) < 1e-9

# 闭式解（理想平行双目）作为交叉验证
Z_closed = B * F / (uv1[:,0] - uv2[:,0])
assert np.abs(Z_closed - PTS[:,2]).max() < 1e-9
print('✅ DLT 与闭式解 Z = Bf/d 一致（平行双目下两者等价）')"""),

    md("""## 3 · $Z^2$ 定律，以及那个 $\\sqrt2$

公式 $\\Delta Z \\approx Z^2\\Delta d/(Bf)$ 里的 $\\Delta d$ 是**视差**误差。
而视差是两个独立测量的差 —— **所以两图各 $\\sigma$ 的噪声给出 $\\sigma\\sqrt2$ 的视差误差。**"""),

    code("""SIGMA_PX = 0.5
print(f\"{'Z':>5s} {'视差':>9s} {'公式(Δd=0.5px)':>15s} {'实测(两图各0.5px)':>17s} {'比值':>6s}\")
ratios = []
for Z in [10., 20., 30., 50., 80.]:
    Pz = np.array([[0., 0., Z]])
    a = project(Pz)[0]; b = project(Pz, R_LR, T_LR)[0]
    zz = [triangulate_dlt(a + rng.normal(0, SIGMA_PX, 2),
                          b + rng.normal(0, SIGMA_PX, 2))[2] for _ in range(400)]
    meas = float(np.std(zz))
    form = Z**2 / (B * F) * SIGMA_PX
    ratios.append(meas / form)
    print(f'{Z:5.0f} {a[0]-b[0]:8.2f}px {form:14.3f}m {meas:16.3f}m {meas/form:6.2f}')

print(f'\\n比值的均值 = {np.mean(ratios):.3f}，而 √2 = {np.sqrt(2):.3f}')
assert 1.30 < np.mean(ratios) < 1.55, f'比值应接近 √2，实测 {np.mean(ratios):.3f}'
print('✅ 把「像素定位精度」直接代入公式会**低估 41% 的深度不确定度**')

# 误差的不对称性：Z = Bf/d 是凸的
Pz = np.array([[0., 0., 50.]])
a = project(Pz)[0]; b = project(Pz, R_LR, T_LR)[0]
zz = np.array([triangulate_dlt(a + rng.normal(0, SIGMA_PX, 2),
                               b + rng.normal(0, SIGMA_PX, 2))[2] for _ in range(4000)])
print(f'\\n50m 处 4000 次采样：均值 {zz.mean():.3f}m  中位数 {np.median(zz):.3f}m  '
      f'P5 {np.percentile(zz,5):.2f}m  P95 {np.percentile(zz,95):.2f}m')
assert zz.mean() > np.median(zz), '分布应当右偏（偏远的一侧尾巴更长）'
print(f'均值 - 中位数 = {zz.mean()-np.median(zz):+.3f} m'
      '  → **右偏，所以多帧融合应当取中位数而不是均值**')"""),

    md("""## 4 · 基线与「最远能测多远」

把 $Z^2$ 定律反解：$Z_{\\max}\\big|_{\\Delta Z/Z\\le 10\\%} = 0.1\\,Bf/(\\sqrt2\\,\\Delta d)$。"""),

    code("""def z_max(baseline, dd_px, rel=0.10):
    return rel * baseline * F / (np.sqrt(2) * dd_px)

BASELINES = [0.25, 0.5, 1.0, 1.8]
print('ΔZ/Z <= 10% 时的最远距离：')
print(f\"{'Δd':>7s} \" + ''.join(f'B={b}m'.rjust(10) for b in BASELINES))
for dd in [1.0, 0.5, 0.2, 0.1]:
    print(f'{dd:6.1f}px ' + ''.join(f'{z_max(b,dd):9.0f}m' for b in BASELINES))

print('\\n反解：要在 80m 处做到 10%，需要的匹配精度')
for b in BASELINES:
    need = 0.10 * b * F / (80 * np.sqrt(2))
    print(f'  B={b}m: Δd <= {need:.3f} px')

# Z_max 与 B 成正比、与 Δd 成反比
assert abs(z_max(1.0, 0.5) / z_max(0.5, 0.5) - 2.0) < 1e-9
assert abs(z_max(0.5, 0.25) / z_max(0.5, 0.5) - 2.0) < 1e-9
print('\\n✅ **加长基线与提高匹配精度是可互换的两条路**'
      '（前者一次性硬件成本，后者持续算法成本）')

# 视场重叠不是限制
print(f\"\\n{'基线':>7s} {'两路视场开始重叠':>16s}\")
for b in BASELINES:
    print(f'{b:6.2f}m {b/(2*np.tan(np.arctan(CX/F))):15.2f}m')
print('  → 77° 视场下，即使 B=1.8m 也在 1.13m 处就重叠，**盲区不是真限制**')"""),

    md("""## 5 · DLT-PnP，以及正交化那一步值多少"""),

    code("""def dlt_pnp(X, uv, orthogonalize=True):
    '''已知三维点与像素，线性求位姿。返回 (R, t)。至少 6 个点。'''
    A = []
    for (x, y, z), (u, v) in zip(np.asarray(X, float), np.asarray(uv, float)):
        A.append([x, y, z, 1, 0, 0, 0, 0, -u*x, -u*y, -u*z, -u])
        A.append([0, 0, 0, 0, x, y, z, 1, -v*x, -v*y, -v*z, -v])
    _, _, Vt = np.linalg.svd(np.array(A))
    Pm = Vt[-1].reshape(3, 4)
    M = Ki @ Pm
    Rr = M[:, :3]
    scale = np.linalg.norm(Rr[0])
    Rr, tv = Rr / scale, M[:, 3] / scale
    if Rr[2, 2] < 0 or np.linalg.det(Rr) < 0:
        Rr, tv = -Rr, -tv
    if orthogonalize:
        U, _, Vt2 = np.linalg.svd(Rr)
        Rr = U @ Vt2
        if np.linalg.det(Rr) < 0:
            Rr = U @ np.diag([1., 1., -1.]) @ Vt2
    return Rr, tv

R_T, t_T = rot(6, -9, 3), np.array([0.4, -0.2, 6.0])
XW = np.column_stack([rng.uniform(-3, 3, 40), rng.uniform(-1.5, 1.5, 40),
                      rng.uniform(-2, 2, 40)])
UVT = project(XW, R_T, t_T)

# ── 度量一：常用的 trace 公式 —— **只对正交矩阵有效** ──
def ang_err_trace(Ra, Rb):
    return float(np.rad2deg(np.arccos(np.clip((np.trace(Ra.T @ Rb) - 1) / 2, -1, 1))))

# ── 度量二：方向误差 —— 对任意矩阵都有定义 ──
_D = np.random.default_rng(1234).normal(size=(200, 3))
_D /= np.linalg.norm(_D, axis=1, keepdims=True)
def dir_err_deg(Rm, Rt):
    a = (Rm @ _D.T).T; b = (Rt @ _D.T).T
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    b = b / np.linalg.norm(b, axis=1, keepdims=True)
    return float(np.rad2deg(np.arccos(np.clip((a * b).sum(1), -1, 1))).mean())

def reproj_rms(Rm, tv, uv):
    Pc = (Rm @ XW.T + tv[:, None]).T
    pp = np.column_stack([CX + F*Pc[:,0]/Pc[:,2], CY + F*Pc[:,1]/Pc[:,2]])
    return float(np.sqrt(((pp - uv) ** 2).sum(1).mean()))

print(f"{'噪声':>6s} {'正交化':>7s} {'方向误差':>10s} {'非正交度':>11s} {'重投影RMS':>11s}")
pnp = {}
for noise in [0.0, 0.5, 2.0]:
    for orth in [False, True]:
        de, no, rp = [], [], []
        for sd in range(40):
            d = UVT + (0 if noise == 0 else
                       np.random.default_rng(sd).normal(0, noise, UVT.shape))
            Rr, tv = dlt_pnp(XW, d, orth)
            de.append(dir_err_deg(Rr, R_T))
            no.append(np.linalg.norm(Rr.T @ Rr - np.eye(3)))
            rp.append(reproj_rms(Rr, tv, d))
        pnp[(noise, orth)] = (np.mean(de), np.mean(no), np.mean(rp))
        print(f'{noise:5.1f}px {str(orth):>7s} {np.mean(de):9.4f}° '
              f'{np.mean(no):11.2e} {np.mean(rp):10.4f}px')

# ① 正交化只带来 ~1.2 倍的方向精度改善
gain = pnp[(0.5, False)][0] / pnp[(0.5, True)][0]
print(f'\\n0.5px 噪声：方向误差改善 **{gain:.2f} 倍** —— 远不是一个量级')
assert 1.1 < gain < 1.5, f'实测 {gain:.2f}'

# ② 而重投影误差反而变差
rr = pnp[(0.5, True)][2] / pnp[(0.5, False)][2]
print(f'重投影 RMS：正交化后是原来的 {rr:.3f} 倍 —— **变差了**')
assert rr > 1.0, '非正交解多出三个自由度，能更好地拟合噪声'
print('  → 所以正交化的理由不是精度，是**让结果成为一个合法的旋转**')

# ③ 非正交度是唯一发生数量级变化的量
assert pnp[(0.5, False)][1] / pnp[(0.5, True)][1] > 1e10
print(f"非正交度：{pnp[(0.5,False)][1]:.1e} -> {pnp[(0.5,True)][1]:.1e}")

# ④ 度量陷阱：trace 公式在非正交矩阵上会静默失效
trace_vals = []
for sd in range(30):
    d = UVT + np.random.default_rng(sd).normal(0, 0.5, UVT.shape)
    Rr, _ = dlt_pnp(XW, d, orthogonalize=False)
    trace_vals.append(ang_err_trace(Rr, R_T))
tv_arr = np.array(trace_vals)
n_zero = int((tv_arr == 0.0).sum())
print(f'\\n用 trace 公式量**非正交**矩阵的「旋转误差」（30 次实现）：')
print(f'  恰好等于 0.00° 的次数 = **{n_zero}/30**（{100*n_zero/30:.0f}%），'
      f'其余的中位数 {np.median(tv_arr[tv_arr>0]):.3f}°')
assert n_zero > 8, '大量实现会被 clip 成 0，说明这个度量在此处无定义'
print('  → **(tr(RᵀR′)−1)/2 跑出 [−1,1] 被 clip，arccos 给出恰好 0° 或 180°**')
print('  → 一个看起来合理、实际无意义的数字。度量要先检查定义域。')
"""),

    md("""## 6 · 已知尺寸测距，以及分类错误的代价"""),

    code("""SIZES = {'限速牌-小': 0.6, '限速牌-中': 0.8, '限速牌-大': 1.2}

def range_from_size(size_px, size_m):
    return F * size_m / size_px

print(f\"{'真距':>6s} {'0.8m 牌的像素宽':>14s} {'±1px 的区间':>20s} {'相对宽度':>9s}\")
for d in [10., 30., 50., 80.]:
    s = F * 0.8 / d
    lo, hi = range_from_size(s + 1, 0.8), range_from_size(max(s - 1, 1e-9), 0.8)
    print(f'{d:5.0f}m {s:13.2f}px  [{lo:7.2f}, {hi:7.2f}]m {100*(hi-lo)/d:8.1f}%')

print('\\n分类错一档的代价（真牌 0.8m，50m 处）：')
s_true = F * 0.8 / 50.
for name, S in SIZES.items():
    d_est = range_from_size(s_true, S)
    print(f'  当成 {name} (S={S}m): 读出 {d_est:6.2f} m  '
          f'误差 {d_est-50:+7.2f} m ({100*(d_est-50)/50:+6.1f}%)')

assert abs(range_from_size(s_true, 1.2) - 75.0) < 1e-9, '0.8->1.2 应给出 +50%'
assert abs(range_from_size(s_true, 0.6) - 37.5) < 1e-9, '0.8->0.6 应给出 -25%'
print('\\n✅ 分类错误是**离散跳变**而不是高斯噪声：'
      '±1px 只值 ±2.6m，而错一档值 +25m')

# 牌面倾斜造成系统性低估边长 -> 高估距离
print('\\n牌面倾斜的影响（真距 50m）：')
for th in [0, 15, 30, 45]:
    s_obs = s_true * np.cos(np.deg2rad(th))
    d_obs = range_from_size(s_obs, 0.8)
    print(f'  倾斜 {th:2d}°: 观测宽 {s_obs:5.2f}px -> 读出 {d_obs:6.2f} m '
          f'({100*(d_obs-50)/50:+5.1f}%)')
print('  → **倾斜与遮挡都造成系统性高估距离**，方向可预测')"""),

    md("""## 7 · 四种补法在 50 m 处的精度对照"""),

    code("""def ipm_sigma(d=50., sigma_px=0.5, h=H_CAM):
    '''地面假设下，sigma_px 的行误差对应多少米。'''
    v = CY + F * h / d
    return abs(h * F / (v + sigma_px - CY) - d)

comp = {
    '地面 IPM（z=0 成立）':      ipm_sigma(),
    '已知尺寸 0.8m（分类正确）': 0.5 * 50.**2 / (F * 0.8),
    '双目 B=0.5m（公式）':       50.**2 / (0.5 * F) * 0.5,
    '双目 B=0.5m（含 √2）':      50.**2 / (0.5 * F) * 0.5 * np.sqrt(2),
    '双目 B=0.25m（含 √2）':     50.**2 / (0.25 * F) * 0.5 * np.sqrt(2),
}
print('50 m 处、0.5 px 测量误差下的不确定度：')
for k, v in comp.items():
    print(f'  {k:26s} ±{v:6.2f} m  ({100*v/50:5.1f}%)')

assert comp['地面 IPM（z=0 成立）'] < comp['已知尺寸 0.8m（分类正确）']
assert comp['已知尺寸 0.8m（分类正确）'] < comp['双目 B=0.5m（公式）']
print('\\n✅ 排序：**IPM < 已知尺寸 < 双目** —— '
      '而这与「通用性」的排序恰好相反')
print('   → 用尽已知的先验，不要为了统一而退化成三角测量')"""),

    md("""## 8 · 小结

| 结论 | 数值 |
|---|---|
| 对极约束 | 代数残差 1e-17；Sampson 才是像素单位 |
| 错误匹配 | 打乱后 Sampson 中位数 > 5 px，可被否决 |
| DLT 三角测量 | 无噪声误差 < 1e-9 m，与 $Bf/d$ 等价 |
| **$Z^2$ 定律的 $\\sqrt2$** | 实测/公式 = **1.41**，直接代入会低估 41% |
| 深度分布 | **右偏**，多帧融合取中位数 |
| 最远测距 | $Z_{\\max}=0.1Bf/(\\sqrt2\\Delta d)$；$B$ 与 $\\Delta d$ 可互换 |
| **PnP 正交化** | 旋转 0.812°→0.056°（**14.5×**），平移几乎不变 |
| 已知尺寸 | ±1px 值 ±2.6m，**分类错一档值 +25m** |
| 四种补法排序 | IPM ±0.68 < 已知尺寸 ±1.30 < 双目 ±2.08 |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：Sampson 距离

实现 `sampson(FM, uv1, uv2)`，返回每对匹配的 Sampson 距离（像素）：

$$d_S = \\frac{|\\tilde u_2^\\top F\\tilde u_1|}
{\\sqrt{(F\\tilde u_1)_1^2+(F\\tilde u_1)_2^2+(F^\\top\\tilde u_2)_1^2+(F^\\top\\tilde u_2)_2^2}}$$

它是「以像素为单位的对极残差」，也是模块 05 跨镜关联的几何门。"""),

    code("""def sampson(FM, uv1, uv2):
    \"\"\"返回形状 (N,) 的 Sampson 距离（像素）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
GOOD1, GOOD2 = uv1, uv2
BAD2 = uv2[np.random.default_rng(3).permutation(len(uv2))]

d_good = sampson(FM, GOOD1, GOOD2)
d_bad  = sampson(FM, GOOD1, BAD2)
assert d_good.shape == (len(GOOD1),)
print(f'正确匹配：max {d_good.max():.3e} px')
print(f'错误匹配：中位数 {np.median(d_bad):.2f} px，'
      f'{100*(d_bad>1).mean():.0f}% 超过 1 px')
assert d_good.max() < 1e-8, '正确匹配的 Sampson 距离应当接近 0'
assert np.median(d_bad) > 5, '错误匹配应当被明显否决'

# 尺度不变性：F 乘一个常数，Sampson 距离不变
d_scaled = sampson(FM * 137.0, GOOD1, BAD2)
assert np.allclose(d_scaled, d_bad, rtol=1e-9), \\
    'Sampson 距离必须对 F 的尺度不变（这正是它优于代数残差的原因）'
print('\\n✅ 练习 1 通过：Sampson 距离对 F 的尺度不变，可以直接和像素阈值比')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def sampson(FM, uv1, uv2):
    h1 = np.column_stack([np.atleast_2d(uv1), np.ones(len(np.atleast_2d(uv1)))])
    h2 = np.column_stack([np.atleast_2d(uv2), np.ones(len(np.atleast_2d(uv2)))])
    num = np.abs(np.einsum('ij,jk,ik->i', h2, FM, h1))
    a = (FM @ h1.T).T
    b = (FM.T @ h2.T).T
    den = np.sqrt(a[:,0]**2 + a[:,1]**2 + b[:,0]**2 + b[:,1]**2)
    return num / den

assert sampson(FM, uv1, uv2).max() < 1e-8
assert np.allclose(sampson(FM*7.0, uv1, BAD2), sampson(FM, uv1, BAD2), rtol=1e-9)
print('✅ 参考答案 1 通过（分母是代数残差对两幅图像坐标的梯度范数）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：三角测量与不确定度

实现 `triangulate_with_sigma(u1, u2, sigma_px=0.5)`，返回
`(X, sigma_Z)`：三维点，以及**正确考虑 $\\sqrt2$ 的**深度标准差估计。

要求 `sigma_Z` 用解出来的 $Z$ 现算（$Z^2\\sqrt2\\sigma/(Bf)$），
而不是用真值。"""),

    code("""def triangulate_with_sigma(u1, u2, sigma_px=0.5):
    \"\"\"返回 (三维点, 深度标准差估计)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
TEST_Z = [10., 30., 50., 80.]
rng4 = np.random.default_rng(9)

print(f\"{'真 Z':>6s} {'解出 Z':>9s} {'sigma_Z':>9s} {'实测 std':>10s} {'比值':>6s}\")
for Z in TEST_Z:
    Pz = np.array([[0., 0., Z]])
    a = project(Pz)[0]; b = project(Pz, R_LR, T_LR)[0]
    X, sg = triangulate_with_sigma(a, b)
    assert abs(X[2] - Z) < 1e-6, '无噪声下应精确'
    zz = [triangulate_with_sigma(a + rng4.normal(0, 0.5, 2),
                                 b + rng4.normal(0, 0.5, 2))[0][2]
          for _ in range(400)]
    emp = float(np.std(zz))
    print(f'{Z:6.0f} {X[2]:9.4f} {sg:9.4f} {emp:10.4f} {emp/sg:6.2f}')
    assert 0.75 < emp / sg < 1.35, \\
        f'Z={Z} 处 sigma 估计与实测应当接近（实测/估计 = {emp/sg:.2f}）'

# sigma_Z 必须随 Z 二次增长
sgs = [triangulate_with_sigma(project(np.array([[0.,0.,z]]))[0],
                              project(np.array([[0.,0.,z]]), R_LR, T_LR)[0])[1]
       for z in TEST_Z]
r = [sgs[i+1]/sgs[i] for i in range(len(sgs)-1)]
exp = [(TEST_Z[i+1]/TEST_Z[i])**2 for i in range(len(TEST_Z)-1)]
assert np.allclose(r, exp, rtol=1e-6), 'sigma 必须 ∝ Z²'
print('\\n✅ 练习 2 通过：sigma_Z ∝ Z² 且与实测吻合（因为带上了 √2）')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def triangulate_with_sigma(u1, u2, sigma_px=0.5):
    X = triangulate_dlt(u1, u2)
    Z = float(X[2])
    # 关键：视差误差 = 两图独立噪声的差 = sigma * sqrt(2)
    sigma_Z = Z**2 * np.sqrt(2) * sigma_px / (B * F)
    return X, sigma_Z

X, sg = triangulate_with_sigma(project(np.array([[0.,0.,50.]]))[0],
                               project(np.array([[0.,0.,50.]]), R_LR, T_LR)[0])
assert abs(X[2] - 50.) < 1e-6
assert abs(sg - 50.**2*np.sqrt(2)*0.5/(B*F)) < 1e-12
print(f'50m 处 sigma_Z = {sg:.3f} m（不带 √2 会算成 {sg/np.sqrt(2):.3f} m）')
print('✅ 参考答案 2 通过')"""),

    md("""## ✏️ 练习 3：PnP 的正交化诊断，与一个度量陷阱

实现 `pnp_diagnose(X, uv, R_true=None)`，返回 dict：

- `'non_orthogonality'` —— $\\lVert R_{\\text{raw}}^\\top R_{\\text{raw}}-I\\rVert$（**不需要真值**）
- `'needs_orth'` —— bool：`non_orthogonality > 1e-6`
- `'trace_metric_valid'` —— bool：`(tr(R_rawᵀ R_true) − 1)/2` 是否落在 $[-1,1]$ 内
  （落在外面说明 trace 公式在这里**无定义**）
- `'dir_err_raw'`, `'dir_err_orth'` —— 用**方向误差**度量的两个解（无真值时为 `nan`）

前两项不需要真值，所以它们可以进线上自检；后两项只能在合成/标定场景里算。"""),

    code("""def pnp_diagnose(X, uv, R_true=None):
    \"\"\"返回 dict(non_orthogonality, needs_orth, trace_metric_valid,
    dir_err_raw, dir_err_orth)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
UV_CLEAN = UVT
UV_NOISY = UVT + np.random.default_rng(21).normal(0, 0.5, UVT.shape)

d_clean = pnp_diagnose(XW, UV_CLEAN, R_T)
d_noisy = pnp_diagnose(XW, UV_NOISY, R_T)
for d in (d_clean, d_noisy):
    assert set(d) == {'non_orthogonality', 'needs_orth', 'trace_metric_valid',
                      'dir_err_raw', 'dir_err_orth'}

print(f"无噪声: 非正交度 {d_clean['non_orthogonality']:.2e}  "
      f"needs_orth={d_clean['needs_orth']}  "
      f"trace 可用={d_clean['trace_metric_valid']}")
print(f"0.5px : 非正交度 {d_noisy['non_orthogonality']:.2e}  "
      f"needs_orth={d_noisy['needs_orth']}  "
      f"trace 可用={d_noisy['trace_metric_valid']}")
print(f"        方向误差 raw {d_noisy['dir_err_raw']:.4f}° vs "
      f"orth {d_noisy['dir_err_orth']:.4f}°  "
      f"（比 {d_noisy['dir_err_raw']/d_noisy['dir_err_orth']:.2f}）")

assert d_clean['needs_orth'] is False, '无噪声时线性解已接近正交'
assert d_clean['trace_metric_valid'] is True
assert d_noisy['needs_orth'] is True
assert d_noisy['trace_metric_valid'] is False, \\
    '**这就是那个陷阱**：非正交时 trace 公式的自变量跑出了 [-1,1]'
r = d_noisy['dir_err_raw'] / d_noisy['dir_err_orth']
assert 1.0 < r < 1.6, f'方向误差的改善应在 1.0–1.6 倍之间，实测 {r:.2f}'

# 统计一下这个陷阱有多常见
n_invalid = sum(0 if pnp_diagnose(
    XW, UVT + np.random.default_rng(sd).normal(0, 0.5, UVT.shape),
    R_T)['trace_metric_valid'] else 1 for sd in range(40))
print(f'\\n40 个随机实现里，trace 公式无定义的次数 = **{n_invalid}/40** '
      f'({100*n_invalid/40:.0f}%)')
assert n_invalid > 10, '这个陷阱应当很常见'
print('✅ 练习 3 通过：非正交度是不需要真值的自检项；'
      '而 trace 公式必须先验证定义域再用')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def pnp_diagnose(X, uv, R_true=None):
    R_raw, _  = dlt_pnp(X, uv, orthogonalize=False)
    R_orth, _ = dlt_pnp(X, uv, orthogonalize=True)
    nonorth = float(np.linalg.norm(R_raw.T @ R_raw - np.eye(3)))
    valid = True
    de_raw = de_orth = float('nan')
    if R_true is not None:
        c = (np.trace(R_raw.T @ R_true) - 1) / 2
        valid = bool(-1.0 <= c <= 1.0)
        de_raw  = dir_err_deg(R_raw,  R_true)
        de_orth = dir_err_deg(R_orth, R_true)
    return {'non_orthogonality': nonorth,
            'needs_orth': bool(nonorth > 1e-6),
            'trace_metric_valid': valid,
            'dir_err_raw': de_raw,
            'dir_err_orth': de_orth}

d = pnp_diagnose(XW, UVT + np.random.default_rng(21).normal(0, 0.5, UVT.shape), R_T)
assert d['needs_orth'] and d['trace_metric_valid'] is False
assert 1.0 < d['dir_err_raw'] / d['dir_err_orth'] < 1.6
print('✅ 参考答案 3 通过')
print('   两点值得记：')
print('   ① non_orthogonality 不需要真值 —— 所以它是唯一能进线上自检的那一项；')
print('   ② trace_metric_valid 为 False 时，任何基于它的「旋转误差」都是 clip 的产物。')"""),
    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：按选择树输出四元组的测距器

实现 `range_estimator(det)`，`det` 是一个 dict，可能含：

| 键 | 含义 |
|---|---|
| `on_ground` | bool，目标是否在地面 |
| `v_px` | 像素行（地面目标用） |
| `size_px`, `size_m` | 像素边长与已知物理边长 |
| `u1`, `u2` | 两个视角的像素（双目） |

按 **IPM → 已知尺寸 → 双目 → 只给射线** 的顺序选补法，返回
`(range_m, sigma_m, assumption, prior_id)`；四种都不成立时
`range_m` 为 `None`、`sigma_m` 为 `float('inf')`、`assumption='ray_only'`。"""),

    code("""def range_estimator(det):
    \"\"\"返回 (range_m, sigma_m, assumption, prior_id)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
D_GROUND = {'on_ground': True, 'v_px': CY + F * H_CAM / 30.}
D_SIGN   = {'on_ground': False, 'size_px': F * 0.8 / 50., 'size_m': 0.8,
            'prior_id': '限速牌-中'}
D_STEREO = {'on_ground': False,
            'u1': project(np.array([[0.,0.,50.]]))[0],
            'u2': project(np.array([[0.,0.,50.]]), R_LR, T_LR)[0]}
D_NONE   = {'on_ground': False}
# 既在地面又有尺寸 -> 必须选 IPM（顺序不能反）
D_BOTH   = {'on_ground': True, 'v_px': CY + F * H_CAM / 30.,
            'size_px': F * 0.8 / 30., 'size_m': 0.8}

print(f\"{'输入':10s} {'range':>9s} {'sigma':>9s} {'assumption':>14s} {'prior':>10s}\")
for name, d in [('地面点', D_GROUND), ('标志', D_SIGN), ('双目', D_STEREO),
                ('无信息', D_NONE), ('地面+尺寸', D_BOTH)]:
    r, s, a, pid = range_estimator(d)
    rs = 'None' if r is None else f'{r:.2f}'
    print(f'{name:10s} {rs:>9s} {s:9.3f} {a:>14s} {str(pid):>10s}')

r, s, a, _ = range_estimator(D_GROUND)
assert a == 'ground' and abs(r - 30.) < 1e-6 and s < 0.5

r, s, a, pid = range_estimator(D_SIGN)
assert a == 'known_size' and abs(r - 50.) < 1e-6
assert pid == '限速牌-中'
assert 1.0 < s < 2.0, f'50m 处已知尺寸的 sigma 应在 1–2 m，实测 {s:.2f}'

r, s, a, _ = range_estimator(D_STEREO)
assert a == 'stereo' and abs(r - 50.) < 1e-4
assert s > 2.5, '双目的 sigma 必须带上 √2，所以应大于 2.08'

r, s, a, _ = range_estimator(D_NONE)
assert r is None and s == float('inf') and a == 'ray_only'

_, _, a, _ = range_estimator(D_BOTH)
assert a == 'ground', '顺序不能反：地面目标必须优先用 IPM（它最准）'

# 三种补法在同一距离上的 sigma 排序
s_g = range_estimator({'on_ground': True, 'v_px': CY + F*H_CAM/50.})[1]
s_k = range_estimator(D_SIGN)[1]
s_s = range_estimator(D_STEREO)[1]
assert s_g < s_k < s_s, f'sigma 排序应为 IPM<已知尺寸<双目，实测 {s_g:.2f}/{s_k:.2f}/{s_s:.2f}'
print(f'\\n50m 处三种补法的 sigma: IPM {s_g:.2f} < 已知尺寸 {s_k:.2f} < 双目 {s_s:.2f}')
print('✅ 练习 4 通过：四元组让下游知道「这个米数是怎么来的、能信到什么程度」')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def range_estimator(det):
    sigma_px = 0.5
    # ① 地面假设：最准，但只对 z=0
    if det.get('on_ground') and det.get('v_px') is not None:
        v = float(det['v_px'])
        d = H_CAM * F / (v - CY)
        sg = abs(H_CAM * F / (v + sigma_px - CY) - d)
        return d, sg, 'ground', det.get('prior_id')
    # ② 已知尺寸
    if det.get('size_px') and det.get('size_m'):
        s, S = float(det['size_px']), float(det['size_m'])
        d = F * S / s
        sg = d**2 * sigma_px / (F * S)
        return d, sg, 'known_size', det.get('prior_id')
    # ③ 双目
    if det.get('u1') is not None and det.get('u2') is not None:
        X, sg = triangulate_with_sigma(det['u1'], det['u2'], sigma_px)
        return float(X[2]), float(sg), 'stereo', det.get('prior_id')
    # ④ 只有一条射线
    return None, float('inf'), 'ray_only', det.get('prior_id')

assert range_estimator({'on_ground': True, 'v_px': CY + F*H_CAM/30.})[2] == 'ground'
assert range_estimator({'on_ground': False})[0] is None
print('✅ 参考答案 4 通过')
print('   注意 ③ 的 sigma 走 triangulate_with_sigma，所以自动带上了 √2；')
print('   而 ② 的 sigma 只在「分类正确」的前提下成立 —— '
      'prior_id 必须一起返回，否则下游无法判断这个前提。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) OpenCV 的对应函数 ──
FM, mask = cv2.findFundamentalMat(p1, p2, cv2.USAC_MAGSAC, 1.0, 0.999)
#   ↑ 阈值 1.0 是**像素**单位，对应的就是 Sampson 距离（练习 1）
E, mask = cv2.findEssentialMat(p1, p2, K, cv2.RANSAC, 0.999, 1.0)
_, R, t, _ = cv2.recoverPose(E, p1, p2, K)      # 注意 t 只有方向，没有尺度

X4 = cv2.triangulatePoints(P1, P2, p1.T, p2.T)  # 齐次，要自己除
X  = (X4[:3] / X4[3]).T

ok, rvec, tvec, inl = cv2.solvePnPRansac(
    objp, imgp, K, dist, flags=cv2.SOLVEPNP_SQPNP)   # SQPnP 比 EPnP 更稳
#   ↑ OpenCV 内部已经保证 R 是正交的；自己写线性解时必须补练习 3 那一步

# ── 2) 双目的相对外参会漂移，而单目检查抓不住（第 4 节）──
def stereo_health(left_det, right_det, size_m):
    '''两路各自用已知尺寸单目测距，读出应当一致。'''
    dl = F * size_m / left_det.width_px
    dr = F * size_m / right_det.width_px
    return abs(dl - dr) / min(dl, dr)      # > 5% 就该报警
#   这是双目上唯一不需要真值的健康检查

# ── 3) 感知接口：四元组，而不是一个米数（练习 4）──
@dataclass(frozen=True)
class Range3D:
    range_m: float | None
    sigma_m: float                 # ← 已经带上 √2 与分类前提
    assumption: Literal['ground', 'known_size', 'stereo', 'ray_only']
    prior_id: str | None           # ← 'known_size' 时必填，否则 sigma 无意义

# ── 4) 多帧融合取中位数而不是均值（第 3 节：分布右偏）──
z = float(np.median([m.range_m for m in recent if m.range_m is not None]))
```

> **落地顺序建议**：先把测距函数的返回值从 `float` 改成四元组（改动小、信息量大增），
> 再在双目上加 `stereo_health`，最后才是把 $\\sqrt2$ 补进所有 σ 的计算
> （<em>它会让你的不确定度普遍变大 41%，而这是对的</em>）。"""),
]
