# 参考清单 · References（VLA 与感知接口）

> 分主题列出。**★ = 必读**（读完这些你能覆盖本课 80% 的内容与绝大多数面试提问）。
> 每条注明**它解决了什么问题**，以及要重点看哪一节——VLA 领域论文极多且更新极快，
> 但每篇真正需要精读的通常只有 1–2 节。
>
> 与相邻课程的分工：**C00** 讲 VLM 本身（视觉编码器 / 连接器 / 指令微调）；
> **C55** 讲 TSR 与自动驾驶感知（本课的上游）；**C26** 讲 agent 与 prompt 方法论；
> **C16/C28** 讲扩散与生成模型原理；**C41** 讲模仿学习与分布漂移；
> **C60** 讲量化与车端部署；**C61** 讲面试组织。
> **本课聚焦「感知输出如何进入 VLA、动作如何出来、以及怎么证明它能用」这一段。**
>
> ⚠️ **本领域半年就会换一批 SOTA。** 下面的清单按「解决了什么问题」组织而不是按新旧，
> 因为**问题的结构比具体模型稳定得多**。读的时候请把注意力放在论文的动机与取舍上，
> 而不是它的排行榜名次。

---

## 一 · VLM 基础（本课的前置，详见 C00）· Vision-Language Foundations

- ★ **Radford et al. 2021, _Learning Transferable Visual Models From Natural Language Supervision (CLIP)_** —
  解决「视觉模型只能认预定义类别」的问题，用对比学习把图像和文本压进同一空间。
  **本课需要的是它的一个副产品：零样本识别能力的来源，以及它对小目标与细粒度差异的先天弱势**
  ——CLIP 类编码器对「限速 60 vs 限速 80」这种细粒度差异并不敏感，这直接解释了
  为什么 VLA 不能替代专用 TSR 检测器。读 §2 与 §3.1。
- ★ **Liu et al. 2023, _Visual Instruction Tuning (LLaVA)_** —
  解决「怎么用少量数据把视觉能力接到 LLM 上」：一个线性投影 + 指令微调。
  **它定义了 VLA 躯干的标准形态**，OpenVLA 等都是它的变体。读 §3 的两阶段训练。
- ★ **Alayrac et al. 2022, _Flamingo: a Visual Language Model for Few-Shot Learning_** —
  解决「如何在不破坏 LLM 的前提下注入视觉」：**门控 cross-attention 层 + Perceiver Resampler**。
  **本课模块 03「特征级融合」一节的直接技术来源**——把感知特征通过 cross-attention 注入
  正是 Flamingo 的做法。读 §2.1 与 §2.2。
- **Li et al. 2023, _BLIP-2_** — Q-Former 作为连接器：用少量可学习 query 从视觉特征里「问」出信息。
  **它和 BEV query、DETR 的 object query 是同一个思想的三次出现**，值得对照理解。
- **Zhai et al. 2023, _Sigmoid Loss for Language Image Pre-Training (SigLIP)_** —
  把 CLIP 的 softmax 对比损失换成 sigmoid，训练更稳、小 batch 也能用。
  **当前多数 VLM 的默认视觉编码器**，知道它是什么即可。
- **Bai et al. 2023+, _Qwen-VL_ / Beyer et al. 2024, _PaliGemma_** —
  开源 VLM 的两条常用骨架，**动态分辨率与 token 预算的处理值得看**：
  这正是「远处小标志能不能被编码进去」的决定因素。

---

## 二 · 机器人 VLA：范式的起点 · Robot VLA

- ★ **Brohan et al. 2022, _RT-1: Robotics Transformer for Real-World Control at Scale_** —
  解决「机器人策略如何吃下大规模多任务数据」：把动作离散化成 token，用 Transformer 统一建模。
  **动作 token 化的起点**，读 §4 的动作表示（每维 256 个 bin）。
