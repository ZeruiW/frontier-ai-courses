# 参考清单 · References（难例挖掘与长尾数据闭环）

> 按主题分组。★ 为**必读**。每条都注明它**解决什么问题**、为什么值得读，以及本课的哪一节用到了它。
> 与相邻课程的分工：**C37** 讲通用 MLOps 与反馈环骨架；**C43** 讲数据管道与版本化的基础设施；
> **C55** 讲 TSR 的失效模式与安全评测；**C56** 讲用增强「造」数据；**C61** 讲误差分析与面试实务。
> **本课只聚焦「哪些数据值得要、怎么把它们找出来、以及怎么证明它们真的有用」这一条纵深。**

---

## 一 · 长尾与类别不平衡 · Long-Tail & Class Imbalance

- ★ **Lin et al. 2017, _Focal Loss for Dense Object Detection_ (RetinaNet, ICCV)** —
  **解决的问题：单阶段检测器里前景-背景 1:1000 的极端不平衡，让海量易负样本主导梯度。**
  (1 − p_t)^γ 的软加权是理解「难例挖掘的连续版本」的入口。
  **本课模块 02 的核心对照物**；也请注意它治的是前景-背景不平衡，**不是类别长尾**——
  这个区分是模块 01 的第一节。
- ★ **Gupta et al. 2019, _LVIS: A Dataset for Large Vocabulary Instance Segmentation_ (CVPR)** —
  **解决的问题：给「检测里的长尾」一个真实的、可比较的基准。**
  1200+ 类别、rare/common/frequent 三档划分、以及 **repeat factor sampling 的原始定义**
  r_c = max(1, √(t/f_c))。**模块 01 的公式与阈值直接出自这里**，
  也是回答「你在什么数据上验证过长尾方法」的标准答案。
- ★ **Cui et al. 2019, _Class-Balanced Loss Based on Effective Number of Samples_ (CVPR)** —
  **解决的问题：为什么按 1/n 反频加权会过度补偿。**
  提出**有效样本数** E_n = (1 − β^n)/(1 − β)，承认样本之间存在信息重叠。
  **模块 01 的权重公式与 β 的直觉全部来自这一篇**，只读方法部分的两页就够。
- ★ **Cao et al. 2019, _Learning Imbalanced Datasets with Label-Distribution-Aware Margin Loss_ (LDAM, NeurIPS)** —
  **解决的问题：不改变数据分布的前提下，怎样让尾部类获得更好的泛化。**
  从泛化界推出 margin 应按 n_j^(−1/4) 分配，并提出 **DRW（延迟重加权）**——
  「先正常训、后期再重加权」这个训练日程本身就是很实用的一招。
- ★ **Kang et al. 2020, _Decoupling Representation and Classifier for Long-Tailed Recognition_ (ICLR)** —
  **解决的问题：长尾到底伤的是特征还是分类器。**
  结论极其实用：**表示用原始长尾分布学最好，只有分类器需要重平衡**（cRT / LWS）。
  **这条结论直接决定了工程上「要不要重训整个模型」**，是模块 01 决策树的关键分支。
- ★ **Menon et al. 2021, _Long-Tail Learning via Logit Adjustment_ (ICLR)** —
  **解决的问题：有没有零训练成本、有理论保证的长尾修正。**
  推理时把 logit 减去 τ·log π_y，最小化平衡误差率。
  **性价比最高的一招**（可随时回滚、不动训练流程），模块 01 的「先问能不能改推理」就是它。
- ★ **Tan et al. 2020, _Equalization Loss for Long-Tailed Object Recognition_ (EQL, CVPR)** 与
  **Tan et al. 2021, _Equalization Loss v2: A New Gradient Balance Approach_ (EQLv2, CVPR)** —
  **解决的问题：检测独有的长尾机制——稀有类的分类器每一步被上千个负梯度淹没。**
  EQL 按频次屏蔽负梯度；**EQLv2 改成用实测正负梯度比做闭环控制，不需要先验频次表**，
  对类别表会变的量产系统更友好。模块 01 第五节的主线。
- **Wang et al. 2021, _Seesaw Loss for Long-Tailed Instance Segmentation_ (CVPR)** —
  **解决的问题：EQL 压住负梯度后，稀有类开始乱报（假正例上升）。**
  用「缓解因子 + 补偿因子」两项分别治「学不到」和「学过头」。是 EQL 系的实用改进。
