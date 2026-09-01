# 术语词典（中英对照）

> 按 7 个内容模块的顺序组织。每条保留英文术语（加粗），配 2–3 句中文释义并与本课语境（账本估算 / 面试 drill）挂钩。读 HTML 讲解或跑 notebook 遇到生词时回查这里。末尾附「常用数值速查」，面试现场口算时直接抄。

---

## 01 · 显存解剖与 Roofline

| 术语 | 释义 |
|------|------|
| **params / weights（参数）** | 模型本体的可训练张量。fp16 下每参数 2 字节、fp32 下 4 字节，所以一个 $P$ 参数模型的权重显存 $=P\cdot b_p$。这是训练显存四块账里最直观、却往往最小的一块——真正撑爆显存的多半是优化器状态和激活。 |
| **grads（梯度）** | 反向传播算出的、与每个参数一一对应的导数张量。它和参数同形、同精度（混合精度下通常 fp16，2 字节/参数），所以梯度显存 ≈ 权重显存。梯度只在一次更新内活着，更新完即可释放（除非梯度累积要攒着）。 |
| **optimizer states（优化器状态）** | 优化器为每个参数额外维护的辅助张量。Adam 存一阶动量 $m$ 与二阶动量 $v$，且混合精度下还要保一份 fp32 主权重——三者各 4 字节，合计 12 字节/参数，常是四块账里最大的一块。换 SGD（无动量）这块几乎为 0，所以「优化器选择」直接改写显存预算。 |
| **activations（激活）** | 前向传播产生、反向要复用的中间张量。随层数 $L$、batch $B$、序列长 $S$、隐藏维 $h$ 线性增长，注意力分数矩阵还带 $S^2$ 项，长上下文训练常先被它压爆显存。它是四块里唯一能被「重计算」大幅压缩的一块（见模块 02）。 |
| **activation memory（激活显存）** | 激活那块账的总量，常用近似 $\approx s\cdot b\cdot h\cdot L\cdot(\text{每层激活系数})$。Korthikanti 2022 给出 Transformer 每层激活 $\approx sbh(34+5\frac{as}{h})$ 字节（$a$=头数）的细账，其中 $\frac{as}{h}$ 项就是 $S^2$ 注意力的来源。 |
| **16 bytes/param 法则** | 混合精度 Adam 训练的经验口径：fp16 权重 2 + fp16 梯度 2 + fp32 主权重 4 + fp32 $m$ 4 + fp32 $v$ 4 = 16 字节/参数（不含 activation）。记住它就能秒估任何模型的训练显存下界：7B 模型 ≈ 112 GB，单卡 80GB 放不下，必须分片或并行。 |
| **roofline model（屋顶线模型）** | 用峰值算力（FLOP/s）与内存带宽（byte/s）两条线给 kernel 运行时间画下界：$T\ge\max(\text{FLOPs}/\text{峰值},\ \text{bytes}/\text{带宽})$。是判断瓶颈在算力还是带宽的标准工具（Williams 2009）。把它画成图：横轴算术强度、纵轴可达 FLOP/s，左半带宽斜坡、右半算力平顶。 |
| **arithmetic intensity（算术强度）** | 一次计算里 FLOPs 与搬运字节数之比，单位 FLOP/byte。强度高于拐点 → compute-bound；低于拐点 → memory-bound。自回归解码（矩阵×向量）强度极低（≈1），是 LLM 推理慢的根因；大 batch GEMM 强度高，才吃得满算力。 |
| **ridge point（拐点强度）** | roofline 上算力斜坡与峰值平顶的交点，$=$ 峰值算力 $/$ 带宽。A100 约 $312\text{T}/2\text{T}\approx156$ FLOP/byte：低于它白白浪费算力，高于它才吃满。算术强度要「越过拐点」是所有分块/批处理优化的共同目标。 |
| **compute-bound（算力受限）** | 时间被峰值算力卡住、带宽有余的状态。大矩阵乘、prefill、大 batch 训练通常如此，优化重点是提高算力利用率（MFU）、用上 Tensor Core。此时换更高带宽的显存没用，得换更高算力或更高 MFU。 |
| **memory-bound（访存受限）** | 时间被内存带宽卡住、算力空转的状态。逐元素操作、softmax、batch=1 解码属于此类，优化重点是减少 HBM 读写（量化、batching、FlashAttention、算子融合）。此时算力再强也用不上。 |
| **HBM（High-Bandwidth Memory）** | GPU 的主显存（A100/H100 几十 GB、带宽 1–3 TB/s）。容量大但相对慢，训练显存四块账都住在这里；减少 HBM 往返是系统优化的核心母题。带宽（TB/s）和容量（GB）是两个独立约束，分别卡 memory-bound 速度与「放不放得下」。 |
| **SRAM（片上共享内存）** | GPU 计算单元旁的小而极快的存储（每 SM 几十~两百 KB，A100 共 ~20MB）。FlashAttention 把分块数据留在 SRAM 上算、不落地 $S^2$ 矩阵到 HBM，正是利用这层。SRAM 容量直接限制了分块大小（见模块 04）。 |
| **FLOPs（浮点运算数）** | 完成某计算所需的浮点运算总数（标量、累积量）。账本里训练总量用 FLOP（如 $6ND$），是和硬件 FLOP/s 相除得到时间的分子。注意复数 FLOPs 既可指「次数」也常被口语当「速率」用，靠上下文区分。 |
| **peak FLOP/s（峰值算力）** | 硬件每秒能做的最大浮点运算数（速率）。A100 bf16 312 TFLOP/s、H100 bf16 ~990 TFLOP/s 都是这个量。它是 roofline 的平顶高度，也是 MFU 的分母——但实际几乎从不达到峰值。 |
| **memory bandwidth（内存带宽）** | GPU 每秒能从 HBM 搬运的字节数（A100 ~2 TB/s、H100 ~3.35 TB/s）。它是 roofline 带宽斜坡的斜率，决定 memory-bound kernel（解码、归一化）的速度上限。 |
| **FLOP vs FLOP/s** | FLOP 是一次浮点运算（计算量，标量）；FLOP/s 是每秒浮点运算数（算力速率）。账本里训练总量用 FLOP（如 $6ND$），硬件能力用 FLOP/s（如 A100 312 TFLOP/s）——两者别混，时间 $=$ FLOP $/$ FLOP/s。 |
| **model FLOPs（模型 FLOPs）** | 模型本身一次前/反向的有效浮点运算量，不含 kernel 实现里的冗余。MFU 用它做分子；区别于把重计算等开销也算进去的 hardware FLOPs（HFU 用后者）。同一次训练，model FLOPs 固定，但 hardware FLOPs 随你是否开重计算而变。 |
| **参数量公式** | Transformer 参数量 $\approx 2Vh$（embedding+输出）$+ L\cdot(4h^2 + 2hI + \text{偏置/LayerNorm})$。本课 notebook 用真实 config 的 $V,h,L,I$ 算出与官方一致的参数量，是所有账本的起点。$4h^2$ 来自注意力的 QKVO 四个投影、$2hI$ 来自 FFN 升降维。 |

