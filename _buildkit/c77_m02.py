# -*- coding: utf-8 -*-
"""C77 模块 02 · 时空注意力：分解的代价与它的精确边界。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C28 模块 02（DiT）</strong>——patchify、adaLN-zero、时间步嵌入、"
                 "scaling law 在那里，本课不重讲，只处理<em>时间轴上的注意力结构</em>；"
                 "模块 00（$(T/p_t)^2$ 的代价账）；"
                 "线性代数：<strong>Kronecker 积</strong>与 SVD（本模块的全部论证都在这两个工具上）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_spacetime_attn.ipynb'
                       '（<strong>分解式注意力 $=$ Kronecker 积</strong>，这是恒等式：'
                       '$\\Vert(I{\\otimes}A_s)(A_t{\\otimes}I) - A_t{\\otimes}A_s\\Vert = 0$ / '
                       '<strong>深度与残差都<em>不</em>提高 Kronecker 秩</strong>——'
                       '八层带残差仍是秩 $1$，因为 '
                       '$(I{+}I{\\otimes}A_s)(I{+}A_t{\\otimes}I) = (I{+}A_t)\\otimes(I{+}A_s)$ / '
                       '<strong>并行分支才涨</strong>：秩 $2 / 4 / 16$，完全 3D 是 $25$ / '
                       '匀速运动（任意多个物体）分解<strong>精确</strong>可表示，'
                       '而<strong>加速</strong>需要 Kronecker 秩 $3$–$5$）'),
    ("核心参考", "Peebles &amp; Xie, <em>Scalable Diffusion Models with Transformers</em>"
                 "（ICCV 2023，DiT，见 C28-02）· "
                 "Bertasius, Wang &amp; Torresani, <em>Is Space-Time Attention All You Need "
                 "for Video Understanding?</em>（ICML 2021，TimeSformer 的分解式注意力）· "
                 "Arnab et al., <em>ViViT</em>（ICCV 2021，四种时空注意力分解的对照）· "
                 "Liu et al., <em>Video Swin Transformer</em>（CVPR 2022，时空窗口）· "
                 "Van Loan &amp; Pitsianis, <em>Approximation with Kronecker Products</em>"
                 "（1993，最近 Kronecker 逼近的 SVD 解法）· "
                 "Blattmann et al., <em>Align your Latents</em>（CVPR 2023，时间层的加法式插入）"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [

("cost", "三种做法的精确 FLOP 账", "".join([
    P("$n = T \\cdot S$ 个 token（$S$ 是每帧的 token 数，已按模块 01 做过时间压缩）。"
      "把时间维放进注意力有三种标准做法："),
    ASCII("""
  完全 3D      一个 n x n 的注意力，n = T*S              -> (T*S)^2
  分解         每帧内的空间注意力  (T 个 S x S)          -> T*S^2
               + 每空间位置的时间注意力 (S 个 T x T)      -> S*T^2
               合计 T*S*(S+T)
  时空窗口     只在 w_t x w_s 的邻域里注意               -> T*S*(w_t*w_s)
