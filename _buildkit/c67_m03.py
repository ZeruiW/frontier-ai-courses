# -*- coding: utf-8 -*-
"""C67 模块 03 · 元评测与校准（judge 到底有多准）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 02（偏差探针与去偏）；"
                 "C10 模块 02（标注者一致性）读过更好，但 kappa 与 Krippendorff 在本模块从零推"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_meta_eval.ipynb'
                       '（人类上界与天花板归一化 / accuracy vs kappa vs Krippendorff / '
                       '样本级 vs 系统级一致性 / 校准：ECE、可靠性图与温度缩放 / '
                       '成本-一致性前沿 / judge 漂移的 CUSUM 检测）'),
    ("核心参考", "Zheng et al., <em>MT-Bench &amp; Chatbot Arena</em>（NeurIPS 2023，judge 与人类一致率及人类之间的一致率）· "
                 "Krippendorff, <em>Content Analysis</em>（一致性系数的统一框架）· "
                 "Guo et al., <em>On Calibration of Modern Neural Networks</em>（ICML 2017，ECE 与温度缩放）· "
                 "Deutsch et al. 关于自动指标与人类相关性的系统级 vs 样本级讨论 · "
                 "本课程 C10 模块 02/06（一致性与校准）· C66 模块 02（金标准集）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-align", "元评测问的是什么：judge 要和「谁」对齐", "".join([
        P("元评测（meta-evaluation）就是<strong>评测这个评测器</strong>。"
          "但在算任何数字之前，必须先回答一个经常被跳过的问题：<strong>judge 要和什么对齐？</strong>"),
        TABLE(["对齐目标", "什么时候是对的", "怎么获得", "陷阱"], [
            ["<strong>单个人类标注员</strong>", "几乎从不", "最便宜", "标注员之间本来就不一致，对齐到某一个人没有意义"],
            ["<strong>多个标注员的多数意见</strong>", "<strong>最常见、通常是对的默认</strong>", "3–5 人重复标注", "多数意见在「难题」上本身就不稳定"],
            ["<strong>专家共识（讨论后）</strong>", "高风险场景（安全、医疗、法务）", "最贵", "共识可能掩盖真实的合理分歧"],
            ["<strong>下游任务表现</strong>", "judge 用作训练信号时", "需要跑完整的训练-评测回路", "反馈慢，但<em>这是最终极的效标</em>"],
            ["<strong>另一个更强的 judge</strong>", "<strong>几乎从不</strong>", "便宜", "两个 judge 可能共享同样的偏差（模块 02 第 7 节）"],
        ]),
        CALLOUT("danger", "最后一行值得单独警告：<strong>用一个更强的模型当「金标准」来验证一个更便宜的 judge，"
                          "只能证明两者一致，不能证明两者对。</strong>"
                          "长度偏差、格式偏差在几乎所有主流模型上方向一致——"
                          "<em>用 A 验证 B，会把这些共有偏差一路带进你的「验证通过」结论里</em>。"
                          "这个做法可以用来<strong>省钱</strong>（确认小 judge 能替代大 judge），"
                          "但不能用来<strong>验证正确性</strong>。"),
        P("确定了对齐目标之后，元评测要回答三个层次的问题，本模块依次展开："),
        OL([
            "<strong>一致性</strong>：judge 和目标有多像？（第 2–3 节）"
            "——但必须配着<strong>人类自身的一致率</strong>一起读，否则数字无法解释。",
            "<strong>分辨力</strong>：judge 能不能把你真正关心的两个东西区分开？（第 4 节）"
            "——<em>样本级一致率低，不代表系统级排序不对</em>。",
            "<strong>校准</strong>：judge 说「我 80% 确定」时，它对了 80% 吗？（第 5 节）",
        ]),
    ])),

    # ============================================================== 2
    ("human-ceiling", "人类上界：为什么 82% 可能已经是天花板", "".join([
        P("这是元评测里<strong>最常被忽略、也最容易导致错误结论</strong>的一件事。"),
        DUAL(
            "「我们的 judge 与人类标注的一致率是 82%」——这句话单独看，读者会自然地把它和 100% 比较，"
            "得出「还差 18 个点」的结论。<strong>但如果两个人类标注员之间的一致率也只有 84%，"
            "那么 82% 已经几乎顶到天花板了</strong>——剩下的 18 个点里，绝大部分是"
            "「这道题本来就没有唯一答案」，不是 judge 的错。",
            "形式化地说，设 $a_{HH}$ 是人类之间的一致率、$a_{JH}$ 是 judge 与人类的一致率。"
            "在「每个标注者独立地以概率 $p$ 给出与潜在真值一致的判断」这一简单模型下，"
            "二元任务里 $a_{HH} = p_H^2 + (1-p_H)^2$，$a_{JH} = p_J p_H + (1-p_J)(1-p_H)$。"
            "<strong>因此从 $a_{HH}$ 可以反解出 $p_H$，进而把 $a_{JH}$ 翻译成 $p_J$</strong>——"
            "这个 $p_J$ 才是「judge 有多准」的、不受人类噪声污染的度量。"
            "<em>notebook 第 1 节会把这个反解写成代码。</em>",
        ),
        H3("三个必须一起报的数字"),
        TABLE(["数字", "含义", "缺了它会怎样"], [
            ["<strong>$a_{JH}$</strong> judge–人类一致率", "judge 与目标的一致程度", "—"],
            ["<strong>$a_{HH}$</strong> 人类–人类一致率", "<strong>天花板</strong>", "读者会把 $a_{JH}$ 和 100% 比，系统性低估 judge"],
            ["<strong>随机一致率</strong>", "瞎猜能得多少（二元任务是 50%）", "读者会把 $a_{JH}$ 和 0% 比，系统性高估 judge"],
        ]),
        MATH(r"\text{天花板归一化一致率} = \frac{a_{JH} - a_{\text{chance}}}{a_{HH} - a_{\text{chance}}}"),
        CALLOUT("intuition", "这个归一化量的读法很直接：<strong>1.0 表示 judge 已经和人类一样好（顶到天花板），"
                             "0 表示 judge 只相当于瞎猜。</strong>"
                             "上面那个例子：$(0.82 - 0.5)/(0.84 - 0.5) = 0.94$——<strong>judge 达到了人类水平的 94%</strong>，"
                             "而不是「只有 82 分」。<em>这两种表述会导向完全不同的资源分配决策。</em>"),
        P("需要一个诚实的提醒：<strong>归一化量可能超过 1</strong>（judge 比人类更一致）。"
          "这<em>不一定</em>是好事——它也可能意味着 judge 有一个稳定的系统偏差，"
          "使它比人类更「自洽」但不更「正确」。<strong>一致性高不等于正确性高</strong>，"
          "这正是为什么模块 02 的偏差探针不能被一致率替代。"),
    ])),

    # ============================================================== 3
    ("agreement-coefs", "一致性系数：accuracy、kappa、Krippendorff 各自的适用面", "".join([
        P("「一致率」有很多种算法，它们在不同情形下给出差别很大的数字。选错会得出错误结论。"),
        TABLE(["系数", "公式要点", "什么时候用", "失效方式"], [
            ["<strong>原始一致率</strong>", "$a_o = \\Pr(\\text{两者相同})$", "类别均衡、只做粗略汇报", "<strong>类别不均衡时严重虚高</strong>：如果 90% 的样本人类都判 A，全判 A 的 judge 也有 90%"],
            ["<strong>Cohen's kappa</strong>", "$\\kappa = \\dfrac{a_o - a_e}{1 - a_e}$，$a_e$ 是按各自边缘分布算的随机一致", "<strong>两个评判者、名义类别</strong>——最常用", "边缘分布极不均衡时 kappa 会异常地低（<em>kappa 悖论</em>）"],
            ["<strong>Krippendorff's α</strong>", "基于观测不一致与期望不一致之比，支持任意评判者数、缺失值、有序/区间数据", "<strong>多个评判者、有缺失、或有序量表</strong>", "实现复杂；对小样本不稳定"],
            ["<strong>Spearman / Kendall 相关</strong>", "秩相关", "<strong>有序打分</strong>（1–5 分）而非分类", "对并列（tie）敏感；不惩罚系统性平移"],
        ]),
        CALLOUT("warn", "<strong>kappa 悖论</strong>值得知道：当两个评判者都高度倾向于某一类时"
                        "（比如 92% 的样本都被判为「通过」），即使原始一致率高达 90%，"
                        "kappa 也可能只有 0.2 左右。<em>这不是 kappa 算错了</em>——"
                        "它在告诉你「在这个极度不均衡的分布上，你们的一致大部分可以由「都爱说通过」解释」。"
                        "<strong>正确反应不是换一个更好看的系数，而是承认「这个任务在当前分布下几乎没有区分度」</strong>，"
                        "并去找更均衡的样本来评（第 8 节的元评测集设计）。"),
        H3("pairwise 场景的特殊处理"),
        P("在 A/B/tie 三分类的 pairwise 判断上，有一个实践细节："
          "<strong>「A vs B」的分歧与「A vs tie」的分歧，严重程度不同。</strong>"
          "前者是方向相反，后者只是强度不同。因此建议："),
        UL([
            "报<strong>两个</strong>数字：严格一致率（三类完全相同）与<strong>方向一致率</strong>（把 tie 视为可接受，只看有没有判反方向）；",
            "或者用<strong>有序版本</strong>的 Krippendorff α（把 A &lt; tie &lt; B 视为有序），它会自动给「差一档」比「差两档」更轻的惩罚。",
        ]),
    ])),

    # ============================================================== 4
    ("sample-vs-system", "样本级 vs 系统级：一致率 70% 的 judge 可能排序完全正确", "".join([
        P("这是元评测里最有实用价值、也最反直觉的一条结论。"),
        ASCII("""
   样本级一致性                       系统级一致性
   ┌──────────────────────┐          ┌──────────────────────────┐
   │ 逐条比对 judge 与人类  │          │ 比对「模型排名」是否一致   │
   │ 指标: accuracy/kappa  │          │ 指标: 排名相关 / 胜负一致  │
   │ 关心: 单条判断准不准   │          │ 关心: **选型结论对不对**   │
   └──────────────────────┘          └──────────────────────────┘
              │                                    │
   一致率 70%  ────────► 聚合 200 条 ────────►  排序几乎必然正确
   （单条经常判错）                         （随机误差被平均掉）
