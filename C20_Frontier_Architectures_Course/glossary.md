# 术语词典 · Glossary（现代模型架构）

> 按主题分组，每条 2–3 句释义。读论文遇到生词回这里查；英文术语保留原文（社区通用语言）。

## 位置编码 · Positional Encoding

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Absolute Positional Encoding | 绝对位置编码 | 给每个位置一个固定（正弦）或可学习的向量，加到 token embedding 上。简单，但相对位置关系要靠模型自己从绝对值里推，且难外推到训练未见的长度。 |
| Relative Positional Encoding | 相对位置编码 | 让 attention 分数显式依赖 query 与 key 的相对距离 m−n，而非各自的绝对位置。更符合语言的平移不变性，外推更友好。 |
| RoPE (Rotary Positional Embedding) | 旋转位置编码 | 把 q/k 向量按位置 m 旋转一个角度，使内积 ⟨q_m,k_n⟩ 只依赖相对距离 m−n。无需额外参数、可外推、与线性注意力兼容，是 Llama/PaLM/Qwen 的标配。 |
| rotate_half | 半旋转 | RoPE 的高效实现技巧：把向量后半段取负搬到前面，配合预计算的 cos/sin 即可用逐元素乘加实现旋转，避免显式构造旋转矩阵。 |
| Rotation Frequency θ_i | 旋转频率 | RoPE 第 i 对维度的角速度 θ_i = base^(−2i/d)。低维高频（短波长，编码近距离）、高维低频（长波长，编码远距离），形成多尺度的"相对位置时钟"。 |
| base / θ_base | 频率基 | RoPE 频率公式里的底数（常用 10000；长上下文模型常调到 500000+）。base 越大、波长越长、可表示的最大相对距离越远，是长上下文外推的关键旋钮。 |
| Position Interpolation (PI) | 位置插值 | 把超长序列的位置坐标线性压缩回训练长度区间再算 RoPE，用少量微调换取长上下文能力。简单但高频信息被压缩。 |
| NTK-aware Scaling | NTK 感知缩放 | 不均匀地放大 RoPE 的 base：高频几乎不动、低频拉长，兼顾局部分辨率与远程覆盖。YaRN 在此基础上进一步分频段处理（详见 C25）。 |
| Long-range Decay | 远程衰减 | RoPE 的一个性质：随相对距离增大，被旋转向量对的内积期望趋于衰减，天然给远处 token 较低的注意力先验。 |

## 注意力变体 · Attention Variants

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MHA (Multi-Head Attention) | 多头注意力 | 原版 Transformer 注意力：h 个独立的 (Q,K,V) 头各自算注意力再拼接。表达力强，但推理时每个头都要缓存自己的 K/V，KV cache 随头数线性增长。 |
| KV Cache | KV 缓存 | 自回归解码时缓存历史 token 的 K/V，避免每步重算。它是长序列推理的显存与带宽瓶颈，几乎所有注意力变体都在压它。 |
| MQA (Multi-Query Attention) | 多查询注意力 | 所有 query 头共享同一组 K/V。KV cache 缩小 h 倍，解码大幅提速，但质量略降、训练易不稳。 |
| GQA (Grouped-Query Attention) | 分组查询注意力 | MHA 与 MQA 的折中：把 query 头分成 g 组，每组共享一份 K/V。Llama-2/3 用它在质量与 KV 开销间取平衡。 |
| MLA (Multi-head Latent Attention) | 多头潜在注意力 | DeepSeek 提出：把 K/V 压成一个低秩潜向量缓存，用时再投影回多头。KV cache 比 GQA 还小，且配合解耦 RoPE 维持位置信息，质量接近 MHA。 |
| Attention Sink | 注意力汇 | 模型倾向于把大量注意力分给序列最前面的少数 token（常是 BOS）。流式推理（StreamingLLM）保留这些 sink token 才能稳定。 |

