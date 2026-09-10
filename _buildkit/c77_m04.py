# -*- coding: utf-8 -*-
"""C77 模块 04 · 世界模型：动作条件、可交互 rollout，与 C41 的分工。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 03（生成侧的漂移：$\\vert\\hat a\\vert^k$、目标函数偏差、不动点）；"
                 "<strong>C41 模块 04（基于模型与世界模型）</strong>——"
                 "MPC / 随机打靶 / Dyna / 规划侧的复合误差在那里，本课不重讲；"
                 "线性系统与最小二乘"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_world_model.ipynb'
                       '（<strong>同一个模型：被动 rollout 高估奖励 $-13.0\\%$，'
                       '主动规划高估 $+251.2\\%$</strong>——而它的分布内一步误差只有 $0.0395$ / '
                       '<strong>动作条件的收益 $= $ 动作在状态变化里占的方差份额</strong>'
                       '（$1.01\\times$ 到 $28.23\\times$），而<strong>喂错动作比不喂更糟</strong> / '
                       '<strong>分布偏移本身不是问题，误配 $\\times$ 偏移才是</strong>：'
                       '模型匹配时一步误差在策略幅度跨 $30$ 倍下平坦（$+1.9\\%$），'
                       '误配时同样偏移下涨 $\\mathbf{44}$ 倍）'),
    ("核心参考", "Ha &amp; Schmidhuber, <em>World Models</em>（NeurIPS 2018）· "
                 "Hafner et al., <em>Dream to Control / DreamerV3</em>"
                 "（ICLR 2020 / Nature 2025）· "
                 "OpenAI, <em>Video generation models as world simulators</em>"
                 "（Sora 技术报告, 2024）· "
                 "Bruce et al., <em>Genie: Generative Interactive Environments</em>"
                 "（ICML 2024，无标注动作的潜在动作学习）· "
                 "Valevski et al., <em>GameNGen: Diffusion Models Are Real-Time Game "
                 "Engines</em>（2024）· "
                 "Yu et al., <em>Cosmos World Foundation Model Platform</em>（NVIDIA, 2025）· "
                 "本课程 <strong>C41 模块 04</strong>（规划侧）· C59（VLA / 模仿学习的复合误差）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [

("two", "「世界模型」有两个互不相同的意思", "".join([
    P("这个词在两条不同的文献线里指两件事，而它们的失效机制不同、诊断方式不同、修法也不同："),
    TABLE(["", "作为<strong>规划器的环境</strong>（C41-04）",
           "作为<strong>可交互的生成器</strong>（本课）"],
          [["用途", "在脑中前瞻搜索好的动作序列（MPC）；"
            "或生成想象经验去训练策略（Dyna）",
            "接受用户/智能体的动作，生成后续画面"],
           ["谁在选动作", "一个<strong>优化器</strong>，目标是最大化模型预测的回报",
            "外部给定（用户操作、录制的轨迹、或一个固定策略）"],
           ["失效机制", "<strong>对抗性</strong>：优化器主动去找模型的错误",
            "<strong>分布性</strong>：rollout 慢慢离开数据流形"],
           ["主要诊断", "模型预测回报 vs 真实回报的差",
            "生成分布 vs 真实分布（模块 03 的平稳性与能量比）"],
           ["主要修法", "悲观化 / 不确定性惩罚 / 限制规划视野",
            "改训练目标 / 加锚帧 / 调采样参数（模块 03）"]]),
    P("本课处理右边一列。但下一节会把两者放在<strong>同一个模型</strong>上直接对比，"
      "因为那个对比本身是理解这条分界最快的方式。"),
    CALLOUT("intuition", "为什么必须分开",
            "两者常被混为一谈，因为它们训练<em>同一个</em>东西："
            "一个动作条件的下一帧/下一状态预测器。"
            "而下一节会量出：同一个模型、同样的一步误差（$0.0395$），"
            "<strong>被动使用时奖励高估 $-13\\%$，"
            "被优化器使用时高估 $+251\\%$</strong>。"
            "所以「这个世界模型准不准」这个问题<em>没有答案</em>，"
            "除非先说清它要被怎么用。"),
])),

("exploit", "同一个模型，两种用法，两个数量级的差别", "".join([
    P("notebook 的设定：真系统的执行器<strong>饱和</strong>"),
    MATH("s_{t+1} = A s_t + B \\tanh(a_t) + \\varepsilon"),
    P("而模型类是<strong>线性</strong>的（$\\hat{s}_{t+1} = \\hat{A}s_t + \\hat{B}a_t$）——"
      "所以存在真实的<em>结构</em>误差，而不只是估计噪声。"
      "训练数据用 $a \\sim U[-0.3, 0.3]$ 收集 $300$ 条轨迹，"
      "<strong>分布内的一步预测相对误差是 $0.0395$</strong>（一个很好的模型）。"),
    P("然后两种用法，都允许动作范围到 $[-a_{\\text{pl}}, a_{\\text{pl}}]$："),
    TABLE(["$a_{\\text{pl}}$", "<strong>主动规划</strong>：模型预测回报",
           "真实回报", "高估", "相对高估",
           "<strong>被动 rollout</strong>（同幅度随机动作）的相对高估"],
          [["$0.3$", "$4.627$", "$4.580$", "$+0.047$", "$1.0\\%$", "$-0.2\\%$"],
           ["$0.5$", "$6.574$", "$6.267$", "$+0.307$", "$4.9\\%$", "$-0.7\\%$"],
           ["$1.0$", "$11.442$", "$9.225$", "$+2.217$", "$24.0\\%$", "$-3.0\\%$"],
           ["$2.0$", "$21.177$", "$11.224$", "$+9.953$", "$88.7\\%$", "$-7.9\\%$"],
           ["$4.0$", "$40.648$", "$11.573$", "$+29.076$", "$\\mathbf{251.2\\%}$",
            "$\\mathbf{-13.0\\%}$"]]),
    P("机制很清楚：<strong>线性模型认为「动作越大收益越大」（它没有饱和），"
      "于是优化器把 $\\vert a \\vert$ 顶到边界，而真系统在那里早已 $\\tanh$ 饱和</strong>。"
      "优化器不是在利用噪声，它是在<em>最大化模型的结构误差</em>。"),
    P("注意被动那一列的<strong>符号</strong>：它是<em>负</em>的（低估），"
      "而且幅度只有主动的二十分之一。被动 rollout 没有任何东西在对抗模型，"
      "所以它的误差就是误差，不朝任何方向系统性地累积。"),
    CALLOUT("danger", "一个直接的工程后果",
            "把一个视频世界模型的「一步预测准确率」当作它<strong>能不能被智能体用来规划</strong>的证据，"
            "是一次量级上的错误。上表的模型一步误差 $3.95\\%$，"
            "而被优化器使用时回报高估 $251\\%$。"
            "<strong>要评估「能不能规划」，必须让一个优化器去攻击它，然后看真实回报</strong>——"
            "而这正是 C41 模块 04 的领地，本课只负责说清两者不是同一件事。"),
])),

("action", "动作条件值多少", "".join([
    P("动作条件是「可交互」的最低要求。它值多少？"
      "notebook 比较三种预测器：只看状态 $s$、看 $s$ 与动作 $a$、"
      "以及看 $s$ 与<strong>打乱的</strong> $a$："),
    TABLE(["动作幅度", "噪声 sd", "只看 $s$", "看 $s{+}a$", "看 $s{+}$<strong>错的</strong>$a$",
           "条件化的收益"],
          [["$0.1$", "$0.05$", "$0.07396$", "$0.05364$", "$0.08982$", "$1.38\\times$"],
           ["$0.1$", "$0.50$", "$0.47690$", "$0.47440$", "$0.47880$", "$1.01\\times$"],
           ["$0.5$", "$0.05$", "$0.25074$", "$0.05207$", "$0.35318$", "$4.82\\times$"],
           ["$1.0$", "$0.05$", "$0.45372$", "$0.04794$", "$0.64486$", "$9.46\\times$"],
           ["$3.0$", "$0.05$", "$0.83535$", "$0.02959$", "$1.19092$", "$\\mathbf{28.23\\times}$"],
           ["$3.0$", "$0.50$", "$0.85101$", "$0.28356$", "$1.17619$", "$3.00\\times$"]]),
    P("<strong>收益等于动作在状态变化里占的方差份额</strong>："
      "动作幅度小或环境噪声大时收益趋于 $1$（条件化白做），"
      "动作主导时收益可达 $28\\times$。"),
    P("第三列是要点：<strong>喂错动作比不喂动作更糟</strong>"
      "（$0.08982 > 0.07396$，$1.19092 > 0.83535$）。"
      "因为模型会<em>照着</em>错动作走——它把一个错误的因当作真的因去外推。"),
    CALLOUT("warn", "这条对「潜在动作」的做法有直接含义",
            "从无标注视频里学「潜在动作」（Genie 一类）时，"
            "潜在动作的<strong>推断错误</strong>不是无害的噪声——"
            "按上表，它会让模型比根本不做动作条件更差。"
            "所以这类系统必须报告一个额外的量："
            "<strong>潜在动作的可辨识性</strong>（同一段真实转移能否被稳定地反推出同一个潜在动作），"
            "而不只是报告重建质量。"),
])),

("shift", "分布偏移本身不是问题", "".join([
    P("「在随机动作上训练、用策略动作 rollout」会带来动作分布偏移。"
      "这有多要紧？notebook 用两个真系统对比——"
      "一个与模型类<strong>完全匹配</strong>（线性），一个<strong>误配</strong>（$\\tanh$ 饱和）："),
    TABLE(["策略增益 $g$", "$\\vert a\\vert$ 均值",
           "匹配：$1$ 步误差", "匹配：$10$ 步",
           "<strong>误配</strong>：$1$ 步误差", "<strong>误配</strong>：$10$ 步"],
          [["$0.0$", "$0.000$", "$0.05360$", "$0.10805$", "$0.05362$", "$0.10809$"],
           ["$0.1$", "$0.109$", "$0.05360$", "$0.13323$", "$0.05368$", "$0.13306$"],
           ["$0.3$", "$0.326$", "$0.05360$", "$0.23663$", "$0.07485$", "$0.57819$"],
           ["$1.0$", "$1.087$", "$0.05370$", "$2.08321$", "$0.53104$", "$40.40066$"],
           ["$3.0$", "$3.261$", "$\\mathbf{0.05461}$", "$199.86$",
            "$\\mathbf{2.38179}$", "$4771.81$"]]),
    P("<strong>匹配时的一步误差在策略幅度跨 $30$ 倍的范围内完全平坦</strong>"
      "（$0.05360 \\to 0.05461$，$+1.9\\%$）；"
      "而误配时同样的偏移让它涨 <strong>$44$ 倍</strong>（$0.05362 \\to 2.38179$）。"),
    DUAL("分布偏移之所以危险，不是因为「模型没见过那里」——"
         "一个正确指定的线性模型在没见过的地方外推得同样好。"
         "危险来自<strong>模型错的那部分在新区域被放大</strong>。"
         "所以「加大训练动作范围」有效（它缩小偏移），"
         "而「加大数据量」无效（它只减小估计误差，不动误配）。",
         "记真映射 $f$、模型类 $\\mathcal{F}$、拟合结果 $\\hat f$。"
         "在分布 $P$ 上训练、在 $Q$ 上评估，误差可分解为"
         "$\\Vert \\hat f - f \\Vert_Q \\leq "
         "\\Vert \\hat f - f^{*} \\Vert_Q + \\Vert f^{*} - f \\Vert_Q$，"
         "其中 $f^{*}$ 是 $\\mathcal{F}$ 中在 $P$ 上的最优元。"
         "第一项是<strong>估计</strong>误差（随 $n$ 消失），"
         "第二项是<strong>逼近</strong>误差（不随 $n$ 消失，且在 $Q$ 上可以任意大）。"
         "匹配情形下 $f^{*} = f$，第二项恒为 $0$——这正是上表左半边平坦的原因。"),
    P("$10$ 步那两列有一个<strong>混淆因素</strong>必须说清："
      "$g{=}3$ 时闭环系统本身不稳定（$\\rho(A + BgK) > 1$），"
      "所以真实轨迹与模型轨迹<em>都</em>发散，$199.86$ 这个数里有很大一部分不是模型误差。"
      "干净的信号在<strong>一步</strong>那两列。"),
])),

("latent_action", "没有动作标注怎么办：潜在动作与它的可辨识性", "".join([
    P("上一节假设动作是<strong>已知的</strong>。而视频数据几乎从不带动作标注——"
      "一段游戏录屏、一段行车记录，都只有画面。"
      "于是有一类做法（Genie 一线）从无标注视频里<strong>反推</strong>潜在动作："),
    ASCII("""
   有标注:    (s_t, a_t) -> s_{t+1}          直接监督
   无标注:    (s_t, s_{t+1}) -> ẑ_t          反推「发生了什么」
                    |
                    v
              (s_t, ẑ_t) -> s_{t+1}          再用它做动作条件
