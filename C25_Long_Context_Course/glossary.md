# 术语词典 · Glossary（长上下文与高效注意力）

> 按主题分组，每条 2–3 句释义。读 YaRN / FlashAttention / StreamingLLM / Mamba / RULER 等论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用 numpy 在 CPU 上从零实现这些概念，但术语与真实长上下文系统一一对应。

## 上下文与长度 · Context & Length

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| context window / context length | 上下文窗口 / 上下文长度 | 模型一次能处理的最大 token 数。是「长上下文」一切讨论的标尺：从早期的 512/2k，到如今的 128k、1M。它由位置编码、注意力实现、KV 显存三者共同设限。 |
| long context | 长上下文 | 把上下文窗口推到远超训练长度（如训练 4k、服务 128k）的能力。它不是单一技巧，而是位置外推 + 高效注意力 + KV 压缩 + 评测的系统工程。 |
| sequence length (n / L) | 序列长度 | 当前输入的 token 数，本课记作 n 或 L。注意力的显存与算力随它分别按 O(n²) 膨胀，是所有长上下文难题的根源变量。 |
| length extrapolation | 长度外推 | 在比训练时更长的序列上推理。朴素 RoPE/绝对位置在外推时性能急剧崩塌；PI/NTK/YaRN/ALiBi 等技术就是为了让外推平稳。 |
| length generalization | 长度泛化 | 模型把在短序列上学到的能力迁移到长序列的程度。常用「困惑度随长度的曲线」或长基准（RULER）的随长度衰减来度量。 |
| effective context | 有效上下文 | 模型真正能利用的长度，往往远短于宣称的窗口。一个号称 128k 的模型可能在 32k 之后检索能力就崩了——「能看长」不等于「看得见」。 |
| prefill / prompt phase | 预填充 / 提示阶段 | 推理时一次性并行处理整段输入 prompt 的阶段。它是计算受限的、要算 n×n 注意力，长 prompt 下是 FlashAttention 的主战场。 |
| decode / generation phase | 解码 / 生成阶段 | 自回归逐 token 生成的阶段，每步只有一个新 query。它是访存受限的，瓶颈在反复读取不断增长的 KV cache。 |

## 位置编码与外推 · Positional Encoding & Extrapolation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| positional encoding | 位置编码 | 给注意力注入「token 在第几位」信息的机制（注意力本身对顺序不敏感）。分绝对（加到 embedding）与相对（作用于 query-key 交互）两大类。 |
| RoPE (Rotary Position Embedding) | 旋转位置编码 | Su et al. 2021 提出：把 query/key 按维度成对、按位置角度旋转，使点积只依赖相对位置。是当今主流 LLM 的标配，也是长上下文外推的核心战场。 |
| rotation angle / frequency | 旋转角 / 频率 | RoPE 中第 i 对维度的旋转角 = 位置 × θ_i，其中 θ_i = base^(−2i/d) 随维度指数衰减。低维转得快（高频）、高维转得慢（低频）。 |
| base / θ (theta) | 基 / 频率底数 | RoPE 频率公式里的底数（常用 10000）。改 base 会整体伸缩所有波长，是 NTK-aware scaling 的旋钮。 |
| wavelength | 波长 | 某一对维度旋转一整圈（2π）所需的位置跨度，= 2π / θ_i。高维的波长可能远超训练长度——这些维度在训练时从没转满过一圈。 |
| Position Interpolation (PI) | 位置插值 | Chen et al. 2023：把超出训练长度的位置等比例「压缩」回训练范围（位置 m → m·L_train/L_target）。简单有效，但均匀压缩高频维度会损失局部分辨率，需少量微调。 |
| NTK-aware scaling | NTK 感知缩放 | 不均匀地缩放：放大 RoPE base，使高频维度几乎不动、只对低频维度做插值。源自神经正切核视角，无需微调即可外推，但纯 NTK 在极长时仍会退化。 |
| NTK-by-parts | 分部 NTK | 把维度按波长分三段：高频（波长远短于训练长度）不插值、低频（波长超训练长度）做 PI、中间平滑过渡。是 YaRN 的频段处理来源。 |
| YaRN (Yet another RoPE extensioN) | —— | Peng et al. 2023：在 NTK-by-parts 的分频段插值之外，再乘一个 attention 温度（把 logits 缩放 1/t）补偿插值带来的注意力熵变化。当前外推效果最好的免/少微调方法之一。 |
| ramp function | 斜坡函数 | YaRN 中按维度波长在 [0,1] 之间平滑过渡的权重，决定某一维「多大程度上插值、多大程度上保留原频率」，实现高频到低频的渐变。 |
| attention temperature / scaling | 注意力温度 | YaRN 给注意力 logits 乘的标量 1/t（t>1 等价于把 √d 放大）。插值改变了 logits 的尺度与 softmax 的熵，温度把它校正回训练时的分布。 |
| ALiBi (Attention with Linear Biases) | 线性偏置注意力 | Press et al. 2021：不加位置编码，而是给注意力 logits 按 query-key 距离减去一个线性惩罚。外推性好、实现简单，是 RoPE 之外的另一条外推路线。 |
| dynamic scaling / dynamic NTK | 动态缩放 | 推理时根据当前实际序列长度动态调整缩放因子（短序列不缩放、超长才缩放），避免对短输入的无谓精度损失。许多开源实现的默认策略。 |

