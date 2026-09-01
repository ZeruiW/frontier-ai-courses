# 术语词典 · Glossary（深度强化学习与决策）

> 按主题分组，每条 2–3 句释义。读 DQN / PPO / SAC / 世界模型 / 离线 RL 论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课假设你已掌握 C13 的表格 RL 基础（MDP、贝尔曼、Q-learning、策略梯度、GAE），这里只补「深度 / 控制 / 模型 / 前沿」层的术语，少量基础项作快速复习收录。

## 基础回顾 · Foundations Recap（详见 C13）

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MDP (Markov Decision Process) | 马尔可夫决策过程 | 由状态、动作、转移概率、奖励、折扣构成的序贯决策框架。「马尔可夫」指下一状态只依赖当前状态与动作，与历史无关。本课所有算法都在 MDP（或其部分可观测推广）上运行。 |
| return / discounted return | 回报 / 折扣回报 | 从某时刻起未来奖励的（折扣）累加 $G_t=\sum_{k\ge0}\gamma^k r_{t+k}$。RL 的最终优化目标是最大化期望回报。折扣 $\gamma\in[0,1)$ 让无穷和收敛并体现「近期奖励更重要」。 |
| value function $V^\pi$, $Q^\pi$ | 状态值 / 动作值函数 | $V^\pi(s)$ 是从 $s$ 起按策略 $\pi$ 的期望回报；$Q^\pi(s,a)$ 是先在 $s$ 执行 $a$、之后按 $\pi$ 的期望回报。二者由贝尔曼方程联系，是值方法的核心对象。 |
| Bellman equation / operator | 贝尔曼方程 / 算子 | 把值函数写成「即时奖励 + 折扣的下一步值」的自洽方程。贝尔曼最优算子是 $\gamma$-压缩映射，表格情形下值迭代必收敛——这一保证在函数逼近下会失效（见致命三要素）。 |
| policy $\pi$, on/off-policy | 策略、同策略 / 离策略 | 策略是状态到动作（分布）的映射。同策略指用当前策略产生的数据更新当前策略（如 SARSA、PPO）；离策略指用别的策略（如旧策略、replay 中的历史数据）的数据更新（如 Q-learning、DQN、SAC）。 |
| TD error / bootstrapping | 时序差分误差 / 自举 | TD 误差 $\delta=r+\gamma V(s')-V(s)$ 用「自己当前的估计」$V(s')$ 当作未来的近似——这就是自举。自举降低方差、可在线学习，但与逼近+离策略组合会引发不稳定（致命三要素）。 |
| advantage $A(s,a)$ | 优势函数 | $A^\pi(s,a)=Q^\pi(s,a)-V^\pi(s)$：动作 $a$ 比该状态平均水平好多少。策略梯度用优势作权重，比用原始回报方差更低。 |
| GAE (Generalized Advantage Estimation) | 广义优势估计 | 用 $\lambda$ 在「单步 TD（低方差高偏差）」与「蒙特卡洛（高方差低偏差）」之间插值的优势估计：$\hat A_t=\sum_{l\ge0}(\gamma\lambda)^l\delta_{t+l}$。C13 已引入，本课 PPO 直接复用它。 |

