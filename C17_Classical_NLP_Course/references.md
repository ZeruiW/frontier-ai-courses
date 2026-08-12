# 参考清单 · References（经典 NLP）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个算法，都能在下列文献里找到原始推导与更完整的工程考量。

## 教材与综述 · Textbooks & Surveys
- ★ **Jurafsky & Martin, _Speech and Language Processing_ (SLP), 3rd ed. draft** — 经典 NLP 的权威教材，免费在线。n-gram 与平滑（第 3 章）、朴素贝叶斯与逻辑回归（第 4–5 章）、向量语义与 embedding（第 6 章）、HMM（附录 A）、序列标注与 CRF（第 8 章）几乎覆盖本课全部模块。**遇到任何概念分歧以它为准，强烈建议全程对照精读。**
- ★ **Manning & Schütze, _Foundations of Statistical Natural Language Processing_** — 统计 NLP 的奠基教材。共现、互信息、n-gram、HMM、文本分类的数学推导比 SLP 更细，是理解「为什么这样估计」的深水区读物。
- **Manning, Raghavan & Schütze, _Introduction to Information Retrieval_** — TF-IDF、向量空间模型、文本分类与评测（P/R/F1、宏微平均）的标准出处。模块 05 的检索/分类部分直接对标其前几章。
- **Eisenstein, _Introduction to Natural Language Processing_** — 较新的统一视角教材，把分类、序列标注、结构化预测放在同一概率框架下讲，适合在读完本课后做体系化整合。

## 词嵌入 · Word Embeddings
- ★ **Mikolov, Chen, Corrado & Dean 2013, _Efficient Estimation of Word Representations in Vector Space_** — word2vec 的开山之作，提出 CBOW 与 skip-gram 两种高效结构，并展示了著名的 king−man+woman≈queen 类比。模块 01 的 worked 实现即复现它的核心。**必读。**
- ★ **Mikolov, Sutskever, Chen, Corrado & Dean 2013, _Distributed Representations of Words and Phrases and their Compositionality_** — word2vec 的第二篇，提出**负采样**与**词频 0.75 次方的噪声分布**、子采样高频词。本课负采样的数学与超参全部源于此，是模块 01 的直接依据。**必读。**
- ★ **Pennington, Socher & Manning 2014, _GloVe: Global Vectors for Word Representation_** — 提出对全局共现计数的对数做加权最小二乘，统一了「计数派」与「预测派」词向量。读它理解为什么 $w_i\cdot w_j\approx\log X_{ij}$、加权函数为何这样设计。**必读。**
- **Levy & Goldberg 2014, _Neural Word Embedding as Implicit Matrix Factorization_** — 证明 skip-gram 负采样隐式地在分解一个移位的 PMI 矩阵，把「预测派」与「计数派」在理论上打通。读它你会对模块 01 的 PPMI+SVD 与 word2vec 的关系恍然大悟。
- **Levy, Goldberg & Dagan 2015, _Improving Distributional Similarity with Lessons Learned from Word Embeddings_** — 系统比较各类词向量方法，指出很多增益来自超参（窗口、负样本数、子采样）而非模型本身。极具工程参考价值。
- **Bojanowski et al. 2017, _Enriching Word Vectors with Subword Information_ (fastText)** — 用字符 n-gram 组合出词向量，缓解 OOV 与形态丰富语言的问题，是 word2vec 的重要延伸。

## 语言模型与平滑 · Language Models & Smoothing
- ★ **Chen & Goodman 1999, _An Empirical Study of Smoothing Techniques for Language Modeling_** — n-gram 平滑的权威实证比较，确立了 **modified Kneser-Ney** 的统治地位。想真正搞懂各种平滑的优劣与实现细节，这是最该读的一篇。
- ★ **Kneser & Ney 1995, _Improved Backing-off for M-gram Language Modeling_** — Kneser-Ney 平滑原始论文，提出用**续延概率**（一个词跟在多少种不同词后）取代低阶词频。模块 02 的 KN 实现即复现其思想。**必读。**
- **Katz 1987, _Estimation of Probabilities from Sparse Data for the Language Model Component of a Speech Recognizer_** — Katz backoff 的出处，把 Good-Turing 折扣与回退结合并保证归一。理解回退机制的经典文献。
- **Good 1953, _The Population Frequencies of Species and the Estimation of Population Parameters_** — Good-Turing 估计的源头（出自生态学！），用「频次的频次」重估未见事件概率。模块 02 Good-Turing 部分的理论根基。
- **Bengio et al. 2003, _A Neural Probabilistic Language Model_** — 第一个成功的神经语言模型，用词向量＋前馈网络缓解 n-gram 的稀疏与维度灾难。它是从经典 n-gram 通往现代 LM 的桥梁，读它理解模块 02 与现代的衔接。

