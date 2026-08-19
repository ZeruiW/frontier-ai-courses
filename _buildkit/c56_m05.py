# -*- coding: utf-8 -*-
"""C56 模块 05 · 增强的消融与验证：怎么证明它真的有用。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–04（几何 / 光度 / 混合 / 流水线）；C61 模块 01（实验方法论）与 C55 模块 05（安全导向评测）是本模块的两个邻居"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_aug_ablation.ipynb'),
    ("核心参考", "Bouthillier et al. 的方差研究、Dodge et al. 的报告规范、Bootstrap 方法、YOLO 系的增强消融表"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("masking", "整体 mAP 会掩盖什么：+0.3 背后可能是「雨天 +3、晴天 −1」", "".join([
        P("前四个模块教你怎么做增强。这一模块回答一个更难也更重要的问题：<strong>你怎么知道它真的有用？</strong>答案不是「跑一遍看 mAP 涨没涨」——那是这个领域里最常见、也最昂贵的错误。"),
        P("先看一组具体数字。某个新增强上线前的分场景评测："),
        TABLE(["场景", "里程占比", "baseline AP", "加增强后 AP", "变化"], [
            ["晴天白天", "60%", "0.7200", "0.7050", "<strong style=\"color:#c33\">−1.50 pt</strong>"],
            ["夜间", "20%", "0.4800", "0.5100", "+3.00 pt"],
            ["雨天", "15%", "0.4100", "0.4400", "+3.00 pt"],
            ["隧道", "5%", "0.3900", "0.4200", "+3.00 pt"],
            ["<strong>里程加权整体</strong>", "100%", "<strong>0.6090</strong>", "<strong>0.6120</strong>", "<strong>+0.30 pt</strong>"],
        ]),
        P("<strong>只看最后一行，你会说「涨了 0.3，微弱正收益，上吧」。</strong>而真相是：这个增强在占 60% 里程的主力场景上掉了 1.5 个点，只是被三个小场景的 +3 抬了回来。<em>这两个结论会导向完全不同的决策</em>。"),
        DUAL(
            "整体 mAP 是一个<strong>加权平均</strong>，而平均的天职就是抹掉分布信息。检测任务的评测集通常由多个异质子群组成（天气、光照、距离、类别、遮挡度），<em>它们的样本量和难度都差好几倍</em>。当你在这样的集合上算一个标量，<strong>任何「一部分涨、一部分掉」的模式都会被压成一个数</strong>，而增强恰恰是最容易产生这种模式的干预——它按定义就是在改变数据分布，<em>而分布的改变很难对所有子群同向</em>。",
            "更精确地说，问题在于<strong>评测集的权重不等于业务的权重</strong>。上表用的是里程占比；但如果按<em>安全风险</em>加权（夜间和雨天的事故率是晴天的 2–3 倍），同一份实验数据算出来是 <strong>+1.26 pt</strong>——是里程加权结果的 4 倍多。<em>同一个实验，两套权重，结论差 4 倍</em>。<strong>所以「增强有没有用」这个问题在没有定义权重之前是不完整的</strong>，而权重必须来自业务而不是来自评测集的天然构成（评测集的构成往往只反映了「哪些数据好收集」）。",
        ),
        CALLOUT("danger", "<p>这个坑在 TSR 上尤其致命，因为<strong>误检与漏检的代价高度不对称且随场景变化</strong>。晴天白天掉 1.5 个点意味着在最常见的路况下多漏了标志——<em>如果漏的是「停车让行」，后果是安全事件；如果漏的是「景点指示」，后果是零</em>。而整体 mAP 对这两者一视同仁。<strong>规则：任何增强的验收都必须同时给出「分场景切片表」与「关键类别表」，只报整体 mAP 的实验报告应当被直接打回。</strong></p>", "面试高频：你怎么验收一个增强/一个改动"),
        CALLOUT("intuition", "把这一节压成一条可执行的规矩：<strong>先定义切片，再跑实验</strong>。切片的定义（哪些维度、每个维度怎么分桶、每桶的最小样本量）应当在实验开始<em>之前</em>写死并进版本库。<em>事后才去切片，你会不自觉地挑那些让结论好看的切法</em>——这是一种极难自我察觉的 p-hacking。"),
    ])),
    ("variance", "种子方差：多少提升才不是噪声", "".join([
        P("第二个问题比第一个更基础：<strong>你观测到的那个差值，有多少是真实效应，有多少是随机噪声？</strong>深度学习的训练是随机过程——初始化、数据顺序、增强采样、cuDNN 的非确定算法，每一样都会让同一份配置跑出不同结果。"),
        P("检测任务上，<strong>单次训练的 mAP 种子标准差典型在 0.3–0.6 个点</strong>（数据量越小、训练越短、类别越长尾，方差越大）。取 σ = 0.5 pt 做一笔账："),
        MATH("\\Delta_{\\text{obs}} = \\mu + (\\varepsilon_A - \\varepsilon_B), \\qquad \\varepsilon \\sim \\mathcal{N}(0, \\sigma^2) \\ \\Longrightarrow\\ \\mathrm{sd}(\\Delta_{\\text{obs}}) = \\sqrt{2}\\,\\sigma \\approx 0.71\\ \\text{pt}"),
        TABLE(["问题", "计算", "答案", "含义"], [
            ["零效应下，观测到 |Δ| &gt; 0.3 的概率", "2(1−Φ(0.3/0.71))", "<strong>67.1%</strong>", "<strong>「+0.3」这个数字几乎不含信息</strong>"],
            ["真实效应 +0.4，单种子比较得出<em>反</em>号的概率", "Φ(−0.4/0.71)", "<strong>28.6%</strong>", "三分之一的概率你会把好改动毙掉"],
            ["跑 3 个种子只报最好的，凭空得到多少", "E[max of 3]·σ", "+0.42 pt", "「挑种子」的作弊幅度"],
            ["跑 10 个种子只报最好的", "E[max of 10]·σ", "<strong>+0.77 pt</strong>", "比绝大多数真实增强的效应还大"],
        ]),
        DUAL(
            "第一行是这一节的核心事实：<strong>在 σ=0.5 的噪声下，两次纯粹相同的训练有 67% 的概率给出 |Δ| &gt; 0.3 的差值</strong>。所以当一篇论文、一个同事、或者你自己说「这个增强带来 +0.3 mAP」，<em>而只跑了一个种子</em>，那句话在统计上等价于「我掷了一次骰子」。<strong>面试里被问「+0.3 算提升吗」，正确答案是先反问「跑了几个种子、种子方差多大」</strong>，而不是直接判断大小。",
            "第三、四行揭示了一个更隐蔽的问题：<strong>「挑最好的种子」在方法上等价于把噪声的最大值当成信号</strong>。它甚至不需要你有意作弊——<em>「这次跑崩了，重跑一遍」本身就是一种选择性报告</em>，因为你只会对结果差的实验说「跑崩了」。<strong>防线是把种子数与报告方式在实验开始前固定下来</strong>：跑 N 个种子，报均值 ± 标准差，N 由功效分析决定而不是由结果决定。<em>「跑到显著为止」和「跑到不显著就停」是同一种错误的两个方向。</em>",
        ),
        CALLOUT("warn", "种子方差还有一个被普遍忽视的来源：<strong>评测本身的方差</strong>。如果验证流水线里残留任何随机性（模块 04 讲过），同一个 checkpoint 评两次就会给出不同的 mAP，<em>这部分方差会叠加到训练方差上，而且无法通过多种子平均消除</em>。所以做显著性分析之前，第一件事是断言「同权重评两次逐位相同」。"),
    ])),
    ("paired", "配对设计：让方差自己抵消掉", "".join([
        P("上一节的数字让人绝望：σ=0.5 意味着要检出 +0.3 需要几十次训练。<strong>但那是「非配对」设计的代价。换成配对设计，同样的检出能力只需要几个种子。</strong>"),
        P("关键的观察是：<strong>训练结果的方差可以分解成「种子效应」与「残差」两部分</strong>。同一个种子下，初始化、数据顺序、shuffle 序列都是相同的——这部分波动对 baseline 和 treatment <em>是共同的</em>，做差就抵消了。"),
        MATH("y_{s,a} = \\mu_a + \\underbrace{b_s}_{\\text{种子效应}} + \\underbrace{\\epsilon_{s,a}}_{\\text{残差}}, \\qquad d_s = y_{s,A} - y_{s,B} = (\\mu_A - \\mu_B) + (\\epsilon_{s,A} - \\epsilon_{s,B})"),
        TABLE(["设计", "差值的标准差", "数值（b=0.45, ε=0.15）", "检出 +0.4 需要的种子数"], [
            ["<strong>非配对</strong>（各自随机种子）", "√(2(σ_b²+σ_ε²))", "<strong>0.67 pt</strong>", "<strong>每组 ~25 个</strong>"],
            ["<strong>配对</strong>（共用同一批种子）", "√(2σ_ε²)", "<strong>0.21 pt</strong>", "<strong>3 个</strong>"],
        ]),
        DUAL(
            "配对设计的做法极其朴素：<strong>用同一组种子 <code>[0,1,2,3,4]</code> 分别跑 baseline 和 treatment，逐种子做差，然后对这 5 个差值做统计</strong>。它把「同一个初始化下这个改动带来了什么」这个问题隔离了出来，<em>而不是问「这个改动的平均效果 vs 那个改动的平均效果」</em>。在上面的数字下，标准差从 0.67 降到 0.21——<strong>方差降了 10 倍，需要的算力降了 8 倍</strong>。这是这个模块里性价比最高的一条建议。",
            "配对要成立有两个前提，都必须显式检查：① <strong>种子必须真的控制住了所有共享随机性</strong>——包括 DataLoader 的 shuffle 序列、增强的 RNG（模块 04）、以及权重初始化；如果 treatment 改变了增强算子的数量，RNG 消耗的次数就变了，<em>后续的随机序列会错开，配对效果部分失效</em>。② <strong>两个 arm 的其他一切必须完全相同</strong>：同 epoch 数、同 LR schedule、同 close-mosaic 时点、同评测代码。<em>只要有一项不同，你测的就不是那个增强。</em>",
        ),
        H3("配对 t 检验与 bootstrap：两个都要看"),
        P("拿到 n 个配对差值 <code>d₁…dₙ</code> 之后，有两件事要做："),
        OL([
            "<strong>配对 t 检验</strong>：<code>t = d̄ / (s_d/√n)</code>，与自由度 <code>n−1</code> 的临界值比较。<em>它假设差值近似正态——小样本下这个假设未必成立，所以不能只看它。</em>",
            "<strong>Bootstrap 置信区间</strong>：对差值有放回重采样 B 次，取均值分布的 2.5%/97.5% 分位数。<em>不依赖分布假设</em>，而且它给出的是<strong>效应量的区间</strong>而不是一个 yes/no。",
            "<strong>工程容差判定</strong>：区间下界是否超过你愿意为之付出代价的阈值。<em>统计显著 ≠ 值得做</em>——一个统计上确凿的 +0.05 pt，若代价是 3 倍的数据管线复杂度，答案仍然是不做。",
        ]),
        CALLOUT("intuition", "这三步的顺序很重要，它对应三个不同的问题：<strong>「有没有效应」（t 检验）→「效应有多大、多确定」（bootstrap 区间）→「这么大的效应值不值得」（工程容差）</strong>。<em>绝大多数实验报告只做了第一步，而第三步才是真正的决策依据</em>。面试里能把这三步分清楚，是资深度的直接信号。"),
    ])),
    ("power", "功效分析：动手之前先算需要多少种子", "".join([
        P("配对设计之后还剩一个问题：<strong>到底要跑几个种子？</strong>这个问题必须在实验开始<em>之前</em>回答，否则你会陷入「跑到显著为止」的陷阱。"),
        MATH("n \\ \\geq\\ \\frac{(z_{1-\\alpha/2} + z_{1-\\beta})^2 \\, \\sigma_d^2}{\\Delta^2}, \\qquad \\text{MDE}(n) = (z_{1-\\alpha/2} + z_{1-\\beta}) \\cdot \\frac{\\sigma_d}{\\sqrt{n}}"),
        P("其中 <code>Δ</code> 是你希望检出的最小效应，<code>σ_d</code> 是配对差值的标准差。取 α=0.05、power=0.80，则 <code>(1.96+0.84)² = 7.85</code>。"),
        TABLE(["设计", "σ_d", "想检出 +0.4", "想检出 +0.2", "想检出 +0.1"], [
            ["<strong>配对</strong>", "0.21 pt", "<strong>3 个种子</strong>", "9 个种子", "<strong>35 个种子</strong>"],
            ["<strong>非配对</strong>", "0.67 pt", "25 个种子", "88 个种子", "<strong>353 个种子</strong>"],
        ]),
        DUAL(
            "把这张表反过来读更有用——<strong>用 MDE（最小可检出效应）代替 n</strong>：「我只能跑 5 个配对种子，那我能检出多小的提升？」答案是 <code>2.80 × 0.21/√5 = 0.26 pt</code>。<em>这意味着任何小于 0.26 pt 的观测差值，无论正负，都不该被当成结论</em>。<strong>MDE 应该写在实验报告的最上面</strong>，它一句话就界定了这次实验能说什么、不能说什么。",
            "最后一列是残酷的现实：<strong>要可靠地检出 +0.1 pt，配对设计要 35 次训练，非配对要 353 次</strong>。对一次要跑 12 小时的检测训练，后者是 176 天。<em>结论不是「想办法跑 353 次」，而是「+0.1 这个量级的改动在当前方差水平下不可验证，所以不要基于它做决策」</em>。<strong>正确的应对有三条</strong>：① 降低 σ_d（配对、固定评测、更长训练）；② 提高 Δ（做更有力的改动，而不是堆小 trick）；③ 换一个方差更小的指标（分场景 AP 往往比整体 mAP 的信噪比更高，因为效应更集中）。",
        ),
        CALLOUT("danger", "<p><strong>多重比较</strong>是这一节的隐藏杀手。你一次消融 10 个增强算子，每个都做 α=0.05 的检验，<em>那么「至少一个假阳性」的概率是 1−0.95¹⁰ = 40%</em>。如果还按 8 个场景切片各看一遍，就是 80 次检验——<strong>纯噪声也会给你四个「显著」的发现</strong>。规则：<strong>要么预先声明一个主指标（primary endpoint）、其余全部标为探索性；要么做 Bonferroni / FDR 校正</strong>。<em>「我在 8 个切片里发现雨天显著提升」这句话，若切片是事后挑的，几乎没有证据价值。</em></p>", "面试高频：怎么避免自欺"),
    ])),
    ("overaug", "增强过强的症状学", "".join([
        P("增强不是越多越好。<strong>过强的增强会让训练分布偏离真实分布，模型把容量花在拟合不存在的变化上</strong>。问题是它的症状容易被误读成别的东西。"),
        TABLE(["症状", "观察到什么", "为什么", "是不是病"], [
            ["<strong>验证指标高于训练指标</strong>", "val mAP &gt; train mAP", "训练集带增强（更难），验证集不带", "<strong>不是病</strong>——强增强下这是正常现象，误诊率极高"],
            ["<strong>训练 loss 居高不下</strong>", "loss 平台期比预期高", "同上，任务变难了", "不是病（单独看）"],
            ["<strong>验证指标低于无增强 baseline</strong>", "val AP 掉了", "<strong>分布偏移超过了正则化收益</strong>", "<strong>是病</strong>——这才是判据"],
            ["<strong>收敛显著变慢</strong>", "到达同一 val AP 需要 2–3 倍 epoch", "有效任务难度上升", "视预算而定（见下一节）"],
            ["<strong>小模型掉点、大模型涨点</strong>", "同一配置在 tiny 上 −1.6、在 large 上 +1.7", "<strong>容量-强度错配</strong>：小模型欠拟合", "<strong>是病</strong>——按模型规模分档配增强"],
            ["<strong>某个切片崩塌</strong>", "整体持平但某场景掉 5+", "该增强破坏了这个场景的关键线索", "<strong>是病</strong>——第 1 节的切片表能抓到"],
        ]),
        DUAL(
            "第一行值得展开，因为它是<strong>最常被误诊的一条</strong>。「验证优于训练」在没有增强的年代确实是数据泄漏的指纹，但在强增强的检测训练里它是<em>预期行为</em>——训练时模型看到的是被 Mosaic 拼过、被透视扭过、被压暗加噪的图，验证时看到的是干净的原图，<strong>后者当然更容易</strong>。<em>把它当成 bug 去查，会浪费大量时间</em>。真正的判据永远是<strong>「验证指标 vs 无增强 baseline」</strong>，而不是「验证 vs 训练」。",
            "第五行「容量-强度错配」是实践中最有用的一条。增强的作用机制是<strong>用「更难的任务」换「更好的泛化」</strong>——这笔交易只有在模型有余量的时候才划算。<em>小模型的容量本来就不够拟合原始任务，再把任务变难，它连原始分布都学不好了</em>。所以 <strong>YOLO 系为 n/s/m/l/x 各档配了不同强度的增强</strong>（小模型关掉 MixUp、降低 Mosaic 比例、缩小尺度抖动范围），这不是调参玄学而是这条原理的直接推论。<em>把大模型的增强配置照搬到 tiny 模型上，是很常见也很昂贵的错误。</em>",
        ),
        ASCII("""增强过强的诊断树（从症状走到处方，不要在第一步就停）

  观察到：val 指标不如预期
        │
        ├─ val > train ？ ──────► 是 ──► **不是病**：训练集带增强本来就更难。
        │                              继续往下走，别在这里停下来查数据泄漏。
        │
        └─► 唯一判据：val vs **无增强 baseline**
              │
              ├─ val ≥ baseline ──► 增强有效。再看分场景切片是否有局部崩塌。
              │
              └─ val < baseline ──► 增强过强，分三种成因：
                    │
                    ├─ 小模型掉/大模型涨 ──► **容量-强度错配**
                    │      处方：按模型档位分配强度（tiny 关 MixUp、降 Mosaic 比例）
                    │
                    ├─ 曲线末段仍在上升 ──► **预算不足**，不是增强的锅
                    │      处方：延长训练，或按比例缩放强度后重比（第 6 节）
                    │
                    └─ 某个切片单独崩塌 ──► **该增强破坏了这个场景的关键线索**
                           处方：查混淆矩阵。TSR 里最常见的是色相抖动
                           导致「禁令牌→指示牌」这类跨颜色族错分 ——
                           整体 mAP 只掉 0.2，安全上却是灾难。"""),
        CALLOUT("warn", "还有一个 TSR 特有的过强症状：<strong>色相抖动破坏语义</strong>（模块 02 量化过）。它的表现不是整体掉点，而是<em>混淆矩阵里出现「禁令牌被判成指示牌」这类跨颜色族的错分</em>——整体 mAP 可能只掉 0.2，但这类错分在安全上是灾难。<strong>所以 TSR 的增强验收表里必须有一列「跨颜色族错分率」</strong>，它比 mAP 敏感得多。"),
    ])),
    ("budget", "增强强度与训练时长的交互：短训练下的比较是不公平的", "".join([
        P("这是消融设计里最容易犯、后果最严重的一个错误：<strong>用短训练预算去比较不同强度的增强</strong>。"),
        P("原理很直接：<strong>增强提高了有效任务难度，因此收敛更慢</strong>。在训练还没收敛的时候比较，你测到的主要是「谁收敛得快」，而不是「谁的终点更高」。下面是一个能算出来的例子（模型容量固定，只变增强强度与 epoch 数）："),
        TABLE(["训练预算", "aug=0.0", "aug=0.3", "aug=0.6", "aug=1.0", "最优强度"], [
            ["12 epoch", "<strong>0.545</strong>", "0.494", "0.431", "0.329", "<strong>0.0</strong>"],
            ["36 epoch", "0.759", "<strong>0.770</strong>", "0.728", "0.627", "<strong>0.3</strong>"],
            ["100 epoch", "0.780", "0.834", "<strong>0.842</strong>", "0.797", "<strong>0.6</strong>"],
            ["300 epoch", "0.780", "0.835", "<strong>0.846</strong>", "0.811", "<strong>0.6</strong>"],
        ]),
        P("看第三列与第一列的对比：<strong>在 12 epoch 的预算下，aug=0.6 比 aug=0.0 低 11.4 个点；在 300 epoch 下，同样的比较是高 6.6 个点。同一个实验，符号相反。</strong>"),
        DUAL(
            "这解释了一个常见的组织性失败：<strong>团队为了「快速迭代」把消融的训练预算砍到 1/10，然后系统性地淘汰掉所有强增强的方案</strong>。<em>短预算下的排序与全预算下的排序不一致，而且不是随机不一致——它有明确的方向：短预算永远偏袒弱增强</em>。于是这个团队会一路收敛到一个「训练很快、天花板很低」的配置，并且永远不知道自己错过了什么。",
            "正确的做法有三种，成本递增：① <strong>用足够长的预算做消融</strong>（最可靠，最贵）；② <strong>在缩短预算的同时按比例缩放增强强度</strong>（把「强度 × 时长」当成一个联合超参，而不是独立变量）；③ <strong>看曲线而不是看终点</strong>——如果强增强的验证曲线在预算末尾仍在明显上升而弱增强已经平了，<em>这本身就是「预算不够、排序不可信」的证据</em>。<strong>第 ③ 条几乎不花额外成本，应当成为默认动作。</strong>",
        ),
        CALLOUT("danger", "<p>同一个逻辑还有一个变体：<strong>「同 budget」必须包含调参预算</strong>。你为 baseline 调了三个月的学习率与 schedule，然后把新增强直接插进去用同一套超参跑一次——<em>新方案没有得到同等的调参机会</em>。强增强通常需要更大的学习率或更长的 warmup，不调就会低估它。<strong>这类不公平比较在论文和内部实验里都极其普遍，而且总是偏向「现状」。</strong>面试里能主动指出这一点，是很强的加分项。</p>", "消融的第一原则：单变量 + 同预算 + 同调参机会"),
        CALLOUT("intuition", "把这一节和上一节合起来看：<strong>增强强度、模型容量、训练时长三者构成一个三角，任意固定两个去调第三个，得到的结论都不能外推</strong>。<em>这也是为什么「某某论文说 Mosaic 有用/没用」这类断言几乎没有信息量</em>——不说清楚模型多大、训多久，那句话是不完整的。"),
    ])),
    ("design", "消融的正确设计：一张检查表", "".join([
        P("把前面几节的规则合成一张可执行的检查表。<strong>每一条都对应一种已经导致过错误结论的真实做法。</strong>"),
        TABLE(["检查项", "为什么", "怎么验"], [
            ["<strong>单变量</strong>", "同时改两处，收益无法归因", "diff 只应包含增强配置；<strong>配置指纹（模块 04）</strong>能自动查出「顺手改了别的」"],
            ["<strong>同训练预算</strong>", "强增强收敛慢，短训练系统性偏袒弱增强", "epoch/iter 数、LR schedule、close-mosaic 时点全部一致"],
            ["<strong>同调参预算</strong>", "现状被调过、新方案没有", "两个 arm 各做同等规模的 LR 搜索，或都用默认"],
            ["<strong>配对种子</strong>", "方差降 10 倍，算力降 8 倍", "两个 arm 用同一组 seed 列表；检查 RNG 消耗未错位"],
            ["<strong>预先声明种子数</strong>", "「跑到显著为止」= 自欺", "由功效分析定 n，写进实验计划，<strong>不许中途加</strong>"],
            ["<strong>预先声明切片</strong>", "事后挑切片 = p-hacking", "切片定义进版本库；每桶最小样本量也要定"],
            ["<strong>预先声明主指标</strong>", "多重比较下纯噪声也能给出「显著」", "一个 primary endpoint，其余标探索性；或做 FDR 校正"],
            ["<strong>确定性评测</strong>", "评测有随机性 → 所有结论作废", "同权重评两次必须逐位相同（模块 04 的断言）"],
            ["<strong>报告代价</strong>", "只报收益会被追问到崩", "训练时长、CPU 需求、显存、部署复杂度都要写"],
        ]),
        ASCII("""一次合格的增强消融，报告长什么样

  ┌─ 实验计划（跑之前写死）────────────────────────────
  │  假设      : 低光合成能提升夜间 AP，不损害晴天 AP
  │  主指标    : 夜间切片 AP           ← 只有一个
  │  次要指标  : 晴天切片 AP（不劣于 −0.5 pt 为门禁）
  │  设计      : 配对，seeds=[0,1,2,3,4]，其余全同
  │  MDE       : 2.80 × 0.21/√5 = **0.26 pt**  ← 小于它的差值不下结论
  │  切片定义  : 天气×4 / 距离桶×4 / 类别族×5（版本 v3，已入库）
  └────────────────────────────────────────────────────
  ┌─ 结果 ─────────────────────────────────────────────
  │  夜间  d̄ = +2.9 pt, 95% CI [+2.1, +3.6], t=8.2 (df=4, crit=2.78) ✅
  │  晴天  d̄ = −0.2 pt, 95% CI [−0.7, +0.3]  → 门禁通过（下界 > −0.5）
  │  整体  d̄ = +0.3 pt  ← **单独看它什么都说明不了**
  │  代价  : t_aug 12.0 → 13.8 ms（+15%），min_workers 7 → 8
  └────────────────────────────────────────────────────
  ┌─ 结论 ─────────────────────────────────────────────
  │  采纳。理由：主指标显著且效应量 (+2.9) 远超 MDE (0.26)，
  │  门禁指标未劣化，代价可接受（还有 1 个核的余量）。
  └────────────────────────────────────────────────────"""),
        DUAL(
            "注意报告里那句<strong>「整体 +0.3 单独看什么都说明不了」</strong>——它出现在结果里，但不是结论的依据。<em>这正是第 1 节和第 2 节合起来的结果：+0.3 既可能被切片掩盖，又落在噪声量级内</em>。而夜间的 +2.9 pt 有两重支撑：效应量远超 MDE，且置信区间下界（+2.1）也远超。<strong>「效应量 vs MDE」这个对比比 p 值有用得多</strong>，因为它同时回答了「有没有」和「有多大」。",
            "还要注意<strong>「门禁指标」的写法</strong>：晴天的判据不是「有没有显著下降」，而是<strong>「置信区间下界是否高于 −0.5 pt」</strong>。<em>这是非劣性检验（non-inferiority）的思路，而不是显著性检验</em>——因为「没测出显著下降」和「确实没下降」是两回事，前者可能只是样本不够。<strong>凡是「不劣化」类的要求，都必须用区间下界来判，不能用 p 值。</strong>这是回归门禁设计里最常见的方法学错误。",
        ),
        CALLOUT("intuition", "整张表可以压成一句话：<strong>把所有的决策自由度都挪到实验开始之前</strong>。跑之前定死种子数、切片、主指标、门禁阈值，跑完就只剩「照表读数」。<em>这不是形式主义——它消灭的是「事后选择」这个人类无法自我察觉的偏差源</em>，而这个偏差源的量级（第 2 节算过：挑 10 个种子的最大值 = +0.77 pt）比绝大多数真实增强的效应还大。"),
    ])),
    ("tsr_recipe", "为 TSR 定制一套增强配方：按失效模式反推", "".join([
        P("最后把整门课收拢：<strong>不要从「有哪些增强算子」出发去挑，要从「模型在哪里失效」出发去反推</strong>。这个方向差别决定了你是在堆 trick 还是在解决问题。"),
        H3("① 从失效模式到算子的映射"),
        TABLE(["失效模式", "当前 AP → 目标", "里程占比", "安全权重", "反推出的增强", "验证切片"], [
            ["<strong>远距离小目标（&lt;16px）</strong>", "0.31 → 0.50", "35%", "3.0", "<strong>Mosaic + 小尺度采样</strong>（制造更多小目标）+ 轻度运动模糊", "按像素尺寸分桶 [&lt;16, 16–32, 32–64, &gt;64]"],
            ["<strong>夜间 / 弱光</strong>", "0.48 → 0.62", "18%", "2.5", "<strong>低光合成</strong>（gamma + 噪声 + 量化）+ 保守 HSV 的 value 通道", "光照标签 = night / dusk"],
            ["<strong>雨雾</strong>", "0.41 → 0.58", "10%", "2.0", "大气散射雾化 <code>I = J·t + A(1−t)</code> + 雨条纹", "天气标签 = rain / fog"],
            ["<strong>稀有类（施工牌/让行）</strong>", "0.36 → 0.60", "4%", "3.5", "<strong>copy-paste</strong>（透视合理的尺度与位置）", "按类别族，尾部类单列"],
            ["<strong>逆光 / 隧道出入口</strong>", "0.44 → 0.60", "6%", "2.5", "局部过曝 + 眩光合成 + 强对比抖动", "场景标签 = tunnel_in / tunnel_out"],
            ["<strong>运动模糊</strong>", "0.52 → 0.65", "12%", "1.5", "方向性运动模糊核（长度按车速采样）", "车速分桶"],
            ["<strong>广告牌误检</strong>", "P 0.90 → 0.96", "25%", "1.2", "<strong>难背景 copy-paste</strong>（把广告牌抠出来贴成负样本）", "FP/km，按 FP 来源分类"],
        ]),
        P("优先级用 <code>(目标−当前) × 里程占比 × 安全权重</code> 排序，结果是 <strong>远距离小目标（0.200）≫ 夜间（0.063）&gt; 雨雾（0.034）≈ 稀有类（0.034）&gt; 逆光（0.024）≈ 运动模糊（0.023）&gt; 广告牌（0.018）</strong>。<em>这个排序和「哪个算子最流行」几乎没关系，这正是它的价值。</em>"),
        H3("② 配方本身（含每条的约束来源）"),
        CODE("""# TSR 增强配方 v1（按失效模式反推，含约束注释）
