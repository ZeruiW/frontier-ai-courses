# 参考清单 · References（前沿机制可解释性 SAE / features / circuits / steering / safety）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy + 合成数据模拟的每个机制，都能在下列文献里找到真实大模型上的对应实现与权衡。本课是 **C06 基础 interp 的前沿深化**：probe / activation patching / logit lens 的入门在 C06，这里聚焦 SAE / 特征 / 电路前沿 / steering / model diffing。

## 叠加：为什么需要 SAE · Superposition
- ★ **Elhage et al. 2022, _Toy Models of Superposition_ (Anthropic)** — 本课的思想起点。在玩具模型里证明：当特征数 > 维度且特征稀疏时，网络会把特征**非正交叠加**进神经元，产生多义性，并给出特征几何（正多胞形、相变）的完整刻画。读它就懂了「为什么不能读单个神经元、为什么需要字典学习」。模块 01/02 全程在复现它的设定。
- ★ **Olah et al. 2020, _Zoom In: An Introduction to Circuits_ (Distill)** — circuits 议程的纲领：主张神经网络由可单独理解的特征与电路组成（features / circuits / universality 三假设）。建立本课世界观，模块 03 的总纲。
- **Gurnee et al. 2023, _Finding Neurons in a Haystack_** — 用稀疏探针研究特征如何分布在神经元上，量化叠加与多义性。把叠加从玩具模型带到真实 LLM 的桥梁。
- **Park et al. 2023, _The Linear Representation Hypothesis and the Geometry of LLMs_** — 把 LRH 拆成 subspace/measurement/intervention 三层并形式化，指出欧氏内积未必是对的度量（需因果内积）。理解「特征 = 方向」到底成立到什么程度。

## 稀疏自编码器：三代演进 · Sparse Autoencoders
- ★ **Bricken et al. 2023, _Towards Monosemanticity: Decomposing Language Models with Dictionary Learning_ (Anthropic)** — 第一代 SAE（L1）的奠基作。证明在一层 MLP 激活上训过完备 + L1 SAE，能从叠加里拆出大量**单义**特征，并引入 dead-feature **resampling**、特征解释与因果验证流程。SAE interp 的「圣经」，必读。模块 01 的 L1 SAE 与 resampling 直接来自它。
- ★ **Templeton et al. 2024, _Scaling Monosemanticity: Extracting Interpretable Features from Claude 3 Sonnet_ (Anthropic)** — 把 SAE 规模化到前沿生产模型，提取数千万特征（含「金门大桥」「代码漏洞」「谄媚」等），并演示特征 steering（Golden Gate Claude）。证明 SAE 不只在玩具上有效。模块 01/04 的现实锚点。
- ★ **Cunningham et al. 2023, _Sparse Autoencoders Find Highly Interpretable Features in Language Models_** — 与 Bricken 同期独立工作，在多模型多层上系统验证 SAE 特征比神经元更可解释、更能用于电路分析。SAE 普适性的关键外部证据。
- ★ **Rajamanoharan et al. 2024, _Improving Dictionary Learning with Gated SAEs_ 与 _Jumping Ahead: Improving Reconstruction Fidelity with JumpReLU SAEs_ (DeepMind)** — 诊断 L1 的**激活收缩**问题并给出解药：Gated SAE 解耦「是否激活/激活多大」，JumpReLU 用可学习阈值 + 直接惩罚 L0。在重建-稀疏帕累托前沿上显著超越 L1。模块 01 三代 SAE 对比的依据。
- ★ **Gao et al. 2024, _Scaling and Evaluating Sparse Autoencoders_ (OpenAI)** — 提出 **TopK SAE**（直接钉死 L0、免调 λ、无收缩）与 auxk 辅助损失治 dead，并给出 SAE 的 scaling laws 与评测协议（下游 loss recovered、探针可分性等）。模块 01 的 TopK 实现与「怎么评 SAE」来自它。
- **Conerly et al. 2024, _Update on how we train SAEs_ (Anthropic, Transformer Circuits)** — 训练 SAE 的工程细节合集（损失、初始化、归一化、resampling 实践）。从零训 SAE 时的实操手册。
- **Bussmann et al. 2024, _BatchTopK SAEs_** 与 **Karvonen et al. 2024, _SAEBench_** — TopK 的批级改进，以及 SAE 的标准化评测基准（含 feature absorption、可解释性、稀疏探针等多维指标）。比较 SAE 优劣的现代工具。

## 电路与归因 · Circuits & Attribution
- ★ **Wang et al. 2022, _Interpretability in the Wild: a Circuit for Indirect Object Identification (IOI)_** — 端到端逆向工程出 GPT-2 small 完成 IOI 任务的完整电路（name mover / S-inhibition / induction 等 head）。activation/path patching 方法论的范本，模块 03 的现实对应。
- ★ **Nanda 2023, _Attribution Patching: Activation Patching at Industrial Scale_ (blog)** — 提出用一阶梯度近似 activation patching，一次前后向估计所有组件的因果效应，把 O(N) 次前向压成 O(1)。规模化电路发现的关键技巧，模块 03 worked 的核心，必读。
- ★ **Syed et al. 2023, _Attribution Patching Outperforms Automated Circuit Discovery_ / Kramár et al. 2024, _AtP\*_ (DeepMind)** — 把 attribution patching 系统化（边归因 EAP）并修正其一阶近似失效处（AtP\*：处理注意力 softmax 等）。模块 03 节点/边归因与近似误差讨论的依据。
- ★ **Marks et al. 2024, _Sparse Feature Circuits: Discovering and Editing Interpretable Causal Graphs in Language Models_** — 把电路的节点从 head/neuron 换成 **SAE 特征**，用归因连边得到稀疏、可解释的特征级因果图，并演示用它消除伪相关（如 SHIFT 去除分类器对性别的依赖）。连接 SAE 与电路两条线，模块 03/05 的桥梁。
- **Conmy et al. 2023, _Automated Circuit Discovery (ACDC)_** — 自动化电路发现算法，把 patching 包成搜索。理解「电路发现」如何从手工走向自动。
- **Meng et al. 2022, _Locating and Editing Factual Associations in GPT (ROME)_** — 用 causal tracing 定位事实存储位置并直接编辑。早期因果定位 + 模型编辑的代表，理解 patching 的因果思想。

