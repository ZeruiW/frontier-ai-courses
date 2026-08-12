# 上下文工程与记忆 · 动手造 Agent 系列

> 工程实践课：亲手造一个能跑的 agent / 编码 agent / skills 系统，不依赖 Claude Code 等框架。中文讲解+英文术语，每本 notebook 用 MockLLM 端到端真实验证，并附接真实 Claude API 的适配代码。CPU 可跑、无需 API key。

## 模块
| # | 模块 | Notebook |
|---|------|----------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` |
| 01 | [Token 预算与截断](01_token_budget/) | `01_token_budget.ipynb` |
| 02 | [Compaction 与摘要](02_compaction/) | `02_compaction.ipynb` |
| 03 | [文件记忆](03_memory/) | `03_memory.ipynb` |
| 04 | [检索入上下文](04_retrieval/) | `04_retrieval.ipynb` |
| 05 | [Prompt 缓存与长会话](05_prompt_caching/) | `05_prompt_caching.ipynb` |

```bash
pip install -r requirements.txt && jupyter lab
```
- [`glossary.md`](glossary.md) · [`references.md`](references.md)
