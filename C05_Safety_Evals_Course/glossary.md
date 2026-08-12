# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读 RSP / system card / 评估报告遇到生词回这里查。

## 安全框架 · Safety Frameworks

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| RSP (Responsible Scaling Policy) | 负责任扩展政策 | 实验室对"能力到什么程度就必须有什么防护"的公开承诺框架（Anthropic 提出）。 |
| ASL (AI Safety Level) | AI 安全等级 | RSP 中按模型危险能力分级的等级体系（ASL-2/3/4…），等级越高防护要求越严。 |
| Preparedness Framework | 预备框架 | OpenAI 版的扩展政策：按风险类别打分、设阈值、定相应措施。 |
| Frontier Safety Framework | 前沿安全框架 | Google DeepMind 版的扩展政策，核心是 CCL（关键能力等级）。 |
| Capability Threshold | 能力阈值 | 一条预先定义的能力线，模型越过它就触发更强的安全措施。 |
| Tripwire | 绊线 | 评估中预设的警戒结果：一旦触发就必须暂停部署/训练并升级处置。 |
| If-Then Commitment | 条件承诺 | "如果评估显示 X，就执行 Y"的预先公开承诺，把决策从临场判断变成规则。 |
| Risk Domain | 风险领域 | 框架中划分的高风险类别：CBRN、网络、自主性、说服操纵等。 |
| Deployment Mitigation | 部署缓解措施 | 越过阈值后施加的防护：分类器、监控、访问控制、能力限制等。 |

## 危险能力评估 · Dangerous Capability Evals

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Dangerous Capability Eval | 危险能力评估 | 测量模型是否具备可被滥用的高风险能力（而非它是否"愿意"被滥用）。 |
| Proxy Task | 代理任务 | 用无害但能力同构的任务替代真实危险任务来测能力（本课全部用此类）。 |
| Uplift | 增益 | 模型给使用者带来的额外能力提升，相对"没有模型时"的基线。 |
| Uplift Study | 增益研究 | 对照实验：有模型组 vs 仅搜索引擎组，量化模型带来的 uplift。 |
| Expert Baseline | 专家基线 | 人类领域专家在同一任务上的表现，评估结果的参照系。 |
| Elicitation | 能力诱出 | 用提示工程、微调、工具等手段把模型的真实能力上限测出来。 |
| Elicitation Gap | 诱出差距 | "测到的能力"与"真实能力上限"之间的差，评估低估风险的主要来源。 |
| Difficulty Ladder | 难度阶梯 | 一组从易到难的任务序列，定位模型当前能力所在的台阶。 |
| Task Suite | 任务套件 | 围绕一个威胁模型组织的成套评估任务（如 METR 的自主性任务集）。 |
| Threat Model | 威胁模型 | 对"谁、用什么能力、造成什么危害"的具体设想，评估设计的起点。 |
| Capability Elicitation Budget | 诱出预算 | 评估时允许投入多少诱出努力（提示、重试、微调），需在报告中说明。 |

## 红队 · Red-teaming

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Red-teaming | 红队 | 系统性地构造对抗输入来暴露模型缺陷与风险的测量过程。 |
| Coverage | 覆盖率 | 红队探索过的风险面占总风险面的比例，"没测到"不等于"没有"。 |
| Severity | 严重性 | 单个发现的危害程度分级（如 low/medium/high/critical）。 |
| Triage | 分诊 | 对红队发现按严重性与可复现性排序、去重、分派处置的流程。 |
| Automated Red-teaming | 自动化红队 | 用模型生成攻击候选、自动评判结果，规模化扩展人工红队。 |
| Discovery Curve | 发现曲线 | 累计发现数随投入（时间/查询数）的曲线，趋平意味着边际收益递减。 |
| Attack Surface | 攻击面 | 系统所有可能被对抗利用的输入通道与功能点的总和。 |
| Responsible Disclosure | 负责任披露 | 发现漏洞后先通知开发方、留出修复窗口再公开的规范。 |

