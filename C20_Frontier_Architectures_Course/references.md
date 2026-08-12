# 参考清单 · References（现代模型架构）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读，建立每个主题的主线；跑完对应 notebook 后再回看论文的工程细节；读完全课后，用最后的 Llama-3 / DeepSeek-V3 报告把所有组件串成一个真实模型。本课的每个模块都对应下面一个主题分区，按图索骥即可。

## 位置编码 · RoPE 与外推
- ★ **Su et al. 2021, “RoFormer: Enhanced Transformer with Rotary Position Embedding”** — RoPE 原始论文。给出旋转编码使内积只依赖相对位置的完整推导，是本课模块 01 的主线；读它就懂为何 Llama/PaLM/Qwen 全线采用。
- **Press et al. 2022, “ALiBi: Train Short, Test Long”** — 用线性偏置代替位置编码实现外推，和 RoPE 是两条外推路线的对照；理解“位置信息加在哪里”的设计空间。
- **Chen et al. 2023, “Extending Context Window via Position Interpolation (PI)”** — 把位置压回训练区间，少量微调得到长上下文；模块 01 练习 2 的来源。
- **bloc97 2023, “NTK-Aware Scaled RoPE”（社区帖）** + ★ **Peng et al. 2023, “YaRN”** — 分频段缩放 base 的外推方法，解决 PI 压缩高频的副作用；C25 长上下文课展开，模块 01 练习 3 是其雏形。
- **Black et al. 2022, “GPT-NeoX”** — rotate_half 的工程实现来源（本课 notebook 采用的半旋转约定），迁移权重时要对齐它与交错式的差别。

## 注意力变体 · KV cache 压缩
- ★ **Vaswani et al. 2017, “Attention Is All You Need”** — MHA 与 Transformer 原版，一切的起点。建议把本课所有变体都对照原版理解“改了哪一处、为何改”。
- **Shazeer 2019, “Fast Transformer Decoding: One Write-Head is All You Need”** — MQA：共享 K/V 头加速解码，KV cache 砍 h 倍的极端方案。
- ★ **Ainslie et al. 2023, “GQA: Training Generalized Multi-Query Transformer”** — GQA：分组共享，Llama-2/3/Qwen 采用；含从 MHA 模型“uptrain”成 GQA 的 5% 训练量配方，解释了 GQA 为何被迅速普及。
- ★ **DeepSeek-AI 2024, “DeepSeek-V2 / V3 Technical Report”** — MLA 低秩 KV 压缩与解耦 RoPE、矩阵吸收的工程细节，模块 02 的高级主题来源。
- **Xiao et al. 2023, “StreamingLLM / Attention Sinks”** — 注意力 sink 现象与流式推理：为何要保留最前面几个 token 才能稳定长流。

## MoE 与前馈
- ★ **Shazeer et al. 2017, “Outrageously Large Neural Networks: Sparsely-Gated MoE”** — 稀疏门控 MoE 的奠基，首次把“参数量与计算量解耦”落地。
- ★ **Fedus et al. 2021, “Switch Transformers”** — top-1 路由 + 负载均衡损失，把 MoE 做到万亿参数且稳定；模块 03 均衡损失公式的出处。
- **Jiang et al. 2024, “Mixtral of Experts”** — 开源稀疏 MoE 的代表，top-2 路由 8 专家，工程读者的标准参照。
- **Shazeer 2020, “GLU Variants Improve Transformer”** — SwiGLU/GeGLU 的对照实验，解释为何 Llama 用 SwiGLU 以及 8/3·d_model 的隐藏维约定。
- **DeepSeek-AI 2024, “DeepSeekMoE”** — 细粒度专家 + 共享专家的路由设计，以及无辅助损失的负载均衡偏置法。

## 归一化与训练稳定性
- ★ **Zhang & Sennrich 2019, “Root Mean Square Layer Normalization”** — RMSNorm 原始论文，模块 04 前向/反向公式的来源。
- **Xiong et al. 2020, “On Layer Normalization in the Transformer Architecture”** — Pre-LN vs Post-LN 的梯度分析，解释 Pre-LN 为何能去掉 warmup、堆到上百层。
- **Chowdhery et al. 2022, “PaLM”** — z-loss、稳定性工程与大规模训练经验，模块 04 z-loss 的出处。
- **Dehghani et al. 2023, “ViT-22B”** — QK-Norm 抑制 attention logit 爆炸，超大模型稳定性的标准手段。
- **Wortsman et al. 2023, “Small-scale proxies for large-scale Transformer training instabilities”** — 用小模型复现并研究大模型不稳定性（logit 增长、attention 坍塌），低成本找药方。

