# 术语词典 · Glossary（多智能体编排与生产化）

> 按主题分组，每条 2–3 句中文释义、英文术语保留。读 Anthropic 的 multi-agent research system 工程博客、《Building effective agents》、orchestrator-worker 模式、OpenTelemetry tracing 规范、AutoGen 等论文遇到生词回这里查。本课用纯标准库 + MockLLM 在 CPU 上模拟这些机制，但术语与真实生产 agent 系统一一对应。

## Agent 与编排基础 · Agents & Orchestration Basics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agent | 智能体 | 一个 LLM 在循环里反复「看观察 → 想 → 调工具 → 看结果」直到任务完成的系统。本课的起点是单个这样的 agent（ReAct 回路），目标是把多个这样的 agent 编排成系统、并推向生产。 |
| orchestration | 编排 | 用代码（或一个 lead agent）把多个步骤 / 多个 agent 组织起来、按某种拓扑（流水线 / 扇出 / 路由 / 主从）协同完成一个任务的过程。本课的核心主题。 |
| orchestrator-worker | 编排者-工作者 | 一种主流多 agent 范式：一个 orchestrator（也叫 lead / supervisor）负责分解任务、调度并汇总；多个 worker（subagent）各自专注一个子任务。Anthropic 的 multi-agent research system 即此结构。 |
| subagent | 子智能体 | 由父 agent（orchestrator）派生、用于完成某个子任务的 agent。它通常有自己隔离的上下文，跑完把结构化结果回传给父 agent。本课模块 01 从零实现它。 |
| lead agent / orchestrator | 主控 agent | 编排里那个负责「拆任务、派活、收结果、合成答案」的顶层 agent。它自己一般不直接干活，而是协调 subagent。 |
| worker | 工作者 | 执行一个具体子任务的 agent 或进程。在编排语境里常等同于 subagent；在部署语境里指从队列取任务执行的进程（模块 05）。 |
| workflow vs agent | 工作流 vs 智能体 | Anthropic《Building effective agents》的关键区分：workflow 是用**代码**按预定路径编排 LLM 与工具（路径固定、可预测）；agent 是让**模型自己**动态决定下一步（更灵活、更不可控）。多数生产系统是两者的混合。 |
| task decomposition | 任务分解 | 把一个大任务拆成若干可独立完成、可并行或可串联的子任务。是编排的第一步，分得好坏直接决定后续并行度与汇总难度。 |
| synthesis / aggregation | 合成 / 汇总 | 把多个 subagent 的结果合并成一个连贯的最终答案。orchestrator 的收尾工作；简单任务可拼接，复杂任务需要再过一遍 LLM 去整合。 |
| MockLLM | 模拟模型 | 本课用的确定性「假模型」：用规则 / 查表代替神经网络，对给定输入返回可预测的输出。它让整套编排与生产管线无需 API key 即可端到端跑通并被 assert 验证，把学习焦点钉在编排控制流与运维状态机上。 |
| context window | 上下文窗口 | 模型一次能看到的 token 上限。单 agent 的硬墙之一：长任务会塞满它。多 agent 的一大动机正是**用多个隔离的上下文窗口**分担一个超出单窗口的任务。 |
| ReAct loop | ReAct 回路 | 单个 agent 的基本循环：推理（Reason）一句、行动（Act，调工具）一次、看观察、再推理……本课把它当作已有的零件，重点在如何编排和运维由它构成的系统。 |

