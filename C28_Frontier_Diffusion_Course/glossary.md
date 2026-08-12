# 术语词典 · Glossary（扩散与流前沿）

> 按主题分组，每条 2–3 句释义。读 SD/DiT/Flow Matching/Consistency 论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用 numpy 在 CPU 上做玩具复现，但术语与真实前沿模型一一对应。基础的 DDPM/score matching 术语见 C16，这里聚焦前沿。

## 扩散基础回顾 · Diffusion Recap（详见 C16）

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| diffusion model | 扩散模型 | 一类生成模型：定义一个把数据逐步加噪到纯高斯的前向过程，再学一个神经网络逆转它、从噪声逐步去噪生成样本。本课的所有前沿技术都建立在这个框架上。 |
| forward / noising process | 前向 / 加噪过程 | 把干净数据 $x_0$ 按预定噪声表逐步加高斯噪声，$T$ 步后变成近似标准高斯。它无参数、闭式可采样：$x_t=\sqrt{\bar\alpha_t}x_0+\sqrt{1-\bar\alpha_t}\,\epsilon$。 |
| reverse / denoising process | 反向 / 去噪过程 | 用神经网络从 $x_t$ 预测并去除噪声、逐步还原 $x_0$ 的过程。训练目标通常是预测被加入的噪声 $\epsilon$（或等价的 score / $x_0$ / $v$）。 |
| DDPM | —— | Denoising Diffusion Probabilistic Models（Ho 2020）。把扩散落实为可训练的去噪模型，奠定了现代扩散的训练目标（预测噪声的简单 MSE）与采样流程。 |
| noise schedule $\beta_t,\bar\alpha_t$ | 噪声表 | 规定每一步加多少噪声的序列。$\bar\alpha_t=\prod_{s\le t}(1-\beta_s)$ 是从 $x_0$ 直接跳到 $x_t$ 的信号保留系数，决定 SNR 随时间的衰减。 |
| score function | 分数函数 | 对数密度的梯度 $\nabla_x\log p(x)$。扩散的去噪等价于估计加噪分布的 score（Song & Ermon），是连接扩散、flow、能量模型的统一语言。 |
| $\epsilon$-prediction / $v$-prediction / $x_0$-prediction | 噪声/速度/原图预测 | 去噪网络输出的三种等价参数化。$v=\sqrt{\bar\alpha_t}\,\epsilon-\sqrt{1-\bar\alpha_t}\,x_0$ 的 $v$-pred 在高低噪声两端都数值稳定，被 SD2/蒸馏广泛采用。 |
| SNR (signal-to-noise ratio) | 信噪比 | $\bar\alpha_t/(1-\bar\alpha_t)$，刻画第 $t$ 步还剩多少信号。不同时间步的 loss 权重、噪声表设计、采样步分配都围绕 SNR 展开。 |
| classifier guidance | 分类器引导 | Dhariwal & Nichol 2021 提出：用一个在带噪图上训练的分类器的梯度，把采样推向目标类别。CFG 是它的「无分类器」替代品（模块 04）。 |