- **Zhou et al. 2020, _BBN: Bilateral-Branch Network with Cumulative Learning_ (CVPR)** —
  **解决的问题：表示学习与分类器重平衡如何在一次训练里兼得。**
  与 Decoupling 是同一洞察的两种实现，对照读能加深理解。
- **Zhang et al. 2023, _Deep Long-Tailed Learning: A Survey_ (TPAMI)** —
  **解决的问题：这个领域方法太多，需要一张地图。**
  把方法分成类别重平衡 / 信息增强 / 模块改进三族。**当你要给方法选型做决策树时，先看它的分类法。**
- **Van Horn & Perona 2017, _The Devil is in the Tails: Fine-grained Classification in the Wild_** —
  **解决的问题：为什么真实世界的长尾比学术基准更难。**
  很好的动机材料，也解释了「再收十倍数据分布形状不变」这个结论。
- **Oksuz et al. 2020, _Imbalance Problems in Object Detection: A Review_ (TPAMI)** —
  **解决的问题：检测里到底有几种不平衡。**
  把不平衡分成类别、尺度、空间、目标（损失项）四类。
  **读完你会明白为什么「混着治」注定无效**，是模块 01 第一节的骨架来源。

---

## 二 · 难例挖掘与噪声标签 · Hard Mining & Label Noise

- ★ **Shrivastava et al. 2016, _Training Region-based Object Detectors with Online Hard Example Mining_ (OHEM, CVPR)** —
  **解决的问题：手工调「正负样本比例」这个超参既麻烦又不随训练自适应。**
  按 loss 排序在线选取难例。**重点读它关于「必须先 NMS 去重」的那一段**——
  这是模块 02 里最容易被跳过却最致命的实现细节。
- ★ **Northcutt et al. 2021, _Confident Learning: Estimating Uncertainty in Dataset Labels_ (JAIR)** —
  **解决的问题：怎样系统性地找出数据集里被标错的样本。**
  用交叉验证的预测概率估计「标注类 ↔ 真实类」联合分布。cleanlab 的内核。
  **模块 02「难例还是噪声」这一节的主要工具**；注意它要求概率校准良好。
- ★ **Arpit et al. 2017, _A Closer Look at Memorization in Deep Networks_ (ICML)** 与
  **Zhang et al. 2017, _Understanding Deep Learning Requires Rethinking Generalization_ (ICLR)** —
  **解决的问题：网络到底是先学规律还是先记噪声。**
  结论是**先学规律、后记噪声**——这正是用**损失轨迹**区分难例与噪声的理论依据。
  **本课模块 02 的那个「轨迹形状三分法」直接建立在这两篇上。**
- ★ **Pleiss et al. 2020, _Identifying Mislabeled Data using the Area Under the Margin Ranking_ (AUM, NeurIPS)** —
  **解决的问题：只训练一次就能找出错标。**
  记录训练过程中的 margin 并用插入的「阈值样本」自动定分界线。
  比置信学习更轻量，**非常适合塞进现有训练流程当作副产物**。
- **Han et al. 2018, _Co-teaching: Robust Training of Deep Neural Networks with Extremely Noisy Labels_ (NeurIPS)** —
  **解决的问题：训练过程中如何在线过滤噪声。**
  两个网络互相喂「小损失」样本。**读它是为了理解它与难例挖掘方向完全相反**——
  同时开启两者等于什么都没做，这是模块 02 的一个重要提醒。
- **Li et al. 2019, _Gradient Harmonized Single-stage Detector_ (GHM, AAAI)** —
  **解决的问题：Focal Loss 会给「极难到不正常」的样本最大权重，而那些常常是噪声。**
  按梯度密度加权，**把两端（海量易样本 + 离群极难样本）同时压下去**。
  与 Focal Loss 对照读，能看清「难例还是噪声」这个判断的两种立场。
- **Cao et al. 2020, _Prime Sample Attention in Object Detection_ (PISA, CVPR)** —
  **解决的问题：训练目标（逐样本 loss）与评测目标（AP）并不一致。**
  提醒你按 loss 排序其实是个代理指标，对理解「挖到的难例是否真的影响指标」很有帮助。
- **Bengio et al. 2009, _Curriculum Learning_ (ICML)** 与
  **Kumar et al. 2010, _Self-Paced Learning for Latent Variable Models_ (NeurIPS)** —
  **解决的问题：样本的呈现顺序会不会影响最终解。**
  与难例挖掘方向相反，两者的实践综合是「前期均匀、中后期挖掘」这个时间分工。