""".strip("\n")),
    P("这个循环有一个明显的退化解：让 $\\hat z_t$ 直接编码 $s_{t+1}$ 本身。"
      "那样重建完美，而 $\\hat z$ 完全不是「动作」——"
      "它只是把答案抄了一遍。所以这类方法必须限制 $\\hat z$ 的容量"
      "（离散、少量码字、低维），让它只能装下「这一步的意图」。"),
    H3("而第 3 节给出一个必须报告的量"),
    P("第 3 节量出<strong>喂错动作比不喂动作更糟</strong>（$8$ 种配置全部成立："
      "例如 $1.19092 > 0.83535$）。这条对潜在动作有直接后果："),
    CALLOUT("danger", "潜在动作的推断错误不是无害的噪声",
            "如果 $\\hat z_t$ 在部署时被推断错了（用户的操作被映射到错误的潜在动作），"
            "那么模型会<strong>照着错的动作走</strong>——"
            "结果比一个根本不做动作条件的模型<em>更差</em>。"
            "所以这类系统必须报告一个额外的量："
            "<strong>潜在动作的可辨识性</strong>——"
            "同一段真实转移能否被稳定地反推出同一个 $\\hat z$。"
            "而<em>重建质量高不能替代它</em>：退化解的重建质量是最高的。"),
    TABLE(["该报告的量", "怎么量", "不报会怎样"],
          [["动作条件的收益", "不给 $\\hat z$ 的误差 / 给 $\\hat z$ 的误差",
            "动作条件可能是装饰性的（本课实测可低至 $1.01\\times$）"],
           ["<strong>错动作的惩罚</strong>", "喂打乱的 $\\hat z$ 的误差 / 不给的误差",
            "看不出「照着错动作走」这个风险"],
           ["<strong>$\\hat z$ 的可辨识性</strong>",
            "同一转移在不同上下文/噪声下反推出同一个 $\\hat z$ 的比例",
            "可能学到了退化解（$\\hat z$ 抄答案）"],
           ["$\\hat z$ 的信息量", "$\\hat z$ 的熵；以及它对 $s_{t+1}$ 的互信息",
            "分不出「$\\hat z$ 是意图」与「$\\hat z$ 是答案」"]]),
    P("最后一行是区分退化解的关键：<strong>真正的动作 $\\hat z$ 的信息量应当远小于 $s_{t+1}$</strong>。"
      "如果 $I(\\hat z; s_{t+1})$ 接近 $H(s_{t+1})$，那 $\\hat z$ 就是答案的编码而不是意图。"
      "本课不实现这一族度量（它需要真实的 tokenizer 与视频），"
      "但第 3 节的两列（收益、错动作惩罚）是可以直接搬过去用的。"),
])),

("memory", "世界模型的状态：帧窗口还是循环隐状态", "".join([
    P("本模块的模型是<strong>无状态</strong>的：预测 $s_{t+1}$ 只用 $(s_t, a_t)$。"
      "真实系统有两条路线，而模块 00 的遮挡悬崖决定了它们的分界。"),
    TABLE(["路线", "机制", "上下文长度", "代价"],
          [["帧窗口（无状态）", "把最近 $h$ 帧拼起来当输入",
            "硬上限 $h$", "代价 $\\propto h^2$（注意力）或 $\\propto h$（拼接）"],
           ["循环隐状态", "维护一个 $\\dim$ 固定的 $z_t$，$z_{t+1} = g(z_t, s_t, a_t)$",
            "原则上无限", "$z$ 的容量是瓶颈；且它自己会漂移（第 1–4 节全部适用）"]]),
    P("模块 00 的遮挡悬崖给出了对第一条路线的<strong>硬约束</strong>："
      "$h$ 必须覆盖「最长不可观测区间 $+ 2$ 帧」，否则误差 $\\approx 1.0$"
      "（除了均值什么也预测不出）。"
      "而这个约束<em>不能</em>通过增大模型来绕过——它是可观测性的问题。"),
    P("第二条路线原则上没有这个上限，但它把问题挪到了别处："
      "<strong>$z_t$ 自己是一个自回归 rollout</strong>，"
      "所以模块 03 的全部内容（$\\vert\\hat a\\vert^k$、一步拟合的偏差、不动点）"
      "对 $z$ 的动力学同样成立。"
      "区别是 $z$ 的漂移<em>不可见</em>——它不在像素上，所以看画面看不出来。"),
    CALLOUT("warn", "隐状态漂移的诊断",
            "模块 03 第 4 节的批级诊断（平稳性 + 能量比）"
            "<strong>可以直接用在 $z_t$ 上</strong>，而且比用在像素上更灵敏——"
            "因为 $z$ 的维度低、统计量更稳。"
            "具体做法：跑一批长 rollout，记录 $\\Vert z_t\\Vert$ 的轨迹，"
            "然后对它做「前后半段方差比」与「相对真实 rollout 的能量比」两个检验。"
            "这两个数会在画面明显崩坏之前就动。"),
    H3("两条路线的一个混合"),
    P("工业上常见的做法是<strong>短帧窗口 $+$ 长期摘要</strong>："
      "最近 $h$ 帧给精细的时间信息（覆盖典型的遮挡时长），"
      "而一个低维的、更新缓慢的摘要向量携带「场景的持久属性」"
      "（地图、已探索区域、物体清单）。"),
    P("按本课的框架，这个设计的合理性可以说清："
      "帧窗口负责<strong>可观测性</strong>（模块 00 的硬约束），"
      "摘要负责<strong>不随时间衰减的信息</strong>（而它的漂移风险由模块 03 管）。"
      "两者的失效模式不同，所以<em>诊断也要分开做</em>——"
      "这正是模块 04 第 5 节那张「四项互不蕴含」表的一个具体展开。"),
])),

("why_gap", "为什么优化会把误差放大：一个可以算的说法", "".join([
    P("第 2 节量出了 $-13\\%$ 与 $+251\\%$。这一节说清那个量级差<strong>从哪来</strong>，"
      "因为它决定了缓解手段的方向。"),
    P("设真映射 $f$，模型 $\\hat f = f + \\epsilon$，其中 $\\epsilon$ 是模型误差。"
      "被动 rollout 在一个<strong>与 $\\epsilon$ 无关</strong>的动作分布上评估，所以"),
    MATH("E_{a \\sim \\pi_0}[\\epsilon(a)] \\approx 0 \\quad\\text{（误差就是误差）}"),
    P("而规划选的是 $a^{*} = \\arg\\max_a \\hat r(a) = \\arg\\max_a [r(a) + \\epsilon(a)]$，"
      "所以"),
    MATH("\\hat r(a^{*}) - r(a^{*}) = \\epsilon(a^{*}) = \\max_a[\\cdots] "
         "\\gg E_a[\\epsilon(a)]"),
    P("<strong>被动看的是 $\\epsilon$ 的<em>均值</em>，主动看的是它的<em>最大值</em></strong>。"
      "在动作空间上取最大值，所以量级差随<strong>动作空间的大小</strong>增长——"
      "这正是第 2 节那张表里「相对高估随 $a_{\\text{pl}}$ 单调增长」的原因"
      "（$1.0\\% \\to 4.9\\% \\to 24.0\\% \\to 88.7\\% \\to 251.2\\%$）。"),
    CALLOUT("intuition", "这个说法给出三条缓解方向",
            "① <strong>缩小 $\\max$ 的范围</strong>——限制规划的动作范围到训练分布附近"
            "（练习 1 实测它是最直接的旋钮）；"
            "② <strong>让 $\\epsilon$ 的上界变小</strong>——"
            "但注意第 2 节的 $\\epsilon$ 是<em>结构</em>误差（线性 vs $\\tanh$），"
            "所以加数据无效（练习 1 实测：一步误差降了而高估仍是 $251\\%$）；"
            "③ <strong>把 $\\epsilon$ 的不确定性算进目标</strong>——"
            "即悲观化：优化 $\\hat r(a) - \\lambda \\sigma(a)$ 而不是 $\\hat r(a)$。"
            "第三条是 C41 模块 04 的内容，而本节的作用是说清它<em>为什么必要</em>。"),
    P("还有一个推论值得记：<strong>这个量级差与模型的一步精度几乎无关</strong>。"
      "$\\max_a \\epsilon(a)$ 由 $\\epsilon$ 的<em>形状</em>决定（它在哪里最大），"
      "而一步误差量的是它的<em>均值</em>。"
      "两者可以任意脱钩——第 2 节的例子里一步误差 $3.95\\%$ 而高估 $251\\%$，"
      "而练习 1 实测把训练量从 $20$ 条加到 $2000$ 条后前者降了、后者没降。"),
])),

("build", "把一个可交互世界模型的验收拆开", "".join([
    P("综合本模块与模块 03，一个「可交互视频世界模型」的验收至少有四个互不替代的部分："),
    TABLE(["验收项", "量什么", "本课的方法", "不做会怎样"],
          [["① 一步保真", "分布内的一步预测误差", "常规留出集",
            "什么都不知道（但这一项<strong>远远不够</strong>）"],
           ["② 动作可辨识", "喂错动作时误差是否变大；"
            "潜在动作能否被稳定反推", "本模块第 3 节的三列对比",
            "动作条件可能是<strong>装饰性</strong>的（收益 $1.01\\times$）"],
           ["③ 长程分布", "生成批 vs 真实批的能量比与平稳性",
            "模块 03 的批级诊断", "分不清「变静止」与「还在累积」"],
           ["④ <strong>抗优化</strong>", "让优化器最大化模型回报，看真实回报",
            "本模块第 2 节", "把 $3.95\\%$ 的一步误差当成能规划的证据（实际高估 $251\\%$）"]]),
    P("四项的关系是<strong>递进而不是并列</strong>："
      "① 是必要条件；② 决定「交互」是不是真的；"
      "③ 决定长视频能不能用；④ 决定能不能给智能体用。"
      "<strong>而 ① 通过不蕴含任何后三项</strong>——本模块第 2 节就是这句话的量化。"),
    ASCII("""
   一步误差 0.0395  ->  ① 通过
        |
        +--> ② 动作条件的收益？   可能只有 1.01x（动作幅度小/噪声大时）
        |
        +--> ③ 长程能量比？        可能只有真值的 0.35（模块 03）
        |
        +--> ④ 抗优化？            回报高估 251%（本模块第 2 节）

   四项互不蕴含。而工程上通常只报 ①。
