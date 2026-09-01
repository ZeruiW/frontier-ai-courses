# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读论文遇到生词回这里查。

## 监督微调 · SFT

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Post-training | 后训练 | 预训练之后让基座模型变得"有用且对齐"的全部训练阶段（SFT / RLHF / RLVR 等）。 |
| SFT (Supervised Fine-Tuning) | 监督微调 | 用"指令→回答"示范数据做下一 token 预测，教会基座模型遵循指令。 |
| Chat Template | 对话模板 | 把多轮对话序列化成带特殊标记（如 `<\|im_start\|>`）的训练文本的固定格式。 |
| Loss Masking | 损失掩码 | 只在 assistant 回答 token 上计算损失、把 prompt 部分 label 置 -100 的技巧。 |
| Instruction Following | 指令遵循 | 模型按用户指令的内容与格式要求作答的能力，SFT 的直接目标。 |
| LoRA | 低秩适配 | 给权重矩阵加低秩增量 ΔW=BA 来微调，只训极少参数、省显存的主流方法。 |
| QLoRA | 量化 LoRA | 4-bit 量化基座 + LoRA，单卡即可微调大模型。 |
| Catastrophic Forgetting | 灾难性遗忘 | 微调新数据导致模型丢失预训练阶段已有能力的现象。 |
| Packing | 序列打包 | 把多条短样本拼进同一条训练序列以提高算力利用率的技巧。 |
| Rejection Sampling (Best-of-N) | 拒绝采样 | 采样 N 个回答、用 RM 选最好的拿去做 SFT，介于 SFT 与 RL 之间的简易对齐法。 |

## 奖励模型 · Reward Modeling

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Reward Model (RM) | 奖励模型 | 给"prompt+回答"打标量分、代表人类偏好的模型，RLHF 的优化目标来源。 |
| Preference Pair | 偏好对 | 同一 prompt 下"被选中 (chosen) vs 被拒绝 (rejected)"的一对回答，RM 的训练数据。 |
| Bradley-Terry Model | —— | 把"A 赢过 B 的概率"建模为 σ(r_A − r_B) 的成对比较模型，RM 损失的理论基础。 |
| Reward Hacking | 奖励投机 | 策略找到 RM 的漏洞、刷高奖励分但实际质量没变好（甚至变差）的现象。 |
| Reward Overoptimization | 奖励过优化 | 对代理奖励（proxy RM）优化过头，真实偏好（gold reward）反而下降的规律（Goodhart）。 |
| RewardBench | —— | 系统评测奖励模型判别准确率的基准（chat / safety / reasoning 等维度）。 |
| Proxy vs Gold Reward | 代理/真实奖励 | 代理奖励是 RM 打的分，真实奖励是人类真实偏好；两者的偏差是 reward hacking 的根源。 |

## RLHF 与 PPO

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| RLHF | 人类反馈强化学习 | "偏好数据 → 训 RM → RL 优化策略"的三段式对齐流程（InstructGPT）。 |
| Policy | 策略 | RL 视角下的语言模型本身：给定 prompt（状态）输出 token（动作）的分布。 |
| Policy Gradient | 策略梯度 | 沿"提高高奖励轨迹概率"方向更新策略参数的 RL 方法族（REINFORCE 是最简形式）。 |
| PPO (Proximal Policy Optimization) | 近端策略优化 | 用 clipped surrogate 限制每步更新幅度的策略梯度算法，RLHF 的经典选择。 |
| Clipped Surrogate Objective | 截断代理目标 | PPO 的核心损失：把重要性比率 clip 在 [1−ε, 1+ε]，防止单步更新过猛。 |
| Importance Ratio | 重要性比率 | 新旧策略对同一动作的概率之比 π_new/π_old，PPO 截断的对象。 |
| KL Penalty | KL 惩罚 | 在奖励里减去 β·KL(π‖π_ref)，防止策略漂离参考模型太远、防 reward hacking。 |
| Reference Model | 参考模型 | 冻结的 SFT 模型副本，作为 KL 约束的锚点。 |
| Value Model (Critic) | 价值模型 | 估计状态期望回报的网络，用于计算 advantage、降低梯度方差。 |
| Advantage | 优势 | 某动作比平均水平好多少（A = Q − V），策略梯度的加权系数。 |
| GAE (Generalized Advantage Estimation) | 广义优势估计 | 用 λ 在偏差与方差间折中的 advantage 估计法，PPO 标配。 |
| KL Divergence | KL 散度 | 衡量两个分布差异的非对称度量，对齐训练中约束策略偏移的标尺。 |

