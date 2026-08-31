# -*- coding: utf-8 -*-
"""C68 模块 02 · Runner 工程（并发、重试、缓存、预算、续跑）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（spec 与指纹）；"
                 "知道「限流」「指数退避」两个词即可，实现全部从零写"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_runner.ipynb'
                       '（缓存键设计与「改了 prompt 却读到旧结果」的复现 / '
                       '重试与指数退避 + 抖动 / 失败分类与两个分母 / '
                       '令牌桶限流与并发上限 / 预算熔断 / 重试引入的选择偏倚 / 断点续跑）'),
    ("核心参考", "Google SRE Book（重试、退避、抖动、过载处理）· "
                 "Nygard, <em>Release It!</em>（熔断器模式）· "
                 "inspect_ai 的 <code>--max-connections</code> 与 retry 语义 · "
                 "本课程 C66 模块 05（并发是 harness 的一部分）· C24（推理服务与限流）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("cache-key", "缓存：本课最贵的一个 bug 就藏在这里", "".join([
        P("先讲缓存，因为它是 runner 里<strong>收益最大、也最容易出错</strong>的一块。"
          "收益很直接：重跑时省 90% 以上的调用成本。"
          "而错误的形态是模块 00 反模式清单里的第四条——<strong>它不会报错。</strong>"),
        ASCII("""
   ❌ 缓存键 = hash(输入文本)
   ┌──────────────────────────────────────────────────────────┐
   │ 第一次跑:  prompt_v1 + 输入 X  →  调用模型  →  存进缓存    │
   │ 改了 prompt 的一句措辞                                     │
   │ 第二次跑:  prompt_v2 + 输入 X  →  **缓存命中** → 返回旧结果 │
   │                                                          │
   │ 症状: 「我明明改了 prompt，分数却一点没变」                 │
   │ 误读: 「这个改动没有效果」  ← 实际上它根本没被执行           │
   └──────────────────────────────────────────────────────────┘

   ✓ 缓存键 = hash(输入内容) + 完整配置指纹
     prompt 变了 → 指纹变了 → 缓存不命中 → 真的重新调用
"""),
        MATH(r"\text{cache\_key} = H\big(\underbrace{\text{input}}_{\text{内容}} \;\|\; \underbrace{\text{fp}(\text{spec}_{\text{exec}})}_{\text{配置}}\big)"),
        TABLE(["必须进缓存键的东西", "为什么", "漏了会怎样"], [
            ["<strong>输入内容</strong>", "显然", "所有样本共用一个结果"],
            ["<strong>模型 ID 与快照</strong>", "换模型就是换实验", "拿 A 的结果当 B 的"],
            ["<strong>采样参数</strong>（temperature/top_p/seed/max_tokens）", "改了会改变输出分布", "温度扫描全部读到同一个结果"],
            ["<strong>prompt / 模板的哈希</strong>", "<strong>最常被漏的一个</strong>", "改了 prompt 分数不动，被误读成「改动无效」"],
            ["<strong>工具集与 schema</strong>（agent 场景）", "工具变了行为就变了", "同上"],
            ["<strong>缓存格式版本</strong>", "存储结构变更时要整体失效", "新代码读到无法解析的旧记录"],
        ]),
        CALLOUT("danger", "有一条纪律可以一劳永逸地避免这类 bug："
                          "<strong>缓存键直接用模块 01 的 <code>exec_fp</code>（执行指纹），"
                          "而不是手写一个「要包含哪些字段」的列表。</strong>"
                          "<em>手写列表必然会漏——因为新加一个配置项时，没有任何机制提醒你去更新那个列表。</em>"
                          "而 exec_fp 是整个执行配置的哈希，加了字段它自动就变了。"),
        H3("什么时候<strong>不该</strong>缓存"),
        UL([
            "<strong>估计方差、算置信区间、跑 pass^k 时必须关缓存</strong>——"
            "开着缓存重跑两次得到同样的分数，说明的不是「结果可复现」，而是「你根本没有重跑」"
            "（这条与 C66 模块 05 第 8 节完全一致）；",
            "<strong>非确定性判分器</strong>（LLM judge）的缓存要更谨慎："
            "它可以缓存，但缓存键里必须包含 judge 的完整指纹，"
            "且<em>做 swap 探针时两次调用的键必须不同</em>（否则第二次直接命中第一次的结果，探针失效）；",
            "<strong>调试期</strong>——加一个 <code>--no-cache</code> 开关，"
            "并让它<em>显式打印「缓存已禁用」</em>，避免自己被自己骗。",
        ]),
    ])),

    # ============================================================== 2
    ("failures", "失败分类：静默跳过是最常见的数据污染", "".join([
        P("模块 00 讲过「失败样本必须计入分母」。这一节讲得更细："
          "<strong>失败不是一类，而是至少五类，它们该被区别对待。</strong>"),
        TABLE(["失败类型", "典型来源", "该不该重试", "该不该计入分母", "该怎么记"], [
            ["<strong>瞬时基础设施错误</strong>", "网络抖动、502、连接重置", "<strong>该</strong>", "重试成功后按成功计", "记重试次数"],
            ["<strong>限流</strong>（429）", "并发太高", "<strong>该</strong>（退避后）", "同上", "单独统计，用于调并发"],
            ["<strong>超时</strong>", "模型慢、任务难", "<strong>看情况</strong>", "<strong>计入，且算失败</strong>", "超时是一种能力信号，不是纯粹的基础设施问题"],
            ["<strong>模型拒答 / 内容过滤</strong>", "安全策略触发", "<strong>不该</strong>", "<strong>计入，且单独统计</strong>", "拒答率是一个独立指标（C67-05）"],
            ["<strong>输出格式错误</strong>", "没按 schema 返回", "可以重试 1 次", "<strong>计入</strong>", "解析失败率必须报告（C67-01）"],
            ["<strong>判分器崩溃</strong>", "validator 有 bug", "不该（先修 bug）", "<strong>标记为 <code>scorer_error</code>，从主指标里排除但要显式报告</strong>", "这是唯一可以排除的一类"],
        ]),
        DUAL(
            "为什么超时要算失败而不是算基础设施错误？<strong>因为超时是混合的：</strong>"
            "一部分来自基础设施（服务器慢），一部分来自任务本身（这道题模型想太久）。"
            "<em>而后者是真实的能力信号</em>——一个总是超时的 agent，在产品里就是不可用的。"
            "<strong>把超时算成「基础设施错误并重试到成功」，等于系统性地掩盖了这个信号。</strong>",
            "更精确的处理是<strong>把超时按原因拆开</strong>："
            "如果同一批任务在低并发下不超时、高并发下超时，那是基础设施；"
            "如果在任何并发下都超时，那是任务/模型。"
            "<em>C66 模块 05 的「并发敏感性检查」正是用来做这个区分的</em>——"
            "分数对并发不敏感，才说明超时阈值有足够余量、超时反映的是真实能力。",
        ),
        CALLOUT("warn", "最后一行的 <code>scorer_error</code> 是唯一可以从主指标排除的失败类型，"
                        "但<strong>它必须被显式报告，而且它的比例应该趋近于零</strong>。"
                        "<em>如果 5% 的样本因为判分器崩溃被排除，那么这份报告的可信度就取决于"
                        "「崩溃是不是随机发生的」——而它通常不是</em>"
                        "（判分器更容易在奇怪的输出上崩溃，而奇怪的输出更可能是失败的）。"),
    ])),

    # ============================================================== 3
    ("retry", "重试：退避、抖动，以及它悄悄引入的偏倚", "".join([
        P("重试是必需的，但它有两个层面的问题：<strong>工程层面</strong>（怎么退避才不打垮上游）"
          "和<strong>统计层面</strong>（重试会不会污染结果）。后者更少被讨论，但更重要。"),
        H3("工程层面：指数退避 + 抖动"),
        MATH(r"\text{delay}_k = \min\big(\text{base} \cdot 2^{k},\ \text{cap}\big) \cdot U(0.5,\ 1.5)"),
        P("<strong>抖动（jitter）那一项不是可选的。</strong>"
          "没有抖动时，一批同时被限流的请求会在同一时刻同时重试，"
          "形成<span class=\"term\">惊群</span>（thundering herd），把上游再打垮一次。"
          "<em>乘一个 $U(0.5, 1.5)$ 的随机因子，就能把重试时刻摊开。</em>"),
        H3("统计层面：重试引入的选择偏倚"),
        CALLOUT("danger", "<strong>这是本模块最重要的一条：重试的触发条件必须与「结果好坏」无关。</strong>"
                          "如果你对失败的样本重试、对成功的样本不重试，"
                          "就引入了一个<em>只朝一个方向的选择效应</em>——"
                          "<strong>「重试到成功为止」是评测里最隐蔽的一种作弊，而且很多时候是无意的。</strong>"
                          "<em>C66 模块 02 第 8 节的三级复核流水线里已经出现过同一条纪律。</em>"),
        TABLE(["重试触发条件", "有没有偏倚", "为什么"], [
            ["HTTP 5xx / 连接错误", "<strong>没有</strong>", "与模型输出的内容无关"],
            ["429 限流", "<strong>没有</strong>", "同上"],
            ["输出解析失败", "<strong>有轻微偏倚</strong>", "难题更容易输出不合规格式（C67-01）；<em>可以重试，但要记录并报告重试率</em>"],
            ["<strong>判分为 0</strong>", "<strong>严重偏倚</strong>", "这就是「重试到成功为止」——绝对禁止"],
            ["<strong>输出「看起来不对」</strong>", "<strong>严重偏倚</strong>", "同上，只是更隐蔽"],
        ]),
        P("一条可执行的规则：<strong>重试的判断函数只能看异常类型与 HTTP 状态码，"
          "不能看模型输出的内容，更不能看判分结果。</strong>"
          "在代码结构上，这意味着<em>重试逻辑必须在判分之前完成</em>——"
          "拿到判分结果之后就不许再重试了。"),
    ])),

    # ============================================================== 4
    ("concurrency", "并发与限流：为什么并发是 harness 的一部分", "".join([
        P("C66 模块 05 的复现清单第 7 条说「并发度必须写进报告」。这一节讲清楚为什么。"),
        ASCII("""
   并发度 ↑
     │
     ├─ 吞吐 ↑            （想要的）
     ├─ 单请求延迟 ↑      （上游排队）
     ├─ 超时率 ↑          ← **分数会变**
     ├─ 429 率 ↑          ← 重试变多，成本变高
     └─ 容器/CPU 争抢 ↑   ← 代码类任务里测试跑得更慢，更容易超时

   结论：**并发度是一个会影响分数的自变量**，不是一个纯粹的性能旋钮。
