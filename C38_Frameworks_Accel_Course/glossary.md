# 术语词典 · Glossary（深度学习框架与加速计算工程）

> 按主题分组，每条 2–3 句释义。读 PyTorch/JAX 文档、torch.compile / XLA / Triton 源码与论文遇到生词回这里查；英文术语保留原文（框架与社区的通用语言）。本课用 numpy 从零复刻这些机制的内核，术语与真实框架一一对应。

## 自动微分 · Automatic Differentiation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| automatic differentiation (autodiff / AD) | 自动微分 | 对一段由初等运算组成的程序，自动、精确（到机器精度）地求其导数的技术。既不是符号微分（会表达式爆炸），也不是数值差分（有截断/舍入误差），而是用链式法则在计算图上传播导数。 |
| forward-mode AD | 前向模式 | 与函数求值同方向传播导数：从输入扰动出发，每个中间量同时带一个切线（tangent）。一次前向得到输出对*一个*输入的导数，适合输入少、输出多的情形。 |
| reverse-mode AD | 反向模式 | 先前向算出所有中间值，再从输出反向传播伴随（adjoint）。一次反向得到输出对*所有*输入的梯度，适合输入多、输出少（如标量损失对百万参数）的情形——深度学习的标配。 |
| backpropagation | 反向传播 | 反向模式自动微分在神经网络上的别名/特例。本质就是对「损失关于参数」这个标量函数做 reverse-mode AD。 |
| computational graph | 计算图 | 把一段计算表示成有向无环图（DAG）：节点是运算或值，边是数据依赖。autograd 在前向时记录这张图，反向时沿边逆序传播梯度。 |
| node / Value / Tensor (autograd) | 计算节点 | 计算图里的一个量。它记住自己由哪个运算、从哪些父节点产生（即 `_prev` 与 `_backward`），从而支持反向传播。micrograd 里叫 `Value`（标量），PyTorch 里是带 `grad_fn` 的 `Tensor`。 |
| chain rule | 链式法则 | 复合函数求导的法则：dz/dx = dz/dy · dy/dx。反向模式把它推广到 DAG：每个节点把上游传来的梯度乘以本地雅可比，再分发给各父节点。 |
| local gradient / VJP (vector-Jacobian product) | 局部梯度 / 向量-雅可比积 | 反向传播的原子操作：给定上游梯度向量 v 和本运算的雅可比 J，算 vᵀJ。反向模式从不显式构造 J（太大），而是直接算这个积。每个算子只需实现自己的 VJP 规则。 |
| JVP (Jacobian-vector product) | 雅可比-向量积 | 前向模式的原子操作 Jv。JAX 用 `jvp` 暴露它；reverse-mode 的 `vjp` 是它的转置。 |
| adjoint / cotangent | 伴随 / 余切 | 反向传播中沿图回传的量，即「损失对某中间量的梯度」。与前向的 tangent（切线）互为对偶。 |
| topological order | 拓扑序 | DAG 的一种线性排序，保证每个节点排在其所有依赖之后。反向传播必须按拓扑逆序遍历，确保一个节点的梯度在被使用前已从所有下游累加完毕。 |
| gradient accumulation (autograd) | 梯度累加 | 当一个节点被多个下游使用（计算图分叉再汇合）时，它的梯度是各路径贡献之和，必须 `+=` 而非 `=`。漏掉累加是手写 autograd 最常见的 bug。 |
| broadcasting gradient | 广播梯度 | 前向广播（小张量被复制以匹配大张量）在反向时对应「沿被广播的维度求和」。例如 `(n,d)+(d,)` 的偏置，其梯度要把 n 个样本的贡献沿样本维 sum 回 `(d,)`。 |
| custom Function / custom op | 自定义算子 | 框架允许用户为一个运算自定义 forward 与 backward（VJP）。PyTorch 是 `torch.autograd.Function`（`forward`/`backward`），JAX 是 `custom_vjp`。用于嵌入不可微近似、数值稳定实现或外部内核。 |
| numerical gradient / finite difference | 数值梯度 / 有限差分 | 用 (f(x+ε)−f(x−ε))/2ε 近似导数。慢且有误差，但与具体 autograd 实现无关，是验证（gradient check）解析梯度是否正确的黄金参考。本课每个 autograd 都与它对拍。 |
| gradient checking | 梯度检查 | 用数值梯度对拍解析梯度，确认自动微分实现正确。中心差分相对误差 < 1e-5 通常视为通过。 |
| stop_gradient / detach | 截断梯度 | 在计算图上切断某条反向路径：前向值照常，反向梯度不再回传到它之前。PyTorch 是 `.detach()`，JAX 是 `jax.lax.stop_gradient`。用于 target 网络、straight-through estimator 等。 |

