# 构建编码 Agent（你的 Claude Code） · 动手造 Agent 系列

> 工程实践课：**亲手造一个能跑的编码 agent，不依赖任何框架**。一个编码 agent = LLM + 一组工具 + 一个循环——本课把工具（文件/shell/搜索/测试）与循环（edit-test-fix、agent 主循环）一层层从零用**纯标准库**写出来。每本 notebook 用确定性的 **MockLLM** 把「LLM ↔ 工具」循环**端到端跑通**：文件、shell、pytest 全部在 `tempfile` 临时目录里**真实执行**，因此 agent 能在玩具仓库里**真的把 bug 修好、把测试跑绿**。每本都附对接**真实 Claude（Anthropic Messages API, tool use）**的适配代码，**没有 API key 时自动回退 MockLLM，绝不阻断**。中文讲解 + 英文术语，CPU 可跑、无需 GPU/API key。

## 模块
| # | 模块 | 角色 | Notebook |
|---|------|------|----------|
| 00 | [课程总览与环境](00_setup/) | 世界观 + 方法论 | `00_environment_check.ipynb` |
| 01 | [文件工具](01_file_tools/) | 手（read/write/精确编辑/diff/路径安全） | `01_file_tools.ipynb` |
| 02 | [Shell 工具](02_shell_tool/) | 脚（subprocess/超时/截断/cwd/危险命令防护） | `02_shell_tool.ipynb` |
| 03 | [代码导航](03_code_search/) | 眼（grep/glob/智能遍历/符号搜索/排序） | `03_code_search.ipynb` |
| 04 | [Edit-Test-Fix 循环](04_edit_test_loop/) | 小脑（解析 pytest/定位/收敛/防死循环） | `04_edit_test_loop.ipynb` |
| 05 | [完整编码 Agent](05_coding_agent/) | 集大成（注册表+主循环+评测+真实 Claude） | `05_coding_agent.ipynb` |

每模块含 `NN_讲解.html`（9–10K 字深讲）+ `NN_*.ipynb`（30+ cells：worked print+assert → ✏️ 练习 TODO+assert 自测 → 📖 答案 → 🧪 真实数据胶囊）。

## 跑起来
```bash
pip install -r requirements.txt   # 纯标准库即可；anthropic 仅在接真实 API 时需要
jupyter lab
```
全部 notebook 的 worked / 答案 / 自测 cell 已在 `courses` 环境实跑验证：**0 个 assert 失败**（含真跑 pytest、真实 stdlib 源码/包搜索、端到端修 bug）。

- [`glossary.md`](glossary.md)（术语词典，≥12KB）· [`references.md`](references.md)（论文清单，★ 必读：Claude Code、SWE-bench、SWE-agent、aider、Anthropic Messages API/tool use）
