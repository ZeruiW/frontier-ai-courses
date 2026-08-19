# -*- coding: utf-8 -*-
"""C65 模块 03 · 权衡与决策（结构化问题求解与面试沟通）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（四步框架，尤其「收敛与权衡」这一步）与模块 02（诊断与归因，"
                 "本模块承接「诊断出根因之后，几个候选方案怎么选」）；理解基本的加权求和与排序即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_tradeoffs_decisions.ipynb'
                       '（多维加权打分器 + 权重扰动敏感性分析 / 帕累托前沿计算 / '
                       '预算约束下贪心与背包最优的对比 / 三种不确定性决策准则的分歧演示 / 可逆决策速度与沉没成本模拟）'),
    ("核心参考", "本课程 C53 模块 05（帕累托前沿与被支配判断的技术细节，本课只讲面试组织表达）· "
                 "C57 模块 05（预算下方案组合的贪心与背包，本课复用其两步法结论）· "
                 "von Neumann &amp; Morgenstern 期望效用理论 · L. J. Savage《The Foundations of Statistics》"
                 "（minimax regret 的出处）· Jeff Bezos 致股东信（Type 1 / Type 2 决策速度）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-tradeoff-tests", "权衡题在面试里到底考什么", "".join([
        P("权衡与决策题的典型开场是：<strong>「提升检出率还是降低误检率，你会先做哪个？」</strong>"
          "「预算只够做一件事，模型精度、延迟、可解释性你会先保哪个？」「如果只能改进一个指标，你选哪个？」"
          "这类题<strong>没有唯一正确答案</strong>——面试官通常自己也没有标准答案，"
          "无论你选 A 还是选 B，紧接着的追问几乎必然是「那你放弃的是什么？」"),
        CALLOUT("intuition", "权衡题评的不是「选哪个」，是<strong>选择背后有没有一套显式的、可以被审查的推理链</strong>。"
                             "一个说「我选 A，因为 A 更好」的候选人，和一个说「我列了四个维度、按这样定权重、"
                             "打分之后 A 领先，但我要说清楚选 A 意味着放弃了 B 在某个维度上的优势，"
                             "而这个放弃在什么条件下会让我改变主意」的候选人，传达的信号完全不是一个量级的。"),
        P("这正是<strong>取舍显式化</strong>的四步：<span class=\"term\">列维度</span>（这个决策涉及哪几个互相独立的考量）→"
          "<span class=\"term\">定权重</span>（哪个考量更重要，为什么）→<span class=\"term\">打分</span>（每个候选在每个维度上打多少分）→"
          "<strong>说清放弃了什么</strong>（选中的方案在哪个维度上不是最优，这个代价能不能接受）。"
          "最后一步几乎总是被省略——但恰恰是它，把一次「选择」变成一次「决策」。"),
        TABLE(["失败模式", "具体表现", "面试官的解读"], [
            ["只给结论不给维度", "「我选 A 因为 A 更好」", "没有维度分解，无法判断这个判断是否可迁移到别的场景"],
            ["权重是拍脑袋、且看着候选分数临时调", "先看到 A 在某维度领先，才把那个维度的权重调高", "这是<strong>倒果为因</strong>——本节和下一节都会专门拆穿这个坑"],
            ["打分不统一量纲就直接相加", "把「延迟 8ms」和「准确率 92%」这两个数字直接加权求和", "呼应下一节：不同单位的分数必须先归一化才能合成一个数字"],
            ["选完不说放弃了什么", "「所以我们选 B」，然后停在这里", "面试官几乎一定会追问「那 A 更好的地方怎么办」——不提前说清楚，显得没想全"],
        ]),
        P("放到 TSR 场景具体化：<strong>「提升检出率还是降低误检率，你会先做哪个？」</strong>是一道典型的"
          "<span class=\"term\">代价不对称</span>权衡题（技术细节见 C55-05 的工作点选择）——"
          "本课不重复代价矩阵怎么算，只讲这道题在面试里应该<em>怎么组织回答</em>：先问清楚场景（停车让行漏检和广告牌误检的代价完全不是一个量级）、"
          "再显式说出你的权重来自哪里（安全代价 vs 用户体验代价），最后主动说「这个选择意味着我们会容忍更多的哪一类错误」。"),
        DUAL(
            "直白地说：面试官问「你选 A 还是 B」，他其实在问「把你脑子里选择的过程倒出来给我看」。"
            "选错了 A/B 本身通常不扣多少分，<strong>倒不出这个过程</strong>才是真正的减分项。",
            "更严谨地说，这是要求把一个隐式的<span class=\"term\">效用函数</span>（utility function）显式化——"
            "大多数人脑子里确实有一套权衡直觉，但从来没有把它写成「维度 + 权重 + 打分公式」的形式过。"
            "本模块剩下的部分，就是教你怎么把这套隐式直觉快速显式化，并且在显式化之后<strong>检验它是否经得起扰动</strong>"
            "（下下节的权重敏感性分析）——这一步是绝大多数候选人从没做过的，也是本课最想让你带走的方法。",
        ),
    ])),

    # ============================================================== 2
    ("weighted-scoring", "加权打分法：完整流程与三个常见陷阱", "".join([
        P("加权打分法是把「取舍显式化」四步落到纸面上最直接的工具。它的公式很简单："),
        MATH("\\text{Score}(a) \\;=\\; \\sum_i w_i \\cdot s_i(a), \\qquad \\sum_i w_i = 1"),
        P("但简单的公式最容易被用错。三个最常见的陷阱，逐一拆开："),
        H3("陷阱一：维度不正交，重复计分同一属性"),
        P("如果「模型精度」和「用户满意度」两个维度本质上高度相关（精度高用户自然满意），"
          "同时把两者都设高权重，等于把同一个底层因素<strong>算了两遍</strong>，"
          "这个候选方案会被系统性高估。<em>列维度时先问一句：这个维度和已经列出的维度是不是在测同一件事？</em>"),
        H3("陷阱二：权重看着分数临时调（倒果为因）"),
        P("正确的顺序是：<strong>先定权重，再打分，最后才看总分排名</strong>。"
          "如果颠倒过来——先看到某个方案在总分上领先，再回头把它领先的那个维度的权重调高——"
          "打分表就从「决策工具」变成了「合理化工具」，面试官如果追问「你的权重是怎么定的」，"
          "答不出独立于候选方案的理由，这个陷阱立刻会被识破。"),
        H3("陷阱三：不同量纲直接相加"),
        P("「延迟 8 毫秒」和「准确率 92%」不能直接乘权重相加——数值范围不一样，"
          "小的那个维度会被数值大的维度淹没。正确做法是先把每个维度<span class=\"term\">归一化</span>到同一个量纲（通常是 [0,1]），"
          "常用的是<span class=\"term\">最小-最大归一化</span>："),
        MATH("\\tilde{s}_i(a) \\;=\\; \\frac{s_i(a) - \\min_b s_i(b)}{\\max_b s_i(b) - \\min_b s_i(b)}"),
        TABLE(["步骤", "该做的事", "常见错误"], [
            ["① 列维度", "列出互相独立、覆盖决策关心的所有考量的维度", "维度重叠计分；维度不全，漏掉一个隐含但重要的考量（比如「可维护性」）"],
            ["② 定权重", "根据业务/安全优先级独立于候选方案地定权重", "先看候选分数再定权重（倒果为因）"],
            ["③ 打分", "每个候选每个维度打分，先归一化到同一量纲", "跨单位直接相加；打分时受到「我更想选哪个」的主观偏好影响"],
            ["④ 说清放弃了什么", "指出总分最高的方案在哪个维度不是最优，代价多大", "选完就停，不主动交代代价——几乎必然被追问"],
        ]),
        DUAL(
            "怎么在面试白板上快速做这件事？画一个「方案 × 维度」的表格，维度那一行先写权重，"
            "每个格子打分之后按列求加权和，最后一句话补上「X 方案分数最高，但它在 Y 维度上比 Z 方案差，"
            "这个代价我们能接受是因为……」。",
            "更严谨地说，加权打分法本质是把一个多维决策问题<strong>坍缩成一个标量</strong>（scalarization），"
            "这个坍缩本身是有信息损失的——它假设各维度之间可以线性替代（一个维度的收益可以补偿另一个维度的损失）。"
            "<em>这个假设并不总是成立</em>：安全类维度往往是「一票否决」而非「可被其他维度补偿」，"
            "遇到这种情况，正确做法是先做硬约束过滤，再对剩下的候选做加权打分——这正是下面几节要展开的内容。",
        ),
    ])),

    # ============================================================== 3
    ("sensitivity-analysis", "权重扰动敏感性分析：最有说服力的一步", "".join([
        P("加权打分法给出的排名，永远是<strong>相对于一组特定权重</strong>的排名。"
          "而权重几乎总是主观估计的产物——换一个人来定，权重可能上下浮动 20%–30%。"
          "如果排名结果稍微改一下权重就翻转，这个「A 比 B 好」的结论就<strong>不稳健</strong>，"
          "只是恰好在你选的这组权重下成立而已。<strong>敏感性分析要回答的问题是：结论对权重的依赖程度有多高？</strong>"),
        ASCII("""权重空间里的"决策边界"示意（二维简化：w1 沿横轴，w2=1-w1 沿纵轴）

  w2
  1.0 ┤ 方案 B 更优
      │        ╲
      │         ╲←── 决策边界：score_A(w) = score_B(w)
      │          ╲
      │  方案 A 更优 ╲
  0.0 └──────────────╲──── w1
      0.0                  1.0

  原始权重落在边界"哪一侧"、离边界"有多远"，
  直接决定了小幅扰动会不会让排名翻转到边界另一侧。"""),
        P("方法很直接：在原始权重附近加入随机扰动（比如按 ±30% 的相对幅度浮动）、重新归一化使权重仍然求和为 1、"
          "重新打分排序，重复几千次，统计<strong>「最优方案的排名被翻转」的比例</strong>——这个比例就是结论的脆弱程度。"
          "notebook 里会跑一个真实例子：三个改进方案在扰动幅度 ±30% 下，翻转率是 <strong>4.5%</strong>；"
          "把扰动幅度加到 ±80%，翻转率涨到 <strong>26.6%</strong>——这就是「结论有多依赖权重」的量化答案。"),
        P("对照组是一个<strong>方案在所有维度上都不劣于其他方案</strong>的极端情况（帕累托意义上的支配，见下一节）："
          "notebook 会证明只要方案 E 在每个维度都优于方案 F、G，<strong>无论权重怎么扰动（只要权重仍然是正数），"
          "E 的加权总分永远不会被反超</strong>——翻转率精确为 0。这两组对照放在一起，"
          "能非常直观地说明「结论的稳健性」和「候选方案之间的结构关系」是绑在一起的。"),
        DUAL(
            "面试里怎么用？打完分不要只报「A 领先 0.6 分，所以选 A」，而要补一句"
            "「我把权重上下浮动了 30% 重新算了一遍，A 领先的结论在<em>大多数</em>情况下仍然成立，"
            "只有在权重明显偏向某个维度时才会翻转」——<strong>这一句话是整个权衡题回答里最容易让面试官眼前一亮的一句</strong>，"
            "因为它证明你知道「打分法给出的结论是有前提的」，而不是把一次打分当成绝对真理。",
            "更严谨地说，敏感性分析把「哪个方案更好」从一个<strong>点估计</strong>变成一个<strong>区间估计加置信程度</strong>："
            "翻转率越低，说明原始权重距离决策边界越远，结论越稳健；翻转率高，说明原始权重恰好落在边界附近，"
            "此时更诚实的回答是「这两个方案在合理的权重范围内难分伯仲，真正的决定权应该交给对权重更有把握的人（比如产品或安全团队）」。",
        ),
        CALLOUT("danger", "<strong>反面例子</strong>：如果翻转率很高（比如超过 20%），却依然用非常笃定的语气汇报结论"
                          "「毫无疑问应该选 A」，这在面试里是一个危险信号——它说明你要么没做敏感性检验，"
                          "要么做了但选择性忽略了不利的结果。<em>诚实地说「这个结论对权重敏感，我建议先明确权重来源再拍板」，"
                          "比一个虚假的自信更有说服力。</em>"),
    ])),

    # ============================================================== 4
    ("pareto-dominance", "帕累托前沿与「被支配」的判断", "".join([
        P("加权打分法需要先定权重，但有些时候你根本不需要权重就能排除掉一批方案——"
          "如果方案 X <strong>在每一个维度上都不比</strong>方案 Y 差，且至少有一个维度<strong>更好</strong>，"
          "那么 Y 就是<span class=\"term\">被支配</span>（dominated）的，<strong>无论权重怎么定，都不应该选 Y</strong>。"
          "这一判断的技术细节（延迟-精度权衡曲线的完整推导）见 C53-05，本节只讲它在权衡题里怎么组织表达。"),
        ASCII("""收益（benefit）
  6 ┤                                    ● f
    │
  5 ┤                    ● d      ○ e
    │
  3 ┤        ● b
    │
  2 ┤  ● a         ○ c
    └──┴────┴────┴────┴────┴────┴──► 成本（cost）
       1    2    3    4    5

  ● 在帕累托前沿上（a/b/d/f）    ○ 被支配（c 被 b 支配；e 被 d 支配）
  c 和 b 成本相同但收益更低 —— 直接淘汰
  e 比 d 贵却收益相同 —— 直接淘汰"""),
        P("上面这组候选修复方案里，<code>c</code> 和 <code>b</code> 成本相同，但 <code>b</code> 收益更高，"
          "<code>c</code> 被<strong>无条件淘汰</strong>；<code>e</code> 比 <code>d</code> 更贵却收益相同，"
          "<code>e</code> 同样被淘汰。剩下 <code>a/b/d/f</code> 构成前沿——<strong>这一步筛选完全不需要定权重</strong>，"
          "是加权打分之前免费的第一道过滤。"),
        TABLE(["方法", "需要权重吗", "能得到什么", "局限"], [
            ["帕累托前沿筛选", "<strong>不需要</strong>", "淘汰掉「无论怎么权衡都不该选」的方案", "前沿上剩下的方案之间仍然分不出高下，只是把候选集缩小了"],
            ["加权打分法", "需要", "在前沿基础上给出一个具体排名", "权重主观，需要敏感性分析验证稳健性（见上一节）"],
        ]),
        DUAL(
            "面试里正确的顺序是<strong>先筛后打分</strong>：先用帕累托前沿把候选集从「所有方案」缩小到「前沿上的方案」，"
            "这一步不需要辩护权重、没有争议；再在缩小后的候选集里用加权打分法排出最终名次，"
            "这时候权重的争议只留给真正难分伯仲的几个前沿方案，而不是浪费在一开始就该被淘汰的方案上。",
            "呼应 C53-05 的三步法：①用硬约束过滤掉不可行的方案，②在可行集里画帕累托前沿，"
            "③只在前沿上按工程维度加权排序。<strong>这个三步法本身就是一句可以直接在面试里说出来的方法论</strong>，"
            "比不假思索地对所有候选方案一次性加权打分要高一个层次——它显式地把「无争议的淘汰」和「有争议的取舍」分开处理。",
        ),
        CALLOUT("intuition", "记住一句话：<strong>「被支配」不需要权重就能证明，「排第几」才需要权重。</strong>"
                             "面试里被问「这几个方案你怎么选」时，先说一句「我先看有没有谁被别的方案全面碾压，"
                             "这些可以先排除，不需要争论权重」，能立刻显得比直接扎进加权打分更专业。"),
    ])),

    # ============================================================== 5
    ("budget-constrained", "约束优化视角：预算下的最优组合", "".join([
        P("权衡题经常带着一个硬约束：「预算/算力/人力只够做其中一部分，你怎么组合？」"
          "这本质上是一个<span class=\"term\">背包问题</span>（技术细节与「先取免费午餐、再做背包」的两步法见 C57-05，"
          "本节讲的是它在权衡题里最容易被忽略的一个坑：<strong>按性价比贪心排序，不等于拿到最优组合</strong>。"),
        CODE("""items = [('X', cost=10, value=60), ('Y', cost=20, value=100), ('Z', cost=30, value=120)]
