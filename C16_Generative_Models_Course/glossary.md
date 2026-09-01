# 术语词典 · Glossary（生成模型）

> 按主题分组，每条 2–3 句释义。读 VAE / GAN / DDPM / Flow Matching 原始论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用 numpy 在玩具分布上从零实现这些概念，术语与真实模型一一对应。

## 总纲：生成 vs 判别 · Generative vs Discriminative

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| generative model | 生成模型 | 学习数据分布 $p(x)$ 本身、并能从中采样出新样本的模型。与只学条件标签 $p(y\mid x)$ 的判别模型相对。生成模型既可用于采样合成，也可（部分模型）给出样本的似然。 |
| discriminative model | 判别模型 | 只建模决策边界或条件分布 $p(y\mid x)$，不关心 $x$ 本身怎么来。分类器、回归器属此类；它无法凭空「画」出一个新样本。 |
| density estimation | 密度估计 | 估计数据点的概率密度 $p(x)$。显式似然模型（VAE 的下界、流模型的精确似然、扩散的变分界）直接或间接做这件事；GAN 则回避它。 |
| sampling | 采样 | 从模型分布中抽出新样本 $x\sim p_\theta(x)$。是生成模型的核心能力；不同族的采样机制差异巨大（解码一个隐变量、跑一条反向扩散链、积分一条 ODE）。 |
| latent variable | 隐变量 | 不被直接观测、用于解释数据生成过程的变量 $z$（如 VAE 的隐编码、GAN 的噪声输入）。先采 $z$ 再经解码器映射到数据空间，是多数生成模型的生成范式。 |
| prior / posterior | 先验 / 后验 | 先验 $p(z)$ 是对隐变量的事前假设（常取标准正态）；后验 $p(z\mid x)$ 是看到数据 $x$ 后对 $z$ 的更新信念。VAE 用一个可学的 $q_\phi(z\mid x)$ 近似难算的真后验。 |
| likelihood / log-likelihood | 似然 / 对数似然 | $p_\theta(x)$ 在给定数据下作为参数函数的值；取对数便于优化与数值稳定。最大化对数似然是显式生成模型的经典目标，但对隐变量模型 $p_\theta(x)=\int p_\theta(x,z)dz$ 往往不可直接算。 |
| implicit vs explicit model | 隐式 / 显式模型 | 显式模型给出（或下界）样本的似然（VAE、流、扩散）；隐式模型只提供一个采样器、不写出密度（GAN）。这条分界决定了它们各自的训练目标与评估方式。 |
| manifold hypothesis | 流形假设 | 高维真实数据（图像、语音）其实集中在一个低维流形附近。生成模型的隐空间维度远小于数据维度，正是对这个假设的利用。 |

## 自编码器 · Autoencoders

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| autoencoder (AE) | 自编码器 | 把输入压缩成低维编码再重建回来的神经网络，由编码器 $f$、瓶颈 $z$、解码器 $g$ 组成，训练目标是最小化重建误差 $\|x-g(f(x))\|^2$。它学的是表示与压缩，本身不是生成模型。 |
| encoder / decoder | 编码器 / 解码器 | 编码器把数据映到低维隐空间 $z=f(x)$；解码器把隐编码映回数据空间 $\hat{x}=g(z)$。生成模型几乎都有一个「解码」方向：从隐变量造出样本。 |
| bottleneck | 瓶颈 | 自编码器中维度被压窄的隐层。它强迫网络丢弃冗余、只保留重建所必需的信息，是表示学习与降维的来源。 |
| reconstruction loss | 重建损失 | 度量重建 $\hat{x}$ 与原输入 $x$ 的差距，常用 MSE（对应高斯似然）或交叉熵（对应伯努利似然）。它是 AE 与 VAE 重建项的共同核心。 |
| undercomplete / overcomplete | 欠完备 / 过完备 | 瓶颈维度小于（欠完备）或大于（过完备）输入维度。欠完备靠维度约束学表示；过完备需正则（稀疏、去噪）才不退化成恒等映射。 |
| denoising autoencoder (DAE) | 去噪自编码器 | 训练时给输入加噪、要求从带噪输入重建出干净原图。它逼网络学到数据流形的结构而非死记，是连接自编码与「学习数据分布梯度（score）」的桥梁。 |
| representation learning | 表示学习 | 学到对下游任务有用的数据表示（特征）。自编码器、对比学习等用无标签数据学表示；瓶颈编码 $z$ 即一种学到的表示。 |
| linear autoencoder = PCA | 线性自编码器与 PCA | 当编码器/解码器都线性、损失为 MSE 时，AE 的最优解张成与 PCA 相同的主子空间（principal subspace）。这是理解 AE「在学什么」的关键定理：非线性 AE 是 PCA 的非线性推广。 |
| principal subspace | 主子空间 | 数据方差最大的若干方向张成的子空间，PCA 的投影目标。线性 AE 的瓶颈收敛到它（但未必是单个主成分方向，可差一个旋转）。 |
| tied weights | 权重绑定 | 让解码器权重取编码器权重的转置 $W_{dec}=W_{enc}^\top$，减少参数、并与 PCA 的正交投影更贴合。是早期 AE 的常用约束。 |