## 图捕获与编译 · Graph Capture & Compilation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| eager execution | 即时执行 | 算子一写就立刻执行、立刻返回结果（PyTorch 默认、JAX 不 jit 时）。调试直观、灵活，但每个算子单独启动内核、有 Python 开销、无法跨算子优化。 |
| graph mode / lazy execution | 图模式 / 惰性执行 | 先把整段计算记录成图、不立刻执行，待整图就绪后统一编译优化再跑。牺牲一点灵活性，换来融合、常量折叠、调度优化的空间。 |
| tracing | 追踪 | 用具体（或抽象）输入实际跑一遍程序，记录下所经过的算子序列得到图。简单且覆盖真实执行路径，但会「烤死」数据相关的控制流（if/循环按本次走的分支记录），且看不到 Python 副作用。JAX 与 torch.compile/Dynamo 都以 tracing 为主。 |
| scripting | 脚本化 | 直接解析源代码（AST）把程序翻译成图，能保留 if/for 等控制流。`torch.jit.script` 的方式；覆盖更全但需支持 Python 子集、实现复杂。 |
| IR (intermediate representation) | 中间表示 | 编译器内部用来表示程序的数据结构，介于源码与机器码之间。深度学习编译器的 IR 通常是算子级的图（如 torch.fx 的 GraphModule、JAX 的 jaxpr、XLA 的 HLO）。 |
| torch.fx / FX graph | —— | PyTorch 的 Python 级图捕获与变换工具：把模块 trace 成一张由 `call_function`/`call_module` 等节点组成的图，便于做图变换。 |
| jaxpr | —— | JAX 的 IR：把被 trace 的纯函数表示成一串带显式输入输出的原语（primitive）方程。可打印、可分析，是理解 JAX「函数式 = 可变换」的窗口。 |
| HLO (High Level Optimizer) | —— | XLA 的中层 IR。JAX/TF 把计算降低成 HLO，XLA 在其上做融合、布局、内存规划，再生成各后端（GPU/TPU/CPU）代码。 |
| TorchDynamo | —— | torch.compile 的前端：通过 CPython 的帧求值钩子在字节码层面拦截 Python，把可捕获的部分 trace 成 FX 图，遇到不能捕获处「graph break」回退 eager。 |
| graph break | 图断裂 | Dynamo 遇到无法 trace 的 Python（如打印、数据相关分支、不支持的调用）时，把图在此切断、退回 eager 执行该段、之后再开新图。graph break 越多，编译收益越少。 |
| TorchInductor | —— | torch.compile 的默认后端编译器：把 FX 图降低、做融合与调度，在 GPU 上生成 Triton 内核、在 CPU 上生成 C++/OpenMP。把「手写融合内核」自动化。 |
| operator fusion | 算子融合 | 把多个相邻算子合并成一个内核，中间结果留在寄存器/缓存而不落主存，省掉中间张量的读写。逐元素链、规约、归一化最受益。是编译器与 FlashAttention 共同的核心优化。 |
| constant folding | 常量折叠 | 编译期就把只依赖常量的子表达式算出来，用结果替换该子图，运行时不再重复计算。 |
| dead code elimination (DCE) | 死代码消除 | 删掉对最终输出无贡献（没有被任何输出依赖）的节点。配合常量折叠与融合，是图清理的标准步骤。 |
| common subexpression elimination (CSE) | 公共子表达式消除 | 同一个子表达式被算了多次时，只算一次、复用结果。 |
| JIT (just-in-time) compilation | 即时编译 | 在运行时（而非提前）针对实际遇到的形状/类型编译代码。torch.compile、jax.jit、numba 都是 JIT。 |
| guard | 守卫 | JIT 缓存编译结果时记录的前提条件（如输入形状、dtype、某些值）。下次调用先检查 guard 是否成立：成立则复用编译产物，不成立则重新编译。Dynamo 用 guard 保证 trace 出的图对当前输入有效。 |
| recompilation | 重编译 | guard 不满足（如形状变了）时触发的重新编译。形状频繁变化会导致反复重编译、抵消收益，故有 `dynamic=True`、padding 等对策。 |
| CUDA Graph | —— | 把一串内核启动录制成一个可重放的图，重放时绕过逐个内核的 CPU 启动开销。针对开销受限（overhead-bound）的小内核场景，torch.compile 可配合使用。 |

