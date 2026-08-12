# 参考清单 · References（扩散与流前沿）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 玩具复现的每个机制，都能在下列文献里找到真实模型上的完整实现与权衡。基础的 DDPM/score matching 文献见 C16，这里聚焦驱动 SD3/Flux/SoRA 的前沿工作。

## 扩散基础（前置，详见 C16）· Diffusion Foundations
- **Ho, Jain & Abbeel 2020, _Denoising Diffusion Probabilistic Models (DDPM)_** — 现代扩散的起点。把扩散落实为「前向加噪 + 学网络预测噪声」的简单 MSE 训练，给出可用的采样流程。本课默认你已掌握它（C16 详讲），所有前沿技术都在它之上。
- **Song et al. 2021, _Score-Based Generative Modeling through SDEs_** — 把扩散统一进随机微分方程框架，引出 **probability flow ODE**（与扩散同分布的确定性 ODE）。本课模块 03 的「扩散也是 ODE」「flow 与扩散统一」直接源于此，强烈建议在学 flow matching 前读。
- **Song & Ermon 2019, _Generative Modeling by Estimating Gradients of the Data Distribution_** — score matching 视角的奠基。理解「去噪 = 估计 score」这条主线，是看懂 flow/consistency 的公共语言。
- ★ **Karras et al. 2022, _Elucidating the Design Space of Diffusion Models (EDM)_** — 把扩散的噪声表、预条件、采样器、loss 权重拆成正交的设计选择并给出强基线配方。consistency models 的预条件与连续时间表述大量沿用它；做任何扩散工程前都该读，避免重复踩坑。

## Latent Diffusion 与 Stable Diffusion · 模块 01
- ★ **Rombach, Blattmann, Lorenz, Esser & Ommer 2022, _High-Resolution Image Synthesis with Latent Diffusion Models (LDM/Stable Diffusion)_** — 本课模块 01 的核心。提出先用 VAE 把图像压到低维 latent、再在 latent 上扩散，把算力降两个数量级、让高分辨率开源生成成为可能。必读，理解「感知压缩 + 语义扩散」两阶段分工。
- **Esser, Rombach & Ommer 2021, _Taming Transformers (VQGAN)_** — LDM 的 VAE 前身：用感知损失 + 对抗损失训练的强压缩自编码器。理解 LDM 为什么能用很高的下采样因子还保住质量，关键在这套自编码器训练。
- **Podell et al. 2023, _SDXL_** — SD 的工程化升级：更大 UNet、双文本编码器、尺寸/裁剪条件、refiner。看「同一 LDM 框架如何靠工程把质量推到产品级」。
- **Kingma & Welling 2014, _Auto-Encoding Variational Bayes (VAE)_** — VAE 原始论文。模块 01 的 VAE 编解码、KL 正则、重参数化都源于此，是理解 latent 空间的地基。

## Diffusion Transformer · 模块 02
- ★ **Peebles & Xie 2023, _Scalable Diffusion Models with Transformers (DiT)_** — 本课模块 02 的核心。用 Transformer 取代 U-Net 作扩散骨干，提出 **adaLN-zero** 条件注入，并给出扩散的 scaling law（FID 随 Gflops 平滑下降）。SD3/Flux/SoRA 的共同骨架，必读。
- ★ **Esser et al. 2024, _Scaling Rectified Flow Transformers (Stable Diffusion 3)_** — 把 DiT 骨干 + flow matching 路径 + MM-DiT 多模态注意力合成当代 SOTA 文生图。一篇论文同时印证模块 02/03/04 的技术选择，是「前沿如何组合」的最佳案例研究。
- **Dosovitskiy et al. 2021, _An Image is Worth 16x16 Words (ViT)_** — patchify + Transformer 处理图像的原始论文。DiT 的 patchify、位置嵌入、序列化都直接借用 ViT，是模块 02 的前置直觉来源。
- **Bao et al. 2023, _All are Worth Words (U-ViT)_** — 与 DiT 同期的 Transformer 扩散骨干，用「把一切都当 token（含时间步、条件）+ 长跳连」的设计。对照 DiT 的 adaLN 路线，理解 Transformer 扩散的设计分歧。
- **Peebles et al. / OpenAI 2024, _Video generation models as world simulators (SoRA 技术报告)_** — SoRA 把 DiT 推广到时空 patch 做视频生成。看 DiT 骨干如何从图像 scale 到视频，是模块 02 scaling 论点的最强背书。

## Flow Matching 与 Rectified Flow · 模块 03
- ★ **Lipman, Chen, Ben-Hamu, Nickel & Le 2023, _Flow Matching for Generative Modeling_** — 本课模块 03 的核心。提出用简单 MSE 回归速度场来训练连续归一化流（conditional flow matching），统一并简化了扩散，且支持任意概率路径。必读，理解「生成 = 学速度场 + 积分 ODE」。
- ★ **Liu, Gong & Liu 2023, _Flow Straight and Fast: Rectified Flow_** — 提出用直线插值路径 + **reflow** 把流拉直，使 ODE 轨迹接近直线、极少步即可采样。SD3 采用其路径，是模块 03 「为什么直线」「reflow 怎么拉直」的来源。
- **Albergo & Vanden-Eijnden 2023, _Stochastic Interpolants_** — 与 flow matching 并行的统一框架，把扩散与流都纳入「随机插值」并给出更一般的路径设计。读它建立 flow/扩散统一的更高视角。
- **Tong et al. 2024, _Improving and Generalizing Flow-Based Generative Models (OT-CFM)_** — 把最优运输引入条件流匹配，用 minibatch OT 配对噪声与数据，进一步拉直轨迹。理解 rectified flow 与最优运输的联系。
- **Chen et al. 2018, _Neural ODEs_** — 连续归一化流与 ODE 生成的奠基。flow matching 解决了它「训练要模拟 ODE、太贵」的痛点；读它理解 FM 到底改进了什么。

