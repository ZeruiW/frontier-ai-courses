# -*- coding: utf-8 -*-
"""C67 模块 05 · 奖励模型与过优化（judge 变成训练信号之后）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 04（BT 与排名）——奖励模型的训练目标就是 BT 的对数似然；"
                 "C02（后训练与对齐）读过更好，但本模块只需要知道「RLHF 用一个奖励模型给策略打分」"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_reward_models.ipynb'
                       '（BT 损失训练一个奖励模型 / KL–奖励过优化曲线与拐点定位 / '
                       'best-of-n 与 RL 两条优化路径的对比 / 分布外退化 / '
                       'RewardBench 风格的切片评测 / 奖励集成与保守化 / 代理指标 vs 真实指标的背离）'),
    ("核心参考", "Gao, Schulman &amp; Hilton, <em>Scaling Laws for Reward Model Overoptimization</em>（ICML 2023）· "
                 "Stiennon et al., <em>Learning to Summarize from Human Feedback</em>（NeurIPS 2020）· "
                 "Lambert et al., <em>RewardBench</em>（2024）· "
                 "Coste et al., <em>Reward Model Ensembles Help Mitigate Overoptimization</em>（ICLR 2024）· "
                 "Rafailov et al., <em>DPO</em>（NeurIPS 2023，隐式奖励模型）· "
                 "本课程 C02（RLHF/DPO/RLVR）· C22（推理 RL 与 PRM）· C23（可扩展监督）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("rm-is-judge", "奖励模型就是一个被固化下来的 judge", "".join([
        P("前四个模块讲的 judge，都是<strong>用来测量</strong>的。这一节开始讲当它<strong>被用来训练</strong>时，"
          "会发生什么本质不同的事。"),
        P("先说一个结构上的连续性：<strong>奖励模型（reward model, RM）的训练目标，"
          "就是模块 04 的 Bradley–Terry 对数似然。</strong>"),
        MATH(r"\mathcal{L}_{\text{RM}} = -\mathbb{E}_{(x,\,y_w,\,y_l)}\left[\log \sigma\big(r_\phi(x, y_w) - r_\phi(x, y_l)\big)\right]"),
        DUAL(
            "对照模块 04 的 BT：那里每个<em>模型</em>有一个标量 $\\theta_i$；"
            "这里每个 <em>(问题, 回答)</em> 对有一个标量 $r_\\phi(x,y)$，由一个神经网络算出来。"
            "<strong>数学形式完全一样，区别只是「强度参数」从一张查找表变成了一个函数。</strong>"
            "所以模块 04 关于 BT 的一切——只有差值有意义、需要正则化、假设了传递性——"
            "<em>全部原样适用于奖励模型</em>。",
            "更精确地说，RM 是 BT 模型的<span class=\"term\">参数化推广</span>："
            "BT 的参数空间是 $\\mathbb{R}^{|M|}$（每个模型一个数），"
            "RM 的参数空间是函数空间 $\\{r_\\phi: \\mathcal{X}\\times\\mathcal{Y}\\to\\mathbb{R}\\}$。"
            "<strong>推广带来的能力是泛化</strong>（能给没见过的回答打分），"
            "<strong>推广带来的风险是外推</strong>——"
            "<em>在训练分布之外，$r_\\phi$ 的值没有任何数据约束，而优化过程恰恰会把策略推到那里去。</em>"
            "这句话就是本模块后面所有内容的种子。",
        ),
        TABLE(["身份", "被谁消费", "关键性质", "本课程哪里讲"], [
            ["<strong>LLM judge</strong>（prompt 驱动）", "评测流程", "可解释、易改、无需训练", "本课 01–04"],
            ["<strong>奖励模型</strong>（训练出来的打分网络）", "<strong>RL / best-of-n</strong>", "快、便宜、可微；<strong>但会被优化压力主动攻击</strong>", "本模块"],
            ["<strong>隐式奖励模型</strong>（DPO 等）", "直接进策略更新", "不显式存在，但数学上等价于一个 RM", "C02 讲训练，本模块讲它的评测"],
            ["<strong>可验证奖励</strong>（RLVR）", "RL", "<strong>不可被 hack</strong>（只要验证器正确）", "第 7 节的边界讨论"],
        ]),
        CALLOUT("intuition", "一个值得记住的判断：<strong>把 judge 用作测量，误差让你得到错误的读数；"
                             "把 judge 用作训练信号，误差会被<em>主动放大</em>——"
                             "因为优化过程会专门去找它出错的地方。</strong>"
                             "这就是为什么「够用的 judge」和「够用的奖励模型」是两个不同的标准。"),
    ])),

    # ============================================================== 2
    ("overopt", "过优化：那条必然出现的倒 U 曲线", "".join([
        P("这是本模块的核心现象，也是 RLHF 工程里最重要的一条经验规律。"),
        ASCII("""
   分数
    │        代理奖励 (RM 分数)
    │      ╱─────────────────────────  单调上升，永远不会告诉你出问题了
    │    ╱
    │  ╱      真实质量 (人类/金标准)
    │ ╱     ╱────╲
    │╱    ╱        ╲______             倒 U：先升后降
    │   ╱                    ╲____
    └──┴────────┴──────────────────────► 优化强度（KL 距离 / best-of-n 的 n / RL 步数）
              拐点
       ← 有效优化 →│← 过优化（RM 分涨、真实质量跌）→

   致命之处：**你只能看到上面那条线。**下面那条需要人类标注才能画出来。