## 稀疏与前馈 · MoE & FFN

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MoE (Mixture of Experts) | 专家混合 | 用一个路由器为每个 token 选 top-k 个专家 FFN 激活，其余不算。把"参数量"与"每 token 计算量"解耦：总参数巨大，激活参数很小（Mixtral、DeepSeek-V3）。 |
| Router / Gating | 路由 / 门控 | 决定每个 token 走哪些专家的小网络（通常一层 linear + softmax）。路由质量直接决定 MoE 好坏；不可微的 top-k 选择带来训练难题。 |
| Top-k Routing | top-k 路由 | 每个 token 只激活打分最高的 k 个专家（常 k=1 或 2）。k 越大质量越好但越贵。 |
| Load Balancing Loss | 负载均衡损失 | 惩罚专家使用不均的辅助损失，防止"少数专家被挤爆、多数闲置"的路由坍塌。Switch Transformer 的关键 trick。 |
| Expert Capacity | 专家容量 | 每个专家每批最多处理的 token 数。超出就 drop（token dropping）或溢出到下个专家，是吞吐与质量的工程权衡。 |
| SwiGLU | —— | 门控线性单元的一种：FFN(x)=（Swish(xW)⊙(xV)）W₂。比 ReLU/GELU FFN 在等参数下更强，是 Llama/PaLM 的默认前馈层。 |
| GLU (Gated Linear Unit) | 门控线性单元 | 用一条"门"分支逐元素调制另一条分支的输出，让 FFN 具备乘性交互。SwiGLU/GeGLU 都是其变体。 |

## 归一化与稳定性 · Normalization & Stability

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| LayerNorm | 层归一化 | 对每个 token 的特征做减均值除标准差再仿射。Transformer 的标准归一化，但减均值与 bias 带来少量开销。 |
| RMSNorm | 均方根归一化 | 去掉 LayerNorm 的减均值与 bias，只用均方根缩放。计算更省、效果相当，是现代 LLM 的主流选择。 |
| Pre-LN / Post-LN | 前置 / 后置归一化 | 归一化放在残差子层之前(Pre)还是之后(Post)。Pre-LN 训练稳定、易扩深，几乎所有大模型都用；Post-LN 表达力略强但需 warmup 与小心调参。 |
| QK-Norm | QK 归一化 | 对 Q、K 在算注意力前各做一次归一化，抑制 attention logit 爆炸，是大规模训练稳定性的常用手段。 |
| z-loss | —— | 惩罚 softmax 归一化项 log Z 过大的辅助损失，防止 logit 漂移、提升数值稳定性（PaLM 使用）。 |
| Residual Stream Growth | 残差流增长 | 每层都往残差流里加东西，其范数随深度累积增长，可能导致后期层的相对贡献被淹没或数值不稳，需要归一化与初始化配合控制。 |

## 序列模型新范式 · State Space Models

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| SSM (State Space Model) | 状态空间模型 | 用线性递推 h_t=Āh_{t−1}+B̄x_t、y_t=Ch_t 建模序列。可写成卷积（训练并行）也可写成递推（推理 O(1) 状态），是注意力的线性时间替代。 |
| HiPPO | —— | 一套把历史压成多项式系数的最优记忆理论，给出 SSM 状态矩阵 A 的初始化，使其擅长记忆长程依赖，是 S4/Mamba 的理论根。 |
| S4 (Structured State Space) | 结构化状态空间 | 用结构化（对角+低秩）A 矩阵让 SSM 可高效计算的里程碑模型，首次在长程基准 LRA 上大幅超越 Transformer。 |
| Selective SSM / Mamba | 选择性 SSM | Mamba 让 SSM 的 B、C、Δ 随输入变化（input-dependent），获得类似注意力的"内容选择"能力；配合硬件感知的并行扫描实现线性时间高吞吐。 |
| Parallel Scan | 并行扫描 | 把串行递推用结合律重排成 O(log T) 深度的并行前缀运算，是 SSM/Mamba 在 GPU 上训练并行化的关键算法。 |
| Discretization (Δ) | 离散化步长 | 把连续时间 SSM 的 (A,B) 按步长 Δ 离散成 (Ā,B̄)（如 zero-order hold）。Δ 控制"记忆多久"，在 Mamba 里随输入自适应。 |


