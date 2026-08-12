# 推荐系统与大规模排序

工业界最大的机器学习就业面（推荐 · 搜索 · 排序）：协同过滤、矩阵分解、双塔召回、排序学习、CTR/序列推荐——用 numpy 从零实现召回→粗排→精排→重排整条漏斗，真实 MovieLens-like 数据。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 协同过滤 | `01_collaborative_filtering/` |
| 02 | 矩阵分解 | `02_matrix_factorization/` |
| 03 | 双塔召回 | `03_two_tower_retrieval/` |
| 04 | 排序学习 | `04_learning_to_rank/` |
| 05 | CTR 与序列推荐 | `05_ctr_sequential/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立推荐系统的世界观与数学直觉，再跑 `NN_*.ipynb` 用 numpy 从零实现每一个核心算法（协同过滤、矩阵分解、双塔、BPR、FM、序列推荐）：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。每个模型都对拍参考实现或验证损失单调下降，跑出真实的 `Recall@K` / `nDCG@K`。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy/pandas / CPU，无需 GPU / API key，也不依赖 TensorFlow Recommenders / RecBole（仅作设计对照提及）。可选 `scikit-learn` 用于加载真实 MovieLens-like 数据，联网失败或缺失则自动回退到可复现的合成数据、不影响任何 assert。

配套：[术语词典](glossary.md) · [参考清单](references.md)
