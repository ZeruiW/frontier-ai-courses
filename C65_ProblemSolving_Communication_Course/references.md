# 参考清单 · References（结构化问题求解与面试沟通）

> ★ 标必读。每条注明"解决什么问题"——这份清单不是让你把书通读一遍，
> 而是让你在被追问"这个方法有没有依据"时，知道**这不是我编的，是有原始出处的**，
> 需要时也能自己去查原文补深度。本课把这些材料重新组织成了四步框架与沟通三铁律的原材料。

---

## 一 · Fermi 估算经典材料 · Fermi Estimation Classics

- ★ **Lawrence Weinstein & John A. Adam, _Guesstimation: Solving the World's Problems on the Back
  of a Cocktail Napkin_（Princeton University Press, 2008）** —
  解决"完全没有现成数据时，怎么把一个数量级问题拆成可以估出锚点值的子问题"。这本书是 Fermi 估算题
  最广泛引用的入门材料，书中"有多少加油站""地球上有多少高尔夫球"这类例子就是这类面试题的原型，
  **本课 01 模块的锚点数字表方法论直接承袭这本书的拆解范式**。
- **Lawrence Weinstein, _Guesstimation 2.0: Solving Today's Problems on the Back of a Napkin_
  （Princeton University Press, 2012）** —
  续作，解决"怎么把 Fermi 估算用到更贴近工程与环境类问题上"，比第一本更偏向"给定约束反推方案"的题型，
  与 03/04 模块的约束优化视角互相呼应。
- ★ **Sanjoy Mahajan, _Street-Fighting Mathematics: The Art of Educated Guessing and Opportunistic
  Problem Solving_（MIT Press, 2010，MIT OpenCourseWare 免费开放）** —
  解决"怎么系统性地用量纲分析、近似和 lumping（把复杂函数简化成分段常数）代替精确求解"。
  **本课 01 模块"数量级心算"与"隐藏常数与非线性"两个词条的方法论基础均来自这本书**。
- **Sanjoy Mahajan, _The Art of Insight in Science and Engineering: Mastering Complexity_
  （MIT Press, 2014，免费开放版）** —
  前作的续篇，进一步讲"怎么用简化模型快速判断一个复杂系统的行为量级"，适合想把估算能力延伸到
  系统设计（呼应 C63）的读者。
- **William Poundstone, _How Would You Move Mount Fuji? Microsoft's Cult of the Puzzle_
  （Little, Brown, 2003）** —
  解决"这类估算/脑筋急转弯面试题的历史起源、科技公司为什么采用它们、以及它们受到的争议"。
  可作为背景阅读，理解这类题目在面试中被引入的历史脉络与局限。

---

## 二 · 结构化表达：金字塔原理与案例框架 · Structured Communication

- ★ **Barbara Minto, _The Pyramid Principle: Logic in Writing, Thinking, and Problem Solving_
  （初版 1987，多次再版，中文版《金字塔原理》）** —
  解决"怎么把一个复杂论证组织成结论先行、层层支撑、互相独立又合起来穷尽（MECE）的结构"。
  本课"沟通三铁律"里的"结论先行"和 05 模块的"金字塔原理/三点法"直接引用这本书的框架，
  **是本课整个沟通方法论最核心的单一出处**。
- ★ **Marc Cosentino, _Case in Point: Complete Case Interview Preparation_（多版，Burgee Press）** —
  解决"怎么用结构化框架处理一个从未见过的开放性商业问题"。虽然面向咨询案例面试，
  但其"框架先行 → 分解维度 → 逐层论证 → 给出建议"的方法论与本课的四步框架高度同构，
  可作为"结构化表达如何落地到具体案例"的补充练习材料。
- **Google Developers, "Technical Writing Courses"（免费在线课程）** —
  解决"怎么把复杂技术内容写/讲得让非专家也能跟上"，其中关于"先给读者一个路线图再展开细节"的原则
  与本课"十秒结构预告"词条呼应，是一份轻量但实用的补充材料。

---

## 三 · 根因分析方法论 · Root Cause Analysis

