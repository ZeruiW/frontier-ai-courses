# 参考清单 · References（ML 系统设计面试）

> ★ 标必读。每条注明"解决什么问题"——这份清单不是让你把论文读完，
> 而是让你在被问到某个具体设计决策时，知道"这个判断是有系统性依据的，不是我编的"。
> 本课的方法论大量借鉴下面这些材料，但**把它们重新组织成了"45 分钟面试里怎么讲"的形态**。

---

## 一 · ML 系统设计的框架性文献 · Frameworks

- ★ **Sculley et al., "Hidden Technical Debt in Machine Learning Systems"（NeurIPS 2015）** —
  解决"为什么 ML 系统的维护成本远高于代码本身看起来的样子"。
  提出 **CACE 原则**（Changing Anything Changes Everything）、纠缠（entanglement）、
  隐藏反馈回路（hidden feedback loops）、胶水代码（glue code）等一系列债务类型。
  **本课 00/04 讲"不确定性是一等公民"时的核心依据就是这篇论文**：
  它说明了为什么 ML 系统的复杂度不在代码量，而在这些看不见的耦合关系上。
- ★ **Zinkevich, "Rules of Machine Learning: Best Practices for ML Engineering"（Google, 内部经验总结公开版）** —
  解决"什么时候该上模型、什么时候该先用规则"。**Rule #1** 就是
  "Don't be afraid to launch a product without machine learning"——
  **本课 01/03 讲 baseline 优先原则、03 讲兜底规则时都直接呼应这条规则**。
  它按"监控 → 第一个模型要简单 → 特征工程比模型选择更重要 → 训练与服务要一致"这个顺序展开，
  与本课七步框架的后半段高度对应。
- ★ **Chip Huyen, _Designing Machine Learning Systems_（O'Reilly, 2022）** —
  解决"端到端 ML 系统设计缺一本框架性教材"这个真实缺口。
  **本课的七步框架与它的目录结构（数据 → 建模 → 部署 → 监控）对应，
  但为 45 分钟面试场景做了重新组织**：书里可以用一整章讲清楚的取舍，
  面试里必须压缩成一句"我选 A 是因为 X 约束，代价是 Y"。
  **第 4 章（Training Data）、第 6 章（Model Development）、第 7 章（Model Deployment）、
  第 8 章（Data Distribution Shifts and Monitoring）是与本课 02/03/04 对应度最高的四章。**
- ★ **Breck et al., "The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction"（IEEE Big Data 2017）** —
  解决"怎么用一份可打分的清单评估一个 ML 系统是否可以上线"。
  分四大类打分：数据、模型、基础设施、监控——**本课 04 的"发布前验收清单"思路直接来自这篇论文的评分表结构**。
  面试里被问"你怎么知道这个系统可以上线了"时，这份清单提供了一个系统性的回答框架，而不是含糊地说"测试通过了"。
- **Amershi et al., "Software Engineering for Machine Learning: A Case Study"（ICSE-SEIP 2019, Microsoft）** —
  解决"ML 系统的软件工程流程和传统软件哪里不一样"。
  基于对 Microsoft 内部数百个团队的调研，指出**数据获取与管理是被低估最严重的环节**——
  与本课 02 模块把"数据系统设计"独立成一整个模块的判断一致。

---

## 二 · 数据管理与工程债 · Data Management

- ★ **Polyzotis, Roy, Whang & Zinkevich, "Data Management Challenges in Production Machine Learning"（SIGMOD 2017 Tutorial）** —
  解决"数据版本、数据验证、数据血缘这些问题为什么值得系统性研究，而不只是工程杂活"。
  **本课 02 讲数据泄漏防范、数据版本与血缘时的问题框架来自这篇 tutorial**：
  它把"数据生命周期"拆成采集、清洗、变换、验证、服务几个阶段，每个阶段都有对应的失败模式。
- **Polyzotis et al., "Data Lifecycle Challenges in Production Machine Learning: A Survey"（SIGMOD Record 2018）** —
  上一条 tutorial 的扩展综述版，**给出了更完整的"数据验证"技术清单**
  （schema 检查、异常值检测、分布偏移检测），对应本课 04 的漂移监控部分。
