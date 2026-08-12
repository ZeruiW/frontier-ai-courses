# 参考清单 · References（多智能体编排与生产化）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用标准库 + MockLLM 模拟的每个机制，都能在下列文献与规范里找到真实系统上的对应设计与权衡。

## 多智能体编排 · Multi-Agent Orchestration
- ★ **Anthropic, _How we built our multi-agent research system_（工程博客, 2025）** — 本课的灵魂参考。详述一个真实的 orchestrator-worker 多 agent 系统：一个 lead agent 分解研究任务、派生多个 subagent 并行检索、各自隔离上下文、回传结构化结果再合成。讲透了为什么多 agent（用多个上下文窗口分担一个超长任务）、何时多 agent 反而更差、以及 token 消耗、提示工程、评测、生产化的真实权衡。模块 00–02 的范式与模块 04 的评测思路直接源于它，必读。
- ★ **Anthropic, _Building effective agents_（工程博客, 2024）** — 把 agent 系统拆成 workflow（代码编排 LLM，路径固定可控）与 agent（模型自主决定路径）两类，并给出五种可组合的 workflow 模式：prompt chaining（流水线）、routing（路由）、parallelization（并行/扇出）、orchestrator-workers（主从）、evaluator-optimizer（评估-优化）。模块 02 的四大编排模式逐一对应它，且贯穿全课「能用简单方案就别堆 agent」的工程判断。必读。
- ★ **Wu et al. 2023, _AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation_** — 把多 agent 协作抽象成「可对话的 agent」之间的消息传递，支持 group chat、角色分工、人在回路。理解「多 agent = 一组会发消息、各有角色与工具的 agent」这一编排抽象的代表作；本课的 subagent 派生 / 结果回传是它的最小内核。
- **Hong et al. 2023, _MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework_** — 给多 agent 注入「标准作业流程（SOP）」：让不同角色 agent（产品、架构、工程、测试）按软件公司的流程协作，把人类工作流编码进编排。理解「用 SOP 约束多 agent」的方向。
- **Qian et al. 2023, _ChatDev: Communicative Agents for Software Development_** — 一群角色化 agent 通过对话完成软件开发全流程，展示多 agent 流水线在真实任务上的端到端形态。与 MetaGPT 对照看多 agent 分工。
- **OpenAI, _Swarm / Agents SDK：handoffs & routines_（开源框架与文档）** — 把多 agent 编排归结为两个原语：routine（一组指令 + 工具）与 handoff（把对话连同上下文交接给另一个 agent）。理解「交接式编排」与本课「派生/路由式编排」的异同。

## Agent 推理范式（背景）· Agent Reasoning (Background)
- ★ **Yao et al. 2022, _ReAct: Synergizing Reasoning and Acting in Language Models_** — 单个 agent 的基础回路：交替「推理」与「行动（调工具）」。本课把它当作已有的零件——每个 subagent / worker 内部就是一个 ReAct 回路，重点在如何编排和运维由它们构成的系统。
- **Shinn et al. 2023, _Reflexion: Language Agents with Verbal Reinforcement Learning_** — 让 agent 失败后用自然语言反思、把教训写进下一次尝试。模块 02 的 evaluator-optimizer 模式与模块 05 的重试思想都与之相通——「评估 → 反馈 → 再试」。
- **Anthropic, _Tool use (function calling) with the Claude API_（官方文档）** — 工具调用的权威接口：`input_schema`、`tool_use` / `tool_result` 内容块、`tool_choice`、并行工具调用、`is_error` 错误回传。本课每个 agent 内部的工具调用、模块 03 的权限拦截层都对标它。

## 权限、沙箱与安全 · Permissions, Sandboxing & Safety
- ★ **Greshake et al. 2023, _Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection_** — 系统化「间接提示注入」：恶意指令藏在 agent 主动取来的外部内容里，劫持其行为。多 agent 系统的注入面更大（一个 subagent 的污染结果会注入到 orchestrator），模块 03 的权限边界正是对它的结构性防御。必读。
- ★ **Ruan et al. 2023, _Identifying the Risks of LM Agents with an Emulated Sandbox (ToolEmu)_** — 用 LLM 模拟工具执行，在不接真实危险工具的前提下廉价暴露 agent 的高风险行为。本课「用 MockLLM / 规则模拟工具与危险动作来测安全」正是这一思路的教学版，模块 03 的越权检测与沙箱直接呼应它。
- **Debenedetti et al. 2024, _AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses_** — 专门评测 agent 在含注入的环境里完成任务的能力与被攻破率，配套攻击 / 防御套件。把模块 03 的权限防御放到可量化的攻防框架里。
- **Anthropic, _Claude Code / Computer use 的权限与沙箱实践（相关文档）_** — 真实 agent 产品如何做工具白名单、写 / 执行前的人工确认、沙箱化与禁区。模块 03 的审批门与白名单的工程对照。
- **The Confused Deputy Problem（经典安全文献，Hardy 1988）** — 「受蒙蔽的代理」问题的源头：一个有权限的程序被诱导替无权限者行事。理解 prompt injection 为什么在本质上是个经典权限问题，以及为什么最小权限是结构性解药。

