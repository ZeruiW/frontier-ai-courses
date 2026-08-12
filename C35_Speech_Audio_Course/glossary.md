# 术语词典 · Glossary（语音与音频）

> 按主题分组，每条 2–3 句释义。读 DSP 教材 / Whisper / EnCodec / AudioLM 论文遇到生词回这里查；英文术语保留原文（论文与代码的通用语言）。本课用 numpy 在 CPU 上从零实现这些概念，术语与真实语音系统一一对应。

## 信号基础 · Signal Fundamentals

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| waveform | 波形 | 声音在计算机里的最朴素表示：随时间变化的一维振幅序列 $x[n]$。一切语音/音频处理的起点与（生成任务的）终点。 |
| sampling | 采样 | 把连续的声压信号按固定时间间隔离散化。每秒采样次数即采样率，决定了能表示的最高频率与数据量。 |
| sampling rate / fs | 采样率 | 每秒采样点数（Hz）。语音常用 16 kHz（电话/ASR）、音乐用 44.1 kHz（CD）或 48 kHz；EnCodec/Mimi 等编解码也按这些率设计。 |
| Nyquist frequency | 奈奎斯特频率 | 采样率的一半，是无失真可表示的最高频率上限。超过它的频率会被「折叠」成低频假象（aliasing），所以采样前要低通滤波。 |
| aliasing | 混叠 | 采样率不足时，高频成分伪装成低频出现，无法还原。车轮在视频里倒转是同一现象的视觉版。 |
| quantization | 量化 | 把每个采样的连续幅度近似到有限个离散电平（如 16 bit = 65536 级）。位深越高越精细，量化误差表现为底噪。 |
| bit depth | 位深 | 每个采样用多少比特表示幅度。16 bit 是 CD/语音常见值；位深决定动态范围（约 6 dB/bit）。 |
| dynamic range | 动态范围 | 信号最强与最弱可分辨成分的幅度比（dB）。受位深（量化底噪）限制。 |
| amplitude | 振幅 | 波形在某时刻偏离静止的大小，对应声音的瞬时强度；其平方的时间平均对应能量/响度。 |
| frequency | 频率 | 单位时间内的振动次数（Hz），感知上对应音高（pitch）。复杂声音是多个频率成分的叠加。 |
| phase | 相位 | 一个频率成分在周期中的位置（弧度）。人耳对单一相位不敏感，但相位决定波形对齐，是 Griffin-Lim 等重建算法要恢复的东西。 |

## 频域与变换 · Frequency Domain & Transforms

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Fourier transform | 傅里叶变换 | 把信号从时间域分解成不同频率的正弦成分之和。是「频率内容」这一概念的数学定义，整个频域分析的根基。 |
| DFT (Discrete Fourier Transform) | 离散傅里叶变换 | 对有限长离散信号的傅里叶变换：$X[k]=\sum_n x[n]e^{-i2\pi kn/N}$。本课从零实现并与 `np.fft` 对拍。 |
| FFT (Fast Fourier Transform) | 快速傅里叶变换 | 计算 DFT 的高效算法，把 $O(N^2)$ 降到 $O(N\log N)$。结果与 DFT 完全相同，只是更快；`np.fft` 即其实现。 |
| rfft / real FFT | 实数 FFT | 对实信号的 FFT：因共轭对称只需保留前 $N/2+1$ 个频点（$0$ 到 Nyquist），省一半计算与存储。语音特征几乎都用它。 |
| magnitude / power spectrum | 幅度谱 / 功率谱 | DFT 系数的模 $|X[k]|$（幅度）或其平方 $|X[k]|^2$（功率），表示各频率的强弱。丢弃相位、只保留幅度是大量语音特征的共同操作。 |
| spectrogram | 谱图 / 声谱图 | 把 STFT 的幅度（或功率）画成「时间×频率」的二维热图，是观察语音随时间频率变化的标准视图。 |
| bin / frequency bin | 频点 / 频率桶 | DFT 输出的离散频率刻度，第 $k$ 个对应频率 $k\cdot f_s/N$。频点间隔 $f_s/N$ 即频率分辨率。 |

