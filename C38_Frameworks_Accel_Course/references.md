# 参考清单 · References（深度学习框架与加速计算工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零复刻的每个机制（autograd、图捕获+融合、函数变换、混合精度、profiler），都能在下列文献里找到真实框架中的对应实现与权衡。

## 自动微分 · Automatic Differentiation
- ★ **Griewank & Walther 2008, _Evaluating Derivatives: Principles and Techniques of Algorithmic Differentiation_** — 自动微分的权威专著。把前向/反向模式、计算图、伴随、checkpointing 的数学讲到底。本课模块 01 的反向模式与模块 04 的重算-显存权衡都源出于此，是「为什么 AD 既精确又高效」的根。
- ★ **Baydin, Pearlmutter, Radul & Siskind 2018, _Automatic Differentiation in Machine Learning: a Survey_** — 机器学习视角下 AD 的最佳综述。澄清 autodiff ≠ 符号微分 ≠ 数值差分这一最常见误解，把前向/反向模式、各框架实现讲得通俗清晰。入门 autograd 必读。
- ★ **Karpathy, _micrograd_（GitHub + "The spelled-out intro to neural networks and backpropagation"）** — 一个 ~100 行的标量 reverse-mode autograd 引擎 + 配套讲解视频。本课模块 01 的 `Value` 引擎与之同构。看它能确信「autograd 没有魔法，就是链式法则 + 一张图」。
- **Paszke et al. 2017, _Automatic differentiation in PyTorch_（Autograd 论文/技术报告）** — PyTorch 反向模式 AD 的设计：动态构图、`grad_fn`、就地操作的处理。理解真实框架如何把模块 01 的玩具引擎做成工业级。
- **Bradbury et al., _Autodidax: JAX core from scratch_（JAX 文档）** — 从零搭一个 JAX 内核（trace、jaxpr、grad、vmap、jit）的官方教程。把本课模块 01/03 的「numpy 版变换」与真实 JAX 内部精确对上，强烈推荐对照阅读。

## 框架设计 · Framework Design
- ★ **Paszke et al. 2019, _PyTorch: An Imperative Style, High-Performance Deep Learning Library_（NeurIPS）** — PyTorch 的奠基论文。阐述「命令式/eager 优先」的设计哲学，以及如何在保持 Python 灵活性的同时拿到高性能。理解 eager vs graph 取舍的第一手材料，贯穿模块 00/02。
- ★ **Bradbury, Frostig, Hawkins, Johnson, Leary, Maclaurin, Wanderman-Milne, Zhang et al., _JAX: composable transformations of Python+NumPy programs_（GitHub/文档）** — JAX 的官方出处。讲清「纯函数 + 可组合变换（grad/vmap/jit/pmap）」这一核心范式。模块 03 全程在复刻它的心智模型，必读。
- **Abadi et al. 2016, _TensorFlow: A System for Large-Scale Machine Learning_（OSDI）** — 静态图框架的代表作。读它理解「图模式」的来历与早期取舍，反衬 PyTorch eager 与后来 torch.compile 的演进动机。
- **Frostig, Johnson & Leary 2018, _Compiling machine learning programs via high-level tracing_（MLSys/SysML）** — JAX/XLA「以高层 tracing 编译 ML 程序」的方法论原文。模块 02/03 的 tracing 思想出处。

## 图捕获与编译 · Graph Capture & Compilation
- ★ **Ansel et al. 2024, _PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation_（ASPLOS）** — torch.compile 的权威论文。讲 TorchDynamo 如何在 CPython 字节码层捕获图、graph break 如何回退、TorchInductor 如何生成 Triton/C++。模块 02 的现实对应，必读。
- ★ **Tillet, Kung & Cox 2019, _Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations_（MAPL）** — Triton 原始论文。提出「按块编程、编译器管线程映射」的抽象。TorchInductor 在 GPU 上生成的就是 Triton；理解模块 02「编译器自动融合」落到内核长什么样。
- **TorchInductor / torch.compile 官方文档与设计说明（PyTorch dev-discuss、`torch._dynamo`/`torch._inductor`）** — 工程细节：guard、动态形状、融合规则、后端选择。把模块 02 的玩具 tracer/融合接到真实编译栈。
- **`torch.fx`: Reid et al. 2021, _torch.fx: Practical Program Capture and Transformation for Deep Learning in Python_（MLSys）** — PyTorch Python 级图捕获与变换工具的论文。模块 02 「捕获成图再做图变换」的直接对应，适合动手做图 pass。
- **XLA 文档（_XLA: Optimizing Compiler for Machine Learning_, openxla.org）** — XLA 如何把 HLO 融合、做布局与内存规划、生成多后端代码。模块 03 JAX 的编译后端，理解「jit 之后 XLA 做了什么」。

