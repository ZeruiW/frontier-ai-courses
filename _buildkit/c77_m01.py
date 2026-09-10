# -*- coding: utf-8 -*-
"""C77 模块 01 · 视频 latent 与 tokenizer：时间维压缩的账。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（时间轴的代价、3D 压缩收益 = 相关性）；"
                 "<strong>C28 模块 01（Latent Diffusion）</strong>——"
                 "「为什么不在像素上做扩散」「VAE 的作用」在那里，本课不重讲，"
                 "只处理<em>时间维</em>；PCA/SVD、k-means（本课的 VQ 用它）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_video_latent.ipynb'
                       '（<strong>流式（因果）的代价非单调</strong>：'
                       'corr$=0$ 时 $0.9984\\times$、corr$=0.95$ 时峰值 $1.0308\\times$、'
                       'corr$=0.995$ 时又回到 $1.0060\\times$ / '
                       '<strong>代价的峰值落在每个 chunk 的<em>最后</em>一帧</strong>'
                       '（$1.12$ / $1.09$ / $1.10$），而最后一个 chunk 恒为 $1.00$ / '
                       '<strong>固定比特预算下「少而大的 token」更划算</strong>：'
                       '$4$ 个 token $\\times$ $256$ 码本（$0.534$）胜过 '
                       '$16$ 个 token $\\times$ $4$ 码本（$0.843$），差 $1.58\\times$）'),
    ("核心参考", "Rombach et al., <em>High-Resolution Image Synthesis with Latent "
                 "Diffusion Models</em>（CVPR 2022，图像侧的地基，见 C28-01）· "
                 "Yu et al., <em>MAGVIT-v2: Language Model Beats Diffusion — Tokenizer is "
                 "Key to Visual Generation</em>（ICLR 2024）· "
                 "Yu et al., <em>MAGVIT</em>（CVPR 2023，3D VQ）· "
                 "Agarwal et al., <em>Cosmos Tokenizer</em>（NVIDIA, 2025，因果时空 tokenizer）· "
                 "Blattmann et al., <em>Stable Video Diffusion</em>（2023，时间层的加法式设计）· "
                 "van den Oord et al., <em>VQ-VAE</em>（NeurIPS 2017）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [

("three", "视频 latent 的三个决定", "".join([
    P("C28 模块 01 已经回答了「为什么不在像素上做扩散」。"
      "把它推广到视频时要多做三个决定，而这三个决定基本互不影响、可以分开讨论："),
    TABLE(["决定", "取值范围（工业实践）", "影响什么", "本课量出的账"],
          [["空间压缩率 $p_h \\times p_w$", "$8\\times8$ 到 $16\\times16$",
            "空间细节 / token 数", "与图像同理，C28-01 已覆盖"],
           ["<strong>时间压缩率 $p_t$</strong>", "$1$（逐帧）到 $8$",
            "时间细节 / <strong>代价 $\\propto 1/p_t^2$</strong>",
            "收益取决于相关性；$\\text{corr}^{p_t}$ 是有效相关性"],
           ["<strong>因果性</strong>", "因果（流式）/ 非因果（整段）",
            "能不能流式推理 / 能不能与图像共享权重",
            "代价 $\\leq 3.1\\%$ 且<strong>非单调</strong>"],
           ["连续 vs 离散", "VAE latent / VQ token",
            "接扩散还是接自回归 LM", "固定比特下「少而大的 token」更划算"]]),
    P("第二行的 $\\propto 1/p_t^2$ 来自模块 00：注意力代价是 $(T/p_t)^2 S^2$，"
      "所以 <strong>$p_t$ 是唯一能平方级换回算力的旋钮</strong>。"
      "这也是为什么工业模型几乎都做时间压缩，而压多少是一个真正的取舍。"),
    CALLOUT("intuition", "一个被忽略的约束",
            "$p_t = 1$（不做时间压缩）有一个特殊的好处："
            "视频 latent 与图像 latent <strong>逐位兼容</strong>，"
            "于是可以直接复用图像 VAE 的权重、也可以在图文混合数据上训练。"
            "$p_t > 1$ 一旦引入，这个兼容性就没了——"
            "所以「要不要做时间压缩」不只是算力问题，还是<em>能不能继承图像模型</em>的问题。"
            "工业上常见的折中是让第一个 latent 帧只看一帧（$p_t=1$）、"
            "后续的才压缩，这样单帧输入依然兼容。"),
])),

("gain", "时间压缩的收益：有效相关性", "".join([
    P("模块 00 已经量出「3D 压缩的收益是时间相关性的函数」"
      "（corr$=0$ 时 $0.984\\times$，corr$=0.99$ 时 $4.49\\times$）。"
      "本节把它变成一条可以用来<strong>选 $p_t$</strong> 的规则。"),
    P("如果原始相邻帧的相关性是 $\\rho$，且时间结构近似一阶马尔可夫，"
      "那么压缩 $p_t$ 倍之后，相邻 <em>latent 帧</em> 之间的有效相关性是"),
    MATH("\\rho_{\\text{eff}} = \\rho^{p_t}"),
    TABLE(["$\\rho$（原始）", "$p_t{=}1$", "$p_t{=}2$", "$p_t{=}4$", "$p_t{=}8$", "$p_t{=}16$"],
          [["$0.99$", "$0.990$", "$0.980$", "$0.961$", "$0.923$", "$0.851$"],
           ["$0.95$", "$0.950$", "$0.903$", "$0.815$", "$0.663$", "$0.440$"],
           ["$0.90$", "$0.900$", "$0.810$", "$0.656$", "$0.430$", "$\\mathbf{0.185}$"],
           ["$0.70$", "$0.700$", "$0.490$", "$0.240$", "$\\mathbf{0.058}$", "$0.003$"]]),
    P("把这张表和模块 00 的收益表对照就得到一条判据："
      "<strong>压到 $\\rho_{\\text{eff}} < 0.3$ 之后，时间维已经几乎没有可利用的冗余</strong>——"
      "再增大 $p_t$ 只是在丢信息，不再省下「结构」。"
      "对 $\\rho{=}0.90$ 的素材这个上限大约是 $p_t{=}12$；对 $\\rho{=}0.70$ 只有 $p_t{=}4$。"),
    CALLOUT("warn", "$\\rho$ 必须从数据估，而它在数据集内部差异极大",
            "同一个数据集里，「固定机位的风景」与「快速剪辑的预告片」的 $\\rho$ 可以差一个数量级。"
            "用全局常数 $p_t$ 意味着对前者压得不够、对后者压过头。"
            "notebook 的练习 1 给出 $\\rho$ 的一个鲁棒估法，"
            "而工程上更彻底的做法是<strong>按镜头切分</strong>（shot detection）后分别压缩——"
            "因为 $\\rho$ 在镜头边界处会断崖式下降。"),
])),

("causal", "因果（流式）的代价：一个非单调的量", "".join([
    P("非因果 tokenizer 可以看到整段视频；因果 tokenizer 只能看过去。"
      "后者是流式推理与「无限长视频」的前提，代价是什么？"),
    P("notebook 的设定让两者<strong>总预算完全相同</strong>"
      "（时间下采样步长 $s$、每个 latent $k$ 维），差别只在解码时能用哪些 latent："),
    ASCII("""
   总预算相同: (T/s) 个 latent，每个 k 维

   非因果解码第 t 帧:  可用 latent 0 1 2 3 ... T/s-1   （全部）
                                   ^t 在这里
   因果解码第 t 帧  :  可用 latent 0 1 2            （只到 t//s）
                                   ^t 在这里，后面的还没产生