## 高效精确注意力 · Efficient Exact Attention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| attention | 注意力 | softmax(QKᵀ/√d)·V。朴素实现要 materialize n×n 的分数矩阵 S 与概率矩阵 P，显存与 HBM 读写都是 O(n²)，是长序列的内存墙。 |
| scaled dot-product | 缩放点积 | 注意力分数 QKᵀ 除以 √d，防止维度变大时点积方差过大把 softmax 推向饱和。 |
| FlashAttention | —— | Dao et al. 2022：对 K/V 分块、用 online softmax 增量累加输出，永不 materialize 完整 S。显存 O(n²)→O(n)、HBM 访问大降，是「IO 感知」算法设计的范例，让长上下文在显存上首次可行。 |
| online softmax | 在线 / 流式 softmax | Milakov & Gimelshein 2018：一遍流式扫描，动态维护「运行最大值 m」与「运行指数和 l」，每见更大值就用校正因子 exp(m_old−m_new) 回缩已累加量。无需先看完整行，是 FlashAttention 分块的关键。 |
| running max / running sum (m, l) | 运行最大值 / 运行和 | online softmax 流式维护的两个标量（注意力里还有运行输出累加器 O）。它们让一行的归一化可以分块增量完成。 |
| rescale / correction factor | 校正因子 | online softmax 遇到新最大值时，对已累加的 l 与 O 乘上的 exp(m_old−m_new) ∈ (0,1]，把旧的指数基准对齐到新基准。漏乘 O 是最常见的沉默 bug。 |
| IO-awareness | IO 感知 | 以「HBM 读写字节数」而非「FLOPs」为优化目标。FlashAttention 的 FLOPs 并不比朴素少（甚至略多），却快得多，因为它把 HBM IO 从 O(n²) 降到 O(n²d²/M)。 |
| IO complexity / HBM accesses | IO 复杂度 / HBM 访问量 | 一个算子进出高带宽显存（HBM）的总字节数。在访存受限的注意力上，它而非 FLOPs 才是决定速度的量，是 FlashAttention 的优化目标。 |
| tiling / blocking | 分块 | 把大计算切成小块、搬进片上 SRAM 反复复用，把对 HBM 的访问次数除以 tile 规模。FlashAttention 对 K/V 分块就是这一思想在注意力上的应用。 |
| recomputation | 重计算 | 反向传播时不保存巨大的中间矩阵（如概率 P），而用前向存下的少量统计量（LSE）即时重算。用算力换显存，是 FlashAttention 反向的关键。 |
| LogSumExp (LSE) | 对数和指数 | log Σ exp(xᵢ)，softmax 归一化项的对数，= online softmax 的 m + log l。前向只需存它（每行一个标量）即可在反向重算概率，省下 O(n²) 显存。 |
| materialize | 落盘 / 物化 | 把中间张量完整写进显存。FlashAttention 的关键是「永不 materialize n×n 的 S」，从而把显存与 IO 从 O(n²) 降到 O(n)。 |
| FlashAttention-2 / -3 | —— | FA-2（Dao 2023）把 query 放外层循环、减少非矩阵乘运算、改进任务划分，约再快 2×；FA-3（Shah 2024）用 Hopper 异步拷贝与 FP8 进一步提速。 |
| FlashDecoding | —— | 解码阶段（n_q=1）的 FlashAttention 变体：并行的不是 query 而是沿 KV 序列切段，各段算 online softmax 状态再合并。把 FlashAttention 用到生产推理的钥匙。 |

