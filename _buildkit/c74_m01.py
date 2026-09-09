# -*- coding: utf-8 -*-
"""C74 模块 01 · 体渲染与 α 合成的地基。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 体渲染积分是怎么来的、它的三个物理量各是什么；"
                   "② 为什么它的离散化叫「α 合成」，而<strong>对分段常数密度它是精确的</strong>；"
                   "③ <strong>为什么 3DGS 必须排序而 NeRF 不必</strong>；"
                   "④ 提前终止能省多少、代价是什么；"
                   "⑤ α 合成的反向传播为什么要<strong>从后往前</strong>走"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_volume_rendering.ipynb'
                       '（闭式解核对 / <strong>误差 ∝ 1/N²</strong> / '
                       '顺序敏感性随 α 与个数的变化 / '
                       '<strong>提前终止的收益与误差上界</strong> / '
                       '解析梯度 vs 数值梯度 / <strong>1/(1−α) 的病态</strong>）'),
    ("核心参考", "Max, <em>Optical Models for Direct Volume Rendering</em>（TVCG 1995）· "
                 "Kajiya &amp; Von Herzen（SIGGRAPH 1984，体渲染方程）· "
                 "Porter &amp; Duff, <em>Compositing Digital Images</em>（SIGGRAPH 1984，"
                 "α 合成的来源）· "
                 "Mildenhall et al., <em>NeRF</em>（ECCV 2020，式 (3) 即本模块第 2 节）· "
                 "Kerbl et al., <em>3D Gaussian Splatting</em>（SIGGRAPH 2023）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("integral", "体渲染积分：三个物理量与一个微分方程", "".join([
        P("先把式子写出来，再解释它每一部分从哪来。沿一条从相机出发的射线，"
          "位置用 $t$ 参数化，像素颜色是"),
        MATH(r"C = \int_{t_n}^{t_f} T(t)\,\sigma(t)\,c(t)\,\mathrm{d}t,"
             r"\qquad T(t) = \exp\Bigl(-\int_{t_n}^{t}\sigma(s)\,\mathrm{d}s\Bigr)"),
        TABLE(["量", "名字", "单位", "物理含义"], [
            ["$\\sigma(t)$", "体密度 / 消光系数 (volume density)",
             "$\\mathrm{m}^{-1}$",
             "<strong>单位长度上光被吸收或散射掉的概率</strong>。"
             "<em>注意它不是「不透明度」，量纲都不同</em>"],
            ["$c(t)$", "自发光颜色 (emitted radiance)", "无量纲（辐射度）",
             "这一点<em>朝相机方向</em>发出的颜色。"
             "<strong>3DGS 里它是球谐的求值结果</strong>（模块 05）"],
            ["$T(t)$", "透射率 (transmittance)", "无量纲，$\\in(0,1]$",
             "从 $t_n$ 走到 $t$ 还<strong>没被挡住</strong>的比例。"
             "<em>它是一个累积量，这一点决定了后面的一切</em>"],
        ]),
        H3("$T$ 的指数形式不是假设，是一个一阶微分方程的解"),
        P("考虑一束强度 $I$ 的光走过一小段 $\\mathrm{d}t$。"
          "「密度」的定义就是：这一段里被吸收掉的比例是 $\\sigma\\,\\mathrm{d}t$。所以"),
        MATH(r"\frac{\mathrm{d}I}{\mathrm{d}t} = -\sigma(t)\,I(t)"
             r"\;\Longrightarrow\; I(t) = I(t_n)\exp\Bigl(-\int\sigma\Bigr)"),
        DUAL(
            "<strong>把这件事想成「一段一段地活下来」。</strong>"
            "<em>穿过第一段活下来的概率是 $1-\\sigma\\delta$，第二段又是 $1-\\sigma\\delta$……"
            "走 $N$ 段活下来的概率是 $(1-\\sigma\\delta)^N$，而 $N\\to\\infty$ 时它就是 $e^{-\\sigma L}$</em>。"
            "<strong>指数来自「独立事件的连乘」，而不是任何经验拟合。</strong>",
            "<strong>而积分里的 $T(t)\\sigma(t)$ 这个乘积有一个概率解释，"
            "它是本模块后面全部结论的来源：</strong>"
            "<em>$T(t)\\sigma(t)\\,\\mathrm{d}t$ 是「光子恰好在 $t$ 处第一次被吸收」的概率密度</em>"
            "（活着走到 $t$ × 在 $t$ 处被吸收）。"
            "<strong>所以 $C$ 是「第一次碰撞点的颜色」的期望</strong>，"
            "而 $\\int T\\sigma\\,\\mathrm{d}t = 1 - T(t_f) \\le 1$——"
            "<em>它是一个可能有「漏光」的概率分布，漏掉的那部分 $T(t_f)$ 就是背景</em>。"),
        CALLOUT("intuition",
                "<strong>一句话记住三个量的关系</strong>："
                "$\\sigma$ 是<em>局部</em>的性质（这一点有多密），"
                "$T$ 是<em>路径</em>的性质（前面挡了多少），"
                "$C$ 是<em>期望</em>。"
                "<strong>「$T$ 依赖路径」正是「必须排序」的全部原因</strong>——"
                "第 3 节会把这句话量出来。"),
    ])),

    # ============================================================== 2
    ("alpha", "离散化：为什么它叫 α 合成，以及一个精确性结论", "".join([
        P("把射线切成 $N$ 段，第 $i$ 段长 $\\delta_i$、密度 $\\sigma_i$、颜色 $c_i$。"
          "在这一段内把 $\\sigma$ 和 $c$ 当常数，那么这一段的「被吸收概率」是"),
        MATH(r"\alpha_i = 1 - \exp(-\sigma_i \delta_i)\;\in(0,1)"),
        P("而走到第 $i$ 段之前的透射率是前面各段「活下来」概率的乘积。于是"),
        MATH(r"C = \sum_{i=1}^{N} T_i\,\alpha_i\,c_i,\qquad T_i = \prod_{j<i}(1-\alpha_j)"),
        DUAL(
            "<strong>这个式子和图形学里 30 年前的 α 合成（Porter–Duff, 1984）逐字相同。</strong>"
            "<em>把一叠半透明胶片从前往后叠起来，就是这个公式</em>。"
            "<strong>所以「体渲染」与「α 合成」不是两件事："
            "α 合成是体渲染积分在分段常数假设下的离散形式，"
            "而 $\\alpha_i = 1-e^{-\\sigma_i\\delta_i}$ 是两者之间唯一的翻译。</strong>",
            "<strong>而 $\\alpha$ 与 $\\sigma$ 的区别值得单独记一下，"
            "因为混淆它们会导致一类很难查的 bug。</strong>"
            "<em>$\\sigma$ 有量纲（$\\mathrm{m}^{-1}$）、可以任意大、与步长无关；"
            "$\\alpha$ 无量纲、被夹在 $(0,1)$、<strong>依赖步长</strong></em>。"
            "<strong>NeRF 的网络输出 $\\sigma$，所以换采样步长时 $\\alpha$ 自动跟着变；"
            "3DGS 直接存 $\\alpha$，所以它<em>没有步长</em>这个概念</strong>——"
            "<em>这是两者最实质的一个差别，第 6 节会说清后果</em>。"),
        H3("对分段常数密度，α 合成是精确的——连 $N{=}1$ 都对"),
        P("$\\sigma$、$c$ 在长度 $L$ 上恒定时，积分有闭式解 $C = c\\,(1-e^{-\\sigma L})$。"
          "把这段均分成 $N$ 段做 α 合成："),
        MATH(r"\sum_{i=1}^{N} (1-\alpha)^{i-1}\alpha c"
             r"= c\,\alpha\,\frac{1-(1-\alpha)^N}{\alpha}"
             r"= c\bigl(1-(1-\alpha)^N\bigr) = c\bigl(1-e^{-\sigma L}\bigr)"),
        TABLE(["$N$", "α 合成结果", "与闭式解之差"], [
            ["1", "0.760170345305709", "<strong>0</strong>"],
            ["2", "0.760170345305709", "<strong>0</strong>"],
            ["4", "0.760170345305709", "<strong>0</strong>"],
            ["16", "0.760170345305709", "1.1e−16"],
            ["256", "0.760170345305708", "8.9e−16"],
        ]),
        CALLOUT("paper",
                "<strong>这个结论把「离散化误差」的来源锁死在唯一一处：$\\sigma$ 或 $c$ 在一段之内发生变化。</strong>"
                "<em>α 合成本身不引入任何误差，$N$ 也不需要大</em>。"
                "<strong>而当 $\\sigma$ 沿射线变化时，中点法则的误差是 $\\propto 1/N^2$（二阶），不是 $\\propto 1/N$</strong>——"
                "notebook 量到每翻一倍 $N$ 误差降到 <strong>1/4.00</strong>。"
                "<em>这解释了为什么 NeRF 用 64+128 个采样点就够了：二阶收敛下，"
                "把 64 加到 128 只换来 4 倍精度，边际收益极快地耗尽</em>。"),
    ])),

    # ============================================================== 3
    ("order", "顺序：为什么 3DGS 必须排序，而 NeRF 不必", "".join([
        P("$T_i = \\prod_{j<i}(1-\\alpha_j)$ 里的 $j<i$ 说明 $C$ **依赖求和的顺序**。"
          "α 合成不是可交换的。下面是量出来的结果（8 个基元、2000 次随机置换、"
          "满量程 1.0）："),
        TABLE(["$\\alpha$ 的范围", "中位偏差", "P95", "最大", "说明"], [
            ["$[0.30, 0.90]$", "<strong>0.2929</strong>", "0.5843", "0.8394",
             "<strong>接近满量程的一半</strong>"],
            ["$[0.10, 0.70]$", "<strong>0.1961</strong>", "0.4200", "0.6394",
             "3DGS 的典型区间"],
            ["$[0.01, 0.05]$", "0.0027", "0.0061", "0.0099",
             "NeRF 的典型区间（密采样下每点 α 很小）"],
        ]),
        DUAL(
            "<strong>两个区间差了 73 倍。而这不是巧合，可以一阶展开看出来：</strong>"
            "<em>$\\alpha$ 都很小时 $T_i = \\prod_{j<i}(1-\\alpha_j) \\approx 1-\\sum_{j<i}\\alpha_j$，"
            "代进 $C$ 后一阶项是 $\\sum_i \\alpha_i c_i$——<strong>它与顺序无关</strong>，"
            "顺序只影响二阶项 $\\sum_{i}\\sum_{j<i}\\alpha_i\\alpha_j c_i$</em>。"
            "<strong>所以顺序敏感度是 $O(\\alpha^2)$，而 $\\alpha$ 从 0.03 涨到 0.4 是 13 倍，"
            "平方后约 180 倍——量级对得上。</strong>",
            "<strong>于是两种方法在「排序」上的处境完全不同。</strong>"
            "<em>NeRF 沿射线行进，采样点<strong>天然按 $t$ 单调</strong>，"
            "顺序是免费的；而且它的 $\\alpha$ 很小，就算错了也不致命</em>。"
            "<strong>3DGS 把成千上万个高斯投影到屏幕上，它们在内存里的顺序与深度毫无关系，"
            "而每个高斯的 $\\alpha$ 又大</strong>——"
            "<em>所以它必须<strong>显式地按深度排序</strong>，"
            "而这个排序就是模块 03 里最贵的一步（50 万高斯要排 200 万个键）</em>。",
        ),
        CALLOUT("warn",
                "<strong>一个必须说清的诚实之处：3DGS 排的是「高斯中心的深度」，"
                "而不是「每个像素上的真实前后关系」。</strong>"
                "<em>两个相互穿插的椭球，在某些像素上 A 在前、在另一些像素上 B 在前，"
                "但它们在整个 tile 里只有一个顺序</em>。"
                "<strong>这是 3DGS 的一个已知近似</strong>，"
                "它在相机转动时会造成「弹跳」（popping）——"
                "<em>顺序在某个视角突然翻转，画面跳一下。"
                "后续工作（StopThePop, 2024）用逐像素或分层排序来缓解，代价是速度</em>。"),
    ])),

    # ============================================================== 4
    ("saturate", "饱和与提前终止：实时性的第一来源", "".join([
        P("$T_i$ 是单调递减的乘积。一旦它足够小，后面所有基元的贡献 $T_i\\alpha_i c_i$ "
          "都被压到可忽略——**可以直接停下来**。累积不透明度 $1-T$ 的增长："),
        TABLE(["每个 $\\alpha$", "1 个", "4 个", "16 个", "32 个", "达 99% 需要", "达 99.9% 需要"], [
            ["0.1", "0.1000", "0.3439", "0.8147", "0.9657", "<strong>44 个</strong>", "66 个"],
            ["0.2", "0.2000", "0.5904", "0.9719", "0.9992", "<strong>21 个</strong>", "31 个"],
            ["0.3", "0.3000", "0.7599", "<strong>0.9967</strong>", "0.99999", "<strong>13 个</strong>", "20 个"],
            ["0.5", "0.5000", "0.9375", "0.99999", "1.0000", "<strong>7 个</strong>", "10 个"],
        ]),
        DUAL(
            "<strong>「达 99% 需要多少个」有闭式解：$n = \\lceil \\ln(0.01)/\\ln(1-\\alpha)\\rceil$。</strong>"
            "<em>它对 $\\alpha$ 是<strong>对数</strong>依赖，所以 $\\alpha$ 从 0.1 涨到 0.5（5 倍）"
            "只把 $n$ 从 44 降到 7（6.3 倍）——两者大致成反比</em>。"
            "<strong>关键的量级是：不管 $\\alpha$ 多少，都是「几十个」，"
            "而不是「几百个」或「几个」。</strong>",
            "<strong>而模块 03 会量出：1920×1080 下每个 tile 平均要处理 245 个高斯。</strong>"
            "<em>而在 $T_{\\min}{=}10^{-4}$ 的判据下，notebook 量到只需处理 <strong>19</strong> 个 —— "
            "<strong>92.2% 的工作可以被提前终止省掉</strong></em>。"
            "<strong>这是 3DGS 实时性最大的一块来源，而它完全是 $T_i$ 单调递减这个结构性质带来的。</strong>"
            "<em>注意它是<strong>逐 tile</strong>生效的：天空那样的 tile 只有几个高斯，"
            "近处物体的 tile 会在第 19 个左右停下，"
            "而<strong>最坏情况（一整 tile 都是低 $\\alpha$ 的雾）不会终止</strong>——"
            "所以提前终止改善的是平均而不是最坏时延</em>。",
        ),
        H3("代价：它是一个近似，而且是有界的"),
        P("在 $T < T_{\\min}$ 时停下，丢掉的是 $\\sum_{i \\ge k} T_i\\alpha_i c_i$。"
          "因为 $T_i \\le T_k < T_{\\min}$ 且 $\\sum_{i\\ge k}\\alpha_i \\prod(1-\\alpha) \\le 1$，"
          "所以丢掉的量 **严格小于** $T_{\\min}\\cdot\\max_i c_i$。"),
        CALLOUT("intuition",
                "<strong>所以 $T_{\\min}$ 直接就是误差上界，可以按需要选。</strong>"
                "<em>官方实现用 $T_{\\min} = 10^{-4}$，对应最大误差 $10^{-4}$——"
                "远小于 8 bit 显示的 1/255 ≈ 0.0039，所以视觉上完全无损</em>。"
                "<strong>而顺带一个 float32 的坑：$\\alpha=0.3$ 时 256 个高斯后 $T = 2.2\\times10^{-40}$，"
                "已经下溢为 0</strong>——"
                "<em>所以提前终止不只是优化，它还避免了在下溢的 $T$ 上继续做无意义的乘法</em>。"),
    ])),

    # ============================================================== 5
    ("backward", "反向传播：为什么必须从后往前走", "".join([
        P("训练要 $\\partial C/\\partial\\alpha_i$ 与 $\\partial C/\\partial c_i$。颜色那一项很简单："),
        MATH(r"\frac{\partial C}{\partial c_i} = T_i\,\alpha_i"),
        P("$\\alpha_i$ 那一项不简单，因为 $\\alpha_i$ 同时出现在**自己这一项**里，"
          "又出现在**后面所有** $T_k$（$k>i$） 里："),
        MATH(r"\frac{\partial C}{\partial \alpha_i} = T_i c_i"
             r" - \frac{1}{1-\alpha_i}\underbrace{\sum_{k>i} T_k \alpha_k c_k}_{S_{>i}}"),
        DUAL(
            "<strong>第二项的形状决定了实现方式：它需要「$i$ 之后所有项的和」。</strong>"
            "<em>所以反向传播必须<strong>从最远的基元往近处走</strong>，"
            "一边走一边累加 $S_{>i}$</em>。"
            "<strong>前向从近到远累积 $T$，反向从远到近累积 $S$——"
            "这个「一来一回」是 3DGS 那个 CUDA 内核的核心结构</strong>，"
            "<em>而它意味着反向传播必须知道前向的<strong>顺序</strong>，"
            "所以排序结果要么存下来、要么重算</em>。",
            "<strong>而 $1/(1-\\alpha_i)$ 是个明显的病态点。</strong>"
            "<em>$\\alpha_i \\to 1$ 时它发散：$\\alpha=0.99$ 时是 100，$\\alpha=0.9999$ 时是 $10^4$</em>。"
            "<strong>真实实现有两道防线</strong>："
            "① <strong>$\\alpha$ 存成 logit 过 sigmoid，永远到不了 1</strong>；"
            "② <strong>官方内核不算 $1/(1-\\alpha)$，而是在反向走的过程中"
            "顺便把 $T$ 也<em>反推</em>回来</strong>——"
            "<em>它保存前向结束时的 $T_{\\text{final}}$，然后每退一步做一次除法恢复 $T_i$，"
            "把病态限制在同一个量上而不是每项都乘一次</em>。",
        ),
        CALLOUT("danger",
                "<strong>这里有一个真实会遇到的坑：反向传播必须重放<em>提前终止</em>。</strong>"
                "<em>如果前向在第 19 个高斯停了，反向却对全部 245 个求梯度，"
                "那些被跳过的高斯会收到<strong>本该是零的梯度</strong></em>——"
                "<strong>结果是被完全遮挡的高斯也在被优化，"
                "它们会长成「看不见但吃内存」的浮物</strong>。"
                "<em>官方内核的做法是：前向记下每个 tile 实际处理到第几个，反向只走那么多</em>。"),
    ])),

    # ============================================================== 6
    ("byproducts", "同一条积分的两个副产物：累积不透明度与深度图", "".join([
        P("体渲染积分不只产出颜色。同一组权重 $w_i = T_i\\alpha_i$ 换一个被加权的量，"
          "就得到 3DGS 实际会输出的另外两张图："),
        MATH(r"A = \sum_i w_i = 1 - T_{\text{final}},"
             r"\qquad D_{\text{raw}} = \sum_i w_i\, t_i,"
             r"\qquad D_{\text{norm}} = \frac{\sum_i w_i t_i}{\sum_i w_i}"),
        TABLE(["量", "是什么", "用途"], [
            ["$A$ = 累积不透明度 (accumulated alpha)",
             "「这条射线一共被挡住了多少」，$\\in[0,1)$",
             "<strong>合成背景：$C_{\\text{final}} = C + T_{\\text{final}}\\cdot C_{\\text{bg}}$</strong>；"
             "也直接当<em>前景 mask</em> 用；"
             "训练时常加一项让它逼近 0/1，逼表示变「实心」"],
            ["$D_{\\text{raw}}$ = 未归一化期望深度", "$w_i$ 加权的深度",
             "<strong>它有偏，见下</strong>"],
            ["$D_{\\text{norm}}$ = 归一化深度", "除以 $A$ 之后的加权平均深度",
             "深度监督、法向估计、导出网格（C75）、与 LiDAR 对齐"],
        ]),
        H3("$D_{\\text{raw}}$ 的偏差有闭式形式，而且不小"),
        P("取最简的情形：**一个** $\\alpha=0.9$ 的高斯，位于 $t=10\\,\\mathrm{m}$。"
          "那么 $w_1 = 0.9$，于是 $D_{\\text{raw}} = 0.9\\times 10 = 9.0\\,\\mathrm{m}$——"
          "**偏小 1 m，而真相只有一个表面、深度毫无疑义。**"),
        MATH(r"D_{\text{raw}} = A\cdot D_{\text{norm}}"
             r"\;\Longrightarrow\; \text{偏差} = -(1-A)\cdot D_{\text{norm}}"),
        TABLE(["配置（表面在 10 m 附近）", "累积 $A$", "$D_{\\text{raw}}$", "$D_{\\text{norm}}$", "$D_{\\text{raw}}$ 的相对偏差"], [
            ["1 个高斯，$\\alpha=0.9$", "0.9000", "9.000", "<strong>10.000</strong>", "<strong>−10.0%</strong>"],
            ["20 个，$\\alpha=0.05$", "0.6415", "6.666", "10.391", "<strong>−33.3%</strong>"],
            ["20 个，$\\alpha=0.10$", "0.8784", "9.058", "10.312", "−9.4%"],
            ["20 个，$\\alpha=0.20$", "0.9885", "10.071", "10.188", "＋0.7%"],
            ["5 个，$\\alpha=0.90$", "1.0000", "10.011", "10.011", "0.0%"],
        ]),
        DUAL(
            "<strong>规律很干净：$D_{\\text{raw}}$ 的相对偏差就是 $-(1-A)$，"
            "所以它只在射线被完全挡住（$A\\to1$）时才正确。</strong>"
            "<em>而「被完全挡住」恰恰是训练早期<strong>不</strong>成立的情形——"
            "那时候高斯还稀、$\\alpha$ 还小，$A$ 可能只有 0.6</em>。"
            "<strong>于是一个很常见的现象有了解释：用未归一化深度做监督时，"
            "早期的深度损失会把高斯往相机方向拉</strong>，"
            "<em>因为减小 $t$ 与增大 $A$ 对这个损失是等效的，而前者更容易</em>。",
            "<strong>但归一化也不是免费的：$A$ 很小的地方（天空、物体边缘）"
            "$D_{\\text{norm}}$ 的分母接近 0，噪声被放大。</strong>"
            "<em>实践中的做法是两者都输出，并<strong>用 $A$ 当置信度把低 $A$ 的像素屏蔽掉</strong>"
            "（常见阈值 $A>0.5$ 或 $0.9$）</em>。"
            "<strong>还有第三种口径：$w$ 的<em>中位数</em>深度</strong>（表格里 20 个 $\\alpha=0.2$ 时是 10.150）——"
            "<em>它对「一层薄雾 + 一个实心表面」这种双峰分布比均值稳，"
            "所以在做网格提取时（C75）常用它而不是均值</em>。"),
        CALLOUT("warn",
                "<strong>三个口径会给出不同的数，而它们都叫「深度图」。</strong>"
                "<em>比较两份 3DGS 的深度结果、或把 3DGS 深度与 LiDAR 对齐时，"
                "先确认口径一致</em>——"
                "<strong>上表第二行里 $D_{\\text{raw}}$ 与 $D_{\\text{norm}}$ 差了 3.7 m，"
                "这个量级足以让任何评测结论翻转。</strong>"),
    ])),

    # ============================================================== 7
    ("position", "3DGS 在这个框架里的位置：一个高斯 = 一个 α", "".join([
        TABLE(["", "NeRF", "3DGS"], [
            ["基元是什么", "射线上的一个<strong>采样点</strong>",
             "空间里的一个<strong>各向异性椭球</strong>"],
            ["$\\sigma$ 从哪来", "MLP 的输出，每个采样点跑一次网络",
             "<strong>不存在 $\\sigma$</strong>——直接存 $\\alpha$，"
             "乘上椭球在该像素的高斯衰减值"],
            ["$\\delta$（步长）", "相邻采样点的间距，随采样策略变",
             "<strong>没有步长概念</strong>。"
             "<em>「一个高斯 = 一个 α」，$\\alpha_i = \\alpha^{(g)}\\exp(-\\frac12 d^\\top\\Sigma'^{-1}d)$</em>"],
            ["每像素的基元数", "64 + 128（粗采样 + 细采样）",
             "<strong>该 tile 里排过序的高斯，直到 $T<10^{-4}$（典型十几个）</strong>"],
            ["顺序从哪来", "沿 $t$ 单调，<strong>免费</strong>",
             "<strong>必须显式排序</strong>（模块 03 里最贵的一步）"],
            ["典型 $\\alpha$ 量级", "0.01 – 0.05", "<strong>0.1 – 0.9</strong>"],
        ]),
        DUAL(
            "<strong>第三行是最容易被忽略但最有后果的一条。</strong>"
            "<em>3DGS 没有步长，等价于说它<strong>放弃了「同一段物质、不同采样密度应给出同样结果」这个性质</strong>。"
            "在 NeRF 里，把 64 个采样点换成 128 个，渲出的图基本不变（第 2 节：误差 $\\propto 1/N^2$）；"
            "在 3DGS 里，把一个高斯换成两个体积各半的高斯，"
            "<strong>渲出的图会变</strong>，因为 $\\alpha$ 不是从密度算来的</em>。",
            "<strong>而这恰好是模块 04 里「分裂」这个操作起作用的机制</strong>："
            "<em>分裂不是「等价变换 + 更细的表示」，它<strong>真的改变了渲染结果</strong>，"
            "所以分裂之后必须继续优化才能收敛回去</em>。"
            "<strong>反过来说，这也是 3DGS 的表示能力比「体密度场 + 固定采样」更强的地方</strong>——"
            "<em>它可以用一个大高斯精确表示一层硬边的表面，"
            "而基于密度的方法要在那里放很陡的 $\\sigma$，进而需要很密的采样</em>。"),
        CALLOUT("intuition",
                "<strong>$\\alpha$ 大还有一个不在渲染速度上的后果：它让损失曲面更陡。</strong>"
                "<em>$\\partial C/\\partial c_i = T_i\\alpha_i$，而 $T_i$ 随 $\\alpha$ 增大"
                "而更快衰减——所以前几个基元的梯度很大、后面的几乎为零</em>。"
                "<strong>于是 3DGS 的优化天然是「近处先收敛、远处后收敛」的，"
                "而被完全遮挡的高斯几乎收不到梯度</strong>"
                "<em>（这既是它能快速收敛的原因，也是浮物问题的来源之一——模块 05 第 5 节）</em>。"),
        CALLOUT("paper",
                "<strong>带走这一条：本模块的公式对 NeRF 与 3DGS 是同一条，"
                "两者的差别全在「基元是什么」以及由此带来的 $\\alpha$ 量级。</strong>"
                "<em>$\\alpha$ 大 ⟹ 必须排序、可以提前终止、每像素只要十几个基元；"
                "$\\alpha$ 小 ⟹ 顺序无所谓、不能提前终止、每像素要几百个采样</em>。"
                "<strong>3DGS 的实时性，追到底就是这一个量级差。</strong>"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 01 · 体渲染与 α 合成

本 notebook 把讲解页的六个结论全部跑出来：

1. **α 合成对分段常数密度是精确的**（连 $N{=}1$）；
2. σ 沿射线变化时，中点法则的误差 **∝ 1/N²**（每翻一倍降到 1/4）；
3. **顺序敏感度由 α 的大小决定**（大 α 中位偏差 19.6%，小 α 0.27%）；
4. **提前终止能省 92.2% 的工作，误差严格小于 $T_{\\min}$**；
5. α 合成的**解析梯度**与数值梯度逐项吻合，而它必须从后往前算；
6. 深度图的三种口径给出不同的数，且 $D_{\\text{raw}} = A\\cdot D_{\\text{norm}}$。

只用 numpy，CPU，离线。"""),

