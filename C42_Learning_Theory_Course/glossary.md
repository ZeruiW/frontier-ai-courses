# 术语词典 · Glossary（学习理论与优化理论）

> 按主题分组，每条 2–3 句中文释义，英文术语保留原文（理论文献的通用语言）。读 Vapnik / Shalev-Shwartz & Ben-David / Bartlett & Mendelson / Jacot / Soudry 等论文遇到生词回这里查。本课用 numpy 在 CPU 上做数值实验，把每个抽象量（风险、复杂度、收敛率、核）都算出具体数字、与理论预测对拍。

## 风险与学习目标 · Risk & Learning Objectives

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| true / population risk $R(h)$ | 真实风险 / 总体风险 | 假设 $h$ 在数据真实分布 $\mathcal{D}$ 上的期望损失 $R(h)=\mathbb{E}_{(x,y)\sim\mathcal{D}}[\ell(h(x),y)]$。它是我们真正想最小化、却无法直接计算的量（分布未知）。 |
| empirical risk $\hat R_n(h)$ | 经验风险 | $h$ 在有限训练样本上的平均损失 $\hat R_n(h)=\frac1n\sum_i \ell(h(x_i),y_i)$。它是真实风险的无偏估计，但对某个被它选出来的 $h$ 不再无偏（选择偏差）。 |
| generalization gap | 泛化间隙 | 真实风险与经验风险之差 $R(h)-\hat R_n(h)$。学习理论的核心任务就是上界这个差，让「训练好 ⇒ 测试也好」可被证明。 |
| ERM (Empirical Risk Minimization) | 经验风险最小化 | 在假设类 $\mathcal H$ 内最小化经验风险的算法 $\hat h=\arg\min_{h\in\mathcal H}\hat R_n(h)$。几乎所有监督学习训练都是 ERM（或加正则的 ERM）。 |
| excess risk | 超额风险 | $R(\hat h)-\inf_{h\in\mathcal H}R(h)$，学到的假设比类内最优差多少。可拆成估计误差（统计）+ 优化误差两部分。 |
| approximation–estimation tradeoff | 逼近–估计权衡 | 类越大逼近误差（类内最优离贝叶斯最优的差）越小，但估计误差（有限样本带来的间隙）越大。这是「容量」概念的来源，对应经典的偏差–方差权衡。 |
| Bayes risk / Bayes optimal | 贝叶斯风险 / 贝叶斯最优 | 在所有可能函数上能达到的最小真实风险，由数据分布本身决定。任何学习器都无法低于它，是衡量「逼近误差」的基准。 |
| realizable / agnostic | 可实现 / 不可知 | 可实现：存在 $h^\*\in\mathcal H$ 使 $R(h^\*)=0$（标签由类内某函数无噪声生成）。不可知（agnostic）：不假设零误差，只求逼近类内最优。后者更现实，界也更弱（$1/\sqrt n$ 而非 $1/n$）。 |
| surrogate loss | 替代损失 | 用可优化的凸损失（logistic、hinge、平方）替代不可微的 0-1 损失。一致性（calibration）保证最小化替代损失也最小化分类错误。 |

