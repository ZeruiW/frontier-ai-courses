# 术语词典 · Glossary（推理模型 RL：o1/o3/R1 前沿）

> 按主题分组，每条 2–3 句释义。读 DeepSeek-R1 / o1 报告、GRPO / PRM / TTC scaling 论文遇到生词回这里查；英文术语保留原文（这是社区与论文的通用语言）。本课用 numpy 在 CPU 上玩具化模拟这些概念，但术语与真实训练栈（trl / verl / OpenRLHF）一一对应。

## 推理模型与范式 · Reasoning Models & Paradigm

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| reasoning model | 推理模型 | 在给出最终答案前先生成一长串中间推理（思维链）的模型，如 OpenAI o1/o3、DeepSeek-R1。它把「想清楚再答」内化进权重，而非靠提示词临时诱导，推理质量随测试时计算单调提升。 |
| chain-of-thought (CoT) | 思维链 | 模型在答案之前显式写出的逐步推理过程。短 CoT 是几句提示；推理模型的 long CoT 含尝试、回溯、自我检查、换路，可达数千 token。 |
| long CoT | 长思维链 | 推理模型特有的、自发变长的推理轨迹，常表现出反思（reflection）、验证、纠错、探索多解等行为。本课核心问题之一：为什么只奖励最终答案，长 CoT 会自发涌现。 |
| RLHF (RL from Human Feedback) | 人类反馈强化学习 | 用人类偏好训练奖励模型、再用 PPO 优化策略的对齐范式（InstructGPT）。它优化的是「人类觉得好」，而推理 RL 优化的是「答案客观正确」，奖励信号性质不同。 |
| RLVR (RL with Verifiable Rewards) | 可验证奖励强化学习 | 用「答案能被程序自动判对错」的任务（数学、代码、形式证明）做 RL 的范式。奖励来自验证器而非人类偏好模型，几乎无法被风格性地 hack，是 o1/R1 能力的来源。 |
| outcome reward (ORM) | 结果奖励 | 只看最终答案对错给出的标量奖励（对=1，错=0），不管中间推理过程。最易获得、最难 hack，是 R1-Zero 的唯一信号。 |
| R1-Zero | DeepSeek-R1-Zero | DeepSeek 的实验：直接在基座模型上用纯 RL（仅结果奖励，无任何人类示范/SFT 冷启动）训练，自发涌现长 CoT 与反思行为。证明推理能力可以「激励」出来而非「教」出来。 |
| cold start / SFT warmup | 冷启动 / 监督微调预热 | 正式 RL 前先用少量高质量 CoT 数据做监督微调，给策略一个像样的起点。R1（区别于 R1-Zero）用它换取可读性与稳定性，代价是引入人类先验。 |
| emergence | 涌现 | 某种能力/行为不是被显式训练，而是在优化一个简单目标（如「答对」）的过程中作为副产品出现。长 CoT、反思、自我验证在结果奖励 RL 下的出现即典型涌现。 |
| inference-time / test-time compute | 推理时 / 测试时计算 | 模型在回答单个问题时花费的计算量（生成的 token 数、采样的样本数、搜索的宽度/深度）。推理模型的关键转变：把算力从「训练时一次性」挪一部分到「推理时按需」。 |

