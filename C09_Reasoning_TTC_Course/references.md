# 关键论文清单 · References（推理模型与测试时计算）

> 按模块组织。`★` = 必读里程碑。教材中 `[作者 年份]` 对应此处。
> 注：o1 等部分工业界工作无 arXiv 号，以官方链接标注。

## 00 · 总览：推理范式

- ★ OpenAI 2024, *Learning to Reason with LLMs (o1)* — openai.com/index/learning-to-reason-with-llms — 范式宣言：RL 训练长 CoT + 测试时算力换准确率，附两条 scaling 曲线（train-time 与 test-time）。
- ★ DeepSeek-AI 2025, *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning* — arXiv:2501.12948 — 第一份公开完整配方的 o1 级复现：RLVR 从 base model 直接引出长链推理（R1-Zero）、"aha moment"、蒸馏系列。
- Kimi Team 2025, *Kimi k1.5: Scaling Reinforcement Learning with LLMs* — arXiv:2501.12599 — 与 R1 同日发布的另一份配方，特色是 long2short（长度惩罚）与多模态推理 RL 细节。

## 01 · CoT 与任务分解：误差复利的数学

- ★ Wei et al. 2022, *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models* — arXiv:2201.11903 — CoT 的命名之作：few-shot 推理链示例使数学推理能力随规模涌现。
- ★ Kojima et al. 2022, *Large Language Models are Zero-Shot Reasoners* — arXiv:2205.11916 — "Let's think step by step" 一句话引出推理：CoT 能力是预训练已有的，提示只是引出。
- Nye et al. 2021, *Show Your Work: Scratchpads for Intermediate Computation with Language Models* — arXiv:2112.00114 — CoT 的前身：把中间计算外化成 token，让有限深度网络执行更长的串行计算。
- Zhou et al. 2022, *Least-to-Most Prompting Enables Complex Reasoning in Large Language Models* — arXiv:2205.10625 — 显式任务分解：先拆成由易到难的子问题再依次求解，easy-to-hard 泛化优于普通 CoT。

## 02 · Self-Consistency 与 Best-of-N

- ★ Wang et al. 2022, *Self-Consistency Improves Chain of Thought Reasoning in Language Models* — arXiv:2203.11171 — 采样多条推理链 + majority voting：最便宜也最经久耐用的 parallel scaling 方法。
- ★ Brown et al. 2024, *Large Language Monkeys: Scaling Inference Compute with Repeated Sampling* — arXiv:2407.21787 — coverage 随采样数幂律增长、跨数量级不饱和：repeated sampling 是一条真实的 scaling 轴；也指出瓶颈在 verifier。
- Cobbe et al. 2021, *Training Verifiers to Solve Math Word Problems (GSM8K)* — arXiv:2110.14168 — GSM8K 数据集 + 第一代答案 verifier + BoN reranking，本课 02/03 两个模块的共同源头。

## 03 · Verifier 与 PRM：结果监督 vs 过程监督

- ★ Lightman et al. 2023, *Let's Verify Step by Step* — arXiv:2305.20050 — PRM 对 ORM 的决定性胜利（MATH 上 78%）：步骤级监督更准、信用分配更细，附 PRM800K 数据集。
- Wang et al. 2023, *Math-Shepherd: Verify and Reinforce LLMs Step-by-step without Human Annotations* — arXiv:2312.08935 — 用蒙特卡洛 rollout 成功率自动生成步骤标签，绕开 PRM 最贵的人工标注。
- ★ Gao et al. 2022, *Scaling Laws for Reward Model Overoptimization* — arXiv:2210.10760 — Goodhart 的定量化：BoN 与 RL 下 proxy 分数与真实分数的分叉随优化强度的规律，本课 03 模块复现的目标曲线。

## 04 · 推理即搜索：beam / ToT / MCTS

