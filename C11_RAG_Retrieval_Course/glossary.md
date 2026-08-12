# 术语词典 · Glossary（检索增强与长上下文评测）

> 按主题分组，每条 2–3 句释义。读 DPR / FAISS / HNSW / RAGAS / FlashAttention 长上下文论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用纯 numpy/pandas 在 CPU 上把这些概念从零实现，但术语与真实检索系统一一对应。

## RAG 总体框架 · RAG Overall Framework

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| RAG (Retrieval-Augmented Generation) | 检索增强生成 | 在生成前先从外部语料检索相关片段、拼进提示再让模型作答的范式（Lewis 2020）。把易过时、易幻觉的参数化记忆，换成可更新、可溯源的非参数化外部知识。 |
| parametric memory | 参数化记忆 | 模型权重里隐式存下的知识。容量大但更新需重训、无法溯源、易在边角事实上幻觉。RAG 的动机就是给它配一个外部「开卷」记忆。 |
| non-parametric memory | 非参数化记忆 | 存在模型之外、可随时增删改的知识库（文档、向量索引）。RAG 在推理时检索它，使知识可更新、可引用、可审计。 |
| retriever | 检索器 | RAG 的第一段：给定查询，从语料里取回 top-k 候选片段。质量上限决定整个系统上限——检索不到，生成再强也没用（garbage in, garbage out）。 |
| generator / reader | 生成器 / 阅读器 | RAG 的第二段：把查询与检索到的上下文一起读入、生成答案。理想下它只依据给定上下文作答（grounded），不靠或少靠自身参数化记忆。 |
| chunk / passage | 文档块 / 段落 | 把长文档切成的检索单元（如 100–500 词一块）。块太大则稀释相关信号、超预算；太小则割裂语义。chunking 策略是 RAG 工程的第一个隐形旋钮。 |
| context window | 上下文窗口 | 模型一次能读入的最大 token 数。它约束了能塞进多少检索片段，也是「RAG vs 长上下文」权衡的硬约束（模块 06）。 |
| grounding / attribution | 接地 / 溯源 | 让答案的每个论断都能指回检索到的具体来源。是 RAG 相对纯生成的核心卖点，也是评测 faithfulness 的依据。 |
| in-context learning | 上下文学习 | 模型不更新权重、仅凭提示里给的示例/知识就完成任务的能力。RAG 把「检索到的知识」当作上下文喂进去，本质是一种 in-context 的知识注入。 |
| open-domain QA | 开放域问答 | 不限定文档、从大规模语料（如整个维基百科）里找答案的问答任务。是 RAG/DPR 的经典评测场景（NaturalQuestions、TriviaQA）。 |

## 嵌入与相似度 · Embeddings & Similarity

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| embedding | 嵌入 | 把文本（词/句/段）映射成稠密实数向量，使语义相近的文本在向量空间里也相近。是语义检索的基石——检索从「字面匹配」升级成「向量近邻」。 |
| dense vector | 稠密向量 | 维度不高（几百~几千）、几乎每维都非零的向量表示，对应 embedding。与之相对的是稀疏向量（如词袋/TF-IDF，维度等于词表、绝大多数为零）。 |
| dot product | 点积 | 两向量对应分量乘积之和 $\sum_i a_i b_i$，衡量它们的对齐程度。是最廉价的相似度，也是注意力分数与最大内积搜索（MIPS）的核心运算。 |
| cosine similarity | 余弦相似度 | 两向量夹角的余弦 $\frac{a\cdot b}{\|a\|\|b\|}\in[-1,1]$，即归一化后的点积。只看方向不看长度，是语义检索最常用的相似度，对向量模长不敏感。 |
| L2 normalization | L2 归一化 | 把向量除以自身的 L2 范数，使其落到单位球面。归一化后点积 = 余弦相似度；也让欧氏距离与余弦在排序上等价（$\|a-b\|^2=2-2\cos$）。 |
| Euclidean / L2 distance | 欧氏距离 | $\|a-b\|_2$，向量空间里的直线距离。对单位向量，它与余弦相似度给出相同的近邻排序，故很多索引内部用 L2 等价地实现余弦检索。 |
| bi-encoder / dual encoder | 双编码器 | 把查询与文档**各自独立**编码成向量，离线把文档全部编好、在线只编查询再做向量近邻。快（可预计算+索引），但查询与文档无交互，精度有上限。DPR 是代表。 |
| cross-encoder | 交叉编码器 | 把查询与文档**拼在一起**送进模型、让二者在每层充分交互、直接输出一个相关性分数。精度高但必须对每个候选实时跑一遍，贵——故只用于重排少量候选（模块 03）。 |
| DPR (Dense Passage Retrieval) | 稠密段落检索 | Karpukhin 2020 提出的双编码器检索：用对比学习训练 query/passage 编码器，使相关 pair 点积高。证明了稠密检索可显著超过 BM25，是现代 RAG 检索器的范式起点。 |
| query / document encoder | 查询 / 文档编码器 | 双编码器里分别处理查询和文档的两个塔。可共享权重也可不共享；训练目标是让相关 query-doc 的向量相似度高于不相关的。 |
| sentence embedding | 句向量 | 整句/整段的单一向量表示（如 Sentence-BERT 用池化得到）。RAG 检索通常以句/段为单位嵌入与检索。 |
| semantic search | 语义搜索 | 基于 embedding 向量近邻的检索，能匹配同义改写（如「汽车」匹配「automobile」）。与基于词重叠的词法检索互补。 |

