# 参考清单 · References（推荐系统与大规模排序）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制，都能在下列文献里找到工业级的对应实现与权衡。推荐/搜索/排序是机器学习落地最广、就业岗位最多的方向，这份清单覆盖从奠基算法到前沿系统的主干。

## 协同过滤与近邻 · Collaborative Filtering
- ★ **Sarwar, Karypis, Konstan & Riedl 2001, _Item-Based Collaborative Filtering Recommendation Algorithms_** — item-based CF 的奠基论文。提出用物品间相似度（adjusted cosine / 调整余弦）做推荐，论证它比 user-based 更稳定、更可离线预计算、更可扩展。本课模块 01 的直接蓝本，必读。
- ★ **Linden, Smith & York 2003, _Amazon.com Recommendations: Item-to-Item Collaborative Filtering_** — Amazon 把 item-based CF 做成「看了又看」的工业经典案例。讲清为什么物品相似度矩阵可离线算、线上 O(1) 查表，撑起了早期电商推荐。理解工业落地的必读。
- **Hu, Koren & Volinsky 2008, _Collaborative Filtering for Implicit Feedback Datasets_** — 隐式反馈 CF 的奠基（iALS/WALS）。提出把交互强度转成置信度 $c=1+\alpha r$、把未观测当负例加权最小二乘，并给出高效 ALS 解法。现代召回仍在用，模块 01/02 的隐式反馈部分源此。
- **Deshpande & Karypis 2004, _Item-Based Top-N Recommendation Algorithms_** — 系统比较各种 item-based Top-N 方法与相似度/归一化选择，是 Top-N 评估方法论的参考。

## 矩阵分解 · Matrix Factorization
- ★ **Koren, Bell & Volinsky 2009, _Matrix Factorization Techniques for Recommender Systems_ (IEEE Computer)** — Netflix Prize 的总结性必读。把带偏置的隐因子模型 $\hat r=\mu+b_u+b_i+p_u\cdot q_i$、SGD/ALS 训练、时间动态（timeSVD++）、隐式反馈（SVD++）讲得极清楚。本课模块 02 全程对标它，**最该先读的一篇**。
- ★ **Funk (Webb) 2006, _Netflix Update: Try This at Home_（博客）** — Simon Funk 用 SGD 训练带偏置 MF 的原始博客（人称 FunkSVD）。澄清「推荐里的 SVD 其实只在观测项上做」这个关键误解，是现代 MF 的实践起点。
- **Mnih & Salakhutdinov 2007, _Probabilistic Matrix Factorization_ (PMF)** — 从概率图模型视角推出 MF：高斯似然 + 高斯先验 = L2 正则的 MF。理解 MF 的贝叶斯解释、为什么这样正则，读它。
- **Rendle, Zhang & Koren 2019, _On the Difficulty of Evaluating Baselines: A Study on Recommender Systems_** — 警世之作：很多「打败 MF」的深度模型其实是基线没调好。提醒做推荐研究/工程必须认真调 MF/iALS 基线，否则结论不可信。强烈建议读，矫正对「深度一定更好」的迷信。

## 双塔召回与大规模检索 · Two-Tower Retrieval
- ★ **Covington, Adams & Sargin 2016, _Deep Neural Networks for YouTube Recommendations_** — 工业推荐的里程碑。把推荐拆成召回（候选生成，softmax over 数百万视频 + 采样）与排序两阶段，提出用户向量 × 视频向量的双塔召回 + 特征工程。本课「漏斗」世界观与模块 03 的源头，必读。
- ★ **Yi, Hong, Chen et al. 2019, _Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations_ (Google)** — 双塔 + in-batch 负采样 + **logQ 采样偏差校正**的奠基论文。讲清为什么 in-batch 负采样会偏向热门物品、如何从 logit 减 $\log Q$ 纠偏。模块 03 的核心，必读。
- **Huang et al. 2013, _Learning Deep Structured Semantic Models (DSSM)_** — 双塔/双编码器的鼻祖（用于网页搜索语义匹配）。最早系统化「query 塔 × doc 塔 + 余弦 + 采样 softmax」，理解 dual-encoder 谱系读它。
- **Johnson, Douze & Jégou 2017, _Billion-scale similarity search with GPUs_ (FAISS)** — 工业 ANN 库 FAISS 的论文，讲清 IVF/PQ 等十亿级最近邻索引。模块 03 的 ANN 部分落地参考。
- **Malkov & Yashunin 2016, _Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs (HNSW)_** — 当前最常用的图式 ANN 算法。双塔召回上线必经的索引，读它理解亚线性检索怎么做到。
- **Guo et al. 2020, _Accelerating Large-Scale Inference with Anisotropic Vector Quantization (ScaNN)_** — Google 的 MIPS 加速，把量化目标对齐内积而非欧氏距离。理解 MIPS 与 ANN 的区别读它。

