# -*- coding: utf-8 -*-
"""C57 模块 02 · 架构层面的解法：分辨率、多尺度与上下文。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（小目标的五个根因、IoU 位移敏感性）；C18/C53 的检测器结构基础"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_architecture_small.ipynb'),
    ("核心参考", "FPN (Lin 2017) · PANet (Liu 2018) · EfficientDet/BiFPN (Tan 2020) · Deformable DETR (Zhu 2021) · HRNet (Wang 2020)"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("fpn", "多尺度不是「多跑几遍」：FPN 解决的到底是什么矛盾", "".join([
        P("卷积主干有一个无法回避的内在矛盾：<strong>语义强度随深度增长，空间分辨率随深度衰减，而它们由同一条链路决定</strong>。ResNet-50 的四个阶段输出 C2/C3/C4/C5，stride 分别是 4/8/16/32，通道 256/512/1024/2048——通道数（语义容量）涨了 8 倍，格子数掉了 64 倍。"),
        P("把这个矛盾具体到 TSR：一个 60 cm 的限速牌在 50 米外、1920×1080/60°FOV 的相机上是 <strong>20 像素</strong>。它在 C5（stride 32）上占 20/32 = 0.625 个格子——注意，<em>不是「变小了」，是根本没有属于自己的格子</em>。它的响应被摊进一个覆盖 32×32 原图像素的 2048 维向量里，而那 32×32 里还有天空、树叶、灯杆、后面那辆车的车顶。<strong>要在这个向量里把「限速 60」和「限速 80」分开，是在要求网络做一件信息论上就不成立的事。</strong>"),
        TABLE(["朴素做法", "怎么做", "计算代价", "小目标语义", "小目标分辨率", "为什么被淘汰"], [
            ["<strong>图像金字塔</strong>", "把整张图缩放成 N 档，每档跑一遍网络", "<strong>N×（3–5 倍）</strong>", "✅ 强", "✅ 高", "延迟无法接受；训练也贵"],
            ["<strong>只用最后一层</strong>（Faster R-CNN 原版）", "在 C5 上预测所有尺度", "1×", "✅ 强", "❌ 0.6 个格子", "小目标根本没有表示"],
            ["<strong>只用浅层</strong>", "在 C2/C3 上预测", "1×（但特征图大，头很贵）", "❌ 弱（只有边缘纹理）", "✅ 高", "分不清标志和广告牌"],
            ["<strong>多层各自预测</strong>（SSD）", "C3/C4/C5 各接一个头，互不通信", "1.1×", "❌ 浅层语义弱", "✅ 高", "浅层没有语义，SSD 的小目标 AP 一直很差"],
            ["<strong>FPN</strong>", "横向连接 + 自顶向下融合", "<strong>1.2–1.5×</strong>", "✅ 每层都强", "✅ 每层都保留自身分辨率", "——（成为标配）"],
        ]),
        ASCII("""FPN：横向连接（1×1 统一到 C=256）+ 自顶向下（2× 最近邻上采样）+ 3×3 消混叠

  backbone                lateral 1x1              top-down            output 3x3
  ┌────────┐   stride 4   ┌────────┐              ┌────────┐         ┌────────┐
  │  C2    │──────────────▶│ 256ch  │──── (+) ────▶│  M2    │────────▶│  P2    │ stride 4
  │ 256ch  │               └────────┘      ▲       └────────┘         └────────┘
  └───┬────┘                               │ 2x up
      ▼        stride 8    ┌────────┐      │       ┌────────┐         ┌────────┐
  │  C3    │──────────────▶│ 256ch  │──── (+) ────▶│  M3    │────────▶│  P3    │ stride 8
  │ 512ch  │               └────────┘      ▲       └────────┘         └────────┘
  └───┬────┘                               │ 2x up
      ▼        stride 16   ┌────────┐      │       ┌────────┐         ┌────────┐
  │  C4    │──────────────▶│ 256ch  │──── (+) ────▶│  M4    │────────▶│  P4    │ stride 16
  │1024ch  │               └────────┘      ▲       └────────┘         └────────┘
  └───┬────┘                               │ 2x up
      ▼        stride 32   ┌────────┐      │       ┌────────┐         ┌────────┐
  │  C5    │──────────────▶│ 256ch  │──────┘       │  M5    │────────▶│  P5    │ stride 32
  │2048ch  │               └────────┘              └────────┘         └────────┘

  信息流：**只有一个方向** —— 语义从深层往浅层广播。
  浅层的精确定位信息**没有任何通路**能到达深层。这正是 PAN 要补的。"""),
        DUAL(
            "FPN 的直觉是「让每一层都既看得清、又看得懂」：分辨率由这一层自己提供，语义由上面那层送下来。横向连接的 1×1 卷积做两件事——把通道数统一到 256（否则没法相加），以及给浅层一次线性重组的机会；最后那个 3×3 是为了消除最近邻上采样带来的<em>混叠（aliasing）</em>，不加会在特征图上留下棋盘格。",
            "但要精确地说：<strong>FPN 并没有「在 stride 4 上跑一个深网络」，它只是把 stride 32 的语义插值到了 stride 4</strong>。P2 上的语义是<em>借来的</em>，它的空间分辨力上界仍受制于深层的 stride——一个 20 px 的目标在 C5 上被摊在 0.6 个格子里，这个信息损失<em>无法通过上采样恢复</em>。这就是为什么后来出现了两条完全不同的路线：① <span class=\"term\">HRNet</span> 全程保持高分辨率分支（不下采样再上采样，而是并行多分辨率互相交换）；② <span class=\"term\">Deformable DETR</span> 的多尺度稀疏采样（让 query 自己去高分辨率层取证据）。<em>理解「FPN 的语义是借来的」，才能理解这两条路线为什么存在。</em>",
        ),
        CALLOUT("intuition", "一句可迁移的判断：<strong>看到「小目标 AP 低」，先问「这个目标在它被分配到的那一层上占几个格子」</strong>。少于 1 个格子 = 网络在猜；1–2 个格子 = 能检出但框不准；4 个格子以上才谈得上正常学习。<em>这个数字是 <code>目标像素边长 / 该层 stride</code>，两秒就能算出来，却能直接决定接下来该改分辨率、改 stride 还是改分配。</em>"),
    ])),

    ("assign", "层级分配：k = k₀ + ⌊log₂(√(wh)/224)⌋，以及 TSR 分布下的层级负载", "".join([
        P("有了金字塔，下一个问题是：<strong>一个框该由哪一层负责？</strong> FPN 原文（以及 Mask R-CNN 的 RoIAlign）给出的规则是一条闭式公式："),
        MATH("k \\;=\\; \\left\\lfloor k_0 + \\log_2\\!\\left(\\frac{\\sqrt{wh}}{224}\\right) \\right\\rfloor, \\qquad k \\leftarrow \\mathrm{clip}(k,\\; k_{\\min},\\; k_{\\max})"),
        P("三个常数各有来历：<strong>224</strong> 是 ImageNet 预训练的输入边长；<strong>k₀ = 4</strong> 表示「一个 224×224 的框应该由 P4（stride 16）处理」——因为在 ImageNet 预训练里，224 的整图正是被 C4 那一级的感受野覆盖的；<strong>clip 到 [2, 5]</strong> 是因为金字塔只有这几层。公式的含义很朴素：<em>框的边长每减半，就往上（分辨率更高的那一层）挪一级</em>。"),
        TABLE(["√(wh)（像素）", "log₂(√wh/224)", "⌊·⌋ + 4", "clip 到 [2,5]", "该层 stride", "目标占几个格子（每轴）"], [
            ["<strong>448</strong>", "+1.00", "5", "P5", "32", "14.0"],
            ["<strong>224</strong>", "0.00", "4", "P4", "16", "14.0"],
            ["<strong>112</strong>", "−1.00", "3", "P3", "8", "14.0"],
            ["<strong>56</strong>", "−2.00", "2", "P2", "4", "14.0"],
            ["<strong>32</strong>", "−2.81", "1", "<strong>P2（被 clip）</strong>", "4", "8.0"],
            ["<strong>20</strong>", "−3.49", "0", "<strong>P2（被 clip）</strong>", "4", "<strong>5.0</strong>"],
            ["<strong>10</strong>", "−4.49", "−1", "<strong>P2（被 clip）</strong>", "4", "<strong>2.5</strong>"],
            ["<strong>10（没有 P2，clip 到 3）</strong>", "−4.49", "−1", "<strong>P3</strong>", "8", "<strong>1.25</strong>"],
        ]),
        P("注意最后两行——这就是整节的要害。<strong>公式在小尺寸上是「饱和」的：所有小于 56 px 的框都被 clip 到同一层</strong>。公式本身没错，它只是在说「我已经没有更高分辨率的层可以给你了」。"),
        H3("一阶段检测器用的是尺度区间，但结论一样"),
        P("YOLO / RetinaNet / FCOS 不用这条公式：YOLO 用 anchor 的 IoU 匹配，FCOS 用<span class=\"term\">回归范围（regression range）</span>——P3 负责 [0, 64)、P4 负责 [64, 128)、P5 负责 [128, 256)、P6 [256, 512)、P7 [512, ∞)。形式不同，<strong>效果完全一样：所有小目标被压在最高分辨率那一层</strong>。FCOS 的 P3 区间下界是 0，上界 64，意味着 6 px 和 63 px 的目标共用同一层同一套回归尺度。"),
        H3("TSR 尺寸分布：小目标占比不是数据集偏差，是几何必然"),
        P("很多人以为「TT100K 里小目标多」是数据集的采集偏好。<strong>不是——它是针孔几何 + 均匀采样的必然结果，可以推导出来。</strong>针孔模型给出像素尺寸"),
        MATH("s \\;=\\; \\frac{f\\,S}{Z}, \\qquad f \\;=\\; \\frac{W_{\\text{px}}/2}{\\tan(\\mathrm{HFOV}/2)}"),
        P("对 1920×1080、水平 FOV 60° 的前视相机，f ≈ <strong>1662.8 px</strong>；一块 60 cm 的圆形限速牌于是有 s ≈ 997.7 / Z（Z 以米计）。<em>50 米外 20 px，100 米外 10 px，150 米外 6.7 px。</em> 现在关键的一步：车匀速前进、按固定帧率采样，则同一块标志被采到的<strong>距离近似均匀分布</strong>。做变量代换 s = c/Z，得"),
        MATH("p(s) \\;=\\; p(Z)\\left|\\frac{\\mathrm{d}Z}{\\mathrm{d}s}\\right| \\;=\\; \\frac{1}{Z_{\\max}-Z_{\\min}}\\cdot\\frac{c}{s^{2}} \\;\\propto\\; \\frac{1}{s^{2}}"),
        P("<strong>尺寸密度以 1/s² 衰减</strong>——这是一个非常陡的幂律。代入 Z ∈ [8, 150] m：<strong>84% 的标志实例小于 32 px（COCO 的「small」定义），62% 小于 16 px，18% 小于 8 px</strong>。notebook 里会把这个解析结果和蒙特卡洛对上。"),
        TABLE(["FPN 配置", "P2 (stride 4)", "P3 (stride 8)", "P4 (stride 16)", "P5 (stride 32)", "结论"], [
            ["<strong>P2–P5</strong>（含 P2）", "<strong>99.4%</strong>", "0.6%", "0%", "0%", "P3–P5 三层几乎在空转"],
            ["<strong>P3–P5</strong>（无 P2，主流配置）", "—", "<strong>100%</strong>", "0%", "0%", "<strong>付了 3 层的钱，只有 1 层在干活</strong>"],
            ["<strong>P3–P7</strong>（RetinaNet 配置）", "—", "<strong>100%</strong>", "0%", "0%", "P6/P7 在 TSR 上是纯浪费"],
        ]),
        CALLOUT("danger", "<p>这张表是本模块最重要的一个数字。<strong>在 TSR 的尺寸分布下，一个 P3–P7 的 RetinaNet 等价于一个「单尺度、stride 8」的检测器</strong>——多尺度金字塔的全部收益在这个任务上归零，而它的计算成本你一分不少地付了。<em>更糟的是，这一层的 stride 是 8，对一个 10 px 的标志只有 1.25 个格子。</em></p><p><strong>面试里这是一个能立刻显出水平的点</strong>：被问「小目标怎么办」时，标准答案是「加 P2 / 提分辨率 / 用 NWD」；<em>而能先把「你现在这套配置下各层的负载是多少」算出来再谈方案的人，面试官会立刻知道你真的调过</em>。面试官想听的是<strong>「我先统计了尺寸分布和层级负载，发现 99% 压在 P3，所以先动的是分辨率而不是 backbone」</strong>这种归因过程。</p>", "层级负载：先算，再改"),
    ])),

    ("p2", "加 P2 的账：分辨率的平方增长有多贵", "".join([
        P("既然所有目标都挤在最高分辨率那层，最直接的解法就是<strong>再加一层更高分辨率的 P2（stride 4）</strong>。它的收益是确定的：10 px 的目标从 1.25 个格子变成 2.5 个格子，正样本候选点数量按面积翻 4 倍。代价也同样确定，而且可以精确算出来。"),
        H3("成本：为什么恰好是 85/21 ≈ 4.05 倍"),
        P("neck 与 head 的计算量正比于<strong>特征图位置数</strong>，而位置数 = HW/s²。以 P3 为 1 归一化，各层的相对成本是 4^(3−l)："),
        MATH("\\frac{\\mathcal{C}_{\\text{P2--P5}}}{\\mathcal{C}_{\\text{P3--P5}}} \\;=\\; \\frac{4 + 1 + \\tfrac14 + \\tfrac1{16}}{1 + \\tfrac14 + \\tfrac1{16}} \\;=\\; \\frac{85/16}{21/16} \\;=\\; \\frac{85}{21} \\;\\approx\\; 4.05"),
        P("<strong>加一层，检测头的计算量变成原来的 4 倍。</strong> 这不是「多了一层的开销」，而是「新加的这一层比原来<em>整个</em>金字塔还贵 3 倍」——因为 P2 一层的位置数就是 P3+P4+P5 之和的 3 倍。"),
        TABLE(["层", "stride", "1536×864 输入下的位置数", "相对 P3 的成本", "head MACs（C=128，4 conv）", "激活显存（fp16，8 个中间张量）"], [
            ["<strong>P2</strong>", "4", "<strong>82,944</strong>", "<strong>4.00</strong>", "<strong>48.92 G</strong>", "<strong>169.9 MB</strong>"],
            ["P3", "8", "20,736", "1.00", "12.23 G", "42.5 MB"],
            ["P4", "16", "5,184", "0.25", "3.06 G", "10.6 MB"],
            ["P5", "32", "1,296", "0.0625", "0.76 G", "2.7 MB"],
            ["<strong>合计 P3–P5</strong>", "—", "27,216", "1.3125", "<strong>16.05 G</strong>", "55.7 MB"],
            ["<strong>合计 P2–P5</strong>", "—", "110,160", "5.3125", "<strong>64.98 G（×4.05）</strong>", "<strong>225.6 MB（×4.05）</strong>"],
        ]),
        H3("四种降本手段，以及组合后的真实倍数"),
        P("好消息是，P2 的成本几乎全部来自 head 塔，而 head 的成本对通道数是<strong>平方</strong>依赖、对深度是<strong>线性</strong>依赖。这给了四个独立的旋钮："),
        TABLE(["手段", "怎么做", "P2 成本变化", "总成本倍数", "副作用"], [
            ["基线（无 P2）", "P3–P5", "—", "<strong>1.00×</strong>", "小目标只有 1.25 个格子"],
            ["朴素加 P2", "P2 与其他层同构（C=128, 4 conv）", "48.92 G", "<strong>4.05×</strong>", "车端基本不可接受"],
            ["<strong>P2 通道减半</strong>", "P2 用 C=64（成本 ∝ C²，÷4）", "12.23 G", "<strong>1.76×</strong>", "P2 特征表达力下降，需要更依赖上层语义"],
            ["<strong>P2 头变浅</strong>", "P2 只用 1 个 conv（其余复用 P3 权重）", "12.23 G", "<strong>1.76×</strong>", "共享头需要每层独立 BN（见 C53 m03）"],
            ["<strong>P2 只算 ROI</strong>", "只在图像上半部（标志所在区域）算 P2", "24.46 G", "<strong>2.52×</strong>", "需要可靠的 ROI 先验；下方近处大标志会漏"],
            ["<strong>减半通道 + ROI</strong>", "组合上面两条", "6.12 G", "<strong>1.38×</strong>", "工程复杂度上升，但这是量产里真实的选择"],
        ]),
        DUAL(
            "所以「加 P2 太贵」这个结论要打个折扣：<strong>朴素地加确实是 4 倍，但把 P2 当成一个「便宜的、只管小目标的辅助层」来设计，可以压到 1.4 倍左右</strong>。关键的心法是——<em>P2 不需要和 P3–P5 同构</em>。它面对的目标只有 4–30 px，既不需要 128 通道去区分 200 类的精细语义（那部分可以靠上层送下来的语义），也不需要 4 层卷积塔去做大范围回归。",
            "但有一个必须一起算的隐性代价：<strong>加 P2 会让前景-背景比进一步恶化约 4 倍</strong>。以 1536×864、一张图 5 块标志、center-based 分配每个 GT 约 9 个正样本计算：P3–P5 下正样本占比 45/27216 = <strong>0.165%</strong>，加 P2 后总位置数变成 110160，而正样本数几乎不变（中心采样半径按 stride 缩放，落在框内的点数由目标尺寸决定而不是由 stride 决定），占比掉到 <strong>0.041%</strong>。<em>也就是说，你花 4 倍算力买来的分辨率，同时把分类头的正负样本比推到了 1:2400</em>。这不是加 P2 的反对理由，而是说明<strong>架构改动必须和分配 / 损失改动一起做</strong>——这正是下一个模块的内容。",
        ),
        CALLOUT("warn", "一个实现细节的坑：<strong>加了 P2，anchor 的尺度设置也必须跟着改</strong>。RetinaNet 默认每层的基础 anchor 边长是 4×stride（P3 → 32 px）。如果你直接把 P2 挂上去而不改 anchor 配置，P2 的基础 anchor 是 4×4=16 px——听起来合理，但配上 {1, 2^(1/3), 2^(2/3)} 三档尺度后最小 anchor 仍是 16 px，<em>而你要检的目标是 6–10 px</em>。<strong>结果是加了 P2 但 AP_s 几乎没涨，然后得出「加 P2 没用」的错误结论。</strong> 正确做法：先统计尺寸分布，再让最小 anchor 落在分布的 5% 分位上。"),
    ])),

    ("pan_bifpn", "信息该往哪个方向流：PAN、BiFPN 与加权融合", "".join([
        P("FPN 的信息流是<strong>单向</strong>的——语义从深层往浅层广播。反过来的方向呢？浅层拥有最精确的边缘与定位信息，深层却拿不到它。在原始 backbone 里，C2 的信息要到达 C5 需要穿过<strong>一百多层</strong>卷积，经过这么长的路径，精确的空间信息早就被平均掉了。"),
        P("<span class=\"term\">PANet</span>（Path Aggregation Network）的解法直白得近乎粗暴：<strong>在 FPN 之后再接一条自底向上的路径</strong>。这条捷径只有不到 10 层，浅层的定位信息可以近乎无损地送到深层。notebook 里有一个只用 numpy 就能跑的实验来验证这件事：在 P2 上放一个脉冲，跑完 FPN 的 top-down 后 P5 的响应<strong>严格为零</strong>；接上 PAN 的 bottom-up 之后 P5 才有响应。<em>这不是比喻，是可以 assert 的事实。</em>"),
        ASCII("""三代 neck 的连接拓扑（→ 表示特征流动方向）

  FPN                    PAN (= FPN + bottom-up)        BiFPN（一个 block，可重复 N 次）
  P5 ●                   P5 ●────────▶● N5              P5 ●──────────────────▶●
     │↓up                   │↓up      ↑↑down                │↓         ↗ 同层跨接 ↑
  P4 ●───(+)──▶●         P4 ●──(+)──▶●───▶● N4         P4 ●──(+)──▶●──(+)──▶●
     │↓up       │            │↓up      │  ↑↑down            │↓        ↗        ↑
  P3 ●───(+)──▶●         P3 ●──(+)──▶●───▶● N3         P3 ●──(+)──▶●──(+)──▶●
     │↓up       │            │↓up      │  ↑↑down            │↓        ↗        ↑
  P2 ●───(+)──▶●         P2 ●──(+)──▶●───▶● N2         P2 ●─────────(+)──────▶●

  单向：语义↓          双向：语义↓ + 定位↑            双向 + 同层跨接 + **可学权重**
  P2 的信息到不了 P5    捷径 <10 层（原本 >100 层）     删掉只有一个输入的节点（对融合无贡献）""")
        ,
        P("<span class=\"term\">BiFPN</span>（EfficientDet）在 PAN 基础上做了三个改动，其中第三个对小目标最关键："),
        OL([
            "<strong>删掉只有单个输入的节点</strong>——它只做了一次卷积，对「融合」没有贡献，纯粹浪费算力。",
            "<strong>同层加一条从原始输入到输出的跨接</strong>——保留该层自己的信息不被上下层稀释，成本几乎为零。",
            "<strong>加权融合（weighted feature fusion）</strong>——不同层的特征分辨率不同，直接相加等于默认它们同等重要，这是错的。BiFPN 给每个输入配一个可学标量权重。",
        ]),
        MATH("O \\;=\\; \\sum_i \\frac{w_i}{\\varepsilon + \\sum_j w_j}\\cdot I_i, \\qquad w_i = \\mathrm{ReLU}(\\tilde w_i), \\quad \\varepsilon = 10^{-4}"),
        P("这个形式叫 <span class=\"term\">fast normalized fusion</span>：用 ReLU 保证非负、用求和归一化保证权重落在 [0,1]，比 softmax 快得多而效果相当。<strong>为什么它对小目标重要？</strong> 因为 P2 的特征是整个金字塔里语义最弱、噪声最大的（它离 backbone 的深层最远，语义全靠上采样借来）。如果 P2 和上采样来的 P3 <em>等权相加</em>，等于强制规定「这一层自己的证据和借来的语义一样可信」。<strong>加权融合让网络自己去学这个比例——而学出来的结果通常是：在小目标密集的层上，自身分辨率的权重更高。</strong>"),
        TABLE(["neck", "方向", "融合方式", "参数量增量", "典型 AP 增益", "对小目标的意义"], [
            ["<strong>FPN</strong>", "↓ 单向", "逐元素相加", "基线", "基线", "浅层拿到语义，但语义是插值来的"],
            ["<strong>PAN</strong>", "↓↑ 双向", "逐元素相加", "+~1.5×", "+1–2 AP", "深层拿到定位信息；<em>对小目标的直接收益有限</em>"],
            ["<strong>BiFPN</strong>", "↓↑ 双向 + 跨接", "<strong>可学加权</strong>", "+~0.6×（比 PAN 更省）", "+1–2 AP，小模型上更明显", "<strong>让 P2 的自身证据不被稀释</strong>"],
            ["<strong>NAS-FPN</strong>", "搜索出的任意拓扑", "相加 / 全局池化", "视搜索结果", "+2 AP，但不可解释", "工程上难维护，逐渐被 BiFPN 取代"],
            ["<strong>重复 N 次的 BiFPN</strong>", "同上，堆叠", "同上", "×N", "边际递减，N=3–7", "小目标受益于更多轮跨层交换"],
        ]),
        CALLOUT("warn", "两个常见误解。<strong>①「BiFPN 的加权是 attention」——不是。</strong> 它是<em>每个输入一个标量</em>（或每通道一个标量），与输入内容无关，训完就固定了；attention 的权重是逐样本、逐位置动态计算的。这个区别决定了 BiFPN 的加权几乎不增加推理成本，也决定了它的表达力上限。<strong>②「neck 越复杂越好」——在大模型上不成立。</strong> BiFPN 的增益在 EfficientDet-D0/D1 这类小模型上有 1–2 AP，到 D7 就基本被主干的容量淹没了。<em>车端 TSR 恰好在「小模型」那一档，所以 neck 的改动在这里性价比反而更高。</em>"),
    ])),

    ("resolution", "三笔不同的账：提高输入分辨率 vs 加 P2 vs 换更强主干", "".join([
        P("「小目标检不到」有三个看起来都合理的解法，但它们<strong>解决的根本不是同一件事</strong>。分清楚这一点，是这一节唯一要传达的东西。"),
        TABLE(["方案", "改变了什么", "全模型 FLOPs", "目标的<strong>像素数</strong>", "目标占的<strong>格子数</strong>", "本质"], [
            ["<strong>加 P2</strong>（stride 8 → 4）", "只改采样网格", "neck+head ×4.05；主干不变", "<strong>不变</strong>", "×2（每轴）", "<strong>把已有信息采得更细</strong>"],
            ["<strong>输入分辨率 ×2</strong>", "改输入信息量", "<strong>全模型 ×4</strong>", "<strong>×4</strong>", "×2（每轴）", "<strong>恢复被 resize 丢掉的传感器信息</strong>"],
            ["<strong>换更深/更宽主干</strong>", "改表示容量", "主干 ×1.5–3", "不变", "不变", "<strong>对小目标几乎无效</strong>"],
            ["<strong>把 resize 改回原生分辨率</strong>", "停止丢信息", "按面积比例", "<strong>×(比例)²</strong>", "×比例", "<strong>免费的、最高 ROI 的一招</strong>"],
        ]),
        H3("为什么这个区分是决定性的：一个 TSR 的具体数字"),
        P("典型的工程现状是：相机给 1920×1080，训练脚本 letterbox 到 640×640。<strong>缩放比例是 640/1920 = 0.333。</strong> 于是："),
        UL([
            "50 米外的限速牌：原生 <strong>20 px</strong> → 送进网络时 <strong>6.7 px</strong>；在 stride 8 上占 <strong>0.83 个格子</strong>——不到一个格子，<em>结构上不可能检出</em>。",
            "100 米外：原生 10 px → <strong>3.3 px</strong>；在 stride 8 上占 0.42 个格子。这不是「难检」，是「不存在」。",
            "把输入换成 1280×720（比例 0.667）：50 米外变成 <strong>13.3 px</strong>，stride 8 上 1.67 个格子；100 米外 6.7 px。",
            "用原生 1920×1080：50 米外 20 px / 2.5 格，100 米外 10 px / 1.25 格。<strong>同样是 stride 8，检出距离从 30 米推到了 80 米以上。</strong>",
        ]),
        DUAL(
            "所以顺序应该是：<strong>先把输入分辨率提到延迟预算允许的上限，再考虑加 P2，最后才轮到换主干</strong>。原因是——<em>加 P2 只是把同样的信息采得更细，而提高输入分辨率是真的把信息拿回来</em>。一个 6.7 px 的目标无论用多细的网格去采，它也只有 6.7 px 的信息；而把它变回 20 px，是把传感器本来就捕捉到的、被 resize 扔掉的那部分像素找回来。",
            "严格地说，两者的作用可以分解为：<strong>「目标的像素数」决定了信息量上界，「目标占的格子数」决定了网络能不能表示它</strong>。加 P2 只动第二项，提分辨率两项都动。而换主干——把 ResNet-50 换成 ResNet-101 或 Swin——<em>两项都不动</em>，它增加的是「在给定信息量下的表示能力」，而小目标的瓶颈根本不在表示能力，在信息量。<strong>这解释了一个常见的困惑：换了更强的 backbone，AP_m 和 AP_l 都涨了，AP_s 纹丝不动。</strong>",
        ),
        CALLOUT("danger", "<p><strong>面试里这是一个分水岭问题。</strong> 被问「怎么提升小目标检测」时，如果候选人直接开始讲 FPN / BiFPN / 注意力机制，那是背书；<em>如果候选人先反问「你现在的输入分辨率是多少、原图是多少、目标的像素尺寸分布是什么样」，面试官立刻知道这个人做过真实项目</em>。</p><p>因为在工业界，<strong>「训练时把 1920 缩到 640」这个配置是压倒性常见的默认值</strong>（YOLO 的默认 imgsz=640 就是这么来的），而它在 TSR 上直接把一半以上的目标压到了亚格子尺度。<em>把它改回去往往比任何架构改动的收益都大，而且不需要改一行模型代码。</em> <strong>面试官想听的是：你会先量化问题，再选方案；而不是背一串方法名。</strong></p>", "先问分辨率，再谈架构"),
        CALLOUT("warn", "提高输入分辨率不是免费的，有三个必须一起算的代价：<strong>① 全模型 FLOPs 按面积平方增长</strong>（1920 vs 640 是 9 倍）；<strong>② 感受野相对目标变小了</strong>——同一个网络在高分辨率输入上，深层的有效感受野覆盖的<em>物理场景范围</em>变小，可能伤害大目标与上下文；<strong>③ 训练-推理分辨率必须一致</strong>，否则 anchor 尺度、回归范围、归一化尺度全部错位（这是 C60 讲的一致性问题的一个具体实例）。"),
    ])),

    ("deformable", "可变形注意力：稀疏采样为什么对小目标天然友好", "".join([
        P("Transformer 检测器给出了第三条路。但先要说清楚：<strong>朴素的多尺度全局注意力在检测上是算不动的</strong>。把 1536×864 的 P2–P5 全部展平成 token："),
        CODE("""P2: 216×384 =  82,944