## 词法检索 · Lexical Retrieval

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| lexical / sparse retrieval | 词法 / 稀疏检索 | 基于词项重叠打分的检索（TF-IDF、BM25）。精确匹配关键词、可解释、无需训练、对罕见词/实体强，但抓不住同义改写。 |
| BM25 | —— | Robertson 等的经典词法打分函数：在 TF-IDF 上加入词频饱和（saturation）与文档长度归一化。几十年来是检索的强基线，稠密检索常需与它混合才稳。 |
| TF-IDF (Term Frequency–Inverse Document Frequency) | 词频-逆文档频率 | 词在本文档里越频繁、在整个语料里越罕见，权重越高。是最朴素的词项加权，BM25 的前身。 |
| term frequency saturation | 词频饱和 | BM25 用 $\frac{tf(k_1+1)}{tf+k_1}$ 让词频的贡献随出现次数递增但有上限——出现 10 次不该比出现 5 次的相关性翻倍。是 BM25 胜过朴素 TF-IDF 的关键之一。 |
| inverse document frequency (IDF) | 逆文档频率 | $\log\frac{N}{df}$ 量级的量，惩罚常见词、奖励罕见词。让 the/of 这类词几乎无贡献，而专有名词权重高。 |
| document length normalization | 文档长度归一化 | BM25 用参数 $b$ 抵消「长文档天然词频高」的偏置，避免检索一味偏向长文档。 |
| inverted index | 倒排索引 | 从「词 → 含该词的文档列表」的映射，是词法检索高效的根本数据结构。BM25 借它只需扫描含查询词的文档。 |
| hybrid retrieval | 混合检索 | 把稠密（语义）与稀疏（词法）的结果融合，取长补短：语义抓改写、词法抓精确实体。常用分数加权或 RRF 融合（模块 03）。 |
| out-of-vocabulary / rare entity | 未登录词 / 罕见实体 | 训练时少见的词或实体（人名、型号、代码符号）。embedding 容易把它们编得不准，而词法检索靠精确匹配反而更可靠——这是混合检索的动机之一。 |

