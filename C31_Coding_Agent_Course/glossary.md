# 术语词典 · Glossary（构建编码 Agent）

> 按主题分组，每条 2–3 句中文释义，英文术语保留原文（agent / LLM 工具调用领域的通用语言）。读 Claude Code 文档、SWE-agent / aider 源码、Anthropic 工具使用文档遇到生词回这里查。本课用纯标准库 + MockLLM 把这些概念从零实现，术语与真实编码 agent 一一对应。

## Agent 核心概念 · Agent Fundamentals

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| agent | 智能体 | 一个能感知环境、自主决策并采取动作的程序。在 LLM 语境下 = 一个 LLM + 一组工具 + 一个反复「思考→调用工具→观察结果」的循环。它与普通聊天机器人的区别在于能改变外部世界（写文件、跑命令）。 |
| coding agent | 编码智能体 | 专门用于软件工程任务的 agent：读代码库、定位 bug、写补丁、跑测试、迭代修复。Claude Code、SWE-agent、aider、Cursor 的 agent 模式都属于此类。本课从零造一个。 |
| agent loop / agentic loop | agent 主循环 | agent 的心脏：把对话历史发给 LLM → LLM 要么给最终答复、要么请求调用工具 → 执行工具 → 把结果回填进对话 → 再发给 LLM，如此往复直到任务完成或到达步数上限。 |
| ReAct (Reason + Act) | 推理-行动范式 | Yao 等 2022 提出的范式：让 LLM 交替产出「思考（reasoning trace）」与「行动（调用工具）」，思考为行动提供依据、行动的观察结果又喂回思考。现代工具调用 agent 的思想源头。 |
| tool / function calling | 工具 / 函数调用 | 让 LLM 不直接作答、而是输出「调用哪个工具、传什么参数」的结构化请求，由宿主程序执行后把结果返回。是 agent 与外部世界交互的唯一通道。 |
| tool registry / dispatch | 工具注册表 / 分发 | 把「工具名 → 实现函数 + 参数模式（schema）」登记在一张表里；agent 收到 LLM 的工具调用请求后，按名字查表、校验参数、执行、捕获异常。本课模块 05 的核心数据结构。 |
| tool schema | 工具模式 | 用结构化格式（通常 JSON Schema）描述一个工具的名字、用途、参数及类型。LLM 据此知道有哪些工具可用、怎么填参数。Anthropic API 里是 `tools=[{name, description, input_schema}]`。 |
| system prompt | 系统提示 | 放在对话最前、为整个会话设定角色与规则的指令。编码 agent 的系统提示通常交代「你是一个编码助手、可用哪些工具、要先看再改、改完要跑测试」等纪律。 |
| context window | 上下文窗口 | LLM 一次能看到的 token 上限。agent 跑久了对话历史会撑爆窗口，因此要截断工具输出、压缩历史、必要时做总结。是工程上绕不开的硬约束。 |
| scaffolding / harness | 脚手架 / 框架壳 | 包在 LLM 外面、把它变成 agent 的那层代码：工具、循环、提示、解析、错误处理。SWE-agent 论文称之为 agent-computer interface（ACI）。本课造的就是这层。 |
| agent-computer interface (ACI) | 智能体-计算机接口 | SWE-agent 提出的概念：专为 LLM 设计的工具与反馈格式。强调工具的输出要简洁、可读、对 LLM 友好（如带行号、限长、有清晰错误信息），ACI 设计的好坏直接决定 agent 的成败。 |

