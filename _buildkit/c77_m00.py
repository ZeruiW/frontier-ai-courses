# -*- coding: utf-8 -*-
"""C77 模块 00 · 课程总览：时间轴把什么改变了。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C28（前沿扩散）是硬前提</strong>——"
                 "latent diffusion、DiT 架构（patchify / adaLN-zero / 时间步嵌入）、"
                 "flow matching、CFG、一致性模型本课<em>一概不重讲</em>，只把它们推广到时间轴；"
                 "<strong>C41 模块 04</strong>（基于模型 RL：MPC / Dyna / 规划侧的复合误差）"
                 "是模块 04 的对照，本课只做<em>生成侧</em>；线性代数（Kronecker 积、SVD）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（<strong>时间轴的代价是平方的</strong>：$T{=}128$ 时注意力代价是单帧的 $1024$ 倍，'
                       '而「联合 vs 逐帧」的额外因子恰好是 $T$ / '
                       '<strong>3D 压缩的收益是时间相关性的函数</strong>：'
                       'corr$=0$ 时 $1.00\\times$（甚至 $0.984$），corr$=0.99$ 时 $4.49\\times$ / '
                       '<strong>遮挡悬崖</strong>：历史 $h{=}6$ 时误差 $1.003$，$h{=}7$ 塌到 $0.310$ / '
                       '<strong>逐帧特征算的 FVD 对帧序完全免疫</strong>（$7.1\\times10^{-15}$））'),
    ("核心参考", "Ho et al., <em>Video Diffusion Models</em>（NeurIPS 2022）· "
                 "Blattmann et al., <em>Align your Latents / Stable Video Diffusion</em>"
                 "（CVPR 2023 / 2023）· "
                 "OpenAI, <em>Video generation models as world simulators</em>（Sora 技术报告, 2024）· "
                 "Yu et al., <em>MAGVIT-v2</em>（ICLR 2024，视频 tokenizer）· "
                 "Ha &amp; Schmidhuber, <em>World Models</em>（NeurIPS 2018）· "
                 "Unterthiner et al., <em>FVD: A new Metric for Video Generation</em>（2018/2019）· "
                 "本课程 <strong>C28</strong>（图像扩散的全部地基）· <strong>C41 模块 04</strong>（规划侧）"),
    ("预计时长", "读 40 分钟 + 跑 35 分钟"),
]

SECTIONS = [

("frame", "视频不是「图像 × T」", "".join([
    P("把图像生成推广到视频，最省事的想法是「同一套模型跑 $T$ 次」。"
      "这个想法在<em>某些</em>意义上可行——但它错过的东西恰好是本课的全部内容。"),
    P("先看代价。设每帧被切成 $S$ 个 token（$256\\times256$、patch $16\\times16$ 时 $S{=}256$），"
      "时间维按 $p_t$ 压缩，则 token 总数 $n = (T/p_t)\\cdot S$，"
      "而注意力代价 $\\propto n^2$："),
    TABLE(["$T$", "$p_t$", "token 数 $n$", "$n^2$", "相对单帧的注意力代价"],
          [["$1$", "$1$", "$256$", "$65{,}536$", "$1.0\\times$"],
           ["$16$", "$4$", "$1{,}024$", "$1{,}048{,}576$", "$16.0\\times$"],
           ["$64$", "$4$", "$4{,}096$", "$16{,}777{,}216$", "$256.0\\times$"],
           ["$128$", "$4$", "$8{,}192$", "$67{,}108{,}864$", "$\\mathbf{1024.0\\times}$"],
           ["$256$", "$4$", "$16{,}384$", "$268{,}435{,}456$", "$4096.0\\times$"]]),
    P("$T$ 翻倍代价变 <strong>4 倍</strong>，不是 2 倍。"
      "而「联合建模」相对「逐帧独立」的额外因子有一个干净的闭式："),
    MATH("\\frac{(T\\cdot S)^2}{T \\cdot S^2} = T"),
    P("notebook 逐个验证这个比值（$T{=}8$ 时 $8\\times$，$T{=}128$ 时 $128\\times$）。"
      "所以「把时间维也放进注意力」在代价上不是一个小改动，而是乘了一个 $T$。"),
    CALLOUT("intuition", "本课与 C28 的分工",
            "C28 已经把图像扩散的五块地基讲完了："
            "latent diffusion、DiT 架构、flow matching、CFG、一致性模型。"
            "C28 里每一处提到「视频」的地方都是<strong>指向前方的一句带过</strong>——"
            "「SoRA 把 DiT 的 patch 推广成时空 patch」、"
            "「时空一致的 VAE 远比图像难，高质量视频 VAE 仍是瓶颈」、"
            "「把一致性模型扩到视频 DiT 是实时视频生成的关键一步」。"
            "<strong>本课就是那些「一句带过」的展开</strong>，"
            "而 C28 的五块地基本课一概不重讲。"),
])),

("gain", "时间维的收益：不是「视频的性质」，是相关性的函数", "".join([
    P("代价是明确的，那收益呢？直觉是「视频冗余大，所以联合压缩更划算」。"
      "notebook 把这句话做成一个可测量的命题："
      "在<strong>完全相同的系数预算</strong>下，比较"),
    UL(["<strong>逐帧 2D</strong>：每帧保留 $k_s$ 个空间主成分，总系数 $T k_s$；",
        "<strong>联合 3D</strong>：把整段当一个 $T \\times S$ 张量，保留 $k_j = T k_s$ 个时空主成分。"]),
    P("训练/测试分离，数据是「$6$ 个空间模式各自做 AR(1) 演化」的合成视频。"
      "把时间相关性 corr 从 $0$ 扫到 $0.99$："),
    TABLE(["corr", "预算 $16$", "预算 $32$", "预算 $64$", "结论"],
          [["$0.00$", "$1.001\\times$", "$1.000\\times$", "$\\mathbf{0.984\\times}$",
            "3D <strong>不如</strong> 2D"],
           ["$0.50$", "$1.170\\times$", "$1.291\\times$", "$1.378\\times$", ""],
           ["$0.80$", "$1.640\\times$", "$1.980\\times$", "$2.034\\times$", ""],
           ["$0.95$", "$2.871\\times$", "$3.277\\times$", "$2.810\\times$", ""],
           ["$0.99$", "$\\mathbf{4.490\\times}$", "$4.393\\times$", "$3.199\\times$",
            "3D 明显更好"]]),
    P("$\\text{corr}{=}0$ 那一行是要点：<strong>时间维毫无相关性时，联合 3D 压缩略微<em>更差</em></strong>"
      "（$0.984\\times$）——因为它要在一个高 $T$ 倍维度的空间里用同样多的样本估基。"),
    CALLOUT("warn", "一句常见的话需要被修正",
            "「视频冗余大所以要用 3D 压缩」把结论说成了数据的<em>属性</em>。"
            "准确的说法是：<strong>3D 压缩的收益等于时间相关性带来的可预测性</strong>，"
            "而它在相关性为零时是负的。"
            "这一点对工程有直接含义：<em>高帧率</em>素材（相邻帧几乎相同）用 3D 压缩收益极大，"
            "而<em>快速剪辑</em>的素材（每几帧就换镜头）收益接近零甚至为负——"
            "所以时间压缩率不该是一个全局常数。"),
])),

("nonmarkov", "为什么视频需要长上下文", "".join([
    P("既然相关性带来收益，那么「上下文越长越好」应该也成立？notebook 上的答案是<strong>不成立</strong>："),
    TABLE(["过程", "记忆结构", "$h{=}1$", "$h{=}2$", "$h{=}12$", "相对 $h{=}1$ 的改善"],
          [["AR(1)", "一阶马尔可夫", "$0.3506$", "$0.3505$", "$0.3655$",
            "$1.000\\times$ / $0.959\\times$"],
           ["AR(2)（振荡）", "二阶", "$0.8344$", "$0.3636$", "$0.4274$",
            "$\\mathbf{2.295\\times}$ 后持平"],
           ["匀速 + 中段遮挡", "非马尔可夫", "$1.0040$", "$1.0033$", "$0.0213$",
            "$\\mathbf{47.0\\times}$"]]),
    P("AR(1) 的一行说明：<strong>对马尔可夫过程，一帧就够了</strong>，"
      "$h{=}12$ 反而更差（同样的容量预算被摊薄）。"
      "AR(2) 的改善恰好在 $h{=}1 \\to 2$ 完成，之后持平——<em>改善的步数等于过程的阶数</em>。"),
    P("第三行才是视频的真实情形。notebook 构造一个匀速运动的物体，在 $[6,12)$ 帧被完全遮挡，"
      "任务是预测第 $12$ 帧（它重新出现的那一帧）："),
    TABLE(["历史 $h$", "输入覆盖帧", "含未遮挡帧？", "预测相对误差", "相对 $h{=}1$"],
          [["$1$", "$[11,12)$", "否（全空）", "$1.00401$", "$1.000\\times$"],
           ["$6$", "$[6,12)$", "否（全空）", "$1.00289$", "$1.001\\times$"],
           ["$\\mathbf{7}$", "$[5,12)$", "<strong>是</strong>", "$\\mathbf{0.30952}$",
            "$\\mathbf{3.244\\times}$"],
           ["$8$", "$[4,12)$", "是", "$0.05889$", "$17.048\\times$"],
           ["$12$", "$[0,12)$", "是", "$0.02134$", "$47.042\\times$"]]),
    P("$h \\leq 6$ 时输入<strong>全是被遮挡的空帧</strong>，误差 $\\approx 1.0$"
      "（除了均值什么也预测不出）。$h{=}7$ 一旦够到遮挡前的一帧，误差立刻塌到 $0.310$；"
      "$h{=}8$ 够到两帧后降到 $0.059$。"),
    DUAL("一帧告诉你物体<strong>在哪</strong>，两帧才告诉你它<strong>往哪走</strong>。"
         "遮挡期间当前帧什么也没有，所以必须回看到遮挡之前——"
         "而回看多远取决于遮挡有多长，这是一个与「相关性长度」无关的量。",
         "严格地说：位置 $x$ 与速度 $v$ 是状态的两个分量，"
         "而观测 $y_t = \\mathbb{1}[t \\notin \\text{occl}]\\cdot x_t$ 在遮挡期间是"
         "<strong>不可观测</strong>的（观测矩阵为零）。"
         "系统在遮挡区间上的可观测性矩阵秩为 $0$，"
         "所以任何只用遮挡内帧的估计器都只能给出先验均值。"
         "把窗口延长到覆盖 $\\geq 2$ 个未遮挡帧后，可观测性秩恢复到 $2$。"),
    CALLOUT("paper", "这一节修正了一个常见解释",
            "「视频模型需要长上下文，因为视频的相关性长」——这个解释是错的，"
            "AR(1) 那一行就是反例（相关性 $0.95$，但一帧就够）。"
            "正确的解释是：<strong>观测帧层面的视频不是马尔可夫的</strong>。"
            "可预测量（速度、遮挡物背后的状态、场景的持久属性）"
            "在某些帧上根本<em>不可从当前帧观测</em>，"
            "而长上下文买到的是<strong>可观测性</strong>，不是相关性。"),
])),

("map", "六个模块与它们各自要回答的问题", "".join([
    ASCII("""
                            时间轴
                              |
    +-------------+-----------+-----------+-------------+
    |             |           |           |             |
  压缩(m01)    注意力(m02)  漂移(m03)  可交互(m04)   评测(m05)
    |             |           |           |             |
 3D 压缩的收益  分解 =        误差按       被动生成 vs   FVD 的
 = 相关性       Kronecker 积  |â|^k        主动规划      三个病理
    |             |           |           |             |
 corr=0 时      深度与残差    一步拟合     0.0395 的一步  逐帧特征
 反而更差       都**不**涨秩   低估持续性   误差 -> 251%   对帧序
 (0.984x)      并行分支才涨   -> 变静止    的奖励高估     完全免疫