"""),
        P("这条曲线在 best-of-n 和 RL 两种优化方式下都会出现，"
          "但 Gao et al. (2023) 强调<strong>两者的经验形式并不相同</strong>："),
        MATH(r"R_{\text{bon}}(d) \approx d\,(\alpha - \beta d), \qquad "
             r"R_{\text{RL}}(d) \approx d\,(\alpha - \beta \log d), \qquad "
             r"d = \sqrt{\mathrm{KL}(\pi \,\|\, \pi_{\text{ref}})}"),
        P("其中 $R$ 是<strong>真实</strong>质量的提升，$d$ 是 KL 距离的平方根。"
          "$\\alpha$ 是有效优化的斜率，$\\beta$ 是过优化的惩罚项。"
          "<strong>best-of-n 的拐点在 $d^{*} = \\alpha/(2\\beta)$，"
          "RL 的拐点在 $d^{*} = \\exp(\\alpha/\\beta - 1)$——"
          "形式不同，但都有拐点，这才是那篇论文的核心结论。</strong>"
          "<em>关键的经验发现是：$\\alpha$ 和 $\\beta$ 都随奖励模型的规模与数据量变化，"
          "更大的 RM 推得更远、掉得更慢，但拐点<strong>依然存在</strong>。</em>"),
        TABLE(["优化方式", "「优化强度」是什么", "KL 与它的关系", "实践含义"], [
            ["<strong>best-of-n</strong>", "候选数 $n$", "$\\mathrm{KL} \\approx \\log n - \\frac{n-1}{n}$", "便宜、可控、随时能退回去；<strong>调试期的首选</strong>"],
            ["<strong>RL (PPO 等)</strong>", "训练步数 / KL 惩罚系数", "直接被 KL 项控制", "更强但更贵，且<em>退不回去</em>——权重已经变了"],
        ]),
        CALLOUT("danger", "过优化最危险的地方不是它会发生，而是<strong>它在你的监控面板上看起来像成功</strong>。"
                          "代理奖励单调上升，训练曲线漂亮，"
                          "而真实质量的下降<em>只有在人类看到输出时才会被发现</em>——"
                          "通常是在上线之后。"
                          "<strong>所以任何 RLHF 流程都必须有一条独立于 RM 的验证信号</strong>，"
                          "哪怕它很小、很慢、很贵（第 6 节展开）。"),
        H3("为什么必然发生"),
        P("机制在第 1 节的 DUAL 里已经埋好了：<strong>RM 只在训练分布上被约束</strong>。"
          "优化过程的本质就是<em>去找 RM 给高分的地方</em>，"
          "而 RM 给高分最容易的地方，恰恰是它没见过、因此外推得很离谱的区域。"
          "<strong>这是 Goodhart 定律的一个数学上必然的版本，不是实现缺陷。</strong>"),
    ])),

    # ============================================================== 3
    ("hacking-modes", "奖励 hacking 的具体形态：从长度到谄媚", "".join([
        P("抽象地说「过优化」不够用，工程上需要知道<strong>它具体长什么样</strong>。"
          "下面这些形态的共同点是：<em>它们全部对应模块 02 里的某个 judge 偏差</em>——"
          "偏差在测量时是误差，在训练时就是被优化的目标。"),
        TABLE(["形态", "表现", "对应的 judge 偏差（模块 02）", "检测手段"], [
            ["<strong>长度膨胀</strong>", "输出越来越长，信息密度下降", "长度偏差", "监控输出长度分布；长度控制版指标"],
            ["<strong>格式套路化</strong>", "什么问题都用标题 + 编号列表", "风格/格式偏差", "监控 markdown 元素密度"],
            ["<strong>谄媚</strong>（sycophancy）", "顺着用户的错误前提说、不纠正", "标注者偏好「让人舒服」的回答", "构造「用户说了错话」的探针集"],
            ["<strong>自信化</strong>", "含糊表述消失，一律给确定的答案", "自信语气被奖励", "校准检查（模块 03）：ECE 恶化"],
            ["<strong>套话开场</strong>", "「这是一个很好的问题」类的固定前缀", "标注者对礼貌的偏好", "前缀 n-gram 频率监控"],
            ["<strong>拒答漂移</strong>", "该答的也拒答（安全 RM 过强）或该拒的不拒", "安全维度的权重失衡", "拒答率的双向监控"],
        ]),
        CALLOUT("intuition", "这张表最有价值的是第三列。<strong>如果你在模块 02 已经量过 judge 的偏差，"
                             "你就已经知道你的 RM 会往哪个方向被 hack 了。</strong>"
                             "<em>长度偏差 $\\gamma = 0.8$ 的 judge，训出来的 RM 一定会把输出推长</em>——"
                             "这不需要等实验结果，可以事先预测并提前布置监控。"),
        H3("一个反直觉的点：hack 不需要「聪明」"),
        P("这些形态没有一个需要模型「理解」奖励模型的漏洞。"
          "<strong>梯度下降只是在做它该做的事：沿着奖励上升最快的方向走。</strong>"
          "如果「加一句礼貌开场」能稳定地涨 0.1 分，"
          "那么在几万次更新之后，模型必然学会永远加这句开场——"
          "<em>这和「模型在钻空子」这种拟人化描述无关，它就是优化。</em>"),
        P("这个视角有一个实用推论：<strong>与其试图让 RM「更聪明地识破 hack」，"
          "不如从一开始就把可 hack 的维度从奖励里去掉。</strong>"
          "长度控制的 RM（在训练时就把长度回归掉）比事后惩罚长输出有效得多——"
          "<em>这正是模块 02 的去偏方法在训练侧的对应物。</em>"),
    ])),

    # ============================================================== 4
    ("rm-eval", "怎么评测一个奖励模型：切片准确率与它的局限", "".join([
        P("RM 的评测有一个天然的形式：<strong>给一批 (prompt, chosen, rejected) 三元组，"
          "看 RM 是否给 chosen 更高的分。</strong>这就是 RewardBench 类基准的核心。"),
        MATH(r"\text{RM accuracy} = \Pr\big[r_\phi(x, y_w) > r_\phi(x, y_l)\big]"),
        H3("切片是关键"),
        P("总准确率几乎没有信息量。有信息量的是<strong>按能力维度切片</strong>："),
        TABLE(["切片", "考察什么", "典型难点"], [
            ["<strong>Chat</strong>", "一般对话的偏好", "容易饱和——多数 RM 都在 95% 以上"],
            ["<strong>Chat-Hard</strong>", "<strong>刻意构造的困难对</strong>：拒绝对比、细微事实差异、风格诱导", "<strong>最能区分 RM</strong>；许多 RM 在这一片掉到 60% 以下"],
            ["<strong>Safety</strong>", "该拒的拒、不该拒的别拒（双向）", "单向优化会在另一个方向翻车"],
            ["<strong>Reasoning</strong>", "数学/代码的正确性偏好", "RM 常常偏好「看起来严谨」而非「实际正确」"],
        ]),
        CALLOUT("warn", "RM 基准准确率有一个必须知道的局限：<strong>它是在<em>固定的、静态的</em>偏好对上测的，"
                        "而 RM 在实际使用时面对的是<em>被自己的梯度推着走</em>的分布。</strong>"
                        "<em>一个在 RewardBench 上 90% 的 RM，完全可能在 RL 训练的第 2000 步就开始给垃圾输出打高分</em>——"
                        "因为那些输出不在任何静态基准的分布里。"
                        "<strong>静态准确率是必要条件，不是充分条件。</strong>"),
        H3("必须补的两类评测"),
        OL([
            "<strong>分布外探针</strong>：拿被优化过的策略的输出（而不是静态数据集）去测 RM，"
            "看它是否仍然与人类一致。<em>这是唯一能提前发现过优化的离线手段</em>；",
            "<strong>校准</strong>：RM 的分差应当能被翻译成胜率（模块 04 的 BT 性质）。"
            "<strong>分差 1.0 应当对应 73% 的胜率——如果实测只有 55%，说明 RM 的分数尺度是虚的</strong>，"
            "用它做 best-of-n 的截断阈值会完全失准（第 6 节）。",
        ]),
    ])),

    # ============================================================== 5
    ("mitigations", "缓解手段：集成、保守化、迭代", "".join([
        P("过优化不能被消除（第 2 节说过它是数学上必然的），但可以被<strong>推后</strong>和<strong>检测</strong>。"),
        TABLE(["手段", "怎么做", "效果", "代价"], [
            ["<strong>KL 惩罚</strong>", "在目标里加 $-\\beta\\,\\mathrm{KL}(\\pi\\|\\pi_{\\text{ref}})$", "<strong>最基本、必做</strong>：直接限制走多远", "$\\beta$ 是超参；太大则学不动"],
            ["<strong>奖励模型集成</strong>", "训练 $K$ 个 RM（不同 seed / 数据划分），取<strong>最小值</strong>或均值减方差", "<strong>显著推后拐点</strong>：分歧大的区域自动被压低", "训练与推理成本 $\\times K$"],
            ["<strong>保守化 / 悲观估计</strong>", "用 $\\bar{r} - \\lambda\\,\\mathrm{std}(r)$ 代替 $\\bar{r}$", "把「不确定的高分」自动折价", "$\\lambda$ 需要调；过大则过于保守"],
            ["<strong>迭代式数据收集</strong>", "训练一轮 → 用新策略的输出收集新偏好 → 重训 RM", "<strong>最根本的解法</strong>：把分布外变成分布内", "每轮都要人类标注，最贵"],
            ["<strong>早停</strong>", "用独立验证信号定位拐点，停在那里", "简单有效", "需要那条独立信号（第 6 节）"],
            ["<strong>可验证奖励</strong>", "能用程序验证的部分不交给 RM（第 7 节）", "<strong>该部分完全免疫 hack</strong>", "只适用于可验证的任务"],
        ]),
        CALLOUT("intuition", "集成为什么有效，有一个很直观的解释：<strong>过优化找到的是「某一个 RM 的漏洞」，"
                             "而不同 seed 训出来的 RM，漏洞位置不一样。</strong>"
                             "取最小值意味着<em>要骗过所有 RM 才能拿高分</em>，这比骗过一个难得多。"
                             "<strong>但它治不了「所有 RM 共有的偏差」</strong>——"
                             "如果偏好数据本身就奖励长回答，那么每个 RM 都会奖励长回答，集成毫无帮助。"
                             "<em>这与模块 02 第 7 节「集成只能治噪声，治不了共有偏差」是完全同一条结论。</em>"),
        H3("迭代式为什么是根本解法"),
        P("回到第 1 节的病根：<strong>RM 只在训练分布上被约束</strong>。"
          "迭代式数据收集直接解决这个问题——"
          "把优化后策略产生的输出拿去标注，那些原本的「分布外区域」就变成了分布内。"
          "<em>代价是每一轮都需要新的人类标注，所以实践中通常是「几轮迭代 + 每轮内用集成与 KL 惩罚」的组合。</em>"),
    ])),

    # ============================================================== 6
    ("independent-signal", "那条独立信号：过优化的唯一可靠检测方式", "".join([
        P("本模块反复提到「独立于 RM 的验证信号」。这一节把它讲清楚——"
          "<strong>因为它是整个 RLHF 流程里最容易被省掉、也最不该被省掉的一环。</strong>"),
        H3("为什么必须独立"),
        DUAL(
            "如果你用同一个 RM（或它的同门兄弟）来验证训练效果，"
            "那么你测到的只是「优化是否有效地提高了 RM 分数」——"
            "<strong>而这在过优化阶段依然是真的</strong>。"
            "换句话说，非独立的验证信号<em>在你最需要它的时候恰好失效</em>。",
            "形式化：设真实效用 $U$、代理奖励 $\\hat{R}$。"
            "过优化的定义就是 $\\frac{\\partial U}{\\partial d} < 0$ 而 $\\frac{\\partial \\hat{R}}{\\partial d} > 0$。"
            "<strong>任何与 $\\hat{R}$ 高度相关的验证量，在这个区域都会继续上升</strong>，"
            "因此无法检出。"
            "<em>要检出，验证量必须与 $\\hat{R}$ 的<strong>误差项</strong>不相关</em>——"
            "这正是「独立」的技术含义，也是为什么「用一个更强的模型当 judge」经常不够"
            "（它可能共享同样的偏差，呼应模块 03 第 1 节）。",
        ),
        TABLE(["候选信号", "独立性", "成本", "评价"], [
            ["<strong>人类偏好抽样</strong>", "★★★ 最独立", "最高", "<strong>金标准</strong>。哪怕每轮只标 200 条，也比没有强得多"],
            ["<strong>可验证任务的正确率</strong>（数学/代码/单元测试）", "★★★", "低", "<strong>性价比最高</strong>：完全客观，且能自动跑（C66 的判分器）"],
            ["<strong>异族 LLM judge</strong>", "★★☆", "中", "有用，但要先确认它与 RM 的偏差方向不同（模块 02 的探针）"],
            ["<strong>行为分布监控</strong>（长度、格式、拒答率、校准）", "★★★", "极低", "<strong>不测质量，但能测「有没有在被 hack」</strong>——第 3 节的形态清单"],
            ["<strong>留出的 RM</strong>（不参与训练的同门 RM）", "★☆☆", "低", "只能检出「训练 RM 的过拟合」，检不出共有偏差"],
        ]),
        CALLOUT("intuition", "一个便宜且强烈推荐的组合：<strong>「可验证任务正确率」+「行为分布监控」</strong>。"
                             "两者都能全自动跑、成本近乎为零，而且覆盖了过优化的两类表现——"
                             "<em>能力退化</em>（数学题做错了）与<em>形态漂移</em>（输出变长变套路）。"
                             "<strong>人类抽样再补在上面，作为最终的校验。</strong>"),
        H3("拐点怎么定位"),
        P("有了独立信号，定位拐点就是一个曲线拟合问题。实用做法："),
        OL([
            "在若干个优化强度上取检查点（best-of-n 取几个 $n$；RL 取几个 step）；",
            "在每个检查点上跑独立信号，得到 $(d_k, U_k)$；",
            "拟合 $U \\approx d(\\alpha - \\beta d)$，解出 $d^{*} = \\alpha/(2\\beta)$；",
            "<strong>把生产用的 KL 预算设在 $d^{*}$ 之前留有余量的位置</strong>——"
            "因为 $d^{*}$ 本身是有估计误差的，而越过它的代价是不对称的。",
        ]),
    ])),

    # ============================================================== 7
    ("rlvr-boundary", "边界：什么该交给验证器，什么只能交给 judge", "".join([
        P("本课最后一节，回到模块 00 第 2 节埋下的那条线：<strong>校验（verification）与 judge 的分界。</strong>"
          "在训练语境下，这条线就是 RLVR 与 RLHF 的分界。"),
        ASCII("""
   ┌────────────────────────────────────────────────────────────────┐
   │ 可验证奖励 RLVR                    │ 学习到的奖励 RLHF/RM        │
   ├────────────────────────────────────┼─────────────────────────────┤
   │ 数学答案对不对（对答案）            │ 这段解释清不清楚             │
   │ 代码过不过测试                      │ 这个回答有没有帮到人         │
   │ 格式合不合 schema                   │ 语气是否得体                 │
   │ 引用的条款存不存在                  │ 优先级排得对不对             │
   ├────────────────────────────────────┼─────────────────────────────┤
   │ **不可被 hack**（验证器正确的前提下）│ **必然可被 hack**            │
   │ 信号稀疏（只有对错）                │ 信号密集（连续分数）          │
   │ 覆盖窄                              │ 覆盖宽                       │
   └────────────────────────────────────┴─────────────────────────────┘
        实践：**能验证的部分绝不交给 RM**，剩下的才用 RM，并接受它会被 hack。
