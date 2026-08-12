# ML 基础与面试数学 · 研究科学家级系统培训

> 一套面向 model evaluation 研究科学家的 ML/math foundations 课程。
> **讲解中文 + 英文术语**，以真实可运行的 Jupyter notebook 为主线，每本 notebook 带 ✏️ 练习 + assert 自动判分。
> **全课 CPU 可跑** —— 只依赖 numpy / pandas / matplotlib / 标准库，不需要 GPU、API key 或大模型权重。

---

## 🎯 这套教材是什么

不是“机器学习八股”清单，而是一条把白板推导、numpy 实现和评测口径连起来的训练路径。每个模块都回答：公式从哪里来、代码怎么写、面试时怎么解释边界。

读完你应该能：手推 backprop、解释 MLE/KL/CI、从零写经典监督/无监督算法、判断泛化与校准问题，并把这些能力组织成面试回答。

---

## 🗺️ 学习路径

`00 → 01 → 02 → 03 → 04 → 05 → 06 → 07`

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [矩阵微积分与 Backprop 手推](01_matrix_calculus_backprop/) | `01_matrix_calculus_backprop.ipynb` | CPU |
| 02 | [概率统计与信息论](02_probability_statistics_info/) | `02_probability_statistics_info.ipynb` | CPU |
| 03 | [经典监督学习从零](03_supervised_learning_scratch/) | `03_supervised_learning_scratch.ipynb` | CPU |
| 04 | [无监督学习：PCA、K-means、GMM/EM](04_unsupervised_learning/) | `04_unsupervised_learning.ipynb` | CPU |
| 05 | [优化器从零：SGD→AdamW](05_optimizers_from_scratch/) | `05_optimizers_from_scratch.ipynb` | CPU |
| 06 | [泛化与指标](06_generalization_metrics/) | `06_generalization_metrics.ipynb` | CPU |
| 07 | [ML 面试 Drills](07_ml_interview_drills/) | `07_ml_interview_drills.ipynb` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
conda create -n ml-foundations python=3.11 -y && conda activate ml-foundations
pip install -r requirements.txt
python -m ipykernel install --user --name ml-foundations --display-name "ML Foundations Course"
jupyter lab
```

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 关键论文、博客与系统文档清单

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解，再跑 notebook。
- **刷题学**：每本 notebook 的 ✏️ 练习都可单独做；assert 全过即过关。
- **面试准备**：重点看每章公式表、陷阱 callout 和最后的 drills。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，从零手写，CPU 可跑。*
