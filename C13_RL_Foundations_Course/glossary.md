# 术语词典 · Glossary（强化学习地基）

> 按主题分组，每条 2–3 句中文释义、英文术语保留原文（RL 文献与代码库的通用语言）。读 Sutton & Barto、各算法原始论文遇到生词回这里查。本课用纯 numpy 在 GridWorld/toy 环境上把这些概念从零实现，术语与真实 RL 研究一一对应。

## MDP 与基本要素 · MDP & Basic Elements

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Reinforcement Learning (RL) | 强化学习 | 智能体（agent）通过与环境交互、根据获得的奖励信号学习如何行动以最大化长期累积回报的学习范式。它没有监督学习的标注答案，只有「做得好不好」的标量反馈，且反馈常常延迟。 |
| agent | 智能体 | RL 中做决策的学习主体。它在每个时刻观察状态、选择动作、接收奖励与下一状态，目标是学到一个最大化长期回报的策略。 |
| environment | 环境 | agent 之外的一切，接收 agent 的动作、依据自身动力学转移到新状态并发出奖励。本课的环境是手写的 GridWorld 与 toy MDP，小到可枚举全部状态、可解析求真值。 |
| Markov Decision Process (MDP) | 马尔可夫决策过程 | RL 的标准数学框架，由五元组 $(\mathcal{S}, \mathcal{A}, P, R, \gamma)$ 定义：状态集、动作集、转移概率、奖励函数、折扣因子。它把序贯决策问题形式化。 |
| state $s$ | 状态 | 对当前情境的完整描述。在 GridWorld 里就是格子坐标。状态是决策的依据，价值与策略都定义在状态上。 |
| action $a$ | 动作 | agent 在某状态下可采取的选择（GridWorld 的上下左右）。动作改变环境状态并带来奖励。 |
| reward $r$ | 奖励 | 环境在每步发出的标量反馈，定义了「什么是好」。RL 的全部目标可由 reward hypothesis 概括：最大化累积奖励期望。奖励的设计（reward shaping）极大影响学到的行为。 |
| transition probability $P(s'\mid s,a)$ | 转移概率 | 在状态 $s$ 采取动作 $a$ 后转移到 $s'$ 的概率，刻画环境动力学。确定性环境下它是 0/1 的；随机环境下是分布。 |
| Markov property | 马尔可夫性 | 「未来只依赖现在、不依赖过去」：给定当前状态与动作，下一状态的分布与更早的历史无关。它是 MDP 一切动态规划方法成立的前提。 |
| trajectory / episode | 轨迹 / 回合 | 一次从初始状态到终止（或截断）的状态-动作-奖励序列 $s_0,a_0,r_1,s_1,\dots$。回合制任务有自然终点（如走到目标格），持续任务则靠折扣保证回报有限。 |
| horizon | 时间视界 | 一个回合的步数上限。有限视界问题价值函数依赖剩余步数（非平稳）；无限视界配合折扣 $\gamma<1$ 则价值平稳，是本课主要设定。 |

## 回报、价值与策略 · Return, Value & Policy

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| return $G_t$ | 回报 | 从时刻 $t$ 起的（折扣）累积奖励 $G_t=\sum_{k\ge0}\gamma^k r_{t+k+1}$。RL 要最大化的正是回报的期望，而非单步奖励。 |
| discount factor $\gamma$ | 折扣因子 | $\gamma\in[0,1)$ 给未来奖励打折。它既保证无限视界回报收敛（几何级数），又编码了「多看重未来」：$\gamma$ 越大越有远见，越小越短视。有效视界约 $1/(1-\gamma)$。 |
| policy $\pi$ | 策略 | 从状态到动作（分布）的映射 $\pi(a\mid s)$，即 agent 的行为规则。确定性策略 $\pi(s)=a$，随机策略给出动作概率分布。RL 的目标是找最优策略。 |
| state-value function $V^\pi(s)$ | 状态价值函数 | 从状态 $s$ 出发、按策略 $\pi$ 行动的期望回报 $\mathbb{E}_\pi[G_t\mid s_t=s]$。它衡量「处在这个状态有多好」（在 $\pi$ 之下）。 |
| action-value function $Q^\pi(s,a)$ | 动作价值函数 | 在状态 $s$ 先采取动作 $a$、之后按 $\pi$ 行动的期望回报。它衡量「在这个状态做这个动作有多好」，比 $V$ 多一维，使无模型控制（如 Q-learning）成为可能。 |
| optimal value $V^*, Q^*$ | 最优价值 | 所有策略中能达到的最大价值 $V^*(s)=\max_\pi V^\pi(s)$。$Q^*$ 同理。它们满足 Bellman 最优方程，是动态规划求解的目标。 |
| optimal policy $\pi^*$ | 最优策略 | 在所有状态上价值都不劣于任何其他策略的策略。MDP 中必存在一个确定性最优策略，可由 $\pi^*(s)=\arg\max_a Q^*(s,a)$ 贪心导出。 |
| greedy policy | 贪心策略 | 在每个状态选当前价值估计最高的动作 $\arg\max_a Q(s,a)$。对 $Q^*$ 贪心得到 $\pi^*$；但学习中纯贪心会缺乏探索。 |
| advantage $A^\pi(s,a)$ | 优势函数 | $A^\pi(s,a)=Q^\pi(s,a)-V^\pi(s)$，衡量动作 $a$ 比该状态平均水平好多少。它把 $V$ 当 baseline，是策略梯度降方差的核心量。 |
| occupancy / stationary distribution $d^\pi$ | 占用度量 / 平稳分布 | 在策略 $\pi$ 下各状态被访问的（折扣）频率分布。策略梯度定理里的状态权重正是它，解释了为什么常访问的状态对梯度贡献更大。 |

## Bellman 方程与动态规划 · Bellman & Dynamic Programming

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Bellman expectation equation | Bellman 期望方程 | 把价值递归地写成「即时奖励 + 折扣后继价值的期望」：$V^\pi(s)=\sum_a\pi(a\mid s)\sum_{s'}P(s'\mid s,a)[r+\gamma V^\pi(s')]$。它是评估一个给定策略的基础。 |
| Bellman optimality equation | Bellman 最优方程 | 把价值递归写成对动作取 max：$V^*(s)=\max_a\sum_{s'}P(s'\mid s,a)[r+\gamma V^*(s')]$。它非线性（含 max），但其解唯一，是控制问题的目标方程。 |
| Bellman backup / update | Bellman 备份 | 用 Bellman 方程右端更新左端价值估计的一步操作。反复备份是价值迭代/Q-learning 的核心循环，可视为「把后继的信息回传一步」。 |
| dynamic programming (DP) | 动态规划 | 已知环境模型 $(P,R)$ 时，用 Bellman 方程系统求解价值/最优策略的一类方法（价值迭代、策略迭代）。它需要完整模型，是无模型方法的理论参照。 |
| policy evaluation | 策略评估 | 给定策略 $\pi$，求其价值函数 $V^\pi$（解线性 Bellman 期望方程，或迭代逼近）。它是策略迭代的第一步。 |
| policy improvement | 策略改进 | 基于当前 $V^\pi$ 贪心地构造更好的策略 $\pi'(s)=\arg\max_a Q^\pi(s,a)$。policy improvement theorem 保证 $\pi'$ 不劣于 $\pi$。 |
| policy iteration (PI) | 策略迭代 | 交替「策略评估 + 策略改进」直到策略不再变化。它在有限 MDP 上有限步收敛到最优，每步改进单调，但每轮评估较贵。 |
| value iteration (VI) | 价值迭代 | 直接迭代 Bellman 最优备份 $V\leftarrow\max_a(\dots)$ 直到收敛，再一次性导出贪心策略。可视为「评估只做一步」的策略迭代，实现简单、应用最广。 |
| generalized policy iteration (GPI) | 广义策略迭代 | 评估与改进两个过程任意交错、互相驱动的统一框架。几乎所有 RL 算法（DP、TD、actor-critic）都是 GPI 的实例。 |
| contraction mapping | 压缩映射 | 满足 $\lVert Tx-Ty\rVert\le\gamma\lVert x-y\rVert$（$\gamma<1$）的算子。Bellman 算子在 $\infty$-范数下是 $\gamma$-压缩，由 Banach 不动点定理保证价值迭代以 $\gamma$ 的几何速率收敛到唯一不动点。 |
| Banach fixed-point theorem | 巴拿赫不动点定理 | 完备空间上的压缩映射有唯一不动点，且任意初值反复迭代都收敛到它。这是价值迭代收敛性的数学基石。 |
| bootstrapping | 自举 | 用「当前对后继状态价值的估计」来更新当前状态的估计，而非等到回合结束看真实回报。DP 与 TD 都自举；蒙特卡洛不自举。自举降方差但引入偏差。 |

## 时序差分与无模型学习 · TD & Model-Free Learning

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| model-free | 无模型 | 不需要知道环境的 $P,R$，仅靠与环境交互采样来学习价值/策略。TD、Q-learning、策略梯度都是无模型的——这正是它们能用于未知环境的原因。 |
| Monte Carlo (MC) | 蒙特卡洛 | 用一整条回合的真实回报 $G_t$ 作为价值的无偏样本来更新估计。无偏但方差大，且必须等回合结束。 |
| temporal difference (TD) | 时序差分 | 结合 DP 的自举与 MC 的采样：用 $r+\gamma V(s')$（一步真实奖励 + 自举后继估计）更新 $V(s)$，无需等回合结束。是无模型预测的核心。 |
| TD error $\delta$ | TD 误差 | $\delta_t=r_{t+1}+\gamma V(s_{t+1})-V(s_t)$，即「自举目标」与「当前估计」之差。它是 TD 更新的驱动信号，也是 advantage 的单样本无偏估计，贯穿 actor-critic 与 GAE。 |
| TD target | TD 目标 | TD 更新追逐的值 $r+\gamma V(s')$（或 $r+\gamma\max_{a'}Q(s',a')$）。它部分基于真实奖励、部分基于自举估计。 |
| TD(0) | 单步 TD | 只自举一步的 TD：用 $r+\gamma V(s')$ 更新。是最基础的 TD 预测算法。 |
| Q-learning | Q 学习 | 经典 off-policy 控制：用 $r+\gamma\max_{a'}Q(s',a')$ 更新 $Q(s,a)$，目标里的 max 使它直接逼近 $Q^*$，与采样所用的行为策略无关。Watkins 1989 提出并证明收敛。 |
| SARSA | —— | on-policy 控制：用 $r+\gamma Q(s',a')$ 更新，其中 $a'$ 是行为策略实际选的下一动作。它学的是「当前（含探索的）策略」的价值，比 Q-learning 在探索有风险时更保守。 |
| on-policy / off-policy | 同策略 / 异策略 | on-policy 用「正在执行的策略」产生的数据学这同一个策略（SARSA、A2C）；off-policy 可用其他（行为）策略产生的数据学目标策略（Q-learning），数据可复用但更易不稳定。 |
| behavior vs target policy | 行为策略 vs 目标策略 | 行为策略负责探索、实际产生数据（如 ε-greedy）；目标策略是想学的策略（如贪心）。两者一致即 on-policy，不一致即 off-policy。 |
| $\varepsilon$-greedy | ε-贪心 | 最简单的探索策略：以 $1-\varepsilon$ 概率选当前最优动作（利用），以 $\varepsilon$ 概率随机探索。$\varepsilon$ 常随训练衰减，从多探索过渡到多利用。 |
| learning rate $\alpha$ | 学习率 | TD/Q-learning 更新步长 $Q\leftarrow Q+\alpha\,\delta$。它在「新样本」与「旧估计」间加权。太大震荡、太小慢。 |
| Robbins-Monro conditions | 罗宾斯-门罗条件 | 随机近似收敛的步长条件 $\sum_t\alpha_t=\infty,\ \sum_t\alpha_t^2<\infty$（步长不能太快归零、又要最终趋零）。Q-learning/TD 在此条件 + 充分探索下以概率 1 收敛。 |
| tabular | 表格型 | 用一张表显式存每个 $(s)$ 或 $(s,a)$ 的价值（无函数逼近）。本课全程表格型，状态少到能枚举，便于对拍精确解；深度 RL（C41）才换成神经网络。 |

## 策略梯度 · Policy Gradient

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| policy gradient | 策略梯度 | 直接把策略参数化为 $\pi_\theta$、对期望回报 $J(\theta)$ 做梯度上升的一类方法。无需价值函数即可优化策略，天然处理连续/随机动作，是现代深度 RL（PPO 等）的主干。 |
| policy gradient theorem | 策略梯度定理 | 给出 $\nabla_\theta J=\mathbb{E}[\sum_t\nabla_\theta\log\pi_\theta(a_t\mid s_t)\,Q^\pi(s_t,a_t)]$，关键在于梯度不含环境动力学 $\nabla P$，因而可纯由采样估计。Sutton 2000 的奠基结果。 |
| log-derivative trick | 对数导数技巧 | 恒等式 $\nabla_\theta\pi_\theta=\pi_\theta\nabla_\theta\log\pi_\theta$，把对概率的梯度转成「概率加权的对数概率梯度」，从而写成期望、可用样本估计。也叫 REINFORCE trick / score function estimator。 |
| score function | 得分函数 | $\nabla_\theta\log\pi_\theta(a\mid s)$，对数似然对参数的梯度。策略梯度沿它的方向、按回报/优势加权地推高好动作的概率。 |
| REINFORCE | —— | 最基础的策略梯度算法（Williams 1992）：用整条回合的蒙特卡洛回报 $G_t$ 加权 score function 做更新。无偏但方差大，常配 baseline 使用。 |
| baseline $b(s)$ | 基线 | 从回报里减去的、不依赖动作的参照量（常取 $V(s)$）。因 $\mathbb{E}[\nabla\log\pi\cdot b]=0$，减它不引入偏差，却能大幅降低梯度方差。是策略梯度最重要的方差缩减手段。 |
| variance reduction | 方差缩减 | 在不（或少）引入偏差的前提下降低梯度估计方差的技术总称：baseline、advantage、回报标准化、GAE、控制变量等。方差是策略梯度样本效率的主要瓶颈。 |
| return normalization | 回报标准化 | 把一个 batch 内的回报/优势减均值除标准差，稳定不同回合间的梯度尺度、隐式自适应学习率。工程上几乎必用，但严格说会引入小偏差。 |
| entropy regularization | 熵正则 | 在目标里加策略熵奖励 $\beta\,\mathcal{H}(\pi_\theta(\cdot\mid s))$，鼓励策略保持随机、避免过早收敛到次优确定性策略。$\beta$ 控制探索强度。 |
| score function estimator / likelihood-ratio | 得分函数估计 / 似然比 | 策略梯度所用的梯度估计器别名，强调它通过 $\nabla\log\pi$（似然比）而非对环境反传来估计梯度，故可用于不可微环境。 |

## Actor-Critic 与 GAE · Actor-Critic & GAE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| actor-critic | 演员-评论家 | 把策略梯度（actor，更新策略）与价值估计（critic，估 $V$/$Q$）结合：critic 提供低方差的 advantage 估计替代蒙特卡洛回报，actor 据此更新。兼具策略梯度的灵活与自举的低方差。 |
| actor | 演员 | actor-critic 中被优化的策略 $\pi_\theta$，负责产生动作。它沿 critic 给出的 advantage 方向更新。 |
| critic | 评论家 | actor-critic 中估计价值函数 $V_\phi$（或 $Q$）的部分。它用 TD 误差自举训练，给 actor 提供「这一步比平均好多少」的低方差信号。 |
| A2C (Advantage Actor-Critic) | 优势演员-评论家 | actor-critic 的标准同步实现：用 advantage（常由 TD 误差或 GAE 估计）加权 score function 更新 actor，同时用 TD 回归更新 critic。A3C 是其异步版。 |
| Generalized Advantage Estimation (GAE) | 广义优势估计 | Schulman 2016 提出的 advantage 估计族，用参数 $\lambda$ 对不同步数的 TD 误差做指数加权：$\hat A_t=\sum_{l\ge0}(\gamma\lambda)^l\delta_{t+l}$。$\lambda$ 在偏差（小 $\lambda$）与方差（大 $\lambda$）间连续滑动。 |
| $\lambda$ (GAE / TD(λ)) | GAE 衰减参数 | GAE/TD(λ) 中权衡 bias-variance 的旋钮。$\lambda=0$ 退化为单步 TD（低方差高偏差），$\lambda=1$ 退化为蒙特卡洛优势（高方差无偏），中间值通常最优（如 0.95）。 |
| bias-variance tradeoff | 偏差-方差权衡 | 估计量的核心矛盾：自举（短回溯）降方差但因依赖不准的价值估计而有偏；蒙特卡洛（长回溯）无偏但方差大。$\lambda$、$n$-step 都是调这个权衡的旋钮。 |
| $n$-step return | $n$ 步回报 | 用 $n$ 步真实奖励再自举的目标 $\sum_{k=0}^{n-1}\gamma^k r_{t+k+1}+\gamma^n V(s_{t+n})$。$n=1$ 是 TD(0)，$n=\infty$ 是 MC，GAE 是对所有 $n$ 步回报的加权平均。 |
| TD(λ) / eligibility trace | TD(λ) / 资格迹 | 用几何加权融合所有 $n$-step 回报的 TD 算法；资格迹是其在线、增量实现，记录各状态「最近被访问」的程度并据此分配 TD 误差。GAE 是 TD(λ) 思想在 advantage 上的应用。 |
| value function approximation | 价值函数逼近 | 用参数化函数（本课用线性/表格，深度 RL 用神经网络）近似 $V$/$Q$。critic 即一个被训练的价值逼近器，其拟合质量直接决定 advantage 估计的偏差。 |

## 多臂老虎机与探索 · Bandits & Exploration

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| multi-armed bandit (MAB) | 多臂老虎机 | 最简单的 RL 设定：只有一个状态、$K$ 个动作（臂），每臂拉动得到一个随机奖励。它剥离了状态转移，把问题浓缩为最纯粹的 explore-exploit 困境。 |
| exploration vs exploitation | 探索 vs 利用 | RL 的根本矛盾：利用是选当前看起来最好的动作以即时获益，探索是尝试不确定的动作以获取信息、可能发现更优。两者必须平衡——只利用会困在次优，只探索会浪费。 |
| regret | 遗憾 | 累积地，「一直拉最优臂能得的期望奖励」减去「算法实际所得」。它衡量探索的代价。好算法的 regret 随时间次线性增长（$O(\log T)$），即长期看几乎不亏。 |
| Lai-Robbins lower bound | 莱-罗宾斯下界 | 任何「合理」老虎机算法的 regret 至少 $\Omega(\log T)$，且常数与各臂奖励分布的 KL 散度有关。它是 regret 的理论极限，UCB/Thompson 都能达到这个量级。 |
| Upper Confidence Bound (UCB) | 置信上界 | 「面对不确定时保持乐观」的探索策略：给每臂的均值估计加一个随访问次数收缩的置信半径，选上界最高的臂。UCB1 的 regret 是最优的 $O(\log T)$。 |
| UCB1 | —— | Auer 2002 给出的具体 UCB 算法：选 $\arg\max_a[\hat\mu_a+\sqrt{2\ln t/N_a}]$。置信项随该臂被拉次数 $N_a$ 减小、随总步数 $t$ 增大，自动平衡探索与利用。 |
| Thompson sampling | 汤普森采样 | 贝叶斯探索：为每臂维护奖励参数的后验分布，每步从各后验采一个样本、选采样值最大的臂（probability matching）。实现简单、实证常优于 UCB，regret 也达最优。 |
| posterior / Beta-Bernoulli | 后验 / Beta-伯努利 | 贝叶斯更新里数据观测后的参数分布。伯努利奖励的共轭先验是 Beta 分布：观测一次成功/失败就把 Beta 的 $\alpha$/$\beta$ 加一，后验仍是 Beta，便于解析维护。Thompson sampling 据此采样。 |
| optimism in the face of uncertainty | 面对不确定的乐观 | UCB 类方法的指导原则：对不确定（少被尝试）的选项给予乐观的价值估计，从而自然地多探索它们；一旦数据增多、不确定下降，乐观加成消失。 |
| concentration inequality (Hoeffding) | 集中不等式（霍夫丁） | 给出样本均值偏离真均值的概率上界，是 UCB 置信半径的理论来源。Hoeffding 不等式让我们以高概率把真均值框在 $\hat\mu\pm$ 半径内。 |
| probability matching | 概率匹配 | 按「某臂是最优的后验概率」来选择该臂的策略思想。Thompson sampling 通过从后验采样自然实现了概率匹配。 |

## 方法论与本课设定 · Methodology

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| GridWorld | 网格世界 | RL 教学最经典的 toy 环境：智能体在二维格子上移动，撞墙/到目标/落陷阱给不同奖励。状态少到可枚举、可解析求最优，是对拍算法正确性的理想沙盒，本课主力环境。 |
| credit assignment | 信用分配 | 把延迟到来的回报正确归因到此前哪些动作的问题。RL 的核心难点之一：奖励可能在很多步后才出现，算法必须判断是哪一步的功劳。折扣、TD、GAE 都在处理它。 |
| sample efficiency | 样本效率 | 达到给定性能所需的环境交互次数。RL（尤其无模型策略梯度）常样本低效，方差缩减、自举、经验复用都是为提升它。 |
| stochastic approximation | 随机近似 | 用带噪声的样本逐步逼近某个量（如不动点）的迭代框架。TD/Q-learning 本质是 Bellman 算子不动点的随机近似，其收敛性由 Robbins-Monro 理论保证。 |
| reproducibility / seed | 可复现 / 随机种子 | 固定随机数种子使随机实验可精确重跑。本课每条 return/regret 曲线都固定 `np.random.default_rng(seed)`，保证结论可复现——这是严肃 RL 实验的基本纪律。 |
| reward hypothesis | 奖励假设 | Sutton 的论断：一切目标与意图都可表述为「最大化累积标量奖励期望」。它是 RL 把多样目标统一成单一优化问题的哲学前提。 |
