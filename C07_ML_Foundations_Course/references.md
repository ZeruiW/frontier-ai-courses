# References · 参考文献与数据集

> 标注规则：**★ = 必读**（建立本课核心直觉的源头材料）；其余为深入/扩展。每条都注明「解决了什么问题 / 为何值得读」，按主题组织。所有 arXiv/书目均可公开获取。

---

## 一、教材（全课地基，按使用频率排序）

- **★ Goodfellow, Bengio, Courville. _Deep Learning_. MIT Press, 2016.**
  深度学习领域的标准教材，全书在线免费。**解决什么问题**：把 backprop（ch.6）、数值计算与条件数（ch.4）、最优化（ch.8）、正则化（ch.7）讲成一套自洽语言。本课模块 01/05/06 的矩阵推导口径与它一致。第一遍至少读 ch.2（线代）、ch.3（概率信息论）、ch.6（前馈网络与 backprop）、ch.8（训练优化）。

- **★ Hastie, Tibshirani, Friedman. _The Elements of Statistical Learning_ (ESL). Springer, 2009.**
  经典统计学习教材，免费 PDF。**解决什么问题**：bias-variance 分解（ch.7）、线性方法（ch.3）、树与 boosting（ch.9–10、15）、模型评估与交叉验证（ch.7）。本课模块 03/06 的几乎每个结论都能在这里找到更严格的版本。偏数学，配 ISLR 当入门更友好。

- **★ Bishop. _Pattern Recognition and Machine Learning_ (PRML). Springer, 2006.**
  贝叶斯视角的经典。**解决什么问题**：PCA（ch.12，含概率 PCA）、GMM 与 EM（ch.9，EM 的 ELBO/Jensen 推导是全书最值得反复读的一章）、线性回归与正则化的贝叶斯解释（ch.3）。模块 02（MAP=正则化）与模块 04（EM）直接对标本书。

- **★ Murphy. _Probabilistic Machine Learning: An Introduction_ (PML1). MIT Press, 2022.**（及进阶卷 _Advanced Topics_, 2023）
  比 PRML 更新、更工程化的概率 ML 百科，免费 PDF。**解决什么问题**：把 MLE/MAP、信息论、优化、评估指标用现代记号统一重写，覆盖到神经网络与现代主题。作为「一本就够」的案头查阅书最合适，本课术语口径多处参考它。

- Wasserman. _All of Statistics_. Springer, 2004.
  **解决什么问题**：用最少篇幅讲清频率派推断、假设检验、置换检验、bootstrap（本课模块 02/07 的统计部分）。适合「我只想快速搞懂这个统计概念」的查阅。

- Cover & Thomas. _Elements of Information Theory_. Wiley, 2006.
  **解决什么问题**：熵、交叉熵、KL、互信息的权威定义与性质证明（Gibbs 不等式、数据处理不等式）。模块 02 的信息论一节站在这本书肩上；想真正理解「LLM loss 就是交叉熵」要读它的 ch.2、ch.5。

- Boyd & Vandenberghe. _Convex Optimization_. Cambridge, 2004.
  **解决什么问题**：凸性、对偶、KKT 条件（理解 SVM 的对偶形式与逻辑回归为何无局部最优）。免费 PDF。模块 03/05 的「为什么凸问题好优化」的严格来源。

---

## 二、关键论文（按模块）

### 01 · 矩阵微积分与 backprop
- **★ Karpathy. _micrograd_** （GitHub，~150 行）。**解决什么问题**：用最小代码实现完整反向模式 AD，是理解 `loss.backward()` 内部机制的最佳材料。配套 YouTube 讲解逐行重建，强烈建议跟敲一遍。
- **★ Rumelhart, Hinton & Williams 1986. _Learning representations by back-propagating errors_. Nature.** 把 backprop 引入神经网络训练的奠基论文——历史与直觉的源头。
- Baydin, Pearlmutter, Radul & Siskind 2018. _Automatic Differentiation in Machine Learning: a Survey_. JMLR. **解决什么问题**：系统厘清 forward-mode vs reverse-mode、JVP/VJP、与符号/数值微分的区别。模块 01 第 8 节的代价分析出自此。
- CS231n _Backpropagation, Intuitions_ notes（Stanford）。**解决什么问题**：用计算图与「上游×局部」把矩阵反向讲到能手写，本课模块 01 的教学顺序参考它。