""".strip("\n")),
    TABLE(["$s$", "$k$", "总预算", "非因果均值", "因果均值", "流式的代价"],
          [["$2$", "$8$", "$64$", "$0.18941$", "$0.19342$", "$1.021\\times$"],
           ["$4$", "$16$", "$64$", "$0.18635$", "$0.18696$", "$1.003\\times$"],
           ["$4$", "$8$", "$32$", "$0.24403$", "$0.25201$", "$\\mathbf{1.033\\times}$"],
           ["$8$", "$16$", "$32$", "$0.23829$", "$0.24022$", "$1.008\\times$"]]),
    P("代价很小（$\\leq 3.3\\%$）。但它<strong>不是均匀分布</strong>的。"
      "$s{=}4, k{=}8$ 那一行的逐帧比值是"),
    CODE("1.05 1.03 1.01 [1.12] | 1.03 1.02 1.01 [1.09] | 1.03 1.02 1.01 [1.10] | 1.00 1.00 1.00 1.00\n"
         "                ^ chunk 的最后一帧                                        ^ 最后一个 chunk"),
    P("<strong>峰值落在每个 chunk 的<em>最后</em>一帧</strong>，而不是第一帧——"
      "那正是最需要「紧邻的未来」的位置。"
      "而最后一个 chunk 恒为 $1.00$，因为那里因果与非因果<em>等价</em>（后面本来就没有 latent 了）。"),
    H3("代价对相关性是非单调的"),
    TABLE(["corr", "非因果误差", "因果误差", "流式的代价", "解读"],
          [["$0.000$", "$0.77309$", "$0.77187$", "$0.9984\\times$", "未来<strong>无信息</strong>"],
           ["$0.300$", "$0.70628$", "$0.70719$", "$1.0013\\times$", ""],
           ["$0.600$", "$0.55280$", "$0.56070$", "$1.0143\\times$", ""],
           ["$0.800$", "$0.40524$", "$0.41710$", "$1.0293\\times$", ""],
           ["$\\mathbf{0.950}$", "$0.24538$", "$0.25293$", "$\\mathbf{1.0308\\times}$",
            "<strong>峰值</strong>"],
           ["$0.995$", "$0.17215$", "$0.17318$", "$1.0060\\times$",
            "未来与过去<strong>高度冗余</strong>"]]),
    DUAL("两端都便宜，中间最贵。相关性为零时未来什么也不提供，"
         "所以看不见未来毫无损失；相关性接近 1 时未来与过去几乎是同一件事，"
         "看过去就等于看了未来。只有在中间——未来带着过去没有的信息、"
         "而那信息又确实有用——因果性才真的要付钱。",
         "记 $I(\\cdot)$ 为互信息。因果性的代价正比于"
         "$I(X_t ; X_{>t} \\mid X_{\\leq t})$——"
         "未来在<em>给定过去之后</em>还剩下的、关于当前的信息。"
         "对 AR(1)，$X_{>t} \\perp X_t \\mid X_{t}$ 之外的部分随 $\\rho$ 变化："
         "$\\rho \\to 0$ 时 $X_{>t}$ 与 $X_t$ 独立（该条件互信息为 $0$）；"
         "$\\rho \\to 1$ 时 $X_{>t}$ 由 $X_{\\leq t}$ 几乎确定（条件互信息也趋于 $0$）。"
         "非单调因此是必然的。"),
    CALLOUT("paper", "工程含义",
            "「因果 tokenizer 会明显掉质量」在本课的设定下<strong>不成立</strong>（最多 $3.3\\%$）。"
            "而这个小代价还集中在 chunk 边界上，"
            "意味着可以用<em>重叠 chunk</em> 或<em>可变 chunk 边界</em>把它进一步摊薄。"
            "所以在「流式 / 无限长」是产品需求时，因果 tokenizer 的选择"
            "不需要用质量来论证——它的真实成本在别处："
            "<strong>不能与图像 VAE 共享权重</strong>，以及 chunk 边界处的接缝。"),
])),

("discrete", "连续 latent 还是离散 token", "".join([
    P("连续 latent 接扩散，离散 token 接自回归语言模型。"
      "这个选择的时间维版本有一个可以算清的部分：<strong>比特预算怎么花</strong>。"),
    P("设一段视频编成 $T/p_t$ 个 token、每个 token 从大小为 $K$ 的码本里取，"
      "则总比特是 $(T/p_t)\\log_2 K$。固定这个总数，"
      "「多而小的 token」与「少而大的 token」哪个好？"),
    TABLE(["比特预算", "$p_t$", "token 数", "码本 $K$", "重建相对误差", "码本利用率"],
          [["$32$", "$1$", "$16$", "$4$", "$0.84254$", "$100.0\\%$"],
           ["$32$", "$2$", "$8$", "$16$", "$0.71348$", "$100.0\\%$"],
           ["$32$", "$\\mathbf{4}$", "$\\mathbf{4}$", "$\\mathbf{256}$",
            "$\\mathbf{0.53424}$", "$99.6\\%$"],
           ["$64$", "$1$", "$16$", "$16$", "$0.70442$", "$100.0\\%$"],
           ["$64$", "$\\mathbf{2}$", "$\\mathbf{8}$", "$\\mathbf{256}$",
            "$\\mathbf{0.50506}$", "$100.0\\%$"]]),
    P("<strong>少而大的 token 明显更好</strong>：$32$ 比特下 $0.534$ vs $0.843$（$1.58\\times$），"
      "$64$ 比特下 $0.505$ vs $0.704$（$1.39\\times$）。"
      "而码本利用率一直接近 $100\\%$——在这个规模上没有出现码本坍缩。"),
    P("原因和上一节同源：<strong>更长的时间跨度让相关性可以被利用</strong>。"
      "一个覆盖 $4$ 帧的 token 可以只编码「这 $4$ 帧共同的运动」，"
      "而 $4$ 个各覆盖 $1$ 帧的 token 必须各自重复那份共同信息。"),
    CALLOUT("warn", "但这条结论有一个已知的边界",
            "码本增大到某个点会开始<strong>坍缩</strong>（大量码字从不被使用），"
            "此时「有效码本大小」远小于 $K$，上面的账就不成立了。"
            "本课的规模（$K \\leq 256$）没有触到这个边界（利用率 $\\geq 99.6\\%$），"
            "所以<strong>本节的结论只在「码本没坍缩」的前提下有效</strong>，"
            "而这个前提必须被单独测量——练习 4 就是测它。"
            "工业上应对坍缩的手段（EMA 更新、码本重启、乘积量化 / RVQ）"
            "属于 tokenizer 训练的范畴，本课不覆盖。"),
])),

("interact", "空间压缩与时间压缩不能独立选", "".join([
    P("第 1 节把三个决定说成「基本互不影响、可以分开讨论」。"
      "这在<em>代价</em>上是对的（$n = (T/p_t)(H/p_h)(W/p_w)$ 是可分的），"
      "但在<strong>收益</strong>上不对——而不对的方式有一个干净的说法。"),
    P("时间冗余能被利用的前提是<strong>相邻帧在 latent 空间里确实相似</strong>。"
      "而空间压缩率越高，latent 越抽象，"
      "同一个物体的运动在 latent 上的表现就越<em>不</em>连续："
      "一个物体在像素上移动 $2$ 个像素时 latent 几乎不变（$p_h{=}16$ 时它还在同一个 patch 里），"
      "而移动 $20$ 个像素时它跨过了 $1$ 个 latent 格子——"
      "<strong>latent 的时间相关性是「运动幅度相对 latent 网格」的函数</strong>。"),
    MATH("\\rho_{\\text{latent}} \\approx f\\!\\left(\\frac{\\text{每帧位移(像素)}}{p_h}\\right)"),
    TABLE(["每帧位移", "$p_h{=}8$ 时跨过的格子", "$p_h{=}16$ 时", "$p_h{=}32$ 时", "含义"],
          [["$1$ px", "$0.125$", "$0.06$", "$0.03$", "三种压缩率下 latent 都几乎不变"],
           ["$8$ px", "$1.0$", "$0.5$", "$0.25$", "$p_h{=}8$ 时已经换格子了"],
           ["$32$ px", "$4.0$", "$2.0$", "$1.0$", "$p_h{=}8$ 时 latent 的时间相关性已很低"]]),
    P("所以<strong>空间压缩率越低（$p_h$ 越小），时间压缩的收益越小</strong>——"
      "因为同样的物理运动在更细的 latent 网格上造成更大的 latent 变化。"
      "反过来，很高的空间压缩率会让时间维显得异常冗余，"
      "于是「大 $p_t$ 看起来很划算」，而实际上损失被藏进了空间。"),
    CALLOUT("warn", "一个可以直接检查的自洽性条件",
            "拿到一个 tokenizer 之后，<strong>在 latent 空间里量 $\\rho$</strong>"
            "（而不是在像素上量），再用第 2 节的表选 $p_t$。"
            "如果你在像素上量出 $\\rho{=}0.97$ 就去选 $p_t{=}16$，"
            "而 latent 上的 $\\rho$ 只有 $0.75$，那么 $\\rho_{\\text{eff}} = 0.75^{16} = 0.010$——"
            "时间维已经被压过头了整整两个数量级，而在像素上完全看不出来。"),
    H3("这也解释了工业配置的一个规律"),
    P("常见的视频 VAE 配置是空间 $8\\times$、时间 $4\\times$（如 $8{\\times}8{\\times}4$），"
      "而不是空间 $16\\times$、时间 $16\\times$——尽管后者的 token 数少得多。"
      "按上面的分析，$16\\times$ 空间压缩会让 latent 过于抽象、"
      "而 $16\\times$ 时间压缩会把 $\\rho_{\\text{eff}}$ 压到几乎为零。"
      "两者叠加的结果是「token 很少但每个都很难预测」——"
      "<strong>省下的算力被更难的建模问题吃掉了</strong>。"),
])),

("objective", "tokenizer 的训练目标不是下游的生成质量", "".join([
    P("本模块全部用<strong>重建误差</strong>来评价压缩方案。这是标准做法，也是本课能算的东西。"
      "但它与「下游生成模型的质量」<strong>不是同一件事</strong>，而差别的方向是可以说清的。"),
    TABLE(["目标", "偏好什么样的 latent", "为什么"],
          [["重建误差", "信息保留最多", "所有信息都被编码，包括不可预测的高频噪声"],
           ["下游生成", "<strong>可预测</strong>的信息保留最多",
            "生成模型要在 latent 上建分布；不可预测的成分只会增加建模难度"]]),
    P("两者冲突的一个具体形态：<strong>感知损失与对抗损失</strong>。"
      "纯 MSE 重建会保留大量高频噪声（它对 MSE 有贡献），"
      "于是 latent 里塞进了「噪声的具体实现」这种完全不可预测的东西。"
      "而加上感知/对抗损失后重建的 MSE <em>变差</em>，"
      "latent 却变得更适合下游生成——"
      "因为它编码的是「看起来对」而不是「逐像素对」。"),
    CALLOUT("paper", "本课不覆盖这一层，但要说清它的存在",
            "感知损失、对抗判别器、码本的训练技巧（EMA、重启、RVQ）"
            "都属于 tokenizer <em>训练</em>的范畴，需要真实数据与网络。"
            "本课能给的是<strong>信息论层面的账</strong>："
            "在给定的压缩预算下，时间维能提供多少可利用的冗余（第 2 节），"
            "以及比特该怎么在「token 数」与「码本大小」之间分（第 4 节）。"
            "这两个账是<strong>训练技巧的上界</strong>——"
            "再好的训练也不能让 $\\rho_{\\text{eff}} = 0.01$ 的时间维变出冗余来。"),
    P("还有一条实践含义：<strong>不要用重建 PSNR 来选 $p_t$</strong>。"
      "重建 PSNR 会一致地偏好小 $p_t$（信息保留更多），"
      "而下游生成质量在 $p_t$ 上有内点最优（太小则 token 太多、太大则 latent 太难预测）。"
      "本模块第 5 节的决策表里那五个量，没有一个是重建 PSNR。"),
])),

("recap", "本模块的四个量与它们的来源", "".join([
    P("在进入决策表之前，把四个量的<strong>来源</strong>并列一次——"
      "因为它们的可靠性差别很大，而这决定了该多信哪一个："),
    TABLE(["量", "来源", "可靠性"],
          [["注意力代价 $(T/p_t)^2$", "<strong>恒等式</strong>", "完全可靠（与分辨率无关）"],
           ["联合/逐帧的因子 $= T$", "<strong>恒等式</strong>", "完全可靠"],
           ["3D 压缩的收益", "在合成数据上实测", "趋势可靠；具体数值依赖数据"],
           ["有效相关性 $\\rho^{p_t}$", "一阶马尔可夫的<em>近似</em>",
            "notebook 里实测值略高于它（时间平均有平滑作用）"],
           ["流式的代价", "实测（线性编码器）", "趋势与量级可靠；真实 tokenizer 是非线性的"],
           ["比特预算的账", "实测（$k$-means VQ）", "在「码本未坍缩」的前提下可靠"]]),
    P("<strong>前两条是恒等式，可以直接用来做算力规划</strong>；"
      "后四条是在合成数据上的测量，它们给出的是<em>方向与量级</em>，不是可以照搬的数字。"
      "而本模块刻意把它们都做成了<strong>可以在你自己的数据上重跑</strong>的函数——"
      "练习 1 估 $\\rho$、练习 2 选 $p_t$、练习 3 量流式代价、练习 4 测码本坍缩。"),
])),

("bridge01", "两条恒等式，四条测量", "".join([
    P("本模块的六个量分成两类，而这个区分决定了该多信哪一个："
      "<strong>注意力代价 $(T/p_t)^2$ 与「联合/逐帧的因子 $=T$」是恒等式</strong>，"
      "可以直接用来做算力规划；"
      "而 3D 收益、有效相关性、流式代价、比特预算这四条是在合成数据上的<strong>测量</strong>，"
      "它们给出方向与量级，不是可以照搬的数字。"
      "所以本模块的四个练习刻意都做成了<em>可以在你自己的数据上重跑</em>的函数。"),
])),

("summary", "选 $p_t$ 的一张决策表", "".join([
    P("把本模块四节合起来，选时间压缩率时该看的量与它们各自的方向："),
    TABLE(["量", "怎么得到", "增大 $p_t$ 时", "约束"],
          [["注意力代价", "$(T/p_t)^2 S^2$", "<strong>下降 $\\propto 1/p_t^2$</strong>",
            "算力预算的上限"],
           ["有效相关性 $\\rho^{p_t}$", "从数据估 $\\rho$", "下降",
            "$\\rho_{\\text{eff}} < 0.3$ 后收益消失"],
           ["latent 帧数 $T/p_t$", "直接算", "下降",
            "必须 $\\geq$（最长遮挡 $+2$）$/p_t$（模块 00 练习 3）"],
           ["比特效率", "固定比特下的重建误差", "<strong>改善</strong>（$1.39$–$1.58\\times$）",
            "码本坍缩的边界"],
           ["与图像模型的兼容", "$p_t{=}1$ 才有", "<strong>失去</strong>",
            "能否继承图像 VAE 权重"]]),
    P("五个量里有<strong>两个</strong>随 $p_t$ 增大而改善（代价、比特效率）、"
      "<strong>三个</strong>变差（收益、上下文、兼容性）。"
      "所以「调 $p_t$」不是单目标优化——模块 00 的胶囊把这个拉锯做成了一个可执行的体检。"),
    P("还有一条不在表里但同样重要：<strong>这五个量里没有一个是重建 PSNR</strong>。"
      "第 6 节说明了理由——重建误差会一致地偏好小 $p_t$，"
      "而下游生成质量在 $p_t$ 上有内点最优。"
      "用重建指标选压缩率，会系统性地把 $p_t$ 选得太小，"
      "于是算力被浪费在「保留了不可预测的高频」上。"),
    CALLOUT("intuition", "一句话",
            "时间压缩率是本课唯一一个能<strong>平方级</strong>换回算力的旋钮，"
            "而它换走的是<strong>可观测性</strong>。"
            "前者容易算，后者容易忘——"
            "所以选 $p_t$ 时最常见的错误不是压得不够，而是压过了之后"
            "再也没有回头检查「模型还能不能看见需要看见的东西」。"),
])),
]

NB = [
md("""# C77 模块 01 · 视频 latent 与 tokenizer

