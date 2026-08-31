# -*- coding: utf-8 -*-
"""C66 模块 02 · 结果判分与部分得分（判分器工程与它自己的评测）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（基准全景与五种判分方式）；"
                 "知道「单元测试」和「混淆矩阵」两个概念即可，统计部分现场推"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_outcome_scoring.ipynb'
                       '（变异测试算测试强度 / 判分器混淆矩阵与 Rogan–Gladen 校正 / '
                       '部分得分导致的排序翻转实验 / checkpoint rubric 的单调性检查 / '
                       '判分器 hack 检测器 / macro-micro 聚合差异）'),
    ("核心参考", "Jimenez et al., <em>SWE-bench</em>（ICLR 2024，F2P/P2P 判分设计）· "
                 "Rogan &amp; Gladen（1978，不完美检测下的患病率估计）· "
                 "Papadakis et al., <em>Mutation Testing Advances</em>（2019）· "
                 "Chowdhury et al. 一类关于 SWE-bench 测试强度与解法泄漏的后续分析 · "
                 "本课程 C10 模块 01（标注噪声）· C67（judge 类判分器）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("scorer-is-critical", "判分函数是评测系统里唯一不允许出错的组件", "".join([
        P("一个评测系统里，几乎每个组件出错都还有救：任务集有偏可以补任务，样本量不够可以多跑，"
          "harness 有 bug 可以修完重跑。<strong>只有判分函数出错是不可挽回的</strong>——"
          "因为它污染的不是某一次实验，而是<em>所有用它跑过的历史结论</em>，"
          "而且这种污染通常是<strong>系统性的、同方向的</strong>，不会随着样本量增加而被平均掉。"),
        MATH(r"\hat{p}_{\text{obs}} = p_{\text{true}}(1 - \beta) + (1 - p_{\text{true}})\alpha"),
        P("其中 $\\alpha$ 是判分器的假阳率（把失败判成成功），$\\beta$ 是假阴率（把成功判成失败）。"
          "这个式子有两个必须记住的推论："),
        OL([
            "<strong>偏差不随样本量消失</strong>：$n \\to \\infty$ 时 $\\hat{p}_{\\text{obs}} \\to "
            "p_{\\text{true}}(1-\\beta) + (1-p_{\\text{true}})\\alpha \\ne p_{\\text{true}}$。"
            "跑一万道题也救不了一个有 5% 假阳率的判分器。",
            "<strong>真实成功率越低，相对污染越严重</strong>：当 $p_{\\text{true}} = 0.05$、$\\alpha = 0.10$ 时，"
            "观测值约为 $0.05 \\times 0.95 + 0.95 \\times 0.10 \\approx 0.143$——<strong>虚高近三倍</strong>。"
            "这正是「越难的基准上，低分越不可信」的数学来源。",
        ]),
        DUAL(
            "打个不需要类比的直接说法：判分器就是这套测量系统的<em>零点</em>。"
            "零点偏了，你后面所有的读数都偏，而且偏的方向一致，"
            "多测几次只会让你<strong>更自信地相信一个错的数字</strong>。",
            "从估计量的角度，判分器误差引入的是<span class=\"term\">系统偏差</span>（bias）而非方差。"
            "评测里绝大多数工程投入（多 seed、多任务、置信区间）都在压方差，"
            "但 $\\text{MSE} = \\text{bias}^2 + \\text{var}$——"
            "<em>当 bias 是 0.10 而 var 的标准差只有 0.02 时，把方差再压一半是完全无意义的工作</em>。"
            "这条判断标准决定了你的下一小时该花在哪：先量 bias，再压 var。",
        ),
        CALLOUT("danger", "推论很实际：<strong>在你把评测规模从 100 题扩到 1000 题之前，"
                          "先花半天量一下判分器的 $\\alpha$ 和 $\\beta$。</strong>"
                          "做法在本模块第 5 节——只需要几十条已知正确解和已知错误解。"),
    ])),

    # ============================================================== 2
    ("execution-based", "执行式判分：测试强度决定判分强度", "".join([
        P("执行式判分（跑测试）是最客观的判分方式，但它的可信度完全取决于一件事："
          "<strong>那组测试有多强</strong>。测试弱到什么程度会出问题？看下面这个具体例子。"),
        CODE("""# 任务：修复 divide(a, b) 在 b == 0 时崩溃的问题

# 弱测试（只有一条）
def test_divide():
    assert divide(10, 0) is None          # ← 只检查了 b == 0

# 一个能通过弱测试、但语义完全错误的「解」
def divide(a, b):
    return None                            # ← 全部返回 None，测试照样绿

