# 参考清单 · References（研究方法论与科学实践）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课每个模块的方法论，都能在下列文献里找到更系统的论述与真实案例。这门课是「元课程」——它教的不是某个模型，而是如何把任何模型/算法的研究做得可信。

## 读论文与复现 · Reading & Reproducing
- ★ **Keshav 2007, _How to Read a Paper_** — 三遍读法的经典短文（仅 3 页），给出读一篇论文的可操作流程：第一遍鸟瞰决定去留、第二遍抓主旨、第三遍「虚拟复现」。本课模块 01 的方法直接来自它，是每个研究者入门的第一篇必读。
- ★ **Pineau et al. 2021, _Improving Reproducibility in Machine Learning Research_ (NeurIPS Reproducibility Program)** — NeurIPS 可复现性清单的由来与成效报告。系统给出复现一篇机器学习论文要核对哪些项，是模块 01 复现检查表与模块 04 可复现工程的制度蓝本。
- **Raff 2019, _A Step Toward Quantifying Independently Reproducible Machine Learning Research_** — 实证研究：作者尝试独立复现 255 篇论文，量化哪些因素（公开代码、超参完整度、伪代码）让复现更可能成功。读它你会对「复现有多难、哪些细节最致命」有数据支撑的直觉。
- **Gundersen & Kjensmo 2018, _State of the Art: Reproducibility in Artificial Intelligence_** — 用一套可复现性指标审视 AI 顶会论文，发现绝大多数缺关键细节。建立「读到一篇论文先问：我能复现吗」的批判习惯。

## 实验设计与消融 · Experiment Design & Ablation
- ★ **Montgomery, _Design and Analysis of Experiments_（教材）** — 实验设计（DOE）的标准教材。受控实验、因子设计、随机化、区组、交互效应的权威来源。机器学习的消融与多因素实验本质都是 DOE，遇到「该怎么设计这组实验」回它。
- ★ **Lipton & Steinhardt 2019, _Troubling Trends in Machine Learning Scholarship_** — 痛陈机器学习论文的四类通病：解释与推测不分、未识别真正起作用的因素（缺消融）、用数学唬人（mathiness）、术语滥用。这是模块 02（消融纪律）与模块 05（诚实写作）的反面教材与行动纲领，强烈建议精读。
- **Sculley et al. 2018, _Winner's Curse? On Pace, Progress, and Empirical Rigor_** — 批评机器学习「重刷榜、轻严谨」的风气，呼吁对照、消融、调参公平、报告方差。模块 02 与模块 03 的世界观来源：进步应来自理解，而非排行榜上的 0.1 分。
- **Bouthillier et al. 2019, _Unreproducible Research is Reproducible_** — 揭示一个悖论：固定种子能精确复现某次运行，却掩盖了结论对随机性的脆弱。主张报告「在随机源变化下」的结论稳定性，是连接模块 02（随机化）与模块 03（方差）的关键。

## 研究统计 · Statistics for Research
- ★ **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_** — 系统量化机器学习基准里的多种方差来源（随机种子、数据划分、超参），证明只控一个（如只固定种子）会严重低估不确定性，并给出在预算约束下如何分配重复实验。模块 03 的核心论文。
- ★ **Demšar 2006, _Statistical Comparisons of Classifiers over Multiple Data Sets_** — 多个分类器在多个数据集上比较的统计方法奠基论文：为什么不能滥用 t 检验、该用 Friedman + Nemenyi 等非参方法、如何画 critical difference 图。模块 03（多重比较）的方法标准。
- ★ **Henderson et al. 2018, _Deep Reinforcement Learning that Matters_** — 用大量实验证明深度强化学习结果对随机种子、实现细节、超参极其敏感，许多「提升」在控制方差后消失。是「只跑一个种子会骗你」最有力的实证，模块 03 的灵魂案例。
- **Cohen 1992, _A Power Primer_** — 统计功效与效应量的极简实用指南：常见检验要多大样本才有足够功效、Cohen's d 的小/中/大如何解读。模块 03 功效分析与样本量计算的入门。
- **Wasserstein & Lazar 2016, _The ASA Statement on p-Values_** — 美国统计学会对 p 值的官方澄清：p 值是什么、不是什么、六条原则。纠正「p<0.05 = 效应为真/重要」的普遍误读，是任何用统计的研究者的必读校准。
- **Dror et al. 2018, _The Hitchhiker's Guide to Testing Statistical Significance in NLP_** — 面向 NLP 实践者的显著性检验操作指南：怎么选检验、怎么处理多重比较。把模块 03 的统计落到具体任务。

