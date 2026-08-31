# 参考清单 · References（Eval 基础设施与线上监控）

> ★ 标必读。每条注明「解决什么问题」——这份清单不是让你把资料通读一遍，
> 而是让你在被追问「这个做法有没有依据」时，知道**这不是我编的，有原始出处**。
> 本课把这些材料重新组织成了「spec → runner → store → gate → online」这条主线。

---

## 一 · 评测框架的设计 · Eval Framework Design

- ★ **UK AI Safety Institute, `inspect_ai`（框架文档与源码）** —
  解决「怎么把一次评测写成声明式的三件套」：`Task`（数据集 + solver + scorer）。
  它是本课四层架构的最直接对照物：
  **`@task` 装饰的函数就是 ① SPEC，`inspect eval` 是 ② RUNNER，
  `.eval` 日志是 ③ STORE，`inspect view` 是 ④ REPORT**。
  尤其值得看的是它的 `--max-connections`（并发）与 `--epochs`（重复次数）——
  这两个参数正好对应本课模块 02 与 C66 模块 04 的两个核心工程量。
- **OpenAI Evals 的 registry / YAML spec 设计** —
  解决「评测配置怎么与代码分离」。它是「spec 即数据」这一思想较早的公开实现，
  **本课模块 01 的核心主张与它一脉相承**：配置是可序列化的数据，不是脚本里的常量。
- **LM Evaluation Harness（EleutherAI）的 task 注册与版本机制** —
  解决「同一个基准的多个变体怎么共存」。它的 task 版本号机制是本课
  「任务集只增不改、改了发新版本」的一个工业级实例。

## 二 · 数据版本化与文档 · Data Versioning & Documentation

- ★ **Timnit Gebru, Jamie Morgenstern, Briana Vecchione, et al.,
  _Datasheets for Datasets_（CACM 2021 / arXiv 2018）** —
  解决「一份数据集应当附带哪些说明」：动机、构成、采集过程、预处理、用途、维护。
  **本课模块 01 第 6 节把它裁剪成了评测场景的七个必答问题**，
  并加了一条它没有的、极其实用的：**预期的合理分数区间**。
- **Tom Preston-Werner, _Semantic Versioning 2.0.0_** —
  解决「版本号该怎么走」。本课把它翻译成评测语义：
  **新增样本走次版本（历史全部有效），修改或删除走主版本（分母变了）**。
- **D. Sculley, Gary Holt, Daniel Golovin, et al.,
  _Hidden Technical Debt in Machine Learning Systems_（NeurIPS 2015）** —
  解决「ML 系统的技术债在哪」。它提出的「配置债」「数据依赖债」「胶水代码」
  三个概念，正是本课六个反模式的上位描述——
  **本课的贡献是把它们具体化到评测这个子领域，并给出每一条的可执行解法**。

## 三 · 执行工程 · Runner Engineering

- ★ **Google, _Site Reliability Engineering_（第 21 章「处理过载」、第 22 章「级联故障」、第 4 章「SLO」）** —
  解决重试、退避、抖动、过载保护的标准做法。
  **本课模块 02 第 3 节的「指数退避 + 抖动」与惊群效应，直接来自这一章**。
  它强调的一点在评测里同样成立：*重试本身可能是下一次雪崩的原因*。
- **Michael T. Nygard, _Release It!_（第 5 章，熔断器模式）** —
  解决「上游挂了的时候怎么不把自己也拖死」。
  本课模块 02 第 5 节的三态熔断器（closed / open / **half_open**）出自这里；
  **half_open 这个状态是它区别于「失败就停」的关键**——它让熔断能自动恢复，
  而评测经常在无人值守时跑。
- **AWS Architecture Blog, _Exponential Backoff and Jitter_（Marc Brooker）** —
  解决「抖动该怎么加」。它对比了几种抖动策略（full / equal / decorrelated jitter），
  结论是**任何抖动都远好于没有抖动**——本课采用最简单的乘性抖动。

## 四 · 数据建模与分析 · Modeling & Analysis

