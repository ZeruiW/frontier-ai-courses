# -*- coding: utf-8 -*-
"""C57 模块 04 · 切片推理与高分辨率策略。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03（IoU 位移敏感性、FPN 层级分配、NWD）；C53 m05 的端到端延迟拆解会很有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_slicing_inference.ipynb'),
    ("核心参考", "SAHI (Akyon et al., 2022)、Power of Tiling、VisDrone/xView 高分辨率检测实践、量产 ADAS 的两级 ROI 方案"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("why", "切片为什么有效：它不是超分，是「不丢信息」", "".join([
        P("模块 01 已经把账算清楚了：一个 60 米外的 60cm 限速牌，在 1920×1080 / 60° FOV 的前视主摄上只有 <strong>16.6 像素</strong>。而绝大多数检测器的训练输入是 640×640——把 1920 宽的图 letterbox 到 640 宽，缩放比是 1/3，<strong>那个 16.6 px 的标志进入网络时只剩 5.5 px</strong>。"),
        P("5.5 px 意味着什么？在 stride 8 的 P3 特征图上，它占 <strong>0.69 个格子</strong>；在 stride 16 的 P4 上占 0.35 个。<em>没有任何一个特征点的感受野中心落在它身上，标签分配阶段它连一个正样本都拿不到</em>。这不是「模型学得不够好」，这是<strong>信息在预处理阶段就被扔掉了</strong>。"),
        MATH("p_{\\text{input}} \\;=\\; p_{\\text{native}} \\cdot \\frac{L_{\\text{input}}}{L_{\\text{crop}}} \\qquad\\Longrightarrow\\qquad \\text{全图: } 16.6\\cdot\\frac{640}{1920}=5.5\\;\\text{px}, \\quad \\text{切片: } 16.6\\cdot\\frac{640}{640}=16.6\\;\\text{px}"),
        P("<span class=\"term\">Slicing inference</span>（切片推理，代表实现是 <span class=\"term\">SAHI</span>：Slicing Aided Hyper Inference）的全部机理就在这个公式里：<strong>把裁剪窗口 L<sub>crop</sub> 从 1920 缩到 640，目标在网络输入里的线性尺寸就放大 3 倍、面积放大 9 倍</strong>。"),
        DUAL(
            "很多人第一次听会以为切片是某种「超分辨率」——不是。<strong>切片没有创造任何新信息，它只是拒绝丢弃已有信息</strong>。原图里那 16.6×16.6 ≈ 276 个像素一直都在，只是被 <code>resize</code> 抽成了 30 个。切片做的事情是：<em>别 resize，直接把原生像素喂进网络</em>。所以切片的收益上限，就是「原图里本来有多少信息」——原图里就只有 4 px 的目标，切多少片都救不回来。",
            "严谨地说，下采样是一个低通滤波 + 重采样过程。<strong>标志的判别性特征（数字笔画、图案边缘）位于高频段，1/3 下采样会把高于 Nyquist 频率的分量直接混叠掉</strong>，而且混叠是不可逆的。更致命的是第二重损失：检测头的输出是离散网格，<em>目标尺寸小于 stride 时，它在特征图上连一个完整格子都占不满</em>，此时无论用什么标签分配策略（ATSS / SimOTA / TaskAligned），可用的正样本候选都趋于零。切片同时缓解了这两重损失——但它<strong>只对「原生分辨率里信息充足、被 resize 毁掉」的目标有效</strong>，对原生分辨率里就已经模糊的目标无效。",
        ),
        CALLOUT("intuition", "一句话心法：<strong>切片推理的收益 = 你在预处理阶段丢掉的信息量</strong>。所以判断「切片值不值得做」的第一个动作不是跑实验，而是<em>算一算你的目标在网络输入里还剩几个像素</em>。如果全图 resize 后目标还有 40 px，切片几乎没有收益；如果只剩 5 px，切片可能带来两位数的 AP<sub>small</sub> 提升。<strong>面试时被问「怎么提升小目标」，先给出这个判据再给方案，比直接背方法名高一个层次。</strong>"),
        CALLOUT("warn", "切片的第一个代价常被忽略：<strong>它破坏上下文</strong>。交通标志的识别高度依赖周边线索——杆件、龙门架、路侧护栏、它在图像中的垂直位置（模块 05 会推导「标志只出现在地平线附近的窄带里」）。把 1920×1080 切成 640×640 之后，<em>一个只看到 640×640 局部的检测器丢掉了「这块区域在整幅图的哪里」这个强先验</em>。实践中的表现是：<strong>切片提升了远处小标志的召回，同时抬高了近处大目标与广告牌的误检</strong>。这就是为什么真实系统几乎总是「切片结果 + 全图结果」一起融合，而不是只用切片。"),
    ])),
    ("grid", "切片网格：尺寸 s、步长与重叠率 r 的几何", "".join([
        P("切片推理的参数只有两个半：<strong>切片边长 s</strong>、<strong>重叠率 r</strong>，以及一个工程上的第三个——<strong>是否额外跑一遍全图</strong>。先把网格的几何写清楚。"),
        P("给定图像宽 W、切片边长 s、重叠率 r，<strong>步长</strong>（stride，相邻切片原点的间距）为"),
        MATH("\\text{stride} \\;=\\; s\\,(1-r), \\qquad \\text{overlap}_{\\text{px}} \\;=\\; s - \\text{stride} \\;=\\; s\\cdot r"),
        P("切片原点取 <code>0, stride, 2·stride, …</code>，直到再往前会越界；<strong>最后一片贴右边界</strong>（原点取 <code>W-s</code>），保证覆盖完整。这是 SAHI 的标准做法，代价是最后一片与前一片的重叠可能远大于 r。"),
        ASCII("""W = 1920, s = 640, r = 0.10  ->  stride = 576

 0        576      1152    1280                          1920
 |---------|--------|-------|                             |
 [===== slice 0 =====]                    x∈[0,640]
          [===== slice 1 =====]           x∈[576,1216]
                   [===== slice 2 =====]  x∈[1152,1792]
                       [===== slice 3 =====] x∈[1280,1920]  ← 贴边，重叠更大
                                                  ↑
 每相邻两片共享 s·r = 64 px 的重叠带 ────────────────┘

 一个宽 d = 64 px 的目标，落在哪里都至少被某一片**完整**包住？
 -> 见下一节：当且仅当 s·r >= d""")
        ,
        P("竖直方向同理。总切片数是两个方向的乘积。对 1920×1080、s=640 的几种配置："),
        TABLE(["r（重叠率）", "stride", "overlap px", "横向片数", "纵向片数", "总片数 N", "相对全图的像素量"], [
            ["0.00", "640", "0", "3", "2", "<strong>6</strong>", "1.19×"],
            ["0.10", "576", "64", "4", "2", "<strong>8</strong>", "1.58×"],
            ["0.20", "512", "128", "4", "2", "<strong>8</strong>", "1.58×"],
            ["0.30", "448", "192", "4", "2", "<strong>8</strong>", "1.58×"],
            ["0.40", "384", "256", "5", "2", "<strong>10</strong>", "1.98×"],
            ["0.50", "320", "320", "5", "3", "<strong>15</strong>", "2.96×"],
        ]),
        DUAL(
            "表里有个反直觉的现象：<strong>r 从 0.10 涨到 0.30，片数完全没变</strong>。原因是切片数是<em>向上取整</em>出来的——1920 宽在 stride 576 与 stride 448 下都恰好需要 4 片（3 片不够、4 片有余）。<strong>所以在离散化允许的范围内，把 r 从 0.10 调到 0.30 是「免费」的</strong>：一分钱不多花，抗截断能力却翻了三倍。<em>不算这笔账就按默认 0.2 一把梭，等于白扔了一半的鲁棒性。</em>",
            "严谨地说，横向片数为 <code>n = ⌈(W-s)/stride⌉ + 1</code>，它是 r 的阶梯函数而非连续函数。<strong>正确的调参姿势是：先由「最大目标尺寸」定出 r 的下界（下一节），再在<em>不增加片数</em>的前提下把 r 尽量往上推</strong>。数学上就是求满足 <code>⌈(W-s)/(s(1-r))⌉ = n</code> 的最大 r。工程上更简单：写个循环把 r 从下界扫到 0.5，打印片数，选片数跳变前的那个 r。<em>这个「阶梯函数上找免费午餐」的模式在 batch size、padding 对齐、tile 划分里反复出现。</em>",
        ),
        CALLOUT("warn", "切片边长 s 的选择还有一个<strong>硬约束容易被忽略</strong>：s 应当等于（或接近）<em>检测器训练时的输入尺寸</em>。如果模型是在 640×640 上训练的，你切 1024×1024 再 resize 到 640，就等于把放大倍数从 3× 降到 1.875×，白切了；你切 320×320 再 pad 到 640，模型看到的是一张 1/4 面积有内容、3/4 是灰边的图，<strong>与训练分布严重不符</strong>。<em>切片边长 = 训练输入尺寸，是默认起点。</em>"),
    ])),
    ("overlap", "重叠率的下界：一个必须会推的不等式", "".join([
        P("这是本模块<strong>最值得记住、面试也最容易问到的一个推导</strong>。问题：重叠率 r 至少要多大，才能保证「图像里任意位置的、尺寸不超过 d 的目标，一定被某一片<em>完整</em>包含」？"),
        H3("一维推导"),
        P("只看横轴。切片原点为 <code>o<sub>i</sub> = i·stride</code>，第 i 片覆盖 <code>[o<sub>i</sub>, o<sub>i</sub>+s]</code>。一个目标占 <code>[x, x+d]</code>。目标被第 i 片<strong>完整包含</strong>的条件是"),
        MATH("o_i \\le x \\quad\\text{且}\\quad x+d \\le o_i + s \\qquad\\Longleftrightarrow\\qquad x + d - s \\;\\le\\; o_i \\;\\le\\; x"),
        P("也就是说，合法的原点 <code>o<sub>i</sub></code> 必须落在一个<strong>长度为 s − d 的区间</strong> <code>[x+d−s, x]</code> 里。而原点是以 stride 为间隔的等差数列——<em>一个等差数列必然与任意长度为 L 的闭区间相交，当且仅当公差 ≤ L</em>。于是"),
        MATH("\\text{stride} \\;\\le\\; s - d \\qquad\\Longleftrightarrow\\qquad s\\,(1-r) \\le s - d \\qquad\\Longleftrightarrow\\qquad \\boxed{\\;\\underbrace{s\\cdot r}_{\\text{重叠像素}} \\;\\ge\\; d\\;}"),
        P("结论极其干净：<strong>重叠的像素数必须不小于最大目标的像素尺寸</strong>，等价地"),
        MATH("r \\;\\ge\\; \\frac{d_{\\max}}{s}"),
        DUAL(
            "用一句话讲透：<strong>重叠带就是「接住跨界目标的安全网」，网的宽度必须大于目标本身，否则总有一个位置能让目标同时被两片各切走一半、两边都不完整</strong>。<em>下界是紧的</em>——只要 s·r 比 d 小 1 个像素，就存在一批位置（宽度恰好等于 d − s·r）让目标必然被截断。二维情况下横竖都要满足，两个方向独立成立。",
            "严谨地补三个边界条件。<strong>① d &gt; s 时无解</strong>：r ≥ d/s &gt; 1，几何上不可能——目标比切片还大，只能靠全图那一路兜底。<strong>② 这是「完整包含」的下界，不是「能检出」的下界</strong>：多数检测器对被截掉 10–20% 的目标仍能给出一个（偏小的）框，所以实践中 r 略小于下界不会立刻归零，但会系统性地压低边界区域的召回并抬高定位误差。<strong>③ d<sub>max</sub> 指的是「你希望切片这条路负责的最大目标」</strong>，不是图里最大的目标。TSR 里近处 2 米远的标志有 500 px，按它算 r 会大于 1；正确做法是<em>让切片只负责小目标（d ≤ 64 px），大目标交给全图那一路</em>，然后 r ≥ 64/640 = 0.10。",
        ),
        TABLE(["场景", "s", "d<sub>max</sub>（该路负责的最大目标）", "r 下界", "实际取值", "理由"], [
            ["TSR 远距小标志", "640", "64 px（≈ 15 m 外的标志）", "<strong>0.10</strong>", "0.20–0.25", "在不增加片数的区间内取上限，免费换鲁棒性"],
            ["无人机航拍车辆", "512", "80 px", "<strong>0.16</strong>", "0.20", "SAHI 默认值恰好覆盖"],
            ["卫星影像小目标", "1024", "60 px", "<strong>0.06</strong>", "0.10", "目标相对切片极小，重叠可以很省"],
            ["把大目标也交给切片", "640", "500 px", "<strong>0.78</strong>", "—", "<strong>r&gt;0.5 后片数爆炸，这条路应当放弃</strong>"],
        ]),
        CALLOUT("danger", "<p>一个真实会在评测里翻车的错误：<strong>用「平均目标尺寸」而不是「最大目标尺寸」去定 r</strong>。假设标志平均 20 px、最大 64 px，按平均值算 r ≥ 0.031，取 0.05；结果是所有 20 px 左右的标志都没问题，<em>而恰恰是那些近一点、更重要、更该检出的 40–64 px 标志，在切片边界上被系统性截断</em>。更阴险的是：这类漏检<strong>与位置强相关</strong>（只发生在几条固定的竖线附近），随机划分的验证集上被平均掉，看不出来；上路后表现为「某些路段总是漏牌」。<strong>定 r 用的是 d 的上分位数（p99），不是均值。</strong></p>", "别用平均目标尺寸定重叠率"),
    ])),
    ("merge", "跨片合并：坐标还原、NMS 与 NMM", "".join([
        P("切片推理的后处理有三步，每一步都有坑。"),
        H3("① 坐标还原"),
        P("检测器在第 i 片上输出的是<strong>切片局部坐标</strong>，还原到全图只需平移："),
        CODE("""x_global = x_local + slice_x0