## 策略梯度与 RL 基础 · Policy Gradient & RL Basics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| policy / πθ | 策略 | 给定状态（已生成的上下文）输出下一动作（下一 token）概率的模型。RL 的优化对象。本课用一个 softmax 参数表格当玩具策略。 |
| trajectory / rollout | 轨迹 / 推演 | 从初始状态按策略采样到终止的一整条状态-动作序列（在 LLM 里就是一次完整生成）。奖励通常只在轨迹末端（答对/错）给出。 |
| return / reward-to-go | 回报 / 剩余回报 | 从某时刻起累计的（折扣）奖励。结果奖励下，整条轨迹的每一步共享同一个末端回报。 |
| policy gradient | 策略梯度 | 直接对「期望回报」关于策略参数求梯度并上升的一类方法。核心恒等式 $\nabla_\theta J=\mathbb{E}[\,R\,\nabla_\theta\log\pi_\theta(a\mid s)\,]$：把高回报动作的对数概率推高。 |
| REINFORCE | REINFORCE | 最基础的策略梯度算法（Williams 1992）：用蒙特卡洛回报 $R$ 直接作为权重乘以 $\nabla\log\pi$。无偏但方差大，需要基线（baseline）降方差。 |
| log-derivative trick | 对数导数技巧 | $\nabla_\theta\pi=\pi\,\nabla_\theta\log\pi$，把对采样分布求梯度变成可用样本估计的期望。所有策略梯度算法的数学地基。 |
| baseline | 基线 | 从回报里减去的、与动作无关的量 $b(s)$，用于降低策略梯度方差且不引入偏差（因 $\mathbb{E}[b\nabla\log\pi]=0$）。组均值、价值网络都是基线的实例。 |
| advantage $A(s,a)$ | 优势 | 某动作比该状态「平均」好多少：$A=Q(s,a)-V(s)$ 或 $R-b$。策略梯度用优势替代裸回报，是降方差的核心。GRPO 的优势来自组内归一化。 |
| critic / value network | 价值网络 | 估计状态价值 $V(s)$ 作为基线/优势计算的网络（PPO 用）。它本身要训练、占显存、可能估错。GRPO 的卖点正是去掉它。 |
| variance reduction | 方差缩减 | 在不改变期望（无偏）的前提下降低梯度估计方差的一切手段：基线、优势归一化、组采样、控制变量。RL 能否训稳的关键。 |
| credit assignment | 信用分配 | 把末端的成功/失败归因到中间哪些动作的问题。结果奖励把功劳均摊给所有 token（粗），PRM 试图给到具体步骤（细）。 |
| on-policy / off-policy | 同策略 / 异策略 | 数据是否由当前策略产生。纯策略梯度是 on-policy（用完即弃）；PPO/GRPO 用 importance ratio 在少量 off-policy 更新里复用同一批 rollout。 |
| KL divergence (to reference) | KL 散度（对参考） | 衡量当前策略与一个冻结参考策略（通常是 SFT 模型）的差异。作为正则项拉住策略，防止它为追奖励而崩坏语言能力或遗忘。 |

## GRPO 与 PPO · GRPO & PPO

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| PPO (Proximal Policy Optimization) | 近端策略优化 | Schulman 2017 的主流 RL 算法：用 clipped surrogate 限制每步策略更新幅度，配 GAE 优势与 critic。RLHF 的标配，但需训练 critic、调参多。 |
| GRPO (Group Relative Policy Optimization) | 组相对策略优化 | DeepSeekMath 提出：对同一问题采样一组（如 8–64 条）答案，用组内回报的均值/标准差归一化得到优势，<strong>彻底去掉 critic</strong>。省一半显存、更稳，是 R1 的训练主力。 |
| group / group sampling | 组 / 组采样 | GRPO 对每个 prompt 采样 $G$ 条独立轨迹构成一组。组内互为基线——这是「相对」二字的来源，也是无需价值网络的关键。 |
| group-relative advantage | 组相对优势 | $A_i=(r_i-\text{mean}(\{r_j\}))/(\text{std}(\{r_j\})+\epsilon)$：一条轨迹的回报减组均值、除组标准差。把「绝对答对」变成「在这组里相对好坏」，天然零均值、单位方差。 |
| importance sampling ratio | 重要性采样比 | $\rho=\pi_\theta(a)/\pi_{\theta_{old}}(a)$：新旧策略对同一动作的概率比，用于在旧数据上估计新策略的期望，使一批 rollout 可做多步更新。 |
| clipped surrogate objective | 裁剪代理目标 | $\min(\rho A,\ \text{clip}(\rho,1-\epsilon,1+\epsilon)A)$：当 ratio 偏离 1 太多时削掉梯度，防止单步更新过猛、策略崩塌。PPO 与 GRPO 共用。 |
| clip range $\epsilon$ | 裁剪范围 | ratio 允许偏离 1 的幅度（典型 0.2）。太小学得慢，太大可能崩。GRPO 有时用非对称 clip（DAPO 的 clip-higher）鼓励探索。 |
| KL penalty coefficient $\beta$ | KL 惩罚系数 | 加在目标里的 KL 正则权重。$\beta$ 大→策略更贴参考、更保守；小→更敢探索但可能崩语言。R1 把它调得很小甚至阶段性关掉。 |
| reference policy | 参考策略 | 计算 KL 正则用的冻结模型（通常初始 SFT 策略）。它定义「别跑太远」的锚点。 |
| token-level vs sequence-level loss | 词级 vs 序列级损失 | 优势/损失按每个 token 平均还是按整条序列平均。GRPO 原版按序列；DAPO 改为 token-level 以避免长序列被稀释，是工程上的重要细节。 |
| reward normalization | 奖励归一化 | 把一组奖励减均值除标准差（或仅减均值）。GRPO 的组归一化即其特例；不当的归一化会引入偏差或在全对/全错组上数值不稳。 |
| RLOO (REINFORCE Leave-One-Out) | 留一法 REINFORCE | GRPO 的近亲：用「组内除自己之外」其余样本的均值当基线，避免「自己也在均值里」的轻微偏差。与 GRPO 同属「用采样基线替代 critic」的家族。 |
| ReMax | ReMax | 另一种去 critic 的方差缩减：用贪心（greedy）解码得到的回报作为基线。思想同样是「找一个无需训练的合理基线」。 |