## PAC 学习与样本复杂度 · PAC Learning & Sample Complexity

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| PAC (Probably Approximately Correct) | 可能近似正确 | Valiant 1984 的学习框架：以高概率（$1-\delta$，probably）学到一个误差小于 $\varepsilon$（approximately correct）的假设。它把「学习成功」形式化为概率 + 精度的双参数保证。 |
| sample complexity | 样本复杂度 | 达到 $(\varepsilon,\delta)$-PAC 保证所需的最少样本数 $m(\varepsilon,\delta)$。有限类约 $\frac1\varepsilon(\ln\vert \mathcal H\vert +\ln\frac1\delta)$；VC 类约 $\frac{d}{\varepsilon}$（可实现）或 $\frac{d}{\varepsilon^2}$（不可知）。 |
| uniform convergence | 一致收敛 | 对类内<em>所有</em> $h$ 同时让 $\vert \hat R_n(h)-R(h)\vert $ 一致地小。它是 ERM 泛化的充分条件：一致收敛成立 ⇒ ERM 选出的（数据依赖的）$h$ 也有小间隙。 |
| union bound | 联合界 | $\Pr(\cup_i A_i)\le\sum_i\Pr(A_i)$。把单个假设的 Hoeffding 集中不等式「乘以类大小」推广到有限类一致收敛的最朴素工具，代价是 $\ln\vert \mathcal H\vert $ 项。 |
| Hoeffding's inequality | Hoeffding 不等式 | 对 $[0,1]$ 有界独立随机变量，$\Pr(\vert \bar X-\mathbb E\bar X\vert \ge t)\le 2e^{-2nt^2}$。是「经验均值以 $1/\sqrt n$ 速率集中到期望」的定量来源，几乎所有泛化界的基石。 |
| concentration inequality | 集中不等式 | 一族「随机量高概率接近其期望」的不等式（Hoeffding、Bernstein、McDiarmid、bounded differences）。学习理论用它们把「有限样本估计」变成「高概率保证」。 |
| McDiarmid / bounded differences | McDiarmid 不等式 | 若改动单个样本最多让函数变化 $c_i$，则该函数高概率接近其期望。证明 Rademacher 复杂度界、推导一致收敛的核心工具。 |

## 复杂度度量 · Complexity Measures

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| VC dimension | VC 维 | 假设类能<strong>打散（shatter）</strong>的最大点数：存在这么多点，类能实现其全部 $2^k$ 种标注。它是衡量分类类「容量」的组合量，$\mathbb R^d$ 中线性分类器的 VC 维为 $d+1$。 |
| shattering | 打散 | 类 $\mathcal H$ 打散点集 $S$ 指：$S$ 的每一种 $\pm1$ 标注都能被某个 $h\in\mathcal H$ 实现。打散是 VC 维定义的核心动作。 |
| growth function $\Pi_{\mathcal H}(n)$ | 增长函数 | 类在任意 $n$ 个点上能产生的不同标注数的最大值，$\le 2^n$。它衡量类的「有效假设数」，是把无限类的一致收敛归约到有限情形的桥梁。 |
| Sauer–Shelah lemma | Sauer–Shelah 引理 | 若 VC 维为 $d$，则增长函数被多项式上界 $\Pi_{\mathcal H}(n)\le\sum_{i=0}^d\binom ni\le (en/d)^d$。它把「VC 维有限」翻译成「有效假设数多项式增长」，是 VC 泛化界的关键。 |
| Rademacher complexity | Rademacher 复杂度 | $\hat{\mathfrak R}_S(\mathcal F)=\mathbb E_\sigma\sup_{f\in\mathcal F}\frac1n\sum_i\sigma_i f(x_i)$，$\sigma_i\in\{\pm1\}$ 均匀。衡量类「拟合随机噪声」的能力——能拟合随机标签越强，复杂度越高，泛化越难。它是数据依赖、比 VC 维更紧的复杂度度量。 |
| empirical vs expected Rademacher | 经验 vs 期望 Rademacher | 经验版固定样本 $S$ 取 $\sigma$ 的期望；期望版再对 $S$ 取期望。McDiarmid 保证两者高概率接近，所以可用单份样本估计。 |
| Massart's finite class lemma | Massart 有限类引理 | 对有限向量集 $A$，$\hat{\mathfrak R}(A)\le\frac{\max_{a\in A}\Vert a\Vert _2\sqrt{2\ln\vert A\vert }}{n}$。把有限类的 Rademacher 复杂度用「集大小的对数」上界，是从 Rademacher 推回 VC 风格界的桥。 |
| contraction lemma (Talagrand) | 收缩引理 | 若 $\phi$ 是 $L$-Lipschitz，则 $\hat{\mathfrak R}(\phi\circ\mathcal F)\le L\,\hat{\mathfrak R}(\mathcal F)$。让我们把损失类的复杂度归约到假设类本身的复杂度（剥掉损失函数）。 |
| covering number / metric entropy | 覆盖数 / 度量熵 | 用半径 $\varepsilon$ 的球覆盖函数类所需的最少球数（取对数即熵）。Dudley 积分把覆盖数链式累加成 Rademacher 复杂度，是处理无限类的另一条主线。 |

