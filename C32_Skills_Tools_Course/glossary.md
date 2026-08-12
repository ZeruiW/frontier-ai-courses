# 术语词典 · Glossary（Skills 与工具生态）

> 按主题分组，每条 2–3 句中文释义、英文术语保留。读 Anthropic Agent Skills 文档、MCP 规范、Claude Code slash commands / plugins、JSON-RPC 2.0 规范遇到生词回这里查。本课用纯标准库 + MockLLM 在 CPU 上从零造这些机制，但术语与真实 Claude Code / MCP 生态一一对应。

## 总览与世界观 · Paradigm & World

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| extensibility | 可扩展性 | 一个 agent 在不改核心代码的前提下，能新增能力（技能、工具、命令）的程度。本课的全部主题——skill、slash、MCP、插件——都是为可扩展性服务的不同机制。一个写死能力的 agent 难以演进，可扩展的 agent 才能长大。 |
| harness / scaffold | 框架壳 / 脚手架 | 包裹 LLM 的那层代码：管理上下文、解析输出、执行工具、施加护栏。skills 与工具生态是 harness 的「可扩展性子系统」。本课从零造这套子系统而不依赖任何现成框架（如 Claude Code 本身）。 |
| capability | 能力 | agent 能做的一件具体的事（查天气、改文件、跑 SQL）。能力可以来自工具（可调用函数）、skill（按需加载的指令）、或 MCP server（外部暴露的操作）。本课教你把能力做成可插拔的零件。 |
| context window | 上下文窗口 | 模型一次能看到的 token 上限。skills 与工具生态的核心张力就在这里：能力越多，描述越占上下文；渐进披露、按需加载、tool search 都是为了在有限的窗口里塞下尽可能多的「潜在能力」。 |
| progressive disclosure | 渐进披露 | 核心设计原则：平时只把能力的「轻量描述」放进上下文，真正用到时才加载「完整内容」。skill 平时只占一行 description，命中后才注入正文；工具平时只列名字+简介，需要时才加载完整 schema。是在有限上下文里管理大量能力的关键。 |
| MockLLM | 模拟模型 | 本课用的确定性「假模型」：用规则/查表代替神经网络，对给定输入返回可预测的工具调用或文本。它让整套 skills / 工具管线无需 API key 即可端到端跑通并被 assert 验证，把学习焦点钉在协议与控制流上。无 key 时真实适配代码也回退到它。 |
| no-key fallback | 无 key 回退 | 本课特例：每个内核旁附真实 Claude API 适配（`messages.create`），检测到无 `ANTHROPIC_API_KEY` 时自动改用 MockLLM，让代码永远能跑通、绝不阻断学习。有 key 即走真实模型。 |

