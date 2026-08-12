# 参考清单 · References（概率与贝叶斯机器学习）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个算法，都能在下列文献里找到完整的理论推导与更一般的形式。

## 教材：奠基与全景 · Textbooks

- ★ **Bishop 2006, _Pattern Recognition and Machine Learning_ (PRML)** — 贝叶斯机器学习的经典教材。第 2 章（概率分布与共轭）、第 8 章（图模型）、第 10 章（变分推断）、第 11 章（采样）、第 6 章（核与 GP）几乎覆盖本课全部主题，且以「概率论只有求和与乘法两条规则」的统一视角讲透。本课的符号与推导大量对标它，是配套精读的首选。
- ★ **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin 2013, _Bayesian Data Analysis_ (BDA), 3rd ed.** — 应用贝叶斯的「圣经」。强项是**实践智慧**：先验选择、分层模型、后验预测检验、MCMC 收敛诊断（$\hat R$、ESS 的现代定义就出自这一脉）、模型批判。本课模块 01/02 的可信区间、收缩、诊断思想以它为准。免费 PDF 可得。
- ★ **Murphy 2022/2023, _Probabilistic Machine Learning: An Introduction & Advanced Topics_ (PML 1 & 2)** — 当代最全面的概率 ML 百科。把贝叶斯推断、MCMC、VI、GP、PGM、深度生成模型放在统一框架下，且紧跟前沿（normalizing flows、amortized VI、SVI）。当你想看某个本课主题的「更现代、更一般」版本，查它。
- **MacKay 2003, _Information Theory, Inference, and Learning Algorithms_** — 以信息论视角讲贝叶斯推断、采样与 GP，洞见极多、可免费下载。第 29–30 章（蒙特卡洛）、第 33 章（变分方法）、第 45 章（GP）是绝佳的直觉补充。
- **Barber 2012, _Bayesian Reasoning and Machine Learning_** — 图模型与精确推断（变量消去、信念传播）讲得尤为细致清晰，免费 PDF。本课模块 05 的算法细节可对照它。

## 贝叶斯推断与共轭 · Bayesian Inference

- ★ **Gelman et al., BDA 第 2–3 章** — 单参数与多参数模型的共轭分析（Beta-Binomial、Normal、Poisson-Gamma），以及无信息/弱信息先验的讨论。本课模块 01 的所有共轭更新都是它的特例。
- **Diaconis & Ylvisaker 1979, _Conjugate Priors for Exponential Families_** — 指数族共轭先验的理论刻画，回答「为什么共轭恰好发生在指数族」。想理解共轭的深层结构读它。
- **Jaynes 2003, _Probability Theory: The Logic of Science_** — 把概率论作为「扩展的逻辑」的哲学奠基，最大熵先验、贝叶斯认识论的思想源头。读它理解贝叶斯「为什么是合理的」。
- **Gelman & Hill 2007, _Data Analysis Using Regression and Multilevel/Hierarchical Models_** — 分层模型与 partial pooling 的实践经典，把「各组借力」讲得无比直观。

## MCMC · Markov Chain Monte Carlo

- ★ **Neal 1993, _Probabilistic Inference Using Markov Chain Monte Carlo Methods_** — MCMC 的奠基性综述，系统讲清 Metropolis-Hastings、Gibbs、细致平衡、收敛等核心理论。本课模块 02 的理论骨架来源，必读。
- ★ **Metropolis et al. 1953 & Hastings 1970** — Metropolis 算法的原始论文与 Hastings 的推广。理解「接受率从何而来、为何保证正确平稳分布」的源头。
- ★ **Neal 2011, _MCMC Using Hamiltonian Dynamics_（in Handbook of MCMC）** — HMC 的权威讲解：如何用梯度与哈密顿动力学生成远距离高接受率提议，攻克随机游走 MH 的慢混合。是理解 Stan/PyMC 默认采样器的必读。
- **Hoffman & Gelman 2014, _The No-U-Turn Sampler (NUTS)_** — HMC 的自动调参版本，免去手调步长与轨迹长度，是现代概率编程的默认引擎。
- **Geman & Geman 1984** — Gibbs 采样的原始论文（图像复原语境），「Gibbs sampler」一名即源于此。
- **Gelman & Rubin 1992, _Inference from Iterative Simulation Using Multiple Sequences_** — $\hat R$ 收敛诊断的原始论文：用多链的链间/链内方差比判断收敛。本课模块 02 的 $\hat R$ 实现直接对应它。
- **Vehtari et al. 2021, _Rank-normalized $\hat R$ and ESS_** — $\hat R$ 与 ESS 的现代改进版（rank-normalization、folded $\hat R$），是当今 PPL 报告诊断的标准。

## 变分推断 · Variational Inference

- ★ **Blei, Kucukelbir & McAuliffe 2017, _Variational Inference: A Review for Statisticians_** — 变分推断的现代权威综述。从 KL/ELBO 出发，把平均场、CAVI、SVI、指数族 VI 一气讲透，并坦诚讨论 VI 的偏差。本课模块 03 的结构与符号对标它，**强烈建议先读**。
- ★ **Jordan, Ghahramani, Jaakkola & Saul 1999, _An Introduction to Variational Methods for Graphical Models_** — 变分方法的奠基综述，把平均场从统计物理引入机器学习。理解 CAVI 更新「$\log q_j^*=\mathbb{E}_{-j}[\log p]$」的来源。
- ★ **Kingma & Welling 2014, _Auto-Encoding Variational Bayes_ (VAE)** — 重参数化技巧 + 摊销推断的里程碑，把 VI 与深度学习接通。本课模块 03 重参数化一节的直接来源。
- **Ranganath, Gerrish & Blei 2014, _Black Box Variational Inference_** — 用 score-function 梯度做不依赖模型推导的通用 VI，让 VI「即插即用」。
- **Hoffman, Blei, Wang & Paisley 2013, _Stochastic Variational Inference_** — 用随机梯度 + 小批量把 VI 扩展到海量数据，是大规模贝叶斯的转折点。
- **Bishop, PRML 第 10 章** — 平均场 VI 在高斯混合等模型上的完整逐步推导，是把 CAVI 算清楚的最佳练习材料。