## 文件工具 · File Tools

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| read / view file | 读文件 | agent 看文件内容的工具。为对 LLM 友好通常带上行号、并支持按行范围读（大文件不必整读），让后续的精确编辑和报错定位有坐标系。 |
| write file | 写文件 | 创建或整体覆盖一个文件。适合新建文件；对已有文件做局部修改则危险（易丢内容），所以要配合「先读后写」或改用精确编辑。 |
| string-replace edit | 字符串替换编辑 | 现代编码 agent 的主力编辑方式：给出一段「旧字符串」和「新字符串」，要求旧串在文件中<strong>唯一匹配</strong>才替换。比基于行号的编辑更稳健——它不受其他地方行号漂移影响。 |
| uniqueness check | 唯一性校验 | 字符串替换编辑的安全前提：若旧串在文件里出现 0 次（没找到，可能 LLM 记错）或 ≥2 次（有歧义，会改错地方），都应拒绝并报错，逼 LLM 给出足够上下文使匹配唯一。 |
| unified diff | 统一差异格式 | `diff -u` / git 用的标准差异格式：`---/+++` 头、`@@ -a,b +c,d @@` 定位块（hunk）、`-` 删行 `+` 加行。让人（和 LLM）一眼看清「改了什么」，是 agent 改动可审计性的关键。 |
| hunk | 差异块 | unified diff 中一段连续的改动，带 `@@ ... @@` 头说明它在新旧文件中的行范围。一个 diff 可含多个 hunk。 |
| path traversal | 路径穿越 | 用 `../` 或绝对路径逃出预期目录、读写到工作区之外的攻击/事故。文件工具必须把所有路径解析（`os.path.realpath`）后校验仍在工作区内，否则 agent 可能误删系统文件。 |
| sandbox / workspace root | 沙箱 / 工作区根 | 限定 agent 只能操作的目录。所有文件/shell 操作都相对它、且不得越界。本课用 `tempfile.mkdtemp()` 造一个隔离工作区，既安全又可随时清理。 |
| atomic write | 原子写 | 先写临时文件再 `os.replace` 改名，保证写入要么全成功要么不影响原文件，避免写到一半崩溃留下半截文件。生产级文件工具的常见做法。 |

## Shell 工具 · Shell Execution

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| subprocess | 子进程 | Python 标准库 `subprocess` 模块，用于启动外部命令并捕获其输出。是给 agent 装上「跑命令」能力的标准方式（`subprocess.run(..., capture_output=True, timeout=...)`）。 |
| stdout / stderr | 标准输出 / 标准错误 | 进程的两路输出：正常结果走 stdout，错误与诊断走 stderr。agent 要分别捕获——测试是否通过常看 stdout，崩溃原因常在 stderr。 |
| return code / exit status | 返回码 / 退出状态 | 进程结束时给的整数，约定 `0` 表示成功、非 0 表示失败。agent 据它快速判断命令成没成（如 pytest 失败返回非 0），无需解析全部文本。 |
| timeout | 超时 | 给命令设的最长运行时间，超过就强制终止。防止 agent 触发死循环或卡住的命令把整个会话挂死，是 shell 工具<strong>必备</strong>的安全阀（`subprocess` 的 `timeout=` 参数）。 |
| output truncation | 输出截断 | 把命令输出限制在一定长度（如前后各若干行/字符），中间用省略标记。一条命令可能吐出几万行，不截断会瞬间撑爆 LLM 的上下文窗口、烧掉大量 token。 |
| working directory (cwd) | 工作目录 | 命令执行时的当前目录。agent 必须把它固定在工作区内（`subprocess.run(..., cwd=workspace)`），命令里的相对路径才不会乱跑。 |
| command allow/deny list | 命令白/黑名单 | 限制 agent 能跑哪些命令的策略。黑名单拦截危险命令（`rm -rf /`、`sudo`、`:(){ :\|:& };:` fork 炸弹、`curl ... \| sh`）；白名单更严，只放行已知安全的命令。 |
| shell injection | shell 注入 | 当用 `shell=True` 且命令里拼接了不可信内容时，攻击者可用 `;`、`&&`、反引号注入额外命令。安全做法是尽量用参数列表（`shell=False`）或严格校验。 |
| environment isolation | 环境隔离 | 控制子进程能看到的环境变量、网络、文件系统范围。生产 agent 常在容器/沙箱里跑命令，防止它访问密钥或破坏宿主。本课用临时目录做轻量隔离。 |
| dry run | 试运行 | 在真正执行有副作用的命令前，先展示「将要执行什么」给人确认（或让 agent 自检）。降低破坏性操作误触的风险。 |

