# -*- coding: utf-8 -*-
"""C67 模块 04 · 从成对比较到排名（Bradley-Terry / Elo / 置信区间 / 主动配对）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 03（元评测与校准）；"
                 "逻辑回归在模块 02 已经从零写过，本模块继续复用同一套 numpy 代码"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_ranking.ipynb'
                       '（Bradley–Terry 的 MLE 拟合与自举区间 / Elo 与在线更新的路径依赖 / '
                       '传递性违反的检测与后果 / 主动配对：不确定性最大化 vs 随机配对 / '
                       '排名稳定性与「多少分才算真差距」/ 风格控制的 BT 扩展）'),
    ("核心参考", "Bradley &amp; Terry, <em>Rank Analysis of Incomplete Block Designs</em>（Biometrika 1952）· "
                 "Chiang et al., <em>Chatbot Arena</em>（ICML 2024，BT 模型与 Arena 排名方法）· "
                 "Elo, <em>The Rating of Chessplayers</em>（1978）· "
                 "Zermelo（1929，BT 的更早形式与 MM 迭代解法）· "
                 "本课程 C66 模块 04（配对设计与自举）· C13（bandits 与主动选择）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("problem", "问题：手上是一堆胜负，想要的是一个排行榜", "".join([
        P("模块 01–03 解决的是「一次比较可不可信」。这一节开始解决下一个问题："
          "<strong>你有几千条「A 赢 B」的记录，涉及十几个模型，怎么把它们变成一个带误差棒的排行榜？</strong>"),
        ASCII("""
   输入：稀疏的成对比较矩阵                输出：一维分数 + 区间
   ┌─────────────────────────┐            ┌──────────────────────────┐
   │      M1  M2  M3  M4  M5 │            │ 1. M3   1247  [1231,1263] │
   │ M1    -  12/20  3/5  -  │            │ 2. M1   1198  [1180,1215] │
   │ M2  8/20  -   -  9/15 - │   ─────►   │ 3. M2   1176  [1154,1198] │  ← 与 M1 区间重叠
   │ M3  2/5   -   -   -  7/9│            │ 4. M5   1102  [1068,1136] │
   │ M4   -  6/15  -   -  4/8│            │ 5. M4   1089  [1051,1127] │  ← 与 M5 区间重叠
   │ M5   -   -  2/9  4/8  - │            └──────────────────────────┘
   └─────────────────────────┘            排名 3 vs 2、4 vs 5 实为并列
   注意：矩阵是**稀疏**的（不是每对都比过），而且每格的样本量差别很大。
