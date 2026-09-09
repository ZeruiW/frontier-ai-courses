# -*- coding: utf-8 -*-
"""C74 模块 02 · 各向异性高斯基元、协方差参数化与投影。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① <strong>为什么基元是高斯而不是别的形状</strong>（三个性质，缺一不可）；"
                   "② $\\Sigma = RSS^\\top R^\\top$ 为什么恒正定，而四元数为什么不需要显式归一化约束；"
                   "③ 投影的仿射近似（EWA splatting）；"
                   "④ <strong>这个近似什么时候失效——是张角，不是离轴</strong>，"
                   "而且大张角下「真值」根本不存在；"
                   "⑤ $3\\sigma$ 包围半径与 <strong>$\\Sigma'\\mathrel{+}=0.3I$ 这个尺寸相关的低通滤波</strong>；"
                   "⑥ $z\\to0$ 的 $1/z^2$ 病态与近平面剔除"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_primitive.ipynb'
                       '（四元数 → 协方差 / 特征值 = scale² / '
                       '<strong>蒙特卡洛验证：53° 张角下投影协方差随样本数发散</strong> / '
                       '有界口径下的误差表 / <strong>膨胀滤波把 1 mm 高斯的足迹放大 14.3×</strong> / '
                       '$1/z^2$ 病态）'),
    ("核心参考", "Zwicker et al., <em>EWA Splatting</em>（TVCG 2002，仿射近似的出处）· "
                 "Zwicker et al., <em>Surface Splatting</em>（SIGGRAPH 2001）· "
                 "Kerbl et al., <em>3D Gaussian Splatting</em>（SIGGRAPH 2023，§5.1 与 §5.3）· "
                 "Yu et al., <em>Mip-Splatting</em>（CVPR 2024，把这里的低通滤波做对）· "
                 "Shoemake, <em>Animating Rotation with Quaternion Curves</em>（SIGGRAPH 1985）· "
                 "本课程 <strong>C72</strong> 模块 01（相机模型与投影的雅可比）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-gaussian", "为什么基元是高斯：三个性质，缺一不可", "".join([
        P("这不是「因为高斯常见」。3DGS 的整条流水线依赖高斯的三个具体性质，"
          "换成球、立方体、超椭球中的任何一个都会断掉其中一条。"),
        TABLE(["性质", "具体说什么", "缺了它会怎样"], [
            ["<strong>① 仿射变换下仍是高斯</strong>",
             "$x\\sim\\mathcal N(\\mu,\\Sigma)$，则 $Ax+b\\sim\\mathcal N(A\\mu+b, A\\Sigma A^\\top)$",
             "<strong>投影就没有闭式解了</strong>。"
             "<em>这一条让「3D 椭球 → 屏幕椭圆」变成一次 $2\\times3$ 矩阵乘法，"
             "而不是求交或数值积分</em>"],
            ["<strong>② 处处 $C^\\infty$ 可微</strong>",
             "$\\exp(-\\frac12 d^\\top\\Sigma^{-1}d)$ 对 $\\mu,\\Sigma$ 的梯度是解析的、无处为零",
             "<strong>梯度下降没法移动它</strong>。"
             "<em>硬边基元（球、盒）的边界处梯度是 delta 函数，"
             "而内部梯度恒为 0——高斯的「软」是可优化性的前提</em>"],
            ["<strong>③ 指数衰减 → 有效局部支撑</strong>",
             "$3\\sigma$ 外的贡献只剩 $e^{-4.5}=1.1\\%$，$4\\sigma$ 外 $3.4\\times10^{-4}$",
             "<strong>不能分箱、不能提前终止</strong>。"
             "<em>严格说高斯的支撑是无界的，但它<strong>数值上</strong>是局部的——"
             "这一条让模块 03 的 tile 分箱成立</em>"],
        ]),
        DUAL(
            "<strong>第三条值得多说一句，因为它是一个「近似被当成事实」的地方。</strong>"
            "<em>高斯在数学上处处非零，所以「每个高斯只影响它周围的几个 tile」严格来说是错的</em>。"
            "<strong>3DGS 在 $3\\sigma$ 处截断，而 $3\\sigma$ 处的 $\\alpha$ 衰减因子是 $e^{-4.5} = 0.0111$</strong>——"
            "<em>对 $\\alpha^{(g)} \\le 0.35$ 的高斯，这已经低于 8 bit 的一个色阶 $1/255 = 0.0039$；"
            "但对 $\\alpha^{(g)} = 0.9$ 的高斯，$0.9\\times0.0111 = 0.01$ 仍是 2.5 个色阶</em>。"
            "<strong>所以 $3\\sigma$ 截断在高不透明度的高斯上会留下可见的硬边</strong>，"
            "<em>这是一类真实存在的伪影</em>。",
            "<strong>而三条性质里没有一条要求「各向同性」。</strong>"
            "<em>3DGS 用<strong>各向异性</strong>高斯（三个轴长可以差几个数量级），"
            "而这正是它比早年的 point-based rendering 强的地方</em>："
            "<strong>一个扁平的椭球可以精确地对齐到一个表面上</strong>——"
            "<em>轴长比 100:100:1 的高斯就是一个「有厚度的面片」，"
            "而墙面、桌面、地面在真实场景里占绝大多数</em>。"
            "<strong>代价是参数从 1 个半径变成 6 个自由度，"
            "而这 6 个自由度怎么参数化就是下一节的题目。</strong>"),
    ])),

    # ============================================================== 2
    ("param", "协方差的参数化：为什么是 $RSS^\\top R^\\top$", "".join([
        P("$\\Sigma$ 是 $3\\times3$ 对称正定矩阵，6 个自由度。"
          "一个自然但**错误**的做法是存这 6 个分量直接优化。"),
        MATH(r"\Sigma = R(q)\,S\,S^\top R(q)^\top,\qquad S = \mathrm{diag}(s_1,s_2,s_3)"),
        TABLE(["做法", "存什么", "扰动尺度 0.01 时非正定的比例", "扰动 0.10 时"], [
            ["直接存 $\\Sigma$", "6 个分量", "<strong>71.4%</strong>", "<strong>94.3%</strong>"],
            ["存 $(s, q)$ 再算 $RSS^\\top R^\\top$", "3 + 4 = 7 个数",
             "<strong>0%</strong>", "<strong>0%</strong>"],
        ]),
        DUAL(
            "<strong>右边那个 0% 不是「概率很小」，它是一个恒等式。</strong>"
            "<em>$\\Sigma = MM^\\top$ 其中 $M = RS$；只要 $s_i \\ne 0$，$M$ 满秩，"
            "于是对任意 $v\\ne0$ 有 $v^\\top MM^\\top v = \\Vert M^\\top v\\Vert^2 > 0$</em>。"
            "<strong>正定性被<em>编码进了参数化</em>，而不是靠惩罚项或投影去维持</strong>——"
            "<em>这是一个通用的设计手法：把约束写进参数化，"
            "优化器就再也不可能违反它</em>（$\\alpha$ 存 logit、$s$ 存 $\\log s$ 是同一手法）。",
            "<strong>而 $\\Sigma$ 的特征值恰好是 $s_i^2$，特征向量是 $R$ 的列</strong>——"
            "<em>所以 $(s,q)$ 就是 $\\Sigma$ 的特征分解，只是换了个存法</em>。"
            "<strong>这也解释了为什么 7 个数能表示 6 个自由度：$q$ 有 4 个分量但只有 3 个自由度</strong>，"
            "<em>而 3DGS <strong>不加</strong> $\\Vert q\\Vert=1$ 的约束——它在用 $q$ 之前先归一化。"
            "所以 $q$ 与 $\\lambda q$ 给出同一个旋转，参数空间里有一条「无所谓」的方向，"
            "梯度在那个方向上是零，优化器不会往那走</em>。"),
        H3("三个量都不是直接存的"),
        TABLE(["量", "存的是", "用时的变换", "为什么"], [
            ["$s$（缩放）", "$\\log s$", "$\\exp(\\cdot)$",
             "<strong>保证 $s>0$</strong>；而且尺度跨几个数量级时 $\\log$ 空间的梯度更均衡"],
            ["$q$（旋转）", "4 个自由分量", "先归一化",
             "避免显式约束；<em>模长的梯度为零，所以模长会随机漂移但无害</em>"],
            ["$\\alpha$（不透明度）", "logit", "$\\mathrm{sigmoid}(\\cdot)$",
             "<strong>保证 $\\alpha\\in(0,1)$，且永远到不了 1</strong>——"
             "<em>这正好挡住了模块 01 里 $1/(1-\\alpha)$ 的病态</em>"],
        ]),
        CALLOUT("intuition",
                "<strong>一句话：3DGS 里没有一个「有约束」的参数。</strong>"
                "<em>每个约束都通过一个单调变换被吸收进了参数化，"
                "于是优化器可以在无约束的 $\\mathbb R^{59}$ 上自由走动</em>。"
                "<strong>代价是梯度要过一次链式法则（$\\partial s/\\partial(\\log s) = s$），"
                "以及学习率的含义变成了「相对变化」而不是「绝对变化」</strong>——"
                "<em>所以官方实现对 $\\log s$ 与 $\\mu$ 用了<strong>不同</strong>的学习率"
                "（0.005 vs 0.00016×场景尺度）</em>。"),
    ])),

    # ============================================================== 3
    ("project", "投影：仿射近似（EWA splatting）", "".join([
        P("性质 ① 说的是**仿射**变换下高斯保持高斯。但透视投影 "
          "$\\pi(x,y,z) = (fx/z,\\, fy/z)$ **不是**仿射的。"
          "EWA splatting 的做法：在高斯中心处把 $\\pi$ 线性化。"),
        MATH(r"J = \frac{\partial \pi}{\partial (x,y,z)}\Bigg|_{\mu_c}"
             r" = \begin{bmatrix} f/z & 0 & -fx/z^2 \\ 0 & f/z & -fy/z^2\end{bmatrix},"
             r"\qquad \Sigma' = J\,\Sigma\,J^\top"),
        ASCII("""
   完整链路（世界 -> 屏幕）：

   Σ_world  --[W: 相机外参旋转]-->  Σ_cam  --[J: 投影雅可比]-->  Σ'_screen
      3x3                            3x3                         2x2

   Σ' = J W Σ Wᵀ Jᵀ = (JW) Σ (JW)ᵀ        <- 两步可以合成一个 2x3 矩阵

   官方实现里就是这么写的：
     T = glm::mat3(W) * J;   cov2D = transpose(T) * transpose(Vrk) * T;
        """),
        DUAL(
            "<strong>$J$ 的前两列是缩放 $f/z$（近大远小），第三列是「深度差引起的横向位移」。</strong>"
            "<em>$-fx/z^2$ 的含义：一个在深度上偏了 $\\Delta z$ 的点，"
            "在屏幕上会横向移动 $-fx\\Delta z/z^2$——"
            "因为它离主光轴越远（$x$ 越大），深度变化引起的视线角变化就越大</em>。"
            "<strong>所以第三列在光轴上（$x=y=0$）恰好为零</strong>——"
            "<em>光轴上的高斯，它的深度延展完全不影响屏幕上的形状</em>。",
            "<strong>而这解释了一个容易误判的现象：一个沿深度方向很长的针状高斯，"
            "放在画面中心时投影成一个小点，挪到画面角落时投影成一条长条。</strong>"
            "<em>这不是 bug，是 $J$ 第三列的正确行为——"
            "远离光轴时，深度延展<strong>真的</strong>会在屏幕上表现为横向延展</em>。"
            "<strong>不过要注意：这一条是「仿射近似<em>内部</em>的正确行为」，"
            "而近似本身什么时候整体失效是另一个问题</strong>——下一节。"),
    ])),

    # ============================================================== 4
    ("failure", "近似何时失效：是张角，不是离轴——而且大张角下「真值」不存在", "".join([
        P("直觉的猜测是「离画面中心越远越不准」。**这个猜测是错的**，"
          "或者说它抓错了主变量。真正的主变量是高斯的**张角** "
          "$\\theta = 2\\arctan(\\sigma/z)$——它在屏幕上占多大的角度。"),
        H3("先说一个更强的结论：大张角下，投影后的协方差根本不存在"),
        P("精确投影一个 3D 高斯，得到的**不是**高斯。而当高斯足够大时，"
          "它有一部分质量落在 $z \\le 0$（相机后方或平面上），"
          "而 $z\\to0^+$ 的样本被投影到无穷远。于是二阶矩的积分**发散**。"),
        TABLE(["张角", "$z\\le0$ 的质量", "蒙特卡洛长半轴估计（3 个随机种子）",
               "$n$ 从 $10^4$ 到 $10^6$"], [
            ["0.92°", "0", "4.8 / 4.8 / 4.8 px", "<strong>稳定</strong>"],
            ["11.42°", "0", "61.0 / 60.9 / 61.0 px", "<strong>稳定</strong>"],
            ["53.13°", "<strong>2.28%</strong>",
             "$n{=}10^4$: 5634 / 3332 / 12077 px<br>"
             "$n{=}10^6$: <strong>44698 / 138543 / 78873 px</strong>",
             "<strong>随 $n$ 单调增长，且种子间差 3 倍——发散</strong>"],
        ]),
        CALLOUT("paper",
                "<strong>所以「仿射近似在大张角下误差 40%」这句话是<em>没有意义</em>的，"
                "因为它要对比的那个「真值」不存在。</strong>"
                "<em>准确的说法是：仿射近似给出了一个有限的 $\\Sigma'$，"
                "而真实的投影分布是重尾的、没有二阶矩的</em>。"
                "<strong>这不是精度问题，是<em>类型</em>问题。</strong>"),
        H3("换一个有界的口径：真实样本落在「仿射 $3\\sigma$ 椭圆」内的比例"),
        P("这个量总是定义良好的，而且有理论值：若近似完美，应为 "
          "$1-e^{-4.5} = 98.889\\%$。"),
        TABLE(["张角", "离轴 0°", "离轴 45°", "离轴带来的额外偏差"], [
            ["0.92°", "98.910%（+0.02%）", "98.894%（+0.005%）", "0.02%"],
            ["4.58°", "98.844%（−0.05%）", "98.748%（−0.14%）", "0.10%"],
            ["11.42°", "98.481%（<strong>−0.41%</strong>）", "98.027%（<strong>−0.86%</strong>）", "0.45%"],
            ["22.62°", "96.848%（<strong>−2.04%</strong>）", "95.714%（<strong>−3.18%</strong>）", "1.13%"],
            ["53.13°", "85.693%（<strong>−13.20%</strong>）", "85.664%（−13.23%）", "0.03%"],
        ]),
        DUAL(
            "<strong>把两个变量的影响量级摆在一起：</strong>"
            "<em>张角从 0.92° 到 22.62°（24.6 倍）把误差从 0.02% 变成 2.04%（<strong>100 倍</strong>）；"
            "而在固定张角下把离轴角从 0° 变到 45°，误差最多变 1.6 倍（11.42° 与 22.62° 那两行）</em>。"
            "<strong>所以张角是主变量，离轴是次要修正——但离轴的影响<em>不是零</em>，"
            "我要把这一点说准。</strong>"
            "<em>而在 53° 那一行离轴完全不起作用，"
            "因为那时误差已被「有一部分质量在相机后面」这个更粗暴的机制主导</em>。",
            "<strong>工程含义很直接：约束高斯的<em>屏幕尺寸</em>，而不是它的位置。</strong>"
            "<em>官方实现的做法是在密度控制里剪掉屏幕半径超过阈值的高斯"
            "（<code>max_screen_size</code>，默认 20 像素，对应本表的低张角区间），"
            "而<strong>不</strong>对靠边的高斯做任何特殊处理</em>。"
            "<strong>而张角 = 屏幕尺寸/焦距，所以「屏幕半径 < 20 px、$f=600$」对应张角 < 3.8°</strong>——"
            "<em>正好落在上表误差 < 0.05% 的那一档。这个默认值是有依据的，不是随手挑的</em>。"),
    ])),

    # ============================================================== 5
    ("footprint", "从 2D 协方差到屏幕足迹：$3\\sigma$ 半径与那个 $+0.3I$", "".join([
        P("有了 $\\Sigma'$，还要回答两个实现问题：这个椭圆覆盖哪些 tile？"
          "以及——它会不会小到只有半个像素？"),
        H3("包围半径：$r = 3\\sqrt{\\lambda_{\\max}}$"),
        TABLE(["截断处", "椭圆内的质量", "该处的 $\\alpha$ 衰减因子", "对 8 bit 显示的意义"], [
            ["$1\\sigma$", "39.35%", "0.6065", "—"],
            ["$2\\sigma$", "86.47%", "0.1353", "34 个色阶"],
            ["$3\\sigma$", "<strong>98.889%</strong>", "<strong>0.0111</strong>",
             "2.8 个色阶（$\\alpha^{(g)}{=}1$ 时）"],
            ["$4\\sigma$", "99.967%", "$3.35\\times10^{-4}$",
             "<strong>&lt; 1 个色阶，肉眼不可见</strong>"],
        ]),
        P("官方实现用 $3\\sigma$：<code>my_radius = ceil(3.f * sqrt(max(lambda1, lambda2)))</code>。"
          "**这是一个明确的速度/质量取舍**——$4\\sigma$ 会让覆盖面积变成 "
          "$(4/3)^2 = 1.78$ 倍，而模块 03 会量出面积直接决定排序成本。"),
        H3("低通滤波 $\\Sigma' \\mathrel{+}= 0.3\\,I$：一个尺寸相关的滤波器"),
        P("官方代码在算完 $\\Sigma'$ 后加了一行 "
          "<code>cov[0][0] += 0.3f; cov[1][1] += 0.3f;</code>。"
          "它看起来像一个随手加的正则项，其实是**抗锯齿**：一个投影后小于一个像素的高斯"
          "会在相机移动时闪烁（采样频率不够）。加上 $0.3I$ 强制它至少有约一个像素的足迹。"),
        TABLE(["高斯（4 m 处，各向同性）", "长半轴 (px)", "膨胀后 (px)",
               "屏幕足迹 $\\sqrt{\\det\\Sigma'}$", "膨胀后", "面积倍数"], [
            ["$s = 0.30$ m", "45.000", "45.003", "2025.0 px²", "2025.3 px²",
             "<strong>×1.00</strong>"],
            ["$s = 0.01$ m", "1.500", "1.597", "2.250 px²", "2.550 px²", "×1.13"],
            ["$s = 0.003$ m", "0.450", "0.709", "0.2025 px²", "0.5025 px²", "×2.48"],
            ["$s = 0.001$ m", "0.150", "0.568", "0.0225 px²", "0.3225 px²",
             "<strong>×14.33</strong>"],
        ]),
        DUAL(
            "<strong>规律很清楚：这个滤波器对大于一个像素的高斯几乎是恒等变换，"
            "对亚像素的高斯则是「顶到大约一个像素」。</strong>"
            "<em>可以从式子看出为什么：$\\det(\\Sigma'+0.3I) = \\det\\Sigma' + 0.3\\,\\mathrm{tr}\\Sigma' + 0.09$，"
            "所以相对变化是 $0.3\\,\\mathrm{tr}\\Sigma'/\\det\\Sigma' + 0.09/\\det\\Sigma'$——"
            "$\\Sigma'$ 大时可忽略，小时被 $0.09/\\det\\Sigma'$ 主导</em>。"
            "<strong>顺带它还修好了细长高斯的条件数</strong>："
            "<em>轴长比 300:1 的针（45 px × 0.15 px）条件数从 90000 降到 6280（14.3 倍），"
            "而 $\\Sigma'^{-1}$ 是逐像素都要用的</em>。",
            "<strong>但这个滤波器有一个已知的缺陷，而且它是 Mip-Splatting（CVPR 2024）的出发点："
            "$0.3$ 是一个<em>常数</em>，它不随分辨率或相机距离变化。</strong>"
            "<em>于是在训练分辨率下调好的高斯，在放大渲染（或相机靠近）时膨胀量相对变小、"
            "重新出现锯齿；在缩小渲染时膨胀量相对变大、变糊</em>。"
            "<strong>Mip-Splatting 的修法是把它换成一个真正随采样率变化的 3D 平滑滤波 + 2D Mip 滤波</strong>——"
            "<em>所以如果你看到「3DGS 在训练视角很好、换个分辨率就掉」，"
            "这一行常数是首要嫌疑</em>。"),
    ])),

    # ============================================================== 6
    ("2dgs", "把第三个轴压平：2DGS 与它解决的那个矛盾", "".join([
        P("第 1 节说各向异性是 3DGS 的优势，因为真实场景里表面占绝大多数。"
          "把这句话推到极限就得到一个矛盾——"
          "<strong>要精确表示一个表面，第三个轴长应该是 0；"
          "但 $s_3 \\to 0$ 时 $\\Sigma$ 奇异，$\\Sigma'^{-1}$ 不存在。</strong>"),
        DUAL(
            "<strong>3DGS 是靠 $+0.3I$ 绕过这个矛盾的，而这是一个「凑」出来的解法。</strong>"
            "<em>它意味着 3DGS 里没有真正的表面：每个高斯都有一层非零厚度，"
            "而这层厚度在几何上是假的</em>。"
            "<strong>后果在渲染上看不出来（因为 α 合成不在乎），"
            "但在<em>几何</em>上很明显</strong>："
            "<em>从 3DGS 提取网格（C75）时，深度图会因为这层厚度而带偏，"
            "法向也不明确——一个椭球的「法向」是哪一个方向？</em>",
            "<strong>2D Gaussian Splatting（Huang et al., SIGGRAPH 2024）的做法是"
            "换基元：把高斯定义在一个 2D 平面<em>上</em>，只有两个轴长与一个法向。</strong>"
            "<em>于是 ① 法向是显式的、可以直接加正则；"
            "② 渲染时做<strong>射线-平面精确求交</strong>，"
            "完全不需要本模块第 4 节那个仿射近似；"
            "③ 参数从 59 个浮点数降到 58 个（少一个 scale）</em>。"
            "<strong>代价是它表示不了真正的体积性物质</strong>——"
            "<em>烟、雾、毛发、半透明的叶片，在 2DGS 里只能用一叠面片去堆</em>。"),
        TABLE(["", "3DGS（本模块）", "2DGS"], [
            ["基元", "3D 各向异性椭球（3 个轴）",
             "<strong>2D 椭圆面片（2 个轴 + 法向）</strong>"],
            ["投影", "仿射近似 $\\Sigma'=J\\Sigma J^\\top$，"
                     "<em>大张角下失效（第 4 节）</em>",
             "<strong>射线-平面精确求交，无近似</strong>"],
            ["表面几何", "厚度是假的；法向不明确",
             "<strong>法向显式；可加深度-法向一致性正则</strong>"],
            ["体积性物质", "可以表示", "<strong>表示不了</strong>"],
            ["典型用途", "新视角合成（追求 PSNR）",
             "<strong>几何重建、网格提取</strong>（C75）"],
        ]),
        CALLOUT("intuition",
                "<strong>选哪个取决于你要什么：要图好看用 3DGS，要几何准用 2DGS。</strong>"
                "<em>这不是「2DGS 更先进」——它是一个明确的取舍，"
                "而取舍的位置就是本模块第 5 节那个 $+0.3I$ 常数所在的位置</em>。"),
    ])),

    # ============================================================== 7
    ("degenerate", "退化与剔除：$1/z^2$ 的病态", "".join([
        P("$J$ 的第三列含 $1/z^2$，所以 $z\\to0$ 时投影出的椭圆比 $1/z$ 涨得更快。"
          "下面是一个 $s=0.1$ m、中心横向偏 $x=0.2$ m 的高斯："),
        TABLE(["$z$ (m)", "长半轴（实际）", "若只按 $1/z$ 缩放应为", "超出倍数"], [
            ["10.00", "6.0 px", "6.0 px", "1.0×"],
            ["4.00", "15.0 px", "15.0 px", "1.0×"],
            ["1.00", "61.2 px", "60.0 px", "1.02×"],
            ["0.30", "240.4 px", "200.0 px", "1.20×"],
            ["0.10", "1341.6 px", "600.0 px", "<strong>2.24×</strong>"],
            ["0.03", "13482.5 px", "2000.0 px", "<strong>6.74×</strong>"],
        ]),
        DUAL(
            "<strong>所以近平面剔除不是可选的优化，它是数值上的必需。</strong>"
            "<em>官方实现的判据是 <code>if (p_view.z &lt;= 0.2f) return;</code>——"
            "一个 0.2 m 的硬近平面</em>。"
            "<strong>而它剔除的是<em>高斯中心</em>的深度</strong>，"
            "<em>所以一个中心在 0.25 m、$\\sigma=0.3$ m 的大高斯不会被剔除，"
            "但它有很大一部分质量在相机后面——这就是上一节 53° 那一行的情形</em>。",
            "<strong>另外两个必须处理的退化：</strong>"
            "① <strong>$\\det\\Sigma' \\approx 0$</strong>——"
            "<em>正对相机的完美薄片，$\\Sigma'$ 奇异，$\\Sigma'^{-1}$ 不存在。"
            "$+0.3I$ 恰好也顺手解决了这个（上一节的 14.3 倍就是这个情形的边缘）</em>；"
            "② <strong>视锥外剔除</strong>——"
            "<em>官方用中心点 + 一个保守的球半径做视锥测试，"
            "而不是精确的椭球-视锥求交，因为后者太贵而收益很小</em>。"),
        H3("实现上真正存的不是 $\\Sigma'$，而是它的逆"),
        P("渲染时逐像素要算 $\\exp(-\\frac12 d^\\top\\Sigma'^{-1}d)$，"
          "所以存 $\\Sigma'$ 意味着每个像素都要求一次逆。"
          "官方在预处理阶段就把 $\\Sigma'^{-1}$ 算好，"
          "并利用对称性只存三个数（代码里叫 <code>conic</code>）："),
        MATH(r"\Sigma'^{-1} = \frac{1}{\det\Sigma'}"
             r"\begin{bmatrix} \Sigma'_{22} & -\Sigma'_{12} \\ -\Sigma'_{12} & \Sigma'_{11}\end{bmatrix}"
             r"\;\Longrightarrow\; \text{conic} = (a, b, c),\quad"
             r"d^\top\Sigma'^{-1}d = a\,d_x^2 + 2b\,d_x d_y + c\,d_y^2"),
        DUAL(
            "<strong>所以每个高斯在渲染阶段只需要 9 个数："
            "$uv$（2）+ conic（3）+ $\\alpha$（1）+ RGB（3）。</strong>"
            "<em>而模块 03 会用到这个数字：$9 \\times 4 = 36$ 字节 × 200 万个 "
            "(高斯,tile) 对 = 72 MB 的每帧访存</em>。"
            "<strong>球谐的 48 个系数在预处理阶段就被求值成 3 个 RGB 数，"
            "不进入光栅化的内层循环</strong>——"
            "<em>这也是为什么 SH 阶数对<strong>渲染速度</strong>影响很小，"
            "只影响内存与预处理</em>。",
            "<strong>而 conic 的正定性（$a>0$、$c>0$、$ac-b^2>0$）是必须在预处理时保证的。</strong>"
            "<em>$\\det\\Sigma' \\to 0$ 时 conic 的三个数一起爆炸，"
            "而它们会被逐像素使用——一个非正定的 conic 会让 "
            "$\\exp(-\\frac12 d^\\top\\Sigma'^{-1}d)$ 沿某个方向<strong>发散</strong>，"
            "整帧变成 NaN</em>。"
            "<strong>这正是 $+0.3I$ 与 <code>max(0.1f, ...)</code> 两处硬保护要挡的东西。</strong>"),
        CALLOUT("warn",
                "<strong>一个实践中真会遇到的坑：把相机放到场景内部（比如「走进」一个重建好的房间）时，"
                "画面会出现巨大的半透明色块。</strong>"
                "<em>原因就是本节：墙上那些原本很小的高斯，现在 $z$ 只有几厘米，"
                "投影出的椭圆有几千像素宽，而它们仍然通过了 0.2 m 的近平面测试"
                "（因为中心还在 0.2 m 之外）</em>。"
                "<strong>缓解办法是同时按<em>屏幕半径</em>剔除，"
                "而不是只按深度剔除。</strong>"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 02 · 各向异性高斯基元与投影

本 notebook 把讲解页的六个结论跑出来：

1. $\\Sigma = RSS^\\top R^\\top$ 的**特征值恒等于 $s^2$**，且恒正定；
2. 四元数的**模长方向梯度为零** —— 所以不需要显式的 $\\Vert q\\Vert=1$ 约束；
3. 完整投影链路 $\\Sigma' = (JW)\\Sigma(JW)^\\top$；
4. **53° 张角下投影协方差随样本数发散**（真值不存在），
   而有界口径下误差由**张角**主导、离轴只是次要修正；
5. $+0.3I$ 是一个**尺寸相关**的滤波器：对 45 px 的高斯是恒等变换，
   对 0.15 px 的高斯把足迹放大 **14.33×**；
6. $z\\to0$ 时长半轴比 $1/z$ 涨得更快（$z{=}0.03$ 时超出 **6.74×**）。"""),

