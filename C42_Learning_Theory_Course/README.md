# 学习理论与优化理论

不止知道深度学习「有效」，而是理解它「为什么」有效：PAC/VC/Rademacher 泛化界、GD/SGD 收敛率、NTK 无限宽、隐式偏置、深度泛化与 PAC-Bayes——用纯 numpy 数值实验把每个界与收敛率钉死，研究科学家的理论脊梁。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与世界观 | `00_setup/` |
| 01 | 统计学习理论 | `01_statistical_learning/` |
| 02 | 优化理论 | `02_optimization_theory/` |
| 03 | NTK 与无限宽 | `03_ntk_infinite_width/` |
| 04 | 隐式偏置 | `04_implicit_bias/` |
| 05 | 深度泛化 | `05_generalization_deep/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先把抽象的界与收敛率讲到能写下证明骨架，再跑 `NN_讲解.ipynb`（00 为 `00_environment_check.ipynb`）用纯 numpy 做数值实验把理论钉死：先看 worked 示例（`print` 出「理论预测」与「实测」并 `assert` 两者一致）→ ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。看经验风险随 n 收敛、实测收敛率对拍理论速率、经验 NTK 随宽度趋稳、过参数 logistic 收敛到 max-margin 方向。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU、秒级可跑，无需联网 / GPU / API key。每个界、收敛率、公式都经数值核验，每个 notebook 的 assert 都把「理论 ≈ 实测」断言为真。

配套：[术语词典](glossary.md) · [参考清单](references.md)
