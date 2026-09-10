# -*- coding: utf-8 -*-
"""C77 模块 03 · 时序一致性与自回归漂移。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（观测帧不是马尔可夫的）；模块 01（时间压缩与因果性）；"
                 "<strong>C41 模块 04</strong>（规划侧的复合误差）是本模块的对照——"
                 "那里的误差累积是<em>对抗性</em>的（优化找模型的洞），"
                 "本模块处理的是<em>分布性</em>的；"
                 "AR(1) 与谱半径的基本概念"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_temporal_drift.ipynb'
                       '（<strong>漂移不是必然的</strong>：误差按 $\\vert\\hat a\\vert^k$ 演化，'
                       '$\\vert\\hat a\\vert<1$ 时初始误差<em>会被遗忘</em> / '
                       '<strong>一步最小二乘对持续性的估计向下有偏</strong>'
                       '（$a{=}0.9, n{=}50$ 时 $\\hat a$ 中位数 $0.8835$）'
                       '$\\Rightarrow$ rollout 的稳态方差只有真值的 $\\mathbf{35\\%}$–$49\\%$ / '
                       '而 $a{=}0.995, n{=}30$ 时有 <strong>$28.6\\%$ 的拟合给出 '
                       '$\\vert\\hat a\\vert > 1$</strong>（那些会指数爆炸）/ '
                       '<strong>方差的均值 $1.4\\times10^{14}$ 而中位数 $8.93$</strong>）'),
    ("核心参考", "Ho et al., <em>Video Diffusion Models</em>（NeurIPS 2022，"
                 "以及其中的自回归长视频扩展）· "
                 "Harvey et al., <em>Flexible Diffusion Modeling of Long Videos</em>"
                 "（NeurIPS 2022，层次化 / 关键帧条件）· "
                 "Villegas et al., <em>Phenaki</em>（ICLR 2023，变长自回归视频）· "
                 "Marriott, Pope &amp; Stine, <em>Bias in Estimation of Autoregressive "
                 "Parameters</em>（Biometrika 1954 / Kendall 1954，$\\hat a$ 的向下偏差）· "
                 "Ross &amp; Bagnell, <em>DAgger</em>（AISTATS 2011，"
                 "自回归 rollout 的分布偏移，与 C59 的模仿学习一节呼应）· "
                 "本课程 <strong>C41 模块 04</strong>（规划侧的复合误差）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [

("law", "误差增长律：漂移不是必然的", "".join([
    P("「自回归生成的视频越往后越糟」是一句几乎无人反驳的话。"
      "但它<strong>作为一般命题是错的</strong>，而错在哪里决定了该怎么修。"),
    P("最简的自回归生成：学一个一步预测器 $\\hat x_{t+1} = \\hat a x_t$，然后反复代入自己的输出。"
      "如果初始帧带有误差 $\\delta$，那么 $k$ 步后的误差是 $\\vert\\hat a\\vert^k \\delta$："),
    TABLE(["$\\hat a$", "$1$ 步", "$10$ 步", "$50$ 步", "$200$ 步", "增长律"],
          [["$0.50$", "$0.5$", "$9.8\\times10^{-4}$", "$8.9\\times10^{-16}$",
            "$6.2\\times10^{-61}$", "<strong>收敛到 0</strong>"],
           ["$0.90$", "$0.9$", "$0.349$", "$5.2\\times10^{-3}$", "$7.1\\times10^{-10}$",
            "<strong>收敛到 0</strong>"],
           ["$0.99$", "$0.99$", "$0.904$", "$0.605$", "$0.134$", "<strong>收敛到 0</strong>"],
           ["$1.00$", "$1$", "$1$", "$1$", "$1$", "恒定"],
           ["$1.01$", "$1.01$", "$1.10$", "$1.64$", "$7.32$", "指数爆炸"],
           ["$1.05$", "$1.05$", "$1.63$", "$11.5$", "$1.7\\times10^{4}$", "指数爆炸"]]),
    CALLOUT("intuition", "稳定的动力学会遗忘错误",
            "$\\vert\\hat a\\vert < 1$ 时，<strong>任何单帧的错误都会被指数地遗忘</strong>。"
            "这不是一个近似说法——它是几何级数。"
            "所以「一帧生成得不好，后面就全毁了」在稳定动力学下不成立。"
            "而现实中的视频动力学在大多数尺度上<em>是</em>稳定的"
            "（物体最终会停下、光照会回到均值、镜头会稳住）。"),
    P("那为什么长视频确实会漂？因为真正累积的<strong>不是单条轨迹的误差，而是分布的错误</strong>。"
      "下面两节分别处理它的两种形态。"),
])),

("bias", "第一种形态：一步拟合系统性低估了持续性", "".join([
    P("训练一步预测器用的是<strong>教师强制</strong>（teacher forcing）："
      "输入真实的 $x_t$，预测真实的 $x_{t+1}$。"
      "这个目标函数有一个古老且精确的性质：<strong>它对自回归系数的估计向下有偏</strong>。"),
    MATH("E[\\hat a] - a \\approx -\\frac{1 + 3a}{n}"),
    P("（Kendall 1954 / Marriott–Pope 1954。$n$ 是训练序列长度。）"
      "notebook 在 $6000$ 次重复上量它："),
    TABLE(["真 $a$", "$n$", "$\\hat a$ 中位数", "$\\hat a$ 均值", "偏差（均值）",
           "理论 $-(1{+}3a)/n$"],
          [["$0.90$", "$50$", "$0.88350$", "$0.86709$", "$-0.03291$", "$-0.07400$"],
           ["$0.90$", "$200$", "$0.89576$", "$0.89181$", "$-0.00819$", "$-0.01850$"],
           ["$0.90$", "$1000$", "$0.89944$", "$0.89861$", "$-0.00139$", "$-0.00370$"],
           ["$0.98$", "$50$", "$0.96745$", "$0.95231$", "$-0.02769$", "$-0.07880$"],
           ["$0.98$", "$1000$", "$0.97915$", "$0.97826$", "$-0.00174$", "$-0.00394$"]]),
    P("理论式给出的是量级与符号，实测偏差约是它的一半——"
      "而<strong>符号与 $1/n$ 的标度是稳定的</strong>。"),
    H3("后果：生成的视频变静止，而不是爆炸"),
    P("$\\hat a < a$ 意味着学到的动力学比真实的<strong>更快衰减</strong>。"
      "把它拿去 rollout，稳态方差就会偏小："),
    TABLE(["真 $a$", "$n$", "真稳态方差", "rollout 方差（中位数）", "比值"],
          [["$0.90$", "$50$", "$5.263$", "$3.830$", "$0.728$"],
           ["$0.90$", "$1000$", "$5.263$", "$4.547$", "$0.864$"],
           ["$0.98$", "$50$", "$25.253$", "$8.926$", "$\\mathbf{0.354}$"],
           ["$0.98$", "$200$", "$25.253$", "$10.974$", "$0.435$"],
           ["$0.98$", "$1000$", "$25.253$", "$12.417$", "$0.492$"]]),
    P("$a{=}0.98$ 时 rollout 的运动能量只有真实的 <strong>$35\\%$–$49\\%$</strong>。"),
    CALLOUT("danger", "「越往后越糊、越静止」有一个不需要神经网络的解释",
            "这个现象通常被归因于「模型能力不足」或「误差累积」。"
            "但本节说明：<strong>即使模型类完全正确、即使训练完美收敛到该目标的最优解，"
            "一步拟合本身就会低估动力学的持续性</strong>，"
            "于是 rollout 过度衰减、运动逐渐消失。"
            "这不是能力问题，是<em>目标函数</em>问题——"
            "而它也解释了为什么「多步/rollout 损失」「scheduled sampling」这类做法有用："
            "它们改的正是这个目标。"),
])),

("bimodal", "第二种形态：少数模型会爆炸，而均值指标会同时错判两者", "".join([
    P("上一节看的是中位数。$\\hat a$ 还有方差，而 $\\hat a$ 一旦超过 $1$，rollout 就<strong>指数爆炸</strong>。"
      "notebook 量出这个尾部有多重："),
    TABLE(["真 $a$", "$n$", "$\\hat a$ 中位数", "$P(\\vert\\hat a\\vert > 1)$",
           "$P(\\vert\\hat a\\vert > 1.01)$"],
          [["$0.900$", "$30$", "$0.87435$", "$1.12\\%$", "$0.67\\%$"],
           ["$0.900$", "$100$", "$0.89175$", "$0.00\\%$", "$0.00\\%$"],
           ["$0.980$", "$30$", "$0.96213$", "$16.52\\%$", "$9.73\\%$"],
           ["$0.980$", "$50$", "$0.96745$", "$10.00\\%$", "$3.85\\%$"],
           ["$0.995$", "$30$", "$0.98727$", "$\\mathbf{28.60\\%}$", "$14.40\\%$"],
           ["$0.995$", "$200$", "$0.99180$", "$9.58\\%$", "$0.13\\%$"],
           ["$0.995$", "$1000$", "$0.99421$", "$0.15\\%$", "$0.00\\%$"]]),
    P("真动力学越接近临界（$a \\to 1$）、训练序列越短，不稳定的拟合就越多。"
      "$a{=}0.995, n{=}30$ 时<strong>超过四分之一的模型会爆炸</strong>。"),
    H3("这两种失效的症状完全相反"),
    ASCII("""
                        一步拟合的 â 分布
                              |
              +---------------+---------------+
              |                               |
      多数：â < a （中位数）            尾部：â > 1
              |                               |
      rollout 过度衰减                  rollout 指数爆炸
              |                               |
      症状：越往后越静止/糊              症状：画面崩坏、数值溢出
              |                               |
              +-------------+-----------------+
                            |
                  而**均值指标同时错判两者**