## 凸优化与几何 · Convex Optimization & Geometry

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| convex function | 凸函数 | 任意两点连线在函数图像之上：$f(\lambda x+(1-\lambda)y)\le\lambda f(x)+(1-\lambda)f(y)$。凸性保证「局部最优=全局最优」，是收敛性证明的前提。 |
| $L$-smoothness | $L$-光滑 | 梯度 $L$-Lipschitz：$\Vert \nabla f(x)-\nabla f(y)\Vert \le L\Vert x-y\Vert $，等价于 $f$ 被一个二次函数从上夹住。它给出 GD 的安全步长上限 $1/L$。 |
| $\mu$-strong convexity | $\mu$-强凸 | $f$ 减去 $\frac\mu2\Vert x\Vert ^2$ 仍凸，等价于被二次函数从下夹住。它把次线性收敛 $O(1/t)$ 提升为线性（指数）收敛。 |
| condition number $\kappa$ | 条件数 | $\kappa=L/\mu$（二次问题即 Hessian 最大/最小特征值之比）。它决定病态程度：GD 迭代数 $\propto\kappa$，加速法 $\propto\sqrt\kappa$。越大越难优化。 |
| gradient / subgradient | 梯度 / 次梯度 | 梯度是可微点的最速上升方向；次梯度把它推广到不可微凸函数（如 hinge、$\ell_1$），是任意支撑超平面的斜率。 |
| stationary point | 驻点 | 梯度为零的点 $\nabla f(x)=0$。凸问题里驻点即全局最优；非凸里可能是局部最优、鞍点或局部最大。 |
| saddle point | 鞍点 | 梯度为零但既非极小也非极大的点（Hessian 有正有负特征值）。高维非凸地形中鞍点远多于局部极小，是非凸优化的主要障碍而非坏的局部极小。 |
| PL condition (Polyak–Łojasiewicz) | PL 条件 | $\frac12\Vert \nabla f(x)\Vert ^2\ge\mu(f(x)-f^\*)$。比强凸弱（允许非凸、多个全局最优），却仍给出 GD 线性收敛。过参数网络的损失常近似满足 PL，是它们「好优化」的一种解释。 |
| Lipschitz continuity | Lipschitz 连续 | 函数变化被输入变化线性控制：$\vert f(x)-f(y)\vert \le L\Vert x-y\Vert $。Lipschitz 常数同时进入优化步长与泛化界（控制损失类复杂度）。 |

## 优化算法与收敛率 · Optimizers & Convergence Rates

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| gradient descent (GD) | 梯度下降 | 沿负梯度迭代 $x_{t+1}=x_t-\eta\nabla f(x_t)$。凸+光滑下步长 $1/L$ 给 $O(1/t)$；再加强凸给线性收敛 $(1-\mu/L)^t$。 |
| stochastic gradient descent (SGD) | 随机梯度下降 | 用单样本/小批量的梯度估计代替全梯度。无偏但有方差；凸下衰减步长给 $O(1/\sqrt t)$，强凸下 $O(1/t)$，是大规模训练的事实标准。 |
| convergence rate | 收敛率 | 误差随迭代数下降的速度：次线性 $O(1/t)$、$O(1/\sqrt t)$，或线性（几何）$O(\rho^t)$。本课每个率都用数值实验对拍理论上界。 |
| sublinear vs linear rate | 次线性 vs 线性收敛 | 次线性：误差 $\sim 1/t$ 多项式衰减（凸）。线性：误差 $\sim\rho^t$ 指数衰减（强凸），每步把误差乘一个 $<1$ 的常数。命名易混：线性收敛其实是指数快。 |
| step size / learning rate | 步长 / 学习率 | 每步沿梯度走多远。太大发散，太小慢；光滑凸的安全上界是 $1/L$，强凸最优是 $2/(L+\mu)$。 |
| momentum / heavy ball | 动量 / 重球法 | $x_{t+1}=x_t-\alpha\nabla f(x_t)+\beta(x_t-x_{t-1})$，给迭代「惯性」。在病态二次上把收敛率从 $\kappa$ 改善到 $\sqrt\kappa$，是加速的雏形。 |
| Nesterov acceleration | Nesterov 加速 | 在「前瞻点」算梯度的动量变体，凸下达到最优 $O(1/t^2)$、强凸下 $O((1-\sqrt{\mu/L})^t)$。是一阶方法的理论下界（Nemirovski–Yudin）可达上限。 |
| noise ball / variance floor | 噪声球 / 方差地板 | 固定步长 SGD 不收敛到精确最优，而是停在一个半径 $\sim\eta\sigma^2$ 的球内振荡。要继续下降必须衰减步长或做迭代平均。 |
| iterate averaging (Polyak–Ruppert) | 迭代平均 | 对 SGD 轨迹取平均 $\bar x_T=\frac1T\sum x_t$，在恒定步长下也能达到最优统计率，并降低方差。 |