code("""import numpy as np
print('numpy', np.__version__)

F, CX, CY, W_IMG, H_IMG = 600.0, 320.0, 240.0, 640, 480

def quat_to_R(q):
    '''(w,x,y,z) -> 3x3 旋转矩阵。内部先归一化，所以不要求输入是单位四元数。'''
    q = np.asarray(q, float); q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])

def cov3d(scale, q):
    '''(scale, quat) -> 3x3 协方差 = R S Sᵀ Rᵀ。'''
    M = quat_to_R(q) * np.asarray(scale, float)     # R @ diag(scale)
    return M @ M.T

# R 是不是真的旋转矩阵
for _q in [[1,0,0,0], [0.5,0.5,0.5,0.5], [1,2,3,4], [-0.3,0.9,-0.1,0.2]]:
    R = quat_to_R(_q)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12), f'{_q}: RRᵀ≠I'
    assert abs(np.linalg.det(R) - 1.0) < 1e-12, f'{_q}: det≠1'
print('✓ 四元数 -> R：正交且 det=+1（4 组测试，含未归一化与负 w）')"""),

md("""## 1 · 特征值恒等于 $s^2$，且恒正定

$\\Sigma = (RS)(RS)^\\top$。因为 $R$ 正交，$\\Sigma$ 的特征分解就是 $R\\,\\mathrm{diag}(s^2)\\,R^\\top$ ——
**特征值是 $s_i^2$，特征向量是 $R$ 的列**。所以 $(s,q)$ 就是 $\\Sigma$ 的特征分解换了个存法。"""),

