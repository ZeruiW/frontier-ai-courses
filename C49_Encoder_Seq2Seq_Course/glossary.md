# 术语词典 · Glossary（编码器与 Seq2Seq 模型家族）

> 按主题分组，每条 2–3 句释义。读 BERT / RoBERTa / T5 / BART 论文或 `transformers` 文档遇到生词回这里查；
> 英文术语保留原文。本课用纯 numpy 复现这些机制，但术语与真实模型一一对应。

## 三种形态与注意力 · Architectures & Attention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| encoder-only | 仅编码器 | 用全 1（双向）注意力掩码，每个位置能看到序列全部位置。代表：BERT/RoBERTa/DeBERTa。表示最强，但**无法自回归生成**。 |
| decoder-only | 仅解码器 | 用下三角（因果）掩码，位置 t 只看 ≤t。代表：GPT/LLaMA。可自回归生成，训练与推理形式统一，预训练数据无限。 |
| encoder-decoder | 编码-解码 | 编码器双向 + 解码器因果 + 交叉注意力。代表：原始 Transformer/T5/BART。**Transformer 最初就是这个形态**，另两种是后来的裁剪。 |
| prefix-LM | 前缀语言模型 | 前缀内部双向、后缀因果的混合掩码（UniLM/GLM）。是 encoder-only 与 decoder-only 之间的连续插值，参数只有一套。 |
| bidirectional attention | 双向注意力 | 每个位置可注意所有位置。它使「预测下一个 token」退化成抄答案——这是 MLM 存在的根本原因。 |
| causal mask | 因果掩码 | 下三角掩码，保证 `∂out[t]/∂in[t+k]=0 (k>0)`。可用数值梯度直接验证（本课模块 00 就这么做）。 |
| cross-attention | 交叉注意力 | Q 来自解码器、K/V 来自**编码器输出**的注意力，矩阵形状是 (输出长, 输入长)。近似**词对齐**；其 K/V 只算一次可缓存。 |
| KV cache | KV 缓存 | 解码时缓存已算过的 K/V 避免重算。enc-dec 的 cross-KV 是固定的（算一次），self-KV 随生成增长；decoder-only 则全部随序列增长。 |

## 预训练目标 · Pretraining Objectives

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MLM (masked language modeling) | 掩码语言建模 | 挖掉 15% 的 token 让模型据双向上下文恢复。源自语言学的 cloze test（Taylor 1953）。信号密度只有 0.15×，是它的核心代价。 |
| cloze test | 完形填空 | MLM 的智识来源，心理学/语言学用了七十年的阅读理解测试形式。 |
| 80/10/10 | 80/10/10 策略 | 被选中的 15% 位置：80% 换 `[MASK]`、10% 换随机词、10% 保持原样。**是个补丁**，补的是「`[MASK]` 在下游从不出现」这个分布不匹配。 |
| pretrain-finetune mismatch | 预训练-微调不匹配 | 预训练输入里有 `[MASK]`，下游一次都没有。会让模型学到「只在看到 `[MASK]` 时才建模上下文」的偷懒策略。 |
| NSP (next sentence prediction) | 下一句预测 | BERT 的第二个目标：判断句 B 是否紧跟句 A。**后被推翻**——负例来自不同文档，可被「主题匹配」捷径攻破。 |
| SOP (sentence order prediction) | 句序预测 | ALBERT 的替代：正例 A→B，负例 B→A（**同一对句子换顺序**）。主题相同，堵死了主题捷径，被证明比 NSP 有效。 |
| dynamic masking | 动态掩码 | RoBERTa：每个 epoch 重新采样掩码位置，而非预处理时固定。等于免费的数据增强。 |
| RTD (replaced token detection) | 替换 token 检测 | ELECTRA 的目标：小生成器替换部分 token，判别器对**每个位置**判断是否被替换。信号密度 1.0×，且输入无 `[MASK]`。 |
| span corruption | 片段破坏 | T5 的目标：连续片段整体换成一个哨兵 token，解码器只生成被挖内容。**目标序列短约 5 倍**，是 T5 的效率关键。 |
| sentinel token | 哨兵 token | T5 的 `<extra_id_0>`…`<extra_id_99>`，标记「这里挖了第几段」。不指示长度，所以任务不平凡。 |
| denoising autoencoder | 去噪自编码器 | BART 的范式：多种噪声破坏原文，模型重建**完整**原文。与 T5 的「只输出被挖内容」形成对照。 |
| text infilling | 文本填充 | BART 五种噪声中最有效的一项：连续片段换成**单个** mask（长度未知，可为 0）。同时训练恢复内容、判断长度、保持流畅。 |
| signal density | 信号密度 | 每次前向产生多少个训练预测。CLM/RTD 是 1.0×，MLM 只有 0.15×。但要乘上**每次信号的信息量**才是公平比较（MLM 每次 ~15 bit，RTD 只有 1 bit）。 |
| pseudo-perplexity | 伪困惑度 | MLM 的近似困惑度：逐位置掩掉一个 token 用其余上下文预测。**不可与 CLM 的困惑度直接比较**——MLM 的条件分布族互不相容，不存在对应的联合分布。 |

