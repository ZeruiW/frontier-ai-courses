# -*- coding: utf-8 -*-
"""C73 模块 03 · 体素化与稀疏卷积。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01 的占用率与柱体；模块 02 的对称函数"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_sparse_voxel.ipynb'
                       '（稀疏张量的哈希索引 / '
                       '<strong>常规稀疏卷积 4 层膨胀 52.54×，占用率 0.215% → 11.28%</strong> / '
                       'FLOPs 优势从 465.7× 掉到 8.86× / '
                       '<strong>子流形的真实代价：标志碎成 2 个互不通信的分量，且与地面完全不连通</strong> / '
                       '格内特征编码）'),
    ("核心参考", "Graham, Engelcke &amp; van der Maaten, <em>3D Semantic Segmentation "
                 "with Submanifold Sparse Convolutional Networks</em>（CVPR 2018）· "
                 "Choy et al., <em>4D Spatio-Temporal ConvNets (MinkowskiNet)</em>"
                 "（CVPR 2019）· Yan et al., <em>SECOND</em>（Sensors 2018）· "
                 "spconv / MinkowskiEngine 的实现文档"),
    ("预计时长", "读 45 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("sparse-tensor", "稀疏张量：坐标 + 特征 + 一张哈希表", "".join([
        P("模块 01 量到占用率 0.2% 量级。"
          "<strong>密集张量把 99.8% 的内存与算力花在空气上，"
          "而修法在数据结构层面而不是算法层面。</strong>"),
        ASCII("""
   密集张量                      稀疏张量
   ┌─────────────────┐          coords: (M, 3) int32   ← 只存非空的
   │ 0 0 0 0 0 0 0 0 │          feats:  (M, C) float32
   │ 0 0 3 0 0 0 0 0 │          hash:   coord -> row     ← O(1) 邻居查询
   │ 0 0 0 0 0 7 0 0 │
   │ 0 0 0 0 0 0 0 0 │          内存 ∝ M（非空数），而不是 ∝ (L/r)³
   └─────────────────┘
     4×8 = 32 格，2 个非空       M = 2

   卷积怎么做：
     对每个输出位置 o，遍历核的 27 个偏移 δ
       查 hash[o − δ] → 命中就累加 W[δ] @ feats[row]
     └── 关键：**输出位置的集合怎么定**，决定了下面两节的全部内容
        """),
        DUAL(
            "<strong>最后一行是这一整个模块的枢纽。</strong>"
            "<em>密集卷积的输出位置是「所有位置」；"
            "而稀疏卷积必须显式地决定「哪些位置产出输出」</em>。"
            "<strong>两个自然的选择给出完全不同的行为</strong>："
            "① <strong>任何被核覆盖到的位置</strong>都产出 → <em>常规稀疏卷积</em>；"
            "② <strong>只有输入非空的位置</strong>产出 → <em>子流形稀疏卷积</em>。",
            "<strong>而哈希表这一点值得单说：它让邻居查询变成 $O(1)$，"
            "而且这张表可以在层间复用。</strong>"
            "<em>对比模块 02 第 6b 节：点云路线每一层都要重新建邻域（FPS + 球查询，"
            "$N{=}102{,}668$、$M{=}1024$ 时是 1.05 亿次距离计算）</em>；"
            "<strong>而体素路线的邻居关系由坐标算术直接给出——"
            "只要活跃集不变，规则表（rulebook）也不变。</strong>"
            "<em>这就是「体素路线 FLOP 更高但更快」的结构性原因。</em>",
        ),
    ])),

    # ============================================================== 1b
    ("rulebook", "规则表：稀疏卷积的真实开销与它的一个反直觉性质", "".join([
        P("稀疏卷积的实际计算量不是 $M\\times27\\times C_{in}\\times C_{out}$，"
          "而是<strong>规则表条目数</strong> $\\times C_{in}\\times C_{out}$——"
          "因为 27 个邻居里大部分是空的。"),
        MATH(r"\text{rules} = \bigl|\{(o,\delta) : o\in\mathcal{A},\ "
             r"o-\delta\in\mathcal{A},\ \delta\in K\}\bigr|"),
        P("notebook 第 1b 节在五种活跃集形状上量这两个量："),
        TABLE(["活跃集形状", "活跃数 $M$", "第一层膨胀率", "规则条目/活跃",
               "两者之积"], [
            ["<strong>完全散开（随机 2975 点）</strong>", "2,975",
             "<strong>22.05×</strong>", "<strong>1.33</strong>", "29.3"],
            ["一条直线（50 体素，模拟杆）", "50", "9.36×", "2.96", "27.7"],
            ["一个薄片（10×10，模拟牌面）", "100", "4.32×", "7.84", "33.9"],
            ["一个大平面（60×60，模拟地面）", "3,600", "3.00×", "—", "—"],
            ["<strong>一个实心块（$12^3$）</strong>", "1,728",
             "<strong>1.59×</strong>", "<strong>22.75</strong>", "36.2"],
        ]),
        DUAL(
            "<strong>两列的排序恰好相反，而这不是巧合。</strong>"
            "<em>膨胀率高意味着「活跃体素周围大多是空的」，"
            "而那正好意味着规则条目少（真实邻居少）；"
            "反之实心块几乎不膨胀，但每个位置有 22.75 个真实邻居要算</em>。"
            "<strong>所以两者的积被核大小 27 大致框住（实测 27.7–36.2）</strong>——"
            "<em>因为它们从两端数的是同一批「邻接关系」。</em>",
            "<strong>这给出一个反直觉的推论：越稀疏的活跃集，"
            "单层卷积反而越<em>便宜</em>（规则少），"
            "而它的<em>膨胀</em>越贵。</strong>"
            "<em>所以「稀疏」在这一层是两个方向的作用力："
            "它降低本层的计算，又加速活跃集的增长</em>。"
            "<strong>而子流形卷积的价值正是「拿掉后者、保留前者」</strong>——"
            "<em>它让极度稀疏的输入（本课 0.215%）以最低的规则密度被处理，"
            "而不必承担 52.54× 的膨胀。</em>",
        ),
        CALLOUT("intuition",
                "<strong>顺带纠正一个容易犯的估算错误。</strong>"
                "<em>用 $M\\times27$ 估稀疏卷积的乘加次数，"
                "在散开的活跃集上会高估 20 倍（实测 1.33 而不是 27）</em>。"
                "<strong>正确的估法是先算规则表大小，而它只需要一次邻域查询。</strong>"
                "<em>这与 C72 模块 02「重投影误差是必要非充分条件」是同一类纪律："
                "代理指标要与它代理的量真正相关。</em>"),
    ])),

    # ============================================================== 2
    ("dilation", "常规稀疏卷积会膨胀，而膨胀是指数级的", "".join([
        P("「任何被核覆盖到的位置都产出输出」听起来很自然。"
          "<strong>而它的后果是每一层把活跃集按 $3^3$ 的邻域膨胀一次。</strong>"),
        P("notebook 第 2 节在一帧真实环扫点云上量（检测范围 $80\\times80\\times6$ m，"
          "$r{=}0.2$ m，网格 $400\\times400\\times30$）："),
        TABLE(["层", "常规稀疏卷积的非空数", "占用率", "累计膨胀", "子流形的非空数"], [
            ["0（输入）", "10,306", "0.2147%", "1.00×", "10,306"],
            ["1", "80,103", "1.6688%", "7.77×", "10,306"],
            ["2", "197,780", "4.1204%", "19.19×", "10,306"],
            ["3", "353,314", "7.3607%", "34.28×", "10,306"],
            ["<strong>4</strong>", "<strong>541,523</strong>",
             "<strong>11.2817%</strong>", "<strong>52.54×</strong>",
             "<strong>10,306</strong>"],
        ]),
        DUAL(
            "<strong>四层之后占用率从 0.215% 涨到 11.28%——稀疏性基本消失。</strong>"
            "<em>而第一层就膨胀 7.77×（不是 27×，因为相邻的活跃体素共享很多邻居）；"
            "之后每层大约再乘 2.5×，因为活跃区已经连成片</em>。"
            "<strong>所以膨胀率不是常数 27，它取决于活跃集自身的形状</strong>——"
            "<em>第 1b 节量出的排序是：完全散开 22.05× &gt; 直线 9.36× &gt; "
            "薄片 4.32× &gt; 平面 3.00× &gt; 实心块 1.59×</em>。"
            "<strong>也就是说「越散开膨胀越快」，"
            "而真实点云的第一层（7.77×）落在散开与薄片之间。</strong>",
            "<strong>而这个膨胀是「无中生有」的：新增的 53 万个活跃位置，"
            "对应的输入全是空的。</strong>"
            "<em>它们的特征来自核的边缘权重乘上少量真实输入——"
            "也就是在空气里插值出一片「虚假的占据」</em>。"
            "<strong>这不只是浪费算力，它还改变了后续层「看到」的几何："
            "一个薄薄的标志在四层之后会变成一团直径几米的模糊斑块。</strong>"
            "<em>而这与 C72 模块 04 的「前向映射空洞被形态学闭运算填上」是同一类问题——"
            "用插值伪造观测。</em>",
        ),
    ])),

    # ============================================================== 3
    ("flops", "FLOPs 优势的消失", "".join([
        TABLE(["方案", "活跃位置数", "FLOP（$3^3$，64→64）", "相对密集"], [
            ["密集卷积", "4,800,000（全部）", "<strong>530.84 GFLOP</strong>", "1×"],
            ["<strong>子流形稀疏</strong>", "10,306",
             "<strong>1.140 GFLOP</strong>", "<strong>465.7× 更少</strong>"],
            ["常规稀疏（4 层后）", "541,523", "59.89 GFLOP",
             "<strong>只剩 8.86×</strong>"],
        ]),
        DUAL(
            "<strong>稀疏卷积的全部收益就是「占用率的倒数」——"
            "所以任何让占用率上升的东西都在直接吃掉收益。</strong>"
            "<em>465.7× 与 8.86× 相差 53 倍，而这个 53 正好是第 2 节那个累计膨胀率</em>。"
            "<strong>换句话说：膨胀率与 FLOPs 收益是同一个数的两种说法。</strong>",
            "<strong>所以「用了稀疏卷积」这句话本身不说明任何事——"
            "必须问「哪一种，以及活跃集怎么演化」。</strong>"
            "<em>一个只用常规稀疏卷积的深网络，在最后几层的占用率可能已经超过 50%，"
            "此时它比密集卷积只快不到 2 倍，却承担了稀疏实现的全部复杂度</em>。"
            "<strong>而这件事在 FLOPs 报表上看不出来</strong>——"
            "<em>因为大多数报表只报第一层或平均值。"
            "正确的做法是<strong>逐层报活跃数</strong>（练习 2）。</em>",
        ),
        H3("逐层的活跃数长什么样"),
        TABLE(["层", "常规稀疏", "子流形"], [
            ["0（输入）", "10,306", "10,306"],
            ["1", "80,103", "10,306"],
            ["2", "197,780", "10,306"],
            ["3", "353,314", "10,306"],
            ["4", "<strong>541,523</strong>", "<strong>10,306</strong>"],
        ]),
        P("<strong>右边那一列恒定，就是子流形卷积的全部定义。</strong>"
          "<em>而左边那一列的形状（前两层涨得最快、之后变缓）"
          "反映的是活跃集从「散开」逐渐变成「成片」——"
          "而第 1b 节量过：散开的膨胀率 22.05×、成片的只有 1.59×</em>。"),
        CALLOUT("intuition",
                "<strong>一条零成本的诊断</strong>："
                "在你的稀疏网络里逐层打印 <code>len(coords)</code>。"
                "<em>如果它随深度快速增长，说明你用的是常规稀疏卷积；"
                "如果它保持不变，说明是子流形</em>。"
                "<strong>而如果它增长到网格的百分之几十，"
                "那么换成密集卷积可能反而更快（实现更简单、访存更规则）。</strong>"),
    ])),

    # ============================================================== 4
    ("submanifold", "子流形稀疏卷积：把活跃集钉死", "".join([
        P("Graham et al.（2018）的做法极简："
          "<strong>输出位置 = 输入位置。</strong>"
          "核照样看 27 个邻居，但只在<em>本来就非空</em>的位置写输出。"),
        MATH(r"y_o = \sum_{\delta:\ o-\delta \in \mathcal{A}} W_\delta\, x_{o-\delta},"
             r"\qquad o \in \mathcal{A}\ \text{（活跃集不变）}"),
        DUAL(
            "<strong>于是活跃集在整个网络里恒为 10,306，占用率恒为 0.215%，"
            "FLOPs 优势恒为 465.7×。</strong>"
            "<em>而规则表（rulebook）也只需要算一次，可以在所有同分辨率的层之间复用</em>——"
            "<strong>这是子流形卷积在工程上真正省时间的地方，"
            "而它在 FLOPs 上看不出来。</strong>",
            "<strong>而「活跃集不变」这一条同时是它的全部代价——下一节展开。</strong>"
            "<em>直觉上的问题是：如果输出只在原来非空的位置产生，"
            "那么信息就无法流到空的位置去；"
            "而「空的位置」正是把两个分开的物体部件连起来的地方</em>。"
            "<strong>所以子流形卷积的感受野不像密集卷积那样随层数线性增长——"
            "它被活跃集的<em>连通结构</em>限制住了。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("real-cost", "本模块的核心：子流形卷积下，不连通的部分永远不通信", "".join([
        P("把上一节那句话量出来。"
          "<strong>对每个目标<em>实例</em>算一次连通分量</strong>"
          "（$r{=}0.2$ m、26-邻接；"
          "<em>注意必须按实例算——三块标志相距 30–75 m，"
          "把它们混在一起算出的「间隙」是 225 个体素，没有意义</em>）："),
        TABLE(["目标", "点数", "体素数", "分量数", "内部最大间隙",
               "分量内的地面体素数"], [
            ["车 #0（20 m）", "413", "128", "7", "81.2 体素（16.24 m）",
             "<strong>726</strong>"],
            ["车 #1（35 m）", "131", "82", "8", "105.8 体素（21.15 m）", "297"],
            ["车 #2（60 m）", "30", "30", "6", "8.7 体素（1.73 m）",
             "<strong>0</strong>"],
            ["车 #3（80 m）", "14", "14", "8", "9.5 体素（1.90 m）",
             "<strong>0</strong>"],
            ["<strong>标志 #4（30 m）</strong>", "21", "15",
             "<strong>2</strong>（10 + 5）", "<strong>2.5 体素（0.50 m）</strong>",
             "<strong>0</strong>"],
            ["标志 #5（55 m）", "8", "8", "2（4 + 4）", "2.0 体素（0.40 m）",
             "<strong>0</strong>"],
            ["标志 #6（75 m）", "3", "3", "1", "—", "<strong>0</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>两条结论，而第二条是意外的。</strong>"
                "<em>① <strong>车与地面连通（轮胎接地）</strong>："
                "20 m 处那辆车的分量里含 726 个地面体素，"
                "所以子流形卷积能在车与地面之间传信息；"
                "<strong>而标志悬空，分量里的地面体素恒为 0</strong>——"
                "而「离地多高」正是区分标志与地面标记的唯一线索（模块 01 第 4 节）。</em>"
                "<em>② <strong>「接地」这个性质本身随距离退化</strong>："
                "60 m 与 80 m 处的车也变成 0 个地面体素——"
                "因为点太疏，车与地面之间已经断开。</em>"),
        P("<strong>而标志自身也碎成多块</strong>："
          "30 m 处那块 15 个体素分成 2 个分量（10 + 5），"
          "<strong>内部间隙 2.5 个体素 = 0.50 m</strong>。"
          "<em>所以在纯子流形卷积下，同一块标志的两半也不交换信息。</em>"),
        DUAL(
            "<strong>这不是一个精度问题，是一个可达性问题。</strong>"
            "<em>子流形卷积的信息传播被限制在活跃集的连通分量内，"
            "而稀疏采样让远处的薄物体天然碎成多个分量</em>"
            "（<strong>模块 01 量过：73 m 处的标志只有 4.6 个点</strong>）。"
            "<strong>所以「越远越碎，越碎越无法聚合」——"
            "而这恰好与「越远越需要聚合」相反。</strong>",
            "<strong>实践中的解法是：子流形卷积做主体，"
            "间隔插入少量<em>会膨胀的</em>算子。</strong>"
            "<em>最常见的是「带步长的常规稀疏卷积」（stride-2 下采样）——"
            "它把分辨率降一半，于是原本相距 3 个体素的两块在下一层就相邻了</em>。"
            "<strong>所以真实网络（SECOND、CenterPoint 的骨干）的结构是"
            "「若干子流形层 + 一次下采样」重复几轮</strong>，"
            "<em>而下采样的次数由「最大的物体要在多少层内连通」决定</em>。"
            "<strong>这就是这一层唯一需要人工设计的超参数。</strong>",
        ),
        H3("一个可以直接算的设计判据"),
        P("给定目标的最大内部间隙 $g$（体素数）与下采样次数 $k$，"
          "<strong>连通所需的条件是 $g \\le 2^k$</strong>（每次下采样把间隙折半）。"
          "<em>本课的标志分量之间最大间隙约 4 个体素（$r{=}0.2$ m 即 0.8 m），"
          "所以 $k\\ge2$ 就够——而这与真实网络普遍用 3–4 次下采样是一致的</em>。"),
    ])),

    # ============================================================== 5b
    ("downsample-tension", "下采样：连通性与定位精度直接冲突", "".join([
        P("上一节说下采样能把间隙折半。"
          "<strong>而它同时把分辨率变粗，于是量化误差按 $2^k$ 增长。</strong>"
          "把两件事放在一张表上，会看到一个硬冲突。"),
        P("参照量：模块 05 会算出<strong>一块 $0.8\\times0.1\\times0.8$ m 的限速牌，"
          "沿最薄轴达到 IoU=0.5 只允许 0.0333 m 的平移误差</strong>。"),
        TABLE(["下采样次数 $k$", "分辨率 $r$", "量化误差上界 $r\\sqrt3/2$",
               "相对允许误差", "标志内部间隙（体素）"], [
            ["0", "0.20 m", "0.1732 m", "<strong>5.2×</strong>", "4.00"],
            ["1", "0.40 m", "0.3464 m", "10.4×", "2.00"],
            ["<strong>2</strong>", "<strong>0.80 m</strong>",
             "<strong>0.6928 m</strong>", "<strong>20.8×</strong>",
             "<strong>1.00 ← 连通</strong>"],
            ["3", "1.60 m", "1.3856 m", "41.6×", "0.50"],
        ]),
        CALLOUT("danger",
                "<strong>注意 $k{=}0$ 那一行：即使完全不下采样，"
                "$r{=}0.2$ m 的量化误差已经是允许误差的 5.2 倍。</strong>"
                "<em>而要让标志的两个分量连起来需要 $k\\ge2$（间隙 2.5 个体素），"
                "此时是 20.8 倍</em>。"
                "<strong>所以对又薄又小的目标，"
                "体素路线在<em>任何</em>分辨率上都无法同时满足「连通」与「IoU-0.5 的定位精度」。</strong>"),
        DUAL(
            "<strong>而正确的结论不是「体素路线不行」，是「这个评测口径不行」。</strong>"
            "<em>0.0333 m 的定位精度在 50 m 处对<strong>任何</strong>车载传感器都不可达"
            "（C72 模块 03 量到最好的补法在 50 m 处是 ±0.68 m）</em>。"
            "<strong>所以「IoU ≥ 0.5」这个从 2D 检测继承来的阈值，"
            "对薄目标在物理上是不可达的——它不是一个高标准，是一个错标准。</strong>",
            "<strong>这正是 nuScenes 用<em>中心距离</em>（0.5/1/2/4 m 四档）"
            "而不是 3D IoU 作为匹配判据的原因。</strong>"
            "<em>中心距离不含「三个乘子」，所以它对目标的尺寸与厚度不敏感</em>；"
            "<strong>而对交通标志这类目标，它是唯一物理上可达的口径。</strong>"
            "<em>模块 05 会把这个对比精确算出来，并给出「什么时候该用哪个口径」的判据。</em>"
            "<strong>而本节要留下的是这个因果链："
            "架构的分辨率选择 → 量化误差 → 评测口径的可达性。"
            "三者是同一个约束链上的三段，不能分开决定。</strong>",
        ),
    ])),

    # ============================================================== 6
    ("vfe", "格内怎么聚合：模块 02 的对称函数在这里复用", "".join([
        P("体素化之后，一个格子里可能有多个点（模块 01：$r{=}0.2$ m 时平均 4.8 个）。"
          "<strong>把它们变成一个特征向量，需要的正是模块 02 那套对称函数。</strong>"),
        TABLE(["编码方式", "怎么做", "性质"], [
            ["<strong>二值占据</strong>", "非空就是 1",
             "最简单；<em>丢掉格内的全部信息</em>"],
            ["<strong>手工统计</strong>",
             "点数、均值、方差、最大 $z$…",
             "便宜、可解释；<strong>而「点数」这一项要小心</strong>——"
             "<em>模块 01 量过它主要由距离决定</em>"],
            ["<strong>VFE（VoxelNet）</strong>",
             "格内点做逐点 MLP，再 max-pool",
             "<strong>就是一个作用在格内的小 PointNet</strong>；"
             "<em>所以模块 02 的临界点集结论在这里同样成立</em>"],
            ["<strong>PFN（PointPillars）</strong>",
             "同上，但作用在整根柱子上",
             "柱内点更多（模块 01：$0.16$ m 柱平均 3.44 点），"
             "<em>而 $z$ 只作为特征而不是维度</em>"],
        ]),
        DUAL(
            "<strong>VFE 用 max-pool 而不是 mean，理由和模块 02 完全相同：</strong>"
            "<em>格内点数由距离决定（近处一个格子可能几十个点，远处一个），"
            "而 max 对点数的敏感性远小于 sum、且对密度分布免疫</em>。"
            "<strong>而模块 02 的临界点集结论在这里变成："
            "一个格子的特征实际上只由格内少数几个极值点决定。</strong>",
            "<strong>一个实践上的坑：<code>max_num_points_per_voxel</code> 这个上限。</strong>"
            "<em>它必须设成「足够覆盖近处最密的格子」，"
              "而模块 00 练习 1 的 <code>counts.max()</code> 直接给出这个数</em>。"
            "<strong>设小了会静默丢点，而且丢的是近处最密的格子里的点</strong>——"
            "<em>幸运的是 max-pool 对此相对不敏感（丢掉的大概率是非临界点），"
            "这也是「架构选择恰好兼容工程妥协」的又一个例子</em>。"
            "<strong>但如果编码里含「点数」这一项，那么截断就直接篡改了它。</strong>",
        ),
    ])),

    # ============================================================== 6b
    ("implementations", "三种实现方式，以及它们的访存行为", "".join([
        P("同一个稀疏卷积可以用三种方式实现，"
          "<strong>而它们的 FLOP 数相同、墙钟时间差很多</strong>——"
          "差别全在访存。"),
        TABLE(["实现", "怎么做", "访存特点", "什么时候好"], [
            ["<strong>gather–scatter</strong>",
             "按规则把输入行 gather 成连续矩阵 → 一次 GEMM → scatter 回去",
             "<strong>要物化中间矩阵</strong>："
             "$\\text{rules}\\times C_{in}$ 个 float",
             "规则密度低（散开的活跃集，第 1b 节的 1.33）"],
            ["<strong>implicit GEMM</strong>",
             "不物化中间矩阵，在 GEMM 的内层循环里按规则取数",
             "访存不连续，但<strong>省掉一次全量读写</strong>",
             "规则密度高（实心块，22.75）"],
            ["<strong>逐偏移 GEMM</strong>",
             "对 27 个偏移各做一次小 GEMM，只用该偏移的规则",
             "27 次小 GEMM；<em>每次的规则数差异很大</em>",
             "实现最简单，spconv 早期版本用它"],
        ]),
        DUAL(
            "<strong>gather–scatter 的中间矩阵大小可以直接算：</strong>"
            "<em>本课的输入（$M{=}10{,}306$、规则密度约 1.3、$C_{in}{=}64$）"
            "是 $10{,}306\\times1.3\\times64\\times4$ B ≈ 3.4 MB</em>——"
            "<strong>还能放进缓存</strong>。"
            "<em>而在实心块那种规则密度 22.75 的情形下，"
            "同样的 $M$ 会给出 60 MB 的中间矩阵——那就必须走 implicit GEMM 了。</em>",
            "<strong>所以「哪种实现更快」取决于活跃集的形状，而形状随层数变化"
            "（第 2 节：越深越成片）。</strong>"
            "<em>这就是为什么成熟库（spconv 2.x、MinkowskiEngine）会"
              "<strong>按层自动选择算法</strong>，并把规则表缓存起来</em>。"
            "<strong>而对本课的读者，实用的结论只有一条："
            "不要自己实现稀疏卷积。</strong>"
            "<em>本课从零实现的是「稀疏卷积的语义」（练习 1–2），不是它的高效实现</em>——"
            "<strong>与 C71 模块 04 对受限解码的态度完全一样。</strong>",
        ),
    ])),

    # ============================================================== 7
    ("checklist", "本模块的清单", "".join([
        OL([
            "<strong>逐层打印活跃位置数</strong>（第 3 节）——"
            "<em>这是判断「用的是哪一种稀疏卷积」以及「稀疏性还剩多少」的唯一直接手段</em>",
            "<strong>不要只报第一层的 FLOPs</strong>："
            "常规稀疏卷积 4 层后的优势从 465.7× 掉到 8.86×",
            "<strong>算一次目标的连通分量</strong>（第 5 节）——"
            "<em>如果关心的目标碎成多块，纯子流形卷积在架构上就做不到聚合它们</em>",
            "<strong>下采样次数由 $g \\le 2^k$ 定</strong>（第 5 节），"
            "其中 $g$ 是目标内部的最大间隙（以体素计）",
            "<strong>但要同时检查那个 $k$ 下的量化误差是否还在预算内</strong>（第 5b 节）——"
            "<em>对薄目标两者会直接冲突，而此时该换的是评测口径而不是分辨率</em>",
            "<strong>不要自己实现稀疏卷积</strong>（第 6b 节）："
            "用 spconv / MinkowskiEngine，它们会按层自动选算法并缓存规则表",
            "<strong>格内编码优先 max 而不是 mean/点数</strong>（第 6 节），"
            "理由与模块 02 相同",
            "<strong><code>max_num_points_per_voxel</code> 用实测的 "
            "<code>counts.max()</code> 设</strong>（模块 00 练习 1），"
            "<em>并且如果编码里含「点数」，必须确认没有被截断</em>",
        ]),
        CALLOUT("paper",
                "<strong>如果只做一条，做第 3 条。</strong>"
                "<em>「目标碎成几块」这个数不需要训练、不需要标签之外的任何东西，"
                "而它直接告诉你「这个架构能不能表示这个目标」</em>。"
                "<strong>而它在 TSR 上给出的答案是明确的："
                "26 个体素、5 个分量、0 个地面连接——"
                "所以纯子流形骨干对交通标志是不够的。</strong>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 03 · 体素化与稀疏卷积

这个 notebook 把稀疏卷积的**语义**从零实现一遍（不是高效实现），然后量四件事：

1. **规则表的规模**，以及一个反直觉性质：
   越散开的活跃集**膨胀越快**（22.05×）而**规则越少**（1.33 条/活跃）——两者的积被 27 框住。
2. **常规稀疏卷积 4 层膨胀 52.54×**，占用率 0.215% → **11.28%**。
3. **FLOPs 优势从 465.7× 掉到 8.86×** —— 而这个 53 倍的落差正是膨胀率。
4. **子流形的真实代价**：30 m 处那块标志的 15 个体素被切成 **2 个分量**（间隙 0.50 m），
   而分量里的地面体素恒为 **0**（车却有 726 个）——纯子流形卷积下它们永远不通信。

> 心智模型：**稀疏卷积的全部收益是「占用率的倒数」，
> 所以任何让占用率上升的东西都在直接吃掉收益。**"""),

    md("""## 0 · 环境与一帧点云"""),

    code("""import numpy as np
from collections import deque

print('numpy', np.__version__)

# ── 复用模块 01 的环扫模型（这里只保留必要的部分）──
LIDAR_H, N_BEAM, FOV_DEG, AZ_DEG = 1.8, 64, (-24.9, 2.0), 0.2
EL = np.deg2rad(np.linspace(FOV_DEG[0], FOV_DEG[1], N_BEAM))

BOXES = []
for cx, cy in [(20, -3), (35, 3), (60, -3), (80, 3)]:
    BOXES.append((np.array([cx-2.25, cy-0.95, 0.0]),
                  np.array([cx+2.25, cy+0.95, 1.5]), 1))          # 车
for cx, cy in [(30, -5.5), (55, 5.5), (75, -5.5)]:
    BOXES.append((np.array([cx-0.05, cy-0.40, 1.80]),
                  np.array([cx+0.05, cy+0.40, 2.60]), 2))          # 标志（薄）

def lidar_scan(az_range=(-180., 180.), max_range=120.):
    o = np.array([0., 0., LIDAR_H])
    az = np.deg2rad(np.arange(az_range[0], az_range[1], AZ_DEG))
    A, E = np.meshgrid(az, EL, indexing='ij')
    A, E = A.ravel(), E.ravel()
    dirs = np.column_stack([np.cos(E)*np.cos(A), np.cos(E)*np.sin(A), np.sin(E)])
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (0.0 - o[2]) / dirs[:, 2]
    t = np.where((t > 0) & np.isfinite(t), t, np.inf)
    lab = np.zeros(len(dirs), dtype=np.int64)
    for lo, hi, kind in BOXES:
        with np.errstate(divide='ignore', invalid='ignore'):
            t1, t2 = (lo - o) / dirs, (hi - o) / dirs
        tmin = np.nanmax(np.minimum(t1, t2), axis=1)
        tmax = np.nanmin(np.maximum(t1, t2), axis=1)
        tb = np.where(tmax >= np.maximum(tmin, 0.0), np.maximum(tmin, 0.0), np.inf)
        closer = tb < t
        t = np.where(closer, tb, t); lab = np.where(closer, kind, lab)
    ok = np.isfinite(t) & (t > 0) & (t < max_range)
    return o + dirs[ok] * t[ok, None], lab[ok]

PTS_ALL, LAB_ALL = lidar_scan()

# ── 裁到常见的检测范围 ──
LO = np.array([0., -40., -3.])
HI = np.array([80.,  40.,  3.])
R = 0.2
keep = np.all((PTS_ALL >= LO) & (PTS_ALL < HI), axis=1)
PTS, LAB = PTS_ALL[keep], LAB_ALL[keep]

NX, NY, NZ = [int(round((HI[i] - LO[i]) / R)) for i in range(3)]
TOT = NX * NY * NZ
print(f'检测范围 {HI-LO} m, r={R} m -> 网格 {NX}×{NY}×{NZ} = {TOT:,}')
print(f'点数 {len(PTS):,}（其中标志点 {int((LAB==2).sum())}）')"""),

    md("""## 1 · 稀疏张量：坐标 → 一维键 → 哈希

用「一维键」代替三维坐标，`np.unique` / `np.isin` 就够了（真实实现用哈希表）。"""),

    code("""def to_key(ijk):
    return (ijk[:, 0] * NY + ijk[:, 1]) * NZ + ijk[:, 2]

def to_ijk(keys):
    i = keys // (NY * NZ); rem = keys % (NY * NZ)
    return np.column_stack([i, rem // NZ, rem % NZ])

IJK = np.floor((PTS - LO) / R).astype(np.int64)
KEY = to_key(IJK)
ACTIVE = np.unique(KEY)

print(f'非空体素 {len(ACTIVE):,} / {TOT:,} = {100*len(ACTIVE)/TOT:.4f}%')
print(f'平均每格 {len(PTS)/len(ACTIVE):.2f} 点')

# 键与坐标可逆
assert np.array_equal(to_key(to_ijk(ACTIVE)), ACTIVE)
print('✅ 一维键与三维坐标可逆')

# 稀疏张量的内存 vs 密集
C = 64
sparse_mb = len(ACTIVE) * (3 * 4 + C * 4) / 1e6
dense_mb = TOT * C * 4 / 1e6
print(f'\\n特征维 C={C} 时：')
print(f'  稀疏张量（坐标+特征）{sparse_mb:8.2f} MB')
print(f'  密集张量              {dense_mb:8.2f} MB  -> **{dense_mb/sparse_mb:.0f}× 更多**')
assert dense_mb / sparse_mb > 100"""),

    md("""## 1b · 规则表：真实开销，以及膨胀率与它的反向关系"""),

    code("""OFFSETS = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]

def dilate(keys):
    '''常规稀疏卷积的输出位置：活跃集按 3³ 邻域膨胀。'''
    ijk = to_ijk(keys)
    out = []
    for di, dj, dk in OFFSETS:
        a = ijk + np.array([di, dj, dk])
        m = np.all((a >= 0) & (a < np.array([NX, NY, NZ])), axis=1)
        out.append(to_key(a[m]))
    return np.unique(np.concatenate(out))

def rulebook_size(keys):
    '''子流形卷积的规则条目数：(o, δ) 使得 o 与 o−δ 都活跃。'''
    ijk = to_ijk(keys)
    total = 0
    for di, dj, dk in OFFSETS:
        a = ijk - np.array([di, dj, dk])
        m = np.all((a >= 0) & (a < np.array([NX, NY, NZ])), axis=1)
        total += int(np.isin(to_key(a[m]), keys).sum())
    return total

# 五种活跃集形状（在同一个网格里构造）
def mk_shape(kind):
    r = np.random.default_rng(0)
    if kind == 'scatter':
        a = np.column_stack([r.integers(0, 60, 3000), r.integers(0, 60, 3000),
                             r.integers(0, 30, 3000)])
    elif kind == 'line':
        a = np.column_stack([np.full(50, 30), np.full(50, 30), np.arange(2, 52) % NZ])
    elif kind == 'sheet':
        xs, zs = np.meshgrid(np.arange(25, 35), np.arange(5, 15))
        a = np.column_stack([xs.ravel(), np.full(xs.size, 30), zs.ravel()])
    elif kind == 'block':
        gx, gy, gz = np.meshgrid(np.arange(20, 32), np.arange(20, 32), np.arange(5, 17))
        a = np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()])
    elif kind == 'plane':
        gx, gy = np.meshgrid(np.arange(0, 60), np.arange(0, 60))
        a = np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, 8)])
    return np.unique(to_key(a))

print(f\"{'形状':>10s} {'活跃数':>8s} {'膨胀率':>8s} {'规则/活跃':>10s} {'两者之积':>9s}\")
shapes = {}
for kind in ['scatter', 'line', 'sheet', 'plane', 'block']:
    a = mk_shape(kind)
    dr = len(dilate(a)) / len(a)
    rd = rulebook_size(a) / len(a)
    shapes[kind] = (dr, rd)
    print(f'{kind:>10s} {len(a):8,} {dr:7.2f}× {rd:9.2f} {dr*rd:8.1f}')

# ① 排序：越散开膨胀越快
assert shapes['scatter'][0] > shapes['line'][0] > shapes['sheet'][0] > shapes['block'][0]
print(f'\\n膨胀率排序: 散开 {shapes["scatter"][0]:.2f}× > 直线 '
      f'{shapes["line"][0]:.2f}× > 薄片 {shapes["sheet"][0]:.2f}× > '
      f'实心块 {shapes["block"][0]:.2f}×')

# ② 规则密度的排序**相反**
assert shapes['scatter'][1] < shapes['line'][1] < shapes['sheet'][1] < shapes['block'][1]
print(f'规则密度排序（相反）: 散开 {shapes["scatter"][1]:.2f} < ... < '
      f'实心块 {shapes["block"][1]:.2f}')

# ③ 两者之积被核大小框住
prods = [dr * rd for dr, rd in shapes.values()]
print(f'两者之积: {min(prods):.1f} – {max(prods):.1f}（核大小 = 27）')
assert 20 < min(prods) and max(prods) < 60, prods
print('✅ 它们从两端数的是同一批「邻接关系」，所以积被 27 大致框住')

# ④ 用 M×27 估算会高估多少
real = rulebook_size(ACTIVE)
print(f'\\n真实点云: 规则条目 {real:,}，而 M×27 = {len(ACTIVE)*27:,}'
      f'  → **高估 {len(ACTIVE)*27/real:.1f} 倍**')
assert len(ACTIVE) * 27 / real > 2
print('   → 用 M×27 估稀疏卷积的乘加次数是错的；要先算规则表')"""),

    md("""## 2 · 常规稀疏卷积的膨胀"""),

    code("""print(f\"{'层':>3s} {'常规稀疏 非空':>14s} {'占用率':>10s} {'累计膨胀':>10s} {'子流形':>10s}\")
cur = ACTIVE
grow = [1.0]
print(f'{0:3d} {len(cur):14,} {100*len(cur)/TOT:9.4f}% {1.0:9.2f}× {len(ACTIVE):10,}')
for L in range(1, 5):
    cur = dilate(cur)
    grow.append(len(cur) / len(ACTIVE))
    print(f'{L:3d} {len(cur):14,} {100*len(cur)/TOT:9.4f}% '
          f'{grow[-1]:9.2f}× {len(ACTIVE):10,}')

FINAL_ACTIVE = len(cur)
assert grow[-1] > 40, f'4 层后累计膨胀应超过 40 倍，实测 {grow[-1]:.1f}'
assert len(cur) / TOT > 0.10, '占用率应当涨到 10% 以上'
print(f'\\n✅ 4 层后累计膨胀 {grow[-1]:.2f}×，占用率 '
      f'{100*len(ACTIVE)/TOT:.4f}% → {100*len(cur)/TOT:.4f}%')
print('   第一层就膨胀 %.2f×（不是 27×，因为相邻活跃体素共享邻居）' % grow[1])
print('   而新增的位置对应的输入全是空的 —— 相当于在空气里插值出「虚假的占据」')"""),

    md("""## 3 · FLOPs 优势的消失"""),

    code("""CIN = COUT = 64

def flops(n_active_or_rules):
    return n_active_or_rules * CIN * COUT

print(f\"{'方案':>22s} {'位置/规则数':>13s} {'GFLOP':>10s} {'相对密集':>11s}\")
dense = flops(TOT * 27)
sub = flops(rulebook_size(ACTIVE))
reg4 = flops(FINAL_ACTIVE * 27)
rows = [('密集卷积', TOT * 27, dense),
        ('子流形（按规则表）', rulebook_size(ACTIVE), sub),
        ('常规稀疏（4 层后）', FINAL_ACTIVE * 27, reg4)]
for tag, n, f in rows:
    print(f'{tag:>22s} {n:13,} {f/1e9:9.3f} {dense/f:10.1f}×')

assert dense / sub > 300, f'子流形的优势应超过 300 倍，实测 {dense/sub:.0f}'
assert dense / reg4 < 20, f'常规稀疏 4 层后优势应掉到 20 倍以内，实测 {dense/reg4:.0f}'
print(f'\\n✅ 子流形 {dense/sub:.1f}× → 常规稀疏 4 层后只剩 {dense/reg4:.2f}×')
print(f'   落差 {(dense/sub)/(dense/reg4):.0f} 倍 —— 与累计膨胀率 {grow[-1]:.1f}× 同一量级')
print('   → **膨胀率与 FLOPs 收益是同一个数的两种说法**')"""),

    md("""## 4–5 · 子流形卷积，与它的真实代价

活跃集恒定 → FLOPs 恒定。**但信息只能在连通分量内传播。**"""),

    code("""def submanifold_conv(keys, feats, W):
    '''子流形稀疏卷积：输出位置 = 输入位置。W: (27, Cin, Cout)。'''
    ijk = to_ijk(keys)
    pos = {int(k): i for i, k in enumerate(keys)}
    out = np.zeros((len(keys), W.shape[2]))
    for oi, (di, dj, dk) in enumerate(OFFSETS):
        src = ijk - np.array([di, dj, dk])
        m = np.all((src >= 0) & (src < np.array([NX, NY, NZ])), axis=1)
        sk = to_key(src[m])
        rows = np.where(m)[0]
        for r_out, k_in in zip(rows, sk):
            j = pos.get(int(k_in))
            if j is not None:
                out[r_out] += feats[j] @ W[oi]
    return out

# 小规模验证：活跃集不变
rng = np.random.default_rng(0)
SMALL = ACTIVE[:400]
F0 = rng.normal(size=(len(SMALL), 8))
Wc = rng.normal(size=(27, 8, 8)) * 0.1
F1 = submanifold_conv(SMALL, F0, Wc)
assert F1.shape == (len(SMALL), 8), '输出行数 = 输入行数（活跃集不变）'
print(f'✅ 子流形卷积：{len(SMALL)} 个活跃位置进，{len(F1)} 个出（活跃集恒定）')

# ── 连通分量：信息能传到哪 ──
def components(keys, seeds=None):
    S = set(int(k) for k in keys)
    nb_off = [o for o in OFFSETS if o != (0, 0, 0)]
    seen, comps = set(), []
    targets = S if seeds is None else set(int(s) for s in seeds)
    for st in sorted(targets):
        if st in seen:
            continue
        q, comp = deque([st]), {st}
        seen.add(st)
        while q:
            u = q.popleft()
            iu = to_ijk(np.array([u]))[0]
            for di, dj, dk in nb_off:
                v_ijk = iu + np.array([di, dj, dk])
                if np.any(v_ijk < 0) or np.any(v_ijk >= np.array([NX, NY, NZ])):
                    continue
                v = int(to_key(v_ijk[None])[0])
                if v in S and v not in seen:
                    seen.add(v); comp.add(v); q.append(v)
        comps.append(comp)
    return comps

# ── 按**实例**分析，而不是把所有标志混在一起 ──
def instance_voxels(lo, hi):
    m = np.all((PTS >= lo - 1e-9) & (PTS <= hi + 1e-9), axis=1)
    return np.unique(KEY[m]), int(m.sum())

def instance_report(lo, hi):
    vox, npt = instance_voxels(lo, hi)
    if len(vox) == 0:
        return None
    vset = set(int(v) for v in vox)
    cs = [c for c in components(ACTIVE, seeds=vox) if c & vset]
    ground = set(np.unique(KEY[LAB == 0]).tolist())
    if len(cs) > 1:
        ctr = [to_ijk(np.array(sorted(c))).mean(0) for c in cs]
        gap = max(float(np.linalg.norm(ctr[a] - ctr[b]))
                  for a in range(len(ctr)) for b in range(a + 1, len(ctr)))
    else:
        gap = 1.0
    return {'n_pts': npt, 'n_vox': len(vox), 'n_comp': len(cs),
            'gap_vox': gap, 'gap_m': gap * R,
            'ground_in_comp': sum(len(c & ground) for c in cs),
            'sizes': sorted((len(c) for c in cs), reverse=True)}

print(f"{'目标':>10s} {'点':>6s} {'体素':>6s} {'分量':>5s} "
      f"{'内部间隙':>16s} {'分量内地面体素':>15s}")
reports = {}
for bi, (lo, hi, kind) in enumerate(BOXES):
    r_ = instance_report(lo, hi)
    if r_ is None:
        continue
    name = {1: '车', 2: '标志'}[kind]
    reports[(name, bi)] = r_
    print(f'{name+" #"+str(bi):>10s} {r_["n_pts"]:6d} {r_["n_vox"]:6d} '
          f'{r_["n_comp"]:5d} {r_["gap_vox"]:8.1f} 体素({r_["gap_m"]:4.2f}m) '
          f'{r_["ground_in_comp"]:15d}')

signs = [v for (n, _), v in reports.items() if n == '标志']
cars = [v for (n, _), v in reports.items() if n == '车']

# ① 标志悬空：分量里没有地面体素
assert all(s['ground_in_comp'] == 0 for s in signs), '标志应当与地面不连通'
# ② 车接地：分量里含大量地面体素
assert any(c['ground_in_comp'] > 50 for c in cars), '车应当与地面连通（轮胎接地）'
print()
print('✅ **车与地面连通（轮胎接地），而标志悬空、与地面完全不连通**')
print('   → 子流形卷积可以在车与地面之间传信息，但对标志不行')
print('   → 而「离地多高」正是区分标志与地面标记的唯一线索（模块 01 第 4 节）')

# ③ 标志自身还碎成多块
multi = [s for s in signs if s['n_comp'] > 1]
assert len(multi) >= 2, '至少两块标志应当自身碎成多个分量'
GAP_SIGN = max(s['gap_vox'] for s in signs)
print()
print(f'而标志自身也碎成多块：' +
      '，'.join(f'{s["n_vox"]} 体素 → {s["n_comp"]} 分量 {s["sizes"]}'
                for s in signs))
print(f'   内部最大间隙 {GAP_SIGN:.1f} 个体素 = {GAP_SIGN*R:.2f} m')
print('   → 纯子流形卷积下，同一块标志的两半也不交换信息')
"""),

    md("""## 5b · 下采样：连通性与定位精度直接冲突"""),

    code("""def iou3d(size, delta):
    s = np.asarray(size, float); d = np.abs(np.asarray(delta, float))
    inter = np.prod(np.maximum(s - d, 0.0)); vol = np.prod(s)
    den = 2 * vol - inter
    return inter / den if den > 0 else 0.0

SIGN_SIZE = (0.8, 0.1, 0.8)
thin = int(np.argmin(SIGN_SIZE))
lo, hi = 0.0, 5.0
for _ in range(60):
    mid = (lo + hi) / 2
    d = [0., 0., 0.]; d[thin] = mid
    if iou3d(SIGN_SIZE, d) >= 0.5:
        lo = mid
    else:
        hi = mid
ALLOW = lo
print(f'限速牌 {SIGN_SIZE}：达到 IoU=0.5，沿最薄轴允许平移 {ALLOW:.4f} m\\n')

# 标志**内部**分量之间的最大间隙（第 4–5 节按实例算出的 GAP_SIGN）
GAP0 = GAP_SIGN
print(f'单块标志内部分量之间的最大间隙 = {GAP0:.1f} 个体素'
      f'（r={R} m，即 {GAP0*R:.2f} m）')
print()

print(f\"{'k':>3s} {'分辨率 r':>10s} {'量化误差上界':>13s} {'相对允许误差':>13s} {'间隙(体素)':>11s}\")
for k in range(0, 4):
    rk = R * 2 ** k
    ub = rk * np.sqrt(3) / 2
    gk = GAP0 / 2 ** k
    tag = '  ← 连通' if gk <= 1.0 else ''
    print(f'{k:3d} {rk:9.2f}m {ub:12.4f}m {ub/ALLOW:12.1f}× {gk:10.2f}{tag}')

# 即使 k=0，量化误差已超预算
assert R * np.sqrt(3) / 2 > ALLOW, 'k=0 时量化误差就已超过允许误差'
print(f'\\n✅ 即使不下采样（r={R} m），量化误差 {R*np.sqrt(3)/2:.4f} m '
      f'已是允许误差的 {R*np.sqrt(3)/2/ALLOW:.1f} 倍')
k_need = int(np.ceil(np.log2(max(GAP0, 1.0))))
print(f'   而连通需要 k≈{k_need}，此时是 '
      f'{R*2**k_need*np.sqrt(3)/2/ALLOW:.1f} 倍')
print('   → **对薄目标，体素路线在任何分辨率上都无法同时满足两者**')
print('   → 而 0.0333 m 在 50 m 处对任何车载传感器都不可达（C72：最好 ±0.68 m）')
print('     所以该换的是**评测口径**，不是分辨率（模块 05）')"""),

    md("""## 6 · 格内特征编码：模块 02 的对称函数复用"""),

    code("""def voxel_encode(pts, keys, kind='max', max_pts=32):
    '''把每个格子里的点编码成一个特征向量。'''
    order = np.argsort(keys, kind='stable')
    kk, pp = keys[order], pts[order]
    uniq, start, counts = np.unique(kk, return_index=True, return_counts=True)
    feats, truncated = [], 0
    for s, c in zip(start, counts):
        blk = pp[s:s + min(c, max_pts)]
        if c > max_pts:
            truncated += 1
        rel = blk - blk.mean(0)                      # 相对格心的偏移
        x = np.column_stack([blk, rel])
        feats.append({'max': x.max(0), 'mean': x.mean(0),
                      'binary': np.ones(x.shape[1]),
                      'count': np.full(x.shape[1], len(blk))}[kind])
    return uniq, np.array(feats), truncated

print(f'格内点数分布: 平均 {len(PTS)/len(ACTIVE):.2f}，'
      f'最多 {np.bincount(np.unique(KEY, return_inverse=True)[1]).max()}')
for kind in ['max', 'mean']:
    u, f, tr = voxel_encode(PTS, KEY, kind)
    print(f'  {kind:>6s} 编码: {f.shape}，截断的格子 {tr}')
    assert len(u) == len(ACTIVE)

# max_num_points 设小了会截断，而截断影响哪种编码
mx = int(np.bincount(np.unique(KEY, return_inverse=True)[1]).max())
u1, f_max_full, _ = voxel_encode(PTS, KEY, 'max', max_pts=mx)
u2, f_max_cut, tr = voxel_encode(PTS, KEY, 'max', max_pts=4)
u3, f_cnt_full, _ = voxel_encode(PTS, KEY, 'count', max_pts=mx)
u4, f_cnt_cut, _ = voxel_encode(PTS, KEY, 'count', max_pts=4)
d_max = np.abs(f_max_full - f_max_cut).max()
d_cnt = np.abs(f_cnt_full - f_cnt_cut).max()
print(f'\\nmax_num_points 从 {mx} 降到 4（截断 {tr} 个格子）：')
print(f'  max 编码的最大变化   = {d_max:.4f}')
print(f'  count 编码的最大变化 = {d_cnt:.1f}')
assert d_cnt > d_max * 5, 'count 编码对截断远比 max 敏感'
print('✅ **max 编码对截断相对不敏感，而含「点数」的编码被直接篡改**')
print('   （max 丢掉的大概率是非临界点 —— 模块 02 第 3 节）')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| 稀疏 vs 密集内存（C=64） | **445×** |
| 规则表 vs $M\\times27$ | 真实点云上 $M\\times27$ **高估 2 倍以上** |
| 膨胀率取决于形状 | 散开 **22.05×** > 直线 9.36× > 薄片 4.32× > 实心块 1.59× |
| 规则密度（**反向**） | 散开 1.33 < ... < 实心块 22.75；两者之积被 27 框住 |
| 常规稀疏 4 层 | 累计膨胀 **52×**，占用率 0.215% → **11.28%** |
| FLOPs 优势 | 子流形 **465×** → 常规 4 层后只剩 **8.9×** |
| **子流形的代价** | 标志 15 体素 → **2 个分量**（间隙 0.50 m）；分量内地面体素 **0** |
| **下采样的冲突** | 即使 $k{=}0$，量化误差已是 IoU-0.5 允许误差的 **5.2×** |
| 格内编码 | max 对截断不敏感；**含「点数」的编码被直接篡改** |"""),

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：两种稀疏卷积的输出位置