"""),
        P("这一步引入了一个新的假设，它必须被显式说出来：<strong>「模型的质量可以被一个标量刻画」</strong>。"
          "这个假设在多数情况下够用，但它不是免费的——第 5 节会讲它什么时候崩掉。"),
        TABLE(["方法", "核心思想", "优点", "缺点"], [
            ["<strong>朴素胜率</strong>", "每个模型对所有对手的总胜率", "极简单", "<strong>被对手强度污染</strong>：只和弱模型比过的模型胜率虚高"],
            ["<strong>Bradley–Terry</strong>", "极大似然拟合每个模型的强度参数", "<strong>正确处理对手强度与稀疏性</strong>；有标准误", "假设传递性；批量计算"],
            ["<strong>Elo</strong>", "在线逐条更新评分", "可增量更新，适合流式数据", "<strong>结果依赖比赛顺序</strong>；K 因子是个自由参数"],
            ["<strong>带协变量的 BT</strong>", "BT + 长度/风格作为协变量", "可以同时做去偏（模块 02）与排名", "需要更多数据"],
        ]),
        CALLOUT("intuition", "为什么不能直接用胜率？<strong>因为对手不一样。</strong>"
                             "一个只和弱模型比过 200 场的模型，胜率可能高达 80%；"
                             "一个专挑强对手比的模型可能只有 45%。"
                             "<em>朴素胜率把这两者放在同一个尺度上比较，是没有依据的。</em>"
                             "BT 模型的全部价值就是：<strong>它同时估计所有模型的强度，"
                             "让「赢了谁」这件事被正确地加权。</strong>"),
    ])),

    # ============================================================== 2
    ("bt", "Bradley–Terry 模型：定义、拟合与它的三个性质", "".join([
        P("BT 模型只有一个式子。设模型 $i$ 的强度参数为 $\\theta_i$，则"),
        MATH(r"\Pr(i \succ j) = \frac{e^{\theta_i}}{e^{\theta_i} + e^{\theta_j}} = \sigma(\theta_i - \theta_j)"),
        P("其中 $\\sigma$ 是 sigmoid。<strong>这等价于一个逻辑回归</strong>："
          "把每场比较编码成一个只有两个非零元素的特征向量"
          "（胜者位置 +1、败者位置 −1），标签是「前者是否获胜」，"
          "拟合出来的系数就是 $\\theta$。<em>所以模块 02 写的那个 <code>fit_logistic</code> 可以直接复用。</em>"),
        H3("三个必须知道的性质"),
        OL([
            "<strong>只有差值有意义，绝对值没有。</strong>"
            "$\\theta_i \\to \\theta_i + c$ 对所有 $i$ 同时加一个常数，所有预测概率都不变。"
            "<em>所以必须固定一个基准</em>（把某个模型设为 0，或让所有 $\\theta$ 之和为 0），"
            "否则拟合出来的绝对数字每次都不一样。",
            "<strong>差值直接翻译成胜率</strong>：$\\theta_i - \\theta_j = 0$ → 50%；"
            "$= 1$ → 73%；$= 2$ → 88%。"
            "<em>这条让 BT 分数比 Elo 分数更容易解释</em>——它就是 logit 尺度上的距离。",
            "<strong>存在性条件</strong>：如果比较图不连通（有一组模型从没和另一组比过），"
            "两组之间的相对强度<em>无法确定</em>；如果某个模型全胜或全败，它的 $\\theta$ 会发散到无穷。"
            "<strong>两种情况都需要正则化（等价于加一个先验）来处理。</strong>",
        ]),
        CALLOUT("warn", "第 3 条在真实数据上非常常见，尤其是刚加入榜单的新模型（比赛场次少、可能全胜）。"
                        "<strong>标准处理是加 L2 正则（等价于给 $\\theta$ 一个高斯先验），"
                        "或者用「加一个虚拟的平局对手」的方式做平滑。</strong>"
                        "<em>不做正则化的 BT 拟合在这类数据上会给出荒谬的巨大分数，"
                        "而且这个问题不会报错，只会安静地毁掉你的排行榜。</em>"),
        H3("Elo 分数：BT 的一个仿射变换"),
        P("Arena 类榜单常报的 Elo 分数，本质上是 BT 参数的线性重标："),
        MATH(r"\text{Elo}_i = 1000 + \frac{400}{\ln 10}\,\theta_i \approx 1000 + 173.7\,\theta_i"),
        P("这个换算的意义是让「差 400 分 = 胜率 10:1」这条国际象棋的老约定成立。"
          "<strong>它不增加任何信息，只是换了一个更多人熟悉的刻度。</strong>"
          "<em>知道这一点很重要：当有人说「A 比 B 高 20 个 Elo 分」，"
          "你可以立刻换算成 $20/173.7 = 0.115$ 的 logit 差，即约 <strong>52.9% 的胜率</strong>——"
          "一个远比「20 分」听起来更小的差距。</em>"),
    ])),

    # ============================================================== 3
    ("elo-online", "在线 Elo：为什么它的结果依赖比赛顺序", "".join([
        P("在线 Elo 是另一条路线：不做批量拟合，而是每来一场比赛就更新一次评分。"),
        MATH(r"\theta_i \leftarrow \theta_i + K\left(y - \sigma(\theta_i - \theta_j)\right), \qquad \theta_j \leftarrow \theta_j - K\left(y - \sigma(\theta_i - \theta_j)\right)"),
        P("其中 $y \\in \\{0, 1\\}$ 是实际结果，$K$ 是学习率（国际象棋里叫 K 因子）。"
          "<strong>这就是对 BT 对数似然做随机梯度上升</strong>——它是 BT 的在线版本，不是另一个模型。"),
        TABLE(["性质", "在线 Elo", "批量 BT (MLE)", "实践含义"], [
            ["<strong>顺序依赖</strong>", "<strong>有</strong>：打乱比赛顺序会得到不同的分数", "无：只取决于胜负计数", "报告 Arena 类分数时，<em>批量 BT 是更可复现的选择</em>"],
            ["<strong>增量更新</strong>", "天然支持", "需要重新拟合（但通常很快）", "流式场景用 Elo，定期发布用 BT"],
            ["<strong>自由参数</strong>", "K 因子（大 = 跟得快但噪声大）", "只有正则化强度", "K 选不好会让榜单剧烈抖动"],
            ["<strong>不确定度</strong>", "没有原生的标准误", "<strong>有</strong>（Hessian 或自举）", "要画误差棒必须用 BT 或对 Elo 做自举"],
            ["<strong>处理能力漂移</strong>", "<strong>能</strong>（旧比赛权重自然衰减）", "不能（所有比赛等权）", "如果模型本身在变，Elo 反而更合适"],
        ]),
        CALLOUT("danger", "顺序依赖不是一个理论洁癖问题。<strong>同一批比赛数据，"
                          "换一个随机顺序跑一遍在线 Elo，模型的名次可能改变。</strong>"
                          "这意味着「Elo 分数」这个数字本身不是数据的函数，而是<em>数据加上你处理它的顺序</em>的函数。"
                          "<strong>公开榜单如果用在线 Elo，必须固定并公布顺序，否则不可复现</strong>——"
                          "这与 C66 模块 05 的 运行指纹是同一件事。"
                          "notebook 第 2 节会把这个抖动量化出来。"),
        P("一个折中方案在实践中很常用：<strong>用批量 BT 出正式排名，用在线 Elo 做实时预览。</strong>"
          "两者的差距本身也是一个有用的监控信号——差得越大，说明数据里的时间结构越强"
          "（可能是模型在漂移，也可能是配对策略随时间变了）。"),
    ])),

    # ============================================================== 4
    ("intervals", "置信区间：排行榜上相差 20 分算不算差距", "".join([
        P("这是本模块最有实际价值的一节。<strong>没有区间的排行榜，是一份鼓励过度解读的文档。</strong>"),
        H3("两种算区间的方式"),
        TABLE(["方法", "怎么做", "优点", "注意"], [
            ["<strong>自举</strong>", "对<em>比较记录</em>重采样，每次重新拟合 BT，取分位数", "不依赖渐近假设；能处理正则化", "慢（要拟合几百次）；<strong>重采样单位必须是「一场比较」而不是「一个模型」</strong>"],
            ["<strong>Fisher 信息 / Hessian</strong>", "从对数似然的二阶导算标准误", "快", "是渐近结果，小样本或稀疏图上不准"],
        ]),
        P("推荐<strong>自举</strong>——它慢，但 BT 拟合本身很快（几千场比较、十几个模型，一次拟合是毫秒级），"
          "跑 500 次自举也就几秒钟。"),
        H3("从区间到「名次」"),
        DUAL(
            "有了每个模型的区间，怎么报名次？<strong>正确做法不是按点估计排 1、2、3，"
            "而是给出「排名区间」</strong>：在自举的每一次重采样里都算一遍名次，"
            "然后报这个名次的分布。"
            "<strong>Arena 类榜单报的「rank」通常就是这个意思：与你区间重叠的模型都算并列。</strong>",
            "形式化：设自举重采样得到 $B$ 组参数 $\\{\\theta^{(b)}\\}$，"
            "模型 $i$ 的排名分布为 $\\{r_i^{(b)}\\}$。"
            "报告 <strong>$[\\text{quantile}_{2.5\\%}(r_i),\\ \\text{quantile}_{97.5\\%}(r_i)]$</strong>。"
            "<em>这个区间比分数区间更直接地回答了读者关心的问题——"
            "「这个模型到底是第几名」。</em>"
            "另一个等价的报法是<span class=\"term\">显著优于计数</span>："
            "模型 $i$ 显著优于多少个其他模型（区间不重叠且方向为正），"
            "用这个数排序得到的名次天然是并列友好的。",
        ),
        H3("那 20 个 Elo 分到底算不算"),
        P("把第 2 节的换算和区间宽度放在一起，就能回答这个问题："),
        UL([
            "20 个 Elo 分 ≈ 0.115 logit ≈ <strong>52.9% 的胜率</strong>；",
            "要把 52.9% 与 50% 区分开（$z = 2$），按模块 03 的公式需要约 <strong>1200 场</strong>比较；",
            "<strong>而 Arena 类榜单上一对模型之间的直接对局往往只有几百场</strong>"
            "（其余信息来自与共同对手的间接比较）。",
        ]),
        CALLOUT("intuition", "所以一条可以直接用的读榜规则：<strong>看区间，不看名次。</strong>"
                             "区间重叠的模型就是并列，无论它们的点估计差了多少分。"
                             "<em>而如果一份榜单不给区间，你可以用一个粗糙的心算："
                             "几千场比较对应的区间半宽通常在 ±10 到 ±20 Elo 分之间，"
                             "所以相差 30 分以内的名次基本可以当成并列。</em>"),
    ])),

    # ============================================================== 5
    ("transitivity", "传递性：BT 假设了它，而 LLM judge 经常违反它", "".join([
        P("BT 模型把每个模型压缩成一个标量，这隐含了一个强假设："
          "<strong>如果 A 通常赢 B、B 通常赢 C，那么 A 通常赢 C。</strong>"
          "这叫<span class=\"term\">随机传递性</span>。"),
        P("<strong>而 LLM judge 的成对偏好经常违反它。</strong>违反的典型来源有两个："),
        OL([
            "<strong>能力不是一维的。</strong>A 擅长代码、B 擅长写作、C 擅长推理，"
            "在一个混合任务集上，三者可能形成一个循环——这不是 judge 出错，"
            "而是<em>「一个标量」这个模型本身不够用</em>。",
            "<strong>judge 的偏差与对局有关。</strong>"
            "如果 A 长 B 短、B 结构化 C 不结构化，长度偏差与格式偏差在不同对局里权重不同，"
            "也会造出循环。<em>这一种是真的错，可以靠模块 02 的去偏减轻。</em>",
        ]),
        H3("怎么检测"),
        TABLE(["方法", "怎么做", "读法"], [
            ["<strong>三元环计数</strong>", "枚举所有三元组，统计形成循环（A&gt;B&gt;C&gt;A）的比例", "与<strong>拟合出的 BT 模型下的期望循环率</strong>比较，显著更高才算异常（不要跟「随机胜负」的 25% 比——那个基线太松，任何有区分度的榜单都远低于它）"],
            ["<strong>BT 拟合优度</strong>", "用拟合出的 $\\theta$ 预测每一对的胜率，与实际胜率比较", "<strong>系统性的残差结构</strong>（不是随机噪声）说明一维不够用"],
            ["<strong>分任务类型拟合</strong>", "在代码/写作/推理子集上各拟合一套 BT，看排名是否一致", "<strong>最有信息量</strong>：排名不一致直接证明能力是多维的"],
        ]),
        CALLOUT("danger", "有一个特别值得警惕的现象：<strong>「总榜第一」经常在每个子任务上都不是第一。</strong>"
                          "这不矛盾——总榜是各子任务按<em>某个隐含权重</em>加权的结果，"
                          "而这个权重来自任务集的构成比例，往往没人显式选择过。"
                          "<strong>换句话说，总榜的排名有一部分是由「任务集里代码题占多少比例」决定的。</strong>"
                          "<em>这就是为什么分任务榜比总榜更有决策价值。</em>"),
        P("如果检测到严重的传递性违反，处理方式按代价从低到高："),
        UL([
            "<strong>分维度报告</strong>——最简单也最诚实：不出总榜，出几个子榜；",
            "<strong>先去偏再拟合</strong>——如果循环来自 judge 偏差（第 2 类来源），去偏能减轻；",
            "<strong>多维模型</strong>——把 $\\theta_i$ 换成向量，用类似 Blade-Chest 的低秩模型。"
            "<em>数据需求大幅上升，通常只在数据非常充足时才值得。</em>",
        ]),
    ])),

    # ============================================================== 6
    ("active", "主动配对：同样的预算，多买到多少信息", "".join([
        P("配对策略是排名系统里一个经常被忽略、但收益很大的杠杆。"
          "<strong>随机配对会把大量预算浪费在「早就知道结果」的对局上。</strong>"),
        ASCII("""
   随机配对                          主动配对（不确定性最大化）
   ┌─────────────────────┐          ┌─────────────────────────────┐
   │ 最强 vs 最弱: 大量场次│          │ 最强 vs 最弱: 少量场次(结果已知)│
   │ 结果几乎确定 → 0 bit  │          │ 强度接近的对: 大量场次        │
   │                     │          │ 预测胜率≈50% → 接近 1 bit/场   │
   └─────────────────────┘          └─────────────────────────────┘
      信息效率低                        信息效率高（但引入了选择偏倚）