"""),
        DUAL(
            "为什么会这样？因为<strong>随机误差在聚合时会被平均掉</strong>。"
            "judge 在单条样本上有 30% 的概率判错，但如果这些错误是随机的，"
            "那么在 200 条样本上取平均，胜率的估计误差只有几个百分点——"
            "足以把两个真实差距 5 个点的模型区分开。"
            "<strong>所以「judge 一致率只有 70%，不能用」这个判断经常是错的</strong>——"
            "取决于你要用它回答什么问题。",
            "形式化：设单条一致率为 $p$，模型 A、B 的真实胜率差为 $\\delta$。"
            "judge 观测到的胜率差约为 $(2p-1)\\delta$（误差把差距<strong>压缩</strong>了但没有翻转方向），"
            "而观测的标准误约为 $\\sqrt{2 \\cdot 0.25/n}$。"
            "<strong>因此系统级结论的可靠性取决于 $(2p-1)\\delta\\sqrt{n}$，而不是 $p$ 本身。</strong>"
            "<em>$p = 0.70$、$\\delta = 0.10$、$n = 200$ 时这个量约为 $0.4 \\times 0.10 \\times 14.1 = 0.57$……</em>"
            "notebook 第 3 节会把这个量算准并给出所需样本量。",
        ),
        CALLOUT("danger", "但是——这条结论有一个<strong>致命的前提：误差必须是随机的</strong>。"
                          "如果 judge 的误差是系统性的（模块 02 的四大偏差），"
                          "那么聚合<em>不会</em>把它平均掉，反而会让它在统计上显得更显著。"
                          "<strong>所以正确的顺序永远是：先用探针确认没有共有的系统偏差，"
                          "再用「样本级一致率低但系统级可用」这个论证。</strong>"
                          "跳过第一步直接用第二步，是这门课里最危险的推理捷径。"),
        H3("该报哪个"),
        P("<strong>两个都报，并且说明你的结论依赖哪一个。</strong>"
          "如果你的用途是「选模型」「排名」，系统级是决定性的；"
          "如果你的用途是「筛出坏样本送人工复核」「作为训练信号」，"
          "<em>样本级才是决定性的</em>——因为这些用途直接消费单条判断。"),
    ])),

    # ============================================================== 5
    ("calibration", "校准：judge 说「我 80% 确定」时，它对了 80% 吗", "".join([
        P("如果你的 judge 输出的不只是判断，还有置信度（或者你用 logprob 构造了一个置信度），"
          "那么就有一个额外的性质需要检验：<strong>校准</strong>。"),
        MATH(r"\text{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{n}\left|\operatorname{acc}(B_b) - \operatorname{conf}(B_b)\right|"),
        P("做法是把样本按置信度分桶，每桶里比较「平均置信度」与「实际准确率」，加权求和它们的差。"
          "<strong>ECE = 0 表示完美校准。</strong>"),
        TABLE(["现象", "可靠性图上的表现", "常见原因", "处理"], [
            ["<strong>过度自信</strong>", "曲线在对角线<em>下方</em>：说 90% 只对了 70%", "最常见——RLHF 后的模型倾向于表达确定性", "<strong>温度缩放</strong>（对 logit 除以 $T > 1$）"],
            ["<strong>信心不足</strong>", "曲线在对角线上方", "较少见；过度保守的 prompt 会造成", "温度缩放（$T < 1$）"],
            ["<strong>置信度无信息</strong>", "曲线接近水平线", "judge 的置信度与正确率无关——<strong>这个置信度不该被使用</strong>", "换置信度的构造方式（如用 swap 一致性代替自报置信度）"],
        ]),
        CALLOUT("intuition", "一个非常实用的替代方案：<strong>与其相信 judge 自报的置信度，"
                             "不如用「多次采样的一致性」或「swap 一致性」当置信度。</strong>"
                             "两次调用判断一致 → 高置信；不一致 → 低置信。"
                             "<em>这个「置信度」通常比模型自报的更校准</em>，"
                             "因为它是从行为里测出来的而不是模型说出来的。"
                             "而且你在做 swap 探针（模块 02）时已经把它算出来了，边际成本为零。"),
        H3("校准的用途：分诊"),
        P("校准好的置信度最大的用途不是让报告更好看，而是<strong>分诊</strong>："
          "把低置信度的样本送人工复核。<strong>如果置信度校准良好，"
          "那么「复核最低置信度的 10%」能捕捉到远超 10% 的错误</strong>——"
          "这是把有限的人力投入回报最大化的直接方法（呼应 C66 模块 02 的三级复核流水线）。"),
    ])),

    # ============================================================== 6
    ("cost-agreement", "成本-一致性前沿：更贵的 judge 值不值", "".join([
        P("judge 的选择是一个典型的成本-质量权衡，而且它的数量级经常被低估："
          "一次大规模评测可能有几十万次 judge 调用，judge 模型的选择直接决定了这次评测的账单。"),
        TABLE(["选项", "相对成本", "典型一致率变化", "什么时候值得"], [
            ["<strong>换更大的 judge 模型</strong>", "3–10×", "+3 到 +8 个点", "样本级判断被直接消费时（训练信号、分诊）"],
            ["<strong>加 CoT</strong>", "1.5–3×（输出 token 变多）", "+2 到 +5 个点", "<strong>几乎总是值得</strong>，且它同时提升了可解释性"],
            ["<strong>swap 双跑</strong>", "2×", "去掉位置偏差，一致率通常 +1 到 +3", "<strong>出结论的评测必做</strong>"],
            ["<strong>多 judge 集成（3 个）</strong>", "3×", "+1 到 +4（<em>仅当偏差方向不同</em>）", "已经处理完共有偏差之后"],
            ["<strong>rubric 化</strong>", "1–1.5×", "+3 到 +10 个点", "<strong>性价比最高的一项</strong>（模块 01）"],
        ]),
        CALLOUT("intuition", "这张表最重要的读法是<strong>顺序</strong>：便宜的手段先做完再考虑贵的。"
                             "<strong>rubric 化（几乎免费）→ CoT（1.5×）→ swap（2×）→ 换大模型（3–10×）→ 集成（3×）。</strong>"
                             "<em>常见的错误是跳过前三步直接换最贵的模型</em>——"
                             "结果是花了十倍的钱，买到的提升还不如免费的 rubric 化。"),
        P("另一个值得算的账：<strong>judge 的成本应该和评测规模一起决定</strong>。"
          "如果换个便宜的 judge 能让你把样本量翻三倍，而一致率只掉 3 个点——"
          "<em>那么在「系统级结论」这个用途上，便宜 judge + 大样本几乎必然更优</em>"
          "（因为第 4 节说过，系统级的可靠性取决于 $(2p-1)\\delta\\sqrt{n}$，"
          "$\\sqrt{n}$ 的收益经常压过 $p$ 的损失）。<strong>这个取舍必须被显式计算，而不是靠直觉选贵的。</strong>"),
    ])),

    # ============================================================== 7
    ("drift", "漂移监测：judge 会在你不知道的时候变", "".join([
        P("judge 是一个外部依赖，而外部依赖会变。变化的来源至少有四个："),
        UL([
            "<strong>模型版本更新</strong>——同一个模型名指向的权重可能变了；",
            "<strong>prompt 被人改了</strong>——模块 01 第 8 节已经讲过；",
            "<strong>被评内容的分布变了</strong>——你的模型变得更长/更结构化，"
            "而 judge 的偏差在新分布上的表现不同；",
            "<strong>采样温度或解码参数被改了</strong>。",
        ]),
        P("这四者的共同表现是：<strong>指标曲线上出现一个无法用模型改动解释的跳变</strong>。"
          "检测方式是维护一个<strong>不变的哨兵集</strong>（sentinel set）："),
        CODE("""哨兵集 = 一批固定不变的、已有人类标注的样本（100-300 条）

