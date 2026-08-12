# 参考清单 · References（深度强化学习与决策）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 在 toy 环境从零实现的每个机制，都能在下列文献里找到真实大规模实现与权衡。基础（MDP/贝尔曼/策略梯度/GAE）见 C13 的参考；这里聚焦深度 RL、控制、离线、模型与前沿。

## 教科书与综述 · Textbooks & Surveys
- ★ **Sutton & Barto, _Reinforcement Learning: An Introduction_ (2nd ed., 2018)** — RL 圣经。表格部分是 C13 的底座；本课相关的是函数逼近章（第 9–11 章，含 deadly triad 的经典论述）与 Dyna/规划章（第 8 章）。任何 RL 概念有歧义都以它为准。
- ★ **Achiam, _Spinning Up in Deep RL_ (OpenAI)** — 最好的深度 RL 入门工程文档。把 VPG/TRPO/PPO/DDPG/TD3/SAC 的推导、伪代码、实现要点讲得极清楚，并配可跑代码。本课模块 02 的 PPO/SAC 推导与它高度一致，强烈建议对照精读。
- **Levine et al. 2020, _Offline Reinforcement Learning: Tutorial, Review, and Perspectives_** — 离线 RL 的权威综述。把分布偏移、外推误差、各类约束方法系统梳理。模块 03 的理论框架来源，读它建立离线 RL 的全景。
- **Moerland et al. 2023, _Model-based Reinforcement Learning: A Survey_** — 基于模型 RL 的系统综述：模型学习、规划、Dyna、不确定性、世界模型一网打尽。模块 04 的地图。
- **Henderson et al. 2018, _Deep RL that Matters_** — 揭示深度 RL 的可复现性危机：随机种子、实现细节、超参对结果的巨大影响。读它理解为什么本课强调固定 seed + 稳健阈值，以及为什么 RL 结果要谨慎解读。

## 值函数逼近与 DQN · Value-Based Deep RL
- ★ **Mnih et al. 2015, _Human-level control through deep reinforcement learning_ (DQN, Nature)** — 深度 RL 的开山之作。用 experience replay + target network 让 Q-learning 在神经网络上稳定，单一架构通关 49 款 Atari。模块 01 全程复现它的两大稳定化技巧，必读。
- ★ **van Hasselt, Guez & Silver 2016, _Deep Reinforcement Learning with Double Q-learning_** — 指出并量化 DQN 的过估计偏差，提出 Double DQN：用在线网选动作、目标网评估值，几乎零成本地削过估计、提升性能。模块 01 的核心练习之一。
- **Wang et al. 2016, _Dueling Network Architectures for Deep RL_** — 提出把 Q 拆成 $V(s)+A(s,a)$ 两支的 dueling 架构，在动作影响小的状态下更高效学 $V$。模块 01 讲解与练习覆盖。
- **Schaul et al. 2016, _Prioritized Experience Replay_** — 按 TD 误差给样本分配采样优先级、用重要性权重纠偏，更高效地利用 replay。模块 01 的延伸阅读。
- **Hessel et al. 2018, _Rainbow: Combining Improvements in Deep RL_** — 把 Double/Dueling/PER/多步/分布式/Noisy 六项改进集成，证明它们大体正交可叠加。读它了解 DQN 家族的全貌与各组件贡献。
- **Bellemare, Dabney & Munos 2017, _A Distributional Perspective on RL (C51)_** — 不学 Q 的期望而学其完整分布。开启 distributional RL 一脉，Rainbow 的组件之一，是值方法的重要扩展方向。

## 策略优化 · Policy Optimization
- ★ **Schulman et al. 2017, _Proximal Policy Optimization Algorithms_ (PPO)** — 当今最常用的策略优化算法。用 clipped surrogate 一阶近似信赖域，好实现、稳健、广泛用于连续控制与 RLHF。模块 02 从零实现它，必读。
- ★ **Schulman et al. 2015, _Trust Region Policy Optimization_ (TRPO)** — PPO 的理论前身。用 KL 信赖域约束保证单调改进，给出策略改进的严格下界。读它理解 PPO 的 clip 到底在近似什么。
- ★ **Schulman et al. 2016, _High-Dimensional Continuous Control Using Generalized Advantage Estimation_ (GAE)** — GAE 原始论文（C13 已引入，本课 PPO 复用）。用 $\lambda$ 在偏差与方差间插值优势估计，是现代策略梯度的标配组件。
- **Williams 1992, _Simple statistical gradient-following algorithms (REINFORCE)_** — 策略梯度的奠基（C13 详讲）。本课作为 PPO 的出发点回顾，理解从 REINFORCE 到信赖域的演化脉络。
- **Engstrom et al. 2020, _Implementation Matters in Deep Policy Gradients_** — 实证拆解 PPO 的性能到底来自 clip 还是来自一堆「代码层面」的细节（优势归一化、学习率退火、梯度裁剪等）。做 PPO 工程前必读，避免归因错误。
- **Mnih et al. 2016, _Asynchronous Methods for Deep RL (A3C/A2C)_** — 并行 actor-critic，引入熵正则与 n-step 优势。是 PPO 的近亲，模块 02 的背景。