- **Felzenszwalb et al. 2010, _Object Detection with Discriminatively Trained Part Based Models_ (DPM, TPAMI)** —
  **解决的问题：负样本空间大到无法枚举时怎么训。**
  经典的 **hard negative mining / bootstrapping** 流程（训 → 找假正例 → 加入负集 → 重训）。
  **今天的难负样本挖掘就是它的直系后代**，读一遍能理解这个思想有多老、多稳。
- **Sung & Poggio 1995 / Rowley et al. 1998（人脸检测的 bootstrapping 工作）** —
  **解决的问题：同上，但更早。** 作为思想史读，能看到「误检挖掘」这条路的起点。

---

## 三 · 主动学习与数据选择 · Active Learning & Data Selection

- ★ **Settles 2009, _Active Learning Literature Survey_ (UW-Madison TR)** —
  **解决的问题：给「怎么选样本去标」这件事一张完整地图。**
  池式/流式设定、不确定性采样、QBC、期望模型变化、期望误差减少。
  **读第 2–4 章即可**，它给出的分类法至今仍是讨论触发策略的公共语言。
- ★ **Sener & Savarese 2018, _Active Learning for Convolutional Neural Networks: A Core-Set Approach_ (ICLR)** —
  **解决的问题：批量选择时，逐样本的不确定性会选出一批互相冗余的样本。**
  把批量主动学习形式化成 **k-center 覆盖问题**，贪心有 2-近似保证。
  **模块 04 的 core-set 实现直接来自这一篇**；也请记住它的核心立场是「选覆盖」而非「选最难」。
- ★ **Houlsby et al. 2011, _Bayesian Active Learning for Classification and Preference Learning_ (BALD)** —
  **解决的问题：熵高的样本可能只是本身模糊，标了也没用。**
  用互信息把**认知不确定性**从总不确定性里分离出来。
  **模块 03 最重要的一个公式**：BALD = 平均预测的熵 − 各模型熵的平均。
- ★ **Gal et al. 2017, _Deep Bayesian Active Learning with Image Data_ (ICML)** —
  **解决的问题：怎样在深度网络上实际算出 BALD。**
  用 MC dropout 近似后验采样。**工程上最便宜的落地路径**，模块 03 的实现参照。
- **Kirsch et al. 2019, _BatchBALD_ (NeurIPS)** —
  **解决的问题：朴素 BALD 批量选择时会挑出一批几乎相同的样本。**
  在批内联合互信息上做贪心。**任何一次要选几千张的真实系统都会撞上这个问题。**
- **Beluch et al. 2018, _The Power of Ensembles for Active Learning in Image Classification_ (CVPR)** —
  **解决的问题：MC dropout 的不确定性到底够不够好。**
  结论是**深度集成明显更好**。这解释了为什么工程上宁可多训几个种子模型也不只靠 dropout。
- **Yoo & Kweon 2019, _Learning Loss for Active Learning_ (CVPR)** —
  **解决的问题：如何用一个与任务无关的模块直接预测「这个样本 loss 会有多高」。**
  对检测这种输出结构复杂、不确定性不好定义的任务特别有吸引力。
- **Yuan et al. 2021, _Multiple Instance Active Learning for Object Detection_ (MI-AOD, CVPR)** 与
  **Choi et al. / Yu et al. 的 _Consistency-based Active Learning for Object Detection_ (CALD)** —
  **解决的问题：检测的不确定性是逐框的，如何聚合到图级并处理背景噪声。**
  **模块 03「框级 → 图级聚合」一节的直接来源**，也给出了一致性触发在检测上的量化证据。
- ★ **Lowell et al. 2019, _Practical Obstacles to Deploying Active Learning_ (EMNLP)** —
  **解决的问题：主动学习在真实系统里为什么常常不灵。**
  关键结论：**主动学习采出的数据集与模型强绑定**，换个模型架构后这批数据的优势会消失，
  有时甚至不如随机采样。**这是本课模块 03 里最该被记住的一条警告**，
  也是「必须保留随机回传通道」这个工程建议的依据。
- **Kirsch & Gal 2022, _Unifying Approaches in Active Learning and Active Sampling_** —
  **解决的问题：把信息论视角下的各种准则统一起来。**
  适合在读完 BALD 之后收尾，能看清各准则之间的关系。

---

## 四 · 挖掘基础设施与数据引擎 · Mining Infrastructure & Data Engines