""".strip("\n")),
    TABLE(["真 $a$", "$n$", "真稳态方差", "rollout 方差<strong>中位数</strong>",
           "rollout 方差<strong>均值</strong>"],
          [["$0.90$", "$50$", "$5.263$", "$3.830$", "$4.721$"],
           ["$0.98$", "$50$", "$25.253$", "$\\mathbf{8.926}$",
            "$\\mathbf{1.408\\times10^{14}}$"],
           ["$0.98$", "$200$", "$25.253$", "$10.974$", "$1.468\\times10^{1}$"],
           ["$0.98$", "$1000$", "$25.253$", "$12.417$", "$1.519\\times10^{1}$"]]),
    P("$a{=}0.98, n{=}50$ 那一行：<strong>中位数 $8.93$，均值 $1.4\\times10^{14}$</strong>——"
      "差 $16$ 个数量级。$10\\%$ 的爆炸样本完全主导了均值。"),
    CALLOUT("warn", "所以长视频指标必须报分位数",
            "在一批生成的长视频上报<strong>平均</strong>任何指标"
            "（FVD、逐帧 PSNR、运动幅度）都会被少数崩坏样本主导，"
            "而那些样本本来应该被单独拎出来看。"
            "可操作的做法：报<strong>中位数 + 崩坏率</strong>"
            "（例如「$P(\\text{任一帧的能量} > 10\\times$ 训练分布$)$」），"
            "这两个数分别对应上面那张图的两支。"),
])),

("distribution", "分布的错误不会自我纠正", "".join([
    P("上面两节讲的是 $\\hat a$（动力学的持续性）。"
      "还有一个量同样会错，而且它的错误<strong>完全不随时间衰减</strong>：噪声尺度。"),
    P("真动力学 $a{=}0.95$、真噪声 $\\text{sd}{=}1.0$，真稳态 $\\text{sd} = 1/\\sqrt{1-a^2} = 3.2026$。"
      "如果模型用错的噪声尺度 rollout："),
    TABLE(["模型噪声 sd", "第 $5$ 步的 sd", "第 $50$ 步", "第 $500$ 步",
           "稳态 sd / 真值"],
          [["$0.50$", "$2.674$", "$1.599$", "$1.605$", "$\\mathbf{0.5012}$"],
           ["$0.80$", "$2.962$", "$2.545$", "$2.568$", "$0.8020$"],
           ["$1.00$", "$3.206$", "$3.179$", "$3.210$", "$1.0024$"],
           ["$1.20$", "$3.481$", "$3.813$", "$3.852$", "$1.2029$"],
           ["$2.00$", "$4.779$", "$6.353$", "$6.421$", "$2.0049$"]]),
    P("比值恰好等于噪声尺度的比值（$0.5012$、$0.8020$、$1.2029$、$2.0049$）——"
      "因为稳态 sd 与噪声 sd 成正比。"),
    DUAL("单条轨迹的误差可以被遗忘（第 1 节），"
         "但<strong>分布的错误是持久的</strong>："
         "噪声尺度低估让生成越来越静止，高估让它越来越乱，"
         "而两者都不会「收敛回正确分布」——因为错的是<em>不动点本身</em>。",
         "对 $x_{t+1} = a x_t + \\varepsilon_t$，$\\varepsilon \\sim N(0, \\sigma^2)$，"
         "稳态分布是 $N(0, \\sigma^2/(1-a^2))$。"
         "误差的遗忘（第 1 节）说的是<strong>转移算子</strong>的收缩性；"
         "而不动点由 $(a, \\sigma)$ 共同决定。"
         "收缩性保证「初值不重要」，它<em>不</em>保证「收敛到正确的分布」——"
         "两件事经常被混为一谈。"),
    CALLOUT("intuition", "这解释了两个常见现象",
            "扩散模型在长 rollout 上「越来越糊」通常被解释为误差累积。"
            "更准确的说法是：<strong>采样温度 / 引导强度在自回归 rollout 里的作用被放大了</strong>——"
            "它直接决定了不动点的方差。"
            "CFG 强度偏高会让画面越来越「锐利到失真」，偏低会越来越糊，"
            "而这两个方向都<em>不是</em>误差累积，是不动点选错了。"
            "而修法也不同：误差累积要改训练目标（第 2 节），"
            "不动点错要改采样参数。"),
])),

("diffusion", "在扩散模型里，这两支各对应什么旋钮", "".join([
    P("前三节用 AR(1) 做最小模型。放回扩散视频生成的语境，"
      "两支失效各自对应一组<strong>具体的、可调的</strong>东西——而它们不重叠。"),
    TABLE(["本课的量", "扩散里的对应物", "调它会怎样"],
          [["$\\hat a$（动力学的持续性）", "时间层学到的帧间依赖强度",
            "只能靠训练目标改（多步损失 / 更长的训练窗口）"],
           ["$\\vert\\hat a\\vert > 1$（不稳定）", "自回归段间的能量放大",
            "谱范数约束 / 更密的锚帧 / 段间重归一化"],
           ["噪声尺度 $\\sigma$（不动点）",
            "<strong>采样温度、CFG 强度、噪声调度的末端</strong>",
            "直接决定生成分布的方差 —— 训练完之后还能调"],
           ["起始分布", "第一段的条件（首帧 / 文本）",
            "第 1 节说明它会被指数遗忘 —— 影响最小"]]),
    P("第三行是<strong>唯一在训练之后还能调的</strong>，而它恰好对应第 4 节那一支。"
      "所以有一条直接可用的分诊规则："),
    ASCII("""
   长视频质量下降
        |
   平稳吗？（第 4 节的批级诊断）
        |
   +----+----------------------+
   |                           |
  平稳                      不平稳
   |                           |
  不动点错                  还在累积
   |                           |
  调采样参数                 改训练目标 / 加锚帧
  （CFG 强度 / 温度 /        （多步损失 / 谱约束 /
    噪声调度末端）             更密的锚帧）
   |                           |
  **训练后就能试**          **需要重训**