- ★ **Brohan et al. 2023, _RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control_** —
  **本课模块 01 的主文献，也是 VLA 这个词的来源。** 三个必读点：
  ① **把动作 token 映射到词表中最少用的 token 上**——这个看似取巧的决定，
  使得动作输出可以完全复用 LM 头与预训练权重；
  ② **co-fine-tuning**（动作数据与原始视觉-语言数据混训）——论文证明只用动作数据微调
  会灾难性遗忘语义能力，**这是全篇最重要的消融**；
  ③ **涌现能力的实验**（对未见过物体与抽象指令的泛化）——这是 VLA 相对传统策略网络的唯一质变。
- ★ **Kim et al. 2024, _OpenVLA: An Open-Source Vision-Language-Action Model_** —
  解决「VLA 全是闭源、无法复现」的问题。7B 参数、双视觉编码器（SigLIP + DINOv2）、Llama 2 骨架。
  **它是本课概念的最佳代码对照物**：想搞清楚动作 token 到底怎么进出，读它的
  `prismatic/vla/action_tokenizer.py` 比读任何论文都快。也读它关于 LoRA 微调与量化推理的讨论。
- ★ **Black et al. 2024, _π0: A Vision-Language-Action Flow Model for General Robot Control_** —
  解决「离散动作 token 在高频灵巧控制上精度不够、token 数也吃不消」的问题：
  在 VLM 骨架上接一个**流匹配动作专家**，直接输出 50 Hz 的连续动作块。
  **模块 02 的关键对照**：它证明动作头可以不是 LM 头，但也因此需要额外设计来保住语义泛化。
- **Open X-Embodiment Collaboration 2023, _Open X-Embodiment: Robotic Learning Datasets and RT-X Models_** —
  解决「机器人数据太少且不通用」：把 22 种机体的数据统一成一个格式训练。
  **它对本课的价值是那套统一的数据 schema**——跨形态的动作与观测该怎么定义，是接口设计的好参考。
- **Octo Model Team 2024, _Octo: An Open-Source Generalist Robot Policy_** —
  轻量的开源通才策略，**扩散动作头 + 可插拔的观测/动作接口**。
  它的模块化设计（新传感器、新动作空间可以后接）值得接口设计者一读。
- **Zitkovich et al. / Google DeepMind, _RT-Trajectory_ 与后续工作** —
  用轨迹草图作为条件，是「语言之外的另一种指令接口」，
  对理解「指令不一定要是自然语言」很有帮助。

---

## 三 · 动作表示与策略头 · Action Representation

- ★ **Chi et al. 2023, _Diffusion Policy: Visuomotor Policy Learning via Action Diffusion_** —
  **模块 02 的主文献之一。** 解决回归策略在多模态动作分布下的模式平均问题。
  **必读它对多模态失效的论证与 action horizon 的消融**：
  为什么一次预测一段（chunk）比逐步预测更稳，以及 receding horizon 的执行方式。
- ★ **Zhao et al. 2023, _Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware (ACT)_** —
  **action chunking 这个术语与 temporal ensembling 的出处**。
  解决「逐步预测导致误差累积与抖动」的问题。读 §3.2 与它对 chunk 长度 k 的消融——
  **k 是延迟与反应性的权衡**，这条结论在自驾里同样成立。
- ★ **Lipman et al. 2023, _Flow Matching for Generative Modeling_** —
  流匹配的原始论文，解决扩散模型采样步数多、路径弯曲的问题：
  直接回归一个把噪声推到数据的速度场。**本课只需要它的第 3 节（条件流匹配的训练目标）
  与「路径更直 → 步数更少」这个结论**；生成模型本身的原理见 C16/C28。
- **Liu et al. 2023, _Rectified Flow_** — 与流匹配同源，用「拉直路径」的视角解释为什么能少步采样。
  两篇读一篇即可。
- **Song et al. 2023, _Consistency Models_ / Frans et al. 2024, _One Step Diffusion via Shortcut Models_** —
  解决「去噪步数直接乘进延迟」的问题：把多步蒸馏成 1–4 步。
  **这是扩散策略能否上车的关键技术**，延迟预算紧的系统必须了解。