## 补充术语 · 实现与外推细节

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Interleaved vs Half-rotated RoPE | 交错式/半旋转 RoPE | RoPE 两种等价实现：交错式对相邻维度对 (2i,2i+1) 旋转；半旋转（GPT-NeoX/Llama）把维度劈成前后两半、用 rotate_half。数值等价但权重排布不同，迁移权重时要对齐约定。 |
| Length Generalization | 长度泛化 | 模型在比训练更长的序列上仍能工作的能力。RoPE 的外推（PI/NTK/YaRN）是其中一条路线，但长度泛化还涉及注意力熵、sink 等更广因素。 |
| Sliding Window Attention | 滑动窗口注意力 | 每个 token 只关注最近 w 个 token，把注意力复杂度降为 O(T·w)。Mistral 等用它处理长上下文，常与全局 sink 配合。 |
| Decoupled RoPE | 解耦 RoPE | MLA 中把 K 拆成“可压缩的内容部分（不加 RoPE）”与“专门承载位置的部分（加 RoPE）”，使低秩 KV 压缩与相对位置编码两不耽误。 |
| Matrix Absorption | 矩阵吸收 | MLA 推理优化：把上投影矩阵预先“吸收”进 Q 投影与输出投影，使推理时无需显式展开 K/V，进一步省算力。 |
| Router z-loss | 路由 z-loss | 对 MoE 路由 logits 的 log-sum-exp 加惩罚，稳住路由数值、防止 logits 漂移，与负载均衡损失互补。 |
| Shared Expert | 共享专家 | DeepSeekMoE 中所有 token 都会经过的专家，承载通用知识，让其余路由专家专注差异化技能。 |
| Fine-grained Expert | 细粒度专家 | 把每个专家切得更小、同时增多专家数与激活数，提升专家组合的表达力（DeepSeekMoE）。 |
| Expert Parallelism (EP) | 专家并行 | 把不同专家放到不同设备，路由后用 all-to-all 把 token 发到对应专家所在卡。MoE 分布式训练/推理的核心通信模式（见 C8/C39）。 |
| Capacity Factor | 容量因子 | 决定每个专家每批容量 C=cf·(tokens/N) 的系数。>1 留缓冲少丢 token，越大越占显存/算力。 |
| DeepNorm | —— | 一种残差缩放 + 初始化方案，让 Post-LN 也能稳定堆到上千层。 |
| LayerScale | 层缩放 | 给每个残差子层输出乘一个可学习的小初值向量，温和控制其写入残差流的幅度，稳定深网训练。 |
| Sandwich Norm | 三明治归一化 | 在子层前后各加一次归一化（Pre+Post 夹心），进一步抑制激活漂移，部分大模型采用。 |
| HiPPO Matrix | HiPPO 矩阵 | 由 HiPPO 理论给出的特定 A 初始化，使 SSM 状态成为历史的最优多项式压缩，赋予长程记忆能力。 |
| Selective Copy | 选择性复制 | 一类合成任务：要求模型按内容（而非位置）选择性地记住/复制输入。LTI SSM 做不好，Mamba 的选择性专为此设计。 |
| Associative Scan | 结合性扫描 | 利用运算的结合律把串行前缀计算并行成 O(log T) 深度的算法，是 Mamba 时变递推并行化的基础。 |
| Mamba-2 / SSD | —— | 状态空间对偶框架，证明（masked）注意力与 SSM 可统一表述，并用矩阵乘法实现以吃满 GPU 张量核。 |
| Chunked Scan | 分块扫描 | 把长序列切块，块内并行、块间传递状态，兼顾并行度与内存，是 SSM/线性注意力的常用工程技巧。 |


