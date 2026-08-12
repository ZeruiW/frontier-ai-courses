# 术语词典 · Glossary（分布式训练工程）

> 按主题分组，每条 2–3 句释义。读 Megatron-LM / DeepSpeed ZeRO / PyTorch FSDP / NCCL 文档遇到生词回这里查；英文术语保留原文（社区与框架文档的通用语言）。本课用 numpy 在单进程内模拟这些概念，但术语与真实 torch.distributed 一一对应。

## 并行范式 · Parallelism Paradigms

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data parallelism (DP) | 数据并行 | 每个 rank 持有一份完整模型副本，各自吃一份不同的数据子批，反向后用 all-reduce 把梯度平均同步。它扩的是吞吐（throughput），不缩小单卡显存，是最简单也最常用的并行。 |
| model parallelism | 模型并行 | 把单个模型本身切到多卡的统称，分两条路：张量并行（切单层算子）与流水并行（切层序列）。当一层甚至一个模型放不进单卡显存时必须用它。 |
| tensor parallelism (TP) | 张量并行 | 把单个算子（如线性层的权重矩阵）沿某一维切到多卡并行计算，再用一次 all-reduce 或 all-gather 合并。Megatron-LM 是其代表，通信频繁、对带宽敏感，通常限制在单节点内（NVLink）。 |
| pipeline parallelism (PP) | 流水线并行 | 把模型的层序列切成若干 stage 放到不同 rank，激活在 stage 之间点对点传递，像流水线一样让不同 micro-batch 在不同 stage 同时计算。代价是流水线填充/排空的 bubble。 |
| 3D parallelism | 三维并行 | DP × TP × PP 三种并行的组合，把 world 组织成三维网格。典型布局：TP 放节点内（带宽高）、PP 跨节点、DP 在最外层；训练超大模型的标准配方。 |
| expert parallelism (EP) | 专家并行 | MoE（混合专家）特有的并行：把不同 expert 放到不同 rank，token 经 all-to-all 路由到其所属 expert 所在的 rank。是 3D 并行之外的第四个维度。 |
| sequence / context parallelism | 序列 / 上下文并行 | 沿序列长度维把激活切到多卡，缓解长上下文下激活显存爆炸。与 TP 正交，是长序列训练的关键。 |
| ZeRO (Zero Redundancy Optimizer) | 零冗余优化器 | DeepSpeed 提出的一族技术：把数据并行中本来每卡冗余存一份的优化器状态、梯度、参数逐级分片到各 rank，显存近线性下降，却保持数据并行的编程模型。 |
| FSDP (Fully Sharded Data Parallel) | 全分片数据并行 | PyTorch 原生的 ZeRO-3 等价实现：参数/梯度/优化器状态全部分片，前向/反向时按需 all-gather 出当前层的完整参数、用完即弃。 |
| replica / shard | 副本 / 分片 | 副本指一份完整拷贝（DP 里每卡一份模型）；分片指被切开后每 rank 只持有的一部分（ZeRO/FSDP 里每卡 1/W 的参数）。分片是用通信换显存。 |

## 集合通信 · Collective Communication

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| collective communication | 集合通信 | 一组进程（rank）共同参与的通信原语，相对于点对点（send/recv）。all-reduce、all-gather、reduce-scatter、broadcast、all-to-all 是分布式训练的基本积木，由 NCCL/Gloo 实现。 |
| all-reduce | 全规约 | 把所有 rank 各自的张量按某算子（通常求和）聚合，并让每个 rank 都拿到同一个聚合结果。数据并行同步梯度的核心；可分解为 reduce-scatter + all-gather。 |
| all-gather | 全收集 | 每个 rank 贡献自己的一片，结束后每个 rank 都拥有所有片拼成的完整张量。FSDP 前向时用它把分片参数拼回完整权重。 |
| reduce-scatter | 规约散射 | all-gather 的对偶：把所有 rank 的张量按算子聚合后，把结果切片散给各 rank（每 rank 只拿自己负责的那一片聚合值）。ZeRO 同步梯度分片用它。 |
| broadcast | 广播 | 把某个 root rank 上的张量复制到所有其他 rank。常用于初始化时把 rank0 的参数同步给全体，保证起点一致。 |
| reduce | 规约 | 把所有 rank 的张量聚合到某个 root rank（只有 root 拿到结果）。是 all-reduce 的「只汇到一处」版本。 |
| scatter / gather | 散射 / 收集 | scatter 把 root 上的一个大张量切片分发给各 rank；gather 把各 rank 的片汇集到 root。是 all-gather/reduce-scatter 的单点版本。 |
| all-to-all | 全交换 | 每个 rank 把自己的数据按目标 rank 切块，彼此交换，结束后每 rank 持有来自所有 rank 的对应块。MoE 路由、序列并行重排布的核心原语。 |
| barrier | 同步屏障 | 让所有 rank 在此处会合、谁先到谁等，常用于对齐 checkpoint、计时、调试。同步训练每步隐含一次屏障——最慢的 rank 决定步时。 |
| ring all-reduce | 环形全规约 | 把 rank 排成逻辑环，分 reduce-scatter 与 all-gather 两阶段、各 W−1 步传递分片。每 rank 收发的数据量与 W 无关（约 2×张量大小），带宽最优，是 NCCL 的经典算法。 |
| NCCL | NVIDIA 集合通信库 | NVIDIA 的 GPU 集合通信库，在 NVLink/InfiniBand 上高效实现 all-reduce 等原语，并自动选择 ring/tree 等拓扑算法。`torch.distributed` 的默认 GPU 后端。 |
| bandwidth-optimal / latency-optimal | 带宽最优 / 延迟最优 | 同一集合通信有多种算法：ring 收发字节最少（带宽最优，适合大张量）、tree/递归倍增步数最少（延迟最优，适合小张量）。框架按消息大小自动切换。 |

