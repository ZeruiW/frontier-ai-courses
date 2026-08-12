# MLOps 与生产生命周期

训练完和上线后才是开始：实验追踪、数据/模型版本、评测门禁与 CI/CD、监控与漂移检测、反馈闭环与重训练——从零实现一套能跑的 ML 生命周期工具。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 实验追踪 | `01_experiment_tracking/` |
| 02 | 数据与模型版本 | `02_versioning/` |
| 03 | 评测门禁与 CI/CD | `03_cicd_gates/` |
| 04 | 监控与漂移 | `04_monitoring_drift/` |
| 05 | 反馈闭环与重训练 | `05_feedback_retraining/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）建立直觉 + `NN_*.ipynb` 从零实现（worked 示例 → ✏️ 练习(TODO+assert) → 📖 参考答案）。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯标准库 + numpy（部分课用 pandas），无需联网/GPU/API key。

配套：[术语词典](glossary.md) · [参考清单](references.md)
