# 分布式训练工程

不止会算分布式训练的账，而是会把它工程化地跑起来、调通、救活：集合通信、数据并行/FSDP、张量/流水并行、分片 checkpoint 与容错、编排与调试——用 numpy 在单进程内模拟多 rank 并对拍单卡，旁附 torch.distributed / FSDP / Megatron 真实代码。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 集合通信原语 | `01_collectives/` |
| 02 | 数据并行与 FSDP | `02_data_parallel_fsdp/` |
| 03 | 张量与流水并行 | `03_tensor_pipeline_parallel/` |
| 04 | Checkpoint 与容错 | `04_checkpointing_faulttol/` |
| 05 | 编排与调试 | `05_orchestration_debug/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立分布式训练的工程直觉与成本模型，再跑 `NN_*.ipynb` 用 numpy 在单进程内从零模拟多 rank：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。把多个 rank 模拟成一组数组（all-reduce = 对 rank 列表求和、分片显存 = 每 rank 算自己那 1/W、bubble = 流水线甘特图的空格数），每个机制都与单卡参考 `np.allclose` 对拍到 1e-10。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，本环境无需多 GPU / NCCL / 联网 / API key——用单进程模拟多 rank。旁附的 `torch.distributed` / FSDP / Megatron 代码仅作可迁移对照展示，不参与运行。

配套：[术语词典](glossary.md) · [参考清单](references.md)
