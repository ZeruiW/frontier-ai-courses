# 术语词典 · Glossary（高效推理与服务）

> 按主题分组，每条 2–3 句释义。读 vLLM / SGLang / TensorRT-LLM 文档与 PagedAttention / Orca / 投机解码 / DistServe 等论文遇到生词回这里查；英文术语保留原文（社区与系统文档的通用语言）。本课用 numpy 在 CPU 上把这些机制做成「模拟器 + 账本」，但术语与真实推理引擎一一对应。

## 推理的两个阶段 · The Two Phases

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| prefill / prompt phase | 预填充 / 提示阶段 | 一次性并行处理整段输入 prompt、为每个 token 算出并写入 KV cache 的阶段。它一次喂入很多 token，矩阵乘大、算术强度高，通常是<strong>算力受限（compute-bound）</strong>。 |
| decode / generation phase | 解码 / 生成阶段 | 自回归地一次生成一个 token 的阶段：每步只算 1 个新 query，却要读取全部历史 KV。批量小、算术强度低，通常是<strong>带宽受限（memory-bound）</strong>，是 LLM 服务延迟的主体。 |
| autoregressive decoding | 自回归解码 | 逐 token 生成，第 t 步的输入依赖第 t-1 步的输出，因此天然串行、无法在序列维并行——这是 decode 慢、且催生投机解码的根本原因。 |
| TTFT (Time To First Token) | 首 token 延迟 | 从请求到达到吐出第一个 token 的时间，主要由 prefill 决定。交互式应用（聊天）对 TTFT 敏感。 |
| TPOT / ITL (Time Per Output Token / Inter-Token Latency) | 单 token 延迟 / token 间延迟 | 进入稳定生成后，平均每个输出 token 的耗时，主要由 decode 步的带宽决定。它决定了「打字机」的流畅度。 |
| goodput | 有效吞吐 | 在满足 SLO（如 TTFT/TPOT 上限）前提下系统实际交付的吞吐，区别于不管延迟的裸吞吐。DistServe 等系统优化的真正目标。 |
| SLO (Service Level Objective) | 服务级目标 | 对延迟的承诺，如 P99 TTFT < 1s、TPOT < 50ms。服务系统的所有调度与配比决策本质都在 SLO 约束下最大化吞吐。 |

## KV Cache 与显存 · KV Cache & Memory

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| KV cache | KV 缓存 | 缓存历史 token 的 Key、Value 张量，使每生成一个新 token 时无需重算整段历史的 K/V，只算当前 token 并追加。它把 decode 从 O(n²) 算力降到每步 O(n) 读取，代价是巨大的显存占用。 |
| KV cache size | KV 缓存大小 | 约等于 `2 × 层数 × KV头数 × head_dim × 序列长 × batch × 字节/元素`。系数 2 是 K 与 V。它随序列长与并发线性增长，常常比模型权重还大，是长上下文/高并发的首要显存瓶颈。 |
| internal fragmentation | 内部碎片 | 为一个请求预留了一整段连续显存（按最大长度），却只用了其中一部分，剩余被占用却闲置。传统按 max_len 预分配 KV 的主要浪费来源。 |
| external fragmentation | 外部碎片 | 空闲显存总量够，但被切成不连续的小块，放不下一个需要连续大块的新请求。连续分配方案的顽疾。 |
| memory fragmentation | 显存碎片化 | 内部 + 外部碎片的统称。PagedAttention 出现前，KV 的碎片浪费常使有效利用率低到 20–40%。 |
| block / page (KV block) | 块 / 页 | PagedAttention 把 KV cache 切成的固定大小单元（如每块存 16 个 token 的 K/V）。分配以块为粒度，逻辑上连续的 token 可落在物理上分散的块里。 |
| block size | 块大小 | 一个 KV block 容纳的 token 数（vLLM 默认 16）。块越小内部碎片越少但 block table 开销越大、kernel 访问越碎；是个权衡参数。 |
| block table | 块表 | 每个请求一张表，把它的逻辑块号映射到物理块号——完全类比操作系统页表。注意力 kernel 经它间接寻址，从而无需 KV 物理连续。 |
| paged KV cache | 分页 KV 缓存 | 用块 + 块表管理的 KV，使显存可像 OS 虚拟内存那样按需、非连续地分配，几乎消除外部碎片、把内部碎片限制在「最后一块」之内。 |
| KV utilization | KV 利用率 | 实际存了有效 token 的显存 ÷ 已分配显存。PagedAttention 把它从传统的 20–40% 提到 ~96%，等价于在同样显存下塞下数倍的并发。 |
| copy-on-write (CoW) | 写时复制 | 多个序列共享同一物理块（如相同前缀或并行采样的多个候选），直到某个序列要写入时才复制出私有块。让前缀/采样分支零拷贝共享 KV，大幅省显存。 |
| reference count | 引用计数 | 每个物理块被多少个序列共享的计数。共享时加一、释放时减一、减到零才真正回收；写入共享块（计数>1）时触发 CoW。 |
| prefix sharing | 前缀共享 | 多个请求若有相同的前缀（如同一 system prompt），它们的前缀 KV 完全相同，可共享同一批物理块，只为各自不同的后续部分分配新块。 |
| swapping / offloading | 换出 / 卸载 | 显存不足时把部分请求的 KV 块临时搬到 CPU 内存（或重算），腾出显存给高优先级请求，稍后再换回。vLLM 的抢占恢复手段之一。 |