""".strip("\n")),
    CALLOUT("intuition", "为什么这条分诊值得先做",
            "两支的修法在<strong>成本上差几个数量级</strong>："
            "调采样参数是分钟级的，改训练目标是天级的。"
            "而第 4 节的诊断（批级平稳性 + 能量比）只需要一批已经生成好的视频，"
            "不需要任何额外的训练或标注。"
            "<strong>所以它应该是遇到「长视频质量下降」时的第一步，而不是最后一步。</strong>"),
    H3("CFG 强度在自回归 rollout 里被放大"),
    P("单段生成里 CFG 强度影响的是<em>这一段</em>的锐度。"
      "而在自回归 rollout 里，每一段的输出成为下一段的条件，"
      "于是 CFG 造成的分布偏移<strong>进入了不动点</strong>："),
    P("按第 4 节的机制：如果 CFG 让每段的方差相对真实分布乘了 $\\kappa$，"
      "那么 rollout 的稳态方差就被乘 $\\kappa$——"
      "<strong>不是 $\\kappa^{段数}$（那会是累积），而是一个固定的 $\\kappa$</strong>"
      "（因为它改的是不动点，而不动点不随时间累积）。"
      "这个区别有实践含义：<em>它意味着「越往后越锐」这个现象如果真的在累积，"
      "那它<strong>不是</strong> CFG 造成的，而是 $\\vert\\hat a\\vert>1$ 那一支</em>。"),
    CALLOUT("paper", "这一节没有 notebook 实验，理由要说清",
            "验证「CFG 在扩散视频 rollout 里如何影响不动点」需要一个真实的视频扩散模型。"
            "本课能给的是<strong>机制层面的对应</strong>："
            "第 4 节已经量出「噪声尺度错 $\\Rightarrow$ 稳态方差按同一比例错，且不随时间累积」"
            "（比值 $0.5012 / 0.8020 / 1.2029 / 2.0049$，与噪声比值逐位对应），"
            "而 CFG 在采样里的作用正是改变有效噪声尺度。"
            "把这两件事连起来是一次<em>推断</em>而不是一次测量——所以本课把它标成推断。"),
])),

("teacher", "教师强制为什么必然产生这个偏差", "".join([
    P("第 2 节给出了偏差的数值与经典公式。这一节说清它<strong>为什么必然</strong>——"
      "因为这决定了哪些修法在原理上可能有效。"),
    P("一步最小二乘的解是"),
    MATH("\\hat a = \\frac{\\sum_t x_t x_{t+1}}{\\sum_t x_t^2}"),
    P("分子分母<strong>共享同一批 $x_t$</strong>，所以它们相关。"
      "而分母 $\\sum x_t^2$ 在同一份数据上恰好是<em>偏大</em>的方向与"
      "分子偏大的方向相关——于是比值系统性偏小。"
      "更直观的说法：<strong>有限长度的序列「看起来」比真实过程更快回到均值</strong>，"
      "因为端点效应（序列必须在某处开始和结束）压低了观测到的持续性。"),
    DUAL("想象一个几乎不衰减的过程（$a$ 接近 $1$）。"
         "在一段有限的观测里，它看起来像一条缓慢漂移的曲线。"
         "而拟合会把「漂移」的一部分解释成「均值回归」——"
         "因为在这一段里它确实<em>回到</em>了某个水平（那个水平就是这一段的样本均值）。"
         "样本均值本身是随机的，而拟合把它当成了真均值。",
         "严格地说：$\\hat a$ 的偏差主要来自「用样本均值代替真均值」。"
         "去均值后的序列 $x_t - \\bar x$ 的自相关被系统性压低，"
         "因为 $\\bar x$ 本身随 $x_t$ 变动。"
         "这也解释了为什么偏差 $\\propto 1/n$："
         "$\\bar x$ 的方差 $\\propto 1/n_{\\text{eff}}$，"
         "而 $n_{\\text{eff}} \\propto n(1-a^2)$。"),
    CALLOUT("paper", "哪些修法在原理上可能有效",
            "既然偏差来自<strong>有限样本</strong>（而不是目标函数的形状），"
            "那么：<strong>更长的训练序列</strong>有效（偏差 $\\propto 1/n$，实测跨 $20$ 倍 $n$ 缩小约 $20$ 倍）；"
            "<strong>偏差校正</strong>有效（把 $-(1{+}3\\hat a)/n$ 加回去）；"
            "而<strong>多步损失不必然有效</strong>——练习 1 实测它不修这个偏差。"
            "这解释了为什么视频模型的训练窗口长度是一个比它看起来更重要的超参："
            "它同时决定了可观测性（模块 00）与这个偏差的大小。"),
])),

("bridge03", "四节的关系", "".join([
    P("把前四节的关系说清，因为它们不是并列的四个现象，而是一条链："
      "<strong>第 1 节</strong>说明单条轨迹的误差会被遗忘（所以「必然漂移」是错的）；"
      "<strong>第 2 节</strong>指出真正累积的是<em>目标函数</em>的偏差（运动能量不足）；"
      "<strong>第 3 节</strong>指出这个偏差还有一条方差很大的尾巴（少数模型爆炸），"
      "而两支的症状<em>相反</em>；"
      "<strong>第 4 节</strong>说明分布的错误（不动点）与前两者都不同——它完全不随时间衰减。"
      "下面的修法表就是按「修哪一支」组织的。"),
])),

("fixes", "四种修法，各修哪一支", "".join([
    TABLE(["做法", "机制", "修的是哪一支", "代价"],
          [["<strong>多步 / rollout 损失</strong>",
            "训练时就做 $k$ 步 rollout 并对全部步计损失",
            "第 2 节的<strong>目标函数偏差</strong>", "训练慢 $k$ 倍；梯度可能不稳"],
           ["<strong>scheduled sampling</strong>",
            "训练时按概率把输入换成模型自己的输出",
            "同上（更便宜的近似）", "引入偏差-方差的新超参"],
           ["<strong>关键帧 / 锚帧条件</strong>",
            "每 $m$ 步用一个真实（或先生成的）锚帧重置",
            "两支都截断（把 $k$ 上限压到 $m$）",
            "需要层次化生成；锚帧之间可能不连贯"],
           ["<strong>一次性生成整段</strong>",
            "不自回归，一个 forward 出全部 $T$ 帧",
            "两支<strong>都不存在</strong>（没有 rollout）",
            "代价 $\\propto T^2$（模块 00）；长度固定"]]),
    P("第三行和第四行值得对照：<strong>一次性生成把「漂移」这个问题整个删掉了</strong>，"
      "代价是模块 00 算过的 $(T/p_t)^2$。"
      "所以工业上的主流是<strong>层次化</strong>：一次性生成一小段（无漂移），"
      "然后用锚帧把小段拼成长视频（把漂移限制在段间）。"),
    ASCII("""
   纯自回归:      [f1]->[f2]->[f3]->...->[f100]     漂移累积 100 步
   一次性:        [f1 f2 ... f16]                   无漂移，但代价 (16)^2
   层次化:        [f1 ... f16] [f17 ... f32] ...    段内无漂移
                       ^锚帧      ^锚帧              段间漂移 = 段数（100/16 ≈ 6 步）
""".strip("\n")),
    P("notebook 的练习 3 把这个账算清：<strong>锚帧间隔 $m$ 让有效 rollout 步数从 $T$ 降到 $T/m$</strong>，"
      "而误差按 $\\vert\\hat a\\vert^{T/m}$ 而不是 $\\vert\\hat a\\vert^{T}$——"
      "在不稳定（$\\vert\\hat a\\vert > 1$）的情形下这是指数级的改善。"),
    P("表里第四行值得多说一句：<strong>一次性生成把「漂移」这个问题整个删掉了</strong>，"
      "而它的代价在模块 00 已经算清（$(T/p_t)^2$）。"
      "所以「自回归 vs 一次性」这个选择的本质是"
      "<em>用平方级的算力换掉一个不会报错的失效模式</em>——"
      "而本模块的四节正是在说清那个失效模式到底值多少算力。"),
    CALLOUT("paper", "本模块与 C41 模块 04 的分界",
            "C41-04 讲的是<strong>用模型规划</strong>时的复合误差："
            "那里的优化器会<em>主动</em>去找模型的错误，所以失效是<strong>对抗性</strong>的。"
            "本模块讲的是<strong>用模型生成</strong>："
            "没有优化器在对抗它，失效是<strong>分布性</strong>的（不动点错、目标函数偏）。"
            "<strong>同一个模型、同样的一步误差，两种用法的失效机制不同，修法也不同</strong>——"
            "模块 04 会把这两者放在同一个模型上直接对比（被动 $-13\\%$ vs 主动 $+251\\%$）。"),
])),
]

NB = [
md("""# C77 模块 03 · 时序一致性与自回归漂移

四件事：

1. **漂移不是必然的**：误差按 $|\\hat a|^k$ 演化，稳定动力学会**遗忘**错误；
2. **一步拟合系统性低估持续性** $\\Rightarrow$ rollout 方差只有真值的 35%–49%；
3. **少数模型会爆炸**（$a{=}0.995, n{=}30$ 时 28.6%），而**均值指标同时错判两支**；
4. **分布的错误不会自我纠正**（噪声尺度错 $\\Rightarrow$ 不动点错）。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import numpy as np

def ar1(a, n, seed, sig=1.0):
    '''AR(1) 序列，从稳态分布起始。'''
    r = np.random.default_rng(seed)
    x = np.zeros(n)
    x[0] = r.normal(0, sig / np.sqrt(max(1 - a*a, 1e-6)))
    for t in range(1, n):
        x[t] = a * x[t-1] + r.normal(0, sig)
    return x

def fit_a(x):
    '''一步最小二乘（= 教师强制训练的解析解）。'''
    return float(np.sum(x[:-1] * x[1:]) / np.sum(x[:-1]**2))

print('本模块用 AR(1) 当「视频动力学」的最小模型：')
print('  · 一步最小二乘 = 教师强制训练的解析最优解')
print('  · 自回归 rollout = 反复代入自己的输出')
print('两者都不需要神经网络就能复现「生成的视频越往后越静止」这个现象。')"""),

md("""## 1. 误差增长律：$|\\hat a|^k$

初始帧带误差 $\\delta$，$k$ 步后是 $|\\hat a|^k \\delta$。"""),

code("""print('   â      1 步       10 步        50 步       200 步      增长律')
for ah in (0.50, 0.90, 0.99, 1.00, 1.01, 1.05):
    row = [ah**k for k in (1, 10, 50, 200)]
    law = '收敛到 0' if ah < 1 else ('恒定' if ah == 1 else '指数爆炸')
    print(f'  {ah:5.2f}  ' + '  '.join(f'{v:10.4g}' for v in row) + f'   {law}')

# 数值验证：真的按几何级数走
def rollout_error(ah, delta, k):
    e = delta
    for _ in range(k):
        e = ah * e
    return abs(e)
for ah in (0.5, 0.9, 0.99, 1.01):
    for k in (10, 50):
        assert abs(rollout_error(ah, 1.0, k) - ah**k) < 1e-12 * max(1, ah**k)