## DPO 家族

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| DPO (Direct Preference Optimization) | 直接偏好优化 | 把 RLHF 的带 KL 约束目标解析求解，跳过 RM 和 RL、直接用偏好对训练策略。 |
| Implicit Reward | 隐式奖励 | DPO 推导中策略本身定义的奖励 r = β·log(π/π_ref)，无需显式 RM。 |
| IPO | —— | 把 DPO 的 sigmoid 换成平方损失、缓解对确定性偏好过拟合的变体。 |
| KTO | —— | 基于前景理论、只需"好/坏"单边标注（不需成对偏好）的对齐方法。 |
| SimPO | —— | 去掉参考模型、用长度归一化的平均 log prob 作隐式奖励的简化 DPO 变体。 |
| ORPO | —— | 把偏好的 odds ratio 惩罚项直接并进 SFT 损失、单阶段完成对齐的方法。 |
| Chosen / Rejected | 优选/被拒回答 | 偏好对里的两条回答，DPO 损失同时拉高前者、压低后者的隐式奖励差。 |
| Offline vs Online Alignment | 离线/在线对齐 | 离线（DPO）用固定偏好数据；在线（PPO/GRPO）边采样边训练，分布不漂移但更贵。 |

## RLVR 与推理训练 · RLVR & Reasoning

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| RLVR (RL with Verifiable Rewards) | 可验证奖励强化学习 | 用程序可自动判对错的奖励（数学答案、单测通过）替代 RM 的 RL 训练范式。 |
| Verifiable Reward | 可验证奖励 | 由规则/验证器直接判定的 0/1 奖励，没有 RM 可被 hack 的问题。 |
| GRPO (Group Relative Policy Optimization) | 组相对策略优化 | 同一 prompt 采样一组回答、用组内奖励均值作 baseline，去掉 value model 的 PPO 变体（DeepSeek-R1）。 |
| Group Advantage | 组优势 | GRPO 中每条回答的 advantage = (该回答奖励 − 组内均值)/组内标准差。 |
| Format Reward | 格式奖励 | 奖励模型按规定格式输出（如 `<think>...</think>`）的辅助奖励项。 |
| Chain-of-Thought (CoT) | 思维链 | 模型在给出最终答案前显式生成的中间推理步骤。 |
| ORM (Outcome Reward Model) | 结果奖励模型 | 只看最终答案对错打分的奖励模型。 |
| PRM (Process Reward Model) | 过程奖励模型 | 对推理链的每一步分别打分的奖励模型，监督更密集但标注更贵。 |
| Test-Time Scaling | 测试时扩展 | 推理时多花算力（更长 CoT、多次采样）换取更高准确率的范式。 |
| Length Hacking | 长度投机 | RLVR 训练中模型靠无意义地拉长输出来博取奖励的退化现象。 |

## 对齐的评测 · Alignment Evaluation

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Alignment Tax | 对齐税 | 对齐训练带来的基准能力（如 MMLU、代码）下降。 |
| Sycophancy | 谄媚 | 模型迎合用户观点、用户一质疑就改口的倾向，RLHF 的典型副作用。 |
| Length Bias | 长度偏差 | RM / 人类 / LLM 评委系统性偏好更长回答的偏差。 |
| LLM-as-a-Judge | 大模型评委 | 用强 LLM 给回答打分或两两对比，替代人工评测；自带位置/长度/自偏好等偏差。 |
| Length-Controlled Win Rate | 长度控制胜率 | 回归掉长度影响后的胜率（AlpacaEval 2.0 LC），抑制刷长度。 |
| MT-Bench / Arena | —— | 多轮对话评测基准 / 人类盲投对战平台（Chatbot Arena 的 Elo 排名）。 |
| Refusal Rate / Over-refusal | 拒答率/过度拒答 | 模型拒绝回答的比例；对无害请求也拒答即过度拒答，是安全对齐的失败模式。 |
| KL-Reward Frontier | KL-奖励前沿 | 以 KL(π‖π_ref) 为横轴、奖励为纵轴的曲线，对比对齐算法效率的标准图。 |

## 前沿 · Frontier

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Constitutional AI (CAI) | 宪法式 AI | 用一组成文原则让模型自我批评、自我修订并生成 AI 偏好标签的对齐方法（Anthropic）。 |
| RLAIF | AI 反馈强化学习 | 用 AI（而非人类）生成偏好标签来训 RM / 做 RL 的流程，CAI 的 RL 阶段。 |
| Self-Rewarding LM | 自我奖励语言模型 | 模型自己当评委给自己的输出打分、迭代 DPO 自我改进的方法。 |
| Self-Play | 自博弈 | 模型与自身（或副本）对抗/协作生成训练信号，无需外部标注的训练范式。 |
| Weak-to-Strong Generalization | 弱到强泛化 | 用弱监督者的标签训练强模型、研究强模型能否超越其监督者的对齐课题（superalignment 的代理实验）。 |
| Deliberative Alignment | 审议式对齐 | 让推理模型在回答前显式推理安全规范条文再作答的对齐方法（OpenAI o 系列）。 |
| Scalable Oversight | 可扩展监督 | 当任务难到人类难以直接评判时，如何仍能可靠监督模型的研究方向（辩论、递归奖励建模等）。 |
