# 参考清单 · References（Agent Harness 从零）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用纯标准库 + 自写 MockLLM 模拟的每个机制（循环、工具调用协议、适配器、鲁棒层），都能在下列文献/文档里找到真实系统中的对应实现与设计取舍。

## Agent 范式与推理 · Agent Paradigms & Reasoning
- ★ **Yao, Zhao, Yu, Du, Shafran, Narasimhan & Cao 2022, _ReAct: Synergizing Reasoning and Acting in Language Models_ (arXiv:2210.03629)** — 本课循环范式的奠基论文。提出让模型交替产出「推理（reasoning trace）」与「动作（action）」、再把环境「观察（observation）」喂回，形成 Thought→Action→Observation 链。本课模块 01 的 agent loop 就是它的最小实现；理解它是理解一切 agent 的起点。
- ★ **Anthropic, _Building Effective Agents_（engineering 博客）** — 必读的工程指南。划清 workflow（代码编排步骤）与 agent（模型自主决定步骤）的界线，给出何时该用 agent、如何设计简单可靠的 agent 的原则。本课「先 workflow 思维、确有必要再上 agent」的取舍直接源于它；模块 00/05 反复引用。
- **Wei et al. 2022, _Chain-of-Thought Prompting Elicits Reasoning in Large Language Models_ (arXiv:2201.11903)** — 「让模型先把推理写出来再答」的奠基工作。ReAct 的「reasoning trace」一半血统来自它。理解 CoT 才能理解为什么 agent 要让模型显式 think。
- **Shinn et al. 2023, _Reflexion: Language Agents with Verbal Reinforcement Learning_ (arXiv:2303.11366)** — agent 失败后用自然语言「反思」并改进下次尝试。是把 ReAct 单次轨迹扩展成「带记忆的多次尝试」的代表，指向本课模块 04/05 之后的进阶方向。
- **Yao et al. 2023, _Tree of Thoughts_ (arXiv:2305.10601)** — 把单链推理扩展成搜索树（多分支探索 + 回溯）。展示 agent 决策可以比线性 ReAct 更复杂，是「决策」这一环的前沿之一。

## 工具调用与 Claude Messages API · Tool Use & the Messages API
- ★ **Anthropic, _Tool use (function calling) overview_ — `platform.claude.com/docs/en/agents-and-tools/tool-use/overview`** — 工具调用的官方权威文档。讲清工具定义（`name`/`description`/`input_schema`）、`tool_choice`、以及「助手返回 `tool_use` 块 → 你执行 → 用 `tool_result` 块回传（`tool_use_id` 对应）」的完整协议。本课模块 02/03 的内部消息格式刻意与它同构，遇到协议细节以它为准。
- ★ **Anthropic, _Messages API reference_ — `platform.claude.com/docs/en/api/messages`** — `client.messages.create(model, system, messages, tools, max_tokens)` 的参数与响应结构（`content` 块、`stop_reason`、`usage`）。本课的真实适配器（模块 03）就对接它；理解 `stop_reason=="tool_use"` 是接通 agent 循环与真实 API 的关键一环。
- ★ **Schick et al. 2023, _Toolformer: Language Models Can Teach Themselves to Use Tools_ (arXiv:2302.04761)** — 工具调用的奠基论文之一。提出让模型自监督地学会「何时调用哪个 API、如何填参数、如何把返回值用进生成」。理解它能看清「为什么模型能可靠地产出结构化工具调用」这件事的来龙去脉，是模块 02 的理论背景。
- **Anthropic, _Tool runner & `@beta_tool`_（SDK 文档 / `python/claude-api/tool-use.md`）** — 官方的自动工具循环：用 `@beta_tool` 装饰函数、`client.beta.messages.tool_runner()` 自动跑「调 API→执行工具→回灌→再调」。本课先手写这套循环（模块 01–02），再在模块 03 展示官方现成版，对照着理解。
- **Anthropic, _Handling stop reasons_ — `platform.claude.com/docs/en/build-with-claude/handling-stop-reasons`** — 把 `end_turn`/`tool_use`/`max_tokens`/`pause_turn`/`refusal` 每种停止原因该怎么处理讲透。agent 循环的正确终止与续跑逻辑全靠它，是模块 01/04 的直接依据。