## 稀疏与局部注意力 · Sparse & Local Attention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| sparse attention | 稀疏注意力 | 只计算注意力矩阵的一个子集（每个 query 只看部分 key），把复杂度从 O(n²) 降到 O(n·k)。代价是可能漏看远处的相关 token。 |
| sliding window attention (SWA) | 滑窗注意力 | 每个 token 只注意最近的 W 个 token（局部窗口）。复杂度 O(n·W)，多层堆叠后感受野线性扩大。Mistral、Longformer 的局部部分。 |
| dilated / strided attention | 空洞 / 跨步注意力 | 在窗口内按固定间隔（dilation）跳着取 key，用同样的预算覆盖更大跨度。借鉴空洞卷积，扩大单层感受野。 |
| block-sparse attention | 块稀疏注意力 | 把序列分块，只计算选定的 (query 块, key 块) 对（如对角块 + 少量全局块）。块粒度对硬件友好（能用稠密 GEMM 算每个块），是 BigBird、稀疏 Flash 的实现基础。 |
| receptive field | 感受野 | 经过若干层后，一个位置的表示能间接汇集到的 token 范围。滑窗每层 +W，L 层后感受野 ≈ L·W——这是局部注意力仍能建模长依赖的原因。 |
| attention sink | 注意力汇聚点 | Xiao et al. 2023 的发现：序列最前面的几个 token 会吸走大量注意力（即使语义无关），充当 softmax 的「泄压阀」。丢掉它们会让滑窗推理崩溃。 |
| StreamingLLM | —— | Xiao et al. 2023：保留最前面几个 sink token + 一个滑动窗口，使模型能在不重置的情况下处理「无限长」的流式输入，困惑度保持稳定。 |
| Longformer | —— | Beltagy et al. 2020：滑窗（局部）+ 少量任务相关的全局 token（如 [CLS]）的组合，线性复杂度处理长文档，开创局部-全局稀疏范式。 |
| BigBird | —— | Zaheer et al. 2020：滑窗 + 全局 token + 随机连接三者结合，理论上是图灵完备且能近似全注意力，块稀疏实现。 |
| global token | 全局 token | 稀疏模式里被指定为「所有 token 都能看、也能看所有 token」的少数特殊位置（如分类头、问题 token），用于在局部注意力里保留一条全局信息通路。 |
| recall (sparse) | 召回率 | 稀疏注意力评估指标：被稀疏模式保留下来的注意力质量占全注意力的比例（如保留了 top-k 真实高权重连接的多少）。衡量稀疏化损失了什么。 |

## 线性注意力与状态空间模型 · Linear Attention & SSM

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| linear attention | 线性注意力 | Katharopoulos et al. 2020：用核特征映射 φ 把 softmax(QKᵀ)V 近似成 (φ(Q)·(φ(K)ᵀV))，靠矩阵乘结合律把复杂度从 O(n²d) 降到 O(n d²)，且可写成因果递推。 |
| feature map (φ) | 特征映射 | 把 query/key 映射到特征空间的函数 φ，使 φ(q)·φ(k) 近似 softmax 的指数核。常用 elu+1、正随机特征（Performer）等，质量取决于 φ 对核的逼近。 |
| kernel trick / kernelization | 核技巧 | 把 softmax 的指数相似度视作一个核 k(q,k)，再用特征映射 φ 使 k(q,k)≈φ(q)·φ(k)，从而能交换矩阵乘顺序、线性化注意力。 |
| associativity (matmul) | 矩阵乘结合律 | (φ(Q)φ(K)ᵀ)V = φ(Q)(φ(K)ᵀV)。右结合先算 d×d 的 KᵀV 再乘 Q，避开 n×n 矩阵——这是线性注意力降复杂度的全部数学。 |
| recurrent form / linear recurrence | 递推形式 / 线性递推 | 线性注意力的因果版可写成状态递推：S_t = S_{t−1} + φ(k_t)v_tᵀ，o_t = φ(q_t)·S_t。状态 S 是固定大小 d×d，与序列长度无关，故 O(n) 时间、O(1) 状态。 |
| state (S) | 状态 | 线性注意力/SSM 中固定大小的运行记忆（线性注意力是 d×d 矩阵）。它把「过去全部 token」压缩进一个有限张量，是线性复杂度的来源，也是其表达力上限。 |
| SSM (State Space Model) | 状态空间模型 | 用线性状态递推 h_t = A h_{t−1} + B x_t、y_t = C h_t 建模序列（S4、Mamba）。固定状态 → O(n) 时间、推理时 O(1) 内存，是注意力之外的长序列主流路线。 |
| S4 (Structured State Space) | 结构化状态空间 | Gu et al. 2021：用特殊结构（HiPPO 初始化、对角+低秩）的 SSM 高效建模超长依赖，可并行训练（卷积形式）、可递推推理。 |
| Mamba / selective SSM | —— | Gu & Dao 2023：让 SSM 的 A/B/C 随输入变化（选择性），使其能按内容决定记住/遗忘什么，弥补线性模型的内容寻址弱点，可与 Transformer 媲美。 |
| selective scan | 选择性扫描 | Mamba 中输入相关参数下的并行前缀扫描算法（硬件感知实现），在保持 O(n) 的同时高效训练选择性 SSM。 |
| chunked / parallel scan | 分块 / 并行扫描 | 把线性递推用结合律重排成可并行的前缀和（块内并行、块间递推），兼得递推的 O(n) 与硬件的并行度。现代线性注意力/SSM 训练的关键。 |

