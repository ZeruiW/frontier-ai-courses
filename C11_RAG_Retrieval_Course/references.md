# 参考清单 · References（检索增强与长上下文评测）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy/pandas 从零实现的每个机制，都能在下列文献里找到真实系统中的对应实现与权衡。

## RAG 框架与开放域问答 · RAG & Open-Domain QA
- ★ **Lewis et al. 2020, _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_** — RAG 的命名与奠基论文。把可微的稠密检索器与生成器端到端联合，证明「检索+生成」在知识密集任务上同时提升准确率与可溯源性。本课的总框架（模块 00/04）即源出于此，必读。
- ★ **Karpukhin et al. 2020, _Dense Passage Retrieval for Open-Domain Question Answering_ (DPR)** — 现代稠密检索的范式起点。用对比学习训练 bi-encoder，使相关 query-passage 点积高，首次系统性地大幅超过 BM25。模块 01/03 的双编码器、in-batch negatives 都来自它。
- **Guu et al. 2020, _REALM: Retrieval-Augmented Language Model Pre-Training_** — 把检索作为可学习的潜变量融入预训练，让模型学会「该检索什么」。理解检索与生成如何联合优化（而非检索器固定）的进阶读物。
- **Izacard & Grave 2021, _Leveraging Passage Retrieval with Generative Models (Fusion-in-Decoder, FiD)_** — 如何把多个检索片段高效融进生成器：各片段独立编码、在解码器融合。是把 top-k 上下文喂给 reader 的经典工程方案。
- **Gao et al. 2023, _Retrieval-Augmented Generation for Large Language Models: A Survey_** — RAG 的全景综述，梳理 naive/advanced/modular RAG、各环节（索引、检索、生成、评测）的技术谱系。建立全局地图、查后续文献的好入口。
- **Asai et al. 2023, _Self-RAG_** — 让模型自适应地决定「何时检索、检索后是否采用、答案是否被支持」，引入反思 token。是把检索从静态前置升级为动态按需的代表。

## 词法检索 · Lexical Retrieval
- ★ **Robertson & Zaragoza 2009, _The Probabilistic Relevance Framework: BM25 and Beyond_** — BM25 的权威综述与推导。讲清词频饱和、IDF、文档长度归一化的概率检索来由。本课模块 01 从零实现 BM25 的依据；理解为什么它至今是难以击败的强基线。
- **Spärck Jones 1972, _A Statistical Interpretation of Term Specificity and Its Application in Retrieval_** — IDF 思想的源头：罕见词更有区分力。信息检索的奠基文献之一，读它理解词项加权的第一性原理。
- **Robertson et al. 1994 (TREC), _Okapi at TREC-3_** — BM25 的原始提出场景。了解它如何在 TREC 评测中胜出、参数 $k_1,b$ 的经验取值由来。
- **Formal et al. 2021, _SPLADE: Sparse Lexical and Expansion Model_** — 用神经网络学习稀疏词项权重，兼得词法的可解释/精确与神经的语义扩展。是「稀疏与稠密融合」的现代答案，模块 01 混合检索的延伸。

## 向量检索与索引 · Vector Indexing
- ★ **Johnson, Douze & Jégou 2019, _Billion-scale similarity search with GPUs (FAISS)_** — 工业级向量检索库 FAISS 的系统论文。讲清 IVF、PQ、GPU 加速如何把十亿级近邻搜索做到可行。本课模块 02 的 IVF/PQ 都是它的简化教学版，必读。
- ★ **Malkov & Yashunin 2018, _Efficient and Robust Approximate Nearest Neighbor Search Using HNSW Graphs_** — HNSW 图索引的奠基论文。多层小世界图 + 贪心导航，在高召回下做到对数级查询，是当下最流行的内存 ANN。模块 02 的图导航直觉来源。
- ★ **Jégou, Douze & Schmid 2011, _Product Quantization for Nearest Neighbor Search_** — PQ 压缩的原始论文。把向量切段、各段用小码本量化，配合非对称距离查表，实现极致的内存压缩与快速近似距离。模块 02 PQ 部分的依据。
- **Guo et al. 2020, _Accelerating Large-Scale Inference with Anisotropic Vector Quantization (ScaNN)_** — Google 的向量检索库，提出对齐内积目标的量化损失，在召回-速度前沿上推进。理解量化为何要「为检索目标而设计」而非泛泛压缩。
- **Babenko & Lempitsky 2014, _The Inverted Multi-Index_** — IVF 的增强：用乘积式的多重倒排把空间划得更细。理解 IVF 如何向更大规模扩展。
- **Aumüller et al. 2020, _ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms_** — 各 ANN 算法在召回-延迟前沿上的标准化对比。选索引、读懂「召回-延迟权衡曲线」的实证依据。