## 代码搜索与导航 · Code Search & Navigation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| grep | —— | 按正则表达式在文件内容里逐行搜索匹配的工具（名字源自 ed 编辑器的 `g/re/p`）。agent 用它回答「哪里用到了这个函数/变量/字符串」。 |
| glob | 通配匹配 | 用 `*`、`**`、`?` 等通配符按文件<strong>名/路径</strong>匹配文件（如 `**/*.py`）。与 grep（搜内容）互补，agent 用它回答「项目里有哪些 Python 文件」。 |
| ripgrep (rg) | —— | 极快的现代 grep，默认递归、自动遵守 `.gitignore`、跳过二进制与隐藏文件。是当代编码 agent 事实标准的搜索后端；本课用标准库模拟它的行为。 |
| regular expression (regex) | 正则表达式 | 描述字符串模式的小语言（Python 的 `re` 模块）。代码搜索的核心；要注意把用户输入当字面量搜时需 `re.escape` 转义，否则特殊字符会改变语义。 |
| symbol search | 符号搜索 | 定位某个函数、类、变量<strong>定义处</strong>（而非所有出现处）的搜索。简单实现可用针对 `def name`、`class name` 的正则；进阶用 AST 或 ctags/LSP。 |
| AST (Abstract Syntax Tree) | 抽象语法树 | 源代码解析后的树状结构（Python 的 `ast` 模块）。比正则更精确地理解代码结构，可用于可靠的符号定位、重命名、静态分析。 |
| context lines | 上下文行 | 搜索命中时一并返回的命中行前后若干行（如 `grep -C 3`）。让 LLM 看到匹配处的周边代码，判断这是不是它要找的地方。 |
| relevance ranking | 相关性排序 | 当命中很多时，按某种分数（文件名匹配、命中密度、是否定义处、路径深度等）给结果排序，把最可能相关的放前面。上下文窗口有限，排序质量直接影响 agent 看到的信息质量。 |
| .gitignore filtering | gitignore 过滤 | 搜索时跳过 `.gitignore` 列出的文件（构建产物、依赖目录、虚拟环境）。否则会被 `node_modules/`、`__pycache__/` 等噪音淹没。 |
| binary detection | 二进制检测 | 在搜索前判断文件是否二进制（如含 NUL 字节），是则跳过。避免把图片/可执行文件的乱码塞进结果。 |

## 测试、循环与自我纠错 · Test, Loop & Self-Correction

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pytest | —— | Python 主流测试框架。约定 `test_*` 函数、用 `assert` 断言；命中失败时打印 `FAILED test_x` 与 traceback、返回非 0 退出码。agent 用它判断「补丁对不对」。 |
| edit-test-fix loop | 编辑-测试-修复循环 | 编码 agent 自我纠错的核心循环：改代码 → 跑测试 → 若失败则解析错误、定位、再改 → 直到全绿或到迭代上限。让 agent 不靠「一次写对」，而靠「快速迭代逼近正确」。 |
| test output parsing | 测试输出解析 | 从 pytest 的文本输出里抽出结构化信号：通过/失败数、哪些用例失败、失败的文件:行、断言信息。是把「人看的报告」变成「机器可决策的信号」的一步。 |
| traceback | 回溯栈 | 异常发生时打印的调用栈，含出错的文件、行号、异常类型与消息。agent 解析它来定位「在哪一行、因为什么」出的错。 |
| failure localization | 失败定位 | 根据测试输出/traceback 找出最该改的文件和行。是 edit-test-fix 循环里「下一步改哪」的依据，做不好就会乱改一气。 |
| convergence | 收敛 | 循环达到目标（测试全绿）的状态。判定收敛通常看「退出码为 0」或「失败数为 0」。 |
| iteration budget / max steps | 迭代预算 / 步数上限 | 给循环设的最大轮数。防止 agent 在改不动的问题上无限打转、烧光预算。到上限仍未绿则放弃并报告，是必备的安全阀。 |
| oscillation / loop detection | 来回振荡 / 死循环检测 | agent 反复在两个错误状态间打转（改 A 坏 B、改 B 坏 A）。可通过检测「状态/动作重复」来识别并打断，避免空耗。 |
| regression | 回归 | 改动修好了一个问题、却弄坏了原本正常的功能。所以 agent 修完应跑<strong>整个</strong>测试集而非只跑目标用例，确认没引入回归。 |
| reward signal | 奖励信号 | 评价 agent 一步/一轮做得好不好的信号。编码任务里最干净的奖励就是「测试是否通过」——客观、可自动判定，这也是 SWE-bench 的判分基础。 |

