# 参考清单 · References（Agent 评测与基准）

> ★ 标必读。每条注明「解决什么问题」——这份清单不是让你把论文读一遍，
> 而是让你在被追问「这个做法有没有依据」时，知道**这不是我编的，有原始出处**，
> 需要时能自己去查原文补深度。本课把这些材料重新组织成了「七个决策点」的骨架。

---

## 一 · 代码类 agentic 基准 · Code Agents

- ★ **Carlos E. Jimenez, John Yang, et al., _SWE-bench: Can Language Models Resolve Real-World
  GitHub Issues?_（ICLR 2024）** —
  解决「怎么把真实软件工程任务变成一个判分完全确定性的基准」。
  从已合并 PR 反向构造任务、把 issue 文本与补丁+测试分离、用 `FAIL_TO_PASS` 与 `PASS_TO_PASS`
  两组测试判分——**本课模块 01 的任务构造流程与模块 02 的防回归判分设计全部承袭这篇**。
- ★ **OpenAI, _Introducing SWE-bench Verified_（2024）** —
  解决「一个被广泛引用的基准里到底有多少坏题」。由专业开发者逐条审核 SWE-bench，
  剔除「issue 描述不足以复现」「隐藏测试检查了描述里没提的行为」等任务，得到 500 条可解子集。
  **本课反复引用的一条结论——「坏题是常态而不是意外」——直接来自这份工作。**
- **John Yang et al., _SWE-bench Multimodal_ 与 SWE-bench 家族的多语言/持续更新变体** —
  解决「Python 上的成绩里有多少来自对生态的记忆」以及「怎么用滚动更新对抗污染」。
  代价是每次滚动后分数不可与历史直接比较，这个取舍在模块 01 第 6 节展开。
- **围绕 SWE-bench 的后续质量分析工作（解法泄漏、测试强度不足、任务可解性）** —
  解决「为什么同一个模型在 full 与 Verified 上分数差这么多」。
  这类分析是模块 02「变异测试量化判分强度」一节的动机来源；
  **自建任务集时把 issue 评论区、后续 commit message、PR 描述全部剥离，是从这里得到的清洗规则。**
- **OpenAI, _SWE-Lancer_（2025）一类把任务标价的基准** —
  解决「怎么把成功率折算成经济价值」。它是模块 05 成本视角的一个极端版本：
  不问「做对了几道」，问「赚到了多少钱」。

## 二 · 工具与对话型 agent 基准 · Tool-use & Conversational Agents

- ★ **Shunyu Yao, Noah Shinn, Pedram Razavi, Karthik Narasimhan, _τ-bench: A Benchmark for
  Tool-Agent-User Interaction in Real-World Domains_（2024）** —
  解决三件事：**① 怎么给没有测试可跑的任务判分**（对比数据库终态与标注的目标状态）、
  **② 怎么模拟一个信息挤牙膏式给出的真实用户**（用另一个 LLM 扮演用户）、
  **③ 怎么衡量可靠性而非峰值能力**（引入 pass^k）。
  **本课模块 01 第 3 节与模块 04 第 2 节的核心内容都来自这篇**；
  它留给整个领域最重要的遗产是 pass^k 这个指标。
- **τ²-bench 一类的双向控制扩展** —
  解决「用户不只是提供信息，还要被 agent 指挥去操作环境」这一更真实的设定。
  它引入了新的判分维度：说得对但用户听不懂照做不了，同样是失败。

## 三 · 网页、GUI 与开放网络 · Web / GUI / Open Web

- ★ **Shuyan Zhou et al., _WebArena: A Realistic Web Environment for Building Autonomous Agents_
  （ICLR 2024）** —
  解决「怎么在保住交互性的同时让网页 agent 评测可复现」：**自建可复现的网站集群**
  （购物、论坛、GitLab、CMS、地图全部本地部署），每个任务配一个程序化 validator。
  **本课模块 01 第 4 节的「离线 / 自托管 / 在线」三种取舍，以及「不可能任务」这一被低估的设计，
  都出自这篇。**
- **Jing Yu Koh et al., _VisualWebArena_（2024）** —
  解决「网页任务里需要视觉理解的那一半」，判分方式不变，任务需要 VLM 能力（呼应 C00）。
- ★ **Tianbao Xie et al., _OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real
  Computer Environments_（NeurIPS 2024）** —
  解决「怎么在真实操作系统 + 真实应用上做可判分的任务」：每个任务一段执行式校验脚本。
  跨应用任务（在 A 里查到的填进 B）是这个基准的难点所在。
- **Xiang Deng et al., _Mind2Web_（NeurIPS 2023）** —
  解决「用离线录制的真实网页轨迹做完全可复现的评测」。
  代价是**无法评测「走错了能不能回来」**这一最关键的 agent 能力，
  这一点是模块 03「恢复率」一节的反面动机。
- **Grégoire Mialon et al., _GAIA: A Benchmark for General AI Assistants_（2023）** —
  解决「开放式任务怎么客观判分」：**从判分倒推题目设计**——只出答案唯一、简短、可精确匹配的问题，
  但通往答案的路径需要多步搜索、读文件、看图。
  **「先问我怎么自动判对错，再据此设计题目形态」这条方法论可以直接拿去自建任务集。**
- **OpenAI, _BrowseComp_（2025）一类「难找但易验证」的基准** —
  解决「怎么专门测长程搜索的耐心而不是知识量」：叠加多个稀有约束，使答案在网上只有一处能拼出来。

## 四 · 科研与长程任务 · Research & Long-Horizon

- **Jun Shern Chan et al., _MLE-bench: Evaluating Machine Learning Agents on Machine Learning
  Engineering_（2024）** —
  解决「机器学习任务没有对错、只有分数高低时怎么判分」：**拿真实竞赛排行榜当标尺**，
  折算成奖牌等级；不同任务的分数尺度用「相对人类分布的百分位」统一。