"""),
        H3("并发敏感性检查：一个必做的健康检查"),
        P("做法很简单：<strong>在 1 / 4 / 8 / 16 四个并发度上各跑一遍 smoke 子集，看分数是否稳定。</strong>"),
        TABLE(["现象", "说明", "该做什么"], [
            ["分数对并发不敏感", "超时阈值有足够余量", "✅ 正常，记录并发度即可"],
            ["<strong>高并发下分数下降</strong>", "超时阈值设得太紧，高并发下大量任务撞上超时", "<strong>放宽超时或降低并发</strong>；不要接受这个分数"],
            ["高并发下 429 率暴涨", "超过了上游配额", "上限流器（下一节）"],
            ["低并发下也不稳定", "不是并发的问题", "回去查随机源（模块 00 第 3 节）"],
        ]),
        H3("限流：令牌桶"),
        P("直接用固定并发数是不够的，因为上游的限额通常是<strong>按速率</strong>（每分钟多少请求 / 多少 token）而不是按并发数。"
          "标准做法是<span class=\"term\">令牌桶</span>："),
        CODE("""桶容量 = burst（允许的突发量）
补充速率 = rate（每秒补多少个令牌）

请求前: 取 1 个令牌；没有就等到有为止
        （token 计费的场景：按预估 token 数取多个令牌）

