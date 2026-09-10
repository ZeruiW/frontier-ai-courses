# -*- coding: utf-8 -*-
"""C75 模块 04 · 3D 生成：SDS 与多视角扩散。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① SDS 的梯度为什么<strong>不含 U-Net 的雅可比</strong>，以及那个 $-\\epsilon$ 项去哪了；"
                   "② <strong>SDS 是模式寻求的：它的解是不动点，不是样本</strong>"
                   "（随机版的模式内散布比先验收缩 <strong>8.1 倍</strong>，而<em>精确梯度版严格为 0</em>）；"
                   "③ <strong>它收敛到的模式系统性内移 21.7%</strong>——因为那是「对 $t$ 平均后的平滑密度」的模式；"
                   "④ <strong>CFG 真正买到的是抵消这个内移，而它会过冲</strong>"
                   "（cfg≈3 恰好抵消，cfg=100 时外移到数据分布之外 18%）；"
                   "⑤ Janus 是<strong>目标函数的最优解</strong>，不是优化失败；"
                   "⑥ 多视角扩散怎么从根上改掉它"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_generation.ipynb'
                       '（<strong>用一个解析已知的高斯混合当扩散先验，把 SDS 梯度算到闭式</strong> / '
                       '不动点与它们的稳定性 / <strong>CFG 的两种效应分开量</strong> / '
                       '<strong>一个我踩过的坑：cfg=100 配固定 lr 在 400 步后是 $10^{100}$</strong> / '
                       'Janus 的构造与多视角先验的修法）'),
    ("核心参考", "Poole et al., <em>DreamFusion: Text-to-3D using 2D Diffusion</em>（ICLR 2023，SDS 的出处）· "
                 "Wang et al., <em>Score Jacobian Chaining</em>（CVPR 2023，同期的等价推导）· "
                 "Wang et al., <em>ProlificDreamer / VSD</em>（NeurIPS 2023，把「找模式」改回「采样」）· "
                 "Liu et al., <em>Zero-1-to-3</em>（ICCV 2023，视角条件化）· "
                 "Shi et al., <em>MVDream</em>（ICLR 2024，多视角联合先验）· "
                 "Hong et al., <em>LRM: Large Reconstruction Model</em>（ICLR 2024，前馈路线的对照）· "
                 "本课程 <strong>C28</strong>（扩散与流本身）· C74（被 SDS 优化的那个表示）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("setup", "问题的形状：用一个 2D 先验去雕一个 3D 表示", "".join([
        ASCII("""
   3D 生成（SDS 路线）的循环：

   θ  ──[可微渲染]──>  x = g(θ)  ──[加噪]──>  x_t
   ↑                                            │
   │                                    [预训练的 2D 扩散]
   │                                            │
   └──────────  梯度  <────────────  ε̂(x_t, t, y) - ε

   θ ：一个 3D 表示的参数（NeRF 的权重、或 C74 的一堆高斯）
   g ：可微渲染器（C74 模块 03 就是它的一种）
   y ：文字提示（或一张参考图）

   关键点：**扩散模型完全不知道 3D 的存在**。它只被要求「这张渲出来的图像不像噪声」。
        """),
        DUAL(
            "<strong>所以 SDS 的全部内容是一句话：把「渲出来的每一张图都要像真实图像」"
            "当成对 3D 表示的约束。</strong>"
            "<em>而它的适用条件很宽——不需要任何真实观测，"
            "所以它能做「只有文字」或「只有一张图」的情形</em>。"
            "<strong>这与前三个模块有一个性质上的差别："
            "① SfM、② MVS、③ 前馈都在拟合<em>看到过的</em>图像，"
            "而 SDS 在生成<em>没看到过的</em>部分。</strong>",
            "<strong>后果是「对不对」这个问题没有客观判据。</strong>"
            "<em>模块 01–03 的误差都能对着真值算；"
            "SDS 生成的背面本来就不存在真值，所以只能问「它像不像先验认为合理的东西」</em>。"
            "<strong>而这决定了本模块的分析方式："
            "不去问「生成得好不好」，而去问「这个目标函数的最优解是什么形状」</strong>——"
            "<em>而那是可以精确回答的，本模块就这么做</em>。"),
    ])),

    # ============================================================== 2
    ("gradient", "SDS 的梯度：那个 $-\\epsilon$ 项与消失的雅可比", "".join([
        P("朴素想法是「把扩散模型的损失当成一个可微的图像评分，直接反传」。"
          "而扩散损失 $\\mathcal L_{\\text{diff}} = \\mathbb E\\Vert \\hat\\epsilon(x_t,t) - \\epsilon\\Vert^2$ "
          "对 $x$ 求导会带上 $\\partial\\hat\\epsilon/\\partial x_t$——**U-Net 的雅可比**，"
          "既贵又不稳。SDS 的做法是**把它扔掉**："),
        MATH(r"\nabla_\theta \mathcal L_{\text{SDS}}"
             r"= \mathbb E_{t,\epsilon}\Bigl[w(t)\bigl(\hat\epsilon(x_t,t,y) - \epsilon\bigr)"
             r"\frac{\partial x}{\partial \theta}\Bigr]"),
        DUAL(
            "<strong>扔掉雅可比不是近似——它对应一个<em>不同但合理</em>的目标。</strong>"
            "<em>因为 $\\hat\\epsilon = -\\sigma_t\\nabla_{x_t}\\log p_t(x_t)$，"
            "所以 $(\\hat\\epsilon - \\epsilon)$ 这一项在期望下就是"
            "「把 $x$ 往 $\\log p_t$ 上升的方向推」</em>。"
            "<strong>换句话说：SDS 不是在最小化扩散损失，"
            "而是在做<em>平滑后密度的梯度上升</em>。</strong>"
            "<em>这就是它是模式寻求的根本原因（第 3 节）</em>。",
            "<strong>而那个 $-\\epsilon$ 项值得单独说：它在期望下<em>为零</em>。</strong>"
            "<em>因为 $\\epsilon\\sim\\mathcal N(0,I)$ 与 $x$ 无关，"
            "所以 $\\mathbb E[\\epsilon\\,\\partial x/\\partial\\theta] = 0$</em>。"
            "<strong>notebook 把这一点验到了一个很干净的形式：两个估计量之差恰好是"
            "$-\\frac1n\\sum w(t)\\alpha_t\\epsilon$，它<em>完全不含 $x$</em></strong>——"
            "<em>所以用同一批随机数时，这个差在 6 个不同的 $x$ 处逐位相同"
            "（标准差 $1.7\\times10^{-17}$）</em>。"
            "<strong>也就是说它是一个纯加性的、均值为零的噪声项，不改变任何不动点。</strong>"),
        CALLOUT("danger",
                "<strong>它常被说成「一个降方差的控制变量」。notebook 实测下来，"
                "这句话<em>只在特定条件下成立</em>。</strong>"
                "<em>逐 $t$ 看效应完全反转：$t{=}0.05$（低噪）时含 $-\\epsilon$ 的方差是"
                "不含的 <strong>391 倍</strong>；$t{=}0.95$（高噪）时只有 <strong>1/1533</strong></em>。"
                "<strong>机制很清楚</strong>："
                "<em>$t\\to1$ 时 $x_t\\approx\\sigma_t\\epsilon$，于是 $\\hat\\epsilon\\approx\\epsilon$，"
                "两者几乎抵消；而 $t\\to0$ 时 $\\hat\\epsilon\\approx0$，"
                "减去 $\\epsilon$ 等于<strong>凭空加进</strong>一个方差为 1 的噪声</em>。"
                "<strong>净效应还依赖当前的 $x$</strong>："
                "<em>在模式附近（$\\pm2.5$）含 $-\\epsilon$ 更好（1.65×），"
                "而在两模式之间（0.0）它反而差 0.57×</em>。"
                "<strong>无条件成立的只有一条：它不改变期望。</strong>"
                "<em>我最初写的是「它无条件降方差」，被实测推翻了——"
                "但结论的用途没变，因为闭式期望梯度只需要「期望不变」这一条。</em>"),
        CALLOUT("intuition",
                "<strong>本模块的分析策略就建立在这个观察上。</strong>"
                "<em>既然 $-\\epsilon$ 的期望为零、而 $\\hat\\epsilon$ 对一个<strong>已知</strong>的先验有闭式，"
                "那么整个 SDS 的<strong>期望</strong>梯度就有闭式</em>："
                "<strong>$g(x) = \\mathbb E_t\\bigl[w(t)\\,\\alpha_t\\,"
                "\\mathbb E_\\epsilon[\\hat\\epsilon(\\alpha_t x + \\sigma_t\\epsilon, t)]\\bigr]$。</strong>"
                "<em>notebook 用高斯混合当先验、用高斯-埃尔米特求积算 $\\mathbb E_\\epsilon$、"
                "用细网格算 $\\mathbb E_t$——于是可以把 SDS 的动力学<strong>精确</strong>地画出来，"
                "没有任何随机性</em>。"),
    ])),

    # ============================================================== 3
    ("mode-seeking", "SDS 的解是不动点，不是样本", "".join([
        P("先验取一个两模式的高斯混合：$\\mu = \\pm 2$、$\\sigma = 0.35$、等权。"
          "把 SDS 的期望梯度算出来，找它的零点："),
        TABLE(["位置", "$g$ 的斜率", "类型"], [
            ["<strong>−1.5663</strong>", "+0.1080", "<strong>稳定（吸引子）</strong>"],
            ["0.0000", "−0.1496", "不稳定（分水岭）"],
            ["<strong>+1.5663</strong>", "+0.1080", "<strong>稳定（吸引子）</strong>"],
        ]),
        DUAL(
            "<strong>两个吸引子、一个分水岭——这是一个确定性的动力系统，不是一个采样过程。</strong>"
            "<em>用<strong>精确</strong>期望梯度跑，从任何初值出发都收敛到两个点之一，"
            "模式内散布<strong>严格为 0</strong></em>。"
            "<strong>而真实的 SDS 用蒙特卡洛估计梯度，所以有残余散布</strong>："
            "<em>notebook 用 16 个采样的随机版量到模式内标准差 <strong>0.0431</strong>，"
            "而先验是 0.35——收缩 <strong>8.1 倍</strong></em>。"
            "<strong>所以「多样性坍缩」的准确说法是："
            "残余的多样性<em>只</em>来自梯度噪声，而不是来自先验的分布。</strong>",
            "<strong>另一个后果：落到哪个模式由<em>吸引域</em>决定，而不是由先验的概率质量决定。</strong>"
            "<em>notebook 把先验权重改掉重跑，结果比「比例被压平」更强</em>："),
        TABLE(["先验权重 $\\pi$", "SDS 的不动点结构", "SDS 的模式占比"], [
            ["(0.5, 0.5)", "±1.5663（吸引子）+ 0（分水岭）", "50.4% / 49.6%"],
            ["(0.7, 0.3)", "−1.7624、+1.1530（吸引子）+ <strong>+0.4851</strong>（分水岭）",
             "<strong>54.4% / 45.6%</strong>（而先验是 70/30）"],
            ["<strong>(0.9, 0.1)</strong>",
             "<strong>只剩一个吸引子（−1.9138）</strong>",
             "<strong>100% / 0%</strong>（而先验是 90/10）"],
        ]),
        DUAL(
            "<strong>第二行：占比被<em>压向</em> 50/50（54.4% vs 先验的 70%）</strong>——"
            "<em>因为它由分水岭的位置（$+0.4851$）与初值分布决定，而不是由概率质量</em>。",
            "<strong>第三行更强：$\\pi{=}(0.9,0.1)$ 时次模式<em>不再是吸引子</em>，"
            "不动点只剩一个。</strong>"
            "<em>所以次模式被生成的概率是<strong>零</strong>，而不是 10%</em>。"
            "<strong>这就是「同一个提示词跑十次得到十个几乎一样的东西」的完整机制："
            "不只是概率被压平，而是<em>少数模式在 SDS 的动力学里直接消失</em>。</strong>"),
        CALLOUT("paper",
                "<strong>而 ProlificDreamer（VSD）正是针对这一点：它把「找模式」改回「采样」。</strong>"
                "<em>做法是维护一个关于 $\\theta$ 的<strong>分布</strong>（用一个 LoRA 拟合它的 score），"
                "让目标变成两个分布之间的 KL 而不是一个点的密度</em>。"
                "<strong>代价是要在优化过程中同时训练那个辅助模型</strong>——"
                "<em>所以它慢得多，但输出的多样性与细节都明显更好</em>。"),
    ])),

    # ============================================================== 4
    ("inward-shift", "它收敛到的模式内移 21.7%，而这是可预测的", "".join([
        P("上表的吸引子在 $\\pm1.5663$，而真实模式在 $\\pm2.0$——**内移 21.7%**。"
          "这不是数值误差："),
        DUAL(
            "<strong>SDS 找的不是 $p$ 的模式，而是「对 $t$ 平均后的 $p_t$」的模式。</strong>"
            "<em>而 $p_t$ 是 $p$ 与一个方差 $\\sigma_t^2$ 的高斯的卷积——"
            "也就是<strong>平滑</strong></em>。"
            "<strong>平滑会把两个相邻的模式互相拉近</strong>"
            "（<em>极限情况：$\\sigma_t$ 足够大时两个模式合并成一个，位置在中点</em>）。"
            "<em>所以对 $t$ 求平均（$t$ 从 0.02 到 0.98，覆盖从几乎无噪到几乎纯噪）"
            "得到的吸引子必然介于「真模式」与「中点」之间</em>。",
            "<strong>这解释了一个真实的观察：SDS 生成的东西倾向于「更中庸」。</strong>"
            "<em>细长的结构变短粗、尖锐的特征变圆滑、"
            "两个应该分开的部件粘在一起</em>。"
            "<strong>而它不是「优化没收敛」或「表示能力不够」，"
            "是目标函数的不动点<em>本来</em>就在那里。</strong>"
            "<em>所以加迭代、加高斯、换渲染器都不会改善它</em>。"),
        H3("而 CFG 真正买到的东西就是抵消这个内移"),
        TABLE(["cfg", "$\\vert g\\vert$ @ $x{=}1.5$", "全域 $\\max\\vert g\\vert$",
               "稳定所需的 $lr$ 上界", "<strong>吸引子位置</strong>",
               "相对真模式 ±2.0"], [
            ["1.0", "0.007", "0.994", "$1.22\\times10^{1}$",
             "<strong>±1.5663</strong>", "<strong>内移 21.7%</strong>"],
            ["<strong>3.0</strong>", "0.150", "2.297", "$3.71\\times10^{0}$",
             "<strong>±2.0530</strong>", "<strong>外移 2.7%（几乎恰好抵消）</strong>"],
            ["7.5", "0.470", "5.228", "$1.42\\times10^{0}$", "±2.2355", "外移 11.8%"],
            ["30.0", "2.074", "19.882", "$3.46\\times10^{-1}$", "±2.3352", "外移 16.8%"],
            ["100.0", "7.064", "65.475", "$1.03\\times10^{-1}$",
             "<strong>±2.3594</strong>", "<strong>外移 18.0%</strong>"],
        ]),
        DUAL(
            "<strong>cfg ≈ 3 时内移被恰好抵消；再大就<em>过冲</em>——"
            "吸引子跑到数据分布<em>之外</em>。</strong>"
            "<em>而 DreamFusion 报的经验值是 cfg ≈ 100（图像生成只用 7.5）</em>。"
            "<strong>在本课这个玩具先验上，cfg=100 对应外移 18%</strong>——"
            "<em>这正是 SDS 结果「过饱和、对比度过高、颜色过艳」的机制："
            "解被推到了比训练数据更极端的地方</em>。",
            "<strong>而表格的第 3、4 列说明 CFG 的<em>另一个</em>效应必须分开算：梯度幅度。</strong>"
            "<em>$\\max\\vert g\\vert$ 从 0.994 涨到 65.5（66 倍，近线性），"
            "所以稳定所需的学习率上界从 12.2 掉到 0.103（<strong>118 倍</strong>）</em>。"
            "<strong>我第一次做这个实验时正是踩了这个：cfg=100 配固定 $lr{=}0.25$，"
            "400 步之后 $x$ 是 $10^{100}$。</strong>"
            "<em>而我一开始把那个数当成了「CFG 的效应」写进结论里——"
            "它其实只是我没缩学习率</em>。"
            "<strong>补一句准确的：那次 $10^{100}$ 出现在<em>随机</em>梯度版"
            "（无条件先验的代理 score 在数据支撑外线性增长，没有边界）；"
            "而 notebook 用网格插值的确定性版本时，同样的违规表现为一个"
            "<em>周期-2 的极限环</em>（在 $+0.78$ 与 $+3.33$ 之间来回跳，振幅 2.55，"
            "与两模式间距 4.0 同量级）。</strong>"
            "<em>两者是同一个原因（$lr$ 超过 $2/\\max\\vert g'\\vert$），"
            "只是一个无界、一个有界</em>。"
            "<strong>所以比较不同 cfg 时必须把 $lr$ 按 $1/\\text{cfg}$ 缩放，"
            "否则比的是步长而不是形状。</strong>"),
    ])),

    # ============================================================== 5
    ("schedule", "$w(t)$ 与 $t$ 的采样范围：同一个旋钮的两种写法", "".join([
        P("第 4 节的内移 21.7% 是在 $w(t)=\\sigma_t^2$、$t\\in[0.02,0.98]$ 下测的。"
          "**换掉这两个之中的任何一个，不动点的位置就变了**——"
          "所以它们不是超参数细节，而是直接决定目标函数最优解在哪。"),
        H3("换权重"),
        TABLE(["$w(t)$", "吸引子位置", "相对真模式 ±2.0"], [
            ["$\\sigma_t^2$（DreamFusion 的选择）", "±1.5663", "<strong>内移 21.7%</strong>"],
            ["$1$（对 $t$ 均匀）", "±1.8739", "内移 6.3%"],
            ["<strong>$\\mathrm{SNR} = (\\alpha_t/\\sigma_t)^2$</strong>", "±1.9974",
             "<strong>内移 0.1%</strong>"],
            ["$1/\\sigma_t^2$", "±1.9919", "内移 0.4%"],
        ]),
        DUAL(
            "<strong>SNR 加权几乎完全消除了内移（0.1%）。</strong>"
            "<em>因为它把权重压在<strong>低噪</strong>（$\\sigma_t$ 小、$\\alpha_t$ 大）的那一端，"
            "而低噪处的 $p_t$ 几乎就是 $p$，没有平滑</em>。"
            "<strong>那为什么 DreamFusion 不用 SNR 加权？</strong>"
            "<em>因为低噪处的梯度<strong>信息量</strong>也最小——"
            "$\\hat\\epsilon$ 在 $t\\to0$ 时趋于噪声本身，梯度趋于零。"
            "所以 SNR 加权在玩具先验上「更准」，在真实场景里会几乎不动</em>。",
            "<strong>这是一个真实的取舍，而不是一个「更好的选择」：</strong>"
            "<em>权重压向低噪 → 不动点更接近真模式，但收敛更慢、更容易卡在初值附近；"
            "权重压向高噪 → 收敛快、能大幅改变形状，但不动点更「中庸」</em>。"
            "<strong>所以实践中的做法是<em>退火</em>——早期用高噪、后期用低噪。</strong>"),
        H3("换 $t$ 的采样范围——而这里有一个质变"),
        TABLE(["$t$ 的范围", "不动点", "解读"], [
            ["$[0.02, 0.98]$", "±1.5663（吸引）+ 0（分水岭）", "两个模式可分，内移 21.7%"],
            ["$[0.02, 0.50]$", "±1.9685 + 0", "内移 1.6%"],
            ["$[0.02, 0.30]$", "±1.9999 + 0", "<strong>内移 0.0%</strong>"],
            ["$[0.30, 0.98]$", "±1.4044 + 0", "内移 29.8%"],
            ["<strong>$[0.50, 0.98]$</strong>",
             "<strong>只有一个吸引子，在 0.0000</strong>",
             "<strong>两个模式合并了</strong>"],
            ["$[0.70, 0.98]$", "只有一个吸引子，在 0.0000", "同上"],
        ]),
        DUAL(
            "<strong>关键在于「是否包含小 $t$」，而不是上界多大。</strong>"
            "<em>只要区间里有低噪的样本，两个吸引子就在；"
            "而只采高噪段（$t \\ge 0.5$）时，平滑已经把两个模式合成了一个，"
            "SDS 的动力系统里<strong>只剩一个位于中点的吸引子</strong></em>。"
            "<strong>这就是「SDS 早期生成一团糊」的精确含义</strong>——"
            "<em>不是还没收敛，而是那个阶段的目标函数<strong>真的</strong>只有一个「中庸」的最优解</em>。",
            "<strong>而这给出一条可操作的规则：$t$ 的采样必须包含低噪端。</strong>"
            "<em>常见的实现是「$t\\sim U[0.02, t_{\\max}]$ 且 $t_{\\max}$ 随迭代退火」——"
            "notebook 量了三个阶段：$[0.40,0.98]$ → ±0.9623；"
            "$[0.20,0.70]$ → ±1.7446；$[0.02,0.40]$ → ±1.9962</em>。"
            "<strong>所以退火 $t_{\\max}$ 的作用就是「让吸引子从中庸逐步移向真模式」</strong>——"
            "<em>而这与 CFG 在做同一件事（第 4 节），只是机制不同</em>。"),
        H3("两个旋钮不独立"),
        TABLE(["$t_{\\max}$ ＼ cfg", "1.0", "7.5", "30.0", "100.0"], [
            ["0.98", "±1.566（−21.7%）", "±2.236", "±2.335", "<strong>±2.359（+18.0%）</strong>"],
            ["0.70", "±1.765", "±2.265", "±2.334", "±2.351"],
            ["0.40", "±1.996（−0.2%）", "±2.169", "±2.191", "±2.196（+9.8%）"],
            ["0.20", "<strong>±2.000（0.0%）</strong>", "±2.083", "±2.093",
             "<strong>±2.096（+4.8%）</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>读法：两个旋钮都在抵消同一个内移，所以同时开满会过冲。</strong>"
                "<em>$t_{\\max}{=}0.98$ 时 cfg 从 1 到 100 把偏差从 −21.7% 推到 +18.0%（跨 39.7 个百分点）；"
                "而 $t_{\\max}{=}0.20$ 时 cfg=1 已经是 0.0%，"
                "再加 cfg=100 只带来 +4.8% 的<strong>纯过冲</strong>——没有任何好处</em>。"
                "<strong>所以实践中的陷阱是：退火了 $t_{\\max}$ 却没有同时降 cfg。</strong>"
                "<em>症状就是「后期细节变多但颜色越来越艳、形状越来越夸张」</em>。"),
    ])),

    # ============================================================== 6
    ("janus", "Janus 是目标函数的最优解", "".join([
        P("**Janus（多面）问题**：生成出来的物体正面和背面都是一张脸、"
          "或者一只动物有两个头。"
          "它常被当成「优化没收敛」，而它其实是**逐视角独立打分**这个目标的严格最优解。"),
        ASCII("""
   构造（记「像正面」得 1.0、「像背面」得 0.2）：

   方案                        前视得分   后视得分   总得分
   ────────────────────────────────────────────────────────
   一致（前=正面、后=背面）        1.0        0.2       1.2
   Janus（两侧都是正面）          1.0        1.0     **2.0**   <- 更高
        """),
        DUAL(
            "<strong>所以只要先验对「背面」的打分低于对「正面」的打分，"
            "Janus 就<em>严格优于</em>正确答案。</strong>"
            "<em>而这个条件几乎总成立：文字提示是「一只猫」，"
            "而扩散模型在训练数据里见到的猫绝大多数是正面/侧面</em>。"
            "<strong>换句话说：Janus 是先验的<em>视角偏置</em>被逐视角独立目标放大的结果。</strong>",
            "<strong>而这决定了修法必须改<em>目标</em>，不能改优化器。</strong>"
            "<em>加迭代、换初值、加正则强度都不改变「2.0 > 1.2」这个不等式</em>。"
            "<strong>三条真实的修法：</strong>"
            "① <strong>视角条件化</strong>——"
            "<em>把相机方位放进提示或条件里（Zero-1-to-3），"
            "于是「背面」在<em>后视</em>的先验下得分变高</em>；"
            "② <strong>联合多视角先验</strong>——"
            "<em>一次生成 4–6 个视角并要求它们互相一致（MVDream），"
            "于是「两侧都是正面」在联合先验下得分<strong>变低</strong></em>；"
            "③ <strong>几何正则</strong>（对称性、法向一致）——"
            "<em>最弱的一条，因为它不改先验的偏置，只是加了一个竞争项</em>。"),
        CALLOUT("intuition",
                "<strong>为什么②比①更彻底：它改的是先验的<em>联合</em>结构，而不只是边缘。</strong>"
                "<em>①（视角条件化）仍然是逐视角独立打分——"
                "只是每个视角的打分函数不同了。"
                "所以它减轻了偏置，但没有引入「视角之间必须一致」这个约束</em>。"
                "<strong>②直接让「不一致」本身变成低分</strong>，"
                "<em>于是 Janus 不再是最优解。代价是先验必须重新训练成多视角的，"
                "而那需要 3D 或多视角数据——也就是回到了「数据」这个瓶颈</em>。"),
    ])),

    # ============================================================== 6
    ("routes", "三条路线的分工：SDS、多视角扩散、前馈重建", "".join([
        TABLE(["", "SDS（逐场景优化）", "多视角扩散 + 重建", "前馈重建（LRM 类）"], [
            ["输入", "文字 或 单图", "文字 或 单图", "<strong>单图 或 少量图</strong>"],
            ["每个资产的成本", "<strong>几十分钟的优化</strong>",
             "一次扩散采样 + 一次快速重建", "<strong>一次前向（秒级）</strong>"],
            ["多样性", "<strong>差</strong>（第 3 节：解是不动点）",
             "好（真的在采样）", "确定性（同一输入同一输出）"],
            ["几何一致性", "<strong>差</strong>（第 5 节：Janus）",
             "<strong>好</strong>（联合先验）", "取决于训练数据"],
            ["细节", "<strong>好</strong>（可以优化很久）",
             "受限于扩散的分辨率", "受限于模型容量"],
            ["需要 3D 数据吗", "<strong>不需要</strong>",
             "需要（训练多视角先验）", "需要（训练重建模型）"],
        ]),
        DUAL(
            "<strong>最后一行是这三条路线的真正分界。</strong>"
            "<em>SDS 的全部价值在于「只用 2D 先验」——"
            "所以它在 2022–2023 年是唯一可行的路，因为那时没有足够的 3D 数据</em>。"
            "<strong>而 Objaverse 等大规模 3D 数据集出现之后，"
            "②③ 变得可行，且它们在速度与一致性上全面更好。</strong>"
            "<em>所以 SDS 的地位从「主流方法」变成了「不需要 3D 数据时的兜底」，"
            "以及「作为一个精修阶段」</em>。",
            "<strong>而本模块的分析对②③同样有用，因为它们里面仍然有 SDS 的影子。</strong>"
            "<em>很多流程是「多视角扩散给初值 → SDS 精修」，"
            "而精修阶段的内移（第 4 节）与过饱和（CFG 过冲）会照样发生</em>。"
            "<strong>诊断方式：如果精修之后细节变多但形状变「胖」、颜色变艳，"
            "那就是第 4 节的两个效应</strong>——"
            "<em>而对策是降 cfg（接受细节少一些）或用 VSD 替代 SDS</em>。"),
        CALLOUT("paper",
                "<strong>与本课程其他模块的接口</strong>："
                "<em>SDS 优化的那个表示通常就是 C74 的 3DGS（或 NeRF），"
                "所以 C74 模块 03 的可微光栅化正是这里的 $\\partial x/\\partial\\theta$；"
                "而生成出来的资产要评测、要出网格，就走本课模块 05；"
                "扩散模型本身（DiT、采样器、flow matching）在 C28</em>。"),
    ])),

    # ============================================================== 8
    ("diagnose", "诊断：SDS 出了问题时该动哪个旋钮", "".join([
        TABLE(["症状", "最可能的原因", "动哪个旋钮"], [
            ["<strong>形状「胖」、细节圆滑、部件粘连</strong>",
             "第 4 节的内移——不动点本来就在那里",
             "<strong>退火 $t_{\\max}$</strong>（第 5 节：$[0.02,0.30]$ 时内移 0.0%）；"
             "<em>或换 SNR 加权，代价是收敛变慢</em>"],
            ["<strong>颜色过饱和、对比度过高</strong>",
             "CFG 过冲——吸引子被推到数据分布之外",
             "<strong>降 cfg</strong>。<em>而如果同时已经退火了 $t_{\\max}$，"
             "那么 cfg 需要降得更多（第 5 节的交互表）</em>"],
            ["<strong>训练几百步后炸成 NaN / 数值爆掉</strong>",
             "梯度幅度随 cfg 近线性增长（第 4 节：cfg=100 时 66 倍）",
             "<strong>按 $1/\\text{cfg}$ 缩学习率</strong>，或加梯度裁剪。"
             "<em>这是我自己第一次做实验时踩的坑</em>"],
            ["<strong>早期一直是一团糊，怎么都不成形</strong>",
             "$t$ 的采样范围没包含低噪端（第 5 节：$t\\ge0.5$ 时只有一个中点吸引子）",
             "<strong>把 $t$ 的下界压到 0.02 附近</strong>"],
            ["<strong>正反两面都是同一张脸 / 两个头</strong>",
             "Janus——目标函数的最优解（第 6 节）",
             "<strong>必须改目标</strong>：视角条件化，或换多视角先验。"
             "<em>加迭代、换初值、加正则都不改变「2.0 &gt; 1.2」这个不等式</em>"],
            ["<strong>同一个提示词跑十次几乎一样</strong>",
             "<strong>正常</strong>——SDS 的解是不动点（第 3 节）",
             "<em>要多样性就得换目标（VSD），而不是换随机种子</em>"],
        ]),
        CALLOUT("intuition",
                "<strong>把这张表压成一句话：SDS 的问题几乎都是「目标函数的不动点在哪」的问题，"
                "而不是「优化收敛得好不好」的问题。</strong>"
                "<em>所以调参的正确心态是「我在移动不动点」，而不是「我在帮优化器找到最优解」</em>。"
                "<strong>而这也是本模块把 $w(t)$、$t$ 范围、cfg 三个旋钮"
                "全部换算成「吸引子位置」来量的原因</strong>——"
                "<em>那是它们唯一的共同度量</em>。"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 04 · 3D 生成：SDS 与多视角扩散

本 notebook 用一个**解析已知**的扩散先验（高斯混合），把 SDS 的动力学算到闭式：

1. SDS 梯度里的 $-\\epsilon$ 项**期望为零** —— 它是控制变量，不改变期望但降方差；
2. **SDS 的解是不动点，不是样本**：精确梯度下模式内散布**严格为 0**，
   而随机版是 0.0476（先验是 0.35，收缩 **7 倍**）；
3. **它收敛到的模式内移 21.7%**（±1.5663 vs 真值 ±2.0）—— 而这是可预测的；
4. **CFG 真正买到的是抵消这个内移，而它会过冲**：cfg≈3 恰好抵消，cfg=100 时外移 18%；
   而它的**另一个**效应（梯度幅度 ×66）会让固定 lr 直接发散；
5. **$t$ 的采样范围决定两个模式能不能被区分**：只采高噪段时它们**合并**成一个中点吸引子；
6. **Janus 是目标函数的最优解**，不是优化失败。

只用 numpy，CPU，离线。不用任何真实扩散模型 —— 用高斯混合当替身。"""),

