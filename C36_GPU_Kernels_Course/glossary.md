# 术语词典 · Glossary（GPU 内核与性能工程）

> 按主题分组，每条 2–3 句释义。读 CUDA 文档 / FlashAttention 论文 / Triton 教程遇到生词回这里查；英文术语保留原文（社区与硬件文档的通用语言）。本课用 numpy 在 CPU 上模拟这些概念，但术语与真实 GPU 编程一一对应。

## 硬件与执行层级 · Hardware & Execution Hierarchy

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| GPU (Graphics Processing Unit) | 图形/通用并行处理器 | 由几十到上百个流式多处理器（SM）组成的吞吐导向处理器。它牺牲单线程延迟，换取海量线程的并行吞吐，靠同时在飞的成千上万个线程把内存延迟藏起来。 |
| SM (Streaming Multiprocessor) | 流式多处理器 | GPU 的基本计算单元，内含若干 CUDA core、warp 调度器、寄存器堆与一块 shared memory / L1。一个 block 被整体派发到一个 SM 上执行，直到结束都不迁移。 |
| CUDA core / lane | CUDA 核心 / 通道 | SM 内执行一条线程算术指令的最小硬件单元。一个 warp 的 32 条 lane 在同一时钟被同一条指令驱动（SIMT）。 |
| Tensor Core | 张量核心 | 专做小矩阵乘累加（如 16×16×16 的 D=A·B+C）的硬件单元，是现代 GPU 上 FP16/BF16/FP8 GEMM 与注意力高吞吐的来源；cuBLAS/CUTLASS/FlashAttention 都围绕它编排数据。 |
| thread | 线程 | GPU 上最小的执行实体，通常处理一个输出元素或一个数据下标。它有自己的寄存器和程序计数器（逻辑上），但调度以 warp 为单位。 |
| warp | warp（线程束） | 32 个被绑定在一起、同步执行同一条指令的线程，是 GPU 真正的调度与执行粒度。理解 warp 是理解合并访问、分支发散、shuffle 规约的前提。 |
| block / CTA (Cooperative Thread Array) | 线程块 | 一组线程（如 256 个 = 8 个 warp），共享同一块 shared memory，可用 `__syncthreads()` 互相同步。block 是程序员组织协作的单位，整体驻留在一个 SM 上。 |
| grid | 网格 | 一次内核启动的所有 block 的集合。grid 与 block 都可以是 1/2/3 维，用于把问题域（向量、矩阵、张量）映射到线程。 |
| kernel | 内核 | 在 GPU 上由海量线程并行执行的同一个函数。写 kernel = 描述「单个线程做什么」+「如何把线程映射到数据」，CUDA 用 `__global__`、Triton 用 `@triton.jit`。 |
| SIMT (Single Instruction, Multiple Threads) | 单指令多线程 | GPU 的执行范式：一个 warp 的 32 线程共享一个指令流，但各自持有不同数据与寄存器。它像 SIMD，但允许各线程独立分支（代价是分支发散）。 |
| occupancy | 占用率 | 一个 SM 上实际驻留的活跃 warp 数 ÷ 硬件上限。占用率不是越高越好，但太低会让调度器没有足够 warp 来隐藏内存延迟。受寄存器用量、shared memory 用量、block 尺寸三者制约。 |
| latency hiding | 延迟隐藏 | GPU 性能的核心机制：当一个 warp 因等待内存而停顿时，调度器立刻切到另一个就绪 warp 执行，从而用并行掩盖单次访存数百周期的延迟。 |
| launch configuration | 启动配置 | 启动内核时指定的 grid 维度与 block 维度（CUDA 的 `<<<grid, block>>>`）。它决定线程总数与如何分块，是性能调优的第一个旋钮。 |
| global thread index | 全局线程下标 | 线程在整个 grid 中的唯一编号，经典公式 `idx = block_id * block_size + thread_id`。它把抽象的线程映射到具体的数据元素。 |
| bounds check / masking | 边界保护 / 掩码 | 当数据量不是 block 尺寸整数倍时，多出的线程必须用 `if idx < n` 跳过，否则越界访问。Triton 用 `mask=` 参数在 load/store 上做同样的事。 |

