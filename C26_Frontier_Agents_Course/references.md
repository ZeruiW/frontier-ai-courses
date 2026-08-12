# 参考清单 · References（前沿智能体）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy / 标准库 + MockLLM 模拟的每个机制，都能在下列文献与规范里找到真实系统上的对应设计与权衡。

## 工具调用与协议 · Tool Use & Protocols
- ★ **Anthropic, _Tool use (function calling) with the Claude API_（官方文档）** — 工具调用的权威接口定义：`input_schema`（JSON Schema）、`tool_use` / `tool_result` 内容块、`tool_choice`（auto/any/tool/none）、并行工具调用、`is_error` 错误回传、strict 结构化输出。本课模块 01 从零模拟的工具注册表、schema 校验、并行调用、错误重试，全部对标它，遇到字段分歧以它为准。
- ★ **Anthropic, _Model Context Protocol (MCP) specification & docs_（modelcontextprotocol.io）** — MCP 的权威规范：host/client/server 架构、resources/tools/prompts 三类能力、基于 JSON-RPC 2.0 的 `initialize` 握手与能力协商、`tools/list`·`tools/call`·`resources/list`·`resources/read` 方法、stdio / Streamable HTTP 传输。模块 02 从零写的 mini MCP 直接复现它的消息流。必读。
- ★ **Schick et al. 2023, _Toolformer: Language Models Can Teach Themselves to Use Tools_** — 证明「工具使用」可以被自监督地训练进模型本身：模型自己决定在文本何处插入哪个 API 调用、怎么填参数、并用「调用是否降低后续 loss」筛选。理解「工具调用是一种可学习的能力，而不止靠提示」的奠基论文。
- **OpenAI, _Function calling_（官方文档）** — 与 Anthropic tool use 平行的接口（字段名 `parameters` / `tool_calls`），对照阅读能看清两家在同一抽象下的命名差异，帮助你写出可移植的 scaffold。
- **JSON-RPC 2.0 Specification（jsonrpc.org）** — MCP 传输层所用的极简 RPC 规范：请求/响应/通知的字段、错误码。模块 02 实现消息编解码时的字典级依据。
- **JSON Schema Specification（json-schema.org）** — 工具参数约束所用的标准。理解 `type`/`properties`/`required`/`enum`/`additionalProperties` 等关键字，是写对 schema 校验器的基础。

## Agent 框架与推理范式 · Agent Frameworks & Reasoning
- ★ **Yao et al. 2022, _ReAct: Synergizing Reasoning and Acting in Language Models_** — 提出「推理 + 行动」交替的范式：先写一句思考再调一个工具，把思维链与工具使用编织起来。是当代几乎所有工具调用 agent 的基础模板，模块 01 的循环即 ReAct 的最小实现。
- ★ **Shinn et al. 2023, _Reflexion: Language Agents with Verbal Reinforcement Learning_** — 让 agent 失败后用自然语言反思、把教训写进下一次尝试的上下文，实现不更新权重的「言语强化学习」。理解「上下文即可塑性」的代表作，也是 agentic RL 的轻量替身。
- **Wang et al. 2024, _Executable Code Actions Elicit Better LLM Agents (CodeAct)_** — 主张让 agent 直接输出可执行代码作为动作，用代码的表达力统一并扩展动作空间，比固定 JSON 工具调用更灵活。理解「动作空间设计」的一个重要方向。
- **Anthropic, _Building effective agents_（工程博客）** — 把 agent 模式拆成 workflow（代码编排）与 agent（模型自主）两类，给出何时该用更简单的方案。建立「不要为了 agent 而 agent」的工程判断，贯穿全课。

## Computer Use 与 GUI agent · Computer Use
- ★ **Anthropic, _Developing a computer use model_ / _Computer use (beta)_ 文档** — Claude computer use 的设计与接口：截图→动作循环、坐标 grounding、`click`/`type`/`scroll`/`key` 动作、以及安全注意事项。模块 03 的模拟 GUI 环境与动作循环对标它。
- **OpenAI 2025, _Operator / Computer-Using Agent (CUA)_** — 另一条 computer use 路线，强调在真实浏览器/桌面上自主操作与必要的人类确认。与 Anthropic 方案对照，理解 GUI agent 的共性难点（grounding、终止、安全）。
- **Zheng et al. 2024, _GPT-4V(ision) is a Generalist Web Agent if Grounded (SeeAct)_** — 系统研究「视觉模型当网页 agent」时 grounding 是主要瓶颈，并比较截图坐标 vs 元素选择两种 grounding 方式。模块 03「坐标映射 / grounding」一节的现实依据。
- **Xie et al. 2024, _OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments_** — 真实操作系统环境下的 GUI agent 基准，揭示当前模型在多步桌面任务上的真实成功率（远低于人类）。理解 computer use 还有多远。

