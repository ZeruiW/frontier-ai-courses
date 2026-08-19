# 参考清单 · References（检测工程实战与面试实务）

> 分主题列出。**★ = 必读**（读完这些，你能覆盖本课 80% 的内容，以及面试里「你怎么知道这个提升是真的」
> 「你怎么定位到这个原因」这两类追问的全部弹药）。
> 每条注明**它解决什么问题**，以及要重点看哪一节——这门课引用的很多是短文与博客，
> **它们的信噪比通常高于论文**，因为方法论本来就不适合写成论文。
>
> 与相邻课程的分工：**C40** 讲研究方法论与统计学通论；**C37** 讲实验跟踪与门禁的工程形态；
> **C18/C55** 讲检测指标本身的定义；**C60** 讲部署侧的一致性排查。
> **本课聚焦「判断结论是否成立、定位原因、把结论讲清楚」这三件事。**

---

## 一 · 检测误差分析与诊断 · Detection Error Analysis（模块 02 的骨架）

- ★ **Bolya, Foley, Hays, Hoffman 2020, _TIDE: A General Toolbox for Identifying Object Detection Errors_ (ECCV)** —
  **本课模块 02 的主文献。** 解决的问题是：mAP 是一个标量，它告诉你「差」但不告诉你「差在哪」。
  TIDE 把 mAP 的损失拆成 **Cls / Loc / Both / Dupe / Bkg / Miss** 六个互斥类型，
  并对每一类算出**修复收益**（把这类错全部改对，mAP 能涨多少）。
  **必读 §3 的误差定义与 §4 的 ΔAP 计算方式**——特别注意各类修复收益**不可相加**（它们互相重叠），
  只能用于相对排序。官方实现 `dbolya/tide`（`pip install tidecv`），本课 notebook 是它的从零复现版。
- ★ **Hoiem, Chodpathumwan, Dai 2012, _Diagnosing Error in Object Detectors_ (ECCV)** —
  TIDE 的思想源头，早了八年。它把 FP 分成**定位不准 / 相似类混淆 / 其他类 / 纯背景**四类，
  并系统性地分析了目标尺寸、遮挡、视角等属性对性能的影响。
  **它最有价值的结论是「不同类别的误差构成差异极大」**——所以只看整体分解是不够的，必须逐类看。
  没有工具链时，按这四类手工归档 100 个 FP，两小时就能得到方向。
- ★ **Lin et al. 2014, _Microsoft COCO_ + `cocoapi` 的 `cocoeval.py` 源码** —
  评测协议的一手来源。**代码比论文重要**：读 `COCOeval.evaluateImg` 你才会知道
  匹配是**按分数降序贪心**（不是匈牙利）、每个 GT 只能被匹配一次、`iscrowd` 区域如何被忽略、
  AP 用 101 点插值。**自己实现评测和官方对不上，九成是这几条里的某一条。**
  另外 `cocoapi` 里的 `analyze()` 能画出那套经典的七条曲线（逐步放宽约束看 AP 上限），
  本质就是 Hoiem 式分析的官方实现。
- ★ **Padilla et al. 2021, _A Comparative Analysis of Object Detection Metrics with a Companion Open-Source Toolkit_ (Electronics)** —
  解决「VOC mAP、COCO mAP、各家实现为什么算出来不一样」这个长期困惑。
  **把各种 AP 变体的定义差异列成了表**，是自己写评测代码时的对照手册，也是面试被问
  「COCO mAP 和 VOC mAP 的区别」时的完整答案来源。
- **Oksuz, Cam, Kalkan, Akbas 2020, _Imbalance Problems in Object Detection: A Review_ (TPAMI)** —
  把检测里的不平衡系统性地分成**类别不平衡 / 尺度不平衡 / 空间不平衡 / 目标不平衡**四类，
  每类都给出问题定义与已有解法的谱系。**做误差归因时，这张分类表能帮你把「为什么这类学不好」问到底。**