code("""import numpy as np, math, time
print('numpy', np.__version__)

# ---- 一个解析已知的「扩散先验」：两模式高斯混合 ----
MU = np.array([-2.0, 2.0])
SD = np.array([0.35, 0.35])
PI = np.array([0.5, 0.5])

def sched(t):
    '''余弦调度：alpha_t, sigma_t。t∈(0,1)，t→0 无噪、t→1 纯噪。'''
    t = np.asarray(t, float)
    return np.cos(t*np.pi/2), np.sin(t*np.pi/2)

def score_pt(x, a, s):
    '''∇_x log p_t(x)，闭式。p_t = Σ π_k N(a·μ_k, a²s_k² + σ_t²)。'''
    x = np.asarray(x, float).reshape(-1)
    m = a*MU
    v = (a*SD)**2 + s**2
    lg = (-0.5*np.log(2*np.pi*v)[None, :]
          - 0.5*(x[:, None]-m[None, :])**2/v[None, :] + np.log(PI)[None, :])
    lg -= lg.max(1, keepdims=True)
    w = np.exp(lg); w /= w.sum(1, keepdims=True)
    return np.sum(w*(-(x[:, None]-m[None, :])/v[None, :]), 1)

def sample_prior(n, seed=0):
    r = np.random.default_rng(seed)
    k = r.choice(len(MU), n, p=PI)
    return MU[k] + SD[k]*r.normal(size=n)

_pr = sample_prior(50000, 0)
print(f'先验：两个模式 μ=±2、σ=0.35、等权')
print(f'  整体标准差 {_pr.std():.4f}   模式内标准差 ≈ {SD[0]:.4f}')
# 验证 score 是对的：数值微分 log p_t
_a, _s = sched(0.3)
_x = np.array([0.7])
_h = 1e-6
def logpt(x, a, s):
    x = np.atleast_1d(x); m = a*MU; v = (a*SD)**2 + s**2
    return np.log(np.sum(PI/np.sqrt(2*np.pi*v)*np.exp(-0.5*(x[:,None]-m)**2/v), 1))
_num = (logpt(_x+_h, _a, _s) - logpt(_x-_h, _a, _s))/(2*_h)
_ana = score_pt(_x, _a, _s)
print(f'\\nscore 的解析式 vs 数值微分: {_ana[0]:.10f} vs {_num[0]:.10f}  '
      f'相对差 {abs(_ana[0]-_num[0])/abs(_num[0]):.2e}')
assert abs(_ana[0]-_num[0])/abs(_num[0]) < 1e-6"""),

