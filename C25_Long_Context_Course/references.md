# 参考清单 · References（长上下文与高效注意力）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每条技术，都能在下列文献里找到完整方法与真实规模的实验。

## 位置编码与外推 · Positional Encoding & Extrapolation
- ★ **Su et al. 2021, _RoFormer: Enhanced Transformer with Rotary Position Embedding_（RoPE）** — 旋转位置编码的原始论文，给出「按维度成对旋转、点积只依赖相对位置」的构造。是当今主流 LLM 的位置编码标配，也是本课模块 01 一切外推讨论的起点。基础推导亦见本系列 C20。
- ★ **Chen et al. 2023, _Extending Context Window of Large Language Models via Position Interpolation_（PI）** — 位置插值的奠基工作。发现直接外推 RoPE 会因「没见过的大旋转角」而崩，提出把位置等比压回训练范围，仅需极少微调即可把 LLaMA 上下文从 2k 扩到 32k。模块 01 的第一种缩放。
- ★ **Peng et al. 2023, _YaRN: Efficient Context Window Extension of Large Language Models_** — 当前外推效果最好的方法之一。在 NTK-by-parts 分频段插值之外，引入注意力温度补偿插值带来的熵变化。本课模块 01 的核心，完整实现其 ramp 与温度。
- **bloc97 2023, _NTK-Aware Scaled RoPE_（社区帖 + 后续 dynamic NTK）** — NTK-aware 与 NTK-by-parts 的来源。提出「放大 base 让高频几乎不动、只插值低频」，无需微调即可外推。模块 01 的第二种缩放；dynamic 版是众多开源实现的默认。
- **Press et al. 2021, _Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation_（ALiBi）** — RoPE 之外的另一条外推路线：不加位置编码，给 logits 按距离加线性惩罚。外推性好、实现极简，理解它有助于看清「相对位置偏置」这一类方法的共性。
- **kaiokendev 2023, _SuperHOT / linear RoPE scaling_（社区）** — 把 PI 推广到实践的早期社区工作，催化了开源社区的长上下文热潮，是理解 PI→NTK→YaRN 演进脉络的一环。

## 高效精确注意力 · Efficient Exact Attention
- ★ **Dao et al. 2022, _FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness_** — 本课模块 02 的主线。对 K/V 分块 + online softmax，永不 materialize n×n 分数矩阵，显存 O(n²)→O(n)、HBM 访问 O(n²d²/M)，且是精确注意力。让长上下文在显存上首次可行。必读。内核级实现见本系列 C36。
- ★ **Dao 2023, _FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning_** — FA-1 的工程化重写：query 放外层、减少非矩阵乘运算、改进 warp 间任务划分，约再快 2×。读它理解「同一算法，工程化能再压一倍」。本课 numpy 实现采用其循环结构。
- **Shah et al. 2024, _FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision_** — 面向 Hopper 的异步拷贝（TMA）、warp 专门化、FP8。展示在前沿硬件上把「算」与「搬」重叠到极致的样子。
- ★ **Milakov & Gimelshein 2018, _Online normalizer calculation for softmax_** — online softmax 的原始论文。证明可一遍流式维护 max 与归一化和，把三遍 softmax 压成一遍。这是 FlashAttention 在线 softmax 的直接前身，模块 02/04 的数学核心。
- **Rabe & Staats 2021, _Self-attention Does Not Need O(n²) Memory_** — 与 FlashAttention 并行的洞察：用在线累加把注意力显存降到 O(1)/O(log n)。理解「分块在线 softmax」的另一条独立推导。
- **Dao et al. 2023+, _Flash-Decoding for long-context inference_（博客/实现）** — 解码阶段沿 KV 切分并合并 online softmax 状态，解决长上下文「单 query、超长 KV」的并行度问题。模块 02 练习「合并两段状态」的现实对应，接 C24 推理服务。

## 稀疏与局部注意力 · Sparse & Local Attention
- ★ **Beltagy, Peters & Cohan 2020, _Longformer: The Long-Document Transformer_** — 滑窗（局部）+ 任务相关全局 token 的组合，线性复杂度处理长文档，开创局部-全局稀疏范式。模块 03 的局部+全局模式来源。
- ★ **Zaheer et al. 2020, _Big Bird: Transformers for Longer Sequences_** — 滑窗 + 全局 + 随机三种连接的组合，理论上图灵完备且能近似全注意力，块稀疏实现。理解稀疏注意力「需要哪些连接才不丢表达力」的代表作。
- ★ **Xiao et al. 2023, _Efficient Streaming Language Models with Attention Sinks_（StreamingLLM）** — 发现「注意力汇聚点（attention sink）」现象：丢掉最前面几个 token 会让滑窗推理崩溃。保留 sink + 滑窗即可处理「无限长」流式输入。模块 03 必读，sink 实验直接复现它。
- **Child et al. 2019, _Generating Long Sequences with Sparse Transformers_** — 最早系统化稀疏注意力（跨步 + 局部）的工作，把生成式 Transformer 推到上万长度。dilated/strided 模式的源头。
- **Jiang et al. 2023, _Mistral 7B_（滑窗注意力 SWA 的工业落地）** — 把滑窗注意力用进强开源模型，展示「局部 + 多层感受野扩张」在真实模型上的有效性。模块 03 滑窗多层感受野的现实对应。
- **Kitaev et al. 2020, _Reformer: The Efficient Transformer_** — 用局部敏感哈希（LSH）把注意力近似成对相近 token 的稀疏计算。理解「数据相关稀疏」（按内容而非固定模式选连接）的一条路线。

