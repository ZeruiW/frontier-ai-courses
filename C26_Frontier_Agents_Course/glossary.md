# 术语词典 · Glossary（前沿智能体）

> 按主题分组，每条 2–3 句中文释义、英文术语保留。读 Anthropic / OpenAI 的 tool-use 文档、MCP 规范、computer use / SWE-agent / τ-bench 论文遇到生词回这里查。本课用纯 numpy / 标准库 + MockLLM 在 CPU 上模拟这些机制，但术语与真实 agent 系统一一对应。

## Agent 范式与控制流 · Agent Paradigm & Control Flow

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agent | 智能体 | 一个能感知环境、自主决策并采取行动、跨多步完成任务的系统。当代语境里通常指：一个 LLM 在循环中反复「看观察 → 想 → 调工具 → 看结果」，直到任务完成。与「一次问答」的根本区别是它有状态、有循环、能改变外部世界。 |
| agentic loop | 智能体循环 | agent 的核心控制流：模型输出动作（工具调用）→ 环境执行并返回观察 → 把观察喂回模型 → 模型输出下一个动作，循环往复直至终止。本课每个模块都在实现这个循环的不同变体。 |
| perceive-act loop / sense-think-act | 感知-动作循环 | agent 范式的更一般表述：观察（perceive）→ 决策（think）→ 行动（act）→ 新观察。源自经典 AI 与机器人学，LLM agent 是它的语言版本。 |
| ReAct | —— | Yao 等 2022 提出的范式：让模型交替产生「推理（Reasoning）」与「行动（Acting）」——先写一句思考再调一个工具，把思维链与工具使用编织在一起。是当代工具调用 agent 的基础模板。 |
| Reflexion | —— | Shinn 等 2023：让 agent 在失败后用自然语言「反思」哪里错了，把反思写进下一次尝试的上下文，实现「言语强化学习」（不更新权重，只更新提示）。 |
| trajectory / rollout | 轨迹 | agent 完成一次任务过程中产生的完整序列：观察、思考、动作、观察……直到终止。是 agentic RL 的基本训练单位，奖励通常只在轨迹末尾给出。 |
| episode | 回合 | 一次从初始状态到终止的完整交互。一条轨迹对应一个 episode。 |
| horizon | 时域 / 步数 | 一个任务从开始到完成需要的步数。LLM agent 的难点之一是 long horizon（长程）：几十上百步里任何一步出错都可能让整条轨迹失败。 |
| state / observation | 状态 / 观察 | 状态是环境的完整内部情况；观察是 agent 实际看到的部分（如一段工具输出、一张截图）。多数 agent 任务是部分可观察的（POMDP）。 |
| action space | 动作空间 | agent 在每一步可选的动作集合。在工具调用里是「可用工具 × 合法参数」；在 computer use 里是 click/type/scroll/key 等 GUI 动作。 |
| terminal / termination | 终止 | 循环何时停：任务完成、达到最大步数、模型主动声明结束、或触发护栏。设计可靠的终止条件是写 agent 循环的关键，漏掉会导致死循环或提前放弃。 |
| scaffolding / harness | 脚手架 / 框架壳 | 包裹 LLM 的那层代码：解析模型输出、执行工具、管理循环与上下文、施加护栏。同一个模型配不同 scaffold，能力可能天差地别——本课很大程度上就是在教写 scaffold。 |
| system prompt | 系统提示 | 注入在对话最前、定义 agent 角色、可用工具、行为约束的指令。是 agent 行为的「宪法」，也是 prompt injection 想要绕过的对象。 |
| context window | 上下文窗口 | 模型一次能看到的 token 上限。长程 agent 会塞满它，于是需要上下文管理（裁剪旧观察、压缩历史、写入外部记忆）。 |
| MockLLM | 模拟模型 | 本课用的确定性「假模型」：用规则/查表代替神经网络，对给定输入返回可预测的工具调用或文本。它让整套 agent 管线无需 API key 即可端到端跑通并被 assert 验证，把学习焦点钉在协议与控制流上。 |