code("""EPS = np.finfo(float).eps
rng = np.random.default_rng(0)
print('随机测 2000 组 (scale, quat)，scale 跨 8 个数量级：')
max_ev_err = 0.0; min_ev = np.inf; worst_ratio = 0.0
for _ in range(2000):
    s = np.exp(rng.uniform(-6, 2, 3))            # e^-6 ~ e^2
    q = rng.normal(0, 1, 4)
    S = cov3d(s, q)
    ev = np.linalg.eigvalsh(S)
    rel = np.max(np.abs(np.sort(ev) - np.sort(s**2)) / np.sort(s**2))
    cond = (s.max()/s.min())**2                  # Σ 的条件数
    max_ev_err = max(max_ev_err, rel)
    worst_ratio = max(worst_ratio, rel/(EPS*cond))
    min_ev = min(min_ev, ev.min())
    assert np.allclose(S, S.T)
print(f'  特征值 vs scale² 的最大**相对**误差 {max_ev_err:.2e}')
print(f'  所有 6000 个特征值的最小值 {min_ev:.3e}  (> 0)')
print(f'  最大的 相对误差/(eps·cond) = {worst_ratio:.1f}')
assert min_ev > 0, '必须恒正定'
assert worst_ratio < 50, '相对误差应在 eps·cond 的常数倍以内'
print('\\n✓ 恒等式成立，而误差的**正确容差是条件数感知的**：')
print('  对称特征求解器对小特征值的相对精度上界是 O(eps · λ_max/λ_min)，')
print('  所以「相对误差 < 1e-9」这种固定阈值只是运气 —— 换一组更极端的 scale 就会失效。')
print(f'  本轮最坏条件数约 {(np.exp(8))**2:.1e}，对应可容忍的相对误差约 {50*EPS*np.exp(16):.1e}')

# 特征向量就是 R 的列
s0 = np.array([0.30, 0.08, 0.05]); q0 = np.array([0.6, -0.3, 0.7, 0.2])
S0 = cov3d(s0, q0)
ev, evec = np.linalg.eigh(S0)
R0 = quat_to_R(q0)
# eigh 按升序返回，而 s0 是降序 -> R0 的列顺序要反过来对
cos_ang = np.abs(evec.T @ R0[:, ::-1])
print(f'\\n特征向量与 R 的列的对齐度（对角线应全为 1）: {np.round(np.diag(cos_ang), 12)}')
assert np.allclose(np.diag(cos_ang), 1.0, atol=1e-10)
print('✓ 特征向量 = R 的列（顺序按特征值排）')"""),