### 02 · 概率统计与信息论
- **★ Shannon 1948. _A Mathematical Theory of Communication_. Bell System Tech. J.** 信息论的开山之作，定义了熵与信道容量。理解交叉熵/困惑度的终极源头。
- Kullback & Leibler 1951. _On Information and Sufficiency_. KL 散度的出处。
- Kaplan et al. 2020. _Scaling Laws for Neural Language Models_；Hoffmann et al. 2022. _Training Compute-Optimal LLMs (Chinchilla)_. **解决什么问题**：这两篇画的 loss-vs-scale 曲线，其纵轴正是模块 02 定义的交叉熵；把「困惑度」与「模型规模/数据量」连成可外推的定律。

### 03 · 经典监督学习
- **★ Breiman 2001. _Random Forests_. Machine Learning.** 随机森林奠基；解释 bagging + 随机特征如何通过去相关把方差降下来（模块 03 的方差公式出自此思路）。
- **★ Chen & Guestrin 2016. _XGBoost: A Scalable Tree Boosting System_. KDD.** 工程化梯度提升的里程碑，至今表格竞赛的强 baseline。
- **★ Cortes & Vapnik 1995. _Support-Vector Networks_. Machine Learning.** SVM 与最大间隔/核技巧的源头，理解 hinge loss 与支持向量。
- Friedman 2001. _Greedy Function Approximation: A Gradient Boosting Machine_. Annals of Statistics. boosting 的统计学解释（拟合负梯度）。
- Grinsztajn, Oyallon & Varoquaux 2022. _Why do tree-based models still outperform deep learning on tabular data?_ NeurIPS. **解决什么问题**：系统实验说明中小规模表格数据上 GBDT 仍胜深度网络——评测时务必带 XGBoost baseline 的实证依据。

### 04 · 无监督学习
- **★ Dempster, Laird & Rubin 1977. _Maximum Likelihood from Incomplete Data via the EM Algorithm_. JRSS-B.** EM 算法的奠基论文，定义 E 步/M 步与单调收敛性。
- **★ Arthur & Vassilvitskii 2007. _k-means++: The Advantages of Careful Seeding_. SODA.** 解决 k-means 对初始化敏感、易陷劣质局部最优的问题，给出带理论保证的初始化。
- Pearson 1901 / Hotelling 1933. PCA 的两条历史源头（最大方差 / 最小重构误差视角）。
- Eckart & Young 1936. 低秩逼近定理——PCA 用前 $k$ 个奇异向量重构最优的数学依据。
- Tipping & Bishop 1999. _Probabilistic Principal Component Analysis_. 把 PCA 纳入概率隐变量框架，连接到 EM。

### 05 · 优化器
- **★ Kingma & Ba 2015. _Adam: A Method for Stochastic Optimization_. ICLR.** Adam 的原始论文；偏差校正、$\beta_1/\beta_2$ 的含义、与 RMSProp/AdaGrad 的关系都在这里。**必读**——大模型训练的默认起点。
- **★ Loshchilov & Hutter 2019. _Decoupled Weight Decay Regularization (AdamW)_. ICLR.** 指出 Adam 把 L2 当梯度会被自适应分母缩放污染，解耦 weight decay 后泛化更好。今天几乎所有 LLM 都用 AdamW——**必读**。
- Sutskever, Martens, Dahl & Hinton 2013. _On the importance of initialization and momentum in deep learning_. ICML. 动量与 Nesterov 在深度网络中的作用。
- Duchi, Hazan & Singer 2011. _Adaptive Subgradient Methods (AdaGrad)_. JMLR. 自适应学习率的起点。
- Loshchilov & Hutter 2017. _SGDR: Stochastic Gradient Descent with Warm Restarts_. cosine 退火与重启调度的来源。
- Smith 2017. _Cyclical Learning Rates for Training Neural Networks_. warmup 与 lr range test 的经验依据。