- **Shafiullah et al. 2022, _Behavior Transformers (BeT)_ / Lee et al. 2024, _VQ-BeT_** —
  另一条处理多模态的路线：用聚类/VQ 把动作离散成「模式 + 残差」。
  **它是离散 token 与连续回归之间的中间形态**，token 数比均匀分箱少得多，值得知道。
- **Janner et al. 2022, _Planning with Diffusion for Flexible Behavior Synthesis_** —
  把规划本身当作生成问题。**它提供了「用采样代替搜索」的视角**，
  对理解扩散策略为什么天然支持加约束（通过引导采样）很有用。
- **Bishop 1994, _Mixture Density Networks_** — 处理多模态回归的经典方案，比扩散早了近 30 年。
  **面试里被问「除了扩散还能怎么处理多模态」时，MDN 是一个显示知识深度的答案。**

---

## 四 · 端到端自动驾驶 · End-to-End Driving

- ★ **Hu et al. 2023 (CVPR Best Paper), _Planning-oriented Autonomous Driving (UniAD)_** —
  **端到端自驾的里程碑。** 解决「模块化的接口丢信息、误差级联」的问题，
  但**关键设计是保留所有中间任务**（检测、跟踪、建图、运动预测、占据）并让它们通过 query 串起来。
  **必读 §3 关于「为什么不做纯粹的黑箱端到端」的论证**——这段话是本课接口设计哲学的直接来源。
- ★ **Jiang et al. 2023, _VAD: Vectorized Scene Representation for Efficient Autonomous Driving_** —
  解决 UniAD 太慢的问题：用**矢量化**场景表示（而非稠密栅格）大幅提速。
  **它给出的「用结构化稀疏表示替代稠密表示」正是模块 03 三种融合层次里「中间表示级」的实例。**
- **Chitta et al. 2022, _TransFuser: Imitation with Transformer-Based Sensor Fusion_** —
  图像与激光雷达的注意力融合，CARLA 上的长期强基线。
  **多模态融合怎么做的经典参考**，读它的融合位置消融。
- **Hu et al. 2022, _ST-P3_ / Chen et al. 2024, _End-to-End Autonomous Driving: Challenges and Frontiers_（综述）** —
  后者是**入门这个方向最省时间的一篇**，把 imitation / RL / 输入表示 / 输出表示 / 评测的
  全部分支画成了一张图。建议先读综述再挑论文。
- **Li et al. 2022, _BEVFormer_** — BEV query + 时序自注意力，**BEV 表示的标准做法之一**。
  本课模块 03 讲「BEV query 作为共享表示」时用它作技术锚点。
- **Tian et al. 2024, _Occ3D / 各类 occupancy 网络_** — 占据表示的现状。
  本课只需要知道它补的是「异形障碍与未知类别」这块短板，以及它**没有实例概念**这个局限。

---

## 五 · 自动驾驶中的语言与 VLA · Language & VLA for Driving

- ★ **Tian et al. 2024, _DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models_** —
  **本课模块 04「快慢双系统」一节的主文献。** 解决「大模型太慢、传统模块不懂长尾语义」的矛盾：
  VLM 做场景描述 → 场景分析 → 分层规划，与传统端到端模块并行组成 DriveVLM-Dual。
  **必读它对延迟的讨论**——这是少数几篇认真算延迟账的自驾 VLA 论文。
- ★ **Hwang et al. 2024 (Waymo), _EMMA: End-to-End Multimodal Model for Autonomous Driving_** —
  解决「如何最大化复用多模态大模型」：把感知输出、路由信息、自车状态、乃至输出轨迹
  **全部表达成文本**，交给一个 Gemini 模型统一处理。
  **本课模块 03 的关键对照物**：它是「符号/文本级融合」的极致形态，
  论文本身也诚实地讨论了代价——token 消耗、3D 精度、以及无法处理长序列多帧。
  **面试里能同时说出 EMMA 的做法与它的三个代价，是很强的信号。**
