# -*- coding: utf-8 -*-
"""C68 模块 03 · 结果存储与分析。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 02（runner 与失败分类）；"
                 "会写基本的 SQL SELECT / GROUP BY，或者能读懂等价的 Python 聚合"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_result_store.ipynb'
                       '（宽表 schema 与只追加写入 / 切片查询与 Simpson 悖论复现 / '
                       '聚合逻辑与结果分离：同一批结果算出四个不同的数 / '
                       '两次运行的结构化 diff 与逐题变化矩阵 / 存储规模与保留策略 / '
                       '结果的完整性校验）'),
    ("核心参考", "Kimball 的事实表/维度表建模思想（本课只借「宽事实表 + 后置聚合」这一条）· "
                 "Simpson (1951) 与分层悖论的经典讨论 · "
                 "inspect_ai 的 <code>.eval</code> 日志格式（每条 sample 一条记录 + 全局配置快照）· "
                 "本课程 C66 模块 02（micro/macro 聚合）· C66 模块 03（轨迹 schema）· C43（数据建模）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("one-row", "一条 rollout 一行：宽事实表与后置聚合", "".join([
        P("结果层的核心设计只有一句话：<strong>存最细粒度的事实，把聚合留到查询时做。</strong>"
          "听起来平淡，但它决定了这套系统能不能回答半年后才被问出来的问题。"),
        ASCII("""
   ❌ 存聚合结果                          ✓ 存最细粒度事实
   ┌──────────────────────────┐          ┌────────────────────────────────┐
   │ run_id | score | n       │          │ run_id | task_id | attempt |…  │
   │ r-001  | 0.412 | 512     │          │ r-001  | t001    | 0       |…  │
   │ r-002  | 0.447 | 498     │          │ r-001  | t001    | 1       |…  │
   └──────────────────────────┘          │ r-001  | t002    | 0       |…  │
                                          └────────────────────────────────┘
   能回答: "总分是多少"                    能回答: 总分 / macro / 按难度切片 /
   不能回答: 按难度切片？pass^k？          pass^k / 与上次逐题 diff / 只用强判分
             哪些题变了？只用强判分任务？   任务重算 / 任何**当时没想到**的问题
                                          ——**而且不用重跑**
"""),
        DUAL(
            "为什么这条如此重要？因为<strong>你现在想不到的问题，半年后一定会被问到</strong>。"
            "「这个提升在难题上也成立吗」「是不是只在某个子系统上涨的」"
            "「如果只算判分器强的那些任务呢」——"
            "<em>这些问题在存了明细的系统里是一句查询，在只存了聚合的系统里是一次重跑</em>（几百美元 + 几小时）。",
            "从数据建模的角度，这是<span class=\"term\">事实表</span>的标准形态："
            "每行是一个不可再分的观测事件（一次 rollout 的结果），"
            "所有能想到的维度（任务属性、配置、时间）都作为列或外键存在。"
            "<strong>聚合是这张表上的视图，而不是表本身。</strong>"
            "<em>存储成本换来的是分析的自由度</em>——"
            "而评测结果的存储量通常很小（几十万行、几百 MB），这个交换几乎总是划算的。",
        ),
        H3("最小 schema：11 个字段"),
        CODE("""-- 主键三元组（模块 00）
run_id        TEXT     -- 一次运行
task_id       TEXT     -- 稳定样本 ID（模块 01）
attempt       INTEGER  -- 第几次重复（pass^k 需要）

-- 可归因性
fingerprint   TEXT     -- 执行配置指纹（模块 01/02）
dataset_ver   TEXT     -- 任务集版本（跨版本比较需要）
scorer_ver    TEXT     -- 判分器版本

-- 结果
status        TEXT     -- ok | timeout | refusal | parse_error | scorer_error
score         REAL     -- NULL when status != 'ok'
output        TEXT     -- 原始输出（失败样本尤其要留，否则永远查不出原因）

-- 成本与诊断
cost_usd      REAL
latency_ms    INTEGER

PRIMARY KEY (run_id, task_id, attempt)"""),
        CALLOUT("warn", "<code>output</code> 这一列经常被以「太占空间」为由砍掉。"
                        "<strong>不要砍——至少对失败样本不要砍。</strong>"
                        "<em>「为什么这道题失败了」这个问题，没有原始输出就只能重跑；"
                        "而重跑时的随机性可能让那次失败不再复现</em>。"
                        "如果确实需要省空间，正确做法是<strong>对成功样本做压缩或抽样保留，"
                        "对失败样本全量保留</strong>——因为你要看的永远是失败的那些。"),
    ])),

    # ============================================================== 2
    ("separate-agg", "聚合逻辑必须与结果分离", "".join([
        P("上一节说「聚合留到查询时做」。这一节说清楚为什么这不只是灵活性问题，"
          "更是<strong>正确性</strong>问题。"),
        P("同一批结果，可以算出好几个都「对」但含义不同的数字（C66 模块 02 已经展示过 micro/macro）。"
          "如果聚合逻辑被写死在 runner 里，那么<strong>换一个口径就要重跑</strong>——"
          "而重跑的成本会让人倾向于「就用现在这个数」，即使它不是回答当前问题的正确口径。"),
        TABLE(["口径", "定义", "回答什么问题", "什么时候是错的"], [
            ["<strong>micro</strong>", "所有 rollout 一视同仁求平均", "「在这个任务分布上表现如何」", "任务数不均衡时，大子集主导总分"],
            ["<strong>macro（按任务）</strong>", "先按 task_id 求平均，再对任务求平均", "「典型任务上表现如何」", "各任务重复次数不同时，等权可能不是你要的"],
            ["<strong>macro（按子集）</strong>", "先按子系统/难度求平均，再等权", "「各类任务都还行吗」", "小子集的噪声被放大到与大子集同权"],
            ["<strong>pass^k</strong>", "每个任务 k 次全对的比例", "「可靠性如何」（C66-04）", "结果有人复核时（那时该看 pass@k）"],
            ["<strong>加权</strong>", "按线上流量占比加权", "「对用户的实际影响」", "权重来源没写进报告时"],
        ]),
        CALLOUT("intuition", "一条实践规范：<strong>把聚合写成一组独立的、可组合的函数，"
                             "并让报告同时输出至少两个口径。</strong>"
                             "<em>如果 micro 与 macro 给出相反的排序，这件事本身就是报告里最重要的发现</em>"
                             "（C66 模块 02 第 7 节已经说过一次，这里是它的工程落实）。"
                             "<strong>而这一切的前提，是明细还在。</strong>"),
        H3("聚合函数的三条约束"),
        OL([
            "<strong>纯函数</strong>：输入是明细行，输出是数字。不读文件、不发请求、不依赖全局状态。"
            "<em>这样它可以被单元测试，而聚合逻辑的 bug 是最难被发现的一类</em>；",
            "<strong>显式声明分母</strong>：每个聚合函数都要能报出它用了多少行、排除了多少行、"
            "为什么排除。<em>「分数 0.412」和「分数 0.412（n=498，排除 14 条判分器崩溃）」"
            "是两个可信度完全不同的陈述</em>；",
            "<strong>对空输入有定义</strong>：分母为 0 时返回 <code>nan</code> 而不是 0——"
            "<em>返回 0 会让「没有数据」和「全错」在下游变得无法区分</em>。",
        ]),
    ])),

    # ============================================================== 3
    ("slicing", "切片分析：Simpson 悖论会在评测里真实发生", "".join([
        P("有了明细，切片就是一句 <code>GROUP BY</code>。但切片会暴露一个"
          "<strong>在评测里真实发生、且经常被误读</strong>的现象。"),
        ASCII("""
                       模型 A        模型 B
   easy  (400 题)      95% (380)     98% (98)      ← B 每一片都更好
   hard  (100 题)      40% (40)      45% (45)      ←
   ──────────────────────────────────────────
   总计                84%           58%           ← 但 A 的总分更高

   原因: 两个模型跑的**任务构成比例不同**
         A: 400 easy + 100 hard    B: 100 easy + 100 hard
   这不是矛盾，是 Simpson 悖论——总分被"跑了哪些题"这个混杂变量污染了。