code("""import numpy as np
print('numpy', np.__version__)

def alpha_composite(alphas, colors, return_T=False):
    '''按给定顺序（近 -> 远）做 α 合成。
    返回 RGB；return_T=True 时额外返回 (每项的 T_i, 最终 T)。'''
    alphas = np.asarray(alphas, float); colors = np.asarray(colors, float)
    T = 1.0; out = np.zeros(colors.shape[-1]); Ts = np.empty(len(alphas))
    for i, (a, c) in enumerate(zip(alphas, colors)):
        Ts[i] = T
        out += T * a * c
        T *= (1 - a)
    return (out, Ts, T) if return_T else out

# 一个最小例子
_a = [0.5, 0.5, 0.5]
_c = [[1., 0, 0], [0, 1., 0], [0, 0, 1.]]
_out, _Ts, _Tf = alpha_composite(_a, _c, return_T=True)
print('三个 α=0.5 的基元（红/绿/蓝）:', np.round(_out, 4))
print('T_i =', np.round(_Ts, 4), ' T_final =', round(_Tf, 4))
assert np.allclose(_out, [0.5, 0.25, 0.125]), '权重应为 0.5/0.25/0.125'
assert abs(_Tf - 0.125) < 1e-15
assert abs(_out.sum() + _Tf - 1.0) < 1e-15, '权重和 + T_final = 1'
print('\\n✓ 权重逐项减半，且 Σw + T_final = 1（这是概率解释的直接后果）')"""),

