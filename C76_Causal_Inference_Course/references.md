# C76 参考文献 · 因果推断与线上归因

按模块组织。每条注明**它在本课的哪个具体结论上被用到**。

---

## 模块 00 · 总览

- **Imbens, G. & Rubin, D.** *Causal Inference for Statistics, Social, and Biomedical
  Sciences.* Cambridge University Press, 2015.
  → 潜在结果框架的标准参考。第 1–3 章给出「朴素差 $=$ ATT $+$ 选择偏差」这条恒等式
  与 SUTVA 的两个部分（无干扰、一致性）。本课 m00 的恒等式与 m01 的四个目标量都出自此。

- **Holland, P.** *Statistics and Causal Inference.* JASA 81(396), 1986.
  → 「因果推断的根本问题」这个说法的来源，以及对「因果」与「关联」区分的经典讨论。

- **Rubin, D.** *Estimating Causal Effects of Treatments in Randomized and
  Nonrandomized Studies.* Journal of Educational Psychology 66(5), 1974.
  → 潜在结果记号 $Y_i(t)$ 的出处。

- **Kohavi, R., Tang, D. & Xu, Y.** *Trustworthy Online Controlled Experiments.*
  Cambridge University Press, 2020.
  → 本课与 C10 模块 07 的边界由这本书划定：它覆盖 A/B 的统计工具箱，
  本课处理它假设成立<em>之外</em>的情形。第 22 章（干扰）与第 23 章（长期效应）
  是本课 m05 的直接前身。

---

## 模块 01 · 潜在结果框架

- **Cochran, W.** *The Effectiveness of Adjustment by Subclassification in Removing
  Bias in Observational Studies.* Biometrics 24(2), 1968.
  → 「五层足以消除约 $90\%$ 的偏差」这条经典结论的来源。
  本课 m01 实测 $K{=}5$ 消除 $89.7\%$，与之吻合。

- **Hernán, M. & Robins, J.** *Causal Inference: What If.* Chapman & Hall/CRC, 2020.
  （作者提供免费 PDF）
  → 第 1–3 章把「识别 vs 估计」讲得最清楚。本课 m01 第 4–5 节的结构照它组织：
  识别失败的症状是「置信区间越来越窄，而窄区间的中心是错的」。

- **Athey, S. & Imbens, G.** *The State of Applied Econometrics: Causality and Policy
  Evaluation.* Journal of Economic Perspectives 31(2), 2017.
  → 对本课全部五种方法的鸟瞰式综述，以及「先选目标量再选估计量」这条纪律。

- **Rosenbaum, P. & Rubin, D.** *Assessing Sensitivity to an Unobserved Binary
  Covariate in an Observational Study with Binary Outcome.* JRSS-B 45(2), 1983.
  → 敏感性分析的原始形式。本课 m01 练习 3 的做法（「未观测混杂要多强才翻掉结论」）
  是它的连续版本。

- **Cinelli, C. & Hazlett, C.** *Making Sense of Sensitivity.* JRSS-B 82(1), 2020.
  → 敏感性分析的现代实现，把「多强」换成可解释的 $R^2$ 尺度。

---

## 模块 02 · 因果图与识别

- **Pearl, J.** *Causality: Models, Reasoning, and Inference.* 2nd ed., Cambridge
  University Press, 2009.
  → d-分离、后门准则、调整公式的原始出处（第 1、3、11 章）。
  本课 m02 的 `DAG.backdoor_ok` 是第 3.3 节定义的直接实现。