## 状态空间模型 · SSM / Mamba
- ★ **Gu et al. 2021, “Efficiently Modeling Long Sequences with Structured State Spaces (S4)”** — 结构化 SSM 的里程碑，首次在 LRA 长程基准大幅超越 Transformer。
- **Gu et al. 2020, “HiPPO: Recurrent Memory with Optimal Polynomial Projections”** — SSM 状态矩阵 A 初始化的理论根，赋予长程记忆。
- ★ **Gu & Dao 2023, “Mamba: Linear-Time Sequence Modeling with Selective State Spaces”** — selective SSM（时变 B/C/Δ）+ 硬件感知并行扫描，模块 05 主线。
- **Dao & Gu 2024, “Transformers are SSMs (Mamba-2 / SSD)”** — 把注意力与 SSM 统一在状态空间对偶框架下，并用矩阵乘法吃满 GPU。
- **Blelloch 1990, “Prefix Sums and Their Applications”** — 并行扫描（前缀和）算法的经典出处，模块 05 并行扫描练习的理论根。

## 延伸阅读 · 实现与综述
- **Llama 2 / Llama 3 技术报告（Meta 2023/2024）** — GQA、RMSNorm、RoPE base 调整在真实旗舰模型里的取舍，工程读者必看。
- **Qwen2 / Gemma 技术报告** — 另一组现代架构选择（含 QK-Norm、归一化位置、logit soft-cap）的对照样本。
- **Mistral 7B（Jiang et al. 2023）** — 滑动窗口注意力 + GQA 的组合，长上下文工程的简洁范例。
- **Lilian Weng, “The Transformer Family”（博客）** — 架构变体的系统综述，适合建立全景。
- **EleutherAI, “Rotary Embeddings: A Relentless Survey”（博客）** — RoPE 的实现细节与社区经验汇总（交错 vs 半旋转、base 调参）。
- **Sasha Rush et al., “The Annotated S4”** — 逐行实现 S4 的教程，理解 SSM 离散化与卷积核的最佳上手材料。
- **Albert Gu, “Mamba / SSM” 讲座与博客** — 选择性、并行扫描、硬件感知实现的一手讲解。
- **Horace He, “Making Deep Learning Go Brrrr From First Principles”（博客）** — 算术强度、带宽 vs 算力瓶颈的直觉，解释为何解码是带宽受限、KV 压缩为何重要。

## 数值 / 工程对照
- **FlashAttention（Dao 2022，见 C8/C36）** — 注意力的 IO 感知实现：把注意力融合成一个 kernel、中间结果不落 HBM，与本课的注意力变体（GQA/MLA）正交叠加。理解它能体会“硬件感知实现”这一与 Mamba 扫描相通的主题。
- **FlashAttention-2 / 3（Dao 2023/2024）** — 进一步的并行划分与 Hopper 上的异步/warp 专门化，是“算法 + 硬件协同设计”的范例，与模块 05 Mamba 的硬件感知扫描思路一致。
- **vLLM / PagedAttention（Kwon 2023，见 C24）** — KV cache 的分页管理，像操作系统管虚拟内存一样消除碎片、提升并发，是“压 KV”之外的另一条正交优化线；与 GQA/MLA 叠加使用。
- **Switch Transformer 与 GShard 的容量/通信工程** — MoE 在真实分布式训练中的吞吐、负载均衡与 all-to-all 通信工程细节，是把模块 03 单机原理放大到集群的关键读物。
- **Megatron-LM / DeepSpeed（见 C8/C39）** — 张量/流水/专家并行的工业实现，理解 MoE 的专家并行与本课其它组件在真实大模型训练栈里如何拼装。

## 课程交叉与背景
- **Kaplan 2020 / Hoffmann 2022（Scaling Laws / Chinchilla，见 C1/C8）** — 架构改良的收益最终要放进 scaling 框架里衡量；本课组件多以“等算力下更优”为卖点。
- **Gemma 2 技术报告（Google 2024）** — logit soft-cap、交替滑窗/全局注意力、GQA 的综合应用，现代架构组件的集大成样本之一。
- **RWKV / RetNet 论文** — 与 SSM 并列的“线性注意力/循环”家族，理解序列建模的统一图景；C25 长上下文课展开。
- ★ **DeepSeek-V3 技术报告（2024）** — MLA + 细粒度/共享专家 MoE + 无辅助损失负载均衡的工业级集成，几乎覆盖本课全部主题，强烈建议读完全课后通读一遍作为综合案例。

## 怎么用这份清单
1. 先读每节 ★ 标记的奠基论文，建立主线。
2. 跑完对应 notebook 后再回看论文的工程细节（容量因子、初始化、数值技巧）。
3. 最后用 Llama-3 / DeepSeek-V3 报告把所有组件串成一个真实模型，对照“它改了原版哪一处、为何改”。