---

## 02 · 混合精度与重计算

| 术语 | 释义 |
|------|------|
| **mixed precision（混合精度）** | 训练时大部分计算用低精度（fp16/bf16）省显存提速、关键处（更新、累加）保 fp32 防误差的范式。标准配方：fp16/bf16 算前反向、fp32 主权重做更新、（fp16 时）配 loss scaling。是现代大模型训练的默认设置（Micikevicius 2018）。 |
| **fp32（单精度）** | 32 位浮点：1 符号 + 8 指数 + 23 尾数，动态范围 ~$10^{\pm38}$。是数值基准，混合精度训练里用作主权重与优化器状态的格式。精度足够但显存与带宽是 fp16 的两倍。 |
| **fp16（半精度）** | 16 位：1+5+10，动态范围窄（~$6\times10^{\pm4}$）。省一半显存，但小梯度易下溢为 0、大值易上溢，因此通常必须配 loss scaling。是 V100 时代的主力，现已大多被 bf16 取代。 |
| **bf16（bfloat16）** | 16 位：1+8+7，指数位与 fp32 同宽，动态范围 ≈ fp32，只是尾数精度低（相对误差 ~$2^{-8}$）。几乎不下溢、不需 loss scaling，是现代训练的首选 16 位格式（A100/H100 原生支持）。 |
| **fp8（E4M3 / E5M2）** | 8 位浮点的两种排布：E4M3（4 指数 3 尾数，范围 ~±448，精度高，前向用）、E5M2（5 指数 2 尾数，范围大，反向梯度用）。H100 Transformer Engine 起支持，再省一半但需精细的 per-tensor 缩放才数值可用（Micikevicius 2022）。 |
| **mantissa（尾数）** | 浮点数表示有效数字的部分，决定精度（相邻可表示数的相对间隔 ≈ $2^{-\text{尾数位}}$）。fp16 有 10 位、bf16 只有 7 位——这是 bf16 比 fp16 精度低的直接原因。 |
| **exponent（指数）** | 浮点数表示数量级的部分，决定动态范围（能表示多大/多小）。bf16 与 fp32 同为 8 位指数，故动态范围相同；fp16 只有 5 位，范围窄得多，这是它需要 loss scaling 的根源。 |
| **dynamic range（动态范围）** | 一种格式能表示的最大值与最小正规数之比。训练梯度跨多个数量级，范围不够（fp16）就溢出/下溢，这是 bf16 取代 fp16 的根本原因——bf16 用精度换范围，对深度学习是划算的交易。 |
| **underflow / overflow（下溢 / 上溢）** | 数值小到落入次正规区甚至变 0 叫下溢，大到超出最大可表示数变 inf 叫上溢。fp16 训练里小梯度下溢使参数停更，是 loss scaling 要救的主要病；上溢则使梯度变 inf、动态 loss scaling 会检测到并跳过该步。 |
| **subnormal（次正规数）** | 小于最小正规数、用前导零换更小可表示值的浮点区间。fp16 的次正规下限 ~$6\times10^{-8}$，梯度落进这里精度急剧损失，再小就下溢为 0。 |
| **loss scaling（损失缩放）** | fp16 下反向前把 loss 乘大常数 $s$，使梯度整体放大进可表示范围，更新前再除回 $s$：$g_{\text{fp16}}=\nabla(sL)=s\nabla L$。静态版固定 $s$（如 1024），动态版遇 inf/nan 减半并跳过该步、连续 $N$ 步正常则加倍。bf16 因范围够大通常不需要它。 |
| **static / dynamic loss scaling（静态/动态损失缩放）** | 静态：手调一个固定缩放因子，简单但需调参、不适应训练阶段变化。动态：自动探测溢出回退、平稳期加倍，无需调参且鲁棒，是框架默认。 |
| **master weights（fp32 主权重）** | 混合精度下额外保存的一份 fp32 权重。fp16 权重用于前/反向计算，但参数更新（Adam 的微小累加）在 fp32 主权重上做，避免「大权重 + 小更新」在 fp16 下被精度吃掉（舍入到无变化）。这份主权重就是 16 bytes/param 里的那 4 字节。 |
| **gradient accumulation（梯度累积）** | 把大 batch 拆成 $k$ 个 micro-batch，逐个前/反向、累加梯度但不更新，攒满 $k$ 个再更新一次，数学上等价 $k$ 倍大 batch。用计算时间换显存（不必一次性放下大 batch 的激活）。注意 loss 要按总样本归一化，漏除 $k$ 会把等效学习率放大 $k$ 倍。 |
| **micro-batch（微批）** | 梯度累积或流水线并行里，一次实际前/反向处理的小批量。多个 micro-batch 累加成一个等效大 batch（更新粒度），或填充流水线摊薄气泡。micro-batch 大小直接决定单步激活显存峰值。 |
| **effective batch size（等效批大小）** | 一次参数更新实际覆盖的样本总数 $=$ micro-batch $\times$ 累积步数 $\times$ 数据并行度。它（而非单卡 micro-batch）才是影响优化动力学与学习率的量。调系统配置（拆 micro-batch、加并行）时要保持它不变，否则等于偷偷改了超参。 |
| **activation checkpointing / recomputation（激活检查点 / 重计算）** | 前向只存少数 checkpoint 的激活、其余丢弃，反向需要时从最近 checkpoint 重新前向算一遍。把激活显存从 $O(L)$ 降到 $O(\sqrt L)$，代价是约多一次前向（算力 +~33%）。又名 gradient checkpointing，是长序列/大模型训练的标配开关。 |
| **gradient checkpointing** | activation checkpointing 的同义别名（PyTorch `torch.utils.checkpoint` 用此名）。强调它服务于「为算梯度而重算前向」，本质同一技术。 |
| **√L memory（√L 显存）** | 重计算的最优分段结果：存 $m$ 个 checkpoint，峰值激活 $\approx O(L/m + m)$，对 $m$ 求极小得 $m=\sqrt L$，故显存 $O(\sqrt L)$，而额外计算仅一次前向（Chen 2016）。这是「用 $O(1)$ 倍计算换 $O(\sqrt L)$ 倍显存」的漂亮权衡。 |
| **selective recomputation（选择性重计算）** | 只对显存大而重算便宜的算子（如注意力的 $S^2$ 部分）做重计算，保留矩阵乘等结果。Korthikanti 2022 指出这能以远低于 33% 的算力代价（~2–5%）省下大部分激活显存，是比「全部重算」更精明的做法。 |
| **Transformer Engine** | NVIDIA 在 H100 上的 fp8 训练库，自动管理 per-tensor 缩放因子、按张量选 E4M3/E5M2，使 fp8 训练数值可用。把模块 02（精度）与模块 05（量化缩放）的思想用在了训练前反向上。 |