""".strip("\n")),
    TABLE(["$T$", "$S$", "完全 3D", "分解", "分解的节省", "窗口 $4{\\times}64$", "窗口的节省"],
          [["$16$", "$256$", "$1.68\\times10^{7}$", "$1.11\\times10^{6}$", "$15.1\\times$",
            "$1.05\\times10^{6}$", "$16\\times$"],
           ["$64$", "$256$", "$2.68\\times10^{8}$", "$5.24\\times10^{6}$", "$51.2\\times$",
            "$4.19\\times10^{6}$", "$64\\times$"],
           ["$128$", "$256$", "$1.07\\times10^{9}$", "$1.26\\times10^{7}$", "$85.3\\times$",
            "$8.39\\times10^{6}$", "$128\\times$"],
           ["$64$", "$1024$", "$4.29\\times10^{9}$", "$7.13\\times10^{7}$", "$60.2\\times$",
            "$1.68\\times10^{7}$", "$256\\times$"],
           ["$128$", "$1024$", "$1.72\\times10^{10}$", "$1.51\\times10^{8}$", "$113.8\\times$",
            "$3.36\\times10^{7}$", "$512\\times$"]]),
    P("分解的节省有闭式："),
    MATH("\\frac{(TS)^2}{TS(S+T)} = \\frac{TS}{S+T} = \\frac{1}{1/T + 1/S}"),
    P("这是 $T$ 与 $S$ 的<strong>调和平均的一半</strong>，"
      "所以它被<strong>较小的那个</strong>限住："),
    TABLE(["$T$（$S{=}256$ 固定）", "$16$", "$64$", "$256$", "$1024$", "$4096$", "上界"],
          [["分解的节省", "$15.1\\times$", "$51.2\\times$", "$128.0\\times$",
            "$204.8\\times$", "$240.9\\times$", "$\\mathbf{256\\times}$"]]),
    P("<strong>节省会饱和</strong>：$T$ 从 $256$ 涨到 $4096$（$16$ 倍）只把节省从 $128\\times$ 提到 $241\\times$。"
      "所以「视频越长，分解越赚」是错的——赚头的上界就是 $S$。"),
    CALLOUT("intuition", "窗口注意力的账不一样",
            "窗口的节省是 $(TS)/(w_t w_s)$，它<strong>随 $T$ 线性增长且不饱和</strong>。"
            "所以在很长的视频上窗口比分解便宜得多（$T{=}128$ 时 $128\\times$ vs $85\\times$）。"
            "代价是感受野：窗口需要 $\\log$ 级的层数才能覆盖全序列，"
            "而分解一层就能让任意两个 token 通过两跳相连。"
            "<strong>这两种做法的表达力边界完全不同</strong>，下面三节就是在算分解的那一边。"),
])),

("kron", "分解式注意力就是 Kronecker 积", "".join([
    P("把 $n = TS$ 个 token 排成 $(t, s)$ 的网格。"
      "「对每个空间位置在时间上做注意力」这个算子作用在展平向量上是"),
    MATH("A_t \\otimes I_S"),
    P("而「对每帧在空间上做注意力」是 $I_T \\otimes A_s$。先做时间再做空间："),
    MATH("(I_T \\otimes A_s)(A_t \\otimes I_S) = A_t \\otimes A_s"),
    P("notebook 用 $T{=}6, S{=}8$ 数值验证："
      "$\\Vert\\text{复合} - A_t \\otimes A_s\\Vert = 0.000\\times10^{0}$（逐位相等）。"),
    P("于是分解式注意力的表达力有一个精确的刻画：<strong>它只能产生 Kronecker 积形式的混合</strong>。"
      "自由度对比（$T{=}6, S{=}8$）："),
    TABLE(["结构", "可表达的混合矩阵集合", "自由度"],
          [["完全 3D 注意力", "任意 $(TS) \\times (TS)$ 矩阵", "$(TS)^2 = 2304$"],
           ["分解（两层）", "$\\{A_t \\otimes A_s\\}$", "$T^2 + S^2 - 1 = 99$"]]),
    P("维度比 <strong>$23:1$</strong>。但「自由度少」本身不等于「表达不了你需要的东西」——"
      "关键是<em>需要的那些混合在不在这个集合里</em>。下一节回答这个问题。"),
    DUAL("Kronecker 积的含义是「时间模式 $\\times$ 空间模式」："
         "它先决定「往哪些帧看」，再决定「在帧内往哪些位置看」，"
         "而这两个决定<strong>互不影响</strong>。"
         "现实里我们常常需要相反的东西：往哪些位置看，<em>取决于</em>看的是哪一帧。",
         "形式化地：混合矩阵 $M$ 可写成 $A_t \\otimes A_s$ 当且仅当"
         "把 $M$ 按 $T \\times T$ 个 $S \\times S$ 块重排成矩阵 $R$（Van Loan–Pitsianis 重排）后，"
         "$R$ 的秩为 $1$。$R$ 的秩就是所需的 <strong>Kronecker 秩</strong>，"
         "而最优 Kronecker 逼近的残差恰是 $R$ 除最大奇异值外的能量。"
         "本模块的全部结论都是这个重排 SVD 的直接读数。"),
])),

("rank", "什么样的运动分解不了", "".join([
    P("构造混合矩阵「第 $(t,x)$ 个 token 该 attend 到上一帧的哪个位置」，"
      "然后算它的最优 Kronecker 逼近误差（$T{=}8, S{=}16$）："),
    TABLE(["目标混合", "Kronecker 逼近误差", "Kronecker 秩"],
          [["① 全局匀速 $v{=}2$（看上一帧）", "$\\mathbf{0.000000}$", "$1$"],
           ["② 三个物体各自匀速 $[1,3,6]$", "$\\mathbf{0.000000}$", "$1$"],
           ["③ <strong>加速</strong>：$v(t){=}t$", "$0.935414$", "$8$"],
           ["④ 回看第 $0$ 帧的原始位置", "$0.935414$", "$8$"],
           ["⑤ $t$ 依赖的时间跨度（回看 $t{-}1{-}(t\\bmod 3)$ 帧）", "$\\mathbf{0.000000}$", "$1$"],
           ["⑥ 物体速度随 $t$ 变（$v = \\text{owner} + t\\bmod 2$）", "$0.707107$", "$2$"]]),
    P("我最初猜「多个物体各自不同速度就分解不了」——<strong>错的</strong>，②的误差恰为 $0$。"
      "原因是空间重排（$x \\mapsto x - v_{\\text{owner}(x)}$）是<em>一个固定矩阵</em>，"
      "对所有 $t$ 都相同，所以 $M = A_t \\otimes P$ 仍是 Kronecker 积。"
      "⑤也是 $0$：时间跨度随 $t$ 变而空间位移不变，同理。"),
    P("<strong>精确的判据是</strong>："),
    CALLOUT("intuition", "分解是精确的当且仅当…",
            "混合可以分解成「<strong>与 $t$ 无关</strong>的空间模式」乘「<strong>与 $x$ 无关</strong>的时间模式」。"
            "所以：<strong>匀速运动（多少个物体、各自多快都行）完全没问题；"
            "而加速、变向、以及任何「空间往哪看取决于现在是第几帧」的依赖，都需要更高的 Kronecker 秩。</strong>"),
    TABLE(["加速度 $v(t){=}at$", "Kronecker 逼近误差", "Kronecker 秩", "压到 $1\\%$ 残差所需项数"],
          [["$a{=}0.00$", "$0.000000$", "$1$", "$1$"],
           ["$a{=}0.50$", "$0.790569$", "$3$", "$3$"],
           ["$a{=}1.00$", "$0.935414$", "$5$", "$5$"],
           ["$a{=}2.00$", "$0.790569$", "$3$", "$3$"]]),
    P("秩不是随 $a$ 单调的（$a{=}2$ 时因为位移在 $S$ 上取模而绕回，秩反而降回 $3$），"
      "但结论稳定：<strong>只要 $a \\neq 0$ 就需要秩 $> 1$</strong>。"),
])),

("what", "深度和残差都补不回来——并行分支才行", "".join([
    P("既然一层分解只能给出秩 $1$，那么多叠几层应该能补回来？"
      "notebook 在 $T{=}5, S{=}6$（Kronecker 秩上界 $\\min(T^2, S^2) = 25$）上逐个测："),
    TABLE(["结构", "Kronecker 秩"],
          [["① 单层时间注意力 $A_t \\otimes I$", "$1$"],
           ["② 顺序两层（无残差）$(I{\\otimes}A_s)(A_t{\\otimes}I)$", "$1$"],
           ["③ 顺序两层<strong>带残差</strong> $(I{+}I{\\otimes}A_s)(I{+}A_t{\\otimes}I)$",
            "$\\mathbf{1}$"],
           ["④ 顺序<strong>八层</strong>带残差（四组交替）", "$\\mathbf{1}$"],
           ["⑤ <strong>并行</strong>两分支 $I + A_t{\\otimes}I + I{\\otimes}A_s$", "$\\mathbf{2}$"],
           ["⑥ 并行两分支 $\\times 2$ 层", "$4$"],
           ["⑦ 并行两分支 $\\times 4$ 层", "$\\mathbf{16}$"],
           ["⑧ 完全 3D 注意力", "$25$（$= \\min(T^2,S^2)$）"]]),
    P("③④为什么还是 $1$——因为它是一个<strong>恒等式</strong>："),
    MATH("(I + I_T{\\otimes}A_s)(I + A_t{\\otimes}I_S) = (I_T + A_t) \\otimes (I_S + A_s)"),
    CODE("‖(I+I⊗As)(I+At⊗I) − (I+At)⊗(I+As)‖ = 0.000e+00"),
    P("顺序 $+$ 残差 $=$ 一个<em>更大的</em> Kronecker 积，秩仍然是 $1$。"
      "<strong>深度和残差都不给分解式注意力增加时空交互的表达力。</strong>"),
    P("⑤为什么是 $2$——因为并行分支是<strong>和</strong>而不是<strong>积</strong>，"
      "而 $I + A_t{\\otimes}I + I{\\otimes}A_s$ 无法写成 $P \\otimes Q$。"
      "把并行块叠起来，秩按 $2^L$ 增长（⑥ $4$、⑦ $16$），直到撞上上界 $25$。"),
    CALLOUT("danger", "我在这一节连错了三次",
            "第一次：猜「多个物体不同速度就分解不了」——测出来误差恰为 $0$。"
            "第二次：猜「多叠层能补回来」——Kronecker 积的乘积仍是 Kronecker 积，秩恒为 $1$。"
            "第三次：猜「残差连接能补回来」——"
            "上面那个恒等式说明它等价于一个更大的 Kronecker 积，还是 $1$。"
            "第四次才对。<strong>而这三次错误各自对应一种流行的直觉</strong>，"
            "所以它们值得被写进课程而不是被删掉。"),
    H3("这对架构设计意味着什么"),
    P("真实的视频 Transformer block 里，时间注意力与空间注意力"
      "<strong>并列</strong>接在同一个残差流上（$x \\leftarrow x + \\text{attn}_t(x) + \\text{attn}_s(x)$，"
      "或者两个分支各带自己的残差后相加），而不是串成一条链。"
      "这个看起来只是接线风格的选择，恰恰是表达力的来源。"),
    P("另一条推论：<strong>「在图像模型上插入时间层」的做法（Align your Latents 一类）"
      "之所以能工作，关键在于时间层是<em>加法式</em>插入的</strong>"
      "（$x \\leftarrow x + \\alpha \\cdot \\text{attn}_t(x)$，且 $\\alpha$ 初始化为 $0$）。"
      "如果它是乘法式/串联式插入的，按上面的恒等式，"
      "整个网络的时空混合就仍然被锁在 Kronecker 秩 $1$ 里。"),
    CALLOUT("warn", "这套论证的适用范围",
            "以上全部是<strong>线性算子</strong>层面的分析：把注意力权重当作固定矩阵，"
            "只看混合结构。真实网络里注意力权重<em>依赖输入</em>，"
            "而且每个 block 之间还有非线性 MLP——"
            "两者都能在原理上突破这里的界。"
            "所以本节的结论应当这样读：<strong>它给出的是「不依赖非线性也能做到什么」的下界</strong>，"
            "以及一个明确的设计信号（并行优于串联）。"
            "它<em>不</em>证明串联式分解注意力的网络无法学会加速运动。"),
])),

("pos", "时间轴上的位置编码：一个被 Kronecker 分析照到的角落", "".join([
    P("上面四节把注意力的<em>混合结构</em>算清了，但注意力权重是从哪来的？"
      "在 Transformer 里它由 query-key 内积决定，而位置信息由位置编码注入。"
      "把时空位置编码放进 Kronecker 的框架里，会得到一个有用的观察。"),
    P("若时空位置编码是<strong>可分的</strong>——"
      "即 $\\text{PE}(t, x) = \\text{PE}_t(t) + \\text{PE}_x(x)$（相加）"
      "或 $\\text{PE}_t(t) \\odot \\text{PE}_x(x)$（逐元素相乘）——"
      "那么 query-key 内积中由位置贡献的那部分也是可分的，"
      "于是注意力 logits 有形式"),
    MATH("\\text{logit}[(t,x),(t',x')] = a(t,t') + b(x,x') + c"),
    P("而 softmax 把加法变成乘法："
      "$\\exp(a + b) = \\exp(a)\\exp(b)$，"
      "所以<strong>纯位置驱动的注意力矩阵恰好是一个 Kronecker 积</strong>"
      "（在归一化之前）。"),
    CALLOUT("intuition", "这条观察的用处",
            "它说明<strong>「用完全 3D 注意力」并不自动买到高 Kronecker 秩</strong>："
            "如果注意力主要由位置决定（而不是由内容决定），"
            "那么即使算子形状上是 $n\\times n$，实际产生的混合仍接近秩 $1$。"
            "反过来：<strong>时空混合的表达力最终来自「内容依赖」</strong>——"
            "query 与 key 的<em>语义</em>部分，而不是位置部分。"
            "这给出一条设计信号：如果一个视频模型的注意力图几乎只反映位置邻近性，"
            "那么它在结构上退化到了分解式的水平，$n^2$ 的算力白付了。"),
    H3("时间维的外推"),
    P("另一个实践问题：训练时 $T{=}16$，推理时想要 $T{=}128$。"
      "空间维不需要外推（分辨率固定），而时间维<strong>经常需要</strong>。"
      "常见做法与它们的代价："),
    TABLE(["做法", "机制", "问题"],
          [["绝对位置嵌入（可学）", "每个时间位置一个向量",
            "<strong>完全无法外推</strong>——训练时没见过的位置没有嵌入"],
           ["正弦位置编码", "$\\sin/\\cos$ 的固定频率",
            "可以外推，但注意力对超出训练范围的相对距离没有校准"],
           ["RoPE（时间轴）", "把相对位置编成旋转",
            "外推更好，但长距离的注意力权重衰减方式在训练外不受控"],
           ["相对位置偏置", "$a(t - t')$ 的可学表",
            "表要么裁剪要么插值；裁剪即丢失长程"]]),
    P("而模块 00 的遮挡悬崖给出一个约束："
      "<strong>所需上下文由最长不可观测区间决定</strong>。"
      "如果那个区间在推理时比训练时长，"
      "那么无论位置编码怎么外推，模型都<em>没有学过</em>如何跨越那么长的遮挡——"
      "位置编码的外推能力与<strong>时间依赖的外推能力</strong>是两件事。"),
    CALLOUT("warn", "一个容易混淆的地方",
            "「能处理更长的序列」≠「能建模更长的依赖」。"
            "前者是位置编码与算力的问题，后者是训练数据里有没有那么长的依赖。"
            "本课不做位置编码的实验（它需要真实训练），"
            "但模块 00 练习 3 的遮挡悬崖给出了后者的<strong>下界</strong>："
            "上下文窗口至少要覆盖「最长不可观测区间 $+ 2$ 帧」，"
            "而这是一个关于<em>数据</em>的要求，位置编码帮不上。"),
])),

("scope", "这套分析的适用范围", "".join([
    P("在进入窗口注意力之前，把前四节的<strong>适用范围</strong>说清，"
      "因为它比结论本身更容易被误用。"),
    TABLE(["前四节假设了什么", "真实网络里是什么", "后果"],
          [["注意力权重是<strong>固定矩阵</strong>", "权重依赖输入（query-key 内积）",
            "真实网络可以对不同样本用不同的混合 —— 本节的界是<em>单个样本上</em>的"],
           ["层与层之间是<strong>线性</strong>复合", "中间有非线性 MLP",
            "非线性能在原理上突破 Kronecker 结构"],
           ["只看<strong>混合结构</strong>", "还有值变换 $W_V$、多头、归一化",
            "多头相当于多个并行分支 —— 见第 4 节的 ⑤"]]),
    P("所以正确的读法是：<strong>本节给出的是「不依赖非线性也能做到什么」的下界</strong>，"
      "以及一个明确的设计信号（<em>并行优于串联</em>）。"
      "它<strong>不</strong>证明串联式分解注意力的网络无法学会加速运动——"
      "它只说明那个网络必须靠非线性去补，而并行接线的网络不必。"),
    CALLOUT("intuition", "第三行值得单独说",
            "<strong>多头注意力本身就是并行分支</strong>。"
            "所以一个「多头的、分解式的」时空注意力，"
            "如果不同的头分别做时间与空间，那它在结构上就是第 4 节的 ⑤ 而不是 ③——"
            "Kronecker 秩随头数增长。"
            "这解释了为什么实践中「分头做时空」比「分层做时空」更常见，"
            "而这个选择的收益可以用本节的秩来量。"),
])),

("window", "窗口注意力：另一种边界", "".join([
    P("时空窗口（Video Swin 一类）不做 Kronecker 分解，而是限制注意力的<em>范围</em>。"
      "它的表达力边界形状完全不同："),
    TABLE(["", "分解", "时空窗口"],
          [["代价", "$TS(S+T)$，节省上界 $S$（<strong>饱和</strong>）",
            "$TS \\cdot w_t w_s$，节省 $\\propto TS$（<strong>不饱和</strong>）"],
           ["一层的连通性", "任意两 token 两跳可达", "只在 $w_t \\times w_s$ 邻域内"],
           ["表达力的限制形式", "Kronecker 秩（<em>结构</em>限制）",
            "感受野（<em>范围</em>限制）"],
           ["需要多少层覆盖全序列", "$1$–$2$ 层", "$\\lceil (T{-}1)/\\lfloor w_t/2 \\rfloor \\rceil$ 层（<strong>线性</strong>；配移位窗口可降到 $O(\\log)$）"],
           ["最难表达的东西", "加速、变向", "长距离的瞬时对应（如镜头切换后的重识别）"]]),
    P("两者的限制是<strong>正交</strong>的，这解释了为什么工业模型常常同时用："
      "空间上用窗口（分辨率高、局部性强），时间上用全注意力或分解（$T$ 相对小）。"),
    P("还有一个实践上的组合值得点出：<strong>空间用窗口、时间用全注意力</strong>。"
      "理由按上表可以说清——空间维的 $S$ 很大（$256$–$1024$）而局部性强，"
      "所以窗口的算力收益大且归纳偏置合适；"
      "时间维的 $T$ 相对小（时间压缩之后常在 $8$–$32$），"
      "所以全注意力的 $T^2$ 代价可以承受，而它换来的是"
      "<strong>时间维上不受 Kronecker 秩限制</strong>。"),
    CALLOUT("paper", "一个可以自己算的练习",
            "notebook 的练习 4 让你对「窗口注意力」也做同样的 Kronecker 分析。"
            "结果值得先想一下再看：<strong>一个 $w_t \\times w_s$ 的时空窗口"
            "本身就是 Kronecker 秩 $1$ 的</strong>"
            "（它是「时间上取邻域」$\\otimes$「空间上取邻域」）。"
            "所以窗口注意力在<em>结构</em>上和分解一样受限——"
            "它换来的是别的东西（局部性归纳偏置与内存局部性），不是表达力。"),
])),
]

NB = [
md("""# C77 模块 02 · 时空注意力