## Guidance 与可控生成 · 模块 04
- ★ **Ho & Salimans 2022, _Classifier-Free Diffusion Guidance_** — 本课模块 04 的核心。提出训练时随机丢条件、采样时外推条件与无条件预测来放大条件，无需额外分类器。当代几乎一切可控生成的默认机制，必读。
- **Dhariwal & Nichol 2021, _Diffusion Models Beat GANs (classifier guidance)_** — CFG 的前身：用分类器梯度引导采样。读它理解 CFG 解决了什么痛点（不必再训一个带噪分类器），以及「引导」概念的由来。
- **Lin et al. 2024, _Common Diffusion Noise Schedules and Sample Steps are Flawed (CFG rescale / zero-SNR)_** — 诊断高 CFG 的过饱和，提出 CFG rescale 与 zero-terminal-SNR 修复。模块 04 「过饱和与缓解」的直接依据。
- **Karras et al. 2024, _Guiding a Diffusion Model with a Bad Version of Itself (autoguidance)_** — 用一个更弱的同族模型作引导基线，比 CFG 更干净地提质。代表引导研究的前沿方向，理解 CFG 的本质与改进空间。
- **Sadat et al. 2024, _CADS / 动态引导 等_** — 通过给条件退火/调度引导强度提升多样性。模块 04 「动态 CFG」的现实对应。

## 一致性模型与少步采样 · 模块 05
- ★ **Song, Dhariwal, Chen & Sutskever 2023, _Consistency Models_** — 本课模块 05 的核心。提出学一个把 ODE 轨迹上任意点映到起点的自洽函数，实现单步/少步生成。给出一致性蒸馏(CD)与一致性训练(CT)两条路。必读。
- **Song & Dhariwal 2024, _Improved Techniques for Consistency Models (iCT)_** — 修正 CM 训练的诸多不稳定（噪声表、loss 权重、EMA），让从零训练(CT)追上蒸馏。理解 CM 工程化要点。
- ★ **Luo et al. 2023, _Latent Consistency Models (LCM)_** — 把 CM 搬到 SD 的 latent 空间并蒸馏掉 CFG，使 SD 4 步出图。配合 **LCM-LoRA** 可低成本给现成模型加少步能力，是模块 05 落地的代表，必读。
- **Salimans & Ho 2022, _Progressive Distillation for Fast Sampling_** — CM 之前的主流少步方案：反复把采样步数减半蒸馏。思想上是 CM/LCM 的前身，对照理解「少步」的两条技术路线。
- **Sauer et al. 2024, _Adversarial Diffusion Distillation (SDXL-Turbo)_** / **Yin et al. 2024, _DMD_** — 用对抗/分布匹配损失做少步蒸馏，1~4 步生成且质量高。代表少步生成的另一大流派（对抗蒸馏），与一致性路线并列。
- **Frans et al. 2024 / Geng et al. 2024, _shortcut / mean-flow 等少步流模型_** — 把少步思想直接做进 flow matching（学「跳一大步」的速度）。是少步采样与 flow 结合的前沿，模块 03/05 的交汇点。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课聚焦「前沿」**：DDPM/score matching/采样器基础在 **C16（生成模型）**，这里默认你已掌握前向加噪与反向去噪，直接讲 latent 扩散、DiT、flow matching、CFG、consistency 这五块领先实验室在用的技术。若对扩散基础不熟，先过一遍 C16。
- ⚠️ **CPU 玩具复现**：全课用 numpy 在 CPU 上做**玩具规模**复现——2D 双月/八高斯分布、几十维的小「图」、几层的小网络。每个机制都与朴素参考**对拍验证**（latent 往返、加噪/去噪闭式、速度场目标、CFG 外推、自洽损失），保证你写的核心逻辑**正确**；真实模型只是同一逻辑放大 + 工程。
- **可迁移性**：你在 numpy 里验证过的 latent 两阶段、patchify/adaLN、直线速度场、CFG 外推、一致性自洽损失，与 SD3/DiT/Flux 的实现**结构一致**，只差规模与算子。读懂本课，再读这些模型的开源实现会顺畅得多。
- **课程衔接**：上游接 **C16**（基础扩散/生成模型）、**C15/C20**（Transformer 与现代架构，DiT 的骨干）；横向接 **C04/C08**（训练系统、注意力——DiT 就是注意力 + adaLN）；下游接 **C24/C27**（推理服务与模型压缩——少步蒸馏正是为部署）。视频生成（SoRA）是 DiT + flow 的时空推广。