## 重排与融合 · Reranking & Fusion
- ★ **Nogueira & Cho 2019, _Passage Re-ranking with BERT (monoBERT)_** — 把 BERT 当 cross-encoder 对候选逐一打分重排，大幅提升排序质量。两段式「召回+重排」范式的奠基，模块 03 的核心参考。
- ★ **Cormack, Clarke & Büttcher 2009, _Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods_** — RRF 的原始论文。证明只用名次的简单融合 $\sum 1/(k+\text{rank})$ 异常稳健，胜过需要调参的分数融合。模块 03 RRF 的依据。
- **Carbonell & Goldstein 1998, _The Use of MMR, Diversity-Based Reranking for Reordering Documents_** — MMR 的原始论文。用 $\lambda$ 平衡相关性与多样性，避免结果冗余。模块 03 多样性重排的依据。
- **Khattab & Zaharia 2020, _ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT_** — late interaction：token 级向量 + MaxSim，介于 bi- 与 cross-encoder 之间的折中。理解「精度 vs 成本」连续谱的关键一点。
- **Nogueira et al. 2020, _Document Ranking with a Pretrained Sequence-to-Sequence Model (monoT5)_** — 用 T5 生成式地做相关性判断（输出 true/false 的概率）。cross-encoder 重排的生成式变体，理解重排器的不同实现。

## RAG 评测 · RAG Evaluation
- ★ **Es et al. 2023, _RAGAS: Automated Evaluation of Retrieval Augmented Generation_** — 无参考 RAG 自动评测框架。把答案拆成论断逐条核验，给出 faithfulness/answer relevance/context precision/recall 四项分。本课模块 04 用规则版模拟其思想，必读。
- ★ **Chen et al. 2023, _Benchmarking Large Language Models in Retrieval-Augmented Generation (RGB)_** — 系统性地测 RAG 在噪声鲁棒性、负样本拒答、信息整合、反事实抵抗四种能力上的表现。理解 RAG 会以哪些方式失败、该测什么。
- **Saad-Falcon et al. 2023, _ARES: An Automated Evaluation Framework for RAG_** — 用少量人工标注 + LLM 判官构建可校准的 RAG 评测，并给出统计置信。RAGAS 的互补路线，理解自动评测如何兼顾规模与可信。
- **Manakul et al. 2023, _SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection_** — 不依赖外部知识、靠多次采样一致性检测幻觉。理解 faithfulness/幻觉检测的另一条无参考思路。
- **Honovich et al. 2022, _TRUE: Re-evaluating Factual Consistency Evaluation_** — 把忠实度/事实一致性评测统一成 NLI（蕴含）问题并系统比较各种自动指标。模块 04 用 entailment 判 faithfulness 的理论依据。