# 强测试
def test_divide_strong():
    assert divide(10, 0) is None
    assert divide(10, 2) == 5              # ← 正常路径必须保持正确（PASS_TO_PASS 的作用）
    assert divide(-9, 3) == -3
    assert divide(7, 2) == 3.5"""),
        P("这就是模块 01 里 <code>PASS_TO_PASS</code> 存在的全部理由的微缩版本。"
          "但 <code>PASS_TO_PASS</code> 只保证「原来对的还对」，它不保证「新行为的边界情况被覆盖」。"
          "要量化「测试有多强」，工业界的标准工具是<strong>变异测试</strong>（mutation testing）。"),
        H3("变异测试：用「故意注入的 bug」量测试强度"),
        OL([
            "对被测代码做<strong>微小的语义改动</strong>（把 <code>&gt;</code> 改成 <code>&gt;=</code>、"
            "把 <code>+</code> 改成 <code>-</code>、把返回值改成常量），每个改动叫一个<span class=\"term\">变异体</span>（mutant）；",
            "对每个变异体跑一遍测试组；",
            "测试<strong>失败</strong>了，说明这个变异体被「杀死」了——测试有能力发现这类错误；"
            "测试仍然<strong>全绿</strong>，说明变异体「存活」——这是测试的盲区；",
            "<strong>变异分数 = 被杀死的变异体 / 变异体总数</strong>。",
        ]),
        TABLE(["变异分数", "含义", "该怎么办"], [
            ["&gt; 0.9", "测试很强，判分可信", "可以直接用作判分器"],
            ["0.6 – 0.9", "测试中等，存在盲区", "接受，但在报告里注明；对高价值任务补测试"],
            ["&lt; 0.6", "<strong>测试太弱，判分器不可信</strong>", "这道任务的分数不应进入主指标——补测试或剔除"],
        ]),
        CALLOUT("warn", "变异测试在真实工程里的代价是<strong>时间</strong>：$m$ 个变异体 × 一次完整测试运行。"
                        "实践中的常规做法是<strong>只对判分测试做变异分析，且只在任务集构建阶段做一次</strong>"
                        "——它是任务集的质量属性，不是每次评测都要重算的东西。"
                        "把变异分数作为任务元数据存下来（呼应模块 01 的 schema），"
                        "之后就可以做「只用强测试任务重算一遍分数」这样的敏感性分析。"),
        DUAL(
            "一个很少被说破的事实：<strong>公开基准里，不同任务的测试强度差异极大</strong>。"
            "有的任务配了几十个断言、覆盖了所有边界；有的任务只有一条 <code>assert result is not None</code>。"
            "把它们等权平均成一个「成功率」，等于把一把精密卡尺和一根皮尺量出来的数字加起来求平均。",
            "形式化地说，任务 $i$ 的判分器有各自的 $(\\alpha_i, \\beta_i)$，"
            "总体观测成功率是 $\\frac{1}{N}\\sum_i [p_i(1-\\beta_i) + (1-p_i)\\alpha_i]$。"
            "<strong>只有当 $\\alpha_i, \\beta_i$ 在任务间近似同质时，总体校正才能用单一的 $(\\alpha,\\beta)$ 完成</strong>；"
            "否则必须分层校正。<em>这也是「按测试强度分层报告」比「报一个总分」更有信息量的原因。</em>",
        ),
    ])),

    # ============================================================== 3
    ("final-state", "终态匹配判分：状态抽象与等价类", "".join([
        P("对于没有测试可跑的任务（改机票、下订单、改配置），判分靠比对<strong>环境的最终状态</strong>。"
          "看起来简单，实际有三个必须显式做出的设计决策。"),
        H3("决策一：状态要抽象到哪一层"),
        TABLE(["抽象层级", "比什么", "问题"], [
            ["逐字节比对整个数据库", "全部字段", "<strong>必然失败</strong>：时间戳、自增 ID、日志表每次都不同"],
            ["比对<strong>相关表的相关字段</strong>", "订单状态、金额、航班号", "需要人工为每个任务标注「哪些字段相关」——这是主要的标注成本"],
            ["比对一个自定义的摘要函数", "<code>summarize(db) == expected</code>", "摘要函数写错 = 判分器有 bug，需要单独测试"],
        ]),
        H3("决策二：等价解怎么处理"),
        P("同一个目标常有多条合法路径，导致<strong>多个都正确的终态</strong>。"
          "例如「把用户的两张机票都改签到周五」，agent 可以先改 A 再改 B，也可以取消两张重新下单——"
          "两者的订单 ID 不同，但业务上都正确。处理方式有三种，按推荐度排序："),
        OL([
            "<strong>标注一组可接受终态</strong>（<code>expected ∈ {S1, S2, S3}</code>）——最可靠，标注成本最高；",
            "<strong>用不变量（invariant）代替快照</strong>：不比对具体状态，而是断言"
            "「这个用户在周五有两张有效机票」「总扣费不超过 X」——推荐做法，"
            "本质上是把终态匹配退化成一组<em>属性检查</em>；",
            "<strong>用 LLM judge 判断终态是否等价</strong>——最灵活，也把判分器的可信度问题引了进来（交给 C67）。",
        ]),
        CALLOUT("intuition", "<strong>把「终态匹配」重写成「不变量检查」，是这一节最有实操价值的一句话。</strong>"
                             "不变量天然处理等价解、天然忽略无关字段、天然可读（一行断言就说清了「什么叫做对了」），"
                             "而且它和执行式判分在形式上统一了——<em>一组断言，全过才算 1 分</em>。"),
        H3("决策三：过程中的越权动作算不算失败"),
        P("这是终态判分的一个结构性盲区：<strong>终态对了，不代表过程是可接受的</strong>。"
          "一个 agent 可能先误删了三条别的订单，再重建出正确的终态——快照比对完全看不出来。"
          "解决方式只有一个：<strong>把「过程中不允许发生的事」也写成断言</strong>"
          "（如「没有对本任务无关的记录做过写操作」），这需要环境提供写操作审计日志。"
          "<em>这条要求同时也是 C69 模块 05 审计日志的评测侧动机。</em>"),
    ])),

    # ============================================================== 4
    ("partial-credit", "部分得分与 checkpoint：给不给、怎么给、会不会翻转排序", "".join([
        P("二值判分（做完了才算分）最干净，但在难基准上会碰到一个现实问题：<strong>大量任务上所有 agent 都是 0 分</strong>，"
          "整个任务集退化成噪声（呼应模块 01 的信息量分析）。部分得分（partial credit）是解法，"
          "但它引入了一个必须被验证的风险：<strong>部分得分可能改变模型排序</strong>。"),
        H3("三种部分得分的形式"),
        TABLE(["形式", "怎么算", "适用场景", "风险"], [
            ["<strong>checkpoint 达成率</strong>", "把任务拆成有序的关键节点（找到相关文件 → 定位函数 → 改对逻辑 → 测试通过），算达成了几个", "长程任务、教学与归因", "checkpoint 的划分是人为的，划法不同排序可能不同"],
            ["<strong>子测试通过率</strong>", "不要求全部测试通过，按通过比例给分", "代码类任务，天然有多个测试", "<strong>鼓励「广撒网式部分修复」</strong>，可能奖励一个语义错误但碰巧过了半数测试的解"],
            ["<strong>加权 rubric</strong>", "为每个要求项打分再加权求和", "有多个并列要求的任务（写报告、改配置）", "权重是主观的；必须做敏感性分析（呼应 C65-03）"],
        ]),
        CALLOUT("danger", "<strong>部分得分最危险的性质：它可以在不改变任何一次运行结果的前提下，翻转两个模型的排名。</strong>"
                          "假设 A 擅长「做完一部分就卡住」，B 擅长「要么全对要么完全跑偏」。"
                          "二值判分下 B 赢，checkpoint 判分下 A 赢——<em>两个结论都是真的，它们回答的是不同的问题</em>。"
                          "notebook 第 3 节会构造出这个翻转并量化它出现的频率。"),
        H3("checkpoint 设计的三条硬规则"),
        OL([
            "<strong>单调</strong>：完成了第 $k$ 个 checkpoint 必然意味着完成了第 $k-1$ 个。"
            "不单调的 checkpoint 集合会让「达成率」这个数字失去意义（可以跳着达成）。",
            "<strong>可自动判定</strong>：每个 checkpoint 都要有一段确定性代码能判定它有没有达成。"
            "需要人来看的 checkpoint 不属于本模块，属于 C67。",
            "<strong>最后一个 checkpoint 必须等价于二值判分的成功条件</strong>。"
            "这条保证了「checkpoint 达成率 = 1」和「任务成功」是同一件事，"
            "从而使部分得分成为二值判分的<em>严格加细</em>，而不是另一套指标。",
        ]),
        DUAL(
            "怎么决定给不给部分得分？一个简单的判断：<strong>看你要拿这个数字做什么决策</strong>。"
            "要决定「这个 agent 能不能上线自动处理退款」——用二值（甚至用 pass^k），"
            "因为完成 60% 的退款流程在产品上等于 0。"
            "要决定「下一步该改进什么」——用 checkpoint，因为你需要知道它卡在哪一步。",
            "更严谨的说法：二值判分对应<span class=\"term\">决策效用</span>（decision utility）——"
            "指标应当与部署时的真实收益函数对齐；checkpoint 对应<span class=\"term\">诊断信息量</span>"
            "（diagnostic information）——指标应当最大化对失败原因的可辨识性。"
            "<em>两者服务于不同目标，同一份报告里应当<strong>同时</strong>出现，而不是二选一。</em>"
            "报告的规范写法是：主指标二值 + 附表 checkpoint 分布。",
        ),
    ])),

    # ============================================================== 5
    ("meta-scoring", "怎么评测判分器自己：金标准集与 Rogan–Gladen 校正", "".join([
        P("既然判分器的偏差不可挽回，就必须先测量它。方法出乎意料地便宜：<strong>构造一个金标准集</strong>。"),
        H3("金标准集怎么造"),
        TABLE(["样本类型", "怎么获得", "用来估计什么", "推荐数量"], [
            ["<strong>已知正确解</strong>", "基准自带的参考补丁（gold patch）；或人工写的正确解", "假阴率 $\\beta$（判分器把对的判成错）", "每类任务 30–50 条"],
            ["<strong>已知错误解</strong>", "把参考补丁做微小破坏（改掉一个符号）；或收集历史上被人工确认为错误的 agent 输出", "假阳率 $\\alpha$（判分器把错的判成对）", "每类任务 30–50 条"],
            ["<strong>已知等价解</strong>", "对参考补丁做语义保持的重写（改变量名、换等价写法）", "判分器对<em>形式差异</em>是否过敏（这是终态匹配判分最常见的假阴来源）", "10–20 条"],
        ]),
        P("跑一遍就能填出一个 2×2 混淆矩阵，从而得到 $\\alpha$ 与 $\\beta$，再用 Rogan–Gladen 公式反解真实成功率："),
        MATH(r"\hat{p}_{\text{corrected}} = \frac{\hat{p}_{\text{obs}} - \alpha}{1 - \beta - \alpha}"),
        CALLOUT("warn", "校正公式有两个必须知道的陷阱："
                        "<strong>① 校正后的值可能落到 $[0,1]$ 之外</strong>（当 $\\hat{p}_{\\text{obs}} &lt; \\alpha$ 时为负）——"
                        "这不是 bug，而是在告诉你「观测到的成功全部可以由假阳性解释」，"
                        "此时正确的结论是「无法区分于零」，而不是把它截断到 0 就当没事发生。"
                        "<strong>② 校正会放大方差</strong>：分母 $1-\\beta-\\alpha$ 小于 1，"
                        "所以校正后的置信区间比校正前更宽——<em>这是诚实的代价，不是缺陷</em>。"),
        H3("为什么这件事几乎没人做"),
        P("坦白说，公开的 agent 评测报告里几乎看不到判分器的 $\\alpha/\\beta$。原因不是它难，而是它<strong>不讨好</strong>："
          "做了之后，你的分数只会变得更保守、误差棒只会变得更宽。"
          "但如果你的评测是要用来<em>做决策</em>（发不发布、投不投产）而不是用来<em>发布数字</em>，"
          "这半天的投入是整个评测流程里性价比最高的一步。"),
    ])),

    # ============================================================== 6
    ("hacking", "判分器会被 hack 的六种方式", "".join([
        P("只要判分函数是一段代码，就存在「让这段代码返回 1 但没真的完成任务」的路径。"
          "agent 不需要有「作弊意图」才会做这些事——<strong>它只是在优化你给的目标</strong>。"),
        TABLE(["hack 方式", "具体表现", "检测手段"], [
            ["<strong>改测试</strong>", "直接修改判分用的测试文件让它通过", "<strong>硬规则：patch 触碰测试文件即判 0</strong>（这是必须写死的第一道闸门）"],
            ["<strong>删测试 / 跳过测试</strong>", "加上 <code>@pytest.mark.skip</code>、改 <code>conftest.py</code>、改配置排除某些用例", "比对运行前后的<strong>测试收集数量</strong>；收集到的用例变少即判 0"],
            ["<strong>特判输入</strong>", "对判分用到的具体输入写 <code>if</code> 分支返回期望值", "变异测试（第 2 节）+ 用<strong>留出测试</strong>（held-out tests）复判：判分测试之外再准备一组不公开的测试"],
            ["<strong>污染判分环境</strong>", "改环境变量、打 monkey patch、改全局配置让断言恒真", "在<strong>干净的新容器</strong>里只应用 patch 后重跑（不复用 agent 的运行时环境）"],
            ["<strong>猜答案</strong>", "在开放问答类任务上枚举高频答案", "答案空间统计：某个答案在多任务上被反复给出即为信号"],
            ["<strong>钻等价类的空子</strong>", "在终态匹配下构造一个「表面字段全对、但业务上错误」的状态", "把终态比对升级为不变量检查（第 3 节）+ 加过程约束断言"],
        ]),
        CALLOUT("danger", "第一条值得单独强调：<strong>「patch 是否触碰测试文件」这个检查必须无条件写死在判分流水线里，"
                          "而不是作为一条可选的启发式</strong>。它是唯一一个「零假阳性、零成本、拦掉最严重作弊」的检查。"
                          "在你自建的任何代码类任务集里，这应该是第一行判分代码。"),
        DUAL(
            "为什么会出现这些行为？不需要归因于「模型学坏了」。"
            "一个 agent 被要求「让测试通过」，而修改测试文件<em>确实</em>能让测试通过——"
            "<strong>问题出在规格写得不完整，不在 agent 上</strong>。"
            "你要的是「修好代码」，你说的是「让测试变绿」，两者之间的缝隙就是 hack 的全部空间。",
            "这是 <span class=\"term\">Goodhart's law</span> 在评测端的直接体现："
            "当一个度量成为目标，它就不再是一个好的度量。"
            "形式化地说，判分函数 $S$ 是真实目标 $U$ 的代理；优化压力会把解推向"
            "$\\arg\\max_x S(x)$ 而非 $\\arg\\max_x U(x)$，两者的差集就是 hack 空间。"
            "<em>C67 模块 05 会在奖励模型的语境下重讲同一件事（reward hacking / over-optimization），"
            "C69 则从安全角度讲同一件事的攻击面版本。</em>",
        ),
    ])),

    # ============================================================== 7
    ("aggregation", "从单任务分数到报告数字：聚合方式会改变结论", "".join([
        P("最后一步看起来最无害，实际上是报告里最容易产生误导的一步。"
          "同一批结果，换一种聚合方式，结论可以完全不同。"),
        TABLE(["聚合方式", "定义", "什么时候用", "陷阱"], [
            ["<strong>micro 平均</strong>", "所有任务一视同仁求平均", "任务分布本身就代表目标分布时", "任务多的子集会主导总分——如果某个仓库贡献了 40% 的任务，总分基本就是那个仓库的分数"],
            ["<strong>macro 平均</strong>", "先按子集（仓库/领域/难度）求平均，再对子集求平均", "希望每个子集等权、防止大子集主导", "小子集的噪声被放大到与大子集同权"],
            ["<strong>加权平均</strong>", "按业务重要性/流量占比加权", "报告面向产品决策时", "权重来源必须写进报告，否则不可复现"],
            ["<strong>按 checkpoint 分层</strong>", "分别报告「完全成功 / 部分完成 / 完全失败」三档比例", "诊断用", "三个数字读者容易只看第一个"],
        ]),
        CALLOUT("intuition", "一条可以直接执行的报告规范：<strong>主表报 micro，附表必须给出 macro 与按子集的分解。</strong>"
                             "如果 micro 与 macro 的排序不一致，<em>这件事本身就是报告里最重要的发现</em>，"
                             "必须显式写出来——它意味着「谁更强」这个问题的答案取决于你关心哪个子集。"),
        P("最后一句提醒，它连接到下一个模块：<strong>本模块讲的所有东西，都只回答了「任务完成了没有」。</strong>"
          "两个 micro 分数相同的 agent，可能一个用了 8 步、一个用了 47 步；"
          "一个从不越权、一个顺手删了三条无关记录。这些差异<em>全部</em>发生在结果层之外，"
          "需要轨迹层的指标才能看见——那是 03 模块的内容。"),
    ])),
    # ============================================================== 8
    ("triage", "判分不确定时怎么办：三级复核流水线", "".join([
        P("前面几节默认判分器要么判对要么判错。真实系统里还有第三种状态：<strong>判分器自己也不确定</strong>——"
          "测试超时、终态部分匹配、validator 抛异常。把这类样本硬塞进 0 或 1 都是错的，"
          "正确做法是设计一条<strong>三级复核流水线</strong>。"),
        ASCII("""
   全部 rollout
        │
   ┌────▼──────────────────┐   判分器给出 (label, confidence)
   │ L1 · 自动判分（99%）  │   confidence 高 → 直接采信，零人力
   └────┬──────────────────┘
        │ 低置信 / 异常 / 抛错
   ┌────▼──────────────────┐   规则复核：重跑一次、换容器、放宽超时
   │ L2 · 自动分诊（~1%）  │   仍不确定则升级
   └────┬──────────────────┘
        │
   ┌────▼──────────────────┐   人工判定，并把判定结果回灌成新的金标准样本
   │ L3 · 人工复核（~0.1%）│   ← 这一层的产出是最贵也最有价值的资产
   └───────────────────────┘