md("""### 1.1 四元数的模长方向梯度为零

3DGS **不加** $\\Vert q\\Vert = 1$ 的约束。理由是 `quat_to_R` 内部先归一化，
所以 $q$ 与 $\\lambda q$ 给出同一个旋转 —— 参数空间里存在一条**完全无所谓**的方向，
而任何损失在那个方向上的梯度必然为零。"""),

code("""def loss_of_q(q, target_S):
    '''任取一个依赖 R 的损失：与目标协方差的 Frobenius 距离。'''
    return float(np.linalg.norm(cov3d([0.3, 0.1, 0.05], q) - target_S, 'fro')**2)

q_test = np.array([0.6, -0.3, 0.7, 0.2])
tgt = cov3d([0.3, 0.1, 0.05], [1, 0.2, -0.1, 0.4])

# 数值梯度
eps = 1e-6
g = np.empty(4)
for i in range(4):
    qp = q_test.copy(); qp[i] += eps
    qm = q_test.copy(); qm[i] -= eps
    g[i] = (loss_of_q(qp, tgt) - loss_of_q(qm, tgt)) / (2*eps)

radial = q_test / np.linalg.norm(q_test)          # 模长方向
comp_radial = float(g @ radial)
print(f'梯度            {np.round(g, 8)}')
print(f'模长方向         {np.round(radial, 6)}')
print(f'梯度在模长方向上的分量  {comp_radial:.3e}')
print(f'梯度总模长              {np.linalg.norm(g):.6f}')
print(f'占比                    {abs(comp_radial)/max(np.linalg.norm(g),1e-30):.2e}')
assert abs(comp_radial) < 1e-5 * max(np.linalg.norm(g), 1e-12) + 1e-7, \\
    '模长方向的梯度必须为零'

# 直接验证：缩放 q 不改变 R
for lam in [0.1, 2.0, 1e4]:
    assert np.allclose(quat_to_R(q_test*lam), quat_to_R(q_test), atol=1e-12)
print('\\n✓ 梯度在模长方向上的分量是 0（相对占比 %.0e）——' % (abs(comp_radial)/np.linalg.norm(g)))
print('  所以优化器不会往那个方向走，模长只会因为数值误差缓慢漂移，而漂移无害')
print('  推论：不需要每步做 renormalize，也不需要加 (||q||-1)² 的惩罚项')

# 但漂移确实会发生：模拟 30000 步的随机漂移
qd = q_test.copy()
r2 = np.random.default_rng(1)
for _ in range(30000):
    qd = qd + r2.normal(0, 1e-3, 4)
print(f'\\n30000 步随机漂移后 ||q|| = {np.linalg.norm(qd):.4f}（初始 {np.linalg.norm(q_test):.4f}）')
print('  ✓ 模长确实漂移了，但归一化后的旋转仍然完全有效 —— 这就是「无害」的含义')"""),

md("""## 2 · 投影：完整链路 $\\Sigma' = (JW)\\,\\Sigma\\,(JW)^\\top$

世界坐标的高斯先过相机外参旋转 $W$，再过投影雅可比 $J$。
两步可以合成一个 $2\\times3$ 矩阵 —— 官方实现就是这么做的。"""),

code("""def proj_J(mu_cam, f=F):
    x, y, z = np.asarray(mu_cam, float)
    assert z > 0, f'高斯必须在相机前方，实得 z={z}'
    return np.array([[f/z, 0.0, -f*x/z**2],
                     [0.0, f/z, -f*y/z**2]])

def project_full(mu_world, Sigma_world, R_wc, t_wc, f=F):
    '''世界 -> 屏幕。R_wc/t_wc 把世界点变到相机系：p_cam = R_wc @ p_world + t_wc。
    返回 (uv, Sigma2, mu_cam)。'''
    mu_cam = R_wc @ np.asarray(mu_world, float) + np.asarray(t_wc, float)
    J = proj_J(mu_cam, f)
    A = J @ R_wc                                   # 2x3，一次合成
    Sigma2 = A @ Sigma_world @ A.T
    uv = np.array([CX + f*mu_cam[0]/mu_cam[2], CY + f*mu_cam[1]/mu_cam[2]])
    return uv, Sigma2, mu_cam

# 一个绕 y 轴转 25°、平移过的相机
ang = np.deg2rad(25.0)
R_wc = np.array([[np.cos(ang), 0, np.sin(ang)],
                 [0, 1, 0],
                 [-np.sin(ang), 0, np.cos(ang)]])
t_wc = np.array([0.1, -0.05, 3.0])
S_w = cov3d([0.30, 0.08, 0.05], [0.9, 0.1, -0.3, 0.2])
mu_w = np.array([0.4, 0.1, 0.6])

uv, S2, mu_c = project_full(mu_w, S_w, R_wc, t_wc)
print(f'mu_cam = {np.round(mu_c, 4)}   uv = ({uv[0]:.2f}, {uv[1]:.2f})')
print('Σ\\' =\\n', np.round(S2, 4))
ev2 = np.linalg.eigvalsh(S2)
print(f'半轴 {np.sqrt(ev2[1]):.2f} / {np.sqrt(ev2[0]):.2f} px')

# 分两步做应该一样
S_c = R_wc @ S_w @ R_wc.T
S2b = proj_J(mu_c) @ S_c @ proj_J(mu_c).T
assert np.allclose(S2, S2b, rtol=1e-12), '合成 (JW) 与分两步必须一致'
assert np.allclose(S2, S2.T) and ev2.min() > 0
# 旋转不改变 3D 的谱
assert np.allclose(np.sort(np.linalg.eigvalsh(S_c)), np.sort(np.linalg.eigvalsh(S_w))), \\
    '相机旋转不该改变 3D 协方差的特征值'
print('\\n✓ (JW) 一次合成 == 分两步；相机旋转不改变 3D 的谱（只改朝向）')

# J 的第三列在光轴上为零
J_axis = proj_J([0.0, 0.0, 4.0])
print(f'\\n光轴上（x=y=0）J 的第三列 = {J_axis[:, 2]}')
assert np.allclose(J_axis[:, 2], 0.0), '光轴上第三列必须为零'
print('✓ 所以光轴上的高斯，深度延展完全不影响屏幕形状')

# 而离轴时不为零：一根沿深度方向的针
needle = cov3d([0.01, 0.01, 0.50], [1, 0, 0, 0])       # 沿 z 很长
for x_off in [0.0, 0.5, 1.5]:
    _, Sn, _ = project_full([0, 0, 0], needle, np.eye(3), [x_off, 0, 4.0])
    e = np.sqrt(np.linalg.eigvalsh(Sn))
    print(f'  沿深度的针，横向偏 {x_off:.1f} m: 屏幕半轴 {e[1]:7.2f}/{e[0]:5.2f} px')
print('  ✓ 画面中心时是个小点，挪到边上就拉成长条 —— J 第三列的正确行为，不是 bug')"""),

