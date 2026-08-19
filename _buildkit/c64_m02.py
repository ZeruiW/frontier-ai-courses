# -*- coding: utf-8 -*-
"""C64 模块 02 · 优化与训练问答（ML/DL 技术知识问答）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "知道梯度下降是什么、见过反向传播的链式法则；不需要重新推导任何优化器的收敛证明"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_optimization_qa.ipynb（纯 numpy，6 种优化器同一玩具问题对比 / '
                    'AdamW 解耦衰减量化 / warmup 梯度范数对比 / 初始化前向方差追踪 / 损失函数梯度形状对比）'),
    ("核心参考", "C07 模块 05「优化器从零：SGD→AdamW」（本课不重复推导，只讲怎么在 60 秒内说清楚并接住追问）· "
              "Kingma&Ba 2015 · Loshchilov&Hutter 2019 (AdamW) · Goyal et al. 2017（线性缩放规则）"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("optimizer-family", "优化器家族：从 SGD 到 AdamW，机制差异与怎么选", "".join([
        P("面试里被问「说说你了解的优化器」时，最容易翻车的答法是<strong>背名字</strong>——"
          "SGD、Momentum、AdaGrad、RMSProp、Adam、AdamW 说一串，然后被一句「那你训 ResNet 用哪个」问住。"
          "<strong>三段式答法</strong>要求你对每个优化器都能说出：一句话机制、它解决了前一个的什么问题、"
          "它在什么场景下反而更差。"),
        TABLE(["优化器", "核心更新（一句话）", "解决了什么问题", "什么时候它反而更差 / 踩雷点"], [
            ["<strong>SGD</strong>", "$x \\leftarrow x - \\eta g$", "最朴素的基线，可解释、超参少", "病态曲率（山谷）下振荡剧烈，收敛慢；对学习率极敏感"],
            ["<strong>Momentum</strong>", "累积历史梯度的指数加权方向再走", "缓解山谷震荡，冲过平坦区/鞍点", "$\\mu$ 太大会<strong>超调（overshoot）</strong>，在陡峭方向来回震荡幅度反而变大"],
            ["<strong>Nesterov</strong>", "先按动量方向探一步，在<em>探到的位置</em>算梯度再修正", "比 Momentum 更早「看到」前方曲率变化，收敛更稳", "对高度非凸的损失面（深度网络中后期）收益变小，工程上常与 Momentum 差异不大"],
            ["<strong>AdaGrad</strong>", "$x \\leftarrow x - \\dfrac{\\eta}{\\sqrt{\\sum g^2}+\\epsilon} g$", "<strong>按维度自适应缩放</strong>：稀疏特征的维度获得更大有效步长", "分母单调只增不减，训练越久有效学习率越接近 0——<strong>过早停止学习</strong>"],
            ["<strong>RMSProp</strong>", "把 AdaGrad 的累加换成指数滑动平均", "修好 AdaGrad「学习率死亡」的问题，非平稳目标下仍好用", "没有动量项，遇到窄谷仍可能震荡；仍需要调 $\\eta$"],
            ["<strong>Adam</strong>", "RMSProp 的二阶矩 + Momentum 的一阶矩，都做 bias correction", "工业界默认起手式：收敛快、对学习率不敏感、对超参鲁棒", "<strong>L2 正则在 Adam 下被自适应分母缩放，等价性被破坏</strong>（下一节）；在 CV 分类任务上常有更大泛化 gap"],
            ["<strong>AdamW</strong>", "Adam + <strong>解耦</strong>权重衰减（衰减直接作用在参数上）", "修好 Adam 的 weight-decay bug；现在语言/视觉 Transformer 的默认选择", "解耦衰减率仍是全局超参，不同层的合适衰减强度可能不同（需要 per-group 配置）"],
        ]),
        ASCII("""                    高曲率方向(y)
                         ▲
        SGD 轨迹：       │  ╱╲  ╱╲  ╱╲
        沿窄谷反复        │ ╱  ╲╱  ╲╱  ╲          <- 每步都在 y 方向来回，
        撞壁，x 方向      │╱                        x 方向几乎不进展
        几乎不进展   ─────┼───────────────────▶ 低曲率方向(x)
                         │
        自适应方法       │
        (AdaGrad/RMSProp │  ＼
        /Adam) 轨迹：     │    ＼___
        两个方向的有效    │        ＼___
        步长被独立归一化  │            ＼____▶ 直接斜着走向最优点
        到同一量级        └──────────────────────

        本节 notebook 会在 f(x,y)=0.5(x² + 100y²) 这个「病态曲率」玩具问题上把这张图跑出真实数字：
        SGD 让 x、y 两个方向的收敛速度差几十个数量级；RMSProp/Adam/AdaGrad 几乎完全拉平。"""),
        MATH("v_t = \\mu v_{t-1} - \\eta g_t,\\qquad x_t = x_{t-1} + v_t \\qquad\\text{(Momentum)}"),
        MATH("m_t=\\beta_1 m_{t-1}+(1-\\beta_1)g_t,\\;\\; v_t=\\beta_2 v_{t-1}+(1-\\beta_2)g_t^2,\\;\\; "
             "x_t = x_{t-1} - \\eta\\,\\dfrac{\\hat m_t}{\\sqrt{\\hat v_t}+\\epsilon} \\qquad\\text{(Adam，}\\hat m,\\hat v\\text{ 为偏差修正后的值)}"),
        DUAL(
            "「为什么 CV 里 SGD+Momentum 常常仍是首选，而 NLP/Transformer 几乎全用 Adam/AdamW？」——这是本节<strong>最高频的追问</strong>。"
            "直白的答案：CV 里的经典 backbone（ResNet 系）训练配方是十年集体调参调出来的，SGD+Momentum+精心设计的 LR schedule "
            "在 ImageNet 上的<em>最终精度</em>普遍略高于 Adam；而 Transformer 的损失面在训练早期极不友好（下一节会展开），"
            "Adam 的自适应缩放这时候是「保命」的，没有它训练根本起不来。",
            "更严谨地说，这是<strong>优化难度</strong>与<strong>泛化质量</strong>两件事的权衡。经验证据（Wilson et al. 2017,"
            " <em>The Marginal Value of Adaptive Gradient Methods</em>）显示，在同样收敛到训练误差很低的前提下，"
            "自适应方法找到的极小值在图像分类任务上<span class=\"term\">泛化 gap</span>更大——一种解释是自适应方法更容易收敛到"
            "尖锐（sharp）极小值，而 SGD 的各向同性噪声更容易被"
            "「甩」向平坦（flat）极小值。<em>这个解释目前仍有争议</em>（sharp/flat 与泛化的因果关系本身在文献里没有定论），"
            "但它是面试里可以给出的最佳可引用答案。工程上更朴素的原因是：CV 的成熟训练配方（LR warmup+cosine、"
            "weight decay、BN）本来就是围绕 SGD+Momentum 调出来的，换成 Adam 需要重新调一整套超参。",
        ),
        CALLOUT("warn", "<strong>常见踩雷点</strong>：① 把 Adam 的「对学习率不敏感」理解成「不需要调学习率」——"
                        "Adam 仍然需要 warmup 和 schedule，只是没有 SGD 那么容易训练发散。"
                        "② 混淆 AdaGrad 和 RMSProp：<strong>两者唯一区别就是分母的累积方式</strong>"
                        "（AdaGrad 全程累加、RMSProp 指数滑动平均），说不出这一点会被追问「那你说说 AdaGrad 为什么后来不常用了」。"
                        "③ 认为 Nesterov 一定比 Momentum 好——在深度网络的高度非凸损失面上，"
                        "「向前探一步」用的曲率信息本身就不准，实践中二者差异往往很小。"),
    ])),

    # ============================================================== 2
    ("weight-decay-adamw", "Weight Decay 与 L2：AdamW 到底修的是哪个 bug", "".join([
        P("这是 C64 全课<strong>面试价值最高的单个知识点之一</strong>——因为它有一个精确、可推导、"
          "大多数候选人说不清楚的机制，而且刚好可以用一句话验证「候选人是真懂还是背书」："
          "<strong>「在 SGD 下，L2 正则和 weight decay 完全等价；在 Adam 下，它们不等价——为什么？」</strong>"),
        MATH("\\text{L2 正则（加进 loss）：}\\; g'_t = g_t + \\lambda x_{t-1} \\qquad\\qquad "
             "\\text{Weight decay（直接作用在参数上）：}\\; x_t = (1-\\eta\\lambda)\\,x_{t-1} - \\eta g_t"),
        P("在 <strong>SGD</strong> 下把 $g'_t=g_t+\\lambda x_{t-1}$ 代入更新式，"
          "$x_t = x_{t-1}-\\eta(g_t+\\lambda x_{t-1}) = (1-\\eta\\lambda)x_{t-1}-\\eta g_t$——"
          "和右边 weight decay 的公式<strong>完全一样</strong>。这是很多人「L2 = weight decay」这个直觉的来源，"
          "但这个直觉<strong>只在 SGD 下成立</strong>。"),
        P("在 <strong>Adam</strong> 下，正则项 $\\lambda x_{t-1}$ 会先被当成梯度的一部分，"
          "进入一阶矩 $m_t$ 和二阶矩 $v_t$ 的滑动平均，然后被 $1/\\sqrt{\\hat v_t}$ 缩放——"
          "而 $\\hat v_t$ 恰恰是这个参数<strong>历史梯度方差的估计</strong>。"
          "结果是：历史梯度方差越大（$v_t$ 越大）的参数，正则项被压得越小，衰减效果越弱；"
          "方差小的参数反而被过度衰减。<strong>这不是「差不多等价」，是方向性的系统偏差。</strong>"),
        TABLE(["优化器", "L2（加进 loss）与 Weight Decay（直接衰减参数）", "对不同参数的衰减是否一致"], [
            ["SGD / Momentum", "数学上完全等价", "是——衰减率对所有参数统一是 $\\eta\\lambda$"],
            ["Adam（把 L2 当梯度处理）", "<strong>不等价</strong>：衰减强度被 $1/\\sqrt{\\hat v}$ 缩放", "否——梯度历史方差大的参数衰减被显著削弱（notebook 会算出具体倍数）"],
            ["AdamW（解耦衰减）", "衰减项 $\\eta\\lambda x$ 直接作用在参数上，绕开 $m,v$", "是——衰减率对所有参数重新变得统一，与 Adam 想解决的问题被修复"],
        ]),
        DUAL(
            "直白地说：Adam 的分母是在问「这个参数最近抖得凶不凶」，抖得凶的参数会被自动缩小步长——"
            "这本来是件好事（自适应）。但如果你把正则化的「拉回去」这个动作也塞进同一个分母里，"
            "抖得凶的参数连「被拉回去」这件事也一起被缩小了，等于是<em>越需要被管教的参数，"
            "反而被管教得越轻</em>——这显然不是设计权重衰减的初衷。AdamW 的修法极简单：把「拉回去」这个动作单独拎出来，"
            "不让自适应分母碰它。",
            "Loshchilov & Hutter (2019, <em>Decoupled Weight Decay Regularization</em>) 用这个观察解释了"
            "「为什么 Adam 训出来的模型往往比同等设置的 SGD 泛化更差」的一部分原因——"
            "并不是 Adam 本身有问题，而是<strong>大多数实现把 L2 和 weight decay 混为一谈</strong>，"
            "导致 Adam 实际生效的正则化强度远小于名义设置的 $\\lambda$，且因参数而异、不可控。"
            "AdamW 把两者解耦后，在 ImageNet 与语言模型上都能用<strong>更大且更可控</strong>的 weight decay，"
            "缩小了与 SGD+Momentum 的泛化差距。这也是<strong>现在几乎所有 Transformer 训练配方默认用 AdamW 而非 Adam</strong>的原因。",
        ),
        CALLOUT("danger", "<strong>面试高频陷阱</strong>：如果你在 PyTorch 里写 <code>torch.optim.Adam(params, weight_decay=1e-4)</code>，"
                          "它做的是<strong>把 weight decay 加进梯度</strong>（即 L2 style），<strong>不是</strong>解耦版本！"
                          "解耦版本必须显式用 <code>torch.optim.AdamW</code>。这个 API 命名坑真实存在，"
                          "很多论文复现失败的根因就是这一行调错了类。"),
    ])),

    # ============================================================== 3
    ("lr-schedule-warmup", "学习率调度与 Warmup：为什么不能一上来就用目标学习率", "".join([
        P("三个调度器的一句话机制：<strong>step</strong>——每隔固定 epoch 数把学习率乘一个衰减因子（简单粗暴，"
          "衰减点靠手调）；<strong>cosine</strong>——学习率沿余弦曲线从初始值平滑降到接近 0（无需手调衰减点，"
          "结尾降得慢，末期训练更稳定）；<strong>one-cycle</strong>——先升后降，"
          "峰值学习率可以设得比传统方案更大，整个训练时长更短（Leslie Smith 的超收敛 super-convergence 思路）。"),
        ASCII("""学习率
  │
  │  step:      ▔▔▔▔▔▔▔╗
  │                     ╚▔▔▔▔▔╗
  │                           ╚▔▔▔▔▔▏
  │
  │  cosine:    ╭─╮
  │            ╱   ╲___
  │           ╱        ╲___
  │          ╱             ╲______
  │
  │  one-cycle:      ╱╲
  │                 ╱  ╲
  │                ╱    ╲________
  │               ╱
  │  warmup ─────╱│
  │ (前 W 步线性爬升，再接上面任一种调度)
  └──────────────────────────────────────▶ 训练步数"""),
        MATH("\\eta_t = \\eta_{\\max}\\cdot\\min\\!\\Big(1,\\ \\frac{t}{W}\\Big) \\qquad\\text{（线性 warmup，}W\\text{ 为 warmup 步数)}"),
        P("<strong>Warmup 为什么必要</strong>——这是本节的核心追问，三个独立成因都要能说："),
        TABLE(["成因", "机制", "对应对策"], [
            ["<strong>自适应优化器早期统计量不可靠</strong>", "Adam 在 $t=1$ 时，无论真实梯度量级多大，更新幅度都约等于 $\\eta$ 本身"
             "（本节 notebook 会数值验证：梯度从 $10^{-3}$ 到 $10^{3}$ 跨 6 个数量级，第一步更新量恒为 $\\approx\\eta$）——"
             "这在随机初始化、损失面条件数未知时是一次「盲目的满幅步」，warmup 把它压小", "线性/指数 warmup"],
            ["<strong>大 batch 训练的方差累积</strong>", "batch 越大，单步梯度的统计量越可信，但如果一上来就用为大 batch 标定的大学习率，"
             "初始参数下的损失面曲率还没被「探明」，容易一步迈进不稳定区域", "warmup + 线性缩放规则（下一节）"],
            ["<strong>Transformer 的 LayerNorm 梯度尺度问题</strong>", "Post-LN 结构在训练初期，深层的梯度经过多层归一化后方差会被放大，"
             "自适应优化器叠加未收敛的二阶矩估计，极易在训练前几十步震荡发散", "Transformer 几乎<strong>必须</strong>用 warmup；"
             "Pre-LN 结构对此更鲁棒，但工业界仍普遍保留 warmup"],
        ]),
        DUAL(
            "直白理解：模型刚初始化时，你完全不知道损失面长什么样——可能有的方向很陡有的很平，"
            "优化器的「胆子」（学习率、自适应缩放）都还没来得及根据真实情况调整，这时候如果一步就迈很大，"
            "很可能一脚踩空。Warmup 相当于「先小步试探几脚，等地形摸清楚了再放开走」。",
            "更精确地：warmup 期间学习率从 0（或很小值）线性爬升到目标值，这段时间里 Adam 的 $\\hat m_t,\\hat v_t$ "
            "逐渐从「几乎没有历史」的高方差估计过渡到统计上可信的估计；同时给参数一段「原地小幅调整」的窗口，"
            "让损失面的局部曲率信息通过若干步梯度传播开。notebook 会在一个简化的 1D 问题上直接测量"
            "「有无 warmup 时训练轨迹上的梯度范数」，量化不加 warmup 时早期梯度范数的尖峰有多大。",
        ),
        CALLOUT("intuition", "记住一句可以直接在面试里说的话：<strong>「Adam 的自适应机制解决的是『不同参数该用多大步长』，"
                             "但它解决不了『整个模型在训练第一步该不该迈出一个满幅步』——这正是 warmup 要补的洞。」</strong>"),
    ])),

    # ============================================================== 4
    ("vanishing-exploding", "梯度消失与爆炸：成因、诊断与四件套对策", "".join([
        P("<strong>一句话定义</strong>：反向传播的梯度是逐层相乘得到的，如果每层的「乘数」持续小于 1 或大于 1，"
          "经过足够多层后梯度会指数级趋于 0（消失）或发散（爆炸）。"),
        MATH("\\frac{\\partial L}{\\partial x_0} = \\frac{\\partial L}{\\partial x_L}\\prod_{l=1}^{L} "
             "\\frac{\\partial x_l}{\\partial x_{l-1}} \\;\\approx\\; \\frac{\\partial L}{\\partial x_L}\\cdot c^{L}"
             "\\qquad\\text{（若每层乘数近似恒为 }c\\text{，}L\\text{ 层后梯度按 }c^L\\text{ 缩放)}"),
        P("$c<1$（比如 sigmoid 在非零区的导数上界只有 0.25，权重初始化又偏小）→ 梯度消失；"
          "$c>1$（权重初始化偏大，或 RNN 里同一权重矩阵被重复相乘很多个时间步）→ 梯度爆炸。"
          "这四个独立成因、四类对策要能对应上，是本节最容易被追问「除了初始化你还知道什么」的地方："),
        TABLE(["成因", "典型场景", "对策"], [
            ["<strong>饱和激活函数</strong>", "sigmoid/tanh 在输入绝对值大时导数趋于 0", "换 ReLU/GELU 类分段线性或近似线性的激活"],
            ["<strong>初始化不当</strong>", "权重方差与 fan_in/fan_out 不匹配，逐层放大或缩小激活方差", "Xavier/He 初始化（下一节）"],
            ["<strong>网络过深、无跳连</strong>", "梯度要连续乘过几十上百层的雅可比", "<strong>残差连接</strong>：跳连提供一条梯度为 1 的「高速公路」（见 C64-03）"],
            ["<strong>内部协变量偏移累积</strong>", "每层输入分布随参数更新持续漂移，梯度尺度不稳定", "<strong>归一化</strong>（BN/LN/GN，见 C64-03）把每层输入方差重新拉回可控范围"],
            ["<strong>长序列的重复相乘（RNN 特有）</strong>", "同一权重矩阵在时间维度上被相乘 $T$ 次，$c^T$ 极易失控", "梯度裁剪（应对爆炸）+ 门控结构 LSTM/GRU（应对消失，用加法路径代替连乘）"],
        ]),
        DUAL(
            "怎么诊断？消失的症状是<strong>浅层参数几乎不更新</strong>（打印每层梯度范数，越靠近输入层越接近 0）、"
            "loss 下降极慢或早早停滞；爆炸的症状是 <strong>loss 突然变成 NaN/Inf</strong>，或者打印梯度范数发现某一步突然飙升几个数量级。"
            "两者的排查手法几乎相反：消失要往「加深路径、换激活、查初始化」方向查，爆炸要往「加裁剪、降学习率、查数据里的异常值」方向查。",
            "严谨地说，$\\partial x_l/\\partial x_{l-1}$ 是一个雅可比矩阵，真正决定长期行为的是它的谱（最大/最小奇异值），"
            "「乘数恒为 $c$」只是最简化的标量近似。梯度裁剪（gradient clipping，按范数或按值裁剪）"
            "不解决消失问题，只是把爆炸的幅度限制在一个安全范围内，让优化器不至于因为一次异常大梯度直接把参数带飞——"
            "<em>它是对症状的兜底，不是对成因的修复</em>，这个区分在面试里经常被追问。",
        ),
        CALLOUT("warn", "<strong>踩雷点</strong>：把梯度裁剪当成万能药。裁剪只能防止<em>单步</em>梯度过大导致的发散，"
                        "如果模型结构本身有系统性的梯度消失（比如极深的 sigmoid 网络没有跳连），"
                        "裁剪完全无能为力——因为问题不是「太大」而是「太小」。"),
    ])),

    # ============================================================== 5
    ("initialization", "初始化：Xavier 与 He 的方差守恒直觉", "".join([
        P("<strong>一句话定义</strong>：好的初始化让激活值的方差在前向传播中<strong>逐层保持稳定</strong>，"
          "不随深度增加而爆炸或坍缩为 0——这既是为了前向传播时的数值健康，也是为了反向传播时梯度尺度稳定"
          "（两者是同一个方差守恒思想在两个方向上的应用）。"),
        P("推导直觉（不重复 C07 的完整推导，只讲「为什么是这个系数」）：设一层线性变换 $y=Wx$，"
          "$x$ 的各分量独立、方差为 $\\mathrm{Var}(x)$，$W$ 的元素独立零均值、方差为 $\\mathrm{Var}(W)$，"
          "fan_in 个输入相加，则 $\\mathrm{Var}(y) = \\text{fan\\_in}\\cdot\\mathrm{Var}(W)\\cdot\\mathrm{Var}(x)$。"
          "要让 $\\mathrm{Var}(y)=\\mathrm{Var}(x)$（方差不随层数变化），就必须让 $\\mathrm{Var}(W)=1/\\text{fan\\_in}$。"),
        MATH("\\text{线性/tanh 附近（Xavier/Glorot）：}\\; \\mathrm{Var}(W)=\\frac{2}{\\text{fan\\_in}+\\text{fan\\_out}} "
             "\\qquad\\qquad \\text{ReLU（He/Kaiming）：}\\; \\mathrm{Var}(W)=\\frac{2}{\\text{fan\\_in}}"),
        P("He 初始化多出来的那个系数 <strong>2</strong> 是全部推导里唯一需要「新增假设」的地方："
          "ReLU 会把约一半的预激活值置零（假设预激活关于 0 对称），所以输出的方差大约只有输入线性部分方差的一半，"
          "$\\mathrm{Var}(\\mathrm{ReLU}(z)) \\approx \\tfrac12 \\mathrm{Var}(z)$——"
          "要抵消这个「打对折」，权重方差必须<strong>翻倍</strong>补偿。Xavier 的推导没有这个假设，"
          "因为它是为 tanh/sigmoid 这类关于 0 近似对称、不做「打对折」操作的激活设计的。"),
        TABLE(["方案", "适配的激活假设", "方差公式（简化的 fan_in 版）", "用错会怎样"], [
            ["Xavier/Glorot", "线性、tanh、sigmoid（对称，不砍一半）", "$1/\\text{fan\\_in}$", "配 ReLU 用：每层方差打对折，几十层后激活值<strong>指数级坍缩到 0</strong>（notebook 会实测 20 层后方差降到初始的 $10^{-6}$ 量级）"],
            ["He/Kaiming", "ReLU 及其变体（LeakyReLU/GELU 近似适用）", "$2/\\text{fan\\_in}$", "配纯线性/tanh 深网络用：方差会略微偏大但通常问题不大（少了「打对折」，补偿系数变成多余但不致命）"],
        ]),
        DUAL(
            "直白说：如果一层网络会让信号「变小一半」（ReLU 干的事），你就得让这一层的权重「放大一倍」补回来，"
            "不然信息传几十层就没了——这就是深层网络訓練不动、loss 长期不下降的一个常见根因。",
            "严谨地说，这套推导有两个隐含假设：① 各层激活近似独立同分布、关于 0 对称；② 只看前向方差，"
            "没有联合考虑反向传播时梯度方差的匹配约束（Xavier 原论文实际上是同时求解前向、反向两个约束的折中，"
            "这也是为什么 Xavier 用 $\\text{fan\\_in}+\\text{fan\\_out}$ 而不是单独的 fan_in——完整推导见 C07-05）。"
            "实践中现代框架的默认初始化已经内置了这套逻辑（PyTorch 的 <code>nn.Linear</code> 默认用 Kaiming-uniform 的变体），"
            "但<strong>自定义层、非标准激活（如 Swish/GELU 的具体系数）时，仍需要自己核对假设是否成立</strong>。",
        ),
        CALLOUT("intuition", "面试可以直接背的一句话：<strong>「Xavier 假设激活是对称、线性近似的；He 在此基础上专门为 ReLU "
                             "会砍掉一半激活值这件事补了个系数 2。用错激活对应的初始化，本质上是让方差守恒的假设失效了。」</strong>"),
    ])),

    # ============================================================== 6
    ("batch-size-generalization", "批大小与泛化：大 batch 为什么会「变笨」", "".join([
        P("<strong>一句话定义</strong>：固定 epoch 数下，用更大的 batch size 训练，往往会在<em>相同训练精度</em>下"
          "得到<em>更差的验证/测试精度</em>——这个现象叫<span class=\"term\">大 batch 泛化差距</span>"
          "（generalization gap），不是简单地「大 batch 就是差」，而是需要配套调整才能追平。"),
        P("<strong>为什么会这样</strong>——主流解释是 SGD 每一步的梯度噪声本身起到隐式正则化的作用："
          "小 batch 下单步梯度是真实梯度加上一个方差较大的噪声项，这个噪声会让优化轨迹更容易「跳出」尖锐的极小值，"
          "倾向于落在更平坦（flat）的区域；大 batch 减小了梯度噪声，优化更「精确」地沿真实梯度下降，"
          "反而更容易停在尖锐极小值里——而<strong>尖锐极小值通常泛化更差</strong>（这个「平坦=泛化好」的假说本身仍有争议，"
          "但是目前面试里最常被接受的解释框架）。"),
        MATH("\\eta_{\\text{new}} = \\eta_{\\text{base}}\\cdot\\frac{B_{\\text{new}}}{B_{\\text{base}}} "
             "\\qquad\\text{（线性缩放规则，Goyal et al. 2017，需配合 warmup 使用）}"),
        P("<strong>线性缩放规则</strong>的直觉：batch size 增大 $k$ 倍，单步梯度的方差降低约 $k$ 倍"
          "（$k$ 个独立同分布梯度的均值方差是单个的 $1/k$），如果保持「同样多个 epoch 内参数总的期望移动量不变」，"
          "学习率应该同步放大 $k$ 倍来补偿方差降低带来的「步子变保守」。但这条规则<strong>只在一定范围内成立</strong>——"
          "batch size 大到一定程度后线性缩放会失效（需要 LARS/LAMB 这类逐层自适应学习率的方法，或者干脆放弃线性缩放）。"),
        TABLE(["batch size 区间", "现象", "配套对策"], [
            ["小（数十到数百）", "梯度噪声大，天然正则化强，但吞吐低、硬件利用率差", "标准 SGD/Adam 配方即可"],
            ["中等（数千）", "线性缩放规则通常有效，配合 warmup 可追平小 batch 精度", "线性缩放学习率 + warmup（呼应上一节）"],
            ["极大（数万以上，如 ImageNet in 1 hour 的 8192）", "线性缩放开始失效，训练不稳定/精度掉点", "分层自适应学习率（LARS/LAMB）、更长 warmup、"
             "有时需要专门的正则化补偿（label smoothing 等）"],
        ]),
        DUAL(
            "直白说：小 batch 训练时每一步都带点「噪声」，这点噪声像是给优化过程加了随机扰动，"
            "反而不容易让模型钻进一个很窄很陡的坑里出不来；大 batch 每一步都算得很「准」，"
            "精准地滑向最近的坑，但那个坑可能又窄又陡，换个数据（测试集）稍微一偏就掉出去了。",
            "工程上这也解释了为什么<strong>只调大 batch size 而不动学习率</strong>是常见误区——"
            "很多人扩大 batch 后发现精度不升反降，第一反应是「大 batch 就是不好」，"
            "但真正的根因往往是没有同步放大学习率、没有加 warmup，属于<em>没调超参</em>而不是<em>方法本身有问题</em>。"
            "本课程 notebook 的重点是让你能在讨论里区分「大 batch 的固有泛化差距」和「没配套调参导致的伪差距」这两件事。",
        ),
        CALLOUT("warn", "<strong>面试追问预案</strong>：「那车端训练/云端大规模训练该怎么选 batch size？」——"
                        "标准答案骨架：先看硬件吞吐能压榨到什么程度（显存、通信开销），"
                        "定下 batch size 后<strong>必须</strong>同步给出学习率的缩放方案和 warmup 步数，"
                        "并且用小规模实验（呼应 C61-01 的种子方差原则）验证精度没有因为换 batch size 而回退。"),
    ])),

    # ============================================================== 7
    ("mixed-precision", "混合精度与梯度累积：fp16 溢出、loss scaling、bf16", "".join([
        P("<strong>一句话定义</strong>：混合精度训练用 fp16/bf16 做大部分计算（省显存、提吞吐，"
          "现代 GPU 的 fp16/bf16 算力常是 fp32 的数倍），同时保留一份 fp32 的「主权重」副本做参数更新，"
          "避免低精度舍入误差在多步累积后侵蚀训练稳定性。"),
        TABLE(["格式", "指数位/尾数位", "动态范围", "典型问题"], [
            ["fp32", "8 / 23", "很大（约 $10^{\\pm38}$）", "显存/带宽占用大，是基线"],
            ["fp16", "5 / 10", "较小（约 $10^{\\pm4.8}$）——<strong>容易溢出</strong>", "梯度值稍小就直接下溢为 0，稍大就上溢为 Inf"],
            ["bf16", "8 / 7", "与 fp32 相同（约 $10^{\\pm38}$）——<strong>不容易溢出</strong>", "尾数位比 fp16 更少，小数值的相对精度更差（不是溢出问题，是精度问题）"],
        ]),
        P("<strong>fp16 溢出</strong>的根因：反向传播里很多梯度值远小于 fp16 能表示的最小正规数"
          "（尤其是深层网络接近输入端的梯度，经过层层链式相乘后数值本就偏小），直接用 fp16 存储会大量<strong>下溢为 0</strong>——"
          "相当于凭空丢掉了大量梯度信息。<strong>Loss scaling</strong> 的对策极简单：反向传播前把 loss 乘一个大的缩放因子"
          "（比如 $2^{14}$），这样所有梯度都被同比例放大，进入 fp16 可表示的健康范围；"
          "更新参数前再把梯度除回缩放因子——由于是线性缩放，数学上完全等价，只是绕开了 fp16 的下溢陷阱。"),
        MATH("g_{\\text{fp16}} = \\text{fp16}\\big(S\\cdot L\\big)\\text{ 反传得到的梯度} \\;\\Rightarrow\\; "
             "g_{\\text{真实}} = g_{\\text{fp16}}/S \\qquad\\text{（}S\\text{ 为 loss scale，通常动态调整）}"),
        P("<strong>动态 loss scaling</strong>：$S$ 定得太小起不到防下溢的作用，定得太大又会导致梯度<strong>上溢为 Inf/NaN</strong>——"
          "现代实现（如 <code>torch.cuda.amp</code>）用自适应策略：正常训练时每隔 $N$ 步把 $S$ 翻倍试探更大范围，"
          "一旦某步检测到 Inf/NaN 就跳过这次更新并把 $S$ 减半，本质是一个「不断试探安全上限」的反馈控制。"
          "<strong>bf16 因为指数位与 fp32 相同</strong>，动态范围天然够大，<strong>通常不需要 loss scaling</strong>，"
          "这是它相比 fp16 最大的工程简化——代价是同样 16 位下尾数位更少，小梯度的相对精度比 fp16 差。"),
        H3("梯度累积：显存不够时的「假装大 batch」"),
        P("<strong>一句话定义</strong>：把一个大 batch 拆成若干个 micro-batch 依次前向反向，"
          "梯度在参数更新前<strong>累加</strong>（不清零、不更新），凑够等效 batch size 后再统一执行一次优化器更新。"
          "解决的问题是「显存放不下目标 batch size」，代价是<strong>训练时间变长</strong>（多次前向反向但只有一次参数更新的收益）。"
          "<strong>踩雷点</strong>：如果模型里有 BatchNorm，梯度累积并不会让 BN 的统计量跟着「变大的等效 batch」一起变——"
          "BN 仍然只看到每个 micro-batch 各自的统计量，<strong>等效 batch size 变大但 BN 的行为并没有真正变成大 batch</strong>，"
          "这是很多人认为「梯度累积等价于大 batch 训练」时会漏掉的一点。"),
        DUAL(
            "直白说：fp16 的表示范围窄，很多本来该有的小梯度会被直接归零，等于白算；loss scaling 就是先把所有数字放大一批，"
            "算完再缩小回去，数学上没有任何变化，纯粹是「借用更大的数字避开归零陷阱」。bf16 因为指数位留得多，"
            "根本不会掉进这个陷阱，所以不需要这个额外机制。",
            "更完整的图景是：混合精度训练要同时管理<strong>三份状态</strong>——fp32 主权重（保证累积更新不失真）、"
            "fp16/bf16 的前向/反向计算副本（吞吐与显存收益的来源）、以及优化器状态（Adam 的 $m,v$ 通常仍保留 fp32 精度，"
            "否则动量的长期累积同样会被舍入误差侵蚀）。<em>「混合」的本质是精度分层管理，不是简单地把所有东西换成低精度</em>。",
        ),
        CALLOUT("danger", "<strong>面试常见追问</strong>：「BN 的 running mean/var 要不要用 fp16？」——正确答案：<strong>不要</strong>，"
                          "running statistics 是长期指数滑动平均，用低精度会让小的更新量被舍入吞掉、统计量长期漂移；"
                          "这类需要长期累积、数值范围可能很小的状态（优化器动量、BN running stats）"
                          "<strong>惯例上都保留 fp32</strong>，只有单步的前向激活与梯度计算才用低精度。"),
    ])),

    # ============================================================== 8
    ("loss-choice", "损失函数选择：MSE/MAE/Huber 与 CE/Focal/Label Smoothing", "".join([
        P("<strong>回归损失三选一</strong>的判据只有一条：<strong>你有多在乎离群值</strong。"),
        MATH("\\text{MSE: } \\tfrac12 e^2,\\ \\ \\partial e = e \\qquad "
             "\\text{MAE: } |e|,\\ \\ \\partial e=\\mathrm{sign}(e) \\qquad "
             "\\text{Huber}_\\delta\\text{: } \\begin{cases}\\tfrac12 e^2 & |e|\\le\\delta\\\\ "
             "\\delta(|e|-\\tfrac12\\delta) & |e|>\\delta\\end{cases},\\ \\ \\partial e=\\mathrm{clip}(e,-\\delta,\\delta)"),
        TABLE(["损失", "梯度形状", "对离群值的行为", "典型场景"], [
            ["MSE", "梯度<strong>随误差线性增长</strong>，无上限", "一个巨大的离群误差会产生巨大梯度，把整个训练拖偏", "误差近似高斯、无明显离群点的回归"],
            ["MAE", "梯度恒为 $\\pm1$，与误差大小无关", "对离群值天然鲁棒（不会被单个大误差主导）", "标注噪声大、有离群点的场景；代价是 0 附近不可导，收敛后期梯度不会自动变小"],
            ["Huber", "小误差区二次（信息量足），大误差区线性（有界）", "兼顾 MSE 的精细收敛与 MAE 的离群鲁棒性", "检测里的框回归（L1/smooth-L1 就是 Huber 的近亲），见 C54-02"],
        ]),
        P("<strong>分类损失</strong>：CE（交叉熵）是默认基线，梯度大小正比于 $(1-p_t)$（$p_t$ 为真实类别的预测概率）——"
          "越自信地答错，梯度越大，这本身已经有一定的「难例加权」效果。<strong>Focal Loss</strong> "
          "在此基础上再乘一个 $(1-p_t)^\\gamma$ 调制因子，专门压低<em>已经分对且很自信</em>的样本对总损失/梯度的贡献。"),
        MATH("\\mathrm{FL}(p_t) = -(1-p_t)^{\\gamma}\\log(p_t) \\qquad "
             "\\text{（}\\gamma=0\\text{ 退化为标准 CE；}\\gamma\\text{ 越大，对易分样本的压制越狠）}"),
        DUAL(
            "为什么需要 Focal？前景背景比例悬殊的检测任务里（一张图几万个候选框，正样本可能只有几十个），"
            "海量「一眼就能分对」的背景框虽然单个梯度不大，但<strong>数量太多，加总起来会淹没稀少的难例/正样本梯度</strong>——"
            "Focal 相当于把训练预算从「人多的简单题」重新分配给「人少的难题」。",
            "notebook 会用数值微分直接测出 Focal 相对 CE 的梯度衰减曲线：对预测很自信且答对的样本"
            "（比如预测概率 0.99），Focal 的梯度只有 CE 的千分之一量级；而对预测严重出错的难例（预测概率很低），"
            "Focal 的梯度不仅没被压制，衰减系数本身求导还会带来一个额外的<strong>放大项</strong>，"
            "这是很多人只记住「Focal=降权简单样本」而漏掉的细节——完整机制见 C54-02。",
        ),
        H3("Label Smoothing：给「越来越自信」这件事踩刹车"),
        P("<strong>一句话定义</strong>：把 one-hot 标签 $[0,\\dots,1,\\dots,0]$ 替换成"
          "$(1-\\epsilon)\\cdot\\text{one-hot}+\\epsilon/K$（$K$ 为类别数），"
          "让「正确答案」不再是绝对的 100% 置信度目标。<strong>为什么需要它</strong>：不加约束的交叉熵训练会持续鼓励"
          "模型把正确类的 logit 推向无穷大（因为只要预测概率没到 100%，梯度就还是负的、还在往上推），"
          "这既会造成<strong>过度自信</strong>（校准变差，见 C64-04），也可能通过让模型过度依赖训练集里的细微线索而<strong>损害泛化</strong>。"
          "加了 label smoothing 后，一旦预测概率超过目标软标签值，梯度会<strong>变号</strong>——"
          "从「继续推高」变成「往回拉」，相当于给置信度装了一个软性天花板。"),
        CALLOUT("intuition", "<strong>什么时候不该用 label smoothing</strong>：如果下游任务本身需要模型输出精确校准的概率"
                             "（比如要用置信度直接做阈值决策），过度的 label smoothing 会让概率整体压缩、"
                             "反而让校准变得不可预测，需要配合温度缩放等校准手段一起评估（见 C64-04）；"
                             "另外如果类别数 $K$ 很大（比如上千类），$\\epsilon/K$ 分给每个错误类别的量微乎其微，"
                             "smoothing 的实际效果会大打折扣，需要相应调大 $\\epsilon$。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("这一节的问题不会直接出现在你的一面里，但能帮你在被追问「你还知道什么更新的东西吗」时不露怯。"),
        UL([
            "<strong>自适应优化器为什么在非凸问题上有效，理论收敛保证却很弱？</strong>Adam 原论文的收敛性证明后来被发现有漏洞"
            "（Reddi et al. 2018 指出 Adam 在某些简单凸问题上甚至不收敛，并提出 AMSGrad 修复），"
            "但工程实践里 Adam/AdamW 的效果远好于理论保证所暗示的下界。<em>「理论落后于实践」在优化器这个方向尤其明显。</em>",
            "<strong>Sharpness-Aware Minimization（SAM）</strong>把「平坦极小值泛化更好」这个假说直接做成了优化目标——"
            "显式地在参数邻域内找最坏情况损失并最小化它，在多个视觉基准上取得了一致的泛化提升，"
            "<em>但每步需要两次前向反向，训练成本翻倍，这是它没有成为默认选择的主要原因。</em>",
            "<strong>无需 warmup 的优化器是否可行？</strong>近期一些工作（如 Lion、Sophia 等）尝试通过改变更新规则本身"
            "（符号化更新、二阶信息）减少对 warmup 的依赖，但在超大规模 Transformer 预训练里，"
            "<em>warmup 至今仍是几乎所有公开训练配方的标配，尚未有充分证据证明可以安全去掉。</em>",
            "<strong>μP（maximal update parametrization）</strong>试图解决「小模型上调好的超参数换到大模型上直接失效」这个"
            "工程界长期头疼的问题——通过重新参数化，让最优学习率等超参数<em>不随模型宽度变化</em>，"
            "从而可以在小模型上搜索超参再直接迁移到大模型。<em>这是目前大规模预训练超参搜索最有希望的方向之一，"
            "但对不同架构、不同优化器的适配细节仍在发展中。</em>",
            "<strong>混合精度与量化训练的边界在哪？</strong>FP8 训练已经在部分大模型预训练中被验证可行，"
            "<em>这意味着「哪些状态必须保留高精度」这个问题的答案还在继续演化——本节给出的 fp32/fp16/bf16 三分法"
            "可能在几年内需要再加一档。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Kingma & Ba, <em>Adam: A Method for Stochastic Optimization</em>（2015）——"
                         "Adam 的原始机制与偏差修正推导。"
                         "<strong>★</strong> Loshchilov & Hutter, <em>Decoupled Weight Decay Regularization</em>（2019，AdamW）——"
                         "本节第 2 节的核心出处，也是 SGDR 余弦退火的作者。"
                         "<strong>★</strong> Goyal et al., <em>Accurate, Large Minibatch SGD</em>（2017）——"
                         "线性缩放规则与 warmup 在 ImageNet 大 batch 训练上的系统验证。"
                         "<strong>★</strong> Glorot & Bengio, <em>Understanding the Difficulty of Training Deep Feedforward "
                         "Neural Networks</em>（2010，Xavier 初始化）与 He et al., <em>Delving Deep into Rectifiers</em>（2015，He 初始化）。"
                         "<strong>★</strong> Lin et al., <em>Focal Loss for Dense Object Detection</em>（2017）；"
                         "Szegedy et al., <em>Rethinking the Inception Architecture</em>（2016，label smoothing 出处）；"
                         "Micikevicius et al., <em>Mixed Precision Training</em>（2018）。</p>"
                         "<p>配套材料：Wilson et al., <em>The Marginal Value of Adaptive Gradient Methods in Machine "
                         "Learning</em>（2017，本节 CV 里 SGD+Momentum 优势的证据来源）；Foret et al., "
                         "<em>Sharpness-Aware Minimization</em>（2021）；Reddi et al., <em>On the Convergence of Adam "
                         "and Beyond</em>（2018）。数学推导完整版见 <strong>C07 模块 05</strong>「优化器从零：SGD→AdamW」；"
                         "损失函数在检测任务里的具体形态见 <strong>C54 模块 02</strong>；相邻模块："
                         "<strong>C64-01</strong>（ML 基础问答）、<strong>C64-03</strong>（深度学习架构问答）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · 优化与训练问答（6 种优化器对拍 / AdamW 解耦衰减 / warmup / 初始化方差 / 损失梯度形状）

目标：把「说说 Adam 和 SGD 的区别」这类问题，从背概念变成**能亲手跑出数字来支撑答案**。

本 notebook 你会亲手实现并验证：
1. **6 种优化器**在同一个「病态曲率」玩具问题上的真实轨迹差异
2. **AdamW 解耦衰减 vs Adam+L2** 的衰减强度差异（量化到具体倍数）
3. **有无 warmup** 时 Adam 早期更新幅度的对比
4. **Xavier vs He 初始化**对深层 ReLU 网络前向方差的影响（20 层追踪）
5. **Focal Loss / Label Smoothing** 的梯度形状与标准 CE 的差异

> 心智模型：**每一个「优化器八卦」都对应一个可以用 20 行 numpy 复现的具体现象——背答案不如背怎么现场证明它。**"""),

    md("""## 0 · 环境自检"""),

    code("""import sys
import numpy as np

print('Python:', sys.version.split()[0])
print('numpy :', np.__version__)
assert sys.version_info >= (3, 8)
rng = np.random.default_rng(0)
print('\\n✅ 环境自检通过：本课全程 numpy + 标准库，无需 GPU，不联网。')"""),

    md("""## 1 · 六种优化器在「病态曲率」玩具问题上的真实差异

玩具问题：$f(x,y) = 0.5(a x^2 + b y^2)$，取 $a{=}1, b{=}100$（条件数 100，是一个典型的窄山谷）。
梯度 $\\nabla f = (ax, by)$。从 $(1,1)$ 出发，看谁能把两个方向都收敛好。"""),

    code("""def grad_fn(xy, a=1.0, b=100.0):
    return np.array([a * xy[0], b * xy[1]])

def run_sgd(xy0, lr, steps, a=1.0, b=100.0):
    xy = xy0.copy()
    for _ in range(steps):
        xy = xy - lr * grad_fn(xy, a, b)
    return xy

def run_momentum(xy0, lr, steps, mu=0.9, nesterov=False, a=1.0, b=100.0):
    xy = xy0.copy(); v = np.zeros_like(xy)
    for _ in range(steps):
        g = grad_fn(xy + mu * v, a, b) if nesterov else grad_fn(xy, a, b)
        v = mu * v - lr * g
        xy = xy + v
    return xy

def run_adagrad(xy0, lr, steps, eps=1e-8, a=1.0, b=100.0):
    xy = xy0.copy(); G = np.zeros_like(xy)
    for _ in range(steps):
        g = grad_fn(xy, a, b)
        G += g ** 2
        xy = xy - lr * g / (np.sqrt(G) + eps)
    return xy

def run_rmsprop(xy0, lr, steps, beta=0.9, eps=1e-8, a=1.0, b=100.0):
    xy = xy0.copy(); s = np.zeros_like(xy)
    for _ in range(steps):
        g = grad_fn(xy, a, b)
        s = beta * s + (1 - beta) * g ** 2
        xy = xy - lr * g / (np.sqrt(s) + eps)
    return xy

def run_adam(xy0, lr, steps, beta1=0.9, beta2=0.999, eps=1e-8, a=1.0, b=100.0):
    xy = xy0.copy(); m = np.zeros_like(xy); v = np.zeros_like(xy)
    for t in range(1, steps + 1):
        g = grad_fn(xy, a, b)
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g ** 2
        mhat = m / (1 - beta1 ** t)
        vhat = v / (1 - beta2 ** t)
        xy = xy - lr * mhat / (np.sqrt(vhat) + eps)
    return xy

x0 = np.array([1.0, 1.0])
print('六种优化器实现就位（SGD / Momentum / Nesterov / AdaGrad / RMSProp / Adam）。')"""),

    code("""# ---- 实验 A：病态曲率下，SGD 对两个方向的收敛速度极不平衡，自适应方法几乎完全拉平 ----
steps = 200
xy_sgd = run_sgd(x0, lr=0.008, steps=steps)
xy_adagrad = run_adagrad(x0, lr=0.1, steps=steps)
xy_rmsprop = run_rmsprop(x0, lr=0.1, steps=steps)
xy_adam = run_adam(x0, lr=0.1, steps=steps)

def balance_ratio(xy):
    \"\"\"y 方向剩余量 / x 方向剩余量：越接近 1 说明两个方向收敛得越"平衡"。\"\"\"
    return abs(xy[1]) / abs(xy[0])

r_sgd = balance_ratio(xy_sgd)
r_ada = balance_ratio(xy_adagrad)
r_rms = balance_ratio(xy_rmsprop)
r_adam = balance_ratio(xy_adam)

print(f'SGD      最终位置={xy_sgd}   平衡比 r={r_sgd:.3e}   (b=100a 的高曲率方向几乎瞬间归零，'
      f'低曲率方向严重滞后)')
print(f'AdaGrad  最终位置={xy_adagrad}   平衡比 r={r_ada:.4f}')
print(f'RMSProp  最终位置={xy_rmsprop}   平衡比 r={r_rms:.4f}')
print(f'Adam     最终位置={xy_adam}   平衡比 r={r_adam:.4f}')

assert r_sgd < 1e-6, 'SGD 应表现出极端不平衡（两方向收敛速度差几十个数量级）'
assert abs(r_ada - 1.0) < 0.2, 'AdaGrad 应把两个方向的收敛速度拉到接近 1:1'
assert abs(r_rms - 1.0) < 0.2, 'RMSProp 同理'
assert abs(r_adam - 1.0) < 0.2, 'Adam 同理'
print('\\n✅ 验证：自适应方法对每个维度独立按曲率归一化，SGD 没有这个机制。')"""),

    code("""# ---- 实验 B：Momentum / Nesterov 相比 SGD 的加速 —— 与随之而来的震荡代价 ----
steps_b = 60
lr_b = 0.008
sgd_traj = [x0.copy()]
xy = x0.copy()
for _ in range(steps_b):
    xy = xy - lr_b * grad_fn(xy)
    sgd_traj.append(xy.copy())
sgd_traj = np.array(sgd_traj)

def trajectory(runner, **kw):
    xy = x0.copy(); out = [xy.copy()]
    return out

def momentum_traj(lr, steps, mu=0.9, nesterov=False):
    xy = x0.copy(); v = np.zeros_like(xy); out = [xy.copy()]
    for _ in range(steps):
        g = grad_fn(xy + mu * v) if nesterov else grad_fn(xy)
        v = mu * v - lr * g
        xy = xy + v
        out.append(xy.copy())
    return np.array(out)

mom_traj = momentum_traj(lr_b, steps_b, nesterov=False)
nes_traj = momentum_traj(lr_b, steps_b, nesterov=True)

def sign_changes(seq):
    s = np.sign(seq); s = s[s != 0]
    return int(np.sum(s[1:] != s[:-1]))

def loss(xy, a=1.0, b=100.0):
    return 0.5 * (a * xy[0] ** 2 + b * xy[1] ** 2)

loss_sgd, loss_mom, loss_nes = loss(sgd_traj[-1]), loss(mom_traj[-1]), loss(nes_traj[-1])
sc_sgd, sc_mom, sc_nes = sign_changes(sgd_traj[:, 1]), sign_changes(mom_traj[:, 1]), sign_changes(nes_traj[:, 1])

print(f'SGD       final loss={loss_sgd:.5f}   y方向变号次数={sc_sgd}')
print(f'Momentum  final loss={loss_mom:.5f}   y方向变号次数={sc_mom}')
print(f'Nesterov  final loss={loss_nes:.5f}   y方向变号次数={sc_nes}')

assert loss_mom < loss_sgd, 'Momentum 应比 SGD 收敛得更好（低曲率方向被加速）'
assert loss_nes < loss_mom, 'Nesterov 的前瞻修正应进一步改善'
assert sc_mom > sc_sgd, 'Momentum 的加速是有代价的：陡峭方向出现了震荡（变号次数增多）'
print('\\n✅ 验证：动量法用"陡峭方向出现震荡"换来了"低曲率方向更快收敛"——这正是它的权衡。')"""),

    md("""## 2 · AdamW 的解耦衰减 vs Adam 的 L2：量化衰减强度的偏差

构造两个参数：一个历史梯度方差大（$v_{\\text{big}}$），一个历史梯度方差小（$v_{\\text{small}}$）。
假设当前真实任务梯度为 0（只看"权重衰减"这一项单独的效果），比较两种做法让参数收缩了多少。"""),

    code("""def adam_decay_step(x, v_prior, wd, lr, beta1=0.9, beta2=0.999, eps=1e-8, t=1000, decoupled=False):
    \"\"\"单步：任务梯度=0，只看权重衰减项的效果；t 取较大值使 bias correction≈1，避免干扰对比。\"\"\"
    if decoupled:
        decay_update = lr * wd * x                 # AdamW：直接作用在参数上，与 v 无关
        return x - decay_update
    g_reg = wd * x                                   # Adam+L2：正则项被当成梯度的一部分
    m = (1 - beta1) * g_reg
    v = beta2 * v_prior + (1 - beta2) * g_reg ** 2   # v_prior 远大于 g_reg^2 时几乎不变
    mhat = m / (1 - beta1 ** t)
    vhat = v / (1 - beta2 ** t)
    return x - lr * mhat / (np.sqrt(vhat) + eps)

wd, lr = 0.01, 0.1
x_start = 1.0
v_big, v_small = 1.0, 1e-4     # 一个"历史梯度方差大"的参数、一个"历史梯度方差小"的参数

x1_l2  = adam_decay_step(x_start, v_big,   wd, lr, decoupled=False)
x2_l2  = adam_decay_step(x_start, v_small, wd, lr, decoupled=False)
x1_adw = adam_decay_step(x_start, v_big,   wd, lr, decoupled=True)
x2_adw = adam_decay_step(x_start, v_small, wd, lr, decoupled=True)

shrink1_l2, shrink2_l2 = (x_start - x1_l2) / x_start, (x_start - x2_l2) / x_start
shrink1_adw, shrink2_adw = (x_start - x1_adw) / x_start, (x_start - x2_adw) / x_start

print(f'Adam+L2   ：v_big 收缩比例={shrink1_l2:.3e}   v_small 收缩比例={shrink2_l2:.3e}   '
      f'两者相差 {shrink2_l2/shrink1_l2:.1f} 倍')
print(f'AdamW     ：v_big 收缩比例={shrink1_adw:.3e}   v_small 收缩比例={shrink2_adw:.3e}   '
      f'两者相差 {shrink2_adw/shrink1_adw:.4f} 倍')

assert shrink2_l2 / shrink1_l2 > 50, 'Adam+L2 下，梯度历史方差小的参数应被过度衰减（相差应远大于1）'
assert abs(shrink2_adw / shrink1_adw - 1.0) < 1e-6, 'AdamW 的衰减率必须与 v 无关，两者应完全相等'
assert np.isclose(shrink1_adw, lr * wd) and np.isclose(shrink2_adw, lr * wd), 'AdamW 的收缩比例应恒等于 lr*wd'
print('\\n✅ 验证：Adam+L2 的衰减强度被 v 缩放（相差 100 倍量级），AdamW 对所有参数统一衰减率 lr·wd。')"""),

    md("""## 3 · Warmup 为什么必要：Adam 首步更新幅度与训练早期梯度范数"""),

    code("""# ---- 现象 1：Adam 在 t=1 时，更新幅度几乎恒为 lr，与真实梯度的量级无关 ----
def adam_first_step(g1, lr=1.0, beta1=0.9, beta2=0.999, eps=1e-8):
    m = (1 - beta1) * g1
    v = (1 - beta2) * g1 ** 2
    mhat = m / (1 - beta1)      # t=1
    vhat = v / (1 - beta2)
    return lr * mhat / (np.sqrt(vhat) + eps)

print(f\"{'|g1|':>10} {'update':>10} {'update/lr':>10}\")
for g1 in [1e-3, 1e-1, 1.0, 10.0, 1000.0]:
    u = adam_first_step(g1, lr=1.0)
    print(f'{g1:>10} {u:>10.6f} {u/1.0:>10.6f}')
    assert abs(u - 1.0) < 0.02, f'g1={g1} 时首步更新幅度应仍接近 lr(=1.0)'
print('\\n✅ 验证：无论真实梯度是 1e-3 还是 1e3，Adam 第一步的更新幅度都约等于学习率本身——'
      '这是一次"盲目的满幅步"，warmup 就是用来压小它的。')"""),

    code("""# ---- 现象 2：在一个简单非线性问题上，有无 warmup 时训练早期梯度范数的差异 ----
def grad_quartic(x):
    return 4 * x ** 3            # f(x)=x^4，远离 0 的区域梯度增长很快（模拟"走远了梯度暴涨"的损失面）

def adam_run(x0, lr_base, steps, warmup=0, beta1=0.9, beta2=0.999, eps=1e-8):
    x = x0; m = 0.0; v = 0.0
    grad_norms = []
    for t in range(1, steps + 1):
        g = grad_quartic(x)
        grad_norms.append(abs(g))
        lr_t = lr_base * min(1.0, t / warmup) if warmup > 0 else lr_base
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g ** 2
        mhat = m / (1 - beta1 ** t)
        vhat = v / (1 - beta2 ** t)
        x = x - lr_t * mhat / (np.sqrt(vhat) + eps)
        if abs(x) > 1e6:
            break
    return x, grad_norms

x_final_no, gn_no = adam_run(0.1, lr_base=0.5, steps=30, warmup=0)
x_final_yes, gn_yes = adam_run(0.1, lr_base=0.5, steps=30, warmup=10)

max_no, max_yes = max(gn_no), max(gn_yes)
print(f'无 warmup: 最终 x={x_final_no:.4f}   全程最大梯度范数={max_no:.4f}')
print(f'有 warmup: 最终 x={x_final_yes:.4f}   全程最大梯度范数={max_yes:.4f}')
print(f'无 warmup / 有 warmup 的最大梯度范数比 = {max_no/max_yes:.2f}')

assert max_no > max_yes * 10, '不加 warmup 时，早期大步长把 x 推离原点导致梯度暴涨，应显著大于有 warmup 的情形'
print('\\n✅ 验证：没有 warmup 时，第一次满幅步就把参数推到了梯度陡增的区域，形成"早期不稳定"的正反馈。')"""),

    md("""## 4 · Xavier vs He：20 层前向传播的激活方差追踪"""),

    code("""def forward_track(width=256, depth=20, batch=512, gain=1.0, activation='relu', seed=0):
    r = np.random.default_rng(seed)
    x = r.standard_normal((batch, width))
    variances = [float(np.var(x))]
    for _ in range(depth):
        std = np.sqrt(gain / width)          # fan_in = width
        W = r.standard_normal((width, width)) * std
        z = x @ W
        x = np.maximum(z, 0) if activation == 'relu' else z
        variances.append(float(np.var(x)))
    return variances

v_xavier_relu = forward_track(gain=1.0, activation='relu')      # Xavier 配 ReLU：错误搭配
v_he_relu = forward_track(gain=2.0, activation='relu')          # He 配 ReLU：正确搭配
v_xavier_linear = forward_track(gain=1.0, activation='linear')  # Xavier 配线性：正确搭配

ratio_xavier_relu = v_xavier_relu[-1] / v_xavier_relu[0]
ratio_he_relu = v_he_relu[-1] / v_he_relu[0]
ratio_xavier_linear = v_xavier_linear[-1] / v_xavier_linear[0]

print(f'Xavier(gain=1)+ReLU   : 第0层方差={v_xavier_relu[0]:.4f}  第20层方差={v_xavier_relu[-1]:.6f}  比值={ratio_xavier_relu:.3e}')
print(f'He(gain=2)+ReLU       : 第0层方差={v_he_relu[0]:.4f}  第20层方差={v_he_relu[-1]:.4f}  比值={ratio_he_relu:.4f}')
print(f'Xavier(gain=1)+线性   : 第0层方差={v_xavier_linear[0]:.4f}  第20层方差={v_xavier_linear[-1]:.4f}  比值={ratio_xavier_linear:.4f}')

assert ratio_xavier_relu < 1e-3, 'Xavier 配 ReLU 应导致深层激活方差指数级坍缩'
assert 0.2 < ratio_he_relu < 5.0, 'He 配 ReLU 应把方差维持在同一量级'
assert 0.3 < ratio_xavier_linear < 3.0, 'Xavier 配线性激活本就该保持方差'
print('\\n✅ 验证：用错初始化(Xavier+ReLU)会让 20 层后的激活值只剩初始的千分之一以下——'
      '这正是"配错激活函数的初始化"这个踩雷点的真实数值证据。')"""),

    md("""## 5 · 损失函数的梯度形状：Huber / Focal / Label Smoothing"""),

    code("""# ---- Huber vs MSE vs MAE 的梯度形状 ----
def huber_grad(e, delta=1.0):
    return np.where(np.abs(e) <= delta, e, delta * np.sign(e))

errors = np.array([-5.0, -2.0, -0.5, 0.0, 0.5, 2.0, 5.0])
mse_grad = errors                      # d/de [0.5 e^2] = e
mae_grad = np.sign(errors)             # d/de |e| = sign(e)
hub_grad = huber_grad(errors, delta=1.0)

print('errors        :', errors)
print('MSE   grad(=e):', mse_grad)
print('MAE   grad    :', mae_grad)
print('Huber grad(δ=1):', hub_grad)

assert np.allclose(mse_grad, errors)
assert np.allclose(mae_grad, np.sign(errors))
assert np.allclose(hub_grad, np.array([-1.0, -1.0, -0.5, 0.0, 0.5, 1.0, 1.0]))
print('\\n✅ 验证：|e|<=delta 时 Huber 退化为 MSE 的梯度（e 本身），|e|>delta 时退化为 MAE 的有界梯度（±delta）。')"""),

    code("""# ---- CE vs Focal Loss 的梯度衰减（数值微分，二分类，target=1）----
def sigmoid(z):
    return 1 / (1 + np.exp(-z))

def ce_loss(z, y=1.0):
    p = np.clip(sigmoid(z), 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))

def focal_loss(z, y=1.0, gamma=2.0):
    p = np.clip(sigmoid(z), 1e-12, 1 - 1e-12)
    pt = p if y == 1.0 else (1 - p)
    return -(1 - pt) ** gamma * np.log(pt)

def numgrad(f, z, eps=1e-5):
    return (f(z + eps) - f(z - eps)) / (2 * eps)

print(f\"{'z':>4} {'pt':>7} {'CE_grad':>10} {'Focal_grad':>11} {'比值':>8}\")
ratios = {}
for z in [-3, 0, 1, 3, 5]:
    p = sigmoid(z)
    g_ce = numgrad(lambda zz: ce_loss(zz, 1.0), z)
    g_fl = numgrad(lambda zz: focal_loss(zz, 1.0, 2.0), z)
    ratios[z] = g_fl / g_ce
    print(f'{z:>4} {p:>7.4f} {g_ce:>10.5f} {g_fl:>11.5f} {ratios[z]:>8.5f}')

assert ratios[5] < 0.01, '预测很自信且答对(z=5)时，Focal 梯度应被压制到 CE 的百分之一以下'
assert ratios[-3] > 0.5, '预测严重出错(z=-3)的难例，Focal 梯度不应被过度压制'
print('\\n✅ 验证：Focal 对"自信且答对"的样本梯度衰减极快，对难例梯度基本不打折——这就是"难例加权"的数值证据。')"""),

    code("""# ---- Label Smoothing：给"越来越自信"踩刹车（sigmoid+BCE 对 logit 的梯度 = p - y）----
def bce_grad_logit(z, y):
    return sigmoid(z) - y

eps_ls = 0.1
y_hard = 1.0
y_smooth = 1 - eps_ls / 2     # 二分类下 label smoothing 目标: (1-eps)*1 + eps*0.5

z_probe = [0, 1, 2, 3, 4, 5]
hard_grads = [bce_grad_logit(z, y_hard) for z in z_probe]
smooth_grads = [bce_grad_logit(z, y_smooth) for z in z_probe]

for z, gh, gs in zip(z_probe, hard_grads, smooth_grads):
    print(f'z={z:>2}  p={sigmoid(z):.4f}  hard_grad={gh:+.5f}  smooth_grad={gs:+.5f}')

assert all(g < 0 for g in hard_grads), '硬标签下梯度应恒为负，持续鼓励 logit 增大（永不满足）'
assert smooth_grads[0] < 0 and smooth_grads[-1] > 0, 'label smoothing 下梯度应在 p 超过 y_smooth 后变号（踩刹车）'
z_cross = np.log(y_smooth / (1 - y_smooth))
assert 2.5 < z_cross < 3.5
print(f'\\n✅ 验证：label smoothing 让梯度在 z≈{z_cross:.2f}（p≈{y_smooth}）处变号，'
      f'从"继续推高置信度"变成"往回拉"——硬标签下这件事永远不会发生。')"""),

    md("""## ✏️ 练习 1：AdamW 与 Adam+L2 的衰减比率函数

实现 `l2_vs_decoupled_ratio(v_big, v_small, wd, lr, beta1=0.9, t=1000)`，
返回 `(ratio_l2, ratio_decoupled)`：
- `ratio_l2` = Adam+L2 下 `v_small` 参数的收缩比例 / `v_big` 参数的收缩比例（应远大于 1）
- `ratio_decoupled` = AdamW 下同样的比值（应恒等于 1.0，因为与 v 无关）

复用第 2 节已经定义的 `adam_decay_step`。"""),

    code("""def l2_vs_decoupled_ratio(v_big, v_small, wd, lr, beta1=0.9, t=1000):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
r_l2, r_dec = l2_vs_decoupled_ratio(1.0, 1e-4, 0.01, 0.1)
print(f'ratio_l2={r_l2:.2f}   ratio_decoupled={r_dec:.6f}')
assert r_l2 > 50, r_l2
assert abs(r_dec - 1.0) < 1e-6, r_dec
r_l2_b, r_dec_b = l2_vs_decoupled_ratio(4.0, 1e-2, 0.02, 0.2)
assert r_l2_b > 1.0
assert abs(r_dec_b - 1.0) < 1e-6
print('✅ 练习 1 通过：AdamW 的衰减率与参数的历史梯度方差无关，Adam+L2 不是。')"""),

    md("""## ✏️ 练习 2：Adam 首步更新幅度的普适性

实现 `adam_first_step_magnitude(g1, lr=1.0, beta1=0.9, beta2=0.999, eps=1e-8)`，
返回 Adam 在 $t=1$ 时对某个梯度值 `g1` 的更新幅度（标量，取绝对值）。

要点：$t=1$ 时的 bias correction 恰好抵消掉 $(1-\\beta_1)$ 与 $(1-\\beta_2)$，
使得更新幅度约等于 $\\eta\\cdot\\mathrm{sign}(g_1)$ 的量级。"""),

    code("""def adam_first_step_magnitude(g1, lr=1.0, beta1=0.9, beta2=0.999, eps=1e-8):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
for g1 in [1e-4, 1e-2, 1.0, 100.0, 1e4]:
    u = adam_first_step_magnitude(g1, lr=0.3)
    assert abs(u - 0.3) < 0.3 * 0.05, (g1, u)
    print(f'g1={g1:<10} -> update={u:.6f}  (目标 lr=0.3)')
print('✅ 练习 2 通过：跨 8 个数量级的梯度，首步更新幅度都锁定在 lr 附近。')"""),

    md("""## ✏️ 练习 3：He / Xavier 的方差公式反推

实现 `required_gain(activation)`，返回让方差在一次线性层后保持不变所需的 `gain`
（其中 $\\mathrm{Var}(W)=\\mathrm{gain}/\\text{fan\\_in}$）：
- `'relu'` → 需要补偿 ReLU 砍掉一半激活值 → `gain = 2.0`
- `'linear'` / `'tanh'` → 不需要补偿 → `gain = 1.0`

再实现 `layer_std(fan_in, activation)` = $\\sqrt{\\mathrm{gain}/\\text{fan\\_in}}$。"""),

    code("""def required_gain(activation):
    # TODO
    raise NotImplementedError

def layer_std(fan_in, activation):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert required_gain('relu') == 2.0
assert required_gain('linear') == 1.0
assert required_gain('tanh') == 1.0
assert np.isclose(layer_std(256, 'relu'), np.sqrt(2 / 256))
assert np.isclose(layer_std(256, 'linear'), np.sqrt(1 / 256))
assert layer_std(256, 'relu') > layer_std(256, 'linear'), 'He 的标准差应比 Xavier 大（因为要补偿 ReLU 打对折）'
print('layer_std(256, relu)  =', layer_std(256, 'relu'))
print('layer_std(256, linear)=', layer_std(256, 'linear'))
print('✅ 练习 3 通过：He 比 Xavier 多一个恰好 sqrt(2) 倍的标准差，用来补偿 ReLU 砍掉的那一半方差。')"""),

    md("""## ✏️ 练习 4：Label Smoothing 的梯度变号临界点

实现 `label_smoothing_crossover(eps, num_classes=2)`，返回二分类 sigmoid+BCE 梯度
由负变正的临界 logit $z^\\*=\\log\\big(\\dfrac{y_s}{1-y_s}\\big)$，其中
$y_s = (1-\\epsilon) + \\epsilon/\\text{num\\_classes}$。"""),

    code("""def label_smoothing_crossover(eps, num_classes=2):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
z_star = label_smoothing_crossover(0.1, num_classes=2)
assert 2.5 < z_star < 3.5, z_star
p_star = sigmoid(z_star)
assert abs(p_star - 0.95) < 1e-6, p_star     # y_smooth = 1-0.1/2 = 0.95
# eps 越大，天花板越低，交叉点应越靠前（越小的 z 就会触发刹车）
z_star_big_eps = label_smoothing_crossover(0.4, num_classes=2)
assert z_star_big_eps < z_star
print(f'eps=0.1 -> z*={z_star:.4f} (p*={p_star:.4f})')
print(f'eps=0.4 -> z*={z_star_big_eps:.4f}')
print('✅ 练习 4 通过：eps 越大，"置信度天花板"越低，模型更早被拉回。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def l2_vs_decoupled_ratio(v_big, v_small, wd, lr, beta1=0.9, t=1000):
    x_start = 1.0
    x1_l2 = adam_decay_step(x_start, v_big, wd, lr, beta1=beta1, t=t, decoupled=False)
    x2_l2 = adam_decay_step(x_start, v_small, wd, lr, beta1=beta1, t=t, decoupled=False)
    x1_dec = adam_decay_step(x_start, v_big, wd, lr, beta1=beta1, t=t, decoupled=True)
    x2_dec = adam_decay_step(x_start, v_small, wd, lr, beta1=beta1, t=t, decoupled=True)
    shrink1_l2 = (x_start - x1_l2) / x_start
    shrink2_l2 = (x_start - x2_l2) / x_start
    shrink1_dec = (x_start - x1_dec) / x_start
    shrink2_dec = (x_start - x2_dec) / x_start
    return shrink2_l2 / shrink1_l2, shrink2_dec / shrink1_dec"""),

    code("""# 练习 2 参考答案
def adam_first_step_magnitude(g1, lr=1.0, beta1=0.9, beta2=0.999, eps=1e-8):
    m = (1 - beta1) * g1
    v = (1 - beta2) * g1 ** 2
    mhat = m / (1 - beta1)
    vhat = v / (1 - beta2)
    return abs(lr * mhat / (np.sqrt(vhat) + eps))"""),

    code("""# 练习 3 参考答案
def required_gain(activation):
    return 2.0 if activation == 'relu' else 1.0

def layer_std(fan_in, activation):
    return np.sqrt(required_gain(activation) / fan_in)"""),

    code("""# 练习 4 参考答案
def label_smoothing_crossover(eps, num_classes=2):
    y_s = (1 - eps) + eps / num_classes
    return np.log(y_s / (1 - y_s))"""),

    md("""---
## 🧪 真实工程胶囊：优化器/初始化/损失函数的选型速查 + 常见配置坑"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 优化器选型速查（面试可直接背的一句话版本）
# ══════════════════════════════════════════════════════════════════════
# □ CV 分类/检测 backbone 训练          -> SGD + Momentum(0.9) + cosine/step schedule + warmup
# □ Transformer（视觉或语言）           -> AdamW(beta1=0.9, beta2=0.999 或 0.95) + cosine + warmup
# □ 稀疏特征/推荐系统                   -> AdaGrad 或其变体（天然适合稀疏梯度）
# □ RNN/序列模型的历史遗留代码           -> RMSProp（AdaGrad 的"学习率死亡"问题在这里被绕开）
# □ 不确定用什么 -> 默认起手 AdamW，收敛快、对学习率不敏感、坑最少

# ══════════════════════════════════════════════════════════════════════
# B. Adam/AdamW 常见配置坑
# ══════════════════════════════════════════════════════════════════════
# 坑1: torch.optim.Adam(weight_decay=...) 做的是 L2（不是解耦衰减）
#      -> 要解耦衰减必须显式用 torch.optim.AdamW
# 坑2: BN/LayerNorm 的 weight 和 bias 不应该被 weight decay
#      -> 常见做法：把 1D 参数（norm 层的 gamma/beta、所有 bias）单独分组，weight_decay=0
# 坑3: 混合精度下，优化器状态 (m, v) 与 BN running stats 建议保留 fp32
#      -> 只有前向激活与梯度计算用 fp16/bf16

# ══════════════════════════════════════════════════════════════════════
# C. 初始化速查
# ══════════════════════════════════════════════════════════════════════
# ReLU/LeakyReLU/GELU(近似)      -> He/Kaiming: std = sqrt(2/fan_in)
# tanh/sigmoid/线性输出层         -> Xavier/Glorot: std = sqrt(2/(fan_in+fan_out))
# 残差分支的最后一层                -> 常见技巧：额外把该层权重初始化为 0 或很小
#                                    （让残差块初始时近似恒等映射，训练更稳，见 C64-03）

# ══════════════════════════════════════════════════════════════════════
# D. 混合精度速查
# ══════════════════════════════════════════════════════════════════════
# fp16 + 动态 loss scaling          -> 老一代 GPU（无原生 bf16 支持）的标准选择
# bf16（无需 loss scaling）         -> 新一代 GPU 的默认选择，工程更简单
# 排查"训练出现 NaN"的第一步        -> 检查是不是 loss scale 溢出，看 loss scale 是否被自动减半

# ══════════════════════════════════════════════════════════════════════
# E. 损失函数速查
# ══════════════════════════════════════════════════════════════════════
# 回归 + 数据干净                   -> MSE
# 回归 + 有离群点/标注噪声           -> Huber（检测框回归的 smooth-L1 是它的近亲，见 C54-02）
# 分类 + 类别平衡                   -> 标准 CE
# 分类 + 极度不平衡（检测里的背景/前景）-> Focal Loss
# 分类 + 担心过度自信/需要更好泛化    -> Label Smoothing（但会牺牲部分置信度可解释性，见 C64-04）

# ══════════════════════════════════════════════════════════════════════
# F. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 优化器的完整数学推导（收敛性证明、动量的物理类比）  -> C07 模块 05（本课不重复）
# · Focal Loss / GIoU 等检测专用损失的完整推导与实现     -> C54 模块 02
# · 归一化家族、残差连接、注意力机制                     -> C64 模块 03（下一站）
# · 校准、ROC/PR、A/B 测试                              -> C64 模块 04
'''
print(RECIPE)
for token in ['AdamW', 'He/Kaiming', 'loss scale', 'Focal Loss', 'C07 模块 05', 'C54 模块 02']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：优化器选型 / 配置坑 / 初始化 / 混合精度 / 损失函数 / 课程分工')"""),

    md("""### 小结

- **优化器不是背名字，是背「解决了前一个的什么问题、什么时候反而更差」**：Momentum 缓解震荡但可能超调；
  AdaGrad 自适应但学习率会"死掉"；RMSProp 修复了这一点；Adam 加上动量与偏差修正成为默认起手式；
  **AdamW 修复了 Adam 里 L2 正则被自适应分母不均匀缩放的 bug**——这是本模块面试价值最高的单点。
- **Warmup 不是玄学**：Adam 在训练早期（尤其 $t=1$）的更新幅度几乎恒为学习率本身，与真实梯度量级无关——
  这是一次"盲目的满幅步"，warmup 用来给它踩刹车，直到二阶矩估计变得可信。
- **He 比 Xavier 多的那个系数 2，是专门为 ReLU 砍掉一半激活值这件事补的**——配错组合
  （Xavier+ReLU）会让 20 层后的激活方差坍缩到初始值的千分之一以下。
- **批大小不是越大越好**：大 batch 降低了梯度噪声这个"隐式正则化"，需要配合线性缩放学习率 + warmup
  才能追平小 batch 的泛化表现。
- **损失函数选择是一道约束满足题**：离群值多选 Huber/MAE 不选 MSE；类别不平衡选 Focal 不选纯 CE；
  担心过度自信就上 Label Smoothing，但要知道它会牺牲部分置信度的可解释性。

下一站：**模块 03 · 深度学习架构问答** —— 卷积口算、归一化家族、残差连接、
注意力与 Transformer，同样是"60 秒讲清楚 + 接住追问"的打法。"""),
]