实现 `output_positions(keys, mode)`，`mode` 取 `'submanifold'` / `'regular'`，
返回该层的输出活跃位置（升序去重的一维键）。

然后实现 `conv_cost(keys_in, keys_out)`：返回
`(规则条目数, 乘加次数)`（$C_{in}=C_{out}=64$）。"""),

    code("""def output_positions(keys, mode):
    \"\"\"返回输出活跃位置（一维键，升序去重）。\"\"\"
    # TODO
    raise NotImplementedError

def conv_cost(keys_in, keys_out, cin=64, cout=64):
    \"\"\"返回 (规则条目数, 乘加次数)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
SUB = output_positions(ACTIVE, 'submanifold')
REG = output_positions(ACTIVE, 'regular')
assert np.array_equal(SUB, np.unique(ACTIVE)), '子流形的输出位置 = 输入位置'
assert len(REG) > len(SUB) * 5, f'常规应当明显膨胀（{len(REG)} vs {len(SUB)}）'
assert np.array_equal(REG, dilate(ACTIVE))
print(f'子流形: {len(SUB):,} 个输出位置（= 输入）')
print(f'常规  : {len(REG):,} 个输出位置（膨胀 {len(REG)/len(SUB):.2f}×）')

r_sub, m_sub = conv_cost(ACTIVE, SUB)
r_reg, m_reg = conv_cost(ACTIVE, REG)
print(f'\\n{"方案":>8s} {"规则条目":>12s} {"乘加次数":>16s}')
print(f'{"子流形":>8s} {r_sub:12,} {m_sub:16,}')
print(f'{"常规":>8s} {r_reg:12,} {m_reg:16,}')