md("""## 3 · 近似何时失效：先证明「真值」不存在

精确投影一个 3D 高斯得到的不是高斯。当高斯足够大时，它有一部分质量落在 $z\\le0$，
而 $z\\to0^+$ 的样本被投影到无穷远 —— 二阶矩的积分**发散**。
下面用蒙特卡洛看它是不是真的发散。"""),

code("""import math

def gauss_samples(mu, S, n, seed):
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(S)
    return np.asarray(mu, float) + rng.standard_normal((n, 3)) @ L.T

def mc_semiaxis(mu, S, n, seed):
    '''精确投影 n 个样本，返回屏幕协方差的长半轴估计（px）。'''
    P = gauss_samples(mu, S, n, seed)
    P = P[P[:, 2] > 1e-6]
    uv = np.stack([CX + F*P[:, 0]/P[:, 2], CY + F*P[:, 1]/P[:, 2]], 1)
    return float(np.sqrt(np.linalg.eigvalsh(np.cov(uv.T))[1]))

print('张角 θ = 2·arctan(σ/z)。σ 各向同性，中心在光轴上。\\n')
print(' σ(m)  z(m)  张角     z≤0 的质量    n=1e4 三个种子       n=1e6 三个种子')
stable, diverged = [], []
for sigma, z in [(0.02, 2.5), (0.25, 2.5), (1.25, 2.5)]:
    theta = np.degrees(2*np.arctan(sigma/z))
    p_behind = 0.5*(1 + math.erf(-z/(sigma*np.sqrt(2))))
    S = np.eye(3)*sigma**2
    lo = [mc_semiaxis([0, 0, z], S, 10_000, sd) for sd in range(3)]
    hi = [mc_semiaxis([0, 0, z], S, 1_000_000, sd) for sd in range(3)]
    print(f' {sigma:5.2f} {z:4.1f} {theta:6.2f}°   {p_behind:.2e}   '
          f'{lo[0]:8.1f}/{lo[1]:7.1f}/{lo[2]:7.1f}   {hi[0]:8.1f}/{hi[1]:8.1f}/{hi[2]:8.1f}')
    spread = max(hi)/min(hi)
    growth = np.mean(hi)/np.mean(lo)
    (diverged if (spread > 2 or growth > 2) else stable).append(theta)

print(f'\\n稳定的张角: {[f"{t:.2f}°" for t in stable]}')
print(f'发散的张角: {[f"{t:.2f}°" for t in diverged]}')
assert len(stable) == 2 and len(diverged) == 1
# 具体核对发散那一档
_hi = [mc_semiaxis([0, 0, 2.5], np.eye(3)*1.25**2, 1_000_000, sd) for sd in range(3)]
_lo = [mc_semiaxis([0, 0, 2.5], np.eye(3)*1.25**2, 10_000, sd) for sd in range(3)]
assert np.mean(_hi)/np.mean(_lo) > 5, '样本数 ×100 时估计值必须显著增长'
assert max(_hi)/min(_hi) > 2, '种子间必须差 2 倍以上'
print(f'\\n✓ 53.13° 那一档：n 从 1e4 到 1e6，估计值涨了 {np.mean(_hi)/np.mean(_lo):.1f}×，'
      f'种子间差 {max(_hi)/min(_hi):.1f}×')
print('  这是二阶矩不存在的标准症状 —— 所以「仿射近似在这里误差多少」这个问题**问错了**：')
print('  它要对比的那个「真值」根本不存在。这不是精度问题，是类型问题。')"""),

code("""# 换一个总是有界的口径：真实样本落在「仿射 3σ 椭圆」内的比例
# 若近似完美，理论值 = 1 - exp(-9/2)
THEORY = 1 - np.exp(-4.5)
print(f'理论值 1-exp(-4.5) = {THEORY:.6%}\\n')

def affine_quality(sigma, z, off_deg, n=400_000, seed=1):
    '''真实样本落入仿射 3σ 椭圆的比例（分母含被剔除的 z<=0 样本）。'''
    r = z*np.tan(np.deg2rad(off_deg))
    mu = np.array([r/np.sqrt(2), r/np.sqrt(2), z]) if off_deg > 0 else np.array([0., 0., z])
    S = np.eye(3)*sigma**2
    J = proj_J(mu); Sa = J @ S @ J.T
    uv0 = np.array([CX + F*mu[0]/mu[2], CY + F*mu[1]/mu[2]])
    P = gauss_samples(mu, S, n, seed)
    keep = P[:, 2] > 1e-6
    Pf = P[keep]
    d = np.stack([CX + F*Pf[:, 0]/Pf[:, 2], CY + F*Pf[:, 1]/Pf[:, 2]], 1) - uv0
    m2 = np.einsum('ni,ij,nj->n', d, np.linalg.inv(Sa), d)
    return float((m2 <= 9.0).sum() / n)

print(' 张角      离轴 0°              离轴 45°            离轴带来的额外偏差')
tbl = {}
for sigma in [0.02, 0.10, 0.25, 0.50, 1.25]:
    th = np.degrees(2*np.arctan(sigma/2.5))
    q0 = affine_quality(sigma, 2.5, 0.0)
    q45 = affine_quality(sigma, 2.5, 45.0)
    tbl[round(th, 2)] = (q0, q45)
    print(f' {th:6.2f}°   {q0:8.4%} ({q0-THEORY:+7.4%})   '
          f'{q45:8.4%} ({q45-THEORY:+7.4%})      {abs(q45-q0):.4%}')

e_small = abs(tbl[0.92][0] - THEORY)
e_mid   = abs(tbl[22.62][0] - THEORY)
off_max = max(abs(a-b) for a, b in tbl.values())
print(f'\\n张角 0.92° -> 22.62°（{22.62/0.92:.1f}×）：误差从 {e_small:.4%} 到 {e_mid:.4%}'
      f'，放大 {e_mid/e_small:.0f}×')
print(f'固定张角下离轴 0° -> 45°：误差最多变化 {off_max:.2%}')
assert e_mid/e_small > 30, '张角必须是主变量'
assert off_max < e_mid, '离轴的影响必须小于张角的影响'
assert tbl[22.62][1] < tbl[22.62][0], '同一张角下，离轴确实更差（这一点不是零）'
print('\\n✓ 张角是主变量（放大约 100×），离轴是次要修正（最多 1.6×）——')
print('  但离轴的影响**不是零**，22.62° 那一行 0°->45° 让误差从 2.04% 变到 3.18%')
print(f'\\n工程含义：官方按**屏幕半径**剪枝（max_screen_size=20 px）。')
print(f'  20 px @ f=600 对应张角 2·arctan(20/600) = {np.degrees(2*np.arctan(20/600)):.2f}°，')
print(f'  正好落在误差 < 0.05% 的那一档 —— 这个默认值是有依据的')"""),

md("""## 4 · 屏幕足迹：$3\\sigma$ 半径与那个 $+0.3I$

官方代码算完 $\\Sigma'$ 后有一行 `cov[0][0] += 0.3f; cov[1][1] += 0.3f;`。
它是一个**尺寸相关**的低通滤波器。"""),

code("""print('截断处   椭圆内的质量   该处 α 衰减因子   相当于几个 8bit 色阶')
for k in [1, 2, 3, 4]:
    mass = 1 - np.exp(-k*k/2)
    decay = np.exp(-k*k/2)
    print(f'  {k}σ     {mass:9.6f}      {decay:.6f}         {decay*255:8.2f}'
          + ('   <- < 1 个色阶' if decay*255 < 1 else ''))
assert abs((1-np.exp(-4.5)) - 0.988891) < 1e-6
assert np.exp(-4.5)*255 > 1 and np.exp(-8.0)*255 < 1
print('\\n✓ 3σ 覆盖 98.889% 的质量，但该处 α 衰减因子 0.0111 仍相当于 2.83 个色阶 ——')
print('  所以对 α 接近 1 的高斯，3σ 截断会留下可见的硬边（一类真实伪影）')
print('  4σ 才降到 1 个色阶以下，但覆盖面积要变 (4/3)²=1.78 倍（模块 03：面积决定排序成本）')"""),