"""),
        DUAL(
            "在评测里这个现象最常见的成因不是有人故意，而是<strong>两次运行的任务集不完全相同</strong>："
            "有些任务超时被排除了、有些是新加的、有些在一次运行里失败被跳过了。"
            "<em>只要两边的任务构成不同，总分就不可直接比较</em>——"
            "这和模块 01 的「跨版本比较要做交集重算」是同一件事，只是这里发生在同一个数据集版本内部。",
            "形式化地说，总分是各层分数按各层<strong>样本占比</strong>加权的结果："
            "$\\bar{s} = \\sum_g w_g \\bar{s}_g$，其中 $w_g = n_g / n$。"
            "<strong>当两次运行的 $\\{w_g\\}$ 不同时，"
            "$\\bar{s}_A - \\bar{s}_B$ 里混着「各层分数差」与「权重差」两部分</strong>，"
            "而后者与模型能力无关。"
            "<em>解法是标准化权重：用同一套 $\\{w_g\\}$（通常取两边的交集或目标分布）重算两边</em>——"
            "这在流行病学里叫<span class=\"term\">直接标准化</span>，在评测里就是「按共同任务集重算」。",
        ),
        CALLOUT("danger", "所以报告里有一条硬规范：<strong>比较两次运行时，必须先检查它们的任务集是否一致；"
                          "不一致就在交集上重算。</strong>"
                          "<em>这条检查应当是自动的</em>——"
                          "notebook 第 3 节会把它写成一个函数，"
                          "而模块 04 会把它变成 CI 里的一行断言。"),
        H3("哪些切片维度值得预留"),
        UL([
            "<strong>任务属性</strong>：难度、子系统、来源、创建时间（污染检验用）、判分器强度（C66-02）；",
            "<strong>执行属性</strong>：attempt 序号（看首次 vs 重试）、并发度、是否命中缓存；",
            "<strong>结果属性</strong>：失败类型（模块 02 的五分类）、延迟分桶、成本分桶；",
            "<strong>时间</strong>：run 的时间戳——<em>用来画趋势图，也用来定位「什么时候开始变的」</em>。",
        ]),
        P("<strong>这些维度不需要在存储时预聚合，只需要保证它们能被 join 到</strong>——"
          "任务属性来自数据集（模块 01 的 tags），执行属性来自 spec，结果属性来自明细行本身。"),
    ])),

    # ============================================================== 4
    ("run-diff", "两次运行的 diff：从「分数变了」到「哪些题变了」", "".join([
        P("「分数从 41.2% 涨到 44.7%」——这句话几乎不包含可行动的信息。"
          "<strong>有信息的是：哪些题从错变对了，哪些题从对变错了。</strong>"),
        MATH(r"\Delta = \underbrace{|\{i: s_i^{A}=0,\ s_i^{B}=1\}|}_{\text{fixed}} - \underbrace{|\{i: s_i^{A}=1,\ s_i^{B}=0\}|}_{\text{regressed}}"),
        TABLE(["量", "含义", "为什么比总分有用"], [
            ["<strong>fixed</strong>", "从错变对的题数", "直接对应「这个改动修好了什么」"],
            ["<strong>regressed</strong>", "<strong>从对变错的题数</strong>", "<strong>最重要的一个</strong>——净提升为正也可能伴随大量退化"],
            ["<strong>churn</strong>", "$\\text{fixed} + \\text{regressed}$", "衡量「改动有多大」；churn 高而净变化小 = 只是噪声在翻转"],
            ["<strong>net</strong>", "$\\text{fixed} - \\text{regressed}$", "这才是总分变化的来源"],
        ]),
        CALLOUT("intuition", "<strong>churn 是一个被严重低估的量。</strong>"
                             "如果 fixed=30、regressed=25，净提升只有 5 题，"
                             "但有 55 道题的结果翻转了——<em>这说明模型的行为在这些题上本来就不稳定，"
                             "那 5 题的「提升」很可能只是这次采样的运气</em>。"
                             "<strong>正确的判读是：先看 churn 与净变化的比例。"
                             "churn 远大于净变化时，应该增加重复次数而不是宣布提升</strong>"
                             "（呼应 C66 模块 04 的方差分析）。"),
        H3("配对分析：这里可以直接用 McNemar"),
        P("逐题 diff 天然是一个配对设计（同一批任务、两个配置），"
          "所以 C66 模块 04 的 <strong>McNemar 检验</strong>可以原样用上："
          "只有 fixed 与 regressed 这两类不一致对携带信息，"
          "$\\chi^2 = (|f - r| - 1)^2 / (f + r)$。"
          "<em>这让「这次提升是不是显著」变成一个可以自动计算的判断</em>，"
          "而不需要人去感觉「3.5 个点好像挺多的」。"),
    ])),

    # ============================================================== 5
    ("integrity", "结果的完整性校验：五条应当自动跑的检查", "".join([
        P("存储层还有一个容易被忽略的职责：<strong>在把结果交给分析之前，先检查它自己是不是完整的。</strong>"
          "下面五条检查很便宜，但每一条都对应一类真实发生过的事故。"),
        TABLE(["检查", "断言", "不通过说明什么"], [
            ["<strong>指纹唯一</strong>", "一个 run 内 <code>fingerprint</code> 只有一个值", "<strong>run_id 被复用</strong>，新旧配置的结果混在一起（模块 02 第 7 节）"],
            ["<strong>覆盖完整</strong>", "行数 == 任务数 × attempts", "有任务被静默跳过了——通常是异常被吞了"],
            ["<strong>无重复</strong>", "主键三元组唯一", "幂等写入被绕过了"],
            ["<strong>状态合法</strong>", "<code>status</code> 只取枚举内的值；<code>status='ok'</code> ⟺ <code>score</code> 非空", "runner 里有分支忘了赋值"],
            ["<strong>数据集一致</strong>", "所有行的 <code>dataset_ver</code> 相同", "跑到一半数据集被换了"],
        ]),
        CALLOUT("warn", "第二条「覆盖完整」有一个容易被绕过的情况值得单说："
                        "<strong>如果 runner 在任务级别 catch 了所有异常并 <code>continue</code>，"
                        "那么失败的任务连一行都不会写入</strong>——"
                        "<em>行数少了，而分数看起来正常甚至更高</em>（因为最难的那些任务恰恰最容易抛异常）。"
                        "<strong>所以这条检查必须比对「预期行数」而不是「已有行数的内部一致性」</strong>，"
                        "而预期行数只能从 spec 里算出来（任务数 × attempts）。"),
        P("这五条应当作为<strong>加载函数的一部分</strong>，而不是一个「记得跑一下」的脚本——"
          "<em>放在加载函数里，它就不可能被忘记；放在脚本里，它半年后一定会被忘记。</em>"),
    ])),

    # ============================================================== 6
    ("retention", "存储规模与保留策略", "".join([
        P("最后一个工程问题：这些明细会不会撑爆存储。答案通常是<strong>不会</strong>，"
          "但值得算一笔账，因为这笔账会影响你要不要保留 <code>output</code> 列。"),
        MATH(r"\text{行数} = N_{\text{tasks}} \times k_{\text{attempts}} \times N_{\text{runs}}"),
        TABLE(["场景", "单次行数", "一年的运行次数", "总行数", "含 output 的体量"], [
            ["CI smoke", "60 × 1", "每天 20 次 × 250 天 = 5000", "30 万", "约 1–3 GB"],
            ["每日全量", "500 × 3", "365", "55 万", "约 5–15 GB"],
            ["模型选型", "500 × 5", "每月几十次", "约 100 万", "约 10–30 GB"],
            ["<strong>合计量级</strong>", "—", "—", "<strong>百万行</strong>", "<strong>几十 GB</strong>"],
        ]),
        P("<strong>百万行、几十 GB——对任何数据库都是小数据。</strong>"
          "所以默认策略应当是<strong>全部保留</strong>，"
          "而不是一上来就设计复杂的归档流程。"),
        H3("如果确实需要缩减"),
        OL([
            "<strong>先压缩 output，不要先删它</strong>——文本压缩率通常有 5–10 倍；",
            "<strong>按状态差异化保留</strong>：失败样本的 output 全留，成功样本的可以只留哈希或抽样留；",
            "<strong>冷热分层</strong>：三个月以上的运行归档到对象存储，"
            "<em>但保留每个 run 的聚合摘要在热库里</em>（趋势图需要它）；",
            "<strong>永远不要删的</strong>：主键、fingerprint、status、score。"
            "<em>这四列加起来每行不到 100 字节，百万行也只有几十 MB</em>——"
            "删它们省不了多少空间，却会让历史彻底不可用。",
        ]),
        CALLOUT("intuition", "关于保留策略有一条经验：<strong>决定「删什么」时，"
                             "想的不是「现在需要什么」，而是「半年后有人会问什么」。</strong>"
                             "<em>而半年后被问得最多的问题是「这道题当时为什么错了」——"
                             "答这个问题需要的恰恰是失败样本的原始输出。</em>"),
    ])),

    # ============================================================== 7
    ("report-shape", "报告的形状：从明细到一份可以贴出去的东西", "".join([
        P("把 C66/C67 的报告规范与本课的存储层接起来，得到一份完整报告的生成路径："),
        CODE("""明细行 (store)
  │
  ├─ 完整性校验（第 5 节）───────────► 不通过就停，不要出报告
  │
  ├─ 主指标 ────► micro + macro + 分母与排除说明
  ├─ 不确定度 ──► 按任务聚类自举（C66-04）
  ├─ 切片 ──────► 按难度/子系统/判分器强度（第 3 节）
  ├─ 与基线 diff ► fixed / regressed / churn / McNemar（第 4 节）
  ├─ 成本 ──────► $/success 而不是 $/task（C66-05）
  └─ 运行健康 ──► 五个数（模块 02 第 7 节）
  │
  └──► EVAL CARD（C66-05 的模板 + 本课的运行健康块）"""),
        UL([
            "<strong>完整性校验是一个门</strong>，不是一个提示——不通过就不该产出报告；",
            "<strong>每一个数字旁边都要带分母</strong>，这是本课能提供的最便宜的可信度提升；",
            "<strong>与基线的 diff 优先于绝对分数</strong>——因为读者真正要决策的是「这个改动能不能合」；",
            "<strong>运行健康块必须在报告里</strong>，而不是只在日志里。"
            "<em>「缓存命中率 30%（首次运行）」这种异常，只有出现在报告顶部才会被看见。</em>",
        ]),
        CALLOUT("intuition", "最后一句总结本模块：<strong>存储层的价值不在于存得快，"
                             "而在于它决定了你未来能问出什么问题。</strong>"
                             "<em>存了明细，半年后的新问题是一句查询；"
                             "只存了聚合，同一个问题是一次几百美元的重跑</em>——"
                             "而在那种成本下，大多数问题最终不会被问。"),
    ])),
    # ============================================================== 7x
    ("schema-evolution", "结果表的 schema 演化：加字段容易，改语义要命", "".join([
        P("结果表会活很多年，字段一定会变。这一节的规则与模块 01 的 spec 演化同构，"
          "但有一个结果表特有的约束。"),
        TABLE(["变更", "安全吗", "怎么做"], [
            ["<strong>加一列</strong>（可空）", "✅ 安全", "历史行为 NULL；聚合函数要能处理 NULL"],
            ["<strong>加一个 status 枚举值</strong>", "⚠️ 要小心", "<strong>必须同时更新「哪些计入分母」的策略表</strong>，否则新状态会被默认计入或默认排除"],
            ["<strong>改一列的语义</strong>", "🚫 危险", "<em>历史行照样能读，但含义变了</em>——必须加新列而不是改旧列"],
            ["<strong>删一列</strong>", "🚫 危险", "历史分析脚本会静默地少一个维度"],
        ]),
        CALLOUT("danger", "第二行是结果表特有的坑：<strong>新增一个 <code>status</code> 值时，"
                          "所有历史聚合都会被影响。</strong>"
                          "<em>比如加了 <code>env_error</code>（环境重置失败，见模块 02 第 8 节）——"
                          "如果聚合函数用的是「除了 scorer_error 都计入」，"
                          "那么这个新状态会被当成失败计入分母，历史数据与新数据的口径就不一致了。</em>"
                          "<strong>所以策略表（哪些计入分母）必须与 status 枚举<em>一起</em>版本化，"
                          "并且聚合结果要记录它用的是哪个版本的策略。</strong>"),
        P("一条便宜的防御：<strong>聚合函数遇到未知的 status 值时抛异常，而不是默默归类。</strong>"
          "<em>这把「新状态被静默错误分类」从一个数据问题变成了一个立刻可见的报错</em>——"
          "而这正是本课反复主张的：<strong>让不会报错的问题变得会报错。</strong>"),
    ])),

    # ============================================================== 8
    ("trend", "趋势与基线：一条时间序列比两个点有用得多", "".join([
        P("前七节都在讲「两次运行的比较」。这一节讲<strong>时间维度</strong>——"
          "因为很多问题只有在时间序列上才看得见。"),
        H3("三类只有趋势才能回答的问题"),
        TABLE(["问题", "两点比较能答吗", "趋势能答什么"], [
            ["<strong>「什么时候开始变的」</strong>", "✗", "定位到具体的某一天/某个 commit"],
            ["<strong>「这是波动还是趋势」</strong>", "✗", "看方差带与斜率——单次下降 2 个点可能是噪声，连续五次下降不是"],
            ["<strong>「基线该更新了吗」</strong>", "✗", "基线与当前的距离持续拉大 = 基线过期了"],
        ]),
        DUAL(
            "第三个问题在实践中最容易被忽略。<strong>CI 门禁需要一个基线，"
            "而基线用久了会过期</strong>——模型改进了很多次之后，"
            "拿三个月前的基线做比较，<em>「相对基线没有退化」这句话已经没有信息量了</em>。"
            "<strong>正确做法是滚动基线：每次成功合并后更新基线</strong>，"
            "让门禁始终比较的是「相对上一个已知良好状态」。",
            "但滚动基线有一个必须警惕的副作用：<span class=\"term\">渐进式退化</span>"
            "（creeping regression）。"
            "<em>如果每次都只退化 0.3 个点（远低于门禁阈值），"
            "滚动基线会把每一次都判为通过，而二十次之后总共退化了 6 个点</em>。"
            "<strong>防御方式是<em>同时</em>维护两个基线</strong>："
            "<strong>滚动基线</strong>（比上一次，抓突发退化）与"
            "<strong>锚定基线</strong>（比一个季度前的固定版本，抓渐进退化）。"
            "<em>两个都要在门禁里检查，阈值可以不同——锚定基线的阈值应当更宽但绝不能没有。</em>",
        ),
        CALLOUT("intuition", "渐进式退化是所有「只比上一次」的门禁的共同盲区，"
                             "而它在真实项目里非常常见——<strong>因为每一次单独看都是合理的取舍</strong>"
                             "（「这次为了修 bug 稍微牺牲一点分数」）。"
                             "<em>锚定基线的作用就是让这些取舍的<strong>累积效应</strong>可见。</em>"),
        H3("基线更新的一个反直觉细节"),
        P("滚动基线还有一个容易做错的地方：<strong>基线应当在「合并后」更新，"
          "而不是在「门禁通过后」更新。</strong>"
          "<em>两者的差别在于：门禁通过的 PR 可能最终没有被合并（作者放弃了、被别的 PR 取代了）。"
          "如果基线跟着「通过的门禁」走，它就会指向一个从未进入主干的状态</em>——"
          "而后续所有 PR 都在和这个不存在的状态比较。"),
        P("<strong>实现上这意味着基线更新必须由「合并事件」触发，而不是由「CI 成功」触发。</strong>"
          "<em>这个细节不做对的症状是：主干上的分数与基线记录的分数长期对不上</em>，"
          "而且很难查——因为每一次单独看都是正常的。"),
        H3("趋势图上该画什么"),
        UL([
            "<strong>主指标 + 置信带</strong>——没有置信带的趋势图会让人过度解读每一个小波动；",
            "<strong>标注事件</strong>：模型版本变更、任务集版本变更、judge prompt 变更。"
            "<em>指标跳变时第一件事是看有没有事件对齐——通常有</em>；",
            "<strong>分子集的趋势</strong>：核心能力集与回归集的趋势应当分开画，"
            "<em>它们的正常形态完全不同</em>（前者缓慢上升，后者应当贴着 100%）；",
            "<strong>运行健康的趋势</strong>（模块 02 的五个数）——"
            "<em>成本或重试率的缓慢上升，往往比分数变化更早地预告问题</em>。",
        ]),
    ])),
]

NB = [
    md("""# 03 · 结果存储与分析（宽事实表 / 后置聚合 / 切片与 Simpson / run diff / 完整性校验）

