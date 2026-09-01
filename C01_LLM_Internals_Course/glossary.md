# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读论文遇到生词回这里查。

## 分词 · Tokenization

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Tokenization | 分词 | 把原始文本切成模型可处理的离散单元（token）的过程。 |
| BPE (Byte-Pair Encoding) | 字节对编码 | 反复把语料中最高频的相邻 pair 合并成新 token 的分词算法，GPT 系的标准做法。 |
| Merge Rule | 合并规则 | BPE 训练学到的 "(a, b) → ab" 规则表，编码时按学习顺序依次应用。 |
| Byte-level BPE | 字节级 BPE | 以 256 个字节为初始词表的 BPE，任何 Unicode 文本都能编码、永无 OOV。 |
| Vocabulary | 词表 | token 与整数 id 的映射表，大小是模型的超参数（如 GPT-2 的 50257）。 |
| OOV (Out-of-Vocabulary) | 未登录词 | 词表里没有的词；byte-level 方案从根本上消除了这个问题。 |
| Special Token | 特殊标记 | 词表里有特定功能的 token，如 `<\|endoftext\|>` 标记文档边界。 |

## 注意力与架构 · Attention & Architecture

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Self-Attention | 自注意力 | 序列中每个位置对所有位置加权汇聚信息的机制，Transformer 的核心。 |
| Q / K / V (Query, Key, Value) | 查询/键/值 | 注意力的三组线性投影：用 Q·K 算相关度，再加权求和 V。 |
| Scaled Dot-Product | 缩放点积 | 注意力分数除以 √d_k 防止 softmax 饱和、梯度消失。 |
| Causal Mask | 因果掩码 | 把"未来位置"的注意力分数设为 −∞，保证每个 token 只能看见左边。 |
| Multi-Head Attention (MHA) | 多头注意力 | 把注意力拆成多个低维子空间并行计算再拼接，让不同头关注不同模式。 |
| Pre-LN | 前置层归一化 | 把 LayerNorm 放在子层之前（GPT-2 起的主流），训练比 Post-LN 稳定。 |
| Residual Connection | 残差连接 | 子层输出加回输入 x + f(x)，让梯度有"高速公路"可走。 |
| Residual Stream | 残差流 | 把残差连接串起来的那条主干向量通道，可解释性研究的核心视角。 |
| FFN / MLP Block | 前馈网络 | Transformer block 中先升维再降维的两层全连接，存储大部分"知识"。 |
| Embedding | 嵌入 | 把 token id 映射为连续向量的查表层。 |
| Positional Encoding | 位置编码 | 给序列注入位置信息的机制（学习式、正弦式或 RoPE）。 |
| Weight Tying | 权重绑定 | 输入 embedding 与输出 unembedding 共享同一矩阵，省参数。 |

## 训练 · Training

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Next-Token Prediction | 下一词预测 | LLM 的预训练目标：给定前文，预测下一个 token 的分布。 |
| Cross-Entropy Loss | 交叉熵损失 | 衡量预测分布与真实 token 差距的损失函数，语言建模的标准目标。 |
| Perplexity | 困惑度 | exp(平均交叉熵)，直觉是"模型每步平均在几个候选里犹豫"。 |
| AdamW | —— | 把 weight decay 从梯度更新中解耦出来的 Adam 变体，LLM 训练标配。 |
| Learning Rate Warmup | 学习率预热 | 训练初期把学习率从 0 线性升到峰值，避免早期大梯度震荡。 |
| Cosine Decay | 余弦衰减 | warmup 后按余弦曲线把学习率降到底的调度策略。 |
| Gradient Clipping | 梯度裁剪 | 把梯度范数限制在阈值内（如 1.0），防止梯度爆炸毁掉训练。 |
| Batch Size / Context Length | 批大小/上下文长度 | 每步样本数与每条序列的 token 数，二者乘积决定每步消耗的数据量。 |
| Overfitting | 过拟合 | 训练损失下降但验证损失回升，模型在背语料而非学规律。 |

