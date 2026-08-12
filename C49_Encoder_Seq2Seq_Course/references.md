# 参考清单 · References（编码器与 Seq2Seq 模型家族）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C01** 从零写 decoder-only Transformer；**C17** 讲神经网络之前的经典 NLP；
> **C20** 讲现代架构组件（RoPE/GQA/MoE/SSM）；**C21** 讲大规模预训练的数据与缩放；
> **本课**补 encoder-only 与 encoder-decoder 这两种形态及其独有的目标与任务范式；
> **C50** 讲怎么用 HuggingFace 生态把它们真正跑起来。

## 三种形态与原始架构 · Architectures
- ★ **Vaswani et al. 2017, _Attention Is All You Need_** — 原始 Transformer，**encoder-decoder** 形态。重新精读一遍会发现很多细节被后来的教程简化掉了：cross-attention 的确切定义、warmup 调度、label smoothing、以及为什么当时选了 post-LN。本课模块 04 的一手来源。
- ★ **Devlin, Chang, Lee & Toutanova 2019, _BERT: Pre-training of Deep Bidirectional Transformers_** — encoder-only 路线的开创。**重点读第 3、5 节的消融**而不是结果表：MLM 的 80/10/10 消融、NSP 的贡献、以及四种下游范式的定义都在那里。
- ★ **Radford et al. 2018/2019, _Improving Language Understanding by Generative Pre-Training_ / _Language Models are Unsupervised Multitask Learners_** — decoder-only 路线。与 BERT 对读，能清楚看到「掩码形状决定一切」这条主线。
- **Dong et al. 2019, _Unified Language Model Pre-training (UniLM)_** — prefix-LM 的代表：用一个模型、三种掩码同时训练。理解三种形态是一个连续谱而非三个孤立点。
- **Tay et al. 2022, _UL2: Unifying Language Learning Paradigms_** — 在同等算力下系统比较 enc-dec / dec-only / prefix-LM，并提出混合去噪目标。目前对「哪种形态更好」这个问题最系统的实证工作。
- **Taylor 1953, _"Cloze Procedure": A New Tool for Measuring Readability_** — MLM 的智识来源。读它你会发现 BERT 的核心想法在语言学里已经用了七十年。

## 预训练目标的改良 · Objectives
- ★ **Liu et al. 2019, _RoBERTa: A Robustly Optimized BERT Pretraining Approach_** — **本课模块 02 的核心必读**。零架构改动、只重调配方即提升 7 分。重点读消融表，它系统地拆开了每一项改动（去 NSP、动态掩码、大 batch、更多数据、更长训练）的边际贡献。这篇论文对整个领域的方法论意义超过它的技术贡献。
- ★ **Clark, Luong, Le & Manning 2020, _ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators_** — 判别式目标把信号密度从 0.15 拉回 1.0，算力效率约 4×。**特别注意读它对「这不是 GAN」的澄清**（文本离散，生成器不接收对抗梯度）以及生成器规模的消融。
- ★ **He, Liu, Gao & Chen 2021, _DeBERTa: Decoding-enhanced BERT with Disentangled Attention_** 与 **He et al. 2023, _DeBERTaV3_** — 解耦注意力的推导与 EMD 的动机；v3 把 RTD 与解耦注意力结合。DeBERTa-v3 至今是编码器任务的最强开源基线之一，做 NLU 任务的起点应该是它而不是 bert-base。
- **Lan et al. 2020, _ALBERT: A Lite BERT_** — SOP 的提出（负例设计的经典案例）与参数共享的真实收益。读它主要为了理解「参数量 ≠ 效率」这个澄清。
- **Wettig, Gao, Zhong & Chen 2023, _Should You Mask 15% in Masked Language Modeling?_** — 推翻了 15% 是普适最优这个默认假设，发现更大模型适合更高掩码率。一个很好的「早期经验值被当成定律」的例子。
- **Wang & Cho 2019, _BERT has a Mouth, and It Must Speak: BERT as a Markov Random Field Language Model_** — 把 MLM 当 MRF 用 Gibbs 采样生成。读它理解「BERT 不能生成」的准确边界：不是不能，是代价很大。

## Encoder-Decoder 与生成 · Seq2Seq
- ★ **Raffel et al. 2020, _Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (T5)_** — **第 3 节是本领域最完整的架构/目标对比实验之一**：形态、目标、破坏率、片段长度、数据集全都做了系统消融。「万物皆文本」的思想被后来的指令微调与 prompt 范式完全继承。
- ★ **Lewis et al. 2020, _BART: Denoising Sequence-to-Sequence Pre-training_** — 五种噪声的消融，结论是 text infilling 最有效。与 T5 对读能看清「重建整句 vs 只输出被挖内容」这个设计分歧。
- ★ **Ranzato, Chopra, Auli & Zaremba 2016, _Sequence Level Training with Recurrent Neural Networks_** — exposure bias 的提出与序列级训练的早期尝试。这个概念在 RLHF 时代依然重要（on-policy 采样解决的是同一个问题）。
- **Wu et al. 2016, _Google's Neural Machine Translation System (GNMT)_** — 长度惩罚公式 `lp(t)=((5+t)/6)^α` 的出处，以及大规模 NMT 的完整工程配方。
- **Koehn & Knowles 2017, _Six Challenges for Neural Machine Translation_** — **beam search 诅咒的实证来源**：beam 增大反而降低 BLEU。它揭示了训练目标（MLE）与真实目标之间的系统性错位。
- **He, Peng et al. 2021, _On Exposure Bias in Neural Machine Translation_（及相关复盘工作）** — 论证 exposure bias 的影响在强模型上可能被高估。与 Ranzato 对读，理解一个被广泛引用的概念如何被后续工作重新审视。
- **Gu et al. 2018, _Non-Autoregressive Neural Machine Translation_** — 一次性并行生成全部输出。enc-dec 天然适合 NAT（编码器已给出完整输入表示），这条线在翻译上有实用价值。