## 连续控制与最大熵 · Continuous Control & Max-Entropy
- ★ **Haarnoja et al. 2018, _Soft Actor-Critic_ (SAC)** — 离策略 + 最大熵的连续控制主力算法。双 Q 削过估计、随机策略 + 重参数化、自动温度调节。采样高效、稳健，模块 02 的核心。必读。
- **Haarnoja et al. 2018, _Soft Actor-Critic Algorithms and Applications_** — SAC 的扩展版，给出自动温度调节（约束最大熵）的推导与更多实验。配合上一篇读懂温度 $\alpha$ 怎么自学。
- **Lillicrap et al. 2015, _Continuous control with deep RL_ (DDPG)** — 把 DQN 思路搬到连续动作：确定性 actor + critic + 目标网络。SAC/TD3 的前身，理解确定性策略梯度的起点。
- **Fujimoto et al. 2018, _Addressing Function Approximation Error in Actor-Critic (TD3)_** — 用双 Q（取 min）、目标策略平滑、延迟策略更新修 DDPG 的过估计与脆弱。SAC 双 Q 思路的近亲，模块 02 提及。

## 离线强化学习 · Offline RL
- ★ **Kumar et al. 2020, _Conservative Q-Learning for Offline RL_ (CQL)** — 在 TD 损失上加保守正则，主动压低 OOD 动作的 Q、学到真实值的下界，从根上杜绝追逐高估的 OOD 动作。模块 03 的核心算法之一，必读。
- ★ **Kostrikov et al. 2021, _Offline RL with Implicit Q-Learning_ (IQL)** — 用 expectile 回归学值、完全不查询 OOD 动作的 Q，再用优势加权回归抽策略。简单、稳健、强基线。模块 03 的另一核心，必读。
- **Fujimoto et al. 2019, _Off-Policy Deep RL without Exploration (BCQ)_** — 最早系统指出离线 RL 的外推误差问题，提出用生成模型约束动作在数据支撑内。离线 RL 的奠基之一。
- **Fujimoto & Gu 2021, _A Minimalist Approach to Offline RL (TD3+BC)_** — 在 TD3 上只加一个 BC 正则项就达到强离线性能。说明「别离行为策略太远」这一条原则的威力，极简而有效。
- **Fu et al. 2020, _D4RL: Datasets for Deep Data-Driven RL_** — 离线 RL 的标准基准。理解论文里离线分数的来源与数据质量分层（random/medium/expert/混合）。
- **Chen et al. 2021, _Decision Transformer_** — 也属离线/序列建模（见下），离线设置下的强基线。

## 基于模型与世界模型 · Model-Based & World Models
- ★ **Ha & Schmidhuber 2018, _World Models_** — 世界模型的标志性工作：VAE 编码观测 + RNN 预测 latent 动态 + 小控制器，甚至能「在自己的梦里」训练。模块 04 的世界模型直觉来源，且行文极具启发性，必读。
- ★ **Hafner et al. 2020–2023, _Dream to Control / DreamerV2 / DreamerV3_** — 在 latent 世界模型里想象长程 rollout、用 actor-critic 在想象中训练策略。DreamerV3 用一套超参通吃上百个任务。模块 04 的当代世界模型代表，必读。
- **Hafner et al. 2019, _Learning Latent Dynamics for Planning from Pixels (PlaNet)_** — 在 latent 空间用 CEM 做 MPC 规划（Dreamer 的前身）。模块 04 的 latent 规划线索。
- **Chua et al. 2018, _Deep RL in a Handful of Trials (PETS)_** — 用概率集成动态模型 + CEM-MPC，少量交互即学会控制。模块 04 的 MPC + 模型不确定性的代表，展示采样效率。
- **Sutton 1991, _Dyna: Integrated Architectures for Learning, Planning, and Reacting_** — Dyna 框架原始文献：真实经验与模型生成的模拟经验共同更新值/策略。模块 04 的 Dyna 练习来源。
- **Janner et al. 2019, _When to Trust Your Model (MBPO)_** — 用短程模型 rollout 喂给无模型算法，理论与实践地回答「模型该信多远」（即误差累积下的有效 horizon）。模块 04 误差累积一节的现代对应。
- **Schrittwieser et al. 2020, _Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model (MuZero)_** — 学一个「只为规划够用」的隐式模型 + MCTS，无需环境规则即达 AlphaZero 水平。模型 + 规划的巅峰之一。

