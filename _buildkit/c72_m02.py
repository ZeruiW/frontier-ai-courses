# -*- coding: utf-8 -*-
"""C72 模块 02 · 标定：内参、外参与验收。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01 的 $K$ 与畸变模型；最小二乘与 SVD 会用就行"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_calibration.ipynb'
                       '（合成棋盘格与多视角 / Zhang 约束矩阵的 rank / '
                       'DLT 与归一化对条件数的影响 / 重投影误差的分位数与分层 / '
                       '<strong>可辨识性实验：σ(pitch) 从 3.74° 降到 0.035°，'
                       '靠的不是多拍而是扩大图像行覆盖</strong>）'),
    ("核心参考", "Zhang, <em>A Flexible New Technique for Camera Calibration</em>"
                 "（TPAMI 2000）· Hartley, <em>In Defense of the Eight-Point Algorithm</em>"
                 "（TPAMI 1997，归一化的必要性）· "
                 "本课程 C40 模块 03（消融与验收纪律）· C68 模块 04（分层门禁）"),
    ("预计时长", "读 45 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-is-calibration", "标定在求什么：一个最小化问题", "".join([
        P("标定常被说成「测量镜头的参数」。"
          "<strong>更准确的说法是：找一组参数，使得「用它们预测的像素位置」"
          "与「实际观测到的像素位置」差得最小。</strong>"),
        MATH(r"\min_{K,\;\text{dist},\;\{R_i,t_i\}}\ "
             r"\sum_i\sum_j \bigl\lVert u_{ij} - \pi(K,\text{dist},R_i,t_i,X_j)\bigr\rVert^2"),
        DUAL(
            "<strong>这个写法有三个立刻可用的推论。</strong>"
            "① <strong>标定结果是「一组参数」，不是「几个独立的物理量」</strong>——"
            "<em>参数之间可以互相补偿，所以单看某一个数对不对是没有意义的</em>"
            "（第 6 节会量出这件事有多严重）。"
            "② 目标函数是<strong>像素</strong>域的，"
            "所以它对「远处一米」和「近处一米」的权重完全不同。"
            "③ 外参 $\\{R_i,t_i\\}$ 是<strong>被顺带求出来的</strong>——"
            "标定板每摆一次就多一组，它们不是产物而是中间变量。",
            "<strong>而这三条合起来解释了标定最常见的失败方式</strong>："
            "重投影误差很小、参数看起来很合理、"
            "<em>而把它拿去测远处的距离时系统性地偏</em>。"
            "因为像素域的目标函数在远处几乎没有梯度："
            "<strong>50 m 处 1 px ≈ 1.35 m</strong>（模块 00 已量），"
            "所以远处的米级误差在像素域里根本看不见。"
            "<strong>本模块的态度是：重投影误差是必要条件，不是充分条件</strong>——"
            "第 7 节给出必须补上的那几项。",
        ),
    ])),

    # ============================================================== 2
    ("zhang", "Zhang 的方法：一块平面板为什么够", "".join([
        P("直觉上标定需要一个三维标定物。"
          "Zhang（2000）的贡献是说明<strong>一块平面板、换几个朝向拍几张，就够了</strong>。"
          "论证只有三步："),
        OL([
            "标定板在自己的坐标系里是 $Z=0$ 的平面，"
            "所以「板 → 图像」是一个<strong>单应</strong> "
            "$H=K[r_1\\;r_2\\;t]$（8 个自由度，可由 4 个以上角点解出）",
            "$r_1,r_2$ 是旋转矩阵的两列，因此<strong>正交且等长</strong>。"
            "把这两个条件写出来，就得到关于 "
            "$\\omega=K^{-\\top}K^{-1}$ 的<strong>两个线性方程</strong>",
            "$\\omega$ 是对称的 $3\\times3$、齐次，"
            "所以有 <strong>5 个自由度</strong>；"
            "每个视角给 2 个方程 → <strong>至少 3 个视角</strong>。"
            "解出 $\\omega$ 后由 Cholesky 反解 $K$",
        ]),
        P("notebook 第 2 节把约束矩阵的 rank 直接算出来，验证这个计数："),
        TABLE(["采集配置", "约束矩阵", "rank", "可解？"], [
            ["1 个视角", "2×6", "2", "❌ 欠定"],
            ["2 个视角（不同朝向）", "4×6", "4", "❌ 欠定"],
            ["<strong>3 个视角（不同朝向）</strong>", "6×6", "<strong>5</strong>",
             "<strong>✅ 刚好可解</strong>"],
            ["5 个视角（不同朝向）", "10×6", "5", "✅（rank 已饱和）"],
        ]),
        CALLOUT("intuition",
                "注意第四行：<strong>rank 在 5 就饱和了。</strong>"
                "再多拍不会增加<em>可辨识性</em>，只会降低<em>噪声</em>。"
                "<strong>这是两件不同的事</strong>——"
                "而下一节说明「多拍」在某些配置下连噪声都降不了。"),
    ])),

    # ============================================================== 3
    ("degenerate", "退化配置：多拍不能替代换朝向", "".join([
        P("上一节的关键词是「<strong>不同朝向</strong>」。"
          "如果几张图之间只差平移、或只绕光轴旋转，"
          "<strong>那么无论拍多少张，约束都是同一批。</strong>"),
        TABLE(["采集配置", "张数", "rank", "结论"], [
            ["纯平移（板只在前后左右移动，朝向不变）", "5", "<strong>2</strong>",
             "<strong>❌ 与只拍 1 张等价</strong>"],
            ["只绕光轴转（板在图像里转圈，法向不变）", "5", "<strong>2</strong>",
             "<strong>❌ 同样等价于 1 张</strong>"],
            ["只绕一个轴倾斜（每张倾斜 8°、方向相同）", "5", "5",
             "✅ 可解——<em>倾斜一个轴就够了</em>"],
            ["不同朝向（俯仰 + 偏航 + 滚转都变）", "5", "5", "✅ 可解且条件数最好"],
        ]),
        DUAL(
            "<strong>前两行是真实采集里最常犯的错。</strong>"
            "「把板举着在相机前面走一圈」——那是纯平移；"
            "「把板转着拍一圈」——如果板始终正对相机，那是绕光轴转。"
            "<em>两者都会得到一堆看起来很不一样的图片，而数学上它们是同一张</em>。"
            "<strong>症状是：标定「成功」了、重投影误差也不大，"
            "但 $f$ 与主点的解严重依赖初值。</strong>",
            "<strong>第三行是个好消息</strong>："
            "只需要绕<em>一个</em>轴倾斜就能让 rank 到 5。"
            "所以采集协议可以很简单："
            "<strong>把板往前后倾一倾、再往左右倾一倾，各拍几张</strong>，"
            "覆盖 ±30° 左右。"
            "<em>而「倾斜」必须是板法向相对光轴的倾斜，"
            "不是板在画面里的位置变化——这是最容易被采集人员误解的一句话。</em>"
            "notebook 第 2 节把这两种情形都跑出来，"
            "<strong>rank 的差别是 2 vs 5，非常好判</strong>。",
        ),
        CALLOUT("danger",
                "<strong>把 rank 检查写进标定脚本，在优化之前跑。</strong>"
                "它只需要各视角的单应矩阵，代价是一次 SVD。"
                "<em>而它能在采集现场就告诉你「这批图不够，再倾一倾重拍」</em>——"
                "比拿回去标完发现不对便宜得多。"),
    ])),

    # ============================================================== 4
    ("dlt", "线性解与非线性精化的分工", "".join([
        P("标定几乎总是两段式："),
        ASCII("""
   ① 线性解（DLT / Zhang 的闭式解）
        把约束写成 A h = 0，取最小奇异向量
        优点：无需初值、一步出结果
        缺点：**最小化的是代数误差，不是像素误差**

   ② 非线性精化（Levenberg–Marquardt）
        以①为初值，最小化真正的重投影误差
        同时把畸变系数放进来一起优化
        优点：目标函数是我们真正关心的量
        缺点：需要初值，会陷局部极小
        """),
        DUAL(
            "<strong>为什么不能只做①？</strong>"
            "因为代数误差 $\\lVert Ah\\rVert$ 与像素误差之间差一个"
            "依赖点位置的权重——"
            "<em>结果是①会系统性地偏向图像中远离主点的点</em>。"
            "<strong>而为什么不能只做②？</strong>"
            "因为它需要初值，"
            "<em>而 $f$ 的初值差一倍时 LM 经常收敛到一个荒谬的解</em>"
            "（畸变系数会把一切吸收掉）。",
            "<strong>①里有一个几乎总被建议的预处理：点坐标归一化</strong>"
            "（Hartley 1997）。"
            "直接用像素坐标（量级 $10^3$）与齐次 1 混在一起，"
            "$A$ 的列量级差很大，<em>本课的配置下条件数到 $1.8\\times10^{7}$</em>。"
            "标准做法是先把点平移到质心、缩放到平均距离 $\\sqrt2$，"
            "解完再变换回去。"
            "<strong>notebook 第 3 节把它量了一遍，"
            "而结果与教科书的常见说法不完全一样。</strong>",
        ),
        H3("归一化到底换来什么：一个诚实的测量"),
        TABLE(["条件", "归一化", "cond($A$)", "$H$ 的相对误差"], [
            ["<strong>无噪声</strong>", "否", "1.7×10¹⁹", "1.04×10⁻¹³"],
            ["<strong>无噪声</strong>", "是", "2.8×10¹⁵", "<strong>2.27×10⁻¹⁵</strong>"],
            ["角点噪声 0.2 px", "否", "1.8×10⁷", "1.62×10⁻³"],
            ["角点噪声 0.2 px", "是", "1.7×10³", "1.86×10⁻³"],
            ["角点噪声 1.0 px", "否", "3.6×10⁶", "9.88×10⁻³"],
            ["角点噪声 1.0 px", "是", "3.2×10²", "9.93×10⁻³"],
        ]),
        DUAL(
            "<strong>无噪声那两行：归一化把误差从 $1.04\\times10^{-13}$ 降到 "
            "$2.27\\times10^{-15}$，改善 45.8 倍——数值收益是真实的。</strong>"
            "<em>而一旦加上 0.2 px 的角点噪声，两者都变成 $\\sim1.7\\times10^{-3}$，"
            "差别只有 13%，而且是归一化<strong>略差</strong>；噪声升到 1.0 px 时差别是 0%</em>。"
            "notebook 里还试了点聚集（只占板的一角）与点近共线两种更糟的分布，"
            "<strong>以及把 $A$ 降到 float32——归一化在这些条件下同样测不出精度收益</strong>。",
            "<strong>所以准确的说法是：归一化改善的是「数值条件」，"
            "而不是真实标定里的精度上限。</strong>"
            "<em>因为真实标定的误差被角点检测噪声支配（$\\sim10^{-3}$），"
            "它比任何数值误差都大好几个数量级</em>。"
            "<strong>结论不是「别做归一化」——它零成本、把条件数改善 4 个数量级（$1.1\\times10^{4}$）、"
            "而且在无噪声或极低噪声的合成/仿真场景里确实值 45.8 倍。</strong>"
            "结论是：<strong>不要把它当成精度手段</strong>。"
            "<em>想提高标定精度，该投入的是角点检测的亚像素精度与采集配置"
            "（第 6 节的 106 倍就在那里），而不是数值技巧。</em>",
        ),
    ])),

    # ============================================================== 5
    ("extrinsics", "外参：1° 值多少米，以及它在行驶中会变", "".join([
        P("模块 00 已经量过俯仰角误差的代价，这里把它放到标定的语境里复述一遍，"
          "因为它是决定「标定要做到多准」的唯一依据："),
        TABLE(["距离", "1 px 定位误差", "1° 俯仰误差", "1° 相当于"], [
            ["10 m", "0.055 m", "1.35 m", "24.4 px"],
            ["30 m", "0.492 m", "16.13 m", "32.8 px"],
            ["<strong>50 m</strong>", "1.351 m", "<strong>69.63 m</strong>",
             "<strong>51.5 px</strong>"],
            ["80 m", "2.667 m", "1078.74 m", "404.5 px"],
        ]),
        P("<strong>注意 80 m 那一行：抬头 1° 时地面交点跑到 1158 m。</strong>"
          "这不是数值不稳定，是几何本身——射线快要与地面平行了。"),
        DUAL(
            "<strong>所以外参的精度要求不是「越准越好」，而是可以反解出来的。</strong>"
            "如果规控要求 50 m 处的纵向误差不超过 2 m，"
            "那么按上表的斜率反解，俯仰角误差必须小于 <strong>0.066°</strong>"
            "（notebook 第 6 节用二分法算出这个阈值）。"
            "<em>而第 6 节会告诉你：用最常见的采集方式，σ(pitch) 是 3.74°——"
            "差 57 倍</em>。",
            "<strong>还有一个静态标定管不了的问题：外参在行驶中会变。</strong>"
            "悬挂在加减速时让车体俯仰，"
            "<em>而相机是固定在车体上的</em>。"
            "急刹时车头下沉造成的俯仰变化通常在<strong>零点几度</strong>的量级——"
            "按上表，这已经足以在 50 m 处产生十几米的误差。"
            "<strong>所以生产系统里 pitch 通常是「在线估计」的</strong>："
            "用地平线、车道线的消失点、或 IMU 来逐帧修正。"
            "<em>本课不实现在线估计（那需要真实序列），"
            "但把它列为模块 05 的一个输入</em>。",
        ),
        CALLOUT("warn",
                "一个常见的误解是「静态标定做准了就行」。"
                "<strong>上表说明：静态标定的精度上限和行驶中的动态变化是同一个量级</strong>，"
                "<em>所以只做静态标定、不做在线修正，"
                "远距离的米数在物理上就是不可靠的</em>——"
                "这不是工程质量问题，是设计选择问题，"
                "而它必须被显式记录在感知接口的 `sigma_m` 里（C59 模块 03）。"),
    ])),

    # ============================================================== 5b
    ("extrinsic-methods", "外参怎么标：三种方法与它们各自缺什么", "".join([
        P("内参可以在实验室里用标定板搞定，"
          "而<strong>外参必须在装车之后、在车体坐标系里标</strong>。"
          "常用的三种方法解决的是不同的自由度。"),
        TABLE(["方法", "怎么做", "能定几个自由度", "缺什么"], [
            ["<strong>地面标定板</strong>",
             "在车前地面上按已知位置摆几块板/贴几个标记，"
             "用 PnP（模块 03 第 4 节）解 $R,t$",
             "<strong>全部 6 个</strong>",
             "需要一块平整、可测量的场地；"
             "<em>而地面不平会直接变成 pitch 误差</em>"],
            ["<strong>已知场景点</strong>",
             "用全站仪/卷尺测出若干固定点的车体坐标，再 PnP",
             "全部 6 个，精度最高",
             "最贵；<em>且每台车都要做一次</em>"],
            ["<strong>车道线消失点</strong>",
             "直行时两条车道线在图像上的交点 = 前进方向的消失点，"
             "由它直接读出 pitch 与 yaw",
             "<strong>只有 2 个</strong>（pitch, yaw）",
             "<strong>定不了 roll、也定不了相机高度</strong>；"
             "<em>但它可以逐帧做，所以是在线修正的标准手段</em>"],
        ]),
        DUAL(
            "<strong>第三行值得单独说，因为它是「静态标定 + 在线修正」这个组合的基础。</strong>"
            "消失点法只需要一段直路和车道线检测，"
            "<em>而它恰好定的是第 5 节里最贵的那两个自由度</em>。"
            "所以生产系统的分工通常是："
            "<strong>装车时用地面标定板把 6 个自由度都标一次（离线、慢、准），"
            "行驶中用消失点把 pitch/yaw 逐帧修正（在线、快、只管 2 个）</strong>。",
            "<strong>而三种方法有一个共同的坑：它们都依赖「车体坐标系」这个约定。</strong>"
            "$Z=0$ 是什么——地面？后轴中心所在的水平面？空车还是满载？"
            "<em>相机高度 $H$ 随载重变化几厘米，"
            "而模块 00 的中心公式里 $H$ 出现在分母上</em>："
            "$H$ 从 1.50 m 变到 1.45 m，"
            "<strong>对离地 1 m 的目标，读出距离的倍数从 3.00 变成 3.22（差 7.4%）</strong>。"
            "所以标定文档必须写明「$Z=0$ 指哪个平面、车辆处于什么载荷状态」——"
            "<strong>这句话看起来像形式主义，而它值几个百分点。</strong>",
        ),
        CALLOUT("warn",
                "一个可以立刻加的自查：<strong>把标定得到的相机高度与卷尺量的值比一比。</strong>"
                "<em>如果差超过 3 cm，说明你的 $Z=0$ 平面定义与标定时的假设不一致</em>——"
                "而这个偏差会以第 6 节那种「参数互相吸收」的方式藏进 pitch 里，"
                "在重投影误差上完全看不出来。"),
    ])),

    # ============================================================== 6
    ("identifiability", "本模块的中心结论：想标好远处，必须采近处", "".join([
        P("$c_y$ 与俯仰角对成像位置的影响几乎相同（模块 01 第 2 节的等价性）。"
          "<strong>那么标定能把它们分开吗？先看一个直接的实验。</strong>"),
        P("把 $c_y$ 故意标错 10 px，再用一个俯仰角去补偿。结果是："),
        TABLE(["任务", "补偿后的误差", "结论"], [
            ["单相机测距（像素 → 米）", "最大 <strong>0.012 m</strong>",
             "误差<strong>几乎完全抵消</strong>"],
            ["把已知三维点投影到图像", "最大 <strong>0.21 px</strong>",
             "同样<strong>几乎完全抵消</strong>"],
        ]),
        CALLOUT("intuition",
                "<strong>这是一个我原本以为会相反的结果。</strong>"
                "常见说法是「内外参分开标会互相吸收误差，合起来在远处是错的」。"
                "<em>而实测是：吸收得非常干净，两个任务上都只剩厘米级/亚像素级残差。</em>"
                "<strong>所以问题不是「补偿会失效」，而是「这两个参数根本分不开」</strong>——"
                "它是一个可辨识性问题，不是精度问题。"),
        P("既然分不开，就该问：<strong>什么条件下能分开？</strong>"
          "把 $v$ 对 $(c_y,\\text{pitch})$ 的雅可比写出来，"
          "$\\partial v/\\partial c_y=1$ 而 "
          "$\\partial v/\\partial \\text{pitch}=f\\sec^2\\theta\\approx f\\bigl(1+(\\tfrac{v-c_y}{f})^2\\bigr)$。"
          "<strong>第二列只在 $v$ 变化很大时才与第一列分开。</strong>"
          "于是有了这张表（角点噪声 0.2 px）："),
        P("下表每一档用 20 个观测点。<strong>σ 随观测数按 $1/\\sqrt{n}$ 缩小</strong>，所以这些数只在「同样 20 个点」的前提下可比——"
          "<em>重要的是各档之间的比例，它与 $n$ 无关</em>。"),
        TABLE(["采集覆盖的图像行范围（各 20 点）", "$\\Delta v$", "条件数",
               "σ($c_y$)", "σ(pitch)"], [
            ["只用远处地面（$v$ 570–600）", "30 px", "2.1×10⁶", "78.4 px",
             "<strong>3.74°</strong>"],
            ["中等范围（$v$ 570–720）", "150 px", "1.8×10⁵", "6.7 px", "0.316°"],
            ["<strong>全画幅地面（$v$ 570–1070）</strong>", "500 px", "2.3×10⁴",
             "0.79 px", "<strong>0.035°</strong>"],
            ["再加上地平线以上的标志（$v$ 380–1070）", "690 px", "2.3×10⁴", "0.65 px",
             "0.030°"],
        ]),
        DUAL(
            "<strong>第一行与第三行差 106 倍</strong>，"
            "而两者的区别只是「有没有采近处的地面点」。"
            "<em>这条结论是反直觉的：我们关心的是远处的距离，"
            "而想把远处标准，采集必须覆盖近处</em>——"
            "因为近处的点才提供把 pitch 与 $c_y$ 分开所需的 $v$ 跨度。"
            "<strong>而最方便的采集方式（只对着远处那段路拍）恰好是最差的："
            "σ(pitch)=3.74°，比它要防的 1° 误差还大 3.7 倍。</strong>",
            "<strong>第四行说明这个收益会饱和。</strong>"
            "从 500 px 扩到 690 px，条件数几乎不动（2.3×10⁴ → 2.3×10⁴），"
            "σ(pitch) 只从 0.035° 降到 0.030°。"
            "<em>所以「把地平线以上的目标也纳入标定」不值得为它额外设计流程</em>。"
            "<strong>该做的是把地面覆盖从 30 px 扩到 500 px，"
            "而这只要求标定场地里既有近处也有远处的参照物。</strong>"
            "回到第 5 节的需求（50 m 处 2 m ⇒ pitch &lt; 0.066°）："
            "<em>全画幅覆盖的 0.035° 有约 1.9 倍余量，而只采远处的 3.74° 差 57 倍</em>。",
        ),
    ])),

    # ============================================================== 7
    ("acceptance", "重投影误差：必要但不充分，且必须报分位数", "".join([
        P("重投影误差是标定唯一的<strong>内生</strong>质量指标——它不需要外部真值。"
          "但它有两个用法上的陷阱。"),
        H3("陷阱一：只报均值"),
        P("角点检测偶尔会失手（反光、遮挡、板边缘）。"
          "<strong>几个离群点能让 P95 翻几倍而均值几乎不动</strong>，"
          "而恰恰是离群点在污染解。"
          "所以验收要报 <strong>中位数 / P95 / 最大值</strong> 三个数，"
          "<em>并把 P95 作为门禁阈值</em>。"),
        H3("陷阱二：不按图像位置分层"),
        P("模块 01 量过畸变是纯边缘现象（0.26 → 197.7 px）。"
          "<strong>相应地，畸变模型的误差也集中在边缘</strong>。"
          "只报全图平均，会把画幅角上的问题平均掉——"
          "<em>而画幅角正是近处标志所在的位置</em>。"),
        H3("陷阱三：重投影误差可以靠「把板拍远」变小"),
        P("固定一个物理角点定位误差（比如 0.5 mm），"
          "它对应的像素误差是 $f\\delta/D$——<strong>与板到相机的距离成反比</strong>："),
        TABLE(["板距 $D$", "0.5 mm 物理误差 → 像素误差", "0.24 m 宽的板占多少像素"], [
            ["0.5 m", "1.20 px", "576 px"],
            ["1.0 m", "0.60 px", "288 px"],
            ["2.0 m", "<strong>0.30 px</strong>", "<strong>144 px</strong>"],
        ]),
        P("<strong>把板从 0.5 m 挪到 2 m，重投影误差降到 1/4，"
          "而板的像素面积降到 1/16。</strong>"
          "<em>后者意味着约束变弱、畸变的边缘区域根本覆盖不到</em>——"
          "也就是说<strong>这是一次「指标变好而标定变差」的改动</strong>。"
          "所以重投影误差必须与「角点总数」和「板覆盖的图像面积比例」一起报，"
          "<em>单独一个 0.3 px 是无法解读的</em>。"),
        TABLE(["验收项", "阈值（示例）", "为什么是这一项"], [
            ["重投影误差中位数", "&lt; 0.3 px", "基本质量"],
            ["<strong>重投影误差 P95</strong>", "&lt; 0.8 px",
             "<strong>抓离群点污染</strong>"],
            ["<strong>离群点占比</strong>（&gt; 5×中位数）", "&lt; 0.02",
             "<strong>P95 只在离群点占比 &gt; 5% 时才动</strong>；"
             "<em>占比 1.2% 时 P95 完全看不见，只有这一项抓得住</em>。"
             "阈值取 5 倍而非 3 倍，因为 3 倍在干净数据上就有 4.3% 假阳性"],
            ["<strong>画幅外圈 1/3 区域的 P95</strong>", "&lt; 1.2 px",
             "<strong>抓「只用中心区域标定」</strong>（模块 01 第 4 节的陷阱）"],
            ["畸变模型余量", "&ge; 1.2", "模块 01 练习 3 的单调性检查"],
            ["Zhang 约束 rank", "= 5", "第 3 节：抓退化采集"],
            ["<strong>标定采集的 $\\Delta v$ 覆盖</strong>", "&ge; 400 px",
             "<strong>第 6 节：抓「只采远处」</strong>"],
            ["σ(pitch)（由雅可比反解）", "&lt; 0.05°", "第 5/6 节：与下游需求挂钩"],
            ["<strong>角点总数与板覆盖面积比</strong>", "&ge; 400 点 / &ge; 15%",
             "<strong>陷阱三：让重投影误差变得可解读</strong>"],
            ["<strong>外圈 1/3 的角点数</strong>", "&ge; 20",
             "<strong>覆盖率高不代表覆盖到了<em>边缘</em></strong>。"
             "<em>notebook 里本课自己的 5 视角配置在这一项上只有 1 个点——"
             "其余七项全部合格</em>"],
        ]),
        CALLOUT("paper",
                "<strong>最后两项是本模块新增的、而在常见标定流程里没有的。</strong>"
                "它们的共同点是<em>只依赖采集配置，不依赖优化结果</em>——"
                "所以可以在<strong>拍完就算、优化之前就拒绝</strong>。"
                "这与 C68 模块 04 的「确定性阻断优先于统计阻断」是同一个原则。"),
    ])),

    # ============================================================== 8
    ("versioning", "标定件的版本化与清单", "".join([
        P("标定的产物是一个<strong>会过期的资产</strong>："
          "换镜头、换传感器、重新装车、甚至一次碰撞都会让它失效。"),
        CODE("""# intrinsics.yaml —— 每一项都不是装饰