## 真实模型与 API · Real LLM & API

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MockLLM | 模拟 LLM | 本课用来代替真实模型的<strong>确定性</strong>桩：按预设脚本依次返回「调用某工具」或「最终答复」，使整个 agent 循环可在无网络、无 API key、零成本下端到端跑通且结果可复现，便于教学与测试。 |
| Anthropic Messages API | —— | 调用 Claude 的接口：`client.messages.create(model=..., messages=[...], tools=[...])`。返回的内容块可能是文本，也可能是 `tool_use`（请求调用工具）；宿主执行后用 `tool_result` 块回填再次请求。 |
| tool_use / tool_result | 工具调用块 / 工具结果块 | Anthropic API 多轮工具调用的两种内容块。模型发 `tool_use`（带工具名、入参、`id`）；宿主执行后以同 `id` 的 `tool_result` 块放进 `role:"user"` 消息回传，模型据此继续。 |
| stop_reason | 停止原因 | API 响应里说明模型为何停下的字段。`tool_use` 表示它要调用工具（循环继续）；`end_turn` 表示它给出了最终答复（循环结束）。agent 主循环据它决定是否继续。 |
| model id | 模型标识 | 指定调用哪个 Claude 模型的字符串，如 `claude-sonnet-4-6`、`claude-opus-4-6`。本课默认用 Sonnet 级模型；具体可用 id 以官方文档为准。 |
| graceful fallback | 优雅回退 | 当真实依赖不可用（无 API key、无网络）时，自动切到本地替身（MockLLM）继续运行而非崩溃。本课所有 notebook 的契约：有 key 用真 Claude，无 key 用 MockLLM，<strong>绝不阻断</strong>。 |
| temperature | 温度 | 控制采样随机性的参数，0 最确定、越高越发散。agent 任务常用低温度以求稳定可复现的工具调用。 |
| token | —— | 模型处理文本的最小单位（约 0.75 个英文词）。计费与上下文窗口都按 token 计；工具输出截断、历史压缩都是为了省 token、不撑爆窗口。 |
| prompt caching | 提示缓存 | 把会话中不变的前缀（如长系统提示、工具定义）缓存，后续请求复用以省钱省延迟。长跑的编码 agent 受益明显。 |

## 评测与生态 · Evaluation & Ecosystem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| SWE-bench | —— | Jimenez 等 2023 提出的基准：从真实 GitHub 仓库取「issue + 修复该 issue 的 PR」，要求 agent 在仓库快照上生成补丁，用该 PR 自带的测试判定是否解决。是编码 agent 能力的事实标准评测。 |
| SWE-bench Verified | —— | SWE-bench 的人工筛选子集，剔除了描述不清、测试有问题的样本，结果更可信。报告编码 agent 成绩时常用它。 |
| pass@k | —— | 允许 agent 对一题尝试 k 次、只要有一次通过测试就算解决的指标。`pass@1` 最严（一次成功），k 越大越宽松。 |
| golden patch / gold patch | 标准补丁 | 基准里人类专家写的、已知能解决该 issue 的正确补丁。用作参照（但评测靠测试是否通过，而非与它逐字比对）。 |
| trajectory / rollout | 轨迹 | agent 解一道题的完整过程记录：每一步的思考、调用了什么工具、得到什么观察。用于调试、复盘和训练。 |
| Claude Code | —— | Anthropic 官方的命令行编码 agent。可读改代码库、跑命令、跑测试、用 MCP 接外部工具。本课的命名与设计灵感来源——目标是让你理解它内部如何运转。 |
| SWE-agent | —— | Yang 等 2024 的开源编码 agent 与论文，提出 agent-computer interface（ACI）概念：为 LLM 量身设计工具与反馈格式，证明 ACI 设计对成绩的影响巨大。 |
| aider | —— | 流行的开源 AI 结对编程 CLI。特点是与 git 深度集成、用 diff/edit 块的编辑格式、把仓库结构（repo map）喂给模型。本课文件编辑与 diff 部分的现实参照。 |
| MCP (Model Context Protocol) | 模型上下文协议 | Anthropic 提出的开放协议，让 agent 以统一方式接入外部工具与数据源（数据库、API、文件系统）。把「给 agent 加工具」标准化，是本课工具层的工业级延伸。 |
