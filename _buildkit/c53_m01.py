# -*- coding: utf-8 -*-
"""C53 模块 01 · YOLO 家族演进：每一代到底改了什么。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00；C18（anchor / IoU / NMS / FPN / mAP）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_yolo_evolution.ipynb'),
    ("核心参考", "YOLOv1–v4 原论文、YOLOX、RepVGG、YOLOv6/v7、Ultralytics YOLOv8 文档、YOLOv9、YOLOv10"),
    ("预计时长", "读 75 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("v1", "YOLOv1：把检测变成一次回归，以及它的结构性上限", "".join([
        P("YOLOv1 的贡献是一句到今天仍然成立的话：<strong>检测可以是一次前向，不需要 proposal 阶段</strong>。它把图像切成 <code>S×S</code>（原文 7×7）个格子，每个格子直接回归 <code>B</code>（原文 2）个框加一个置信度，再加一份类别概率向量。"),
        ASCII("""YOLOv1 的输出张量：7 x 7 x 30

  每个格子 30 维 = B x 5 + C = 2 x 5 + 20
     |             |          |
     |             |          +-- 20 个类别的**条件概率** P(class | object)
     |             +------------- 每个框 5 维: x, y, w, h, confidence
     +--------------------------- 7x7 = 49 个格子，每格 448/7 = 64 px

  关键限制（全部是结构性的，不是训练不够）：
    (1) 一个格子最多输出 B=2 个框     -> 一格里 3 个目标必丢 1 个
    (2) 一个格子只有**一份**类别向量  -> 一格里两个不同类别的目标，只能保住一个
    (3) 类别与框是分开的两件事        -> 两个框被迫共享同一个类别判断
    (4) 全连接层把空间尺寸写死        -> 换输入分辨率就要重训

  对 TSR 意味着什么：一个施工区门架上 5 块牌子挤在 100 px 内 ——
  它们全部落进 2 个格子，v1 结构上最多输出 4 个框、且只能给出 2 个类别。""")
        ,
        P("notebook 第 1 节会把这笔账算出来：一个合成的 TSR 场景里 9 个标志，YOLOv1 的结构<strong>最多只能表达 6 个</strong>——1 个死于「每格 B=2」，2 个死于「每格一份类别向量」。同一批目标交给一个 stride 8 的现代 dense head，<strong>9 个全部可表达</strong>。"),
        DUAL(
            "这三条限制的共同根源是<strong>「格子」既是空间单元又是语义单元</strong>。v1 让一个格子同时承担「这里有几个东西」和「这里是什么」两个职责，于是密集场景下两个职责互相挤压。<em>后面所有的演进，本质上都是在把这两个职责解耦</em>——anchor 把「有几个」变成「每个 anchor 一个」，解耦头把「是什么」和「在哪里」拆成两条支路，anchor-free 又把 anchor 换成更细的格点。",
            "还有一条不那么显眼但影响巨大的限制：<strong>v1 的框是从格子直接回归绝对坐标的</strong>，模型要从零学出「宽度大概是多少像素」。这个回归目标的<em>尺度跨度极大且分布高度非高斯</em>（小目标密集、大目标稀疏），训练极不稳定——原论文用 <code>√w, √h</code> 作为回归目标就是在硬压这个问题。<strong>v2 引入 anchor 的第一动机其实是「把回归变成对一个先验框的相对偏移」，让回归目标分布集中在 1 附近</strong>，而不是教科书上常说的「支持多尺度」。这是面试里能显出你读过原文的一个细节。",
        ),
        CALLOUT("warn", "别把 v1 的失败归因于「网络不够深」。<strong>上面四条限制在参数量增加时一条都不会消失</strong>——它们是输出张量的形状决定的。<em>这是一个可迁移的判断方法：看到一个模型在某类样本上系统性失败，先问「这是容量问题还是表达能力问题」</em>。容量问题加参数能解决，表达能力问题必须改输出结构。密集小目标场景下 v1 的失败属于后者。"),
    ])),
    ("anchor", "v2/v3：anchor 先验、维度聚类与多尺度", "".join([
        P("YOLOv2（YOLO9000）与 YOLOv3 用三个改动把 v1 的结构性上限拆掉。它们至今仍是理解检测器的基本语言。"),
        TABLE(["改动", "解决 v1 的哪条限制", "机制", "代价"], [
            ["<strong>anchor（先验框）</strong>", "每格 B=2 且类别共享", "每个格点配 k 个先验框，<strong>每个 anchor 独立预测类别与偏移</strong>", "引入超参：anchor 的数量与尺寸；<em>它们必须和数据分布匹配</em>"],
            ["<strong>维度聚类<br>dimension cluster</strong>", "anchor 尺寸靠手工设", "在训练集的 <code>(w,h)</code> 上跑 k-means，<strong>距离用 1−IoU 而不是欧氏距离</strong>", "需要提前统计数据；换数据集要重聚类"],
            ["<strong>多尺度 + FPN</strong>", "单一 stride 覆盖不了尺度跨度", "在 stride 8/16/32 三层各出一套预测，高层语义经上采样与低层融合", "显存与计算量上升；<em>层级分配规则成了新的调参点</em>"],
            ["<strong>相对偏移 + logistic</strong>", "回归目标尺度跨度大", "<code>b<sub>x</sub>=σ(t<sub>x</sub>)+c<sub>x</sub></code>，中心被约束在本格内", "无（纯收益）"],
            ["<strong>多标签分类</strong>", "softmax 假设类别互斥", "每类独立 sigmoid", "无（对含层次标签的 TSR 尤其重要）"],
        ]),
        P("<strong>为什么 k-means 的距离必须用 1−IoU？</strong> 因为欧氏距离会被大框主导：一个 300×300 的框和一个 320×320 的框，欧氏距离是 28；而一个 8×8 和一个 10×10 的框欧氏距离只有 2.8——<em>但后者的 IoU 只有 0.64，前者高达 0.88</em>。用欧氏距离聚类，聚类中心会全部被大框拽走，小目标分不到 anchor。"),
        MATH("d(b, a) = 1 - \\mathrm{IoU}(b, a), \\qquad \\mathrm{IoU}(b,a) = \\frac{\\min(w_b,w_a)\\cdot\\min(h_b,h_a)}{w_b h_b + w_a h_a - \\min(w_b,w_a)\\cdot\\min(h_b,h_a)}"),
        P("notebook 第 2 节会在一个<strong>按针孔模型合成的交通标志尺寸分布</strong>上把这件事跑出来（<code>px = f·S/Z</code>，标志物理尺寸 0.6/0.8/1.2 m、距离 10–120 m）。三个结果值得记住："),
        UL([
            "<strong>IoU 距离显著优于欧氏距离</strong>：k=9 时平均最佳 IoU 0.847 vs 0.809，k=3 时 0.648 vs 0.588。",
            "<strong>COCO 的默认 anchor 用在 TSR 上是灾难</strong>：平均最佳 IoU 只有 0.589（重新聚类可达 0.847），且 <strong>60.4% 的标志的最佳 anchor 是最小的那一个 <code>[10,13]</code></strong>。<em>「大量样本挤在最小 anchor 上」是一个明确的工程信号：你的 anchor 尺寸下界不够，要么加更小的 anchor，要么加更细的 stride（P2）</em>。",
            "<strong>TSR 的 anchor 长宽比几乎全是 1</strong>（聚类出来是 6.2×6.0、8.2×8.2、11.1×11.1…）。这意味着 9 个 anchor 全部花在<em>尺度</em>上而不是<em>长宽比</em>上——<strong>而这正是 anchor-free 在 TSR 上代价极小的原因：anchor 本来就没在表达长宽比先验</strong>。",
        ]),
        DUAL(
            "多尺度这一步的收益同样要落到数字上。notebook 会统计这份 TSR 分布在三层 FPN 上的负载：<strong>84.9% 的标志落在 P3（stride 8），11.8% 在 P4，只有 3.4% 在 P5</strong>。<em>也就是说 P5 那一层的算力几乎白花了</em>——这直接解释了为什么 TSR 系统常常砍掉 P5、加上 P2。",
            "更刺眼的一个数字：<strong>22.2% 的标志边长小于 8 px，在 stride 8 的特征图上连一个格子都占不满</strong>。对这批样本，无论标签分配怎么改、损失怎么调，信息在下采样时就已经丢了。<em>这是架构层面的天花板，只能靠更细的 stride、更高的输入分辨率或切片推理来解决</em>（C57 模块 02/04）。<strong>能把「这个问题在哪一层，改哪一层才有用」说清楚，是检测工程师和调参工程师的分界线。</strong>",
        ),
        CALLOUT("intuition", "anchor 聚类还有一个常被忽略的用法：<strong>它是数据分布的体检报告，而不只是一个超参生成器</strong>。跑一次 k-means，看「平均最佳 IoU」「BPR（best possible recall）」「多少比例的样本挤在最小/最大 anchor 上」，你就知道了：数据的尺度跨度有多大、现有 stride 够不够细、要不要加 P2。<em>即使你用的是 anchor-free 检测器，这个体检也值得做</em>——notebook 的练习 3 就是把它做成一个可复用的报告函数。"),
    ])),
    ("engineering", "v4/v5：工程集大成，以及「训练期红利」这个概念的成型", "".join([
        P("YOLOv4 与 YOLOv5 几乎没有提出新的检测范式，但它们做了一件更重要的事：<strong>把「有用的技巧」系统地筛了一遍，并按「是否增加推理成本」把它们分成两类</strong>。v4 论文的 <span class=\"term\">Bag of Freebies</span>（BoF，免费赠品）与 <span class=\"term\">Bag of Specials</span>（BoS，特价品）这两个词，是这门课模块 00 那条心法的原始出处。"),
        TABLE(["类别", "定义", "典型成员", "决策规则"], [
            ["<strong>Bag of Freebies</strong>", "<strong>只在训练期付出代价，推理零成本</strong>", "Mosaic、MixUp、CIoU loss、label smoothing、余弦退火、EMA、自适应 anchor", "<strong>默认全开</strong>。唯一成本是训练时间与调参"],
            ["<strong>Bag of Specials</strong>", "增加少量推理成本，换较大精度", "SPP/SPPF、PAN、Mish/SiLU、注意力模块（SE/CBAM）、DIoU-NMS", "<strong>必须逐个算延迟账</strong>。在 2.45 ms 预算下大多数进不来"],
        ]),
        H3("四个真正留下来的结构改动"),
        UL([
            "<strong>CSPNet（Cross Stage Partial）</strong>：把特征图按通道劈成两半，只让一半过密集的残差块，另一半直接短接到末端再拼接。<em>动机不是精度而是「减少重复的梯度信息」</em>——它把计算量降了约 20% 而精度不掉，是纯粹的效率改进。<strong>它是 v4 之后所有 YOLO backbone 的基本积木</strong>（v5 的 C3、v8 的 C2f、RTMDet 的 CSPNeXt 都是它的变体）。",
            "<strong>PAN（Path Aggregation Network）</strong>：在 FPN 的自顶向下之后再加一条自底向上的通路。<em>FPN 把语义从高层送到低层，PAN 把定位信息从低层送回高层</em>。对小目标的收益尤其明显，因为高层的框回归可以拿到低层的精确边缘。",
            "<strong>SPPF（Spatial Pyramid Pooling - Fast）</strong>：用三次串联的 5×5 max-pool 等价替代并联的 5/9/13 池化，输出完全一致但快得多。<em>这是「等价变换换速度」的又一个例子，和第 5 节的重参数化是同一类思想</em>。",
            "<strong>Mosaic 增强</strong>：把 4 张图拼成 1 张训练。三个作用：变相增大 batch 内的场景多样性、<strong>把大目标缩小成小目标（等于免费的小目标数据）</strong>、丰富上下文。<em>代价是训练分布与真实分布不一致，所以最后 10–15 个 epoch 必须关掉（close-mosaic）</em>——这个细节在 v8 里变成了默认配置项（C56 模块 03 展开）。",
        ]),
        DUAL(
            "v5 还有一个工程上影响深远的贡献：<strong>自适应 anchor</strong>。它在训练启动时自动对数据集跑一次 k-means 与遗传算法优化，并给出 BPR（best possible recall）；<em>BPR 低于 0.98 就自动重新聚类</em>。这把「anchor 没配好」这个最常见也最隐蔽的坑变成了自动化流程的一部分。<strong>对 TSR 尤其关键——第 2 节的数字说明，直接用 COCO 默认 anchor 会让 4.1% 的标志在任何 IoU 阈值下都匹配不上</strong>。",
            "另一个容易被忽略的是 <strong>letterbox 与 stride 对齐</strong>：v5 把图像按长边缩放后 padding 到 stride 的整数倍（默认填 114），而不是简单 resize 到正方形。<em>这保住了长宽比，避免标志被拉伸变形</em>——对 TSR 是有语义意义的，因为圆形禁令牌被拉成椭圆会削弱形状先验。<strong>但 letterbox 也是训练-部署不一致的头号来源</strong>：padding 值、是否居中、缩放比例是否取整，任何一处两边不一致，框就会整体偏移（C60 模块 01 会把这些差异逐个量化）。",
        ),
        CALLOUT("intuition", "<strong>面试里被问「YOLOv5 相比 v4 有什么创新」，正确的回答不是列结构，而是指出「v5 本质上不是一篇论文而是一套工程基线」</strong>：自适应 anchor、自动超参进化、完整的导出链路（ONNX/TensorRT/CoreML）、统一的训练-验证-导出接口。<em>它的价值在于把「复现一个检测器」的成本从数周降到数小时</em>。面试官想听的是你能区分「学术贡献」与「工程贡献」，并且知道后者在工业界往往更值钱。"),
    ])),
    ("yolox", "YOLOX 三件套：解耦头 / anchor-free / SimOTA", "".join([
        P("YOLOX 是这条演进线上信息量最大的一篇——因为它的消融表把三个改动的收益<strong>分别</strong>列了出来，这在这个领域很罕见。三件套彼此独立，可以单独采纳。"),
        TABLE(["改动", "解决什么问题", "机制要点", "推理成本"], [
            ["<strong>① 解耦头<br>decoupled head</strong>", "分类与定位<strong>需要的特征不同</strong>，共享一个卷积会互相拖累（分类要语义不变性，定位要空间敏感性）", "1×1 降维后分出两条支路，各自 2 个 3×3；末端三个 1×1 分别出 cls / reg / obj", "<strong>不低</strong>，见下方账"],
            ["<strong>② anchor-free</strong>", "anchor 是超参、要聚类、还会让预测数翻 k 倍", "每个格点直接回归到四条边的距离；正样本由中心先验 + 分配器决定", "<strong>负</strong>（预测数减少 2/3）"],
            ["<strong>③ SimOTA</strong>", "静态 IoU 阈值分配对小目标与密集场景极不公平", "构造代价矩阵，按 <strong>dynamic-k</strong>（k 由该 GT 的候选 IoU 之和决定）动态选正样本", "<strong>零</strong>（纯训练期）"],
        ]),
        P("<strong>解耦头的代价必须自己会算</strong>，因为它是这三件套里唯一有推理成本的。notebook 第 5 节实现了这个计算器，结果值得记住（256 通道、三层 FPN、80 类、输入 640）："),
        TABLE(["检测头", "参数量", "MACs（三层合计）", "相对耦合头"], [
            ["耦合头（1×1，3 anchor × 85）", "65,535", "0.55 G", "1×"],
            ["<strong>解耦头 c_mid=256</strong>（YOLOX 式）", "2,447,957", "<strong>20.55 G</strong>", "<strong>37.5×</strong>"],
            ["解耦头 c_mid=64（轻量化）", "169,685", "1.42 G", "2.6×"],
        ]),
        DUAL(
            "37.5 倍这个数字第一次看到会觉得离谱，但它的构成很简单：<strong>代价的主项是两条支路各 2 个 3×3 卷积，即 <code>4 · c_mid² · 9</code> 每像素</strong>。而耦合头只有 <code>c_in · 255</code>。<em>于是 c_mid 从 256 降到 64，代价降到 1/14.5</em>（3×3 项按 c_mid² 走，降 4 倍就是 16 倍）。<strong>这解释了所有后续工作对解耦头的处理：不是不用，而是把 c_mid 压到很小</strong>——YOLOv8 用 <code>max(c_in/4, 16, reg_max·4)</code>，RTMDet 则用跨层共享权重把参数量摊薄。",
            "<strong>面试高频追问：「解耦头为什么有用？」</strong> 想听的不是「因为解耦了」，而是<em>任务冲突的具体表现</em>：分类要的是平移不变性（标志挪 5 px 还是同一类），定位要的是平移敏感性（挪 5 px 边界就变了）。共享卷积时，这两个梯度方向在同一组权重上打架。YOLOX 的消融显示解耦头不只涨 AP，还<strong>显著加快收敛</strong>——因为梯度冲突消失了。<em>更强的回答会补一句：这也是为什么 IoU 分支/obj 分支要不要独立、放哪条支路上，是个真实的设计选择</em>。",
        ),
        P("<strong>anchor-free 的本质</strong>常被讲错。它不是「不用先验」，而是<strong>把「哪些位置是正样本」这个决定，从「与 anchor 的 IoU」交给了「分配器」</strong>。第 2 节的数据已经暗示了这一点：TSR 的 anchor 长宽比几乎全是 1，anchor 实际上只在编码尺度先验；<em>而尺度先验完全可以由 FPN 的层级分配来提供</em>。所以对 TSR 这种长宽比单一的任务，anchor-free 几乎是纯收益。"),
        CALLOUT("danger", "<p>一个真实的踩坑：<strong>把 YOLOX 的三件套「打包」采纳，然后归因说「YOLOX 涨了 3 AP」</strong>。三件套的收益量级完全不同——<em>SimOTA（纯训练期、零推理成本）通常贡献最大，anchor-free 收益中等且省算力，解耦头收益最小却最贵</em>。在 2.45 ms 的 TSR 预算下，正确的采纳顺序是：<strong>先上 SimOTA（免费）→ 再上 anchor-free（省钱）→ 最后才考虑解耦头，且必须把 c_mid 压到 1/4</strong>。<em>面试里能说出这个排序与理由，比说得出三件套的名字有价值得多。</em></p>", "别打包归因"),
    ])),
    ("reparam", "v6/v7：结构重参数化——训练时多分支，推理时单分支", "".join([
        P("这是这门课里最漂亮的一个机制，也是唯一一个可以<strong>用 <code>assert</code> 严格证明</strong>的机制。它的主张听起来像作弊：训练时用一个复杂的多分支结构（更好优化），推理时把它<strong>数值等价地</strong>折叠成一个单一卷积（更快）。"),
        P("基础是 <span class=\"term\">Conv-BN 融合</span>。推理期的 BatchNorm 是一个逐通道的仿射变换，可以被吸进前面卷积的权重与偏置："),
        MATH("W' = \\frac{\\gamma}{\\sqrt{\\sigma^2+\\epsilon}} \\odot W, \\qquad b' = \\frac{\\gamma\\,(b-\\mu)}{\\sqrt{\\sigma^2+\\epsilon}} + \\beta"),
        P("<strong>RepVGG 把这一招推到了极致</strong>：训练时每个块是三条并行分支（3×3 conv+BN、1×1 conv+BN、identity+BN），推理时合并成一个 3×3 卷积。合并的三步是："),
        ASCII("""训练期（三分支，好优化）                推理期（单个 3x3，好部署）

        x                                        x
        |                                         |
   +----+----+----+                               |
   |         |    |                          +---------+
 3x3+BN   1x1+BN  BN(identity)      ===>     |  3x3    |   数值完全等价
   |         |    |                          +---------+
   +----+----+----+                               |
        (+)                                       y
         |
         y