code("""def footprint(Sigma2, dilate=0.0):
    '''返回 (3σ 包围半径 px, 屏幕足迹 sqrt(det) px², 条件数)。'''
    S = np.asarray(Sigma2, float) + dilate*np.eye(2)
    ev = np.linalg.eigvalsh(S)
    lo = max(ev[0], 1e-300)
    return 3*np.sqrt(ev[1]), np.sqrt(np.linalg.det(S)), ev[1]/lo

print('各向同性高斯 @ 4 m（f=600）：')
print(' scale(m)  长半轴(px)  膨胀后    足迹(px²)      膨胀后      面积倍数')
for s in [0.30, 0.05, 0.01, 0.003, 0.001]:
    S2_ = proj_J([0, 0, 4.0]) @ cov3d([s, s, s], [1, 0, 0, 0]) @ proj_J([0, 0, 4.0]).T
    r0, a0, _ = footprint(S2_)
    r1, a1, _ = footprint(S2_, 0.3)
    print(f'  {s:6.3f}   {r0/3:9.3f}  {r1/3:8.3f}  {a0:11.5f}  {a1:10.5f}   ×{a1/a0:7.2f}')

_S_big = proj_J([0,0,4.]) @ cov3d([0.30]*3, [1,0,0,0]) @ proj_J([0,0,4.]).T
_S_tiny = proj_J([0,0,4.]) @ cov3d([0.001]*3, [1,0,0,0]) @ proj_J([0,0,4.]).T
_rb = footprint(_S_big, 0.3)[1]/footprint(_S_big)[1]
_rt = footprint(_S_tiny, 0.3)[1]/footprint(_S_tiny)[1]
print(f'\\n45 px 的高斯足迹变 {_rb:.4f}×（几乎恒等），0.15 px 的高斯变 {_rt:.2f}×')
assert _rb < 1.001, '对大高斯必须近乎恒等'
assert _rt > 10, '对亚像素高斯必须显著放大'
print('✓ 这是一个**尺寸相关**的滤波器，而不是一个统一的正则项')
print('  从式子能看出为什么：det(Σ\\'+0.3I) = detΣ\\' + 0.3·trΣ\\' + 0.09')
print('  Σ\\' 大时后两项可忽略；Σ\\' 小时被常数项 0.09 主导 —— 于是「顶到大约一个像素」')

# 顺带修好细长高斯的条件数
print('\\n对细长高斯的条件数：')
for s3 in [0.05, 0.005, 0.001]:
    Sn = proj_J([0,0,4.]) @ cov3d([0.30, s3, s3], [1,0,0,0]) @ proj_J([0,0,4.]).T
    _, _, c0 = footprint(Sn)
    _, _, c1 = footprint(Sn, 0.3)
    print(f'  轴长比 {0.30/s3:5.0f}:1  cond {c0:9.1f} -> {c1:8.1f}   改善 {c0/c1:5.1f}×')
_Sn = proj_J([0,0,4.]) @ cov3d([0.30, 0.001, 0.001], [1,0,0,0]) @ proj_J([0,0,4.]).T
assert footprint(_Sn)[2]/footprint(_Sn, 0.3)[2] > 10
print('  ✓ 而 Σ\\'⁻¹ 是逐像素都要用的，所以条件数直接关系到渲染的数值稳定性')

print('\\n⚠ 但 0.3 是一个**常数**，不随分辨率或距离变化 ——')
print('  于是训练分辨率下调好的高斯，换个分辨率渲染就会重新出现锯齿或变糊。')
print('  这正是 Mip-Splatting (CVPR 2024) 的出发点：把它换成随采样率变化的滤波。')"""),

md("""## 5 · 退化：$1/z^2$ 的病态与近平面剔除

$J$ 的第三列含 $1/z^2$，所以对**离轴**的高斯，$z\\to0$ 时椭圆比 $1/z$ 涨得更快。"""),

code("""S_test = cov3d([0.1, 0.1, 0.1], [1, 0, 0, 0])
print('s=0.1m 的高斯，横向偏 x=0.2m：')
print('   z(m)    长半轴(px)   按 1/z 应为   超出倍数')
for z in [10.0, 4.0, 1.0, 0.3, 0.1, 0.03]:
    Jz = proj_J([0.2, 0.0, z])
    ev = np.linalg.eigvalsh(Jz @ S_test @ Jz.T)
    pred = F*0.1/z
    print(f'  {z:5.2f}   {np.sqrt(ev[1]):10.1f}   {pred:10.1f}    {np.sqrt(ev[1])/pred:6.2f}×')

_J = proj_J([0.2, 0.0, 0.03])
_ratio = np.sqrt(np.linalg.eigvalsh(_J @ S_test @ _J.T)[1]) / (F*0.1/0.03)
assert _ratio > 5, f'z=0.03 时应超出 5 倍以上，实测 {_ratio:.2f}'
# 而在光轴上（x=0）就严格按 1/z
_J0 = proj_J([0.0, 0.0, 0.03])
_r0 = np.sqrt(np.linalg.eigvalsh(_J0 @ S_test @ _J0.T)[1]) / (F*0.1/0.03)
assert abs(_r0 - 1.0) < 1e-9, f'光轴上应严格 ∝1/z，实测 {_r0:.6f}'
print(f'\\n✓ 离轴时 z=0.03 超出 {_ratio:.2f}×，而光轴上严格按 1/z（比值 {_r0:.6f}）——')
print('  证实病态来自 J 的第三列（∝1/z²），而它在光轴上为零')
print('\\n所以近平面剔除是数值上的必需，不是可选优化。')
print('官方判据：if (p_view.z <= 0.2f) return;  —— 一个 0.2 m 的硬近平面')

# 但它剔的是中心深度
print('\\n⚠ 它剔的是**中心**深度。一个中心在 0.25 m、σ=0.3 m 的大高斯：')
_p_behind = 0.5*(1 + math.erf(-0.25/(0.3*np.sqrt(2))))
print(f'  能通过 0.2 m 的测试，但有 {_p_behind:.1%} 的质量在相机后面')
print(f'  这就是第 3 节里「张角 53°」那一档的情形 —— 真值不存在')
assert _p_behind > 0.15
print('\\n缓解办法：同时按**屏幕半径**剔除，而不是只按深度。')
print('（这也解释了「把相机放进重建好的房间里、画面出现巨大半透明色块」的现象）')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 从 (scale, quaternion) 构造协方差

实现 `my_cov3d(scale, q)`：返回 $3\\times3$ 协方差 $RSS^\\top R^\\top$。
要求 **不假设 `q` 是单位四元数**（内部先归一化）。"""),

code("""def my_cov3d(scale, q):
    '''(scale (3,), quat (w,x,y,z)) -> 3x3 协方差。'''
    # TODO: 1) q 归一化，构造 R（公式见本 notebook 的 quat_to_R）
    #       2) M = R @ diag(scale)   —— 提示：R * np.asarray(scale) 就是按列缩放
    #       3) 返回 M @ M.T
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_rg = np.random.default_rng(4)
_cases = [(np.array([1., 1., 1.]), np.array([1., 0, 0, 0])),
          (np.array([0.30, 0.08, 0.05]), np.array([0.6, -0.3, 0.7, 0.2])),
          (np.array([2.0, 0.001, 50.0]), np.array([-1., 2., -3., 4.]))]   # 未归一化
_hard = [(np.exp(_rg.uniform(-6, 2, 3)), _rg.normal(0, 1, 4)) for _ in range(500)]

for _s, _q in _cases + _hard:
    _S = my_cov3d(_s, _q)
    assert _S.shape == (3, 3), f'形状 {_S.shape}'
    assert np.allclose(_S, _S.T, atol=1e-12), '必须对称'
    _ev = np.linalg.eigvalsh(_S)
    assert _ev.min() > 0, f'必须正定，最小特征值 {_ev.min():.3e}'
    _rel = np.max(np.abs(np.sort(_ev) - np.sort(_s**2)) / np.sort(_s**2))
    _cond = (np.max(_s)/np.min(_s))**2
    # 容差必须是条件数感知的：对称特征求解器对小特征值的相对精度是 O(eps·cond)
    assert _rel <= 1e-13 + 100*np.finfo(float).eps*_cond, \\
        f'特征值必须等于 scale²：相对误差 {_rel:.2e}, cond {_cond:.2e}'
    assert np.allclose(_S, cov3d(_s, _q), rtol=1e-10), '应与参考实现一致'

# 缩放 q 不改变结果
_s0, _q0 = _cases[1]
for _lam in [0.01, 3.0, 1e5]:
    assert np.allclose(my_cov3d(_s0, _q0*_lam), my_cov3d(_s0, _q0), rtol=1e-10), \\
        '缩放四元数不该改变协方差'
# 单位 scale + 任意 q -> 单位矩阵（因为 R Rᵀ = I）
assert np.allclose(my_cov3d([1., 1., 1.], _rg.normal(0, 1, 4)), np.eye(3), atol=1e-12), \\
    'scale 全为 1 时，任意旋转都给出 I'
print('✓ 练习 1 通过：503 组（含 scale 比 50000:1、未归一化四元数、各向同性边界）')
print('  注意自测用的是**条件数感知**的容差 1e-13 + 100·eps·cond ——')
print('  那组 scale=[2.0, 0.001, 50.0] 的条件数是 2.5e9，固定阈值 1e-9 在它上面必然失败')"""),

md("""### 📖 参考答案 1"""),