- **Oksuz et al. 2018/2021, _Localization Recall Precision (LRP) Error_** —
  提出一个把定位质量、召回、精度合成到一起的单一指标，**并且能直接给出最优工作点**。
  实用价值在于：AP 无法告诉你「该用哪个阈值上线」，LRP 的 oLRP 可以。**做工作点选择时值得一读。**
- **Everingham et al. 2015, _The PASCAL VOC Challenge: A Retrospective_ (IJCV)** —
  一份评测协议设计的复盘。**重点读它对「难例标注（difficult flag）与忽略区域」的讨论**，
  这直接对应 TSR 里「太小/太模糊/背面的标志怎么标、怎么评」这个必答问题。

---

## 二 · 切片评测、行为测试与系统性错误发现 · Slices & Behavioral Testing

- ★ **Ribeiro, Wu, Guestrin, Singh 2020, _Beyond Accuracy: Behavioral Testing of NLP Models with CheckList_ (ACL Best Paper)** —
  虽然是 NLP，但**方法论对检测完全可迁移，而且是本课最值得偷的一篇**。
  它把测试组织成「**能力 × 测试类型**」的矩阵（最小功能测试 / 不变性测试 / 方向性期望测试），
  强迫你在整体指标之外列出「模型应该具备的能力清单」。
  翻译到 TSR：不变性测试 = 加雨雾后类别不该变；方向性测试 = 目标变小时置信度应单调下降；
  最小功能测试 = 每个关键类都要有一个专属小集合。**面试里讲评测体系设计时引用它会非常出彩。**
- **Wu, Ribeiro, Heer, Weld 2019, _Errudite: Scalable, Reproducible, and Testable Error Analysis_ (ACL)** —
  解决「误差分析靠随手翻几个 case，结论不可复现也不可验证」的问题。
  核心主张：**把误差假设写成可执行的查询**（"所有宽度<32 且被遮挡的实例"），
  然后在全量数据上验证这个假设覆盖了多少误差。**这正是本课「分层抽样而非随便看」的理论表达。**
- **Eyuboglu et al. 2022, _Domino: Discovering Systematic Errors with Cross-Modal Embeddings_ (ICLR)** —
  解决「我不知道该按什么维度切片」这个更难的问题：用跨模态嵌入自动发现**成片失败的数据子群**。
  对 TSR 的意义很直接——你事先想不到"隧道出口逆光 + 蓝底指路牌"这种组合，但它能被自动挖出来。
  与 C58 的挖掘基础设施是同一条技术线。
- **d'Eon et al. 2022, _The Spotlight: A General Method for Discovering Systematic Errors in Deep Learning Models_ (FAccT)** —
  同类问题的另一条路：在表示空间里找一个连续区域，使得该区域内的损失显著偏高。
  **比 Domino 更简单、无需额外模态**，工程上更容易先落地。
- **Chen et al. 2019, _Slice-based Learning_ (NeurIPS)** —
  不只是「按切片评测」，而是**让模型对关键切片专门建模**。
  在 TSR 这种「少数关键类别决定安全」的场景里，这个思路比单纯加权更有结构。
- **Voxel51 `fiftyone` 文档与 `Detection Evaluation` 教程** —
  ★ 工程上最省时间的一个工具：把预测与 GT 一起加载，按 FP/FN/IoU/尺寸/自定义标签**交互式筛选并可视化**。
  **它解决的是「分层抽样看 badcase」的最后一公里**——写脚本能算出该看哪些，但翻图还是要工具。

---

## 三 · 实验设计、方差与统计 · Experiment Design & Statistics（模块 01 的骨架）

- ★ **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_ (MLSys)** —
  **本课模块 01 最重要的一篇。** 它系统性地量化了各种随机源（权重初始化、数据顺序、数据划分、
  超参搜索、非确定性算子）各自贡献了多少方差，并给出一个关键结论：
  **只固定种子重跑得到的方差，会严重低估真实的方法间比较所需的方差估计**；
  作者给出的实践建议是**随机化尽可能多的来源并做多次重复**，而不是把一切都固定死。
  **§4 的方差分解图是这门课所有数字的来源。**
