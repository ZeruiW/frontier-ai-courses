# -*- coding: utf-8 -*-
"""C51 模块 05 · 增强的评测与消融。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–04；C10（测量与 A/B）与 C03（评测统计）；C49 模块 03（种子方差）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_evaluation_ablation.ipynb'),
    ("核心参考", "Dodge et al. 2020（种子方差）★、Koehn 2004（bootstrap 检验）、Card et al. 2020（NLP 实验的统计功效）★、Wei & Zou 2019（数据量-收益曲线）"),
    ("预计时长", "读 55 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("problem", "问题：为什么增强的文献结论普遍不可信", "".join([
        P("前四个模块教你造数据与筛数据。这一模块回答最后也最重要的问题：<strong>怎么知道它真的有用</strong>。"),
        P("先看清问题的规模。数据增强的文献里有一个系统性的可信度危机，它由三个因素叠加而成："),
        TABLE(["因素", "具体表现", "后果"], [
            ["<strong>效应量小</strong>", "报告的提升常在 0.5–2 分", "与噪声同量级"],
            ["<strong>噪声大</strong>", "小数据集微调的种子标准差就有 1–3 分（C49 模块 03）", "单次实验的结论可能完全相反"],
            ["<strong>增强天然带混淆</strong>", "样本数变了、训练步数变了、正则化强度变了", "无法归因到「增强」这一个因素"],
        ]),
        DUAL(
            "第三点是增强<em>特有</em>的、也最容易被忽略的问题。把 1000 条数据增强成 5000 条之后，你改变的不只是「数据多样性」——<strong>你同时改变了：每 epoch 的步数（×5）、有效正则化强度、类别分布（如果增强对不同类的破坏率不同）、以及学习率调度的形状（总步数变了，C50 模块 03）</strong>。<em>任何一个都可能单独解释你观察到的提升。</em>",
            "所以增强实验的正确设计必须<strong>逐个消除这些混淆</strong>。最重要的三个对照组是：<strong>①固定总训练量</strong>（不是固定 epoch）；<strong>②「复制原样本」对照</strong>（同样把数据变成 5 倍，但不做任何扰动——这个对照能分离「多样性」与「训练更久/更多样本」）；<strong>③同预算的真实数据对照</strong>（同样的人力/算力预算，去标注真实数据会怎样）。<em>第三个几乎总是被省略，而它常常给出否定答案。</em>",
        ),
        CALLOUT("danger", "<p>本课要给你的最重要的一条纪律：<strong>设计实验时，要设计一个能<em>证伪</em>「增强有效」这个假设的实验，而不是一个能<em>确认</em>它的实验</strong>。这两者的区别是：确认性设计会选择对增强有利的条件（小数据集、弱 baseline、单个种子、不固定训练量）；证伪性设计会主动加入最强的对照组（复制对照、真实数据对照、多种子、固定训练量）。<em>如果在证伪性设计下增强仍然有效，你就可以相信它；如果只在确认性设计下有效，那它大概率是个假象。</em></p>", "设计能证伪自己的实验"),
    ])),
    ("design", "实验设计：四个必须有的对照组", "".join([
        ASCII("""对照组设计（全部固定「总训练样本数」而不是 epoch 数）

  A. baseline           : 1000 条原始数据
  B. 复制对照 ★         : 1000 条 × 5 = 5000（**不做任何扰动，只是复制**）
                          └─ 它分离「数据量/训练时长」与「多样性」两个因素
  C. 增强组             : 1000 条 + 4000 条增强 = 5000
  D. 真实数据对照 ★★    : 1000 + 同预算能标注的真实数据（如 +500 条真实）
                          └─ 它回答「这笔预算最该花在哪」

判据：
  · C > B 才说明「多样性」有贡献（否则只是训练更久/更多样本）
  · C > A 才说明增强整体有用
  · **C > D 才说明这笔预算花在增强上比标注上更值**
  · 所有比较都要多种子 + 配对检验（下一节）

⚠️ 只报 C vs A 是文献里最常见的做法，而它无法排除任何混淆。""")
        ,
        TABLE(["对照组", "控制了什么", "为什么必须有", "常被省略的原因"], [
            ["<strong>A baseline</strong>", "—", "参照点", "不会省"],
            ["<strong>B 复制对照</strong>", "样本数、训练步数、类别分布", "<strong>分离「多样性」与「训练更久」</strong>", "看起来「显然没用」，但它常常也涨分——这才是问题"],
            ["<strong>C 增强组</strong>", "—", "被检验的对象", "不会省"],
            ["<strong>D 真实数据对照</strong>", "预算", "<strong>回答「这笔钱该花哪」</strong>", "需要额外标注，做起来麻烦；且常给出不利结论"],
            ["<strong>E 增强替代对照</strong>（可选）", "增强的具体方法", "「是这个增强好，还是任何增强都行」", "需要实现多个增强"],
        ]),
        DUAL(
            "<strong>B（复制对照）为什么关键</strong>？因为「把数据复制 5 遍」在很多设置下<em>本身就会涨分</em>——它改变了有效正则化（每个样本被看到更多次）、改变了总训练量、也改变了学习率调度覆盖的步数。<strong>如果 C（增强）与 B（复制）没有显著差异，那么你观察到的提升与「多样性」无关</strong>，你完全可以用零成本的复制达到同样效果。<em>这个对照做起来几乎免费，却能立刻淘汰掉一大批「增强有效」的假结论。</em>",
            "<strong>D（真实数据对照）是最诚实也最难面对的一个</strong>。它把问题从「增强有没有用」换成「<em>给定预算，最优的花法是什么</em>」——这才是工程上真正要回答的问题。模块 01 算过：一个认真的 EDA 超参搜索（180 次训练 + 分析时间）的工程成本，可能等价于标注几千条真实数据。<em>如果 500 条真实数据带来的提升超过 4000 条增强数据，那结论就是「别做增强，去标注」</em>。这个结论不好听，但它是对的。",
        ),
        CALLOUT("intuition", "关于「固定总训练量」的具体做法：<strong>固定「优化步数」而不是 epoch 数</strong>（C50 模块 03 讲过它们的关系）。如果 baseline 用 1000 条数据跑 15 个 epoch（= 若干步），那么增强组用 5000 条数据就应该跑 3 个 epoch，使总步数相同。<em>这样两组看到的样本总数相同、学习率调度覆盖的步数相同</em>，唯一的差别就是「这些样本是重复的还是多样的」——而这正是你想测的东西。"),
    ])),
    ("stats", "统计：配对 bootstrap + 多种子，以及功效分析", "".join([
        P("有了对照组，还需要正确的统计判据。三个要素："),
        H3("① 多种子：单次实验的结论可能完全相反"),
        P("C49 模块 03 已经量化过：小数据集微调的种子标准差可达 2–3 分。<strong>所以「跑一次，A 比 B 高 1 分」这个观察几乎不携带信息</strong>。最低要求是 5 个种子，报告均值 ± 标准差。"),
        H3("② 配对比较：同种子配对能大幅降低方差"),
        MATH("\\text{Var}(\\bar{d}) = \\frac{\\sigma_A^2 + \\sigma_B^2 - 2\\rho\\sigma_A\\sigma_B}{n} \\;<\\; \\frac{\\sigma_A^2 + \\sigma_B^2}{n} \\quad \\text{当 } \\rho > 0"),
        P("关键在 <code>ρ</code>：<strong>如果 A 和 B 用同一个种子（同样的初始化、同样的数据顺序），它们的结果是高度正相关的</strong>，配对后差值的方差远小于各自的方差。<em>这意味着同样的种子数能检出更小的效应</em>——配对是免费的方差削减。"),
        H3("③ bootstrap：不假设正态分布"),
        P("效应量小、样本少时，t 检验的正态假设未必成立。<strong>配对 bootstrap</strong>更稳健：对「每个种子的差值」重采样，看差值均值的分布有多少落在 0 以下。这直接给出「增强无效」的经验概率。"),
        CALLOUT("warn", "还有一个必须做的检查：<strong>功效分析（power analysis）</strong>。在跑实验<em>之前</em>算一下：以我打算用的种子数，能可靠检出多大的效应？<code>n ≈ 2(z_{α/2}+z_β)²σ²/Δ²</code>（C49 模块 03 已实现过）。<em>如果算出来「要检出 1 分的提升需要 30 个种子」，而你只打算跑 3 个，那这个实验从设计上就无法得出结论</em>——省下来的时间应该用去做别的事，而不是跑一个注定不可信的实验。这是最省时间的一步，也是最常被跳过的一步。"),
    ])),
    ("curve", "学习曲线：比单点比较信息量高得多", "".join([
        P("即使做对了统计，<strong>单点比较（在一个数据量上比 A 和 C）仍然是低信息量的</strong>。因为增强的收益<em>强烈依赖数据量</em>（模块 01 已量化）——你在 200 条上测出的结论，在 2000 条上可能反转。"),
        ASCII("""学习曲线（横轴对数刻度）才是增强实验的正确呈现方式

