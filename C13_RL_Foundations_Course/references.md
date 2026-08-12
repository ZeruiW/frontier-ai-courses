# 参考清单 · References（强化学习地基）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用纯 numpy 在 GridWorld/toy 环境上从零实现的每个算法，都能在下列文献里找到它的原始推导、收敛性证明与现代延伸。

## 教材与综述 · Textbooks & Surveys
- ★ **Sutton & Barto, _Reinforcement Learning: An Introduction_ (2nd ed., 2018)** — RL 的「圣经」，本课每个模块都对标它的章节。第 3 章 MDP/Bellman、第 4 章动态规划（VI/PI）、第 6 章 TD、第 2 章老虎机、第 13 章策略梯度。**第二版全文作者免费公开**。遇到任何概念分歧以它为准；强烈建议配套精读对应章节，本课是它的「动手实现版」。
- ★ **Sutton & Barto 第 2 章 _Multi-armed Bandits_** — 把 explore-exploit 困境、$\varepsilon$-greedy、UCB、增量均值更新讲到极致清晰，是模块 05 的直接来源。它先在无状态的老虎机里把探索讲透，再进入完整 MDP，这个教学顺序本课沿用。
- **Szepesvári, _Algorithms for Reinforcement Learning_ (2010)** — 更偏理论的精炼综述，对 TD/Q-learning 的随机近似收敛性、函数逼近下的发散问题有紧凑的数学处理。想深究收敛性证明时读它。
- **Bertsekas, _Dynamic Programming and Optimal Control_** — 从最优控制视角讲动态规划与近似 DP，对压缩映射、值/策略迭代的收敛性有最严格的处理。模块 01 收敛性部分的理论靠山。
- **Lattimore & Szepesvári, _Bandit Algorithms_ (2020)** — 老虎机理论的现代权威专著，Lai-Robbins 下界、UCB 各变体、Thompson sampling 的 regret 分析一应俱全。模块 05 想往深里走的下一本。

## MDP、Bellman 与动态规划 · MDP, Bellman & DP
- ★ **Bellman, _Dynamic Programming_ (1957)** — 动态规划与 Bellman 方程的原始出处，「最优性原理」的提出。理解 VI/PI 为何成立的历史与思想源头。
- **Howard, _Dynamic Programming and Markov Processes_ (1960)** — 策略迭代（policy iteration）算法的原始论文，证明其有限步收敛。模块 01 策略迭代部分的奠基文献。
- **Puterman, _Markov Decision Processes_ (1994)** — MDP 理论的标准参考书，关于最优策略存在性、值/策略迭代收敛速率的定理叙述最完整。查 MDP 定理的工具书。
- **Banach (1922) 不动点定理 / 任意泛函分析教材** — 价值迭代以 $\gamma$ 几何速率收敛的数学基石：Bellman 算子是 $\infty$-范数下的 $\gamma$-压缩映射，故有唯一不动点且迭代必收敛。模块 01 收敛性证明直接用它。

## 时序差分与 Q-learning · TD & Q-learning
- ★ **Sutton 1988, _Learning to Predict by the Methods of Temporal Differences_** — TD 学习的奠基论文，提出用自举 + 采样做预测、证明 TD(0) 的收敛性。模块 02 的理论原点，解释「为什么不必等回合结束就能学」。
- ★ **Watkins 1989 (博士论文) & Watkins & Dayan 1992, _Q-learning_** — Q-learning 的提出与收敛性证明（在 Robbins-Monro 步长 + 充分探索下以概率 1 收敛到 $Q^*$）。模块 02 的核心，off-policy 控制的开端，也是 DQN（C41）的直接祖先。
- **Rummery & Niranjan 1994, _On-line Q-learning using Connectionist Systems_** — SARSA 算法的原始出处（"modified Q-learning"，SARSA 之名来自 Sutton）。模块 02 对比 on-policy 与 off-policy 的依据。
- **Tsitsiklis & Van Roy 1997, _An Analysis of Temporal-Difference Learning with Function Approximation_** — 揭示 TD 在 off-policy + 函数逼近 + 自举「致命三要素」下可能发散。本课表格型不受其害，但它是理解为何深度 RL（C41）难稳定的必读，承上启下。
- **Jaakkola, Jordan & Singh 1994, _Convergence of Stochastic Iterative DP Algorithms_** — 用随机近似理论统一证明 TD/Q-learning 收敛。把 TD 看成随机近似的严格视角来源。