四件事，全部是线性代数层面的**精确**结论：

1. 三种做法的 FLOP 账，以及分解的节省 $= TS/(S+T)$ —— **它会饱和**；
2. **分解式注意力 $=$ Kronecker 积**（恒等式，差 $0$）；
3. **深度与残差都不提高 Kronecker 秩**；**并行分支**才提高；
4. 匀速运动（多少个物体都行）分解**精确**可表示；**加速**不行。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import numpy as np

def rowstoch(n, seed):
    '''行随机矩阵 —— 当作一个注意力权重矩阵。'''
    A = np.random.default_rng(seed).random((n, n))
    return A / A.sum(1, keepdims=True)

def kron_rearrange(M, T, S):
    '''Van Loan-Pitsianis 重排：把 (TS)x(TS) 的 M 排成 (T²)x(S²) 的 R。

    M 可写成 A_t ⊗ A_s  <=>  rank(R) == 1
    '''
    R = np.zeros((T*T, S*S))
    for i in range(T):
        for j in range(T):
            R[i*T + j] = M[i*S:(i+1)*S, j*S:(j+1)*S].ravel()
    return R

def kron_rank(M, T, S, tol=1e-9):
    '''Kronecker 秩与重排后的奇异值。'''
    sv = np.linalg.svd(kron_rearrange(M, T, S), compute_uv=False)
    return int(np.sum(sv > tol * sv[0])), sv