## 函数式变换 · Functional Transforms (JAX)

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pure function | 纯函数 | 输出只由输入决定、无副作用（不改全局、不做 IO、不依赖隐藏状态）的函数。JAX 的一切变换都要求纯函数——纯，才能安全地 trace、缓存、并行、重排。 |
| functional transform | 函数变换 | 接受一个函数、返回一个新函数的高阶操作。JAX 的 `grad`/`vmap`/`jit`/`pmap` 都是函数变换，且可任意组合（`jit(vmap(grad(f)))`）。这是 JAX 与 PyTorch 心智模型的最大分野。 |
| `jax.grad` | —— | 函数变换：`grad(f)` 返回一个计算 f 梯度的新函数。底层是 reverse-mode AD，但以「函数→函数」而非「张量.backward()」的形式暴露。 |
| `jax.vmap` (vectorizing map) | 向量化映射 | 自动把一个写给单个样本的函数批量化：`vmap(f)` 沿新增的批维并行应用 f，无需手写 batch 维。等价于自动插入正确的 broadcasting/批处理，比手写循环或手动加维更不易错。 |
| `jax.jit` | —— | 函数变换：trace 出 jaxpr、交给 XLA 编译融合后缓存。首调编译、后续复用，对同一形状只编译一次。 |
| `jax.pmap` / sharding | 并行映射 / 分片 | 把计算沿设备维并行（多 GPU/TPU）。新版多用 `jit` + `shard_map`/`Mesh` 表达分布式。 |
| pytree | —— | JAX 对「嵌套容器」（dict/list/tuple 套张量）的统称。变换会自动「穿过」pytree 作用到叶子上。`tree_flatten`/`tree_unflatten` 把结构与叶子分离再复原，是处理模型参数的基础。 |
| leaf / treedef | 叶子 / 树定义 | pytree 展平后，`leaves` 是所有叶子张量的扁平列表，`treedef` 记录如何把它们装回原结构。两者合起来无损表示一个 pytree。 |
| functional updates | 函数式更新 | 不原地改张量，而是返回改过的新张量（`x.at[i].set(v)`）。配合纯函数范式；优化器状态、参数更新都写成「旧状态→新状态」的纯函数。 |
| `jax.lax` | —— | JAX 的底层原语库（控制流 `scan`/`cond`/`while_loop`、规约、`stop_gradient` 等）。可被 trace 进 jaxpr 的结构化控制流，替代会被 trace「烤死」的 Python `if/for`。 |

