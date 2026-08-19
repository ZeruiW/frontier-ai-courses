# -*- coding: utf-8 -*-
"""C54 模块 01 · 二分图匹配与匈牙利算法。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00；C18（IoU / NMS）；线性代数与基础组合优化。不需要图论背景"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_hungarian_matching.ipynb'),
    ("核心参考", "Kuhn 1955（匈牙利算法原始论文）；DETR §3；DN-DETR §3.1（匹配不稳定性）"),
    ("预计时长", "读 75 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("why", "为什么必须先匹配：两个无序集合之间没有天然的对应关系", "".join([
        P("检测的输出是一个<strong>集合</strong>：{（限速60, 框A）,（禁止超车, 框B）}。GT 也是一个集合。两个集合<em>都没有顺序</em>——你把 GT 列表里的两个元素交换位置，标注的含义一点都没变。"),
        P("但损失函数是逐元素算的。<code>loss(pred[0], gt[0]) + loss(pred[1], gt[1])</code> 这种写法<strong>隐含地假设了「第 0 个预测负责第 0 个 GT」</strong>——而这个假设毫无根据。同一份标注，把 GT 的存储顺序换一下，损失值就变了，梯度方向就变了，训练结果就变了。<em>一个依赖数据存储顺序的损失函数在数学上是没有定义的。</em>"),
        DUAL(
            "传统检测器是怎么绕开这个问题的？<strong>它们用「空间位置」当成了天然的对应关系</strong>：Faster R-CNN 说「和这个 anchor 的 IoU 最大的那个 GT 归你负责」，FCOS 说「落在这个 GT 框内部的所有位置都归它负责」，YOLO 说「GT 中心点所在的那个格子负责它」。<em>这些规则把「谁对应谁」这个问题用手工先验回答掉了</em>——代价是这些规则本身变成了一堆要调的超参（IoU 阈值、中心采样半径、层级分配公式），也就是 C53 模块 02 讲的<span class=\"term\">label assignment</span>（标签分配）。",
            "集合预测拿掉了 anchor，也就同时拿掉了这个天然对应关系。<strong>N 个 object query 在几何上没有任何先验位置</strong>（原版 DETR 的 query 就是 N 个可学习向量，编号本身没有含义），所以「第 3 个 query 该对哪个 GT 负责」必须<em>在每次前向之后现算</em>。这就是匹配（matching）：<strong>给定这一次前向的预测结果，找出一个使总代价最小的一一对应</strong>。它每个 iteration 都会重算一次，而且结果可能和上一个 iteration 不同——这个「可能不同」正是本模块第 8 节的主题。",
        ),
        CALLOUT("intuition", "换个角度看，<strong>匹配就是「动态的标签分配」</strong>：传统检测器用固定规则做分配（静态），DETR 用一个最优化问题做分配（动态，依赖当前预测）。<em>面试里如果被问「DETR 的标签分配是什么」，标准答案就是「基于匈牙利算法的一对一动态分配」</em>——而不是「DETR 没有标签分配」。这两者的差别决定了后面所有的性质：一对一带来无 NMS，动态带来不稳定。"),
    ])),
    ("formal", "形式化：线性指派问题（Linear Assignment Problem）", "".join([
        P("把它写成数学。设预测集合有 N 个元素 <code>ŷ_1..ŷ_N</code>（N = query 数，固定），GT 集合有 M 个元素 <code>y_1..y_M</code>（M 随图像变化，通常 M ≪ N）。定义一个<strong>代价矩阵</strong> <code>C ∈ ℝ^{N×M}</code>，其中 <code>C_ij</code> 表示「让第 i 个预测去认领第 j 个 GT」的代价。我们要找的是一个单射 σ: {1..M} → {1..N}，使总代价最小："),
        MATH("\\hat{\\sigma} \\;=\\; \\arg\\min_{\\sigma}\\; \\sum_{j=1}^{M} C\\big(\\hat{y}_{\\sigma(j)},\\, y_j\\big) \\qquad \\text{s.t.}\\quad \\sigma(j_1) \\neq \\sigma(j_2)\\ \\ \\forall\\, j_1 \\neq j_2"),
        P("这就是运筹学里的<strong>线性指派问题</strong>（linear assignment problem, LAP），也叫二分图最小权完美匹配。三个要素缺一不可："),
        TABLE(["要素", "含义", "去掉它会怎样"], [
            ["<strong>代价矩阵</strong> <code>C_ij</code>", "「预测 i 认领 GT j」有多贵。它把「像不像」量化成一个数", "无法比较不同配对的优劣，问题不成立"],
            ["<strong>一对一约束</strong>", "每个 GT 恰好一个预测，每个预测至多一个 GT（<code>σ</code> 是单射）", "<strong>退化成逐 GT 独立取 argmin</strong>——多个 GT 会抢同一个 query，重复框就回来了"],
            ["<strong>总代价最小</strong>", "优化的是<em>总和</em>，不是逐个最优", "变成贪心匹配，会得到次优解（notebook 里实测约 37% 的随机矩阵上贪心次优）"],
        ]),
        DUAL(
            "第二行是这门课的地基。<strong>「一对一」这三个字承载了 DETR 的全部特殊性</strong>：如果允许多个预测认领同一个 GT（一对多），那就是传统检测器的标签分配，输出必然重复，必须 NMS；只有强制一对一，模型才被迫学会「一个目标只输出一个框」。<em>而一对一约束恰恰是让这个问题从「N 次独立 argmin」变成「一个组合优化问题」的原因</em>——也是它需要匈牙利算法而不是一行 <code>argmin</code> 的原因。",
            "第三行则常被低估。<strong>「总代价最小」与「每个 GT 各自选最便宜的」是两回事</strong>。考虑一个 2×2 的代价矩阵 <code>[[1, 2], [2, 100]]</code>：贪心先拿走全局最小的 <code>C[0,0]=1</code>，剩下只能吃 <code>C[1,1]=100</code>，总代价 101；而最优解是交叉配对 <code>C[0,1]+C[1,0] = 2+2 = 4</code>。<em>差了 25 倍</em>。<strong>贪心的错误不是「选贵了」，而是「它的选择锁死了别人的选择」</strong>——这正是组合优化与逐点优化的分界线。",
        ),
        CALLOUT("warn", "一个实现上的坑：<strong>M 可能是 0</strong>（这一帧没有任何交通标志，在 TSR 数据里非常常见——高速空旷路段整段都是空帧）。此时代价矩阵是 <code>N×0</code>，匹配为空集，所有 N 个 query 都算 no-object 损失。<em>没有对空矩阵做保护是 DETR 复现里最常见的 crash 来源之一</em>，而且它只在遇到空帧的那个 batch 才炸，可能训练几个小时后才暴露。"),
    ])),
    ("augment", "机理之一：增广路径——先解「有没有」，再解「多好」", "".join([
        P("匈牙利算法的名字来自 König 与 Egerváry 两位匈牙利数学家的定理，Kuhn 在 1955 年把它整理成算法。理解它要分两步走：<strong>先理解无权版本（最大二分匹配），再把权重加进去</strong>。无权版本的核心概念只有一个——<span class=\"term\">augmenting path</span>（增广路径）。"),
        ASCII("""左边是 query，右边是 GT，一条边表示「这对可以配」。粗线 ═ 表示已在当前匹配里。

  当前匹配 M = { q0═g0, q1═g1 }，匹配数 2。现在轮到 q2：

     q0 ═══════ g0          q2 只连着 g1，而 g1 已被 q1 占用。
                             直接放弃？不行 —— 也许 q1 可以让位。
     q1 ═══════ g1
                ╱            走一条**交替路径**（非匹配边、匹配边交替出现）：
     q2 ───────╱
                              q2 ──→ g1     (非匹配边)
     q1 ─────── g2             g1 ══→ q1     (匹配边，反向走)
                               q1 ──→ g2     (非匹配边)
                               g2 是**未匹配**的右点 → 路径终止

  这条路径就是**增广路径**：起点是未匹配左点，终点是未匹配右点，边交替。

  增广 = 把路径上所有边的「匹配/非匹配」状态取反：
       非匹配边 3 条 → 变匹配 (+3)      匹配边 1 条 → 变非匹配 (−1)
       净增 1 条匹配边。

     增广前: q0═g0, q1═g1              (2 条)
     增广后: q0═g0, q2═g1, q1═g2       (3 条)   ← q1 让位给 q2，自己去了 g2

  Berge 定理：一个匹配是最大匹配  ⟺  图中不存在增广路径。
  所以算法就是：**对每个左点找一次增广路径，找到就增广。** 复杂度 O(V·E)。""")
        ,
        DUAL(
            "增广路径的直觉是<strong>「链式让位」</strong>：新来的 query 想要一个已被占用的 GT，那就问占用者能不能换个别的；占用者去问下一个……只要这条链最终走到一个空位，整条链就能集体挪一格，多容纳一个人。<em>如果走不到空位（所有可达的右点都已被占且它们的占用者也无处可去），说明当前匹配在这一块已经饱和，这个新 query 就只能落空。</em>",
            "这个「落空」的情形在 DETR 里有直接对应：<strong>当 M &gt; N（GT 数超过 query 数）时，必然有 GT 无法被匹配，它们的监督信号直接丢失</strong>。这就是「N 必须大于单图最大目标数」这条工程铁律的来源。<em>TSR 场景要特别小心：绝大多数帧只有 0–3 块标志，但复杂路口一次能出现十几块（龙门架 + 路侧杆 + 地面附着牌）</em>。按平均数设 N 会在最需要它的那些帧上漏检——而这些帧恰恰是安全最关键的。",
        ),
        CALLOUT("intuition", "这里有个可迁移的心法：<strong>「先解可行性，再解最优性」</strong>。无权最大匹配回答的是「最多能配几对」，带权最优匹配回答的是「在配满的前提下总代价最小是多少」。<em>KM 算法的整个设计就是把第二个问题化归成第一个问题反复求解</em>——用对偶变量筛出一个「只保留最划算的边」的子图，然后在这个子图上跑最大匹配。下一节就是这件事。"),
    ])),
    ("km", "机理之二：对偶变量与 Kuhn–Munkres，为什么是 O(n³) 而不是 O(n!)", "".join([
        P("带权版本的核心技巧是<strong>对偶</strong>。给每一行（query）配一个数 <code>u_i</code>，每一列（GT）配一个数 <code>v_j</code>，要求它们满足："),
        MATH("u_i + v_j \\;\\le\\; C_{ij} \\qquad \\forall\\, i, j"),
        P("在这个约束下，<strong>对任意一个合法的一对一匹配，其总代价都 ≥ Σu + Σv</strong>（把匹配上的每一对的不等式加起来即可）。所以 <code>Σu + Σv</code> 是最优总代价的一个<strong>下界</strong>。线性规划对偶告诉我们：把这个下界推到最大，它就等于最优值。"),
        MATH("\\max_{u,v}\\ \\Big(\\sum_i u_i + \\sum_j v_j\\Big) \\quad = \\quad \\min_{\\sigma}\\ \\sum_j C_{\\sigma(j)\\, j}"),
        P("取等的条件是<strong>互补松弛</strong>：被匹配上的那些格子必须满足 <code>u_i + v_j = C_{ij}</code>（称为<span class=\"term\">tight edge</span>，紧边）。于是算法的形态就出来了："),
        OL([
            "维护一组满足 <code>u_i + v_j ≤ C_ij</code> 的对偶变量（初始可全取 0，若代价有负数则先做行减最小值）。",
            "只看<strong>紧边</strong>组成的子图（<span class=\"term\">equality subgraph</span>，相等子图），在上面用<strong>增广路径</strong>找匹配。",
            "如果找不到增广路径，说明紧边不够用——计算一个最小的松弛量 <code>δ</code>，调整 <code>u/v</code> 让至少一条新的边变紧，然后回到第 2 步。",
            "每次调整至少让一条边变紧，每个左点最多做 O(n) 次调整，每次调整扫描 O(n) 列 → <strong>总复杂度 O(n³)</strong>。",
        ]),
        TABLE(["方法", "复杂度", "N=100, M=7 时的规模", "能不能用"], [
            ["<strong>暴力枚举全排列</strong>", "O(n!) / P(N,M)", "<strong>8.07 × 10¹³ 种指派</strong>", "❌ 只能用来做正确性对拍（n ≤ 7）"],
            ["<strong>贪心（每次取全局最小）</strong>", "O(n² log n)", "≈ 10⁴", "❌ 快但<strong>不是最优</strong>，约 37% 的随机矩阵上会次优"],
            ["<strong>匈牙利 / KM（本课手写）</strong>", "<strong>O(n³)</strong>", "≈ 10⁶ 次操作，CPU 上 &lt; 10 ms", "✅ 最优且够快"],
            ["Jonker–Volgenant（scipy 用的）", "O(n³)，常数更小", "同上，快 3–10×", "✅ 生产用它，但<strong>面试要能手写</strong>"],
        ]),
        DUAL(
            "为什么这个复杂度可以接受？<strong>因为匹配是在 CPU 上、对每张图单独做的，而且矩阵极小</strong>：N=100（或 DINO 的 900），M 通常个位数。<em>DETR 的官方实现直接调 <code>scipy.optimize.linear_sum_assignment</code>，在整个训练里占比不到 1%</em>。真正的代价不在时间，而在它是一个<strong>不可微的离散步骤</strong>——它决定了梯度流向谁，但它自己没有梯度。",
            "「不可微」这一点值得说透。<strong>匹配 <code>σ̂</code> 是一个 <code>argmin</code>，在反向传播里被当作常量</strong>（DETR 实现里外面套了 <code>torch.no_grad()</code>）。所以匹配代价 <code>C</code> 里那些项（分类概率、L1、GIoU）在<em>匹配阶段</em>只起「选择」作用，它们的梯度来自后面的<em>损失</em>阶段。<em>这也是为什么匹配代价和损失函数可以用不同的形式</em>——比如匹配用 <code>−p</code>，损失用 <code>−log p</code>（下一节详述）。<strong>面试里能主动区分「匹配代价」和「损失函数」是加分项，很多人以为它们是同一个东西。</strong>",
        ),
        CALLOUT("danger", "<p><strong>不要在面试里说「匈牙利算法是 O(n!)」或者「它就是暴力枚举的优化」</strong>。它和暴力枚举没有任何关系——它是一个基于线性规划对偶的原始-对偶算法，每一步都在<em>可证明地</em>提升下界。<em>被追问「为什么是 O(n³)」时，标准答案骨架是：n 个左点，每个点最多 n 次对偶调整，每次调整扫描 n 列</em>。如果还能补一句「它的对偶变量 u/v 满足互补松弛，所以算法终止时自带一个最优性证书」，这题就满分了。</p>", "O(n³) 的来源要能说清"),
    ])),
    ("cost", "DETR 的匹配代价：三项设计，以及为什么分类项用概率而不是 log", "".join([
        P("代价矩阵怎么填，决定了「谁认领谁」，进而决定了每个 query 收到什么梯度。<strong>代价函数的设计比匹配算法本身更影响最终精度</strong>。DETR 用的是三项之和："),
        MATH("C_{ij} \\;=\\; -\\,\\lambda_{cls}\\,\\hat p_i(c_j) \\;+\\; \\lambda_{L1}\\,\\lVert \\hat b_i - b_j \\rVert_1 \\;-\\; \\lambda_{giou}\\,\\mathrm{GIoU}(\\hat b_i,\\, b_j)"),
        TABLE(["项", "形式", "默认权重", "它负责什么", "单独用会怎样"], [
            ["<strong>分类项</strong>", "<code>−p̂_i(c_j)</code>，直接用 softmax <strong>概率</strong>", "1", "让「已经觉得自己是这一类」的 query 优先认领", "只按分数匹配 → <strong>选到框很差的 query</strong>（C53 模块 04 讲的 query selection 同一个病）"],
            ["<strong>L1 项</strong>", "<code>‖b̂ − b‖₁</code>，归一化 cxcywh 四维之和", "5", "中心与尺寸的绝对偏差，对<em>小框</em>友好（不随尺度衰减）", "<strong>对尺度极其敏感</strong>：同样 0.01 的偏差，对小框是致命的，对大框无所谓"],
            ["<strong>GIoU 项</strong>", "<code>−GIoU(b̂, b)</code> ∈ [−1, 1]", "2", "尺度不变的重叠度量；<strong>不相交时仍有梯度</strong>（IoU 没有）", "尺度不变意味着它<em>无法区分</em>「小框差一点」和「大框差很多」"],
        ]),
        DUAL(
            "<strong>L1 与 GIoU 必须同时用，因为它们的失效模式正好互补</strong>。L1 在归一化坐标下对小目标不友好：一块 24×24 像素的限速牌在 1920 宽的图上，宽度归一化后只有 0.0125，你的框宽错一倍（0.025）L1 才 0.0125，几乎不产生代价；而对一块占半张图的指路牌，同样 0.0125 的误差可以忽略不计。<em>GIoU 反过来：它只看重叠比例，24 像素的框错 2 像素 IoU 就掉到 0.39，代价立刻拉满。</em>",
            "而 <strong>GIoU 相对 IoU 的关键改进是「不相交时仍有梯度」</strong>：两个完全不相交的框，IoU 恒为 0，无论它们相距 10 像素还是 500 像素——<em>作为代价它无法区分「差一点」和「差得离谱」</em>。GIoU 减去了「最小外接框中的空白占比」，所以框越远 GIoU 越负，一直到 −1。<strong>这一点对匹配尤其重要</strong>：训练早期所有预测框都是乱的，几乎没有一个和 GT 相交，如果只用 IoU，代价矩阵会退化成一片 0，匹配就完全由分类项决定，等于随机分配。<em>模块 02 会把 GIoU/DIoU/CIoU 的梯度性质完整推一遍。</em>",
        ),
        H3("为什么分类项是 <code>−p</code> 而不是 <code>−log p</code>"),
        P("这是本节最值得记住的一个细节，也是高频面试题。DETR 论文明确写了：<strong>匹配代价里的分类项用概率而非对数概率，「这样它就与框的代价项在同一量级上，我们观察到这带来了更好的表现」</strong>。原因有两层："),
        UL([
            "<strong>有界性</strong>：<code>−p ∈ [−1, 0]</code>，和 GIoU 项的 <code>[−1, 1]</code> 量级相当；而 <code>−log p</code> 在 <code>p→0</code> 时趋于 +∞。DETR 有 91 个类，训练初期每类概率约 0.01，<code>−log p ≈ 4.6</code>，而 L1 项通常在 0.1–1 之间——<strong>分类项会以数量级优势主导整个代价矩阵，匹配几乎完全由分类分数决定，框的质量被忽略</strong>。",
            "<strong>饱和性</strong>：<code>−p</code> 在 <code>p</code> 已经很高时增益递减（0.9→0.99 只多赚 0.09），所以「非常自信」的 query 不会因为多一点自信就压倒「框更准」的 query。<code>−log p</code> 则在低概率区极度陡峭，会把一个框很好但分类还没学会的 query 直接判死刑——<em>而训练早期所有 query 的分类都还没学会</em>。",
        ]),
        P("notebook 里有一个三选一的最小反例：q0 分类很自信但框偏了 0.4，q1 框几乎完美（GIoU 0.95）但分类概率只有 0.02，q2 两头都平庸。<strong>用 <code>−p</code> 匹配选中 q1（框好的那个，正确）；换成 <code>−log p</code> 就选中了 q2</strong>——一个两头平庸的 query 拿走了这个 GT，而框最准的 q1 被判成背景。"),
        CALLOUT("warn", "但要注意<strong>损失函数里仍然用 <code>−log p</code>（交叉熵）</strong>，只有匹配代价用 <code>−p</code>。<em>把这两处搞混（匹配也用 log，或者损失也用概率）是复现 DETR 时的经典 bug</em>：前者会让训练早期匹配退化成按分数排序，后者会让分类梯度在 <code>p</code> 很小时消失。<strong>记法：匹配要「公平比较」所以要有界；损失要「强力纠错」所以要无界。</strong>"),
    ])),
    ("padding", "N 个 query、M 个 GT：矩形代价矩阵与 no-object", "".join([
        P("实际的代价矩阵几乎从不是方阵。DETR 用 N=100（DINO 用 900），而一张图里的 GT 通常只有几个。<strong>TSR 场景更极端</strong>：一段高速上大量帧的 M=0，市区普通路段 M=1–3，复杂路口偶尔 M=12。所以代价矩阵是 <code>100×M</code> 的瘦长矩形。"),
        ASCII("""            GT (M=3)                          padding 到方阵 (N=6)
        g0     g1     g2                    g0     g1     g2    ∅    ∅    ∅
   q0 [ 0.3    2.1    1.8 ]            q0 [ 0.3    2.1    1.8   c    c    c ]
   q1 [ 1.9    0.4    2.2 ]            q1 [ 1.9    0.4    2.2   c    c    c ]
   q2 [ 2.4    1.7    0.5 ]     ==>    q2 [ 2.4    1.7    0.5   c    c    c ]
   q3 [ 1.1    1.3    1.6 ]            q3 [ 1.1    1.3    1.6   c    c    c ]
   q4 [ 2.0    2.2    1.4 ]            q4 [ 2.0    2.2    1.4   c    c    c ]
   q5 [ 1.5    1.9    2.1 ]            q5 [ 1.5    1.9    2.1   c    c    c ]

   要点：padding 列的代价是**同一个常数 c**。
         每种指派方案里恰好有 (N−M)=3 行落到 padding 列，贡献 3c —— **对所有方案都一样**。
         => c 取什么值都不改变 argmin。**所以直接解矩形问题即可，不需要真的 padding。**

   落到 padding 列的那 3 个 query 的实际待遇：**在损失里被判为 no-object (∅)**。""")
        ,
        DUAL(
            "很多人第一次看 DETR 的公式会卡在「GT 集合要 pad 到大小 N」这句话上，以为要真的构造一个 N×N 矩阵。<strong>数学上 padding 是为了让 <code>σ</code> 成为一个排列（permutation），叙述更干净；工程上完全不需要</strong>——因为 padding 列的代价是常数，它对所有指派方案的贡献相同，argmin 不受影响。<em>DETR 官方实现里就是直接把 N×M 的矩形矩阵扔给 <code>linear_sum_assignment</code>。</em>",
            "但「no-object 在匹配里代价为常数」这个设计本身是有后果的，值得想清楚：<strong>它意味着「一个 query 该不该被判为背景」这件事完全不由匹配决定，只由「有没有轮到它」决定</strong>。哪怕某个 query 的框和某个 GT 极度吻合，只要有另一个 query 更吻合，它就被打成背景，承受完整的 no-object 损失。<em>这就是「训练期压制重复」的机械原理，也是匹配不稳定性伤害如此之大的原因</em>——身份翻转会让同一个 query 在相邻 epoch 收到方向完全相反的分类监督。",
        ),
        CALLOUT("intuition", "顺带回答一个常见困惑：<strong>为什么 N 不能设得太大？</strong> 三个理由。① <strong>正样本比例</strong>：N=100、M=3 时前景 query 只占 3%，no-object 损失即使降权也会主导训练（模块 02 量化这一点）；② <strong>计算量</strong>：decoder 的 self-attention 是 O(N²)，N 从 100 到 900 是 81 倍；③ <strong>重复风险</strong>：query 越多，「两个 query 都学到差不多的行为」的机会越大。<em>反过来 N 也不能太小——N &lt; 单图最大目标数会直接漏检</em>。<strong>实务经验：N 取「数据集里单图目标数的 99.9 分位数」的 3–5 倍。</strong>TSR 数据上这通常意味着 N=100 足够，但要先真的去统计那个分位数，而不是照抄 COCO 的配置。"),
    ])),
    ("nonms", "为什么一对一匹配能替代 NMS：训练期压制 vs 推理期删除", "".join([
        P("这是本模块、也是整门课最核心的一个问题，几乎每场 DETR 相关的面试都会问。答案的骨架是三句话：<strong>① 重复框的根源是「多个预测同时被判为同一目标的正样本」；② 一对一匹配从训练目标上禁止了这件事；③ 被禁止的那些 query 收到 no-object 梯度，于是学会主动把自己压低。</strong>"),
        TABLE(["", "一对多分配（传统检测器）", "一对一匹配（DETR 系）"], [
            ["训练时一个 GT 对应几个正样本", "几个到几十个（IoU 阈值 / center sampling / SimOTA 的 dynamic-k）", "<strong>恰好 1 个</strong>"],
            ["训练信号密度", "<strong>稠密</strong>——收敛快（12–36 epoch）", "稀疏——收敛慢（原版 500 epoch）"],
            ["推理时同一目标的高分预测数", "多个（因为训练时它们都被教成正样本）", "<strong>≈ 1 个</strong>"],
            ["去重发生在", "<strong>推理期</strong>：NMS 按 IoU 阈值删（不可微、O(n²)、阈值全局）", "<strong>训练期</strong>：no-object 损失把落选者压低（可微、无额外开销）"],
            ["误删真目标的风险", "存在（模块 00 算过：TSR 组合牌场景阈值窗口为空集）", "<strong>不存在</strong>（没有抑制步骤）"],
            ["延迟随目标数", "增长，p99 不可控", "<strong>常数</strong>"],
        ]),
        P("notebook 里有一个可以完整跑起来的最小实验：8 个 query、2 个 GT、纯 numpy 手写梯度下降 600 步，只改「分配方式」这一个变量。"),
        ASCII("""同一份数据、同一个模型、同一套梯度，只改分配方式：

  一对多（半径 0.15 内全算正样本）      一对一（匈牙利匹配，每 GT 只 1 个正样本）
  ────────────────────────────────      ──────────────────────────────────────
  正样本: q1 q2 q3 | q4 q5 q6            正样本: q2 | q5
  负样本: q0, q7                          负样本: q0 q1 q3 q4 q6 q7

  训练 600 步后 sigmoid(score)：          训练 600 步后 sigmoid(score)：
    q0 0.01                                q0 0.01
    q1 0.99  ┐                             q1 0.01
    q2 0.99  ├ 3 个框挤在 GT0 上           q2 0.99  ← 只有它认领 GT0
    q3 0.99  ┘                             q3 0.01
    q4 0.99  ┐                             q4 0.01
    q5 0.99  ├ 3 个框挤在 GT1 上           q5 0.99  ← 只有它认领 GT1
    q6 0.99  ┘                             q6 0.01
    q7 0.01                                q7 0.01

  触发数 = 6  →  **必须 NMS 才能回到 2**    触发数 = 2  →  **不需要任何后处理**""")
        ,
        DUAL(
            "这个实验里有一个自我强化的动力学值得注意：<strong>匹配代价里包含 <code>−p</code>，所以分数被压低的 query 代价更高、更不容易被匹配上，下一步又被压得更低</strong>。这个正反馈让「谁认领这个 GT」很快就锁定下来。<em>它既是一对一匹配能稳定收敛的原因，也是「一旦早期锁错了 query 就很难纠正」的原因</em>——后者是 DETR 训练里 query 利用率不均衡问题的一个来源（模块 05 会给诊断指标）。",
            "必须诚实地补上另一半：<strong>一对一匹配换来无 NMS，代价是监督信号密度掉了一个数量级</strong>。一对多分配下一张图有几百个正样本，一对一只有 M 个（TSR 场景常常就 1–3 个）。<em>这是 DETR 需要 500 epoch 的第一个根因</em>。所以 2022 年之后出现了一批「训练时加一对多分支、推理时丢掉」的工作（Group DETR、H-DETR、Co-DETR），都能稳定涨点 1–2 AP。<strong>它们证明了一件重要的事：一对一是「推理端的需求」，不是「训练端的最优」。</strong>面试里能说出这一层，说明你不只是背了 DETR 的结论。",
        ),
        CALLOUT("danger", "<p>面试高频陷阱题：<strong>「一对一匹配就够了吗？把 decoder 的 self-attention 去掉，还能不出重复框吗？」</strong> 正确答案是<strong>不能</strong>。<em>一对一匹配提供的是「不要重复」的<strong>动机</strong>，decoder self-attention 提供的是「知道别人已经认领了」的<strong>能力</strong></em>——query 之间必须能互相看到，才能协商谁让谁。去掉 self-attention 后，多个 query 面对同一个目标时无法区分彼此，训练会在几个近似解之间震荡，重复框显著回升。<strong>把「动机 vs 能力」这组词说出来，这题就答满分了。</strong></p>", "动机（匹配）与能力（self-attention）缺一不可"),
    ])),
    ("instability", "匹配不稳定性：DETR 收敛慢的第二个根因", "".join([
        P("现在讲这个模块最有价值、也最少被讲清楚的一件事。<strong>匹配是一个离散的 <code>argmin</code>，代价矩阵的微小扰动可以让整个指派翻转。</strong>而代价矩阵在训练中每个 iteration 都会变（模型在更新、数据在换、增强在随机）。后果是：<strong>同一个 GT 在相邻 epoch 可能被不同的 query 认领。</strong>"),
        ASCII("""同一块 40x40 的「禁止超车」牌，在相邻 epoch 被谁认领：

  epoch    120   121   122   123   124   125   126   127   128
  认领者   q17   q17   q42   q17   q42   q42   q17   q42   q17
                   └翻转┘ └翻转┘ └翻转┘     └翻转┘ └翻转┘ └翻转┘   翻转率 6/8 = 75%

  q17 这一路收到的监督信号：
  epoch    120   121   122   123   124   125   126   127   128
  身份     前景  前景  背景  前景  背景  背景  前景  背景  前景
  分类梯度  ↑     ↑     ↓     ↑     ↓     ↓     ↑     ↓     ↑
  框梯度   拉向GT 拉向GT  无   拉向GT   无    无   拉向GT   无  拉向GT

  净效果：分类梯度方向来回抵消 —— 累计 9 步只净得 (5−4)/9 ≈ 11% 的有效信号，
          而一个**稳定被认领**的 query 净得 100%。
          等价于：**有歧义的那批 query 的有效学习率只有别人的 1/9。**""")
        ,
        P("notebook 里把这件事做成了可量化的实验：构造一个 8 query × 4 GT 的代价矩阵，其中 GT0 和 GT2 各有两个「势均力敌」的候选 query（代价差 0.01 / 0.02），GT1 和 GT3 的候选则拉开明显差距（代价差 0.70）。给代价矩阵叠加高斯噪声模拟训练抖动，跑 2000 个「epoch」统计翻转率："),
        TABLE(["噪声 σ", "GT0（代价差 0.01）", "GT1（代价差 0.70）", "GT2（代价差 0.02）", "GT3（代价差 0.70）", "平均"], [
            ["0.002", "0.000", "0.000", "0.000", "0.000", "<strong>0.000</strong>"],
            ["0.01", "0.358", "0.000", "0.136", "0.000", "<strong>0.124</strong>"],
            ["0.05", "0.482", "0.000", "0.474", "0.000", "<strong>0.239</strong>"],
            ["0.20", "0.488", "0.014", "0.493", "0.013", "<strong>0.252</strong>"],
        ]),
        DUAL(
            "三个必须读出来的结论。<strong>① 不稳定性是局部的，不是全局的</strong>：代价差 0.70 的那两个 GT 在任何噪声下都几乎不翻转，而代价差 0.01 的那两个一翻就是 48%。<em>所以「匹配不稳定」真正的意思是「一小撮势均力敌的候选之间反复易主」，而不是整个指派随机乱跳</em>。② <strong>翻转率会饱和在 0.5</strong>：两个候选完全势均力敌时，每个 epoch 各 50% 概率，相邻两 epoch 不同的概率就是 0.5。σ 从 0.05 加到 0.20 平均翻转率只从 0.239 涨到 0.252，就是因为已经饱和了。",
            "③ <strong>「势均力敌」在真实训练里是常态而不是例外</strong>。想想 TSR 场景：一块 24 像素的远处限速牌周围，好几个 query 的预测框只差一两个像素，它们的 L1 项与 GIoU 项几乎相同，分类概率也在同一个量级——<em>代价差恰恰就在 0.01 这个量级上</em>。而每个 iteration 里数据增强的随机裁剪、颜色抖动、乃至 dropout，都会给代价矩阵注入远超 0.01 的扰动。<strong>小目标 + 密集目标的场景，匹配不稳定性最严重</strong>——这正好是 TSR 的画像。",
        ),
        P("这个观察直接催生了后面两代工作，模块 04 会展开："),
        TABLE(["工作", "对付不稳定性的思路", "效果"], [
            ["<strong>DN-DETR</strong>（CVPR 2022）", "把「加了噪声的 GT 框」作为额外的 query 送进 decoder，它们的标签<strong>已知且固定，完全绕过匹配</strong>，只做去噪重建", "50 epoch 达到原版 500 epoch 的精度；论文里直接画了「不稳定性指标随 epoch 下降」的曲线"],
            ["<strong>DINO</strong>（ICLR 2023）", "在 DN 基础上加<strong>对比去噪</strong>（同一个 GT 给一组小噪声正样本 + 一组大噪声负样本），教模型「多远算同一个目标」", "长期 SOTA 骨架；对重复框的抑制也更强"],
            ["<strong>Stable-DINO</strong>（ICCV 2023）", "用<strong>定位质量给分类分数加权</strong>再进匹配代价，让「框准」这件事在匹配里更有决定性，减少势均力敌", "直接针对匹配不稳定，在多个 backbone 上稳定涨点"],
            ["<strong>Group / H / Co-DETR</strong>", "训练时并行多组一对多分配，<strong>用监督密度对冲不稳定的伤害</strong>", "涨 1–2 AP，推理零开销"],
        ]),
        CALLOUT("intuition", "把这一节压成一句可迁移的话：<strong>凡是「用一个离散 argmin 决定谁接受监督」的系统，都会有优化目标抖动的问题</strong>。这不是 DETR 独有的——MoE 的专家路由、稀疏检索的 top-k 选择、乃至 SimOTA 的 dynamic-k，都是同一个病。<em>通用解法只有两类：让选择更确定（Stable-DINO 的加权、MoE 的负载均衡损失），或者绕过选择（DN-DETR 的去噪 query、MoE 的 soft routing）</em>。<strong>能把 DETR 的匹配不稳定和 MoE 的路由不稳定联系起来，是很强的信号。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("匹配这件事看起来已经被解决了（算法是 1955 年的，代价函数是 2020 年定下来的），但它仍然是 DETR 系里最活跃的改进入口之一。"),
        UL([
            "<strong>匹配稳定性的理论刻画仍然缺失</strong>。目前所有工作都是「观察到不稳定 → 提出一个启发式 → 实验证明有效」，没有人回答「给定代价矩阵的分布，翻转率的期望是多少」「翻转率降到多少才不影响收敛」。<em>本模块 notebook 里的那个 2000 次模拟，本质上就是在做这件事的最小版本</em>——把它扩展到真实代价矩阵上是一个现成的研究点。",
            "<strong>一对一与一对多的最优配比</strong>。Group DETR 用 11 组，H-DETR 用一对多分支 + 一对一分支，Co-DETR 挂三个辅助头——<em>组数、噪声强度、损失权重全是调出来的</em>。「训练时该给多稠密的监督」目前没有理论指导，也没有随训练进程自适应的方案。",
            "<strong>可微匹配 / 软匹配</strong>。用 Sinkhorn 迭代做熵正则化的最优传输（OTA、SimOTA 的思想来源）可以得到一个可微的软指派，理论上能让梯度流过匹配步骤。<em>但在 DETR 上至今没有稳定超过硬匹配的方案</em>——软指派会让多个 query 都收到部分前景梯度，重复抑制的效果被削弱，绕回了一对多的老问题。",
            "<strong>代价函数的自动设计</strong>。三项权重 (1, 5, 2) 是 DETR 论文里试出来的，此后几乎所有工作都沿用。<em>但它对数据集分布是敏感的</em>：小目标为主的数据集（TSR、航拍）理论上应该提高 GIoU 权重或改用 NWD 这类尺度不变度量（C57 模块 03）。目前没有系统的调参方法论，也没有「按数据集自动搜代价权重」的工作。",
            "<strong>匹配与时序的结合</strong>。视频/多帧场景里，同一个目标在相邻帧应当被同一个 query 认领（这样 query 就自带跟踪 ID）。TrackFormer / MOTR 这类工作把 query 沿时间传播，<em>但「跨帧匹配一致性」与「单帧最优匹配」之间的冲突还没有好的解法</em>。<strong>对 TSR 尤其有价值</strong>：交通标志是静止的、自车运动可预测，跨帧一致的 query 认领能直接给出稳定的跟踪 ID（见 C55 模块 04）。",
        ]),
        CALLOUT("paper", "必读（按重要性）：<strong>★ Carion et al., <em>End-to-End Object Detection with Transformers</em>（DETR, ECCV 2020）§3.1</strong>——匹配代价的定义，以及「分类项用概率而非 log」那句关键说明；<strong>★ Li et al., <em>DN-DETR: Accelerate DETR Training by Introducing Query DeNoising</em>（CVPR 2022）§3.1</strong>——匹配不稳定性的定义与量化指标（本节表格的直接来源）；<strong>★ Kuhn, <em>The Hungarian Method for the Assignment Problem</em>（Naval Research Logistics Quarterly, 1955）</strong>——只有 12 页，读原文能真正理解对偶变量的来历；<strong>★ Zhang et al., <em>DINO</em>（ICLR 2023）</strong>——对比去噪；Liu et al., <em>Detection Transformer with Stable Matching</em>（Stable-DINO, ICCV 2023）——直接针对匹配稳定性；Chen et al., <em>Group DETR</em> / Jia et al., <em>DETRs with Hybrid Matching</em>（H-DETR, CVPR 2023）/ Zong et al., <em>Co-DETR</em>——一对多的回归；Ge et al., <em>OTA: Optimal Transport Assignment</em>（CVPR 2021）——把标签分配看成最优传输。相邻课程：C53 模块 02（一对多标签分配的完整谱系）、C54 模块 02（集合损失）、C57 模块 03（小目标的尺度不变度量 NWD）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 二分图匹配与匈牙利算法（代价矩阵 / 增广路径 / KM 对偶 / GIoU / 匹配翻转率）

目标：**从零手写一个 O(n³) 的匈牙利算法**（禁止 `scipy.optimize.linear_sum_assignment`），
用暴力枚举全排列对拍证明它真的最优，然后用它把 DETR 的匹配流程完整跑一遍。

本 notebook 你会亲手实现：
1. **暴力枚举全排列**求最优指派（作为一切对拍的黄金标准）
2. **Kuhn 的增广路径算法**（0-1 二分图最大匹配）——带路径打印，看清「链式让位」
3. **Kuhn–Munkres / 匈牙利算法 O(n³)**（对偶变量 + 相等子图 + 松弛调整），
   与暴力对拍 **400 组随机矩阵**，并验证**互补松弛**这个最优性证书
4. **GIoU** 及其关键性质（不相交时仍有梯度，而 IoU 恒为 0）
5. **DETR 完整代价矩阵**（分类项用**概率**而非 log + L1 + GIoU），在合成 TSR 场景上匹配
6. **一对一 vs 一对多**的最小可训练实验：证明一对一不需要 NMS
7. **匹配不稳定性的量化**：叠加训练噪声，统计**匹配翻转率**与**有效监督信号占比**

> 心智模型：**匹配是「动态的标签分配」。它不可微、只决定梯度流向谁；
> 而它每个 iteration 都会重算一次 —— 这就是 DETR 收敛慢的第二个根因。**"""),
    md("""## 1 · 问题形式化：代价矩阵 + 一对一约束 + 总代价最小

先把黄金标准写出来：**暴力枚举所有一对一指派**。它只能用于 n ≤ 7，
但后面所有算法的正确性都要靠它来证明。"""),
    code("""import sys, itertools, math, time
import numpy as np
np.set_printoptions(precision=3, suppress=True)
rng = np.random.default_rng(0)
print('Python', sys.version.split()[0], '| numpy', np.__version__)
print('⚠️  本模块**禁止** scipy.optimize.linear_sum_assignment —— 匈牙利算法要自己写。')

# 5 个 query x 3 个 GT 的代价矩阵（越小越该配对）
C0 = np.array([
    [0.30, 2.10, 1.80],
    [1.90, 0.40, 2.20],
    [2.40, 1.70, 0.50],
    [1.10, 1.30, 1.60],
    [2.00, 2.20, 1.40],
])

def brute_force_assignment(cost):
    '''暴力枚举所有**一对一**指派，返回 (row_ind, col_ind, 最小总代价)。
       n<=m 时枚举「每行去哪一列」；n>m 时枚举「每列由哪一行认领」。
       复杂度 P(max,min) —— 只能用于小矩阵，作为对拍的黄金标准。'''
    a = np.asarray(cost, dtype=float)
    n, m = a.shape
    best, best_pair = np.inf, (np.zeros(0, int), np.zeros(0, int))
    if n <= m:
        for perm in itertools.permutations(range(m), n):
            t = float(sum(a[i, perm[i]] for i in range(n)))
            if t < best:
                best, best_pair = t, (np.arange(n), np.array(perm, dtype=int))
    else:
        for perm in itertools.permutations(range(n), m):
            t = float(sum(a[perm[j], j] for j in range(m)))
            if t < best:
                r = np.array(perm, dtype=int); c = np.arange(m); o = np.argsort(r)
                best, best_pair = t, (r[o], c[o])
    if not np.isfinite(best):
        best = 0.0
    return best_pair[0], best_pair[1], best

r, c, tot = brute_force_assignment(C0)
print('\\n代价矩阵 C[query, GT]:'); print(C0)
print('最优指派:', [(f'q{i}', f'g{j}') for i, j in zip(r, c)], f'| 总代价 {tot:.3f}')
assert list(r) == [0, 1, 2] and list(c) == [0, 1, 2] and abs(tot - 1.20) < 1e-9
print('✅ 枚举了 P(5,3) =', math.perm(5, 3), '种指派')"""),
    code("""# 「GT 集合是无序的」到底意味着什么：换一下 GT 的存储顺序
naive_totals = []
for perm in [[0, 1, 2], [2, 0, 1], [1, 2, 0]]:
    Cp = C0[:, perm]
    _, _, tp = brute_force_assignment(Cp)
    naive = float(sum(Cp[j, j] for j in range(3)))     # 「第 j 个 query 负责第 j 个 GT」
    naive_totals.append(round(naive, 6))
    print(f'GT 顺序 {perm}: **最优**总代价 {tp:.3f} | 按下标硬配的总代价 {naive:.3f}')
    assert abs(tp - tot) < 1e-9, '最优总代价必须与 GT 存储顺序无关'

assert len(set(naive_totals)) == 3, '按下标硬配的损失会随存储顺序变化 —— 它在数学上没有定义'
print(f'\\n按下标硬配得到三个完全不同的值 {naive_totals} —— **同一份标注，换个存储顺序损失就变了**。')
print('✅ 这就是为什么必须先匹配：无序集合之间没有天然的对应关系。')

# 边界：M = 0（TSR 里高速空旷路段整段都是空帧）
r_e, c_e, t_e = brute_force_assignment(C0[:, :0])
print(f'\\nM=0 的空帧: 匹配对数 {len(r_e)}, 总代价 {t_e:.1f} -> 全部 N 个 query 都算 no-object')
assert len(r_e) == 0 and t_e == 0.0
print('⚠️  没对 M=0 做保护是 DETR 复现的经典 crash 点，而且要跑到遇见空帧那个 batch 才炸。')"""),
    md("""## 2 · 增广路径：先解「最多能配几对」

带权问题的地基是无权问题。Kuhn 的算法只有一个想法：
**为每个左点找一条增广路径**——起点是未匹配的左点，终点是未匹配的右点，
路径上「非匹配边 / 匹配边」交替出现。找到就把整条路径取反，匹配数净增 1。

Berge 定理：**一个匹配是最大匹配 ⟺ 图中不存在增广路径。**"""),
    code("""def kuhn_max_matching(adj, n_left, n_right):
    '''0-1 二分图最大匹配（增广路径 / Kuhn 算法）。
       adj[v] = 左点 v 能连的右点列表。返回 (匹配数, match, 每次增广的路径)。
       match[j] = 匹配到右点 j 的左点下标，-1 表示未匹配。'''
    match = [-1] * n_right
    paths = []

    def try_augment(v, used, trace):
        for to in adj[v]:
            if used[to]:
                continue
            used[to] = True
            trace.append((v, to))
            if match[to] == -1 or try_augment(match[to], used, trace):
                match[to] = v
                return True
            trace.pop()                      # 这条分支走不通，回溯
        return False

    cnt = 0
    for v in range(n_left):
        used = [False] * n_right
        trace = []
        if try_augment(v, used, trace):
            cnt += 1
            paths.append(list(trace))
    return cnt, match, paths

# 图 A：4 个 query，3 个 GT，边表示「代价够低，可以配」
ADJ_A = [[0], [0, 1], [1, 2], [2]]
cnt_a, match_a, paths_a = kuhn_max_matching(ADJ_A, 4, 3)
print('图 A  adj =', ADJ_A)
print(f'  最大匹配数 = {cnt_a}  match(右点->左点) = {match_a}')
for k, p in enumerate(paths_a):
    print(f'  为 q{p[0][0]} 找到的交替路径: ' + ' -> '.join(f'q{v}=g{t}' for v, t in p))
assert cnt_a == 3, '3 个右点全被匹配上'
print('  ✅ q1 让位给 q2，自己去了 g2 —— 这就是「链式让位」')"""),
    code("""# 图 B：三个 query 都只能连 g0 —— 瓶颈在右侧
ADJ_B = [[0], [0], [0], [1, 2]]
cnt_b, match_b, _ = kuhn_max_matching(ADJ_B, 4, 3)
print('图 B  adj =', ADJ_B)
print(f'  最大匹配数 = {cnt_b}  match = {match_b}   ← g2 没人能连，永远匹配不上')
assert cnt_b == 2
print('  ⚠️  找不到增广路径 = 这一块已经饱和，多出来的 query 只能落空。')

# 直接对应 DETR 的工程铁律：N < M 时，多出来的 GT **监督信号直接丢失**
print(f'\\n{"单图 GT 数 M":>14s} {"query 数 N":>12s} {"能被匹配的 GT":>14s} {"漏掉":>6s}')
for M, N in [(3, 100), (12, 100), (120, 100), (15, 10)]:
    matched = min(M, N)
    flag = '' if matched == M else '  ← **必然漏检**'
    print(f'{M:>14d} {N:>12d} {matched:>14d} {M - matched:>6d}{flag}')
assert min(120, 100) == 100
print('''
✅ 「N 必须大于单图最大目标数」这条铁律就来自这里。
   TSR 要特别小心：绝大多数帧只有 0-3 块标志，但复杂路口一次能出十几块
   （龙门架 + 路侧杆 + 附着牌）。**按平均数设 N，会在最安全关键的那些帧上漏检。**''')"""),
    md("""## 3 · 从 0-1 到带权：Kuhn–Munkres 与对偶变量

给每行配一个数 `u_i`、每列配一个数 `v_j`，要求 `u_i + v_j <= C_ij`。
则任意合法匹配的总代价都 `>= Σu + Σv`，所以 `Σu + Σv` 是最优值的**下界**。
算法反复做两件事：**在紧边（`u_i+v_j == C_ij`）子图上找增广路径**；
找不到就算出最小松弛量 `δ`，调整 `u/v` 让新的边变紧。

下面是完整的 O(n³) 实现（e-maxx 风格的 KM，要求行数 ≤ 列数；`solve_assignment` 负责转置）。"""),
    code("""OPS = {'count': 0}          # 内层扫描计数器，用来实测复杂度

def hungarian(cost):
    '''Kuhn-Munkres / 匈牙利算法，O(n^3)，**最小化**总代价。
       cost: (n, m) 且 n <= m。返回 (row_ind, col_ind, u, v)。
       u/v 是对偶变量，终止时满足互补松弛 —— 它本身就是一份最优性证书。'''
    a = np.asarray(cost, dtype=float)
    n, m = a.shape
    assert n <= m, '行数必须 <= 列数；请用 solve_assignment 包装'
    INF = float('inf')
    u = np.zeros(n + 1)                 # 行的对偶变量（下标 1..n，0 号是哨兵）
    v = np.zeros(m + 1)                 # 列的对偶变量
    p = np.zeros(m + 1, dtype=int)      # p[j] = 匹配到列 j 的行（1-based），0 = 未匹配
    way = np.zeros(m + 1, dtype=int)    # 记录增广路径上「列 j 是从哪一列来的」

    for i in range(1, n + 1):           # 逐行加入，每加一行做一次增广
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, INF)      # minv[j] = 到列 j 的最小 reduced cost
        used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta, j1 = INF, -1
            for j in range(1, m + 1):           # ← 扫描所有未用列，O(m)
                if used[j]:
                    continue
                OPS['count'] += 1
                cur = a[i0 - 1, j - 1] - u[i0] - v[j]     # reduced cost
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):              # ← 用松弛量 delta 调整对偶变量
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:                      # 走到一个未匹配的列 -> 找到增广路径
                break
        while j0:                               # 沿 way 回溯，翻转整条路径
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1

    cols = np.zeros(n, dtype=int)
    for j in range(1, m + 1):
        if p[j] != 0:
            cols[p[j] - 1] = j - 1
    return np.arange(n), cols, u, v

def solve_assignment(cost):
    '''任意形状的最小代价一对一指派。返回 (row_ind, col_ind)，row_ind 升序。'''
    a = np.asarray(cost, dtype=float)
    if a.size == 0:
        return np.zeros(0, int), np.zeros(0, int)
    if a.shape[0] <= a.shape[1]:
        r_, c_, _, _ = hungarian(a)
        return r_, c_
    r_, c_, _, _ = hungarian(a.T)       # 转置后 行=GT、列=query
    o = np.argsort(c_)
    return c_[o], r_[o]

rr, cc = solve_assignment(C0)
print('匈牙利解:', [(f'q{i}', f'g{j}') for i, j in zip(rr, cc)],
      f'| 总代价 {C0[rr, cc].sum():.3f}')
assert abs(C0[rr, cc].sum() - tot) < 1e-9
print('✅ 与暴力枚举的最优解一致')"""),
    code("""# ============ 与暴力枚举全排列对拍：400 组随机矩阵 ============
rng_t = np.random.default_rng(0)
bad, checked = 0, 0
for _ in range(400):
    n = int(rng_t.integers(1, 7))
    m = int(rng_t.integers(1, 7))
    A = np.round(rng_t.normal(size=(n, m)) * 3, 2)       # **含负数**，刻意增加难度
    r1, c1 = solve_assignment(A)
    _, _, opt = brute_force_assignment(A)
    checked += 1
    if not np.isclose(float(A[r1, c1].sum()), opt, atol=1e-9):
        bad += 1
        print('❌ MISMATCH', n, m, A[r1, c1].sum(), opt)
print(f'随机对拍 {checked} 组（形状 1x1 ~ 6x6，含负代价）：不一致 {bad} 组')
assert bad == 0

# 边界矩阵：全零 / 全相同 / 全负 / 贪心陷阱 / 极长条
CASES = {
    '全零 3x3':      np.zeros((3, 3)),
    '全相同 4x6':    np.ones((4, 6)),
    '全负 5x5':      -np.eye(5),
    '贪心陷阱 2x2':  np.array([[1., 2.], [2., 100.]]),
    '极长条 2x9':    np.round(rng_t.normal(size=(2, 9)), 2),
    '极长条 9x2':    np.round(rng_t.normal(size=(9, 2)), 2),
}
print(f'\\n{"用例":>14s} {"匈牙利":>10s} {"暴力":>10s}  一致')
for name, A in CASES.items():
    r1, c1 = solve_assignment(A)
    got = float(A[r1, c1].sum())
    _, _, opt = brute_force_assignment(A)
    ok = np.isclose(got, opt, atol=1e-9)
    print(f'{name:>14s} {got:>10.3f} {opt:>10.3f}  {"✅" if ok else "❌"}')
    assert ok, name
print('\\n✅ **手写匈牙利算法通过全部对拍** —— 它真的是全局最优，不是「差不多」。')"""),
    code("""# ============ 复杂度：O(n^3) 还是 O(n!)？ ============
sizes = [8, 16, 32, 64, 128]
ops_list, t_list = [], []
rng_c = np.random.default_rng(1)
for n in sizes:
    A = rng_c.random((n, n))
    OPS['count'] = 0
    t0 = time.perf_counter()
    solve_assignment(A)
    t_list.append(time.perf_counter() - t0)
    ops_list.append(OPS['count'])

print(f'{"n":>6s} {"内层扫描次数":>14s} {"耗时(ms)":>10s} {"次数/上一档":>12s}')
for k, n in enumerate(sizes):
    ratio = '-' if k == 0 else f'{ops_list[k] / ops_list[k-1]:.2f}x'
    print(f'{n:>6d} {ops_list[k]:>14d} {t_list[k]*1e3:>10.2f} {ratio:>12s}')
slope = float(np.polyfit(np.log(sizes), np.log(ops_list), 1)[0])
print(f'\\n对数-对数拟合的增长指数 ≈ n^{slope:.2f}   (最坏情况的理论上界是 n^3)')
assert 2.0 < slope < 3.3, slope

print(f'\\n{"n":>6s} {"暴力枚举 n! 种":>20s} {"匈牙利 ~n^3":>14s}')
for n in [5, 8, 10, 20, 100]:
    print(f'{n:>6d} {float(math.factorial(n)):>20.3e} {n**3:>14d}')
inj = math.perm(100, 7)
print(f'\\nDETR 真实规模 N=100 query, M=7 GT -> 指派方案数 = {inj:.4e}')
assert 8e13 < inj < 9e13
assert math.factorial(20) > 2e18
print('''
✅ 面试标准答案骨架：**n 个左点，每个点最多 n 次对偶调整，每次调整扫描 n 列 -> O(n^3)**。
   它和暴力枚举没有任何关系 —— 它是一个基于线性规划对偶的原始-对偶算法。
   实际训练里匹配在 CPU 上做、矩阵极小（100 x 个位数），耗时占比 < 1%。
   真正的代价不在时间，而在它是一个**不可微的离散步骤**。''')"""),
    code("""# ============ 对偶变量：算法自带的「最优性证书」 ============
A = np.round(rng.random((6, 6)) * 10, 2)
r6, c6, u6, v6 = hungarian(A)
reduced = A - u6[1:7][:, None] - v6[1:7][None, :]       # reduced cost = C_ij - u_i - v_j

print('① 对偶可行性  u_i + v_j <= C_ij  ->  reduced cost 处处 >= 0')
print(f'   min(reduced) = {reduced.min():.12f}')
assert reduced.min() > -1e-9

print('② 互补松弛    被匹配上的格子必须取等 (reduced == 0)')
print(f'   匹配格上的 reduced cost = {np.round(reduced[r6, c6], 12)}')
assert np.allclose(reduced[r6, c6], 0.0, atol=1e-9)

print('③ 强对偶      sum(u) + sum(v) == 最优总代价')
lb = float(u6[1:].sum() + v6[1:].sum())
opt = float(A[r6, c6].sum())
print(f'   下界 sum(u)+sum(v) = {lb:.6f}   最优总代价 = {opt:.6f}')
assert abs(lb - opt) < 1e-9

# 矩形情形（DETR 的真实形状）同样成立
B = np.round(rng.random((3, 8)) * 10, 2)
r3, c3, u3, v3 = hungarian(B)
red3 = B - u3[1:4][:, None] - v3[1:9][None, :]
assert red3.min() > -1e-9 and np.allclose(red3[r3, c3], 0.0, atol=1e-9)
assert abs(float(u3[1:].sum() + v3[1:].sum()) - float(B[r3, c3].sum())) < 1e-9
print('\\n✅ 矩形 3x8 同样满足三条性质。')
print('''
✅ 这三条一起构成**最优性证书**：任何人拿到 (匹配, u, v) 都能在 O(nm) 时间内
   独立验证「这个匹配确实是最优的」，而不需要重跑算法。
   面试里补一句「算法终止时自带最优性证书」，这题就满分了。''')"""),
    md("""## 4 · DETR 的代价矩阵：分类项 + L1 项 + GIoU 项

`C_ij = -λ_cls · p̂_i(c_j) + λ_L1 · ‖b̂_i − b_j‖₁ − λ_giou · GIoU(b̂_i, b_j)`，
默认权重 `(1, 5, 2)`，框用**归一化 cxcywh**。

先把 GIoU 写出来并验证它的关键性质：**两框不相交时 IoU 恒为 0（无梯度），而 GIoU 继续下降。**"""),
    code("""def cxcywh_to_xyxy(b):
    b = np.asarray(b, dtype=float)
    cx, cy, w, h = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=-1)

def iou_matrix(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter + 1e-12)

def giou_matrix(a, b):
    '''GIoU = IoU - (C - union)/C，C 为最小外接框面积。范围 [-1, 1]。'''
    a, b = np.asarray(a, float), np.asarray(b, float)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = aa[:, None] + bb[None, :] - inter
    iou = inter / (union + 1e-12)
    ex1 = np.minimum(a[:, None, 0], b[None, :, 0]); ey1 = np.minimum(a[:, None, 1], b[None, :, 1])
    ex2 = np.maximum(a[:, None, 2], b[None, :, 2]); ey2 = np.maximum(a[:, None, 3], b[None, :, 3])
    Cc = np.clip(ex2 - ex1, 0, None) * np.clip(ey2 - ey1, 0, None)
    return iou - (Cc - union) / (Cc + 1e-12)

BOX = np.array([[0., 0., 1., 1.]])
assert abs(giou_matrix(BOX, BOX)[0, 0] - 1.0) < 1e-9, '与自己的 GIoU 必须是 1'

# 关键实验：把一个框沿 x 轴逐渐推开，看 IoU 与 GIoU 各自怎么变
shifts = np.linspace(0.0, 4.0, 9)
ious = np.array([iou_matrix(BOX, np.array([[t, 0., t + 1., 1.]]))[0, 0] for t in shifts])
gious = np.array([giou_matrix(BOX, np.array([[t, 0., t + 1., 1.]]))[0, 0] for t in shifts])
print(f'{"位移":>6s} {"IoU":>9s} {"GIoU":>9s}   说明')
for t, i_, g_ in zip(shifts, ious, gious):
    note = '两框相交' if i_ > 0 else '**不相交：IoU 已无梯度，GIoU 仍在下降**'
    print(f'{t:>6.1f} {i_:>9.4f} {g_:>9.4f}   {note}')

assert np.allclose(ious[2:], 0.0), '位移 >= 1 后两框不相交，IoU 恒为 0'
assert np.all(np.diff(gious) < -1e-9), 'GIoU 必须严格单调下降'
assert gious.min() > -1.0 and gious.max() <= 1.0 + 1e-9
# GIoU <= IoU 恒成立（随机验证）
ra = np.random.default_rng(3)
for _ in range(200):
    p1 = np.sort(ra.random((1, 2)) * 2, axis=1); p2 = np.sort(ra.random((1, 2)) * 2, axis=1)
    q1 = np.sort(ra.random((1, 2)) * 2, axis=1); q2 = np.sort(ra.random((1, 2)) * 2, axis=1)
    X = np.array([[p1[0, 0], p2[0, 0], p1[0, 1], p2[0, 1]]])
    Y = np.array([[q1[0, 0], q2[0, 0], q1[0, 1], q2[0, 1]]])
    assert giou_matrix(X, Y)[0, 0] <= iou_matrix(X, Y)[0, 0] + 1e-9
print('''
✅ **GIoU 相对 IoU 的关键改进：不相交时仍有梯度。**
   训练早期所有预测框都是乱的、几乎没有一个和 GT 相交 ——
   只用 IoU 的话代价矩阵会退化成一片 0，匹配就完全由分类项决定，等于随机分配。''')"""),
    code("""# ============ TSR 锚点：IoU 对小框位移有多敏感 ============
print(f'{"框尺寸(px)":>12s} {"对角位移 2px 后的 IoU":>22s}')
for s in [8, 16, 24, 40, 64, 128]:
    a_ = np.array([[0., 0., float(s), float(s)]])
    b_ = np.array([[2., 2., float(s) + 2, float(s) + 2]])
    print(f'{f"{s}x{s}":>12s} {iou_matrix(a_, b_)[0, 0]:>22.4f}')
iou8  = iou_matrix(np.array([[0., 0., 8., 8.]]),   np.array([[2., 2., 10., 10.]]))[0, 0]
iou64 = iou_matrix(np.array([[0., 0., 64., 64.]]), np.array([[2., 2., 66., 66.]]))[0, 0]
assert abs(iou8 - 36 / 92) < 1e-9 and abs(iou64 - 3844 / 4348) < 1e-9
print(f'''
⚠️  同样 2 像素的对角位移：8x8 的框 IoU 从 1.0 掉到 {iou8:.2f}，
    64x64 的框还有 {iou64:.2f}。**同一个 IoU 数值对不同尺度完全不是一回事。**
    TSR 里 60 米外的限速牌只有 20 来像素，标注误差本身就有 ±2px ——
    这意味着**代价矩阵里 GIoU 项对小目标天然噪声更大**，
    也就是第 8 节要讲的「势均力敌」为什么在小目标场景里是常态。''')"""),
    code("""# ============ DETR 完整代价矩阵，跑在一个合成 TSR 场景上 ============
# 归一化 cxcywh；像素尺寸按 1920x1080 换算（24px 宽 -> 24/1920 = 0.0125）
GT_CXCYWH = np.array([
    [0.4700, 0.4200, 0.0125, 0.0222],   # g0 远处限速60      24x24 px
    [0.6350, 0.3700, 0.0208, 0.0370],   # g1 中距禁止超车    40x40 px
    [0.3490, 0.4170, 0.0313, 0.0556],   # g2 近处注意行人    60x60 px
    [0.7500, 0.5500, 0.0500, 0.0889],   # g3 很近的指路牌    96x96 px
])
GT_LABEL = np.array([2, 5, 9, 13])          # 类别 id（共 20 类）
GT_NAME  = ['限速60(24px)', '禁止超车(40px)', '注意行人(60px)', '指路牌(96px)']

N_Q, N_CLS = 12, 20
rg = np.random.default_rng(11)
q_prob_all = rg.uniform(0.01, 0.06, size=(N_Q, N_CLS))                 # 大多数 query 都很不自信
q_box_all = np.column_stack([rg.uniform(0.1, 0.9, N_Q), rg.uniform(0.1, 0.9, N_Q),
                             rg.uniform(0.10, 0.35, N_Q), rg.uniform(0.10, 0.35, N_Q)])
GOOD = [2, 5, 7, 10]                        # 这 4 个 query 已经学会了对应的标志
for k, qi in enumerate(GOOD):
    q_box_all[qi] = GT_CXCYWH[k] + rg.normal(0, 0.001, 4)              # 框几乎准确
    q_prob_all[qi, GT_LABEL[k]] = 0.80 + 0.04 * k                      # 分类也自信

W_CLS, W_L1, W_GIOU = 1.0, 5.0, 2.0

def detr_cost_matrix_ref(prob, pred_cxcywh, tgt_labels, tgt_cxcywh,
                         w_cls=W_CLS, w_l1=W_L1, w_giou=W_GIOU):
    '''DETR 匹配代价矩阵 (N, M)。注意分类项用**概率**而不是 log。'''
    prob = np.asarray(prob, float)
    cls_cost  = -prob[:, np.asarray(tgt_labels, int)]                  # (N, M)
    l1_cost   = np.abs(np.asarray(pred_cxcywh, float)[:, None, :]
                       - np.asarray(tgt_cxcywh, float)[None, :, :]).sum(-1)
    giou_cost = -giou_matrix(cxcywh_to_xyxy(pred_cxcywh), cxcywh_to_xyxy(tgt_cxcywh))
    return w_cls * cls_cost + w_l1 * l1_cost + w_giou * giou_cost

COST_TSR = detr_cost_matrix_ref(q_prob_all, q_box_all, GT_LABEL, GT_CXCYWH)
print('代价矩阵 (12 query x 4 GT) 的前 8 行:')
print('      ' + '  '.join(f'{n:>16s}' for n in GT_NAME))
for i in range(8):
    mark = '  <- 好 query' if i in GOOD else ''
    print(f'  q{i:<2d} ' + '  '.join(f'{COST_TSR[i, j]:>16.3f}' for j in range(4)) + mark)

r_t, c_t = solve_assignment(COST_TSR)
_, _, opt_t = brute_force_assignment(COST_TSR)       # P(12,4)=11880 种，还能暴力
print(f'\\n匈牙利总代价 {COST_TSR[r_t, c_t].sum():.4f} | 暴力最优 {opt_t:.4f}')
assert np.isclose(float(COST_TSR[r_t, c_t].sum()), opt_t, atol=1e-9)
print('匹配结果:')
for i, j in zip(r_t, c_t):
    print(f'  {GT_NAME[j]:>16s}  <-  q{i:<2d}  (代价 {COST_TSR[i, j]:.3f})')
assert list(r_t) == GOOD and list(c_t) == [0, 1, 2, 3]
print(f'\\n✅ 4 个 GT 恰好被 4 个「好 query」认领，其余 {N_Q - 4} 个 query 全判 no-object。')"""),
    md("""## 5 · 为什么分类项用 `−p` 而不是 `−log p`

DETR 论文里明确写了：匹配代价的分类项用**概率**而非对数概率，
「这样它就与框的代价项在同一量级上」。下面是一个三选一的最小反例，
换成 `−log p` 就会选错。"""),
    code("""# 三个候选 query 争夺同一个 GT
CAND = [
    ('q0  分类很自信但框偏了', 0.90, 0.40, 0.20),   # (名字, 分类概率, L1, GIoU)
    ('q1  框几乎完美但分类弱', 0.02, 0.02, 0.95),
    ('q2  两头都平庸',        0.30, 0.25, 0.50),
]
print(f'{"候选":<26s} {"p":>6s} {"L1":>6s} {"GIoU":>6s} | {"cost(-p)":>10s} {"cost(-log p)":>13s}')
cost_p, cost_log = [], []
for name, p_, l1_, g_ in CAND:
    cp  = W_CLS * (-p_)          + W_L1 * l1_ + W_GIOU * (-g_)
    cl  = W_CLS * (-np.log(p_))  + W_L1 * l1_ + W_GIOU * (-g_)
    cost_p.append(cp); cost_log.append(cl)
    print(f'{name:<26s} {p_:>6.2f} {l1_:>6.2f} {g_:>6.2f} | {cp:>10.3f} {cl:>13.3f}')

win_p, win_log = int(np.argmin(cost_p)), int(np.argmin(cost_log))
print(f'\\n用 -p     匹配 -> 选中 q{win_p}  ({CAND[win_p][0].split()[1]})')
print(f'用 -log p 匹配 -> 选中 q{win_log}  ({CAND[win_log][0].split()[1]})')
assert win_p == 1 and win_log == 2, (win_p, win_log)
print('''
❌ 换成 -log p 之后，**框最准的 q1 被判成背景**，一个两头平庸的 q2 拿走了这个 GT。
   原因：-log(0.02) = 3.91，而整个框项才 -1.8 ~ +2.0 —— **分类项以数量级优势主导了匹配**。

✅ 两层原因（面试答案）：
   ① **有界**：-p ∈ [-1,0]，与 GIoU 的 [-1,1] 同量级；-log p 在 p->0 时趋于 +∞。
      DETR 有 91 类，训练初期每类概率约 0.01，-log p ≈ 4.6，直接压过框项。
   ② **饱和**：-p 在高概率区增益递减（0.9->0.99 只多赚 0.09），
      不会让「非常自信」的 query 压倒「框更准」的 query。

⚠️  但**损失函数里仍然用 -log p（交叉熵）**，只有匹配代价用 -p。
    记法：**匹配要「公平比较」所以要有界；损失要「强力纠错」所以要无界。**''')"""),
    code("""# 权重敏感性：匹配代价的权重不是损失权重，它决定的是「谁认领这个 GT」
box_term = np.array([W_L1 * l1_ + W_GIOU * (-g_) for _, _, l1_, g_ in CAND])
probs    = np.array([p_ for _, p_, _, _ in CAND])
print('框项（与 w_cls 无关）:', np.round(box_term, 3))
print(f'\\n{"w_cls":>7s} {"cost q0":>9s} {"cost q1":>9s} {"cost q2":>9s}  胜者')
winners = []
for w in [0, 1, 2, 3, 4, 5]:
    cost_w = box_term - w * probs
    win = int(np.argmin(cost_w))
    winners.append(win)
    print(f'{w:>7d} {cost_w[0]:>9.3f} {cost_w[1]:>9.3f} {cost_w[2]:>9.3f}  q{win}')
assert winners == [1, 1, 1, 1, 0, 0], winners
print('''
⚠️  w_cls 从 3 调到 4，认领者就从「框好的 q1」翻转成「分类自信的 q0」。
✅ **匹配代价的权重决定了梯度流向谁，它比损失权重更关键、也更少被调。**
   DETR 的 (1, 5, 2) 是论文里试出来的，此后几乎所有工作都照抄 ——
   但它对数据集分布是敏感的：小目标为主的数据集（TSR / 航拍）理论上
   应该提高 GIoU 权重或换用尺度不变的度量（见 C57 模块 03 的 NWD）。''')"""),
    md("""## 6 · 矩形代价矩阵与 no-object padding

数学表述里要把 GT 集合 pad 到大小 N，让 σ 成为一个排列。
**但 padding 列的代价是同一个常数 c**，每种指派方案里恰好有 (N−M) 行落到 padding 列，
贡献 (N−M)·c —— 对所有方案都一样，所以 **argmin 与 c 无关，直接解矩形问题即可**。"""),
    code("""def pad_cost_to_square_ref(cost, fill):
    '''把 (N, M) 的代价矩阵右侧补 (N-M) 列常数 fill，成为 (N, N) 方阵。'''
    a = np.asarray(cost, dtype=float)
    n, m = a.shape
    if n <= m:
        return a
    return np.hstack([a, np.full((n, n - m), float(fill))])

rect_pairs = sorted((int(i), int(j)) for i, j in zip(*solve_assignment(COST_TSR)))
print(f'直接解矩形 12x4 : {rect_pairs}')
print(f'\\n{"padding 常数 c":>16s} {"落到真实列的配对":>44s}  与矩形解一致')
for fill in [-100.0, 0.0, 1.0, 100.0]:
    Csq = pad_cost_to_square_ref(COST_TSR, fill)
    rs, cs = solve_assignment(Csq)
    real = sorted((int(i), int(j)) for i, j in zip(rs, cs) if j < COST_TSR.shape[1])
    print(f'{fill:>16.1f} {str(real):>44s}  {"✅" if real == rect_pairs else "❌"}')
    assert real == rect_pairs, fill
    assert Csq.shape == (12, 12)

print('''
✅ **c 取 -100 还是 +100 都不影响匹配结果** —— 所以工程上不需要真的 padding，
   DETR 官方实现就是直接把 N x M 的矩形矩阵扔给求解器。

⚠️  但这个设计有后果：「一个 query 该不该被判为背景」完全**不由匹配代价决定**，
   只由「有没有轮到它」决定。哪怕某个 query 的框和 GT 极度吻合，
   只要有另一个 query 更吻合，它就被打成背景、承受完整的 no-object 损失。
   **这正是「训练期压制重复」的机械原理，也是匹配不稳定伤害如此之大的原因。**''')"""),
    md("""## 7 · 一对一 vs 一对多：为什么一对一能替代 NMS

同一份数据、同一个模型、同一套手写梯度，**只改「分配方式」这一个变量**，训练 600 步。

模型极简：8 个 query，每个有一个位置 `p_i` 和一个分数 logit `s_i`；2 个 GT 在 0.30 / 0.70。
- **一对多**：距离 GT 小于 0.15 的 query 全算正样本（模拟 center sampling）
- **一对一**：用匈牙利匹配，每个 GT 只有 1 个正样本"""),
    code("""def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

def toy_train(mode, steps=600, lr_s=0.2, lr_p=0.005, radius=0.15):
    '''8 个 query、2 个 GT 的一维玩具检测器，纯手写梯度。
       返回 (最终位置, 最终分数, 每步的正样本集合大小)。'''
    g = np.array([0.30, 0.70])
    p = np.array([0.0625, 0.1875, 0.3125, 0.4375, 0.5625, 0.6875, 0.8125, 0.9375])
    s = np.zeros(8)
    n_pos_hist = []
    for _ in range(steps):
        prob = sigmoid(s)
        if mode == 'one2one':
            # 匹配代价 = L1(位置) - 概率，与 DETR 同构
            Ct = np.abs(p[:, None] - g[None, :]) - 1.0 * prob[:, None]
            ri, ci = solve_assignment(Ct)
            pos = {int(a_): int(b_) for a_, b_ in zip(ri, ci)}
        else:                                   # one2many：半径内全算正样本
            pos = {}
            for j in range(len(g)):
                d = np.abs(p - g[j])
                idx = np.where(d < radius)[0]
                if len(idx) == 0:
                    idx = [int(np.argmin(d))]
                for i in idx:
                    pos[int(i)] = j
        n_pos_hist.append(len(pos))
        # 分类梯度：dBCE(s,y)/ds = sigmoid(s) - y
        gs = prob.copy()
        for i in pos:
            gs[i] = prob[i] - 1.0
        s = s - lr_s * gs
        # 位置梯度（只有正样本有框损失）：d|p-g|/dp = sign(p-g)
        gp = np.zeros_like(p)
        for i, j in pos.items():
            gp[i] = np.sign(p[i] - g[j])
        p = p - lr_p * gp
    return p, sigmoid(s), n_pos_hist

p_o2m, s_o2m, npos_o2m = toy_train('one2many')
p_o2o, s_o2o, npos_o2o = toy_train('one2one')

print(f'{"query":>7s} {"one2many 位置":>15s} {"分数":>7s} | {"one2one 位置":>14s} {"分数":>7s}')
for i in range(8):
    f1 = '  ←触发' if s_o2m[i] > 0.5 else ''
    f2 = '  ←触发' if s_o2o[i] > 0.5 else ''
    print(f'{f"q{i}":>7s} {p_o2m[i]:>15.4f} {s_o2m[i]:>7.3f}{f1:<8s}| {p_o2o[i]:>14.4f} {s_o2o[i]:>7.3f}{f2}')

fire_o2m = np.where(s_o2m > 0.5)[0]
fire_o2o = np.where(s_o2o > 0.5)[0]
print(f'\\n每步正样本数：one2many = {npos_o2m[-1]}，one2one = {npos_o2o[-1]}')
print(f'训练后触发的 query：one2many {fire_o2m.tolist()} ({len(fire_o2m)} 个) | '
      f'one2one {fire_o2o.tolist()} ({len(fire_o2o)} 个)')
assert len(fire_o2m) == 6 and len(fire_o2o) == 2
assert fire_o2o.tolist() == [2, 5]"""),
    code("""def nms_1d(pos, score, radius=0.1):
    '''一维 NMS：按分数降序保留，抑制距离小于 radius 的。'''
    order = np.argsort(-score)
    keep = []
    for i in order:
        if all(abs(pos[i] - pos[k]) > radius for k in keep):
            keep.append(int(i))
    return keep

k_o2m = nms_1d(p_o2m[fire_o2m], s_o2m[fire_o2m])
k_o2o = nms_1d(p_o2o[fire_o2o], s_o2o[fire_o2o])
print(f'one2many: 触发 {len(fire_o2m)} 个 -> NMS 后 {len(k_o2m)} 个   **必须靠 NMS 才能回到 2**')
print(f'one2one : 触发 {len(fire_o2o)} 个 -> NMS 后 {len(k_o2o)} 个   **NMS 什么也没删，它是多余的**')
assert len(k_o2m) == 2 and len(k_o2o) == 2

# 监督密度的代价：一对一的正样本数少了多少
dens = npos_o2m[-1] / npos_o2o[-1]
print(f'\\n监督密度：one2many 是 one2one 的 {dens:.1f} 倍（真实检测器上是几百倍）')
assert dens >= 3.0
print('''
✅ 三句话总结（面试标准答案）：
   ① 重复框的根源是「多个预测同时被判为同一目标的**正样本**」；
   ② 一对一匹配从**训练目标**上禁止了这件事；
   ③ 落选的 query 收到 no-object 梯度，于是学会主动把自己压低。
   —— **NMS 是在推理期删掉重复，一对一匹配是在训练期不让重复长出来。**

⚠️  代价也要说：**监督信号密度掉了一个数量级**，这是 DETR 需要 500 epoch 的第一个根因。
    所以后来出现了 Group DETR / H-DETR / Co-DETR：训练时加一对多分支、推理时丢掉。
    **它们证明了一对一是「推理端的需求」，不是「训练端的最优」。**

⚠️  另一个高频陷阱题：把 decoder 的 self-attention 去掉还能不出重复框吗？**不能。**
    一对一匹配提供的是「不要重复」的**动机**，self-attention 提供的是
    「知道别人已经认领了」的**能力** —— 两者缺一不可。''')"""),
    md("""## 8 · 匹配不稳定性：DETR 收敛慢的第二个根因

匹配是一个离散 `argmin`，代价矩阵的微小扰动可以让整个指派翻转。
而代价矩阵在训练中每个 iteration 都在变（模型在更新、数据在换、增强在随机）。

下面构造 8 query × 4 GT 的代价矩阵：GT0 / GT2 各有两个**势均力敌**的候选（代价差 0.01 / 0.02），
GT1 / GT3 的候选**差距明显**（代价差 0.70）。叠加高斯噪声模拟训练抖动，跑 2000 个 epoch。"""),
    code("""def flip_experiment(sigma, T=2000, seed=0):
    '''返回 (history, base)。history[t, j] = 第 t 个 epoch 里认领 GT j 的 query 下标。'''
    r_ = np.random.default_rng(seed)
    base = np.full((8, 4), 5.0)              # 其余 query 代价很高，不参与竞争
    base[0, 0], base[1, 0] = 0.50, 0.51      # GT0：势均力敌，差 0.01
    base[2, 1], base[3, 1] = 0.20, 0.90      # GT1：差距明显，差 0.70
    base[4, 2], base[5, 2] = 0.40, 0.42      # GT2：势均力敌，差 0.02
    base[6, 3], base[7, 3] = 0.30, 1.00      # GT3：差距明显，差 0.70
    hist = np.zeros((T, 4), dtype=int)
    for t in range(T):
        Ct = base + r_.normal(0, sigma, size=base.shape)      # 训练抖动
        ri, ci = solve_assignment(Ct)
        owner = np.zeros(4, dtype=int)
        for a_, b_ in zip(ri, ci):
            owner[b_] = a_
        hist[t] = owner
    return hist, base

SIGMAS = [0.002, 0.01, 0.05, 0.2]
rates, HIST_005 = {}, None
print(f'{"噪声 σ":>8s} {"GT0(差0.01)":>12s} {"GT1(差0.70)":>12s} '
      f'{"GT2(差0.02)":>12s} {"GT3(差0.70)":>12s} {"平均":>8s}')
for sg in SIGMAS:
    h, _ = flip_experiment(sg)
    f = (h[1:] != h[:-1]).mean(axis=0)          # 相邻 epoch 认领者是否变了
    rates[sg] = f
    if sg == 0.05:
        HIST_005 = h
    print(f'{sg:>8.3f} {f[0]:>12.3f} {f[1]:>12.3f} {f[2]:>12.3f} {f[3]:>12.3f} {f.mean():>8.3f}')

means = [rates[s].mean() for s in SIGMAS]
assert means[0] < means[1] < means[2] <= means[3], means
assert rates[0.05][0] > 0.30 and rates[0.05][2] > 0.30, '势均力敌的 GT 翻转率应当很高'
assert rates[0.05][1] < 0.05 and rates[0.05][3] < 0.05, '差距明显的 GT 几乎不翻转'
print('''
✅ 三个必须读出来的结论：
   ① **不稳定性是局部的**：代价差 0.70 的 GT 在任何噪声下都几乎不翻转；
      代价差 0.01 的一翻就是 48%。「匹配不稳定」= 一小撮势均力敌的候选反复易主。
   ② **翻转率饱和在 0.5**：完全势均力敌时每 epoch 各 50%，相邻两 epoch 不同的概率就是 0.5。
      σ 从 0.05 加到 0.20，平均翻转率只从 0.239 涨到 0.252，就是因为已经饱和。
   ③ **「势均力敌」在真实训练里是常态**：一块 24px 的远处限速牌周围，
      好几个 query 的框只差一两个像素，代价差恰恰就在 0.01 这个量级 ——
      而随机裁剪、颜色抖动带来的扰动远超 0.01。**小目标 + 密集目标最严重，正是 TSR 的画像。**''')"""),
    code("""# 不稳定性到底伤害了什么：**有效监督信号占比**
def supervision_efficiency(hist, n_query=8):
    '''对每个 query：每个 epoch 它要么是前景(+1) 要么是背景(-1)。
       有效信号占比 = |Σg| / Σ|g|。稳定 = 1.0（方向一致）；来回翻转 -> 趋近 0（互相抵消）。'''
    eff = np.zeros(n_query)
    matched_frac = np.zeros(n_query)
    for i in range(n_query):
        is_fg = (hist == i).any(axis=1)
        g = np.where(is_fg, 1.0, -1.0)
        eff[i] = abs(g.sum()) / np.abs(g).sum()
        matched_frac[i] = is_fg.mean()
    return eff, matched_frac

eff, frac = supervision_efficiency(HIST_005)
ROLE = ['GT0 候选(势均力敌)', 'GT0 候选(势均力敌)', 'GT1 赢家(稳定)', 'GT1 输家(稳定)',
        'GT2 候选(势均力敌)', 'GT2 候选(势均力敌)', 'GT3 赢家(稳定)', 'GT3 输家(稳定)']
print(f'{"query":>7s} {"角色":>22s} {"被认领的 epoch 占比":>20s} {"有效监督信号占比":>18s}')
for i in range(8):
    print(f'{f"q{i}":>7s} {ROLE[i]:>22s} {frac[i]:>20.3f} {eff[i]:>18.3f}')

assert eff[2] > 0.99 and eff[3] > 0.99 and eff[6] > 0.99 and eff[7] > 0.99
assert eff[0] < 0.25 and eff[1] < 0.25 and eff[4] < 0.35 and eff[5] < 0.35
ratio = eff[2] / max(eff[0], 1e-9)
print(f'\\n稳定 query 的有效信号是势均力敌 query 的 {ratio:.1f} 倍')
assert ratio > 4.0
print('''
✅ **等价说法：有歧义的那批 query，有效学习率只有别人的 1/9。**
   分类梯度一会儿推向前景、一会儿推向 no-object，方向来回抵消；
   框梯度更糟 —— 落选的 epoch 里它**完全收不到框损失**（no-object 不算框损失）。

✅ 这个观察直接催生了后面两代工作（模块 04 展开）：
   · **DN-DETR**：把带噪 GT 作为额外 query，标签已知且固定，**完全绕过匹配** -> 50 epoch 追平 500
   · **DINO**：对比去噪（小噪声正样本 + 大噪声负样本），教模型「多远算同一个目标」
   · **Stable-DINO**：用定位质量给分类分数加权再进匹配，**直接减少势均力敌**
   · **Group / H / Co-DETR**：用一对多的监督密度**对冲**不稳定的伤害

💡 可迁移的心法：凡是「用一个离散 argmin 决定谁接受监督」的系统，都有优化目标抖动问题 ——
   MoE 的专家路由、稀疏检索的 top-k、SimOTA 的 dynamic-k 全是同一个病。
   通用解法只有两类：**让选择更确定**，或者**绕过选择**。''')"""),
    md("""## ✏️ 练习 1：手写标量版 GIoU

实现 `giou_pair(box_a, box_b)`：两个 **xyxy** 格式的框（长度 4 的序列），返回一个标量 GIoU。

```
IoU  = inter / union
GIoU = IoU - (C - union) / C        C = 最小外接框的面积
```

**白板高频题**，写的时候注意三点：交集要 `clip` 到非负、除零保护、
以及 `C` 用的是**最小外接框**而不是并集的外接框（这两个说法其实等价，但很多人写错成前者的补集）。"""),
    code("""def giou_pair(box_a, box_b):
    # TODO: 返回标量 GIoU，范围 [-1, 1]
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
# 手算：a=[0,0,2,2], b=[1,1,3,3] -> inter=1, union=4+4-1=7, IoU=1/7
#       最小外接框 [0,0,3,3] 面积 9 -> GIoU = 1/7 - (9-7)/9 = 1/7 - 2/9
assert abs(giou_pair([0., 0., 2., 2.], [1., 1., 3., 3.]) - (1/7 - 2/9)) < 1e-9
assert abs(giou_pair([0., 0., 2., 2.], [0., 0., 2., 2.]) - 1.0) < 1e-9, '与自己的 GIoU = 1'
far = giou_pair([0., 0., 1., 1.], [5., 5., 6., 6.])
assert abs(far - (-34 / 36)) < 1e-9, f'完全不相交且很远 -> 接近 -1，得到 {far}'

# 与本 notebook 的向量化实现对拍 300 组随机框
rq = np.random.default_rng(21)
for _ in range(300):
    xs = np.sort(rq.random(2) * 4); ys = np.sort(rq.random(2) * 4)
    us = np.sort(rq.random(2) * 4); vs = np.sort(rq.random(2) * 4)
    A_ = [xs[0], ys[0], xs[1] + 1e-3, ys[1] + 1e-3]
    B_ = [us[0], vs[0], us[1] + 1e-3, vs[1] + 1e-3]
    ref = float(giou_matrix(np.array([A_]), np.array([B_]))[0, 0])
    got = float(giou_pair(A_, B_))
    assert abs(got - ref) < 1e-8, (A_, B_, got, ref)
    assert -1.0 - 1e-9 <= got <= 1.0 + 1e-9
print('✅ 练习 1 通过：与向量化实现在 300 组随机框上完全一致，且恒在 [-1, 1] 内')
print('   面试加分点：说清「GIoU 相对 IoU 的价值是不相交时仍有梯度」，而不是只背公式。')"""),
    md("""## ✏️ 练习 2：DETR 的完整代价矩阵

实现 `detr_cost_matrix(prob, pred_cxcywh, tgt_labels, tgt_cxcywh, w_cls, w_l1, w_giou)`：

- `prob`：`(N, C)` 每个 query 在 C 个类上的 **softmax 概率**
- `pred_cxcywh`：`(N, 4)` 归一化 cxcywh 预测框
- `tgt_labels`：`(M,)` 每个 GT 的类别 id
- `tgt_cxcywh`：`(M, 4)` 归一化 cxcywh GT 框

返回 `(N, M)` 的代价矩阵：`w_cls·(−prob[:, tgt_labels]) + w_l1·L1 + w_giou·(−GIoU)`。

**注意分类项用概率不是 log**；并且必须能处理 `M = 0`（空帧）。
可以直接调用本 notebook 已有的 `cxcywh_to_xyxy` / `giou_matrix`。"""),
    code("""def detr_cost_matrix(prob, pred_cxcywh, tgt_labels, tgt_cxcywh,
                     w_cls=1.0, w_l1=5.0, w_giou=2.0):
    # TODO: 返回 (N, M) 代价矩阵
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
# 手算：prob=[0.1,0.7,0.2] 目标类=1 -> cls = -0.7
#       pred(0.5,0.5,0.2,0.2) vs tgt(0.5,0.5,0.1,0.1) -> L1 = 0+0+0.1+0.1 = 0.2
#       小框完全落在大框内: inter=0.01, union=0.04 -> IoU=0.25，外接框=大框 -> GIoU=0.25
#       cost = -0.7 + 5*0.2 + 2*(-0.25) = -0.2
C_hand = detr_cost_matrix(np.array([[0.1, 0.7, 0.2]]), np.array([[0.5, 0.5, 0.2, 0.2]]),
                          np.array([1]), np.array([[0.5, 0.5, 0.1, 0.1]]), 1.0, 5.0, 2.0)
assert C_hand.shape == (1, 1) and abs(C_hand[0, 0] - (-0.2)) < 1e-9, C_hand

# 与本 notebook 的参考实现在真实 TSR 场景上完全一致
C_ex = detr_cost_matrix(q_prob_all, q_box_all, GT_LABEL, GT_CXCYWH, 1.0, 5.0, 2.0)
assert C_ex.shape == (12, 4) and np.allclose(C_ex, COST_TSR)
r_ex, c_ex = solve_assignment(C_ex)
assert list(r_ex) == GOOD and list(c_ex) == [0, 1, 2, 3]

# 单项开关：只留 GIoU 项时必须等于 -GIoU
C_g = detr_cost_matrix(q_prob_all, q_box_all, GT_LABEL, GT_CXCYWH, 0.0, 0.0, 1.0)
assert np.allclose(C_g, -giou_matrix(cxcywh_to_xyxy(q_box_all), cxcywh_to_xyxy(GT_CXCYWH)))
# 只留分类项时必须等于 -prob
C_c = detr_cost_matrix(q_prob_all, q_box_all, GT_LABEL, GT_CXCYWH, 1.0, 0.0, 0.0)
assert np.allclose(C_c, -q_prob_all[:, GT_LABEL])
# M=0 的空帧
C_0 = detr_cost_matrix(q_prob_all, q_box_all, np.zeros(0, int), np.zeros((0, 4)), 1.0, 5.0, 2.0)
assert C_0.shape == (12, 0), C_0.shape
r_0, c_0 = solve_assignment(C_0)
assert len(r_0) == 0
print('✅ 练习 2 通过：三项 + 权重开关 + M=0 空帧全部正确')
print('   面试加分点：主动说出「匹配代价用 -p、损失用 -log p」这个区别。')"""),
    md("""## ✏️ 练习 3：padding 到方阵，并证明它不改变结果

实现 `pad_cost_to_square(cost, fill)`：把 `(N, M)`（`N >= M`）的代价矩阵右侧补
`N - M` 列常数 `fill`，返回 `(N, N)` 方阵；若 `N <= M` 则原样返回。

然后用自测验证：**无论 `fill` 取什么值，落在真实列上的配对都与直接解矩形问题相同。**
这就是「工程上不需要真的 padding」的证明。"""),
    code("""def pad_cost_to_square(cost, fill):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
Csq = pad_cost_to_square(COST_TSR, 3.0)
assert Csq.shape == (12, 12)
assert np.allclose(Csq[:, :4], COST_TSR) and np.allclose(Csq[:, 4:], 3.0)
assert pad_cost_to_square(np.ones((3, 7)), 9.0).shape == (3, 7), 'N<=M 时原样返回'

base_pairs = sorted((int(i), int(j)) for i, j in zip(*solve_assignment(COST_TSR)))
for fill in [-1000.0, -1.0, 0.0, 2.5, 1000.0]:
    rs, cs = solve_assignment(pad_cost_to_square(COST_TSR, fill))
    real = sorted((int(i), int(j)) for i, j in zip(rs, cs) if j < COST_TSR.shape[1])
    assert real == base_pairs, (fill, real)
    # 方阵总代价 = 矩形最优 + (N-M)*fill —— 常数偏移，与 argmin 无关
    tot_sq = float(pad_cost_to_square(COST_TSR, fill)[rs, cs].sum())
    tot_rect = float(COST_TSR[tuple(np.array(base_pairs).T)].sum())
    assert abs(tot_sq - (tot_rect + 8 * fill)) < 1e-6, (fill, tot_sq, tot_rect)
print(f'padding 常数取 -1000 ~ +1000，真实配对恒为 {base_pairs}')
print('✅ 练习 3 通过：总代价只差一个常数 (N-M)*c，**argmin 与 c 无关**')
print('   所以 DETR 官方实现直接把 N x M 的矩形矩阵扔给求解器，不做 padding。')"""),
    md("""## ✏️ 练习 4：匹配翻转率

实现 `match_flip_rate(history)`：`history` 是 `(T, M)` 的整数数组，
`history[t, j]` 表示第 t 个 epoch 里认领 GT j 的 query 下标。

返回 `(per_gt, mean_rate)`：
- `per_gt[j]` = 相邻两个 epoch 认领者发生变化的比例
- `mean_rate` = `per_gt` 的均值

`T < 2` 时无法定义翻转，返回全 0（**不要让它出 nan**——这是训练监控里最烦人的一类 bug）。

**这是可以直接搬到线上训练监控里的指标**：它比 loss 更早告诉你「匹配收敛了没有」。"""),
    code("""def match_flip_rate(history):
    # TODO: 返回 (per_gt, mean_rate)
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
H = np.array([[0, 2],
              [1, 2],
              [0, 2],
              [0, 2]])
per, mean_ = match_flip_rate(H)
assert np.allclose(per, [2 / 3, 0.0]), per      # GT0: 0->1, 1->0, 0->0 => 2/3；GT1 从不变
assert abs(mean_ - 1 / 3) < 1e-12

per1, mean1 = match_flip_rate(np.array([[1, 2, 3]]))
assert np.allclose(per1, 0.0) and mean1 == 0.0 and np.all(np.isfinite(per1)), 'T<2 不能出 nan'

# 在第 8 节的真实实验数据上复算，必须与那里的统计完全一致
per2, mean2 = match_flip_rate(HIST_005)
assert np.allclose(per2, rates[0.05]), (per2, rates[0.05])
print(f'σ=0.05 的逐 GT 翻转率 = {np.round(per2, 3).tolist()}  平均 {mean2:.3f}')

print(f'\\n{"训练阶段":>16s} {"典型 flip_rate":>14s}  判读')
for stage, fr, note in [('epoch 0-10', 0.55, '正常：模型还没学会，匹配自然乱'),
                        ('epoch 10-30', 0.18, '正常：应当稳步下降'),
                        ('epoch 30+', 0.35, '**异常**：匹配没收敛 -> 考虑 DN-DETR 的去噪 query')]:
    print(f'{stage:>16s} {fr:>14.2f}  {note}')
print('\\n✅ 练习 4 通过：**这个指标比 loss 更早暴露「匹配没收敛」**，务必挂进 tensorboard。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def giou_pair(box_a, box_b):
    ax1, ay1, ax2, ay2 = [float(v) for v in box_a]
    bx1, by1, bx2, by2 = [float(v) for v in box_b]
    # 交集
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(ix2 - ix1, 0.0) * max(iy2 - iy1, 0.0)
    area_a = max(ax2 - ax1, 0.0) * max(ay2 - ay1, 0.0)
    area_b = max(bx2 - bx1, 0.0) * max(by2 - by1, 0.0)
    union = area_a + area_b - inter
    iou = inter / (union + 1e-12)
    # 最小外接框
    cx1, cy1 = min(ax1, bx1), min(ay1, by1)
    cx2, cy2 = max(ax2, bx2), max(ay2, by2)
    c_area = max(cx2 - cx1, 0.0) * max(cy2 - cy1, 0.0)
    return iou - (c_area - union) / (c_area + 1e-12)"""),
    code("""# 练习 2 参考答案
def detr_cost_matrix(prob, pred_cxcywh, tgt_labels, tgt_cxcywh,
                     w_cls=1.0, w_l1=5.0, w_giou=2.0):
    prob = np.asarray(prob, dtype=float)
    pred = np.asarray(pred_cxcywh, dtype=float)
    tgt_l = np.asarray(tgt_labels, dtype=int)
    tgt_b = np.asarray(tgt_cxcywh, dtype=float).reshape(-1, 4)
    cls_cost  = -prob[:, tgt_l]                                   # (N,M) 用**概率**不是 log
    l1_cost   = np.abs(pred[:, None, :] - tgt_b[None, :, :]).sum(-1)
    giou_cost = -giou_matrix(cxcywh_to_xyxy(pred), cxcywh_to_xyxy(tgt_b))
    return w_cls * cls_cost + w_l1 * l1_cost + w_giou * giou_cost"""),
    code("""# 练习 3 参考答案
def pad_cost_to_square(cost, fill):
    a = np.asarray(cost, dtype=float)
    n, m = a.shape
    if n <= m:
        return a
    return np.hstack([a, np.full((n, n - m), float(fill))])"""),
    code("""# 练习 4 参考答案
def match_flip_rate(history):
    h = np.asarray(history)
    if h.ndim != 2 or h.shape[0] < 2:
        per = np.zeros(h.shape[1] if h.ndim == 2 else 0)
        return per, 0.0
    per = (h[1:] != h[:-1]).mean(axis=0)
    return per, float(per.mean())"""),
    md("""---
## 🧪 真实工程胶囊：可直接放进项目的 HungarianMatcher + 匹配监控"""),
    code("""RECIPE = r'''
# ============================================================
# A. DETR 的 HungarianMatcher（PyTorch 版，可直接放进项目）
#    三处必须做对：① 分类项用**概率**不是 log ② no_grad ③ 逐图切分求解
# ============================================================
import torch
from scipy.optimize import linear_sum_assignment   # 生产用它；面试要能手写（见本 notebook）

class HungarianMatcher(torch.nn.Module):
    def __init__(self, w_cls=1.0, w_l1=5.0, w_giou=2.0):
        super().__init__()
        self.w_cls, self.w_l1, self.w_giou = w_cls, w_l1, w_giou

    @torch.no_grad()                                   # ② 匹配是离散 argmin，**不参与反传**
    def forward(self, outputs, targets):
        B, Q = outputs["pred_logits"].shape[:2]
        prob = outputs["pred_logits"].flatten(0, 1).softmax(-1)   # (B*Q, C)
        bbox = outputs["pred_boxes"].flatten(0, 1)                # (B*Q, 4) 归一化 cxcywh
        tgt_ids  = torch.cat([t["labels"] for t in targets])
        tgt_bbox = torch.cat([t["boxes"]  for t in targets])

        if tgt_ids.numel() == 0:                       # M=0 的空帧必须短路，否则 crash
            empty = torch.as_tensor([], dtype=torch.int64)
            return [(empty, empty) for _ in range(B)]

        cost_cls  = -prob[:, tgt_ids]                  # ① **概率**，不是 -log p
        cost_l1   = torch.cdist(bbox, tgt_bbox, p=1)
        cost_giou = -generalized_box_iou(box_cxcywh_to_xyxy(bbox),
                                         box_cxcywh_to_xyxy(tgt_bbox))
        C = self.w_cls * cost_cls + self.w_l1 * cost_l1 + self.w_giou * cost_giou
        C = C.view(B, Q, -1).cpu()                     # 求解在 CPU 上，矩阵极小，占比 < 1%

        sizes = [len(t["boxes"]) for t in targets]     # ③ 一个 batch 里每张图 M 不同，必须切分
        idx = [linear_sum_assignment(c[k]) for k, c in enumerate(C.split(sizes, -1))]
        return [(torch.as_tensor(i, dtype=torch.int64),
                 torch.as_tensor(j, dtype=torch.int64)) for i, j in idx]

# ============================================================
# B. 训练期必须挂的监控：匹配翻转率（本 notebook 的指标搬到线上）
# ============================================================
class MatchMonitor:
    # 按 image_id 记录「每个 GT 被哪个 query 认领」，逐 epoch 算翻转率
    def __init__(self):
        self.prev = {}
    def update(self, image_id, gt_ids, query_ids):
        cur = dict(zip(gt_ids, query_ids))
        old = self.prev.get(image_id)
        flips = None
        if old is not None:
            common = set(cur) & set(old)
            if common:
                flips = sum(cur[k] != old[k] for k in common) / len(common)
        self.prev[image_id] = cur
        return flips                                   # log 到 tensorboard: match/flip_rate

# 健康区间（经验值）：
#   epoch  0-10 : flip_rate 0.4-0.7  正常，模型还没学会
#   epoch 10-30 : 应当稳步下降到 < 0.2
#   epoch  30+  : 仍 > 0.3 -> **匹配没收敛**，上 DN-DETR 的去噪 query
#   dup_rate（每个 GT 被几个高分预测认领）应当在 epoch 20 前降到 ~1.0

# ============================================================
# C. 匹配相关的五类典型故障与排查方向
# ============================================================
FAULTS = [
  ("loss 正常但推理出大量重复框",
   "检查 decoder self-attention 是否被误关 —— 一对一只给动机，self-attn 才给能力"),
  ("某些 GT 从头到尾没有 query 认领",
   "N < 单图最大目标数。统计数据集单图目标数的 99.9 分位，N 取其 3-5 倍"),
  ("flip_rate 长期高位 + 收敛极慢",
   "匹配不稳定。上 DN/DINO 的去噪 query，或用定位质量加权分类分数(Stable-DINO)"),
  ("空帧 batch 直接 crash",
   "M=0 时代价矩阵是 Nx0，matcher 要短路返回空匹配"),
  ("匹配代价里误用 -log p",
   "训练早期匹配退化成按分数排序，框最准的 query 被判背景"),
]
for symptom, fix in FAULTS:
    print("症状:", symptom)
    print("  处理:", fix)
'''
print(RECIPE)
for token in ['HungarianMatcher', 'no_grad', '-prob[:, tgt_ids]', 'cdist',
              'generalized_box_iou', 'C.split(sizes, -1)', 'numel() == 0',
              'MatchMonitor', 'flip_rate', 'Stable-DINO']:
    assert token in RECIPE, token
print('✅ 胶囊覆盖：matcher 三处易错点 / 空帧保护 / 翻转率监控 / 五类故障排查')"""),
    md("""### 小结

- **匹配是「动态的标签分配」**。传统检测器用固定规则（IoU 阈值 / center sampling）回答
  「谁负责哪个 GT」，DETR 用一个**每 iteration 重算一次的最优化问题**来回答。
  面试被问「DETR 的标签分配是什么」，答「基于匈牙利算法的一对一动态分配」，不是「没有分配」。
- **线性指派问题三要素**：代价矩阵、一对一约束、总代价最小。去掉一对一 → 重复框回来；
  把「总代价最小」换成贪心 → 约 37% 的随机矩阵上次优（`[[1,2],[2,100]]` 上贪心差 25 倍）。
- **匈牙利算法是 O(n³) 不是 O(n!)**：n 个左点 × 每点最多 n 次对偶调整 × 每次扫描 n 列。
  本 notebook 手写版在 400 组随机矩阵（含负代价、1x1~6x6）上与暴力枚举**完全一致**，
  并且终止时的对偶变量 `(u, v)` 满足**互补松弛**——那是一份可独立验证的**最优性证书**。
- **代价三项**：`−p`（分类，用**概率**不是 log）+ `L1`（对小框友好）+ `−GIoU`（尺度不变、
  **不相交时仍有梯度**）。`−log p` 会以数量级优势主导匹配，实测让「框最准的 query 被判成背景」。
  **匹配用 −p、损失用 −log p**：匹配要公平比较所以要有界，损失要强力纠错所以要无界。
- **no-object 的代价是常数** → padding 到方阵只是叙述方便，`fill` 取 −1000 还是 +1000
  都不改变 argmin，工程上直接解矩形即可。但后果是：一个 query 被判背景**完全不由它自己的质量决定**。
- **一对一替代 NMS 的三句话**：重复框源于「多个预测被判为同一目标的正样本」→
  一对一从训练目标上禁止 → 落选者收 no-object 梯度、学会自我压制。
  玩具实验里一对多触发 6 个框（必须 NMS 才回到 2），一对一直接触发 2 个。
  **代价是监督密度掉一个数量级**——这就是 Group/H/Co-DETR 存在的理由。
- **匹配不稳定性是局部的**：代价差 0.70 的 GT 从不翻转，代价差 0.01 的翻转率 48%（饱和在 0.5）。
  受害 query 的**有效监督信号只有稳定 query 的 1/9**。
  **小目标 + 密集目标最严重，正是 TSR 的画像**——这是 DN-DETR / DINO / Stable-DINO 的直接动机。

下一站：**模块 02 · 集合预测损失** —— 匹配之后怎么算账，以及 no-object 权重为什么是生死线。"""),
]
