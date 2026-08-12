# 术语词典 · Glossary（推荐系统与大规模排序）

> 按主题分组，每条 2–3 句释义。读推荐系统论文（Koren、Rendle、Covington、He、Naumov、Kang）或工业博客（YouTube、淘宝、Netflix、Meta）遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用 numpy 从零实现这些机制，术语与真实工业系统一一对应。

## 系统与漏斗 · System & Funnel

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| recommender system | 推荐系统 | 在没有明确查询的情况下，从海量物品（视频、商品、帖子）里为每个用户预测最可能感兴趣的少数几个并排序展示的系统。是 YouTube/TikTok/Amazon/Netflix 等的核心收入引擎。 |
| candidate generation / retrieval | 召回 / 候选生成 | 漏斗第一层：从百万~十亿级物品库中**快速**筛出几百~几千个候选。要求极高吞吐、低精度容忍，典型用双塔 + ANN 或协同过滤。 |
| pre-ranking | 粗排 | 召回与精排之间的轻量打分层，把几千候选压到几百。用比精排小得多的模型（常是轻量双塔或蒸馏模型）平衡延迟与效果。 |
| ranking / fine-ranking | 精排 | 漏斗核心层：用重模型（DLRM、深度 CTR）对几百候选逐个精细打分（CTR、时长、转化等多目标），决定最终排序。算力几乎都花在这里。 |
| re-ranking | 重排 | 漏斗最后一层：在精排分基础上加业务规则与列表级目标——多样性（diversity）、新鲜度、打散、去重、商业加权、公平性。优化的是整个列表而非单点。 |
| funnel | 漏斗 | 召回→粗排→精排→重排的级联架构。每层候选数量级递减、模型复杂度递增，用「先粗后精」在延迟预算内服务十亿级物品库。 |
| candidate / item / document | 候选 / 物品 / 文档 | 被推荐的对象。推荐里叫 item，搜索里叫 document，本质都是要打分排序的候选集。 |
| serving latency | 服务延迟 | 一次推荐请求从进来到返回结果的耗时（通常要求几十毫秒）。漏斗设计、ANN、模型大小都受它约束。 |
| candidate pool / corpus | 物品库 / 语料库 | 全部可被推荐物品的集合，工业上常达 10^6~10^9。召回层必须在亚线性时间内从中取候选，这是 ANN 存在的理由。 |

## 反馈与数据 · Feedback & Data

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| explicit feedback | 显式反馈 | 用户主动给出的评分/点赞/差评（如 1–5 星）。信号干净但**稀疏**（多数人不评分），且只在用户愿意表态时存在。 |
| implicit feedback | 隐式反馈 | 从行为推断的偏好：点击、观看时长、加购、停留。量大但**有噪声且只有正例**——没点击不等于不喜欢（可能没看到）。现代工业系统主要靠它。 |
| positive-only / one-class | 单类问题 | 隐式反馈只观测到正向行为，没有可靠的负例。如何采样/构造负例（负采样）是隐式推荐的核心难题。 |
| confidence weighting | 置信度加权 | 隐式反馈里把交互强度（看了几次、停留多久）转成置信度 $c_{ui}=1+\alpha r_{ui}$，让模型更信任强信号。源自 Hu 2008 的 iALS。 |
| user-item interaction matrix | 用户-物品交互矩阵 | 行是用户、列是物品、元素是评分或交互的稀疏矩阵 $R$。推荐的核心数据结构，稀疏度常 >99%。 |
| sparsity | 稀疏度 | 交互矩阵中已观测元素的占比极低（如 MovieLens-100k 约 6%）。稀疏是推荐区别于普通监督学习的根本特征。 |
| cold start | 冷启动 | 新用户/新物品没有历史交互，纯协同过滤无法处理。解法：用内容特征（content-based）、人口属性、或双塔的 side feature 把新实体接入。 |
| data leakage (temporal) | 时间泄漏 | 用未来交互预测过去，导致离线指标虚高。正确评估必须按时间切分（leave-last-out / 时间窗），不能随机划分。 |
| feedback loop | 反馈回路 | 推荐影响用户行为、行为又成为下一轮训练数据，形成自我强化。会放大流行度偏置、制造信息茧房，是工业系统的长期隐患。 |
| MovieLens | —— | GroupLens 发布的经典电影评分公开数据集（100k/1M/20M 多个规模）。推荐研究的「MNIST」，本课的真实数据来源。 |

