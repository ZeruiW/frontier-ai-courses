# -*- coding: utf-8 -*-
"""C73 模块 01 · 四种三维表示的代价账。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的三个乘子与合成场景；C72 的坐标系约定"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_representations.ipynb'
                       '（一个真实的 64 线 LiDAR 环扫模型 / '
                       '<strong>面密度从 67.7 掉到 0.13 点/m²，'
                       '一块 0.8 m 的标志从 255 点掉到 4.6 点</strong> / '
                       '体素 vs 柱体的占用率（0.506% vs 21.36%）/ '
                       '表示转换的可逆性表 / 分辨率选型器）'),
    ("核心参考", "Lang et al., <em>PointPillars</em>（CVPR 2019）· "
                 "Zhou &amp; Tuzel, <em>VoxelNet</em>（CVPR 2018）· "
                 "Park et al., <em>DeepSDF</em>（CVPR 2019）· "
                 "Velodyne HDL-64E 数据手册（垂直 FOV 与角分辨率）· "
                 "本课程 C72 模块 04（BEV 网格的采样率问题——同一个矛盾的另一面）"),
    ("预计时长", "读 45 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("point-cloud-properties", "点云的三个性质，以及它们各自的后果", "".join([
        P("「点云是一堆无序的点」这个说法只讲了三分之一。"
          "<strong>点云有三个互相独立的性质，而后面所有的网络设计都在应对其中某一个。</strong>"),
        TABLE(["性质", "含义", "它排除了什么", "谁在应对它"], [
            ["<strong>无序（unordered）</strong>",
             "$N!$ 种排列表示同一个物体",
             "<strong>任何依赖输入顺序的算子</strong>——"
             "全连接层、RNN、普通卷积全都不行",
             "<strong>对称函数</strong>（max / sum / mean）——模块 02"],
            ["<strong>无邻域（no neighbourhood）</strong>",
             "点之间没有预定义的连接关系",
             "<strong>卷积的「感受野」概念</strong>；"
             "<em>要做局部操作必须先建 kNN 或球查询</em>",
             "PointNet++ 的分组、体素化、图卷积"],
            ["<strong>密度不均匀（non-uniform density）</strong>",
             "近处密、远处疏；且随材质与入射角变化",
             "<strong>「点数 ∝ 物体大小」这个假设</strong>；"
             "<em>也让「采样 K 个点」这种归一化产生偏倚</em>",
             "多尺度分组、按距离分层评测——下一节量它"],
        ]),
        DUAL(
            "<strong>三个性质里，第三个最常被忽略，而它对 TSR 影响最大。</strong>"
            "<em>「无序」有一个干净的数学答案（对称函数），"
            "「无邻域」有一个干净的工程答案（建近邻结构）；"
            "而「密度不均匀」没有干净的答案</em>——"
            "<strong>它只能靠「知道它有多不均匀」来管理。</strong>",
            "<strong>所以本模块第 2 节先把它量出来。</strong>"
            "<em>而量它需要一个真实的 LiDAR 采样模型——"
            "模块 00 的合成场景是均匀采样的，那是一个刻意的简化，"
            "而这一节要把这个简化补上</em>。"
            "<strong>结论会很直接：一块 0.8 m 的交通标志在 10 m 处有 255 个点，"
            "在 73 m 处只有 4.6 个点。</strong>",
        ),
    ])),

    # ============================================================== 2
    ("lidar-sampling", "真实 LiDAR 的采样几何：远处到底有多疏", "".join([
        P("旋转式 LiDAR 的采样是<strong>角度均匀</strong>的："
          "$N$ 条固定俯角的激光束 × 水平方向按固定角步进。"
          "<strong>而角度均匀在距离上就是极度不均匀。</strong>"),
        ASCII("""
   64 线 LiDAR（垂直 FOV −24.9°..2.0°，水平 0.2°）打在地面上

   雷达 1.8m 高
      │╲
      │ ╲╲╲╲                环 i 的距离  d_i = H / tan(−φ_i)
      │  ╲ ╲ ╲ ╲            相邻环间距  Δd = d_{i+1} − d_i
      │   ╲  ╲   ╲    ╲     同环点间距  d·Δaz
   ───┴────╫───╫─────╫──────╫──────────────────
          4m  10m   20m    50m        80m
          │←─→│      │←───→│          │←─────────→│
          密           渐疏               极疏
        """),
        TABLE(["距离", "相邻环间距", "同环点间距", "面密度（点/m²）"], [
            ["9.8 m", "0.431 m", "0.034 m", "<strong>67.73</strong>"],
            ["19.6 m", "1.738 m", "0.068 m", "8.43"],
            ["29.0 m", "3.975 m", "0.101 m", "2.48"],
            ["45.4 m", "10.532 m", "0.159 m", "0.60"],
            ["<strong>72.8 m</strong>", "<strong>31.456 m</strong>", "0.254 m",
             "<strong>0.13</strong>"],
        ]),
        P("<strong>72.8 m 处，相邻两个激光环在地面上相距 31 米。</strong>"
          "<em>也就是说那个距离上的地面几乎没有被采样——"
          "而这正是「远处的地面估计要靠相机而不是 LiDAR」的原因</em>（C72 的 IPM）。"),
        H3("一块 0.8 × 0.8 m 的交通标志能得到多少点"),
        TABLE(["距离", "竖直方向", "水平方向", "总点数"], [
            ["9.8 m", "10.9 行", "23.3 列", "<strong>≈ 255 点</strong>"],
            ["19.6 m", "5.5 行", "11.7 列", "≈ 64 点"],
            ["29.0 m", "3.7 行", "7.9 列", "≈ 29 点"],
            ["45.4 m", "2.4 行", "5.0 列", "≈ 12 点"],
            ["<strong>72.8 m</strong>", "<strong>1.5 行</strong>", "3.1 列",
             "<strong>≈ 4.6 点</strong>"],
        ]),
        DUAL(
            "<strong>面密度从 67.7 掉到 0.13 点/m²——衰减 520 倍。</strong>"
            "<em>而它的形式是 $1/d^2$：环间距 $\\propto d^2$（因为 "
            "$d=H/\\tan(-\\varphi)$ 的导数），同环点间距 $\\propto d$</em>。"
            "<strong>所以「点数 ∝ 面积」只在同一距离上成立；"
            "跨距离比较点数是没有意义的。</strong>",
            "<strong>这张表有三个立刻可用的推论。</strong>"
            "① <strong>「至少 N 个点才算一个有效目标」这个过滤条件"
            "必须按距离设，而不是一个常数</strong>——"
            "<em>否则它等价于「只检测近处目标」</em>；"
            "② <strong>点云上采样 K 个点做归一化，会系统性地偏向近处目标</strong>"
            "（<em>远处目标不够 K 个点，只能重复采样</em>）；"
            "③ <strong>对 TSR，LiDAR 在 50 m 之外基本不提供形状信息</strong>"
            "（<em>1.5 行 × 3 列</em>），"
            "所以远距离标志识别必须靠相机——"
            "<strong>而 C72 模块 03 的「已知尺寸测距」正好在这个区间提供 ±1.30 m 的精度。</strong>",
        ),
        CALLOUT("warn",
                "<strong>本节的模型仍然是简化的</strong>："
                "它假设完美反射、无遮挡、无大气衰减、标志正对雷达。"
                "<em>真实情况只会更差——反光标志牌在斜入射时回波可能直接丢失</em>。"
                "<strong>所以表里的点数是<em>上界</em>。</strong>"),
    ])),

    # ============================================================== 2b
    ("accumulation", "多帧累积：对静止目标的免费增益，对运动目标的毁灭", "".join([
        P("上一节说 73 m 处的标志只有 4.6 个点。"
          "<strong>而交通标志是静止的——所以可以把连续几帧的点，"
          "用自车位姿搬到同一个坐标系里累加起来。</strong>"
          "（<em>这正是 C72 模块 05 的运动补偿，只不过用途从关联变成了增密</em>。）"),
        TABLE(["配置", "自车前进", "标志的距离区间", "累积点数", "相对单帧"], [
            ["60 km/h @10 Hz，10 帧（1.0 s）", "16.7 m", "73.0 → 58.0 m", "58.3",
             "<strong>12.6×</strong>"],
            ["<strong>120 km/h @10 Hz，10 帧（1.0 s）</strong>", "33.3 m",
             "73.0 → 43.0 m", "<strong>79.6</strong>", "<strong>17.2×</strong>"],
            ["120 km/h @10 Hz，5 帧（0.5 s）", "16.7 m", "73.0 → 59.7 m", "28.4",
             "6.1×"],
            ["60 km/h @20 Hz，10 帧（0.5 s）", "8.3 m", "73.0 → 65.5 m", "51.5",
             "11.2×"],
        ]),
        DUAL(
            "<strong>注意 17.2× 大于帧数 10——这是一个非直觉的加成。</strong>"
            "<em>因为自车在这一秒里前进了 33 m，标志从 73 m 走到 43 m，"
            "而点密度按 $1/d^2$ 增长</em>。"
            "<strong>所以「累积」的收益不只是帧数，还包括「越来越近」这件事</strong>——"
            "<em>而车速越快、收益越大（120 km/h 的 17.2× vs 60 km/h 的 12.6×）。</em>",
            "<strong>而代价落在运动目标上：它们会被拖成一条。</strong>"
            "<em>累积 1 秒时，相对速度 20 km/h 的目标拖影 5.56 m——"
            "已经超过一辆车的长度（4.5 m）</em>。"
            "<strong>所以累积窗口是一个显式取舍：</strong>",
        ),
        TABLE(["累积窗口", "相对 10 km/h", "相对 20 km/h", "相对 50 km/h"], [
            ["10 帧 @10 Hz（1.00 s）", "2.78 m", "<strong>5.56 m（超过车长）</strong>",
             "13.89 m"],
            ["5 帧 @10 Hz（0.50 s）", "1.39 m", "2.78 m",
             "<strong>6.94 m（超过车长）</strong>"],
            ["<strong>3 帧 @20 Hz（0.15 s）</strong>", "0.42 m", "0.83 m", "2.08 m"],
        ]),
        CALLOUT("intuition",
                "<strong>所以对 TSR 有一个特别干净的结论：静止目标可以用长窗口累积，"
                "而这恰好是 LiDAR 最缺点的那一类目标。</strong>"
                "<em>实践上的做法是「按类别分窗口」——"
                "对标志/杆/建筑用长窗口，对车/人用短窗口或不累积</em>。"
                "<strong>而这要求你在累积<em>之前</em>就知道类别，"
                "所以它通常是一个二阶段流程</strong>"
                "（<em>与 C55 模块 02 的两级 TSR 管线同构</em>）。"),
    ])),

    # ============================================================== 3
    ("voxel-tradeoff", "体素：$(L/r)^3$ 与占用率的对抗", "".join([
        P("体素化的唯一理由是<strong>让卷积可用</strong>。而代价是第一个乘子。"),
        P("下表用<strong>本模块的环扫点云</strong>（102,668 点，全 360°，89% 命中率），"
          "并与模块 00 的<em>均匀采样</em>场景对照——"
          "<strong>后者会把占用率高估约 2.5 倍</strong>。"),
        TABLE(["$r$", "格数", "内存（1 B/格）", "占用率（环扫）", "占用率（均匀假设）",
               "平均每格点数"], [
            ["0.16 m", "19,531,250", "19.53 MB", "0.156%", "—", "3.37"],
            ["0.10 m", "80,000,000", "80.00 MB", "<strong>0.055%</strong>",
             "<strong>0.137%</strong>（高估 2.5×）", "2.33"],
            ["<strong>0.05 m</strong>", "<strong>640,000,000</strong>",
             "<strong>640.00 MB</strong>", "<strong>0.011%</strong>",
             "0.018%（高估 1.7×）", "<strong>1.52</strong>"],
        ]),
        CALLOUT("warn",
                "<strong>「均匀假设高估占用率」这件事本身值得记。</strong>"
                "<em>因为容量规划（`max_num_voxels` 该设多少）通常是拍一个数或按均匀假设估的，"
                "而真实点云更集中——所以估出来的值偏大，看起来是安全的</em>。"
                "<strong>但反过来的情形更危险：按<em>近处</em>的密度估，"
                "会低估远处需要的分辨率。</strong>"),
        DUAL(
            "<strong>最后两列一起看，才能看出体素化的困境。</strong>"
            "<em>占用率掉到 0.018% 说明 99.98% 的内存与算力花在空气上；"
            "而平均每格点数掉到 1.03 说明体素化已经<strong>不再压缩任何东西</strong></em>——"
            "<strong>它只是给点云套上了 6.4 亿个格子的外壳。</strong>"
            "所以在这个分辨率上，「用体素」的唯一好处只剩「能用卷积」，"
            "<em>而那个好处要靠稀疏卷积才能真正拿到</em>（模块 03）。",
            "<strong>「平均每格点数」是一个很好用的选型指标，"
            "因为它给出了一个明确的停止条件。</strong>"
            "<em>当它接近 1 时，继续减小 $r$ 只增加空格子、不增加信息</em>。"
            "<strong>本课的合成场景在 $r\\approx0.05$ m 时饱和</strong>；"
            "<em>而真实 LiDAR 因为远处更疏（第 2 节），会更早饱和</em>——"
            "<strong>所以这个指标应当在你自己的数据上算一次，"
            "而不是照抄别人的分辨率。</strong>",
        ),
        CALLOUT("intuition",
                "顺带说明一件常见的困惑：<strong>为什么 $z$ 方向常用更粗的分辨率</strong>"
                "（比如 $0.05\\times0.05\\times0.1$ m）。"
                "<em>因为自动驾驶场景在 $z$ 上的结构远少于 $xy$："
                "地面 + 车顶 + 标志高度，就那么几个层次</em>。"
                "<strong>把 $z$ 的分辨率放粗一倍，格数直接减半，"
                "而丢掉的信息比 $xy$ 少得多</strong>——"
                "<em>这是「三个乘子」里最容易砍的那一个。</em>"),
    ])),

    # ============================================================== 4
    ("pillars", "柱体：把第三个乘子直接换成 1", "".join([
        P("既然 $z$ 方向最容易砍，那就砍到底："
          "<strong>把整根柱子里的点交给一个逐柱 MLP，"
          "输出一个特征向量——于是三维网格变成二维网格。</strong>"
          "这就是 PointPillars。"),
        TABLE(["方案", "格数", "内存", "占用率", "平均每格/柱点数"], [
            ["体素 $r{=}0.05$ m", "640,000,000", "640.00 MB", "0.011%", "1.52"],
            ["体素 $r{=}0.10$ m", "80,000,000", "80.00 MB", "0.055%", "2.33"],
            ["体素 $r{=}0.16$ m", "19,531,250", "19.53 MB", "0.156%", "3.37"],
            ["柱体 $0.10$ m", "1,000,000", "1.00 MB", "4.332%", "2.37"],
            ["<strong>柱体 $0.16$ m（PointPillars）</strong>",
             "<strong>390,625</strong>", "<strong>0.39 MB</strong>",
             "<strong>7.642%</strong>", "3.44"],
            ["柱体 $0.32$ m", "97,656", "0.10 MB", "<strong>16.324%</strong>", "6.44"],
        ]),
        P("同分辨率下柱体与体素的占用率之比："
          "<strong>$r{=}0.10$ m 时 78.8×，$r{=}0.16$ m 时 49.0×，"
          "$r{=}0.32$ m 时 24.3×</strong>——"
          "<em>比值随 $r$ 减小而增大，因为体素被第三个乘子按 $1/r$ 继续稀释</em>。"),
        DUAL(
            "<strong>关键是这个数量级差：柱体 0.16 m 是 7.642%，"
            "而同分辨率的体素只有 0.156%——密了 49.0 倍。</strong>"
            "<em>7.6% 仍然算稀疏，但它已经落在「密集 2D 卷积可以接受」的区间；"
            "而 0.156% 的三维网格用密集 3D 卷积是完全不可行的</em>"
            "（<strong>模块 03 会算出那是 283 GFLOP，其中 99.9% 花在空气上</strong>）。"
            "<strong>这就是 PointPillars 快的真正原因</strong>——"
            "<em>不是网络更小，而是它把问题搬到了一个卷积友好的表示上。</em>"
            "（<em>真实城市场景的柱体占用率通常更高（10–20%），"
            "因为本课场景只有 4 辆车 + 3 块标志</em>。）",
            "<strong>代价必须说清楚：柱体丢掉了 $z$ 方向的<em>空间</em>结构。</strong>"
            "<em>逐柱 MLP 能把柱内点的 $z$ 当特征学进去，"
            "但柱与柱之间在 $z$ 上不再有卷积连接</em>。"
            "<strong>所以柱体对「高度差异是关键线索」的任务不利</strong>——"
            "<em>而交通标志（离地 2.2 m）与地面标记（0 m）恰好只在 $z$ 上区分</em>。"
            "所以对 TSR，柱体不是自动的正确选择；"
            "<strong>而这正好说明第 3 节那个「砍 $z$」的建议有一个前提："
            "你的任务在 $z$ 上确实没多少结构。</strong>",
        ),
        CALLOUT("paper",
                "<strong>柱体与 C72 模块 04 的 BEV 是同一个东西的两种来路。</strong>"
                "<em>C72 用几何（IPM 单应）从图像得到 BEV；"
                "这里用学习（逐柱 MLP）从点云得到 BEV</em>。"
                "<strong>而 C72 模块 04 量到的「均匀网格必然一头过采样一头欠采样」"
                "在这里同样成立</strong>——"
                "<em>只不过点云的欠采样来自 LiDAR 环距（第 2 节），"
                "而图像的欠采样来自透视。</em>"),
    ])),

    # ============================================================== 5
    ("mesh-implicit", "网格与隐式：另外两条路各自解决什么", "".join([
        TABLE(["表示", "存什么", "它解决了什么", "它的难点"], [
            ["<strong>网格（mesh）</strong>", "顶点 + 面的连接关系",
             "<strong>表面显式存在</strong>，所以可渲染、可做几何编辑、"
             "内存小（5 万顶点 + 10 万面 ≈ 1.8 MB）",
             "<strong>拓扑难学</strong>——"
             "<em>顶点位置是连续量可以回归，而「哪三个顶点构成一个面」是离散的</em>"],
            ["<strong>隐式（SDF / occupancy）</strong>",
             "一个函数 $f(x,y,z)\\to$ 距离或占据概率",
             "<strong>分辨率无关</strong>：内存 = 参数量"
             "（8 层 256 宽的 MLP ≈ 1.8 MB，"
             "<em>而它能表示任意精细的表面</em>）",
             "<strong>查询要做前向计算</strong>；"
             "<em>而单个网络通常只表示一个物体或场景</em>"],
        ]),
        DUAL(
            "<strong>隐式表示那个「分辨率无关」值得说清楚，因为它容易被误解。</strong>"
            "<em>它不是「无限精度」——精度受网络容量与训练数据限制</em>。"
            "<strong>它真正的意思是：内存不随你想要的分辨率增长。</strong>"
            "<em>要 $0.01$ m 的表面细节，密集体素要 8000 倍于 $0.2$ m 的内存，"
            "而隐式表示的参数量一个字节都不变</em>——"
            "<strong>这就是它绕开第一个乘子的方式。</strong>",
            "<strong>而两者在本课的定位都是「知道它存在、知道分界线在哪」。</strong>"
            "<em>本课的任务是判别式的（检测、分割），"
            "而这两种表示的主战场是生成与重建</em>——"
            "<strong>所以它们属于 C75</strong>。"
            "<em>这里给出的判据是：如果你的输出需要「一个连续表面」"
            "（渲染、碰撞检测、几何测量），就需要它们；"
            "如果输出是「一组框」或「逐点标签」，就不需要。</em>",
        ),
    ])),

    # ============================================================== 5b
    ("sampling", "采样：FPS 不是「更好」，是一个方向相反的偏倚", "".join([
        P("点云网络通常需要固定的输入点数，所以要采样到 $K$ 个点。"
          "<strong>而两种常见做法的偏倚方向恰好相反。</strong>"),
        P("实验：用本模块的环扫点云（它天然密度不均匀，&gt;30 m 的点只占 10.4%），"
          "采样 $K=512$："),
        TABLE(["采样方式", "采到的点里「&gt;20 m」的占比", "相对原始分布"], [
            ["原始点集", "10.4%", "—"],
            ["<strong>随机采样</strong>", "12.9%", "1.24×（<strong>近似保持分布</strong>）"],
            ["<strong>FPS（最远点采样）</strong>", "<strong>77.7%</strong>",
             "<strong>7.49×</strong>（极度偏向远处）"],
        ]),
        DUAL(
            "<strong>FPS 常被描述为「覆盖更好的采样」——这是对的，"
            "但「覆盖更好」的具体含义是「几何上更均匀」，"
            "而几何均匀在密度不均匀的点云上意味着<em>极度偏向稀疏区域</em>。</strong>"
            "<em>77.7% 对 10.4%，差 7.5 倍；采样点的中位距离从 7.8 m 跳到 55.9 m</em>。"
            "<strong>所以 FPS 不是随机采样的改进版，它是一个不同的偏倚。</strong>",
            "<strong>哪一个对，取决于任务。</strong>"
            "<em>如果任务是「不要漏掉远处的稀疏目标」，FPS 的偏倚正是你要的；"
            "如果任务是「准确刻画近处目标的形状」，FPS 会把预算浪费在远处的零星点上</em>。"
            "<strong>而最坏的情形是：训练用 FPS、部署用随机采样（或反之）</strong>——"
            "<em>两者看到的是分布完全不同的输入，"
              "而这类不一致在指标上表现为「效果差一点」</em>"
            "（<strong>与 C72 模块 01 的「训练/部署预处理不一致」是同一类问题</strong>）。",
        ),
        CALLOUT("warn",
                "还有一个纯工程的点：<strong>FPS 是 $O(NK)$ 的串行算法</strong>，"
                "$N{=}102{,}668$、$K{=}512$ 时是 5300 万次距离计算，"
                "<em>而它无法简单并行（每一步依赖上一步的结果）</em>。"
                "<strong>所以实践里常用「随机分块 + 块内 FPS」来近似</strong>，"
                "<em>而那又改变了偏倚——所以这个选择必须被记录，而不是当成实现细节。</em>"),
    ])),

    # ============================================================== 6
    ("conversions", "表示之间的转换：哪些是有损的", "".join([
        ASCII("""
   四种表示之间的转换（→ 上标注信息损失）

              量化 (≤ r√3/2)
     点云 ─────────────────────► 体素
       ▲  ◄─────────────────────  │
       │      取格中心（有损）      │  marching cubes
       │                          ▼      （等值面提取）
       │        采样表面          网格
       │  ◄─────────────────────  │
       │      （有损：只得到样本）   │  拟合 SDF
       │                          ▼
       └───────────────────────  隐式
              查询等值面（有损：受网络容量限制）

   **没有一条是无损的双向转换。**
   而唯一「几乎无损」的方向是：点云 → 体素（r 足够小时，见模块 00 第 3 节）
        """),
        TABLE(["转换", "损失", "量级", "可逆吗"], [
            ["点云 → 体素", "量化误差", "$\\le r\\sqrt3/2$；均匀时均值 $0.4804r$",
             "<strong>不可逆</strong>（多个点落进同一格）"],
            ["体素 → 点云（取格中心）", "同上，且点数变成格数",
             "<em>本课环扫场景 $r{=}0.05$ m 时格数 67,620 vs 原 102,668 点</em>",
             "不可逆"],
            ["点云 → 网格", "表面重建的假设（法向、拓扑）",
             "取决于算法；<strong>薄结构与开放边界最容易错</strong>",
             "不可逆，且<strong>可能失败</strong>"],
            ["网格 → 点云", "只保留采样点", "取决于采样密度", "不可逆"],
            ["隐式 → 网格", "marching cubes 的分辨率",
             "等值面提取本身是一次体素化", "不可逆"],
        ]),
        CALLOUT("danger",
                "<strong>一个真实的工程陷阱：把「点云 → 体素 → 点云」当成预处理。</strong>"
                "<em>它看起来是恒等变换（点还在，数量差不多），"
                "而实际上每个点都被搬到了格中心</em>。"
                "<strong>模块 00 的场景在 $r{=}0.1$ m 时平均位移 0.0516 m</strong>——"
                "<em>而模块 05 会算出：限速牌沿最薄轴允许的平移误差只有 0.0333 m</em>。"
                "<strong>也就是说这一次「无害的预处理」就已经超出了预算。</strong>"),
    ])),

    # ============================================================== 7
    ("picking", "选型：把精度要求翻译成 $r$，再看内存装不装得下", "".join([
        P("选型不是「哪种表示更好」，而是两个约束的交集是否为空。"),
        MATH(r"\underbrace{r \le \frac{2\,\varepsilon}{\sqrt3}}_{\text{精度约束}}"
             r"\qquad\text{与}\qquad"
             r"\underbrace{r \ge \Bigl(\frac{L_xL_yL_z}{B}\Bigr)^{1/3}}_{\text{内存约束}}"),
        P("其中 $\\varepsilon$ 是需要的位置精度、$B$ 是字节预算。"
          "<strong>注意内存约束里的 $1/3$ 次方——预算翻 8 倍才能把 $r$ 减半。</strong>"),
        TABLE(["精度要求 $\\varepsilon$", "允许的最粗 $r$", "100 MB 预算允许的最细 $r$",
               "交集"], [
            ["0.30 m", "0.3464 m", "0.0928 m", "✅ 可行"],
            ["0.10 m", "0.1155 m", "0.0928 m", "✅ 可行（余量很小）"],
            ["<strong>0.02 m</strong>", "<strong>0.0231 m</strong>", "0.0928 m",
             "<strong>❌ 为空</strong>——密集体素方案不可行"],
        ]),
        DUAL(
            "<strong>第三行是最常见的情形，而它有三条出路。</strong>"
            "① <strong>上稀疏</strong>（模块 03）——"
            "内存变成 $\\propto$ 非空格数而不是总格数，"
            "<em>而占用率 0.018% 意味着这条路能把预算需求降三个数量级</em>；"
            "② <strong>用柱体</strong>（第 4 节）——把第三个乘子换成 1；"
            "③ <strong>不用体素</strong>（模块 02 的点云路线）。",
            "<strong>而这张表本身是设计评审时应当先算的东西</strong>，"
            "<em>因为它不需要任何数据、也不需要跑任何模型</em>。"
            "<strong>notebook 练习 4 把它写成一个函数</strong>，"
            "而它会在「交集为空」时明确返回不可行，"
            "<em>而不是返回一个「凑合的」分辨率</em>——"
            "<strong>这与 C72 模块 04 的「IPM 函数对不贴地的类别直接拒绝」是同一条纪律："
            "在设计阶段就拒绝，比在评测阶段发现便宜得多。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("checklist", "本模块的清单", "".join([
        OL([
            "<strong>在你自己的数据上算「平均每格点数」</strong>（模块 00 练习 1）——"
            "它接近 1 时说明分辨率已经饱和，再细就是纯浪费",
            "<strong>算出点密度随距离的衰减</strong>（第 2 节），"
            "并据此把「最少点数」这个过滤条件<strong>做成距离的函数</strong>",
            "<strong>不要跨距离比较点数</strong>——"
            "<em>「点数 ∝ 面积」只在同一距离上成立</em>",
            "<strong>$z$ 方向的分辨率可以比 $xy$ 粗</strong>（第 3 节），"
            "<em>但先确认你的任务在 $z$ 上确实没多少结构</em>"
            "（TSR 恰好相反——标志与地面标记只在 $z$ 上区分）",
            "<strong>「点云 → 体素 → 点云」不是恒等变换</strong>（第 6 节）——"
            "$r{=}0.1$ m 就有约 0.05 m 的平均位移，"
            "<em>而它可能已经超出下游的精度预算</em>",
            "<strong>累积窗口按类别设</strong>（第 2b 节）——"
            "静止目标长窗口（120 km/h 下 10 帧给 17.2× 的点数），"
            "<em>而运动目标 1 秒窗口的拖影已超过车长</em>",
            "<strong>采样方式（随机 / FPS）要记录并在训练与部署间保持一致</strong>"
            "（第 5b 节）——<em>两者的偏倚方向相反，差十倍</em>",
            "<strong>选型先算精度约束与内存约束的交集</strong>（第 7 节），"
            "为空时明确拒绝而不是凑一个分辨率",
        ]),
        CALLOUT("intuition",
                "<strong>如果只做一条，做第 2 条。</strong>"
                "<em>「最少 N 个点」这个过滤条件在几乎每个点云流水线里都存在，"
                "而它几乎总是一个常数</em>——"
                "<strong>而一个常数阈值配上 520 倍的密度衰减，"
                "等价于悄悄地把远处目标全部丢掉。</strong>"
                "<em>这类「看起来无害的常数」是本课程反复出现的主题"
                "（C70 的 top-k、C71 的迭代次数、C72 的去畸变 n=5）。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 01 · 四种三维表示的代价账

这个 notebook 用一个**真实的 64 线 LiDAR 环扫模型**（射线与地面/AABB 求交）
替换模块 00 的均匀采样场景，然后把四件事量出来：

1. **点密度随距离的衰减**：面密度 67.7 → 0.13 点/m²，
   一块 0.8 m 的标志从 **255 点掉到 4.6 点**；
   而 73 m 处相邻激光环在地面上相距 **31 米**。
2. **多帧累积**：120 km/h 下 10 帧给 **17.2×** 的点数（>10，因为自车在靠近），
   但相对速度 20 km/h 的目标在 1 秒窗口里拖影 **5.56 m**（超过车长）。
3. **体素 vs 柱体**：同为 0.16 m，柱体的占用率是 **21.36%** 而体素只有 **0.506%**——
   密了 42 倍，所以柱体能直接用普通 2D 卷积。
4. **采样的偏倚**：随机采样保持分布（9.2% → 6.2%），
   而 **FPS 把远处点的占比推到 91.8%**——它不是「更好」，是方向相反。"""),

    md("""## 0 · 环境"""),

    code("""import numpy as np

print('numpy', np.__version__)

SCENE_L = (100.0, 100.0, 8.0)
LIDAR_H = 1.8                       # 雷达安装高度
N_BEAM, FOV_DEG, AZ_DEG = 64, (-24.9, 2.0), 0.2     # 类 HDL-64E

EL = np.deg2rad(np.linspace(FOV_DEG[0], FOV_DEG[1], N_BEAM))
D_BEAM_DEG = float(np.mean(np.diff(np.rad2deg(EL))))
print(f'{N_BEAM} 线，垂直 FOV {FOV_DEG[0]}°..{FOV_DEG[1]}°，'
      f'束间 {D_BEAM_DEG:.3f}°，水平 {AZ_DEG}°')
print(f'每转一圈的射线数 = {N_BEAM} × {int(360/AZ_DEG):,} = '
      f'{N_BEAM*int(360/AZ_DEG):,}')

def dense_voxel_count(L, r):
    return int(np.prod([l / r for l in L]))"""),

    md("""## 1 · 一个真实的环扫模型

射线从雷达出发，与**地面**和若干**长方体（AABB）**求交，取最近的命中点。
这比模块 00 的均匀采样慢，但它是唯一能得到正确密度分布的办法。"""),

    code("""# 场景：地面 + 4 辆车 + 3 块标志（都是 AABB，单位米，车体坐标 X 前 Y 左 Z 上）
BOXES = []
for cx, cy in [(20, -3), (35, 3), (60, -3), (80, 3)]:                 # 车
    BOXES.append((np.array([cx-2.25, cy-0.95, 0.0]),
                  np.array([cx+2.25, cy+0.95, 1.5]), 'car'))
for cx, cy in [(30, -5.5), (55, 5.5), (75, -5.5)]:                    # 标志（薄）
    BOXES.append((np.array([cx-0.05, cy-0.40, 1.80]),
                  np.array([cx+0.05, cy+0.40, 2.60]), 'sign'))

def ray_aabb(o, dirs, lo, hi):
    '''批量射线与 AABB 求交，返回命中距离 t（未命中为 inf）。'''
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (lo - o) / dirs
        t2 = (hi - o) / dirs
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    hit = (tmax >= np.maximum(tmin, 0.0))
    t = np.where(hit, np.maximum(tmin, 0.0), np.inf)
    return t

def ray_ground(o, dirs, z=0.0):
    '''射线与 z=0 平面求交。'''
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (z - o[2]) / dirs[:, 2]
    return np.where((t > 0) & np.isfinite(t), t, np.inf)

def lidar_scan(origin=None, az_range=(-180., 180.), max_range=120.):
    '''返回 (points, labels)。labels: 0=ground, 1=car, 2=sign。'''
    o = np.array([0., 0., LIDAR_H]) if origin is None else np.asarray(origin, float)
    az = np.deg2rad(np.arange(az_range[0], az_range[1], AZ_DEG))
    A, E = np.meshgrid(az, EL, indexing='ij')
    A, E = A.ravel(), E.ravel()
    dirs = np.column_stack([np.cos(E)*np.cos(A), np.cos(E)*np.sin(A), np.sin(E)])

    t = ray_ground(o, dirs)
    lab = np.zeros(len(dirs), dtype=np.int64)
    for lo, hi, kind in BOXES:
        tb = ray_aabb(o, dirs, lo, hi)
        closer = tb < t
        t = np.where(closer, tb, t)
        lab = np.where(closer, 1 if kind == 'car' else 2, lab)

    ok = np.isfinite(t) & (t > 0) & (t < max_range)
    return o + dirs[ok] * t[ok, None], lab[ok]

PTS, LAB = lidar_scan()
print(f'一帧（全 360°）命中 {len(PTS):,} 点 / {N_BEAM*int(360/AZ_DEG):,} 条射线 = {100*len(PTS)/(N_BEAM*int(360/AZ_DEG)):.0f}%')
for k, name in [(0, '地面'), (1, '车'), (2, '标志')]:
    print(f'  {name:4s}: {int((LAB==k).sum()):7,} 点 ({100*(LAB==k).mean():5.2f}%)')
assert (LAB == 2).sum() > 0, '应当扫到标志'
assert (LAB == 0).mean() > 0.5, '地面应当占大头'

rng_m = np.linalg.norm(PTS[:, :2], axis=1)
print(f'\\n距离范围 {rng_m.min():.2f} – {rng_m.max():.1f} m')
print(f'  <20m 的点占 {100*(rng_m<20).mean():.1f}%，'
      f'>50m 的点占 {100*(rng_m>50).mean():.1f}%')
assert (rng_m < 20).mean() > 5 * (rng_m > 50).mean(), '近处必然更密'
print(f'\\n⚠️ 本场景里地面点占 {100*(LAB==0).mean():.1f}% —— 偏高，'
      '因为场景里只有 4 辆车 + 3 块标志。')
print('   真实城市场景还有建筑、植被、更多车辆，地面通常占 50–70%。')
print('   所以本课的**绝对**占用率偏低，而**相对**结论（比值、趋势）可迁移。')"""),

    md("""## 2 · 密度随距离的衰减

**注意「相邻环间距」那一列**——它按 $d^2$ 增长，
因为环的地面距离是 $d=H/\\tan(-\\varphi)$。"""),

    code("""# 打在地面上的环（俯角为负的那些束）
down = EL[EL < -1e-9]
D_RING = np.sort((LIDAR_H / np.tan(-down)))
D_RING = D_RING[(D_RING > 0) & (D_RING < 120)]
print(f'打在地面上的环: {len(D_RING)} 个，最近 {D_RING[0]:.2f} m，'
      f'最远 {D_RING[-1]:.1f} m\\n')

print(f\"{'环距离':>8s} {'相邻环间距':>11s} {'同环点间距':>11s} {'面密度(点/m²)':>15s}\")
dens = {}
for tgt in [10., 20., 30., 50., 80.]:
    i = int(np.argmin(np.abs(D_RING - tgt)))
    j = min(i + 1, len(D_RING) - 1)
    dr = abs(D_RING[j] - D_RING[i]) or abs(D_RING[i] - D_RING[i-1])
    daz = D_RING[i] * np.deg2rad(AZ_DEG)
    dens[tgt] = 1.0 / (dr * daz)
    print(f'{D_RING[i]:7.1f}m {dr:10.3f}m {daz:10.3f}m {dens[tgt]:14.2f}')

ratio = dens[10.] / dens[80.]
print(f'\\n面密度从 {dens[10.]:.1f} 掉到 {dens[80.]:.2f} 点/m² —— 衰减 **{ratio:.0f} 倍**')
assert ratio > 100, f'密度衰减应超过 100 倍，实测 {ratio:.0f}'

# 环间距按 d² 增长
i10 = int(np.argmin(np.abs(D_RING - 10.))); i40 = int(np.argmin(np.abs(D_RING - 40.)))
g10 = D_RING[i10+1] - D_RING[i10]; g40 = D_RING[i40+1] - D_RING[i40]
print(f'环间距: {D_RING[i10]:.1f}m 处 {g10:.3f}m,  {D_RING[i40]:.1f}m 处 {g40:.3f}m'
      f'  → 比值 {g40/g10:.1f}，而 (d₂/d₁)² = {(D_RING[i40]/D_RING[i10])**2:.1f}')
assert abs(g40/g10 / (D_RING[i40]/D_RING[i10])**2 - 1) < 0.3, '应当近似按 d² 增长'

# 一块 0.8×0.8m 的标志能得到多少点
def pts_on_sign(d, S=0.8):
    vert = S / (d * np.deg2rad(D_BEAM_DEG))
    horiz = S / (d * np.deg2rad(AZ_DEG))
    return max(0.0, vert) * max(0.0, horiz)

print(f\"\\n{'距离':>7s} {'竖直':>8s} {'水平':>8s} {'总点数':>9s}\")
for d in [10., 20., 30., 50., 73., 80.]:
    v = 0.8/(d*np.deg2rad(D_BEAM_DEG)); h = 0.8/(d*np.deg2rad(AZ_DEG))
    print(f'{d:6.1f}m {v:7.1f} {h:7.1f} {v*h:8.1f}')
assert pts_on_sign(10.) / pts_on_sign(80.) > 50
print(f'\\n✅ 标志点数从 {pts_on_sign(10.):.0f}（10m）掉到 {pts_on_sign(73.):.1f}（73m）')
print('   → **「至少 N 个点」这个过滤条件必须是距离的函数，否则等于只检测近处**')"""),

    md("""## 3 · 多帧累积：静止目标的免费增益"""),

    code("""def accumulate_static(d0, speed_kmh, fps, k_frames, S=0.8):
    '''自车匀速靠近一个静止目标，累积 k 帧的点数。'''
    v = speed_kmh / 3.6
    ds = [d0 - v * (i / fps) for i in range(k_frames)]
    ds = [d for d in ds if d > 2.0]
    return sum(pts_on_sign(d, S) for d in ds), ds

print(f\"{'配置':>28s} {'自车前进':>9s} {'距离区间':>16s} {'累积点数':>9s} {'相对单帧':>9s}\")
acc = {}
for kmh, fps, k in [(60,10,10), (120,10,10), (120,10,5), (60,20,10)]:
    tot, ds = accumulate_static(73., kmh, fps, k)
    base = pts_on_sign(73.)
    acc[(kmh,fps,k)] = tot/base
    print(f'{f"{kmh}km/h @{fps}Hz × {k} 帧":>28s} {kmh/3.6*k/fps:8.1f}m '
          f'{f"{ds[0]:.1f} → {ds[-1]:.1f}m":>16s} {tot:8.1f} {tot/base:8.1f}×')

# 增益大于帧数：因为自车在靠近，而密度 ∝ 1/d²
assert acc[(120,10,10)] > 10, '120km/h 的 10 帧增益应当超过 10 倍'
assert acc[(120,10,10)] > acc[(60,10,10)], '车速越快、收益越大'
print(f'\\n✅ 120 km/h 下 10 帧给 {acc[(120,10,10)]:.1f}× —— **大于帧数 10**')
print('   因为自车前进 33 m，标志从 73 m 走到 43 m，而密度 ∝ 1/d²')

# 代价：运动目标被拖成一条
print(f\"\\n{'累积窗口':>18s} \" + ''.join(f'{v}km/h'.rjust(11) for v in [10,20,50]))
CAR_LEN = 4.5
for k, fps in [(10,10), (5,10), (3,20)]:
    T = k/fps
    row = [v/3.6*T for v in [10,20,50]]
    print(f'{f"{k} 帧 @{fps}Hz ({T:.2f}s)":>18s} ' +
          ''.join(f'{x:8.2f}m{"*" if x>CAR_LEN else " "} ' for x in row))
print(f'  （* = 拖影超过车长 {CAR_LEN} m）')
assert 20/3.6*1.0 > CAR_LEN, '1 秒窗口下 20km/h 的拖影应超过车长'
assert 50/3.6*0.15 < CAR_LEN, '0.15 秒窗口下即使 50km/h 也在车长内'
print('✅ 所以累积窗口应当**按类别设**：静止目标长窗口，运动目标短窗口')"""),

    md("""## 4 · 体素 vs 柱体：为什么柱体能用普通卷积"""),

    code("""def occupancy(pts, r, pillar=False, L=SCENE_L):
    q = pts[:, :2] if pillar else pts
    idx = np.unique(np.floor(q / r).astype(np.int64), axis=0)
    total = int((L[0]/r) * (L[1]/r) * (1 if pillar else L[2]/r))
    return {'n': len(idx), 'total': total, 'rate': len(idx)/total,
            'per_cell': len(pts)/len(idx)}

print(f\"{'方案':>24s} {'非空':>9s} {'总格数':>14s} {'占用率':>10s} {'每格点数':>10s}\")
occ = {}
for tag, r, pil in [('体素 0.05m', 0.05, False), ('体素 0.10m', 0.10, False),
                    ('体素 0.16m', 0.16, False),
                    ('柱体 0.10m', 0.10, True), ('柱体 0.16m', 0.16, True)]:
    s = occupancy(PTS, r, pil)
    occ[tag] = s
    print(f'{tag:>24s} {s["n"]:9,} {s["total"]:14,} {100*s["rate"]:9.3f}% '
          f'{s["per_cell"]:9.2f}')

r_pil = occ['柱体 0.16m']['rate']; r_vox = occ['体素 0.16m']['rate']
print(f'\\n同为 0.16 m：柱体 {100*r_pil:.2f}% vs 体素 {100*r_vox:.3f}%'
      f'  → 密了 **{r_pil/r_vox:.0f} 倍**')
assert r_pil / r_vox > 20, f'柱体应当密一个数量级以上，实测 {r_pil/r_vox:.1f}'
assert r_pil > 0.05, '柱体的占用率应当「足够密」，可以直接用密集 2D 卷积'
print('✅ 这就是 PointPillars 快的真正原因：'
      '**它把问题搬到了一个卷积友好的表示上**')

# 内存对比
print(f'\\n内存（1 B/格）：')
for tag in ['体素 0.05m', '体素 0.10m', '柱体 0.16m']:
    print(f'  {tag:>12s} {occ[tag]["total"]/1e6:9.2f} MB')
print(f'  柱体 0.16m 是体素 0.05m 的 '
      f'1/{occ["体素 0.05m"]["total"]/occ["柱体 0.16m"]["total"]:.0f}')"""),

    md("""## 5 · 采样的偏倚：随机 vs FPS"""),

    code("""def fps_sample(P, K, seed=0):
    '''最远点采样。O(NK)，串行。'''
    P = np.asarray(P, float)
    idx = [int(np.random.default_rng(seed).integers(len(P)))]
    dist = np.linalg.norm(P - P[idx[0]], axis=1)
    for _ in range(K - 1):
        i = int(np.argmax(dist))
        idx.append(i)
        dist = np.minimum(dist, np.linalg.norm(P - P[i], axis=1))
    return np.array(idx)

# 用真实环扫的点云（它天然密度不均匀）
K = 512
rng = np.random.default_rng(0)
ri = rng.choice(len(PTS), K, replace=False)
fi = fps_sample(PTS, K)

far_all = (rng_m > 30).mean()
print(f'原始点集里 >30 m 的点占 {100*far_all:.1f}%\\n')
print(f\"{'采样方式':>10s} {'>30m 占比':>11s} {'相对原始':>10s} {'中位距离':>10s}\")
bias = {}
for tag, i in [('随机', ri), ('FPS', fi)]:
    f = (np.linalg.norm(PTS[i, :2], axis=1) > 30).mean()
    bias[tag] = f / far_all
    print(f'{tag:>10s} {100*f:10.1f}% {f/far_all:9.2f}× '
          f'{np.median(np.linalg.norm(PTS[i,:2],axis=1)):9.1f}m')

assert abs(bias['随机'] - 1.0) < 0.35, '随机采样应当近似保持分布'
assert bias['FPS'] > 3.0, f'FPS 应当极度偏向远处，实测 {bias["FPS"]:.2f}×'
print(f'\\n✅ 随机采样保持分布（{bias["随机"]:.2f}×），'
      f'而 FPS 把远处占比推到 {bias["FPS"]:.1f} 倍')
print('   → **FPS 不是「更好的采样」，它是一个方向相反的偏倚**')

# 标志点被采到的概率：这才是 TSR 关心的
for tag, i in [('随机', ri), ('FPS', fi)]:
    n_sign = int((LAB[i] == 2).sum())
    print(f'  {tag}采样采到的标志点: {n_sign:3d} / {K}'
          f'  （原始占比 {100*(LAB==2).mean():.2f}%）')

# 成本
print(f'\\nFPS 的成本: O(NK) = {len(PTS):,} × {K} = '
      f'{len(PTS)*K/1e6:.1f}M 次距离计算，且**无法简单并行**')"""),

    md("""## 6 · 选型：两个约束的交集"""),

    code("""def feasible_r(accuracy_m, budget_mb, L=SCENE_L):
    '''返回 (精度允许的最粗 r, 内存允许的最细 r, 是否可行)。'''
    r_acc = 2.0 * accuracy_m / np.sqrt(3)                  # r√3/2 <= accuracy
    r_mem = (np.prod(L) / (budget_mb * 1e6)) ** (1/3)      # 格数 <= budget
    return r_acc, r_mem, bool(r_mem <= r_acc)

print(f\"{'精度要求':>9s} {'预算':>8s} {'精度允许最粗 r':>15s} {'内存允许最细 r':>15s} {'交集':>8s}\")
for acc in [0.30, 0.10, 0.05, 0.02]:
    for bud in [100.0]:
        ra, rm, ok = feasible_r(acc, bud)
        print(f'{acc:8.2f}m {bud:7.0f}MB {ra:14.4f}m {rm:14.4f}m '
              f'{"✅ 可行" if ok else "❌ 为空":>8s}')

assert feasible_r(0.30, 100.)[2] is True
assert feasible_r(0.02, 100.)[2] is False
ra, rm, _ = feasible_r(0.02, 100.)
print(f'\\n0.02 m 精度需要 r <= {ra:.4f} m，而 100 MB 只够 {rm:.4f} m'
      f'  → 差 {rm/ra:.1f} 倍')

# 三条出路
print('\\n三条出路：')
sp = occ['体素 0.05m']
print(f'  ① 稀疏化：内存 ∝ 非空格数 {sp["n"]:,} 而不是 {sp["total"]:,}'
      f'  → 只需 {sp["n"]/1e6:.2f} MB（模块 03）')
print(f'  ② 柱体：格数 {occ["柱体 0.16m"]["total"]:,} = '
      f'{occ["柱体 0.16m"]["total"]/1e6:.2f} MB（第 4 节）')
print(f'  ③ 不用体素：点云 {len(PTS)*3*4/1e6:.2f} MB（模块 02）')
assert sp['n'] * 1.0 / 1e6 < 100, '稀疏化后应当远低于预算'
print('\\n✅ 交集为空时应当明确拒绝，而不是凑一个分辨率')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| 面密度衰减 | 67.7 → 0.13 点/m²（10 → 80 m），**约 520 倍** |
| 环间距 | 按 $d^2$ 增长；**73 m 处相邻环相距 31 m** |
| 标志点数 | 255（10 m）→ **4.6（73 m）** |
| 多帧累积 | 120 km/h 10 帧 = **17.2×**（>10，因自车在靠近） |
| 累积的代价 | 1 s 窗口 + 相对 20 km/h → 拖影 **5.56 m > 车长** |
| 柱体 vs 体素 | 同 0.16 m：**7.642% vs 0.156%**（密 **49.0 倍**） |
| 采样偏倚 | 随机 **1.24×**，**FPS 7.49×**（中位距离 7.8 → 55.9 m） |
| 选型 | 0.02 m 精度 + 100 MB → **交集为空**；三条出路 |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：按距离分段的密度报告

实现 `density_report(pts, bands)`，`bands` 是 `[(lo, hi), ...]` 的距离分段
（用 $xy$ 平面距离），返回 dict：`{(lo,hi): {...}}`，每段含：

- `'n'` —— 点数
- `'area_m2'` —— 该环带的面积（**只算被扫到的方位角范围**，本 notebook 是 ±30°）
- `'density'` —— 点数 / 面积
- `'rel_density'` —— 相对第一段的密度比

用它验证密度衰减，并说明「跨距离比较点数」为什么没有意义。"""),

    code("""def density_report(pts, bands, az_span_deg=60.0):
    \"\"\"返回 {(lo,hi): dict(n, area_m2, density, rel_density)}。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
BANDS = [(5., 15.), (15., 30.), (30., 50.), (50., 80.)]
rep = density_report(PTS, BANDS)
assert set(rep) == set(BANDS)
for k, v in rep.items():
    assert set(v) == {'n', 'area_m2', 'density', 'rel_density'}

print(f\"{'距离段':>14s} {'点数':>8s} {'面积(m²)':>11s} {'密度(点/m²)':>13s} {'相对密度':>9s}\")
for b in BANDS:
    v = rep[b]
    print(f'{f"{b[0]:.0f}–{b[1]:.0f}m":>14s} {v["n"]:8,} {v["area_m2"]:10.1f} '
          f'{v["density"]:12.3f} {v["rel_density"]:8.3f}')

# ① 密度必须单调下降
ds = [rep[b]['density'] for b in BANDS]
assert ds == sorted(ds, reverse=True), f'密度应单调下降：{ds}'
assert rep[BANDS[0]]['rel_density'] == 1.0
assert rep[BANDS[-1]]['rel_density'] < 0.05, \\
    f'最远段的相对密度应低于 5%，实测 {rep[BANDS[-1]]["rel_density"]:.3f}'

# ② 面积按环带算：外圈面积更大，所以「点数少」有一部分只是面积效应
areas = [rep[b]['area_m2'] for b in BANDS]
assert areas == sorted(areas), '外圈环带面积更大'
n_far, n_near = rep[BANDS[-1]]['n'], rep[BANDS[0]]['n']
print(f'\\n50–80m 段的点数是 5–15m 段的 {n_far/n_near:.2f}×，'
      f'而面积是 {areas[-1]/areas[0]:.2f}×')
print(f'  → 密度比只有 {rep[BANDS[-1]]["rel_density"]:.3f}×'
      ' —— **点数比会严重低估真实的稀疏程度**')
print('✅ 练习 1 通过：跨距离比较点数没有意义，必须比密度')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def density_report(pts, bands, az_span_deg=60.0):
    d = np.linalg.norm(np.asarray(pts, float)[:, :2], axis=1)
    frac = az_span_deg / 360.0
    out = {}
    first = None
    for lo, hi in bands:
        m = (d >= lo) & (d < hi)
        area = np.pi * (hi**2 - lo**2) * frac        # 环带面积 × 方位角占比
        dens = m.sum() / area
        if first is None:
            first = dens
        out[(lo, hi)] = {'n': int(m.sum()), 'area_m2': float(area),
                         'density': float(dens),
                         'rel_density': float(dens / first)}
    return out

rep = density_report(PTS, BANDS)
assert rep[BANDS[-1]]['rel_density'] < 0.05
print('✅ 参考答案 1 通过')
print('   关键是面积要用**环带**（π(hi²−lo²)）而不是别的——')
print('   否则「远处点少」里混着面积效应，得不到真实的密度比。')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：累积窗口的选择器

实现 `pick_accumulation(target_pts, d0, speed_kmh, fps, max_smear_m, rel_speed_kmh)`：
选出**满足拖影上限的前提下**、能达到 `target_pts` 的最小帧数。

返回 `(k_frames, accumulated_pts, smear_m, feasible)`：

- 从 $k=1$ 起递增，直到累积点数 $\\ge$ `target_pts`
- 若在 `smear <= max_smear_m` 的范围内达不到，返回 `feasible=False`
  和**该上限允许的最大 $k$** 及其点数"""),

    code("""def pick_accumulation(target_pts, d0, speed_kmh, fps,
                      max_smear_m, rel_speed_kmh, S=0.8):
    \"\"\"返回 (k_frames, accumulated_pts, smear_m, feasible)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# 场景：73m 处的标志，想要至少 30 个点
print(f\"{'车速':>8s} {'相对速度':>9s} {'拖影上限':>9s} {'帧数':>5s} \"
      f\"{'点数':>7s} {'拖影':>8s} {'可行':>6s}\")
rows = []
for kmh in [60, 120]:
    for rel in [0, 20, 50]:
        for smax in [1.0, 5.0]:
            k, pts_n, sm, ok = pick_accumulation(30., 73., kmh, 10, smax, rel)
            rows.append((kmh, rel, smax, k, pts_n, sm, ok))
            print(f'{kmh:7d}k {rel:8d}k {smax:8.1f}m {k:5d} {pts_n:6.1f} '
                  f'{sm:7.2f}m {str(ok):>6s}')

# ① 相对速度为 0（纯静止场景）时，拖影恒为 0 -> 一定可行
for kmh in [60, 120]:
    k, n, sm, ok = pick_accumulation(30., 73., kmh, 10, 1.0, 0)
    assert ok is True and sm == 0.0, (kmh, sm, ok)

# ② 拖影上限很紧 + 相对速度大 -> 不可行
k, n, sm, ok = pick_accumulation(30., 73., 60, 10, 1.0, 50)
assert ok is False, (k, n, sm, ok)
assert sm <= 1.0 + 1e-12, '不可行时也不能超过上限'
print(f'\\n60km/h + 相对 50km/h + 拖影上限 1.0m: 只能累积 {k} 帧'
      f'（{n:.1f} 点 < 30）-> 不可行')

# ③ 车速越快，达到同样点数需要的帧数越少（因为自车在靠近）
k60 = pick_accumulation(30., 73., 60, 10, 99., 0)[0]
k120 = pick_accumulation(30., 73., 120, 10, 99., 0)[0]
assert k120 <= k60, f'120km/h 应当不多于 60km/h 的帧数（{k120} vs {k60}）'
print(f'达到 30 点所需帧数: 60km/h 要 {k60} 帧，120km/h 只要 {k120} 帧')
print('✅ 练习 2 通过：**拖影上限是硬约束，点数目标是软目标**——'
      '所以先判可行再取最小帧数')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def pick_accumulation(target_pts, d0, speed_kmh, fps,
                      max_smear_m, rel_speed_kmh, S=0.8):
    v_rel = rel_speed_kmh / 3.6
    best_k, best_n, best_s = 1, pts_on_sign(d0, S), 0.0
    k = 1
    while True:
        smear = v_rel * (k / fps)
        if smear > max_smear_m + 1e-12:
            break                                  # 超过硬约束，停在上一个 k
        tot, _ = accumulate_static(d0, speed_kmh, fps, k, S)
        best_k, best_n, best_s = k, tot, smear
        if tot >= target_pts:
            return k, float(tot), float(smear), True
        k += 1
        if k > 200:
            break
    return best_k, float(best_n), float(best_s), False

assert pick_accumulation(30., 73., 60, 10, 1.0, 0)[3] is True
assert pick_accumulation(30., 73., 60, 10, 1.0, 50)[3] is False
print('✅ 参考答案 2 通过')
print('   注意 while 循环先判拖影再累积：**硬约束必须在软目标之前检查**，')
print('   否则会返回一个「点数够了但拖影超标」的配置。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：采样偏倚报告

实现 `sampling_bias(pts, labels, K, method, seed=0)`，
`method` 取 `'random'` / `'fps'`，返回 dict：

- `'far_frac'` —— 采样结果里 $>30$ m 的点占比
- `'far_bias'` —— 上者 / 原始点集的对应占比
- `'sign_pts'` —— 采到的标志点数（`labels==2`）
- `'median_range'` —— 采样点的中位距离
- `'cost_ops'` —— 距离计算次数（random 记 0，FPS 记 $N\\cdot K$）"""),

    code("""def sampling_bias(pts, labels, K, method, seed=0):
    \"\"\"返回 dict(far_frac, far_bias, sign_pts, median_range, cost_ops)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
for m in ['random', 'fps']:
    b = sampling_bias(PTS, LAB, 512, m)
    assert set(b) == {'far_frac', 'far_bias', 'sign_pts', 'median_range', 'cost_ops'}

br = sampling_bias(PTS, LAB, 512, 'random')
bf = sampling_bias(PTS, LAB, 512, 'fps')
print(f\"{'方式':>8s} {'>30m 占比':>11s} {'偏倚':>8s} {'标志点':>8s} \"
      f\"{'中位距离':>10s} {'距离计算次数':>14s}\")
for tag, b in [('random', br), ('fps', bf)]:
    print(f'{tag:>8s} {100*b["far_frac"]:10.1f}% {b["far_bias"]:7.2f}× '
          f'{b["sign_pts"]:7d} {b["median_range"]:9.1f}m {b["cost_ops"]:14,}')

# ① 随机采样近似保持分布，FPS 极度偏向远处
assert abs(br['far_bias'] - 1.0) < 0.35, br['far_bias']
assert bf['far_bias'] > 3.0, bf['far_bias']
assert bf['median_range'] > br['median_range'], 'FPS 的中位距离更远'

# ② 成本差别
assert br['cost_ops'] == 0 and bf['cost_ops'] == len(PTS) * 512
print(f'\\nFPS 的成本是 {bf["cost_ops"]/1e6:.1f}M 次距离计算，而随机是 0')

# ③ K 增大时随机采样的偏倚趋于 1，而 FPS 的偏倚下降（远处点被采完了）
b_small = sampling_bias(PTS, LAB, 128, 'fps')
b_large = sampling_bias(PTS, LAB, 2048, 'fps')
print(f'FPS 的偏倚: K=128 时 {b_small["far_bias"]:.2f}×，'
      f'K=2048 时 {b_large["far_bias"]:.2f}×')
assert b_large['far_bias'] < b_small['far_bias'], \\
    'K 越大，FPS 的偏倚越小（稀疏区的点被采完后只能采密区）'
print('  → **FPS 的偏倚强度取决于 K**，所以换 K 会改变输入分布')
print('✅ 练习 3 通过：采样方式与 K 都必须记录，并在训练/部署间保持一致')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def sampling_bias(pts, labels, K, method, seed=0):
    pts = np.asarray(pts, float); labels = np.asarray(labels)
    d_all = np.linalg.norm(pts[:, :2], axis=1)
    far_all = (d_all > 30).mean()
    if method == 'random':
        idx = np.random.default_rng(seed).choice(len(pts), K, replace=False)
        cost = 0
    elif method == 'fps':
        idx = fps_sample(pts, K, seed=seed)
        cost = len(pts) * K
    else:
        raise ValueError(method)
    d = np.linalg.norm(pts[idx, :2], axis=1)
    ff = float((d > 30).mean())
    return {'far_frac': ff, 'far_bias': float(ff / far_all),
            'sign_pts': int((labels[idx] == 2).sum()),
            'median_range': float(np.median(d)), 'cost_ops': int(cost)}

assert sampling_bias(PTS, LAB, 512, 'fps')['far_bias'] > 3.0
assert sampling_bias(PTS, LAB, 512, 'random')['cost_ops'] == 0
print('✅ 参考答案 3 通过')
print('   far_bias 用「相对原始分布」而不是绝对占比 ——')
print('   因为绝对占比取决于场景，而偏倚倍数是采样方式自身的性质。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：分辨率可行性与出路

实现 `resolution_plan(accuracy_m, budget_mb, pts, L=SCENE_L)`，返回 dict：

- `'r_accuracy'`, `'r_memory'` —— 两个约束给出的界
- `'dense_feasible'` —— bool
- `'routes'` —— 当密集不可行时，给出可行的出路列表，每项是
  `(名称, 所需内存 MB)`，从下面三条里选出**真正装得下**的：
  `'sparse'`（内存 = 非空格数 × 1 B，$r$ 取 `r_accuracy`）、
  `'pillar'`（$r$ 取 `r_accuracy`，格数 = $(L_x/r)(L_y/r)$）、
  `'point_cloud'`（$N\\times3\\times4$ B）
- `'recommended'` —— `routes` 里内存最小的那个名称，或密集可行时为 `'dense'`"""),

    code("""def resolution_plan(accuracy_m, budget_mb, pts, L=SCENE_L):
    \"\"\"返回 dict(r_accuracy, r_memory, dense_feasible, routes, recommended)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
print(f\"{'精度':>8s} {'预算':>8s} {'密集可行':>9s} {'推荐':>13s} {'可行出路':>40s}\")
for acc in [0.30, 0.10, 0.02]:
    for bud in [1.0, 100.0]:
        pl = resolution_plan(acc, bud, PTS)
        assert set(pl) == {'r_accuracy', 'r_memory', 'dense_feasible',
                           'routes', 'recommended'}
        rs = ', '.join(f'{n}({m:.2f}MB)' for n, m in pl['routes'])
        print(f'{acc:7.2f}m {bud:7.0f}MB {str(pl["dense_feasible"]):>9s} '
              f'{pl["recommended"]:>13s} {rs:>40s}')

# ① 精度松 + 预算大 -> 密集可行
p1 = resolution_plan(0.30, 100., PTS)
assert p1['dense_feasible'] is True and p1['recommended'] == 'dense'

# ② 精度苛刻 -> 密集不可行，但稀疏/柱体/点云可以
p2 = resolution_plan(0.02, 100., PTS)
assert p2['dense_feasible'] is False
names = [n for n, _ in p2['routes']]
assert 'sparse' in names and 'pillar' in names and 'point_cloud' in names, names
assert p2['recommended'] in names
print(f'\\n0.02m 精度 + 100MB: 密集不可行；出路 {names}')
for n, m in p2['routes']:
    print(f'    {n:12s} {m:8.3f} MB')

# ③ 预算极小 -> 只剩点云或什么都不剩
p3 = resolution_plan(0.02, 1.0, PTS)
print(f'\\n0.02m 精度 + 1MB: 出路 {[n for n,_ in p3["routes"]]}，'
      f'推荐 {p3["recommended"]}')
assert all(m <= 1.0 for _, m in p3['routes']), '列出的出路必须真的装得下'

# ④ 两个界的关系
p = resolution_plan(0.10, 100., PTS)
assert abs(p['r_accuracy'] - 2*0.10/np.sqrt(3)) < 1e-12
assert abs(p['r_memory'] - (np.prod(SCENE_L)/100e6)**(1/3)) < 1e-12
print('\\n✅ 练习 4 通过：**不可行时给出路，而不是凑一个分辨率**')""" ),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def resolution_plan(accuracy_m, budget_mb, pts, L=SCENE_L):
    r_acc = 2.0 * accuracy_m / np.sqrt(3)
    r_mem = (np.prod(L) / (budget_mb * 1e6)) ** (1/3)
    dense_ok = bool(r_mem <= r_acc)

    routes = []
    if not dense_ok:
        # 稀疏：内存 ∝ 非空格数（用精度要求的 r）
        n_occ = len(np.unique(np.floor(pts / r_acc).astype(np.int64), axis=0))
        routes.append(('sparse', n_occ / 1e6))
        # 柱体：第三个乘子换成 1
        n_pil = int((L[0] / r_acc) * (L[1] / r_acc))
        routes.append(('pillar', n_pil / 1e6))
        # 点云：原样存
        routes.append(('point_cloud', len(pts) * 3 * 4 / 1e6))
        routes = [(n, m) for n, m in routes if m <= budget_mb]

    rec = 'dense' if dense_ok else (
        min(routes, key=lambda t: t[1])[0] if routes else 'infeasible')
    return {'r_accuracy': float(r_acc), 'r_memory': float(r_mem),
            'dense_feasible': dense_ok, 'routes': routes, 'recommended': rec}