- ★ **Wayve, _LINGO-1 / LINGO-2_（技术博客与报告）** —
  解决「端到端系统无法解释自己」的问题：让模型在驾驶的同时输出自然语言解释，
  LINGO-2 进一步让语言**反过来影响驾驶行为**（真正的指令跟随）。
  **这是「可解释输出」与「指令跟随」两个概念最直观的展示**，也要配合本课的提醒读：
  模型说出的理由是事后生成的文本，与内部计算未必因果一致。
- ★ **Sima et al. 2024, _DriveLM: Driving with Graph Visual Question Answering_** —
  解决「怎么评测驾驶场景的语义理解」：把感知-预测-规划组织成图结构的 VQA 任务。
  **它是目前把「TSR 语义 → 决策」这条链路做成可评测任务的最好尝试**，
  本课模块 05 的场景化评测设计参考了它。
- **Xu et al. 2023, _DriveGPT4_ / Mao et al. 2023, _GPT-Driver_** —
  早期把 LLM 直接当规划器的尝试（把状态与检测结果文本化，让 LLM 输出轨迹）。
  **它们的价值在于暴露问题**：数值精度差、延迟高、无法保证可行性——
  正好对应本课模块 03/04 要解决的三件事。
- **Choudhary et al. 2023, _Talk2BEV_** — 把 BEV 表示与语言对齐，可以用语言查询 BEV 场景。
  **「中间表示级融合 + 语言接口」的具体实例。**
- **Wang et al. 2024, _OmniDrive_ / Jiang et al. 2024, _Senna_** —
  3D 感知与语言推理结合、以及「大模型出决策 + 小模型出轨迹」的分工。
  **后者的分工方式与本课模块 02 的分层控制思想一致**，可作为对照。
- **Kim et al. 2018, _Textual Explanations for Self-Driving Vehicles (BDD-X)_** —
  这个方向最早的工作之一，**提出了「解释必须与控制信号对齐」这个至今未解决的问题**。
  读它能让你对「可解释输出」保持恰当的怀疑。

---

## 六 · 开环评测的失效：必须知道的批判 · The Open-Loop Critique

> 这一组是本课**最有面试价值**的部分。能准确复述这两篇的结论，
> 意味着你能判断一个自驾方案的实验是否可信——这是资深度的直接信号。

- ★ **Zhai et al. 2023, _Rethinking the Open-Loop Evaluation of End-to-End Autonomous Driving in nuScenes (AD-MLP)_** —
  **必读，而且要读透。** 它做了一件极简的事：构造一个**只吃自车历史状态、完全不看任何图像**
  的 MLP，在 nuScenes 开环评测上得到了与当时 SOTA 相当甚至更好的 L2 与碰撞率。
  **结论：开环 L2 主要度量的是「能否从自车运动学外推」，而不是「能否理解场景」。**
  这直接质疑了一大批论文的实验结论。
- ★ **Li et al. 2024 (CVPR), _Is Ego Status All You Need for Open-Loop End-to-End Autonomous Driving? (BEV-Planner)_** —
  **与上一篇互补，论证更系统。** 它指出：① 自车状态一旦进入模型就会主导预测；
  ② nuScenes 的场景分布高度偏向直行，使得「保持当前状态」成为强基线；
  ③ 现有碰撞率指标的计算方式本身有缺陷。
  **并给出了改进的评测建议**。读完这两篇，你会对任何只报开环 L2 的论文保持警惕。
- ★ **Dauner et al. 2024 (NeurIPS), _NAVSIM: Data-Driven Non-Reactive Autonomous Vehicle Simulation and Benchmarking_** —
  解决「开环不可信、闭环太贵」的两难：提出**非反应式仿真 + PDM score**，
  在短时域内做有限的闭环推演，与真实闭环表现的相关性显著高于开环 L2。
  **这是当前最务实的折中方案，也是本课模块 05 推荐的评测起点。**