""".strip("\n")),
    P("而这四项都不需要真实的视频模型就能先想清楚："
      "① 是常规留出集；② 是本模块第 3 节的三列对比；"
      "③ 是模块 03 的批级诊断；④ 是本模块第 2 节的抗优化测试。"
      "四项<strong>合起来只需要一个动作条件的一步预测器</strong>，"
      "而这正是本课全部实验的规模。"),
    CALLOUT("paper", "本课与 C41-04 的分工，最后说一次",
            "C41 模块 04 已经完整覆盖了「有了模型之后怎么规划」："
            "MPC 随机打靶、Dyna 的经验混合、模型误差在多步 rollout 中的累积、"
            "以及基于模型 vs 无模型的权衡。"
            "本模块<strong>不重复</strong>那些内容，只做两件 C41-04 没做的事："
            "① 把「被动生成」与「主动规划」在<em>同一个模型</em>上量出量级差（$-13\\%$ vs $+251\\%$）；"
            "② 把「动作条件值多少」与「分布偏移什么时候真的伤人」"
            "量成两条可以直接用来做验收的规则。"),
])),
]

NB = [
md("""# C77 模块 04 · 世界模型

三件事：

1. **同一个模型两种用法**：被动 rollout 高估 $-13.0\\%$，主动规划高估 $+251.2\\%$；
2. **动作条件的收益** $=$ 动作在状态变化里占的方差份额（$1.01\\times$ 到 $28.23\\times$），
   而**喂错动作比不喂更糟**；
3. **分布偏移本身不是问题，误配 $\\times$ 偏移才是**。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import numpy as np

DS, DA = 4, 2                       # 状态维、动作维
_r0 = np.random.default_rng(0)
A = _r0.normal(0, 0.5, (DS, DS))
A *= 0.9 / max(abs(np.linalg.eigvals(A)).max(), 1e-9)     # 谱半径 0.9（稳定）
B = _r0.normal(0, 0.8, (DS, DA))
W = _r0.normal(0, 1, DS)                                   # 奖励权重 r = W·s

def step(s, a, saturate, rng=None, noise=0.02):
    '''真系统的一步。saturate=True 时执行器饱和（tanh）—— 线性模型对它是误配的。'''
    e = 0.0 if rng is None else rng.normal(0, noise, np.shape(s))
    u = np.tanh(a) if saturate else a
    return s @ A.T + u @ B.T + e if np.ndim(s) > 1 else A @ s + B @ u + e

print(f'状态维 {DS}, 动作维 {DA}, 真系统谱半径 {abs(np.linalg.eigvals(A)).max():.4f}')
print('奖励 r = W·s；真系统的执行器**饱和**（tanh），而模型类是线性的。')""" ),

md("""## 1. 训练一个动作条件的一步预测器

用 $a \\sim U[-0.3, 0.3]$ 收集数据，拟合线性模型 $\\hat s_{t+1} = \\hat A s_t + \\hat B a_t$。"""),

code("""def collect(ntraj, H, amax, seed, saturate=True, noise=0.02):
    r = np.random.default_rng(seed)
    X, U, Y = [], [], []
    for _ in range(ntraj):
        s = r.normal(0, 1, DS)
        for _ in range(H):
            a = r.uniform(-amax, amax, DA)
            s2 = A @ s + B @ (np.tanh(a) if saturate else a) + r.normal(0, noise, DS)
            X.append(s); U.append(a); Y.append(s2)
            s = s2
    return np.array(X), np.array(U), np.array(Y)

