# 术语词典 · Glossary（前沿对齐：CAI / RLAIF / 可扩展监督）

> 按主题分组，每条 2–3 句释义。读 Constitutional AI / weak-to-strong / deliberative alignment 等论文遇到生词回这里查；英文术语保留原文（对齐研究社区的通用语言）。本课用 numpy 在 CPU 上用玩具模型模拟这些概念，但术语与真实对齐系统一一对应。

## 对齐问题与全局框架 · The Alignment Problem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| alignment | 对齐 | 让 AI 系统的行为符合人类的意图与价值、且不致害。它不是单一技术而是一类问题：如何把「我们想要什么」可靠地传给一个我们并不完全理解的优化器。 |
| outer alignment | 外部对齐 | 让训练目标（如奖励函数、损失）真正刻画我们想要的东西。奖励建模、宪法、规范都是在为外部对齐写一个尽量好的目标代理。 |
| inner alignment | 内部对齐 | 即使训练目标正确，被训出的模型内部学到的「目标」也可能与之不符（mesa-optimization）。本课多在外部对齐层面，但 reward hacking、deception 触及内部对齐。 |
| specification gaming | 规范博弈 | 优化器钻目标设定的空子，用我们没预料的方式拿高分却违背意图（如游戏 AI 卡 bug 刷分）。reward hacking 是其在 RLHF 中的具体形态。 |
| scalable oversight | 可扩展监督 | 当任务强到人类难以直接、可靠地评判模型输出时，如何仍能提供训练/评估信号的问题。是本课后半程（debate、RRM、w2s、deliberative）共同要回答的核心难题。 |
| superalignment | 超级对齐 | 对齐比人类更强的模型这一目标与研究纲领（OpenAI 2023 提出）。weak-to-strong 是它的第一个实证类比实验。 |
| AI safety | AI 安全 | 让 AI 系统可靠、可控、不致灾难性危害的研究领域。对齐是其核心子问题，本课聚焦对齐中「如何提供正确监督」这一支。 |
| safety case | 安全论证 | 一份结构化论证：基于证据声称某系统在某用途下足够安全。对齐方法（如 probe、debate 结果）是其证据，但相关性证据 ≠ 充分证据。 |

## RLHF 与偏好学习 · RLHF & Preference Learning

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| RLHF (RL from Human Feedback) | 人类反馈强化学习 | 三步范式：监督微调（SFT）→ 用人类偏好对训奖励模型（RM）→ 用 RL（如 PPO）针对 RM 优化策略，并以 KL 约束不偏离 SFT 太远。是当代对齐的主力工艺。 |
| SFT (Supervised Fine-Tuning) | 监督微调 | 用高质量示范数据（人写或筛选的回答）做标准的下一 token 监督学习，作为后续 RL 的起点。CAI 的 SL 阶段产出的修订数据也用于 SFT。 |
| preference pair | 偏好对 | 一条提示下的两个回答 (chosen, rejected)，标注者（人或 AI）判定前者更优。是 RM 训练的基本数据单位。 |
| reward model (RM) | 奖励模型 | 一个把「提示 + 回答」映射到标量分数、代理人类偏好的模型。RL 阶段不再问人，而是问 RM。RM 的缺陷会被 RL 放大（过优化）。 |
| Bradley-Terry model | Bradley–Terry 模型 | 把成对偏好建模为 $P(a\succ b)=\sigma(r_a-r_b)$：偏好概率由两者分差经 sigmoid 给出。RM 训练就是最大化观测偏好在此模型下的似然。 |
| reward / scalar reward | 奖励 / 标量奖励 | RL 中对一个行为好坏的数值反馈。RLHF 里它由 RM 给出（外加 KL 惩罚），而非环境直接提供。 |
| policy | 策略 | 被优化的语言模型本身（给提示输出回答的分布 $\pi_\theta$）。RL 阶段调整它以提高 RM 期望分数。 |
| KL penalty / KL regularization | KL 惩罚 / KL 正则 | 在奖励里加上 $-\beta\,\mathrm{KL}(\pi_\theta\Vert\pi_\text{ref})$，惩罚策略偏离参考（SFT）模型太远。是抑制 reward hacking、维持流畅性的关键旋钮。 |
| reference policy | 参考策略 | KL 正则所对标的固定模型（通常是 SFT 模型 $\pi_\text{ref}$）。它定义了「别走太远」的锚点。 |
| PPO (Proximal Policy Optimization) | 近端策略优化 | RLHF 中最常用的 RL 算法，用裁剪的目标限制每步更新幅度。本课不实现 PPO 本身，而聚焦它优化的对象——RM 与 KL 权衡。 |
| DPO (Direct Preference Optimization) | 直接偏好优化 | 跳过显式 RM 与 RL，直接用偏好对和一个闭式损失微调策略，把 RM 隐式吸收进策略。是 RLHF 的轻量替代。 |