## Skill 定义与加载 · Skill Definition & Loading

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| skill | 技能 | 一份按需加载的「指令 + 知识」包，本质是一个带 frontmatter 的 markdown 文件（Anthropic 称 SKILL.md）。它告诉模型「在某类任务下该怎么做」。与工具的区别：工具是可执行的函数，skill 是给模型读的文本指导。 |
| frontmatter | 前置元数据 | markdown 文件头部、用 `---` 包裹的一段结构化元数据（YAML 风格），含 `name`、`description` 等字段。skill 的发现与触发全靠它——尤其是 `description`，模型据此判断「这个 skill 跟当前任务相关吗」。 |
| SKILL.md | —— | Anthropic Agent Skills 约定的 skill 文件名：`---` frontmatter（name/description）+ markdown 正文（详细指令、示例、注意事项）。本课从零解析它，不依赖任何 YAML 库。 |
| skill body | skill 正文 | frontmatter 之后的 markdown 内容：完成该类任务的详细步骤、约定、示例。平时不进上下文（省 token），命中后才被注入——这正是渐进披露在 skill 上的体现。 |
| skill discovery | skill 发现 | 扫描某个目录（如 `.claude/skills/`）、解析每个 SKILL.md 的 frontmatter、建立一张「name → skill」的清单。发现只读 frontmatter（轻量），不读正文（重）。 |
| skill registry / catalog | skill 注册表 / 目录 | 内存里维护的「skill 名 → (元数据, 正文路径)」映射。注册表常驻一份「名字 + 描述」的轻量目录给模型看；正文按需从磁盘加载。 |
| relevance trigger | 相关性触发 | 判断「当前任务该不该激活某个 skill」的机制。最朴素的实现是关键词匹配 description；真实系统让模型读 description 清单自行决定。触发后才加载正文、注入上下文。 |
| on-demand loading / lazy loading | 按需加载 / 惰性加载 | 只在 skill 被判定相关时，才从磁盘读它的正文并注入上下文。与「启动时把所有 skill 全读进来」相反。是渐进披露的实现手段，直接决定能塞下多少 skill。 |
| token budget | token 预算 | 注入上下文的内容总量上限。当多个 skill 同时命中、正文加起来超预算时，要按相关性排序、截断或取舍。本课从零实现一个简单的预算控制器。 |
| skill injection | skill 注入 | 把命中 skill 的正文拼进发给模型的 prompt（通常作为 system 或一段上下文前缀）。注入后模型就「知道」了该类任务的做法。 |
| name collision | 命名冲突 | 两个 skill 重名时的冲突。注册表需要一个明确的去重/覆盖/报错策略（如「后注册覆盖」或「报错拒绝」），否则发现阶段就埋下隐患。 |

## Slash 命令与动态注入 · Slash Commands & Dynamic Injection

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| slash command | 斜杠命令 | 以 `/` 开头的用户指令（如 `/review src/app.py`），用来显式触发一段预设的工作流或 prompt 模板。Claude Code 的 `/`-命令是代表。与 skill 的区别：skill 由模型按相关性自动触发，slash 命令由用户显式触发。 |
| command parsing | 命令解析 | 把一行 `/cmd arg1 arg2` 文本拆成「命令名 + 参数列表」的过程。要处理前导 `/`、空白分隔、带引号的参数等。是 slash 命令系统的入口。 |
| argument binding | 参数绑定 | 把解析出的位置/具名参数填进命令模板的占位符（如 `$1`、`$ARGUMENTS`、`{{file}}`）。Claude Code 用 `$ARGUMENTS` 表示全部参数、`$1`/`$2` 表示位置参数。 |
| command template | 命令模板 | 一个 slash 命令背后的 prompt 模板（常是一个带 frontmatter 的 markdown 文件），含占位符。绑定参数后展开成发给模型的实际 prompt。 |
| dynamic injection | 动态注入 | 在展开命令时，把「运行时才知道的内容」拼进 prompt：如 `!`command`` 执行一条 shell 命令并把其输出注入、`@file` 把文件内容注入。让命令能携带实时上下文。 |
| bang command (`!`) | 叹号命令 | Claude Code slash 命令模板里 `!`...`` 语法：执行其中的 shell 命令，把 stdout 注入到展开后的 prompt 里。本课从零模拟它（用一个白名单的安全执行器）。 |
| file reference (`@`) | 文件引用 | 命令/prompt 里 `@path` 语法：把该文件的内容注入上下文。是动态注入的一种常见形式。 |
| command routing | 命令路由 | 根据命令名把请求分发到对应的处理器（模板展开、内置命令、或报「未知命令」）。是 slash 命令系统的分发中枢，和工具分发同构。 |
| namespacing (commands) | 命令命名空间 | 用目录或前缀给命令分组（如 `/git:commit`、`/project:deploy`），避免重名、便于组织。来自插件的命令常带插件名前缀。 |
| built-in vs custom command | 内置 vs 自定义命令 | 内置命令由 harness 硬编码（如 `/help`、`/clear`）；自定义命令来自用户/项目/插件提供的模板文件。路由时通常自定义可覆盖或并存。 |