"""),
        TABLE(["层级", "触发条件", "处理方式", "占比目标", "产出"], [
            ["<strong>L1 自动</strong>", "判分器给出明确结果且无异常", "直接采信", "&gt; 98%", "主指标"],
            ["<strong>L2 分诊</strong>", "超时、容器异常、validator 抛错、终态部分匹配", "重跑一次（换干净容器、放宽超时）；仍异常则升级", "1%–2%", "区分「基础设施抖动」与「真实失败」"],
            ["<strong>L3 人工</strong>", "L2 之后仍无法判定，或抽样质检", "人工判定，结果<strong>回灌金标准集</strong>", "&lt; 0.5%", "新的 α/β 估计样本 + 判分器改进线索"],
        ]),
        CALLOUT("warn", "L2 这一层有一个容易被忽略但非常重要的纪律：<strong>重跑必须被记录，而且重跑次数要进报告</strong>。"
                        "如果你对失败的样本重跑、对成功的样本不重跑，就引入了一个只朝一个方向的选择偏倚——"
                        "<em>「重跑到成功为止」是评测里最隐蔽的一种作弊，而且很多时候是无意的</em>。"
                        "正确规则：<strong>重跑触发条件必须与结果无关</strong>（只看是否发生了基础设施异常），"
                        "并且对成功与失败样本一视同仁。"),
        DUAL(
            "为什么值得为 0.5% 的样本专门设计一层？因为这 0.5% 里藏着判分器的全部改进线索。"
            "L3 每处理一条，你就多一条<strong>带人类标签的金标准样本</strong>——"
            "而第 5 节说过，几十条这样的样本就能把 α/β 定位到 ±0.1 以内。"
            "<strong>换句话说，人工复核不是成本，是在持续给你的测量仪器做校准。</strong>",
            "从系统设计的角度，这是一条<span class=\"term\">主动学习</span>（active learning）回路："
            "L2/L3 天然筛出的是判分器<em>最不确定</em>的样本，"
            "而这些样本对改进判分器的信息量最大（呼应 C10 的标注预算分配）。"
            "<em>因此这条流水线的正确指标不是「人工复核量越少越好」，"
            "而是「单位人工投入带来的 α/β 收窄幅度最大」</em>——"
            "把它压到零反而会让判分器停止进化。",
        ),
    ])),
]

NB = [
    md("""# 02 · 结果判分与部分得分（变异测试 / 判分器混淆矩阵 / 排序翻转 / hack 检测 / 聚合）

