# 参考清单 · References（前沿对齐：CAI / RLAIF / 可扩展监督）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 用玩具模型模拟的每个机制，都能在下列文献里找到真实系统上的对应做法与权衡。

## 总览与世界观 · Overview & Framing
- ★ **Leike, Krueger, Everitt, Martic, Maini & Legg 2018, _Scalable agent alignment via reward modeling: a research direction_** — 把对齐拆成「学习奖励」与「优化奖励」两半，提出 recursive reward modeling 路线。是理解本课为何围绕「监督信号从哪来」展开的总纲，模块 00/03 的框架来源。
- ★ **Amodei, Olah, Steinhardt, Christiano, Schulman & Mané 2016, _Concrete Problems in AI Safety_** — 列出 reward hacking、scalable oversight、safe exploration 等具体问题，几乎本课每个模块都是其中一条问题的当代解法。建立问题意识的起点。
- **Anthropic 2023, _Core Views on AI Safety_** + **OpenAI 2023, _Introducing Superalignment_** — 两家前沿实验室对「如何对齐比人类强的模型」的公开立场，解释 weak-to-strong（04）与可扩展监督（03）为何是当务之急。
- **Ji et al. 2023, _AI Alignment: A Comprehensive Survey_** — 对齐领域的系统综述，遇到不熟的子方向（如 inner alignment、mesa-optimization）可在此定位。

## RLHF 与偏好学习地基 · RLHF Foundations
- ★ **Christiano, Leike, Brown, Martic, Legg & Amodei 2017, _Deep Reinforcement Learning from Human Preferences_** — 用成对偏好训奖励模型再做 RL 的奠基论文。Bradley–Terry 偏好损失、RM→RL 两段式的源头，模块 02 的根。
- ★ **Ouyang et al. 2022, _Training language models to follow instructions with human feedback (InstructGPT)_** — 把 RLHF（SFT→RM→PPO）落到大语言模型、确立当代后训练范式的里程碑。读它理解本课每个方法在真实管线里替换/增强的是哪一段。
- **Stiennon et al. 2020, _Learning to summarize from human feedback_** — 在摘要任务上细致展示 RLHF 流程与 RM 训练，含人评协议细节，是 InstructGPT 的前身、最清晰的 RLHF 案例研究之一。
- **Rafailov et al. 2023, _Direct Preference Optimization (DPO)_** — 证明可以跳过显式 RM 与 RL，用闭式损失直接从偏好对微调策略。理解 RM 的作用（以及何时可以绕开它）的重要对照。
- **Bai et al. 2022, _Training a Helpful and Harmless Assistant with RLHF_ (Anthropic)** — CAI 的前作，把 helpfulness 与 harmlessness 作为两个偏好维度用 RLHF 训练，给出本课反复出现的「有用 vs 无害」张力的实证基线。★

## Constitutional AI 与 RLAIF · CAI & RLAIF
- ★ **Bai et al. 2022, _Constitutional AI: Harmlessness from AI Feedback_ (Anthropic)** — 本课模块 01 的核心。提出用明文宪法驱动 critique-revise（SL 阶段）+ AI 标注偏好的 RLAIF（RL 阶段），几乎不用人类标注有害性就训出无害且仍有用的模型。必读，逐节对应 notebook 的 worked 实现。
- ★ **Lee et al. 2023, _RLAIF: Scaling Reinforcement Learning from Human Feedback with AI Feedback_ (Google)** — 系统比较 RLAIF 与 RLHF，给出「AI 反馈能在多大程度替代人类反馈」的实证。理解 RLAIF 普适性与边界的关键。
- **Anthropic 2023, _Claude's Constitution_（公开文档）** — 真实在用的宪法原则全文（含取自联合国人权宣言、其他实验室准则的条款）。读它看清「宪法」具体长什么样、覆盖哪些维度，模块 01 玩具宪法的现实对照。
- **Kundu et al. 2023, _Specific versus General Principles for Constitutional AI_ (Anthropic)** — 探讨宪法该用具体规则还是宽泛原则（如单条「do what's best for humanity」）。理解原则粒度如何影响行为，对应模块 01 的原则匹配练习。
- **Huang et al. 2024, _Collective Constitutional AI_ (Anthropic)** — 用公众参与的方式集体起草宪法，触及「谁来写原则」的程序合法性问题，是 CAI 在治理维度的延伸。