# 子流形的规则数与第 1b 节的独立实现一致
assert r_sub == rulebook_size(ACTIVE), (r_sub, rulebook_size(ACTIVE))
# 常规的规则数更多（输出位置更多）
assert r_reg > r_sub
# 乘加 = 规则 × Cin × Cout
assert m_sub == r_sub * 64 * 64
print('\\n✅ 练习 1 通过：**输出位置的集合就是两种稀疏卷积的唯一区别**')
print(f'   而它带来 {r_reg/r_sub:.1f} 倍的规则条目差')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def output_positions(keys, mode):
    keys = np.unique(np.asarray(keys))
    if mode == 'submanifold':
        return keys
    if mode == 'regular':
        return dilate(keys)
    raise ValueError(mode)

def conv_cost(keys_in, keys_out, cin=64, cout=64):
    keys_in = np.unique(np.asarray(keys_in))
    ijk_out = to_ijk(np.asarray(keys_out))
    rules = 0
    for di, dj, dk in OFFSETS:
        src = ijk_out - np.array([di, dj, dk])
        m = np.all((src >= 0) & (src < np.array([NX, NY, NZ])), axis=1)
        rules += int(np.isin(to_key(src[m]), keys_in).sum())
    return rules, rules * cin * cout

assert np.array_equal(output_positions(ACTIVE, 'submanifold'), np.unique(ACTIVE))
assert conv_cost(ACTIVE, output_positions(ACTIVE, 'submanifold'))[0] == \\
       rulebook_size(ACTIVE)