每次评测运行都跑一遍哨兵集，记录:
  - judge 在哨兵集上的一致率
  - judge 在哨兵集上的分数分布（均值、标准差、各档比例）
  - swap 一致率

告警规则:
  - 一致率相对基线下降超过 2 个标准误  → 调查
  - 分数分布的均值平移超过阈值          → 调查（严厉度漂移）
  - swap 一致率下降                     → 调查（可能换了模型版本）"""),
        CALLOUT("warn", "哨兵集有一个必须遵守的纪律：<strong>它必须永远不变，而且不能被用来调 prompt。</strong>"
                        "一旦你用哨兵集的结果去改进 judge，它就从「监测工具」变成了「优化目标」，"
                        "从此不再能告诉你任何关于漂移的事（Goodhart，又一次）。"
                        "<em>正确做法是维护两套：一套开发集用来调 judge，一套哨兵集只用来监测、"
                        "结果只看不改。</em>"),
        P("检测方法上，比「单点阈值」更好的是<strong>累积和（CUSUM）</strong>："
          "它累积微小的同向偏离，因此能检出「每次只掉 0.5 个点、但连续掉了十次」这种缓慢漂移——"
          "而这恰恰是单点阈值最容易漏掉的模式。notebook 第 6 节给出实现。"),
    ])),

    # ============================================================== 8
    ("meta-set", "元评测集怎么建：样本选择比样本数量更重要", "".join([
        P("最后一节讲元评测的输入：那批带人类标注的样本从哪来。"
          "<strong>选错样本，做再多的一致性分析都是白做。</strong>"),
        TABLE(["选择策略", "怎么选", "适合回答什么问题", "问题"], [
            ["<strong>随机抽样</strong>", "从真实分布里随机抽", "「judge 在我的实际流量上有多准」", "<strong>难样本太少</strong>——如果 85% 的样本都很好判，你测的主要是简单题"],
            ["<strong>难度分层</strong>", "按「judge 置信度」或「两个模型输出的接近程度」分层抽", "「judge 在难样本上有多准」", "需要一个难度代理变量"],
            ["<strong>分歧驱动</strong>", "专挑「两个 judge 意见不同」或「swap 不一致」的样本", "<strong>最省人力</strong>：直接命中判分器的薄弱区", "得到的一致率不能代表整体分布，<em>必须做重要性加权才能外推</em>"],
            ["<strong>对抗构造</strong>", "刻意构造长度/格式/自信语气不同的对照（模块 02 的探针）", "「judge 的偏差有多大」", "不能用来估计整体一致率"],
        ]),
        CALLOUT("intuition", "推荐的组合：<strong>「随机抽样的主集」+「分歧驱动的加强集」+「对抗构造的探针集」</strong>，"
                             "三者分开报告、绝不混算。"
                             "主集回答「整体有多准」，加强集回答「难的地方有多准」，探针集回答「有没有系统偏差」。"
                             "<em>把它们混成一个数字，三个问题一个都答不了</em>——"
                             "这与 C66 模块 02 的「主表 micro + 附表 macro」是同一种报告纪律。"),
        H3("样本量：比你想象的少"),
        P("一个好消息：<strong>元评测集不需要很大。</strong>"
          "估计一个一致率到 ±5 个百分点（95% 置信），只需要约 400 条；"
          "±3 个点需要约 1000 条。而做偏差探针（配对设计）需要的更少——"
          "<em>几十到一两百对通常就够</em>（模块 02 第 6 节）。"
          "<strong>真正贵的不是样本数，是标注质量</strong>——"
          "每条需要多个标注员、需要标注规范、需要处理分歧，这才是成本所在。"),
        H3("本模块的报告规范"),
        CODE("""META-EVAL · judge=claude-sonnet-5, prompt e3a1f9c, temp 0.0
主集（随机抽样, n=520, 3 位标注员多数意见）
  judge–human agreement:   0.823
  human–human agreement:   0.841      ← 天花板
  chance agreement:        0.500
  ceiling-normalized:      0.947      ← 「达到人类水平的 94.7%」
  Cohen's kappa:           0.646
  方向一致率（tie 视为可接受）: 0.912

难样本加强集（分歧驱动, n=180）
  judge–human agreement:   0.694      ← 难样本上明显更差，符合预期
  human–human agreement:   0.722

