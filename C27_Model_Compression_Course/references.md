# 参考清单 · References（模型压缩与高效化）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零复现的每个算法，都能在下列文献里找到原始动机、完整推导与真实规模的实验。

## 整数量化与离群值 · Integer Quantization & Outliers
- ★ **Dettmers, Lewis, Belkada & Zettlemoyer 2022, _LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale_** — 8-bit 推理的奠基之作。发现大模型（>6.7B）的激活里存在少数「离群特征维度」，一旦用普通 int8 量化就会灾难性掉点；提出对这些维度保留 fp16、其余用 int8 的混合精度分解，实现几乎无损。本课模块 01 的离群值讨论与 bitsandbytes 都源于它，必读。
- ★ **Nagel et al. 2021, _A White Paper on Neural Network Quantization_（Qualcomm）** — 量化的系统综述与「教科书」。把对称/非对称、per-tensor/per-channel、PTQ/QAT、cross-layer equalization 等讲得最清楚、记号最统一。模块 01 的术语与公式以它为准，遇到量化概念分歧查这里。
- **Jacob et al. 2018, _Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference_（Google，"gemmlowp"）** — 工业界整数推理的经典：定义了仿射量化 `q=round(x/s)+z`、整数-only 矩阵乘的零点处理，是 TFLite 量化的理论基础。想搞清 zero-point 在矩阵乘里怎么展开，读它。
- **Dettmers et al. 2023, _QLoRA: Efficient Finetuning of Quantized LLMs_** — 提出 4-bit NormalFloat（NF4，按正态分位点设量化级别）、double quantization 与分页优化器，使单卡微调 65B 成为可能。模块 01 「量化级别不必均匀」的最佳现实例证。

## 后训练量化算法 · PTQ Algorithms (GPTQ / AWQ / SmoothQuant)
- ★ **Frantar, Ashkboos, Hoefler & Alistarh 2022, _GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers_** — 本课模块 02 的主线之一。把 Optimal Brain Quantization 做成对大模型可行的逐列算法：逐列量化、用逆 Hessian 的 Cholesky 分解把误差补偿到未量化列，几小时把 175B 量化到 int3/int4。误差补偿的完整推导都在这里，必读。
- ★ **Lin, Tang, Tang et al. 2023, _AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration_** — 模块 02 的另一条主线。核心洞察：权重是否重要由对应激活的幅度决定，只要保护好约 1% 的显著通道（给它们缩放保护）就能保住精度，无需逐列重建、无反量化开销、对指令模型友好。必读，与 GPTQ 对照着看最有收获。
- **Frantar & Alistarh 2022, _Optimal Brain Compression (OBC/OBQ)_** — GPTQ 的直接前身与理论根基，把 Optimal Brain Surgeon 的逆 Hessian 思想统一用于剪枝与量化。想理解 GPTQ 的误差补偿系数从哪来、为什么是逆 Hessian，读它。
- **Xiao, Lin, Seznec, Wu, Demouth & Han 2022, _SmoothQuant: Accurate and Efficient Post-Training Quantization for LLMs_** — 让权重+激活都量化到 int8（W8A8）可行：把激活的离群「难度」按通道部分迁移到权重上（激活除 s、权重乘 s）。与 AWQ 同源的「缩放迁移」思想，模块 02 的延伸阅读。
- **Nagel et al. 2020, _Up or Down? Adaptive Rounding for Post-Training Quantization (AdaRound)_** — 证明逐元素 round-to-nearest 并非最优，应按对损失的影响自适应地决定每个权重向上还是向下取整。是「RTN 不是最优」这一关键认知的奠基，GPTQ 与它一脉相承。

## 低精度浮点与 fp8 训练 · Low-precision Floating-point & FP8
- ★ **Micikevicius et al. 2017, _Mixed Precision Training_（NVIDIA/Baidu）** — 混合精度训练的奠基：fp16 算、fp32 存主权重、loss scaling 防梯度下溢。模块 03 的 loss scaling、master weights 全部源于此，是理解一切低精度训练的起点，必读。
- ★ **Micikevicius et al. 2022, _FP8 Formats for Deep Learning_（NVIDIA/Arm/Intel）** — fp8 的标准化提案，定义 E4M3 与 E5M2 两种格式及各自适用场景（E4M3 前向、E5M2 梯度），给出训练配方。模块 03 的 fp8 表示与 scaling 直接来自它，必读。
- **NVIDIA, _Transformer Engine 文档_** — fp8 训练的工程实现：delayed scaling、amax 历史缓冲、fp8 GEMM 的封装。把模块 03 的纸面 scaling 落到真实训练，看它。
- **Wang et al. 2018, _Training Deep Neural Networks with 8-bit Floating Point Numbers_（IBM）** — 早期 8-bit 浮点训练探索，提出 chunk-based 累加等技巧应对低精度累加误差。理解 fp8 训练为何对「累加精度」格外讲究，读它。
- **Peng et al. 2023, _FP8-LM: Training FP8 Large Language Models_（Microsoft）** — 把 fp8 用到优化器状态与分布式通信，端到端 fp8 训练大模型。模块 03 「fp8 不止用于 GEMM」的现实延伸。

