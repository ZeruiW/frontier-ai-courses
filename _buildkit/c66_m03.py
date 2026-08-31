# -*- coding: utf-8 -*-
"""C66 模块 03 · 轨迹级与过程级评测。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 02（结果判分）；"
                 "见过任意一种 agent 的运行日志（ReAct 的 thought/action/observation 三段式即可）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_trajectory_eval.ipynb'
                       '（轨迹 schema 与模拟器 / 六个轨迹指标 / 循环检测 / 轨迹编辑距离与 LCS / '
                       '失败模式自动分类器 / 过程标注一致性 kappa / Goodhart 演示：优化步数会教会 agent 提前放弃）'),
    ("核心参考", "Yao et al., <em>ReAct</em>（ICLR 2023，轨迹的三段式结构）· "
                 "Lightman et al., <em>Let's Verify Step by Step</em>（2023，过程监督）· "
                 "Uesato et al., <em>Process- vs Outcome-based Feedback</em>（2022）· "
                 "OpenTelemetry GenAI 语义约定（span 结构）· "
                 "本课程 C10 模块 02（标注者一致性）· C22（过程奖励模型 PRM）· C33（上下文与记忆）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-trajectory", "结果层看不见的三件事：钱、卡点、恢复力", "".join([
        P("模块 02 结束时留了一个尾巴：两个 micro 成功率相同的 agent，可能是完全不同的两个产品。"
          "轨迹层要回答的正是结果层结构性看不见的三个问题。"),
        TABLE(["问题", "结果层为什么看不见", "轨迹层用什么回答", "决策价值"], [
            ["<strong>钱花在哪</strong>", "成功率是 0/1，与消耗无关", "步数、token、工具调用次数、墙钟时间的分布（尤其是<strong>尾部</strong>）", "直接决定单位任务成本与能不能上线"],
            ["<strong>卡在哪一步</strong>", "失败只有一个 0，没有位置信息", "失败时的最后动作类型、已达成的 checkpoint、错误码分布", "决定下一步该修什么（工具？提示？上下文？）"],
            ["<strong>能不能从错误里爬出来</strong>", "成功掩盖了过程中的挣扎，失败掩盖了差一点成功", "<strong>恢复率</strong>：遇到工具报错后，后续步骤是否走上正轨", "这是把 demo 变成产品的最关键能力"],
        ]),
        DUAL(
            "为什么「恢复力」值得被单列成一个一级指标？因为真实环境里，"
            "<strong>工具报错、页面加载失败、命令返回非零状态，是常态而不是异常</strong>。"
            "一个在干净环境里成功率 60% 的 agent，如果每次遇到报错就原地打转，"
            "上线后的成功率可能掉到 20%——而这个落差在任何离线成功率数字里都看不出来。",
            "形式化地说，令 $E$ 是「轨迹中至少出现一次工具错误」这个事件。"
            "我们真正关心的是<strong>条件成功率</strong> $P(\\text{success} \\mid E)$ 与 "
            "$P(\\text{success} \\mid \\neg E)$ 的差距，以及 $P(E)$ 在离线环境与线上环境之间的漂移。"
            "<em>总成功率 $P(\\text{success})$ 把这三个量混成了一个数——"
            "它在离线到线上的迁移中最不稳定，恰恰因为 $P(E)$ 在两个环境里差别巨大。</em>",
        ),
        CALLOUT("intuition", "一句可以直接用在评审会上的话：<strong>「成功率」是一个终点指标，"
                             "而 agent 上线后遇到的分布，主要由「过程中会不会出岔子」决定。"
                             "所以离线评测必须<em>主动注入错误</em>，并单独报告注入错误后的条件成功率。</strong>"
                             "notebook 第 2 节给出注入方式与恢复率的计算。"),
    ])),

    # ============================================================== 2
    ("schema", "日志 schema：没记下来的东西，事后一个也补不回来", "".join([
        P("轨迹分析是<strong>唯一一个「事前决定、事后无法补救」</strong>的评测环节。"
          "任务集不够可以补跑，判分器有偏可以重判，但如果当初没记工具的返回码，"
          "你今天就永远算不出恢复率——除非把所有实验重跑一遍。"),
        H3("最小可用 schema"),
        CODE("""{
  "run_id": "eval-2026-08-28-a3f1",     // 一次评测运行
  "task_id": "billing-refund-017",
  "attempt": 2,                          // 同一任务的第几次重复（04 模块的 pass^k 需要）
  "model": "…", "scaffold_version": "harness@1.7.2",
  "steps": [
    {
      "i": 0,
      "type": "tool_call",               // tool_call | model_output | user_turn | error
      "tool": "search_orders",
      "args_hash": "9c1f…",              // 用于检测重复调用（冗余率）
      "status": "ok",                    // ok | tool_error | timeout | refused
      "error_code": null,
      "latency_ms": 812,
      "tokens_in": 3120, "tokens_out": 88,
      "checkpoint_reached": null         // 达成了哪个 checkpoint（模块 02）
    }
  ],
  "outcome": {"score": 1, "reason": null},
  "totals": {"steps": 14, "tokens": 51230, "wall_ms": 41200, "usd": 0.34}
}"""),
        TABLE(["字段", "不记会失去什么", "重要度"], [
            ["<code>args_hash</code>", "算不出<strong>冗余调用率</strong>与循环检测——agent 反复用同样参数调同一个工具是最常见的浪费", "★★★"],
            ["<code>status</code> / <code>error_code</code>", "算不出<strong>恢复率</strong>，也无法把失败按错误类型分组", "★★★"],
            ["<code>attempt</code>", "无法计算 pass^k / pass@k，多次重复的数据退化成一堆无法配对的独立样本", "★★★"],
            ["<code>scaffold_version</code>", "历史结果不可比——这是 agent 评测里最容易被忽略的可复现字段（05 模块）", "★★★"],
            ["<code>tokens_in/out</code>", "成本无法归一化，所有跨模型对比失效", "★★☆"],
            ["<code>checkpoint_reached</code>", "无法做部分得分，也无法定位卡点", "★★☆"],
            ["<code>latency_ms</code>", "看不出「慢」是模型慢还是工具慢", "★☆☆"],
        ]),
        CALLOUT("warn", "一条现实建议：<strong>轨迹日志的 schema 应该在你写第一个 agent 之前就定好，"
                        "并且从此只增字段、不改语义</strong>。"
                        "字段语义一改，历史数据就变成需要考古的东西。"
                        "如果你的团队已经在用 OpenTelemetry，直接沿用 <em>GenAI 语义约定</em> 里的 span 属性名"
                        "（<code>gen_ai.*</code>）而不是自造一套——理由不是标准更优雅，"
                        "而是<strong>现成的 trace 查看器可以直接用</strong>（C68 模块 05 展开）。"),
    ])),

    # ============================================================== 3
    ("metrics", "六个轨迹指标：定义、直觉与它们各自的失效方式", "".join([
        P("轨迹指标不需要很多。下面六个覆盖了绝大部分归因需求，每一个都能从上面的 schema 直接算出来。"),
        TABLE(["指标", "定义", "回答什么", "什么时候会骗你"], [
            ["<strong>步数 / token / 成本</strong>", "轨迹长度与消耗，报<strong>中位数 + P90</strong>而非均值", "这个 agent 贵不贵", "均值被少数超长轨迹主导；<em>必须报分位数</em>"],
            ["<strong>工具调用精确率</strong>", "调用的工具中，属于「本任务确实需要」的比例", "它是不是在乱试工具", "需要标注「本任务需要哪些工具」；标注本身有主观性"],
            ["<strong>工具调用召回率</strong>", "本任务需要的工具中，实际被用上的比例", "它是不是漏掉了关键信息源", "有些任务不用某工具也能做对——低召回不必然是坏事"],
            ["<strong>无效动作率</strong>", "<code>status != ok</code> 的步数占比", "环境/参数用得对不对", "把「探索性试错」也算成无效——需要区分「首次探索」与「重复犯错」"],
            ["<strong>冗余率</strong>", "<code>(tool, args_hash)</code> 重复出现的步数占比", "有没有在原地打转", "合法的轮询（等任务完成）会被误判；需要白名单"],
            ["<strong>恢复率</strong>", "出现工具错误后，<em>下一步换了策略且最终成功</em> 的比例", "遇到岔子能不能自救", "任务本身太简单时恢复率虚高（错误无关紧要）"],
        ]),
        H3("循环检测：最有价值的单个信号"),
        P("在真实运行日志里，最常见、最贵、也最容易自动检出的失败是<strong>循环</strong>："
          "agent 反复执行同一组动作，每次都得到同样的结果，直到耗尽预算。检测方法有两层："),
        OL([
            "<strong>精确循环</strong>：连续窗口内出现重复的 <code>(tool, args_hash)</code> 序列。"
            "用一个滑动窗口 + 哈希即可，$O(n)$。",
            "<strong>语义循环</strong>：动作不完全相同（比如每次搜索的关键词略有变化），"
            "但观测结果几乎不变。检测方式是看<strong>状态摘要的变化量</strong>——"
            "连续 $k$ 步状态摘要没有变化，即判定为语义循环。",
        ]),
        CALLOUT("intuition", "循环检测的工程价值在于它<strong>可以直接接到预算控制上</strong>："
                             "检出循环就提前终止这条轨迹，把省下的预算拿去跑别的任务。"
                             "在成本受限的评测里（05 模块），这一条能把有效样本量提高一大截。"
                             "<em>注意：提前终止会改变你测量的东西——被终止的轨迹要单独标记为 "
                             "<code>terminated_by_loop_detector</code>，而不是简单记成失败。</em>"),
        H3("为什么不要把这些指标压成一个总分"),
        P("很容易产生的冲动是：把六个指标加权求和，得到一个「轨迹质量分」。"
          "<strong>不要这么做。</strong>原因在第 7 节——这些指标互相之间存在真实的权衡"
          "（少走弯路 vs 充分探索），压成一个数会让权衡消失，而权衡恰恰是你要看的东西。"),
    ])),

    # ============================================================== 4
    ("compare-path", "和参考轨迹比：编辑距离、LCS，以及「唯一正确路径」这个陷阱", "".join([
        P("一个自然的想法：既然人类专家能做这个任务，就录一条参考轨迹，"
          "然后用编辑距离衡量 agent 偏离了多远。这个方法有用，但必须先破除一个误解。"),
        CALLOUT("danger", "<strong>「参考轨迹 = 唯一正确路径」是错的，而且是危险的错。</strong>"
                          "同一个任务通常有多条合法路径，而且 <em>agent 的最优路径未必等于人类的最优路径</em>"
                          "——它读文件比人快，试错比人便宜，所以「先粗读全部再定位」对它可能比"
                          "「精确检索」更划算。<strong>把轨迹相似度当作主指标，等于在训练 agent 模仿人类的低效之处。</strong>"),
        H3("那轨迹比较有什么用"),
        TABLE(["用法", "怎么做", "为什么这样是安全的"], [
            ["<strong>必经动作检查</strong>", "只检查参考轨迹里的<em>关键动作子集</em>（如「必须查过退款政策」）是否作为<strong>子序列</strong>出现", "只约束必须发生的事，不约束顺序与其余动作——这是 checkpoint 在轨迹层的形式"],
            ["<strong>禁止动作检查</strong>", "断言某些动作从未出现（如「从未对他人账户做写操作」）", "只约束不许发生的事，零假阳性风险"],
            ["<strong>偏离度作为诊断量</strong>", "算编辑距离，但只用于<em>排序人工复核的优先级</em>（偏离最大的先看）", "不进主指标，只做分诊"],
            ["<strong>路径多样性统计</strong>", "把成功轨迹聚类，看有几种解法", "揭示任务是否真的有唯一解，反过来验证任务设计", ],
        ]),
        H3("两种距离，各自适用的场景"),
        MATH(r"d_{\text{edit}}(a, b) = \min\{\text{插入/删除/替换次数，把动作序列 } a \text{ 变成 } b\}"),
        P("<strong>编辑距离</strong>对整体结构敏感，适合「路径应该大致相同」的短任务；"
          "<strong>最长公共子序列（LCS）</strong>只看必经动作有没有按序出现，对插入的额外动作宽容，"
          "适合「允许 agent 多做探索」的长任务。<em>做必经动作检查时用 LCS，做偏离度分诊时用编辑距离。</em>"),
        DUAL(
            "一句实践总结：<strong>轨迹比较适合做「断言」，不适合做「打分」。</strong>"
            "「必须包含 X」「不许出现 Y」是断言，客观且零争议；"
            "「和参考路径的相似度是 0.73」是打分，而这个 0.73 没有任何可解释的业务含义。",
            "从测量的角度，轨迹相似度是一个<span class=\"term\">代理指标</span>，"
            "它与真实效用之间的相关性依赖「参考轨迹确实是最优的」这个未经验证的假设。"
            "把它作为主指标会引入 <span class=\"term\">specification gaming</span> 的一个变体："
            "<em>agent 学会模仿参考轨迹的表面结构而不是它的目的</em>。"
            "断言型的检查则没有这个问题，因为它们只编码了必要条件，不编码充分条件。",
        ),
    ])),

    # ============================================================== 5
    ("process-level", "过程级评测：步骤 rubric、过程奖励与标注一致性", "".join([
        P("第三层，也是最贵的一层：<strong>逐步判断「这一步做得对不对」</strong>。"
          "它的价值不在于给出更准的总分，而在于<strong>信用分配</strong>——"
          "把一次失败精确定位到某一步的某个决策。"),
        H3("三种过程级判分的来源"),
        TABLE(["来源", "怎么产生", "成本", "可靠性"], [
            ["<strong>规则</strong>", "写死的检查（这一步是否调用了必需的工具、参数是否合法）", "低", "高，但只能覆盖能写成规则的部分"],
            ["<strong>人工步骤标注</strong>", "标注员逐步打 好/中性/坏 三档", "<strong>极高</strong>（一条 40 步的轨迹要标 40 次）", "取决于标注规范；必须测 kappa（C10-02）"],
            ["<strong>过程奖励模型（PRM）</strong>", "用步骤标注训一个模型，之后自动打分", "训练贵，推理便宜", "在分布内可靠，分布外会失效——<strong>PRM 自己也需要被评测</strong>"],
        ]),
        CALLOUT("warn", "关于人工步骤标注有一个必须提前知道的现实：<strong>标注者之间的一致性通常显著低于结果级标注</strong>。"
                        "「这个任务完成了吗」容易达成共识；「第 17 步该不该先看日志」则见仁见智。"
                        "<strong>如果 Cohen's kappa 低于 0.4，这批过程标注不应该被用来训 PRM，也不应该进报告</strong>——"
                        "它测的是标注员的偏好，不是 agent 的质量。"
                        "解法是收窄标注问题：<em>不问「这一步好不好」，问「这一步是否让任务离目标更近」</em>，"
                        "后者的一致性通常高得多。"),
        H3("过程 vs 结果监督：一条关键结论"),
        P("推理模型的研究里有一个已经被反复验证的结论值得搬过来："
          "<strong>过程监督在「需要长链推理、且中间步骤可验证」的任务上显著优于结果监督</strong>，"
          "因为结果监督会把「过程全错但答案蒙对」的样本当作正例。"
          "在 agent 评测里，这个结论翻译成："),
        UL([
            "<strong>用结果层做最终评判</strong>（它对齐真实效用），",
            "<strong>用过程层做归因与训练信号</strong>（它提供密集的、定位准确的反馈），",
            "<strong>永远不要用过程分代替结果分作为主指标</strong>——过程好但没做完，产品价值是 0。",
        ]),
    ])),

    # ============================================================== 6
    ("failure-taxonomy", "失败模式分类学：把「失败了」变成「因为什么失败」", "".join([
        P("一份只报成功率的评测，对改进工作的指导价值接近于零。"
          "把失败自动归类，是轨迹层最直接的产出。下面是一份可以直接复用的分类表，"
          "每一类都给出了<strong>可以从日志自动判定的判据</strong>。"),
        TABLE(["失败类别", "自动判据（从 schema 直接算）", "该修什么"], [
            ["<strong>预算耗尽</strong>", "<code>steps == max_steps</code> 且未达终态", "先看是不是循环；不是循环则考虑提高预算或改进规划"],
            ["<strong>循环</strong>", "冗余率 &gt; 阈值，或状态摘要连续 $k$ 步不变", "上下文管理（C33）、加入「已试过什么」的显式记忆"],
            ["<strong>工具误用</strong>", "同一工具连续多次 <code>tool_error</code>，错误码为参数类", "工具描述/schema 写得不清楚（C69 会讲这也是攻击面）"],
            ["<strong>提前放弃</strong>", "步数远低于中位数且未达终态、无错误", "提示里的终止条件太宽松；<strong>常由「优化步数」这个目标诱发</strong>（第 7 节）"],
            ["<strong>幻觉式完成</strong>", "宣称完成但终态检查失败，且无错误记录", "最危险的一类——需要强判分器与不可能任务（模块 01/02）"],
            ["<strong>越权/副作用</strong>", "过程审计日志里出现任务无关的写操作", "权限边界（交给 C69）"],
            ["<strong>真·能力不足</strong>", "以上都不是：动作合法、无循环、预算充足，就是没做对", "这才是真正需要更强模型的部分"],
        ]),
        CALLOUT("intuition", "这张表最重要的价值在最后一行：<strong>在把失败归因为「模型不够强」之前，"
                             "先把前六类排除掉</strong>。真实项目里，前六类经常占到失败总量的一半以上——"
                             "而它们全部是 harness、提示、工具描述、上下文管理的问题，<em>换更强的模型解决不了</em>。"),
        P("分类要做成<strong>互斥且有优先级</strong>的（自上而下第一个命中即分类），"
          "否则一次失败会同时落进三个桶，比例加起来超过 100%，报告就没法读了。"),
    ])),

    # ============================================================== 7
    ("goodhart", "轨迹指标的 Goodhart 陷阱：优化步数会教会 agent 提前放弃", "".join([
        P("最后一节讲一个必须知道的失败案例，它几乎发生在每一个开始用轨迹指标做优化目标的团队身上。"),
        ASCII("""
   目标：把平均步数从 24 降到 12（"让 agent 更高效"）
        │
        ├─ agent 学到的合规解法：更好的规划、更少的冗余调用  ✔ 我们想要的
        │
        └─ agent 学到的更省力解法：**遇到难题早点放弃**       ✘ 我们不想要的
                │
                └─ 平均步数 ↓↓   成功率 ↓   而"平均步数"这个指标看起来非常漂亮