"""),
        MATH(r"\text{单场信息量} \approx H\big(\sigma(\theta_i - \theta_j)\big) \quad\text{（二元熵，在 } \theta_i = \theta_j \text{ 时最大）}"),
        TABLE(["策略", "怎么选下一对", "收益", "代价"], [
            ["<strong>随机</strong>", "均匀抽两个模型", "无偏；覆盖均匀；实现最简单", "把预算浪费在结果已知的悬殊对局上"],
            ["<strong>不确定性最大化</strong>", "选当前预测胜率最接近 50% 的一对", "<strong>相邻名次的区间显著变窄</strong>", "悬殊对的估计变成纯外推，那些对的区间反而变宽"],
            ["<strong>方差缩减</strong>", "选能最大程度缩小<em>某个特定名次判断</em>不确定度的一对", "针对性最强", "需要先声明你关心哪个判断"],
            ["<strong>混合</strong>", "$\\epsilon$ 概率随机 + $1-\\epsilon$ 主动", "<strong>推荐</strong>：兼顾效率与覆盖", "多一个超参数"],
        ]),
        CALLOUT("intuition", "notebook 第 6 节会跑出一个值得记住的结果："
                             "<strong>主动配对并不是「全面更好」，而是「把精度搬了个地方」</strong>——"
                             "相邻名次的差值区间窄了，但「能被显著区分开的模型对」总数反而<em>少了</em>。"
                             "这完全说得通：预算是守恒的，你把它挪到难分的对上，"
                             "悬殊的对就只能靠模型外推。<em>所以「用哪种配对策略」取决于你要回答哪个问题——"
                             "「谁是第一」用主动，「给我一个完整可信的全表」用随机。</em>"),
        CALLOUT("warn", "主动配对有一个必须处理的副作用：<strong>它让数据不再是「随机缺失」的。</strong>"
                        "如果你只在强度接近的对之间收集数据，那么"
                        "「强弱悬殊的对」的估计就完全依赖模型外推——"
                        "<em>而这恰恰是传递性假设发挥作用最强、也最可能失效的地方</em>。"
                        "<strong>缓解：保留一定比例的随机配对（$\\epsilon \\ge 0.1$），"
                        "并在报告里注明配对策略。</strong>"),
        P("<em>顺带一提：这个问题与 C13 的 bandit 探索-利用是同一个结构</em>——"
          "「利用」是去比最有信息量的对，「探索」是保持覆盖。"
          "区别在于这里的目标不是最大化累积回报，而是最小化排名的不确定度。"),
    ])),

    # ============================================================== 7
    ("style-control", "把去偏接进排名：带协变量的 BT", "".join([
        P("模块 02 讲了长度控制回归，模块本节讲排名。两者可以合成一个模型——"
          "<strong>这是目前 Arena 类榜单「风格控制」版本的做法。</strong>"),
        MATH(r"\operatorname{logit}\Pr(i \succ j) = (\theta_i - \theta_j) + \gamma^\top (x_i - x_j)"),
        P("其中 $x$ 是风格特征向量（长度、markdown 标题数、列表项数、代码块数…），"
          "$\\gamma$ 是这些特征的效应。<strong>拟合后把 $x_i - x_j$ 设为 0，"
          "得到的 $\\theta$ 就是「控制风格后的强度」。</strong>"),
        TABLE(["版本", "$\\theta$ 的含义", "什么时候看这个"], [
            ["<strong>原始 BT</strong>", "「模型在这个 judge 眼里有多受欢迎」", "你关心真实用户偏好，且用户也吃这一套", "—"],
            ["<strong>风格控制 BT</strong>", "「排除掉长度与格式效应后的强度」", "<strong>你关心内容质量本身</strong>，或者担心模型在优化风格", "—"],
            ["<strong>两者之差</strong>", "<strong>这个模型的排名有多少来自风格</strong>", "<em>这个差值本身是最有信息量的一列</em>", "—"],
        ]),
        CALLOUT("intuition", "第三行值得强调：<strong>「原始名次 vs 风格控制后名次」的变化量，"
                             "是一个直接可读的诊断量。</strong>"
                             "一个模型在风格控制后掉了五名，说明它的优势有相当部分来自「写得长、排版好」；"
                             "<em>这未必是坏事（如果用户确实喜欢），但它必须被知道，"
                             "而不是被混在一个总分里。</em>"),
        P("实现上有两个细节值得注意："),
        UL([
            "<strong>风格特征要标准化</strong>，理由与模块 02 相同——量纲不同会让某个特征获得不成比例的杠杆；",
            "<strong>$\\gamma$ 应当全局共享而不是每个模型一份</strong>："
            "$\\gamma$ 描述的是<em>judge 的偏好</em>，不是模型的属性。"
            "<em>如果你给每个模型一个自己的 $\\gamma$，模型就能通过「假装自己的风格特别有效」来吸收掉质量差异，"
            "参数不可识别。</em>",
        ]),
    ])),

    # ============================================================== 8
    ("reporting", "排行榜的报告规范", "".join([
        P("把本模块的结论压缩成一份可以照抄的模板："),
        CODE("""LEADERBOARD · judge=claude-sonnet-5, prompt e3a1f9c, swap=on
拟合方法: Bradley–Terry MLE, L2 正则 λ=0.01, 基准=M4 固定为 0
区间: 对**比较记录**自举 1000 次的 2.5%/97.5% 分位
比较总数: 18,432 场   模型数: 12   比较图: 连通（最小边度 = 3）
配对策略: 0.15 随机 + 0.85 不确定性最大化

rank  model    Elo    95% CI        rank CI   显著优于  风格控制后 Elo   Δrank
 1    M3      1247  [1231, 1263]    [1,1]      11        1238            0
 2    M1      1198  [1180, 1215]    [2,3]       9        1152           -1
 2    M2      1176  [1154, 1198]    [2,4]       9        1183           +1
 4    M5      1102  [1068, 1136]    [4,6]       6        1096            0
...
注: rank CI 重叠的模型视为并列（M1 与 M2 并列第 2）。
    Δrank = 风格控制后的名次变化。M1 掉一名说明其优势中有一部分来自长度/格式。