## 分支与同步 · Divergence & Synchronization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| warp divergence | 分支发散 | 同一 warp 内不同线程走了 `if/else` 的不同分支时，硬件只能串行执行各分支、用掩码关闭不参与的 lane，吞吐下降。让 32 条 lane 尽量走同一条路径是 SIMT 优化的要点。 |
| predication | 谓词执行 | 编译器把短小的分支转成「带掩码执行两边、再选择结果」，避免真正的控制流跳转。是缓解 warp divergence 的常用手段。 |
| `__syncthreads()` / barrier | 块内同步屏障 | 让一个 block 内所有线程在此处会合，常用于「写完 shared memory 再开始读」。漏写会导致读到尚未写入的数据（竞态）；放在分支里可能死锁。 |
| warp shuffle (`__shfl_*`) | warp 内洗牌 | 让同一 warp 的线程不经 shared memory 直接交换寄存器值的指令，是 warp 级规约（求和/求最大）的高效原语，比 shared memory 规约少一次往返。 |
| atomic operation | 原子操作 | 保证「读-改-写」不被其他线程打断的操作（如 `atomicAdd`）。用于多个 block 向同一地址累加结果，但争用激烈时会成为瓶颈。 |
| race condition | 竞态 | 多个线程对同一内存无序读写、结果依赖执行时序的 bug。GPU 上极易因漏写 barrier 或误用 shared memory 而出现。 |

## 内存层级 · Memory Hierarchy

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| register | 寄存器 | 速度最快、线程私有的存储，位于 SM 内。每线程寄存器用量越多，能同时驻留的 warp 越少（影响占用率）；寄存器不够会 spill 到本地内存（慢）。 |
| shared memory / SMEM | 共享内存 | block 内所有线程共享的片上高速存储（与 L1 共用容量），延迟比 global 低一两个数量级。是 tiling 复用数据、warp 间协作的关键，由程序员显式管理。 |
| L1 / L2 cache | 一级 / 二级缓存 | 硬件自动管理的缓存。L1 在 SM 内（常与 shared memory 同一块 SRAM 划分），L2 被所有 SM 共享，缓冲对 global memory 的访问。 |
| global memory / HBM | 全局内存 / 高带宽显存 | GPU 的主显存（如 H100 的 80GB HBM3），容量大、带宽高（TB/s 级）但延迟高（数百周期）、相对算力仍是瓶颈。所有 block 可见，内核间持久。 |
| HBM (High Bandwidth Memory) | 高带宽内存 | 堆叠式 DRAM，提供 GPU 的主显存带宽。FlashAttention 的核心洞察正是：注意力受 HBM 读写量支配，减少 HBM 往返比减少 FLOPs 更重要。 |
| memory transaction | 内存事务 | 访存硬件一次搬运的最小连续块（一条 cache line，典型 32/128 字节）。一个 warp 的 32 次访问若落在同一/相邻 cache line，可合并成最少的事务。 |
| memory hierarchy | 内存层级 | register > shared/L1 > L2 > global(HBM) > host。越靠上越快越小。性能工程的主线就是：把数据搬到尽量靠上的层级并尽量复用，减少对下层（尤其 HBM）的访问。 |
| bandwidth | 带宽 | 单位时间能搬运的字节数（GB/s 或 TB/s）。访存受限内核的性能上限 = 带宽 ÷ 每字节产生的有用工作量。 |
| memory-bound | 访存受限 | 内核的瓶颈在「喂数据」而非「算」：算术强度低于硬件的 ridge point。逐元素算子、softmax、LayerNorm、注意力大多如此。 |
| compute-bound | 算力受限 | 瓶颈在算术单元吞吐而非访存：算术强度高于 ridge point。大尺寸 GEMM、卷积在分块良好时属于此类。 |