## 补充术语 · 推理与权衡

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Arithmetic Intensity | 算术强度 | 每从显存读入一字节数据所执行的浮点运算次数。解码阶段算术强度低（KV 读入量与计算量同阶），故受显存带宽而非算力限制——这是所有 KV 压缩技术的根本动机。 |
| Prefill vs Decode | 预填充 vs 解码 | 推理两阶段：prefill 一次性并行处理整段 prompt（算力受限），decode 逐 token 生成（带宽受限）。注意力变体主要优化 decode（见 C24）。 |
| KV Cache Quantization | KV 缓存量化 | 把缓存的 K/V 存成 int8/fp8 进一步省显存带宽，与 GQA/MLA 正交叠加（见 C27）。 |
| Grouped vs Multi-Query | 分组/多查询 | 同一谱系上的两端：MQA 是 g=1 的极端 GQA。工程上 g 是质量↔显存的连续旋钮。 |
| Token Dropping | 令牌丢弃 | MoE 中超出专家容量的 token 跳过该层专家、只走残差。容量因子决定丢弃率，是吞吐与质量的权衡。 |
| Swish / SiLU | —— | 激活函数 z·σ(z)，平滑、非单调，是 SwiGLU 的门控分支用的非线性。 |
| Logit Soft-cap | logit 软上限 | 用 tanh 把注意力或输出 logits 压到有界区间（Gemma-2），另一种数值稳定手段，与 z-loss/QK-Norm 同族。 |


## 补充术语 · 数学与推导工具

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Permutation Equivariance | 置换等变 | 自注意力的固有性质：打乱输入顺序，输出只相应被打乱。它看不见顺序，正是必须注入位置编码的根本原因。 |
| Translation Invariance | 平移不变 | 注意力分数理想上应只依赖 query 与 key 的相对距离 m−n，而非绝对位置；RoPE 用旋转精确实现这一点。 |
| Zero-Order Hold (ZOH) | 零阶保持 | 把连续时间系统按步长 Δ 离散化的标准方法（假设输入在一步内恒定），给出 SSM 的 ā=exp(Δa)、b̄=(exp(Δa)−1)/a·b。配合 a<0 天然保证离散系统稳定（ā 落在 (0,1)）。 |
| Linear Time-Invariant (LTI) | 线性时不变 | 参数不随时间/输入变化的线性系统。LTI 的 SSM 才能写成卷积；Mamba 打破 LTI（时变）以获得选择性，代价是失去卷积形式、必须改用并行扫描。 |
| Associativity | 结合律 | 运算满足 (a∘b)∘c = a∘(b∘c)。一阶线性递推的“段变换”复合满足结合律，是并行扫描能把串行递推降到 O(log T) 深度的数学前提，对时变递推同样成立（故 Mamba 仍可并行）。 |
| Riemann–Lebesgue（黎曼–勒贝格） | —— | 一条分析学引理：函数与高频振荡相乘后积分趋于零。它解释了 RoPE 的远程衰减——不同频率项在远距离上相位错乱、相互抵消，使期望内积随距离衰减。 |
| Numerical Gradient Check | 数值梯度校验 | 用有限差分 (f(x+ε)−f(x−ε))/(2ε) 核对解析梯度，模块 04 用它确认 RMSNorm 反向公式正确，是实现层归一化类算子的标准自检。 |
| Low-Rank Factorization | 低秩分解 | 把大矩阵近似成两个瘦长矩阵之积。MLA 用它把 KV 压成低秩潜向量缓存；SVD 截断给出最优低秩近似（模块 02 练习 3）。 |
| Monte Carlo Estimate | 蒙特卡洛估计 | 用大量随机样本的平均逼近期望。模块 01 用它画 RoPE 的远程衰减曲线（对随机 q/k 求内积期望随距离的变化）。 |

## 补充术语 · 推理服务与系统

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Batching | 批处理 | 把多个请求的计算摊到同一次权重读取上，提高算术强度、把带宽受限的解码往算力受限推，是提升推理吞吐的核心手段（见 C24）。 |
| PagedAttention | 分页注意力 | vLLM 提出：像操作系统管理虚拟内存一样分页管理 KV cache，消除碎片、提升并发，是“压 KV”之外的另一条正交优化线（见 C24）。 |
| Memory-bound vs Compute-bound | 带宽受限/算力受限 | 一个 kernel 的瓶颈在搬数据还是在算。解码是带宽受限（故压 KV 有效），训练/prefill 偏算力受限（故压 FLOPs 有效）。 |
| Hardware-aware Implementation | 硬件感知实现 | 把中间结果保持在 GPU 片上 SRAM、减少 HBM 读写的实现策略。FlashAttention 与 Mamba 的扫描都靠它，把“理论可并行”变成“实际跑得快”。 |