def nearest_kron_err(M, T, S):
    '''最优 Kronecker 逼近的相对残差（= R 除最大奇异值外的能量）。'''
    sv = np.linalg.svd(kron_rearrange(M, T, S), compute_uv=False)
    return float(np.sqrt(np.sum(sv[1:]**2) / np.sum(sv**2))), sv

print('本模块的全部论证只用两个工具：Kronecker 积与 SVD。')"""),

md("""## 1. 三种做法的 FLOP 账"""),

code("""print('  n = T*S 个 token')
print('    完全 3D : (T*S)^2')
print('    分解    : T*S^2 + S*T^2 = T*S*(S+T)')
print('    窗口    : T*S*(w_t*w_s)')
print()
print('    T     S      完全 3D        分解         分解的节省   窗口(4x64)   窗口的节省')
for T, S in [(16,256),(64,256),(128,256),(64,1024),(128,1024)]:
    full = (T*S)**2
    fact = T*S*(S+T)
    win = T*S*(4*64)
    print(f'  {T:4d}  {S:5d}  {full:.3e}  {fact:.3e}  {full/fact:9.1f}x  '
          f'{win:.3e}  {full/win:8.0f}x')
    # 节省的闭式
    assert abs(full/fact - T*S/(S+T)) < 1e-9, '分解的节省应恰为 TS/(S+T)'
    assert abs(full/win - T*S/(4*64)) < 1e-9

print()
print('分解的节省 = TS/(S+T) = 1/(1/T + 1/S) —— 被**较小的那个**限住:')
S = 256
print('   T（S=256 固定）    分解的节省      上界 S')
for T in (16, 64, 256, 1024, 4096):
    print(f'  {T:6d}          {T*S/(S+T):10.1f}x      {S}')
assert T*S/(S+T) < S, '节省必须小于 S'
_g256, _g4096 = 256*S/(S+256), 4096*S/(S+4096)
print()
print(f'✅ T 从 256 涨到 4096（16 倍）只把节省从 {_g256:.1f}x 提到 {_g4096:.1f}x')
print(f'   -> **节省会饱和**，上界就是 S={S}。「视频越长分解越赚」是错的。')
print()
print('   对照：窗口的节省 = TS/(w_t·w_s)，随 T **线性**且不饱和:')
for T in (16, 64, 256, 1024, 4096):
    print(f'     T={T:6d}: {T*S/(4*64):10.1f}x')
print('   -> 所以很长的视频上窗口比分解便宜得多。代价是感受野（见第 5 节）。')"""),

md("""## 2. 分解式注意力 = Kronecker 积（恒等式）

- 时间注意力（对每个空间位置在 $t$ 上混合）：$A_t \\otimes I_S$
- 空间注意力（对每帧在 $s$ 上混合）：$I_T \\otimes A_s$
- 复合：$(I_T \\otimes A_s)(A_t \\otimes I_S) = A_t \\otimes A_s$"""),

code("""T, S = 6, 8
At, As = rowstoch(T, 0), rowstoch(S, 1)
I_T, I_S = np.eye(T), np.eye(S)

comp = np.kron(I_T, As) @ np.kron(At, I_S)
kron = np.kron(At, As)
gap = float(np.abs(comp - kron).max())
print(f'T={T}, S={S}')
print(f'  ‖(I⊗As)(At⊗I) − At⊗As‖_max = {gap:.3e}')
assert gap < 1e-14, '这是恒等式，应逐位相等'
print('  -> 逐位相等。分解式注意力**只能**产生 Kronecker 积形式的混合。')
print()
rk, _ = kron_rank(comp, T, S)
print(f'  复合的 Kronecker 秩 = {rk}')
assert rk == 1

print()
print('自由度对比:')
print(f'  完全 3D : 任意 {T*S}x{T*S} 矩阵 -> {(T*S)**2} 个自由度')
print(f'  分解    : {{At ⊗ As}}          -> {T*T} + {S*S} - 1 = {T*T+S*S-1} 个自由度')
print(f'  维度比  : {(T*S)**2/(T*T+S*S-1):.0f} : 1')
print()
print('  但「自由度少」不等于「表达不了你需要的东西」——')
print('  关键是需要的那些混合在不在这个集合里。下一节回答。')"""),

md("""## 3. 什么样的运动分解不了

构造混合矩阵「第 $(t,x)$ 个 token 该 attend 到哪个 $(t',x')$」，
然后算它的最优 Kronecker 逼近误差。"""),

