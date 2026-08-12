# 术语词典 · Glossary（深度学习理论与数据/生成媒体评测）

> 按主题分组，每条 2–3 句中文释义，英文术语保留原文（论文与社区通用语）。读 double descent / grokking / 数据流水线 / 生成评测相关论文遇到生词回这里查。本课用纯 numpy 玩具复现这些现象，术语与真实研究一一对应。

## 泛化与偏差-方差 · Generalization & Bias-Variance

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| generalization | 泛化 | 模型在未见过的数据上的表现。泛化误差 = 测试误差，是训练的真正目标；训练误差低而测试误差高即过拟合。本课多数现象（双下降、grokking）都是关于「训练误差与泛化误差如何随容量/时间分离」。 |
| bias-variance decomposition | 偏差-方差分解 | 把期望测试误差拆成 偏差²（模型族系统性偏离真函数）+ 方差（对不同训练集的抖动）+ 不可约噪声。是理解经典泛化的核心工具，但其「U 型」结论在过参数化下被双下降推翻。 |
| bias | 偏差 | 模型族的表达力不足导致的系统性误差。容量越小偏差越大（欠拟合）；高偏差表现为训练与测试误差都高。 |
| variance | 方差 | 模型对训练集随机性的敏感度。容量越大方差通常越大（过拟合）；但过参数化区方差可能因隐式正则而回落，这正是双下降的来源之一。 |
| irreducible error / noise | 不可约误差 / 噪声 | 数据本身的随机性（标签噪声、测量误差）带来的误差下界，任何模型都无法消除。偏差-方差分解的第三项。 |
| capacity / model complexity | 容量 / 模型复杂度 | 模型族能表达的函数集合的「大小」，可用参数量、VC 维、范数等度量。经典理论认为容量越大越易过拟合；双下降表明这只在欠参数化区成立。 |
| underparameterized / overparameterized | 欠参数化 / 过参数化 | 参数量少于 / 多于（拟合训练集所需的）样本约束数。现代深度网络几乎都在过参数化区，参数量远超样本数却仍泛化良好——经典理论的盲区。 |
| capacity sweep | 容量扫描 | 固定数据、系统改变模型容量（如随机特征数），记录训练/测试误差随容量的曲线。是复现双下降的标准实验设计，本课模块 01 的核心做法。 |

## 双下降与隐式正则 · Double Descent & Implicit Regularization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| double descent | 双下降 | 测试误差随容量先按经典 U 型上升到峰、越过插值阈值后**再次下降**的现象 [Belkin 2019]。打破「容量越大越过拟合」的经典直觉，是现代过参数化模型泛化的关键经验图景。 |
| interpolation threshold | 插值阈值 | 模型容量恰好够把训练集**完美拟合**（训练误差降到 0）的临界点，通常在 参数量 ≈ 样本数 附近。测试误差在此处达到**尖峰**，是双下降两段之间的分界。 |
| interpolation | 插值 | 模型完美拟合所有训练点（含噪声），训练误差为 0。经典理论视其为过拟合的极端，但过参数化下的插值解反而可能泛化良好（取决于是哪个插值解）。 |
| model-wise double descent | 模型维双下降 | 横轴是模型容量（参数/特征数）的双下降。与之相对的还有 sample-wise（横轴样本数）与 epoch-wise（横轴训练步数）双下降 [Nakkiran 2021]。 |
| epoch-wise double descent | 训练步维双下降 | 固定模型，测试误差随**训练时间**先降后升再降。说明双下降不止关于容量，也关于优化轨迹，与 grokking 的延迟泛化有思想上的呼应。 |
| effective model complexity (EMC) | 有效模型复杂度 | Nakkiran 等提出的统一量：模型+优化过程能拟合到接近零误差的最大样本数。用它把 model/sample/epoch 三种双下降统一在「EMC 越过样本数」这一条件下。 |
| min-norm solution | 最小范数解 | 在所有能插值训练集的解里，参数范数最小的那个（如最小二乘的伪逆解 $X^+y$）。过参数化区优化器隐式偏向它，范数小 → 函数平滑 → 泛化好，是双下降第二段下降的主因。 |
| implicit regularization | 隐式正则 | 优化算法（如 GD/SGD）本身、而非显式惩罚项，对解施加的偏好。例如梯度下降从 0 出发在过参数化线性回归上收敛到最小范数解——「没加正则，却像加了」。 |
| pseudo-inverse / Moore-Penrose | 伪逆 | $X^+=X^\top(XX^\top)^{-1}$（行满秩时）等，给出最小二乘/最小范数解的闭式。本课用它直接构造过参数化区的最小范数插值解。 |
| ridge regression / Tikhonov | 岭回归 | 在最小二乘上加 $\lambda\|w\|^2$ 惩罚。显式正则的代表，可平滑掉插值阈值处的尖峰——把它与隐式正则对照，是理解双下降的好抓手。 |
| random features | 随机特征 | 用随机权重把输入映射到高维特征 $\phi(x)=\sigma(Wx)$ 再做线性回归 [Rahimi & Recht 2007]。特征数 = 可调容量，是在 CPU 上复现双下降最干净的玩具模型，本课模块 01 主力。 |
| benign overfitting | 良性过拟合 | 模型完美拟合含噪训练集却仍泛化良好的现象 [Bartlett 2020]。是双下降第二段的理论解释方向：高维下噪声被「吸收」进无害的方向。 |