## 协同过滤 · Collaborative Filtering

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| collaborative filtering (CF) | 协同过滤 | 仅用「谁和谁交互过」的协同信号做推荐，不需要物品内容。核心假设：行为相似的用户会喜欢相似的物品。 |
| user-based CF | 基于用户的 CF | 找与目标用户口味最相似的 k 个邻居，用他们的评分加权预测。直观但用户数大时邻居计算贵、用户兴趣易漂移。 |
| item-based CF | 基于物品的 CF | 用「物品间相似度」预测：你喜欢的物品的相似物品也推给你。物品相似度比用户相似度更稳定、可离线预计算，是 Amazon 早年的主力（Sarwar 2001、Linden 2003）。 |
| cosine similarity | 余弦相似度 | 两个向量夹角的余弦 $\frac{a\cdot b}{\|a\|\|b\|}\in[-1,1]$，只看方向不看模长。CF 里最常用的相似度。 |
| Pearson correlation | 皮尔逊相关 | 先减去各自均值再算余弦，等价于中心化余弦。能抵消用户/物品的评分基准差异（有人习惯打高分），CF 里常优于裸余弦。 |
| adjusted cosine | 调整余弦 | item-based CF 中减去**用户**均值再算物品间余弦，消除用户评分尺度差异，Sarwar 2001 证明优于普通余弦。 |
| neighborhood / kNN | 邻域 / k 近邻 | 预测时只用最相似的 k 个邻居（而非全部），既降噪又提速。k 是 CF 的关键超参。 |
| shrinkage | 收缩 | 当两物品共同评分用户很少时，相似度不可靠，用 $\frac{n}{n+\lambda}$ 把它向 0 收缩，避免偶然高相似度。 |

## 矩阵分解 · Matrix Factorization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| matrix factorization (MF) | 矩阵分解 | 把交互矩阵 $R\approx PQ^\top$ 分解为用户隐因子 $P$ 与物品隐因子 $Q$，预测 $\hat r_{ui}=p_u\cdot q_i$。Netflix Prize 的核心武器（Koren 2009）。 |
| latent factor model | 隐因子模型 | 用低维稠密向量（隐因子）表示用户与物品，把高维稀疏交互压成低维表示。MF、双塔、深度推荐都是它的变体。 |
| embedding | 嵌入 | 把离散 ID（用户、物品、特征）映射成可学习的稠密向量。是所有现代推荐模型的基本构件。 |
| bias term | 偏置项 | 预测里加上全局均值 $\mu$、用户偏置 $b_u$、物品偏置 $b_i$：$\hat r=\mu+b_u+b_i+p_u\cdot q_i$。捕捉「这个用户总打高分」「这部电影普遍受欢迎」，常贡献相当大一部分准确率。 |
| SGD (stochastic gradient descent) | 随机梯度下降 | MF 的一种训练法：每次抽一个观测 $(u,i)$ 算梯度更新 $p_u,q_i$。实现简单、可在线，但需调学习率。 |
| ALS (alternating least squares) | 交替最小二乘 | MF 的另一训练法：固定 $Q$ 解 $P$（凸的最小二乘）、再固定 $P$ 解 $Q$，交替迭代。每步有闭式解、易并行，特别适合隐式反馈（iALS）。 |
| regularization (L2) | L2 正则 | 在损失里加 $\lambda(\|p_u\|^2+\|q_i\|^2)$ 防止过拟合稀疏数据。推荐里正则强度对效果影响极大。 |
| SVD / truncated SVD | 奇异值分解 / 截断 SVD | 线代里把矩阵分解为 $U\Sigma V^\top$。MF 常被叫「SVD」但其实不同：真 SVD 要求矩阵无缺失，而推荐矩阵大量缺失，所以只在**观测项**上最小化误差（Funk 的 "SVD"）。 |
| FunkSVD | —— | Simon Funk 在 Netflix Prize 中用 SGD 训练带偏置 MF 的方法（2006 博客），是现代 MF 的起点，严格说不是 SVD。 |
| WALS / iALS | 加权/隐式 ALS | 针对隐式反馈的 ALS：对所有 (u,i) 对（含未观测的当负例）按置信度加权做最小二乘。Hu 2008 提出，工业召回常用。 |