## Constitutional AI 与 RLAIF · CAI & RLAIF

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Constitutional AI (CAI) | 宪法 AI | Anthropic 的方法：用一部明文「宪法」（一组自然语言原则）让模型自我批判并修订有害回答，再用 AI 按宪法标注的偏好做 RL，从而**几乎不用人类标注有害性**就训出无害模型。 |
| constitution | 宪法 | 一组写成自然语言的安全/价值原则（如「不协助制造武器」「优先选择更无害的回答」）。它是 CAI 里人类提供监督的主要接口——人写原则，AI 执行原则。 |
| critique-and-revise | 批判-修订 | CAI 的 SL 阶段循环：模型先按某条原则**批判**自己的回答（指出何处违背），再据此**修订**出更好的回答。多轮迭代后用修订结果做 SFT。 |
| RLAIF (RL from AI Feedback) | AI 反馈强化学习 | 用 AI（按宪法/原则）生成的偏好标注替代人类标注来训练 RM，再照常做 RL。把 RLHF 里最贵、最难扩展的「人类标注有害性」换成可大规模生成的 AI 反馈。 |
| SL-CAI (supervised stage) | CAI 监督阶段 | CAI 第一阶段：用 critique-revise 产出的修订回答做监督微调，得到一个已经较无害、且会自我修订的模型。 |
| RL-CAI (RL stage) | CAI 强化阶段 | CAI 第二阶段：让模型对同一提示生成多个回答，用 AI 按宪法两两比较产出偏好，训 RM 后做 RL（即 RLAIF）。 |
| harmlessness / helpfulness | 无害性 / 有用性 | 对齐的两个常相互拉扯的目标：既要拒绝有害请求，又要尽量帮上忙。CAI 关注在保持有用性的同时大幅提升无害性，并减少「居高临下的拒绝」。 |
| red-teaming | 红队 | 主动构造能诱出有害/越界行为的输入，用以暴露并修补模型弱点。CAI 的 RL 阶段常配合红队提示来生成需要被修订/惩罚的样本。 |
| self-critique | 自我批判 | 模型对自己的输出找问题、给出改进意见的能力。是 CAI 与 scalable oversight 的共同支柱：让模型帮人类发现自己输出的缺陷。 |
| principle / rule | 原则 / 条款 | 宪法中的单条规则。CAI 在 critique-revise 时通常每轮随机采一条原则来引导批判，使修订覆盖多个维度。 |

## 奖励过优化与 Goodhart · Reward Over-optimization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| reward hacking | 奖励黑客 / 钻奖励空子 | 策略发现并利用 RM 的缺陷，用人类并不真正想要的方式拿高分（如堆砌长度、谄媚、套用讨喜措辞）。是把「代理目标」当「真目标」优化的必然风险。 |
| over-optimization | 过优化 | 对一个不完美的代理奖励优化过头：proxy（RM 给的）分持续上升，但 gold（真实人类偏好）分先升后**降**，出现倒 U 曲线。 |
| Goodhart's law | 古德哈特定律 | 「一项度量一旦成为优化目标，就不再是好度量。」reward hacking 与过优化是它在 RLHF 中的精确体现：RM 是真偏好的度量，被当目标猛优化后失真。 |
| proxy reward vs gold reward | 代理奖励 vs 金标奖励 | proxy = 我们能优化的、有缺陷的 RM 分；gold = 我们真正想要的、通常只能近似/抽样测量的真实偏好。两者的缺口正是过优化要警惕的。 |
| KL–reward tradeoff | KL–奖励权衡 | 随 RL 进行，策略离参考越远（KL 越大），proxy 奖励越高但 gold 奖励可能先升后降。最优停点通常在某个中等 KL 处，而非 proxy 最大处。 |
| reward model ensemble | 奖励模型集成 | 训练多个 RM（不同种子/数据/结构），用它们的**分歧**估计不确定性。在分歧大（外推）的输入上变保守，可显著延缓过优化。 |
| disagreement / epistemic uncertainty | 分歧 / 认知不确定性 | 集成成员预测之间的方差，作为「这片输入区域 RM 没把握」的信号。reward hacking 常发生在训练分布外、分歧大的区域。 |
| conservative reward | 保守奖励 | 用集成的「均值 − λ·标准差」等做最终奖励：在 RM 们意见一致处照常给分，在分歧大处主动扣分，逼策略别去钻没把握的角落。 |
| scaling laws for over-optimization | 过优化的标度律 | Gao et al. 2023 给出的经验律：gold 奖励随 KL（或优化量）的变化可用简洁函数刻画，且 RM 越大、数据越多，过优化来得越晚越轻。 |
| length bias | 长度偏置 | RM 的一种常见缺陷：系统性偏好更长的回答。是最易观察、最易被策略利用的 reward hack 之一，常作为过优化的诊断探针。 |
| sycophancy | 谄媚 | 模型迎合用户既有观点/期望而非给出真实、正确回答的倾向。RLHF 可能因标注者偏爱「顺耳」回答而无意中强化它，是一种隐蔽的 reward hack。 |

