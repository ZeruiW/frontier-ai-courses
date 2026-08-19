# 参考清单 · References（ML/DL 技术知识问答）

> ★ 标必读。每条注明"解决什么问题"——这份清单不是让你把论文通读一遍，
> 而是让你在被追问"这个结论有没有依据"时，知道**这不是我编的，是有原始出处的**，
> 需要时也能自己去查原文补深度。本课把这些材料重新组织成了"三段式答法"的原材料。

---

## 一 · 综合教材：知识体系的骨架 · Foundational Textbooks

- ★ **Goodfellow, Bengio & Courville, _Deep Learning_（MIT Press, 2016，免费在线版）** —
  解决"这些零散知识点该按什么体系组织起来"。**第 5 章（Machine Learning Basics）对应本课 01 模块的
  偏差-方差、正则化、维度灾难；第 8 章（Optimization for Training Deep Models）对应 02 模块的优化器与
  初始化；第 9 章（Convolutional Networks）对应 03 模块的卷积/感受野部分**。这本书至今仍是"讲得清为什么"
  而不是"罗列是什么"的最权威公开教材。
- ★ **Bishop, _Pattern Recognition and Machine Learning_（Springer, 2006）** —
  解决"偏差-方差分解、生成式 vs 判别式模型的数学根基从哪来"。**第 1.5 节和第 3 章**给出了
  偏差-方差分解最经典的推导，是本课 01 模块的数学底本（推导细节见 C07，本课只取结论）。
- **Hastie, Tibshirani & Friedman, _The Elements of Statistical Learning_（Springer, 第 2 版，免费在线版）** —
  解决"bagging/boosting/正则化路径这些经典统计学习方法的完整理论"。**第 7 章（Model Assessment and
  Selection）、第 8.7 节（Bagging）、第 10 章（Boosting）**是本课 01 模块相应词条的原始理论依据。

---

## 二 · 泛化、正则化与双下降 · Generalization & Double Descent

- ★ **Belkin, Hsu, Ma & Mandal, "Reconciling modern machine-learning practice and the classical
  bias–variance trade-off"（PNAS, 2019）** —
  解决"为什么深度学习里模型越大有时反而泛化越好，经典 U 形曲线为什么会被打破"。
  **这是"双下降"现象最早被系统性提出并命名"插值阈值（interpolation threshold）"的论文**，
  本课 01 模块讲双下降时引用的核心是它的实验框架。
- ★ **Nakkiran, Kaplan, Bansal, Yang, Barak & Sutskever, "Deep Double Descent: Where Bigger Models
  and More Data Can Hurt"（ICLR 2020）** —
  解决"双下降不只在模型容量维度出现，在训练轮数和数据量维度上是否也存在"。
  **本课 01 模块的双下降数值实验直接对应这篇论文的"model-wise / epoch-wise double descent"框架**。
- **Srivastava, Hinton, Krizhevsky, Sutskever & Salakhutdinov, "Dropout: A Simple Way to Prevent
  Neural Networks from Overfitting"（JMLR, 2014）** —
  解决"怎么用一个简单机制近似训练指数级数量的子网络集成"。**dropout 的集成学习视角与 inverted dropout
  的推理期缩放细节，都来自这篇原论文**，是本课 01 模块 dropout 词条的直接出处。
- **Breiman, "Bagging Predictors"（Machine Learning, 1996）** 与
  **Freund & Schapire, "A Decision-Theoretic Generalization of On-Line Learning and an Application
  to Boosting"（AdaBoost 原论文，JCSS, 1997）** —
  分别解决"怎么用重采样降方差"和"怎么用串行加权纠错降偏差"。**这两篇是本课"bagging 降方差、boosting
  降偏差"这句话的最早出处**，随机森林（Breiman, 2001）和 GBDT 都是它们的后续发展。
- **Cawley & Talbot, "On Over-fitting in Model Selection and Subsequent Selection Bias in Performance
  Evaluation"（JMLR, 2010）** —
  解决"为什么在同一份数据上既调参又报告性能会导致系统性偏高的评估结果"。
  **本课 01 模块讲嵌套 CV 时的核心论据就是这篇论文对"选择偏差"的系统性论证**。

---

## 三 · 优化与训练 · Optimization & Training