md("""## 1 · α 合成对分段常数密度是精确的

$\\sigma$、$c$ 在长度 $L$ 上恒定时闭式解是 $c(1-e^{-\\sigma L})$。
把这段切成 $N$ 段，因为 $(1-\\alpha)^N = e^{-\\sigma L}$，所以 α 合成**对任意 $N$ 都精确**。"""),

code("""def march_const(sigma, L, c, N):
    '''分段常数密度的 α 合成（标量颜色）。'''
    delta = L / N
    alpha = 1.0 - np.exp(-sigma*delta)
    return alpha_composite([alpha]*N, [[c]]*N)[0]

print('σ=2.0  L=1.5  c=0.8')
closed = 0.8 * (1 - np.exp(-2.0*1.5))
print(f'闭式解 = {closed:.17f}\\n')
print('   N     α 合成                   |差|')
for N in [1, 2, 4, 16, 256]:
    v = march_const(2.0, 1.5, 0.8, N)
    print(f'{N:5d}   {v:.17f}   {abs(v-closed):.3e}')
    assert abs(v - closed) < 1e-14

print('\\n换几组极端参数再验一遍（薄而密 / 厚而稀 / 近乎透明）：')
for sg, L, c in [(0.05, 30.0, 1.0), (50.0, 0.02, 0.3), (1e-4, 1.0, 0.5)]:
    cl = c*(1-np.exp(-sg*L))
    errs = [abs(march_const(sg, L, c, N) - cl) for N in [1, 3, 7, 512]]
    print(f'  σ={sg:<8g} L={L:<6g} c={c}: 闭式 {cl:.10f}  最大误差 {max(errs):.2e}')
    assert max(errs) < 1e-13

# 透射率恒等式：这就是精确性的全部原因
sg, L, N = 2.0, 1.5, 7
assert abs((np.exp(-sg*L/N))**N - np.exp(-sg*L)) < 1e-15
print('\\n✓ (1-α)^N = (e^(-σδ))^N = e^(-σL)，与 N 无关 —— 所以离散化误差**只**来自 σ 在段内变化')"""),