""".strip("\n")),
    TABLE(["模块", "要回答的问题", "本课量出的关键数"],
          [["01", "时间维该怎么压，压多少",
            "3D 收益 $0.984\\times$（corr$=0$）到 $4.49\\times$（corr$=0.99$）；"
            "流式的代价 $\\leq 3.1\\%$ 且<strong>非单调</strong>"],
           ["02", "分解式时空注意力损失了什么",
            "分解 $=$ Kronecker 积（差 $0$）；<strong>深度与残差都不涨秩</strong>，"
            "并行分支把秩推到 $2/4/16$"],
           ["03", "长视频为什么会漂",
            "一步拟合的 $\\hat a$ 向下有偏 $\\Rightarrow$ rollout 方差只有真值的 $35\\%$–$49\\%$；"
            "而 $28.6\\%$ 的拟合给出 $\\vert\\hat a\\vert > 1$"],
           ["04", "世界模型与视频生成是同一件事吗",
            "同一个模型：被动 rollout 高估 $-13\\%$，主动规划高估 $\\mathbf{+251\\%}$"],
           ["05", "视频生成怎么评",
            "FVD 在同分布下 $\\propto 1/N$；对匹配前两阶矩的分布<strong>看不出差别</strong>；"
            "逐帧特征对帧序的敏感度是 $7.1\\times10^{-15}$"]]),
    CALLOUT("danger", "本课的一条纪律",
            "以上每个数字都在 notebook 里由<strong>断言</strong>验证。"
            "而本轮探数阶段有<strong>五处</strong>结论被测量结果推翻后重写——"
            "其中最值得记的是模块 02："
            "我先猜「多个物体各自匀速就分解不了」（错，误差恰为 $0$），"
            "再猜「多叠层能补回来」（错，Kronecker 积之积仍是 Kronecker 积），"
            "再猜「残差连接能补回来」（也错，"
            "$(I{+}I{\\otimes}A_s)(I{+}A_t{\\otimes}I) = (I{+}A_t)\\otimes(I{+}A_s)$）。"
            "第四次才对：<strong>并行分支</strong>才是表达力的来源。"),
])),

("howto", "怎么用这门课", "".join([
    P("六个模块沿「从数据到评测」排列，而不是沿「模型从小到大」排列："),
    OL(["<strong>模块 01</strong>：视频 latent 与 tokenizer——时间维压缩的账，"
        "以及因果（流式）要付的代价。",
        "<strong>模块 02</strong>：时空注意力——三种做法的精确 FLOP 账，"
        "以及分解式注意力的表达力边界（一个 Kronecker 秩的问题）。",
        "<strong>模块 03</strong>：时序一致性与自回归漂移——"
        "误差增长律、一步拟合的系统性偏差、以及两种<em>症状相反</em>的失效。",
        "<strong>模块 04</strong>：世界模型——动作条件值多少、"
        "以及「被动生成」与「主动规划」为什么必须分开看（本课与 C41-04 的分界）。",
        "<strong>模块 05</strong>：视频评测——FVD 的三个病理，"
        "以及为什么逐帧指标结构性地看不见运动。"]),
    P("每个模块的 notebook 是纯 numpy、CPU、离线，含 4 个练习（TODO 桩 + 自测断言）、"
      "参考答案与一个真实工程胶囊。<strong>不训练任何神经网络</strong>——"
      "本课要说明的性质（压缩率、Kronecker 秩、谱半径、矩匹配）"
      "都是<em>线性代数与统计</em>层面的，用网络反而会把它们藏起来。"),
    CALLOUT("paper", "一句话读法",
            "如果只读一节：读<strong>模块 02 第 4 节</strong>"
            "（分解式注意力的 Kronecker 秩——那里有三个连续的、被数值推翻的猜想）。"
            "如果只跑一个 notebook：跑<strong>模块 03</strong>"
            "（那里能看到「生成的视频越往后越静止」这个现象"
            "在不需要任何神经网络的情况下就已经出现了）。"),
])),
]

NB = [
md("""# C77 模块 00 · 环境检查与总览

