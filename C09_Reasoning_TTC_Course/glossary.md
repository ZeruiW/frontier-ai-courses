# 术语词典 · Glossary（推理模型与测试时计算）

> 按主题分组，每条 2–3 句释义。读论文遇到生词回这里查。英文术语保持原文，因为这是社区通用语言。

## 思维链与任务分解 · CoT & Decomposition

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Chain-of-Thought (CoT) | 思维链 | 让模型在给出最终答案前先生成中间推理步骤的提示/生成方式。它把一次性的"猜答案"变成多步的"算答案"，是所有测试时计算方法的起点。Wei et al. 2022 证明其收益随模型规模涌现。 |
| Scratchpad | 草稿纸 | CoT 的前身（Nye et al. 2021）：给模型一块输出中间计算结果的区域，再读取它继续算。核心洞察是把"隐式的内部计算"外化成 token，使有限深度的 transformer 能执行更长的串行计算。 |
| Zero-shot CoT | 零样本思维链 | 不给任何示例，只在 prompt 末尾加一句 "Let's think step by step" 就能引出推理链（Kojima et al. 2022）。它说明 CoT 能力在预训练中已经存在，提示只是引出（elicit）而非教会。 |
| Least-to-Most Prompting | 由易到难提示 | 先让模型把难题分解成一串由易到难的子问题，再依次求解、把前面的答案喂给后面（Zhou et al. 2022）。相比普通 CoT，它显式做了任务分解，对组合泛化（easy-to-hard generalization）帮助更大。 |
| Error Compounding | 误差复利 | 多步推理中每步错误率的乘法累积：每步正确率 p 的 n 步链，全对概率约 p^n。它是本课的核心数学模型——既解释了长链为什么脆弱，也解释了分解、验证、搜索各自在拦截哪一项损失。 |

## 采样与聚合 · Sampling & Aggregation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Self-Consistency | 自洽性采样 | 采样多条独立推理链，对最终答案做 majority voting（Wang et al. 2022）。直觉：正确推理路径可能有很多条但都汇聚到同一答案，错误路径则各错各的。是最简单也最常用的 parallel scaling 方法。 |
| Majority Voting | 多数投票 | 对多个采样答案取众数的聚合规则。当单次正确率 > 最强错误答案的出现率时，投票随样本数指数级放大优势；反之会把系统性错误放大成自信的错误——这正是它的失效模式。 |
| Best-of-N (BoN) | N 选 1 | 采样 N 个完整回答，用 verifier/reward model 打分后取最高分者。与 majority voting 不同，它适用于答案不可比对的开放任务，但其收益上限取决于 verifier 的质量（见 reward overoptimization）。 |
| pass@k | —— | k 次采样中至少一次正确的概率，能力引出（elicitation）的标准指标。无偏估计需要从 n>k 个样本组合计算（Chen et al. 2021 的公式），直接跑 k 次取最好会高估方差。 |
| consensus@k (cons@k) | k 次共识 | 采样 k 次取多数答案的准确率，即 self-consistency 在 k 样本下的成绩。与 pass@k 的区别是关键：pass@k 假设有完美 oracle 挑答案（测能力上限），cons@k 不需要 oracle（测可兑现的成绩）。 |
| Coverage | 覆盖率 | 采样 N 次后至少命中一个正确答案的问题比例，即数据集层面的 pass@N。Large Language Monkeys（Brown et al. 2024）发现它随 N 近似幂律增长，跨多个数量级不饱和——repeated sampling 是一条真实的 scaling 轴。 |