md("""## 2 · σ 变化时：中点法则是二阶的

取一个沿射线平滑变化的密度 $\\sigma(t) = 1 + 2\\sin^2(2t)$ 与颜色 $c(t) = 0.3 + t/3$，
用中点采样做行进，看误差随 $N$ 怎么降。"""),

code("""sig = lambda t: 1.0 + 2.0*np.sin(2.0*t)**2
col = lambda t: 0.3 + 0.5*t/1.5
Lr = 1.5

def march_varying(N):
    '''中点法则：在每段中心取 σ 与 c。向量化实现。'''
    delta = Lr/N
    tm = (np.arange(N) + 0.5) * delta
    a = 1 - np.exp(-sig(tm)*delta)
    T = np.concatenate([[1.0], np.cumprod(1-a)[:-1]])
    return float(np.sum(T * a * col(tm)))

ref = march_varying(1_000_000)
print(f'参考值（N=10^6）= {ref:.12f}\\n')
print('   N      结果            误差        上一档误差/本档')
prev = None
for N in [8, 16, 32, 64, 128, 256]:
    v = march_varying(N); e = abs(v - ref)
    ratio = '' if prev is None else f'{prev/e:.2f}'
    print(f'{N:5d}   {v:.12f}   {e:.3e}   {ratio}')
    if prev is not None:
        assert 3.8 < prev/e < 4.2, f'N={N} 的比值应≈4，实测 {prev/e:.2f}'
    prev = e

print('\\n✓ 比值稳定在 4.00 -> 误差 ∝ 1/N²（二阶）。')
print('  对照：如果在段**起点**取样（左端点法则）应该是一阶，比值≈2：')
def march_left(N):
    delta = Lr/N
    tl = np.arange(N) * delta
    a = 1 - np.exp(-sig(tl)*delta)
    T = np.concatenate([[1.0], np.cumprod(1-a)[:-1]])
    return float(np.sum(T * a * col(tl)))
prev = None
for N in [32, 64, 128, 256]:
    e = abs(march_left(N) - ref)
    print(f'    N={N:4d} 左端点误差 {e:.3e}' + ('' if prev is None else f'  比值 {prev/e:.2f}'))
    prev = e
print('\\n  ✓ 左端点法则的比值≈2（一阶）。所以「取中点」这一个细节就换来了一整个收敛阶')"""),

md("""## 3 · 顺序敏感度由 α 的大小决定"""),

