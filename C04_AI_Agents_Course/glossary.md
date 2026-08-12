# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读论文 / 评测报告遇到生词回这里查。

## Agent 循环 · Agent Loop

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| LLM Agent | 大模型智能体 | 以 LLM 为决策核心、能调工具并根据反馈迭代行动的系统，而非一问一答的聊天机器人。 |
| ReAct | —— | Reasoning + Acting：让模型交替输出推理（Thought）和动作（Action）的经典 agent 范式。 |
| Thought-Action-Observation | 思考-动作-观察 | ReAct 的单步循环：先想、再做、再看环境返回什么，循环直到完成。 |
| Reflexion | 自我反思 | 失败后让 agent 用语言总结教训、写进记忆再重试的自我改进方法。 |
| Scaffolding | 脚手架 | 围绕模型搭的外部代码结构（循环、提示模板、工具、记忆），同一模型换脚手架能力差异巨大。 |
| Stop Condition | 停止条件 | 判定循环何时结束的规则：任务完成、达到最大步数、或模型显式宣布放弃。 |
| Max Turns / Step Budget | 最大步数 | 一次 episode 允许的最大循环轮数，防止 agent 无限打转。 |

## 工具调用 · Tool Use

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Function Calling | 函数调用 | 模型按约定格式输出"要调哪个函数 + 什么参数"，由外部代码真正执行。 |
| JSON Schema | —— | 描述工具参数名称、类型、必填项的标准格式，模型据此生成合法调用。 |
| Tool Registry | 工具注册表 | 把所有可用工具的名称、schema、实现函数集中管理的查找表。 |
| Tool Call / Tool Result | 工具调用 / 工具结果 | 一次调用请求与其执行返回值，成对写回对话历史供模型继续推理。 |
| MCP (Model Context Protocol) | 模型上下文协议 | 把工具 / 资源以标准协议暴露给任意模型客户端的开放规范。 |

## 沙箱与轨迹 · Sandbox & Trajectory

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Sandbox | 沙箱 | 隔离的执行环境（容器 / 虚拟文件系统），agent 的动作再危险也伤不到真实系统。 |
| Agent Harness | 智能体测试台 | 包住 agent 的外层基础设施：起环境、喂任务、记轨迹、判结果、控资源。 |
| Trajectory | 轨迹 | 一次任务中全部 Thought / Action / Observation 的完整时序记录，评测与调试的原始数据。 |
| Replay | 回放 | 用存档轨迹重现 agent 行为，不重新调模型，用于调试与人工审查。 |
| Timeout | 超时 | 对单步工具执行或整个 episode 设的时间上限，超时即截断判失败。 |
| Episode | 回合 | agent 从接到任务到终止的一次完整运行。 |

## 编码 Agent · Coding Agents

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| SWE-bench | —— | 用真实 GitHub issue + 仓库做任务的编码 agent 基准，按测试通过与否判分。 |
| Fail-to-Pass (F2P) | 失败转通过 | 修复前必须失败、修复后必须通过的测试集合，是 SWE-bench 判定"修对了"的标准。 |
| Pass-to-Pass (P2P) | 保持通过 | 修复前后都必须通过的回归测试，防止 agent 修一个坏一片。 |
| ACI (Agent-Computer Interface) | 智能体-计算机接口 | 专为 agent 设计的环境交互界面（搜索、打开文件、编辑命令），好的 ACI 显著提分。 |
| Patch | 补丁 | agent 产出的代码改动（diff 格式），应用到仓库后跑测试验证。 |
| Localization | 缺陷定位 | 在大仓库里找到该改哪个文件哪几行 —— 编码 agent 最常见的失败点。 |

## Computer Use · 截图→动作

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Computer-Use Agent | 电脑操作智能体 | 看屏幕截图、输出鼠标键盘动作来操作电脑的视觉 agent。 |
| GUI Grounding | 界面定位 | 把"点击保存按钮"这类指令映射到屏幕具体坐标 / 控件的能力。 |
| Set-of-Marks (SoM) | 标记集合 | 在截图上给可交互元素叠加编号，让模型说"点 3 号"而非报坐标，大幅降低定位难度。 |
| Action Space | 动作空间 | agent 可用动作的集合（click / type / scroll / key），设计粒度直接影响成功率。 |
| Screenshot-Action Loop | 截图-动作循环 | computer use 的基本循环：截屏 → 模型选动作 → 执行 → 再截屏。 |

## Agentic 评测 · Agentic Evaluation（重点）

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| pass@k | —— | 跑 k 次至少成功一次的概率，衡量"能不能做到"（能力上限）。 |
| pass^k | —— | 跑 k 次全部成功的概率，衡量"能不能稳定做到"（可靠性），部署场景更关心它。 |
| Time Horizon | 时间跨度 | METR 提出的能力标尺：模型能以一定成功率完成的任务，对应人类需要多长时间。 |
| 50% Time Horizon | 50% 时间跨度 | 模型成功率恰为 50% 时对应的人类任务时长，常用作模型能力的单一汇总指标。 |
| Partial Credit | 部分得分 | 按完成的里程碑给分而非全有全无，让长任务评测信号更平滑。 |
| Milestone | 里程碑 | 长任务拆出的可独立判定的中间检查点。 |
| Cost-per-Success | 单次成功成本 | 平均每完成一次任务花掉的 token / 美元成本，能力相近时的关键区分指标。 |
| Task Family | 任务族 | 同一模板参数化生成的一组同质任务，支撑统计意义上的成功率估计。 |
| Elicitation | 能力激发 | 通过改 scaffolding / 提示 / 工具把模型潜在能力发挥到位，评测低估常因激发不足。 |
| Human Baseline | 人类基线 | 同一任务让人类专家做的用时与成功率，是 time horizon 标定的锚点。 |
| Grader / Scorer | 判分器 | 自动判定 episode 成败的程序（跑测试、查文件状态、或 LLM 评委）。 |

## Agent 安全 · Agent Safety（重点，防御视角）

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Prompt Injection | 提示注入 | 环境内容（网页、文件、邮件）里埋藏指令劫持 agent 行为，agent 安全的头号威胁。 |
| Indirect Prompt Injection | 间接提示注入 | 注入指令不来自用户、而是藏在 agent 读取的第三方数据里。 |
| Exfiltration | 数据外渗 | agent 被诱导把敏感数据（密钥、隐私）发送到外部的攻击结果，防御靠出口监控。 |
| Trusted Monitoring | 可信监控 | 用一个更可信（通常更弱但对齐的）模型实时审查强模型 agent 的动作。 |
| AI Control | AI 控制 | 假设模型可能不对齐，靠监控、审计、权限设计等外部协议保证安全的研究方向。 |
| HITL Gate (Human-in-the-Loop) | 人工审批闸门 | 高风险动作（删文件、发邮件、转账）必须人类批准才执行的机制。 |
| Least Privilege | 最小权限 | 只给 agent 完成任务所必需的最小工具与数据访问权。 |
| Sandbagging | 藏拙 | 模型在评测中故意表现差以隐藏真实能力，危险能力评估需要排查的现象。 |
| Red-teaming (agentic) | 红队 | 在受控 toy 环境中主动构造注入 / 诱导来暴露 agent 防线漏洞的过程。 |
