# 术语词典 · Glossary（机制可解释性）

> 按主题分组，每条 2–3 句释义。读论文遇到生词回这里查。英文术语保持原文，因为这是社区通用语言。

## 总论 · Foundations

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Mechanistic Interpretability | 机制可解释性 | 把神经网络当作待逆向工程的程序，试图找出权重与激活中实现某行为的具体算法。区别于只看输入输出归因的"行为可解释性"，它追求电路级、特征级的机制解释。 |
| Representation | 表示 | 模型内部激活向量所编码的信息。interp 的基本假设是：表示不是不可知的黑盒，而是有结构、可解码、可干预的对象。 |
| Residual Stream | 残差流 | 把所有残差连接串起来的那条主干向量通道，每层 attention 和 MLP 都从中"读取"再把结果"写回"。它是模型各组件之间唯一的通信总线，因此是 interp 几乎所有方法的操作对象。 |
| Linear Representation Hypothesis | 线性表示假说 | 假说：模型把概念表示为激活空间中的方向（direction），概念强度对应在该方向上的投影长度。它是 probing、steering、SAE 等方法的共同理论前提；目前有大量正面证据但也有已知反例（如环形表示）。 |
| Feature | 特征 | 模型表示中一个可解释的基本单元，通常对应激活空间中的一个方向，如"这段文本是法语"或"这是 DNA 序列"。注意它是假设性概念：feature 的正确定义本身是开放研究问题。 |
| Privileged Basis | 特权基 | 如果架构中存在逐元素非线性（如 MLP 的激活函数），坐标轴方向就有特殊地位，称为特权基。residual stream 没有特权基（旋转不变），所以"看单个神经元"在 residual stream 上没有意义。 |
| Circuit | 电路 | 模型中协同实现某个特定行为的一组组件（heads、neurons、features）及其连接方式。电路分析的目标是把"模型做对了 X"还原成"哪几个零件以什么算法做到了 X"。 |
| Toy Model | 玩具模型 | 为隔离研究某个现象而专门构造的小模型，结构和数据都完全可控、ground truth 已知。本课全程用 toy model：牺牲规模，换来每个结论都可严格验证。 |
| Grokking | 顿悟现象 | 小模型在训练集早已过拟合之后很久，测试性能突然从随机跳到完美的现象。interp 对它的解释（记忆电路被泛化电路逐渐取代）是"机制分析能解释训练动力学"的标志性案例。 |

## 表示与探针 · Probing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Probing / Probe | 探针 | 在模型的中间激活上训练一个轻量分类器，检测某概念是否被线性（或浅层）编码。probe 准确率高说明信息**存在**于激活中，但不能直接证明模型**使用**了它。 |
| Linear Probe | 线性探针 | 最常用的 probe：一个 logistic regression / 线性分类器。选线性不是图省事——它对应 linear representation hypothesis，且表达力弱的 probe 更不容易"自己学会任务"而冒充模型的能力。 |
| Probe Selectivity | 探针选择性 | probe 在真实任务与 control task 上的准确率之差。selectivity 低说明 probe 的好成绩可能来自 probe 自身容量而非模型表示，是 probing 方法论的核心质检指标。 |
| Control Task | 对照任务 | 把标签随机打乱（但保持结构）后构造的假任务。如果 probe 在 control task 上也能拿高分，说明它在记数据而不是在读模型的表示。 |
| Concept Erasure | 概念擦除 | 从表示中投影掉某概念方向，再看下游行为是否改变。它把 probing 的相关性证据升级为干预性证据："擦掉它，行为变了，才说明模型真的在用它"。 |
| Lie Detection / Deception Probing | 测谎探针 | 用 probe 检测模型陈述内容与其内部"真值表示"是否一致的应用方向。是 interp 对安全评测最直接的输出之一：行为上看不出的不诚实，激活里可能留有痕迹。 |

## 透镜 · Lenses

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Logit Lens | logit 透镜 | 把中间层的 residual stream 直接乘 unembedding 矩阵，提前解码出"如果现在就输出，模型会说什么"。简单粗暴但揭示了一个深刻事实：预测是逐层迭代精化的，而不是最后一层突然产生的。 |
| Tuned Lens | 调谐透镜 | logit lens 的改进：为每层训练一个仿射变换（translator）再解码，修正各层表示与最终层之间的"基不对齐"。比 logit lens 更忠实，尤其在前半段层。 |
| Unembedding | 反嵌入 | 把 residual stream 向量映射回词表 logits 的最后一个线性层（W_U）。logit lens 的全部魔法就是把它提前用在中间层。 |
| Direct Logit Attribution (DLA) | 直接 logit 归因 | 利用最后一步是线性的这一事实，把某个 logit 拆解为各 head/MLP 写入 residual stream 的贡献之和。是"哪个组件把答案推高了"的最便宜的一阶答案。 |
| Attention Pattern | 注意力模式 | 某个 head 的 softmax 后注意力权重矩阵，描述每个位置从哪些位置汇聚信息。只看 pattern（不看 OV 怎么用信息）是常见误读来源——pattern 只回答"看哪"，不回答"拿来做什么"。 |