- **Dauner et al. 2023, _Parting with Misconceptions about Learning-based Vehicle Motion Planning (PDM)_** —
  在 nuPlan 上证明：**一个调好的基于规则的规划器在闭环上打败了所有学习方法**，
  而学习方法在开环上更强。**「开环强 ≠ 闭环强」最有力的实证**。
  这篇同时也是「不要低估规则基线」的最佳论据。
- **Codevilla et al. 2018, _On Offline Evaluation of Vision-based Driving Models_** —
  **这个批判的最早版本**（比上面几篇早了五年）：离线指标与在线驾驶表现的相关性很弱。
  引用它能显示你知道这个问题不是新发现。
- **Ross et al. 2011, _A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning (DAgger)_** —
  **误差累积的理论根源**：模仿学习的误差随时域呈 T² 增长，除非用在线数据修正。
  本课模块 05 的误差累积模拟就是它的数值版本。原理详见 C41。

---

## 七 · 数据集、仿真与评测基础设施 · Benchmarks

- ★ **Caesar et al. 2020, _nuScenes: A Multimodal Dataset for Autonomous Driving_** —
  自驾感知与规划的通用数据集。**本课需要知道的是它的局限**：
  场景以直行为主、时长 20 秒、开环评测协议不统一——这正是第六组批判的对象。
- ★ **Caesar et al. 2021, _nuPlan: A Closed-Loop ML-based Planning Benchmark_** —
  **第一个大规模闭环规划基准**，同时提供开环、非反应式闭环、反应式闭环三种评测模式。
  **它的三种模式恰好构成本课模块 05 的评测阶梯**，值得认真读评测协议部分。
- ★ **Dosovitskiy et al. 2017, _CARLA: An Open Urban Driving Simulator_ 与 CARLA Leaderboard 2.0** —
  闭环评测的事实标准。**重点看 Leaderboard 的 driving score 构成**
  （route completion × infraction penalty），以及 infraction 里
  **闯红灯、闯停车标志、超速各自的惩罚系数**——这是「规则违反率」最标准的工程化定义。
- ★ **Jia et al. 2024, _Bench2Drive: Towards Multi-Ability Benchmarking of Closed-Loop End-to-End Autonomous Driving_** —
  解决「CARLA 上各方法评测协议不一致、无法比较」的问题，
  并把能力拆成多个维度（合流、超车、让行、紧急刹车…）分别评。
  **分能力评测正是本课主张的「场景化测试」。**
- **Sun et al. 2020, _Scalability in Perception for Autonomous Driving: Waymo Open Dataset_** —
  规模与标注质量都更高，**其 Motion / End-to-End 子集适合做规划评测**。
- **Zhu et al. 2016 / Houben et al. 2013, _TT100K / GTSDB_** — TSR 的数据基础（详见 C55）。
  **本课需要它们的地方是：模块 03 的 schema 字段要能覆盖这些数据集的标注粒度**，
  否则接口在真实数据上会缺项。
- **Qian et al. 2024, _NuScenes-QA_ / Marcu et al. 2023, _LingoQA_** —
  驾驶场景的视觉问答基准，**是度量「场景语义理解」而非「轨迹拟合」的少数工具**。
  评测 TSR 语义是否真的被理解时可以借鉴它们的题型设计。

---

## 八 · 约束、安全兜底与可靠性 · Constraints & Safety

- ★ **Shalev-Shwartz et al. 2017, _On a Formal Model of Safe and Scalable Self-Driving Cars (RSS)_** —
  **本课模块 04 安全兜底层的理论来源。** 它把「安全」形式化成可验证的最小距离与责任规则，
  提供了一套**不依赖学习模型的独立判据**。
  **必读它对「安全不能靠统计验证」的论证**：要用路测证明比人类安全，需要的里程数在工程上不可行——
  这就是为什么必须有形式化的兜底层。
- ★ **Alshiekh et al. 2018, _Safe Reinforcement Learning via Shielding_** —
  「学习系统 + 形式化护盾」这个组合范式的清晰表述。
  **它给出的架构（模型提议 → 护盾过滤 → 执行）与本课模块 04 的兜底层完全同构。**