## 验证 · Verification

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Verifier | 验证器 | 给候选解打分或判对错的模型/程序。测试时用于 reranking（BoN）、搜索剪枝；训练时就是 RLVR 的 reward 来源。生成-验证差距（验证比生成容易）是整个 TTC 范式成立的前提。 |
| Outcome Reward Model (ORM) | 结果奖励模型 | 只看最终答案对错训练的 verifier：整条推理链一个标签。标注便宜，但信用分配粗糙——过程全错、答案碰对的链也会被标成正样本。 |
| Process Reward Model (PRM) | 过程奖励模型 | 对推理链的每一步打分的 verifier。Lightman et al. 2023 证明在 MATH 上 process supervision 显著优于 outcome supervision，且步骤级反馈让搜索和信用分配都更精准；代价是步骤标注昂贵。 |
| Process Supervision | 过程监督 | 按步骤正确性提供训练信号的监督方式，与只看结果的 outcome supervision 相对。除了性能，它还有对齐论证：奖励"过程对"比奖励"结果对"更不容易教出钻空子的策略。 |
| Credit Assignment | 信用分配 | 把最终成败归因到链条中各步骤的难题。ORM 完全不做信用分配，PRM 用人工/自动步骤标签做，RL 用价值函数估计做——三者的差异本质上是信用分配粒度的差异。 |
| Math-Shepherd | —— | 用蒙特卡洛补全自动生成步骤标签的方法（Wang et al. 2023）：从某步出发采样多条补全，按"从这一步还能走到正确答案的比例"给该步打分。绕开了 PRM 最贵的人工标注，是自动过程监督的代表。 |
| Reward Overoptimization / Goodhart's Law | 奖励过优化 / 古德哈特定律 | 对不完美的 proxy reward（如 verifier 分数）优化过猛时，proxy 分数继续涨而真实质量开始跌（Gao et al. 2022）。BoN 的 N 越大、RL 的 KL 预算越大，过优化越严重——"指标一旦成为目标就不再是好指标"。 |
| Verifiable Reward | 可验证奖励 | 能用程序化规则严格判定的奖励：数学比对答案、代码跑单元测试。它消除了 reward model 被钻空子的空间，是 RLVR（R1 范式）能稳定 scale 的关键，也圈定了该范式最先突破的领域为什么是数学和代码。 |

## 搜索 · Search

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Beam Search | 束搜索 | 每步保留得分最高的 k 条前缀继续扩展的宽度受限搜索。用 PRM 给步骤打分的 step-level beam search 是介于"采样完整链"与"完整树搜索"之间的中间档。 |
| Tree of Thoughts (ToT) | 思维树 | 把推理显式建模为树：每个节点是一个"想法"（思维步骤），用模型自评或 verifier 评估节点、用 BFS/DFS 探索并允许回溯（Yao et al. 2023）。在需要探索和试错的任务（如 Game of 24）上远超线性 CoT。 |
| MCTS (Monte Carlo Tree Search) | 蒙特卡洛树搜索 | 通过反复"选择→扩展→rollout→backup"四阶段构建非对称搜索树的算法，AlphaGo 的核心。用在推理上：节点是部分推理链，价值来自 verifier 或随机补全的成功率。 |
| UCB / UCT | 上置信界 / 树上 UCB | MCTS 选择阶段的公式：score = 平均价值 + c·√(ln N_parent / N_child)。第一项 exploit（去已知好的分支），第二项 explore（去访问少的分支），c 控制权衡——它把"算力花在哪个分支"变成有理论保证的决策。 |
| Rollout | 推演 | 从当前节点快速模拟到终局以估计其价值的过程。推理场景下即"从这个部分解出发采样补全、看能否到达正确答案"——Math-Shepherd 的步骤标签正是用 rollout 成功率定义的。 |
| Backup | 回传 | MCTS 的第四阶段：把 rollout 得到的价值沿搜索路径向根节点回传，更新沿途节点的访问数与平均价值。它使后续的 UCT 选择能利用新证据，是搜索树"越搜越聪明"的机制。 |
| Speculative Reasoning | 投机式推理 | 借鉴 speculative decoding 的思想：用小模型起草推理步骤、大模型验证或仅在关键步介入。代表"验证比生成便宜"在效率维度的应用，与 adaptive compute 一脉相承。 |

