# 术语词典 · Glossary（Agent Harness 从零）

> 按主题分组，每条 2–3 句释义。读 ReAct / Anthropic「Building effective agents」/ Messages API tool use 文档遇到生词回这里查；英文术语保留原文（社区与官方文档的通用语言）。本课用纯标准库 + 自写 MockLLM 把这些概念从零实现并端到端验证，术语与真实 agent 框架（Claude Code、LangChain、AutoGPT）一一对应。

## Agent 与循环 · Agent & Loop

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agent | 智能体 | 一个把 LLM 放进「循环 + 工具 + 上下文」里的程序，能自主决定下一步动作、调用工具、观察结果、再决定，直到完成任务。注意：agent 不是模型本身，而是围绕模型的那套编排代码——本课造的正是这套代码。 |
| agent harness | agent 运行框架 / 脚手架 | 承载 agent 运行的基础设施：主循环、工具注册与分发、LLM 适配层、上下文管理、错误处理与可观测。Claude Code、LangChain 都是 harness 的实例；本课从零造一个最小但完整的 harness。 |
| agent loop | agent 循环 | 「感知（读取上下文）→ 决策（调用 LLM 选动作）→ 行动（执行工具）→ 观察（把结果写回上下文）」的反复，直到模型决定结束或触发上限。是 agent 区别于单次问答的本质。 |
| perceive-decide-act-observe | 感知-决策-行动-观察 | agent 循环的四个阶段。感知=把当前状态/历史组织成 prompt；决策=LLM 输出一个动作；行动=harness 执行该动作（调工具）；观察=把工具结果回灌进上下文，进入下一轮。 |
| ReAct (Reason + Act) | 推理与行动交替 | Yao 等 2022 提出的 agent 范式：让模型交替产出「思考（reasoning trace）」与「动作（action）」，再把环境返回的「观察（observation）」喂回，形成 Thought→Action→Observation 的链。把推理显式写出来能显著提升多步任务的可靠性与可解释性。 |
| thought / reasoning trace | 思考 / 推理痕迹 | ReAct 里模型在选动作前写下的自然语言推理（如「我需要先查 X 再算 Y」）。它不直接作用于环境，但能引导模型选对动作、也方便人类调试 agent 的决策。 |
| action | 动作 | 模型决定要执行的事：调用某个工具（带参数）或给出最终答案。harness 负责把这个抽象动作落实成真实执行。 |
| observation | 观察 | 环境（工具）对一个动作返回的结果。它被写回上下文，成为模型下一步决策的依据。observation 回灌是 agent 能「闭环」学习当前任务状态的关键。 |
| scratchpad / agent scratchpad | 草稿区 | 把历史的 thought/action/observation 累积起来的那段上下文，喂给模型让它「记得」自己做过什么。本课用一个 messages 列表充当 scratchpad。 |
| stop condition | 停止条件 | 决定循环何时结束的判据：模型给出最终答案（end_turn / Final Answer）、或触发安全上限（max steps / 超预算）。每个 agent 必须有明确的停止条件，否则可能永不停机。 |
| max-steps / max-iterations guard | 最大步数守卫 | 强制循环最多跑 N 步的上限，防止模型陷入「调工具→观察→再调同样的工具」的死循环。是 agent 最基本的安全阀，本课模块 01/04 反复强调。 |
| termination | 终止 | agent 结束运行的统称：正常终止（产出答案）或异常终止（超步数、超预算、不可恢复错误）。harness 必须对每种终止给出明确状态，而非静默卡死。 |
| trajectory / rollout | 轨迹 | 一次 agent 运行从开始到结束经过的完整 (thought, action, observation) 序列。评测、复现、调试 agent 都以轨迹为单位。 |

