# 参考清单 · References（GPU 内核与性能工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 模拟的每个机制，都能在下列文献里找到真实硬件上的对应实现与权衡。

## 编程模型与硬件 · Programming Model & Hardware
- ★ **NVIDIA, _CUDA C++ Programming Guide_** — GPU 编程的权威手册。讲清 thread/warp/block/grid 四级层级、内存模型、`__syncthreads()` 与 warp 原语、SIMT 执行。本课模块 01/02 的所有术语都源出于此，遇到概念分歧以它为准。
- ★ **Hwu, Kirk & Hajj, _Programming Massively Parallel Processors_ (PMPP), 4th ed.** — 公认的 GPU 编程教材。从向量加法到 tiled GEMM、规约、卷积循序渐进，每章都有「为什么这样映射线程」的推导。本课的难度阶梯与章节顺序大体对标它，强烈建议配套精读第 3–6、8 章。
- **NVIDIA, _CUDA C++ Best Practices Guide_** — 性能优化清单：合并访问、shared memory、占用率、bank conflict 的具体规则与示例。当你写真实内核卡在带宽时，按它逐条排查。
- **NVIDIA GPU 架构白皮书（Volta/Ampere/Hopper, 如 _NVIDIA H100 Tensor Core GPU Architecture_）** — 每代 SM 的 warp 调度器数量、寄存器/shared 容量、Tensor Core 规格、HBM 带宽。算 roofline 与占用率上限时需要这些硬数字。
- **Volkov 2010, _Better Performance at Lower Occupancy_** — 反直觉但重要：高占用率不是性能的充要条件，靠每线程更多寄存器、指令级并行（ILP）也能隐藏延迟。读它矫正「占用率越高越好」的误解。

## 内存、合并访问与性能模型 · Memory, Coalescing & Roofline
- ★ **Williams, Waterman & Patterson 2009, _Roofline: An Insightful Visual Performance Model for Multicore Architectures_** — roofline 模型原始论文。把性能上限拆成带宽段与算力段，用算术强度一眼判断内核瓶颈。本课模块 03 用它解释「分块到底带来了什么」。
- ★ **Harris (NVIDIA), _How to Access Global Memory Efficiently in CUDA C/C++_（NVIDIA 技术博客）** — 合并访问最清晰的图文讲解：为什么相邻线程要读相邻地址，跨步访问的带宽代价。模块 02 的直觉来源。
- **NVIDIA, _Using Shared Memory in CUDA C/C++_（技术博客）** — shared memory 的用法、bank 结构与 bank conflict 的成因和 padding 解法，配合矩阵转置示例。模块 02 练习的现实对应。
- **Harris (NVIDIA), _Optimizing Parallel Reduction in CUDA_（经典演讲/讲义）** — 把规约内核从朴素一路优化到接近带宽上限的七个版本：消除分支发散、消除 bank conflict、warp 内展开、grid-stride。模块 04 的必读，展示同一算法不同写法的巨大差距。

## 矩阵乘 · GEMM
- ★ **NVIDIA CUTLASS（开源库与文档）** — 把高性能 GEMM 拆成 threadblock/warp/thread 多级 tile + 双缓冲 + Tensor Core 编排的可组合模板。读它的设计文档能看到本课模块 03 的「一层 tiling」在真实世界要叠到三四层。
- **Huang et al. / BLIS, _Anatomy of High-Performance Matrix Multiplication_(Goto & van de Geijn 2008)** — CPU 端 GEMM 的分层 blocking 经典分析，把「为什么要多级分块、每级对应哪级缓存」讲透，思想直接迁移到 GPU。
- **NVIDIA, _CUTLASS: Fast Linear Algebra in CUDA C++_（开发者博客）** — CUTLASS 设计动机的高层导读，适合在精读源码前建立框架。
- **CUDA 官方 `matrixMul` 样例** — 最小可读的 shared-memory tiled GEMM，和本课模块 03 的 numpy 模拟一一对应，建议对照阅读。