- ★ **Loshchilov & Hutter, "Decoupled Weight Decay Regularization"（AdamW 原论文，ICLR 2019）** —
  解决"为什么 Adam 里直接加 L2 惩罚项和真正的 weight decay 效果不一样"。
  **这是本课 02 模块"weight decay 解耦"词条的唯一权威出处**——论文里给出了 L2 惩罚被自适应学习率
  重新缩放导致正则化强度不一致的完整论证，是面试被追问到深处时最值得引用的一篇。
- **Kingma & Ba, "Adam: A Method for Stochastic Optimization"（ICLR 2015）** —
  解决"怎么把动量和自适应学习率结合起来，并修正训练早期的偏差"。**Adam 的一阶/二阶矩偏差修正公式
  出自这篇原论文**，是理解 warmup 为何在 Adam 上依然必要的数学起点。
- **Goyal et al., "Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour"（Facebook, 2017）** —
  解决"大 batch 训练怎么在不损失精度的前提下加速"。**本课 02 模块"批大小与泛化"和 warmup 词条
  引用的线性缩放规则（learning rate 随 batch size 等比例放大）与 warmup 实践细节均来自这篇论文**。
- **Glorot & Bengio, "Understanding the Difficulty of Training Deep Feedforward Neural Networks"
  （Xavier 初始化原论文，AISTATS 2010）** 与
  **He, Zhang, Ren & Sun, "Delving Deep into Rectifiers: Surpassing Human-Level Performance on
  ImageNet Classification"（He/Kaiming 初始化原论文，ICCV 2015）** —
  分别解决"tanh/sigmoid 网络"和"ReLU 网络"该怎么设定初始化方差才能让前向激活方差保持稳定。
  **本课 02 模块两条初始化词条的推导直觉与"补偿因子 2"的具体数字都出自这两篇原论文**。
- **Micikevicius et al., "Mixed Precision Training"（NVIDIA/百度联合团队, ICLR 2018）** —
  解决"fp16 训练怎么避免小梯度值下溢为 0"。**loss scaling 机制的完整设计与实验依据来自这篇论文**，
  是本课 02 模块混合精度词条的直接出处。

---

## 四 · 架构：归一化、残差与注意力 · Architectures

- ★ **Ioffe & Szegedy, "Batch Normalization: Accelerating Deep Network Training by Reducing
  Internal Covariate Shift"（ICML 2015）** —
  解决"怎么让每层输入的分布在训练中保持稳定，从而允许更大学习率、加速收敛"。
  **本课 03 模块 BN 词条的训练/推理行为差异描述直接来自这篇原论文**，"internal covariate shift"
  这个动机解释虽然后续有争议（见下方 Santurkar et al.），但仍是理解 BN 历史地位的起点。
- ★ **Ba, Kiros & Hinton, "Layer Normalization"（2016）** —
  解决"序列长度可变、batch 内统计量不稳定时该怎么做归一化"。**本课 03 模块"Transformer 为什么用 LN
  而不是 BN"这一结论的原始出处**，论文明确指出 LN 不依赖 batch 维度是其适用于 RNN/Transformer 的关键。
- **Wu & He, "Group Normalization"（ECCV 2018）** —
  解决"检测/分割这类小 batch 任务里 BN 性能明显下降的问题"。**本课 03 模块"BN 在小 batch 下失效、
  GN 作为替代方案"的实验依据来自这篇论文**，其中展示了 GN 性能不随 batch size 剧烈波动的对比实验。
- **Santurkar, Tsipras, Ilyas & Madry, "How Does Batch Normalization Help Optimization?"（NeurIPS 2018）** —
  解决"BN 真正起作用的原因是不是 Ioffe & Szegedy 说的 internal covariate shift"。
  **这篇论文提出 BN 真正的作用更可能是让损失曲面更平滑**，是"什么时候原始解释会失效"这一边界意识
  的绝佳案例，被追问 BN 深层机制时值得提及。
- ★ **He, Zhang, Ren & Sun, "Deep Residual Learning for Image Recognition"（ResNet 原论文，CVPR 2016）** —
  解决"怎么训练几十上百层的深度网络而不出现退化问题"。**本课 03 模块"残差连接"词条的梯度视角
  直接出自这篇原论文**；集成视角的互补解释见下一条。
