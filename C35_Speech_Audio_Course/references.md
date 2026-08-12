# 参考清单 · References（语音与音频）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制（STFT/梅尔/MFCC、CTC、VQ/RVQ、Griffin-Lim、离散语音 LM），都能在下列文献里找到完整理论与真实系统的对应。

## 信号处理基础 · DSP Foundations
- ★ **Oppenheim & Schafer, _Discrete-Time Signal Processing_** — 数字信号处理的权威教科书。采样定理、DFT/FFT、加窗与频谱泄漏、STFT、滤波器设计全部出自此书。本课模块 01 的每个公式（奈奎斯特、DFT 定义、窗函数、overlap-add）都能在这里找到严格推导，遇到概念分歧以它为准。
- ★ **Rabiner & Schafer, _Theory and Applications of Digital Speech Processing_** — 语音信号处理的经典专著。讲清语音的产生模型（声源-声道）、短时分析、倒谱、共振峰、基频提取，是 MFCC 与一切语音特征的理论母体。模块 01 听觉特征部分的延伸阅读。
- **Smith, _The Scientist and Engineer's Guide to Digital Signal Processing_（免费在线）** — 极其直观、面向工程师的 DSP 入门，对傅里叶变换、卷积、滤波的图解胜过千言。想先建立直觉再啃 Oppenheim 的人从这本起步。
- **Stevens, Volkmann & Newman 1937, _A Scale for the Measurement of the Psychological Magnitude Pitch_** — 梅尔刻度的原始心理声学实验。读它理解「为什么是 $2595\log_{10}(1+f/700)$」——梅尔不是数学发明，而是人耳听感的测量结果。模块 01 梅尔滤波器组的根据。
- **Davis & Mermelstein 1980, _Comparison of Parametric Representations for Monosyllabic Word Recognition_** — MFCC 的奠基论文，确立了「log-mel + DCT」这套至今仍是强基线的语音特征。模块 01 的 MFCC 直接复现它。

## 自动语音识别 · ASR
- ★ **Graves, Fernández, Gomez & Schmidhuber 2006, _Connectionist Temporal Classification: Labelling Unsegmented Sequence Data with Recurrent Neural Networks_** — CTC 的原始论文，本课模块 02 的核心。提出 blank 符号 + 折叠规则 + 前向-后向算法，让序列模型无需逐帧对齐即可训练。必读，模块 02 全程在复现它的前向算法与解码。
- ★ **Radford, Kim, Xu, Brockman, McLeavey & Sutskever 2022, _Robust Speech Recognition via Large-Scale Weak Supervision_（Whisper）** — 用 68 万小时弱监督数据训练的 encoder–decoder ASR/翻译模型。展示「规模 + 弱监督」如何带来零样本鲁棒性与多任务能力。模块 02 架构概览的主角，读它理解现代 ASR 的工程范式。
- **Graves & Jaitly 2014, _Towards End-to-End Speech Recognition with Recurrent Neural Networks_** — 把 CTC 用到端到端语音识别的早期里程碑，展示无需 HMM 对齐的纯神经 ASR 可行。理解 CTC 从理论到 ASR 落地的桥梁。
- **Chan, Jaitly, Le & Vinyals 2015, _Listen, Attend and Spell (LAS)_** — 注意力 seq2seq 做 ASR 的代表作，是 Whisper 式 encoder–decoder 的前身。与 CTC 对照阅读，理解「对齐求和」vs「注意力软对齐」两条技术路线。
- **Graves 2012, _Sequence Transduction with Recurrent Neural Networks (RNN-T)_** — 把 CTC 与语言模型联合的转导器，是流式 ASR（手机听写）的主流框架。模块 02/05 流式部分的延伸。
- **Amodei et al. 2016, _Deep Speech 2_** — 大规模 CTC 端到端 ASR 的工程化样板（多语、GPU 训练、束搜索 + 语言模型）。理解 CTC 在工业界的完整流水线。

## 神经离散表示与音频编解码 · Neural Discrete Representations & Codecs
- ★ **van den Oord, Vinyals & Kavukcuoglu 2017, _Neural Discrete Representation Learning (VQ-VAE)_** — 矢量量化进入深度学习的奠基作。提出可学习码本 + 最近邻量化 + 直通梯度 + commitment loss，让自编码器学出离散表示。本课模块 03 的 VQ 直接源于它，也是一切音频 token 化的根。
- ★ **Défossez, Copet, Synnaeve & Adi 2022, _High Fidelity Neural Audio Compression (EnCodec)_** — Meta 的神经音频编解码，本课模块 03 的工程目标。卷积自编码器 + 残差矢量量化（RVQ）+ 多尺度谱判别器，在 1.5–24 kbps 高保真重建，并把音频离散成 token 供语言模型使用。必读，模块 03 的 RVQ 复现它的核心。
- ★ **Zeghidour, Luebs, Omran, Skoglund & Tagliasacchi 2021, _SoundStream: An End-to-End Neural Audio Codec_** — 首个系统化用 RVQ + 对抗训练做低比特率音频的端到端编解码，EnCodec 与 AudioLM token 化的直接前身。读它理解 RVQ 为何是「可变比特率 + 高保真」的关键设计。
- **Kumar et al. 2023, _High-Fidelity Audio Compression with Improved RVQGAN (DAC)_** — 改进的 RVQ 编解码，用因子化码本 + 量化 dropout 等技巧大幅提升码本利用率与音质。模块 03「码本利用率/坍缩」一节的现实对应与解药。
- **Gray 1984, _Vector Quantization_（IEEE ASSP Magazine）** — VQ 的经典综述，把矢量量化、码本设计（LBG/k-means）、率失真讲透。理解 VQ-VAE 之前，传统 VQ 的数学基础。