- **Ames et al. 2019, _Control Barrier Functions: Theory and Applications_** —
  用连续时间的不变集给出安全保证，是可行性校验的数学工具。
  **本课只需要它的直觉**：存在一个可以持续维持的安全集合，控制量必须让系统不离开它。
- **ISO 21448 (SOTIF) 与 ISO 26262（标准文本 / 公开摘要）** —
  **SOTIF 处理的正是「功能没坏但表现不足」的失效**（感知漏检、模型泛化不足），
  这是 VLA 类系统的主要风险类别。
  知道这两个标准分别管什么，在量产团队的面试里是明显的加分项。
- **Willard et al. 2023, _Efficient Guided Generation for LLMs_（Outlines）与 JSON-mode / grammar-constrained decoding 的实现** —
  解决「结构化输出格式不可靠」的问题：用有限状态机在解码时约束词表。
  **模块 03/04 的工程标配**——但要记住它只保证语法合法，不保证语义正确。
- **Guo et al. 2017, _On Calibration of Modern Neural Networks_** —
  **置信度标定的起点**：证明现代深度网络系统性过度自信，并给出温度缩放这个极简解法。
  **本课模块 03 的可靠性图与 ECE 实现直接来自这篇**，必读 §2 与 §4。
- **Lakshminarayanan et al. 2017, _Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles_** —
  不确定性估计的强基线。**本课需要的是它的结论**：集成给出的不确定性比单模型 softmax 可靠得多，
  这是「置信度该怎么算」这个问题的实用答案之一。
- **Kendall & Gal 2017, _What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?_** —
  **偶然不确定性（数据噪声）与认知不确定性（模型无知）的区分**。
  这个区分在接口设计上有直接后果：前者靠更好的传感器解决，后者靠更多数据解决，
  **下游对两者的应对策略也不同**。

---

## 九 · 幻觉、鲁棒性与错误传播 · Hallucination & Robustness

- ★ **Li et al. 2023, _Evaluating Object Hallucination in Large Vision-Language Models (POPE)_** —
  **幻觉度量的标准方法**：用「图中有没有 X」的二元问题探测，并按 random / popular / adversarial
  三种负样本采样策略分别测。**本课模块 05 的幻觉率实现借鉴了它的采样设计**——
  关键洞察是：**问「有没有一块限速牌」时，负样本要挑那些在该场景下高频共现的标志，才测得出真幻觉。**
- **Rohrbach et al. 2018, _Object Hallucination in Image Captioning (CHAIR)_** —
  幻觉度量的更早版本。**它指出幻觉与语言先验强相关**：模型倾向于说出该场景下常见的物体。
  对 TSR 的含义很直接：**在高速场景里，模型会倾向于「补出」一块限速牌。**
- **Huang et al. 2023, _A Survey on Hallucination in Large Language Models_** —
  把幻觉按成因分类（数据、训练、推理）。**本课需要的是它对「推理期幻觉」的部分**：
  上下文冲突与自我一致性压力如何制造幻觉——这正是错误合理化的机制。
- **Sharma et al. 2023, _Towards Understanding Sycophancy in Language Models_** —
  模型会迎合输入中的前提与暗示。**接口设计的直接后果**：
  prompt 里写「前方有一块限速牌，请问限速多少」会显著提高幻觉率，
  而写「以下检测结果置信度为 0.42，可能不可靠」则会触发保守——**措辞是可设计的**。
- **Hendrycks & Dietterich 2019, _Benchmarking Neural Network Robustness to Common Corruptions (ImageNet-C)_** —
  **输入退化对模型的影响是可以系统性度量的**。
  本课模块 03 的「感知错误注入实验」在方法上与它同源。
- **Liu et al. 2023, _Lost in the Middle: How Language Models Use Long Contexts_** —
  **长上下文中间位置的信息容易被忽略**。
  对接口设计的直接后果：**最关键的感知字段应该放在 prompt 的开头或结尾，不要埋在中间**。
  这是一个可以立刻用上的工程结论。