## Agentic RL 与编码 agent · Agentic RL & Coding Agents
- ★ **Jimenez et al. 2023, _SWE-bench: Can Language Models Resolve Real-World GitHub Issues?_** — 用真实 issue + 单元测试构成编码 agent 基准，把「可验证奖励」落到真实软件工程上。是当前编码 agent 训练与评测的事实标准，模块 04 的「测试通过=奖励」即其精神。
- ★ **Yang et al. 2024, _SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering_** — 证明「给 agent 设计什么样的命令接口（ACI）」对成功率影响巨大——面向 agent 的文件/编辑/执行命令远优于裸 shell。把「scaffold 设计本身就是能力」讲透。
- ★ **Zelikman et al. 2022, _STaR: Self-Taught Reasoner_** — 拒绝采样自举的奠基：采样多条推理、只留答对的、用它们再微调、迭代。模块 04「reject sampling / best-of-n」一节的思想源头，是 RL 之外用可验证奖励改进 agent 的简单强力路线。
- **Sutton & Barto, _Reinforcement Learning: An Introduction_（第 2 版，相关章节）** — 策略梯度、回报与折扣、信用分配、基线/优势的标准教材。模块 04 的玩具 REINFORCE 与优势基线即取自这里，遇到 RL 概念分歧以它为准。
- **Schulman et al. 2017, _Proximal Policy Optimization (PPO)_** — 当代 RLHF / agentic RL 最常用的策略优化算法。本课只实现最朴素的 REINFORCE 以看清机制，PPO 是把它工程化、稳定化的下一步。

## Agent 评测与安全 · Evaluation & Safety
- ★ **Yao et al. 2024, _τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains_** — 在航司/零售客服等真实领域评测 agent 与「用户+工具+规则」交互，并用 **pass^k** 衡量可靠性，暴露「单次看着行、多次重试就崩」的生产脆弱。模块 05 的 pass^k 与可靠性曲线直接源于它。
- ★ **Greshake et al. 2023, _Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection_** — 系统化「间接提示注入」：恶意指令藏在 agent 主动取来的外部内容里，劫持其行为。理解 agent 头号安全威胁的奠基论文，模块 05 注入攻防的依据。
- ★ **Ruan et al. 2023, _Identifying the Risks of LM Agents with an Emulated Sandbox (ToolEmu)_** — 用 LLM 模拟工具执行，在不接真实危险工具的前提下廉价地暴露 agent 的高风险行为，给出风险评测方法。模块 05「不接真实危险工具也能测安全」的范例。
- **Debenedetti et al. 2024, _AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses_** — 专门评测 agent 在含注入的环境里完成任务的能力与被攻破率，配套攻击/防御套件。把模块 05 的注入攻防放到可量化的框架里。
- **Liu et al. 2023, _AgentBench: Evaluating LLMs as Agents_** — 跨多类环境（OS、数据库、网页、游戏…）评测 LLM 的 agent 能力，给出横向对比方法。理解 agent 评测的多样性与难度。
- **Anthropic, _Mitigating prompt injection / Agent safety_（相关文档）** — 防注入与 agent 安全的工程实践清单：数据/指令分离、最小权限、确认高危动作、监控。模块 05 防御部分的工程对照。

## 真实数据与接口来源 · Real Data & Interfaces
- **HuggingFace Datasets：`glaiveai/glaive-function-calling-v2`** — 真实的函数调用对话数据（含工具 JSON schema 与模型产生的调用），可用来对照本课 MockLLM 产出的调用格式与真实分布。
- **`princeton-nlp/SWE-bench`（HuggingFace / 官网）** — SWE-bench 的真实任务实例（repo、issue、测试补丁），是模块 04「测试即奖励」最权威的真实数据来源。
- **Anthropic / OpenAI 官方 SDK 与 API 文档** — tool use / function calling / computer use 的可执行真实接口。本课刻意让 MockLLM 的输入输出贴近它们的形状，学完照着把验证过的 scaffold 接到真实模型是最自然的下一步。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU、无需任何 API key**：全课用 numpy / 标准库 + **MockLLM**（确定性假模型）在 CPU 上端到端模拟 agent 管线——工具注册表与 schema 校验、mini MCP 的 JSON-RPC 握手、computer-use 的截图→动作循环、玩具 agentic RL 的轨迹采样与策略更新、注入攻防与 pass^k。每个内核都与朴素参考对拍、用 `assert` 兜底，保证你写的**协议与控制流逻辑正确**。
- **可迁移性**：你在 MockLLM 上验证过的 scaffold（工具定义、循环、校验、护栏、评测），可几乎一对一换成真实 Anthropic / OpenAI / MCP 接口——把 `MockLLM(...)` 换成真实 `messages.create(...)` 即可。本课刻意让形状贴近真实接口。
- **课程衔接**：上游接讲 Transformer / 工具与函数调用基础的课程；与本系列的「推理服务」「长上下文」「评测」「对齐与安全」诸课互补——agent 是它们的集大成应用场景。