## Latent Diffusion 与 VAE · Latent Diffusion & VAE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| latent diffusion (LDM) | 隐空间扩散 | Rombach 2022 提出：不在像素空间而在 VAE 压缩出的低维 latent 上做扩散。把昂贵的扩散从百万维降到几千维，是 Stable Diffusion 的核心、让高分辨率生成在消费级 GPU 上可行。 |
| Stable Diffusion (SD) | —— | 基于 LDM 的开源文生图模型族（SD1.x/2.x 用 UNet，SD3 用 DiT+flow）。由 VAE 编解码器、latent 去噪骨干、文本编码器（CLIP/T5）三部分组成，是开源生成生态的事实标准。 |
| VAE (Variational Autoencoder) | 变分自编码器 | 一个编码器把图像压成 latent、一个解码器还原的自编码器，用 KL 正则让 latent 分布规整。LDM 用它做「感知压缩」：去掉人眼不敏感的高频细节，保留语义结构。 |
| encoder / decoder $\mathcal{E},\mathcal{D}$ | 编码器 / 解码器 | $\mathcal{E}$ 把图像 $x$ 映到 latent $z=\mathcal{E}(x)$，$\mathcal{D}$ 把 latent 还原 $\hat x=\mathcal{D}(z)$。扩散只在 $z$ 空间进行，采样完再用 $\mathcal{D}$ 一次性解码回像素。 |
| perceptual compression | 感知压缩 | LDM 的两阶段分工里 VAE 负责的那一半：丢弃人眼不敏感的高频细节、保留感知上重要的结构。与「语义压缩」（扩散负责语义内容生成）分开，各司其职。 |
| downsampling factor $f$ | 下采样因子 | VAE 把图像每边压缩的倍数（SD 用 $f=8$：$512^2\to64^2$）。$f$ 越大 latent 越小、扩散越省算力，但太大会丢失细节、解码模糊。是 LDM 最关键的超参之一。 |
| KL / VQ regularization | KL / VQ 正则 | 约束 VAE latent 分布的两种方式：KL 让 latent 接近高斯（连续 latent，SD 用），VQ 把 latent 量化到码本（离散 latent）。防止 latent 空间方差任意大、利于下游扩散。 |
| latent scaling factor | latent 缩放系数 | 把 VAE 输出的 latent 乘一个常数（SD 约 0.18215）使其方差≈1，匹配扩散假设的单位方差噪声。看似工程细节，不缩放会让扩散训练发散。 |
| two-stage training | 两阶段训练 | LDM 先单独训好 VAE（自编码重建），冻结后再在其 latent 上训扩散。解耦了「压缩」与「生成」，让扩散专注于建模 latent 分布。 |

## 条件注入与文本对齐 · Conditioning

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| conditioning | 条件 | 喂给生成模型用于控制输出的额外信息：类别标签、文本 prompt、时间步、图像（图生图）等。如何把条件高效注入去噪网络是架构设计的核心问题。 |
| cross-attention | 交叉注意力 | SD 把文本注入图像的方式：图像 token 作 query、文本 token 作 key/value 做注意力，让每个图像位置「查阅」相关词。是 UNet 时代文本条件的主力机制。 |
| text encoder (CLIP / T5) | 文本编码器 | 把 prompt 编码成向量序列供扩散条件用。SD1/2 用 CLIP text encoder，SD3/Flux 叠加 T5-XXL 以增强长文本与拼写理解。文本理解的上限很大程度由它决定。 |
| timestep embedding | 时间步嵌入 | 把当前去噪步 $t$（标量）编码成向量喂给网络，让同一套权重知道「现在噪声有多大」。常用正弦位置编码 + MLP，与 Transformer 的位置编码同源。 |
| adaptive normalization (AdaLN) | 自适应归一化 | 用条件向量（如时间步+类别）预测归一化层的缩放 $\gamma$ 与平移 $\beta$，从而把条件注入每一层。DiT 的核心条件机制，比 cross-attention 更省参数。 |
| adaLN-zero | —— | DiT 的关键技巧：把 adaLN 预测的残差缩放系数初始化为 0，使每个 block 初始等于恒等映射。训练初期网络≈恒等、稳定，是 DiT 能稳定 scale 到很深的原因。 |
| FiLM (Feature-wise Linear Modulation) | 特征级线性调制 | 用条件预测逐通道的仿射变换 $\gamma\odot h+\beta$ 来调制特征。AdaLN 是它在归一化层上的实例，是「轻量条件注入」的通用思路。 |
| guidance | 引导 | 在采样时放大条件信号、使输出更贴合条件的技术总称。包括需要额外分类器的 classifier guidance 与不需要的 classifier-free guidance（模块 04）。 |