## Steering 与表示工程 · Steering & RepE
- ★ **Turner et al. 2023, _Activation Addition: Steering Language Models Without Optimization (ActAdd)_** — 最简 steering：把概念方向按强度加进激活即可定向改变行为，无需训练。模块 04 的起点。
- ★ **Rimsky et al. 2023, _Steering Llama 2 via Contrastive Activation Addition (CAA)_** — 用对比样本的均值差作 steering 向量，稳健且可在多行为上扫强度。模块 04 把它当 SAE 特征 steering 的强基线对比。
- ★ **Arditi et al. 2024, _Refusal in LLMs Is Mediated by a Single Direction_** — 发现拒绝行为由**单个方向**中介：消融它即绕过拒绝、加强它即过度拒绝。单方向因果中介复杂行为的标志性结果，模块 04/05 的关键案例。
- **Zou et al. 2023, _Representation Engineering: A Top-Down Approach to AI Transparency (RepE)_** — 系统化「读方向 + 控方向」用于监控与控制（诚实、情绪、危害等）。steering 与白盒监控的方法论母体。
- **Templeton et al. 2024（同上）的 feature steering 部分 / Anthropic _Golden Gate Claude_** — SAE 特征 steering 的旗舰演示与其副作用观察。模块 04 SAE-steering 与 off-target 度量的现实参照。

## 可解释性用于安全 · Interpretability for Safety
- ★ **Hubinger et al. 2024, _Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training_ (Anthropic)** — 构造带后门的模型并证明标准安全训练难以根除。模块 05 后门检测的问题设定来源。
- ★ **MacDiarmid et al. 2024, _Simple Probes Can Catch Sleeper Agents_ (Anthropic)** — 用极简对比 prompt 的方向，在后门触发**之前**高 AUC 报警。白盒监控可行性的直接证据，模块 05 worked 的现实对应。
- ★ **Lindsey et al. 2024, _Sparse Crosscoders for Cross-Layer Features and Model Diffing_ (Anthropic)** — 提出 crosscoder：一个 SAE 同时重建多模型/多层激活，使特征跨模型对齐，从而**直接比较**两个模型的特征（model diffing），定位微调引入的新特征/后门。模块 05 model diffing 的核心，必读。
- **Marks et al. 2025 / Anthropic, _Auditing Language Models for Hidden Objectives_** — 用 interp（含 SAE 特征）做模型审计、找隐藏目标的端到端演练。把 interp 接到「审计」这一安全用例。
- **Greenblatt et al. 2023, _AI Control_** — 不假设理解模型也要安全部署的协议；白盒监控（interp）可作为其中一类监控器。理解 interp 在安全栈里的位置与「相关性监控」的定位。
- **Bereska & Gavves 2024, _Mechanistic Interpretability for AI Safety: A Review_** — 把 mech interp 与 AI safety 的连接做成综述，含局限与开放问题。建立全局图景的好入口。

## 综述、批评与工具 · Surveys, Critiques & Tooling
- ★ **Sharkey et al. 2025, _Open Problems in Mechanistic Interpretability_** — 系统梳理 mech interp 的开放问题（SAE 的根本局限、评测、可扩展性、与安全的对接）。模块 05 前沿与开放问题一节的依据，强烈建议通读。
- **Olah et al. 2024, _Circuits Updates_ / Transformer Circuits Thread** — Anthropic 持续更新的 interp 进展合集（SAE 训练、crosscoder、attribution 等）。追前沿的主阵地。
- **Till 2024, _Do SAEs find true features?_ / Various, _SAE 的批评_** — 对 SAE 是否真的恢复「模型在用的」特征的质疑（feature absorption/splitting、与下游因果脱节）。保持批判，避免 interp 幻觉。
- ★ **Nanda, _TransformerLens_ / Joseph Bloom et al., _SAELens_ / _Neuronpedia_** — 机制 interp 的标准工具链：TransformerLens 读写激活与 patching、SAELens 训练/加载 SAE、Neuronpedia 浏览特征。本课从零实现的 numpy 版，下一步即用它们在真模型上复现。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课是前沿深化，不是入门**：linear probe、activation patching、logit lens、表示几何等**基础 interp** 在 **C06** 已系统讲过；本课直接从叠加出发，聚焦 **SAE / 特征 / 电路前沿 / steering / model diffing / safety**。若对 probe / patching 不熟，建议先过 C06。
- ⚠️ **本环境玩具规模、CPU**：全课用**合成叠加数据**与**纯 numpy toy transformer** 模拟上述机制——SAE 在「我们植入的真特征」上训练并对拍恢复率；attribution patching 与真 activation patching 对拍近似误差；steering / 后门检测在玩具激活上演示。结论可对照 ground truth 验证，看懂机制后再上真模型（TransformerLens / SAELens / Neuronpedia）。
- **课程衔接**：上游接 C01（Transformer 内部结构）、C06（基础 interp 工具）；下游接 C05（AI safety / control / 白盒监控）、C12（负责任 AI / 审计）。本课是把「读懂内部」从基础工具推进到前沿字典学习与电路、并接到安全用例的一环。
