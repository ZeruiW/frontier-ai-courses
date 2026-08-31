# 参考清单 · References（LLM-as-a-Judge 与评分模型）

> ★ 标必读。每条注明「解决什么问题」——这份清单不是让你把论文读一遍，
> 而是让你在被追问「这个做法有没有依据」时，知道**这不是我编的，有原始出处**。
> 本课把这些材料重新组织成了「仪器 → 设计 → 去偏 → 元评测 → 排名 → 训练信号」这条主线。

---

## 一 · LLM judge 的奠基工作 · Foundations

- ★ **Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, et al., _Judging LLM-as-a-Judge with MT-Bench
  and Chatbot Arena_（NeurIPS 2023 Datasets & Benchmarks）** —
  解决三件事，而且是本课引用最多的一篇：
  **① 系统性地命名并测量了位置偏差、长度偏差、自偏好偏差**（本课模块 02 的四大偏差里有三个出自这里）；
  **② 给出了 judge 与人类一致率、以及人类之间一致率的对照**（模块 03「人类上界」的直接来源）；
  **③ 对比了 pairwise 与 single-answer grading 两种用法**（模块 01 第 2–3 节）。
  如果这份清单只读一篇，读这篇。
- ★ **Cheng-Han Chiang & Hung-yi Lee, _Can Large Language Models Be an Alternative to Human
  Evaluations?_（ACL 2023）** —
  解决「LLM 评测能不能替代人类评测」这个总问题，并给出了两者在何种任务上一致、
  何种任务上分歧的经验证据。**本课「先问 judge 要和谁对齐」这一节的问题意识来自这篇。**
- **Yang Liu, Dan Iter, Yichong Xu, et al., _G-Eval: NLG Evaluation using GPT-4 with Better
  Human Alignment_（EMNLP 2023）** —
  解决「pointwise 打分的分数分布压缩」：用 CoT + **token 概率加权**把整数分变成连续分。
  本课模块 01 把它列为缓解手段之一，同时提醒它**要求能拿到 logprobs**，
  且「模型对分数的不确定性」不等于「质量的中间态」。
- **Seungone Kim, Jamin Shin, Yejin Cho, et al., _Prometheus_ 系列（2023 / 2024）** —
  解决「怎么用细粒度 rubric + 参考答案做出可复现的开源 judge」。
  **本课模块 01 第 4–5 节的 rubric 设计原则与参考答案的双刃效果，与这条线索直接呼应。**
- **Jeffrey Zhou, Tianjian Lu, Swaroop Mishra, et al., _IFEval: Instruction-Following Eval_（2023）** —
  解决「哪些指令可以被程序自动验证」。它的思想是本课模块 00 第 2 节
  「能写成校验就不要用 judge」的直接依据，也是模块 05 RLVR 边界的前身。

## 二 · 偏差与去偏 · Bias & Debiasing

- ★ **Yann Dubois, Balázs Galambosi, Percy Liang, Tatsunori Hashimoto,
  _Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators_（2024）** —
  解决「怎么把长度偏差从胜率里回归掉」：把长度差作为协变量放进逻辑回归，
  拟合完把长度差置 0。**本课模块 02 第 3 节与模块 04 第 7 节的方法直接来自这篇**。
  它最重要的性质是「没有偏差时自动退化成不做任何事」。
- ★ **Arjun Panickssery, Samuel R. Bowman, Shi Feng,
  _LLM Evaluators Recognize and Favor Their Own Generations_（NeurIPS 2024）** —
  解决「自偏好是不是真的存在，机制是什么」：给出了**自我识别能力与自偏好强度相关**的证据。
  本课模块 02 第 4 节的四种实验设计（交叉评审 / 人类锚定 / 风格迁移 / 识别度关联）以此为基础。
- **关于位置偏差与顺序敏感性的一系列后续工作（如 Wang et al. 的 fairness/校准提议）** —
  解决「swap 之后不一致的样本怎么处理」。本课采用最保守的做法（记平局），
  并强调 **swap 一致率本身必须被报告**——低于 0.80 时胜率数字不可用。
- **关于 judge 对权威、从众、身份等无关信息敏感的实证工作** —
  解决「除了位置/长度/风格，还有哪些表面属性会影响 judge」。
  本课把它们统一到模块 02 第 6 节的**反事实探针范式**下：
  造一批只差某个属性的成对样本，做配对检验。

## 三 · 元评测、一致性与校准 · Meta-evaluation

- ★ **Klaus Krippendorff, _Content Analysis: An Introduction to Its Methodology_** —
  解决「多个评判者、有缺失值、有序或名义数据时，一致性该怎么算」。
  Krippendorff's α 是本课模块 03 推荐的通用系数；
  **在「两个评判者 + 名义数据」这个特例下 α 退化为 Scott's π；
  它与 Cohen's kappa 的差别正是「期望一致率用合并边缘还是各自边缘」**——
  这个差别在边缘极不均衡时会变得可观（下一条的 kappa 悖论）。
- **Jacob Cohen（1960）与关于 kappa 悖论的方法学讨论（Feinstein & Cicchetti, 1990 等）** —
  解决「为什么原始一致率 0.9 而 kappa 只有 0.2」。
  本课模块 03 把它讲成一条实践结论：**kappa 塌陷是信号不是缺陷**，
  正确反应是承认该样本分布没有区分度，而不是换一个好看的系数。
- ★ **Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger,
  _On Calibration of Modern Neural Networks_（ICML 2017）** —
  解决「置信度与实际准确率不匹配怎么量、怎么修」：ECE、可靠性图、**温度缩放**。
  本课模块 03 第 5 节直接搬用，并补上一条 judge 特有的实践：
  **用 swap 一致性构造的置信度通常比模型自报的更校准，且边际成本为零**。