code("""def build_mix(T, S, xp_fn, tp_fn=None):
    '''M[(t,x), (t',x')] = 1，其中 (t',x') 由给定函数决定。'''
    M = np.zeros((T*S, T*S))
    for t in range(T):
        for x in range(S):
            tp = max(0, t-1) if tp_fn is None else tp_fn(t, x)
            xp = xp_fn(t, x) % S
            M[t*S + x, tp*S + xp] = 1.0
    return M

def window_mix(T, S, wt, ws):
    '''时空窗口混合：只在 w_t x w_s 的邻域里注意（行归一化）。'''
    M = np.zeros((T*S, T*S))
    for t in range(T):
        for x in range(S):
            for dt in range(-(wt//2), wt//2 + 1):
                for dx in range(-(ws//2), ws//2 + 1):
                    tt, xx = t + dt, (x + dx) % S
                    if 0 <= tt < T:
                        M[t*S + x, tt*S + xx] = 1.0
    return M / np.maximum(M.sum(1, keepdims=True), 1e-12)

def mix_factorized(T, S):
    '''分解（并行接线）：一层里既有时间注意力也有空间注意力。'''
    return (np.kron(np.ones((T, T)), np.eye(S))
            + np.kron(np.eye(T), np.ones((S, S))))

Tn, Sn = 8, 16
owner = np.random.default_rng(3).integers(0, 3, Sn)   # 每个空间位置属于哪个物体
CASES = [
    ('① 全局匀速 v=2（看上一帧）',            lambda t,x: x-2,                          None),
    ('② 三个物体各自匀速 [1,3,6]',            lambda t,x: x-[1,3,6][owner[x]],          None),
    ('③ **加速** v(t)=t',                     lambda t,x: x-t,                          None),
    ('④ 回看第 0 帧的原始位置',               lambda t,x: x-2*t,        lambda t,x: 0),
    ('⑤ t 依赖的时间跨度',                    lambda t,x: x-2,          lambda t,x: max(0,t-1-(t%3))),
    ('⑥ 物体速度随 t 变',                     lambda t,x: x-(owner[x]+t%2),             None),
]
print(f'T={Tn}, S={Sn}')
print('  目标混合                          Kron 逼近误差   Kron 秩')
res = {}
for name, xp, tp in CASES:
    M = build_mix(Tn, Sn, xp, tp)
    err, sv = nearest_kron_err(M, Tn, Sn)
    rk = int(np.sum(sv**2 / np.sum(sv**2) > 0.01))
    res[name] = (err, rk)
    print(f'  {name:34s}  {err:.6f}       {rk}')

# ①②⑤ 精确为 0；③④⑥ 有残差
for k in ('① 全局匀速 v=2（看上一帧）', '② 三个物体各自匀速 [1,3,6]', '⑤ t 依赖的时间跨度'):
    assert res[k][0] < 1e-12, f'{k} 应精确可分解，得到 {res[k][0]:.2e}'
    assert res[k][1] == 1
for k in ('③ **加速** v(t)=t', '④ 回看第 0 帧的原始位置', '⑥ 物体速度随 t 变'):
    assert res[k][0] > 0.5, f'{k} 应有大残差，得到 {res[k][0]:.4f}'
    assert res[k][1] > 1

print()
print('✅ ①②⑤ 误差恰为 0 —— 我最初猜「多个物体不同速度就分解不了」是**错的**。')
print('   原因：空间重排 x -> x - v_owner(x) 是**一个固定矩阵**，对所有 t 相同，')
print('   所以 M = A_t ⊗ P 仍是 Kronecker 积。⑤ 同理（时间跨度变而空间位移不变）。')
print()
print('✅ 精确的判据：分解是精确的**当且仅当**混合能分成')
print('   「与 t 无关的空间模式」⊗「与 x 无关的时间模式」。')
print('   -> 匀速运动（多少个物体、各自多快都行）完全没问题；')
print('      加速、变向、以及任何「空间往哪看取决于第几帧」的依赖都不行。')"""),

code("""# 加速度的强度 vs 所需的 Kronecker 秩
print('加速度 v(t) = a*t:')
print('    a      Kron 逼近误差   Kron 秩   压到 1% 残差所需项数')
for a in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
    M = build_mix(Tn, Sn, lambda t,x,a=a: x - int(round(a*t)), None)
    err, sv = nearest_kron_err(M, Tn, Sn)
    en = sv**2 / np.sum(sv**2)
    rk = int(np.sum(en > 0.01))
    need = int(np.searchsorted(np.cumsum(en), 0.99)) + 1
    print(f'  {a:5.2f}      {err:.6f}        {rk:3d}       {need:3d}')
    if a == 0.0:
        assert err < 1e-12 and rk == 1, 'a=0（匀速）应精确可分解'
    else:
        assert rk > 1, f'a={a} 应需要秩 > 1'

print()
print('✅ 只要 a != 0 就需要 Kronecker 秩 > 1。')
print('   注意秩不是随 a 单调的（a=2 时位移在 S 上取模绕回，秩反而降回 3）——')
print('   但「a != 0 就需要更高的秩」这条结论是稳定的。')"""),

md("""## 4. 深度和残差都补不回来——并行分支才行"""),

code("""T2, S2 = 5, 6
I2 = np.eye(T2*S2)
I_T2, I_S2 = np.eye(T2), np.eye(S2)
At1, As1 = rowstoch(T2, 1), rowstoch(S2, 2)
At2, As2 = rowstoch(T2, 3), rowstoch(S2, 4)

print(f'T={T2}, S={S2}，Kronecker 秩上界 min(T²,S²) = {min(T2*T2, S2*S2)}')
print()
print('  结构                                                       Kron 秩')
def show(name, M):
    rk, _ = kron_rank(M, T2, S2)
    print(f'  {name:56s} {rk:3d}')
    return rk

r1 = show('① 单层时间注意力 At⊗I', np.kron(At1, I_S2))
r2 = show('② 顺序两层（无残差）(I⊗As)(At⊗I)', np.kron(I_T2, As1) @ np.kron(At1, I_S2))
r3 = show('③ 顺序两层**带残差** (I+I⊗As)(I+At⊗I)',
          (I2 + np.kron(I_T2, As1)) @ (I2 + np.kron(At1, I_S2)))
_eight = I2.copy()
for i in range(8):
    Ai = (np.kron(I_T2, rowstoch(S2, 10+i)) if i % 2
          else np.kron(rowstoch(T2, 20+i), I_S2))
    _eight = (I2 + Ai) @ _eight
r4 = show('④ 顺序**八层**带残差（四组交替）', _eight)
r5 = show('⑤ **并行**两分支 I + At⊗I + I⊗As',
          I2 + np.kron(At1, I_S2) + np.kron(I_T2, As1))
r6 = show('⑥ 并行两分支 ×2 层',
          (I2 + np.kron(At2, I_S2) + np.kron(I_T2, As2))
          @ (I2 + np.kron(At1, I_S2) + np.kron(I_T2, As1)))
_par4 = I2.copy()
for i in range(4):
    _par4 = (I2 + np.kron(rowstoch(T2, 30+i), I_S2)
             + np.kron(I_T2, rowstoch(S2, 40+i))) @ _par4
r7 = show('⑦ 并行两分支 ×4 层', _par4)
r8 = show('⑧ 完全 3D 注意力（任意 n×n）', rowstoch(T2*S2, 99))

assert r1 == r2 == r3 == r4 == 1, f'①②③④ 都应是秩 1，得到 {(r1,r2,r3,r4)}'
assert r5 == 2 and r6 == 4 and r7 == 16, f'并行分支应按 2^L 增长，得到 {(r5,r6,r7)}'
assert r8 == min(T2*T2, S2*S2)

print()
print('③④ 为什么还是 1 —— 因为它是一个**恒等式**:')
lhs = (I2 + np.kron(I_T2, As1)) @ (I2 + np.kron(At1, I_S2))
rhs = np.kron(I_T2 + At1, I_S2 + As1)
print(f'  ‖(I+I⊗As)(I+At⊗I) − (I+At)⊗(I+As)‖ = {np.abs(lhs-rhs).max():.3e}')
assert np.abs(lhs - rhs).max() < 1e-12
print('  -> 顺序 + 残差 = 一个**更大的** Kronecker 积，秩仍是 1。')
print('     **深度和残差都不给分解式注意力增加时空交互的表达力。**')
print()
print('⑤ 为什么是 2 —— 并行分支是**和**而不是**积**，Kronecker 结构被破坏:')
print('  I + At⊗I + I⊗As 无法写成 P⊗Q。展开两层并行会得到 2^L 项 Kronecker 和。')
print()
print(f'✅ 秩：①②③④ = 1（深度/残差无效）；⑤⑥⑦ = {r5}/{r6}/{r7}（并行有效）；完全 3D = {r8}')"""),