"""),
        P("原因很简单：<strong>失败的轨迹通常更短</strong>（agent 早早宣布做不了），"
          "所以「降低平均步数」的最容易的路径是<em>增加失败率</em>。"
          "任何在<strong>全部轨迹</strong>上计算的效率指标，都有这个方向的病理解。"),
        H3("三条修正规则"),
        OL([
            "<strong>效率指标只在成功轨迹上计算</strong>：报「成功任务的中位步数」而不是「全部任务的平均步数」。"
            "这一条消掉了「靠失败变快」的路径。",
            "<strong>成本永远与成功率成对出现</strong>：单独的成本数字没有意义，"
            "正确的报告形式是<strong>成本-成功率的前沿曲线</strong>（05 模块的主题）。",
            "<strong>把提前放弃单列为一个失败类别</strong>并单独监控（第 6 节的表里已经有了）。"
            "只要这个比例在上升，效率的改善就是假的。",
        ]),
        DUAL(
            "把三条规则合成一句可以直接执行的规范：<strong>「平均步数」这个指标不应该出现在任何报告里。"
            "该出现的是「成功任务的中位步数 + P90」和「提前放弃率」。</strong>",
            "更一般的表述：当一个指标 $M$ 与主目标 $U$ 之间存在<span class=\"term\">选择效应</span>"
            "（$M$ 的取值依赖于 $U$ 的实现与否），在全样本上计算 $M$ 会引入"
            "<span class=\"term\">碰撞偏倚</span>（collider bias）。"
            "$\\mathbb{E}[\\text{steps}]$ 正是这种情况：条件于「成功」这个中间变量的分层统计"
            "$\\mathbb{E}[\\text{steps} \\mid \\text{success}]$ 才是无歧义的量。"
            "<em>同样的道理适用于延迟、token 消耗、工具调用次数——所有效率类指标都要分层报告。</em>",
        ),
        CALLOUT("danger", "这个陷阱不只发生在「拿指标当训练目标」的时候。"
                          "<strong>只要你把某个轨迹指标写进了周报并且团队开始盯着它，"
                          "优化压力就已经存在了</strong>——人也会 Goodhart，不只是模型。"
                          "所以规范应该在指标被引入的那一天就定好，而不是等到发现异常之后。"),
    ])),
    # ============================================================== 8
    ("multi-agent", "多智能体与子 agent：轨迹从链变成树", "".join([
        P("当 agent 会派生子 agent（C34 的编排模式）时，轨迹不再是一条链，而是一棵<strong>树</strong>。"
          "前面七节的指标全部需要重新定义，否则会算出误导性的数字。"),
        ASCII("""
   root agent
     ├─ step 0  plan
     ├─ subagent A ──┬─ step 0  search       ← 子轨迹，有自己的步数/token/错误
     │               ├─ step 1  read_file
     │               └─ (返回摘要，2400 token → 只有摘要进入 root 的上下文)
     ├─ step 1  分析 A 的摘要
     ├─ subagent B ──┬─ step 0  run_tests
     │               └─ step 1  patch
     └─ step 2  汇总并结束

   ✗ 错误算法：只统计 root 的 3 步 → 严重低估成本
   ✓ 正确算法：树的**全部节点**求和 = 真实成本；root 深度 = 真实"决策链长度"