## 高斯过程 · Gaussian Processes

- ★ **Rasmussen & Williams 2006, _Gaussian Processes for Machine Learning_ (GPML)** — GP 的权威教科书，免费 PDF。第 2 章（回归、预测方程、边际似然）、第 4 章（核）、第 5 章（超参与模型选择）是本课模块 04 的完整理论依据。本课的预测均值/方差、对数边际似然公式逐字对应它的式 (2.22)–(2.30)。
- **MacKay 1998, _Introduction to Gaussian Processes_** — 简短而深刻的 GP 引论，把「从权空间到函数空间」「核即先验」的直觉讲得极清楚。
- **Duvenaud 2014, _Automatic Construction of Kernels (PhD thesis), "The Kernel Cookbook"_** — 各种核的性质、组合规则与可视化，回答「该选什么核、核的加/乘意味着什么」。建模时的实用手册。
- **Williams & Seeger 2001 / Quiñonero-Candela & Rasmussen 2005** — 稀疏 GP 与诱导点近似，攻克 GP 的 $O(n^3)$ 瓶颈，是 GP 走向大数据的关键，本课模块 04 前沿一节的延伸。
- **Wilson & Adams 2013, _Gaussian Process Kernels for Pattern Discovery (Spectral Mixture)_** — 用谱混合核让 GP 自动发现结构（周期、趋势），展示核工程的威力。

## 概率图模型 · Probabilistic Graphical Models

- ★ **Koller & Friedman 2009, _Probabilistic Graphical Models: Principles and Techniques_** — PGM 的百科全书。表示（贝叶斯网/MRF/因子图）、推断（变量消去、信念传播、团树）、学习全覆盖，d-分离、诱导宽度等概念以它为准。本课模块 05 的理论权威，篇幅大但查阅价值极高。
- ★ **Pearl 1988, _Probabilistic Reasoning in Intelligent Systems_** — 贝叶斯网与信念传播的奠基之作，d-分离、消息传递的思想源头。Pearl 后续的因果推断（do-演算）也由此生长。
- **Kschischang, Frey & Loeliger 2001, _Factor Graphs and the Sum-Product Algorithm_** — 因子图与 sum-product 的统一论文，证明 BP、Kalman 滤波、解码算法都是它的特例。本课模块 05 因子图与 BP 的直接依据。
- **Yedidia, Freeman & Weiss 2003, _Understanding Belief Propagation and its Generalizations_** — 把 loopy BP 与统计物理的自由能联系起来，解释有环图上 BP 为何（有时）有效。
- **Wainwright & Jordan 2008, _Graphical Models, Exponential Families, and Variational Inference_** — 用变分视角统一图模型推断的高阶专著，把本课模块 03 与 05 接通（推断 = 在边际多胞形上的优化）。

## 概率编程与工具 · Probabilistic Programming

- ★ **Carpenter et al. 2017, _Stan: A Probabilistic Programming Language_** — Stan 的论文。理解工业级 HMC/NUTS + 自动微分如何把本课的手写采样器自动化。学完本课，Stan/PyMC 的每个旋钮你都能说出所以然。
- **Salvatier, Wiecki & Fonnesbeck 2016, _Probabilistic Programming in Python using PyMC3_** — Python 生态最常用的 PPL，API 直观，是把本课知识落到实战的自然下一步。
- **Bingham et al. 2019, _Pyro: Deep Universal Probabilistic Programming_** — 基于 PyTorch 的 PPL，主打随机变分推断与深度概率模型，连接本课模块 03 与现代深度学习。
- **GPyTorch / GPflow 文档** — 可扩展 GP 的现代实现（利用 GPU 与稀疏近似），是把本课模块 04 的 numpy GP 推向真实规模的工具。

## 本课定位与衔接 · Scope & Cross-links

- ⚠️ **纯 numpy / CPU 从零**：全课不依赖 PyMC/Stan/sklearn，每个算法（共轭更新、MH、Gibbs、CAVI、GP 回归、变量消去、信念传播）都用 numpy 亲手实现，并与一个**绝对可信的参照对拍**——共轭更新对拍解析后验、MCMC 对拍真分布的矩、CAVI 对拍 MCMC、GP 对拍 Cholesky 闭式解、变量消去对拍暴力枚举。结构正确则数值一致。
- **可迁移性**：你在 numpy 里验证过的 ELBO、接受率、消息更新、核矩阵，可一对一对应到 PyMC/Stan/Pyro/GPyTorch 的内部机制；学完本课再读这些库的源码或文档，会发现「原来如此」。
- **课程衔接**：本课是概率视角的根基课，下游接生成模型（VAE/扩散的变分基础来自模块 03）、贝叶斯深度学习与不确定性量化（模块 01/04）、因果推断（模块 05 的 d-分离与 Pearl 体系）、以及强化学习中的贝叶斯方法（Thompson 采样等）。
