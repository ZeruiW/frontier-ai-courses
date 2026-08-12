# 参考清单 · References（生成模型）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制，都能在下列文献里找到原始推导与完整模型。本课是**基础**生成模型课；前沿扩散（DiT / score-based / flow 前沿）见 C28，这里只在「研究前沿」小节点到为止、不展开。

## 自编码器与表示学习 · Autoencoders & Representation Learning
- ★ **Hinton & Salakhutdinov 2006, _Reducing the Dimensionality of Data with Neural Networks_** — 用（深度）自编码器做非线性降维的奠基之作，把 AE 从玩具带向实用。读它理解「瓶颈即降维」和 AE 相对 PCA 的非线性优势。
- ★ **Vincent et al. 2008/2010, _Extracting and Composing Robust Features with Denoising Autoencoders_ / _Stacked Denoising Autoencoders_** — 去噪自编码器原始论文。证明「从带噪输入重建干净数据」逼网络学到数据流形结构，并把它与学习数据分布的梯度（score）联系起来——这正是日后扩散/score 模型的思想前身。
- **Baldi & Hornik 1989, _Neural Networks and Principal Component Analysis_** — 证明线性自编码器（MSE 损失）的最优解张成 PCA 主子空间。本课模块 01「线性 AE = PCA」定理的来源，理解 AE 在学什么的关键。
- **Bengio, Courville & Vincent 2013, _Representation Learning: A Review and New Perspectives_** — 表示学习的全景综述。把 AE、稀疏编码、流形学习放进统一框架，建立「为什么要学表示」的世界观。
- **Goodfellow, Bengio & Courville, _Deep Learning_（第 14 章 Autoencoders）** — 教科书级梳理：欠/过完备、正则化 AE、去噪 AE、收缩 AE，以及它们与流形、生成的联系。模块 01 的配套精读。

## 变分自编码器 · VAE
- ★ **Kingma & Welling 2013, _Auto-Encoding Variational Bayes_** — VAE 奠基论文。提出 ELBO + 重参数化技巧，把难算的隐变量后验推断变成可用 SGD 训练的自编码器。本课模块 02 全程在复现它，必读。
- ★ **Rezende, Mohamed & Wierstra 2014, _Stochastic Backpropagation and Approximate Inference in Deep Generative Models_** — 与 VAE 同期、独立提出重参数化与随机变分推断的工作。两篇并读能看清「让梯度穿过采样」这一核心技巧的全貌。
- **Higgins et al. 2017, _β-VAE: Learning Basic Visual Concepts with a Constrained Variational Framework_** — 给 KL 项加权 $\beta$ 以鼓励解耦表示。模块 02 讲后验坍塌与 β-VAE 权衡的依据。
- **Burda, Grosse & Salakhutdinov 2015, _Importance Weighted Autoencoders (IWAE)_** — 用重要性加权收紧 ELBO，得到更紧的似然下界。理解「ELBO 只是一个下界、可以更紧」的延伸。
- **Kingma & Welling 2019, _An Introduction to Variational Autoencoders_（综述/专著）** — 作者亲自写的 VAE 系统教程，从概率图模型到现代变体。想把 VAE 学透的最佳单篇。
- **Bowman et al. 2016, _Generating Sentences from a Continuous Space_** — 最早系统记录并缓解后验坍塌（KL vanishing）的工作。模块 02「后验坍塌」一节的现实案例与对策（KL annealing）来源。

## 生成对抗网络 · GAN
- ★ **Goodfellow et al. 2014, _Generative Adversarial Nets_** — GAN 奠基论文。提出 minimax 对抗框架，证明最优判别器下目标等价于最小化 JS 散度、全局最优在 $p_g=p_{data}$。模块 03 的核心，必读其定理 1。
- ★ **Arjovsky, Chintala & Bottou 2017, _Wasserstein GAN_** — 诊断原始 GAN 在分布不重叠时梯度消失的病根，改用 Wasserstein 距离，大幅稳定训练。理解 GAN 为何不稳、以及怎么修，必读。
- **Radford, Metz & Chintala 2015, _DCGAN_** — 把 GAN 做进卷积网络的工程指南（架构、归一化、激活的经验法则），让 GAN 第一次稳定地生成清晰图像。
- **Salimans et al. 2016, _Improved Techniques for Training GANs_** — 一篮子稳定技巧（feature matching、minibatch discrimination、历史平均等）与 Inception Score 的提出。模块 03「稳定技巧」一节的来源。
- **Gulrajani et al. 2017, _Improved Training of WGANs (WGAN-GP)_** — 用梯度惩罚替代权重裁剪来约束 Lipschitz，是 WGAN 落地的标准做法。
- **Miyato et al. 2018, _Spectral Normalization for GANs_** — 用谱归一化约束判别器 Lipschitz 常数，简单有效，成为现代 GAN 的常备组件。
- **Metz et al. 2016, _Unrolled GANs_ / Arjovsky & Bottou 2017, _Towards Principled Methods..._** — 从理论与方法两面剖析模式坍塌与不稳定。想深究 GAN 病理读这两篇。