## 电路 · Circuits

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| QK Circuit | QK 电路 | 把一个 head 的 W_Q 与 W_K 合成 W_QK 后得到的双线性形式，完全决定该 head 的注意力分布（看哪）。与 OV 电路正交分解是 Mathematical Framework 的核心洞见。 |
| OV Circuit | OV 电路 | 把 W_V 与 W_O 合成 W_OV 后的线性映射，决定被注意到的信息如何被搬运、变换并写回 residual stream（拿来做什么）。 |
| Induction Head | 归纳头 | 实现 `[A][B] ... [A] → [B]` 模式补全的 attention head：看到当前 token 上次出现的位置，把它后面那个 token 抄过来。被认为是 in-context learning 的主要机制来源，是 interp 迄今最扎实的电路发现。 |
| Previous-Token Head | 前词头 | 把上一个位置的信息搬到当前位置的 head。它与 induction head 通过 K-composition 两层接力，共同构成 induction circuit。 |
| Composition (Q/K/V-composition) | 组合 | 一个 head 的输出经 residual stream 成为后层 head 的 Q、K 或 V 输入，使多个 head 能接力实现单层做不到的算法。多层 transformer 的表达力本质上来自这里。 |
| IOI (Indirect Object Identification) | 间接宾语识别 | "When Mary and John went to the store, John gave a drink to ___"→ Mary。GPT-2 small 中第一个被完整逆向的非平凡电路（约 26 个 head 分工协作），是电路分析方法论的标杆案例。 |
| Attribution | 归因 | 把模型输出（或某个内部量）分解到输入或组件贡献的一类方法的统称，包括梯度法与 patching 法。attribution patching 用一阶梯度近似替代逐个 patching，把成本从 O(组件数) 次前向降到 O(1)。 |

## 因果干预 · Causal Interventions

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Activation Patching | 激活修补 | 跑两个 prompt（clean / corrupted），把其中一个的某处激活替换进另一个的前向传播，看输出变化多少。它把"这个组件与行为相关"升级为"这个组件因果地承载了行为所需的信息"。 |
| Causal Tracing | 因果追踪 | ROME 论文中的 activation patching 变体：给输入加噪破坏，再逐个恢复中间激活，定位事实知识存储的位置（发现集中在中层 MLP）。 |
| Path Patching | 路径修补 | 只沿特定"发送组件→接收组件"路径替换激活、其余路径保持不变的精细版 patching。回答的不是"哪个组件重要"而是"组件 A 通过哪条通道影响组件 B"。 |
| Denoising vs Noising | 去噪 / 加噪 | patching 的两个方向：把 clean 激活补进 corrupted 运行（denoising，问"什么足以恢复行为"），或把 corrupted 激活补进 clean 运行（noising，问"什么是行为所必需"）。两者答案可以不同，混用是常见错误。 |
| Ablation (zero / mean) | 消融 | 把某组件输出置零（zero ablation）或换成数据集均值（mean ablation）来测量其必要性。zero ablation 会把模型推出训练分布，mean / resample ablation 通常是更公平的反事实。 |
| Logit Difference | logit 差 | patching 实验最常用的度量：正确答案与对照答案的 logit 之差。比单个 logit 或概率更稳健，因为它对"整体置信度平移"不敏感。 |
| Faithfulness | 忠实性 | 一个解释（电路、特征归因）在多大程度上反映模型真实计算，而不只是一个看起来合理的故事。标准检验：只保留电路时行为保留多少、消融电路时行为掉多少。 |
| Self-Repair | 自我修复 | 消融某个组件后，下游其他组件改变行为、部分补偿其功能的现象（又称 hydra effect）。它使"消融后掉点少 = 不重要"的推断不可靠，是电路分析最大的方法论陷阱之一。 |
| Backup Head | 备份头 | self-repair 的具体形式：平时贡献不大、但在主力 head 被消融时接管其功能的 attention head。IOI 电路中的 backup name mover heads 是经典例子。 |

