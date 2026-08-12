# 参考清单 · References（推理模型 RL：o1/o3/R1 前沿）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 玩具化模拟的每个机制，都能在下列文献里找到真实大模型上的对应实现、规模与权衡。年份与作者按公开发布信息标注。

## 推理模型与训练范式 · Reasoning Models & Paradigm
- ★ **DeepSeek-AI 2025, _DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning_** — 本课的中心文献。提出 R1-Zero（纯 RL、仅结果奖励、无 SFT 冷启动即涌现长 CoT 与反思）与 R1（加冷启动+多阶段 RL 提升可读性）。把「推理能力可以被激励而非教出」讲到可复现，模块 01/02 全程对标它。读它理解：规则奖励、GRPO、format+正确性奖励、为什么长 CoT 会自发变长。
- ★ **OpenAI 2024, _Learning to Reason with LLMs（o1 发布博客）_** — 推理模型范式的开山公告。提出「用 RL 训练模型在回答前进行长时间思考」「准确率随训练计算与<strong>测试时计算</strong>双双 scaling」两条核心主张。虽无技术细节，但定义了整个领域的问题，是模块 00/05 的世界观来源。
- **OpenAI 2024, _OpenAI o1 System Card_（Jaech et al.）** — o1 的系统卡，给出能力评测、安全分析与「思维链可作为对齐/监控抓手」的讨论。理解推理模型在真实部署中的能力边界与风险。
- **DeepSeek-AI 2025, _DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models_（Shao et al.）** — ★ 同时是 GRPO 的原始出处（见下）与「数学推理数据+RL」配方的完整案例。读它看 GRPO 在真实数学任务上的端到端使用。
- **Anthropic / Google 等的推理模型（如 Claude 的 extended thinking、Gemini 2.x thinking）公开说明** — 横向对照不同实验室对「测试时思考」的工程选择，理解这是全行业的范式转移而非单点技巧。

## 策略优化算法 · Policy Optimization
- ★ **Schulman et al. 2017, _Proximal Policy Optimization Algorithms (PPO)_** — 现代 RL 与 RLHF 的主力算法。clipped surrogate 用一个简单的 min/clip 把「信赖域」近似出来，稳、好调。模块 02 的对照基准，理解 GRPO 必须先懂 PPO 的 ratio clip 从何而来。
- ★ **Shao et al. 2024, _DeepSeekMath（GRPO）_** — GRPO 的提出处。核心洞察：对同一问题采一组答案、用<strong>组内归一化回报</strong>当优势，<strong>去掉 critic</strong>。省显存、少调参、训得稳，是 R1 的训练主力。模块 02 逐行复现它的优势与 loss。
- **Williams 1992, _Simple Statistical Gradient-Following Algorithms (REINFORCE)_** — 策略梯度的奠基。理解 $\nabla J=\mathbb{E}[R\nabla\log\pi]$、基线为何不引入偏差、方差从哪来——这是 PPO/GRPO 一切技巧的根。模块 01/02 的数学地基。
- **Sutton & Barto, _Reinforcement Learning: An Introduction_（2nd ed.）** — RL 教科书。策略梯度、优势、基线、credit assignment 的权威阐述。本课所有 RL 术语遇到分歧以它为准；建议精读策略梯度章。
- **Yu et al. 2025, _DAPO: An Open-Source LLM Reinforcement Learning System at Scale_** — GRPO 的工程化改进合集：clip-higher（非对称裁剪鼓励探索）、token-level loss（避免长序列被稀释）、动态采样、去 KL 等。读它理解把 GRPO 跑到大规模时会撞到哪些坑、怎么补，是模块 02 「前沿」一节的延伸。
- **Schulman et al. 2015, _High-Dimensional Continuous Control Using Generalized Advantage Estimation (GAE)_** — PPO 配套的优势估计法。理解 GRPO「用组采样替代 GAE/critic」到底替代了什么。