## 探索 · Exploration
- ★ **Burda et al. 2018, _Exploration by Random Network Distillation_ (RND)** — 用固定随机网络的预测误差作新颖性内在奖励，优雅且 scalable，在 Montezuma's Revenge 等硬探索任务上突破。模块 05 的核心实现，必读。
- **Pathak et al. 2017, _Curiosity-driven Exploration by Self-supervised Prediction (ICM)_** — 用预测自身动作后果的误差作内在奖励，并用逆模型滤掉不可控噪声。好奇心探索的代表，模块 05 讲解覆盖。
- **Bellemare et al. 2016, _Unifying Count-Based Exploration and Intrinsic Motivation_** — 把表格的计数探索推广到高维：用密度模型导出伪计数。连接 count-based 与内在动机两条线。
- **Osband et al. 2016, _Deep Exploration via Bootstrapped DQN_** — 用 Q 网络的集成做基于不确定性的深度探索（后验采样直觉），是 ε-贪婪之外的另一条重要思路。
- **Ecoffet et al. 2021, _Go-Explore_** — 先「记住并返回」有希望的状态再从那里探索，攻克极难探索任务。展示探索问题的另一种结构化解法。

## 多智能体与决策序列建模 · MARL & Sequence Modeling
- ★ **Chen et al. 2021, _Decision Transformer: RL via Sequence Modeling_** — 把 RL 重铸成回报条件的序列建模，用 Transformer 监督学习离线轨迹、推理时按目标回报条件生成动作。模块 05 的核心玩具，必读。
- **Janner et al. 2021, _Offline RL as One Big Sequence Modeling Problem (Trajectory Transformer)_** — 与 DT 并行的序列建模思路：用 beam search 在序列模型上规划。理解「RL = 序列建模」这一范式的另一支。
- **Emmons et al. 2021, _RvS: What is Essential for Offline RL via Supervised Learning?_** — 系统拆解「监督式 RL」（含 DT）到底靠什么 work、何时不如值方法（轨迹拼接弱）。读它客观看待 DT 的边界。
- **Lowe et al. 2017, _Multi-Agent Actor-Critic (MADDPG)_** — CTDE 范式代表：集中式 critic 看全局、分散式 actor 各自执行。模块 05 MARL 部分的入门。
- **Rashid et al. 2018, _QMIX_** — 合作 MARL 的值分解：用单调混合网络把联合 Q 分解到个体 Q，兼顾集中训练与分散执行。
- **Silver et al. 2016/2017, _AlphaGo / AlphaGo Zero / AlphaZero_** — 自我博弈 + MCTS + 深度网络的里程碑。模块 05 self-play 与「规划 + 学习」结合的标杆。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境纯 numpy / CPU、自写 toy 环境**：GridWorld、numpy 版 CartPole、连续控制玩具均从零实现；网络（小 MLP）、反向传播、优化器、replay buffer 全部手写。每个算法在 toy 环境上跑出**可复现**的收敛/回报提升（固定 seed + 稳健阈值），重在「看懂机制」，规模远小于论文。
- **上游衔接 C13（强化学习地基）**：本课假设你已掌握 MDP/贝尔曼、值迭代、Q-learning/TD、REINFORCE、Actor-Critic/GAE、赌博机探索的**表格与浅层**版本。本课不重复这些，直接处理「搬到神经网络上」的新问题。
- **下游 / 旁系衔接 C22（推理 RL）**：C22 的 GRPO、PRM、verifier 把策略优化用到 LLM 推理上；本课的 PPO/策略梯度是其同源背景。两课互补：C41 讲控制/决策的深度 RL，C22 讲语言/推理的 RL。
- **可迁移性**：你在 numpy 里验证过的 DQN（replay+target+Double）、PPO（clip+GAE）、SAC（双 Q+熵+温度）、CQL/IQL、MPC、RND、DT 训练循环，结构可几乎一对一搬到 PyTorch + Gymnasium/MuJoCo + Stable-Baselines3/CleanRL，再换真实环境与规模。