---

## 03 · 并行策略

| 术语 | 释义 |
|------|------|
| **data parallelism（DP，数据并行）** | 每张卡放一份完整模型、各处理 batch 的一部分，反向后 all-reduce 同步梯度。简单、扩展性好，解决「想更快」，但每卡仍存完整 $16P$ 状态，不省单卡显存。是最基础的并行维度，常与下面其它维度叠加。 |
| **tensor parallelism（TP，张量并行）** | 把单层的权重矩阵按行/列切到多卡，每卡算一部分再 all-reduce/all-gather 拼回（Megatron 做法：一层前向 2 次 all-reduce）。解决「单层都放不下」，但通信极频繁，几乎只限机内 NVLink 域用。 |
| **pipeline parallelism（PP，流水线并行）** | 把模型按层分段放到不同卡，数据像流水线依次流过。解决「层数太多、单卡放不下整个模型」，通信量小（只传层间激活），但有填充/排空的气泡，需多 micro-batch 摊薄。 |
| **ZeRO（Zero Redundancy Optimizer）** | DeepSpeed 的分片技术，消除 DP 里每卡重复存的 $16P$ 拷贝。Stage 1 分片优化器状态、Stage 2 再分梯度、Stage 3 连参数也分，每卡显存逐级降到 ≈ $16P/N$（Rajbhandari 2020）。它在「不改模型并行结构」的前提下省显存，思想优雅。 |
| **ZeRO stage 1/2/3** | 三级分片的每卡显存近似：Stage 1 $=2P+2P+12P/N$；Stage 2 $=2P+(2P+12P)/N$；Stage 3 $=16P/N$。级越高越省显存，但用时要 all-gather 参数，通信越多。Stage 3 用一份完整模型的通信量换到几乎线性的显存缩减。 |
| **FSDP（Fully Sharded Data Parallel）** | PyTorch 原生的 ZeRO-3 等价实现：参数/梯度/优化器状态全分片，前向/反向按需 all-gather 重组该层权重、用完即释放。是当下训练大模型最常用的省显存方案，与 `torch.compile`、混合精度配合良好。 |
| **all-reduce** | 把各卡的张量求和（或平均）后再分发回所有卡的集合通信。DP 用它同步梯度；ring 实现下通信量 ≈ $2P\cdot b_g$、与卡数近乎无关，这是 DP 能扩展的关键。 |
| **ring all-reduce（环形归约）** | all-reduce 的环形实现：分 reduce-scatter 与 all-gather 两阶段、各 $N-1$ 步、每步传 $P/N$，总通信量 $\approx 2\frac{N-1}{N}P\approx 2P$。这是「通信量与卡数无关」的来源，让大规模 DP 通信不爆炸。 |
| **all-gather（全收集）** | 把每张卡各自持有的分片收集成完整张量、分发给所有卡。ZeRO-3/FSDP 在用到分片参数前靠它临时重组出完整权重，用完即丢。 |
| **reduce-scatter（归约散射）** | all-reduce 的前半段：求和的同时把结果按卡切分，每卡只留 $1/N$。与 all-gather 互为逆操作，是分片通信的基本积木；ZeRO-2 用它同步并分片梯度。 |
| **pipeline bubble（流水线气泡）** | PP 中填充与排空阶段部分卡空闲造成的浪费，占比 $\approx\frac{p-1}{m+p-1}$（$p$ 段数、$m$ micro-batch 数）。增大 $m$ 可摊薄，所以 PP 总配大 micro-batch 数；这也是 PP 与梯度累积天然契合的原因。 |
| **micro-batch（PP 中的微批）** | 流水线并行里被切碎、依次注入流水线的小批量。micro-batch 越多，气泡占比越小、流水线越「满」，但每个的激活都要留到反向，故 micro-batch 数与激活显存此消彼长。 |
| **1F1B schedule（一前一后调度）** | PP 的稳态调度：进入稳态后每个 stage 交替做一次前向、一次反向，使在飞的激活数被限制在 $\approx p$ 个而非全部 $m$ 个，大幅降低 PP 的激活显存峰值（Narayanan 2021 的 PTD-P 用它）。 |
| **3D parallelism（三维并行）** | TP × PP × DP/ZeRO 的组合：TP 机内切层、PP 跨机分段、DP/ZeRO 再复制或分片。训练 GPT-3/PaLM 级万亿参数模型的标准配方，三个维度分别治「单层放不下/层数太多/想更快且省显存」。 |
| **sequence / context parallelism（序列 / 上下文并行）** | 把超长序列沿序列维切到多卡，分摊注意力与激活的 $S$/$S^2$ 开销，是长上下文训练的关键补充维度。它与 TP 正交，常叠加使用，专治「序列太长导致激活爆炸」。 |
| **expert parallelism（专家并行，MoE）** | MoE 模型里把不同专家（FFN）分到不同卡，按 router 分发 token（all-to-all 通信）。让总参数远大于单卡容量而每 token 只激活少数专家，实现「大容量、低算力」。 |
| **NVLink** | NVIDIA 的机内高带宽 GPU 互联（数百 GB/s，远超 PCIe/以太网）。TP 通信频繁，只有在 NVLink 域内才划算，跨节点用 TP 会被网络拖死——这就是「TP 限机内、PP/DP 跨机」的物理原因。 |
| **通信-计算 overlap（重叠）** | 把集合通信（如梯度 all-reduce、参数 all-gather）与计算在时间上重叠，隐藏通信延迟。是 ZeRO/FSDP/DP 实现里影响 MFU 的关键工程点，做不好通信就会暴露成纯等待。 |