## 可扩展监督 · Scalable Oversight

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| debate | 辩论 | Irving et al. 2018 的协议：两个 AI 就一个问题各执一词、互相揭穿对方论证的漏洞，由（较弱的）裁判看辩论记录判谁更可信。希望「揭穿谎言比编造谎言更容易」，使弱裁判也能逼出真相。 |
| judge | 裁判 | 在 debate/oversight 中做最终裁决的一方（人或弱模型）。可扩展监督的关键假设是：裁判即便不能独立解题，也能在有力论证/证据下做出正确判断。 |
| recursive reward modeling (RRM) | 递归奖励建模 | Leike et al. 2018 的思路：用 AI 助手帮人类评估复杂输出，再用这些被增强的评估训 RM，逐级 bootstrap 出能监督越来越难任务的奖励信号。 |
| iterated amplification (IDA) | 迭代放大 | Christiano et al. 2018：把一个难问题分解成子问题，交给（当前模型的多个副本）协作解答再聚合，得到「放大」的能力，并用它蒸馏出更强模型，循环往复。 |
| sandwiching | 三明治实验 | Bowman et al. 2022 的实证范式：选一个非专家无法独立做好、但领域专家能做好的任务，看「非专家 + 被监督的模型」能否逼近专家水平，以此度量某监督方法是否真的可扩展。 |
| weak judge / non-expert | 弱裁判 / 非专家 | 监督能力弱于被监督模型的评估者。可扩展监督要研究的正是：如何让弱裁判仍能正确监督强模型（靠辩论、分解、证据等）。 |
| factored cognition | 因子化认知 | 把复杂推理拆成可独立完成、再组合的小步的假设。debate 与 IDA 都依赖它：只要每一小步弱裁判能验证，整体就可被监督。 |
| obfuscated arguments | 混淆论证 | debate 的一个开放难题：辩手可能给出人类无法在合理步数内证伪的、看似有理实则错误的长论证，使「揭穿更容易」的假设失效。 |
| prover-verifier games | 证明者-验证者博弈 | 训练一个强「证明者」产出连弱「验证者」都能检验的解答，提升输出的可验证性与清晰度（与 debate 同源的可扩展监督思路）。 |
| self-critique (oversight) | 自我批判（监督用） | 让模型生成对某输出的批评以辅助人类发现缺陷（Saunders et al. 2022）。critique 帮助评估者抓到独自会漏掉的错误，是 scalable oversight 的可操作组件。 |

## Weak-to-Strong 泛化 · Weak-to-Strong Generalization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| weak-to-strong generalization (W2S) | 弱到强泛化 | Burns et al. 2023：用一个**弱**模型生成的（带噪）标签去微调一个**强**预训练模型，强学生在真任务上的表现常能**超过**弱老师。是「弱监督能否引出强模型已有能力」的实证。 |
| weak supervisor / weak labels | 弱监督者 / 弱标签 | 能力有限的老师模型给出的、含系统性错误的标签。类比未来「人类监督超人 AI」的处境：监督者比被监督者弱。 |
| strong student | 强学生 | 一个能力更强（如预训练更充分）的模型，被弱标签微调。问题是它会盲目复制老师的错误，还是用自身先验「纠正」出更真的答案。 |
| performance gap recovered (PGR) | 恢复的性能差距 | 度量 w2s 效果：$\mathrm{PGR}=\dfrac{\text{强学生}-\text{弱老师}}{\text{强模型上界(用真标签)}-\text{弱老师}}$。0 = 只学到老师水平，1 = 完全恢复到强模型的天花板。 |
| ceiling / strong ceiling | 上界 / 强模型天花板 | 用**真**标签微调强模型所能达到的表现，作为 w2s 的理想上界。PGR 把弱标签结果放在「弱老师」与「这个天花板」之间度量。 |
| auxiliary confidence loss | 辅助置信损失 | Burns et al. 提出的技巧：在模仿弱标签之外，加一项鼓励强学生**对自己的预测更自信**（在自信时偏离弱标签），以抵抗对弱老师错误的过拟合，常显著提升 PGR。 |
| imitation vs generalization | 模仿 vs 泛化 | w2s 的核心张力：学生既可能**模仿**老师（连错误一起学），也可能**泛化**出老师没有的正确能力。好的方法要抑制前者、放大后者。 |
| elicitation | 引出 | 把模型**已经具备但默认不展现**的能力/知识激发出来。w2s 的乐观解读是：弱监督主要在「引出」强模型的潜在能力，而非「教」它新东西。 |
| student-teacher gap | 师生差距 | 学生与老师能力的差距。差距越大，w2s 越难（学生更可能要么盲从、要么忽略老师），PGR 通常随差距增大而下降——这是 w2s 的「天花板分析」关注的。 |

