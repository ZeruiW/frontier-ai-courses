# 术语词典 · Glossary（经典神经网络架构）

> 按主题分组，每条 2–3 句释义。读 LeNet/AlexNet/VGG/ResNet/LSTM/seq2seq/attention 原论文遇到生词回这里查；英文术语保留原文（深度学习社区与论文的通用语言）。本课用 numpy 从零实现这些机制，术语与真实框架（PyTorch/TensorFlow）一一对应。

## 卷积与空间算子 · Convolution & Spatial Ops

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| convolution | 卷积 | 数学上指把核翻转（kernel flip）后做滑窗加权求和。深度学习里「卷积层」实际算的是不翻转的互相关；因为核是学出来的，翻不翻转只差一个参数重排，习惯上仍叫卷积。 |
| cross-correlation | 互相关 | 把核**不翻转**地在输入上滑窗、逐位相乘再求和。这是所有深度学习框架 `Conv2d` 真正执行的运算。理解「框架的卷积 = 数学的互相关」是读懂实现的第一关。 |
| kernel / filter | 卷积核 / 滤波器 | 一小块可学习权重（如 3×3×C_in），在输入上滑动以检测某种局部模式（边缘、纹理、角点）。一层有多个核，每个产出一张输出通道（特征图）。 |
| feature map / activation map | 特征图 | 一个卷积核扫过整张输入后产出的二维响应图，每个位置的值表示该位置与核模式的匹配强度。一层的输出是若干张特征图堆叠成的张量。 |
| channel | 通道 | 张量在「特征」维度上的切片。输入图像有 RGB 三通道；卷积层的输出通道数 = 该层核的个数，每个通道是一种被检测的模式。 |
| padding | 填充 | 在输入边缘补零（或反射/复制），用于控制输出尺寸。`same` 填充让输出与输入同尺寸；`valid`（不填充）让输出按核大小缩小。填充也缓解边缘像素被卷积「采样不足」。 |
| stride | 步幅 | 卷积核每次滑动的像素数。stride=1 逐像素扫；stride=2 隔一个扫，输出尺寸约减半，是池化之外另一种降采样手段。 |
| receptive field | 感受野 | 输出某个位置「看得到」的输入区域大小。它随网络加深、stride 与池化累积而扩大；感受野要足够大才能覆盖目标尺度，是 CNN 设计的核心几何量。 |
| parameter sharing | 参数共享 | 同一个卷积核在整张输入的所有位置复用同一组权重。这把参数量从「全连接的 H×W×…」降到「只有核大小」，并赋予平移等变性。是 CNN 相对 MLP 的根本优势。 |
| translation equivariance | 平移等变性 | 输入平移 → 输出（特征图）同样平移。卷积的参数共享天然带来这一性质：在哪检测到边缘，边缘移动后就在对应新位置检测到。注意它不同于平移不变性。 |
| translation invariance | 平移不变性 | 输入平移 → 输出**不变**。池化（尤其全局池化）在小范围内带来近似不变性：物体稍微移位，池化后的特征基本不变，利于分类。 |
| output size formula | 输出尺寸公式 | 一维方向上 `out = floor((in + 2*pad - kernel) / stride) + 1`。二维各方向独立套用。背熟它才能调通任何卷积/池化的维度。 |
| im2col | 图像转列 | 把每个卷积窗口拉成一列、拼成大矩阵，从而把卷积变成一次稠密矩阵乘（GEMM）。是 cuDNN 之前框架实现卷积的标准技巧，也便于复用高度优化的 BLAS。 |
| dilation | 空洞 / 膨胀 | 卷积核元素之间插入间隔，使核在不增加参数的前提下覆盖更大感受野。常用于语义分割、WaveNet 等需要大感受野的场景。 |

## 池化与归一化 · Pooling & Normalization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pooling | 池化 | 在小窗口内做聚合（取最大或平均），用于降采样、扩大感受野、提供局部平移不变性。无可学习参数，反向只是把梯度路由回相应位置。 |
| max pooling | 最大池化 | 取窗口内最大值。反向时梯度只回传给「当时最大」的那个位置（argmax），其余为零。保留最强响应，对小位移鲁棒。 |
| average pooling | 平均池化 | 取窗口内平均值。反向时把梯度均分给窗口内每个位置。比 max 更平滑，常用于全局平均池化（GAP）把特征图压成向量。 |
| global average pooling (GAP) | 全局平均池化 | 把整张特征图平均成一个标量（每通道一个），替代末端的全连接层。大幅减少参数、抑制过拟合，是 NiN/ResNet 等的标配收尾。 |
| batch normalization (BN) | 批归一化 | 对一个 mini-batch 内每个特征做标准化（减均值除标准差）再仿射缩放平移。稳定并加速训练、允许更大学习率、有轻微正则作用。训练用 batch 统计、推理用滑动平均统计。 |
| internal covariate shift | 内部协变量偏移 | BN 原论文提出的动机：训练中每层输入分布随前层参数更新而漂移，拖慢收敛。后续研究表明 BN 的主要好处更可能来自平滑损失曲面，但这一术语已成历史标记。 |
| layer normalization (LN) | 层归一化 | 对单个样本的所有特征做标准化，不依赖 batch。天然适合变长序列与小 batch，是 RNN 与 Transformer 的归一化首选。 |