"""),
        CALLOUT("warn", "一个必须补充的诚实说明：<strong>RLVR 的「不可被 hack」是有条件的</strong>——"
                        "条件是验证器本身正确且完整。"
                        "<em>如果测试写得弱，策略照样能学会「让测试变绿但代码是错的」</em>——"
                        "这正是 C66 模块 02 讲的判分器 hack，只是发生在训练侧。"
                        "<strong>所以「用可验证奖励」不等于「不用操心奖励设计」，"
                        "它只是把问题从「RM 会不会外推错」换成了「验证器写得全不全」。</strong>"
                        "后者通常容易得多，但不是零。"),
        H3("组合的实践形态"),
        P("真实系统里两者几乎总是组合使用，常见形态："),
        UL([
            "<strong>可验证部分做硬约束</strong>：格式不合法、测试不通过直接给 0 或负奖励，"
            "不进入 RM 打分——<em>这一步能挡掉大量最粗糙的 hack</em>；",
            "<strong>RM 只负责剩余维度</strong>，并且这些维度<strong>尽量 rubric 化</strong>"
            "（模块 01）——rubric 项越接近可判定，可 hack 空间越小；",
            "<strong>把已知的 hack 形态写成负向验证器</strong>："
            "「开头是不是套话」「markdown 元素密度是否异常」都可以写成程序检查，"
            "<em>直接扣分，而不是指望 RM 学会不喜欢它们</em>。",
        ]),
        H3("全课收尾"),
        P("把这门课的五个模块串起来看，是同一条逻辑的五次展开："),
        OL([
            "<strong>00</strong> judge 是测量仪器，误差与被测物相关，所以要先验证仪器；",
            "<strong>01</strong> 仪器的设计决定了它的量程与噪声——能写成校验就别打分；",
            "<strong>02</strong> 把系统偏差量出来、减掉，并诚实报告残留的不可识别性；",
            "<strong>03</strong> 用人类上界校准你对「一致率」的解读，用校准度决定分诊；",
            "<strong>04</strong> 把成对比较聚合成排名时，看区间不看名次；",
            "<strong>05</strong> 一旦仪器变成目标，它就开始失效——"
            "<strong>所以永远要有一条独立于它的信号。</strong>",
        ]),
        P("<strong>下一门课 C68</strong> 把这一切工程化：judge 与 RM 的调用怎么缓存、怎么接进 CI、"
          "怎么监控漂移、怎么做线上线下的双回路。"),
    ])),
    # ============================================================== 8
    ("checklist", "上线前的 judge/RM 检查清单", "".join([
        P("把这门课的六个模块压缩成一份可以逐项打勾的清单。"
          "<strong>按用途分三档——用途越重，要求越严。</strong>"),
        H3("档位 A · judge 只用于内部看趋势"),
        UL([
            "☐ swap 一致性 ≥ 0.80，且已做 swap 平均（模块 01/02）",
            "☐ 长度系数 $\\gamma$ 已拟合，raw 与 LC 两个数一起看（模块 02）",
            "☐ judge prompt 有版本指纹，改动会让指纹变（模块 01）",
            "☐ 解析失败率已记录，失败样本按重试→平局处理而非丢弃（模块 01）",
        ]),
        H3("档位 B · judge 用于选型或对外报告"),
        P("在档位 A 之上追加："),
        UL([
            "☐ 与人类的一致率，<strong>且给出人类之间的一致率作为上界</strong>（模块 03）",
            "☐ 风格探针与自偏好探针的幅度已量化（模块 02）",
            "☐ 报告了系统级分辨力：能检出多大的差距（模块 03）",
            "☐ 若出榜单：名次区间、比较图连通性、配对策略、传递性检查（模块 04）",
            "☐ 若出榜单：风格控制版与 Δrank 并列给出（模块 04）",
            "☐ 有哨兵集，且<strong>从未被用来调 prompt</strong>（模块 03）",
        ]),
        H3("档位 C · judge/RM 用作训练信号"),
        P("在档位 B 之上追加——<strong>这一档的要求显著更严，因为误差会被优化过程主动放大</strong>："),
        UL([
            "☐ RM 的<strong>切片评测</strong>已做，且 <strong>worst slice 达标</strong>（不是 macro）（本模块）",
            "☐ RM 的校准已检验：分差 1.0 是否真的对应约 73% 的胜率（本模块）",
            "☐ 已在<strong>被优化过的策略输出</strong>上测过 RM 一致率（分布外探针）（本模块）",
            "☐ <strong>存在一条与 RM 误差不相关的独立信号</strong>，且它是停止规则的依据（本模块）",
            "☐ 行为分布监控已接上：长度、格式密度、拒答率、ECE（本模块）",
            "☐ 已知的 hack 形态写成了负向验证器，而不是指望 RM 学会不喜欢它们（本模块）",
            "☐ 能验证的部分走验证器，不进 RM（本模块）",
        ]),
        CALLOUT("danger", "档位 C 里最不能省的是<strong>倒数第四条（独立信号）</strong>。"
                          "其余每一条缺失都只是让你少一层保护；"
                          "<strong>缺了独立信号，你在过优化开始之后就完全失明了</strong>——"
                          "而那正是你最需要看见的时候。"
                          "<em>哪怕它只是「每轮跑 200 道数学题」这么简陋，也远好过没有。</em>"),
        DUAL(
            "为什么要按用途分档，而不是一律要求做全套？因为<strong>「太贵所以不做」的实际后果是「一项都不做」</strong>。"
            "档位 A 的四项加起来只需要几行代码和零额外调用（长度回归甚至是零成本），"
            "<em>但它们已经能挡掉最常见的两类误读</em>——位置偏差和长度偏差。"
            "先把便宜的做完，再按用途往上加。",
            "从决策理论的角度，检查项的价值等于「它能避免的错误决策的期望损失」。"
            "内部看趋势时，一个偏了的数字造成的损失有限；"
            "而当 judge 被用作训练信号时，<strong>误差不再是一次性的读数错误，"
            "而会通过优化过程被固化进模型权重</strong>——"
            "<em>损失从「这次结论错了」变成「这个模型的行为被永久带偏了」，"
            "而且退不回去（best-of-n 可以退，RL 不能）</em>。"
            "这就是档位 C 的要求显著更严的形式化理由。",
        ),
    ])),
]

NB = [
    md("""# 05 · 奖励模型与过优化（BT 损失训练 RM / KL–奖励曲线 / hack 形态 / 集成 / 切片评测）

