# 深度学习理论与数据/生成媒体评测 · 研究科学家级系统培训

> 把反常的评测曲线与数据陷阱缩小成**能手算、能 numpy 跑通、能 assert 验证**的玩具。
> **讲解中文 + 英文术语**，以真实可运行 Jupyter notebook 为主线，每本带 ✏️ 练习 + assert 自动判分 + 📖 参考答案 + 🧪 真实数据胶囊。
> **纯 numpy · CPU 可跑** —— 只依赖 numpy（matplotlib/pandas 可选），每条曲线、每个指标都可逐位复现。

本课的立场：double descent 的二次下降、grokking 的延迟跳变、涌现是不是度量假象、自训练为何会让分布坍塌、FID/IS 到底在量什么——这些看似反常的现象，大多能在玩具规模上**精确复现并讲清**。我们不停在「读过论文」，而是把每个现象从零实现、对拍验证。

## 🗺️ 模块

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [泛化与双下降](01_generalization_double_descent/) | `01_generalization_double_descent.ipynb` | CPU |
| 02 | [Grokking 与涌现](02_grokking_emergence/) | `02_grokking_emergence.ipynb` | CPU |
| 03 | [数据流水线](03_data_pipeline/) | `03_data_pipeline.ipynb` | CPU |
| 04 | [合成数据与模型坍塌](04_synthetic_data/) | `04_synthetic_data.ipynb` | CPU |
| 05 | [生成媒体评测](05_generative_media_eval/) | `05_generative_media_eval.ipynb` | CPU |

每个模块 = HTML 讲解（8–9 节、~9000 字符）+ notebook（35+ cells：worked 从零复现 → ✏️ 练习 → 📖 答案 → 🧪 真实数据胶囊）。

> 也可以直接打开 [`index.html`](index.html)。

## 各模块复现什么（纯 numpy 玩具）

- **01 双下降**：bias-variance 分解、经典 U 型、随机特征回归从零画出 double descent 曲线（尖峰在 p≈n、二次下降）、最小范数解与隐式正则。
- **02 Grokking / 涌现**：忠实可靠地复现 grokking（记忆解→泛化解的迁移，weight decay 驱动，progress measure 平滑爬升）；Schaeffer 的「度量假象」（同一能力 exact-match 看是跳变、连续度量看是平滑）。
- **03 数据流水线**：清洗、质量过滤、**MinHash 近重复去重**（签名相等率无偏估计 Jaccard）、shuffle 缓冲偏差、分片、端到端流水线 + 吞吐统计。
- **04 合成数据 / 模型坍塌**：递归自训练的**方差几何收缩**（对拍 ((N-1)/N)^g 理论）、mode dropping、质量-多样性权衡、真实数据锚定 / 累积 vs 替换的缓解。
- **05 生成媒体评测**：从零算 **FID**（含矩阵平方根）、**IS**（含 KL）、**improved precision-recall**（k-NN 流形）；保真 vs 多样为何必须分开看、各指标能被怎样钻空子。

## 🚀 快速开始
```bash
pip install -r requirements.txt && jupyter lab
```
仅 `numpy` 为必需；`matplotlib`/`pandas` 可选。全课 CPU 秒级到分钟级运行，无需 GPU。

## 📚 配套
- [`glossary.md`](glossary.md) 术语词典（≥12KB，按主题分组）· [`references.md`](references.md) 论文清单（≥8KB，★ 标必读）

*中文讲解，英文术语，玩具可复现，CPU 可跑，每条结论 assert 兜底。*