## CNN 架构 · CNN Architectures

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| LeNet | —— | LeCun 等 1998 年的手写数字识别 CNN（卷积+池化+全连接），奠定了「卷积特征提取 + 分类头」的范式。本课模块 02 的起点。 |
| AlexNet | —— | Krizhevsky 等 2012 年 ImageNet 夺冠网络。把 CNN 做深做大，引入 ReLU、dropout、GPU 训练与数据增强，点燃了深度学习的复兴。 |
| VGG | —— | Simonyan & Zisserman 2014：用堆叠的 3×3 小卷积替代大卷积核，证明「深 + 小核」既省参数又增表达力。结构极规整，至今常作特征提取骨干。 |
| ResNet | 残差网络 | He 等 2015：引入残差连接（skip connection）让网络能堆到上百甚至上千层而不退化，是现代深度网络的转折点，其残差思想后来成为 Transformer 的标配。 |
| residual connection / skip connection | 残差连接 / 跳跃连接 | 让一层学「相对于输入的增量」`y = F(x) + x` 而非直接学 `y`。反向时梯度可经 `+x` 这条恒等通路**直通**到浅层，根治深网络的梯度消失与退化。 |
| identity mapping | 恒等映射 | 残差块里那条「什么都不做、直接把 x 加过去」的捷径。它保证「再加一层至少不会更差」（学到 F=0 即恢复恒等），是 ResNet 能堆深的理论支点。 |
| degradation problem | 退化问题 | ResNet 论文观察到：朴素堆深网络后，**训练**误差反而上升（不是过拟合）。说明深网络难以优化；残差连接正是为解决它而生。 |
| bottleneck block | 瓶颈块 | ResNet 深层版的残差块：用 1×1 卷积先降维、3×3 卷积处理、再 1×1 升维，大幅减少计算量，让上百层在算力上可行。 |
| 1×1 convolution | 1×1 卷积 | 核大小为 1 的卷积，逐像素地在通道维做线性组合（等价于对每个空间位置做一次全连接）。用于升降维（改通道数）、跨通道信息融合、加非线性。 |
| inductive bias | 归纳偏置 | 模型结构对解的先验假设。卷积假设「局部性 + 平移等变」，RNN 假设「时序 + 参数随时间共享」。偏置越契合数据，样本效率越高；本课贯穿这一视角。 |

## 循环网络与 BPTT · RNN & BPTT

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| recurrent neural network (RNN) | 循环神经网络 | 处理序列的网络：维护一个随时间更新的隐藏状态 `h_t = f(W_x x_t + W_h h_{t-1} + b)`，同一组权重在每个时间步复用。是参数共享在时间维上的体现。 |
| hidden state | 隐藏状态 | RNN 在时间步之间传递的「记忆」向量，编码到目前为止看过的序列信息。它是 RNN 的全部状态，下一步的输出与新状态都由它（与新输入）决定。 |
| unrolling / unfolding | 时间展开 | 把循环结构按时间步「摊开」成一个很深的前馈网络（每个时间步一层，但权重共享）。展开后即可套用标准反向传播——这就是 BPTT 的视角。 |
| backpropagation through time (BPTT) | 随时间反向传播 | 在展开后的计算图上做反向传播，沿时间步把梯度从后往前累积，同一组共享权重的梯度要在所有时间步上求和。是训练 RNN 的核心算法。 |
| truncated BPTT | 截断 BPTT | 对很长的序列，只在固定长度的窗口内反向传播（梯度不传到更早），以控制内存与计算、并缓解梯度爆炸。代价是学不到超过窗口的依赖。 |
| vanishing gradient | 梯度消失 | 反向时梯度经过许多步的雅可比连乘后指数衰减到接近零，导致远距离时间步学不到。其根源是循环雅可比的谱半径 < 1 时连乘趋零，是朴素 RNN 学不了长依赖的主因。 |
| exploding gradient | 梯度爆炸 | 与消失相反：雅可比谱半径 > 1 时连乘指数增长，梯度变成巨大值甚至 NaN，训练发散。常用梯度裁剪应对。 |
| gradient clipping | 梯度裁剪 | 当梯度范数超过阈值时按比例缩小（`g ← g * thr/‖g‖`），防止梯度爆炸导致的参数巨幅跳变。是训练 RNN（乃至 Transformer）的标准稳定手段。 |
| jacobian | 雅可比矩阵 | 向量到向量映射的一阶偏导矩阵。BPTT 中隐藏状态对前一隐藏状态的雅可比连乘，其谱半径决定梯度消失还是爆炸——这是理解 RNN 梯度问题的数学核心。 |
| teacher forcing | 教师强制 | 训练序列生成模型时，把**真实**的上一步输出（而非模型自己的预测）喂给下一步。加速收敛，但带来训练/推理分布不一致（exposure bias）。 |
| exposure bias | 暴露偏差 | teacher forcing 训练、自回归推理导致的不匹配：训练时每步输入都正确，推理时一旦出错会沿序列累积放大，模型从未见过自己的错误输入。 |
| BPTT weight gradient accumulation | 权重梯度累加 | 因为同一权重在每个时间步都被使用，它的总梯度是各时间步贡献之和。漏掉某些时间步的累加是 RNN 从零实现最常见的 bug。 |

