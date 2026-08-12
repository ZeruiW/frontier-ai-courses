# 机制可解释性：打开模型黑盒的显微镜 · 研究科学家级系统培训

> 一套从 linear probe、logit lens、induction heads、activation patching 到 SAE 与 steering vectors 的体系化培训教材。
> **讲解中文 + 术语英文**，以**真实可运行的 Jupyter notebook** 为主线，每本 notebook 带 ✏️ 练习 + assert 自动判分。
> **全课纯 numpy 从零实现** —— 无需 torch、无需下载模型权重、无需 API key，笔记本电脑 CPU 秒级运行。这是本课的卖点：每一个 interp 方法都亲手在 toy model 上造一遍，而不是调 TransformerLens 的黑盒函数。

---

## 🎯 这套教材是什么

这是 RS-Evaluation 技能栈的**第 7 门课**。前六门课教你测模型的**行为**（黑盒：benchmark、judge、红队）；这门课教你打开**内部**（白盒：表示、电路、特征）。每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation：为什么行为证据不够）
2. **它在数学和工程上怎么实现？**（推导 + 纯 numpy 从零手写）
3. **怎么验证你做对了？**（在已知 ground truth 的 toy model 上复现论文结论 + assert 判分）

读完你应该能：从零写出 linear probe 并用 control task 检验它没作弊；解释 residual stream 为什么是 interp 的核心视角；手工构造一个会 in-context copy 的 induction circuit；用 activation patching 定位行为的因果来源；复现 Toy Models of Superposition 并从零训一个 SAE；用一根 steering vector 改变模型行为；最后把这些工具用回评测与安全审计。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   地基·表示与透镜    │ 00 总览 → 01 Linear Probes → 02 Logit Lens  │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   电路与因果        │ 03 QK/OV 与 Induction → 04 Activation       │
                    │    Patching（因果干预）                       │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   特征分解          │ 05 Superposition 与 SAE → 06 Steering       │
                    │    Vectors 与表示工程                         │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   应用·评测与审计    │ 07 Interp × 评测与安全审计                    │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [Linear Probes：表示即向量](01_linear_probes/) | `01_linear_probes.ipynb` | CPU |
| 02 | [Residual Stream 与 Logit Lens](02_logit_lens/) | `02_logit_lens.ipynb` | CPU |
| 03 | [QK/OV 电路与 Induction Heads](03_attention_induction/) | `03_induction_heads.ipynb` | CPU |
| 04 | [Activation Patching：因果干预](04_activation_patching/) | `04_activation_patching.ipynb` | CPU |
| 05 | [叠加假说与稀疏自编码器](05_superposition_sae/) | `05_superposition_sae.ipynb` | CPU |
| 06 | [Steering Vectors 与表示工程](06_steering/) | `06_steering_vectors.ipynb` | CPU |
| 07 | [Interp × 评测与安全审计](07_interp_for_evals/) | `07_interp_for_evals.ipynb` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n interp python=3.11 -y && conda activate interp

# 2. 安装依赖（纯 numpy 技术栈，无需 CUDA、无需 torch）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name interp --display-name "Interpretability Course"

# 4. 启动
jupyter lab
```

**无需任何 API key，也无需 torch。** 全部 8 个模块都用 numpy 在 toy model 上从零实现：toy transformer 的前向传播手写、SAE 的训练循环手写、patching 的 hook 机制手写。这样做的代价是模型小，收益是每一步都没有黑盒——这正是 interp 课该有的样子。学完后迁移到 TransformerLens / SAELens 等真实工具只是换 API。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（约 50 个核心术语，中英对照）
- [`references.md`](references.md) —— 关键论文清单（按模块组织，含 arXiv 链接与一句话点评）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手写代码、过 assert。
- **查漏补缺**：直接挑模块。01/02 可独立学；04 依赖 03 的 toy transformer；06 依赖 01 的"方向即概念"直觉；07 综合全课。
- **面试准备**：03（induction heads）、04（patching）、05（superposition/SAE）是 interp 方向面试的高频考点。

---

## 🔗 与其他六门课的衔接

本课是技能栈中的**显微镜**：其他课测行为，本课看机制。

| 课程 | 关系 |
|------|------|
| [`LLM_Internals_Course`](../LLM_Internals_Course/) | **前置**。本课默认你已手写过 attention 与 residual connection（其 02 模块）；本课把同一个 residual stream 从"工程部件"重新解读为"通信总线"。 |
| [`LLM_Evals_Course`](../LLM_Evals_Course/) | **互补的另一半**。行为评测只能告诉你模型在测的分布上做对了没有；interp 提供机制证据回答"它是真会还是背题/走捷径"。probe 的 selectivity 检验与 eval 的统计严谨性是同一种方法论洁癖。 |
| [`Safety_Evals_Course`](../Safety_Evals_Course/) | **直接下游**。其 05 模块（sandbagging 与评测完整性）和 07 模块（safety case）依赖白盒证据：probing 测谎/检测隐藏目标、refusal direction 解释越狱、model diffing 审计后训练改动——这些正是本课 06/07 模块的内容。 |
| [`Post_Training_Course`](../Post_Training_Course/) | RLHF/DPO 到底改了模型内部的什么？model diffing 与 refusal direction（本课 06/07）是回答这个问题的工具。 |
| [`AI_Agents_Course`](../AI_Agents_Course/) | agent 的不可解释行为（如 reward hacking 的内部前兆）是 interp 监控的应用场景。 |
| [`VLM_Multimodal_Course`](../VLM_Multimodal_Course/) | 多模态分支。probing 与 patching 同样适用于视觉表示。 |

一句话：**evals 给你模型行为的统计描述，interp 给你机制解释——audit 一个前沿模型两者缺一不可。**

---

*Built as a self-study research curriculum. 中文讲解，英文术语，纯 numpy 从零手写，CPU 可跑。*