print()
print('✅ 误差严格按几何级数 |â|^k 演化（这是恒等式，不是近似）')
print()
print('-> |â| < 1 时**任何单帧的错误都会被指数地遗忘**。')
print('   所以「一帧生成得不好，后面就全毁了」在稳定动力学下不成立。')
print('   而现实的视频动力学在多数尺度上是稳定的（物体会停、光照回均值、镜头稳住）。')
print()
print('   那长视频为什么确实会漂？因为真正累积的不是单条轨迹的误差，')
print('   而是**分布的错误** —— 见第 2、4 节。')"""),

md("""## 2. 一步拟合对持续性的估计向下有偏

$E[\\hat a] - a \\approx -(1+3a)/n$（Kendall 1954 / Marriott–Pope 1954）。"""),

code("""print('  真 a    n      â 中位数    â 均值     偏差(均值)   理论 -(1+3a)/n   实测/理论')
bias_tab = {}
for a in (0.90, 0.98):
    for n in (50, 200, 1000):
        ahs = np.array([fit_a(ar1(a, n, s)) for s in range(6000)])
        bias = ahs.mean() - a
        theo = -(1 + 3*a) / n
        bias_tab[(a, n)] = (float(np.median(ahs)), float(ahs.mean()), float(bias))
        print(f'  {a:5.2f}  {n:5d}   {np.median(ahs):+.5f}  {ahs.mean():+.5f}  '
              f'{bias:+.5f}     {theo:+.5f}      {bias/theo:8.3f}')
    print()

# 偏差为负、且按 1/n 缩小
for a in (0.90, 0.98):
    for n in (50, 200, 1000):
        assert bias_tab[(a, n)][2] < 0, f'a={a}, n={n}: 偏差应为负'
    b50, b1000 = bias_tab[(a, 50)][2], bias_tab[(a, 1000)][2]
    ratio = b50 / b1000
    print(f'  a={a}: 偏差从 n=50 的 {b50:+.5f} 缩到 n=1000 的 {b1000:+.5f}'
          f'（缩小 {ratio:.1f} 倍，n 比是 20 倍）')
    assert 8 < ratio < 40, f'偏差应大致按 1/n 缩小，实测 {ratio:.1f} 倍'

print()
print('✅ 偏差恒为负、且按 ~1/n 缩小 —— 符号与标度都与理论一致')
print('✅ 实测偏差约是理论式的一半（理论式给的是量级与符号）')"""),

code("""# 后果：rollout 的稳态方差偏小 —— 生成的视频变静止
def rollout_var(a, n, seeds=400, horizon=400, burn=200):
    '''在长度 n 的序列上拟合，然后 rollout，返回稳态方差的中位数与均值。'''
    vs = []
    for s in range(seeds):
        x = ar1(a, n, 10_000 + s)
        aa = fit_a(x)
        sg = (x[1:] - aa * x[:-1]).std()          # 用训练残差当噪声尺度
        y = np.zeros(horizon)
        y[0] = x[-1]
        rr = np.random.default_rng(50_000 + s)
        for t in range(1, horizon):
            y[t] = aa * y[t-1] + rr.normal(0, sg)
        vs.append(y[burn:].var())
    vs = np.array(vs)
    return float(np.median(vs)), float(vs.mean())

print('  真 a    n     真稳态方差   rollout 方差(中位数)   比值     rollout 方差(均值)')
var_tab = {}
for a in (0.90, 0.98):
    for n in (50, 200, 1000):
        med, mean = rollout_var(a, n)
        vt = 1.0 / (1 - a*a)
        var_tab[(a, n)] = (med, mean, vt)
        print(f'  {a:5.2f}  {n:5d}  {vt:11.3f}   {med:19.3f}   {med/vt:.4f}   {mean:.3e}')
    print()

# 方差系统性偏小
for key, (med, mean, vt) in var_tab.items():
    assert med < vt, f'{key}: rollout 方差应偏小'
assert var_tab[(0.98, 50)][0] / var_tab[(0.98, 50)][2] < 0.5, \\
    'a=0.98, n=50 时方差比应 <0.5'
# n 越大越接近真值
for a in (0.90, 0.98):
    r50 = var_tab[(a, 50)][0] / var_tab[(a, 50)][2]
    r1000 = var_tab[(a, 1000)][0] / var_tab[(a, 1000)][2]
    assert r1000 > r50, f'a={a}: n 越大方差比应越接近 1'

print(f'✅ a=0.98 时 rollout 的运动能量只有真实的 '
      f'{var_tab[(0.98,50)][0]/var_tab[(0.98,50)][2]*100:.0f}%–'
      f'{var_tab[(0.98,1000)][0]/var_tab[(0.98,1000)][2]*100:.0f}%')
print()
print('-> 「越往后越糊、越静止」有一个不需要神经网络的解释:')
print('   即使模型类完全正确、即使训练完美收敛到该目标的最优解，')
print('   **一步拟合本身就会低估动力学的持续性** —— 这是目标函数问题，不是能力问题。')
print('   这也解释了为什么「多步/rollout 损失」「scheduled sampling」有用：它们改的正是这个目标。')"""),

md("""## 3. 尾部：少数模型会爆炸，而均值指标同时错判两支"""),

code("""print('  真 a     n      â 中位数   â 均值    P(|â|>1)   P(|â|>1.01)')
tail = {}
for a in (0.900, 0.980, 0.995):
    for n in (30, 50, 100, 200, 1000):
        ahs = np.array([fit_a(ar1(a, n, s)) for s in range(6000)])
        p1 = float(np.mean(np.abs(ahs) > 1))
        tail[(a, n)] = (float(np.median(ahs)), p1)
        print(f'  {a:5.3f}  {n:5d}   {np.median(ahs):+.5f}  {ahs.mean():+.5f}   '
              f'{p1*100:6.2f}%    {np.mean(np.abs(ahs)>1.01)*100:6.2f}%')
    print()

# a 越接近 1、n 越小，不稳定拟合越多
assert tail[(0.995, 30)][1] > 0.2, f'a=0.995, n=30 时应有 >20% 不稳定'
assert tail[(0.900, 100)][1] < 0.01, f'a=0.900, n=100 时应几乎没有不稳定'
for a in (0.980, 0.995):
    seq = [tail[(a, n)][1] for n in (30, 50, 100, 200, 1000)]
    for i in range(1, len(seq)):
        assert seq[i] <= seq[i-1] + 1e-9, f'a={a}: 不稳定比例应随 n 下降 {seq}'

print(f'✅ a=0.995, n=30 时 {tail[(0.995,30)][1]*100:.1f}% 的拟合给出 |â|>1（会指数爆炸）')
print(f'✅ a=0.900, n=100 时降到 {tail[(0.900,100)][1]*100:.2f}%')

print()
print('两支的症状完全相反，而**均值指标同时错判两者**:')
print('  真 a    n     真稳态方差   方差中位数     方差均值        均值/中位数')
for a, n in [(0.90, 50), (0.98, 50), (0.98, 200), (0.98, 1000)]:
    med, mean, vt = var_tab[(a, n)]
    print(f'  {a:5.2f}  {n:5d}  {vt:11.3f}   {med:11.3f}   {mean:.3e}   {mean/med:.3e}')

_med, _mean, _ = var_tab[(0.98, 50)]
assert _mean / _med > 1e10, f'a=0.98, n=50 时均值应被爆炸样本主导，实测 {_mean/_med:.2e}'
print()
print(f'✅ a=0.98, n=50: 中位数 {_med:.2f}，均值 {_mean:.3e} —— 差 '
      f'{np.log10(_mean/_med):.0f} 个数量级')
print(f'   {tail[(0.98,50)][1]*100:.0f}% 的爆炸样本完全主导了均值。')
print()
print('-> 所以长视频指标必须报**中位数 + 崩坏率**，而不是平均。')
print('   在一批生成的长视频上报平均任何指标（FVD、逐帧 PSNR、运动幅度）')
print('   都会被少数崩坏样本主导，而那些样本本该被单独拎出来看。')"""),

md("""## 4. 分布的错误不会自我纠正

真 $a{=}0.95$、真噪声 $\\text{sd}{=}1.0$，真稳态 $\\text{sd} = 1/\\sqrt{1-a^2}$。
如果模型的噪声尺度错了会怎样。"""),

