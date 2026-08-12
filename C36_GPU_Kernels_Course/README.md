# GPU 内核与性能工程

不止用 FlashAttention，而是会写它：GPU 执行模型、内存合并、分块矩阵乘、并行规约与融合 softmax、FlashAttention 内核——用 numpy 模拟 GPU 编程模型并对拍参考实现，旁附 Triton 伪代码。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 执行模型 | `01_execution_model/` |
| 02 | 内存层级与合并访问 | `02_memory_coalescing/` |
| 03 | 分块矩阵乘 | `03_tiled_matmul/` |
| 04 | 规约与融合 softmax | `04_reductions_softmax/` |
| 05 | FlashAttention 内核 | `05_flash_attention/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）建立直觉 + `NN_*.ipynb` 从零实现（worked 示例 → ✏️ 练习(TODO+assert) → 📖 参考答案）。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯标准库 + numpy（部分课用 pandas），无需联网/GPU/API key。

配套：[术语词典](glossary.md) · [参考清单](references.md)