P3: 108×192 =  20,736
P4:  54× 96 =   5,184
P5:  27× 48 =   1,296
                -------
总计            110,160 个 token

全局 self-attention 的复杂度 O(N²·C) = 110160² × 256 ≈ 3.1 × 10¹² MAC
—— 比整个 ResNet-50 主干贵四个数量级。不可行。"""),
        P("<span class=\"term\">Deformable attention</span> 的做法是：<strong>每个 query 不看全部 110,160 个位置，而是只采样 M×L×K 个点</strong>（M 个注意力头 × L 个金字塔层 × 每层 K 个采样点），采样位置由 query 自己预测的偏移量决定。取 M=8、L=4、K=4，就是 <strong>128 个采样点</strong>："),
        MATH("\\frac{\\text{全局注意力的 key 数}}{\\text{可变形采样点数}} \\;=\\; \\frac{110{,}160}{8\\times4\\times4} \\;=\\; \\frac{110{,}160}{128} \\;\\approx\\; 861\\times"),
        ASCII("""可变形采样：一个 query 在四个层上各采 K=4 个点（偏移量可学）

           P2 (stride 4)              P3 (stride 8)         P4        P5
     ┌───┬───┬───┬───┬───┐        ┌───┬───┬───┐        ┌───┬───┐   ┌───┐
     │   │ ✱ │ ✱ │   │   │        │   │ ✱ │   │        │ ✱ │   │   │ ✱ │
     ├───┼───┼───┼───┼───┤        ├───┼───┼───┤        ├───┼───┤   └───┘
     │ ✱ │▓▓▓▓▓▓▓│ ✱ │   │        │ ✱ │▓▓▓│   │        │   │ ✱ │
     ├───┼▓ GT ▓┼───┼───┤        ├───┼───┼───┤        └───┴───┘
     │   │▓▓▓▓▓▓▓│   │   │        │   │ ✱ │ ✱ │
     └───┴───┴───┴───┴───┘        └───┴───┴───┘
       10 px 目标 = 2.5×2.5 格      = 1.25×1.25 格      0.6 格    0.3 格
       采样点可以**全部落进目标**    只能落在同一格上      无区分度

  关键：✱ 的位置是 **query 预测出来的偏移**，不是固定网格。
       所以模型可以学会「小目标 query 把采样点收紧到 P2 的两三个格子里」。""")
        ,
        P("对小目标，这个机制有两个具体的好处，都能量化："),
        OL([
            "<strong>注意力质量不被背景稀释。</strong> 在全局 softmax attention 里，一个 10 px 的目标在 P2 上只占 6.25 个格子，占全部 110,160 个 key 的 <strong>5.7 × 10⁻⁵</strong>。初始化时注意力接近均匀，<em>目标能拿到的注意力质量是十万分之五</em>——这正是 DETR 收敛慢的根因之一（见 C54 m04）。而可变形注意力用一组学到的偏移把采样点直接放到目标上，notebook 的模拟显示：在 P2 上，采样点落进 10 px 目标框内的比例可达 <strong>62%</strong>。<em>从 5.7×10⁻⁵ 到 0.62，是四个数量级的差别。</em>",
            "<strong>天然跨层。</strong> 一个 query 同时在 P2–P5 上采样，不需要「先决定这个目标属于哪一层」。<em>这等于把上一节讲的「层级分配」问题从硬性划分变成了软性加权</em>——对处在层级边界上的目标（比如 60 px 恰好在 P2/P3 分界处）尤其重要。",
        ]),
        DUAL(
            "所以可变形注意力对小目标友好，本质上是因为它<strong>把「在哪里取证据」变成了可学的</strong>。卷积的采样位置是固定网格，全局注意力的采样位置是「全部」，可变形注意力的采样位置是「学出来的少数几个」——对一个只有几个格子的目标，这恰好是最有效的形式。",
            "但有两个必须知道的约束。<strong>① 初始化极其关键</strong>：Deformable DETR 把采样偏移的初始值设成围绕参考点的规则网格（不同的头指向不同方向），并且把预测偏移的线性层权重初始化为 0、偏置设成那个网格。<em>如果随机初始化，采样点会散到图像各处，小目标上根本收不回来，训练直接不收敛</em>——这是一个「论文里一句话、复现时踩三天」的细节。<strong>② 采样用双线性插值，梯度可以传到亚像素位置</strong>，这既是优点（定位精度不受网格限制）也是隐患（对 4–8 px 的目标，插值出来的梯度信噪比很低）。",
        ),
        CALLOUT("intuition", "把三代方案排成一条线就清楚了：<strong>FPN 是「把语义搬到高分辨率上」，PAN/BiFPN 是「让搬运双向且可加权」，可变形注意力是「不搬了，让需要的人自己去取」</strong>。<em>而所有这些都在同一个前提下工作：高分辨率的那一层必须存在。</em> 如果你的金字塔从 P3 开始，那么再精巧的采样机制也只能在 stride 8 的网格上采——<strong>这就是为什么本模块的顺序是「先分辨率，后融合，再采样」。</strong>"),
    ])),

    ("context", "上下文：一个 8 像素的目标必须靠周围", "".join([
        P("把信息瓶颈算清楚：一个 8×8 px 的标志，在 stride 8 的 P3 上占据<strong>恰好一个格子</strong>。这一个格子是一个 C 维向量（典型 C=256），而它要同时编码："),
        UL([
            "<strong>objectness</strong>——这里有没有东西",
            "<strong>类别</strong>——中国 GB 5768 体系下含限速变体有 200+ 类，需要 log₂(200) ≈ 7.6 bit 的可区分度",
            "<strong>框回归</strong>——中心偏移 + 宽高，4 个连续量",
            "<strong>（若有）属性</strong>——是否电子牌、是否对向车道、遮挡程度",
        ]),
        P("而这个向量的输入信息来自原图 8×8 = 64 个像素，经过 ISP、JPEG 压缩、运动模糊、下采样之后，有效信息远低于 64×3 字节的名义上界。<strong>结论是清楚的：仅靠目标自身的像素，不足以完成这个任务。必须用上下文。</strong>"),
        H3("TSR 的上下文是什么"),
        TABLE(["上下文线索", "具体是什么", "怎么用", "风险"], [
            ["<strong>杆件（pole）</strong>", "标志几乎总是装在竖直杆件上；杆件的像素长度远大于标志本身", "扩大感受野让「杆 + 牌」一起被看到", "<strong>路灯、电线杆也是竖直杆</strong>"],
            ["<strong>位置先验</strong>", "标志在图像中的位置高度受限：消失点附近、地平线以上、道路两侧带状区域", "位置编码 / ROI 裁剪 / 位置相关的先验分数", "上下坡、弯道会破坏先验；<em>不能做成硬约束</em>"],
            ["<strong>成组出现</strong>", "限速牌下常挂辅助牌；施工区域标志成串出现", "同图内的目标间关系建模（self-attention 天然支持）", "训练数据里的共现偏差会被学成规则"],
            ["<strong>与车道的几何关系</strong>", "本车道的标志 vs 对向车道 / 辅路的标志", "把车道线检测结果作为额外输入", "<strong>关联错误比漏检更危险</strong>（限速 40 误用到主路）"],
            ["<strong>路面与场景类型</strong>", "高速 / 城市 / 乡道决定了可能出现的标志子集", "场景分类作为条件，或用作后处理先验", "跨域时先验失效"],
            ["<strong>时序</strong>", "同一块标志在连续帧中由远及近", "多帧融合（见 C55 m04）", "延迟与稳定性的权衡"],
        ]),
        H3("三种把上下文注入模型的方式"),
        TABLE(["方式", "代表做法", "有效感受野的变化", "成本", "适用性"], [
            ["<strong>扩大感受野</strong>", "5×5 depthwise 大核（RTMDet）、空洞卷积、非局部块", "直接增大", "大核 depthwise 极便宜；非局部很贵", "<strong>首选</strong>，尤其大核 depthwise"],
            ["<strong>显式上下文特征</strong>", "把 ROI 周围 2× 区域的特征一并池化后拼接", "不变，但输入变多", "中（多一路 RoIAlign）", "两级方案里很自然（见 C55 m02）"],
            ["<strong>先验编码</strong>", "把归一化的 (x, y) 坐标、消失点距离作为额外通道", "不变", "几乎为零", "<strong>性价比极高但容易过拟合</strong>"],
        ]),
        DUAL(
            "上下文的收益是真实的：一个 8 px 的红色圆形本身可能是标志、可能是尾灯、可能是广告牌上的圆点；<strong>但「装在竖直杆上、位于地平线上方、在道路右侧带状区域内」的 8 px 红色圆形，几乎一定是禁令标志</strong>。这个联合先验能把一个几乎不可解的分类问题变成可解的。",
            "但上下文有一个具体的失效模式，必须提前防：<strong>当目标自身的信息太弱时，模型会退化成「只学上下文」</strong>。症状是——在有杆件的位置产生高置信度误检（而那里其实是路牌背面或者路灯），同时对不在典型位置的标志（临时施工牌放在地上、龙门架上的标志）完全漏检。<em>诊断方法很直接：把目标区域遮黑只留上下文，看模型的置信度掉多少</em>。<strong>如果掉得不多，说明模型根本没在看目标本身。</strong>",
        ),
        CALLOUT("warn", "所以上下文的大小是一个需要调的超参，而不是「越大越好」。经验区间：<strong>上下文范围取目标尺寸的 3–6 倍</strong>。低于 3 倍拿不到杆件；高于 6 倍开始引入无关背景，并且让模型学到「路边区域 = 有标志」的捷径。<em>在 TSR 上这个捷径的直接后果就是广告牌与车身贴纸的误检——而误检在量产系统里的代价远高于漏检（会触发莫名其妙的减速）。</em>"),
    ])),

    ("superres_light", "超分、特征增强，以及轻量化与小目标的根本矛盾", "".join([
        P("最后两类做法值得单独一节，因为它们在论文里看起来很有吸引力，但在量产系统里的实际排序<strong>远低于</strong>前面几节的方法。"),
        H3("超分与特征级增强：为什么排在最后"),
        P("这一类方法的思路是：既然小目标像素少，就<strong>先把它放大</strong>——图像级超分（先超分再检测）、特征级超分（<span class=\"term\">Perceptual GAN</span> 把小目标特征映射到大目标特征的分布上）、或者用 GAN 判别器逼迫小目标特征「看起来像」大目标特征。"),
        TABLE(["方法", "做什么", "论文报告增益", "真实代价", "工程建议"], [
            ["<strong>图像级超分</strong>", "整图 2–4× 超分后再检测", "AP_s +1–3", "<strong>额外一个大网络 + 分辨率翻倍的检测</strong>，延迟不可接受", "❌ 车端不考虑"],
            ["<strong>特征级超分</strong>（Perceptual GAN 系）", "把小目标的浅层特征映射到「大目标风格」", "AP_s +1–2", "多一个生成器 + 判别器，训练不稳定", "⚠️ 收益不如直接提分辨率"],
            ["<strong>特征重建 / 自蒸馏</strong>", "用高分辨率分支的特征蒸馏低分辨率分支", "AP_s +0.5–1.5", "<strong>只在训练期，推理零成本</strong>", "✅ 值得试，是这类里唯一划算的"],
            ["<strong>直接提输入分辨率</strong>", "见上一节", "AP_s <strong>+5–15</strong>（TSR 上）", "FLOPs 按面积增长", "✅✅ <strong>先做这个</strong>"],
        ]),
        CALLOUT("danger", "<p><strong>超分在 TSR 上有一个特有的、安全相关的风险：幻觉（hallucination）。</strong> 超分网络的本质是「用学到的先验补全缺失的高频信息」——它不创造信息，它<em>发明</em>信息。在自然图像上，把模糊的树叶补成清晰的树叶无伤大雅；<strong>但在一个 8 px 的限速牌上，超分网络完全可能把「60」补成「80」，而且补得非常清晰、非常自信。</strong></p><p>下游拿到的是一个高置信度的错误限速。<em>这类错误无法通过置信度过滤，因为超分让整条链路的置信度都升高了。</em> <strong>结论：任何在安全关键路径上引入生成式补全的做法，都必须有一条不依赖它的旁路来交叉验证</strong>（例如地图先验、多帧一致性）。这是量产 TSR 系统的一条红线。</p>", "超分不创造信息，它发明信息"),
        H3("轻量化与小目标：三板斧，每一斧都砍在小目标上"),
        P("车端模型必须轻量化，而轻量化的三个标准手段<strong>恰好都直接伤害小目标</strong>——这不是巧合，是因为小目标依赖的正是被裁掉的那些东西。"),
        TABLE(["轻量化手段", "省了什么", "为什么专门伤小目标", "缓解"], [
            ["<strong>降输入分辨率</strong>", "FLOPs ∝ 面积", "<strong>直接删除小目标的像素</strong>；20 px → 6.7 px", "<strong>不要做</strong>；改用 ROI 裁剪保留关键区域的原生分辨率"],
            ["<strong>减通道</strong>", "FLOPs ∝ C²", "小目标的判别信息本就集中在少数通道，减通道优先损失细粒度纹理", "只减深层通道，保留 P2/P3 的通道数"],
            ["<strong>减深度 / 用 depthwise</strong>", "FLOPs 线性下降", "depthwise 去掉了通道间混合，而小目标的语义恰恰需要跨通道组合弱信号", "<strong>大核 depthwise + 1×1 pointwise</strong>（RTMDet 的做法）保留混合能力"],
            ["<strong>结构化剪枝</strong>", "去掉低激活通道", "<strong>小目标的激活本来就低</strong> → 负责小目标的通道被优先剪掉", "按分尺寸的 AP 做剪枝敏感度评估，而不是只看总 mAP"],
            ["<strong>INT8 量化</strong>", "算力 / 带宽", "小目标的 logit 分布集中在低分区，量化后区分度下降更明显", "分类头保 FP16；校准集必须含足量小目标（见 C60 m03）"],
        ]),
        DUAL(
            "所以「又要轻量又要小目标好」这个需求本身是有内在张力的。<strong>解决张力的方式不是在两者之间折中，而是让计算量花在该花的地方</strong>：整图用低分辨率跑一个粗检测器找 ROI，只在 ROI 上用高分辨率精检（这就是模块 04 要讲的两级级联）；或者只对图像的上半部分算 P2。<em>「均匀地降低所有地方的精度」是最差的一种轻量化。</em>",
            "还有一个容易被忽略的评测陷阱：<strong>剪枝 / 量化的敏感度评估如果只看总 mAP，几乎必然会牺牲小目标</strong>。因为在 COCO 式的评测里 AP_s 只占 mAP 的三分之一权重，而在 TSR 的真实分布里小目标占 84%。<em>一个「总 mAP 只掉 0.5」的剪枝方案，完全可能对应「AP_s 掉 4、AP_l 涨 1」</em>。<strong>正确做法是把按尺寸分桶的 AP 作为剪枝与量化的主指标</strong>——这一点在模块 05 和 C60 m03 会再展开。",
        ),
        CALLOUT("intuition", "把本模块的所有手段按「收益 / 成本」排一次序，对 TSR 场景大致是：<strong>① 把输入分辨率改回接近原生（收益极大，成本 = FLOPs 按面积增长，无工程风险）→ ② 加 P2 且用减半通道 / ROI 限制成本（收益大，1.4× 成本）→ ③ neck 换 BiFPN 或加权融合（收益中，成本小）→ ④ 上下文与位置先验（收益中，成本几乎为零，但要防捷径）→ ⑤ 特征蒸馏（收益小，推理零成本）→ ⑥ 超分（收益不确定，有安全风险）</strong>。<em>注意前两条都是「分辨率」，这不是巧合——小目标问题在架构层面上，八成是分辨率问题。</em>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("架构层面的小目标解法在 2020 年之后进入了一个「大方向已定、细节仍在动」的阶段。以下是几个仍然开放、且与 TSR 直接相关的问题。"),
        UL([
            "<strong>高分辨率主干 vs 编码-解码金字塔。</strong> <span class=\"term\">HRNet</span> 路线主张全程保持高分辨率分支并行交换，而不是「先降采样再上采样」。它在姿态估计上确定性地更好，但在检测上因为计算量分布不友好（高分辨率分支贯穿全网）一直没成为主流。<em>随着车端算力上升、以及「小目标才是瓶颈」的共识增强，这条路线值得重新评估</em>——尤其是「只在浅层保持高分辨率、深层正常下采样」的混合形态。",
            "<strong>P2 的成本该怎么摊。</strong> 目前的做法（减通道、减头深度、ROI 限制）都是工程折中，缺少原则性的答案。一个开放问题是：<em>能否让 P2 只承担「定位」而把「分类」完全交给上层</em>——即把检测头按任务拆到不同分辨率上（定位需要分辨率，分类需要语义）。已有零星工作（task-decoupled heads across levels），但尚无公认结论。",
            "<strong>可变形采样在极小目标上的退化。</strong> 当目标只有 2–3 个格子时，K=4 个采样点已经覆盖了目标的大部分，继续增大 K 没有收益；而学到的偏移量的方差可能超过目标本身的尺寸，使采样退化为噪声。<em>「采样点数与目标尺寸的匹配」目前靠调参，缺少自适应机制。</em>",
            "<strong>上下文的可控注入。</strong> 如何在利用上下文的同时防止模型学成「位置捷径」，目前只有经验做法（限制上下文范围、加位置扰动增强）。<em>一个有价值的方向是显式建模「目标证据」与「上下文证据」的分离，并在推理时能报告两者各贡献了多少</em>——这对可解释性与安全论证都有意义。",
            "<strong>与事件相机 / 多曝光的结合。</strong> 小目标的根本瓶颈是信息量，而传统 RGB 相机在远距离 + 高动态范围场景下的信息采集本身就是受限的。事件相机的高时间分辨率、多曝光 HDR 的高动态范围，都是「在传感器端增加信息」的路线。<em>这一路线绕过了所有架构技巧，直接从源头解决问题，但成本与成熟度仍是障碍。</em>",
            "<strong>神经架构搜索的回归。</strong> NAS-FPN 之后这条路一度沉寂（不可解释、迁移性差）。但在「给定车端芯片的算子支持与延迟模型，搜索最优金字塔拓扑」这个受约束的设定下，它重新变得实用——<em>因为约束足够强，搜索空间小到可以穷举，结果也可解释</em>。",
        ]),
        CALLOUT("paper", "必读：<em>Feature Pyramid Networks for Object Detection</em>（Lin et al., CVPR 2017，层级分配公式的出处，第 4.2 节）；<em>Path Aggregation Network for Instance Segmentation</em>（Liu et al., CVPR 2018，PAN 的自底向上路径与「路径长度」论证）；<em>EfficientDet: Scalable and Efficient Object Detection</em>（Tan et al., CVPR 2020，BiFPN 与 fast normalized fusion，第 3.2 节）；<em>Deformable DETR: Deformable Transformers for End-to-End Object Detection</em>（Zhu et al., ICLR 2021，多尺度可变形注意力，注意附录里的偏移初始化细节）；<em>Deep High-Resolution Representation Learning</em>（Wang et al., TPAMI 2020，HRNet）。小目标专题综述：<em>Towards Large-Scale Small Object Detection: Survey and Benchmarks</em>（Cheng et al., TPAMI 2023）。相邻课程：C53 m03（RTMDet 的大核与共享头）、C54 m04（可变形注意力的收敛分析）、C57 m03（分配与损失）、C57 m04（切片推理）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 架构层面的解法：分辨率、多尺度与上下文（FPN 层级分配 / P2 成本 / 加权融合 / 可变形采样）

目标：把「小目标要不要加 P2」这类问题从<strong>争论</strong>变成<strong>计算</strong>。
本 notebook 全程纯 numpy，所有结论都以 `assert` 固定下来。

**你会亲手实现：**
1. 针孔模型下的 TSR 尺寸分布，并**解析地证明**尺寸密度 ∝ 1/s²（不是数据集偏差，是几何必然）
2. FPN 的层级分配公式 `k = k0 + floor(log2(sqrt(wh)/224))`，并统计 TSR 分布下各层的负载
3. 「一个目标在某 stride 的网格上有几个中心点」的解析式与蒙特卡洛验证
4. 加 P2 的 FLOPs / 显存增量计算器（精确到 85/21 这个分数），以及四种降本手段
5. FPN top-down / PAN bottom-up / BiFPN fast normalized fusion，用**脉冲实验**证明 FPN 单向性
6. 可变形采样点在小目标上的覆盖率分析

> 心智模型：**小目标在架构层面上，八成是分辨率问题。
> 「目标的像素数」决定信息量上界，「目标占的格子数」决定网络能否表示它——
> 提分辨率两项都动，加 P2 只动第二项，换主干两项都不动。**"""),

    md("""## 1 · TSR 尺寸分布：从针孔模型推出来，而不是从数据集统计出来"""),
    code("""import numpy as np, math, json
rng = np.random.default_rng(57)

def focal_px(width_px, hfov_deg):
    '''针孔模型：f = (W/2) / tan(HFOV/2)，单位是像素。'''
    return (width_px / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

W_IMG, H_IMG, HFOV = 1920, 1080, 60.0
F_PX  = focal_px(W_IMG, HFOV)
SIGN_M = 0.60                      # 中国圆形限速牌直径 60 cm

def sign_px(dist_m, sign_m=SIGN_M, f=F_PX):
    '''标志在图像上的像素边长： s = f * S / Z'''
    return f * sign_m / np.asarray(dist_m, dtype=float)

print(f'相机: {W_IMG}x{H_IMG}, HFOV={HFOV}deg  ->  f = {F_PX:.2f} px')
print(f'60 cm 限速牌的像素尺寸:')
for z in [10, 20, 30, 50, 60, 80, 100, 130, 150]:
    s = float(sign_px(z))
    tag = '  <- COCO small (<32px)' if s < 32 else ''
    print(f'   {z:4d} m  ->  {s:6.2f} px{tag}')

assert abs(F_PX - 1662.77) < 0.05,  F_PX
assert abs(float(sign_px(50)) - 19.95) < 0.05
assert float(sign_px(100)) < 12.0
print('\\n✅ 50 m 外 ~20 px, 100 m 外 ~10 px —— 这就是 TSR 的物理起点。')"""),

    code("""# 距离均匀采样 -> 尺寸密度 ∝ 1/s^2 （s = c/Z, Z~U(a,b) => p(s) = c / ((b-a) s^2)）
Z_MIN, Z_MAX, N_SAMP = 8.0, 150.0, 400_000
C_GEO = F_PX * SIGN_M                       # s = C_GEO / Z

Z = rng.uniform(Z_MIN, Z_MAX, N_SAMP)
S = C_GEO / Z                               # 每个实例的像素边长

def frac_below_analytic(thr):
    '''P(s < thr) = P(Z > C/thr)，解析式。'''
    z_star = np.clip(C_GEO / thr, Z_MIN, Z_MAX)
    return (Z_MAX - z_star) / (Z_MAX - Z_MIN)

print(f'尺寸范围: {S.min():.2f} .. {S.max():.2f} px   (Z in [{Z_MIN}, {Z_MAX}] m)')
print(f"\\n{'阈值':>8s} {'蒙特卡洛':>12s} {'解析式':>12s}")
for thr in [8, 12, 16, 24, 32, 48, 96]:
    emp, ana = float((S < thr).mean()), float(frac_below_analytic(thr))
    assert abs(emp - ana) < 0.005, (thr, emp, ana)
    print(f'  s<{thr:3d}px {emp:11.3%} {ana:11.3%}')

FRAC_SMALL = float((S < 32).mean())
assert FRAC_SMALL > 0.80, FRAC_SMALL
assert float((S < 16).mean()) > 0.55
print(f'\\n⚠️  {FRAC_SMALL:.1%} 的实例小于 32 px（COCO 的 small 定义）——')
print('    这不是数据集采集偏好，是 p(s) ∝ 1/s² 的几何必然。')
print('✅ 推导: s = c/Z, Z~U(a,b)  =>  p(s) = p(Z)|dZ/ds| = c / ((b-a) s²)')"""),

    code("""# 标注截断的影响：很多数据集会丢弃 < 8px 的框，这让"数据集看起来"没那么极端
for cut in [0, 4, 8, 12, 16]:
    kept = S[S >= cut]
    print(f'标注下限 {cut:2d} px: 保留 {len(kept)/len(S):6.1%} 的实例, '
          f'其中 <32px 占 {float((kept < 32).mean()):6.1%}, 中位尺寸 {np.median(kept):5.1f} px')
kept8 = S[S >= 8]
assert (kept8 < 32).mean() < FRAC_SMALL, '截断后小目标占比下降'
print('\\n⚠️  标注截断是"离线指标好、路测体验差"的一个隐性来源：')
print('    被丢掉的极小目标在路上是**真实存在**的，只是评测集里看不到它们。')
print('    正确做法：把 <8px 的框标成 ignore 区域（不算正也不算负），而不是直接删掉。')"""),

    md("""## 2 · FPN 层级分配公式，以及 TSR 分布下的层级负载"""),
    code("""def fpn_level(w, h, k0=4, lo=2, hi=5):
    '''FPN / Mask R-CNN 的 RoI 层级分配： k = floor(k0 + log2(sqrt(wh)/224))，再 clip。'''
    k = k0 + math.floor(math.log2(math.sqrt(w * h) / 224.0 + 1e-12))
    return int(min(max(k, lo), hi))

STRIDE = {2: 4, 3: 8, 4: 16, 5: 32, 6: 64, 7: 128}

print(f"{'sqrt(wh)':>10s} {'log2(s/224)':>12s} {'k(未clip)':>10s} "
      f"{'k(P2-P5)':>10s} {'stride':>7s} {'占格子/轴':>10s}")
for s in [448, 224, 112, 56, 32, 20, 10, 6]:
    raw = 4 + math.floor(math.log2(s / 224.0))
    k = fpn_level(s, s)
    print(f'{s:>10d} {math.log2(s/224.0):>12.2f} {raw:>10d} '
          f'{"P%d" % k:>10s} {STRIDE[k]:>7d} {s/STRIDE[k]:>10.2f}')

assert fpn_level(224, 224) == 4
assert fpn_level(112, 112) == 3
assert fpn_level(56, 56)   == 2
assert fpn_level(500, 500) == 5
assert fpn_level(10, 10)   == 2, '10px 被 clip 到 P2'
assert fpn_level(10, 10, lo=3) == 3, '没有 P2 时 clip 到 P3'
print('\\n⚠️  公式在小尺寸上是**饱和**的：所有 <56px 的框都被 clip 到同一层。')
print('    公式没错，它只是在说「我已经没有更高分辨率的层可以给你了」。')"""),

    code("""def level_load(sizes, lo, hi, k0=4):
    '''统计一批目标在金字塔各层上的负载占比。'''
    ks = np.array([fpn_level(s, s, k0=k0, lo=lo, hi=hi) for s in sizes])
    return {int(k): float((ks == k).mean()) for k in range(lo, hi + 1)}

SUB = S[rng.choice(len(S), 40_000, replace=False)]      # 抽样加速
load_p2 = level_load(SUB, lo=2, hi=5)
load_p3 = level_load(SUB, lo=3, hi=5)
load_p37 = level_load(SUB, lo=3, hi=7)

print(f"{'配置':<22s} " + ' '.join(f'{"P%d"%k:>8s}' for k in range(2, 8)))
for name, ld in [('P2-P5 (含 P2)', load_p2), ('P3-P5 (主流)', load_p3),
                 ('P3-P7 (RetinaNet)', load_p37)]:
    cells = ' '.join(f'{ld.get(k, float("nan")):>7.1%}' if k in ld else f'{"—":>8s}'
                     for k in range(2, 8))
    print(f'{name:<22s} {cells}')

assert load_p2[2] > 0.98,  load_p2
assert load_p3[3] > 0.999, load_p3
assert load_p37[3] > 0.999 and load_p37[6] == 0.0 and load_p37[7] == 0.0
print(f'\\n⚠️  P2-P5: {load_p2[2]:.1%} 的目标压在 P2；P3-P5/P3-P7: **100%** 压在 P3。')
print('    => 在 TSR 分布下，P3-P7 的 RetinaNet 等价于一个「单尺度 stride 8」检测器。')
print('    你付了 5 层金字塔的钱，只有 1 层在干活，而它的 stride 是 8。')

# 每层的"格子预算"：目标在被分配到的那层上占几个格子
for name, lo in [('有 P2', 2), ('无 P2', 3)]:
    ks = np.array([fpn_level(s, s, lo=lo, hi=5) for s in SUB])
    cells = SUB / np.array([STRIDE[k] for k in ks])
    print(f'{name}: 中位格子数/轴 = {np.median(cells):.2f}, '
          f'低于 1 个格子的比例 = {float((cells < 1).mean()):.1%}')"""),

    md("""## 3 · 「有几个中心点落在框里」：正样本稀缺的第一层原因

center-based 分配（FCOS / YOLOX / 大多数 anchor-free 检测器）要求**特征图的格子中心落在 GT 框内**。
对小目标，这个条件本身就可能无法满足——而且概率可以精确算出来。"""),
    code("""def p_zero_center_analytic(size_px, stride):
    '''格子中心位于 {c0 + k*stride}。GT 框边长 L 随机放置时，
       每个轴上落入至少一个中心的概率 = min(1, L/stride)。
       二维需要两个轴同时满足 => P(一个正样本都没有) = 1 - min(1, L/s)^2 。'''
    p_axis = min(1.0, size_px / stride)
    return 1.0 - p_axis ** 2

def p_zero_center_mc(size_px, stride, n=200_000, rng=rng):
    '''蒙特卡洛：框左上角在一个 stride 周期内均匀放置。'''
    a = rng.uniform(0.0, stride, size=(n, 2))
    # 格子中心在 stride/2 + k*stride；数一数 [a, a+L) 内有几个
    lo = np.ceil((a - stride / 2.0) / stride)
    hi = np.ceil((a + size_px - stride / 2.0) / stride)
    cnt = (hi - lo)                       # 每轴的中心点个数
    return float((cnt.min(axis=1) == 0).mean())

print(f"{'目标边长':>9s} {'stride':>7s} {'E[中心点数]':>12s} "
      f"{'P(0个正样本) 解析':>18s} {'蒙特卡洛':>10s}")
for L, s in [(4, 8), (6, 8), (8, 8), (10, 8), (16, 8),
             (4, 4), (6, 4), (10, 4), (10, 16), (10, 32)]:
    ana, mc = p_zero_center_analytic(L, s), p_zero_center_mc(L, s)
    assert abs(ana - mc) < 0.01, (L, s, ana, mc)
    print(f'{L:>9d} {s:>7d} {(L/s)**2:>12.2f} {ana:>17.1%} {mc:>10.1%}')

assert p_zero_center_analytic(6, 8) > 0.4,  '6px 目标在 stride 8 上有 >40% 概率一个正样本都没有'
assert p_zero_center_analytic(6, 4) == 0.0, '换到 stride 4 就必然有正样本'
print('\\n⚠️  stride 8 上：4px 目标 75% 没有正样本，6px 目标 44% 没有正样本。')
print('    「没有正样本」= 这个 GT 对损失没有任何贡献 = 模型永远学不到它。')
print('✅ 换到 stride 4（加 P2），>=4px 的目标就必然至少有一个中心点。')"""),

    code("""# 把这个概率套到真实的 TSR 尺寸分布上，算"结构性漏检率"
for lo, name in [(3, '无 P2 (最细 stride 8)'), (2, '有 P2 (最细 stride 4)')]:
    ks = np.array([fpn_level(s, s, lo=lo, hi=5) for s in SUB])
    strides = np.array([STRIDE[k] for k in ks], dtype=float)
    p0 = np.array([p_zero_center_analytic(L, st) for L, st in zip(SUB, strides)])
    print(f'{name:<26s} 结构性零正样本率 = {p0.mean():.2%}')

ks3 = np.array([fpn_level(s, s, lo=3, hi=5) for s in SUB])
p0_no_p2 = np.mean([p_zero_center_analytic(L, STRIDE[k]) for L, k in zip(SUB, ks3)])
ks2 = np.array([fpn_level(s, s, lo=2, hi=5) for s in SUB])
p0_p2 = np.mean([p_zero_center_analytic(L, STRIDE[k]) for L, k in zip(SUB, ks2)])
assert p0_no_p2 > 3 * p0_p2, (p0_no_p2, p0_p2)
print(f'\\n✅ 加 P2 把结构性零正样本率从 {p0_no_p2:.2%} 降到 {p0_p2:.2%}（{p0_no_p2/max(p0_p2,1e-9):.1f}×）')
print('   注意这只是**必要条件**——有中心点不等于能匹配上（IoU 阈值还有一关，见模块 03）。')"""),

    md("""## 4 · 加 P2 的账：FLOPs 与显存，精确到 85/21"""),
    code("""IN_HW = (864, 1536)      # 车端常用的 16:9 输入

def level_cost(hw, stride, C=128, n_conv=4, roi_frac=1.0, k=3):
    '''该层 head 塔的 MACs。roi_frac: 只在图像上方这一比例的高度上计算（ROI 限制）。'''
    H, W = hw
    pos = (int(H * roi_frac) // stride) * (W // stride)
    return pos * n_conv * k * k * C * C

def act_mem_bytes(hw, stride, C=128, n_tensors=8, bytes_per=2, roi_frac=1.0):
    H, W = hw
    return (int(H * roi_frac) // stride) * (W // stride) * C * n_tensors * bytes_per

print(f"{'层':>4s} {'stride':>7s} {'位置数':>10s} {'相对P3':>8s} "
      f"{'head MACs':>13s} {'激活显存':>11s}")
tot_pos = {}
for lvl, st in [(2, 4), (3, 8), (4, 16), (5, 32)]:
    H, W = IN_HW
    pos = (H // st) * (W // st)
    tot_pos[lvl] = pos
    print(f'P{lvl:<3d} {st:>7d} {pos:>10,d} {4.0**(3-lvl):>8.4f} '
          f'{level_cost(IN_HW, st)/1e9:>11.2f} G {act_mem_bytes(IN_HW, st)/1e6:>9.1f} MB')

base = sum(level_cost(IN_HW, s) for s in (8, 16, 32))
with_p2 = sum(level_cost(IN_HW, s) for s in (4, 8, 16, 32))
ratio = with_p2 / base
print(f'\\nP3-P5 合计 {base/1e9:6.2f} G MACs, 位置数 {sum(tot_pos[l] for l in (3,4,5)):,d}')
print(f'P2-P5 合计 {with_p2/1e9:6.2f} G MACs, 位置数 {sum(tot_pos.values()):,d}')
print(f'倍数 = {ratio:.6f}   （解析值 85/21 = {85/21:.6f}）')
assert abs(ratio - 85/21) < 1e-6, ratio
assert abs(tot_pos[2] / tot_pos[3] - 4.0) < 1e-9
print('\\n✅ 加一层，检测头计算量 ×4.05 —— 因为 P2 一层就是 P3+P4+P5 之和的 3 倍。')"""),

    code("""# 四种降本手段，以及组合后的真实倍数
# 每个方案写成 [(stride, C, n_conv, roi_frac), ...]
PLANS = {
    '基线 P3-P5':                 [(8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
    '朴素加 P2':                  [(4,128,4,1.0), (8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
    'P2 通道减半 (C=64)':         [(4, 64,4,1.0), (8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
    'P2 头变浅 (1 conv)':         [(4,128,1,1.0), (8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
    'P2 只算上半图 (ROI 0.5)':    [(4,128,4,0.5), (8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
    'P2 减半通道 + ROI 0.5':      [(4, 64,4,0.5), (8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)],
}
base_cost = sum(level_cost(IN_HW, *L) for L in PLANS['基线 P3-P5'])
print(f"{'方案':<26s} {'总 MACs':>11s} {'倍数':>8s} {'P2 占比':>9s}")
results = {}
for name, plan in PLANS.items():
    tot = sum(level_cost(IN_HW, *L) for L in plan)
    p2c = sum(level_cost(IN_HW, *L) for L in plan if L[0] == 4)
    results[name] = tot / base_cost
    print(f'{name:<26s} {tot/1e9:>9.2f} G {tot/base_cost:>8.3f}x {p2c/tot:>8.1%}')

assert abs(results['朴素加 P2'] - 85/21) < 1e-6
assert abs(results['P2 通道减半 (C=64)'] - results['P2 头变浅 (1 conv)']) < 1e-9, \\
    'C 减半(∝C²，÷4) 与 conv 数 4->1(∝n，÷4) 效果相同'
assert results['P2 减半通道 + ROI 0.5'] < 1.45
print(f"\\n✅ 朴素加 P2 是 {results['朴素加 P2']:.2f}x，"
      f"减半通道+ROI 后只有 {results['P2 减半通道 + ROI 0.5']:.2f}x。")
print('   心法：**P2 不需要和 P3-P5 同构** —— 它面对的目标只有 4-30 px，')
print('   既不需要 128 通道去区分 200 类的精细语义，也不需要 4 层塔做大范围回归。')"""),

    code("""# 隐性代价：加 P2 会让前景-背景比进一步恶化约 4 倍
N_SIGNS_PER_IMG = 5
POS_PER_GT      = 9          # center-based 分配典型值（由目标尺寸决定，与 stride 关系不大）
n_pos = N_SIGNS_PER_IMG * POS_PER_GT
for name, lvls in [('P3-P5', (3,4,5)), ('P2-P5', (2,3,4,5))]:
    n_total = sum(tot_pos[l] for l in lvls)
    print(f'{name}: 总位置 {n_total:>8,d}, 正样本 {n_pos:>3d}, '
          f'正样本占比 {n_pos/n_total:.4%}, 正负比 1:{n_total/n_pos:,.0f}')
r_p3 = n_pos / sum(tot_pos[l] for l in (3,4,5))
r_p2 = n_pos / sum(tot_pos[l] for l in (2,3,4,5))
assert r_p3 / r_p2 > 3.9
print(f'\\n⚠️  加 P2 让正样本占比从 {r_p3:.4%} 掉到 {r_p2:.4%}（恶化 {r_p3/r_p2:.1f}x）。')
print('    你花 4 倍算力买来的分辨率，同时把分类头推到了 1:2400 的正负比。')
print('✅ 结论：**架构改动必须和分配/损失改动一起做** —— 这正是模块 03 的内容。')

# 显存
mem_base = sum(act_mem_bytes(IN_HW, s) for s in (8,16,32))
mem_p2   = sum(act_mem_bytes(IN_HW, s) for s in (4,8,16,32))
print(f'\\n激活显存(fp16, 8 个中间张量, batch=1): '
      f'P3-P5 {mem_base/1e6:.1f} MB -> P2-P5 {mem_p2/1e6:.1f} MB ({mem_p2/mem_base:.2f}x)')
assert abs(mem_p2/mem_base - 85/21) < 1e-6"""),

    md("""## 5 · 多尺度融合：FPN 的单向性（脉冲实验）、PAN 与 BiFPN 加权融合"""),
    code("""def upsample2x(x):
    '''最近邻 2x 上采样， x: (H, W, C)'''
    return np.repeat(np.repeat(x, 2, axis=0), 2, axis=1)

def downsample2x(x):
    '''2x 平均池化下采样'''
    H, W, C = x.shape
    return x.reshape(H // 2, 2, W // 2, 2, C).mean(axis=(1, 3))

_t = rng.normal(size=(8, 8, 3))
assert np.allclose(downsample2x(upsample2x(_t)), _t), '最近邻上采样后平均池化应严格还原'

def fpn_topdown(feats):
    '''自顶向下：语义从深层广播到浅层。feats: {level: (H,W,C)}，level 越大分辨率越低。'''
    out, prev = {}, None
    for l in sorted(feats, reverse=True):
        cur = feats[l].copy()
        if prev is not None:
            cur = cur + upsample2x(prev)
        out[l] = cur
        prev = cur
    return out

def pan_bottomup(feats):
    '''自底向上：定位信息从浅层送到深层。'''
    out, prev = {}, None
    for l in sorted(feats):
        cur = feats[l].copy()
        if prev is not None:
            cur = cur + downsample2x(prev)
        out[l] = cur
        prev = cur
    return out

SHAPES = {2: (32, 32, 4), 3: (16, 16, 4), 4: (8, 8, 4), 5: (4, 4, 4)}
feats = {l: np.zeros(s) for l, s in SHAPES.items()}
feats[2][10, 10, 0] = 1.0                    # 在 P2 放一个脉冲：细节/定位信息

td = fpn_topdown(feats)
pan = pan_bottomup(td)
print(f"{'层':>4s} {'FPN(top-down) 后能量':>22s} {'再接 PAN(bottom-up) 后':>24s}")
for l in sorted(SHAPES):
    print(f'P{l:<3d} {td[l].sum():>22.4f} {pan[l].sum():>24.4f}')

assert td[2].sum() == 1.0
assert td[5].sum() == 0.0 and td[4].sum() == 0.0 and td[3].sum() == 0.0, \\
    'FPN 的 top-down **无法**把 P2 的信息送到深层'
assert pan[5].sum() > 0.0 and pan[3].sum() > 0.0, 'PAN 的 bottom-up 补上了这条通路'
print('\\n⚠️  FPN 的信息流是**单向**的：P2 的脉冲在 P3/P4/P5 上响应严格为 0。')
print('    在原始 backbone 里，C2 -> C5 要穿过 100+ 层；PAN 的捷径只有不到 10 层。')
print('✅ 这不是比喻，是可以 assert 的事实。')"""),

    code("""def fast_norm_fusion(inputs, w_raw, eps=1e-4):
    '''BiFPN 的 fast normalized fusion:  O = sum_i ReLU(w_i)/(eps + sum_j ReLU(w_j)) * I_i'''
    w = np.maximum(np.asarray(w_raw, dtype=float), 0.0)
    denom = eps + w.sum()
    out = np.zeros_like(np.asarray(inputs[0], dtype=float))
    for wi, x in zip(w, inputs):
        out = out + wi * np.asarray(x, dtype=float)
    return out / denom

a = rng.normal(size=(4, 4, 2))
b = rng.normal(size=(4, 4, 2))
c = rng.normal(size=(4, 4, 2))

TOL = dict(rtol=1e-3, atol=1e-4)          # eps=1e-4 会带来 ~1e-4 的相对偏差，用 rtol 判定
assert np.allclose(fast_norm_fusion([a, b], [1.0, 1.0]), (a + b) / 2, **TOL), '等权 = 平均'
assert np.allclose(fast_norm_fusion([a, b], [1.0, 0.0]), a, **TOL),          'one-hot = 直通'
assert np.allclose(fast_norm_fusion([a, b], [1.0, -5.0]), a, **TOL),         'ReLU 把负权重归零'
assert np.allclose(fast_norm_fusion([a, b, c], [2.0, 1.0, 1.0]),
                   (2*a + b + c) / 4, **TOL)

print(f"{'原始权重':>22s} {'归一化后':>28s}")
for w_raw in [[1., 1.], [3., 1.], [1., 0.], [5., 1., 1.], [-2., 1., 1.]]:
    w = np.maximum(np.array(w_raw), 0.0)
    norm = w / (1e-4 + w.sum())
    print(f'{str(w_raw):>22s} {str(np.round(norm, 3).tolist()):>28s}')

# 为什么加权对小目标重要：P2 自身证据 vs 上采样来的语义
own   = np.ones((4, 4, 2)) * 1.0        # P2 自身（高分辨率、语义弱、噪声大）
sem   = np.ones((4, 4, 2)) * 4.0        # 从 P3 上采样来的语义（幅值更大）
eq    = fast_norm_fusion([own, sem], [1.0, 1.0])
learn = fast_norm_fusion([own, sem], [3.0, 1.0])
print(f'\\n等权相加:   融合值 {eq.mean():.3f}  -> P2 自身证据只占 {1*1/(1+4):.1%} 的能量')
print(f'学到的权重: 融合值 {learn.mean():.3f}  -> P2 自身证据占 {3*1/(3*1+1*4):.1%}')
assert eq.mean() > learn.mean(), '把权重挪给幅值小的 P2 后，融合结果被 P2 拉低'
print('✅ 加权融合让网络自己决定「这一层的证据值多少」，')
print('   而不是默认「自身分辨率证据 = 借来的语义」同等可信。')"""),

    md("""## 6 · 可变形采样：token 数的账，与小目标上的覆盖率"""),
    code("""# 多尺度全局 attention 的 token 数
tokens = {l: (IN_HW[0] // STRIDE[l]) * (IN_HW[1] // STRIDE[l]) for l in (2, 3, 4, 5)}
N_KV = sum(tokens.values())
M, L_LV, K = 8, 4, 4                       # 头数 / 层数 / 每层采样点
n_samples = M * L_LV * K

for l in sorted(tokens):
    print(f'P{l}: {IN_HW[0]//STRIDE[l]:>4d} x {IN_HW[1]//STRIDE[l]:>4d} = {tokens[l]:>8,d} token')
print(f'{"总计":<5s}{" ":>17s}{N_KV:>8,d} token')
print(f'\\n全局 self-attention: O(N²·C) = {N_KV:,d}² × 256 ≈ {N_KV**2*256:.2e} MAC —— 不可行')
print(f'可变形采样点数     : M×L×K = {M}×{L_LV}×{K} = {n_samples}')
print(f'比值               : {N_KV/n_samples:,.0f}x')
assert N_KV == 110_160, N_KV
assert 800 < N_KV / n_samples < 900
print(f'\\n✅ 可变形注意力把 key 数从 {N_KV:,d} 降到 {n_samples}，约 {N_KV/n_samples:.0f} 倍。')"""),

    code("""def _phi(z):
    '''标准正态 CDF'''
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def sample_coverage(size_px, stride, sigma_cells=1.0):
    '''采样点偏移 ~ N(0, (sigma_cells*stride)²)（Deformable DETR 的偏移初始化尺度 ∝ stride）。
       返回采样点落进 size_px × size_px 目标框内的概率。'''
    sigma = sigma_cells * stride
    p_axis = 2.0 * _phi(size_px / (2.0 * sigma)) - 1.0
    return p_axis ** 2

print(f"{'目标尺寸':>9s} {'层':>4s} {'stride':>7s} {'占格子/轴':>10s} {'采样点命中率':>13s}")
for size in [10, 20]:
    for lvl in (2, 3, 4, 5):
        st = STRIDE[lvl]
        print(f'{size:>9d} {"P%d"%lvl:>4s} {st:>7d} {size/st:>10.2f} '
              f'{sample_coverage(size, st):>12.1%}')
    print()

cov = [sample_coverage(10, STRIDE[l]) for l in (2, 3, 4, 5)]
assert cov[0] > cov[1] > cov[2] > cov[3], '越高分辨率的层，采样点越容易落进小目标'
assert cov[0] > 0.55 and cov[0] / cov[3] > 20
print(f'✅ 10 px 目标: P2 命中率 {cov[0]:.1%}，P5 只有 {cov[3]:.2%}（差 {cov[0]/cov[3]:.0f} 倍）')

# 与"全局均匀注意力"对比：目标能拿到多少注意力质量
cells_on_p2 = (10 / STRIDE[2]) ** 2
uniform_mass = cells_on_p2 / N_KV
print(f'\\n全局均匀 attention: 10px 目标在 P2 上占 {cells_on_p2:.2f} 格 / {N_KV:,d} token'
      f' = {uniform_mass:.2e} 的注意力质量')
print(f'可变形采样        : {cov[0]:.2%} 的采样点直接落在目标上')
assert cov[0] / uniform_mass > 1e3
print(f'✅ 相差 {cov[0]/uniform_mass:.1e} 倍 —— 这正是 DETR 收敛慢、Deformable DETR 快的量化根因。')
print('⚠️  实现细节：偏移必须初始化成围绕参考点的规则网格（预测层权重置 0、偏置置为网格），')
print('    随机初始化会让采样点散到全图，小目标上根本收不回来 —— 论文一句话，复现三天。')"""),

    md("""## ✏️ 练习 1：层级负载统计器

实现 `fpn_level_load(sizes, k0=4, lo=2, hi=5)`，返回 `{level: 占比}`（所有 level 都要出现，
没有目标的层占比为 0.0）。用上面的 `fpn_level` 即可。"""),
    code("""def fpn_level_load(sizes, k0=4, lo=2, hi=5):
    # TODO: 对每个 size 调用 fpn_level(size, size, k0, lo, hi)，统计各层占比
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
r = fpn_level_load([224, 224, 112, 56], lo=2, hi=5)
assert set(r) == {2, 3, 4, 5}, r
assert abs(r[4] - 0.5) < 1e-9 and abs(r[3] - 0.25) < 1e-9 and abs(r[2] - 0.25) < 1e-9
assert r[5] == 0.0
r2 = fpn_level_load(SUB, lo=2, hi=5)
assert r2[2] > 0.98 and abs(sum(r2.values()) - 1.0) < 1e-9
r3 = fpn_level_load(SUB, lo=3, hi=7)
assert r3[3] > 0.999 and r3[6] == 0.0 and r3[7] == 0.0
print('TSR 分布下的层级负载:')
for name, ld in [('P2-P5', r2), ('P3-P7', r3)]:
    print(f'  {name}: ' + '  '.join(f'P{k}={v:.1%}' for k, v in sorted(ld.items())))
print('✅ 练习 1 通过：**先算负载，再谈方案** —— 这是面试里的分水岭')"""),

    md("""## ✏️ 练习 2：金字塔成本比计算器

实现 `plan_cost_ratio(hw, base_plan, new_plan)`，plan 是 `[(stride, C, n_conv, roi_frac), ...]`，
返回 `new_plan` 相对 `base_plan` 的总 MACs 倍数。直接复用上面的 `level_cost`。"""),
    code("""def plan_cost_ratio(hw, base_plan, new_plan):
    # TODO: 分别求和再相除
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
BASE = [(8,128,4,1.0), (16,128,4,1.0), (32,128,4,1.0)]
assert abs(plan_cost_ratio(IN_HW, BASE, BASE) - 1.0) < 1e-12
assert abs(plan_cost_ratio(IN_HW, BASE, [(4,128,4,1.0)] + BASE) - 85/21) < 1e-6
assert abs(plan_cost_ratio(IN_HW, BASE, [(4,64,4,1.0)] + BASE)
           - plan_cost_ratio(IN_HW, BASE, [(4,128,1,1.0)] + BASE)) < 1e-9
r_cheap = plan_cost_ratio(IN_HW, BASE, [(4,64,4,0.5)] + BASE)
assert 1.30 < r_cheap < 1.45, r_cheap
print(f"{'方案':<28s} {'倍数':>8s}")
for name, plan in PLANS.items():
    print(f'{name:<28s} {plan_cost_ratio(IN_HW, BASE, plan):>7.3f}x')
print('✅ 练习 2 通过：**P2 不必与 P3-P5 同构** —— 4.05x 可以压到 1.38x')"""),

    md("""## ✏️ 练习 3：BiFPN 的加权融合（含尺寸对齐）

实现 `bifpn_node(inputs, w_raw, target_hw, eps=1e-4)`：
先把每个输入用 `upsample2x` / `downsample2x` 反复调整到 `target_hw`（只会差 2 的整数次幂），
再做 fast normalized fusion。假设所有输入的通道数一致。"""),
    code("""def bifpn_node(inputs, w_raw, target_hw, eps=1e-4):
    # TODO: ① 逐个 resize 到 target_hw（大了就 downsample2x，小了就 upsample2x）
    #       ② 调用 fast_norm_fusion
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
x_hi  = rng.normal(size=(16, 16, 2))
x_mid = rng.normal(size=( 8,  8, 2))
x_lo  = rng.normal(size=( 4,  4, 2))

o = bifpn_node([x_hi, x_mid, x_lo], [1., 1., 1.], (8, 8))
assert o.shape == (8, 8, 2), o.shape
ref = (downsample2x(x_hi) + x_mid + upsample2x(x_lo)) / 3.0
assert np.allclose(o, ref, rtol=1e-3, atol=1e-4)

o1 = bifpn_node([x_hi, x_lo], [1., 0.], (16, 16))
assert o1.shape == (16, 16, 2) and np.allclose(o1, x_hi, rtol=1e-3, atol=1e-4)
o2 = bifpn_node([x_mid], [2.0], (8, 8))
assert np.allclose(o2, x_mid, rtol=1e-3, atol=1e-4), \\
    '单输入节点做的只是一次恒等变换 —— BiFPN 把它删掉了'
print('融合输出形状:', o.shape, '| 等权融合与手算参考一致 ✅')
print('✅ 练习 3 通过：加权融合让 P2 的自身证据不被上采样来的语义稀释')"""),

    md("""## ✏️ 练习 4：反推 stride —— 「要看清这个目标，最粗能用多大的 stride」

实现 `max_stride_for(size_px, min_cells_per_axis, candidates=(1,2,4,8,16,32,64,128))`：
返回满足 `size_px / stride >= min_cells_per_axis` 的**最大**候选 stride；无解返回 `None`。
再实现 `required_input_scale(native_px, min_cells, stride)`：
在给定 stride 下，要让原生尺寸为 `native_px` 的目标占到 `min_cells` 个格子，
输入图像最少要保留原始分辨率的多少比例。"""),
    code("""def max_stride_for(size_px, min_cells_per_axis, candidates=(1,2,4,8,16,32,64,128)):
    # TODO
    raise NotImplementedError

def required_input_scale(native_px, min_cells, stride):
    # TODO: 返回 min_cells * stride / native_px
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
assert max_stride_for(10, 2) == 4      # 10/4 = 2.5 >= 2, 而 10/8 = 1.25 < 2
assert max_stride_for(10, 3) == 2
assert max_stride_for(6, 2)  == 2
assert max_stride_for(100, 2) == 32
assert max_stride_for(1, 2) is None
assert abs(required_input_scale(20, 2, 8) - 0.8) < 1e-12
assert abs(required_input_scale(20, 2, 4) - 0.4) < 1e-12

print(f"{'距离':>6s} {'原生px':>8s} {'最粗stride(>=2格)':>18s} "
      f"{'stride8 需保留比例':>20s} {'stride4 需保留比例':>20s}")
for z in [30, 50, 80, 100, 130]:
    s_native = float(sign_px(z))
    ms = max_stride_for(s_native, 2)
    r8 = required_input_scale(s_native, 2, 8)
    r4 = required_input_scale(s_native, 2, 4)
    print(f'{z:>5d}m {s_native:>8.1f} {str(ms):>18s} '
          f'{min(r8,9.99):>19.2f}x {min(r4,9.99):>19.2f}x')
print('\\n⚠️  100 m 外的标志（10 px）在 stride 8 上需要**超过原生分辨率**才能占到 2 个格子。')
print('✅ 练习 4 通过：这个求解器把「要检多远」直接翻译成「输入分辨率 + stride」的配置约束')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def fpn_level_load(sizes, k0=4, lo=2, hi=5):
    ks = [fpn_level(s, s, k0=k0, lo=lo, hi=hi) for s in sizes]
    n = max(len(ks), 1)
    return {k: sum(1 for v in ks if v == k) / n for k in range(lo, hi + 1)}"""),
    code("""# 练习 2 参考答案
def plan_cost_ratio(hw, base_plan, new_plan):
    base = sum(level_cost(hw, *L) for L in base_plan)
    new  = sum(level_cost(hw, *L) for L in new_plan)
    return new / base"""),
    code("""# 练习 3 参考答案
def bifpn_node(inputs, w_raw, target_hw, eps=1e-4):
    aligned = []
    for x in inputs:
        y = np.asarray(x, dtype=float)
        while y.shape[0] > target_hw[0]:
            y = downsample2x(y)
        while y.shape[0] < target_hw[0]:
            y = upsample2x(y)
        aligned.append(y)
    return fast_norm_fusion(aligned, w_raw, eps=eps)"""),
    code("""# 练习 4 参考答案
def max_stride_for(size_px, min_cells_per_axis, candidates=(1,2,4,8,16,32,64,128)):
    ok = [s for s in candidates if size_px / s >= min_cells_per_axis]
    return max(ok) if ok else None

def required_input_scale(native_px, min_cells, stride):
    return min_cells * stride / float(native_px)"""),

    md("""---
## 🧪 真实工程胶囊：把本模块的结论变成配置"""),
    code("""RECIPE = r'''
# ============================================================================
# TSR 小目标 · 架构层面的配置清单（按收益/成本排序，从上往下做）
# ============================================================================

# ---- 步骤 0：先量化，别急着改模型 -------------------------------------------
#   ① 统计标注框的 sqrt(w*h) 分布（画直方图 + 5/25/50/75/95 分位）
#   ② 算每个框在"它会被分配到的那一层"上占几个格子： size / stride
#   ③ 算层级负载： 各层的目标占比。>90% 集中在一层 = 金字塔在空转
#   ④ 算 letterbox 缩放比例： imgsz / 原图宽。这一步常常就能找到问题。

# ---- 步骤 1：把输入分辨率改回接近原生（最高 ROI，零工程风险）-----------------
# Ultralytics YOLO
model.train(data='tsr.yaml',
            imgsz=1280,            # ← 从默认 640 提到 1280；1920 原生更好但要看延迟
            rect=True,             # 保持 16:9，别 pad 成正方形（pad 是纯浪费的算力）
            scale=0.5, mosaic=1.0) # 多尺度训练下界不要太低，否则更伤小目标

# MMDetection：train_pipeline / test_pipeline 的 scale 必须一致
train_pipeline = [
    dict(type='Resize', scale=(1536, 864), keep_ratio=True),   # ← 不是 (1333, 800)
    ...
]

# ---- 步骤 2：加 P2，但让它便宜 ------------------------------------------------
# MMDetection: FPN 从 P2 开始（start_level=0 表示用 C2）
neck = dict(
    type='FPN',
    in_channels=[256, 512, 1024, 2048],   # C2..C5
    out_channels=128,                      # ← 车端用 128 而不是 256
    start_level=0,                         # ← 0 = 从 C2 开始，产出 P2
    num_outs=4,                            # P2..P5（不要 P6/P7，TSR 上它们负载为 0）
)
bbox_head = dict(
    strides=[4, 8, 16, 32],                # ← 必须同步改！忘了改是最常见的坑
    stacked_convs=4,
    # anchor-based 时还要改 anchor 尺度：让最小 anchor 落在尺寸分布的 5% 分位
    anchor_generator=dict(type='AnchorGenerator',
                          octave_base_scale=2,     # ← 默认 4 => P2 最小 anchor 16px，太大
                          scales_per_octave=3,
                          ratios=[0.8, 1.0, 1.25], # 交通标志接近方形，别用 [0.5,1,2]
                          strides=[4, 8, 16, 32]),
)
# FCOS/ATSS 风格还要改回归范围：
#   regress_ranges = ((-1, 32), (32, 96), (96, 256), (256, 1e8))   # ← 为小目标下移

# ---- 步骤 3：neck 换加权融合（成本小，小模型上收益明显）----------------------
neck = dict(type='BiFPN' , num_stages=3, out_channels=128, start_level=0)
# 或 YOLO 系直接用 PAN（v5/v8 默认已含），确认它确实接了 P2 分支

# ---- 步骤 4：上下文与位置先验（几乎零成本）-----------------------------------
#   · 主干里换 5x5 depthwise 大核（RTMDet 的做法），扩大有效感受野
#   · 把归一化坐标 (x/W, y/H) 作为额外 2 个通道拼进 neck 输入
#   · 训练时对位置先验加扰动增强（随机上下平移），防止学成"位置捷径"

# ---- 步骤 5：评测必须按尺寸分桶，否则改进不可见 ------------------------------
SIZE_BUCKETS = [(0, 8), (8, 16), (16, 32), (32, 96), (96, 1e9)]
# 只看总 mAP 的话，一个"AP_s +4 / AP_l -1"的正确改动可能显示为 +0.3（看起来像噪声）

# ---- 反模式清单（看到就要警惕）-----------------------------------------------
#   ✗ imgsz=640 训 1920 的图，然后抱怨小目标检不到
#   ✗ 加了 P2 但没改 strides / anchor 尺度 / regress_ranges
#   ✗ P3-P7 的配置用在 TSR 上（P6/P7 永远拿不到目标）
#   ✗ 用总 mAP 做剪枝/量化的敏感度评估（会系统性牺牲小目标）
#   ✗ 上超分：它不创造信息，它发明信息 —— "60" 可能被补成 "80"
'''
print(RECIPE)
for key in ['imgsz=1280', 'start_level=0', 'strides=[4, 8, 16, 32]',
            'octave_base_scale', 'regress_ranges', 'SIZE_BUCKETS', '反模式']:
    assert key in RECIPE, key
print('✅ 配方覆盖：先量化 -> 提分辨率 -> 便宜地加 P2 -> 加权融合 -> 上下文 -> 分桶评测')"""),

    md("""### 小结

- **层级分配公式 `k = ⌊k0 + log2(√(wh)/224)⌋` 在小尺寸上是饱和的**：所有 <56 px 的框被 clip 到同一层。
  在 TSR 的尺寸分布下，**P3–P7 的金字塔有 100% 的目标压在 P3**——你付了 5 层的钱，只有 1 层在干活。
- **TSR 的小目标占比是几何必然，不是数据集偏差**：s = fS/Z 加上距离均匀采样 ⇒ p(s) ∝ 1/s²，
  于是 84% 的实例 <32 px。**推导它比统计它更有说服力。**
- **加 P2 的成本恰好是 85/21 ≈ 4.05×**（neck+head），显存同比例。但 **P2 不必与其他层同构**：
  通道减半（∝C²，÷4）或头变浅（÷4）各能把倍数压到 1.76×，配合 ROI 限制可到 **1.38×**。
- **加 P2 的隐性代价是正负样本比恶化 4 倍**（0.165% → 0.041%）。
  **架构改动必须和分配/损失改动一起做**——这是模块 03 的内容。
- **提分辨率 ≠ 加 P2 ≠ 换主干**：「目标的像素数」决定信息量上界，「占的格子数」决定网络能否表示它。
  **提分辨率两项都动，加 P2 只动第二项，换主干两项都不动**——这解释了「换了更强 backbone，AP_s 纹丝不动」。
- **FPN 的信息流是单向的**（P2 的脉冲在 P5 上响应严格为 0），PAN 补上自底向上的捷径，
  BiFPN 再加上**可学的加权融合**，让 P2 的自身证据不被上采样来的语义稀释。
- **可变形注意力把 key 数从 110,160 降到 128（861×）**，并让采样点命中小目标的比例从
  5.7×10⁻⁵ 提到 62%——但**偏移初始化必须是规则网格**，随机初始化直接不收敛。
- **上下文范围取目标尺寸的 3–6 倍**：太小拿不到杆件，太大会学成「路边 = 有标志」的捷径 → 广告牌误检。
- **超分是最后手段且有安全风险**：它不创造信息，它发明信息。8 px 的「60」可能被补成清晰自信的「80」。

下一站：**模块 03 · 分配与损失层面的解法**——当分辨率已经用足，
剩下的问题是「IoU 这把尺子本身对小框就是坏的」，而 **NWD** 换掉了这把尺子。"""),
]