## 知识蒸馏 · Knowledge Distillation
- ★ **Hinton, Vinyals & Dean 2015, _Distilling the Knowledge in a Neural Network_** — 知识蒸馏的开山之作。提出用教师的软标签 + 温度训练学生，并解释「暗知识」为何比硬标签更有信息量、温度如何放大它、损失为何要乘 `T²`。模块 04 全程在复现它的核心，必读。
- **Romero et al. 2014, _FitNets: Hints for Thin Deep Nets_** — 特征蒸馏奠基：不只匹配输出，还让学生中间层去拟合教师中间层的「提示」（hint），并用投影对齐维度。模块 04 feature distillation 的来源。
- **Sanh et al. 2019, _DistilBERT_** — 工业界蒸馏的代表：用蒸馏把 BERT 压到 40% 大小、保留 97% 性能。组合了软标签、MLM 与 cosine 嵌入损失，是「蒸馏真的能压缩」的最有力证据之一。
- **Jiao et al. 2019, _TinyBERT_ / Wang et al. 2020, _MiniLM_** — Transformer 蒸馏的进阶：蒸馏注意力矩阵与隐藏状态的关系（attention/value-relation distillation）。模块 04 attention distillation 的现实对应，效果显著。
- **Furlanello et al. 2018, _Born-Again Neural Networks_** — 自蒸馏的代表：学生与教师同架构，用上一代自己当教师反复蒸馏，竟能超过教师。模块 04 self-distillation 的来源，揭示蒸馏不只是「压缩」。
- **Agarwal et al. 2023 / Gu et al. 2023, _On-policy / Generalized KD (GKD)_** — 指出固定数据集蒸馏存在训练-推理分布不匹配，应在学生自己生成的样本上蒸馏（on-policy）。模块 04 on-policy 蒸馏的依据，对生成式 LLM 尤为重要。

## 剪枝与稀疏 · Pruning & Sparsity
- ★ **Frantar & Alistarh 2023, _SparseGPT: Massive Language Models Can Be Accurately Pruned in One-Shot_** — 把 GPTQ 的逐层逆 Hessian 重建用到剪枝：一次性把 175B 剪到 50%+ 稀疏几乎不掉点、无需重训，还能与量化叠加。模块 05 「剪枝也能做误差补偿重建」的主线，必读。
- ★ **Mishra et al. 2021, _Accelerating Sparse Deep Neural Networks_（NVIDIA，2:4 稀疏白皮书）** — 2:4 半结构稀疏的奠基与硬件支持说明：每 4 个权重留 2 个、配合 Ampere Sparse Tensor Core 原生 2× 加速，并给出「剪枝→重训」恢复精度的配方。模块 05 的 2:4 部分直接来自它，必读。
- ★ **Frankle & Carlin 2018, _The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks_** — 提出稠密网络里存在用原始初始化即可单独训练到同等精度的稀疏子网（中奖彩票），并用迭代幅度剪枝（IMP）找到它。深刻影响了对稀疏与可训练性的理解，模块 05 必读。
- **Han, Pool, Tran & Dally 2015, _Learning both Weights and Connections / Deep Compression_** — 现代剪枝的奠基：幅度剪枝 + 重训 + 量化 + 哈夫曼编码的流水线，把模型压缩一个数量级。模块 05 幅度剪枝与「剪枝-微调」循环的源头。
- **Frankle et al. 2020, _Linear Mode Connectivity and the Lottery Ticket Hypothesis_（rewinding）** — 修正彩票假说：大模型上要把保留权重回卷到训练早期（而非最初随机）才稳定有效。理解 rewinding 为什么必要，读它。
- **Sun et al. 2023, _Wanda: Pruning by Weights and Activations_** — 比 SparseGPT 更简单的 one-shot 剪枝准则：按 `|权重| × ‖激活‖` 排序剪枝，无需逆 Hessian 也能很好。模块 05 「剪枝准则可以更简单」的对照阅读。

## 综述与系统视角 · Surveys & Systems
- ★ **Horace He 2022, _Making Deep Learning Go Brrrr From First Principles_（博客）** — 把性能瓶颈分成算力受限、访存受限、开销受限三类。理解「为什么 weight-only 量化即便要反量化也能加速」（LLM 推理访存受限，省的是带宽不是算力）的世界观文章，贯穿全课，强烈建议先读。
- **Gholami et al. 2021, _A Survey of Quantization Methods for Efficient Neural Network Inference_** — 量化方法的全面综述，把本课模块 01/02 的各种维度（粒度、对称性、PTQ/QAT、混合精度）放进统一图景，适合建立全局观后按图索骥。
- **Hoefler et al. 2021, _Sparsity in Deep Learning_** — 稀疏的百科全书式综述，覆盖剪枝准则、结构、训练动力学与硬件。模块 05 的延伸总图。
- ⚠️ **本课定位**：全程用 numpy 在 CPU 上**从零实现**这些算法的核心机制（量化-反量化、逆 Hessian 误差补偿、AWQ scale 搜索、fp8 cast 与 scaling、温度蒸馏 KL、幅度剪枝与 2:4 mask），并与全精度参考**对拍**，确保逻辑数值正确。真实 GPT-2 权重张量可选加载（联网失败回退到统计匹配的合成权重）。
- **课程衔接**：上游接 C01（Transformer 数学）；与 C36（GPU 内核：量化/稀疏内核如何在硬件上真正变快）、C08（训练系统：混合精度与并行）、C24/C25（推理服务与长上下文：weight-only 量化、KV-cache 量化、2:4 稀疏的落地）紧密互补。
