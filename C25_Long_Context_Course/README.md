# 长上下文与高效注意力（前沿） · 前沿 AI 系统培训

> SOTA 前沿课，领先实验室真实在用的技术。中文讲解+英文术语，真实数据 notebook，每本 ✏️练习+assert 判分。CPU 可跑。

## 模块
| # | 模块 | Notebook |
|---|------|----------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` |
| 01 | [RoPE Scaling 与 YaRN](01_rope_scaling/) | `01_rope_scaling.ipynb` |
| 02 | [FlashAttention](02_flash_attention/) | `02_flash_attention.ipynb` |
| 03 | [稀疏与滑窗注意力](03_sparse_attention/) | `03_sparse_attention.ipynb` |
| 04 | [线性注意力与 SSM](04_linear_ssm/) | `04_linear_ssm.ipynb` |
| 05 | [KV 压缩与长上下文评测](05_kv_compression/) | `05_kv_compression.ipynb` |

```bash
pip install -r requirements.txt && jupyter lab
```
- [`glossary.md`](glossary.md) · [`references.md`](references.md)