目标：把结果层做成「决定你未来能问出什么问题」的那一层。

本 notebook 你会亲手实现：
1. **宽事实表与只追加写入** —— 11 个字段的最小 schema
2. **后置聚合** —— 同一批结果算出 micro / macro / pass^k / 加权四个数
3. **切片与 Simpson 悖论** —— 复现「每一片都更好，总分却更低」
4. **交集重算** —— 任务集不一致时唯一正确的比较方式
5. **run diff** —— fixed / regressed / churn + McNemar，把「涨了 3 点」变成可行动的信息
6. **完整性校验** —— 五条应当写进加载函数的断言

> 心智模型：**存最细粒度的事实，把聚合留到查询时做。
> 你现在想不到的问题，半年后一定会被问到——而那时明细还在，就是一句查询。**"""),

    md("""## 0 · 环境与结果表"""),

    code("""import os, json, math, sqlite3, shutil, random, itertools
from collections import Counter, defaultdict

import numpy as np

TMP = os.path.abspath('./_eval_tmp')
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP, exist_ok=True)

SCHEMA = '''CREATE TABLE IF NOT EXISTS results (
    run_id       TEXT,
    task_id      TEXT,
    attempt      INTEGER,
    fingerprint  TEXT,
    dataset_ver  TEXT,
    scorer_ver   TEXT,
    status       TEXT,
    score        REAL,
    output       TEXT,
    cost_usd     REAL,
    latency_ms   INTEGER,
    PRIMARY KEY (run_id, task_id, attempt))'''

VALID_STATUS = {'ok', 'timeout', 'refusal', 'parse_error', 'scorer_error'}

class ResultStore:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def put_many(self, rows):
        \"\"\"只追加、幂等（主键冲突则忽略）。返回真正写入的行数。\"\"\"
        before = self.count()
        self.conn.executemany(
            'INSERT OR IGNORE INTO results VALUES (:run_id,:task_id,:attempt,:fingerprint,'
            ':dataset_ver,:scorer_ver,:status,:score,:output,:cost_usd,:latency_ms)', rows)
        self.conn.commit()
        return self.count() - before

    def count(self):
        return self.conn.execute('SELECT COUNT(*) FROM results').fetchone()[0]

    def rows(self, run_id=None):
        q = 'SELECT * FROM results' + (' WHERE run_id=?' if run_id else '')
        cur = self.conn.execute(q, (run_id,) if run_id else ())
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

store = ResultStore(os.path.join(TMP, 'results.db'))
print('结果表就位，字段:', [c.split()[0] for c in SCHEMA.split('(')[1].split(',')][:11])
print('\\n✅ 主键是 (run_id, task_id, attempt) —— 幂等性、pass^k、逐题 diff 全靠它。')"""),

    md("""## 1 · 造一批带任务属性的结果

任务属性（难度、子系统、判分器强度）**不存在结果表里**，而是来自数据集，
分析时 join 上去 —— 这样任务属性被重新标注时，历史结果不需要迁移。"""),

    code("""rng = np.random.default_rng(0)
SUBSYSTEMS = ['billing', 'flight', 'account']
DIFFICULTIES = ['easy', 'medium', 'hard']

TASK_META = {}
for i in range(500):
    tid = f't{i:03d}'
    TASK_META[tid] = {
        'task_id': tid,
        'difficulty': DIFFICULTIES[0] if i < 250 else (DIFFICULTIES[1] if i < 420 else DIFFICULTIES[2]),
        'subsystem': SUBSYSTEMS[i % 3],
        # 判分器强度（C66-02 的变异分数）：低于 0.6 的任务判分不可信
        'scorer_strength': float(np.clip(rng.beta(5, 2), 0, 1)),
    }

BASE_ACC = {'easy': 0.88, 'medium': 0.55, 'hard': 0.22}

def synth_run(run_id, fingerprint, attempts=3, acc_shift=0.0, seed=0,
              task_ids=None, dataset_ver='v3', scorer_ver='v2',
              p_timeout=0.02, p_scorer_err=0.004):
    r = np.random.default_rng(seed)
    ids = task_ids if task_ids is not None else list(TASK_META)
    out = []
    for tid in ids:
        m = TASK_META[tid]
        p = float(np.clip(BASE_ACC[m['difficulty']] + acc_shift, 0.01, 0.99))
        for a in range(attempts):
            u = r.random()
            if u < p_scorer_err:
                st, sc = 'scorer_error', None
            elif u < p_scorer_err + p_timeout:
                st, sc = 'timeout', None
            else:
                st, sc = 'ok', float(r.random() < p)
            out.append({'run_id': run_id, 'task_id': tid, 'attempt': a,
                        'fingerprint': fingerprint, 'dataset_ver': dataset_ver,
                        'scorer_ver': scorer_ver, 'status': st, 'score': sc,
                        'output': None if st == 'ok' else f'<{st} raw output>',
                        'cost_usd': float(r.gamma(2, 0.004)),
                        'latency_ms': int(r.gamma(3, 900))})
    return out

ROWS_A = synth_run('run-A', 'fpA00001', seed=1, acc_shift=0.0)
ROWS_B = synth_run('run-B', 'fpB00002', seed=2, acc_shift=0.05)
n_w = store.put_many(ROWS_A) + store.put_many(ROWS_B)
print(f'写入 {n_w} 行 | 表内共 {store.count()} 行')
assert n_w == len(ROWS_A) + len(ROWS_B)
# 幂等：重写一遍不产生新行
assert store.put_many(ROWS_A) == 0
print('重复写入新增行数: 0  ✓ 幂等')
print('\\n✅ 任务属性存在 TASK_META 里而不是结果表里——')
print('   难度被重新标注时（模块 01 的 meta_changed），历史结果一行都不用改。')"""),

    md("""## 2 · 后置聚合：同一批结果，四个都「对」的数字"""),

    code("""def _usable(rows):
    \"\"\"分母：排除 scorer_error（模块 02 的唯一可排除项），其余全部计入。\"\"\"
    return [r for r in rows if r['status'] != 'scorer_error']

def agg_micro(rows):
    u = _usable(rows)
    vals = [(r['score'] or 0.0) for r in u]
    return {'value': (sum(vals) / len(u)) if u else float('nan'),
            'n_rows': len(u), 'n_excluded': len(rows) - len(u), 'unit': 'rollout'}

def agg_macro_task(rows):
    by = defaultdict(list)
    for r in _usable(rows):
        by[r['task_id']].append(r['score'] or 0.0)
    means = [np.mean(v) for v in by.values() if v]
    return {'value': float(np.mean(means)) if means else float('nan'),
            'n_rows': len(means), 'n_excluded': len(rows) - len(_usable(rows)),
            'unit': 'task'}

def agg_macro_slice(rows, key):
    by = defaultdict(list)
    for r in _usable(rows):
        by[TASK_META[r['task_id']][key]].append(r['score'] or 0.0)
    means = [np.mean(v) for v in by.values() if v]
    return {'value': float(np.mean(means)) if means else float('nan'),
            'n_rows': len(means), 'n_excluded': len(rows) - len(_usable(rows)),
            'unit': key}

def agg_pass_pow_k(rows, k=3):
    by = defaultdict(list)
    for r in _usable(rows):
        by[r['task_id']].append(r['score'] or 0.0)
    hits = [1.0 if (len(v) >= k and all(x == 1.0 for x in v[:k])) else 0.0
            for v in by.values()]
    return {'value': float(np.mean(hits)) if hits else float('nan'),
            'n_rows': len(hits), 'n_excluded': len(rows) - len(_usable(rows)),
            'unit': f'task (pass^{k})'}

rows_a = store.rows('run-A')
print(f"{'口径':<26}{'数值':>10}{'分母':>8}{'排除':>8}{'单位':>16}")
for name, fn in [('micro（全部 rollout）', agg_micro),
                 ('macro by task', agg_macro_task),
                 ('macro by difficulty', lambda r: agg_macro_slice(r, 'difficulty')),
                 ('pass^3', agg_pass_pow_k)]:
    a = fn(rows_a)
    print(f'{name:<26}{a["value"]:>10.1%}{a["n_rows"]:>8}{a["n_excluded"]:>8}{a["unit"]:>16}')

m = agg_micro(rows_a); md_ = agg_macro_slice(rows_a, 'difficulty'); pk = agg_pass_pow_k(rows_a)
assert md_['value'] < m['value'], 'easy 题多，micro 被它们抬高；macro 等权后下降'
assert pk['value'] < m['value'], 'pass^3 必然低于单次成功率'
assert all(a['n_excluded'] > 0 for a in [m, md_, pk])
print('\\n✅ 四个数字都是「对」的，但回答的是四个不同的问题。')
print('   **只有存了明细，换口径才是一句查询而不是一次重跑。**')
print('   注意每个数字都带着分母与排除数——这是最便宜的可信度提升。')"""),

    code("""# 空输入必须返回 nan 而不是 0
empty = agg_micro([])
assert math.isnan(empty['value']), '分母为 0 必须返回 nan'
all_err = agg_micro([{'status': 'scorer_error', 'score': None, 'task_id': 't000'}] * 5)
assert math.isnan(all_err['value']) and all_err['n_excluded'] == 5
print('空输入 → nan ✓ | 全是判分器崩溃 → nan，排除 5 行 ✓')
print('✅ 返回 0 会让「没有数据」和「全错」在下游变得无法区分——')
print('   而这两者在告警逻辑里应当触发完全不同的动作。')"""),

    md("""## 3 · 切片与 Simpson 悖论：每一片都更好，总分却更低"""),

    code("""def slice_table(rows, key):
    by = defaultdict(list)
    for r in _usable(rows):
        by[TASK_META[r['task_id']][key]].append(r['score'] or 0.0)
    return {k: (float(np.mean(v)), len(v)) for k, v in sorted(by.items())}

# 构造 Simpson：模型 X 每一片都更好，但它的任务构成偏向难题
EASY_IDS = [t for t, m in TASK_META.items() if m['difficulty'] == 'easy']
HARD_IDS = [t for t, m in TASK_META.items() if m['difficulty'] == 'hard']

rows_X = (synth_run('run-X', 'fpX', attempts=3, seed=11, acc_shift=0.12,
                    task_ids=EASY_IDS[:60], p_timeout=0.0, p_scorer_err=0.0)
          + synth_run('run-X', 'fpX', attempts=3, seed=12, acc_shift=0.12,
                      task_ids=HARD_IDS, p_timeout=0.0, p_scorer_err=0.0))
rows_Y = (synth_run('run-Y', 'fpY', attempts=3, seed=13, acc_shift=0.0,
                    task_ids=EASY_IDS, p_timeout=0.0, p_scorer_err=0.0)
          + synth_run('run-Y', 'fpY', attempts=3, seed=14, acc_shift=0.0,
                      task_ids=HARD_IDS[:30], p_timeout=0.0, p_scorer_err=0.0))

sx, sy = slice_table(rows_X, 'difficulty'), slice_table(rows_Y, 'difficulty')
print(f"{'难度':<10}{'模型X':>16}{'模型Y':>16}")
for d in ['easy', 'hard']:
    vx, nx = sx.get(d, (float('nan'), 0)); vy, ny = sy.get(d, (float('nan'), 0))
    print(f'{d:<10}{f"{vx:.0%} (n={nx})":>16}{f"{vy:.0%} (n={ny})":>16}')
tx, ty = agg_micro(rows_X)['value'], agg_micro(rows_Y)['value']
print(f'{"总计":<10}{tx:>16.0%}{ty:>16.0%}')

assert sx['easy'][0] > sy['easy'][0] and sx['hard'][0] > sy['hard'][0], 'X 每一片都更好'
assert tx < ty, '但 X 的总分更低'
print('\\n⚠️ Simpson 悖论：X 在每个难度上都更好，总分却更低——')
print('   因为 X 跑的难题占比更高。**总分被「跑了哪些题」这个混杂变量污染了。**')
print('   在评测里这最常见的成因不是有人故意，而是两次运行的任务集不完全相同')
print('   （超时被排除、新加了题、某些题在一次运行里失败被跳过）。')"""),

    code("""def intersect_recompute(rows_a, rows_b):
    \"\"\"唯一正确的比较方式：在共同任务集上重算两边（= 流行病学的直接标准化）。\"\"\"
    ids_a = {r['task_id'] for r in _usable(rows_a)}
    ids_b = {r['task_id'] for r in _usable(rows_b)}
    common = ids_a & ids_b
    fa = [r for r in rows_a if r['task_id'] in common]
    fb = [r for r in rows_b if r['task_id'] in common]
    return {'n_common': len(common), 'n_only_a': len(ids_a - common),
            'n_only_b': len(ids_b - common),
            'a': agg_micro(fa)['value'], 'b': agg_micro(fb)['value']}

ic = intersect_recompute(rows_X, rows_Y)
print(f'任务集: X 独有 {ic["n_only_a"]} 条 | 共同 {ic["n_common"]} 条 | Y 独有 {ic["n_only_b"]} 条')
print(f'朴素比较:   X {tx:.1%}  vs  Y {ty:.1%}   → 差 {tx-ty:+.1%}')
print(f'交集重算:   X {ic["a"]:.1%}  vs  Y {ic["b"]:.1%}   → 差 {ic["a"]-ic["b"]:+.1%}')
assert ic['n_common'] > 0
assert (tx - ty) < 0 < (ic['a'] - ic['b']), '交集重算把结论翻了过来'
print('\\n✅ 交集重算把结论翻了过来——而这才是正确的那个。')
print('   → 报告规范：**比较两次运行前必须先检查任务集是否一致，不一致就在交集上重算。**')
print('   这条检查应当是自动的（模块 04 会把它变成 CI 里的一行断言）。')"""),

    md("""## 4 · Run diff：从「涨了 3 点」到「哪些题变了」"""),

    code("""def task_scores(rows, agg='mean'):
    by = defaultdict(list)
    for r in _usable(rows):
        by[r['task_id']].append(r['score'] or 0.0)
    if agg == 'mean':
        return {t: float(np.mean(v)) for t, v in by.items() if v}
    return {t: float(v[0]) for t, v in by.items() if v}

def run_diff(rows_a, rows_b, thresh=0.5):
    \"\"\"逐题二值化后比较。返回 fixed / regressed / churn / net + McNemar。\"\"\"
    a, b = task_scores(rows_a), task_scores(rows_b)
    common = sorted(set(a) & set(b))
    fixed = [t for t in common if a[t] < thresh <= b[t]]
    regressed = [t for t in common if b[t] < thresh <= a[t]]
    f, r = len(fixed), len(regressed)
    if f + r == 0:
        chi2, p = 0.0, 1.0
    else:
        chi2 = max(abs(f - r) - 1, 0) ** 2 / (f + r)
        p = math.erfc(math.sqrt(chi2 / 2))
    return {'n_common': len(common), 'fixed': f, 'regressed': r,
            'churn': f + r, 'net': f - r, 'chi2': chi2, 'p': p,
            'fixed_ids': fixed[:5], 'regressed_ids': regressed[:5]}

d = run_diff(store.rows('run-A'), store.rows('run-B'))
print(f'共同任务 {d["n_common"]} 条')
print(f'  修好了 (fixed)      {d["fixed"]:>4}')
print(f'  退化了 (regressed)  {d["regressed"]:>4}   ← 净提升为正也可能伴随大量退化')
print(f'  翻转总数 (churn)    {d["churn"]:>4}')
print(f'  净变化 (net)        {d["net"]:>+4}')
print(f'  McNemar chi2={d["chi2"]:.2f}  p={d["p"]:.4f}')
print(f'  退化的样例: {d["regressed_ids"]}')
assert d['churn'] >= abs(d['net'])
ratio = d['churn'] / max(abs(d['net']), 1)
print(f'\\nchurn / |net| = {ratio:.1f}')
if ratio > 4:
    print('⚠️ churn 远大于净变化 → 模型在这些题上本来就不稳定，')
    print('   这次的「提升」很可能只是采样运气。**该增加重复次数，而不是宣布提升。**')
print('\\n✅ 「涨了 3 点」不可行动；「修好 42 道、退化 30 道，其中 XXX 是核心路径」可行动。')"""),

    code("""# 逐题变化矩阵：按切片看退化集中在哪里
def regression_by_slice(rows_a, rows_b, key, thresh=0.5):
    a, b = task_scores(rows_a), task_scores(rows_b)
    common = set(a) & set(b)
    tab = defaultdict(lambda: {'fixed': 0, 'regressed': 0, 'n': 0})
    for t in common:
        k = TASK_META[t][key]
        tab[k]['n'] += 1
        if a[t] < thresh <= b[t]:
            tab[k]['fixed'] += 1
        elif b[t] < thresh <= a[t]:
            tab[k]['regressed'] += 1
    return dict(tab)

rb = regression_by_slice(store.rows('run-A'), store.rows('run-B'), 'difficulty')
print(f"{'难度':<10}{'n':>6}{'fixed':>8}{'regressed':>12}{'net':>8}")
for k in ['easy', 'medium', 'hard']:
    v = rb.get(k, {'n': 0, 'fixed': 0, 'regressed': 0})
    print(f'{k:<10}{v["n"]:>6}{v["fixed"]:>8}{v["regressed"]:>12}{v["fixed"]-v["regressed"]:>+8}')
assert sum(v['n'] for v in rb.values()) == d['n_common']
print('\\n✅ 这张表回答的是「提升来自哪里、退化集中在哪里」——')
print('   如果退化全部集中在 easy 上，那是一个比「总分涨了」严重得多的信号。')"""),

    md("""## 5 · 完整性校验：五条写进加载函数的断言"""),

    code("""def integrity_check(rows, expected_tasks, expected_attempts):
    problems = []
    # ① 指纹唯一
    fps = {r['fingerprint'] for r in rows}
    if len(fps) != 1:
        problems.append(f'指纹不唯一: {sorted(fps)} → run_id 被复用了')
    # ② 覆盖完整（比对**预期行数**，而不是已有行数的内部一致性）
    expected = expected_tasks * expected_attempts
    if len(rows) != expected:
        problems.append(f'行数 {len(rows)} != 预期 {expected} → 有任务被静默跳过')
    # ③ 无重复主键
    keys = [(r['run_id'], r['task_id'], r['attempt']) for r in rows]
    if len(set(keys)) != len(keys):
        problems.append('主键重复 → 幂等写入被绕过')
    # ④ 状态合法 且 status=='ok' ⟺ score 非空
    bad_status = {r['status'] for r in rows} - VALID_STATUS
    if bad_status:
        problems.append(f'非法状态: {bad_status}')
    mismatched = sum(1 for r in rows if (r['status'] == 'ok') != (r['score'] is not None))
    if mismatched:
        problems.append(f'{mismatched} 行的 status 与 score 不一致')
    # ⑤ 数据集版本一致
    dvs = {r['dataset_ver'] for r in rows}
    if len(dvs) != 1:
        problems.append(f'数据集版本不一致: {sorted(dvs)}')
    return (len(problems) == 0, problems)

ok, probs = integrity_check(store.rows('run-A'), len(TASK_META), 3)
print('run-A 完整性:', ok, probs)
assert ok

# 三种真实事故
bad1 = store.rows('run-A') + [dict(store.rows('run-B')[0], run_id='run-A')]   # 指纹混入
bad2 = store.rows('run-A')[:-30]                                              # 任务被静默跳过
bad3 = [dict(r) for r in store.rows('run-A')]; bad3[0]['status'] = 'ok'; bad3[0]['score'] = None
for name, rows_bad, n_task in [('run_id 被复用', bad1, len(TASK_META)),
                               ('任务被静默跳过', bad2, len(TASK_META)),
                               ('status 与 score 不一致', bad3, len(TASK_META))]:
    ok_, p_ = integrity_check(rows_bad, n_task, 3)
    print(f'{name:<24} 通过={ok_}  → {p_[0][:44]}')
    assert not ok_
print('\\n✅ 五条检查全部生效。**它们必须放在加载函数里，而不是一个「记得跑一下」的脚本里**——')
print('   放在加载函数里，它就不可能被忘记。')"""),

    md("""## ✏️ 练习 1：带分母的聚合函数

实现 `agg_with_denominator(rows, filter_fn=None)`：返回
`{'value', 'n_rows', 'n_excluded_scorer', 'n_filtered_out'}`。
`filter_fn(row) -> bool` 用来做切片（例如只保留判分器强度 ≥ 0.6 的任务）。
分母排除 `scorer_error`；被 `filter_fn` 过滤掉的单独计数。"""),

    code("""def agg_with_denominator(rows, filter_fn=None):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
all_rows = store.rows('run-A')
a1 = agg_with_denominator(all_rows)
assert abs(a1['value'] - agg_micro(all_rows)['value']) < 1e-12
assert a1['n_excluded_scorer'] > 0 and a1['n_filtered_out'] == 0

strong_only = agg_with_denominator(
    all_rows, filter_fn=lambda r: TASK_META[r['task_id']]['scorer_strength'] >= 0.6)
print(f"全部任务:       {a1['value']:.1%}  (n={a1['n_rows']}, 排除判分器崩溃 {a1['n_excluded_scorer']})")
print(f"只用强判分任务: {strong_only['value']:.1%}  (n={strong_only['n_rows']}, "
      f"被过滤 {strong_only['n_filtered_out']})")
assert strong_only['n_rows'] < a1['n_rows'] and strong_only['n_filtered_out'] > 0
print('✅ 练习 1 通过：「只用判分器强的任务重算一遍」是 C66-02 的敏感性分析——')
print('   有明细在，它就是一个 filter_fn，而不是一次重跑。')"""),

    md("""## ✏️ 练习 2：任务集一致性检查

实现 `same_task_set(rows_a, rows_b)`：返回
`(是否一致, 只在 A 里的任务数, 只在 B 里的任务数)`。
任务集只统计 `status != 'scorer_error'` 的行涉及的 task_id。"""),

    code("""def same_task_set(rows_a, rows_b):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
same, oa, ob = same_task_set(store.rows('run-A'), store.rows('run-B'))
print(f'run-A vs run-B: 一致={same} (A 独有 {oa}, B 独有 {ob})')
diff_, oa2, ob2 = same_task_set(rows_X, rows_Y)
print(f'run-X vs run-Y: 一致={diff_} (X 独有 {oa2}, Y 独有 {ob2})')
assert diff_ is False and oa2 > 0 and ob2 > 0
assert same_task_set(store.rows('run-A'), store.rows('run-A'))[0] is True
print('✅ 练习 2 通过：这个函数应当在任何跨 run 比较之前被调用——')
print('   返回 False 时，直接比较总分是无意义的（Simpson），必须走交集重算。')"""),

    md("""## ✏️ 练习 3：churn 与净变化的判读

实现 `diff_verdict(diff, min_net=10, max_churn_ratio=4.0, alpha=0.05)`：
根据 run_diff 的结果返回结论字符串：
- `p >= alpha` → `'not_significant'`
- `churn / max(|net|,1) > max_churn_ratio` → `'noisy'`（波动太大，该加重复次数）
- `net >= min_net` → `'improved'`；`net <= -min_net` → `'regressed'`
- 其余 → `'inconclusive'`

判定顺序就是上面的顺序。"""),

    code("""def diff_verdict(diff, min_net=10, max_churn_ratio=4.0, alpha=0.05):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert diff_verdict({'p': 0.4, 'churn': 10, 'net': 2}) == 'not_significant'
assert diff_verdict({'p': 0.001, 'churn': 100, 'net': 5}) == 'noisy'
assert diff_verdict({'p': 0.001, 'churn': 60, 'net': 40}) == 'improved'
assert diff_verdict({'p': 0.001, 'churn': 60, 'net': -40}) == 'regressed'
assert diff_verdict({'p': 0.001, 'churn': 12, 'net': 4}) == 'inconclusive'
print('实际 run-A → run-B 的判读:', diff_verdict(d))
print(f'  (net={d["net"]}, churn={d["churn"]}, p={d["p"]:.4f})')
print('✅ 练习 3 通过：`noisy` 这一档是最有价值的——')
print('   它把「显著但不可靠」的情况单独拎了出来，而 p 值本身区分不了这个。')"""),

    md("""## ✏️ 练习 4：存储规模估算

实现 `storage_estimate(n_tasks, attempts, runs_per_year, bytes_per_row_core=100,
bytes_per_output=2000, keep_output_for=('timeout','refusal','parse_error','scorer_error'),
fail_rate=0.03)`：返回
`{'rows', 'core_gb', 'output_gb', 'total_gb'}`。
核心列每行 `bytes_per_row_core`；只有失败样本保留 output。"""),

    code("""def storage_estimate(n_tasks, attempts, runs_per_year,
                     bytes_per_row_core=100, bytes_per_output=2000,
                     fail_rate=0.03):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
SCENARIOS = [('CI smoke', 60, 1, 5000), ('每日全量', 500, 3, 365), ('模型选型', 500, 5, 300)]
print(f"{'场景':<14}{'行数':>12}{'核心列 GB':>12}{'output GB':>12}{'合计 GB':>10}")
total = 0.0
for name, nt, at, ry in SCENARIOS:
    e = storage_estimate(nt, at, ry)
    total += e['total_gb']
    print(f'{name:<14}{e["rows"]:>12,}{e["core_gb"]:>12.2f}{e["output_gb"]:>12.2f}'
          f'{e["total_gb"]:>10.2f}')
print(f'{"合计":<14}{"":>12}{"":>12}{"":>12}{total:>10.2f}')
e1 = storage_estimate(500, 3, 365)
assert e1['rows'] == 500 * 3 * 365
assert e1['core_gb'] < 1.0, '核心列很小'
assert e1['total_gb'] > e1['core_gb']
assert total < 20, '三个场景加起来仍然是小数据'
print('\\n✅ 练习 4 通过：几百万行、十几 GB——对任何数据库都是小数据。')
print('   所以默认策略应当是**全部保留**，而不是一上来就设计复杂的归档流程。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def agg_with_denominator(rows, filter_fn=None):
    kept = [r for r in rows if (filter_fn is None or filter_fn(r))]
    n_filtered = len(rows) - len(kept)
    usable = [r for r in kept if r['status'] != 'scorer_error']
    n_excl = len(kept) - len(usable)
    vals = [(r['score'] or 0.0) for r in usable]
    return {'value': (sum(vals) / len(usable)) if usable else float('nan'),
            'n_rows': len(usable), 'n_excluded_scorer': n_excl,
            'n_filtered_out': n_filtered}"""),

    code("""# 练习 2 参考答案
def same_task_set(rows_a, rows_b):
    ia = {r['task_id'] for r in rows_a if r['status'] != 'scorer_error'}
    ib = {r['task_id'] for r in rows_b if r['status'] != 'scorer_error'}
    return (ia == ib, len(ia - ib), len(ib - ia))"""),

    code("""# 练习 3 参考答案
def diff_verdict(diff, min_net=10, max_churn_ratio=4.0, alpha=0.05):
    if diff['p'] >= alpha:
        return 'not_significant'
    if diff['churn'] / max(abs(diff['net']), 1) > max_churn_ratio:
        return 'noisy'
    if diff['net'] >= min_net:
        return 'improved'
    if diff['net'] <= -min_net:
        return 'regressed'
    return 'inconclusive'"""),

    code("""# 练习 4 参考答案
def storage_estimate(n_tasks, attempts, runs_per_year,
                     bytes_per_row_core=100, bytes_per_output=2000,
                     fail_rate=0.03):
    rows = n_tasks * attempts * runs_per_year
    core = rows * bytes_per_row_core
    out = rows * fail_rate * bytes_per_output
    GB = 1024 ** 3
    return {'rows': rows, 'core_gb': core / GB, 'output_gb': out / GB,
            'total_gb': (core + out) / GB}"""),

    md("""---
## 🧪 真实工程胶囊：结果层的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 加载函数里必须包含完整性校验（不是一个"记得跑"的脚本）
# ══════════════════════════════════════════════════════════════════
def load_run(store, run_id, spec):
    rows = store.rows(run_id)
    ok, problems = integrity_check(rows, n_tasks=spec["dataset"]["n"],
                                   n_attempts=spec["budget"]["max_attempts"])
    if not ok:
        raise ValueError(f"run {run_id} 完整性校验失败: {problems}")
    return rows
# 关键：**校验失败就抛异常，不产出报告**。警告会被忽略，异常不会。

# ══════════════════════════════════════════════════════════════════
# B. 常用切片查询（有明细的话都是一句 SQL）
# ══════════════════════════════════════════════════════════════════
# 按难度:
#   SELECT m.difficulty, AVG(r.score), COUNT(*)
#   FROM results r JOIN task_meta m USING (task_id)
#   WHERE r.run_id = ? AND r.status != 'scorer_error'
#   GROUP BY m.difficulty
#
# 只用强判分任务（C66-02 的敏感性分析）:
#   ... AND m.scorer_strength >= 0.6
#
# 首次尝试 vs 重试（看恢复力）:
#   ... GROUP BY r.attempt
#
# 逐题 diff（第 4 节）:
#   SELECT a.task_id, AVG(a.score) sa, AVG(b.score) sb
#   FROM results a JOIN results b USING (task_id)
#   WHERE a.run_id=? AND b.run_id=? GROUP BY a.task_id
#   HAVING (sa<0.5) != (sb<0.5)          -- 只看翻转的题

# ══════════════════════════════════════════════════════════════════
# C. 报告生成的固定顺序（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
# 1) 完整性校验 → 不通过就停
# 2) 任务集一致性检查 → 不一致就交集重算（练习 2）
# 3) 主指标: micro + macro，**每个都带分母与排除说明**
# 4) 不确定度: 按任务聚类自举（C66-04）
# 5) 与基线 diff: fixed/regressed/churn + McNemar + verdict（练习 3）
# 6) 切片表: 难度 × 子系统
# 7) 成本: $/success（C66-05）
# 8) 运行健康: 五个数（本课模块 02）

# ══════════════════════════════════════════════════════════════════
# D. 保留策略：默认全留
# ══════════════════════════════════════════════════════════════════
# 永远不删: run_id, task_id, attempt, fingerprint, status, score
#           （每行 < 100 字节，百万行也只有几十 MB）
# 可以压缩: output（文本压缩率 5-10 倍）
# 可以分层: 三个月以上归档到对象存储，**但每个 run 的聚合摘要留在热库**
# 差异化:   失败样本的 output 全留，成功样本的可以只留哈希
#           —— 因为你要看的永远是失败的那些
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 宽事实表 | 存最细粒度事实，聚合留到查询时做 | schema 设计 |
| 后置聚合 | 同一批结果算出四个都对但含义不同的数；每个都要带分母 | 报告 |
| 空输入返回 nan | 返回 0 会让「没数据」和「全错」无法区分 | 聚合函数 |
| Simpson 悖论 | 任务集不同则总分不可比——必须交集重算 | 跨 run 比较 |
| run diff | churn / |net| > 4 时该加重复次数，而不是宣布提升 | 判读改动 |
| 五条完整性校验 | 放进**加载函数**，不是放进「记得跑一下」的脚本 | 每次加载 |
| 保留策略 | 百万行几十 GB 是小数据；默认全留，失败样本的 output 尤其不能删 | 存储规划 |

下一模块：**04 · CI 回归门禁**——阈值该怎么从方差推出来、
什么该阻断什么只该警告、以及「误报让团队关掉门禁」这个最终失败模式。""")
]