## 工具与调用协议 · Tools & Calling Protocol

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| tool / function | 工具 / 函数 | agent 能调用的外部能力：计算器、搜索、读写文件、调 API 等。每个工具 = 一个名字 + 一段参数 schema + 一个可执行函数。给 LLM「手脚」靠的就是工具。 |
| tool use / function calling | 工具调用 | LLM 不直接执行动作，而是输出一个结构化的「我要调用工具 X、参数为 {...}」，由 harness 解析并真正执行。现代模型（Claude、GPT）原生支持这种结构化输出。 |
| tool registry | 工具注册表 | 名字 → (可执行函数 + schema) 的映射。注册即「把一个 Python 函数声明成 agent 可用的工具」。分发器据此按名字找到并调用正确的函数。 |
| JSON Schema | JSON 模式 | 用 JSON 声明一个工具参数的类型、必填项、取值范围的标准（`type`/`properties`/`required`/`enum`）。它既告诉模型「这个工具怎么调」，也让 harness 在执行前校验参数合法性。 |
| tool schema / input_schema | 工具模式 / 输入模式 | 一个工具的完整声明：`name`、`description`、`input_schema`（JSON Schema）。description 写得好坏直接决定模型用不用得对——它是模型选工具、填参数的唯一依据。 |
| argument validation | 参数校验 | 执行工具前，按 schema 检查模型给的参数是否齐全、类型是否对、是否在允许范围内。校验失败应返回结构化错误（让模型改），而不是抛异常崩掉整个 agent。 |
| dispatch / dispatcher | 分发 / 分发器 | 拿到一个 tool_use（工具名 + 参数），在注册表里查到对应函数、校验参数、调用、把返回值包装成 observation/tool_result 的过程。是工具系统的执行中枢。 |
| tool_use block | 工具调用块 | 助手消息里表示「我要调用工具」的结构化块，含 `id`、`name`、`input`。Anthropic Messages API 用它来传达模型的工具调用意图。 |
| tool_result block | 工具结果块 | 用户消息里回传工具执行结果的结构化块，含 `tool_use_id`（对应哪个调用）、`content`（结果）、可选 `is_error`。模型据此继续推理。 |
| tool_use_id | 工具调用标识 | 把一次 tool_use 和它对应的 tool_result 关联起来的 id。并行调多个工具时，靠它把每个结果对回正确的调用，绝不能错位。 |
| parallel tool calls | 并行工具调用 | 模型在一条助手消息里一次返回多个 tool_use（彼此独立），harness 可并行执行，再把所有 tool_result 放进**同一条** user 消息回传。能减少往返、提速。 |
| error isolation | 错误隔离 | 工具执行抛异常时，捕获它、包装成带 `is_error=True` 的 tool_result 反馈给模型（让它换法子），而不是让异常冒泡崩掉 agent。是 harness 健壮性的基石。 |
| tool description | 工具描述 | 工具 schema 里的自然语言说明，告诉模型「这个工具做什么、何时该用、参数什么意思」。Anthropic 的建议是把它写得像给新同事的文档一样清楚——它常常比模型本身更影响工具调用质量。 |

## LLM 接口与适配 · LLM Interface & Adapter

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| LLM interface / LLMClient | LLM 接口 | harness 内部对「大脑」的统一抽象，通常是一个 `complete(system, messages, tools) -> 结构化响应` 方法。有了它，agent 循环就不关心背后是 mock 还是真实 API。 |
| adapter | 适配器 | 把某个具体 LLM 提供方（如 Anthropic SDK）的对象/格式，翻译成 harness 内部统一格式（dict）的转换层。换提供方时只改适配器，不动 agent 循环。 |
| MockLLM | 模拟 LLM | 一个返回**预设动作序列**的「假大脑」，不联网、确定性、零成本。用它能让整个 agent 端到端跑起来、用 assert 精确验证循环/工具/停止逻辑，是本课所有测试的基础。 |
| pluggable / dependency injection | 可插拔 / 依赖注入 | 把 LLM 当成一个参数传进 agent，而不是在内部写死。于是 MockLLM 与真实 client 实现同一接口、可一行互换——测试用 mock，上线用真实。 |
| Messages API | 消息 API | Anthropic 调用 Claude 的核心接口（`client.messages.create(model, system, messages, tools, max_tokens)`），输入是消息列表、输出是带 `content` 块与 `stop_reason` 的响应。本课的真实适配就对接它。 |
| system prompt | 系统提示 | 一段放在对话最前、定义 agent 角色与规则的指令（Messages API 的 `system` 字段）。它定调 agent 的行为，且通常保持稳定以利于 prompt 缓存。 |
| stop_reason | 停止原因 | 模型本轮停下来的原因：`end_turn`（自然说完）、`tool_use`（想调工具，等你执行）、`max_tokens`（达到输出上限）、`refusal`（安全拒答）等。agent 循环靠它判断「该执行工具还是该收尾」。 |
| content block | 内容块 | Messages API 响应 `content` 是一个块列表，每块有 `type`：`text`（文字）、`tool_use`（工具调用）、`thinking`（思考）等。解析响应 = 遍历这些块按类型处理。 |
| adaptive thinking | 自适应思考 | Claude 4.6+ 的扩展思考模式（`thinking={"type":"adaptive"}`），让模型自行决定何时、思考多深，无需手工设 token 预算。本课真实适配里推荐开它处理复杂多步任务。 |
| max_tokens | 最大输出 token | 单次请求允许模型生成的最多 token 数。设太小会把输出截断（`stop_reason==max_tokens`）、需重试或调大；agent 多步任务要给足余量。 |
| streaming | 流式输出 | 让模型边生成边逐块返回（SSE），而非等全部生成完。长输出/高 max_tokens 时用流式可避免请求超时，并能实时展示进度。 |