## 门控循环单元 · Gated Units (LSTM / GRU)

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| long short-term memory (LSTM) | 长短期记忆网络 | Hochreiter & Schmidhuber 1997：用一个受门控保护的 cell state 携带长期信息，配合遗忘/输入/输出三个门，缓解梯度消失，能学远距离依赖。 |
| cell state | 细胞状态 | LSTM 中沿时间近似**线性**流动的「记忆传送带」。更新是加性的 `c_t = f⊙c_{t-1} + i⊙g`，让梯度能沿它几乎无衰减地回传——这是 LSTM 缓解梯度消失的关键。 |
| constant error carousel (CEC) | 恒定误差环 | LSTM 原论文对 cell state 这条加性通路的称呼：误差（梯度）在其上以接近常数（不指数衰减）的方式传递，是「long short-term」之所以可能的机制。 |
| forget gate | 遗忘门 | 一个 0–1 门，决定 cell state 的每个分量保留多少 `f_t = σ(...)`。设为 1 即完整保留旧记忆，设为 0 即清空。是 LSTM 控制记忆时长的旋钮。 |
| input gate | 输入门 | 控制候选记忆 `g_t` 有多少写入 cell state `i_t = σ(...)`。与遗忘门配合完成「擦掉一些、写入一些」的记忆更新。 |
| output gate | 输出门 | 控制把（经 tanh 的）cell state 暴露多少作为本步隐藏状态 `h_t = o_t ⊙ tanh(c_t)`。把「内部记忆」与「对外输出」解耦。 |
| candidate / cell input | 候选记忆 | 由当前输入与上一隐藏态算出的、待写入 cell state 的新信息 `g_t = tanh(...)`，受输入门调制后加入 cell state。 |
| gated recurrent unit (GRU) | 门控循环单元 | Cho 等 2014：LSTM 的简化版，合并 cell 与隐藏态、只用更新门与重置门（少一个门、少一组参数）。性能常与 LSTM 相当而更轻量。 |
| update gate | 更新门 | GRU 中决定「保留多少旧状态 vs 采纳多少新候选」的门 `z_t`，相当于把 LSTM 的遗忘门与输入门耦合成一个。 |
| reset gate | 重置门 | GRU 中决定计算候选状态时「忽略多少旧状态」的门 `r_t`，让单元能在需要时「忘掉」历史、只看当前输入。 |
| gradient highway | 梯度高速公路 | 对加性记忆通路（LSTM 的 cell state、ResNet 的残差连接）的比喻：梯度可沿这条近似恒等的通路畅通回传，不被反复的非线性与矩阵乘衰减。 |