目标：把「judge 变成训练信号之后会发生什么」从一句警告，变成**能画出来、能定位拐点的曲线**。

本 notebook 你会亲手实现：
1. **用 BT 损失训练一个奖励模型** —— 与模块 04 的 BT 是同一个损失，只是参数化不同
2. **过优化的倒 U 曲线** —— best-of-n 与 RL 两条路径，代理奖励涨而真实质量跌
3. **拐点定位** —— 拟合 $R(d) = d(\\alpha - \\beta d)$，解出 $d^* = \\alpha/2\\beta$
4. **分布外退化** —— RM 在训练分布内很准，在被优化推到的区域完全失准
5. **奖励集成与保守化** —— 取最小值 / 均值减方差，把拐点推后多少
6. **RewardBench 风格的切片评测** —— 为什么总准确率没有信息量
7. **独立信号** —— 用一个与 RM 误差不相关的验证量，把拐点真的抓出来

> 心智模型：**RM 只在训练分布上被约束，而优化过程恰恰会把策略推到分布之外。
> 过优化不是实现缺陷，是数学上必然的——你只能推后它、检测它，不能消除它。**"""),

    md("""## 1 · 用 BT 损失训练一个奖励模型

为了能在 CPU 上跑通并且**知道真值**，我们用一个线性 RM 和一个可控的"回答空间"：
每个回答由若干个特征描述（其中一部分是真实质量维度，一部分是"表面属性"如长度）。

真实效用只看质量维度；但**偏好数据是由一个带长度偏好的标注者生成的**——
于是 RM 会学到「长 = 好」，这正是模块 02 的长度偏差在训练侧的样子。"""),

    code("""import math, json, itertools
from collections import Counter, defaultdict
import numpy as np

D_QUALITY, D_SURFACE = 4, 2          # 4 个质量维度 + 2 个表面维度（长度/格式）
D = D_QUALITY + D_SURFACE

W_QUALITY = np.array([1.0, 0.8, 0.6, 0.4])       # 质量维度的真实权重
KAPPA = np.array([0.45, 0.30])                   # 表面维度过头之后的惩罚
W_LABELER = np.concatenate([W_QUALITY, [1.0, 0.5]])   # 标注者还偏好长/格式（线性、无上限）

def true_utility(Y):
    # 真实效用有两个现实特征，而代理奖励两个都没有：
    #   ① 质量维度**会饱和**（tanh）——再好也好不到哪去；
    #   ② 表面维度**过头会扣分**（-kappa*x^2）——适度的长度/结构有用，过头则是注水。
    # 代理奖励是线性无上限的，这个失配就是过优化的全部来源。
    Y = np.asarray(Y, dtype=float)
    return np.tanh(Y[:, :D_QUALITY]) @ W_QUALITY - (Y[:, D_QUALITY:] ** 2) @ KAPPA

def labeler_score(Y):
    # 标注者的打分：线性、无饱和、无惩罚——他们在单条比较里看不出「过头」
    return np.asarray(Y, dtype=float) @ W_LABELER

def sample_responses(n, rng, scale=1.0):
    \"\"\"从参考策略采样回答：每个回答是一个 D 维特征向量。\"\"\"
    return rng.normal(0, scale, size=(n, D))