md("""## 1 · SDS 的梯度：$-\\epsilon$ 项的期望为零

$$\\nabla_\\theta\\mathcal L_{\\text{SDS}}
= \\mathbb E_{t,\\epsilon}\\bigl[w(t)(\\hat\\epsilon(x_t,t) - \\epsilon)\\,\\partial x/\\partial\\theta\\bigr]$$

取渲染器为恒等（$x = \\theta$），并用 $\\hat\\epsilon = -\\sigma_t\\nabla\\log p_t$。
因为 $\\epsilon\\sim\\mathcal N(0,I)$ 与 $x$ 独立，所以 $\\mathbb E[\\epsilon] = 0$ ——
那一项在期望下**消失**。

它常被说成一个「降方差的控制变量」。**本节把这句话验一遍，而结论需要限定条件。**"""),

code("""def sds_grad_mc(x, n_mc, seed, cfg=1.0, keep_eps=True, t_lo=0.02, t_hi=0.98,
                w_mode='sigma2'):
    '''蒙特卡洛估计的 SDS 梯度（单点）。keep_eps=False 时去掉 -eps 项。'''
    r = np.random.default_rng(seed)
    ts = r.uniform(t_lo, t_hi, n_mc)
    g = 0.0
    for t in ts:
        a, s = sched(t)
        w = s**2 if w_mode == 'sigma2' else 1.0
        eps = r.normal()
        xt = a*x + s*eps
        eh = -s*score_pt(np.array([xt]), a, s)[0]
        if cfg != 1.0:
            eu = -s*(-(xt)/(a**2*4.0 + s**2))
            eh = eu + cfg*(eh - eu)
        g += w*((eh - eps) if keep_eps else eh)*a
    return g/n_mc

# ---- ① 期望相同，而且两个估计量之差**完全不依赖 x** ----
print('两个估计量之差 = -(1/n)Σ w(t)·α_t·ε —— 它根本不含 x。')
print('  所以用同一批随机数时，差应当在所有 x 处**恰好相同**：')
print('   x       含 -eps      不含 -eps     差')
_diffs = []
for x in [-2.5, -1.0, 0.0, 0.9, 2.5, 4.0]:
    a_ = np.mean([sds_grad_mc(x, 32, 2000+i, keep_eps=True) for i in range(200)])
    b_ = np.mean([sds_grad_mc(x, 32, 2000+i, keep_eps=False) for i in range(200)])
    _diffs.append(a_ - b_)
    print(f' {x:+5.1f}   {a_:+11.6f}  {b_:+11.6f}  {a_-b_:+.6e}')
assert np.std(_diffs) < 1e-12, f'差应与 x 无关，实测标准差 {np.std(_diffs):.2e}'
print(f'\\n✓ 差在 6 个 x 处完全相同（标准差 {np.std(_diffs):.1e}）——')
print(f'  证实它是一个纯加性的、与 x 无关的噪声项，均值为 0（这里 {np.mean(_diffs):+.2e}，')
print(f'  是 200 次平均的抽样误差）。所以它**不改变任何不动点**。')

# ---- ② 方差效应：逐 t 看，它是有条件的 ----
print('\\n而「降方差」这句话需要限定条件。固定 t，只对 ε 求方差（20000 个样本，x=0.9）：')
print('   t      α_t     σ_t     Var[含 -eps]    Var[不含]      不含/含')
_r = np.random.default_rng(0)
_ratios = {}
for t in [0.05, 0.2, 0.4, 0.6, 0.8, 0.95]:
    a, s = sched(t); w = s**2
    eps = _r.normal(size=20000)
    xt = a*0.9 + s*eps
    eh = -s*score_pt(xt, a, s)
    with_ = w*a*(eh - eps); without = w*a*eh
    _ratios[t] = without.var()/with_.var()
    print(f' {t:5.2f} {a:7.3f} {s:7.3f}  {with_.var():13.5e} {without.var():13.5e}'
          f'  {_ratios[t]:10.2f}')
assert _ratios[0.05] < 0.01, '低噪端 -eps 应大幅**增加**方差'
assert _ratios[0.95] > 100, '高噪端 -eps 应大幅降低方差'
print(f'\\n✓ 逐 t 看，效应完全反转：')
print(f'  t=0.05（低噪）：含 -eps 的方差是不含的 {1/_ratios[0.05]:.0f} 倍 —— **增加**方差')
print(f'  t=0.95（高噪）：含 -eps 的方差是不含的 1/{_ratios[0.95]:.0f} —— 降低 {_ratios[0.95]:.0f} 倍')
print('  机制：t→1 时 x_t ≈ σ_t ε，于是 ε̂ ≈ ε，(ε̂-ε) 几乎抵消掉；')
print('        而 t→0 时 ε̂ ≈ 0，减去 ε 等于**凭空加进**一个方差为 1 的噪声。')"""),