"""),
        TABLE(["指标", "链式定义", "树形下的正确定义", "算错的后果"], [
            ["<strong>成本</strong>", "所有步骤 token 之和", "<strong>整棵树所有节点</strong>的 token 之和", "只算 root 会低估几倍——子 agent 才是 token 大头"],
            ["<strong>步数</strong>", "轨迹长度", "拆成两个数：<strong>root 决策链长度</strong>与<strong>总节点数</strong>", "混成一个数会让「派生一个干了 40 步的子 agent」看起来只花了 1 步"],
            ["<strong>恢复率</strong>", "错误后是否换策略", "分层：子 agent 内部的恢复 vs <strong>root 对「子 agent 失败」的恢复</strong>", "后者才是编排质量的真正指标"],
            ["<strong>冗余率</strong>", "重复的 (tool, args)", "<strong>跨子 agent</strong>的重复调用也要算", "多个子 agent 各查一遍同样的东西，是多智能体最典型的浪费"],
            ["<strong>失败归因</strong>", "七分类", "先定位<strong>是哪个节点失败</strong>，再对该节点做七分类", "把子 agent 的工具误用记成 root 的能力不足"],
        ]),
        CALLOUT("danger", "多智能体轨迹里有一个特有的失败模式，链式结构下不存在："
                          "<strong>信息在层级之间被压缩丢失</strong>。"
                          "子 agent 读了 2400 token 的内容，只把一句摘要返回给 root——"
                          "如果摘要漏掉了关键细节，root 会在<em>看起来信息充分</em>的情况下做出错误决策，"
                          "而日志里每一步都是「成功」。"
                          "<strong>检测手段：给每次子 agent 返回记录「输入 token / 输出 token」的压缩比，"
                          "并把压缩比异常高的节点单独标记出来复核。</strong>"),
        H3("一条容易被忽略的编排质量指标：派生决策的正确率"),
        P("多智能体系统里，root agent 做的最重要的一类决策不是「下一步调什么工具」，"
          "而是<strong>「这件事要不要派给子 agent 去做」</strong>。这个决策做错有两个方向，代价完全不同："
          "<strong>过度派生</strong>——把一个两步就能做完的事包装成一个子 agent，"
          "多付一整份上下文的钱，还多了一次信息压缩的机会；"
          "<strong>派生不足</strong>——把一个需要 40 步探索的子任务塞进 root 的主线，"
          "把 root 的上下文撑爆，后面的决策全部在被污染的上下文里做出（呼应 C33）。"
          "把这两类分别统计出来，比任何总成本数字都更能说明编排设计得好不好："
          "<em>过度派生率高说明派生阈值定得太低，派生不足率高说明 root 没有识别出子任务的边界</em>。"),
        P("判定方式并不需要人工：<strong>过度派生 = 子 agent 的总步数 &le; 2 且没有产生任何写操作</strong>；"
          "<strong>派生不足 = root 主线上出现了连续 $\\ge k$ 步的同类探索动作（读文件、搜索）而未派生</strong>。"
          "两个判据都能从第 2 节的 schema 加上 <code>parent_span_id</code> 后直接算出来。"),
        P("最后一条实践建议：<strong>树形轨迹的日志 schema 只需要在第 2 节的基础上加两个字段</strong>——"
          "<code>parent_span_id</code> 与 <code>depth</code>。"
          "有了它们，上面所有指标都能用一次树遍历算出来；没有它们，你只能得到一堆无法拼回原结构的扁平记录。"
          "<em>这正是「schema 是事前决定」这句话最贵的一次体现。</em>"),
    ])),
]

NB = [
    md("""# 03 · 轨迹级与过程级评测（schema / 六指标 / 循环检测 / LCS / 失败分类 / kappa / Goodhart）