---

## 04 · FlashAttention

| 术语 | 释义 |
|------|------|
| **online softmax（在线 softmax）** | 流式增量地算 softmax：维护已见过的 running max $m$ 与指数和 $\ell$，每来一块新分数就更新它们，并按校正因子折算旧的累积。扫完逐位等于一次性 softmax，却从不存整行（Milakov 2018）。这是 FlashAttention 不落地 $S^2$ 矩阵的数学前提。 |
| **safe softmax（数值稳定 softmax）** | 算 softmax 前先减去该行最大值再取指数，避免 $e^x$ 上溢为 inf。数学上与朴素 softmax 等价（分子分母同乘常数），online softmax 把这个「减最大值」做成可随新最大值动态更新的运行态版本。 |
| **running max / running sum（运行最大值 / 运行和）** | online softmax 维护的两个标量：到目前为止见过的最大分数 $m$、以及以 $m$ 为基准的指数和 $\ell$。新块到来时据其更新，保证数值稳定与结果精确；注意力里还多维护一个运行输出向量 $O$。 |
| **correction factor（校正因子）** | 当发现更大的最大值 $m_{\text{new}}$ 时，对旧的指数和与输出乘 $e^{m_{\text{old}}-m_{\text{new}}}\in(0,1]$ 做缩放，等价于「重新以新最大值为基准」。是 online softmax 正确性的核心，漏乘它结果就错。 |
| **tiling（分块）** | 把 Q、K、V 切成小块，外层循环 Q 块、内层循环 K/V 块，每对块的分数只在 SRAM 上算并用 online softmax 累积到输出。FlashAttention 借此避免把 $S^2$ 分数矩阵落地 HBM，是它省显存又省带宽的机制本体。 |
| **SRAM（片上高速存储）** | GPU 计算单元旁的小而极快的存储。FlashAttention 把分块的 Q/K/V 与中间分数留在 SRAM 上算、不回 HBM；SRAM 容量（每 SM 几十~两百 KB）直接限制了可用的 block size。 |
| **IO complexity（IO 复杂度）** | 衡量 kernel 的 HBM 读写字节量（而非 FLOPs）。标准 attention 的 HBM 访问 $\Theta(S^2)$，FlashAttention 降到 $\Theta(S^2 d^2/M)$（$M=$ SRAM 大小），这是它更快的真正原因——FLOPs 几乎没少，省的是搬运。 |
| **HBM accesses（HBM 访问量）** | 计算单元与主显存之间搬运的总字节数。因为 attention 是 memory-bound，墙钟时间几乎由 HBM 访问量决定，省搬运比省计算更值钱——这就是「IO 感知算法」的立论点。 |
| **memory-bound attention（访存受限的注意力）** | 标准注意力的瓶颈不在算 $QK^\top$ 的 FLOPs，而在反复读写 $S^2$ 分数矩阵的 HBM 带宽。认清这点，才理解 FlashAttention 为何「FLOPs 没少反而更快」。 |
| **recomputation（FlashAttention 反向重计算）** | FlashAttention 反向不存正向的 $S^2$ 分数矩阵，而是用保存下来的 $m,\ell$ 统计量按需重算（呼应模块 02 的重计算思想），用少量额外 FLOPs 换 $O(S)$ 而非 $O(S^2)$ 的显存。 |
| **block size（分块大小）** | tiling 中每块的行/列数，受 SRAM 容量约束。太大放不进 SRAM，太小并行度与复用率不足；是 FlashAttention 调优的关键超参，FA-2 起常用 autotune 搜索。 |
| **FlashAttention-2 / -3** | 后续版本：FA-2 改进并行与 work partition、减少非 matmul FLOPs、把 Q 放外层循环，更逼近峰值（Dao 2023）；FA-3 针对 H100 用异步拷贝（TMA）、warp 专门化与 fp8 再提速（Shah 2024）。 |
| **kernel fusion（算子融合）** | 把多个本要各自读写 HBM 的算子合并成一个 kernel，中间结果留在寄存器/SRAM。FlashAttention 本质就是把 $QK^\top$ + softmax + $\cdot V$ 三步融成一个 IO 高效的 kernel，省掉中间张量的 HBM 往返。 |