传递性检查: 三元环比例 4.1%（BT 模型下期望 3.7%，n=220 三元组）→ 未见异常
分任务榜: code / writing / reasoning 三个子榜的 Spearman 两两相关 0.71-0.88
          → **总榜排名对任务集构成比例敏感，请优先看子榜**"""),
        UL([
            "<strong>rank CI 比 Elo CI 更重要</strong>——读者真正关心的是名次；",
            "<strong>比较图连通性必须报</strong>——不连通时跨组比较毫无意义；",
            "<strong>配对策略必须报</strong>——它决定了哪些对的区间可信；",
            "<strong>风格控制版必须与原始版并列</strong>，且报出 Δrank；",
            "<strong>如果子榜之间相关不高，就该说「优先看子榜」</strong>——"
            "把这句话写出来，比让读者自己发现要负责得多。",
        ]),
        CALLOUT("danger", "最后重申模块 03 的那条前提，因为它在排名场景下同样成立且更隐蔽："
                          "<strong>本模块所有的统计工具，都建立在「judge 没有共有的系统偏差」这个前提上。</strong>"
                          "如果所有比较都被同一个长度偏差污染，那么再精确的 BT 拟合、"
                          "再窄的自举区间，也只是<em>对一个偏了的量的精确估计</em>。"
                          "<strong>顺序永远是：先做偏差探针（02）→ 再做元评测（03）→ 最后才拟合排名（本模块）。</strong>"),
    ])),
    # ============================================================== 9
    ("leaderboard-hygiene", "榜单卫生：三个会安静毁掉排行榜的操作", "".join([
        P("最后一节讲三件在实践中反复出现、而且<strong>都不会报错</strong>的操作。"
          "它们的共同点是：数字照样算得出来，只是不再有意义。"),
        H3("① 把不同 judge / 不同 prompt 的比较混在一起拟合"),
        P("这是最常见也最严重的一个。<strong>judge 换了，或者 prompt 改了一句，"
          "之前所有的比较记录就不能与新记录混在一起拟合 BT</strong>——"
          "因为 BT 假设所有比较来自同一个「评判者」。混拟合的结果是："
          "<em>早期用旧 judge 比得多的模型，与后期用新 judge 比得多的模型，"
          "它们之间的相对位置由两个 judge 的系统差异决定，而不是由模型质量决定。</em>"),
        CALLOUT("danger", "<strong>缓解办法只有两个，没有第三个</strong>："
                          "① judge 变更时<strong>作废历史数据</strong>，重新开始积累；"
                          "② 在变更时设一个<strong>双跑重叠期</strong>，用同一批样本同时跑新旧 judge，"
                          "估计出两者的系统差异，把它作为一个额外的协变量放进 BT"
                          "（形式上与第 7 节的风格控制完全一样，只是协变量换成了「哪个 judge 判的」）。"
                          "<em>第二个办法更好，但需要提前计划——变更之后再想做就来不及了。</em>"),
        H3("② 让新模型只和强对手比（或只和弱对手比）"),
        P("BT 能修正赛程不均衡（第 2 节演示过），但它<strong>修正的能力是有限的</strong>："
          "一个模型只和 2 个对手比过 50 场，它的区间会非常宽——"
          "<em>而宽区间在按点估计排的榜单上是看不见的</em>。"
          "<strong>规范：榜单必须列出每个模型的总场次与对手数，"
          "并对场次低于阈值的模型显式标记「数据不足」而不是给它一个名次。</strong>"),
        H3("③ 在同一个榜单里混合「不同任务分布」的比较"),
        P("这是第 5 节传递性讨论的实践版本。如果早期的比较大多来自代码任务、"
          "后期大多来自写作任务，那么<strong>拟合出来的「总强度」实际上是一个随时间变化的加权平均</strong>，"
          "而这个权重从来没有人显式选择过。"
          "<em>症状是：一个模型的名次随着榜单积累新数据而缓慢漂移，"
          "而它自己一行代码都没改。</em>"),
        TABLE(["操作", "症状", "为什么不会报错", "规范"], [
            ["混合不同 judge", "早期模型与后期模型的相对位置莫名其妙", "BT 拟合对「谁判的」一无所知", "作废历史 或 双跑重叠期 + judge 作为协变量"],
            ["赛程严重不均衡", "某些模型的名次每周都在跳", "点估计照样算得出来", "列出场次与对手数；场次不足的标「数据不足」"],
            ["混合不同任务分布", "模型自己没变，名次却在漂", "总强度是一个隐含加权平均", "按任务分榜；总榜必须公布任务构成比例"],
        ]),
        CALLOUT("intuition", "三条的共同教训：<strong>排行榜的可信度，"
                             "主要不取决于拟合方法有多精巧，而取决于<em>喂进去的比较记录是不是同质的</em>。</strong>"
                             "<em>而「同质」这件事必须靠流程保证（记录 judge 指纹、监控赛程、按任务打标），"
                             "拟合阶段已经来不及了。</em>"),
    ])),
]

NB = [
    md("""# 04 · 从成对比较到排名（BT 拟合 / Elo 顺序依赖 / 自举区间 / 传递性 / 主动配对 / 风格控制）

目标：把一堆「A 赢 B」变成一个**带误差棒、带名次区间、带风格控制列**的排行榜。

本 notebook 你会亲手实现：
1. **Bradley–Terry 的 MLE 拟合** —— 复用模块 02 的逻辑回归，加正则化处理全胜/全败
2. **朴素胜率 vs BT** —— 对手强度不同时，朴素胜率错得有多离谱
3. **在线 Elo 的顺序依赖** —— 同一批数据换个顺序，名次会变吗
4. **自举区间与名次区间** —— 「排行榜上相差 20 分算不算差距」的定量回答
5. **传递性违反的检测** —— 三元环计数 + 分任务拟合
6. **主动配对 vs 随机配对** —— 同样预算下区间能窄多少
7. **风格控制 BT** —— 把模块 02 的去偏接进排名，输出 Δrank