## 深度学习理论 · Deep Learning Theory

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| overparameterization | 过参数化 | 参数数远多于训练样本数（$p\gg n$），模型能精确插值（零训练误差）。深度网络的典型工作区，也是经典容量理论失效之处。 |
| NTK (Neural Tangent Kernel) | 神经正切核 | $\Theta(x,x')=\langle\nabla_\theta f(x;\theta),\nabla_\theta f(x';\theta)\rangle$，由网络在初始化处的梯度内积定义。Jacot 2018 证明：宽度趋于无穷时它收敛到一个确定核且训练中保持不变，使网络训练等价于该核的核回归。 |
| infinite-width limit | 无限宽极限 | 隐层宽度 $\to\infty$ 的理想化。此时网络在初始化是高斯过程（NNGP），训练动力学由 NTK 线性化主导——这是把深度网络变成可分析对象的关键简化。 |
| lazy training | 惰性训练 | 在 NTK 区，参数只在初始化附近微动（相对变化 $\to0$），网络近似为参数的线性函数。「惰性」=特征不学习，与「feature learning（特征学习）」区相对。 |
| kernel regression / ridge | 核回归 / 核岭回归 | 用核 $K$ 做的线性回归：$\hat f(x)=k(x,X)(K+\lambda I)^{-1}y$。$\lambda\to0$ 的 ridgeless 解在训练点上插值。无限宽网络的预测由 NTK 核回归给出。 |
| NNGP (NN Gaussian Process) | 神经网络高斯过程 | 无限宽网络在随机初始化下，其输出在函数空间是一个高斯过程，协方差核可逐层递推。它刻画「训练前」的先验，NTK 刻画「训练后」的解。 |
| feature learning | 特征学习 | 训练中隐层表示发生实质改变（与惰性训练相对）。有限宽、大学习率、长时间训练会偏离 NTK 区进入特征学习区，这被认为是深度学习超越固定核的来源。 |
| implicit bias / regularization | 隐式偏置 / 隐式正则 | 在有无穷多个零训练误差解时，优化算法（而非显式正则项）自发偏好其中某一个的倾向。如 GD 在可分数据上偏好 max-margin 解、在最小二乘上偏好最小范数解。 |
| max-margin solution | 最大间隔解 | 把两类分得最开的分隔超平面（hard-margin SVM 解）。Soudry 2018 证明：logistic/指数损失上 GD 的方向 $w_t/\Vert w_t\Vert $ 缓慢（$\sim 1/\log t$）收敛到它。 |
| min-norm interpolation | 最小范数插值 | 在所有插值训练数据的解中范数最小的那个。最小二乘上从零初始化的 GD 收敛到它（$w=X^\top(XX^\top)^{-1}y$），是过参数化下泛化的一种几何解释。 |
| flat minima | 平坦极小 | 损失地形中曲率小、周围一大片都接近最优的极小点。经验上平坦极小泛化更好；与 PAC-Bayes / 最小描述长度有形式联系，但「平坦」的尺度依赖也引发争议。 |
| double descent | 双下降 | 测试误差随模型容量先降后升（经典 U 型）、过插值阈值后<em>再次</em>下降的现象。它直接挑战经典偏差–方差权衡，C14 讲现象、本课从最小范数/有效容量角度讲机制。 |
| interpolation threshold | 插值阈值 | 模型容量刚好能把训练集拟合到零误差的临界点（$p\approx n$）。双下降的峰值出现在这里，越过它进入过参数化的「现代区」。 |