code("""def my_cov3d(scale, q):
    q = np.asarray(q, float); q = q / np.linalg.norm(q)
    w, x, y, z = q
    R = np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])
    M = R * np.asarray(scale, float)          # = R @ diag(scale)
    return M @ M.T

print('参考答案 1 已定义')
print('要点一：R * scale 与 R @ diag(scale) 等价，但前者省一次矩阵乘 ——')
print('       在几十万个高斯上每帧都要算，这个细节有意义。')
print('要点二：正定性不是「大概率成立」，是恒等式。v ᵀMMᵀv = ||Mᵀv||² > 0 只要 M 满秩。')
print('要点三：scale 全为 1 时结果是 I —— 说明各向同性的高斯没有朝向，q 的梯度全为零。')
print('要点四：自测的容差为什么写成 1e-13 + 100·eps·cond 而不是一个固定的小数 ——')
print('       eigvalsh 对**小**特征值的相对精度上界是 O(eps · λmax/λmin)。')
print('       scale 比 50000:1 时 cond=2.5e9，可容忍的相对误差就有 5e-5 量级。')
print('       这类「容差的量纲/尺度选错」是数值代码里最常见的假失败与假通过来源。')"""),

md("""### ✏️ 练习 2 · 完整投影链路

实现 `my_project(mu_world, Sigma_world, R_wc, t_wc, f)`，返回 `(uv, Sigma2, mu_cam)`。
其中 `p_cam = R_wc @ p_world + t_wc`，并要求把 $J$ 与 $W$ **合成一个 $2\\times3$ 矩阵**
再作用到 $\\Sigma$ 上（这是官方实现的做法）。"""),

code("""def my_project(mu_world, Sigma_world, R_wc, t_wc, f=F):
    '''世界 -> 屏幕。返回 (uv (2,), Sigma2 (2,2), mu_cam (3,))。'''
    # TODO: 1) mu_cam = R_wc @ mu_world + t_wc；断言 mu_cam[2] > 0
    #       2) J = [[f/z,0,-f*x/z²],[0,f/z,-f*y/z²]]  用 mu_cam 的 (x,y,z)
    #       3) A = J @ R_wc  （2x3）
    #       4) Sigma2 = A @ Sigma_world @ A.T
    #       5) uv = (CX + f*x/z, CY + f*y/z)
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_ang = np.deg2rad(25.0)
_Rwc = np.array([[np.cos(_ang), 0, np.sin(_ang)], [0, 1, 0],
                 [-np.sin(_ang), 0, np.cos(_ang)]])
_twc = np.array([0.1, -0.05, 3.0])
_Sw = cov3d([0.30, 0.08, 0.05], [0.9, 0.1, -0.3, 0.2])
_muw = np.array([0.4, 0.1, 0.6])
_Siso = cov3d([0.1, 0.1, 0.1], [1, 0, 0, 0])

_uv, _S2, _muc = my_project(_muw, _Sw, _Rwc, _twc)
_uvr, _S2r, _mucr = project_full(_muw, _Sw, _Rwc, _twc)
assert np.allclose(_uv, _uvr) and np.allclose(_S2, _S2r) and np.allclose(_muc, _mucr), \\
    '与参考实现不符'
assert np.allclose(_S2, _S2.T) and np.linalg.eigvalsh(_S2).min() > 0

# 分两步做必须一样
_Sc = _Rwc @ _Sw @ _Rwc.T
_J = np.array([[F/_muc[2], 0, -F*_muc[0]/_muc[2]**2],
               [0, F/_muc[2], -F*_muc[1]/_muc[2]**2]])
assert np.allclose(_S2, _J @ _Sc @ _J.T, rtol=1e-12), '合成必须等于分两步'

# 恒等相机 + 光轴上的各向同性高斯 -> 闭式解 (f/z)²·σ²·I
_uv2, _S22, _ = my_project([0., 0., 5.], _Siso, np.eye(3), np.zeros(3))
assert np.allclose(_uv2, [CX, CY]), '光轴上应投在主点'
_exp = (F/5.0)**2 * 0.01
assert np.allclose(_S22, np.diag([_exp, _exp]), rtol=1e-12), f'应为 {_exp:.4f}·I'

# 相机旋转不改变 3D 的谱
assert np.allclose(np.sort(np.linalg.eigvalsh(_Rwc @ _Sw @ _Rwc.T)),
                   np.sort(np.linalg.eigvalsh(_Sw))), '相机旋转不该改变特征值'
# 相机后方必须报错
try:
    my_project([0., 0., -1.], _Siso, np.eye(3), np.zeros(3))
    raise SystemExit('相机后方的高斯必须被拒绝')
except AssertionError:
    pass
print(f'✓ 练习 2 通过：uv=({_uv[0]:.2f},{_uv[1]:.2f})  '
      f'半轴 {np.sqrt(np.linalg.eigvalsh(_S2)[1]):.2f}/'
      f'{np.sqrt(np.linalg.eigvalsh(_S2)[0]):.2f} px；'
      f'合成==分两步；z<0 被拒绝')"""),

md("""### 📖 参考答案 2"""),

code("""def my_project(mu_world, Sigma_world, R_wc, t_wc, f=F):
    mu_cam = np.asarray(R_wc, float) @ np.asarray(mu_world, float) + np.asarray(t_wc, float)
    x, y, z = mu_cam
    assert z > 0, f'高斯必须在相机前方，实得 z={z}'
    J = np.array([[f/z, 0.0, -f*x/z**2],
                  [0.0, f/z, -f*y/z**2]])
    A = J @ np.asarray(R_wc, float)                 # 2x3，一次合成
    Sigma2 = A @ np.asarray(Sigma_world, float) @ A.T
    uv = np.array([CX + f*x/z, CY + f*y/z])
    return uv, Sigma2, mu_cam

print('参考答案 2 已定义')
print('要点：官方 CUDA 里就是 T = W * J; cov2D = Tᵀ Vrk T 这两行 ——')
print('     合成成 2x3 之后，每个高斯每帧只做一次 2x3 @ 3x3 @ 3x2，而不是两次完整变换。')
print('     顺带：A = J@R_wc 的秩至多是 2，所以 Σ\\' 一定是 2x2 且由 A 的行空间决定 ——')
print('     这就是「深度方向的延展只通过 J 第三列进入屏幕」的矩阵版说法。')"""),

md("""### ✏️ 练习 3 · 屏幕足迹与那个尺寸相关的滤波器

实现 `my_footprint(Sigma2, dilate)`，返回 `(radius_3sigma, area, cond)`：
$3\\sigma$ 包围半径（px）、屏幕足迹 $\\sqrt{\\det(\\Sigma'+dI)}$（px²）、条件数 $\\lambda_{\\max}/\\lambda_{\\min}$。"""),

code("""def my_footprint(Sigma2, dilate=0.0):
    '''返回 (3σ 半径 px, sqrt(det) px², 条件数)。'''
    # TODO: S = Sigma2 + dilate*I
    #       ev = eigvalsh(S)（升序）
    #       返回 (3*sqrt(ev[1]), sqrt(det(S)), ev[1]/ev[0])
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
def _S2_of(scale, z=4.0):
    _J = np.array([[F/z, 0, 0], [0, F/z, 0]])
    return _J @ cov3d(scale, [1, 0, 0, 0]) @ _J.T

_big  = _S2_of([0.30, 0.30, 0.30])
_tiny = _S2_of([0.001, 0.001, 0.001])
_needle = _S2_of([0.30, 0.001, 0.001])

# 与参考实现一致
for _S in [_big, _tiny, _needle, _S2_of([0.05, 0.02, 0.01])]:
    for _d in [0.0, 0.3, 1.0]:
        assert np.allclose(my_footprint(_S, _d), footprint(_S, _d), rtol=1e-10), \\
            f'与参考不符 (dilate={_d})'

# 各向同性 0.30 m @ 4 m：半轴应为 f*0.30/4 = 45 px，半径 135 px
_r, _a, _c = my_footprint(_big)
assert abs(_r - 135.0) < 1e-9, f'3σ 半径应为 135 px，实测 {_r}'
assert abs(_a - 2025.0) < 1e-6, f'足迹应为 2025 px²，实测 {_a}'
assert abs(_c - 1.0) < 1e-12, '各向同性的条件数必须是 1'

# 膨胀是尺寸相关的
_rb = my_footprint(_big, 0.3)[1] / my_footprint(_big)[1]
_rt = my_footprint(_tiny, 0.3)[1] / my_footprint(_tiny)[1]
assert _rb < 1.001, f'对 45 px 的高斯应近乎恒等，实测 ×{_rb:.4f}'
assert _rt > 10, f'对 0.15 px 的高斯应显著放大，实测 ×{_rt:.2f}'
# 有意义的比较对象是「偏离 1 的程度」，而不是两个倍数之比
assert (_rt - 1) / (_rb - 1) > 1e4, \
    f'偏离 1 的程度应差 4 个数量级：{_rt-1:.3e} vs {_rb-1:.3e}'

# 膨胀改善细长高斯的条件数
_c0 = my_footprint(_needle)[2]; _c1 = my_footprint(_needle, 0.3)[2]
assert _c0 > 5e4 and _c1 < 1e4 and _c0/_c1 > 10, \\
    f'条件数应从 {_c0:.0f} 降到 {_c1:.0f}'
# 膨胀不会让任何东西变小
for _S in [_big, _tiny, _needle]:
    assert my_footprint(_S, 0.3)[1] >= my_footprint(_S)[1]
print(f'✓ 练习 3 通过：45 px 高斯足迹变 ×{_rb:.6f}，0.15 px 的变 ×{_rt:.2f}')
print(f'  偏离 1 的程度：{_rb-1:.3e} vs {_rt-1:.3e}，差 {(_rt-1)/(_rb-1):.0f} 倍')
print(f'  针状高斯的条件数 {_c0:.0f} -> {_c1:.0f}（改善 {_c0/_c1:.1f}×）')"""),