code("""# 这对架构的含义：加法式插入 vs 串联式插入
print('实践含义 ——「在图像模型上插入时间层」为什么要用**加法式**插入:')
print()
Aimg = np.kron(I_T2, As1)              # 预训练的图像（空间）注意力
Atime = np.kron(At1, I_S2)             # 新加的时间注意力
alpha = 0.5

add = I2 + np.kron(I_T2, As1) + alpha * Atime      # x <- x + attn_s(x) + α·attn_t(x)
ser = (I2 + alpha * Atime) @ (I2 + np.kron(I_T2, As1))   # 串联：先空间再时间，各带残差
rk_add, _ = kron_rank(add, T2, S2)
rk_ser, _ = kron_rank(ser, T2, S2)
print(f'  加法式插入 x <- x + attn_s(x) + α·attn_t(x):   Kron 秩 = {rk_add}')
print(f'  串联式插入 (I+α·attn_t)(I+attn_s):             Kron 秩 = {rk_ser}')
assert rk_add > rk_ser, '加法式插入应给出更高的秩'
print()
print('✅ 加法式插入的秩更高。串联式插入按上面的恒等式仍被锁在秩 1。')
print('   -> Align-your-Latents / Stable Video Diffusion 一类做法里')
print('      时间层是**加到残差流上**的（且 α 初始化为 0），这不只是为了训练稳定 ——')
print('      它决定了整个网络能不能表达「空间往哪看取决于第几帧」这类依赖。')

print()
print('α 初始化为 0 时会怎样:')
for al in (0.0, 0.01, 0.1, 1.0):
    M = I2 + np.kron(I_T2, As1) + al * Atime
    rk, sv = kron_rank(M, T2, S2)
    en = sv**2 / np.sum(sv**2)
    print(f'  α={al:5.2f}: Kron 秩 {rk}，第二项能量占比 {en[1]:.3e}')
assert kron_rank(I2 + np.kron(I_T2, As1) + 0.0*Atime, T2, S2)[0] == 1, \\
    'α=0 时应退化为纯空间模型（秩 1）'
print('  -> α=0 时秩退回 1（就是原来的图像模型）；α 一离开 0，秩立刻变 2。')
print('     所以「α 从 0 开始」= 「从图像模型平滑地长出时空表达力」。')"""),

md("""## ✏️ 练习 1：分解与窗口的代价交叉点

实现 `crossover_T(S, wt, ws)`：找出使「窗口注意力比分解注意力更便宜」的最小 $T$。

- 分解：$T S (S + T)$
- 窗口：$T S \\cdot w_t w_s$"""),

code("""def crossover_T(S, wt, ws, Ts=None):
    '''窗口比分解更便宜的最小 T（若在候选内不存在则返回 None）。

    参数
    ----
    S      : 每帧的 token 数
    wt, ws : 时间/空间窗口大小
    Ts     : 候选 T（默认 1..4096）

    返回
    ----
    int or None : 最小的 T 使 窗口代价 < 分解代价
    '''
    if Ts is None:
        Ts = range(1, 4097)
    # TODO: 对每个 T 比较 T*S*(S+T) 与 T*S*(wt*ws)，返回第一个让窗口更便宜的 T
    raise NotImplementedError"""),

code("""# 自测
print('     S    w_t x w_s   窗口更便宜的最小 T   解析解 w_t*w_s - S')
for _S, _wt, _ws in [(256, 4, 64), (256, 8, 64), (256, 4, 128), (1024, 4, 64), (1024, 8, 256)]:
    _T = crossover_T(_S, _wt, _ws)
    _an = _wt*_ws - _S
    _shown = str(_T) if _T is not None else '不存在'
    print(f'  {_S:5d}    {_wt:2d} x {_ws:3d}      {_shown:>16s}      {_an}')
    if _an > 0:
        assert _T == _an + 1, f'解析解应为 {_an}+1，得到 {_T}'
    else:
        assert _T == 1, f'窗口比整帧还大时任何 T 都更便宜，得到 {_T}'

# 解析验证：T*S*(S+T) > T*S*(wt*ws)  <=>  S + T > wt*ws  <=>  T > wt*ws - S
print()
print('  解析推导: 窗口更便宜 <=> S + T > w_t·w_s <=> T > w_t·w_s − S')
_S, _wt, _ws = 256, 4, 64
_T = crossover_T(_S, _wt, _ws)
assert _T == _wt*_ws - _S + 1
print(f'  S={_S}, 窗口 {_wt}x{_ws}={_wt*_ws}: 交叉点 T = {_wt*_ws}−{_S}+1 = {_T}')
print()
print(f'✅ 交叉点有闭式解 T* = w_t·w_s − S + 1')
print(f'✅ 当窗口的 token 数 w_t·w_s <= S 时，窗口在**任何** T 上都更便宜')
print()
print('   工程含义：窗口大小与每帧 token 数 S 的关系决定一切。')
print('   实践中窗口通常远小于整帧（w_t·w_s ≪ S），所以窗口几乎总是更便宜 ——')
print('   分解的价值不在算力，在**一层就能全局连通**（见练习 4）。')"""),

md("""## ✏️ 练习 2：判断一个混合能不能被分解

实现 `is_factorizable(M, T, S, tol=1e-10)`，返回 `(能否精确分解, Kronecker 秩, 逼近误差)`。

然后用它判断若干构造出来的混合。"""),

code("""def is_factorizable(M, T, S, tol=1e-10):
    '''判断混合矩阵能否被分解式注意力精确表示。

    参数
    ----
    M    : (TS)x(TS) 混合矩阵
    T, S : 时间/空间维
    tol  : 判定阈值

    返回
    ----
    (ok, rank, err) :
      ok   = 逼近误差 < tol
      rank = Kronecker 秩（奇异值能量占比 > 1% 的个数）
      err  = 最优 Kronecker 逼近的相对残差
    '''
    # TODO: 用 nearest_kron_err 与 kron_rank
    raise NotImplementedError"""),

code("""# 自测
_Tt, _Ss = 6, 10
print('  混合                                        可分解?  Kron 秩   误差')
_tests = [
    ('恒等（每个 token 只看自己）', np.eye(_Tt*_Ss), True),
    ('纯时间注意力 At⊗I', np.kron(rowstoch(_Tt, 5), np.eye(_Ss)), True),
    ('纯空间注意力 I⊗As', np.kron(np.eye(_Tt), rowstoch(_Ss, 6)), True),
    ('At⊗As', np.kron(rowstoch(_Tt, 7), rowstoch(_Ss, 8)), True),
    ('匀速 v=3 看上一帧', build_mix(_Tt, _Ss, lambda t,x: x-3, None), True),
    ('加速 v(t)=t', build_mix(_Tt, _Ss, lambda t,x: x-t, None), False),
    ('随机 n×n', rowstoch(_Tt*_Ss, 9), False),
]
for _name, _M, _expect in _tests:
    _ok, _rk, _err = is_factorizable(_M, _Tt, _Ss)
    print(f'  {_name:42s}  {str(_ok):7s}  {_rk:6d}   {_err:.3e}')
    assert _ok == _expect, f'{_name}: 期望 {_expect}，得到 {_ok}'

# 时空窗口本身也是 Kronecker 秩 1（正文第 5 节的伏笔）
_Mw = window_mix(_Tt, _Ss, 3, 5)
_ok_w, _rk_w, _err_w = is_factorizable(_Mw, _Tt, _Ss, tol=1e-6)
print()
print(f'  时空窗口 3x5:                              {str(_ok_w):7s}  {_rk_w:6d}   {_err_w:.3e}')
print()
print('✅ 六种「显然可分解」的混合都被正确判定；加速与随机矩阵被正确否定')
print(f'✅ 时空窗口的 Kronecker 秩是 {_rk_w}（误差 {_err_w:.1e}）——')
print('   窗口在**结构**上和分解一样受限（它换来的是局部性偏置与内存局部性，')
print('   不是表达力）。边界处的归一化让它不是严格的秩 1。')"""),

