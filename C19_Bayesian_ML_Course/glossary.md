# 术语词典 · Glossary（概率与贝叶斯机器学习）

> 按主题分组，每条 2–3 句中文释义，英文术语保留原文（论文与库的通用语言）。读 Bishop PRML / Gelman BDA / Murphy PML / Rasmussen GP / Koller PGM 遇到生词回这里查。本课用 numpy 从零实现这些概念，术语与真实贝叶斯建模一一对应。

## 概率与分布基础 · Probability & Distributions

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| random variable | 随机变量 | 把随机实验的结果映射到数值的函数。离散随机变量有概率质量函数（PMF），连续随机变量有概率密度函数（PDF）。贝叶斯把模型参数也当随机变量，这是与频率派的根本分歧。 |
| probability density function (PDF) | 概率密度函数 | 连续随机变量的相对似然函数 $p(x)$，本身不是概率（可大于 1），其在区间上的积分才是概率。所有后验、似然、先验在连续情形下都以密度表示。 |
| probability mass function (PMF) | 概率质量函数 | 离散随机变量在每个取值上的概率 $P(X=x)$，非负且求和为 1。Binomial、Poisson、Categorical 等用它描述。 |
| joint / marginal / conditional | 联合 / 边缘 / 条件分布 | 联合 $p(x,y)$ 描述多个变量同时的分布；边缘 $p(x)=\int p(x,y)\,dy$ 是积掉其他变量；条件 $p(x\mid y)=p(x,y)/p(y)$ 是固定 $y$ 后 $x$ 的分布。三者经由求和/乘法规则相互转换，是一切概率推断的代数基础。 |
| expectation / variance | 期望 / 方差 | 期望 $\mathbb{E}[X]=\int x\,p(x)\,dx$ 是分布的「重心」；方差 $\mathrm{Var}[X]=\mathbb{E}[(X-\mathbb{E}X)^2]$ 度量离散程度。贝叶斯里后验均值常作点估计、后验方差度量不确定性。 |
| sum rule / product rule | 求和规则 / 乘法规则 | 概率论的两条公理化运算：求和规则 $p(x)=\sum_y p(x,y)$（边缘化），乘法规则 $p(x,y)=p(x\mid y)p(y)$。Bishop 反复强调：整个概率推断只是这两条规则的反复应用。 |
| independence / conditional independence | 独立 / 条件独立 | 独立指 $p(x,y)=p(x)p(y)$；条件独立指给定 $z$ 后 $p(x,y\mid z)=p(x\mid z)p(y\mid z)$，记作 $x \perp y \mid z$。条件独立是概率图模型能把高维联合分布分解成小因子的核心，决定了推断的可处理性。 |
| change of variables | 变量替换 | 概率密度在可逆变换 $y=g(x)$ 下的变换公式 $p_Y(y)=p_X(x)\,\lvert dx/dy\rvert$（多维用 Jacobian 行列式）。重参数化技巧、归一化流都依赖它。 |
| Monte Carlo estimate | 蒙特卡洛估计 | 用样本均值 $\frac1N\sum f(x_i)$（$x_i\sim p$）近似期望 $\mathbb{E}_p[f]$。无偏，误差按 $O(1/\sqrt N)$ 下降，与维度无关——这是高维积分能被采样攻克的根本原因。 |