## Diffusion Transformer · DiT

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Diffusion Transformer (DiT) | —— | Peebles & Xie 2023 提出：用 Transformer（而非 U-Net）作扩散去噪骨干。把 latent 切成 patch token 序列、用标准 Transformer block + adaLN 条件处理。SD3/Flux/SoRA 的共同骨架。 |
| patchify | 分块嵌入 | 把 $H\times W\times C$ 的 latent 切成 $p\times p$ 的不重叠小块、每块展平后线性投影成一个 token。与 ViT 的做法相同，是把图像「序列化」喂给 Transformer 的第一步。 |
| patch size $p$ | patch 边长 | patchify 的块大小（DiT 常用 2/4/8）。$p$ 越小 token 越多、计算越贵但越精细；token 数 $=(H/p)\times(W/p)$，直接决定注意力的序列长度与算力。 |
| positional embedding | 位置嵌入 | 给每个 patch token 加上表示其空间位置的向量（DiT 用固定正弦 2D 位置编码）。因为注意力本身对顺序不敏感，必须显式注入位置，否则模型不知道 patch 在图中的哪里。 |
| unpatchify | 反分块 | DiT 输出端的逆操作：把每个 token 投影回 $p\times p\times C$ 的块、按位置拼回完整 latent 张量。与 patchify 一进一出，保证输入输出形状一致。 |
| DiT block | DiT 模块 | 一个 DiT 层：自注意力 + MLP，两处归一化都换成 adaLN（由时间步+条件调制），残差路径用 adaLN-zero 缩放。堆叠 $N$ 个构成骨干。 |
| scaling law (for DiT) | 缩放律 | Peebles 发现 DiT 的生成质量（FID）随计算量（Gflops，由深度/宽度/patch 数决定）平滑下降。这种可预测的 scaling 是它取代 U-Net 成为大模型骨干的关键论据。 |
| U-Net | —— | 带跳跃连接的编码-解码卷积网络，扩散早期的主力骨干（SD1/2）。擅长局部纹理、有归纳偏置，但 scaling 行为不如 Transformer 平滑、长程依赖弱。DiT 是它的替代。 |
| inductive bias | 归纳偏置 | 模型架构自带的、关于数据的先验假设。卷积有「局部性+平移等变」偏置（U-Net 强），Transformer 偏置弱、更依赖数据与规模——大数据下后者反而更能 scale。 |
| MM-DiT (multimodal DiT) | 多模态 DiT | SD3 用的 DiT 变体：图像 token 与文本 token 拼在一起做联合注意力（双流），让文本与图像深度交互，比单向 cross-attention 对齐更好。 |

## Flow Matching 与 ODE · Flow Matching & ODE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| flow matching (FM) | 流匹配 | Lipman 2023 提出的生成框架：直接回归一个把噪声分布连续变形到数据分布的「速度场」，无需扩散的随机过程与变分下界。训练是简单的 MSE 回归，与扩散统一但更直接。 |
| continuous normalizing flow (CNF) | 连续归一化流 | 用一个 ODE $\mathrm{d}x=v_\theta(x,t)\mathrm{d}t$ 把简单分布连续变形到复杂分布的生成模型。flow matching 给了它一个无需模拟 ODE 即可训练的目标，使其大规模可行。 |
| velocity field / vector field $v(x,t)$ | 速度场 / 向量场 | flow matching 学习的对象：在时刻 $t$、位置 $x$ 处样本应当移动的方向与速率。沿着它积分 ODE，噪声就被「流」成数据。 |
| probability path $p_t$ | 概率路径 | 一条随时间从噪声分布 $p_0$ 连续演化到数据分布 $p_1$ 的分布族。flow matching 选定一条路径（如高斯插值），再学产生它的速度场。 |
| conditional flow matching (CFM) | 条件流匹配 | FM 的可训练形式：把难算的边际速度场目标，换成对每个数据点的「条件」速度场回归（其期望等于边际目标）。这是 FM 能用简单 MSE 训练的关键定理。 |
| linear / straight-line interpolation | 直线插值 | 取 $x_t=(1-t)x_0+t\,x_1$（噪声到数据的直线）作概率路径。其条件速度场恒为 $x_1-x_0$（常向量），是 rectified flow 与 SD3 用的最简路径。 |
| rectified flow | 整流 / 直线流 | Liu 2023 提出：用直线插值路径学速度场，并通过 reflow 迭代把流「拉直」，使 ODE 轨迹接近直线、从而极少步数即可采样。SD3 采用其路径。 |
| reflow | 重流 | rectified flow 的拉直操作：用当前模型把噪声采样成数据、再把这些(噪声,数据)配对重新训练。每轮 reflow 让轨迹更直、采样步数更省，可迭代多次。 |
| ODE sampling / solver | ODE 采样 / 求解器 | 从噪声出发对学到的速度场做数值积分（Euler、Heun、RK45 等）生成样本。步数=求解器调用次数，是质量-速度权衡的旋钮；轨迹越直，越少步够用。 |
| Euler / Heun method | 欧拉 / Heun 法 | 两种 ODE 数值积分：Euler 一阶（每步走 $v\cdot\Delta t$），Heun 二阶（用中点校正，更准）。采样器选择直接影响相同步数下的样本质量。 |
| transport / optimal transport (OT) | 运输 / 最优运输 | 把一个分布「搬」成另一个分布的代价最小方案。直线插值对应 OT 位移，rectified flow 的拉直与 OT 思想相通，是 FM 几何直觉的来源。 |
| probability flow ODE | 概率流 ODE | 与扩散 SDE 共享同一边际分布的确定性 ODE（Song 2021）。它把扩散也写成一个 ODE，从而扩散与 flow matching 在这个视角下统一——都是学速度场、积分 ODE。 |

