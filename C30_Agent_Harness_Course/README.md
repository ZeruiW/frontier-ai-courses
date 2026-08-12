# Agent Harness 从零（动手造 Agent） · 动手造 Agent 系列

> 工程实践课：**亲手造一个能跑的 agent，不依赖任何框架**。从零搭出 agent loop、工具系统、LLM 适配器（mock ↔ 真实 Claude Messages API）、鲁棒层，最后拼成一个能用工具多步完成任务的最小 agent。中文讲解 + 英文术语。每本 notebook 用**纯标准库 + 自写 MockLLM 端到端真实运行并用 assert 验证**，并附「换上真实 Claude API」的适配代码——**有 key 接真模型、没 key 自动回退 MockLLM，全程可跑、无需 API key**。

## 模块
| # | 模块 | Notebook |
|---|------|----------|
| 00 | [课程总览与环境](00_setup/00_overview.html) | `00_environment_check.ipynb` |
| 01 | [Agent 循环](01_agent_loop/01_讲解.html) | `01_agent_loop.ipynb` |
| 02 | [工具系统](02_tool_system/02_讲解.html) | `02_tool_system.ipynb` |
| 03 | [LLM 适配器](03_llm_adapter/03_讲解.html) | `03_llm_adapter.ipynb` |
| 04 | [鲁棒性](04_robustness/04_讲解.html) | `04_robustness.ipynb` |
| 05 | [最小可用 Agent](05_minimal_agent/05_讲解.html) | `05_minimal_agent.ipynb` |

## 怎么用
1. 打开 [`index.html`](index.html) 进课程主页，或直接读各模块的 HTML 讲解建立直觉。
2. 跑 notebook 亲手从零实现：**学全部机制只需 Python 3.8+ 标准库，无需任何第三方包、无需 API key**（MockLLM 端到端驱动）。

```bash
jupyter lab          # 逐 cell 运行；纯标准库即可跑通全部 worked / 练习 / 胶囊
```

3. （可选）接真实 Claude：
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
# 同一份代码会自动走真实路径(claude-opus-4-8); 无 key 则回退 MockLLM
```

- [`glossary.md`](glossary.md) 术语词典 · [`references.md`](references.md) 参考清单（★ ReAct、Anthropic «Building effective agents»、Messages API / tool use 文档、Toolformer 等）

## 特色
- **不依赖框架**：不装 LangChain/AutoGPT，从零造 agent loop / 工具系统 / 适配器 / 鲁棒层。
- **端到端真实验证**：每个 agent 用确定性 MockLLM 真实运行、用 `assert` 验证它确实多步完成任务（不是伪代码）。
- **接真实 Claude，无 key 不阻断**：每个 notebook 附 Claude Messages API 适配（`tool_use`/`tool_result` 协议），有 key 接真模型、没 key 自动回退 MockLLM。
- **每个练习 assert 判分**：✏️ 练习给骨架 + 自测 assert + 📖 参考答案；🧪 胶囊接真实 Claude。
