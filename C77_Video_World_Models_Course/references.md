# C77 参考文献 · 视频与世界模型

按模块组织。每条注明**它在本课的哪个具体结论上被用到**。

---

## 模块 00 · 总览

- **OpenAI.** *Video generation models as world simulators.* Sora 技术报告, 2024.
  → 「时空 patch」这个说法的来源，也是把「视频生成」与「世界模型」放在同一篇文档里的
  最有影响力的一次。本课 m00 的 token 账与 m04 的两义之分都以它为背景。

- **Ho, J., Salimans, T., Gritsenko, A., Chan, W., Norouzi, M. & Fleet, D.**
  *Video Diffusion Models.* NeurIPS 2022.
  → 把扩散推广到视频的第一批系统工作，包含 3D U-Net 与自回归长视频扩展。
  本课 m00/m03 的问题设定来自它。

- **Blattmann, A. et al.** *Align your Latents: High-Resolution Video Synthesis with
  Latent Diffusion Models.* CVPR 2023.
  → **时间层的加法式插入**（在预训练图像模型上加时间注意力，$\alpha$ 初始化为 0）。
  本课 m02 第 4 节给出这个设计选择的 Kronecker 秩解释——
  它不只是为了训练稳定，它决定了整个网络能不能表达「空间往哪看取决于第几帧」。

- **Bertasius, G., Wang, H. & Torresani, L.** *Is Space-Time Attention All You Need
  for Video Understanding?* ICML 2021（TimeSformer）.
  → 分解式时空注意力的代表性工作，也是 m02 全部分析的对象。

---

## 模块 01 · 视频 latent 与 tokenizer

- **Rombach, R., Blattmann, A., Lorenz, D., Esser, P. & Ommer, B.**
  *High-Resolution Image Synthesis with Latent Diffusion Models.* CVPR 2022.
  → 图像侧的地基（见 **C28 模块 01**）。本课不重讲，只处理时间维。

- **Yu, L. et al.** *Language Model Beats Diffusion — Tokenizer is Key to Visual
  Generation.* ICLR 2024（MAGVIT-v2）.
  → 「tokenizer 是关键」这个论断，以及无查找量化（LFQ）。
  本课 m01 第 4 节的比特预算账是它那条论断的一个最小可执行版本。

- **Yu, L. et al.** *MAGVIT: Masked Generative Video Transformer.* CVPR 2023.
  → 3D VQ tokenizer。本课 m01 的「少而大的 token」结论对应它的时空 patch 设计。

- **Agarwal, N. et al.** *Cosmos World Foundation Model Platform for Physical AI.*
  NVIDIA, 2025.
  → **因果**时空 tokenizer 的工业实现（为流式与「无限长」设计）。
  本课 m01 第 3 节量出因果性的代价（$\leq 3.3\%$ 且非单调），
  并指出它的真实成本在别处：不能与图像 VAE 共享权重、以及 chunk 边界的接缝。

- **van den Oord, A., Vinyals, O. & Kavukcuoglu, K.** *Neural Discrete
  Representation Learning.* NeurIPS 2017（VQ-VAE）.
  → 离散 tokenizer 的原始形式，以及码本坍缩问题的起点。

- **Zhu, Y. et al.** *Scaling the Codebook Size of VQ-GAN to 100,000 with a
  Utilization Rate of 99%.* NeurIPS 2024.
  → 码本利用率的工程处理。本课 m01 练习 4 指出**利用率不是坍缩的正确判据**
  （利用率可接近 100% 而分布极度不均），应看熵 $/\log_2 K$。

---

## 模块 02 · 时空注意力

- **Peebles, W. & Xie, S.** *Scalable Diffusion Models with Transformers.* ICCV 2023（DiT）.
  → DiT 架构与它的 scaling law（见 **C28 模块 02**）。本课不重讲。

- **Arnab, A., Dehghani, M., Heigold, G., Sun, C., Lučić, M. & Schmid, C.**
  *ViViT: A Video Vision Transformer.* ICCV 2021.
  → 系统对照了四种时空注意力分解方式。本课 m02 把其中「分解 vs 完全 3D」这一对
  的表达力差别算成了一个 Kronecker 秩的问题。

- **Liu, Z. et al.** *Video Swin Transformer.* CVPR 2022.
  → 时空窗口注意力。本课 m02 第 5 节与练习 2/4 指出
  **窗口的 Kronecker 秩也是 1** ——
  它换来的是局部性归纳偏置与内存局部性，不是表达力。

- **Van Loan, C. & Pitsianis, N.** *Approximation with Kronecker Products.*
  In *Linear Algebra for Large Scale and Real-Time Applications*, 1993.
  → 最近 Kronecker 逼近的 SVD 解法（重排 + SVD）。
  **本模块全部定量结论都是这个重排 SVD 的直接读数。**