- **Gebru et al., "Datasheets for Datasets"（Communications of the ACM 2021）** —
  解决"一份数据集该如何被记录，才能让下游使用者知道它的采集方式、局限性和适用范围"。
  **面试里被问"这批数据够不够用"时，这篇论文提供的问题清单
  （动机/构成/采集过程/预处理/使用建议）可以直接迁移成需求澄清的一部分**。
- **Sambasivan et al., "Everyone wants to do the model work, not the data work"（CHI 2021, Google）** —
  用访谈研究证明"数据质量问题是生产 ML 系统里最常被低估、最少被主动投入的环节"。
  **这篇论文的标题本身就是本课反复强调"数据系统设计值得单独一个模块"的最好证据。**

---

## 三 · 评测方法论：离线与在线 · Evaluation Methodology

- ★ **Kohavi, Tang & Xu, _Trustworthy Online Controlled Experiments_（Cambridge University Press, 2020）** —
  A/B 测试领域公认的权威教材，解决"怎么把一次线上实验做对"。
  **本课 03 的样本量与功效计算、新奇效应（novelty effect）、多重比较问题都来自这本书**。
  **第 3 章（"Twyman's Law and Experimentation Trustworthiness"）尤其值得读**：
  它讲"看起来好得不像真的的结果，通常是哪里错了"，这正是"离线-在线背离"诊断时该有的第一反应。
- ★ **Kohavi, Longbotham, Sommerfield & Henne, "Controlled experiments on the web: survey and practical guide"（Data Mining and Knowledge Discovery, 2009）** —
  比上一本书更早的综述版，**给出了 A/B 测试里最常见的陷阱清单**
  （辛普森悖论、新奇效应、样本比例不匹配 SRM），是快速建立直觉的更短路径。
- ★ **Breck, Zinkevich et al.（Google TFX 团队公开材料）关于 slice-based evaluation 的实践总结** —
  解决"为什么只看整体指标会掩盖问题"。**本课 03 的切片评测设计直接对应这类实践**：
  按子群体分桶评测，是发现"整体指标涨、某个关键子群体掉"这类问题的标准做法。
- **Papineni et al. 等早期 NLP 评测文献里关于"离线指标不代表下游任务表现"的讨论**
  （以 BLEU 与人工评估的相关性研究为代表）——
  **提供了"为什么需要在线评测校准离线指标"这个论点在另一个领域的独立证据**，
  说明离线-在线背离不是 CV/自动驾驶特有的问题，而是 ML 系统的普遍现象。

---

## 四 · 容量规划与 SRE · Capacity Planning & SRE

- ★ **Beyer, Jones, Petoff & Murphy (eds.), _Site Reliability Engineering_（Google, O'Reilly 2016，免费在线版）** —
  解决"怎么系统性地做容量规划、定义 SLO、设计降级与回滚"。
  **第 17 章（"Addressing Cascading Failures"）与第 21 章（"Handling Overload"）
  是本课 04 讲降级方案与兜底规则时的直接依据**：级联失败与过载保护的原则可以直接迁移到 ML 服务场景。
- **Beyer, Murphy et al., _The Site Reliability Workbook_（Google, O'Reilly 2018）** —
  上一本书的实践续篇，**第 2 章关于 SLO 制定的具体方法**
  （error budget、可用性目标怎么定）对应本课 01 讲 SLA 时"数字要具体"这条要求。
- **Allspaw, "The Art of Capacity Planning"（O'Reilly, 2008）** —
  虽然是传统 Web 服务时代的书，但**峰值 vs 均值容量规划、增长预测的方法论至今适用**，
  是本课 04 容量估算器背后的经典参考。
- **NVIDIA / MLPerf Inference 公开的基准测试方法论文档** —
  解决"FLOPs、显存、吞吐这些数字该怎么测才可信"。**MLPerf 的测试规范明确区分了
  离线（offline）与服务（server）两种场景的吞吐定义**，是理解"论文报的 FPS 为什么不能直接套用"
  （呼应 C53）在系统设计层面的公开依据。

---

## 五 · 自动驾驶感知系统的公开架构材料 · AD Perception Architecture