## 数据并行机制 · Data-Parallel Mechanics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| DDP (DistributedDataParallel) | 分布式数据并行 | PyTorch 的数据并行实现：反向时按 bucket 把梯度做 all-reduce，并与反向计算重叠（overlap）以隐藏通信。等价于在 W 倍大的全局 batch 上训练单卡。 |
| gradient bucketing | 梯度分桶 | 把许多小梯度张量攒成几个大 bucket 再 all-reduce，减少启动次数、提高带宽利用，并能让先算完的 bucket 提前开始通信。 |
| communication–computation overlap | 通信-计算重叠 | 在反向还在算前面层梯度时，就异步发送后面层已算好的梯度；把通信时间藏到计算之下，是 DDP/FSDP 高效扩展的关键。 |
| effective / global batch size | 有效 / 全局批大小 | 一步里所有 rank 合起来处理的样本数 = 每卡 local batch × DP 度数 ×（梯度累积步数）。它决定优化的统计行为，调大 DP 通常要相应调 lr。 |
| gradient accumulation | 梯度累积 | 在一次参数更新前，串行累加多个小 micro-batch 的梯度，等效放大 batch 而不增显存。常与并行组合以凑到目标全局 batch。 |
| optimizer state | 优化器状态 | 优化器为更新参数而维护的额外张量。Adam 每个参数存一阶动量 m 与二阶动量 v（各 1 份），混合精度下还有 fp32 master 参数，是显存大头。 |
| mixed precision | 混合精度 | 用 fp16/bf16 做前向反向（省显存、提吞吐），同时保留 fp32 的 master 参数与优化器状态以保数值稳定。每参数显存约 16 字节（2 fp16 参数 + 2 fp16 梯度 + 4 fp32 master + 8 Adam 动量）。 |
| parameter / gradient / optimizer sharding | 参数 / 梯度 / 优化器分片 | ZeRO 的三个阶段分别分片的对象：ZeRO-1 分片优化器状态、ZeRO-2 再分片梯度、ZeRO-3 连参数也分片。每进一阶显存更省、通信更多。 |

## 模型并行机制 · Model-Parallel Mechanics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| column / row parallel linear | 列 / 行并行线性层 | Megatron 切线性层的两种方式：列并行把权重按输出维（列）切，各 rank 算输出的一部分、无需通信；行并行把权重按输入维（行）切，各 rank 算部分和、需 all-reduce 求和。 |
| Megatron MLP block | Megatron MLP 块 | 把 MLP 设计成「列并行 → 行并行」，使前向只需 1 次 all-reduce、反向 1 次，通信次数最省。注意力则把 QKV 按 head 切到各 rank。 |
| micro-batch | 微批 | 流水线并行里把一个 batch 再切成的小块。micro-batch 越多，流水线填得越满、bubble 越小，但激活显存与调度开销上升。 |
| pipeline bubble | 流水线气泡 | 流水线填充（warm-up）和排空（cool-down）阶段部分 stage 闲置造成的浪费。朴素调度的 bubble 比例 = (P−1)/(m+P−1)，P 为 stage 数、m 为 micro-batch 数。 |
| 1F1B schedule | 一前一后调度 | one-forward-one-backward：稳态下每个 stage 交错执行一次前向和一次反向，使在飞的激活数从 m 降到约 P，大幅降低激活显存峰值。 |
| interleaved 1F1B | 交错式 1F1B | 让每个 rank 持有多段不连续的层（virtual stage），进一步缩小 bubble，代价是更多点对点通信。Megatron-LM 的默认高级调度。 |
| activation / activation memory | 激活 / 激活显存 | 前向算出、反向要用的中间张量。它常是显存第一大头，随 batch、序列长度、层数增长；流水线调度与 activation checkpointing 都是为压它。 |
| activation checkpointing / recomputation | 激活重算 | 前向时只保存少量激活，反向时重新前向算出其余，用算力换显存。与并行正交，是放下大模型的常用手段。 |
| point-to-point (send/recv) | 点对点通信 | 两个特定 rank 间的直接收发。流水线并行用它在相邻 stage 间传递激活（前向）与梯度（反向）。 |

