# 多智能体编排与生产化 · 动手造 Agent 系列

> 工程实践课：亲手造一个能跑的 agent / 编码 agent / skills 系统，不依赖 Claude Code 等框架。中文讲解+英文术语，每本 notebook 用 MockLLM 端到端真实验证，并附接真实 Claude API 的适配代码。CPU 可跑、无需 API key。

## 模块
| # | 模块 | Notebook |
|---|------|----------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` |
| 01 | [Subagent](01_subagents/) | `01_subagents.ipynb` |
| 02 | [编排模式](02_orchestration/) | `02_orchestration.ipynb` |
| 03 | [权限与沙箱](03_permissions/) | `03_permissions.ipynb` |
| 04 | [可观测与评测](04_observability/) | `04_observability.ipynb` |
| 05 | [部署 Agent](05_deploy/) | `05_deploy.ipynb` |

```bash
pip install -r requirements.txt && jupyter lab
```
- [`glossary.md`](glossary.md) · [`references.md`](references.md)