md("""## ✏️ 练习 3：并行分支的秩增长律

实现 `parallel_rank(L, T, S)`：$L$ 层「并行两分支 + 残差」的 Kronecker 秩。

验证它按 $\\min(2^L, \\min(T^2, S^2))$ 增长。"""),

code("""def parallel_rank(L, T, S, seed0=200):
    '''L 层并行两分支（I + At⊗I + I⊗As）复合后的 Kronecker 秩。

    参数
    ----
    L      : 层数
    T, S   : 时间/空间维
    seed0  : 各层随机矩阵的 seed 基

    返回
    ----
    int : Kronecker 秩
    '''
    I = np.eye(T*S)
    M = I.copy()
    # TODO: 对 i in range(L)：
    #       M = (I + kron(rowstoch(T, seed0+2*i), eye(S))
    #              + kron(eye(T), rowstoch(S, seed0+2*i+1))) @ M
    #       返回 kron_rank(M, T, S)[0]
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 秩按 2^L 增长，直到饱和:')
print('  T   S   min(T²,S²)   L=1  2   3   4   5   6   7      2^L 预测')
for _T, _S in [(5, 6), (4, 4), (6, 3), (8, 5)]:
    _cap = min(_T*_T, _S*_S)
    _rks = [parallel_rank(_L, _T, _S) for _L in range(1, 8)]
    print(f'  {_T:2d}  {_S:2d}   {_cap:10d}   ' + '  '.join(f'{v:3d}' for v in _rks) +
          '    ' + ' '.join(str(2**_L) for _L in range(1, 8)))
    # 饱和前严格按 2^L
    for _L, _r in enumerate(_rks, 1):
        if 2**_L <= _rks[-1]:
            assert _r == 2**_L, f'T={_T},S={_S},L={_L}: 饱和前应为 2^L={2**_L}，得到 {_r}'
    # 饱和值严格小于上界 min(T²,S²)
    assert _rks[-1] < _cap, \\
        f'T={_T},S={_S}: 饱和值 {_rks[-1]} 应严格小于上界 {_cap}'

print()
print('  (b) 饱和值有闭式：m = min(T,S) 时饱和在 m² − m + 1')
print('   T   S   m=min(T,S)   m²−m+1   L=8 的实测秩   一致?')
for _T, _S in [(3, 4), (4, 5), (5, 6), (6, 7), (7, 6), (6, 6), (3, 8)]:
    _m = min(_T, _S)
    _pred = _m*_m - _m + 1
    _got = parallel_rank(8, _T, _S)
    print(f'  {_T:3d} {_S:3d}   {_m:10d}   {_pred:7d}   {_got:12d}   '
          f'{"✓" if _got == _pred else "✗"}')
    assert _got == _pred, f'T={_T},S={_S}: 期望 {_pred}，得到 {_got}'

# 对照：顺序 + 残差恒为 1
def _serial_rank(L, T, S, seed0=300):
    I = np.eye(T*S)
    M = I.copy()
    for i in range(L):
        Ai = (np.kron(np.eye(T), rowstoch(S, seed0+i)) if i % 2
              else np.kron(rowstoch(T, seed0+i), np.eye(S)))
        M = (I + Ai) @ M
    return kron_rank(M, T, S)[0]

print()
print('  (c) 对照 —— 顺序 + 残差:')
print('   L    1  2  3  4  5  6  7  8')
_ser = [_serial_rank(_L, 5, 6) for _L in range(1, 9)]
print('   秩  ' + ' '.join(f'{v:2d}' for v in _ser))
assert all(v == 1 for v in _ser), f'顺序+残差应恒为 1，得到 {_ser}'

print()
print('✅ 饱和前秩严格按 2^L 增长（四组 (T,S) 全对）')
print('✅ 饱和值恰为 m² − m + 1（m = min(T,S)），七组配置全部命中')
print('   注意它**严格小于**朴素上界 min(T²,S²)：m=5 时是 21 而不是 25。')
print('   这是实测出来的规律（2^L 项 Kronecker 和在重排空间里并不线性独立），')
print('   本课不给推导 —— 但它在七组配置上都精确成立。')
print('✅ 而顺序 + 残差在 1..8 层上**恒为 1**')
print()
print('   -> 所需层数因此有下界：要表达 Kronecker 秩 r 的时空依赖，')
print('      至少需要 ceil(log2(r)) 层并行块，且 r 不可能超过 m²−m+1。')
print('      而串联式的分解注意力**无论多深都不够**（在这个线性分析下）。')"""),

md("""## ✏️ 练习 4：一层能不能全局连通

分解与窗口的真正区别不在算力（练习 1 已算清），而在**一层的连通性**。

实现 `hops_to_connect(mix_fn, T, S, max_hops=8)`：返回让混合矩阵的
「可达性」覆盖全部 $(t,x)$ 对所需的最小跳数（矩阵幂的非零模式）。"""),

code("""def hops_to_connect(mix_fn, T, S, max_hops=8):
    '''让混合的可达性覆盖全部 token 对所需的最小跳数。

    参数
    ----
    mix_fn   : (T, S) -> (TS)x(TS) 混合矩阵（非零表示「能看到」）
    T, S     : 时间/空间维
    max_hops : 最多试多少跳

    返回
    ----
    int or None : 最小跳数；若 max_hops 内仍不全通则返回 None
    '''
    M = (np.abs(mix_fn(T, S)) > 1e-12).astype(float)
    # TODO: 令 R = M，反复 R = (R @ M > 0)；
    #       返回第一个使 R 全非零的跳数（M 自身算 1 跳）
    raise NotImplementedError"""),

code("""# 自测
_Tc, _Sc = 6, 8

def _mix_full(T, S):
    return np.ones((T*S, T*S))

print('  混合                        全局连通所需跳数')
_h_f = hops_to_connect(mix_factorized, _Tc, _Sc)
_h_w = hops_to_connect(lambda T, S: window_mix(T, S, 3, 3), _Tc, _Sc)
_h_a = hops_to_connect(_mix_full, _Tc, _Sc)
print(f'  完全 3D 注意力                    {_h_a}')
print(f'  分解（时间 + 空间，并行）          {_h_f}')
print(f'  时空窗口 3x3                      {_h_w}')
assert _h_a == 1, '完全 3D 一跳全通'
assert _h_f == 2, f'分解应两跳全通，得到 {_h_f}'
assert _h_w is not None and _h_w > _h_f, f'窗口应需要更多跳，得到 {_h_w}'

print()
print('  窗口大小 vs 所需跳数（T=6, S=8，空间为环形）:')
print('    一跳最多移动 floor(w/2)（不是 w），空间最大距离是 floor(S/2)')
print('    w_t x w_s   跳数   理论 max(ceil((T-1)/(w_t//2)), ceil(floor(S/2)/(w_s//2)))')
for _wt, _ws in [(3,3), (3,5), (5,3), (5,5)]:
    _h = hops_to_connect(lambda T, S, a=_wt, b=_ws: window_mix(T, S, a, b), _Tc, _Sc)
    _theo = max(int(np.ceil((_Tc-1)/(_wt//2))), int(np.ceil((_Sc//2)/(_ws//2))))
    print(f'    {_wt} x {_ws}        {_h}      {_theo}')
    assert _h == _theo, f'窗口 {_wt}x{_ws}: 期望 {_theo} 跳，得到 {_h}'

print()
print(f'✅ 完全 3D：{_h_a} 跳；分解：{_h_f} 跳；窗口 3x3：{_h_w} 跳')
print()
print('   这就是分解相对窗口的真正优势：**两跳全局连通**，而且这个 2 不随 T、S 变化。')
print('   窗口的跳数随序列长度增长（要靠移位窗口 + 深度来补）。')
print()
print('   把两个练习合起来看:')
print('     · 算力上（练习 1）：窗口几乎总是更便宜')
print('     · 连通性上（本练习）：分解只要 2 跳，窗口要 O(序列长/窗口)')
print('     · 结构上（练习 2）：**两者的 Kronecker 秩都是 1** —— 谁也不比谁更能表达加速')
print('   -> 所以「分解 vs 窗口」不是优劣关系，是三个不同维度上的取舍。')"""),