def fit_model(X, U, Y):
    M = np.linalg.lstsq(np.column_stack([X, U]), Y, rcond=None)[0]
    return M[:DS].T, M[DS:].T          # Â, B̂

Xtr, Utr, Ytr = collect(300, 20, 0.3, 1)
Ah, Bh = fit_model(Xtr, Utr, Ytr)
Xte, Ute, Yte = collect(100, 20, 0.3, 999)
onestep = float(np.linalg.norm((Xte @ Ah.T + Ute @ Bh.T) - Yte)
                / np.linalg.norm(Yte - Yte.mean(0)))
print(f'训练: 300 条轨迹 x 20 步，动作 ∈ [-0.3, 0.3]')
print(f'**分布内的一步预测相对误差 = {onestep:.5f}** —— 一个很好的模型')
assert onestep < 0.06, '分布内一步误差应很小'
print()
print('接下来两种用法都用**这一个**模型。')""" ),

md("""## 2. 被动 rollout vs 主动规划

对线性模型来说「动作越大收益越大」，所以规划的最优解一定顶在动作边界上。
模型是线性的，最优开环动作序列可以解析写出。"""),

code("""H = 10

def roll_model(s0, acts):
    s = s0.copy(); out = []
    for a in acts:
        s = Ah @ s + Bh @ a
        out.append(s.copy())
    return np.array(out)

def roll_true(s0, acts, seed=5, noise=0.02):
    r = np.random.default_rng(seed)
    s = s0.copy(); out = []
    for a in acts:
        s = A @ s + B @ np.tanh(a) + r.normal(0, noise, DS)
        out.append(s.copy())
    return np.array(out)

def plan(apl):
    '''最大化模型预测的累积奖励 sum_t W·ŝ_t，动作被 [-apl, apl] 约束。

    对线性模型，d(累积奖励)/d a_k = sum_{t>k} W·Â^(t-1-k)·B̂ 是常向量，
    所以最优解就是沿它顶到边界。
    '''
    G = np.zeros((H, DA))
    for k in range(H):
        g = np.zeros(DA)
        for t in range(k+1, H+1):
            g += W @ np.linalg.matrix_power(Ah, t-1-k) @ Bh
        G[k] = g
    return np.clip(1e9 * G, -apl, apl)          # 顶到边界

s0 = np.random.default_rng(77).normal(0, 1, DS)
print('  a_pl   |a| 均值   主动规划: 模型预测   真实回报   高估      相对高估')
active = {}
for apl in (0.3, 0.5, 1.0, 2.0, 4.0):
    acts = plan(apl)
    pm, pt = roll_model(s0, acts), roll_true(s0, acts)
    rm, rt = float(np.sum(W @ pm.T)), float(np.sum(W @ pt.T))
    active[apl] = (rm, rt, (rm-rt)/max(abs(rt), 1e-9))
    print(f'  {apl:4.1f}   {np.abs(acts).mean():8.3f}   {rm:17.3f}   {rt:9.3f}   '
          f'{rm-rt:+8.3f}   {active[apl][2]*100:7.1f}%')

print()
print('  a_pl   被动 rollout（同幅度**随机**动作）: 模型预测   真实回报   相对高估')
passive = {}
for apl in (0.3, 0.5, 1.0, 2.0, 4.0):
    acts = np.random.default_rng(31).uniform(-apl, apl, (H, DA))
    pm, pt = roll_model(s0, acts), roll_true(s0, acts)
    rm, rt = float(np.sum(W @ pm.T)), float(np.sum(W @ pt.T))
    passive[apl] = (rm, rt, (rm-rt)/max(abs(rt), 1e-9))
    print(f'  {apl:4.1f}   {rm:41.3f}   {rt:9.3f}   {passive[apl][2]*100:7.1f}%')

# 主动的高估远大于被动，且随动作范围单调增长
for apl in (0.5, 1.0, 2.0, 4.0):
    assert active[apl][2] > abs(passive[apl][2]), \\
        f'a_pl={apl}: 主动的高估应大于被动'
_seq = [active[a][2] for a in (0.3, 0.5, 1.0, 2.0, 4.0)]
for i in range(1, len(_seq)):
    assert _seq[i] > _seq[i-1], f'主动的相对高估应单调增长：{_seq}'
assert active[4.0][2] > 2.0, f'a_pl=4 时应高估 >200%，实测 {active[4.0][2]*100:.1f}%'
assert passive[4.0][2] < 0, f'被动应是**低估**（负号），实测 {passive[4.0][2]*100:.1f}%'

print()
print(f'✅ 一步误差 {onestep:.5f}（3.95%）的同一个模型:')
print(f'   主动规划 a_pl=4.0 时回报高估 {active[4.0][2]*100:+.1f}%')
print(f'   被动 rollout 同幅度时是 {passive[4.0][2]*100:+.1f}%（**负号** = 低估）')
print(f'   量级差 {active[4.0][2]/abs(passive[4.0][2]):.1f} 倍，且符号相反')
print()
print('   机制：线性模型认为「动作越大收益越大」（它没有饱和），')
print('   优化器于是把 |a| 顶到边界，而真系统在那里早已 tanh 饱和 ——')
print('   **优化器不是在利用噪声，它是在最大化模型的结构误差**。')
print()
print('   -> 所以「一步预测准确率」不是「能不能被智能体用来规划」的证据。')
print('      要评估后者，必须让一个优化器去攻击它，然后看真实回报。')""" ),

md("""## 3. 动作条件值多少

比较三种预测器：只看 $s$、看 $s{+}a$、看 $s{+}$**打乱的** $a$。"""),

code("""def gen_pairs(n, amax, noise, seed, saturate=False):
    r = np.random.default_rng(seed)
    S = r.normal(0, 1, (n, DS))
    Aa = r.uniform(-amax, amax, (n, DA))
    U = np.tanh(Aa) if saturate else Aa
    Y = S @ A.T + U @ B.T + r.normal(0, noise, (n, DS))
    return S, Aa, Y

def fit_pred(Xtr, Ytr, Xte, Yte):
    M = np.linalg.lstsq(np.column_stack([np.ones(len(Xtr)), Xtr]), Ytr, rcond=None)[0]
    P = np.column_stack([np.ones(len(Xte)), Xte]) @ M
    return float(np.sqrt(np.sum((P - Yte)**2) / np.sum((Yte - Yte.mean(0))**2)))

print('  动作幅度   噪声 sd   只看 s     看 s+a    看 s+**错的** a   条件化的收益')
gains = {}
for amax in (0.1, 0.5, 1.0, 3.0):
    for sn in (0.05, 0.50):
        Str, Atr, Ytr2 = gen_pairs(20_000, amax, sn, 1)
        Ste, Ate, Yte2 = gen_pairs(5_000, amax, sn, 2)
        e_s = fit_pred(Str, Ytr2, Ste, Yte2)
        e_sa = fit_pred(np.column_stack([Str, Atr]), Ytr2,
                        np.column_stack([Ste, Ate]), Yte2)
        Ash = Ate[np.random.default_rng(9).permutation(len(Ate))]
        e_bad = fit_pred(np.column_stack([Str, Atr]), Ytr2,
                         np.column_stack([Ste, Ash]), Yte2)
        gains[(amax, sn)] = (e_s, e_sa, e_bad)
        print(f'  {amax:8.1f}   {sn:7.2f}   {e_s:.5f}   {e_sa:.5f}   {e_bad:.5f}       '
              f'{e_s/e_sa:8.2f}x')

# 收益随动作幅度上升、随噪声上升而下降
for sn in (0.05, 0.50):
    seq = [gains[(am, sn)][0]/gains[(am, sn)][1] for am in (0.1, 0.5, 1.0, 3.0)]
    for i in range(1, len(seq)):
        assert seq[i] > seq[i-1], f'噪声 {sn}: 收益应随动作幅度上升 {seq}'
for am in (0.1, 0.5, 1.0, 3.0):
    g_low = gains[(am, 0.05)][0]/gains[(am, 0.05)][1]
    g_high = gains[(am, 0.50)][0]/gains[(am, 0.50)][1]
    assert g_high < g_low, f'幅度 {am}: 噪声大时收益应更小'
# 喂错动作比不喂更糟
for key, (e_s, e_sa, e_bad) in gains.items():
    assert e_bad > e_s, f'{key}: 喂错动作应比不喂更糟（{e_bad:.5f} vs {e_s:.5f}）'