- **Bouthillier, Laurent, Vincent 2019, _Unreproducible Research is Reproducible_ (ICML)** —
  只有几页，但把「可复现（同代码同结果）」与「结论可重复（换个随机化仍成立）」的区别讲透了。
  **结论是刺人的：一个完全可复现的实验，其结论可能完全不可重复。** 值得在做门禁设计前读一遍。
- ★ **Henderson et al. 2018, _Deep Reinforcement Learning that Matters_ (AAAI)** —
  虽然是 RL，但**它对「种子方差如何伪装成算法提升」的演示是所有领域里最震撼的**：
  同一算法不同种子分成两组，两组之间的"差异"看起来完全像是两个不同的算法。
  **面试里要举例说明「+0.3 可能是噪声」时，这篇是最有力的引用。**
- ★ **Dodge et al. 2019, _Show Your Work: Improved Reporting of Experimental Results_ (EMNLP)** —
  解决「不同调参预算下的对比无效」这个最普遍的不公平。
  它提出报告**「期望最大性能 vs 超参搜索预算」曲线**而不是单个最好结果，
  一张图就能看出「A 比 B 好」到底是方法好还是搜得多。**这是「同调参预算」这条规则的正式依据。**
- **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping_** —
  量化了「只换初始化和数据顺序」能造成多大的最终指标差异（结论：大到足以逆转论文排名）。
  **迁移到检测：同一份配置多跑几个种子再下结论，成本远低于一次错误的技术决策。**
- **Colas, Sigaud, Oudeyer 2018, _How Many Random Seeds? Statistical Power Analysis in Deep RL Experiments_** —
  **把「跑几个种子」这个问题正式化的一篇**：给定想检出的效应量与方差，用功效分析反推种子数，
  并强调**事后功效分析**对解释阴性结果的必要性。本课 01 的功效分析小节直接对应它。
- ★ **Benjamini & Hochberg 1995, _Controlling the False Discovery Rate_ (JRSS-B)** —
  多重比较校正的现代标准。**为什么不用 Bonferroni**：消融场景下你要的是「宣称显著的那批里假的比例可控」，
  而不是「一个假阳性都不能有」。**算法本身只有五行**（p 值升序、找最大的 k 满足 p₍k₎ ≤ k·q/m），
  notebook 里会实现。面试里能说清 FWER 与 FDR 的区别是很强的信号。
- ★ **Dror, Baumer, Shlomov, Reichart 2018, _The Hitchhiker's Guide to Testing Statistical Significance in NLP_ (ACL)** —
  **一份可以照着做的决策流程图**：指标是什么类型 → 数据是否配对 → 该用哪种检验。
  对 mAP 这种非均值型指标，它明确指向 **bootstrap / 置换检验**而不是 t 检验，理由讲得很清楚。
- **Berg-Kirkpatrick, Burkett, Klein 2012, _An Empirical Investigation of Statistical Significance in NLP_ (EMNLP)** —
  配对 bootstrap 检验在机器学习评测里的经典实践依据，**给出了"多大的差异在多大测试集上才可信"的经验表**。
- **Demšar 2006, _Statistical Comparisons of Classifiers over Multiple Data Sets_ (JMLR)** —
  多个方法 × 多个数据集时的正确比较方式（Friedman 检验 + Nemenyi 后验）。
  **当你要同时比较 4 个检测器在 6 个切片上的表现时，这篇是唯一正确的做法来源。**
- **Efron & Tibshirani 1993, _An Introduction to the Bootstrap_** —
  bootstrap 的原始教材。只需要读**前三章 + 配对/分层重采样那一节**：
  为什么重采样的对象是「评测样本」而不是「模型」，以及分层 bootstrap 在类别不平衡下的必要性。
- **Cohen 1992, _A Power Primer_ (Psychological Bulletin)** —
  三页纸讲清效应量与功效的关系，附常用样本量表。**这是最快建立"统计显著 ≠ 工程重要"直觉的材料。**

---

## 四 · 为什么很多「提升」是假的 · Rigor & the Winner's Curse