## 隐马尔可夫模型 · HMM
- ★ **Rabiner 1989, _A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition_** — HMM 的传奇教程，把三大问题（评估/解码/学习）、前向-后向、Viterbi、Baum-Welch 讲得无比清晰。模块 03 的结构与符号完全对标它，**是 HMM 唯一必读文献。**
- **Viterbi 1967, _Error Bounds for Convolutional Codes and an Asymptotically Optimum Decoding Algorithm_** — Viterbi 算法的原始论文（出自通信编码！），动态规划求最可能路径。理解解码问题的源头。
- **Baum et al. 1970, _A Maximization Technique Occurring in the Statistical Analysis of Probabilistic Functions of Markov Chains_** — Baum-Welch（EM 的特例）原始论文。模块 03 无监督学习部分的依据。
- **Church 1988, _A Stochastic Parts Program and Noun Phrase Parser for Unrestricted Text_** — 把 HMM 用于词性标注的早期经典，确立了统计 POS 标注的范式。

## CRF 与结构化预测 · CRF & Structured Prediction
- ★ **Lafferty, McCallum & Pereira 2001, _Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data_** — CRF 的开山之作，指出 HMM/MEMM 的不足（标签偏置 label bias），提出在整条序列上全局归一的判别式模型。模块 04 的理论核心，**必读。**
- ★ **Collins 2002, _Discriminative Training Methods for Hidden Markov Models: Theory and Experiments with Perceptron Algorithms_** — 结构化感知机原始论文，用 Viterbi＋感知机更新做序列学习，不需算配分函数却很有效。模块 04 的 worked 实现即复现它，是理解 CRF 训练的最佳起点。**必读。**
- **Sutton & McCallum 2011, _An Introduction to Conditional Random Fields_** — CRF 的长篇导论/综述，把线性链与一般图 CRF、推断与学习、与逻辑回归/HMM 的关系系统梳理。读完本课想深入 CRF 的首选。
- **McCallum, Freitag & Pereira 2000, _Maximum Entropy Markov Models for Information Extraction and Segmentation_** — MEMM，CRF 的前身。读它理解「局部归一」的标签偏置问题，从而明白 CRF 为何要全局归一。
- **Lample et al. 2016, _Neural Architectures for Named Entity Recognition_** — BiLSTM-CRF，把神经特征与 CRF 标签层结合，是经典 CRF 通往现代序列标注的关键一步。读它看清模块 04 的思想如何延续到深度学习。

## 文本分类与评测 · Text Classification & Evaluation
- ★ **Wang & Manning 2012, _Baselines and Bigrams: Simple, Good Sentiment and Topic Classification_** — 证明朴素贝叶斯/SVM 配合 bigram 特征是极强的基线（NBSVM），常逼平复杂模型。提醒我们：上经典基线前别急着上深度模型。模块 05 的精神支柱。
- **McCallum & Nigam 1998, _A Comparison of Event Models for Naive Bayes Text Classification_** — 厘清多项式与伯努利两种朴素贝叶斯事件模型的差异，是正确实现 NB 文本分类的必读细节。
- **Joachims 1998, _Text Categorization with Support Vector Machines_** — 把 SVM 引入文本分类的经典，论证高维稀疏特征下线性分类器为何有效。理解模块 05 线性分类器的代表作。
- **Sebastiani 2002, _Machine Learning in Automated Text Categorization_** — 文本分类的全面综述（特征选择、分类器、评测指标），是体系化了解该领域的地图。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课全部用纯 numpy 从零实现**：不调用 NLTK / spaCy / gensim / scikit-learn 的现成模型，而是亲手写 word2vec 的负采样梯度、n-gram 的 Kneser-Ney、HMM 的对数空间前向/Viterbi、线性链 CRF 的配分函数、TF-IDF 与朴素贝叶斯。每个实现都配 `assert` 自测（前向==暴力枚举、Viterbi 得分==该路径得分、KN 概率归一、F1 与手算一致），保证逻辑正确。
- **真实数据，联网失败回退**：词向量用 tiny-shakespeare、序列标注用 CoNLL-2003 风格语料；下载失败时回退到内置的真实小样本，算法路径完全一致，保证 CPU 秒级可跑。
- **课程衔接**：本课是 AI 知识体系的**地基课**。上承语言学与概率论，下接 C01（Transformer 与现代注意力——其前身正是这里的序列模型与表示学习）、C02/C03（预训练与微调——困惑度、交叉熵的评测传统源自模块 02）、信息抽取与检索类课程（NER、TF-IDF 的现代版本）。理解经典 NLP，是读懂「现代 NLP 哪些是真新、哪些是旧瓶新酒」的前提。