## 过程奖励与验证 · Process Reward & Verification

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| verifier | 验证器 | 判断/打分候选解的组件。可以是规则（数学答案精确匹配、代码跑测试）、也可以是学习的模型（ORM/PRM）。RLVR 的奖励来源。 |
| ORM (Outcome Reward Model) | 结果奖励模型 | 学习预测「整条解最终对不对」的模型，对每个候选输出一个标量分。用于 best-of-N 重排；只看结果、不看过程。 |
| PRM (Process Reward Model) | 过程奖励模型 | 给推理的<strong>每一步</strong>打分（这步对/有希望吗）的模型。比 ORM 信号更密、信用分配更准，但标注成本高（Lightman 2023 证明其在数学上优于 ORM）。 |
| step-level label | 步级标签 | PRM 训练所需的「某一步好不好」的监督信号。人工标注昂贵；Math-Shepherd 用自动 MC 估计代替。 |
| Math-Shepherd | Math-Shepherd | Wang 2024 提出的<strong>自动</strong>步级标注法：从某一步出发多次 rollout 到底，用「答对的比例」作为该步的软价值标签，无需人工标注。 |
| Monte-Carlo (MC) estimation | 蒙特卡洛估计 | 用大量随机采样的平均近似一个期望。Math-Shepherd 用它估计「从这一步还能不能走到正确答案」的概率。 |
| soft label | 软标签 | 取值在 [0,1] 连续区间（而非 0/1 硬标签）的监督目标。MC 答对比例就是天然的软标签，比硬标签信息更丰富、训练更稳。 |
| aggregation (min / prod / mean / last) | 聚合 | 把一条解的多个步级分数合成一个解级分数的方式。min/prod 强调「一步错全错」（适合需步步正确的证明），mean/last 更宽松。聚合方式显著影响 best-of-N 表现。 |
| reward hacking | 奖励黑客 | 策略找到「奖励高但并非真正解对问题」的捷径（如迎合 PRM 的表面模式、复读触发词）。学习的奖励越被优化越易被 hack，是 PRM 的主要风险。 |
| Goodhart's law | 古德哈特定律 | 「当一个度量成为目标，它就不再是好度量。」过度优化一个代理奖励（如 PRM 分），真实任务表现会先升后降，呈<strong>倒 U 形</strong>。 |
| over-optimization | 过度优化 | 对代理奖励（PRM/ORM/RM）优化过头，KL 越偏离参考、代理分越高，但真实性能反而下降的现象。需用 KL 正则或早停控制。 |
| process vs outcome supervision | 过程 vs 结果监督 | 两种监督粒度之争：过程监督（PRM）credit 更准、更可解释、更安全；结果监督（ORM）更易得、更难 hack。前沿做法常二者结合。 |