## 训练动力学：Grokking 与涌现 · Grokking & Emergence

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| grokking | grokking（顿悟） | 模型在训练集上**早早**达到近乎完美，测试集却长时间停留在随机水平，再训练很久后测试性能**突然跃升**到完美 [Power 2022]。延迟泛化的戏剧化案例。 |
| delayed generalization | 延迟泛化 | grokking 的核心特征：泛化的发生远滞后于记忆（拟合训练集）。提示「拟合训练集」与「学到可泛化结构」是两个可在时间上分离的过程。 |
| memorization vs generalization | 记忆 vs 泛化 | 记忆 = 逐样本背下训练集（高训练分、低测试分）；泛化 = 学到能迁移的规律。grokking 展示模型可以先记忆、后泛化，两者机制不同。 |
| weight decay | 权重衰减 | 对参数范数的 L2 惩罚（等价于每步把权重乘一个 <1 的因子）。是 grokking 的**关键驱动**：它持续施压把记忆解推向范数更小的泛化解；去掉它 grokking 往往不发生 [Power 2022, Nanda 2023]。 |
| phase transition | 相变 | 系统行为在某个参数临界值附近发生质变（类比物理相变）。grokking 的测试性能跃升、涌现能力的阶跃常被描述为相变，但是否「真相变」取决于度量（见 mirage）。 |
| circuit formation | 回路形成 | grokking 期间网络内部从「记忆回路」逐渐长出「泛化回路」（如模算术的傅里叶/三角恒等式回路）的机制解释 [Nanda 2023 progress measures]。 |
| progress measure | 进展度量 | 一个在最终指标跳变之前就**平滑变化**的内部量（如特定频率成分的强度），揭示跳变其实是平滑进展累积到阈值的结果。是反驳「突现」的有力工具。 |
| emergent ability | 涌现能力 | 小模型几乎没有、大模型突然具备的能力 [Wei 2022]。最初被视为规模带来的质变；后续争议在于它多大程度是度量选择造成的假象。 |
| emergence (as a mirage) | 涌现假象 | Schaeffer 2023 的论点：许多「涌现」源于用了**非线性/不连续**的度量（如 exact-match accuracy）。换成平滑、连续的度量（如 token 级对数似然、编辑距离），同样的能力呈**平滑可预测**增长。 |
| metric discontinuity | 度量不连续 | 度量本身的阶跃性（如「全对才得分」的 all-or-nothing 评分）会把底层能力的平滑提升放大成表观跳变。是涌现假象的技术核心。 |
| scaling laws | 缩放律 | 损失随参数量/数据量/算力呈幂律下降的经验规律 [Kaplan 2020, Hoffmann 2022]。平滑的缩放律与表观「涌现」并存，正是 mirage 争议的背景。 |