- ★ **Johnson et al. 2019, _Billion-scale Similarity Search with GPUs_ (FAISS, IEEE Trans. Big Data)** —
  **解决的问题：十亿级向量上怎么做近邻检索。**
  IVF、乘积量化（PQ）、以及召回-延迟-内存三者的权衡。
  **模块 04 嵌入检索一节的工程底座**；即使你只用它的 Python 封装，也该知道 nprobe 与 nlist 在调什么。
- ★ **Malkov & Yashunin 2018, _Efficient and Robust Approximate Nearest Neighbor Search Using HNSW_ (TPAMI)** —
  **解决的问题：如何在高召回下仍保持低延迟。**
  可导航小世界图索引，今天绝大多数向量库的默认选择。
  **读它是为了理解「召回率是可以调的、而且默认值未必够」**——ANN 丢掉的往往正是稀疏区域的长尾样本。
- ★ **Radford et al. 2021, _Learning Transferable Visual Models From Natural Language Supervision_ (CLIP, ICML)** —
  **解决的问题：从哪儿来一个通用的、可用自然语言查询的图像嵌入。**
  **它是现代数据挖掘流水线的事实标准工具**：既做场景级检索，又做零样本场景打标
  （「夜间」「雨天」「隧道」），是模块 04 里 VLM 打标最轻量的实现路径。
- ★ **Kirillov et al. 2023, _Segment Anything_ (SAM, ICCV)——重点读 §4「Data Engine」** —
  **解决的问题：怎样用「模型辅助标注 → 训练 → 更强的模型辅助标注」的循环，
  在有限预算下造出十亿级标注。**
  **本课「数据飞轮」这个概念最清晰、最可复制的公开案例**，三阶段（辅助手工 → 半自动 → 全自动）
  的设计值得逐段读。这一节比论文的方法部分更有价值。
- ★ **Sorscher et al. 2022, _Beyond Neural Scaling Laws: Beating Power Law Scaling via Data Pruning_ (NeurIPS)** —
  **解决的问题：数据规模律是不是不可打破的。**
  结论是**通过有原则的数据剪枝可以把幂律变成指数级下降**，而且
  「数据少时该保留容易样本、数据多时该保留困难样本」这个反转结论极其反直觉且实用。
  **本课「定向加 2000 张胜过随机加 10 万张」这个主张的理论支撑。**
- ★ **Abbas et al. 2023, _SemDeDup: Data-efficient Learning at Web-scale through Semantic Deduplication_** —
  **解决的问题：语义重复（不是像素重复）在大规模数据里占多大比例、去掉后会怎样。**
  在嵌入空间聚类去重，**几乎不掉点的前提下砍掉可观比例的数据**。
  **模块 04 去重一节的方法原型**；TSR 的连续帧场景比网络图片的重复度还高得多。
- **Gadre et al. 2023, _DataComp: In Search of the Next Generation of Multimodal Datasets_ (NeurIPS)** —
  **解决的问题：把「数据筛选策略」本身当作可比较的研究对象。**
  固定模型与算力、只比数据筛选方法。**这个实验范式正是本课模块 05 想教的东西**：
  数据工作也要有受控实验。
- **Wei et al. 2015, _Submodularity in Data Subset Selection and Active Learning_ (ICML)** 与
  **Killamsetty et al. 2021, _GLISTER / GRAD-MATCH_** —
  **解决的问题：子集选择的贪心算法凭什么有效。**
  次模性与 (1 − 1/e) 保证。**读它是为了知道哪些目标有保证、哪些没有**——
  覆盖类目标有，纯难例挖掘没有。
- **Mirzasoleiman et al. 2020, _CRAIG: Coresets for Data-efficient Training of Machine Learning Models_ (ICML)** —
  **解决的问题：怎样选一个子集，使其梯度近似全量数据的梯度。**
  与 core-set 的「几何覆盖」视角互补，提供了「功能覆盖」视角。
- **Zauner 2010, _Implementation and Benchmarking of Perceptual Image Hash Functions_（pHash 的标准参考）** —
  **解决的问题：怎样用几十字节判断两张图是不是近重复。**
  DCT 低频指纹 + 汉明距离。**模块 04 去重流水线第一级的实现依据**；
  也要记住它的边界：换天气换车就完全失效，语义重复得靠嵌入。