## 检索排序指标 · Ranking Metrics
- ★ **Järvelin & Kekäläinen 2002, _Cumulated Gain-Based Evaluation of IR Techniques_** — nDCG 的原始论文。提出用分级相关性 + 位置折损来评排序，并归一到 [0,1]。模块 05 nDCG 推导的依据，理解为什么要折损、为什么要归一。
- ★ **Manning, Raghavan & Schütze 2008, _Introduction to Information Retrieval_ (第 8 章 Evaluation)** — IR 评测的权威教材章节。Precision/Recall、MAP、MRR、nDCG 的定义与动机一网打尽。模块 05 的标准参考，强烈建议精读。
- **Voorhees 1999 (TREC-8 QA Track) / Craswell 2009, _Mean Reciprocal Rank / qrels_** — MRR 与 TREC 相关性标注（qrels）的来源。理解学术检索评测的实验协议与数据格式。
- **Wang et al. 2013, _A Theoretical Analysis of NDCG Ranking Measures_** — nDCG 的理论性质分析（一致性、对增益/折损函数的依赖）。想严谨理解指标性质的进阶读物。

## 长上下文评测 · Long-Context Evaluation
- ★ **Liu et al. 2023, _Lost in the Middle: How Language Models Use Long Contexts_** — 揭示位置偏置：关键信息在上下文中段时模型利用率显著下降，准确率呈 U 形。长上下文评测最重要的实证发现，模块 06 的核心，对 RAG 上下文排序有直接启示，必读。
- ★ **Kamradt 2023, _Needle In A Haystack — Pressure Testing LLMs_** — NIAH 测试的提出（开源项目/博客）。把一句事实藏进长文本、在不同长度与位置下测检索能力，成为长上下文事实检索的事实标准。模块 06 从零复现它。
- ★ **Hsieh et al. 2024, _RULER: What's the Real Context Size of Your Long-Context Language Models?_** — 在 NIAH 之上加多针、变量追踪、聚合等更难任务，揭示模型「有效上下文长度」远短于宣称值。理解「128k 不等于 128k 处仍准」的关键，模块 06 多针/有效长度的依据。
- **Dao et al. 2022, _FlashAttention_** — 让长上下文在算力上可行的底层内核（O(n²)→显存 O(n)）。理解长窗口路线为何在工程上成为可能（与本课 C36 衔接）。
- **An et al. 2023, _L-Eval_ / Bai et al. 2023, _LongBench_** — 面向真实任务（长文摘要、长文 QA、代码补全）的长上下文基准。NIAH 测合成检索能力，它们测真实长任务能力，二者互补。
- **Xu et al. 2023, _Retrieval meets Long Context Large Language Models_** — 直接对比「RAG vs 长上下文」并尝试结合：用长上下文模型 + 检索常优于单用其一。模块 06「RAG vs 长上下文权衡」的直接实证。

## 数据集与工具 · Datasets & Tooling
- **Rajpurkar et al. 2016/2018, _SQuAD / SQuAD 2.0_** — 经典抽取式 QA 数据集（问题 + 段落 + 答案跨度，2.0 含不可答问题）。本课真实数据胶囊优先联网拉取它来做检索/评测实验。
- **Kwiatkowski et al. 2019, _Natural Questions_ / Joshi et al. 2017, _TriviaQA_** — 大规模开放域 QA，DPR/RAG 的标准评测集。理解检索器与端到端 RAG 在真实问答上的评估场景。
- **Thakur et al. 2021, _BEIR: A Heterogeneous Benchmark for Zero-shot IR_** — 跨 18 个检索任务的零样本评测套件。理解检索器泛化性、稠密 vs 词法在不同领域的此消彼长。
- ⚠️ **本课的实现立场**：全程**纯 numpy/pandas、CPU 可跑**。embedding 用确定性哈希/共现构造的玩具向量（不训练神经网络），ANN/PQ/重排/评测/NIAH 全部从零实现并对拍暴力/朴素参考；真实数据（SQuAD）**优先联网下载、失败回退到内置真实样本**，保证逻辑与真实系统一致、且离线也能跑通。
- **课程衔接**：上游接 C01（Transformer/注意力）、C10（评测测量学）；底层依赖 C36（FlashAttention 让长上下文可行）；下游接智能体系列（检索作为工具/记忆）。本课聚焦**检索与评测**这一在通用课程里常被跳过的整块缺口。
