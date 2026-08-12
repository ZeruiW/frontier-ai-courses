# 参考清单 · References（Skills 与工具生态）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用纯标准库 + MockLLM 从零造的每个机制（skill 加载、slash 命令、MCP、插件、完整系统），都能在下列文献与规范里找到真实系统上的对应设计与权衡。

## Skills 与渐进披露 · Skills & Progressive Disclosure
- ★ **Anthropic, _Agent Skills_（官方文档，`platform.claude.com/docs/en/agents-and-tools/skills`）** — skill 的权威定义：每个 skill 是一个文件夹，含一个 `SKILL.md`（`---` frontmatter 里的 `name`/`description` + markdown 正文）；description 常驻上下文供模型判断相关性，正文按需加载。本课模块 01 从零实现的 frontmatter 解析、发现、相关性触发、按需注入，全部对标它。必读。
- ★ **Anthropic, _Claude Code: Skills_（`docs.claude.com` / Claude Code 文档）** — Claude Code 里 skills 的组织（`.claude/skills/<name>/SKILL.md`）、发现路径、与 agent 的集成方式。理解「不依赖框架」时你究竟在重造什么——本课正是把 Claude Code 的这套子系统亲手再造一遍。
- ★ **「渐进披露 / progressive disclosure」设计原则** — 核心思想：把能力的轻量描述常驻、完整内容按需加载，以在有限上下文里管理大量能力。贯穿本课 skill（01）、tool search（04 旁注）、完整系统（05）。Anthropic 的 skills 与 tool-search 文档都以它为设计基石。
- **Anthropic, _Engineering at Anthropic: Building effective agents_（工程博客）** — 把 agent 模式拆成 workflow（代码编排）与 agent（模型自主）两类，强调「能力要可组合、上下文要精简」。建立「为什么需要 skills/工具生态这套可扩展性机制」的工程判断。

## Slash 命令与插件 · Slash Commands & Plugins
- ★ **Anthropic, _Claude Code: Slash commands_（官方文档）** — slash 命令的权威定义：自定义命令是带 frontmatter 的 markdown 文件，放在 `.claude/commands/`（或插件里）；`$ARGUMENTS`/`$1`/`$2` 做参数绑定；`!`cmd`` 注入 shell 输出、`@file` 注入文件内容；命令可命名空间化。本课模块 02 从零实现的解析、绑定、动态注入、路由，逐项对标它。
- ★ **Anthropic, _Claude Code: Plugins_（官方文档）** — plugin 的权威定义：一个插件用 manifest（`.claude-plugin/plugin.json`）声明它提供的 skills / commands / agents / MCP servers；插件可被安装、启停、命名空间化。本课模块 04 从零造的 manifest 解析、发现、加载、命名空间隔离、版本检查，对标它的设计。必读。
- **Anthropic, _Claude Code: Plugin marketplaces_（官方文档）** — 插件如何被发现与分发（marketplace 索引、版本、来源）。理解模块 04 末尾「分发」一节在真实生态里的样子。

## MCP 模型上下文协议 · Model Context Protocol
- ★ **Anthropic, _Model Context Protocol specification & docs_（`modelcontextprotocol.io`）** — MCP 的权威规范：host/client/server 架构、resources/tools/prompts 三类能力、基于 JSON-RPC 2.0 的 `initialize` 握手与能力协商、`tools/list`·`tools/call`·`resources/list`·`resources/read`·`prompts/list`·`prompts/get` 方法、stdio / Streamable HTTP 传输。模块 03 从零写的 mini MCP 直接复现它的消息流。必读。
- ★ **JSON-RPC 2.0 Specification（`jsonrpc.org/specification`）** — MCP 传输层所用的极简 RPC 规范：请求/响应/通知的字段、id 配对规则、标准错误码（-32700/-32600/-32601/-32602/-32603）。模块 03 实现消息编解码时的字典级依据。必读。
- ★ **Anthropic, _Tool use (function calling) with the Claude API_（官方文档）** — 工具调用的权威接口：`input_schema`（JSON Schema）、`tool_use`/`tool_result` 内容块、`tool_choice`、并行调用、错误回传。MCP 的 `inputSchema` 与 tools/call 结果形状与它一脉相承；本课所有工具相关代码都以它为形状基准。
- **Anthropic, _MCP connector (Messages API `mcp_servers`)_ 文档** — 真实 Claude API 直接连远程 MCP server 的方式（`mcp_servers` 参数 + `mcp_toolset` 工具，beta header `mcp-client-2025-11-20`）。理解本课 mini MCP 在真实 Claude 上的落点——你写的 server 可被真实 host 接入。
- **Anthropic, _Tool search tool_（`platform.claude.com/.../tool-search-tool`）** — 工具多时按需检索 schema、保留 prompt cache 的官方机制（`tool_search_tool_regex/bm25` + 其它工具 `defer_loading`）。模块 04「延迟加载工具 schema」旁注的现实依据，也是渐进披露在工具层的体现。