code("""a = 0.95
true_sd = 1.0 / np.sqrt(1 - a*a)
print(f'真 a={a}，真噪声 sd=1.0，真稳态 sd = {true_sd:.4f}')
print()
print('  模型噪声 sd   第 5 步 sd   第 50 步   第 500 步   稳态 sd / 真值')
fix = {}
for sg in (0.50, 0.80, 1.00, 1.20, 2.00):
    r = np.random.default_rng(0)
    N = 4000
    y = np.zeros((N, 501))
    y[:, 0] = r.normal(0, true_sd, N)              # 从**正确的**稳态起始
    for t in range(1, 501):
        y[:, t] = a * y[:, t-1] + r.normal(0, sg, N)
    sds = [float(y[:, k].std()) for k in (5, 50, 500)]
    fix[sg] = sds[-1] / true_sd
    print(f'  {sg:11.2f}   {sds[0]:10.3f}   {sds[1]:8.3f}   {sds[2]:9.3f}   '
          f'{sds[-1]/true_sd:14.4f}')
    # 稳态 sd 与噪声 sd 成正比
    assert abs(sds[-1]/true_sd - sg) < 0.02, \\
        f'稳态比值应等于噪声比值 {sg}，得到 {sds[-1]/true_sd:.4f}'

print()
print('✅ 稳态 sd 的比值恰好等于噪声 sd 的比值 —— 因为稳态 sd = σ/sqrt(1−a²)')
print('✅ 即使从**正确的**稳态分布起始，错的噪声尺度也会把它拉到错的不动点')
print()
print('-> 单条轨迹的误差可以被遗忘（第 1 节），但**分布的错误是持久的**。')
print('   收缩性保证「初值不重要」，它**不**保证「收敛到正确的分布」——')
print('   两件事经常被混为一谈。')
print()
print('   实践含义：采样温度 / 引导强度在自回归 rollout 里直接决定不动点的方差。')
print('   CFG 偏高 -> 越来越「锐利到失真」；偏低 -> 越来越糊。')
print('   这两个方向都**不是**误差累积，而是不动点选错了 —— 修法也不同：')
print('   误差累积要改训练目标（第 2 节），不动点错要改采样参数。')"""),

md("""## ✏️ 练习 1：多步损失到底改了什么

「用 rollout 损失修漂移」是一条流行的建议。这个练习把它测清楚。

实现 `fit_a_multistep(x, k)`：最小化 $k$ 步 rollout 的总误差
$\\sum_t \\sum_{j=1}^{k} (a^j x_t - x_{t+j})^2$（对标量 $a$ 用网格搜索即可）。

自测会验证三件事，其中第一件与直觉相反。"""),

code("""def fit_a_multistep(x, k, grid=None):
    '''最小化 k 步 rollout 总误差的 a。

    目标: sum_t sum_{j=1..k} (a^j * x_t − x_{t+j})^2

    参数
    ----
    x    : 训练序列
    k    : rollout 步数（k=1 时应与一步最小二乘接近）
    grid : 候选 a（默认 −1.2 到 1.2 的 2401 个点）

    返回
    ----
    float : 最优 a
    '''
    if grid is None:
        grid = np.linspace(-1.2, 1.2, 2401)
    # TODO: 对每个候选 a 算目标函数，返回 argmin 对应的 a
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 多步损失**不**修 â 的向下偏差（与直觉相反）')
print('    真 a    n     一步中位   k=2      k=4      k=8      k=16     偏差最小的 k')
_bestk = []
for _a in (0.90, 0.98):
    for _n in (50, 200, 1000):
        _m1 = float(np.median([fit_a(ar1(_a, _n, s)) for s in range(200)]))
        _ms = {_k: float(np.median([fit_a_multistep(ar1(_a, _n, s), _k)
                                    for s in range(200)])) for _k in (2, 4, 8, 16)}
        _b = {1: abs(_m1 - _a)}
        _b.update({_k: abs(v - _a) for _k, v in _ms.items()})
        _bk = min(_b, key=_b.get)
        _bestk.append(_bk)
        print(f'    {_a:5.2f} {_n:5d}  {_m1:+.5f}  ' +
              '  '.join(f'{_ms[_k]:+.5f}' for _k in (2,4,8,16)) + f'   k={_bk}')
        # 全部估计仍然向下偏
        assert _m1 < _a and all(v < _a + 1e-9 for v in _ms.values()), \\
            '一步与多步的估计都应向下偏'
assert len(set(_bestk)) > 1, f'最优 k 应在不同配置下变化（说明它不是系统性的）：{_bestk}'
print(f'    -> 偏差最小的 k 在 {sorted(set(_bestk))} 之间跳，**不是系统性的**。')
print('       原因：对**正确指定**的 AR(1)，一步最小二乘已经接近有效估计，')
print('       多步损失没有额外信息可用。')

print()
print('  (b) 模型正确指定时，多步损失几乎什么也不改')
def _hpred_err(a, seqs, H):
    '''用 AR(1) 系数 a 做 H 步预测的相对误差。'''
    num = den = 0.0
    for x in seqs:
        n = len(x)
        pred, targ = (a**H) * x[:n-H], x[H:]
        num += float(((pred - targ)**2).sum())
        den += float(((targ - targ.mean())**2).sum())
    return float(np.sqrt(num / den))

_tr = [ar1(0.95, 200, s) for s in range(60)]
_te = [ar1(0.95, 400, 10_000 + s) for s in range(60)]
print('    拟合用的 k   â        H=1 误差   H=4       H=8       H=16')
_e_ok = {}
for _k in (1, 2, 4, 8, 16):
    _ah = (float(np.median([fit_a(x) for x in _tr])) if _k == 1
           else float(np.median([fit_a_multistep(x, _k) for x in _tr])))
    _row = {_H: _hpred_err(_ah, _te, _H) for _H in (1, 4, 8, 16)}
    _e_ok[_k] = _row
    print(f'    {_k:10d}   {_ah:+.4f}   ' + '  '.join(f'{_row[_H]:.5f}' for _H in (1,4,8,16)))
for _H in (1, 4, 8, 16):
    _spread = max(_e_ok[_k][_H] for _k in _e_ok) - min(_e_ok[_k][_H] for _k in _e_ok)
    assert _spread < 0.005, f'H={_H}: 各 k 的误差差异应 <0.005，实测 {_spread:.5f}'
print('    -> 各 k 的误差只差在第 4 位小数。多步损失在这里是白做的。')

print()
print('  (c) 模型**误配**时才是真实的取舍')
def _ar2(n, seed, rad=0.95, per=6.0, sig=0.3):
    '''振荡的 AR(2) —— AR(1) 模型对它是误配的。'''
    r = np.random.default_rng(seed)
    w = 2*np.pi/per
    c1, c2 = 2*rad*np.cos(w), -rad**2
    x = np.zeros(n)
    x[0], x[1] = r.normal(), r.normal()
    for t in range(2, n):
        x[t] = c1*x[t-1] + c2*x[t-2] + r.normal(0, sig)
    return x

_tr2 = [_ar2(200, s) for s in range(60)]
_te2 = [_ar2(400, 10_000 + s) for s in range(60)]
print('    拟合用的 k   â        H=1 误差   H=4       H=8       H=16')
_e_mis = {}
for _k in (1, 2, 4, 8, 16):
    _ah = (float(np.median([fit_a(x) for x in _tr2])) if _k == 1
           else float(np.median([fit_a_multistep(x, _k) for x in _tr2])))
    _row = {_H: _hpred_err(_ah, _te2, _H) for _H in (1, 4, 8, 16)}
    _e_mis[_k] = _row
    print(f'    {_k:10d}   {_ah:+.4f}   ' + '  '.join(f'{_row[_H]:.5f}' for _H in (1,4,8,16)))

# k=1 在 H=1 最好
assert _e_mis[1][1] == min(_e_mis[_k][1] for _k in _e_mis), 'k=1 应在 H=1 最好'
# 但 k=1 在 H=4 时**比预测均值还差**（误差 > 1.0）
assert _e_mis[1][4] > 1.0, f'k=1 在 H=4 应比均值预测更差，实测 {_e_mis[1][4]:.5f}'
# 而 k>=2 避免了这一点
assert _e_mis[4][4] < 1.005, f'k=4 在 H=4 应不比均值预测差，实测 {_e_mis[4][4]:.5f}'

print()
print(f'✅ (a) 多步损失**不**修 â 的向下偏差 —— 最优 k 在 {sorted(set(_bestk))} 之间跳')
print(f'✅ (b) 模型正确指定时它几乎什么也不改（各 k 差在第 4 位小数）')
print(f'✅ (c) 模型误配时是真实取舍：k=1 在 H=1 最好（{_e_mis[1][1]:.5f}），')
print(f'      但在 H=4 时是 {_e_mis[1][4]:.5f} > 1.0 —— **比直接预测均值还差**；')
print(f'      而 k=4 在 H=4 是 {_e_mis[4][4]:.5f}，避免了这一点。')
print()
print('   所以「用 rollout 损失修漂移」这条建议需要被限定:')
print('     · 它修不了第 2 节那个目标函数偏差（那是有限样本效应，不是目标形状问题）；')
print('     · 它在模型正确指定时是白做的；')
print('     · 它的真实作用是在**误配**下把精度从短跨度挪到长跨度 ——')
print('       而「一步拟合的模型在长跨度上可能比预测均值还差」是这个挪动的理由。')"""),

md("""## ✏️ 练习 2：崩坏率是一个可测量的指标

正文说长视频指标应报「中位数 + 崩坏率」。
实现 `collapse_rate(a, n, seeds, horizon, thresh)`：返回
rollout 过程中<strong>任一帧</strong>的能量超过训练分布 `thresh` 倍的比例。"""),