## 模型与改进 · Models & Improvements

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| BERT | BERT | 2018 年的双向编码器：MLM + NSP、WordPiece 30k、学习式绝对位置（**512 硬上限**）、post-LN。今天它的架构已明显过时。 |
| RoBERTa | RoBERTa | **零架构改动**、只重调配方（去 NSP、动态掩码、10× 数据、8k batch、更长训练）即提升 7 分。证明 BERT 严重欠训练。 |
| ELECTRA | ELECTRA | 用 RTD 替代 MLM，算力效率约 4×。生成器要「小」（1/4~1/2）是难度匹配；**不是 GAN**（无对抗梯度）；λ=50 让判别器拿到主要梯度。 |
| DeBERTa | DeBERTa | 解耦注意力（内容→内容、内容→位置、位置→内容三项）+ 相对位置 + EMD。v3 结合 RTD，至今是编码器任务的最强基线之一。 |
| disentangled attention | 解耦注意力 | 把 BERT 中纠缠的「内容+位置」注意力显式拆成三项分别计算。代价约 3× 注意力分数计算，且与 FlashAttention 等标准 kernel 不兼容。 |
| ALBERT | ALBERT | 嵌入分解 + 跨层参数共享 + SOP。**参数少 89% 但 FLOPs 一点不省**——层数没减。持久贡献是 SOP 与「参数量≠效率」这个澄清。 |
| T5 | T5 | 「万物皆文本」：所有任务转成文本到文本，靠任务前缀区分。思想被指令微调与 prompt 范式完全继承。代价是分类/回归失去输出空间约束。 |
| BART | BART | 去噪自编码的 enc-dec；解码器起始 token 用 `</s>` 而非 `<s>`（历史遗留，自己实现易踩坑）。 |
| relative position encoding | 相对位置编码 | 位置项只依赖 `i-j` 而非绝对位置。带来平移不变与小位置表（`2*max_rel+1` 行 vs BERT 的 512 行），也带来长度外推能力。 |

## 下游任务与解码 · Downstream & Decoding

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| sequence classification | 序列分类 | 用 `[CLS]` 或池化向量接一个 C 类 softmax。**要微调用 [CLS]，不微调抽向量用 mean pooling**。 |
| token classification | token 分类 | 每个位置一个标签（NER/POS）。输出空间有**语法约束**，必须做约束解码。 |
| BIO / IOB2 | BIO 标注 | `B-X` 实体开始、`I-X` 实体内部、`O` 非实体。合法性约束：`O→I-X` 非法、`B-PER→I-LOC` 非法。 |
| Viterbi decoding | 维特比解码 | `O(n·K²)` 动态规划求最优合法标签路径。相比一次前向的 1e10 FLOPs 完全可忽略——**零成本的正确性保证**。 |
| CRF layer | 条件随机场层 | 在 Viterbi 基础上把转移分数也变成可学参数。在强预训练模型上增益已明显缩小，但**约束解码本身仍必要**。 |
| entity-level F1 | 实体级 F1 | 按完整实体匹配算 F1（seqeval）。**token 级 F1 会系统性高估**——边界错一个 token，该实体就完全没抽对。 |
| span extraction | span 抽取 | 两个位置分类器给出 start/end logits。必须**联合搜索**（`end≥start`、限长度、限上下文区），否则会产出无效答案。 |
| EM / exact match | 精确匹配 | QA 指标。**必须先归一化**（小写、去标点、去冠词、压空格），否则低估 5-10 个点。 |
| MCC | 马修斯相关系数 | 综合混淆矩阵四格的指标，对类别不平衡鲁棒。GLUE 的 CoLA 用它。可以出现 accuracy 95% 而 MCC 0.00 的情况。 |
| discriminative fine-tuning | 判别式学习率 | 底层学习率更小（逐层 ×0.95）。底层学的是通用特征，改动它们收益小、破坏大。 |
| catastrophic forgetting | 灾难性遗忘 | 学习率过大时，几个 batch 就把预训练知识冲掉。这是微调学习率要比从头训练小 100 倍的原因。 |
| teacher forcing | 教师强制 | 训练时把**真实**目标右移一位喂给解码器，使所有位置并行计算（1 次前向 vs 推理的 m 次）。 |
| exposure bias | 暴露偏差 | 训练时喂真实前缀、推理时喂自己生成的前缀，导致错误累积。RLHF 的 on-policy 采样在解决同一个古老问题。 |
| beam search | 束搜索 | 每步保留 beam 条最优部分序列。分数需**长度归一化**（GNMT 的 `lp(t)=((5+t)/6)^α`），否则系统性偏好短输出。 |
| beam search curse | beam 诅咒 | beam 超过 5–10 后质量反而下降——更大的 beam 更接近真正的最大似然序列，而 MLE 模型的众数往往是退化的（过短/套话）。 |