- ★ **Sculley, Snoek, Wiltschko, Rahimi 2018, _Winner's Curse? On Pace, Progress, and Empirical Rigor_ (ICLR Workshop)** —
  **只有四页，是本课价值密度最高的一篇。** 核心论点：在追求 SOTA 的竞赛压力下，
  被选出的「最好结果」系统性地被高估，而**消融不充分、调参预算不对等、缺少方差报告**是三大帮凶。
  它提出的补救措施（调优对照、消融、误差分析、可复现性）几乎就是本课 01+02 的大纲。
- ★ **Lipton & Steinhardt 2018, _Troubling Trends in Machine Learning Scholarship_** —
  点名四种坏模式：**解释与推测混淆、无法定位收益来源（failure to identify the sources of empirical gains）、
  用数学装点而非说明、术语滥用**。第二条正是本课「归因」这条主线的反面教材。
  **它对「不要把提升归给你最想讲的那个部件」的论证，可以直接用在面试答辩里。**
- ★ **Musgrave, Belongie, Lim 2020, _A Metric Learning Reality Check_ (ECCV)** —
  把一个领域十年的"进步"在统一的公平协议下重测，结论是**大部分提升在控制了训练设置后消失了**。
  **它是"公平对比的五个同"最完整的实证案例**，也是「你怎么保证对比公平」这个追问的标准回答素材。
- **Dacrema, Cremonesi, Jannach 2019, _Are We Really Making Much Progress?_ (RecSys Best Paper)** —
  推荐系统版的同一故事：18 篇神经推荐论文里只有 7 篇能复现，其中多数被简单基线打败。
  **要点是「基线是否被认真调过」——这也是面试官问你 baseline 时真正想确认的事。**
- **Recht, Roelofs, Schmidt, Shankar 2019, _Do ImageNet Classifiers Generalize to ImageNet?_ (ICML)** —
  重新采集一个同分布测试集，所有模型都掉点，但**排名基本保持**。
  这个双重结论很重要：**绝对数字不可迁移，相对排序相对稳健**——它决定了你该怎么引用别人的数字。
- **Gorman & Bedrick 2019, _We Need to Talk about Standard Splits_ (ACL)** —
  证明「换一个随机划分，方法排名就变」。对应到自动驾驶：**按帧随机划分几乎必然泄漏**，
  按路段/时间划分才有意义，而换个划分方式结论可能翻转。
- **Ioannidis 2005, _Why Most Published Research Findings Are False_ (PLoS Medicine)** —
  经典中的经典。**读它的第一节就够**：结论的可信度取决于先验命中率、功效与检验数量，
  而不只是 p 值。**它是理解「多重比较为什么致命」的最短路径。**

---

## 五 · 调试手册与训练诊断 · Debugging Playbooks（模块 03 的骨架）

- ★ **Karpathy 2019, _A Recipe for Training Neural Networks_（博客）** —
  **本课模块 03 的精神源头，也是这门课唯一一篇「必须整篇读完」的材料。**
  核心主张：神经网络训练是**泄漏的抽象**，失败通常不报错，只是静默地变差；
  因此必须按「与数据做朋友 → 端到端骨架 + 固定基线 → 过拟合 → 正则化 → 调参 → 榨干」的顺序推进，
  每一步都带可验证的断言。**「先把一个 batch 过拟合」「先跑通一个最蠢的基线」都出自这里。**
- ★ **Karpathy, _Most Common Neural Net Mistakes_（推文清单）** —
  五分钟能读完的一张清单：忘了 `zero_grad`、train/eval 模式弄错、loss 没做 batch 归约、
  数据增强用在了验证集上……**看起来都是低级错误，但它们占了真实事故的大半**，
  而本课模块 03 的诊断树就是把这类清单结构化的产物。
- ★ **Josh Tobin, _Troubleshooting Deep Neural Networks_（Full Stack Deep Learning 讲义）** —
  **最系统的一份调试方法论**：把调试分成「先跑起来 → 与基线对齐 → 评估与误差分析 → 改进模型/数据 → 调参」，
  并给出每个阶段的常见 bug 清单与判定方法。**它对「模型 bug、数据 bug、超参问题」三者的区分标准，
  正是本课诊断树的分支依据。**