## 双塔与召回 · Two-Tower & Retrieval

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| two-tower model | 双塔模型 | 一个塔（网络）编码用户/查询、另一个塔编码物品，各输出一个向量，用点积/余弦打分。塔互相独立 → 物品向量可离线预算并建 ANN 索引，是工业召回的标准架构（Yi 2019、Covington 2016）。 |
| dual encoder | 双编码器 | 双塔的别名，强调两个独立编码器。与 cross-encoder（把 query-item 拼起来一起编码，精度高但不能预算）相对。 |
| in-batch negatives | 批内负采样 | 训练双塔时，把同一 batch 里**别人的正例物品**当作当前样本的负例，几乎零成本地得到大量负样本。是双塔训练的关键技巧。 |
| sampled softmax | 采样 softmax | 物品数百万时无法对全表算 softmax，只在一小撮采样负例上近似。in-batch negatives 是它的一种实现。 |
| logQ correction / sampling bias correction | logQ 校正 / 采样偏差校正 | in-batch 负采样里热门物品被采为负例的概率高，导致系统性低估它们。从 logit 里减去 $\log Q(i)$（采样概率）来纠偏（Yi 2019）。 |
| approximate nearest neighbor (ANN) | 近似最近邻 | 在向量库里**亚线性**地找与查询向量最近的 k 个（不保证精确）。让百万级物品的点积召回可在毫秒完成。代表：HNSW、IVF、ScaNN、FAISS。 |
| HNSW | —— | Hierarchical Navigable Small World，基于多层图的 ANN 索引，查询快、召回率高，是当前最常用的 ANN 算法之一。 |
| maximum inner product search (MIPS) | 最大内积搜索 | 找内积最大（而非欧氏距离最近）的向量。双塔召回正是 MIPS；可通过变换转成最近邻问题用 ANN 解。 |
| temperature | 温度 | softmax/对比损失里给 logit 除以的标量 $\tau$，控制分布尖锐程度。检索训练里 $\tau$ 对收敛与效果敏感。 |
| hard negative | 难负例 | 模型容易误判为正的负例（比如同类但用户没交互的物品）。混入难负例能显著提升排序质量，但要小心假负例。 |

## 排序学习 · Learning to Rank

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| learning to rank (LTR) | 排序学习 | 直接学一个把候选排好序的模型，而非单纯预测评分。按损失作用范围分 pointwise / pairwise / listwise 三类。 |
| pointwise | 逐点 | 把排序当回归/分类：独立预测每个候选的分（如 CTR），按分排序。简单但忽略了「排序是相对的」，对 list 内相对顺序不直接优化。 |
| pairwise | 成对 | 学习候选对的相对顺序：让正例分高于负例。代表 RankNet、BPR、LambdaRank。直接优化「谁该在谁前面」，更贴合排序目标。 |
| listwise | 列表 | 直接对整个候选列表的排序质量建损失（如 ListNet、ListMLE、Softmax loss、LambdaMART 的 NDCG 优化）。理论最优但实现复杂。 |
| BPR (Bayesian Personalized Ranking) | 贝叶斯个性化排序 | Rendle 2009 提出的 pairwise 隐式反馈损失：对每个 (用户, 正例 i, 负例 j) 三元组最大化 $\ln\sigma(\hat x_{ui}-\hat x_{uj})$。隐式推荐的奠基损失。 |
| RankNet | —— | Burges 2005 的 pairwise 神经排序：用交叉熵建模「i 排在 j 前」的概率 $\sigma(s_i-s_j)$。LambdaRank/LambdaMART 的前身。 |
| LambdaRank / LambdaMART | —— | 在 RankNet 梯度上乘以「交换 i,j 带来的 nDCG 变化」$|\Delta\text{NDCG}|$，从而间接优化不可导的 nDCG。LambdaMART（GBDT 版）长期是 LTR 竞赛 SOTA。 |
| nDCG (normalized DCG) | 归一化折损累计增益 | 排序质量指标：DCG 按位置对数折损累加相关性，再除以理想排序的 DCG 归一到 [0,1]。最常用的排序离线指标（Järvelin 2002）。 |
| DCG / IDCG | 折损累计增益 / 理想 DCG | $\text{DCG}@k=\sum_{i=1}^k \frac{2^{rel_i}-1}{\log_2(i+1)}$；IDCG 是把相关性降序排得到的最大 DCG。两者之比即 nDCG。 |
| MAP / MRR | 平均精度均值 / 平均倒数排名 | MAP 对每个查询算 average precision 再平均；MRR 取第一个相关结果排名的倒数。都是 Top-N 排序的常用指标。 |
| Recall@K / Precision@K / Hit@K | —— | Top-K 推荐里命中的相关物品占全部相关的比例（Recall）、占 K 的比例（Precision）、是否至少命中一个（Hit）。召回层最看重 Recall@K。 |