- **DVC / lakeFS / Delta Lake 的官方文档（任选其一精读）** —
  **解决的问题：数据集怎么做不可变快照与版本回溯。**
  **模块 04「数据血缘」一节的落地工具**；完整的数据工程讨论在 **C43**。
  重点看它们怎么表达「某次训练用的到底是哪一份数据」。

---

## 五 · 闭环验证、统计与 ML 系统工程 · Validation, Statistics & ML Systems

- ★ **Hoiem et al. 2012, _Diagnosing Error in Object Detectors_ (ECCV)** 与
  **Bolya et al. 2020, _TIDE: A General Toolbox for Identifying Object Detection Errors_ (ECCV)** —
  **解决的问题：mAP 掉了/涨了，到底是哪一类错误在动。**
  把误差拆成分类/定位/重复/背景/漏检，并算出**修好每一类各能涨多少 mAP**。
  **这是触发策略的输入**：先知道哪类错最值钱，才知道该挖什么。详细展开在 **C61**。
- ★ **Benjamini & Hochberg 1995, _Controlling the False Discovery Rate_ (JRSS-B)** —
  **解决的问题：同时看 20 个切片时，「至少一个显著」几乎必然发生。**
  BH 过程控制 FDR，比 Bonferroni 实用得多。
  **模块 05 门禁判定的统计基础**——不做校正的分切片汇报等于允许自己挑好看的看。
- ★ **Dror et al. 2018, _The Hitchhiker's Guide to Testing Statistical Significance in NLP_ (ACL)** —
  **解决的问题：什么时候该用什么检验，以及配对与多重比较该怎么处理。**
  虽然写给 NLP，**但它是这一整套方法论最好读的一份入门**，
  配对 bootstrap 的做法可以直接搬到 AP 上（注意以图/片段为单位重采样）。
- ★ **Sculley et al. 2015, _Hidden Technical Debt in Machine Learning Systems_ (NeurIPS)** —
  **解决的问题：ML 系统的复杂度到底藏在哪里。**
  数据依赖、反馈环、配置债、纠缠效应（CACE）。
  **本课「触发器偏差会被闭环自我强化」这条警告，就是它讲的隐藏反馈环在感知系统里的具体形态。**
- ★ **Sambasivan et al. 2021, _"Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI_ (CHI)** —
  **解决的问题：为什么数据问题总是被推迟，以及推迟的代价如何逐级放大。**
  **读完你会对模块 05 的门禁与血缘设计有完全不同的重视程度**；
  也是说服团队投入数据工作时最好用的一份材料。
- **Breck et al. 2017, _The ML Test Score: A Rubric for ML Production Readiness_ (IEEE Big Data)** —
  **解决的问题：怎样把「这个系统能不能上线」变成一份可打分的清单。**
  数据测试、模型测试、基础设施测试、监控四大类。**模块 05 发布门禁清单的模板来源。**
- **Zinkevich, _Rules of Machine Learning: Best Practices for ML Engineering_（Google, 在线）** —
  **解决的问题：工程实践里那些「没人写在论文里」的经验。**
  关于训练-服务偏斜、指标选择、以及「不要过早优化模型、先把数据管道做对」的建议非常中肯。
- **Recht et al. 2019, _Do ImageNet Classifiers Generalize to ImageNet?_ (ICML)** —
  **解决的问题：在同一个测试集上反复迭代，会不会把它「过拟合」掉。**
  结论既让人安心又让人警惕。**它是「黄金评测集必须冻结、且要定期换血」这条纪律的依据。**
- **Kirkpatrick et al. 2017, _Overcoming Catastrophic Forgetting in Neural Networks_ (EWC, PNAS)** —
  **解决的问题：持续学习时旧能力为什么会塌，以及怎么保住。**
  **模块 05 的立场是「工程上先用回放与配比解决，EWC 类方法是备选」**，但理解机制仍然必要。
- **Hestness et al. 2017, _Deep Learning Scaling is Predictable, Empirically_** 与
  **Kaplan et al. 2020, _Scaling Laws for Neural Language Models_** —
  **解决的问题：性能随数据量增长的形状是什么，以及能不能外推。**
  **模块 05 边际收益曲线 AP(n) ≈ a − b·n^(−c) 的形式来源**；
  同时也要记住外推超过 2–3 倍数据量就非常不可靠。
- **Kaufman et al. 2012, _Leakage in Data Mining: Formulation, Detection, and Avoidance_ (TKDD)** —
  **解决的问题：泄漏有哪些形态、为什么它能让离线指标假涨。**
  **模块 05「挖掘集与评测集污染」一节的系统性参考**；
  自动驾驶里最典型的形态是同一路段的相邻帧被分到训练与评测两侧，
  正确做法是按采集片段做 group split。