## 合并访问与 Tiling · Coalescing & Tiling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| coalesced access | 合并访问 | 一个 warp 的 32 个线程访问连续（或落在同一 cache line）的地址，硬件合并成最少的内存事务，带宽利用率接近 100%。是 global memory 访问的第一优化目标。 |
| strided / uncoalesced access | 跨步 / 非合并访问 | 相邻线程访问相隔很远的地址（如按列遍历行优先矩阵），每个线程触发独立事务，有效带宽可能只有合并访问的 1/8 甚至更低。 |
| row-major / column-major | 行优先 / 列优先 | 多维数组在线性内存中的展开顺序。行优先（C/numpy 默认）下同一行相邻；线程映射要顺着存储顺序走才能合并访问。 |
| bank conflict | bank 冲突 | shared memory 被分成 32 个 bank；若一个 warp 的多个线程访问同一 bank 的不同地址，访问被串行化。常用 padding（如把列数 +1）错开地址来消除。 |
| tiling / blocking | 分块 | 把大计算切成小块（tile），把每块数据先搬进 shared memory / 寄存器再反复复用，从而把对 global memory 的访问次数除以 tile 边长。是 GEMM、卷积、注意力高性能的通用套路。 |
| tile | 块 | tiling 中搬进片上存储的一小块数据（如 GEMM 的 32×32 子矩阵）。tile 越大复用越多、算术强度越高，但占用越多 shared memory / 寄存器。 |
| double buffering / software pipelining | 双缓冲 / 软件流水 | 在计算当前 tile 的同时异步预取下一 tile，用计算掩盖搬运延迟。现代 GEMM/注意力内核的标准技巧（CUTLASS、FlashAttention-3 的异步拷贝）。 |
| operator fusion | 算子融合 | 把多个逐元素/规约算子合并进一个内核，中间结果留在寄存器/shared 而不落 global，省掉中间张量的 HBM 读写。融合 softmax、FlashAttention 都是其极致体现。 |
| materialize | 落盘 / 物化 | 把一个中间张量完整写回 global memory。FlashAttention 的关键是「永不 materialize n×n 的分数矩阵」，从而把显存与带宽从 O(n²) 降到 O(n)。 |

## 矩阵乘与性能模型 · GEMM & Performance Model

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| GEMM (General Matrix Multiply) | 通用矩阵乘 | C = αAB + βC 形式的稠密矩阵乘，是深度学习算力的主体（线性层、注意力的 QKᵀ 与 AV）。高性能 GEMM 的核心是多级 tiling 与数据复用。 |
| arithmetic intensity (AI) | 算术强度 | 每从内存搬运一个字节所执行的浮点运算数（FLOPs/byte）。它决定一个内核是访存受限还是算力受限，是 roofline 模型的横轴。 |
| FLOPs / FLOP/s | 浮点运算次数 / 每秒浮点运算 | FLOPs 指完成任务所需的浮点运算总数；FLOP/s（带斜杠）指硬件每秒能做多少。两者之比给出理论最短计算时间。 |
| roofline model | roofline 模型 | 把性能上限画成两段：低算术强度时受带宽限制（斜线 = AI × 带宽），高算术强度时受峰值算力限制（水平线）。直观判断内核离硬件上限多远、该优化访存还是算力。 |
| ridge point | 脊点 | roofline 上斜线与水平线的交点，算术强度 = 峰值算力 ÷ 带宽。AI 在脊点左侧 → 访存受限；右侧 → 算力受限。把内核的 AI 推过脊点是分块的目标。 |
| FMA (Fused Multiply-Add) | 融合乘加 | a*b+c 一条指令完成、计 2 FLOPs，是 GEMM 内层循环的基本运算，也是统计 FLOPs 的基准。 |
| reuse / data reuse | 数据复用 | 一份从 global 读入的数据被用于多少次运算。tiling 通过把数据留在片上提高复用，等价于提高算术强度。 |

## 规约与 Softmax · Reduction & Softmax

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| reduction | 规约 | 把一组数聚合成一个（求和、求最大、求范数等）。并行规约的难点是把本质串行的累加重排成并行结构。 |
| tree reduction | 树形规约 | 两两合并、每步把待合并元素减半，用 O(log n) 步、O(n) 工作完成规约。GPU 上对应「每轮一半线程把另一半加过来 + 一次同步」。 |
| parallel scan / prefix sum | 并行扫描 / 前缀和 | 计算所有前缀聚合（如累加和）。用结合律重排成 O(log n) 深度的并行运算，是规约的「保留中间结果」版本，也是部分 SSM/排序算法的核心。 |
| associativity | 结合律 | (a∘b)∘c = a∘(b∘c)。规约与扫描能并行化的数学前提；浮点加法并不严格结合，因此并行规约与串行规约的结果可能有微小差异。 |
| numerically stable softmax | 数值稳定 softmax | 先减去每行最大值再取 exp，避免大 logit 导致 exp 溢出为 inf。数学上与朴素 softmax 等价（分子分母同乘常数），是所有正确实现的标配。 |
| online softmax | 在线 / 流式 softmax | 一遍流式扫描数据、动态维护「当前最大值」与「当前指数和」，每见到更大的值就用校正因子 `exp(old_max − new_max)` 回缩已累加的和。让 softmax 无需先看完整行，是 FlashAttention 分块的关键。 |
| running max / running sum | 运行最大值 / 运行和 | online softmax 流式维护的两个标量（注意力里还有运行输出向量）。它们让一行的归一化可以分块增量完成。 |
| rescale / correction factor | 校正因子 | online softmax 中遇到新最大值时，对已累加的和与输出乘上的 `exp(old_max − new_max) ∈ (0,1]`，把旧的指数基准对齐到新基准。 |
| LogSumExp (LSE) | 对数和指数 | log Σ exp(xᵢ)，softmax 归一化项的对数。数值稳定地计算它（减最大值）等价于在线 softmax 维护的量，常被反向传播复用。 |