## KV cache 与压缩 · KV Cache & Compression

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| KV cache | 键值缓存 | 自回归解码时缓存历史 token 的 K、V，避免每步重算。显存随序列长度线性增长（2·层数·头数·d·n），长上下文解码的主要显存与带宽瓶颈。 |
| KV cache compression | KV 缓存压缩 | 通过量化、淘汰、合并等手段减小 KV cache 占用，在尽量不损精度的前提下让更长上下文/更大批量装进显存。 |
| KV quantization | KV 量化 | 把缓存的 K、V 从 FP16 降到 INT8/INT4 等低精度存储，显存按比特数成比例下降。常按通道/分组量化以控误差，K 通常比 V 更敏感。 |
| KV eviction | KV 淘汰 | 丢弃「不重要」token 的 KV 以限制缓存大小。难点是如何判定重要性而不误删后面会用到的 token——这正是 H2O/SnapKV 要解决的。 |
| H2O (Heavy-Hitter Oracle) | 重要击中预言机 | Zhang et al. 2023：观察到少数 token（heavy hitters）贡献了大部分注意力质量；据累积注意力分数保留 heavy hitters + 最近窗口，丢弃其余，在小缓存下维持性能。 |
| heavy hitter | 重要击中者 | 累积注意力分数高、被许多后续 query 反复关注的少数 token。H2O 的核心假设是它们决定了输出质量，应优先保留。 |
| SnapKV | —— | Li et al. 2024：用 prompt 末尾一段「观察窗」的注意力来预测哪些 prompt token 重要，在 prefill 后一次性压缩 KV，对长 prompt 检索任务尤其有效。 |
| KV merging | KV 合并 | 把相似或相邻 token 的 KV 合并成一个（如取平均/加权），而非直接丢弃，以在压缩的同时保留更多信息。 |
| GQA / MQA | 分组 / 多查询注意力 | 让多个 query 头共享同一组 K/V 头（MQA 共享一组、GQA 分若干组），直接把 KV cache 缩小数倍。是工业界最常用的「结构性」KV 压缩（详见 C20）。 |
| PagedAttention | 分页注意力 | vLLM 的 KV cache 管理：像操作系统分页一样把 KV 存成不连续的块，消除碎片、支持高效共享，是长上下文高吞吐服务的基础设施。 |
| compression ratio | 压缩率 | 保留的 KV 量（token 数或字节数）÷ 原始量。评估压缩方法时与「在目标任务上的精度保持」一起看，单看压缩率没有意义。 |

## 长上下文评测 · Long-Context Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| perplexity (PPL) | 困惑度 | 语言模型对文本的平均不确定性（= exp(平均负对数似然)）。常用「PPL 随长度的曲线」看外推是否崩，但 PPL 低不代表能真正利用长上下文。 |
| needle in a haystack (NIAH) | 大海捞针 | Kamradt 提出的探针测试：把一句无关的「针」（如一个随机事实）埋进很长的「干草堆」文本，问模型能否检索出来。按针的深度 × 上下文长度画热力图，直观暴露「有效上下文」边界。 |
| RULER | —— | Hsieh et al. 2024：合成的长上下文基准，含多针检索、变量追踪（多跳）、聚合、长上下文问答等 13 类任务，按长度分档，比单一 NIAH 更能区分模型的真实长上下文能力。 |
| retrieval / lost-in-the-middle | 检索 / 中间遗失 | Liu et al. 2023 的发现：模型对放在上下文开头和结尾的信息检索好、对放在中间的信息检索差，呈 U 形。是长上下文「能看长 ≠ 看得见」的典型证据。 |
| multi-hop / variable tracking | 多跳 / 变量追踪 | 需要串联多处分散信息才能作答的任务（如 A=1; B=A; C=B; 问 C）。RULER 用它考察模型在长上下文里维持并组合多条线索的能力，远难于单针检索。 |
| depth (needle depth) | 针的深度 | NIAH 中「针」插入位置占全文的相对位置（0%=开头，100%=结尾）。沿深度扫描能定位模型在上下文哪一段最容易「看丢」信息。 |
| haystack | 干草堆 | NIAH 中作为背景的长文本（常用 Paul Graham 文集等真实长文），针被埋在其中。其长度即被测的上下文长度。 |