budget = 50

贪心（按 value/cost 比排序）：X(比6.0) > Y(比5.0) > Z(比4.0)
  依次拿 X(10,60) → 拿 Y(20,100) → 剩余预算 20，拿不下 Z(30)
  贪心组合 = {X, Y}，成本 30，总收益 160

真正最优（0/1 背包 DP 枚举所有组合）：
  {Y, Z} 成本 20+30=50（刚好用满预算），总收益 100+120 = 220

贪心以为自己找到了最优解，实际上比真正最优少了 60（27%）"""),
        P("为什么会这样？贪心的问题在于它<strong>贪心地拿走了性价比最高的小项目</strong>，"
          "却挤占了预算，导致一个性价比稍低、但恰好能把预算用满的大项目组合（Y+Z）永远进不了候选——"
          "<strong>0/1 背包问题里，「性价比最高」和「组合起来最优」不是一回事</strong>，"
          "这一点在只有几个候选方案时用动态规划精确求解完全负担得起。"),
        TABLE(["方法", "复杂度", "结果质量", "面试里怎么用"], [
            ["贪心（按性价比排序）", "$O(n\\log n)$", "通常接近最优，但<strong>不保证</strong>最优，可能因为「预算刚好用不满」而留下缺口", "候选方案很多（几十上百个）时的默认选择，说清楚它是近似解"],
            ["0/1 背包动态规划", "$O(n \\times \\text{budget})$", "<strong>保证最优</strong>", "候选方案数量少（面试里通常几个到十几个），预算是离散小数值时，直接上 DP 精确求解，比贪心更有说服力"],
        ]),
        DUAL(
            "怎么在面试里讲这件事？先给贪心方案（快、可解释、通常够用），再主动说"
            "「如果候选方案不多，我会用背包 DP 精确验证一下贪心解和最优解差多少——这里差了 27%，"
            "说明这个场景下贪心不够用，应该上精确解」。<strong>主动去验证自己给出的近似解到底多近似，是这道题里最加分的一步。</strong>",
            "更严谨地说，贪心算法对 0/1 背包问题<strong>没有最坏情况的近似比保证</strong>——"
            "可以构造出贪心解只有最优解一半甚至更差的例子。这与<em>分数背包</em>（可以切分物品）不同，"
            "后者贪心恰好是最优解。<strong>判断该用哪种视角的第一个问题是「候选方案能不能被拆分」</strong>——"
            "TSR 里「要不要上某个数据增强方法」是不可分的 0/1 决策，而「给某类样本重采样加权到什么比例」则更接近连续可分的资源分配。",
        ),
        CALLOUT("warn", "<strong>不要把贪心当成理所当然的答案</strong>——很多候选人一提到「预算约束下选方案」就直接说"
                        "「按性价比排序拿到预算用完为止」，却从没想过这个解可能不是最优的。"
                        "<em>面试官如果追问「你怎么知道这是最优的」，答不出「我没验证，也可以用 DP 精确算」，"
                        "会显得对这个问题理解不深。</em>"),
    ])),

    # ============================================================== 6
    ("uncertainty-decisions", "不确定性下的决策：期望效用 / 最坏情况 / 后悔最小化", "".join([
        P("到目前为止的打分都假设「每个方案在每个维度的表现是确定的」。但很多真实决策面对的是"
          "<strong>不同未来场景下表现不同</strong>的方案——要不要为极端天气单独训练一个专用小模型，"
          "取决于「极端天气出现的概率」和「专用模型在常见天气下的机会成本」。这类问题有三种经典决策准则，"
          "<strong>它们可能会给出完全不同的答案，而这个分歧本身就是一个值得在面试里主动指出的洞察</strong>。"),
        MATH("\\text{期望效用: } EU(a) = \\sum_s p(s)\\, u(a,s) \\qquad\\quad \\text{最坏情况: } a^\\star = \\arg\\max_a \\min_s u(a,s)"),
        MATH("\\text{后悔: } \\text{regret}(a,s) = \\max_{a'} u(a',s) - u(a,s) \\qquad \\text{后悔最小化: } a^\\star = \\arg\\min_a \\max_s \\text{regret}(a,s)"),
        TABLE(["准则", "核心思想", "适用条件", "弱点"], [
            ["<strong>期望效用</strong>", "按概率加权平均，长期跑下来这样选收益最高", "对各场景发生概率有相对靠谱的估计，且决策可以重复很多次分摊风险", "单次决策里，小概率的极端场景可能被平均掉、代价被低估"],
            ["<strong>最坏情况</strong>（maximin）", "只关心每个方案最差能有多差，选「最差情况下最不差」的那个", "后果极端、不可挽回、或者根本没有靠谱的概率估计", "过度保守——为了防范小概率的极端场景，牺牲了绝大多数正常场景下的收益"],
            ["<strong>后悔最小化</strong>（minimax regret）", "选一个「不管未来是哪种场景，都不会后悔太多」的方案", "不同方案在不同场景下表现差异很大，想要一个「稳健但不极端保守」的折中", "「后悔」的定义依赖于「事后才知道的最优选择」，计算上比前两者复杂"],
        ]),
        P("举一个 TSR 场景的具体例子：常见天气发生概率 90%，极端天气（暴雨/暴雪）发生概率 10%。"
          "「专用模型」在常见天气下效用 6、极端天气下效用 9；「通用模型」常见天气 8、极端天气 3；「不做」常见天气 9、极端天气 0。"
          "notebook 会算出：<strong>期望效用选「不做」（8.1 分最高），最坏情况和后悔最小化都选「专用模型」</strong>"
          "——三选二地分裂成两派，且期望效用和另外两者的分歧恰好反映了「概率占优 vs 极端后果」这个真实的张力。"),
        DUAL(
            "怎么在面试里用？如果面试官问「你会怎么决策」，先说「这取决于我用哪种准则」，"
            "然后把三种准则各自的答案都算一遍摆出来——<strong>「三种准则分歧」这件事本身，"
            "就足以说明这不是一个可以靠直觉一步到位的问题，需要先确认公司/团队对风险的容忍态度</strong>。",
            "更严谨地说，选哪种准则本质上是在回答「这个决策能不能被重复很多次、后果是否可挽回」——"
            "这正好和下一节「可逆 vs 不可逆决策」是同一个问题的两个角度：可逆、可重复的决策适合用期望效用；"
            "不可逆、后果极端的决策更适合用最坏情况或后悔最小化兜底。",
        ),
        CALLOUT("intuition", "记住这个具体例子的教训：<strong>「按最可能发生的情况优化」和「按最坏可能发生的情况兜底」"
                             "经常会给出相反的答案，两者都不是错的，区别只在于你愿意为小概率的极端场景付出多少常规场景下的代价。</strong>"),
    ])),

    # ============================================================== 7
    ("reversibility", "可逆 vs 不可逆决策：用不同的速度做决定", "".join([
        P("并不是所有决策都值得花同样多的精力去权衡。Jeff Bezos 在亚马逊股东信里提出的"
          "<span class=\"term\">Type 1 / Type 2 decisions</span>（单向门 / 双向门决策）区分，"
          "是面试里组织「怎么排优先级、怎么分配决策精力」这类问题最好用的框架之一：<strong>可逆决策</strong>"
          "（走错了能轻松退回来）应该<em>快</em>做、允许直觉主导；<strong>不可逆决策</strong>（撤回代价极高甚至不可能）"
          "应该<em>慢</em>做、多方核实、主动留退路。"),
        TABLE(["决策", "可逆性", "建议速度", "理由"], [
            ["调整置信度阈值（线上可回滚）", "可逆", "快——先小流量灰度，不满意立刻改回来", "撤回成本几乎为零，试错本身就是最快的信息获取方式"],
            ["更换标注供应商", "基本可逆", "较快——签短期合同，留出评估期", "换回来有沟通成本，但不构成技术锁定"],
            ["选择车端推理芯片/部署平台", "<strong>几乎不可逆</strong>", "慢——多方案 POC、多团队会签、留架构层面的可迁移性", "一旦大规模量产，锁定的是数年的工具链、算子支持、团队技能栈（呼应 C60 的部署一致性）"],
            ["删除历史训练数据快照", "不可逆", "慢——先归档降级存储，观察期后才真正删除", "一旦真删除，任何后续排查（呼应模块 02 的血缘追溯，见 C63-02）都失去了物证"],
        ]),
        DUAL(
            "直白地说：可逆的事，先做了再说，做错了改回来的成本比纠结的时间成本还低；"
            "不可逆的事，宁可多花一周开会，也不要为了「显得果断」仓促拍板——"
            "<strong>决策速度本身应该是一个被显式判断的变量，而不是一个人的固定风格。</strong>",
            "更严谨地说，这个框架把「决策精力」的分配变成了 <em>可逆性 × 影响范围</em> 的函数——"
            "notebook 会实现一个简化的打分：不可逆决策的建议决策精力是可逆决策的数倍（在相同影响范围下）。"
            "<strong>面试里最容易失分的组合，是把一个不可逆的高风险决策，用可逆决策的速度和随意程度去处理。</strong>",
        ),
        H3("沉没成本谬误与锚定效应"),
        P("<span class=\"term\">沉没成本谬误</span>（sunk cost fallacy）：已经投入的成本（两个月的开发时间、"
          "已经买的算力）<strong>不应该影响面向未来的选择</strong>——决策应该只看「继续」和「切换」两条路各自<em>未来</em>的收益，"
          "过去投入了多少不该改变这个比较。notebook 会用一个显式对比证明：理性决策函数在任何沉没成本下给出同一个答案，"
          "而「把沉没成本按比例折算进当前方案分数」的偏误决策函数，会在沉没成本足够大时把结论拖着不肯换——"
          "这正是「都已经投入这么久了，不能说换就换」这句话背后的认知偏误。"),
        P("<span class=\"term\">锚定效应</span>（anchoring）：面试官先给出的第一个数字（比如「假设延迟预算是 10ms」）"
          "会不成比例地影响你后续所有的判断，即使这个数字本身值得重新审视。<strong>正确的应对不是无视它，"
          "而是显式确认它</strong>：「10ms 是硬约束还是一个初始假设？如果后面发现某个方案 11ms 但收益大很多，"
          "这个数字是否可以商量？」——把锚点从「默认接受」变成「显式确认的前提」，本身就是一种去锚定。"),
        CALLOUT("warn", "<strong>沉没成本谬误在项目复盘类面试题里极其高发</strong>：「已经投入两个月的方案，"
                        "现在发现另一个架构明显更好，你会换吗？」——正确答案的核心永远是「看两条路<em>未来</em>的成本收益对比，"
                        "而不是已经花了多少」，但很多候选人会不自觉地把「不想让前面的投入白费」当成理由说出口，"
                        "这在面试官听来是一个明确的减分信号。"),
    ])),

    # ============================================================== 8
    ("one-choice-framework", "「如果只能选一个」的回答框架", "".join([
        P("面试官经常会把权衡题逼到极限：「如果只能改进一个指标，你选哪个？」「如果只让你保留一个功能，你留哪个？」"
          "这类问题的陷阱在于——<strong>候选人会本能地想给一个「都很重要，很难取舍」的模糊回答来逃避真正做选择</strong>，"
          "而这恰恰是最大的失分点：题目就是在测试你敢不敢真的排出优先级。"),
        OL([
            "<strong>先给出明确的选择</strong>：不要用「这要看情况」开头。一句话说出你选哪个。",
            "<strong>给出一个独立于当前候选的决策准则</strong>：「我的判断标准是安全 &gt; 用户体验 &gt; 开发效率，"
            "这个类别涉及的是漏检安全类标志，所以我优先选它」——准则要能推广到其他类似问题，而不是为这一题量身定制。",
            "<strong>主动说清放弃了什么，以及在什么条件下会改变选择</strong>：「这意味着我们短期内不改善某类别的误检率，"
            "如果后续发现误检率带来的用户投诉超过某个阈值，我会重新评估这个优先级」——"
            "这一步给了一个明确的<span class=\"term\">反悔条件</span>（escape hatch），呼应上一节「可逆决策」的思路："
            "把一次看似不可逆的口头承诺，变成一个附带触发条件的可逆决策。",
        ]),
        P("<strong>「你会怎么排优先级」</strong>这类更开放的问题，用「影响 × 成本 × 不确定性」三个维度打分排序即可"
          "（完整的澄清与收敛流程见 C65-04，本节不重复），本节只强调一点：<strong>排优先级题里，"
          "「暂时无法证明哪个更好」不是拒绝排序的理由</strong>——用当下最好的估计排出一个顺序，"
          "并说明这个顺序会随什么新信息改变，永远优于不排。"),
        DUAL(
            "直白地说：「只能选一个」类问题，面试官要看的不是你选得对不对，是你<strong>敢不敢真的选，"
            "以及选完之后能不能面不改色地说出代价</strong>。",
            "更严谨地说，这类问题是在检验你能否把一个多准则决策问题坍缩成<strong>一个可执行的排序</strong>，"
            "而不是停留在「都重要」的多维描述里。工程组织的资源永远是有限的，"
            "一个团队如果拿不出一个哪怕不完美的优先级顺序，实际执行时反而会陷入「什么都做一点、什么都做不好」的更差结果。",
        ),
        CALLOUT("danger", "<strong>「都很重要，不能只选一个」是这类题里最危险的回答</strong>——"
                          "它听起来像是在展示全面性，实际传达的信息是「我不敢做决定」或者「我没有一套可以排出优先级的准则」。"
                          "<em>哪怕你的真实判断确实是「两者旗鼓相当」，正确的说法也是"
                          "「我倾向于 A，但承认这是个接近的判断，理由是……」——给出一个方向，而不是拒绝回答。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("权衡与决策的方法论看似古老（期望效用理论已有近百年历史），但把它做成「可靠、可自动化、"
          "可对齐真实偏好」的工具，仍然有不少悬而未决的问题。"),
        UL([
            "<strong>人类的真实决策系统性偏离期望效用理论。</strong>Kahneman &amp; Tversky 的"
            "<span class=\"term\">前景理论</span>（Prospect Theory）证明人们对「损失」和「收益」的感知不对称"
            "（损失厌恶）、对小概率事件的权重会被系统性高估或低估。<em>这意味着「面试官心里的理想答案」"
            "本身可能就不是严格的期望效用最大化，而是带着这些认知偏误的直觉判断——"
            "理解这些偏误，既能帮你识别自己回答里的偏误，也能帮你理解面试官可能带着什么偏误在评估你。</em>",
            "<strong>多准则决策分析（MCDA）的权重启发式与真实偏好之间仍有差距。</strong>"
            "现实中获取「真实权重」的方法（专家打分、成对比较法 AHP、体验采样）各有各的偏差，"
            "<em>本模块的敏感性分析是一个务实的补丁——不追求得到「正确」的权重，"
            "而是检验结论对权重的依赖程度，这本身已经是工业界常用的稳健性检验思路。</em>",
            "<strong>LLM 辅助生成决策维度的可靠性还缺少系统评估。</strong>让大模型帮你列出「这个决策应该考虑哪些维度」"
            "正在变得常见，但模型给出的维度列表本身可能不完整、不正交，"
            "<em>目前还没有成熟的方法去验证一份 AI 生成的维度清单是否覆盖了真正重要的考量——"
            "这本身也是一个「元决策」问题：你要不要相信这份维度清单本身就够全。</em>",
            "<strong>不可逆决策的「留退路」设计缺少系统化的工程方法。</strong>怎么在一个几乎不可逆的架构决策里"
            "预留最大的可迁移性（比如芯片平台选型时的抽象层设计），目前主要靠经验，"
            "还没有一套通用的「可逆性工程」方法论。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Daniel Kahneman &amp; Amos Tversky, "
                         "<em>Prospect Theory: An Analysis of Decision under Risk</em>（Econometrica, 1979）——"
                         "行为经济学证明人类决策系统性偏离期望效用理论的奠基之作。"
                         "<strong>★</strong> L. J. Savage, <em>The Foundations of Statistics</em>（1954）——"
                         "minimax regret 准则的理论出处。"
                         "<strong>★</strong> Jeff Bezos, 1997 年致亚马逊股东信——"
                         "Type 1 / Type 2 决策速度框架的原始表述，工业界至今在用的可逆性分级思路。</p>"
                         "<p>相邻课程：<strong>C53 模块 05</strong>（帕累托前沿与延迟-精度权衡的技术细节，本课只讲面试表达）、"
                         "<strong>C57 模块 05</strong>（预算约束下的贪心与背包最优，本课复用其两步法结论）、"
                         "<strong>C65 模块 02</strong>（诊断与归因，本模块承接其后的方案选择）、"
                         "<strong>C65 模块 04</strong>（模糊问题与优先级排序，本节「只能选一个」框架与之衔接）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · 权衡与决策（加权打分 / 权重扰动敏感性分析 / 帕累托前沿 / 贪心vs背包 / 不确定性决策准则 / 沉没成本）

目标：把「选 A 还是选 B」从一次拍脑袋，变成一套**可以运行、可以断言的决策方法论**。

本 notebook 你会亲手实现：
1. **多维加权打分器** —— 列维度、定权重、归一化、打分排序
2. **权重扰动敏感性分析** —— 权重扰动会不会翻转结论，这是本模块最有说服力的一步
3. **帕累托前沿计算** —— 不需要权重就能淘汰掉「被支配」的方案
4. **预算约束下的方案组合** —— 贪心 vs 0/1 背包最优，量化贪心到底差多少
5. **三种不确定性决策准则** —— 期望效用 / 最坏情况 / 后悔最小化在同一问题上的分歧
6. **可逆决策速度与沉没成本模拟** —— 用代码证明"已经投入多少"不该影响面向未来的选择

> 心智模型：**权衡题考的不是选哪个，是你选择背后那条推理链能不能被摊开来审查。**"""),

    md("""## 1 · 多维加权打分器：列维度 → 定权重 → 打分

三个改进方案在四个维度上的原始打分（1-10，越高越好），按权重加权求和排序。"""),

    code("""def weighted_score(scores, weights):
    \"\"\"score = sum(w_i * s_i)，要求各维度已经统一量纲（见下面的归一化演示）。\"\"\"
    return sum(s * w for s, w in zip(scores, weights))

def rank_options(options, weights):
    \"\"\"options: {方案名: [各维度打分, ...]}  ->  (按分数降序的名字列表, {名字: 分数})\"\"\"
    scored = {name: weighted_score(scores, weights) for name, scores in options.items()}
    return sorted(scored, key=lambda k: -scored[k]), scored

DIMENSIONS = ['准确率提升', '实现成本(已反向,越高越省事)', '维护复杂度(已反向,越高越省事)', '延迟影响(已反向,越高越省事)']
OPTIONS = {
    '方案A：升级 backbone':   [9, 3, 4, 5],
    '方案B：加一层后处理规则': [5, 8, 7, 8],
    '方案C：扩充训练数据':     [6, 6, 6, 6],
}
WEIGHTS = [0.4, 0.2, 0.15, 0.25]
assert abs(sum(WEIGHTS) - 1.0) < 1e-9

order, scored = rank_options(OPTIONS, WEIGHTS)
for name in order:
    print(f'{name:<24} {scored[name]:.2f} 分')

assert order[0] == '方案B：加一层后处理规则'
assert abs(scored['方案B：加一层后处理规则'] - 6.65) < 1e-9
assert abs(scored['方案A：升级 backbone'] - 6.05) < 1e-9
assert abs(scored['方案C：扩充训练数据'] - 6.00) < 1e-9
print(f\"\\n✅ 方案B领先方案A {scored['方案B：加一层后处理规则']-scored['方案A：升级 backbone']:.2f} 分\"
      f\"，领先方案C {scored['方案B：加一层后处理规则']-scored['方案C：扩充训练数据']:.2f} 分——\")
print('   但这个领先幅度稳不稳健，取决于权重本身有多可信，这正是下一节要检验的。')"""),

    md("""## 2 · 归一化：不同量纲的分数不能直接相加

如果原始打分不是统一的 1-10 量表，而是"延迟(ms，越小越好)"和"准确率(%，越大越好)"这类真实单位，
必须先做最小-最大归一化，再套加权公式。"""),

    code("""def minmax_normalize(raw_values, higher_is_better=True):
    \"\"\"把一组原始数值归一化到 [0,1]。higher_is_better=False 时先取负数再归一化（越小原始值归一化后越接近1）。\"\"\"
    vals = [v if higher_is_better else -v for v in raw_values]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [0.5] * len(vals)          # 所有候选在这个维度上并列，归一化给中性值
    return [(v - lo) / (hi - lo) for v in vals]

# 三个方案的"真实单位"表现：延迟(ms，越小越好)，准确率提升(百分点，越大越好)
latency_ms = [12, 3, 7]          # 方案A/B/C
acc_gain_pp = [4.5, 1.2, 2.8]

norm_latency = minmax_normalize(latency_ms, higher_is_better=False)
norm_acc = minmax_normalize(acc_gain_pp, higher_is_better=True)

print('原始延迟(ms)      :', latency_ms, ' -> 归一化(越大越好):', [round(x, 3) for x in norm_latency])
print('原始准确率提升(pp):', acc_gain_pp, ' -> 归一化(越大越好):', [round(x, 3) for x in norm_acc])

assert norm_latency[1] == 1.0 and norm_latency[0] == 0.0   # 延迟最小(方案B,3ms) 归一化到1；最大(方案A,12ms) 归一化到0
assert norm_acc[0] == 1.0 and norm_acc[1] == 0.0            # 准确率提升最大(方案A) 归一化到1；最小(方案B) 归一化到0
print('\\n✅ 归一化之后，延迟和准确率提升才能在同一个 [0,1] 量纲上被加权相加，直接把 12ms 和 4.5pp 相加是没有意义的。')"""),

    md("""## 3 · 权重扰动敏感性分析：结论稳不稳健

在原始权重附近按相对比例随机扰动、重新归一化、重新打分排序，重复几千次，
统计"最优方案被翻转"的比例——这是本模块最有说服力的一步。"""),

    code("""import random

def perturb_weights(weights, rng, scale=0.3):
    \"\"\"每个权重按 ±scale 的相对比例随机浮动，再重新归一化使权重和为 1。\"\"\"
    noisy = [max(0.01, w * (1 + rng.uniform(-scale, scale))) for w in weights]
    total = sum(noisy)
    return [w / total for w in noisy]

def sensitivity_analysis(options, base_weights, rng, n_trials=2000, scale=0.3):
    \"\"\"返回 (原始最优方案, 翻转率)。翻转率 = 扰动后最优方案与原始不同的试验占比。\"\"\"
    base_top = rank_options(options, base_weights)[0][0]
    flips = 0
    for _ in range(n_trials):
        w = perturb_weights(base_weights, rng, scale)
        top = rank_options(options, w)[0][0]
        if top != base_top:
            flips += 1
    return base_top, flips / n_trials

rng = random.Random(0)
top, flip_rate = sensitivity_analysis(OPTIONS, WEIGHTS, rng, n_trials=2000, scale=0.3)
print(f'原始最优方案：{top}')
print(f'±30% 权重扰动下，翻转率 = {flip_rate:.3f}（{flip_rate:.1%}）')
assert top == '方案B：加一层后处理规则'
assert abs(flip_rate - 0.045) < 1e-9
print('\\n✅ 4.5% 的翻转率说明结论总体稳健，但不是绝对稳健——面试里可以诚实地报这个数字，而不是笼统地说"肯定选B"。')"""),

    code("""# 对照组：方案在每个维度都不劣于其他方案时（帕累托支配），翻转率应该精确为 0——
# 这是下一节"被支配"概念的一个预告，也验证了"支配关系 -> 加权分数必然占优"这个数学事实。
ROBUST_OPTIONS = {
    'E（全维度占优）': [9, 9, 9, 9],
    'F': [5, 5, 5, 5],
    'G': [3, 3, 3, 3],
}
rng2 = random.Random(1)
top2, flip_rate2 = sensitivity_analysis(ROBUST_OPTIONS, WEIGHTS, rng2, n_trials=2000, scale=0.3)
print(f'全维度占优方案：{top2}，翻转率 = {flip_rate2}')
assert top2 == 'E（全维度占优）'
assert flip_rate2 == 0.0

# 再看翻转率如何随扰动幅度增大而上升——扰动越大，越容易触达"决策边界"
print(f\"\\n{'扰动幅度':>8} {'翻转率':>8}\")
prev_rate = -1.0
for scale in (0.1, 0.2, 0.3, 0.5, 0.8):
    rng3 = random.Random(0)
    _, rate = sensitivity_analysis(OPTIONS, WEIGHTS, rng3, n_trials=2000, scale=scale)
    print(f'{scale:>8.1f} {rate:>8.3f}')
    assert rate >= prev_rate, '扰动幅度增大，翻转率不应该下降'
    prev_rate = rate
print('\\n✅ 翻转率随扰动幅度单调不减：这正是"结论对权重的依赖程度"可以被量化观察的证据。')"""),

    md("""## 4 · 帕累托前沿：不需要权重就能淘汰的方案

方案 c 和方案 b 成本相同但收益更低、方案 e 比方案 d 更贵却收益相同——这两个可以无条件淘汰，
不需要争论任何权重。"""),

    code("""CANDIDATES = {
    'a': {'cost': 1, 'benefit': 2},
    'b': {'cost': 2, 'benefit': 3},
    'c': {'cost': 2, 'benefit': 2},
    'd': {'cost': 3, 'benefit': 5},
    'e': {'cost': 4, 'benefit': 5},
    'f': {'cost': 5, 'benefit': 6},
}

def is_dominated(name, candidates):
    \"\"\"存在另一个候选，成本不高于它、收益不低于它、且至少一项严格更优 -> 被支配。\"\"\"
    x = candidates[name]
    for other, y in candidates.items():
        if other == name:
            continue
        if y['cost'] <= x['cost'] and y['benefit'] >= x['benefit'] and (y['cost'] < x['cost'] or y['benefit'] > x['benefit']):
            return True
    return False

def pareto_front(candidates):
    return sorted([n for n in candidates if not is_dominated(n, candidates)], key=lambda n: candidates[n]['cost'])

front = pareto_front(CANDIDATES)
dominated = [n for n in CANDIDATES if n not in front]
print('帕累托前沿：', front)
print('被支配（可直接淘汰）：', dominated)

assert front == ['a', 'b', 'd', 'f']
assert dominated == ['c', 'e']
print('\\n✅ c 被 b 支配（成本相同收益更低）、e 被 d 支配（收益相同成本更高）——')
print('   这一步筛选完全不需要定权重，是加权打分之前免费的第一道过滤（呼应 C53-05 的三步选型法）。')"""),

    md("""## 5 · 预算约束下的方案组合：贪心先跑一遍

三个候选修复方案 (成本, 收益)，预算 50。先看贪心按性价比排序能拿到多少——
`knapsack_best`（0/1 背包精确解）留在练习 3，你自己实现后再和贪心的结果对比。"""),

    code("""ITEMS = [('X', 10, 60), ('Y', 20, 100), ('Z', 30, 120)]   # (名字, 成本, 收益)
BUDGET = 50

def greedy_by_ratio(items, budget):
    \"\"\"按 收益/成本 比降序贪心装入，直到预算装不下下一个为止。\"\"\"
    order = sorted(items, key=lambda it: -it[2] / it[1])
    chosen, cost, value = [], 0, 0
    for name, c, v in order:
        if cost + c <= budget:
            chosen.append(name)
            cost += c
            value += v
    return chosen, cost, value

g_chosen, g_cost, g_value = greedy_by_ratio(ITEMS, BUDGET)
ratios = sorted([(n, round(v / c, 2)) for n, c, v in ITEMS], key=lambda t: -t[1])
print('性价比排序（收益/成本，降序）：', ratios)
print(f'贪心选择: {g_chosen}  成本={g_cost}  收益={g_value}')

assert g_chosen == ['X', 'Y']
assert g_cost == 30 and g_value == 160
print('\\n贪心用了 30/50 预算，拿到 160 收益——看起来不错，但预算还剩 20 没用完。')
print('练习 3 会让你亲手写 0/1 背包 DP，验证贪心到底是不是真的最优。')"""),

    md("""## 6 · 三种不确定性决策准则的分歧演示

要不要为极端天气单独训练一个专用小模型？常见天气发生概率 90%，极端天气 10%。
三种决策准则可能给出不同答案——这个分歧本身就是本节最重要的结论。"""),

    code("""SCENARIO_PROB = {'常见天气': 0.9, '极端天气': 0.1}
PAYOFF = {
    '专用模型': {'常见天气': 6, '极端天气': 9},
    '通用模型': {'常见天气': 8, '极端天气': 3},
    '不做':     {'常见天气': 9, '极端天气': 0},
}

def expected_utility(payoff, probs):
    return {a: sum(probs[s] * v[s] for s in probs) for a, v in payoff.items()}

def maximin(payoff):
    return {a: min(v.values()) for a, v in payoff.items()}

def minimax_regret(payoff):
    scenarios = list(next(iter(payoff.values())).keys())
    best_per_scenario = {s: max(payoff[a][s] for a in payoff) for s in scenarios}
    return {a: max(best_per_scenario[s] - payoff[a][s] for s in scenarios) for a in payoff}

eu = expected_utility(PAYOFF, SCENARIO_PROB)
mm = maximin(PAYOFF)
mr = minimax_regret(PAYOFF)

best_eu = max(eu, key=eu.get)
best_mm = max(mm, key=mm.get)
best_mr = min(mr, key=mr.get)

print('期望效用   :', {k: round(v, 2) for k, v in eu.items()}, '-> 选', best_eu)
print('最坏情况   :', mm, '-> 选', best_mm)
print('后悔最小化 :', mr, '-> 选', best_mr)

assert best_eu == '不做'
assert best_mm == '专用模型'
assert best_mr == '专用模型'
print('\\n✅ 期望效用选"不做"（长期概率占优），最坏情况和后悔最小化都选"专用模型"（防极端场景兜底）——')
print('   三选二地分裂：这说明这不是一道靠直觉能一步到位的题，需要先确认团队对风险的容忍态度。')"""),

    md("""## 7 · 可逆决策速度与沉没成本谬误"""),

    code("""def decision_speed_budget(reversibility, stakes):
    \"\"\"reversibility: 'reversible'/'irreversible'；stakes: 1-10（影响范围/撤回代价）。
    返回"建议投入的决策精力"相对值——不可逆决策在同等 stakes 下应该分配数倍精力。\"\"\"
    base = {'reversible': 1, 'irreversible': 4}[reversibility]
    return base * stakes

DECISIONS = [
    ('调整置信度阈值(线上可回滚)', 'reversible', 2),
    ('更换标注供应商', 'reversible', 3),
    ('删除历史训练数据快照', 'irreversible', 7),
    ('选择车端推理芯片平台', 'irreversible', 9),
]
for name, kind, stakes in DECISIONS:
    budget = decision_speed_budget(kind, stakes)
    print(f'{name:<24} {kind:<12} stakes={stakes}  建议决策精力(相对值)={budget}')

assert decision_speed_budget('reversible', 5) < decision_speed_budget('irreversible', 5)
print('\\n✅ 同等影响范围下，不可逆决策应该分配数倍的决策精力——这不是"性格谨慎"，是显式的速度分配规则。')"""),

    code("""# 沉没成本谬误：理性决策只看未来价值，不应该被"已经投入多少"左右
def rational_choice(future_value_current, future_value_alternative, sunk_cost):
    return 'switch' if future_value_alternative > future_value_current else 'stay'

def biased_choice(future_value_current, future_value_alternative, sunk_cost, sunk_weight=0.1):
    \"\"\"沉没成本谬误：把已投入的沉没成本按比例折算进"继续当前方案"的分数里。\"\"\"
    adjusted_current = future_value_current + sunk_weight * sunk_cost
    return 'switch' if future_value_alternative > adjusted_current else 'stay'

# 同样的"未来价值对比"（新架构未来价值8 明显高于旧架构未来价值5），只是已投入的沉没成本不同
assert rational_choice(future_value_current=5, future_value_alternative=8, sunk_cost=0) == 'switch'
assert rational_choice(future_value_current=5, future_value_alternative=8, sunk_cost=1000) == 'switch'
print('理性决策：不管已经投入多少（0 还是 1000），结论都是 switch —— 未来价值对比没有变。')

assert biased_choice(future_value_current=5, future_value_alternative=8, sunk_cost=0) == 'switch'
assert biased_choice(future_value_current=5, future_value_alternative=8, sunk_cost=1000) == 'stay'
print('偏误决策：沉没成本从 0 涨到 1000 之后，结论从 switch 被拖成了 stay —— 这正是"都已经投入这么久了"背后的谬误。')
print('\\n✅ 理性决策函数对沉没成本的大小完全不敏感；偏误决策函数会被拖着不肯换——这就是可以在面试里讲清楚的机制。')"""),

    md("""## ✏️ 练习 1：多维打分的归一化 + 加权排序一体化

实现 `score_options(raw_options, directions, weights)`：`raw_options` 是 `{方案名: [原始值,...]}`，
`directions` 是每个维度 `'max'`（越大越好）或 `'min'`（越小越好）的列表。
函数需要先对每个维度做最小-最大归一化（复用第 2 节的 `minmax_normalize`），再加权求和，
返回 `{方案名: 加权总分}`。"""),

    code("""def score_options(raw_options, directions, weights):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
raw = {
    '方案A': [12, 4.5],   # [延迟ms, 准确率提升pp]
    '方案B': [3, 1.2],
    '方案C': [7, 2.8],
}
directions = ['min', 'max']       # 延迟越小越好，准确率提升越大越好
w = [0.5, 0.5]
result = score_options(raw, directions, w)
print(result)

assert abs(result['方案A'] - (0.0 * 0.5 + 1.0 * 0.5)) < 1e-9     # 延迟最差(归一化0)，准确率提升最好(归一化1)
assert abs(result['方案B'] - (1.0 * 0.5 + 0.0 * 0.5)) < 1e-9     # 延迟最好(归一化1)，准确率提升最差(归一化0)
assert 0.0 < result['方案C'] < 1.0                                 # 方案C两项都居中
print('✅ 练习 1 通过：先归一化到同一量纲，再加权，才能公平地合成一个数字。')"""),

    md("""## ✏️ 练习 2：n 维帕累托前沿

实现 `pareto_front_nd(candidates, directions)`：泛化第 4 节的二维版本到任意维度。
`candidates`: `{名字: [维度值,...]}`；`directions`: 每维 `'max'` 或 `'min'`。
返回未被支配的名字列表（被支配定义：存在另一候选在每一维都不差、且至少一维更好）。"""),

    code("""def pareto_front_nd(candidates, directions):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
def _better_or_equal(v, u, directions):
    \"\"\"v 在每一维是否都不差于 u（按 directions 的方向）。\"\"\"
    for vi, ui, d in zip(v, u, directions):
        if d == 'max' and vi < ui:
            return False
        if d == 'min' and vi > ui:
            return False
    return True

# 三维候选：(成本[越小越好], 收益[越大越好], 风险[越小越好])
CANDS_3D = {
    'p1': [1, 2, 5],
    'p2': [2, 3, 3],
    'p3': [2, 2, 3],   # 与 p2 成本相同，收益更低、风险相同 -> 被 p2 支配
    'p4': [3, 5, 2],
    'p5': [4, 5, 4],   # 与 p4 相比：成本更高、收益相同、风险更高 -> 被 p4 支配
}
front3d = pareto_front_nd(CANDS_3D, ['min', 'max', 'min'])
print('三维帕累托前沿：', sorted(front3d))

assert sorted(front3d) == ['p1', 'p2', 'p4']
assert 'p3' not in front3d and 'p5' not in front3d

# 退化检验：全部候选互不支配时，前沿应该等于候选全集
CANDS_TIE = {'x': [1, 5], 'y': [2, 6], 'z': [3, 7]}   # 成本越高收益也越高，谁都不支配谁
front_tie = pareto_front_nd(CANDS_TIE, ['min', 'max'])
assert sorted(front_tie) == ['x', 'y', 'z']
print('✅ 练习 2 通过：n 维支配关系的判断和二维完全一样，只是要在每一维上都检查。')"""),

    md("""## ✏️ 练习 3：0/1 背包动态规划（验证贪心到底差多少）

实现 `knapsack_best(items, budget)`：`items` 是 `[(名字, 成本, 收益), ...]`，成本均为非负整数。
返回 `(选中的名字列表, 最优总收益)`。用动态规划求**精确最优解**，再和第 5 节的贪心结果对比。"""),

    code("""def knapsack_best(items, budget):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
k_chosen, k_value = knapsack_best(ITEMS, BUDGET)
print(f'背包最优解: {sorted(k_chosen)}  收益={k_value}')

assert sorted(k_chosen) == ['Y', 'Z']
assert k_value == 220
assert k_value > g_value, '最优解不应该比贪心解差'
print(f'\\n对比：贪心收益 {g_value}（用了 {g_cost}/{BUDGET} 预算），背包最优 {k_value}（用满 50/{BUDGET} 预算）')
print(f'贪心比最优少了 {k_value - g_value} 收益，相对差距 {(k_value - g_value) / k_value:.1%}——')
print('✅ 练习 3 通过：这正是"性价比最高不等于组合起来最优"的量化证据。')"""),

    md("""## ✏️ 练习 4：统一的不确定性决策器

实现 `decide_under_uncertainty(payoff, probs, criterion)`：`criterion` ∈
`'expected_utility' / 'maximin' / 'minimax_regret'`，返回该准则下的最优方案名字。
复用第 6 节已经定义的 `expected_utility` / `maximin` / `minimax_regret` 三个函数即可，
本练习只是把"选择哪个准则"这件事封装成一个统一入口。"""),

    code("""def decide_under_uncertainty(payoff, probs, criterion):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
assert decide_under_uncertainty(PAYOFF, SCENARIO_PROB, 'expected_utility') == '不做'
assert decide_under_uncertainty(PAYOFF, SCENARIO_PROB, 'maximin') == '专用模型'
assert decide_under_uncertainty(PAYOFF, SCENARIO_PROB, 'minimax_regret') == '专用模型'

try:
    decide_under_uncertainty(PAYOFF, SCENARIO_PROB, 'unknown_criterion')
    assert False, '未知准则应该报错'
except (KeyError, ValueError):
    pass
print('✅ 练习 4 通过：三种准则封装成一个入口后，面试里可以现场把同一个 payoff 表在三种准则下各跑一遍。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def score_options(raw_options, directions, weights):
    names = list(raw_options)
    n_dims = len(directions)
    norm_cols = []
    for d in range(n_dims):
        col = [raw_options[name][d] for name in names]
        higher_is_better = (directions[d] == 'max')
        norm_cols.append(minmax_normalize(col, higher_is_better=higher_is_better))
    result = {}
    for i, name in enumerate(names):
        result[name] = sum(norm_cols[d][i] * weights[d] for d in range(n_dims))
    return result"""),

    code("""# 练习 2 参考答案
def pareto_front_nd(candidates, directions):
    def dominated(name):
        v = candidates[name]
        for other, u in candidates.items():
            if other == name:
                continue
            if _better_or_equal(u, v, directions) and u != v:
                return True
        return False
    return [n for n in candidates if not dominated(n)]"""),

    code("""# 练习 3 参考答案
def knapsack_best(items, budget):
    n = len(items)
    dp = [[0] * (budget + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        name, c, v = items[i - 1]
        for b in range(budget + 1):
            dp[i][b] = dp[i - 1][b]
            if c <= b:
                dp[i][b] = max(dp[i][b], dp[i - 1][b - c] + v)
    b = budget
    chosen = []
    for i in range(n, 0, -1):
        if dp[i][b] != dp[i - 1][b]:
            name, c, v = items[i - 1]
            chosen.append(name)
            b -= c
    return list(reversed(chosen)), dp[n][budget]"""),

    code("""# 练习 4 参考答案
def decide_under_uncertainty(payoff, probs, criterion):
    if criterion == 'expected_utility':
        eu = expected_utility(payoff, probs)
        return max(eu, key=eu.get)
    if criterion == 'maximin':
        mm = maximin(payoff)
        return max(mm, key=mm.get)
    if criterion == 'minimax_regret':
        mr = minimax_regret(payoff)
        return min(mr, key=mr.get)
    raise ValueError(f'未知准则: {criterion}')"""),

    md("""---
## 🧪 真实工程胶囊：权衡决策白板模板 + 面试口播要点"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 权衡决策白板模板（面试当场可以照这个骨架展开）
# ══════════════════════════════════════════════════════════════════════
# 1. 列维度：这个决策涉及哪几个互相独立的考量？有没有维度在重复计分？
# 2. 定权重：权重来自业务/安全优先级，独立于候选方案打分之前先定好
# 3. 打分：不同量纲先做最小-最大归一化，再加权求和
# 4. 帕累托预筛：有没有方案在所有维度都被别的方案碾压？先淘汰，不用权重
# 5. 敏感性分析：把权重扰动 ±20%~30%，结论会不会翻转？翻转率多高？
# 6. 不确定性：如果各方案的表现依赖未来场景，明确说清楚用的是期望效用/最坏情况/后悔最小化中的哪个
# 7. 可逆性：这个决策能不能轻松撤回？决定该用多快的速度、要不要多方会签
# 8. 说清放弃了什么：选中的方案在哪个维度不是最优，代价是什么，什么条件下会重新评估

# ══════════════════════════════════════════════════════════════════════
# B. 面试里最容易被追问的三句话，提前想好怎么答
# ══════════════════════════════════════════════════════════════════════
# Q: "你为什么选 A 不选 B？"
# A: "我列了四个维度、按这样定权重，A 领先 B 0.6 分；我把权重扰动了 ±30% 重跑了一遍，
#     A 领先的结论在 95% 的情况下依然成立，所以这个结论是稳健的。"
#
# Q: "那 B 更好的地方怎么办？"
# A: "B 在实现成本上确实更低，选 A 意味着我们要多付出这部分工程代价；
#     如果后续发现这个代价超出预算，我会重新评估。"
#
# Q: "如果只能选一个，你选哪个？"
# A: "我选 A。我的判断标准是安全 > 用户体验 > 开发效率，这个场景涉及漏检安全类别，
#     所以按这个标准 A 优先；这意味着我们暂时不改善另一类的误检率。"

# ══════════════════════════════════════════════════════════════════════
# C. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 帕累托前沿与延迟-精度权衡的技术细节        -> C53 模块 05（本课只讲面试组织表达）
# · 预算约束下贪心与背包最优的技术细节          -> C57 模块 05（本课复用其两步法结论）
# · 诊断出根因之后的方案选择                    -> 承接 C65 模块 02
# · 模糊问题的收敛与优先级排序                  -> C65 模块 04（"只能选一个"框架与之衔接）
'''
print(RECIPE)
for token in ['帕累托预筛', '敏感性分析', '不确定性', 'C53 模块 05', 'C57 模块 05']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：权衡决策白板骨架 / 高频追问的标准答法 / 与其他课程的分工边界')"""),

    md("""### 小结

- **取舍显式化的四步是列维度→定权重→打分→说清放弃了什么**——最后一步几乎总被省略，但正是它把"选择"变成"决策"。
- **权重扰动敏感性分析是本模块最有说服力的一步**：与其笼统地说"选 A"，不如报出"权重扰动 30% 下翻转率 4.5%"，
  用一个数字证明结论的稳健程度；全维度占优的方案，翻转率精确为 0，这是可以严格证明的数学事实。
- **帕累托前沿不需要权重就能淘汰方案**：被支配的方案无论权重怎么定都不该选，这是加权打分之前免费的第一道过滤。
- **性价比最高不等于组合起来最优**：0/1 背包问题里贪心没有最坏情况保证，候选数量少时应该用 DP 精确验证。
- **不确定性下的三种决策准则会给出不同答案**：期望效用适合可重复、概率靠谱的场景；最坏情况和后悔最小化
  适合后果极端或不可挽回的场景——分歧本身就是值得主动指出的洞察。
- **可逆决策快做，不可逆决策慢做**；沉没成本不该影响面向未来的选择，理性决策函数对已投入多少完全不敏感。
- **"如果只能选一个"必须给出明确选择 + 独立准则 + 放弃的代价**——"都很重要"式回答是最危险的失分项。

下一站：**模块 04 · 模糊问题与需求澄清** —— 权衡的前提是候选方案已经摆在桌上，
下一个更难的问题是：题目本身连边界都没有，你要先把它收敛成一个能权衡的问题。"""),
]