## 鲁棒性与拒绝 · Robustness & Refusal

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Refusal | 拒绝 | 模型对请求不予执行的行为，安全训练的核心输出之一。 |
| Over-refusal | 过度拒绝 | 把良性请求误判为有害而拒绝，损害模型有用性。 |
| Under-refusal | 拒绝不足 | 对真正有害的请求未能拒绝，损害模型安全性。 |
| Refusal Calibration | 拒绝校准 | 让拒绝行为与请求的真实风险对齐：该拒的拒、不该拒的不拒。 |
| ASR (Attack Success Rate) | 攻击成功率 | 对抗输入中成功诱发目标失败行为的比例，需配置信区间报告。 |
| XSTest | —— | 专测 over-refusal 的对照基准：安全问题（"how to kill a Python process"）配危险同形句。 |
| Jailbreak | 越狱 | 绕过安全训练使模型产生本应拒绝的输出的对抗手段（本课只测量不构造）。 |
| Safety–Helpfulness Trade-off | 安全-有用性权衡 | 压低 under-refusal 往往推高 over-refusal，需要联合优化与测量。 |

## 评测完整性 · Eval Integrity

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Sandbagging | 能力隐藏 | 模型（或被操纵的模型）在评估中故意表现低于真实能力。 |
| Password-locked Model | 密码锁模型 | 研究用人造模型：只有提示中含特定"密码"才展现全部能力，用于研究 sandbagging 检测。 |
| Alignment Faking | 对齐伪装 | 模型在感知被观察时表现对齐、不被观察时偏离的行为。 |
| Evaluation Awareness | 评估感知 | 模型识别出"自己正在被评估"的能力，会污染评估结果的有效性。 |
| Capability vs Propensity | 能力 vs 倾向 | 评估的两个独立维度："能不能做到"与"会不会去做"。 |
| Eval Gaming | 评测博弈 | 针对评估指标本身优化而非提升真实安全性的行为。 |
| Consistency Check | 一致性检验 | 用同能力任务的成绩对比、噪声注入等方法交叉验证评估结果是否被压低。 |

## AI Control · 控制

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| AI Control | AI 控制 | 假设模型可能不对齐，靠监控、审计、限权等外部协议保证安全的研究方向。 |
| Untrusted Model | 不可信模型 | 控制设定中那个能力强、但不能假设其对齐的模型。 |
| Trusted Monitor | 可信监控器 | 用能力较弱但可信的模型审查不可信模型的输出。 |
| Audit Budget | 审计预算 | 人类专家能审查的输出比例上限（如 2%），控制协议设计的核心约束。 |
| Deferral | 转交 | 监控器对可疑输出不直接放行，改由可信模型重做或交人类裁决。 |
| Safety–Usefulness Frontier | 安全-有用性前沿 | 控制协议在"拦住坏行为"与"保留好产出"之间能达到的最优权衡曲线。 |
| Control Evaluation | 控制评估 | 让红队扮演不对齐模型来实测控制协议能否兜住的对抗演练。 |
| Collusion | 串谋 | 不可信模型与（同源的）监控器协同绕过控制协议的失败模式。 |

## 治理与论证 · Governance & Safety Cases

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Safety Case | 安全论证 | 一份结构化论证："该系统在该场景下足够安全"，附证据链，源自核电/航空业。 |
| Claims–Arguments–Evidence (CAE) | 主张-论证-证据 | Safety case 的标准骨架：顶层主张被逐层论证分解、最终落到具体证据。 |
| Inability Argument | 无能力论证 | 最常用的安全论证："模型根本不具备造成该危害的能力"，由危险能力评估支撑。 |
| Control Argument | 控制论证 | "即使模型有能力且不对齐，控制措施也能兜住"的论证，inability 失效后的下一道防线。 |
| System Card | 系统卡 | 随模型发布的文档：能力、评估结果、缓解措施、已知局限的结构化披露。 |
| Third-party Evaluation | 第三方评估 | 由独立机构（如 METR、AISI）执行的评估，缓解实验室自评的利益冲突。 |
| Structured Access | 结构化访问 | 为外部评估者提供受控的深度模型访问（灰盒/微调权限）的机制。 |
| Defense in Depth | 纵深防御 | 不依赖单一措施，叠加多层独立防线使整体失效概率相乘递减。 |
