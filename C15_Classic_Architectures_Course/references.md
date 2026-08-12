# 参考清单 · References（经典神经网络架构）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制，都能在下列原始论文里找到它被提出的动机与完整设计。

## 卷积网络奠基 · Foundations of ConvNets
- ★ **LeCun, Bottou, Bengio & Haffner 1998, _Gradient-Based Learning Applied to Document Recognition_（LeNet-5）** — 卷积网络的奠基论文。提出局部感受野、参数共享、下采样（池化）的完整 CNN 范式，并端到端用梯度训练识别手写数字。本课模块 01/02 的所有概念都源出于此，是理解「为什么是卷积」的起点。
- ★ **Krizhevsky, Sutskever & Hinton 2012, _ImageNet Classification with Deep Convolutional Neural Networks_（AlexNet）** — 点燃深度学习复兴的标志性工作。把 CNN 做深做大拿下 ImageNet，系统性引入 ReLU、dropout、数据增强与双 GPU 训练。读它体会「深 + 大数据 + GPU」如何改变格局，模块 02 的演化叙事从这里加速。
- ★ **Simonyan & Zisserman 2014, _Very Deep Convolutional Networks for Large-Scale Image Recognition_（VGG）** — 用清一色 3×3 小卷积堆出 16/19 层，论证「两个 3×3 叠加 = 一个 5×5 的感受野，但更少参数、更多非线性」。结构极规整，是理解「小核堆深」与感受野计算的最佳范例，模块 02 的练习直接对应。
- **Lin, Chen & Yan 2013, _Network In Network_（NiN）** — 提出 1×1 卷积（跨通道的逐像素全连接）与全局平均池化（GAP）替代末端全连接。模块 02 的 1×1 降维与 GAP 收尾的思想来源。
- **Szegedy et al. 2015, _Going Deeper with Convolutions_（GoogLeNet / Inception）** — 用多尺度并行卷积分支（Inception 模块）与 1×1 降维在控制算力下做深。展示了 1×1 卷积作为「计算瓶颈」的妙用，是模块 02 的延伸阅读。

## 残差学习与归一化 · Residual Learning & Normalization
- ★ **He, Zhang, Ren & Sun 2015, _Deep Residual Learning for Image Recognition_（ResNet）** — 现代深度网络的转折点。指出朴素堆深会**退化**（训练误差升高），用残差连接 `F(x)+x` 让网络能训到 152 层乃至上千层。其残差思想后来成为 Transformer 的标配。模块 02 全程在复现并解释它，**必读**。
- ★ **Ioffe & Szegedy 2015, _Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift_** — 提出对 mini-batch 做标准化以稳定并加速训练、允许更大学习率。模块 02 从零实现 BN 的前向与「训练 vs 推理」差异的依据，**必读**。
- **He et al. 2016, _Identity Mappings in Deep Residual Networks_（ResNet-v2 / pre-activation）** — ResNet 的后续分析，论证「干净的恒等通路」（pre-activation 排布）让梯度直通得更彻底，把残差能堆多深又推进一步。读它深化对「梯度高速公路」的理解。
- **Santurkar et al. 2018, _How Does Batch Normalization Help Optimization?_** — 用实验反驳「BN 靠减少内部协变量偏移」的原始解释，提出 BN 主要是**平滑了损失曲面**。读它理解「论文给的动机未必是真正起作用的机制」这一科研态度。
- **Ba, Kiros & Hinton 2016, _Layer Normalization_** — 对单样本全特征归一化、不依赖 batch，适配变长序列与小 batch。是 RNN 与后来 Transformer 的归一化首选，模块 04/05 的衔接点。

## 循环网络与梯度问题 · RNNs & the Gradient Problem
- ★ **Hochreiter & Schmidhuber 1997, _Long Short-Term Memory_（LSTM）** — 门控循环单元的奠基论文。提出受门保护的 cell state（恒定误差环 CEC）以根治朴素 RNN 的梯度消失，使学习远距离依赖成为可能。模块 04 全程复现其门控机制，**必读**。
- ★ **Bengio, Simard & Frasconi 1994, _Learning Long-Term Dependencies with Gradient Descent is Difficult_** — 从理论上刻画了梯度消失/爆炸：循环雅可比连乘的谱半径决定梯度指数衰减或增长。模块 03 梯度消失分析的数学依据，**必读**。
- ★ **Pascanu, Mikolov & Bengio 2013, _On the Difficulty of Training Recurrent Neural Networks_** — 把梯度爆炸/消失讲透，并提出**梯度裁剪**这一至今通用的稳定手段。模块 03 梯度裁剪实现的直接来源，**必读**。
- **Cho et al. 2014, _Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation_（GRU + encoder-decoder）** — 同时提出 GRU（LSTM 的简化）与 RNN encoder-decoder 框架。模块 04 的 GRU 与模块 05 的 seq2seq 都源出于此，一篇顶两个里程碑，**必读**。
- **Werbos 1990, _Backpropagation Through Time: What It Does and How to Do It_** — BPTT 的经典阐述。把「时间展开 + 标准反向传播」讲清楚，模块 03 从零实现 BPTT 的方法论参考。
- **Karpathy 2015, _The Unreasonable Effectiveness of Recurrent Neural Networks_（博客）** — 极佳的 RNN 直觉入门与 char-RNN 实战，附 min-char-rnn 的百行实现。模块 03 动手前的最佳热身读物。
- **Karpathy, Johnson & Fei-Fei 2015, _Visualizing and Understanding Recurrent Networks_** — 可视化 LSTM 内部 cell 的可解释单元（如「引号开关」「行长计数器」）。读它把抽象的 cell state 落到具体可见的记忆行为。