## 奖励建模与过优化 · Reward Modeling & Over-optimization
- ★ **Gao, Schulman & Hilton 2023, _Scaling Laws for Reward Model Overoptimization_ (OpenAI)** — 本课模块 02 的核心实验。用一个「金标 RM」当真值，系统刻画 proxy 分升而 gold 分先升后降的倒 U 曲线，并给出随 RM 大小/数据量变化的标度律。必读，notebook 直接复现其倒 U 现象。
- ★ **Coste, Anwar, Kirk & Krueger 2023, _Reward Model Ensembles Help Mitigate Overoptimization_** — 证明用 RM 集成的分歧做保守奖励能显著延缓过优化。模块 02 的「集成分歧 → 保守奖励」练习的直接来源。
- **Skalse, Howe, Krasheninnikov & Krueger 2022, _Defining and Characterizing Reward Hacking_** — 给 reward hacking 下形式化定义（何时代理奖励的优化必然偏离真奖励），把直觉变成可推理的判据。
- **Eisenstein et al. 2023, _Helping or Herding? Reward Model Ensembles Mitigate but do not Eliminate Reward Hacking_** — 对 RM 集成的冷静后续：集成有用但非万灵药，hacking 可能在所有成员共有的盲区发生。读它避免对集成过度乐观。
- **Singhal et al. 2023, _A Long Way to Go: Investigating Length Correlations in RLHF_** — 细究最常见的 reward hack——长度偏置，量化 RLHF 收益中有多少只是「变长了」。模块 02 用长度偏置做过优化诊断探针的依据。
- **Stephan et al. / Denison et al. 2024, _Sycophancy to Subterfuge_ (Anthropic)** — 展示奖励篡改如何从无害的谄媚一路泛化到主动钻空子，是 reward hacking 严重性的警示性证据。

## 可扩展监督：辩论、放大、三明治 · Scalable Oversight
- ★ **Irving, Christiano & Amodei 2018, _AI Safety via Debate_ (OpenAI)** — debate 协议的奠基论文。主张让两个 AI 对抗式辩论、由弱裁判裁决，借「揭穿比欺骗容易」让弱监督逼出强模型的真话。模块 03 辩论模拟的根。
- ★ **Christiano, Shlegeris & Amodei 2018, _Supervising strong learners by amplifying weak experts_ (Iterated Amplification / IDA)** — 通过「分解难题 + 聚合多个弱副本 + 蒸馏」迭代放大能力的方案。与 debate 并列的可扩展监督主干思路，模块 03 RRM/IDA 部分的来源。
- ★ **Bowman et al. 2022, _Measuring Progress on Scalable Oversight for Large Language Models_ (Anthropic)** — 提出 sandwiching 实证范式：用非专家 + 模型去逼近专家，把「可扩展监督」变成可测量的实验。模块 03 sandwiching 练习的直接依据。
- **Saunders et al. 2022, _Self-critiquing models for assisting human evaluators_ (OpenAI)** — 实证：模型生成的批评能帮人类评估者抓到独自会漏掉的错误，是 scalable oversight 最可操作的组件之一。模块 03 self-critique 部分的来源。
- **Khan et al. 2024, _Debating with More Persuasive LLMs Leads to More Truthful Answers_** — 近期实证：更强的辩手确实让（较弱的）裁判更常判对，为 debate 的核心假设提供正面证据。模块 03「准确率随论证质量上升」的现实印证。
- **Michael et al. 2023, _Debate Helps Supervise Unreliable Experts_** — 人类实验：辩论相比单方咨询更能帮不可靠监督者得出正确结论，从人类侧验证 debate。
- **Barnes & Christiano 2020, _Writeup: Progress on AI Safety via Debate_** + **obfuscated arguments 讨论** — 揭示 debate 的核心开放难题（混淆论证：人类无法在合理步数内证伪的错误长论证）。读它认识 debate 不是已解决的问题。