好处: 平时允许突发，长期严格遵守平均速率——正好匹配多数 API 的限额语义"""),
        CALLOUT("intuition", "限流器和并发上限<strong>要同时存在</strong>，它们管的不是一件事："
                             "<em>并发上限管的是「同时有多少请求在飞」（保护内存与连接数），"
                             "限流器管的是「单位时间发出多少请求」（遵守上游配额）</em>。"
                             "<strong>只有并发上限没有限流器，会在请求快速返回时超速；"
                             "只有限流器没有并发上限，会在请求变慢时堆积。</strong>"),
    ])),

    # ============================================================== 5
    ("budget", "预算控制：熔断、上限、以及「先跑一小批」", "".join([
        P("评测可以很贵。一个没有预算保护的 runner，"
          "有可能在你去吃午饭的时候花掉一个月的额度——"
          "<strong>而这类事故通常不是因为写错了循环，而是因为某个环节开始疯狂重试。</strong>"),
        TABLE(["保护机制", "触发条件", "动作", "为什么需要"], [
            ["<strong>硬性总预算</strong>", "累计成本 &gt; 上限", "<strong>立即停止</strong>并保存已有结果", "最后一道防线"],
            ["<strong>单任务上限</strong>", "单条任务成本 &gt; 上限", "终止该任务，标记 <code>budget_exceeded</code>", "防止一条失控的轨迹吃掉全部预算（呼应 C66-03 的循环检测）"],
            ["<strong>错误率熔断</strong>", "最近 N 次调用的失败率 &gt; 阈值", "<strong>暂停并告警</strong>", "上游挂了的时候不要继续烧钱重试"],
            ["<strong>预检（dry run）</strong>", "正式跑之前", "跑 5–10 条，外推总成本并<strong>要求确认</strong>", "<strong>最有效的一个</strong>：把「事故」变成「预估」"],
        ]),
        CALLOUT("intuition", "第四条值得强调，因为它便宜到几乎没有理由不做："
                             "<strong>先跑 10 条，用实测的单条成本 × 总任务数，"
                             "打印出「本次运行预计花费 X」，然后再继续。</strong>"
                             "<em>这一步能抓住绝大多数「配置写错导致成本爆炸」的情况</em>——"
                             "比如不小心把 max_tokens 写成了 100000，或者 attempts 写成了 50。"),
        H3("熔断器的三个状态"),
        P("熔断器（circuit breaker）不是简单的「失败就停」，它有三个状态，"
          "这个设计是为了<strong>能自动恢复</strong>："),
        UL([
            "<strong>closed</strong>（正常）：请求正常通过，统计失败率；",
            "<strong>open</strong>（熔断）：失败率超阈值，<em>直接拒绝所有请求</em>，不再打上游；",
            "<strong>half-open</strong>（试探）：熔断一段时间后，<strong>放一个请求过去试试</strong>；"
            "成功就回到 closed，失败就回到 open 并延长等待。",
        ]),
        P("<strong>关键在 half-open 这个状态</strong>——没有它，熔断之后需要人工介入才能恢复；"
          "而评测经常在无人值守时跑（夜间、CI），<em>自动恢复的价值远大于它的实现成本</em>。"),
    ])),

    # ============================================================== 6
    ("resume", "断点续跑：三个层次", "".join([
        P("模块 00 已经实现了最基本的续跑（主键去重）。这一节讲它的三个层次，"
          "以及为什么第三层经常被忽略。"),
        TABLE(["层次", "能续什么", "实现", "什么时候不够用"], [
            ["<strong>① 任务级</strong>", "已完成的任务不重跑", "主键 <code>(run_id, task_id, attempt)</code> 去重", "单条任务本身很贵时（agent 跑 40 步）"],
            ["<strong>② 调用级</strong>", "同一任务内已完成的模型调用不重发", "<strong>缓存</strong>（第 1 节）", "调用之间有状态时（agent 的环境已经变了）"],
            ["<strong>③ 状态级</strong>", "agent 的中间状态（环境快照、上下文）", "检查点 + 环境快照", "环境不可序列化时"],
        ]),
        CALLOUT("warn", "第三层有一个必须知道的陷阱：<strong>从检查点恢复的运行，"
                        "与从头跑到底的运行，未必是同一个实验。</strong>"
                        "<em>如果 agent 的行为依赖于「已经花了多少预算」「上下文里有什么」，"
                        "那么恢复点的状态就成了一个隐藏变量。</em>"
                        "<strong>实践建议：状态级续跑只用于「省钱地重跑失败任务」，"
                        "不要用于产出正式报告的运行</strong>——正式运行应当从头跑完，"
                        "并在 spec 里记录 <code>resumed: false</code>。"),
        H3("run_id 的设计"),
        P("续跑的一切都建立在 <code>run_id</code> 上，所以它的设计值得单独说："),
        UL([
            "<strong>run_id 应当由 spec 指纹 + 时间戳组成</strong>，"
            "例如 <code>f2a91b7c-20260829-1430</code>。"
            "<em>前半段让你一眼看出「这次跑的是什么配置」，后半段保证唯一。</em>",
            "<strong>复用 run_id 必须是显式的</strong>：加 <code>--resume &lt;run_id&gt;</code> 参数，"
            "而不是默认复用。<em>模块 00 练习 3 的「跳过数 &gt; 0」就是检测意外复用的信号</em>；",
            "<strong>续跑时必须校验指纹</strong>：如果 <code>--resume</code> 的那个 run_id "
            "对应的指纹与当前 spec 不同，<strong>直接报错退出</strong>——"
            "<em>否则你会得到一个「一半用旧配置、一半用新配置」的运行，而且完全看不出来</em>。",
        ]),
    ])),

    # ============================================================== 7
    ("observability", "Runner 本身的可观测性：五个必报的数", "".join([
        P("最后一节：runner 自己也需要被监控。下面五个数应当在每次运行结束时打印，"
          "并落到结果里——<strong>它们不是「性能指标」，而是「这份结果可不可信」的判据</strong>。"),
        CODE("""RUN SUMMARY · run_id=f2a91b7c-20260829-1430
  完成:            512 / 512 tasks × 3 attempts = 1536 rows
  失败分解:        ok 1489 | timeout 22 | refusal 11 | parse_error 9 | scorer_error 5
  ────────────────────────────────────────────────────────────────
  ① 缓存命中率:     0.0%      ← 首次运行应为 0；非 0 说明 run_id 被复用了
  ② 重试率:         3.2%      （其中 429 占 2.1%，5xx 占 1.1%）
  ③ 并发实际值:     8         （配置 8，未被限流器压低）
  ④ 限流等待占比:   11.4%     ← 超过 30% 说明并发设得比配额高，纯粹在浪费墙钟时间
  ⑤ 成本:           $12.47    （预检估计 $11.80，偏差 +5.7%）
  ────────────────────────────────────────────────────────────────
  scorer_error 0.33%          ← 必须趋近于零；超过 1% 就该去修判分器"""),
        TABLE(["指标", "健康范围", "异常时说明什么"], [
            ["<strong>缓存命中率</strong>", "首次 0%，重跑 &gt; 90%", "首次运行非 0 → <strong>run_id 被意外复用</strong>；重跑很低 → 缓存键里混进了不该有的东西（比如时间戳）"],
            ["<strong>重试率</strong>", "&lt; 5%", "高 → 上游不稳或并发过高；<em>同时要看重试是否只发生在失败样本上（第 3 节的偏倚）</em>"],
            ["<strong>限流等待占比</strong>", "&lt; 30%", "高 → 并发设得比配额高，加并发只会增加等待，不会提高吞吐"],
            ["<strong>成本 vs 预检估计</strong>", "偏差 &lt; 20%", "偏差大 → 预检样本不代表整体（通常是难题更贵）"],
            ["<strong>scorer_error 率</strong>", "<strong>趋近 0</strong>", "&gt; 1% → 判分器有 bug，这份结果的可信度存疑"],
        ]),
        CALLOUT("intuition", "这五个数里最容易被忽略、也最有诊断价值的是<strong>「首次运行的缓存命中率非 0」</strong>。"
                             "<em>它几乎总是意味着有人复用了 run_id</em>——"
                             "而复用 run_id 会让新配置的结果与旧配置的结果混在同一个 run 里，"
                             "<strong>这是一个「指纹校验都抓不到」的污染</strong>"
                             "（因为写入时用的是当前指纹，混进去的旧行用的是旧指纹，"
                             "而聚合时如果没检查「一个 run 内指纹唯一」就发现不了）。"
                             "<strong>所以模块 00 里那条 <code>assert len(fingerprints) == 1</code> 是必须的。</strong>"),
    ])),
    # ============================================================== 7x
    ("cost-attribution", "成本归因：钱到底花在哪", "".join([
        P("模块 02 第 5 节讲了怎么<strong>不超支</strong>，这一节讲怎么<strong>知道钱花在哪</strong>——"
          "因为「总共花了 12 美元」这个数字不足以做任何优化决策。"),
        TABLE(["切分维度", "回答什么问题", "典型发现"], [
            ["<strong>按任务</strong>", "哪些题最贵", "长尾极端：5% 的任务吃掉 40% 的预算（通常是循环或超长轨迹）"],
            ["<strong>按失败类型</strong>", "钱有多少花在了失败上", "<strong>失败样本的成本占比经常超过一半</strong>——因为失败往往伴随重试与超长轨迹"],
            ["<strong>按重试</strong>", "重试消耗了多少", "重试率 5% 但成本占比 15%（重试的都是难题，本身就更贵）"],
            ["<strong>按缓存命中</strong>", "缓存省了多少", "用来验证缓存是不是真的在工作"],
        ]),
        CALLOUT("intuition", "第二行的发现最有行动价值：<strong>如果一半的预算花在了最终失败的样本上，"
                             "那么「提前放弃明显没救的任务」就是一个立竿见影的优化</strong>"
                             "（C66 模块 03 的循环检测 + 本模块第 5 节的单任务预算）。"
                             "<em>而这个判断只有在成本按失败类型切分之后才能做出</em>——"
                             "看总成本永远看不出来。"),
        P("实现上这不需要新字段：<strong>模块 02 已经在每行结果里记了 <code>cost_usd</code> 与 "
          "<code>status</code></strong>，切分只是一句 <code>GROUP BY</code>（模块 03）。"
          "<em>这是「存最细粒度事实」这条设计的又一次兑现</em>。"),
    ])),

    # ============================================================== 8
    ("agent-runner", "Agent 场景的额外复杂度：轨迹、环境、嵌套调用", "".join([
        P("前七节讲的 runner 假定「一个任务 = 一次模型调用」。"
          "<strong>agent 场景下这个假定不成立</strong>，而它带来的复杂度值得单独说清楚。"),
        TABLE(["维度", "单次调用场景", "agent 场景", "runner 要多做什么"], [
            ["<strong>调用次数</strong>", "1 次", "几十到几百次", "预算控制要下沉到<strong>单任务</strong>粒度（第 5 节）"],
            ["<strong>缓存</strong>", "输入 → 输出，直接缓存", "<strong>调用之间有状态</strong>，第 3 步的输入依赖第 2 步的输出", "只能缓存<em>确定性前缀</em>，或整条轨迹一起缓存"],
            ["<strong>失败</strong>", "一次调用失败", "<strong>第 17 步失败</strong>——前 16 步的成本已经花掉了", "记录失败发生在第几步；决定是重跑整条还是从检查点续"],
            ["<strong>环境</strong>", "无状态", "容器/数据库/浏览器，<strong>必须在任务之间重置</strong>", "环境生命周期管理；重置失败也是一类失败"],
            ["<strong>超时</strong>", "单次调用超时", "<strong>两级</strong>：单步超时 + 整条轨迹超时", "两个都要配，且都要进 spec"],
        ]),
        CALLOUT("danger", "第四行是 agent 评测里最常见的一类<strong>静默污染</strong>："
                          "<strong>环境没有在任务之间被正确重置。</strong>"
                          "<em>上一个任务往数据库里写的数据还在，下一个任务读到了它——"
                          "结果可能变好（信息泄漏）也可能变坏（状态冲突），而且完全不报错。</em>"
                          "<strong>防御方式是在每个任务开始前做一次「环境指纹」校验</strong>："
                          "对初始状态取哈希，与预期值比对，不一致就判为 <code>env_error</code> 并跳过——"
                          "<em>这与本课反复出现的「确定性检查优先」是同一条思路</em>。"),
        H3("agent 场景的缓存：只能缓存确定性前缀"),
        P("由于状态依赖，agent 的调用无法逐个独立缓存。可行的两种做法："),
        UL([
            "<strong>整条轨迹缓存</strong>：键 = <code>(task_id, exec_fp)</code>，值 = 完整轨迹。"
            "<em>命中率低（任何配置变化都失效），但语义绝对正确</em>；",
            "<strong>确定性前缀缓存</strong>：如果 agent 的前 $k$ 步在给定配置下是确定的"
            "（temperature=0 且环境已重置），可以缓存这个前缀。"
            "<strong>但必须把「环境初始状态的哈希」也放进键里</strong>——"
            "<em>否则环境变了而缓存命中，会得到一条在错误环境上产生的轨迹</em>。",
        ]),
        H3("嵌套调用的成本归因"),
        P("agent 场景还有一个成本侧的细节：<strong>一次任务的成本要归因到哪一步</strong>。"
          "<em>如果只记总成本，你会知道「这个任务花了 0.8 美元」，"
          "但不知道其中 0.6 美元花在了一个反复重试的工具调用上。</em>"),
        P("解法是让每一步的成本都单独落库，并在聚合时提供两个视角："
          "<strong>按任务</strong>（这道题贵不贵）与<strong>按步骤类型</strong>"
          "（钱花在规划、工具调用、还是最后的总结上）。"
          "<em>后者是优化成本时唯一有用的视角</em>——"
          "而它需要的字段在 C66 模块 03 的轨迹 schema 里已经有了，"
          "<strong>这里只是把它接进 runner 的成本统计</strong>。"),
        H3("单任务预算：与 C66-03 的循环检测接在一起"),
        P("模块 02 第 5 节讲的预算控制，在 agent 场景下有一个额外的抓手："
          "<strong>C66 模块 03 的循环检测</strong>。"
          "<em>检出循环就提前终止这条轨迹，省下的预算拿去跑别的任务</em>。"
          "<strong>但被终止的轨迹必须单独标记为 <code>terminated_by_loop_detector</code>，"
          "而不是简单记成失败</strong>——因为「被我们主动掐掉的」和「模型自己做不出来的」"
          "是两个不同的量，混在一起会让失败分类失去意义（第 2 节）。"),
    ])),
]

NB = [
    md("""# 02 · Runner 工程（缓存键 / 失败分类 / 重试与偏倚 / 限流 / 预算熔断 / 续跑）