## 适配器、SDK 与可插拔设计 · Adapter, SDK & Pluggability
- ★ **Anthropic Python SDK（`anthropic`，github.com/anthropics/anthropic-sdk-python）** — 真实适配的落地基础。`client.messages.create(...)` 发请求、自动重试 429/5xx（`max_retries` 默认 2、指数退避）、`messages.stream(...)` 流式。本课模块 03/04 的真实路径与重试直觉都对照它；其 `examples/` 目录是最佳实战参考。
- **Gamma et al., _Design Patterns_（适配器模式 / 策略模式那两章）** — 「把具体实现藏在统一接口后、可一行互换」是本课 LLMClient/MockLLM 设计的根。适配器模式解释了为什么换 LLM 提供方只需改一个类；策略模式解释了为什么 LLM 能当参数注入 agent。
- **Anthropic, _Models overview & pricing_ — `platform.claude.com/docs/en/about-claude/models/overview`** — 模型 ID（`claude-opus-4-8` 当前最强、\$5/\$25 每百万 token、1M 上下文）、能力与定价。模块 04 的成本追踪/预算熔断要用到这些真实单价，挑模型时也以它为准。

## 鲁棒性、可靠性与可观测 · Robustness, Reliability & Observability
- ★ **Amazon, _Exponential Backoff And Jitter_（AWS Architecture 博客）** — 退避重试的经典讲解。为什么要指数退避、为什么要加 jitter（避免「重试风暴」同步砸向过载服务）。本课模块 04 的重试实现直接落地它的思想。
- **Google SRE Book, _Handling Overload_ / _Addressing Cascading Failures_ 章** — 从系统视角讲超时、重试、降级、熔断如何共同防止「一个慢调用拖垮整条链路」。把模块 04 的单点鲁棒手段放进系统全局来理解，强烈建议通读这两章。
- **Nygard, _Release It!_（Circuit Breaker、Timeout、Bulkhead 等稳定性模式）** — 生产系统稳定性模式的经典。超时、断路器、舱壁隔离——本课的循环检测、错误隔离、降级都是这些模式在 agent 语境的具体化。
- **Anthropic, _Reducing latency_ / _Error handling_（SDK 与 API 文档）** — 错误码语义（429 rate_limit / 5xx 可重试；400 invalid_request 不可重试）与降低延迟的实务。模块 04 区分「瞬时 vs 永久错误」的判据来源。

## 上下文、记忆与评测 · Context, Memory & Evaluation
- **Anthropic, _Context editing & Compaction_ — `platform.claude.com/docs/en/build-with-claude/context-editing`、`.../compaction`** — 当 agent 多轮累积的 scratchpad 逼近上下文窗口时，如何裁剪旧 tool_result（context editing）或摘要压缩（compaction）。是把本课最小 agent 扩展到长程任务的下一步。
- **Anthropic, _Prompt caching_ — `platform.claude.com/docs/en/build-with-claude/prompt-caching`** — 多轮 agent 把稳定前缀（system + 工具定义）缓存起来可大幅省钱省时。理解「为什么 system 与工具列表要保持稳定」对设计高效 agent 很重要，是模块 03/04 的成本优化背景。
- **Liu et al. 2023, _AgentBench_ (arXiv:2308.03688) / _τ-bench_ 等 agent 评测基准** — 怎样系统地衡量一个 agent 好不好（任务完成率、轨迹质量）。本课用 assert 验证最小 agent 的正确性，是评测的雏形；要严肃评测 agent，这些基准是下一步。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课全程纯标准库 + 自写 MockLLM**：不依赖任何 agent 框架（不装 LangChain/AutoGPT），不需要 API key。每个 agent 都用确定性 MockLLM **端到端真实运行**，并用 `assert` 验证「它确实按预期多步完成了任务」（解析对、分发对、停止对）。这保证你写的循环/工具/适配逻辑**正确**，而非「看起来像」。
- **接真实 API 的可迁移性**：本课内部消息格式与 Anthropic 的 `tool_use`/`tool_result` 块结构**同构**，所以把 `MockLLM` 换成 `AnthropicLLM` 几乎是一行替换。每个 notebook 都附这段真实适配代码：`pip install anthropic`、`export ANTHROPIC_API_KEY=...`，**有 key 就接 `claude-opus-4-8`、没 key 自动回退 MockLLM**，notebook 全程可跑。
- **课程衔接**：上游可配合任何「LLM 基础/prompt 工程」课；下游接「上下文工程 / 长程 agent」「多 agent 协作」「agent 评测与安全」。学完本课，你握住的是所有这些方向共同的地基——一个你亲手造过、彻底理解的 agent harness。