## 下游任务与评估 · Downstream & Evaluation
- ★ **Rajpurkar et al. 2016, _SQuAD_ 与 2018, _Know What You Don't Know (SQuAD 2.0)_** — span 抽取范式的定义，以及「不可回答」如何用 `[CLS]` 作为 (0,0) span 优雅地表达。评估脚本里的答案归一化是本课模块 03 的一手来源。
- ★ **Wang et al. 2019, _GLUE_ 与 _SuperGLUE_** — 多任务基准。重点看它为每个任务选择指标的理由（为什么 CoLA 用 MCC 而不是 accuracy）。
- ★ **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping_** — **做微调实验前必读**。系统研究了种子方差：小数据集上仅换种子波动 2–3 分，甚至有些种子会训崩。它让「我的方法涨了 1 分」这类结论必须重新审视。
- **Howard & Ruder 2018, _Universal Language Model Fine-tuning (ULMFiT)_** — 判别式学习率、逐层解冻、斜三角学习率的提出。虽然写在 BERT 之前，但这些技巧至今有效。
- **Lample et al. 2016, _Neural Architectures for Named Entity Recognition_** — BiLSTM-CRF 与 BIO 约束解码的经典。理解 CRF 层在做什么，以及为什么在强预训练模型上它的增益变小了。
- **Ramshaw & Marcus 1995, _Text Chunking using Transformation-Based Learning_** — IOB 标注体系的起源。

## 蒸馏、句嵌入与检索 · Distillation & Retrieval
- ★ **Hinton, Vinyals & Dean 2015, _Distilling the Knowledge in a Neural Network_** — 软标签与温度的原始推导，**注意 `T²` 因子的来源**（软标签梯度按 `1/T²` 衰减）。dark knowledge 这个概念也出自这里。
- ★ **Sanh, Debut, Chaumond & Wolf 2019, _DistilBERT_** — 同架构蒸馏的标准配方（logit + 隐状态 + cosine 三项损失）：6 层、小 40%、快 60%、保留 97% 性能。
- ★ **Reimers & Gurevych 2019, _Sentence-BERT_** — **为什么原始 BERT 的句向量不能直接用**（比 GloVe 平均还差），以及怎么用孪生网络 + NLI 数据修好它。做检索/相似度前必读。
- ★ **Gao, Yao & Chen 2021, _SimCSE: Simple Contrastive Learning of Sentence Embeddings_** — 用 dropout 作为最小数据增强做无监督对比学习，并对各向异性给出了清晰的分析（alignment 与 uniformity）。
- ★ **Karpukhin et al. 2020, _Dense Passage Retrieval (DPR)_** — 双塔检索的标准做法与 **hard negatives 的重要性**。它把「负例设计决定学到什么」这条原理第三次摆到台面上。
- **Nogueira & Cho 2019, _Passage Re-ranking with BERT_** — 交叉编码精排的开创工作，两阶段检索架构的另一半。
- **Jiao et al. 2020, _TinyBERT_** — 中间层蒸馏（隐状态 + 注意力矩阵），信号比纯 logit 蒸馏更密集，但需要处理层数与维度对齐。
- **Muennighoff et al. 2023, _MTEB: Massive Text Embedding Benchmark_** — 嵌入模型的统一评估。既是选型参考，也提醒你注意「刷榜」与真实检索效果之间的差距。

## 跨课衔接 · Cross-course
- **C01 LLM 内核** — 从零实现 decoder-only Transformer。本课的注意力实现与它是同一套，只是掩码不同。
- **C17 经典 NLP** — word2vec / n-gram / HMM / CRF。本课模块 03 的 Viterbi 与 CRF 在那门课有完整的概率图模型基础。
- **C20 现代架构** — RoPE / GQA / MLA / MoE / SSM。模块 02 末尾讲的「编码器现代化」需要的组件全在那门课。
- **C27 模型压缩** — 量化、剪枝、蒸馏的系统处理。本课模块 05 的蒸馏只讲了与 encoder 选型相关的部分。
- **C11 RAG 与检索** — 向量检索、重排、RAG 评测。本课模块 05 的双塔/交叉编码是它的模型侧基础。
- **C50 HuggingFace 生态实操** — 把本课的每个概念变成能跑的真实代码（`AutoModel`、`Trainer`、`DataCollator`、`PEFT`）。**两课配套使用效果最好**。