- **Zinkevich, _Rules of Machine Learning: Best Practices for ML Engineering_（Google）** —
  43 条规则，解决「什么时候该用 ML、监控该怎么设、指标该怎么选」。
  **对本课最相关的是「先做端到端的可监控管线，再优化模型」这一组规则**，
  它是 C37 与本课交叉的地方。**面试讲系统设计时可以直接借它的结构。**
- **Breck, Cai, Nielsen, Salib, Sculley 2017, _The ML Test Score: A Rubric for ML Production Readiness_ (IEEE Big Data)** —
  把「这个模型能不能上线」变成一张可打分的清单（数据测试、模型测试、基础设施测试、监控测试）。
  **对应 JD 里的 regression testing 与 model version management，是回答「你们怎么保证质量」的现成骨架。**
- **Sculley et al. 2015, _Hidden Technical Debt in Machine Learning Systems_ (NeurIPS)** —
  「胶水代码、管线丛林、配置债、纠缠（CACE：改变任何一处会改变一切）」。
  **CACE 原则是本课「单变量原则总被破坏」的系统层解释**——它说明这不是纪律问题，而是结构问题。
- ★ **PyTorch 官方文档：_Reproducibility_ / `DistributedSampler.set_epoch` / `torch.amp` 疑难解答** —
  解决模块 03 里最具体的那批坑：cuDNN 确定性开关与它的性能代价、
  **多卡训练忘记 `set_epoch` 会导致每个 epoch 数据顺序完全相同**、
  GradScaler 反复 skip step 意味着前向已经溢出。**这些都是不读文档就一定会踩的。**
- **NVIDIA `framework-determinism`（原 `tensorflow-determinism`）仓库** —
  列出了哪些算子是非确定性的、怎么替换。**在排查"同种子两次结果不同"时，这份清单能直接省掉一天。**
- **Ng, _Machine Learning Yearning_（免费电子书）** —
  **它对「误差分析」的操作化讲得比任何论文都清楚**：手工过 100 个 badcase、按原因打勾统计、
  用"上限分析（ceiling analysis）"决定投入哪个模块。**级联式 TSR 系统（检测 + 分类）正是上限分析的教科书场景。**

---

## 六 · 交付纪律：文档、数据与可复现 · Delivery Discipline

- ★ **Mitchell et al. 2019, _Model Cards for Model Reporting_ (FAT*)** —
  解决「模型交付时只有一个 mAP 数字，没人知道它在什么条件下会失效」。
  模型卡要求写明用途、训练数据、**分组评测结果**、已知局限与不适用场景。
  **对 TSR 这类安全相关系统，分组结果（按尺寸/光照/天气/区域）是模型卡的核心而非附录。**
  面试里说"我会给每个上车模型写一张模型卡"，是很强的工程成熟度信号。
- ★ **Gebru et al. 2021, _Datasheets for Datasets_ (CACM)** —
  解决「数据集的偏差在使用时已经不可追溯」。要求记录采集动机、采集方式、构成、清洗、标注流程与已知偏差。
  **TSR 场景的直接对应**：采集车相机型号与 ISP 配置、采集城市与季节分布、
  哪些类别是补采的、标注规范的版本号——**没有这些，跨域掉点将永远无法解释。**
- ★ **Sambasivan et al. 2021, _"Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI_ (CHI)** —
  访谈高风险 AI 从业者后得出的结论：**上游数据问题会在下游被放大成级联故障，且往往在部署后才暴露**。
  论文里的案例大量来自医疗与自动驾驶。**它给了你一套讲"为什么我把时间花在数据上"的、有引用的语言。**
- **Northcutt, Athalye, Mueller 2021, _Pervasive Label Errors in Test Sets_ (NeurIPS D&B) 与 Northcutt et al. 2021, _Confident Learning_ (JAIR)** —
  解决「测试集本身就是错的怎么办」：给出估计标签噪声、自动定位可疑标注的方法。
  **实测结论很刺眼——主流数据集测试集平均有约 3.4% 的标签错误，且纠正后模型排名会变。**
  在 TSR 上意义更大：小目标 ±2 px 的标注误差就是 25% 的相对误差。