_g_min = min(gains[k][0]/gains[k][1] for k in gains)
_g_max = max(gains[k][0]/gains[k][1] for k in gains)
print()
print(f'✅ 条件化的收益从 {_g_min:.2f}x 到 {_g_max:.2f}x —— 它等于**动作在状态变化里**')
print('   **占的方差份额**：动作幅度小或环境噪声大时收益趋于 1（条件化白做）')
print('✅ 而**喂错动作比不喂动作更糟**（全部 8 种配置都成立）——')
print('   因为模型会**照着**错动作走，把一个错误的因当作真的因去外推')
print()
print('   -> 对「潜在动作」的做法（从无标注视频里学动作）有直接含义：')
print('      潜在动作的推断错误不是无害的噪声，它会让模型比不做条件更差。')
print('      所以这类系统必须额外报告**潜在动作的可辨识性**，而不只是重建质量。')""" ),

md("""## 4. 分布偏移本身不是问题

在随机动作上训练、用线性策略 $a = g \\cdot Ks$ rollout。
两个真系统：一个与模型类匹配（线性），一个误配（tanh）。"""),

code("""K = np.random.default_rng(11).normal(0, 1, (DA, DS))

def shift_experiment(saturate):
    '''返回 {g: (1 步误差, 10 步误差)}，用**固定参考尺度**归一化。'''
    rt = np.random.default_rng(1)
    n = 40_000
    S = rt.normal(0, 1, (n, DS))
    Aa = rt.uniform(-0.3, 0.3, (n, DA))
    U = np.tanh(Aa) if saturate else Aa
    Y = S @ A.T + U @ B.T + rt.normal(0, 0.05, (n, DS))
    M = np.linalg.lstsq(np.column_stack([S, Aa]), Y, rcond=None)[0]
    Ah2, Bh2 = M[:DS].T, M[DS:].T
    ref = float(np.sqrt(np.mean(Y**2)))            # 固定参考尺度
    out = {}
    for g in (0.0, 0.1, 0.3, 1.0, 3.0):
        rr = np.random.default_rng(4)
        m = 4_000
        s0b = rr.normal(0, 1, (m, DS))
        a1 = g * (s0b @ K.T)
        u1 = np.tanh(a1) if saturate else a1
        y1 = s0b @ A.T + u1 @ B.T + rr.normal(0, 0.05, (m, DS))
        p1 = s0b @ Ah2.T + a1 @ Bh2.T
        e1 = float(np.sqrt(np.mean((p1 - y1)**2))) / ref
        st, sm = s0b.copy(), s0b.copy()
        r2 = np.random.default_rng(6)
        for _ in range(10):
            at, am = g * (st @ K.T), g * (sm @ K.T)
            ut = np.tanh(at) if saturate else at
            st = st @ A.T + ut @ B.T + r2.normal(0, 0.05, (m, DS))
            sm = sm @ Ah2.T + am @ Bh2.T
        e10 = float(np.sqrt(np.mean((sm - st)**2))) / ref
        out[g] = (e1, e10, float(np.abs(a1).mean()))
    return out, ref

res_ok, ref_ok = shift_experiment(saturate=False)
res_mis, ref_mis = shift_experiment(saturate=True)
print('  策略增益 g   |a| 均值    匹配: 1 步    匹配: 10 步    误配: 1 步    误配: 10 步')
for g in (0.0, 0.1, 0.3, 1.0, 3.0):
    print(f'  {g:10.1f}   {res_ok[g][2]:8.3f}    {res_ok[g][0]:9.5f}    '
          f'{res_ok[g][1]:10.5f}    {res_mis[g][0]:9.5f}    {res_mis[g][1]:11.5f}')

# 匹配时一步误差平坦
_flat = res_ok[3.0][0] / res_ok[0.0][0]
assert _flat < 1.05, f'匹配时一步误差应平坦，实测涨 {_flat:.3f} 倍'
# 误配时一步误差大幅上升
_blow = res_mis[3.0][0] / res_mis[0.0][0]
assert _blow > 20, f'误配时一步误差应大幅上升，实测涨 {_blow:.1f} 倍'

print()
print(f'✅ **匹配**时一步误差在策略幅度跨 30 倍下几乎不变:'
      f' {res_ok[0.0][0]:.5f} -> {res_ok[3.0][0]:.5f}（+{(_flat-1)*100:.1f}%）')
print(f'✅ **误配**时同样的偏移让一步误差涨 {_blow:.0f} 倍:'
      f' {res_mis[0.0][0]:.5f} -> {res_mis[3.0][0]:.5f}')
print()
print('⚠️  10 步那两列有混淆因素：g=3 时闭环系统本身不稳定')
_rho = max(abs(np.linalg.eigvals(A + B @ (3.0*K))))
print(f'    ρ(A + B·3K) = {_rho:.3f} > 1，所以真实与模型轨迹**都**发散 ——')
print(f'    {res_ok[3.0][1]:.1f} 这个数里有很大一部分不是模型误差。')
print('    干净的信号在**一步**那两列。')
assert _rho > 1.0, 'g=3 时闭环应不稳定（这正是混淆因素的来源）'
print()
print('   统一的说法：**分布偏移本身不是问题，误配 × 偏移才是**。')
print('   一个正确指定的线性模型在没见过的地方外推得同样好。')
print('   -> 这解释了为什么「加大训练动作范围」有效（缩小偏移）')
print('      而「加大数据量」无效（只减小估计误差，不动误配）。')""" ),

md("""## ✏️ 练习 1：抗优化测试

正文说「要评估能不能规划，必须让优化器去攻击模型」。
把它做成一个可复用的测试：实现 `adversarial_gap(Ah, Bh, apl, H, seed)`，
返回 `(模型预测回报, 真实回报, 相对高估)`。"""),

code("""def adversarial_gap(Ah_, Bh_, apl, H=10, seed=77, saturate=True):
    '''抗优化测试：用模型规划最优开环动作，再在真系统上执行。

    参数
    ----
    Ah_, Bh_ : 待测模型
    apl      : 允许的动作幅度
    H        : 规划视野
    seed     : 初始状态的 seed
    saturate : 真系统是否饱和

    返回
    ----
    (r_model, r_true, rel_gap)
    '''
    s0_ = np.random.default_rng(seed).normal(0, 1, DS)
    # TODO: ① 算梯度 G[k] = sum_{t>k} W·Ah_^(t-1-k)·Bh_，把动作顶到 ±apl；
    #       ② 用 (Ah_, Bh_) rollout 得模型预测的状态序列，回报 = sum W·s；
    #       ③ 在真系统上执行同样的动作（noise=0.02, seed=5），得真实回报；
    #       ④ 返回 (r_model, r_true, (r_model-r_true)/|r_true|)
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 用不同数据量训练的模型，抗优化差距如何变化:')
print('    训练轨迹数   分布内一步误差   a_pl=4 的相对高估')
_gaps = {}
for _nt in (20, 100, 300, 2000):
    _X, _U, _Y = collect(_nt, 20, 0.3, 1)
    _Ah, _Bh = fit_model(_X, _U, _Y)
    _e1 = float(np.linalg.norm((Xte @ _Ah.T + Ute @ _Bh.T) - Yte)
                / np.linalg.norm(Yte - Yte.mean(0)))
    _rm, _rt, _rel = adversarial_gap(_Ah, _Bh, 4.0)
    _gaps[_nt] = (_e1, _rel)
    print(f'    {_nt:10d}   {_e1:14.5f}   {_rel*100:16.1f}%')

# 加数据能降低一步误差，但**不能**降低抗优化差距（因为那是误配造成的）
_e_small, _e_large = _gaps[20][0], _gaps[2000][0]
assert _e_large < _e_small, '加数据应降低一步误差'
_rel_small, _rel_large = _gaps[20][1], _gaps[2000][1]
assert _rel_large > 1.5, f'加数据后抗优化差距仍应很大，实测 {_rel_large*100:.1f}%'
print()
print(f'✅ 一步误差从 {_e_small:.5f} 降到 {_e_large:.5f}（加数据有效）')
print(f'✅ 而抗优化的相对高估仍是 {_rel_large*100:.0f}% —— **加数据修不了它**')
print('   因为它来自模型类的误配（线性 vs tanh），不是估计误差。')

print()
print('  (b) 动作范围是这个差距的主要旋钮:')
print('    a_pl    相对高估')
_X, _U, _Y = collect(300, 20, 0.3, 1)
_Ah, _Bh = fit_model(_X, _U, _Y)
_prev = None
for _apl in (0.3, 0.5, 1.0, 2.0, 4.0, 8.0):
    _, _, _rel = adversarial_gap(_Ah, _Bh, _apl)
    print(f'    {_apl:4.1f}    {_rel*100:8.1f}%')
    if _prev is not None:
        assert _rel > _prev, f'相对高估应随 a_pl 单调增长'
    _prev = _rel

print()
print('✅ 相对高估随允许的动作范围单调增长（6 档全对）')
print()
print('   -> 两条可操作的结论:')
print('      · 抗优化测试必须**报告它用的动作范围** —— 否则数字不可比。')
print('      · 限制规划时的动作范围到训练分布附近，是最直接的缓解手段')
print('        （这正是 C41-04 里「悲观化 / 信任域」那一类做法的最简形式）。')""" ),

md("""## ✏️ 练习 2：动作条件的收益有闭式