## MCP 模型上下文协议 · Model Context Protocol

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MCP (Model Context Protocol) | 模型上下文协议 | Anthropic 2024 提出的开放标准，统一「AI 应用」与「外部工具/数据源」的对接方式。把过去 M 个应用 × N 个工具的 M×N 集成爆炸，收敛成大家都讲同一种协议的 M+N。常被比作「AI 世界的 USB-C」。 |
| host | 宿主 | 跑 LLM、面向用户的应用（如 Claude Desktop、Claude Code、IDE 插件）。它在内部为每个外部 server 创建一个 client，并把各 server 暴露的能力汇总给模型。 |
| MCP client | MCP 客户端 | host 内部、与某一个 server 一对一连接的连接器。负责握手、能力协商、转发列举/调用请求。本课从零写一个 mini client。 |
| MCP server | MCP 服务端 | 暴露具体能力（工具/资源/提示）的独立进程或服务。一个 server 专注一类能力（如文件系统、GitHub、数据库），可被任意支持 MCP 的 host 复用。本课从零写一个 mini server。 |
| tools (MCP) | 工具 | MCP server 暴露的、可被模型调用以产生副作用或取数的操作，每个带 name、description 与 `inputSchema`。语义与函数调用的工具一致，只是经协议暴露。 |
| resources (MCP) | 资源 | MCP server 暴露的、可被读取的（通常只读）上下文数据，用 URI 寻址（如 `file:///readme.md`）。模型/应用可列举并读取它们作为上下文。 |
| prompts (MCP) | 提示模板 | MCP server 暴露的可复用提示模板（可带参数），供 host 以「斜杠命令」等形式呈现给用户。把本课模块 02 与模块 03 串了起来——MCP 的 prompt 可以变成 host 的 slash 命令。 |
| JSON-RPC 2.0 | —— | MCP 的传输消息格式：请求含 `jsonrpc`/`id`/`method`/`params`，响应含 `id`/`result` 或 `id`/`error`；无 `id` 的是通知（notification）。本课从零实现它的编解码。 |
| initialize / initialized | 初始化握手 | MCP 连接的第一步：client 发 `initialize`（带协议版本与能力），server 回能力，client 再发 `notifications/initialized` 通知确认。之后才能列举与调用。 |
| capability negotiation | 能力协商 | 握手阶段 client 与 server 互相声明各自支持的能力（是否提供 tools/resources/prompts、协议版本等），据此决定后续可用的交互。 |
| transport (stdio / HTTP) | 传输层 | MCP 消息怎么传：本地 server 常用 stdio（标准输入输出管道，按行分隔的 JSON）；远程用 Streamable HTTP / SSE。协议内容与传输无关。本课用内存队列模拟 stdio。 |
| tools/list · tools/call | 列举 / 调用 | MCP 的两个核心方法：`tools/list` 让 client 发现 server 有哪些工具及其 schema；`tools/call` 携带工具名与参数请求执行，server 回结果（含 `isError` 标志）。 |
| error code | 错误码 | JSON-RPC 标准错误码：`-32700` 解析失败、`-32600` 非法请求、`-32601` 方法不存在、`-32602` 参数非法、`-32603` 内部错误。协议层错误用它；工具执行错误则放进 result 的 `isError`。 |
| notification | 通知 | 无 `id`、不需要回复的 JSON-RPC 消息（如 `notifications/initialized`）。发出即可，不等响应。 |

