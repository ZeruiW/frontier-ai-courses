# -*- coding: utf-8 -*-
"""C57 模块 03 · 分配与损失层面的解法。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（IoU 位移敏感性）、模块 02（层级负载与格子数）；C53 m02（标签分配谱系）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_assignment_loss_small.ipynb'),
    ("核心参考", "NWD (Wang 2021) · RFLA (Xu, ECCV 2022) · ATSS (Zhang 2020) · GIoU/DIoU/CIoU/EIoU/SIoU · Focal Loss"),
    ("预计时长", "读 70 分钟 + 跑 65 分钟"),
]

SECTIONS = [
    ("scarcity", "先把问题钉死：IoU 这把尺子对小框本身就是坏的", "".join([
        P("模块 02 解决了「目标在特征图上有没有格子」，这一节要解决的是下一个问题：<strong>格子有了，但它能不能被判成正样本</strong>。这两件事经常被混为一谈，而它们的解法完全不同。"),
        P("回到模块 01 的核心事实：<strong>IoU 对绝对位移的敏感度反比于框的边长</strong>。对边长为 w 的方框，沿对角线每轴各位移 δ："),
        MATH("\\mathrm{IoU}(\\delta) \\;=\\; \\frac{(w-\\delta)^2}{2w^2-(w-\\delta)^2}, \\qquad \\left|\\frac{\\partial\\,\\mathrm{IoU}}{\\partial \\delta}\\right|_{\\delta=0} \\;=\\; \\frac{4}{w}"),
        TABLE(["每轴位移 δ", "IoU（8×8 框）", "IoU（64×64 框）", "NWD（8×8，C=12.8）", "NWD（64×64，C=12.8）"], [
            ["0 px", "1.000", "1.000", "1.000", "1.000"],
            ["1 px", "<strong>0.620</strong>", "0.940", "0.895", "0.895"],
            ["2 px", "<strong>0.391</strong>", "0.884", "0.802", "0.802"],
            ["4 px", "<strong>0.143</strong>", "0.784", "0.643", "0.643"],
            ["8 px", "<strong>0.000（死区）</strong>", "0.620", "0.413", "0.413"],
            ["位移灵敏度 |∂/∂δ|", "<strong>0.50 /px</strong>", "0.031 /px", "<strong>0.110 /px</strong>", "<strong>0.110 /px</strong>"],
        ]),
        P("最后一行是全模块的钥匙：<strong>IoU 的位移灵敏度是 4/w——对 8 px 的框比对 128 px 的框陡 16 倍；而 NWD 的灵敏度恒为 √2/C，与框的尺寸完全无关。</strong>"),
        H3("这个不公平的三个具体后果"),
        OL([
            "<strong>同一个阈值对不同尺度是完全不同的要求。</strong> 把 IoU ≥ τ 反解成「允许的位移半径」，得 <em>r = w(1−τ)/(1+τ)</em>——<strong>半径正比于框的边长</strong>。τ = 0.5 时，8 px 的框只允许位移 2.67 px，而 128 px 的框允许 42.7 px。",
            "<strong>而网格量化本身就带来 4 px 的误差。</strong> 在 stride 8 的特征图上，格子中心间隔 8 px，GT 中心到最近格子中心的偏移在每轴上最大 4 px。<em>2.67 px 的容忍半径小于 4 px 的固有误差</em>——这是一个<strong>结构性的不匹配</strong>，不是调参能解决的。notebook 会算出：即使 anchor 尺寸完美匹配，<strong>也只有约 25% 的 8 px 目标能在 stride 8 网格上找到 IoU ≥ 0.5 的 anchor</strong>（16 px 时是 85%，32 px 时是 100%）。",
            "<strong>不相交时 IoU 恒为 0，梯度也恒为 0。</strong> 对 8 px 的框，只要位移超过 8 px（在 stride 8 上就是一个格子）就进入死区。<em>死区里所有的「错得多远」信息全部丢失</em>——错 9 px 和错 90 px 在 IoU 眼里一模一样。",
        ]),
        DUAL(
            "所以「小目标正样本少」不是一个统计现象，是<strong>度量本身的性质导致的必然结果</strong>。很多工程实践里的第一反应是「把 IoU 阈值从 0.5 降到 0.3」——这有用，但它只是把不公平从一个点挪到另一个点：<em>τ = 0.3 时 8 px 框的容忍半径是 4.3 px，勉强够；而 128 px 框的容忍半径变成 69 px，等于把一大批明显错的框也收成了正样本</em>。<strong>单一阈值下，无论取什么值，总有一头是错的。</strong>",
            "更精确地说：<strong>IoU 是一个「相对」度量——它衡量的是位移相对于框尺寸的比例</strong>。这在目标尺寸跨度不大时是优点（尺度不变），在目标尺寸跨越 4–200 px 时就是灾难。而小目标真正需要的是一个<em>「绝对」度量</em>——因为对小目标构成威胁的误差（网格量化 ±4 px、标注抖动 ±2 px、亚像素回归精度）<strong>都是绝对像素量，与目标尺寸无关</strong>。<em>用相对度量去衡量绝对误差，就是整个问题的根源。</em> 这直接指向了解法：换一个位置项是绝对距离的度量——<strong>这就是 NWD。</strong>",
        ),
        CALLOUT("intuition", "把三层解法的关系先摆清楚，后面就不会乱：<strong>① 改分配（谁是正样本）→ ② 换度量（用什么尺子判）→ ③ 调损失（正样本怎么加权）</strong>。三者独立且可叠加，但<em>优先级是从上往下的</em>——如果度量本身是坏的，再精巧的损失加权也只是在错误的正样本集合上优化。<strong>面试里如果只答「加大小目标的损失权重」，那是从第三层入手，会被追问到底。</strong>"),
    ])),

    ("nwd", "NWD：把框建模成 2D 高斯，用 Wasserstein 距离量相似度", "".join([
        P("<span class=\"term\">NWD（Normalized Wasserstein Distance）</span>的构造分三步，每一步都可以在纸上验算。"),
        H3("第一步：bbox → 2D 高斯"),
        P("一个框 (c_x, c_y, w, h) 里的目标并不是均匀铺满整个矩形的——中心的像素属于目标，四角往往是背景。用一个<strong>内切椭圆</strong>去近似目标的实际占据区域更合理，而椭圆恰好是二维高斯的等密度线："),
        MATH("\\mathcal{N}_b \\;=\\; \\mathcal{N}\\!\\left(\\boldsymbol\\mu = \\begin{bmatrix} c_x \\\\ c_y\\end{bmatrix},\\; \\boldsymbol\\Sigma = \\begin{bmatrix} \\frac{w^2}{4} & 0 \\\\[2pt] 0 & \\frac{h^2}{4}\\end{bmatrix}\\right)"),
        ASCII("""bbox -> 2D 高斯：把框的内切椭圆当作高斯的 1-sigma 等密度线

     (cx-w/2, cy-h/2)
        ┌──────────────────────────┐        Sigma^{1/2} = diag(w/2, h/2)
        │        ╭────────╮        │        <=> 沿 x 轴 sigma_x = w/2
        │     ╭──╯        ╰──╮     │            沿 y 轴 sigma_y = h/2
        │    ╱   ●(cx,cy)    ╲     │  h
        │     ╰──╮        ╭──╯     │        四角是背景 -> 高斯自然衰减
        │        ╰────────╯        │        中心是目标 -> 高斯密度最高
        └──────────────────────────┘
                     w                       **注意 Sigma 是对角阵**：
                                             轴对齐框没有 xy 相关性。
                                             旋转框才需要非对角 Sigma。""")
        ,
        H3("第二步：两个高斯之间的 2-Wasserstein 距离"),
        P("对两个高斯分布，二阶 Wasserstein 距离有闭式解。把它写出来，代入对角协方差之后<strong>会退化成一个极其简单的形式</strong>："),
        MATH("W_2^2(\\mathcal{N}_a, \\mathcal{N}_b) \\;=\\; \\|\\boldsymbol\\mu_a - \\boldsymbol\\mu_b\\|_2^2 \\;+\\; \\left\\|\\boldsymbol\\Sigma_a^{1/2} - \\boldsymbol\\Sigma_b^{1/2}\\right\\|_F^2"),
        MATH("=\\; (c_{x_a}-c_{x_b})^2 + (c_{y_a}-c_{y_b})^2 + \\left(\\frac{w_a-w_b}{2}\\right)^{\\!2} + \\left(\\frac{h_a-h_b}{2}\\right)^{\\!2}"),
        P("换句话说，<strong>W₂² 就是把框写成四维向量 [c_x, c_y, w/2, h/2] 之后的欧氏距离平方</strong>。实现只需要一行。但这个简洁形式背后有真正的意义：<em>位置项和尺寸项被放在同一个度量空间里，且都是绝对像素量</em>。"),
        H3("第三步：归一化成 (0, 1] 的相似度"),
        P("W₂ 是一个距离（越小越像），量纲是像素，取值无上界——不能直接当 IoU 用。NWD 用一个指数把它映射到相似度："),
        MATH("\\mathrm{NWD}(\\mathcal{N}_a, \\mathcal{N}_b) \\;=\\; \\exp\\!\\left(-\\frac{\\sqrt{W_2^2(\\mathcal{N}_a, \\mathcal{N}_b)}}{C}\\right) \\;\\in\\; (0, 1]"),
        TABLE(["符号", "含义", "取值", "怎么定"], [
            ["<strong>C</strong>", "<strong>NWD 唯一的超参</strong>：把「像素距离」换算成「相似度」的尺度常数", "AI-TOD 上用 12.8", "<strong>取数据集目标的平均绝对尺寸</strong>（√(wh) 的均值）"],
            ["<strong>W₂</strong>", "两个高斯的 2-Wasserstein 距离，单位是像素", "[0, ∞)", "闭式解，无需迭代"],
            ["<strong>NWD</strong>", "相似度，可直接替换 IoU 用于分配 / NMS / 损失", "(0, 1]，= 1 当且仅当两框完全相同", "τ 与 C 联动，见下节"],
        ]),
        DUAL(
            "所以 NWD 的实现只有三行：<em>把两个框各写成 [c_x, c_y, w/2, h/2]，算欧氏距离，取 exp(−d/C)</em>。它比 IoU 还简单（不需要求交集），也<strong>处处可导</strong>（IoU 在框刚好相切时不可导，在不相交时梯度为 0）。作为一把「尺子」，它可以原样替换掉分配器里的 IoU、NMS 里的 IoU、以及回归损失里的 IoU（用 L = 1 − NWD）。",
            "要注意 NWD 用的是 <strong>W₂ 而不是 KL 散度</strong>，这个选择是有讲究的。<em>KL 散度在两个分布不重叠时会发散到无穷</em>（它衡量的是「用一个分布编码另一个分布的代价」），而 Wasserstein 距离衡量的是「把一堆土从一个分布搬成另一个分布需要多少功」——<strong>即使两个分布完全不重叠，这个功也是有限且连续变化的</strong>。这正是 WGAN 当年选择 Wasserstein 而不是 JS 散度的同一个理由。<em>对小目标检测，「不重叠时仍有有意义的度量」恰恰是最需要的性质。</em>",
        ),
        CALLOUT("warn", "一个必须澄清的常见误读：<strong>NWD 里的高斯不是「不确定性建模」</strong>。它不是在说「这个框的位置有多不确定」，而是<em>纯粹把矩形换成一个更平滑的、有解析距离的等价表示</em>。σ = w/2 是硬性规定的（框的半宽），不是学出来的、也不是估计出来的。<em>把 NWD 和「概率化检测 / 不确定性估计」混为一谈是面试里常见的答错点。</em>"),
    ])),

    ("nwd_props", "NWD 的三个关键性质：为什么它恰好补上了 IoU 的短板", "".join([
        P("公式写出来只是第一步。真正要说清楚的是<strong>它到底解决了前面列的哪几条</strong>——以下三条都可以在 notebook 里 assert。"),
        H3("性质一：对「相同绝对位移」给出相同的相似度，与框的大小无关"),
        P("如果两个框尺寸相同、只有位置不同，那么 Σ 项完全抵消，W₂ = ‖Δμ‖。于是"),
        MATH("\\mathrm{NWD} \\;=\\; \\exp\\!\\left(-\\frac{\\|\\Delta\\boldsymbol\\mu\\|}{C}\\right), \\qquad \\left|\\frac{\\partial\\,\\mathrm{NWD}}{\\partial \\|\\Delta\\boldsymbol\\mu\\|}\\right|_{0} = \\frac{1}{C} \\;\\;(\\text{与 } w \\text{ 无关})"),
        P("对照 IoU 的 4/w：<strong>8 px 的框和 64 px 的框位移 2 px，IoU 分别是 0.391 和 0.884（差 2.3 倍），NWD 都是 0.802（完全相同）</strong>。这是可以精确 assert 的等式，不是近似。"),
        P("把它翻译成分配阈值下的「正样本容忍半径」，对比更直观："),
        MATH("r_{\\mathrm{IoU}}(\\tau, w) \\;=\\; w\\cdot\\frac{1-\\tau}{1+\\tau} \\;\\;(\\propto w), \\qquad r_{\\mathrm{NWD}}(\\tau, C) \\;=\\; -\\,C\\ln\\tau \\;\\;(\\text{常数})"),
        TABLE(["框边长 w", "r（IoU@0.5）", "r（IoU@0.3）", "r（NWD@0.5, C=12.8）", "stride 8 网格的固有量化误差"], [
            ["<strong>4 px</strong>", "1.33 px", "2.15 px", "<strong>8.87 px</strong>", "最大 4 px / 轴"],
            ["<strong>8 px</strong>", "<strong>2.67 px ❌</strong>", "4.31 px", "<strong>8.87 px ✅</strong>", "最大 4 px / 轴"],
            ["<strong>16 px</strong>", "5.33 px", "8.62 px", "<strong>8.87 px</strong>", "最大 4 px / 轴"],
            ["<strong>64 px</strong>", "21.3 px", "34.5 px ⚠️", "<strong>8.87 px</strong>", "最大 4 px / 轴"],
            ["<strong>256 px</strong>", "85.3 px", "138 px ⚠️⚠️", "<strong>8.87 px</strong>", "最大 4 px / 轴"],
        ]),
        P("这张表把「降低 IoU 阈值」这个常见做法的问题暴露得很清楚：<strong>把 τ 从 0.5 降到 0.3，确实把 8 px 框的容忍半径从 2.67 提到 4.31（够用了），但同时把 256 px 框的容忍半径从 85 提到了 138 px</strong>——那是把中心偏了半个框的预测也收成正样本。<em>NWD 则在所有尺度上给出同一个 8.87 px 的半径，这个半径由 C 和 τ 共同决定，可以按「网格量化误差 + 标注抖动」直接设计。</em>"),
        H3("性质二：不相交时仍有非零梯度，而且惩罚「放大预测框」"),
        P("IoU 在不相交时恒为 0，梯度也恒为 0——这是一个<strong>平台（plateau）</strong>，优化完全停滞。GIoU 用「最小外接框的空洞比例」补上梯度，但它有一个著名的病态：<em>在不相交时，让预测框变大可以缩小空洞比例，于是 GIoU 的梯度主要在推动「把框放大」</em>。notebook 里可以算出来：一个 8×8 的 GT，预测框中心偏 30 px 时，<strong>预测框从 8×8 放大到 40×40，GIoU 从 −0.911 涨到 −0.429（「变好了」），而 IoU 全程为 0</strong>。对小目标，这直接产生系统性偏大的框。"),
        P("NWD 没有这个问题，因为 Σ 项<strong>显式地惩罚尺寸不匹配</strong>：同样的场景下，预测框从 8×8 放大到 40×40，W₂² 从 1800 涨到 2312，NWD 从 0.0363 <strong>降到</strong> 0.0234。<em>GIoU 奖励放大，NWD 惩罚放大——方向相反。</em>"),
        H3("性质三：处处光滑，且等值面是正圆"),
        P("NWD 是 exp 复合欧氏距离，<strong>C^∞ 光滑</strong>，没有 IoU 在相切处的折点、也没有死区。此外，因为它只依赖 ‖Δμ‖，<strong>它的等值面是标准圆</strong>；而 IoU 的等值面是各向异性的（沿轴移动和沿对角移动的容忍度不同——对同一个 8 px 框，τ=0.5 时沿轴能容忍 2.67 px，沿对角每轴只能容忍 1.47 px）。<em>各向异性意味着同一个目标落在格子的不同相对位置上，被匹配的概率不同——这是一种没人想要的随机性。</em>"),
        CALLOUT("danger", "<p><strong>但 NWD 不是免费的，它有一个必须知道的代价：对大目标的区分度不足。</strong></p><p>因为位置项是绝对距离，<em>一个 3 px 的偏移在 10 px 的框上和在 300 px 的框上被同等对待</em>——而后者显然是好得多的定位。结果是：<strong>纯 NWD 训练会让大目标的定位精度下降</strong>（AP@0.75 尤其明显）。</p><p>工程上的标准做法有两种：<strong>① 混合</strong>——<code>metric = (1−α)·IoU + α·NWD</code>，α 按数据集的小目标占比设（TSR 上 α 取 0.5–0.8 合理）；<strong>② 按尺寸切换</strong>——小于某个阈值（如 √(wh) &lt; 32 px）的 GT 用 NWD 分配，其余用 IoU。<em>NWD 原论文在 AI-TOD（几乎全是极小目标）上用纯 NWD，那是因为那个数据集没有大目标。直接照搬到有大目标的场景会掉点</em>——<strong>这正是面试里区分「读过论文」和「用过方法」的地方。</strong></p>", "纯 NWD 会伤大目标"),
        CALLOUT("warn", "C 的取值不是随便定的，它<strong>决定了 NWD 的有效作用范围</strong>。因为 NWD = exp(−d/C)，当 d ≫ C 时它指数衰减到 0，梯度也随之消失。<em>C 太小 → 稍远一点就没有梯度，退化成 IoU 的死区；C 太大 → 远处的错误框也拿到高分，正样本质量下降。</em> <strong>经验规则：C ≈ 数据集目标 √(wh) 的均值</strong>（AI-TOD 上是 12.8）。在 TSR 上，如果尺寸中位数是 14 px，C 取 12–16 是合理起点，然后配合 τ 用「r = −C ln τ 应当略大于网格量化误差 + 标注抖动」来验算。"),
    ])),

    ("center", "解法一·A：center-based 分配与尺度自适应阈值", "".join([
        P("换度量之外，另一条独立的路是<strong>改变「谁有资格当正样本」的规则</strong>。这条路更早、更简单，而且和 NWD 完全可以叠加。"),
        H3("center-based：从「框和框比」到「点在不在框里」"),
        P("<span class=\"term\">FCOS</span> 式的 anchor-free 分配把问题换了个提法：不再问「这个 anchor 和 GT 的 IoU 够不够」，而是问「<strong>这个特征点的中心落没落在 GT 框里</strong>」。这对小目标有一个直接的好处——<em>它绕开了 IoU 阈值，也绕开了 anchor 尺寸是否匹配的问题</em>。"),
        P("但它有自己的天花板，而且是模块 02 算过的那个：<strong>对边长 L 的框，每轴上落入至少一个格子中心的概率是 min(1, L/stride)</strong>，二维需要两轴同时满足，于是"),
        MATH("P(\\text{一个正样本都没有}) \\;=\\; 1 - \\min\\!\\left(1, \\frac{L}{s}\\right)^{\\!2}"),
        P("在 stride 8 上：<strong>4 px 的目标有 75% 的概率一个中心点都落不进去，6 px 的目标是 44%</strong>。center-based 不能解决这个，只有更高分辨率（P2）能。<em>这就是为什么模块 02 必须排在前面。</em>"),
        P("实践中还会加两个修正："),
        UL([
            "<strong>center sampling</strong>：只把「距 GT 中心 &lt; r·stride」的点算正样本（YOLOX / FCOS 改进版用 r = 1.5 或 2.5），避免框边缘的点被当正样本——那些点的特征其实是背景。<em>对小目标要注意：r·stride 可能已经大于目标本身，此时必须再和「点在框内」求交</em>，否则会把背景点收进来。",
            "<strong>centerness / IoU-aware 分支</strong>：给每个正样本打一个「离中心多近」的软标签，推理时乘到分类分数上，压制边缘点产生的低质量框。<em>对小目标，centerness 的取值范围被压缩（框太小，中心和边缘差不了几个像素），这个分支的作用会减弱。</em>",
        ]),
        H3("尺度自适应阈值：让「容忍半径」在所有尺度上恒定"),
        P("如果不想换度量，还有一个更保守的改法：<strong>让 IoU 阈值随目标尺寸变化</strong>。关键是别拍脑袋定阈值表，而是<em>反解出来</em>——要求容忍半径恒为 r₀，直接从 r = w(1−τ)/(1+τ) 解出："),
        MATH("\\tau(w) \\;=\\; \\mathrm{clip}\\!\\left(\\frac{w-r_0}{w+r_0},\\; \\tau_{\\min},\\; \\tau_{\\max}\\right)"),
        TABLE(["框边长 w", "τ(w)（r₀ = 4 px）", "反算的容忍半径", "对比：固定 τ=0.5 的半径"], [
            ["8 px", "<strong>0.333</strong>", "4.0 px ✅", "2.67 px ❌"],
            ["16 px", "0.600", "4.0 px ✅", "5.33 px"],
            ["32 px", "0.778", "4.0 px ✅", "10.7 px"],
            ["64 px", "0.882", "4.0 px ✅", "21.3 px"],
            ["256 px", "0.969 → clip 0.90", "13.5 px", "85.3 px ⚠️"],
        ]),
        DUAL(
            "这个式子的好处是它<strong>不是经验表，而是从一个明确的设计目标反解出来的</strong>：「我希望在所有尺度上，容忍的定位误差都是 r₀ 像素」。r₀ 该取多少也不是猜的——<em>它应该覆盖「网格量化误差（stride/2）+ 标注抖动（±1–2 px）+ 亚像素回归的固有精度」</em>。stride 8 时 r₀ = 4–6 px 是合理区间。",
            "而一旦这么写出来，就会发现一件事：<strong>「尺度自适应的 IoU 阈值」和「固定阈值的 NWD」在做的是同一件事——让容忍半径与尺度解耦</strong>。NWD 的 r = −C ln τ 天然就是常数，而尺度自适应阈值是用一个补偿函数把 IoU 掰成常数半径。<em>两者的区别在于：NWD 在整个度量上都是绝对的（包括不相交的情形和梯度），而尺度自适应阈值只在「判正负」这一个点上做了补偿，回归损失里的 IoU 该多陡还是多陡。</em> <strong>所以如果只能改一处，改度量比改阈值更彻底。</strong>",
        ),
        CALLOUT("intuition", "把这一节浓缩成一句：<strong>所有对小目标友好的分配策略，本质上都在做同一件事——把「相对误差」的判据换成「绝对误差」的判据</strong>。center-based 用「点在不在框里」（绝对），尺度自适应阈值用补偿函数（把相对掰成绝对），NWD 直接用绝对距离。<em>认出这个共同点，就不用记三套方法，只需要记一条原则。</em>"),
    ])),

    ("adaptive", "解法一·B：ATSS 与 SimOTA 的自适应性，以及它们在小目标上的意外表现", "".join([
        P("动态分配（ATSS / OTA / SimOTA / TaskAligned，详见 C53 m02）常被说成「天然对小目标更公平」。这句话<strong>一半对，一半是错的</strong>，值得逐条拆开。"),
        H3("ATSS：阈值从数据里长出来，确实更公平"),
        P("<span class=\"term\">ATSS</span> 的规则是：对每个 GT，在每个金字塔层各选 k=9 个中心最近的候选 anchor，算它们与 GT 的 IoU，然后把<strong>阈值定成这些 IoU 的 均值 + 标准差</strong>，超过阈值且中心在框内的成为正样本。"),
        P("<strong>为什么这对小目标更公平：</strong> 阈值是从候选集里算出来的。小目标的所有候选 IoU 都低（比如 0.02–0.08），阈值也就自动变低（0.05 左右），于是仍能选出正样本——<em>而固定 0.5 的阈值会一个都选不出来</em>。"),
        CALLOUT("warn", "<strong>但 ATSS 在极小目标上会退化。</strong> 均值+标准差这个设计的原意是：标准差大 = 该 GT 在某一层上明显更合适 → 抬高阈值只留那一层；标准差小 = 各层差不多 → 阈值接近均值。<em>对极小目标，所有候选的 IoU 都挤在 0 附近，标准差趋近于 0</em>，于是阈值 ≈ 均值 ≈ 0.03，<strong>结果是 top-9 候选几乎全部被收成正样本，而它们的 IoU 全都低于 0.1</strong>。<em>正样本数量有了，质量没有</em>——模型被要求从一堆几乎不含目标的 anchor 上回归出准确的框。<strong>解法：把 ATSS 里的 IoU 换成 NWD，两个机制叠加。</strong>"),
        H3("SimOTA 的 dynamic-k：对小目标的作用方向是反的"),
        P("<span class=\"term\">SimOTA</span> 的动态 k 规则是：取每个 GT 的 top-q（q=10）个候选的 IoU，<strong>把它们求和再取整，作为该 GT 应分配的正样本个数</strong> k_i = max(1, round(Σ IoU))。这个设计的直觉是「和 GT 匹配得好的候选多，就多给几个正样本」。"),
        P("<strong>但把它套到小目标上，方向恰好是反的。</strong> 小目标的所有候选 IoU 都低，求和自然小，于是 k 被压到 1–2；而大目标的候选 IoU 高，k 可以到 7–10。<em>结果是：本来正样本就稀缺的小目标，被 dynamic-k 又砍了一刀。</em>"),
        TABLE(["GT 尺寸", "top-10 候选 IoU 之和", "k（IoU 版）", "top-10 候选 NWD 之和", "k（纯 NWD 版）", "k（混合 α=0.7）"], [
            ["<strong>8 px</strong>", "2.06", "<strong>2</strong> ❌", "5.53", "<strong>6</strong> ✅", "<strong>4</strong> ✅"],
            ["32 px", "4.74", "5", "4.92", "5", "5"],
            ["<strong>128 px</strong>", "4.74", "<strong>5</strong> ✅", "0.83", "<strong>1</strong> ❌", "<strong>2</strong>"],
        ]),
        P("最后一行同样重要，而且它是本课「必须混合」这条建议的直接证据：<strong>纯 NWD 版把 128 px 目标的 k 从 5 砍到了 1</strong>——因为位置项是绝对距离，一个大目标的候选中心偏十几像素就被 NWD 判成「很远」。<em>不公平只是被倒向了另一头。</em> 换成 <code>0.3·IoU + 0.7·NWD</code> 的混合度量后是 <strong>4 / 5 / 2</strong>：小目标的 k 被拉起来（2 → 4），大目标不至于塌到 1。<em>α 越大越偏袒小目标——它是一个可以按数据分布调的旋钮，而不是一个常数。</em>"),
        P("<strong>所以修法有三条，可以叠加：</strong> ① 把 dynamic-k 里的 IoU 换成 <strong>IoU 与 NWD 的混合</strong>；② 给 k 设一个下界（如 k ≥ 3）；③ 按尺寸切换度量。<em>第二条最粗暴但最好调试，第一条最一致。</em>"),
        DUAL(
            "这一节的价值不在于「ATSS/SimOTA 好不好」，而在于一个更一般的判断力：<strong>任何以 IoU 为内部度量的自适应机制，都会把 IoU 的尺度不公平继承下来，而且往往被自适应性放大</strong>。ATSS 的均值+标准差、SimOTA 的 dynamic-k、TaskAligned 的 t = s^α·u^β（u 就是 IoU）——<em>它们都在「自适应」，但适应的是一把对小框有系统性偏见的尺子。</em>",
            "所以正确的做法不是「在 ATSS 和 NWD 之间二选一」，而是<strong>把 NWD 装进 ATSS / SimOTA / TaskAligned 的内部</strong>。这是一个几乎零成本的改动（换一个函数调用），却把两条独立的改进叠加了起来：<em>自适应性负责「不同 GT 该拿多少正样本」，NWD 负责「候选好不好这件事怎么量」</em>。<strong>面试里能说出这个组合关系，比背出任何单个方法的公式都有价值——因为它说明你理解了这些方法各自在解决哪一层的问题。</strong>",
        ),
    ])),

    ("rfla", "RFLA：把「感受野」而不是「anchor」当作先验", "".join([
        P("<span class=\"term\">RFLA（Receptive Field based Label Assignment）</span>是另一条思路，它质疑的是一个更底层的假设：<strong>为什么要拿「anchor 框」或「格子中心点」去和 GT 比？真正接收信息的是那个特征点的感受野。</strong>"),
        H3("三个组成部分"),
        OL([
            "<strong>把有效感受野建模成高斯。</strong> 理论感受野（TRF）是一个方块，但<span class=\"term\">有效感受野（ERF）</span>——真正对输出有显著贡献的区域——近似一个<em>以特征点为中心的二维高斯</em>，且远小于 TRF（典型只有 TRF 面积的几分之一，见 C53 m03 的数值实验）。RFLA 于是给每个特征点配一个高斯 N(μ_点, σ²_ERF·I)，σ_ERF 由该层的感受野决定。",
            "<strong>用 KLD 度量「感受野高斯」与「GT 高斯」的匹配度</strong>，代替 IoU。",
            "<strong>HLA（Hierarchical Label Assignment）分层分配</strong>：先按 KLD 排序取 top-k；对没拿够 k 个的 GT，逐级放宽条件再补；<em>保证每个 GT 至少有 k 个正样本</em>。",
        ]),
        MATH("D_{\\mathrm{KL}}(\\mathcal{N}_g \\,\\|\\, \\mathcal{N}_e) = \\frac12\\left[\\mathrm{tr}(\\boldsymbol\\Sigma_e^{-1}\\boldsymbol\\Sigma_g) + (\\boldsymbol\\mu_e - \\boldsymbol\\mu_g)^{\\!\\top}\\boldsymbol\\Sigma_e^{-1}(\\boldsymbol\\mu_e - \\boldsymbol\\mu_g) - 2 + \\ln\\frac{|\\boldsymbol\\Sigma_e|}{|\\boldsymbol\\Sigma_g|}\\right]"),
        H3("一个必须搞清楚的细节：KLD 的方向决定了公平性"),
        P("KLD 是<strong>非对称</strong>的，而这里的不对称性恰恰是关键。看中间那个位置项——它是<span class=\"term\">马氏距离（Mahalanobis distance）</span>，<strong>用「参考分布」的协方差做归一化</strong>："),
        TABLE(["方向", "位置项", "对固定 2 px 偏移的行为", "对小目标是否公平"], [
            ["<strong>D_KL(GT ‖ 预测框)</strong>", "Δᵀ Σ_pred⁻¹ Δ，用预测框尺寸归一化", "∝ 1/w²：8 px 框的惩罚是 64 px 框的 <strong>64 倍</strong>", "❌ <strong>比 IoU 还不公平</strong>"],
            ["<strong>D_KL(GT ‖ ERF)</strong>（RFLA 用的）", "Δᵀ Σ_ERF⁻¹ Δ，用<strong>感受野</strong>尺寸归一化", "σ_ERF 由层决定、与 GT 尺寸无关 → <strong>惩罚恒定</strong>", "✅ 与 NWD 同类"],
            ["<strong>W₂（NWD 用的）</strong>", "‖Δ‖²，纯绝对距离", "恒定", "✅"],
        ]),
        CALLOUT("intuition", "所以 <strong>RFLA 的公平性不来自 KLD，而来自「拿感受野当参考分布」这个选择</strong>——因为感受野的尺度由<em>网络层</em>决定，与目标大小无关，于是位置项自动变成了「绝对距离除以一个固定尺度」。<em>如果有人告诉你「KLD 比 IoU 对小目标更公平」，那是没说全：方向搞反了会更不公平。</em> <strong>这是一个很好的面试追问点——它检验你是不是真的把公式展开算过。</strong>"),
        P("RFLA 相比 NWD 的取舍："),
        TABLE(["", "NWD", "RFLA"], [
            ["核心先验", "GT 框本身的高斯化", "<strong>特征点的有效感受野</strong>"],
            ["度量", "W₂（对称、绝对距离）", "KLD（非对称、按 ERF 归一化）"],
            ["超参", "<strong>只有 C</strong>", "σ_ERF（需按层估计）+ HLA 的 k + 放宽策略"],
            ["能否直接当损失", "✅ L = 1 − NWD，处处可导", "⚠️ 主要用于分配；当损失需额外归一化"],
            ["「每个 GT 至少 k 个正样本」保证", "❌ 需自己加保底逻辑", "<strong>✅ HLA 内建</strong>"],
            ["实现复杂度", "<strong>三行</strong>", "中等（要估 ERF、要写分层逻辑）"],
            ["工程建议", "<strong>先上这个</strong>（改动最小、收益确定）", "已有 NWD 后再叠加 HLA 的保底逻辑"],
        ]),
        DUAL(
            "实践上最划算的组合往往不是「选 NWD 还是选 RFLA」，而是<strong>取 NWD 的度量 + 取 RFLA 的「保底 k」思想</strong>：用 NWD 判正负，同时保证每个 GT 至少拿到 k 个正样本（不够就取 NWD 最大的前 k 个）。这两行代码解决了「某些极端小或极端偏的 GT 完全没有监督」的问题。",
            "「保底 k」为什么重要，值得算一笔账：在 TSR 的尺寸分布下，即使加了 P2，<em>仍有一小部分 GT（极小 + 恰好落在格子边界）拿不到任何正样本</em>。这些 GT 对损失的贡献是 0——<strong>它们不是「学得差」，而是「完全没被学」</strong>。更隐蔽的是，它们所在的位置会被当成<em>负样本</em>去训练，<strong>模型被主动教育「这里没有目标」</strong>。<em>这比单纯漏掉它们更糟。</em> 保底 k 把这种「负向监督」变成了正向监督。",
        ),
    ])),

    ("iou_family", "IoU 变体家族：GIoU / DIoU / CIoU / EIoU / SIoU 在小框上的真实差异", "".join([
        P("分配之外，<strong>回归损失</strong>用哪个 IoU 变体也是个真问题。这几个变体的关系经常被讲成一串「后一个比前一个好」的故事，但在小目标上它们的差异是具体且可验算的。"),
        TABLE(["度量", "在 IoU 之上加的惩罚项", "不相交时", "在小框上的具体问题", "TSR 建议"], [
            ["<strong>IoU</strong>", "—", "<strong>恒为 0，梯度为 0</strong>", "8 px 框位移 8 px 就进死区", "❌ 单用不行"],
            ["<strong>GIoU</strong>", "外接框空洞比 <code>|C\\(A∪B)|/|C|</code>", "∈ [−1, 0)，有梯度", "<strong>梯度主要在推「把预测框放大」</strong> → 小目标框系统性偏大", "⚠️ 有更好的选择"],
            ["<strong>DIoU</strong>", "中心距离 <code>ρ²/c²</code>", "有梯度，且直接拉中心", "对小目标是<strong>正确的方向</strong>（小目标的主要误差就是中心偏）", "✅ 可用"],
            ["<strong>CIoU</strong>", "DIoU + 长宽比项 <code>αv</code>", "同 DIoU", "<strong>①</strong> ∂v/∂w ∝ 1/w，小框上梯度大 25×（官方实现把 1/(w²+h²) 直接删掉了）<br><strong>②</strong> 长宽比一致时 v ≡ 0，<em>即使预测框大 5 倍也不惩罚</em>", "⚠️ 需用修正版"],
            ["<strong>EIoU</strong>", "DIoU + 分别惩罚 <code>(w−w_g)²/c_w²</code> 与 <code>(h−h_g)²/c_h²</code>", "同 DIoU", "修掉了 CIoU 的两个毛病：不再有 1/(w²+h²)，也不再有「比例对了就不管」的退化", "<strong>✅ 推荐</strong>"],
            ["<strong>SIoU</strong>", "角度代价 + 距离代价 + 形状代价", "有梯度", "角度项要求中心偏移有明确方向；<em>亚像素级偏移时角度基本是噪声</em>", "⚠️ 收益不稳定，超参多"],
        ]),
        H3("三个可以验算的具体事实"),
        OL([
            "<strong>GIoU 奖励放大，NWD 惩罚放大。</strong> 8×8 的 GT，预测框中心偏 30 px：预测框从 8×8 放大到 40×40，<em>GIoU 从 −0.911 涨到 −0.429</em>（优化器会朝这个方向走），而 <em>NWD 从 0.0363 降到 0.0234</em>。前者产生偏大的框，后者不会。",
            "<strong>CIoU 的长宽比项在小框上梯度大一个量级。</strong> ∂v/∂w = −(8/π²)·(arctan(w_g/h_g) − arctan(w/h))·h/(w²+h²)，对方形框这个因子是 1/(2w)，<em>正比于 1/w</em>。8 px 与 200 px 相差 <strong>25 倍</strong>。而在归一化坐标下（除以图宽 1920），8 px 对应的因子是 120——<strong>这就是 CIoU 原文说「w²+h² 在归一化坐标下很小，容易梯度爆炸，所以我们的实现里直接把这个分母去掉了」的由来</strong>。<em>如果你用的框架没做这个处理，小目标上会出现莫名其妙的训练不稳。</em>",
            "<strong>CIoU 的长宽比项会完全失效。</strong> 预测框 40×40、GT 8×8、中心重合：长宽比相同 ⇒ v = 0，中心距离为 0 ⇒ DIoU 项也为 0，于是 <em>CIoU = IoU = 0.04</em>，惩罚全部来自 IoU 本身。而 EIoU 的宽高项给出 <em>−1.24</em>——<strong>差了一个半量级的信号</strong>。这正是 EIoU 存在的理由。",
        ]),
        H3("回归损失的组合建议"),
        P("单一 IoU 类损失在小目标上都偏弱，需要和 L1 类损失配合。但这里有一个<strong>容易被忽略的陷阱</strong>："),
        CALLOUT("danger", "<p><strong>归一化坐标下的 L1 损失会系统性地低估小目标的误差。</strong> 假设图宽 1920：一个 8 px 的框宽度错了 50%（4 px），归一化 L1 = 4/1920 = <strong>0.00208</strong>；一个 200 px 的框宽度错了 10%（20 px），归一化 L1 = 20/1920 = <strong>0.0104</strong>。<em>客观上明显更差的那个预测，损失只有另一个的五分之一。</em></p><p>这解释了一个常见困惑：「我用了 L1 + GIoU 的标准组合，小目标还是不准」——<strong>因为 L1 项在归一化坐标下把小目标的权重压掉了，而 GIoU 项对小目标本来就陡峭到近乎噪声</strong>。<em>三种修法：① 把 L1 换成按框尺寸归一化的相对误差；② 加 scale-aware 权重（下一节）；③ 直接用 L = 1 − NWD 作为回归损失——它的位置项是绝对像素距离，天然没有这个问题。</em></p>", "L1 在归一化坐标下对小目标是打折的"),
        DUAL(
            "所以给 TSR 的一套具体推荐是：<strong>分配用 NWD（或 IoU/NWD 混合），回归损失用 <code>L = 1 − NWD</code> 或 <code>EIoU + 尺度归一化的 L1</code>，避开纯 GIoU 和未修正的 CIoU</strong>。这不是「哪个最新用哪个」，而是逐条对应到上面验算出来的问题。",
            "还有一个常被忽略的地方：<strong>NMS 里的 IoU 同样有这个不公平</strong>。两个 8 px 的框中心相距 5 px，IoU 只有 <strong>0.23</strong>，在任何常用阈值（0.5–0.65）下都会被当成两个不同目标全部保留——<em>于是小目标区域出现大量重复框</em>；而两个 200 px 的框中心同样相距 5 px，IoU 高达 <strong>0.95</strong>，会被正确合并。<em>NWD 对这两种情形给出的都是 0.677——同样的绝对偏移，同样的判断。</em> <strong>把 NMS 的 IoU 也换成 NWD（阈值相应调整）能显著减少小目标的重复框</strong>。<em>这一步在论文里很少提，但在真实系统里很有效——而且改动只有一行。</em>",
        ),
    ])),

    ("scale_loss", "解法三：scale-aware 损失加权，与「加过头」的两种代价", "".join([
        P("最后一层是损失加权：既然小目标学不好，<strong>就在损失里给它更大的权重</strong>。典型形式是"),
        MATH("w_i \\;=\\; \\left(\\frac{s_{\\mathrm{ref}}}{s_i}\\right)^{\\!\\gamma}, \\qquad s_i = \\sqrt{w_i h_i}, \\qquad \\text{并归一化使 } \\frac{1}{N}\\sum_i w_i = 1"),
        P("这条路最容易实现（改一行），也最容易做过头。<strong>「加权多少」有一个内点最优解，而不是「越大越好」</strong>——notebook 里用一个可以精确求解的模型把这件事算出来。"),
        H3("为什么最优 γ 是内点：两股相反的力"),
        TABLE(["γ 增大时", "机制", "效果方向"], [
            ["<strong>①  修正梯度杠杆不平衡</strong>", "归一化坐标下小目标的损失/梯度本来就小（上一节的 5 倍差距）；加权把它补回来", "<strong>↑ 变好</strong>"],
            ["<strong>②  容量冲突</strong>", "检测头是共享的，小目标与大目标的最优参数不同。权重全给小目标 ⇒ 大目标退化", "<strong>↓ 变差</strong>"],
            ["<strong>③  噪声放大</strong>", "小目标的标注噪声相对量级最大（±2 px 对 8 px 框是 25% 相对误差）。加权同时放大了噪声的方差", "<strong>↓ 变差</strong>"],
            ["<strong>④  与 Focal 的双重加权</strong>", "Focal Loss 已按「难度」隐式加权，而小目标本来就难 ⇒ 隐式 × 显式 = 过度", "<strong>↓ 变差</strong>"],
        ]),
        P("notebook 的模拟（共享参数 + 两组不同最优值 + 异方差噪声）给出的结论是定量的：<strong>在按尺寸分桶等权的指标下，最优 γ ≈ 1.4，指标从 0.463 降到 0.250；而 γ = 3 时指标回升到 0.476，比不加权还差</strong>。同时估计量的方差从 2.8×10⁻⁵ 涨到 1.07×10⁻²（<strong>380 倍</strong>）——<em>这就是「加了小目标权重后训练开始不稳、多种子方差变大」的机制。</em>"),
        CALLOUT("warn", "<strong>三条实操约束，都直接来自上表：</strong> ① <strong>γ 取 0.25–0.5</strong>（不是 1 更不是 2）；② <strong>必须归一化使权重均值为 1</strong>，否则总梯度尺度改变，等价于偷偷改了学习率——这是「加了加权之后 loss 曲线整体抬高、需要重调 lr」的原因；③ <strong>只对回归损失加权，不对分类损失加权</strong>。分类的不平衡应该由 Focal / 采样策略处理，两边同时加权就是上表的第 ④ 条。"),
        H3("Focal Loss 的参数在小目标场景要往回调"),
        P("Focal Loss 的 <code>(1−p_t)^γ_f</code> 把梯度集中到「难」样本上。<strong>在小目标密集的场景，这个机制有一个特定的失效模式，而且后果很严重。</strong>"),
        DUAL(
            "小目标场景里最「难」的负样本，往往<strong>不是真的负样本，而是漏标的真实目标</strong>——标注员看不清 6 px 的牌子，于是没标；模型（尤其在训练后期）却能对它产生响应。<em>在 Focal 眼里，这就是一个「模型很自信、标签说是背景」的极难负样本，会拿到最大的权重</em>。<strong>γ_f = 2 时，模型被最用力地训练去把真实目标压成背景。</strong>",
            "所以在 TSR 这类「小目标 + 标注必然不完整」的任务上，建议是：<strong>① γ_f 从 2 降到 1.0–1.5</strong>（削弱对极难负样本的聚焦）；<strong>② α 从 0.25 提到 0.4–0.5</strong>（正样本占比只有 0.04%，见模块 02，需要更强的正样本权重）；<strong>③ 更根本的一招——把低于标注下限的区域标成 ignore</strong>，让它们既不算正也不算负，从源头切断这条错误监督；<strong>④ 如果用 Quality Focal / VariFocal 这类以 IoU 为软标签的损失，把软标签换成 NWD</strong>——因为小目标的 IoU 软标签系统性偏低，会把模型训成对小目标永远不自信（这直接影响下游的置信度阈值设定）。",
        ),
        ASCII("""三层解法的关系与推荐叠加顺序（TSR 场景）

  第 ①层 · 分配「谁是正样本」
     ├─ center-based（点在框内）……………… 绕开 anchor 尺寸匹配
     ├─ ATSS（阈值 = 均值+标准差）………… 自适应，但极小目标上会退化
     ├─ SimOTA dynamic-k ………………………… **对小目标方向是反的**，需设 k 下界
     └─ HLA / 保底 k ……………………………… 保证每个 GT 至少 k 个正样本
                     ▲
                     │  这一层的所有机制内部都在用一把「尺子」
                     ▼
  第 ②层 · 度量「用什么尺子判」          ← **优先级最高，改动最小**
     ├─ IoU ………………………… 相对度量，对小框有系统性偏见
     ├─ 尺度自适应 IoU 阈值 …… 只在判正负这一点上补偿
     ├─ **NWD** …………………… 位置项是绝对距离，处处光滑，三行实现
     └─ KLD(GT‖ERF) (RFLA) …… 用感受野当参考分布
                     ▲
                     ▼
  第 ③层 · 损失「正样本怎么加权」
     ├─ scale-aware 加权（γ ∈ [0.25, 0.5]，均值归一化，只加回归）
     ├─ IoU 变体选择（EIoU / 1−NWD；避开纯 GIoU、未修正 CIoU）
     └─ Focal 参数回调（γ_f 1.0–1.5, α 0.4–0.5, 低于下限的标 ignore）

  推荐顺序：② → ① → ③   （先把尺子换对，再改分配规则，最后微调权重）"""),
        CALLOUT("intuition", "为什么顺序是 ② → ① → ③：<strong>第 ② 层的改动最小、收益最确定、且会自动改善第 ① 层</strong>（因为分配器内部就在用这把尺子）；第 ① 层的保底 k 解决的是「完全没有监督」这种极端情况，收益大但只影响少数 GT；第 ③ 层的加权是<em>在已经正确的正样本集合上做微调</em>，收益最小、副作用最多。<strong>如果面试时被问「你会先做哪个」，这个排序本身就是答案，而给出排序的理由比排序本身更重要。</strong>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("小目标的分配与损失是近三年最活跃的方向之一，但也是最容易「刷点」的地方——很多提升在换数据集后不复现。以下是仍然开放、且对 TSR 有直接意义的问题。"),
        UL([
            "<strong>度量的统一理论仍然缺失。</strong> IoU、GIoU、NWD、KLD、GWD（Gaussian Wasserstein Distance，用于旋转框）各自解决一部分问题，但<em>没有一个框架能说明「给定目标尺寸分布与噪声水平，最优的度量是什么」</em>。目前的选择基本靠试。一个有价值的方向是把度量的选择建模成「在标注噪声下的最优判决规则」——<em>如果标注抖动是 ±2 px 的高斯，什么度量能最大化正样本判决的信噪比？</em>",
            "<strong>C 的自适应。</strong> NWD 的 C 是全局常数，但一张图里可能同时有 6 px 和 200 px 的目标。<em>让 C 随目标尺寸或金字塔层变化</em>，理论上更合理，但会破坏「绝对度量」这个核心性质（C 随尺寸变就又回到相对度量了）。这个张力目前没有干净的解法，实践上用「按尺寸切换 IoU/NWD」绕过。",
            "<strong>分配的稳定性。</strong> 动态分配在训练早期极不稳定（同一个 GT 在相邻 epoch 被不同的 anchor 认领），这个问题在小目标上被放大——<em>因为小目标的候选之间差异本来就小，排序容易翻转</em>。C54 m04 讲的 DN-DETR 式「去噪 query」是 DETR 系的解法，密集检测器这边还缺少对应的机制。",
            "<strong>标注噪声与难例的纠缠。</strong> 小目标的标注误差相对量级最大（±2 px 对 8 px 框是 25%），于是「难例」和「噪声标签」在损失空间里几乎不可分。<em>Focal Loss 与 OHEM 都会优先学噪声</em>（见 C58 m02）。一个开放问题是：<strong>能否用度量本身的性质做区分</strong>——例如噪声标签在 NWD 下的表现与真难例是否有系统差异（噪声是位置抖动 → W₂ 的位置项主导；真难例是遮挡/模糊 → 分类分数低但位置准）。",
            "<strong>与端到端检测器的结合。</strong> DETR 系用匈牙利匹配做一对一分配，代价矩阵里的 L1 + GIoU 对小目标同样不友好。<em>把代价矩阵里的 GIoU 换成 NWD</em> 是一个直接的想法，但一对一匹配下正样本本来就只有一个，度量的改变对匹配结果的影响与密集检测器不同——这方面的系统研究还很少。",
            "<strong>评测的循环论证。</strong> 小目标方法几乎都在 AI-TOD / VisDrone / TinyPerson 上评测，而这些数据集的标注下限、尺寸分布、噪声水平各不相同。<em>一个在 AI-TOD 上 +4 AP 的方法在 TT100K 上可能只有 +0.5</em>。<strong>更根本的是：如果评测集本身就漏标了大量极小目标，那么「学会检出它们」的模型反而会被判为误检更多。</strong> 这是 TSR 上离线指标与路测体验背离的一个直接来源（详见 C55 m05）。",
        ]),
        CALLOUT("paper", "必读：<em>A Normalized Gaussian Wasserstein Distance for Tiny Object Detection</em>（Wang, Xu, Yang, Yu, 2021，arXiv:2110.13389——本模块的核心，重点看第 3 节的推导与图 3 的 IoU/NWD 敏感性对比）；<em>RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection</em>（Xu et al., ECCV 2022，注意 KLD 的方向与 HLA 的三级放宽策略）；<em>Bridging the Gap Between Anchor-based and Anchor-free Detection via ATSS</em>（Zhang et al., CVPR 2020，均值+标准差阈值的动机）；<em>OTA / YOLOX（SimOTA）</em>（Ge et al., 2021，dynamic-k 的出处）；IoU 变体一族：<em>GIoU</em>（Rezatofighi, CVPR 2019）、<em>DIoU/CIoU</em>（Zheng et al., AAAI 2020——第 4 节明确写了去掉 1/(w²+h²) 分母的理由）、<em>Focal-EIoU</em>（Zhang et al., 2021）、<em>SIoU</em>（Gevorgyan, 2022）；<em>Focal Loss</em>（Lin et al., ICCV 2017）。旋转框方向的 <em>GWD</em>（Yang et al., ICML 2021）与 <em>KLD</em>（Yang et al., NeurIPS 2021）是同一套高斯建模思路的延伸，很值得对照阅读。相邻课程：C57 m01（IoU 敏感性推导）、C57 m02（层级与分辨率）、C53 m02（标签分配谱系）、C58 m02（难例与噪声的区分）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · 分配与损失层面的解法（NWD / RFLA / center-based / IoU 变体 / scale-aware 加权）

目标：把「IoU 这把尺子对小框是坏的」从一句话变成一组**可以 assert 的等式**，
然后从零实现 **NWD**，并证明它恰好补上了 IoU 的三个短板。

**你会亲手实现：**
1. IoU 的位移灵敏度 `4/w` 与 NWD 的 `√2/C`——**一个反比于框长，一个是常数**
2. **NWD 全套**：bbox → 2D 高斯 → 2-Wasserstein 闭式解 → 指数归一化（三行）
3. **关键对比实验**：正样本容忍半径、死区比例、跨尺度一致性，逐条 assert
4. stride-8 网格上的**匹配率**：IoU@0.5 下 8 px 目标只有 ~25%，NWD@0.5 下 100%
5. center-based 分配 + **从设计目标反解出来的**尺度自适应阈值 `τ(w) = (w−r₀)/(w+r₀)`
6. ATSS 的自适应阈值、SimOTA 的 dynamic-k（**证明它对小目标方向是反的**）
7. RFLA 的 KLD——并算清楚**方向搞反会比 IoU 更不公平**
8. IoU / GIoU / DIoU / CIoU / EIoU / SIoU 全套，验证 **GIoU 奖励放大、NWD 惩罚放大**
9. scale-aware 加权的**内点最优 γ**，以及噪声方差被放大 380 倍

> 心智模型：**小目标面对的威胁（网格量化 ±4 px、标注抖动 ±2 px）都是绝对像素量，
> 而 IoU 是相对度量。用相对度量去衡量绝对误差，就是整个问题的根源。
> NWD 的全部价值，就是把位置项换成绝对距离。**"""),

    md("""## 1 · 把问题钉死：IoU 的位移灵敏度是 4/w"""),
    code("""import numpy as np, math
rng = np.random.default_rng(573)

def to_xyxy(b):
    b = np.asarray(b, dtype=float)
    cx, cy, w, h = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([cx - w/2, cy - h/2, cx + w/2, cy + h/2], axis=-1)

def iou(a, b):
    '''a, b: (..., 4) 的 (cx, cy, w, h)。支持广播。'''
    A, B = to_xyxy(a), to_xyxy(b)
    x1 = np.maximum(A[..., 0], B[..., 0]); y1 = np.maximum(A[..., 1], B[..., 1])
    x2 = np.minimum(A[..., 2], B[..., 2]); y2 = np.minimum(A[..., 3], B[..., 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    ar_a = np.clip(A[...,2]-A[...,0], 0, None) * np.clip(A[...,3]-A[...,1], 0, None)
    ar_b = np.clip(B[...,2]-B[...,0], 0, None) * np.clip(B[...,3]-B[...,1], 0, None)
    return inter / np.maximum(ar_a + ar_b - inter, 1e-12)

# 模块 01 的两个招牌数字，先对上
assert abs(float(iou((0,0,8,8),  (2,2,8,8)))  - 36/92)     < 1e-12
assert abs(float(iou((0,0,64,64),(2,2,64,64))) - 3844/4348) < 1e-12
print(f'8x8  框对角位移 2px: IoU = {float(iou((0,0,8,8),(2,2,8,8))):.4f}')
print(f'64x64 框对角位移 2px: IoU = {float(iou((0,0,64,64),(2,2,64,64))):.4f}')
print(f'=> 同样 2 px 的绝对误差，小框被惩罚了 '
      f'{float(iou((0,0,64,64),(2,2,64,64)))/float(iou((0,0,8,8),(2,2,8,8))):.2f} 倍')"""),

    md("""## 2 · 从零实现 NWD：bbox → 2D 高斯 → W₂ → exp 归一化"""),
    code("""C_NWD = 12.8          # NWD 唯一的超参：取数据集目标 sqrt(wh) 的均值（AI-TOD 用 12.8）

def box_to_gauss(b):
    '''(cx,cy,w,h) -> (mu, Sigma^{1/2} 的对角元)。
       Sigma = diag(w²/4, h²/4)  =>  Sigma^{1/2} = diag(w/2, h/2)。
       物理含义：把框的**内切椭圆**当作高斯的等密度线。'''
    b = np.asarray(b, dtype=float)
    return b[..., :2], b[..., 2:] / 2.0

def w2_sq(a, b):
    '''两个对角高斯的 2-Wasserstein 距离平方（闭式解）：
       W2² = ||mu_a - mu_b||² + ||Sigma_a^{1/2} - Sigma_b^{1/2}||_F²
       对角情形下 = 把框写成 [cx, cy, w/2, h/2] 之后的欧氏距离平方。'''
    mu_a, s_a = box_to_gauss(a)
    mu_b, s_b = box_to_gauss(b)
    return ((mu_a - mu_b) ** 2).sum(-1) + ((s_a - s_b) ** 2).sum(-1)

def nwd(a, b, C=C_NWD):
    '''NWD = exp(-sqrt(W2²)/C)，取值 (0, 1]，= 1 当且仅当两框完全相同。'''
    return np.exp(-np.sqrt(w2_sq(a, b)) / C)

# —— 正确性校验：手算对拍 ——
assert abs(float(w2_sq((0,0,8,8), (2,2,8,8))) - 8.0) < 1e-12       # 4+4+0+0
assert abs(float(w2_sq((0,0,8,8), (0,0,16,16))) - 2*16.0) < 1e-12  # 0+0+4²+4²
assert abs(float(nwd((3,7,11,5), (3,7,11,5))) - 1.0) < 1e-15,  'NWD(x,x) 必须恰为 1'
assert 0 < float(nwd((0,0,8,8), (999,999,8,8))) < 1e-40,        'NWD 恒 > 0（永不进死区）'
manual = math.exp(-math.sqrt(8.0) / C_NWD)
assert abs(float(nwd((0,0,8,8), (2,2,8,8))) - manual) < 1e-15
print(f'W2²((0,0,8,8),(2,2,8,8)) = {float(w2_sq((0,0,8,8),(2,2,8,8))):.1f}')
print(f'NWD = exp(-sqrt(8)/12.8) = {manual:.6f}')
print('✅ 三行实现，处处可导，且不需要求交集。')"""),

    code("""# **性质一（核心）**：相同绝对位移 -> 相同 NWD，与框大小无关（可精确 assert）
print(f"{'框边长':>8s} {'IoU(位移2px)':>14s} {'NWD(位移2px)':>14s}")
nwds = []
for w in [4, 8, 16, 32, 64, 128, 256]:
    i_ = float(iou((0,0,w,w), (2,2,w,w)))
    n_ = float(nwd((0,0,w,w), (2,2,w,w)))
    nwds.append(n_)
    print(f'{w:>8d} {i_:>14.4f} {n_:>14.6f}')

assert max(nwds) - min(nwds) < 1e-14, 'NWD 对同一绝对位移在所有尺度上完全相同'
ious = [float(iou((0,0,w,w), (2,2,w,w))) for w in [4, 8, 16, 32, 64, 128, 256]]
pen  = [1.0 - v for v in ious]          # 「惩罚」= 1 - IoU，差异看得更清楚
assert max(ious) / min(ious) > 6.0, 'IoU 本身在不同尺度上相差数倍'
assert max(pen) / min(pen) > 25.0,  '按「惩罚」看差了一个多量级'
print(f'\\n⚠️  IoU 最大/最小 = {max(ious)/min(ious):.1f} 倍；'
      f'按惩罚(1−IoU) 看是 {max(pen)/min(pen):.0f} 倍   ❌ 极不公平')
print(f'✅ NWD: 最大−最小 = {max(nwds)-min(nwds):.2e}   —— 是恒等式，不是近似')"""),

    md("""## 3 · 关键对比实验：灵敏度、死区、容忍半径"""),
    code("""# (a) 位移灵敏度： |d(metric)/d(delta)| 在 delta=0 处
def sens_at_zero(metric, w, eps=1e-3):
    '''沿对角线每轴位移 eps，用有限差分估计灵敏度。'''
    return (metric((0,0,w,w), (0,0,w,w)) - metric((0,0,w,w), (eps,eps,w,w))) / eps

print(f"{'框边长 w':>10s} {'IoU 灵敏度':>12s} {'理论 4/w':>10s} "
      f"{'NWD 灵敏度':>12s} {'理论 √2/C':>11s}")
for w in [4, 8, 16, 32, 64, 128]:
    si = float(sens_at_zero(lambda a,b: iou(a,b), w))
    sn = float(sens_at_zero(lambda a,b: nwd(a,b), w))
    assert abs(si - 4.0/w) < 0.01, (w, si)
    assert abs(sn - math.sqrt(2)/C_NWD) < 1e-4, (w, sn)
    print(f'{w:>10d} {si:>12.4f} {4.0/w:>10.4f} {sn:>12.4f} {math.sqrt(2)/C_NWD:>11.4f}')

s4, s128 = float(sens_at_zero(lambda a,b: iou(a,b), 4)), \\
           float(sens_at_zero(lambda a,b: iou(a,b), 128))
assert abs(s4/s128 - 32.0) < 0.5
print(f'\\n⚠️  IoU 的灵敏度 = 4/w —— 4px 框比 128px 框陡 {s4/s128:.0f} 倍')
print(f'✅ NWD 的灵敏度 = √2/C = {math.sqrt(2)/C_NWD:.4f} —— **与 w 完全无关**')"""),

    code("""# (b) 死区：IoU 在不相交时恒为 0（梯度也为 0）；NWD 永远 > 0
print(f"{'框边长':>8s} {'δ∈[0,2w] 上 IoU==0 的比例':>26s} {'NWD 最小值':>14s}")
for w in [8, 32, 128]:
    d = np.linspace(0, 2*w, 401)
    boxes_a = np.tile(np.array([0., 0., w, w]), (len(d), 1))
    boxes_b = np.stack([d, d, np.full(len(d), float(w)), np.full(len(d), float(w))], 1)
    iv, nv = iou(boxes_a, boxes_b), nwd(boxes_a, boxes_b)
    dead = float((iv <= 0).mean())
    assert dead > 0.49, (w, dead)
    assert nv.min() > 0
    print(f'{w:>8d} {dead:>25.1%} {nv.min():>14.3e}')
print('\\n⚠️  IoU 在一半以上的位移范围内恒为 0：错 9px 和错 90px 在它眼里一模一样。')
print('✅ NWD 恒 > 0；但注意 C 决定了有效范围 —— d >> C 时它指数衰减，梯度同样消失。')
print('   经验规则：C ≈ 数据集目标 sqrt(wh) 的均值。')"""),

    code("""# (c) 正样本容忍半径（沿轴位移）：IoU 正比于 w，NWD 恒定
def iou_radius_axis(w, tau):
    '''解 (w-r)/(w+r) = tau  =>  r = w(1-tau)/(1+tau)'''
    return w * (1.0 - tau) / (1.0 + tau)

def nwd_radius(C, tau):
    '''解 exp(-r/C) = tau  =>  r = -C ln(tau)   （等尺寸框，Sigma 项抵消）'''
    return -C * math.log(tau)

# 数值验证两个闭式解
for w, tau in [(8, 0.5), (32, 0.3), (128, 0.7)]:
    r = iou_radius_axis(w, tau)
    assert abs(float(iou((0,0,w,w), (r,0,w,w))) - tau) < 1e-9
r = nwd_radius(C_NWD, 0.5)
assert abs(float(nwd((0,0,20,20), (r,0,20,20))) - 0.5) < 1e-9

GRID_ERR = 4.0        # stride 8 网格：GT 中心到最近格子中心的偏移，每轴最大 4 px
print(f"{'w':>6s} {'r(IoU@0.5)':>12s} {'r(IoU@0.3)':>12s} {'r(NWD@0.5)':>12s} {'够不够 4px 量化误差'}")
for w in [4, 8, 16, 64, 256]:
    r5, r3, rn = iou_radius_axis(w,0.5), iou_radius_axis(w,0.3), nwd_radius(C_NWD,0.5)
    ok5 = '✅' if r5 >= GRID_ERR else '❌'
    print(f'{w:>6d} {r5:>11.2f}{ok5} {r3:>12.2f} {rn:>12.2f} '
          f'{"IoU@0.5 覆盖不了网格误差" if r5 < GRID_ERR else ""}')

assert iou_radius_axis(8, 0.5) < GRID_ERR, '8px 框在 IoU@0.5 下的容忍半径小于网格量化误差'
assert iou_radius_axis(256, 0.3) > 100, '把阈值降到 0.3 会让大框的容忍半径失控'
print(f'\\n⚠️  IoU@0.5: 8px 框只容忍 {iou_radius_axis(8,0.5):.2f}px < 网格固有误差 4px'
      f' -> **结构性不匹配**')
print(f'⚠️  降到 IoU@0.3: 8px 够了({iou_radius_axis(8,0.3):.2f}px)，'
      f'但 256px 框变成 {iou_radius_axis(256,0.3):.0f}px -> 收进大量明显错的框')
print(f'✅ NWD@0.5: 所有尺度都是 {nwd_radius(C_NWD,0.5):.2f}px —— 由 C 与 τ 直接设计')"""),

    code("""# (d) 决定性实验：stride-8 网格上的**匹配率**（anchor 尺寸完美匹配，已是最有利情形）
def match_rate(size, stride, metric, thr, n=200_000, anchor_size=None):
    '''GT 中心随机 -> 到最近格子中心的偏移每轴 ~ U(-stride/2, stride/2)。'''
    a_sz = float(anchor_size if anchor_size is not None else size)
    d = rng.uniform(-stride/2.0, stride/2.0, size=(n, 2))
    gt  = np.tile(np.array([0., 0., float(size), float(size)]), (n, 1))
    anc = np.stack([d[:,0], d[:,1], np.full(n, a_sz), np.full(n, a_sz)], axis=1)
    return float((metric(gt, anc) >= thr).mean())

def adaptive_iou_thr(size, r0=4.0, tau_min=0.15, tau_max=0.90):
    '''**轴向**设计：让「沿轴位移」的容忍半径恒为 r0。
       解 w(1-τ)/(1+τ) = r0  =>  τ = (w-r0)/(w+r0)'''
    return float(np.clip((size - r0) / (size + r0), tau_min, tau_max))

def adaptive_iou_thr_diag(size, r0=4.5, tau_min=0.05, tau_max=0.90):
    '''**对角**设计：让「两轴各偏 r0」这个最坏角点恰好达到阈值。
       IoU_diag(δ) = a/(2-a)，a = (1-δ/w)²  =>  τ = a/(2-a)'''
    a = max(0.0, 1.0 - r0 / float(size)) ** 2
    return float(np.clip(a / (2.0 - a), tau_min, tau_max))

print(f"{'GT 尺寸':>8s} {'IoU@0.5':>9s} {'IoU@0.3':>9s} {'自适应(轴向)':>13s} "
      f"{'自适应(对角)':>13s} {'NWD@0.5':>9s}")
rates = {}
for size in [4, 8, 16, 32, 64]:
    r1 = match_rate(size, 8, lambda a,b: iou(a,b), 0.5)
    r2 = match_rate(size, 8, lambda a,b: iou(a,b), 0.3)
    r3 = match_rate(size, 8, lambda a,b: iou(a,b), adaptive_iou_thr(size))
    r3d = match_rate(size, 8, lambda a,b: iou(a,b), adaptive_iou_thr_diag(size))
    r4 = match_rate(size, 8, lambda a,b: nwd(a,b), 0.5)
    rates[size] = (r1, r2, r3, r3d, r4)
    print(f'{size:>8d} {r1:>8.1%} {r2:>8.1%} {r3:>12.1%} {r3d:>12.1%} {r4:>8.1%}')

assert 0.20 < rates[8][0]  < 0.30, rates[8][0]     # 8px + IoU@0.5 -> ~25%
assert 0.80 < rates[16][0] < 0.90, rates[16][0]    # 16px -> ~85%
assert rates[32][0] > 0.999                        # 32px -> 100%
assert rates[8][4] > 0.999 and rates[4][4] > 0.999, 'NWD@0.5 在所有尺度上都是 100%'
assert rates[8][3] > 0.999 and rates[8][3] > rates[8][2], '对角设计才真的拉到 100%'
print(f'\\n⚠️  **即使 anchor 尺寸完美匹配**，8px 目标在 IoU@0.5 下也只有 '
      f'{rates[8][0]:.0%} 能匹配上 —— 另外 {1-rates[8][0]:.0%} 一个正样本都没有。')
print('    真实配置里 anchor 尺寸未必匹配，只会更差。')
print(f'⚠️  轴向设计的自适应阈值只能到 {rates[8][2]:.0%} —— 因为 **IoU 的等值面是各向异性的**：')
print('    同样 4px 的偏移，沿对角(4,4) 比沿轴(5.66,0) 更伤 IoU。')
print(f'✅ 按对角最坏角点设计后达到 {rates[8][3]:.0%}；NWD@0.5 直接就是 {rates[8][4]:.0%} ——')
print('    因为 **NWD 只依赖 ||Δμ||，等值面是标准圆**，根本没有各向异性这回事。')

# NWD 并没有退化成「什么都匹配」：尺寸差太多照样拒绝
n_mismatch = float(nwd((0,0,8,8), (0,0,32,32)))
assert n_mismatch < 0.5, n_mismatch
print(f'✅ 但 NWD 不是万能通行证：8px GT vs 32px anchor（中心重合）NWD = '
      f'{n_mismatch:.3f} < 0.5，照样拒绝 —— Σ 项显式惩罚尺寸不匹配。')"""),

    md("""## 4 · center-based 分配与尺度自适应阈值"""),
    code("""def center_sampling(gt, points, radius_cells, stride):
    '''FCOS 式 center sampling：点必须同时
       ① 落在 GT 框内   ② 距 GT 中心 < radius_cells * stride
       对小目标 ② 的半径可能大于目标本身，所以**必须求交**，否则会收进背景点。'''
    gt = np.asarray(gt, float); pts = np.asarray(points, float)
    x1, y1, x2, y2 = gt[0]-gt[2]/2, gt[1]-gt[3]/2, gt[0]+gt[2]/2, gt[1]+gt[3]/2
    in_box = (pts[:,0] >= x1) & (pts[:,0] <= x2) & (pts[:,1] >= y1) & (pts[:,1] <= y2)
    r = radius_cells * stride
    in_rad = (np.abs(pts[:,0]-gt[0]) < r) & (np.abs(pts[:,1]-gt[1]) < r)
    return in_box & in_rad

STRIDE, R_CELLS = 8, 2.5          # YOLOX 的 center sampling 半径是 2.5 个格子
grid = np.array([[x + STRIDE/2, y + STRIDE/2]
                 for x in range(0, 128, STRIDE) for y in range(0, 128, STRIDE)])
print(f"{'GT 尺寸':>8s} {'只用半径':>10s} {'只在框内':>10s} {'两者求交':>10s}")
n_rad_only = None
for size in [6, 8, 16, 32, 64]:
    g = (64., 64., float(size), float(size))
    only_rad = int(((np.abs(grid[:,0]-64) < R_CELLS*STRIDE) &
                    (np.abs(grid[:,1]-64) < R_CELLS*STRIDE)).sum())
    n_rad_only = only_rad
    x1,y1,x2,y2 = 64-size/2, 64-size/2, 64+size/2, 64+size/2
    only_box = int(((grid[:,0]>=x1)&(grid[:,0]<=x2)&(grid[:,1]>=y1)&(grid[:,1]<=y2)).sum())
    both = int(center_sampling(g, grid, R_CELLS, STRIDE).sum())
    print(f'{size:>8d} {only_rad:>10d} {only_box:>10d} {both:>10d}')

n6  = int(center_sampling((64.,64.,6.,6.),   grid, R_CELLS, STRIDE).sum())
n64 = int(center_sampling((64.,64.,64.,64.), grid, R_CELLS, STRIDE).sum())
assert n6 <= 1 and n_rad_only >= 9 and n64 >= 9, (n6, n_rad_only, n64)
print(f'\\n⚠️  只用半径 -> 6px 的目标会拿到 {n_rad_only} 个正样本，'
      f'而它们的特征**几乎全是背景**（目标只有 6px，半径覆盖 40px）。')
print(f'✅ 必须与「点在框内」求交。但求交之后，6px 目标只剩 {n6} 个正样本 ——')
print('   这个上限只有更高分辨率（P2）能突破，分配规则本身解决不了。')"""),

    code("""# 尺度自适应阈值：从设计目标（容忍半径恒为 r0）反解，而不是拍脑袋定表
print(f"{'w':>6s} {'τ(w), r0=4':>12s} {'反算半径':>10s} {'固定τ=0.5 的半径':>18s}")
for w in [8, 16, 32, 64, 256]:
    t = adaptive_iou_thr(w, r0=4.0)
    r = iou_radius_axis(w, t)
    print(f'{w:>6d} {t:>12.3f} {r:>10.2f} {iou_radius_axis(w,0.5):>18.2f}')

for w in [8, 16, 32, 64]:
    assert abs(iou_radius_axis(w, adaptive_iou_thr(w, r0=4.0)) - 4.0) < 1e-9, w
assert adaptive_iou_thr(256, r0=4.0) == 0.90, '大框会被 tau_max 截断（有意为之）'
print('\\n✅ τ(w) = (w−r0)/(w+r0) 让容忍半径在所有尺度上恒为 r0。')
print('   r0 的取法：网格量化误差(stride/2) + 标注抖动(±1~2px) + 亚像素回归精度。')
print('   ⚠️  注意：这与「固定阈值的 NWD」在做同一件事 —— 让容忍半径与尺度解耦。')
print('       区别是它只补偿了「判正负」这一个点，回归损失里的 IoU 该多陡还是多陡。')"""),

    md("""## 5 · ATSS 的自适应阈值，与 SimOTA dynamic-k 的反向作用"""),
    code("""def atss_threshold(gt, cand_boxes, metric):
    '''ATSS: 阈值 = 候选集上度量值的 均值 + 标准差。'''
    v = metric(np.tile(np.asarray(gt, float), (len(cand_boxes), 1)),
               np.asarray(cand_boxes, float))
    return float(v.mean() + v.std()), v

STRIDES = (4, 8, 16, 32)
# 每层的 anchor：RetinaNet 惯例 base scale = 4 x stride
LEVEL_ANCHORS = {}
for st in STRIDES:
    LEVEL_ANCHORS[st] = np.array([[x + st/2, y + st/2, 4.0*st, 4.0*st]
                                  for x in range(0, 256, st) for y in range(0, 256, st)])
anchors = np.concatenate([LEVEL_ANCHORS[st] for st in STRIDES], axis=0)

def topk_per_level(gt, k=9):
    '''ATSS 的候选集：**每层各取 k 个中心最近的 anchor**，再并起来。'''
    out = []
    for st in STRIDES:
        A = LEVEL_ANCHORS[st]
        d = np.linalg.norm(A[:, :2] - np.asarray(gt, float)[:2], axis=1)
        out.append(A[np.argsort(d)[:k]])
    return np.concatenate(out, axis=0)

GC = 127.3          # 故意放在非网格对齐的位置，打破对称性
print(f"{'GT 尺寸':>8s} {'候选均值':>10s} {'标准差':>9s} {'ATSS 阈值':>11s} "
      f"{'正样本数':>9s} {'正样本平均IoU':>14s} {'固定0.5能选出':>14s}")
info = {}
for size in [8, 32, 128]:
    g = (GC, GC, float(size), float(size))
    cand = topk_per_level(g, k=9)
    thr, v = atss_threshold(g, cand, lambda a, b: iou(a, b))
    pos = v >= thr - 1e-12
    n_fixed = int((v >= 0.5).sum())
    info[size] = dict(mean=float(v.mean()), std=float(v.std()), thr=thr,
                      n_pos=int(pos.sum()), q=float(v[pos].mean()), n05=n_fixed)
    print(f'{size:>8d} {v.mean():>10.4f} {v.std():>9.4f} {thr:>11.4f} '
          f'{int(pos.sum()):>9d} {v[pos].mean():>14.4f} {n_fixed:>14d}')

assert info[8]['thr'] < 0.3, 'ATSS 的阈值对小目标自动降下来（固定 0.5 会一个都选不出）'
assert info[128]['thr'] > 2 * info[8]['thr'], '阈值随目标变大而升高'
assert info[8]['n05'] == 0, '固定 IoU@0.5 对 8px 目标一个候选都选不出'
assert info[128]['n05'] > 0
assert info[8]['q'] < 0.5 * info[128]['q'], '小目标的正样本**质量**远低于大目标'
print('\\n✅ ATSS 的阈值从数据里长出来，对小目标自动降低 —— 确实比固定 0.5 公平：')
print(f"   8px 目标在固定 IoU@0.5 下能选出 {info[8]['n05']} 个候选，"
      f"ATSS 把阈值降到 {info[8]['thr']:.3f} 后选出 {info[8]['n_pos']} 个。")
print(f"⚠️  但正样本的**质量**没有跟上：8px 的正样本平均 IoU 只有 {info[8]['q']:.3f}，"
      f"而 128px 是 {info[128]['q']:.3f}。")
print('    模型被要求从一堆几乎不含目标的 anchor 上回归出准确的框。')
print('✅ 解法：把 ATSS 内部的 IoU 换成 NWD，两个机制叠加（自适应 + 公平的尺子）。')"""),

    code("""def dynamic_k(gt, anchors, metric, q=10):
    '''SimOTA: k = max(1, round(sum(top-q 候选的度量值)))'''
    v = metric(np.tile(np.asarray(gt, float), (len(anchors), 1)), np.asarray(anchors, float))
    topq = np.sort(v)[-q:]
    return max(1, int(round(float(topq.sum())))), float(topq.sum())

print(f"{'GT 尺寸':>8s} {'top10 IoU 和':>13s} {'k(IoU版)':>10s} "
      f"{'top10 NWD 和':>13s} {'k(NWD版)':>10s}")
ks = {}
for size in [8, 32, 128]:
    g = (128., 128., float(size), float(size))
    k_i, s_i = dynamic_k(g, anchors, lambda a,b: iou(a,b))
    k_n, s_n = dynamic_k(g, anchors, lambda a,b: nwd(a,b))
    ks[size] = (k_i, k_n)
    print(f'{size:>8d} {s_i:>13.2f} {k_i:>10d} {s_n:>13.2f} {k_n:>10d}')

assert ks[8][0] < ks[128][0], 'IoU 版的 dynamic-k 给小目标的正样本**更少**'
assert ks[8][1] > ks[8][0],   'NWD 版把小目标的 k 拉了回来'
assert ks[128][1] < ks[128][0], '但纯 NWD 版把**大目标**砍了 —— 这正是必须混合的理由'
print(f'\\n⚠️  **SimOTA 对小目标的作用方向是反的**：IoU 版给 8px 目标 k={ks[8][0]}，'
      f'给 128px 目标 k={ks[128][0]}。')
print('    本来正样本就稀缺的小目标，被 dynamic-k 又砍了一刀。')
print(f'✅ 换成 NWD 后 8px 的 k 从 {ks[8][0]} 回到 {ks[8][1]}。')
print(f'⚠️  但注意最后一行：**纯 NWD 把 128px 目标的 k 从 {ks[128][0]} 砍到了 {ks[128][1]}** ——')
print('    因为位置项是绝对距离，128px 目标的候选中心偏十几像素就被判成"很远"。')
print('    这就是本课反复强调的那条：**纯 NWD 会伤大目标，必须混合**')
print('    metric = (1-α)·IoU + α·NWD（α 按小目标占比设，TSR 上 0.5~0.8），')
print('    或按尺寸切换（sqrt(wh) < 32 用 NWD，其余用 IoU）。')
print('   一般判断：**任何以 IoU 为内部度量的自适应机制，都会继承 IoU 的尺度不公平；')
print('   而换成纯 NWD 又会把不公平倒向另一头。**')

# 验证混合度量能同时照顾两头
def mixed(a, b, alpha=0.7):
    return (1 - alpha) * iou(a, b) + alpha * nwd(a, b)
k_mix_8,   _ = dynamic_k((128., 128., 8., 8.),     anchors, mixed)
k_mix_128, _ = dynamic_k((128., 128., 128., 128.), anchors, mixed)
print(f'\\n混合度量(α=0.7): 8px -> k={k_mix_8}, 128px -> k={k_mix_128}')
assert k_mix_8 > ks[8][0] and k_mix_128 >= ks[128][1], (k_mix_8, k_mix_128)
print('✅ 混合后两头都不塌：小目标的 k 被拉起来，大目标的 k 不至于掉到 1。')"""),

    md("""## 6 · RFLA：KLD 的方向决定了公平性"""),
    code("""def kld_gauss(p, g):
    '''D_KL(N_p || N_g)，对角高斯，box = (cx,cy,w,h)。
       = 0.5[ tr(Σ_g⁻¹Σ_p) + (μ_g-μ_p)ᵀΣ_g⁻¹(μ_g-μ_p) - 2 + ln(|Σ_g|/|Σ_p|) ]
       **注意第二项是马氏距离：用「后一个参数」的协方差归一化。**'''
    mu_p, s_p = box_to_gauss(p); mu_g, s_g = box_to_gauss(g)
    var_p, var_g = s_p**2, s_g**2
    tr   = (var_p / var_g).sum(-1)
    maha = (((mu_g - mu_p) ** 2) / var_g).sum(-1)
    logd = (np.log(var_g) - np.log(var_p)).sum(-1)
    return 0.5 * (tr + maha - 2.0 + logd)

assert abs(float(kld_gauss((5,5,20,20), (5,5,20,20)))) < 1e-12, 'KL(x||x) = 0'
assert float(kld_gauss((0,0,8,8), (2,2,8,8))) > 0

# 方向 A：以 GT 为参考（位置项 ∝ 1/w²，比 IoU 还不公平）
print('方向 A：D_KL(pred ‖ GT)  —— 用 **GT 尺寸** 归一化位置项')
print(f"{'框边长':>8s} {'KLD(位移2px)':>14s} {'相对 8px 的比值':>16s}")
base_a = None
for w in [8, 16, 32, 64]:
    v = float(kld_gauss((2,2,w,w), (0,0,w,w)))
    base_a = base_a or v
    print(f'{w:>8d} {v:>14.6f} {v/base_a:>16.4f}')
v8  = float(kld_gauss((2,2,8,8),   (0,0,8,8)))
v64 = float(kld_gauss((2,2,64,64), (0,0,64,64)))
assert abs(v8 / v64 - 64.0) < 1e-6, (v8, v64)
print(f'⚠️  8px 的惩罚是 64px 的 {v8/v64:.0f} 倍 = (64/8)² —— **比 IoU 还不公平**')

# 方向 B（RFLA 用的）：以**有效感受野**为参考（σ 由网络层决定，与 GT 尺寸无关）
def erf_gauss(cx, cy, stride, erf_cells=2.0):
    '''把特征点的有效感受野建模成高斯：sigma_ERF = erf_cells * stride。
       用 box 表示则 w = h = 2*sigma。'''
    s = erf_cells * stride
    return (cx, cy, 2*s, 2*s)

print('\\n方向 B：D_KL(GT ‖ ERF)  —— 用 **感受野尺寸** 归一化位置项（RFLA 的做法）')
print(f"{'GT 边长':>8s} {'KLD 总值':>12s} {'其中位置项(马氏)':>18s}")
maha_vals = []
for w in [8, 16, 32, 64]:
    e = erf_gauss(2.0, 2.0, stride=8, erf_cells=2.0)      # ERF 中心偏 GT 中心 2px
    v = float(kld_gauss((0., 0., float(w), float(w)), e))
    _, s_e = box_to_gauss(np.array(e, float))
    m = float((((np.array(e[:2]) - np.array([0., 0.]))**2) / (s_e**2)).sum())
    maha_vals.append(m)
    print(f'{w:>8d} {v:>12.4f} {m:>18.6f}')
assert max(maha_vals) - min(maha_vals) < 1e-12, '位置项与 GT 尺寸无关 —— 这才是公平性的来源'
print('\\n✅ **RFLA 的公平性不来自 KLD，而来自「拿感受野当参考分布」这个选择** ——')
print('   σ_ERF 由网络层决定，与目标大小无关，位置项于是变成绝对距离除以固定尺度。')
print('⚠️  方向搞反（用 GT 当参考）会比 IoU 更不公平。这是很好的面试追问点。')"""),

    code("""# RFLA 的另一半：HLA 的「保底 k」—— 保证每个 GT 至少拿到 k 个正样本
def assign_with_floor(gts, anchors, metric, thr=0.5, k_min=3):
    '''① 先取 metric >= thr 的；② 不足 k_min 个的，用 metric 最大的前 k_min 个补齐。'''
    gts, anchors = np.asarray(gts, float), np.asarray(anchors, float)
    out = []
    for g in gts:
        v = metric(np.tile(g, (len(anchors), 1)), anchors)
        idx = np.flatnonzero(v >= thr)
        if len(idx) < k_min:
            idx = np.argsort(v)[-k_min:]
        out.append(np.sort(idx))
    return out

# 多尺度 anchor（每个格点 3 档），格距 8
anc2 = np.array([[x+4., y+4., float(sz), float(sz)]
                 for x in range(0, 128, 8) for y in range(0, 128, 8)
                 for sz in (8, 16, 32)])
gts2 = np.array([[64., 64., 8., 8.], [64., 64., 32., 32.]])

n_iou_small = int((iou(np.tile(gts2[0], (len(anc2),1)), anc2) >= 0.5).sum())
n_nwd_small = int((nwd(np.tile(gts2[0], (len(anc2),1)), anc2) >= 0.5).sum())
print(f'8px GT: IoU@0.5 匹配到 {n_iou_small} 个 anchor, NWD@0.5 匹配到 {n_nwd_small} 个')
assert n_iou_small <= 2 and n_nwd_small >= 5, (n_iou_small, n_nwd_small)

res = assign_with_floor(gts2, anc2, lambda a,b: nwd(a,b), thr=0.5, k_min=3)
for g, r in zip(gts2, res):
    print(f'  GT {g[2]:.0f}x{g[3]:.0f}px -> {len(r)} 个正样本')
assert all(len(r) >= 3 for r in res)
print('\\n✅ 「保底 k」解决的是「某些 GT 完全没有监督」这种极端情况。')
print('⚠️  没有保底时，这些 GT 的位置会被当作**负样本**训练 ——')
print('    模型被主动教育「这里没有目标」，比单纯漏掉它们更糟。')"""),

    md("""## 7 · IoU 变体家族：GIoU / DIoU / CIoU / EIoU / SIoU"""),
    code("""def _enclose(a, b):
    A, B = to_xyxy(a), to_xyxy(b)
    x1 = np.minimum(A[...,0], B[...,0]); y1 = np.minimum(A[...,1], B[...,1])
    x2 = np.maximum(A[...,2], B[...,2]); y2 = np.maximum(A[...,3], B[...,3])
    return x1, y1, x2, y2

def giou(a, b):
    i = iou(a, b)
    x1, y1, x2, y2 = _enclose(a, b)
    Ac = np.maximum((x2-x1)*(y2-y1), 1e-12)
    A, B = to_xyxy(a), to_xyxy(b)
    ar_a = (A[...,2]-A[...,0])*(A[...,3]-A[...,1])
    ar_b = (B[...,2]-B[...,0])*(B[...,3]-B[...,1])
    xi1 = np.maximum(A[...,0],B[...,0]); yi1 = np.maximum(A[...,1],B[...,1])
    xi2 = np.minimum(A[...,2],B[...,2]); yi2 = np.minimum(A[...,3],B[...,3])
    inter = np.clip(xi2-xi1,0,None)*np.clip(yi2-yi1,0,None)
    union = ar_a + ar_b - inter
    return i - (Ac - union) / Ac

def diou(a, b):
    a_, b_ = np.asarray(a,float), np.asarray(b,float)
    rho2 = ((a_[...,0]-b_[...,0])**2 + (a_[...,1]-b_[...,1])**2)
    x1,y1,x2,y2 = _enclose(a,b)
    c2 = np.maximum((x2-x1)**2 + (y2-y1)**2, 1e-12)
    return iou(a,b) - rho2/c2

def _v_aspect(a, b):
    a_, b_ = np.asarray(a,float), np.asarray(b,float)
    return (4/np.pi**2) * (np.arctan(b_[...,2]/np.maximum(b_[...,3],1e-12)) -
                           np.arctan(a_[...,2]/np.maximum(a_[...,3],1e-12)))**2

def ciou(a, b):
    i, v = iou(a,b), _v_aspect(a,b)
    alpha = v / np.maximum((1 - i) + v, 1e-12)
    return diou(a,b) - alpha*v

def eiou(a, b):
    a_, b_ = np.asarray(a,float), np.asarray(b,float)
    x1,y1,x2,y2 = _enclose(a,b)
    cw2 = np.maximum((x2-x1)**2, 1e-12); ch2 = np.maximum((y2-y1)**2, 1e-12)
    return (diou(a,b) - (a_[...,2]-b_[...,2])**2/cw2 - (a_[...,3]-b_[...,3])**2/ch2)

def siou(a, b, theta=4.0, eps=1e-9):
    a_, b_ = np.asarray(a,float), np.asarray(b,float)
    dx, dy = b_[...,0]-a_[...,0], b_[...,1]-a_[...,1]
    sigma = np.maximum(np.sqrt(dx**2+dy**2), eps)
    x = np.clip(np.abs(dy)/sigma, 0.0, 1.0)
    Lam = 1 - 2*np.sin(np.arcsin(x) - np.pi/4)**2         # 角度代价
    gam = 2 - Lam
    x1,y1,x2,y2 = _enclose(a,b)
    Cw = np.maximum(x2-x1, eps); Ch = np.maximum(y2-y1, eps)
    Delta = (1-np.exp(-gam*(dx/Cw)**2)) + (1-np.exp(-gam*(dy/Ch)**2))
    ow = np.abs(a_[...,2]-b_[...,2])/np.maximum(np.maximum(a_[...,2],b_[...,2]), eps)
    oh = np.abs(a_[...,3]-b_[...,3])/np.maximum(np.maximum(a_[...,3],b_[...,3]), eps)
    Omega = (1-np.exp(-ow))**theta + (1-np.exp(-oh))**theta
    return iou(a,b) - (Delta + Omega)/2

same = (10., 10., 20., 20.)
for f, nm in [(iou,'IoU'),(giou,'GIoU'),(diou,'DIoU'),(ciou,'CIoU'),(eiou,'EIoU'),(siou,'SIoU')]:
    assert abs(float(f(same, same)) - 1.0) < 1e-9, nm
print('✅ 六个度量在完全重合时都等于 1（一致性校验通过）')"""),

    code("""# 事实 ①：GIoU 奖励「把预测框放大」，NWD 惩罚它
GT = (0., 0., 8., 8.)
print(f"{'预测框边长':>11s} {'IoU':>8s} {'GIoU':>9s} {'DIoU':>9s} {'NWD':>9s}")
gs, ns = [], []
for w in [8, 16, 24, 40]:
    pred = (30., 30., float(w), float(w))       # 中心偏 30px（不相交）
    g_, n_ = float(giou(pred, GT)), float(nwd(pred, GT))
    gs.append(g_); ns.append(n_)
    print(f'{w:>11d} {float(iou(pred,GT)):>8.4f} {g_:>9.4f} '
          f'{float(diou(pred,GT)):>9.4f} {n_:>9.4f}')

assert all(float(iou((30.,30.,float(w),float(w)), GT)) == 0.0 for w in [8,16,24,40])
assert gs[-1] > gs[0] + 0.4, 'GIoU 随预测框放大而**变好** -> 优化器会朝这个方向走'
assert ns[-1] < ns[0],       'NWD 随预测框放大而变差 -> 方向相反'
print(f'\\n⚠️  预测框 8x8 -> 40x40: GIoU {gs[0]:.4f} -> {gs[-1]:.4f}（"变好了"）')
print(f'✅ 同样的变化: NWD {ns[0]:.4f} -> {ns[-1]:.4f}（变差）')
print('    Σ 项显式惩罚尺寸不匹配 —— **GIoU 奖励放大，NWD 惩罚放大，方向相反**。')
print('    对小目标，GIoU 的这个性质直接产生系统性偏大的框。')"""),

    code("""# 事实 ②：CIoU 的长宽比项梯度 ∝ 1/w （小框上大一个量级）
def dv_dw(w0, ar=1.25, eps=1e-6):
    '''在「GT 为 w0 x w0 方形、预测框为 (ar*w0) x w0」这一点上，
       固定 h，用有限差分求 ∂v/∂w。理论值 ∝ h/(w²+h²) ∝ 1/w0。'''
    gt, h = (0., 0., float(w0), float(w0)), float(w0)
    f = lambda ww: float(_v_aspect((0., 0., ww, h), gt))
    return (f(w0*ar + eps) - f(w0*ar - eps)) / (2*eps)

print(f"{'w':>6s} {'|∂v/∂w|':>12s} {'理论 ∝1/w（以 w=4 归一）':>26s}")
g4 = abs(dv_dw(4))
for w in [4, 8, 32, 128, 200]:
    gv = abs(dv_dw(w))
    print(f'{w:>6d} {gv:>12.6f} {g4 * 4.0/w:>26.6f}')
    assert abs(gv - g4*4.0/w) / (g4*4.0/w) < 0.02, w

r = abs(dv_dw(8)) / abs(dv_dw(200))
assert abs(r - 25.0) < 1.0, r
print(f'\\n⚠️  8px 与 200px 的长宽比项梯度相差 {r:.0f} 倍（= 200/8，精确的 1/w 关系）')
print('    归一化坐标下（除以图宽 1920），8px 对应的 h/(w²+h²) 因子约 120 ——')
print('    **这就是 CIoU 原文说「容易梯度爆炸、实现里直接去掉 w²+h² 分母」的由来**。')

# 事实 ③：CIoU 的长宽比项会完全失效（比例对了就不惩罚，哪怕大 5 倍）
pred_big, gt_small = (0., 0., 40., 40.), (0., 0., 8., 8.)
v = float(_v_aspect(pred_big, gt_small))
assert abs(v) < 1e-15, '长宽比相同 => v ≡ 0'
c_, e_ = float(ciou(pred_big, gt_small)), float(eiou(pred_big, gt_small))
print(f'\\n预测框 40x40 vs GT 8x8（中心重合、长宽比相同）:')
print(f'  v(长宽比项) = {v:.1e}  -> CIoU 退化成 IoU = {c_:.4f}')
print(f'  EIoU 分别惩罚 w 与 h  -> EIoU = {e_:.4f}')
assert abs(c_ - float(iou(pred_big, gt_small))) < 1e-9
assert e_ < c_ - 1.0, 'EIoU 给出强得多的信号'
print(f'✅ 差了 {c_ - e_:.2f} —— 这正是 EIoU 存在的理由。')"""),

    code("""# 归一化坐标下的 L1 会系统性低估小目标的误差
IMG_W = 1920.0
cases = [('8px 框宽度错 50%',   8.0, 0.50), ('200px 框宽度错 10%', 200.0, 0.10)]
l1s = []
for name, w, rel in cases:
    err_px = w * rel
    l1_norm = err_px / IMG_W
    l1s.append(l1_norm)
    print(f'{name:<22s} 绝对误差 {err_px:5.1f}px  归一化 L1 = {l1_norm:.5f}')
assert l1s[1] / l1s[0] > 4.5
print(f'\\n⚠️  客观上明显更差的那个预测（8px 框错了一半），'
      f'损失只有另一个的 {l1s[0]/l1s[1]:.2f} 倍。')
print('✅ 三种修法：① 按框尺寸归一化的相对误差；② scale-aware 加权；')
print('   ③ 直接用 L = 1 − NWD —— 它的位置项是**绝对像素距离**，天然没有这个问题。')

# NMS 里的 IoU 同样不公平
print(f'\\nNMS 场景：两个框中心相距 5px')
for w in [8, 200]:
    i_ = float(iou((0.,0.,float(w),float(w)), (5.,0.,float(w),float(w))))
    n_ = float(nwd((0.,0.,float(w),float(w)), (5.,0.,float(w),float(w))))
    print(f'  {w:>3d}px 框: IoU = {i_:.3f} ({"会被合并" if i_>0.5 else "**保留成两个目标**"}), '
          f'NWD = {n_:.3f}')
assert float(iou((0.,0.,8.,8.), (5.,0.,8.,8.))) < 0.5
assert float(iou((0.,0.,200.,200.), (5.,0.,200.,200.))) > 0.9
print('✅ 把 NMS 的 IoU 也换成 NWD 能显著减少小目标的重复框 —— 改动只有一行。')"""),

    md("""## 8 · scale-aware 加权：最优 γ 是内点，不是越大越好"""),
    code("""# 一个可精确求解的模型：共享一个参数 theta，两组目标的最优 theta 不同（容量冲突）
N_S, N_L   = 800, 200        # 小目标多、大目标少（TSR 的真实比例）
X_S, X_L   = 0.1, 1.0        # 「梯度杠杆」：归一化坐标下小目标的损失/梯度本来就小
TH_S, TH_L = 1.0, 2.0        # 两组的最优参数不同 -> 共享检测头的容量冲突
S_S, S_L   = 0.1, 1.0        # 尺度（用于加权）

def solve(gamma):
    '''加权最小二乘的闭式解： theta* = Σ w x² θ* / Σ w x² '''
    w_s, w_l = S_S ** (-gamma), S_L ** (-gamma)
    num = N_S*w_s*X_S**2*TH_S + N_L*w_l*X_L**2*TH_L
    den = N_S*w_s*X_S**2      + N_L*w_l*X_L**2
    return num/den, w_s, w_l, den

gammas = np.linspace(0, 3, 31)
thetas = np.array([solve(g)[0] for g in gammas])
# 指标：**按尺寸分桶等权**（每个桶算一次，再平均）—— 这正是分桶 mAP 的形式
score = 0.5*((thetas - TH_S)**2 + (thetas - TH_L)**2)
best = int(np.argmin(score))

print(f"{'gamma':>7s} {'theta*':>9s} {'小目标误差':>11s} {'大目标误差':>11s} {'分桶指标':>10s}")
for i in range(0, 31, 5):
    print(f'{gammas[i]:>7.2f} {thetas[i]:>9.4f} {(thetas[i]-TH_S)**2:>11.4f} '
          f'{(thetas[i]-TH_L)**2:>11.4f} {score[i]:>10.4f}')
print(f'\\n最优 gamma = {gammas[best]:.2f}, 指标 {score[best]:.4f}')

assert 0 < best < len(gammas)-1, '最优 gamma 是**内点**，不是端点'
assert score[best] < score[0],   '适度加权确实比不加权好'
assert score[-1] > score[0],     'gamma=3 时比**完全不加权还差**'
print(f'⚠️  不加权(γ=0): {score[0]:.4f} -> 最优(γ={gammas[best]:.1f}): {score[best]:.4f} '
      f'-> 过度(γ=3.0): {score[-1]:.4f}')
print('✅ 两股相反的力：① 修正梯度杠杆不平衡（变好） ② 容量冲突（变差）')
print('   => 最优 γ 是内点。实操建议 **γ ∈ [0.25, 0.5]**（本模型的最优值偏大是因为')
print('      杠杆差距被刻意设成了 10 倍；真实场景差距更小，最优 γ 也更小）。')"""),

    code("""# 第二股反向力：噪声放大。小目标标注噪声大（±2px 对 8px 框是 25% 相对误差）
SIG_S, SIG_L = 0.30, 0.05

def theta_variance(gamma):
    '''加权最小二乘估计量的方差： Var = Σ w² x² σ² / (Σ w x²)²'''
    _, w_s, w_l, den = solve(gamma)
    num = N_S*w_s**2*X_S**2*SIG_S**2 + N_L*w_l**2*X_L**2*SIG_L**2
    return num / den**2

var = np.array([theta_variance(g) for g in gammas])
print(f"{'gamma':>7s} {'估计量方差':>14s} {'相对 γ=0':>12s}")
for i in range(0, 31, 5):
    print(f'{gammas[i]:>7.2f} {var[i]:>14.3e} {var[i]/var[0]:>12.1f}x')
assert np.all(np.diff(var) > 0), '方差随 gamma 单调递增'
assert var[-1] / var[0] > 100
print(f'\\n⚠️  γ 从 0 到 3，估计量方差涨了 {var[-1]/var[0]:.0f} 倍 ——')
print('    这就是「加了小目标权重后训练开始不稳、多种子方差变大」的机制。')
print('✅ 三条实操约束：')
print('   ① γ ∈ [0.25, 0.5]（不是 1，更不是 2）')
print('   ② **必须归一化使权重均值为 1** —— 否则总梯度尺度改变 = 偷偷改了学习率')
print('   ③ **只对回归损失加权，不对分类损失加权**（分类不平衡交给 Focal / 采样）')"""),

    code("""# Focal Loss 的 gamma 在小目标场景要往回调：它会最用力地去学「漏标的真实目标」
p_neg = rng.beta(1.2, 12.0, size=200_000)        # 负样本得分：多数很低，少数很高
print(f"{'focal γ_f':>10s} {'最难的 1% 负样本占总损失的比例':>32s}")
shares = []
for gf in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
    fl = (p_neg ** gf) * (-np.log(np.clip(1 - p_neg, 1e-12, None)))
    share = float(np.sort(fl)[-2000:].sum() / fl.sum())
    shares.append(share)
    print(f'{gf:>10.1f} {share:>31.1%}')
assert all(shares[i] < shares[i+1] for i in range(len(shares)-1)), 'γ_f 越大越集中于极难负样本'
assert shares[-1] > 3 * shares[0]
print(f'\\n⚠️  γ_f 从 0 到 3，最难的 1% 负样本从占 {shares[0]:.1%} 涨到 {shares[-1]:.1%} 的损失。')
print('    **在小目标场景，这批"最难负样本"里有相当比例是漏标的真实目标**')
print('    （标注员看不清 6px 的牌子）—— γ_f=2 时模型被最用力地训练去把真目标压成背景。')
print('✅ TSR 建议：γ_f 降到 1.0–1.5；α 从 0.25 提到 0.4–0.5（正样本占比只有 0.04%）；')
print('   **更根本的一招：把低于标注下限的区域标成 ignore**，从源头切断这条错误监督。')
print('   若用 Quality Focal / VariFocal，把 IoU 软标签换成 NWD ——')
print('   小目标的 IoU 软标签系统性偏低，会把模型训成对小目标永远不自信。')"""),

    md("""## ✏️ 练习 1：从零实现 NWD

实现 `my_nwd(a, b, C)`：输入两个 `(cx, cy, w, h)`（支持 `(...,4)` 广播），返回 NWD。
**不许调用上面的 `nwd` / `w2_sq`**，从高斯建模开始自己写。"""),
    code("""def my_nwd(a, b, C=12.8):
    # TODO: ① mu = (cx, cy)，Sigma^{1/2} 的对角元 = (w/2, h/2)
    #       ② W2² = ||Δmu||² + ||ΔSigma^{1/2}||_F²
    #       ③ 返回 exp(-sqrt(W2²)/C)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
assert abs(float(my_nwd((3,7,11,5), (3,7,11,5))) - 1.0) < 1e-15
assert abs(float(my_nwd((0,0,8,8), (2,2,8,8))) - math.exp(-math.sqrt(8)/12.8)) < 1e-12
assert abs(float(my_nwd((0,0,8,8), (0,0,16,16))) - math.exp(-math.sqrt(32)/12.8)) < 1e-12
# 尺度不敏感（核心性质）
vals = [float(my_nwd((0,0,w,w), (2,2,w,w))) for w in [4,8,16,32,64,128,256]]
assert max(vals) - min(vals) < 1e-14, '相同绝对位移 -> 相同 NWD'
# 与参考实现逐元素对拍（含广播）
A = rng.uniform(0, 100, size=(50, 4)) + np.array([0,0,1,1])
B = rng.uniform(0, 100, size=(50, 4)) + np.array([0,0,1,1])
assert np.allclose(my_nwd(A, B, 12.8), nwd(A, B, 12.8), rtol=1e-12, atol=1e-14)
assert np.all(my_nwd(A, B) > 0), 'NWD 恒 > 0'
print(f'NWD((0,0,8,8),(2,2,8,8)) = {float(my_nwd((0,0,8,8),(2,2,8,8))):.6f}')
print(f'跨尺度极差 = {max(vals)-min(vals):.2e}')
print('✅ 练习 1 通过：三行实现，位置项是**绝对距离** —— 这就是 NWD 的全部')"""),

    md("""## ✏️ 练习 2：尺度自适应阈值 + 容忍半径反解

实现 `scale_adaptive_thr(size, r0, tau_min, tau_max)`（让容忍半径恒为 `r0`）
和 `tolerance_radius(size, tau)`（给定阈值反算容忍半径，沿轴位移）。
两者应当互为逆运算（在未被 clip 的区间内）。"""),
    code("""def tolerance_radius(size, tau):
    # TODO: 解 (w-r)/(w+r) = tau
    raise NotImplementedError

def scale_adaptive_thr(size, r0=4.0, tau_min=0.15, tau_max=0.90):
    # TODO: 解 tolerance_radius(size, tau) = r0，再 clip
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert abs(tolerance_radius(8, 0.5) - 8/3) < 1e-12
assert abs(tolerance_radius(256, 0.3) - 256*0.7/1.3) < 1e-9
# 数值验证：把半径代回 IoU 应当恰好等于 tau
for w, t in [(8, 0.5), (32, 0.3), (128, 0.7)]:
    assert abs(float(iou((0,0,w,w), (tolerance_radius(w,t),0,w,w))) - t) < 1e-9
# 互逆性
for w in [8, 16, 32, 64]:
    assert abs(tolerance_radius(w, scale_adaptive_thr(w, r0=4.0)) - 4.0) < 1e-9, w
assert scale_adaptive_thr(4, r0=4.0) == 0.15, '4px 框需要 τ=0 才有 4px 半径 -> 被 tau_min 截断'
assert scale_adaptive_thr(1000, r0=4.0) == 0.90, '大框被 tau_max 截断（有意为之）'
# 单调性
ts = [scale_adaptive_thr(w) for w in [8, 16, 32, 64, 128]]
assert all(ts[i] <= ts[i+1] for i in range(len(ts)-1))
print(f"{'w':>6s} {'τ(w)':>8s} {'反算半径':>10s}")
for w in [8, 16, 32, 64, 256]:
    t = scale_adaptive_thr(w)
    print(f'{w:>6d} {t:>8.3f} {tolerance_radius(w, t):>10.2f}')
print('✅ 练习 2 通过：阈值表要**从设计目标反解**，不要拍脑袋定')"""),

    md("""## ✏️ 练习 3：EIoU

实现 `my_eiou(pred, gt)`：
`EIoU = IoU − ρ²(中心)/c² − (w−w_g)²/c_w² − (h−h_g)²/c_h²`，
其中 c 是最小外接框的对角线长度、c_w / c_h 是外接框的宽和高。可以调用已有的 `iou` / `_enclose`。"""),
    code("""def my_eiou(pred, gt):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert abs(float(my_eiou((10,10,20,20), (10,10,20,20))) - 1.0) < 1e-9, '完全重合 = 1'
# 与参考实现对拍
A = rng.uniform(0, 60, size=(60, 4)) + np.array([0,0,2,2])
B = rng.uniform(0, 60, size=(60, 4)) + np.array([0,0,2,2])
assert np.allclose(my_eiou(A, B), eiou(A, B), rtol=1e-9, atol=1e-12)
# 关键性质：长宽比相同但尺寸差 5 倍时，EIoU 远强于 CIoU
pb, gs = (0.,0.,40.,40.), (0.,0.,8.,8.)
assert abs(float(_v_aspect(pb, gs))) < 1e-15
assert float(my_eiou(pb, gs)) < float(ciou(pb, gs)) - 1.0
# 不相交时仍有梯度（值随距离单调下降）
vs = [float(my_eiou((d,0.,8.,8.), (0.,0.,8.,8.))) for d in [10, 20, 40, 80]]
assert all(vs[i] > vs[i+1] for i in range(len(vs)-1)), '不相交时仍单调 -> 有梯度'
print(f'EIoU(40x40 vs 8x8, 中心重合) = {float(my_eiou(pb, gs)):.4f}  '
      f'vs CIoU = {float(ciou(pb, gs)):.4f}')
print(f'不相交时随距离: {[round(v,4) for v in vs]}')
print('✅ 练习 3 通过：EIoU 修掉了 CIoU 的两个毛病（1/(w²+h²) 与「比例对了就不管」）')"""),

    md("""## ✏️ 练习 4：scale-aware 权重（均值归一化）

实现 `scale_aware_weights(sizes, gamma, s_ref=None, w_max=None)`：
`w_i ∝ (s_ref/s_i)^gamma`，然后**归一化使权重均值恰为 1**（保持总梯度尺度不变）；
若给了 `w_max`，先把 `(s_ref/s_i)^gamma` 截断到 `w_max` 再归一化。
`s_ref` 缺省用 `sizes` 的中位数。"""),
    code("""def scale_aware_weights(sizes, gamma, s_ref=None, w_max=None):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
sz = np.array([8., 8., 16., 32., 64., 128.])
w0 = scale_aware_weights(sz, 0.0)
assert np.allclose(w0, 1.0), 'gamma=0 时所有权重都是 1'
w = scale_aware_weights(sz, 0.5)
assert abs(w.mean() - 1.0) < 1e-12, '**必须归一化使均值为 1**'
assert w[0] > w[-1], '小目标权重更大'
assert np.all(np.diff(w) <= 1e-12), '权重随尺寸单调不增'
wc = scale_aware_weights(sz, 2.0, w_max=4.0)
assert abs(wc.mean() - 1.0) < 1e-12
assert wc.max() / wc.min() <= 4.0 / (min(1.0, (np.median(sz)/sz.max())**2)) + 1e-9
# 截断确实生效：不截断时比值更大
wnc = scale_aware_weights(sz, 2.0)
assert wnc.max()/wnc.min() > wc.max()/wc.min()
print(f"{'尺寸':>7s} {'γ=0':>8s} {'γ=0.5':>8s} {'γ=1.0':>8s} {'γ=2.0(截断4)':>13s}")
w1 = scale_aware_weights(sz, 1.0)
for i, s in enumerate(sz):
    print(f'{s:>7.0f} {w0[i]:>8.3f} {w[i]:>8.3f} {w1[i]:>8.3f} {wc[i]:>13.3f}')
print('✅ 练习 4 通过：**归一化 + 截断** 是让 scale-aware 加权可控的两个必备开关')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def my_nwd(a, b, C=12.8):
    a_, b_ = np.asarray(a, float), np.asarray(b, float)
    mu_a, mu_b = a_[..., :2], b_[..., :2]           # 高斯均值 = 框中心
    s_a,  s_b  = a_[..., 2:] / 2.0, b_[..., 2:] / 2.0   # Sigma^{1/2} = diag(w/2, h/2)
    w2 = ((mu_a - mu_b) ** 2).sum(-1) + ((s_a - s_b) ** 2).sum(-1)
    return np.exp(-np.sqrt(w2) / C)"""),
    code("""# 练习 2 参考答案
def tolerance_radius(size, tau):
    return size * (1.0 - tau) / (1.0 + tau)

def scale_adaptive_thr(size, r0=4.0, tau_min=0.15, tau_max=0.90):
    return float(np.clip((size - r0) / (size + r0), tau_min, tau_max))"""),
    code("""# 练习 3 参考答案
def my_eiou(pred, gt):
    p, g = np.asarray(pred, float), np.asarray(gt, float)
    x1, y1, x2, y2 = _enclose(pred, gt)
    cw, ch = np.maximum(x2 - x1, 1e-12), np.maximum(y2 - y1, 1e-12)
    rho2 = (p[...,0]-g[...,0])**2 + (p[...,1]-g[...,1])**2
    return (iou(pred, gt) - rho2/(cw**2 + ch**2)
            - (p[...,2]-g[...,2])**2/cw**2 - (p[...,3]-g[...,3])**2/ch**2)"""),
    code("""# 练习 4 参考答案
def scale_aware_weights(sizes, gamma, s_ref=None, w_max=None):
    s = np.asarray(sizes, dtype=float)
    ref = float(np.median(s)) if s_ref is None else float(s_ref)
    w = (ref / np.maximum(s, 1e-12)) ** gamma
    if w_max is not None:
        w = np.minimum(w, float(w_max))
    return w / w.mean()                     # 归一化：保持总梯度尺度不变"""),

    md("""---
## 🧪 真实工程胶囊：把 NWD 装进现有检测器"""),
    code("""RECIPE = r'''
# ============================================================================
# 小目标 · 分配与损失配置清单（按 ② -> ① -> ③ 的顺序做）
# ============================================================================

# ---- ② 换度量：NWD（改动最小、收益最确定）------------------------------------
import torch

def nwd(a, b, C=12.8, eps=1e-7):
    # a, b: (..., 4) 的 (cx, cy, w, h)，像素坐标。返回 (0, 1] 的相似度。
    mu = (a[..., :2] - b[..., :2]).pow(2).sum(-1)
    sg = ((a[..., 2:] - b[..., 2:]) / 2).pow(2).sum(-1)
    return torch.exp(-(mu + sg).clamp(min=eps).sqrt() / C)

# C 怎么定：取训练集所有 GT 的 sqrt(w*h) 的**均值**（不是中位数）
#   C = float(np.sqrt(gt_w * gt_h).mean())        # TSR 上典型 12~16
# tau 怎么定：由 r = -C*ln(tau) 反推
#   要求 r >= stride/2（网格量化） + 2px（标注抖动）
#   stride 8 -> r >= 6  ->  tau <= exp(-6/12.8) = 0.626   取 0.5~0.6

# ⚠️ 纯 NWD 会伤大目标（位置项是绝对距离，对大框区分度不足）。两种混合方式：
ALPHA = 0.7                                   # 按小目标占比设，TSR 上 0.5~0.8
metric = (1 - ALPHA) * iou(a, b) + ALPHA * nwd(a, b, C)         # ① 加权混合
# metric = torch.where(gt_size < 32, nwd(a,b,C), iou(a,b))      # ② 按尺寸切换

# 装进 MMDetection 的 assigner（把 IoUCalculator 换掉即可）
assigner = dict(type='MaxIoUAssigner', iou_calculator=dict(type='NWDCalculator', C=12.8),
                pos_iou_thr=0.5, neg_iou_thr=0.4, min_pos_iou=0.3)
# ATSS / SimOTA 同理：只换内部的 iou_calculator，自适应逻辑一行不改
# ⚠️ SimOTA 还要给 dynamic-k 设下界： k = max(3, round(topq.sum()))

# 回归损失也换（处处可导，不相交仍有梯度）
loss_bbox = dict(type='NWDLoss', C=12.8, loss_weight=2.0)   # L = 1 - NWD
# 或保守做法： loss = 0.5*(1-NWD) + 0.5*EIoULoss

# NMS 里的 IoU 同样不公平 —— 两个 8px 框相距 5px，IoU 只有 0.1 会被当两个目标
nms = dict(type='nwd_nms', C=12.8, iou_threshold=0.55)      # 显著减少小目标重复框

# ---- ① 改分配：保底 k（RFLA 的 HLA 思想，两行）-------------------------------
#   pos = (metric >= tau).nonzero()
#   if pos.numel() < K_MIN: pos = metric.topk(K_MIN).indices     # 保底
# 目的：避免某些 GT 完全没有正样本 —— 它们的位置会被当**负样本**训练，
#       模型被主动教育「这里没有目标」，比单纯漏掉更糟。

# ---- ③ 调损失：scale-aware 加权 + Focal 参数回调 ------------------------------
GAMMA_SCALE = 0.35                     # ∈ [0.25, 0.5]，不是 1 更不是 2
w = (s_ref / gt_size).clamp(max=4.0) ** GAMMA_SCALE
w = w / w.mean()                       # ← **必须归一化**，否则等于偷偷改了学习率
loss_reg = (w * per_sample_reg_loss).mean()     # 只加权**回归**，不加权分类

loss_cls = dict(type='FocalLoss', gamma=1.5, alpha=0.4)   # 从 (2.0, 0.25) 回调
# ⚠️ 小目标场景最"难"的负样本往往是**漏标的真实目标** ->
#    gamma=2 会最用力地训练模型把真目标压成背景。
# ✅ 更根本：把低于标注下限（如 <8px）的区域标成 ignore（既不算正也不算负）

# ---- 验证清单（每一项都要在合成数据上先跑通再上真数据）------------------------
#   [ ] nwd(x, x) == 1.0 ；nwd 恒 > 0
#   [ ] 相同绝对位移下，不同尺寸框的 NWD **完全相同**（这是恒等式）
#   [ ] 8px GT vs 32px anchor 中心重合时 NWD < 0.5（Σ 项没写漏）
#   [ ] 换 NWD 前后，统计每个 GT 的正样本数直方图 —— 小目标那一端应明显抬升
#   [ ] **分尺寸桶评测**：AP_[0,8) / AP_[8,16) / AP_[16,32) / AP_[32,96) / AP_96+
#       只看总 mAP 的话，"AP_s +4 / AP_l −1" 会显示成 +0.3（看起来像噪声）
#   [ ] 大目标是否掉点？掉了就调 ALPHA 或改成按尺寸切换

# ---- 反模式清单 ---------------------------------------------------------------
#   ✗ 直接把 IoU 阈值从 0.5 降到 0.3（8px 够了，但 256px 框的容忍半径变成 138px）
#   ✗ 照搬 AI-TOD 的纯 NWD 配置到有大目标的数据集（那个数据集没有大目标）
#   ✗ 用未修正的 CIoU（1/(w²+h²) 在归一化坐标下会梯度爆炸）
#   ✗ scale-aware 权重不归一化（总梯度尺度改变 = 偷偷改学习率）
#   ✗ 分类和回归同时加 scale 权重（与 Focal 的隐式加权叠加 = 过度）
#   ✗ 只改损失不改分配（第③层是在已有正样本集合上微调，度量错了它救不回来）
'''
print(RECIPE)
for key in ['def nwd', 'ALPHA', 'k = max(3', 'NWDLoss', 'nwd_nms', 'K_MIN',
            'w / w.mean()', 'gamma=1.5', 'ignore', '分尺寸桶评测', '反模式']:
    assert key in RECIPE, key
print('✅ 配方覆盖：换度量 -> 混合防大目标掉点 -> 保底 k -> 加权与 Focal 回调 -> 分桶验证')"""),

    md("""### 小结

- **IoU 是相对度量，小目标面对的威胁是绝对像素量**（网格量化 ±4 px、标注抖动 ±2 px）。
  用相对度量衡量绝对误差，就是整个问题的根源。IoU 的位移灵敏度 = **4/w**。
- **NWD 三行就能实现**：框 → 2D 高斯（Σ = diag(w²/4, h²/4)）→ W₂² = 把框写成
  `[cx, cy, w/2, h/2]` 后的欧氏距离平方 → `exp(−√W₂²/C)`。
  它的灵敏度恒为 **√2/C**，与框大小**完全无关**（是恒等式，不是近似）。
- **三个关键性质**：① 相同绝对位移 → 相同相似度；② 不相交仍有梯度，且
  **惩罚放大预测框**（GIoU 恰好相反，它奖励放大）；③ 处处光滑、等值面是正圆。
- **决定性数字**：stride 8 网格上，即使 anchor 尺寸完美匹配，
  **8 px 目标在 IoU@0.5 下只有 ~25% 能匹配上**（16 px 85%，32 px 100%）；NWD@0.5 下是 100%。
- **NWD 不是免费的**：位置项是绝对距离 ⇒ 对大目标区分度不足。
  **必须混合**（`(1−α)·IoU + α·NWD`，α = 0.5–0.8）或按尺寸切换。照搬 AI-TOD 的纯 NWD 会掉点。
- **RFLA 的公平性不来自 KLD，而来自「拿感受野当参考分布」**——KLD 方向搞反
  （用 GT 当参考）会让位置项 ∝ 1/w²，**比 IoU 还不公平**。它真正值得抄的是 **HLA 的保底 k**。
- **任何以 IoU 为内部度量的自适应机制都会继承 IoU 的偏见**：ATSS 在极小目标上退化成
  「top-k 全收但质量极差」；**SimOTA 的 dynamic-k 对小目标方向是反的**（8 px 给 k=2，128 px 给 k=7）。
  修法都是「把内部的 IoU 换成 NWD」。
- **IoU 变体选择**：避开纯 GIoU（奖励放大）与未修正的 CIoU
  （∂v/∂w ∝ 1/w，8 px 比 200 px 大 25 倍；且长宽比一致时 v ≡ 0，大 5 倍也不罚）；
  用 **EIoU** 或 **1 − NWD**。**归一化坐标下的 L1 会把小目标的损失打 5 折**。
- **scale-aware 加权的最优 γ 是内点**（本模型 1.4，实操建议 0.25–0.5）：
  修正梯度杠杆（变好）与容量冲突 + 噪声放大（变差）两股力相抗；γ=3 时方差涨 380 倍。
  **必须归一化使均值为 1，且只加权回归**。
- **优先级 ② → ① → ③**：先把尺子换对（改动最小、且分配器内部就在用它），
  再补分配的保底逻辑，最后才微调损失权重。**给出这个排序的理由，比排序本身更能说明水平。**

下一站：**模块 04 · 切片推理与高分辨率策略**——当分配和损失都做对了，
剩下的最后一招是在推理时**提高目标的相对尺寸**。"""),
]