- **Shachter, R.** *Bayes-Ball: The Rational Pastime (for Determining Irrelevance
  and Requisite Information in Belief Networks and Influence Diagrams.* UAI 1998.
  → 本课 m02 的 `d_sep` 用的就是这个算法：状态为「节点 $+$ 来向」的线性时间 BFS。

- **Greenland, S., Pearl, J. & Robins, J.** *Causal Diagrams for Epidemiologic
  Research.* Epidemiology 10(1), 1999.
  → 把 DAG 语言引入应用领域的关键论文，也是 M-bias 讨论的起点。

- **Cinelli, C., Forney, A. & Pearl, J.** *A Crash Course in Good and Bad Controls.*
  Sociological Methods & Research 53(3), 2024.
  → 本课 m02 第 5 节那张「好控制 / 坏控制」八类表的直接来源。
  它也是「只有纯结果预测变量无条件安全」这个结论的出处。

- **Shrier, I. & Platt, R.** *Reducing bias through directed acyclic graphs.*
  BMC Medical Research Methodology 8(70), 2008.
  → M-bias 的教学式讨论，含「控制处理前变量也可能有害」的具体例子。

- **Ding, P. & Miratrix, L.** *To Adjust or Not to Adjust? Sensitivity Analysis of
  M-Bias and Butterfly-Bias.* Journal of Causal Inference 3(1), 2015.
  → 对 M-bias 实践量级的定量讨论。本课 m02 练习 4 的结论
  （四条边同时存在才有 M-bias，断一条即消失）与它一致。

- **Pearl, J.** *Comment: Understanding Simpson's Paradox.* The American
  Statistician 68(1), 2014.
  → 「该不该分层」这个问题只能由图回答。与本课 **C65** 的辛普森悖论一节互补：
  C65 把它当作数据诊断的陷阱，本课把它当作图的判定问题。

---

## 模块 03 · 倾向得分、IPW、双重稳健与 DML

- **Rosenbaum, P. & Rubin, D.** *The Central Role of the Propensity Score in
  Observational Studies for Causal Effects.* Biometrika 70(1), 1983.
  → 倾向得分定理（只按一维 $e(X)$ 调整即可）的原始出处。

- **Robins, J., Rotnitzky, A. & Zhao, L.** *Estimation of Regression Coefficients
  When Some Regressors Are Not Always Observed.* JASA 89(427), 1994.
  → AIPW / 双重稳健的原始形式。本课 m03 第 3 节那张 $2\times2$ 表
  （只在两个 nuisance 都错时失效）是它的核心命题的数值验证。

- **Bang, H. & Robins, J.** *Doubly Robust Estimation in Missing Data and Causal
  Inference Models.* Biometrics 61(4), 2005.
  → 双重稳健的实用化讨论，也包括对「DR 在有限样本里可能不如单一模型」的坦诚分析。

- **Kang, J. & Schafer, J.** *Demystifying Double Robustness.* Statistical Science
  22(4), 2007.
  → 一篇著名的批评性研究：在特定设定下 DR 估计量表现很差。
  本课 m03 的两个 bit 级恒等式（常数 $\hat e$ 使 AIPW $\equiv$ G-comp；
  过拟合把修正项吃掉）是同一类现象的、机制更清楚的版本。

- **Crump, R., Hotz, V., Imbens, G. & Mitnik, O.** *Dealing with Limited Overlap in
  Estimation of Average Treatment Effects.* Biometrika 96(1), 2009.
  → $[0.1, 0.9]$ 截断规则的来源。关键是它被明确设计为一个**换估计目标**的规则，
  而不是一个去偏规则——本课 m03 第 2 节把这一点量化为 $2.0019 \to 1.4371$。

- **Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W.
  & Robins, J.** *Double/Debiased Machine Learning for Treatment and Structural
  Parameters.* The Econometrics Journal 21(1), 2018.
  → DML 的原始论文。本课 m03 第 6 节把它的两个组件分开量化，
  并给出两个与通常表述不同的结论：正交化在 OLS nuisance 下是恒等变换；
  交叉拟合在部分线性得分里可能没有帮助。这两点与论文本身不矛盾——
  论文的定理关于的是**一阶正则化偏差**，而本课量的是有限样本下的实际差异。

- **Lovell, M.** *A Simple Proof of the FWL Theorem.* Journal of Economic Education
  39(1), 2008.
  → Frisch–Waugh–Lovell 定理的简洁证明。本课 m03 把它验证到 $2.2\times10^{-16}$。

- **Hirano, K., Imbens, G. & Ridder, G.** *Efficient Estimation of Average Treatment
  Effects Using the Estimated Propensity Score.* Econometrica 71(4), 2003.
  → 为什么用**估计的**倾向得分有时比用真值更有效率。
  与本课 m03 第 1 节（用真值仍然方差爆炸）形成对照。

---

## 模块 04 · 准实验

- **Angrist, J. & Pischke, J.** *Mostly Harmless Econometrics.* Princeton University
  Press, 2009.
  → 本模块四种方法的标准教材。第 4 章（IV）、第 5 章（DiD）、第 6 章（RDD）。

- **Card, D. & Krueger, A.** *Minimum Wages and Employment: A Case Study of the Fast-Food
  Industry in New Jersey and Pennsylvania.* AER 84(4), 1994.
  → DiD 的经典应用，也是后续关于平行趋势可信性的长期争论的起点。

- **Roth, J.** *Pre-test with Caution: Event-Study Estimates after Testing for
  Parallel Trends.* American Economic Journal: Applied Economics 14(3), 2022.
  → 本课 m04 第 2 节与练习 1 的直接来源：pre-trend 检验的功效常常不足，
  而「通过检验」这一步本身还会引入选择效应。

- **Goodman-Bacon, A.** *Difference-in-Differences with Variation in Treatment
  Timing.* Journal of Econometrics 225(2), 2021.
  → 处理时点不同时 DiD 的分解。本课不覆盖交错处理（staggered DiD），
  这是最重要的延伸方向。

- **Staiger, D. & Stock, J.** *Instrumental Variables Regression with Weak
  Instruments.* Econometrica 65(3), 1997.
  → 「第一阶段 $F > 10$」这条经验规则的来源。本课 m04 实测 $F$ 中位数 $9.88$
  恰是分界，且给出 $1/(F{+}1)$ 的偏差比例近似。

- **Nelson, C. & Startz, R.** *Some Further Results on the Exact Small Sample
  Properties of the Instrumental Variable Estimator.* Econometrica 58(4), 1990.
  → 恰好识别的 2SLS **没有有限矩**这一事实的来源。
  本课 m04 用它解释为什么均值那一列不可读、必须报中位数。

- **Angrist, J. & Imbens, G.** *Identification and Estimation of Local Average
  Treatment Effects.* Econometrica 62(2), 1994.
  → LATE 的定义。本课 m04 用它说明「把 2SLS 结果写成『该功能的效应』
  是一次无声的口径替换」。

- **Gelman, A. & Imbens, G.** *Why High-Order Polynomials Should Not Be Used in
  Regression Discontinuity Designs.* JBES 37(3), 2019.
  → 本课 m04 第 4 节的量化对象：次数从 $2$ 升到 $9$ 偏差不改善，标准差涨 $3.4$ 倍。

- **Calonico, S., Cattaneo, M. & Titiunik, R.** *Robust Nonparametric Confidence
  Intervals for Regression-Discontinuity Designs.* Econometrica 82(6), 2014.
  → RDD 的最优带宽选择与偏差校正。本课只给出 RMSE 曲线，
  这篇给出理论上的最优带宽公式。

- **Abadie, A., Diamond, A. & Hainmueller, J.** *Synthetic Control Methods for
  Comparative Case Studies.* JASA 105(490), 2010.
  → 合成控制与单纯形约束的原始出处。

- **Abadie, A.** *Using Synthetic Controls: Feasibility, Data Requirements, and
  Methodological Aspects.* Journal of Economic Literature 59(2), 2021.
  → 对「什么时候能用合成控制」的系统讨论，包括凸包位置的重要性。
  本课 m04 第 5 节把「凸包内 / 凸包外该用哪种权重」量化为 $1.57$ 倍与 $3.51$ 倍。

- **Doudchenko, N. & Imbens, G.** *Balancing, Regression, Difference-In-Differences
  and Synthetic Control Methods: A Synthesis.* NBER w22791, 2016.
  → 说明单纯形约束不是必需的，无约束版本在某些情形下更好——
  与本课 m04 的凸包外结果一致。

---

## 模块 05 · 线上归因

- **Rubin, D.** *Comment: Which Ifs Have Causal Answers.* JASA 81(396), 1986.
  → SUTVA 这个名字的出处。

- **Ugander, J., Karrer, B., Backstrom, L. & Kleinberg, J.** *Graph Cluster
  Randomization: Network Exposure to Multiple Universes.* KDD 2013.
  → 图聚类随机化的标准方法，以及「网络暴露」这个概念。
  本课 m05 的「邻居暴露差」诊断量是它的一个简化版本。

- **Eckles, D., Karrer, B. & Ugander, J.** *Design and Analysis of Experiments in
  Networks: Reducing Bias from Interference.* Journal of Causal Inference 5(1), 2017.
  → 干扰下的偏差与集群化的方差之间的权衡。
  本课 m05 练习 1 的 MSE 曲线是这个权衡的最小可执行版本。

- **Saveski, M., Pouget-Abadie, J., Saint-Jacques, G., Duan, W., Ghosh, S., Xu, Y. &
  Airoldi, E.** *Detecting Network Effects: Randomizing Over Randomized Experiments.*
  KDD 2017.
  → 一个直接**检测**干扰是否存在的设计（在随机化之上再随机化）。
  本课不覆盖，这是 m05 最重要的延伸方向。

- **Bojinov, I., Simchi-Levi, D. & Zhao, J.** *Design and Analysis of Switchback
  Experiments.* Management Science 69(7), 2023.
  → switchback 的理论分析，包括最优切换频率与 carryover 的处理。

- **Donner, A. & Klar, N.** *Design and Analysis of Cluster Randomization Trials in
  Health Research.* Arnold, 2000.
  → 设计效应 $1 + (m-1)\text{ICC}$ 的标准参考。本课 m05 把它验证到 $1.6\%$。

- **Shapley, L.** *A Value for n-Person Games.* In *Contributions to the Theory of
  Games II*, Princeton University Press, 1953.
  → Shapley 值与它的公理刻画。本课 m05 练习 2 验证其中三条（有效性、对称性、虚拟性）。

- **Dalessandro, B., Perlich, C., Stitelman, O. & Provost, F.** *Causally Motivated
  Attribution for Online Advertising.* ADKDD 2012.
  → 把归因问题明确写成因果问题的早期论文，并指出顺序规则不满足这个目标。

- **Anderl, E., Becker, I., von Wangenheim, F. & Schumann, J.** *Mapping the
  Customer Journey: Lessons Learned from Graph-Based Online Attribution Modeling.*
  International Journal of Forecasting 32(2), 2016.
  → Markov 链归因（移除效应）的实现与与顺序规则的对比。

- **Athey, S., Chetty, R., Imbens, G. & Kang, H.** *The Surrogate Index: Combining
  Short-Term Proxies to Estimate Long-Term Treatment Effects More Rapidly and
  Precisely.* NBER w26463, 2019.
  → 代理指标（surrogate index）的方法论与替代性假设的正式陈述。
  本课 m05 第 4 节的检验（$Y \sim T + S$ 中 $T$ 的系数）出自它。

- **Prentice, R.** *Surrogate Endpoints in Clinical Trials: Definition and
  Operational Criteria.* Statistics in Medicine 8(4), 1989.
  → 替代终点的原始判据（Prentice criterion）。
  本课的「符号反转」正是它失效时的一种表现。

- **VanderWeele, T.** *Surrogate Measures and Consistent Surrogates.* Biometrics
  69(3), 2013.
  → 为什么「代理指标与结果高度相关」不足以保证它是好的替代终点。
  与本课 m05「误差恒等于 $-d$，与代理指标选得多好无关」一致。

---

## 与本课程其他课的关系

- **C10 模块 07 · 在线 A/B 评测** —— A/B 统计工具箱（假设检验、功效、多重比较、
  序贯、CUPED）。本课的前提，且本课不重复其中任何内容。
- **C19 · 可解释性** —— 那里的 d-分离用于分析网络中的信息流；
  本课的 d-分离用于决定回归里放哪些变量。同一工具，两种用途。
- **C65 · 数据质量与诊断** —— 辛普森悖论作为数据陷阱。
  本课 m02 把「该不该分层」变成图上的判定问题。
- **C47 · 排序与推荐** —— 位置偏差与 IPS（逆倾向打分）。
  那是本课 m03 加权思想在排序场景的一个专门应用，
  其中倾向得分由展示策略已知，所以正性问题的形态不同。
- **C37 / C40 / C63 · 系统与运维方向** —— 多处提到「归因」，
  但那里指的是故障归因（root cause），与本课的因果归因是不同的问题。