- ★ **Apollo（百度）与 Autoware 的公开架构文档** —
  解决"一个真实自动驾驶软件栈里，感知模块的输入输出接口长什么样"。
  两者都公开了感知-预测-规划的模块划分与消息接口定义，**是本课 04 讲"三条线：数据流/控制流/边界"
  时最具体的公开参照物**——面试画架构图时，边界划分的合理性可以用这类真实系统的模块切分来校验。
- **Caesar et al., "nuScenes: A multimodal dataset for autonomous driving"（CVPR 2020）** —
  除了数据集本身，**论文里对多传感器时间同步、标注协议的描述**
  是本课 02 讲"数据采集策略"与"标注体系设计"时的一个具体公开案例。
- **Sun et al., "Scalability in Perception for Autonomous Driving: Waymo Open Dataset"（CVPR 2020）** —
  同上，**附录里关于数据采集车队规模、标注流程的描述**为"标注成本模型"提供了公开的量级参照。
- **各大自动驾驶公司工程博客中关于"影子模式"（shadow mode）验证新模型的公开描述**
  （如 Tesla、Waymo 等公司在会议报告/工程博客里对影子模式验证流程的介绍）——
  **本课 03 的影子模式定义与验证流程直接对应这类公开实践**，说明这不是教科书概念而是量产系统的标准做法。
- **本课 05 的 TSR 案例引用 C55（TSR 领域知识）、C57（小目标检测）、C58（长尾数据闭环）、
  C60（训练-部署一致性）的结论**——这四门课各自有更完整的参考文献列表，
  **本课不重复列出，需要深挖某个技术细节时请直接查对应课程的 references.md**。

---

## 六 · 本库内的交叉引用 · Cross-References

- **C07 · ML 基础与面试数学** — 数学推导（softmax 梯度、贝叶斯、k-fold、偏差-方差）。
  本课 03 用到的显著性检验、置信区间等统计概念**引用**其结论，不重推导。
  **C07 模块 07 是全库唯一在本课诞生前讲过 ML system design 框架的一节**——本课是它的完整展开版。
- **C37 · MLOps 生命周期** — CI/CD、模型注册、特征平台、监控告警的完整工程实现。
  本课 04 提到"上线流程"时只引用结论（"要有回归门禁""要有回滚"），不重讲怎么搭建这些系统。
- **C48 · 云端部署** — 容器编排、弹性伸缩、多区域部署的工程细节。
  本课 04 讲服务分层时引用其部署形态，不重讲具体的云平台配置。
- **C55 · TSR 与自动驾驶感知** — TSR 领域知识、失效模式框架、安全导向评测体系。
  **本课 05 的 TSR 主案例直接引用它的结论**作为案例背景，是本课与既有课程结合最紧密的一处。
- **C57 · 小目标检测** — IoU 对位移的敏感性、NWD、切片推理等小目标专项技术。
  本课 05 的 TSR 案例提到"远距离小目标漏检"时引用其量化结论，不重推导 NWD 公式。
- **C58 · 难例挖掘与长尾数据闭环** — 主动学习触发器、嵌入检索、闭环验证的完整实现。
  **本课 02/05 大量引用它的结论**（触发器怎么设计、边际收益曲线怎么用来判断"还值不值得标"）。
- **C60 · 车端部署与训练-部署一致性** — resize/TensorRT/INT8 校准/后处理对齐的逐层排查方法论。
  本课 04/05 讲"车端云端分工"与"离线-在线背离"时引用其定位方法，不重讲怎么对拍张量。
- **C61 · 检测工程实战与面试实务** — 检测专项白板题、误差分析、调试手册、项目叙事。
  与本课同为一面补全课，但 C61 讲"检测知识怎么讲"，本课讲"系统设计怎么组织"。
- **C62 · 编程面试实战** — 通用算法与数据结构。对应 HR 说的 Practical (Coding) Exercise 板块，
  与本课（Problem-Solving 里的 system design 部分）是同批但完全不同的板块。
- **C65 · 结构化问题求解与沟通** — 估算、诊断归因、权衡决策、模糊需求澄清的通用方法论。
  本课 01/05 的"需求澄清""取舍显式"是这套通用方法论在 system design 场景的具体应用，两者互相引用。

一句话记住五门补全课的分工：**C62 编码 · C63 设计 · C64 问答 · C65 沟通 · C61 检测专项。**