## 短时分析 · Short-Time Analysis

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| framing | 分帧 | 把长信号切成许多短小、相互重叠的片段（帧），因为语音是「短时平稳」的——只有在 20–40 ms 的尺度上频率成分才近似不变。 |
| frame length / window size | 帧长 / 窗长 | 每帧的采样点数（如 16 kHz 下 400 点 = 25 ms）。帧长越长频率分辨率越高、时间分辨率越低（时频不确定性）。 |
| hop length / stride | 帧移 / 步长 | 相邻帧起点的间隔（如 160 点 = 10 ms）。帧长与帧移之差即重叠量；帧移决定特征的时间帧率。 |
| windowing | 加窗 | 给每帧乘一个两端渐弱的窗函数，抑制因截断产生的频谱泄漏（spectral leakage）。不加窗等于乘矩形窗，旁瓣很大。 |
| Hann / Hamming window | 汉宁 / 汉明窗 | 常用的钟形窗函数，主瓣略宽但旁瓣低，能显著减少泄漏。语音处理默认选择之一。 |
| spectral leakage | 频谱泄漏 | 信号频率不恰好落在某个 DFT 频点时，能量「泄漏」到邻近频点形成拖尾。加窗是主要缓解手段。 |
| STFT (Short-Time Fourier Transform) | 短时傅里叶变换 | 对每个加窗帧做 DFT，得到随时间变化的频谱 $X[t,k]$。是谱图、梅尔谱、MFCC 的共同第一步，本课从零实现。 |
| overlap-add (OLA) | 重叠相加 | STFT 逆变换：把每帧 IDFT 回时域后按帧移重叠累加（再除以窗能量）重建波形。Griffin-Lim 的 iSTFT 即基于它。 |
| time-frequency resolution | 时频分辨率 | 帧长决定的权衡：窗越长频率越准、时间越糊；窗越短反之。海森堡式不确定性，无法同时无限精确。 |

## 听觉特征 · Auditory Features

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| mel scale | 梅尔刻度 | 模拟人耳对音高的非线性感知：低频分得细、高频分得粗。常用 $m=2595\log_{10}(1+f/700)$，是梅尔谱/MFCC 的核心。 |
| mel filterbank | 梅尔滤波器组 | 一组在梅尔刻度上等间隔、形状为三角的带通滤波器。把线性频率的功率谱「打包」成几十个梅尔频带的能量，压缩并贴近听觉。 |
| mel spectrogram | 梅尔谱 | 功率谱经梅尔滤波器组加权求和（常再取对数）得到的「时间×梅尔频带」特征。是现代语音/TTS 模型（Whisper、声码器）的主力输入/中间表示。 |
| log-mel | 对数梅尔 | 对梅尔能量取对数，模拟人耳对响度的对数感知、压缩动态范围。Whisper 的输入即 log-mel 谱。 |
| MFCC (Mel-Frequency Cepstral Coefficients) | 梅尔频率倒谱系数 | 对 log-mel 谱做 DCT 得到的少数几个系数（常取前 13）。能去相关、压缩维度，是深度学习前最主流的语音特征，至今仍是强基线。 |
| cepstrum | 倒谱 | 对（对数）谱再做一次傅里叶/余弦变换得到的「谱的谱」。能把声源（基频）与声道（共振峰）在倒谱域分离，是 MFCC 的理论来源。 |
| DCT (Discrete Cosine Transform) | 离散余弦变换 | 一种只用余弦基的实变换，能量集中在前几个系数（去相关性强）。MFCC 用 DCT-II 把 log-mel 压成低维、近似不相关的系数。 |
| formant | 共振峰 | 声道（口腔/咽腔）的共振频率，在谱包络上表现为几个峰，决定元音音色。语音识别与合成都隐式建模它。 |
| pitch / F0 | 基频 | 声带振动的基本频率，感知为音高，对应谱中等间隔的谐波梳。语调、声调语言（如中文）都由它承载。 |
| fbank / filterbank features | 滤波器组特征 | 不做 DCT 的 log-mel 能量。深度模型常直接吃 fbank（保留更多信息），把「去相关」交给网络自己学。 |