## 变分自编码器 · VAE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| variational autoencoder (VAE) | 变分自编码器 | 给自编码器加上概率结构：编码器输出隐变量的分布 $q_\phi(z\mid x)$ 而非一个点，先验 $p(z)=\mathcal{N}(0,I)$，从而既能重建又能从先验采样生成。Kingma & Welling 2013 提出。 |
| ELBO (Evidence Lower BOund) | 证据下界 | 对数似然 $\log p_\theta(x)$ 的一个可优化下界：$\mathbb{E}_{q}[\log p(x\mid z)] - \mathrm{KL}(q\,\|\,p)$。最大化它等价于「尽量拉高似然」。VAE 的全部训练就是最大化 ELBO。 |
| variational inference | 变分推断 | 用一族可优化的简单分布 $q_\phi$ 去逼近难算的真后验 $p(z\mid x)$，把推断问题变成优化问题。ELBO 正是这套框架的目标函数。 |
| reconstruction term | 重建项 | ELBO 中的 $\mathbb{E}_{q_\phi(z\mid x)}[\log p_\theta(x\mid z)]$，鼓励从隐编码能重建出原数据。高斯解码下退化为 MSE，伯努利解码下为交叉熵。 |
| KL term / regularizer | KL 项 / 正则项 | ELBO 中的 $\mathrm{KL}(q_\phi(z\mid x)\,\|\,p(z))$，把后验拉向先验，使隐空间规整、可从先验采样。它是 VAE 区别于普通 AE 的关键。 |
| reparameterization trick | 重参数化技巧 | 把随机采样 $z\sim\mathcal{N}(\mu,\sigma^2)$ 改写成 $z=\mu+\sigma\odot\epsilon,\ \epsilon\sim\mathcal{N}(0,I)$，把随机性挪到与参数无关的 $\epsilon$ 上，从而梯度能穿过采样、可反向传播。VAE 可训练的核心技巧。 |
| closed-form KL (Gaussian) | 高斯 KL 闭式解 | 当 $q=\mathcal{N}(\mu,\sigma^2)$、$p=\mathcal{N}(0,1)$ 时，$\mathrm{KL}=\tfrac12\sum(\mu^2+\sigma^2-1-\log\sigma^2)$。有解析式，无需采样估计，是 VAE 训练高效稳定的原因之一。 |
| posterior collapse | 后验坍塌 | 解码器过强或 KL 权重过大时，模型干脆让 $q_\phi(z\mid x)\approx p(z)$、忽略 $z$，隐变量不携带信息。表现为 KL 项趋零、重建靠解码器自身，是 VAE 的典型病。 |
| beta-VAE ($\beta$-VAE) | β-VAE | 给 KL 项乘一个权重 $\beta$：$\mathcal{L}=\text{重建}-\beta\,\mathrm{KL}$。$\beta>1$ 更强地正则隐空间、鼓励解耦表示（disentanglement），但过大会加重后验坍塌、损害重建。Higgins 等 2017。 |
| amortized inference | 摊销推断 | 用一个共享的编码器网络对所有 $x$ 直接输出其后验参数，而非对每个 $x$ 单独优化。「摊销」了推断成本，是 VAE 编码器的本质。 |
| disentanglement | 解耦表示 | 隐空间不同维度对应数据的不同独立生成因子（如角度、粗细）。β-VAE 等通过加强先验约束鼓励它，便于可解释与可控生成。 |