print('✅ 参考答案 1 通过')
print('   注意规则是按**输出**位置枚举的：对每个输出 o 与偏移 δ，查 o−δ 是否在输入里。')
print('   所以输出位置变多（常规），规则就变多 —— 而这正是膨胀的成本形式。')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：逐层剖面

实现 `layer_profile(keys, n_layers, mode)`，返回一个 list，
每项是 dict：`{'layer', 'active', 'occupancy', 'growth', 'rules', 'gflop'}`。

**这是本模块最实用的诊断**——它一眼看出「稀疏性还剩多少」。"""),

    code("""def layer_profile(keys, n_layers, mode, total=None):
    \"\"\"返回每层的 dict(layer, active, occupancy, growth, rules, gflop)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
prof_sub = layer_profile(ACTIVE, 4, 'submanifold')
prof_reg = layer_profile(ACTIVE, 4, 'regular')
for p in (prof_sub, prof_reg):
    assert len(p) == 5, '应当含第 0 层（输入）'
    for row in p:
        assert set(row) == {'layer', 'active', 'occupancy', 'growth',
                            'rules', 'gflop'}

print(f\"{'层':>3s} | {'子流形 活跃':>11s} {'占用率':>9s} {'GFLOP':>8s} \"
      f\"| {'常规 活跃':>11s} {'占用率':>9s} {'GFLOP':>8s}\")
for a, b in zip(prof_sub, prof_reg):
    print(f'{a["layer"]:3d} | {a["active"]:11,} {100*a["occupancy"]:8.4f}% '
          f'{a["gflop"]:8.3f} | {b["active"]:11,} {100*b["occupancy"]:8.4f}% '
          f'{b["gflop"]:8.2f}')

# ① 子流形的活跃数与占用率恒定
assert len({r['active'] for r in prof_sub}) == 1, '子流形的活跃数必须恒定'
assert all(abs(r['growth'] - 1.0) < 1e-12 for r in prof_sub)

# ② 常规的活跃数单调增长
act = [r['active'] for r in prof_reg]
assert act == sorted(act) and act[-1] > 40 * act[0]
assert prof_reg[-1]['growth'] > 40

# ③ GFLOP 的比值就是规则数的比值
tot_sub = sum(r['gflop'] for r in prof_sub[1:])
tot_reg = sum(r['gflop'] for r in prof_reg[1:])
print(f'\\n4 层总计: 子流形 {tot_sub:.3f} GFLOP，常规 {tot_reg:.2f} GFLOP'
      f'  → **{tot_reg/tot_sub:.0f}× 差距**')
assert tot_reg / tot_sub > 20
print('✅ 练习 2 通过：逐层剖面是判断「用了哪种稀疏卷积」的唯一直接手段')
print(f'   而它是零成本的：只需要 len(coords)')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def layer_profile(keys, n_layers, mode, total=None):
    total = TOT if total is None else total
    keys = np.unique(np.asarray(keys))
    n0 = len(keys)
    out = [{'layer': 0, 'active': n0, 'occupancy': n0 / total,
            'growth': 1.0, 'rules': 0, 'gflop': 0.0}]
    cur = keys
    for L in range(1, n_layers + 1):
        nxt = output_positions(cur, mode)
        rules, macs = conv_cost(cur, nxt)
        out.append({'layer': L, 'active': len(nxt),
                    'occupancy': len(nxt) / total,
                    'growth': len(nxt) / n0,
                    'rules': rules, 'gflop': macs / 1e9})
        cur = nxt
    return out

ps = layer_profile(ACTIVE, 4, 'submanifold')
pr = layer_profile(ACTIVE, 4, 'regular')
assert len({r['active'] for r in ps}) == 1
assert pr[-1]['growth'] > 40
print('✅ 参考答案 2 通过')
print('   把这个函数接到真实网络上的办法：在每个稀疏卷积后打印 len(x.indices)。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：可聚合性检查

实现 `aggregability(keys, target_keys)`，返回 dict：

- `'n_target'` —— 目标占的体素数
- `'n_components'` —— 目标碎成几个连通分量（26-邻接）
- `'sizes'` —— 各分量大小（降序）
- `'max_gap_voxels'` —— 分量中心之间的最大距离（体素）
- `'submanifold_ok'` —— bool：`n_components == 1`
  （**只有为真时纯子流形卷积才能聚合这个目标**）
- `'k_needed'` —— 让它连通所需的下采样次数 $\\lceil\\log_2 g\\rceil$"""),

    code("""def aggregability(keys, target_keys):
    \"\"\"返回 dict(n_target, n_components, sizes, max_gap_voxels,
    submanifold_ok, k_needed)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# 按**实例**取体素 —— 把不同目标混在一起算连通性没有意义：
# 三块标志相距 30–75 m，它们之间的「间隙」是 225 个体素
SIGN_VOX, _ = instance_voxels(*BOXES[4][:2])      # 30 m 处那块标志
CAR_VOX,  _ = instance_voxels(*BOXES[0][:2])      # 20 m 处那辆车
a_sign = aggregability(ACTIVE, SIGN_VOX)
a_car = aggregability(ACTIVE, CAR_VOX)
for a in (a_sign, a_car):
    assert set(a) == {'n_target', 'n_components', 'sizes', 'max_gap_voxels',
                      'submanifold_ok', 'k_needed'}

print(f\"{'目标':>6s} {'体素数':>8s} {'分量数':>7s} {'最大间隙':>9s} \"
      f\"{'纯子流形可聚合':>15s} {'需要 k':>7s}\")
for tag, a in [('标志', a_sign), ('车', a_car)]:
    print(f'{tag:>6s} {a["n_target"]:8d} {a["n_components"]:7d} '
          f'{a["max_gap_voxels"]:8.1f} {str(a["submanifold_ok"]):>15s} '
          f'{a["k_needed"]:7d}')
    print(f'        各分量大小: {a["sizes"][:8]}')

# ① 标志碎成多块 -> 纯子流形不行
assert a_sign['n_components'] > 1 and a_sign['submanifold_ok'] is False
# ② 车的点多得多，分量应当更少（或至少不比标志多）
assert a_car['n_target'] > a_sign['n_target'] * 3
# ③ k_needed 与最大间隙一致
import math
assert a_sign['k_needed'] == math.ceil(math.log2(max(a_sign['max_gap_voxels'], 1.0)))

print(f'\\n✅ 练习 3 通过：标志碎成 {a_sign["n_components"]} 块 -> '
      f'纯子流形卷积**在架构上**无法聚合它')
print(f'   而这个检查不需要训练、不需要标签之外的任何东西')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
import math

def aggregability(keys, target_keys):
    target_keys = np.unique(np.asarray(target_keys))
    comps = components(keys, seeds=target_keys)
    # 只保留真正含目标体素的分量
    tset = set(int(k) for k in target_keys)
    comps = [c for c in comps if c & tset]
    sizes = sorted((len(c) for c in comps), reverse=True)
    if len(comps) <= 1:
        gap = 1.0
    else:
        ctrs = [to_ijk(np.array(sorted(c))).mean(0) for c in comps]
        gap = max(float(np.linalg.norm(ctrs[i] - ctrs[j]))
                  for i in range(len(ctrs)) for j in range(i + 1, len(ctrs)))
    return {'n_target': int(len(target_keys)),
            'n_components': int(len(comps)),
            'sizes': sizes,
            'max_gap_voxels': float(gap),
            'submanifold_ok': bool(len(comps) == 1),
            'k_needed': int(math.ceil(math.log2(max(gap, 1.0))))}

a = aggregability(ACTIVE, SIGN_VOX)
assert a['submanifold_ok'] is False and a['n_components'] > 1
print('✅ 参考答案 3 通过')
print('   注意 components() 的种子只给目标体素 —— 否则会把整个地面连通分量也算进来。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：下采样规划器

实现 `downsample_plan(gap_voxels, r0, allow_err_m, max_k=6)`，返回 dict：

- `'k_connect'` —— 让间隙 $\\le 1$ 所需的最小 $k$
- `'r_at_k'` —— 该 $k$ 下的分辨率
- `'quant_err'` —— 该分辨率的量化误差上界
- `'err_ratio'` —— `quant_err / allow_err_m`
- `'feasible'` —— bool：在 `k_connect` 处误差是否仍在预算内
- `'k_max_by_error'` —— 误差预算允许的最大 $k$（可能为 −1，表示连 $k{=}0$ 都超）"""),

    code("""def downsample_plan(gap_voxels, r0, allow_err_m, max_k=6):
    \"\"\"返回 dict(k_connect, r_at_k, quant_err, err_ratio, feasible,
    k_max_by_error)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# fixture：单块标志与单辆车的**内部**间隙（第 4–5 节按实例算过）
GAP_S = GAP_SIGN                                   # 标志内部最大间隙（体素）
_car_rep = instance_report(*BOXES[0][:2])
GAP_C = _car_rep['gap_vox']
print(f'单块标志内部间隙 {GAP_S:.1f} 体素（{GAP_S*R:.2f} m）；'
      f'单辆车 {GAP_C:.1f} 体素（{GAP_C*R:.2f} m）')
print()

# ① 标志：连通与精度直接冲突
p_sign = downsample_plan(GAP_S, R, ALLOW)
assert set(p_sign) == {'k_connect', 'r_at_k', 'quant_err', 'err_ratio',
                       'feasible', 'k_max_by_error'}
print('标志（允许误差 %.4f m）:' % ALLOW)
for k, v in p_sign.items():
    print(f'  {k:16s} = {v}')
assert p_sign['feasible'] is False, '标志的两个要求应当冲突'
assert p_sign['k_max_by_error'] == -1, \\
    f"连 k=0 都超预算（{R*np.sqrt(3)/2:.4f} > {ALLOW:.4f}），应当返回 -1"

# ② 车：预算宽松得多
lo2, hi2 = 0.0, 5.0
for _ in range(60):
    mid = (lo2 + hi2) / 2
    d = [0., 0., 0.]; d[1] = mid                       # 车的最短轴是宽 1.9m
    if iou3d((4.5, 1.9, 1.5), d) >= 0.5:
        lo2 = mid
    else:
        hi2 = mid
ALLOW_CAR = lo2
p_car = downsample_plan(GAP_C, R, ALLOW_CAR)
print(f'\\n车（允许误差 {ALLOW_CAR:.4f} m）:')
for k, v in p_car.items():
    print(f'  {k:16s} = {v}')
assert p_car['k_max_by_error'] >= 1, '车的预算应当允许至少一次下采样'
assert ALLOW_CAR > ALLOW * 10, '车的允许误差应当比标志大一个数量级'

# ③ 放宽预算 -> 变可行
p_relaxed = downsample_plan(GAP_S, R, 2.0)
assert p_relaxed['feasible'] is True
print(f'\\n把允许误差放宽到 2.0 m（中心距离口径）-> 可行 '
      f'{p_relaxed["feasible"]}，k={p_relaxed["k_connect"]}')
print('✅ 练习 4 通过：**同一个架构对不同目标的可行性完全不同**')
print('   而对薄目标，让它变可行的办法是换口径（IoU → 中心距离），不是换分辨率')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def downsample_plan(gap_voxels, r0, allow_err_m, max_k=6):
    k_conn = int(math.ceil(math.log2(max(gap_voxels, 1.0))))
    r_at = r0 * 2 ** k_conn
    qerr = r_at * np.sqrt(3) / 2
    # 误差预算允许的最大 k（k=0 都超时返回 -1）
    k_max = -1
    for k in range(0, max_k + 1):
        if (r0 * 2 ** k) * np.sqrt(3) / 2 <= allow_err_m + 1e-15:
            k_max = k
    return {'k_connect': k_conn, 'r_at_k': float(r_at),
            'quant_err': float(qerr),
            'err_ratio': float(qerr / allow_err_m),
            'feasible': bool(k_conn <= k_max),
            'k_max_by_error': int(k_max)}

assert downsample_plan(4.0, 0.2, 0.0333)['feasible'] is False
assert downsample_plan(4.0, 0.2, 2.0)['feasible'] is True
print('✅ 参考答案 4 通过')
print('   `k_max_by_error == -1` 是一个重要的返回值：')
print('   它表示「连最细的分辨率都超预算」，此时任何 k 都不行 ——')
print('   而这不是分辨率的问题，是**预算（评测口径）本身不可达**。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) spconv 里两种卷积的区别就是一个类名 ──
import spconv.pytorch as spconv
net = spconv.SparseSequential(
    spconv.SubMConv3d(64, 64, 3, indice_key='sub1'),   # 子流形：活跃集不变
    spconv.SubMConv3d(64, 64, 3, indice_key='sub1'),   # ← 复用规则表（关键！）
    spconv.SparseConv3d(64, 128, 3, stride=2),         # 常规 + 下采样：膨胀
    spconv.SubMConv3d(128, 128, 3, indice_key='sub2'),
)
#   ⚠️ `indice_key` 相同的 SubMConv3d 会**复用规则表** —— 忘了传它就每层重算一次，
#      而规则表的构建是这一层的主要开销之一（第 1b 节）。

# ── 2) 逐层剖面：一行接上（练习 2）──
def hook(m, i, o):
    print(f'{type(m).__name__:16s} active={o.indices.shape[0]:8d}')
for m in net.modules():
    if isinstance(m, (spconv.SubMConv3d, spconv.SparseConv3d)):
        m.register_forward_hook(hook)
#   ↑ 如果 active 快速增长，说明常规卷积用多了；如果它已到网格的百分之几十，
#     换密集卷积可能更快（实现更简单、访存更规则）

# ── 3) 体素化的两个上限，用实测值设（第 6 节 + 模块 00 练习 1）──
gen = spconv.utils.PointToVoxel(
    vsize_xyz=[0.2, 0.2, 0.2],
    coors_range_xyz=[0, -40, -3, 80, 40, 3],
    max_num_points_per_voxel=counts_max,   # ← 实测的 counts.max()
    max_num_voxels=int(active * 1.3),      # ← 实测的非空数 × 余量
)
#   ⚠️ 如果你的格内编码含「点数」这一项，截断会**直接篡改它**（第 6 节量到的差）

# ── 4) 下采样次数由目标的连通性定（练习 3–4）──
#   先算一次 aggregability(active_voxels, target_voxels)：
#   n_components > 1 就说明纯子流形骨干在架构上无法聚合这个目标。
#   而 CenterPoint / SECOND 的骨干普遍用 3–4 次 stride-2 —— 这个数不是随便定的。
```

> **落地顺序建议**：先加逐层剖面的 hook（一行，立刻告诉你稀疏性还剩多少），
> 再核对 `indice_key` 是否在同分辨率的层间复用，
> 最后才是用练习 3–4 检查你关心的目标在架构上能不能被聚合。"""),
]