camera_id:      front_wide
calib_date:     2026-09-05
image_size:     [1920, 1080]      # ← K 与尺寸绑定（模块 01 第 7 节）
K:              [[1200.0, 0, 960.0], [0, 1200.0, 540.0], [0, 0, 1]]
dist_model:     brown_conrady
dist:           [-0.28, 0.09, 0.0012, -0.0008, -0.012]   # k1 k2 p1 p2 k3
acceptance:
  reproj_median_px:   0.21
  reproj_p95_px:      0.63
  reproj_p95_outer_px: 0.94      # ← 外圈单独报
  distortion_margin:  2.03
  zhang_rank:         5
  delta_v_coverage_px: 512
  sigma_pitch_deg:    0.034
sha:            4a1c88e2          # ← 供 LUT / 下游校验（模块 01 第 5 节）""", "yaml"),
        OL([
            "<strong>没有 <code>acceptance</code> 段的标定文件不允许上车</strong>——"
            "它是唯一能事后判断「这次标定行不行」的依据",
            "<strong>$K$ 与 <code>image_size</code> 必须同时出现</strong>，"
            "缺一个就无法判断它对应哪一级预处理",
            "<strong>畸变系数的顺序要写清</strong>"
            "（OpenCV 是 $k_1k_2p_1p_2k_3$，与公式书写顺序不同，"
            "<em>这是一个真实的、静默的错误来源</em>）",
            "<strong>外参单独一个文件</strong>，因为它的更新频率不同"
            "（重新装车要重标外参，不用重标内参——模块 01 第 9 节的不变量②）",
            "<strong>标定文件带 <code>sha</code></strong>，"
            "所有派生产物（去畸变 LUT、BEV 映射表）都记录它，不匹配拒绝加载",
        ]),
        CALLOUT("intuition",
                "<strong>如果只加一项，加 <code>delta_v_coverage_px</code>。</strong>"
                "它计算代价为零（就是角点行号的极差），"
                "<em>而它抓的是第 6 节那个 106 倍的差距</em>——"
                "本模块所有验收项里，只有它能防住一整类"
                "「标定看起来成功、远处系统性偏」的失败。"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 02 · 标定：内参、外参与验收

四件事：

1. **验证 Zhang 的约束计数**：1 视角 rank 2、2 视角 rank 4、**3 视角 rank 5（刚好可解）**；
   而「纯平移」和「只绕光轴转」拍多少张都是 **rank 2**。
2. **把归一化的收益诚实地量一遍** —— 结果与教科书的常见说法不完全一样。
3. **从多视角单应解出 K**（闭式解，相对误差 5e-15）。
4. **可辨识性实验**：σ(pitch) 从 **3.74° 降到 0.035°**，
   靠的不是多拍，而是**扩大图像行覆盖**。"""),

    md("""## 0 · 环境与真值"""),

    code("""import numpy as np

print('numpy', np.__version__)

F, CX, CY = 1200.0, 960.0, 540.0
W, HGT = 1920, 1080
H_CAM = 1.5
K_TRUE = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.]])

def rot(rx, ry, rz):
    '''按 X-Y-Z 顺序的欧拉角（度）构造旋转矩阵。'''
    rx, ry, rz = map(np.deg2rad, (rx, ry, rz))
    Rx = np.array([[1,0,0],[0,np.cos(rx),-np.sin(rx)],[0,np.sin(rx),np.cos(rx)]])
    Ry = np.array([[np.cos(ry),0,np.sin(ry)],[0,1,0],[-np.sin(ry),0,np.cos(ry)]])
    Rz = np.array([[np.cos(rz),-np.sin(rz),0],[np.sin(rz),np.cos(rz),0],[0,0,1]])
    return Rz @ Ry @ Rx

# 棋盘格：9x6 个内角点，格距 30mm，位于板坐标系的 Z=0 平面
NX, NY, PITCH_M = 9, 6, 0.030
gx, gy = np.meshgrid(np.arange(NX) * PITCH_M, np.arange(NY) * PITCH_M)
BOARD = np.stack([gx.ravel(), gy.ravel()], axis=1)      # (54, 2)
print(f'标定板 {NX}x{NY} 内角点，格距 {PITCH_M*1000:.0f}mm，'
      f'板面 {(NX-1)*PITCH_M*1000:.0f}x{(NY-1)*PITCH_M*1000:.0f}mm')"""),

    md("""## 1 · 多视角与单应

板在自己坐标系里是 $Z=0$，所以「板 → 图像」是一个单应 $H=K[r_1\\;r_2\\;t]$。"""),

    code("""def H_of_view(R, t, Kmat=None):
    '''平面板（Z=0）到图像的单应。'''
    Kmat = K_TRUE if Kmat is None else Kmat
    Hm = Kmat @ np.column_stack([R[:, 0], R[:, 1], np.asarray(t, float)])
    return Hm / Hm[2, 2]

def apply_H(Hm, pts):
    ph = np.column_stack([pts, np.ones(len(pts))]) @ Hm.T
    return ph[:, :2] / ph[:, 2:]

VIEWS_GOOD = [
    (rot(  0,   0,   0), [ 0.00,  0.00, 0.50]),
    (rot( 25, -20,  10), [ 0.05,  0.00, 0.55]),
    (rot(-30,  15,  -8), [-0.04,  0.02, 0.60]),
    (rot( 10,  35,  20), [ 0.02, -0.03, 0.52]),
    (rot(-18, -28, -15), [ 0.01,  0.04, 0.58]),
]

# 另外四个视角：把板推到画幅的四个象限（板距 1.0m，这样整块板仍在画幅内）
VIEWS_EDGE = [
    (rot( 18, -24,  -8), [-0.58, -0.335, 1.0]),
    (rot( 16,  25,   8), [ 0.34, -0.335, 1.0]),
    (rot(-20,  22,   8), [ 0.34,  0.185, 1.0]),
    (rot(-17, -21,  -8), [-0.58,  0.185, 1.0]),
]
VIEWS_FULL = VIEWS_GOOD + VIEWS_EDGE

def corners_of(views):
    return np.vstack([apply_H(H_of_view(R, t), BOARD) for R, t in views])

RD = np.hypot(CX, CY)
print(f\"{'配置':22s} {'角点数':>6s} {'画幅内':>7s} {'外 1/3 半径的点数':>18s} {'Δv':>7s}\")
for name, vs in [('VIEWS_GOOD (5)', VIEWS_GOOD), ('VIEWS_FULL (9)', VIEWS_FULL)]:
    uv = corners_of(vs)
    rn = np.linalg.norm(uv - np.array([CX, CY]), axis=1) / RD
    ins = ((uv[:,0] >= 0) & (uv[:,0] < W) & (uv[:,1] >= 0) & (uv[:,1] < HGT))
    print(f'{name:22s} {len(uv):6d} {ins.mean():7.2f} {int((rn>=2/3).sum()):18d} '
          f'{np.ptp(uv[:,1]):7.0f}')
    assert ins.all(), f'{name}: 所有角点都应在画幅内'

UV_ALL_GOOD = corners_of(VIEWS_GOOD)
UV_ALL_FULL = corners_of(VIEWS_FULL)
n_outer_good = int((np.linalg.norm(UV_ALL_GOOD - [CX,CY], axis=1) / RD >= 2/3).sum())
n_outer_full = int((np.linalg.norm(UV_ALL_FULL - [CX,CY], axis=1) / RD >= 2/3).sum())
assert n_outer_good <= 2, '五视角配置几乎没有边缘角点'
assert n_outer_full > 30, '加了四象限视角后边缘才被覆盖'
print(f'\\n✅ 两个配置的 rank 都会是 5、Δv 都够，'
      f'但边缘角点数是 **{n_outer_good} vs {n_outer_full}**')
print('   → **「朝向够」与「覆盖到边缘」是两件不同的事**'
      '（模块 01 第 4 节的陷阱就在这里）')"""),

    md("""## 2 · Zhang 的约束计数与退化配置

$\\omega=K^{-\\top}K^{-1}$ 对称齐次 → **5 个自由度**；每视角给 **2 个**线性约束。
所以至少要 3 个视角 —— 但**「视角」指的是朝向不同，不是位置不同**。"""),

    code("""def v_ij(h, i, j):
    '''Zhang 论文里的 v_ij 行向量（作用在 omega 的 6 个分量上）。'''
    return np.array([h[0,i]*h[0,j],
                     h[0,i]*h[1,j] + h[1,i]*h[0,j],
                     h[1,i]*h[1,j],
                     h[2,i]*h[0,j] + h[0,i]*h[2,j],
                     h[2,i]*h[1,j] + h[1,i]*h[2,j],
                     h[2,i]*h[2,j]])

def constraint_matrix(views):
    rows = []
    for R, t in views:
        h = H_of_view(R, t)
        rows.append(v_ij(h, 0, 1))                      # r1 · r2 = 0
        rows.append(v_ij(h, 0, 0) - v_ij(h, 1, 1))      # |r1| = |r2|
    return np.array(rows)

CONFIGS = {
    '1 视角':                VIEWS_GOOD[:1],
    '2 视角（不同朝向）':     VIEWS_GOOD[:2],
    '3 视角（不同朝向）':     VIEWS_GOOD[:3],
    '5 视角（不同朝向）':     VIEWS_GOOD,
    '退化：5 张纯平移':       [(rot(0,0,0), [0.02*i, 0.01*i, 0.50+0.05*i]) for i in range(5)],
    '退化：5 张只绕光轴转':   [(rot(0,0,15*i), [0,0,0.50]) for i in range(5)],
    '5 张只绕一个轴倾斜':     [(rot(8*i,0,0), [0,0,0.50]) for i in range(5)],
}
ranks = {}
print(f\"{'采集配置':24s} {'A 的形状':>10s} {'rank':>5s}  结论\")
for name, vs in CONFIGS.items():
    A = constraint_matrix(vs)
    r = int(np.linalg.matrix_rank(A, tol=1e-8))
    ranks[name] = r
    print(f'{name:24s} {str(A.shape):>10s} {r:5d}  '
          f\"{'可解' if r >= 5 else '**欠定**'}\")

assert ranks['1 视角'] == 2 and ranks['2 视角（不同朝向）'] == 4
assert ranks['3 视角（不同朝向）'] == 5, '三个不同朝向刚好够'
assert ranks['5 视角（不同朝向）'] == 5, 'rank 在 5 就饱和'
assert ranks['退化：5 张纯平移'] == 2, '纯平移拍 5 张 == 拍 1 张'
assert ranks['退化：5 张只绕光轴转'] == 2
assert ranks['5 张只绕一个轴倾斜'] == 5, '只倾斜一个轴就够'
print('\\n✅ rank 在 3 个不同朝向时到 5 并饱和；'
      '而两种退化配置**拍 5 张仍然只有 rank 2**')
print('   → **多拍不能替代换朝向**，而 rank 检查只要一次 SVD')"""),

    md("""## 3 · DLT 与归一化：一个诚实的测量

常见说法是「归一化换来几个数量级的精度」。**下面把它量一遍。**"""),

    code("""def normalize_pts(p):
    '''平移到质心、缩放到平均距离 sqrt(2)。返回 (归一化点, 变换矩阵 T)。'''
    c = p.mean(0)
    d = np.sqrt(((p - c) ** 2).sum(1)).mean()
    s = np.sqrt(2) / d
    T = np.array([[s, 0, -s*c[0]], [0, s, -s*c[1]], [0, 0, 1.]])
    ph = np.column_stack([p, np.ones(len(p))]) @ T.T
    return ph[:, :2], T

def dlt_homography(src, dst, normalize=True, dtype=np.float64):
    '''最小二乘解单应。返回 (H, cond(A))。'''
    if normalize:
        s_n, Ts = normalize_pts(src); d_n, Td = normalize_pts(dst)
    else:
        s_n, d_n, Ts, Td = src, dst, np.eye(3), np.eye(3)
    A = []
    for (x, y), (u, v) in zip(s_n, d_n):
        A.append([-x, -y, -1,  0,  0,  0, u*x, u*y, u])
        A.append([ 0,  0,  0, -x, -y, -1, v*x, v*y, v])
    A = np.array(A, dtype=dtype)
    cond = float(np.linalg.cond(A.astype(np.float64)))
    _, _, Vt = np.linalg.svd(A)
    Hn = np.array(Vt[-1].reshape(3, 3), dtype=np.float64)
    Hm = np.linalg.inv(Td) @ Hn @ Ts
    return Hm / Hm[2, 2], cond

R0, t0 = VIEWS_GOOD[1]
H_TRUE = H_of_view(R0, t0)
UV_TRUE = apply_H(H_TRUE, BOARD)
rng = np.random.default_rng(7)

print(f\"{'噪声(px)':>9s} {'归一化':>7s} {'cond(A)':>11s} {'H 相对误差':>12s}\")
res = {}
for noise in [0.0, 0.2, 1.0]:
    for nz in [False, True]:
        errs, conds = [], []
        for _ in range(30):
            uv = UV_TRUE + (0 if noise == 0 else rng.normal(0, noise, UV_TRUE.shape))
            Hm, c = dlt_homography(BOARD, uv, normalize=nz)
            conds.append(c)
            errs.append(np.linalg.norm(Hm - H_TRUE) / np.linalg.norm(H_TRUE))
        res[(noise, nz)] = (np.mean(conds), np.mean(errs))
        print(f'{noise:9.1f} {str(nz):>7s} {np.mean(conds):11.3e} {np.mean(errs):12.3e}')

# 无噪声：归一化的数值收益是真实且巨大的
gain = res[(0.0, False)][1] / res[(0.0, True)][1]
print(f'\\n无噪声时归一化带来的精度提升 = **{gain:.0f} 倍**')
assert gain > 10, f'无噪声时归一化应有显著收益，实测 {gain:.1f}'

# 有噪声：收益被噪声淹没
for noise in [0.2, 1.0]:
    e_no, e_yes = res[(noise, False)][1], res[(noise, True)][1]
    print(f'噪声 {noise} px: 未归一化 {e_no:.2e} vs 归一化 {e_yes:.2e}'
          f'  → 差别 {abs(e_no-e_yes)/max(e_no,e_yes)*100:.0f}%')
    assert abs(e_no - e_yes) / max(e_no, e_yes) < 0.5, \\
        '有噪声时两者应当在同一量级'

# 条件数的改善始终是 4-5 个数量级
for noise in [0.2, 1.0]:
    assert res[(noise, False)][0] / res[(noise, True)][0] > 1e3
print('\\n✅ 归一化改善的是**数值条件**（4–5 个数量级），'
      '而真实标定的精度由角点噪声支配')
print('   → 它是好习惯（零成本），但**不是精度手段**')"""),

    md("""## 3b · 更糟的点分布，以及 float32

如果归一化的收益真的是精度，那它应该在点聚集、近共线、低精度浮点下显现出来。
**实测：都没有。**"""),

    code("""def rel_err(src, uv_true, noise, nz, dtype, trials=30, seed=11):
    r = np.random.default_rng(seed)
    es = []
    for _ in range(trials):
        uv = uv_true + (0 if noise == 0 else r.normal(0, noise, uv_true.shape))
        Hm, _ = dlt_homography(src, uv, normalize=nz, dtype=dtype)
        es.append(np.linalg.norm(Hm - H_TRUE) / np.linalg.norm(H_TRUE))
    return float(np.mean(es))

# 三种点分布：把板坐标压扁/聚集，单应真值不变
SPREADS = {
    '铺满整板':        BOARD,
    '聚集在一角(1/12)': BOARD * (1/12) + 0.01,
    '近共线(窄带)':     np.column_stack([BOARD[:, 0], BOARD[:, 1] * 0.02]),
}
print(f\"{'点分布':20s} {'dtype':>9s} {'未归一化':>12s} {'归一化':>12s} {'谁更好':>8s}\")
for name, src in SPREADS.items():
    uvt = apply_H(H_TRUE, src)
    for dt, dn in [(np.float64, 'float64'), (np.float32, 'float32')]:
        e_no  = rel_err(src, uvt, 0.2, False, dt)
        e_yes = rel_err(src, uvt, 0.2, True,  dt)
        who = '归一化' if e_yes < e_no else '未归一化'
        print(f'{name:20s} {dn:>9s} {e_no:12.3e} {e_yes:12.3e} {who:>8s}')

print('\\n✅ 三种点分布 × 两种精度，归一化都没有可测的精度收益'
      '（0.2 px 噪声引入的 ~1e-3 误差把一切数值差异都盖住了）')"""),

    md("""## 4 · 从多视角单应解出 K（Zhang 的闭式解）"""),

    code("""def solve_K_from_homographies(views):
    '''由多视角的单应解 omega，再闭式反解 K。'''
    A = constraint_matrix(views)
    _, _, Vt = np.linalg.svd(A)
    b = Vt[-1]
    B = np.array([[b[0], b[1], b[3]],
                  [b[1], b[2], b[4]],
                  [b[3], b[4], b[5]]])
    v0  = (B[0,1]*B[0,2] - B[0,0]*B[1,2]) / (B[0,0]*B[1,1] - B[0,1]**2)
    lam = B[2,2] - (B[0,2]**2 + v0*(B[0,1]*B[0,2] - B[0,0]*B[1,2])) / B[0,0]
    al  = np.sqrt(lam / B[0,0])
    be  = np.sqrt(lam * B[0,0] / (B[0,0]*B[1,1] - B[0,1]**2))
    ga  = -B[0,1] * al**2 * be / lam
    u0  = ga * v0 / be - B[0,2] * al**2 / lam
    return np.array([[al, ga, u0], [0, be, v0], [0, 0, 1.]])

K_est = solve_K_from_homographies(VIEWS_GOOD)
print('恢复的 K：')
print(np.round(K_est, 6))
print(f'\\n  f_x 相对误差 {abs(K_est[0,0]-F)/F:.3e}')
print(f'  f_y 相对误差 {abs(K_est[1,1]-F)/F:.3e}')
print(f'  c_x 相对误差 {abs(K_est[0,2]-CX)/CX:.3e}')
print(f'  c_y 相对误差 {abs(K_est[1,2]-CY)/CY:.3e}')
print(f'  skew = {K_est[0,1]:.3e}（真值 0）')

worst = max(abs(K_est[0,0]-F)/F, abs(K_est[1,1]-F)/F,
            abs(K_est[0,2]-CX)/CX, abs(K_est[1,2]-CY)/CY)
assert worst < 1e-12, f'无噪声时应精确恢复，实测 {worst:.2e}'
assert abs(K_est[0,1]) < 1e-6, 'skew 应为 0'
print(f'\\n✅ 无噪声时闭式解精确恢复内参（最大相对误差 {worst:.1e}）')

# 三视角同样够
K3 = solve_K_from_homographies(VIEWS_GOOD[:3])
assert abs(K3[0,0]-F)/F < 1e-10
print('✅ 只用 3 个视角同样精确 —— 与第 2 节的 rank 计数一致')"""),

    md("""## 5 · 重投影误差：分位数与分层

**只报均值会把离群点和边缘问题都平均掉。**"""),

    code("""def reproj_errors(Hm, src, uv_obs):
    return np.linalg.norm(apply_H(Hm, src) - uv_obs, axis=1)

rng = np.random.default_rng(5)
uv_obs = UV_TRUE + rng.normal(0, 0.25, UV_TRUE.shape)
# 注入 3 个离群点（角点检测失手）
bad_idx = rng.choice(len(uv_obs), 3, replace=False)
uv_obs[bad_idx] += rng.normal(0, 6.0, (3, 2))

H_fit, _ = dlt_homography(BOARD, uv_obs)
e = reproj_errors(H_fit, BOARD, uv_obs)

print(f'  角点数        {len(e)}')
print(f'  均值          {e.mean():.3f} px')
print(f'  中位数        {np.median(e):.3f} px')
print(f'  P95           {np.percentile(e,95):.3f} px')
print(f'  最大值        {e.max():.3f} px')
print(f'  P95/中位数    {np.percentile(e,95)/np.median(e):.1f}x')

assert np.percentile(e,95) / np.median(e) > 2.0, '离群点应当把 P95 顶起来'
assert e.mean() < np.percentile(e,95), '均值被大多数好点拉低'
print('\\n✅ 3 个离群点让 P95 是中位数的数倍，而均值几乎没动'
      ' → **门禁必须用 P95**')

# 按半径分层 —— 用**所有视角的并集**，因为覆盖是整批采集的性质
print(f\"\\n{'配置':>16s} {'图像半径分档':>12s} {'点数':>6s}\")
for cfg_name, uv_all in [('VIEWS_GOOD (5)', UV_ALL_GOOD), ('VIEWS_FULL (9)', UV_ALL_FULL)]:
    rn = np.linalg.norm(uv_all - np.array([CX, CY]), axis=1) / RD
    for lo, hi, nm in [(0.0, 1/3, '内 1/3'), (1/3, 2/3, '中 1/3'), (2/3, 9.9, '外 1/3')]:
        cnt = int(((rn >= lo) & (rn < hi)).sum())
        print(f'{cfg_name:>16s} {nm:>12s} {cnt:6d}')
    print()

rn_g = np.linalg.norm(UV_ALL_GOOD - [CX, CY], axis=1) / RD
rn_f = np.linalg.norm(UV_ALL_FULL - [CX, CY], axis=1) / RD
assert (rn_g >= 2/3).sum() <= 2, 'VIEWS_GOOD 在外圈几乎没有点'
assert (rn_f >= 2/3).sum() > 30, 'VIEWS_FULL 才真正覆盖了外圈'
print('✅ 分层报告暴露了一件 rank 检查看不到的事：'
      'VIEWS_GOOD 的外圈只有 1 个角点')
print('   → 用它标出来的畸变模型在画幅角上是**外推**，'
      '而模块 01 量过那里的位移是 197.71 px')"""),

    md("""## 6 · 可辨识性：想标好远处，必须采近处

$\\partial v/\\partial c_y = 1$，而
$\\partial v/\\partial\\text{pitch} = f\\sec^2\\theta \\approx f\\bigl(1+((v-c_y)/f)^2\\bigr)$。
**第二列只在 $v$ 跨度大时才与第一列分开。**"""),

    code("""def jac_cy_pitch(vs):
    '''(c_y, pitch[rad]) 对像素行 v 的雅可比。'''
    vs = np.asarray(vs, float)
    return np.column_stack([np.ones_like(vs), F * (1 + ((vs - CY) / F) ** 2)])

def identifiability(vs, corner_noise_px=0.2):
    J = jac_cy_pitch(vs)
    cov = np.linalg.inv(J.T @ J) * corner_noise_px ** 2
    return {'delta_v': float(np.ptp(vs)),
            'cond': float(np.linalg.cond(J)),
            'sigma_cy_px': float(np.sqrt(cov[0, 0])),
            'sigma_pitch_deg': float(np.rad2deg(np.sqrt(cov[1, 1])))}

COVERAGE = {
    '只用远处地面 (v 570–600)':      np.linspace(570, 600, 20),
    '中等范围 (v 570–720)':          np.linspace(570, 720, 20),
    '全画幅地面 (v 570–1070)':       np.linspace(570, 1070, 20),
    '再加地平线以上 (v 380–1070)':   np.linspace(380, 1070, 30),
}
print(f\"{'采集覆盖':30s} {'Δv':>6s} {'cond':>11s} {'σ(c_y)':>9s} {'σ(pitch)':>10s}\")
ident = {}
for name, vs in COVERAGE.items():
    r = identifiability(vs)
    ident[name] = r
    print(f\"{name:30s} {r['delta_v']:6.0f} {r['cond']:11.3e} \"
          f\"{r['sigma_cy_px']:8.2f}px {r['sigma_pitch_deg']:9.4f}°\")

far  = ident['只用远处地面 (v 570–600)']['sigma_pitch_deg']
full = ident['全画幅地面 (v 570–1070)']['sigma_pitch_deg']
print(f'\\n只采远处 σ(pitch) = {far:.2f}°   全画幅 σ(pitch) = {full:.4f}°'
      f'   → 改善 **{far/full:.0f} 倍**')
assert far > 3.0, '只采远处时 σ(pitch) 应超过 3°'
assert full < 0.05, '全画幅覆盖应把 σ(pitch) 压到 0.05° 以下'
assert far / full > 50, f'改善应超过 50 倍，实测 {far/full:.0f}'

# 收益会饱和
sat = ident['再加地平线以上 (v 380–1070)']['sigma_pitch_deg']
print(f'再扩到 Δv=690: σ(pitch) = {sat:.4f}°  (仅再降 {100*(1-sat/full):.0f}%)')
assert sat / full > 0.8, '继续扩大覆盖的收益应当饱和'

# 与下游需求挂钩：50m 处 2m 误差要求 pitch 多准？
def pitch_err_to_m(deg, d=50.0):
    th = np.arctan2(H_CAM, d)
    th2 = th - np.deg2rad(deg)
    return abs(H_CAM / np.tan(th2) - d) if th2 > 1e-9 else np.inf
for need in [2.0]:
    lo, hi = 1e-4, 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if pitch_err_to_m(mid) < need: lo = mid
        else: hi = mid
    print(f'\\n若要求 50m 处误差 < {need}m，则 pitch 误差必须 < **{lo:.4f}°**')
    print(f'  只采远处 ({far:.2f}°) 差 {far/lo:.0f} 倍；'
          f'全画幅 ({full:.4f}°) {\"够用\" if full < lo else f\"仍差 {full/lo:.1f} 倍\"}')
print('\\n✅ 最方便的采集方式（只对着远处拍）是最差的选择')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| Zhang 的约束计数 | 1/2/3 视角 → rank 2/4/**5**，在 5 饱和 |
| 退化采集 | 纯平移、只绕光轴转 → **拍 5 张仍是 rank 2** |
| 只倾斜一个轴 | rank 5，**够用** |
| 归一化（无噪声） | 精度提升 **数百倍** |
| 归一化（0.2 px 噪声） | **差别消失**，两者都 ~1e-3 |
| 闭式解恢复 K | 无噪声下相对误差 < 1e-12 |
| 离群点 | 3 个点让 P95/中位数 > 2×，均值几乎不动 |
| **可辨识性** | σ(pitch) **3.74° → 0.035°**，靠扩大 Δv 而非多拍 |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：带归一化的 DLT

实现 `homography_dlt(src, dst, normalize=True)`，返回 `(H, cond(A))`，
其中 `H[2,2] == 1`。要求归一化用「质心 + 平均距离 $\\sqrt2$」的标准做法。"""),

    code("""def homography_dlt(src, dst, normalize=True):
    \"\"\"返回 (H, cond(A))；H 归一化到 H[2,2]=1。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
SRC = BOARD
DST = apply_H(H_TRUE, SRC)

for nz in [False, True]:
    Hm, c = homography_dlt(SRC, DST, normalize=nz)
    assert abs(Hm[2, 2] - 1.0) < 1e-12, 'H 应归一化到 H[2,2]=1'
    err = np.linalg.norm(Hm - H_TRUE) / np.linalg.norm(H_TRUE)
    print(f'normalize={str(nz):5s}  cond={c:11.3e}  相对误差={err:.3e}')
    assert err < 1e-8, f'无噪声时应精确，实测 {err:.2e}'

c_no  = homography_dlt(SRC, DST, normalize=False)[1]
c_yes = homography_dlt(SRC, DST, normalize=True)[1]
assert c_no / c_yes > 1e3, f'归一化应把条件数改善 3 个数量级以上（实测 {c_no/c_yes:.1e}）'

# 少于 4 点应当无法确定单应
try:
    homography_dlt(SRC[:3], DST[:3])
    got = True
except Exception:
    got = False
print(f'\\n3 个点时{\"没有报错（解不唯一，但 SVD 仍会给一个）\" if got else \"抛出异常\"}')
print('✅ 练习 1 通过：无噪声下精确，且归一化把条件数改善 3+ 个数量级')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def homography_dlt(src, dst, normalize=True):
    src = np.asarray(src, float); dst = np.asarray(dst, float)
    if normalize:
        s_n, Ts = normalize_pts(src); d_n, Td = normalize_pts(dst)
    else:
        s_n, d_n, Ts, Td = src, dst, np.eye(3), np.eye(3)
    A = []
    for (x, y), (u, v) in zip(s_n, d_n):
        A.append([-x, -y, -1,  0,  0,  0, u*x, u*y, u])
        A.append([ 0,  0,  0, -x, -y, -1, v*x, v*y, v])
    A = np.array(A)
    cond = float(np.linalg.cond(A))
    _, _, Vt = np.linalg.svd(A)
    Hm = np.linalg.inv(Td) @ Vt[-1].reshape(3, 3) @ Ts
    return Hm / Hm[2, 2], cond

Hm, c = homography_dlt(BOARD, apply_H(H_TRUE, BOARD))
assert np.linalg.norm(Hm - H_TRUE) / np.linalg.norm(H_TRUE) < 1e-8
print('✅ 参考答案 2 通过'.replace('2', '1'))"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：采集配置审计

实现 `collection_audit(views)`，在**优化之前**就判断这批图能不能标：

- `'n_views'` —— 视角数
- `'rank'` —— 约束矩阵的 rank
- `'solvable'` —— bool：`rank >= 5`
- `'degenerate_reason'` —— str 或 None：`rank < 5` 时给出原因
  （`'too_few_views'` 若视角数 < 3，否则 `'insufficient_orientation_diversity'`）"""),

    code("""def collection_audit(views):
    \"\"\"返回 dict(n_views, rank, solvable, degenerate_reason)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
CASES = {
    '3 视角（不同朝向）':   VIEWS_GOOD[:3],
    '5 视角（不同朝向）':   VIEWS_GOOD,
    '2 视角':               VIEWS_GOOD[:2],
    '退化：5 张纯平移':     CONFIGS['退化：5 张纯平移'],
    '退化：5 张绕光轴转':   CONFIGS['退化：5 张只绕光轴转'],
}
for name, vs in CASES.items():
    a = collection_audit(vs)
    assert set(a) == {'n_views', 'rank', 'solvable', 'degenerate_reason'}
    print(f\"{name:22s} n={a['n_views']} rank={a['rank']} \"
          f\"solvable={str(a['solvable']):5s} reason={a['degenerate_reason']}\")

assert collection_audit(VIEWS_GOOD[:3])['solvable'] is True
assert collection_audit(VIEWS_GOOD[:3])['degenerate_reason'] is None
a2 = collection_audit(VIEWS_GOOD[:2])
assert a2['solvable'] is False and a2['degenerate_reason'] == 'too_few_views'
for k in ['退化：5 张纯平移', '退化：5 张绕光轴转']:
    a = collection_audit(CASES[k])
    assert a['solvable'] is False
    assert a['degenerate_reason'] == 'insufficient_orientation_diversity', a
    assert a['n_views'] == 5, '视角数够，但朝向多样性不够 —— 两个信号必须分开'
print('\\n✅ 练习 2 通过：「张数够」与「朝向够」是两个独立的判据')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def collection_audit(views):
    n = len(views)
    A = constraint_matrix(views)
    r = int(np.linalg.matrix_rank(A, tol=1e-8))
    ok = r >= 5
    reason = None
    if not ok:
        reason = 'too_few_views' if n < 3 else 'insufficient_orientation_diversity'
    return {'n_views': n, 'rank': r, 'solvable': ok, 'degenerate_reason': reason}

assert collection_audit(VIEWS_GOOD)['solvable']
assert collection_audit(CONFIGS['退化：5 张纯平移'])['degenerate_reason'] \\
       == 'insufficient_orientation_diversity'
print('✅ 参考答案 2 通过')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：可解读的重投影报告

实现 `reproj_report(errs, uv)`，返回 dict：

- `'n'`, `'median'`, `'p95'`, `'max'`
- `'p95_outer'` —— 图像外 1/3 半径区域的 P95（无点时 `float('nan')`）
- `'outlier_ratio'` —— 误差大于 `5 × 中位数` 的点占比

> 为什么是 5 倍而不是 3 倍：误差近似半正态时中位数 $=0.6745\\sigma$，
> 所以 `3×中位数` 只有 $2.02\\sigma$ —— **干净数据上就有 4.3% 的假阳性**
> （实测 4.269%，理论 4.302%）。`5×中位数` 是 $3.37\\sigma$，假阳性 **0.07%**。
- `'coverage_frac'` —— 角点包围盒面积 / 图像面积
- `'n_outer'` —— 落在外 1/3 半径区域的角点数

> `uv` 应当传**所有视角的并集**——覆盖是整批采集的性质，不是单张图的性质。"""),

    code("""def reproj_report(errs, uv, img_w=W, img_h=HGT):
    \"\"\"返回 dict(n, median, p95, max, p95_outer, outlier_ratio, coverage_frac)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# —— 所有 fixture 先建好（放在调用 stub 之前）——
rng2 = np.random.default_rng(5)

UV_ONE  = apply_H(H_of_view(*VIEWS_GOOD[1]), BOARD)          # 单视角 54 点
e_one   = np.abs(rng2.normal(0, 0.25, len(UV_ONE)))
e_one3  = e_one.copy()
e_one3[rng2.choice(len(e_one), 3, replace=False)] += 6.0      # 3/54 = 5.6%

e_good  = np.abs(rng2.normal(0, 0.25, len(UV_ALL_GOOD)))      # 5 视角并集
e_full  = np.abs(rng2.normal(0, 0.25, len(UV_ALL_FULL)))      # 9 视角并集
e_few   = e_full.copy()
e_few[rng2.choice(len(e_full), 6, replace=False)] += 6.0       # 6/486 = 1.2%
e_dirty = e_full.copy()
e_dirty[rng2.choice(len(e_full), 20, replace=False)] += 6.0    # 20/486 = 4.1%

uv_small = (UV_ALL_FULL - [CX, CY]) * 0.25 + [CX, CY]

# —— 第一组：离群点占比 5.6% 时，P95 抓得住 ——
r_one, r_one3 = reproj_report(e_one, UV_ONE), reproj_report(e_one3, UV_ONE)
for r in (r_one, r_one3):
    assert set(r) == {'n', 'median', 'p95', 'max', 'p95_outer',
                      'outlier_ratio', 'coverage_frac', 'n_outer'}
print(f"54 点 + 3 个离群点 (5.6%)：P95 {r_one['p95']:.3f} -> {r_one3['p95']:.3f}，"
      f"均值 {e_one.mean():.3f} -> {e_one3.mean():.3f}")
assert r_one3['p95'] > r_one['p95'] * 2, '占比 5.6% 时 P95 必须被顶起来'

# —— 第二组：占比 1.2% 时 P95 看不见 ——
r_full_r, r_few = reproj_report(e_full, UV_ALL_FULL), reproj_report(e_few, UV_ALL_FULL)
print(f"486 点 + 6 个离群点 (1.2%)：P95 {r_full_r['p95']:.3f} -> {r_few['p95']:.3f}，"
      f"outlier_ratio {r_full_r['outlier_ratio']:.4f} -> {r_few['outlier_ratio']:.4f}")
assert r_few['p95'] < r_full_r['p95'] * 1.2, '占比 1.2% 时 P95 几乎不动'
assert r_few['outlier_ratio'] > 0.005 and r_full_r['outlier_ratio'] < 0.005, \
    'outlier_ratio 才抓得住（干净数据上它应当接近 0）'
print('  -> **P95 的检出能力取决于离群点占比**：低于 5% 时它看不见，'
      '必须同时报 outlier_ratio')

# —— 第三组：覆盖是整批采集的性质 ——
r_g = reproj_report(e_good, UV_ALL_GOOD)
print(f"\\nGOOD(5): coverage={r_g['coverage_frac']:.3f} n_outer={r_g['n_outer']}")
print(f"FULL(9): coverage={r_full_r['coverage_frac']:.3f} n_outer={r_full_r['n_outer']}")
assert r_full_r['coverage_frac'] > r_g['coverage_frac'] * 2
assert r_g['n_outer'] <= 2 and r_full_r['n_outer'] > 30
print(f"GOOD(5) 的 p95_outer = {r_g['p95_outer']}"
      f"  (外圈只有 {r_g['n_outer']} 个点 -> 统计量无意义)")
assert r_full_r['p95_outer'] == r_full_r['p95_outer'], 'FULL 才有真实的外圈 P95'

# —— 第四组：覆盖率抓「板拍太远」——
assert reproj_report(e_full, uv_small)['coverage_frac'] < r_full_r['coverage_frac'] / 10
print('\\n✅ 练习 3 通过：P95 与 outlier_ratio 分工检出离群点、'
      'n_outer 抓边缘覆盖、coverage_frac 抓「板拍太远」')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def reproj_report(errs, uv, img_w=W, img_h=HGT):
    e = np.asarray(errs, float); uv = np.asarray(uv, float)
    med = float(np.median(e))
    r_norm = np.linalg.norm(uv - np.array([img_w/2, img_h/2]), axis=1) \\
             / np.hypot(img_w/2, img_h/2)
    outer = e[r_norm >= 2/3]
    bbox = (np.ptp(uv[:, 0]) * np.ptp(uv[:, 1])) / (img_w * img_h)   # numpy 2 移除了 ndarray.ptp()
    return {'n': int(len(e)),
            'median': med,
            'p95': float(np.percentile(e, 95)),
            'max': float(e.max()),
            'p95_outer': float(np.percentile(outer, 95)) if len(outer) else float('nan'),
            'outlier_ratio': float((e > 5 * med).mean()),   # 5 倍：假阳性 0.07%
            'coverage_frac': float(min(bbox, 1.0)),
            'n_outer': int(len(outer))}

r = reproj_report(e_one3, UV_ONE)
assert r['p95'] > r['median'] * 2
assert reproj_report(e_good, UV_ALL_GOOD)['n_outer'] <= 2
print('✅ 参考答案 3 通过')
print('   coverage_frac 用包围盒（抓「板太远」与「板只在画面一角」）；'
      'n_outer 单独一项，因为覆盖率高不代表覆盖到了**边缘**。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：标定验收器

把本模块所有判据装进一个函数。实现
`calib_acceptance(views, errs, uv, v_rows)`，返回
`(是否通过, {检查项: (通过?, 实测值)})`，包含：

| 检查项 | 阈值 |
|---|---|
| `zhang_rank` | `== 5` |
| `reproj_p95` | `< 0.8` px |
| `reproj_p95_outer` | `< 1.2` px |
| `outlier_ratio` | `< 0.02` |
| `coverage_frac` | `>= 0.15` |
| `n_outer` | `>= 20` |
| `delta_v` | `>= 400` px |
| `sigma_pitch_deg` | `< 0.05` |

**只有全部通过才返回 True。**

> 自测里会出现一个值得注意的结果：**`VIEWS_GOOD`（5 视角）通不过**——
> 它的 rank、Δv、重投影误差全都合格，栽在 `n_outer` 上。"""),

    code("""def calib_acceptance(views, errs, uv, v_rows):
    \"\"\"返回 (bool, {检查项: (通过?, 实测值)})。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
V_WIDE = np.linspace(570, 1070, 40)     # 全画幅地面覆盖
V_FAR  = np.linspace(570, 600,  40)     # 只采远处

def show(tag, res):
    ok, det = res
    print(f'{tag}  ->  ' + ('通过' if ok else '**不通过**'))
    for k, (passed, val) in det.items():
        v = f'{val:.4f}' if isinstance(val, float) else str(val)
        print(f"   {'OK  ' if passed else 'FAIL'} {k:20s} = {v}")
    print()

r_full_acc = calib_acceptance(VIEWS_FULL, e_full, UV_ALL_FULL, V_WIDE)
show('VIEWS_FULL (9 视角) + 全画幅 Δv', r_full_acc)
assert r_full_acc[0] is True, r_full_acc[1]

# ★ 本模块最有意思的一条：五视角配置栽在边缘覆盖上
r_good_acc = calib_acceptance(VIEWS_GOOD, e_good, UV_ALL_GOOD, V_WIDE)
show('VIEWS_GOOD (5 视角) + 全画幅 Δv', r_good_acc)
assert r_good_acc[0] is False, '五视角配置不该通过'
assert r_good_acc[1]['zhang_rank'][0] is True, 'rank 是合格的'
assert r_good_acc[1]['delta_v'][0] is True, 'Δv 是合格的'
assert r_good_acc[1]['reproj_p95'][0] is True, '重投影误差是合格的'
assert r_good_acc[1]['n_outer'][0] is False, '**它只栽在 n_outer 上**'

# 退化采集
bad1 = calib_acceptance(CONFIGS['退化：5 张纯平移'], e_good, UV_ALL_GOOD, V_WIDE)
assert bad1[0] is False and bad1[1]['zhang_rank'][0] is False

# 离群点
bad2 = calib_acceptance(VIEWS_FULL, e_dirty, UV_ALL_FULL, V_WIDE)
assert bad2[0] is False
assert (bad2[1]['outlier_ratio'][0] is False) or (bad2[1]['reproj_p95'][0] is False)

# 只采远处：Δv 与 σ(pitch) 同时报警
bad3 = calib_acceptance(VIEWS_FULL, e_full, UV_ALL_FULL, V_FAR)
assert bad3[0] is False
assert bad3[1]['delta_v'][0] is False and bad3[1]['sigma_pitch_deg'][0] is False, \
    '只采远处应当同时触发 Δv 与 σ(pitch) 两项'
print(f"只采远处时 σ(pitch) = {bad3[1]['sigma_pitch_deg'][1]:.2f}°"
      '  → **两项同时报警，因为它们量的是同一件事**')
print()
print('✅ 练习 4 通过。而最值得记的是第二组：'
      '**本课自己的 5 视角配置通不过验收**——')
print('   rank / Δv / 重投影误差全合格，栽在「一个角点都没采到边缘」上。')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def calib_acceptance(views, errs, uv, v_rows):
    a = collection_audit(views)
    r = reproj_report(errs, uv)
    idt = identifiability(v_rows)
    checks = {
        'zhang_rank':       (a['rank'] == 5,                a['rank']),
        'reproj_p95':       (r['p95'] < 0.8,                r['p95']),
        'reproj_p95_outer': (not (r['p95_outer'] >= 1.2),   r['p95_outer']),
        'outlier_ratio':    (r['outlier_ratio'] < 0.02,     r['outlier_ratio']),
        'coverage_frac':    (r['coverage_frac'] >= 0.15,    r['coverage_frac']),
        'n_outer':          (r['n_outer'] >= 20,            r['n_outer']),
        'delta_v':          (idt['delta_v'] >= 400,         idt['delta_v']),
        'sigma_pitch_deg':  (idt['sigma_pitch_deg'] < 0.05, idt['sigma_pitch_deg']),
    }
    return all(p for p, _ in checks.values()), checks

assert calib_acceptance(VIEWS_FULL, e_full, UV_ALL_FULL,
                        np.linspace(570, 1070, 40))[0] is True
assert calib_acceptance(VIEWS_GOOD, e_good, UV_ALL_GOOD,
                        np.linspace(570, 1070, 40))[0] is False
print('✅ 参考答案 4 通过')
print('   两个实现细节：')
print('   ① p95_outer 用 `not (x >= 1.2)` 而不是 `x < 1.2` —— '
      '外圈无点时它是 nan，而 `nan < 1.2` 是 False，会把「没采到边缘」误判成 FAIL；')
print('   ② 真正抓「没采到边缘」的是 n_outer，'
      '它是**计数**而不是误差，所以不会被 nan 干扰。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) OpenCV 的标定入口 ──
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, (w, h), None, None,
    flags=cv2.CALIB_ZERO_TANGENT_DIST |      # 先不标 p1,p2（模块 01 第 3 节）
          cv2.CALIB_FIX_K3)                  # k3 只在广角上需要
#   ⚠️ ret 是**均值** RMS —— 它就是第 5 节说的「只报均值」。
#      要自己算 P95：
per_pt = [np.linalg.norm(cv2.projectPoints(o, r, t, K, dist)[0].reshape(-1,2) - i,
                         axis=1) for o, i, r, t in zip(objpoints, imgpoints, rvecs, tvecs)]
e = np.concatenate(per_pt)
report = dict(median=np.median(e), p95=np.percentile(e, 95), max=e.max())

# ── 2) 采集现场就能跑的两条检查（练习 2 与第 6 节）──
#    都不需要跑优化，拍完立刻算：
audit = collection_audit(homographies)          # rank 够不够
assert audit['solvable'], audit['degenerate_reason']
assert np.ptp(all_corner_rows) >= 400, '角点的图像行跨度不足，pitch 标不准'

# ── 3) 外参：写进 ROS 的 TF 静态变换，而不是散落在代码里 ──
# extrinsics.yaml
#   parent_frame: base_link      # REP-105
#   child_frame:  camera_front
#   translation:  [1.70, 0.00, 1.50]     # ← Z=0 指哪个平面必须在文档里写明
#   rotation_rpy: [0.0, 0.0342, 0.0]     # 弧度
#   load_state:   empty                  # ← 第 5b 节：载荷状态影响 H，值 7.4%
#   sigma_pitch_deg: 0.034               # ← 由练习 4 反解，供下游算 sigma_m
```

> **落地顺序建议**：先加采集现场的两条检查（零成本、抓一整类失败），
> 再把重投影误差从「均值」改成「中位数/P95/外圈 P95」三个数，
> 最后才是把 σ(pitch) 接到下游的 `sigma_m` 上。"""),
]