## 自动语音识别 · ASR

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| ASR (Automatic Speech Recognition) | 自动语音识别 | 把语音波形转写成文字的任务。核心难点是输入（成百上千帧）与输出（几十个字符）长度不一且未对齐。 |
| CTC (Connectionist Temporal Classification) | 连接时序分类 | 一种无需逐帧对齐就能训练序列模型的损失/解码框架。引入空白符（blank）与「折叠重复」规则，把所有能产生目标文本的对齐路径概率求和。本课从零实现其前向算法。 |
| blank token | 空白符 | CTC 中的特殊符号 $\epsilon$，表示「此帧不输出新字符」。它让模型可以停顿、可以重复字符（用 blank 隔开），是 CTC 处理长度不齐的关键。 |
| alignment / path | 对齐 / 路径 | 一条逐帧的标签序列（含 blank 与重复），折叠后得到输出文本。一个文本对应指数多条对齐路径，CTC 对它们求和。 |
| collapse rule | 折叠规则 | 把一条对齐路径变成文本的两步：先合并连续相同字符，再删除所有 blank。如 `a a ε a → a a`，`ε a a ε b → a b`。 |
| forward algorithm | 前向算法 | 用动态规划在 $O(T\cdot S)$ 时间内对所有对齐路径概率求和（$T$ 帧、$S$ 扩展标签长度），是 CTC 训练与似然计算的核心。本课对拍暴力枚举。 |
| forward–backward | 前向–后向 | 前向 $\alpha$ 与后向 $\beta$ 结合，给出每个时刻每个标签的后验占据概率，用于计算 CTC 梯度。 |
| greedy decoding | 贪心解码 | 每帧取概率最大的符号，再折叠成文本。快但次优（忽略了路径求和），是 CTC 解码的最简基线。 |
| beam search decoding | 束搜索解码 | 维护若干条最优「文本前缀」假设，逐帧扩展并按折叠后概率合并，逼近最可能的文本。比贪心好，是 CTC/seq2seq 的常用解码。 |
| seq2seq / encoder–decoder | 序列到序列 / 编码器–解码器 | 编码器把语音编成隐表示，解码器自回归地生成文本 token。Whisper 即此架构，用交叉注意力让解码器「看」语音。 |
| Whisper | —— | OpenAI 2022 的大规模弱监督 ASR/翻译模型：log-mel 输入 + Transformer encoder–decoder，用 68 万小时多语数据训练，靠规模获得强鲁棒性与多任务能力（转写/翻译/语种识别）。 |
| WER (Word Error Rate) | 词错误率 | ASR 标准评测：把识别结果对齐到参考文本，统计 (替换+删除+插入)/参考词数。越低越好，是论文报告的主指标。 |
| LAS / RNN-T | —— | 两类经典 ASR 架构：LAS（Listen-Attend-Spell）是注意力 seq2seq；RNN-Transducer 把 CTC 式对齐与语言模型联合，适合流式。 |

## 神经音频编解码 · Neural Audio Codecs

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| codec | 编解码器 | 把音频压缩成紧凑表示（编码）再还原（解码）的系统。神经编解码用神经网络做编码器/解码器，并用离散码替代传统量化。 |
| vector quantization (VQ) | 矢量量化 | 把一个向量近似成码本中最近的一个码字，用其下标（整数）代替原向量。是把连续表示离散化的最基本手段，本课从零实现最近邻量化。 |
| codebook | 码本 | 一组可学习的代表性向量（码字）。VQ 用它做最近邻替换；码本大小 $K$ 决定每个 token 的比特数 $\log_2 K$。 |
| codeword / code index | 码字 / 码本下标 | 码本中的一个向量及其整数编号。编码后传输/存储的就是这些整数下标，解码时查表还原。 |
| VQ-VAE | —— | van den Oord 2017 提出的离散自编码器：编码器输出经 VQ 离散化再解码，用直通梯度（straight-through）训练。是神经离散表示与神经编解码的奠基工作。 |
| residual VQ (RVQ) | 残差矢量量化 | 用多个码本逐级量化「上一级的残差」：第一级量化 $x$，第二级量化 $x-q_1$，依此类推。用 $N$ 个小码本表达 $K^N$ 级精度，是 SoundStream/EnCodec 的核心。本课从零实现。 |
| quantizer / codebook level | 量化器 / 码本级数 | RVQ 中串联的每一级 VQ。级数越多重建越精、比特率越高；可在推理时只用前几级实现可变比特率。 |
| codebook utilization | 码本利用率 | 实际被用到的码字占码本的比例。利用率低（码本坍缩）意味着浪费比特，是 VQ 训练的常见病，需 EMA 更新/重启等技巧缓解。 |
| codebook collapse | 码本坍缩 | 大量码字从不被选中、只有少数码字反复使用的退化现象。导致有效码本变小、重建变差。 |
| bitrate | 比特率 | 每秒音频用多少比特表示（bps/kbps）。$=\text{帧率}\times\text{级数}\times\log_2 K$。神经编解码能在 1.5–24 kbps 达到接近原声的质量。 |
| EnCodec | —— | Meta 2022 的神经音频编解码：卷积自编码器 + RVQ + 对抗/重建损失，可在极低比特率高保真重建，并把音频离散成 token 供下游语言模型使用。 |
| SoundStream | —— | Google 2021 的端到端神经编解码，首次系统化用 RVQ + 对抗训练做低比特率音频，是 EnCodec/AudioLM token 化的前身。 |
| acoustic token | 声学 token | 神经编解码（如 EnCodec/SoundStream RVQ）产出的离散码，细致刻画波形细节（音色、声学环境），是音频 LM 的「词表」。 |
| semantic token | 语义 token | 从自监督语音模型（如 HuBERT/w2v-BERT）量化得到的离散码，更偏语言内容、较少声学细节。AudioLM 用「语义→声学」两段建模。 |
| reconstruction loss | 重建损失 | 衡量解码输出与原音频差异的损失（时域 L1/L2 + 多尺度谱损失）。与对抗损失共同决定编解码的保真度。 |