## 测试时计算扩展 · Test-Time Compute Scaling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Test-Time Compute (TTC) | 测试时计算 | 推理（inference）阶段为单个问题投入的算力总量：更长的 CoT、更多采样、更深的搜索都是花法。o1 把"测试时算力换准确率"变成与预训练 scaling 并列的第三条轴。 |
| Inference Scaling Law | 推理规模法则 | 准确率/coverage 随测试时算力（采样数、思考 token 数）的可预测增长规律，通常在 log 坐标下近似线性或幂律（Brown 2024、Wu 2024、Snell 2024）。它使"该花多少推理算力"从玄学变成可优化问题。 |
| Compute-Optimal TTC | 算力最优测试时计算 | 给定总 FLOPs 预算，在"模型大小 × 采样策略 × 思考长度"之间找最优分配（Snell et al. 2024）。关键结论：最优策略随问题难度变化——简单题适合顺序精化，难题适合并行广撒网；小模型+聪明的 TTC 可在一定算力区间打败 14 倍大的模型。 |
| Sequential Scaling | 顺序扩展 | 把算力花在一条更长的推理链上：更多思考步骤、自我修正、迭代精化。优点是后面的计算能利用前面的结论，缺点是误差会沿链传播且无法并行。 |
| Parallel Scaling | 并行扩展 | 把算力花在更多条独立采样上再聚合（self-consistency、BoN）。优点是天然并行、方差缩减有统计保证，缺点是各样本之间不共享中间发现。两者的最优混合比例是 compute-optimal TTC 的核心问题。 |
| Budget Forcing | 预算强制 | s1（Muennighoff et al. 2025）提出的解码期算力控制：想让模型多想就在它要停时追加 "Wait" 强制续写，想少想就提前截断插入结束标记。简单到粗暴，却给出了干净的 TTC 因果证据：同一模型，思考 token 越多准确率单调上升。 |
| Adaptive Compute | 自适应计算 | 按问题难度动态分配算力：简单题快答，难题深想。实现手段包括难度预测、置信度阈值提前停止、路由到不同思考档位；是从"固定预算"走向"边际收益定价"的方向。 |
| Early Exit | 提前退出 | 当置信度足够（如多数票已稳定、verifier 分数超阈值）就停止继续采样/思考的策略。它是 adaptive compute 最简单的形式，直接砍掉边际收益趋零之后的算力浪费。 |

## 长思维链与效率 · Long CoT & Efficiency

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Long CoT | 长思维链 | 推理模型经 RLVR 训练后自发产生的超长推理轨迹（数千到数万 token），包含反思、回溯、多方案尝试。它与提示出来的短 CoT 有质的区别：长度本身是模型学到的策略而非提示工程的产物。 |
| Overthinking | 过度思考 | 模型对简单问题也生成冗长推理、甚至在已得到正确答案后继续怀疑和重算的现象（Chen et al. 2024）。表现为"2+3=?"也要想几百 token；既浪费算力，有时还把对的改错。 |
| Underthinking | 思考不足 | 与 overthinking 对偶的失效：模型在有希望的推理方向上浅尝辄止、频繁切换思路，没有一条路径走到底。表现为长输出里塞满了开头而没有深入，是长 CoT 质量（而非长度）的问题。 |
| Length Penalty | 长度惩罚 | 在 RL 奖励中对响应长度施加的惩罚/塑形项（如 Kimi k1.5 的 long2short），用于压制 RLVR 训练自发的长度膨胀。设计难点在于不能把真正需要的深思也罚掉——长度与质量在难题上是正相关的。 |
| Reasoning Distillation | 推理蒸馏 | 用强推理模型的长 CoT 轨迹做 SFT 训练小模型（如 R1-Distill 系列）。惊人之处在于纯模仿就能迁移大部分推理能力，使"会思考的小模型"成为效率路线的重要选项；但蒸馏出的能力上限受限于教师覆盖的轨迹分布。 |