> 心智模型：**看区间，不看名次。而所有这些统计工具的前提，
> 是 judge 没有共有的系统偏差——所以偏差探针永远排在排名拟合之前。**"""),

    md("""## 1 · Bradley–Terry：拟合与基准固定"""),

    code("""import math, json, itertools
from collections import Counter, defaultdict
import numpy as np

def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

def fit_bt(pairs, n_models, l2=0.01, lr=0.5, iters=4000):
    \"\"\"pairs: [(i, j, y)]，y=1 表示 i 赢 j。返回中心化后的 theta。
    L2 正则处理全胜/全败导致的发散（等价于给 theta 一个高斯先验）。\"\"\"
    I = np.array([p[0] for p in pairs])
    J = np.array([p[1] for p in pairs])
    Y = np.array([p[2] for p in pairs], dtype=float)
    theta = np.zeros(n_models)
    for _ in range(iters):
        z = theta[I] - theta[J]
        p = sigmoid(z)
        err = p - Y
        grad = np.zeros(n_models)
        np.add.at(grad, I, err)
        np.add.at(grad, J, -err)
        grad = grad / len(Y) + l2 * theta
        theta -= lr * grad
    return theta - theta.mean()          # 固定基准：中心化（只有差值有意义）

def elo_from_theta(theta, base=1000.0):
    return base + (400 / math.log(10)) * np.asarray(theta)

# 造数据：8 个模型，真实强度已知
rng = np.random.default_rng(0)
N_MODELS = 8
true_theta = np.array([1.4, 1.1, 0.7, 0.3, 0.0, -0.4, -0.9, -1.5])

def simulate_pairs(true_theta, n_pairs, rng, pair_fn=None):
    n = len(true_theta)
    out = []
    for _ in range(n_pairs):
        if pair_fn is None:
            i, j = rng.choice(n, size=2, replace=False)
        else:
            i, j = pair_fn(rng)
        y = int(rng.random() < sigmoid(true_theta[i] - true_theta[j]))
        out.append((int(i), int(j), y))
    return out

pairs = simulate_pairs(true_theta, 12000, rng)
theta_hat = fit_bt(pairs, N_MODELS)
print(f"{'模型':>6}{'真实 theta':>12}{'拟合 theta':>12}{'真实 Elo':>10}{'拟合 Elo':>10}")
for k in range(N_MODELS):
    print(f'M{k:<5}{true_theta[k]:>12.3f}{theta_hat[k]:>12.3f}'
          f'{elo_from_theta(true_theta - true_theta.mean())[k]:>10.0f}'
          f'{elo_from_theta(theta_hat)[k]:>10.0f}')

corr = np.corrcoef(true_theta, theta_hat)[0, 1]
assert corr > 0.99, 'BT 应当能几乎完美地还原真实强度'
assert abs(theta_hat.mean()) < 1e-6, '必须中心化，否则绝对值没有意义'
print(f'\\n拟合与真值的相关: {corr:.4f}')
print('✅ BT 就位。注意 theta 被中心化了——只有差值有意义，加一个常数所有预测都不变。')"""),

    code("""# theta 差值 → 胜率，以及 Elo 差 → 胜率的换算
print(f"{'theta 差':>10}{'胜率':>10}{'Elo 差':>10}")
for d in [0.0, 0.115, 0.3, 0.5, 1.0, 2.0]:
    print(f'{d:>10.3f}{sigmoid(d):>10.1%}{d * 400 / math.log(10):>10.0f}')

wr_20elo = sigmoid(20 * math.log(10) / 400)
print(f'\\n**20 个 Elo 分 = {wr_20elo:.1%} 的胜率**')
assert abs(wr_20elo - 0.5288) < 1e-3
n_needed = math.ceil(4 * 0.25 / (wr_20elo - 0.5) ** 2)
print(f'要把 {wr_20elo:.1%} 与 50% 区分开（z=2），需要约 {n_needed:,} 场直接对局')
assert n_needed > 1000
print('✅ 而 Arena 类榜单上一对模型的直接对局往往只有几百场——')
print('   所以「相差 20 分」这件事，单靠直接对局是分辨不出来的。')"""),

    md("""## 2 · 朴素胜率错在哪：对手强度不一样"""),

    code("""def naive_winrate(pairs, n_models):
    w = np.zeros(n_models); t = np.zeros(n_models)
    for i, j, y in pairs:
        t[i] += 1; t[j] += 1
        w[i] += y; w[j] += 1 - y
    return np.where(t > 0, w / np.maximum(t, 1), 0.5)

# 构造一个不均衡的赛程：M2 专挑弱对手，M5 专挑强对手
def biased_pairing(rng):
    r = rng.random()
    if r < 0.35:
        return 2, int(rng.integers(6, 8))       # M2 只打 M6/M7（最弱的两个）
    if r < 0.70:
        return 5, int(rng.integers(0, 2))       # M5 只打 M0/M1（最强的两个）
    i, j = rng.choice(8, size=2, replace=False)
    return int(i), int(j)

rng = np.random.default_rng(3)
pairs_b = simulate_pairs(true_theta, 16000, rng, pair_fn=biased_pairing)
naive = naive_winrate(pairs_b, N_MODELS)
theta_b = fit_bt(pairs_b, N_MODELS)

rank_true = np.argsort(-true_theta)
rank_naive = np.argsort(-naive)
rank_bt = np.argsort(-theta_b)
print(f"{'真实排名':<28}{'朴素胜率排名':<28}{'BT 排名'}")
print(f"{str([f'M{i}' for i in rank_true]):<28}"
      f"{str([f'M{i}' for i in rank_naive]):<28}"
      f"{str([f'M{i}' for i in rank_bt])}")

def spearman(a, b):
    ra = np.argsort(np.argsort(-np.asarray(a)))
    rb = np.argsort(np.argsort(-np.asarray(b)))
    ra, rb = ra - ra.mean(), rb - rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra ** 2).sum() * (rb ** 2).sum()))

s_naive = spearman(true_theta, naive)
s_bt = spearman(true_theta, theta_b)
print(f'\\n与真实强度的 Spearman: 朴素胜率 {s_naive:.3f} | BT {s_bt:.3f}')
assert s_bt > s_naive
assert s_bt > 0.99, 'BT 应当完全还原真实排名'
print(f'M2（真实第 3）朴素胜率 {naive[2]:.1%}（专挑最弱的两个）'
      f'→ 朴素排第 {list(rank_naive).index(2)+1} 名，BT 排第 {list(rank_bt).index(2)+1} 名')
print(f'M5（真实第 6）朴素胜率 {naive[5]:.1%}（专挑最强的两个）'
      f'→ 朴素排第 {list(rank_naive).index(5)+1} 名，BT 排第 {list(rank_bt).index(5)+1} 名')
print('\\n✅ 朴素胜率把 M2 抬到了 M1 之上、把 M5 压到了 M6 之下——纯粹是赛程造成的。')
print('   BT 通过同时估计所有模型的强度，把这两个错位都修正了回来。')"""),

    md("""## 3 · 在线 Elo 的顺序依赖：同一批数据，不同的名次"""),

    code("""def online_elo(pairs, n_models, K=0.05, init=None):
    theta = np.zeros(n_models) if init is None else np.array(init, dtype=float)
    for i, j, y in pairs:
        p = sigmoid(theta[i] - theta[j])
        upd = K * (y - p)
        theta[i] += upd
        theta[j] -= upd
    return theta - theta.mean()

rng = np.random.default_rng(7)
orders = []
for trial in range(30):
    perm = rng.permutation(len(pairs))
    shuffled = [pairs[k] for k in perm]
    th = online_elo(shuffled, N_MODELS, K=0.05)
    orders.append(np.argsort(np.argsort(-th)))     # 每个模型的名次
orders = np.array(orders)

print(f"{'模型':>6}{'名次范围':>14}{'名次标准差':>12}")
for k in range(N_MODELS):
    lo, hi = orders[:, k].min() + 1, orders[:, k].max() + 1
    print(f'M{k:<5}{f"{lo}-{hi}":>14}{orders[:, k].std():>12.2f}')

n_changed = int((orders.std(axis=0) > 0).sum())
theta_bt_fixed = fit_bt(pairs, N_MODELS)
print(f'\\n30 次随机打乱顺序后，有 {n_changed}/{N_MODELS} 个模型的名次发生过变化')
assert n_changed > 0, '在线 Elo 必然存在顺序依赖'
for trial in range(3):
    perm = rng.permutation(len(pairs))
    th2 = fit_bt([pairs[k] for k in perm], N_MODELS)
    assert np.allclose(th2, theta_bt_fixed, atol=1e-6), 'BT 与顺序无关'
print('✅ 批量 BT 对顺序完全不敏感（三次打乱后拟合结果一致到 1e-6）。')
print('   → 公开榜单用在线 Elo 必须固定并公布顺序，否则不可复现。')"""),

    md("""## 4 · 自举区间与名次区间：谁和谁其实是并列"""),

    code("""def bootstrap_bt(pairs, n_models, n_boot=400, seed=0, l2=0.01):
    \"\"\"对**比较记录**重采样（不是对模型），每次重新拟合。\"\"\"
    rng = np.random.default_rng(seed)
    n = len(pairs)
    thetas = np.zeros((n_boot, n_models))
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boot = [pairs[k] for k in idx]
        thetas[b] = fit_bt(boot, n_models, l2=l2, iters=1200)
    return thetas

pairs_small = simulate_pairs(true_theta, 2500, np.random.default_rng(11))
theta_pt = fit_bt(pairs_small, N_MODELS)
boots = bootstrap_bt(pairs_small, N_MODELS, n_boot=300, seed=1)

elo_pt = elo_from_theta(theta_pt)
elo_lo = elo_from_theta(np.percentile(boots, 2.5, axis=0))
elo_hi = elo_from_theta(np.percentile(boots, 97.5, axis=0))
ranks_boot = np.argsort(np.argsort(-boots, axis=1), axis=1) + 1
rank_lo = np.percentile(ranks_boot, 2.5, axis=0)
rank_hi = np.percentile(ranks_boot, 97.5, axis=0)

order = np.argsort(-elo_pt)
print(f"{'rank':>5}{'model':>7}{'Elo':>7}{'95% CI':>18}{'rank CI':>11}")
for r, k in enumerate(order, 1):
    print(f'{r:>5}{"M"+str(k):>7}{elo_pt[k]:>7.0f}'
          f'{f"[{elo_lo[k]:.0f}, {elo_hi[k]:.0f}]":>18}'
          f'{f"[{rank_lo[k]:.0f}, {rank_hi[k]:.0f}]":>11}')

width = float(np.mean(elo_hi - elo_lo))
print(f'\\n平均区间宽度: {width:.0f} Elo 分（{len(pairs_small):,} 场比较）')
assert width > 40, '两千多场比较对应的区间不可能很窄'
overlapping = sum(1 for a, b in itertools.combinations(range(N_MODELS), 2)
                  if elo_lo[a] <= elo_hi[b] and elo_lo[b] <= elo_hi[a])
print(f'区间重叠（即「并列」）的模型对: {overlapping} / {N_MODELS*(N_MODELS-1)//2}')
assert overlapping > 0
print('✅ 相当一部分名次其实是并列——读榜规则：**看区间，不看名次**。')"""),

    code("""# 「显著优于计数」：一个天然并列友好的排序方式
def significantly_better_count(lo, hi):
    n = len(lo)
    return np.array([sum(1 for j in range(n) if j != i and lo[i] > hi[j]) for i in range(n)])

sig = significantly_better_count(elo_lo, elo_hi)
print(f"{'model':>7}{'Elo':>7}{'显著优于':>10}")
for k in np.argsort(-sig):
    print(f'{"M"+str(k):>7}{elo_pt[k]:>7.0f}{sig[k]:>10}')
assert sig.sum() < N_MODELS * (N_MODELS - 1), '不可能每一对都显著'
assert sig[np.argmax(elo_pt)] >= sig[np.argmin(elo_pt)], '最强的模型显著优于的数量应当最多'

# 样本量翻倍看这个数怎么涨
pairs_big = simulate_pairs(true_theta, 10000, np.random.default_rng(11))
boots_big = bootstrap_bt(pairs_big, N_MODELS, n_boot=200, seed=1)
lo_big = elo_from_theta(np.percentile(boots_big, 2.5, axis=0))
hi_big = elo_from_theta(np.percentile(boots_big, 97.5, axis=0))
sig_big = significantly_better_count(lo_big, hi_big)
print(f'\\n显著优于计数之和: {len(pairs_small):,} 场 → {sig.sum()} | '
      f'{len(pairs_big):,} 场 → {sig_big.sum()}')
assert sig_big.sum() > sig.sum(), '样本量增大，能分辨的对更多'
print('✅ 「显著优于几个」这个数比 Elo 点估计更抗噪，也天然处理并列。')
print('   它随样本量单调上升——这条曲线本身就是「还要跑多少场」的直接指引。')"""),

    md("""## 5 · 传递性：三元环检测与分任务拟合"""),

    code("""def cycle_rate(pairs, n_models, min_games=15):
    \"\"\"三元环比例：枚举三元组，看是否形成 A>B>C>A。只统计三条边都有足够场次的三元组。\"\"\"
    wins = defaultdict(lambda: [0, 0])
    for i, j, y in pairs:
        a, b = (i, j) if i < j else (j, i)
        wins[(a, b)][0] += (y if i < j else 1 - y)
        wins[(a, b)][1] += 1
    def beats(a, b):
        key = (a, b) if a < b else (b, a)
        w, t = wins.get(key, (0, 0))
        if t < min_games:
            return None
        rate = w / t if a < b else 1 - w / t
        return rate > 0.5
    total = cyc = 0
    for a, b, c in itertools.combinations(range(n_models), 3):
        ab, bc, ca = beats(a, b), beats(b, c), beats(c, a)
        if None in (ab, bc, ca):
            continue
        total += 1
        if (ab and bc and ca) or ((not ab) and (not bc) and (not ca)):
            cyc += 1
    return (cyc / total if total else float('nan')), total

r_bt, n_tri = cycle_rate(pairs, N_MODELS)
print(f'一维真值下的三元环比例: {r_bt:.1%}（{n_tri} 个三元组）')

# 造一个二维能力的场景：两个维度，任务集混合 → 传递性会被破坏
rng = np.random.default_rng(19)
skill_2d = np.array([[1.6, -1.4], [-1.4, 1.6], [0.1, 0.1],
                     [1.0, -0.9], [-0.9, 1.0], [0.4, -0.3],
                     [-0.3, 0.4], [0.0, 0.0]])
pairs_2d = []
for _ in range(12000):
    i, j = rng.choice(N_MODELS, size=2, replace=False)
    dim = int(rng.integers(0, 2))                  # 这道题考哪个维度
    d = skill_2d[i, dim] - skill_2d[j, dim]
    pairs_2d.append((int(i), int(j), int(rng.random() < sigmoid(d))))

r_2d, n_tri2 = cycle_rate(pairs_2d, N_MODELS)
print(f'二维能力下的三元环比例: {r_2d:.1%}（{n_tri2} 个三元组）')
assert r_2d > r_bt, '能力是多维时，传递性违反显著增多'
print('\\n✅ 三元环比例从一维的几个百分点涨到二维的一大截——')
print('   这不是 judge 出错，而是「一个标量」这个模型本身不够用。')"""),

    code("""# 更有信息量的检测：分任务拟合，看排名一致不一致
pairs_dim0 = [(i, j, int(np.random.default_rng(i*1000+j).random() < sigmoid(skill_2d[i,0]-skill_2d[j,0])))
              for i, j, _ in pairs_2d[:6000]]
sub0, sub1 = [], []
rng = np.random.default_rng(23)
for _ in range(8000):
    i, j = rng.choice(N_MODELS, size=2, replace=False)
    sub0.append((int(i), int(j), int(rng.random() < sigmoid(skill_2d[i,0]-skill_2d[j,0]))))
    sub1.append((int(i), int(j), int(rng.random() < sigmoid(skill_2d[i,1]-skill_2d[j,1]))))

th_all = fit_bt(pairs_2d, N_MODELS)
th0 = fit_bt(sub0, N_MODELS)
th1 = fit_bt(sub1, N_MODELS)
print(f"{'model':>7}{'总榜':>9}{'子榜A':>9}{'子榜B':>9}")
for k in range(N_MODELS):
    print(f'{"M"+str(k):>7}{th_all[k]:>9.2f}{th0[k]:>9.2f}{th1[k]:>9.2f}')

s01 = spearman(th0, th1)
top_all = int(np.argmax(th_all))
print(f'\\n两个子榜之间的 Spearman: {s01:.3f}')
print(f'总榜第一是 M{top_all}；它在子榜A是第 {list(np.argsort(-th0)).index(top_all)+1} 名、'
      f'子榜B是第 {list(np.argsort(-th1)).index(top_all)+1} 名')
assert s01 < 0.5, '两个维度的排名应当显著不一致'
print('✅ 总榜第一在两个子榜上都不是第一——这不矛盾：')
print('   **总榜是各子任务按「任务集构成比例」这个隐含权重加权的结果**，而这个权重往往没人显式选过。')
print('   → 分任务榜比总榜更有决策价值。')"""),

    md("""## 6 · 主动配对：同样预算，区间能窄多少"""),

    code("""def pair_info(theta, i, j):
    \"\"\"单场比较的期望信息量：预测胜率的二元熵。\"\"\"
    p = float(sigmoid(theta[i] - theta[j]))
    if p <= 0 or p >= 1:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

def collect(strategy, n_rounds, true_theta, seed=0, eps=0.15, batch=50):
    \"\"\"strategy: 'random' | 'active'。每 batch 场重新拟合一次当前估计。\"\"\"
    rng = np.random.default_rng(seed)
    n = len(true_theta)
    got, theta_cur = [], np.zeros(n)
    for r in range(n_rounds // batch):
        for _ in range(batch):
            if strategy == 'random' or rng.random() < eps:
                i, j = rng.choice(n, size=2, replace=False)
            else:
                cands = [(pair_info(theta_cur, a, b), a, b)
                         for a, b in itertools.combinations(range(n), 2)]
                _, i, j = max(cands, key=lambda t: t[0] + rng.normal(0, 0.02))
            y = int(rng.random() < sigmoid(true_theta[i] - true_theta[j]))
            got.append((int(i), int(j), y))
        theta_cur = fit_bt(got, n, iters=800)
    return got

def adjacent_diff_width(boots, true_theta):
    # 相邻名次之间「强度差」的自举区间宽度——这才是主动配对真正优化的量
    order = np.argsort(-np.asarray(true_theta))
    widths = []
    for a, b in zip(order, order[1:]):
        d = boots[:, a] - boots[:, b]
        widths.append(np.percentile(d, 97.5) - np.percentile(d, 2.5))
    return float(np.mean(widths))

def distinguishable_pairs(lo, hi):
    n = len(lo)
    return sum(1 for i, j in itertools.combinations(range(n), 2)
               if lo[i] > hi[j] or lo[j] > hi[i])

BUDGET = 3000
res = {}
print(f"{'策略':<8}{'平均区间宽度':>14}{'相邻差区间宽度':>16}{'可区分的对':>12}")
for strat in ['random', 'active']:
    data = collect(strat, BUDGET, true_theta, seed=5)
    bo = bootstrap_bt(data, N_MODELS, n_boot=200, seed=2)
    lo, hi = np.percentile(bo, 2.5, axis=0), np.percentile(bo, 97.5, axis=0)
    elo_lo_, elo_hi_ = elo_from_theta(lo), elo_from_theta(hi)
    w_mean = float(np.mean(elo_hi_ - elo_lo_))
    w_adj = adjacent_diff_width(bo, true_theta)
    n_dist = distinguishable_pairs(elo_lo_, elo_hi_)
    res[strat] = dict(w_mean=w_mean, w_adj=w_adj, n_dist=n_dist, data=data)
    print(f'{strat:<8}{w_mean:>14.1f}{w_adj:>16.3f}{n_dist:>12}')

assert res['active']['w_adj'] < res['random']['w_adj'], '主动配对应当让相邻名次更容易分开'
print(f'\\n相邻名次的强度差区间: 主动配对窄了 '
      f'{1 - res["active"]["w_adj"]/res["random"]["w_adj"]:.0%}')
assert res['active']['n_dist'] < res['random']['n_dist']
print(f'但「可区分的模型对」总数反而少了: {res["random"]["n_dist"]} → {res["active"]["n_dist"]}')

# 原因：主动配对下，强弱悬殊的对被比得更少
def pair_counts(data, n):
    c = np.zeros((n, n))
    for i, j, _ in data:
        c[i, j] += 1; c[j, i] += 1
    return c
c_rand = pair_counts(res['random']['data'], N_MODELS)
c_act = pair_counts(res['active']['data'], N_MODELS)
far = abs(true_theta[0] - true_theta[-1])
print(f'\\n最强 vs 最弱（theta 差 {far:.1f}）的直接对局数: '
      f'随机 {c_rand[0,-1]:.0f} 场 → 主动 {c_act[0,-1]:.0f} 场')
assert c_act[0, -1] < c_rand[0, -1]
print('\\n✅ 这是本节最诚实的结论：**主动配对不是「全面更好」，而是「把精度搬了个地方」。**')
print('   它把预算从「结果已知的悬殊对局」搬到「难分胜负的相邻名次」上——')
print('   相邻名次因此更容易分开，但悬殊对的估计变得完全依赖模型外推，')
print('   而那恰恰是传递性假设最可能失效的地方。所以要保留 eps≥0.1 的随机配对做覆盖。')"""),

    md("""## 7 · 风格控制 BT：把去偏接进排名"""),

    code("""def fit_bt_with_covariates(pairs, X, n_models, l2=0.01, l2_gamma=0.0,
                           lr=1.0, iters=20000):
    \"\"\"logit P(i>j) = (theta_i - theta_j) + gamma^T (x_i - x_j)。
    X: (n_models, d) 每个模型的平均风格特征（已标准化）。返回 (theta, gamma)。
    注意 gamma 用单独（更弱的）正则：它是**一个全局参数**，
    对它做和 theta 同样强度的收缩会系统性低估风格效应。\"\"\"
    I = np.array([p[0] for p in pairs]); J = np.array([p[1] for p in pairs])
    Y = np.array([p[2] for p in pairs], dtype=float)
    X = np.asarray(X, dtype=float)
    d = X.shape[1]
    theta = np.zeros(n_models); gamma = np.zeros(d)
    DX = X[I] - X[J]
    for _ in range(iters):
        z = theta[I] - theta[J] + DX @ gamma
        err = sigmoid(z) - Y
        g_theta = np.zeros(n_models)
        np.add.at(g_theta, I, err); np.add.at(g_theta, J, -err)
        theta -= lr * (g_theta / len(Y) + l2 * theta)
        gamma -= lr * (DX.T @ err / len(Y) + l2_gamma * gamma)
    return theta - theta.mean(), gamma

# 造数据：真实质量 + 风格。judge 对风格有偏好（gamma_true > 0）
rng = np.random.default_rng(29)
quality = np.array([1.2, 0.9, 0.6, 0.3, 0.0, -0.3, -0.7, -1.2])
style = np.array([[-0.8], [1.5], [0.2], [-1.0], [0.0], [1.2], [-0.4], [0.6]])  # 标准化后的"长度/排版"
GAMMA_TRUE = 0.8

pairs_style = []
for _ in range(20000):
    i, j = rng.choice(N_MODELS, size=2, replace=False)
    z = (quality[i] - quality[j]) + GAMMA_TRUE * (style[i, 0] - style[j, 0])
    pairs_style.append((int(i), int(j), int(rng.random() < sigmoid(z))))

th_raw = fit_bt(pairs_style, N_MODELS)
th_sc, gamma_hat = fit_bt_with_covariates(pairs_style, style, N_MODELS)
print(f'拟合的风格系数 gamma = {gamma_hat[0]:.3f}（真值 {GAMMA_TRUE}）')
assert abs(gamma_hat[0] - GAMMA_TRUE) < 0.2

rank_raw = np.argsort(np.argsort(-th_raw)) + 1
rank_sc = np.argsort(np.argsort(-th_sc)) + 1
print(f"\\n{'model':>7}{'原始 Elo':>11}{'风格控制 Elo':>15}{'原名次':>8}{'控制后':>8}{'Δrank':>8}{'风格':>8}")
for k in np.argsort(rank_raw):
    print(f'{"M"+str(k):>7}{elo_from_theta(th_raw)[k]:>11.0f}'
          f'{elo_from_theta(th_sc)[k]:>15.0f}{rank_raw[k]:>8}{rank_sc[k]:>8}'
          f'{rank_raw[k]-rank_sc[k]:>+8}{style[k,0]:>8.1f}')

corr_sc = np.corrcoef(quality, th_sc)[0, 1]
corr_raw = np.corrcoef(quality, th_raw)[0, 1]
assert corr_sc > corr_raw, '风格控制后应当更接近真实质量'
print(f'\\n与真实质量的相关: 原始 {corr_raw:.3f} → 风格控制后 {corr_sc:.3f}')
print('✅ Δrank 这一列是最有信息量的输出：')
print('   风格分高的模型（M1、M5）控制后掉名次，风格分低的（M0、M3）升名次。')
print('   这未必是坏事（如果用户确实喜欢那种风格），但它必须被知道，而不是混在一个总分里。')"""),

    md("""## ✏️ 练习 1：Elo 差与所需场次

实现 `elo_to_winrate(elo_diff)` 与 `games_for_elo_gap(elo_diff, target_z=2.0)`：
前者把 Elo 差换算成胜率（$\\sigma(\\Delta \\ln 10 / 400)$），
后者返回把该胜率与 50% 区分开所需的场次（$z^2 \\cdot 0.25 / (p-0.5)^2$，向上取整）。"""),

    code("""def elo_to_winrate(elo_diff):
    # TODO
    raise NotImplementedError

def games_for_elo_gap(elo_diff, target_z=2.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(elo_to_winrate(0) - 0.5) < 1e-12
assert abs(elo_to_winrate(400) - 10 / 11) < 1e-9      # 差 400 分 = 胜率 10:1
assert abs(elo_to_winrate(20) - 0.5288) < 1e-3
assert games_for_elo_gap(20) > games_for_elo_gap(100)
print(f"{'Elo 差':>8}{'胜率':>10}{'所需场次':>12}")
for d in [10, 20, 50, 100, 200]:
    print(f'{d:>8}{elo_to_winrate(d):>10.1%}{games_for_elo_gap(d):>12,}')
print('✅ 练习 1 通过：这张表就是「读榜时相差多少分才算真差距」的直接答案。')"""),

    md("""## ✏️ 练习 2：名次区间与并列判定

实现 `rank_intervals(boot_thetas)`：输入自举得到的 `(n_boot, n_models)` 参数矩阵，
返回每个模型的 `(点估计名次, 2.5% 分位名次, 97.5% 分位名次)`。
再实现 `tied_groups(lo, hi)`：返回所有「名次区间重叠」的模型对集合。"""),

    code("""def rank_intervals(boot_thetas):
    # TODO：名次 = 按 theta 降序的位次（从 1 开始）
    raise NotImplementedError

def tied_groups(lo, hi):
    # TODO：返回 [(i, j), ...]，i < j 且区间重叠
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
pt_r, lo_r, hi_r = rank_intervals(boots)
assert len(pt_r) == N_MODELS
assert all(lo_r[k] <= pt_r[k] <= hi_r[k] for k in range(N_MODELS))
ties = tied_groups(lo_r, hi_r)
assert all(i < j for i, j in ties)
print(f"{'model':>7}{'名次':>7}{'名次区间':>12}")
for k in np.argsort(pt_r):
    print(f'{"M"+str(k):>7}{pt_r[k]:>7.0f}{f"[{lo_r[k]:.0f}, {hi_r[k]:.0f}]":>12}')
print(f'\\n判定为并列的模型对: {[(f"M{i}", f"M{j}") for i, j in ties]}')
assert len(ties) > 0, '2500 场比较下必然有并列'
print('✅ 练习 2 通过：把「名次」报成区间，读者就不会去解读那些本来就分不开的差距。')"""),

    md("""## ✏️ 练习 3：比较图的连通性检查

实现 `is_connected(pairs, n_models, min_games=1)`：
把「比过至少 `min_games` 场」的模型对视为一条边，判断整个图是否连通（BFS 即可）。
不连通时 BT 参数在组之间不可识别。"""),

    code("""def is_connected(pairs, n_models, min_games=1):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert is_connected(pairs, N_MODELS) is True
# 构造一个断裂的赛程：M0-M3 一组，M4-M7 一组，两组从不交手
rng = np.random.default_rng(41)
split_pairs = []
for _ in range(3000):
    grp = [0, 1, 2, 3] if rng.random() < 0.5 else [4, 5, 6, 7]
    i, j = rng.choice(grp, size=2, replace=False)
    split_pairs.append((int(i), int(j), int(rng.random() < sigmoid(true_theta[i]-true_theta[j]))))
assert is_connected(split_pairs, N_MODELS) is False
assert is_connected(pairs, N_MODELS, min_games=100000) is False   # 阈值太高 → 无边
th_split = fit_bt(split_pairs, N_MODELS)
print('断裂赛程下拟合出的 theta:', np.round(th_split, 2))
print('组内 Spearman（M0-M3）:', round(spearman(true_theta[:4], th_split[:4]), 3))
print('✅ 练习 3 通过：组内排序仍然对，但**跨组的相对位置完全由正则化决定，没有数据支撑**。')
print('   所以比较图的连通性必须写进报告——不连通时跨组比较毫无意义。')"""),

    md("""## ✏️ 练习 4：风格贡献度

实现 `style_contribution(theta_raw, theta_sc)`：返回每个模型
`(原始 Elo, 控制后 Elo, 风格贡献的 Elo 分数, 名次变化)`，
风格贡献 = 原始 Elo − 控制后 Elo。"""),

    code("""def style_contribution(theta_raw, theta_sc):
    # TODO：返回一个 list，每项是 (elo_raw, elo_sc, style_elo, delta_rank)
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
contrib = style_contribution(th_raw, th_sc)
assert len(contrib) == N_MODELS
style_elos = np.array([c[2] for c in contrib])
assert np.corrcoef(style_elos, style[:, 0])[0, 1] > 0.9, '风格贡献必须与风格特征强相关'
assert abs(sum(c[3] for c in contrib)) < 1e-9, '名次变化之和必然为 0'
print(f"{'model':>7}{'原始':>9}{'控制后':>9}{'风格贡献':>10}{'Δrank':>8}")
for k in range(N_MODELS):
    r, sc_, st, dr = contrib[k]
    print(f'{"M"+str(k):>7}{r:>9.0f}{sc_:>9.0f}{st:>+10.0f}{dr:>+8}')
print('✅ 练习 4 通过：「风格贡献了多少 Elo 分」是一个可以直接放进榜单的列。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def elo_to_winrate(elo_diff):
    return float(sigmoid(elo_diff * math.log(10) / 400))

def games_for_elo_gap(elo_diff, target_z=2.0):
    p = elo_to_winrate(elo_diff)
    if abs(p - 0.5) < 1e-12:
        return float('inf')
    return math.ceil(target_z ** 2 * 0.25 / (p - 0.5) ** 2)"""),

    code("""# 练习 2 参考答案
def rank_intervals(boot_thetas):
    B = np.asarray(boot_thetas)
    ranks = np.argsort(np.argsort(-B, axis=1), axis=1) + 1
    pt = np.median(ranks, axis=0)
    lo = np.percentile(ranks, 2.5, axis=0)
    hi = np.percentile(ranks, 97.5, axis=0)
    return pt, lo, hi

def tied_groups(lo, hi):
    n = len(lo)
    return [(i, j) for i, j in itertools.combinations(range(n), 2)
            if lo[i] <= hi[j] and lo[j] <= hi[i]]"""),

    code("""# 练习 3 参考答案
def is_connected(pairs, n_models, min_games=1):
    cnt = defaultdict(int)
    for i, j, _ in pairs:
        a, b = (i, j) if i < j else (j, i)
        cnt[(a, b)] += 1
    adj = defaultdict(set)
    for (a, b), c in cnt.items():
        if c >= min_games:
            adj[a].add(b); adj[b].add(a)
    seen, stack = {0}, [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); stack.append(v)
    return len(seen) == n_models"""),

    code("""# 练习 4 参考答案
def style_contribution(theta_raw, theta_sc):
    e_raw = elo_from_theta(theta_raw)
    e_sc = elo_from_theta(theta_sc)
    r_raw = np.argsort(np.argsort(-np.asarray(theta_raw))) + 1
    r_sc = np.argsort(np.argsort(-np.asarray(theta_sc))) + 1
    return [(float(e_raw[k]), float(e_sc[k]), float(e_raw[k] - e_sc[k]),
             int(r_raw[k] - r_sc[k])) for k in range(len(theta_raw))]"""),

    md("""---
## 🧪 真实工程胶囊：排行榜的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 从 judge 结果表到排行榜（完整流程）
# ══════════════════════════════════════════════════════════════════
import pandas as pd, numpy as np
df = pd.read_json("judge_results.jsonl", lines=True)
# 必需列: model_a, model_b, verdict(A/B/tie), a_len_tokens, b_len_tokens, order, consistent

# 1) 只用 swap 一致的样本；不一致的记平局（模块 01/02）
df = df[df.consistent | (df.verdict == "tie")]

# 2) 平局按半分拆成两条记录（与 BT 的处理一致）
rows = []
for r in df.itertuples():
    if r.verdict == "tie":
        rows += [(r.model_a, r.model_b, 1, 0.5), (r.model_a, r.model_b, 0, 0.5)]
    else:
        rows.append((r.model_a, r.model_b, int(r.verdict == "A"), 1.0))
# 注：带权重的 BT 需要在梯度里乘以 weight；简化做法是把平局拆成两条等权记录。

# 3) 连通性检查 —— 不连通时直接停止，不要出榜
assert is_connected(pairs, n_models), "比较图不连通，跨组排名无意义"

# 4) 拟合 + 自举 + 名次区间
theta = fit_bt(pairs, n_models, l2=0.01)
boots = bootstrap_bt(pairs, n_models, n_boot=1000)
pt, lo, hi = rank_intervals(boots)

# 5) 风格控制版：X 用每个模型的**平均**风格特征（标准化后）
X = np.column_stack([
    zscore(df.groupby("model").a_len_tokens.mean()),
    zscore(df.groupby("model").md_heading_count.mean()),
    zscore(df.groupby("model").list_item_count.mean()),
])
theta_sc, gamma = fit_bt_with_covariates(pairs, X, n_models)

# ══════════════════════════════════════════════════════════════════
# B. 必须写进榜单页脚的六行
# ══════════════════════════════════════════════════════════════════
# judge 模型 + prompt 哈希 + 是否开 swap
# 拟合方法 + 正则化强度 + 基准如何固定
# 区间方法（对**比较记录**自举）+ 自举次数
# 比较总数 + 模型数 + 比较图连通性
# 配对策略（随机 / 主动 / 混合比例）
# 传递性检查结果 + 子榜之间的 Spearman

# ══════════════════════════════════════════════════════════════════
# C. 增量更新：什么时候可以不重拟合
# ══════════════════════════════════════════════════════════════════
# 新增比较 < 总量的 5%  → 用在线 Elo 做预览，正式榜单仍走批量 BT
# 新增了一个模型        → 必须重拟合（新模型会改变所有人的相对位置）
# 换了 judge / prompt   → **所有历史比较作废**，不能与新数据混拟合
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| BT vs 朴素胜率 | 朴素胜率被赛程污染；BT 同时估计所有强度 | 任何排行榜 |
| theta 与 Elo | Elo 是 BT 的仿射变换；20 Elo 分 = 52.9% 胜率 | 读榜心算 |
| Elo 顺序依赖 | 在线 Elo 的分数是「数据 + 处理顺序」的函数 | 选拟合方法 |
| 自举与名次区间 | 看区间不看名次；区间重叠即并列 | 报告规范 |
| 传递性 | 总榜第一在子榜上常常不是第一，这不矛盾 | 优先看子榜 |
| 主动配对 | 区间更窄，但强弱悬殊的对被比得更少，要留 ε 随机 | 预算分配 |
| 风格控制 BT | Δrank 是最有信息量的一列 | 诊断风格贡献 |

下一模块：**05 · 奖励模型与过优化**——judge 变成训练信号之后会发生什么，
RewardBench 类评测怎么做，以及 KL–奖励曲线上那个必然出现的拐点。""")
]