正文说「收益等于动作在状态变化里占的方差份额」。把它写成公式并验证。

实现 `predicted_gain(amax, noise)`：用**解析**方式预测条件化的收益比
（只看 $s$ 的误差 / 看 $s{+}a$ 的误差），然后与模拟对照。

提示：$\\Delta s = (A{-}I)s + Ba + \\varepsilon$。看 $s$ 时残差方差是
$\\text{Var}(Ba) + \\sigma^2$；看 $s{+}a$ 时是 $\\sigma^2$。
误差比是这两个的平方根之比。"""),

code("""def predicted_gain(amax, noise):
    '''条件化收益的解析预测。

    动作 a ~ U[-amax, amax]（每维独立），Var(a_i) = amax^2/3。
    只看 s   : 残差方差 = trace(B Cov(a) B^T) + DS*noise^2
    看 s+a   : 残差方差 = DS*noise^2
    收益 = sqrt(前者 / 后者)

    参数
    ----
    amax  : 动作幅度
    noise : 每维的噪声 sd

    返回
    ----
    float : 预测的收益比
    '''
    # TODO: Cov(a) = (amax^2/3) * I_DA；
    #       num = trace(B @ Cov @ B.T) + DS*noise^2；den = DS*noise^2；
    #       返回 sqrt(num/den)
    raise NotImplementedError"""),

code("""# 自测
print('  动作幅度   噪声 sd   解析预测的收益   模拟的收益   相对差')
for _am in (0.1, 0.5, 1.0, 3.0):
    for _sn in (0.05, 0.50):
        _pred = predicted_gain(_am, _sn)
        _e_s, _e_sa, _ = gains[(_am, _sn)]
        _emp = _e_s / _e_sa
        print(f'  {_am:8.1f}   {_sn:7.2f}   {_pred:14.3f}   {_emp:11.3f}   '
              f'{abs(_pred-_emp)/_emp*100:6.1f}%')
        assert abs(_pred - _emp) / _emp < 0.20, \\
            f'幅度 {_am}, 噪声 {_sn}: 解析 {_pred:.3f} vs 模拟 {_emp:.3f}'

# 极限行为
assert abs(predicted_gain(0.0, 0.05) - 1.0) < 1e-9, '动作幅度为 0 时收益应为 1'
_big = predicted_gain(100.0, 0.05)
assert _big > 100, '动作幅度极大时收益应极大'
print()
print(f'✅ 解析预测与模拟在 8 种配置上都吻合到 20% 以内')
print(f'✅ 极限：amax=0 时收益恰为 1.000；amax=100 时是 {_big:.0f}')
print()
print('   闭式因此给出一个**事前**判据：在收集数据之前就能算出')
print('   「做动作条件能带来多少」—— 只需要知道动作的方差与环境噪声的量级。')
print('   收益接近 1 时，「可交互」这件事在这个环境里是装饰性的。')""" ),

md("""## ✏️ 练习 3：三种误差下界，而不是两种

正文的严谨版把误差分成估计误差（随 $n$ 消失）与逼近误差（不消失）。
实测会发现还有**第三种**：观测噪声底。

实现 `error_decomposition(ntraj_list, g, saturate)`：返回每个训练量下的
一步误差（在策略增益 $g$ 的偏移分布上评估），用它把三种下界分开。"""),

code("""def error_decomposition(ntraj_list, g=1.0, saturate=True, seed=1):
    '''不同训练量下的一步误差（在策略增益 g 的偏移分布上评估）。

    参数
    ----
    ntraj_list : 训练轨迹数的列表
    g          : 评估时的策略增益（g=0 表示动作恒为 0）
    saturate   : 真系统是否饱和（误配）
    seed       : 训练数据 seed

    返回
    ----
    dict : ntraj -> 一步相对误差
    '''
    rr = np.random.default_rng(4)
    m = 4_000
    s0b = rr.normal(0, 1, (m, DS))
    a_ev = g * (s0b @ K.T)
    u_ev = np.tanh(a_ev) if saturate else a_ev
    y_ev = s0b @ A.T + u_ev @ B.T + rr.normal(0, 0.05, (m, DS))
    # TODO: 对每个 nt：用 collect(nt, 20, 0.3, seed, saturate=saturate, noise=0.05)
    #       拟合模型；在 (s0b, a_ev) 上预测；
    #       误差 = ||pred − y_ev|| / ||y_ev − mean(y_ev)||
    raise NotImplementedError"""),

code("""# 自测
_NTS = (10, 30, 100, 300, 1000, 3000)
print('  情形          ' + '  '.join(f'n={n:<6d}' for n in _NTS) + '   末/首   末段比')
_rows = {}
for _tag, _sat, _g in [('匹配 g=0', False, 0.0), ('误配 g=0', True, 0.0),
                       ('匹配 g=3', False, 3.0), ('误配 g=3', True, 3.0)]:
    _d = error_decomposition(_NTS, g=_g, saturate=_sat)
    _rows[_tag] = _d
    print(f'  {_tag:12s}  ' + '  '.join(f'{_d[n]:.5f}' for n in _NTS) +
          f'   {_d[_NTS[-1]]/_d[_NTS[0]]:.3f}   {_d[_NTS[-1]]/_d[_NTS[-3]]:.3f}')

# ① g=0 时匹配与误配**完全相同** —— 误配只在动作通道里
_m0, _s0 = _rows['匹配 g=0'], _rows['误配 g=0']
for _n in _NTS:
    assert abs(_m0[_n] - _s0[_n]) < 1e-3, \\
        f'g=0 时匹配与误配应几乎相同（n={_n}: {_m0[_n]:.5f} vs {_s0[_n]:.5f}）'
print()
print('① g=0 时匹配与误配的曲线**几乎逐点相同** ——')
print('   因为 tanh 的误配只在动作通道里，而 g=0 时动作恒为 0。')
print('   -> 所以在**训练分布**（或无动作）上做的诊断根本看不见误配。')

# ② g=0 的误差被**观测噪声底**主导：n 涨 300 倍几乎不降
_noise_floor = 0.05 * np.sqrt(DS) / float(np.sqrt(np.mean(
    (np.random.default_rng(4).normal(0, 1, (4000, DS)) @ A.T)**2) * DS))
assert _m0[_NTS[-1]] / _m0[_NTS[0]] > 0.85, \\
    f'g=0 时误差应几乎不随 n 下降（噪声底），实测末/首 {_m0[_NTS[-1]]/_m0[_NTS[0]]:.3f}'
print()
print(f'② g=0 的误差从 {_m0[_NTS[0]]:.5f} 只降到 {_m0[_NTS[-1]]:.5f}（末/首 '
      f'{_m0[_NTS[-1]]/_m0[_NTS[0]]:.3f}）—— n 涨 300 倍几乎不动')
print('   它被**观测噪声底**主导（每维 σ=0.05），而不是估计误差。')
print('   -> 这是第三种下界：加数据无用，但它也不表示模型有问题。')

# ③ 匹配 + 大偏移：误差随 n 明显下降（估计误差可见）
_m3 = _rows['匹配 g=3']
assert _m3[_NTS[-1]] / _m3[_NTS[0]] < 0.6, \\
    f'匹配+大偏移时误差应明显下降，实测末/首 {_m3[_NTS[-1]]/_m3[_NTS[0]]:.3f}'
print()
print(f'③ 匹配 + 大偏移：{_m3[_NTS[0]]:.5f} -> {_m3[_NTS[-1]]:.5f}'
      f'（末/首 {_m3[_NTS[-1]]/_m3[_NTS[0]]:.3f}）—— 估计误差可见，加数据有效')

# ④ 误配 + 大偏移：饱和在一个高水平（逼近误差主导）
_s3 = _rows['误配 g=3']
_late = _s3[_NTS[-1]] / _s3[_NTS[-3]]
assert _late > 0.95, f'误配+大偏移时误差应已饱和，实测末段比 {_late:.3f}'
assert _s3[_NTS[-1]] > 20 * _m3[_NTS[-1]], \\
    f'误配的饱和水平应远高于匹配（{_s3[_NTS[-1]]:.4f} vs {_m3[_NTS[-1]]:.4f}）'
print()
print(f'④ 误配 + 大偏移：饱和在 {_s3[_NTS[-1]]:.4f}（末段比 {_late:.3f}）——')
print(f'   那个水平就是**逼近误差**，是匹配情形的 {_s3[_NTS[-1]]/_m3[_NTS[-1]]:.0f} 倍，')
print('   加数据到无穷也降不下去。')

