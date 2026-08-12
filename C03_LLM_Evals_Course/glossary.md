# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读论文遇到生词回这里查。

## 统计严谨性 · Statistical Rigor

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Bootstrap | 自助法 | 对样本有放回重采样大量次数，用统计量的经验分布来估计其不确定性。 |
| Confidence Interval (CI) | 置信区间 | 量化估计不确定性的区间；95% CI 指重复实验中约 95% 的区间会覆盖真值。 |
| Standard Error (SE) | 标准误 | 统计量（如平均准确率）抽样分布的标准差，误差棒的基本单位。 |
| Paired Test | 配对检验 | 比较两个模型时按"同一道题"配对再检验差值，消掉题目难度方差，功效远高于非配对检验。 |
| McNemar's Test | McNemar 检验 | 针对配对二元结果（对/错）的检验，只看两模型"一对一错"的不一致格子。 |
| Clustered Standard Errors | 聚类标准误 | 当样本成簇相关（如同一文档出多题）时校正 SE，否则误差棒会假性变窄。 |
| Statistical Power | 统计功效 | 真实差异存在时检验能发现它的概率；决定"要多少道题才能区分两个模型"。 |
| Multiple Comparisons | 多重比较 | 同时做很多检验时假阳性率膨胀的问题，最简单的校正是 Bonferroni（α 除以检验次数）。 |
| Effect Size | 效应量 | 差异的实际大小（如准确率差几个点），与"是否显著"互补，两者都要报。 |

## LLM 评委 · LLM-as-a-Judge

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| LLM-as-a-Judge | 大模型评委 | 用强 LLM 给开放式回答打分或两两比较，替代昂贵的人工评测。 |
| Position Bias | 位置偏差 | Judge 系统性偏向某个呈现位置（如先出现的回答）的偏差，用换序测试（swap test）暴露。 |
| Length Bias | 长度偏差 | Judge 系统性偏爱更长回答的倾向，与质量无关也会加分。 |
| Self-Preference Bias | 自我偏好偏差 | Judge 偏爱自己（或同系模型）生成的回答的倾向。 |
| Cohen's κ (kappa) | Cohen's κ 系数 | 扣除随机一致后的标注一致性度量，验证 judge 与人类是否真的对齐。 |
| Inter-Annotator Agreement (IAA) | 标注者间一致性 | 多个标注者（人或 judge）对同一批样本判断的一致程度。 |
| Rubric | 评分细则 | 给 judge（或人类）的结构化打分标准，把"好"拆解成可核查的维度。 |
| Pairwise Comparison | 两两比较 | 让 judge 在两个回答中选更好的，比单点打绝对分（pointwise）更稳定。 |

## 数据污染 · Contamination

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Data Contamination | 数据污染 | 测试题（或其答案）泄漏进训练数据，导致分数虚高、不再反映泛化能力。 |
| Canary String | 金丝雀字符串 | 埋在评测集里的唯一标识串（如 BIG-bench canary），模型能复述即证明训练时见过。 |
| N-gram Overlap | n-gram 重叠 | 检测训练语料与测试集的连续 n 词重叠，最常用的污染筛查手段。 |
| No-Input Baseline | 无输入基线 | 把题干（或关键输入）抹掉再测：分数仍显著高于随机，说明模型在背答案。 |
| Benchmark Saturation | 基准饱和 | 前沿模型分数逼近天花板、benchmark 失去区分度的现象。 |
| Dynamic / Live Benchmark | 动态基准 | 持续换新题（如 LiveBench、按日期切分）以对抗污染的 benchmark 设计。 |