## 语音合成与声码器 · TTS & Vocoders
- ★ **Griffin & Lim 1984, _Signal Estimation from Modified Short-Time Fourier Transform_** — Griffin-Lim 算法的原始论文，本课模块 04 的核心。给出仅凭幅度谱迭代估计相位的方法与收敛性分析。必读，模块 04 从零复现它的迭代。
- ★ **van den Oord et al. 2016, _WaveNet: A Generative Model for Raw Audio_** — 用扩张因果卷积逐采样点自回归生成原始波形，首次让神经声码器合成出接近真人的语音。模块 04 神经声码器的开山之作，读它理解「直接建模波形」这条路线的起点与代价（慢）。
- **Shen et al. 2017, _Tacotron 2: Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions_** — 确立「文本→梅尔谱（声学模型）→波形（声码器）」两段式 TTS 范式。模块 04 流水线划分的依据。
- **Kong, Kim & Bae 2020, _HiFi-GAN: Generative Adversarial Networks for Efficient and High Fidelity Speech Synthesis_** — 用 GAN 做并行神经声码器，质量接近 WaveNet 而速度快几个数量级，是当前 TTS 的主力声码器。模块 04「神经声码器演进」的现代终点。
- **Ren et al. 2019/2020, _FastSpeech (2)_** — 非自回归声学模型，用时长预测器并行生成梅尔谱，解决 Tacotron 自回归的慢与不稳。理解 TTS 声学模型一侧的并行化。

## 音频语言模型与流式 · Audio LMs & Streaming
- ★ **Borsos et al. 2022, _AudioLM: a Language Modeling Approach to Audio Generation_** — 把音频生成变成「在离散 token 上的语言建模」的奠基框架，本课模块 05 的主角。先用语义 token 建长程结构、再用声学 token（RVQ）补细节的分层方案，生成连贯且高保真的语音/音乐。必读，串起模块 03（token 化）与模块 05（语音 LM）。
- ★ **Wang et al. 2023, _Neural Codec Language Models are Zero-Shot Text to Speech Synthesizers (VALL-E)_** — 把 TTS 当成「在 EnCodec token 上的条件语言建模」，仅凭 3 秒示例零样本克隆音色。读它理解「编解码 token + LM」如何统一识别、合成与生成。
- **Défossez et al. 2024, _Moshi: a speech-text foundation model for real-time dialogue_** — 全双工实时语音对话模型，用 Mimi 流式编解码 + 多流语音 LM 实现低延迟、可同时听说。模块 05 流式/全双工部分的现实标杆。
- **Agostinelli et al. 2023, _MusicLM: Generating Music From Text_** — 把 AudioLM 的分层 token 建模用于文本到音乐生成，展示该范式在音乐上的威力。模块 05 的延伸应用。
- **Hsu et al. 2021, _HuBERT: Self-Supervised Speech Representation Learning by Masked Prediction_** — 自监督语音表示，其量化产出常作为 AudioLM 的「语义 token」。理解语义 token 从何而来。
- **Lakhotia et al. 2021, _Generative Spoken Language Modeling from Raw Audio (GSLM)_** — 「无文本」语音语言建模的早期系统化工作，把语音离散成单元再做 LM，是语音 LLM 的思想先驱。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **全程纯 numpy / 标准库 / CPU**：本课用 numpy 从零实现 STFT/梅尔/MFCC、CTC 前向、VQ/RVQ、Griffin-Lim、离散语音 LM；音频用**合成信号**（正弦/啁啾/脉冲串），需要真实参数时用**真实工程数值**（16 kHz、Whisper/EnCodec 配置）。每个机制都与**朴素参考或暴力枚举对拍**（CTC 前向 == 路径枚举、RVQ 残差递减、Griffin-Lim 谱收敛单调），保证逻辑正确、`assert` 能过；**联网或 scipy 缺失时一律回退到内置合成数据**。
- **可迁移性**：你在 numpy 里验证过的 STFT/梅尔/CTC/RVQ/Griffin-Lim 逻辑，几乎一对一对应 `torchaudio` / `librosa` / Whisper / EnCodec 的真实实现，学完照着切换到真实框架是最自然的下一步。
- **课程衔接**：上游接 C01（Transformer/注意力，Whisper 与语音 LM 的骨架）；与 C16（多模态）、C24（推理服务/流式）、C25（长上下文）互补——语音正是「长序列 + 流式 + 多模态」三者交汇的实战场景。