## 引导与可控生成 · Guidance

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| classifier-free guidance (CFG) | 无分类器引导 | Ho & Salimans 2022 提出：训练时随机丢弃条件、让一个网络同时学条件与无条件预测；采样时把两者外推 $\epsilon=\epsilon_\varnothing+w(\epsilon_c-\epsilon_\varnothing)$ 来放大条件。无需额外分类器，是当代可控生成的默认开关。 |
| guidance scale $w$ | 引导强度 | CFG 外推的系数。$w=0$ 退化为无条件，$w=1$ 为普通条件采样，$w>1$ 放大条件信号。典型 7~12；越大越贴合 prompt 但多样性下降、易过饱和。 |
| unconditional prediction $\epsilon_\varnothing$ | 无条件预测 | 把条件置空（null token / 空 prompt）时网络的去噪预测。CFG 用它作「基线」，条件预测相对它的偏移就是「条件指明的方向」，放大这个偏移即引导。 |
| null / empty conditioning | 空条件 | 训练 CFG 时以一定概率（如 10%）把条件替换成的占位符（空文本或可学习的 null embedding）。让同一网络具备无条件生成能力，是 CFG 可行的前提。 |
| negative prompt | 负向提示 | 把 CFG 的无条件基线换成「不想要的内容」的条件预测，从而主动远离它。如负 prompt 写 “blurry, low quality” 可推开模糊低质，是实用的可控手段。 |
| oversaturation / over-guidance | 过饱和 / 过度引导 | $w$ 过大时图像颜色过浓、对比过强、细节崩坏的伪影。源于外推把预测推出了数据流形。解法有动态 CFG、CFG rescale、限制引导的时间区间等。 |
| dynamic / scheduled CFG | 动态引导 | 让引导强度随去噪步变化（如早期强、后期弱），或只在中段施加引导。比全程恒定 $w$ 更能兼顾结构对齐与细节自然，是常见的实用改进。 |
| CFG rescale | 引导重标定 | 一种缓解过饱和的技巧（Lin 2024）：引导后把预测的标准差重新缩回条件预测的水平，抵消外推带来的方差膨胀。 |
| guidance distillation | 引导蒸馏 | 把「跑两次网络（条件+无条件）」的 CFG 蒸馏进单次前向的学生模型，省掉一半算力。Flux schnell 等少步模型常把 CFG 一并蒸馏掉。 |

