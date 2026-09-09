# -*- coding: utf-8 -*-
"""C72 模块 05 · 时空对齐与跨镜关联。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的投影链、模块 03 的 Sampson 距离、模块 04 的 BEV"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_spatiotemporal.ipynb'
                       '（时间戳 × 车速的误差表 / '
                       '<strong>rolling shutter 对小目标可忽略（50 m 处牌高只变 0.005 px）</strong> / '
                       '线性插值的 $aT^2/8$ 上界 / '
                       '<strong>运动补偿：关联门被自车运动支配而不是被测量噪声支配</strong> / '
                       '跨镜关联的几何门）'),
    ("核心参考", "本课程 C55 模块 04（单相机时序融合：ByteTrack / 卡尔曼 / "
                 "贝叶斯 log-odds / 迟滞双阈值）· C60 模块 05（延迟剖析）· "
                 "ROS REP-105（坐标系与时间约定）· "
                 "Ait-Aider et al., <em>Simultaneous Object Pose and Velocity "
                 "Computation … Rolling Shutter</em>（ECCV 2006）"),
    ("预计时长", "读 40 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("time-is-a-coordinate", "时间是第五个坐标", "".join([
        P("模块 00 那条链走完之后，得到的是「某个时刻、某个坐标系里的一个米数」。"
          "<strong>而多路相机、IMU、上一帧——它们的「某个时刻」都不一样。</strong>"),
        ASCII("""
   一个目标的米数，实际上带四个标签

        (X, Y, Z)  @  frame=base_link  @  t=1757320000.033  @  exposure=8ms
         └ 米数         └ 空间坐标系          └ 时间戳             └ 有效时长

   四个标签里，工程上最常被丢掉的是**第三个**。
   而丢掉它的代价：

        误差(米) = |时间戳错位| × 车速

        120 km/h × 33 ms = **1.10 m**
        └── 比模块 03 里双目在 50 m 处的 σ（2.9 m）小，但比 IPM 的 σ（0.68 m）大
        """),
        DUAL(
            "<strong>这一层的特点是：它的误差与距离无关。</strong>"
            "<em>模块 01–04 的误差都随距离放大（$1/\\text{px}$、$Z^2$、$H/(H-z)$），"
            "而时间误差是纯运动学的——它在 10 m 和 80 m 处一样大</em>。"
            "<strong>所以它在近处反而是主导项</strong>："
            "10 m 处 IPM 的 σ 只有 0.03 m，"
            "而 33 ms 的时间戳错位值 1.10 m。",
            "<strong>本模块的结论会有点反直觉：时间层的误差预算高度集中在一项上。</strong>"
            "<em>rolling shutter 对小目标可以忽略（第 3 节）、"
            "线性插值已经足够精确（第 4 节）</em>——"
            "<strong>钱全部花在「时间戳到底对不对」上。</strong>"
            "而这恰好是一个工程问题而不是算法问题："
            "<em>它取决于硬件同步、驱动的时间戳语义、以及有没有人验证过它。</em>",
        ),
    ])),

    # ============================================================== 2
    ("timestamp", "时间戳错位 × 车速 = 米", "".join([
        TABLE(["车速", "5 ms", "10 ms", "16 ms", "33 ms", "50 ms", "100 ms"], [
            ["30 km/h", "0.042", "0.083", "0.133", "0.275", "0.417", "0.833"],
            ["60 km/h", "0.083", "0.167", "0.267", "0.550", "0.833", "1.667"],
            ["90 km/h", "0.125", "0.250", "0.400", "0.825", "1.250", "2.500"],
            ["<strong>120 km/h</strong>", "0.167", "0.333", "0.533",
             "<strong>1.100</strong>", "1.667", "<strong>3.333</strong>"],
        ]),
        P("单位是米。<strong>33 ms 是 30 fps 的一帧，100 ms 是一个常见的端到端延迟预算。</strong>"),
        H3("时间戳的四种常见错位，以及它们的量级"),
        TABLE(["错位来源", "典型量级", "@120 km/h", "怎么发现"], [
            ["<strong>用「收到帧的时刻」当曝光时刻</strong>",
             "10–50 ms（传输 + 解码）", "0.33–1.67 m",
             "<strong>与硬触发信号比</strong>；<em>没有硬触发时几乎无法发现</em>"],
            ["<strong>曝光中点 vs 曝光开始</strong>", "曝光时长的一半，1–10 ms",
             "0.03–0.33 m", "读驱动文档；<em>不同厂商约定不同</em>"],
            ["<strong>多路相机不同步</strong>", "无硬同步时可达一帧（33 ms）",
             "<strong>1.10 m</strong>",
             "<strong>模块 04 第 6 节的重叠区一致性</strong>（但它会把这误判成外参误差）"],
            ["<strong>时钟漂移</strong>（相机时钟 vs 主机时钟）",
             "无 PTP 时每分钟数毫秒", "累积", "长时间记录里看时间戳差的趋势"],
        ]),
        CALLOUT("danger",
                "第三行那个括号很重要：<strong>时间不同步会伪装成外参误差。</strong>"
                "<em>两路相机在不同时刻拍同一个地面点，"
                "自车已经动了，于是两路读出的距离不一致</em>——"
                "而模块 04 的一致性监控会把它归到「外参漂移」。"
                "<strong>区分方法：不同步造成的不一致与车速成正比，"
                "而外参误差与车速无关。</strong>"
                "<em>所以监控要按车速分档看——这是练习 3 的内容。</em>"),
    ])),

    # ============================================================== 3
    ("rolling-shutter", "rolling shutter：对小目标可以忽略", "".join([
        P("CMOS 逐行曝光，整幅读出通常 10–30 ms。"
          "<strong>所以同一帧里，不同行对应的是不同时刻。</strong>"
          "直觉上这该是个大问题——而算一下会发现要分两种情形。"),
        P("取整幅读出 20 ms、车速 120 km/h（33.3 m/s）："),
        TABLE(["目标跨多少行", "行间时差", "对应的世界位移"], [
            ["12 行（80 m 处的 0.8 m 牌）", "0.22 ms", "<strong>0.007 m</strong>"],
            ["20 行", "0.37 ms", "0.012 m"],
            ["50 行", "0.93 ms", "0.031 m"],
            ["100 行", "1.85 ms", "0.062 m"],
            ["<strong>1080 行（整幅）</strong>", "<strong>20.00 ms</strong>",
             "<strong>0.667 m</strong>"],
        ]),
        DUAL(
            "<strong>结论分两半。</strong>"
            "① <strong>对单个小目标，rolling shutter 可以忽略</strong>："
            "80 m 处的标志只跨 12 行，牌高的畸变是 "
            "<em>0.005 px</em>（notebook 第 3 节量出的），"
            "<strong>比任何检测器的定位精度都小两个数量级</strong>。"
            "<em>所以「给标志建 rolling shutter 模型」是不值得的工程投入。</em>",
            "② <strong>而对「同一帧里的不同目标」，它不可忽略</strong>："
            "画幅顶部（远处）与底部（近处）差了整个读出时长，"
            "<strong>@120 km/h 就是 0.667 m。</strong>"
            "<em>于是同一帧里，近处目标的时间戳比远处目标晚 20 ms</em>。"
            "<strong>正确的处理是：给每个目标一个「按其像素行插值出来的时间戳」，"
            "而不是给整帧一个时间戳。</strong>"
            "<em>这只需要一行代码，而它把 0.667 m 的误差降到第 3 节表里对应的行数那一档。</em>",
        ),
        CALLOUT("intuition",
                "<strong>rolling shutter 真正会咬人的是快速旋转与横向高速运动</strong>"
                "（<em>螺旋桨、快速转向、以及相机自身的振动</em>）。"
                "而 TSR 的场景是<strong>纵向匀速</strong>为主，"
                "所以本课的结论是「按行给时间戳，不建畸变模型」。"
                "<em>换到无人机或手持场景时，这个结论需要重测。</em>"),
    ])),

    # ============================================================== 3b
    ("exposure", "曝光时长：一个观测是一段区间，而它的距离依赖是反的", "".join([
        P("时间戳标的是一个<strong>时刻</strong>，而曝光是一段<strong>区间</strong>。"
          "区间内自车在动，所以像素上留下拖影。"
          "<strong>把它换算成像素，会发现一件和本课其它误差都相反的事。</strong>"),
        P("车速 120 km/h，地面点的行位移："),
        TABLE(["曝光时长", "曝光期间的世界位移", "10 m 处", "20 m 处", "50 m 处",
               "80 m 处"], [
            ["2 ms", "0.067 m", "1.21 px", "0.30 px", "0.05 px", "0.02 px"],
            ["<strong>8 ms</strong>", "0.267 m", "<strong>4.93 px</strong>",
             "1.22 px", "<strong>0.19 px</strong>", "0.08 px"],
            ["20 ms（夜间/隧道）", "0.667 m", "<strong>12.86 px</strong>",
             "3.10 px", "0.49 px", "0.19 px"],
        ]),
        DUAL(
            "<strong>近处显著、远处可忽略——这个方向和本课其它所有误差都相反。</strong>"
            "<em>标定误差、测距误差、地面假设误差全都随距离放大；"
            "而曝光拖影随距离<strong>缩小</strong></em>，"
            "因为远处目标的像素位置对距离变化不敏感"
            "（$\\partial v/\\partial d = -f(H-z)/d^2$）。"
            "<strong>所以它是这一层唯一「近处才需要担心」的项。</strong>",
            "<strong>两个可操作的推论。</strong>"
            "① <strong>夜间/隧道里曝光变长，近处的定位精度会掉</strong>——"
            "<em>而这在白天的评测集上完全看不出来</em>。"
            "所以评测集必须按曝光时长分层"
            "（<strong>曝光时长是一个应当被记录进每帧元数据的字段</strong>）。"
            "② <strong>时间戳应当标在曝光中点</strong>，"
            "<em>因为那是拖影的重心；标在开始或结束都会引入半个曝光时长的系统偏差</em>"
            "（8 ms 曝光下是 4 ms，@120 km/h 值 0.13 m）。"
            "<strong>而第 2 节说过：三种约定差 1–50 ms，没写清就等于没有。</strong>",
        ),
        CALLOUT("intuition",
                "<strong>一条便宜的自查</strong>："
                "在数据里找同一块标志在近处（&lt;15 m）的连续几帧，"
                "<em>比较它的像素高度的帧间抖动</em>。"
                "<strong>如果夜间的抖动明显大于白天，那就是曝光拖影</strong>——"
                "<em>而它不是检测器的问题，调模型修不了。</em>"),
    ])),

    # ============================================================== 4
    ("interpolation", "线性插值就够了：$aT^2/8$", "".join([
        P("把不同时刻的观测对齐到共同时刻，需要在时间上插值自车位姿。"
          "<strong>该用线性还是更高阶？</strong>"
          "线性插值对二阶项的最大误差有闭式上界："),
        MATH(r"\varepsilon_{\max} = \frac{a\,T^2}{8}"),
        TABLE(["采样间隔 $T$", "$a=1$ m/s²", "$a=3$ m/s²", "$a=8$ m/s²（紧急制动）"], [
            ["10 ms", "0.013 mm", "0.037 mm", "0.100 mm"],
            ["<strong>20 ms</strong>", "0.050 mm", "<strong>0.150 mm</strong>",
             "0.400 mm"],
            ["50 ms", "0.313 mm", "0.938 mm", "2.500 mm"],
            ["100 ms", "1.250 mm", "3.750 mm", "10.000 mm"],
        ]),
        DUAL(
            "<strong>全表都在毫米级。</strong>"
            "<em>而这一层其它误差源是米级（时间戳错位）到分米级（rolling shutter 整幅）</em>——"
            "<strong>相差三到四个数量级。</strong>"
            "所以答案很干脆：<strong>线性插值，不需要更高阶。</strong>"
            "<em>把工程投入放在「让时间戳正确」上，而不是「让插值更精细」上。</em>",
            "<strong>但有两个前提必须成立，否则上面的表不适用。</strong>"
            "① <strong>要插值的是位姿而不是像素</strong>——"
            "<em>在图像上插值目标位置会引入透视非线性，那不是 $aT^2/8$ 能界定的</em>；"
            "② <strong>不能外推</strong>。"
            "<em>$aT^2/8$ 是插值（在两个采样点之间）的界；"
            "外推 $\\Delta t$ 的误差是 $a\\Delta t^2/2$——同样时长下大 4 倍，"
            "而且它随外推距离二次增长、没有上界</em>。"),
        H3("那么该外推，还是该等下一个采样？"),
        P("<strong>这个取舍可以算，而算出来的答案是压倒性的。</strong>"
          "等待一个采样周期的代价不是精度，是<em>延迟</em>——"
          "而延迟同样换算成米：等 $T$ 的时间，自车前进 $vT$。"),
        TABLE(["IMU 频率", "一个周期", "等待的延迟代价（120 km/h）",
               "外推同样时长的位姿误差（$a=3$）", "比值"], [
            ["50 Hz", "20.0 ms", "0.667 m", "0.000600 m", "<strong>1111×</strong>"],
            ["<strong>100 Hz</strong>", "10.0 ms", "<strong>0.333 m</strong>",
             "<strong>0.000150 m</strong>", "<strong>2222×</strong>"],
            ["200 Hz", "5.0 ms", "0.167 m", "0.000037 m", "4444×"],
        ]),
        DUAL(
            "<strong>外推的误差比等待的代价小三个数量级——所以应该外推。</strong>"
            "<em>这与「插值比外推准」的直觉不矛盾：外推确实更不准，"
            "但它不准的那个量（亚毫米）与它省下的那个量（分米）差 2000 倍</em>。"
            "<strong>本课的结论是：在这一层，为了精度而增加延迟几乎总是错的取舍。</strong>",
            "<strong>而这条结论有一个边界：它假设 $a$ 是有界的。</strong>"
            "<em>紧急制动（8 m/s²）下 20 ms 外推的误差是 1.6 mm，仍然可忽略；"
            "但碰撞、失控、路面剧烈起伏时加速度可以高一个量级以上</em>。"
            "<strong>所以正确的实现是外推 + 把 $a\\Delta t^2/2$ 加进 σ</strong>——"
            "<em>这样在剧烈机动时不确定度会自动放大，而下游按 σ 加权时会自动降低对它的信任</em>。"
            "<strong>这与模块 03 的四元组是同一个设计：不确定度必须随条件变化，"
            "而不是一个常数。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("motion-compensation", "运动补偿：关联门被自车运动支配", "".join([
        P("跟踪要把上一帧的目标和这一帧的目标关联起来。"
          "<strong>而对一个静止的交通标志，帧间的「距离变化」全部来自自车运动。</strong>"),
        TABLE(["车速", "10 fps", "20 fps", "30 fps"], [
            ["60 km/h", "1.667 m", "0.833 m", "0.556 m"],
            ["<strong>120 km/h</strong>", "<strong>3.333 m</strong>", "1.667 m",
             "1.111 m"],
        ]),
        P("单位是米，即<strong>帧间自车前进的距离</strong>。"),
        DUAL(
            "<strong>把它和模块 03 的测量不确定度放在一起，结论就出来了。</strong>"
            "<em>50 m 处，IPM 的 σ 是 0.68 m、已知尺寸 1.30 m、双目 2.93 m；"
            "而 120 km/h @10 fps 的帧间位移是 3.33 m</em>。"
            "<strong>所以不做运动补偿时，关联门必须开到 5 m 以上——"
            "而那时它是被自车运动支配的，不是被测量噪声支配的。</strong>"
            "<em>门开得越大，误关联越多（尤其是连续多块标志的路段）。</em>",
            "<strong>运动补偿把这一项几乎完全消掉。</strong>"
            "做法是：用自车位姿把上一帧的目标搬到当前时刻的车体坐标系里，"
            "<em>再和当前帧的观测比</em>。"
            "<strong>补偿之后，关联门只需要覆盖测量噪声</strong>——"
            "按上面的数，从 5 m 降到 1–3 m（<em>取决于用哪种补法</em>）。"
            "<strong>而这条推理链给出了一个可计算的门宽</strong>："
            "$\\text{gate} = k\\sqrt{\\sigma_1^2+\\sigma_2^2}$，"
            "<em>其中 σ 就是模块 03 练习 4 返回的那个值</em>。"
            "<strong>所以「四元组」在这里第二次派上用场</strong>——"
            "第一次是融合加权（模块 04 第 5 节），这次是关联门宽。",
        ),
        CALLOUT("warn",
                "<strong>运动补偿的误差来源是自车位姿，而它自己也有时间戳。</strong>"
                "<em>用错了时刻的位姿去补偿，等于把第 2 节的时间戳错位又引入一次</em>——"
                "而这次它藏在跟踪器内部，更难发现。"
                "<strong>所以补偿函数应当强制要求「位姿的时间戳」与「观测的时间戳」一起传，"
                "并断言两者的差在容许范围内。</strong>"),
    ])),

    # ============================================================== 6
    ("cross-camera", "跨镜关联：用几何而不是外观", "".join([
        P("同一块标志同时出现在两路相机里，要判断它们是不是同一个目标。"
          "<strong>这一层能给的是几何证据，而它比外观相似度更硬。</strong>"),
        TABLE(["门", "怎么算", "适用", "代价"], [
            ["<strong>BEV 距离门</strong>",
             "两路各自测距、投到车体坐标，比欧氏距离",
             "<strong>首选</strong>：物理量、可解释、门宽由 σ 决定",
             "需要两路都能测距（模块 03 的四种补法之一）"],
            ["<strong>Sampson 距离门</strong>（模块 03 练习 1）",
             "用两路的相对外参算 $F$，判对极残差",
             "<strong>不需要测距</strong>，只要外参",
             "<em>只能否决、不能确认</em>——极线上所有点都通过"],
            ["外观相似度", "特征向量的余弦",
             "几何门通过后的二次确认",
             "<strong>跨视角外观差异大</strong>，且它不是几何证据"],
        ]),
        DUAL(
            "<strong>Sampson 门那一行的「只能否决」值得强调。</strong>"
            "<em>对极约束把候选从「整幅图」缩小到「一条线」，"
            "而线上还有无穷多个点</em>。"
            "<strong>所以它是一个必要条件检查器，不是匹配器</strong>——"
            "这与模块 03 第 2 节说的「对极几何的工程价值是否决匹配」是同一条。",
            "<strong>而 BEV 距离门的门宽有一个正确的算法。</strong>"
            "<em>两路的 σ 不一样（一路可能走 IPM、另一路走已知尺寸），"
            "所以门宽应当是 $k\\sqrt{\\sigma_1^2+\\sigma_2^2}$ 而不是一个常数</em>。"
            "<strong>取 $k=3$ 时，50 m 处 IPM(0.68) 与已知尺寸(1.30) 配对的门宽是 4.4 m</strong>；"
            "<em>而如果两路都走双目（2.93），门宽要开到 12.4 m</em>。"
            "<strong>这个差别说明：提高测距精度的收益会传导到关联正确率上</strong>——"
            "<em>而这条链在只看「跟踪指标」时是看不见的。</em>",
        ),
    ])),

    # ============================================================== 7
    ("boundary-c55", "与 C55 模块 04 的分界", "".join([
        P("C55 模块 04 是一整个模块的时序融合，本课模块 05 不重复它。"
          "<strong>分界线是「一路还是多路」。</strong>"),
        TABLE(["问题", "在哪门课", "内容"], [
            ["同一路相机的时间轴上怎么融合", "<strong>C55 模块 04</strong>",
             "ByteTrack 两阶段关联 · 卡尔曼滤波 · 贝叶斯 log-odds 累积 · "
             "迟滞双阈值 · 生命周期状态机 · 「越稳越晚」的取舍"],
            ["多路之间怎么对齐到同一时刻", "<strong>本课模块 05</strong>",
             "时间戳语义 · rolling shutter · 位姿插值 · 运动补偿 · 跨镜关联的几何门"],
            ["时间戳本身对不对", "<strong>本课模块 05 第 2 节</strong>",
             "<em>C55 假设它是对的；本课量它错了值多少米</em>"],
            ["延迟怎么剖析与优化", "<strong>C60 模块 05</strong>",
             "端到端延迟分解、各段耗时"],
        ]),
        CALLOUT("paper",
                "<strong>两门课的交界点是「时间戳」这一个字段。</strong>"
                "<em>C55-04 的卡尔曼滤波需要一个正确的 $\\Delta t$，"
                "而本课第 2 节说明这个 $\\Delta t$ 的常见错位值 0.3–1.7 m</em>。"
                "<strong>所以先修本课第 2 节，再谈 C55-04 的滤波调参</strong>——"
                "<em>否则你会在一个错误的时间轴上调一个正确的滤波器。</em>"),
    ])),

    # ============================================================== 6b
    ("output-validity", "端到端延迟：结果对哪个时刻有效", "".join([
        P("前面几节都在对齐<strong>输入</strong>的时间。"
          "<strong>还有一个对称的问题：输出对哪个时刻有效？</strong>"
          "感知从曝光到被规控读到，中间有一整条流水线。"),
        TABLE(["端到端延迟", "@60 km/h 自车已前进", "@120 km/h 自车已前进"], [
            ["30 ms", "0.500 m", "1.000 m"],
            ["60 ms", "1.000 m", "2.000 m"],
            ["<strong>100 ms</strong>", "1.667 m", "<strong>3.333 m</strong>"],
            ["150 ms", "2.500 m", "5.000 m"],
        ]),
        P("<strong>这是一个<em>系统偏差</em>，不是噪声</strong>——"
          "所有目标都被一致地报得比实际更远（因为自车已经靠近了）。"),
        DUAL(
            "<strong>修法是把结果预测到「被使用的时刻」，而它几乎免费。</strong>"
            "<em>按第 4 节的算法，线性预测 100 ms 的残差是 "
            "$a\\Delta t^2/2 = 15.0$ mm（$a{=}3$）</em>——"
            "<strong>而不预测的系统偏差是 3.333 m，相差 222 倍</strong>。"
            "<em>150 ms 时残差 33.8 mm vs 偏差 5.000 m，仍然是 148 倍。</em>",
            "<strong>而这条推理和第 4 节的「外推 vs 等待」是同一条，"
            "只是用在了链路的另一端。</strong>"
            "<em>前者说「不要为了等一个更准的位姿而增加延迟」，"
            "后者说「已经产生的延迟要靠预测补掉」</em>。"
            "<strong>两者合起来是一条统一的原则："
            "在这一层，延迟是一种系统偏差，而预测的残差是二阶小量——"
            "所以永远选预测。</strong>"
            "<em>代价同样是必须把 $a\\Delta t^2/2$ 加进 σ，"
            "这样剧烈机动时下游会自动降低对它的信任。</em>",
        ),
        CALLOUT("warn",
                "<strong>要预测，就必须知道延迟是多少——而这个数常常没人测过。</strong>"
                "<em>它不是「模型推理耗时」，而是「曝光中点到规控读到」的全链路</em>："
                "曝光 + 读出 + 传输 + 预处理 + 推理 + 后处理 + 序列化 + 传输 + 排队。"
                "<strong>C60 模块 05 讲的就是怎么把它分解出来</strong>，"
                "<em>而本节说明为什么值得去测：每 30 ms 值 1 米。</em>"),
    ])),

    # ============================================================== 8
    ("budget", "时间层的误差预算：钱花在哪", "".join([
        P("把本模块量出来的四项放在同一张表上（120 km/h、20 ms 读出、30 fps）："),
        TABLE(["误差源", "量级", "与距离的关系", "修它的成本"], [
            ["<strong>时间戳错位（一帧）</strong>", "<strong>1.10 m</strong>",
             "<strong>无关</strong>", "<strong>硬同步 / 验证驱动语义——工程，不是算法</strong>"],
            ["整帧一个时间戳（rolling shutter）", "0.667 m", "无关",
             "<strong>一行代码</strong>：按像素行插值时间戳"],
            ["不做运动补偿（关联门被迫开大）", "1.111 m（@30 fps）", "无关",
             "中等：需要自车位姿"],
            ["单目标内的 rolling shutter 畸变", "<strong>0.007 m</strong>", "无关",
             "<em>不值得修</em>"],
            ["<strong>曝光拖影（8 ms）</strong>", "4.93 px @10 m / 0.19 px @50 m",
             "<strong>反的（近处才大）</strong>",
             "低：时间戳标曝光中点 + 记录曝光时长并分层评测"],
            ["位姿线性插值", "<strong>0.00015 m</strong>", "无关",
             "<em>不值得修</em>"],
            ["外推 10 ms（而不是等待）", "0.00015 m vs 等待的 0.333 m",
             "无关", "<em>应当外推，并把 $a\\Delta t^2/2$ 加进 σ</em>"],
            ["<strong>端到端延迟未补偿（100 ms）</strong>",
             "<strong>3.333 m</strong>（系统偏差）", "无关",
             "<strong>预测到使用时刻，残差 15 mm——改善 222 倍</strong>"],
        ]),
        DUAL(
            "<strong>前三项差不多是同一个量级（0.7–1.1 m），后两项小三到四个数量级。</strong>"
            "<em>所以这一层的优化顺序是确定的</em>："
            "先验证时间戳（最贵也最大）、"
            "再按行给时间戳（最便宜的一米级收益）、"
            "最后做运动补偿。"
            "<strong>而「rolling shutter 建模」与「高阶插值」应当被明确地放弃。</strong>",
            "<strong>把这张表和模块 01–04 的合起来，就是这门课的全部交付物。</strong>"
            "<em>50 m 处的总误差预算大致是</em>："
            "标定 σ(pitch)=0.035° 贡献约 2.4 m（模块 02）、"
            "测距 σ 0.68–2.93 m（模块 03）、"
            "未建模坡度 1% 贡献 25 m（模块 04，<strong>如果不处理</strong>）、"
            "时间 1.1 m（本模块）。"
            "<strong>坡度那一项是压倒性的——"
            "所以模块 04 第 4 节的三种应对里，选一个做，比这一层所有优化加起来都值。</strong>",
        ),
    ])),

    # ============================================================== 9
    ("checklist", "本模块的验收清单", "".join([
        OL([
            "<strong>每个观测带时间戳，而不是每帧带一个</strong>（第 3 节）——"
            "按像素行插值，一行代码换 0.667 m",
            "<strong>时间戳的语义写进文档</strong>："
            "曝光开始 / 曝光中点 / 收到帧。"
            "<em>三者差 1–50 ms，而没写清就等于没有</em>",
            "<strong>多路相机硬同步；没有硬同步就把「一帧」的误差写进 σ</strong>（第 2 节）",
            "<strong>重叠区一致性按车速分档看</strong>（第 2 节的告警）——"
            "<em>与车速成正比的不一致是时间问题，不是外参问题</em>",
            "<strong>位姿该外推就外推</strong>——"
            "等一个采样周期的延迟代价比外推误差大 2222 倍；"
            "<em>但必须把 $a\\Delta t^2/2$ 加进 σ</em>（第 4 节）",
            "<strong>时间戳标在曝光中点，并把曝光时长记进每帧元数据</strong>（第 3b 节）——"
            "<em>否则夜间近处的精度下降在评测里看不见</em>",
            "<strong>运动补偿函数强制传两个时间戳并断言其差</strong>（第 5 节）",
            "<strong>关联门宽用 $k\\sqrt{\\sigma_1^2+\\sigma_2^2}$，不用常数</strong>（第 6 节）",
            "<strong>把端到端延迟测出来，并把结果预测到使用时刻</strong>（第 6b 节）——"
            "<em>每 30 ms 值 1 米，而预测的残差是毫米级</em>",
            "<strong>明确不做：rolling shutter 畸变建模、高阶位姿插值</strong>（第 8 节）——"
            "<em>把「决定不做」也记录下来，否则它会被反复重新提出</em>",
        ]),
        CALLOUT("intuition",
                "<strong>最后一条是本课最想留下的一条工作习惯。</strong>"
                "<em>这门课量出了不少「不值得修」的项——"
                "单目标的 rolling shutter（0.007 m）、高阶插值（0.15 mm）、"
                "归一化的精度收益（模块 02 第 4 节）、"
                "PnP 正交化的精度收益（模块 03 第 6 节）</em>。"
                "<strong>把这些结论连同数字一起写进文档，"
                "比只记录「我们做了什么」有用得多</strong>——"
                "<em>因为「为什么没做」是最容易丢失、也最容易被重新踩的知识。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 05 · 时空对齐与跨镜关联

这个 notebook 的主线是**一张误差预算表**，而它的结论有点反直觉：

1. **时间戳错位是主导项**（120 km/h × 33 ms = **1.10 m**），而且它**与距离无关**。
2. **rolling shutter 对小目标可以忽略**（50 m 处的牌高只变 **0.005 px**），
   但「整帧一个时间戳」不可忽略（**0.667 m**）。
3. **曝光拖影的距离依赖是反的**：10 m 处 4.93 px，50 m 处 0.19 px。
4. **该外推就外推**：等一个 IMU 周期的延迟代价比外推误差大 **2222 倍**。
5. **不做运动补偿时，关联门被自车运动支配**（3.33 m）而不是被测量噪声支配（0.68–2.93 m）。"""),

    md("""## 0 · 环境"""),

    code("""import numpy as np

print('numpy', np.__version__)

H_CAM = 1.5
F, CX, CY = 1200.0, 960.0, 540.0
W, HGT = 1920, 1080
READOUT_S = 0.020          # 整幅读出 20ms
SIGN_M = 0.8

def kmh(v):
    return v / 3.6

def v_row_of(d, z=0.0):
    '''地面/离地 z 的点在距离 d 处成像的像素行。'''
    return CY + F * (H_CAM - z) / d

print(f'整幅读出 {READOUT_S*1000:.0f} ms，画幅 {HGT} 行'
      f' -> 每行 {READOUT_S/HGT*1e6:.1f} µs')"""),

    md("""## 1 · 时间戳错位 × 车速 = 米（主导项）"""),

    code("""DTS = [5, 10, 16, 33, 50, 100]
SPEEDS = [30, 60, 90, 120]
print(f\"{'车速':>9s} \" + ''.join(f'{t}ms'.rjust(9) for t in DTS))
tbl = {}
for s in SPEEDS:
    row = [kmh(s) * t / 1000 for t in DTS]
    tbl[s] = dict(zip(DTS, row))
    print(f'{s:6d}km/h ' + ''.join(f'{x:8.3f}m' for x in row))

# 与距离无关：纯运动学
assert abs(tbl[120][33] - 1.100) < 1e-3, tbl[120][33]
print(f'\\n120 km/h 下一帧（33 ms）的错位 = {tbl[120][33]:.3f} m')

# 和模块 03 的测距 sigma 比一比
sig = {'IPM @50m': 0.68, '已知尺寸 @50m': 1.30, '双目 @50m': 2.93,
       'IPM @10m': abs(H_CAM*F/(v_row_of(10.)+0.5-CY) - 10.)}
print('\\n对照模块 03 的测距不确定度：')
for k, v in sorted(sig.items(), key=lambda kv: kv[1]):
    verdict = '**时间是主导项**' if tbl[120][33] > v else '测距是主导项'
    print(f'  {k:16s} sigma = {v:5.3f} m   vs 时间 1.100 m  -> {verdict}')
assert tbl[120][33] > sig['IPM @10m'], '近处时间误差应当压倒测距误差'
assert tbl[120][33] < sig['双目 @50m'], '而远处双目的测距误差更大'
print('\\n✅ 时间误差与距离无关，所以它在**近处**是主导项')"""),

    md("""## 2 · rolling shutter：分两种情形，结论相反"""),

    code("""print('整幅读出 20 ms、车速 120 km/h：\\n')
print(f\"{'目标跨多少行':>14s} {'行间时差':>10s} {'世界位移':>10s}\")
v120 = kmh(120)
spans = [(F*SIGN_M/80, '80m 处的 0.8m 牌'), (20, ''), (50, ''), (100, ''),
         (HGT, '整幅')]
disp = {}
for rows, tag in spans:
    dt = READOUT_S * rows / HGT
    disp[rows] = v120 * dt
    label = f'{rows:.0f} 行' + (f'（{tag}）' if tag else '')
    print(f'{label:>14s} {dt*1000:9.2f}ms {v120*dt:9.3f}m')

small = disp[F*SIGN_M/80]
full  = disp[HGT]
print(f'\\n小目标（{F*SIGN_M/80:.0f} 行）: {small:.4f} m')
print(f'整幅（{HGT} 行）:  {full:.4f} m   -> 相差 {full/small:.0f} 倍')
assert small < 0.01, '小目标内部的 rolling shutter 应当可忽略'
assert full > 0.5, '而整幅的时间跨度不可忽略'

# 换算成「牌高的像素变化」——这才是它对测距的实际影响
print('\\nrolling shutter 对「按已知尺寸测距」的影响：')
for d in [20., 50., 80.]:
    s_px = F * SIGN_M / d
    dt = READOUT_S * s_px / HGT
    shift = v120 * dt
    s_px2 = F * SIGN_M / (d - shift)
    print(f'  {d:3.0f}m: 牌高 {s_px:5.1f}px, 顶底时差 {dt*1000:5.3f}ms'
          f' -> 牌高变化 {s_px2-s_px:+.4f} px')
    assert abs(s_px2 - s_px) < 0.1, '牌高的畸变应当远小于定位精度'
print('\\n✅ **给标志建 rolling shutter 畸变模型不值得**（0.005 px 量级）')
print('   而「整帧一个时间戳」值 0.667 m -> **按像素行插值时间戳，一行代码**')"""),

    md("""## 3 · 曝光拖影：距离依赖是反的"""),

    code("""print('车速 120 km/h，地面点在曝光期间的行位移：\\n')
print(f\"{'曝光':>7s} {'世界位移':>9s} \" + ''.join(f'{d:.0f}m'.rjust(10) for d in [10,20,50,80]))
smear = {}
for ex_ms in [2, 8, 20]:
    ex = ex_ms / 1000
    dx = v120 * ex
    row = [abs(v_row_of(d) - v_row_of(d - dx)) for d in [10., 20., 50., 80.]]
    smear[ex_ms] = dict(zip([10, 20, 50, 80], row))
    print(f'{ex_ms:5d}ms {dx:8.3f}m ' + ''.join(f'{r:9.2f}px' for r in row))

near, far = smear[8][10], smear[8][50]
print(f'\\n8 ms 曝光：10 m 处 {near:.2f} px vs 50 m 处 {far:.2f} px'
      f'  -> 近处大 {near/far:.0f} 倍')
assert near > far * 10, '拖影应当近处远大于远处'
assert near > 3.0 and far < 0.5

# 与本课其它误差的距离依赖相反
print('\\n各误差源随距离的方向：')
for name, tenm, fiftym in [
        ('曝光拖影 (8ms)', smear[8][10], smear[8][50]),
        ('IPM 测距 sigma', abs(H_CAM*F/(v_row_of(10.)+0.5-CY)-10.),
         abs(H_CAM*F/(v_row_of(50.)+0.5-CY)-50.)),
]:
    d = '**随距离缩小**' if tenm > fiftym else '随距离放大'
    print(f'  {name:18s} 10m={tenm:8.3f}  50m={fiftym:8.3f}  {d}')

# 时间戳该标在曝光中点
half = v120 * 0.008 / 2
print(f'\\n时间戳标在曝光开始/结束而不是中点 -> 系统偏差 '
      f'{0.008/2*1000:.0f} ms = {half:.3f} m @120km/h')
assert abs(half - 0.133) < 0.01
print('✅ 曝光拖影是这一层唯一「近处才需要担心」的项')"""),

    md("""## 4 · 插值的 $aT^2/8$，以及「外推还是等待」"""),

    code("""def interp_err(a, T):
    '''两个采样点之间线性插值的最大误差。'''
    return a * T * T / 8

def extrap_err(a, dt):
    '''外推 dt 的误差。'''
    return a * dt * dt / 2

ACCS = [1.0, 3.0, 8.0]
print(f\"{'采样间隔':>9s} \" + ''.join(f'a={a}'.rjust(13) for a in ACCS))
for T_ms in [10, 20, 50, 100]:
    T = T_ms / 1000
    print(f'{T_ms:8d}ms ' + ''.join(f'{interp_err(a,T)*1000:10.3f}mm' for a in ACCS))

e = interp_err(3.0, 0.020)
print(f'\\n20 ms 采样 + 3 m/s²: 插值误差 {e*1000:.3f} mm'
      f'  -> 比时间戳错位（1100 mm）小 {1100/(e*1000):.0f} 倍')
assert e < 1e-3, '插值误差应当在毫米级'
print('✅ 线性插值就够了，不需要更高阶')

print('\\n—— 外推 vs 等待 ——')
print(f\"{'IMU 频率':>9s} {'一个周期':>9s} {'等待的延迟代价':>14s} \"
      f\"{'外推的位姿误差':>15s} {'比值':>9s}\")
for hz in [50, 100, 200]:
    T = 1 / hz
    wait = v120 * T
    ext = extrap_err(3.0, T)
    print(f'{hz:8d}Hz {T*1000:8.1f}ms {wait:13.3f}m {ext:14.6f}m {wait/ext:8.0f}x')
    assert wait / ext > 500, '等待的代价应当远大于外推的误差'

print('\\n✅ **该外推就外推**：等待的代价大三个数量级')

# 但剧烈机动时要把误差加进 sigma
print('\\n把外推误差加进 sigma（100 Hz、外推 10 ms）：')
for a, tag in [(3.0, '正常行驶'), (8.0, '紧急制动'), (30.0, '碰撞/剧烈起伏')]:
    ee = extrap_err(a, 0.010)
    print(f'  a={a:4.1f} m/s² ({tag}): 外推误差 {ee*1000:7.3f} mm')
assert extrap_err(30.0, 0.010) < 0.005, '即使 30 m/s² 也只有毫米级'
print('  → 即使 30 m/s² 也只有毫米级，但**把它加进 sigma 是免费的正确做法**')"""),

    md("""## 5 · 运动补偿：关联门被自车运动支配"""),

    code("""print(f\"{'车速':>8s} \" + ''.join(f'{f} fps'.rjust(11) for f in [10,20,30]))
frame_disp = {}
for s in [60, 120]:
    row = [kmh(s) / f for f in [10, 20, 30]]
    frame_disp[s] = dict(zip([10, 20, 30], row))
    print(f'{s:5d}km/h ' + ''.join(f'{x:10.3f}m' for x in row))

SIGMA_50 = {'IPM': 0.68, '已知尺寸': 1.30, '双目': 2.93}
print('\\n不做运动补偿时，关联门必须覆盖「自车位移 + 测量噪声」：')
for fps in [10, 30]:
    d_ego = frame_disp[120][fps]
    for name, sg in SIGMA_50.items():
        gate_no = 1.5 * d_ego + 3 * sg
        gate_yes = 3 * np.sqrt(2) * sg
        print(f'  @{fps:2d}fps {name:8s}: 不补偿门宽 {gate_no:5.2f}m'
              f'  补偿后 {gate_yes:5.2f}m  -> 缩小 {gate_no/gate_yes:4.2f}x')

# 关键结论：不补偿时门宽被自车运动支配
d_ego = frame_disp[120][10]
assert d_ego > SIGMA_50['IPM'] * 3, '自车位移应当超过 IPM 的 3 sigma'
print(f'\\n120 km/h @10 fps 帧间位移 {d_ego:.2f} m，'
      f'而 IPM 的 3σ 只有 {3*SIGMA_50["IPM"]:.2f} m')
print('  → **不补偿时门宽被自车运动支配，不是被测量噪声支配**')

def gate_width(sigma1, sigma2, k=3.0):
    '''两个观测的关联门宽。'''
    return k * np.sqrt(sigma1**2 + sigma2**2)

print('\\n补偿之后，门宽由 sigma 决定（k=3）：')
for a in ['IPM', '已知尺寸', '双目']:
    for b in ['IPM', '已知尺寸', '双目']:
        if a <= b:
            print(f'  {a:8s} + {b:8s} -> {gate_width(SIGMA_50[a], SIGMA_50[b]):5.2f} m')
assert gate_width(0.68, 1.30) < gate_width(2.93, 2.93)
print('\\n✅ 门宽应当是 k·sqrt(σ1²+σ2²) 而不是一个常数')
print('   → 提高测距精度的收益会传导到关联正确率上')"""),

    md("""## 6 · 时间不同步会伪装成外参误差

**区分方法：不同步造成的不一致与车速成正比，而外参误差与车速无关。**"""),

    code("""def side_reading_time_offset(d, dt_s, speed_ms):
    '''侧相机的时间戳晚了 dt_s，此时自车已前进，读出的距离偏小。'''
    return d - speed_ms * dt_s

def side_reading_pitch_err(d, pitch_deg):
    '''侧相机 pitch 错了 pitch_deg 时的读数。'''
    v = v_row_of(d)
    th = np.deg2rad(pitch_deg) + np.arctan2(v - CY, F)
    return H_CAM / np.tan(th) if th > 1e-9 else np.inf

print(f\"{'车速':>8s} {'时间不同步 33ms 的相对差':>24s} {'外参错 0.5° 的相对差':>22s}\")
rows = []
for s in [30, 60, 120]:
    d = 50.
    a = abs(side_reading_time_offset(d, 0.033, kmh(s)) - d) / d
    b = abs(side_reading_pitch_err(d, 0.5) - d) / d
    rows.append((s, a, b))
    print(f'{s:5d}km/h {100*a:23.2f}% {100*b:21.2f}%')

# 时间项与车速成正比
a30, a120 = rows[0][1], rows[2][1]
assert abs(a120 / a30 - 4.0) < 1e-6, '时间项应当与车速严格成正比'
# 外参项与车速无关
b30, b120 = rows[0][2], rows[2][2]
assert abs(b120 - b30) < 1e-12, '外参项应当与车速无关'
print(f'\\n时间项：30->120 km/h 放大 {a120/a30:.1f} 倍（严格正比）')
print(f'外参项：30->120 km/h 变化 {abs(b120-b30):.2e}（无关）')
print('\\n✅ **按车速分档看重叠区一致性，就能把两者分开**')
print('   → 模块 04 第 6 节那个监控要加一个车速维度')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| 时间戳错位（一帧 @120 km/h） | **1.100 m**，且**与距离无关** |
| 单目标内的 rolling shutter | 0.007 m / 牌高变 **0.005 px** → 不值得建模 |
| 整帧一个时间戳 | **0.667 m** → 按像素行插值，一行代码 |
| **曝光拖影（8 ms）** | 10 m 处 4.93 px vs 50 m 处 0.19 px → **距离依赖是反的** |
| 时间戳标曝光开始而非中点 | 系统偏差 0.133 m |
| 位姿线性插值（20 ms, 3 m/s²） | **0.150 mm** → 不需要高阶 |
| **外推 vs 等待** | 等待的代价大 **2222 倍** → 该外推 |
| 不做运动补偿 | 帧间位移 3.33 m 压倒测距 3σ（2.04 m） |
| 关联门宽 | $k\\sqrt{\\sigma_1^2+\\sigma_2^2}$，不是常数 |
| **时间不同步 vs 外参误差** | 前者与车速**严格正比**，后者**无关** |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：按像素行插值时间戳

实现 `row_timestamp(t_frame, v_px, readout_s=READOUT_S, anchor='mid')`：
给定帧的时间戳与目标所在的像素行，返回该行实际的曝光时刻。

`anchor` 指 `t_frame` 标的是什么：`'start'`（第一行开始）/ `'mid'`（画幅中间行）/
`'end'`（最后一行）。

> 自测里会顺带撞上一个真实的工程坑：**Unix 时间戳量级下 float64 的分辨率只有
> 0.238 µs**，所以两个绝对时间戳相减必然带 $\\sim10^{-7}$ 的误差。
> 这正是 ROS / PTP 用整数 `(sec, nsec)` 而不是 float 秒的原因。"""),

    code("""def row_timestamp(t_frame, v_px, readout_s=READOUT_S, anchor='mid', n_rows=HGT):
    \"\"\"返回该像素行的曝光时刻。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
T0 = 1757320000.0
for anchor, ref_row in [('start', 0), ('mid', HGT / 2), ('end', HGT - 1)]:
    t_ref = row_timestamp(T0, ref_row, anchor=anchor)
    assert abs(t_ref - T0) < 1e-12, f'{anchor} 处应当正好等于 t_frame'

# 行号越大、时刻越晚，且总跨度等于读出时长
t_first = row_timestamp(T0, 0, anchor='mid')
t_last  = row_timestamp(T0, HGT - 1, anchor='mid')
assert t_last > t_first
span_err = abs((t_last - t_first) - READOUT_S * (HGT - 1) / HGT)
print(f'跨度误差 = {span_err:.2e} s'
      f'（float64 在 {T0:.3e} 处的分辨率 = {np.spacing(T0)*1e6:.3f} µs）')
assert span_err < 1e-6, span_err
# ⚠️ 这里不能用 1e-9 的容差：Unix 时间戳量级(1.76e9)下 float64 的分辨率是
#    0.238 µs，两个这样的数相减必然带 ~1e-7 的误差。
#    **这正是 ROS / PTP 用整数 (sec, nsec) 而不是 float 秒的原因。**

print(f\"{'像素行':>8s} {'距离(地面)':>11s} {'相对帧时间戳':>13s} {'@120km/h 位移':>14s}\")
for v in [560, 600, 720, 900, 1079]:
    d = H_CAM * F / (v - CY)
    dt = row_timestamp(T0, v, anchor='mid') - T0
    print(f'{v:7d} {d:10.2f}m {dt*1000:+12.2f}ms {v120*dt:+13.3f}m')

# 远处（v 小）与近处（v 大）的时间差
dt_far  = row_timestamp(T0, 560, anchor='mid') - T0
dt_near = row_timestamp(T0, 1079, anchor='mid') - T0
gap = (dt_near - dt_far) * v120
print(f'\\n同一帧里，560 行（{H_CAM*F/(560-CY):.0f}m）与 1079 行'
      f'（{H_CAM*F/(1079-CY):.2f}m）的时间差 = {(dt_near-dt_far)*1000:.2f} ms'
      f' -> {gap:.3f} m')
assert gap > 0.3, f'同帧内的时间跨度应当值 0.3 m 以上，实测 {gap:.3f}'
print('✅ 练习 1 通过：一行代码把 0.667 m 的「整帧一个时间戳」误差消掉')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def row_timestamp(t_frame, v_px, readout_s=READOUT_S, anchor='mid', n_rows=HGT):
    per_row = readout_s / n_rows
    ref = {'start': 0.0, 'mid': n_rows / 2, 'end': n_rows - 1}[anchor]
    return t_frame + (float(v_px) - ref) * per_row

assert abs(row_timestamp(0.0, HGT/2, anchor='mid')) < 1e-12
assert abs(row_timestamp(0.0, 0, anchor='start')) < 1e-12
print('✅ 参考答案 1 通过')
print('   ① anchor 必须是显式参数：三种约定差一整个读出时长（20 ms = 0.667 m）；')
print(f'   ② 绝对时间戳只用来「减」，不要用来「比 1e-9」——'
      f'float64 在 1.76e9 处的分辨率是 {np.spacing(1.757e9)*1e6:.3f} µs。')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：位姿插值/外推，并把误差记进 σ

实现 `pose_at(samples, t_query, a_max=3.0)`，`samples` 是按时间排序的
`[(t, x), ...]`（`x` 为自车纵向位置，米），返回 `(x, sigma, mode)`：

- 落在采样区间内 → 线性插值，`sigma = a_max·T²/8`，`mode='interp'`
- 落在最后一个采样之后 → 线性外推，`sigma = a_max·Δt²/2`，`mode='extrap'`
- 落在第一个采样之前 → `mode='before'`，`sigma = inf`（**不要反向外推**）"""),

    code("""def pose_at(samples, t_query, a_max=3.0):
    \"\"\"返回 (位置, sigma, mode)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
HZ = 100
T_S = 1.0 / HZ
V = v120
SAMPLES = [(i * T_S, V * i * T_S) for i in range(11)]   # 匀速，0–100 ms

# ① 采样点上精确
for t, x in SAMPLES:
    got, sg, mode = pose_at(SAMPLES, t)
    assert abs(got - x) < 1e-9, (t, got, x)
    assert mode in ('interp', 'extrap')

# ② 区间内插值：匀速时线性插值无误差，但 sigma 反映的是「可能的加速度」
mid = 0.5 * T_S
got, sg, mode = pose_at(SAMPLES, mid)
assert mode == 'interp'
assert abs(got - V * mid) < 1e-9, '匀速下插值应当精确'
assert abs(sg - 3.0 * T_S**2 / 8) < 1e-15, f'sigma 应为 aT²/8，实测 {sg:.3e}'

# ③ 外推
t_ex = SAMPLES[-1][0] + 0.010
got, sg, mode = pose_at(SAMPLES, t_ex)
assert mode == 'extrap'
assert abs(got - V * t_ex) < 1e-9
assert abs(sg - 3.0 * 0.010**2 / 2) < 1e-15

# ④ 不反向外推
got, sg, mode = pose_at(SAMPLES, -0.005)
assert mode == 'before' and sg == float('inf')

print(f\"{'查询时刻':>11s} {'mode':>8s} {'位置':>10s} {'sigma':>12s}\")
for t in [-0.005, 0.0, 0.005, 0.055, 0.100, 0.110, 0.150]:
    x, sg, mode = pose_at(SAMPLES, t)
    xs = 'None' if x is None else f'{x:.4f}'
    print(f'{t*1000:10.1f}ms {mode:>8s} {xs:>10s} {sg*1000:11.4f}mm'
          if np.isfinite(sg) else
          f'{t*1000:10.1f}ms {mode:>8s} {xs:>10s} {"inf":>11s}')

# ⑤ 外推的 sigma 随 Δt 二次增长，而插值的 sigma 是常数
sg1 = pose_at(SAMPLES, SAMPLES[-1][0] + 0.010)[1]
sg2 = pose_at(SAMPLES, SAMPLES[-1][0] + 0.020)[1]
assert abs(sg2 / sg1 - 4.0) < 1e-9, '外推 sigma 应当二次增长'
sgi1 = pose_at(SAMPLES, 0.003)[1]
sgi2 = pose_at(SAMPLES, 0.007)[1]
assert abs(sgi1 - sgi2) < 1e-15, '插值 sigma 在区间内是常数'
print('\\n✅ 练习 2 通过：外推 sigma 二次增长、插值 sigma 恒定、'
      '而反向外推被显式拒绝')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def pose_at(samples, t_query, a_max=3.0):
    ts = np.array([t for t, _ in samples], float)
    xs = np.array([x for _, x in samples], float)
    T = float(np.median(np.diff(ts))) if len(ts) > 1 else 0.0
    if t_query < ts[0] - 1e-12:
        return None, float('inf'), 'before'
    if t_query <= ts[-1] + 1e-12:
        return float(np.interp(t_query, ts, xs)), a_max * T * T / 8, 'interp'
    dt = t_query - ts[-1]
    vel = (xs[-1] - xs[-2]) / (ts[-1] - ts[-2])
    return float(xs[-1] + vel * dt), a_max * dt * dt / 2, 'extrap'

assert pose_at(SAMPLES, -0.01)[2] == 'before'
assert pose_at(SAMPLES, 0.15)[2] == 'extrap'
print('✅ 参考答案 2 通过')
print('   反向外推被拒绝而不是照做：那说明观测比最早的位姿还早，')
print('   通常意味着时间戳有问题 —— **应当报错而不是给一个数**。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：运动补偿与关联门

实现两个函数：

- `compensate(range_prev, ego_prev, ego_now)` —— 把上一帧对**静止**目标的距离
  搬到当前时刻（自车前进使距离变小）
- `associate(prev, now, k=3.0)` —— `prev`/`now` 是
  `[(range_m, sigma_m), ...]`，做一次贪心最近邻关联，
  门宽 `k·sqrt(σ1²+σ2²)`；返回 `[(i, j)]` 与未匹配的索引"""),

    code("""def compensate(range_prev, ego_prev, ego_now):
    \"\"\"把上一帧的距离搬到当前时刻（静止目标）。\"\"\"
    # TODO
    raise NotImplementedError

def associate(prev, now, k=3.0):
    \"\"\"返回 (matches, unmatched_prev, unmatched_now)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
EGO_PREV, EGO_NOW = 0.0, v120 / 30          # 30 fps，前进 1.111 m
SIGNS = [30.0, 45.0, 46.5, 80.0]            # 45/46.5 是一对近邻，专门用来试门宽

prev_obs = [(d, 1.30) for d in SIGNS]                       # 已知尺寸测距
now_true = [d - (EGO_NOW - EGO_PREV) for d in SIGNS]
now_obs  = [(d, 1.30) for d in now_true]

# ① 补偿本身
for d in SIGNS:
    got = compensate(d, EGO_PREV, EGO_NOW)
    assert abs(got - (d - (EGO_NOW - EGO_PREV))) < 1e-12, (d, got)
print(f'自车前进 {EGO_NOW-EGO_PREV:.3f} m -> 静止目标的距离各减这么多  ✅')

# ② 不补偿时的关联：门宽必须覆盖自车位移
m_no, up_no, un_no = associate(prev_obs, now_obs)
comp = [(compensate(d, EGO_PREV, EGO_NOW), s) for d, s in prev_obs]
m_yes, up_yes, un_yes = associate(comp, now_obs)

print(f'\\n不补偿: 匹配 {len(m_no)}/{len(SIGNS)}，未匹配 prev {len(up_no)}')
print(f'补偿后: 匹配 {len(m_yes)}/{len(SIGNS)}，未匹配 prev {len(up_yes)}')
assert len(m_yes) == len(SIGNS), '补偿后应当全部正确关联'
assert all(i == j for i, j in m_yes), f'补偿后应当一一对应，实得 {m_yes}'

# ③ 门宽的作用：把 sigma 调大会把近邻错配起来
tight = [(d, 0.10) for d in SIGNS]
tight_now = [(d, 0.10) for d in now_true]
m_t, _, _ = associate([(compensate(d, EGO_PREV, EGO_NOW), s) for d, s in tight],
                      tight_now)
assert all(i == j for i, j in m_t)
print(f'\\nsigma=0.10 时门宽 {3*np.sqrt(2)*0.10:.3f} m -> 匹配 {len(m_t)}，全部正确')
wide = [(d, 3.0) for d in SIGNS]
wide_now = [(d, 3.0) for d in now_true]
m_w, _, _ = associate([(compensate(d, EGO_PREV, EGO_NOW), s) for d, s in wide],
                      wide_now)
print(f'sigma=3.00 时门宽 {3*np.sqrt(2)*3.0:.3f} m -> 匹配 {len(m_w)}')
assert 3*np.sqrt(2)*3.0 > 46.5 - 45.0, '宽门会把 45/46.5 这对近邻纳入同一个门'
print('  → **门宽由 sigma 决定，而 sigma 由用哪种补法决定（模块 03）**')
print('\\n✅ 练习 3 通过')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def compensate(range_prev, ego_prev, ego_now):
    return float(range_prev) - (float(ego_now) - float(ego_prev))

def associate(prev, now, k=3.0):
    cand = []
    for i, (d1, s1) in enumerate(prev):
        for j, (d2, s2) in enumerate(now):
            gate = k * np.sqrt(s1**2 + s2**2)
            dist = abs(d1 - d2)
            if dist <= gate:
                cand.append((dist, i, j))
    cand.sort()
    used_i, used_j, matches = set(), set(), []
    for _, i, j in cand:
        if i in used_i or j in used_j:
            continue
        used_i.add(i); used_j.add(j); matches.append((i, j))
    return (matches,
            [i for i in range(len(prev)) if i not in used_i],
            [j for j in range(len(now)) if j not in used_j])

comp = [(compensate(d, 0.0, v120/30), 1.30) for d in SIGNS]
m, _, _ = associate(comp, [(d - v120/30, 1.30) for d in SIGNS])
assert all(i == j for i, j in m)
print('✅ 参考答案 3 通过')
print('   贪心按距离升序取 —— 简单且够用；')
print('   而门宽用 sqrt(σ1²+σ2²) 而不是常数，是这道题唯一的要点。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：时间层的误差预算审计

实现 `time_budget(speed_kmh, cfg)`，`cfg` 是一个 dict：

| 键 | 含义 |
|---|---|
| `ts_error_ms` | 时间戳错位（ms） |
| `per_row_timestamp` | bool，是否按像素行给时间戳 |
| `readout_ms` | 整幅读出时长 |
| `exposure_ms` | 曝光时长 |
| `ts_at_exposure_mid` | bool，时间戳是否标在曝光中点 |
| `motion_compensated` | bool |
| `fps` | 帧率 |

返回 `(总误差的平方和根, {项: 米})`，并把每一项按第 8 节的公式算出来。
**未按行给时间戳时，rolling shutter 那一项按整幅算。**"""),

    code("""def time_budget(speed_kmh, cfg):
    \"\"\"返回 (rss, {项: 米})。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
BAD = {'ts_error_ms': 33, 'per_row_timestamp': False, 'readout_ms': 20,
       'exposure_ms': 8, 'ts_at_exposure_mid': False,
       'motion_compensated': False, 'fps': 30}
GOOD = {'ts_error_ms': 1, 'per_row_timestamp': True, 'readout_ms': 20,
        'exposure_ms': 8, 'ts_at_exposure_mid': True,
        'motion_compensated': True, 'fps': 30}

for tag, cfg in [('未优化', BAD), ('优化后', GOOD)]:
    rss, items = time_budget(120, cfg)
    print(f'{tag}（120 km/h）: 总计 {rss:.3f} m')
    for k, v in sorted(items.items(), key=lambda kv: -kv[1]):
        print(f'   {k:26s} {v:7.3f} m')
    print()

rss_bad, it_bad = time_budget(120, BAD)
rss_good, it_good = time_budget(120, GOOD)
assert rss_bad > rss_good * 5, f'优化应当带来 5 倍以上的改善（{rss_bad:.2f} -> {rss_good:.2f}）'
assert it_bad['timestamp_error'] > 1.0
assert it_bad['rolling_shutter'] > 0.5, '未按行给时间戳时应当按整幅算'
assert it_good['rolling_shutter'] < 0.05, '按行给时间戳后这一项应当很小'
assert it_bad['exposure_anchor'] > 0.1 and it_good['exposure_anchor'] == 0.0
assert it_bad['motion_uncompensated'] > 1.0 and it_good['motion_uncompensated'] == 0.0

# 时间层的误差与距离无关，但与车速成正比
r30 = time_budget(30, BAD)[0]
r120 = time_budget(120, BAD)[0]
assert abs(r120 / r30 - 4.0) < 1e-9, '整个时间预算应当与车速严格成正比'
print(f'30 km/h 总计 {r30:.3f} m  vs 120 km/h {r120:.3f} m'
      f'  -> 严格 {r120/r30:.1f} 倍')
print('\\n✅ 练习 4 通过：**时间层的总预算与车速严格成正比、与距离无关**')
print(f'   而优化的顺序由这张表决定：'
      f'最大项是 {max(it_bad, key=it_bad.get)}')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def time_budget(speed_kmh, cfg):
    v = speed_kmh / 3.6
    items = {}
    # ① 时间戳错位（主导项）
    items['timestamp_error'] = v * cfg['ts_error_ms'] / 1000
    # ② rolling shutter：按行给时间戳后只剩单目标内部的那一点
    if cfg['per_row_timestamp']:
        rows = F * SIGN_M / 80.0          # 80m 处的牌只跨这么多行
    else:
        rows = HGT                        # 整幅
    items['rolling_shutter'] = v * (cfg['readout_ms'] / 1000) * rows / HGT
    # ③ 时间戳没标在曝光中点 -> 半个曝光的系统偏差
    items['exposure_anchor'] = (0.0 if cfg['ts_at_exposure_mid']
                                else v * (cfg['exposure_ms'] / 1000) / 2)
    # ④ 不做运动补偿 -> 帧间位移进入预算
    items['motion_uncompensated'] = (0.0 if cfg['motion_compensated']
                                     else v / cfg['fps'])
    rss = float(np.sqrt(sum(x * x for x in items.values())))
    return rss, items

rb, _ = time_budget(120, BAD)
rg, _ = time_budget(120, GOOD)
assert rb > rg * 5
print(f'未优化 {rb:.3f} m -> 优化后 {rg:.3f} m（{rb/rg:.1f} 倍）')
print('✅ 参考答案 4 通过')
print('   四项都与车速成正比、与距离无关 —— 所以总预算也是。')
print('   注意用平方和根而不是直接相加：这四项的误差方向是独立的。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) 时间戳的语义必须显式（第 2 节：三种约定差 1–50 ms）──
@dataclass(frozen=True)
class Frame:
    img: np.ndarray
    t_exposure_mid: float      # ← 名字里就写清是哪一个时刻
    exposure_s: float          # ← 第 3b 节：夜间分层评测要用
    readout_s: float
    seq: int
#   ⚠️ 不要叫 `timestamp` —— 那个名字在三种约定下都成立，等于没说

# ── 2) 每个检测带自己的时间戳（第 2 节，一行代码换 0.667 m）──
def det_timestamp(frame: Frame, v_px: float) -> float:
    per_row = frame.readout_s / frame.img.shape[0]
    return frame.t_exposure_mid + (v_px - frame.img.shape[0] / 2) * per_row

# ── 3) ROS 里的时间对齐 ──
from message_filters import ApproximateTimeSynchronizer, Subscriber
sync = ApproximateTimeSynchronizer([Subscriber('/cam_front', Image),
                                    Subscriber('/cam_side', Image)],
                                   queue_size=10, slop=0.005)   # ← slop 要算出来
#   slop 的上限由第 2 节的表反解：容许 0.1 m @120km/h -> slop <= 3 ms
#   ⚠️ ApproximateTimeSynchronizer 只是**丢掉**对不上的帧，它不修时间

# ── 4) 位姿查询：外推而不是等待，但把误差记进 sigma（第 4 节）──
x, sigma_pose, mode = pose_at(imu_buffer, det_timestamp(frame, v_px))
if mode == 'before':
    raise TimestampError('观测早于最早的位姿 —— 时间戳有问题')
total_sigma = math.sqrt(det.sigma_m**2 + sigma_pose**2)

# ── 5) 重叠区一致性要加车速维度（第 6 节）──
metrics.histogram('geom/overlap_rel_diff', rel,
                  tags={'band': band, 'speed_bin': speed_bin})
#   与车速成正比 -> 时间不同步；与车速无关 -> 外参漂移
```

> **落地顺序建议**：先把 `timestamp` 这个字段名改成带语义的名字（几乎零成本，
> 而它会立刻暴露出团队里三种不同的理解），再加按行时间戳，
> 最后给重叠区监控加车速维度。
> <em>而 rolling shutter 建模与高阶插值——本课量过了，明确不做。</em>"""),
]