## 答案抽取与 Prompt · Extraction & Prompting

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Answer Extraction | 答案抽取 | 从模型自由生成的文本里解析出最终答案的步骤，写错正则会系统性冤枉模型。 |
| Prompt Sensitivity | prompt 敏感性 | 分数随模板措辞、选项顺序、格式等微小改动大幅波动的现象。 |
| Logprob-based Evaluation | 对数概率评测 | 不生成文本、直接比较各候选答案的 logprob，快且免抽取但偏离真实使用。 |
| Generative Evaluation | 生成式评测 | 让模型自由生成再抽取答案打分，贴近真实使用但引入抽取与解码噪声。 |
| Few-shot Examples | 少样本示例 | 在 prompt 里放几个带答案的例题（in-context examples）；示例数量与选择也会显著影响分数。 |

## 能力引出 · Elicitation

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Elicitation | 能力引出 | 用更好的 prompt（如 CoT）、工具、采样策略把模型潜在能力激发出来的过程。 |
| Elicitation Gap | 引出差距 | 模型潜在最佳表现与当前评测设置测出来的表现之间的差距——评测测的是下界。 |
| pass@k | —— | k 次采样中至少一次通过的概率，代码评测的标准指标。 |
| Unbiased pass@k Estimator | pass@k 无偏估计 | 采 n>k 个样本、按组合公式 1−C(n−c,k)/C(n,k) 估计 pass@k，避免直接采 k 个的偏差。 |
| Best-of-N (BoN) | N 选一 | 采 N 个回答用打分器选最好的，衡量"有验证器时"的能力上限。 |
| Scaffolding | 脚手架 | 包在模型外面的工具、重试、规划等 agent 结构，同一模型换脚手架分数可以差数倍。 |
| Sandbagging | 故意藏拙 | 模型（或被微调后）在评测中策略性表现差于真实能力，安全评测的核心威胁。 |

## Arena 与排行 · Arena & Leaderboards

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Elo Rating | Elo 等级分 | 源自国际象棋的在线更新等级分，由两两对战胜负迭代出全局排名。 |
| Bradley-Terry Model | Bradley-Terry 模型 | 从两两比较数据估计潜在实力参数的统计模型，Chatbot Arena 排名的正规做法。 |
| Chatbot Arena | 聊天竞技场 | 真实用户盲测两个匿名模型并投票的众包对战平台（LMSYS/LMArena）。 |
| Style Control | 风格控制 | 在 Arena 回归中把长度、markdown 排版等风格变量当协变量剔除，分离"实质质量"。 |
| Leaderboard Overfitting | 刷榜过拟合 | 针对某个榜单反复调优导致榜上分数与真实能力脱钩（Goodhart 定律的评测版）。 |

## Harness 工程 · Harness Engineering

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Eval Harness | 评测框架 | 把任务定义、模型调用、打分、汇总流水线化的工程框架（如 lm-evaluation-harness、Inspect）。 |
| Response Cache | 响应缓存 | 按 (模型, prompt, 解码参数) 缓存模型输出，重跑不花钱且结果可复现。 |
| Random Seed | 随机种子 | 固定采样、shuffle 等随机源的初始值，复现实验的最低要求。 |
| Reproducibility | 可复现性 | 别人（或未来的你）用同样配置能得到同样分数的性质，harness 设计的第一目标。 |
| Task Specification | 任务规约 | 一个 eval 的完整声明：数据、模板、解码参数、打分器（scorer）、指标，缺一项结果就不可比。 |

## 报告与效度 · Reporting & Validity

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Eval Card | 评测卡 | 随评测结果发布的结构化文档：任务定义、设置、误差棒、已知局限，类比 model card。 |
| Error Bars | 误差棒 | 图表上表示估计不确定性的区间标记，没有误差棒的 benchmark 对比图不可信。 |
| Construct Validity | 构念效度 | 评测真的在测它声称要测的能力吗——benchmark 设计的根本问题。 |
| Time Horizon (METR) | 时间跨度 | 用"模型能以 50% 成功率完成的人类任务时长"来刻画 agent 能力的指标。 |
| Capability vs. Propensity | 能力 vs 倾向 | "模型能不能做到"与"模型默认会不会去做"是两种不同的测量对象，报告时必须区分。 |