code("""# ---- ③ 净效应：取决于 x 与 t 的范围 ----
def std_ratio(x, n_mc=32, trials=300, t_lo=0.02, t_hi=0.98, w_mode='sigma2'):
    '''返回 (含 -eps 的 std, 不含的 std)。用同一批种子。'''
    a_ = np.array([sds_grad_mc(x, n_mc, 4000+i, keep_eps=True,
                               t_lo=t_lo, t_hi=t_hi, w_mode=w_mode) for i in range(trials)])
    b_ = np.array([sds_grad_mc(x, n_mc, 4000+i, keep_eps=False,
                               t_lo=t_lo, t_hi=t_hi, w_mode=w_mode) for i in range(trials)])
    return a_.std(), b_.std()

print('净效应（n_mc=32, t~U[0.02,0.98], w=σ_t²）：')
print('   x      含 -eps 的 std   不含的 std   不含/含   谁的方差小')
NET = {}
for x in [-2.5, -1.0, 0.0, 0.9, 1.6, 2.5, 4.0]:
    sa, sb = std_ratio(x)
    NET[x] = sb/sa
    print(f' {x:+5.1f}   {sa:14.6f}  {sb:11.6f}  {sb/sa:8.3f}   '
          f'{"含 -eps" if sb > sa else "不含"}')
assert NET[-2.5] > 1.3 and NET[2.5] > 1.3, '模式附近含 -eps 应更好'
assert NET[0.0] < 0.8 and NET[0.9] < 0.9, '两模式之间含 -eps 应更差'
print(f'\\n✓ 净效应**依赖 x**：')
print(f'  在模式附近（±2.5）含 -eps 更好（{NET[-2.5]:.2f}× / {NET[2.5]:.2f}×）；')
print(f'  在两模式之间（0.0, 0.9）含 -eps 反而更差（{NET[0.0]:.2f}× / {NET[0.9]:.2f}×）。')

print('\\n也依赖 t 的范围（x=0.9）：')
print('  t 范围            不含/含    谁的方差小')
for lo, hi in [(0.02, 0.98), (0.02, 0.50), (0.50, 0.98), (0.70, 0.98), (0.90, 0.98)]:
    sa, sb = std_ratio(0.9, t_lo=lo, t_hi=hi)
    print(f'  [{lo:.2f}, {hi:.2f}]        {sb/sa:7.3f}    '
          f'{"含 -eps" if sb > sa else "不含"}')
_sa7, _sb7 = std_ratio(0.9, t_lo=0.7, t_hi=0.98)
_sa9, _sb9 = std_ratio(0.9, t_lo=0.9, t_hi=0.98)
assert _sb7/_sa7 > 1.2 and _sb9/_sa9 > 3.0, '只采高噪时含 -eps 应明显更好'
print(f'\\n✓ 只有当 t 限制在高噪端时，含 -eps 才可靠地更好'
      f'（[0.9,0.98] 时 {_sb9/_sa9:.1f} 倍）。')
print('\\n所以「-ε 是一个降方差的控制变量」这句话**只在特定条件下成立**：')
print('  高噪端（或初始化在模式附近）时它降方差；')
print('  低到中噪端、且当前解在两模式之间时它**增加**方差。')
print('  而无条件成立的只有一条：它不改变期望（① 已验证，且差与 x 无关）。')
print('\\n⚠ 我最初写的是「它无条件降方差」，被这一格的实测推翻了。')
print('  但结论的**用途**没变：正因为期望不变，整个 SDS 的期望梯度有闭式 —— 下一节。')"""),

md("""## 2 · SDS 的期望梯度：闭式，无随机性

$$g(x) = \\mathbb E_t\\Bigl[w(t)\\,\\alpha_t\\,
\\mathbb E_\\epsilon\\bigl[\\hat\\epsilon(\\alpha_t x + \\sigma_t\\epsilon,\\,t)\\bigr]\\Bigr]$$

$\\mathbb E_\\epsilon$ 用高斯-埃尔米特求积（对 $\\mathcal N(0,1)$ 精确到高阶），
$\\mathbb E_t$ 用细网格。"""),

code("""HN, HW = np.polynomial.hermite_e.hermegauss(32)
HW = HW/HW.sum()
GRID = np.linspace(-8, 8, 2001)

def sds_grad_exact(cfg=1.0, t_lo=0.02, t_hi=0.98, n_t=120, w_mode='sigma2', grid=GRID):
    '''SDS 期望梯度，在 grid 上求值。返回与 grid 同长的数组。'''
    ts = (np.arange(n_t) + 0.5)/n_t*(t_hi - t_lo) + t_lo
    A_, S_ = sched(ts)
    g = np.zeros_like(grid)
    for a, s in zip(A_, S_):
        if w_mode == 'sigma2':     w = s**2
        elif w_mode == 'one':      w = 1.0
        elif w_mode == 'snr':      w = (a/s)**2
        elif w_mode == 'inv_sigma2': w = 1.0/s**2
        else: raise ValueError(w_mode)
        acc = np.zeros_like(grid)
        for e, ww in zip(HN, HW):
            xt = a*grid + s*e
            eh = -s*score_pt(xt, a, s)
            if cfg != 1.0:
                eu = -s*(-(xt)/(a**2*4.0 + s**2))
                eh = eu + cfg*(eh - eu)
            acc += ww*eh
        g += w*a*acc
    return g/n_t

t0 = time.time()
G1 = sds_grad_exact()
print(f'闭式期望梯度算完，{time.time()-t0:.2f} s')

# 与蒙特卡洛的期望一致
print('\\n闭式 vs 蒙特卡洛（每点 4000 个样本）：')
print('   x        闭式        MC 均值 ± 标准误')
for x in [-1.0, 0.5, 1.4, 2.5]:
    i = int(np.argmin(np.abs(GRID - x)))
    mc = np.array([sds_grad_mc(x, 200, 900+j) for j in range(20)])
    print(f' {x:+5.1f}   {G1[i]:+9.5f}   {mc.mean():+9.5f} ± {mc.std()/np.sqrt(20):.5f}')
    assert abs(G1[i] - mc.mean()) < 4*mc.std()/np.sqrt(20) + 0.02, f'x={x} 不一致'
print('\\n✓ 闭式与蒙特卡洛的期望一致 —— 所以后面可以完全抛开随机性来分析动力学')"""),

md("""## 3 · 不动点：两个吸引子 + 一个分水岭，而模式内移 21.7%"""),

code("""def fixed_points(g, grid=GRID):
    '''返回 [(位置, 斜率, 类型)]。我们做 x <- x - lr*g，所以 g'>0 是吸引子。'''
    out = []
    sgn = np.sign(g)
    for i in np.where(np.diff(sgn) != 0)[0]:
        sl = (g[i+1]-g[i])/(grid[i+1]-grid[i])
        x0 = grid[i] - g[i]*(grid[i+1]-grid[i])/(g[i+1]-g[i])
        out.append((float(x0), float(sl), '吸引子' if sl > 0 else '分水岭'))
    return out

FP = fixed_points(G1)
print(' 位置        斜率        类型')
for x0, sl, tp in FP:
    print(f' {x0:+8.4f}   {sl:+9.4f}   {tp}')
ATT = [x0 for x0, sl, tp in FP if sl > 0 and abs(x0) > 0.1]
SAD = [x0 for x0, sl, tp in FP if sl < 0]
assert len(ATT) == 2 and len(SAD) == 1, f'应有 2 个吸引子 + 1 个分水岭，实测 {FP}'
assert abs(SAD[0]) < 1e-6, '分水岭应在 0'
_att = float(np.mean(np.abs(ATT)))
assert abs(_att - 1.5663) < 0.01, f'吸引子应在 ±1.5663，实测 ±{_att:.4f}'
print(f'\\n✓ 两个吸引子在 ±{_att:.4f}，分水岭在 {SAD[0]:+.1e}')
print(f'✓ 真实模式在 ±2.0 -> **内移 {(1-_att/2.0):.1%}**')
print('\\n为什么内移是可预测的：SDS 找的不是 p 的模式，而是「对 t 平均后的 p_t」的模式。')
print('  而 p_t 是 p 与方差 σ_t² 的高斯的卷积 —— 也就是**平滑**，它把两个模式互相拉近。')

# 直接验证：单个 t 下平滑密度的模式位置
print('\\n单个 t 下 p_t 的模式位置（在 x 空间，已除掉 α_t）：')
print('   t      σ_t      p_t 的模式 / α_t')
for t in [0.05, 0.2, 0.4, 0.6, 0.8]:
    a, s = sched(t)
    xs = np.linspace(0.01, 3.0, 4000)
    lp = logpt(a*xs, a, s)
    k = int(np.argmax(lp))
    print(f' {t:5.2f}  {s:6.4f}   {xs[k]:8.4f}' +
          ('   <- 两模式已合并到 0 附近' if xs[k] < 0.3 else ''))
print('\\n✓ σ_t 越大，模式越往中间移 —— 而 SDS 对整个 t 范围求平均，')
print('  所以它的吸引子必然介于「真模式 ±2.0」与「中点 0」之间。')
print('  实践后果：SDS 生成的东西倾向于「更中庸」——')
print('  细长的变短粗、尖锐的变圆滑、该分开的部件粘在一起。')
print('  而这不是优化没收敛，是目标函数的不动点本来就在那里。')"""),

md("""## 4 · 精确梯度是确定性的；随机版的残余散布只来自梯度噪声"""),