- **Ralph Kimball, _The Data Warehouse Toolkit_（事实表 / 维度表建模）** —
  解决「分析型数据该怎么建模」。**本课只借用其中最核心的一条：
  存最细粒度的事实，聚合是它上面的视图**。
  评测结果天然适合这个形态——一条 rollout 一行，任务属性作为可 join 的维度。
- ★ **E. H. Simpson, _The Interpretation of Interaction in Contingency Tables_
  （JRSS-B, 1951）** 与后续关于分层悖论的方法学讨论 —
  解决「为什么每一层都更好，合并后却更差」。
  **本课模块 03 第 3 节复现了它在评测场景下的真实成因**：
  两次运行的任务集不完全相同（超时被跳过的题不一样），
  而**流行病学里的「直接标准化」正是它的标准解法**——在评测里就是交集重算。
- **Quinn McNemar（1947）与配对二值数据的检验** —
  解决「同一批任务上比较两个配置」。它在本课出现了两次
  （模块 03 的 run diff、模块 04 的配对门禁），
  而在 C66 模块 04 里已经出现过一次——**同一个结构在三门课里反复出现，
  因为「配对消掉最大方差源」这件事在评测里无处不在**。

## 五 · CI 门禁与测试可靠性 · Gating & Flakiness

- ★ **Google Testing Blog / _Testing on the Toilet_ 关于 flaky test 的系列文章** —
  解决「不稳定的测试怎么治理」。核心结论与本课模块 04 完全一致：
  **flaky test 的真正代价不是它偶尔失败，而是它让人不再相信测试结果**。
  Google 的做法（自动重跑、隔离 flaky 用例、把 flakiness 当成一级指标追踪）
  正是本课「连续两次才阻断」与「门禁健康报告」的来源。
- **Jez Humble & David Farley, _Continuous Delivery_（部署流水线的分层）** —
  解决「什么该在提交时跑、什么该在合并前跑」。
  **本课模块 04 第 5 节的 smoke / full / deep 三级结构就是它在评测上的实例**，
  区别在于评测多了一个统计维度——所以本课额外给出了「smoke 不该配统计门禁」这个算出来的结论。
- **Abraham Wald, _Sequential Analysis_（1947）中的序贯概率比检验（SPRT）** —
  解决「什么时候可以提前停止」。本课的「连续两次才阻断」是它的一个极简特例；
  **想做更精细的早停判定时，SPRT 与 alpha spending 是标准工具**
  （C66 模块 04 第 8 节讨论过窥视问题）。

## 六 · 线上监控 · Online Monitoring

- ★ **Ron Kohavi, Diane Tang, Ya Xu,
  _Trustworthy Online Controlled Experiments_（Cambridge University Press, 2020）** —
  解决「线上实验怎么做才可信」：样本比例失衡检验、护栏指标、
  代理指标与真实指标的关系、以及「为什么大多数线上实验的效应量比预期小」。
  **本课模块 05 第 1 节「离线-在线的两层不匹配」与第 5 节的行为代理指标，
  方法论都建立在这本书之上**。
- **OpenTelemetry, _Semantic Conventions for Generative AI_（`gen_ai.*` 属性）** —
  解决「LLM 应用的埋点字段该怎么起名」。
  沿用标准字段名的理由不是优雅，而是**现成的 trace 查看器可以直接用**。
  本课在它之上补了三个评测特有的字段：
  **`sample_kind`、`sample_p`（采样偏倚修正必需）、`guardrail.layer`**。
- **Population Stability Index 与 KS 检验在模型监控中的常规实践
  （信贷风控领域的长期惯例，判读阈值 0.1 / 0.25）** —
  解决「分布漂移怎么量」。
  **本课强调的是它们的局限而非用法**：PSI 高只说明「变了」，
  不说明「变差了」——所以漂移告警的正确动作是触发带标签抽样，而不是回滚。
- **逆概率加权（IPW）/ Horvitz–Thompson 估计量** —
  解决「非均匀采样的数据怎么做无偏估计」。
  本课模块 05 第 5 节用它修正尾部采样的偏倚；
  **关键前提是采样概率必须被记录下来**——没有 `sample_p` 这个字段，
  尾部采样的数据就永远只能当诊断素材，进不了统计。