## 序列到序列与注意力 · Seq2Seq & Attention
- ★ **Sutskever, Vinyals & Le 2014, _Sequence to Sequence Learning with Neural Networks_** — seq2seq 的奠基：用 LSTM encoder 压源序列、LSTM decoder 生成目标序列做机器翻译，并发现「反转源序列」能显著提分。模块 05 encoder-decoder 与定长瓶颈讨论的源头，**必读**。
- ★ **Bahdanau, Cho & Bengio 2014, _Neural Machine Translation by Jointly Learning to Align and Translate_** — 首个注意力机制。指出定长上下文向量是瓶颈，提出让 decoder 每步对所有 encoder 态加权（加性注意力）以**联合学习对齐与翻译**。注意力的起点、Transformer 的祖先，模块 05 全程复现，**必读**。
- ★ **Luong, Pham & Manning 2015, _Effective Approaches to Attention-based Neural Machine Translation_** — 系统化注意力：提出乘性（dot/general）打分、global vs local 注意力。其点积形式是 Transformer 缩放点积注意力的直接前身，模块 05 打分函数对比的依据，**必读**。
- ★ **Vaswani et al. 2017, _Attention Is All You Need_（Transformer）** — 本课的**终点与下一课的起点**：彻底丢掉循环，只用（自）注意力 + 残差 + LayerNorm。读它你会发现本课每个组件（注意力来自模块 05、残差来自模块 02、LN 来自模块 02/04 的衔接）如何被重组成 Transformer。学完本课再读它，会有「原来都是老朋友」的顿悟。
- **Graves 2013, _Generating Sequences With Recurrent Neural Networks_** — 用 LSTM 做序列生成（手写、文本）并引入一种注意力雏形做对齐。理解注意力在 seq2seq 之外的更早萌芽。

## 教材与综述 · Textbooks & Surveys
- ★ **Goodfellow, Bengio & Courville 2016, _Deep Learning_（花书）** — 系统教材。第 9 章卷积网络、第 10 章循环网络是本课模块 01–04 的权威配套，推导详尽。遇到概念分歧以它为准。
- **Zhang, Lipton, Li & Smola, _Dive into Deep Learning_（D2L，d2l.ai）** — 带可运行代码的开放教材，CNN/RNN/seq2seq/attention 各章都有从零实现，与本课「从零 + 对拍」的精神一致，强烈建议对照其代码。
- **Olah 2015, _Understanding LSTM Networks_（colah 博客）** — 公认讲 LSTM/GRU 门控最清晰的图文。模块 04 的门控直觉与配图思路深受其影响，动手前必看。
- **CS231n（斯坦福，_Convolutional Neural Networks for Visual Recognition_）讲义** — CNN 的经典课程讲义，卷积/池化/反向传播/架构演化讲得极透，模块 01/02 的难度阶梯对标它。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **纯 numpy / CPU / 玩具规模**：全课不调用任何深度学习框架，每个算子（conv2d 前向反向、池化、残差块、RNN/BPTT、LSTM/GRU、注意力）都用 numpy **从零实现**并与朴素参考或 `scipy.signal` **对拍到 `atol=1e-10`**，或用**数值梯度检验**确认反向正确。数据用 `optdigits`（8×8 手写数字）与合成序列，规模刻意小，追求**看懂机制**而非刷指标。
- **可迁移性**：你在 numpy 里验证过的前向/反向逻辑，与 PyTorch 的 `nn.Conv2d` / `nn.LSTM` / `nn.MultiheadAttention` 的数学完全一致——只是框架替你做了自动微分与 GPU 加速。
- **课程衔接**：本课是 **Transformer（C01）之前的地基**。下游直接接 C01（自注意力 = 模块 05 注意力的自指版 + 模块 02 的残差/归一化）；模块 02 的卷积视角也衔接视觉 Transformer（ViT）与卷积-注意力混合架构。先修建议：基础线性代数、微积分链式法则、一点点概率。