def make_preference_data(n_pairs, rng, noise=0.6):
    \"\"\"标注者按 labeler_score 的 BT 概率给出偏好（带噪声）。\"\"\"
    A = sample_responses(n_pairs, rng)
    B = sample_responses(n_pairs, rng)
    d = (labeler_score(A) - labeler_score(B)) / noise
    win_a = (rng.random(n_pairs) < 1 / (1 + np.exp(-np.clip(d, -30, 30)))).astype(int)
    return A, B, win_a

def train_rm(A, B, win_a, l2=1e-3, lr=0.5, iters=4000):
    \"\"\"线性 RM，BT 损失（与模块 04 的 fit_bt 是同一个损失）。\"\"\"
    A, B = np.asarray(A, float), np.asarray(B, float)
    y = np.asarray(win_a, float)
    w = np.zeros(A.shape[1])
    for _ in range(iters):
        z = (A - B) @ w
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        grad = (A - B).T @ (p - y) / len(y) + l2 * w
        w -= lr * grad
    return w

rng = np.random.default_rng(0)
A_tr, B_tr, y_tr = make_preference_data(20000, rng)
w_rm = train_rm(A_tr, B_tr, y_tr)

print(f"{'维度':<14}{'标注者 W':>12}{'学到的 RM':>12}{'真实效用的形状':>20}")
names = [f'quality_{i}' for i in range(D_QUALITY)] + ['length', 'format']
shapes = [f'{W_QUALITY[i]:.1f}·tanh(x)' for i in range(D_QUALITY)] + \
         [f'-{KAPPA[0]:.2f}x²', f'-{KAPPA[1]:.2f}x²']
for i, nm in enumerate(names):
    print(f'{nm:<14}{W_LABELER[i]:>12.2f}{w_rm[i]:>12.2f}{shapes[i]:>20}')

assert w_rm[D_QUALITY] > 0.5, 'RM 必然学到了标注者的长度偏好'
assert np.corrcoef(w_rm[:D_QUALITY], W_QUALITY)[0, 1] > 0.9
print('\\n✅ RM 学到的质量维度权重与真值排序一致——但它**同时学到了长度偏好**，')
print('   而且是**线性无上限**的：真实效用里长度过头会扣分，RM 里长度永远加分。')
print('   这不是 bug：RM 忠实地拟合了偏好数据，而偏好数据本身就带着标注者的偏差。')
print('   → 模块 02 的 judge 偏差，在训练侧就变成了 RM 权重里的一项。')"""),

    code("""# RM 的静态准确率看起来很好——这正是问题所在