code("""def collapse_rate(a, n, seeds=400, horizon=200, thresh=10.0):
    '''崩坏率：rollout 中任一帧的 |x| 超过训练分布 sd 的 thresh 倍的样本比例。

    参数
    ----
    a, n     : 真动力学与训练序列长度
    seeds    : 重复次数
    horizon  : rollout 长度
    thresh   : 判定倍数（相对训练序列的 sd）

    返回
    ----
    (rate, median_var) : 崩坏率，以及**未崩坏样本**的 rollout 方差中位数
    '''
    # TODO: 对每个 seed：x = ar1(a, n, 10_000+s)；aa = fit_a(x)；
    #       sg = 训练残差 sd；从 x[-1] 起 rollout horizon 步（噪声 sd = sg）；
    #       若 max|y| > thresh * x.std() 记为崩坏；
    #       返回 (崩坏比例, 未崩坏样本的 y[horizon//2:].var() 的中位数)
    raise NotImplementedError"""),

code("""# 自测
print('  真 a     n     崩坏率    未崩坏样本的方差中位数   真稳态方差   比值')
rates = {}
for _a in (0.90, 0.98, 0.995):
    for _n in (30, 100, 1000):
        _rate, _med = collapse_rate(_a, _n)
        _vt = 1.0 / (1 - _a*_a)
        rates[(_a, _n)] = _rate
        print(f'  {_a:5.3f}  {_n:5d}   {_rate*100:6.2f}%   {_med:20.3f}   '
              f'{_vt:10.3f}   {_med/_vt:.4f}')
    print()

# 崩坏率随 n 下降、随 a→1 上升
for _a in (0.98, 0.995):
    _seq = [rates[(_a, _n)] for _n in (30, 100, 1000)]
    for _i in range(1, len(_seq)):
        assert _seq[_i] <= _seq[_i-1] + 1e-9, f'a={_a}: 崩坏率应随 n 下降 {_seq}'
assert rates[(0.995, 30)] > rates[(0.90, 30)], 'a 越接近 1 崩坏率应越高'
assert rates[(0.90, 1000)] < 0.02, 'a=0.90, n=1000 时崩坏率应很低'

# 未崩坏样本的方差仍系统性偏小 —— 两支是独立的问题
_r, _m = collapse_rate(0.98, 100)
assert _m / (1/(1-0.98**2)) < 0.7, \\
    '未崩坏样本的方差仍应明显偏小（这是第 2 节的偏差，与崩坏无关）'

print(f'✅ 崩坏率随 n 下降（a=0.995: {rates[(0.995,30)]*100:.1f}% -> '
      f'{rates[(0.995,1000)]*100:.1f}%）、随 a→1 上升')
print(f'✅ 而**未崩坏样本**的方差比仍只有 {_m/(1/(1-0.98**2)):.3f} ——')
print('   两支是独立的问题：排除崩坏样本后，剩下的仍然过度衰减。')
print()
print('   -> 所以「中位数 + 崩坏率」这两个数缺一不可：')
print('      崩坏率捕捉尾部那一支，中位数捕捉主体那一支。')
print('      只报平均值会把两者混成一个无意义的数。')"""),

md("""## ✏️ 练习 3：锚帧间隔的账

实现 `anchor_error(ah, T, m)`：用间隔 $m$ 的锚帧重置时，
第 $T$ 帧的误差放大倍数。

- 无锚帧（$m \\geq T$）：误差 $= |\\hat a|^T$
- 有锚帧：每 $m$ 步重置，所以最大连续 rollout 长度是 $m-1$，
  而误差在锚帧处被清零 $\\Rightarrow$ 最终误差 $= |\\hat a|^{(T-1) \\bmod m}$ 级别。

用它算出「要把误差压到 $\\varepsilon$ 以下所需的锚帧间隔」。"""),

code("""def anchor_error(ah, T, m):
    '''间隔 m 的锚帧下，第 T 帧的误差放大倍数（初始误差 = 1）。

    锚帧在 t = 0, m, 2m, ... 处把误差清零（那些帧是给定的/另外生成的）。
    所以第 T 帧的误差 = |ah|^(距离最近的前一个锚帧的步数)。

    参数
    ----
    ah : 学到的谱半径 |â|
    T  : 目标帧序号
    m  : 锚帧间隔（m >= T 表示只有 t=0 一个锚帧）

    返回
    ----
    float : |ah|^k，k = T - (最大的 <= T 的锚帧位置)
    '''
    # TODO: 找到 <= T 的最大锚帧位置 (T // m) * m；k = T - 那个位置；返回 ah**k
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 稳定动力学（â=0.95）。注意「无锚」要用 m > T ——')
print('      若取 m = T，锚帧恰好落在第 T 帧上，误差会被算成 1（这是一个容易踩的坑）')
print('     T    无锚(m>T)     m=16      m=8       m=4     m=T（错的写法）')
for _T in (16, 64, 256):
    _row = [anchor_error(0.95, _T, _T + 1)] + \
           [anchor_error(0.95, _T, _m) for _m in (16, 8, 4)] + \
           [anchor_error(0.95, _T, _T)]
    print(f'   {_T:4d}   ' + '  '.join(f'{v:9.3e}' for v in _row))
    assert abs(_row[0] - 0.95**_T) < 1e-12, '无锚应等于 |â|^T'
    assert abs(_row[-1] - 1.0) < 1e-12, 'm=T 时锚帧落在第 T 帧上，误差恰为 1'

print()
print('  (b) **不稳定**动力学（â=1.02）—— 锚帧的收益是指数级的:')
print('     T    无锚(m>T)      m=16       m=8        m=4     无锚/m=8')
for _T in (16, 64, 256, 1024):
    _no = anchor_error(1.02, _T, _T + 1)
    _row = [_no] + [anchor_error(1.02, _T, _m) for _m in (16, 8, 4)]
    print(f'   {_T:4d}   ' + '  '.join(f'{v:10.3e}' for v in _row) +
          f'   {_no/_row[2]:.3e}')
    # 改善倍数 = |â|^T / |â|^(T mod m)，T 是 m 的倍数时就是 |â|^T
    assert _no / _row[2] > 1.0, f'T={_T}: 锚帧应带来改善'
    if _T >= 256:
        assert _no / _row[2] > 1e2, \
            f'T={_T}: 改善应 >100 倍（1.02^{_T} = {1.02**_T:.3g}），实测 {_no/_row[2]:.3g}'

# 锚帧位置的正确性
assert abs(anchor_error(0.9, 16, 17) - 0.9**16) < 1e-12   # m>T：只有 t=0 一个锚帧
assert abs(anchor_error(0.9, 16, 16) - 0.9**0) < 1e-12    # m=T：锚帧正落在第 16 帧上
assert abs(anchor_error(0.9, 16, 8) - 0.9**0) < 1e-12     # t=16 也正好是锚帧
assert abs(anchor_error(0.9, 17, 8) - 0.9**1) < 1e-12     # t=16 是锚帧，差 1 步
assert abs(anchor_error(0.9, 23, 8) - 0.9**7) < 1e-12     # t=16 是锚帧，差 7 步

# 求所需锚帧间隔
print()
print('  (c) 锚帧只在 |â| > 1 时有用 —— 而这正是第 1 节的结论')
print('      |â| < 1 时误差自己就衰减，chunk 内的最坏值恰好在锚帧上（= 1），')
print('      所以加锚帧**一点也不减小**最坏误差。')
print()
print('     â      chunk 内最坏放大倍数 = |â|^(m-1)')
print('              m=2      m=4      m=8      m=16     m=64')
for _ah in (0.90, 0.99, 1.00, 1.02, 1.05):
    _row = [_ah**(_m-1) for _m in (2, 4, 8, 16, 64)]
    print(f'    {_ah:5.2f}   ' + '  '.join(f'{v:7.3g}' for v in _row))
    if _ah < 1.0:
        # 稳定：最坏值恒为 1（在锚帧处），与 m 无关
        _worst = max(anchor_error(_ah, _t, 8) for _t in range(240, 257))
        assert abs(_worst - 1.0) < 1e-12, \
            f'â={_ah}: chunk 内最坏值应恒为 1（在锚帧上），得到 {_worst}'
print()
print('     -> |â|<1 那两行的最坏放大倍数都 <= 1（误差在衰减）；')
print('        |â|>1 那两行 > 1，而 m 越小越接近 1。')
print()
print('  (d) 所以正确的问法是：|â| > 1 时，多密的锚帧能把放大倍数压到 F 以下')
print('      闭式解: |â|^(m-1) <= F  <=>  m <= 1 + ln F / ln|â|')
print('     â      F=1.5 所需 m     F=2 所需 m     F=10 所需 m')
for _ah in (1.01, 1.02, 1.05, 1.10):
    _row = []
    for _F in (1.5, 2.0, 10.0):
        _m_max = int(np.floor(1 + np.log(_F)/np.log(_ah)))
        # 验证闭式
        assert _ah**(_m_max - 1) <= _F + 1e-9, f'â={_ah}, F={_F}: 闭式应成立'
        assert _ah**_m_max > _F, f'â={_ah}, F={_F}: m+1 应超出'
        _row.append(_m_max)
    print(f'    {_ah:5.2f}   {_row[0]:12d}   {_row[1]:12d}   {_row[2]:13d}')
print()
print('     -> 例如 â=1.02、要求放大不超过 2 倍：m <= 1 + ln2/ln1.02 = '
      f'{int(np.floor(1+np.log(2)/np.log(1.02)))}，即每 '
      f'{int(np.floor(1+np.log(2)/np.log(1.02)))} 帧要一个锚帧。')
print('        而不加锚帧时 T=256 的放大是 '
      f'{1.02**256:.3g} 倍。')

print()
print('✅ 锚帧把有效 rollout 长度从 T 压到 <= m，误差从 |â|^T 变成 |â|^(<=m)')
print(f'✅ 在不稳定动力学下改善是**指数级**的：â=1.02 时')
print(f'   T=64 改善 {1.02**64:.2f} 倍，T=256 是 {1.02**256:.3g} 倍，T=1024 是 {1.02**1024:.3g} 倍')
print('   （改善倍数恰为 |â|^T，因为 T 是 m 的倍数时锚帧把误差清零）')
print()
print('   -> 这就是层次化生成的账：一次性生成一小段（段内无漂移），')
print('      再用锚帧把小段拼长（段间漂移 = 段数）。')
print('      代价见模块 00：段长 m 的一次性生成代价 ∝ m²。')"""),