md("""### 📖 参考答案 3"""),

code("""def my_footprint(Sigma2, dilate=0.0):
    S = np.asarray(Sigma2, float) + dilate*np.eye(2)
    ev = np.linalg.eigvalsh(S)
    lo = max(ev[0], 1e-300)
    return 3*np.sqrt(ev[1]), float(np.sqrt(np.linalg.det(S))), float(ev[1]/lo)

print('参考答案 3 已定义')
print('要点：det(Σ\\'+dI) = detΣ\\' + d·trΣ\\' + d² —— 这个展开直接说明了尺寸相关性。')
print('     Σ\\' 大时 detΣ\\' 主导（膨胀可忽略）；Σ\\' 小时 d² 主导（顶到约一个像素）。')
print('     所以 0.3 这个数的含义是「最小足迹约 sqrt(0.3)=0.55 px 的标准差」，')
print('     而它是一个常数 —— 这正是 Mip-Splatting 要修的地方。')"""),

md("""### ✏️ 练习 4 · 仿射近似的有界质量口径

实现 `my_quality(sigma, z, off_deg, n, seed)`：生成 `n` 个各向同性高斯样本，
**精确**投影，返回落在「仿射 $3\\sigma$ 椭圆」内的样本比例
（分母是 `n`，即把 $z\\le0$ 被剔除的样本算作「不在椭圆内」）。

理论值 $1-e^{-4.5} = 98.889\\%$。"""),

code("""def my_quality(sigma, z, off_deg, n=200_000, seed=1):
    '''真实样本落入仿射 3σ 椭圆的比例。'''
    # TODO: 1) 中心 mu：off_deg=0 时 (0,0,z)；否则 r=z*tan(off_deg)，
    #          放在 (r/√2, r/√2, z)
    #       2) S = I*sigma²；用 J = proj_J(mu) 算 Sa = J S Jᵀ；uv0 = 投影中心
    #       3) 采样 n 个点（用 gauss_samples(mu,S,n,seed)），只保留 z>1e-6 的
    #       4) 精确投影，算马氏距离平方 m2 = dᵀ Sa⁻¹ d
    #       5) 返回 (m2<=9).sum() / n      <- 分母是 n，不是保留下来的个数
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_TH = 1 - np.exp(-4.5)
_res = {}
for _sg in [0.02, 0.25, 0.50, 1.25]:
    _th = round(np.degrees(2*np.arctan(_sg/2.5)), 2)
    _res[_th] = (my_quality(_sg, 2.5, 0.0, 200_000, 1),
                 my_quality(_sg, 2.5, 45.0, 200_000, 1))

for _th, (_q0, _q45) in _res.items():
    assert 0.0 <= _q0 <= 1.0 and 0.0 <= _q45 <= 1.0, '必须是比例'

# ① 小张角时应非常接近理论值
assert abs(_res[0.92][0] - _TH) < 2e-3, f'0.92° 应接近 {_TH:.4%}，实测 {_res[0.92][0]:.4%}'
# ② 张角越大误差越大（单调）
_errs = [abs(_res[t][0] - _TH) for t in sorted(_res)]
assert all(_errs[i] < _errs[i+1] for i in range(len(_errs)-1)), \\
    f'误差应随张角单调增大，实测 {[f"{e:.4%}" for e in _errs]}'
# ③ 大张角时严重偏低
assert _res[53.13][0] < 0.90, f'53° 时应显著低于 90%，实测 {_res[53.13][0]:.4%}'
# ④ 张角是主变量：它的影响远大于离轴
_span_theta = _errs[-1] / max(_errs[0], 1e-9)
_span_off = max(abs(a-b) for a, b in _res.values())
assert _span_theta > 30, f'张角的影响跨度应 >30×，实测 {_span_theta:.0f}×'
assert _span_off < _errs[-1], '离轴的影响必须小于张角的影响'
# ⑤ 但离轴的影响不是零（在中等张角处最明显）
assert _res[22.62][1] < _res[22.62][0] - 5e-3, \\
    '22.62° 时离轴 45° 应明显更差'
print(f'✓ 练习 4 通过：0.92° 误差 {_errs[0]:.4%} -> 53.13° 误差 {_errs[-1]:.4%}'
      f'（跨 {_span_theta:.0f}×）；离轴最多影响 {_span_off:.2%}')"""),

md("""### 📖 参考答案 4"""),

code("""def my_quality(sigma, z, off_deg, n=200_000, seed=1):
    r = z * np.tan(np.deg2rad(off_deg))
    mu = (np.array([r/np.sqrt(2), r/np.sqrt(2), z]) if off_deg > 0
          else np.array([0.0, 0.0, z]))
    S = np.eye(3) * sigma**2
    J = proj_J(mu)
    Sa = J @ S @ J.T
    uv0 = np.array([CX + F*mu[0]/mu[2], CY + F*mu[1]/mu[2]])
    P = gauss_samples(mu, S, n, seed)
    Pf = P[P[:, 2] > 1e-6]
    d = np.stack([CX + F*Pf[:, 0]/Pf[:, 2], CY + F*Pf[:, 1]/Pf[:, 2]], 1) - uv0
    m2 = np.einsum('ni,ij,nj->n', d, np.linalg.inv(Sa), d)
    return float((m2 <= 9.0).sum() / n)

print('参考答案 4 已定义')
print('要点一：分母必须是 n。若用「保留下来的样本数」当分母，')
print('       就把「有一部分质量在相机后面」这个最严重的失效模式抹掉了。')
print('要点二：为什么要换这个口径 —— 因为大张角下投影协方差不存在（第 3 节），')
print('       所以「协方差的相对误差」这个量根本没有定义。落入比例总是有界的。')
print('要点三：结论是「约束屏幕尺寸，不是约束位置」。官方 max_screen_size=20 px')
print('       对应张角 3.82°，正落在误差 <0.05% 的档内。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 官方实现：参数化（scene/gaussian_model.py）----
class GaussianModel:
    def setup_functions(self):
        self.scaling_activation = torch.exp          # 存 log s
        self.opacity_activation = torch.sigmoid      # 存 logit α
        self.rotation_activation = torch.nn.functional.normalize   # 用时才归一化
    @property
    def get_covariance(self, scaling_modifier=1):
        L = build_scaling_rotation(scaling_modifier * self.get_scaling, self._rotation)
        actual_covariance = L @ L.transpose(1, 2)    # = (RS)(RS)ᵀ，恒正定
# 注意 rotation 用的是 normalize 而不是加约束 —— 练习 1 的「模长梯度为零」就是依据

# 三组参数用了不同的学习率（因为参数化改变了「学习率」的含义）
l = [{'params': [self._xyz],      'lr': position_lr_init * self.spatial_lr_scale},  # 1.6e-4 × 尺度
     {'params': [self._scaling],  'lr': 0.005},     # 对 log s，所以是「相对变化率」
     {'params': [self._rotation], 'lr': 0.001},
     {'params': [self._opacity],  'lr': 0.05}]

# ---- 官方实现：投影（cuda_rasterizer/forward.cu）----
# computeCov2D()：
#   float3 t = transformPoint4x3(mean, viewmatrix);
#   glm::mat3 J = glm::mat3(focal_x / t.z, 0.0f, -(focal_x * t.x) / (t.z * t.z),
#                           0.0f, focal_y / t.z, -(focal_y * t.y) / (t.z * t.z),
#                           0, 0, 0);
#   glm::mat3 T = W * J;
#   glm::mat3 cov = glm::transpose(T) * glm::transpose(Vrk) * T;
#   cov[0][0] += 0.3f;  cov[1][1] += 0.3f;      // ← 练习 3 的那个尺寸相关滤波器
#
# preprocessCUDA()：
#   if (p_view.z <= 0.2f) return;                            // ← 第 5 节的近平面
#   float mid = 0.5f * (cov.x + cov.z);
#   float lambda1 = mid + sqrt(max(0.1f, mid*mid - det));
#   float my_radius = ceil(3.f * sqrt(max(lambda1, lambda2)));   // ← 3σ
# 注意 max(0.1f, ...)：又一处硬夹，防止 det 接近 0 时开根号出 NaN

# ---- 2DGS（几何更准的变体，接 C75 的网格提取）----
# pip install git+https://github.com/hbb1/2d-gaussian-splatting
# 它把第三个 scale 去掉，改成射线-平面精确求交 —— 于是本模块第 3、4 节的
# 仿射近似问题**整体消失**，代价是表示不了体积性物质
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| loss 变 NaN | 协方差是否直接优化；`det` 是否有下限保护 | 直接参数化在扰动 0.01 下已有 71.4% 非正定 |
| 换分辨率渲染就掉点 | `cov += 0.3f` 这一行 | 0.3 是常数，不随采样率变（Mip-Splatting 的出发点） |
| 大高斯边缘形状怪 | 它的**张角**多大 | 张角 22.6° 时误差 2%，53° 时真值已不存在 |
| 相机进入场景内部出现巨大色块 | 是否只按深度剔除 | 近平面剔的是**中心**深度；离轴时误差 ∝ $1/z^2$ |
| 提取的网格有厚度、法向乱 | 是不是该用 2DGS | 3DGS 的第三个轴永远压不到 0（$+0.3I$ 挡着） |
| 高不透明度高斯有硬边 | $3\\sigma$ 截断 | 3σ 处 α 衰减 0.0111，仍相当于 2.8 个 8bit 色阶 |"""),
]