code("""def run_exact(cfg=1.0, n=2000, steps=3000, lr=None, seed=3, **kw):
    '''用闭式梯度（网格插值）跑 SDS。完全确定性。'''
    g = sds_grad_exact(cfg=cfg, **kw)
    r = np.random.default_rng(seed)
    x = r.uniform(-6, 6, n)
    lr = (0.25/cfg) if lr is None else lr
    for _ in range(steps):
        x = np.clip(x - lr*np.interp(x, GRID, g), -8, 8)
    return x

def run_mc(cfg=1.0, n_runs=200, steps=600, lr=0.25, n_mc=16, seed=1):
    '''用蒙特卡洛梯度跑 SDS（真实做法）。'''
    r = np.random.default_rng(seed)
    out = []
    for i in range(n_runs):
        x = r.uniform(-5, 5)
        for st in range(steps):
            x = x - lr*sds_grad_mc(x, n_mc, 5000 + i*steps + st)
            if not np.isfinite(x) or abs(x) > 50: x = np.nan; break
        out.append(x)
    return np.array(out)

def mode_stats(x):
    x = x[np.isfinite(x)]
    nm = [x[np.abs(x-m) < 1.2] for m in MU]
    pos = float(np.mean([abs(a.mean()) for a in nm if len(a) > 5]))
    sd = float(np.mean([a.std() for a in nm if len(a) > 5]))
    frac = [len(a)/len(x) for a in nm]
    return pos, sd, frac

x_ex = run_exact()
p_ex, s_ex, f_ex = mode_stats(x_ex)
print(f'精确梯度：吸引子 ±{p_ex:.4f}   模式内散布 {s_ex:.3e}   '
      f'两模式占比 {f_ex[0]:.1%}/{f_ex[1]:.1%}')
assert s_ex < 1e-6, f'精确梯度下应确定性收敛，实测散布 {s_ex:.2e}'

t0 = time.time()
x_mc = run_mc()
p_mc, s_mc, f_mc = mode_stats(x_mc)
print(f'蒙特卡洛（n_mc=16）：吸引子 ±{p_mc:.4f}   模式内散布 {s_mc:.4f}   '
      f'占比 {f_mc[0]:.1%}/{f_mc[1]:.1%}   ({time.time()-t0:.1f} s)')
print(f'\\n先验的模式内标准差 {SD[0]:.4f}（对照）')
print(f'✓ 精确梯度：散布 **严格为 0**（{s_ex:.1e}）—— 它是一个确定性动力系统')
print(f'✓ 蒙特卡洛：散布 {s_mc:.4f}，比先验收缩 {SD[0]/s_mc:.1f} 倍')
assert 0.01 < s_mc < 0.2, f'MC 版应有可观但远小于先验的散布，实测 {s_mc:.4f}'
assert SD[0]/s_mc > 2, '应比先验明显收缩'
print('\\n✓ 所以「多样性坍缩」的准确说法是：')
print('  残余的多样性**只**来自梯度噪声，而不是来自先验的分布。')
print('  SDS 的解是不动点，不是样本。')

# 落到哪个模式由**吸引域**决定，而不是由先验的概率质量决定
print('\\n把先验权重改掉，看 SDS 的模式占比会不会跟着变：')
print(' 先验权重      不动点结构                                    SDS 的占比')
_PI_bak = PI.copy()
SKEW = {}
for _w in [(0.5, 0.5), (0.7, 0.3), (0.9, 0.1)]:
    PI[:] = np.array(_w)
    _G = sds_grad_exact()
    _fp = fixed_points(_G)
    _x = run_exact()
    _nm = [_x[np.abs(_x - mu) < 1.2] for mu in MU]
    _fr = [len(a)/len(_x) for a in _nm]
    SKEW[_w] = (_fp, _fr)
    _desc = '  '.join(f'{a:+.4f}({t})' for a, s, t in _fp)
    print(f' {str(_w):12s}  {_desc:44s}  {_fr[0]:.1%}/{_fr[1]:.1%}')
PI[:] = _PI_bak

_fp5, _fr5 = SKEW[(0.5, 0.5)]
_fp7, _fr7 = SKEW[(0.7, 0.3)]
_fp9, _fr9 = SKEW[(0.9, 0.1)]
_att9 = [x for x, s, t in _fp9 if s > 0 and abs(x) > 0.1]
assert len([x for x, s, t in _fp5 if s > 0 and abs(x) > 0.1]) == 2
assert len(_att9) == 1, f'π=(0.9,0.1) 时应只剩一个吸引子，实测 {_fp9}'
assert _fr9[1] < 0.01, f'次模式应完全拿不到，实测占比 {_fr9[1]:.1%}'
assert abs(_fr7[0] - 0.7) > 0.1, f'π=(0.7,0.3) 时占比不应等于先验，实测 {_fr7[0]:.1%}'
print(f'\\n✓ 两个结论，一个比一个强：')
print(f'  ① π=(0.7,0.3) 时 SDS 给出 {_fr7[0]:.1%}/{_fr7[1]:.1%}，而先验是 70%/30% ——')
print(f'     占比被**压向 50/50**。因为它由分水岭的位置（这里 {[f"{x:+.4f}" for x,s,t in _fp7 if s<0][0]}）')
print(f'     与初值分布决定，而不是由概率质量决定。')
print(f'  ② π=(0.9,0.1) 时**次模式不再是吸引子** —— 不动点只剩一个（{_att9[0]:+.4f}）。')
print(f'     所以 SDS 给出 {_fr9[0]:.0%}/{_fr9[1]:.0%}：次模式被生成的概率是**零**，不是 10%。')
print(f'\\n  这就是「同一个提示词跑十次得到十个几乎一样的东西」的完整机制：')
print(f'  不只是「概率被压平」，而是**少数模式在 SDS 的动力学里直接消失**。')

"""),

md("""## 5 · CFG 的两种效应必须分开量"""),

code("""print(' cfg    |g|@1.5    max|g|     稳定 lr 上界    吸引子      相对真模式 ±2.0')
CFG = {}
for cfg in [1.0, 3.0, 7.5, 30.0, 100.0]:
    g = sds_grad_exact(cfg=cfg)
    dg = np.gradient(g, GRID)
    i15 = int(np.argmin(np.abs(GRID - 1.5)))
    att = [x0 for x0, sl, tp in fixed_points(g) if sl > 0 and abs(x0) > 0.1]
    a_ = float(np.mean(np.abs(att))) if att else np.nan
    lr_max = 2.0/np.abs(dg).max()
    CFG[cfg] = (float(np.abs(g).max()), lr_max, a_)
    tag = f'内移 {(1-a_/2.0):.1%}' if a_ < 2.0 else f'**外移 {(a_/2.0-1):.1%}**'
    print(f' {cfg:6.1f} {abs(g[i15]):9.3f} {np.abs(g).max():10.3f}   {lr_max:.3e}    '
          f'±{a_:.4f}   {tag}')

assert CFG[1.0][2] < 2.0, 'cfg=1 时应内移'
assert CFG[3.0][2] > 2.0, 'cfg=3 时应已抵消（略微外移）'
assert CFG[100.0][2] > 2.3, 'cfg=100 时应明显外移'
_gm_ratio = CFG[100.0][0]/CFG[1.0][0]
assert _gm_ratio > 50, f'梯度幅度应涨 50 倍以上，实测 {_gm_ratio:.0f}'
print(f'\\n✓ 效应②（形状）：吸引子从 ±{CFG[1.0][2]:.4f}（内移 {(1-CFG[1.0][2]/2):.1%}）'
      f'移到 ±{CFG[100.0][2]:.4f}（外移 {(CFG[100.0][2]/2-1):.1%}）')
print(f'  cfg≈3 时恰好抵消（±{CFG[3.0][2]:.4f}）—— **这才是 CFG 在 SDS 里真正买到的东西**')
print(f'  再大就**过冲**：吸引子跑到数据分布之外，这正是 SDS 结果「过饱和」的机制')
print(f'\\n✓ 效应①（幅度）：max|g| 从 {CFG[1.0][0]:.3f} 涨到 {CFG[100.0][0]:.3f}'
      f'（{_gm_ratio:.0f} 倍，近线性）')
print(f'  所以稳定所需的 lr 上界从 {CFG[1.0][1]:.3e} 掉到 {CFG[100.0][1]:.3e}'
      f'（{CFG[1.0][1]/CFG[100.0][1]:.0f} 倍）')

# 演示：lr 超过稳定界之后会怎样
print('\\n⚠ 我第一次做这个实验时踩的坑：cfg=100 配固定 lr=0.25')
print(f'  稳定界是 lr < 2/max|g′| = {CFG[100.0][1]:.3e}，而 0.25 超出它 '
      f'{0.25/CFG[100.0][1]:.0f} 倍\\n')
_g100 = sds_grad_exact(cfg=100.0)
_x = 0.9; _traj = []
for _k in range(80):
    _x = _x - 0.25*float(np.interp(_x, GRID, _g100))
    _traj.append(_x)
print(f'  前 10 步：{[f"{v:+.2f}" for v in _traj[:10]]}')
print(f'  后 10 步：{[f"{v:+.2f}" for v in _traj[-10:]]}')
_tail = np.array(_traj[-40:])
print(f'  后 40 步的标准差 {_tail.std():.4f}   范围 [{_tail.min():+.2f}, {_tail.max():+.2f}]')
# 与按 1/cfg 缩放后的对比
_x2 = 0.9
for _k in range(4000):
    _x2 = _x2 - (0.25/100.0)*float(np.interp(_x2, GRID, _g100))
print(f'\\n  而 lr = 0.25/100 时：收敛到 {_x2:+.4f}（就是 cfg=100 的吸引子 '
      f'±{CFG[100.0][2]:.4f}）')
assert _tail.std() > 0.5, f'超过稳定界时不该收敛，实测后段标准差 {_tail.std():.4f}'
assert abs(_x2 - CFG[100.0][2]) < 1e-3, '缩放 lr 后应精确收敛到吸引子'
assert _tail.max() - _tail.min() > 2.0, '振幅应与模式间距同量级'
print(f'\\n✓ 超过稳定界的后果是**不收敛**：轨迹落入一个周期-2 的极限环，')
print(f'  在 {_tail.min():+.2f} 与 {_tail.max():+.2f} 之间来回跳 —— 振幅 {_tail.max()-_tail.min():.2f}，')
print(f'  与两个模式的间距 4.0 同量级。所以「结果」取决于你在第几步停下。')
print(f'✓ 而按 1/cfg 缩放 lr 之后精确收敛（后段标准差 < 1e-15）。')
print()
print('  我第一版用的是**随机**梯度 + 一个无界的代理无条件先验，')
print('  那时同样的违规产生的是真正的发散（400 步后 x ≈ 1e100）——')
print('  因为 score 在数据支撑之外线性增长，没有边界把它拉回来。')
print('  本格用网格插值，网格外被截断，所以表现为极限环而不是发散。')
print('  两者是同一个原因：**lr 超过了 2/max|g′|**。')
print('  而我一开始把那个 1e100 当成了「CFG 的效应」写进结论 —— 它只是我没缩学习率。')
print('  所以比较不同 cfg 必须把 lr 按 1/cfg 缩放，否则比的是步长而不是形状。')

"""),

md("""## 6 · $w(t)$ 与 $t$ 的采样范围：同一个旋钮的两种写法"""),