## 训练与实现细节 · Training & Implementation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| WordPiece | WordPiece 分词 | BERT 的子词切分，未登录词切成 `##` 前缀的片段。30k 词表。RoBERTa 改用 byte-level BPE（无 UNK、跨语言更鲁棒）。 |
| whole word masking | 整词掩码 | 要掩就把一个词的**所有子词**一起掩掉。只掩一个子词会让任务退化成拼写补全（看到 `un` 和 `##able` 就能猜出中间）。实测有稳定提升。 |
| shallow vs deep bidirectional | 浅层 vs 深层双向 | ELMo 是两个独立单向 LSTM 最后拼接（浅层）；BERT 是**每一层的每个位置**都同时注意左右（深层）。这是 BERT 大幅超越 ELMo 的主要来源之一。 |
| warmup | 学习率预热 | 前若干步线性升到峰值 lr。Transformer 训练初期极不稳定（LayerNorm 与残差的相互作用），没有 warmup 常直接发散。 |
| two-stage sequence length | 两阶段序列长度 | BERT：90% 步数用 128 长度、10% 用 512。注意力是 O(L²)，这一招省约 84% 的注意力计算，同时让长位置嵌入得到训练。 |
| `[CLS]` / `[SEP]` | 特殊 token | `[CLS]` 是序列首位的汇总占位符，`[SEP]` 分隔句对与标记结束。`[CLS]` 的表示能力**完全来自有目标在训练它**。 |
| segment embedding | 片段嵌入 | 标记 token 属于句 A 还是句 B。为 NSP 服务；去掉 NSP 后很多模型简化掉了它。 |
| learned position embedding | 学习式位置嵌入 | 每个位置一个可学向量。**512 是物理硬上限**（索引越界，不是效果变差），且无法外推。被相对位置编码与 RoPE 取代。 |
| label smoothing | 标签平滑 | 把 one-hot 目标改成 `(1-ε)` 与均匀分布的混合。原始 Transformer 用 ε=0.1；能提升 BLEU 但会让困惑度变差。 |
| off-by-one (decoder shift) | 解码器错位 | teacher forcing 时 decoder 输入必须是目标**右移一位**。写错则每个位置的输入就是它要预测的目标，loss 迅速趋零但推理全是垃圾。 |
| seed variance | 种子方差 | 小数据集上仅换随机种子，微调分数可波动 2–3 分，甚至训崩。「涨了 1 分」通常需要十几个种子才站得住（Dodge et al. 2020）。 |
| linear probing | 线性探针 | 冻结主干、只训一个线性头。用来度量**表示质量**（而非预训练 loss）——低 loss ≠ 好表示。 |

## 蒸馏与检索 · Distillation & Retrieval

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| knowledge distillation | 知识蒸馏 | 用 teacher 的**完整概率分布**（软标签）训练 student，携带类间相似结构（dark knowledge），信息量远超 one-hot。 |
| temperature (T) | 温度 | `softmax(logits/T)`，T 越大分布越平滑、暴露越多类间结构。典型 2–5。 |
| T² scaling | T² 缩放 | 软标签梯度按 `1/T²` 衰减，必须乘 `T²` 补回。**忘了它，T=4 时蒸馏项梯度只剩 1/16，等于没做蒸馏**。 |
| data distillation | 数据蒸馏 | 用 teacher 在无标注数据上打标签，当普通监督数据训 student。**跨架构唯一可行的路**（LLM→encoder 的 logit 空间根本对不上）。 |
| DistilBERT | DistilBERT | 同架构 logit 蒸馏的标准配方：6 层、小 40%、快 60%、保留约 97% 的 GLUE 性能。 |
| bi-encoder | 双塔编码 | 查询与文档**分别**编码成向量，点积打分。**在线成本与语料规模无关**（文档向量离线预计算）——这是它不可替代的原因。 |
| cross-encoder | 交叉编码 | 查询与文档拼接后一起编码。精度最高但无法预计算，N 个候选就要 N 次前向。 |
| two-stage retrieval | 两阶段检索 | 双塔召回 top-k + 交叉编码精排。最优 k 在 recall 曲线拐点（通常 50–200）。是成本-精度前沿上的正确取点。 |
| anisotropy | 各向异性 | BERT 句向量挤在狭窄锥体里，任意两句余弦相似度都在 0.7+，失去区分度。缓解：白化、对比学习。 |
| InfoNCE | InfoNCE 损失 | 对比学习的标准损失：拉近正例对、推远负例。`τ`（温度）控制难度。 |
| hard negatives | 困难负例 | 用当前模型检索出的、排名靠前但实际不相关的样本。随机负例太容易区分，学不到细粒度。**负例设计决定学到什么**——这是 NSP/SOP/对比学习三次体现的同一条原理。 |
| SBERT / SimCSE | 句嵌入训练 | SBERT 用有监督 NLI 数据、SimCSE 用 dropout 作数据增强做对比学习，把 BERT 变成可用的句嵌入模型。 |