## 序列到序列与注意力 · Seq2Seq & Attention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| sequence-to-sequence (seq2seq) | 序列到序列 | Sutskever 等 2014：用一个 encoder RNN 把输入序列压成（定长）上下文向量，再用 decoder RNN 据此生成输出序列。机器翻译、摘要等的奠基框架。 |
| encoder-decoder | 编码器-解码器 | seq2seq 的结构：encoder 读入并表示源序列，decoder 自回归地生成目标序列。注意力出现前，两者唯一的桥梁是 encoder 末态那一个向量。 |
| context vector | 上下文向量 | encoder 传给 decoder 的源序列表示。在无注意力的 seq2seq 里它是**定长**的（encoder 末态），构成「定长瓶颈」；有注意力后它在每个解码步动态加权重算。 |
| fixed-length bottleneck | 定长瓶颈 | 无注意力 seq2seq 的根本缺陷：再长的源句也被压进一个固定维度向量，长句信息严重丢失。注意力正是为打破这个瓶颈而生。 |
| attention | 注意力 | 让 decoder 每一步根据当前需要，对所有 encoder 状态做**加权求和**得到动态上下文。权重（对齐）由 decoder 状态与各 encoder 状态的相关性打分并 softmax 得到。 |
| Bahdanau attention (additive) | Bahdanau 注意力 / 加性注意力 | Bahdanau 等 2014 首个注意力：用一个小前馈网 `vᵀ tanh(W_s s + W_h h)` 给 decoder 态 s 与各 encoder 态 h 打分。也叫 additive / concat attention。 |
| Luong attention (multiplicative) | Luong 注意力 / 乘性注意力 | Luong 等 2015：用点积/双线性 `sᵀh` 或 `sᵀWh` 打分，更简单高效。其 dot/general 形式是 Transformer 缩放点积注意力的直接前身。 |
| alignment / alignment matrix | 对齐 / 对齐矩阵 | 注意力权重构成的「目标位置 × 源位置」矩阵，每行（一个解码步）是源位置上的概率分布。可视化它能看到模型在翻译时把哪个目标词对到哪个源词。 |
| attention score / energy | 注意力打分 / 能量 | softmax 之前的相关性原始值 `e_{ij}`，衡量解码步 i 与源位置 j 的匹配程度。对一行 e 做 softmax 得到该步的注意力权重。 |
| query / key / value | 查询 / 键 / 值 | 注意力的统一抽象：用 query（decoder 态）与各 key（encoder 态）打分得权重，再对 value（encoder 态）加权求和。Transformer 把这套抽象推到极致。 |
| greedy decoding | 贪心解码 | 推理时每步都选概率最大的词作为输出并喂入下一步。简单快速但可能错过整体更优的序列；beam search 是其更优的替代。 |
| beam search | 束搜索 | 解码时同时保留 top-k 条候选序列、逐步扩展并按累计概率剪枝。在贪心与全搜索之间取平衡，是序列生成的常用近似最优解码。 |
| autoregressive | 自回归 | 逐个生成元素、每步以已生成的前缀为条件。seq2seq 的 decoder、语言模型、Transformer 解码都是自回归的。 |

## 训练与通用概念 · Training & General

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| backpropagation | 反向传播 | 用链式法则自输出向输入逐层计算梯度的算法。本课所有「从零反向」都是它在具体结构（卷积、循环、门控）上的展开。 |
| computational graph | 计算图 | 把运算表示成节点（算子）与边（张量）的有向图。前向求值、反向沿图传梯度。理解任何复杂结构的反向，都先把它画成计算图。 |
| numerical gradient check | 数值梯度检验 | 用有限差分 `(f(x+ε)-f(x-ε))/(2ε)` 近似梯度，与解析梯度比对，验证反向实现正确。是本课多个模块「确认 backward 写对了」的金标准。 |
| activation function | 激活函数 | 引入非线性的逐元素函数（ReLU、tanh、sigmoid）。没有它，多层线性叠加仍是线性。门控单元里 sigmoid 当「门」(0–1)、tanh 当「候选值」(−1–1)。 |
| ReLU | 修正线性单元 | `max(0, x)`。计算简单、缓解梯度消失（正区间导数恒为 1），是 CNN 的默认激活，AlexNet 起广泛使用。 |
| softmax | —— | 把一组实数转成概率分布 `exp(x_i)/Σexp(x_j)`。用于分类输出、注意力权重归一化。数值稳定实现需先减去最大值再取 exp。 |
| cross-entropy loss | 交叉熵损失 | 分类的标准损失 `-Σ y_i log p_i`，衡量预测分布与真实分布的差距。与 softmax 配合时梯度化简为 `p - y`，干净易实现。 |
| weight initialization | 权重初始化 | 起始权重的选取（Xavier/Glorot、He/Kaiming）。初始化不当会让信号/梯度在深网络中爆炸或消失；与 BN、残差连接共同决定深网络能否训起来。 |
| epoch / mini-batch | 轮次 / 小批量 | epoch 是遍历一次全部训练数据；mini-batch 是每次更新所用的一小撮样本。BN 的统计、随机梯度的噪声都以 mini-batch 为单位。 |