## 注意力与 FlashAttention · Attention & FlashAttention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| attention | 注意力 | softmax(QKᵀ/√d)·V。朴素实现要先算出 n×n 的分数矩阵 S 再 softmax，显存与 HBM 读写都是 O(n²)，长序列下爆炸。 |
| scaled dot-product | 缩放点积 | 注意力分数 QKᵀ 除以 √d，防止维度变大时点积方差过大、把 softmax 推向饱和区。 |
| FlashAttention | —— | Dao 等 2022 提出的精确注意力内核：对 K/V 分块、用 online softmax 增量累加输出，永不 materialize 完整 S。显存 O(n²)→O(n)，HBM 访问大幅下降，是 IO 感知（IO-aware）算法设计的范例。 |
| IO-awareness | IO 感知 | 以「HBM 读写字节数」而非「FLOPs」为优化目标来设计算法。FlashAttention 的 FLOPs 并不比朴素少（甚至因重算略多），却快得多，正因为它把 HBM IO 从 O(n²) 降到 O(n²d²/M)。 |
| KV block / tiling over K,V | KV 分块 | FlashAttention 把 K、V 沿序列维切成块，外层遍历 Q 块、内层流式遍历 K/V 块，对每个 Q 块在线累加注意力输出。 |
| recomputation | 重算 | 反向传播时不保存巨大的中间矩阵（如注意力概率），而是用保存下来的 LSE 等少量统计量重新算出来。用算力换显存，是 FlashAttention 反向的关键。 |
| causal mask | 因果掩码 | 自回归注意力中让每个位置只看自己及之前的位置（屏蔽上三角）。在分块内核里表现为：对角块需逐元素掩码，纯下三角块全算，纯上三角块整块跳过。 |
| softmax denominator / l, m | softmax 分母与统计量 | FlashAttention 论文里每个 query 行维护的运行和 ℓ 与运行最大值 m，配合输出累加器 O，构成分块在线 softmax 的全部状态。 |

## 工程工具与生态 · Tooling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| CUDA | —— | NVIDIA 的 GPU 并行计算平台与 C++ 扩展。直接写 `__global__` 内核、管理 shared memory 与同步，控制力最强但开发成本高。 |
| Triton | —— | 以 Python 写 GPU 内核的 DSL/编译器（Tillet 2019）：程序员按「块」编程（`tl.load`/`tl.store` 带 mask、`tl.dot`），编译器自动处理线程映射、合并访问与部分流水。本课的伪代码即对标它。 |
| Triton program / `program_id` | Triton 程序实例 / 程序号 | Triton 的并行单位类似一个 block；`tl.program_id(axis)` 取本实例在网格中的编号，用于算出本块负责的数据范围（对应 CUDA 的 blockIdx）。 |
| `tl.dot` | Triton 块内点积 | Triton 中对两个块做矩阵乘的原语，会被映射到 Tensor Core。是 Triton 版 GEMM/注意力内层的核心。 |
| autotune | 自动调优 | 让框架在多组配置（block 尺寸、num_warps、流水级数等）中实测搜出最快的一组。Triton 用 `@triton.autotune` 实现，因为最优分块依赖具体形状与硬件。 |
| cuBLAS / CUTLASS | —— | NVIDIA 的高性能线性代数库（cuBLAS）与可组合的开源 GEMM 模板库（CUTLASS）。它们把本课的多级 tiling、双缓冲、Tensor Core 编排做到了极致，是手写内核的对照基准。 |
| nsight / profiler | 性能分析器 | NVIDIA Nsight Compute/Systems 等工具，测量内核的占用率、带宽利用率、各级缓存命中、是否访存受限等，是性能调优的「显微镜」。 |
| ncu / achieved occupancy | 实测占用率 | profiler 报告的运行时实际活跃 warp 比例，常低于理论占用率（受 tail effect、同步等待影响），是判断 launch 配置是否合理的依据。 |