## 批处理与调度 · Batching & Scheduling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| static / request-level batching | 静态 / 请求级批处理 | 凑齐一批请求一起跑，整批同步推进、必须等批内最长的请求生成完才能整体返回并接下一批。短请求被长请求拖住，GPU 大量空转。 |
| continuous / iteration-level batching | 连续 / 迭代级批处理 | 在每个生成<strong>迭代</strong>而非整个请求的粒度上调度：某序列生成完就立刻让出，新到达的请求立刻补进当前 batch。Orca 提出，是现代引擎吞吐翻倍的关键。 |
| in-flight batching | 在途批处理 | TensorRT-LLM 对 continuous batching 的称呼，含义相同：让不同进度的请求在同一个运行中的 batch 里共存。 |
| iteration / decode step | 迭代 / 解码步 | 引擎前向一次、为 batch 中每个活跃序列产出一个 token 的最小调度单元。连续批处理就是在这个粒度上增删序列。 |
| scheduler | 调度器 | 决定每个迭代里哪些请求进入 batch、谁被抢占、prefill 与 decode 如何混合的组件。它在 SLO、显存、吞吐之间做权衡，是服务引擎的大脑。 |
| waiting / running / swapped queue | 等待 / 运行 / 换出队列 | vLLM 调度器的三个请求队列：等待被调度的、正在 batch 里生成的、因显存压力被换出的。每迭代在三者间流转请求。 |
| preemption | 抢占 | 显存不够时，调度器暂停（换出或重算）某些正在运行的请求，把资源让给别的请求，稍后恢复。保证系统在过载时仍能推进而非死锁。 |
| chunked prefill | 分块预填充 | 把一个长 prompt 的 prefill 切成若干小块，分散到多个迭代里、与 decode 步混合执行，避免一次巨大的 prefill 阻塞所有正在生成的请求、推高它们的 TPOT。Sarathi-Serve 提出。 |
| prefill–decode interference | 预填充-解码干扰 | 在同一 GPU 上混跑 prefill（算力重）与 decode（带宽重）时，长 prefill 会卡住 decode、抬高 TPOT，反之亦然。chunked prefill 与 PD 分离都是为缓解它。 |
| batch size / running requests | 批大小 / 运行中请求数 | 当前迭代同时在生成的序列数。越大吞吐越高（更好地摊薄权重读取），但越受 KV 显存限制、且抬高单请求延迟。 |
| throughput | 吞吐 | 单位时间产出的 token 数（tokens/s）或完成的请求数。服务系统的核心效率指标，与延迟存在根本张力。 |

