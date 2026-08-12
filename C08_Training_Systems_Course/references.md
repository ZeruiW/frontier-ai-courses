# References · 参考文献与数据来源

> 每条注明「解决了什么问题 / 为何值得读」。**★ = 必读**：这几篇是理解本课账本与系统直觉的地基，面试前务必能复述其核心结论。arXiv id 在确知处给出，存疑处只给作者+年份+标题（不臆造编号）。

---

## 01 · 显存解剖与 Roofline

- **★ Williams, Waterman & Patterson 2009 — *Roofline: An Insightful Visual Performance Model*** (CACM)。
  用峰值算力与内存带宽两条线给任意 kernel 画性能上界，提出算术强度与拐点的概念。**为何读**：本课判断“瓶颈在算力还是带宽”的全部直觉都源自这张图，是理解为什么自回归解码慢的母模型。
- **★ Korthikanti et al. 2022 — *Reducing Activation Recomputation in Large Transformer Models*** (arXiv:2205.05198, MLSys 2023)。
  精细拆解 Transformer 各算子的激活显存，提出 selective recomputation：只重算 $S^2$ 注意力部分，以远低于 33% 的算力代价省下大部分激活显存。**为何读**：把模块 01 的 activation 账与模块 02 的重计算量化到工程可用，并和张量并行配合。

---

## 02 · 混合精度与重计算

- **★ Micikevicius et al. 2018 — *Mixed Precision Training*** (arXiv:1710.03740, ICLR)。
  fp16 计算 + fp32 主权重 + loss scaling 的奠基论文。**为何读**：解释了为什么训练要保 fp32 主权重、loss scaling 怎么救梯度下溢——“16 bytes/param”账本的由来。
- **★ Chen et al. 2016 — *Training Deep Nets with Sublinear Memory Cost*** (arXiv:1604.06174)。
  提出 $\sqrt L$ 激活检查点：存 $O(\sqrt L)$ 个 checkpoint、反向重算，用一次额外前向换显存。**为何读**：长上下文/超深模型能训起来的关键技巧，模块 02 的核心推导。
- **Micikevicius et al. 2022 — *FP8 Formats for Deep Learning*** (arXiv:2209.05433)。
  定义 E4M3/E5M2 两种 fp8 排布及其训练用法。**为何读**：H100 fp8 训练（Transformer Engine）的格式标准，理解“再省一半”的前沿。

---

## 03 · 并行策略

- **★ Rajbhandari et al. 2020 — *ZeRO: Memory Optimizations Toward Training Trillion Parameter Models*** (arXiv:1910.02054, SC)。
  指出 DP 里每卡重复存的 $16P$ 状态是纯浪费，分三级分片到 $\approx16P/N$。**为何读**：FSDP/DeepSpeed 的理论根，本课模块 03 分片显存表的出处，训练大模型的第一选择。
- **Shoeybi et al. 2019 — *Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism*** (arXiv:1909.08053)。
  张量并行的经典做法：attention/MLP 矩阵一列切一行切，一层只需 2 次 all-reduce。**为何读**：理解 TP 通信代价与“限机内 NVLink”经验法则的来源。
- **Huang et al. 2019 — *GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism*** (arXiv:1811.06965, NeurIPS)。
  流水线并行与 micro-batch 摊薄气泡的奠基。**为何读**：模块 03 气泡占比 $\frac{p-1}{m+p-1}$ 公式的来由。
- **Narayanan et al. 2021 — *Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM (PTD-P)*** (arXiv:2104.04473, SC)。
  把 TP×PP×DP 的 3D 并行在数千卡上系统化，给出选维度的工程经验。**为何读**：训练 GPT-3 级模型的并行配方与 MFU 实战数据。

---

## 04 · FlashAttention

- **★ Dao et al. 2022 — *FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness*** (arXiv:2205.14135, NeurIPS)。
  用 tiling + online softmax + 反向重计算，把 attention 显存从 $O(S^2)$ 降到 $O(S)$，HBM I/O 从 $\Theta(S^2)$ 降到 $\Theta(S^2 d/M)$。**为何读**：本课“FLOPs 没少却更快”的 IO 视角范本，几乎所有现代长上下文模型的默认实现。