## 工具调用与 Schema · Tool / Function Calling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| function calling / tool use | 函数调用 / 工具使用 | 让 LLM 输出一个结构化的工具调用（工具名 + 参数对象），由外部代码执行后把结果喂回模型。是 agent 与世界交互的主通道；Anthropic 称 tool use，OpenAI 称 function calling，本质一致。 |
| tool definition | 工具定义 | 提供给模型的工具描述：名称、自然语言说明、以及参数的 JSON Schema（`input_schema`）。模型靠它决定「何时调、怎么填参数」，所以描述质量直接决定调用质量。 |
| JSON Schema | —— | 用 JSON 声明数据结构的标准：类型（string/integer/object…）、必填字段（required）、枚举（enum）、嵌套（properties）等。工具参数用它来约束，是参数校验的依据。 |
| input_schema / parameters | 参数模式 | 工具定义里描述参数的那段 JSON Schema。Anthropic 字段名是 `input_schema`，OpenAI 是 `parameters`，内容都是一个 JSON Schema 对象。 |
| tool_use block | 工具调用块 | 模型输出里表示「我要调这个工具」的结构化片段，含工具名、唯一 id、参数对象。Anthropic 的响应 `content` 里以 `type:"tool_use"` 出现。 |
| tool_result block | 工具结果块 | 把工具执行结果回传给模型的结构化片段，用 `tool_use_id` 与对应调用配对；失败时带 `is_error:true`。一条用户消息里要包含本轮所有工具结果。 |
| argument validation | 参数校验 | 在真正执行工具前，检查模型给的参数是否符合 schema（类型对不对、必填全不全、枚举值合不合法）。校验不过应回错误让模型改，而非崩溃——这是 agent 鲁棒性的第一道防线。 |
| parallel tool calls | 并行工具调用 | 模型在一次响应里同时请求多个互不依赖的工具调用。应并发执行、把全部结果放进同一条结果消息回传；拆成多条会让模型「学会」少做并行。 |
| tool_choice | 工具选择策略 | 控制模型是否/必须用工具的开关：`auto`（自己决定）、`any`（必须用某个）、`tool`（强制用指定的某个）、`none`（禁止）。 |
| tool registry / dispatch | 工具注册表 / 分发 | scaffold 里维护「工具名 → 可执行函数 + schema」的映射，并按模型给的名字把调用路由到对应函数。本课模块 01 从零实现它。 |
| strict mode / structured output | 严格模式 / 结构化输出 | 让模型输出严格符合给定 JSON Schema 的机制（如 `strict:true`），从生成侧保证参数合法，减少校验失败。 |
| Toolformer | —— | Schick 等 2023：让模型通过自监督学会「在文本里何处插入 API 调用、调哪个、怎么填」，证明工具使用能力可以被训练进模型本身，而不止靠提示。 |
| hallucinated tool / argument | 工具/参数幻觉 | 模型调用不存在的工具，或给出不符合 schema 的参数。好的 scaffold 用「未知工具→报错」「校验失败→报错并要求改」把幻觉挡在执行之外。 |
| retry / backoff | 重试 / 退避 | 工具失败（瞬时错误、超时）后再试的策略；指数退避（每次等待翻倍 + 随机抖动）避免雪崩。区分可重试错误（5xx/超时）与不可重试错误（参数非法）很重要。 |

## MCP 模型上下文协议 · Model Context Protocol

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MCP (Model Context Protocol) | 模型上下文协议 | Anthropic 2024 提出的开放标准，统一「AI 应用」与「外部工具/数据源」的对接方式。把过去 M 个应用 × N 个工具的 M×N 集成爆炸，收敛成大家都讲同一种协议的 M+N。 |
| host | 宿主 | 跑 LLM、面向用户的应用（如 Claude Desktop、IDE 插件）。它在内部为每个外部 server 创建一个 client，并把各 server 暴露的能力汇总给模型。 |
| MCP client | MCP 客户端 | host 内部、与某一个 server 一对一连接的连接器。负责握手、能力协商、转发列举/调用请求。 |
| MCP server | MCP 服务端 | 暴露具体能力（工具/资源/提示）的独立进程或服务。一个 server 专注一类能力（如文件系统、GitHub、数据库），可被任意支持 MCP 的 host 复用。 |
| resources | 资源 | MCP server 暴露的、可被读取的（通常只读）上下文数据，用 URI 寻址（如 `file:///path`）。模型/应用可列举并读取它们作为上下文。 |
| tools (MCP) | 工具 | MCP server 暴露的、可被模型调用以产生副作用或取数的操作，每个带名称、说明与 `inputSchema`。语义与 function calling 的工具一致，只是经协议暴露。 |
| prompts (MCP) | 提示模板 | MCP server 暴露的可复用提示模板（可带参数），供 host 以「斜杠命令」等形式呈现给用户。 |
| capability negotiation | 能力协商 | 握手阶段 client 与 server 互相声明各自支持的能力（是否提供 tools/resources/prompts、协议版本等），据此决定后续可用的交互。 |
| JSON-RPC 2.0 | —— | MCP 的传输消息格式：请求含 `jsonrpc`/`id`/`method`/`params`，响应含 `id`/`result` 或 `id`/`error`；无 `id` 的是通知（notification）。本课模块 02 从零实现它。 |
| initialize / initialized | 初始化握手 | MCP 连接的第一步：client 发 `initialize`（带协议版本与能力），server 回能力，client 再发 `initialized` 通知确认。之后才能列举与调用。 |
| transport (stdio / HTTP) | 传输层 | MCP 消息怎么传：本地 server 常用 stdio（标准输入输出管道）；远程用 Streamable HTTP / SSE。协议内容与传输无关。 |
| tools/list · tools/call | 列举 / 调用 | MCP 的两个核心方法：`tools/list` 让 client 发现 server 有哪些工具及其 schema；`tools/call` 携带工具名与参数请求执行，server 回结果。`resources/list`·`resources/read` 同理用于资源。 |