## 可观测性与评测 · Observability & Evaluation
- ★ **OpenTelemetry Specification（opentelemetry.io）+ GenAI semantic conventions** — 分布式追踪的事实标准：trace / span、trace_id / span_id / parent_id、span 的属性与事件、以及面向 LLM/agent 的语义约定（记录模型、token 数、成本等）。模块 04 从零拼的 span 树直接复现它的数据模型，遇到字段分歧以它为准。必读。
- **Dapper（Sigelman et al. 2010, Google）** — 分布式追踪的奠基论文，提出 trace / span / 因果关联的核心抽象，是 OpenTelemetry 的思想源头。理解「为什么追踪是树、为什么要传播 trace 上下文」的根。
- **LangSmith / Langfuse / Arize Phoenix（LLM 可观测平台文档）** — 专门为 LLM / agent 应用做的 tracing 与评测平台：可视化 span 树、聚合 token 与成本、跑评测集、做回放与对比。模块 04 实现的 tracing + 成本聚合 + 评测，就是这类平台的可运行最小内核。
- **Yao et al. 2024, _τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains_** — 在真实领域评测 agent 与「用户 + 工具 + 规则」交互，用 pass^k 衡量可靠性。模块 04 的「看最终状态 + 可断言评测 + pass^k」直接源于它。
- **Anthropic, _Building effective agents_ 附录 / agent 评测部分** — 评测 agent 的实践要点：用真实任务、看端到端结果、关注可靠性而非单步分数。与模块 04 的评测设计一致。

## 部署与生产化 · Deployment & Production
- ★ **Nygard, _Release It! Design and Deploy Production-Ready Software_（第 2 版）** — 生产化的经典：重试与退避、超时、熔断器（circuit breaker）、舱壁隔离（bulkhead）、稳定性与容量模式。模块 05 的重试退避、健康检查、熔断思想取自它，遇到稳定性设计分歧以它为准。必读。
- **Kleppmann, _Designing Data-Intensive Applications_（相关章节）** — 任务队列、消息投递语义（at-least-once / at-most-once）、幂等性、状态持久与一致性的系统性论述。模块 05 的队列 + 状态机 + 幂等设计的理论依据。
- **Google SRE Book（sre.google）— 相关章节** — 健康检查（liveness / readiness）、优雅停机、负载管理、错误预算的工程实践。模块 05 的健康探针与运维状态机的现实对照。
- **Celery / Sidekiq / Temporal（任务队列与工作流引擎文档）** — 真实的任务队列与持久化工作流系统：入队 / worker / 重试 / 死信队列 / 状态持久 / 可见性超时。模块 05 用内存模拟的队列 + worker + 重试 + 持久，就是这类系统的最小骨架。
- **Anthropic, _Claude Agent SDK / Messages API_（官方文档）** — 把验证过的 scaffold 接到真实 Claude 的可执行接口：`messages.create`、`model='claude-opus-4-6'/'claude-opus-4-8'`、tools、流式、停止原因。本课刻意让 MockLLM 的输入输出贴近它的形状，并提供无 key 自动回退到 MockLLM 的适配器，学完照着把验证过的编排 / 部署骨架接到真实模型是最自然的下一步。

## 真实数据与接口来源 · Real Data & Interfaces
- **Anthropic Messages API（`claude-opus-4-8` 等）** — 本课所有 agent 内核的真实模型接口。`05_deploy/agent_cli.py` 提供了一个最小的真实适配器：有 `ANTHROPIC_API_KEY` 用真实 Claude，无 key 自动回退到 MockLLM，绝不阻断学习。
- **OpenTelemetry GenAI conventions（语义约定）** — 真实里记录一次 LLM 调用该带哪些字段（模型名、输入/输出 token、成本、首 token 延迟…）的权威清单。模块 04 的 span 属性贴近它。
- **τ-bench / AgentDojo 数据集** — 真实的多步 agent 任务 / 含注入环境，是模块 03–04「评测可靠性与安全」最权威的真实数据来源。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU、无需任何 API key**：全课用标准库 + **MockLLM**（确定性假模型）在 CPU 上端到端模拟多 agent 编排与生产管线——subagent 派生 / 隔离 / 扇出、orchestrator 的四大编排模式、权限白名单 / 审批 / 沙箱 / 越权检测、trace/span 树与成本聚合与评测、内存队列 + worker + 状态机 + 重试退避 + 持久 + 健康检查。每个零件都与明确不变量对拍、用 `assert` 兜底，保证你写的**编排控制流与运维状态机逻辑正确**。
- **可迁移性**：你在 MockLLM 上验证过的编排 / 权限 / 追踪 / 部署骨架，可几乎一对一换成真实 Claude——把 `MockLLM(...)` 换成真实 `messages.create(...)`（`model='claude-opus-4-8'`）即可。本课刻意让形状贴近真实接口，并给出无 key 自动回退的适配器。
- **课程衔接**：上游接讲「前沿智能体（工具调用 / MCP / computer use / agentic RL / 评测安全）」的课程（C26）；本课从「会写一个 agent」推进到「会把多个 agent 编排成系统、并把它部署进生产」，是 agent 工程从「单体」到「系统」的关键一跃。