## 投机解码 · Speculative Decoding

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| speculative decoding | 投机解码 | 用一个小而快的 draft 模型一次猜出若干个未来 token，再用大的 target 模型<strong>并行</strong>验证这些猜测，一次前向就可能确认多个 token。在输出分布不变的前提下加速 decode。 |
| draft model | 草稿模型 | 投机解码里负责提出候选 token 的小模型（或大模型自身的轻量头）。它要足够快、且与 target 分布足够接近（接受率才高）。 |
| target model | 目标模型 | 投机解码里被加速的大模型，是输出质量的<strong>唯一</strong>裁判。它一次前向并行算出 draft 提议位置的全部概率用于验证。 |
| speculative sampling | 投机采样 | 验证 draft token 的接受/拒绝规则：以 `min(1, p_target/p_draft)` 接受，拒绝时从校正分布 `normalize(max(0, p_target − p_draft))` 重采样。可<strong>证明</strong>最终样本服从 target 分布，故无损。 |
| acceptance rate | 接受率 | target 接受 draft 提议的平均比例。接受率越高，每次验证确认的 token 越多、加速比越大。取决于 draft 与 target 分布的接近程度。 |
| speedup / expected tokens | 加速比 / 期望确认 token 数 | 一轮 draft-verify 平均确认的 token 数（含拒绝处由 target 补的那个）。理论上 = `(1 − α^(k+1)) / (1 − α)`，α 为接受率、k 为草稿长度。 |
| draft length / γ | 草稿长度 | 每轮 draft 一次提议的 token 数。太短则验证摊销不足，太长则后段接受率低、白算。是投机解码的关键超参。 |
| Medusa | —— | 给 target 模型加多个并行解码<strong>头</strong>，一次预测未来多个位置的候选，配合树形注意力验证，免去单独的 draft 模型。 |
| EAGLE | —— | 在<strong>特征</strong>（feature）层而非 token 层做自回归草稿，并重用 target 的表示，接受率显著高于普通小 draft 模型。 |
| tree attention / tree speculation | 树形注意力 / 树形投机 | 一次提议多条候选 token 路径组成一棵树，用一个精心设计的注意力 mask 在一次前向里并行验证所有路径，提升每步确认的期望 token 数。 |
| verification | 验证 | target 模型对 draft 提议序列做一次前向，得到每个位置的真实概率，再逐位置应用接受/拒绝规则。是投机解码保证无损的环节。 |
| lossless / distribution-preserving | 无损 / 保分布 | 投机解码的核心承诺：加速后输出的概率分布与直接用 target 自回归采样<strong>完全相同</strong>。本课会用 numpy 实验验证这一点。 |

## 前缀复用与分离 · Prefix Reuse & Disaggregation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| prefix cache | 前缀缓存 | 缓存已计算过的前缀（如公共 system prompt、few-shot 示例、多轮对话历史）的 KV，新请求若命中相同前缀就直接复用、跳过其 prefill，大幅降 TTFT。 |
| RadixAttention | —— | SGLang 提出：用一棵<strong>基数树（radix tree）</strong>自动管理所有请求的 KV，公共前缀对应树上共享的路径，实现跨请求、自动、细粒度的前缀复用，无需手动声明。 |
| radix tree / trie | 基数树 / 前缀树 | 把 token 序列按公共前缀压缩存储的树，每条根到节点的路径是一个被缓存前缀，边可携带多 token（radix 压缩）。RadixAttention 的数据结构核心。 |
| prefix hit rate | 前缀命中率 | 新请求的 prompt 中能在缓存里找到匹配前缀的 token 比例。命中率越高，越多 prefill 被省掉、TTFT 越低。 |
| LRU eviction | 最近最少使用淘汰 | 前缀缓存满时优先淘汰最久未被命中的前缀块。RadixAttention 在 radix 树叶子上做带引用计数的 LRU，保护正在被使用的前缀。 |
| PD disaggregation (prefill–decode disaggregation) | PD 分离 | 把 prefill 与 decode 放到<strong>不同</strong>的 GPU/实例上各自专门优化：prefill 实例追求高算力利用、decode 实例追求高带宽与大 batch，再把 KV 从前者传给后者。DistServe / Mooncake 的核心架构。 |
| KV transfer / KV migration | KV 传输 / 迁移 | PD 分离里把 prefill 算出的 KV cache 从 prefill 实例搬到 decode 实例（经 NVLink/RDMA）。其带宽与延迟是 PD 分离能否划算的关键约束。 |
| resource ratio / PD ratio | 资源配比 | prefill 实例数 ∶ decode 实例数。按负载（平均 prompt 长、生成长、到达率）与各自速率调到使 TTFT 与 TPOT 都达标且无瓶颈。 |
| disaggregated serving | 分离式服务 | 泛指把推理流水的不同阶段拆到不同硬件池独立扩缩容的架构，PD 分离是其最典型形态。 |