stage_A_mixing:
  mosaic:            p=1.0   scale=(0.4,1.2)   close_at_epoch=-15   # ★ 最后 15 epoch 必关
  mixup:             p=0.08                                          # 小模型档位置 0
stage_B_geometric:                     # ★ 合成一个仿射矩阵，只重采样一次
  affine:            p=0.9   scale=(0.5,1.5) translate=0.1 rotate=(-8,8) shear=(-4,4)
  small_scale_bias:  p=0.5   extra_downscale=(0.5,0.8)  # ← 主动制造小目标
  hflip:             p=0.5   whitelist=SYMMETRIC_CLASSES  # ★ 左转/右转/文字牌禁翻
stage_C_cleanup:
  clip + min_area=16px^2 + min_visibility=0.3            # ★ 紧跟几何段
stage_D_photometric:                   # ★ 必须在几何之后
  lowlight_synth:    p=0.30  gamma=(1.6,2.6) iso_noise=(8,30) quant_bits=7
  atmos_fog:         p=0.15  beta=(0.4,1.2)  A=(0.7,0.95)
  glare:             p=0.10  radius=(20,80)
  hsv:               p=0.70  hue=±8   sat=±25  val=±25  # ★ hue<=10：颜色是语义
  motion_blur:       p=0.20  length=(5,15) angle=按车速与转向采样
  jpeg/isp_artifact: p=0.25  quality=(45,90)