assert resolution_plan(0.30, 100., PTS)['recommended'] == 'dense'
assert resolution_plan(0.02, 100., PTS)['dense_feasible'] is False
print('✅ 参考答案 4 通过')
print('   三条出路的内存公式各自绕开一个乘子：')
print('     sparse  —— 把「总格数」换成「非空格数」（占用率的倒数）')
print('     pillar  —— 把第三个乘子换成 1')
print('     point_cloud —— 完全不建网格')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) 真实数据集的密度分层（第 2 节）──
#   KITTI / nuScenes 的评测本来就按距离分档，而原因就是密度衰减：
#   nuScenes 的 mAP 在 0–20 / 20–30 / 30–50 m 三档上差异极大。
#   所以「最少点数」这个过滤条件要写成距离的函数：
def min_points_for(range_m, k=8.0, ref=20.0):
    return max(1, int(k * (ref / max(range_m, 1.0)) ** 2))     # ∝ 1/d²
#   ↑ 常数阈值 + 520 倍的密度衰减 = 悄悄地把远处目标全丢掉

# ── 2) 多帧累积（第 3 节）──
#   nuScenes 官方基线就用 10 帧累积（0.5 s），并把每点的 Δt 作为一个额外通道：
pts = np.concatenate([transform(f.pts, ego_now @ inv(f.ego)) for f in frames])
dt  = np.concatenate([np.full(len(f.pts), t_now - f.t) for f in frames])
feat = np.column_stack([pts, intensity, dt])       # ← Δt 让网络能自己学会处理拖影
#   ⚠️ transform 用的 ego 位姿必须与点的时间戳对齐 —— 而 C72 模块 05 量过：
#      用错时刻的位姿等于把时间戳错位又引入一次

# ── 3) 体素化的两个上限由本 notebook 算出来 ──
from spconv.pytorch.utils import PointToVoxel
gen = PointToVoxel(vsize_xyz=[0.16, 0.16, 4.0],          # ← z=4.0 就是「柱体」
                   coors_range_xyz=[0, -40, -3, 80, 40, 1],
                   max_num_points_per_voxel=32,          # ← 练习 1 的 counts.max()
                   max_num_voxels=30000)                 # ← 由占用率算出来
#   这两个上限设小了会**静默丢点**（不报错、不警告）

# ── 4) 采样方式必须进配置（第 5 节）──
#   MMDetection3D 的 PointSample 支持 'random' 与 'fps'，而两者的偏倚相反：
#   train/test pipeline 里用了不同的 sample_method 是一个真实的、静默的 bug。
```

> **落地顺序建议**：先把「最少点数」改成距离的函数（一行，抓一整类漏检），
> 再核对训练/部署两侧的采样方式是否一致，最后才考虑累积（它需要可靠的位姿与时间戳，
> 而那是 C72 模块 05 的前提）。"""),
]