md("""## ✏️ 练习 4：区分「误差累积」与「不动点错」

给一批生成的序列，怎么判断它属于哪一支？关键区别是**序列是否平稳**：

- **不动点错** → 序列已经平稳（前后半段方差一致），只是水平不对；
- **误差还在累积** → 序列不平稳（后半段方差明显不同）。

实现 `diagnose_drift(gen_seqs, ref_seqs, tol=0.20)`。

两个设计要点，自测会分别验证：

1. 它必须接收**一批**序列而不是一条（(a) 部分）；
2. 能量比必须相对**一批真实序列**算，而不是相对理论值——
   因为 sd 估计量本身在短序列上向下有偏（(b) 部分）。"""),

code("""def diagnose_drift(gen_seqs, ref_seqs, tol=0.20):
    '''区分「不动点错」与「误差还在累积」。

    参数
    ----
    gen_seqs : 生成的序列列表
    ref_seqs : **真实**序列列表（同样长度、同样统计量口径）
    tol      : 判定「平稳」与「能量正常」的相对容差

    返回
    ----
    dict : {'energy_ratio', 'stat_ratio', 'is_stationary', 'verdict'}
      energy_ratio = median(gen 后半段 sd) / median(ref 后半段 sd)
      stat_ratio   = median(gen 后半段 sd / 前半段 sd)
      is_stationary = |stat_ratio − 1| < tol
      verdict: 'ok' | 'fixed_point' | 'compounding'
    '''
    # TODO: 对 gen_seqs 算 (后半 sd / 前半 sd) 的中位数 = stat_ratio；
    #       energy_ratio = median(gen 后半 sd) / median(ref 后半 sd)；
    #       不平稳 -> 'compounding'；平稳且 |energy_ratio−1|<tol -> 'ok'；
    #       平稳但能量偏离 -> 'fixed_point'
    raise NotImplementedError"""),

code("""# 自测
_a, _true_sd = 0.95, 1.0/np.sqrt(1-0.95**2)
def _mk(ah, sg, T=400, seed=0):
    r = np.random.default_rng(seed)
    y = np.zeros(T)
    y[0] = r.normal(0, _true_sd)
    for t in range(1, T):
        y[t] = ah*y[t-1] + r.normal(0, sg)
    return y
def _batch(ah, sg, n=60, T=400, seed0=0):
    return [_mk(ah, sg, T=T, seed=seed0+s) for s in range(n)]

_REF = _batch(0.95, 1.0, n=200, seed0=900_000)          # 一批**真实**序列

print('  (a) 为什么必须在一批上做：单条序列的 s2/s1 抖动比信号还大')
_one = np.array([_mk(0.95, 1.0, seed=s)[200:].std() / _mk(0.95, 1.0, seed=s)[:200].std()
                 for s in range(200)])
_neff = (400/2)*(1-_a*_a)/(1+_a*_a)
print(f'    单条 s2/s1（T=400, 200 seeds）: 中位 {np.median(_one):.3f}, '
      f'p5 {np.percentile(_one,5):.3f}, p95 {np.percentile(_one,95):.3f}')
print(f'    理论有效样本量 n_eff = (T/2)(1−a²)/(1+a²) = {_neff:.1f}  ->  '
      f'sd(sd) ≈ 1/sqrt(2·n_eff) = {1/np.sqrt(2*_neff):.3f}')
assert np.percentile(_one, 95) - np.percentile(_one, 5) > 0.5
print('    -> p5–p95 跨了 '
      f'{np.percentile(_one,5):.2f}–{np.percentile(_one,95):.2f}，'
      '**任何单条容差都不可能工作**')

print()
print('  (b) 为什么能量比要相对**真实批**而不是理论值:')
_med_ref = float(np.median([y[200:].std() for y in _REF]))
print(f'    理论稳态 sd = {_true_sd:.4f}')
print(f'    真实批的 median(后半 sd) = {_med_ref:.4f}  ->  估计量本身只有理论值的 '
      f'{_med_ref/_true_sd:.4f}')
assert _med_ref / _true_sd < 0.95, 'sd 估计量的中位数应明显低于真值'
print('    原因：sd 估计量右偏，而 n_eff≈10 时中位数明显低于真值。')
print('    所以拿理论值做分母会把一个**好**模型误判成「偏静止」。')
_bad_er = float(np.median([y[200:].std() for y in _batch(0.95, 1.0)])) / _true_sd
_good_er = float(np.median([y[200:].std() for y in _batch(0.95, 1.0)])) / _med_ref
print(f'    同一批生成序列: 相对理论值 {_bad_er:.4f}（会误判）'
      f'  vs  相对真实批 {_good_er:.4f}（正确）')
assert _bad_er < 0.88 and abs(_good_er - 1.0) < 0.15

print()
print('  (c) 四种情形的诊断:')
print('    情形                     能量比      平稳比    平稳?    诊断')
for _tag, _ah, _sg, _expect in [
        ('â=0.95 σ=1.0（正确）', 0.95, 1.0, 'ok'),
        ('â=0.88（低估持续性）', 0.88, 1.0, 'fixed_point'),
        ('σ=0.5（低估噪声）', 0.95, 0.5, 'fixed_point'),
        ('σ=2.0（高估噪声）', 0.95, 2.0, 'fixed_point'),
        ('â=1.02（不稳定）', 1.02, 1.0, 'compounding')]:
    _d = diagnose_drift(_batch(_ah, _sg), _REF)
    print(f'    {_tag:24s} {_d["energy_ratio"]:9.3f}   {_d["stat_ratio"]:8.3f}   '
          f'{str(_d["is_stationary"]):6s}  {_d["verdict"]}')
    assert _d['verdict'] == _expect, f'{_tag}: 期望 {_expect}，得到 {_d["verdict"]}'

_dl = diagnose_drift(_batch(0.95, 0.5), _REF)
_dh = diagnose_drift(_batch(0.95, 2.0), _REF)
assert _dl['energy_ratio'] < 1 < _dh['energy_ratio']

print()
print('✅ 五种情形被正确区分')
print(f'✅ 两种「不动点错」的能量比一个 {_dl["energy_ratio"]:.3f}（偏静止）、'
      f'一个 {_dh["energy_ratio"]:.3f}（偏乱），但**都平稳**')
print('✅ 而不稳定的那一条不平稳 —— 这是区分两支的关键信号')
print()
print('   三个可操作的结论:')
print('     · 平稳性诊断必须在**批**上做：单条序列的抖动比信号大。')
print('     · 能量比必须相对**真实批**算：同一个统计量两边都算一次，估计量偏差自动抵消。')
print('     · 两支的修法相反 —— fixed_point 调采样参数，compounding 改训练目标/加锚帧。')
print('       而只看「后半段比前半段糊」这一个现象分不出是哪一支。')"""),

md("""## 📖 参考答案"""),