## 扩散模型 · Diffusion / Score-based
- ★ **Sohl-Dickstein et al. 2015, _Deep Unsupervised Learning using Nonequilibrium Thermodynamics_** — 扩散模型的真正奠基。首次提出「前向逐步加噪、反向学习去噪」的框架，灵感来自非平衡热力学。读它看清扩散的第一性原理。
- ★ **Ho, Jain & Abbeel 2020, _Denoising Diffusion Probabilistic Models (DDPM)_** — 让扩散一举成为顶级生成模型的论文。给出任意时刻边缘的闭式、把变分界简化为简单的去噪 MSE（ε-prediction）。本课模块 04 全程复现它，必读。
- ★ **Song & Ermon 2019, _Generative Modeling by Estimating Gradients of the Data Distribution (NCSN)_** — 从 score matching 角度独立到达扩散：估计 $\nabla_x\log p(x)$ 并用 Langevin 采样。理解「预测噪声 = 估计 score」的另一视角。
- **Song et al. 2021, _Score-Based Generative Modeling through SDEs_** — 用随机微分方程统一 DDPM 与 score-based，并引出概率流 ODE。是连接扩散与流（模块 05）的桥梁，进阶必读（前沿展开在 C28）。
- **Song, Meng & Ermon 2021, _Denoising Diffusion Implicit Models (DDIM)_** — 把反向过程改成确定性隐式更新，用更少步数采样，并把扩散与 ODE 连起来。模块 04 提到的快速采样与确定性采样依据。
- **Nichol & Dhariwal 2021, _Improved DDPM_** — cosine 噪声调度、学习方差等改进。模块 04「噪声调度」一节的现实参考。

## 归一化流与流匹配 · Flows & Flow Matching
- ★ **Rezende & Mohamed 2015, _Variational Inference with Normalizing Flows_** — 归一化流的奠基论文（也用于改进 VAE 后验）。提出用一串可逆变换 + 变量替换精确算似然。模块 05 流的起点。
- ★ **Lipman et al. 2023, _Flow Matching for Generative Modeling_** — 流匹配奠基论文。提出无模拟地回归（条件）速度场来训练连续流，把 CNF 训练变得像扩散一样简单稳定，并统一了扩散。本课模块 05 的核心，必读。
- ★ **Liu, Gong & Liu 2023, _Flow Straight and Fast: Rectified Flow_** — 取直线概率路径、恒定目标速度，得到可极少步（甚至一步）采样的流。当前文生图主流之一，模块 05 worked 实现的就是它的玩具版。
- **Chen et al. 2018, _Neural Ordinary Differential Equations_** — 连续归一化流（CNF）的源头：用 ODE 定义连续可逆变换、用瞬时变量替换算似然。理解「连续流」概念的必读，也解释了 Flow Matching 之前训练为何昂贵。
- **Dinh et al. 2017, _Density Estimation using Real NVP_ / Kingma & Dhariwal 2018, _Glow_** — 离散归一化流的代表，用精心设计的耦合层让雅可比行列式易算。理解归一化流「可逆 + 易算雅可比」约束的具体实现。
- **Albergo & Vanden-Eijnden 2023, _Stochastic Interpolants_** — 与 Flow Matching 高度相关的统一框架，把扩散与流都看作在两个分布间插值。想深究流与扩散统一视角的进阶读物。

## 综述、教材与统一视角 · Surveys, Texts & Unifying Views
- ★ **Goodfellow, Bengio & Courville, _Deep Learning_（2016，第 20 章 Deep Generative Models）** — 生成模型的经典教科书章节，系统覆盖到扩散之前的全部主流方法。打地基的最佳单一来源。
- **Murphy, _Probabilistic Machine Learning: Advanced Topics_（2023，生成模型相关章节）** — 现代、统一、数学完整地讲 VAE/GAN/流/扩散，含最新视角。想要一本「全在一起」的权威参考选它。
- **Tomczak, _Deep Generative Modeling_（2021/2024 教材）** — 专门讲深度生成模型的教材，从 AE 到扩散循序渐进，配代码。难度与本课最贴合的配套读物。
- **Weng (Lilian) 博客：_From Autoencoder to Beta-VAE_ / _What are Diffusion Models?_ / _Flow-based Deep Generative Models_** — 高质量中英文友好的系统笔记，把上述论文的推导讲得清楚直观。每个模块读前/读后都值得对照。
- **Luo 2022, _Understanding Diffusion Models: A Unified Perspective_** — 把 DDPM 从 VAE/ELBO、score、SDE 多个角度推一遍，是连接模块 02/04 的最佳单篇推导。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU、无需深度学习框架**：全课用 numpy 在 CPU 上**从零**实现（自写反向传播、自写采样循环），在**玩具 1D/2D 分布或小图**上跑到**可复现的收敛**，并与解析参考**对拍**（线性 AE 对拍 PCA 子空间、高斯 KL 对拍闭式、DDPM 前向对拍闭式边缘、Flow Matching 速度场对拍解析目标）。追求「看懂机制」而非 SOTA 画质。
- **可迁移性**：你在 numpy 里验证过的 ELBO、重参数、minimax 更新、ε-prediction、速度场回归，可几乎一对一改写成 PyTorch/JAX，再换上卷积/Transformer 主干与真实数据。本课刻意让实现贴近论文公式。
- **课程衔接**：上游接神经网络与反向传播基础、概率论（KL/期望/高斯）；本课是**基础**生成模型课。下游接 **C28 前沿扩散**（DiT、score-based SDE、概率流 ODE、引导与蒸馏等前沿，本课只点到不展开，避免重复）。模块 04/05 正是为 C28 打的地基。