## 数据流水线 · Data Pipeline

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data pipeline | 数据流水线 | 把原始爬取语料变成可训练数据的一连串处理：抽取、清洗、过滤、去重、混合、shuffle、分片、tokenize、打包。预训练质量很大程度由它决定。 |
| cleaning / normalization | 清洗 / 规范化 | 去除 HTML 标签、控制字符、修复编码、统一空白/Unicode 等。最基础但收益巨大的一步，脏数据会直接污染下游一切。 |
| quality filtering | 质量过滤 | 用启发式（长度、符号比、停用词比、重复率）或分类器/困惑度，剔除低质文档（乱码、模板、SEO 垃圾）。RefinedWeb、Gopher 等的核心步骤 [Penedo 2023, Rae 2021]。 |
| deduplication / dedup | 去重 | 移除重复或近重复文档。重复数据会被过度记忆、虚增某些内容权重、并污染评测；去重能显著提升模型质量与训练效率 [Lee 2022]。 |
| exact dedup | 精确去重 | 移除逐字节相同（或哈希相同）的文档/段落。简单但只能抓完全重复，抓不住「改了几个字」的近重复。 |
| near-duplicate | 近重复 | 内容高度相似但不逐字相同的文档（转载、模板微调）。需用 Jaccard/MinHash 等相似度方法识别，是去重的难点与重点。 |
| shingle / k-gram | shingle / k-元组 | 把文档切成所有长度为 k 的连续词/字符片段构成的集合。两文档的 shingle 集合越像，内容越像，是 Jaccard 相似度的输入表示。 |
| Jaccard similarity | Jaccard 相似度 | 两集合交集大小 ÷ 并集大小，$\|A\cap B\|/\|A\cup B\|\in[0,1]$。度量两文档 shingle 集合的重叠度，是近重复判定的标准相似度。 |
| MinHash | MinHash | 用多个随机哈希，取每个哈希下集合元素的最小值组成签名 [Broder 1997]。两签名在某位相等的概率**恰等于** Jaccard 相似度，于是可用短签名近似估计相似度，近线性时间完成大规模去重。 |
| LSH (locality-sensitive hashing) | 局部敏感哈希 | 把 MinHash 签名分桶（banding），让相似文档大概率落入同一桶，从而只在桶内两两比较，避免 $O(n^2)$ 全比对。大规模近重复去重的工程骨架。 |
| shuffle buffer | 乱序缓冲 | 流式训练无法把全量数据载入内存全局打乱时，维护一个固定大小缓冲区，每次随机取出一条、补入一条，近似全局 shuffle。缓冲越大越接近真随机，太小则残留顺序偏差。 |
| sharding | 分片 | 把数据集切成多个文件/块（shard），便于并行读取、断点续训、跨 worker 划分。分片+局部 shuffle 是大规模流式训练的标配。 |
| streaming | 流式 | 不把数据集整体下载/载入内存，而是边训练边按需读取（如从对象存储流式拉取）。海量语料的必然选择，但限制了能做的全局操作（如全局 shuffle、全局去重）。 |
| data contamination | 数据污染 | 评测基准的样本（或其近重复）混进了训练集，导致评测分数虚高、不再反映真实泛化。去重与 decontamination 是评测可信度的前提（呼应 C03）。 |
| token packing | token 打包 | 把多条短文档拼接、按固定上下文长度切块，减少 padding 浪费、提高训练吞吐。会引入跨文档注意力等细节问题。 |
| throughput | 吞吐 | 单位时间处理的样本/token 数。数据流水线常是训练吞吐瓶颈（IO、解析、shuffle），需与计算并行（prefetch）。 |

## 合成数据与模型坍塌 · Synthetic Data & Model Collapse

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| synthetic data | 合成数据 | 由模型（而非人类/真实世界）生成的训练数据。可缓解数据稀缺、定制分布、做蒸馏；但质量与多样性需严格评估，否则反噬。 |
| self-training / bootstrapping | 自训练 / 自举 | 用模型自己的输出（经过滤/打标）作为新训练数据再训模型。STaR、Self-Instruct 等的范式 [Wang 2023]。迭代进行时若无真实数据锚定，易触发坍塌。 |
| distillation | 蒸馏 | 用强模型（teacher）的输出训练弱/小模型（student）。合成数据的重要来源；student 受 teacher 分布约束，也会继承其偏差与盲区。 |
| model collapse | 模型坍塌 | 在「上一代模型生成的数据」上递归训练，**分布逐代退化**：先丢失尾部/罕见模式（早期坍塌），最终收敛到低方差的少数模式（晚期坍塌）[Shumailov 2024]。生成式互联网时代的核心风险。 |
| early vs late collapse | 早期 / 晚期坍塌 | 早期：分布尾部（稀有事件）先消失，方差开始收缩；晚期：分布塌成一个或少数尖峰，多样性近乎归零。本课用迭代高斯自训练精确复现方差的逐代收缩。 |
| variance shrinkage | 方差收缩 | 模型坍塌的可量化标志：每代用有限样本拟合再重采样，估计方差系统性偏小（采样+拟合误差累积），方差按代数近似几何衰减。 |
| diversity | 多样性 | 生成分布覆盖真实分布模式的广度（vs 只会生成少数模式）。与保真度（单样本真不真）是两个独立维度，坍塌首先伤的是多样性。 |
| quality-diversity tradeoff | 质量-多样性权衡 | 过滤/温度调低可提高单样本质量，却往往降低多样性（砍掉尾部）。合成数据与生成模型评估都绕不开这对张力，对应生成评测的 precision-recall。 |
| filtering / curation | 过滤 / 策展 | 对合成数据按质量/正确性/多样性筛选（如只保留可验证正确的解题）。是让自训练**不坍塌甚至变好**的关键，但过度过滤会自己制造分布偏移。 |
| real-data anchoring | 真实数据锚定 | 在每代训练中混入足量真实数据，阻止递归坍塌。理论与实验都表明：只要真实数据占比不衰减，分布退化可被遏制 [Gerstgrasser 2024]。 |
| accumulate vs replace | 累积 vs 替换 | 递归训练时，是用新合成数据**替换**旧数据（易坍塌）还是把合成数据**累积**到真实数据上（坍塌大为缓解）。是 model collapse 是否致命的关键变量。 |