code("""print('换权重 w(t)：')
print(' w(t)                    吸引子      相对真模式')
for wm, lab in [('sigma2', 'σ_t²（DreamFusion）'), ('one', '1（对 t 均匀）'),
                ('snr', 'SNR=(α/σ)²'), ('inv_sigma2', '1/σ_t²')]:
    g = sds_grad_exact(w_mode=wm)
    att = [x0 for x0, sl, tp in fixed_points(g) if sl > 0 and abs(x0) > 0.1]
    a_ = float(np.mean(np.abs(att)))
    print(f' {lab:22s} ±{a_:.4f}    {"内移" if a_<2 else "外移"} {abs(1-a_/2.0):.1%}')
_a_snr = float(np.mean(np.abs([x0 for x0, sl, tp in fixed_points(sds_grad_exact(w_mode="snr"))
                               if sl > 0 and abs(x0) > 0.1])))
assert abs(_a_snr - 2.0) < 0.02, f'SNR 加权应几乎消除内移，实测 ±{_a_snr:.4f}'
print(f'\\n✓ SNR 加权几乎完全消除内移（±{_a_snr:.4f}）—— 因为它把权重压在低噪端')
print('  那为什么 DreamFusion 不用它？因为低噪处的梯度**信息量**也最小：')
print('  t→0 时 ε̂ 趋于噪声本身、梯度趋于零。所以它在玩具先验上更准，在真实场景里几乎不动。')
print('  这是一个真实的取舍，不是一个「更好的选择」。')

print('\\n换 t 的采样范围 —— 这里有一个**质变**：')
print(' t 范围            不动点')
TR = {}
for lo, hi in [(0.02, 0.98), (0.02, 0.50), (0.02, 0.30), (0.30, 0.98),
               (0.50, 0.98), (0.70, 0.98)]:
    g = sds_grad_exact(t_lo=lo, t_hi=hi)
    fp = fixed_points(g)
    att = [x0 for x0, sl, tp in fp if sl > 0]
    TR[(lo, hi)] = att
    desc = '  '.join(f'{x0:+.4f}({tp})' for x0, sl, tp in fp)
    print(f' [{lo:.2f}, {hi:.2f}]     {desc}')

assert len([a for a in TR[(0.02, 0.98)] if abs(a) > 0.1]) == 2, '含小 t 时应有两个吸引子'
assert len([a for a in TR[(0.50, 0.98)] if abs(a) > 0.1]) == 0, \\
    't>=0.5 时两个模式应合并'
assert len(TR[(0.50, 0.98)]) == 1 and abs(TR[(0.50, 0.98)][0]) < 1e-6, \\
    '只剩一个位于 0 的吸引子'
print('\\n✓ 关键在于「是否包含小 t」，而不是上界多大：')
print('  只要区间里有低噪样本，两个吸引子就在；')
print('  而只采高噪段（t≥0.5）时，**只剩一个位于 0 的吸引子** —— 两个模式合并了。')
print('  这就是「SDS 早期生成一团糊」的精确含义：那个阶段的目标函数**真的**只有')
print('  一个「中庸」的最优解，而不是还没收敛。')

print('\\n退火 t 上界（模拟真实做法）：')
for lo, hi, tag in [(0.40, 0.98, '早期（粗形状）'), (0.20, 0.70, '中期'),
                    (0.02, 0.40, '后期（细节）')]:
    att = [x0 for x0, sl, tp in fixed_points(sds_grad_exact(t_lo=lo, t_hi=hi))
           if sl > 0 and abs(x0) > 0.1]
    print(f'  {tag:14s} [{lo:.2f}, {hi:.2f}] -> ±{float(np.mean(np.abs(att))):.4f}')
print('  ✓ 退火 t 上界 = 让吸引子从「中庸」逐步移向真模式。')

print('\\n两个旋钮不独立：')
print('  t_hi \\\\ cfg      1.0        7.5       30.0      100.0')
INT = {}
for hi in [0.98, 0.70, 0.40, 0.20]:
    row = []
    for c in [1.0, 7.5, 30.0, 100.0]:
        att = [x0 for x0, sl, tp in fixed_points(sds_grad_exact(cfg=c, t_hi=hi))
               if sl > 0 and abs(x0) > 0.1]
        a_ = float(np.mean(np.abs(att))) if att else np.nan
        INT[(hi, c)] = a_
        row.append(f'±{a_:.3f}')
    print(f'  {hi:.2f}        ' + '  '.join(row))

_span_hi = abs(INT[(0.98, 100.0)] - INT[(0.98, 1.0)])
_span_lo = abs(INT[(0.20, 100.0)] - INT[(0.20, 1.0)])
assert _span_hi > 3*_span_lo, 'cfg 的效应在大 t_hi 下应强得多'
assert abs(INT[(0.20, 1.0)] - 2.0) < 0.02, 't_hi=0.20 时 cfg=1 已经几乎无偏'
print(f'\\n✓ 两个旋钮都在抵消同一个内移，所以同时开满会过冲：')
print(f'  t_hi=0.98 时 cfg 从 1 到 100 把偏差从 {(INT[(0.98,1.0)]/2-1):+.1%} '
      f'推到 {(INT[(0.98,100.0)]/2-1):+.1%}（跨 {_span_hi/2*100:.1f} 个百分点）')
print(f'  而 t_hi=0.20 时 cfg=1 已经是 {(INT[(0.20,1.0)]/2-1):+.1%}，'
      f'再加 cfg=100 只带来 {(INT[(0.20,100.0)]/2-1):+.1%} 的**纯过冲** —— 没有任何好处')
print('  所以实践中的陷阱是：退火了 t_max 却没有同时降 cfg。')
print('  症状就是「后期细节变多但颜色越来越艳、形状越来越夸张」。')"""),

md("""## 7 · Janus 是目标函数的最优解"""),

code("""def janus_scores(front_pref=1.0, back_pref=0.2, n_views=2):
    '''逐视角独立打分。返回 {方案: (各视角得分, 总分)}。
    「一致」= 前面是正面、后面是背面；「Janus」= 两侧都是正面。'''
    out = {}
    out['一致（前=正面, 后=背面）'] = ([front_pref] + [back_pref]*(n_views-1),
                                       front_pref + back_pref*(n_views-1))
    out['Janus（每一侧都是正面）'] = ([front_pref]*n_views, front_pref*n_views)
    return out

print('构造：先验对「正面」打 1.0、对「背面」打 0.2（因为训练数据里正面多得多）\\n')
print(' 视角数   方案                        各视角得分        总分')
for nv in [2, 4]:
    for tag, (per, tot) in janus_scores(n_views=nv).items():
        print(f'  {nv:4d}    {tag:26s} {[f"{v:.1f}" for v in per]}   {tot:5.1f}')
    print()

_s2 = janus_scores(n_views=2)
_cons = _s2['一致（前=正面, 后=背面）'][1]
_jan = _s2['Janus（每一侧都是正面）'][1]
assert _jan > _cons, f'Janus 必须得分更高：{_jan} vs {_cons}'
print(f'✓ Janus 的总分 {_jan:.1f} > 一致方案的 {_cons:.1f} —— 它是**严格最优解**')
print('  条件只是「先验对背面的打分低于对正面的打分」，而这几乎总成立。')
print('  所以 Janus 不是优化没收敛，而是逐视角独立目标本身的最优解。')

# 什么时候 Janus 不再最优
print('\\n什么时候「一致」才会胜出：')
print(' back_pref   一致的总分   Janus 的总分   谁胜')
for bp in [0.2, 0.5, 0.8, 1.0, 1.2]:
    s = janus_scores(back_pref=bp, n_views=2)
    c = s['一致（前=正面, 后=背面）'][1]; j = s['Janus（每一侧都是正面）'][1]
    print(f'  {bp:8.1f}    {c:10.1f}   {j:12.1f}   {"一致" if c > j else ("平" if c == j else "Janus")}')
assert janus_scores(back_pref=1.2)['一致（前=正面, 后=背面）'][1] > \\
       janus_scores(back_pref=1.2)['Janus（每一侧都是正面）'][1]
print('\\n✓ 只有当先验对「背面」的打分**高于**正面时，一致方案才胜出。')
print('  所以修法必须改**目标**，不能改优化器：')
print('  ① 视角条件化（Zero-1-to-3）：让后视的先验对「背面」打高分')
print('     —— 等价于把 back_pref 提到 1.0 以上')
print('  ② 联合多视角先验（MVDream）：让「不一致」本身变成低分')
print('     —— 这是唯一改了先验**联合结构**的做法')
print('  ③ 几何正则：最弱，因为它不改先验的偏置，只加了一个竞争项')

# ② 为什么更彻底：构造一个联合先验
print('\\n构造一个「联合」先验来看 ② 为什么更彻底：')
def joint_scores(consistency_bonus):
    '''联合先验：逐视角分 + 一致性奖励（Janus 拿不到）。'''
    s = janus_scores(n_views=2)
    return {'一致': s['一致（前=正面, 后=背面）'][1] + consistency_bonus,
            'Janus': s['Janus（每一侧都是正面）'][1] + 0.0}
print(' 一致性奖励   一致    Janus   谁胜')
for cb in [0.0, 0.4, 0.8, 1.2]:
    j = joint_scores(cb)
    print(f'  {cb:9.1f}   {j["一致"]:5.1f}   {j["Janus"]:5.1f}   '
          f'{"一致" if j["一致"] > j["Janus"] else "Janus"}')
assert joint_scores(1.0)['一致'] > joint_scores(1.0)['Janus']
print('\\n✓ 一致性奖励超过 0.8 时「一致」才胜出（正好是 front-back 的打分差）。')
print('  而 ①（视角条件化）仍然是逐视角独立打分 —— 它只是改了每个视角的打分函数，')
print('  没有引入「视角之间必须一致」这个约束。所以它减轻偏置但不改变结构。')
print('  ② 直接让不一致变成低分，于是 Janus 不再是最优解 ——')
print('  代价是先验必须重新训练成多视角的，而那需要 3D 或多视角数据。')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · SDS 的期望梯度（闭式）

实现 `my_sds_grad(cfg, t_lo, t_hi, n_t, w_mode, grid)`：
用高斯-埃尔米特求积算 $\\mathbb E_\\epsilon$、用细网格算 $\\mathbb E_t$。

$$g(x) = \\frac{1}{n_t}\\sum_t w(t)\\,\\alpha_t\\sum_k \\mathrm{HW}_k\\,
\\hat\\epsilon(\\alpha_t x + \\sigma_t\\,\\mathrm{HN}_k,\\, t)$$

其中 $\\hat\\epsilon = -\\sigma_t\\,\\texttt{score\\_pt}$；
`cfg != 1` 时用宽的零均值高斯（方差 $4\\alpha_t^2+\\sigma_t^2$）当无条件先验做外推。"""),

code("""def my_sds_grad(cfg=1.0, t_lo=0.02, t_hi=0.98, n_t=120, w_mode='sigma2', grid=GRID):
    '''返回与 grid 同长的期望梯度数组。'''
    # TODO: ts = (arange(n_t)+0.5)/n_t*(t_hi-t_lo) + t_lo ; A_, S_ = sched(ts)
    #       对每个 (a, s)：
    #          w = s² / 1 / (a/s)² / 1/s²   按 w_mode
    #          acc = Σ_k HW[k] * eh，其中 xt = a*grid + s*HN[k]，eh = -s*score_pt(xt,a,s)
    #          cfg != 1 时：eu = -s*(-(xt)/(a²*4 + s²)) ; eh = eu + cfg*(eh-eu)
    #          g += w*a*acc
    #       返回 g/n_t
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
# ① 与参考实现逐位一致（4 组配置）
for _kw in [dict(), dict(cfg=7.5), dict(t_hi=0.5), dict(w_mode='snr')]:
    _a = my_sds_grad(**_kw); _b = sds_grad_exact(**_kw)
    assert _a.shape == GRID.shape, f'形状 {_a.shape}'
    assert np.allclose(_a, _b, rtol=1e-12, atol=1e-14), f'{_kw} 与参考不符'

# ② 奇对称：先验对称（μ=±2 等权），所以 g 应是奇函数
_g = my_sds_grad()
assert np.allclose(_g, -_g[::-1], atol=1e-10), '先验对称时 g 应为奇函数'
assert abs(np.interp(0.0, GRID, _g)) < 1e-10, 'g(0) 应为 0'

# ③ 与蒙特卡洛的期望一致
for _x in [-1.0, 0.6, 1.8]:
    _i = int(np.argmin(np.abs(GRID - _x)))
    _mc = np.array([sds_grad_mc(_x, 200, 3300+_j) for _j in range(16)])
    assert abs(_g[_i] - _mc.mean()) < 4*_mc.std()/np.sqrt(16) + 0.02, \\
        f'x={_x}: 闭式 {_g[_i]:.5f} vs MC {_mc.mean():.5f}±{_mc.std()/4:.5f}'

# ④ n_t 与 grid 的分辨率不敏感（求积已收敛）
_g_fine = my_sds_grad(n_t=400)
assert np.allclose(_g, _g_fine, atol=2e-4), 'n_t=120 应已收敛'

# ⑤ cfg 越大梯度幅度越大（近线性）
_mags = [np.abs(my_sds_grad(cfg=c)).max() for c in [1.0, 10.0, 100.0]]
assert _mags[0] < _mags[1] < _mags[2], f'应单调，实测 {_mags}'
assert _mags[2]/_mags[0] > 50, f'cfg 100 倍应让幅度涨 50 倍以上，实测 {_mags[2]/_mags[0]:.0f}'

# ⑥ 只采高噪段时 g 只有一个零点（在 0）
_g_hi = my_sds_grad(t_lo=0.5, t_hi=0.98)
_z = np.where(np.diff(np.sign(_g_hi)) != 0)[0]
assert len(_z) == 1, f't>=0.5 时应只有一个零点，实测 {len(_z)} 个'
print(f'✓ 练习 1 通过：4 组配置与参考逐位一致；g 是奇函数；'
      f'与 MC 期望一致；n_t=120 已收敛')
print(f'  cfg 1/10/100 的 max|g| = {_mags[0]:.3f}/{_mags[1]:.3f}/{_mags[2]:.3f}'
      f'（涨 {_mags[2]/_mags[0]:.0f} 倍）；t≥0.5 时只有一个零点')"""),