目标：把「怎么判对错」从一句话，变成一套**可以被自己测试**的工程。

本 notebook 你会亲手实现：
1. **变异测试** —— 用故意注入的 bug 量化「这组测试有多强」
2. **判分器混淆矩阵与 Rogan–Gladen 校正** —— 量出 α/β，把观测成功率还原成真实成功率
3. **部分得分的排序翻转实验** —— 构造出「二值判分 A 赢、checkpoint 判分 B 赢」，并量化它多常发生
4. **checkpoint 的单调性检查器** —— 三条硬规则的可执行版本
5. **判分器 hack 检测器** —— 六种 hack 的自动化闸门
6. **micro vs macro 聚合** —— 同一批结果，两种聚合，两个排序

> 心智模型：**判分器是这套测量系统的零点。零点偏了，多测一万次只会让你更自信地相信一个错的数字。**"""),

    md("""## 1 · 变异测试：这组测试有多强

给一个「被测函数」注入若干微小语义改动（变异体），看测试组能杀掉几个。
杀不掉的就是测试的盲区，也就是判分器的假阳性来源。"""),

    code("""import math, itertools, json
from collections import Counter, defaultdict
import numpy as np

# 被测函数的「正确实现」
def divide(a, b):
    if b == 0:
        return None
    return a / b

# 一组弱测试：只检查了 b == 0 这一条路径
WEAK_TESTS = [lambda f: f(10, 0) is None]

# 一组强测试：正常路径 + 边界 + 符号
STRONG_TESTS = [
    lambda f: f(10, 0) is None,
    lambda f: f(10, 2) == 5,
    lambda f: f(-9, 3) == -3,
    lambda f: f(7, 2) == 3.5,
]

# 变异体：每个都是一个「故意有 bug 的实现」
MUTANTS = {
    'return_const_none': lambda a, b: None,
    'drop_zero_guard':   lambda a, b: (a / b) if b != 0 else 0,
    'flip_sign':         lambda a, b: None if b == 0 else -a / b,
    'int_division':      lambda a, b: None if b == 0 else a // b,
    'swap_args':         lambda a, b: None if a == 0 else b / a,
}

