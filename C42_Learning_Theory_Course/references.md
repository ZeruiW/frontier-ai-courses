# 参考清单 · References（学习理论与优化理论）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 做数值实验的每条界与收敛率，都能在下列文献里找到证明与更一般的形式。学习理论的引用规范：教材给框架，论文给突破。

## 教材与综述 · Textbooks & Surveys
- ★ **Shalev-Shwartz & Ben-David 2014, _Understanding Machine Learning: From Theory to Algorithms_** — 当代学习理论的标准入门教材，PDF 作者免费提供。把 PAC 学习、no-free-lunch、VC 维、Rademacher 复杂度、凸优化、稳定性、SGD 一条线讲到能动手证。本课模块 01–02 的定义与定理编号大体对标它，强烈建议作为主参考精读第 2–6、9、13、14 章。
- ★ **Vapnik 1998/1999, _Statistical Learning Theory_ / _The Nature of Statistical Learning Theory_** — 统计学习理论（SLT）的奠基之作。VC 维、结构风险最小化（SRM）、一致收敛的充要条件都源出于此。语言偏数学但思想极深：它把「学习何时可能」变成关于函数类容量的精确命题。读它理解 VC 理论的<em>动机</em>而非只是公式。
- **Mohri, Rostamizadeh & Talwalkar 2018, _Foundations of Machine Learning_, 2nd ed.** — 比 SSBD 更偏 Rademacher/covering 主线的研究生教材，Rademacher 复杂度、margin 界、kernel、多分类的证明尤其完整。模块 01 的 Rademacher 链式推导可对照它第 3 章。
- **Boyd & Vandenberghe 2004, _Convex Optimization_** — 凸优化的权威教材（PDF 免费）。凸集/凸函数、对偶、KKT、内点法。模块 02 的凸性、强凸、光滑定义以它为准。优化的语言基础。
- **Nesterov 2018, _Lectures on Convex Optimization_, 2nd ed.** — 一阶方法收敛率与下界的权威来源。$O(1/t)$、$O(1/t^2)$ 加速、强凸线性率、复杂度下界的证明都在此。模块 02 的所有收敛率定理的原始出处级参考。
- **Bottou, Curtis & Nocedal 2018, _Optimization Methods for Large-Scale Machine Learning_（SIAM Review 综述）** — 把 SGD 在机器学习语境下的收敛分析（恒定 vs 衰减步长、方差、复杂度）梳理成一篇可读综述。模块 02 SGD 部分的现代视角来源。
- **Telgarsky 2021, _Deep Learning Theory_（讲义）** 与 **Arora 等人深度学习理论暑校讲义** — 把 NTK、隐式偏置、近似/优化/泛化三分法整理成现代研究生讲义。模块 03–05 的脉络参考，跟踪前沿的好入口。

## 统计学习理论：VC、Rademacher、一致收敛 · SLT
- ★ **Vapnik & Chervonenkis 1971, _On the Uniform Convergence of Relative Frequencies of Events to Their Probabilities_** — VC 理论的开山论文，第一次给出一致收敛与 VC 维的关系。今天所有「容量 ⇒ 泛化」的界都是它的后代。历史意义极大。
- ★ **Bartlett & Mendelson 2002, _Rademacher and Gaussian Complexities: Risk Bounds and Structural Results_** — 把 Rademacher 复杂度系统引入学习理论，给出数据依赖、比 VC 更紧的泛化界与收缩/结构引理。模块 01 的 Rademacher 泛化界（间隙 $\le 2\hat{\mathfrak R}+3\sqrt{\ln(2/\delta)/2n}$）与 Massart 引理、Talagrand 收缩都来自这条线，必读。
- **Koltchinskii & Panchenko 2002, _Empirical Margin Distributions and Bounding the Generalization Error of Combined Classifiers_** — margin + Rademacher 界的奠基，把「间隔越大泛化越好」严格化。模块 05 margin 界的理论根。
- **Valiant 1984, _A Theory of the Learnable_** — PAC 学习框架的提出。把「学习」第一次定义为计算复杂度意义下的问题。模块 01 PAC 定义的源头。
- **Blumer, Ehrenfeucht, Haussler & Warmuth 1989, _Learnability and the Vapnik–Chervonenkis Dimension_** — 证明「PAC 可学 ⟺ VC 维有限」，给出 VC 维与样本复杂度的双向界。模块 01 样本复杂度公式的出处。
- **Bousquet & Elisseeff 2002, _Stability and Generalization_** — 不走一致收敛，而用「算法稳定性 ⇒ 泛化」。为 SGD 等具体算法的泛化分析开了另一条门。模块 05 稳定性词条的来源。

