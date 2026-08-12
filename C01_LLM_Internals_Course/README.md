# LLM 内核：从零实现与理解 Transformer · 研究科学家级系统培训

> 一套从零手写 BPE、attention、GPT、解码策略到 KV cache 的体系化培训教材。
> **讲解中文 + 术语英文**，以**真实可运行的 Jupyter notebook** 为主线，每本 notebook 带 ✏️ 练习 + assert 自动判分。
> **全课 CPU 可跑** —— mini 规模模型几分钟训完，是六门课中算力门槛最低的地基课。

---

## 🎯 这套教材是什么

不是 "怎么调 API" 的速成班，而是一条**亲手把 LLM 的每个零件造一遍**的研究路径。
每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation）
2. **它在数学和工程上怎么实现？**（推导 + 从零手写代码）
3. **怎么验证你写对了？**（与 tiktoken / HuggingFace 参考实现逐项对照 + assert 判分）

读完你应该能：从空白文件写出一个能训练、能生成的 GPT；解释 KV cache 为什么省算力；亲手拟合一条 scaling law；读懂 RoPE/GQA/MoE/SSM 这些现代架构论文的核心公式。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   地基              │ 00 环境 → 01 BPE 分词 → 02 手写 Attention    │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   训练·解码·规模    │ 03 训练 mini-GPT → 04 解码策略 → 05 Scaling  │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   推理与现代架构    │ 06 KV Cache 与高效推理 → 07 现代架构          │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [Tokenization：从零实现 BPE](01_tokenization/) | `01_bpe_from_scratch.ipynb` | CPU |
| 02 | [手写 Attention 与 Transformer Block](02_attention_transformer/) | `02_attention_transformer.ipynb` | CPU |
| 03 | [从零训练 mini-GPT](03_train_minigpt/) | `03_train_minigpt.ipynb` | CPU |
| 04 | [解码策略全手写](04_decoding/) | `04_decoding_strategies.ipynb` | CPU |
| 05 | [Scaling Laws：亲手拟合](05_scaling_laws/) | `05_scaling_laws.ipynb` | CPU |
| 06 | [KV Cache 与高效推理](06_kv_cache_inference/) | `06_kv_cache.ipynb` | CPU |
| 07 | [现代架构：RoPE/GQA/MoE/SSM](07_modern_architectures/) | `07_modern_architectures.ipynb` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n internals python=3.11 -y && conda activate internals

# 2. 安装依赖（纯 CPU 即可，无需 CUDA）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name internals --display-name "LLM Internals Course"

# 4. 启动
jupyter lab
```

**无需任何 API key。** 全部 8 个模块都在 CPU 上运行：mini 规模的 GPT 在笔记本电脑上几分钟即可训完，scaling law 实验用一组小模型完成。tiktoken / transformers 只用来做参考对照（查 config、对比 tokenizer 输出），不下载大模型权重。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键论文清单（按模块组织，含 arXiv 链接）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手写代码、过 assert。
- **查漏补缺**：直接挑模块。04 解码、06 KV cache 可独立学；05 scaling laws 只依赖 03 的训练脚手架。
- **作为地基**：这是六门课中的第一块基石 —— 后续 VLM、Evals、Agents 等课程默认你已掌握本课内容。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，从零手写，CPU 可跑。*