- **Daniel Deutsch, Rotem Dror, Dan Roth 关于自动指标评测方法学的工作
  （样本级相关 vs 系统级相关、置信区间与显著性）** —
  解决「一个自动指标该怎么被评测」这个元问题。
  **本课模块 03 第 4 节「样本级一致率 70% 的 judge 也能给出正确排名」的论证结构来自这条线**，
  同时本课强调了它的前提：误差必须是随机的。

## 四 · 排名与聚合 · Ranking

- ★ **Ralph Allan Bradley & Milton E. Terry, _Rank Analysis of Incomplete Block Designs:
  I. The Method of Paired Comparisons_（Biometrika, 1952）** —
  解决「从稀疏的成对比较中估计每个对象的强度」。
  这是本课模块 04 与模块 05 共同的数学基础——**奖励模型的训练目标就是这篇论文的对数似然**。
  更早的形式见 **Zermelo（1929）**，其迭代解法至今仍是标准实现之一。
- ★ **Wei-Lin Chiang, Lianmin Zheng, Ying Sheng, et al.,
  _Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference_（ICML 2024）** —
  解决「怎么把众包的成对偏好变成一个带统计保证的排行榜」：
  BT 拟合、自举置信区间、**名次区间与并列判定**、以及后来的风格控制版本。
  **本课模块 04 的报告规范基本对标这套做法。**
- **Arpad E. Elo, _The Rating of Chessplayers, Past and Present_（1978）** —
  解决「怎么在线增量地维护一个评分」。本课强调一个常被忽略的事实：
  **在线 Elo 是 BT 对数似然的随机梯度上升，因此结果依赖比赛顺序**，
  公开榜单若用它必须固定并公布顺序，否则不可复现。
- **关于成对偏好中传递性违反与多维能力建模的工作（如 Blade-Chest 一类的低秩扩展）** —
  解决「当一个标量不足以刻画能力时怎么办」。
  本课模块 04 第 5 节给出成本从低到高的三条路：分维度报告 → 先去偏再拟合 → 多维模型，
  并指出**总榜第一常常在每个子榜上都不是第一，这不矛盾**。

## 五 · 奖励模型与过优化 · Reward Models

- ★ **Leo Gao, John Schulman, Jacob Hilton,
  _Scaling Laws for Reward Model Overoptimization_（ICML 2023）** —
  解决「过优化会不会发生、什么时候发生、更大的 RM 能不能避免」。
  给出了两个**随优化方式不同而不同**的经验形式（$d = \sqrt{\mathrm{KL}}$）：best-of-n 是 $R_{\text{bon}}(d) \approx d(\alpha - \beta d)$，RL 是 $R_{\text{RL}}(d) \approx d(\alpha - \beta \log d)$，
  并证明 **best-of-n 与 RL 两条路径都会出现倒 U，更大的 RM 推得更远但拐点依然存在**。
  **本课模块 05 第 2–3 节完全建立在这篇之上。**
- ★ **Nisan Stiennon, Long Ouyang, Jeff Wu, et al.,
  _Learning to Summarize from Human Feedback_（NeurIPS 2020）** —
  解决「RLHF 的完整流程长什么样」，并**最早清晰地展示了「优化 RM 分数到一定程度后人类评价反而下降」**。
  它也是「必须有一条独立于 RM 的人类验证信号」这条实践的来源。
- ★ **Nathan Lambert, Valentina Pyatkin, Jacob Morrison, et al., _RewardBench_（2024）** —
  解决「怎么系统地评测一个奖励模型」：**按能力切片**（chat / chat-hard / safety / reasoning），
  而不是报一个总准确率。**本课模块 05 第 4 节与第 6 节的切片思想与「报 worst slice」的主张来自这里**，
  同时本课补充了它的局限：静态偏好对上的准确率是必要条件而非充分条件。
- **Thomas Coste, Usman Anwar, Robert Kirk, David Krueger,
  _Reward Model Ensembles Help Mitigate Overoptimization_（ICLR 2024）** —
  解决「集成与保守化能把拐点推后多少」。
  本课模块 05 第 5 节复现了这个结论，同时强调它的边界：
  **集成治各 RM 独有的误差，治不了偏好数据里的共有偏差**——与模块 02 第 7 节是同一条结论。
- **Rafael Rafailov, Archit Sharma, Eric Mitchell, et al., _Direct Preference Optimization_
  （NeurIPS 2023）** —
  解决「能不能不显式训练 RM 就做偏好优化」。对本课的意义是：
  **DPO 在数学上等价于一个隐式奖励模型**，因此本课关于 RM 的偏差与过优化讨论同样适用，
  只是那个 RM 不再是一个你可以单独拿出来评测的对象——这反而让独立验证信号更重要。

## 六 · 工具与实践 · Tooling

- **UK AI Safety Institute, `inspect_ai` 的 model-graded scorer** —
  解决「怎么把 LLM judge 写成一个可复用、可版本化的 scorer」。
  与本课模块 01 第 8 节的 **judge prompt 版本指纹**主张一致：judge prompt 是 harness 的一部分。
- **各家 LLM API 的结构化输出 / 工具调用约束** —
  解决模块 01 第 6 节的解析失败问题。
  优先用原生 schema 约束，宽松解析只作兜底，并且**必须记录 parse_ok、retry_count 与失败样本的原文**。
- **开源的 Krippendorff α 与 bootstrap 实现（如 `krippendorff`、`scipy.stats.bootstrap`）** —
  本课为了保持零依赖全部从零实现了一遍；
  生产环境建议直接用成熟实现，但**理解一遍再用**能避免最常见的错误：
  自举时重采样错了单位（模块 04 第 4 节）。
