# 图机器学习 · 图神经网络

补整条几何深度学习分支：图拉普拉斯、消息传递、注意力聚合、邻居采样、图 Transformer、链接预测——纯 numpy 从零实现 GCN / GAT / GraphSAGE / 图 Transformer，小图对拍与可复现收敛。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 图与谱基础 | `01_graph_basics/` |
| 02 | 消息传递与 GCN | `02_message_passing/` |
| 03 | GAT 与 GraphSAGE | `03_gat_sage/` |
| 04 | 图 Transformer | `04_graph_transformer/` |
| 05 | 可扩展与应用 | `05_scalability_apps/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立几何深度学习的直觉与数学，再跑 `NN_*.ipynb` 用 numpy 从零实现每一种 GNN 层：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。用小图（合成 SBM、Karate club、小 Cora-like 引文图）让每个机制都可对拍——谱聚类对拍 ground-truth 社区、GCN 传播对拍稀疏与稠密两种实现、注意力系数对拍手算、训练损失单调下降。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，无需联网 / GPU / API key，也不依赖 PyG / DGL。可选 `scipy`（稀疏矩阵对照）/`networkx`（图工具与可视化），缺失自动回退到纯 numpy 实现、不影响任何 assert。

配套：[术语词典](glossary.md) · [参考清单](references.md)