## 排序学习 · Learning to Rank
- ★ **Rendle, Freudenthaler, Gantner & Schmidt-Thieme 2009, _BPR: Bayesian Personalized Ranking from Implicit Feedback_** — 隐式反馈排序的奠基损失。把推荐建成 pairwise 排序：最大化 $\ln\sigma(\hat x_{ui}-\hat x_{uj})$，并给出基于自助采样的 SGD（LearnBPR）。模块 04 的核心，必读。
- ★ **Järvelin & Kekäläinen 2002, _Cumulated Gain-Based Evaluation of IR Techniques_** — nDCG 指标的原始论文。定义 DCG 的位置折损与归一化，是排序质量评估的事实标准。模块 04 的评估部分源此，必读。
- **Burges et al. 2005, _Learning to Rank using Gradient Descent (RankNet)_** — pairwise 神经排序奠基：用 $\sigma(s_i-s_j)$ 的交叉熵学相对顺序。LambdaRank/LambdaMART 的前身，读它理解 pairwise 思想。
- **Burges 2010, _From RankNet to LambdaRank to LambdaMART: An Overview_** — Burges 亲笔综述：如何用 $|\Delta\text{nDCG}|$ 加权 RankNet 梯度，间接优化不可导的 nDCG，并落到 GBDT（LambdaMART）。LTR 必读综述。
- **Cao et al. 2007, _Learning to Rank: From Pairwise Approach to Listwise Approach (ListNet)_** — listwise LTR 的代表，用排列概率分布的交叉熵。理解 pointwise→pairwise→listwise 的演进读它。
- **Liu 2009, _Learning to Rank for Information Retrieval_（专著/综述）** — LTR 的系统性综述，三大范式、各类损失、评估一网打尽。想全面建立 LTR 框架的参考书。

## CTR、特征交叉与精排 · CTR & Fine-Ranking
- ★ **Rendle 2010, _Factorization Machines_** — FM 的奠基论文。提出用隐向量内积建模二阶特征交叉，在稀疏数据上自动学所有交叉，且预测可 $O(kn)$ 线性时间算。模块 05 的核心，必读。
- ★ **Naumov et al. 2019, _Deep Learning Recommendation Model for Personalization and Recommendation Systems (DLRM)_ (Meta)** — 开源工业级精排的代表。稀疏特征过 embedding、与稠密特征做点积交互后过 MLP，强调 embedding 表巨大、通信是训练瓶颈。模块 05「DLRM 思想」的源头，必读。
- **Cheng et al. 2016, _Wide & Deep Learning for Recommender Systems_ (Google)** — 把线性部分（wide，记忆）与 DNN（deep，泛化）并联的经典精排架构。工业 CTR 的常见起点，读它理解记忆 vs 泛化的权衡。
- **Guo et al. 2017, _DeepFM: A Factorization-Machine based Neural Network for CTR Prediction_** — 把 FM 与 DNN 共享 embedding 并联，免去人工特征交叉。Wide&Deep 的进化，CTR 工程常用。
- **Zhou et al. 2018, _Deep Interest Network (DIN)_ (Alibaba)** — 用注意力让用户历史行为对当前候选做加权，捕捉「兴趣随候选变化」。淘宝精排的代表作，理解行为注意力读它。
- **Juan et al. 2016, _Field-aware Factorization Machines for CTR Prediction (FFM)_** — FM 的域感知扩展，CTR 竞赛常胜。理解 FM→FFM 的精细化读它。