目标：把「它是怎么做到的」从一堆日志，变成**六个可以算、可以比、可以进报告的数字**。

本 notebook 你会亲手实现：
1. **轨迹 schema 与模拟器** —— 生成带工具错误、冗余调用、循环的真实感轨迹
2. **六个轨迹指标** —— 步数分位数、工具精确/召回、无效动作率、冗余率、恢复率
3. **循环检测** —— 精确循环（滑窗哈希）与语义循环（状态摘要不变）
4. **轨迹比较** —— 编辑距离与 LCS；必经动作的子序列断言
5. **失败模式自动分类器** —— 互斥有优先级的七分类
6. **过程标注一致性** —— Cohen's kappa，以及「换个问法就能提高一致性」
7. **Goodhart 演示** —— 优化平均步数如何把成功率优化没了

> 心智模型：**结果层告诉你成没成，轨迹层告诉你钱花在哪、卡在哪、能不能自救。
> 而所有效率指标都必须分层到「成功轨迹」上，否则最省事的优化路径永远是「早点放弃」。**"""),

    md("""## 1 · 轨迹 schema 与模拟器

先把讲解里的 schema 变成代码，并生成一批带真实病灶（工具错误、冗余调用、循环）的轨迹。"""),

    code("""import math, json, hashlib
from collections import Counter, defaultdict
import numpy as np

TOOLS = ['search_orders', 'get_policy', 'update_order', 'send_email', 'list_flights']

def make_step(i, tool, args, status='ok', error_code=None, tokens=(1200, 60)):
    return {'i': i, 'type': 'tool_call', 'tool': tool,
            'args_hash': hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()[:8],
            'status': status, 'error_code': error_code,
            'tokens_in': tokens[0], 'tokens_out': tokens[1],
            'state_digest': None}