## Checkpoint 与容错 · Checkpointing & Fault Tolerance

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| checkpoint | 检查点 | 把训练状态（参数 + 优化器状态 + RNG 状态 + 步数 + data loader 位置 + lr 调度器）落盘的快照。少存任何一项都无法精确续训。 |
| sharded checkpoint | 分片检查点 | 每个 rank 只写自己持有的那片状态，并行写、容量可扩展；相对于 rank0 gather 全部再写的单文件方案，避免 OOM 与串行瓶颈。 |
| asynchronous checkpoint | 异步检查点 | 先把状态快速拷到 CPU pinned 内存，再由后台线程慢慢落盘，训练几乎不停。有效开销≈拷贝时间而非写盘时间。 |
| atomic write | 原子写 | 先写临时文件、写完再 rename 到正式名，保证「要么是旧的完整检查点、要么是新的完整检查点」，杜绝半截文件被当成有效检查点。 |
| MTBF (Mean Time Between Failures) | 平均故障间隔 | 硬件平均多久坏一次。系统级 MTBF ≈ 单卡 MTBF ÷ 卡数：卡越多越频繁坏。几千卡时每隔几小时必有一次失败，逼出 checkpoint+恢复。 |
| failure recovery | 故障恢复 | 检测失败 → 重启进程/换节点 → 各 rank 载入自己分片 → 从保存的步数与 RNG 状态精确续训，使续训轨迹与未中断时一致。 |
| Young/Daly optimal interval | 最优检查点间隔 | 平衡「checkpoint 写盘开销」与「故障丢失的计算」的最优频率，近似为 √(2·δ·MTBF)，δ 为单次 checkpoint 成本。 |
| elastic training | 弹性训练 | 允许 world_size 在运行中变化：节点挂了用剩余节点继续、或重新 rendezvous 加入新节点，常需把 checkpoint re-shard 到新的 rank 数。 |
| rendezvous | 会合 | 弹性训练中各进程互相发现、协商出 rank/world_size 的过程（如 torchrun 的 c10d 后端）。节点变动时重新 rendezvous。 |
| determinism / RNG state | 确定性 / 随机数状态 | 为精确续训需保存并恢复每个 rank 的随机数发生器状态，使 dropout、数据打散等在续训后与未中断时逐位一致。 |

## 编排、调度与可观测性 · Orchestration & Observability

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| rank / world size | 进程号 / 总进程数 | rank 是每个进程在全局的唯一编号（0..world_size−1），world_size 是参与训练的进程总数（通常 = 总 GPU 数）。一切并行的坐标系。 |
| local rank | 本地进程号 | 进程在其所在节点内的编号，用于把进程绑定到该节点的第几块 GPU（`torch.cuda.set_device(local_rank)`）。 |
| process group | 通信组 | 参与某次集合通信的 rank 子集。按并行维度建多个子组（DP group / TP group / PP group），每个 collective 在对应组上执行。 |
| torchrun / SLURM | 启动器 / 作业调度 | torchrun 在每节点拉起多进程并设好 rank/world/MASTER_ADDR 等环境；SLURM 是 HPC 集群的作业调度器，负责分配节点与排队。 |
| MASTER_ADDR / MASTER_PORT | 主节点地址 / 端口 | rank0 的网络地址与端口，其他 rank 据此建立初始连接、协商 rendezvous。配错是新手最常见的「卡住」原因。 |
| straggler | 落后者 | 比其他 rank 慢的那个进程（硬件降频、网络抖动、数据不均所致）。同步训练是木桶效应，步时由最慢的 rank 决定，一个 straggler 拖垮全体。 |
| strong scaling | 强扩展 | 固定总问题规模、增加卡数，看加速比。受 Amdahl 定律与通信占比限制，卡越多边际效率越低。 |
| weak scaling | 弱扩展 | 每卡问题规模固定、同比增加卡数与总问题规模，看单步时间是否保持恒定。理想下时间不变，现实中被随 N 增长的通信侵蚀。 |
| Amdahl's law | 阿姆达尔定律 | 加速比 = 1 / ((1−p) + p/N)，p 为可并行比例。串行部分（含不可重叠的通信）决定加速比上限，是扩展效率的天花板。 |
| scaling efficiency | 扩展效率 | 实测加速比 ÷ 理想加速比（= 卡数）。低于 1 的差距来自通信、straggler、负载不均、尾部效应等。 |
| MFU (Model FLOPs Utilization) | 模型算力利用率 | 实测每秒有效模型 FLOPs ÷ 硬件峰值 FLOPs。衡量整套并行+实现离硬件上限有多远；大模型训练常报 30–50%。 |
| deadlock / hang | 死锁 / 卡住 | 分布式最常见的 bug：某些 rank 进了某个 collective、另一些没进（分支不对齐、形状/步数不一致），所有 rank 互等到 NCCL 超时。 |
| NCCL timeout / flight recorder | NCCL 超时 / 飞行记录器 | collective 久等不到对端会触发超时；flight recorder 记录每个 rank 最近的 collective，帮助定位是谁、在哪个 collective 上掉队。 |
| profiling / trace | 性能剖析 / 追踪 | 用 timeline/trace 区分一个慢步是 compute-bound、communication-bound 还是 straggler-bound，并定位到具体的 collective 或 stage。 |