四件事：

1. **时间轴的代价是平方的**：$T{=}128$ 时注意力代价是单帧的 1024 倍；
2. **3D 压缩的收益是时间相关性的函数**——corr$=0$ 时它反而更差；
3. **遮挡悬崖**：长上下文买到的是可观测性，不是相关性；
4. **逐帧特征算的 FVD 对帧序完全免疫**（$7.1\\times10^{-15}$）。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import sys, platform
import numpy as np
print('python   ', sys.version.split()[0])
print('platform ', platform.platform())
print('numpy    ', np.__version__)
print()
print('本课全部计算为纯 numpy / CPU / 离线：无 GPU、无网络、无外部数据集，')
print('也**不训练任何神经网络** —— 要说明的性质都在线性代数与统计层面。')
assert np.__version__ >= '1.20', 'numpy 版本过低'
print('OK')"""),

md("""## 1. 时间轴的代价：token 数与注意力的精确账

$n = (T/p_t)\\cdot S$，注意力 FLOPs $\\propto n^2$。"""),

code("""H = W = 256
ph = pw = 16
S = (H // ph) * (W // pw)          # 每帧的 token 数
print(f'H=W={H}, patch {ph}x{pw}  ->  每帧 S = {S} 个 token')
print()
print('   T    p_t   token 数 n     n^2            相对 T=1 的注意力代价')
base = None
for T, pt in [(1,1),(16,4),(64,4),(128,4),(256,4)]:
    n = (T // pt) * S
    c = n * n
    if base is None:
        base = c
    print(f'  {T:4d}  {pt:3d}   {n:9,}   {c:14,}   {c/base:14.1f}x')

_n128 = (128 // 4) * S
assert _n128 == 8192
assert (_n128**2) // (S**2) == 1024, 'T=128, p_t=4 应是单帧的 1024 倍'
print()
print(f'-> T=128, p_t=4 时 n = {_n128}，注意力代价是单帧的 {(_n128**2)//(S**2)} 倍。')
print('   T 翻倍代价变 4 倍，不是 2 倍。')

print()
print('「联合建模」相对「逐帧独立」的额外因子:')
print('   T     逐帧: T 个 S^2       联合: (T*S)^2        联合/逐帧')
for T in (8, 16, 64, 128):
    sep = T * S * S
    joint = (T * S)**2
    print(f'  {T:4d}   {sep:16,}   {joint:18,}   {joint//sep:9d}x')
    assert joint // sep == T, '比值应恰好等于 T'
print()
print('-> 比值恒等于 T：(T·S)²/(T·S²) = T。这是一个恒等式，不是估计。')"""),

md("""## 2. 3D 压缩的收益 = 时间相关性

合成视频：6 个空间模式，各自的系数做 AR(1) 演化。
在**完全相同的系数预算**下比较逐帧 2D 与联合 3D，训练/测试分离。"""),

code("""S_PIX, DPF = 8, 64          # 8x8 像素 = 64 维/帧

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
    '''一段合成「视频」：空间模式的系数做 AR(1)。'''
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

def test_err(X, mu, P):
    Xc = X - mu
    R = Xc - (Xc @ P.T) @ P
    return float(np.sqrt(np.sum(R**2) / np.sum(Xc**2)))

T = 16
print(f'T={T}, {S_PIX}x{S_PIX}={DPF} 维/帧, 训练 4000 段 / 测试 1000 段')
print()
print('  corr   预算   逐帧 2D (k_s)  误差      联合 3D (k_j)  误差      误差比 (2D/3D)')
ratios = {}
for corr in (0.0, 0.5, 0.8, 0.95, 0.99):
    tr, te = gen(4000, 0, T=T, corr=corr), gen(1000, 10_000, T=T, corr=corr)
    for budget in (16, 32, 64):
        ks = budget // T
        mu2, P2 = fit_pca(tr.reshape(-1, DPF), ks)
        e2 = test_err(te.reshape(-1, DPF), mu2, P2)
        mu3, P3 = fit_pca(tr.reshape(len(tr), -1), budget)
        e3 = test_err(te.reshape(len(te), -1), mu3, P3)
        ratios[(corr, budget)] = e2 / e3
        print(f'  {corr:.2f}  {budget:5d}   k_s={ks:2d}       {e2:.5f}   '
              f'k_j={budget:3d}      {e3:.5f}   {e2/e3:8.3f}x')
    print()

# corr=0 时 3D 不比 2D 好（甚至更差）
assert all(ratios[(0.0, b)] < 1.01 for b in (16, 32, 64)), \\
    f'corr=0 时 3D 不该有优势：{[round(ratios[(0.0,b)],4) for b in (16,32,64)]}'
assert ratios[(0.0, 64)] < 1.0, '预算 64 时 3D 应略差于 2D'
# corr 越大收益越大
for b in (16, 32):
    seq = [ratios[(c, b)] for c in (0.0, 0.5, 0.8, 0.95, 0.99)]
    for i in range(1, len(seq)):
        assert seq[i] > seq[i-1], f'预算 {b}: 收益应随 corr 单调上升 {seq}'
assert ratios[(0.99, 16)] > 4.0, 'corr=0.99 时应有 4 倍以上收益'

print(f'✅ corr=0.00: 收益 {ratios[(0.0,16)]:.3f} / {ratios[(0.0,32)]:.3f} / '
      f'{ratios[(0.0,64)]:.3f}  —— 3D **不如** 2D')
print(f'✅ corr=0.99: 收益 {ratios[(0.99,16)]:.3f} / {ratios[(0.99,32)]:.3f} / '
      f'{ratios[(0.99,64)]:.3f}')
print()
print('-> 「视频冗余大所以要用 3D 压缩」把结论说成了数据的属性。')
print('   准确的说法：3D 压缩的收益 = 时间相关性带来的可预测性，')
print('   而它在相关性为零时是**负的**（要在高 T 倍维度的空间里用同样多样本估基）。')"""),

md("""## 3. 遮挡悬崖：长上下文买到的是可观测性

一个匀速运动的物体，在 $[6,12)$ 帧被**完全遮挡**（像素置零）。
任务：预测第 12 帧（它重新出现的那一帧）。"""),

code("""def make_occl(T=18, seed=0, t0=6, t1=12, noise=0.02):
    '''匀速运动 + [t0,t1) 完全遮挡。'''
    r = np.random.default_rng(seed)
    nm = len(BASIS)
    a = np.zeros((T, nm))
    a[0] = r.normal(0, 1, nm)
    v = r.normal(0, 0.3, nm)               # 每段视频有自己的速度
    for t in range(1, T):
        a[t] = a[t-1] + v
    V = a @ BASIS
    m = np.zeros((T, 1))
    m[t0:t1] = 1.0
    return V * (1 - m) + r.normal(0, noise, V.shape)

def gen_occl(n, seed0, **kw):
    return np.array([make_occl(seed=seed0+i, **kw) for i in range(n)])

def reg(Z, Y):
    return np.linalg.lstsq(np.column_stack([np.ones(len(Z)), Z]), Y, rcond=None)[0]
def apply_reg(Z, W):
    return np.column_stack([np.ones(len(Z)), Z]) @ W
def rel(Yh, Y):
    return float(np.sqrt(np.sum((Yh-Y)**2) / np.sum((Y - Y.mean(0, keepdims=True))**2)))

T2, T0, T1 = 18, 6, 12
TR, TE = gen_occl(6000, 0, T=T2, t0=T0, t1=T1), gen_occl(1500, 700_000, T=T2, t0=T0, t1=T1)
print(f'T={T2}, 遮挡区间 [{T0},{T1})。任务：预测第 {T1} 帧')
print(f'用 <= {T1-1} 的 h 帧作为输入。h <= {T1-T0} 时输入**全是被遮挡的空帧**')
print()
print('   历史 h   输入覆盖帧    含未遮挡帧?   预测相对误差   相对 h=1 的改善')
errs = {}
e1 = None
for h in (1, 2, 4, 6, 7, 8, 10, 12):
    lo = T1 - h
    Xtr = TR[:, lo:T1, :].reshape(len(TR), -1)
    Xte = TE[:, lo:T1, :].reshape(len(TE), -1)
    mu, P = fit_pca(Xtr, 48)
    W = reg((Xtr - mu) @ P.T, TR[:, T1, :])
    e = rel(apply_reg((Xte - mu) @ P.T, W), TE[:, T1, :])
    errs[h] = e
    if e1 is None:
        e1 = e
    has = '是' if lo < T0 else '否（全空）'
    print(f'  {h:6d}   [{lo:2d},{T1:2d})      {has:10s}   {e:.5f}        {e1/e:7.3f}x')

# h<=6 什么也预测不出；h=7 立刻塌下来
for h in (1, 2, 4, 6):
    assert errs[h] > 0.99, f'h={h} 应只能给出均值（误差 ~1.0），得到 {errs[h]:.5f}'
assert errs[7] < 0.4, f'h=7 应立刻改善，得到 {errs[7]:.5f}'
assert errs[8] < 0.1, f'h=8（够到两个未遮挡帧）应大幅改善，得到 {errs[8]:.5f}'
assert errs[1] / errs[12] > 40, f'h=12 相对 h=1 应改善 40 倍以上'

print()
print(f'✅ h<=6 时误差 ~1.0（除了均值什么也预测不出）')
print(f'✅ h=7 一够到遮挡前一帧 -> {errs[7]:.5f}（{e1/errs[7]:.2f}x）')
print(f'✅ h=8 够到两帧 -> {errs[8]:.5f}（{e1/errs[8]:.2f}x）')
print()
print('   一帧告诉你物体**在哪**，两帧才告诉你它**往哪走**。')
print('   -> 「视频模型需要长上下文因为相关性长」是错的解释。')
print('      正确的解释：观测帧层面的视频**不是马尔可夫的** ——')
print('      长上下文买到的是**可观测性**，不是相关性。')"""),

md("""## 4. 对照：马尔可夫过程不需要长上下文"""),

code("""def make_ar(T=18, seed=0, order=1, corr=0.95):
    '''order=1: AR(1)（一阶马尔可夫）；order=2: 振荡的 AR(2)。'''
    r = np.random.default_rng(seed)
    nm = len(BASIS)
    a = np.zeros((T, nm))
    if order == 1:
        a[0] = r.normal(0, 1, nm)
        for t in range(1, T):
            a[t] = corr * a[t-1] + np.sqrt(1 - corr**2) * r.normal(0, 1, nm)
    else:
        w = 2*np.pi/6.0
        c1, c2 = 2*corr*np.cos(w), -corr**2
        a[0], a[1] = r.normal(0,1,nm), r.normal(0,1,nm)
        for t in range(2, T):
            a[t] = c1*a[t-1] + c2*a[t-2] + 0.3*r.normal(0, 1, nm)
    return a @ BASIS + r.normal(0, 0.05, (T, DPF))

print('同样的预测任务（用 <= t 的 h 帧预测第 t+1 帧）:')
print()
gains = {}
for order, tag in [(1, 'AR(1)  一阶马尔可夫'), (2, 'AR(2)  振荡二阶')]:
    T3 = 18
    tr = np.array([make_ar(T=T3, seed=s, order=order) for s in range(6000)])
    te = np.array([make_ar(T=T3, seed=800_000+s, order=order) for s in range(1500)])
    tp = T3 - 1
    print(f'  {tag}:')
    print('     历史 h   预测相对误差   相对 h=1 的改善')
    g1 = None
    for h in (1, 2, 3, 6, 12):
        Xtr = tr[:, tp-h:tp, :].reshape(len(tr), -1)
        Xte = te[:, tp-h:tp, :].reshape(len(te), -1)
        mu, P = fit_pca(Xtr, 32)
        W = reg((Xtr-mu) @ P.T, tr[:, tp, :])
        e = rel(apply_reg((Xte-mu) @ P.T, W), te[:, tp, :])
        if g1 is None:
            g1 = e
        gains[(order, h)] = g1 / e
        print(f'     {h:6d}   {e:.5f}        {g1/e:7.3f}x')
    print()

assert abs(gains[(1, 2)] - 1.0) < 0.02, 'AR(1) 加一帧历史不该有改善'
assert abs(gains[(1, 3)] - 1.0) < 0.02, 'AR(1) 加两帧历史也不该有改善'
assert gains[(1, 12)] < 1.0, 'AR(1) 上 h=12 反而更差（容量被摊薄）'
assert gains[(2, 2)] > 2.0, 'AR(2) 从 h=1 到 h=2 应有 2 倍以上改善'
assert abs(gains[(2, 3)] / gains[(2, 2)] - 1.0) < 0.05, 'AR(2) 在 h=2 之后应持平'

print(f'✅ AR(1): h=2 的改善 {gains[(1,2)]:.3f}x（无改善），h=12 是 {gains[(1,12)]:.3f}x（更差）')
print(f'✅ AR(2): h=2 的改善 {gains[(2,2)]:.3f}x，h=3 是 {gains[(2,3)]:.3f}x（持平）')
print('   -> 改善的步数**恰好等于过程的阶数**，之后加历史只摊薄容量。')"""),

md("""## 5. 评测的预演：逐帧特征对帧序完全免疫"""),

code("""def frechet(m1, C1, m2, C2):
    '''高斯假设下的 Frechet 距离。'''
    d = m1 - m2
    ev1, V1 = np.linalg.eigh(C1)
    S1 = V1 @ np.diag(np.sqrt(np.clip(ev1, 0, None))) @ V1.T
    ev = np.clip(np.linalg.eigvalsh(S1 @ C2 @ S1), 0, None)
    return float(d @ d + np.trace(C1) + np.trace(C2) - 2*np.sum(np.sqrt(ev)))

def fd_samples(X, Y):
    return frechet(X.mean(0), np.cov(X, rowvar=False),
                   Y.mean(0), np.cov(Y, rowvar=False))

r = np.random.default_rng(1)
n, Tv, dfeat = 3000, 8, 16
base = r.normal(0, 1, (n, Tv, dfeat))
for t in range(1, Tv):
    base[:, t] = 0.9*base[:, t-1] + 0.436*base[:, t]    # 给它时间结构
perm = np.random.default_rng(2).permutation(Tv)
shuf = base[:, perm, :]                                  # 只把帧顺序打乱

print(f'同一批 {n} 段「视频」，只把帧顺序打乱（perm = {perm}）')
print()
def feats_perframe(V):
    '''逐帧特征后对时间取平均 —— 很多实现就是这么做的。'''
    return V.mean(1)
def feats_spatiotemporal(V):
    '''加上时间差分的最简时空特征。'''
    return np.concatenate([V.mean(1), np.abs(np.diff(V, axis=1)).mean(1)], 1)

fd_pf = fd_samples(feats_perframe(base), feats_perframe(shuf))
fd_st = fd_samples(feats_spatiotemporal(base), feats_spatiotemporal(shuf))
print(f'  逐帧特征取时间平均:    FD = {fd_pf:.6e}')
print(f'  含时间差分的时空特征:  FD = {fd_st:.6e}')
assert fd_pf < 1e-10, f'逐帧平均特征应对帧序完全免疫，得到 {fd_pf:.3e}'
assert fd_st > 0.1, f'时空特征应能看出帧序被打乱，得到 {fd_st:.3e}'
print()
print(f'✅ 逐帧平均特征下 FD = {fd_pf:.1e}（机器精度）—— 打乱帧序它一点也看不出来')
print(f'✅ 时空特征下 FD = {fd_st:.4f}')
print()
print('-> 这不是「不够敏感」，是**结构性免疫**：对时间取平均之后，')
print('   帧的顺序在特征里已经不存在了。所以「用逐帧特征算的 FVD」')
print('   根本不是在评测时间维 —— 模块 05 会把这一点做完。')"""),

md("""## ✏️ 练习 1：时空 patch 的代价账

实现 `attn_cost(T, H, W, pt, ph, pw)`，返回 `(token 数, 注意力代价, 相对单帧的倍数)`。

单帧的基准取 `pt=1, T=1` 时的代价。"""),

code("""def attn_cost(T, H, W, pt, ph, pw):
    '''时空 patch 下的 token 数与注意力代价。

    参数
    ----
    T, H, W    : 帧数、高、宽
    pt, ph, pw : 时间/高/宽方向的 patch 大小

    返回
    ----
    (n, cost, rel) :
      n    = (T//pt) * (H//ph) * (W//pw)
      cost = n^2
      rel  = cost / (单帧代价)，单帧 = ((H//ph)*(W//pw))^2
    '''
    # TODO
    raise NotImplementedError"""),

code("""# 自测
_n, _c, _r = attn_cost(128, 256, 256, 4, 16, 16)
assert _n == 8192, f'token 数应为 8192，得到 {_n}'
assert _c == 8192**2
assert abs(_r - 1024.0) < 1e-9, f'相对倍数应为 1024，得到 {_r}'
print(f'✅ T=128, p_t=4, 256x256/16: n={_n}, 相对单帧 {_r:.0f}x')

# T 翻倍 -> 代价 4 倍
_prev = None
print()
print('   T     n       相对单帧      相对上一档')
for _T in (16, 32, 64, 128, 256):
    _n, _c, _r = attn_cost(_T, 256, 256, 4, 16, 16)
    _ratio = '' if _prev is None else f'{_c/_prev:.2f}x'
    print(f'  {_T:4d}  {_n:6d}   {_r:10.1f}x   {_ratio:>10s}')
    if _prev is not None:
        assert abs(_c/_prev - 4.0) < 1e-9, 'T 翻倍代价应恰好变 4 倍'
    _prev = _c

# p_t 翻倍 -> 代价 1/4
_c4 = attn_cost(128, 256, 256, 4, 16, 16)[1]
_c8 = attn_cost(128, 256, 256, 8, 16, 16)[1]
assert abs(_c4 / _c8 - 4.0) < 1e-9, 'p_t 翻倍代价应恰好变 1/4'

# 相对单帧的代价恰好是 (T/p_t)^2 —— 与空间分辨率无关
print()
print('  相对单帧的代价与空间分辨率无关（恰好是 (T/p_t)²）:')
for _H in (128, 256, 512, 1024):
    _r = attn_cost(128, _H, _H, 4, 16, 16)[2]
    print(f'    {_H}x{_H}: {_r:.1f}x   ((T/p_t)² = {(128//4)**2})')
    assert abs(_r - (128//4)**2) < 1e-9, '相对代价应恰为 (T/p_t)²'
print()
print('✅ T 翻倍 -> 代价 ×4；p_t 翻倍 -> 代价 ×1/4；相对单帧的倍数 = (T/p_t)²'
      '（与分辨率无关）')
print('   -> 时间压缩率是唯一能**平方级**换回算力的旋钮，这是模块 01 的主题。')"""),

md("""## ✏️ 练习 2：3D 压缩何时才值得

实现 `compression_gain(corr, budget, T)`，返回该相关性与预算下
「逐帧 2D 误差 / 联合 3D 误差」的比值。

用它找出**收益跨过 1.0 的相关性阈值**。"""),

code("""def compression_gain(corr, budget, T=16, ntr=2000, nte=500):
    '''逐帧 2D 与联合 3D 在相同系数预算下的误差比。

    参数
    ----
    corr   : 时间相关性
    budget : 每段视频保留的总系数个数
    T      : 帧数
    ntr, nte : 训练/测试段数

    返回
    ----
    float : 误差比 (2D / 3D)，> 1 表示 3D 更好
    '''
    # TODO: 用 gen(ntr, 0, T=T, corr=corr) 与 gen(nte, 10_000, T=T, corr=corr)；
    #       2D 用 fit_pca(tr.reshape(-1, DPF), budget//T)；
    #       3D 用 fit_pca(tr.reshape(ntr, -1), budget)；
    #       都用 test_err 在测试集上评估，返回 e2/e3
    raise NotImplementedError"""),

code("""# 自测
print('   corr    预算 32 的收益')
_gs = {}
for _c in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95):
    _gs[_c] = compression_gain(_c, 32)
    print(f'  {_c:5.2f}    {_gs[_c]:8.4f}x')

# 单调上升
_seq = [_gs[c] for c in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95)]
for _i in range(1, len(_seq)):
    assert _seq[_i] > _seq[_i-1], f'收益应随 corr 单调上升：{[round(v,4) for v in _seq]}'
# corr=0 时不该有优势
assert _gs[0.0] < 1.02, f'corr=0 时不该有优势，得到 {_gs[0.0]:.4f}'
assert _gs[0.95] > 2.0, f'corr=0.95 时应有 2 倍以上收益，得到 {_gs[0.95]:.4f}'

# 找阈值
_grid = np.linspace(0.0, 0.6, 25)
_vals = [compression_gain(float(c), 32) for c in _grid]
_idx = int(np.argmax(np.array(_vals) > 1.05))
print()
print(f'✅ 收益跨过 1.05 的相关性阈值 ≈ {_grid[_idx]:.3f}')
print(f'✅ corr=0 时收益 {_gs[0.0]:.4f}（无优势），corr=0.95 时 {_gs[0.95]:.4f}')
print()
print('   工程含义：时间压缩率不该是一个全局常数。')
print('   高帧率素材（相邻帧几乎相同）收益极大；')
print('   快速剪辑的素材（每几帧换镜头）收益接近零甚至为负。')"""),

md("""## ✏️ 练习 3：可观测性悬崖的位置

实现 `occlusion_cliff(t0, t1, tpred)`，返回让预测误差首次跌破 0.5 的历史长度 $h^*$。

验证 $h^* = t_{pred} - t_0 + 1$：即窗口刚好够到遮挡前**一帧**的那个长度。"""),

code("""def occlusion_cliff(t0, t1, tpred, T=18, ntr=3000, nte=800, thresh=0.5):
    '''找出预测误差首次跌破 thresh 的历史长度 h*。

    参数
    ----
    t0, t1 : 遮挡区间 [t0, t1)
    tpred  : 要预测的帧
    T      : 总帧数
    thresh : 判定阈值

    返回
    ----
    (h_star, errs) : h*，以及 {h: 误差} 字典（h 从 1 到 tpred）
    '''
    tr = gen_occl(ntr, 0, T=T, t0=t0, t1=t1)
    te = gen_occl(nte, 700_000, T=T, t0=t0, t1=t1)
    # TODO: 对 h in 1..tpred，用 tr[:, tpred-h:tpred, :] 作为输入预测第 tpred 帧；
    #       用 fit_pca(..., 48) 降维、reg/apply_reg 回归、rel 算误差；
    #       返回首个误差 < thresh 的 h 与全部误差
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 预测遮挡后**第一帧**（tpred = t1）:')
print('      遮挡区间   预测帧   h*   理论 t1-t0+1   前若干档误差')
for _t0, _t1 in [(6, 12), (4, 10), (8, 14), (5, 9)]:
    _h, _e = occlusion_cliff(_t0, _t1, _t1)
    _theo = _t1 - _t0 + 1
    _shown = ' '.join(f'{_e[k]:.2f}' for k in sorted(_e)[:min(9, len(_e))])
    print(f'      [{_t0:2d},{_t1:2d})      {_t1:3d}    {_h:2d}   {_theo:10d}     {_shown}')
    assert _h == _theo, f'h* 应为 {_theo}（够到遮挡前一帧），得到 {_h}'

print()
print('  (b) 预测遮挡结束**之后**的帧（tpred > t1）:')
print('      遮挡区间   预测帧   h*   说明')
for _t0, _t1, _tp in [(6, 12, 13), (6, 12, 15), (4, 10, 14)]:
    _h, _e = occlusion_cliff(_t0, _t1, _tp)
    print(f'      [{_t0:2d},{_t1:2d})      {_tp:3d}    {_h:2d}   前一帧已可见，一帧就够')
    assert _h == 1, f'tpred>t1 时 h* 应为 1，得到 {_h}'

# 悬崖是突变的，不是渐变的
_h, _e = occlusion_cliff(6, 12, 12)
assert _e[_h-1] > 0.9, f'h*-1 时应仍在 ~1.0，得到 {_e[_h-1]:.4f}'
assert _e[_h] < 0.5, f'h* 时应已跌破 0.5，得到 {_e[_h]:.4f}'
assert _e[_h-1] / _e[_h] > 2.5, '悬崖应是突变（相邻两档差 2.5 倍以上）'
print()
print(f'✅ h*={_h}：h={_h-1} 时误差 {_e[_h-1]:.4f}，h={_h} 时 {_e[_h]:.4f}'
      f'（一档之差 {_e[_h-1]/_e[_h]:.2f} 倍）')
print(f'✅ 预测遮挡后第一帧时 h* 恰为 t1-t0+1（四组配置全对）；')
print(f'   而预测更晚的帧时 h*=1 —— **所需上下文不是全局属性，它取决于预测哪一帧**。')
print()
print('   -> 工程判据因此是「最坏情况」的：上下文窗口要覆盖')
print('      「场景中最长的不可观测区间 + 2 帧」（一帧给位置，两帧给速度），')
print('      因为你无法只在需要的那些帧上临时加长窗口。')"""),

md("""## ✏️ 练习 4：一个指标对帧序敏感吗

实现 `order_sensitivity(feat_fn, n=2000, T=8, d=16, seeds=5)`：
对给定的特征函数，返回「打乱帧序后的 FD」在多个随机置换下的**中位数**。

这是一个可以直接套用到任何视频指标上的检验。"""),

code("""def order_sensitivity(feat_fn, n=2000, T=8, d=16, seeds=5):
    '''特征函数对帧序的敏感度（多次随机置换的 FD 中位数）。

    参数
    ----
    feat_fn : 把 (n, T, d) 的视频批映射到 (n, k) 特征的函数
    n, T, d : 批大小、帧数、每帧特征维
    seeds   : 试多少个随机置换

    返回
    ----
    float : FD 的中位数
    '''
    r = np.random.default_rng(11)
    V = r.normal(0, 1, (n, T, d))
    for t in range(1, T):
        V[:, t] = 0.9*V[:, t-1] + 0.436*V[:, t]
    # TODO: 对 s in range(seeds)：用 np.random.default_rng(100+s).permutation(T)
    #       打乱帧序，算 fd_samples(feat_fn(V), feat_fn(V_shuffled))，返回中位数
    raise NotImplementedError"""),

code("""# 自测：几种特征的帧序敏感度
def _f_mean(V):
    '''逐帧特征取时间平均。'''
    return V.mean(1)
def _f_concat(V):
    '''把所有帧拼起来（保留全部顺序信息）。'''
    return V.reshape(len(V), -1)
def _f_diff(V):
    '''时间差分的绝对值均值。'''
    return np.abs(np.diff(V, axis=1)).mean(1)
def _f_first_last(V):
    '''首末帧之差。'''
    return V[:, -1] - V[:, 0]
def _f_sorted(V):
    '''对时间轴排序后再平均 —— 故意构造的、对顺序免疫的特征。'''
    return np.sort(V, axis=1).mean(1)

print('  特征                          帧序敏感度 (FD 中位数)   判定')
_res = {}
for _name, _fn, _expect in [
        ('逐帧平均 mean_t', _f_mean, 'blind'),
        ('时间排序后平均', _f_sorted, 'blind'),
        ('全帧拼接', _f_concat, 'sensitive'),
        ('时间差分均值', _f_diff, 'sensitive'),
        ('首末帧之差', _f_first_last, 'sensitive')]:
    _v = order_sensitivity(_fn)
    _res[_name] = _v
    _verdict = '对帧序免疫' if _v < 1e-9 else '能看出帧序'
    print(f'  {_name:28s}  {_v:.6e}      {_verdict}')
    if _expect == 'blind':
        assert _v < 1e-9, f'{_name} 应对帧序免疫，得到 {_v:.3e}'
    else:
        assert _v > 1e-3, f'{_name} 应能看出帧序，得到 {_v:.3e}'

print()
print('✅ 两类特征被干净地分开：免疫的 < 1e-9（机器精度），敏感的 > 1e-3')
print()
print('   注意「时间排序后平均」这一行：它是一个**看起来很时空**的特征')
print('   （它确实用到了整段时间），但对帧序完全免疫。')
print('   -> 所以判断一个指标能不能评时间维，不能看它「用了多少帧」，')
print('      只能看它在帧序置换下变不变。这个检验应该对每个视频指标跑一次。')"""),

md("""## 📖 参考答案"""),

code("""def attn_cost(T, H, W, pt, ph, pw):
    '''时空 patch 下的 token 数与注意力代价。'''
    nf = (H // ph) * (W // pw)
    n = (T // pt) * nf
    cost = n * n
    return n, cost, float(cost / (nf * nf))

def compression_gain(corr, budget, T=16, ntr=2000, nte=500):
    '''逐帧 2D 与联合 3D 在相同系数预算下的误差比。'''
    tr = gen(ntr, 0, T=T, corr=corr)
    te = gen(nte, 10_000, T=T, corr=corr)
    mu2, P2 = fit_pca(tr.reshape(-1, DPF), max(1, budget // T))
    e2 = test_err(te.reshape(-1, DPF), mu2, P2)
    mu3, P3 = fit_pca(tr.reshape(ntr, -1), budget)
    e3 = test_err(te.reshape(nte, -1), mu3, P3)
    return float(e2 / max(e3, 1e-12))

def occlusion_cliff(t0, t1, tpred, T=18, ntr=3000, nte=800, thresh=0.5):
    '''找出预测误差首次跌破 thresh 的历史长度 h*。'''
    tr = gen_occl(ntr, 0, T=T, t0=t0, t1=t1)
    te = gen_occl(nte, 700_000, T=T, t0=t0, t1=t1)
    errs, h_star = {}, None
    for h in range(1, tpred + 1):
        lo = tpred - h
        Xtr = tr[:, lo:tpred, :].reshape(len(tr), -1)
        Xte = te[:, lo:tpred, :].reshape(len(te), -1)
        mu, P = fit_pca(Xtr, 48)
        W = reg((Xtr - mu) @ P.T, tr[:, tpred, :])
        errs[h] = rel(apply_reg((Xte - mu) @ P.T, W), te[:, tpred, :])
        if h_star is None and errs[h] < thresh:
            h_star = h
    return h_star, errs

def order_sensitivity(feat_fn, n=2000, T=8, d=16, seeds=5):
    '''特征函数对帧序的敏感度（多次随机置换的 FD 中位数）。'''
    r = np.random.default_rng(11)
    V = r.normal(0, 1, (n, T, d))
    for t in range(1, T):
        V[:, t] = 0.9*V[:, t-1] + 0.436*V[:, t]
    vals = []
    for s in range(seeds):
        perm = np.random.default_rng(100 + s).permutation(T)
        vals.append(fd_samples(feat_fn(V), feat_fn(V[:, perm, :])))
    return float(np.median(vals))

print('参考答案已定义。')
print()
print('要点：')
print('  1. 时间压缩率 p_t 是唯一能**平方级**换回算力的旋钮（p_t 翻倍 -> 代价 1/4）。')
print('  2. 3D 压缩的收益是相关性的函数，corr=0 时为负 —— 不该用全局常数压缩率。')
print('  3. 所需上下文长度由**最长不可观测区间**决定（+2 帧给位置和速度），')
print('     与相关性长度无关。')
print('  4. 判断指标能否评时间维，只能看帧序置换检验，不能看它「用了多少帧」。')"""),

md("""## 🧪 真实工程胶囊：一份视频生成配置的代价-收益体检

下面这段代码把本模块的四件事压成一次「配置体检」：给定分辨率、帧数、
时间压缩率、素材的时间相关性、以及场景里最长的遮挡时长，
它输出**算力代价**、**压缩收益**、**所需上下文**，并指出配置里自相矛盾的地方。

关键设计：它不给「推荐配置」，而是把三个量放在一起，让**互相冲突的部分显形**——
因为它们确实会冲突（更大的 $p_t$ 省算力但降低时间分辨率，
而遮挡决定的上下文下界又要求足够的时间跨度）。"""),

code("""def audit_video_config(cfg):
    '''视频生成配置的代价-收益体检。

    cfg 字段:
      H, W, T          : 分辨率与帧数
      ph, pw, pt       : 空间/时间 patch
      corr             : 素材的相邻帧相关性（可从数据估）
      max_occl_frames  : 场景里最长的不可观测（遮挡）时长，单位=原始帧
      budget_ratio     : 允许的注意力代价上限（相对单帧的倍数）
    '''
    n, cost, rel_cost = attn_cost(cfg['T'], cfg['H'], cfg['W'],
                                  cfg['pt'], cfg['ph'], cfg['pw'])
    issues = []
    print(f"配置: {cfg['H']}x{cfg['W']}, T={cfg['T']}, patch {cfg['pt']}x{cfg['ph']}x{cfg['pw']}")
    print(f"  token 数 n = {n:,}")
    print(f"  注意力代价 = {rel_cost:,.0f}x 单帧" +
          (f"   （上限 {cfg['budget_ratio']:,}x）" if 'budget_ratio' in cfg else ''))

    # ① 算力预算
    if 'budget_ratio' in cfg and rel_cost > cfg['budget_ratio']:
        need_pt = cfg['pt'] * np.sqrt(rel_cost / cfg['budget_ratio'])
        issues.append(f"COST: 超预算 {rel_cost/cfg['budget_ratio']:.1f}x。"
                      f"把 p_t 提到 >= {np.ceil(need_pt):.0f} 可以压回来"
                      f"（代价 ∝ 1/p_t²）")

    # ② 时间压缩的收益（用相关性判断）
    #    相邻 latent 帧之间的有效相关性 = corr^pt
    eff = cfg['corr'] ** cfg['pt']
    print(f"  素材相邻帧相关性 = {cfg['corr']:.3f}，"
          f"压缩 p_t={cfg['pt']} 后 latent 间相关性 = {eff:.4f}")
    if cfg['corr'] < 0.3:
        issues.append(f"GAIN: corr={cfg['corr']:.2f} 太低，3D 联合压缩的收益 <= 1.0 "
                      f"（本课实测 corr=0 时是 0.984x，即**更差**）。"
                      f"这种素材应逐帧压缩")
    elif eff < 0.3:
        issues.append(f"GAIN: p_t={cfg['pt']} 把 latent 间相关性压到 {eff:.3f}，"
                      f"时间维已经几乎没有可利用的冗余 —— 再增大 p_t 只丢信息不省结构")

    # ③ 上下文下界（由最长遮挡决定）
    need_ctx = cfg['max_occl_frames'] + 2          # 遮挡 + 位置 + 速度
    need_latent = int(np.ceil(need_ctx / cfg['pt']))
    have_latent = cfg['T'] // cfg['pt']
    print(f"  最长遮挡 {cfg['max_occl_frames']} 帧 -> 上下文下界 {need_ctx} 原始帧 "
          f"= {need_latent} 个 latent 帧；当前有 {have_latent} 个")
    if have_latent < need_latent:
        issues.append(f"CONTEXT: latent 帧数 {have_latent} < 所需 {need_latent}。"
                      f"遮挡期间的可观测性秩为 0 —— 模型只能给出先验均值"
                      f"（本课实测误差 ~1.0）")

    print('-' * 74)
    if not issues:
        print('  ✅ 三项都在范围内')
    for it in issues:
        print(f'  ⚠️  {it}')
    print('-' * 74)
    print(f'  {len(issues)} 项冲突')
    print()
    return issues

print('=== 配置 A：一个「看起来很合理」的高分辨率长视频配置 ===')
_a = audit_video_config(dict(H=512, W=512, T=128, ph=16, pw=16, pt=4,
                             corr=0.97, max_occl_frames=24, budget_ratio=500))
assert any(x.startswith('COST') for x in _a), '应报出算力超预算'

print('=== 配置 B：把 p_t 提到 16 来压算力 ===')
_b = audit_video_config(dict(H=512, W=512, T=128, ph=16, pw=16, pt=16,
                             corr=0.97, max_occl_frames=24, budget_ratio=500))
assert not any(x.startswith('COST') for x in _b), 'p_t=16 应已压回预算内'

print('=== 配置 C：同样的 p_t=16，但素材是快速剪辑（corr 低）===')
_c = audit_video_config(dict(H=512, W=512, T=128, ph=16, pw=16, pt=16,
                             corr=0.15, max_occl_frames=24, budget_ratio=500))
assert any(x.startswith('GAIN') for x in _c), 'corr 低时应报出 3D 压缩无收益'

print('=== 配置 D：上下文不够覆盖遮挡 ===')
_d = audit_video_config(dict(H=512, W=512, T=32, ph=16, pw=16, pt=8,
                             corr=0.97, max_occl_frames=40, budget_ratio=500))
assert any(x.startswith('CONTEXT') for x in _d), '应报出上下文不足'

print('工程含义：')
print('  · 三项**互相冲突**：p_t 变大省算力（∝1/p_t²）但同时')
print('    ① 压低 latent 间相关性（收益变小）② 减少 latent 帧数（上下文变短）。')
print('    所以「调 p_t」不是一个单目标优化，而是三方拉锯 —— 体检器的作用是')
print('    让拉锯显形，而不是给一个假装最优的数字。')
print('  · corr 与 max_occl_frames 都应该**从数据估**，而不是拍。')
print('    本课模块 01 与练习 3 给出这两个量的估法。')""")
,]