## 策略梯度 · Policy Gradient
- ★ **Williams 1992, _Simple Statistical Gradient-Following Algorithms (REINFORCE)_** — REINFORCE 与 log-derivative（似然比）梯度估计的奠基论文，并最早讨论 baseline 降方差。模块 03 全程在复现它，策略梯度的起点。
- ★ **Sutton, McAllester, Singh & Mansour 2000, _Policy Gradient Methods for RL with Function Approximation_** — 策略梯度定理的严格表述与证明：梯度可写成 $\mathbb{E}[\nabla\log\pi\cdot Q]$，不含 $\nabla P$，故可纯采样估计。模块 03 数学推导的核心依据。
- **Baxter & Bartlett 2001, _Infinite-Horizon Policy-Gradient Estimation (GPOMDP)_** — 折扣/平均奖励下策略梯度的另一条严格推导，对 baseline 与方差有深入分析。与 Sutton 2000 互补。
- **Greensmith, Bartlett & Baxter 2004, _Variance Reduction Techniques for Gradient Estimates in RL_** — 系统分析 baseline、actor-critic 等方差缩减手段，给出最优 baseline 的形式。模块 03/04 方差缩减部分的理论支撑。
- **Peters & Schaal 2008, _Reinforcement Learning of Motor Skills with Policy Gradients_** — 自然策略梯度与策略梯度在实际控制中的应用综述，连接基础理论与现代算法（TRPO/PPO 的前身）。

## Actor-Critic 与 GAE · Actor-Critic & GAE
- ★ **Schulman, Moritz, Levine, Jordan & Abbeel 2016, _High-Dimensional Continuous Control Using Generalized Advantage Estimation (GAE)_** — GAE 的原始论文，把 advantage 估计写成 TD 误差的 $(\gamma\lambda)$ 指数加权和，用一个 $\lambda$ 连续调节 bias-variance。模块 04 的核心，现代 PPO 的标配组件。
- ★ **Konda & Tsitsiklis 2000, _Actor-Critic Algorithms_** — actor-critic 的奠基理论分析，证明用 critic 估计的 advantage 做策略梯度的收敛性（兼容函数逼近的 compatible features）。模块 04 把策略梯度与价值估计结合的依据。
- **Mnih et al. 2016, _Asynchronous Methods for Deep RL (A3C/A2C)_** — A3C/A2C 的提出，把 actor-critic + n-step advantage + 熵正则组装成实用的深度 RL 算法。模块 04 的 A2C 环路对标它（本课用 numpy 表格版）。
- **Degris, White & Sutton 2012, _Off-Policy Actor-Critic_** — 把 actor-critic 推广到 off-policy 数据，引入重要性采样修正。理解 actor-critic 如何复用数据的延伸阅读。

## 探索与多臂老虎机 · Exploration & Bandits
- ★ **Lai & Robbins 1985, _Asymptotically Efficient Adaptive Allocation Rules_** — 证明老虎机 regret 的 $\Omega(\log T)$ 下界，并给出达到它的策略。模块 05 regret 理论的奠基，所有「好」探索算法的标尺。
- ★ **Auer, Cesa-Bianchi & Fischer 2002, _Finite-time Analysis of the Multiarmed Bandit Problem (UCB1)_** — UCB1 算法与其 $O(\log T)$ 有限时间 regret 证明。模块 05 UCB 部分的直接来源，「面对不确定的乐观」的范本。
- ★ **Thompson 1933, _On the Likelihood that One Unknown Probability Exceeds Another_** — Thompson sampling 的原始论文（早于整个 RL 领域！），按后验概率采样选臂。模块 05 贝叶斯探索的源头。
- **Chapelle & Li 2011, _An Empirical Evaluation of Thompson Sampling_** — 实证证明 Thompson sampling 在实际问题上常优于 UCB，让这个 1933 年的老方法在现代复兴。模块 05 比较实验的依据。
- **Agrawal & Goyal 2012, _Analysis of Thompson Sampling for the Multi-armed Bandit Problem_** — 首个 Thompson sampling 的 regret 理论上界（达到最优 $O(\log T)$），补齐其理论保证。
- **Russo et al. 2018, _A Tutorial on Thompson Sampling_** — 现代、可读性极强的 Thompson sampling 教程，覆盖语境老虎机、强化学习中的后验采样。想系统学贝叶斯探索读它。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课全程纯 numpy、CPU、表格型**：环境是手写 GridWorld 与 toy MDP/老虎机，状态少到可枚举。我们刻意停在表格世界，因为这样**每个价值/策略都能对拍解析精确解**（VI/PI 收敛到同一 $V^*$、Q-learning 学到的贪心策略 == DP 最优策略），**每条曲线都能固定种子复现**。先把算法的*骨架与正确性*在干净环境里夯死。
- **为什么不上 gym/torch**：深度 RL 的不稳定（致命三要素、超参敏感）会淹没对算法本身的理解。本课的纪律是：在能求出真值的小环境里，确认你写的 Bellman 备份、TD 更新、策略梯度估计、GAE 递推**逻辑完全正确**，再去深度 RL 里加神经网络这个「方差与不稳定的放大器」。
- **课程衔接**：下游接 **C41 深度强化学习**（DQN = Q-learning + 神经网络 + 经验回放；PPO = 策略梯度 + GAE + 裁剪；SAC = actor-critic + 最大熵）——你会发现 C41 的每个算法都是本课某个表格算法换上函数逼近；以及 **C22 推理 RL**（RLHF/PPO、GRPO、reward model）——大语言模型的 RL 微调本质仍是策略梯度 + advantage 估计，本课的 REINFORCE/baseline/GAE 正是其内核。**地基不牢，上层全是玄学。**