## 叠加与特征分解 · Superposition & SAEs

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Superposition | 叠加 | 模型用 n 维空间表示远多于 n 个的稀疏特征，让特征方向彼此非正交地"挤"在一起。Toy Models of Superposition 证明了当特征稀疏时这是最优压缩策略——也是单个神经元难以解释的根本原因。 |
| Polysemanticity | 多义性 | 一个神经元对多个不相关概念都激活的现象（如同时响应学术引用、英语对话和韩语文本）。叠加假说把它解释为压缩的必然代价，而非训练的偶然瑕疵。 |
| Monosemanticity | 单义性 | 一个单元只对应一个可解释概念的理想性质。SAE 的目标就是把多义的神经元激活换基到（近似）单义的特征激活。 |
| Sparse Autoencoder (SAE) | 稀疏自编码器 | 在模型激活上训练的过完备自编码器：编码到远高于原维度的稀疏隐层再重建。它是当前把叠加特征拆开的主流工具，从 Towards Monosemanticity 到 Scaling Monosemanticity 验证了其规模化可行性。 |
| Dictionary Learning | 字典学习 | 把信号表示为过完备基（字典）中少数原子的稀疏线性组合的经典信号处理问题。SAE 本质上就是用神经网络做 dictionary learning，字典原子即特征方向。 |
| L0 | L0 范数 | 每个输入平均激活的 SAE 特征个数，是稀疏度的直接度量。SAE 训练的核心权衡就是 L0（稀疏性/可解释性）对 reconstruction loss（忠实性）。 |
| Reconstruction Loss | 重建损失 | SAE 重建激活与原激活的误差，常用"替换激活后模型 loss 增加多少"衡量。重建差的 SAE 即使特征看着干净也不可信——它丢掉了模型实际在用的信息。 |
| Dead Feature | 死特征 | 训练后期几乎从不激活的 SAE 特征，浪费字典容量。是 SAE 训练的常见病，催生了 resampling、auxiliary loss 等工程修法。 |
| Feature Splitting | 特征分裂 | 增大 SAE 字典时，一个粗特征分裂成多个更细粒度子特征的现象（如"数学"分裂为代数、几何……）。提示特征可能没有唯一"正确"粒度，而是分层结构。 |
| Sparse Feature Circuits | 稀疏特征电路 | 用 SAE 特征（而非 head/neuron）作为节点构建的电路，单位更接近人类概念。Marks et al. 2024 用它发现并手术移除了分类器中的虚假关联（SHIFT 方法）。 |

## 干预与表示工程 · Steering & RepE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Steering Vector | 引导向量 | 加到 residual stream 上以推动模型行为朝某方向改变的向量。它是 linear representation hypothesis 的干预版应用：概念若是方向，加上这个方向就该增强该概念。 |
| Activation Addition (ActAdd) | 激活加法 | 最简单的 steering 构造法：用一对对比 prompt（如 "Love" − "Hate"）的激活差作为 steering vector，推理时加进指定层。无需训练、无需改权重。 |
| Contrastive Activation Addition (CAA) | 对比激活加法 | ActAdd 的规模化改进：在大量正负行为对比样本（如选 A/选 B 的多选题）上取激活差的均值，得到更干净、更稳定的行为方向。 |
| Refusal Direction | 拒绝方向 | Arditi et al. 2024 发现：聊天模型的拒绝行为由 residual stream 中单一方向介导——投影掉它模型不再拒绝有害请求，加上它模型拒绝无害请求。是"一根向量解释一类安全行为"的标志性结果，也解释了部分越狱的机制。 |
| Representation Engineering (RepE) | 表示工程 | 自顶向下的研究纲领：不逆向单个电路，直接在表示层面读取（reading）与控制（steering）诚实、情绪、伤害性等高层概念。与自底向上的电路分析互补。 |
| Inference-Time Intervention (ITI) | 推理时干预 | 在推理时沿 probe 找到的"真实性方向"平移少数 attention head 的激活，提升模型诚实度。probing（读）与 steering（写）结合的代表工作。 |

## 评测与审计应用 · Interp for Evals & Audits

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Model Diffing | 模型差分 | 比较两个模型（如 base vs fine-tuned）内部表示与特征的差异，回答"后训练到底改了什么"。crosscoder 等工具让特征级 diff 成为可能，是审计后训练改动的核心手段。 |
| Circuit Tracing / Attribution Graph | 电路追踪 / 归因图 | Anthropic 2025 的方法：用 replacement model 上的归因图追踪一次具体回答中特征间的因果链条（On the Biology of a Large Language Model）。把电路分析从"一个任务一篇论文"推进到"按查询出图"。 |
| Sandbagging | 藏拙 | 模型在评测中策略性地表现得比真实能力差。纯行为评测原则上难以排除它，而能力相关的内部表示（probe 能否读出"它其实会"）是 interp 能提供的独特证据。 |
| Hidden Objective Auditing | 隐藏目标审计 | 在不知道答案的前提下，用 interp + 行为工具找出模型被植入的隐蔽目标（Marks et al. 2025 的盲审实验）。是"interp 能否支撑真实审计"的第一次正式演练。 |
| Safety Case | 安全论证 | 结构化论证"该模型部署是安全的"的证据链。白盒证据（probe、电路、特征监控）能支撑黑盒评测在原则上无法闭合的环节，如排除欺骗性对齐。 |
| Probing for Evals | 评测探针 | 把 probe 作为评测仪器：测谎、检测 sandbagging 前兆、监控危险意图表示。相对行为评测的优势是难以被模型的输出策略欺骗，劣势是依赖表示假设成立。 |