## CTR、特征交叉与序列 · CTR, Feature Crossing & Sequential

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| click-through rate (CTR) | 点击率 | 展示后被点击的概率。精排的核心预测目标之一，广告系统直接用它定价（eCPM = CTR × bid）。 |
| logistic regression (LR) | 逻辑回归 | CTR 预估的经典基线：$\sigma(w\cdot x+b)$，特征常是 one-hot 的 ID 与人工交叉。可解释、可扩展，曾是工业 CTR 主力。 |
| feature crossing | 特征交叉 | 把两个特征的组合（如 城市×品类）作为新特征，捕捉协同效应。LR 需手工交叉，FM/DNN 自动学交叉。 |
| factorization machine (FM) | 因子分解机 | Rendle 2010：给每个特征学一个向量 $v_i$，二阶交叉项用 $\langle v_i,v_j\rangle x_i x_j$ 建模。能在稀疏数据上自动学所有二阶交叉，且预测可 $O(kn)$ 线性时间算。 |
| field-aware FM (FFM) | 域感知 FM | FM 的扩展：每个特征对不同「域」（field）学不同向量，交叉更精细。CTR 竞赛常胜军。 |
| DeepFM / Wide&Deep | —— | 把 FM/线性部分（记忆）与 DNN（泛化）并联的 CTR 架构。Wide&Deep（Cheng 2016）、DeepFM（Guo 2017）是工业精排的常见起点。 |
| DLRM (Deep Learning Recommendation Model) | 深度学习推荐模型 | Meta 2019（Naumov）：稀疏特征过 embedding、与稠密特征交互（点积）后过 MLP。是开源工业级精排的代表，强调 embedding 表巨大、通信是瓶颈。 |
| embedding table | 嵌入表 | 存所有 ID 特征向量的大查找表，工业上可达 TB 级（亿级 ID）。是推荐模型的主要参数与显存/通信瓶颈。 |
| sequential recommendation | 序列推荐 | 把用户历史行为当成有序序列，预测下一个交互。捕捉兴趣的时序演化与短期意图，是现代推荐的主流方向之一。 |
| GRU4Rec | —— | Hidasi 2016：用 GRU（RNN）建模 session 内点击序列预测下一项，开创了把序列模型用于推荐。 |
| SASRec (Self-Attentive Sequential Rec) | 自注意力序列推荐 | Kang 2018：用单向自注意力（类 GPT）建模行为序列预测下一项，比 RNN 更并行、长程依赖更好，是序列推荐的强基线。 |
| BERT4Rec | —— | Sun 2019：用双向 Transformer + 掩码物品预测（类 BERT）做序列推荐，常优于单向的 SASRec。 |
| next-item prediction | 下一项预测 | 序列推荐的训练目标：给定前缀行为序列，预测下一个物品（常用 softmax / 采样 softmax over 物品表）。 |

## 偏置、去偏与评估 · Bias, Debiasing & Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| position bias | 位置偏置 | 用户更容易点击靠前的结果，与相关性无关。直接用点击当标签训排序会把位置当成了相关性，必须去偏。 |
| inverse propensity weighting (IPW) | 逆倾向加权 | 用「该位置被观察的概率（propensity）」的倒数给样本加权，纠正位置/曝光偏置，得到无偏的损失估计。 |
| propensity | 倾向得分 | 一个样本被观测（被曝光/被点击位置）的概率。IPW、反事实评估的核心量。 |
| examination hypothesis | 检验假设 | 点击 = 被看到（examine）× 相关（relevant）。把点击概率拆成位置相关的检验概率与内容相关的相关概率，是位置去偏的基础模型。 |
| popularity bias | 流行度偏置 | 热门物品因曝光多而被更多交互，模型进一步放大它们，挤压长尾。反馈回路的主要表现。 |
| selection bias | 选择偏置 | 观测到的数据不是随机采样（用户只对自己选的物品评分），导致 MNAR（缺失非随机）。离线评估与训练都受其困扰。 |
| counterfactual evaluation | 反事实评估 | 用日志数据估计「换一个推荐策略会怎样」，无需上线 A/B。基于 IPW 的 off-policy estimator（如 IPS、SNIPS）。 |
| A/B test | A/B 测试 | 把用户随机分流到新旧策略对比线上指标（CTR、时长、留存、GMV）。推荐效果的最终裁判，离线指标只是代理。 |
| offline / online metrics gap | 离线/在线指标鸿沟 | 离线 nDCG 提升不一定带来线上收益（因离线评估有偏、目标不完全对齐）。弥合这道鸿沟是工业推荐的核心难题。 |
| diversity / novelty / serendipity | 多样性 / 新颖性 / 惊喜度 | 重排阶段的列表级目标：结果不要太同质、要有新内容、能带来意外之喜。与纯精度常有权衡。 |
| MMR (Maximal Marginal Relevance) | 最大边际相关 | 重排里平衡相关性与多样性的经典贪心算法：每步选「与查询相关且与已选结果不相似」的物品。 |