三件事：

1. **有效相关性 $\\rho^{p_t}$** 给出选时间压缩率的上限；
2. **流式（因果）的代价非单调**，峰值在中间相关性，且集中在 chunk 的最后一帧；
3. **固定比特预算下「少而大的 token」更划算**（$1.39$–$1.58\\times$）。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import numpy as np

S_PIX, DPF = 8, 64          # 8x8 像素 = 64 维/帧

def spatial_basis(nmode=6):
    xs = np.arange(S_PIX)
    B = []
    for k in range(nmode):
        kx, ky = (k % 3) + 1, (k // 3) + 1
        B.append(np.outer(np.sin(np.pi * kx * (xs + 1) / (S_PIX + 1)),
                          np.cos(np.pi * ky * xs / S_PIX)).ravel())
    B = np.array(B)
    return B / np.linalg.norm(B, axis=1, keepdims=True)

BASIS = spatial_basis()

def make_seg(T=16, seed=0, corr=0.95, noise=0.05):
    r = np.random.default_rng(seed)
    nm = len(BASIS)
    a = np.zeros((T, nm))
    a[0] = r.normal(0, 1, nm)
    for t in range(1, T):
        a[t] = corr * a[t-1] + np.sqrt(1 - corr**2) * r.normal(0, 1, nm)
    return a @ BASIS + r.normal(0, noise, (T, DPF))

def gen(n, seed0, T=16, corr=0.95):
    return np.array([make_seg(T=T, seed=seed0+i, corr=corr) for i in range(n)])

def fit_pca(X, k):
    mu = X.mean(0, keepdims=True)
    _, _, Vt = np.linalg.svd(X - mu, full_matrices=False)
    return mu, Vt[:min(k, Vt.shape[0])]
def encode(X, mu, P):
    return (X - mu) @ P.T
def reg(Z, Y):
    return np.linalg.lstsq(np.column_stack([np.ones(len(Z)), Z]), Y, rcond=None)[0]
def apply_reg(Z, W):
    return np.column_stack([np.ones(len(Z)), Z]) @ W
def rel(Yh, Y):
    return float(np.sqrt(np.sum((Yh-Y)**2) / np.sum((Y - Y.mean(0, keepdims=True))**2)))

print('本模块只用 PCA（作为最优线性编码器）与 k-means（作为 VQ），无网络训练。')"""),

md("""## 1. 有效相关性 $\\rho^{p_t}$

如果时间结构近似一阶马尔可夫，压缩 $p_t$ 倍后相邻 latent 帧的相关性是 $\\rho^{p_t}$。"""),

code("""print('  ρ（原始）  ' + '  '.join(f'p_t={p:<5d}' for p in (1,2,4,8,16)))
for rho in (0.99, 0.95, 0.90, 0.70):
    row = [rho**p for p in (1,2,4,8,16)]
    flag = ''
    below = [p for p, v in zip((1,2,4,8,16), row) if v < 0.3]
    if below:
        flag = f'   <- p_t>={below[0]} 时 ρ_eff<0.3'
    print(f'  {rho:9.2f}  ' + '  '.join(f'{v:<10.3f}' for v in row) + flag)

# 实测：latent 帧之间的相关性确实是 rho^pt
print()
print('实测验证（把每 p_t 帧的均值当 latent 帧，量它们的相邻相关性）:')
print('   ρ      p_t    理论 ρ^p_t   实测相邻相关   差')
for rho in (0.9, 0.95):
    for pt in (1, 2, 4, 8):
        segs = gen(3000, 0, T=64, corr=rho)
        nl = 64 // pt
        lat = segs.reshape(len(segs), nl, pt, DPF).mean(2)     # (n, nl, DPF)
        # 取第一个空间模式方向上的系数序列，量其相邻相关
        c = lat @ BASIS[0]
        a = c[:, :-1].ravel(); b = c[:, 1:].ravel()
        emp = float(np.corrcoef(a, b)[0,1])
        print(f'  {rho:.2f}   {pt:3d}    {rho**pt:10.4f}   {emp:12.4f}   {abs(rho**pt-emp):.4f}')
    print()
print('-> 时间平均会让实测值略高于 ρ^p_t（平均本身有平滑作用），')
print('   但趋势与量级一致，足以用来选 p_t 的上限。')"""),

md("""## 2. 流式（因果）的代价

总预算完全相同，差别只在解码第 $t$ 帧时能用哪些 latent。"""),

code("""def causal_cost(T=16, s=4, k=8, corr=0.95, ntr=2500, nte=800, seed0=0):
    '''返回 (非因果逐帧误差, 因果逐帧误差)。总预算 = (T/s)*k，两者相同。'''
    TR, TE = gen(ntr, seed0, T=T, corr=corr), gen(nte, 900_000 + seed0, T=T, corr=corr)
    nch = T // s
    Ztr, Zte = [], []
    for j in range(nch):
        btr = TR[:, j*s:(j+1)*s, :].reshape(len(TR), -1)
        bte = TE[:, j*s:(j+1)*s, :].reshape(len(TE), -1)
        mu, P = fit_pca(btr, k)
        Ztr.append(encode(btr, mu, P)); Zte.append(encode(bte, mu, P))
    Ztr, Zte = np.concatenate(Ztr, 1), np.concatenate(Zte, 1)
    en, ec = [], []
    for t in range(T):
        Ytr, Yte = TR[:, t, :], TE[:, t, :]
        W = reg(Ztr, Ytr)
        en.append(rel(apply_reg(Zte, W), Yte))
        m = (t // s + 1) * k                       # 因果：只到 t//s 这个 chunk
        Wc = reg(Ztr[:, :m], Ytr)
        ec.append(rel(apply_reg(Zte[:, :m], Wc), Yte))
    return np.array(en), np.array(ec)

print('  s    k   总预算   非因果均值   因果均值   流式的代价')
for s, k in [(2,8), (4,16), (4,8), (8,16)]:
    en, ec = causal_cost(s=s, k=k)
    print(f'  {s:2d}  {k:3d}   {16//s*k:6d}   {en.mean():.5f}     {ec.mean():.5f}    '
          f'{ec.mean()/en.mean():.3f}x')
    assert ec.mean() >= en.mean() - 1e-9, '因果不可能优于非因果（信息更少）'
    assert ec.mean()/en.mean() < 1.05, f'代价应 <5%，得到 {ec.mean()/en.mean():.3f}'

print()
print('逐帧的代价分布（s=4, k=8）:')
en, ec = causal_cost(s=4, k=8)
ratios = ec / en
for j in range(4):
    seg = ratios[j*4:(j+1)*4]
    mark = '  <- 最后一个 chunk：因果与非因果等价' if j == 3 else ''
    print(f'  chunk {j}: ' + ' '.join(f'{v:.2f}' for v in seg) +
          f'   （峰值在第 {int(np.argmax(seg))} 帧）{mark}')

# 峰值在每个 chunk 的最后一帧
for j in range(3):
    seg = ratios[j*4:(j+1)*4]
    assert int(np.argmax(seg)) == 3, f'chunk {j} 的峰值应在最后一帧，得到 {np.argmax(seg)}'
# 最后一个 chunk 全为 1.00
assert np.allclose(ratios[12:], 1.0, atol=1e-6), '最后一个 chunk 应恒为 1.00'
print()
print('✅ 峰值落在每个 chunk 的**最后**一帧（那里最需要紧邻的未来）')
print('✅ 最后一个 chunk 恒为 1.00 —— 那里因果与非因果等价')"""),

code("""# 代价对相关性是**非单调**的
print('代价 vs 时间相关性（s=4, k=8）:')
print('   corr    非因果误差   因果误差   流式的代价   解读')
costs = {}
for corr in (0.0, 0.3, 0.6, 0.8, 0.95, 0.995):
    en, ec = causal_cost(s=4, k=8, corr=corr)
    costs[corr] = ec.mean() / en.mean()
    note = '未来无信息' if corr < 0.1 else ('未来与过去高度冗余' if corr > 0.99 else '')
    print(f'  {corr:.3f}   {en.mean():.5f}    {ec.mean():.5f}   {costs[corr]:.4f}x     {note}')

_peak = max(costs, key=costs.get)
assert costs[0.0] < 1.005, f'corr=0 时代价应 ~1.00，得到 {costs[0.0]:.4f}'
assert costs[0.995] < costs[_peak], 'corr→1 时代价应回落'
assert _peak in (0.8, 0.95), f'峰值应在中间相关性，得到 {_peak}'
print()
print(f'✅ 峰值在 corr={_peak}（代价 {costs[_peak]:.4f}x），两端都回到 ~1.00')
print()
print('   两端都便宜的原因：corr=0 时未来什么也不提供；')
print('   corr→1 时未来与过去几乎是同一件事，看过去就等于看了未来。')
print('   只有中间 —— 未来带着过去没有的信息、而那信息确实有用 —— 才真的要付钱。')
print()
print('   工程含义：「因果 tokenizer 会明显掉质量」在本设定下不成立（最多 3.3%）。')
print('   它的真实成本在别处：**不能与图像 VAE 共享权重**，以及 chunk 边界的接缝。')"""),

md("""## 3. 固定比特预算：多而小 vs 少而大的 token

总比特 $= (T/p_t)\\log_2 K$。固定它，比较不同的 $(p_t, K)$ 组合。"""),

code("""def assign(X, C, chunk=4096):
    '''最近码字分配。用 ||x-c||² = ||x||² − 2x·c + ||c||² 走 matmul，
    避免建 (chunk, K, dim) 的中间数组（那个在 K 大时会到几十 GB）。'''
    cn = (C * C).sum(1)
    lab = np.empty(len(X), dtype=np.int64)
    for i in range(0, len(X), chunk):
        blk = X[i:i+chunk]
        d = cn[None, :] - 2.0 * (blk @ C.T)          # 省掉与 k 无关的 ||x||²
        lab[i:i+chunk] = np.argmin(d, 1)
    return lab

def kmeans(X, K, iters=30, seed=0):
    r = np.random.default_rng(seed)
    C = X[r.choice(len(X), K, replace=False)].copy()
    for _ in range(iters):
        lab = assign(X, C)
        cnt = np.bincount(lab, minlength=K)
        Cn = np.zeros_like(C)
        np.add.at(Cn, lab, X)
        nz = cnt > 0
        C[nz] = Cn[nz] / cnt[nz][:, None]
    return C

def vq_eval(Xtr, Xte, K, seed=0):
    '''返回 (重建相对误差, 码本利用率)。'''
    C = kmeans(Xtr, K, seed=seed)
    lab = assign(Xte, C)
    R = Xte - C[lab]
    err = float(np.sqrt(np.sum(R**2) / np.sum((Xte - Xte.mean(0))**2)))
    return err, len(np.unique(lab)) / K

T = 16
TR, TE = gen(4000, 0, T=T), gen(1000, 20_000, T=T)
print(f'一段视频 T={T} 帧 x {DPF} 维。总比特 = (T/p_t) * log2(K)')
print()
print('  比特预算   p_t   token 数   码本 K    重建相对误差   码本利用率')
best = {}
for bits in (32, 64):
    for pt in (1, 2, 4, 8):
        ntok = T // pt
        lg = bits / ntok
        if not (1 <= lg <= 10):
            continue
        K = int(round(2**lg))
        Xtr = TR.reshape(len(TR), ntok, pt*DPF).reshape(-1, pt*DPF)
        Xte = TE.reshape(len(TE), ntok, pt*DPF).reshape(-1, pt*DPF)
        if len(Xtr) < K:
            continue
        e, util = vq_eval(Xtr, Xte, K, seed=1)
        best.setdefault(bits, {})[pt] = (e, util, ntok, K)
        print(f'  {bits:8d}   {pt:3d}   {ntok:8d}   {K:6d}    {e:.5f}        {util*100:5.1f}%')
    print()

for bits in (32, 64):
    d = best[bits]
    pts = sorted(d)
    e_small, e_large = d[pts[0]][0], d[pts[-1]][0]
    assert e_large < e_small, f'{bits} 比特：少而大的 token 应更好'
    print(f'✅ {bits} 比特: p_t={pts[0]}（{d[pts[0]][2]} tok x {d[pts[0]][3]} 码本）'
          f'误差 {e_small:.5f}  vs  p_t={pts[-1]}（{d[pts[-1]][2]} tok x {d[pts[-1]][3]} 码本）'
          f'误差 {e_large:.5f}  ->  好 {e_small/e_large:.2f}x')
    assert all(v[1] > 0.99 for v in d.values()), '本规模下码本不该坍缩'
print()
print('✅ 全部配置的码本利用率 > 99% —— 本规模没有触到坍缩边界')
print()
print('-> 原因与第 1、2 节同源：**更长的时间跨度让相关性可以被利用**。')
print('   一个覆盖 4 帧的 token 只需编码「这 4 帧共同的运动」，')
print('   而 4 个各覆盖 1 帧的 token 必须各自重复那份共同信息。')"""),

md("""## ✏️ 练习 1：从数据估相邻帧相关性

实现 `estimate_rho(segs)`：给定一批视频段 `(n, T, D)`，
返回相邻帧相关性的**鲁棒估计**（用中位数而不是均值，
因为镜头边界会产生极端值）。

提示：对每段视频，算相邻帧向量的相关系数；然后对所有 (段, 位置) 取中位数。"""),

code("""def estimate_rho(segs):
    '''相邻帧相关性的鲁棒估计。

    参数
    ----
    segs : (n, T, D) 视频批

    返回
    ----
    float : 全部 (段, 相邻位置) 的相关系数的中位数
    '''
    # TODO: 对每个 (i, t) 算 corr(segs[i,t], segs[i,t+1])（长度为 D 的两个向量），
    #       返回全部值的中位数。注意跳过方差为 0 的退化情形。
    raise NotImplementedError"""),

code("""# 自测
print('   真 corr    估计的 ρ     误差')
for _c in (0.0, 0.3, 0.6, 0.9, 0.99):
    _segs = gen(400, 0, T=16, corr=_c)
    _rho = estimate_rho(_segs)
    print(f'  {_c:8.2f}   {_rho:9.4f}    {abs(_rho-_c):.4f}')
    assert abs(_rho - _c) < 0.15, f'真 corr={_c} 时估计 {_rho:.4f} 偏差过大'

# 鲁棒性：混入 20% 的「镜头切换」段（相邻帧完全无关）
print()
print('  鲁棒性检验：在 corr=0.9 的数据里混入 20% 的镜头切换段')
_good = gen(320, 0, T=16, corr=0.9)
_cut = gen(80, 500_000, T=16, corr=0.0)
_mixed = np.concatenate([_good, _cut], 0)
_rho_mixed = estimate_rho(_mixed)
_mean_based = float(np.mean([np.corrcoef(_mixed[i,t], _mixed[i,t+1])[0,1]
                             for i in range(len(_mixed)) for t in range(15)]))
print(f'    中位数估计 = {_rho_mixed:.4f}   （纯净数据是 {estimate_rho(_good):.4f}）')
print(f'    均值估计   = {_mean_based:.4f}   <- 被 20% 的切换段拉低了')
assert _rho_mixed > _mean_based + 0.05, '中位数应比均值更鲁棒'
assert abs(_rho_mixed - 0.9) < 0.12, '中位数应仍接近 0.9'

print()
print(f'✅ 中位数估计在 20% 污染下仍是 {_rho_mixed:.3f}，而均值被拉到 {_mean_based:.3f}')
print()
print('   工程含义：ρ 应该按**镜头**估而不是按数据集估。')
print('   混合估计会同时对慢镜头压得不够、对快剪辑压过头 ——')
print('   而中位数至少能告诉你「典型镜头」的 ρ 是多少。')"""),

md("""## ✏️ 练习 2：$p_t$ 的上限

实现 `max_pt(rho, T, rho_eff_min=0.3, max_occl=0, min_latent=None)`，
返回同时满足下面两个约束的最大时间压缩率：

- **收益约束**：$\\rho^{p_t} \\geq \\rho_{\\text{eff,min}}$；
- **上下文约束**：latent 帧数要够「跨过遮挡 + 再留 2 帧给位置和速度」，
  即 $T/p_t \\geq \\lceil \\text{max\\_occl}/p_t \\rceil + 2$。
  化简后就是 $p_t \\lesssim (T - \\text{max\\_occl})/2$——
  **可见跨度必须容得下至少 2 个 latent 帧**。"""),

code("""def max_pt(rho, T, rho_eff_min=0.3, max_occl=0, min_latent=None,
           candidates=(1,2,4,8,16,32)):
    '''同时满足收益与上下文约束的最大 p_t。

    参数
    ----
    rho          : 原始相邻帧相关性
    T            : 帧数
    rho_eff_min  : 有效相关性的下限（低于它时时间压缩已无收益）
    max_occl     : 场景中最长的不可观测区间（原始帧）
    min_latent   : latent 帧数的硬下限（可选）
    candidates   : 候选 p_t

    返回
    ----
    (best_pt, reason) : 最大可行的 p_t，以及它被哪个约束卡住（'gain'/'context'/'none'）
    '''
    # TODO: 遍历 candidates（升序），对每个 pt 检查
    #       ① rho**pt >= rho_eff_min
    #       ② T//pt >= ceil(max_occl/pt) + 2，且 >= (min_latent or 1)
    #       返回最大可行的 pt，以及下一个候选被哪个条件卡住
    raise NotImplementedError"""),

code("""# 自测
print('    ρ     T    最长遮挡   最大 p_t   卡在哪个约束')
_cases = [
    (0.99, 128, 0,  None),
    (0.95, 128, 0,  None),
    (0.90, 128, 0,  None),
    (0.70, 128, 0,  None),
    (0.99, 128, 24, None),
    (0.99, 32,  24, None),
    (0.99, 16,  24, None),
]
for _rho, _T, _occ, _ml in _cases:
    _pt, _why = max_pt(_rho, _T, max_occl=_occ, min_latent=_ml)
    print(f'  {_rho:.2f}  {_T:4d}   {_occ:8d}   {_pt:8d}   {_why}')

# ρ 越小，允许的 p_t 越小
_seq = [max_pt(r, 128)[0] for r in (0.99, 0.95, 0.90, 0.70)]
for _i in range(1, len(_seq)):
    assert _seq[_i] <= _seq[_i-1], f'ρ 越小 p_t 上限应越小：{_seq}'
assert max_pt(0.70, 128)[0] <= 4, 'ρ=0.70 时 p_t 上限应 <=4'
assert max_pt(0.99, 128)[0] >= 16, 'ρ=0.99 时 p_t 上限应 >=16'

# 短视频 + 长遮挡时被上下文卡住
_pt_s, _why_s = max_pt(0.99, 16, max_occl=24)
assert _why_s == 'context', f'T=16 + 遮挡 24 应被上下文卡住，得到 {_why_s}'
_pt_l, _why_l = max_pt(0.70, 128)
assert _why_l == 'gain', f'ρ=0.70 应被收益卡住，得到 {_why_l}'

print()
print(f'✅ ρ=0.99, T=128, 无遮挡: p_t 上限 {max_pt(0.99,128)[0]}（被收益约束卡住）')
print(f'✅ ρ=0.99, T=16, 遮挡 24 帧: p_t 上限 {_pt_s}（被**上下文**约束卡住）')
print(f'✅ ρ=0.70, T=128: p_t 上限 {_pt_l}（被收益约束卡住）')
print()
print('   两个约束会在不同场景下轮流成为瓶颈 ——')
print('   所以「业界都用 p_t=4」这种全局答案在两端都是错的。')"""),

md("""## ✏️ 练习 3：因果代价的峰值位置

实现 `causal_peak_frames(T, s, k, corr)`：返回因果/非因果误差比
在每个 chunk 内取最大值的**帧偏移**（相对 chunk 起点）。

正文说峰值在每个 chunk 的最后一帧。用这个函数在多个 $s$ 上验证。"""),

code("""def causal_peak_frames(T=16, s=4, k=8, corr=0.95):
    '''每个 chunk 内因果代价最大的帧偏移。

    参数
    ----
    T, s, k, corr : 传给 causal_cost

    返回
    ----
    (offsets, ratios) :
      offsets = 每个 chunk 内 argmax(ratio) 的**帧内偏移**（0..s-1）；
                最后一个 chunk 因果与非因果等价，用 -1 表示
      ratios  = 完整的逐帧比值数组
    '''
    en, ec = causal_cost(T=T, s=s, k=k, corr=corr)
    ratios = ec / en
    # TODO: 把 ratios 切成 T//s 个 chunk；
    #       对每个 chunk 求 argmax 的帧内偏移；
    #       若该 chunk 的比值全都 ≈1.0（容差 1e-6），记 -1
    raise NotImplementedError"""),

code("""# 自测
print('  (a) s >= 4：峰值稳定落在每个 chunk 的最后一帧')
print('    T   s   每个 chunk 内峰值的帧内偏移（-1 = 该 chunk 无代价）')
for _T, _s in [(16, 4), (16, 8), (24, 4), (24, 6)]:
    _off, _rat = causal_peak_frames(T=_T, s=_s)
    print(f'  {_T:4d}  {_s:2d}   {_off}')
    assert _off[-1] == -1, f'T={_T}, s={_s}: 最后一个 chunk 应无代价，得到 {_off[-1]}'
    for _j, _o in enumerate(_off[:-1]):
        assert _o == _s - 1, \\
            f'T={_T}, s={_s}, chunk {_j}: 峰值应在偏移 {_s-1}，得到 {_o}'

print()
print('  (b) s = 2：chunk 内只有两帧，两者统计上无法区分')
_off2, _rat2 = causal_peak_frames(T=16, s=2)
_spread = []
for _j in range(7):                      # 跳过最后一个 chunk
    _seg = _rat2[_j*2:(_j+1)*2]
    _spread.append(float(abs(_seg[1] - _seg[0])))
print(f'    chunk 内两帧的比值之差: ' + ' '.join(f'{v:.2e}' for v in _spread))
print(f'    最大差 {max(_spread):.2e}  <-  远小于代价本身（~2%）')
assert max(_spread) < 5e-3, f's=2 时 chunk 内差应可忽略，得到 {max(_spread):.2e}'
print(f'    argmax 因此是噪声: {_off2[:7]}')

print()
print('  (c) 峰值的**显著性**（峰值 vs chunk 内最小值）:')
print('    s    峰值比值   chunk 内最小   峰/谷')
for _s in (4, 6, 8):
    _T = 24 if _s == 6 else 16
    _off, _rat = causal_peak_frames(T=_T, s=_s)
    _seg = _rat[:_s]
    print(f'   {_s:3d}    {_seg.max():.4f}    {_seg.min():.4f}      {_seg.max()/_seg.min():.4f}')
    assert _seg.max() / _seg.min() > 1.03, f's={_s} 时峰谷比应 >1.03'

print()
print('✅ s >= 4 时峰值稳定在每个 chunk 的**最后一帧**（偏移 s-1），峰谷比 > 1.03')
print('✅ s = 2 时 chunk 内差 < 5e-3 —— 结论的成立范围是 s >= 3')
print('✅ 最后一个 chunk 恒无代价（因果与非因果等价）')
print()
print('   工程含义：代价既小又**集中在 chunk 末尾**，所以可以用重叠 chunk 或')
print('   把 chunk 边界对齐到镜头切换来进一步摊薄 —— 而不需要放弃因果性。')
print('   而 s=2 那一行说明这个优化在很小的 chunk 上没有意义（本来就摊平了）。')"""),

md("""## ✏️ 练习 4：码本什么时候开始坍缩

正文说「少而大的 token 更划算」有一个前提：码本没坍缩。
实现 `codebook_collapse(pt, Ks, ntr)`：返回每个码本大小下的
**利用率**与**有效码本大小**（$2^{H}$，$H$ 为码字使用分布的熵，单位 bit）。

有效码本大小比利用率更有信息：利用率 100% 但分布极度不均时，
有效大小仍然远小于 $K$。"""),

code("""def codebook_collapse(pt=4, Ks=(16, 64, 256, 1024), ntr=4000, nte=1000, T=16):
    '''每个码本大小下的利用率与有效码本大小。

    返回
    ----
    dict : K -> {'err', 'util', 'eff_K', 'entropy_bits'}
      util         = 被用到的码字比例
      entropy_bits = 码字使用分布的熵（bit）
      eff_K        = 2^entropy_bits（「有效码本大小」）
    '''
    tr, te = gen(ntr, 0, T=T), gen(nte, 20_000, T=T)
    ntok = T // pt
    Xtr = tr.reshape(len(tr), ntok, pt*DPF).reshape(-1, pt*DPF)
    Xte = te.reshape(len(te), ntok, pt*DPF).reshape(-1, pt*DPF)
    out = {}
    # TODO: 对每个 K：用 kmeans(Xtr, K, seed=1) 得码本；
    #       在 Xte 上分配码字（分块 argmin）；
    #       算 err（相对重建误差）、util、熵（用码字频率，跳过 0 频）、eff_K = 2^熵
    raise NotImplementedError"""),

code("""# 自测
_res = codebook_collapse(pt=4, Ks=(16, 64, 256, 1024))
print('     K      重建误差   利用率    熵(bit)   有效码本 2^H   有效/K')
for _K in sorted(_res):
    _r = _res[_K]
    print(f'  {_K:6d}    {_r["err"]:.5f}   {_r["util"]*100:5.1f}%   '
          f'{_r["entropy_bits"]:6.2f}    {_r["eff_K"]:11.1f}   {_r["eff_K"]/_K:.3f}')

# 误差随 K 单调下降
_errs = [_res[K]['err'] for K in sorted(_res)]
for _i in range(1, len(_errs)):
    assert _errs[_i] < _errs[_i-1], f'误差应随 K 单调下降：{[round(e,5) for e in _errs]}'
# 有效/K 随 K 增大而下降（坍缩的定量形式）
_ratio = [_res[K]['eff_K']/K for K in sorted(_res)]
assert _ratio[-1] < _ratio[0], f'有效/K 应随 K 下降：{[round(r,3) for r in _ratio]}'
# 熵的增长慢于 log2(K)
_Ks = sorted(_res)
_H = [_res[K]['entropy_bits'] for K in _Ks]
_lg = [np.log2(K) for K in _Ks]
print()
print('  熵的增长 vs log2(K):')
for _K, _h, _l in zip(_Ks, _H, _lg):
    print(f'    K={_K:5d}: 熵 {_h:5.2f} bit   log2(K) = {_l:5.2f}   比值 {_h/_l:.3f}')
assert _H[-1]/_lg[-1] < _H[0]/_lg[0], '熵/log2(K) 应随 K 下降'

print()
print(f'✅ 误差随 K 单调下降（{_errs[0]:.5f} -> {_errs[-1]:.5f}）')
print(f'✅ 而**有效码本 / K** 从 {_ratio[0]:.3f} 降到 {_ratio[-1]:.3f} —— 这就是坍缩的定量形式')
print()
print('   注意利用率与有效大小的区别：利用率可以接近 100% 而分布极度不均，')
print(f'   此时有效码本远小于 K（本例 K={_Ks[-1]} 时有效只有 {_res[_Ks[-1]]["eff_K"]:.0f}）。')
print('   -> 所以「少而大的 token 更划算」这条结论必须带上「熵在增长」这个前提，')
print('      而检验它要看熵 / log2(K) 而不是利用率。')"""),

md("""## 📖 参考答案"""),

code("""def estimate_rho(segs):
    '''相邻帧相关性的鲁棒估计（中位数）。'''
    vals = []
    n, T, D = segs.shape
    for i in range(n):
        for t in range(T - 1):
            a, b = segs[i, t], segs[i, t+1]
            sa, sb = a.std(), b.std()
            if sa < 1e-12 or sb < 1e-12:
                continue
            vals.append(float(np.corrcoef(a, b)[0, 1]))
    return float(np.median(vals))

def max_pt(rho, T, rho_eff_min=0.3, max_occl=0, min_latent=None,
           candidates=(1,2,4,8,16,32)):
    '''同时满足收益与上下文约束的最大 p_t。'''
    ok, why = 1, 'none'
    for pt in sorted(candidates):
        gain_ok = (rho ** pt) >= rho_eff_min
        need = max(int(np.ceil(max_occl / pt)) + 2, min_latent or 1)
        ctx_ok = (T // pt) >= need
        if gain_ok and ctx_ok:
            ok = pt
        else:
            why = 'gain' if not gain_ok else 'context'
            break
    return ok, why

def causal_peak_frames(T=16, s=4, k=8, corr=0.95):
    '''每个 chunk 内因果代价最大的帧偏移。'''
    en, ec = causal_cost(T=T, s=s, k=k, corr=corr)
    ratios = ec / en
    offs = []
    for j in range(T // s):
        seg = ratios[j*s:(j+1)*s]
        offs.append(-1 if np.allclose(seg, 1.0, atol=1e-6) else int(np.argmax(seg)))
    return offs, ratios

def codebook_collapse(pt=4, Ks=(16, 64, 256, 1024), ntr=4000, nte=1000, T=16):
    '''每个码本大小下的利用率与有效码本大小。'''
    tr, te = gen(ntr, 0, T=T), gen(nte, 20_000, T=T)
    ntok = T // pt
    Xtr = tr.reshape(len(tr), ntok, pt*DPF).reshape(-1, pt*DPF)
    Xte = te.reshape(len(te), ntok, pt*DPF).reshape(-1, pt*DPF)
    out = {}
    for K in Ks:
        if len(Xtr) < K:
            continue
        C = kmeans(Xtr, K, seed=1)
        lab = assign(Xte, C)
        R = Xte - C[lab]
        err = float(np.sqrt(np.sum(R**2) / np.sum((Xte - Xte.mean(0))**2)))
        cnt = np.bincount(lab, minlength=K).astype(float)
        p = cnt[cnt > 0] / cnt.sum()
        H = float(-np.sum(p * np.log2(p)))
        out[K] = {'err': err, 'util': float((cnt > 0).mean()),
                  'entropy_bits': H, 'eff_K': float(2.0**H)}
    return out

print('参考答案已定义。')
print()
print('要点：')
print('  1. ρ 要按**镜头**估、用**中位数** —— 混合估计在两端都错。')
print('  2. p_t 的上限由收益（ρ^p_t >= 0.3）与上下文（覆盖最长遮挡）**轮流**决定。')
print('  3. 因果代价既小（<=3.3%）又集中在 chunk 边界 —— 可以用重叠 chunk 摊薄。')
print('  4. 判断码本有没有坍缩要看**熵 / log2(K)**，不能看利用率。')"""),

md("""## 🧪 真实工程胶囊：一个 tokenizer 配置的验收清单

下面这段代码把本模块的四个量做成一次验收：给定一批素材，
它估出 $\\rho$、给出 $p_t$ 的上限、量出因果代价、并检查码本的熵是否还在增长。

关键设计：**每一项都从数据算出来，没有一个是拍的**。
而输出不是「推荐配置」而是**一组上下界**，
因为这四项里有两项随 $p_t$ 改善、两项变差（见正文第 5 节的决策表）。"""),

code("""def tokenizer_acceptance(segs, T, max_occl, bit_budget=None, pt_candidates=(1,2,4,8,16)):
    '''tokenizer 配置的验收清单。全部量都从 segs 估出。'''
    print('=' * 74)
    # ① 从数据估 ρ
    rho = estimate_rho(segs[:min(300, len(segs))])
    print(f'① 相邻帧相关性 ρ（中位数估计）= {rho:.4f}')

    # ② p_t 的上限
    pt_gain, why = max_pt(rho, T, max_occl=max_occl, candidates=pt_candidates)
    print(f'② p_t 上限 = {pt_gain}（被 {why} 约束卡住）')
    print(f'   逐档的有效相关性 ρ^p_t:')
    for pt in pt_candidates:
        need = int(np.ceil(max_occl / pt)) + 2
        have = T // pt
        ok = '✓' if (rho**pt >= 0.3 and have >= need) else '✗'
        print(f'     p_t={pt:3d}: ρ_eff={rho**pt:.4f}, latent 帧 {have} (需 >= {need})  {ok}')

    # ③ 因果代价（在选定的 p_t 上量）
    s = max(pt_gain, 2)
    en, ec = causal_cost(T=T if T <= 24 else 16, s=min(s, 8), k=8, corr=float(rho))
    cost = ec.mean() / en.mean()
    print(f'③ 流式（因果）代价 = {cost:.4f}x（s={min(s,8)}）')
    if cost > 1.10:
        print(f'   ⚠️  代价 > 10%：这个相关性区间对因果性最敏感')
    else:
        print(f'   ✓ 代价 <= 10%：因果性不需要用质量来论证')

    # ④ 码本的熵是否还在增长
    if bit_budget is not None:
        print(f'④ 固定 {bit_budget} 比特的配置对比:')
        rows = []
        for pt in pt_candidates:
            ntok = (T if T <= 16 else 16) // pt
            if ntok < 1:
                continue
            lg = bit_budget / ntok
            if not (1 <= lg <= 10):
                continue
            K = int(round(2**lg))
            r = codebook_collapse(pt=pt, Ks=(K,), ntr=1500, nte=400,
                                  T=(T if T <= 16 else 16))
            if K not in r:
                continue
            e = r[K]
            rows.append((pt, ntok, K, e['err'], e['entropy_bits']/np.log2(K)))
            print(f'     p_t={pt:3d}: {ntok:2d} tok x {K:5d} 码本 -> 误差 {e["err"]:.5f}, '
                  f'熵/log2(K) = {e["entropy_bits"]/np.log2(K):.3f}')
        if rows:
            best = min(rows, key=lambda x: x[3])
            print(f'   -> 该比特预算下最优是 p_t={best[0]}（误差 {best[3]:.5f}）')
            if best[4] < 0.7:
                print(f'   ⚠️  它的熵/log2(K) = {best[4]:.3f} < 0.7：码本已开始坍缩，'
                      f'「少而大更划算」这条结论在这里不再可靠')
    print('=' * 74)
    print()
    return dict(rho=rho, pt_max=pt_gain, bottleneck=why, causal_cost=float(cost))

print('=== 素材 A：慢镜头（ρ 高），长视频，无长遮挡 ===')
_A = tokenizer_acceptance(gen(400, 0, T=16, corr=0.97), T=128, max_occl=4, bit_budget=64)
assert _A['pt_max'] >= 8, 'ρ 高、无长遮挡时 p_t 上限应较大'

print('=== 素材 B：快剪辑（ρ 低）===')
_B = tokenizer_acceptance(gen(400, 0, T=16, corr=0.45), T=128, max_occl=4, bit_budget=64)
assert _B['pt_max'] < _A['pt_max'], 'ρ 低时 p_t 上限应更小'
assert _B['bottleneck'] == 'gain', 'ρ 低时应被收益约束卡住'

print('=== 素材 C：ρ 高但视频短、遮挡长 ===')
_C = tokenizer_acceptance(gen(400, 0, T=16, corr=0.97), T=16, max_occl=10, bit_budget=32)
assert _C['bottleneck'] == 'context', '短视频 + 长遮挡应被上下文约束卡住'

print('工程含义：')
print(f'  · 三份素材的 p_t 上限分别是 {_A["pt_max"]} / {_B["pt_max"]} / {_C["pt_max"]}，')
print(f'    而被卡住的约束分别是 {_A["bottleneck"]} / {_B["bottleneck"]} / {_C["bottleneck"]} ——')
print('    三种情形需要三种不同的应对，用一个全局 p_t 会在至少两处出错。')
print('  · 这份清单的输出是**上下界**而不是推荐值。')
print('    因为四项里两项随 p_t 改善（算力、比特效率）、两项变差（收益、上下文），')
print('    最终取哪个值是产品决策（要不要流式？要不要继承图像权重？），不是本清单能定的。')""")
,]