stage_E_instance:
  copy_paste_rare:   p=0.30  classes=TAIL_20  scale_by_perspective=True
  copy_paste_hardbg: p=0.20  source=广告牌/车身贴纸实例库  as_negative=True
stage_F_normalize:                     # ★ 与 val / 部署共用同一份代码
  letterbox(pad=114, stride=32) -> RGB -> /255 -> mean/std"""),
        DUAL(
            "配方里有<strong>四条星标约束</strong>，每一条都能追溯到前面的模块：<code>close_at_epoch=-15</code> 来自模块 03（close-mosaic）；<code>hflip whitelist</code> 来自模块 01（<em>水平翻转会把「左转」变「右转」</em>，这是 TSR 面试可以主动提的点）；<code>hue≤10</code> 来自模块 02（<em>红=禁令、蓝=指示、黄=警告，色相是语义</em>）；<code>stage_C 紧跟几何</code> 与 <code>stage_F 共用代码</code> 来自模块 04。<strong>一份没有这些约束注释的配方，下一个人一定会把它们改坏。</strong>",
            "还有一条隐性约束是<strong>算力</strong>：把上面所有算子的 CPU 成本加起来约 38.7 ms/样本，再加解码约 8 ms ≈ 46.7 ms。按模块 04 的公式，喂饱一张卡需要 <code>⌈533 × 0.0467⌉ = 25</code> 个 worker——<em>16 核的机器做不到</em>。<strong>所以配方必须连带给出算力方案</strong>：预解码成未压缩格式（省掉 8 ms）、Mosaic 移到 GPU 侧、或者把 <code>p</code> 调低换吞吐。<em>不带算力账的增强配方是不可执行的</em>，这是训练平台上最常见的返工原因。",
        ),
        H3("③ 验证方案"),
        OL([
            "<strong>逐条上、不要一次全上</strong>：按优先级顺序，每次只加一组算子，配对 5 种子，主指标 = 该失效模式对应的切片 AP，门禁 = 其余切片下界不低于 −0.5 pt。<em>一次全上的话，涨了不知道是谁的功劳，掉了不知道是谁的锅。</em>",
            "<strong>每条都要过 MDE 检查</strong>：σ_d 用该切片的历史方差（<em>小切片的方差更大</em>，MDE 也更大——夜间切片只有 18% 的样本，σ_d 可能是整体的 2 倍）。",
            "<strong>跨颜色族错分率</strong>作为 HSV 类算子的专项门禁（模块 02 的量化方法），mAP 对它不敏感。",
            "<strong>FP/km</strong> 作为 hard-background copy-paste 的主指标——<em>precision 会被 TP 数量稀释，FP/km 不会</em>（C55 模块 05）。",
            "<strong>最后做一次全配方 vs baseline 的联合验证</strong>，并检查是否出现「单条都涨、合起来不涨」——那说明算子之间在争夺同一份模型容量，需要重新分配 p。",
            "<strong>报告代价</strong>：t_aug、min_workers、训练时长、以及 close-mosaic 后的收敛曲线是否已平（否则第 6 节的预算陷阱又回来了）。",
        ]),
        CALLOUT("intuition", "这套方法的可迁移之处不在于具体算子，而在于<strong>「先量化失效模式、再反推干预、再逐条验证」这个闭环</strong>。<em>它和 C58 讲的数据闭环是同构的</em>：失效模式清单 ↔ 触发器，增强算子 ↔ 挖掘策略，切片门禁 ↔ 回归门禁。<strong>面试里能把「增强配方」讲成这样一个闭环而不是一串算子名，是最有效的区分度。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("消融与验证看起来是「方法学」，但它连着几个仍然开放的问题——而且这些问题正在变得更重要，因为模型改动的边际收益越来越小，噪声相对越来越大。"),
        UL([
            "<strong>深度学习实验的方差来源分解</strong>：Bouthillier 等人的工作系统地测量了初始化、数据顺序、增强、非确定 kernel、数据划分各自贡献了多少方差，结论之一是<em>「数据划分」的方差常常大于「随机种子」的方差</em>——这意味着很多论文的 ±std 严重低估了真实不确定性。<strong>检测任务上的同类测量仍然稀缺。</strong>",
            "<strong>报告规范与可复现性</strong>：Dodge 等人提出「报告计算预算与超参搜索规模」（因为「最好模型的性能」是搜索预算的函数），以及用 <em>expected max performance vs budget</em> 曲线代替单点数字。<em>这个规范在检测领域几乎没有被采纳</em>，而它恰恰能解决第 6 节讲的「同调参预算」问题。",
            "<strong>增强效果的理论刻画</strong>：现有理论主要把增强解释为「群等变性的近似」或「隐式正则化」，能定性解释但不能定量预测「这个增强在这个数据集上能涨多少」。<strong>「给定数据分布与模型容量，预测某个增强的收益」目前完全做不到</strong>——这也是为什么一切只能靠实验。",
            "<strong>分场景/分组的鲁棒评测</strong>：Group DRO、最差组精度（worst-group accuracy）这一支工作把「不能只看平均」形式化成了优化目标而不只是评测口径。<em>把它用到检测的分场景 AP 上（直接优化最差场景而不是平均）是一个自然但尚未成熟的方向</em>，难点在于场景标签本身的噪声与不完备。",
            "<strong>自动化的切片发现</strong>：人工定义切片必然漏掉「你没想到的失效模式」。Slice Discovery / Domino 这类方法尝试<em>用嵌入聚类自动找出模型表现异常差的样本子群</em>，再交给人命名。<strong>它与 C58 的难例挖掘是同一件事的两个入口</strong>，但在检测任务上（框级而非图级）的适配仍然开放。",
            "<strong>用 LLM/VLM 辅助实验分析</strong>：自动读实验日志、生成切片对比、指出不公平比较、起草消融报告——这是当前工业界正在快速落地的方向，也是 JD 里「automated workflows」的一部分。<em>开放问题是可靠性</em>：一个会「合理化」错误结论的分析助手，比没有更危险。",
        ]),
        CALLOUT("paper", "必读：<em>Accounting for Variance in Machine Learning Benchmarks</em>（Bouthillier et al., MLSys 2021）——方差来源分解与「多少次运行才够」的一手证据，本模块第 2/4 节的方法论基础；<em>Show Your Work: Improved Reporting of Experimental Results</em>（Dodge et al., EMNLP 2019）——报告规范与「性能是搜索预算的函数」；<em>Distributionally Robust Neural Networks (Group DRO)</em>（Sagawa et al., ICLR 2020）——把「最差组」变成优化目标；<em>Domino: Discovering Systematic Errors with Cross-Modal Embeddings</em>（Eyuboglu et al., ICLR 2022）——自动切片发现；<em>Bag of Freebies for Training Object Detection Neural Networks</em>（Zhang et al., 2019）与 YOLOv4/v7 论文的消融表——检测增强消融的实操范本（<em>注意用本模块的检查表去读它们，你会发现不少条目是不可比的</em>）。相邻课程：C61 模块 01（实验方法论）、C55 模块 05（安全导向评测）、C58 模块 05（闭环验证）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 增强的消融与验证（分场景切片 / 种子方差 / 配对检验 / 功效分析 / TSR 配方）

目标：把「这个增强有用吗」从一句直觉，变成一条**可以照着读数的流程**。

路线：**整体 mAP 的掩盖效应** → 种子方差与符号翻转率 → 配对设计与显著性 →
功效分析与 MDE → 增强过强的症状学 → **增强强度 × 训练时长的交互** →
**为 TSR 定制配方与验证方案** → ✏️ 4 道练习 → 📖 答案 → 🧪 工程胶囊。

> 心智模型：**平均会掩盖分布，单次会淹没在噪声，短训练会偏袒弱增强。**
> 这三件事各自都足以让你得出相反的结论 —— 而它们经常同时发生。

本 notebook 你会亲手实现：
1. 分场景切片对比：整体 +0.3 如何掩盖「晴天 −1.5、雨天 +3」，以及权重如何改变结论
2. 种子噪声下的**符号翻转率**与「挑最好种子」的作弊幅度
3. **配对 vs 非配对**的方差差异、配对 t 检验、bootstrap 置信区间
4. 功效分析（需要几个种子）与 **MDE**（这次实验能检出多小的提升）
5. 增强过强的症状学：容量-强度错配的定量演示
6. **增强强度 × 训练时长的交互**：同一比较在 12 与 300 epoch 下符号相反
7. **TSR 增强配方生成器** + 配方审计器 + 验证方案"""),

    md("""## 1 · 整体 mAP 会掩盖什么

同一份实验数据，按里程加权和按安全风险加权，可以差 4 倍以上。
**「有没有用」这个问题在没有定义权重之前是不完整的。**"""),
    code("""import numpy as np, math, itertools, json

SCENES = ['晴天白天', '夜间', '雨天', '隧道']
MILEAGE = np.array([0.60, 0.20, 0.15, 0.05])          # 里程占比
RISK = np.array([1.0, 2.5, 2.0, 3.0])                 # 单位里程的安全风险倍数
AP_BASE = np.array([0.7200, 0.4800, 0.4100, 0.3900])
AP_NEW = np.array([0.7050, 0.5100, 0.4400, 0.4200])

delta = AP_NEW - AP_BASE
print('%-10s %8s %10s %10s %10s' % ('场景', '里程占比', 'baseline', '加增强后', '变化(pt)'))
for i, s in enumerate(SCENES):
    print('%-10s %7.0f%% %10.4f %10.4f %+10.2f'
          % (s, 100 * MILEAGE[i], AP_BASE[i], AP_NEW[i], 100 * delta[i]))

ov_base = float(MILEAGE @ AP_BASE)
ov_new = float(MILEAGE @ AP_NEW)
print('%-10s %8s %10.4f %10.4f %+10.2f'
      % ('里程加权', '100%', ov_base, ov_new, 100 * (ov_new - ov_base)))
assert abs(100 * (ov_new - ov_base) - 0.30) < 1e-9
assert abs(100 * delta[0] + 1.50) < 1e-9
print()
print('⚠️  只看最后一行 -> "+0.3，微弱正收益，上吧"。')
print('    真相是：占 60%% 里程的主力场景掉了 1.5 个点，被三个小场景的 +3 抬了回来。')"""),

    code("""# 换一套权重，同一份数据给出 4 倍不同的结论
w_mile = MILEAGE / MILEAGE.sum()
w_risk = (MILEAGE * RISK) / (MILEAGE * RISK).sum()

d_mile = float(w_mile @ delta) * 100
d_risk = float(w_risk @ delta) * 100
print('%-16s %s' % ('里程权重', np.round(w_mile, 4).tolist()))
print('%-16s %s' % ('风险权重', np.round(w_risk, 4).tolist()))
print()
print('里程加权的整体变化: %+.2f pt' % d_mile)
print('风险加权的整体变化: %+.2f pt   <- 是里程加权的 %.1f 倍' % (d_risk, d_risk / d_mile))
assert abs(d_mile - 0.30) < 1e-9
assert d_risk / d_mile > 4.0

# 回归门禁：任何切片跌破容差就拦截，与整体是否为正无关
def regression_gate(base, new, names, tol_pt=1.0):
    drops = [(n, 100 * (b2 - b1)) for n, b1, b2 in zip(names, base, new)
             if 100 * (b2 - b1) < -tol_pt]
    return {'blocked': len(drops) > 0, 'violations': drops}

g1 = regression_gate(AP_BASE, AP_NEW, SCENES, tol_pt=1.0)
g2 = regression_gate(AP_BASE, AP_NEW, SCENES, tol_pt=2.0)
print()
print('门禁 tol=1.0pt:', '❌ 拦截' if g1['blocked'] else '✅ 通过',
      [(n, round(v, 2)) for n, v in g1['violations']])
print('门禁 tol=2.0pt:', '❌ 拦截' if g2['blocked'] else '✅ 通过')
assert g1['blocked'] and not g2['blocked']
print()
print('✅ 规矩：**先定义切片与权重，再跑实验**。事后挑切法是无法自我察觉的 p-hacking。')"""),

    md("""## 2 · 种子方差：多少提升才不是噪声

检测任务上，单次训练 mAP 的种子标准差典型在 **0.3–0.6 pt**。取 σ=0.5 算一笔账。"""),
    code("""SIGMA = 0.5          # 单次训练的种子标准差（pt）
rng = np.random.default_rng(0)
NT = 40000

def phi(z):          # 标准正态 CDF
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

sd_diff = math.sqrt(2) * SIGMA
print('单次训练 sigma = %.2f pt  ->  两次独立训练之差的 sd = %.3f pt' % (SIGMA, sd_diff))
print()

# (a) 零效应下观测到 |Δ| > 0.3 的概率
p_theory = 2 * (1 - phi(0.3 / sd_diff))
d_null = rng.normal(0, SIGMA, NT) - rng.normal(0, SIGMA, NT)
p_emp = float((np.abs(d_null) > 0.3).mean())
print('两个**完全相同**的配置各跑一次，|Δ| > 0.3 的概率:')
print('   理论 %.1f%%   实测 %.1f%%' % (100 * p_theory, 100 * p_emp))
assert abs(p_emp - p_theory) < 0.02 and abs(p_theory - 0.6714) < 0.002
print('   -> "+0.3 mAP" 这个数字，在单种子实验里几乎不含信息。')
print()

# (b) 真实效应 +0.4 时，单种子比较得出反号的概率
TRUE = 0.4
p_flip_theory = phi(-TRUE / sd_diff)
d_real = (TRUE + rng.normal(0, SIGMA, NT)) - rng.normal(0, SIGMA, NT)
p_flip = float((d_real < 0).mean())
print('真实效应 +%.1f pt，单种子比较给出**反号**的概率:' % TRUE)
print('   理论 %.1f%%   实测 %.1f%%' % (100 * p_flip_theory, 100 * p_flip))
assert abs(p_flip - p_flip_theory) < 0.02 and abs(p_flip_theory - 0.2858) < 0.002
print('   -> 约三分之一的概率，你会把一个真正有用的改动毙掉。')"""),

    code("""# 挑最好的种子：作弊幅度有多大
print('跑 k 个种子，只报最好的那个（哪怕真实效应为 0）:')
print('%-8s %14s %14s' % ('k', '平均"凭空收益"', '相对真实效应 +0.4'))
prev = -1e9
for k in (1, 2, 3, 5, 10, 20):
    best = rng.normal(0, SIGMA, size=(NT, k)).max(axis=1).mean()
    print('%-8d %+13.3f pt %13.2fx' % (k, best, best / 0.4))
    assert best > prev, '最大值的期望随 k 单调上升'
    prev = best
best10 = rng.normal(0, SIGMA, size=(NT, 10)).max(axis=1).mean()
assert 0.65 < best10 < 0.90
print()
print('⚠️  跑 10 个种子只报最好的，凭空得到 +%.2f pt —— **比绝大多数真实增强的效应还大**。' % best10)
print('    而且它不需要你有意作弊："这次跑崩了，重跑一遍" 就是一种选择性报告，')
print('    因为你只会对结果**差**的实验说"跑崩了"。')
print('✅ 防线：跑之前定死种子数与报告方式（均值±std），N 由功效分析决定，不由结果决定。')"""),

    md("""## 3 · 配对设计：让方差自己抵消掉

`y[s,a] = mu[a] + b[s] + eps[s,a]`。同一个种子下 `b[s]` 对两个 arm 是共同的，做差就抵消。
**这是本模块性价比最高的一条建议。**"""),
    code("""SD_SEED, SD_RESID = 0.45, 0.15          # 种子效应 / 残差
MU = 0.40                                # 真实效应 (pt)
NS = 60000
r2 = np.random.default_rng(7)

b_shared = r2.normal(0, SD_SEED, NS)     # 配对：两个 arm 共用同一个种子效应
d_paired = (MU + b_shared + r2.normal(0, SD_RESID, NS)) \\
           - (0.0 + b_shared + r2.normal(0, SD_RESID, NS))
d_unpaired = (MU + r2.normal(0, SD_SEED, NS) + r2.normal(0, SD_RESID, NS)) \\
             - (0.0 + r2.normal(0, SD_SEED, NS) + r2.normal(0, SD_RESID, NS))

sd_p, sd_u = float(d_paired.std(ddof=1)), float(d_unpaired.std(ddof=1))
th_p = math.sqrt(2 * SD_RESID ** 2)
th_u = math.sqrt(2 * (SD_SEED ** 2 + SD_RESID ** 2))
print('%-24s %10s %10s' % ('设计', '实测 sd', '理论 sd'))
print('%-24s %10.4f %10.4f' % ('配对（共用种子）', sd_p, th_p))
print('%-24s %10.4f %10.4f' % ('非配对（各自种子）', sd_u, th_u))
assert abs(sd_p - th_p) < 0.01 and abs(sd_u - th_u) < 0.02
assert sd_u / sd_p > 2.5
print()
print('方差比 = %.1fx，标准差比 = %.1fx' % ((sd_u / sd_p) ** 2, sd_u / sd_p))
print('-> 同样的检出能力，配对设计所需的训练次数少了约 %.0f 倍。' % ((sd_u / sd_p) ** 2))
print()
print('⚠️  配对成立的两个前提（必须显式检查）：')
print('   ① 种子真的控制住了所有共享随机性（初始化 / shuffle / 增强 RNG）')
print('      —— 若 treatment 改变了增强算子数量，RNG 消耗次数就变了，后续序列错开，配对部分失效')
print('   ② 两个 arm 的其他一切完全相同（epoch / LR schedule / close-mosaic 时点 / 评测代码）')"""),

    code("""# 配对 t 检验 + bootstrap 置信区间：两个都要看
T_CRIT_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
             8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
             14: 2.145, 15: 2.131, 19: 2.093, 24: 2.064, 29: 2.045}

def paired_t(diffs):
    d = np.asarray(diffs, float); n = len(d)
    sd = float(d.std(ddof=1)); df = n - 1
    t = float(d.mean()) / (sd / math.sqrt(n)) if sd > 0 else float('inf')
    crit = T_CRIT_95.get(df, 1.960)
    return {'mean': float(d.mean()), 'sd': sd, 't': t, 'df': df,
            'crit': crit, 'significant': abs(t) > crit}

def bootstrap_ci(diffs, B=8000, alpha=0.05, seed=0):
    d = np.asarray(diffs, float); n = len(d)
    g = np.random.default_rng(seed)
    means = d[g.integers(0, n, size=(B, n))].mean(axis=1)
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))

# 两组差值，**均值都是 +0.40 pt**，唯一的区别是方差
D_PAIRED = [0.42, 0.31, 0.55, 0.28, 0.44]        # 配对设计得到的 5 个差值
D_UNPAIR = [0.95, -0.42, 1.10, -0.15, 0.52]      # 非配对设计得到的 5 个差值

print('%-14s %8s %8s %8s %8s %-10s %s' % ('设计', 'mean', 'sd', 't', 'crit', '显著?', '95% CI'))
for tag, d in [('配对', D_PAIRED), ('非配对', D_UNPAIR)]:
    r = paired_t(d); lo, hi = bootstrap_ci(d, seed=1)
    print('%-14s %+8.3f %8.3f %8.2f %8.3f %-10s [%+.3f, %+.3f]'
          % (tag, r['mean'], r['sd'], r['t'], r['crit'],
             '✅ 是' if r['significant'] else '❌ 否', lo, hi))

rp, ru = paired_t(D_PAIRED), paired_t(D_UNPAIR)
assert abs(rp['mean'] - 0.40) < 1e-9 and abs(ru['mean'] - 0.40) < 1e-9
assert rp['significant'] and not ru['significant']
lo_p, hi_p = bootstrap_ci(D_PAIRED, seed=1)
lo_u, hi_u = bootstrap_ci(D_UNPAIR, seed=1)
assert lo_p > 0, '配对：区间下界 > 0'
assert lo_u < 0 < hi_u, '非配对：区间跨过 0，证据不足'
assert (hi_u - lo_u) > 3 * (hi_p - lo_p)
print()
print('两组的均值**完全一样**（+0.40 pt），结论却相反 —— 差别只在方差。')
print('区间宽度：配对 %.3f  vs  非配对 %.3f （%.1f 倍）'
      % (hi_p - lo_p, hi_u - lo_u, (hi_u - lo_u) / (hi_p - lo_p)))
print('✅ 三步顺序：① 有没有效应(t) -> ② 效应多大多确定(CI) -> ③ 值不值得(工程容差)')"""),

    md("""## 4 · 功效分析：动手之前先算需要多少种子

`n >= (z_{1-a/2} + z_{1-b})^2 * sd_d^2 / delta^2`，反过来是
`MDE(n) = (z+zb) * sd_d / sqrt(n)` —— **MDE 应该写在实验报告的最上面。**"""),
    code("""Z_ALPHA = {0.05: 1.959964, 0.10: 1.644854}
Z_POWER = {0.80: 0.841621, 0.90: 1.281552}

def seeds_needed(sigma_d, delta, alpha=0.05, power=0.80):
    k = (Z_ALPHA[alpha] + Z_POWER[power]) ** 2
    return int(math.ceil(k * sigma_d ** 2 / delta ** 2))

def mde(sigma_d, n, alpha=0.05, power=0.80):
    return (Z_ALPHA[alpha] + Z_POWER[power]) * sigma_d / math.sqrt(n)

SD_PAIRED, SD_UNPAIRED = 0.21, 0.67
print('alpha=0.05, power=0.80  ->  (z + z_beta)^2 = %.3f'
      % (Z_ALPHA[0.05] + Z_POWER[0.80]) ** 2)
print()
print('%-14s %8s %14s %14s %14s' % ('设计', 'sd_d', '检出+0.4', '检出+0.2', '检出+0.1'))
for tag, s in [('配对', SD_PAIRED), ('非配对', SD_UNPAIRED)]:
    print('%-14s %8.2f %13d个 %13d个 %13d个'
          % (tag, s, seeds_needed(s, 0.4), seeds_needed(s, 0.2), seeds_needed(s, 0.1)))
assert seeds_needed(0.21, 0.4) == 3
assert seeds_needed(0.21, 0.2) == 9
assert seeds_needed(0.21, 0.1) == 35
assert seeds_needed(0.67, 0.1) == 353
print()
print('%-24s %12s' % ('能跑的配对种子数', 'MDE (pt)'))
for n in (3, 5, 10, 20):
    print('%-24d %12.3f' % (n, mde(SD_PAIRED, n)))
assert abs(mde(0.21, 5) - 0.26311) < 1e-4
print()
print('-> 只能跑 5 个配对种子，MDE = %.2f pt。' % mde(SD_PAIRED, 5))
print('   **任何小于它的观测差值，无论正负，都不该被当成结论。**')
print()
print('要可靠检出 +0.1 pt：配对 %d 次训练，非配对 %d 次（12h/次 -> %.0f 天）。'
      % (seeds_needed(0.21, 0.1), seeds_needed(0.67, 0.1),
         seeds_needed(0.67, 0.1) * 0.5))
print('✅ 结论不是"想办法跑 353 次"，而是"+0.1 在当前方差下不可验证，不要基于它做决策"。')
print('   三条出路：① 降 sd_d（配对/确定性评测/更长训练）')
print('             ② 提 delta（做更有力的改动，别堆小 trick）')
print('             ③ 换信噪比更高的指标（分场景 AP 通常比整体 mAP 好）')"""),

    code("""# 多重比较：一次看 10 个算子 × 8 个切片会发生什么
def any_false_positive(n_tests, alpha=0.05):
    return 1 - (1 - alpha) ** n_tests

print('%-30s %14s' % ('检验次数', 'P(至少一个假阳性)'))
for n in (1, 5, 10, 40, 80):
    print('%-30d %13.1f%%' % (n, 100 * any_false_positive(n)))
assert abs(any_false_positive(10) - 0.4013) < 1e-3
assert any_false_positive(80) > 0.98
print()
print('10 个算子各做一次检验 -> 40%% 概率至少有一个假阳性。')
print('再乘 8 个切片 = 80 次检验 -> %.0f%% —— **纯噪声也会给你四个"显著"发现**。'
      % (100 * any_false_positive(80)))
print()

def bonferroni(pvals, alpha=0.05):
    m = len(pvals)
    return [p * m <= alpha for p in pvals]

pv = [0.001, 0.012, 0.030, 0.041, 0.049]
print('原始 p 值:', pv)
print('未校正显著:', [p <= 0.05 for p in pv], '-> %d 个' % sum(p <= 0.05 for p in pv))
print('Bonferroni:', bonferroni(pv), '-> %d 个' % sum(bonferroni(pv)))
assert sum(p <= 0.05 for p in pv) == 5 and sum(bonferroni(pv)) == 1
print()
print('✅ 规则：要么预先声明**一个**主指标（其余标探索性），要么做 Bonferroni/FDR 校正。')
print('   "我在 8 个切片里发现雨天显著提升" —— 若切片是事后挑的，几乎没有证据价值。')"""),
]