- ★ Yao et al. 2023, *Tree of Thoughts: Deliberate Problem Solving with Large Language Models* — arXiv:2305.10601 — 把推理建模为树上的探索+回溯+自评估，Game of 24 上对 CoT 的碾压性证据。
- Hao et al. 2023, *Reasoning with Language Model is Planning with World Model (RAP)* — arXiv:2305.14992 — 用 MCTS 做推理规划：LLM 既当策略也当世界模型，UCT 平衡探索与利用。
- Browne et al. 2012, *A Survey of Monte Carlo Tree Search Methods* — IEEE TCIAIG — MCTS 四阶段（selection/expansion/rollout/backup）与 UCT 的标准参考，手写 MCTS 前读它。
- Silver et al. 2016, *Mastering the Game of Go with Deep Neural Networks and Tree Search (AlphaGo)* — Nature 529 — "学习的价值函数 + 搜索"组合拳的源头，推理即搜索范式的精神祖先。

## 05 · 测试时计算 Scaling Laws

- ★ Snell et al. 2024, *Scaling LLM Test-Time Compute Optimally Can Be More Effective than Scaling Model Parameters* — arXiv:2408.03314 — compute-optimal TTC：最优策略随难度变化，难度自适应的 TTC 用 4 倍少算力打平 BoN，小模型+TTC 可胜 14 倍大模型。
- ★ Wu et al. 2024, *Inference Scaling Laws: An Empirical Analysis of Compute-Optimal Inference for Problem-Solving with Language Models* — arXiv:2408.00724 — 系统刻画"模型大小 × 采样策略"的推理算力前沿：小模型+树搜索常是 Pareto 最优。
- OpenAI 2024, *Learning to Reason with LLMs (o1)* — 见 00 模块 — test-time scaling 曲线的第一份公开展示，本模块的现象学起点。

## 06 · Overthinking 与预算控制

- ★ Muennighoff et al. 2025, *s1: Simple Test-Time Scaling* — arXiv:2501.19393 — 1K 精选样本 SFT + budget forcing（"Wait" 续写 / 提前截断）：最小配方复现 test-time scaling，控制思考长度的最干净实验。
- Chen et al. 2024, *Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs* — arXiv:2412.21187 — overthinking 的命名与量化：简单题上的冗余思考、效率指标（outcome/process efficiency）与缓解方案。
- Kimi Team 2025, *Kimi k1.5* — arXiv:2501.12599（见 00 模块）— long2short 与 length penalty 的工业级实践：怎么在不砍深思的前提下压长度。

## 07 · 评测推理模型：faithfulness、污染与前沿基准

- ★ Lanham et al. 2023, *Measuring Faithfulness in Chain-of-Thought Reasoning* — arXiv:2307.13702 — faithfulness 的扰动实验方法学：truncation/paraphrase/添加错误，发现"答案常常不依赖 CoT"，且模型越大越不忠实。
- ★ Turpin et al. 2023, *Language Models Don't Always Say What They Think* — arXiv:2305.04388 — hint sensitivity 实验的源头：偏置特征改变答案但 CoT 绝口不提，事后合理化的实锤证据。
- Arcuschin et al. 2025, *Chain-of-Thought Reasoning In The Wild Is Not Always Faithful* — arXiv:2503.08679 — 无人为偏置的自然设定下也测到系统性不忠实（隐性纠错、无依据捷径），faithfulness 问题在推理模型上依然存在。
- Mirzadeh et al. 2024, *GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in Large Language Models* — arXiv:2410.05229 — 模板化扰动揭示成绩中的记忆成分：改个数字就掉分，抗污染评测的设计范本。
- Glazer et al. 2024, *FrontierMath: A Benchmark for Evaluating Advanced Mathematical Reasoning in AI* — arXiv:2411.04872 — 原创研究级数学题 + 自动验证 + 不公开题库：防饱和防污染的评测设计极限。
- Phan et al. 2025, *Humanity's Last Exam* — arXiv:2501.14249 — 跨学科专家难题的"最后一个封闭式基准"：低准确率 + 高校准误差，推理模型的谦逊测试。