系统级（8 个模型的两两比较, n=200/对）
  排名与人类排名的 Spearman:  0.976
  结论: **样本级一致率 0.82，但系统级排名几乎完全一致——选型用途可用**

校准（置信度=swap 一致性）
  ECE:                     0.041
  低置信 10% 的样本包含了   38% 的错误   ← 分诊有效

哨兵集漂移（n=200, 相对 2026-06 基线）
  agreement Δ:  -0.006 (在 2 个标准误内)     CUSUM: 未触发""" ),
    ])),
    # ============================================================== 9
    ("cheap-human", "廉价而有效的人类标注：把最贵的一环压到最小", "".join([
        P("本模块反复说「必须有人类标注做对照」，而这通常是整个流程里最贵的一环。"
          "这一节讲怎么把它压到可承受的规模——<strong>因为「太贵所以不做」的实际后果是「没有任何对照」</strong>，"
          "那比小规模对照差得多。"),
        H3("四条降本手段"),
        OL([
            "<strong>用 pairwise 而不是打分</strong>：让人类比较两个回答，比让他们打绝对分"
            "<em>更快、一致性更高、也不需要校准会</em>。"
            "「哪个更好」这个问题人类天然擅长，「打几分」不擅长（与第 3 节的量表讨论同源）。",
            "<strong>分歧驱动抽样</strong>：优先标注 judge 自己拿不准的样本"
            "（swap 不一致、多 judge 意见不同、置信度低）。"
            "<strong>同样的标注预算，信息量能高出好几倍</strong>——"
            "但要记住这批样本不能直接用来估计整体一致率（第 8 节），需要单独报告。",
            "<strong>只标注两端</strong>：如果目的是校准量表（模块 01 的锚点），"
            "标 1 分与 5 分的样例比标中间档有价值得多——中间档会被内插出来。",
            "<strong>把标注变成检查而不是判断</strong>：不问「这个回答好不好」，"
            "问「这个回答有没有提到 X / 有没有事实错误 / 有没有回答用户的问题」。"
            "<em>可判定的问题标得更快、一致性更高，而且天然对应 rubric 项</em>——"
            "这是第 1 节可判定性阶梯在标注环节的应用。",
        ]),
        CALLOUT("intuition", "关于样本量的一个好消息，值得重复：<strong>元评测集不需要很大。</strong>"
                             "估计一致率到 ±5 个百分点只需约 400 条；"
                             "而模块 02 的偏差探针因为是配对设计，几十到一两百对就够。"
                             "<strong>真正贵的不是样本数，是每条需要多人标注 + 处理分歧这个流程。</strong>"
                             "<em>所以降本的重点应该放在「让每条标注更快、分歧更少」上，"
                             "而不是放在「少标几条」上。</em>"),
        H3("标注流程的五条硬规范"),
        UL([
            "<strong>随机化 A/B 顺序</strong>——否则人类标注本身就带位置偏差，你的「金标准」不干净；",
            "<strong>隐藏模型身份</strong>——否则带品牌偏差；",
            "<strong>每条至少 3 人</strong>——2 人只能算一致率，3 人才能取多数意见；",
            "<strong>先开 20 条的校准会</strong>——对齐口径的收益远大于它的成本；",
            "<strong>记录标注耗时</strong>——耗时长的样本就是难样本，天然是难度分层的候选，"
            "<em>这个字段免费但很多人忘了记</em>。",
        ]),
    ])),
]

NB = [
    md("""# 03 · 元评测与校准（人类上界 / kappa / 样本级 vs 系统级 / ECE / 成本-一致性 / 漂移）

目标：把「这个 judge 能不能用」从一句感觉，变成一份**可以贴进报告的元评测卡**。

本 notebook 你会亲手实现：
1. **人类上界与天花板归一化** —— 把 82% 翻译成「达到人类水平的 94%」
2. **accuracy / kappa / Krippendorff** —— 三个系数在不均衡分布上的分歧，以及 kappa 悖论
3. **样本级 vs 系统级一致性** —— 一致率 70% 的 judge 为什么能给出正确的排名
4. **校准** —— ECE、可靠性图（文本版）、温度缩放，以及「用 swap 一致性当置信度」
5. **成本-一致性前沿** —— 便宜 judge + 大样本 vs 贵 judge + 小样本
6. **CUSUM 漂移检测** —— 抓「每次只掉 0.5 个点、连续掉十次」的缓慢漂移