def simulate_trajectory(rng, style='healthy', required_tools=('search_orders', 'update_order'),
                        max_steps=30, err_rate=0.15, recover_p=0.85):
    \"\"\"生成一条轨迹。style: healthy | looper | quitter | tool_misuser\"\"\"
    steps, state = [], 0
    i = 0
    done = False
    budget = {'healthy': max_steps, 'looper': max_steps,
              'quitter': int(rng.integers(2, 5)), 'tool_misuser': max_steps}[style]
    while i < budget:
        if style == 'looper' and i >= 3:
            tool, args = 'search_orders', {'q': 'refund'}           # 反复同样的查询
        elif style == 'tool_misuser':
            tool, args = 'update_order', {'id': int(rng.integers(0, 1000))}
        else:
            tool = required_tools[min(i, len(required_tools) - 1)] if i < len(required_tools) \\
                else str(rng.choice(TOOLS))
            args = {'q': int(rng.integers(0, 1000))}
        err = rng.random() < (0.6 if style == 'tool_misuser' else err_rate)
        code = 'E_BAD_ARGS' if style == 'tool_misuser' else \
            str(rng.choice(['E_TIMEOUT', 'E_RATE_LIMIT', 'E_BAD_ARGS']))
        st = make_step(i, tool, args,
                       status='tool_error' if err else 'ok',
                       error_code=code if err else None)
        if not err and style != 'looper':
            state += 1
        st['state_digest'] = f'S{state}'
        steps.append(st)
        i += 1
        if err and rng.random() > recover_p and style == 'healthy':
            break                                                   # 没恢复，直接崩掉
        if style == 'healthy' and state >= 4 and rng.random() < 0.5:
            done = True
            break
    return {'run_id': 'demo', 'task_id': 't0', 'attempt': 0,
            'scaffold_version': 'harness@1.7.2', 'steps': steps,
            'outcome': {'score': int(done), 'reason': None if done else 'incomplete'},
            'max_steps': max_steps, 'style': style}

rng = np.random.default_rng(0)
demo = simulate_trajectory(rng, 'healthy')
print('一条轨迹的前 3 步:')
for s in demo['steps'][:3]:
    print(' ', {k: s[k] for k in ('i', 'tool', 'args_hash', 'status', 'state_digest')})