## 工具打包与插件 · Tool Packaging & Plugins

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| plugin | 插件 | 把一组相关能力（skills + 工具 + slash 命令 + MCP server 配置）打包成一个可分发、可安装、可启停的单元。Claude Code 的 plugin 是代表。本课从零造插件的发现-加载-隔离机制。 |
| manifest | 清单 | 描述插件元数据的结构化文件（如 `plugin.json` / `.claude-plugin/plugin.json`）：插件名、版本、提供的 skills/commands/tools、依赖、入口。加载器先读 manifest 再决定怎么装。 |
| plugin discovery | 插件发现 | 扫描插件目录、读取每个插件的 manifest、建立可安装清单的过程。与 skill 发现同构，只是单位更大（一个插件含多种能力）。 |
| plugin loading | 插件加载 | 按 manifest 把插件提供的 skills 注册进 skill 注册表、命令注册进命令路由、工具注册进工具注册表。加载是「把插件的能力接入 agent」的动作。 |
| namespace isolation | 命名空间隔离 | 给每个插件的能力加前缀（如 `myplugin:format`），避免不同插件的同名能力互相覆盖。是多插件共存的前提，和 Python 的模块命名空间是同一种思想。 |
| semantic versioning (semver) | 语义化版本 | `MAJOR.MINOR.PATCH` 的版本号约定：MAJOR 不兼容、MINOR 向后兼容加功能、PATCH 修 bug。插件依赖用它表达「我需要 X 插件 >=1.2.0」。本课从零写一个版本约束检查器。 |
| dependency resolution | 依赖解析 | 根据各插件 manifest 声明的依赖，确定加载顺序、检查版本是否满足、发现缺失或冲突。本课实现一个最小的依赖检查（拓扑序 + 版本满足）。 |
| version constraint | 版本约束 | 依赖里对版本的要求，如 `>=1.2.0`、`^1.0.0`、`~1.2.3`。约束检查器判断某个具体版本是否满足约束。 |
| entry point | 入口 | 插件被加载时调用的初始化点（manifest 里声明）。本课用一个简化的「注册函数」模拟。 |
| capability provider | 能力提供方 | 一个插件作为「skills/commands/tools 的提供方」的角色。加载器把提供方声明的能力逐一接入对应注册表。 |
| sandbox / isolation | 沙箱 / 隔离 | 限制插件能访问的资源/能影响的范围。命名空间隔离是「逻辑隔离」；更强的是进程/权限隔离（本课只做逻辑隔离，点到真实隔离的方向）。 |

## 完整 Skills 系统 · The Full Skills System

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| skills system | skills 系统 | 把发现、加载、选择、执行、组合统一起来的子系统：扫描 skills/plugins → 建注册表 → 按相关性选择 → 注入/调用 → 与 agent 循环集成。模块 05 把前四个模块的零件组装成它。 |
| selection | 选择 | 在众多已发现的能力里，挑出与当前任务相关的子集（命中的 skill、要调的工具、要展开的命令）。是把「潜在能力」变成「本轮实际能力」的关键一步。 |
| composition | 组合 | 把多种能力协同起来完成一个任务：一个 skill 指导怎么做，几个工具被依次调用，可能还展开一个 slash 命令。组合能力是「完整系统」相对「单个零件」的价值所在。 |
| agent loop integration | 与 agent 循环集成 | 把 skills 系统接到「观察 → 模型决策 → 执行 → 新观察」的循环里：每轮把命中的 skill 注入、把可用工具的 schema 提供给模型、执行模型选的工具、把结果回喂。 |
| evaluation (skills) | 评测 | 衡量 skills 系统好不好：相关 skill 有没有被选中（召回）、选中的是不是真相关（精度）、组合执行能不能完成任务、token 用量是否受控。本课用确定性任务 + assert 做最基本的评测。 |
| capability resolution | 能力解析 | 给定一个任务，确定「需要哪些 skill + 哪些工具 + 哪个命令」的整体过程。是选择 + 组合的合称。 |
| tool registry | 工具注册表 | 「工具名 → (可执行函数, schema)」的映射；模型给名字，系统查表执行。skills 系统里它与 skill 注册表、命令路由并列为三大注册表。 |
| dispatch | 分发 | 把模型给的工具调用按名字路由到真实函数执行，并把错误安全地包成结果而非崩溃。贯穿 MCP（模块 03）与完整系统（模块 05）。 |
| Claude Code | —— | Anthropic 的官方 agent CLI，原生支持 skills、slash 命令、plugins、MCP。本课的「不依赖框架」正是指：不依赖 Claude Code，而是亲手把它的这些子系统从零造一遍，从而真正理解它们。 |
| MCP prompt as slash command | MCP 提示即斜杠命令 | host 把某个 MCP server 暴露的 prompt 模板，呈现为一个 slash 命令给用户。这是 MCP（03）与 slash（02）在真实系统里的接合点，模块 05 会体现这种打通。 |