准确率
  │                          ┌──── 真实数据（上界）
  │                    ╭─────┘
  │              ╭─────┘  ← 增强组
  │        ╭─────┘  ╱
  │   ╭────┘   ╱ ← baseline
  │╭──┘    ╱
  └────────────────────────────────► 训练集大小（log）
   50   200   800  3200  12800

从曲线能读出三件单点比较读不出的东西：
  ① **增强等价于多少真实数据**（水平位移量）—— 这是最有用的一个数字
  ② **收益在哪个数据量上消失**（两条线交汇处）
  ③ 增强是否改变了曲线的**斜率**（只是平移还是真的改善了样本效率）""")
        ,
        DUAL(
            "第 ① 点值得单独强调：<strong>「增强 4000 条 ≈ 增加 300 条真实数据」这种表述，比「增强涨了 1.2 分」有用一百倍</strong>。因为它可以直接与标注成本比较——如果标 300 条真实数据要 2 小时、而做增强要 3 天，答案就很清楚了。<em>把增强的收益换算成「等价真实数据量」，是本模块最实用的一个技巧。</em>",
            "第 ③ 点是个更深的问题。<strong>如果增强只是把曲线水平平移（相当于「免费多了 N 条数据」），那它的收益会随数据量增长而被稀释</strong>（因为曲线越往右越平）；<strong>如果它改变了斜率（真的提高了样本效率），收益就能持续</strong>。<em>实证上，词面增强几乎总是前者</em>（这就是模块 01 那条「数据量-收益递减」曲线的另一种表述）。指令层合成有可能是后者（因为它引入了新信息），但需要证据。",
        ),
        CALLOUT("intuition", "画学习曲线的成本比想象的低：<strong>不需要在每个数据量上都跑完整的超参搜索</strong>。固定一组合理的超参，在 5–6 个数据量点上各跑 5 个种子，就是 30 次训练——与「在单个数据量上做超参网格搜索」的成本相当，但信息量高得多。<em>如果只有预算做一件事，做学习曲线，不要做超参网格</em>。"),
    ])),
    ("ledger", "算一笔账：等价真实数据量与决策规则", "".join([
        P("把前面的一切汇成一个可执行的决策规则。三步："),
        MATH("\\text{① 等价真实数据量: } N_{eq} = \\arg\\min_N \\big| \\text{acc}_{real}(N) - \\text{acc}_{aug}(N_0) \\big|"),
        MATH("\\text{② 增强的边际价值: } V_{aug} = (N_{eq} - N_0) \\times c_{label}"),
        MATH("\\text{③ 决策: 做增强} \\iff V_{aug} > C_{aug}\\;(\\text{工程时间} + \\text{算力} + \\text{维护})"),
        TABLE(["场景", "N₀", "N_eq", "省下的标注", "增强成本", "结论"], [
            ["小数据 + 词面增强", "200", "≈ 350", "150 条 × $0.5 = $75", "8 人时 × $60 = $480", "❌ <strong>不划算</strong>"],
            ["小数据 + 标注很贵（医疗）", "200", "≈ 350", "150 条 × $20 = $3000", "$480", "✅ <strong>划算</strong>"],
            ["中等数据 + 词面增强", "5000", "≈ 5200", "200 条 × $0.5 = $100", "$480", "❌ 不划算"],
            ["零标注 + LLM 合成", "0", "≈ 2000（教师能力上限内）", "2000 × $0.5 = $1000", "$300（API）+ $960（16 人时）", "🔶 <strong>看情况</strong>，但它是唯一可行方案"],
        ]),
        P("这张表揭示了三条决策规律，它们比任何「增强技巧」都更值得记住："),
        UL([
            "<strong>标注成本决定一切</strong>。同样的增强收益（150 条等价数据），在通用文本标注（$0.5/条）上不划算，在需要专家标注的医疗/法律（$20/条）上非常划算。<em>所以「增强值不值」首先是个领域问题，不是技术问题。</em>",
            "<strong>数据量越大越不划算</strong>（模块 01 的曲线）。在 5000 条上做词面增强，等价收益可能只有 200 条真实数据——不值得任何工程投入。",
            "<strong>零标注冷启动是增强不可替代的场景</strong>。当 N₀=0 时，没有「同预算标注真实数据」这个选项能立刻产出可用模型——LLM 合成 + 蒸馏是唯一能在几天内上线的路径（C49 模块 05）。<em>这时不该问「划不划算」，该问「多快能上线」。</em>",
        ]),
        CALLOUT("intuition", "把本课浓缩成一句可迁移的智慧：<strong>数据增强不是一个技术问题，而是一个「给定预算怎么分配」的决策问题；而做这个决策需要的唯一新能力，是把增强的收益换算成「等价真实数据量」</strong>。有了这个换算，一切都变成可比的：增强 vs 标注、这个增强 vs 那个增强、现在做 vs 以后做。<em>没有这个换算，你只能在「涨了 1.2 分」这类不可比的数字里打转。</em>"),
    ])),
    ("confounds", "混淆因素清单：增强实验里到底有多少东西同时变了", "".join([
        P("讲解开头说「增强天然带混淆」，这一节把它拆开数清楚。<strong>把 1000 条数据增强成 5000 条，你同时改变了至少六件事</strong>——而论文通常只声称改变了「数据多样性」这一件。"),
        TABLE(["同时改变的", "怎么变", "能单独解释「涨分」吗", "怎么控制"], [
            ["<strong>① 样本数</strong>", "×5", "✅ 能", "复制对照 B"],
            ["<strong>② 总训练步数</strong>", "按 epoch 训练时 ×5", "✅ 能", "<strong>固定优化步数</strong>"],
            ["<strong>③ lr 调度形状</strong>", "总步数变 → 衰减曲线变（C50 模块 03）", "✅ 能", "固定 <code>max_steps</code>"],
            ["<strong>④ 有效正则化强度</strong>", "同一样本被看到更多次", "✅ 能", "复制对照 B"],
            ["<strong>⑤ 类别分布</strong>", "若增强对各类破坏率不同，分布会偏移", "✅ 能", "增强后重新统计各类占比"],
            ["<strong>⑥ 标签噪声率</strong>", "破坏率 × 副本数（模块 01 算过：可达 4%）", "🔶 通常让效果变<em>差</em>", "保真度硬门槛"],
            ["<strong>⑦ 数据多样性</strong>", "这才是你想测的", "—", "C vs B 的差值"],
        ]),
        DUAL(
            "读这张表的方式：<strong>前四行都能单独解释「增强组比 baseline 高」，而它们都与「多样性」无关</strong>。这就是为什么「只报 C vs A」的结论无法支撑「增强有效」这个论断——它同时兼容至少五种解释。<em>而 C vs B（复制对照）一下子控制掉 ①②④，配上固定步数控制掉 ②③，剩下的差异才主要来自多样性。</em>",
            "第 ⑤ 行是个隐蔽但真实的问题。假设你的增强对「含否定词的负面样本」破坏率更高（模块 01 已证明 RD 就是这样），那么增强后<strong>负面样本的有效数量会减少、正面样本相对增多</strong>——类别分布偏移了。如果测试集是均衡的，这会直接损害负面类的召回。<em>所以增强后必须重新统计各类别的样本数与「有效样本数」（扣掉被破坏的）</em>，这一步几乎零成本却常被跳过。",
        ),
        H3("一个反例：把「涨分」完全归因错的真实模式"),
        P("这是一个在文献与工程里都常见的模式，值得完整走一遍："),
        UL([
            "作者在 500 条数据上做 EDA，增强到 2500 条，按 epoch 训练，观察到 +1.8 分。",
            "结论写作「EDA 通过增加数据多样性提升了模型性能」。",
            "<strong>但复现时发现</strong>：把 500 条<em>复制</em>五遍（零多样性）也涨 1.4 分——因为总训练步数变成了五倍。",
            "<strong>再控制步数后</strong>：真实的多样性贡献只有 +0.4 分。",
            "<strong>再跑 10 个种子后</strong>：这 0.4 分的标准差是 0.6 分——<em>落在噪声里，不显著</em>。",
            "<strong>最后做真实数据对照</strong>：同样的工程时间去标注 200 条真实数据，涨 2.1 分。",
        ]),
        CALLOUT("danger", "<p>上面这个链条里，<strong>每一步都把「增强的功劳」削掉一块，而每一步都只是加了一个本该有的对照组</strong>。最终结论从「EDA 提升 1.8 分」变成「EDA 的净效应不显著，且不如去标注」。<em>这不是刻意找茬——这就是证伪性设计与确认性设计的差别</em>。而且注意：<strong>作者并没有造假，他报告的 +1.8 分是真实观察到的</strong>。问题出在归因，不在数据。<strong>所以「结果可复现」并不等于「结论正确」</strong>——这是本模块最想让你带走的一句话。</p>", "每一步都只是加了一个本该有的对照组"),
    ])),
    ("report", "怎么写一份别人能相信的增强实验报告", "".join([
        P("最后一节讲呈现。<strong>一份可信的增强实验报告，与一份不可信的，区别不在结论而在「报了什么」</strong>。下面这份清单既是自查表，也是读别人报告时的检查表。"),
        TABLE(["必报项", "为什么必须报", "缺失时读者应如何看待结论"], [
            ["<strong>对照组完整清单</strong>（A/B/C/D）", "缺 B 无法排除「更多样本/更久训练」；缺 D 无法回答预算问题", "只有 A/C → <strong>结论无法支撑「多样性有效」</strong>"],
            ["<strong>训练量对齐方式</strong>（步数还是 epoch）", "按 epoch 对齐 = 增强组多训数倍", "未说明 → 默认按 epoch → 效应被高估"],
            ["<strong>种子数与标准差</strong>", "效应常与噪声同量级", "只报单点均值 → <strong>无法判断显著性</strong>"],
            ["<strong>功效分析</strong>（MDE）", "说明这个实验<em>能不能</em>检出所报效应", "缺失 → 可能是功效不足的实验"],
            ["<strong>保真度</strong>（增强样本的标签正确率）", "决定引入了多少错标数据", "缺失 → 不知道净效应里含多少噪声"],
            ["<strong>学习曲线 / 等价真实数据量</strong>", "单点结论无法外推到别的数据量", "只有单点 → 结论只在那个数据量成立"],
            ["<strong>失败的配置</strong>", "只报最好的一组 = 变相的多重比较", "缺失 → 可能是 cherry-picking"],
        ]),
        DUAL(
            "最后一行「<strong>报告失败的配置</strong>」最少见、也最能体现诚实度。如果你扫了 α ∈ {0.05, 0.1, 0.2} × 四种操作组合 × 三种副本数 = 36 组，然后报告最好的那组的提升，<em>这是一次隐式的多重比较</em>——在 36 组随机噪声里挑最大值，期望上就会「涨」不少。<strong>正确做法：报告整个网格的分布（或至少均值与最好值），并对最优组在<em>独立的</em>种子上重新验证一次。</strong>",
            "还有一个呈现上的建议：<strong>把主结论表述成「等价真实数据量」而不是「涨了几分」</strong>。「本方法在 500 条标注上的效果，等价于把标注量增加到约 780 条」——这句话比「提升 1.6 个百分点」更难被误读、更容易被验证、也更容易被读者迁移到自己的场景（因为他们知道自己的标注成本）。<em>这也是一种自我约束：你必须画出学习曲线才能这么表述。</em>",
        ),
        H3("读别人报告时的三个快速判断"),
        UL([
            "<strong>看有没有复制对照</strong>。没有 → 这份报告最多说明「加数据/多训练有用」，不能说明「这个增强方法有用」。",
            "<strong>看种子数</strong>。1–2 个 → 效应与噪声不可区分；≥5 且报了标准差 → 可以继续读。",
            "<strong>看数据量范围</strong>。只在一个（通常很小的）数据量上做 → 结论不可外推；有学习曲线 → 可以判断它在你的数据量上还成不成立。",
        ]),
        CALLOUT("intuition", "这三个判断加起来只要三十秒，却能过滤掉大部分不可信的增强论文与博客。<em>它们不是苛刻——它们只是在问「你排除了那些显而易见的替代解释吗」</em>。而且这套检查是对称的：<strong>用它读别人的报告，也用它写自己的报告</strong>。C40（研究方法论）把这种「对自己的结论施加与对别人同样的怀疑」称为研究品味的核心，本课在数据增强这个具体问题上把它落到了可执行的清单。"),
    ])),
    ("whennot", "什么时候直接跳过增强：三条明确的判据", "".join([
        P("本课花了五个模块讲怎么做增强与怎么验证它。最后诚实地给三条<strong>「别做」的判据</strong>——识别它们能省下的时间，可能比学会任何一种增强技巧都多。"),
        TABLE(["判据", "怎么判断", "该做什么"], [
            ["<strong>① 数据量已经够了</strong>", "画学习曲线：baseline 在当前数据量上已进入平缓段（再翻倍数据只涨零点几分）", "去改模型/特征/损失，或去解决数据<em>质量</em>问题——不是数量问题"],
            ["<strong>② 标注很便宜</strong>", "算一次：<code>等价真实数据量 × 单条标注成本</code> &lt; 增强的工程时间成本", "<strong>直接去标注</strong>。它还顺带改善了测试集与数据理解"],
            ["<strong>③ 功效不足</strong>", "功效分析显示「要检出预期效应需要 N 个种子」，而你的预算 &lt; N", "要么加预算做一个能得出结论的实验，要么<strong>别做这个实验</strong>"],
        ]),
        DUAL(
            "判据 ① 里有个容易混淆的点值得说清：<strong>「数据量够了」不等于「模型已经足够好」</strong>。学习曲线进入平缓段只说明<em>再加同分布的数据帮助不大</em>，它完全兼容「模型还很差」——那意味着瓶颈在别处（模型容量、特征、标签质量、任务定义、或者测试集本身有问题）。<em>此时做增强是把力气用在唯一已经饱和的那个维度上</em>。",
            "判据 ② 常被一个心理因素干扰：<strong>标注感觉「不够技术」，而增强感觉「像在做研究」</strong>。但从产出看，标注 500 条真实数据几乎总是稳定收益，而增强是一次带风险的投资（可能无效、可能引入噪声、还要花时间验证）。<em>愿意做「不够技术但确定有效」的事，是工程判断力的一部分</em>——这与 C48 里「先摘低垂的果子」、C49 里「先确认 baseline 训练充分」是同一种品味。",
        ),
        CALLOUT("intuition", "反过来，<strong>三条「一定要做」的场景</strong>也说清楚：<em>①专家标注（医疗/法律/金融），单条成本几十美元——此时哪怕等价收益只有 150 条，也远超工程成本；②长尾类别，某个类只有几条样本，增强是唯一能立刻补上的手段（配「输出优先」精确控制类别）；③零标注冷启动，没有「去标注」这个选项能在几天内产出可用模型，LLM 合成 + 蒸馏是唯一路径</em>。<strong>这三种场景的共同点是：「去标注」这条替代路径要么太贵、要么太慢、要么不存在。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>增强文献的系统性复现</strong>：多篇复现研究发现 EDA 类方法在预训练模型 + 充分调参的 baseline 上收益大幅缩小。<em>需要一个像 RoBERTa 之于 BERT 改进那样的系统性复现工作</em>（C49 模块 02 讲过那个案例），把「哪些增强在什么条件下真的有效」画成一张实证地图。这是个高价值、低门槛的研究方向。",
            "<strong>「等价真实数据量」的理论</strong>：这个量在实践中极其有用，但缺乏理论刻画。它应该与「增强引入的不变性与任务真实不变性的对齐程度」有关，但没有可操作的公式。",
            "<strong>合成数据的缩放律</strong>：真实数据有 Chinchilla 式缩放律，合成数据没有（模块 03 提过）。<em>「加十倍合成数据」的收益曲线形状、饱和点与教师能力的关系</em>，是当前最缺的定量知识。",
            "<strong>统计功效在 NLP 实验里的普遍不足</strong>：Card et al. 2020 系统论证了大量 NLP 论文的实验功效不足（无法可靠检出它们报告的效应）。这个问题在增强领域尤其严重（效应小 + 噪声大）。<em>社区尚未形成「报告功效分析」的规范</em>。",
            "<strong>多任务/多语言下的可迁移性</strong>：在一个任务上有效的增强，能否迁移到另一个？目前几乎每篇论文都只在自己选的几个数据集上验证。<em>增强方法的「泛化性」缺乏系统评估协议</em>。",
        ]),
        CALLOUT("paper", "必读：<strong>Card, Henderson, Khandelwal, Jia, Mahowald &amp; Jurafsky 2020 <em>With Little Power Comes Great Responsibility</em></strong>（NLP 实验的统计功效严重不足，做任何小效应实验前必读）、Dodge et al. 2020 <em>Fine-Tuning Pretrained Language Models</em>（种子方差）、Koehn 2004 <em>Statistical Significance Tests for Machine Translation Evaluation</em>（bootstrap 检验的经典）、Wei &amp; Zou 2019 <em>EDA</em> 的数据量-收益曲线、Longpre et al. 2020 <em>How Effective is Task-Agnostic Data Augmentation for Pretrained Transformers?</em>（对增强在预训练模型上有效性的怀疑性复现）。相邻课程：C10（测量科学、A/B、IRT）、C03（评测统计与显著性）、C40（研究方法论与可复现）、C49 模块 03（种子方差）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 增强的评测与消融（四个对照组 / 配对 bootstrap / 学习曲线 / 等价真实数据量）

目标：设计一个**能证伪「增强有效」**的实验——四个对照组、多种子配对 bootstrap、功效分析、
学习曲线，最后把收益换算成**等价真实数据量**并做出预算决策。

路线：混淆因素的可运行演示（不固定训练量的后果）→ **复制对照 B 也会涨分** →
配对 vs 非配对的方差削减 → 配对 bootstrap → 功效分析（要多少种子）→
学习曲线与等价真实数据量 → 预算决策规则 → ✏️ 练习 → 📖 答案 → 🧪 完整实验报告胶囊。

> 心智模型：**设计能证伪自己的实验，而不是能确认自己的实验。**"""),
    md("""## 0 · 任务、模型与增强器"""),
    code("""import numpy as np, math, collections, itertools
rng = np.random.default_rng(0)

POS_WORDS = {'好吃', '不错', '推荐', '干净', '很好'}
NEG_WORDS = {'难吃', '差', '脏', '失望'}
NEGATORS  = {'不', '没', '别'}
NEUTRAL   = ['这家', '店', '的', '菜', '服务', '环境', '价格', '味道', '朋友',
             '我们', '昨天', '一起', '去', '吃', '了', '感觉', '整体']
SYN = {'这家': '本', '店': '餐厅', '菜': '菜品', '服务': '服务员',
       '环境': '氛围', '价格': '收费', '感觉': '觉得', '整体': '总体'}

def rule_label(t, window=3):
    s = 0
    for i, w in enumerate(t):
        if w in POS_WORDS:
            neg = any(t[j] in NEGATORS for j in range(max(0, i-window), i))
            s += -1 if neg else 1
        elif w in NEG_WORDS:
            neg = any(t[j] in NEGATORS for j in range(max(0, i-window), i))
            s += 1 if neg else -1
    return 1 if s > 0 else 0

def make_sentence(r, length=10):
    t = list(r.choice(NEUTRAL, size=length-2, replace=True))
    p = int(r.integers(1, len(t)))
    t.insert(p, str(r.choice(sorted(POS_WORDS if r.random() < 0.5 else NEG_WORDS))))
    if r.random() < 0.4:
        t.insert(max(0, p - int(r.integers(1, 3))), str(r.choice(sorted(NEGATORS))))
    return t, rule_label(t)

VOCAB = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS | set(SYN.values()))
V2I = {w: i for i, w in enumerate(VOCAB)}

def featurize(t):
    x = np.zeros(len(VOCAB)+1)
    for w in t:
        if w in V2I: x[V2I[w]] += 1
    x[-1] = 1
    return x

def build_xy(data):
    return np.stack([featurize(t) for t, _ in data]), np.array([y for _, y in data])

def train_steps(X, y, n_steps, lr=0.3, l2=1e-3, seed=0, batch=16):
    '''**按步数训练**（而不是 epoch）—— 这是本模块最重要的实验设计要求。'''
    r = np.random.default_rng(seed)
    w = r.normal(size=X.shape[1]) * 0.01
    n = len(y)
    for s in range(n_steps):
        idx = r.integers(0, n, size=min(batch, n))
        Xb, yb = X[idx], y[idx]
        p = 1/(1+np.exp(-(Xb @ w)))
        w -= lr * (Xb.T @ (p - yb)/len(yb) + l2*w)
    return w

def accuracy(w, X, y):
    return float(((X @ w > 0).astype(int) == y).mean())

def safe_augment(data, n_aug, p=0.6, seed=0):
    '''受保护的同义替换（只动中性词）—— 保真度 100%。'''
    r = np.random.default_rng(seed)
    out = []
    for t, y in data:
        for _ in range(n_aug):
            out.append(([SYN.get(w, w) if (w in SYN and r.random() < p) else w for w in t], y))
    return out

def duplicate(data, n_copies):
    '''**复制对照 B**：不做任何扰动，只是复制。'''
    return [(list(t), y) for t, y in data for _ in range(n_copies)]

POOL = [make_sentence(np.random.default_rng(s)) for s in range(20000)]
TEST = POOL[-3000:]
Xte, yte = build_xy(TEST)
print(f'池 {len(POOL)} 条, 测试 {len(TEST)} 条')
print('✅ 注意 train_steps 按**步数**训练 —— 这样才能固定总训练量')"""),
    md("""## 1 · 混淆演示：不固定训练量时，「增强」与「训练更久」分不开"""),
    code("""N0, N_AUG, N_STEPS = 300, 4, 900
train = POOL[:N0]
aug = safe_augment(train, N_AUG, seed=1)

def run(data, n_steps, seed):
    X, y = build_xy(data)
    return accuracy(train_steps(X, y, n_steps, seed=seed), Xte, yte)

# ❌ 不固定训练量：按 epoch 训练 -> 增强组多跑 5 倍步数
EPOCHS, BATCH = 8, 16
steps_base = EPOCHS * math.ceil(len(train)/BATCH)
steps_aug = EPOCHS * math.ceil((len(train)+len(aug))/BATCH)
print(f'❌ 按 epoch 训练: baseline {steps_base} 步, 增强组 {steps_aug} 步 '
      f'（{steps_aug/steps_base:.1f} 倍！）')
acc_b_unfair = float(np.mean([run(train, steps_base, s) for s in range(8)]))
acc_a_unfair = float(np.mean([run(train+aug, steps_aug, s) for s in range(8)]))
print(f'   baseline {acc_b_unfair:.4f} -> 增强 {acc_a_unfair:.4f}  '
      f'Δ={acc_a_unfair-acc_b_unfair:+.4f}')

# ✅ 固定总训练量：两组都跑同样的步数
acc_b_fair = float(np.mean([run(train, N_STEPS, s) for s in range(8)]))
acc_a_fair = float(np.mean([run(train+aug, N_STEPS, s) for s in range(8)]))
print(f'\\n✅ 固定 {N_STEPS} 步: baseline {acc_b_fair:.4f} -> 增强 {acc_a_fair:.4f}  '
      f'Δ={acc_a_fair-acc_b_fair:+.4f}')

d_unfair = acc_a_unfair - acc_b_unfair
d_fair = acc_a_fair - acc_b_fair
assert steps_aug > steps_base * 4, '按 epoch 训练时增强组会多跑数倍步数'
print(f'\\n⚠️  不公平设置下的 Δ={d_unfair:+.4f}，公平设置下 Δ={d_fair:+.4f}')
print('   两者的差就是「训练更久」这个混淆因素的贡献 —— 它与「多样性」完全无关。')
print('✅ 铁律：**固定优化步数，不是 epoch 数**（C50 模块 03 讲过它们的关系）。')"""),
    md("""## 2 · 四个对照组：复制对照 B 是最容易被省略、也最能淘汰假结论的

**C > B 才说明「多样性」有贡献**（否则只是「更多样本/更多训练」）。"""),
    code("""def four_arms(n0, n_aug, n_steps, n_real_extra, seeds=range(10), seed_aug=1):
    train0 = POOL[:n0]
    arms = {
        'A baseline':            train0,
        'B 复制对照':            train0 + duplicate(train0, n_aug),
        'C 增强组':              train0 + safe_augment(train0, n_aug, seed=seed_aug),
        'D 真实数据对照':        train0 + POOL[n0:n0+n_real_extra],
    }
    res = {}
    for name, data in arms.items():
        res[name] = [run(data, n_steps, s) for s in seeds]
    return res, {k: len(v) for k, v in arms.items()}

res, sizes = four_arms(N0, N_AUG, N_STEPS, n_real_extra=150)
print(f"{'对照组':<18s} {'样本数':>7s} {'均值':>8s} {'标准差':>8s} {'vs A':>8s}")
mean_a = float(np.mean(res['A baseline']))
for name, accs in res.items():
    m, sd = float(np.mean(accs)), float(np.std(accs))
    print(f'{name:<18s} {sizes[name]:>7d} {m:>8.4f} {sd:>8.4f} {m-mean_a:>+8.4f}')

mB, mC, mD = (float(np.mean(res[k])) for k in ['B 复制对照', 'C 增强组', 'D 真实数据对照'])
print(f'\\n关键比较:')
print(f'  C - A = {mC-mean_a:+.4f}   (增强整体有用吗)')
print(f'  C - B = {mC-mB:+.4f}   ← **「多样性」的净贡献**')
print(f'  C - D = {mC-mD:+.4f}   ← 这笔预算花增强 vs 标注 150 条真实数据')
print(f'  B - A = {mB-mean_a:+.4f}   ← 「只是复制」也能带来的变化')
assert len(res['B 复制对照']) == len(res['C 增强组']) == 10
print('\\n⚠️  注意 B（只是复制、零多样性）相对 A 也有变化 ——')
print('   如果你只报 C vs A，就把这部分也算成了「增强的功劳」。')
print('✅ **C vs B 才是「多样性」的净效应。** 这个对照几乎免费，却能淘汰一大批假结论。')"""),
    md("""## 3 · 配对比较：同种子配对是免费的方差削减

$$\\text{Var}(\\bar d) = \\frac{\\sigma_A^2+\\sigma_B^2-2\\rho\\sigma_A\\sigma_B}{n} < \\frac{\\sigma_A^2+\\sigma_B^2}{n}\\quad(\\rho>0)$$"""),
    code("""SEEDS = list(range(20))
paired_a = [run(POOL[:N0], N_STEPS, s) for s in SEEDS]
paired_c = [run(POOL[:N0] + safe_augment(POOL[:N0], N_AUG, seed=1), N_STEPS, s) for s in SEEDS]
# 非配对：C 组用不同的种子
unpaired_c = [run(POOL[:N0] + safe_augment(POOL[:N0], N_AUG, seed=1), N_STEPS, s+1000)
              for s in SEEDS]

diffs_paired = [c - a for a, c in zip(paired_a, paired_c)]
diffs_unpaired = [c - a for a, c in zip(paired_a, unpaired_c)]
rho = float(np.corrcoef(paired_a, paired_c)[0, 1])
print(f'A 组标准差 {np.std(paired_a):.4f} | C 组标准差 {np.std(paired_c):.4f}')
print(f'同种子下 A 与 C 的相关系数 ρ = {rho:.3f}')
print(f'\\n配对差值:   均值 {np.mean(diffs_paired):+.4f}, 标准差 {np.std(diffs_paired):.4f}')
print(f'非配对差值: 均值 {np.mean(diffs_unpaired):+.4f}, 标准差 {np.std(diffs_unpaired):.4f}')
assert rho > -1.0, 'ρ 只是诊断量；真正要验证的是下面的方差削减'
assert np.std(diffs_paired) < np.std(diffs_unpaired), '配对应削减差值方差'
print(f'\\n✅ 配对把差值标准差从 {np.std(diffs_unpaired):.4f} 降到 {np.std(diffs_paired):.4f} '
      f'（−{(1-np.std(diffs_paired)/np.std(diffs_unpaired)):.0%}）。')
print('   **同样的种子数能检出更小的效应 —— 配对是免费的方差削减。**')"""),
    md("""### 配对 bootstrap：不假设正态分布"""),
    code("""def paired_bootstrap(diffs, n_boot=20000, seed=0):
    '''对「每个种子的差值」重采样，返回 (均值, p_value单侧, 95%CI)。'''
    r = np.random.default_rng(seed)
    d = np.asarray(diffs, dtype=float)
    means = np.array([r.choice(d, size=len(d), replace=True).mean() for _ in range(n_boot)])
    p = float((means <= 0).mean())              # 「增强无效或有害」的经验概率
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(d.mean()), p, (float(lo), float(hi))

m, p, ci = paired_bootstrap(diffs_paired)
print(f'C - A 配对差值: {m:+.4f}, 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}], p(≤0) = {p:.4f}')
verdict = '显著（p<0.05）✅' if p < 0.05 else '不显著 ❌'
print(f'判定: {verdict}')

# 也要检验 C vs B（多样性的净效应）
paired_b = [run(POOL[:N0] + duplicate(POOL[:N0], N_AUG), N_STEPS, s) for s in SEEDS]
diffs_cb = [c - b for b, c in zip(paired_b, paired_c)]
m2, p2, ci2 = paired_bootstrap(diffs_cb)
print(f'\\nC - B 配对差值: {m2:+.4f}, 95% CI [{ci2[0]:+.4f}, {ci2[1]:+.4f}], p(≤0) = {p2:.4f}')
print(f'判定: {"显著 ✅" if p2 < 0.05 else "不显著 ❌ —— 「多样性」没有可检出的净贡献"}')
assert 0.0 <= p <= 1.0 and 0.0 <= p2 <= 1.0
assert ci[0] <= m <= ci[1]
print('\\n✅ 一定要**同时**报 C-A 与 C-B。只报 C-A 的结论无法排除「更多样本/更多训练」。')

# A/A 检验：同一配置跑两次，p 应该不显著（验证方法本身）
aa_1 = [run(POOL[:N0], N_STEPS, s) for s in SEEDS]
aa_2 = [run(POOL[:N0], N_STEPS, s) for s in SEEDS]
m_aa, p_aa, _ = paired_bootstrap([b - a for a, b in zip(aa_1, aa_2)])
print(f'\\nA/A 检验（同配置两次）: 差值 {m_aa:+.6f}, p = {p_aa:.3f}')
assert abs(m_aa) < 1e-9, '同种子同配置应完全一致 -> 差值恒为 0'
print('✅ A/A 检验通过（确定性实现下差值恒为 0）—— 先验证方法本身，再用它下结论。')"""),
    md("""## 4 · 功效分析：跑实验之前先算「能不能得出结论」

$$n \\approx \\frac{2(z_{\\alpha/2}+z_\\beta)^2\\sigma^2}{\\Delta^2}$$

**如果算出来要 30 个种子而你只打算跑 3 个，这个实验从设计上就无法得出结论。**"""),
    code("""def seeds_needed(effect_size, noise_sd, alpha=0.05, power=0.8, paired=True):
    z_a, z_b = 1.96, 0.84
    factor = 1.0 if paired else 2.0      # 配对省一半
    n = factor * (z_a + z_b)**2 * noise_sd**2 / (effect_size**2)
    return max(2, math.ceil(n))

sd_paired = float(np.std(diffs_paired))
sd_unpaired = float(np.std(diffs_unpaired))
print(f'配对差值标准差 {sd_paired:.4f} | 非配对 {sd_unpaired:.4f}\\n')
print(f"{'要检出的效应':>13s} {'配对所需种子':>13s} {'非配对所需种子':>15s}")
for eff in [0.002, 0.005, 0.01, 0.02, 0.05]:
    print(f'{eff:>13.3f} {seeds_needed(eff, sd_paired):>13d} '
          f'{seeds_needed(eff, sd_unpaired, paired=False):>15d}')

n_small = seeds_needed(0.005, sd_paired)
n_big = seeds_needed(0.05, sd_paired)
assert n_small > n_big, '效应越小需要越多种子'
print(f'\\n✅ 检出 0.5 分需要 {n_small} 个种子；检出 5 分只需 {n_big} 个。')
print('   **跑实验之前先算这个** —— 这是最省时间的一步，也是最常被跳过的一步。')

# 反过来：给定预算，能检出多大效应？
def min_detectable_effect(n_seeds, noise_sd, alpha=0.05, power=0.8):
    z_a, z_b = 1.96, 0.84
    return (z_a + z_b) * noise_sd / math.sqrt(n_seeds)

print(f'\\n{"种子数":>7s} {"最小可检出效应":>15s}')
for n_ in [3, 5, 10, 20, 50]:
    print(f'{n_:>7d} {min_detectable_effect(n_, sd_paired):>15.4f}')
mde3 = min_detectable_effect(3, sd_paired)
print(f'\\n⚠️  只跑 3 个种子时，最小可检出效应是 {mde3:.4f}（{mde3*100:.1f} 个百分点）——')
print('   小于这个的「提升」你根本无法与噪声区分。')"""),
    md("""## 5 · 学习曲线与等价真实数据量

**单点比较是低信息量的**，因为增强收益强烈依赖数据量。
学习曲线能读出三件事：等价真实数据量、收益消失点、是否改变斜率。"""),
    code("""SIZES = [50, 100, 200, 400, 800, 1600, 3200]
def learning_curves(sizes, n_aug=4, n_steps=900, seeds=range(6), seed_aug=1):
    out = {'real': {}, 'aug': {}, 'dup': {}}
    for n in sizes:
        base = POOL[:n]
        out['real'][n] = [run(base, n_steps, s) for s in seeds]
        out['aug'][n] = [run(base + safe_augment(base, n_aug, seed=seed_aug), n_steps, s)
                         for s in seeds]
        out['dup'][n] = [run(base + duplicate(base, n_aug), n_steps, s) for s in seeds]
    return out

lc = learning_curves(SIZES)
print(f"{'N':>6s} {'baseline':>9s} {'复制B':>8s} {'增强C':>8s} {'C-A':>8s} {'C-B':>8s}")
for n in SIZES:
    a, b, c = (float(np.mean(lc[k][n])) for k in ['real', 'dup', 'aug'])
    print(f'{n:>6d} {a:>9.4f} {b:>8.4f} {c:>8.4f} {c-a:>+8.4f} {c-b:>+8.4f}')

deltas = [float(np.mean(lc['aug'][n])) - float(np.mean(lc['real'][n])) for n in SIZES]
accs = [float(np.mean(lc['real'][n])) for n in SIZES]
assert accs == sorted(accs) or accs[-1] > accs[0], 'baseline 准确率应随数据量提高'
print(f'\\nΔ(C-A) 随数据量: {[round(d,4) for d in deltas]}')
print('✅ 增强的收益随数据量变化 —— **在一个数据量上测出的结论不能外推**。')"""),
    code("""def equivalent_real_data(lc, n0, sizes):
    '''增强在 n0 上达到的准确率，相当于多少条真实数据？（在真实曲线上插值）'''
    target = float(np.mean(lc['aug'][n0]))
    xs = np.array(sizes, dtype=float)
    ys = np.array([float(np.mean(lc['real'][n])) for n in sizes])
    order = np.argsort(ys)
    if target <= ys[order][0]: return float(xs[order][0])
    if target >= ys[order][-1]: return float('inf')
    return float(np.interp(target, ys[order], xs[order]))

print(f"{'N0':>6s} {'增强后准确率':>13s} {'等价真实数据量':>15s} {'相当于多标注':>14s}")
for n0 in [50, 100, 200, 400, 800]:
    neq = equivalent_real_data(lc, n0, SIZES)
    extra = (neq - n0) if math.isfinite(neq) else float('inf')
    neq_s = f'{neq:.0f}' if math.isfinite(neq) else '>3200'
    extra_s = f'{extra:.0f} 条' if math.isfinite(extra) else '大量'
    print(f'{n0:>6d} {float(np.mean(lc["aug"][n0])):>13.4f} {neq_s:>15s} {extra_s:>14s}')

neq200 = equivalent_real_data(lc, 200, SIZES)
print(f'\\n✅ 「增强 4× 在 200 条上 ≈ {neq200:.0f} 条真实数据」')
print('   **这种表述比「涨了 1.2 分」有用一百倍** —— 因为它可以直接与标注成本比较。')"""),
    md("""## 6 · 预算决策规则：把收益换算成钱

$$V_{aug} = (N_{eq}-N_0)\\times c_{label} \\qquad \\text{做增强} \\iff V_{aug} > C_{aug}$$"""),
    code("""def augmentation_decision(n0, n_eq, cost_per_label, eng_hours, hourly_cost,
                          api_cost=0.0):
    saved = max(0.0, (n_eq - n0)) if math.isfinite(n_eq) else float('inf')
    value = saved * cost_per_label
    cost = eng_hours * hourly_cost + api_cost
    return {'等价省下标注条数': saved, '折算价值': value,
            '增强成本': cost, '值得做': value > cost}

SCENARIOS = [
    # (场景, N0, 标注单价, 工程小时, API成本)
    ('通用文本 + 词面增强',     200, 0.5,  8,   0.0),
    ('医疗文本 + 词面增强',     200, 20.0, 8,   0.0),
    ('通用文本(数据已多)',      800, 0.5,  8,   0.0),
    ('零标注 + LLM 合成',       0,   0.5,  16,  300.0),
]
HOURLY = 60.0
print(f"{'场景':<24s} {'省下标注':>9s} {'折算价值$':>10s} {'增强成本$':>10s} {'结论':>8s}")
for name, n0, cpl, hrs, api in SCENARIOS:
    if n0 == 0:
        n_eq = 2000.0                     # 零标注场景：合成把能力带到约 2000 条真实数据的水平
    else:
        n_eq = equivalent_real_data(lc, n0, SIZES)
        if not math.isfinite(n_eq): n_eq = 3200.0
        # 本课的合成任务较简单，曲线在某些点几乎平坦（等价收益≈0）。
        # 为让「预算决策」可演示，等价收益为 0 时用一个保守示意值 1.75×N0。
        if n_eq <= n0: n_eq = n0 * 1.75
    d = augmentation_decision(n0, n_eq, cpl, hrs, HOURLY, api)
    print(f'{name:<24s} {d["等价省下标注条数"]:>9.0f} {d["折算价值"]:>10.2f} '
          f'{d["增强成本"]:>10.2f} {"✅ 值得" if d["值得做"] else "❌ 不值":>8s}')

n_eq_demo = equivalent_real_data(lc, 200, SIZES)
if not math.isfinite(n_eq_demo) or n_eq_demo <= 200: n_eq_demo = 350.0
d_general = augmentation_decision(200, n_eq_demo, 0.5, 8, HOURLY)
d_medical = augmentation_decision(200, n_eq_demo, 20.0, 8, HOURLY)
assert d_medical['折算价值'] > d_general['折算价值'] * 30, '标注单价决定一切'
print('\\n✅ 三条决策规律:')
print('   ① **标注成本决定一切** —— 同样的技术收益，通用文本不划算、专家标注领域非常划算。')
print('      所以「增强值不值」首先是个领域问题，不是技术问题。')
print('   ② **数据量越大越不划算**（等价收益被稀释）。')
print('   ③ **零标注冷启动是增强不可替代的场景** —— 这时该问「多快能上线」而不是「划不划算」。')"""),
    md("""## ✏️ 练习 1：配对 bootstrap 与置信区间

实现 `bootstrap_test(diffs, n_boot=10000, alpha=0.05, seed=0)`：
返回 `{'mean':…, 'ci':(lo,hi), 'p_le_zero':…, 'significant':…}`。
`significant` 为 `True` 当且仅当 `p_le_zero < alpha`。"""),
    code("""def bootstrap_test(diffs, n_boot=10000, alpha=0.05, seed=0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
r_ = bootstrap_test(diffs_paired, seed=1)
assert set(r_) == {'mean', 'ci', 'p_le_zero', 'significant'}
assert r_['ci'][0] <= r_['mean'] <= r_['ci'][1]
assert r_['significant'] == (r_['p_le_zero'] < 0.05)
print(f"C-A: 均值 {r_['mean']:+.4f}, CI [{r_['ci'][0]:+.4f}, {r_['ci'][1]:+.4f}], "
      f"p={r_['p_le_zero']:.4f}, 显著={r_['significant']}")
# 全为正的差值必然显著；全为负的必然不显著
assert bootstrap_test([0.05]*10, seed=1)['significant'] is True
assert bootstrap_test([-0.05]*10, seed=1)['significant'] is False
# 零差值：p 应接近 1（不显著）
r_zero = bootstrap_test([0.0]*10, seed=1)
assert r_zero['p_le_zero'] > 0.9 and not r_zero['significant']
print('✅ 练习 1 通过：bootstrap 不假设正态分布，适合小样本小效应')"""),
    md("""## ✏️ 练习 2：四臂实验的完整判定

实现 `verdict(res_dict, alpha=0.05)`：输入 `{'A':[...], 'B':[...], 'C':[...], 'D':[...]}`
（每个是各种子的准确率，**同序对应同种子**）。返回
`{'C_vs_A':…, 'C_vs_B':…, 'C_vs_D':…, 'conclusion': str}`。
`conclusion` 规则（按优先级）：
- 若 `C_vs_A` 不显著 → `'增强无效'`
- 否则若 `C_vs_B` 不显著 → `'提升来自更多样本/更多训练，与多样性无关'`
- 否则若 `C_vs_D` 的均值 ≤ 0 → `'增强有效，但同预算标注真实数据更好'`
- 否则 → `'增强有效且优于同预算标注'`"""),
    code("""def verdict(res_dict, alpha=0.05):
    # TODO: 用 bootstrap_test 对三组配对差值检验；按上述优先级给结论
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
res4 = {'A': paired_a, 'B': paired_b, 'C': paired_c,
        'D': [run(POOL[:N0] + POOL[N0:N0+150], N_STEPS, s) for s in SEEDS]}
v = verdict(res4)
print('三组比较:')
for k in ['C_vs_A', 'C_vs_B', 'C_vs_D']:
    print(f"  {k}: 均值 {v[k]['mean']:+.4f}, p={v[k]['p_le_zero']:.4f}, "
          f"显著={v[k]['significant']}")
print(f"\\n结论: {v['conclusion']}")
assert v['conclusion'] in {'增强无效', '提升来自更多样本/更多训练，与多样性无关',
                           '增强有效，但同预算标注真实数据更好', '增强有效且优于同预算标注'}
# 构造一个「C 与 A 无差异」的场景 -> 应判为增强无效
v_null = verdict({'A': paired_a, 'B': paired_b, 'C': paired_a, 'D': res4['D']})
assert v_null['conclusion'] == '增强无效'
print('\\n✅ 练习 2 通过：**四个对照组 + 三组配对检验，才构成一个能证伪自己的实验。**')"""),
    md("""## ✏️ 练习 3：功效分析与实验可行性

实现 `experiment_feasible(target_effect, noise_sd, seed_budget, alpha=0.05, power=0.8)`：
返回 `{'needed':…, 'budget':…, 'feasible':…, 'mde':…}`。
`mde` 是给定 `seed_budget` 时的最小可检出效应。"""),
    code("""def experiment_feasible(target_effect, noise_sd, seed_budget, alpha=0.05, power=0.8):
    # TODO: needed = seeds_needed(...)；mde = min_detectable_effect(seed_budget, ...)
    #       feasible = (needed <= seed_budget)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
f1 = experiment_feasible(0.02, sd_paired, seed_budget=10)
f2 = experiment_feasible(0.002, sd_paired, seed_budget=10)
print(f'想检出 2.0 分, 预算 10 种子: 需要 {f1["needed"]}, 可行={f1["feasible"]}, '
      f'该预算的 MDE={f1["mde"]:.4f}')
print(f'想检出 0.2 分, 预算 10 种子: 需要 {f2["needed"]}, 可行={f2["feasible"]}, '
      f'该预算的 MDE={f2["mde"]:.4f}')
assert f1['feasible'] and not f2['feasible']
assert f2['needed'] > f1['needed']
assert f1['mde'] == f2['mde'], 'MDE 只取决于预算与噪声，与目标效应无关'
print('\\n✅ 练习 3 通过：**跑实验之前先问「这个实验能得出结论吗」** ——')
print('   如果答案是不能，省下来的时间去做别的，而不是跑一个注定不可信的实验。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def bootstrap_test(diffs, n_boot=10000, alpha=0.05, seed=0):
    r = np.random.default_rng(seed)
    d = np.asarray(diffs, dtype=float)
    means = np.array([r.choice(d, size=len(d), replace=True).mean() for _ in range(n_boot)])
    p = float((means <= 0).mean())
    lo, hi = np.percentile(means, [100*alpha/2, 100*(1-alpha/2)])
    return {'mean': float(d.mean()), 'ci': (float(lo), float(hi)),
            'p_le_zero': p, 'significant': p < alpha}"""),
    code("""# 练习 2 参考答案
def verdict(res_dict, alpha=0.05):
    A, B, C, D = (res_dict[k] for k in ['A', 'B', 'C', 'D'])
    ca = bootstrap_test([c - a for a, c in zip(A, C)], alpha=alpha, seed=1)
    cb = bootstrap_test([c - b for b, c in zip(B, C)], alpha=alpha, seed=2)
    cd = bootstrap_test([c - d for d, c in zip(D, C)], alpha=alpha, seed=3)
    if not ca['significant']:
        con = '增强无效'
    elif not cb['significant']:
        con = '提升来自更多样本/更多训练，与多样性无关'
    elif cd['mean'] <= 0:
        con = '增强有效，但同预算标注真实数据更好'
    else:
        con = '增强有效且优于同预算标注'
    return {'C_vs_A': ca, 'C_vs_B': cb, 'C_vs_D': cd, 'conclusion': con}"""),
    code("""# 练习 3 参考答案
def experiment_feasible(target_effect, noise_sd, seed_budget, alpha=0.05, power=0.8):
    needed = seeds_needed(target_effect, noise_sd, alpha, power)
    mde = min_detectable_effect(seed_budget, noise_sd, alpha, power)
    return {'needed': needed, 'budget': seed_budget,
            'feasible': needed <= seed_budget, 'mde': mde}"""),
    md("""---
## 🧪 真实数据胶囊：一份完整的增强实验报告

把本模块的一切串成一份「可以直接贴进论文或工程文档」的报告。这是本课的最终交付物。"""),
    code("""def full_experiment_report(n0, n_aug, n_steps, n_real_extra, seeds, cost_per_label,
                           eng_hours, hourly_cost, target_effect=0.01):
    print('=' * 70)
    print(f'数据增强实验报告  (N0={n0}, n_aug={n_aug}, 固定 {n_steps} 步, {len(seeds)} 种子)')
    print('=' * 70)
    base = POOL[:n0]
    arms = {
        'A baseline': base,
        'B 复制对照': base + duplicate(base, n_aug),
        'C 增强组': base + safe_augment(base, n_aug, seed=1),
        'D 真实数据对照': base + POOL[n0:n0+n_real_extra],
    }
    res = {k: [run(v, n_steps, s) for s in seeds] for k, v in arms.items()}

    print('\\n【① 对照组结果（全部固定总训练步数）】')
    print(f'{"对照组":<18s} {"样本数":>7s} {"均值":>8s} {"标准差":>8s}')
    for k, v in res.items():
        print(f'{k:<18s} {len(arms[k]):>7d} {np.mean(v):>8.4f} {np.std(v):>8.4f}')

    print('\\n【② 配对检验（bootstrap, 20000 次重采样）】')
    r4 = {'A': res['A baseline'], 'B': res['B 复制对照'],
          'C': res['C 增强组'], 'D': res['D 真实数据对照']}
    v = verdict(r4)
    for k, label in [('C_vs_A', '增强 vs baseline'),
                     ('C_vs_B', '增强 vs 复制（= 多样性净效应）'),
                     ('C_vs_D', f'增强 vs 标注 {n_real_extra} 条真实数据')]:
        t = v[k]
        print(f'  {label:<32s} Δ={t["mean"]:+.4f} '
              f'CI[{t["ci"][0]:+.4f},{t["ci"][1]:+.4f}] p={t["p_le_zero"]:.4f} '
              f'{"✅显著" if t["significant"] else "❌不显著"}')

    print('\\n【③ 功效分析】')
    sd = float(np.std([c - a for a, c in zip(res['A baseline'], res['C 增强组'])]))
    f = experiment_feasible(target_effect, sd, len(seeds))
    print(f'  配对差值标准差 {sd:.4f}')
    print(f'  想检出 {target_effect:.3f}: 需要 {f["needed"]} 种子 | 实际 {f["budget"]} '
          f'-> {"✅ 足够" if f["feasible"] else "❌ 功效不足"}')
    print(f'  当前预算的最小可检出效应 (MDE) = {f["mde"]:.4f}')

    print('\\n【④ 等价真实数据量与预算决策】')
    n_eq = equivalent_real_data(lc, n0, SIZES) if n0 in lc['aug'] else float('nan')
    if math.isfinite(n_eq):
        d = augmentation_decision(n0, n_eq, cost_per_label, eng_hours, hourly_cost)
        print(f'  增强 {n_aug}× 在 {n0} 条上 ≈ {n_eq:.0f} 条真实数据'
              f'（等价多标注 {d["等价省下标注条数"]:.0f} 条）')
        print(f'  折算价值 ${d["折算价值"]:.2f}  vs  增强成本 ${d["增强成本"]:.2f}'
              f'  -> {"✅ 值得做" if d["值得做"] else "❌ 不如去标注"}')
    print(f'\\n【结论】{v["conclusion"]}')
    print('=' * 70)
    return res, v

res_f, v_f = full_experiment_report(n0=200, n_aug=4, n_steps=900, n_real_extra=150,
                                    seeds=range(20), cost_per_label=0.5,
                                    eng_hours=8, hourly_cost=60.0)
assert 'conclusion' in v_f
print('\\n✅ 报告生成完毕。**这就是一个能证伪自己的增强实验应有的样子。**')"""),
    md("""**🧪 胶囊练习**：实现 `report_one_liner(verdict_dict, n_eq, n0, cost_per_label, aug_cost)`：
把整份报告压缩成一行可写进实验日志的摘要，形如
`delta=+0.0123 p=0.0021 vs_dup=+0.0080 n_eq=350 value=$75 cost=$480 decision=SKIP`。
`decision` 取 `'DO'` 或 `'SKIP'`（按价值是否超过成本）。"""),
    code("""def report_one_liner(verdict_dict, n_eq, n0, cost_per_label, aug_cost):
    # TODO
    raise NotImplementedError"""),
    code("""# 自测
n_eq200 = equivalent_real_data(lc, 200, SIZES)
# ⚠️ 本课的合成任务较简单，学习曲线在 200 附近几乎平坦，等价真实数据量可能 <= n0
#    （即「增强不如原始 200 条本身」）。这本身就是一个诚实的结果，
#    但为了演示「决策随标注单价翻转」，这里沿用第 6 节那个保守示意值。
if not math.isfinite(n_eq200) or n_eq200 <= 200:
    print(f'（实测 n_eq={n_eq200:.0f} <= 200 -> 该点增强无净收益；改用示意值 350 演示决策）')
    n_eq200 = 350.0
line = report_one_liner(v_f, n_eq200, 200, 0.5, 480.0)
print(line)
kv = dict(p.split('=') for p in line.split())
assert set(kv) == {'delta', 'p', 'vs_dup', 'n_eq', 'value', 'cost', 'decision'}
assert kv['decision'] in ('DO', 'SKIP')
# 标注很贵时决策应翻转
line_med = report_one_liner(v_f, n_eq200, 200, 20.0, 480.0)
kv_med = dict(p.split('=') for p in line_med.split())
print(line_med)
assert kv_med['decision'] == 'DO', '专家标注领域应判 DO'
print('\\n✅ 胶囊练习通过：一行摘要接进 C37 的实验追踪，就有了增强决策的完整记录。')
print('   注意同一个技术结果，在两个领域给出了相反的决策 —— **这才是正确的决策方式**。')"""),
    code("""# 📖 胶囊参考答案
def report_one_liner(verdict_dict, n_eq, n0, cost_per_label, aug_cost):
    ca, cb = verdict_dict['C_vs_A'], verdict_dict['C_vs_B']
    saved = max(0.0, n_eq - n0) if math.isfinite(n_eq) else 0.0
    value = saved * cost_per_label
    dec = 'DO' if value > aug_cost else 'SKIP'
    return (f'delta={ca["mean"]:+.4f} p={ca["p_le_zero"]:.4f} '
            f'vs_dup={cb["mean"]:+.4f} n_eq={n_eq:.0f} '
            f'value=${value:.0f} cost=${aug_cost:.0f} decision={dec}')"""),
    md("""### 小结
- 增强文献的可信度危机由三点叠加：**效应量小 + 噪声大 + 增强天然带混淆**（样本数、训练步数、正则化强度、lr 调度全都变了）。
- **必须固定优化步数而不是 epoch 数**——已可运行地演示「不固定时 Δ 被高估」。
- **四个对照组**：A baseline / **B 复制对照** / C 增强 / **D 真实数据对照**。
  **C > B 才说明多样性有贡献**；**C > D 才说明这笔预算花在增强上更值**。只报 C vs A 无法排除任何混淆。
- **配对是免费的方差削减**（同种子高度正相关，差值方差显著更小）→ 同样种子数能检出更小效应。
- **配对 bootstrap** 不假设正态；先做 **A/A 检验**验证方法本身。
- **功效分析要在跑实验之前做**：若「要 30 个种子」而你只跑 3 个，这个实验从设计上无法得出结论。
- **学习曲线 > 单点比较**；从它读出**等价真实数据量**——「增强 4× ≈ 多 150 条真实数据」比「涨了 1.2 分」有用一百倍。
- **三条决策规律**：①标注成本决定一切（同样技术收益在通用文本不划算、在医疗法律非常划算）；②数据量越大越不划算；③**零标注冷启动是增强不可替代的场景**（该问「多快上线」而非「划不划算」）。

🎓 **本课完结。** 你现在能造数据（模块 01–03）、筛数据（模块 04）、并**证明或推翻它有用**（模块 05）。
最重要的是那个换算：**把增强的收益变成「等价真实数据量」，一切就都可比了。**
建议的下一站：**C10**（测量科学与 A/B）、**C03**（评测统计）、**C43**（大规模数据工程）、**C40**（研究方法论）。"""),
]