## 函数逼近与深度 RL · Function Approximation & Deep RL

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| function approximation | 函数逼近 | 用参数化函数（线性、神经网络）表示 $V/Q/\pi$，而非为每个状态存一个数。状态空间巨大或连续时唯一可行的路；代价是丢掉了表格法的收敛保证，并引入泛化与干扰。 |
| deadly triad | 致命三要素 | 自举（bootstrapping）+ 离策略（off-policy）+ 函数逼近，三者同时出现时 RL 训练可能发散。任意去掉一个通常都稳。理解它是理解 DQN 一切稳定化技巧的钥匙。 |
| semi-gradient | 半梯度 | TD 类更新只对预测值 $Q(s,a)$ 求梯度，把自举目标 $r+\gamma\max Q(s',\cdot)$ 当常数（不回传其梯度）。它不是任何固定损失的真梯度，这正是不稳定的根源之一。 |
| deep RL | 深度强化学习 | 用深度神经网络做函数逼近的 RL。从 DQN（2015 玩 Atari）起成为主流；带来表达力的同时也带来训练不稳定、采样低效、调参敏感等系统性难题。 |
| replay buffer / experience replay | 经验回放（缓冲） | 把交互产生的 $(s,a,r,s',done)$ 转移存入一个大缓冲，训练时随机小批量采样。打破样本时间相关性（满足近似 i.i.d.）、提高数据复用率，是 off-policy 深度 RL 的标配。 |
| target network | 目标网络 | DQN 中一个参数被「冻结/缓慢更新」的 Q 网络副本，专门用来算自举目标 $r+\gamma\max_{a'}Q_{\bar\theta}(s',a')$。让目标在一段时间内不动，缓解「追逐移动靶」的不稳定。 |
| Polyak / soft update | 软更新 | 目标网络参数缓慢跟踪在线网络：$\bar\theta\leftarrow\tau\theta+(1-\tau)\bar\theta$，$\tau\ll1$。相对「每 N 步硬拷贝」更平滑，SAC/DDPG 常用。 |
| overestimation bias | 过估计偏差 | $\max_{a'}Q(s',a')$ 中的 max 会系统性地高估真实最优值——因为它对带噪声的估计取最大，噪声的正向波动被选中。Double DQN/双 Q 专门修这个。 |
| Double DQN | 双重 DQN | 用在线网络选动作、用目标网络评估其值：$r+\gamma Q_{\bar\theta}(s',\arg\max_{a'}Q_\theta(s',a'))$。把「选」与「评」解耦，削弱过估计。 |
| Dueling network | 对决网络架构 | 把 Q 网络拆成「状态值 $V(s)$」与「动作优势 $A(s,a)$」两支再合并：$Q=V+(A-\text{mean}_aA)$。在动作好坏差别不大的状态下更高效地学 $V$。 |
| TD target / TD loss | TD 目标 / 损失 | 目标 $y=r+\gamma\max_{a'}Q_{\bar\theta}(s',a')$（终止则 $y=r$）；损失 $(Q_\theta(s,a)-y)^2$（常用 Huber）。DQN 把 RL 变成对这个回归目标的监督学习，但目标本身在变。 |
| Huber loss | Huber 损失 | 小误差用平方、大误差用线性的混合损失。对 TD 误差中的离群值更鲁棒（梯度有界），DQN 原文用它稳定训练。 |
| epsilon-greedy | ε-贪婪 | 以概率 $\varepsilon$ 随机探索、否则取 $\arg\max_a Q$。DQN 的默认探索策略，$\varepsilon$ 通常从 1 线性退火到 0.05 左右。 |
| Rainbow | —— | 把 Double、Dueling、优先回放、多步、分布式 Q、Noisy Net 六项 DQN 改进集成的工作（Hessel 2018）。说明这些技巧大多正交、可叠加。 |
| prioritized experience replay (PER) | 优先经验回放 | 按 TD 误差大小给转移分配采样概率，多学「意外」的样本，并用重要性权重纠偏。比均匀采样更高效，是 Rainbow 的组件之一。 |

## 策略优化 · Policy Optimization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| policy gradient | 策略梯度 | 直接对参数化策略 $\pi_\theta$ 的期望回报求梯度并上升。基本形式 $\nabla J=\mathbb E[\nabla\log\pi_\theta(a\vert s)\,\hat A]$。C13 讲了 REINFORCE/Actor-Critic，本课接着做信赖域与 clip。 |
| importance sampling ratio | 重要性采样比 | $r_t(\theta)=\pi_\theta(a_t\vert s_t)/\pi_{\theta_{\text{old}}}(a_t\vert s_t)$。让用旧策略采的数据能评估新策略，是 PPO/TRPO 复用数据做多次更新的关键；比值偏离 1 太多则估计方差爆炸。 |
| surrogate objective | 代理目标 | 用重要性比把策略改进写成可对采样数据优化的目标 $\mathbb E[r_t(\theta)\hat A_t]$。直接最大化它会步子过大，故需信赖域或 clip 约束。 |
| trust region / TRPO | 信赖域 / TRPO | 限制新旧策略的 KL 散度在一个「信赖域」内，保证单调改进（Schulman 2015）。理论漂亮但需二阶优化（共轭梯度 + 线搜索），实现复杂——PPO 是它的一阶廉价近似。 |
| PPO (Proximal Policy Optimization) | 近端策略优化 | 用 clip 把重要性比限制在 $[1-\epsilon,1+\epsilon]$ 来近似信赖域：$\min(r_t\hat A_t,\ \text{clip}(r_t,1-\epsilon,1+\epsilon)\hat A_t)$。一阶、好实现、稳健，是当今最常用的策略优化算法（含 RLHF）。 |
| clipped surrogate | 裁剪代理目标 | PPO 的核心目标（上条公式）。取裁剪与未裁剪的较小值，使「优势为正时不奖励过大的比、优势为负时不惩罚过小的比」，从而抑制过大更新。 |
| KL penalty / early stopping | KL 惩罚 / 提前停止 | PPO 的两种辅助约束：在目标里加 $-\beta\,\mathrm{KL}$ 惩罚，或当本轮 KL 超阈值时提前停止本批更新。防止多轮 epoch 把策略推离旧策略太远。 |
| entropy bonus | 熵奖励 | 在策略目标里加策略熵 $\mathcal H(\pi)$ 鼓励随机性、维持探索、防过早收敛到次优确定策略。PPO/A2C 的常见正则项。 |
| maximum entropy RL | 最大熵强化学习 | 优化目标改为「回报 + 温度 × 策略熵」：$\sum_t\mathbb E[r_t+\alpha\mathcal H(\pi(\cdot\vert s_t))]$。鼓励在获得高回报的同时尽量随机，提升探索与鲁棒性。SAC 的理论框架。 |
| SAC (Soft Actor-Critic) | 软演员-评论家 | 离策略 + 最大熵的连续控制算法（Haarnoja 2018）：双 Q 削过估计、随机策略（高斯 + tanh 压缩）、自动调温度 $\alpha$。采样高效、稳健，是连续控制的主力之一。 |
| temperature $\alpha$ | 温度系数 | 最大熵目标里熵项的权重。大 $\alpha$ 更随机更探索，小 $\alpha$ 更贪婪。SAC 把它设成可学习参数，自动维持目标熵水平，省去手调。 |
| reparameterization trick | 重参数化技巧 | 把随机采样 $a\sim\mathcal N(\mu,\sigma)$ 写成 $a=\mu+\sigma\cdot\epsilon,\ \epsilon\sim\mathcal N(0,1)$，使梯度能穿过采样回传到 $\mu,\sigma$。SAC/VAE 用它对随机策略做低方差梯度估计。 |
| squashing (tanh) | 压缩（tanh） | 把高斯动作经 $\tanh$ 映到有界区间 $[-1,1]$ 以满足动作约束。需对 log-prob 做雅可比修正 $\log(1-\tanh^2 a)$，SAC 的实现细节。 |
| DDPG / TD3 | —— | 确定性策略梯度的连续控制算法。DDPG（Lillicrap 2015）actor 输出确定动作 + critic；TD3（Fujimoto 2018）加双 Q、目标策略平滑、延迟更新修 DDPG 的过估计与脆弱。 |
| GRPO | 群体相对策略优化 | 去掉价值网络、用同一提示下多条采样的组内相对优势做基线的策略优化（DeepSeek）。RLHF/推理 RL 常用，详见 C22；与本课 PPO 同源。 |

## 离线强化学习 · Offline RL

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| offline / batch RL | 离线 / 批量 RL | 只给一个固定的、别人采好的数据集，训练中不许再与环境交互。贴近医疗、自动驾驶、推荐等「试错代价高」的现实，但失去了纠错性探索，分布偏移成为核心难题。 |
| distribution shift | 分布偏移 | 学到的策略想执行的动作分布，偏离了数据集里行为策略的分布。一旦策略偏到数据稀疏处，值估计无从校验，错误被自举放大。离线 RL 的万恶之源。 |
| extrapolation error | 外推误差 | 在数据集没覆盖的 (s,a) 上，Q 网络只能外推、且无真实回报来纠正。$\max_a Q$ 会专挑这些被高估的 OOD 动作，导致策略追逐幻觉价值。 |
| OOD action (out-of-distribution) | 分布外动作 | 行为策略几乎没在该状态尝试过的动作。离线 RL 的危险全在这里：对它们的 Q 估计不可信，却最容易被 max 选中。 |
| behavior cloning (BC) | 行为克隆 | 把离线数据当监督学习，直接模仿 $\pi(a\vert s)\approx$ 数据中的动作。简单稳健，但天花板是数据的平均水平，无法超过示范者，也不会「拼接」次优轨迹。 |
| behavior policy $\pi_\beta$ | 行为策略 | 采集离线数据集所用的（未知）策略。离线算法的约束大多围绕「别离 $\pi_\beta$ 的支撑集太远」展开。 |
| policy constraint | 策略约束 | 显式限制学到的策略接近行为策略（如 KL、MMD、BC 正则项）。BCQ/BEAR/TD3+BC 等的思路：在数据支撑内改进，避开 OOD。 |
| CQL (Conservative Q-Learning) | 保守 Q 学习 | 在标准 TD 损失上加一项，主动压低 OOD 动作的 Q、抬高数据内动作的 Q（Kumar 2020）。学到一个真实值的下界，从根上杜绝「追逐高估的 OOD 动作」。 |
| IQL (Implicit Q-Learning) | 隐式 Q 学习 | 用 expectile 回归学值函数、完全不查询 OOD 动作的 Q（Kostrikov 2021）：只用数据内样本，靠 expectile 近似「数据内的最优」，再用优势加权回归抽策略。简单稳健。 |
| expectile regression | expectile 回归 | 非对称平方损失（权重 $\tau$ 偏向高估/低估侧）。$\tau\to1$ 的 expectile 近似最大值——IQL 用它在「只看数据内动作」的前提下逼近 $\max_a Q$，绕开 OOD 查询。 |
| advantage-weighted regression (AWR/AWAC) | 优势加权回归 | 用 $\exp(A/\beta)$ 作权重的加权行为克隆抽取策略：多模仿优势高的数据动作。IQL/AWAC 的策略抽取步，把「评估」与「不碰 OOD」解耦。 |
| D4RL | —— | 离线 RL 的标准基准数据集集合（Fu 2020），含 MuJoCo 运动、迷宫、机械臂等多种数据质量（random/medium/expert/混合）。论文里的离线分数大多在它上面报。 |

## 基于模型与世界模型 · Model-Based RL & World Models

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| model-based RL (MBRL) | 基于模型的 RL | 先学一个环境动态模型 $\hat T(s'\vert s,a)$、$\hat r(s,a)$，再用它做规划或生成想象经验来训练策略。通常比无模型法采样高效得多，但受模型误差拖累。 |
| dynamics model | 动态模型 | 预测「给定 (s,a) 下一状态与奖励」的学习模型。可确定性（回归 $s'$）或概率性（输出分布）。模型质量直接决定规划/想象的可信度。 |
| model-free vs model-based | 无模型 vs 有模型 | 无模型直接从经验学 $V/Q/\pi$（DQN/PPO/SAC），简单但费样本；有模型多学一个动态模型换取样本效率，代价是误差与复杂度。两者可混合（Dyna）。 |
| planning | 规划 | 在（学到的或已知的）模型里前瞻搜索/优化动作序列，而非靠试错。MPC、蒙特卡洛树搜索（MCTS）、值迭代都是规划。 |
| MPC (Model Predictive Control) | 模型预测控制 | 每步在模型里向前模拟若干候选动作序列、选首步最优者执行，下一步用新观测重新规划（滚动时域）。只执行第一步是它对模型误差的天然鲁棒性来源。 |
| random shooting / CEM | 随机打靶 / 交叉熵法 | 两种在 MPC 里搜动作序列的采样优化器。随机打靶：随机采一批序列、选回报最高者；CEM：迭代地把采样分布往高回报序列收紧。无需梯度、易实现。 |
| Dyna | —— | Sutton 的经典框架：交错进行「真实交互 + 用模型生成模拟经验」，两种经验都拿去更新同一个值/策略。少量真实样本 + 大量廉价模拟，提升样本效率。 |
| model error / compounding error | 模型误差 / 误差累积 | 单步预测的小误差在多步 rollout 中逐步放大（误差进入下一步输入，再被放大），导致长程想象失真。限制规划/想象的有效步数 $H$ 是主要对策。 |
| world model | 世界模型 | 学习环境的生成式模型（常在压缩的 latent 空间），让智能体能「在脑中模拟/想象」并在想象里训练策略（Ha & Schmidhuber 2018）。是把感知、记忆、规划统一起来的雄心方向。 |
| latent dynamics | 潜在动态 | 把高维观测编码到低维 latent，并在 latent 空间预测演化。比在像素空间预测更高效、更平滑，是 Dreamer/PlaNet 等的核心。 |
| Dreamer | —— | 在学到的 latent 世界模型里「想象」长程 rollout、用 actor-critic 在想象中训练策略的算法（Hafner 2020+）。靠想象大幅减少真实交互，是当代世界模型 RL 的代表。 |
| imagination / rollout in model | 想象 / 模型内推演 | 不与真实环境交互，纯在动态模型里向前生成轨迹用于训练或规划。世界模型方法把大部分学习挪进想象里完成。 |
| sample efficiency | 样本效率 | 达到某性能所需的真实环境交互量。是 RL 落地的关键瓶颈；基于模型/世界模型的主要卖点就是用模型换取更高的样本效率。 |

## 探索、多智能体与决策序列建模 · Exploration, MARL & Sequence Modeling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| exploration vs exploitation | 探索 vs 利用 | RL 的根本张力：利用已知最优动作拿当下回报，还是探索未知动作搏取更高的长远回报。稀疏奖励下纯利用会卡死，需要系统化探索。 |
| sparse reward | 稀疏奖励 | 绝大多数步奖励为零、只有少数关键状态才给信号（如「到终点 +1」）。朴素 ε-贪婪几乎不可能撞到信号，是探索研究的主战场。 |
| intrinsic reward / motivation | 内在奖励 / 内在动机 | 智能体自造的、奖励「新颖/惊讶」的额外奖励信号，加到稀疏的外在奖励上驱动探索。count-based、好奇心、RND 都属此类。 |
| count-based exploration | 基于计数的探索 | 给访问次数少的状态更高的探索奖励，如 $r^+\propto1/\sqrt{N(s)}$。表格直接计数；大/连续状态空间需用伪计数或哈希近似。 |
| RND (Random Network Distillation) | 随机网络蒸馏 | 用一个固定随机网络的输出作目标、训练一个预测网络去拟合它；预测误差大 = 状态新颖 = 内在奖励高（Burda 2018）。优雅地把「新颖性」变成可学的回归误差，无需密度估计。 |
| curiosity / ICM | 好奇心 / 内在好奇模块 | 用「预测自己动作后果的误差」作内在奖励（Pathak 2017）。在 latent 特征空间预测下一状态，预测不准处即值得探索；并用逆模型滤掉与控制无关的噪声。 |
| novelty / pseudo-count | 新颖性 / 伪计数 | 衡量状态「有多没见过」。连续空间无法精确计数，用密度模型/哈希/RND 误差等给出伪计数，作为内在奖励的依据。 |
| MARL (Multi-Agent RL) | 多智能体强化学习 | 多个学习中的智能体共处一环境，彼此的策略互为环境的一部分。带来非平稳、信用分配、合作/竞争、均衡等独有难题。 |
| non-stationarity (MARL) | 非平稳性 | 在 MARL 中，因为别的智能体也在学习、其策略在变，单个智能体眼中的环境转移与奖励随时间改变，破坏了单体 RL 的平稳 MDP 假设。 |
| CTDE (Centralized Training, Decentralized Execution) | 集中训练、分散执行 | MARL 常用范式：训练时可用全局信息（如联合观测/动作）学，执行时每个智能体只靠自己的局部观测行动。QMIX/MADDPG 等的框架。 |
| self-play | 自我博弈 | 让智能体与自己（的历史版本）对战来产生越来越强的对手与课程。AlphaGo/AlphaZero、围棋/星际等的关键，自动生成难度递增的训练信号。 |
| Nash equilibrium | 纳什均衡 | 博弈中无人能单方面改策略获益的策略组合。竞争性 MARL 的解概念之一；一般和博弈里均衡的存在与求解远比单体最优复杂。 |
| Decision Transformer (DT) | 决策 Transformer | 把 RL 重铸成序列建模：把 (回报-to-go, 状态, 动作) 序列喂给 Transformer 自回归预测动作（Chen 2021）。训练就是监督学习，推理时给定目标回报「条件生成」动作。 |
| return-to-go (RTG) | 剩余回报 | 从当前步到回合结束的回报之和。DT 把它作为「想要达到多少回报」的条件 token 输入，靠它在推理时指定希望的表现水平。 |
| upside-down RL / RvS | 颠倒的 RL / 监督式 RL | 把 RL 反过来：不学「在状态下选什么动作最大化回报」，而学「要达到某回报、在某状态下该输出什么动作」，用纯监督学习做（Schmidhuber 2019；Emmons 2021 RvS）。DT 是其代表实现。 |
| trajectory stitching | 轨迹拼接 | 把不同次优轨迹中的好片段「缝」成一条更优轨迹的能力。是值方法（动态规划）相对纯序列建模/BC 的关键优势；DT 在这点上较弱，是其已知局限。 |
