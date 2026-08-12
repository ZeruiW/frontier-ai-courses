# 参考清单 · References（分布式训练工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 在单进程内模拟的每个机制，都能在下列文献里找到真实集群上的对应实现与权衡。

## 集合通信与拓扑 · Collectives & Topology
- ★ **Patarasuk & Yuan 2009, _Bandwidth Optimal All-reduce Algorithms for Clusters of Workstations_** — ring all-reduce 的奠基论文。证明把 rank 排成环、分 reduce-scatter + all-gather 两阶段，每 rank 收发的数据量与节点数无关（带宽最优）。本课模块 01 全程在复现它，理解「为什么 all-reduce 的通信量不随 W 爆炸」必读。
- ★ **Thakur, Rabenseifner & Gropp 2005, _Optimization of Collective Communication Operations in MPICH_** — 系统梳理 all-reduce/all-gather/broadcast 等的多种算法（recursive doubling、ring、tree）及其延迟-带宽权衡。解释了框架为何按消息大小切换算法，模块 01 成本模型的理论来源。
- **NVIDIA, _NCCL（NVIDIA Collective Communications Library）文档与博客_** — 生产级 GPU 集合通信库：在 NVLink/InfiniBand 上实现 ring/tree all-reduce，自动探测拓扑选算法。本课所有 collective 的真实对应实现，调优分布式训练必读其环境变量（`NCCL_DEBUG`、`NCCL_ALGO`）。
- **Sergeev & Del Balso 2018, _Horovod: fast and easy distributed deep learning in TensorFlow_** — 把 ring all-reduce 引入主流深度学习框架的工程化工作，提出 tensor fusion（≈ 梯度分桶）。理解数据并行通信工程化的早期里程碑。

## 数据并行、ZeRO 与 FSDP · Data Parallel, ZeRO & FSDP
- ★ **Rajbhandari, Rasley, Ruwase & He 2020, _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_** — 本课模块 02 的核心。提出把数据并行中冗余的优化器状态/梯度/参数逐级分片（ZeRO-1/2/3），显存近线性下降而保持数据并行的编程模型。必读，配合 DeepSpeed 文档看每一阶段的通信量代价。
- ★ **Zhao et al. 2023, _PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel_** — FSDP（ZeRO-3 的 PyTorch 原生实现）的设计与工程经验：参数按 unit 分片、前向/反向时 all-gather 出完整层用完即弃、prefetch 与通信重叠。模块 02 的真实代码对照，讲清了分片粒度与显存峰值的取舍。
- **Rajbhandari et al. 2021, _ZeRO-Infinity: Breaking the GPU Memory Wall for Extreme Scale Deep Learning_** — 把分片进一步下沉到 CPU/NVMe（offload），用慢存储换显存，让单机也能跑超大模型。理解「显存墙」之外的存储层级权衡。
- **Ren et al. 2021, _ZeRO-Offload: Democratizing Billion-Scale Model Training_** — 把优化器状态与更新计算卸载到 CPU，让消费级硬件也能训大模型。模块 02 前沿一节的延伸阅读。

## 张量并行、流水并行与 3D 并行 · TP, PP & 3D
- ★ **Shoeybi et al. 2019, _Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism_** — 张量并行的奠基论文。提出把 MLP 设计成「列并行→行并行」使前向只需 1 次 all-reduce、注意力按 head 切，是模块 03 张量并行一节的直接来源。必读。
- ★ **Narayanan et al. 2021, _Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM_** — 3D 并行（DP×TP×PP）的系统性工作：如何组合三种并行、interleaved 1F1B 调度降 bubble、维度该怎么分配（TP 放节点内、PP 跨节点）。模块 03 后半与「3D 并行」一节的蓝本。
- ★ **Huang et al. 2019, _GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism_** — 流水线并行的奠基论文。提出 micro-batch 填充流水线 + re-materialization，给出 bubble 比例 (P−1)/(m+P−1)。模块 03 流水并行与 bubble 公式的来源。
- ★ **Narayanan et al. 2019, _PipeDream: Generalized Pipeline Parallelism for DNN Training_** — 提出 1F1B 调度与异步流水，降低激活显存峰值与 bubble。模块 03「1F1B」一节的直接出处，理解流水线调度演进必读。
- **Qi et al. 2023, _Zero Bubble Pipeline Parallelism_** — 把反向拆成「算输入梯度」与「算权重梯度」两半并重排调度，几乎消除 bubble。模块 03 前沿一节的代表性进展。
- **Zheng et al. 2022, _Alpa: Automating Inter- and Intra-Operator Parallelism for Distributed Deep Learning_** — 自动搜索并行策略（把 TP/PP/DP 的组合当成编译问题）。模块 03/05 前沿「auto-parallel」的代表作。