---

## 05 · 量化

| 术语 | 释义 |
|------|------|
| **symmetric / asymmetric quantization（对称 / 非对称量化）** | 对称：零映射到零、范围关于 0 对称（absmax，适合近零均值对称的权重）；非对称：引入 zero-point 把 $[\min,\max]$ 映射到无符号整数区间（适合 ReLU 后全正的激活）。选错会浪费一半量化级或引入偏置。 |
| **absmax** | 对称量化的缩放定法：取张量绝对值的最大值，$s=\max\vert W\vert /127$（int8），把 $[-\max,\max]$ 线性映射到 $[-127,127]$。简单且对权重很合适，但一个离群值会撑大 $s$、毁掉其余值精度。 |
| **scale（缩放因子 $s$）** | 量化整数与浮点之间的换算系数：$\hat W=q\cdot s$（对称）。$s$ 越小量化步长越细、误差越小，这正是 per-channel/per-group 的动机——把一个大 $s$ 拆成多个局部小 $s$。 |
| **zero-point（$z$，零点）** | 非对称量化里「真实浮点 0 对应的整数值」：$q=\text{round}(W/s)+z$，反量化 $\hat W=(q-z)\cdot s$。保证浮点 0 能被精确表示，避免引入系统性偏置误差。 |
| **per-tensor / per-channel / per-group（量化粒度）** | 整张量共用一个 $s$（最省、但一个离群值撑大 $s$）/ 每列每行一个 $s$ / 每 $G$ 个元素一组一个 $s$。粒度越细误差越小，只多存少量 scale；本课在真实 GPT-2 权重上实测 per-channel RMSE 明显低于 per-tensor。 |
| **group size（组大小 $G$）** | per-group 量化里每组共享一个 scale 的元素数（常用 64/128）。$G$ 越小越贴合局部分布、误差越低，但 scale 的存储开销 $\propto 1/G$ 越大，是精度与开销的旋钮。 |
| **quantization error variance $s^2/12$（量化误差方差）** | 把数四舍五入到步长 $s$ 的网格，误差近似均匀分布于 $[-s/2,s/2]$，期望 0、方差 $s^2/12$、RMSE $=s/\sqrt{12}$。据此减小 $s$（更细粒度）直接按比例减小误差，是量化误差分析的基石公式。 |
| **RMSE / relative error（均方根误差 / 相对误差）** | 量化误差的常用度量：$\text{RMSE}=\sqrt{\mathbb E[(\hat W-W)^2]}\approx s/\sqrt{12}$；相对误差再除以 $\Vert W\Vert $。本课在真实 GPT-2 权重张量上实测这两个量来对比各种粒度与位宽。 |
| **int4 packing（int4 打包）** | int4 只 16 个值，两个 int4 塞进一字节：$\text{byte}=(q_{\text{hi}}\ll4)\,\vert\,q_{\text{lo}}$，解包 $q_{\text{hi}}=\text{byte}\gg4$、$q_{\text{lo}}=\text{byte}\,\&\,\text{0xF}$。显存降到 fp16 的 1/4，是 4-bit 推理省显存的物理手段。 |
| **GPTQ** | 误差感知的逐列量化：每量化一列就用二阶（Hessian）信息调整剩余未量化列以补偿引入的误差，最小化整体输出误差。int4 下保精度的主力方法，几分钟即可量化大模型（Frantar 2023）。 |
| **AWQ（Activation-aware Weight Quantization）** | 观察到少数「被大激活乘」的权重通道对输出影响最大，对它们做保护性缩放再量化，使量化更不伤要害通道（Lin 2023）。无需反传、对指令模型友好。 |
| **outlier features（离群特征）** | LLM 激活中数值极端的少数维度（可达常规值百倍）。它们会撑大 per-tensor 的 $s$、毁掉其余值的精度，是大模型量化的头号敌人；模型越大越普遍（Dettmers 2022）。 |
| **LLM.int8() mixed-precision decomposition（混合精度分解）** | 把含离群维度的那一小部分留 fp16、其余 99% 走 int8 矩阵乘，再合并结果。让 175B 级模型几乎无损地 int8 推理，代价是少量 fp16 计算（Dettmers 2022）。 |
| **QLoRA / NF4** | QLoRA 用 4-bit NormalFloat（NF4，按正态分布最优分配量化级、外加 double quantization）冻结量化基座、只训 LoRA 适配器，使单卡微调 65B 模型成为可能（Dettmers 2023）。 |
| **SmoothQuant** | 把激活的量化难度「平滑」地按通道搬一部分到权重上（等价缩放对调），让激活与权重都易于 int8 量化。专治激活离群值导致的激活难量化问题（Xiao/Zhang 2023）。 |
| **calibration（校准）** | 用少量代表性数据跑前向、统计激活/权重的数值范围，据此定 scale/zero-point。是 GPTQ/AWQ/SmoothQuant 等 post-training 量化的必经步骤，校准集分布偏了量化就会失真。 |
| **weight / activation / KV quantization（权重/激活/KV 量化）** | 三类可量化对象，难度递增：权重量化最易（分布良性）、激活量化受离群值困扰、KV cache 量化对长上下文显存最关键（呼应模块 06）。生产中常先量化权重，再视情况碰激活与 KV。 |