NB += [
    md("""## 5 · 增强过强的症状学

用一个可解析的玩具模型把「容量-强度错配」算出来：
增强提高有效任务难度（收敛更慢）、带来泛化收益（饱和）、但容量不足时会反噬。"""),
    code("""def run_model(capacity, aug, epochs, tau0=10.0):
    '''玩具模型：capacity=模型容量上限, aug=增强强度, epochs=训练预算。
       val_clean = 干净验证集上的表现； train_aug = 训练日志里看到的（训练集带增强）。'''
    tau = tau0 * (1 + 1.5 * aug)                     # 强增强 -> 收敛更慢
    prog = 1 - math.exp(-epochs / tau)               # 训练进度
    robust = 0.14 * (1 - math.exp(-2.0 * aug))       # 泛化收益（随强度饱和）
    penalty = 0.07 * aug ** 2 / capacity             # 容量不足时的反噬（∝ 强度^2 / 容量）
    val_clean = capacity * prog + robust - penalty
    return {'val_clean': val_clean, 'train_aug': val_clean - 0.22 * aug}

CAP_LARGE, CAP_TINY, EP = 0.78, 0.55, 100
AUGS = [0.0, 0.3, 0.6, 1.0, 1.4]

print('训练 %d epoch，两档模型容量下的表现' % EP)
print('%-6s | %-28s | %-28s' % ('aug', 'large (capacity 0.78)', 'tiny (capacity 0.55)'))
print('%-6s | %10s %10s %6s | %10s %10s %6s'
      % ('', 'train(带增强)', 'val(干净)', 'Δpt', 'train(带增强)', 'val(干净)', 'Δpt'))
base_L = run_model(CAP_LARGE, 0.0, EP)['val_clean']
base_T = run_model(CAP_TINY, 0.0, EP)['val_clean']
vals_L, vals_T = [], []
for a in AUGS:
    L, T = run_model(CAP_LARGE, a, EP), run_model(CAP_TINY, a, EP)
    vals_L.append(L['val_clean']); vals_T.append(T['val_clean'])
    print('%-6.1f | %10.4f %10.4f %+6.1f | %10.4f %10.4f %+6.1f'
          % (a, L['train_aug'], L['val_clean'], 100 * (L['val_clean'] - base_L),
             T['train_aug'], T['val_clean'], 100 * (T['val_clean'] - base_T)))

best_L = AUGS[int(np.argmax(vals_L))]
best_T = AUGS[int(np.argmax(vals_T))]
print()
print('最优强度: large = %.1f   tiny = %.1f' % (best_L, best_T))
assert best_L == 0.6 and best_T == 0.3
i1 = AUGS.index(1.0)
d_L = 100 * (vals_L[i1] - base_L); d_T = 100 * (vals_T[i1] - base_T)
print('同一份 aug=1.0 的配置: large %+.1f pt，tiny %+.1f pt —— **符号相反**' % (d_L, d_T))
assert d_L > 0 > d_T
print()
print('✅ 这就是 YOLO 系为 n/s/m/l/x 各档配不同增强强度的原因，不是调参玄学。')
print('   把大模型的增强配置照搬到 tiny 模型上，是很常见也很昂贵的错误。')"""),

    code("""# 症状诊断器：区分"正常现象"与"真的病了"
def diagnose(capacity, aug, epochs, tau0=10.0):
    base = run_model(capacity, 0.0, epochs, tau0)['val_clean']
    r = run_model(capacity, aug, epochs, tau0)
    return {
        'val_gt_train': r['val_clean'] > r['train_aug'],      # 症状：验证优于训练
        'val_below_baseline': r['val_clean'] < base,          # 判据：验证低于无增强 baseline
        'delta_pt': 100 * (r['val_clean'] - base),
    }

print('%-8s %-16s %-20s %10s %s' % ('aug', '验证>训练?', '验证<无增强baseline?', 'Δpt', '诊断'))
for a in AUGS:
    d = diagnose(CAP_LARGE, a, EP)
    verdict = ('✅ 健康' if not d['val_below_baseline'] else '❌ 增强过强')
    print('%-8.1f %-16s %-20s %+10.1f %s'
          % (a, '是（正常现象）' if d['val_gt_train'] else '否',
             '是' if d['val_below_baseline'] else '否', d['delta_pt'], verdict))

d06 = diagnose(CAP_LARGE, 0.6, EP)
d14 = diagnose(CAP_LARGE, 1.4, EP)
assert d06['val_gt_train'] and not d06['val_below_baseline'], 'aug=0.6：验证优于训练但完全健康'
assert d14['val_below_baseline'], 'aug=1.4：真的过强了'
print()
print('⚠️  「验证指标高于训练指标」在强增强的检测训练里是**预期行为**，不是 bug ——')
print('    训练时看到的是拼过/扭过/压暗加噪的图，验证时看到的是干净原图，后者当然更容易。')
print('    把它当成数据泄漏去查，会浪费大量时间。')
print('✅ 唯一的判据是 **验证指标 vs 无增强 baseline**，而不是「验证 vs 训练」。')"""),

    md("""## 6 · 增强强度 × 训练时长：短训练下的比较是不公平的

**同一个比较，在 12 epoch 和 300 epoch 下符号相反。**
这是消融设计里最容易犯、后果最严重的错误。"""),
    code("""EPOCH_GRID = [12, 36, 100, 300]
AUG_GRID = [0.0, 0.3, 0.6, 1.0]
table = np.zeros((len(EPOCH_GRID), len(AUG_GRID)))
for i, ep in enumerate(EPOCH_GRID):
    for j, a in enumerate(AUG_GRID):
        table[i, j] = run_model(CAP_LARGE, a, ep)['val_clean']

print('%-12s' % '训练预算', end='')
for a in AUG_GRID:
    print('%12s' % ('aug=%.1f' % a), end='')
print('%14s' % '最优强度')
best_augs = []
for i, ep in enumerate(EPOCH_GRID):
    j = int(np.argmax(table[i]))
    best_augs.append(AUG_GRID[j])
    print('%-12s' % ('%d epoch' % ep), end='')
    for k in range(len(AUG_GRID)):
        mark = '*' if k == j else ' '
        print('%11.3f%s' % (table[i, k], mark), end='')
    print('%14.1f' % AUG_GRID[j])

print()
print('最优增强强度随预算变化:', best_augs)
assert best_augs == [0.0, 0.3, 0.6, 0.6]
assert all(best_augs[i] <= best_augs[i + 1] for i in range(len(best_augs) - 1)), '单调不减'

j0, j6 = AUG_GRID.index(0.0), AUG_GRID.index(0.6)
d12 = 100 * (table[0, j6] - table[0, j0])
d300 = 100 * (table[3, j6] - table[3, j0])
print()
print('同一个比较（aug=0.6 vs aug=0.0）:')
print('  12 epoch 预算下 : %+.2f pt  -> 结论"强增强有害"' % d12)
print('  300 epoch 预算下: %+.2f pt  -> 结论"强增强有益"' % d300)
assert d12 < -10.0 and d300 > 6.0
print()
print('⚠️  团队为了"快速迭代"把消融预算砍到 1/10，就会**系统性地**淘汰掉所有强增强方案 ——')
print('    短预算下的排序不是随机偏差，它有明确方向：**永远偏袒弱增强**。')
print('✅ 三条对策（成本递增）：')
print('   ① 用足够长的预算做消融（最可靠、最贵）')
print('   ② 缩短预算的同时按比例缩放增强强度（把"强度×时长"当联合超参）')
print('   ③ **看曲线不看终点**：强增强曲线在预算末尾仍明显上升 = "排序不可信"的证据')
print('      —— 第 ③ 条几乎不花额外成本，应当成为默认动作。')"""),

    code("""# 第 ③ 条的代码化：末段斜率检测器
def tail_slope(capacity, aug, epochs, window=0.2, tau0=10.0):
    '''最后 window 比例的训练区间里，val 还涨了多少（pt）。'''
    e0 = epochs * (1 - window)
    v0 = run_model(capacity, aug, e0, tau0)['val_clean']
    v1 = run_model(capacity, aug, epochs, tau0)['val_clean']
    return 100 * (v1 - v0)

print('%-10s %14s %14s %s' % ('aug', '12ep 末段斜率', '300ep 末段斜率', '12ep 是否已收敛'))
for a in AUG_GRID:
    s12, s300 = tail_slope(CAP_LARGE, a, 12), tail_slope(CAP_LARGE, a, 300)
    print('%-10.1f %+13.2f %+13.2f %s'
          % (a, s12, s300, '✅ 是' if s12 < 1.0 else '❌ 否，排序不可信'))
assert tail_slope(CAP_LARGE, 1.0, 12) > 1.0, '强增强在 12ep 时远未收敛'
assert tail_slope(CAP_LARGE, 1.0, 300) < 0.1, '300ep 时已平'
print()
print('✅ 12 epoch 下 aug>=0.3 的曲线全都还在明显上升 -> 这个预算下的排序不能采信。')
print('   把"末段斜率"打进实验报告，一眼就知道这次消融的结论有没有资格下。')"""),

    md("""## 7 · 为 TSR 定制一套增强配方：按失效模式反推

**不要从「有哪些算子」出发去挑，要从「模型在哪里失效」出发去反推。**
优先级 = (目标 − 当前) × 里程占比 × 安全权重。"""),
    code("""FAILURE_MODES = [
    # id,             中文,                cur,  target, mileage, safety
    ('far_small',     '远距离小目标(<16px)', 0.31, 0.50, 0.35, 3.0),
    ('night',         '夜间 / 弱光',        0.48, 0.62, 0.18, 2.5),
    ('rain_fog',      '雨雾',              0.41, 0.58, 0.10, 2.0),
    ('rare_class',    '稀有类(施工/让行)',   0.36, 0.60, 0.04, 3.5),
    ('backlight',     '逆光 / 隧道出入口',   0.44, 0.60, 0.06, 2.5),
    ('motion_blur',   '运动模糊',           0.52, 0.65, 0.12, 1.5),
    ('billboard_fp',  '广告牌误检(precision)', 0.90, 0.96, 0.25, 1.2),
]

AUG_CATALOG = {
    'mosaic':        dict(targets=['far_small'], cpu_ms=26.0, p=1.0,
                          risk='中：必须配 close_mosaic'),
    'small_scale':   dict(targets=['far_small'], cpu_ms=0.4, p=0.5,
                          risk='低：主动制造小目标'),
    'motion_blur':   dict(targets=['motion_blur', 'far_small'], cpu_ms=1.2, p=0.2,
                          risk='中：过强会毁掉小目标的高频信息'),
    'lowlight':      dict(targets=['night', 'backlight'], cpu_ms=1.8, p=0.3,
                          risk='低：gamma + ISO 噪声 + 量化'),
    'hsv_mild':      dict(targets=['night', 'backlight'], cpu_ms=0.9, p=0.7,
                          risk='高：hue<=10，颜色是语义'),
    'atmos_fog':     dict(targets=['rain_fog'], cpu_ms=2.1, p=0.15,
                          risk='低：I = J*t + A(1-t)'),
    'copy_paste':    dict(targets=['rare_class'], cpu_ms=3.5, p=0.3,
                          risk='中：尺度/位置必须符合透视'),
    'hard_bg_paste': dict(targets=['billboard_fp'], cpu_ms=2.8, p=0.2,
                          risk='低：广告牌实例库贴成负样本'),
    'hflip':         dict(targets=[], cpu_ms=0.2, p=0.5,
                          risk='极高：左转->右转，必须类别白名单'),
}

def priority(m):
    _id, _cn, cur, tgt, mile, safe = m
    return (tgt - cur) * mile * safe

ranked = sorted(FAILURE_MODES, key=priority, reverse=True)
print('%-16s %-22s %8s %8s %8s %10s' % ('id', '失效模式', '缺口pt', '里程', '安全权重', '优先级'))
for m in ranked:
    print('%-16s %-22s %8.1f %7.0f%% %8.1f %10.4f'
          % (m[0], m[1], 100 * (m[3] - m[2]), 100 * m[4], m[5], priority(m)))
assert [m[0] for m in ranked[:3]] == ['far_small', 'night', 'rain_fog']
assert abs(priority(ranked[0]) - 0.1995) < 1e-9
print()
print('-> 排序结果和"哪个算子最流行"几乎没关系。**这正是它的价值。**')"""),

    code("""# 按优先级装配配方，并算算力账
def build_recipe(ranked_modes, catalog, decode_ms=8.0):
    chosen, cover = [], {}
    for m in ranked_modes:
        mid = m[0]
        for name, spec in catalog.items():
            if mid in spec['targets'] and name not in chosen:
                chosen.append(name)
                cover.setdefault(mid, []).append(name)
    cpu = decode_ms + sum(catalog[n]['cpu_ms'] for n in chosen)
    return {'ops': chosen, 'cover': cover, 'cpu_ms': cpu, 'decode_ms': decode_ms}

rec = build_recipe(ranked, AUG_CATALOG)
print('选中算子(%d 个):' % len(rec['ops']))
for n in rec['ops']:
    s = AUG_CATALOG[n]
    print('  %-16s p=%.2f  cpu=%5.1fms  targets=%-28s %s'
          % (n, s['p'], s['cpu_ms'], ','.join(s['targets']), s['risk']))
print()
print('单样本 CPU 成本: 解码 %.1f + 增强 %.1f = %.1f ms'
      % (rec['decode_ms'], rec['cpu_ms'] - rec['decode_ms'], rec['cpu_ms']))
assert set(rec['ops']) >= {'mosaic', 'small_scale', 'lowlight', 'atmos_fog', 'copy_paste'}
assert 'hflip' not in rec['ops'], 'hflip 不针对任何失效模式，不该被自动选入'
assert abs(rec['cpu_ms'] - 46.7) < 1e-9

# 算力账（复用模块 04 的公式）
GPU_IPS, CORES = 32 / 0.060, 16
def need_workers(cpu_ms):
    return int(math.ceil(GPU_IPS * cpu_ms / 1000.0))

print()
print('%-38s %10s %10s %8s' % ('方案', 'CPU(ms)', '最少worker', '16核可行?'))
plans = [('原样上（含 JPEG 解码）', rec['cpu_ms']),
         ('+ 预解码成未压缩格式', rec['cpu_ms'] - rec['decode_ms']),
         ('+ 预解码 + Mosaic 移到 GPU 侧', rec['cpu_ms'] - rec['decode_ms'] - 26.0)]
for tag, c in plans:
    w = need_workers(c)
    print('%-38s %10.1f %10d %8s' % (tag, c, w, '✅' if w <= CORES else '❌'))
assert need_workers(46.7) == 25 and need_workers(38.7) == 21 and need_workers(12.7) == 7
print()
print('⚠️  **不带算力账的增强配方是不可执行的** —— 这是训练平台上最常见的返工原因。')
print('    原样上要 25 个 worker，16 核机器给不出来；必须预解码 + Mosaic 上 GPU。')"""),

    code("""# 验证方案：每条失效模式配一个主指标切片 + 门禁 + 该切片的 MDE
def slice_sigma(sigma_overall, frac):
    '''切片越小，方差越大（样本量 ∝ frac）。'''
    return sigma_overall / math.sqrt(frac)

N_SEEDS = 5
SLICE_DEF = {'far_small': '像素尺寸桶 [<16,16-32,32-64,>64]',
             'night': '光照标签 night/dusk',
             'rain_fog': '天气标签 rain/fog',
             'rare_class': '类别族：尾部 20 类单列',
             'backlight': '场景标签 tunnel_in/tunnel_out',
             'motion_blur': '车速分桶',
             'billboard_fp': 'FP/km，按 FP 来源分类'}

print('配对 %d 种子，整体 sd_d = %.2f pt' % (N_SEEDS, SD_PAIRED))
print('%-14s %8s %9s %9s %10s %s' % ('失效模式', '切片占比', 'sd_slice',
                                     'MDE(5)', '缺口pt', '5 种子够吗'))
plan = []
for m in ranked:
    mid, _cn, cur, tgt, mile, _safe = m
    s = slice_sigma(SD_PAIRED, mile)
    md_ = mde(s, N_SEEDS)
    gap = 100 * (tgt - cur)
    ok = gap > md_
    plan.append((mid, s, md_, gap, ok))
    print('%-14s %7.0f%% %9.3f %9.3f %10.1f %s'
          % (mid, 100 * mile, s, md_, gap, '✅ 够' if ok else '❌ 不够，要加种子/扩切片'))

sig_rare = slice_sigma(SD_PAIRED, 0.04)
assert abs(sig_rare - 1.05) < 1e-9
assert abs(mde(sig_rare, 5) - 1.3158) < 1e-3
print()
print('稀有类切片只占 4%% 里程 -> sd 是整体的 %.1f 倍，MDE 高达 %.2f pt。'
      % (sig_rare / SD_PAIRED, mde(sig_rare, 5)))
print('要在这个切片上可靠检出 +0.5 pt，需要 %d 个配对种子 —— 不现实。'
      % seeds_needed(sig_rare, 0.5))
print('✅ 对策不是加种子，而是**扩大该切片的评测样本量**（定向采集/标注），')
print('   或者换一个方差更小的指标（尾部类召回 @ 固定 FP/km）。')
print()
print('验证方案（逐条上，不要一次全上）:')
for i, (mid, s, md_, gap, ok) in enumerate(plan[:4], 1):
    print('  %d. 加 %-28s -> 主指标 %s' % (i, ','.join(rec['cover'].get(mid, ['—'])),
                                          SLICE_DEF[mid]))
    print('     门禁：其余切片 95%%CI 下界 >= -0.5 pt；MDE=%.2f pt' % md_)
print('  5. 最后做一次全配方 vs baseline 的联合验证，检查"单条都涨、合起来不涨"')
print('     （那说明算子在争夺同一份模型容量，需要重新分配 p）')"""),

    md("""## ✏️ 练习 1：分场景切片判定

实现 `slice_verdict(base, new, weights, names, tol_pt=1.0)`，返回
`{'overall_delta_pt', 'worst_slice', 'worst_delta_pt', 'blocked'}`。
`overall_delta_pt` 用 `weights` 加权（weights 会先归一化）；
`blocked` = 任一切片跌幅超过 `tol_pt`。"""),
    code("""def slice_verdict(base, new, weights, names, tol_pt=1.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
v = slice_verdict(AP_BASE, AP_NEW, MILEAGE, SCENES, tol_pt=1.0)
assert abs(v['overall_delta_pt'] - 0.30) < 1e-9, v
assert v['worst_slice'] == '晴天白天' and abs(v['worst_delta_pt'] + 1.50) < 1e-9
assert v['blocked'] is True
v2 = slice_verdict(AP_BASE, AP_NEW, MILEAGE, SCENES, tol_pt=2.0)
assert v2['blocked'] is False and abs(v2['overall_delta_pt'] - 0.30) < 1e-9
# 换成风险权重，整体收益是里程权重的 4 倍以上
v3 = slice_verdict(AP_BASE, AP_NEW, MILEAGE * RISK, SCENES, tol_pt=1.0)
assert v3['overall_delta_pt'] / v['overall_delta_pt'] > 4.0
# 全面上涨的情形
v4 = slice_verdict(AP_BASE, AP_BASE + 0.01, MILEAGE, SCENES)
assert not v4['blocked'] and abs(v4['overall_delta_pt'] - 1.0) < 1e-9
print('里程权重: 整体 %+.2f pt, 最差切片 %s %+.2f pt, 门禁 %s'
      % (v['overall_delta_pt'], v['worst_slice'], v['worst_delta_pt'],
         '拦截' if v['blocked'] else '通过'))
print('风险权重: 整体 %+.2f pt' % v3['overall_delta_pt'])
print('✅ 练习 1 通过：**只报整体 mAP 的实验报告应当被直接打回**')"""),

    md("""## ✏️ 练习 2：配对检验的三步判定

实现 `paired_test(diffs, tol_pt)`，把三个问题分开回答，返回
`{'mean','ci','stat_sig','practically_sig','verdict'}`：
- `stat_sig`：配对 t 显著 **且** bootstrap 95% CI 不跨过 0
- `practically_sig`：CI 下界 > `tol_pt`（工程容差：值不值得做）
- `verdict`：`'证据不足：加种子'` / `'统计显著但不值得'` / `'采纳'`

（bootstrap 用 `bootstrap_ci(diffs, seed=1)`，保证可复现。）"""),
    code("""def paired_test(diffs, tol_pt):
    # TODO: 依次算 paired_t / bootstrap_ci / 工程容差，再给 verdict
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r1 = paired_test(D_PAIRED, tol_pt=0.20)
assert r1['stat_sig'] and r1['practically_sig'] and r1['verdict'] == '采纳', r1
r2 = paired_test(D_PAIRED, tol_pt=0.60)
assert r2['stat_sig'] and not r2['practically_sig']
assert r2['verdict'] == '统计显著但不值得', r2
r3 = paired_test(D_UNPAIR, tol_pt=0.20)
assert not r3['stat_sig'] and r3['verdict'] == '证据不足：加种子', r3
assert abs(r1['mean'] - 0.40) < 1e-9 and abs(r3['mean'] - 0.40) < 1e-9
print('%-34s %8s %10s %s' % ('输入', 'mean', 'CI下界', 'verdict'))
for tag, r in [('配对差值, 容差0.20', r1), ('配对差值, 容差0.60', r2),
               ('非配对差值, 容差0.20', r3)]:
    print('%-34s %+8.3f %+10.3f %s' % (tag, r['mean'], r['ci'][0], r['verdict']))
print('✅ 练习 2 通过：**统计显著 ≠ 值得做**，第三步才是真正的决策依据')"""),

    md("""## ✏️ 练习 3：实验可行性规划

实现 `plan_experiment(sigma_d, delta_target, n_available, alpha=0.05, power=0.80)`，返回
`{'n_needed','mde','feasible','advice'}`。
`advice` 取 `'GO'`（`n_available >= n_needed`）或 `'NEED_MORE_SEEDS'`。
**跑之前算这一步，跑完就只剩照表读数。**"""),
    code("""def plan_experiment(sigma_d, delta_target, n_available, alpha=0.05, power=0.80):
    # TODO: 复用 seeds_needed 与 mde
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
a = plan_experiment(0.21, 0.4, 5)
assert a['n_needed'] == 3 and a['feasible'] and a['advice'] == 'GO'
assert abs(a['mde'] - 0.26311) < 1e-4
b = plan_experiment(0.21, 0.1, 5)
assert b['n_needed'] == 35 and not b['feasible'] and b['advice'] == 'NEED_MORE_SEEDS'
c = plan_experiment(0.67, 0.4, 5)
assert c['n_needed'] == 23 and not c['feasible']
assert abs(c['mde'] - 0.83945) < 1e-4
d = plan_experiment(1.05, 0.5, 5)          # 稀有类切片
assert d['n_needed'] == seeds_needed(1.05, 0.5) and not d['feasible']
print('%-40s %9s %9s %s' % ('场景', 'n_needed', 'MDE', 'advice'))
for tag, args in [('配对, 想检出+0.4, 有5种子', (0.21, 0.4, 5)),
                  ('配对, 想检出+0.1, 有5种子', (0.21, 0.1, 5)),
                  ('非配对, 想检出+0.4, 有5种子', (0.67, 0.4, 5)),
                  ('稀有类切片, 想检出+0.5, 有5种子', (1.05, 0.5, 5))]:
    r = plan_experiment(*args)
    print('%-40s %9d %9.3f %s' % (tag, r['n_needed'], r['mde'], r['advice']))
print('✅ 练习 3 通过：**MDE 应该写在实验报告的最上面**，它界定了这次实验能说什么')"""),

    md("""## ✏️ 练习 4：TSR 增强配方审计器

实现 `audit_recipe(recipe)`，返回**排序后**的问题代码列表。规则：

| 代码 | 触发条件 |
|---|---|
| `FLIP_NO_WHITELIST` | `ops` 含 `hflip` 且 `p>0`，但 `flip_whitelist` 为空 |
| `HUE_TOO_STRONG` | 任一算子的 `hue_deg > 10`（颜色是语义） |
| `MOSAIC_NO_CLOSE` | `ops` 含 `mosaic` 但 `close_mosaic_epochs <= 0` |
| `AUG_TOO_SPARSE` | `prod(1-p) > 0.25`（太多样本完全没被增强） |
| `CPU_OVER_BUDGET` | `cpu_ms > cpu_budget_ms` |
| `MODE_UNCOVERED` | `top_modes` 里有不在 `covered_modes` 的 |
| `NO_VAL_SLICE` | `val_slices` 为空 |"""),
    code("""def audit_recipe(recipe):
    # TODO: 逐条检查，返回 sorted(codes)
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
BAD = {'ops': {'hflip': {'p': 0.5}, 'hsv': {'p': 0.5, 'hue_deg': 25},
               'mosaic': {'p': 1.0}},
       'flip_whitelist': None, 'close_mosaic_epochs': 0,
       'cpu_ms': 52.0, 'cpu_budget_ms': 30.0,
       'top_modes': ['far_small', 'night', 'rain_fog'], 'covered_modes': ['far_small'],
       'val_slices': []}
GOOD = {'ops': {'hflip': {'p': 0.5}, 'hsv': {'p': 0.7, 'hue_deg': 8},
                'mosaic': {'p': 1.0}, 'lowlight': {'p': 0.3}, 'copy_paste': {'p': 0.3}},
        'flip_whitelist': ['circle_speed', 'warning_tri'], 'close_mosaic_epochs': 15,
        'cpu_ms': 12.7, 'cpu_budget_ms': 30.0,
        'top_modes': ['far_small', 'night', 'rain_fog'],
        'covered_modes': ['far_small', 'night', 'rain_fog', 'rare_class'],
        'val_slices': ['size_bucket', 'light', 'weather']}
SPARSE = dict(GOOD, ops={'lowlight': {'p': 0.1}, 'atmos_fog': {'p': 0.1},
                         'motion_blur': {'p': 0.1}})

assert audit_recipe(BAD) == ['CPU_OVER_BUDGET', 'FLIP_NO_WHITELIST', 'HUE_TOO_STRONG',
                             'MODE_UNCOVERED', 'MOSAIC_NO_CLOSE', 'NO_VAL_SLICE'], audit_recipe(BAD)
assert audit_recipe(GOOD) == [], audit_recipe(GOOD)
assert audit_recipe(SPARSE) == ['AUG_TOO_SPARSE'], audit_recipe(SPARSE)
print('BAD   ->', audit_recipe(BAD))
print('GOOD  ->', audit_recipe(GOOD) or '无问题 ✅')
print('SPARSE->', audit_recipe(SPARSE))
print('✅ 练习 4 通过：约束注释必须进 CI，不能指望下一个人记得')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def slice_verdict(base, new, weights, names, tol_pt=1.0):
    base = np.asarray(base, float); new = np.asarray(new, float)
    w = np.asarray(weights, float); w = w / w.sum()
    d_pt = 100 * (new - base)
    i = int(np.argmin(d_pt))
    return {'overall_delta_pt': float(w @ d_pt),
            'worst_slice': names[i],
            'worst_delta_pt': float(d_pt[i]),
            'blocked': bool(d_pt.min() < -tol_pt)}"""),
    code("""# 练习 2 参考答案
def paired_test(diffs, tol_pt):
    r = paired_t(diffs)
    lo, hi = bootstrap_ci(diffs, seed=1)
    stat = bool(r['significant'] and (lo > 0 or hi < 0))
    prac = bool(lo > tol_pt)
    if not stat:
        verdict = '证据不足：加种子'
    elif not prac:
        verdict = '统计显著但不值得'
    else:
        verdict = '采纳'
    return {'mean': r['mean'], 'ci': (lo, hi), 'stat_sig': stat,
            'practically_sig': prac, 'verdict': verdict}"""),
    code("""# 练习 3 参考答案
def plan_experiment(sigma_d, delta_target, n_available, alpha=0.05, power=0.80):
    n_need = seeds_needed(sigma_d, delta_target, alpha, power)
    m = mde(sigma_d, n_available, alpha, power)
    ok = n_available >= n_need
    return {'n_needed': n_need, 'mde': m, 'feasible': ok,
            'advice': 'GO' if ok else 'NEED_MORE_SEEDS'}"""),
    code("""# 练习 4 参考答案
def audit_recipe(recipe):
    ops = recipe.get('ops', {})
    codes = []
    if ops.get('hflip', {}).get('p', 0) > 0 and not recipe.get('flip_whitelist'):
        codes.append('FLIP_NO_WHITELIST')
    if any(spec.get('hue_deg', 0) > 10 for spec in ops.values()):
        codes.append('HUE_TOO_STRONG')
    if 'mosaic' in ops and recipe.get('close_mosaic_epochs', 0) <= 0:
        codes.append('MOSAIC_NO_CLOSE')
    p_none = 1.0
    for spec in ops.values():
        p_none *= (1.0 - spec.get('p', 0.0))
    if p_none > 0.25:
        codes.append('AUG_TOO_SPARSE')
    if recipe.get('cpu_ms', 0) > recipe.get('cpu_budget_ms', float('inf')):
        codes.append('CPU_OVER_BUDGET')
    if set(recipe.get('top_modes', [])) - set(recipe.get('covered_modes', [])):
        codes.append('MODE_UNCOVERED')
    if not recipe.get('val_slices'):
        codes.append('NO_VAL_SLICE')
    return sorted(codes)"""),

    md("""---
## 🧪 真实工程胶囊：实验计划模板 + 分场景报告 + TSR 配方"""),
    code("""RECIPE = r'''
# ============ 1. 实验计划（**跑之前写死并入库**）============
plan:
  hypothesis : 低光合成能提升夜间 AP，且不损害晴天 AP
  primary    : 夜间切片 AP                       # ★ 只有一个主指标
  gate       : 晴天切片 AP 的 95%CI 下界 >= -0.5 pt   # ★ 非劣性，用区间下界不用 p 值
  design     : paired, seeds=[0,1,2,3,4]          # ★ 配对：方差降 10 倍
  identical  : epochs / lr_schedule / close_mosaic_epoch / eval_code 全同
  mde        : (1.96+0.84) * sd_d / sqrt(5)       # ★ 写在报告最上面
  slices     : weather x4 / size_bucket x4 / class_family x5   (slices_v3, 已入库)
  n_locked   : true                                # ★ 不许中途加种子

# ============ 2. 跑之前的三条前置断言 ============
assert eval(model, val) == eval(model, val)        # 评测必须纯确定性（模块 04）
assert aug_fingerprint(cfg_A) != aug_fingerprint(cfg_B)   # 确实改了增强
assert diff_only_touches(cfg_A, cfg_B, allow={'aug'})     # ★ 单变量

# ============ 3. 分场景报告（**只报整体 mAP 的报告应被打回**）============
for slice_name in SLICES:
    d = [ap_new[s][slice_name] - ap_base[s][slice_name] for s in SEEDS]   # 逐种子配对差
    t   = paired_t(d)                        # 有没有效应
    ci  = bootstrap_ci(d)                    # 效应多大、多确定
    print(slice_name, mean=t['mean'], ci=ci, t=t['t'], crit=t['crit'],
          vs_mde=t['mean']/MDE)              # ★ 效应量 vs MDE 比 p 值有用
# 多重比较：主指标之外全部标 exploratory，或做 Bonferroni/FDR

# ============ 4. TSR 增强配方 v1（按失效模式反推，★=约束来源）============
stage_A_mixing:
  mosaic:       p=1.0  scale=(0.4,1.2)  close_at_epoch=-15   # ★m03 close-mosaic
  mixup:        p=0.08                                        # 小模型档置 0（容量-强度错配）
stage_B_geometric:                        # ★m04 合成一个仿射矩阵，只重采样一次
  affine:       p=0.9  scale=(0.5,1.5) translate=0.1 rotate=(-8,8) shear=(-4,4)
  small_scale:  p=0.5  extra_downscale=(0.5,0.8)   # ← 主动制造小目标（far_small）
  hflip:        p=0.5  whitelist=SYMMETRIC_CLASSES # ★m01 左转/右转/文字牌禁翻
stage_C_cleanup:
  clip + min_area=16px^2 + min_visibility=0.3      # ★m04 紧跟几何段
stage_D_photometric:                      # ★m04 必须在几何之后（否则被插值抹平）
  lowlight:     p=0.30 gamma=(1.6,2.6) iso_noise=(8,30) quant_bits=7   # night
  atmos_fog:    p=0.15 beta=(0.4,1.2) A=(0.7,0.95)                     # rain_fog
  hsv:          p=0.70 hue=+-8 sat=+-25 val=+-25   # ★m02 hue<=10：颜色是语义
  motion_blur:  p=0.20 length=(5,15) angle~车速与转向
stage_E_instance:
  copy_paste_rare:   p=0.30 classes=TAIL_20 scale_by_perspective=True  # rare_class
  copy_paste_hardbg: p=0.20 source=广告牌实例库 as_negative=True        # billboard_fp
stage_F_normalize:
  letterbox(pad=114, stride=32) -> RGB -> /255 -> mean/std   # ★与 val/部署共用同一函数

# ============ 5. 算力账（不带算力账的配方不可执行）============
# 增强 38.7ms + 解码 8.0ms = 46.7ms/样本 -> 需要 25 个 worker（16 核给不出）
# 对策：预解码成未压缩格式（-8ms）+ Mosaic 移到 GPU 侧（-26ms）-> 12.7ms -> 7 个 worker ✅

# ============ 6. 验证顺序（逐条上，不要一次全上）============
# 1) small_scale+mosaic -> 主指标 size_bucket<16px      2) lowlight+hsv -> 光照切片
# 3) atmos_fog -> 天气切片                              4) copy_paste -> 尾部类召回@固定FP/km
# 5) 全配方联合验证：检查"单条都涨、合起来不涨"（算子在争夺同一份容量）
# 门禁：其余切片 95%CI 下界 >= -0.5 pt；专项门禁：跨颜色族错分率（mAP 对它不敏感）
# 报告代价：t_aug / min_workers / 训练时长 / close-mosaic 后曲线是否已平（末段斜率）
'''
print(RECIPE)
for k in ['primary', 'gate', 'paired', 'mde', 'n_locked', 'aug_fingerprint',
          'close_at_epoch', 'whitelist', 'hue<=10', 'min_visibility',
          'copy_paste_rare', '25 个 worker', '末段斜率']:
    assert k in RECIPE, k
print('✅ 配方覆盖：实验计划 · 前置断言 · 分场景报告 · TSR 配方 · 算力账 · 验证顺序')"""),

    md("""### 小结

- **整体 mAP 是加权平均，平均的天职就是抹掉分布**。+0.3 可能是「晴天 −1.5、雨天 +3」；
  换一套权重（里程 vs 安全风险）同一份数据能差 **4 倍**。
  **先定义切片与权重，再跑实验**——事后挑切法是无法自我察觉的 p-hacking。
- **种子方差**：σ=0.5 pt 时，两个完全相同的配置有 **67%** 概率给出 |Δ|>0.3；
  真实效应 +0.4 时单种子有 **29%** 概率给出反号；跑 10 个种子只报最好的，
  凭空得到 **+0.77 pt**——比大多数真实增强的效应还大。
- **配对设计**是性价比最高的一招：共用同一批种子，差值 sd 从 0.67 降到 0.21，
  **方差降 10 倍、算力降 8 倍**。两组均值同为 +0.40 pt，配对显著、非配对不显著。
- **三步顺序**：有没有效应（t）→ 效应多大多确定（bootstrap CI）→ 值不值得（工程容差）。
  **MDE 写在报告最上面**；「不劣化」类要求必须用**区间下界**判，不能用 p 值。
- **增强过强的判据是「验证 vs 无增强 baseline」**，不是「验证 vs 训练」——
  后者在强增强下是**预期行为**。容量-强度错配：同一份 aug=1.0 在 large 上 +1.7、tiny 上 −1.6。
- **短训练系统性偏袒弱增强**：aug=0.6 vs 0.0 在 12 epoch 下 −11.4 pt、300 epoch 下 +6.6 pt。
  低成本对策：**看末段斜率**——曲线还在涨就说明这次消融没资格下结论。
- **TSR 配方按失效模式反推**：优先级 =(缺口 × 里程 × 安全权重)，
  远距离小目标 ≫ 夜间 > 雨雾 ≈ 稀有类。每条算子都要带**约束来源**与**验证切片**，
  并且**必须带算力账**（46.7 ms/样本 = 25 个 worker，16 核跑不动）。

至此 C56 全部结束。下一站建议：**C57（小目标检测）**——本模块排在第一优先级的
「远距离小目标」缺口，在那里有系统的架构与损失层面的解法。"""),
]