code("""def fit_a_multistep(x, k, grid=None):
    '''最小化 k 步 rollout 总误差的 a。'''
    if grid is None:
        grid = np.linspace(-1.2, 1.2, 2401)
    n = len(x)
    best, best_loss = grid[0], np.inf
    for a in grid:
        loss = 0.0
        p = 1.0
        for j in range(1, k+1):
            p *= a
            if n - j <= 0:
                break
            d = p * x[:n-j] - x[j:]
            loss += float(d @ d)
        if loss < best_loss:
            best, best_loss = float(a), loss
    return best

def collapse_rate(a, n, seeds=400, horizon=200, thresh=10.0):
    '''崩坏率与未崩坏样本的方差中位数。'''
    bad, vars_ok = 0, []
    for s in range(seeds):
        x = ar1(a, n, 10_000 + s)
        aa = fit_a(x)
        sg = (x[1:] - aa * x[:-1]).std()
        y = np.zeros(horizon)
        y[0] = x[-1]
        rr = np.random.default_rng(60_000 + s)
        for t in range(1, horizon):
            y[t] = aa * y[t-1] + rr.normal(0, sg)
        if not np.isfinite(y).all() or np.abs(y).max() > thresh * x.std():
            bad += 1
        else:
            vars_ok.append(y[horizon//2:].var())
    med = float(np.median(vars_ok)) if vars_ok else float('nan')
    return bad / seeds, med

def anchor_error(ah, T, m):
    '''间隔 m 的锚帧下第 T 帧的误差放大倍数。'''
    last_anchor = (T // m) * m
    return float(ah ** (T - last_anchor))

def diagnose_drift(gen_seqs, ref_seqs, tol=0.20):
    '''区分「不动点错」与「误差还在累积」。两个统计量都在批上算。'''
    def halves(seqs):
        r, s2s = [], []
        for y in seqs:
            h = len(y) // 2
            s1, s2 = float(np.std(y[:h])), float(np.std(y[h:]))
            r.append(s2 / max(s1, 1e-12))
            s2s.append(s2)
        return float(np.median(r)), float(np.median(s2s))
    stat_ratio, med_gen = halves(gen_seqs)
    _, med_ref = halves(ref_seqs)
    energy_ratio = med_gen / max(med_ref, 1e-12)
    is_stat = abs(stat_ratio - 1.0) < tol
    if not is_stat:
        verdict = 'compounding'
    elif abs(energy_ratio - 1.0) < tol:
        verdict = 'ok'
    else:
        verdict = 'fixed_point'
    return {'energy_ratio': energy_ratio, 'stat_ratio': stat_ratio,
            'is_stationary': bool(is_stat), 'verdict': verdict}

print('参考答案已定义。')
print()
print('要点：')
print('  1. 多步损失**不**修一步拟合的向下偏差；它在模型正确指定时几乎什么也不改。')
print('     它的真实作用是在**误配**下把精度从短跨度挪到长跨度。')
print('  2. 「中位数 + 崩坏率」缺一不可：它们分别捕捉相反症状的两支。')
print('  3. 锚帧把误差从 |â|^T 变成 |â|^(<=m)，在不稳定动力学下是指数级改善。')
print('  4. 「不动点错」与「误差累积」的区分信号是**序列是否平稳**，')
print('     而它必须在**一批**上做（单条 s2/s1 在 T=400 时 p5–p95 跨 0.67–1.59），')
print('     且能量比要相对**真实批**算 —— sd 估计量的中位数本身只有真值的 0.885。')"""),

md("""## 🧪 真实工程胶囊：长视频生成的漂移体检

下面这段代码在一批生成的序列上跑完本模块的四项诊断，
并按「哪一支」给出**对应的修法**——而不是笼统地说「有漂移」。

关键设计：它先用**崩坏率**把两支分开，再对未崩坏的部分做平稳性诊断。
这个顺序是必要的：崩坏样本会让任何方差诊断失去意义（第 3 节的 $10^{14}$）。"""),

code("""def drift_report(gen_seqs, ref_seqs, thresh=10.0, tol=0.20):
    '''一批生成序列的漂移体检。ref_seqs 是一批**真实**序列（同口径的参照）。'''
    train_sd = float(np.median([np.std(y) for y in ref_seqs]))
    n = len(gen_seqs)
    collapsed = [y for y in gen_seqs
                 if (not np.isfinite(y).all()) or np.abs(y).max() > thresh * train_sd]
    ok_seqs = [y for y in gen_seqs
               if np.isfinite(y).all() and np.abs(y).max() <= thresh * train_sd]
    rate = len(collapsed) / n
    print(f'  样本数 {n}，崩坏 {len(collapsed)}（{rate*100:.1f}%）')
    if not ok_seqs:
        print('  ⚠️  全部崩坏 —— 后续诊断无意义')
        return dict(collapse_rate=rate, verdict='all_collapsed', fixes=['降低 |â|（多步损失/正则）'])

    d = diagnose_drift(ok_seqs, ref_seqs, tol=tol)
    maj, er = d['verdict'], d['energy_ratio']
    print(f'  未崩坏样本（批级）: 能量比 {er:.3f}，平稳比 {d["stat_ratio"]:.3f}，'
          f'平稳 = {d["is_stationary"]}，判定 = {maj}')

    fixes = []
    if rate > 0.02:
        fixes.append(f'崩坏率 {rate*100:.1f}% > 2%：一部分模型的 |â|>1。'
                     f'修法 = 多步损失 / 谱范数约束 / 更长的训练序列')
    if maj == 'compounding':
        fixes.append('主体仍在累积（不平稳）：修法 = 多步/rollout 损失，或加锚帧'
                     '（把有效 rollout 长度压到 m）')
    elif maj == 'fixed_point':
        d = '偏静止/糊' if er < 1 else '偏乱/过锐'
        fixes.append(f'主体已平稳但不动点错（能量比 {er:.3f}，{d}）：'
                     f'修法 = 调采样参数（温度 / CFG 强度 / 噪声调度），**不是**改训练目标')
    elif maj == 'ok' and rate <= 0.02:
        fixes.append('无明显问题')
    print('  ' + '-' * 70)
    for f in fixes:
        print(f'  -> {f}')
    print('  ' + '-' * 70)
    print()
    return dict(collapse_rate=rate, energy_ratio=er, verdict=maj, fixes=fixes)

def _gen_batch(a_hat, noise_sd, n=60, T=400, x0_sd=None, seed0=0):
    '''模拟一批「生成」出来的序列。'''
    x0_sd = x0_sd if x0_sd is not None else 1.0/np.sqrt(max(1-0.95**2, 1e-9))
    out = []
    for s in range(n):
        r = np.random.default_rng(seed0 + s)
        y = np.zeros(T)
        y[0] = r.normal(0, x0_sd)
        for t in range(1, T):
            y[t] = a_hat * y[t-1] + r.normal(0, noise_sd)
        out.append(y)
    return out

TRUE_A, TRUE_SD = 0.95, 1.0/np.sqrt(1-0.95**2)
REF_BATCH = _gen_batch(TRUE_A, 1.0, n=200, seed0=900_000)     # 一批**真实**序列作参照
print(f'训练分布: a={TRUE_A}, 噪声 sd=1.0, 稳态 sd={TRUE_SD:.4f}')
print(f'参照批（200 条真实序列）的 median(全段 sd) = '
      f'{np.median([np.std(y) for y in REF_BATCH]):.4f}')
print()

print('=== 场景 A：模型很好 ===')
_A = drift_report(_gen_batch(0.95, 1.0), REF_BATCH)
assert _A['verdict'] == 'ok', f'应判为 ok，得到 {_A["verdict"]}'

print('=== 场景 B：â 被低估（生成变静止）===')
_B = drift_report(_gen_batch(0.88, 1.0), REF_BATCH)
assert _B['verdict'] == 'fixed_point' and _B['energy_ratio'] < 1, \\
    f'应判为不动点错且偏静止，得到 {_B["verdict"]}, {_B["energy_ratio"]:.3f}'
assert any('采样参数' in f for f in _B['fixes'])

print('=== 场景 C：噪声尺度高估（生成变乱）===')
_C = drift_report(_gen_batch(0.95, 1.8), REF_BATCH)
assert _C['energy_ratio'] > 1, f'应偏乱，得到 {_C["energy_ratio"]:.3f}'

print('=== 场景 D：一部分模型不稳定（混合批）===')
_mix = _gen_batch(0.95, 1.0, n=50, seed0=0) + _gen_batch(1.02, 1.0, n=10, seed0=500)
_D = drift_report(_mix, REF_BATCH)
assert _D['collapse_rate'] > 0.1, f'应检出崩坏，得到 {_D["collapse_rate"]:.3f}'
assert any('崩坏率' in f for f in _D['fixes'])

print('=== 场景 E：全部不稳定 ===')
_E = drift_report(_gen_batch(1.03, 1.0), REF_BATCH)
assert _E['verdict'] == 'all_collapsed'

print('工程含义：')
print('  · 诊断顺序是**必要的**：先按崩坏率把两支分开，再对未崩坏部分做平稳性诊断。')
print('    如果先算方差，场景 D 的均值会被那 10 个崩坏样本主导（第 3 节的 1e14）。')
print('  · 场景 B 与 C 的现象都是「后半段看起来不对」，而修法相反 ——')
print('    B 要调大采样温度/降 CFG，C 要调小。')
print('    如果只看「有漂移」就去加多步损失，两个场景都修不好。')
print('  · 场景 A 的判定是 ok，说明这套诊断不会对好模型误报。')""")
,]