## 生成对抗网络 · GAN

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| generative adversarial network (GAN) | 生成对抗网络 | 让生成器 $G$ 与判别器 $D$ 对抗博弈：$G$ 把噪声映成假样本骗过 $D$，$D$ 学着分辨真假，二者交替提升，最终 $G$ 生成的分布逼近真实分布。Goodfellow 等 2014 提出，是隐式（无似然）生成模型代表。 |
| generator / discriminator | 生成器 / 判别器 | $G(z)$ 把先验噪声 $z$ 映到数据空间造样本；$D(x)\in(0,1)$ 估计 $x$ 来自真实数据的概率。训练是二者的对抗：$D$ 求分得越准，$G$ 求骗得越狠。 |
| minimax objective | 极小极大目标 | GAN 的博弈写成 $\min_G\max_D\ \mathbb{E}_{x\sim p_{data}}[\log D(x)]+\mathbb{E}_{z}[\log(1-D(G(z)))]$。$D$ 想最大化、$G$ 想最小化同一个值函数，是一个二人零和博弈。 |
| optimal discriminator | 最优判别器 | 固定 $G$ 时，$D^*(x)=\frac{p_{data}(x)}{p_{data}(x)+p_g(x)}$。把它代回值函数，目标等价于最小化真实分布与生成分布的 Jensen–Shannon 散度。这是 GAN「在优化什么」的理论解释。 |
| Jensen–Shannon divergence (JSD) | JS 散度 | 一种对称、有界的分布差异度量。原始 GAN 在最优 $D$ 下等价于最小化 $p_{data}$ 与 $p_g$ 的 JS 散度——这也暴露了它在两分布不重叠时梯度消失的隐患。 |
| mode collapse | 模式坍塌 | 生成器只学会产出真实分布的少数几个模式（甚至单一样本），丢失多样性。是 GAN 最典型、最难缠的失败模式，多峰目标分布上尤其明显。 |
| training instability | 训练不稳定 | GAN 的对抗目标没有单一可下降的损失，$D$ 与 $G$ 此消彼长，易振荡、发散或一方碾压另一方。表现为损失乱跳、生成质量忽好忽坏。 |
| non-saturating loss | 非饱和损失 | 把 $G$ 的目标从最小化 $\log(1-D(G(z)))$ 改成最大化 $\log D(G(z))$。训练初期 $D$ 很强时前者梯度近零（饱和），后者仍有强梯度，是几乎所有实现的默认做法。 |
| Nash equilibrium | 纳什均衡 | 博弈中任何一方单方面改变策略都无法获益的状态。GAN 的理想终点是 $G$ 完美还原数据分布、$D$ 处处输出 $1/2$ 的均衡，但实践中很难精确到达。 |
| Wasserstein distance / WGAN | Wasserstein 距离 / WGAN | 用最优传输的「推土机距离」替代 JS 散度度量分布差异；即便两分布不重叠也给出有意义的梯度，缓解训练不稳定。WGAN（Arjovsky 2017）是稳定 GAN 的里程碑。 |
| spectral normalization / gradient penalty | 谱归一化 / 梯度惩罚 | 约束判别器的 Lipschitz 常数以稳定训练的两类常用技巧（SN-GAN、WGAN-GP）。本质都是别让 $D$ 太「陡峭」而给出爆炸或消失的梯度。 |