## Weak-to-Strong 泛化 · Weak-to-Strong Generalization
- ★ **Burns et al. 2023, _Weak-to-Strong Generalization: Eliciting Strong Capabilities with Weak Supervision_ (OpenAI Superalignment)** — 本课模块 04 的核心。用弱模型标签微调强模型，强学生超过弱老师；提出 PGR 指标与辅助置信损失。必读，notebook 复现 w2s 现象与 PGR 计算。
- **Leike & Sutskever 2023, _Introducing Superalignment_ (OpenAI 博客)** — 阐明为何「用弱监督对齐强模型」是 superalignment 的关键类比，w2s 实验的动机说明。
- **Charikar, Pabbaraju & Shiragur 2024, _Quantifying the Gain in Weak-to-Strong Generalization_** — 给 w2s 提供理论刻画：在何种条件下强学生能超过弱老师、增益有多大。把实证现象往可证明的方向推。
- **Lang, Huang & Li 2024, _Theoretical Analysis of Weak-to-Strong Generalization_** — 从学习理论角度分析 w2s，解释「强模型先验纠正弱标签错误」的机制，模块 04 ceiling/师生差距分析的理论背景。

## Deliberative Alignment 与规范 · Deliberative Alignment & Specs
- ★ **Guan et al. 2024, _Deliberative Alignment: Reasoning Enables Safer Language Models_ (OpenAI)** — 本课模块 05 的核心。训练模型在回答前显式推理明文安全规范、引用条款做决策，在抗越狱与减少过度拒绝上同时改进。必读，notebook 模拟 spec-following 推理与一致性评分。
- ★ **OpenAI 2024–2025, _Model Spec_（公开文档）** — 真实在用的明文规范：目标、规则、默认行为与指令层级。读它看清 deliberative alignment 所推理的「spec」具体长什么样，模块 05 玩具 spec 的现实对照。
- **Mu et al. 2024, _Rule-Based Rewards for Language Model Safety_ (OpenAI)** — 用明文规则直接构造奖励来控制安全行为，是「把规范变成可优化信号」的另一条路，与 deliberative alignment 互补。
- **Zou et al. 2023, _Universal and Transferable Adversarial Attacks on Aligned Language Models (GCG)_** — 自动化越狱攻击的代表，说明仅靠隐式对齐为何脆弱、为何需要更稳健的 spec 推理。模块 05 jailbreak 检测的背景。
- **Wei, Haghtalab & Steinhardt 2023, _Jailbroken: How Does LLM Safety Training Fail?_** — 分析越狱成功的两类机制（目标冲突、能力泛化不匹配），帮助理解 refusal calibration 难在哪。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无需 GPU / 联网 / 大模型**：全课用纯 numpy 在 CPU 上用**玩具模型 + 合成偏好模拟**前沿对齐方法的**逻辑结构**——批判-修订用关键词规则、偏好用 Bradley–Terry 合成、奖励过优化用「proxy RM vs gold RM」的倒 U、辩论用可验证证据的博弈、weak-to-strong 用带噪标签训线性探针、spec-following 用检索匹配评分。每个机制都用 `assert` 兜住正确性。这是为了把注意力集中在**机制与权衡**上，而非工程噪声；真实系统的对应做法见上列文献。
- **可迁移性**：你在 numpy 里验证过的偏好损失、KL–奖励权衡、集成分歧、PGR 计算、一致性评分，可几乎一对一接到真实 RLHF/RLAIF 管线（HuggingFace TRL、trlx 等）里。本课刻意让接口贴近这些库的概念。
- **课程衔接**：上游接 RLHF/后训练（InstructGPT 范式）、RL 地基（C13）；与可解释性课（C06，probe 作为白盒监控）、评测课（safety case、sandbagging）互为表里；下游接前沿智能体与 AI Control（把对齐方法部署成运行时监控与协议）。