## 规约、Softmax 与在线归一化 · Reduction & Online Softmax
- ★ **Milakov & Gimelshein 2018, _Online normalizer calculation for softmax_** — online softmax 的原始论文。证明可以一遍流式地维护 max 与归一化和，把传统的三遍（求max/求和/归一）softmax 压成一遍。这是 FlashAttention 在线 softmax 的直接前身，模块 04/05 的数学核心。
- **Blelloch 1990, _Prefix Sums and Their Applications_** — 并行扫描（prefix sum）的奠基文献，给出 work-efficient 扫描算法。规约/扫描的结合律视角来源。
- **NVIDIA, _Faster Parallel Reductions on Kepler_（技术博客）** — 用 warp shuffle（`__shfl_down`）做规约，省掉 shared memory 往返。模块 04 「warp shuffle 规约」的现实对应。

## FlashAttention 与 IO 感知算法 · FlashAttention & IO-Awareness
- ★ **Dao, Fu, Ermon, Rudra & Ré 2022, _FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness_** — 本课的集大成目标。提出对 K/V 分块 + online softmax，永不 materialize n×n 分数矩阵，把注意力的 HBM 访问从 O(n²) 降到 O(n²d²/M)，显存 O(n²)→O(n)，且数学上是精确注意力。必读，模块 05 全程在复现它。
- ★ **Dao 2023, _FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning_** — FA-1 的工程化重写：减少非矩阵乘运算、调整循环顺序让 Q 在外层、改进 warp 间任务划分，逼近 GEMM 的硬件利用率。读它理解「同一算法，工程化能再快 2 倍」。
- **Shah et al. 2024, _FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision_** — 面向 Hopper：用异步拷贝（TMA）、warp 专门化、FP8 把注意力推到新的吞吐与精度前沿。展示双缓冲/软件流水/异步在前沿内核里的样子。
- **Rabe & Staats 2021, _Self-attention Does Not Need O(n²) Memory_** — 与 FlashAttention 并行的洞察：用在线累加把注意力显存降到 O(1)（不含输出）/O(log n)。理解「分块在线 softmax」的另一条独立推导。
- **Dao & Gu 2024 等关于 attention 变体与 IO 的后续** — 把 IO 感知思想推广到带掩码、变长、MQA/GQA、解码阶段（FlashDecoding）等场景，是把模块 05 落到生产推理的延伸。

## 工具与编译器 · Tooling & Compilers
- ★ **Tillet, Kung & Cox 2019, _Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations_** — Triton 原始论文。提出「按块（tile）编程」的抽象：程序员管分块与算法，编译器管线程映射、合并访问、寄存器分配。本课所有 Triton 伪代码的依据。
- ★ **Triton 官方教程（`triton-lang.org` 的 vector-add / fused-softmax / matmul / flash-attention）** — 把本课五个模块的 numpy 模拟一一对应到可跑的 `@triton.jit` 内核。学完本课后照着把验证过的逻辑写成真实内核，是最自然的下一步。
- ★ **Horace He 2022, _Making Deep Learning Go Brrrr From First Principles_（博客）** — 把性能瓶颈清晰分成三类：算力受限（compute）、访存受限（memory/bandwidth）、开销受限（overhead），并给出判断与对策。是建立性能直觉、贯穿全课的世界观文章，强烈建议先读。
- **OpenAI/PyTorch, _torch.compile / TorchInductor_ 文档** — 生产中自动做算子融合并生成 Triton 内核的编译器。理解本课的「手写融合」如何被自动化，以及何时仍需手写。
- **NVIDIA Nsight Compute / Nsight Systems 文档** — 测量占用率、带宽利用率、缓存命中、是否访存受限的 profiler。把本课的纸面 roofline 与真实测量对上，靠它。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU**：全课用 numpy 在 CPU 上**模拟** GPU 编程模型——线程网格用循环展开、shared tile 用小数组、warp shuffle 用切片、online softmax 用流式标量。每个内核都与朴素实现**对拍到 `atol=1e-10`**（分块 GEMM == `A@B`、FlashAttention == 朴素注意力），保证你写的分块/规约/在线 softmax 逻辑**正确**。
- **可迁移性**：你在 numpy 里验证过的分块结构、规约树、在线 softmax 递推，可几乎一对一改写成 `@triton.jit` 内核，再用 `triton.autotune` 搜 block 尺寸。本课刻意让伪代码贴近 Triton。
- **课程衔接**：上游接 C01（Transformer/注意力数学）；下游接 C08（训练系统 / roofline / 并行）、C24（推理服务 / FlashDecoding）、C25（长上下文，FlashAttention 让 32k+ 可行的直接受益者）。