print()
print('✅ 三种下界被分开:')
print(f'   · 观测噪声底  : g=0 的 {_m0[_NTS[-1]]:.5f}（加数据无用，但无害）')
print(f'   · 估计误差    : 匹配 g=3 从 {_m3[_NTS[0]]:.5f} 降到 {_m3[_NTS[-1]]:.5f}（加数据有效）')
print(f'   · 逼近误差    : 误配 g=3 饱和在 {_s3[_NTS[-1]]:.4f}（加数据无用，且有害）')
print()
print('   可执行的诊断：画误差 vs 训练量的曲线，看它**在什么水平上变平**:')
print('     · 平在噪声底附近  -> 一切正常')
print('     · 还在下降        -> 加数据/加算力有用')
print('     · 平在远高于噪声底 -> 问题在模型类或数据分布，加数据无用')
print()
print('   而这个诊断必须在**目标分布**（含偏移）上做 —— 见 ①：')
print('   g=0 时匹配与误配的曲线逐点相同，完全掩盖了后者的问题。')"""),

md("""## ✏️ 练习 4：四项验收之间到底哪些独立

正文说四项验收「互不蕴含」。这个练习把它测清楚——
而结果比那句话更细：**有一对是耦合的**。

实现 `acceptance_report(Ah, Bh, ...)`，一次跑完四项并返回一个字典。"""),

code("""def acceptance_report(Ah_, Bh_, amax_train=0.3, apl=4.0, verbose=True):
    '''可交互世界模型的四项验收。

    返回
    ----
    dict : {'onestep', 'action_gain', 'wrong_action_penalty',
            'adversarial_rel_gap', 'rho',
            'pass_onestep', 'pass_action', 'pass_longrange', 'pass_adversarial'}
      onestep              : 分布内一步相对误差
      action_gain          : 条件化收益（不给动作的误差 / 给动作的误差）
      wrong_action_penalty : 喂错动作的误差 / 不给动作的误差（>1 表示错动作更糟）
      adversarial_rel_gap  : 抗优化测试的相对高估
      rho                  : ρ(Â)，作为③长程分布的代理（见模块 03 第 1 节）
    '''
    # ① 一步保真
    e1 = float(np.linalg.norm((Xte @ Ah_.T + Ute @ Bh_.T) - Yte)
               / np.linalg.norm(Yte - Yte.mean(0)))
    # ② 动作可辨识
    Ssm, Asm, Ysm = gen_pairs(5_000, amax_train, 0.05, 2, saturate=True)
    den = np.sqrt(np.sum((Ysm - Ysm.mean(0))**2))
    e_sa = float(np.sqrt(np.sum((Ssm @ Ah_.T + Asm @ Bh_.T - Ysm)**2)) / den)
    e_s = float(np.sqrt(np.sum((Ssm @ Ah_.T - Ysm)**2)) / den)
    Ash = Asm[np.random.default_rng(9).permutation(len(Asm))]
    e_bad = float(np.sqrt(np.sum((Ssm @ Ah_.T + Ash @ Bh_.T - Ysm)**2)) / den)
    # ③ 长程（用 ρ(Â) 作代理）
    rho = float(max(abs(np.linalg.eigvals(Ah_))))
    # ④ 抗优化
    _, _, rel = adversarial_gap(Ah_, Bh_, apl)
    # TODO: 组装返回字典，四个布尔判定的阈值:
    #       pass_onestep     : e1 < 0.10
    #       pass_action      : (e_s/e_sa) > 1.5 且 (e_bad/e_s) > 1.05
    #       pass_longrange   : rho < 1.0
    #       pass_adversarial : |rel| < 0.30
    #       verbose=True 时打印四行
    raise NotImplementedError"""),

code("""# 自测
_Xg, _Ug, _Yg = collect(2000, 20, 0.3, 1)
_Ah_good, _Bh_good = fit_model(_Xg, _Ug, _Yg)

print('=== 模型 A：正常训练（线性模型 / tanh 真系统）===')
_rA = acceptance_report(_Ah_good, _Bh_good)
assert _rA['pass_onestep'] and _rA['pass_action'] and _rA['pass_longrange']
assert not _rA['pass_adversarial'], '④ 应失败（线性 vs tanh 的误配）'
print(f'  -> ① ② ③ 全通过而 ④ 失败：**① 不蕴含 ④**')
print()

print('=== 模型 C：Â 的谱半径被放大到 1.05 ===')
_Ah_bad = _Ah_good * (1.05 / max(abs(np.linalg.eigvals(_Ah_good)).max(), 1e-9))
_rC = acceptance_report(_Ah_bad, _Bh_good)
assert not _rC['pass_longrange'], '③ 应失败（ρ>1）'
print(f'  -> ρ(Â) = {_rC["rho"]:.4f} > 1，③ 失败')
print()

print('=== 动作通道逐级退化：① 与 ② 会不会分开？===')
print('  B̂ 的缩放   一步误差   ① 通过   动作收益   错动作惩罚   ② 通过')
_pairs = []
for _sc in (1.0, 0.6, 0.3, 0.1, 0.0):
    _r = acceptance_report(_Ah_good, _sc * _Bh_good, verbose=False)
    _pairs.append((_r['pass_onestep'], _r['pass_action']))
    print(f'  {_sc:9.2f}   {_r["onestep"]:.5f}   {str(_r["pass_onestep"]):6s}  '
          f'{_r["action_gain"]:8.3f}   {_r["wrong_action_penalty"]:10.3f}   '
          f'{_r["pass_action"]}')

# 关键：不存在「① 通过而 ② 失败」的缩放
assert not any(p1 and not p2 for p1, p2 in _pairs), \\
    f'实测里不存在 ①通过 ②失败 的配置：{_pairs}'
print()
print('⚠️  **没有哪个缩放能让 ① 通过而 ② 失败** —— ① 与 ② 是**耦合**的。')
print('   原因：两者都在量「动作通道被建模得多好」。')
print('   $\\\\hat B$ 一退化，分布内的一步误差立刻变差（因为训练数据里动作是有效的）。')

print()
print('=== 那 ② 什么时候会单独失败？当动作**输入**在部署时是错的 ===')
_r_full = acceptance_report(_Ah_good, _Bh_good, verbose=False)
print(f'  模型完好（① 通过，一步误差 {_r_full["onestep"]:.5f}）')
print(f'  而喂错动作时的误差 / 不给动作的误差 = {_r_full["wrong_action_penalty"]:.3f}x')
assert _r_full['wrong_action_penalty'] > 1.05
print('  -> 这正是「潜在动作推断错误」的情形：模型没问题，输入有问题。')
print('     此时 ① 完全正常，而实际交互质量比不做动作条件更差。')
print('     所以 ② 必须同时报告**两个**量：条件化的收益，与错动作的惩罚。')

print()
print('=== 四项之间的蕴含关系（实测）===')
print('  ① -> ②   耦合（动作通道退化时一起坏）')
print('  ① -> ③   **不蕴含**（模型 C：① 通过而 ρ=1.05）')
print('  ① -> ④   **不蕴含**（模型 A：① 通过而 ④ 高估 '
      f'{_rA["adversarial_rel_gap"]*100:+.0f}%）')
print()
print(f'✅ 模型 A：① ② ③ 通过、④ 失败（{_rA["adversarial_rel_gap"]*100:+.0f}%）')
print(f'✅ 模型 C：ρ(Â) = {_rC["rho"]:.4f} > 1，③ 失败')
print('✅ 而 ① 与 ② 在动作通道退化时**一起**坏 —— 这修正了「四项互不蕴含」这句话')
print()
print('   -> 可操作的结论：工程上通常只报 ①，而它**不蕴含** ③ 与 ④。')
print('      ② 虽与 ① 耦合，但它的「错动作惩罚」那一半仍然必须单独报 ——')
print('      因为那一半量的是部署时的输入质量，不是模型质量。')"""),

md("""## 📖 参考答案"""),