## 贝叶斯推断核心 · Bayesian Inference

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Bayes' theorem | 贝叶斯定理 | $p(\theta\mid D)=\dfrac{p(D\mid\theta)\,p(\theta)}{p(D)}$：后验 ∝ 似然 × 先验。它把「看到数据后对参数的信念」表达为先验信念被似然按比例重新加权。整门课都是它的不同实现。 |
| prior | 先验 | 看到数据前对参数的信念分布 $p(\theta)$。可来自领域知识（informative）或刻意保持模糊（weakly-informative / uninformative）。先验的选择是贝叶斯方法既强大又被诟病的来源。 |
| likelihood | 似然 | 给定参数时数据出现的概率 $p(D\mid\theta)$，看作 $\theta$ 的函数（不是概率分布，不对 $\theta$ 积分为 1）。频率派的 MLE 只用它，贝叶斯用它来更新先验。 |
| posterior | 后验 | 看到数据后对参数的信念 $p(\theta\mid D)$。它是贝叶斯推断的**核心产物**——一切预测、决策、不确定性量化都从后验导出。本课五个模块都在用不同手段获取或近似它。 |
| evidence / marginal likelihood | 证据 / 边际似然 | $p(D)=\int p(D\mid\theta)p(\theta)\,d\theta$，贝叶斯定理的归一化常数。它对参数推断无关紧要（是常数），但对**模型比较**至关重要（贝叶斯因子），也是 GP 超参优化的目标。通常难算，是近似推断的主因。 |
| conjugate prior | 共轭先验 | 使后验与先验属于**同一分布族**的先验。如 Beta 对 Binomial、Normal 对已知方差的 Normal、Gamma 对 Poisson。共轭让后验更新退化为参数的代数运算，给出闭式解，是理解贝叶斯更新的最佳起点。 |
| posterior predictive distribution | 后验预测分布 | 对**新数据**的预测 $p(\tilde x\mid D)=\int p(\tilde x\mid\theta)p(\theta\mid D)\,d\theta$，对后验积分（而非只用点估计）。它自动把参数不确定性传播到预测，是贝叶斯优于「插值点估计」的关键体现。 |
| prior predictive | 先验预测 | 在看到数据前、用先验对数据的预测 $p(x)=\int p(x\mid\theta)p(\theta)\,d\theta$。常用于先验预测检验（prior predictive check）——看先验蕴含的数据是否合理。 |
| MAP (maximum a posteriori) | 最大后验估计 | 取后验的众数 $\hat\theta_{\text{MAP}}=\arg\max_\theta p(\theta\mid D)$ 作为点估计。等价于带正则（先验对数）的 MLE；先验为均匀分布时退化为 MLE。是后验的一个「点摘要」，丢弃了不确定性。 |
| MLE (maximum likelihood) | 最大似然估计 | $\hat\theta_{\text{MLE}}=\arg\max_\theta p(D\mid\theta)$，频率派的主力。等价于先验为常数（improper uniform）时的 MAP。数据多时与贝叶斯结果趋同，数据少时差异显著。 |
| credible interval | 可信区间 | 后验概率为 $1-\alpha$ 的参数区间，可直接说「参数有 95% 概率落在此区间」（这是频率派置信区间**不能**说的）。常用等尾（equal-tailed）或最高后验密度（HPD）两种构造。 |
| highest posterior density (HPD) | 最高后验密度区间 | 满足总概率 $1-\alpha$ 且区间内每点密度都不低于区间外的可信区间，是同等覆盖率下**最短**的区间。多峰后验下 HPD 可能不连通。 |
| shrinkage | 收缩 | 后验估计被先验「拉向」先验均值的现象，数据越少拉得越多。共轭更新的后验均值常是先验均值与数据均值的**精度加权平均**，收缩是其自然结果，能降低小样本下的方差。 |
| pooling (no / complete / partial) | 不/完全/部分汇合 | 多组数据的建模光谱：完全独立（no pooling）、合并成一组（complete pooling）、分层模型介于两者之间（partial pooling），让各组互相借力。分层贝叶斯的核心收益。 |