## 向量检索与索引 · Vector Retrieval & Indexing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| kNN (k-Nearest Neighbors) | k 近邻 | 在向量集合里找与查询最近的 k 个。暴力法对每个库向量算一次相似度，精确但 O(N·d)，库一大就慢。 |
| brute-force / exact search | 暴力 / 精确搜索 | 逐一比对所有库向量、保证返回真正的 top-k。是精度的金标准（recall=100%），也是衡量 ANN 召回率的对照。 |
| ANN (Approximate Nearest Neighbor) | 近似最近邻 | 牺牲一点召回率换取数量级的加速：只检查库向量的一小部分。FAISS/HNSW/ScaNN 都属此类，是十亿级检索可行的关键。 |
| MIPS (Maximum Inner Product Search) | 最大内积搜索 | 找内积最大（而非距离最近）的向量。归一化后等价于余弦近邻；很多检索本质是 MIPS。 |
| recall@k (of ANN) | 召回率 | ANN 返回的 top-k 里，有多少是暴力精确 top-k 的成员。是衡量近似索引「找得准不准」的核心指标，与延迟/内存做权衡。 |
| IVF (Inverted File Index) | 倒排文件索引 | 先用聚类把向量空间分成若干 cell（Voronoi 区），查询时只搜最近的 `nprobe` 个 cell。用「分桶+只看几桶」把候选量从 N 降到 N·nprobe/nlist。 |
| coarse quantizer / centroid | 粗量化器 / 质心 | IVF 里用来划分 cell 的聚类中心（如 k-means 质心）。查询先找最近的几个质心，再在对应桶内细搜。 |
| nprobe / nlist | 探查桶数 / 总桶数 | IVF 的两个旋钮：nlist 是聚类桶总数，nprobe 是查询时实际搜索的桶数。nprobe 越大召回越高但越慢——召回-延迟权衡的直接旋钮。 |
| HNSW (Hierarchical Navigable Small World) | 分层可导航小世界图 | Malkov 2018 的图索引：建一个多层近邻图，上层稀疏供远距离跳转、下层稠密供局部精搜，贪心导航到近邻。高召回低延迟，是当下最流行的内存 ANN。 |
| greedy graph traversal | 贪心图导航 | 从入口点出发，每步移动到邻居中离查询更近的那个，直到无法更近。HNSW 的查询过程，平均 O(log N) 跳到达近邻区。 |
| PQ (Product Quantization) | 乘积量化 | Jégou 2011 的压缩法：把高维向量切成 m 段子向量，各段用一个小码本（如 256 个质心）量化成 1 字节。把向量从几 KB 压到几十字节，并支持查表式近似距离。 |
| codebook / sub-quantizer | 码本 / 子量化器 | PQ 里每个子空间的一组质心（如 256 个）。向量的每段被替换成最近质心的编号（码字），码本就是编号到质心的查找表。 |
| ADC (Asymmetric Distance Computation) | 非对称距离计算 | PQ 查询时不量化查询本身，而是预先算出查询各段到该段码本所有质心的距离表，库向量距离 = 按其码字查表求和。快且比对称量化更准。 |
| recall-latency / speed-accuracy tradeoff | 召回-延迟权衡 | ANN 的根本张力：搜得越多（nprobe 大、ef 大）召回越高但越慢。调参就是在给定延迟/内存预算下把召回率推到最高。 |
| ef / efSearch | 搜索宽度 | HNSW 查询时维护的候选集大小。越大则探索越广、召回越高、越慢，是 HNSW 版的 nprobe。 |

## 重排与融合 · Reranking & Fusion

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| two-stage retrieval | 两段式检索 | 先用便宜的 bi-encoder/BM25 从全库召回 top-N（几百），再用昂贵但精准的 cross-encoder 重排成 top-k（几个）。兼顾召回的广与精排的准，是工业 RAG 的标配。 |
| reranking | 重排 | 对第一段召回的候选重新打分排序。重排器看得更细（查询-文档交互），常能把真正相关的文档从第 20 名提到前 3，显著提升 nDCG/MRR。 |
| monoBERT / cross-encoder reranker | —— | Nogueira & Cho 2019 把 BERT 当作相关性分类器对每个 query-doc 打分重排，大幅提升排序质量。是「召回+重排」两段式范式的奠基工作。 |
| MMR (Maximal Marginal Relevance) | 最大边际相关 | Carbonell & Goldstein 1998 的去冗余排序：每步选「与查询相关且与已选结果不相似」的文档，用 $\lambda$ 平衡相关性与多样性。避免 top-k 全是near-duplicate。 |
| diversity / redundancy | 多样性 / 冗余 | top-k 里若全是同一信息的重复表述，浪费了宝贵的上下文预算。MMR 等方法提升结果集覆盖的信息面，对多跳/多方面问题尤其重要。 |
| RRF (Reciprocal Rank Fusion) | 倒数排名融合 | Cormack 2009 的融合法：一个文档的融合分 $=\sum_{\text{各路}}\frac{1}{k+\text{rank}}$。只用名次不用原始分数，无需归一化、异常稳健，是混合检索/多召回融合的默认选择。 |
| score normalization | 分数归一化 | 融合不同检索器（BM25 分数与余弦分数量纲不同）前，把分数缩放到可比区间（min-max、z-score）。RRF 的优势正是绕开了这个易错步骤。 |
| late interaction (ColBERT) | 延迟交互 | 介于 bi- 与 cross-encoder 之间：为每个 token 存向量，查询时做 token 级 MaxSim 交互。比 bi-encoder 准、比 cross-encoder 省，是重排/检索的折中路线。 |
| candidate set / top-N | 候选集 | 第一段召回交给重排的文档集合（如 top-100）。N 太小则真正相关文档可能没进候选（重排也救不回），太大则重排变贵——召回与精排的接力棒。 |