- **METR 关于 agent 任务时间跨度（time horizon）的系列工作** —
  解决「怎么把不同难度的任务统一到一根有物理意义的轴上」：
  不问成功率，问「这个 agent 能以 50% 成功率完成的任务，人类专家要花多久」。
  好处是可跨基准比较，坏处是需要为每个任务标注可靠的人类耗时。

## 五 · 评测方法论与统计 · Methodology & Statistics

- ★ **Sayash Kapoor, Benedikt Stroebl, et al., _AI Agents That Matter_（2024）** —
  解决「为什么 agent 排行榜的数字不可靠」。三条核心论点与本课模块 05 完全一致：
  **① 不报成本的准确率是无意义的**（准确率可以靠多花钱买）、
  **② 应当报告成本-精度的帕累托前沿而非单点**、
  **③ agent 评测普遍缺乏可复现性与标准化 harness**。
  **如果这份清单只读一篇，读这篇。**
- ★ **Mark Chen et al., _Evaluating Large Language Models Trained on Code_（2021）** —
  解决「怎么用 $n$ 次采样无偏地估计 pass@k」：$1-\binom{n-c}{k}/\binom{n}{k}$。
  **本课模块 04 的两个无偏估计器都源自这篇的思路**（pass^k 是同一思路的对偶形式）。
- ★ **Evan Miller, _Adding Error Bars to Evals_（2024）** —
  解决「评测报告该怎么算和报误差」：中心极限定理、方差削减、配对设计、聚类结构。
  **本课模块 04 第 4 节「把 $Nk$ 条 rollout 当独立样本是错的」直接对应这篇的聚类讨论。**
- **Bradley Efron & Robert Tibshirani, _An Introduction to the Bootstrap_（Chapman & Hall, 1993）** —
  解决「不做分布假设怎么算置信区间」，以及**分组数据该怎么重采样**。
  记住一句话即可：自举要重采样最外层的独立单位。
- **Rogan & Gladen, _Estimating Prevalence from the Results of a Screening Test_
  （American Journal of Epidemiology, 1978）** —
  解决「检测手段本身不完美时，怎么从观测阳性率反推真实患病率」。
  **本课模块 02 把它整个搬到了判分器上**：$\hat p_{\text{corrected}}=(\hat p_{\text{obs}}-\alpha)/(1-\beta-\alpha)$。
  校正结果可能落到 $[0,1]$ 之外，这一点在原文里也有讨论——那是信号不是 bug。
- **Quinn McNemar（1947）与两比例检验的功效分析标准教材** —
  解决「配对二值数据怎么做显著性检验」以及「要多少样本才够」。
  本课模块 04 第 3、5 节的样本量公式全部来自这套标准结果。

## 六 · 过程监督与轨迹 · Process Supervision & Trajectories

- ★ **Hunter Lightman et al., _Let's Verify Step by Step_（2023）** —
  解决「过程监督与结果监督哪个更好」：在需要长链推理且中间步骤可验证的任务上，
  **过程监督显著优于结果监督**——因为结果监督会把「过程全错但答案蒙对」的样本当作正例。
  本课模块 03 第 5 节把这个结论翻译成 agent 评测的三条实践规则。
- **Jonathan Uesato et al., _Solving Math Word Problems with Process- and Outcome-based Feedback_
  （2022）** — 同一问题的更早期系统研究，给出了两种反馈方式在最终答案正确率与推理正确率上的分解。
- **Shunyu Yao et al., _ReAct: Synergizing Reasoning and Acting in Language Models_（ICLR 2023）** —
  解决「agent 的轨迹该长什么样」：thought / action / observation 三段式。
  本课模块 03 的日志 schema 是这个结构的工程化版本。
- **OpenTelemetry _Semantic Conventions for Generative AI_（`gen_ai.*` span 属性）** —
  解决「轨迹字段名该怎么起」。沿用标准字段名的理由不是它更优雅，
  而是**现成的 trace 查看器（Jaeger / Tempo / Phoenix 等）可以直接用**——这个理由已经足够。
- **Mike Papadakis, Marinos Kintis, Jie Zhang et al., _Mutation Testing Advances: An Analysis and Survey_
  （Advances in Computers, 2019）** —
  解决「怎么量化一组测试的强度」。本课模块 02 用它来回答「这个判分器可不可信」，
  工具层面对应 `mutmut` / `cosmic-ray`。

## 七 · 报告规范与工具 · Reporting & Tooling

- **Margaret Mitchell et al., _Model Cards for Model Reporting_（FAT* 2019）** —
  解决「一份模型报告的最小集合是什么」。本课模块 05 的**评测卡（eval card）**是这个思想在
  agent 评测上的具体化：让读者在不重跑实验的情况下判断这个数字能不能用。
- **UK AI Safety Institute, `inspect_ai` 框架文档** —
  解决「怎么把 eval 写成声明式的 task / solver / scorer 三件套」，
  以及 `--epochs`、`sandbox="docker"` 这些直接对应本课统计与可复现性要求的参数。
  **C68 会把这套框架的设计思想整个展开。**
- **SWE-bench 官方评测 harness（容器化、逐条起容器跑测试）** —
  解决「怎么把判分做成可复现的流水线」。
  值得注意的实现细节：`--max_workers` 会影响超时行为，**因此并发度是 harness 的一部分**，
  必须写进报告——这是本课模块 05 复现清单第 7 条的出处。
- **`vcrpy`（HTTP 录制回放）** —
  解决「必须联网的评测怎么做到可复现」。注意 `filter_headers` 一定要过滤掉密钥，
  否则录制文件里会留下凭证。