code("""def order_devs(lo, hi, n_gauss=8, trials=2000, seed=1):
    '''打乱顺序造成的最大通道偏差（满量程 1.0）。'''
    rng = np.random.default_rng(seed)
    devs = np.empty(trials)
    for t in range(trials):
        a = rng.uniform(lo, hi, n_gauss)
        c = rng.uniform(0, 1, (n_gauss, 3))
        ref_c = alpha_composite(a, c)
        p = rng.permutation(n_gauss)
        devs[t] = np.abs(alpha_composite(a[p], c[p]) - ref_c).max()
    return devs

print('α 区间          中位     P95      最大')
med = {}
for lo, hi in [(0.30, 0.90), (0.10, 0.70), (0.01, 0.05)]:
    d = order_devs(lo, hi); med[(lo, hi)] = np.median(d)
    print(f'  [{lo:.2f},{hi:.2f}]     {np.median(d):.4f}   {np.percentile(d,95):.4f}   {d.max():.4f}')

r = med[(0.10,0.70)] / med[(0.01,0.05)]
print(f'\\n大 α / 小 α = {r:.0f}×')
assert med[(0.10,0.70)] > 0.15 and med[(0.01,0.05)] < 0.01 and r > 20

# 二阶依赖的验证：把 α 整体缩放 k 倍，敏感度应约缩 k² 倍
print('\\n把 α 区间整体缩放，检验「敏感度 ∝ α²」的适用范围：')
print('  α 区间                 中位偏差    相对上一档(×2)   等效指数')
prev = None
for k in [0.25, 0.5, 1.0, 2.0, 4.0]:
    lo, hi = 0.02*k, 0.10*k
    m = np.median(order_devs(lo, hi, seed=7))
    if prev is None:
        print(f'  [{lo:.4f},{hi:.4f}]      {m:.6f}')
    else:
        print(f'  [{lo:.4f},{hi:.4f}]      {m:.6f}     {m/prev:.3f}          {np.log2(m/prev):.3f}')
    prev = m

_e_small = np.log2(np.median(order_devs(0.02, 0.10, seed=7)) /
                   np.median(order_devs(0.01, 0.05, seed=7)))
_e_large = np.log2(np.median(order_devs(0.08, 0.40, seed=7)) /
                   np.median(order_devs(0.04, 0.20, seed=7)))
print(f'\\n小 α 端的等效指数 {_e_small:.2f}（趋向 2），大 α 端 {_e_large:.2f}')
assert _e_small > 1.85, f'小 α 端应接近 2，实测 {_e_small:.2f}'
assert _e_large < 1.7,  f'大 α 端应明显低于 2，实测 {_e_large:.2f}'
print('✓ α² 律**只在小 α 极限下成立**。α 大到 0.4 时指数掉到 1.55 —— 因为一阶展开')
print('  丢掉的三阶及以上项开始起作用，而它们的符号与二阶项相反，起了抵消作用。')
print('  所以「顺序敏感度 ∝ α²」是一个渐近判断，不是可以外推到 α=0.9 的定量公式')

# 基元个数的影响
print('\\n基元个数的影响（α∈[0.1,0.7]）：')
print('  个数    中位     均值     P95     P(随机置换恰为恒等)')
import math
for n in [1, 2, 3, 4, 8, 16, 32, 64, 128]:
    d = order_devs(0.10, 0.70, n_gauss=n, trials=600, seed=3)
    print(f'  {n:4d}  {np.median(d):.4f}  {d.mean():.4f}  {np.percentile(d,95):.4f}'
          f'      {1/math.factorial(n):.1%}' if n <= 5 else
          f'  {n:4d}  {np.median(d):.4f}  {d.mean():.4f}  {np.percentile(d,95):.4f}      ~0')

_d1 = order_devs(0.1, 0.7, n_gauss=1, trials=200, seed=3)
_d2 = order_devs(0.1, 0.7, n_gauss=2, trials=600, seed=3)
_d128 = order_devs(0.1, 0.7, n_gauss=128, trials=300, seed=3)
_d32 = order_devs(0.1, 0.7, n_gauss=32, trials=300, seed=3)
assert _d1.max() == 0.0, '1 个基元时任何置换都是恒等'
assert np.median(_d2) == 0.0 and _d2.mean() > 0.03, \
    'n=2 的**中位**为 0 但均值不为 0'
assert np.median(_d128)/np.median(_d32) < 1.3, '32 -> 128 应已趋于饱和'
print('\\n✓ 两个容易看错的地方：')
print('  ① n=1 与 n=2 的**中位**都是 0，但原因不同：n=1 是恒等置换是唯一的置换；')
print('     n=2 是随机置换有 50% 概率恰为恒等（1/n!），所以中位数落在 0 上 ——')
print(f'     而 n=2 的**均值**是 {_d2.mean():.4f}，并不为 0。这是分位数的性质，不是物理')
print('  ② n≥3 后单调上升，但到 32 个左右就饱和在 ~0.29 —— 因为大 α 下前几个基元')
print('     吃掉了几乎全部权重，再多的基元排在哪里都影响不到结果')"""),

md("""## 4 · 提前终止：省多少，错多少

在 $T < T_{\\min}$ 时停下。丢掉的量 $\\sum_{i\\ge k}T_i\\alpha_i c_i < T_{\\min}\\cdot\\max c$，
所以 **$T_{\\min}$ 直接就是误差上界**。"""),

code("""def composite_early(alphas, colors, T_min=1e-4):
    '''带提前终止的 α 合成。返回 (颜色, 实际处理的基元数)。'''
    alphas = np.asarray(alphas, float); colors = np.asarray(colors, float)
    T = 1.0; out = np.zeros(colors.shape[-1])
    for i, (a, c) in enumerate(zip(alphas, colors)):
        if T < T_min:
            return out, i
        out += T * a * c
        T *= (1 - a)
    return out, len(alphas)

print('累积不透明度 1-T 的增长：')
print('  α      1个      4个      16个     32个    达99%需  达99.9%需')
for al in [0.1, 0.2, 0.3, 0.5]:
    vals = [1-(1-al)**n for n in [1, 4, 16, 32]]
    n99 = int(np.ceil(np.log(0.01)/np.log(1-al)))
    n999 = int(np.ceil(np.log(0.001)/np.log(1-al)))
    print(f' {al:.1f}   ' + '  '.join(f'{v:.6f}' for v in vals) + f'    {n99:3d}      {n999:3d}')
assert int(np.ceil(np.log(0.01)/np.log(0.7))) == 13, 'α=0.3 达 99% 应需 13 个'

# 模块 03 的场景：每 tile 245 个高斯
rng = np.random.default_rng(11)
n_tile = 245
al = rng.uniform(0.1, 0.7, n_tile)
cl = rng.uniform(0, 1, (n_tile, 3))
full = alpha_composite(al, cl)
print(f'\\n每 tile {n_tile} 个高斯（α∈[0.1,0.7]，已按深度排好）：')
print('  T_min      处理个数   省下     最大误差    误差上界(=T_min)')
for tm in [1e-2, 1e-3, 1e-4, 1e-6]:
    v, used = composite_early(al, cl, tm)
    err = np.abs(v - full).max()
    print(f'  {tm:.0e}     {used:4d}     {1-used/n_tile:5.1%}    {err:.3e}    {tm:.0e}')
    assert err < tm, f'T_min={tm} 时误差必须小于上界，实测 {err:.3e}'

v4, used4 = composite_early(al, cl, 1e-4)
print(f'\\n✓ T_min=1e-4：只处理 {used4}/{n_tile} 个（省 {1-used4/n_tile:.0%}），'
      f'误差 {np.abs(v4-full).max():.1e}')
print(f'  8 bit 显示的一个色阶是 1/255 = {1/255:.4f}，所以这个误差**视觉上完全无损**')

# 最坏情况：一整 tile 都是低 α 的雾
al_fog = np.full(n_tile, 0.01)
cl_fog = rng.uniform(0, 1, (n_tile, 3))
_, used_fog = composite_early(al_fog, cl_fog, 1e-4)
print(f'\\n最坏情况（α 全为 0.01 的雾）：处理 {used_fog}/{n_tile} 个 -> '
      f'{"完全不终止" if used_fog == n_tile else "仍能终止"}')
assert used_fog == n_tile, '低 α 时无法提前终止'
print('  ✓ 提前终止改善的是**平均**时延，不是最坏时延')

# float32 下 T 的下溢
print('\\nfloat32 下 T 的下溢（α=0.3）：')
for n in [16, 64, 128, 256]:
    T32 = np.float32(0.7)**np.float32(n)
    print(f'  {n:3d} 个后 T = {float(T32):.3e}' + ('   <- 已下溢为 0' if T32 == 0 else ''))
print('  ✓ 所以提前终止还避免了在下溢的 T 上继续做无意义的乘法')"""),

md("""## 5 · 反向传播：从后往前累加

$$\\frac{\\partial C}{\\partial c_i} = T_i\\alpha_i,\\qquad
\\frac{\\partial C}{\\partial \\alpha_i} = T_i c_i - \\frac{1}{1-\\alpha_i}\\sum_{k>i}T_k\\alpha_k c_k$$

第二项需要「$i$ 之后所有项的和」，所以必须**从最远的基元往近处走**。"""),