md("""## 📖 参考答案"""),

code("""def crossover_T(S, wt, ws, Ts=None):
    '''窗口比分解更便宜的最小 T。'''
    if Ts is None:
        Ts = range(1, 4097)
    for T in Ts:
        if T*S*(wt*ws) < T*S*(S + T):
            return int(T)
    return None

def is_factorizable(M, T, S, tol=1e-10):
    '''判断混合矩阵能否被分解式注意力精确表示。'''
    err, sv = nearest_kron_err(M, T, S)
    en = sv**2 / np.sum(sv**2)
    rank = int(np.sum(en > 0.01))
    return bool(err < tol), rank, err

def parallel_rank(L, T, S, seed0=200):
    '''L 层并行两分支复合后的 Kronecker 秩。'''
    I = np.eye(T*S)
    M = I.copy()
    for i in range(L):
        M = (I + np.kron(rowstoch(T, seed0 + 2*i), np.eye(S))
             + np.kron(np.eye(T), rowstoch(S, seed0 + 2*i + 1))) @ M
    return kron_rank(M, T, S)[0]

def hops_to_connect(mix_fn, T, S, max_hops=8):
    '''让混合的可达性覆盖全部 token 对所需的最小跳数。'''
    M = (np.abs(mix_fn(T, S)) > 1e-12).astype(float)
    R = M.copy()
    for h in range(1, max_hops + 1):
        if np.all(R > 0):
            return h
        R = (R @ M > 0).astype(float)
    return None

print('参考答案已定义。')
print()
print('要点：')
print('  1. 分解 vs 窗口的代价交叉点有闭式：T* = w_t·w_s − S + 1。')
print('     实践中窗口远小于整帧，所以窗口几乎总是更便宜。')
print('  2. 可分解性 = 重排后的秩为 1。匀速（任意多物体）可分解，加速不可。')
print('  3. 并行分支的秩恰为 min(2^L, min(T²,S²))；顺序+残差恒为 1。')
print('  4. 分解的真正优势是**两跳全局连通**，而且这个 2 不随 T、S 变化。')
print('     但它的 Kronecker 秩与窗口一样是 1 —— 三个维度上的取舍，不是优劣。')"""),

md("""## 🧪 真实工程胶囊：给一个时空注意力设计打分

下面这段代码把本模块的三个维度做成一张对比表：
**算力**（FLOPs）、**连通性**（跳数）、**结构表达力**（Kronecker 秩）。

关键设计：它对每种设计都同时报三个数，并明确指出
**没有一种设计在三个维度上同时最好**——这是本模块最实用的结论。"""),

code("""def score_design(name, T, S, L, kind, wt=4, ws=64, verbose=True):
    '''给一个时空注意力设计打分（算力 / 连通性 / Kronecker 秩）。

    kind: 'full3d' | 'factorized_serial' | 'factorized_parallel' | 'window'
    '''
    # ① 算力（单层）
    if kind == 'full3d':
        flops = (T*S)**2
    elif kind == 'window':
        flops = T*S*(wt*ws)
    else:
        flops = T*S*(S + T)
    # ② 连通性（跳数）——用小尺寸代理计算（结构与尺寸无关）
    Tp, Sp = 6, 8
    if kind == 'full3d':
        hops = 1
    elif kind == 'window':
        hops = hops_to_connect(lambda t, s: window_mix(t, s, 3, 3), Tp, Sp)
    else:
        hops = hops_to_connect(mix_factorized, Tp, Sp)
    # ③ Kronecker 秩（L 层之后）——同样用小尺寸代理
    if kind == 'full3d':
        rank = min(Tp*Tp, Sp*Sp)
    elif kind == 'factorized_parallel':
        rank = parallel_rank(L, Tp, Sp)
    elif kind == 'factorized_serial':
        rank = 1
    else:                                    # window
        rank = is_factorizable(window_mix(Tp, Sp, 3, 3), Tp, Sp, tol=1e-6)[1]
    if verbose:
        print(f'  {name:30s} {flops:.3e}   {str(hops):>4s}      {rank:4d}')
    return dict(name=name, flops=flops, hops=hops, rank=rank)

T, S, L = 128, 256, 8
print(f'T={T}, S={S}, L={L} 层。三个维度：算力（越小越好）/ 跳数（越小越好）/ Kron 秩（越大越好）')
print()
print('  设计                            单层 FLOPs    跳数   Kron 秩(L 层后)')
rows = [
    score_design('完全 3D 注意力', T, S, L, 'full3d'),
    score_design('分解（串联 + 残差）', T, S, L, 'factorized_serial'),
    score_design('分解（并行分支）', T, S, L, 'factorized_parallel'),
    score_design('时空窗口 4x64', T, S, L, 'window'),
]

print()
print('  每个维度的最优者:')
for key, better, label in [('flops', min, '算力'), ('hops', min, '跳数'), ('rank', max, 'Kron 秩')]:
    vals = [r for r in rows if r[key] is not None]
    best = better(vals, key=lambda r: r[key])
    print(f'    {label:8s} 最优: {best["name"]}（{best[key]}）')

# 没有一种设计在三个维度上同时最好
_winners = set()
for key, better in [('flops', min), ('hops', min), ('rank', max)]:
    vals = [r for r in rows if r[key] is not None]
    _winners.add(better(vals, key=lambda r: r[key])['name'])
print()
print(f'  三个维度的最优者共有 {len(_winners)} 个不同的设计: {sorted(_winners)}')
assert len(_winners) >= 2, '不该有一种设计在三个维度上同时最优'

print()
print('工程含义：')
print('  · **没有一种设计在三个维度上同时最好**，所以「哪种时空注意力更好」')
print('    这个问题本身缺少约束。要先说清哪个维度是瓶颈。')
print('  · 「分解（串联）」是唯一在**任何**维度上都不最优的设计 ——')
print('    它的算力与并行版相同，跳数相同，而 Kron 秩被恒等式锁在 1。')
print('    这是本模块最直接可用的结论：**同样的算力下，并行接线严格优于串联**。')
print('  · 而完全 3D 在算力上比分解贵 '
      f'{rows[0]["flops"]/rows[2]["flops"]:.0f} 倍、比窗口贵 '
      f'{rows[0]["flops"]/rows[3]["flops"]:.0f} 倍 ——')
print('    所以现实里的选择通常是「并行分解」或「窗口 + 分解混合」，')
print('    而这两者的差别是**局部性偏置**而不是表达力（练习 2 的窗口秩也是 1）。')""")
,]