## Computer Use 与 GUI agent · Computer Use

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| computer use | 计算机使用 | 让模型像人一样操作图形界面：看屏幕截图、移动鼠标点击、敲键盘，从而使用任意软件而非只调专用 API。Anthropic 2024 与 OpenAI Operator 2025 是代表。 |
| screenshot-action loop | 截图-动作循环 | computer use 的核心循环：截一张屏 → 模型据图输出一个动作（点哪、打什么字）→ 执行 → 再截一张屏看结果，循环往复。是「感知-动作循环」在 GUI 上的具体化。 |
| grounding | 落地 / 定位 | 把模型的高层意图（「点登录按钮」）映射到具体的屏幕像素坐标 `(x,y)`。grounding 不准是 GUI agent 失败的主因之一。 |
| bounding box | 包围盒 | 一个 UI 元素在屏幕上占据的矩形坐标范围 `(x1,y1,x2,y2)`。其中心点常被用作点击目标。 |
| action space (GUI) | 动作空间（GUI） | GUI agent 可发的动作集合：`click(x,y)`、`type(text)`、`scroll(dx,dy)`、`key(combo)`、`wait`、`screenshot` 等。动作要被解析成结构化形式才能执行。 |
| coordinate mapping | 坐标映射 | 截图分辨率与真实屏幕分辨率不一致时，把模型在缩放图上给的坐标换算回真实坐标。换算错位会点偏。 |
| accessibility tree / DOM | 无障碍树 / DOM | 界面的结构化表示（元素、角色、文本）。有的 GUI agent 用它替代或补充截图，定位更精确但不总是可得。 |
| guardrail / safety check | 护栏 / 安全检查 | 在执行动作前的检查：高风险动作（删除、付款、提交表单）要求确认；禁止越界点击；限制可操作的应用范围。防误操作与防被注入劫持的关键。 |
| human-in-the-loop | 人在回路 | 对不可逆或高风险动作，暂停并等人确认后再执行。computer use 与高权限 agent 的标准安全实践。 |

## Agentic RL 与编码 agent · Agentic RL & Coding Agents

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agentic RL | 智能体强化学习 | 在 agent 的多步轨迹上做强化学习：奖励通常稀疏（只在任务成功时给）、时域长、动作是「调工具/写代码」。与单步 RLHF 的关键区别是要处理「整条轨迹的成败如何归因到中间动作」。 |
| reward | 奖励 | 衡量一条轨迹好坏的标量信号。编码 agent 常用「单元测试是否通过」「任务是否完成」作为可自动验证的奖励——这类可程序化检验的奖励是 agentic RL 能 scale 的前提。 |
| outcome reward / verifiable reward | 结果奖励 / 可验证奖励 | 只看最终结果对不对的奖励（如测试全过=1，否则=0），不依赖人工打分。可自动、客观、可大规模生成，是当前编码/数学 agent RL 的主流。 |
| credit assignment | 信用分配 | 把整条轨迹的最终成败归因到沿途各个动作：哪几步是关键、哪几步无关。长程稀疏奖励下这是核心难题，是 RL 比模仿学习难的根本原因。 |
| return / discounted return | 回报 / 折扣回报 | 从某一步往后累计的（可折扣）奖励 $G_t=\sum_k \gamma^k r_{t+k}$。折扣因子 $\gamma\in(0,1]$ 让近期奖励权重更高，也保证无限时域收敛。 |
| policy | 策略 | 从状态到动作（分布）的映射，即 agent 的「大脑」。LLM 本身就是策略：给定上下文，输出下一个动作的概率分布。 |
| policy gradient / REINFORCE | 策略梯度 | 直接对策略参数求「期望回报」的梯度并上升：$\nabla J=\mathbb{E}[G_t\nabla\log\pi(a_t\vert s_t)]$。直觉是「让得到高回报的动作概率更大」。本课用它的最朴素形式演示轨迹级更新。 |
| baseline / advantage | 基线 / 优势 | 从回报里减去一个基线（如平均回报）得到优势 $A=G-b$，降低策略梯度的方差。优势为正的动作被强化、为负的被抑制。 |
| rejection sampling / best-of-n | 拒绝采样 / 取优 | 对同一任务采样多条轨迹，只保留成功（高奖励）的那些，用它们做监督微调（即 reject sampling fine-tuning / STaR 式自举）。是 RL 之外另一条用可验证奖励改进 agent 的简单路线。 |
| pass@k | —— | 评测指标：对一个任务采样 k 次，只要有一次成功就算通过。衡量「多试几次能不能做出来」，对应有验证器可挑选的场景。 |
| pass^k | —— | 可靠性指标：连续 k 次独立尝试**全部**成功的概率（≈ 单次成功率的 k 次方）。衡量「能不能稳定做对」，对生产 agent 比 pass@k 更苛刻、更相关。 |
| SWE-bench | —— | Jimenez 等 2023：用真实 GitHub issue + 对应单元测试构成的编码 agent 基准，要求 agent 改代码让测试通过。把「可验证奖励」落到真实软件工程任务上。 |
| SWE-agent | —— | Yang 等 2024：为编码 agent 设计的「agent-计算机接口（ACI）」，证明给 LLM 一套精心设计的、面向 agent 的文件/编辑/执行命令，比直接给 shell 更高效。 |
| CodeAct | —— | Wang 等 2024：让 agent 直接输出可执行代码作为「动作」（而非固定 JSON 工具调用），用代码的表达力统一动作空间。 |
| sparse vs dense reward | 稀疏 vs 稠密奖励 | 稀疏：只在终点给一次（任务成败）；稠密：沿途多次给（每步小反馈）。agent 任务多为稀疏奖励，这正是信用分配难的来源。 |