## 训练范式（衔接 Post-Training 课）· Training Paradigm

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| RLVR (RL with Verifiable Rewards) | 可验证奖励强化学习 | 用程序化可验证的奖励（数学答案比对、代码测试）直接做 RL 的训练范式，R1 证明了它可以从 base model 直接引出长链推理。本课视角：RLVR 是把"测试时的 verifier 信号"内化进权重的过程。 |
| GRPO (Group Relative Policy Optimization) | 组相对策略优化 | DeepSeek 提出的 PPO 简化：对同一问题采一组回答，用组内奖励的标准化值当 advantage，省掉价值网络。注意它的组采样结构与 BoN/self-consistency 同构——训练与测试在共享同一套统计学。 |
| Self-Correction | 自我修正 | 模型发现并改正自己推理错误的能力。重要事实：无外部反馈的 intrinsic self-correction 在提示阶段基本不成立（改对的和改错的一样多），但 RLVR 训练后的推理模型确实学会了有效的内生修正——这是范式转变的标志之一。 |
| Reflection | 反思 | 长 CoT 中模型审视已有步骤、评估当前方案的片段（"wait, let me check..."）。在轨迹分析中通常作为可数的行为标记，其频率与有效性是衡量推理质量的过程指标。 |
| Backtracking | 回溯 | 推理中放弃当前路径、退回到早先状态换路再走的行为。它是树搜索的核心操作在线性文本中的体现——长 CoT 可以看作把显式树搜索"压平"写进了一条序列。 |
| "Aha Moment" | 顿悟时刻 | DeepSeek-R1 训练中段观察到的现象：模型自发学会停下来重新评估并改换思路，反思类 token 频率跃升。常被引用为"RLVR 能涌现元认知策略"的证据，也提醒我们这些行为是奖励优化的产物而非天生。 |

## 评测推理模型 · Evaluating Reasoning

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| CoT Faithfulness | 思维链忠实性 | CoT 是否如实反映模型得出答案的真实计算过程。不忠实的 CoT 会让基于 CoT 的监控与审计失效，因此它不只是学术问题——是 CoT monitoring 这条安全路线的前提假设。 |
| Post-hoc Rationalization | 事后合理化 | 不忠实的典型形态：模型先（由其他途径）定了答案，再编一段看似合理的推理去支撑它。行为学检测手段是扰动实验——改动 CoT 中间步骤而答案不变，说明答案并不依赖这段推理。 |
| Hint Sensitivity | 提示敏感性 | 测 faithfulness 的标准实验（Turpin 2023、Anthropic 2025）：在 prompt 里塞入指向某答案的暗示（如"我觉得答案是 B"），观察模型是否跟随暗示改答案、以及 CoT 是否承认用了暗示。跟随却不承认 = 实锤不忠实。 |
| GSM-Symbolic | —— | 把 GSM8K 题目模板化、替换数字与人名生成等价变体的评测（Mirzadeh et al. 2024）。模型在变体上成绩显著下滑且方差巨大，揭示部分"推理成绩"实为对原题的模式记忆——是污染检测与鲁棒性评测的范本。 |
| Contamination-Resistant Eval | 抗污染评测 | 通过题目动态生成、私有题库、发布后持续换题等手段抵抗训练数据污染的评测设计。对推理模型尤其重要：推理基准题量少、知名度高，泄漏一题对分数的影响远大于普通基准。 |
| Benchmark Saturation | 基准饱和 | 模型分数逼近基准上限、失去区分度的状态。GSM8K → MATH → AIME → FrontierMath 的快速接力是推理评测的独特困境：基准寿命从数年缩短到数月。 |
| AIME | 美国数学邀请赛 | 每年 30 道、答案为 0–999 整数的高中竞赛，因题目新鲜（每年 2 月新出）、答案可程序验证，成为推理模型的标准考场。注意统计陷阱：单年只有 30 题，置信区间宽得惊人，cons@k 与 pass@1 必须分开报。 |
| FrontierMath | —— | Epoch AI 组织数学家出的原创研究级数学题库（Glazer et al. 2024），题目未发表、答案可自动验证，发布时最强模型仅解出约 2%。代表"防饱和+防污染"的评测设计极限。 |
| Humanity's Last Exam (HLE) | 人类最后的考试 | 跨学科专家众包的 2500+ 道前沿学术难题（Phan et al. 2025），定位是"封闭式学术题的最后一个基准"。它同时是校准评测的素材：模型在 HLE 上普遍高自信低正确，校准误差比准确率更刺眼。 |