- **Veit, Wilber & Belongie, "Residual Networks Behave Like Ensembles of Relatively Shallow Networks"
  （NeurIPS 2016）** —
  解决"残差网络为什么删掉个别模块不会彻底崩溃"。**本课 03 模块"残差连接的集成视角"这半句话
  的原始出处**，与梯度视角互补，两者合起来才是这道题的完整答案。
- ★ **Vaswani et al., "Attention Is All You Need"（NeurIPS 2017）** —
  解决"怎么完全用注意力机制替代循环结构做序列建模"。**本课 03 模块 scaled dot-product attention、
  多头注意力、正余弦位置编码三个词条全部直接出自这篇原论文**，包括除以 √d_k 的动机说明
  （"we suspect that for large values of d_k, the dot products grow large in magnitude"）。
- **Howard et al., "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications"
  （2017）** 与 **Chollet, "Xception: Deep Learning with Depthwise Separable Convolutions"（CVPR 2017）** —
  解决"怎么用更少参数和计算量达到接近标准卷积的精度"。**本课 03 模块深度可分离卷积词条的
  参数量对比数字来自这两篇论文**，是车端部署场景的架构基础。
- **Luo, Li, Urtasun & Zemel, "Understanding the Effective Receptive Field in Deep Convolutional
  Neural Networks"（NeurIPS 2016）** —
  解决"理论感受野和网络实际用到的信息范围是不是一回事"。**本课 03 模块"有效感受野远小于理论
  感受野，且呈高斯状衰减"这一结论的原始实验依据**。

---

## 五 · 评估、校准与实验方法论 · Evaluation, Calibration & Experimentation

- ★ **Guo, Pleiss, Sun & Weinberger, "On Calibration of Modern Neural Networks"（ICML 2017）** —
  解决"为什么现代深度网络精度很高但置信度普遍过度自信，以及怎么用最简单的方法修正"。
  **本课 04 模块校准、可靠性图、ECE、温度缩放四个词条全部直接出自这篇论文**——
  论文核心发现是"模型容量和训练时长增加会让校准变差，即使精度在变好"，是"精度和置信度可信度
  是两件独立的事"这一论点最有力的实证来源。
- ★ **Davis & Goadrich, "The Relationship Between Precision-Recall and ROC Curves"（ICML 2006）** —
  解决"ROC 曲线和 PR 曲线到底是什么关系，为什么不平衡数据下二者的结论会分歧"。
  **本课 04 模块"ROC-AUC vs PR-AUC"词条的理论依据直接来自这篇论文**，其中证明了一条曲线上的
  支配关系在另一条曲线上不一定保持，这是"ROC-AUC 会撒谎"这句话背后的严格数学论证。
- **Wilson, "Probable Inference, the Law of Succession, and Statistical Inference"（JASA, 1927）**
  以及现代综述 **Brown, Cai & DasGupta, "Interval Estimation for a Binomial Proportion"
  （Statistical Science, 2001）** —
  解决"二项比例的置信区间在小样本或极端比例下该怎么算才不失真"。**本课 04 模块 Wilson 区间词条
  直接出自 Wilson 原始 1927 年论文，Brown et al. 的综述则系统对比了正态近似区间在这些场景下
  的失效模式**，是本课"三种置信区间不能任选其一"这一论点的权威依据。
- ★ **Kohavi, Tang & Xu, _Trustworthy Online Controlled Experiments_（Cambridge University Press, 2020）** —
  A/B 测试领域公认的权威教材，解决"怎么把一次线上实验的样本量、功效、多重比较都做对"。
  **本课 04 模块 A/B 样本量与功效、新奇效应、多重比较三个词条均引用这本书的框架**（与 C63 的引用
  同源，但本课只取"这些概念该怎么用一句话讲清楚"，完整实验设计方法论见 C63）。
- **Kohavi, Longbotham, Sommerfield & Henne, "Controlled experiments on the web: survey and
  practical guide"（Data Mining and Knowledge Discovery, 2009）** —
  上一本书的早期综述版，**给出了新奇效应、样本比例不匹配（SRM）等 A/B 测试陷阱的简明清单**，
  是快速建立直觉的更短路径。

---

## 六 · 概率与统计陷阱的经典来源 · Classic Statistical Pitfalls