## Agent 评测与安全 · Evaluation & Safety

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agent evaluation | 智能体评测 | 衡量 agent 在多步任务上的能力与可靠性。比单轮评测难：要构造可复现的环境、可自动验证的成功判据、并区分「会做」（pass@k）与「稳定做对」（pass^k）。 |
| tau-bench / τ-bench | —— | Yao 等 2024：在真实领域（航司、零售客服）里评测 agent 与「用户 + 工具 + 规则」交互完成任务的基准。强调用 pass^k 衡量可靠性——多次重试是否都成功，揭示 agent 在生产中的脆弱。 |
| reliability | 可靠性 | agent 稳定完成任务的程度。若单步成功率 p，n 步全对的概率约 $p^n$——这条连乘曲线解释了为什么「单步看着不错」的 agent 在长任务上常常崩，也是 pass^k 想刻画的东西。 |
| prompt injection | 提示注入 | 攻击者把恶意指令藏进 agent 会读到的内容里（网页、邮件、工具返回、文件），诱导 agent 执行非用户本意的动作（泄密、转账、删数据）。是 agent 安全的头号威胁。 |
| indirect prompt injection | 间接提示注入 | 注入不来自用户输入，而来自 agent 在执行任务时主动取来的外部内容（如它抓取的一个网页里埋的指令）。Greshake 等 2023 系统化了这类威胁。 |
| data/instruction separation | 数据/指令分离 | 防注入的核心原则：让模型把「工具返回的内容」当数据看待，而非当作要执行的指令。难点在于 LLM 没有硬性的指令/数据边界，需要靠提示、标注、权限多层缓解。 |
| tool misuse | 工具误用 | agent 调用了它本不该调的工具，或用越权的参数（如本该只读却去删除）。可能源于幻觉、注入或目标误解。 |
| least privilege / permission boundary | 最小权限 / 权限边界 | 只给 agent 完成任务所必需的最小权限；高危工具（删除、付款、外发）加确认或禁用。权限沙箱是把「被劫持的后果」限制住的关键。 |
| sandbox | 沙箱 | 限制 agent 可执行动作范围的隔离环境/白名单机制。本课模块 05 从零写一个按权限放行/拦截工具调用的策略沙箱。 |
| ToolEmu | —— | Ruan 等 2023：用一个 LLM 模拟工具执行环境，在不接真实危险工具的前提下，廉价地暴露 agent 的高风险行为，用于安全评测。 |
| monitoring / oversight | 监控 / 监督 | 在 agent 运行时观测其动作、捕捉异常信号（越权调用、命中注入特征、偏离任务）并告警/拦截。是「不能事前消灭风险就事中发现风险」的防线。 |
| confused deputy | 受蒙蔽的代理 | 一个有权限的主体（agent）被无权限者（注入内容）诱导去滥用自己的权限。prompt injection 在安全上常被归为此类问题。 |
| permission policy (allow/deny/ask) | 权限策略 | 对每个工具/动作的放行规则：自动允许、拒绝、或暂停询问人。生产 agent 常按工具的「可逆性/风险」分级配置。 |