code("""def alpha_backward(alphas, colors, dL_dC):
    '''α 合成的解析梯度。返回 (dL/dα, dL/dc)。'''
    alphas = np.asarray(alphas, float); colors = np.asarray(colors, float)
    w = np.asarray(dL_dC, float)
    n = len(alphas)
    _, Ts, _ = alpha_composite(alphas, colors, return_T=True)

    # 从后往前累加 S_{>i} = sum_{k>i} T_k α_k c_k
    suffix = np.zeros_like(colors)
    acc = np.zeros(colors.shape[-1])
    for i in range(n-1, -1, -1):
        suffix[i] = acc
        acc = acc + Ts[i]*alphas[i]*colors[i]

    g_alpha = np.array([w @ (Ts[i]*colors[i] - suffix[i]/(1-alphas[i])) for i in range(n)])
    g_color = w[None, :] * (Ts*alphas)[:, None]
    return g_alpha, g_color

rng = np.random.default_rng(0)
n = 12
a = rng.uniform(0.05, 0.7, n); c = rng.uniform(0, 1, (n, 3))
w = rng.normal(0, 1, 3)                       # 上游梯度 dL/dC
loss = lambda aa, cc: float(w @ alpha_composite(aa, cc))

g_a, g_c = alpha_backward(a, c, w)

eps = 1e-6
ga_num = np.empty(n)
for i in range(n):
    ap = a.copy(); ap[i] += eps; am = a.copy(); am[i] -= eps
    ga_num[i] = (loss(ap, c) - loss(am, c)) / (2*eps)
gc_num = np.empty((n, 3))
for i in range(n):
    for k in range(3):
        cp = c.copy(); cp[i, k] += eps; cm = c.copy(); cm[i, k] -= eps
        gc_num[i, k] = (loss(a, cp) - loss(a, cm)) / (2*eps)

ea = np.max(np.abs(g_a - ga_num) / (np.abs(ga_num) + 1e-9))
ec = np.max(np.abs(g_c - gc_num) / (np.abs(gc_num) + 1e-9))
print(f'dL/dα 最大相对误差 {ea:.2e}')
print(f'dL/dc 最大相对误差 {ec:.2e}')
assert ea < 1e-4 and ec < 1e-4, '解析梯度必须与数值梯度吻合'
print('（这个量级就是中心差分本身的误差 O(eps²) + 舍入，不是解析式的问题）')

print('\\n各基元的 dL/dα（近 -> 远）：')
print(' ', np.round(g_a, 4))
print(f'  |dL/dα| 的近端/远端之比 = {abs(g_a[0])/abs(g_a[-1]):.1f}×'
      f'  （T_1/T_{n} = {1.0/alpha_composite(a,c,return_T=True)[1][-1]:.1f}×）')
print('  ✓ 远处基元的梯度被 T 压小 —— 被挡住的高斯几乎收不到梯度，这既是特性也是问题（模块 04）')"""),

code("""# 1/(1-α) 的病态
print('反向式里 1/(1-α) 的量级：')
for am in [0.9, 0.99, 0.999, 0.9999, 1-1e-7]:
    print(f'  α={am:.7f} -> 1/(1-α) = {1/(1-am):.3e}')

print('\\n所以真实实现的两道防线：')
print('  ① α 存 logit 过 sigmoid，永远到不了 1（sigmoid(20) = %.10f）' % (1/(1+np.exp(-20))))
print('  ② 官方 CUDA 内核不逐项算 1/(1-α)，而是保存前向末尾的 T，')
print('     反向走时每退一步做一次除法把 T_i 反推回来 —— 病态被限制在一处')

# 演示②：反推 T
_, Ts_fwd, T_end = alpha_composite(a, c, return_T=True)
T_back = np.empty(len(a)); T = T_end
for i in range(len(a)-1, -1, -1):
    T = T / (1 - a[i])            # T_{i+1} = T_i(1-α_i) -> T_i = T_{i+1}/(1-α_i)
    T_back[i] = T
print(f'\\n反推的 T 与前向的 T 最大相对误差 {np.max(np.abs(T_back-Ts_fwd)/Ts_fwd):.2e}')
assert np.allclose(T_back, Ts_fwd, rtol=1e-10)
print('✓ 反推可行。代价：α 接近 1 的基元会放大这个除法的误差 —— 与①是同一个约束')

# 提前终止必须在反向里被重放
print('\\n提前终止若不在反向里重放会怎样：')
al2 = np.concatenate([np.full(8, 0.6), np.full(40, 0.5)])      # 前 8 个就几乎挡满
cl2 = np.random.default_rng(5).uniform(0, 1, (48, 3))
_, used2 = composite_early(al2, cl2, 1e-4)
g_all, _ = alpha_backward(al2, cl2, np.ones(3))
print(f'  前向实际只处理了 {used2}/48 个基元')
print(f'  但对全部 48 个求梯度时，第 {used2+1}~48 个的 |dL/dα| 之和 = '
      f'{np.abs(g_all[used2:]).sum():.3e}')
print(f'  而前 {used2} 个的 |dL/dα| 之和 = {np.abs(g_all[:used2]).sum():.3e}')
print('  ✓ 后者大 %d 倍。被遮挡的基元梯度虽小但**不为零**，' %
      int(np.abs(g_all[:used2]).sum()/max(np.abs(g_all[used2:]).sum(), 1e-30)))
print('    长期累积会把它们优化成「看不见但吃内存」的浮物 —— 所以反向必须重放终止点')"""),

md("""## 6 · 副产物：累积不透明度与三种深度口径

同一组权重 $w_i = T_i\\alpha_i$，换被加权的量就得到另外两张图。"""),

code("""def render_extras(alphas, ts):
    '''返回 (A, D_raw, D_norm, D_median)。ts 是各基元的深度。'''
    alphas = np.asarray(alphas, float); ts = np.asarray(ts, float)
    T = np.concatenate([[1.0], np.cumprod(1-alphas)[:-1]])
    w = T * alphas
    A = float(w.sum())
    D_raw = float((w*ts).sum())
    D_norm = D_raw / A if A > 0 else np.nan
    idx = int(np.searchsorted(np.cumsum(w)/A, 0.5))
    return A, D_raw, D_norm, float(ts[min(idx, len(ts)-1)])

def surface(k, al, spacing=0.05, t0=10.0):
    '''一个「表面」由 k 个等间距、同 α 的基元堆成，从 t0 开始。'''
    return np.full(k, al), t0 + np.arange(k)*spacing

print('配置                     A        D_raw    D_norm   D_median  D_raw 相对偏差')
rows = [(1, 0.90, 0.10), (20, 0.05, 0.05), (20, 0.10, 0.05),
        (20, 0.20, 0.05), (5, 0.90, 0.10)]
for k, al, sp in rows:
    a_, t_ = surface(k, al, sp)
    A, Dr, Dn, Dm = render_extras(a_, t_)
    print(f'  {k:2d} 个 α={al:.2f}          {A:.4f}   {Dr:7.3f}  {Dn:7.3f}  {Dm:7.3f}'
          f'   {(Dr-Dn)/Dn:+7.1%}')
    # 恒等式：D_raw = A * D_norm，所以相对偏差恒为 -(1-A)
    assert abs(Dr - A*Dn) < 1e-12, 'D_raw = A·D_norm 必须成立'
    assert abs((Dr-Dn)/Dn - (A-1.0)) < 1e-12, '相对偏差必须恒等于 -(1-A)'

A1, Dr1, Dn1, _ = render_extras(*surface(1, 0.90, 0.10))
print(f'\\n✓ 最简情形：**一个** α=0.9 的基元位于 10.0 m')
print(f'  D_raw = {Dr1:.3f} m，而真相毫无疑义就是 10.0 m —— 偏小正好 (1-α)×t = {0.1*10:.1f} m')
assert abs(Dr1 - 9.0) < 1e-12 and abs(Dn1 - 10.0) < 1e-12

A2, Dr2, Dn2, _ = render_extras(*surface(20, 0.05, 0.05))
print(f'\\n✓ 而 A 很小时偏差很大：A={A2:.4f} 时 D_raw={Dr2:.3f} vs D_norm={Dn2:.3f}，'
      f'差 {Dn2-Dr2:.2f} m')
print('  这个量级足以让任何深度评测的结论翻转 —— 比较两份结果前先确认口径')

# 归一化的代价：A 小的地方分母噪声被放大
print('\\n归一化的代价（A 很小时分母噪声被放大）：')
rng2 = np.random.default_rng(9)
for A_target in [0.9, 0.3, 0.05]:
    # 用一个基元凑出目标 A，然后给 α 加 1% 的相对扰动看 D_norm 抖多少
    al0 = A_target
    ds = []
    for _ in range(400):
        al_p = np.array([al0*(1+rng2.normal(0, 0.01)), 0.001])
        ts_p = np.array([10.0, 30.0])
        ds.append(render_extras(al_p, ts_p)[2])
    print(f'  A≈{A_target:.2f}: D_norm 标准差 {np.std(ds):.4f} m')
print('  ✓ 所以实践中两张图都输出，并用 A 当置信度屏蔽低 A 的像素（常见阈值 A>0.5）')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 中点法则的行进器

实现 `my_march(sigma_fn, color_fn, L, N)`：把 $[0,L]$ 均分 $N$ 段，
在**每段中心**取 $\\sigma$ 与 $c$，返回 α 合成结果（标量）。
自测会验证：① 对常数 $\\sigma$ 精确；② 对变化的 $\\sigma$ 误差 ∝ 1/N²。"""),