## 数值精度与显存 · Precision & Memory

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| floating point (IEEE 754) | 浮点数 | 用「符号 × 尾数 × 2^指数」表示实数。位宽分给指数（决定动态范围）与尾数（决定相对精度），不同格式的分配方式造成了 fp32/fp16/bf16 的取舍。 |
| fp32 / single precision | 单精度 | 1 符号 + 8 指数 + 23 尾数。深度学习长期的默认精度，范围与精度都够用，但显存与带宽是 fp16 的两倍。 |
| fp16 / half precision | 半精度 | 1 + 5 + 10。尾数多但**指数只有 5 位**，动态范围窄（最大 ~65504），易上溢/下溢，故训练需配 loss scaling。算力与带宽优势显著。 |
| bf16 / bfloat16 | —— | 1 + 8 + 7。指数与 fp32 一样宽（范围几乎相同），但尾数只有 7 位（精度低）。范围大使它**通常无需 loss scaling**，是现代大模型训练的主流半精度格式。 |
| fp8 (E4M3 / E5M2) | —— | 8 位浮点，两种指数/尾数分配。前沿训练/推理（Hopper 及以后）用它进一步提吞吐，需更精细的 scaling 与混合策略。 |
| dynamic range | 动态范围 | 一种格式能表示的最大值与最小正规数之比，由**指数位数**决定。范围不够会上溢成 inf 或下溢成 0——半精度训练的核心风险。 |
| machine epsilon | 机器精度 | 1.0 与下一个可表示浮点数之差，由**尾数位数**决定，刻画相对精度。fp16 的 eps ≈ 1e-3，bf16 ≈ 8e-3，fp32 ≈ 1e-7。 |
| overflow / underflow | 上溢 / 下溢 | 数值超出格式最大值变 inf（上溢），或小于最小正规数被冲刷成 0（下溢）。fp16 训练中梯度极小，最易下溢消失。 |
| rounding | 舍入 | 把一个实数映射到最近的可表示浮点数。低精度下舍入误差累积会影响训练，故有「主权重 fp32、计算 fp16」的混合策略。 |
| mixed precision training | 混合精度训练 | 前向/反向用低精度（fp16/bf16）算以提速省显存，关键处（主权重副本、loss scaling、某些规约）保 fp32 以保稳。PyTorch 的 `autocast` + `GradScaler` 是其实现。 |
| autocast | —— | PyTorch 自动混合精度上下文：在其中，每个算子按预设规则自动选 fp16/bf16 或 fp32（如 matmul 用半精度、softmax/loss 用 fp32），无需手动转换每个张量。 |
| loss scaling | 损失缩放 | fp16 训练防梯度下溢的关键技巧：反向前把 loss 乘一个大常数 S（梯度同比放大、逃离下溢区），更新前再把梯度除回 S。bf16 因范围大通常不需要。 |
| dynamic loss scaling | 动态损失缩放 | 自动调 S：遇到梯度出现 inf/nan（缩放过大溢出）就跳过本步并把 S 减半；连续若干步正常就把 S 翻倍。`GradScaler` 的默认策略。 |
| master weights | 主权重 | 混合精度训练中保留的一份 fp32 参数副本。前向用其 fp16 拷贝算，但优化器在 fp32 主权重上更新——避免「极小更新量加到 fp16 权重上被舍入丢失」。 |
| activation memory | 激活显存 | 前向产生、为反向保留的中间张量（激活）所占显存。深层网络里它常是显存大头，且随 batch、序列长、层数线性增长。 |
| gradient checkpointing / activation recomputation | 梯度检查点 / 激活重算 | 用算力换显存：前向只保存少量检查点处的激活，反向需要时从最近检查点**重新前向**算出来。把激活显存从 O(L) 降到 O(√L) 量级，代价是约一次额外前向。 |
| memory peak | 显存峰值 | 训练过程中任意时刻的最大显存占用，决定能否放进卡。它发生在反向开始时（参数 + 梯度 + 优化器状态 + 全部激活同时在场），是 OOM 的判据。 |
| optimizer state | 优化器状态 | 优化器为更新而维护的额外张量。Adam 每个参数存一阶、二阶矩两份，加上 fp32 主权重，使显存可达参数本身的数倍——大模型显存账的重要一项。 |
| OOM (out of memory) | 显存溢出 | 申请的显存超过设备容量导致的失败。对策：减 batch、梯度累加、checkpointing、混合精度、分片（ZeRO/FSDP）。 |