## 扩散模型 · Diffusion / DDPM

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| diffusion model | 扩散模型 | 一族生成模型：定义一个把数据逐步加噪成纯噪声的前向过程，再学一个把噪声逐步去噪还原成数据的反向过程；采样即从噪声出发跑反向链。Sohl-Dickstein 2015 奠基，Ho 2020（DDPM）发扬。 |
| forward / diffusion process | 前向 / 扩散过程 | 固定的、无需学习的马尔可夫链 $q(x_t\mid x_{t-1})=\mathcal{N}(\sqrt{1-\beta_t}\,x_{t-1},\beta_t I)$，每步注入少量高斯噪声，$T$ 步后 $x_T$ 近似标准正态。 |
| reverse / denoising process | 反向 / 去噪过程 | 可学习的链 $p_\theta(x_{t-1}\mid x_t)$，每步去掉一点噪声。训练好后从 $x_T\sim\mathcal{N}(0,I)$ 一路采样回 $x_0$ 即生成新样本。 |
| closed-form marginal $q(x_t\mid x_0)$ | 任意时刻边缘的闭式 | 前向过程可一步跳到任意 $t$：$x_t=\sqrt{\bar\alpha_t}\,x_0+\sqrt{1-\bar\alpha_t}\,\epsilon$，其中 $\bar\alpha_t=\prod_{s\le t}(1-\beta_s)$。无需逐步模拟即可生成训练样本，是 DDPM 高效训练的关键。 |
| noise schedule | 噪声调度 | 一组随步数变化的方差 $\{\beta_t\}$（线性、cosine 等），决定加噪快慢。调度的好坏显著影响样本质量与所需步数。 |
| noise prediction ($\epsilon$-prediction) | 噪声预测 | DDPM 让网络 $\epsilon_\theta(x_t,t)$ 预测加在 $x_t$ 上的噪声 $\epsilon$，训练目标是简单的 $\mathbb{E}\|\epsilon-\epsilon_\theta(x_t,t)\|^2$。这是 DDPM 出奇有效又好训的形式。 |
| variational bound (diffusion) | 扩散的变分界 | 扩散的对数似然有一个类 ELBO 的变分下界，由各步 KL 之和构成；DDPM 证明它在重参数化后简化为上面的去噪 MSE。把扩散与 VAE 在数学上连了起来。 |
| score function / score matching | 得分函数 / 得分匹配 | $\nabla_x\log p(x)$，指向数据概率上升最快的方向。预测噪声等价于（按尺度）估计 score，所以 DDPM 与 score-based 模型（Song & Ermon）是一回事的两种视角。 |
| reverse sampling step | 反向采样步 | 给定 $x_t$ 与预测的 $\epsilon_\theta$，按公式算出 $x_{t-1}$ 的均值并加入适量噪声。重复 $T$ 步把噪声变成样本。 |
| DDIM | —— | 一种确定性（或可调随机性）的快速采样器，把反向过程改写成非马尔可夫的隐式更新，用更少步数采样。Song 2021；是把扩散与 ODE/流连起来的关键一步。 |
| signal-to-noise ratio (SNR) | 信噪比 | $\bar\alpha_t/(1-\bar\alpha_t)$，衡量 $x_t$ 里还剩多少原信号。它随 $t$ 单调下降，是分析噪声调度与损失加权的统一语言。 |

