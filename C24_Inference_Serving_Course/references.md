# 参考清单 · References（高效推理与服务）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 做成「模拟器 + 账本」的每个机制，都能在下列文献里找到真实系统上的对应实现与权衡。

## 显存管理与 PagedAttention · Memory & PagedAttention
- ★ **Kwon, Li, Zhuang, Sheng, Zheng, Yu, Gonzalez, Zhang & Stoica 2023, _Efficient Memory Management for Large Language Model Serving with PagedAttention_ (vLLM, SOSP)** — 本课模块 01 的源头。指出传统按 max_len 预分配 KV 导致 60–80% 显存被碎片浪费，借鉴操作系统虚拟内存提出把 KV 分页（block + block table），把利用率提到 ~96%、吞吐提升 2–4×，并用 copy-on-write 实现前缀/采样的零拷贝共享。必读，模块 01 全程在复现它。
- ★ **vLLM 官方文档与源码（`docs.vllm.ai`，`vllm/core/block_manager`、`scheduler`）** — 把论文落成工程：块管理器、三队列调度器、抢占与换出的真实代码。读它把模块 01/02 的 numpy 模拟器对回真实实现。
- **Sheng, Zheng, Yuan, Li, … & Zhang 2023, _FlexGen: High-throughput Generative Inference with a Single GPU_** — 在显存极度受限时如何用 CPU/磁盘卸载与张量级调度跑大模型。理解 KV/权重卸载（swapping）这一抢占恢复手段的来龙去脉。
- **NVIDIA, _TensorRT-LLM: KV cache 管理与 paged KV_ 文档** — 同一思想在 NVIDIA 栈的实现（paged KV、block reuse），与 vLLM 对照看会更立体。

## 连续批处理与调度 · Continuous Batching & Scheduling
- ★ **Yu, Jeong, Kim, Kim & Chun 2022, _Orca: A Distributed Serving System for Transformer-Based Generative Models_ (OSDI)** — 提出 iteration-level（continuous）batching 与 selective batching，让不同进度的请求在迭代粒度上动态进出 batch，相比静态批处理吞吐数倍提升。模块 02 的理论基础，必读。
- ★ **Agrawal, Panwar, Mohan, Kwatra, Gulavani & Ramjee 2024, _Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve_ (OSDI)** — 提出 chunked prefill：把长 prefill 切块、与 decode 混跑，消除 prefill 对 decode 的阻塞，在不牺牲吞吐的前提下压住 TPOT 尾延迟。模块 02/04 的关键技术。
- **Kwon et al. 2023（同上 vLLM 论文的调度章节）** — continuous batching 在 PagedAttention 之上的具体调度：等待/运行/换出三队列、显存压力下的抢占。模块 02 调度器模拟的现实蓝本。
- **Patel, Choukse, Zhang, … 2024, _Splitwise: Efficient Generative LLM Inference Using Phase Splitting_** — 与 DistServe 并行的 PD 分离工作，强调按阶段拆分到不同硬件，给出真实负载下的配比与功耗分析。

## 投机解码 · Speculative Decoding
- ★ **Leviathan, Kalman & Matias 2023, _Fast Inference from Transformers via Speculative Decoding_ (ICML)** — 投机解码奠基作之一。给出 draft-then-verify 框架与<strong>可证明保分布</strong>的接受/拒绝规则，推导期望加速比 `(1−α^(γ+1))/(1−α)`。模块 03 接受采样与加速公式的来源，必读。
- ★ **Chen, Borgeaud, Irving, Lespiau, Sifre & Jumper 2023, _Accelerating Large Language Model Decoding with Speculative Sampling_ (DeepMind)** — 与 Leviathan 同期、独立提出投机采样，对无损性的证明与多 token 验证写得尤为清晰。两篇对照读能彻底吃透「为什么加速还不改分布」。模块 03 必读。
- ★ **Cai, Li, Geng, Peng, Lee, Chen & Dao 2024, _Medusa: Simple LLM Inference Acceleration with Multiple Decoding Heads_** — 不用单独 draft 模型，而给 target 加多个并行解码头 + 树形注意力验证，工程上极简且有效。模块 03 树形投机一节的代表方案。
- **Li, Wei, Zhang & Zhang 2024, _EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty_** — 在特征层（而非 token 层）做自回归草稿并重用 target 表示，把接受率推到新高度。理解「draft 越像 target，加速越大」的极致工程化。
- **Stern, Shazeer & Uszkoreit 2018, _Blockwise Parallel Decoding for Deep Autoregressive Models_** — 投机/并行解码的早期思想源头，先于大模型时代提出一次预测多个位置再验证。读它看清这一脉络的起点。
- **Miao, Oliaro, … & Jia 2024, _SpecInfer: Accelerating LLM Serving with Tree-based Speculative Inference and Verification_** — 系统化的树形投机：用多个小模型生成 token 树、一次验证整棵树，给出树构造与验证 mask 的工程细节。模块 03 tree-spec 练习的现实对应。