## 性能剖析与调试 · Profiling & Debugging

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| profiling | 性能剖析 | 测量程序各部分的耗时、显存、设备利用率，定位瓶颈。优化的第一步永远是「先测量、别猜」。 |
| profiler | 性能分析器 | 做 profiling 的工具：PyTorch 的 `torch.profiler`、NVIDIA Nsight Systems/Compute、Python 的 `cProfile`。给出按算子/调用栈聚合的耗时与显存。 |
| operator-level timing | 算子级计时 | 把总时间归因到每个算子（matmul 花多少、softmax 花多少），找出最值得优化的热点。本课玩具 profiler 复刻这一能力。 |
| wall-clock vs device time | 墙钟时间 vs 设备时间 | 墙钟是从开始到结束的真实流逝时间；设备时间是 GPU/TPU 实际计算的时间。两者差距大说明有同步/启动/数据搬运开销。 |
| CUDA synchronization | CUDA 同步 | GPU 算子是异步下发的，CPU 计时若不 `torch.cuda.synchronize()` 会量到「下发时间」而非「执行时间」——GPU 计时最常见的坑。 |
| roofline model | roofline 模型 | 把性能上限画成带宽段（斜线）与算力段（水平线），用算术强度判断内核受带宽还是算力限制。本课模块 05 回顾它来给 profiling 结论定性。 |
| arithmetic intensity | 算术强度 | 每搬运一字节所做的浮点运算数（FLOPs/byte），决定算子是访存受限还是算力受限，是 roofline 的横轴。 |
| compute-bound / memory-bound / overhead-bound | 算力 / 访存 / 开销受限 | 性能瓶颈的三大类：等算（大 matmul）、等数据搬运（逐元素、softmax）、等调度与启动（大量小内核、Python 开销）。先归类再对症。 |
| NaN / Inf debugging | NaN/Inf 调试 | 训练出现 NaN 的溯源：常见源头是 log(0)、0/0、exp 上溢、过大学习率、fp16 未做 loss scaling。对策是定位**首次**出现 NaN 的算子并检查其输入。 |
| anomaly detection | 异常检测 | 框架提供的「一出现 NaN/Inf 就报错并指出是哪个算子」的调试模式（PyTorch 的 `torch.autograd.set_detect_anomaly`）。代价是大幅变慢，仅调试时开。 |
| gradient clipping | 梯度裁剪 | 把梯度范数限制在阈值内，防止梯度爆炸导致 NaN/训练发散。是稳住训练的常用手段。 |
| determinism / reproducibility | 确定性 / 可复现 | 让多次运行结果逐位一致。需固定随机种子、禁用非确定性内核（某些 atomic 规约顺序不定）、控制并行规约顺序。代价通常是性能。 |
| flame graph / trace timeline | 火焰图 / 时间线 | profiler 输出的可视化：火焰图按调用栈展示耗时占比，时间线按时间轴展示各算子/流的执行与重叠。 |

## 框架与生态 · Frameworks & Ecosystem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| PyTorch | —— | 以 eager、动态图、Python 优先著称的框架。`autograd` 提供反向模式 AD，`torch.compile`（2.0）引入图捕获 + 编译以缩小与图模式的性能差距。 |
| JAX | —— | 以「可组合的函数变换 + XLA 编译」为核心的框架。要求纯函数，`grad`/`vmap`/`jit`/`pmap` 自由组合，研究界尤其青睐其表达力。 |
| TensorFlow | —— | 早期以静态图（`tf.Graph`）为主、后引入 eager 的框架。XLA 最初为它而生。 |
| XLA (Accelerated Linear Algebra) | —— | Google 的深度学习编译器，把 HLO 图融合、优化、生成 GPU/TPU/CPU 代码。JAX 与 TF 的编译后端。 |
| Triton | —— | 用 Python 写 GPU 内核的 DSL/编译器（Tillet 2019）：按「块」编程，编译器管线程映射与融合。TorchInductor 在 GPU 上生成的就是 Triton 内核。 |
| TorchScript | —— | PyTorch 早期的图捕获方案（`torch.jit.trace`/`script`），用于序列化与部署；torch.compile 之后逐渐让位。 |
| ONNX | —— | 跨框架的模型交换格式与算子集，便于把训练好的模型导出到各推理运行时。 |
| accelerator (GPU/TPU) | 加速器 | 为张量运算优化的并行硬件。框架的编译与混合精度都是为了榨取它的算力与带宽。 |