## 流匹配与连续归一化流 · Flow Matching & CNF

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| normalizing flow | 归一化流 | 用一串可逆变换把简单分布（高斯）映成复杂数据分布，靠变量替换公式精确算出似然。需要可逆且雅可比行列式易算，限制了网络结构（RealNVP、Glow）。Rezende & Mohamed 2015。 |
| change of variables | 变量替换公式 | $\log p_x(x)=\log p_z(z)-\log\bigl\vert \det \tfrac{\partial f}{\partial z}\bigr\vert $。可逆变换下密度如何变换的法则，是归一化流能精确算似然的数学基础。 |
| continuous normalizing flow (CNF) | 连续归一化流 | 把离散的可逆层取极限，用一个 ODE $\tfrac{dx}{dt}=v_\theta(x,t)$ 定义连续形变；样本沿向量场 $v$ 流动。似然由瞬时变量替换给出，但训练需积分 ODE，曾经很贵。Chen 等 2018（Neural ODE）。 |
| vector field / velocity field | 向量场 / 速度场 | $v(x,t)$：在时间 $t$、位置 $x$ 处粒子的移动速度。CNF / Flow Matching 学的就是它——一个把噪声分布「搬运」成数据分布的速度场。 |
| probability path | 概率路径 | 一条随时间 $t\in[0,1]$ 从先验 $p_0$（噪声）连续过渡到数据 $p_1$ 的分布序列 $\{p_t\}$。Flow Matching 先选定一条好算的路径，再回归能实现它的速度场。 |
| flow matching | 流匹配 | 一种训练 CNF 的无模拟（simulation-free）方法：不积分 ODE，而是直接回归目标速度场。Lipman 等 2023 提出，把连续流的训练变得像扩散一样简单稳定。 |
| conditional flow matching (CFM) | 条件流匹配 | Flow Matching 的可操作形式：对每个数据点 $x_1$ 构造一条条件概率路径（如把噪声 $x_0$ 直线插值到 $x_1$），回归其条件速度场；其期望恰好等于难算的边缘速度场。 |
| rectified flow | 直流 / 整流流 | 取最简单的直线路径 $x_t=(1-t)x_0+t x_1$、目标速度恒为 $x_1-x_0$ 的 Flow Matching。路径笔直，采样可用极少步数甚至一步，是当前文生图主流之一。Liu 等 2023。 |
| ODE sampling | ODE 采样 | 从噪声 $x_0\sim p_0$ 出发，用数值积分器（如 Euler：$x_{t+\Delta}=x_t+\Delta\,v_\theta(x_t,t)$）沿学到的速度场积分到 $t=1$，得到数据样本。确定性、步数可控。 |
| Euler / Heun integrator | Euler / Heun 积分器 | 解 ODE 的数值方法。Euler 一阶最简单；Heun（改进欧拉）二阶更准。采样步数与积分器阶数共同决定速度-质量权衡。 |
| transport map | 传输映射 | 把一个分布的质量搬到另一个分布的映射。最优传输给出「代价最小」的搬法；Flow Matching / rectified flow 学的就是一种（近似最优的）传输。 |
| simulation-free training | 无模拟训练 | 训练时无需真正跑（积分）生成过程，只需在随机时刻 $t$ 上做一次回归。扩散与 Flow Matching 共享这一优点，是它们比早期 CNF 好训的根本原因。 |

## 训练与评估通用 · Training & Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Monte Carlo estimate | 蒙特卡洛估计 | 用有限采样的样本均值近似一个期望（如 ELBO 的重建项、Flow Matching 的回归损失）。生成模型训练里无处不在；方差大小直接影响梯度质量。 |
| KL divergence | KL 散度 | $\mathrm{KL}(q\|p)=\mathbb{E}_q[\log\frac{q}{p}]\ge 0$，度量用 $p$ 近似 $q$ 的信息损失，不对称。VAE 的正则项、扩散变分界、变分推断都建立在它上面。 |
| Gaussian reparameterization | 高斯重参数 | 把对高斯的采样写成 $\mu+\sigma\epsilon$ 的可微形式（见 VAE）。同一思想也支撑扩散的前向闭式与 Flow Matching 的条件路径采样。 |
| mode coverage vs sample quality | 模式覆盖 vs 样本质量 | 生成模型的两难：覆盖数据所有模式（多样性）与每个样本都逼真（保真度）常此消彼长。VAE 偏模糊但覆盖广，GAN 偏锐利但易坍塌，扩散两者兼顾但慢。 |
| FID / Inception Score | FID / IS | 评估生成图像质量的常用指标：FID 比较生成与真实特征分布的距离（越低越好），IS 衡量清晰度与多样性。本课玩具数据用更直接的分布距离替代。 |
| log-likelihood (nats/bits) | 对数似然（nats/bits per dim） | 显式模型在测试集上的对数似然，衡量密度估计好坏。流模型与扩散可报告它；GAN 不能。 |
| teacher forcing / ancestral sampling | 祖先采样 | 按图模型的拓扑顺序逐变量采样（如扩散从 $x_T$ 到 $x_0$ 逐步）。与之相对的是用 ODE/求解器一次性积分得到样本。 |