## 鲁棒性与可观测 · Robustness & Observability

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| robustness | 鲁棒性 | agent 在面对瞬时错误、坏输出、超时、幻觉工具名等异常时仍能稳定运转（重试、降级、隔离）而非崩溃的能力。把一个跑通的 demo 变成能用的系统，靠的就是它。 |
| retry with backoff | 退避重试 | 遇到可重试错误（限流、5xx、网络抖动）时，等待一段时间再试，等待时间随失败次数指数增长（如 1s、2s、4s）。给瞬时故障恢复的时间，又不至于雪上加霜地猛打。 |
| exponential backoff | 指数退避 | 退避重试的具体策略：第 n 次重试前等约 `base × 2^n` 秒，常叠加随机抖动（jitter）打散并发重试，避免「重试风暴」同时砸向已过载的服务。 |
| jitter | 抖动 | 在退避等待时间上加的小随机量，让大量客户端的重试时刻错开，避免它们同步重试形成新的洪峰。 |
| transient vs permanent error | 瞬时 vs 永久错误 | 瞬时错误（429 限流、5xx、超时）重试有望成功；永久错误（400 参数非法、401 认证失败）重试也没用、应立刻上报。harness 必须能区分二者，只重试该重试的。 |
| timeout | 超时 | 给单次操作（LLM 调用、工具执行）设的时间上限，超过即放弃并按失败处理。没有超时，一个卡住的调用能让整个 agent 永久挂起。 |
| loop detection | 循环检测 | 发现 agent 在重复同样的（动作, 参数）而毫无进展，判定它陷入死循环并提前止损。常见做法：记录近几步的动作指纹，发现重复就警告或中止。 |
| hallucinated tool | 幻觉工具 | 模型调用了一个**不存在**的工具名（或编造了不存在的参数）。harness 应返回「无此工具，可用工具为 [...]」的结构化错误引导它改正，而不是 KeyError 崩溃。 |
| graceful degradation | 优雅降级 | 当首选路径失败时退而求其次而非彻底失败：如真实 API 不可用就回退 MockLLM、某工具坏了就跳过并告知模型。让系统「带伤可用」。 |
| input validation | 输入校验 | 在执行前检查输入（工具参数、用户请求）是否合法、是否在允许范围。把坏输入挡在执行之前，是错误隔离的上游防线。 |
| observability / tracing | 可观测 / 追踪 | 把 agent 每一步的 thought/action/observation、token 用量、耗时、错误都记录下来，便于事后复盘「它为什么这么做」「钱花在哪」。生产 agent 离不开它。 |
| token usage | token 用量 | 每次 LLM 调用消耗的输入/输出 token 数（响应 `usage` 字段）。累加它能估算成本、也能据此做预算熔断。 |
| cost tracking | 成本追踪 | 按 token 用量 × 单价累计一次运行花了多少钱。Claude Opus 4.8 约 \$5/百万输入、\$25/百万输出 token——多步 agent 很容易把钱花超，必须追踪。 |
| budget cutoff | 预算熔断 | 在调用前预测「再调一次会不会超预算」，若超则提前停止，避免 agent 失控烧钱。是成本维度的安全阀，与 max-steps 互补。 |
| idempotency | 幂等性 | 一个操作执行一次和执行多次效果相同的性质。重试有副作用的工具（如「发邮件」）时若不幂等，可能重复发送——设计可重试工具时要留意。 |

## 工程生态与对照 · Ecosystem & Cross-reference

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Anthropic SDK | Anthropic 软件开发包 | 官方 Python 库 `anthropic`，封装 Messages API；`client.messages.create(...)` 发请求，`@beta_tool` + `client.beta.messages.tool_runner()` 还能自动跑工具循环。本课真实适配基于它。 |
| tool runner | 工具运行器 | Anthropic SDK 的 beta 助手，自动帮你跑「调 API→执行工具→回灌结果→再调」的循环，直到模型不再调工具。等于官方版的 agent loop——本课先手写它，再展示官方现成版。 |
| Claude Code / LangChain / AutoGPT | —— | 主流 agent 框架/产品。它们内部都有本课造的那几样东西（循环、工具系统、适配器、鲁棒层）。学完本课你能读懂它们的源码、知道每个设计取舍为什么这么做。 |
| workflow vs agent | 工作流 vs 智能体 | Anthropic《Building effective agents》的核心区分：workflow 是预先写死步骤编排（可控、可预测）；agent 是让模型自主决定步骤（灵活、但更难控）。多数任务用 workflow 就够，真正需要开放式探索才上 agent。 |
| context window | 上下文窗口 | 模型一次能看到的最大 token 数（Claude Opus 4.8 为 1M）。agent 多轮累积的 scratchpad 会不断变长，逼近窗口时需要裁剪/压缩历史。 |
| context management | 上下文管理 | 控制喂给模型的历史长度的策略：截断旧的 tool_result、压缩（compaction）成摘要、或把状态写进外部记忆。长程 agent 的必备技术。 |
| determinism | 确定性 | 同样输入产生同样输出的性质。MockLLM 是确定性的，所以 agent 测试可复现、assert 可靠；真实 LLM 带随机性，测试它要换思路（评测、快照）。 |
| SPMD / single-source of truth | —— | 工程原则的统称：让「大脑」只有一处接口（LLMClient）、工具只有一处注册（registry），改一处即全局生效。本课 harness 的结构设计处处体现它。 |