## 解码 · Decoding

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Greedy Decoding | 贪心解码 | 每步取概率最高的 token，确定性但容易重复、僵硬。 |
| Temperature | 温度 | 对 logits 除以 T 再 softmax：T<1 更尖锐保守，T>1 更平坦随机。 |
| Top-k Sampling | top-k 采样 | 只在概率最高的 k 个 token 里重新归一化后采样。 |
| Top-p / Nucleus Sampling | 核采样 | 取累积概率刚超过 p 的最小 token 集合采样，候选集大小随分布自适应。 |
| Beam Search | 束搜索 | 同时维护 k 条最优前缀路径的搜索式解码，翻译常用、开放生成少用。 |
| Repetition Penalty | 重复惩罚 | 对已出现过的 token 降低 logit，缓解复读机现象。 |
| Speculative Decoding | 投机解码 | 用小模型快速起草多个 token、大模型一次并行验证，无损加速生成。 |
| Logits | —— | 模型输出的未归一化分数向量，softmax 之前的那一层。 |

## 规模法则 · Scaling Laws

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Scaling Law | 规模法则 | 损失随参数量/数据量/算力按幂律平滑下降的经验规律。 |
| Power Law | 幂律 | L = a·N^(−b) + c 形式的关系，log-log 坐标下是一条直线。 |
| Chinchilla | —— | DeepMind 2022 的结论：固定算力下参数与数据应同比例扩，约 20 tokens/参数。 |
| Compute-Optimal | 算力最优 | 给定 FLOPs 预算下，使最终损失最低的模型大小与数据量配比。 |
| Iso-FLOP Curve | 等算力曲线 | 固定总 FLOPs、变化模型大小画出的损失曲线，谷底即最优配比。 |
| Irreducible Loss | 不可约损失 | 幂律公式中的常数项 c，代表数据本身的熵、再大的模型也消不掉。 |
| Emergent Ability | 涌现能力 | 小模型上接近零、过某规模后突然出现的能力（度量方式仍有争议）。 |

## 推理与高效化 · Inference & Efficiency

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| KV Cache | KV 缓存 | 缓存历史 token 的 K/V 矩阵，使每步生成只需算新 token，复杂度从 O(n²) 降到 O(n)。 |
| Prefill / Decode | 预填充/解码 | 推理的两阶段：prefill 并行吃完 prompt（算力密集），decode 逐 token 生成（带宽密集）。 |
| Memory-Bound | 带宽受限 | 速度瓶颈在显存读写而非计算，decode 阶段的典型状态。 |
| Quantization | 量化 | 用更低精度（int8/int4）存权重或激活，省内存、提吞吐。 |
| FlashAttention | —— | 用分块计算 + 在线 softmax 避免写出 n×n 注意力矩阵的精确加速算法。 |
| PagedAttention | 分页注意力 | vLLM 提出，借鉴操作系统分页管理 KV cache，消除显存碎片。 |
| Continuous Batching | 连续批处理 | 推理服务中请求随到随插入 batch，不等整批结束，大幅提高吞吐。 |
| Throughput / Latency | 吞吐/延迟 | 推理服务的两大指标：单位时间总 token 数 vs 单请求响应时间。 |

## 现代架构 · Modern Architectures

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| RoPE (Rotary Position Embedding) | 旋转位置编码 | 把 Q/K 向量按位置旋转一个角度来编码相对位置，Llama 系标配。 |
| MQA (Multi-Query Attention) | 多查询注意力 | 所有 Q 头共享一组 K/V，KV cache 缩小数十倍但可能掉点。 |
| GQA (Grouped-Query Attention) | 分组查询注意力 | MHA 与 MQA 的折中：若干 Q 头共享一组 K/V，Llama-2/3 采用。 |
| MoE (Mixture-of-Experts) | 专家混合 | FFN 换成多个专家、每个 token 只激活少数几个，参数扩大算力不变。 |
| Router | 路由器 | MoE 中决定每个 token 送给哪些专家的小网络（通常 top-2 门控）。 |
| Load Balancing Loss | 负载均衡损失 | 防止 router 把所有 token 都送给少数专家的辅助损失。 |
| RMSNorm | 均方根归一化 | 去掉均值中心化、只按 RMS 缩放的简化 LayerNorm，更快且效果相当。 |
| SwiGLU | —— | 带 Swish 门控的 GLU 前馈层，现代 LLM 中替代 ReLU/GELU FFN 的主流选择。 |
| SSM (State Space Model) | 状态空间模型 | 用递推状态替代注意力的序列架构（如 Mamba），推理 O(1) 显存每步。 |
| Mamba / Selective SSM | —— | 让 SSM 参数依赖输入（选择性），使其具备内容感知能力的代表工作。 |