md("""### 📖 参考答案 1"""),

code("""def my_sds_grad(cfg=1.0, t_lo=0.02, t_hi=0.98, n_t=120, w_mode='sigma2', grid=GRID):
    ts = (np.arange(n_t) + 0.5)/n_t*(t_hi - t_lo) + t_lo
    A_, S_ = sched(ts)
    g = np.zeros_like(grid)
    for a, s in zip(A_, S_):
        if w_mode == 'sigma2':       w = s**2
        elif w_mode == 'one':        w = 1.0
        elif w_mode == 'snr':        w = (a/s)**2
        elif w_mode == 'inv_sigma2': w = 1.0/s**2
        else: raise ValueError(w_mode)
        acc = np.zeros_like(grid)
        for e, ww in zip(HN, HW):
            xt = a*grid + s*e
            eh = -s*score_pt(xt, a, s)
            if cfg != 1.0:
                eu = -s*(-(xt)/(a**2*4.0 + s**2))
                eh = eu + cfg*(eh - eu)
            acc += ww*eh
        g += w*a*acc
    return g/n_t

print('参考答案 1 已定义')
print('要点一：能写出这个闭式，全靠 -ε 项的期望为 0（第 1 节）。')
print('       所以「那一项是多余的吗」这个问题的答案是：它对期望多余、对方差不多余。')
print('要点二：自测 ② 的奇对称是一个免费的正确性检查 ——')
print('       先验对称时 g 必须是奇函数，而这能抓住绝大多数索引/符号错误。')
print('要点三：自测 ⑥ 是本模块最重要的结构性事实：只采高噪段时 g 只有一个零点。')
print('       也就是两个模式在平滑后已不可区分 —— 那不是收敛问题，是目标本身变了。')"""),

md("""### ✏️ 练习 2 · 找不动点并分类

实现 `my_fixed_points(g, grid)`：返回 `[(位置, 斜率, 类型)]`。
在 `g` 变号处用线性插值定位零点；因为更新是 $x \\leftarrow x - lr\\cdot g$，
所以 $g' > 0$ 是**吸引子**、$g' < 0$ 是**分水岭**。"""),

code("""def my_fixed_points(g, grid=GRID):
    '''返回 [(位置, 斜率, '吸引子'/'分水岭')]。'''
    # TODO: 对 np.where(np.diff(np.sign(g)) != 0)[0] 里的每个 i：
    #         斜率 sl = (g[i+1]-g[i])/(grid[i+1]-grid[i])
    #         位置 x0 = grid[i] - g[i]*(grid[i+1]-grid[i])/(g[i+1]-g[i])
    #         类型 = '吸引子' if sl > 0 else '分水岭'
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_g1 = sds_grad_exact()
_fp = my_fixed_points(_g1)

# ① 与参考实现一致
_ref = fixed_points(_g1)
assert len(_fp) == len(_ref)
for (a1, b1, c1), (a2, b2, c2) in zip(sorted(_fp), sorted(_ref)):
    assert abs(a1-a2) < 1e-12 and abs(b1-b2) < 1e-9 and c1 == c2

# ② 结构：2 个吸引子 + 1 个分水岭，分水岭在 0
_att = sorted(x for x, s, t in _fp if s > 0)
_sad = [x for x, s, t in _fp if s < 0]
assert len(_att) == 2 and len(_sad) == 1, f'实测 {_fp}'
assert abs(_sad[0]) < 1e-6, f'分水岭应在 0，实测 {_sad[0]}'
assert abs(_att[0] + _att[1]) < 1e-9, '两个吸引子应对称'

# ③ 吸引子在 ±1.5663，内移 21.7%
_a = abs(_att[1])
assert abs(_a - 1.5663) < 0.01, f'应在 ±1.5663，实测 ±{_a:.4f}'
assert abs((1 - _a/2.0) - 0.217) < 0.01, f'内移应是 21.7%，实测 {(1-_a/2.0):.1%}'

# ④ 一个人造的简单例子：g(x) = x(x²-1) 在 -1,0,1 有零点
#    注意网格要**避开**零点本身：np.sign 在恰好为 0 处会让 diff 两侧都变号，
#    于是每个零点被数两次。所以这里给网格加一个微小偏移。
_gr = np.linspace(-2, 2, 4001) + 3.7e-7
_gt = _gr*(_gr**2 - 1)
_fp2 = my_fixed_points(_gt, _gr)
assert len(_fp2) == 3, f'应有 3 个零点，实测 {len(_fp2)} 个（网格是否命中了零点？）'
_d = {round(x, 3): t for x, s, t in _fp2}
assert _d[-1.0] == '吸引子' and _d[1.0] == '吸引子' and _d[0.0] == '分水岭', _d
# 而不偏移时会被数两次 —— 这是 np.sign 的一个真实边界情形
_gr_bad = np.linspace(-2, 2, 4001)
assert len(my_fixed_points(_gr_bad*(_gr_bad**2-1), _gr_bad)) == 6, \
    '网格命中零点时每个零点会被数两次'

# ⑤ 只采高噪段：只剩一个吸引子，在 0
_fp3 = my_fixed_points(sds_grad_exact(t_lo=0.5, t_hi=0.98))
assert len(_fp3) == 1 and _fp3[0][2] == '吸引子' and abs(_fp3[0][0]) < 1e-6, \\
    f'实测 {_fp3}'

# ⑥ cfg 大时吸引子外移到真模式之外
_fp4 = my_fixed_points(sds_grad_exact(cfg=100.0))
_a4 = float(np.mean([abs(x) for x, s, t in _fp4 if s > 0 and abs(x) > 0.1]))
assert _a4 > 2.0, f'cfg=100 时应外移，实测 ±{_a4:.4f}'
print(f'✓ 练习 2 通过：cfg=1 时 2 个吸引子 ±{_a:.4f}（内移 {(1-_a/2):.1%}）+ 分水岭在 0')
print(f'  人造例子 x(x²-1) 的三个零点分类正确（而网格命中零点时会被数成 6 个）')
print(f'  t≥0.5 时只剩一个位于 0 的吸引子（两模式合并）')
print(f'  cfg=100 时吸引子在 ±{_a4:.4f}（外移 {(_a4/2-1):.1%}，跑到数据分布之外）')"""),

md("""### 📖 参考答案 2"""),

code("""def my_fixed_points(g, grid=GRID):
    g = np.asarray(g, float); grid = np.asarray(grid, float)
    out = []
    for i in np.where(np.diff(np.sign(g)) != 0)[0]:
        sl = (g[i+1]-g[i])/(grid[i+1]-grid[i])
        x0 = grid[i] - g[i]*(grid[i+1]-grid[i])/(g[i+1]-g[i])
        out.append((float(x0), float(sl), '吸引子' if sl > 0 else '分水岭'))
    return out

print('参考答案 2 已定义')
print('要点一：符号约定容易搞反。更新是 x <- x - lr*g（梯度**下降**），')
print('       所以 g 从负变正（g\\' > 0）时 x 被推回中间 —— 那是吸引子。')
print('       自测 ④ 的 x(x²-1) 专门检查这一点：它在 ±1 是吸引子、0 是分水岭。')
print('要点二：自测 ⑤⑥ 把本模块的两个核心事实变成了断言：')
print('       只采高噪段 -> 模式合并（一个吸引子在 0）；')
print('       cfg 太大 -> 吸引子跑到数据分布之外（过饱和的机制）。')
print('要点三：这两件事都是「不动点在哪」的问题，不是「优化收敛得好不好」。')
print('       所以调 SDS 的正确心态是「我在移动不动点」。')
print('要点四（自测 ④ 的边界情形）：np.sign 在恰好为 0 处返回 0，')
print('       于是 diff(sign) 在零点**两侧**都非零 —— 每个零点被数两次。')
print('       本课的 SDS 梯度不会恰好在网格点上为 0（除了对称中心），所以平时不暴露；')
print('       但换一个函数或换一个网格就会。稳健的写法是先把 |g| < eps 的点当作零点合并。')"""),

md("""### ✏️ 练习 3 · CFG 的两种效应

实现 `my_cfg_effects(cfg)`：返回
`(max|g|, 稳定所需的 lr 上界, 吸引子位置的绝对值)`。

- $lr$ 上界用 $2/\\max\\vert g'\\vert$（梯度下降在二次近似下的稳定条件）；
- 吸引子位置取所有 $\\vert x\\vert > 0.1$ 的吸引子的绝对值均值。"""),

code("""def my_cfg_effects(cfg):
    '''返回 (max|g|, lr 上界, 吸引子位置的绝对值)。'''
    # TODO: g = sds_grad_exact(cfg=cfg)（或 my_sds_grad）
    #       dg = np.gradient(g, GRID)
    #       lr_max = 2.0/np.abs(dg).max()
    #       att = [|x| for x,s,t in my_fixed_points(g) if s>0 and |x|>0.1]
    #       返回 (np.abs(g).max(), lr_max, mean(att))
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_E = {c: my_cfg_effects(c) for c in [1.0, 3.0, 7.5, 30.0, 100.0]}
for _c, _v in _E.items():
    assert len(_v) == 3 and all(np.isfinite(_v)), f'cfg={_c}: {_v}'

# ① 效应①：梯度幅度随 cfg 近线性增长
_m = [_E[c][0] for c in [1.0, 3.0, 7.5, 30.0, 100.0]]
assert all(_m[i] < _m[i+1] for i in range(4)), f'应单调，实测 {_m}'
assert 50 < _m[-1]/_m[0] < 100, f'cfg 100 倍应让幅度涨 50~100 倍，实测 {_m[-1]/_m[0]:.0f}'

# ② lr 上界反比缩小
_l = [_E[c][1] for c in [1.0, 3.0, 7.5, 30.0, 100.0]]
assert all(_l[i] > _l[i+1] for i in range(4)), f'应单调递减，实测 {_l}'
assert _l[0]/_l[-1] > 50, f'lr 上界应缩小 50 倍以上，实测 {_l[0]/_l[-1]:.0f}'

# ③ 效应②：吸引子从内移到外移，cfg≈3 处过零
_p = [_E[c][2] for c in [1.0, 3.0, 7.5, 30.0, 100.0]]
assert _p[0] < 2.0, f'cfg=1 应内移，实测 ±{_p[0]:.4f}'
assert _p[1] > 2.0, f'cfg=3 应已抵消，实测 ±{_p[1]:.4f}'
assert all(_p[i] < _p[i+1] for i in range(4)), f'应单调外移，实测 {_p}'
assert _p[-1] > 2.3, f'cfg=100 应明显外移，实测 ±{_p[-1]:.4f}'

# ④ 与参考实现一致
for _c in [1.0, 7.5]:
    _g = sds_grad_exact(cfg=_c)
    assert abs(_E[_c][0] - np.abs(_g).max()) < 1e-12
    assert abs(_E[_c][1] - 2.0/np.abs(np.gradient(_g, GRID)).max()) < 1e-12

# ⑤ 固定 lr=0.25 时，哪些 cfg 会发散（lr 上界 < 0.25）
_div = [c for c in _E if _E[c][1] < 0.25]
assert 100.0 in _div, 'cfg=100 配 lr=0.25 必然发散'
assert 1.0 not in _div, 'cfg=1 配 lr=0.25 应稳定'
# 实际跑一遍确认：超过稳定界时**不收敛**（落入极限环），而缩放 lr 后精确收敛
_g100 = sds_grad_exact(cfg=100.0)
def _iterate(lr, steps=200, x0=0.9):
    x = x0; tr = []
    for _ in range(steps):
        x = x - lr*float(np.interp(x, GRID, _g100)); tr.append(x)
    return np.array(tr)
_tr_big = _iterate(0.25)          # 超过稳定界
_tr_ok = _iterate(0.25/100.0, steps=4000)
assert _tr_big[-40:].std() > 0.5, \
    f'lr=0.25 超过稳定界，不该收敛，实测后段标准差 {_tr_big[-40:].std():.4f}'
assert _tr_big[-40:].max() - _tr_big[-40:].min() > 2.0, '振幅应与模式间距同量级'
assert _tr_ok[-40:].std() < 1e-9, f'缩放后应精确收敛，实测 {_tr_ok[-40:].std():.2e}'
assert abs(abs(_tr_ok[-1]) - _E[100.0][2]) < 1e-3, '应收敛到 cfg=100 的吸引子'
print(f'✓ 练习 3 通过：max|g| 从 {_m[0]:.3f} 涨到 {_m[-1]:.3f}（{_m[-1]/_m[0]:.0f} 倍）')
print(f'  lr 上界从 {_l[0]:.3e} 掉到 {_l[-1]:.3e}（{_l[0]/_l[-1]:.0f} 倍）')
print(f'  吸引子从 ±{_p[0]:.4f}（内移 {(1-_p[0]/2):.1%}）到 ±{_p[-1]:.4f}'
      f'（外移 {(_p[-1]/2-1):.1%}），cfg≈3 处恰好抵消（±{_p[1]:.4f}）')
print(f'  固定 lr=0.25 时超过稳定界的 cfg: {sorted(_div)}')
print(f'  而超界的后果是**不收敛**：cfg=100 时轨迹落入周期-2 极限环，'
      f'振幅 {_tr_big[-40:].max()-_tr_big[-40:].min():.2f}（模式间距 4.0）')
print(f'  按 1/cfg 缩放后精确收敛到 ±{abs(_tr_ok[-1]):.4f}')"""),