- ★ **Taiichi Ohno, _Toyota Production System: Beyond Large-Scale Production_（Productivity Press,
  1988）** —
  解决"怎么通过连续追问'为什么'从表面症状定位到真正根因"。**5 Whys 方法最广为人知的系统性阐述
  即来自丰田生产方式的实践总结**，是本课"诊断树"与"可证伪假设"两个词条的历史源头之一。
- **Kaoru Ishikawa, _Guide to Quality Control_（Asian Productivity Organization, 1976）** —
  解决"怎么系统性列出一个问题可能的多个成因类别而不遗漏"。石川馨（Ishikawa）鱼骨图把根因
  归入人/机/料/法/环等类别，**是"诊断树"构建候选假设集合时可借用的分类骨架**。
- ★ **Google SRE Team, _Site Reliability Engineering_（O'Reilly, 2016，全文免费在线）**，
  第 15 章 "Postmortem Culture: Learning from Failure" —
  解决"工程事故复盘里怎么系统性做根因分析而不止步于表面归因，以及怎么避免'归咎于人'的错误文化"。
  **本课"混杂因素"与"排除法与反例构造"两个词条的工程实践视角直接呼应这一章的方法论**。
- **Judea Pearl & Dana Mackenzie, _The Book of Why: The New Science of Cause and Effect_
  （Basic Books, 2018）** —
  见下方"因果推断"分组，也是根因分析里"混杂因素"概念最严谨的现代理论来源。

---

## 四 · 决策理论经典 · Decision Theory Classics

- ★ **John von Neumann & Oskar Morgenstern, _Theory of Games and Economic Behavior_
  （Princeton University Press, 1944）** —
  解决"不确定性下怎么定义一套自洽、可排序的理性偏好准则"。**期望效用理论（expected utility theory）
  的公理化奠基之作**，是本课"期望效用"词条的原始理论来源。
- ★ **Leonard J. Savage, _The Foundations of Statistics_（Wiley, 1954）** —
  解决"当无法获得客观概率时，怎么依然能做出一致的决策"。**minimax regret（后悔最小化）准则常被
  追溯至 Savage 对主观概率与决策一致性的公理化讨论**，是本课"后悔最小化"词条的理论出处。
- **Abraham Wald, _Statistical Decision Functions_（Wiley, 1950）** —
  解决"完全不知道概率分布、只能假设最坏情况时该怎么决策"。**minimax（最坏情况）准则的经典来源**，
  与期望效用、后悔最小化构成本课"不确定性下三种决策准则"的完整三角。
- ★ **Jeff Bezos, Amazon 1997 Shareholder Letter（"Type 1 and Type 2 Decisions"）** —
  解决"怎么根据决策的可逆性来分配决策速度和审批层级"。这封信提出的"one-way door（不可逆）
  vs two-way door（可逆）"决策分类，**是本课"可逆/不可逆决策速度"词条在工程管理实践中最常被
  引用的通俗出处**，比学术文献更贴近面试语境。

---

## 五 · 因果推断入门：混杂因素 · Causal Inference & Confounding

- ★ **Judea Pearl & Dana Mackenzie, _The Book of Why: The New Science of Cause and Effect_
  （Basic Books, 2018）** —
  解决"相关不等于因果背后的图模型（DAG）解释，混杂因素怎么被严格定义与识别"。这是非数学背景读者
  理解因果推断最好的入门读物，**本课"混杂因素"词条的现代理论框架直接来自这本书**，其中用因果图
  重新解释了辛普森悖论产生的结构性原因。
- **Judea Pearl, _Causality: Models, Reasoning, and Inference_（Cambridge University Press，
  第 2 版 2009）** —
  解决"混杂因素、后门准则、do-calculus 等因果推断核心概念的完整数学形式化"。是上一本科普书背后
  更技术性的原始文献，适合想深挖因果图数学基础的读者，本课只取其中"混杂"这一个概念的直觉解释。
