# 模型压缩与高效化（前沿） · 前沿 AI 系统培训

> SOTA 前沿课，领先实验室真实在用的技术。**不止会调用 bitsandbytes/AutoGPTQ/AutoAWQ，而是会从零写出它们的核心**：纯 numpy 在 CPU 上实现量化/误差补偿/fp8/蒸馏/剪枝并与全精度对拍。中文讲解 + 英文术语，真实 GPT-2 权重可选（联网失败回退合成），每本 ✏️ 练习 + assert 判分。

## 怎么用
每个模块先读 **HTML 讲解**（建立「为什么这样压才不掉点」的直觉与数学），再跑 **notebook**（从零实现 + 对拍全精度 + ✏️ 练习 assert 判分）。从 [`index.html`](index.html) 进入，模块间有 pager 串联。

## 模块
| # | 模块 | 讲解 | Notebook |
|---|------|------|----------|
| 00 | [课程总览与环境](00_setup/) | `00_overview.html` | `00_environment_check.ipynb` |
| 01 | [整数量化](01_quantization/) | `01_讲解.html` | `01_quantization.ipynb` |
| 02 | [GPTQ 与 AWQ](02_gptq_awq/) | `02_讲解.html` | `02_gptq_awq.ipynb` |
| 03 | [fp8 训练](03_fp8_training/) | `03_讲解.html` | `03_fp8_training.ipynb` |
| 04 | [知识蒸馏](04_distillation/) | `04_讲解.html` | `04_distillation.ipynb` |
| 05 | [剪枝与稀疏](05_pruning/) | `05_讲解.html` | `05_pruning.ipynb` |

五大支柱统一在一个框架下：**压缩 = 带约束的逐层近似** `min ‖Wx − Ŵx‖²`（约束 = 量化网格 / 稀疏 / 小模型）。GPTQ↔RTN、SparseGPT↔幅度剪枝 共用同一套逆 Hessian 误差补偿。

```bash
pip install -r requirements.txt && jupyter lab
```
- [`glossary.md`](glossary.md)（术语词典）· [`references.md`](references.md)（论文清单，★ 标必读：LLM.int8()、GPTQ、AWQ、FP8 Formats、Hinton 蒸馏、SparseGPT、2:4 稀疏、彩票假说）

> 纯 numpy / CPU 可跑，无需 GPU。notebook 代码已实跑验证（每本 assert 全过、0 失败）。