md("""### 📖 参考答案 3"""),

code("""def my_cfg_effects(cfg):
    g = sds_grad_exact(cfg=cfg)
    dg = np.gradient(g, GRID)
    lr_max = 2.0/float(np.abs(dg).max())
    att = [abs(x) for x, s, t in my_fixed_points(g) if s > 0 and abs(x) > 0.1]
    return float(np.abs(g).max()), lr_max, float(np.mean(att))

print('参考答案 3 已定义')
print('要点一：这道题的全部意义在于**把两种效应分开**。')
print('       我第一次做实验时把它们混在一起 —— 固定 lr=0.25 配 cfg=100，')
print('       400 步后 x 是 1e100，而我把那个数当成了「CFG 的效应」。')
print('       它其实只是效应①（幅度）导致的发散。')
print('要点二：效应②（形状）才是 CFG 真正买到的东西 ——')
print('       它抵消平滑造成的内移。cfg≈3 恰好抵消，再大就过冲。')
print('       而「过冲」的物理含义是：解被推到比训练数据更极端的地方，')
print('       这正是 SDS 结果「过饱和、对比度过高、颜色过艳」的机制。')
print('要点三：所以比较不同 cfg 必须把 lr 按 1/cfg 缩放，否则比的是步长而不是形状。')"""),

md("""### ✏️ 练习 4 · Janus 的构造与两种修法

实现 `my_janus(front_pref, back_pref, n_views, consistency_bonus)`：
返回 `{'一致': 总分, 'Janus': 总分}`。

- 「一致」= 第一个视角看到正面（得 `front_pref`），其余看到背面（各得 `back_pref`），
  **再加上** `consistency_bonus`（联合先验给的一致性奖励）；
- 「Janus」= 每个视角都看到正面（各得 `front_pref`），**拿不到**一致性奖励。"""),

code("""def my_janus(front_pref=1.0, back_pref=0.2, n_views=2, consistency_bonus=0.0):
    '''返回 {'一致': 总分, 'Janus': 总分}。'''
    # TODO: 一致  = front_pref + back_pref*(n_views-1) + consistency_bonus
    #       Janus = front_pref * n_views
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
# ① 默认参数下 Janus 严格胜出
_s = my_janus()
assert set(_s.keys()) == {'一致', 'Janus'}
assert _s['Janus'] > _s['一致'], f'Janus 应胜出：{_s}'
assert abs(_s['一致'] - 1.2) < 1e-12 and abs(_s['Janus'] - 2.0) < 1e-12, _s

# ② 视角越多，Janus 的优势越大
_gaps = []
for _nv in [2, 3, 4, 6]:
    _x = my_janus(n_views=_nv)
    _gaps.append(_x['Janus'] - _x['一致'])
    assert _x['Janus'] > _x['一致'], f'n_views={_nv} 时 Janus 应仍胜出'
assert all(_gaps[i] < _gaps[i+1] for i in range(3)), f'差距应随视角数增大，实测 _gaps={_gaps}'

# ③ back_pref >= front_pref 时「一致」才胜出（或平）
assert my_janus(back_pref=1.0)['一致'] == my_janus(back_pref=1.0)['Janus'], \\
    'back_pref = front_pref 时应打平'
assert my_janus(back_pref=1.2)['一致'] > my_janus(back_pref=1.2)['Janus']
# 而这正是「视角条件化」在做的事
assert my_janus(back_pref=0.2)['Janus'] > my_janus(back_pref=0.2)['一致']

# ④ 一致性奖励的临界值 = (front - back)*(n_views-1)
for _nv in [2, 3, 4]:
    _crit = (1.0 - 0.2)*(_nv - 1)
    _lo = my_janus(n_views=_nv, consistency_bonus=_crit - 0.01)
    _hi = my_janus(n_views=_nv, consistency_bonus=_crit + 0.01)
    assert _lo['Janus'] > _lo['一致'], f'n_views={_nv}: 略低于临界时 Janus 仍胜'
    assert _hi['一致'] > _hi['Janus'], f'n_views={_nv}: 略高于临界时一致胜'

# ⑤ 一致性奖励**不**改变 Janus 的分数（它拿不到）
for _cb in [0.0, 1.0, 5.0]:
    assert my_janus(consistency_bonus=_cb)['Janus'] == my_janus()['Janus']

# ⑥ 与参考实现一致
for _nv in [2, 4]:
    _r = janus_scores(n_views=_nv)
    _m = my_janus(n_views=_nv)
    assert abs(_m['一致'] - _r['一致（前=正面, 后=背面）'][1]) < 1e-12
    assert abs(_m['Janus'] - _r['Janus（每一侧都是正面）'][1]) < 1e-12
print(f'✓ 练习 4 通过：默认下 Janus {_s["Janus"]:.1f} > 一致 {_s["一致"]:.1f}')
print(f'  视角数 2/3/4/6 时 Janus 的优势 {[f"{g:.1f}" for g in _gaps]} —— 越多越大')
print(f'  两种修法的临界条件：back_pref ≥ front_pref（视角条件化），')
print(f'  或一致性奖励 ≥ (front−back)×(n_views−1)（联合多视角先验）')"""),

md("""### 📖 参考答案 4"""),

code("""def my_janus(front_pref=1.0, back_pref=0.2, n_views=2, consistency_bonus=0.0):
    return {'一致': front_pref + back_pref*(n_views-1) + consistency_bonus,
            'Janus': front_pref*n_views}

print('参考答案 4 已定义')
print('要点一：这道题只是算术，但它说明的是一件结构性的事 ——')
print('       Janus 不是优化失败，而是「逐视角独立打分」这个目标的**严格最优解**。')
print('       所以加迭代、换初值、加正则强度都不改变 2.0 > 1.2 这个不等式。')
print('要点二：自测 ② 说明视角越多 Janus 的优势越大（差距 0.8/1.6/2.4/4.0）——')
print('       所以「多渲几个视角」本身不解决问题，反而放大它。')
print('要点三：两种修法的临界条件不同（自测 ③④）：')
print('       ① 视角条件化：把 back_pref 提到 front_pref 以上 ——')
print('          仍然是逐视角独立打分，只是改了每个视角的打分函数；')
print('       ② 联合先验：一致性奖励 ≥ (front−back)×(n_views−1) ——')
print('          它改的是先验的**联合结构**，所以更彻底。')
print('       而 ② 的代价是先验必须重新训练成多视角的，')
print('       那需要 3D 或多视角数据 —— 也就是回到了「数据」这个瓶颈。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- threestudio（SDS 的标准实现）----
# python launch.py --config configs/dreamfusion-if.yaml --train \
#   system.prompt_processor.prompt="a DSLR photo of a corgi"
#
# 关键超参与本 notebook 的对应：
#   system.guidance.guidance_scale=100          # ← 练习 3 的 cfg（注意配合 lr！）
#   system.guidance.min_step_percent=0.02       # ← t 的下界，**必须小**（第 6 节）
#   system.guidance.max_step_percent=0.98       # ← t 的上界，通常退火
#   system.guidance.weighting_strategy="sds"    # ← w(t) = σ_t²（第 6 节）
#   system.loss.lambda_sds=1.0
#
# 退火 t 上界的常见写法（第 6 节的三阶段）：
#   max_step_percent: [5000, 0.98, 0.5, 5001]   # iter 5000 后从 0.98 降到 0.5
# ⚠ 而 guidance_scale 通常**不**跟着退火 —— 那正是第 6 节末尾说的陷阱

# ---- SDS 梯度的实际实现（threestudio/models/guidance/*.py）----
# with torch.no_grad():
#     noise = torch.randn_like(latents)
#     latents_noisy = self.scheduler.add_noise(latents, noise, t)
#     noise_pred = self.unet(latents_noisy, t, encoder_hidden_states=text_emb)
#     noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
#     noise_pred = noise_pred_uncond + guidance_scale*(noise_pred_text - noise_pred_uncond)
# w = (1 - self.alphas[t])                       # ← w(t)，等价于 σ_t²
# grad = w * (noise_pred - noise)                # ← 那个 -noise 就是练习 1 的控制变量
# target = (latents - grad).detach()
# loss_sds = 0.5*F.mse_loss(latents, target, reduction='sum')/batch_size
# 注意 `.detach()` 与那个 0.5*MSE 的写法：它让自动微分给出 grad 本身 ——
# 而 U-Net 的雅可比被 no_grad 挡掉了（讲解页第 2 节）

# ---- 换成 VSD（ProlificDreamer）：把「找模式」改回「采样」----
#   system.guidance.guidance_scale=7.5          # ← VSD 不需要 cfg=100
#   system.guidance_type="stable-diffusion-vsd-guidance"
# 因为 VSD 的目标是两个分布之间的 KL，而不是一个点的密度 ——
# 所以它不需要用大 cfg 去抵消内移（第 5 节）

# ---- 多视角先验（MVDream）：从根上改 Janus ----
#   system.guidance_type="multiview-diffusion-guidance"   # 一次生成 4 个视角
# 它让「不一致」本身变成低分（练习 4 的 consistency_bonus）
```

**排查清单**

| 症状 | 原因 | 动哪个旋钮 |
|---|---|---|
| 形状「胖」、细节圆滑、部件粘连 | 不动点内移 21.7% | 退火 $t_{\\max}$（$[0.02,0.30]$ 时内移 0.0%）|
| 颜色过饱和、对比度过高 | CFG 过冲（吸引子在数据分布之外）| 降 cfg；若已退火 $t_{\\max}$ 则要降更多 |
| 几百步后 NaN / 数值爆掉 | 梯度幅度 ∝ cfg（cfg=100 时 66 倍）| 按 $1/\\text{cfg}$ 缩 lr，或加梯度裁剪 |
| 早期一直是一团糊 | $t$ 没包含低噪端 | 把 $t$ 下界压到 0.02 |
| 正反两面同一张脸 | Janus —— 目标的最优解 | **必须改目标**：视角条件化或多视角先验 |
| 同一提示词跑十次几乎一样 | **正常** —— 解是不动点 | 要多样性得换目标（VSD）|
| 换随机种子结果几乎不变 | **正常** —— 残余散布只来自梯度噪声 | 同上 |"""),
]