## 量化与数值 · Quantization & Numerics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| quantization | 量化 | 用更少比特表示张量（如 FP16→FP8/INT8/INT4），减小显存与带宽、提速访存受限的 decode，代价是引入量化误差。推理服务里 KV cache 与权重是主要量化对象。 |
| FP8 (E4M3 / E5M2) | 8 位浮点 | 8 比特浮点格式：E4M3（4 位指数 3 位尾数，精度高、范围小，多用于前向/权重/激活）与 E5M2（5 位指数 2 位尾数，范围大、精度低，多用于梯度）。把显存/带宽相对 FP16 减半。 |
| exponent / mantissa | 指数 / 尾数 | 浮点数 `(-1)^s × 2^(e−bias) × 1.m` 的两部分：指数决定<strong>动态范围</strong>（能表示多大/多小），尾数决定<strong>相对精度</strong>（有几位有效数字）。FP8 两种格式就是在二者间取舍。 |
| dynamic range | 动态范围 | 一种数值格式能表示的最大值与最小正规数之比。指数位越多动态范围越大，越不容易因离群值而溢出/下溢。 |
| INT8 quantization | INT8 量化 | 用 8 位整数 + 一个缩放因子表示浮点：`q = round(x / scale)`，`x ≈ q × scale`。等间隔量化，对分布均匀的数据有效，对有离群值的数据需配合更细的 scale。 |
| scale / zero-point | 缩放因子 / 零点 | 把浮点映射到整数的两个参数：scale 是步长，zero-point 是表示 0 的整数偏移。对称量化 zero-point=0，非对称量化用它对齐非零均值。 |
| per-tensor / per-channel / per-token scale | 张量级 / 通道级 / token级 缩放 | scale 的粒度：整个张量共用一个（最省、最粗）、每个通道一个、每个 token 一个（最细、最准）。粒度越细越能抵抗离群值，但元数据与 kernel 开销越大。 |
| outlier | 离群值 | 激活/KV 中数值远大于其余元素的少数维度。它把 per-tensor scale 拉大，使绝大多数正常值被压到极少数量化档位，精度崩塌——是 LLM 量化最难啃的骨头。 |
| KV cache quantization | KV 缓存量化 | 把 KV cache 存成 FP8/INT8 而非 FP16，直接把 decode 的主要带宽与显存开销减半，常用 per-token 或 per-channel scale 控制误差。 |
| quantization error | 量化误差 | 量化再反量化后与原值的差 `x − dequant(quant(x))`。对均匀量化，误差幅度 ∝ scale；选 scale 就是在「溢出截断」与「步长过粗」之间权衡。 |
| calibration | 校准 | 用一小批代表性数据统计激活/KV 的数值范围，据此选定 scale（如取分位数而非最大值以抵抗离群值）。静态量化的前置步骤。 |
| weight-only quantization | 仅权重量化 | 只量化权重、激活仍用高精度（如 AWQ/GPTQ 的 W4A16）。在带宽受限的 decode 上，仅靠减小权重读取就能提速，且精度损失可控。 |

## 引擎与生态 · Engines & Ecosystem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| vLLM | —— | 开源 LLM 推理引擎，以 PagedAttention + continuous batching 著称，是高吞吐服务的事实标准之一。本课模块 01/02 的机制直接源出于它。 |
| SGLang | —— | 面向复杂 LLM 程序（多轮、并行、结构化）的服务框架，核心是 RadixAttention 自动前缀复用与高效的约束解码。本课模块 04 的机制来自它。 |
| TensorRT-LLM | —— | NVIDIA 的高性能推理库，提供 in-flight batching、融合 kernel、FP8/INT8 量化等，把本课机制在 NVIDIA 硬件上做到极致。 |
| Orca | —— | 提出 iteration-level（continuous）batching 的系统论文，现代连续批处理的源头。模块 02 的理论基础。 |
| DistServe / Mooncake | —— | 把 prefill 与 decode 分离到不同资源池的代表性系统，用 goodput 而非裸吞吐为目标。模块 04 PD 分离的来源。 |
| PagedAttention | —— | vLLM 的核心算法（Kwon et al. 2023）：借鉴 OS 虚拟内存，用块 + 块表管理 KV，几乎消除碎片。本课模块 01 全程在复现它。 |
| FlashAttention / FlashDecoding | —— | IO 感知的注意力 kernel；FlashDecoding 是其 decode 阶段变体，沿 KV 长度切分并行以喂饱小 batch 的 decode。推理引擎都依赖它，详见 C36。 |
| continuous batching scheduler | 连续批处理调度器 | 实现迭代级调度的具体组件（如 vLLM 的 `Scheduler`）。模块 02 会从零写一个可运行的简化版。 |
| serving metrics (P50/P99) | 服务指标分位数 | 用中位数（P50）与尾延迟（P99）刻画延迟分布。服务 SLO 通常约束尾延迟，因为它决定最差用户体验。 |