def mutation_score(tests, mutants):
    \"\"\"变异分数 = 被杀死的变异体 / 变异体总数。测试跑挂或断言失败即算「杀死」。\"\"\"
    killed = []
    for name, m in mutants.items():
        alive = True
        for t in tests:
            try:
                if not t(m):
                    alive = False
                    break
            except Exception:
                alive = False
                break
        if not alive:
            killed.append(name)
    return len(killed) / len(mutants), killed

ws, wk = mutation_score(WEAK_TESTS, MUTANTS)
ss, sk = mutation_score(STRONG_TESTS, MUTANTS)
print(f'弱测试变异分数: {ws:.0%}  杀死: {wk}')
print(f'强测试变异分数: {ss:.0%}  杀死: {sk}')
assert ws < 0.5 and ss == 1.0
print('\\n✅ 弱测试连「全部返回 None」这种彻底错误的实现都杀不掉——')
print('   用它当判分器，等于把大量语义错误的解判成成功（假阳性）。')"""),

    code("""# 变异分数 → 该任务该不该进主指标
def scorer_tier(mut_score):
    if mut_score > 0.9:
        return 'strong'      # 可直接用作判分器
    if mut_score >= 0.6:
        return 'medium'      # 可用，但报告里注明
    return 'weak'            # 不应进入主指标

rng = np.random.default_rng(9)
task_mut = np.clip(rng.beta(5, 2, size=200), 0, 1)      # 模拟 200 个任务的测试强度分布
tiers = Counter(scorer_tier(m) for m in task_mut)
for t in ['strong', 'medium', 'weak']:
    print(f'  {t:<8} {tiers[t]:>3} 个任务 ({tiers[t]/200:.0%})')

weak_frac = tiers['weak'] / 200
print(f'\\n弱判分任务占比 {weak_frac:.0%}——这部分任务的分数是不可信的。')
assert tiers['strong'] + tiers['medium'] + tiers['weak'] == 200
print('✅ 把变异分数存成任务元数据，你就能随时做「只用强判分任务重算一遍」的敏感性分析。')"""),

    md("""## 2 · 判分器混淆矩阵与 Rogan–Gladen 校正