## Subagent 与上下文隔离 · Subagents & Context Isolation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| spawn | 派生 | orchestrator 创建一个 subagent 去执行子任务的动作。派生时要给它一份明确的任务说明、必要的输入、以及它能用的工具子集。 |
| context isolation | 上下文隔离 | 每个 subagent 拥有自己独立的对话历史 / 上下文，互不污染。隔离的好处：子任务的中间噪声不挤占父 agent 的上下文、各 subagent 可并行、失败可局部隔离。是多 agent 能扩展上下文的根本机制。 |
| result handoff / collect | 结果回传 | subagent 完成后把**结构化结果**（而非整段对话）交还给父 agent。只回传精炼结论而非全部中间过程，是控制父 agent 上下文增长的关键。 |
| fan-out / fan-in | 扇出 / 扇入 | 扇出：orchestrator 同时派生多个 subagent 并行处理互不依赖的子任务；扇入（gather）：等它们全部完成、收集结果。是多 agent 提速的主要手段。 |
| structured result | 结构化结果 | subagent 回传的、约定好字段的结果对象（如 `{subagent_id, task, result, ...}`），而非自由文本。结构化才便于父 agent 程序化地汇总、便于校验、便于归因。 |
| token budget | token 预算 | 分给一个 agent / subagent 的 token 上限。多 agent 系统天然更耗 token（每个 subagent 都有自己的上下文），所以要按子任务难度分配预算、并监控总消耗（与模块 04 相通）。 |
| delegation | 委派 | orchestrator 把一个子任务连同所需上下文交给某个 subagent 去做。委派的说明写得越清楚（目标、边界、输出格式），subagent 跑偏的概率越低。 |
| isolation failure containment | 失败隔离 | 一个 subagent 失败不应拖垮整个编排。好的设计让单个 subagent 的失败被局部捕获、回传一个「失败」结果，由 orchestrator 决定重试、跳过或换路。 |

## 编排模式 · Orchestration Patterns

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pipeline / chaining | 流水线 / 链式 | 把多个步骤串成一条链：上一步的输出是下一步的输入。Anthropic 称 prompt chaining。适合能清晰拆成固定顺序子步骤的任务（如「起草 → 校对 → 翻译」）。 |
| parallelization / fan-out | 并行化 | 把互不依赖的子任务同时分给多个 agent 跑，再汇总。两种形态：sectioning（把任务切成独立块）与 voting（同一任务跑多次取共识）。本课重点实现 sectioning 式 fan-out。 |
| routing | 路由 | 先用一个分类器 / 路由 agent 判断输入属于哪一类，再分派给专门处理该类的下游 agent / 提示。让每条路径都能用最合适、最专精的处理者。 |
| supervisor-worker | 主从 | 一个 supervisor agent 动态决定派生哪些 worker、给什么任务、何时停止；worker 执行并回传。比固定流水线更灵活，是 orchestrator-worker 的「agent 自主」版本。 |
| evaluator-optimizer | 评估-优化 | 一个 agent 产出结果，另一个 agent 评估并给反馈，循环改进直到达标。适合有明确评判标准、且迭代能稳定提升质量的任务（如带评审的写作 / 编码）。 |
| map-reduce | 映射-归约 | 把任务 map 成许多同构子任务并行处理（map / 扇出），再把结果 reduce 成一个汇总（reduce / 合成）。fan-out + synthesis 的经典命名。 |
| DAG / dependency graph | 有向无环图 / 依赖图 | 把子任务及其依赖关系建成一张图：无依赖的可并行、有依赖的须等前驱完成。比线性流水线更通用的编排拓扑；拓扑排序决定执行顺序。 |
| topological sort | 拓扑排序 | 在依赖图上求一个合法的执行顺序：任一任务都排在它依赖的任务之后。是按依赖图调度子任务的基础算法（模块 02 练习）。 |
| handoff | 交接 | 一个 agent 把控制权 / 任务连同上下文交给另一个 agent（如客服 agent 把退款诉求交给退款 agent）。是多 agent 框架（如 OpenAI Swarm）的核心原语，本质是带状态转移的路由。 |