code("""def my_march(sigma_fn, color_fn, L, N):
    '''中点法则的体渲染行进器。sigma_fn/color_fn 接受 ndarray，返回 ndarray。'''
    # TODO: delta = L/N
    #       tm = (arange(N)+0.5)*delta          <- 中点，不是左端点
    #       a  = 1 - exp(-sigma_fn(tm)*delta)
    #       T  = concatenate([[1.0], cumprod(1-a)[:-1]])
    #       返回 float(sum(T*a*color_fn(tm)))
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_const_s = lambda t: np.full_like(np.asarray(t, float), 2.0)
_const_c = lambda t: np.full_like(np.asarray(t, float), 0.8)
_var_s   = lambda t: 1.0 + 2.0*np.sin(2.0*np.asarray(t, float))**2
_var_c   = lambda t: 0.3 + 0.5*np.asarray(t, float)/1.5
_closed  = 0.8*(1 - np.exp(-2.0*1.5))
_ref_var = my_march(_var_s, _var_c, 1.5, 1_000_000)

# ① 常数 σ：任意 N 都精确
for _N in [1, 2, 5, 64]:
    _v = my_march(_const_s, _const_c, 1.5, _N)
    assert abs(_v - _closed) < 1e-13, f'常数 σ 下 N={_N} 应精确：{_v} vs {_closed}'

# ② 变化 σ：二阶收敛
_prev = None
for _N in [16, 32, 64, 128]:
    _e = abs(my_march(_var_s, _var_c, 1.5, _N) - _ref_var)
    if _prev is not None:
        assert 3.8 < _prev/_e < 4.2, f'N={_N} 的误差比值应≈4，实测 {_prev/_e:.2f}'
    _prev = _e

# ③ 与本 notebook 的参考实现一致
assert abs(my_march(_var_s, _var_c, 1.5, 64) - march_varying(64)) < 1e-14
# ④ 若误取左端点，比值会是 ≈2 而不是 ≈4，所以上面的 ② 会失败
print(f'✓ 练习 1 通过：常数 σ 精确到 1e-13，变化 σ 的误差比值 ≈4.00（二阶）')"""),

md("""### 📖 参考答案 1"""),

code("""def my_march(sigma_fn, color_fn, L, N):
    delta = L / N
    tm = (np.arange(N) + 0.5) * delta
    a = 1.0 - np.exp(-sigma_fn(tm) * delta)
    T = np.concatenate([[1.0], np.cumprod(1.0 - a)[:-1]])
    return float(np.sum(T * a * color_fn(tm)))

print('参考答案 1 已定义')
print('要点：cumprod(1-a)[:-1] 前面补一个 1.0 —— T_i 是「i 之前」的乘积，不含自己。')
print('     这个 off-by-one 是本模块最常见的实现错误：错了之后第一个基元会被算成 T=1-α_1。')"""),

md("""### ✏️ 练习 2 · 提前终止与它的误差上界

实现 `my_early(alphas, colors, T_min)`，返回 `(颜色, 实际处理的基元数)`：
在**处理第 $i$ 个之前**检查 $T < T_{\\min}$，若成立立即返回。"""),

code("""def my_early(alphas, colors, T_min=1e-4):
    '''带提前终止的 α 合成。返回 (颜色 ndarray, 处理的基元数 int)。'''
    # TODO: T=1.0, out=zeros(3)
    #       枚举 i, (a, c)：先判 if T < T_min: return out, i
    #       再 out += T*a*c; T *= (1-a)
    #       循环结束返回 (out, len(alphas))
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_rng = np.random.default_rng(11)
_al = _rng.uniform(0.1, 0.7, 245)
_cl = _rng.uniform(0, 1, (245, 3))
_full = alpha_composite(_al, _cl)
_fog_a = np.full(245, 0.01)
_fog_c = _rng.uniform(0, 1, (245, 3))

for _tm in [1e-2, 1e-3, 1e-4, 1e-6]:
    _v, _u = my_early(_al, _cl, _tm)
    _err = np.abs(_v - _full).max()
    assert _err < _tm, f'T_min={_tm}: 误差 {_err:.3e} 必须严格小于上界'
    assert 0 < _u <= 245

_v4, _u4 = my_early(_al, _cl, 1e-4)
assert _u4 < 60, f'α∈[0.1,0.7] 时 T_min=1e-4 应在 60 个内终止，实测 {_u4}'
assert np.allclose(_v4, my_early(_al, _cl, 1e-4)[0]), '必须是确定性的'

# 低 α 的雾无法终止
_, _uf = my_early(_fog_a, _fog_c, 1e-4)
assert _uf == 245, f'α=0.01 时不该终止，实测 {_uf}'
# T_min=0 时等于不终止
_v0, _u0 = my_early(_al, _cl, 0.0)
assert _u0 == 245 and np.allclose(_v0, _full), 'T_min=0 应退化为完整合成'
print(f'✓ 练习 2 通过：T_min=1e-4 处理 {_u4}/245 个（省 {1-_u4/245:.0%}），'
      f'误差 {np.abs(_v4-_full).max():.1e} < 1e-4；雾的情形不终止')"""),

md("""### 📖 参考答案 2"""),

code("""def my_early(alphas, colors, T_min=1e-4):
    alphas = np.asarray(alphas, float); colors = np.asarray(colors, float)
    T = 1.0; out = np.zeros(colors.shape[-1])
    for i, (a, c) in enumerate(zip(alphas, colors)):
        if T < T_min:
            return out, i
        out += T * a * c
        T *= (1 - a)
    return out, len(alphas)

print('参考答案 2 已定义')
print('要点：判断放在**处理之前**。若放在之后，最坏情况会多处理一个基元 ——')
print('     单看无所谓，但它破坏了「误差 < T_min」这个上界的严格性（会变成 <T_min·(1+α_max)）。')"""),

md("""### ✏️ 练习 3 · α 合成的解析梯度

实现 `my_backward(alphas, colors, dL_dC)`，返回 `(g_alpha, g_color)`：

$$\\frac{\\partial C}{\\partial c_i} = T_i\\alpha_i,\\qquad
\\frac{\\partial C}{\\partial \\alpha_i} = T_i c_i - \\frac{1}{1-\\alpha_i}\\sum_{k>i}T_k\\alpha_k c_k$$

`g_alpha` 形状 `(n,)`，`g_color` 形状 `(n,3)`。"""),

code("""def my_backward(alphas, colors, dL_dC):
    '''返回 (g_alpha (n,), g_color (n,3))。'''
    # TODO: 1) 先前向拿到 Ts（可用 alpha_composite(..., return_T=True)）
    #       2) **从后往前**累加 suffix[i] = sum_{k>i} T_k*α_k*c_k
    #       3) g_alpha[i] = dL_dC @ (Ts[i]*colors[i] - suffix[i]/(1-alphas[i]))
    #          g_color    = dL_dC[None,:] * (Ts*alphas)[:,None]
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_r3 = np.random.default_rng(0)
_n3 = 12
_a3 = _r3.uniform(0.05, 0.7, _n3)
_c3 = _r3.uniform(0, 1, (_n3, 3))
_w3 = _r3.normal(0, 1, 3)
_loss3 = lambda aa, cc: float(_w3 @ alpha_composite(aa, cc))
_eps3 = 1e-6

_ga, _gc = my_backward(_a3, _c3, _w3)
assert _ga.shape == (_n3,) and _gc.shape == (_n3, 3), f'形状不对：{_ga.shape} {_gc.shape}'

_ga_num = np.empty(_n3)
for _i in range(_n3):
    _ap = _a3.copy(); _ap[_i] += _eps3
    _am = _a3.copy(); _am[_i] -= _eps3
    _ga_num[_i] = (_loss3(_ap, _c3) - _loss3(_am, _c3)) / (2*_eps3)
_gc_num = np.empty((_n3, 3))
for _i in range(_n3):
    for _k in range(3):
        _cp = _c3.copy(); _cp[_i, _k] += _eps3
        _cm = _c3.copy(); _cm[_i, _k] -= _eps3
        _gc_num[_i, _k] = (_loss3(_a3, _cp) - _loss3(_a3, _cm)) / (2*_eps3)

_ea = np.max(np.abs(_ga - _ga_num) / (np.abs(_ga_num) + 1e-9))
_ec = np.max(np.abs(_gc - _gc_num) / (np.abs(_gc_num) + 1e-9))
assert _ea < 1e-4, f'dL/dα 相对误差 {_ea:.2e} 太大'
assert _ec < 1e-4, f'dL/dc 相对误差 {_ec:.2e} 太大'

# 最后一个基元没有后继，suffix 必须是 0
_ga2, _ = my_backward(_a3, _c3, _w3)
_Ts = alpha_composite(_a3, _c3, return_T=True)[1]
assert abs(_ga2[-1] - _w3 @ (_Ts[-1]*_c3[-1])) < 1e-12, '最后一项应只有 T_i·c_i'
# 单基元：dC/dα = c
_g1, _ = my_backward([0.4], [[0.7, 0.2, 0.5]], np.ones(3))
assert abs(_g1[0] - 1.4) < 1e-12, f'单基元时 dL/dα 应为 sum(c)=1.4，实测 {_g1[0]}'
print(f'✓ 练习 3 通过：dL/dα 相对误差 {_ea:.1e}，dL/dc {_ec:.1e}；'
      f'末项与单基元的边界情形也对')"""),