## RAG 评测 · RAG Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| faithfulness / groundedness | 忠实度 / 接地度 | 答案中的每个论断是否都能由检索到的上下文支持。低 faithfulness = 模型在「编」（幻觉），即便答案恰好正确也算不忠实。是 RAG 评测最核心的安全指标。 |
| answer relevance | 答案相关性 | 答案是否切题地回应了问题（不跑题、不答非所问、不啰嗦无关内容）。与 faithfulness 正交：可以忠实于上下文却答非所问。 |
| context precision | 上下文精确率 | 检索到的上下文里，真正与问题相关的比例。低精确率 = 检索带回大量噪声片段，稀释信号、挤占预算、还可能误导生成。 |
| context recall | 上下文召回率 | 回答问题所需的信息，有多少被检索上下文覆盖到。低召回 = 关键证据没检索到，生成器巧妇难为无米之炊。是 RAG 失败最常见的根因。 |
| RAGAS | —— | Es 2023 提出的无参考（reference-free）RAG 自动评测框架：用 LLM 把答案拆成论断逐条核验，给出 faithfulness/answer relevance/context precision/recall 四项分。本课用规则版模拟其思想。 |
| hallucination | 幻觉 | 模型生成了无法由上下文（或事实）支持的内容。RAG 通过提供上下文来抑制它，但生成器仍可能「无视上下文」自说自话——故必须用 faithfulness 检测。 |
| claim / statement decomposition | 论断分解 | 把一段答案拆成若干可独立验证的原子论断，再逐条判断是否被上下文支持。是 faithfulness 自动评测（RAGAS）的核心操作。 |
| reference-free evaluation | 无参考评测 | 不依赖人工标注的标准答案，仅凭问题、上下文、答案三者间的一致性来打分。RAGAS 的卖点——让 RAG 评测可规模化、可在线监控。 |
| NLI / entailment | 自然语言推理 / 蕴含 | 判断「上下文是否蕴含某论断」的任务，是 faithfulness 判定的技术底座：论断被上下文 entail = 忠实，contradict/neutral = 可能幻觉。 |
| context utilization | 上下文利用率 | 答案实际用到了检索上下文中多少有效信息。高召回但低利用 = 证据检索到了却没被生成器用上，指向生成端而非检索端的问题。 |
| end-to-end evaluation | 端到端评测 | 同时考察检索与生成两段、给出系统级结论。需把 context recall/precision（检索）与 faithfulness/answer relevance（生成）合起来看，定位瓶颈在哪一段。 |

