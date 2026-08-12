# 参考清单 · References（MLOps 与生产生命周期）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课从零实现的每个工具，都能在下列文献/系统里找到生产级的对应实现与权衡。

## 世界观与就绪度 · Worldview & Production-Readiness
- ★ **Sculley et al. 2015, _Hidden Technical Debt in Machine Learning Systems_ (NeurIPS)** — 本课的思想原点。论证「真正的 ML 代码只是冰山一角」，系统化地命名了 ML 特有的技术债：CACE（改一处动全身）、纠缠、数据依赖比代码依赖更难管、反馈回路、配置债、监控缺位。读完你会明白为什么「训练完才是开始」，以及本课五个模块各自在偿还哪一类债。**全课必读，先读这一篇。**
- ★ **Breck et al. 2017, _The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction_ (IEEE Big Data)** — 把上一篇的抽象债务变成 28 条可勾选的检查项（数据测试、模型测试、基础设施测试、监控测试四大类），每项 0/0.5/1 计分。它是一份「生产就绪自查表」，本课许多 worked/练习直接对应其中的具体条目（如「特征分布有监控吗」「能回滚吗」「训练可复现吗」）。
- ★ **Google Cloud, _MLOps: Continuous delivery and automation pipelines in machine learning_（白皮书）** — 给出 MLOps 成熟度分级 L0/L1/L2，清晰区分 CI/CD 与 ML 特有的 CT（持续训练），并画出「自动化训练流水线 + 自动化部署流水线」的参考架构。理解本课各模块如何拼成一条完整的、人逐步退出循环的流水线，看它。
- **Sato, Wider & Windheuser 2019, _Continuous Delivery for Machine Learning (CD4ML)_（martinfowler.com）** — 把 CD 的纪律落到 ML：数据/模型/代码三条版本线如何协同、流水线如何编排、如何在每个关口设质量门。工程视角最完整的一篇入门长文。
- **Huyen 2022, _Designing Machine Learning Systems_ (O'Reilly)** — 系统设计视角的权威教材，数据工程、特征、部署、监控、持续学习各成一章，案例丰富。把本课的「工具内核」放回「整体系统」语境里读它。
- **Paleyes, Urma & Lawrence 2022, _Challenges in Deploying Machine Learning: a Survey of Case Studies_** — 从大量真实落地案例里归纳部署难点（数据、复现、监控、组织）。看别人踩过的坑，理解这些工具为何不得不存在。

## 实验追踪与可复现 · Experiment Tracking & Reproducibility
- ★ **MLflow（开源平台 + 文档）, Zaharia et al. 2018, _Accelerating the ML Lifecycle with MLflow_** — 实验追踪的事实标准。其 Tracking 组件的数据模型（experiment ⊃ run，run = params + metrics + artifacts + tags）正是本课模块 01 从零复刻的对象。读它的 REST/存储后端设计，对照你写的 JSON 落盘版本，能看清「最小可用」到「生产级」差在哪。
- **Weights & Biases / Neptune.ai 文档** — 商业实验追踪平台，强在指标曲线可视化、run 比较、超参搜索与协作。看它们的 run 比较与 leaderboard 交互，理解模块 01 「选最优 run」在产品里长什么样。
- **Pineau et al. 2021, _Improving Reproducibility in Machine Learning Research (the NeurIPS Reproducibility Checklist)_** — 给出可复现研究的清单（代码、数据、环境、随机性、计算预算的披露要求）。把「复现」从口号变成可检查项，与本课的 config hash / seed 记录直接呼应。
- **Sugimura & Hartl 2018, _Building a Reproducible Machine Learning Pipeline_** — 专门谈如何用数据版本 + 环境固定 + 流水线把整条训练做到可复现，是模块 01/02 的工程化延伸阅读。

## 数据与模型版本、血缘 · Versioning & Lineage
- ★ **DVC (Data Version Control)（开源工具 + 文档）** — 把 Git 的内容寻址思想扩展到大数据/大模型：内容哈希 + 对象存储 + 小指针文件 + 可复现 pipeline。本课模块 02 从零实现的「内容寻址存储 + manifest + lineage」正是它的内核。读它的 `.dvc` 文件格式与 cache 机制，对照你写的版本库。
- ★ **Torvalds & Hamano, _Git internals_（Pro Git 第 10 章）** — Git 的对象模型（blob/tree/commit 全是内容寻址的、不可变的、靠 SHA-1 寻址）是一切现代版本系统的范本。读它你会发现模块 02 的「哈希即地址、标签是可移动指针、历史不可变」全是 Git 的直接搬运。
- **Pachyderm 文档, _Data-driven pipelines & data lineage_** — 把数据版本与流水线血缘做成一等公民的平台：每次数据变更自动触发下游、全程可追溯。模块 02 lineage DAG 的生产级形态。
- **OpenLineage / Marquez 项目** — 跨工具的血缘元数据开放标准与采集系统。理解「血缘」如何在异构栈里被统一记录与查询，看它。
- **Schelter et al. 2017, _Automatically Tracking Metadata and Provenance of Machine Learning Experiments_** — 系统化讨论如何自动捕获 ML 实验的元数据与来源，是追踪 + 血缘的学术化处理。

## 评测门禁、测试与 CI/CD · Gates, Testing & CI/CD
- ★ **Breck et al. 2019, _Data Validation for Machine Learning_ (SysML)** — Google TFX 的数据校验：自动推断 schema、检测训练/服务偏斜与异常，在数据进入训练前把关。模块 03 「门禁」和模块 02 「schema 校验」的直接出处。
- **Polyzotis et al. 2017/2019, _Data Management Challenges in Production ML_ / _Data Validation for ML_** — 从数据管理视角讲生产 ML 的校验、监控、版本难题，是上面那篇的姊妹篇与背景。
- ★ **Efron & Tibshirani 1993, _An Introduction to the Bootstrap_** — bootstrap 的权威教材。本课模块 03 用它给指标加置信区间、判两模型差异是否显著。理解「为什么有放回重采样能估出统计量的分布」，读它的前几章足矣。
- **Demšar 2006, _Statistical Comparisons of Classifiers over Multiple Data Sets_ (JMLR)** — 如何严谨地比较多个模型/数据集上的指标（配对检验、多重比较校正、避免被随机波动骗）。门禁里「差异是否显著」的统计学依据。
- **Dietterich 1998, _Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms_** — 经典地讨论比较两个分类器时各种检验的陷阱（如未校正的重用测试集会高估显著性）。配合上一条读，避免门禁给出虚假的「显著提升」。
- **Zhang et al. 2020, _Machine Learning Testing: Survey, Landscapes and Horizons_** — ML 测试的全景综述（数据测试、模型测试、metamorphic 测试等）。把「门禁里该测什么」扩展到比单一指标阈值丰富得多的检查面。

## 监控与漂移检测 · Monitoring & Drift Detection
- ★ **Gama et al. 2014, _A Survey on Concept Drift Adaptation_ (ACM Computing Surveys)** — 概念漂移的权威综述。系统梳理漂移类型（突变/渐变/周期/重现）、检测方法（基于性能、基于分布）、适应策略（窗口、集成、重训）。模块 04/05 的理论骨架，强烈建议精读。
- ★ **Webb et al. 2016, _Characterizing Concept Drift_** — 给漂移下精确的概率定义并提出量化刻画维度（漂移的幅度、频率、可预测性）。把「模型过时」从模糊感觉变成可测量的量，模块 04 的概念地基。
- **Lu et al. 2018, _Learning under Concept Drift: A Review_ (IEEE TKDE)** — 与 Gama 综述互补的较新综述，覆盖更多检测器（DDM、EDDM、ADWIN、Page-Hinkley）与在线适应方法。想实现更强的漂移检测器时按它索引。
- **Bifet & Gavaldà 2007, _Learning from Time-Changing Data with Adaptive Windowing (ADWIN)_** — 自适应窗口的经典算法：用统计检验自动决定该用多长的历史窗口，兼顾「反应快」与「不被噪声骗」。模块 04 滑窗思想的进阶。
- **Rabanser, Günnemann & Lipton 2019, _Failing Loudly: An Empirical Study of Methods for Detecting Dataset Shift_ (NeurIPS)** — 系统比较各种分布偏移检测方法（含降维 + 两样本检验、KS、MMD）的实证研究。理解 PSI/KS 之外还有哪些武器、各自何时失效。
- **Evidently AI / NannyML / Alibi-Detect（开源库 + 文档）** — 生产级漂移与模型监控库，内置 PSI、KS、χ²、PSI、性能估计（NannyML 的无标签性能估计尤其值得看）。模块 04 从零实现的统计内核，在这里是开箱即用的组件。
- **NannyML, _Estimating Performance without Labels (CBPE / DLE)_（文档/博客）** — 直面「标签延迟」：在真值未到时估计模型性能。是模块 04/05 「代理指标」思路的现成方法论。

## 反馈闭环、持续学习与遗忘 · Feedback, Continual Learning & Forgetting
- ★ **Kirkpatrick et al. 2017, _Overcoming Catastrophic Forgetting in Neural Networks (EWC)_ (PNAS)** — 灾难性遗忘的代表作：用 Fisher 信息给重要参数加「弹性」约束，让模型学新不忘旧。模块 05 量化遗忘、对抗遗忘的核心参考。
- ★ **French 1999, _Catastrophic Forgetting in Connectionist Networks_** — 最早系统阐述灾难性遗忘现象与成因（稳定-可塑性困境）的综述性文章。理解「为什么持续学习这么难」的源头。
- **Lopez-Paz & Ranzato 2017, _Gradient Episodic Memory (GEM)_** — 用少量旧样本约束梯度方向，避免更新损害旧任务。回放/复演类方法的代表，模块 05 「重训混入旧数据」的理论版。
- **Parisi et al. 2019, _Continual Lifelong Learning with Neural Networks: A Review_** — 持续学习的全景综述（正则化、回放、参数隔离三大流派）。系统理解对抗遗忘的方法谱系。
- **Sculley et al. 2015（同上）关于反馈回路一节** — 专门点出 ML 系统的「直接/隐藏反馈回路」如何让模型影响自己未来的训练数据，造成失控。模块 05 讨论「反馈偏差/失控回路」的出处。
- **Huyen 2022（同上）「Continual Learning and Test in Production」章** — 工程视角讲重训触发、在线评测、影子/金丝雀如何与持续学习配合。模块 05 落地化阅读。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **从零造工具，不调平台 API**：全课用 **标准库 + numpy/pandas** 把 MLflow/DVC/Evidently 的**核心机制**重写一遍——实验追踪器（JSON 落盘 + run 比较）、内容寻址版本库（`hashlib` + manifest + lineage DAG）、评测门禁（阈值 + 回归 + bootstrap 显著性）、漂移检测器（PSI 分箱 + KS/ECDF）、反馈→重训触发器。每件工具都**逻辑正确、可实跑、assert 全过**（用 `tempfile`/`sqlite3` 做真实小工具）。目的不是替代这些平台，而是让你**看穿它们在替你做什么**、设计取舍在哪。
- **可迁移性**：你在 numpy/pandas 里验证过的「内容哈希、lineage DAG、PSI/KS、bootstrap CI、重训触发逻辑」，可几乎一对一映射到 MLflow `log_*`、DVC `add/repro`、Evidently 报告、Airflow DAG。本课刻意让接口贴近真实工具。
- **课程衔接**：上游接 C24（推理/服务）、C34（评测）等具体技能课——它们教「怎么训得好、评得准、服务得快」；**C37 接管「训完之后的组织级运维」**：怎么把这些资产**可复现地版本化、安全地放行、上线后持续盯住、并随世界变化重训**。本课是把零散技能拼成一条能长期运转的生命周期的黏合层。