## 优化理论 · Optimization
- ★ **Nemirovski & Yudin 1983, _Problem Complexity and Method Efficiency in Optimization_** — 一阶优化的复杂度下界（任何只用梯度的方法在凸光滑问题上至少需要 $\Omega(1/\sqrt t)$、$\Omega(1/t^2)$）。它告诉我们 Nesterov 加速是<em>最优</em>的，模块 02 「加速到此为止」的理论依据。
- ★ **Nesterov 1983, _A Method for Solving the Convex Programming Problem with Convergence Rate $O(1/k^2)$_** — 加速梯度法原始论文，达到凸光滑的最优率。模块 02 加速部分的核心。
- **Polyak 1964, _Some Methods of Speeding Up the Convergence of Iteration Methods_** — heavy-ball（重球）动量法的提出，病态二次上把率从 $\kappa$ 改善到 $\sqrt\kappa$。模块 02 动量 worked 实验（实测 $\sim20\times$ 加速，$\kappa\approx414$）复现的就是它。
- **Robbins & Monro 1951, _A Stochastic Approximation Method_** — SGD 的鼻祖，给出步长可和但平方可和（$\sum\eta_t=\infty,\sum\eta_t^2<\infty$）的收敛条件。模块 02 SGD 步长选择的理论根。
- **Polyak & Juditsky 1992, _Acceleration of Stochastic Approximation by Averaging_** — 迭代平均（Polyak–Ruppert averaging）达到最优统计率。模块 02 「噪声球 + 平均」的来源。
- **Karimi, Nutini & Schmidt 2016, _Linear Convergence of Gradient and Proximal-Gradient Methods Under the PL Condition_** — 用 PL 条件（比强凸弱）证 GD 线性收敛，解释过参数网络为何「好优化」。模块 02 PL 词条 + 模块 03 衔接的关键。
- **Ghadimi & Lan 2013, _Stochastic First-Order Methods for Nonconvex Stochastic Programming_** — 非凸 SGD 找近似驻点（$\|\nabla f\|\le\varepsilon$）的 $O(1/\varepsilon^4)$ 复杂度。模块 02 非凸驻点部分的现代参考。

## NTK 与无限宽 · Neural Tangent Kernel & Infinite Width
- ★ **Jacot, Gabriel & Hongler 2018, _Neural Tangent Kernel: Convergence and Generalization in Neural Networks_** — NTK 的原始论文。证明无限宽网络的训练动力学由一个在初始化处确定、训练中不变的核（NTK）支配，从而等价于核回归。模块 03 全程复现它：经验 NTK、随宽度趋稳、核回归预测。必读。
- ★ **Arora, Du, Hu, Li, Salakhutdinov & Wang 2019, _On Exact Computation with an Infinitely Wide Neural Net_** — 给出 CNN 的精确 NTK（CNTK）并在真实数据上评测，把 NTK 从理论变成可计算的核。模块 03 「无限宽网络=可显式计算的核」的依据，也展示了 NTK 与有限网络的差距。
- **Lee, Xiao, Schoenholz, Bahri, Novak, Sohl-Dickstein & Pennington 2019, _Wide Neural Networks of Any Depth Evolve as Linear Models Under Gradient Descent_** — 证明宽网络在训练中近似为参数的线性模型（lazy training），并给出有限宽修正。模块 03 「惰性训练/线性化」的核心实验对照。
- **Neal 1996, _Priors for Infinite Networks_** — 最早指出单隐层无限宽网络在初始化是高斯过程（NNGP）。NTK 的「训练前」对偶，模块 03 NNGP 词条的源头。
- **Lee, Bahri, Novak, Schoenholz, Pennington & Sohl-Dickstein 2018, _Deep Neural Networks as Gaussian Processes_** — 把 NNGP 推广到深层、给出逐层核递推。模块 03 「无限宽先验」的具体计算。
- **Chizat, Oyallon & Bach 2019, _On Lazy Training in Differentiable Programming_** — 指出 lazy training 是某种缩放下的普遍现象（不限于神经网络），并辨析它与特征学习的边界。模块 03 lazy vs feature learning 讨论的关键参考。