---

## 06 · 推理服务

| 术语 | 释义 |
|------|------|
| **prefill（预填充）** | 推理第一阶段：把整个 prompt 一次并行喂入，做大矩阵乘、填好 KV cache。算术强度高、compute-bound，优化重点是算力利用率。它决定首 token 延迟（TTFT），prompt 越长越贵。 |
| **decode（解码）** | 推理第二阶段：逐 token 自回归生成，每步只算 1 个 token（矩阵×向量）。算术强度极低、memory-bound，主要时间在搬权重与 KV，是推理慢且贵的根源；batching 主要救的就是它。 |
| **KV cache** | 缓存历史 token 的 K、V，使每步只需算新 token 的 K/V 并追加，把每步 K/V 计算从 $O(S)$ 降到 $O(1)$。代价是显存——它随 batch 和序列长线性增长，长上下文时能超过模型权重本身。 |
| **KV cache bytes（KV 显存公式）** | 每序列 KV 字节数 $=2\cdot L\cdot S\cdot h\cdot b$（2=K 和 V，$L$ 层，$S$ 长度，$h$ 隐藏维，$b$ 字节/数）。乘上 batch 就是总 KV 显存；GQA/MQA 通过缩小有效 $h$ 直接砍这个量。 |
| **MHA（Multi-Head Attention）** | 标准多头注意力：每个 query 头配独立的 K/V 头。表达力强但 KV cache 最大（每个头都要缓存），是 GQA/MQA 要优化的基线。 |
| **GQA（Grouped-Query Attention）** | 让若干 query 头共享一组 K/V 头，把 KV cache 缩小数倍（缩小因子 = 组数），几乎不掉精度。LLaMA-2/3 等现代模型的标配，是质量与 KV 显存的最佳折中（Ainslie 2023）。 |
| **MQA（Multi-Query Attention）** | GQA 的极端版：所有 query 头共享同一组 K/V，KV cache 最小（缩小 = 头数倍），但可能略损质量。GQA 介于 MHA 与 MQA 之间。 |
| **MLA（Multi-head Latent Attention）** | DeepSeek 提出的注意力变体：把 K/V 压成低秩潜向量缓存、用时再投影回来，KV cache 比 GQA 更小且质量不降。是 KV 显存优化的较新前沿。 |
| **continuous batching（连续批处理）** | 一个序列生成完就立刻把它的槽位让给新请求、不等整批结束。把 memory-bound 的解码「搬一次权重服务多序列」，吞吐大幅提升，是 vLLM/TGI 的核心调度（又名 in-flight batching）。 |
| **static batching（静态批处理）** | 凑齐一批一起跑、要等批内最慢的请求结束才换下一批，造成大量空等（短请求陪长请求干等）。continuous batching 正是为治它而生。 |
| **PagedAttention** | 像操作系统分页一样以小块（page）管理 KV cache，消除碎片、让 KV 显存利用率接近 100%，并支持序列间共享前缀。是 vLLM 高吞吐的关键（Kwon 2023）。 |
| **prefix caching（前缀缓存）** | 复用多个请求共享的相同 prompt 前缀（如统一 system prompt）的 KV，避免重复 prefill。配合 PagedAttention 的块共享，省下大量重复计算与显存。 |
| **speculative decoding（投机解码）** | 用小 draft 模型自回归猜 $k$ 个 token，大 target 模型一次并行验证，逐个接受、第一个不一致处用 target 分布重采样。输出分布与直接用 target 完全一致（无损），把 memory-bound 解码的多步并行化（Leviathan 2023）。 |
| **draft / target model（草稿 / 目标模型）** | 投机解码的两个模型：draft 小而快、负责串行猜测；target 大而准、负责一次前向并行验证多个位置。draft 越像 target，接受率越高、加速越大。 |
| **acceptance rate（接受率 $\alpha$）** | target 接受 draft 猜测的概率。它越高、投机解码越划算；决定整个方法的加速比，是评估 draft 模型好坏的核心指标。 |
| **expected acceptance length（期望接受长度）** | 一轮投机里被接受的 token 期望数，随 $\alpha$ 与猜测步数 $k$ 增长（几何级数 $\approx\frac{1-\alpha^{k+1}}{1-\alpha}$）。它直接乘进加速比公式，是把 $\alpha$ 换算成实际收益的桥梁。 |
| **chunked prefill（分块预填充）** | 把长 prompt 的 prefill 切成小块、与 decode 步混合调度，平衡两阶段对硬件的占用、避免长 prefill 阻塞所有解码，提升整体利用率与尾延迟。 |
| **disaggregation（预填充-解码分离）** | 把 compute-bound 的 prefill 与 memory-bound 的 decode 放到不同机器/资源池各自吃满硬件，是大规模推理服务的前沿调度思路。 |
| **throughput vs latency（吞吐 vs 延迟）** | 吞吐 = 单位时间总 token 数（关乎成本/单价），延迟 = 单请求响应快慢。batching 提吞吐但可能增延迟，服务化要在两者间按 SLA 取舍——这是推理系统设计的根本张力。 |
| **TTFT / TPOT** | Time To First Token（首 token 延迟，主要由 prefill 决定）/ Time Per Output Token（每后续 token 时延，由 decode 决定）。是推理服务的两个核心延迟指标，分别对应两个阶段。 |