## 共轭族与具体分布 · Conjugate Families

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Beta distribution | Beta 分布 | 定义在 $[0,1]$ 上、由 $(\alpha,\beta)$ 参数化的分布，是概率 / 比例的自然先验。均值 $\alpha/(\alpha+\beta)$。它是 Binomial / Bernoulli 似然的共轭先验。 |
| Binomial / Bernoulli | 二项 / 伯努利 | Bernoulli 描述单次成功概率为 $\theta$ 的试验，Binomial 是 $n$ 次独立 Bernoulli 的成功数。Beta-Binomial 共轭：后验 $\mathrm{Beta}(\alpha+k,\beta+n-k)$，更新只是「把成功数加到 $\alpha$、失败数加到 $\beta$」。 |
| Gamma distribution | Gamma 分布 | 定义在正实数上、由形状 $\alpha$ 与速率 $\beta$ 参数化。是 Poisson 速率、指数分布速率、以及 Normal **精度**（方差倒数）的共轭先验。 |
| Normal-Normal conjugacy | 正态-正态共轭 | 已知方差时，Normal 似然的均值以 Normal 为共轭先验。后验均值是先验均值与样本均值的**精度加权平均**，后验精度 = 先验精度 + 数据精度（精度可加），是收缩现象最干净的范例。 |
| Normal-Inverse-Gamma | 正态-逆 Gamma | 均值与方差都未知时 Normal 的共轭先验，对均值用 Normal、对方差用 Inverse-Gamma（等价对精度用 Gamma）。给出 $(\mu,\sigma^2)$ 的联合后验。 |
| Dirichlet distribution | Dirichlet 分布 | Beta 在多类上的推广，是 Categorical / Multinomial 的共轭先验，也是 LDA 等主题模型的支柱。参数 $\boldsymbol\alpha$ 控制各类的先验权重与集中度。 |
| precision | 精度 | 方差的倒数 $\tau=1/\sigma^2$。贝叶斯里常以精度而非方差参数化高斯，因为「精度可加」让共轭更新与多源信息融合写起来格外简洁。 |
| sufficient statistic | 充分统计量 | 从数据中提炼、对参数推断而言「足够」的少数量（如 Binomial 的成功数、Normal 的样本和与平方和）。共轭更新本质上只依赖充分统计量，这是它高效的原因。 |
| pseudo-count | 伪计数 | 共轭先验参数的直观解释：Beta$(\alpha,\beta)$ 相当于「先验已见 $\alpha-1$ 次成功、$\beta-1$ 次失败」。把先验当成「虚拟的历史数据」，让先验强度可量化。 |