## 数据划分与评测陷阱 · Data Splits & Evaluation Pitfalls
- ★ **Gorman & Bedrick 2019, _We Need to Talk about Standard Splits_** — 证明只用一个「标准」训练/测试划分会让系统排名不稳定：换几个随机划分，所谓的 SOTA 排名就洗牌了。主张用多次随机划分 + 统计检验。模块 02/03 必读，直击「单一划分」陷阱。
- **Recht et al. 2019, _Do ImageNet Classifiers Generalize to ImageNet?_** — 重新采集新测试集，发现模型准确率普遍下降——揭示对单一测试集长期调优带来的过拟合（adaptive overfitting）。外部效度与「测试集泄漏」的经典警示。
- **Kapoor & Narayanan 2023, _Leakage and the Reproducibility Crisis in ML-based Science_** — 系统梳理机器学习用于科学时的数据泄漏（leakage）八种形态，导致大量跨学科论文结论虚高。读它学会在复现与设计时主动排查泄漏。

## 研究工程与可复现 · Research Engineering & Reproducibility
- ★ **Wilson et al. 2017, _Good Enough Practices in Scientific Computing_** — 面向普通研究者（非软件工程师）的务实科研软件规范：数据管理、代码组织、协作、项目结构、可复现。不追求完美工程，但守住底线。模块 04 的行动手册，强烈建议通读并照做。
- ★ **Bergstra & Bengio 2012, _Random Search for Hyper-Parameter Optimization_** — 证明在只有少数超参真正重要时，随机搜索在同等预算下通常优于网格搜索。模块 04 超参 sweep 策略的理论依据，颠覆「网格更全面」的直觉。
- **Wilson et al. 2014, _Best Practices for Scientific Computing_** — 上一篇的「进阶版」：版本控制、测试、代码评审、不要重复造轮子等更完整的清单。和 Good Enough 配合读，按自己项目的成熟度取用。
- **Sculley et al. 2015, _Hidden Technical Debt in Machine Learning Systems_** — 著名的「机器学习系统的隐性技术债」：胶水代码、配置膨胀、管道丛林、实验难复现。提醒研究工程不只是写模型，更是管住复杂度。
- **Sandve et al. 2013, _Ten Simple Rules for Reproducible Computational Research_** — 十条可操作的可复现规则（记录每一步、记录随机种子、归档原始数据与脚本……）。模块 04 的极简检查清单。

## 写作、审稿与诚信 · Writing, Review & Integrity
- ★ **Bender, _How to Write a Paper_ / 学术写作讲义** — 关于科学写作的实用指导：以读者为中心、先讲贡献、claim-evidence 对齐、figures 自包含。模块 05 写作部分的依据（Emily Bender 等人的写作课材料），把「写清楚」当成一项可学的技能。
- ★ **Whitesides 2004, _Writing a Paper_** — 化学家 Whitesides 的传世短文：论文从 outline 开始、写作即组织思想、每张图都要服务一个论点。跨学科通用，是科学写作最被推荐的入门之一。
- **Mensh & Kording 2017, _Ten Simple Rules for Structuring Papers_** — 把论文写作拆成可操作的十条（一个中心贡献、讲一个故事、段落的 C-C-C 结构……）。模块 05 论文结构的清单化版本。
- **Smith 1990, _The Task of the Referee_** — 怎么当一个好审稿人：评审的职责、怎么读、怎么写有建设性的意见。模块 05 审稿部分的经典指南。
- **Sculley, Snoek, Wiltschko & Rahimi 2018, _Avoiding Analysis Paralysis_ / Rahimi & Recht 2017 "ML is Alchemy" 演讲** — 关于「炼金术 vs 科学」的著名争论：呼吁可解释、可复现、有理论支撑的实验科学。给研究品味与严谨性提供立场参照。
- **NeurIPS / ICML _Reviewer Guidelines_ 与 _Paper Checklist_** — 顶会官方的审稿指南与可复现清单。既是投稿前的自检表，也是学习「评审在看什么」的一手材料。模块 05 审稿与可复现声明练习的现实对应。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本课是「元课程」**：它不教任何新模型，而教如何把这套培训里学到的所有模型/算法/系统的研究做得**可信**——读懂并复现别人的工作（01）、设计能下结论的实验（02）、用统计区分信号与噪声（03）、把实验管到可复现（04）、把结果诚实地写出来并扛住审稿（05）。
- **全程可跑**：方法论不空谈。每个模块的 notebook 都用 numpy/pandas 把原则跑成可 assert 的小实验——复现一个数字、跑受控玩具实验、算 bootstrap CI 与功效、固定种子核验可复现、从结果生成诚实图表数据。结构正确则 assert 通过，亲手做过才真正内化。
- **课程衔接**：本课是全栈培训的**收口课**。前面每一门课（模型内部、训练、评测、安全、系统、GPU 内核……）产出的都是「知识与技能」；本课教你如何用这些知识**产出新的、可信的知识**。学完任何一门技术课后，都可回到本课，用它的检查表审视自己的实验是否站得住脚。