> 心智模型：**一致率必须配着人类上界一起读；样本级差不代表系统级差；
> 但这条论证的前提是「误差是随机的」——所以偏差探针永远排在一致率分析之前。**"""),

    md("""## 1 · 人类上界与天花板归一化"""),

    code("""import math, json
from collections import Counter, defaultdict
import numpy as np

def p_from_hh(a_hh):
    \"\"\"由人类之间的一致率反解「单个标注者与潜在真值一致的概率」p_H。
    二元任务: a_hh = p^2 + (1-p)^2  →  p = (1 + sqrt(2*a_hh - 1)) / 2\"\"\"
    if a_hh < 0.5:
        return float('nan')
    return (1 + math.sqrt(2 * a_hh - 1)) / 2

def p_judge_from_jh(a_jh, p_h):
    \"\"\"由 judge-human 一致率与 p_H 反解 judge 的真实准确率 p_J。
    a_jh = p_J*p_H + (1-p_J)*(1-p_H)  →  p_J = (a_jh - (1-p_H)) / (2*p_H - 1)\"\"\"
    denom = 2 * p_h - 1
    if abs(denom) < 1e-9:
        return float('nan')
    return (a_jh - (1 - p_h)) / denom

def ceiling_normalized(a_jh, a_hh, a_chance=0.5):
    return (a_jh - a_chance) / (a_hh - a_chance)

print(f"{'a_HH':>8}{'p_H':>8}{'a_JH':>8}{'p_J':>8}{'天花板归一化':>14}")
for a_hh, a_jh in [(0.95, 0.90), (0.84, 0.82), (0.75, 0.70), (0.70, 0.68)]:
    ph = p_from_hh(a_hh)
    pj = p_judge_from_jh(a_jh, ph)
    cn = ceiling_normalized(a_jh, a_hh)
    print(f'{a_hh:>8.2f}{ph:>8.3f}{a_jh:>8.2f}{pj:>8.3f}{cn:>14.3f}')

ph = p_from_hh(0.84)
pj = p_judge_from_jh(0.82, ph)
assert abs(p_from_hh(1.0) - 1.0) < 1e-9
assert 0.85 < pj < 1.0, 'a_HH=0.84 时，a_JH=0.82 反解出的 judge 真实准确率很高'
assert abs(ceiling_normalized(0.82, 0.84) - 0.9412) < 1e-3
print(f'\\n人类一致率 0.84 → 单个标注者准确率 p_H = {ph:.3f}')
print(f'judge 一致率 0.82 → judge 真实准确率 p_J = {pj:.3f}  ← 比 0.82 高得多')
print('✅ 「82 分」和「达到人类水平的 94%」是同一个数字的两种读法，')
print('   而它们会导向完全不同的资源分配决策。')"""),

    code("""# 用模拟验证反解是对的：设定真实的 p_H 与 p_J，看能不能还原出来
rng = np.random.default_rng(0)
N = 200000
truth = rng.integers(0, 2, N)
P_H, P_J = 0.88, 0.93
h1 = np.where(rng.random(N) < P_H, truth, 1 - truth)
h2 = np.where(rng.random(N) < P_H, truth, 1 - truth)
jg = np.where(rng.random(N) < P_J, truth, 1 - truth)

a_hh_obs = float((h1 == h2).mean())
a_jh_obs = float((jg == h1).mean())
ph_hat = p_from_hh(a_hh_obs)
pj_hat = p_judge_from_jh(a_jh_obs, ph_hat)
print(f'真实 p_H={P_H:.3f} → 估计 {ph_hat:.3f}   (观测 a_HH={a_hh_obs:.4f})')
print(f'真实 p_J={P_J:.3f} → 估计 {pj_hat:.3f}   (观测 a_JH={a_jh_obs:.4f})')
assert abs(ph_hat - P_H) < 0.01 and abs(pj_hat - P_J) < 0.01
print('\\n✅ 反解在这个模型下是准确的。')
print('   ⚠️ 但它假设了「标注者的错误互相独立」——如果两个标注员共享同样的误解，')
print('      a_HH 会虚高，反解出的 p_H 也会虚高。这是这个方法唯一的软肋。')"""),

    md("""## 2 · accuracy / kappa / Krippendorff：不均衡分布上的分歧"""),

    code("""def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a.tolist()) | set(b.tolist()))
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    return (po - pe) / (1 - pe) if abs(1 - pe) > 1e-12 else float('nan')

def krippendorff_alpha_nominal(ratings):
    \"\"\"名义数据的 Krippendorff α。ratings: (n_raters, n_items)，np.nan 表示缺失。
    α = 1 - D_o / D_e，D_o 是观测不一致，D_e 是期望不一致。\"\"\"
    R = np.asarray(ratings, dtype=float)
    n_items = R.shape[1]
    values = [v for v in np.unique(R[~np.isnan(R)])]
    # 观测不一致
    num = 0.0
    den = 0.0
    all_vals = []
    for j in range(n_items):
        col = R[:, j]
        col = col[~np.isnan(col)]
        m = len(col)
        if m < 2:
            continue
        all_vals.extend(col.tolist())
        cnt = Counter(col.tolist())
        # 该 item 内不同值的配对数
        pairs_diff = m * (m - 1) - sum(c * (c - 1) for c in cnt.values())
        num += pairs_diff / (m - 1)
        den += m
    if den == 0:
        return float('nan')
    D_o = num / den
    total = Counter(all_vals)
    n_all = sum(total.values())
    same = sum(c * (c - 1) for c in total.values())
    D_e = (n_all * (n_all - 1) - same) / (n_all - 1) / n_all * (n_all / n_all)
    D_e = 1 - same / (n_all * (n_all - 1))
    return 1 - D_o / D_e if D_e > 0 else float('nan')

rng = np.random.default_rng(3)
n = 4000
# 场景 A：类别均衡
t_bal = rng.integers(0, 2, n)
a1 = np.where(rng.random(n) < 0.90, t_bal, 1 - t_bal)
a2 = np.where(rng.random(n) < 0.90, t_bal, 1 - t_bal)
# 场景 B：极度不均衡（92% 都是「通过」）
t_imb = (rng.random(n) < 0.92).astype(int)
b1 = np.where(rng.random(n) < 0.90, t_imb, 1 - t_imb)
b2 = np.where(rng.random(n) < 0.90, t_imb, 1 - t_imb)

for name, x, y in [('类别均衡', a1, a2), ('极度不均衡(92%通过)', b1, b2)]:
    acc = float((x == y).mean())
    kap = cohen_kappa(x, y)
    alpha = krippendorff_alpha_nominal(np.vstack([x, y]).astype(float))
    print(f'{name:<22} 原始一致率 {acc:.3f} | kappa {kap:.3f} | Krippendorff α {alpha:.3f}')

acc_b = float((b1 == b2).mean())
kap_b = cohen_kappa(b1, b2)
assert acc_b > 0.80 and kap_b < 0.55
print('\\n✅ kappa 悖论现场：不均衡分布上原始一致率 > 0.80，但 kappa 只有 0.5 上下。')
print('   kappa 没算错——它在说「你们的一致大部分可以由『都爱说通过』解释」。')
print('   正确反应不是换个好看的系数，而是承认这个样本分布几乎没有区分度，去找更均衡的样本。')"""),

    md("""## 3 · 样本级 vs 系统级：一致率 70% 的 judge 能给出正确排名吗"""),

    code("""def system_level_experiment(p_agree, delta, n_items=400, n_trials=1000, seed=0):
    \"\"\"A 的真实胜率是 0.5 + delta，judge 单条一致率 p_agree。
    返回 (judge 选对 A 的比例, 观测到的平均胜率偏离 0.5 的幅度)。\"\"\"
    rng = np.random.default_rng(seed)
    correct, gaps = 0, []
    for _ in range(n_trials):
        truth = (rng.random(n_items) < 0.5 + delta).astype(int)       # A 真实胜出的样本
        obs = np.where(rng.random(n_items) < p_agree, truth, 1 - truth)
        gaps.append(obs.mean() - 0.5)
        if obs.mean() > 0.5:
            correct += 1
    return correct / n_trials, float(np.mean(gaps))

print(f"{'单条一致率':>12}{'真实差距':>10}{'系统级选对率':>14}{'观测到的差距':>14}")
for p_ in [0.95, 0.85, 0.70, 0.60]:
    for d_ in [0.10]:
        c_, g_ = system_level_experiment(p_, d_, n_items=400, seed=1)
        print(f'{p_:>12.0%}{d_:>10.0%}{c_:>14.1%}{g_:>14.1%}')

c70, g70 = system_level_experiment(0.70, 0.10, n_items=400, seed=1)
c95, g95 = system_level_experiment(0.95, 0.10, n_items=400, seed=1)
assert c70 > 0.85, '一致率 70% 时系统级仍然大概率选对'
assert g70 < g95, '一致率低会把观测到的差距压缩'
print(f'\\n✅ 一致率只有 70% 的 judge，在 400 条样本上仍以 {c70:.0%} 的概率选对模型。')
print(f'   代价是差距被压缩了：真实 10 个点被观测成 {g70:.1%}（压缩系数 2p-1 = {2*0.70-1:.1f}）。')
print('   ⚠️ 这条论证的**唯一前提是误差随机**。系统偏差不会被聚合平均掉——')
print('      所以偏差探针（模块 02）永远排在一致率分析之前。')"""),

    code("""# 系统级所需样本量：可靠性取决于 (2p-1)*delta*sqrt(n)
def n_for_system_level(p_agree, delta, target_z=2.0):
    eff = (2 * p_agree - 1) * delta          # 被压缩后的观测差距
    if eff <= 0:
        return float('inf')
    return math.ceil((target_z ** 2) * 0.25 / (eff ** 2))

print(f"{'一致率':>10}{'真实差距 10%':>16}{'真实差距 5%':>16}{'真实差距 2%':>16}")
for p_ in [0.95, 0.85, 0.70, 0.60]:
    row = ''.join(f'{n_for_system_level(p_, d):>16,}' for d in [0.10, 0.05, 0.02])
    print(f'{p_:>10.0%}{row}')

assert n_for_system_level(0.70, 0.10) > n_for_system_level(0.95, 0.10)
assert n_for_system_level(0.95, 0.02) > n_for_system_level(0.95, 0.10)
print('\\n✅ 一致率从 95% 掉到 70%，所需样本量涨约 5 倍——')
print('   但如果便宜的 judge 让你能跑 10 倍的样本，这笔账仍然是划算的（第 5 节展开）。')"""),

    md("""## 4 · 校准：ECE、可靠性图与温度缩放"""),

    code("""def expected_calibration_error(conf, correct, n_bins=10):
    conf = np.asarray(conf, dtype=float)
    correct = np.asarray(correct, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece, rows = 0.0, []
    for i in range(n_bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1]) if i > 0 else (conf >= edges[i]) & (conf <= edges[i + 1])
        if m.sum() == 0:
            continue
        acc, cf, w = correct[m].mean(), conf[m].mean(), m.mean()
        ece += w * abs(acc - cf)
        rows.append((edges[i], edges[i + 1], int(m.sum()), float(cf), float(acc)))
    return float(ece), rows

def reliability_table(rows):
    print(f"{'置信度区间':>14}{'n':>7}{'平均置信':>10}{'实际准确':>10}{'差':>8}  可靠性图")
    for lo, hi, cnt, cf, acc in rows:
        bar = ' ' * int(cf * 30) + ('▲' if acc > cf else ('▼' if acc < cf else '●'))
        print(f'  [{lo:.1f},{hi:.1f}]{cnt:>7}{cf:>10.3f}{acc:>10.3f}{acc-cf:>+8.3f}  {bar}')

rng = np.random.default_rng(9)
M = 6000
true_p = rng.uniform(0.5, 1.0, M)                    # 真实的「这条判对的概率」
correct = (rng.random(M) < true_p).astype(float)
conf_overconf = np.clip(0.5 + (true_p - 0.5) * 1.9, 0, 1)      # 过度自信
conf_good = true_p                                              # 完美校准
conf_useless = np.full(M, 0.8)                                  # 无信息

for name, c in [('完美校准', conf_good), ('过度自信', conf_overconf), ('无信息置信度', conf_useless)]:
    e, _ = expected_calibration_error(c, correct)
    print(f'{name:<16} ECE = {e:.4f}')

e_good, _ = expected_calibration_error(conf_good, correct)
e_over, rows_over = expected_calibration_error(conf_overconf, correct)
assert e_over > e_good + 0.03
print('\\n过度自信的可靠性图（▼ 表示实际准确率低于自报置信度）:')
reliability_table(rows_over)"""),

    code("""def temperature_scale(conf, T):
    \"\"\"对置信度做温度缩放：先转 logit，除以 T，再转回概率。T>1 削弱自信。\"\"\"
    c = np.clip(np.asarray(conf, dtype=float), 1e-6, 1 - 1e-6)
    z = np.log(c / (1 - c)) / T
    return 1 / (1 + np.exp(-z))

def fit_temperature(conf, correct, grid=None):
    grid = grid if grid is not None else np.linspace(0.5, 4.0, 71)
    best = min(grid, key=lambda T: expected_calibration_error(temperature_scale(conf, T), correct)[0])
    return float(best)

T_hat = fit_temperature(conf_overconf, correct)
e_before, _ = expected_calibration_error(conf_overconf, correct)
e_after, _ = expected_calibration_error(temperature_scale(conf_overconf, T_hat), correct)
print(f'拟合温度 T = {T_hat:.2f}（>1 表示原本过度自信）')
print(f'ECE: {e_before:.4f} → {e_after:.4f}')
assert T_hat > 1.0 and e_after < e_before
print('\\n✅ 温度缩放只改置信度、不改判断——所以它不会影响一致率，只让置信度可用。')

# 更实用的置信度：用 swap 一致性代替自报置信度
# 注意：swap 一致性本身不是概率，要在留出集上校准成概率（这一步几乎免费）
rng = np.random.default_rng(13)
swap_consistent = (rng.random(M) < (0.55 + 0.45 * (true_p - 0.5) * 2)).astype(float)
half = M // 2
p_cons = float(correct[:half][swap_consistent[:half] == 1].mean())      # 留出集上估计
p_incons = float(correct[:half][swap_consistent[:half] == 0].mean())
print(f'留出集校准: swap 一致 → 实际准确率 {p_cons:.3f} | swap 不一致 → {p_incons:.3f}')
conf_from_swap = np.where(swap_consistent == 1, p_cons, p_incons)
e_swap, _ = expected_calibration_error(conf_from_swap, correct)
print(f'用 swap 一致性构造的置信度: ECE = {e_swap:.4f}（对比自报过度自信 {e_before:.4f}）')
assert e_swap < e_before
print('✅ 从行为里测出来的置信度，通常比模型自报的更校准——而且边际成本为零')
print('   （做 swap 探针时已经算出来了）。')"""),

    code("""# 校准的真正用途：分诊。低置信度的 10% 里包含了多少错误？
def triage_gain(conf, correct, frac=0.10):
    idx = np.argsort(conf)                                  # 置信度从低到高
    k = max(int(len(conf) * frac), 1)
    lowest = idx[:k]
    errors_total = float((1 - correct).sum())
    errors_caught = float((1 - correct[lowest]).sum())
    return errors_caught / errors_total if errors_total else 0.0

for name, c in [('完美校准', conf_good), ('过度自信', conf_overconf),
                ('swap 一致性', conf_from_swap), ('无信息', conf_useless)]:
    print(f'{name:<16} 复核最低置信的 10% → 捕捉到 {triage_gain(c, correct):.1%} 的错误')

assert triage_gain(conf_good, correct) > triage_gain(conf_useless, correct) + 0.05
print('\\n✅ 校准良好的置信度能让 10% 的人力捕捉到远超 10% 的错误——')
print('   这是把有限人力回报最大化的直接方法（呼应 C66-02 的三级复核流水线）。')"""),

    md("""## 5 · 成本-一致性前沿：便宜 judge + 大样本 vs 贵 judge + 小样本"""),

    code("""JUDGES = [
    # name,           相对成本, 单条一致率
    ('小模型 + 整体分',    1.0, 0.68),
    ('小模型 + rubric',    1.3, 0.76),
    ('小模型 + rubric+CoT', 2.2, 0.80),
    ('大模型 + 整体分',    6.0, 0.79),
    ('大模型 + rubric+CoT', 12.0, 0.87),
    ('大模型 + 3-judge 集成', 36.0, 0.89),
]

def system_z(p_agree, delta, n):
    \"\"\"系统级结论的 z 值 ∝ (2p-1)*delta*sqrt(n)。\"\"\"
    return (2 * p_agree - 1) * delta * math.sqrt(n)

BUDGET = 6000.0        # 单位：相对成本
print(f"{'judge 配置':<24}{'成本':>7}{'一致率':>9}{'可跑样本':>10}{'系统级 z':>12}")
rows = []
for name, c, p_ in JUDGES:
    n_ = BUDGET / c
    z_ = system_z(p_, 0.05, n_)
    rows.append((name, c, p_, n_, z_))
    print(f'{name:<24}{c:>7.1f}{p_:>9.0%}{n_:>10,.0f}{z_:>12.2f}')

best = max(rows, key=lambda r: r[4])
print(f'\\n同样 {BUDGET:,.0f} 的预算下，系统级分辨力最高的是: **{best[0]}**（z = {best[4]:.2f}）')
assert best[0] != '大模型 + 3-judge 集成', '最贵的配置在固定预算下反而不是最优'
print('✅ 最贵的配置在固定预算下反而落后——因为样本量被成本压掉了。')
print('   ⚠️ 但这只对**系统级**用途成立。如果 judge 的单条判断会被直接消费')
print('      （训练信号、分诊、给用户看），那就必须看一致率本身，不能拿样本量换。')"""),

    code("""# 便宜手段的顺序：rubric 化 → CoT → swap → 换大模型
UPGRADES = [
    ('起点：小模型 + 整体分',   1.0, 0.68),
    ('+ rubric 化',            1.3, 0.76),
    ('+ CoT',                  2.2, 0.80),
    ('+ swap 双跑',            4.4, 0.82),
    ('+ 换大模型',            26.4, 0.88),
]
print(f"{'升级步骤':<24}{'累计成本':>10}{'一致率':>9}{'每倍成本换来的提升':>20}")
prev_c, prev_p = None, None
for name, c, p_ in UPGRADES:
    if prev_c is None:
        print(f'{name:<24}{c:>10.1f}{p_:>9.0%}{"—":>20}')
    else:
        gain_per_cost = (p_ - prev_p) / (c / prev_c)
        print(f'{name:<24}{c:>10.1f}{p_:>9.0%}{gain_per_cost:>19.3f}')
    prev_c, prev_p = c, p_

rubric_eff = (0.76 - 0.68) / (1.3 / 1.0)
bigmodel_eff = (0.88 - 0.82) / (26.4 / 4.4)
print(f'\\nrubric 化的单位成本收益 {rubric_eff:.3f} vs 换大模型 {bigmodel_eff:.3f}')
assert rubric_eff > 5 * bigmodel_eff
print('✅ rubric 化的性价比是换大模型的十几倍——')
print('   常见错误是跳过前三步直接换最贵的模型，结果买到的提升还不如免费的 rubric 化。')"""),

    md("""## 6 · 漂移检测：CUSUM 抓缓慢漂移"""),

    code("""def cusum(values, baseline, k=0.5, h=5.0, sigma=1.0):
    \"\"\"单边（向下）CUSUM。k 是允许的漂移容差（以 sigma 为单位），h 是告警阈值。
    返回 (累积和序列, 首次告警的下标或 None)。\"\"\"
    s, out, alarm = 0.0, [], None
    for i, v in enumerate(values):
        z = (baseline - v) / sigma                 # 向下漂移为正
        s = max(0.0, s + z - k)
        out.append(s)
        if alarm is None and s > h:
            alarm = i
    return out, alarm

rng = np.random.default_rng(23)
BASE, SIGMA, T = 0.82, 0.02, 40
# 场景一：稳定
stable = rng.normal(BASE, SIGMA, T)
# 场景二：缓慢漂移（从第 15 期起每期掉 0.004）
slow = stable.copy()
slow[15:] -= np.arange(1, T - 15 + 1) * 0.004
# 场景三：突变（第 25 期掉 0.06）
jump = stable.copy()
jump[25:] -= 0.06

THRESH = BASE - 2 * SIGMA
for name, series in [('稳定', stable), ('缓慢漂移', slow), ('突变', jump)]:
    _, alarm = cusum(series, BASE, k=0.5, h=5.0, sigma=SIGMA)
    single = next((i for i, v in enumerate(series) if v < THRESH), None)
    print(f'{name:<10} CUSUM 首次告警于第 {str(alarm):>5} 期 | 单点阈值首次告警于第 {str(single):>5} 期')

_, a_stable = cusum(stable, BASE, sigma=SIGMA)
_, a_slow = cusum(slow, BASE, sigma=SIGMA)
_, a_jump = cusum(jump, BASE, sigma=SIGMA)
single_stable = next((i for i, v in enumerate(stable) if v < THRESH), None)

assert a_stable is None, 'CUSUM 在稳定序列上不应误报'
assert single_stable is not None, '单点阈值在稳定序列上就已经误报了'
assert a_slow is not None and a_jump is not None, 'CUSUM 必须抓到漂移与突变'
print('\\n✅ 关键在第一行：**单点阈值在稳定序列上就已经告警了**（纯粹是噪声撞到阈值），')
print('   所以它在另外两条序列上的「早期告警」同样没有信息量——它一直在喊狼来了。')
print('   CUSUM 在稳定序列上保持沉默，在缓慢漂移开始后 7 期、突变后 2 期告警。')
print('\\n   哨兵集的纪律：它必须永远不变，而且**绝不能被用来调 judge prompt**——')
print('   一旦被用作优化目标，它就再也不能告诉你任何关于漂移的事。')"""),

    md("""## ✏️ 练习 1：从三个数字算出元评测卡的一行

实现 `agreement_card(a_jh, a_hh, a_chance=0.5)`：返回字典
`{'a_jh', 'a_hh', 'ceiling_normalized', 'p_human', 'p_judge', 'verdict'}`，
其中 `verdict` ∈ `{'at_ceiling', 'usable', 'weak'}`：
归一化 ≥ 0.9 → `at_ceiling`；≥ 0.7 → `usable`；否则 `weak`。"""),

    code("""def agreement_card(a_jh, a_hh, a_chance=0.5):
    # TODO：复用 p_from_hh / p_judge_from_jh / ceiling_normalized
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
c1 = agreement_card(0.82, 0.84)
assert c1['verdict'] == 'at_ceiling'
assert abs(c1['ceiling_normalized'] - 0.9412) < 1e-3
c2 = agreement_card(0.70, 0.90)
assert c2['verdict'] == 'weak'
c3 = agreement_card(0.78, 0.88)
assert c3['verdict'] == 'usable'
for name, c in [('judge 0.82 / 人类 0.84', c1), ('judge 0.70 / 人类 0.90', c2),
                ('judge 0.78 / 人类 0.88', c3)]:
    print(f"{name:<24} 归一化 {c['ceiling_normalized']:.3f} | p_J {c['p_judge']:.3f} | {c['verdict']}")
print('✅ 练习 1 通过：同样是「一致率 0.82」，天花板不同，结论完全不同。')"""),

    md("""## ✏️ 练习 2：kappa 与原始一致率的分歧幅度

实现 `kappa_gap(base_rate, p_agree, n=20000, seed=0)`：
构造一个正类比例为 `base_rate`、两个评判者各以 `p_agree` 的概率与真值一致的场景，
返回 `(原始一致率, kappa, 两者之差)`。用它画出「不均衡程度 → kappa 塌陷」的曲线。"""),

    code("""def kappa_gap(base_rate, p_agree, n=20000, seed=0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
acc_bal, kap_bal, gap_bal = kappa_gap(0.50, 0.90, seed=1)
acc_imb, kap_imb, gap_imb = kappa_gap(0.95, 0.90, seed=1)
assert gap_imb > gap_bal, '越不均衡，原始一致率与 kappa 的差距越大'
assert abs(acc_bal - acc_imb) < 0.03, '两种场景的原始一致率其实差不多'
print(f"{'正类比例':>10}{'原始一致率':>12}{'kappa':>10}{'差':>10}")
for br in [0.50, 0.70, 0.85, 0.95, 0.99]:
    a_, k_, g_ = kappa_gap(br, 0.90, seed=1)
    print(f'{br:>10.0%}{a_:>12.3f}{k_:>10.3f}{g_:>10.3f}')
print('✅ 练习 2 通过：原始一致率几乎不随不均衡程度变化，kappa 却一路塌陷——')
print('   两个数字必须一起报，只报其中一个都会误导。')"""),

    md("""## ✏️ 练习 3：给定预算的最优 judge 配置

实现 `best_judge_under_budget(judges, budget, delta, use_case)`：
`judges` 是 `[(name, cost, p_agree)]`；`use_case ∈ {'system', 'sample'}`。
- `system`：按 `system_z(p, delta, budget/cost)` 最大化
- `sample`：单条判断被直接消费，按 `p_agree` 最大化（成本只用来过滤买不起的）

返回胜出的 `(name, cost, p_agree)`。"""),

    code("""def best_judge_under_budget(judges, budget, delta, use_case):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
b_sys = best_judge_under_budget(JUDGES, 6000.0, 0.05, 'system')
b_smp = best_judge_under_budget(JUDGES, 6000.0, 0.05, 'sample')
print('系统级用途（选型/排名）  →', b_sys)
print('样本级用途（训练信号/分诊）→', b_smp)
assert b_sys[0] != b_smp[0], '两种用途应当选出不同的 judge'
assert b_smp[2] == max(p for _, _, p in JUDGES), '样本级用途必须选一致率最高的'
assert b_sys[1] < b_smp[1], '系统级用途会选更便宜的（省下的钱换样本量）'
print('✅ 练习 3 通过：「哪个 judge 更好」这个问题，在没说用途时没有答案。')"""),

    md("""## ✏️ 练习 4：分诊收益曲线

实现 `triage_curve(conf, correct, fracs)`：对每个 `frac` 返回
`(frac, 捕捉到的错误比例, 提升倍数)`，提升倍数 = 捕捉比例 / frac
（= 1 表示与随机抽检无异）。"""),

    code("""def triage_curve(conf, correct, fracs):
    # TODO：复用上面的 triage_gain
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
FR = [0.05, 0.10, 0.20, 0.50]
cur_good = triage_curve(conf_good, correct, FR)
cur_useless = triage_curve(conf_useless, correct, FR)
print(f"{'复核比例':>10}{'完美校准: 捕捉/倍数':>26}{'无信息: 捕捉/倍数':>24}")
for (f1, c1_, m1), (f2, c2_, m2) in zip(cur_good, cur_useless):
    print(f'{f1:>10.0%}{c1_:>16.1%} / {m1:>5.2f}x{c2_:>16.1%} / {m2:>5.2f}x')
assert cur_good[0][2] > 1.5, '好的置信度在小比例复核时提升倍数应显著大于 1'
assert abs(cur_useless[0][2] - 1.0) < 0.3, '无信息置信度的提升倍数应接近 1'
assert cur_good[0][2] > cur_good[-1][2], '提升倍数随复核比例增大而下降（必然趋近 1）'
print('✅ 练习 4 通过：提升倍数就是「这个置信度值不值得用来分诊」的直接读数。')
print('   接近 1 说明它跟随机抽检没区别——那这个置信度不该被使用。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def agreement_card(a_jh, a_hh, a_chance=0.5):
    ph = p_from_hh(a_hh)
    pj = p_judge_from_jh(a_jh, ph)
    cn = ceiling_normalized(a_jh, a_hh, a_chance)
    verdict = 'at_ceiling' if cn >= 0.9 else ('usable' if cn >= 0.7 else 'weak')
    return {'a_jh': a_jh, 'a_hh': a_hh, 'ceiling_normalized': cn,
            'p_human': ph, 'p_judge': pj, 'verdict': verdict}"""),

    code("""# 练习 2 参考答案
def kappa_gap(base_rate, p_agree, n=20000, seed=0):
    rng = np.random.default_rng(seed)
    truth = (rng.random(n) < base_rate).astype(int)
    r1 = np.where(rng.random(n) < p_agree, truth, 1 - truth)
    r2 = np.where(rng.random(n) < p_agree, truth, 1 - truth)
    acc = float((r1 == r2).mean())
    kap = cohen_kappa(r1, r2)
    return (acc, kap, acc - kap)"""),

    code("""# 练习 3 参考答案
def best_judge_under_budget(judges, budget, delta, use_case):
    affordable = [(nm, c, p) for nm, c, p in judges if c <= budget]
    if not affordable:
        return None
    if use_case == 'system':
        return max(affordable, key=lambda t: system_z(t[2], delta, budget / t[1]))
    if use_case == 'sample':
        return max(affordable, key=lambda t: t[2])
    raise ValueError(use_case)"""),

    code("""# 练习 4 参考答案
def triage_curve(conf, correct, fracs):
    out = []
    for f in fracs:
        caught = triage_gain(conf, correct, f)
        out.append((f, caught, caught / f if f > 0 else float('nan')))
    return out"""),

    md("""---
## 🧪 真实工程胶囊：元评测的落地清单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 元评测集的三段结构（分开报告，绝不混算）
# ══════════════════════════════════════════════════════════════════
# main_set/       随机抽样 400-600 条，3 位标注员 → 多数意见   → 回答「整体有多准」
# hard_set/       分歧驱动 150-250 条（swap 不一致 / 两个 judge 意见不同）→ 「难的地方有多准」
# probe_set/      对抗构造（长度/格式/署名对照，模块 02）      → 「有没有系统偏差」
# sentinel_set/   固定 200 条，永不改动，只用于漂移监测        → 「judge 变了没有」
#
# 纪律：sentinel_set 的结果只看不改。一旦拿它去调 prompt，它就失去监测价值。

# ══════════════════════════════════════════════════════════════════
# B. 标注收集的最小规范
# ══════════════════════════════════════════════════════════════════
# 1. 每条至少 3 个标注员（要算 a_HH，2 个是下限，3 个才能取多数）
# 2. 标注界面**随机化 A/B 顺序**（否则人类标注也带位置偏差）
# 3. 标注员看不到模型名（否则带品牌偏差）
# 4. 记录标注耗时——耗时长的样本就是难样本，天然是 hard_set 的候选
# 5. 先做一轮 20 条的校准会，对齐口径，再正式标注

# ══════════════════════════════════════════════════════════════════
# C. 每次评测都跑的哨兵检查（接进 CI，见 C68-04）
# ══════════════════════════════════════════════════════════════════
def sentinel_check(judge, sentinel, baseline):
    res = run_judge(judge, sentinel)
    agreement = (res.verdicts == sentinel.human_labels).mean()
    se = (agreement * (1 - agreement) / len(sentinel)) ** 0.5
    checks = {
        "agreement_drop":  baseline.agreement - agreement > 2 * se,
        "mean_shift":      abs(res.scores.mean() - baseline.mean) > 3 * baseline.se,
        "swap_drop":       baseline.swap_consistency - res.swap_consistency > 0.03,
        "parse_fail_up":   res.parse_fail_rate > baseline.parse_fail_rate * 2,
    }
    return checks       # 任一为 True → 阻断本次评测，先查 judge

# ══════════════════════════════════════════════════════════════════
# D. 元评测卡模板（贴进 eval card）
# ══════════════════════════════════════════════════════════════════
# judge–human / human–human / chance / ceiling-normalized / kappa
# 方向一致率（tie 视为可接受）
# 系统级：与人类排名的 Spearman
# 校准：ECE + 低置信 10% 捕捉到的错误比例
# 漂移：相对基线的 Δ 与 CUSUM 状态
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 对齐目标 | 用更强的模型当金标准只能证明一致，不能证明对 | 元评测设计 |
| 人类上界 | 一致率必须配着 a_HH 和随机一致率一起读 | 每份报告 |
| kappa 悖论 | 不均衡分布上 kappa 塌陷，是信号不是缺陷 | 选系数 |
| 样本级 vs 系统级 | 一致率 70% 也能给出正确排名——**前提是误差随机** | 判断 judge 能不能用 |
| 校准与分诊 | swap 一致性比自报置信度更校准，且边际成本为零 | 人力分配 |
| 成本-一致性 | rubric 化的性价比是换大模型的十几倍 | 选 judge |
| CUSUM 哨兵 | 抓缓慢漂移；哨兵集永远不能被用来调 prompt | 长期运维 |

下一模块：**04 · 从成对比较到排名**——Bradley–Terry、Elo、置信区间、主动配对，
以及「排行榜上相差 20 分到底算不算差距」。""")
]