## 过程奖励与验证 · Process Reward & Verification
- ★ **Lightman et al. 2023, _Let's Verify Step by Step_（OpenAI, PRM800K）** — 过程监督的奠基实证。在 MATH 上证明<strong>过程奖励模型（PRM）显著优于结果奖励模型（ORM）</strong>，并开源 80 万步级人工标注 PRM800K。模块 03 的核心，理解「为什么给每一步打分值得」。
- ★ **Wang et al. 2024, _Math-Shepherd: Verify and Reinforce LLMs Step-by-step without Human Annotations_** — 解决 PRM 标注贵的痛点：用<strong>蒙特卡洛 rollout 的答对比例</strong>自动生成步级软标签，无需人工。模块 03 的 MC 标注 worked 即复现它，是 PRM 能规模化的关键。
- ★ **Cobbe et al. 2021, _Training Verifiers to Solve Math Word Problems (GSM8K)_** — 同时贡献了 GSM8K 数据集与「训一个 verifier 做 best-of-N 重排，远胜单纯放大生成」的范式。模块 03/04 的共同源头，也是本课真实数据胶囊的数据来源。
- **Uesato et al. 2022, _Solving Math Word Problems with Process- and Outcome-based Feedback_（DeepMind）** — 与 Lightman 并列的过程 vs 结果监督早期对比。给出另一条独立证据线，读它平衡单一来源的结论。
- **Zhang et al. 2024 / 2025 关于 PRM 陷阱（如 _The Lessons of Developing PRMs in Mathematical Reasoning_）** — 总结 PRM 实践中的坑：MC 标签噪声、数据偏置、聚合选择、评测泄漏。模块 03 「Goodhart/倒 U」一节的现实依据。
- **Gao et al. 2023, _Scaling Laws for Reward Model Overoptimization_** — 量化「优化代理奖励过头，真实表现先升后降」的倒 U 规律与 KL 的关系。本课讲奖励黑客/过度优化时的定量支撑。

## 测试时计算与搜索 · Test-Time Compute & Search
- ★ **Snell et al. 2024, _Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters_** — TTC scaling 的代表作。系统比较串行（revision）与并行（BoN/搜索）TTC、按难度做 compute-optimal 分配，并论证<strong>小模型+更多测试时计算可在等算力下胜过更大模型</strong>。模块 04/05 的主线文献。
- ★ **Brown et al. 2024, _Large Language Monkeys: Scaling Inference Compute with Repeated Sampling_** — 揭示 pass@k 随样本数近似幂律上升（覆盖率惊人），但前提是有 verifier 能从大量样本里挑出对的。模块 04 BoN/pass@k 的核心，也点出「采样易、挑选难」的瓶颈。
- ★ **Wang et al. 2022, _Self-Consistency Improves Chain of Thought Reasoning in Language Models_** — 多数投票（self-consistency）的提出。无需 verifier、仅对最终答案取众数即大幅提升，是最易部署的 TTC。模块 04 投票方法的源头。
- **Wu et al. 2024, _Inference Scaling Laws / An Empirical Analysis of Compute-Optimal Inference for Problem-Solving_** — 对推理时计算分配（模型大小 × 采样数 × 搜索策略）的 compute-optimal 经验律分析。模块 05 帕累托/分配的定量来源之一。
- **Chen et al. 2021, _Evaluating Large Language Models Trained on Code (Codex)_** — 给出<strong>无偏 pass@k 估计量</strong> $1-\binom{n-c}{k}/\binom{n}{k}$ 的出处（附录）。模块 04 练习直接实现它；理解为什么 $1-(1-\hat p)^k$ 在小样本下有偏。
- **Yao et al. 2023, _Tree of Thoughts: Deliberate Problem Solving with LLMs_** — 把推理组织成可搜索的树（BFS/DFS + 价值评估）。模块 04 verifier-guided 搜索（beam/MCTS）的代表性方法。
- **Lightman/OpenAI 与后续的 _weighted best-of-N / PRM-reranking_ 实践** — best-of-N 用 PRM 聚合（min/prod）打分重排、加权投票的具体做法。模块 04 加权投票与聚合练习的现实对应。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课不训练真模型、不用 GPU**：全程用 numpy 在 CPU 上<strong>玩具化模拟</strong>——策略是 softmax 参数表、环境是可自动判分的算术题/GridWorld、verifier 是带可控噪声的打分函数、TTC 是对采样数/搜索宽度的预算分配。每个算法都与<strong>解析公式或朴素实现对拍</strong>（策略梯度数值梯度对拍解析梯度、GRPO 优势对拍组归一化定义、pass@k 估计对拍组合数、online 投票对拍批量统计），保证你掌握的是<strong>正确的算法结构</strong>。
- **可迁移性**：你在 numpy 里验证过的 GRPO 优势/loss、PRM MC 标注、BoN/投票/pass@k 估计、TTC 分配逻辑，可几乎一对一映射到 `trl` 的 `GRPOTrainer`、`verl` 的训练循环、或自建推理服务的采样-打分-聚合栈。本课刻意让函数签名贴近这些框架。
- **课程衔接**：上游接 RL 基础（策略梯度、PPO）与后训练/RLHF（C02 类）；横向接评测（pass@k、TTC 曲线）；下游接推理服务（C24，BoN/投票/搜索的工程化与 KV-cache 复用）与长上下文（C25，长 CoT 让超长生成成为常态）。