## 数值精度与显存 · Precision & Memory
- ★ **Micikevicius et al. 2018, _Mixed Precision Training_（ICLR）** — 混合精度训练的奠基论文。提出 fp16 计算 + fp32 主权重 + loss scaling 的配方，分析下溢为何发生、loss scaling 为何有效。模块 04 全程在复现它，必读。
- ★ **Chen, Xu, Zhang & Guestrin 2016, _Training Deep Nets with Sublinear Memory Cost_（gradient checkpointing 原始论文）** — 用激活重算把训练显存从 O(L) 降到 O(√L) 的开创性工作。模块 04 「checkpoint 的时间-显存权衡」的数学出处，必读。
- ★ **He (Horace He) 2022, _Making Deep Learning Go Brrrr From First Principles_（博客）** — 把性能瓶颈清晰分成算力受限 / 访存受限 / 开销受限三类并给出判断与对策。是建立性能直觉、贯穿模块 04/05 的世界观文章，强烈建议先读。
- **Kalamkar et al. 2019, _A Study of BFLOAT16 for Deep Learning Training_** — 系统研究 bf16：为什么它的大动态范围使训练通常无需 loss scaling。模块 04 比较 fp16/bf16 的依据。
- **NVIDIA, _Train With Mixed Precision_（深度学习性能文档）+ `torch.cuda.amp` / `torch.amp` 文档** — autocast 与 GradScaler 的算子精度规则、动态 loss scaling 实现。把模块 04 的数值模拟接到真实 API。
- **Rajbhandari et al. 2020, _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_（SC）** — 把优化器状态/梯度/参数分片到多卡以省显存。模块 04 显存账（参数+梯度+优化器状态）的分布式延伸。

## 性能剖析与调试 · Profiling & Debugging
- ★ **Williams, Waterman & Patterson 2009, _Roofline: An Insightful Visual Performance Model for Multicore Architectures_（CACM）** — roofline 模型原始论文。用算术强度一眼判断内核受带宽还是算力限制。模块 05 给 profiling 结论定性的工具。
- **PyTorch 官方, _PyTorch Profiler_ 文档与 _Profiler Recipes_** — `torch.profiler` 的算子级耗时/显存、与 TensorBoard/Chrome trace 的集成、CUDA 同步注意事项。模块 05 玩具 profiler 的现实对应。
- **NVIDIA Nsight Systems / Nsight Compute 文档** — 系统级时间线与内核级指标（占用率、带宽利用率、缓存命中）。把模块 05 的纸面分析与真实测量对上。
- **PyTorch 官方, _Reproducibility_ 与 `torch.use_deterministic_algorithms` 文档** — 确定性训练怎么做、代价是什么（禁用非确定性内核、固定规约顺序）。模块 05 确定性一节的依据。
- **PyTorch 官方, `torch.autograd.set_detect_anomaly`（Anomaly Detection）文档** — 自动定位首次产生 NaN/Inf 的算子。模块 05 NaN 溯源的真实工具。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课的立场**：整套课程（C00–C37）几乎每个机制你都已「纯 numpy 从零」写过，唯独缺「真实框架是怎么工程化地把它们跑快/跑稳/跑省显存的」——本课补这个洞。核心机制仍用 **纯 numpy 从零复刻**（剥掉工程外壳、只留算法骨架，是最佳教学），真实 **PyTorch/JAX/Triton** 代码作 **对照**。notebook 在纯 numpy/CPU 下可跑、`assert` 全过，**绝不因缺 torch/jax 阻断**；若环境恰好装了 torch，部分对照可选实跑。
- **可迁移性**：你在 numpy 里验证过的 autograd VJP 规则、图融合/折叠 pass、grad/vmap 变换、loss-scaling 选择、profiler 归因，都能几乎一对一对应到 `torch.autograd.Function`、torch.fx/Inductor 的图 pass、`jax.grad`/`jax.vmap`、`GradScaler`、`torch.profiler`。
- **课程衔接**：上游接 C07（ML 基础 / 反向传播）、C36（GPU 内核 / roofline / Triton，本课的算子融合与 profiling 与之呼应）；下游接 C08（训练系统 / 并行 / ZeRO）、C24（推理服务）、C27（模型压缩 / 量化，与混合精度同源）。本课是「从手写 numpy 到驾驭真实框架」的桥。