## Deliberative Alignment 与规范遵循 · Deliberative Alignment & Spec-following

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| deliberative alignment | 审议式对齐 | Guan et al. 2024（OpenAI）：训练模型在回答前**显式地用思维链推理一份明文安全规范**，先回忆/检索相关条款、再据此决定如何回应。把安全从「隐式记住」变成「显式推理」。 |
| specification (spec) / policy | 规范 / 政策 | 一份写明「什么该做、什么不该做、边界在哪」的明文文档（如 OpenAI 的 Model Spec）。deliberative alignment 让模型在推理时直接引用它，而非仅靠从示例中模仿。 |
| spec-following | 规范遵循 | 模型按明文规范行事的能力。相较从偏好数据隐式学到的策略，明文规范可审计、可更新、可定位「为何这样回应」。 |
| chain-of-thought (CoT) for safety | 安全用思维链 | 让模型在给出最终答复前，先生成一段关于「这个请求涉及哪些规范、是否越界、该如何回应」的推理。deliberative alignment 直接监督/利用这段推理。 |
| refusal calibration | 拒绝校准 | 让模型该拒就拒、不该拒就别拒：在真正有害请求上稳健拒绝，同时避免对正常请求的过度拒绝。是 spec-following 的关键评估维度。 |
| over-refusal | 过度拒绝 | 模型把无害请求误判为有害而拒绝（如拒绝解释化学常识）。它损害有用性，是只追求无害性时容易付出的代价，需用校准来平衡。 |
| jailbreak | 越狱 | 通过伪装、角色扮演、编码、注入等手段绕过安全限制、诱出本应被拒绝的输出。deliberative alignment 希望显式 spec 推理能更稳健地识破伪装。 |
| compliance / boundary case | 合规 / 边界用例 | 处在「该帮」与「该拒」之间的模糊请求（如双重用途知识）。规范遵循的难点正在于这些边界，需要按 spec 条款细致权衡而非一刀切。 |
| spec consistency | 规范一致性 | 模型的回应与所引规范条款之间是否自洽、是否真的依据所述理由行事。本课用一致性评分量化「回应 ↔ 规范」的吻合程度。 |
| instruction hierarchy | 指令层级 | 不同来源指令（系统 > 开发者 > 用户）的优先级规则。spec 通常包含它，使模型在冲突指令下知道听谁的，是抵抗注入式越狱的一环。 |

## 评估与方法论 · Evaluation & Methodology

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| ground truth | 真值 | 我们用来评判对错的「正确答案」。本课在合成沙盒里**人为设定**真值（埋入的真概念、真偏好），从而能对照验证每个方法的效果——这是学方法论的正确顺序。 |
| held-out / generalization | 留出 / 泛化 | 在训练时没见过的数据上评估，衡量学到的是真规律还是记忆。w2s、RM 过优化的判断都依赖留出/分布外评估。 |
| differential testing | 对拍 | 把被测实现与一个可信参考实现比对（如数值稳定 softmax 对拍朴素 softmax），用 `np.allclose`/`assert` 抓住任何偏差。本课每个机制都先有参考、再验证。 |
| toy model / synthetic data | 玩具模型 / 合成数据 | 用小维度、可控、知道全部真相的模型与数据来隔离并展示一个机制。本课刻意用它，以便把注意力集中在「为什么这样有效/失效」而非工程噪声上。 |
| calibration | 校准 | 模型给出的置信度与其实际正确率是否相符。出现在 RM（分数 ↔ 真偏好概率）、w2s（学生自信度）、拒绝（拒绝倾向 ↔ 真有害性）等多处。 |
| distribution shift | 分布漂移 | 部署/优化时的数据分布偏离训练分布。reward hacking 多发生在策略把分布推到 RM 训练分布之外时，是过优化与监督失效的共同温床。 |