## 权限、沙箱与安全 · Permissions, Sandboxing & Safety

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| permission system | 权限系统 | 决定一个 agent 的某次工具调用准不准执行的那层逻辑。生产 agent 的必备件：模型可以「想」调任何工具，但执行与否由权限系统说了算。模块 03 从零实现它。 |
| allowlist / whitelist | 白名单 | 只允许名单内的工具被调用，名单外一律拒绝（默认拒绝）。比黑名单安全得多——黑名单总会漏掉新出现的危险动作，白名单则把攻击面收敛到你明确批准的集合。 |
| approval gate / human-in-the-loop | 审批门 / 人在回路 | 对高风险 / 不可逆动作（删除、付款、外发、提交）暂停执行、要求人确认后才放行。把「被劫持或判断失误的后果」卡在执行前的最后一道闸。 |
| least privilege | 最小权限 | 只给 agent 完成任务所必需的最小权限集。一个只读检索的 agent 不该有写 / 删 / 外发权限——没有那把刀，被劫持也捅不出血。是 agent 安全最朴素也最有效的原则。 |
| sandbox | 沙箱 | 限制 agent 可执行动作范围的隔离环境 / 策略层。它按权限策略对每个工具调用放行、拦截或转人工，把 agent 能造成的影响圈在一个受控边界内。 |
| permission policy (allow/deny/ask) | 权限策略 | 对每个工具 / 动作的放行规则三态：自动允许（allow）、拒绝（deny）、暂停询问人（ask）。生产 agent 常按工具的「可逆性 / 风险」分级配置这三态。 |
| capability / scope | 能力 / 作用域 | 授予 agent 的一组具体权限（能调哪些工具、能访问哪些资源、能操作哪些路径）。把 capability 设计得细粒度（精确到资源 / 路径而非「全部文件」），是最小权限落地的关键。 |
| privilege escalation / over-permission | 越权 | agent 调用了它本不该有权限调用的工具，或用越权的参数（本该只读却去删除）。可能源于幻觉、注入或目标误解。权限系统的核心职责就是检测并拦截它。 |
| prompt injection | 提示注入 | 攻击者把恶意指令藏进 agent 会读到的内容里（工具返回、子 agent 结果、外部文档），诱导它执行非用户本意的动作。多 agent 系统的注入面更大——一个 subagent 的污染结果可能注入到 orchestrator。 |
| confused deputy | 受蒙蔽的代理 | 一个持有权限的主体（agent）被无权限者（注入内容）诱导去滥用自己的权限。prompt injection 在安全上常被归为此类；权限系统与最小权限正是对它的结构性防御。 |
| dry-run | 演练 | 让 agent 先「不真正执行、只列出它打算做什么」，由人或策略审一遍再决定是否真跑。高风险编排上线前的常用安全实践。 |

## 可观测性与评测 · Observability & Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| observability | 可观测性 | 从一个运行中的 agent 系统外部，能看清它内部发生了什么的程度。对多 agent 尤其关键：一个错误结果背后可能是几十步、跨多个 subagent 的交互，没有可观测性就无从调试与归因。 |
| trace | 追踪 | 一次完整请求 / 任务从开始到结束的端到端记录，由一棵 span 树组成。OpenTelemetry 的核心概念。本课用它记录「orchestrator 分解 → 各 subagent 执行 → 合成」的全过程。 |
| span | 跨度 | trace 里的一个工作单元，有名字、起止时间、属性、以及父子关系。一个 LLM 调用、一次工具调用、一个 subagent 的运行都可以是一个 span。span 嵌套成树，刻画调用结构。 |
| span tree / call tree | span 树 / 调用树 | 由 span 的父子关系构成的树：根 span 是整次任务，子 span 是 orchestrator 的各步与各 subagent，叶 span 是具体的 LLM / 工具调用。读懂这棵树就读懂了一次运行。 |
| trace_id / span_id / parent_id | 追踪/跨度/父 id | 把分散的 span 关联成一棵树的三个 id：同一 trace 的所有 span 共享 trace_id；每个 span 有唯一 span_id；parent_id 指向它的父 span。本课模块 04 用它们从零拼出 span 树。 |
| structured logging | 结构化日志 | 以机器可解析的结构（如 JSON / dict）而非自由文本记录事件，每条带时间、级别、字段。便于按字段过滤、聚合、关联到 trace。是 agent 可观测性的基础。 |
| cost / latency / token tracking | 成本/延迟/token 追踪 | 在每个 span 上记录它消耗的 token 数、花费的时间、对应的钱，再沿 span 树聚合出一次运行的总成本与总延迟。多 agent 系统耗费可能成倍增长，追踪它是控成本的前提。 |
| metric aggregation | 指标聚合 | 把分散在各 span 上的原始数值（token、耗时、调用次数、错误数）按某种维度（按 subagent、按工具、按整次运行）汇总成可读指标。 |
| agent evaluation | 智能体评测 | 衡量 agent / 编排在任务上的能力与可靠性。比单轮评测难：要看多步交互后的最终状态、要能自动判对错、要能区分「会做」与「稳定做对」。本课用 trace 上可断言的不变量做评测。 |
| LLM-as-judge | 模型评判 | 用一个 LLM 去评估另一个 agent 的输出质量（按 rubric 打分）。适合没有程序化判据的开放任务；本课用规则模拟一个判官以保持确定性。 |
| pass^k / reliability | 可靠性 | 连续 k 次独立尝试**全部**成功的概率（≈单次成功率的 k 次方）。衡量 agent 稳不稳定，对生产比「试几次能做出来」更相关。多 agent 的连乘链路尤其要看它。 |
| replay | 回放 | 用记录下来的 trace / 输入重跑一次 agent，以复现某个 bug 或对比不同版本。可观测性产出的 trace 是回放的素材。 |