## 前缀复用与 PD 分离 · Prefix Reuse & Disaggregation
- ★ **Zheng, Yin, Xie, Sun, Huang, Yu, Cao, Kozyrakis, Stoica, Gonzalez, Barrett & Sheng 2024, _SGLang: Efficient Execution of Structured Language Model Programs_** — 提出 RadixAttention：用基数树自动、跨请求地复用 KV 前缀，无需手动声明；配合压缩状态机做约束解码。模块 04 radix 前缀缓存的源头，必读。
- ★ **Zhong, Liu, Chen, Hu, Zhu, Liu, Jin & Zhang 2024, _DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving_ (OSDI)** — 提出把 prefill 与 decode 分离到不同 GPU 各自优化，以 goodput（满足 SLO 的吞吐）为目标，给出资源配比与 KV 传输的分析。模块 04 PD 分离的源头，必读。
- **Qin, Cheng, … 2024, _Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving_** — 以 KV cache 为中心的分离式架构（Kimi 背后），把 KV 池化、分级存储与传输做成一等公民。读它看 PD 分离在超大规模生产中的样子。
- **Gim, Chen, … 2024, _Prompt Cache: Modular Attention Reuse for Low-Latency Inference_** — 把可复用的 prompt 模块（如 few-shot、文档）的 KV 预计算并跨请求复用，与 RadixAttention 互补的前缀复用视角。

## 量化与 FP8 · Quantization & FP8
- ★ **Micikevicius, Stosic, Burgess, … 2022, _FP8 Formats for Deep Learning_ (NVIDIA/Arm/Intel)** — FP8 的标准定义文档：E4M3 与 E5M2 的比特布局、表示范围、特殊值与使用约定。模块 05 fp8 cast/范围分析的权威依据，必读。
- ★ **Dettmers, Lewis, Belkada & Zettlemoyer 2022, _LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale_** — 揭示 LLM 激活里的<strong>离群值</strong>会摧毁朴素 INT8 量化，提出混合精度分解保护离群维度。模块 05 离群值一节的必读，解释「为什么量化 LLM 这么难」。
- **Lin, Tang, Tang, … & Han 2024, _AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration_** — 仅权重量化（W4A16）：按激活重要性保护关键权重通道，几乎无损地把权重压到 4 bit。理解 decode 带宽受限下「只量化权重也能提速」。
- **Frantar, Ashkboos, Hoefler & Alistarh 2023, _GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers_** — 高精度的训练后权重量化经典方法，逐层最小化量化误差。与 AWQ 对照看权重量化两条主流路线。
- **Hooper, Kim, … 2024, _KVQuant: Towards 10 Million Context Length LLM Inference with KV Cache Quantization_** — 专攻 KV cache 量化：per-channel/per-token scale、离群值处理，把 KV 压到极低比特以支持超长上下文。模块 05 KV 量化的现实对应。

## 性能模型与综述 · Performance Models & Surveys
- ★ **Pope, Douglas, Chowdhery, … 2022, _Efficiently Scaling Transformer Inference_ (Google)** — 把 LLM 推理的延迟/吞吐/成本拆成 prefill 与 decode 两阶段、用算术强度与并行策略分析，是建立「两阶段、各自瓶颈不同」世界观的奠基文献。强烈建议先读，贯穿全课。
- **Kim, Hooper, … 2023, _Full Stack Optimization of Transformer Inference: a Survey_** — 从算子到系统的推理优化全景综述，可作为本课各模块的索引地图。
- **Horace He 2022, _Making Deep Learning Go Brrrr From First Principles_（博客）** — 把瓶颈分成算力受限 / 访存受限 / 开销受限三类的世界观文章。理解为什么 decode 是访存受限、为什么量化与大 batch 有用，先读它。
- **Weng et al. / Lilian Weng, _Large Transformer Model Inference Optimization_（博客）** — 对 KV cache、量化、投机解码、并行的清晰科普整理，适合作为各模块的轻量复习。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境聚焦机制而非吞吐**：全课用 numpy 在 CPU 上把每个机制做成<strong>逻辑正确的模拟器 + 账本</strong>——显存用整数块账本、调度用事件循环、注意力用小矩阵、量化用 numpy 的浮点位操作。我们不追求真实的 tokens/s，而追求把<strong>不变量</strong>钉死：分页 KV 零浪费且能正确读回、连续批处理吞吐严格高于静态、投机采样输出分布<strong>逐位等于</strong>目标模型、radix 命中等于暴力前缀匹配、量化误差随 scale 与离群值的变化符合理论。每个机制都与朴素参考<strong>对拍</strong>、用 `assert` 兜底。
- **可迁移性**：你在 numpy 里验证过的块表寻址、CoW 引用计数、迭代级调度循环、接受/拒绝采样、radix 插入匹配、fp8 cast 与 scale 选择，可几乎一对一对回 vLLM / SGLang / TensorRT-LLM 的对应模块。本课刻意让数据结构与控制流贴近真实引擎。
- **课程衔接**：上游接 C01（Transformer/注意力数学）与 C36（GPU 内核 / FlashAttention，本课的 attention kernel 即出自那里）；平行参考 C08（训练系统 / 并行）；下游可接长上下文与 Agent 服务等专题。把本课的服务机制与 C36 的 kernel 实现合起来看，才是现代推理引擎的全貌。