A_te, B_te, y_te = make_preference_data(5000, np.random.default_rng(1))
pred = ((A_te - B_te) @ w_rm > 0).astype(int)
acc_labeler = float((pred == y_te).mean())
true_pref = (true_utility(A_te) > true_utility(B_te)).astype(int)
acc_true = float((pred == true_pref).mean())
print(f'RM 与**标注者**的一致率:  {acc_labeler:.1%}   ← 静态基准测的是这个')
print(f'RM 与**真实效用**的一致率: {acc_true:.1%}   ← 我们真正关心的是这个')
assert acc_labeler > acc_true
print(f'\\n差距 {acc_labeler - acc_true:.1%} —— 这部分完全来自标注者的长度/格式偏好。')
print('✅ 静态基准准确率高，只说明 RM 忠实地复制了标注者（包括他们的偏差）。')"""),

    md("""## 2 · 过优化的倒 U 曲线：best-of-n"""),

    code("""def best_of_n(n, n_prompts, rng, w_score):
    \"\"\"对每个 prompt 采 n 个候选，按 w_score 选最好的一个。
    返回 (被选中回答的代理奖励均值, 真实效用均值, KL 估计)。\"\"\"
    proxy, true_u = [], []
    for _ in range(n_prompts):
        cands = sample_responses(n, rng)
        s = cands @ w_score
        k = int(np.argmax(s))
        proxy.append(float(s[k]))
        true_u.append(float(true_utility(cands[k:k+1])[0]))
    kl = math.log(n) - (n - 1) / n if n > 1 else 0.0
    return float(np.mean(proxy)), float(np.mean(true_u)), kl

rng = np.random.default_rng(7)
NS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
rows = []
for n in NS:
    pr, tu, kl = best_of_n(n, 3000, rng, w_rm)
    rows.append((n, kl, pr, tu))

base_true = rows[0][3]
print(f"{'n':>6}{'KL':>8}{'代理奖励(RM)':>14}{'真实效用':>12}{'相对 n=1 的提升':>16}")
for n, kl, pr, tu in rows:
    print(f'{n:>6}{kl:>8.2f}{pr:>14.3f}{tu:>12.3f}{tu - base_true:>+16.3f}')

proxy_seq = [r[2] for r in rows]
true_seq = [r[3] for r in rows]
assert all(proxy_seq[i] < proxy_seq[i+1] for i in range(len(proxy_seq)-1)), '代理奖励必然单调上升'
peak = int(np.argmax(true_seq))
assert 0 < peak < len(true_seq) - 1, '真实效用必须是倒 U（先升后降）'
print(f'\\n✅ 代理奖励单调上升到底；真实效用在 n={NS[peak]} 达到峰值，之后开始**下降**。')
print(f'   n 从 {NS[peak]} 加到 {NS[-1]}：代理奖励 +{proxy_seq[-1]-proxy_seq[peak]:.2f}，'
      f'真实效用 {true_seq[-1]-true_seq[peak]:+.2f}')
print('   **而在真实项目里，你只能看到上面那条线。**')"""),

    code("""# 被选中的回答，长什么样？——第 3 节 hack 形态的定量版本
def selected_profile(n, n_prompts, rng, w_score):
    feats = []
    for _ in range(n_prompts):
        c = sample_responses(n, rng)
        feats.append(c[int(np.argmax(c @ w_score))])
    return np.mean(feats, axis=0)

print(f"{'n':>6}" + ''.join(f'{nm:>12}' for nm in names))
for n in [1, 8, 64, 512]:
    prof = selected_profile(n, 2000, np.random.default_rng(11), w_rm)
    print(f'{n:>6}' + ''.join(f'{v:>12.3f}' for v in prof))

p1 = selected_profile(1, 2000, np.random.default_rng(11), w_rm)
p512 = selected_profile(512, 2000, np.random.default_rng(11), w_rm)
len_growth = p512[D_QUALITY] - p1[D_QUALITY]
qual_growth = p512[0] - p1[0]
print(f'\\nn 从 1 到 512：length 维度 +{len_growth:.2f}，最重要的质量维度 +{qual_growth:.2f}')
assert len_growth > 0.5
print('✅ 优化压力把「长度」这个维度推得很高——**这就是长度膨胀的机制**。')
print('   模型没有在「钻空子」，它只是在沿着 RM 给的梯度走。')"""),

    md("""## 3 · 拐点定位：拟合 $R(d) = d(\\alpha - \\beta d)$"""),

    code("""def fit_overopt_curve(d_list, gain_list):
    \"\"\"拟合 R(d) = alpha*d - beta*d^2（无截距的二次），返回 (alpha, beta, d_star)。\"\"\"
    d = np.asarray(d_list, dtype=float)
    g = np.asarray(gain_list, dtype=float)
    X = np.column_stack([d, -d ** 2])            # 设计矩阵，无截距
    coef, *_ = np.linalg.lstsq(X, g, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    d_star = alpha / (2 * beta) if beta > 0 else float('inf')
    return alpha, beta, d_star

d_vals = np.array([math.sqrt(r[1]) for r in rows])
gains = np.array([r[3] - base_true for r in rows])
alpha, beta, d_star = fit_overopt_curve(d_vals, gains)
print(f'拟合结果: alpha = {alpha:.3f}, beta = {beta:.3f}')
print(f'拐点 d* = alpha/(2*beta) = {d_star:.3f}  →  KL* = {d_star**2:.3f}')
n_star = math.exp(d_star ** 2 + 1) if d_star < 10 else float('inf')
print(f'对应的 best-of-n 大致在 n ≈ {n_star:.0f}')
assert beta > 0, '必须有正的二次惩罚项，否则不存在拐点'
assert 0 < d_star < d_vals.max(), '拐点应当落在实验范围内'
observed_peak_d = d_vals[int(np.argmax(gains))]
print(f'实测峰值出现在 d = {observed_peak_d:.3f}，拟合拐点 d* = {d_star:.3f}')
assert abs(d_star - observed_peak_d) < 0.8
print('\\n✅ 拟合曲线定位到的拐点与实测峰值一致。')
print('   实践建议：**把生产用的 KL 预算设在 d* 之前留有余量的位置**——')
print('   d* 本身有估计误差，而越过它的代价是不对称的（真实质量下降，且你看不见）。')"""),

    md("""## 4 · 分布外退化：RM 在被推到的区域有多不准"""),

    code("""def rm_agreement_at_optimization_level(n, n_pairs, rng, w_rm):
    \"\"\"在 best-of-n 优化后的分布上，测 RM 与真实效用的一致率。\"\"\"
    agree = 0
    for _ in range(n_pairs):
        # 两个都是被 best-of-n 选出来的回答（即优化后分布）
        c1 = sample_responses(n, rng); a = c1[int(np.argmax(c1 @ w_rm))]
        c2 = sample_responses(n, rng); b = c2[int(np.argmax(c2 @ w_rm))]
        if (a @ w_rm > b @ w_rm) == (true_utility(a[None])[0] > true_utility(b[None])[0]):
            agree += 1
    return agree / n_pairs

print(f"{'优化强度 n':>12}{'RM 与真实效用的一致率':>24}")
for n in [1, 8, 64, 512]:
    a_ = rm_agreement_at_optimization_level(n, 2000, np.random.default_rng(13), w_rm)
    print(f'{n:>12}{a_:>24.1%}')

a1 = rm_agreement_at_optimization_level(1, 2000, np.random.default_rng(13), w_rm)
a512 = rm_agreement_at_optimization_level(512, 2000, np.random.default_rng(13), w_rm)
assert a512 < a1
print(f'\\n✅ 一致率从 {a1:.1%} 掉到 {a512:.1%}——**RM 在它自己推出来的分布上变得更不准了**。')
print('   机制：优化把样本推到「长度维度很高」的区域，而在那个区域，')
print('   RM 的分数几乎全部由长度决定，与真实质量的关联被稀释了。')
print('   → 这就是为什么 RewardBench 类的静态准确率是必要条件而非充分条件。')"""),

    md("""## 5 · 集成与保守化：把拐点推后多少"""),

    code("""def train_rm_ensemble(K, n_pairs, base_seed=100, l2=1e-3):
    \"\"\"K 个 RM，各自用不同的数据划分与初始化（这里用不同 seed 的数据）。\"\"\"
    ws = []
    for k in range(K):
        rg = np.random.default_rng(base_seed + k)
        A, B, y = make_preference_data(n_pairs, rg)
        ws.append(train_rm(A, B, y, l2=l2))
    return np.array(ws)

W_ENS = train_rm_ensemble(5, 8000)
print('集成中各 RM 的 length 权重:', np.round(W_ENS[:, D_QUALITY], 3))
print('→ 方向完全一致（都学到了长度偏好），因为**偏差来自数据而不是随机性**')

def bon_with_scorer(n, n_prompts, rng, score_fn):
    proxy, true_u = [], []
    for _ in range(n_prompts):
        c = sample_responses(n, rng)
        s = score_fn(c)
        k = int(np.argmax(s))
        proxy.append(float(s[k])); true_u.append(float(true_utility(c[k:k+1])[0]))
    return float(np.mean(proxy)), float(np.mean(true_u))

SCORERS = {
    '单个 RM':        lambda c: c @ w_rm,
    '集成均值':       lambda c: (c @ W_ENS.T).mean(axis=1),
    '集成最小值':     lambda c: (c @ W_ENS.T).min(axis=1),
    '保守化 μ-λσ':    lambda c: (c @ W_ENS.T).mean(axis=1) - 1.0 * (c @ W_ENS.T).std(axis=1),
}
print(f"\\n{'策略':<16}" + ''.join(f'{f"n={n}":>10}' for n in [1, 16, 128, 512]))
results = {}
for name, fn in SCORERS.items():
    tus = []
    for n in [1, 16, 128, 512]:
        _, tu = bon_with_scorer(n, 2000, np.random.default_rng(17), fn)
        tus.append(tu)
    results[name] = tus
    print(f'{name:<16}' + ''.join(f'{v:>10.3f}' for v in tus))

single_drop = results['单个 RM'][1] - results['单个 RM'][-1]
cons_drop = results['保守化 μ-λσ'][1] - results['保守化 μ-λσ'][-1]
print(f'\\n从峰值到 n=512 的真实效用跌幅: 单个 RM {single_drop:.3f} | 保守化 {cons_drop:.3f}')
assert cons_drop < single_drop, '保守化应当减缓过优化'
print('✅ 保守化（μ-λσ）确实减缓了跌幅——它把「不确定的高分」自动折价了。')
print('⚠️ 但注意第一行的观察：**所有 RM 的 length 权重方向一致**，')
print('   所以集成治不了长度偏差这类「共有偏差」——它只能治各 RM 独有的那部分误差。')
print('   （与模块 02 第 7 节「集成只能治噪声，治不了共有偏差」是同一条结论。）')"""),

    md("""## 6 · RewardBench 风格的切片评测：总准确率没有信息量"""),

    code("""def make_slice(kind, n, rng):
    \"\"\"造不同难度/类型的偏好对。返回 (A, B, 真实偏好标签)。\"\"\"
    A = sample_responses(n, rng)
    if kind == 'easy':
        B = A - np.column_stack([rng.uniform(0.8, 1.5, n)] + [np.zeros(n)] * (D - 1))
    elif kind == 'hard':
        B = A.copy()
        B[:, 0] -= rng.uniform(0.05, 0.15, n)          # 质量只差一点点
    elif kind == 'style_trap':
        B = A.copy()
        B[:, 0] -= rng.uniform(0.1, 0.3, n)            # B 质量略差
        B[:, D_QUALITY] += rng.uniform(1.0, 2.0, n)    # 但 B 更长 —— 陷阱
    else:
        raise ValueError(kind)
    label = (true_utility(A) > true_utility(B)).astype(int)
    return A, B, label

print(f"{'切片':<14}{'单个 RM':>12}{'集成最小值':>14}{'样本数':>8}")
accs = {}
for kind in ['easy', 'hard', 'style_trap']:
    A_, B_, lab = make_slice(kind, 4000, np.random.default_rng(23))
    a_single = float((((A_ - B_) @ w_rm > 0).astype(int) == lab).mean())
    ens_s = ((A_ @ W_ENS.T).min(axis=1) - (B_ @ W_ENS.T).min(axis=1) > 0).astype(int)
    a_ens = float((ens_s == lab).mean())
    accs[kind] = (a_single, a_ens)
    print(f'{kind:<14}{a_single:>12.1%}{a_ens:>14.1%}{4000:>8}')

overall = np.mean([accs[k][0] for k in accs])
print(f'\\n"总准确率"（三片平均）: {overall:.1%}')
assert accs['easy'][0] > 0.95, 'easy 片必然饱和'
assert accs['style_trap'][0] < 0.5, '风格陷阱片上 RM 应当比瞎猜还差'
print(f'\\n✅ 三个数字讲了完全不同的故事：')
print(f'   easy {accs["easy"][0]:.0%}（饱和，无信息）· '
      f'hard {accs["hard"][0]:.0%} · style_trap {accs["style_trap"][0]:.0%}')
print('   **风格陷阱片上比瞎猜还差**——因为 RM 学到的长度偏好在这里直接指向错误答案。')
print('   而这三片的平均值把这个致命弱点完全掩盖了。→ 切片报告，不报总分。')"""),

    md("""## 7 · 独立信号：把拐点真的抓出来"""),

    code("""def verifiable_signal(n, n_prompts, rng, w_score, q_thresh=0.6, len_budget=1.5):
    \"\"\"一个「可验证任务正确率」的代理，模拟一条真实的自动检查：
    「答案正确（质量维度够高）**且** 输出在长度预算之内」。
    后半条正是 RM 完全没有的约束——所以这个信号与 RM 的误差项不相关。
    这才是「独立」的技术含义，而不是「换一个更强的模型来看」。\"\"\"
    ok = 0
    for _ in range(n_prompts):
        c = sample_responses(n, rng)
        best = c[int(np.argmax(c @ w_score))]
        ok += int(best[0] > q_thresh and abs(best[D_QUALITY]) < len_budget)
    return ok / n_prompts

def correlated_signal(n, n_prompts, rng, w_score):
    \"\"\"一个"不独立"的验证信号：用同门 RM（同样的数据分布训出来）打分。\"\"\"
    w_sibling = W_ENS[0]
    vals = []
    for _ in range(n_prompts):
        c = sample_responses(n, rng)
        best = c[int(np.argmax(c @ w_score))]
        vals.append(float(best @ w_sibling))
    return float(np.mean(vals))

print(f"{'n':>6}{'代理奖励(RM)':>14}{'同门 RM 验证':>14}{'可验证信号':>12}{'真实效用':>12}")
ind_seq, corr_seq = [], []
for n in [1, 8, 32, 128, 512]:
    pr, tu, _ = best_of_n(n, 1500, np.random.default_rng(31), w_rm)
    ind = verifiable_signal(n, 1500, np.random.default_rng(31), w_rm)
    cor = correlated_signal(n, 1500, np.random.default_rng(31), w_rm)
    ind_seq.append(ind); corr_seq.append(cor)
    print(f'{n:>6}{pr:>14.3f}{cor:>14.3f}{ind:>12.1%}{tu:>12.3f}')

assert corr_seq[-1] > corr_seq[0], '同门 RM 的验证信号会一路上升——在过优化区域依然如此'
peak_ind = int(np.argmax(ind_seq))
assert peak_ind < len(ind_seq) - 1, '独立信号必须能看到下降'
print(f'\\n✅ 同门 RM 的验证值一路上升（{corr_seq[0]:.2f} → {corr_seq[-1]:.2f}），')
print('   它在你最需要它的时候恰好失效——因为它与被优化的 RM 共享同样的误差项。')
print(f'   而独立的可验证信号在 n={[1,8,32,128,512][peak_ind]} 见顶后开始下降，成功抓到了拐点。')
print('\\n   → 便宜且强推荐的组合：**可验证任务正确率 + 行为分布监控**，')
print('     两者全自动、成本近乎为零，覆盖「能力退化」与「形态漂移」两类表现。')"""),

    md("""## ✏️ 练习 1：best-of-n 的 KL 与拐点换算

实现 `bon_kl(n)`（$\\log n - \\frac{n-1}{n}$）与
`kl_to_n(kl)`（给定 KL 预算，反解最大可用的 $n$，返回满足 `bon_kl(n) <= kl` 的最大整数 $n \\ge 1$）。"""),

    code("""def bon_kl(n):
    # TODO
    raise NotImplementedError

def kl_to_n(kl, n_max=100000):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert bon_kl(1) == 0.0
assert abs(bon_kl(2) - (math.log(2) - 0.5)) < 1e-12
assert kl_to_n(0.0) == 1
n_ = kl_to_n(2.0)
assert bon_kl(n_) <= 2.0 < bon_kl(n_ + 1)
print(f"{'n':>8}{'KL':>10}    |    {'KL 预算':>10}{'最大 n':>10}")
for n, kl in zip([1, 4, 16, 64, 256], [0.5, 1.0, 2.0, 3.0, 4.0]):
    print(f'{n:>8}{bon_kl(n):>10.3f}    |    {kl:>10.1f}{kl_to_n(kl):>10}')
print(f'\\n本 notebook 拟合出的 KL* = {d_star**2:.2f} → 对应 n ≈ {kl_to_n(d_star**2)}')
print('✅ 练习 1 通过：KL 预算与 best-of-n 的 n 可以互相换算——')
print('   这让「RL 里该设多大的 KL 惩罚」和「best-of-n 该取多少」变成同一个决策。')"""),

    md("""## ✏️ 练习 2：保守化系数 λ 的选择

实现 `sweep_lambda(lams, n, n_prompts=1500, seed=0)`：对每个 λ，
用 `μ - λσ` 作为打分函数跑 best-of-n，返回 `[(λ, 真实效用), ...]`。
用它找出使真实效用最大的 λ。"""),

    code("""def sweep_lambda(lams, n, n_prompts=1500, seed=0):
    # TODO：复用 bon_with_scorer 与 W_ENS
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
LAMS = [0.0, 0.5, 1.0, 2.0, 4.0]
res_l = sweep_lambda(LAMS, n=256, seed=41)
assert len(res_l) == len(LAMS)
best_lam = max(res_l, key=lambda t: t[1])
print(f"{'lambda':>8}{'真实效用':>12}")
for l_, u_ in res_l:
    mark = '  ← 最优' if l_ == best_lam[0] else ''
    print(f'{l_:>8.1f}{u_:>12.3f}{mark}')
assert best_lam[0] > 0.0, 'λ=0（不保守化）不应当是最优'
u0 = dict(res_l)[0.0]
assert best_lam[1] > u0
print(f'\\n最优 λ = {best_lam[0]}，相对 λ=0 提升真实效用 {best_lam[1]-u0:+.3f}')
print('✅ 练习 2 通过：λ 太小起不到保守化作用，太大则把有效信号也压掉了——')
print('   这条曲线要用**独立信号**扫，不能用 RM 自己扫（那样 λ=0 永远最优）。')"""),

    md("""## ✏️ 练习 3：hack 形态的自动检测

实现 `hack_monitor(profile_base, profile_now, names, thresh=0.5)`：
比较优化前后被选中回答的平均特征，返回所有漂移超过 `thresh` 的维度
`[(维度名, 漂移量), ...]`，按漂移量降序。"""),

    code("""def hack_monitor(profile_base, profile_now, names, thresh=0.5):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
alerts = hack_monitor(p1, p512, names, thresh=0.5)
print('优化前后的特征漂移告警:')
for nm, delta in alerts:
    print(f'  {nm:<12} {delta:+.3f}')
assert any(nm == 'length' for nm, _ in alerts), 'length 维度必须被告警'
assert alerts == sorted(alerts, key=lambda t: -abs(t[1])), '必须按漂移量降序'
assert hack_monitor(p1, p1, names) == [], '没有漂移时不应告警'
print('\\n✅ 练习 3 通过：这就是「行为分布监控」的最小实现——')
print('   它不测质量，但能告诉你「模型正在往哪个方向被 hack」，而且成本近乎为零。')"""),

    md("""## ✏️ 练习 4：切片评测卡

实现 `rm_eval_card(w, slices, n=3000, seed=0)`：对每个切片算准确率，
返回 `{'per_slice': {切片: 准确率}, 'macro': 宏平均, 'worst_slice': (名字, 准确率)}`。
**`worst_slice` 才是决定 RM 能不能用的那个数。**"""),

    code("""def rm_eval_card(w, slices, n=3000, seed=0):
    # TODO：用 make_slice 造数据
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
card = rm_eval_card(w_rm, ['easy', 'hard', 'style_trap'], seed=53)
assert set(card) == {'per_slice', 'macro', 'worst_slice'}
assert card['worst_slice'][0] == 'style_trap'
assert card['worst_slice'][1] < card['macro']
for k, v in card['per_slice'].items():
    print(f'  {k:<14} {v:.1%}')
print(f"  {'macro':<14} {card['macro']:.1%}")
print(f"  {'worst':<14} {card['worst_slice'][0]} @ {card['worst_slice'][1]:.1%}")
card_ens = rm_eval_card(W_ENS.min(axis=0), ['easy', 'hard', 'style_trap'], seed=53)
print(f"\\n集成最小值的 worst slice: {card_ens['worst_slice'][1]:.1%}")
print('✅ 练习 4 通过：**报 worst_slice，不报 macro**——')
print('   一个在风格陷阱片上低于 50% 的 RM，无论总分多高都不该被用作训练信号。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def bon_kl(n):
    n = int(n)
    return 0.0 if n <= 1 else math.log(n) - (n - 1) / n

def kl_to_n(kl, n_max=100000):
    best = 1
    for n in range(1, n_max + 1):
        if bon_kl(n) <= kl:
            best = n
        else:
            break
    return best"""),

    code("""# 练习 2 参考答案
def sweep_lambda(lams, n, n_prompts=1500, seed=0):
    out = []
    for lam in lams:
        fn = (lambda c, L=lam: (c @ W_ENS.T).mean(axis=1) - L * (c @ W_ENS.T).std(axis=1))
        _, tu = bon_with_scorer(n, n_prompts, np.random.default_rng(seed), fn)
        out.append((lam, tu))
    return out"""),

    code("""# 练习 3 参考答案
def hack_monitor(profile_base, profile_now, names, thresh=0.5):
    base = np.asarray(profile_base, dtype=float)
    now = np.asarray(profile_now, dtype=float)
    alerts = [(names[i], float(now[i] - base[i])) for i in range(len(names))
              if abs(now[i] - base[i]) > thresh]
    return sorted(alerts, key=lambda t: -abs(t[1]))"""),

    code("""# 练习 4 参考答案
def rm_eval_card(w, slices, n=3000, seed=0):
    per = {}
    for i, kind in enumerate(slices):
        A_, B_, lab = make_slice(kind, n, np.random.default_rng(seed + i))
        per[kind] = float((((A_ - B_) @ np.asarray(w) > 0).astype(int) == lab).mean())
    worst = min(per.items(), key=lambda t: t[1])
    return {'per_slice': per,
            'macro': float(np.mean(list(per.values()))),
            'worst_slice': worst}"""),

    md("""---
## 🧪 真实工程胶囊：RLHF 流程里必须接上的四条线"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 训练 RM 的最小骨架（BT 损失 —— 与模块 04 是同一个损失）
# ══════════════════════════════════════════════════════════════════
import torch, torch.nn.functional as F
def rm_loss(model, batch):
    r_chosen  = model(batch["prompt"], batch["chosen"]).squeeze(-1)
    r_rejected = model(batch["prompt"], batch["rejected"]).squeeze(-1)
    return -F.logsigmoid(r_chosen - r_rejected).mean()
# 常见附加项：
#   + 0.01 * (r_chosen**2 + r_rejected**2).mean()   # 防止分数尺度漂移
#   + margin loss（当偏好标注带强度时）

# ══════════════════════════════════════════════════════════════════
# B. 训练时必须并行跑的四条监控线（缺一条你就是在盲飞）
# ══════════════════════════════════════════════════════════════════
MONITORS = {
  # 1. 代理奖励 —— 你唯一"免费"的信号，但它在过优化时依然上升
  "proxy_reward":    lambda ckpt: eval_rm_score(ckpt),
  # 2. 可验证任务正确率 —— 独立、自动、便宜。**最重要的一条**
  "verifiable_acc":  lambda ckpt: run_math_and_code_tests(ckpt),
  # 3. 行为分布 —— 不测质量，但能看出在往哪个方向被 hack
  "behavior":        lambda ckpt: {
      "mean_output_tokens": ...,      # 长度膨胀
      "md_elements_per_1k": ...,      # 格式套路化
      "refusal_rate":       ...,      # 拒答漂移（双向）
      "hedge_word_rate":    ...,      # 自信化（含糊表述消失）
      "ece":                ...,      # 校准恶化（模块 03）
  },
  # 4. 人类抽样 —— 金标准。每轮 200 条也远好过没有
  "human_sample":    lambda ckpt: collect_human_prefs(ckpt, n=200),
}
# 停止规则：verifiable_acc 连续两个检查点下降 → 停，回退到上一个检查点。
# **不要**用 proxy_reward 做停止规则——它在过优化区域依然上升。

# ══════════════════════════════════════════════════════════════════
# C. 硬约束：能验证的绝不交给 RM（第 7 节）
# ══════════════════════════════════════════════════════════════════
def total_reward(prompt, response):
    # 1) 可验证的硬门禁：不合格直接负奖励，不进 RM
    if not schema_valid(response):          return -1.0
    if not tests_pass(prompt, response):    return -1.0
    # 2) 已知 hack 形态的负向验证器（比指望 RM 学会不喜欢它们有效得多）
    penalty = 0.0
    penalty += 0.2 * has_boilerplate_opening(response)
    penalty += 0.2 * (md_element_density(response) > MD_DENSITY_P95)
    # 3) 剩余维度才交给 RM，并做保守化
    scores = np.array([rm(prompt, response) for rm in RM_ENSEMBLE])
    return scores.mean() - LAMBDA * scores.std() - penalty

# ══════════════════════════════════════════════════════════════════
# D. RM 的评测卡（发布 RM 时必须附带）
# ══════════════════════════════════════════════════════════════════
# per-slice accuracy: chat / chat-hard / safety(双向) / reasoning / style-trap
# worst slice        ← **决定能不能用的就是这个数**
# 校准: 分差 1.0 实测对应多少胜率（BT 性质要求 73%）
# 分布外探针: 在被优化过的策略输出上的一致率
# 集成信息: K、各 RM 在关键维度上的权重方向是否一致
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| RM = 参数化的 BT | 训练目标就是模块 04 的 BT 损失，只是查找表变成了函数 | 理解 RM |
| 过优化必然发生 | RM 只在训练分布上被约束，而优化会把策略推到分布外 | 预期管理 |
| 拐点 $d^*=\\alpha/2\\beta$ | 拟合独立信号的曲线定位，KL 预算留余量 | 设 KL 惩罚 / 选 n |
| hack 形态 | 每一种都对应模块 02 的一个 judge 偏差——可以事先预测 | 布置监控 |
| 集成的边界 | 治各 RM 独有的误差，治不了偏好数据里的共有偏差 | 选缓解手段 |
| 切片评测 | 报 worst slice，不报 macro；静态准确率是必要不充分条件 | 发布 RM |
| 独立信号 | 与 RM 误差不相关才叫独立；可验证任务 + 行为监控最划算 | RLHF 流程必备 |

**全课收尾**：00 仪器 → 01 设计 → 02 去偏 → 03 元评测 → 04 排名 → 05 训练信号。
一条逻辑贯穿始终：**先验证测量仪器，再相信读数；而一旦仪器变成目标，它就开始失效。**

**下一门课 C68 · Eval 基础设施与线上监控**：把这一切工程化——
judge 与 RM 的调用怎么缓存、怎么接进 CI 门禁、怎么监控漂移、怎么做线上线下双回路。""")
]