md("""### 📖 参考答案 3"""),

code("""def my_backward(alphas, colors, dL_dC):
    alphas = np.asarray(alphas, float); colors = np.asarray(colors, float)
    w = np.asarray(dL_dC, float)
    n = len(alphas)
    _, Ts, _ = alpha_composite(alphas, colors, return_T=True)
    suffix = np.zeros_like(colors)
    acc = np.zeros(colors.shape[-1])
    for i in range(n-1, -1, -1):
        suffix[i] = acc
        acc = acc + Ts[i]*alphas[i]*colors[i]
    g_alpha = np.array([w @ (Ts[i]*colors[i] - suffix[i]/(1-alphas[i])) for i in range(n)])
    g_color = w[None, :] * (Ts*alphas)[:, None]
    return g_alpha, g_color

print('参考答案 3 已定义')
print('要点一：suffix 的循环方向不能反。前向从近到远累积 T，反向从远到近累积 S ——')
print('       这个「一来一回」就是官方 CUDA 内核的结构，也是它必须知道排序结果的原因。')
print('要点二：1/(1-α_i) 是式子里唯一的病态处，α→1 时发散。α 存 logit 就把它挡住了。')"""),

md("""### ✏️ 练习 4 · 三种深度口径与那个恒等式

实现 `my_extras(alphas, ts)`，返回 `(A, D_raw, D_norm, D_median)`。
`D_median` 定义为：使归一化累积权重首次达到 0.5 的那个基元的深度。
自测会验证恒等式 $D_{\\text{raw}} = A\\cdot D_{\\text{norm}}$，
以及「$D_{\\text{raw}}$ 的相对偏差恒等于 $-(1-A)$」。"""),

code("""def my_extras(alphas, ts):
    '''返回 (A, D_raw, D_norm, D_median)。'''
    # TODO: T = concatenate([[1.0], cumprod(1-alphas)[:-1]]); w = T*alphas
    #       A = w.sum(); D_raw = (w*ts).sum(); D_norm = D_raw/A
    #       D_median = ts[searchsorted(cumsum(w)/A, 0.5)]（注意别越界）
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
def _surf(k, al, sp=0.05, t0=10.0):
    return np.full(k, float(al)), t0 + np.arange(k)*sp

_cfgs = [(1, 0.90, 0.10), (20, 0.05, 0.05), (20, 0.10, 0.05),
         (20, 0.20, 0.05), (5, 0.90, 0.10), (3, 0.30, 1.00)]

for _k, _al, _sp in _cfgs:
    _a4, _t4 = _surf(_k, _al, _sp)
    _A, _Dr, _Dn, _Dm = my_extras(_a4, _t4)
    assert 0 < _A < 1.0 + 1e-12, f'A 必须在 (0,1]，实测 {_A}'
    assert abs(_Dr - _A*_Dn) < 1e-12, f'恒等式 D_raw=A·D_norm 失败：{_Dr} vs {_A*_Dn}'
    assert abs((_Dr - _Dn)/_Dn - (_A - 1.0)) < 1e-12, '相对偏差必须恒等于 -(1-A)'
    assert _t4[0] - 1e-12 <= _Dn <= _t4[-1] + 1e-12, 'D_norm 必须落在基元的深度范围内'
    assert _Dm in set(_t4.tolist()), 'D_median 必须是某个基元的深度'
    # 与本 notebook 的参考实现一致
    assert np.allclose(my_extras(_a4, _t4), render_extras(_a4, _t4))

# 最简情形：一个 α=0.9 的基元在 10 m
_A1, _Dr1, _Dn1, _Dm1 = my_extras([0.9], [10.0])
assert abs(_A1 - 0.9) < 1e-15 and abs(_Dr1 - 9.0) < 1e-15
assert abs(_Dn1 - 10.0) < 1e-15 and abs(_Dm1 - 10.0) < 1e-15
# 完全不透明时三种口径重合
_A2, _Dr2, _Dn2, _Dm2 = my_extras([1.0 - 1e-12, 0.5], [7.0, 20.0])
assert abs(_Dr2 - _Dn2) < 1e-9 and abs(_Dn2 - 7.0) < 1e-9, 'A≈1 时 D_raw 与 D_norm 应重合'
print(f'✓ 练习 4 通过：6 组配置的恒等式全部成立；'
      f'单个 α=0.9 的基元在 10 m 处给出 D_raw={_Dr1:.1f} / D_norm={_Dn1:.1f}')"""),

md("""### 📖 参考答案 4"""),

code("""def my_extras(alphas, ts):
    alphas = np.asarray(alphas, float); ts = np.asarray(ts, float)
    T = np.concatenate([[1.0], np.cumprod(1.0 - alphas)[:-1]])
    w = T * alphas
    A = float(w.sum())
    D_raw = float((w * ts).sum())
    D_norm = D_raw / A
    idx = int(np.searchsorted(np.cumsum(w)/A, 0.5))
    return A, D_raw, D_norm, float(ts[min(idx, len(ts)-1)])

print('参考答案 4 已定义')
print('要点：D_raw = A·D_norm 不是近似，是定义带来的恒等式 —— 所以 D_raw 的相对偏差')
print('     **恒等于** -(1-A)，与场景、深度、基元个数全都无关。')
print('     这也说明它不是「可以调好的偏差」：想让 D_raw 准，唯一办法是让 A→1。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 官方 3DGS 的 CUDA 内核结构（submodules/diff-gaussian-rasterization）----
# 前向 renderCUDA()：每个 tile 一个 block，共享内存里分批载入高斯
#   T = 1.0f;
#   for (chunk of gaussians in this tile) {          // 已按深度排好
#       for (j in chunk) {
#           float alpha = min(0.99f, con_o.w * exp(power));   // ← 练习 3 的两道防线之①
#           if (alpha < 1.0f/255.0f) continue;               // 小 α 直接跳过
#           float test_T = T * (1 - alpha);
#           if (test_T < 0.0001f) { done = true; break; }    // ← 练习 2 的 T_min
#           for (ch in 0..2) C[ch] += features[ch] * alpha * T;
#           T = test_T;
#           last_contributor = contributor;                  // ← 反向要重放的终止点
#       }
#   }
#   out_alpha[pix] = 1 - T;                                  // ← 第 6 节的 A
#
# 反向 renderCUDA<BACKWARD>()：反着遍历同一批高斯
#   T = final_T[pix];                                        // 从末尾的 T 开始
#   for (j reversed) {
#       if (contributor > last_contributor) continue;         // 跳过前向没处理的
#       T = T / (1.f - alpha);                                // ← 反推 T_i
#       accum_rec = last_alpha*last_color + (1-last_alpha)*accum_rec;   // ← suffix
#       ...
#   }
# 注意 min(0.99f, ...)：α 被硬夹在 0.99，正是为了压住 1/(1-α)

# ---- gsplat 里对应的开关 ----
from gsplat import rasterization
colors, alphas, meta = rasterization(
    ..., render_mode='RGB+ED',   # 'RGB' / 'D'(D_raw) / 'ED'(expected=D_norm) / 'RGB+ED'
)
# render_mode 的 'D' 与 'ED' 就是第 6 节的两种口径 —— 差别在 20 个 α=0.05 的情形下是 3.7 m

# ---- 训练里的 A 正则（让表示变「实心」）----
# 常见做法：loss += lam * (-(A*log(A+eps) + (1-A)*log(1-A+eps))).mean()
# 这一项把 A 往 0 或 1 推，从而顺带修好 D_raw 的偏差（因为偏差 = -(1-A)）
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 半透明区域颜色错乱 | tile 内是否真按深度排序 | 8 个大 α 基元打乱后中位偏差 19.6% |
| 相机转动时画面「跳一下」 | 是否是 popping（顺序在某视角翻转） | 3DGS 排的是中心深度，不是逐像素前后关系 |
| 深度图与 LiDAR 差几米 | `render_mode` 是 `D` 还是 `ED` | $D_{\\text{raw}}=A\\cdot D_{\\text{norm}}$，$A{=}0.64$ 时差 3.7 m |
| 天空/边缘的深度是噪声 | 是否用 $A$ 屏蔽了低置信像素 | $D_{\\text{norm}}$ 的分母是 $A$ |
| 训练久了内存涨、但画面没变化 | 反向是否重放了提前终止点 | 被遮挡的高斯收到非零梯度会长成浮物 |
| 加采样点画面不变、以为代码坏了 | 这是对的 | 误差 ∝ 1/N²，64→128 只换 4 倍精度 |"""),
]