## 线性注意力与状态空间模型 · Linear Attention & SSM
- ★ **Katharopoulos et al. 2020, _Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention_** — 线性注意力奠基。用特征映射 φ + 矩阵乘结合律把注意力降到 O(n)，并指出因果版等价于一个线性 RNN（固定大小状态递推）。模块 04 的主线。
- **Choromanski et al. 2020, _Rethinking Attention with Performers_（FAVOR+）** — 用正随机特征无偏逼近 softmax 核，给线性注意力更好的特征映射。理解「φ 的质量决定线性注意力逼近好坏」的关键。
- ★ **Gu, Goel & Ré 2021, _Efficiently Modeling Long Sequences with Structured State Spaces (S4)_** — 用结构化 SSM（HiPPO + 对角低秩）高效建模超长依赖，可并行训练、可递推推理。注意力之外的长序列主流路线奠基作。
- ★ **Gu & Dao 2023, _Mamba: Linear-Time Sequence Modeling with Selective State Spaces_** — 让 SSM 参数随输入变化（选择性），弥补线性模型内容寻址弱点，配硬件感知的选择性扫描，性能可与 Transformer 媲美。模块 04 的前沿落点。
- **Yang et al. 2023, _Gated Linear Attention (GLA)_ / Sun et al. 2023, _RetNet_** — 给线性注意力加门控/衰减，并用分块并行扫描兼得 O(n) 与硬件并行度。理解现代线性模型如何缩小与 Transformer 的差距。
- **Dao & Gu 2024, _Transformers are SSMs (Mamba-2)_** — 揭示线性注意力与 SSM 的对偶（structured state space duality），把两条线统一起来。读它把模块 04 的两半（线性注意力、SSM）连成一个框架。

## KV cache 与压缩 · KV Cache & Compression
- ★ **Zhang et al. 2023, _H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models_** — 观察到少数 heavy-hitter token 贡献大部分注意力，据累积注意力分数保留它们 + 最近窗口、淘汰其余，小缓存下维持性能。模块 05 的 eviction 主线，直接复现其打分。
- ★ **Li et al. 2024, _SnapKV: LLM Knows What You are Looking for Before Generation_** — 用 prompt 末尾观察窗的注意力预测哪些 prompt token 重要，prefill 后一次性压缩 KV，对长 prompt 检索尤其有效。模块 05 的另一种 eviction 思路。
- **Liu et al. 2024, _KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache_** — 对 K 按通道、对 V 按 token 的非对称低比特量化，几乎无损地把 KV 压到 2bit。模块 05 KV 量化的代表方案，解释「为什么 K、V 要不同对待」。
- **Ainslie et al. 2023, _GQA: Training Generalized Multi-Query Transformer Models_** — 让多个 query 头共享少数 KV 头，结构性地把 KV cache 缩小数倍，是工业界最常用的 KV 压缩。背景见 C20，本课作为压缩谱系的一端。
- **Kwon et al. 2023, _Efficient Memory Management for LLM Serving with PagedAttention_（vLLM）** — 像 OS 分页一样管理 KV cache，消碎片、支持共享，是长上下文高吞吐服务的基础设施。把模块 05 的压缩接到真实服务系统。

## 长上下文评测 · Long-Context Evaluation
- ★ **Kamradt 2023, _Needle In A Haystack_（开源评测）** — 把一句「针」埋进长文、按深度 × 长度扫描检索成功率，画出直观的「有效上下文」热力图。模块 05 的 NIAH 任务直接复现它。是所有长上下文模型的第一道体检。
- ★ **Hsieh et al. 2024, _RULER: What's the Real Context Size of Your Long-Context Language Models?_** — 合成基准，含多针检索、变量追踪（多跳）、聚合等 13 类任务、按长度分档，揭示许多模型「宣称的窗口」远大于「有效窗口」。模块 05 多跳任务的来源，长上下文评测的当前标杆。
- ★ **Liu et al. 2023, _Lost in the Middle: How Language Models Use Long Contexts_** — 发现模型对上下文开头/结尾检索好、中间差的 U 形曲线。是「能看长 ≠ 看得见」最有名的证据，提醒评测必须扫描信息位置而非只测平均。
- **An et al. 2023, _L-Eval_ / Bai et al. 2023, _LongBench_** — 更贴近真实任务（长文摘要、问答、代码）的长上下文基准。与合成的 NIAH/RULER 互补：合成基准定位能力边界，真实基准衡量实用价值。
- **Zhang et al. 2024, _∞Bench (InfiniteBench)_** — 面向 100k+ 超长上下文的基准，把评测推到百万级，检验最前沿模型的极限。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境纯 CPU/numpy**：全课用 numpy 在 CPU 上**从零实现**每条技术（PI/NTK/YaRN 三种缩放、分块 FlashAttention 前向、滑窗/sink/block-sparse 掩码、线性注意力 O(n) 递推、H2O 淘汰、NIAH/RULER 任务构造），每个都与朴素参考**对拍**（如 flash == 朴素注意力到 `atol=1e-10`、线性递推 == 二次形式）。玩具规模、看懂机制为先。
- **四条正交杠杆**：①位置外推（01）让模型「敢看」长位置；②IO 高效注意力（02）让长 prefill「算得起」；③稀疏/线性（03/04）把二次复杂度降为次二次/线性；④KV 压缩（05）让长解码「存得下」。再用⑤评测（05）检验「看长」是否等于「看见」。
- **课程衔接**：上游接 C20（RoPE/GQA/MLA 等现代架构基础——本课不重复 RoPE 推导，直接用于讲外推）、C36（FlashAttention 的 GPU 内核实现——本课讲它在长上下文中的系统角色与 IO 账，不重复内核细节）；下游接 C24（推理服务 / PagedAttention / FlashDecoding）。本课聚焦的维度始终是「**长**」。