- ★ **Simpson, "The Interpretation of Interaction in Contingency Tables"（JRSS-B, 1951）** —
  解决"分组内趋势一致，汇总后趋势却反转"这一现象最早的严格统计学描述。
  **本课 04 模块辛普森悖论词条的最早出处**，Judea Pearl 在《The Book of Why》（Basic Books, 2018）
  里用因果图（DAG）重新解释了这个悖论产生的因果结构，是更直观的现代补充读物。
- ★ **Mangel & Samaniego, "Abraham Wald's Work on Aircraft Survivability"（JASA, 1984）** —
  解决"幸存者偏差"这个概念最广为流传的历史案例——二战时期统计学家 Abraham Wald 指出
  应该加固返航飞机弹孔少的部位（因为弹孔多的部位中弹后飞机大多没能返航）。
  **本课 04 模块幸存者偏差词条的经典叙事直接来自这篇论文对 Wald 原始分析的还原**。
  应用于本课语境：数据采集流程本身可能隐含类似的"只看到跟踪成功的目标"式偏差。
- ★ **Ioannidis, "Why Most Published Research Findings Are False"（PLOS Medicine, 2005）** —
  解决"为什么大量看起来统计显著的科研结论无法被独立重复验证"。**本课 04 模块 p-hacking 词条
  的核心论据来自这篇论文对多重比较、灵活分析路径、发表偏倚等因素的系统性归因**，
  是"可复现性危机"这个话题最常被引用的一篇。
- **Head, Holman, Lanfear, Kahn & Jennions, "The Extent and Consequences of P-Hacking in Science"
  （PLOS Biology, 2015）** —
  解决"p-hacking 到底有多普遍、能不能通过分析已发表 p 值的分布检测出来"。
  是 Ioannidis 那篇更偏理论论证的实证补充，**本课把它作为"p-hacking 不是危言耸听而是可测量现象"
  的佐证材料**。

---

## 七 · 本库内的交叉引用 · Cross-References

- **C07 · ML 基础与面试数学** — softmax 梯度、贝叶斯公式、k-fold 方差等**数学推导**。
  **本课 01–04 模块用到的所有需要"手推"的公式，完整推导过程都在 C07，本课只给结论和三段式答法**，
  这是本课与 C07 分工最核心的一条：C07 是推导层，本课是表达层。
- **C13 · 强化学习地基** / **C41 · 深度强化学习** — MDP/Bellman、Q-learning、策略梯度、DQN、PPO/SAC
  等 RL 完整推导与实现。**本课不覆盖 RL 专项问答**，被问到时指向这两门课。
- **C18 · 计算机视觉** — 图像滤波、分类、检测、分割、自监督的**完整任务实现**。
  本课 03 模块讲的是卷积/归一化/attention 等**架构机制的广度问答**，C18 讲的是把这些机制组装成
  完整可跑的 CV 系统，两者互相引用但不重复实现细节。
- **C53–C61 · TSR/检测专项课程群**（实时检测器架构、DETR 家族、TSR 领域知识、检测增强、小目标检测、
  长尾数据闭环、VLA 感知接口、车端部署一致性、检测面试实务）— **本课 05 模块题库中所有 CV 深题的
  入口都指向这九门课**，本课不重复它们已经讲透的技术细节。
- **C62 · 编程面试实战** — 算法与数据结构手撕代码。对应 HR 说的 **Practical (Coding) Exercise** 板块，
  与本课（对应 **Technical Knowledge Assessment**）是同批但完全不同的板块。
- **C63 · ML 系统设计面试** — 七步框架与六个完整案例演练。与本课同属 Problem-Solving/Knowledge
  板块，但粒度不同：**C63 讲怎么组织一道 45 分钟开放设计题，本课讲怎么在 60 秒内讲清楚一个具体知识点**。
  本课 04 模块的显著性/功效等概念被 C63 直接引用，不重复展开。
- **C65 · 结构化问题求解与沟通** — 估算、诊断归因、权衡决策、模糊需求澄清的**通用**方法论。
  本课"三段式答法"与"我不知道的正确说法"是这套通用方法论在知识问答场景下的具体应用，两者互相引用。

一句话记住这批补全课的分工：**C62 编码 · C63 设计 · C64 问答 · C65 沟通 · C61 检测专项。**