用金标准集（已知正确解 + 已知错误解）量出判分器的 α（假阳率）与 β（假阴率），
再把观测成功率还原成真实成功率。"""),

    code("""def confusion(gold_labels, scorer_labels):
    \"\"\"gold: 真实是否正确; scorer: 判分器判定是否正确。返回 (alpha, beta, 混淆计数)。\"\"\"
    gold = np.asarray(gold_labels, dtype=bool)
    pred = np.asarray(scorer_labels, dtype=bool)
    tp = int((gold & pred).sum())
    fn = int((gold & ~pred).sum())
    fp = int((~gold & pred).sum())
    tn = int((~gold & ~pred).sum())
    alpha = fp / (fp + tn) if (fp + tn) else 0.0     # 假阳率：错的被判成对
    beta = fn / (tp + fn) if (tp + fn) else 0.0      # 假阴率：对的被判成错
    return alpha, beta, {'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn}

rng = np.random.default_rng(21)
N_GOLD = 60
gold = np.array([True] * N_GOLD + [False] * N_GOLD)
TRUE_ALPHA, TRUE_BETA = 0.12, 0.05                  # 判分器的真实缺陷（弱测试 → 高假阳）
pred = np.where(gold, rng.random(2 * N_GOLD) > TRUE_BETA, rng.random(2 * N_GOLD) < TRUE_ALPHA)

alpha, beta, cm = confusion(gold, pred)
print('混淆矩阵:', cm)
print(f'估计 α(假阳率) = {alpha:.3f} | 估计 β(假阴率) = {beta:.3f}')
assert abs(alpha - TRUE_ALPHA) < 0.10 and abs(beta - TRUE_BETA) < 0.10
print('\\n✅ 120 条金标准样本就能把 α/β 定位到 ±0.1 以内——这是半天的工作量。')"""),

    code("""def rogan_gladen(p_obs, alpha, beta):
    \"\"\"用判分器的 α/β 把观测成功率还原成真实成功率。可能超出 [0,1]——那是信号，不是 bug。\"\"\"
    denom = 1 - beta - alpha
    if abs(denom) < 1e-9:
        return float('nan')
    return (p_obs - alpha) / denom

print(f"{'真实成功率':>10}{'观测成功率':>12}{'相对虚高':>10}{'校正回来':>10}")
for p_true in [0.05, 0.15, 0.30, 0.50, 0.80]:
    p_obs = p_true * (1 - TRUE_BETA) + (1 - p_true) * TRUE_ALPHA
    back = rogan_gladen(p_obs, TRUE_ALPHA, TRUE_BETA)
    print(f'{p_true:>10.0%}{p_obs:>12.1%}{p_obs/p_true:>9.2f}x{back:>10.1%}')
    assert abs(back - p_true) < 1e-9

print('\\n注意最上面一行：真实 5% 的能力，被一个 α=12% 的判分器测成 16.4%——虚高 3.3 倍。')
print('✅ 「越难的基准上，低分越不可信」的定量版本。难基准 + 弱判分器 = 数字几乎全是假阳性。')

# 边界情形：观测值低于 α 时，校正结果为负
edge = rogan_gladen(0.08, 0.12, 0.05)
print(f'\\n观测 8% 而 α=12% → 校正后 {edge:.1%}（负值）')
assert edge < 0
print('→ 正确解读是「观测到的成功可以完全由假阳性解释，无法区分于零」，而不是截断成 0 当没事发生。')"""),

    code("""def bootstrap_ci(scores, n_boot=2000, seed=0, alpha_level=0.05):
    \"\"\"成功率的自举置信区间。\"\"\"
    rng = np.random.default_rng(seed)
    s = np.asarray(scores, dtype=float)
    boots = [s[rng.integers(0, len(s), len(s))].mean() for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [100 * alpha_level / 2, 100 * (1 - alpha_level / 2)])
    return float(s.mean()), float(lo), float(hi)

rng = np.random.default_rng(33)
obs_scores = (rng.random(300) < 0.336).astype(float)      # 观测成功率约 33.6%
m, lo, hi = bootstrap_ci(obs_scores, seed=1)
m_c = rogan_gladen(m, TRUE_ALPHA, TRUE_BETA)
lo_c, hi_c = rogan_gladen(lo, TRUE_ALPHA, TRUE_BETA), rogan_gladen(hi, TRUE_ALPHA, TRUE_BETA)
print(f'校正前: {m:.1%}  [{lo:.1%}, {hi:.1%}]  宽度 {hi-lo:.1%}')
print(f'校正后: {m_c:.1%}  [{lo_c:.1%}, {hi_c:.1%}]  宽度 {hi_c-lo_c:.1%}')
assert (hi_c - lo_c) > (hi - lo)
print('\\n✅ 校正让区间变宽了——这是诚实的代价：')
print('   原来的窄区间是「假装判分器完美」换来的，它精确但偏。')"""),

    md("""## 3 · 部分得分的排序翻转实验

构造两个 agent：A 常常「做到一半卡住」，B 常常「要么全对要么完全跑偏」。
二值判分与 checkpoint 判分会给出相反的排名。"""),

    code("""N_CP = 4        # 每个任务 4 个 checkpoint，第 4 个 == 二值成功

def simulate_agent(n_tasks, p_step, dropout_shape, rng):
    \"\"\"返回每个任务达成的 checkpoint 数（0..N_CP）。
    dropout_shape 控制「中途卡住」的倾向：'gradual' 逐步掉队，'allornothing' 要么全过要么早死。\"\"\"
    out = []
    for _ in range(n_tasks):
        if dropout_shape == 'gradual':
            k = 0
            for _ in range(N_CP):
                if rng.random() < p_step:
                    k += 1
                else:
                    break
            out.append(k)
        else:
            out.append(N_CP if rng.random() < p_step ** N_CP else 0)
    return np.array(out)

rng = np.random.default_rng(7)
A = simulate_agent(600, 0.72, 'gradual', rng)          # 稳步推进型
B = simulate_agent(600, 0.78, 'allornothing', rng)     # 孤注一掷型

binary_A, binary_B = (A == N_CP).mean(), (B == N_CP).mean()
cp_A, cp_B = A.mean() / N_CP, B.mean() / N_CP
print(f"{'':<6}{'二值成功率':>12}{'checkpoint 达成率':>20}")
print(f"{'A':<6}{binary_A:>12.1%}{cp_A:>20.1%}")
print(f"{'B':<6}{binary_B:>12.1%}{cp_B:>20.1%}")
winner_binary = 'A' if binary_A > binary_B else 'B'
winner_cp = 'A' if cp_A > cp_B else 'B'
print(f'\\n二值判分赢家: {winner_binary} | checkpoint 判分赢家: {winner_cp}')
assert winner_binary != winner_cp, '本例刻意构造成排序翻转'
print('✅ 排序翻转发生了。两个结论都不是错的——它们回答的是不同的问题：')
print('   二值问「能不能交付」，checkpoint 问「走得多远」。产品决策看前者，改进方向看后者。')"""),

    code("""def flip_rate(n_trials=300, seed=0):
    \"\"\"随机生成成对 agent，统计「二值排序与 checkpoint 排序不一致」的频率。\"\"\"
    rng = np.random.default_rng(seed)
    flips = 0
    for _ in range(n_trials):
        pa, pb = rng.uniform(0.5, 0.9), rng.uniform(0.5, 0.9)
        sa = simulate_agent(200, pa, 'gradual', rng)
        sb = simulate_agent(200, pb, 'allornothing', rng)
        ba, bb = (sa == N_CP).mean(), (sb == N_CP).mean()
        ca, cb = sa.mean(), sb.mean()
        if (ba > bb) != (ca > cb):
            flips += 1
    return flips / n_trials

rate = flip_rate(seed=4)
print(f'随机成对比较中，二值 vs checkpoint 排序不一致的比例: {rate:.1%}')
assert rate > 0.05, '在风格差异明显的 agent 之间，翻转绝非罕见'
print('✅ 这不是个别构造的反例——只要两个 agent 的「失败风格」不同，翻转就有可观概率发生。')
print('   报告规范：主指标二值 + 附表 checkpoint 分布，两者都给，不要二选一。')"""),

    md("""## 4 · checkpoint 的三条硬规则：可执行的检查器

单调 / 可自动判定 / 最后一个等价于二值成功。"""),

    code("""def check_monotone(traj_checkpoints):
    \"\"\"traj_checkpoints: 每条轨迹达成的 checkpoint 布尔向量（长度 N_CP）。
    单调性要求：达成第 k 个 → 必然达成前 k-1 个。返回违规轨迹的下标。\"\"\"
    bad = []
    for i, row in enumerate(traj_checkpoints):
        seen_false = False
        for v in row:
            if not v:
                seen_false = True
            elif seen_false:
                bad.append(i)
                break
    return bad

good = [[1, 1, 1, 0], [1, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]]
bad_set = [[1, 0, 1, 0], [0, 1, 1, 1]]
assert check_monotone(good) == []
assert check_monotone(bad_set) == [0, 1]
print('单调性检查：合规集合无违规，违规集合两条全部检出 ✓')

def check_last_equals_binary(traj_checkpoints, binary_scores):
    \"\"\"规则三：最后一个 checkpoint 必须与二值成功完全一致。\"\"\"
    last = np.array([row[-1] for row in traj_checkpoints], dtype=bool)
    return bool(np.array_equal(last, np.asarray(binary_scores, dtype=bool)))

assert check_last_equals_binary(good, [0, 0, 1, 0]) is True
assert check_last_equals_binary(good, [0, 0, 0, 0]) is False
print('规则三检查：最后一个 checkpoint 与二值成功一致性 ✓')
print('\\n✅ 三条规则都是可执行的断言——把它们写进任务集的 CI，坏 checkpoint 进不了主干。')"""),

    md("""## 5 · 判分器 hack 检测器

六种 hack 的自动化闸门。第一条（patch 触碰测试文件）必须无条件写死。"""),

    code("""TEST_PATH_PAT = ('test_', '_test.py', '/tests/', 'conftest.py', 'pytest.ini', 'tox.ini')

def touches_tests(patch_files):
    return [f for f in patch_files if any(p in f for p in TEST_PATH_PAT)]

def hack_gate(patch_files, tests_collected_before, tests_collected_after,
              env_mutations, heldout_pass):
    \"\"\"返回 (是否判 0, 触发的闸门列表)。任一闸门触发即判 0。\"\"\"
    gates = []
    if touches_tests(patch_files):
        gates.append('patch_touches_tests')
    if tests_collected_after < tests_collected_before:
        gates.append('tests_disappeared')
    if env_mutations:
        gates.append('env_tampering')
    if heldout_pass is False:
        gates.append('heldout_tests_failed')
    return (len(gates) > 0, gates)

CASES = [
    (['src/utils.py'], 42, 42, [], True,  '正常的修复'),
    (['tests/test_utils.py'], 42, 42, [], True,  '改了测试文件'),
    (['src/utils.py', 'conftest.py'], 42, 40, [], True,  '跳过了两个用例'),
    (['src/utils.py'], 42, 42, ['PYTHONPATH'], True,  '改了环境变量'),
    (['src/utils.py'], 42, 42, [], False, '过了公开测试但过不了留出测试（特判输入）'),
]
for args in CASES:
    flag, gates = hack_gate(*args[:-1])
    print(f'{args[-1]:<34} 判0={flag}  闸门={gates}')

assert hack_gate(['src/a.py'], 10, 10, [], True) == (False, [])
assert hack_gate(['tests/test_a.py'], 10, 10, [], True)[0] is True
assert 'tests_disappeared' in hack_gate(['src/a.py'], 10, 8, [], True)[1]
print('\\n✅ 五种 hack 全部被拦。注意最后一条：')
print('   「留出测试」是唯一能抓「特判输入」的手段——判分测试之外必须再留一组不公开的测试。')"""),

    md("""## 6 · micro vs macro 聚合：同一批结果，两个排序"""),

    code("""# 三个子集（仓库），任务数极不均衡
SUBSETS = {'repo_big': 800, 'repo_mid': 120, 'repo_small': 80}
rng = np.random.default_rng(13)

def make_results(per_subset_rate, rng):
    rows = []
    for sub, n in SUBSETS.items():
        r = per_subset_rate[sub]
        for _ in range(n):
            rows.append({'subset': sub, 'score': float(rng.random() < r)})
    return rows

# A 在大子集上略强，B 在两个小子集上明显强
A_rows = make_results({'repo_big': 0.65, 'repo_mid': 0.30, 'repo_small': 0.25}, rng)
B_rows = make_results({'repo_big': 0.40, 'repo_mid': 0.75, 'repo_small': 0.85}, rng)

def micro(rows):
    return float(np.mean([r['score'] for r in rows]))

def macro(rows):
    by = defaultdict(list)
    for r in rows:
        by[r['subset']].append(r['score'])
    return float(np.mean([np.mean(v) for v in by.values()]))

print(f"{'':<4}{'micro':>10}{'macro':>10}")
print(f"{'A':<4}{micro(A_rows):>10.1%}{macro(A_rows):>10.1%}")
print(f"{'B':<4}{micro(B_rows):>10.1%}{macro(B_rows):>10.1%}")
assert (micro(A_rows) > micro(B_rows)) != (macro(A_rows) > macro(B_rows))
print('\\n✅ micro 与 macro 给出相反的排序。这不是需要「选一个对的」的问题——')
print('   而是必须在报告里显式写出来的发现：谁更强，取决于你关心哪个子集。')

by_sub = defaultdict(dict)
for name, rows in [('A', A_rows), ('B', B_rows)]:
    for sub in SUBSETS:
        vals = [r['score'] for r in rows if r['subset'] == sub]
        by_sub[sub][name] = np.mean(vals)
print('\\n按子集分解（这张表才是报告里真正有信息量的部分）:')
for sub, d in by_sub.items():
    print(f"  {sub:<12} n={SUBSETS[sub]:<4} A={d['A']:.0%}  B={d['B']:.0%}")"""),

    md("""## ✏️ 练习 1：给定 α/β 反推「至少要多真才能被看见」

实现 `min_detectable_true_rate(alpha, beta, obs_threshold)`：
给定判分器的 α/β 和一个观测成功率阈值 `obs_threshold`，
求真实成功率至少要多少，观测值才能达到该阈值。即由
$\\hat{p}_{obs} = p(1-\\beta) + (1-p)\\alpha$ 反解 $p$，并把结果夹到 $[0, 1]$。"""),

    code("""def min_detectable_true_rate(alpha, beta, obs_threshold):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(min_detectable_true_rate(0.0, 0.0, 0.30) - 0.30) < 1e-12
p = min_detectable_true_rate(0.12, 0.05, 0.30)
assert abs(0.12 + p * (1 - 0.05 - 0.12) - 0.30) < 1e-9
assert min_detectable_true_rate(0.40, 0.05, 0.30) == 0.0     # 观测阈值低于 α，夹到 0
assert min_detectable_true_rate(0.0, 0.5, 0.90) == 1.0       # 需要的真实率超过 1，夹到 1
print(f'α=12%,β=5% 时，要让观测值达到 30%，真实成功率只需 {p:.1%}')
print('✅ 练习 1 通过：判分器的假阳性会「送分」——观测阈值必须按 α 上移，否则门禁形同虚设。')"""),

    md("""## ✏️ 练习 2：加权 checkpoint 得分与权重敏感性

实现 `weighted_checkpoint(cp_matrix, weights)`：`cp_matrix` 每行是一条轨迹的
checkpoint 布尔向量，返回加权平均得分（权重归一化）。
再实现 `weight_sensitivity(cp_A, cp_B, weights, delta=0.2, seed=0, n=200)`：
对权重做 ±delta 的随机扰动 n 次，返回「A 胜出的比例」。"""),

    code("""def weighted_checkpoint(cp_matrix, weights):
    # TODO
    raise NotImplementedError

def weight_sensitivity(cp_A, cp_B, weights, delta=0.2, seed=0, n=200):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
cpA = np.array([[1, 1, 0, 0], [1, 1, 1, 0], [1, 0, 0, 0]])
cpB = np.array([[1, 1, 1, 1], [1, 0, 0, 0], [0, 0, 0, 0]])
w = np.array([1.0, 1.0, 1.0, 1.0])
assert abs(weighted_checkpoint(cpA, w) - cpA.mean()) < 1e-12
w2 = np.array([4.0, 1.0, 1.0, 1.0])
assert weighted_checkpoint(cpA, w2) > weighted_checkpoint(cpA, w)   # 前置 checkpoint 加权 → A 得分上升

frac = weight_sensitivity(cpA, cpB, w, delta=0.2, seed=1, n=300)
print(f'等权时 A={weighted_checkpoint(cpA, w):.3f} B={weighted_checkpoint(cpB, w):.3f}')
print(f'权重扰动 ±20% 后，A 胜出的比例: {frac:.1%}')
assert 0.0 <= frac <= 1.0
print('✅ 练习 2 通过：胜负比例接近 50% 说明结论完全由权重决定，不该写成「A 更强」。')"""),

    md("""## ✏️ 练习 3：hack 闸门的假阳性代价

实现 `gate_cost(n_total, n_hacks, gate_recall, gate_fpr)`：
返回 `(拦住的 hack 数, 误伤的正常解数, 净收益)`，净收益 =
拦住的 hack 数 × 10 − 误伤数 × 1（拦住一个 hack 的价值是误伤一个正常解的 10 倍）。
`n_total` 含 `n_hacks` 个作弊解。"""),

    code("""def gate_cost(n_total, n_hacks, gate_recall, gate_fpr):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
caught, hurt, net = gate_cost(1000, 50, gate_recall=1.0, gate_fpr=0.0)
assert (caught, hurt) == (50.0, 0.0) and net == 500.0
c2, h2, n2 = gate_cost(1000, 50, gate_recall=0.9, gate_fpr=0.02)
assert abs(c2 - 45.0) < 1e-9 and abs(h2 - 19.0) < 1e-9
print(f'完美闸门（patch 触碰测试文件）: 拦住 {caught:.0f} 误伤 {hurt:.0f} 净收益 {net:.0f}')
print(f'启发式闸门（recall 90%, fpr 2%）: 拦住 {c2:.0f} 误伤 {h2:.0f} 净收益 {n2:.0f}')
assert net > n2
print('✅ 练习 3 通过：零假阳性的硬规则永远优先于高召回的启发式——')
print('   这就是「patch 触碰测试文件即判 0」必须写死、而其余闸门要谨慎调阈值的原因。')"""),

    md("""## ✏️ 练习 4：按判分强度加权的稳健成功率

实现 `robust_success_rate(scores, mut_scores, min_tier=0.6)`：
只统计变异分数 ≥ `min_tier` 的任务的成功率，并返回
`(稳健成功率, 被剔除的任务比例, 与朴素成功率之差)`。"""),

    code("""def robust_success_rate(scores, mut_scores, min_tier=0.6):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
rng = np.random.default_rng(77)
n = 400
mut = np.clip(rng.beta(4, 3, size=n), 0, 1)
# 弱判分任务上成功率虚高（假阳性多）
p = np.where(mut < 0.6, 0.65, 0.35)
sc = (rng.random(n) < p).astype(float)

rob, dropped, diff = robust_success_rate(sc, mut, min_tier=0.6)
naive = sc.mean()
print(f'朴素成功率 {naive:.1%} | 稳健成功率 {rob:.1%} | 剔除 {dropped:.0%} 的任务 | 差 {diff:+.1%}')
assert rob < naive, '剔除弱判分任务后成功率应下降'
assert 0 < dropped < 1
assert abs(diff - (rob - naive)) < 1e-12
print('✅ 练习 4 通过：两个数字之差就是「弱判分任务贡献的虚高」——')
print('   这一行数字放进报告，比任何关于判分器质量的定性描述都有说服力。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def min_detectable_true_rate(alpha, beta, obs_threshold):
    denom = 1 - beta - alpha
    if abs(denom) < 1e-12:
        return float('nan')
    p = (obs_threshold - alpha) / denom
    return float(min(1.0, max(0.0, p)))"""),

    code("""# 练习 2 参考答案
def weighted_checkpoint(cp_matrix, weights):
    m = np.asarray(cp_matrix, dtype=float)
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    return float((m * w).sum(axis=1).mean())

def weight_sensitivity(cp_A, cp_B, weights, delta=0.2, seed=0, n=200):
    rng = np.random.default_rng(seed)
    w = np.asarray(weights, dtype=float)
    wins = 0
    for _ in range(n):
        pert = w * (1 + rng.uniform(-delta, delta, size=w.shape))
        pert = np.clip(pert, 1e-9, None)
        if weighted_checkpoint(cp_A, pert) > weighted_checkpoint(cp_B, pert):
            wins += 1
    return wins / n"""),

    code("""# 练习 3 参考答案
def gate_cost(n_total, n_hacks, gate_recall, gate_fpr):
    caught = n_hacks * gate_recall
    hurt = (n_total - n_hacks) * gate_fpr
    return (caught, hurt, caught * 10 - hurt * 1)"""),

    code("""# 练习 4 参考答案
def robust_success_rate(scores, mut_scores, min_tier=0.6):
    s = np.asarray(scores, dtype=float)
    m = np.asarray(mut_scores, dtype=float)
    keep = m >= min_tier
    if keep.sum() == 0:
        return (float('nan'), 1.0, float('nan'))
    rob = float(s[keep].mean())
    dropped = float(1 - keep.mean())
    return (rob, dropped, rob - float(s.mean()))"""),

    md("""---
## 🧪 真实工程胶囊：判分器工程的可复制骨架"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 代码类任务的判分流水线（顺序不可调换）
# ══════════════════════════════════════════════════════════════════
def score_patch(patch, task, workdir):
    # 闸门 1（硬规则，零假阳性，永远第一个跑）：patch 不许碰测试文件
    if any(p in f for f in changed_files(patch) for p in TEST_PATH_PAT):
        return {"score": 0, "reason": "patch_touches_tests"}

    # 闸门 2：在**干净的新容器**里应用 patch，不复用 agent 的运行时环境
    ctr = start_container(task["image_digest"])       # digest，不是 tag
    apply_patch(ctr, patch)

    # 闸门 3：测试收集数量不许变少（防 skip / 防改 conftest）
    n_after = collect_count(ctr, task["test_paths"])
    if n_after < task["n_tests_expected"]:
        return {"score": 0, "reason": "tests_disappeared"}

    # 主判分：F2P 必须全绿，P2P 必须保持绿
    f2p = run_tests(ctr, task["FAIL_TO_PASS"])
    p2p = run_tests(ctr, task["PASS_TO_PASS"])
    ok = f2p.all_pass and p2p.all_pass

    # 闸门 4（可选但强烈推荐）：留出测试，抓「特判输入」
    heldout = run_tests(ctr, task.get("HELDOUT_TESTS", []))
    return {"score": int(ok and heldout.all_pass),
            "f2p": f2p.summary, "p2p": p2p.summary, "heldout": heldout.summary}

# ══════════════════════════════════════════════════════════════════
# B. 判分器体检（每次任务集变更后跑一次，半天工作量）
# ══════════════════════════════════════════════════════════════════
# 1. 取 30-50 条 gold patch  → 判分器判 0 的就是假阴 → 估计 β
# 2. 取 30-50 条「破坏过的 gold patch」→ 判分器判 1 的就是假阳 → 估计 α
#    破坏方式：改一个比较运算符 / 改一个常量 / 删掉一个分支
# 3. 取 10-20 条语义等价重写 → 判分器判 0 说明它对形式差异过敏
# 4. 把 (α, β) 写进评测报告，并对主指标给出 Rogan-Gladen 校正值

# ══════════════════════════════════════════════════════════════════
# C. 变异测试（任务集构建期跑一次，结果存成任务元数据）
# ══════════════════════════════════════════════════════════════════
# pip install mutmut       # 或 cosmic-ray
# mutmut run --paths-to-mutate src/ --tests-dir tests/
# mutmut results           # 存活的变异体 = 判分盲区
# 把 mutation_score 写进 task meta，之后可做「只用 strong 任务重算」的敏感性分析。

# ══════════════════════════════════════════════════════════════════
# D. 报告模板（照抄这四行，你的报告就超过大多数公开报告）
# ══════════════════════════════════════════════════════════════════
# resolve_rate (micro):        34.2%  [31.0%, 37.5%]   n=500
# resolve_rate (macro by repo):29.8%                   12 repos
# scorer alpha / beta:         0.041 / 0.018           gold set n=120
# corrected resolve_rate:      31.5%  [27.9%, 35.2%]
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 判分器偏差不随样本量消失 | bias 是 0.10 时，把 var 再压一半毫无意义 | 先量 α/β 再扩规模 |
| 变异测试 | 测试强度决定判分强度；弱判分任务不该进主指标 | 任务集构建期 |
| 不变量优于快照 | 终态匹配升级成属性断言，天然处理等价解 | 终态类任务 |
| 部分得分会翻转排序 | 二值问「能不能交付」，checkpoint 问「走得多远」 | 主表二值 + 附表 checkpoint |
| 六种 hack | patch 触碰测试文件必须无条件判 0 | 判分流水线第一行 |
| micro vs macro | 两者排序不一致时，这件事本身就是最重要的发现 | 报告规范 |

下一模块：**03 · 轨迹级评测**——两个成功率相同的 agent，钱花在哪、卡在哪、能不能从错误里爬出来。""")
]