---

## 六 · 自动驾驶数据闭环的工程实践 · The AD Data Engine in Practice

> 这一组大多不是论文，而是工业演讲、技术博客与标准文件。
> **数据闭环的权威材料本来就在这里**——学术界很少发表「我们怎么组织标注预算」。

- ★ **Andrej Karpathy, _Building the Software 2.0 Stack_ / _Software 2.0_（Spark+AI Summit 演讲与同名文章）** —
  **解决的问题：为什么工程重心要从写代码转移到组织数据。**
  「Operation Vacation」（工程师去度假、系统靠数据自己变好）这个说法就出自这里。
  **本课「数据飞轮是护城河」这一主张最好的一份思想来源**，二十分钟的演讲，强烈建议看原视频。
- ★ **Tesla AI Day 2021 / 2022 中关于 data engine、triggers 与 auto-labeling 的部分** —
  **解决的问题：一个真实车队规模的闭环长什么样。**
  重点看它讲的**触发器设计**（车队里什么条件下回传片段）、影子模式、
  以及自动标注如何把人工标注的产出放大几个数量级。
  **模块 03 的触发器分类法与模块 04 的挖掘流水线，工业对照物就是它。**
  面试里被问「你了解量产的数据闭环吗」，这是最直接可引用的公开材料。
- ★ **Zhu et al. 2016, _Traffic-Sign Detection and Classification in the Wild_ (TT100K, CVPR)** —
  **解决的问题：给中国路况下的 TSR 一个真实的、长尾且小目标为主的基准。**
  10 万张全景图、3 万个标志实例，**类别频次跨越三个数量级，是典型的长尾**。
  **本课讨论「TSR 的类别分布」时的一手数据来源**（领域细节见 C55）。
- **Ertler et al. 2020, _The Mapillary Traffic Sign Dataset_ (ECCV)** —
  **解决的问题：跨国家、跨地区的标志体系差异与地域性长尾。**
  它清楚地展示了「长尾是**区域相关**的」——在德国常见的牌在中国是零样本，
  这直接影响模块 01 里 logit adjustment 的先验该用哪一份。
- **Waymo / nuScenes / Argoverse 的官方数据集论文与长尾挖掘技术博客** —
  **解决的问题：多传感器、多城市数据集的构建方法与场景标签体系。**
  重点看它们的**场景标签维度设计**（天气、时段、路况），
  可以直接作为模块 04 里 taxonomy 设计的参照。
- **Segment Anything 的 data engine（见上一组）与各家「auto-labeling」技术博客** —
  **解决的问题：模型辅助标注的三阶段如何逐步降低人工比例。**
  与 Tesla 的 auto-labeling 对照读，能看出同一套方法论在不同任务上的形态。
- **ISO 21448 (SOTIF) · 预期功能安全** —
  **解决的问题：当系统「没有故障」但因为感知能力不足而不安全时，怎么管理。**
  **它的核心是「已知不安全场景」与「未知不安全场景」的收敛**——
  这正是长尾挖掘在安全工程语言下的表述。
  **面试里能把 hard-case mining 与 SOTIF 联系起来，是明显的加分项。**
- **UN R157 (ALKS) 与各地区的自动驾驶法规文本（相关章节）** —
  **解决的问题：监管对场景覆盖与验证证据的要求。**
  它解释了为什么量产团队的评测集必须**按场景组织并可追溯**，
  也是模块 05 里「切片评测 + 数据血缘」在合规侧的动机。
- **Sculley et al.（见上一组）与各家 ML 平台的 feature/data store 文档** —
  **解决的问题：数据与特征的版本、血缘与复用如何在平台层实现。**
  平台层的完整讨论在 **C43**（数据工程）与 **C37**（MLOps），
  本课只用到它们的接口语义：**一次训练必须能唯一地指回一份不可变数据快照。**
- **各家关于 VLM 自动打标与数据筛选的工程博客（如用多模态模型做 caption / 属性标注的实践分享）** —
  **解决的问题：JD 里 "automated data mining workflows" 落到实处是什么样。**
  阅读时重点看两件事：**它们如何评估打标质量**，以及**哪些维度仍然保留人工复核**——
  这两点才是把 VLM 打标从演示变成生产系统的分界线。