---

## 十 · 蒸馏、量化与上车 · Distillation & Deployment

- ★ **Hinton et al. 2015, _Distilling the Knowledge in a Neural Network_** —
  蒸馏的起点。**本课需要的是「软标签携带了类间关系信息」这个核心洞察**，
  以及它对「蒸什么」这个问题的第一个答案。云端-车端路线的所有变体都从这里出发。
- ★ **Beyer et al. 2022, _Knowledge Distillation: A Good Teacher is Patient and Consistent_** —
  解决「蒸馏为什么常常不 work」：**必须让师生看到完全相同的输入视图，并训练足够久**。
  **这条在车端蒸馏里尤其关键**——师生的预处理不一致会让蒸馏效果大打折扣（对齐方法见 C60）。
- **Xiao et al. 2023, _SmoothQuant_ / Lin et al. 2023, _AWQ_ / Frantar et al. 2023, _GPTQ_** —
  大模型量化的三条主流路线。**本课只需要它们的误差量级作为输入**，
  方法本身在 C27/C60 详讲。**要特别注意长链推理中的误差放大**：
  单步 1% 的偏差在 10 步推理后不是 10% 而可能更糟。
- **Leviathan et al. 2023, _Fast Inference from Transformers via Speculative Decoding_** —
  用小模型起草、大模型验证来降低延迟。**它对 VLA 的意义在于：
  输出是结构化且高度可预测时（比如固定 schema 的动作 token），起草命中率极高**，加速比可观。
- **Wang et al. 2024, _A Survey on Efficient Inference for Large Language Models_** —
  推理优化的全景图，用来定位各种技术的适用条件。**当作索引读，不要通读。**
- **Tesla / XPENG / 各家 AI Day 与技术发布的公开材料** —
  **量产系统的架构信息几乎只能从这里获得。**
  读的时候请记住本课 README 的提醒：**把「公开报道的路线」与「你自己的推断」分开说**，
  面试里把推断说成事实是最容易翻车的地方。

---

## 十一 · 代码与工程资料 · Code & Engineering

- ★ **`openvla/openvla`** — **本课概念的最佳代码对照物。**
  重点读 `action_tokenizer.py`（动作如何分箱与映射到词表）、
  数据处理里的动作归一化（分位数裁剪，避免离群值撑爆分箱范围），
  以及推理脚本里 prompt 的实际拼接方式——**这三处合起来就是模块 01/02 的全部工程实质**。
- ★ **`Physical-Intelligence/openpi`** — π0 系列的开源实现。
  **重点看流匹配动作专家的接口**：它如何与 VLM 骨架相连、动作块如何输出与执行。
- ★ **`OpenDriveLab/UniAD` 与 `hustvl/VAD`** —
  端到端自驾的两份参考实现。**读它们的 query 在模块之间如何传递**，
  这是「中间表示级接口」最具体的样子。
- **`huggingface/lerobot`** — 机器人策略的统一脚手架（数据格式、训练、评测）。
  **它的数据集 schema 设计值得所有做接口的人看一眼。**
- **`real-stanford/diffusion_policy`** — Diffusion Policy 官方实现，
  含 action horizon / observation horizon 的完整配置，**是理解 chunking 参数的最快路径**。
- **`carla-simulator/leaderboard` 与 `motional/nuplan-devkit`** —
  两套闭环评测的官方实现。**重点读 infraction 的判定代码**：
  「什么算闯停车标志」「超速多久算违规」这些判据的具体实现，
  比任何论文描述都精确，也是设计自己的规则违反率指标时最好的起点。
- **各仓库 issues 里关于「动作输出不平滑」「chunk 边界跳变」「量化后行为变化」的讨论** —
  **这些是最真实的工程知识来源**，比教程更接近实际。
  按关键词 `action chunk`、`temporal ensemble`、`quantization`、`latency` 检索。