目标：把 runner 从「一个 for 循环」变成一个**不会骗你、不会烧穿预算、崩了能续**的执行器。

本 notebook 你会亲手实现：
1. **缓存键设计** —— 复现「改了 prompt 却读到旧结果」这个不报错的 bug，再修好它
2. **失败分类器** —— 五类失败，各自的重试策略与分母归属
3. **指数退避 + 抖动** —— 以及不加抖动时的惊群效应
4. **重试引入的选择偏倚** —— 「重试到成功为止」会把分数抬高多少
5. **令牌桶限流 + 并发上限** —— 两者管的不是一件事
6. **预算熔断与预检** —— 把「事故」变成「预估」
7. **run summary 的五个数** —— 尤其是「首次运行缓存命中率非 0」这个告警

> 心智模型：**runner 的正确性不是「跑完了」，而是「跑出来的数字没有被执行过程污染」。
> 缓存、重试、并发这三件事，每一件都能在不报错的情况下改变你的分数。**"""),

    md("""## 0 · 环境与被评「模型」"""),

    code("""import os, json, math, time, random, hashlib, shutil, itertools
from collections import Counter, defaultdict

import numpy as np

TMP = os.path.abspath('./_eval_tmp')
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP, exist_ok=True)

def stable_hash(obj, n=8):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:n]

class RateLimited(Exception): pass
class Transient(Exception): pass
class Timeout(Exception): pass
class Refusal(Exception): pass
class ParseError(Exception): pass

class FakeAPI:
    \"\"\"可控的被评模型。所有失败都是显式注入的，便于精确验证 runner 的行为。\"\"\"

    def __init__(self, prompt_version='v1', accuracy=0.7, seed=0,
                 p_rate_limited=0.0, p_transient=0.0, p_timeout=0.0,
                 p_refusal=0.0, p_parse=0.0, cost_per_call=0.01):
        self.prompt_version = prompt_version
        self.accuracy = accuracy
        self.rng = random.Random(seed)
        self.ps = dict(rate=p_rate_limited, trans=p_transient, to=p_timeout,
                       refuse=p_refusal, parse=p_parse)
        self.cost_per_call = cost_per_call
        self.n_calls = 0
        self.total_cost = 0.0

    def __call__(self, task):
        self.n_calls += 1
        self.total_cost += self.cost_per_call
        r = self.rng.random()
        if r < self.ps['rate']:
            raise RateLimited('429')
        if r < self.ps['rate'] + self.ps['trans']:
            raise Transient('502')
        if r < self.ps['rate'] + self.ps['trans'] + self.ps['to']:
            raise Timeout('deadline exceeded')
        if r < sum([self.ps['rate'], self.ps['trans'], self.ps['to'], self.ps['refuse']]):
            raise Refusal('content policy')
        if r < sum(self.ps.values()):
            raise ParseError('not valid json')
        # prompt_v2 比 v1 强 15 个点 —— 这就是第 1 节要检测的那个改动
        acc = self.accuracy + (0.15 if self.prompt_version == 'v2' else 0.0)
        return {'answer': task['target'] if self.rng.random() < acc else 'WRONG'}

TASKS = [{'task_id': f't{i:03d}', 'input': f'q{i}', 'target': f'a{i}'} for i in range(120)]
api = FakeAPI(seed=1)
print('一次调用:', api(TASKS[0]), '| 累计成本:', f'${api.total_cost:.3f}')
print('\\n✅ 五类失败都可以被精确注入——这比真实 API 更适合验证 runner 的正确性。')"""),

    md("""## 1 · 缓存键：复现那个不报错的 bug，再修好它"""),

    code("""class Cache:
    def __init__(self):
        self.store = {}
        self.hits = 0
        self.misses = 0

    def get_or_call(self, key, fn):
        if key in self.store:
            self.hits += 1
            return self.store[key], True
        self.misses += 1
        val = fn()
        self.store[key] = val
        return val, False

    @property
    def hit_rate(self):
        n = self.hits + self.misses
        return self.hits / n if n else 0.0


def exec_fingerprint(spec):
    \"\"\"模块 01 的执行指纹：整个执行配置的哈希。加了新字段它自动就变。\"\"\"
    return stable_hash({'model': spec['model'], 'budget': spec['budget'],
                        'prompt_sha': spec['prompt_sha']}, 8)

def key_bad(task, spec):
    return stable_hash(task['input'], 16)                       # ❌ 只有输入内容

def key_good(task, spec):
    return stable_hash([task['input'], exec_fingerprint(spec)], 16)   # ✓ 内容 + 配置指纹


SPEC_V1 = {'model': {'id': 'm1', 'temperature': 0.0},
           'budget': {'retries': 2, 'timeout_s': 30},
           'prompt_sha': stable_hash('PROMPT TEMPLATE v1', 8)}
SPEC_V2 = json.loads(json.dumps(SPEC_V1))
SPEC_V2['prompt_sha'] = stable_hash('PROMPT TEMPLATE v2 —— 改了一句措辞', 8)

def run_with_cache(spec, tasks, cache, key_fn, prompt_version, seed=1):
    api = FakeAPI(prompt_version=prompt_version, accuracy=0.7, seed=seed)
    scores = []
    for t in tasks:
        out, _ = cache.get_or_call(key_fn(t, spec), lambda t=t: api(t))
        scores.append(1.0 if out['answer'] == t['target'] else 0.0)
    return float(np.mean(scores)), api.n_calls

print('=== ❌ 缓存键只含输入内容 ===')
c_bad = Cache()
s1, n1 = run_with_cache(SPEC_V1, TASKS, c_bad, key_bad, 'v1')
s2, n2 = run_with_cache(SPEC_V2, TASKS, c_bad, key_bad, 'v2')   # 改了 prompt
print(f'  prompt v1: 分数 {s1:.1%}  实际调用 {n1} 次')
print(f'  prompt v2: 分数 {s2:.1%}  实际调用 {n2} 次  ← 一次都没调用！')
assert s1 == s2 and n2 == 0
print('  症状：「我明明改了 prompt，分数却一点没变」 → 被误读成「这个改动没有效果」')

print('\\n=== ✓ 缓存键 = 内容 + 执行指纹 ===')
c_good = Cache()
s3, n3 = run_with_cache(SPEC_V1, TASKS, c_good, key_good, 'v1')
s4, n4 = run_with_cache(SPEC_V2, TASKS, c_good, key_good, 'v2')
print(f'  prompt v1: 分数 {s3:.1%}  实际调用 {n3} 次')
print(f'  prompt v2: 分数 {s4:.1%}  实际调用 {n4} 次')
assert n4 == len(TASKS) and s4 > s3 + 0.05
print(f'  真实效果：prompt v2 比 v1 高 {s4-s3:.1%} —— 这个改动其实很有效')

# 同配置重跑仍然能省钱
c2 = Cache()
run_with_cache(SPEC_V1, TASKS, c2, key_good, 'v1')
run_with_cache(SPEC_V1, TASKS, c2, key_good, 'v1')
print(f'\\n同配置重跑的缓存命中率: {c2.hit_rate:.0%}')
assert c2.hit_rate >= 0.5
print('✅ 缓存该省的钱一分没少省，该失效的时候准确失效——关键是键里用了 exec_fingerprint，')
print('   而不是手写一份「要包含哪些字段」的列表（那种列表加新字段时没人会记得更新）。')"""),

    md("""## 2 · 失败分类：五类失败，五种处理"""),

    code("""FAILURE_POLICY = {
    'RateLimited': dict(retry=True,  in_denominator=True,  counts_as='retryable'),
    'Transient':   dict(retry=True,  in_denominator=True,  counts_as='retryable'),
    'Timeout':     dict(retry=True,  in_denominator=True,  counts_as='failure'),
    'Refusal':     dict(retry=False, in_denominator=True,  counts_as='refusal'),
    'ParseError':  dict(retry=True,  in_denominator=True,  counts_as='parse_error'),
    'ScorerError': dict(retry=False, in_denominator=False, counts_as='scorer_error'),
}

def classify(exc):
    return type(exc).__name__

for name, pol in FAILURE_POLICY.items():
    print(f'{name:<14} 重试={str(pol["retry"]):<6} 计入分母={str(pol["in_denominator"]):<6} '
          f'归类={pol["counts_as"]}')

assert FAILURE_POLICY['Refusal']['retry'] is False, '拒答不该重试'
assert FAILURE_POLICY['Timeout']['in_denominator'] is True, '超时必须计入分母'
assert FAILURE_POLICY['ScorerError']['in_denominator'] is False, '判分器崩溃是唯一可排除的'
print('\\n✅ 注意 Timeout：它重试，但**如果重试后仍然超时就算失败并计入分母**——')
print('   因为超时是混合信号，一部分来自基础设施，一部分是真实的能力信号。')
print('   把它当成「基础设施错误并重试到成功」，等于系统性地掩盖后者。')"""),

    md("""## 3 · 指数退避 + 抖动：不加抖动会怎样"""),

    code("""def backoff_delay(attempt, base=0.1, cap=8.0, jitter=True, rng=None):
    d = min(base * (2 ** attempt), cap)
    if jitter:
        rng = rng or random
        d *= rng.uniform(0.5, 1.5)
    return d

print(f"{'第几次重试':>10}{'无抖动':>10}{'有抖动(样本)':>16}")
rng = random.Random(0)
for k in range(6):
    no_j = backoff_delay(k, jitter=False)
    with_j = [round(backoff_delay(k, jitter=True, rng=rng), 3) for _ in range(3)]
    print(f'{k:>10}{no_j:>10.2f}{str(with_j):>16}')

# 惊群效应：100 个同时被限流的请求，在同一时刻重试
def herd_spread(n=200, attempt=3, jitter=True, seed=0):
    rng = random.Random(seed)
    times = [backoff_delay(attempt, jitter=jitter, rng=rng) for _ in range(n)]
    buckets = Counter(round(t, 1) for t in times)
    return max(buckets.values()), len(buckets)

peak_no, slots_no = herd_spread(jitter=False)
peak_yes, slots_yes = herd_spread(jitter=True)
print(f'\\n200 个同时被限流的请求，第 3 次重试时:')
print(f'  无抖动: 全部挤在 {slots_no} 个时刻，峰值 {peak_no} 个请求  ← 把上游再打垮一次')
print(f'  有抖动: 摊到 {slots_yes} 个时刻，峰值 {peak_yes} 个请求')
assert peak_no == 200 and peak_yes < 40
print('\\n✅ 抖动那一项不是可选的——没有它，重试本身就是下一次雪崩的原因。')"""),

    md("""## 4 · 重试引入的选择偏倚：「重试到成功为止」抬高多少分"""),

    code("""def run_with_retry_policy(tasks, policy, seed=0, max_retries=3, true_acc=0.55):
    \"\"\"policy: 'infra_only'（只对基础设施错误重试，正确）
               'until_pass'（判分为 0 就重试，严重偏倚）
               'on_parse'  （解析失败也重试，轻微偏倚）\"\"\"
    rng = random.Random(seed)
    scores, n_calls = [], 0

    def one_call():
        nonlocal n_calls
        n_calls += 1
        r = rng.random()
        if r < 0.08:
            raise Transient('502')
        if r < 0.14:
            raise ParseError('bad json')
        return 1.0 if rng.random() < true_acc else 0.0

    for _ in tasks:
        score = None
        for attempt in range(max_retries + 1):
            try:
                score = one_call()
            except Transient:
                continue                                  # 所有策略都重试
            except ParseError:
                if policy in ('on_parse', 'until_pass'):
                    continue
                score = 0.0                               # 不重试就记为失败
                break
            # 拿到判分结果之后还重试 —— 这就是偏倚的来源
            if policy == 'until_pass' and score == 0.0 and attempt < max_retries:
                continue
            break
        scores.append(0.0 if score is None else score)
    return float(np.mean(scores)), n_calls

TRUE_ACC = 0.55
print(f'真实能力: {TRUE_ACC:.0%}\\n')
print(f"{'重试策略':<24}{'观测分数':>10}{'偏离真值':>12}{'调用次数':>10}")
res = {}
for pol, label in [('infra_only', '只重试基础设施错误 ✓'),
                   ('on_parse', '解析失败也重试'),
                   ('until_pass', '判分为 0 就重试 ❌')]:
    s, n = run_with_retry_policy(TASKS, pol, seed=7, true_acc=TRUE_ACC)
    res[pol] = s
    print(f'{label:<24}{s:>10.1%}{s - TRUE_ACC:>+12.1%}{n:>10}')

assert abs(res['infra_only'] - TRUE_ACC) < 0.06, '正确策略应当接近真值'
assert res['until_pass'] > res['infra_only'] + 0.15, '「重试到成功」必然大幅抬高分数'
print(f'\\n✅ 「判分为 0 就重试」把 {TRUE_ACC:.0%} 的真实能力抬到了 {res["until_pass"]:.0%}。')
print('   它不会报错、日志看起来正常、代码读起来也很合理——')
print('   **这就是为什么规则必须写死：重试的判断只能看异常类型，不能看判分结果。**')
print('   代码结构上的落实方式：重试逻辑必须在判分之前完成。')"""),

    md("""## 5 · 令牌桶限流 + 并发上限：两者管的不是一件事"""),

    code("""class TokenBucket:
    \"\"\"令牌桶：平时允许突发，长期严格遵守平均速率。\"\"\"

    def __init__(self, rate, burst, now=0.0):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.t = now
        self.total_wait = 0.0

    def acquire(self, now, n=1):
        \"\"\"返回需要等待的时间（模拟时钟，不真的 sleep）。\"\"\"
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        need = (n - self.tokens) / self.rate
        self.tokens = 0.0
        self.t = now + need
        self.total_wait += need
        return need

def simulate(n_req, rate, burst, concurrency, service_time=0.05):
    \"\"\"模拟时钟下的执行：并发上限决定同时在飞多少，限流器决定发出速率。\"\"\"
    bucket = TokenBucket(rate, burst)
    now, in_flight, finished, wait_total = 0.0, [], 0, 0.0
    for i in range(n_req):
        while len(in_flight) >= concurrency:
            now = max(now, min(in_flight))
            in_flight = [t for t in in_flight if t > now]
            finished += 1
        w = bucket.acquire(now)
        wait_total += w
        now += w
        in_flight.append(now + service_time)
    makespan = max(in_flight) if in_flight else now
    return {'makespan': makespan, 'throughput': n_req / makespan,
            'wait_ratio': wait_total / makespan if makespan else 0.0}

print(f"{'并发':>6}{'限流(req/s)':>14}{'总耗时(s)':>12}{'吞吐(req/s)':>14}{'限流等待占比':>14}")
for conc in [1, 4, 8, 16, 32]:
    r = simulate(400, rate=20, burst=20, concurrency=conc)
    print(f'{conc:>6}{20:>14}{r["makespan"]:>12.1f}{r["throughput"]:>14.1f}'
          f'{r["wait_ratio"]:>14.0%}')

r4 = simulate(400, rate=20, burst=20, concurrency=4)
r32 = simulate(400, rate=20, burst=20, concurrency=32)
assert abs(r32['throughput'] - r4['throughput']) < 3, '限流封顶后，加并发不再提高吞吐'
assert r32['wait_ratio'] > r4['wait_ratio'], '加并发只是让更多请求在等令牌'
print('\\n✅ 限流器把吞吐封在 20 req/s 之后，把并发从 4 加到 32 完全没用——')
print('   只是让更多请求在排队等令牌（等待占比从 '
      f'{r4["wait_ratio"]:.0%} 涨到 {r32["wait_ratio"]:.0%}）。')
print('   **限流等待占比 > 30% 就是「并发设得比配额高」的信号**——加并发纯属浪费。')"""),

    md("""## 6 · 预算保护：预检 + 熔断"""),

    code("""def dry_run_estimate(tasks, cost_per_call, n_probe=10, attempts=1):
    \"\"\"先跑一小批，外推总成本。这一步能抓住绝大多数「配置写错导致成本爆炸」。\"\"\"
    probe_cost = n_probe * attempts * cost_per_call
    per_task = probe_cost / n_probe
    return {'n_probe': n_probe, 'per_task': per_task,
            'estimated_total': per_task * len(tasks)}

est = dry_run_estimate(TASKS, cost_per_call=0.01, attempts=3)
print(f'预检: {est["n_probe"]} 条 → 单条 ${est["per_task"]:.4f} → '
      f'全量 {len(TASKS)} 条预计 ${est["estimated_total"]:.2f}')

# 配置写错的情况：attempts 被误写成 50
est_bad = dry_run_estimate(TASKS, cost_per_call=0.01, attempts=50)
print(f'如果 attempts 误写成 50: 预计 ${est_bad["estimated_total"]:.2f}  '
      f'← 预检会在花钱之前就把它暴露出来')
assert est_bad['estimated_total'] > 10 * est['estimated_total']
print('\\n✅ 预检便宜到几乎没有理由不做：跑 10 条，打印预估总花费，然后再继续。')"""),

    code("""class CircuitBreaker:
    \"\"\"三状态熔断器。half_open 是关键——它让熔断能**自动恢复**，无人值守时尤其重要。\"\"\"

    def __init__(self, window=20, threshold=0.5, cooldown=5.0):
        self.window, self.threshold, self.cooldown = window, threshold, cooldown
        self.recent = []
        self.state = 'closed'
        self.opened_at = None

    def allow(self, now):
        if self.state == 'open':
            if now - self.opened_at >= self.cooldown:
                self.state = 'half_open'
                return True                       # 放一个请求过去试探
            return False
        return True

    def record(self, ok, now):
        if self.state == 'half_open':
            self.state = 'closed' if ok else 'open'
            if not ok:
                self.opened_at = now
                self.cooldown *= 2                # 失败则延长等待
            self.recent = []
            return
        self.recent.append(ok)
        if len(self.recent) > self.window:
            self.recent.pop(0)
        if len(self.recent) == self.window and (1 - np.mean(self.recent)) > self.threshold:
            self.state = 'open'
            self.opened_at = now

cb = CircuitBreaker(window=10, threshold=0.5, cooldown=3.0)
timeline = []
now = 0.0
# 前 10 步正常，第 10-39 步上游挂了（全部失败），第 40 步起恢复
for step in range(80):
    now += 0.5
    allowed = cb.allow(now)
    state_at_allow = cb.state          # ← half_open 是**瞬态**：allow 里进入，record 里立刻离开
    if allowed:
        ok = (step < 10) or (step >= 40)
        cb.record(ok, now)
    timeline.append((step, state_at_allow, allowed, cb.state))

probe_steps = [i for i, s, _, _ in timeline if s == 'half_open']
blocked = sum(1 for _, _, a, _ in timeline if not a)
transitions = [f'{i}:{after}' for i, _, _, after in timeline
               if i == 0 or after != timeline[i-1][3]]
print('状态变化:', transitions)
print(f'进入 half_open 试探的时刻: {probe_steps}')
print(f'被熔断挡下的请求: {blocked} / 80')
assert 'open' in [t[3] for t in timeline], '上游全挂时必须熔断'
assert len(probe_steps) >= 2, '必须反复进入试探状态'
assert timeline[-1][3] == 'closed', '上游恢复后必须自动回到正常'
assert blocked > 20
print('\\n✅ 熔断 → 试探（失败则延长等待）→ 再试探 → 恢复，全程无人介入。')
print('   注意 half_open 是一个**瞬态**：allow() 里进入，record() 里立刻转向 closed 或 open，')
print('   所以只有在 allow 的那一刻才观察得到——这也是它只放行一个请求的实现方式。')
print('   没有它的话，熔断之后需要人工重启，而评测经常在夜间/CI 里无人值守地跑。')"""),

    md("""## 7 · Run Summary：五个必报的数"""),

    code("""def run_summary(run_id, rows, cache, n_retries, concurrency, wait_ratio,
                cost, cost_estimate):
    kinds = Counter(r['kind'] for r in rows)
    n = len(rows)
    n_scorer_err = kinds.get('scorer_error', 0)
    denom = n - n_scorer_err
    ok = kinds.get('ok', 0)
    return {
        'run_id': run_id,
        'n_rows': n,
        'breakdown': dict(kinds),
        'score': ok / denom if denom else float('nan'),
        'cache_hit_rate': cache.hit_rate,
        'retry_rate': n_retries / n if n else 0.0,
        'concurrency': concurrency,
        'ratelimit_wait_ratio': wait_ratio,
        'cost_usd': cost,
        'cost_vs_estimate': (cost - cost_estimate) / cost_estimate if cost_estimate else 0.0,
        'scorer_error_rate': n_scorer_err / n if n else 0.0,
    }

rng = np.random.default_rng(3)
KINDS = ['ok'] * 1489 + ['timeout'] * 22 + ['refusal'] * 11 + \\
        ['parse_error'] * 9 + ['scorer_error'] * 5
rows = [{'kind': k} for k in KINDS]
fresh_cache = Cache(); fresh_cache.misses = len(rows)
summ = run_summary('f2a91b7c-20260829-1430', rows, fresh_cache,
                   n_retries=49, concurrency=8, wait_ratio=0.114,
                   cost=12.47, cost_estimate=11.80)
print(f'RUN SUMMARY · {summ["run_id"]}')
print(f'  行数 {summ["n_rows"]} | 分解 {summ["breakdown"]}')
print(f'  分数 {summ["score"]:.1%}   （分母已排除 {summ["breakdown"].get("scorer_error",0)} 条判分器崩溃）')
for k in ['cache_hit_rate', 'retry_rate', 'ratelimit_wait_ratio',
          'cost_vs_estimate', 'scorer_error_rate']:
    print(f'  {k:<24} {summ[k]:.2%}')

HEALTH = {
    'cache_hit_rate':      lambda v, first: (v == 0.0) if first else (v > 0.9),
    'retry_rate':          lambda v, first: v < 0.05,
    'ratelimit_wait_ratio':lambda v, first: v < 0.30,
    'cost_vs_estimate':    lambda v, first: abs(v) < 0.20,
    'scorer_error_rate':   lambda v, first: v < 0.01,
}
alerts = [k for k, fn in HEALTH.items() if not fn(summ[k], True)]
print(f'\\n健康检查未通过的项: {alerts}')
assert alerts == [], '本次运行应当全部健康'

# 制造一个「首次运行却有缓存命中」的情况 —— run_id 被意外复用
reused = Cache(); reused.hits = 300; reused.misses = 1236
summ2 = run_summary('same-run-id', rows, reused, 49, 8, 0.114, 12.47, 11.80)
alerts2 = [k for k, fn in HEALTH.items() if not fn(summ2[k], True)]
print(f'run_id 被复用时的告警: {alerts2}  (命中率 {summ2["cache_hit_rate"]:.0%})')
assert 'cache_hit_rate' in alerts2
print('\\n✅ 「首次运行的缓存命中率非 0」是一个高价值告警——')
print('   它几乎总是意味着 run_id 被复用，而复用会让新旧配置的结果混进同一个 run。')
print('   这类污染连指纹校验都抓不到（写入用当前指纹，混进去的旧行用旧指纹），')
print('   所以聚合时那条 assert「一个 run 内指纹唯一」是必须的。')"""),

    md("""## ✏️ 练习 1：缓存键的完整性检查

实现 `cache_key_covers(key_fn, spec, task, mutations)`：
对 `mutations`（一个 `{描述: 修改后的 spec}` 字典）逐个检查
`key_fn(task, mutated_spec) != key_fn(task, spec)`，
返回 `(是否全部覆盖, 未被覆盖的修改描述列表)`。"""),

    code("""def cache_key_covers(key_fn, spec, task, mutations):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
def mut(spec, path, value):
    s = json.loads(json.dumps(spec))
    d = s
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = value
    return s

MUTATIONS = {
    '改 prompt':      mut(SPEC_V1, ['prompt_sha'], 'deadbeef'),
    '改模型':         mut(SPEC_V1, ['model', 'id'], 'm2'),
    '改温度':         mut(SPEC_V1, ['model', 'temperature'], 0.7),
    '改重试次数':     mut(SPEC_V1, ['budget', 'retries'], 5),
}
ok_bad, miss_bad = cache_key_covers(key_bad, SPEC_V1, TASKS[0], MUTATIONS)
ok_good, miss_good = cache_key_covers(key_good, SPEC_V1, TASKS[0], MUTATIONS)
print(f'❌ key_bad : 全覆盖={ok_bad}, 漏掉 {len(miss_bad)} 项 → {miss_bad}')
print(f'✓ key_good: 全覆盖={ok_good}, 漏掉 {len(miss_good)} 项')
assert ok_bad is False and len(miss_bad) == len(MUTATIONS)
assert ok_good is True and miss_good == []
print('✅ 练习 1 通过：这个检查应当作为单元测试跑在 CI 里——')
print('   每加一个配置项，就往 MUTATIONS 里加一条，确保缓存键真的覆盖了它。')"""),

    md("""## ✏️ 练习 2：失败分类的分母计算

实现 `compute_denominators(rows)`：输入 `[{'kind': ...}, ...]`，
返回 `{'n_total', 'n_denominator', 'n_success', 'score', 'excluded'}`，
其中分母排除 `scorer_error`，`n_success` 只算 `kind == 'ok'`。"""),

    code("""def compute_denominators(rows):
    # TODO：用上面的 FAILURE_POLICY 判断哪些计入分母
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
POLICY_KIND = {'ok': True, 'retryable': True, 'failure': True, 'timeout': True,
               'refusal': True, 'parse_error': True, 'scorer_error': False}
r = compute_denominators(rows)
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
assert r['n_total'] == len(rows)
assert r['excluded'] == 5 and r['n_denominator'] == len(rows) - 5
assert abs(r['score'] - 1489 / (len(rows) - 5)) < 1e-9

# 全部是判分器崩溃的极端情形
r2 = compute_denominators([{'kind': 'scorer_error'}] * 10)
assert r2['n_denominator'] == 0 and math.isnan(r2['score'])
print('\\n全部判分器崩溃时: 分母为 0，分数为 nan（而不是 0 或 1）')
print('✅ 练习 2 通过：分母排除 scorer_error，但它的**比例必须被报告**——')
print('   超过 1% 就说明判分器有 bug，这份结果的可信度存疑。')"""),

    md("""## ✏️ 练习 3：重试预算的分配

实现 `retry_budget(n_tasks, base_calls, retry_rate, max_retries)`：
估算总调用次数 = `n_tasks * base_calls * (1 + retry_rate + retry_rate^2 + ... + retry_rate^max_retries)`
（等比级数，因为每次重试也可能再失败）。返回 `(总调用次数, 相对无重试的倍数)`。"""),

    code("""def retry_budget(n_tasks, base_calls, retry_rate, max_retries):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
n0, m0 = retry_budget(500, 1, 0.0, 3)
assert n0 == 500 and abs(m0 - 1.0) < 1e-12
n1, m1 = retry_budget(500, 1, 0.10, 3)
n2, m2 = retry_budget(500, 1, 0.50, 3)
assert n2 > n1 > n0
print(f"{'失败率':>8}{'总调用':>10}{'成本倍数':>10}")
for rr in [0.0, 0.05, 0.10, 0.30, 0.50, 0.80]:
    n_, m_ = retry_budget(500, 1, rr, 3)
    print(f'{rr:>8.0%}{n_:>10.0f}{m_:>10.2f}x')
n_hi, m_hi = retry_budget(500, 1, 0.80, 3)
assert m_hi > 2.5
print('✅ 练习 3 通过：失败率 30% 时成本就涨了四成，80% 时接近 3 倍——')
print('   **预算估算必须把重试算进去**，否则预检的估计会系统性偏低。')"""),

    md("""## ✏️ 练习 4：并发的最优选择

实现 `best_concurrency(n_req, rate, burst, candidates, wait_cap=0.30)`：
在候选并发度里，选出「限流等待占比 ≤ wait_cap」且吞吐最高的那个。
返回 `(最优并发, 该并发下的吞吐, 等待占比)`。"""),

    code("""def best_concurrency(n_req, rate, burst, candidates, wait_cap=0.30):
    # TODO：用上面的 simulate
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
CANDS = [1, 2, 4, 8, 16, 32, 64]
c, tp, wr = best_concurrency(400, rate=20, burst=20, candidates=CANDS)
print(f'配额 20 req/s 时的最优并发: {c}  (吞吐 {tp:.1f} req/s, 等待占比 {wr:.0%})')
assert wr <= 0.30
assert c < max(CANDS), '最优并发不该是最大的那个'

c2, tp2, wr2 = best_concurrency(400, rate=100, burst=100, candidates=CANDS)
print(f'配额 100 req/s 时的最优并发: {c2}  (吞吐 {tp2:.1f} req/s)')
assert c2 >= c, '配额更高时，最优并发应当不降低'
print('✅ 练习 4 通过：最优并发由**上游配额**决定，不是越大越好——')
print('   超过配额之后加并发只增加等待，不增加吞吐，还会推高 429 率与超时率。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def cache_key_covers(key_fn, spec, task, mutations):
    base = key_fn(task, spec)
    missed = [desc for desc, m in mutations.items() if key_fn(task, m) == base]
    return (len(missed) == 0, missed)"""),

    code("""# 练习 2 参考答案
def compute_denominators(rows):
    kinds = Counter(r['kind'] for r in rows)
    excluded = sum(c for k, c in kinds.items() if not POLICY_KIND.get(k, True))
    n_total = len(rows)
    n_denom = n_total - excluded
    n_succ = kinds.get('ok', 0)
    return {'n_total': n_total, 'n_denominator': n_denom, 'n_success': n_succ,
            'score': (n_succ / n_denom) if n_denom else float('nan'),
            'excluded': excluded}"""),

    code("""# 练习 3 参考答案
def retry_budget(n_tasks, base_calls, retry_rate, max_retries):
    factor = sum(retry_rate ** k for k in range(max_retries + 1))
    total = n_tasks * base_calls * factor
    return (total, factor)"""),

    code("""# 练习 4 参考答案
def best_concurrency(n_req, rate, burst, candidates, wait_cap=0.30):
    best = None
    for c in candidates:
        r = simulate(n_req, rate, burst, c)
        if r['wait_ratio'] <= wait_cap:
            if best is None or r['throughput'] > best[1]:
                best = (c, r['throughput'], r['wait_ratio'])
    if best is None:                       # 全都超过等待上限，退回最小并发
        r = simulate(n_req, rate, burst, min(candidates))
        best = (min(candidates), r['throughput'], r['wait_ratio'])
    return best"""),

    md("""---
## 🧪 真实工程胶囊：runner 的落地要点"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 缓存键：永远用执行指纹，不要手写字段列表
# ══════════════════════════════════════════════════════════════════
def cache_key(task, spec):
    return sha256(json.dumps({
        "input": task["input"],
        "exec_fp": exec_fingerprint(spec),   # ← 整个执行配置的哈希，加字段自动生效
        "cache_format": 3,                   # ← 存储结构变更时整体失效
    }, sort_keys=True).encode()).hexdigest()

# 单元测试（练习 1）：每加一个配置项就往 MUTATIONS 里加一条
def test_cache_key_covers_all_config():
    for path, val in [(["model","id"],"other"), (["model","temperature"],0.7),
                      (["prompt_sha"],"x"), (["budget","retries"],9),
                      (["tools"],["a","b"])]:
        assert cache_key(T, mutate(SPEC, path, val)) != cache_key(T, SPEC), path

# ══════════════════════════════════════════════════════════════════
# B. 重试：只看异常类型，绝不看判分结果
# ══════════════════════════════════════════════════════════════════
RETRYABLE = (ConnectionError, TimeoutError, RateLimitError, InternalServerError)

async def call_with_retry(fn, *a, max_retries=3, **kw):
    for k in range(max_retries + 1):
        try:
            return await fn(*a, **kw)
        except RETRYABLE as e:
            if k == max_retries:
                raise
            await asyncio.sleep(min(0.5 * 2**k, 8) * random.uniform(0.5, 1.5))  # 抖动必需
# 结构上的落实：这个函数**拿不到 scorer**，所以它在物理上不可能"重试到通过为止"。

# ══════════════════════════════════════════════════════════════════
# C. 并发 + 限流：两个都要有
# ══════════════════════════════════════════════════════════════════
sem = asyncio.Semaphore(CONCURRENCY)         # 同时在飞多少（保护内存/连接数）
limiter = AsyncLimiter(RATE_PER_MIN, 60)     # 单位时间发多少（遵守上游配额）

async def guarded(task):
    async with sem, limiter:
        return await call_with_retry(api_call, task)

# inspect-ai: --max-connections N 对应 sem；限流通常由 SDK 内置的 retry 处理。
# **报告里必须写 concurrency**（C66-05 复现清单第 7 条）。

# ══════════════════════════════════════════════════════════════════
# D. 上线前必做：并发敏感性检查
# ══════════════════════════════════════════════════════════════════
# for c in [1, 4, 8, 16]:
#     run_eval(spec, smoke_subset, concurrency=c)
# 分数随 c 变化 → 超时阈值设得太紧，这个分数不能用。
# 分数对 c 不敏感 → ✅ 超时有余量，超时反映的是真实能力而非基础设施。

# ══════════════════════════════════════════════════════════════════
# E. 每次运行结束必须打印的五个数（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
# cache_hit_rate（首次应为 0）· retry_rate（<5%）· concurrency
# ratelimit_wait_ratio（<30%）· cost vs 预检估计（偏差<20%）· scorer_error_rate（→0）
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 缓存键 | 用 `exec_fingerprint` 而不是手写字段列表 | 每个 runner |
| 何时关缓存 | 估方差、算区间、跑 pass^k 时必须关 | 统计分析 |
| 失败五分类 | 只有 `scorer_error` 可以从分母排除，且必须报告比例 | 结果聚合 |
| 退避 + 抖动 | 抖动不是可选的——没有它重试就是下一次雪崩 | 重试实现 |
| 重试的偏倚 | **重试只看异常类型，不看判分结果**；结构上让重试拿不到 scorer | 最重要的一条 |
| 并发 vs 限流 | 两者管的不是一件事，都要有；等待占比 >30% = 并发白加 | 性能与成本 |
| 预检与熔断 | 预检把事故变成预估；half_open 让熔断能自动恢复 | 预算保护 |
| 五个必报的数 | 「首次运行缓存命中率非 0」= run_id 被复用 | run summary |

下一模块：**03 · 结果存储与分析**——schema 设计、切片查询、
以及「为什么聚合逻辑应该和结果分开」。""")
]