## 检索排序指标 · Retrieval Ranking Metrics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| relevance judgment / qrels | 相关性标注 | 每个 (查询, 文档) 是否相关（二元）或相关到几级（分级）的人工标注。是所有检索指标的 ground truth，TREC 的 qrels 文件是经典格式。 |
| Precision@k | 前 k 精确率 | top-k 结果里相关文档的比例。直观但不看名次（第 1 名和第 k 名同等计）、也不看召回。 |
| Recall@k | 前 k 召回率 | 所有相关文档里，有多少出现在 top-k。衡量「漏没漏」，与 precision 此消彼长。RAG 里检索召回直接决定生成上限。 |
| MRR (Mean Reciprocal Rank) | 平均倒数排名 | 第一个相关结果名次的倒数，对所有查询取平均：$\frac1Q\sum\frac1{\text{rank}_1}$。只关心「第一个对的在多靠前」，适合「找一个正确答案即可」的场景。 |
| AP / MAP (Mean Average Precision) | 平均精度 / 其均值 | AP = 在每个相关文档处的 precision 的平均，综合了精确率与名次；MAP = 所有查询 AP 的均值。是二元相关性下最常用的综合排序指标。 |
| nDCG (normalized Discounted Cumulative Gain) | 归一化折损累积增益 | 支持**分级**相关性的排序指标：高相关文档排前面得分高，名次越靠后增益按 $1/\log_2(rank+1)$ 折损；再除以理想排序（IDCG）归一到 [0,1]。 |
| DCG / IDCG | 折损累积增益 / 理想 DCG | DCG 是带位置折损的增益累加；IDCG 是把所有文档按真实相关性完美排序后的 DCG。nDCG = DCG/IDCG，使不同查询可比。 |
| graded relevance | 分级相关性 | 相关性不止 0/1，而是 0/1/2/3 多档（如「不相关/有点相关/相关/完美」）。nDCG 能利用它，而 MAP/MRR 只能用二元。 |
| gain / discount | 增益 / 折损 | nDCG 的两个要件：gain 由相关性等级决定（常用 $2^{rel}-1$），discount 由位置决定（$1/\log_2(rank+1)$）——奖励「把高相关的排前面」。 |
| binary vs graded metrics | 二元 vs 分级指标 | MRR/MAP 用二元相关性、实现简单；nDCG 用分级相关性、更贴近「有些结果比另一些更相关」的现实。选指标要匹配标注粒度与任务目标。 |
| metric sensitivity | 指标敏感度 | 不同指标对不同变化敏感：MRR 只对第一个相关项的位置敏感，Recall@k 对截断 k 敏感，nDCG 对高相关项是否靠前敏感。报多个指标才不被单一视角误导。 |

## 长上下文评测 · Long-Context Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| long context | 长上下文 | 模型能处理的超长输入（数万~数百万 token）。它让「把整本书塞进提示」成为可能，与 RAG 形成「外置检索 vs 内置长窗口」的路线之争。 |
| NIAH (Needle In A Haystack) | 大海捞针 | Kamradt 的经典长上下文压力测试：把一句无关事实（针）藏进很长的无关文本（草堆），在不同上下文长度与不同插入位置下，测模型能否检索出针。 |
| needle / haystack | 针 / 草堆 | 针 = 要被检索出的关键事实句；草堆 = 包裹它的大量无关文本。NIAH 通过移动针的位置、加长草堆，画出模型的检索能力地图。 |
| lost in the middle | 中段迷失 | Liu 2023 的发现：当关键信息位于长上下文的**中间**时，模型的利用率显著低于它在**开头或结尾**时，准确率曲线呈 U 形。位置偏置是长上下文的核心缺陷。 |
| positional bias | 位置偏置 | 模型对上下文不同位置的信息利用不均（通常首尾强、中间弱）。它意味着「把关键证据放哪」会显著影响答案——对 RAG 的上下文排序有直接启示。 |
| U-shaped curve | U 形曲线 | lost-in-the-middle 的标志：准确率随针的相对位置变化，两端高、中间低，形似 U。是诊断位置偏置最直观的图。 |
| multi-needle | 多针 | NIAH 的加强版：藏入多个针，要求模型全部检索到。比单针更难，更贴近真实「需要综合多处信息」的场景。 |
| multi-hop | 多跳 | 答案需要串联多处分散信息、逐步推理才能得到（如「A 的导师的出生地」）。考验检索的覆盖与推理的链式整合，是 RAG 与长上下文都吃力的硬骨头。 |
| RULER | —— | Hsieh 2024 提出的长上下文合成基准，在 NIAH 之上加入多针、变量追踪、聚合等更难任务，给出模型「有效上下文长度」——往往远短于宣称的最大长度。 |
| effective context length | 有效上下文长度 | 模型能真正可靠利用的上下文长度，常显著小于其宣称的最大窗口。RULER 等基准揭示：宣称 128k 不等于在 128k 处仍准确。 |
| RAG vs long-context | RAG 与长上下文之争 | 两条给模型补充知识的路线：RAG 外置检索（省 token、可溯源、可更新、但受检索质量限）vs 长窗口直接全塞（简单、无检索误差、但贵、慢、受位置偏置限）。常互补而非互斥。 |
| context stuffing | 上下文塞满 | 不做检索筛选、把大量文档直接塞进长窗口。简单但浪费算力、放大位置偏置与干扰项噪声，且仍受有效长度限制。 |
| distractor | 干扰项 | 与查询表面相关但实则无关的片段。长上下文/检索里干扰项越多，模型越容易被带偏，是评测鲁棒性的关键变量。 |