- **Vaswani, A. et al.** *Attention Is All You Need.* NeurIPS 2017.
  → 残差连接与「加法式」子层的来源。m02 第 4 节说明这个接线方式
  （并行接在残差流上而不是串成链）恰恰是分解式时空注意力表达力的来源。

- **注**：本课 m02 练习 3 给出的饱和律 $m^2 - m + 1$（$m = \min(T,S)$）
  是探数阶段实测出来的（七组配置精确命中），**本课不给推导**。
  它与「$m \times m$ 矩阵生成的代数的维数」有关，但严格的表述超出本课范围。

---

## 模块 03 · 时序一致性与自回归漂移

- **Kendall, M.** *Note on Bias in the Estimation of Autocorrelation.*
  Biometrika 41, 1954. · **Marriott, F. & Pope, J.** *Bias in the Estimation of
  Autocorrelations.* Biometrika 41, 1954.
  → $E[\hat a] - a \approx -(1+3a)/n$ 的来源。
  本课 m03 第 2 节把它与「生成的视频越往后越静止」直接连起来：
  一步拟合系统性低估持续性 $\Rightarrow$ rollout 的运动能量只有真值的 $35\%$–$49\%$。

- **Bengio, S., Vinyals, O., Jaitly, N. & Shazeer, N.** *Scheduled Sampling for
  Sequence Prediction with Recurrent Neural Networks.* NeurIPS 2015.
  → 「训练时按概率喂模型自己的输出」。本课 m03 第 5 节把它与多步损失、锚帧、
  一次性生成放在同一张表里，按「修哪一支」区分。

- **Ross, S. & Bagnell, D.** *Efficient Reductions for Imitation Learning /
  DAgger.* AISTATS 2010 / 2011.
  → 自回归 rollout 的分布偏移与它的 $O(H^2)$ 界。
  与 **C59**（VLA / 模仿学习）呼应；本课只做生成侧。

- **Harvey, W., Naderiparizi, S., Masrani, V., Weilbach, C. & Wood, F.**
  *Flexible Diffusion Modeling of Long Videos.* NeurIPS 2022.
  → 层次化 / 关键帧条件生成。本课 m03 练习 3 把锚帧的收益算成
  「误差从 $\vert\hat a\vert^T$ 变成 $\vert\hat a\vert^{\leq m}$」，
  并给出所需锚帧间隔的闭式 $m \leq 1 + \ln F/\ln\vert\hat a\vert$。

- **Villegas, R. et al.** *Phenaki: Variable Length Video Generation from Open
  Domain Textual Descriptions.* ICLR 2023.
  → 变长自回归视频生成的代表工作，也是「长视频靠自回归拼」这条路线的实例。

- **本课程 C41 模块 04** —— 规划侧的复合误差。
  本模块处理的是**生成侧**（分布性失效），两者的分界在 m04 第 2 节被量化。

---

## 模块 04 · 世界模型

- **Ha, D. & Schmidhuber, J.** *World Models.* NeurIPS 2018.
  → 「世界模型」这个词在深度学习语境里的起点（VAE + RNN + 控制器）。

- **Hafner, D., Lillicrap, T., Ba, J. & Norouzi, M.** *Dream to Control: Learning
  Behaviors by Latent Imagination.* ICLR 2020. ·
  **Hafner, D. et al.** *Mastering Diverse Control Tasks through World Models.*
  Nature 2025（DreamerV3）.
  → 「在 latent 空间里想象」这条线。见 **C41 模块 04**；本课不重讲规划部分。

- **Bruce, J. et al.** *Genie: Generative Interactive Environments.* ICML 2024.
  → 从**无标注**视频里学潜在动作。本课 m04 第 3 节对它有一条直接含义：
  潜在动作的推断错误**不是无害的噪声**——
  实测「喂错动作比不喂动作更糟」在 8 种配置上全部成立，
  所以这类系统必须额外报告**潜在动作的可辨识性**，而不只是重建质量。

- **Valevski, D., Leviathan, Y., Arar, M. & Fruchter, S.**
  *Diffusion Models Are Real-Time Game Engines.* 2024（GameNGen）.
  → 「可交互视频」的代表实现（实时、动作条件、长 rollout）。
  本课 m04 的「四项验收」正是针对这类系统设计的。

- **Yu, L. et al.** *Cosmos World Foundation Model Platform.* NVIDIA, 2025.
  → 把世界模型当作基础模型来做的工程平台，含 tokenizer、后训练与评测。

- **Kidambi, R., Rajeswaran, A., Netrapalli, P. & Joachims, T.**
  *MOReL: Model-Based Offline RL.* NeurIPS 2020. ·
  **Yu, T. et al.** *MOPO: Model-based Offline Policy Optimization.* NeurIPS 2020.
  → 「模型被利用」的标准应对（悲观化 / 不确定性惩罚）。
  本课 m04 第 2 节量出这个问题的量级（一步误差 $3.95\%$ → 回报高估 $251\%$），
  而具体的悲观化方法属于 **C41 模块 04** 的范围。