## TTS 与声码器 · TTS & Vocoders

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| TTS (Text-to-Speech) | 语音合成 | 把文字变成自然语音。现代流水线常分两段：文本→声学特征（如梅尔谱），再声学特征→波形（声码器）。 |
| acoustic model | 声学模型 | TTS 中把文本/音素序列映射成声学特征（梅尔谱）的模型，如 Tacotron、FastSpeech。 |
| vocoder | 声码器 | 把声学特征（梅尔谱）还原成时域波形的模块。难点在于谱图通常只有幅度、丢了相位，需要「造」出相位。 |
| Griffin-Lim | —— | 一种仅凭幅度谱迭代重建相位的经典算法：反复 iSTFT→STFT、每轮用当前估计的相位替换、保持幅度不变，直到一致。本课从零实现并观察收敛。 |
| phase reconstruction | 相位重建 | 从只有幅度的谱图恢复出可听波形所需的相位信息。Griffin-Lim 是无学习的经典解，神经声码器是数据驱动的解。 |
| neural vocoder | 神经声码器 | 用神经网络从梅尔谱直接生成波形，质量远超 Griffin-Lim。代表：WaveNet（自回归）、WaveRNN、Parallel WaveGAN、HiFi-GAN（GAN）。 |
| WaveNet | —— | DeepMind 2016 的自回归原始波形生成模型：用扩张因果卷积逐采样点建模 $p(x_t\mid x_{<t})$，首次让神经网络合成出接近真人的语音，是神经声码器的开山之作。 |
| mel inversion | 梅尔逆变换 | 从梅尔谱近似还原线性幅度谱的步骤（用梅尔滤波器组的伪逆）。Griffin-Lim 式声码器先做它再做相位重建。 |
| spectral convergence | 谱收敛度 | 衡量重建谱与目标幅度谱差异的指标，常用作 Griffin-Lim 收敛与声码器质量的量化标准。 |
| autoregressive vocoder | 自回归声码器 | 逐采样点/逐帧依赖已生成内容的声码器（WaveNet/WaveRNN），质量高但慢；与之相对的是并行（GAN/flow）声码器。 |

## 语音 LLM 与流式 · Speech LLMs & Streaming

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| audio tokenization | 音频 token 化 | 把连续音频离散成整数 token 序列（经神经编解码或自监督量化），从而可以套用文本 LLM 的「下一个 token 预测」范式。 |
| speech / audio language model | 语音 / 音频语言模型 | 在离散音频 token 上训练的自回归模型，直接「续写音频」。AudioLM、MusicLM、VALL-E、Moshi 等都属此类。 |
| discrete token | 离散 token | 把音频量化后的整数序列。离散化让音频能用与文本相同的交叉熵、采样、KV-cache 等机制建模。 |
| AudioLM | —— | Google 2022 的音频生成框架：先用语义 token 建模长程结构，再用声学 token（RVQ）补全细节，分层生成连贯且高保真的语音/音乐。 |
| VALL-E | —— | 微软 2023 的神经编解码语言模型 TTS：把 TTS 当成「在 EnCodec token 上的条件语言建模」，仅凭 3 秒示例即可零样本克隆音色。 |
| Moshi | —— | Kyutai 2024 的全双工语音对话模型：用 Mimi 神经编解码 + 多流语音 LM，实现低延迟、可同时听说的流式语音交互。 |
| Mimi | —— | Moshi 配套的流式神经音频编解码，低帧率、低延迟、语义+声学联合，专为实时语音 LM 设计。 |
| streaming / online generation | 流式 / 在线生成 | 不等完整输入就分块（chunk）边收边算边出，关键指标是延迟（latency）。实时语音对话与 ASR 的硬要求。 |
| chunk / lookahead | 块 / 前瞻 | 流式处理一次消费的一小段音频，以及为提精度允许多看的少量未来帧。块越小延迟越低、上下文越少。 |
| n-gram language model | n 元语言模型 | 用前 $n-1$ 个 token 的频次估计下一个 token 概率的经典统计 LM。本课用它做「玩具离散语音 LM」，把 token 序列建模与文本 LM 完全打通。 |
| interleaving / alignment | 交错 / 对齐 | 把文本 token 与音频 token（或语义与声学流）按时间交错排列，让单个自回归模型同时建模二者。是多流语音 LM 的关键技巧。 |
| full-duplex | 全双工 | 系统能同时收听与说话（如人类对话中的插话/反馈），而非「你说完我再说」的半双工。Moshi 的核心卖点。 |
| latency | 延迟 | 从输入到输出的时间。流式语音系统的生命线：端到端延迟低于约 200–300 ms 才有自然对话的感觉。 |