code("""def adversarial_gap(Ah_, Bh_, apl, H=10, seed=77, saturate=True):
    '''抗优化测试：用模型规划最优开环动作，再在真系统上执行。'''
    s0_ = np.random.default_rng(seed).normal(0, 1, DS)
    G = np.zeros((H, DA))
    for k in range(H):
        g = np.zeros(DA)
        for t in range(k+1, H+1):
            g += W @ np.linalg.matrix_power(Ah_, t-1-k) @ Bh_
        G[k] = g
    acts = np.clip(1e9 * G, -apl, apl)
    s = s0_.copy(); r_model = 0.0
    for a in acts:
        s = Ah_ @ s + Bh_ @ a
        r_model += float(W @ s)
    rr = np.random.default_rng(5)
    s = s0_.copy(); r_true = 0.0
    for a in acts:
        u = np.tanh(a) if saturate else a
        s = A @ s + B @ u + rr.normal(0, 0.02, DS)
        r_true += float(W @ s)
    return r_model, r_true, (r_model - r_true) / max(abs(r_true), 1e-9)

def predicted_gain(amax, noise):
    '''条件化收益的解析预测。'''
    cov = (amax**2 / 3.0) * np.eye(DA)
    num = float(np.trace(B @ cov @ B.T)) + DS * noise**2
    den = DS * noise**2
    return float(np.sqrt(num / den))

def error_decomposition(ntraj_list, g=1.0, saturate=True, seed=1):
    '''不同训练量下的一步误差（在偏移分布上评估）。'''
    rr = np.random.default_rng(4)
    m = 4_000
    s0b = rr.normal(0, 1, (m, DS))
    a_ev = g * (s0b @ K.T)
    u_ev = np.tanh(a_ev) if saturate else a_ev
    y_ev = s0b @ A.T + u_ev @ B.T + rr.normal(0, 0.05, (m, DS))
    den = float(np.linalg.norm(y_ev - y_ev.mean(0)))
    out = {}
    for nt in ntraj_list:
        Xn, Un, Yn = collect(nt, 20, 0.3, seed, saturate=saturate, noise=0.05)
        An, Bn = fit_model(Xn, Un, Yn)
        pred = s0b @ An.T + a_ev @ Bn.T
        out[nt] = float(np.linalg.norm(pred - y_ev) / den)
    return out

def acceptance_report(Ah_, Bh_, amax_train=0.3, apl=4.0, verbose=True):
    '''可交互世界模型的四项验收。'''
    e1 = float(np.linalg.norm((Xte @ Ah_.T + Ute @ Bh_.T) - Yte)
               / np.linalg.norm(Yte - Yte.mean(0)))
    Ssm, Asm, Ysm = gen_pairs(5_000, amax_train, 0.05, 2, saturate=True)
    den = np.sqrt(np.sum((Ysm - Ysm.mean(0))**2))
    e_sa = float(np.sqrt(np.sum((Ssm @ Ah_.T + Asm @ Bh_.T - Ysm)**2)) / den)
    e_s = float(np.sqrt(np.sum((Ssm @ Ah_.T - Ysm)**2)) / den)
    Ash = Asm[np.random.default_rng(9).permutation(len(Asm))]
    e_bad = float(np.sqrt(np.sum((Ssm @ Ah_.T + Ash @ Bh_.T - Ysm)**2)) / den)
    _, _, rel = adversarial_gap(Ah_, Bh_, apl)
    gain = e_s / max(e_sa, 1e-12)
    penalty = e_bad / max(e_s, 1e-12)
    rho = float(max(abs(np.linalg.eigvals(Ah_))))
    out = {'onestep': e1, 'action_gain': gain, 'wrong_action_penalty': penalty,
           'adversarial_rel_gap': rel, 'rho': rho,
           'pass_onestep': bool(e1 < 0.10),
           'pass_action': bool(gain > 1.5 and penalty > 1.05),
           'pass_longrange': bool(rho < 1.0),
           'pass_adversarial': bool(abs(rel) < 0.30)}
    if verbose:
        print(f'  ① 一步保真     : {e1:.5f}                        -> '
              f'{"通过" if out["pass_onestep"] else "失败"}')
        print(f'  ② 动作可辨识   : 收益 {gain:.3f}x, 错动作惩罚 {penalty:.3f}x -> '
              f'{"通过" if out["pass_action"] else "失败"}')
        print(f'  ③ 长程（代理）  : ρ(Â) = {rho:.4f}                  -> '
              f'{"通过" if out["pass_longrange"] else "失败"}')
        print(f'  ④ 抗优化       : 相对高估 {rel*100:+.1f}%                 -> '
              f'{"通过" if out["pass_adversarial"] else "失败"}')
    return out

print('参考答案已定义。')
print()
print('要点：')
print('  1. 抗优化差距**加数据修不了**（它来自误配），而限制动作范围能直接缓解。')
print('  2. 动作条件的收益有闭式：sqrt((tr(B Cov(a) Bᵗ) + dσ²)/(dσ²))。')
print('     它是一个**事前**判据 —— 收集数据之前就能算。')
print('  3. 误差 vs 训练量的曲线**在什么水平上变平**，区分三种下界：')
print('     噪声底（无害）/ 估计误差（加数据有用）/ 逼近误差（加数据无用且有害）。')
print('     而这个诊断必须在含偏移的目标分布上做 —— g=0 时匹配与误配的曲线逐点相同。')
print('  4. ① 不蕴含 ③ 也不蕴含 ④；但 ① 与 ② 是**耦合**的（动作通道退化时一起坏）。')
print('     ② 里「错动作惩罚」那一半量的是部署输入质量，必须单独报。')""" ),

md("""## 🧪 真实工程胶囊：世界模型的用途-验收对照表

一个世界模型「够不够好」取决于它要被怎么用。
下面这段代码把用途与验收项对应起来，并对给定模型给出
**按用途分别判定**的结论——同一个模型可以「够做视频生成」而「不够做规划」。"""),

code("""USE_CASES = {
    '离线视频生成（固定动作序列）': {
        'needs': ['onestep', 'longrange'],
        'note': '动作是录好的，没有优化器；关键是长程分布（模块 03）',
    },
    '可交互视频（用户实时操作）': {
        'needs': ['onestep', 'action', 'longrange'],
        'note': '用户不会对抗模型，但动作分布不可控 —— ② 与 ③ 都必须过',
    },
    '给智能体规划（MPC / Dyna）': {
        'needs': ['onestep', 'action', 'longrange', 'adversarial'],
        'note': '优化器会主动找模型的洞 —— ④ 是硬要求（C41 模块 04）',
    },
    '作为策略的训练环境': {
        'needs': ['onestep', 'action', 'longrange', 'adversarial'],
        'note': '策略在训练中会逐渐学会利用模型的错误 —— 与规划同级',
    },
}

def evaluate_for_uses(Ah_, Bh_, name='模型'):
    '''按用途分别判定一个世界模型够不够用。'''
    r = acceptance_report(Ah_, Bh_, verbose=False)
    rho = float(max(abs(np.linalg.eigvals(Ah_))))
    checks = {
        'onestep': (r['pass_onestep'], f"一步误差 {r['onestep']:.5f}"),
        'action': (r['pass_action'],
                   f"收益 {r['action_gain']:.2f}x / 错动作惩罚 {r['wrong_action_penalty']:.2f}x"),
        'longrange': (r['pass_longrange'], f"ρ(Â) = {rho:.4f}"),
        'adversarial': (r['pass_adversarial'],
                        f"相对高估 {r['adversarial_rel_gap']*100:+.1f}%"),
    }
    print(f'{name}')
    print('  验收项:')
    for k, (ok, detail) in checks.items():
        print(f'    [{"OK  " if ok else "FAIL"}] {k:12s} {detail}')
    print('  按用途判定:')
    verdicts = {}
    for use, spec in USE_CASES.items():
        failed = [k for k in spec['needs'] if not checks[k][0]]
        verdicts[use] = not failed
        mark = '✅ 够用' if not failed else f'❌ 不够（缺 {", ".join(failed)}）'
        print(f'    {use:26s} {mark}')
    print(f'  -> {sum(verdicts.values())}/{len(verdicts)} 种用途够用')
    print()
    return checks, verdicts

# 本格自备三个模型（不依赖练习自测格）
_Xc, _Uc, _Yc = collect(2000, 20, 0.3, 1)
_Ah_good, _Bh_good = fit_model(_Xc, _Uc, _Yc)
_Ah_bad = _Ah_good * (1.05 / max(abs(np.linalg.eigvals(_Ah_good)).max(), 1e-9))

_c1, _v1 = evaluate_for_uses(_Ah_good, _Bh_good, '=== 模型 A：正常训练（线性模型 / tanh 真系统）===')
assert _v1['离线视频生成（固定动作序列）'], 'A 应够做离线生成'
assert not _v1['给智能体规划（MPC / Dyna）'], 'A 不该够做规划'

_c2, _v2 = evaluate_for_uses(_Ah_good, np.zeros_like(_Bh_good),
                             '=== 模型 B：动作通道置零 ===')
assert not _v2['可交互视频（用户实时操作）'], 'B 不该够做可交互'
assert sum(_v2.values()) < sum(_v1.values()), 'B 的可用用途应少于 A'

_c3, _v3 = evaluate_for_uses(_Ah_bad, _Bh_good,
                             '=== 模型 C：ρ(Â) = 1.05 ===')
assert not _v3['离线视频生成（固定动作序列）'], 'C 连离线生成都不够（长程会炸）'

print('工程含义：')
print('  · **同一个模型可以「够做视频生成」而「不够做规划」** ——')
print(f'    模型 A 通过了 {sum(_v1.values())}/4 种用途，而它的抗优化相对高估是 '
      f'{_c1["adversarial"][1]}。')
print('  · 模型 B 说明动作通道一坏，① 与 ② 会**一起**坏（练习 4 的实测），')
print('    所以它连离线生成都不够 —— 这与我最初的猜测相反。')
print('  · 模型 C 说明 ρ(Â)>1 是**所有**用途的否决项（模块 03 第 1 节）。')
print('  · 所以「这个世界模型准不准」这个问题没有答案，')
print('    除非先说清它要被怎么用 —— 这是本模块开头那句话的可执行版本。')""" )
,]
