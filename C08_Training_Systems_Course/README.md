# 大模型训练与推理系统 · 研究科学家级系统培训

> 一套面向 model evaluation 研究科学家的 large-model systems 课程。
> **讲解中文 + 英文术语**，以真实可运行的 Jupyter notebook 为主线，每本 notebook 带 ✏️ 练习 + assert 自动判分。
> **全课 CPU 可跑** —— 只依赖 numpy / pandas / matplotlib / 标准库，不需要 GPU、API key 或大模型权重。

---

## 🎯 这套教材是什么

不是 CUDA 编程课，也不是框架 API 课，而是训练/推理系统的一阶账本训练：给定模型规模、上下文、硬件和并行策略，你能估算显存、吞吐、延迟、成本和瓶颈。

读完你应该能：解释 params/grads/optimizer/activation/KV cache 账本，比较并行策略，推导 FlashAttention online softmax，手写量化与 serving 模拟，并完成“多少卡训多久”的面试题。

---

## 🗺️ 学习路径

`00 → 01 → 02 → 03 → 04 → 05 → 06 → 07`

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [显存解剖与 Roofline](01_memory_roofline/) | `01_memory_roofline.ipynb` | CPU |
| 02 | [混合精度与重计算](02_mixed_precision_checkpointing/) | `02_mixed_precision_checkpointing.ipynb` | CPU |
| 03 | [并行策略：DP/TP/PP/ZeRO/FSDP](03_parallelism_strategies/) | `03_parallelism_strategies.ipynb` | CPU |
| 04 | [FlashAttention：Online Softmax 与 IO 复杂度](04_flashattention/) | `04_flashattention.ipynb` | CPU |
| 05 | [量化从零：int8/int4 与 GPTQ/AWQ 思想](05_quantization_from_scratch/) | `05_quantization_from_scratch.ipynb` | CPU |
| 06 | [推理服务：KV Cache、Batching、Speculative Decoding](06_inference_serving/) | `06_inference_serving.ipynb` | CPU |
| 07 | [训练成本估算面试题](07_training_cost_interview/) | `07_training_cost_interview.ipynb` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
conda create -n training-systems python=3.11 -y && conda activate training-systems
pip install -r requirements.txt
python -m ipykernel install --user --name training-systems --display-name "Training Systems Course"
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