### 06 · 泛化与指标
- **★ Fawcett 2006. _An introduction to ROC analysis_. Pattern Recognition Letters.** ROC/AUC 的标准教程，含 AUC 的 Mann–Whitney 概率解释。
- **★ Guo, Pleiss, Sun & Weinberger 2017. _On Calibration of Modern Neural Networks_. ICML.** 证明现代深度网络普遍过自信，提出温度缩放（temperature scaling）这一极简事后校准。理解 ECE 与可靠性图必读。
- Saito & Rehmsmeier 2015. _The Precision-Recall Plot Is More Informative than the ROC Plot..._ PLOS ONE. 极不平衡数据下应看 PR 而非 ROC 的实证。
- Niculescu-Mizil & Caruana 2005. _Predicting Good Probabilities With Supervised Learning_. ICML. 各类模型的校准行为对比（Platt scaling、isotonic）。
- Belkin et al. 2019. _Reconciling modern machine-learning practice and the bias–variance trade-off_. PNAS. **解决什么问题**：double descent——过参数化时测试误差二次下降，对经典 bias-variance 图的现代补充。

### 07 · 面试 drills / 评估方法
- **★ Efron & Tibshirani 1993. _An Introduction to the Bootstrap_. Chapman & Hall.** bootstrap 置信区间的权威来源；模块 07 给 eval 分数配误差棒的核心技术。
- Kohavi 1995. _A Study of Cross-Validation and Bootstrap for Accuracy Estimation and Model Selection_. IJCAI. k-fold 与 bootstrap 在模型选择中的偏差/方差比较。
- Dietterich 1998. _Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms_. Neural Computation. 比较两个分类器时的检验方法（配对设计、5×2cv）。

---

## 三、本课使用的真实数据集（均可公开下载、首次运行缓存到 `~/.ml_foundations_data/`）

| 数据集 | 模块 | 用途 | 来源 |
|--------|------|------|------|
| Palmer Penguins | 00, 02 | 标准化 / 分层划分 / 高斯 MLE / 置换检验 | seaborn-data（GitHub raw） |
| UCI Breast Cancer (WDBC) | 01, 05 | backprop 两层 MLP / 逻辑回归 / 优化器对比 | UCI ML Repository |
| Karpathy tiny-shakespeare | 02 | 熵 / 交叉熵 / 困惑度（bigram 语言模型） | char-rnn repo（GitHub raw） |
| California Housing (1990) | 03 | OLS 回归 / R² / 共线性与标准化 | ageron/handson-ml2（GitHub raw） |
| UCI optdigits（8×8 手写数字） | 04 | PCA via SVD / k-means / 解释方差比 | UCI ML Repository |
| UCI Wine | 04, 07 | GMM/EM / 多分类 / k-fold CV / bootstrap CI | UCI ML Repository |
| UCI Adult (Census Income) | 06 | ROC/PR/AUC / 校准 ECE（24% 正类，不平衡） | UCI ML Repository |

> 工程纪律：**核心算法全部 numpy 从零实现**（OLS、logistic、树、PCA、k-means、EM、所有优化器、所有指标），数据集仅用 pandas 读取、用真实数值驱动；联网失败时 notebook 用 try/except 回退到内置真实数值，保证离线可跑。matplotlib 仅作可选可视化。

---

## 四、延伸阅读（想再深一层）

- 3Blue1Brown _Neural Networks_ / _Essence of Linear Algebra_（YouTube）：把 backprop、特征值、梯度的几何直觉做成动画，配合模块 01/04 看。
- Roger Grosse, _CSC2541 / CSC421_ lecture notes（多伦多大学）：矩阵微积分、二阶优化、Hessian 与曲率，进阶到模块 05 的前沿。
- distill.pub _Momentum_（Goh 2017）：交互式可视化动量为何加速收敛，模块 05 动量一节的最佳补充。
- Anthropic / OpenAI 的训练技术报告：把本课的「优化器 + 调度 + 数值稳定 + 评估指标」放进真实大模型工程语境，读完本课再看会豁然开朗。
