# 参考清单 · References（LLM 生产部署与云原生）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 本课用纯 Python 模拟复现的每个机制，都能在下列文献/文档里找到真实生产系统上的对应实现与权衡。
> 与相邻课程的分工：**C24** 讲推理引擎内部（PagedAttention、continuous batching），**C37** 讲模型生命周期（实验追踪、漂移、CI/CD 门禁），
> **C39** 讲分布式训练工程，**本课**讲三者之间那段——打包、契约、编排、发布、成本。

## 容器与镜像 · Containers & Images
- ★ **Open Container Initiative, _Image Format Specification_** — 镜像格式的权威定义：manifest、layer digest、config。读它你会发现「镜像」这个概念比工具文档里讲的简单得多——就是一棵 Merkle DAG。模块 01 的分层与内容寻址实现直接对标它。
- ★ **Docker, _Best practices for writing Dockerfiles_ + BuildKit 文档** — 层缓存、`.dockerignore`、多阶段构建、`--mount=type=cache` 的官方说明。模块 01 的「越少变的放越前」与「装了再删必须同层」两条铁律的一手来源。
- ★ **NVIDIA, _NVIDIA Container Toolkit 文档_** — 解释了为什么容器隔离不了 GPU driver、镜像里只能装 CUDA runtime、以及版本兼容矩阵。上线失败最常见原因之一（`CUDA driver version is insufficient`）的根治参考。
- **Merkel 2014, _Docker: Lightweight Linux Containers for Consistent Development and Deployment_** — 容器技术的经典综述，把 namespace/cgroup/联合文件系统三者的关系讲清楚。适合建立「容器不是虚拟化」的准确心智模型。
- **Harter et al. 2016, _Slacker: Fast Distribution with Lazy Docker Containers_ (FAST'16)** — 实测发现容器启动时间中拉镜像占 76%，而实际只有 6.4% 的数据被读取。这是所有懒加载工作（eStargz/SOCI/Nydus）的动机来源，也是模块 01 冷启动分解的实证依据。
- **containerd/stargz-snapshotter 与 AWS SOCI 文档** — 镜像懒加载的两个主流实现。读它理解「按需拉取」在 registry 兼容性与索引构建上的实际代价。

## 服务契约与推理服务 · Serving Contract
- ★ **vLLM, `vllm/entrypoints/openai/` 源码** — 最好的 OpenAI 兼容层参考实现。`protocol.py` 是完整的请求/响应 schema，`api_server.py` 展示了流式、健康端点、指标暴露的工程做法。想自建服务就照着它抄。
- ★ **Kwon et al. 2023, _Efficient Memory Management for Large Language Model Serving with PagedAttention_ (SOSP'23)** — vLLM 的论文。本课只用它一个结论：KV 缓存决定了引擎能并发多少序列（`B_max`），而这个数就是模块 02 准入控制的上限。引擎内部细节见 C24。
- ★ **Agrawal et al. 2024, _Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve_ (OSDI'24)** — 系统地论证了 TTFT 与 TPOT 的冲突（prefill 会拖长正在 decode 的请求），并给出 chunked prefill 的解法。模块 02 「延迟指标必须拆开」的理论支撑。
- **Zhong et al. 2024, _DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving_ (OSDI'24)** — prefill/decode 分池的代表作。读它理解为什么大规模服务正在往「两个实例池 + KV 传输」的架构走，以及这对编排层提出了什么新要求。
- **WHATWG HTML Living Standard, _Server-Sent Events_ 一节** — SSE 的规范定义（`data:` 字段、空行分隔、重连语义）。模块 02 的编解码器按它实现；生产三大坑（缓冲/超时/断连）则是规范之外的工程经验。
- **Gross, Shortle, Thompson & Harris, _Fundamentals of Queueing Theory_, 第 2–3 章** — Erlang-C 的严格推导与 M/M/c 的性质。模块 02 的容量模型以它为准。重点看「为什么 W_q 是 ρ 的双曲函数」和「并发数增大带来的规模经济」。
- **Nygard, _Release It!_ (2nd ed.)** — 稳定性模式的经典：断路器、舱壁、超时、快速失败、背压。模块 02 的四道护栏几乎全部出自这本书的模式语言，强烈建议通读。

## Kubernetes 与编排 · Kubernetes
- ★ **Kubernetes 官方文档：_Pod Lifecycle_ / _Configure Liveness, Readiness and Startup Probes_** — 本模块最重要的一手来源，写得远好于大多数二手教程。探针的精确时序语义（startupProbe 成功前另两个不生效）、终止流程（preStop → SIGTERM → grace period → SIGKILL）都在这里。
- ★ **Kubernetes 官方文档：_Resource Management for Pods and Containers_ + _Pod Quality of Service Classes_** — requests/limits 的准确语义、QoS 分级与驱逐顺序、扩展资源（GPU）为何必须 requests==limits。模块 03 资源模型一节的依据。
- ★ **Kubernetes 官方文档：_Assigning Pods to Nodes_ / _Pod Topology Spread Constraints_ / _Scheduling Framework_** — 亲和性、拓扑分布、调度器的 Filter/Score 插件结构。模块 03 的调度器实现照着这个两阶段结构写。
- ★ **Verma et al. 2015, _Large-scale cluster management at Google with Borg_ (EuroSys'15)** — K8s 的思想源头。优先级与抢占、资源回收、作业分类（prod vs batch）、利用率数据都在这里。读它你会明白 K8s 的很多设计不是凭空来的。
- **Burns, Grant, Oppenheimer, Brewer & Wilkes 2016, _Borg, Omega, and Kubernetes_ (ACM Queue)** — 三代集群管理系统的设计复盘，尤其是「为什么选择声明式与控制循环」。理解 K8s 哲学的最短路径。
- **Coffman, Garey & Johnson, _Approximation Algorithms for Bin Packing: A Survey_** — 装箱问题的理论边界与 FFD 等启发式的竞争比。模块 03 「大 Pod 优先」建议的理论依据。
- **Kubernetes SIG-Scheduling, _Kueue_ 与 **CNCF, _Volcano_** 文档** — 给 K8s 补上批作业排队、配额与 gang scheduling。跑训练/评测作业时必读，否则集群利用率会很难看。
- **Kubernetes Gateway API Inference Extension（社区提案与实现）** — 「比 Deployment 更懂 LLM」的编排抽象尝试：模型版本、KV 缓存亲和路由、prefill/decode 分池。当前变化最快的一层，值得持续跟踪。

## 发布、可靠性与统计判据 · Delivery & Reliability
- ★ **Beyer et al., _Site Reliability Engineering_（Google SRE Book），第 3–5 章与第 27 章** — 错误预算、多窗口多燃烧率告警的原始配方、渐进发布。模块 00 的三笔账与模块 04 的自动回滚判据全部出自这里。第 5 章的 burn-rate 表格建议直接照抄。
- ★ **Argo Rollouts 文档，_Analysis_ / _Canary Strategy_** — 工业界金丝雀判据的实际形态：AnalysisTemplate、指标查询、失败限制、自动回滚。读它看「理论上的假设检验」如何变成可运行的 CRD。
- ★ **Flagger 文档，_Canary Analysis_** — 与 Argo Rollouts 并列的实现，对渐进放量与指标门禁的抽象略有不同，两者对读能看清设计空间。
- ★ **Kubernetes 官方文档：_Horizontal Pod Autoscaling_** — HPA 的精确算法（含容差带）、`behavior` 字段的稳定窗口与速率策略语义。模块 04 的控制律仿真按它实现。
- **Howard, Ramdas, McAuliffe & Sekhon 2021, _Time-uniform, nonparametric, nonasymptotic confidence sequences_ (Annals of Statistics)** — always-valid 推断的现代基础。它解决的正是金丝雀的 peeking 问题：在任意停止时刻都保持覆盖率。想把序贯方法做进发布流水线，从这里入门。
- **Wald 1945, _Sequential Tests of Statistical Hypotheses_** — SPRT 的原始论文。模块 04 的序贯检验实现直接来自它，简洁且易于工程化。
- **Johari, Koomen, Pekelis & Walsh 2017, _Peeking at A/B Tests: Why it matters, and what to do about it_ (KDD'17)** — 用工业界数据展示 peeking 造成的假阳性膨胀，并给出 always-valid p 值的实用方案。本课模块 04 那个「A/A 测试假阳性 20%」的实验，就是它的复现。
- **KEDA 文档** — 事件驱动扩缩与 scale-to-zero。LLM 服务按队列深度扩缩的标准实现，比 prometheus-adapter 路线简单得多。
- **Humble & Farley, _Continuous Delivery_** — 部署流水线、可重复发布、回滚优先于修复等原则的系统论述。虽然写在 K8s 之前，但原则完全适用。

## 云平台、调度与成本 · Cloud, Scheduling & Cost
- ★ **AWS, _Amazon EC2 Spot Instances Best Practices_ / GCP, _Preemptible & Spot VMs_ 文档** — 中断通知的处理、实例池多样化、容量回退策略的官方指南。模块 05 的 spot 工程实践三件套出自这里。
- ★ **SchedMD, _Slurm Quick Start User Guide_ + _Slurm Scheduling Configuration Guide_（backfill 一节）** — Slurm 的一手文档，比任何二手教程都清楚。重点读 backfill 的调度逻辑，它解释了「`--time` 填得越准排队越短」这条最实用的经验。
- ★ **Moritz et al. 2018, _Ray: A Distributed Framework for Emerging AI Applications_ (OSDI'18)** + Ray Architecture Whitepaper — Ray 的设计与 task/actor 模型。理解「Python 原生分布式」这条路线与 K8s/Slurm 的世界观差异。
- ★ **Yang et al. 2023, _SkyPilot: An Intercloud Broker for Sky Computing_ (NSDI'23)** — 跨云选型、spot 容错、作业迁移的开源实现。**非常值得读源码**：它把本模块讲的成本模型、spot 中断处理、多云回退全部工程化了。
- **Patterson et al. 2021, _Carbon Emissions and Large Neural Network Training_** — 算力的碳账与影响因子（模型、硬件、数据中心、电网）。碳感知调度的量化基础。
- **FinOps Foundation, _FinOps Framework_（成本可见性 / 优化 / 治理三阶段）** — 把成本当工程一等公民管理的方法论。模块 05 的成本归因与单位经济分析的框架来源。
- **OpenCost / Kubecost 文档** — K8s 上按 namespace/label 的成本分摊实现。LLM 服务还要在应用层补 `model_version` + `tenant` 的 token 计数才能算准。
- **Amazon S3 / Google Cloud Storage 的一致性与性能文档** — 对象存储的读后写一致性、分片并发下载、请求计费模型。模块 05 「存字节便宜、搬字节贵」的定价依据。

## 跨课衔接 · Cross-course
- **C24 高效推理服务** — 本课模块 02 的 `μ`（单副本服务率）与 `B_max`（并发上限）从哪来，答案在那门课：PagedAttention、continuous batching、投机解码、FP8 服务。本课把它们当作已知参数。
- **C37 MLOps 与生产生命周期** — 实验追踪、数据/模型版本、评测门禁与 CI/CD、监控与漂移。本课的「发布」是那门课「门禁」的下游执行环节，两课合起来是完整的交付链。
- **C39 分布式训练工程** — 多节点通信、FSDP、3D 并行、checkpoint 与容错。本课模块 05 的 Slurm 与 gang scheduling 是它的运行底座；多节点推理的编排需求也源自那门课的并行策略。
- **C03 / C10 评测科学与测量** — 模块 04 金丝雀的「质量指标」判据（judge 胜率、非劣性检验、样本量规划）在那两门课有完整的统计基础。
- **C12 / C45 负责任 AI 与隐私** — 模块 05 数据合规一节（数据出境、日志留存、对话不进训练集）的展开在那两门课。