合并三步：
  (1) 每条分支各自做 Conv-BN 融合  ->  (W_i, b_i)
  (2) 把 1x1 核零填充到 3x3 的**中心**；identity 写成中心为 1 的 3x3 对角核
      (零填充为什么成立：填进去的 0 乘任何值都是 0，包括图像的 padding 区)
  (3) 三个同形状的 3x3 核直接**相加**，偏置也相加   ->  W = W3+W1+Wid, b = b3+b1+bid

收益（C=256, 40x40 特征图）：
  算子数   3 conv + 3 BN + 2 add = 8 个 kernel  ->  1 个
  中间张量 3 份 (每份 0.78 MB fp16)             ->  0 份
  MACs     1.049 G                              ->  0.944 G  (-10%)
  真正的大头不是 FLOPs，而是**访存与 kernel 启动** —— 小模型上这是主要瓶颈"""),
        DUAL(
            "为什么多分支训练更好、单分支推理更快，这两件事同时成立？<strong>因为它们是两个不同的评价函数</strong>。训练期在意的是<em>优化景观</em>——多分支提供了多条梯度通路（identity 分支尤其像残差连接，缓解退化），使深层 plain 网络也能训起来。推理期在意的是<em>访存与并行度</em>——单条 3×3 是 GPU/NPU 上被优化得最好的算子，没有分支就没有中间张量、没有 kernel 启动开销、也不阻碍算子融合。<strong>「训练看优化、推理看访存」是理解这一族方法的钥匙。</strong>",
            "<strong>面试高频：「重参数化会掉点吗？」</strong> 想听的是分层回答：<em>① 数学上不掉，合并是严格等价的（notebook 里 <code>np.allclose</code> 误差 2.7e-15）；② 但 INT8 量化后会掉，而且掉得比原生单分支训练更多</em>。原因是三个分支的权重相加之后，等效核的数值分布往往更长尾（几条分支的极值叠加），per-tensor 量化的 scale 被撑大，其余权重被挤到很少的量化格子里。<strong>解法是 per-channel 量化、或对 rep 块做 QAT</strong>——这正是 C60 模块 03 会重新遇到的问题。能主动提这一点，说明你不是只读了论文摘要。",
        ),
        P("<strong>YOLOv7 的另一条线是辅助头（auxiliary head）与 coarse-to-fine 标签分配</strong>：在网络中部接一个只在训练时存在的辅助检测头，用比主头更宽松的分配（coarse）给它监督，主头用严格的分配（fine）。<em>这又是一个典型的「训练期红利」</em>——推理时辅助头直接丢弃，零成本。它解决的是深层网络中浅层监督不足的问题，与 v9 的 PGI 是同一个动机的两种解法。"),
        CALLOUT("warn", "重参数化有两个前提条件容易被忽略：<strong>① identity 分支要求输入输出通道数相同且 stride=1</strong>（否则恒等映射不存在，只能用 3×3 + 1×1 两条分支）；<strong>② 合并必须在 BN 进入 eval 模式、使用 running statistics 之后做</strong>。<em>用训练期的 batch 统计量去合并，得到的权重是错的，而且不会报错——只会表现为「导出后精度莫名下降」</em>。这属于 C60 讲的训练-部署一致性问题：<strong>凡是「训练时一套、推理时另一套」的机制，都必须配一个数值对拍的 assert</strong>，而不是相信它。"),
    ])),
    ("v8v9", "v8/v9：C2f、TaskAligned 分配与可编程梯度信息", "".join([
        P("YOLOv8 没有论文，只有代码与文档，但它是目前工业界事实上的默认基线。它的改动清单短而准，每一条都能对应到前面讲过的某条主线。"),
        TABLE(["v8 的改动", "属于哪条主线", "具体做了什么", "为什么"], [
            ["<strong>C2f 模块</strong>", "架构（BoS）", "把 v5 的 C3 改成保留更多分支输出的结构，所有中间 bottleneck 的输出都被 concat", "<strong>更丰富的梯度流</strong>，在同等参数量下更好训；思想上和 CSPNet / ELAN 一脉"],
            ["<strong>anchor-free + 解耦头</strong>", "架构", "沿用 YOLOX 路线，但 <strong>去掉了 obj 分支</strong>，c_mid 压到 <code>max(c_in/4, 16, reg_max·4)</code>", "obj 与 cls 的信息高度冗余；压 c_mid 是为了把第 4 节算的 37.5× 降下来"],
            ["<strong>TaskAlignedAssigner</strong>", "<strong>标签分配</strong>", "用 <code>t = s<sup>α</sup>·u<sup>β</sup></code> 联合排序，取 top-k", "让被选中的正样本<strong>同时</strong>分类好、定位好，直接对齐推理时的排序准则"],
            ["<strong>DFL（Distribution Focal Loss）</strong>", "损失", "把每条边的回归变成对 <code>reg_max+1</code> 个离散位置的分布预测，取期望作为最终值", "边界本身是模糊的（遮挡/褪色标志尤其如此），<strong>分布式表示比单点回归更能表达这种不确定性</strong>"],
            ["<strong>close-mosaic</strong>", "训练（BoF）", "最后 10 个 epoch 关闭 Mosaic", "消除训练-推理的分布鸿沟"],
        ]),
        P("<strong>TaskAligned 的公式值得单独看</strong>，因为它是「分配」这条主线的一个分水岭："),
        MATH("t = s^{\\alpha} \\cdot u^{\\beta}, \\qquad s = \\text{分类分数},\\ u = \\text{预测框与 GT 的 IoU},\\ (\\alpha,\\beta) = (0.5, 6)"),
        DUAL(
            "在此之前，分配只看几何（IoU 阈值、中心距离），<strong>而推理时的排序只看分数</strong>——这两者不一致，就产生了经典的 <span class=\"term\">cls-loc misalignment</span>（分类-定位失配）：分数最高的框定位不准、定位最准的框分数不高。<em>NMS 按分数排序，于是它保留的往往不是定位最好的那个框</em>。TaskAligned 的做法是让分配也用「分数 × IoU」来选，<strong>训练期就把两者绑在一起</strong>。",
            "β=6 这个指数值得注意：<strong>它让 IoU 的权重远大于分类分数</strong>。0.88<sup>6</sup>=0.464 而 0.70<sup>6</sup>=0.118——IoU 从 0.70 涨到 0.88，t 就翻了近 4 倍。<em>这是刻意的：分类分数在训练早期几乎没有信息，如果 α 太大，早期会选出一堆定位很差的正样本，形成自我强化的错误</em>。notebook 第 6 节会用这组指数复现一个真实现象：<strong>用「纯分类分数」选 top-1，和用「对齐度量」选 top-1，只有 22% 的情况会选中同一个位置</strong>。",
        ),
        P("<strong>YOLOv9 的 PGI（Programmable Gradient Information）与 GELAN</strong> 走的是另一条路：它主张深层网络中<em>信息在前向传播中不断丢失（information bottleneck），导致梯度不可靠</em>。PGI 的做法是加一条只在训练期存在的<strong>可逆辅助分支</strong>，为主干提供「未被压缩」的梯度信息，推理时整条分支移除。<em>又是一次训练期红利</em>——和 v7 的辅助头动机一致，但实现更系统。"),
        CALLOUT("intuition", "把 v8 的清单重新排一下，你会看到一个清晰的模式：<strong>五条改动里有三条（TaskAligned、DFL 的训练侧、close-mosaic）是零推理成本的，剩下两条（C2f、解耦头）都被刻意做了成本控制</strong>。<em>这就是模块 00 那条心法在一个成熟工程产品上的完整体现</em>：不是不用贵的东西，而是<strong>先把免费的全部吃干净，再为每一个收费项单独算账</strong>。你在自己的项目里做技术选型时，这个顺序同样适用。"),
    ])),
    ("v10", "v10：一致双分配，NMS 真的被去掉了", "".join([
        P("YOLOv10 解决的是模块 00 第 3 节那本账里最刺眼的一项：<strong>NMS 是端到端延迟中唯一随场景波动的部分</strong>（notebook 里 p99/p50 = 1.40）。而它的解法既不是 DETR 的 query，也不是简单地「训练时用一对一」。"),
        ASCII("""YOLOv10 的一致双分配 (consistent dual assignments)

  训练期：一个 backbone/neck，**两个头**
     +-------------------+
     |  one-to-many head |  每个 GT 分配 top-k 个正样本  -> 监督信号密集，收敛快
     |   (o2m, 主监督)   |
     +-------------------+
              |  两个头用**同一个**匹配度量  m = s^alpha * u^beta   <-- 关键
     +-------------------+
     |  one-to-one head  |  每个 GT 只分配 1 个正样本    -> 训练模型自己去重
     |   (o2o)           |
     +-------------------+

  推理期：**只保留 o2o 头，o2m 头整个丢弃，不跑 NMS**

  为什么必须「一致」：
    若两个头用不同度量，o2o 选中的位置常常不在 o2m 的 top-k 里
    -> 同一个位置被一个头当正样本、被另一个头当负样本
    -> 梯度互相抵消，o2o 头学不出干净的单峰响应，推理时仍有重复框

  notebook 实测（12 个标志 x 20 组随机种子）：
    两头同用对齐度量        o2o 的 top-1 落在 o2m 的 top-10 内 = 100%
    o2o 改用纯分类分数      落在 top-10 内 = 73.8%，top-1 完全相同仅 22.1%"""),
        P("notebook 第 6 节会把「不去重会怎样」也跑出来：同一批 12 个交通标志，一对多分支产生 <strong>120 个候选框</strong>（每 GT 10 个），必须靠 NMS 压回 12 个；一对一分支直接输出 <strong>12 个</strong>。而更有意思的是 NMS 阈值的敏感性："),
        TABLE(["NMS IoU 阈值", "一对多输出（120 框）", "一对一输出（12 框）"], [
            ["0.30 / 0.40 / 0.45", "12 ✅", "12 ✅"],
            ["0.50", "13（漏删 1）", "12 ✅"],
            ["0.60（常用默认值）", "<strong>15（漏删 3）</strong>", "12 ✅"],
            ["0.70", "<strong>18（漏删 6）</strong>", "12 ✅"],
        ]),
        DUAL(
            "这张表说明了无 NMS 的第二个收益，而且它常被低估：<strong>去掉 NMS 就去掉了一个必须逐场景调、且调不好会同时产生漏检和重复的超参</strong>。阈值调高留重复框，调低会把<em>真正相邻的两个目标</em>合并成一个——而 TSR 恰好充满相邻目标：门架上并排的三块限速牌、主辅牌组合、限速牌加解除牌。<em>「NMS 把两块并排的标志删成一块」是一类真实且很难查的漏检</em>。",
            "但要诚实地说清收益的边界。<strong>无 NMS 买到的主要是延迟的<em>确定性</em>，不必然是延迟的<em>均值</em></strong>。在模块 00 的账里 NMS 只占 12%（0.30 / 2.42 ms）——如果你的场景候选框本来就不多（高速上的 TSR 就是这样），去掉它省下的绝对时间有限。<em>真正的收益在 p99：雨夜误检爆炸时 NMS 从 0.05 ms 涨到 0.94 ms，而无 NMS 的管线延迟是常数</em>。<strong>面试里被问「无 NMS 值不值」，标准答案是「取决于你的场景候选框分布，先测 p99 再决定」，而不是「值/不值」。</strong>",
        ),
        P("<strong>和 DETR 的一对一匹配是不是一回事？</strong> 这是本节最高频的面试题。相同点：都用「一个 GT 只对应一个预测」来在<em>训练期</em>压制重复，而不是在推理期删重复。不同点有三个，缺一个答案就不完整："),
        UL([
            "<strong>匹配范围</strong>：DETR 是全局二分图匹配（匈牙利算法，O(n³)，所有 query 与所有 GT 一起求最优解）；v10 是<strong>逐 GT 独立取 top-1</strong>，没有全局最优性保证，但快得多且实现简单。",
            "<strong>监督密度</strong>：DETR 只有一对一这一路监督，是它需要 500 epoch 的根因之一；v10 用 o2m 头<strong>额外提供密集监督</strong>，且两头共享 backbone/neck，等于免费拿到 DETR 拿不到的东西。（C54 模块 04 会讲这正是 Co-DETR / Group-DETR 反过来向 YOLO 学的东西。）",
            "<strong>预测的载体</strong>：DETR 的 query 是可学习的、与位置解耦的向量；v10 的 o2o 头仍然是<strong>密集预测</strong>，每个格点一个预测。<em>所以 v10 保留了 CNN 检测器对小目标的所有优势，也保留了「预测数固定为格点数」这个部署上的确定性</em>。",
        ]),
        CALLOUT("intuition", "把这三代放在一起看，会得到一个很干净的结论：<strong>「一对一」是推理端的需求（要输出一个不含重复的集合），不是训练端的最优（一对一的监督太稀疏）</strong>。<em>所以最终的赢家形态是「训练时一对多 + 一对一双路，推理时只留一对一」</em>——YOLOv10 从 CNN 侧到达这个形态，Co-DETR / Group-DETR 从 Transformer 侧到达同一个形态。<strong>两条路殊途同归，本身就是这个结论正确的最好证据。</strong>"),
    ])),
    ("attribution", "收益归因：架构红利还是训练技巧红利", "".join([
        P("这是本模块最有面试价值的一节。<strong>被问「YOLO 从 v5 到 v8 涨的这几个点是怎么来的」，能做归因的人和只会背清单的人差距立刻显现</strong>。核心事实是：<em>这条演进线上的大部分收益来自训练侧，而不是架构侧</em>。"),
        TABLE(["改动", "红利类型", "推理成本", "在 2.45 ms 预算下的采纳优先级"], [
            ["<strong>标签分配</strong>（ATSS/SimOTA/TaskAligned）", "<strong>训练期</strong>", "零", "<strong>P0 · 必须上</strong>。同网络同数据换分配可差 3–5 AP（模块 02）"],
            ["<strong>Mosaic / close-mosaic / 强增强</strong>", "<strong>训练期</strong>", "零", "<strong>P0</strong>。对小目标与长尾尤其有效（C56）"],
            ["<strong>结构重参数化</strong>", "训练期（推理更快）", "<strong>负</strong>", "<strong>P0</strong>，但要配 INT8 精度验证"],
            ["<strong>辅助头 / PGI</strong>", "<strong>训练期</strong>", "零", "P1。训练变慢、显存变大，收益在深模型上更明显"],
            ["<strong>anchor-free</strong>", "架构", "<strong>负</strong>（预测数减 2/3）", "<strong>P0</strong>（对 TSR：长宽比单一，几乎纯收益）"],
            ["<strong>更好的 loss</strong>（CIoU/DFL）", "训练期", "DFL 有极小的解码成本", "P1"],
            ["<strong>backbone/neck 改造</strong>（CSP/C2f/ELAN）", "架构", "看具体设计，通常持平或略降", "P1，必须实测"],
            ["<strong>解耦头</strong>", "架构", "<strong>正，且大</strong>（c_mid=256 时 37.5×）", "P2，且必须压 c_mid"],
            ["<strong>注意力模块</strong>（SE/CBAM/Transformer block）", "架构", "<strong>正</strong>，且常常破坏算子融合", "<strong>P3</strong>，绝大多数进不了预算"],
        ]),
        DUAL(
            "为什么训练期红利这么大？<strong>因为检测器的瓶颈长期不在「表达能力」而在「优化」</strong>。一个 stride 8 的特征图有 6400 个格点，其中只有几十个该是正样本；<em>「哪几十个」这个选择直接决定了绝大部分梯度的方向</em>。选错了，再强的 backbone 也在学错的东西。这就是模块 02 整整一个模块讲标签分配的原因，也是那句「<strong>标签分配是检测器真正的胜负手</strong>」的含义。",
            "<strong>做归因时最常见的错误是「不公平比较」。</strong> 新模型往往同时换了架构、分配、增强、训练轮数、输入分辨率与后处理阈值，然后把总收益记在架构头上。<em>正确的消融必须单变量、同 epoch、同增强、同分辨率、同调参预算</em>——而这在论文里几乎从不成立。<strong>更要命的是种子方差：检测任务同配置不同种子的 mAP 波动典型在 ±0.2–0.5，所以「+0.3 的提升」很可能是噪声</strong>（C61 模块 01 会给出功效分析：要多少种子才能可靠检出 +0.3）。面试里主动提这一点，通常是全场最加分的一句话。",
        ),
        H3("回到 TSR：这张表怎么用"),
        P("假设你接手一个交通标志检测项目，baseline 是 YOLOv5-S，指标不达标。<strong>按上表的优先级，你的动作顺序应该是</strong>："),
        UL([
            "<strong>① 先把免费的吃干净</strong>：换 TaskAligned 或 SimOTA 分配、开 Mosaic + close-mosaic、按自己的数据重新聚类 anchor（第 2 节的数字：COCO 默认 anchor 让 4.1% 的标志匹配不上）。<em>这一步不增加任何推理延迟</em>。",
            "<strong>② 再动架构里「负成本」的部分</strong>：anchor-free（TSR 长宽比单一，先验损失极小）、rep 块（推理更快）。",
            "<strong>③ 然后才是花钱的</strong>：加 P2 层（对 22.2% 边长 &lt; 8 px 的标志是唯一有效的手段，但显存与计算按分辨率平方涨）、解耦头（压 c_mid）。<em>每一项都要在目标硬件上实测 p99 再决定</em>。",
            "<strong>④ 最后重新算账</strong>：改完之后端到端 p99 是否仍在 2.45 ms 内？如果不在，回到模块 00 的三条出路（tiny 档 + INT8 / 降频 / ROI）。",
        ]),
        CALLOUT("danger", "<p><strong>面试里最危险的一个回答是「我们换成了 YOLOv8，涨了 2 个点」。</strong> 追问必然是「那 2 个点是从哪来的？」——如果你答不上来，前面所有的技术细节都会打折扣。<em>正确的叙事结构永远是：baseline 是什么 → 改了哪一项 → 单独测得多少 → 代价是什么 → 怎么验证它不是噪声</em>。<strong>而这门课教你的每一个机制，都应该被组织成这个结构存进你的项目叙事里</strong>（C61 模块 04 会把这件事做成模板）。</p>", "归因不清 = 全场失分"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("YOLO 这条线走到 v10/v11/v12 之后，边际收益已经明显递减——COCO 上的 AP 提升越来越依赖训练配方而非结构。真正开放的问题在别处。"),
        UL([
            "<strong>「YOLO 版本号」已经不再是技术谱系。</strong> v6（美团）、v7（原作者线）、v8/v11（Ultralytics）、v9、v10（清华）来自完全不同的团队，编号只是命名权的结果。<em>把它们理解成「同一条演进线的连续迭代」是错的</em>——它们更像是在同一组公开技巧上做不同排列组合。这也是为什么归因（第 8 节）比背版本号重要得多。",
            "<strong>结构重参数化与量化的冲突尚无干净解法。</strong> 合并后的等效核数值分布更长尾，INT8 per-tensor 量化掉点显著大于原生单分支。目前只能靠 per-channel、混合精度或 QAT 缓解。<em>「量化友好的重参数化」是一个明确存在但还没被解决的问题</em>（C60 模块 03）。",
            "<strong>一对一分配的训练效率仍是瓶颈。</strong> v10 的双分配是一个务实的绕道：用 o2m 提供密集监督、用 o2o 提供无重复输出。<em>但「为什么一对一的监督必然稀疏、能否设计出既一对一又密集的监督」目前没有理论答案</em>。这与 C54 模块 04 讲的 DETR 收敛难题是同一个问题的两面。",
            "<strong>标签分配缺少可优化的形式化目标。</strong> 从 IoU 阈值到 ATSS 到 OTA 到 TaskAligned，每一步都由实验驱动。OTA 的最优传输视角最接近形式化，但代价矩阵仍是手工设计的。<em>「什么是最优分配」至今是开放问题</em>（模块 02 会把这条线完整走一遍）。",
            "<strong>NAS 与手工设计的边界。</strong> 大量工作用神经架构搜索找 backbone/neck，但搜索出的结构在<em>目标硬件</em>上未必快（FLOPs 与实测延迟的相关性在小模型上很弱）。<strong>硬件感知的 NAS（latency-aware NAS）是正确方向，但需要在每种芯片上重建延迟查找表</strong>——对车端多硬件平台是一个组合爆炸问题。",
            "<strong>面向长尾细粒度的检测器设计几乎是空白。</strong> YOLO 全线都在 COCO 的 80 类均衡设定下演进，而 TSR 是 200+ 类、极度长尾、且类间差异极细（限速 60 vs 限速 80 只差一个字符）。<em>「检测器结构该为细粒度长尾做什么改变」在学术界几乎没有对应工作</em>——这也是 C55/C58 存在的理由，以及两级方案（检测 + 分类）在量产中仍占主流的原因。",
        ]),
        CALLOUT("paper", "必读（按本模块顺序）：<em>You Only Look Once: Unified, Real-Time Object Detection</em>(Redmon et al., CVPR 2016) —— 读第 2 节的输出张量定义与第 4.4 节的失败分析；<em>YOLO9000: Better, Faster, Stronger</em>(CVPR 2017) —— <strong>dimension cluster 那一小节必须读原文</strong>，它给出了 1−IoU 距离的动机；<em>YOLOv4: Optimal Speed and Accuracy of Object Detection</em>(2020) —— Bag of Freebies / Bag of Specials 的划分是本课「训练期红利」心法的出处；<em>YOLOX: Exceeding YOLO Series in 2021</em> —— <strong>Table 2 的逐项消融是整个领域信息量最大的一张表</strong>；<em>RepVGG: Making VGG-style ConvNets Great Again</em>(CVPR 2021) —— 公式极简，务必自己推一遍再看 notebook 的 assert；<em>TOOD: Task-aligned One-stage Object Detection</em>(ICCV 2021) —— TaskAligned 度量的出处；<em>YOLOv7</em>(CVPR 2023) 的辅助头与 <em>YOLOv9</em>(2024) 的 PGI；<em>YOLOv10: Real-Time End-to-End Object Detection</em>(NeurIPS 2024) —— 一致双分配，注意读它对「为什么必须一致」的消融。相邻课程：模块 02（标签分配全展开）、模块 03（RTMDet）、C54（DETR 的一对一匹配）、C57（小目标）、C60（重参数化与量化的冲突）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · YOLO 家族演进（网格容量 / anchor 聚类 / 重参数化 / 解耦头账 / 双分配）

这个 notebook 不训练模型，它把 YOLO 演进史上**四个关键机制**从零实现出来，
并且每一个都用 `assert` 把「它到底带来了什么」钉死成数字。

**本 notebook 你会亲手实现：**
1. **YOLOv1 的结构性容量上限** —— 证明它的失败是输出张量形状决定的，不是参数量不够
2. **anchor 维度聚类（k-means with 1−IoU 距离）** —— 并证明 IoU 距离优于欧氏距离、
   COCO 默认 anchor 用在交通标志上是灾难
3. **Conv+BN 融合与 RepVGG 三分支合并** —— 完整的**数值等价证明**（误差 < 1e-14）
4. **解耦头 vs 耦合头的参数量/FLOPs 账** —— 那个 37.5× 是怎么来的、怎么压下去
5. **一对多 vs 一对一分配** —— 复现 YOLOv10 「一致双分配」为什么必须"一致"

> 心智模型：**凡是只在训练期付出代价的改动，都是免费的午餐。
> 所以看到一个新机制，先问它的代价落在训练期还是推理期。**"""),
    md("""## 1 · YOLOv1 的容量上限是**结构性**的

v1 每个格子输出 `B` 个框 + **一份**类别向量。这两条限制在参数量增加时一条都不会消失。

用一个合成的 TSR 场景来量化：一个施工区门架上 5 块牌子挤在 100 px 内，路侧另有 4 块零散标志。"""),
    code("""import numpy as np, math, json, itertools
rng = np.random.default_rng(53)

def yolov1_capacity(gt_boxes, gt_cls, img=448, S=7, B=2):
    '''YOLOv1: SxS 网格，每格 B 个框、**一份**类别向量（先到先得）。
       返回 (可正确表达的目标数, 因每格超过 B 个框而丢失, 因每格只有一份类别向量而丢失)。'''
    cell = img / S
    buckets = {}
    for (cx, cy, w, h), c in zip(gt_boxes, gt_cls):
        key = (int(min(S - 1, cx // cell)), int(min(S - 1, cy // cell)))
        buckets.setdefault(key, []).append(c)
    ok = lost_box = lost_cls = 0
    for key, cs in sorted(buckets.items()):
        keep = min(len(cs), B)
        lost_box += len(cs) - keep          # (1) 每格最多 B 个框
        main = cs[0]                        # (2) 每格只有一份类别向量
        same = sum(1 for c in cs[:keep] if c == main)
        lost_cls += keep - same
        ok += same
    return ok, lost_box, lost_cls, buckets

# 合成场景：门架 5 块牌（类别 0/1/0/2/0）+ 路侧 4 块零散标志
gt, cls = [], []
for i in range(5):
    gt.append((150 + i * 22, 120, 18, 18)); cls.append([0, 1, 0, 2, 0][i])
for i in range(4):
    gt.append((60 + i * 95, 260 + (i % 2) * 30, 24, 24)); cls.append(i % 3)

ok, lb, lc, buckets = yolov1_capacity(gt, cls)
print('场景里共 %d 个交通标志，448 输入 / 7x7 网格（每格 %.0f px）' % (len(gt), 448 / 7))
print('\\n每个被占用的格子里挤了几个标志：')
for key, cs in sorted(buckets.items()):
    flag = '   <-- 超过 B=2' if len(cs) > 2 else ('   <-- 两个不同类别，只能保住一个'
                                                  if len(set(cs)) > 1 else '')
    print('   格子 %s  %d 个  类别 %s%s' % (str(key), len(cs), cs, flag))

print('\\nYOLOv1 结构上最多能表达: %d / %d' % (ok, len(gt)))
print('   因「每格 B=2」丢失          : %d' % lb)
print('   因「每格一份类别向量」丢失  : %d' % lc)
assert (ok, lb, lc) == (6, 1, 2), (ok, lb, lc)
assert ok + lb + lc == len(gt)"""),
    code("""def dense_capacity(gt_boxes, img=640, stride=8, n_pred=3, src=448):
    '''现代 dense head：stride 8 的格点，每格 n_pred 个预测，且**每个预测自带类别**。'''
    scale = img / src
    b = {}
    for (cx, cy, w, h) in gt_boxes:
        k = (int(cx * scale // stride), int(cy * scale // stride))
        b[k] = b.get(k, 0) + 1
    lost = sum(max(0, v - n_pred) for v in b.values())
    return len(gt_boxes) - lost, lost

got, lost = dense_capacity(gt)
print('同一批标志交给 stride 8 的 dense head（640 输入 -> 80x80 格点）:')
print('   可表达 %d / %d，丢失 %d' % (got, len(gt), lost))
assert (got, lost) == (9, 0)

print('\\n%-34s %10s %12s' % ('结构', '格点数', '可表达上限'))
for name, S, B in [('YOLOv1  7x7, B=2, 每格 1 个类别', 7, 2),
                   ('YOLOv2  13x13, 5 anchor, 各自带类别', 13, 5),
                   ('YOLOv3+ stride8 80x80, 3 anchor', 80, 3)]:
    print('%-34s %10d %12d' % (name, S * S, S * S * B))

print('\\n⚠️  v1 的失败是**表达能力**问题不是**容量**问题 —— 加参数一条都解决不了。')
print('✅ 可迁移的判断法：模型在某类样本上**系统性**失败时，先问')
print('   「这是容量问题（加参数能解决）还是表达能力问题（必须改输出结构）」。')"""),
    md("""## 2 · anchor 维度聚类：k-means with 1−IoU 距离

YOLOv2 的 dimension cluster。**距离必须用 1−IoU 而不是欧氏距离**，
因为欧氏距离会被大框主导：300×300 vs 320×320 的欧氏距离是 28、IoU 0.88；
8×8 vs 10×10 的欧氏距离只有 2.8、IoU 却只有 0.64。

数据用**针孔模型合成的交通标志尺寸分布**：`px = f·S/Z`，
物理尺寸 0.6/0.8/1.2 m，距离 10–120 m，1920 宽的图缩放到 1280 的网络输入。"""),
    code("""def make_tsr_wh(n=3000, seed=7, img_w=1920, net_w=1280, hfov=60.0):
    '''按针孔相机模型合成交通标志的 (w,h) 分布 —— 物理上可解释、可复现。'''
    r = np.random.default_rng(seed)
    f = (img_w / 2) / math.tan(math.radians(hfov) / 2)      # 焦距（像素）
    size_m = r.choice([0.6, 0.8, 1.2], size=n, p=[0.60, 0.25, 0.15])   # 标志物理尺寸
    dist_m = r.uniform(10.0, 120.0, size=n)                            # 距离
    w = f * size_m / dist_m * (net_w / img_w) * r.normal(1.0, 0.08, n)  # 含标注/姿态噪声
    h = w * r.normal(1.0, 0.10, n)                                     # 长宽比 ~1
    return np.stack([np.abs(w), np.abs(h)], 1)

def wh_iou(wh, centers):
    '''只比 (w,h) 的 IoU（两框中心对齐）。wh:(n,2) centers:(k,2) -> (n,k)'''
    inter = (np.minimum(wh[:, None, 0], centers[None, :, 0])
             * np.minimum(wh[:, None, 1], centers[None, :, 1]))
    union = wh[:, None, 0] * wh[:, None, 1] + centers[None, :, 0] * centers[None, :, 1] - inter
    return inter / union

def kmeans_anchors(wh, k, iters=100, seed=0, metric='iou'):
    r = np.random.default_rng(seed)
    c = wh[r.choice(len(wh), k, replace=False)].astype(float).copy()
    for _ in range(iters):
        d = (1.0 - wh_iou(wh, c)) if metric == 'iou' else \\
            np.linalg.norm(wh[:, None, :] - c[None, :, :], axis=2)
        a = d.argmin(1)
        new = c.copy()
        for j in range(k):
            m = a == j
            if m.any():
                new[j] = wh[m].mean(0)
        if np.allclose(new, c):
            break
        c = new
    return c[np.argsort(c[:, 0] * c[:, 1])]            # 按面积排序，便于分配到 FPN 层

def mean_best_iou(wh, c):
    return float(wh_iou(wh, c).max(1).mean())

def bpr(wh, c, thr=0.25):
    '''best possible recall: 有多少比例的框能找到 IoU>=thr 的 anchor。'''
    return float((wh_iou(wh, c).max(1) >= thr).mean())

wh = make_tsr_wh()
print('合成的 TSR 尺寸分布（网络输入 1280 尺度下）:')
print('   最小 %.1f px   中位 %.1f px   最大 %.1f px'
      % (wh.min(), np.median(np.sqrt(wh[:, 0] * wh[:, 1])), wh.max()))
print('\\n%6s %18s %12s' % ('k', '平均最佳 IoU', 'BPR@0.25'))
res = {}
for k in (1, 3, 6, 9, 12):
    a = kmeans_anchors(wh, k)
    res[k] = (mean_best_iou(wh, a), bpr(wh, a))
    print('%6d %18.4f %12.4f' % (k, res[k][0], res[k][1]))
assert res[1][0] < res[3][0] < res[6][0] < res[9][0] < res[12][0], 'anchor 越多拟合越好'
assert res[9][1] == 1.0 and res[3][1] < 1.0
print('\\n✅ k=9 时平均最佳 IoU %.4f、BPR=1.0（每个标志都能找到 IoU>=0.25 的 anchor）' % res[9][0])"""),
    code("""# ① IoU 距离 vs 欧氏距离
print('%6s %16s %16s   %s' % ('k', 'IoU 距离', '欧氏距离', '差值'))
for k in (3, 6, 9):
    ai = kmeans_anchors(wh, k, metric='iou')
    ae = kmeans_anchors(wh, k, metric='euclid')
    mi, me = mean_best_iou(wh, ai), mean_best_iou(wh, ae)
    print('%6d %16.4f %16.4f   %+.4f' % (k, mi, me, mi - me))
    assert mi > me, 'IoU 距离在 k=%d 上应优于欧氏距离' % k
print('\\n>>> 欧氏距离被大框主导，聚类中心被拽走，小目标分不到 anchor。')

# ② 直接用 COCO 的默认 anchor 会怎样
COCO_ANCHORS = np.array([[10, 13], [16, 30], [33, 23], [30, 61], [62, 45],
                         [59, 119], [116, 90], [156, 198], [373, 326]], float)
a9 = kmeans_anchors(wh, 9)

def at_smallest(wh, a):
    '''有多少比例的框，其最佳 anchor 是**最小的那一个** -> anchor 下界不够的信号。'''
    return float((wh_iou(wh, a).argmax(1) == int(np.argmin(a[:, 0] * a[:, 1]))).mean())

print('\\n%-26s %14s %10s %16s' % ('anchor 来源', '平均最佳 IoU', 'BPR@0.25', '挤在最小 anchor'))
for name, a in [('COCO 默认', COCO_ANCHORS), ('在 TSR 上重新聚类', a9)]:
    print('%-26s %14.4f %10.4f %15.1f%%'
          % (name, mean_best_iou(wh, a), bpr(wh, a), 100 * at_smallest(wh, a)))

assert bpr(wh, COCO_ANCHORS) < 0.97 and bpr(wh, a9) == 1.0
assert mean_best_iou(wh, a9) > mean_best_iou(wh, COCO_ANCHORS) + 0.2
assert at_smallest(wh, COCO_ANCHORS) > 0.5 > at_smallest(wh, a9)

print('\\n重新聚类得到的 9 个 anchor:')
print('  ', [[round(x, 1) for x in p] for p in a9.tolist()])
print('\\n⚠️  COCO 默认 anchor 让 %.1f%% 的标志在任何 IoU 阈值下都匹配不上，'
      % (100 * (1 - bpr(wh, COCO_ANCHORS))))
print('    且 %.1f%% 的标志全挤在最小的 [10,13] 上 —— 这是「anchor 下界不够」的明确信号。'
      % (100 * at_smallest(wh, COCO_ANCHORS)))
print('✅ 注意聚出来的 anchor 长宽比几乎全是 1 —— **TSR 的 anchor 只在编码尺度先验**，')
print('   完全没在编码长宽比先验。这正是 anchor-free 在 TSR 上代价极小的原因。')"""),
    code("""# ③ 多尺度：这份分布在三层 FPN 上的负载
side = np.sqrt(wh[:, 0] * wh[:, 1])
print('%-22s %10s %10s' % ('FPN 层', '样本数', '占比'))
loads = []
for lo, hi, name in [(0, 32, 'P3 (stride 8)'), (32, 64, 'P4 (stride 16)'),
                     (64, 1e9, 'P5 (stride 32)')]:
    m = (side >= lo) & (side < hi)
    loads.append(m.sum())
    print('%-22s %10d %9.1f%%' % (name, m.sum(), 100 * m.mean()))

tiny = (side < 8).sum()
assert loads[0] > 0.8 * len(wh), 'TSR 的绝大多数目标都落在最细的那一层'
assert loads[2] < 0.05 * len(wh), 'P5 几乎没有负载'
assert tiny > 0.2 * len(wh)

print('\\n>>> %.1f%% 落在 P3，只有 %.1f%% 落在 P5 —— **P5 的算力几乎白花**。'
      % (100 * loads[0] / len(wh), 100 * loads[2] / len(wh)))
print('>>> 更刺眼的是：%.1f%% 的标志边长 < 8 px，在 stride 8 上**连一个格子都占不满**。'
      % (100 * tiny / len(wh)))
print('⚠️  对这批样本，无论标签分配怎么改、损失怎么调，信息在下采样时就已经丢了。')
print('✅ 这是架构层面的天花板 —— 只能靠更细的 stride(P2)、更高输入分辨率或切片推理解决(C57)。')"""),
    md("""## 3 · Conv+BN 融合：最简单的一次结构重参数化

推理期的 BatchNorm 是一个逐通道的仿射变换，可以被**严格等价地**吸进前面卷积的权重与偏置：

$$W' = \\frac{\\gamma}{\\sqrt{\\sigma^2+\\epsilon}} \\odot W, \\qquad
b' = \\frac{\\gamma\\,(b-\\mu)}{\\sqrt{\\sigma^2+\\epsilon}} + \\beta$$

先自己写一个 numpy conv2d，然后把这个等式用 `assert` 钉死。"""),
    code("""def conv2d(x, W, b=None, stride=1, pad=0):
    '''x:(N,Cin,H,W)  W:(Cout,Cin,kh,kw)  -> (N,Cout,Ho,Wo)。零填充。'''
    N, Cin, H, Wd = x.shape
    Cout, Cin2, kh, kw = W.shape
    assert Cin == Cin2, '输入通道不匹配'
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    Ho = (H + 2 * pad - kh) // stride + 1
    Wo = (Wd + 2 * pad - kw) // stride + 1
    out = np.zeros((N, Cout, Ho, Wo))
    for i in range(kh):                       # 按核内位置累加，避免显式 im2col
        for j in range(kw):
            patch = xp[:, :, i:i + stride * Ho:stride, j:j + stride * Wo:stride]
            out += np.einsum('nchw,oc->nohw', patch, W[:, :, i, j])
    if b is not None:
        out += b.reshape(1, -1, 1, 1)
    return out

def bn_infer(x, gamma, beta, mean, var, eps=1e-5):
    '''**推理期**的 BN：用 running statistics，是一个逐通道仿射变换。'''
    r = lambda v: v.reshape(1, -1, 1, 1)
    return r(gamma) * (x - r(mean)) / np.sqrt(r(var) + eps) + r(beta)

def fuse_conv_bn(W, b, gamma, beta, mean, var, eps=1e-5):
    '''把 BN 吸进卷积。返回等价的 (W', b')。'''
    s = gamma / np.sqrt(var + eps)
    return W * s.reshape(-1, 1, 1, 1), (b - mean) * s + beta

C, H = 8, 7
x = rng.normal(size=(2, C, H, H))
W3 = rng.normal(size=(C, C, 3, 3)) * 0.2
b3 = rng.normal(size=C) * 0.1
g3, be3 = rng.normal(1, .2, C), rng.normal(0, .2, C)
mu3, v3 = rng.normal(0, .3, C), rng.uniform(.5, 2., C)      # var 必须为正

y_two_step = bn_infer(conv2d(x, W3, b3, pad=1), g3, be3, mu3, v3)   # conv 然后 bn
Wf, bf = fuse_conv_bn(W3, b3, g3, be3, mu3, v3)
y_fused = conv2d(x, Wf, bf, pad=1)                                  # 融合后的单个 conv

err = float(np.abs(y_two_step - y_fused).max())
print('Conv->BN 两步   输出形状 %s' % (y_two_step.shape,))
print('融合成单个 conv 输出形状 %s' % (y_fused.shape,))
print('最大绝对误差 %.3e   （float64 机器精度量级）' % err)
assert np.allclose(y_two_step, y_fused, atol=1e-10), err
assert err < 1e-12
print('\\n✅ **严格数值等价**，不是近似。推理时 BN 层可以整个消失：')
print('   少一次逐元素读写、少一个 kernel 启动，且不再阻碍算子融合。')"""),
    md("""## 4 · RepVGG：三分支合并成一个 3×3

训练时三条并行分支（3×3+BN、1×1+BN、identity+BN），推理时合并成单个 3×3。

合并三步：① 每条分支各自 Conv-BN 融合 → ② 把 1×1 核零填充到 3×3 的**中心**、
identity 写成中心为 1 的对角核 → ③ 三个同形状的核直接相加。

> 零填充为什么成立：填进去的 0 乘任何值都是 0，**包括图像 padding 区的 0**，所以边界也等价。"""),
    code("""def pad_1x1_to_3x3(W1):
    '''(Cout,Cin,1,1) -> (Cout,Cin,3,3)，1x1 核放到 3x3 的中心。'''
    return np.pad(W1, ((0, 0), (0, 0), (1, 1), (1, 1)))

def identity_to_3x3(C):
    '''恒等映射写成 3x3 卷积核：中心位置的对角线为 1，其余为 0。'''
    K = np.zeros((C, C, 3, 3))
    for c in range(C):
        K[c, c, 1, 1] = 1.0
    return K

# 三条分支各自的参数（identity 分支要求 Cin==Cout 且 stride=1）
W1 = rng.normal(size=(C, C, 1, 1)) * 0.3
g1, be1, mu1, v1 = rng.normal(1, .2, C), rng.normal(0, .2, C), rng.normal(0, .3, C), rng.uniform(.5, 2., C)
gi, bei, mui, vi = rng.normal(1, .2, C), rng.normal(0, .2, C), rng.normal(0, .3, C), rng.uniform(.5, 2., C)
zero = np.zeros(C)

# —— 训练期：三分支相加 ——
y3 = bn_infer(conv2d(x, W3, None, pad=1), g3, be3, mu3, v3)
y1 = bn_infer(conv2d(x, W1, None, pad=0), g1, be1, mu1, v1)
yid = bn_infer(x, gi, bei, mui, vi)
y_multi = y3 + y1 + yid

# —— 推理期：合并成单个 3x3 ——
W3f, b3f = fuse_conv_bn(W3, zero, g3, be3, mu3, v3)                       # 步骤 ①
W1f, b1f = fuse_conv_bn(W1, zero, g1, be1, mu1, v1)
Wif, bif = fuse_conv_bn(identity_to_3x3(C), zero, gi, bei, mui, vi)
W_merged = W3f + pad_1x1_to_3x3(W1f) + Wif                                # 步骤 ②③
b_merged = b3f + b1f + bif
y_merged = conv2d(x, W_merged, b_merged, pad=1)

err = float(np.abs(y_multi - y_merged).max())
print('训练期三分支相加 -> %s' % (y_multi.shape,))
print('推理期单个 3x3   -> %s' % (y_merged.shape,))
print('最大绝对误差 %.3e' % err)
assert np.allclose(y_multi, y_merged, atol=1e-10), err
assert W_merged.shape == (C, C, 3, 3)
# 边界也必须等价（零填充区同样成立）—— 单独检查最外圈
assert np.allclose(y_multi[:, :, 0, :], y_merged[:, :, 0, :], atol=1e-10), '上边界不等价'
assert np.allclose(y_multi[:, :, :, -1], y_merged[:, :, :, -1], atol=1e-10), '右边界不等价'
print('\\n✅ **三分支 = 单个 3x3，数值严格等价，边界也等价。**')
print('   训练时用多分支（多条梯度通路，好优化）；推理时用单分支（无中间张量，好部署）。')"""),
    code("""def rep_block_cost(C=256, H=40, W=40, dtype_bytes=2):
    '''训练期三分支 vs 推理期单 3x3 的算子/访存/计算账。'''
    hw = H * W
    macs3, macs1 = C * C * 9 * hw, C * C * 1 * hw
    bn_ops = 2 * C * hw                                   # BN 推理 = 一次乘一次加
    train_macs = macs3 + macs1 + 3 * bn_ops + 2 * C * hw  # 3 个 BN + 2 次逐元素加
    tensor = C * hw * dtype_bytes                         # 一份中间张量的字节数
    return {
        'train_macs': train_macs, 'infer_macs': macs3,
        'train_kernels': 3 + 3 + 2, 'infer_kernels': 1,   # 3 conv + 3 bn + 2 add
        'train_tensors': 3, 'infer_tensors': 0,
        'tensor_MB': tensor / 1e6,
    }

c = rep_block_cost()
print('RepVGG 块（C=256, 40x40 特征图, fp16）:')
print('%-26s %14s %14s' % ('', '训练期(三分支)', '推理期(单 3x3)'))
print('%-26s %14d %14d' % ('kernel 启动次数', c['train_kernels'], c['infer_kernels']))
print('%-26s %14d %14d' % ('中间张量份数', c['train_tensors'], c['infer_tensors']))
print('%-26s %13.3fG %13.3fG' % ('MACs', c['train_macs'] / 1e9, c['infer_macs'] / 1e9))
print('%-26s %13.2fMB %13.2fMB'
      % ('额外访存(中间张量)', c['train_tensors'] * c['tensor_MB'], 0.0))

assert c['infer_kernels'] == 1 and c['train_kernels'] == 8
assert c['infer_macs'] < c['train_macs']
ratio = c['infer_macs'] / c['train_macs']
assert 0.85 < ratio < 0.95, ratio
print('\\n>>> MACs 只降了 %.0f%%，但 kernel 从 8 个变成 1 个、中间张量从 3 份变成 0 份。'
      % (100 * (1 - ratio)))
print('⚠️  **真正的收益不是 FLOPs 而是访存与 kernel 启动** —— 小模型上这才是瓶颈。')
print('⚠️  另一面：合并后的等效核数值分布更长尾（几条分支的极值叠加），')
print('    **INT8 per-tensor 量化会掉得比原生单分支更多** -> 用 per-channel 或 QAT（C60 模块 03）。')"""),
    md("""## 5 · 解耦头 vs 耦合头：一笔必须会算的账

YOLOX 三件套里唯一有推理成本的一项。**代价的主项是两条支路各 2 个 3×3，
即 `4·c_mid²·9` 每像素** —— 所以 c_mid 是唯一的杠杆。"""),
    code("""def head_cost(c_in, c_mid, n_cls, hw_list, decoupled=True, n_anchor=1):
    '''返回 (params, macs)。多层 FPN **共享同一套头的权重**（RTMDet 式）：
       params 只算一次；macs 按各层空间尺寸求和。params 含 bias，macs 不含。
       耦合头 : 一个 1x1 conv  c_in -> n_anchor*(5+n_cls)
       解耦头 : 1x1 降维 c_in->c_mid；cls/reg 两条支路各 2 个 3x3；三个 1x1 输出头'''
    hw = sum(hw_list)
    if not decoupled:
        out = n_anchor * (5 + n_cls)
        return c_in * out + out, c_in * out * hw
    p, m = c_in * c_mid + c_mid, c_in * c_mid                 # stem 1x1
    for _ in range(4):                                        # 2 支路 x 2 个 3x3
        p += c_mid * c_mid * 9 + c_mid
        m += c_mid * c_mid * 9
    for co in (n_cls, 4, 1):                                  # cls / reg / obj
        p += c_mid * co + co
        m += c_mid * co
    return p, m * hw

LEVELS = [80 * 80, 40 * 40, 20 * 20]        # 640 输入的三层 FPN
CFGS = [('耦合头 (1x1, 3 anchor x 85)', dict(c_mid=256, decoupled=False, n_anchor=3)),
        ('解耦头 c_mid=256 (YOLOX 式)', dict(c_mid=256, decoupled=True)),
        ('解耦头 c_mid=64  (轻量化)',   dict(c_mid=64,  decoupled=True))]

base = None
print('%-30s %14s %14s %10s' % ('检测头', '参数量', 'MACs(三层)', '相对耦合头'))
out = {}
for name, kw in CFGS:
    p, m = head_cost(256, kw['c_mid'], 80, LEVELS,
                     decoupled=kw['decoupled'], n_anchor=kw.get('n_anchor', 1))
    out[name] = (p, m)
    if base is None:
        base = m
    print('%-30s %14s %13.2fG %9.1fx' % (name, '{:,}'.format(p), m / 1e9, m / base))

p_c, m_c = out['耦合头 (1x1, 3 anchor x 85)']
p_d, m_d = out['解耦头 c_mid=256 (YOLOX 式)']
p_l, m_l = out['解耦头 c_mid=64  (轻量化)']
assert (p_c, m_c) == (65535, 548352000), (p_c, m_c)
assert (p_d, m_d) == (2447957, 20551372800), (p_d, m_d)
assert m_d / m_c > 30, '解耦头(c_mid=256) 的 MACs 是耦合头的 30 倍以上'
assert m_l * 10 < m_d, 'c_mid 降到 1/4，代价降到约 1/14（3x3 项按 c_mid^2 走）'

print('\\n>>> 解耦头(c_mid=256) 是耦合头的 %.1fx；把 c_mid 压到 64 只剩 %.1fx。'
      % (m_d / m_c, m_l / m_c))
print('>>> c_mid 降 4 倍 -> 代价降 %.1f 倍（主项 4*c_mid^2*9 按平方走）。' % (m_d / m_l))
print('\\n✅ 所以后续工作不是不用解耦头，而是**把 c_mid 压到很小**：')
print('   YOLOv8 用 max(c_in/4, 16, reg_max*4)；RTMDet 用跨层共享权重摊薄参数量。')
print('⚠️  注意本函数按**共享权重**计。YOLOX 是每层独立头，params 要再乘层数。')"""),
    md("""## 6 · 一对多 vs 一对一：YOLOv10 的一致双分配

复现两件事：
1. **不去重会怎样** —— 一对多分支必须靠 NMS 压回去，而 NMS 阈值极其敏感
2. **为什么必须"一致"** —— 两个头用不同度量时，o2o 的 top-1 常常不在 o2m 的 top-k 里

TaskAligned 度量：$t = s^{\\alpha}\\cdot u^{\\beta}$，$(\\alpha,\\beta)=(0.5, 6)$。"""),
    code("""STRIDE, GRID = 8, 80                                  # 640 输入的 P3 层
gy, gx = np.mgrid[0:GRID, 0:GRID]
anchors = np.stack([(gx + 0.5) * STRIDE, (gy + 0.5) * STRIDE], -1).reshape(-1, 2).astype(float)

GPOS = [(80, 80), (220, 90), (360, 100), (500, 110), (120, 240), (280, 250),
        (440, 260), (560, 270), (100, 400), (260, 410), (420, 420), (560, 430)]
GSZ = [26, 20, 34, 18, 30, 22, 28, 24, 32, 20, 26, 36]
GTS = np.array([[p[0], p[1], s, s] for p, s in zip(GPOS, GSZ)], float)   # 12 个交通标志

def simulate_head(anchors, gts, seed=0, mis=0.35):
    '''模拟一个训练好的 dense head 的输出场：
       u = 定位质量（该 anchor 解码出的框与 GT 的 IoU）
       s = 分类分数（峰值**刻意偏离** GT 中心 —— cls-loc misalignment 是真实现象）'''
    r = np.random.default_rng(seed)
    s, u = np.full(len(anchors), 0.02), np.zeros(len(anchors))
    for (cx, cy, w, h) in gts:
        dx, dy = np.abs(anchors[:, 0] - cx), np.abs(anchors[:, 1] - cy)
        inter = np.clip(w - dx, 0, None) * np.clip(h - dy, 0, None)
        u = np.maximum(u, inter / (2 * w * h - inter))
        off = r.normal(0, mis * w, 2)
        d = np.hypot(anchors[:, 0] - (cx + off[0]), anchors[:, 1] - (cy + off[1]))
        s = np.maximum(s, 0.95 * np.exp(-(d ** 2) / (2 * (0.5 * w) ** 2)))
    return s, u

def per_gt_topk(metric, anchors, gts, k):
    '''中心先验：候选集限制在 GT 附近，再按 metric 取 top-k。'''
    picks = []
    for (cx, cy, w, h) in gts:
        inside = (np.abs(anchors[:, 0] - cx) <= w) & (np.abs(anchors[:, 1] - cy) <= h)
        idx = np.flatnonzero(inside)
        picks.append(idx[np.argsort(-metric[idx])][:k])
    return picks

ALPHA, BETA = 0.5, 6.0
s, u = simulate_head(anchors, GTS, seed=0)
t_align = (s ** ALPHA) * (u ** BETA)          # TaskAligned / v10 的一致度量
t_clsonly = s                                  # 「不一致」的对照：只看分类分数

o2m = per_gt_topk(t_align, anchors, GTS, k=10)      # 一对多：每 GT 10 个正样本
o2o = per_gt_topk(t_align, anchors, GTS, k=1)       # 一对一：每 GT 1 个
print('12 个交通标志，%d 个候选格点' % len(anchors))
print('   一对多分配的正样本总数: %d' % sum(len(p) for p in o2m))
print('   一对一分配的正样本总数: %d' % sum(len(p) for p in o2o))
assert sum(len(p) for p in o2m) == 120 and sum(len(p) for p in o2o) == 12
print('\\nBETA=6 让 IoU 的权重远大于分类分数: 0.88^6=%.3f 而 0.70^6=%.3f（差 %.1f 倍）'
      % (0.88 ** 6, 0.70 ** 6, 0.88 ** 6 / 0.70 ** 6))"""),
    code("""def to_xyxy(b):
    return np.stack([b[..., 0] - b[..., 2] / 2, b[..., 1] - b[..., 3] / 2,
                     b[..., 0] + b[..., 2] / 2, b[..., 1] + b[..., 3] / 2], -1)

def iou_one_vs_many(a, B):
    a, B = to_xyxy(a), to_xyxy(B)
    x1, y1 = np.maximum(a[0], B[:, 0]), np.maximum(a[1], B[:, 1])
    x2, y2 = np.minimum(a[2], B[:, 2]), np.minimum(a[3], B[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    ar = (a[2] - a[0]) * (a[3] - a[1])
    br = (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1])
    return inter / (ar + br - inter)

def nms(boxes, thr=0.6):
    order, keep = np.argsort(-boxes[:, 4]), []
    while len(order):
        i = order[0]; keep.append(int(i))
        if len(order) == 1:
            break
        rest = order[1:]
        order = rest[iou_one_vs_many(boxes[i], boxes[rest]) < thr]
    return np.array(keep)

def emit(picks, gts, seed=1, jitter=1.2):
    '''把正样本 anchor 解码成预测框（带一点回归误差）。'''
    r = np.random.default_rng(seed)
    out = []
    for p, (cx, cy, w, h) in zip(picks, gts):
        for _ in p:
            j = r.normal(0, jitter, 4)
            out.append([cx + j[0], cy + j[1], w + j[2], h + j[3], 0.90 - 0.001 * len(out)])
    return np.array(out)

raw_m, raw_o = emit(o2m, GTS), emit(o2o, GTS)
print('%-14s %10s %s' % ('NMS IoU 阈值', '一对多(120框)', '一对一(12框)'))
for thr in (0.30, 0.40, 0.45, 0.50, 0.60, 0.70):
    nm, no = len(nms(raw_m, thr)), len(nms(raw_o, thr))
    tag = '' if nm == 12 else '   <-- 漏删 %d 个重复' % (nm - 12)
    print('%-14.2f %10d %10d%s' % (thr, nm, no, tag))

assert len(raw_m) == 120 and len(raw_o) == 12
assert len(nms(raw_m, 0.45)) == 12
assert len(nms(raw_m, 0.60)) > 12, '常用默认阈值 0.6 就已经漏删重复框了'
assert all(len(nms(raw_o, t)) == 12 for t in (0.3, 0.45, 0.6, 0.7)), '一对一对阈值完全不敏感'

print('\\n>>> 一对多必须靠 NMS 压回去，而 **NMS 阈值极其敏感**：0.45 刚好、0.6 漏删 3 个、0.7 漏删 6 个。')
print('>>> 一对一在任何阈值下都是 12 —— 因为它根本不需要 NMS。')
print('\\n⚠️  阈值调低的另一面更危险：会把**真正相邻的两个目标合并成一个**。')
print('    而 TSR 恰好充满相邻目标 —— 门架上并排的限速牌、主辅牌组合、限速+解除牌。')
print('✅ 无 NMS 的第二个收益常被低估：**去掉了一个必须逐场景调、调不好两头出错的超参**。')"""),
    code("""# 「一致」到底有多重要：两个头用不同度量时会怎样
rates_align, rates_cls, same_top1 = [], [], []
for seed in range(20):                                   # 20 组随机的 cls-loc 失配
    s_, u_ = simulate_head(anchors, GTS, seed=seed)
    ta, tc = (s_ ** ALPHA) * (u_ ** BETA), s_
    m10 = per_gt_topk(ta, anchors, GTS, 10)              # o2m 分支（始终用对齐度量）
    a1 = per_gt_topk(ta, anchors, GTS, 1)                # o2o 用**同一个**度量
    c1 = per_gt_topk(tc, anchors, GTS, 1)                # o2o 用**纯分类分数**
    rates_align.append(np.mean([p[0] in set(q) for p, q in zip(a1, m10)]))
    rates_cls.append(np.mean([p[0] in set(q) for p, q in zip(c1, m10)]))
    same_top1.append(np.mean([p[0] == q[0] for p, q in zip(c1, m10)]))

ra, rc, st = float(np.mean(rates_align)), float(np.mean(rates_cls)), float(np.mean(same_top1))
print('12 个标志 x 20 组随机种子:')
print('%-42s %8s' % ('两个头的度量', 'o2o 的 top-1 落在 o2m top-10 内'))
print('%-42s %7.1f%%' % ('**一致**（都用 t = s^0.5 * u^6）', 100 * ra))
print('%-42s %7.1f%%' % ('不一致（o2o 改用纯分类分数）', 100 * rc))
print('\\n更严格的指标 —— 两个头的 top-1 **完全相同**的比例: %.1f%%' % (100 * st))

assert ra == 1.0, '同一度量的 top-1 必然在自己的 top-10 里'
assert rc < 0.85, rc
assert st < 0.40, st
print('\\n>>> 不一致时，o2o 选中的位置有 %.1f%% 根本不在 o2m 的 top-10 里 ——' % (100 * (1 - rc)))
print('    同一个位置被一个头当正样本、被另一个头当负样本，梯度互相抵消。')
print('>>> 而两个头 top-1 完全相同的比例只有 %.1f%%（分类分数最高的位置定位往往不准）。' % (100 * st))
print('\\n✅ 这就是 YOLOv10 「**一致**双分配」里那个「一致」的含义：')
print('   不是「两个头都要有」，而是「两个头必须用同一个匹配度量」。')
print('✅ 和 DETR 一对一匹配的三个区别：① DETR 是全局二分图匹配(匈牙利)，v10 是逐 GT 取 top-1；')
print('   ② v10 有 o2m 头额外提供密集监督，DETR 没有（这是它 500 epoch 的根因之一，C54）；')
print('   ③ v10 的 o2o 头仍是**密集预测**，保留了 CNN 对小目标的全部优势。')"""),
    md("""## ✏️ 练习 1：重参数化的两块积木

实现 `pad_1x1_to_3x3(W1)` 与 `identity_to_3x3(C)`：

- `pad_1x1_to_3x3`：把 `(Cout,Cin,1,1)` 的核零填充成 `(Cout,Cin,3,3)`，**1×1 的值放在中心**
- `identity_to_3x3`：返回 `(C,C,3,3)`，它作为 `pad=1` 的卷积核时等价于恒等映射"""),
    code("""def pad_1x1_to_3x3(W1):
    # TODO: (Cout,Cin,1,1) -> (Cout,Cin,3,3)，把 1x1 的值放到 3x3 的**中心**
    raise NotImplementedError

def identity_to_3x3(C):
    # TODO: (C,C,3,3)，中心位置 [c,c,1,1] = 1，其余全 0
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
Wp = pad_1x1_to_3x3(W1)
assert Wp.shape == (C, C, 3, 3), Wp.shape
assert np.allclose(Wp[:, :, 1, 1], W1[:, :, 0, 0]), '1x1 的值必须落在**中心**'
assert Wp[:, :, 0, 0].sum() == 0 and Wp[:, :, 2, 2].sum() == 0, '其余 8 个位置必须是 0'
# 零填充后用 pad=1 卷积，必须等价于原 1x1 用 pad=0 卷积（含边界）
assert np.allclose(conv2d(x, Wp, pad=1), conv2d(x, W1, pad=0), atol=1e-12)

K = identity_to_3x3(C)
assert K.shape == (C, C, 3, 3) and abs(K.sum() - C) < 1e-12, '只有 C 个 1'
assert K[0, 0, 1, 1] == 1.0 and K[0, 1, 1, 1] == 0.0 and K[0, 0, 0, 1] == 0.0
assert np.allclose(conv2d(x, K, pad=1), x, atol=1e-12), '它必须真的是恒等映射'

print('pad_1x1_to_3x3(W1)[0,0] =')
print(np.round(Wp[0, 0], 3))
print('\\nidentity_to_3x3(3)[0,0] =')
print(identity_to_3x3(3)[0, 0])
print('\\n✅ 练习 1 通过。零填充为什么成立：填进去的 0 乘任何值都是 0，')
print('   **包括图像 padding 区的 0** —— 所以边界也严格等价。')"""),
    md("""## ✏️ 练习 2：把整个 RepVGG 块合并成一个 3×3

实现 `merge_rep_branches(W3, bn3, W1, bn1, bn_id, C)`，返回合并后的 `(W, b)`。

- `bn*` 是四元组 `(gamma, beta, mean, var)`；可直接用上面给好的 `fuse_conv_bn`
- **`bn_id` 可以是 `None`** —— 当 stride≠1 或输入输出通道数不同时，identity 分支不存在，
  这时只合并 3×3 与 1×1 两条分支。**这个边界条件是真实实现里必须处理的。**"""),
    code("""def merge_rep_branches(W3, bn3, W1, bn1, bn_id, C, eps=1e-5):
    # TODO: ① 三条分支各自 fuse_conv_bn（卷积分支的 bias 传 np.zeros(C)）
    #       ② 1x1 核 pad 到 3x3；identity 用 identity_to_3x3(C) 再过 fuse_conv_bn
    #       ③ 三个 3x3 核相加、bias 相加；bn_id 为 None 时跳过第三条分支
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
bn3, bn1_, bnid = (g3, be3, mu3, v3), (g1, be1, mu1, v1), (gi, bei, mui, vi)

Wm, bm = merge_rep_branches(W3, bn3, W1, bn1_, bnid, C)
assert Wm.shape == (C, C, 3, 3) and bm.shape == (C,), (Wm.shape, bm.shape)
err3 = float(np.abs(conv2d(x, Wm, bm, pad=1) - y_multi).max())
assert err3 < 1e-10, err3

# 无 identity 分支（stride!=1 或通道数变化时的真实情况）
Wm2, bm2 = merge_rep_branches(W3, bn3, W1, bn1_, None, C)
err2 = float(np.abs(conv2d(x, Wm2, bm2, pad=1) - (y3 + y1)).max())
assert err2 < 1e-10, err2

print('三分支合并  最大绝对误差 %.3e' % err3)
print('两分支合并  最大绝对误差 %.3e   （无 identity 分支）' % err2)
print('\\n合并后等效核的数值分布 vs 单条 3x3 分支：')
for nm, W_ in [('单条 3x3 分支', W3), ('合并后的等效核', Wm)]:
    a = np.abs(W_)
    print('   %-16s  max/p90 = %6.2f   （越大越难 per-tensor 量化）'
          % (nm, a.max() / np.percentile(a, 90)))
print('\\n✅ 练习 2 通过：**数学上严格等价**。')
print('⚠️  但注意最后两行 —— 合并后的核往往更长尾，这就是 INT8 掉点的来源（C60 模块 03）。')
print('⚠️  另外两个前提：① identity 要求 Cin==Cout 且 stride=1；')
print('   ② 合并必须在 BN 用 **running statistics**（eval 模式）之后做，否则权重是错的且不报错。')"""),
    md("""## ✏️ 练习 3：anchor 拟合体检报告

实现 `anchor_fit_report(wh, anchors, thr=0.25)`，返回 dict：

| 字段 | 含义 |
|---|---|
| `mean_best_iou` | 每个框与最佳 anchor 的 IoU 的均值 |
| `bpr` | best possible recall：最佳 IoU ≥ `thr` 的比例 |
| `at_smallest` | 最佳 anchor 恰好是**面积最小**那个的比例 → **anchor 下界不够**的信号 |
| `at_largest` | 最佳 anchor 是**面积最大**那个的比例 → anchor 上界不够 |

**即使你用的是 anchor-free 检测器，这份体检也值得做**——它告诉你数据的尺度跨度
与现有 stride 够不够细。"""),
    code("""def anchor_fit_report(wh, anchors, thr=0.25):
    # TODO: 用 wh_iou 得到 (n,k) 矩阵，再算上表四个字段
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
r9 = anchor_fit_report(wh, a9)
rc = anchor_fit_report(wh, COCO_ANCHORS)

assert abs(r9['mean_best_iou'] - mean_best_iou(wh, a9)) < 1e-12
assert r9['bpr'] == 1.0 and rc['bpr'] < 0.97, (r9['bpr'], rc['bpr'])
assert r9['mean_best_iou'] > rc['mean_best_iou'] + 0.2
assert rc['at_smallest'] > 0.5 > r9['at_smallest'], (rc['at_smallest'], r9['at_smallest'])
assert rc['at_largest'] < 0.01, 'TSR 里没有大目标，最大的 [373,326] 基本没人用'
assert abs(sum(anchor_fit_report(wh, a9[:1])[k] for k in ('at_smallest', 'at_largest')) - 2.0) < 1e-9, \\
    '只有一个 anchor 时它既是最小也是最大'

print('%-22s %14s %10s %14s %13s' % ('anchor 来源', 'mean_best_iou', 'BPR', '挤在最小', '挤在最大'))
for nm, a in [('COCO 默认', COCO_ANCHORS), ('TSR 重新聚类 k=9', a9),
              ('TSR 重新聚类 k=3', kmeans_anchors(wh, 3))]:
    r = anchor_fit_report(wh, a)
    print('%-22s %14.4f %10.4f %13.1f%% %12.1f%%'
          % (nm, r['mean_best_iou'], r['bpr'], 100 * r['at_smallest'], 100 * r['at_largest']))

print('\\n✅ 练习 3 通过。**怎么读这份报告**：')
print('   BPR < 0.98        -> 有样本永远匹配不上，必须重新聚类（v5 的 autoanchor 就用这条）')
print('   at_smallest 很高  -> anchor 尺寸下界不够 -> 加更小的 anchor 或加 P2 层')
print('   at_largest 很高   -> 上界不够 -> 加更大的 anchor 或加更粗的 stride')
print('   mean_best_iou 低  -> anchor 数量不够，或数据尺度跨度太大（考虑分层建模）')"""),
    md("""## ✏️ 练习 4：检测头的参数量 / FLOPs 账

实现 `head_cost(c_in, c_mid, n_cls, hw_list, decoupled=True, n_anchor=1)`，
返回 `(params, macs)`。约定见第 5 节的 docstring：多层 FPN **共享同一套头的权重**，
`params` 只算一次且含 bias，`macs` 不含 bias 并按各层空间尺寸求和。

**这是面试里可能被要求当场算的一道题**——考的不是记忆，是你会不会拆一个结构的成本。"""),
    code("""def head_cost(c_in, c_mid, n_cls, hw_list, decoupled=True, n_anchor=1):
    # TODO: 耦合头 = 一个 1x1: c_in -> n_anchor*(5+n_cls)
    #       解耦头 = 1x1 降维 c_in->c_mid  +  4 个 3x3 (c_mid->c_mid)  +  三个 1x1 (n_cls/4/1)
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
assert head_cost(256, 256, 80, LEVELS, decoupled=False, n_anchor=3) == (65535, 548352000)
assert head_cost(256, 256, 80, LEVELS, decoupled=True) == (2447957, 20551372800)
assert head_cost(256, 64, 80, LEVELS, decoupled=True) == (169685, 1421952000)
# 单层时 macs 应按空间尺寸线性缩放，params 不变
p1, m1 = head_cost(256, 64, 80, [6400], decoupled=True)
p3, m3 = head_cost(256, 64, 80, LEVELS, decoupled=True)
assert p1 == p3 and abs(m3 / m1 - sum(LEVELS) / 6400) < 1e-9
# c_mid 减半，3x3 主项降 4 倍
assert head_cost(256, 128, 80, LEVELS)[1] < head_cost(256, 256, 80, LEVELS)[1] / 3

print('%-10s %14s %14s %12s' % ('c_mid', '参数量', 'MACs(三层)', '相对耦合头'))
base = head_cost(256, 256, 80, LEVELS, decoupled=False, n_anchor=3)[1]
for cm in (256, 128, 64, 32, 16):
    p, m = head_cost(256, cm, 80, LEVELS, decoupled=True)
    print('%-10d %14s %13.2fG %11.1fx' % (cm, '{:,}'.format(p), m / 1e9, m / base))
print('\\n✅ 练习 4 通过。**代价的主项是 4·c_mid²·9 每像素** —— c_mid 是唯一的杠杆。')
print('   在模块 00 的 2.45 ms 预算下，c_mid=256 的解耦头一项就吃掉了整个网络的算力预算。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def pad_1x1_to_3x3(W1):
    return np.pad(W1, ((0, 0), (0, 0), (1, 1), (1, 1)))

def identity_to_3x3(C):
    K = np.zeros((C, C, 3, 3))
    for c in range(C):
        K[c, c, 1, 1] = 1.0
    return K"""),
    code("""# 练习 2 参考答案
def merge_rep_branches(W3, bn3, W1, bn1, bn_id, C, eps=1e-5):
    zero = np.zeros(C)
    Wa, ba = fuse_conv_bn(W3, zero, *bn3, eps=eps)                       # 3x3 分支
    Wb, bb = fuse_conv_bn(W1, zero, *bn1, eps=eps)                       # 1x1 分支
    W, b = Wa + pad_1x1_to_3x3(Wb), ba + bb
    if bn_id is not None:                                                # identity 分支（可选）
        Wc, bc = fuse_conv_bn(identity_to_3x3(C), zero, *bn_id, eps=eps)
        W, b = W + Wc, b + bc
    return W, b"""),
    code("""# 练习 3 参考答案
def anchor_fit_report(wh, anchors, thr=0.25):
    m = wh_iou(wh, anchors)
    best, best_iou = m.argmax(1), m.max(1)
    area = anchors[:, 0] * anchors[:, 1]
    return {'mean_best_iou': float(best_iou.mean()),
            'bpr': float((best_iou >= thr).mean()),
            'at_smallest': float((best == int(np.argmin(area))).mean()),
            'at_largest': float((best == int(np.argmax(area))).mean())}"""),
    code("""# 练习 4 参考答案
def head_cost(c_in, c_mid, n_cls, hw_list, decoupled=True, n_anchor=1):
    hw = sum(hw_list)
    if not decoupled:
        out = n_anchor * (5 + n_cls)
        return c_in * out + out, c_in * out * hw
    p, m = c_in * c_mid + c_mid, c_in * c_mid              # 1x1 降维 stem
    for _ in range(4):                                     # cls/reg 两条支路各 2 个 3x3
        p += c_mid * c_mid * 9 + c_mid
        m += c_mid * c_mid * 9
    for co in (n_cls, 4, 1):                               # cls / reg / obj 三个 1x1
        p += c_mid * co + co
        m += c_mid * co
    return p, m * hw"""),
    md("""---
## 🧪 真实工程胶囊：一份可直接抄走的「重参数化 + anchor + 无 NMS」清单

这三件事在真实项目里各有一个必须做的验证步骤，缺了就会变成上线后才发现的问题。"""),
    code("""RECIPE = r'''
# ============ ① 结构重参数化：融合 + **必须做的数值对拍** ============
model.eval()                                   # 关键：BN 必须用 running statistics
with torch.no_grad():
    x = torch.randn(2, 3, 640, 640)
    y_before = model(x)                        # 融合前（训练结构）
    model.fuse()                               # ultralytics: Conv+BN 融合 & RepBlock 合并
    y_after = model(x)                         # 融合后（部署结构）
torch.testing.assert_close(y_before, y_after, rtol=1e-4, atol=1e-5)
# ^ 这一行是不可省的。融合写错**不会报错**，只会表现为「导出后精度莫名下降」。
# 融合后再验一次 INT8：rep 块合并后权重分布更长尾，per-tensor 量化掉点会更明显
#   -> 优先 per-channel；掉点 >1-2 mAP 时对 rep 块做 QAT（C60 模块 03）

# ============ ② anchor：用**自己的数据**重新聚类，并读体检报告 ============
# ultralytics 训练时会自动跑 autoanchor；BPR < 0.98 时才重聚类。手动做法：
#   from ultralytics.utils.autoanchor import check_anchors, kmean_anchors
#   anchors = kmean_anchors(dataset, n=9, img_size=1280, thr=4.0, gen=1000)
# 必看三个数：BPR、mean_best_iou、挤在最小 anchor 的比例
#   BPR < 0.98        -> 有样本永远匹配不上
#   at_smallest 很高  -> anchor 下界不够 -> 加更小 anchor 或加 P2 层（TSR 的典型症状）
# anchor-free 检测器也要跑这个体检 —— 它体检的是**数据**，不是 anchor

# ============ ③ 无 NMS（YOLOv10）：导出时别把 NMS 又加回去 ============
#   yolo export model=yolov10s.pt format=engine half=True
# 检查点：ONNX 图里不应出现 NMS/TopK/NonMaxSuppression 节点；
#         输出应当是固定 shape (batch, 300, 6) 而不是动态的 nnz
# 无 NMS 买到的是**延迟的确定性**，不必然是延迟的均值 -> 用模块 00 的协议测 p99 再决定

# ============ ④ 改动归因：任何一项都要单独测 ============
# 单变量 / 同 epoch / 同增强 / 同分辨率 / 同调参预算 / 多种子
# 检测任务同配置不同种子的 mAP 波动典型 ±0.2-0.5 -> **+0.3 很可能是噪声**（C61 模块 01）
'''
print(RECIPE)
for key in ['model.eval()', 'assert_close', 'fuse()', 'BPR < 0.98',
            'at_smallest', 'p99', '单变量', '种子']:
    assert key in RECIPE, key
print('✅ 覆盖：融合对拍 / 量化风险 / anchor 体检 / 无 NMS 导出检查 / 归因纪律')"""),
    md("""### 小结

- **YOLOv1 的失败是表达能力问题不是容量问题**：每格 B=2 + 一份类别向量，
  9 个标志结构上只能表达 6 个。加参数一条都解决不了 —— 必须改输出结构。
- **anchor 聚类的距离必须是 1−IoU**（欧氏距离被大框主导）。更重要的是
  **它是数据的体检报告**：COCO 默认 anchor 用在 TSR 上，4.1% 的标志永远匹配不上、
  60% 挤在最小的 anchor 上。**anchor-free 检测器也该跑这个体检。**
- **结构重参数化是严格数值等价的**（误差 2.7e-15），收益主要不是 FLOPs（只降 10%）
  而是 **kernel 从 8 个变 1 个、中间张量从 3 份变 0 份**。
  代价在别处：**合并后的核更长尾，INT8 会掉得更多。**
- **解耦头是 YOLOX 三件套里唯一收费的一项**：c_mid=256 时是耦合头的 37.5×。
  主项 `4·c_mid²·9` 按平方走，所以后续工作全都在压 c_mid。
  **采纳顺序：SimOTA（免费）→ anchor-free（省钱）→ 解耦头（最后，且压 c_mid）。**
- **YOLOv10 「一致」双分配的「一致」是指两个头用同一个匹配度量**。
  换成纯分类分数时，o2o 的 top-1 有 26% 落不进 o2m 的 top-10，两头 top-1 相同的只有 22%。
  无 NMS 买到的是**延迟的确定性**与**少调一个敏感超参**，不必然是延迟均值。
- **贯穿全模块的心法：凡是只在训练期付出代价的改动都是免费的午餐。**
  这条演进线上的大部分收益（分配、增强、辅助头、重参数化）都落在训练期 ——
  **所以被问「这几个点是从哪来的」，答案几乎总是「训练侧」，而不是「架构侧」。**

下一站：**模块 02 · 标签分配** —— 把本模块反复提到的那条主线完整走一遍。"""),
]
