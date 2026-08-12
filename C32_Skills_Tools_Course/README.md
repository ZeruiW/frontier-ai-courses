# Skills 与工具生态（不依赖框架） · 动手造 Agent 系列

> 工程实践课：**亲手造**一个 agent 的可扩展性子系统——skills、slash 命令、MCP server、插件——**不依赖任何框架**（不依赖 Claude Code），只用 Python 标准库。中文讲解 + 英文术语，每本 notebook 用 **MockLLM 端到端真实验证**（CPU 可跑、无需 API key），并附「换上真实 Claude API」的适配代码（`messages.create(model=...)`，**无 key 自动回退 MockLLM**，绝不阻断）。

本课立场：不止会**用** Claude Code 的 skills / slash / MCP / 插件，而是会**亲手把它们的内核造出来**。把「让 agent 可扩展」拆成可独立验证的零件，一层层从零搭起。

## 世界观

能力 = 一条流水线：`磁盘上的能力 → 发现(读轻量描述) → 注册表 → 按相关性选择 → 注入/调用`，贯穿原则是**渐进披露**（轻量描述常驻、完整内容按需加载）。

## 模块
| # | 模块 | Notebook |
|---|------|----------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` |
| 01 | [Skill 定义与加载](01_skill_loading/) | `01_skill_loading.ipynb` |
| 02 | [Slash 命令与动态注入](02_slash_commands/) | `02_slash_commands.ipynb` |
| 03 | [从零造 MCP Server](03_mcp_server/) | `03_mcp_server.ipynb` |
| 04 | [工具打包与插件](04_tool_packaging/) | `04_tool_packaging.ipynb` |
| 05 | [完整 Skills 系统](05_skills_system/) | `05_skills_system.ipynb` |

每个模块 = 一篇 `NN_讲解.html`（建立直觉与协议框架）+ 一本 notebook（从零实现 → ✏️ 练习 `assert` 判分 → 📖 参考答案 → 🧪 真实数据胶囊）。

```bash
# 本课纯标准库，无需安装任何东西即可跑通所有 notebook
jupyter lab
# 想接真实 Claude（可选，无 key 自动回退 MockLLM）：
pip install -r requirements.txt   # anthropic SDK
```
- [`glossary.md`](glossary.md)（术语词典）· [`references.md`](references.md)（参考清单：Anthropic Agent Skills、MCP 规范、Claude Code slash commands / plugins、JSON-RPC 2.0、渐进披露 等）