- **Chua, K., Calandra, R., McAllister, R. & Levine, S.**
  *Deep Reinforcement Learning in a Handful of Trials using Probabilistic
  Dynamics Models.* NeurIPS 2018（PETS）.
  → 用模型集合的不一致性来限制规划。与本课 m04 练习 1
  「限制规划时的动作范围」是同一思路的两种实现。

---

## 模块 05 · 视频评测

- **Unterthiner, T., van Steenkiste, S., Kurach, K., Marinier, R., Michalski, M.
  & Gelly, S.** *Towards Accurate Generative Models of Video: A New Metric &
  Challenges.* 2018 / *FVD: A new Metric for Video Generation*, ICLR 2019 Workshop.
  → FVD 的出处。本课 m05 量的三个病理都是它从 FID 继承来的。

- **Heusel, M., Ramsauer, H., Unterthiner, T., Nessler, B. & Hochreiter, S.**
  *GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash
  Equilibrium.* NeurIPS 2017（FID）.
  → Fréchet 距离作为生成质量度量的原始形式，以及「只用前两阶矩」这个设计选择。

- **Chong, M. & Forsyth, D.** *Effectively Unbiased FID and Inception Score and
  Where to Find Them.* CVPR 2020.
  → 有限样本偏差与 $\text{FID}_\infty$（对 $1/N$ 外推）。
  本课 m05 练习 1 实现它，并量出：外推把 $N{=}64$ 的偏差降 2 个数量级，
  但它有一个**绝对**精度底（本设定下约 $0.08$），小于它的效应分辨不出。

- **Ge, S., Mahapatra, A., Parmar, G., Zhu, J.-Y. & Huang, J.-B.**
  *On the Content Bias in Fréchet Video Distance.* CVPR 2024.
  → 实证地说明标准 FVD 主要反映**单帧内容**而不是运动
  （用「打乱帧序的真实视频」都能拿到很好的 FVD）。
  本课 m05 第 4 节给出这个现象的**最小可复现核心**：
  逐帧特征对帧序的敏感度是 $7.1\times10^{-15}$——一个恒等式，而不是一个经验观察。

- **Kynkäänniemi, T., Karras, T., Laine, S., Lehtinen, J. & Aila, T.**
  *Improved Precision and Recall Metric for Assessing Generative Models.*
  NeurIPS 2019.
  → 把保真与多样分开的 $k$-NN 类指标。本课 m05 练习 2 用它的一个最简版本
  补 FVD 的矩匹配盲区，并诚实指出**它不是万能补丁**
  （在矩匹配的坍缩上只降到 $0.90\times$）。

- **Huang, Z. et al.** *VBench: Comprehensive Benchmark Suite for Video
  Generative Models.* CVPR 2024.
  → 把视频质量拆成 16 个维度。本课 m05 第 5 节把它作为「把一个数拆成一组」
  这条对策的代表，但不复现基准本身（它需要真实模型与人工标注）。

- **本课程 C14（评测与度量）** —— 那里把「文生图/视频的评测要同时管保真、多样、
  与提示的对齐、以及时序一致性」列为开放问题。本课把**时序**那一半做完：
  给出一个可执行的判据（帧序置换检验）与三个病理的量化。

---

## 与本课程其他课的关系

- **C28 · 前沿扩散** —— latent diffusion、DiT、flow matching、CFG、一致性模型。
  本课的**硬前提**，且本课一概不重讲。C28 里每一处提到「视频」的地方都是
  指向本课的一句带过。
- **C41 模块 04 · 基于模型与世界模型** —— MPC / Dyna / 规划侧的复合误差。
  本课只做生成侧，并在 m04 第 2 节把两者的失效机制量化区分
  （被动 $-13\%$ vs 主动 $+251\%$）。
- **C59 · VLA 与具身** —— 模仿学习里的复合误差。
  这是第三种同名不同义的「误差累积」（本课 m03 是生成侧、C41-04 是规划侧）。
- **C55 · TSR 感知** —— 那里的「时序一致性」是一个**感知系统**的工具
  （时序累积换单帧信息、时序一致性挖长尾、运动一致性做误检过滤），
  与本课的生成侧完全不同。
- **C14 · 评测与度量** —— 视频评测的开放问题在那里被提出。
- **C20 · SSM** —— 那里的「因果卷积」是把递推展开的另一种视角，
  与本课 m01 的时间维因果压缩是不同的概念。
- **C35 · 语音** —— 流式因果卷积与 RVQ 在音频上的实现，
  与本课 m01 的视频 tokenizer 是同一类工程问题的两个领域。
- **C72–C75 · 三维全链路** —— 另一个「几何 + 生成」的方向。
  C75 的 SDS 一节与本课 m04 的「优化会找模型的洞」是同一现象的两种形态。