## 一致性模型与少步采样 · Consistency & Few-Step

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| consistency model (CM) | 一致性模型 | Song 2023 提出：学一个函数 $f$，把概率流 ODE 轨迹上的**任意**点都直接映到轨迹起点（干净数据）。因为同一条轨迹上所有点目标相同，可一步从噪声生成，也支持少步精修。 |
| self-consistency | 自洽性 | CM 的核心约束：同一条 ODE 轨迹上相邻两点经 $f$ 应得到相同输出，即 $f(x_t,t)=f(x_{t'},t')$。训练就是最小化相邻点输出之差，使 $f$ 沿整条轨迹「自洽」。 |
| boundary condition | 边界条件 | CM 要求在 $t\to0$（无噪声）时 $f(x,0)=x$，即对干净数据是恒等映射。通常用 skip connection 参数化 $f=c_\text{skip}(t)x+c_\text{out}(t)F_\theta(x,t)$ 自动满足。 |
| consistency distillation (CD) | 一致性蒸馏 | 用一个预训练扩散模型当「老师」生成 ODE 轨迹上的相邻点对，训练 CM 学生满足自洽。是获得 CM 最常用的方式，把多步老师压成少步学生。 |
| consistency training (CT) | 一致性训练 | 不依赖预训练老师、从零训练 CM 的方式：用无偏的 score 估计代替老师生成轨迹。比 CD 更难调但不需要先有扩散模型。 |
| skip connection parameterization | skip 参数化 | 用 $f_\theta=c_\text{skip}(t)\,x+c_\text{out}(t)\,F_\theta(x,t)$ 表示一致性函数，其中 $c_\text{skip}(0)=1,c_\text{out}(0)=0$ 自动满足边界条件。EDM 风格的预条件系数是常用选择。 |
| few-step / single-step sampling | 少步 / 单步采样 | 用 1~4 次网络前向就生成样本（对比扩散的几十上百步）。CM 单步即出图，多步则交替「加噪到某 $t$ → 用 $f$ 跳回」精修，质量随步数提升。 |
| progressive distillation | 渐进蒸馏 | Salimans & Ho 2022：反复把一个 $N$ 步采样器蒸馏成 $N/2$ 步的学生，迭代减半。是 CM 之前的主流少步方案，思想上是 CM/LCM 的前身。 |
| LCM (Latent Consistency Model) | 隐一致性模型 | 把 CM 用到 SD 的 latent 空间 + 引入引导蒸馏，使 SD 能 4 步出图。配合 LCM-LoRA 可低成本给现成 SD 模型加少步能力，是实用落地的代表。 |
| EDM (Elucidating Diffusion Models) | —— | Karras 2022：系统梳理扩散的设计空间（噪声表、预条件、采样器、loss 权重），给出一套强基线配方。CM 的预条件系数与连续时间表述大量沿用 EDM。 |
| distillation | 蒸馏 | 用一个（慢但好的）老师模型的行为训练一个（快的）学生模型。前沿少步生成（CM/LCM/进度蒸馏/对抗蒸馏）几乎都是某种蒸馏，用质量换速度。 |

## 评测与工程 · Evaluation & Engineering

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| FID (Fréchet Inception Distance) | —— | 用 Inception 特征比较生成图与真实图两个高斯分布的距离，越低越好。扩散/DiT/flow 的标准质量指标，但对少样本与失真敏感、不完全等同人类偏好。 |
| CLIP score | —— | 用 CLIP 算生成图与文本 prompt 的相似度，衡量「图文对齐」。CFG 强度调高常以牺牲 FID 换取更高 CLIP score，二者权衡是可控生成的常见取舍。 |
| NFE (number of function evaluations) | 函数评估次数 | 生成一个样本调用去噪/速度网络的总次数，是采样成本的硬指标。扩散几十~上百，蒸馏后的 CM/LCM 可降到 1~4——少步研究的核心 KPI。 |
| sampler / scheduler | 采样器 / 调度器 | 把训练好的模型变成生成器的数值算法（DDPM、DDIM、DPM-Solver、Euler、Heun 等）及其步长安排。同一模型换采样器可在相同 NFE 下显著改变质量。 |
| DDIM | —— | Denoising Diffusion Implicit Models（Song 2021）：把 DDPM 的随机采样改成确定性、可跳步的采样，几十步即可，且是 probability flow ODE 的离散化——连接扩散与 ODE 视角的实用桥梁。 |
| latent space arithmetic | 隐空间运算 | 在 latent 上插值/加减实现语义编辑（如风格混合）。latent 扩散与 flow 的确定性 ODE 让「同一噪声→可复现/可编辑的图」成为可能。 |
| guidance-free / distilled sampler | 免引导 / 蒸馏采样器 | 把 CFG 与多步一起蒸馏掉的最终采样器，单次前向、无需跑两遍。Flux schnell、SDXL-Turbo 等实时模型的产物，是前沿落地的形态。 |