y_global = y_local + slice_y0
# 注意：如果切片本身还被 letterbox 到网络输入尺寸，必须先做 letterbox 逆变换，
# 再加切片原点。两次变换的顺序写反 = 框整体偏移（车端最常见的"框错位"根因之一）"""),
        P("<strong>这一步最容易出的错不是公式，而是顺序。</strong>切片 → letterbox → 网络 → 反 letterbox → 加原点，四步必须严格逆序回来。<em>C60 模块 04 会专门讲这个逆变换。</em>"),
        H3("② 同一目标被多片检出"),
        P("重叠带里的目标会被两片（角落上是四片）各检出一次。还原后就是若干个几乎重合的框——<strong>这是标准 NMS 能处理的情形</strong>，因为它们 IoU 很高。"),
        H3("③ 跨边界目标被截断——NMS 处理不了的情形"),
        P("真正的难点在这里。当 r 小于下界，或目标恰好比 d<sub>max</sub> 大时，一个目标会被<strong>两片各看到一部分</strong>，产生两个「半截框」。它们之间的 IoU 很低，NMS 认为它们是两个不同目标，于是<strong>输出两个错框而不是一个对框</strong>。"),
        ASCII("""真值框: [590, 654] (d = 64 px)      切片 0: [0,640]   切片 1: [608,1248]

           590        640    654
            |----------|------|
            [######### 真值 ###]
            [## 片0 只看到 50px #]        -> 碎片 A = [590, 640]
                    [## 片1 只看到 46px ##]  -> 碎片 B = [608, 654]

    IoU(A,B) = 2048 / 4096 = 0.50      <- NMS(thr=0.6) 判定为「两个不同目标」❌
    IoS(A,B) = 2048 / 2944 = 0.70      <- 交集 / **较小框面积**
    union(A,B) = [590, 654]            <- 与真值**完全一致** ✅

  NMS  : 抑制得分低的 -> 剩 1 个**半截**框（定位错）或 2 个框（重复）
  NMM  : 把 IoS 高的**合并成并集** -> 恢复完整框""")
        ,
        P("解法是把 <span class=\"term\">NMS</span>（Non-Maximum Suppression，非极大值抑制）换成/补上 <span class=\"term\">NMM</span>（Non-Maximum Merging，非极大值合并），并且<strong>把判据从 IoU 换成 IoS</strong>（Intersection over Smaller area，交集除以较小框的面积）："),
        MATH("\\mathrm{IoU}(A,B)=\\frac{|A\\cap B|}{|A\\cup B|}, \\qquad \\mathrm{IoS}(A,B)=\\frac{|A\\cap B|}{\\min(|A|,|B|)}"),
        DUAL(
            "为什么必须换成 IoS？<strong>因为「一个碎片是另一个框的一部分」这件事，IoU 天生看不见</strong>。一个 30 px 的碎片完全落在一个 64 px 的框里时，IoU 只有 (30/64)²≈0.22，而 IoS = 1.0。<em>IoU 度量的是「两个框有多像」，IoS 度量的是「小的那个有多大比例被大的包住」</em>——跨片截断场景要问的恰恰是后者。",
            "NMM 的完整算法：按分数降序取种子框，把与它 IoS ≥ τ 的所有框<em>并入</em>（取包围盒的并集、分数取最大值、类别取分数最高者），标记为已消费，继续下一个种子。<strong>与 NMS 的唯一区别是「抑制」变成了「吸收」。</strong>实践中的标准配方是<em>两级</em>：先在<strong>同类别</strong>内做 IoS-NMM 把碎片缝合，再做一次常规 IoU-NMS 去掉真正的重复。SAHI 的默认参数是 NMM IoS 阈值 0.5 与 NMS IoU 阈值 0.5。<strong>另一个必须做的工程细节是「贴边标记」</strong>：记录每个框是否触到所在切片的边界（距边 ≤ 2 px），只对<em>贴边的框</em>启用 NMM——否则两个真实靠得很近的标志（比如上下叠放的限速牌+辅助牌）会被错误地并成一个大框。",
        ),
        CALLOUT("warn", "还有一个必须显式处理的类：<strong>贴边但对侧无碎片的框</strong>。目标被切片边界削掉一半、而另一片因为可见比例太低根本没检出，此时你手上只有一个「半截框」。它的<em>分数通常仍然不低</em>（模型看到半个红圈也会给 0.6），但框是错的，尺寸小了一半。<strong>下游如果按框的像素尺寸估距离（TSR 常这么做），半截框会让距离估计翻倍出错。</strong>处理方式有两种：① 直接丢弃贴边且无法配对的框（牺牲召回换定位可靠性）；② 保留但打上 <code>truncated=True</code> 标记，让跟踪与距离估计模块降权。<em>量产系统里几乎都选 ②——因为丢掉的往往正是最远、最需要早发现的那个。</em>"),
        CALLOUT("intuition", "把这一节压成一句可迁移的话：<strong>NMS 的世界观是「重复的检测应该被删掉」，而跨片场景的世界观是「不完整的检测应该被拼起来」</strong>。凡是「同一个物理实体被切成多份分别观测」的场景——切片推理、多相机重叠视场、时序多帧、点云分块——<em>你需要的都是合并算子而不是抑制算子</em>，判据都是「包含关系」而不是「相似关系」。"),
    ])),
    ("cost", "代价账：切片数、像素吞吐与车端的现实", "".join([
        P("讲完收益必须讲代价，否则就是推销而不是工程。切片推理的代价是<strong>把一次前向变成 N 次前向</strong>，而 N 的量级由一个简单的估计给出："),
        MATH("N \\;\\approx\\; \\left\\lceil\\frac{W-s}{s(1-r)}\\right\\rceil\\!+\\!1 \\;\\times\\; \\left\\lceil\\frac{H-s}{s(1-r)}\\right\\rceil\\!+\\!1 \\;\\;\\xrightarrow[\\;W,H\\gg s\\;]{}\\;\\; \\frac{W\\cdot H}{s^{2}(1-r)^{2}}"),
        P("把 N 乘回每片的像素数 s²，得到一个非常有用的<strong>不变量</strong>："),
        MATH("\\text{总像素吞吐} \\;=\\; N\\cdot s^{2} \\;\\approx\\; \\frac{W\\cdot H}{(1-r)^{2}}"),
        DUAL(
            "这个式子说了一件反直觉的事：<strong>在大图渐近意义下，总计算量几乎<em>与切片大小 s 无关</em>，只由重叠率 r 决定</strong>。切成 64 个小片和切成 16 个大片，处理的总像素数是一样的（都是原图像素 × 1/(1−r)²）。<em>s 决定的不是成本，而是放大倍数 W/s</em>。<strong>所以调参的正确顺序是：先按「目标要被放大到多少像素」定 s，再按重叠下界 d/s 定 r，成本自动落定。</strong>",
            "严谨地补两点。<strong>① 这是渐近结论，对 1920×1080 这种「s 与 H 同量级」的情形不成立</strong>——H=1080 而 s=640 时，纵向只能放下 2 片，贴边冗余把实际吞吐推高到渐近值的 1.07–1.3 倍。notebook 里会在 4096×3072 上验证渐近公式（误差 &lt;7%），在 1920×1080 上用精确计数。<strong>② 像素吞吐不等于延迟</strong>：N 次小前向比 1 次大前向多付 N−1 次 kernel launch、内存分配、后处理与 H2D 拷贝的固定开销；在车端 SoC 上这部分固定开销占比可能到 20–40%。<em>所以真实的延迟倍数通常比像素倍数还差。</em>",
        ),
        P("把数字落到 TSR 的真实场景。设检测器在 640×640 上的推理耗时 5.0 ms（Orin 级 SoC、FP16、一个 tiny/small 量级的模型），耗时按像素线性外推："),
        TABLE(["方案", "输入", "前向次数", "像素吞吐", "推理耗时", "相对全图"], [
            ["<strong>全图下采样</strong>", "1920×1080 → 640×384", "1", "0.25 Mpx", "<strong>3.0 ms</strong>", "1.0×"],
            ["全图原生分辨率", "1920×1088（pad）", "1", "2.09 Mpx", "25.5 ms", "8.5×"],
            ["切片 s=640, r=0.0", "6 × 640²", "6", "2.46 Mpx", "30.0 ms", "10×"],
            ["<strong>切片 s=640, r=0.2</strong>", "8 × 640²", "8", "3.28 Mpx", "<strong>40.0 ms</strong>", "<strong>13.3×</strong>"],
            ["切片 s=640, r=0.5", "15 × 640²", "15", "6.14 Mpx", "75.0 ms", "25×"],
            ["切片 s=512, r=0.2", "15 × 512²", "15", "3.93 Mpx", "48.0 ms", "16×"],
        ]),
        P("现在把它放进车端的延迟预算。30 FPS 意味着<strong>整帧 33.3 ms</strong>，而这 33.3 ms 要装下去畸变与 ISP 后处理、多相机（前视 + 侧视 + 后视，通常 7–11 路）、以及并行运行的车道线、障碍物、可行驶区域、红绿灯、TSR 等多个感知头，再留出融合、跟踪、预测、规控的时间。<strong>TSR 这一路在真实排期里能分到的通常是 5–10 ms</strong>。"),
        ASCII("""一帧 33.3 ms 的真实排期（示意，Orin 级平台）
┌────────────────────────────────────────────────────────────┐
│ ISP/去畸变 3ms │ BEV 主干 & 障碍物 12ms │ 车道 4ms │ 灯 3ms │
│                                                            │
│  TSR 预算 ≈ 5–10ms  ←── 切片推理要 40ms                     │
│  ├─ 全图下采样 3.0ms      ✅ 装得下，但 16px 标志检不出      │
│  ├─ 两级级联   5.0ms      ✅ 装得下，召回可用                │
│  └─ SAHI 切片  40.0ms     ❌ 单这一路就吃掉 1.2 帧           │
│                                                            │
│ 融合/跟踪 4ms │ 预测 3ms │ 规控 4ms │ 余量 …                │
└────────────────────────────────────────────────────────────┘""")
        ,
        CALLOUT("danger", "<p><strong>「切片推理在车端量产系统里基本不可用」——这句话你要能说出来，并且能用上面这张表把它论证清楚。</strong>这是面试里区分「读过论文」与「做过工程」的分水岭：SAHI 在 VisDrone / xView 这类<em>离线、单帧、无延迟约束</em>的高分辨率基准上是标准操作，AP<sub>small</sub> 提升可以到两位数；但它的代价结构（4–16× 计算、且随分辨率平方增长）与车端的实时约束<strong>结构性冲突</strong>。<em>只说「SAHI 能提升小目标」而不给代价，会被追问到崩；主动给出代价再给替代方案，才是完整答案。</em></p>", "面试高频：切片能上车吗"),
        CALLOUT("intuition", "但也别把话说死。切片在车端有<strong>两个仍然成立的用法</strong>：① <strong>离线数据挖掘与自动标注</strong>——用切片跑一个「慢但准」的教师模型给车队回传数据打伪标签，再蒸馏给车端小模型（C58 会讲）；② <strong>低频触发</strong>——不是每帧都切，而是在「地图提示前方有标志」或「上一帧有低分候选」时，对<em>某一个 ROI</em> 做一次高分辨率精检。<em>后者其实已经滑向了下一节的两级级联。</em>"),
    ])),
    ("cascade", "两级级联：量产系统的现实选择", "".join([
        P("既然「全图高分辨率」太贵、「全图低分辨率」看不见，出路就只剩一条：<strong>只在可能有目标的地方付高分辨率的钱</strong>。这就是<span class=\"term\">two-stage cascade</span>（两级级联）。"),
        ASCII("""┌── Level 1：便宜、高召回、可以很不准 ────────────────────────┐
│  输入：1920×1080 下采样到 640×384（或只跑 ROI 带）          │
│  任务：**类别无关**的「这里可能有个标志」提议                 │
│  阈值：**故意调得很低**（score > 0.05），宁可多提议           │
│  输出：K 个 ROI（典型 K = 2–6），耗时 ~0.5–3 ms             │
└───────────────────┬────────────────────────────────────────┘
                    │  ROI 坐标映射回**原始分辨率**
                    ▼
┌── Level 2：贵、精确、只跑 K 次小图 ─────────────────────────┐
│  输入：从**原生 1920×1080** 上裁 K 个 256×256 patch         │
│  任务：精检 + 细分类（限速 40/50/60/…）                      │
│  阈值：正常（score > 0.4），这里才决定最终输出                │
│  耗时：K × 0.8 ms                                          │
└────────────────────────────────────────────────────────────┘
关键：ROI 裁剪用的是**原图像素**，不是 Level 1 的下采样图 ——
      所以 Level 2 看到的标志仍然是 16.6 px 而不是 5.5 px。""")
        ,
        P("级联的收益结构与切片完全不同：<strong>切片是「无差别地把整图放大 3 倍」，级联是「只把 K 个小窗口放大 3 倍」</strong>。当目标稀疏（一帧里通常只有 0–3 个标志）时，后者的浪费小得多。"),
        H3("级联的代价：召回是乘法"),
        MATH("R_{\\text{cascade}} \\;=\\; R_{\\text{level1}} \\times R_{\\text{level2}} \\;\\le\\; \\min(R_1, R_2)"),
        DUAL(
            "<strong>这个乘法是级联系统的阿喀琉斯之踵，也是必考点</strong>：Level 1 漏掉的目标，Level 2 永远没有机会看到。所以级联设计的第一原则是——<strong>Level 1 的工作点必须极度偏向召回，精度完全不重要</strong>。做法是：类别无关（只判「是不是一个牌子状的东西」，任务比多类分类简单得多）、score 阈值压到 0.05、输出 top-K 而不是阈值过滤、必要时把 Level 1 的正样本分配放宽（模块 03 的 NWD / center-based 分配在这里正合适）。<em>Level 1 多提 3 个假 ROI 的代价只是 2.4 ms，漏掉 1 个真标志的代价是漏检。</em>",
            "严谨地说，级联的单帧召回确实低于切片（notebook 里的模拟：切片 0.91、级联 0.52–0.76、全图下采样 0.04）。但<strong>单帧召回不是 TSR 的正确指标</strong>——标志是静止的、自车在接近它，同一个标志会在连续几十帧里反复出现。若把每帧的检出近似为独立事件，<em>N 帧内至少检出一次</em>的概率是 1−(1−R)<sup>N</sup>：级联 R=0.76 时 5 帧后是 <strong>99.9%</strong>，切片 R=0.91 时是 99.999%——<strong>两者在「首次检出距离」上的差距被时序累积几乎抹平，而 8× 的延迟差距是抹不平的</strong>。C55 模块 04 会把这个时序累积讲透。<em>注意独立性假设是乐观的：遮挡、逆光、运动模糊会让相邻帧的失败强相关，实际需要更多帧。</em>",
        ),
        TABLE(["方案", "16.6 px 标志进入网络时的尺寸", "单帧召回（模拟）", "5 帧累积召回", "延迟", "车端可行"], [
            ["全图下采样 640×384", "5.5 px", "0.04", "0.18", "<strong>3.0 ms</strong>", "✅ 但基本检不出"],
            ["两级级联（全图 L1）", "16.6 px", "0.52", "0.97", "<strong>6.2 ms</strong>", "✅"],
            ["<strong>两级级联（ROI 引导 L1）</strong>", "16.6 px", "<strong>0.76</strong>", "<strong>0.999</strong>", "<strong>5.0 ms</strong>", "<strong>✅ 推荐</strong>"],
            ["SAHI 切片 s=640 r=0.2", "16.6 px", "0.91", "0.99999", "40.0 ms", "❌"],
        ]),
        CALLOUT("warn", "级联有一个隐蔽的失败模式：<strong>Level 1 与 Level 2 的训练分布不一致</strong>。Level 2 只在「Level 1 提议的窗口」上推理，而这些窗口是<em>以目标为中心、带一定 padding 的裁剪</em>——如果 Level 2 是在整图上训练的，它见过的目标位置分布是均匀的，而线上见到的目标几乎总在窗口正中央。<strong>模型会学到「中心先验」并在 ROI 边缘的目标上失效</strong>（而 ROI 边缘恰恰是 Level 1 定位不准时目标所在的位置）。<em>解法是用 Level 1 的真实提议（含定位误差）去生成 Level 2 的训练裁剪，而不是用 GT 框裁——这叫「按推理时的分布训练」，是所有级联系统的通用纪律。</em>"),
        CALLOUT("intuition", "级联的第三个好处常被忽略：<strong>它天然把「检测」和「细分类」解耦</strong>。Level 1 只需要知道「有个牌子」，Level 2 在高分辨率 crop 上做 100+ 类的细分类。这正是 C55 模块 02 讲的 TSR 两级方案——<em>新增一个限速档位只要重训 Level 2，检测器完全不动</em>。<strong>所以在 TSR 里，两级级联同时解决了小目标问题和长尾类别问题，这是它比切片更受量产系统青睐的深层原因。</strong>"),
    ])),
    ("prior", "先验驱动的 ROI：地图、车道与消失点", "".join([
        P("上一节的 Level 1 还是要跑一遍全图。<strong>能不能连全图都不跑？</strong>能——只要你有先验知道标志会出现在哪。这是把延迟继续往下压的最后一招，也是把召回往上抬的最有效一招。"),
        TABLE(["先验来源", "能圈出什么", "可靠性", "获取成本", "失效场景"], [
            ["<strong>消失点 / 地平线带</strong>", "远处标志只出现在地平线上方一条窄带内（模块 05 会精确推导）", "<strong>高</strong>（几何必然）", "几乎为零（标定 + 俯仰角）", "急弯、陡坡、颠簸、相机俯仰突变"],
            ["<strong>车道线 / 可行驶区域</strong>", "标志在车道走廊两侧与上方的有限横向范围", "中-高", "复用已有车道感知输出", "路口、匝道、车道线缺失"],
            ["<strong>高精地图 + 定位</strong>", "地图里记录了每块标志的精确位置，可直接投影到图像", "<strong>极高</strong>（有则必有）", "高（建图 + 维护 + 定位精度）", "临时施工牌、新增/移除标志、定位漂移"],
            ["<strong>上一帧的跟踪结果</strong>", "已跟踪目标按自车运动外推的预测位置", "高（近处）", "低（复用跟踪器）", "首次出现的目标——这恰恰是最需要的那个"],
            ["<strong>低分候选（记忆 ROI）</strong>", "上一帧 score 在 0.05–0.4 之间的「疑似」位置", "中", "低", "会累积假 ROI，需要衰减机制"],
        ]),
        DUAL(
            "这些先验的正确用法<strong>不是「圈出来只看这里」，而是「在这里多花算力」</strong>。两种用法差别巨大：前者是 hard gating，先验错一次就是一次彻底漏检；后者是 <em>算力的非均匀分配</em>——ROI 内用原生分辨率精检，ROI 外仍然跑一遍便宜的全图下采样兜底。<strong>后者的最坏情况退化成「只有全图下采样」，而不是「什么都没有」。</strong>",
            "严谨地说，这是一个<span class=\"term\">foveated inference</span>（中心凹式推理）架构：模仿人眼「周边视觉低分辨率 + 中央凹高分辨率」的资源分配。设 ROI 面积占比 α、ROI 内分辨率倍数 β，总像素吞吐 ≈ (1−α)·1 + α·β²（相对全图下采样）。<strong>TSR 的关键数字：模块 05 会算出远距标志所在的地平线带只占全图约 7% 的面积</strong>，取 β=3（原生分辨率），吞吐 = 0.93 + 0.07×9 = <strong>1.56×</strong>——<em>用 1.56 倍的算力买到了远距目标 3 倍的有效分辨率，而全图原生分辨率要 9 倍</em>。这就是 ROI 先验的全部价值。",
        ),
        CALLOUT("danger", "<p>把先验做成 hard gating 是一个会出安全事故的设计。真实案例形态：<strong>ROI 按平路标定的地平线固定在图像 42% 高度处，车辆上坡时相机俯仰变化，标志跑到 ROI 之外，整段坡道上的限速牌全部漏检</strong>——而且这类失效<em>与地点强相关、可复现、集中爆发</em>，恰恰是最糟糕的失效形态（不是随机漏一两个，而是某段路必然全漏）。<strong>纪律：任何基于先验的 ROI 都必须 ① 带足够的余量（俯仰 ±3° 换算成像素的余量）、② 用实时估计的俯仰角/地平线而不是标定常数、③ 保留一路无先验的全图兜底。</strong></p>", "ROI 先验必须是软的"),
        P("<strong>动态分辨率</strong>是同一思想的另一种实现：不裁剪，而是让整张图的采样密度非均匀——远处（图像上部靠近地平线）用高采样率，近处（图像下部）用低采样率。工程上可以用一次可微的重采样（类似 <em>Learning to Zoom</em> / <em>FOVEA</em> 的思路）实现。<em>好处是仍然只有一次前向、张量形状固定，对 TensorRT 友好；代价是几何畸变要在后处理里精确反解，且与增强/标定的耦合更强。</em>"),
        CALLOUT("intuition", "把先验驱动 ROI 与前两节合起来看，会发现一条清晰的演进线：<strong>「全图均匀高分辨率」（太贵）→「全图均匀低分辨率」（看不见）→「切片：均匀高分辨率但分次做」（还是太贵）→「级联/ROI：非均匀分辨率」（可行）</strong>。<em>每一步都在做同一件事——把算力从「哪里都花」变成「花在该花的地方」。</em>这条线在 LLM 推理（KV cache 稀疏化）、视频编码（ROI 码率分配）、雷达波束调度里长得一模一样。"),
    ])),
    ("train", "切片训练：SAHI 的另一半，也是最常被漏掉的一半", "".join([
        P("绝大多数人用 SAHI 只用了推理那一半（<span class=\"term\">SAHI</span> = Slicing Aided Hyper <em>Inference</em>），而论文里还有另一半：<span class=\"term\">slicing aided fine-tuning</span>（切片辅助微调，SF）。<strong>不做 SF 而只做切片推理，收益会显著低于预期，甚至可能掉点。</strong>"),
        H3("为什么必须重新微调"),
        P("原因是<strong>训练与推理的目标尺度分布不一致</strong>。假设你的模型是在「1920×1080 整图 letterbox 到 640」上训练的，那么它见过的标志尺寸分布是 5.5 px 附近；而切片推理时它见到的是 16.6 px 附近。<em>这是一个 3 倍的尺度漂移</em>。"),
        TABLE(["", "训练时（整图 letterbox 640）", "推理时（切片 640 原生）", "后果"], [
            ["标志的输入像素", "5.5 px（60 m 外）", "<strong>16.6 px</strong>", "尺度分布整体右移 3×"],
            ["被分配到的 FPN 层", "P2/P3（最浅）", "P3/P4", "<strong>负责该尺度的分支权重没被充分训练</strong>"],
            ["anchor / 回归目标范围", "集中在最小几档", "中档", "回归头输出分布偏移"],
            ["背景上下文比例", "整幅街景", "<strong>局部 640 窗口</strong>", "上下文先验失效，误检上升"],
            ["近处大标志", "常见（几百 px）", "<strong>被切成碎片或超出切片</strong>", "大目标 AP 下降"],
        ]),
        DUAL(
            "SF 的做法非常朴素：<strong>训练集也切片</strong>——把训练图按与推理相同的 (s, r) 切成小图、同步变换标注、丢掉可见比例过低的框，然后<em>把切片小图与原始整图按一定比例混合</em>训练。混合是关键：只用切片训练会毁掉大目标；SAHI 论文的做法是切片图 + 全图一起喂。<strong>一句话：让训练分布长得像推理分布。</strong>",
            "严谨地说，SF 修正的是四件事里的三件（尺度分布、FPN 层负载、回归目标范围），<em>第四件（上下文缺失）是切片这个方法本身的固有损失，SF 修不了</em>。这也解释了一个常见观察：SF 之后小目标 AP 大涨，但某些强依赖上下文的类别（悬挂在龙门架上的指路牌、需要靠杆件确认的方向牌）反而略降。<strong>另外，切片训练的标注处理有个必须定死的规则：一个被切片边界截断的 GT 框，可见比例低于阈值 τ（典型 0.3–0.5）就丢弃，高于阈值就<em>裁剪到切片内</em>作为新 GT</strong>。τ 太低会引入大量「半个标志」的噪声标签，τ 太高会造成「图里明明有东西却标成背景」的负监督污染——<em>C56 模块 01 讲的越界处理规则在这里完全适用</em>。",
        ),
        CALLOUT("warn", "同样的「训练-推理分布一致」纪律也适用于<strong>两级级联</strong>：Level 2 必须用「Level 1 真实提议裁出来的 crop」训练，而不是用 GT 框裁出来的 crop。<em>前者带着 Level 1 的定位噪声与假阳性，后者是理想化的。用后者训练、用前者推理，是级联系统掉点的头号原因。</em>这与预处理一致性（C60 模块 01）是同一类问题的不同层次：<strong>凡是推理时的输入由另一个模块产生，训练时就必须用那个模块的真实输出，而不是真值。</strong>"),
        CALLOUT("intuition", "所以本模块的三条路径各自需要什么，可以列成一张对照：<strong>切片推理需要切片微调；两级级联需要用真实提议训练 Level 2；ROI 裁剪需要把 ROI 内的分布也放进训练集</strong>。<em>三者的共同结构是「推理时输入被某种裁剪/缩放变换过，训练时就必须复现那个变换」</em>——记住这个结构，比记住三个方法名有用得多。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>可学习的 ROI 提议与端到端 foveation</strong>：目前的 ROI 先验（消失点、地图、跟踪外推）都是手工规则。让网络自己学「该往哪看」——如 <em>Learning to Zoom</em>、<em>FOVEA</em>、<em>Efficient Adaptive Resolution</em> 这一系——在离线基准上已能匹敌固定高分辨率且省 2–4× 算力，但<em>可学习的注意力区域在安全关键系统里难以验证</em>（它可能学到与训练集地理位置强相关的捷径），这是上车的主要障碍。",
            "<strong>切片与端到端检测器的融合</strong>：DETR 系（C54）的 query 本身就是稀疏的，理论上可以让不同 query 在不同分辨率的特征上采样（Deformable DETR 的多尺度可变形注意力已经部分做到）。<em>「让一部分 query 去原生分辨率上采样，其余 query 用低分辨率」——这是把级联思想内化进单个模型的路线</em>，目前的难点是采样位置的学习信号在小目标上仍然稀疏。",
            "<strong>跨片合并的可学习化</strong>：NMM 的 IoS 阈值、贴边判定余量、碎片是否可信，目前全是手工阈值。把「这两个碎片是不是同一个物理目标」建模成一个轻量的关系判别（类似多目标跟踪里的关联网络）是自然的方向，<em>但训练数据需要「被切片截断」的成对标注，构造成本高</em>。",
            "<strong>硬件侧的非均匀采样</strong>：event camera、可变焦/可变分辨率 sensor、以及 ISP 侧的 ROI 直出，能把「非均匀分辨率」从算法层下沉到传感器层，从根上消除下采样损失。<em>量产可行性与标定复杂度是当前瓶颈。</em>",
            "<strong>评测方法学的空白</strong>：几乎所有小目标基准报告的都是整图 AP<sub>small</sub>，<em>没有一个公开基准报告「切片边界附近的召回」这一项</em>——而这正是重叠率下界所刻画的失效模式。模块 05 会给出按像素尺寸分桶的评测实现，但「按<em>位置</em>分桶」（边界 vs 中心）同样必要且几乎无人做。",
            "<strong>切片推理的能耗账</strong>：车端真正的约束往往不是峰值算力而是<strong>热与功耗</strong>。8× 的持续计算会触发降频（C60 模块 05），使延迟在长时间行驶后漂移——<em>这类「跑得久了变慢」的效应在离线基准上完全不可见</em>，也是学术方法与量产之间少有人量化的鸿沟。",
        ]),
        CALLOUT("paper", "必读：<strong>Akyon et al., <em>Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection</em> (ICIP 2022)</strong>——SAHI 原论文，务必读它的 fine-tuning 一节而不只是 inference；<strong>Unel et al., <em>The Power of Tiling for Small Object Detection</em> (CVPRW 2019)</strong>——最早系统性论证切片有效性的工作，重叠率的经验取值来自这里；<strong>Recasens et al., <em>Learning to Zoom</em> (ECCV 2018)</strong> 与 <strong>Thavamani et al., <em>FOVEA: Foveated Image Magnification for Autonomous Navigation</em> (ICCV 2021)</strong>——可学习非均匀采样的两篇代表作，FOVEA 直接以自动驾驶为背景，是本模块「动态分辨率」一节的一手来源；<strong>Zhu et al., <em>Deformable DETR</em> (ICLR 2021)</strong>——稀疏采样的另一条路线；<strong>VisDrone / xView / TT100K</strong> 三个基准的官方报告，用来对照「离线基准上切片能涨多少」的真实数量级。相邻课程：C53 m05（端到端延迟拆解）、C55 m04（时序累积如何抹平单帧召回差距）、C56 m01（裁剪与越界规则）、C60 m01/m05（预处理一致性与降频）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 切片推理与高分辨率策略（SAHI 切片 / 重叠率下界 / 跨片 NMM / 两级级联）

目标：把「切片推理」从一个方法名变成一套**能算清代价、能推出参数、能自己实现**的工程方案，
并亲手论证它<b>为什么在车端量产系统里基本不可用</b>、替代方案是什么。

本 notebook 你会亲手实现：
1. **切片网格生成**（尺寸 s / 步长 / 重叠率 r，含贴边补片），以及片数随 r 的**阶梯效应**
2. **坐标还原**（局部 → 全图）与跨片重复检出的量化
3. **重叠率下界 `s·r ≥ d_max` 的数值验证**——穷举所有位置，证明下界是紧的
4. **跨片合并**：IoU / IoS 的差别，NMS（抑制）与 **NMM（合并）**，以及「贴边门控」
5. **代价账**：切片数、像素吞吐的渐近律 `N·s² ≈ W·H/(1-r)²`、车端延迟预算对照
6. **两级级联** vs 切片 vs 全图下采样的**端到端延迟与召回**对比，以及时序累积如何改变结论

> 心智模型：**切片没有创造信息，它只是拒绝丢弃信息。
> 收益 = 你在 resize 阶段丢掉的那部分；代价 = 4–16 倍的算力。**"""),
    md("""## 1 · 切片网格：尺寸 s、步长与重叠率 r

先把几何写死。步长 `stride = s(1-r)`，重叠像素 `s·r`。
切片原点取 `0, stride, 2·stride, …`，**最后一片贴右边界**保证覆盖完整（SAHI 的标准做法）。"""),
    code("""import numpy as np, math
from collections import Counter
np.set_printoptions(precision=3, suppress=True)

W, H = 1920, 1080      # 车载前视主摄的典型分辨率
S_SIGN = 0.6           # 限速牌物理直径 60 cm
F_PX = 1662.77         # 60° 水平 FOV / 1920 宽 的等效焦距（像素）—— 模块 05 会完整推导

def slice_origins(total, s, stride):
    '''一维切片起点：0, stride, 2*stride, ...，最后一片贴边界保证覆盖完整。'''
    if total <= s:
        return [0]
    xs = list(range(0, total - s + 1, stride))
    if xs[-1] != total - s:
        xs.append(total - s)          # 贴边补片：代价是它与前一片的重叠更大
    return xs

def make_slices(W, H, s, r):
    '''返回 [(x0,y0,x1,y1), ...] 与步长。r = 重叠率。'''
    stride = max(1, int(round(s * (1.0 - r))))
    xs = slice_origins(W, s, stride)
    ys = slice_origins(H, s, stride)
    return [(x, y, x + s, y + s) for y in ys for x in xs], stride

slices, stride = make_slices(W, H, 640, 0.20)
print(f'W×H = {W}×{H},  s = 640,  r = 0.20  ->  stride = {stride},  overlap = {640-stride} px')
for i, sl in enumerate(slices):
    print(f'  slice {i}: x[{sl[0]:4d},{sl[2]:4d})  y[{sl[1]:4d},{sl[3]:4d})')
assert len(slices) == 8 and stride == 512
print(f'\\n切片数 N = {len(slices)}   放大倍数 W/s = {W/640:.1f}×（目标线性尺寸放大 3 倍、面积 9 倍）')"""),
    code("""# ① 覆盖完整性：每个像素至少被一片覆盖（在 1/8 网格上验证）
cov = np.zeros((H // 8, W // 8), dtype=int)
for (x0, y0, x1, y1) in slices:
    cov[y0 // 8:y1 // 8, x0 // 8:x1 // 8] += 1
print('像素被覆盖次数的分布:', dict(zip(*[a.tolist() for a in np.unique(cov, return_counts=True)])))
assert cov.min() >= 1, '存在未被任何切片覆盖的像素'
print(f'最少覆盖 {cov.min()} 次，最多 {cov.max()} 次  ->  重叠带与四角会被重复处理')

# ② 片数是 r 的**阶梯函数** —— 阶梯上有免费午餐
print(f"\\n{'r':>6s} {'stride':>7s} {'overlap px':>11s} {'横':>4s} {'纵':>4s} {'N':>4s} {'像素吞吐(Mpx)':>14s}")
for r in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
    sl, st = make_slices(W, H, 640, r)
    nx, ny = len(slice_origins(W, 640, st)), len(slice_origins(H, 640, st))
    print(f'{r:>6.2f} {st:>7d} {640-st:>11d} {nx:>4d} {ny:>4d} {len(sl):>4d} {len(sl)*640*640/1e6:>14.2f}')
n10 = len(make_slices(W, H, 640, 0.10)[0])
n30 = len(make_slices(W, H, 640, 0.30)[0])
assert n10 == n30 == 8, (n10, n30)
print('\\n✅ r 从 0.10 涨到 0.30，片数都是 8 —— **把 r 从下界推到片数跳变前，是免费的鲁棒性**')
print('   调参顺序：先按「目标要放大到多少像素」定 s，再按下界定 r，最后在阶梯上把 r 往上推')"""),
    md("""## 2 · 坐标还原与跨片重复检出

检测器在切片里输出的是**局部坐标**，还原只需加上切片原点。
但重叠带里的目标会被多片各检出一次——这是 NMS 该处理的情形。"""),
    code("""def make_scene(n=12, seed=7):
    '''合成一张街景里的交通标志：像素尺寸由针孔模型 p = f·S/Z 给出（远小近大），
       位置集中在地平线带附近（模块 05 会精确推导这条带），互相保持最小间距。'''
    g = np.random.default_rng(seed)
    recs, tries = [], 0
    while len(recs) < n and tries < 50000:
        tries += 1
        Z = g.uniform(18.0, 150.0)                 # 距离 18–150 m
        p = F_PX * S_SIGN / Z                      # 像素尺寸：55.4 px（18m）… 6.7 px（150m）
        cx = g.uniform(0.06 * W, 0.94 * W)
        cy = H * 0.42 + g.uniform(-90.0, 90.0)     # 地平线带附近
        if any(abs(cx - c) < 130 and abs(cy - d) < 130 for c, d, _, _ in recs):
            continue                               # 保持最小间距，避免合成出「本来就该合并」的歧义
        recs.append((cx, cy, p, Z))
    boxes = np.array([[c - p / 2, d - p / 2, c + p / 2, d + p / 2] for c, d, p, _ in recs])
    zs = np.array([z for _, _, _, z in recs])
    return boxes, zs

GT, GT_Z = make_scene(12, seed=7)
sizes = GT[:, 2] - GT[:, 0]
order = np.argsort(GT_Z)
print(f"{'#':>3s} {'距离 Z(m)':>10s} {'像素尺寸':>9s} {'中心 (cx, cy)':>22s}")
for i in order:
    cx, cy = (GT[i, 0] + GT[i, 2]) / 2, (GT[i, 1] + GT[i, 3]) / 2
    print(f'{i:>3d} {GT_Z[i]:>10.1f} {sizes[i]:>9.1f} {f"({cx:7.1f}, {cy:6.1f})":>22s}')
print(f'\\n共 {len(GT)} 个标志：{sizes.min():.1f} – {sizes.max():.1f} px；'
      f'其中 < 32 px（COCO small）的有 {int((sizes < 32).sum())} 个')
assert sizes.min() > F_PX * S_SIGN / 150 - 1e-9 and sizes.max() < F_PX * S_SIGN / 18 + 1e-9
D_MAX = float(sizes.max())
print(f'本图的 d_max = {D_MAX:.1f} px  ->  重叠率下界 r >= d_max/s = {D_MAX/640:.4f}')"""),
    code("""def detect_in_slice(gt, sl, vis_thr=0.9):
    '''模拟检测器在一个切片上的输出：GT 与切片的交集占 GT 面积 >= vis_thr 才检出，
       返回的是**被切片截断后的框**（局部坐标）—— 这正是跨片合并要处理的东西。'''
    x0, y0, x1, y1 = sl
    out = []
    for i, (gx0, gy0, gx1, gy1) in enumerate(gt):
        ix0, iy0 = max(gx0, x0), max(gy0, y0)
        ix1, iy1 = min(gx1, x1), min(gy1, y1)
        iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
        vis = iw * ih / ((gx1 - gx0) * (gy1 - gy0))
        if vis >= vis_thr:
            out.append({'box_local': (float(ix0 - x0), float(iy0 - y0),
                                      float(ix1 - x0), float(iy1 - y0)),
                        'score': float(0.50 + 0.45 * vis), 'gt_id': i, 'vis': float(vis)})
    return out

per_slice = [detect_in_slice(GT, sl, vis_thr=0.9) for sl in slices]
print(f"{'切片':>5s} {'检出数':>7s}  命中的 gt_id")
for i, ds in enumerate(per_slice):
    print(f'{i:>5d} {len(ds):>7d}  {[d["gt_id"] for d in ds]}')

# ---- 坐标还原：局部 -> 全图（只是平移；若切片还被 letterbox 过，必须先反 letterbox）----
glob = []
for (x0, y0, _, _), ds in zip(slices, per_slice):
    for d in ds:
        bx0, by0, bx1, by1 = d['box_local']
        glob.append({'box': (bx0 + x0, by0 + y0, bx1 + x0, by1 + y0),
                     'score': d['score'], 'gt_id': d['gt_id']})
cnt = Counter(d['gt_id'] for d in glob)
print(f'\\n还原后共 {len(glob)} 个框，对应 {len(cnt)} 个真值目标')
print('被多片重复检出的目标:', {k: v for k, v in sorted(cnt.items()) if v > 1})
assert set(cnt) == set(range(len(GT))), 'r=0.2 满足下界，所有目标都应被某片完整包含'
assert len(glob) > len(cnt), '重叠带必然产生重复检出'
print(f'\\n✅ 重复率 = {len(glob)/len(cnt):.2f}×  —— 这些是几乎重合的框，标准 NMS 就能处理')
print('⚠️  下一节会看到：r **低于下界**时产生的是「半截框」，NMS 处理不了')"""),
    md("""## 3 · 重叠率的下界：`s·r ≥ d_max`

推导（一维）：目标占 `[x, x+d]`，第 i 片覆盖 `[o_i, o_i+s]`。
完整包含 ⟺ `x+d-s ≤ o_i ≤ x`，即合法原点必须落在一个**长度 s−d 的区间**里。
等差数列（公差 stride）与任意长度 L 的闭区间必然相交 ⟺ `stride ≤ L`。于是

    stride ≤ s − d   ⟺   s(1−r) ≤ s − d   ⟺   **s·r ≥ d**

下面穷举**所有整数位置**验证这个下界是**紧的**。"""),
    code("""def uncovered_positions(total, s, r, d):
    '''穷举所有整数位置，返回「无法被任何一片完整包含」的目标左边界列表 + 切片原点。'''
    stride = max(1, int(round(s * (1.0 - r))))
    origins = slice_origins(total, s, stride)
    bad = [x for x in range(0, total - d + 1)
           if not any(o <= x and x + d <= o + s for o in origins)]
    return bad, origins

s_, d_ = 640, 64
print(f'切片 s = {s_},  目标 d = {d_}   ->   理论下界  r >= d/s = {d_/s_:.4f}')
print(f"\\n{'r':>6s} {'stride':>7s} {'overlap px':>11s} {'必然被截断的位置数':>20s} {'':>3s}")
for r in [0.00, 0.02, 0.05, 0.07, 0.09, 0.10, 0.12, 0.20]:
    bad, _ = uncovered_positions(W, s_, r, d_)
    st = max(1, int(round(s_ * (1 - r))))
    print(f'{r:>6.2f} {st:>7d} {s_-st:>11d} {len(bad):>20d} {"✅" if not bad else "❌":>3s}')

b09, _ = uncovered_positions(W, s_, 0.09, d_)
b10, _ = uncovered_positions(W, s_, 0.10, d_)
assert len(b10) == 0, 'r = d/s 恰好达到下界，应当零失败'
assert len(b09) > 0, 'r 比下界小一点点就出现必然截断的位置'
print(f'\\nr = 0.09  overlap = {s_-int(round(s_*0.91))} px  <  d = 64  ->  失败位置 {b09}')
print(f'r = 0.10  overlap = {s_-int(round(s_*0.90))} px  =  d = 64  ->  失败位置 {b10}')
print('\\n✅ **下界是紧的**：overlap_px >= d 时零失败；少 1 个像素就出现两段必然失败的区间')
print('⚠️  注意失败位置是**固定的几条竖线**（切片边界附近）——')
print('    这类漏检与位置强相关，在随机划分的验证集上被平均掉，上路后表现为「某些路段总漏牌」')"""),
    code("""# ---- r 低于下界时会发生什么：构造一个必然被截断的目标 ----
r_bad = 0.05
sl_bad, st_bad = make_slices(W, H, 640, r_bad)
b_bad, org_bad = uncovered_positions(W, 640, r_bad, 64)
print(f'r = {r_bad}: stride = {st_bad}, overlap = {640-st_bad} px  <  d = 64 px  ❌')
print(f'切片原点 = {org_bad};  必然失败的左边界区间 = [{min(b_bad)}, {max(b_bad)}] 等')

target = np.array([[590.0, 380.0, 654.0, 444.0]])       # 64×64，左边界 590 落在失败区间里
TGT = tuple(float(v) for v in target[0])
print(f'\\n目标框 = {TGT}   (左边界 590 ∈ 失败区间)')

strict = [detect_in_slice(target, sl, vis_thr=0.9) for sl in sl_bad]
n_strict = sum(len(x) for x in strict)
print(f'严格检测器（可见率 >= 0.90 才检出）: 全部 {len(sl_bad)} 片共检出 {n_strict} 个  ->  **完全漏检**')
assert n_strict == 0, '低于下界 + 严格检测器 = 跨边界目标被彻底吞掉'

lenient = [detect_in_slice(target, sl, vis_thr=0.5) for sl in sl_bad]
frags = []
for (x0, y0, _, _), ds in zip(sl_bad, lenient):
    for dd in ds:
        bx0, by0, bx1, by1 = dd['box_local']
        frags.append(((bx0 + x0, by0 + y0, bx1 + x0, by1 + y0), dd['score'], dd['vis']))
print(f'\\n宽松检测器（可见率 >= 0.50）: 得到 {len(frags)} 个**半截框**')
for b, sc, v in frags:
    print(f'  {tuple(round(t,1) for t in b)}   score={sc:.3f}   可见率={v:.3f}')
assert len(frags) == 2
print('\\n⚠️  半截框的 score 仍然不低（模型看到半个红圈也会给高分），但**框是错的、尺寸小了一半**。')
print('    TSR 里若按框的像素尺寸反推距离，半截框会让距离估计直接翻倍出错。')"""),
    md("""## 4 · 跨片合并：IoU vs IoS，NMS（抑制）vs NMM（合并）

跨片截断场景要问的不是「两个框有多像」（IoU），
而是「**小的那个有多大比例被包住**」（IoS = Intersection over Smaller area）。"""),
    code("""def iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def ios(a, b):
    '''Intersection over Smaller area：度量「小框有多大比例被大框包住」。'''
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    sm = min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
    return inter / sm if sm > 0 else 0.0

def nms(boxes, scores, thr=0.6):
    '''标准 NMS：**抑制**（删掉）高 IoU 的低分框。'''
    idx = [int(i) for i in np.argsort(scores)[::-1]]
    keep = []
    while idx:
        i = idx.pop(0)
        keep.append(i)
        idx = [j for j in idx if iou(boxes[i], boxes[j]) <= thr]
    return keep

def nmm(boxes, scores, ios_thr=0.5):
    '''Non-Maximum **Merging**：把 IoS 高的框**并起来**（取包围盒），而不是删掉。'''
    order = [int(i) for i in np.argsort(scores)[::-1]]
    used, out = set(), []
    for i in order:
        if i in used:
            continue
        used.add(i)
        bx, sc, members = list(boxes[i]), float(scores[i]), [i]
        for j in order:
            if j in used:
                continue
            if ios(tuple(bx), boxes[j]) >= ios_thr:
                used.add(j); members.append(j)
                bx = [min(bx[0], boxes[j][0]), min(bx[1], boxes[j][1]),
                      max(bx[2], boxes[j][2]), max(bx[3], boxes[j][3])]
                sc = max(sc, float(scores[j]))
        out.append({'box': tuple(bx), 'score': sc, 'members': members})
    return out

print('IoU / IoS / NMS / NMM 就位')
# 自检：一个小框完全落在大框内部
small, big = (10.0, 10.0, 20.0, 20.0), (0.0, 0.0, 40.0, 40.0)
print(f'  小框完全被大框包住:  IoU = {iou(small, big):.4f}   IoS = {ios(small, big):.4f}')
assert abs(ios(small, big) - 1.0) < 1e-12 and iou(small, big) < 0.07
print('  -> **IoU 看不见「包含」关系，IoS 能**')"""),
    code("""# ---- 用上一节的两个半截框做对比 ----
fb = [f[0] for f in frags]
fs = [f[1] for f in frags]
print(f'碎片 A = {tuple(round(t,1) for t in fb[0])}   score = {fs[0]:.3f}')
print(f'碎片 B = {tuple(round(t,1) for t in fb[1])}   score = {fs[1]:.3f}')
print(f'\\nIoU(A,B) = {iou(fb[0], fb[1]):.4f}   <- NMS 用它  ->  判定为「两个不同目标」❌')
print(f'IoS(A,B) = {ios(fb[0], fb[1]):.4f}   <- NMM 用它  ->  判定为「同一目标的两块」✅')

keep = nms(fb, fs, thr=0.60)
print(f'\\nNMS(IoU > 0.60) 保留 {len(keep)} 个框  ->  重复输出，且两个都是**半截框**')
merged = nmm(fb, fs, ios_thr=0.50)
mb = merged[0]['box']
print(f'NMM(IoS >= 0.50) 输出 {len(merged)} 个框: {tuple(round(t,1) for t in mb)}')
print(f'  与真值 {TGT} 的 IoU = {iou(mb, TGT):.4f}')
assert len(keep) == 2 and len(merged) == 1
assert iou(mb, TGT) > 0.999, 'NMM 的并集应当精确恢复真值框'
print('\\n✅ 「同一物理实体被切成多份分别观测」的场景，需要的是**合并算子**而不是抑制算子')"""),
    code("""def is_boundary(box_local, s, margin=2.0):
    '''框是否触到所在切片的边界 —— 触到就说明它**可能**被截断。'''
    x0, y0, x1, y1 = box_local
    return x0 <= margin or y0 <= margin or x1 >= s - margin or y1 >= s - margin

print(f"{'切片':>5s} {'局部框 (x0,y0,x1,y1)':>34s}  贴边?")
for i, ((x0, y0, _, _), ds) in enumerate(zip(sl_bad, lenient)):
    for dd in ds:
        bl = tuple(round(t, 1) for t in dd['box_local'])
        print(f'{i:>5d} {str(bl):>34s}  {"是 ⚠️ 可能被截断" if is_boundary(dd["box_local"], 640) else "否"}')

# ---- 为什么 NMM 必须以「贴边」为门控 ----
up   = (700.0, 300.0, 740.0, 396.0)     # 限速牌（含下方辅助牌区域的大框）
down = (700.0, 344.0, 740.0, 396.0)     # 下方的辅助牌，完全落在上面那个大框里
print(f'\\n上下叠放的两块牌:  IoU = {iou(up, down):.3f}   IoS = {ios(up, down):.3f}')
assert ios(up, down) > 0.99 and iou(up, down) < 0.6
print('  -> 无条件 NMM 会把它们**错误地并成一个大框**（IoS = 1.0）')
print('  -> 而它们都不贴边（假设它们落在某片内部），贴边门控会跳过它们  ✅')
assert not is_boundary((up[0] - 640, up[1], up[2] - 640, up[3]), 640)
assert not is_boundary((down[0] - 640, down[1], down[2] - 640, down[3]), 640)
print('\\n✅ 工程配方：① 只对**贴边框**做 IoS-NMM 缝合  ② 再对全部框做一次常规 IoU-NMS 去重')
print('   ③ 贴边但配不上对的框，保留并打 truncated 标记（让跟踪与距离估计降权），而不是直接丢')"""),
    md("""## 5 · 代价账：切片数、像素吞吐与车端延迟预算"""),
    code("""def tile_stats(W, H, s, r):
    sl, st = make_slices(W, H, s, r)
    return len(sl), len(sl) * s * s

# ---- 渐近律：N·s² ≈ W·H/(1-r)²，**几乎与 s 无关** ----
W2, H2, r2 = 4096, 3072, 0.2
asym = W2 * H2 / (1 - r2) ** 2
print(f'渐近律验证（{W2}×{H2}, r={r2}）：W·H/(1-r)² = {asym/1e6:.2f} Mpx')
print(f"\\n{'s':>6s} {'N':>5s} {'实际像素吞吐(Mpx)':>18s} {'相对渐近值':>11s}")
for s_c in [512, 640, 1024]:
    n_, px_ = tile_stats(W2, H2, s_c, r2)
    dev = px_ / asym - 1
    print(f'{s_c:>6d} {n_:>5d} {px_/1e6:>18.2f} {dev:>+11.1%}')
    assert abs(dev) < 0.12, (s_c, dev)
print('\\n✅ **总计算量几乎与切片大小 s 无关，只由重叠率 r 决定**（偏差来自贴边补片的离散化）')
print('   s 决定的不是成本，而是**放大倍数 W/s** —— 先按放大倍数定 s，再按下界定 r，成本自动落定')"""),
    code("""MS_PER_MPX = 5.0 / (640 * 640 / 1e6)      # 640² 一次前向 5.0 ms（Orin 级、FP16、small 量级模型）
print(f'耗时模型: {MS_PER_MPX:.2f} ms/Mpx   (640×640 一次 = 5.0 ms)')

PLANS = [('全图下采样 640×384', 1, 640 * 384),
         ('全图原生 1920×1088', 1, 1920 * 1088)]
for r_ in [0.0, 0.2, 0.5]:
    n_, px_ = tile_stats(W, H, 640, r_)
    PLANS.append((f'切片 s=640 r={r_:.1f}', n_, px_))
n_, px_ = tile_stats(W, H, 512, 0.2)
PLANS.append(('切片 s=512 r=0.2', n_, px_))

base = 640 * 384 * MS_PER_MPX / 1e6
print(f"\\n{'方案':<22s} {'前向次数':>8s} {'像素(Mpx)':>10s} {'耗时(ms)':>9s} {'相对全图':>9s}")
for name, n_, px_ in PLANS:
    ms = px_ * MS_PER_MPX / 1e6
    print(f'{name:<22s} {n_:>8d} {px_/1e6:>10.2f} {ms:>9.1f} {ms/base:>8.1f}×')

TSR_BUDGET_MS = 8.0
ms_slice = tile_stats(W, H, 640, 0.2)[1] * MS_PER_MPX / 1e6
print(f'\\n30 FPS -> 整帧 {1000/30:.1f} ms，要装下 ISP、多相机、障碍物、车道、红绿灯、TSR、融合、预测、规控')
print(f'TSR 这一路真实能分到的通常是 5–10 ms（本课按 {TSR_BUDGET_MS:.0f} ms 算）')
print(f'切片 (s=640, r=0.2) 需要 {ms_slice:.1f} ms = 预算的 {ms_slice/TSR_BUDGET_MS:.1f} 倍   ->   ❌ 车端不可行')
assert ms_slice / TSR_BUDGET_MS >= 4.9
print('\\n✅ 「切片能提升小目标」必须连着「代价是 4–16×、车端装不下」一起说 —— 这是面试的分水岭')
print('   切片在车端仍成立的两个用法：① 离线自动标注/教师模型  ② 低频触发的单 ROI 高分辨率精检')"""),
    md("""## 6 · 两级级联 vs 切片 vs 全图：端到端延迟与召回

级联的召回是**乘法**：`R = R_level1 × R_level2`。
Level 1 漏掉的，Level 2 永远看不到 —— 所以 Level 1 必须极度偏向召回。"""),
    code("""def det_recall(px, p50, k=0.5):
    '''检出概率随目标在**网络输入里**的像素尺寸的 logistic 曲线（合成模型，用于相对比较）。'''
    return 1.0 / (1.0 + math.exp(-k * (px - p50)))

P50_DET, P50_PROP = 12.0, 5.0     # 完整检测（要判类别） vs 类别无关 + 低阈值的提议
Z_FAR = 60.0
p_native = F_PX * S_SIGN / Z_FAR
print(f'{Z_FAR:.0f} m 外的 {S_SIGN*100:.0f} cm 标志：原生 {p_native:.2f} px')
print(f'  -> 全图 letterbox 到 640 宽:  {p_native*640/W:.2f} px   （丢掉了 8/9 的像素）')
print(f'  -> 切片 / ROI 原生分辨率:     {p_native:.2f} px')

SCHEMES = {}
SCHEMES['全图下采样 640×384'] = dict(lat=3.0, pxin=p_native * 640 / W,
                                     recall=det_recall(p_native * 640 / W, P50_DET))
SCHEMES['两级级联(全图 L1)'] = dict(lat=6.2, pxin=p_native,
                                    recall=det_recall(p_native * 640 / W, P50_PROP) * det_recall(p_native, P50_DET))
SCHEMES['两级级联(ROI 引导 L1)'] = dict(lat=5.0, pxin=p_native,
                                        recall=det_recall(p_native / 2, P50_PROP) * det_recall(p_native, P50_DET))
SCHEMES['SAHI 切片 s=640 r=0.2'] = dict(lat=ms_slice, pxin=p_native,
                                        recall=det_recall(p_native, P50_DET))

N_FRAMES = 5
print(f"\\n{'方案':<24s} {'进网络px':>9s} {'单帧召回':>9s} {'5帧累积':>9s} {'延迟ms':>8s} {'预算内':>7s}")
for name, v in SCHEMES.items():
    v['seq'] = 1 - (1 - v['recall']) ** N_FRAMES
    print(f'{name:<24s} {v["pxin"]:>9.2f} {v["recall"]:>9.3f} {v["seq"]:>9.4f} '
          f'{v["lat"]:>8.1f} {"✅" if v["lat"] <= TSR_BUDGET_MS else "❌":>7s}')

assert SCHEMES['全图下采样 640×384']['recall'] < 0.06
assert SCHEMES['两级级联(ROI 引导 L1)']['seq'] > 0.99
assert SCHEMES['SAHI 切片 s=640 r=0.2']['seq'] > SCHEMES['两级级联(ROI 引导 L1)']['seq']
print('\\n✅ 单帧召回 0.76 vs 0.91 的差距，5 帧累积后变成 0.9993 vs 0.99999 —— **几乎抹平**')
print('   而 5.0 ms vs 40.0 ms 的延迟差距，**是抹不平的**  ->  量产选级联')"""),
    code("""# ---- 时序累积曲线：多少帧才够 ----
names = list(SCHEMES)
print(f"{'帧数':>5s}" + ''.join(f'{n[:22]:>24s}' for n in names))
for nf in [1, 2, 3, 5, 8, 12]:
    row = f'{nf:>5d}'
    for n in names:
        row += f'{1-(1-SCHEMES[n]["recall"])**nf:>24.4f}'
    print(row)

M_PER_FRAME = 100 / 3.6 / 30      # 100 km/h，30 FPS
print(f'\\n自车 100 km/h、30 FPS -> 每帧前进 {M_PER_FRAME:.2f} m')
need = {}
for n in names:
    k = 1
    while 1 - (1 - SCHEMES[n]['recall']) ** k < 0.95 and k < 999:
        k += 1
    need[n] = k
    print(f'  {n:<24s} 达到 95% 累积召回需 {k:>3d} 帧 = {k*M_PER_FRAME:>6.1f} m 的接近距离')
assert need['全图下采样 640×384'] > 10 * need['两级级联(ROI 引导 L1)']
print('\\n⚠️  独立性假设是**乐观的**：遮挡、逆光、运动模糊会让相邻帧的失败强相关，实际需要更多帧。')
print('    正确的做法是在真实序列上直接测「首次检出距离」的分布，而不是用单帧召回外推。')"""),
    md("""## ✏️ 练习 1：重叠率下界与切片规划

实现 `min_overlap_ratio(d_max, s)`：返回保证「任意位置、尺寸 ≤ d_max 的目标都能被某一片
**完整包含**」的最小重叠率。再实现 `plan_slices(W, H, s, d_max)`，返回
`{'overlap_ratio', 'stride', 'overlap_px', 'n_slices', 'magnification'}`
（`stride` 用 `int(round(s*(1-r)))`，`magnification = W/s`）。"""),
    code("""def min_overlap_ratio(d_max, s):
    # TODO: 由 s·r >= d_max 推出
    raise NotImplementedError

def plan_slices(W, H, s, d_max):
    # TODO: 取下界重叠率，算出 stride / overlap_px / 片数 / 放大倍数
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
assert abs(min_overlap_ratio(64, 640) - 0.10) < 1e-12
assert abs(min_overlap_ratio(96, 480) - 0.20) < 1e-12
assert min_overlap_ratio(700, 640) > 1.0, 'd_max > s 时无解（几何上不可能）'

p = plan_slices(1920, 1080, 640, 64)
print(p)
assert p['stride'] == 576 and p['overlap_px'] == 64 and p['n_slices'] == 8
assert abs(p['magnification'] - 3.0) < 1e-9
assert uncovered_positions(1920, 640, p['overlap_ratio'], 64)[0] == []

print(f"\\n{'d_max':>7s} {'r 下界':>8s} {'stride':>7s} {'N':>4s} {'放大':>6s} {'零失败?':>8s}")
for dm in [32, 64, 96, 128]:
    pp = plan_slices(1920, 1080, 640, dm)
    bad = uncovered_positions(1920, 640, pp['overlap_ratio'], dm)[0]
    print(f'{dm:>7d} {pp["overlap_ratio"]:>8.4f} {pp["stride"]:>7d} {pp["n_slices"]:>4d} '
          f'{pp["magnification"]:>5.1f}× {"✅" if not bad else "❌":>8s}')
    assert bad == []
print('\\n✅ 练习 1 通过：**overlap_px >= d_max** 是切片推理唯一必须记住的不等式')"""),
    md("""## ✏️ 练习 2：完整的跨片合并流水线

实现 `merge_slice_detections(per_slice_dets, slices, s, ios_thr=0.5, iou_thr=0.6, margin=2.0)`：

1. **坐标还原**：局部框 + 切片原点 → 全图坐标；同时用 `is_boundary` 打**贴边标记**
2. **只对贴边框**做 `nmm`（IoS 合并），缝合被截断的碎片；未被合并的（`members` 只有 1 个）
   打上 `truncated=True`
3. 把「合并后的贴边框」与「非贴边框」放在一起做一次 `nms`（IoU 去重）
4. 返回 `[{'box':…, 'score':…, 'truncated':…}, …]`，按分数降序"""),
    code("""def merge_slice_detections(per_slice_dets, slices, s, ios_thr=0.5, iou_thr=0.6, margin=2.0):
    # TODO: 还原坐标 -> 贴边分流 -> NMM 缝合 -> NMS 去重
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
# ① 低于下界产生的两个半截框，应当被缝合成一个精确的框
out_frag = merge_slice_detections(lenient, sl_bad, 640)
print('碎片场景 ->', [(tuple(round(t,1) for t in o['box']), round(o['score'],3), o['truncated'])
                      for o in out_frag])
assert len(out_frag) == 1
assert iou(out_frag[0]['box'], TGT) > 0.999
assert out_frag[0]['truncated'] is False, '被成功缝合的框不应再标记为截断'

# ② 满足下界的完整场景：12 个目标 -> 12 个框，且一一对应
out_full = merge_slice_detections(per_slice, slices, 640)
print(f'\\n完整场景: 还原前 {sum(len(d) for d in per_slice)} 个框  ->  合并后 {len(out_full)} 个框'
      f'（真值 {len(GT)} 个）')
assert len(out_full) == len(GT)
matched = set()
for o in out_full:
    best = int(np.argmax([iou(o['box'], tuple(g)) for g in GT]))
    assert iou(o['box'], tuple(GT[best])) > 0.99, o
    matched.add(best)
assert matched == set(range(len(GT))), '每个真值目标应当恰好对应一个输出框'
print('✅ 练习 2 通过：**贴边门控 + IoS-NMM + IoU-NMS** 是跨片合并的标准三件套')"""),
    md("""## ✏️ 练习 3：延迟预算下的切片配置规划

实现 `slice_latency_ms(W, H, s, r, ms_per_mpx=MS_PER_MPX)` 与
`plan_under_budget(W, H, d_max, budget_ms, s_candidates, ms_per_mpx=MS_PER_MPX)`：

对每个候选切片边长 s（跳过 `d_max >= s` 的），取**下界重叠率** `r = d_max/s`，算出延迟；
在预算内返回**放大倍数最高（即 s 最小）**的那个配置 dict
（含 `'s' / 'r' / 'n_slices' / 'latency_ms' / 'magnification'`）；都不可行返回 `None`。"""),
    code("""def slice_latency_ms(W, H, s, r, ms_per_mpx=MS_PER_MPX):
    # TODO
    raise NotImplementedError

def plan_under_budget(W, H, d_max, budget_ms, s_candidates, ms_per_mpx=MS_PER_MPX):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
CAND = [320, 448, 640, 896]
print(f"{'s':>6s} {'r 下界':>8s} {'N':>4s} {'延迟(ms)':>10s} {'放大':>6s}")
for s_c in CAND:
    r_c = 64 / s_c
    print(f'{s_c:>6d} {r_c:>8.4f} {tile_stats(1920,1080,s_c,r_c)[0]:>4d} '
          f'{slice_latency_ms(1920,1080,s_c,r_c):>10.2f} {1920/s_c:>5.1f}×')

assert abs(slice_latency_ms(1920, 1080, 640, 0.2) - 40.0) < 1e-6

r45 = plan_under_budget(1920, 1080, 64, 45.0, CAND)
assert r45 is not None and r45['s'] == 320, r45
assert abs(r45['magnification'] - 6.0) < 1e-9

r38 = plan_under_budget(1920, 1080, 64, 38.0, CAND)
assert r38 is not None and r38['s'] == 448, r38

assert plan_under_budget(1920, 1080, 64, 20.0, CAND) is None, '20 ms 预算下没有可行切片配置'
print(f'\\n预算 45 ms -> {r45}')
print(f'预算 38 ms -> {r38}')
print('预算 20 ms -> None（**这正是车端的真实处境**）')
print('\\n✅ 练习 3 通过：注意 s=896 反而更贵 —— 渐近律在 s 与 H 同量级时失效（贴边补片的冗余）')"""),
    md("""## ✏️ 练习 4：给定延迟预算的方案决策器

实现 `choose_strategy(budget_ms, schemes, n_frames=5, seq_target=0.95)`，返回 `(方案名, 方案dict)`：

1. 只考虑 `lat <= budget_ms` 的方案；一个都没有 → 返回 `(None, None)`
2. 其中 `n_frames` 帧**累积召回** `1-(1-recall)^n_frames >= seq_target` 的，取**延迟最小**的
3. 若没有达标的，取预算内**累积召回最高**的（保底方案）

返回的 dict 里要额外带上 `'seq'` 字段。"""),
    code("""def choose_strategy(budget_ms, schemes, n_frames=5, seq_target=0.95):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
for b in [2.0, 4.0, 8.0, 100.0]:
    name, info = choose_strategy(b, SCHEMES)
    if name is None:
        print(f'预算 {b:>6.1f} ms  ->  ❌ 无可行方案')
    else:
        print(f'预算 {b:>6.1f} ms  ->  {name:<24s} (延迟 {info["lat"]:.1f} ms, 5帧累积 {info["seq"]:.4f})')

assert choose_strategy(2.0, SCHEMES)[0] is None
assert choose_strategy(4.0, SCHEMES)[0] == '全图下采样 640×384', '预算太紧时只能退到保底方案'
assert choose_strategy(8.0, SCHEMES)[0] == '两级级联(ROI 引导 L1)'
assert choose_strategy(100.0, SCHEMES)[0] == '两级级联(ROI 引导 L1)', \\
    '即使预算无限，达标方案里也该选**最省**的那个，而不是召回最高的'
print('\\n✅ 练习 4 通过：**达标之后就不要再花钱买召回** ——')
print('   把省下的 35 ms 给别的感知任务，比把 TSR 单帧召回从 0.76 推到 0.91 有价值得多')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def min_overlap_ratio(d_max, s):
    return d_max / s                      # 由 s·r >= d_max 直接得到

def plan_slices(W, H, s, d_max):
    r = min_overlap_ratio(d_max, s)
    stride = max(1, int(round(s * (1.0 - r))))
    n = len(slice_origins(W, s, stride)) * len(slice_origins(H, s, stride))
    return {'overlap_ratio': r, 'stride': stride, 'overlap_px': s - stride,
            'n_slices': n, 'magnification': W / s}"""),
    code("""# 练习 2 参考答案
def merge_slice_detections(per_slice_dets, slices, s, ios_thr=0.5, iou_thr=0.6, margin=2.0):
    edge, inner = [], []
    for (x0, y0, _, _), ds in zip(slices, per_slice_dets):
        for d in ds:
            bx0, by0, bx1, by1 = d['box_local']
            rec = {'box': (bx0 + x0, by0 + y0, bx1 + x0, by1 + y0), 'score': float(d['score'])}
            (edge if is_boundary(d['box_local'], s, margin) else inner).append(rec)

    cand = [{'box': r['box'], 'score': r['score'], 'truncated': False} for r in inner]
    if edge:                                        # ① 只对贴边框做 IoS 合并
        for m in nmm([e['box'] for e in edge], [e['score'] for e in edge], ios_thr):
            cand.append({'box': m['box'], 'score': m['score'],
                         'truncated': len(m['members']) == 1})   # 配不上对 -> 保留但打标记
    if not cand:
        return []
    keep = nms([c['box'] for c in cand], [c['score'] for c in cand], iou_thr)  # ② 常规 NMS 去重
    return sorted([cand[i] for i in keep], key=lambda c: -c['score'])"""),
    code("""# 练习 3 参考答案
def slice_latency_ms(W, H, s, r, ms_per_mpx=MS_PER_MPX):
    return tile_stats(W, H, s, r)[1] * ms_per_mpx / 1e6

def plan_under_budget(W, H, d_max, budget_ms, s_candidates, ms_per_mpx=MS_PER_MPX):
    for s in sorted(s_candidates):                  # s 从小到大 = 放大倍数从高到低
        if d_max >= s:
            continue                                # 目标比切片还大，几何上无解
        r = min_overlap_ratio(d_max, s)
        ms = slice_latency_ms(W, H, s, r, ms_per_mpx)
        if ms <= budget_ms:
            return {'s': s, 'r': r, 'n_slices': tile_stats(W, H, s, r)[0],
                    'latency_ms': ms, 'magnification': W / s}
    return None"""),
    code("""# 练习 4 参考答案
def choose_strategy(budget_ms, schemes, n_frames=5, seq_target=0.95):
    aff = {k: v for k, v in schemes.items() if v['lat'] <= budget_ms}
    if not aff:
        return None, None
    seq = {k: 1 - (1 - v['recall']) ** n_frames for k, v in aff.items()}
    ok = [k for k in aff if seq[k] >= seq_target]
    key = min(ok, key=lambda k: aff[k]['lat']) if ok else max(aff, key=lambda k: seq[k])
    return key, dict(aff[key], seq=seq[key])"""),
    md("""---
## 🧪 真实工程胶囊：一份可直接用的切片/级联配置与检查清单"""),
    code("""RECIPE = r'''
# ============ ① 决定要不要切片：先算「目标进网络时还剩几个像素」 ============
f_px      = (W_img / 2) / tan(radians(HFOV) / 2)       # 60°/1920 -> 1662.77
p_native  = f_px * S_object / Z_target                 # 0.6 m 标志 @ 60 m -> 16.63 px
p_input   = p_native * (L_net / L_crop)                # 全图 letterbox 640 -> 5.54 px
#   p_input >= 32 px  -> 别切，没收益
#   p_input <  12 px  -> 切片/级联能带来两位数 AP_small 提升

# ============ ② SAHI 切片参数（离线/云端评测、自动标注用） ============
from sahi.predict import get_sliced_prediction
d_max = np.percentile(gt_sizes, 99)                    # **用 p99 而不是均值**
result = get_sliced_prediction(
    image, detection_model,
    slice_height=640, slice_width=640,                 # = 训练输入尺寸，不要乱改
    overlap_height_ratio=max(0.2, d_max / 640),        # **下界 r >= d_max/s，再往上推到片数跳变前**
    overlap_width_ratio =max(0.2, d_max / 640),
    postprocess_type="NMM",                            # **不是 NMS**：跨片碎片要合并不是抑制
    postprocess_match_metric="IOS",                    # **不是 IOU**：要度量「包含」而非「相似」
    postprocess_match_threshold=0.5,
    perform_standard_pred=True,                        # 额外跑一遍全图：接住大目标 + 补上下文
)
# 别忘了另一半：slicing aided **fine-tuning** —— 训练集也按同样 (s, r) 切，
# 与整图按 ~1:1 混合训练，否则尺度分布错位，收益会大打折扣。

# ============ ③ 车端：两级级联（量产的现实选择） ============
LEVEL1 = dict(input=(384, 640), class_agnostic=True, score_thr=0.05, topk=6)  # 高召回，精度不重要
LEVEL2 = dict(crop=256, source="**原生分辨率**", pad_ratio=0.35, score_thr=0.40)
#  纪律 A：Level 2 的训练 crop 必须由 **Level 1 的真实提议** 裁出（带定位噪声），不能用 GT 裁
#  纪律 B：ROI 先验（消失点/车道/地图）只能是**软的** —— 必须保留一路全图下采样兜底
#  纪律 C：ROI 的垂直位置用**实时估计的地平线**，不要用标定常数（上下坡会整段漏检）

# ============ ④ 上线前必查（切片/级联特有，常规检查之外） ============
CHECKS = [
  "重叠像素 s*r >= d_max(p99)？",
  "跨片合并用的是 IoS-NMM 而不是 IoU-NMS？贴边门控开了吗？",
  "letterbox 逆变换与切片原点的顺序对吗？（框整体偏移的头号原因）",
  "**按位置分桶评测**：切片边界附近 20 px 带内的召回 vs 中心区域，差多少？",
  "延迟的 p99 而不是均值；长时间跑之后有没有因为降频而漂移？",
  "Level 2 的训练分布 = Level 1 的推理输出分布吗？",
]
'''
print(RECIPE)
for k in ['p_input', 'd_max / 640', 'NMM', 'IOS', 'perform_standard_pred',
          'fine-tuning', 'class_agnostic', '真实提议', '地平线']:
    assert k in RECIPE, k
print('✅ 配方覆盖：切不切的判据 / 重叠下界 / NMM+IoS / 切片微调 / 两级级联三条纪律 / 上线检查')"""),
    md("""### 小结

- **切片没有创造信息，只是拒绝丢弃信息**。判断值不值得切，先算
  `p_input = p_native × L_net/L_crop`：还剩 32 px 就别切，只剩 5 px 才有大收益。
- **重叠率下界 `s·r ≥ d_max`**（等价 `r ≥ d_max/s`）。推导只有三行，
  面试要能当场写出来。用 **p99 而不是均值**定 d_max，否则失败会集中在几条固定竖线上。
- 片数是 r 的**阶梯函数** —— 把 r 从下界推到片数跳变前，是**免费的鲁棒性**。
- **跨片合并要用 NMM + IoS，而不是 NMS + IoU**：IoU 度量「两框有多像」，
  IoS 度量「小框有多大比例被包住」。并且必须加**贴边门控**，
  否则上下叠放的限速牌+辅助牌会被并成一个大框。
- **代价的渐近律 `N·s² ≈ W·H/(1-r)²`**：总算力几乎与切片大小无关，只由重叠率决定。
  s 决定的是**放大倍数**而不是成本。
- **切片在车端量产系统里基本不可用**（40 ms vs 8 ms 预算）。
  能说清这一点并给出替代方案，比会背 SAHI 高一个层次。
- **两级级联是现实选择**：召回是乘法 `R1×R2`，所以 Level 1 必须类别无关 + 低阈值 + 极度偏召回。
  单帧召回 0.76 vs 切片 0.91，**5 帧累积后变成 0.9993 vs 0.99999，差距被时序抹平；
  而 8 倍的延迟差抹不平。**
- 三条路径共享同一条纪律：**推理时输入被什么变换裁剪/缩放过，训练时就必须复现那个变换**
  （切片 → SF 微调；级联 → 用真实提议裁 crop；ROI → 把 ROI 分布放进训练集）。

下一站：**模块 05 · TSR 小目标实战** —— 从针孔模型 `px = f·S/Z` 出发，
把「要在多远检出」反推成「需要什么分辨率、什么 stride、什么相机」。"""),
]