- **Pineau et al. 2021, _Improving Reproducibility in Machine Learning Research_ (JMLR) 与 ML Reproducibility Checklist** —
  NeurIPS 复现性计划的完整复盘，附一份可直接使用的清单。
  **本课 01 的「实验记录最小必要字段」就是这份清单的工程精简版。**
- **Gundersen & Kjensmo 2018, _State of the Art: Reproducibility in Artificial Intelligence_ (AAAI)** —
  量化了「有多少论文提供了足以复现的信息」（答案很低）。
  **用来说明"记录数据版本与环境指纹"不是形式主义，而是行业普遍失败的地方。**

---

## 七 · 叙事、写作与技术沟通 · Narrative & Communication（模块 04）

- ★ **Minto, _The Pyramid Principle_** —
  **结论先行 + 下挂 3 条互斥且穷尽的支撑**。它给的不只是表达技巧，更是**思考的检查表**：
  如果三条支撑互相重叠，说明你的拆解还没想清楚。系统设计题的答案结构可以直接套。
  只需要读**前两部分**（自上而下的表达、逻辑顺序），后面的写作细节可跳。
- ★ **Simon Peyton Jones, _How to Write a Great Research Paper_ / _How to Give a Great Research Talk_（讲座与幻灯）** —
  解决「有内容但讲不清楚」。核心可迁移点：**先讲问题再讲方案、用一个具体例子贯穿全篇、
  明确说出你的贡献是什么（不要让听众自己找）**。
  **把"论文"换成"项目叙事"，这套方法一字不用改。**
- **Malte Ubl / Google, _Design Docs at Google_（工程文化文章）** —
  解决「决策三个月后没人记得为什么」。设计文档的价值不在文档本身，
  而在**它强迫你在动手前写下备选方案与拒绝理由**。
  **面试里描述你的工作方式时，"我会先写一页设计文档列出三个方案和拒绝理由"是很有说服力的一句。**
- **Heinrich Hartmann, _Writing for Engineers_（博客）** —
  很实用的一篇：为什么工程师的写作应该**从结论开始、用主动语态、把数据放进句子里**。
  **配合上面的金字塔原理读，一小时能显著改善周报与技术方案的可读性。**