---

## 07 · 成本估算

| 术语 | 释义 |
|------|------|
| **6ND** | 训练总 FLOPs 的万能公式 $\approx 6\cdot N\cdot D$（$N$ 参数、$D$ token）。来由：前向每参数每 token ≈ 2 FLOPs（一次乘一次加），反向 ≈ 2 倍前向 = 4，合计 6。它把「训练一个模型要多少算力」一行算出，是所有成本账的引擎。 |
| **training FLOPs（训练总算力）** | 一次完整预训练消耗的浮点运算总数 $=6ND$（不计重计算）。除以「峰值 × MFU」得训练秒数，再换算卡时与美元。Chinchilla 的全部讨论都建立在固定这个量上。 |
| **inference FLOPs（推理 FLOPs，$2N$/token）** | 推理一次前向每 token 约 $2N$ FLOPs（只有前向、无反向）。常与训练的 $6ND$ 混淆——一个是每 token、一个是整个训练过程，务必分清；服务大量请求时这块累计可超过训练成本。 |
| **MFU（Model FLOPs Utilization）** | 实际有效（模型）算力 $/$ 硬件峰值算力。真实大模型训练通常 30%–55%，受通信、内存、kernel 效率拖累。没有 MFU 的时间/成本估算等于没算——它是把理论 FLOPs 折成真实墙钟的关键折扣。 |
| **HFU（Hardware FLOPs Utilization）** | 把重计算等冗余也计入分子的利用率，故 HFU ≥ MFU。报告时要讲清用的是哪一个，否则数字不可比；开了重计算的训练 HFU 会明显高于 MFU。 |
| **Chinchilla compute-optimal（计算最优）** | 给定算力 $C=6ND$ 使 loss 最低的 $N,D$ 分配：两者应同比例增长，最优约 $D\approx20N$（每参数 ~20 token）（Hoffmann 2022）。它推翻了 Kaplan 偏向「多给参数」的早期结论。 |
| **D ≈ 20N** | Chinchilla 的经验最优配比。据此 70B 模型应训 ~1.4T token；GPT-3（175B/300B token）按此看严重训练不足（应配 ~3.5T token），这正是「同算力下 Chinchilla 击败 Gopher」的原因。 |
| **Kaplan scaling laws（Kaplan 缩放律）** | Kaplan 2020 最早系统拟合 loss 随 $N$、$D$、$C$ 的幂律 $L\approx L_\infty + (N_c/N)^{\alpha_N}$ 等。早期结论偏向把算力多给参数，后被 Chinchilla 在数据配比上修正（因学习率调度等细节差异）。 |
| **scaling exponent（缩放指数）** | 幂律 $L\propto X^{-\alpha}$ 里的 $\alpha$，刻画 loss 随规模下降的速度。Chinchilla 拟合出 $N$ 与 $D$ 的指数接近相等，正是「两者应同比例增长」的数学依据。 |
| **compute budget（算力预算 $C$）** | 一次训练投入的总 FLOPs $=6ND$。scaling law 的核心问题就是给定 $C$ 怎么切分 $N$ 与 $D$ 使 loss 最低——这是「先有多少卡时，再决定训多大模型、喂多少数据」的现实约束。 |
| **GPU-hours / 卡时** | 训练消耗的「GPU 数 × 小时数」，是算力的工程计价单位。成本 $=G\cdot T_{\text{hr}}\cdot$ 单价/卡时，也可写成 $\frac{6ND}{\text{峰值}\cdot\text{MFU}}\cdot\frac{\text{单价}}{3600}$，与卡数无关（更多卡只是更快、总卡时不变）。 |
| **over-training / inference-aware scaling（过度训练 / 推理感知缩放）** | 训练 token 远超 Chinchilla 最优（如 LLaMA-3 训 15T token）。单看训练算力非最优，但换来更小、推理更省的模型——当推理成本主导（要服务海量请求）时，把推理也计入目标的「推理感知缩放」会主动选更小更久训的模型（Sardana 2023）。 |
| **data wall（数据墙）** | 高质量公开 token 用尽后，继续扩 $D$ 难以为继的瓶颈。多 epoch 重复数据边际收益递减、不如加参数或合成数据（Muennighoff 2023），它正在改写「数据无限」的隐含假设。 |
| **failure restart（失败重启）** | 大规模长训练中节点故障、loss 爆炸等导致的回滚重跑。它与数据预处理、调参试错一起，使真实账常是「理论训练」的数倍——估算时要留这笔 overhead。 |