## 生成媒体评测 · Generative Media Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| FID (Fréchet Inception Distance) | FID | 把真实与生成图像各自送进 Inception 网络取特征，假设两组特征服从高斯，计算两高斯间的 Fréchet（2-Wasserstein）距离 [Heusel 2017]。越低越接近真实分布；图像生成的主指标。 |
| Fréchet distance (between Gaussians) | 高斯间 Fréchet 距离 | $\|\mu_1-\mu_2\|^2+\mathrm{Tr}\big(\Sigma_1+\Sigma_2-2(\Sigma_1\Sigma_2)^{1/2}\big)$。同时惩罚均值差（保真）与协方差差（多样性/结构），是 FID 的数学本体。本课从零实现含矩阵平方根。 |
| matrix square root | 矩阵平方根 | 满足 $S^2=M$ 的对称半正定矩阵 $S=M^{1/2}$。Fréchet 公式里 $(\Sigma_1\Sigma_2)^{1/2}$ 需要它；本课用特征分解（对称化后）从零算。 |
| Inception Score (IS) | Inception 分数 | $\exp\big(\mathbb{E}_x\,\mathrm{KL}(p(y\mid x)\,\|\,p(y))\big)$ [Salimans 2016]。奖励单图分类**置信**（保真）且整体类别**均匀**（多样）。无需真实图像，但有不参考真实分布、易被钻空子等缺陷。 |
| KL divergence | KL 散度 | $\mathrm{KL}(p\|q)=\sum_i p_i\log(p_i/q_i)\ge 0$，度量分布 $p$ 相对 $q$ 的信息差异，非对称。IS 的核心运算（条件分布 vs 边际分布）。 |
| marginal class distribution | 边际类别分布 | $p(y)=\mathbb{E}_x\,p(y\mid x)$，对所有生成样本的预测类别分布求平均。IS 用它衡量多样性：越接近均匀越好。 |
| precision / recall (for generative models) | 生成模型的精确率 / 召回率 | 把保真与多样拆成两个量 [Kynkäänniemi 2019]：precision = 生成样本落在真实分布支撑内的比例（保真）；recall = 真实样本被生成分布覆盖的比例（多样）。用 k-NN 流形估计支撑集。 |
| fidelity vs diversity | 保真 vs 多样 | 生成评测的两个正交维度：单个样本像不像真的（fidelity/precision）vs 整体覆盖不覆盖真实的全部模式（diversity/recall）。单一标量（如 FID）会把两者混在一起。 |
| manifold / support estimation | 流形 / 支撑集估计 | 用样本点及其 k 近邻球的并集近似分布的支撑集（数据流形）。improved precision-recall 据此判断一个点是否「落在另一分布的流形内」。 |
| mode coverage / mode dropping | 模式覆盖 / 模式丢弃 | 生成分布是否覆盖真实分布的所有模式；丢弃部分模式（mode dropping）是 GAN 等的常见病，伤 recall/diversity 但可能不伤 precision。 |
| human evaluation | 人评 | 由人对生成质量打分/做偏好比较（如 side-by-side、Elo）。自动指标的最终校准基准，但贵、慢、主观、难复现；常与自动指标互补。 |
| CLIPScore | CLIPScore | 用 CLIP 的图文嵌入余弦相似度，无需参考图地评估「生成图与文本提示」的一致性 [Hessel 2021]。文生图对齐评测的常用指标。 |
| reference-free metric | 无参考指标 | 不需要配对参考样本即可计算的指标（如 IS、CLIPScore）。方便但通常更易被操纵、与人评相关性更脆弱。 |

## 评测方法论 · Evaluation Methodology (cross-cutting)

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| metric design | 度量设计 | 选择/构造评测指标本身是有后果的决定：度量的连续性、对齐人类判断的程度、可被操纵性，都会改变结论（涌现假象就是反例教训）。 |
| Goodhart's law | 古德哈特定律 | 「当一个度量成为目标，它就不再是好度量。」生成评测中过拟合 FID/IS 会牺牲真实质量，提醒任何单一自动指标都需配合人评与多指标交叉验证。 |
| distribution shift | 分布偏移 | 训练分布与部署/评测分布不一致。数据流水线（过滤引入偏移）、合成数据（坍塌引入偏移）、生成评测（特征提取器的域）处处涉及。 |
| reproducibility | 可复现性 | 同样的方法/数据/随机种子能否复现结论。本课刻意全部用固定种子的 numpy 玩具，让每条曲线、每个指标都**可逐位复现**，是研究素养的底线。 |