## 搜索与测试时计算 · Search & Test-Time Compute

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| best-of-N (BoN) | N 选优 | 采样 N 个候选解，用 verifier（ORM/PRM）选打分最高的一个。简单强力，但需要一个好 verifier；其上界是 pass@N。 |
| self-consistency / majority vote | 自洽 / 多数投票 | 采样 N 条解、对<strong>最终答案</strong>取众数（Wang 2022）。不需 verifier、仅靠答案聚合，对有唯一答案的任务极有效，是最易部署的 TTC 方法。 |
| weighted majority vote | 加权多数投票 | 多数投票的加权版：每条解按 verifier 分数投票而非每条一票。结合了投票的鲁棒与 verifier 的判别力，常优于二者单用。 |
| pass@k | pass@k | k 个独立样本里<strong>至少一个正确</strong>的概率。衡量「能力上界」（有一个对就行，如代码可跑测试筛）；随 k 单调升，但不可直接部署（部署得选一个答案）。 |
| pass^k / all-correct@k | pass 的 k 次方 | k 个样本<strong>全部正确</strong>的概率，衡量稳定性/可靠性。与 pass@k 相反方向，随 k 单调降。可靠性敏感场景（agent 多步）关心它。 |
| unbiased pass@k estimator | 无偏 pass@k 估计 | 用 $n$ 个样本里 $c$ 个正确，估计 pass@k 的无偏公式 $1-\binom{n-c}{k}/\binom{n}{k}$（Chen 2021/Codex）。直接用 $1-(1-\hat p)^k$ 在小样本下有偏。 |
| beam search | 束搜索 | 维持宽度 $b$ 的部分解集合、每步扩展并按（过程）打分保留 top-$b$。比独立采样更系统地探索，配 PRM 即「PRM-guided beam search」。 |
| verifier-guided search | 验证器引导搜索 | 用 verifier 的打分指导生成过程（剪枝、重排、扩展哪个分支），而非仅在末端筛选。beam/lookahead/MCTS 都属此类。 |
| MCTS (Monte-Carlo Tree Search) | 蒙特卡洛树搜索 | 选择-扩展-模拟-回传四步在解空间建树搜索的算法（AlphaGo 系）。用于推理时，把 PRM 当价值、把生成当策略，深度探索；成本高。 |
| test-time compute scaling | 测试时计算 scaling | 准确率随推理算力（样本数/搜索宽度/CoT 长度）单调提升的经验规律。是推理模型相对传统「一次前向」的根本新维度。 |
| compute-optimal allocation | 计算最优分配 | 在固定总算力预算下，如何在「更大模型 vs 更多采样」「更宽搜索 vs 更深 CoT」之间分配以最大化准确率（Snell 2024）。常依赖问题难度。 |
| difficulty routing | 难度路由 | 按问题难度分配算力：易题少采样/不搜索、难题多采样/深搜索。比「一刀切预算」显著更 compute-optimal。 |
| Pareto frontier | 帕累托前沿 | 「准确率 vs 算力」平面上不被任何其他方案同时支配的点集。比较「小模型+大量 TTC」与「大模型+少量 TTC」时，看谁的前沿更靠左上。 |
| inference scaling law | 推理 scaling 律 | 描述准确率/误差随测试时计算变化的定量关系（常近似对数线性或幂律）。让我们能<strong>外推</strong>「再加一倍算力值不值」。 |
| sequential vs parallel TTC | 串行 vs 并行测试时计算 | 并行 = 独立采样多条再聚合（BoN/投票）；串行 = 在一条链里反复修订（self-refine/revision）。Snell 2024 指出二者最优配比随难度变化。 |
| self-refine / revision | 自我修订 | 模型读自己的上一版答案与（可能的）反馈，串行地产出改进版。把算力用在「改」而非「重抽」，对某些难题更有效。 |

## 真实系统与工具 · Systems & Tooling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| GSM8K | GSM8K | Cobbe 2021 的小学数学应用题数据集（8.5K 题），含 `####` 标注的最终数值答案与 `<<算式=结果>>` 步骤。是可验证奖励、verifier、TTC 实验的标准试金石。 |
| MATH / AIME | MATH / AIME | 更难的竞赛数学数据集（MATH 5 难度级；AIME 美国数学邀请赛）。o1/R1 的招牌基准，难度足以拉开 TTC scaling 曲线。 |
| trl / verl / OpenRLHF | —— | 主流开源 RL 训练框架：trl（HuggingFace，含 GRPOTrainer/PPOTrainer）、verl（火山引擎，volcano engine RL，工业级 PPO/GRPO）、OpenRLHF。本课 numpy 实现的算法对应它们的核心循环。 |
| rule-based reward | 规则奖励 | 不用学习模型、直接用程序判分的奖励（答案正则匹配、代码单测、格式检查）。R1 的主力奖励，因为它<strong>不可被 hack</strong>且零成本。 |
| format reward | 格式奖励 | 奖励模型把推理放进规定结构（如 `<think>...</think><answer>...</answer>`）。R1-Zero 用它稳定输出格式、便于抽取答案，与正确性奖励叠加。 |
| temperature / sampling | 温度 / 采样 | 控制生成随机性的标量：高温更多样（利于探索与 BoN 覆盖），低温更确定（利于最终作答）。RL 探索与 TTC 多样性都靠它调。 |
| entropy / entropy bonus | 熵 / 熵奖励 | 策略分布的不确定度。加熵奖励鼓励探索、防止过早收敛到单一模式（推理 RL 里防「熵塌缩」的常用手段）。 |
| KL coefficient annealing | KL 系数退火 | 训练中动态调整 $\beta$：早期大（稳）、后期小（放开探索），或反之。控制过度优化与探索的实用旋钮。 |