## 隐式偏置 · Implicit Bias
- ★ **Soudry, Hoffer, Nacson, Gunasekar & Srebro 2018, _The Implicit Bias of Gradient Descent on Separable Data_** — 证明在线性可分数据上，logistic/指数损失的 GD 方向收敛到 hard-margin SVM（max-margin）解，且收敛极慢（$\sim 1/\log t$）。模块 04 max-margin worked（实测 cos 0.9997）复现的正是它。隐式偏置领域的奠基，必读。
- ★ **Gunasekar, Lee, Soudry & Srebro 2018, _Implicit Bias of Gradient Descent on Linear Convolutional Networks_** 与 **Gunasekar 2017, _Implicit Regularization in Matrix Factorization_** — 把隐式偏置推广到矩阵分解（偏好核范数/低秩）与不同参数化（偏好的范数随结构改变）。模块 04 「参数化决定隐式范数」的来源。
- **Ji & Telgarsky 2019, _The Implicit Bias of Gradient Descent on Nonseparable Data_** 与 _Gradient Descent Aligns the Layers of Deep Linear Networks_ — 把 max-margin 收敛推到非可分与深线性网络，给出更紧的方向收敛速率。模块 04 进阶参考。
- **Lyu & Li 2020, _Gradient Descent Maximizes the Margin of Homogeneous Neural Networks_** — 把 max-margin 隐式偏置推广到同质（含 ReLU）深度网络的某种 margin。模块 04 「非线性网络也有 margin 偏置」的依据。
- **Woodworth, Gunasekar, Lee, Moroshko, Savarese, Golan, Soudry & Srebro 2020, _Kernel and Rich Regimes in Overparametrized Models_** — 刻画初始化尺度如何在「核区（惰性，最小 RKHS 范数）」与「富区（特征学习，最小 $\ell_1$）」之间插值。模块 03↔04 衔接的关键。

## 深度泛化：经典界失效与现代界 · Generalization in Deep Learning
- ★ **Zhang, Bengio, Hardt, Recht & Vinyals 2017, _Understanding Deep Learning Requires Rethinking Generalization_** — 引爆当代泛化研究的论文：深度网络能完美拟合<em>随机标签</em>，证明其表达容量足以记忆任意数据，于是基于「容量 ⇒ 泛化」的经典界全部失效（变 vacuous）。模块 05 随机标签 worked 复现它，必读。其 2021 CACM 重刊版加了回顾。
- ★ **Bartlett, Foster & Telgarsky 2017, _Spectrally-Normalized Margin Bounds for Neural Networks_** — 用各层谱范数之积 × 间隔倒数给出与参数计数解耦的泛化界，是 margin 界在深度网络上的代表作。模块 05 谱范数/margin 界的核心。
- ★ **Dziugaite & Roy 2017, _Computing Nonvacuous Generalization Bounds for Deep (Stochastic) Neural Networks with Many More Parameters than Training Data_** — 第一次对真实深度网络算出<em>非平凡</em>（$<1$）的 PAC-Bayes 界，靠优化后验直接最小化界。模块 05 PAC-Bayes 数值界 worked 的直接灵感，必读。
- ★ **Neyshabur, Tomioka & Srebro 2015, _In Search of the Real Inductive Bias: On the Role of Implicit Regularization in Deep Learning_** 与 **Neyshabur, Bhojanapalli, McAllester & Srebro 2017, _Exploring Generalization in Deep Learning_** — 系统提出「容量应由范数而非参数数量度量」，比较多种复杂度度量与真实泛化的相关性。模块 05 「有效容量 / 范数度量」的奠基，必读。
- **McAllester 1999, _PAC-Bayesian Model Averaging_** — PAC-Bayes 框架的提出，给出后验泛化界的原始形式。模块 05 PAC-Bayes 界（含 KL 项与 $\ln(2\sqrt n/\delta)$）的源头。
- **Arora, Ge, Neyshabur & Zhang 2018, _Stronger Generalization Bounds for Deep Nets via a Compression Approach_** — 用噪声稳定性把网络压缩到少量有效参数，给出比谱范数更紧的压缩界。模块 05 压缩界词条的出处。
- **Belkin, Hsu, Ma & Mandal 2019, _Reconciling Modern Machine-Learning Practice and the Classical Bias–Variance Trade-off_** — 命名并系统刻画「double descent」，把经典 U 型曲线与过参数化区缝合。模块 05 双下降理论侧 + C14 现象侧的桥。
- **Nakkiran, Kaplun, Bansal, Yang, Barak & Sutskever 2020, _Deep Double Descent: Where Bigger Models and More Data Hurt_** — 在真实深度网络上系统展示模型/数据/训练时间三种双下降，并提出有效模型复杂度。模块 05 双下降的实证参考。
- **Bartlett, Long, Lugosi & Tsigler 2020, _Benign Overfitting in Linear Regression_** — 精确刻画线性回归中「插值含噪数据却仍泛化」的协方差谱条件。模块 05 benign overfitting 词条、最小范数插值泛化的理论根。
- **Jiang, Neyshabur, Mobahi, Krishnan & Bengio 2020, _Fantastic Generalization Measures and Where to Find Them_** — 大规模实证比较 40+ 种复杂度度量与真实泛化的因果相关性，发现很多直觉度量并不可靠。模块 05 「如何评判一个泛化度量」的方法论参考。