---

## 常用数值速查

> 面试现场口算与做账时直接抄，记住量级比记小数点更重要。

| 量 | 数值 | 备注 |
|------|------|------|
| **A100 bf16/fp16 峰值算力** | ~312 TFLOP/s | Tensor Core；fp32 约 19.5 TFLOP/s |
| **H100 (SXM) bf16 峰值算力** | ~990 TFLOP/s | fp8 约 1979 TFLOP/s（带稀疏更高） |
| **A100 HBM 带宽** | ~2.0 TB/s | 80GB HBM2e（40GB 版 ~1.6 TB/s） |
| **H100 HBM 带宽** | ~3.35 TB/s | 80GB HBM3 |
| **A100 ridge point** | ~156 FLOP/byte | $312\text{T}/2\text{T}$，算术强度低于它即 memory-bound |
| **训练显存** | 16 bytes/param | 混合精度 Adam（不含激活）；7B≈112GB |
| **训练总算力** | $6ND$ FLOPs | $N$ 参数、$D$ token |
| **推理算力** | $2N$ FLOPs/token | 仅前向 |
| **Chinchilla 配比** | $D\approx20N$ | 每参数约 20 token |
| **KV cache/token** | $2Lh\cdot b$ bytes | 7B 类（$L{=}32,h{=}4096$，fp16）≈ 0.5 MB/token |
| **典型训练 MFU** | 30%–55% | 大规模分布式训练实测区间 |
| **fp16 动态范围** | ~$6\times10^{\pm4}$ | 故需 loss scaling |
| **bf16 / fp32 动态范围** | ~$10^{\pm38}$ | 同指数位（8 位），故 bf16 通常免 loss scaling |
| **量化 RMSE** | $\approx s/\sqrt{12}$ | 步长 $s$ 的舍入误差，$s^2/12$ 方差 |