- **Dao 2023 — *FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning*** (arXiv:2307.08691)。
  改进并行与工作划分、减少非 matmul FLOPs，更逼近 GPU 峰值。**为何读**：理解从“IO 最优”到“也吃满算力”的工程演进。
- **Shah et al. 2024 — *FlashAttention-3*** (arXiv:2407.08608)。
  针对 H100 用异步与 fp8 再提速。**为何读**：最新硬件上的 attention 极致优化。
- **Milakov & Gimelshein 2018 — *Online normalizer calculation for softmax*** (arXiv:1805.02867)。
  online softmax 的原始推导：一遍流式扫描 + 运行态校正即可算出与两遍法逐位相等的 softmax。**为何读**：FlashAttention 数值核心的来源，模块 04 从零实现的依据。

---

## 05 · 量化

- **★ Dettmers et al. 2022 — *LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale*** (arXiv:2208.07339, NeurIPS)。
  发现大模型激活的离群特征会毁掉 per-tensor int8，提出混合精度分解：离群维度留 fp16、其余 int8。**为何读**：理解“离群值是量化头号敌人”，本课模块 05 的关键 danger 点。
- **Frantar et al. 2023 — *GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers*** (arXiv:2210.17323, ICLR)。
  逐列量化并用二阶 Hessian 信息调整剩余列补偿误差，使 int4/int3 几乎无损。**为何读**：误差感知量化的代表，int4 保精度的主力。
- **Lin et al. 2023 — *AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration*** (arXiv:2306.00978)。
  按激活幅度保护要害权重通道再量化。**为何读**：与 GPTQ 并列的主流 int4 方法，理解“误差不该被均匀对待”。
- **Dettmers & Zettlemoyer 2023 — *The case for 4-bit precision: k-bit Inference Scaling Laws*** (arXiv:2212.09720)。
  系统研究位宽与模型规模的精度-成本权衡，论证 4-bit 常是 sweet spot。**为何读**：把量化纳入 scaling law 视角，指导“几位最划算”。
- **Dettmers et al. 2023 — *QLoRA: Efficient Finetuning of Quantized LLMs*** (arXiv:2305.14314, NeurIPS)。
  用 4-bit NormalFloat（NF4，按正态分布最优分配量化级）+ double quantization 冻结量化基座、只训 LoRA 适配器。**为何读**：理解 NF4 与“单卡微调 65B”如何把量化与高效微调结合。
- **Xiao et al. 2023 — *SmoothQuant: Accurate and Efficient Post-Training Quantization for LLMs*** (arXiv:2211.10438, ICML)。
  把激活的量化难度按通道等价搬一部分到权重上，让激活与权重都易于 int8（W8A8）。**为何读**：直面激活离群值，是激活量化（而非仅权重量化）落地的关键技巧。

---

## 06 · 推理服务

- **★ Pope et al. 2022 — *Efficiently Scaling Transformer Inference*** (arXiv:2211.05102, MLSys 2023)。
  用 roofline + 并行布局系统分析 PaLM 推理：prefill/decode 的不同瓶颈、KV cache 与 batch 的取舍、延迟-吞吐-成本的权衡。**为何读**：推理成本估算的奠基范本，模块 06/07 推理账本与“多少卡服务”问题的标准参考。
- **★ Kwon et al. 2023 — *Efficient Memory Management for LLM Serving with PagedAttention (vLLM)*** (arXiv:2309.06180, SOSP)。
  像 OS 分页管理 KV cache 消碎片，配合 continuous batching 把吞吐拉满。**为何读**：现代推理引擎吞吐飞跃的关键，理解 KV 显存利用率为何能接近 100%。
- **Leviathan et al. 2023 — *Fast Inference from Transformers via Speculative Decoding*** (arXiv:2211.17192, ICML)。
  draft 猜 + target 一次并行验证，无损加速解码。**为何读**：模块 06 投机解码期望加速推导的出处。
- **Ainslie et al. 2023 — *GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints*** (arXiv:2305.13245)。
  query 头共享 K/V 头缩小 KV cache，几乎不掉精度。**为何读**：LLaMA-2/3 等模型 KV 显存优化的标配，理解 MHA→GQA→MQA 谱系。