## Checkpoint 与容错 · Checkpointing & Fault Tolerance
- ★ **Mohan, Phanishayee & Chidambaram 2021, _CheckFreq: Frequent, Fine-Grained DNN Checkpointing_** — 自动调节 checkpoint 频率、把序列化与写盘流水化并与计算重叠，使频繁 checkpoint 几乎零开销。模块 04 异步/最优频率一节的核心，必读。
- ★ **Daly 2006, _A higher order estimate of the optimum checkpoint interval for restart dumps_**（及 Young 1974 的一阶估计） — 给出最优 checkpoint 间隔 ≈ √(2·δ·MTBF) 的推导，平衡写盘开销与故障丢失的计算。模块 04 公式来源。
- **Wang et al. 2023, _GEMINI: Fast Failure Recovery in Distributed Training with In-Memory Checkpoints_** — 把 checkpoint 存到其他节点的主机内存（冗余副本），恢复时从内存秒级载入，而非慢速持久化存储。模块 04 前沿「in-memory/redundancy」的代表。
- **Eisenman et al. 2022, _Check-N-Run: a Checkpointing System for Training Deep Learning Recommendation Models_** — 工业界（Meta）大规模 checkpoint 系统：差分 checkpoint、量化压缩。理解生产环境 checkpoint 的工程取舍。
- **PyTorch, _Distributed Checkpoint (DCP) 文档_** 与 **TorchElastic / torchrun 文档** — 真实的分片 checkpoint 保存/加载与弹性训练（`--max-restarts`、rendezvous）接口。模块 04 真实代码对照，落地必读。

## 编排、扩展与可观测性 · Orchestration, Scaling & Observability
- ★ **Amdahl 1967, _Validity of the single processor approach to achieving large scale computing capabilities_** — 阿姆达尔定律原始论文。串行比例决定加速比上限，是一切扩展效率分析的天花板。模块 05 strong scaling 一节的基石。
- ★ **Narayanan et al. 2021（同上 Megatron 集群论文）的 MFU 与扩展效率分析** — 给出在数千 GPU 上 strong/weak scaling 的实测曲线与 MFU（模型算力利用率）定义。模块 05 扩展效率一节的现实标尺。
- **Chowdhery et al. 2022, _PaLM: Scaling Language Modeling with Pathways_** — 报告了 6144 TPU 上的训练系统与 MFU（~46%），是大规模编排与效率的工程标杆。读它体会「把效率从 30% 提到 50%」意味着什么。
- **Jiang et al. 2024, _MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs_** — 万卡训练的端到端工程：诊断 straggler、网络/通信优化、全栈可观测性与故障恢复。模块 05 调试与瓶颈定位一节的现实最佳实践。
- **PyTorch, _Distributed 文档（DDP / process groups / NCCL flight recorder）_** — rank/world、process group、`NCCL_DEBUG`、flight recorder 的官方说明。模块 05 调试 hang/deadlock 的第一手工具文档。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无多 GPU / 不装 torch.distributed**：全课用 numpy 在 CPU 上、**单进程内**把多个 rank 模拟成一组数组——all-reduce = 对 rank 列表求和、ring 分步 = 沿环传分片、ZeRO 分片显存 = 每 rank 只算 1/W、pipeline bubble = 甘特图里的空格、容错恢复 = 保存/还原 RNG 与步数。每个机制都与**单卡参考**对拍（DP 平均梯度 == 单卡大 batch 梯度、TP 切分 == 单卡线性层、reduce-scatter+all-gather == all-reduce、续训轨迹 == 未中断轨迹），保证你写的并行逻辑**正确**。
- **可迁移性**：你在 numpy 里验证过的通信模式、分片账、并行切分、调度与恢复逻辑，可几乎一对一映射到 `torch.distributed` 的 `all_reduce` / FSDP 的 `wrap` / Megatron 的 `ColumnParallelLinear` / `torch.distributed.checkpoint`。本课刻意让伪代码贴近真实 API。
- **课程衔接**：上游接 **C08（训练系统：显存/FLOPs/roofline 的成本模型与账本）**——C08 教你算账，本课教你把账变成可运行、可调试、可恢复的工程；并接 C36（GPU 内核，单卡算子怎么快）。下游接 C21（大规模预训练）、C24（推理服务，并行思路在推理侧的镜像）、C27（模型压缩，通信量化）。