## 马尔可夫链蒙特卡洛 · MCMC

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Markov chain | 马尔可夫链 | 满足「未来只依赖当前、与过去无关」的随机序列 $p(x_{t+1}\mid x_t,\dots,x_0)=p(x_{t+1}\mid x_t)$。MCMC 构造一条以目标后验为平稳分布的链，让链跑久后的样本服从后验。 |
| stationary distribution | 平稳分布 | 满足 $\pi(x')=\sum_x \pi(x)T(x\to x')$ 的分布：链一旦进入就不再改变其分布。MCMC 的全部目标就是设计转移核 $T$ 使平稳分布恰为目标后验。 |
| detailed balance | 细致平衡 | 充分（非必要）保证平稳性的条件 $\pi(x)T(x\to x')=\pi(x')T(x'\to x)$。Metropolis-Hastings 的接受率正是为满足它而设计的，是大多数 MCMC 算法正确性的基石。 |
| Metropolis-Hastings (MH) | MH 算法 | 通用 MCMC：从提议分布 $q$ 采候选 $x'$，以接受率 $\min(1, \frac{\pi(x')q(x\mid x')}{\pi(x)q(x'\mid x)})$ 接受或拒绝。只需目标分布的**未归一化**密度（后验无需归一化常数），这正是它强大的原因。 |
| proposal distribution | 提议分布 | MH 中生成候选状态的分布 $q(x'\mid x)$，常用以当前点为中心的高斯（random walk）。其步长（方差）是关键调参：太小走不动、太大全被拒，理论最优接受率约 0.234（高维）/0.44（一维）。 |
| acceptance rate | 接受率 | MH 中候选被接受的比例。过高（>0.7）意味步长太小、探索慢；过低（<0.1）意味步长太大、链卡住。是诊断与调 MH 步长的首要指标。 |
| Gibbs sampling | Gibbs 采样 | MH 的特例：轮流从每个变量的**完全条件分布** $p(x_i\mid x_{-i})$ 采样，接受率恒为 1（无拒绝）。当完全条件可解析采样（常因共轭）时极其高效，是分层模型的主力。 |
| full conditional | 完全条件分布 | 给定所有其他变量后单个变量的条件分布 $p(x_i\mid x_{-i})$。Gibbs 采样的原料；推导它常用「只保留含 $x_i$ 的因子、其余视为常数」的技巧。 |
| burn-in / warm-up | 预烧 / 预热 | 丢弃链初始的一段样本，因为链尚未收敛到平稳分布、带有初值偏差。预烧长度靠收敛诊断判断，没有理论保证的固定值。 |
| thinning | 稀释 | 每隔 $k$ 步保留一个样本以降低自相关。现代观点认为除非存储受限，thinning 通常**得不偿失**（丢弃信息反增方差），但有助于理解自相关。 |
| autocorrelation | 自相关 | 链中相隔 lag 步的样本的相关性。MCMC 样本天然自相关（不独立），自相关越高、等效独立样本越少。自相关函数（ACF）的衰减速度是混合好坏的直接信号。 |
| effective sample size (ESS) | 有效样本量 | 考虑自相关后，$N$ 个相关样本「相当于多少个独立样本」：$\mathrm{ESS}=N/(1+2\sum_k\rho_k)$。它才是 MCMC 估计精度的真实货币——5000 个高自相关样本可能 ESS 只有 50。 |
| R-hat (Gelman-Rubin) | $\hat R$ 收敛诊断 | 跑多条独立链，比较**链间方差**与**链内方差**：$\hat R=\sqrt{\widehat{\mathrm{Var}}^+/W}$。收敛时各链应无法区分，$\hat R\to 1$；$\hat R>1.01$ 提示未收敛。是判断「链跑够了吗」的标准工具。 |
| mixing | 混合 | 链在状态空间中移动、遍历后验的效率。混合好 = 自相关低衰减快、ESS 高；混合差 = 链在某区域卡住。提议步长、参数相关性、后验形状都影响混合。 |
| Hamiltonian Monte Carlo (HMC) | 哈密顿蒙特卡洛 | 借用物理中的哈密顿动力学，用梯度信息生成「远距离、高接受率」的提议，大幅降低自相关。NUTS（No-U-Turn Sampler）是其自动调参版本，是 Stan / PyMC 的默认采样器。 |

## 变分推断 · Variational Inference

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| variational inference (VI) | 变分推断 | 把推断转成**优化**：用一族简单分布 $q_\phi$ 近似难算的后验 $p(\theta\mid D)$，通过最小化 KL 散度 / 最大化 ELBO 找最佳 $q$。比 MCMC 快、可扩展，但给出的是有偏近似。 |
| KL divergence | KL 散度 | $\mathrm{KL}(q\Vert p)=\mathbb{E}_q[\log\frac{q}{p}]\ge 0$，度量分布差异（非对称、非距离）。VI 最小化 $\mathrm{KL}(q\Vert p_{\text{post}})$；这个方向的选择导致 VI 的「抓众数、低估方差」倾向。 |
| ELBO (evidence lower bound) | 证据下界 | $\mathcal L(q)=\mathbb{E}_q[\log p(\theta,D)]-\mathbb{E}_q[\log q(\theta)]$，满足 $\log p(D)=\mathcal L(q)+\mathrm{KL}(q\Vert p_{\text{post}})$。因 KL≥0，$\mathcal L$ 是 $\log$ 证据的下界；最大化 ELBO ⟺ 最小化 KL。VI 的优化目标。 |
| mean-field approximation | 平均场近似 | 假设近似后验在各变量（组）上**完全分解** $q(\theta)=\prod_i q_i(\theta_i)$。把高维联合优化拆成各因子的交替优化，是 VI 最常用的可处理性假设，代价是忽略后验变量间的相关。 |
| CAVI (coordinate ascent VI) | 坐标上升变分推断 | 在平均场假设下，轮流固定其他因子、把单个因子更新为其**最优形式** $\log q_j^*\propto\mathbb{E}_{-j}[\log p(\theta,D)]$，单调抬升 ELBO 直到收敛。与 Gibbs 采样形式上对偶（期望 vs 采样）。 |
| reparameterization trick | 重参数化技巧 | 把 $z\sim q_\phi$ 写成 $z=g_\phi(\epsilon),\ \epsilon\sim p(\epsilon)$（如高斯 $z=\mu+\sigma\epsilon$），使 ELBO 对 $\phi$ 的梯度可穿过采样、用低方差的蒙特卡洛估计。VAE 与现代黑盒 VI 的关键。 |
| black-box VI (BBVI) | 黑盒变分推断 | 用蒙特卡洛 + 随机梯度直接优化 ELBO 的通用 VI，不需对每个模型手推 CAVI 更新，只需能算 $\log p(\theta,D)$。score-function（REINFORCE）与重参数化是其两类梯度估计器。 |
| amortized inference | 摊销推断 | 训练一个推断网络 $q_\phi(z\mid x)$ 对**任意** $x$ 直接输出近似后验参数，而非对每个数据点单独优化。VAE 的编码器即此，把推断成本「摊销」到一次网络前传。 |
| zero-forcing / mode-seeking | 抓众数 | 最小化 $\mathrm{KL}(q\Vert p)$ 的几何后果：$q$ 倾向覆盖 $p$ 的某个峰而非全部质量，故 VI 常**低估后验方差**、在多峰后验下只抓一个峰。与 MCMC 渐近无偏形成对比。 |
| stochastic VI (SVI) | 随机变分推断 | 用数据小批量的随机梯度优化 ELBO，使 VI 可扩展到海量数据集。Hoffman 等 2013 的工作，让 VI 成为大规模贝叶斯的可行方案。 |

## 高斯过程 · Gaussian Processes

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Gaussian process (GP) | 高斯过程 | **函数上的分布**：任意有限个点上的函数值服从联合高斯。由均值函数 $m(x)$ 与核函数 $k(x,x')$ 完全确定，是非参数贝叶斯回归的代表。 |
| kernel / covariance function | 核 / 协方差函数 | $k(x,x')$ 编码「两个输入的函数值有多相关」，从而决定 GP 样本的平滑度、周期、尺度等性质。核必须是半正定的。是 GP 建模中注入先验知识的地方。 |
| RBF / squared exponential | RBF 核 / 平方指数核 | $k(x,x')=\sigma_f^2\exp(-\lVert x-x'\rVert^2/2\ell^2)$，最常用的核，给出无限可微（极平滑）的样本函数。长度尺度 $\ell$ 控制波动快慢，$\sigma_f^2$ 控制幅度。 |
| Matern kernel | Matern 核 | 由平滑度参数 $\nu$ 控制的核族，样本函数 $\lceil\nu\rceil-1$ 次可微。$\nu=1/2$ 退化为指数核（粗糙），$\nu\to\infty$ 趋于 RBF（极平滑）。$\nu=3/2,5/2$ 在实践中最常用，比 RBF 更鲁棒。 |
| length scale | 长度尺度 | 核中的 $\ell$，控制函数沿输入轴变化的快慢：$\ell$ 大则函数平缓、远处仍相关；$\ell$ 小则函数抖动、相关性快速衰减。是最关键的核超参。 |
| GP prior / posterior | GP 先验 / 后验 | 先验是只由核决定的函数分布；用观测数据条件化后得到 GP 后验，其后验均值穿过（带噪时接近）数据点、后验方差在数据稀疏处增大——自动的不确定性量化。 |
| predictive mean / variance | 预测均值 / 方差 | GP 后验在新点 $x_*$ 的均值 $k_*^\top(K+\sigma_n^2 I)^{-1}y$ 与方差 $k_{**}-k_*^\top(K+\sigma_n^2 I)^{-1}k_*$。均值是训练目标的加权平均，方差不依赖 $y$、只随与训练点的距离增长。 |
| noise variance | 噪声方差 | 观测噪声 $\sigma_n^2$，加在核矩阵对角线上 $(K+\sigma_n^2 I)$。它让 GP 从「插值」变为「平滑回归」，并改善求逆的数值条件。又称 nugget。 |
| log marginal likelihood | 对数边际似然 | $\log p(y\mid X,\theta)=-\frac12 y^\top(K+\sigma_n^2 I)^{-1}y-\frac12\log\lvert K+\sigma_n^2 I\rvert-\frac n2\log 2\pi$。GP 超参（$\ell,\sigma_f,\sigma_n$）通过最大化它来选，自动权衡数据拟合与模型复杂度（奥卡姆剃刀）。 |
| Cholesky decomposition | Cholesky 分解 | 把对称正定矩阵分解为 $K=LL^\top$（$L$ 下三角）。GP 实现用它稳定高效地解线性系统与算 $\log$ 行列式，避免显式求逆。是 GP 代码的数值基石。 |
| jitter | 抖动 | 为保证核矩阵数值正定，给对角线加的一个极小量（如 $10^{-6}$）。在无噪声或近重复输入时防止 Cholesky 因舍入误差失败。 |
| marginalization property | 边缘化性质 | GP 的定义性质：任意有限点集上的边缘分布仍是高斯，且与「未观测的其他点」无关。这让我们只需操作有限维高斯就能对无限维函数推断。 |

## 概率图模型 · Probabilistic Graphical Models

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| probabilistic graphical model (PGM) | 概率图模型 | 用图表达随机变量间条件独立结构、从而把高维联合分布**分解**成小因子乘积的框架。分有向（贝叶斯网）与无向（马尔可夫网）两大类。 |
| Bayesian network (DAG) | 贝叶斯网络 | 有向无环图，每个节点带一个条件概率分布 $p(x_i\mid\text{pa}(x_i))$，联合分布按 $\prod_i p(x_i\mid\text{pa}_i)$ 分解。边表达直接依赖，擅长表达因果/生成结构。 |
| Markov random field (MRF) | 马尔可夫随机场 | 无向图，联合分布按团（clique）上的势函数 $\prod_c \psi_c$ 分解、再除以配分函数 $Z$ 归一化。擅长表达对称的、无方向的关联（如图像像素）。 |
| factor graph | 因子图 | 把分布显式画成「变量节点 + 因子节点」的二部图，每个因子是一个非负函数。它统一了有向与无向模型，是信念传播（sum-product）算法运行的天然载体。 |
| conditional probability table (CPT) | 条件概率表 | 离散贝叶斯网中节点给定父节点取值的条件分布表格。本课用 numpy 数组表示，是变量消去与信念传播的输入。 |
| factorization | 因子分解 | 把联合分布写成局部函数（因子）乘积的形式。图结构 ⟺ 因子分解 ⟺ 条件独立断言，三者等价，是 PGM 的中心思想：结构决定可处理性。 |
| d-separation | d-分离 | 在有向图上**纯靠拓扑**判定条件独立的规则，检查两节点间所有路径是否被给定集合「阻断」。它把图结构翻译成条件独立断言 $X\perp Y\mid Z$，无需任何数值。 |
| collider / v-structure | 对撞节点 / v-结构 | 形如 $X\to Z\leftarrow Y$ 的结构。其特殊性：路径默认被对撞点**阻断**，但一旦条件于 $Z$（或其后代）反而被**打开**——这就是「解释消除」（explaining away）的图论根源。 |
| explaining away | 解释消除 | 给定共同结果后，多个原因变得（条件）相关的现象：知道结果且确认一个原因，会降低另一个原因的概率。是 v-结构条件独立行为的直观体现。 |
| Markov blanket | 马尔可夫毯 | 使某节点与图中所有其他节点条件独立的最小节点集。贝叶斯网中 = 父节点 + 子节点 + 子节点的其他父节点。Gibbs 采样某变量时只需它的马尔可夫毯。 |
| variable elimination | 变量消去 | 精确推断算法：按某顺序逐个把变量「加和消去」，每步把含该变量的因子相乘再求和成新因子。复杂度由消去顺序决定的**诱导宽度**主导，是理解精确推断代价的钥匙。 |
| belief propagation / sum-product | 信念传播 / 和积算法 | 在因子图上传递「消息」来计算边缘的算法。树上**精确**且一次扫描完成；有环图上变成近似的 loopy BP。每条消息是局部因子与传入消息的乘积再边缘化。 |
| message passing | 消息传递 | BP 的运行方式：节点间沿边传递关于「相信变量取各值的程度」的函数（消息），汇总后得边缘。是一大类推断算法（BP、EP、VMP）的统一视角。 |
| partition function | 配分函数 | 无向图模型的归一化常数 $Z=\sum_x\prod_c\psi_c(x)$。计算它通常 #P-难，是无向图模型推断与学习的核心困难，近似推断（MCMC/VI）很大程度是为绕开它。 |
| treewidth / induced width | 树宽 / 诱导宽度 | 变量消去过程中产生的最大中间因子所涉变量数减一，由消去顺序决定。它是精确推断复杂度的根本刻画：树宽小则可精确高效推断，树宽大则精确推断指数爆炸。 |
| factor (potential) | 因子 / 势函数 | 图模型中定义在变量子集上的非负函数。有向图里是条件概率，无向图里是势函数（无需归一化）。推断算法（消去、BP）的统一操作对象就是因子的乘积与边缘化。 |

## 学习与决策 · Learning & Decision

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Bayesian model comparison | 贝叶斯模型比较 | 用边际似然（证据）比较模型：$p(M\mid D)\propto p(D\mid M)p(M)$。证据自动惩罚过复杂的模型（贝叶斯奥卡姆剃刀），无需单独的正则项或交叉验证。 |
| Bayes factor | 贝叶斯因子 | 两模型边际似然之比 $p(D\mid M_1)/p(D\mid M_2)$，量化数据对哪个模型的支持。是贝叶斯假设检验的核心量，但对先验敏感、计算困难。 |
| Occam's razor (Bayesian) | 贝叶斯奥卡姆剃刀 | 边际似然内蕴的复杂度惩罚：复杂模型把概率质量摊到更大的数据空间，对实际观测到的数据反而给较低证据。这让贝叶斯天然偏好「恰好够用」的模型。 |
| posterior mean / median / mode | 后验均值/中位数/众数 | 从后验导出点估计的三种方式，分别是平方损失、绝对损失、0-1 损失下的贝叶斯最优估计。选哪个取决于决策的损失函数——贝叶斯决策论的体现。 |
| decision theory | 决策论 | 在后验之上叠加损失函数 $L(\theta,a)$，选使**后验期望损失**最小的行动 $a^*=\arg\min_a\mathbb{E}_{p(\theta\mid D)}[L(\theta,a)]$。把「推断」与「决策」清晰分离，是贝叶斯方法论的优雅之处。 |
| hierarchical model | 分层模型 | 参数本身有共享的上层先验（超先验）的多层模型，让各组数据通过上层「借力」（partial pooling）。是贝叶斯建模最有威力的实践模式之一。 |
| identifiability | 可辨识性 | 不同参数是否能被数据区分。不可辨识时似然在某方向平坦，后验由先验主导。贝叶斯能在不可辨识情形下仍给出合理（受先验支撑的）后验，是其相对 MLE 的稳健之处。 |