## JSON Schema 与解析 · Schemas & Parsing
- **JSON Schema Specification（`json-schema.org`）** — skill frontmatter、工具 `inputSchema`、manifest 的字段约束所依据的标准。理解 `type`/`properties`/`required`/`enum` 是写对校验器的基础。
- **YAML 1.2 Specification（`yaml.org`）** — frontmatter 常用 YAML 风格。本课刻意只用「极简子集 + 纯标准库手写解析」而不依赖 PyYAML，以贴合「不依赖框架」的立场；遇到完整 YAML 语法分歧时以此规范为准。
- **Semantic Versioning 2.0.0（`semver.org`）** — 插件版本与依赖约束所依据的标准：`MAJOR.MINOR.PATCH` 的语义、预发布与构建元数据、约束运算符。模块 04 的版本检查器对标它的核心子集。

## Agent 范式与衔接 · Agent Paradigm & Cross-links
- **Yao et al. 2022, _ReAct: Synergizing Reasoning and Acting in Language Models_** — 「推理 + 行动」交替的范式，是工具调用 agent 的基础模板。本课的工具/MCP 调用都在这个循环里发生；理解 skills/工具生态是「给这个循环装上可扩展的能力」。
- **Schick et al. 2023, _Toolformer: Language Models Can Teach Themselves to Use Tools_** — 工具使用可被训练进模型本身的奠基论文。理解「工具是一种能力」，而 skills/插件是「把能力打包分发」的工程层。
- ★ **本系列「动手造 Agent」其它课程** — 本课聚焦「可扩展性子系统」，与本系列的「工具调用内核」「agent 循环」「评测与安全」诸课互补：那里教 agent 怎么调一个工具、怎么循环；本课教怎么让这些能力可发现、可加载、可打包、可组合，且不依赖任何框架。

## 真实接口与数据来源 · Real Interfaces & Data
- **Anthropic / Claude Code 官方仓库与文档** — skills（`SKILL.md`）、slash 命令、plugins（`plugin.json`）、MCP 的可执行真实形状。本课刻意让 MockLLM 与解析器的输入输出贴近它们，学完照着把验证过的零件接到真实 Claude Code / MCP 是最自然的下一步。
- **Anthropic Python SDK（`anthropic`）** — `messages.create(model="claude-sonnet-4-6"/"claude-opus-4-8", tools=[...], messages=[...])` 是本课每个 notebook「真实适配」旁注的接口。无 `ANTHROPIC_API_KEY` 时本课代码自动回退 MockLLM，绝不阻断。
- **公开 MCP server 实现（modelcontextprotocol.io 的官方/社区 server 列表）** — 真实 MCP server 的样子（文件系统、Git、数据库等）。模块 03 写完 mini server 后，对照它们能看清「同一套协议、不同能力」的生态形态。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU、无需任何 API key**：全课用纯标准库 + **MockLLM**（确定性假模型）在 CPU 上从零造 skills/工具生态——frontmatter 解析与渐进披露、slash 命令解析与动态注入、mini MCP 的 JSON-RPC 握手与调用、插件 manifest 与命名空间隔离、完整系统的选择与组合。每个内核都与朴素参考/不变量对拍、用 `assert` 兜底，保证你写的**协议与控制流逻辑正确**。
- **可迁移性**：你在 MockLLM 上验证过的零件（skill 加载器、命令路由、MCP server/client、插件加载器），可几乎一对一接到真实 Claude Code / MCP 生态——把 `MockLLM(...)` 换成真实 `messages.create(...)`、把内存 stdio 换成真实管道即可。本课刻意让形状贴近真实接口。
- **不依赖框架的意义**：不依赖 Claude Code 等现成框架，亲手造一遍，才能真正理解 skills / slash / MCP / 插件「为什么这样设计、边界在哪、出错时怎么办」。学完你既能用好框架，也能在没有框架时自己搭一套。