- **Edward H. Simpson, "The Interpretation of Interaction in Contingency Tables"（Journal of the
  Royal Statistical Society, Series B, 1951）** —
  解决"分组内趋势一致、汇总后趋势却反转"这一现象最早的严格统计学描述，**是辛普森悖论——混杂因素
  最经典的数字化证明——的原始出处**。

---

## 六 · 技术沟通与面试实务 · Technical Communication & Interview Practice

- ★ **Gayle Laakmann McDowell, _Cracking the Coding Interview_（CareerCup, 第 6 版）**，
  第 I 部分 "The Interview Process" —
  解决"技术面试里考官到底在评估什么、候选人常见的沟通失误有哪些"。虽然全书主体是算法题（呼应 C62），
  但开篇关于"边写代码边讲思路"的建议与本课"边想边说训练"高度一致，可作为通用面试沟通礼仪的补充读物。
- **Camille Fournier, _The Manager's Path_（O'Reilly, 2017）**，关于沟通与决策透明度的章节 —
  解决"工程组织里怎么把决策依据显式沟通给团队"，其中"暴露假设、明确权衡"的沟通原则与本课
  "沟通三铁律"在管理场景下的应用高度呼应，可作为面试之外的延伸阅读。
- **Julia Evans, "How to Explain What You've Been Working On"（个人博客，juliaevans.com）** —
  解决"怎么把一段技术工作用非线性的、结论先行的方式讲清楚，而不是按时间顺序流水账"，是一篇短小
  精悍、可快速读完的实用材料，直接对应本课 00/05 模块的表达骨架。

---

## 七 · 本库内交叉引用 · Cross-References

- **C61-04 · 项目叙事** — 怎么把已经做过的一个项目讲成让人信服的故事（STAR 模板检测版）。
  **与本课的分工**：C61-04 管"怎么讲你做过的具体项目"，本课管"怎么处理一个当场给你的、通用的问题"，
  两者的沟通铁律共享但应用场景不重叠。
- **C63 · ML 系统设计面试** — 七步框架与六个 45 分钟完整设计案例演练。
  **与本课的分工**：C63 教你怎么设计一个具体的 ML 系统，本课 04 模块的"影响-成本-不确定性矩阵"与
  03 模块的权衡框架是 C63 七步框架里"取舍显式化"这一步的通用方法论来源，C63 直接复用不重复展开。
- **C53-05 · 延迟-精度权衡与实时检测器选型** — 帕累托前沿与"被支配"判断的检测器选型完整案例。
  本课 03 模块的帕累托前沿词条只讲"这个工具在面试里怎么组织语言去用"，具体的检测器数值案例见 C53-05。
- **C57-05 · TSR 小目标实战：方案组合的收益-成本排序** — 预算约束下的组合优化（背包问题）完整案例。
  本课 03 模块约束优化视角的方法论解释引用这个案例，不重复实现细节。
- **C61-03 · 训练与部署调试手册** — 检测领域具体的症状 → 诊断树（loss 为 NaN、mAP 恒为 0 等）。
  本课 02 模块把这套检测专项的诊断树抽象成不限定领域的通用诊断方法论，C61-03 负责领域知识，
  本课负责跨领域的搜索策略。
- **C63-04 · 服务、部署与容量估算** — QPS/显存/算力/成本的具体数量级估算与可背锚点数字表。
  本课 01 模块的 Fermi 估算法是这类具体估算题背后的通用方法论，C63-04 给出的是 ML 系统设计场景下
  的专项数字，本课给的是拆解框架本身。
- **C64 · ML/DL 技术知识问答** — 三段式答法（一句话定义 → 为什么需要 → 什么时候失效）是本课通用
  沟通方法论在"知识问答"这一具体场景下的应用。**本课管"怎么想清楚再说"，C64 管"这个具体知识点该
  说什么"**，两者互相引用不重复。
- **C62 · 编程面试实战** — 算法与数据结构手撕代码，对应 HR 说的 Practical (Coding) Exercise 板块，
  与本课（对应 Problem-Solving 板块）是同批但完全不同的板块。

一句话记住这批补全课的分工：**C62 编码 · C63 设计 · C64 问答 · C65 沟通 · C61 检测专项。**