## 部署与生产化 · Deployment & Production

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| deployment | 部署 | 把一个验证过的 agent 从「能在本地手动跑」变成「能作为服务长期、稳定、自动地接受并处理任务」。本课模块 05 从零搭一个最小但完整的部署骨架。 |
| task queue | 任务队列 | 一个先进先出（或带优先级）的缓冲：提交的任务先入队，worker 再从队列取出执行。它把「接收任务」与「执行任务」解耦，让系统能削峰、能横向扩容（多 worker）、能重试。 |
| worker / consumer | 工作者 / 消费者 | 从任务队列取出任务并执行的进程 / 协程。可以有多个并行消费同一队列。部署语境里的 worker（≠ 编排语境里的 subagent，尽管思想相通）。 |
| producer | 生产者 | 向任务队列提交任务的一方（如一个 HTTP 接口、一个定时器）。生产者只管入队、不管执行，是解耦的另一半。 |
| state machine | 状态机 | 把一个任务的生命周期建成有限状态 + 合法转移：如 `queued → running → succeeded / failed → (retry) → queued`。用状态机管理任务，能精确知道每个任务此刻在哪、下一步能去哪、非法转移要拒绝。 |
| retry with backoff | 重试退避 | 任务失败后再试的策略；指数退避（每次等待翻倍 + 随机抖动）避免大量重试在同一时刻打垮下游。要区分可重试错误（瞬时 / 5xx / 超时）与不可重试错误（参数非法），后者重试无用。 |
| exponential backoff | 指数退避 | 第 k 次重试前等待约 base·2^k 的时间，再叠加随机抖动。让重试间隔随失败次数指数增长，既给下游恢复时间，又用抖动打散「惊群」。 |
| idempotency | 幂等性 | 同一个任务即使被执行多次，效果与执行一次相同。重试与「至少一次」投递下，幂等是避免重复副作用（重复扣款 / 重复发信）的关键保证。 |
| state persistence | 状态持久化 | 把任务与其状态写入可重启后仍存在的存储（本课用内存 dict + JSON 快照模拟，真实里是数据库 / Redis）。让系统崩溃重启后能恢复未完成的任务、不丢状态。 |
| health check / liveness / readiness | 健康检查 | 一个让外部（负载均衡 / 编排系统）探测服务是否存活（liveness）、是否就绪可接流量（readiness）的端点。常报告队列深度、worker 状态、错误率等。是自动运维的眼睛。 |
| graceful shutdown | 优雅停机 | 收到停机信号后，不立刻杀死，而是停止接新任务、等在跑的任务跑完（或安全中止并回队），再退出。避免重启 / 扩缩容时丢任务或留下半完成状态。 |
| circuit breaker | 熔断器 | 当下游连续失败超过阈值时，暂时「断开」、快速失败而不再徒劳调用，给下游恢复时间，过段时间再半开试探。防止级联故障拖垮整个系统。 |
| dead-letter queue | 死信队列 | 专门存放「重试用尽仍失败」任务的队列。把它们隔离出来便于人工排查、不阻塞正常任务，是生产队列系统的标配。 |
| at-least-once / at-most-once | 至少一次 / 至多一次 | 投递语义：至少一次保证不丢但可能重复（需幂等兜底）；至多一次不重复但可能丢。多数任务队列默认至少一次，故幂等性几乎是必修。 |
| concurrency / parallelism | 并发 / 并行 | 同时处理多个任务的能力。本课用顺序模拟以保持确定可断言，但接口（队列 + 多 worker）就是为并发设计的；真实里靠多进程 / 异步 / 多机实现。 |