## 当代泛化界 · Modern Generalization Bounds

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| margin-based bound | 间隔界 | 用归一化间隔（margin / 范数）而非参数数量来度量容量的泛化界。对深度网络，Bartlett 1998 / 2017 用各层谱范数之积 × 间隔倒数给出与宽度弱相关的界。 |
| PAC-Bayes bound | PAC-Bayes 界 | 对后验分布 $Q$（随机预测器）的泛化界：间隙被 $\sqrt{(\mathrm{KL}(Q\Vert P)+\ln\frac{2\sqrt n}\delta)/(2n)}$ 之类的量上界，$P$ 是任选的先验。McAllester 1999 提出，是目前对真实网络<em>非平凡</em>（non-vacuous）数值界的主力工具（Dziugaite & Roy 2017）。 |
| KL divergence | KL 散度 | $\mathrm{KL}(Q\Vert P)=\mathbb E_Q\ln\frac{dQ}{dP}$，衡量后验偏离先验的程度。在 PAC-Bayes 里它扮演「复杂度惩罚」，后验越贴近数据无关的先验，界越紧。 |
| non-vacuous bound | 非平凡界 | 数值上 $<1$（对 0-1 损失而言有意义）的泛化界。多数经典界在深度网络上 $\gg1$（平凡/vacuous），能否给出非平凡界是当代理论的试金石。 |
| compression bound | 压缩界 | 若一个网络可被压缩到 $k$ 个有效参数仍保持精度，则其泛化间隙 $\sim\sqrt{k/n}$。Arora 2018 用噪声稳定性形式化压缩，给出比参数计数紧得多的界。 |
| effective capacity | 有效容量 | 模型在某数据/算法下<em>实际</em>表现出的容量，远小于参数计数。随机标签实验（Zhang 2017）证明网络的「最坏情形容量」很大，但 SGD 在真实数据上只动用其一小部分。 |
| spectral norm bound | 谱范数界 | 用各层权重矩阵谱范数之积控制网络 Lipschitz 常数、进而控制容量的一类界（Bartlett 2017、Neyshabur 2018）。是 margin 界的具体实现。 |
| stability (algorithmic) | 算法稳定性 | 换掉一个训练样本时学习算法输出变化的程度。一致稳定 ⇒ 泛化（Bousquet & Elisseeff 2002），是绕过一致收敛、直接从算法性质推泛化的另一条路（SGD 的稳定性 ⇒ 泛化，Hardt 2016）。 |
| benign overfitting | 良性过拟合 | 模型精确插值含噪数据却仍泛化良好的现象。Bartlett 2020 在线性回归里给出精确刻画：当数据协方差谱「又长又平」时插值是良性的。 |

## 实验方法论 · Experimental Methodology（本课特有）

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| theory–experiment matching | 理论–实验对拍 | 本课的方法论核心：把每条界/收敛率算成具体数字，再用 numpy 实测同一个量，用 <code>assert</code> 断言「理论上界 ≥ 实测」或「预测 ≈ 实测」。让抽象不等式变成可证伪的预测。 |
| Monte Carlo estimate | 蒙特卡洛估计 | 用大量随机采样的平均逼近期望（如经验 Rademacher 复杂度对 $\sigma$ 取平均、经验风险间隙对数据集取平均）。本课估计所有「期望型」理论量的通用手段。 |
| toy / synthetic setting | 玩具 / 合成设定 | 用低维、已知真相的合成数据（已知真概念方向、已知最优解、已知贝叶斯风险），使理论量可与 ground truth 对照。先在沙盒校准直觉，是学理论的正确顺序。 |
| ridgeless limit | 无岭极限 | 正则系数 $\lambda\to0$ 的核回归/岭回归。此时解插值训练数据，是研究插值学习器（双下降、良性过拟合、NTK）的标准设定。 |