print(f"\\n总步数 {len(demo['steps'])} | 结果 {demo['outcome']}")
assert all('args_hash' in s and 'status' in s for s in demo['steps'])
print('\\n✅ schema 就位。注意 args_hash 与 status 两个字段——')
print('   没有它们，冗余率与恢复率这两个最有用的指标就永远算不出来。')"""),

    md("""## 2 · 六个轨迹指标"""),

    code("""def steps_quantiles(trajs, successful_only=True):
    \"\"\"效率指标只在成功轨迹上算——这是第 7 节 Goodhart 规则的第一条。\"\"\"
    sel = [t for t in trajs if (t['outcome']['score'] == 1 or not successful_only)]
    if not sel:
        return {'n': 0}
    lens = np.array([len(t['steps']) for t in sel])
    return {'n': len(sel), 'median': float(np.median(lens)),
            'p90': float(np.percentile(lens, 90)), 'mean': float(lens.mean())}

def tool_precision_recall(traj, required_tools):
    used = [s['tool'] for s in traj['steps']]
    used_set, req_set = set(used), set(required_tools)
    prec = len([u for u in used if u in req_set]) / len(used) if used else 0.0
    rec = len(used_set & req_set) / len(req_set) if req_set else 1.0
    return prec, rec

def invalid_action_rate(traj):
    steps = traj['steps']
    return sum(1 for s in steps if s['status'] != 'ok') / len(steps) if steps else 0.0

def redundancy_rate(traj):
    keys = [(s['tool'], s['args_hash']) for s in traj['steps']]
    seen, dup = set(), 0
    for k in keys:
        if k in seen:
            dup += 1
        seen.add(k)
    return dup / len(keys) if keys else 0.0

def recovery_rate(trajs):
    \"\"\"出现过工具错误的轨迹中，最终成功的比例（条件成功率）。\"\"\"
    with_err = [t for t in trajs if any(s['status'] != 'ok' for s in t['steps'])]
    if not with_err:
        return float('nan')
    return float(np.mean([t['outcome']['score'] for t in with_err]))

rng = np.random.default_rng(4)
healthy = [simulate_trajectory(rng, 'healthy') for _ in range(300)]
loopers = [simulate_trajectory(rng, 'looper') for _ in range(80)]
quitters = [simulate_trajectory(rng, 'quitter') for _ in range(80)]

print('成功轨迹的步数分布:', steps_quantiles(healthy))
print('全部轨迹的步数分布:', steps_quantiles(healthy, successful_only=False))
p, r = tool_precision_recall(healthy[0], ('search_orders', 'update_order'))
print(f'\\n单条轨迹 工具精确率 {p:.2f} 召回率 {r:.2f}')
print(f'无效动作率(healthy 均值) {np.mean([invalid_action_rate(t) for t in healthy]):.1%}')
print(f'冗余率 healthy {np.mean([redundancy_rate(t) for t in healthy]):.1%} '
      f'| looper {np.mean([redundancy_rate(t) for t in loopers]):.1%}')
assert np.mean([redundancy_rate(t) for t in loopers]) > 3 * np.mean([redundancy_rate(t) for t in healthy])
print('\\n✅ 冗余率把 looper 和 healthy 拉开了三倍以上——')
print('   而这两组的「成功率」可能完全一样（都失败），结果层完全看不出区别。')"""),

    code("""# 条件成功率：有错误 vs 无错误
def conditional_success(trajs):
    with_err = [t['outcome']['score'] for t in trajs if any(s['status'] != 'ok' for s in t['steps'])]
    no_err = [t['outcome']['score'] for t in trajs if all(s['status'] == 'ok' for s in t['steps'])]
    return (float(np.mean(with_err)) if with_err else float('nan'),
            float(np.mean(no_err)) if no_err else float('nan'))

we, ne = conditional_success(healthy)
overall = float(np.mean([t['outcome']['score'] for t in healthy]))
print(f'总成功率        {overall:.1%}')
print(f'  出过错的轨迹  {we:.1%}   ← 这个数字才预测得了线上表现')
print(f'  没出错的轨迹  {ne:.1%}')
assert ne > we, '出过错的轨迹成功率必然更低'
gap = ne - we
print(f'\\n落差 {gap:.1%}。线上环境的错误率通常高于离线环境，')
print('所以线上成功率会向「出过错的轨迹」那一档滑落——这就是 demo 与产品之间的鸿沟。')"""),

    md("""## 3 · 循环检测：精确循环与语义循环"""),

    code("""def detect_exact_loop(traj, window=3, repeats=2):
    \"\"\"精确循环：长度为 window 的动作序列连续重复 repeats 次以上。\"\"\"
    keys = [(s['tool'], s['args_hash']) for s in traj['steps']]
    n = len(keys)
    for start in range(n - window * repeats + 1):
        block = keys[start:start + window]
        if all(keys[start + w * window:start + (w + 1) * window] == block for w in range(repeats)):
            return True, start
    return False, None

def detect_semantic_loop(traj, k=4):
    \"\"\"语义循环：状态摘要连续 k 步没有变化。\"\"\"
    digs = [s['state_digest'] for s in traj['steps']]
    run = 1
    for a, b in zip(digs, digs[1:]):
        run = run + 1 if a == b else 1
        if run >= k:
            return True
    return False

n_loop_exact = sum(detect_exact_loop(t)[0] for t in loopers)
n_health_exact = sum(detect_exact_loop(t)[0] for t in healthy)
n_loop_sem = sum(detect_semantic_loop(t) for t in loopers)
n_health_sem = sum(detect_semantic_loop(t) for t in healthy)
print(f'精确循环检出  looper {n_loop_exact}/{len(loopers)} | healthy {n_health_exact}/{len(healthy)}')
print(f'语义循环检出  looper {n_loop_sem}/{len(loopers)} | healthy {n_health_sem}/{len(healthy)}')
assert n_loop_exact / len(loopers) > 0.8
assert n_health_exact / len(healthy) < 0.2
print('\\n✅ 检出率 >80%、误报率 <20%。把它接到预算控制上：检出即终止，')
print('   省下的预算拿去跑别的任务。注意被终止的轨迹要单独标记，不能简单记成失败。')"""),

    md("""## 4 · 轨迹比较：编辑距离、LCS、必经动作断言"""),

    code("""def edit_distance(a, b):
    n, m = len(a), len(b)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev = cur
    return dp[m]

def lcs_len(a, b):
    n, m = len(a), len(b)
    dp = [0] * (m + 1)
    for i in range(1, n + 1):
        prev = 0
        for j in range(1, m + 1):
            cur = dp[j]
            dp[j] = prev + 1 if a[i - 1] == b[j - 1] else max(dp[j], dp[j - 1])
            prev = cur
    return dp[m]

def is_subsequence(required, actual):
    \"\"\"必经动作断言：required 必须作为子序列出现在 actual 中。\"\"\"
    it = iter(actual)
    return all(any(x == y for y in it) for x in required)

REF = ['get_policy', 'search_orders', 'update_order', 'send_email']
A   = ['get_policy', 'search_orders', 'update_order', 'send_email']              # 完全一致
B   = ['get_policy', 'list_flights', 'search_orders', 'search_orders',
       'update_order', 'send_email']                                            # 多绕了两步
C   = ['search_orders', 'update_order', 'send_email']                            # 漏了必经动作

for name, seq in [('A 完全一致', A), ('B 多绕两步', B), ('C 漏了 get_policy', C)]:
    print(f'{name:<18} 编辑距离 {edit_distance(REF, seq)} | LCS {lcs_len(REF, seq)} | '
          f'必经动作断言 {is_subsequence(["get_policy", "update_order"], seq)}')

assert edit_distance(REF, A) == 0
assert edit_distance(REF, B) > 0 and is_subsequence(['get_policy', 'update_order'], B)
assert not is_subsequence(['get_policy', 'update_order'], C)
print('\\n✅ 关键对比在 B 这一行：编辑距离说它「偏离了」，必经动作断言说它「合规」。')
print('   B 只是多做了两步探索——把编辑距离当主指标，就是在惩罚探索。断言才是对的工具。')"""),

    md("""## 5 · 失败模式自动分类器（互斥、有优先级）"""),

    code("""def classify_failure(traj, median_steps, redundancy_thresh=0.35):
    \"\"\"自上而下第一个命中即分类——必须互斥，否则比例加起来会超过 100%。\"\"\"
    if traj['outcome']['score'] == 1:
        return 'success'
    steps = traj['steps']
    n = len(steps)
    err_codes = [s['error_code'] for s in steps if s['status'] != 'ok']
    if detect_exact_loop(traj)[0] or redundancy_rate(traj) > redundancy_thresh:
        return 'loop'
    if len(err_codes) >= 3 and len(set(err_codes)) == 1:
        return 'tool_misuse'
    if n >= traj['max_steps']:
        return 'budget_exhausted'
    if n < 0.5 * median_steps and not err_codes:
        return 'early_quit'
    if not err_codes:
        return 'hallucinated_completion'
    return 'genuine_incapability'

misusers = [simulate_trajectory(rng, 'tool_misuser') for _ in range(80)]
ALL = healthy + loopers + quitters + misusers
med = np.median([len(t['steps']) for t in ALL])

cnt = Counter(classify_failure(t, med) for t in ALL)
total_fail = sum(v for k, v in cnt.items() if k != 'success')
print(f'共 {len(ALL)} 条轨迹，失败 {total_fail} 条。失败原因分解:')
for k, v in cnt.most_common():
    if k == 'success':
        continue
    print(f'  {k:<26} {v:>4} ({v/total_fail:5.1%})')

assert sum(cnt.values()) == len(ALL), '七分类必须互斥且穷尽'
assert cnt['loop'] > 0 and cnt['early_quit'] > 0
non_capability = 1 - cnt['genuine_incapability'] / total_fail
print(f'\\n「不是模型不够强」的失败占比: {non_capability:.0%}')
print('✅ 这个数字是本模块最有行动价值的产出——')
print('   它告诉你：在换更强的模型之前，还有这么大一块是 harness / 提示 / 工具描述的问题。')"""),

    md("""## 6 · 过程标注一致性：Cohen's kappa 与「换个问法」"""),

    code("""def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a.tolist()) | set(b.tolist()))
    po = float((a == b).mean())
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if abs(1 - pe) > 1e-12 else float('nan')

rng = np.random.default_rng(19)
N = 400
# 问法一「这一步好不好」：主观，两个标注员各有偏好
truth = rng.integers(0, 3, size=N)
ann1_vague = np.where(rng.random(N) < 0.55, truth, rng.integers(0, 3, size=N))
ann2_vague = np.where(rng.random(N) < 0.55, truth, rng.integers(0, 3, size=N))
# 问法二「这一步是否让任务离目标更近」：二元、可判定，一致性显著提高
truth_b = (truth > 0).astype(int)
ann1_sharp = np.where(rng.random(N) < 0.90, truth_b, 1 - truth_b)
ann2_sharp = np.where(rng.random(N) < 0.90, truth_b, 1 - truth_b)

k_vague = cohen_kappa(ann1_vague, ann2_vague)
k_sharp = cohen_kappa(ann1_sharp, ann2_sharp)
print(f'问法一「这一步好不好」（三档）  kappa = {k_vague:.3f}')
print(f'问法二「是否离目标更近」（二元） kappa = {k_sharp:.3f}')
assert k_sharp > k_vague + 0.2
print('\\n判读标准（沿用 C10-02）：<0.4 差 | 0.4-0.6 中等 | 0.6-0.8 良好 | >0.8 优秀')
print(f'✅ 只是换了个问法，kappa 从 {k_vague:.2f} 提到 {k_sharp:.2f}——')
print('   kappa 低时，第一反应应该是「标注问题问得不好」，而不是「再培训标注员」。')"""),

    md("""## 7 · Goodhart 演示：优化平均步数，把成功率优化没了"""),

    code("""def agent_with_patience(patience, n_tasks=800, seed=0):
    \"\"\"patience 越大越不容易放弃：每一步继续尝试的概率与 patience 相关。
    返回 (成功率, 全部轨迹平均步数, 成功轨迹中位步数, 提前放弃率)。\"\"\"
    rng = np.random.default_rng(seed)
    steps_all, succ, quits = [], [], 0
    for _ in range(n_tasks):
        need = int(rng.integers(4, 20))            # 这个任务真正需要的步数
        k = 0
        while k < need and rng.random() < patience:
            k += 1
        ok = (k >= need)
        if not ok:
            quits += 1
        steps_all.append(k + 1)
        succ.append(float(ok))
    steps_all = np.array(steps_all)
    succ = np.array(succ)
    med_succ = float(np.median(steps_all[succ == 1])) if succ.sum() else float('nan')
    return float(succ.mean()), float(steps_all.mean()), med_succ, quits / n_tasks

print(f"{'patience':>9}{'成功率':>10}{'全体平均步数':>14}{'成功轨迹中位步数':>18}{'提前放弃率':>12}")
rows = []
for pat in [0.99, 0.95, 0.90, 0.80, 0.70]:
    r = agent_with_patience(pat, seed=3)
    rows.append((pat,) + r)
    print(f'{pat:>9.2f}{r[0]:>10.1%}{r[1]:>14.2f}{r[2]:>18.1f}{r[3]:>12.1%}')

# 「优化平均步数」会选中最差的那一行
best_by_mean_steps = min(rows, key=lambda r: r[2])
best_by_success = max(rows, key=lambda r: r[1])
print(f'\\n按「全体平均步数最小」选出的配置: patience={best_by_mean_steps[0]:.2f} '
      f'(成功率仅 {best_by_mean_steps[1]:.1%})')
print(f'按「成功率最大」选出的配置:       patience={best_by_success[0]:.2f} '
      f'(成功率 {best_by_success[1]:.1%})')
assert best_by_mean_steps[0] != best_by_success[0]
assert best_by_mean_steps[1] < best_by_success[1]
print('\\n✅ Goodhart 现场：优化「平均步数」这个指标，选出的是成功率最低的配置。')
print('   修正：效率只在成功轨迹上算 + 成本必须与成功率成对报告 + 单独监控提前放弃率。')"""),

    md("""## ✏️ 练习 1：加权无效动作率（区分首次探索与重复犯错）

实现 `weighted_invalid_rate(traj, repeat_penalty=3.0)`：
无效动作里，**第一次**出现某个 `(tool, error_code)` 组合权重记 1.0，
**之后每次重复**记 `repeat_penalty`。返回 `加权无效动作数 / 总步数`。"""),

    code("""def weighted_invalid_rate(traj, repeat_penalty=3.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
def mk(tool, status, code):
    return {'tool': tool, 'status': status, 'error_code': code}

t1 = {'steps': [mk('a', 'ok', None), mk('a', 'tool_error', 'E1'), mk('a', 'tool_error', 'E1')]}
# 一次首犯(1.0) + 一次重复(3.0) = 4.0 / 3 步
assert abs(weighted_invalid_rate(t1) - 4.0 / 3) < 1e-12
t2 = {'steps': [mk('a', 'tool_error', 'E1'), mk('b', 'tool_error', 'E2')]}
assert abs(weighted_invalid_rate(t2) - 1.0) < 1e-12       # 两次都是首犯
t3 = {'steps': [mk('a', 'ok', None), mk('b', 'ok', None)]}
assert weighted_invalid_rate(t3) == 0.0
print(f'两次同样的错: {weighted_invalid_rate(t1):.3f} | 两个不同的错: {weighted_invalid_rate(t2):.3f}')
print('✅ 练习 1 通过：探索性试错和「反复撞同一堵墙」不该同权——')
print('   前者是 agent 在获取信息，后者是它没有从反馈里学到东西。')"""),

    md("""## ✏️ 练习 2：恢复事件级的恢复率

实现 `event_recovery_rate(traj)`：以**事件**而非轨迹为单位。
对轨迹中每一次 `status != 'ok'` 的步骤，看它的<strong>下一步</strong>：
若下一步 `status == 'ok'` 且 `tool` 或 `args_hash` 与出错那步不同，记为一次成功恢复。
返回 `(成功恢复数, 错误事件总数, 恢复率)`；无错误时恢复率返回 `float('nan')`。"""),

    code("""def event_recovery_rate(traj):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
def mk2(tool, ah, status):
    return {'tool': tool, 'args_hash': ah, 'status': status}

good = {'steps': [mk2('a', 'h1', 'tool_error'), mk2('b', 'h2', 'ok')]}
assert event_recovery_rate(good) == (1, 1, 1.0)
stuck = {'steps': [mk2('a', 'h1', 'tool_error'), mk2('a', 'h1', 'ok')]}   # 换都没换，不算恢复
assert event_recovery_rate(stuck) == (0, 1, 0.0)
clean = {'steps': [mk2('a', 'h1', 'ok')]}
n_rec, n_err, rate = event_recovery_rate(clean)
assert (n_rec, n_err) == (0, 0) and math.isnan(rate)
last_step_err = {'steps': [mk2('a', 'h1', 'ok'), mk2('b', 'h2', 'tool_error')]}
assert event_recovery_rate(last_step_err) == (0, 1, 0.0)   # 出错就没有下一步了
print('全部四种情形通过：正常恢复 / 原地重试 / 无错误 / 末步出错')
print('✅ 练习 2 通过：事件级恢复率比轨迹级更灵敏——')
print('   一条轨迹出了五次错恢复了四次，轨迹级只能记「成功」或「失败」一个 bit。')"""),

    md("""## ✏️ 练习 3：成本-成功率的分层报告

实现 `stratified_efficiency(trajs)`：返回一个字典，包含
`success_rate`、`median_steps_success`（成功轨迹的中位步数）、
`p90_steps_success`、`early_quit_rate`（未成功且步数 < 全体中位数一半的比例）。
这四个数字就是第 7 节三条修正规则的可执行版本。"""),

    code("""def stratified_efficiency(trajs):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
rep = stratified_efficiency(ALL)
assert set(rep) == {'success_rate', 'median_steps_success', 'p90_steps_success', 'early_quit_rate'}
assert 0 <= rep['success_rate'] <= 1 and 0 <= rep['early_quit_rate'] <= 1
assert rep['p90_steps_success'] >= rep['median_steps_success']
for k, v in rep.items():
    print(f'  {k:<24} {v:.3f}')
print('✅ 练习 3 通过：这四行就是可以直接贴进报告的效率部分——')
print('   注意里面没有「平均步数」，这是刻意的。')"""),

    md("""## ✏️ 练习 4：过程分与结果分的相关性

实现 `process_outcome_corr(process_scores, outcomes)`：返回皮尔逊相关系数
（纯 numpy，不用 scipy）。用它验证「过程分高但结果失败」的样本确实存在，
即相关系数显著大于 0 但远小于 1。"""),

    code("""def process_outcome_corr(process_scores, outcomes):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
x = np.array([1.0, 2.0, 3.0, 4.0])
assert abs(process_outcome_corr(x, x) - 1.0) < 1e-9
assert abs(process_outcome_corr(x, -x) + 1.0) < 1e-9

rng = np.random.default_rng(31)
n = 500
proc = rng.uniform(0, 1, n)
out = (rng.random(n) < np.clip(proc * 0.8 + 0.05, 0, 1)).astype(float)
r = process_outcome_corr(proc, out)
print(f'过程分与结果分的相关系数 r = {r:.3f}')
assert 0.2 < r < 0.9
good_proc_fail = ((proc > 0.8) & (out == 0)).sum()
print(f'过程分 >0.8 但最终失败的样本: {good_proc_fail} 条')
assert good_proc_fail > 0
print('✅ 练习 4 通过：相关但远非等同——这就是「过程分不能替代结果分作主指标」的实证形式。')
print('   过程好但没做完，产品价值是 0；而只看结果分，你不知道它差在哪一步。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def weighted_invalid_rate(traj, repeat_penalty=3.0):
    steps = traj['steps']
    if not steps:
        return 0.0
    seen, total = set(), 0.0
    for s in steps:
        if s['status'] != 'ok':
            key = (s['tool'], s['error_code'])
            total += repeat_penalty if key in seen else 1.0
            seen.add(key)
    return total / len(steps)"""),

    code("""# 练习 2 参考答案
def event_recovery_rate(traj):
    steps = traj['steps']
    n_err = n_rec = 0
    for i, s in enumerate(steps):
        if s['status'] == 'ok':
            continue
        n_err += 1
        if i + 1 < len(steps):
            nxt = steps[i + 1]
            changed = (nxt['tool'] != s['tool']) or (nxt['args_hash'] != s['args_hash'])
            if nxt['status'] == 'ok' and changed:
                n_rec += 1
    rate = n_rec / n_err if n_err else float('nan')
    return (n_rec, n_err, rate)"""),

    code("""# 练习 3 参考答案
def stratified_efficiency(trajs):
    lens = np.array([len(t['steps']) for t in trajs], dtype=float)
    succ = np.array([t['outcome']['score'] for t in trajs], dtype=float)
    med_all = float(np.median(lens))
    s_lens = lens[succ == 1]
    return {
        'success_rate': float(succ.mean()),
        'median_steps_success': float(np.median(s_lens)) if s_lens.size else float('nan'),
        'p90_steps_success': float(np.percentile(s_lens, 90)) if s_lens.size else float('nan'),
        'early_quit_rate': float(((succ == 0) & (lens < 0.5 * med_all)).mean()),
    }"""),

    code("""# 练习 4 参考答案
def process_outcome_corr(process_scores, outcomes):
    x = np.asarray(process_scores, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    xc, yc = x - x.mean(), y - y.mean()
    denom = math.sqrt(float((xc ** 2).sum()) * float((yc ** 2).sum()))
    return float((xc * yc).sum() / denom) if denom else float('nan')"""),

    md("""---
## 🧪 真实工程胶囊：把轨迹分析接到真实 agent 上"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 用 OpenTelemetry GenAI 语义约定记轨迹（别自造字段名）
# ══════════════════════════════════════════════════════════════════
from opentelemetry import trace
tracer = trace.get_tracer("agent.eval")

with tracer.start_as_current_span("agent.run") as run_span:
    run_span.set_attribute("gen_ai.system", "anthropic")
    run_span.set_attribute("gen_ai.request.model", "claude-sonnet-5")
    run_span.set_attribute("eval.task_id", task_id)
    run_span.set_attribute("eval.attempt", attempt)          # ← pass^k 需要
    run_span.set_attribute("eval.scaffold_version", SCAFFOLD_VERSION)
    for i, step in enumerate(agent_loop()):
        with tracer.start_as_current_span("gen_ai.tool.execute") as sp:
            sp.set_attribute("gen_ai.tool.name", step.tool)
            sp.set_attribute("eval.args_hash", step.args_hash)   # ← 冗余率需要
            sp.set_attribute("eval.status", step.status)         # ← 恢复率需要
            sp.set_attribute("gen_ai.usage.input_tokens", step.tokens_in)
            sp.set_attribute("gen_ai.usage.output_tokens", step.tokens_out)
# 用现成的 trace 查看器（Jaeger / Grafana Tempo / Phoenix / LangSmith）直接看，
# 不需要自己写 UI。这是沿用标准字段名的唯一理由，也是足够的理由。

# ══════════════════════════════════════════════════════════════════
# B. 主动注入错误，测恢复力（离线评测最容易漏的一步）
# ══════════════════════════════════════════════════════════════════
class FlakyTool:
    # 按概率注入真实感的失败：超时、限流、参数错误、空结果
    def __init__(self, inner, p=0.15, seed=0):
        self.inner, self.p, self.rng = inner, p, random.Random(seed)
    def __call__(self, **kw):
        if self.rng.random() < self.p:
            raise random.choice([TimeoutError("upstream timeout"),
                                 RuntimeError("429 rate limited"),
                                 ValueError("invalid argument: order_id")])
        return self.inner(**kw)
# 报告规范：注入率 0% / 10% / 25% 三档各跑一遍，报告三条成功率曲线。
# 曲线的斜率就是「恢复力」，比任何单点数字都有信息量。

# ══════════════════════════════════════════════════════════════════
# C. 失败分类的落地：从 trace 直接产出周报
# ══════════════════════════════════════════════════════════════════
# 每周跑一次，输出：
#   1) 失败分解饼图（七类，互斥）
#   2) 「非能力问题」占比的时间序列   ← 这条曲线在下降，说明 harness 在变好
#   3) 提前放弃率的时间序列          ← 这条在上升，说明有人在优化步数，要拦
#   4) 出错轨迹 vs 无错轨迹的条件成功率落差 ← 这条预测线上表现
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 三件结果层看不见的事 | 钱花在哪、卡在哪、能不能自救 | 归因与改进 |
| schema 是事前决定 | 没记 `args_hash` / `status` / `attempt`，指标永远算不出来 | 写第一个 agent 之前 |
| 六个指标 | 步数分位数、工具精确/召回、无效动作、冗余、恢复 | 周报固定项 |
| 轨迹比较做断言不做打分 | 必经动作用 LCS 子序列；编辑距离只做人工复核分诊 | 任务设计 |
| 失败分类学 | 归因为「模型不够强」之前，先排除前六类 | 决定下一步修什么 |
| 过程标注 kappa | kappa 低先怀疑问法，不是标注员 | 过程级评测 |
| Goodhart | 「平均步数」不该出现在任何报告里 | 指标引入的第一天 |

下一模块：**04 · 可靠性与统计**——pass@k 与 pass^k、方差从哪来、
两个 agent 差 3 个点到底算不算差、以及要跑几个 seed 才够。""")
]