- **Chip Huyen 2022, _Designing Machine Learning Systems_ (O'Reilly)** —
  ★ **重点读第 6 章（模型开发与离线评测）与第 9 章（持续学习与线上测试）**：
  它把「离线指标好但线上不好」的原因拆得很细，且**大量内容与本课 01/02 直接呼应**。
  也是面试系统设计题最好用的一本通用参考。
- **Amazon 的 STAR 行为面试材料与「6-pager」写作文化（公开资料）** —
  STAR 的原始语境。**要点是 Action 必须是"我"做的具体动作，Result 必须可量化**；
  国内大厂的行为面试基本沿用同一套结构。

---

## 八 · 面试实务与岗位准备 · Interview Practice（模块 05）

- ★ **Chip Huyen, _Introduction to Machine Learning Interviews_（免费电子书 + GitHub 题库）** —
  **覆盖面最全的一份中文/英文可用的 ML 面试准备材料**：从流程、准备节奏到 200+ 道题。
  **重点用它的「数学与 ML 基础」两章做检索式自测**，而不是从头读——
  你的检测专业知识已经由 C53–C60 覆盖，这里补的是通用面。
- **Aminian & Xu 2023, _Machine Learning System Design Interview_** —
  解决「ML 系统设计题不知道怎么组织答案」：给出一个稳定的六步框架
  （澄清需求 → 指标定义 → 数据 → 模型 → 评测 → 部署与监控）。
  **把这个框架套到「设计一个 TSR 闭环」上，就是模块 05 那道压轴题的骨架。**
- **`torchvision.ops.nms` / `mmcv.ops.nms` 的源码，以及 `torchvision.ops.box_iou`** —
  ★ **白板题的官方对照物**。自己手写完之后，一定要和这两处的实现对拍：
  重点看**边界处理（零面积、包含关系）、分数并列时的顺序、batched_nms 的类别偏移技巧**。
  面试官如果做过检测，会顺着问 batched NMS 的偏移量为什么必须大于图像最大边长。
- ★ **本仓库的 `INTERVIEW_PREP_XPENG_TSR.md`** —
  这份 JD 拆解文档是 C53–C61 全部九门课的起点：7 个能力块、9 个缺口、18 道高概率面试题。
  **面试前最后一遍复习应该从它开始，而不是从任何一门课开始**——先确认覆盖，再补深度。
- **XPENG 公开的技术分享（XNGP、图灵芯片、端到端与 VLA 路线的发布会与技术博客）** —
  ★ **面试前一周务必搜一遍最新的**。它解决的问题是：让你的回答能落到**这家公司的技术语境**里
  （例如他们把 VLA 放在什么位置、车端算力大概什么量级）。
  **在反问环节引用对方最近的公开分享，是最有效的一种准备信号。**
- **Karpathy 的 Tesla 数据引擎相关演讲（CVPR 2021 Workshop on Autonomous Driving、Tesla AI Day）** —
  解决「数据闭环叙事怎么讲得像干过」：影子模式触发、场景标签、单元测试式的评测集、
  「Operation Vacation」式的自动化目标。**它是 C58 那套闭环最好的行业级参照，也是叙事的素材库。**
- **各公司公开的检测/感知岗面经与 `leetcode` 上的 IoU/NMS 类题目** —
  **不是用来押题，而是用来校准题目的形态与时长**：白板题通常 15–20 分钟一道，
  意味着你必须在 5 分钟内写完主逻辑，把剩下的时间留给边界情况与追问。

---

## 九 · 内部索引：前八门课在这门课里怎么用 · Course Cross-Index

> 这门课不产生新的技术素材。下表给出「当你需要某类素材时，回去翻哪一门课的哪一节」。

| 需要什么 | 去哪找 | 在本课的用途 |
|---|---|---|
| 选型的延迟-精度账、帕累托前沿 | **C53-05** | 叙事里「为什么选 X 不选 Y」；系统设计题的算力约束段 |
| 标签分配演进与收益归因 | **C53-02** | 白板题之外最常见的架构追问；归因能力的展示素材 |
| 匈牙利匹配的完整实现 | **C54-01** | 模块 05 的第四道白板题；DETR 系追问的地基 |
| 集合损失与一对一 vs 一对多 | **C54-02 / C54-04** | 「DETR 为什么不需要 NMS」的完整答案链 |
| TSR 失效模式清单 | **C55-03** | 叙事的 Situation 段；误差分析的切片维度设计 |
| 安全导向评测（FP/km、分桶、门禁） | **C55-05** | 模块 02 的工作点选择；「mAP 不够用怎么办」 |
| 增强的消融与验证方法 | **C56-05** | 模块 01 的实验设计范例（它本身就是一次完整消融） |
| IoU 位移敏感性、像素尺寸物理推导 | **C57-01 / C57-05** | 「小目标为什么难」的定量回答；Task 段的约束量化 |
| 数据闭环全流程与边际收益曲线 | **C58-05** | 叙事的「下一步」段；系统设计题的闭环骨架 |
| VLA 接口与置信度传递 | **C59-03** | JD 独有条目的针对性准备 |
| 一致性排查 checklist、INT8 掉点决策树 | **C60-01 / C60-03** | 部署题的两道高频题；叙事里的「代价」段 |
| p50/p99 延迟与端到端分解 | **C60-05** | 成对指标里「代价」那一半的具体数字来源 |
| 实验跟踪与门禁的工程形态 | **C37-01 / C37-03** | 本课 01 的记录 schema 落地成工具时看它 |
| 统计检验的一般原理 | **C40-03** | 本课 01 的理论背景（本课只讲检测特化部分） |