## 序列推荐 · Sequential Recommendation
- ★ **Kang & McAuley 2018, _Self-Attentive Sequential Recommendation (SASRec)_** — 用单向自注意力（类 GPT）建模行为序列预测下一项，比 RNN 并行、长程更好，是序列推荐的强基线。模块 05 的核心之一，必读。
- ★ **Hidasi et al. 2016, _Session-based Recommendations with Recurrent Neural Networks (GRU4Rec)_** — 把 RNN 引入推荐的开创作，建模 session 内点击序列。理解序列推荐起点读它，模块 05 必读。
- **Sun et al. 2019, _BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer_** — 用双向 Transformer + 掩码物品预测做序列推荐，常优于单向 SASRec。理解双向 vs 单向序列建模读它。
- **Tang & Wang 2018, _Personalized Top-N Sequential Recommendation via Convolutional Sequence Embedding (Caser)_** — 用 CNN 捕捉序列局部模式（point-level / union-level），序列推荐的另一条技术路线。

## 偏置、去偏与评估 · Bias, Debiasing & Evaluation
- ★ **Joachims, Swaminathan & Schnabel 2017, _Unbiased Learning-to-Rank with Biased Feedback_** — 位置偏置去偏的奠基。用 IPW（逆倾向加权）从有位置偏置的点击里学无偏排序，并给 propensity 估计法。模块 05 去偏部分源此，必读。
- **Schnabel et al. 2016, _Recommendations as Treatments: Debiasing Learning and Evaluation_** — 把推荐当因果处理，用 IPS 同时去偏训练与离线评估，处理 MNAR（缺失非随机）。理解选择偏置与反事实评估读它。
- **Chen et al. 2020, _Bias and Debias in Recommender System: A Survey and Future Directions_** — 系统梳理推荐里七种偏置（位置、流行度、选择、曝光、一致性…）及去偏方法。想全面了解偏置全貌的综述。
- **Steck 2013, _Evaluation of Recommendations: Rating-Prediction and Ranking_** — 讲清 MNAR 下评分预测与排序评估的陷阱，为什么随机划分会高估。评估方法论参考。

## 综述、系统与本课定位 · Surveys, Systems & Scope
- **Zhang, Yao, Sun & Tay 2019, _Deep Learning based Recommender System: A Survey and New Perspectives_** — 深度推荐的全景综述，CF、序列、注意力、图、强化学习推荐一网打尽。建立全局地图的参考。
- **He et al. 2017, _Neural Collaborative Filtering (NCF)_** — 用 MLP 替代点积做 CF 的代表作（及其后续争议，见 Rendle 2019 / Dacrema 2019）。读它+其批评，能学到「深度模型 vs 强基线」的科学态度。
- **Dacrema, Cremonesi & Jannach 2019, _Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches_** — 复现性警世论文：多数新深度推荐方法没真正超过调好的简单基线。做推荐研究/工程的清醒剂，强烈推荐。
- **TensorFlow Recommenders (TFRS)、RecBole、Microsoft Recommenders、NVIDIA Merlin/HugeCTR（开源库与文档）** — 把本课每个 numpy 实现对应到生产框架：双塔（TFRS）、各类模型基准（RecBole）、工业流水线（Merlin）。学完本课照着把验证过的逻辑迁移过去，是最自然的下一步。
- ⚠️ **本课定位与衔接**：全课用 numpy **从零**实现协同过滤/矩阵分解/双塔/BPR/FM/序列推荐，每个模型**对拍参考实现或验证损失收敛**，用真实 **MovieLens-like** 小数据（联网失败回退可复现合成数据）跑真实 Recall/nDCG。上游接 C07（ML 基础）、C11（RAG/检索，双塔召回与向量检索同源）；下游接 C37（MLOps，推荐流水线）、C39（分布式训练，embedding 表并行）、C13（RL，推荐里的 bandit/强化学习）。