---

## 07 · 成本估算与 Scaling Laws

- **★ Kaplan et al. 2020 — *Scaling Laws for Neural Language Models*** (arXiv:2001.08361)。
  首次系统拟合 loss 随参数、数据、算力的幂律。**为何读**：scaling 思维的起点，理解 $6ND$ 视角与“算力怎么分”问题的源头（其结论后被 Chinchilla 修正）。
- **★ Hoffmann et al. 2022 — *Training Compute-Optimal Large Language Models (Chinchilla)*** (arXiv:2203.15556, NeurIPS)。
  修正 Kaplan：给定算力 $N$ 与 $D$ 应同比例增长，最优 $D\approx20N$。**为何读**：判断一个模型是否 compute-optimal 的标准（GPT-3 训练不足、Chinchilla 70B 反超），评测对比模型时的必备前提。
- **Brown et al. 2020 — *Language Models are Few-Shot Learners (GPT-3)*** (arXiv:2005.14165, NeurIPS)。
  175B 参数、300B token 的里程碑模型。**为何读**：本课成本 drill 的经典算例（“GPT-3 训练量级/成本是多少”），也是 Chinchilla 训练不足论证的对象。
- **Sardana & Frankle 2023 — *Beyond Chinchilla-Optimal: Accounting for Inference in Language Model Scaling Laws*** (arXiv:2401.00448)。
  把推理成本计入目标后，应主动选更小、训得更久（over-train）的模型。**为何读**：解释为什么 LLaMA 系列远超 Chinchilla 的 token 数——推理感知缩放的理论依据。
- **Muennighoff et al. 2023 — *Scaling Data-Constrained Language Models*** (arXiv:2305.16264, NeurIPS)。
  高质量 token 用尽后重复数据的边际收益递减，多 epoch 不如加参数。**为何读**：把 Chinchilla 从“数据无限”假设拉回现实，理解 over-training 与数据墙。

---

## 延伸阅读（博客 / 技术报告 / 模型卡）

- **EleutherAI Pythia 套件**（论文 *Pythia: A Suite for Analyzing Large Language Models Across Training and Scaling*, arXiv:2304.01373，及各模型 HuggingFace 卡）。本课显存/并行/成本账本所用的真实 config（160M–12B）与训练事实（300B token Pile）来源。
- **GPT-NeoX-20B 技术报告**（Black et al. 2022, arXiv:2204.06745）与 **LLaMA / LLaMA-2 报告**（Touvron et al. 2023, arXiv:2302.13971 / 2307.09288）。对照更大规模的架构超参与 token 预算（LLaMA 是 over-training 的代表）。
- **NVIDIA A100 / H100 白皮书**：bf16/fp16/fp8 峰值算力与 HBM 带宽规格，本课时间/成本与 roofline 拐点计算的硬件数字来源。
- **HuggingFace `transformers` / `safetensors` 文档**：模块 05 用 HTTP Range 只读取单个权重张量的依据。

---

## 本课使用的真实数据（联网获取）

| 数据 | 用途 | 来源 |
|------|------|------|
| EleutherAI Pythia 160M–12B 的 `config.json` | 参数量 / 显存 / 并行 / 成本账本 | HuggingFace `EleutherAI/pythia-*` |
| GPT-NeoX-20B / GPT-2 的 `config.json` | 更大规模对照 | HuggingFace |
| GPT-2 真实权重张量（`h.0.attn.c_proj.weight`） | int8/int4 量化误差实测 | HuggingFace `openai-community/gpt2` 的 safetensors（HTTP Range 读取） |
| 真实硬件规格（A100 312T / H100 ~990T bf16）、Pythia 训练事实（300B token Pile） | 时间 / 成本估算 | 厂商白皮书 / Pythia 论文 |

> config 与权重首次运行下载并缓存到 `~/.training_systems_data/`。模块 05 用 HTTP Range 只下载需要的那一个权重张量（~2 MB），无需 torch/safetensors 库。全课算的是账本与模拟，CPU 可跑、不需要 GPU。
