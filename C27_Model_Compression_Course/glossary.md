# 术语词典 · Glossary（模型压缩与高效化）

> 按主题分组，每条 2–3 句释义。读 LLM.int8() / GPTQ / AWQ / FP8 / 蒸馏 / SparseGPT 论文与 bitsandbytes / AutoGPTQ / TransformerEngine 代码遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用 numpy 在 CPU 上从零实现这些机制，术语与真实框架一一对应。

## 总览与度量 · Overview & Metrics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| model compression | 模型压缩 | 在尽量不损失质量的前提下，减小模型的显存/存储占用、带宽与计算开销的一族技术。本课五大支柱：量化、后训练量化（GPTQ/AWQ）、低精度训练（fp8）、蒸馏、剪枝/稀疏。 |
| quantization | 量化 | 把高精度数（fp32/bf16）映射到少数离散级别（如 int8 的 256 个、int4 的 16 个）来存储与计算。是当下 LLM 压缩最主力、收益最直接的手段。 |
| post-training quantization (PTQ) | 后训练量化 | 不重新训练、仅用少量校准数据把已训好的权重量化到低 bit。GPTQ、AWQ 是其代表，几小时即可把一个大模型量化到 int4。 |
| quantization-aware training (QAT) | 量化感知训练 | 训练（或微调）时就把量化噪声放进前向，让权重学会对量化鲁棒。质量上限更高但成本远大于 PTQ；本课聚焦 PTQ 与低精度训练。 |
| weight-only quantization | 仅权重量化 | 只把权重量化到低 bit、激活仍用 fp16/bf16，推理时反量化回高精度再算。LLM 推理多为访存受限，单是省权重显存与带宽就能显著提速；GPTQ/AWQ 属此类。 |
| compression ratio | 压缩率 | 原模型大小 ÷ 压缩后大小。int8 ≈ 2×、int4 ≈ 4×（相对 fp16），2:4 稀疏理论 2×，蒸馏取决于学生/教师规模比。 |
| accuracy–efficiency trade-off | 精度–效率权衡 | 压得越狠通常掉点越多。压缩研究的主线就是在给定精度损失预算下尽量提高压缩率，或在给定压缩率下尽量保住精度。 |
| perplexity (PPL) | 困惑度 | 语言模型在测试集上的 exp(平均负对数似然)，越低越好。是衡量压缩是否掉点最常用的内在指标；GPTQ/AWQ 论文都以 WikiText2 PPL 报告。 |
| MSE / reconstruction error | 均方误差 / 重建误差 | 量化值与原值（或量化层输出与原输出）的平方误差。多数 PTQ 算法的优化目标就是最小化某种重建误差。 |
| outlier | 离群值 | 数值远大于多数元素的少数权重或激活。它们撑大量化范围、吞掉精度，是低 bit 量化最大的敌人；LLM.int8()、AWQ、SmoothQuant 都在专门对付它。 |

## 整数量化机制 · Integer Quantization

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| affine quantization | 仿射量化 | 通用量化映射 `q = round(x/s) + z`、反量化 `x ≈ s·(q − z)`，由缩放因子 `s`（scale）与零点 `z`（zero-point）两个参数刻画。对称量化是 `z=0` 的特例。 |
| scale | 缩放因子 | 把浮点范围映射到整数范围的步长。`s = 范围 / (qmax − qmin)`。scale 选得太大丢精度、太小则截断离群值，是量化质量的核心旋钮。 |
| zero-point | 零点 | 整数域中代表浮点 0 的那个整数。非对称量化用它把不关于 0 对称的分布（如 ReLU 后全正的激活）映射满整个整数区间。 |
| symmetric quantization | 对称量化 | `z=0`，整数区间关于 0 对称（如 int8 用 [−127,127]）。实现简单、反量化只需一次乘法，适合关于 0 近似对称的权重；absmax 是其典型 scale。 |
| asymmetric quantization | 非对称量化 | `z≠0`，用 min/max 两端把任意区间铺满整数范围。更贴合偏斜分布（激活），但计算要多处理零点项。 |
| absmax quantization | absmax 量化 | 对称量化的常用 scale 选法：`s = max(\|x\|) / qmax`，让最大绝对值刚好映射到整数边界。简单、无需零点，但对离群值敏感。 |
| qmin / qmax | 整数上下界 | 目标整数类型的可表示范围。int8 对称常用 [−127, 127]（留 −128 不用以保持对称）；uint4 非对称用 [0, 15]。 |
| int8 / int4 | 8 位 / 4 位整数 | 8 位 256 级、4 位 16 级。int8 通常近乎无损，int4 需配合 group-wise + 误差补偿（GPTQ/AWQ）才能保住精度。 |
| per-tensor quantization | 逐张量量化 | 整个权重矩阵共用一个 scale（与 zero-point）。最省元数据、最快，但一个离群值就拖累全矩阵精度。 |
| per-channel quantization | 逐通道量化 | 每个输出通道（权重矩阵的每行/每列）独立一个 scale。把离群值的影响限制在单通道内，几乎是 int8 权重量化的标配。 |
| group-wise quantization | 分组量化 | 把一行再切成每 `g` 个元素（如 g=128）一组、各组独立 scale。是 int4 保精度的关键——粒度越细越准，但元数据开销越大。 |
| bit packing | 位打包 | 把多个低 bit 整数塞进一个标准容器，如把两个 int4 拼进一个 int8（高 4 位一个、低 4 位一个），真正实现 4 bit 的存储节省。反量化前先解包。 |
| dequantization | 反量化 | 把整数 `q` 用 `x ≈ s·(q − z)` 还原回浮点。weight-only 量化在矩阵乘前反量化权重；它本身有误差（量化噪声）。 |
| rounding | 舍入 | 把 `x/s` 取整为整数。最常见是 round-to-nearest（RTN，就近舍入）；GPTQ 证明逐元素 RTN 并非最优，应做误差补偿。 |
| clipping / saturation | 截断 / 饱和 | 超出 `[qmin,qmax]` 的值被夹到边界。适当截断离群值（牺牲它们）反而能给主体更多精度，是高级量化的常用手段。 |
| quantization noise / error | 量化噪声 / 误差 | 反量化值与原值之差。均匀量化下单个误差近似服从 `[−s/2, s/2]` 的均匀分布，期望平方误差约 `s²/12`——本课练习会从零验证这个公式。 |

## 后训练量化算法 · PTQ Algorithms (GPTQ / AWQ)

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| RTN (round-to-nearest) | 就近舍入 | 最朴素的量化：每个权重独立四舍五入到最近的量化级别。简单但在 int4 下掉点明显，因为它对每个权重一视同仁、不顾它对输出的影响。 |
| GPTQ | —— | Frantar et al. 2022 的 PTQ 算法。逐列量化权重，每量化一列就用逆 Hessian 把引入的误差「补偿」到尚未量化的列上，使层输出尽量不变。能把大模型几小时量化到 int3/int4。 |
| OBQ (Optimal Brain Quantization) | 最优脑量化 | GPTQ 的理论基础。源自 Optimal Brain Surgeon：量化一个权重带来的输出误差，可用逆 Hessian 解析地补偿到其余权重。GPTQ 是它在「逐列、固定顺序」下的高效近似。 |
| Hessian (of layer loss) | 海森矩阵 | 这里指层重建误差 `‖Wx − Ŵx‖²` 对权重的二阶导，正比于 `XXᵀ`（X 为校准输入）。它刻画了「动哪个权重对输出影响大」，是误差补偿的依据。 |
| inverse Hessian | 逆 Hessian | `(XXᵀ + λI)⁻¹`。GPTQ 的误差补偿系数来自它的 Cholesky 分解；λ 是阻尼项，保证可逆与数值稳定。 |
| error compensation | 误差补偿 | 量化某权重产生误差后，按逆 Hessian 给出的系数调整其余未量化权重，抵消这部分误差对层输出的影响。GPTQ 的灵魂。 |
| calibration data | 校准数据 | 一小批（几十到几百条）真实输入样本，用来估计激活统计量（GPTQ 的 Hessian、AWQ 的激活幅度）。PTQ 不需训练，但需要它来「看见」激活分布。 |
| AWQ (Activation-aware Weight Quantization) | 激活感知权重量化 | Lin et al. 2023 的 PTQ 算法。洞察：权重是否重要由其对应的激活幅度决定。它给显著通道乘一个保护性缩放 `s`（再在量化时除回），等价于给重要权重更多有效精度。 |
| salient channels | 显著通道 | 对应大激活、对输出贡献最大的那 ~1% 输入通道。保护好它们就能保住大部分精度——AWQ 的核心观察。 |
| activation-aware scaling | 激活感知缩放 | AWQ 的手段：按激活幅度给每个输入通道搜一个缩放因子 `s`，权重乘 `s`、激活除 `s`（数学等价），让显著通道的权重在量化网格上落得更准。 |
| scale search | 缩放搜索 | AWQ 在一组候选缩放（由激活幅度的幂次参数化）里，挑使层输出 MSE 最小的那个。是个小型一维网格搜索。 |
| SmoothQuant | —— | Xiao et al. 2022：把激活的离群「难度」按通道迁移一部分到权重上（激活除 s、权重乘 s），让激活和权重都更好量化，使 W8A8（权重+激活都 int8）可行。与 AWQ 思路同源。 |
| layer-wise reconstruction | 逐层重建 | PTQ 的通用框架：逐层地选量化参数，使该层量化后输出尽量接近原输出（最小化 `‖Wx − Ŵx‖²`）。GPTQ、AWQ、SparseGPT 都在这个框架里。 |

## 浮点格式与低精度训练 · Floating-point & Low-precision Training

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| fp32 / fp16 / bf16 | 单精度 / 半精度 / bfloat16 | fp32：1+8+23 位。fp16：1+5+10，范围小易溢出。bf16：1+8+7，与 fp32 同指数范围、尾数更少，是当下训练主力（牺牲精度换范围与稳定）。 |
| fp8 | 8 位浮点 | 训练/推理用的 8 位浮点，有 E4M3 与 E5M2 两种格式。是 Hopper/Ada 之后大模型训练与推理的前沿低精度格式（Micikevicius et al. 2022）。 |
| E4M3 | E4M3 | 1 符号 + 4 指数 + 3 尾数。精度较高、动态范围较小（约 ±448）。fp8 训练里多用于前向的权重与激活。 |
| E5M2 | E5M2 | 1 符号 + 5 指数 + 2 尾数。动态范围大、精度低。多用于反向的梯度——梯度数值跨度大，更需要范围。 |
| exponent / mantissa | 指数 / 尾数 | 浮点数 `(-1)^s × 1.mantissa × 2^(exp-bias)` 的两部分。指数位决定动态范围，尾数位决定相对精度。fp8 两格式正是在这两者间取不同折中。 |
| dynamic range | 动态范围 | 一种格式能表示的最大与最小（非零）数之比。指数位越多范围越大。低 bit 训练的核心矛盾就是范围与精度都不够，要靠 scaling 腾挪。 |
| scaling factor (fp8) | 缩放因子 | 把张量乘上一个标量，使其数值落进 fp8 的「甜区」（不溢出也不下溢），算完再除回。是 fp8 训练能用的前提。 |
| delayed scaling | 延迟缩放 | 用前几步观测到的张量最大幅度（的滑动统计）来定本步的 fp8 scale，避免每步都先扫一遍张量求 max 的开销。TransformerEngine 的默认策略。 |
| amax | 绝对值最大 | 张量元素绝对值的最大值。fp8 scaling 用它来决定缩放因子，使 amax 刚好映射到格式可表示的上界附近。 |
| loss scaling | 损失缩放 | 反向前把 loss 乘一个大常数，使本会下溢为 0 的小梯度被放大到可表示区间，更新前再除回。fp16/fp8 训练防梯度下溢的经典技巧。 |
| gradient underflow | 梯度下溢 | 很小的梯度在低精度格式下被舍入为 0，导致权重学不动。loss scaling 正是为对付它。 |
| mixed precision | 混合精度 | 关键处用高精度、其余用低精度的训练配方：如 fp8 算矩阵乘、bf16/fp32 存主权重与做累加、fp32 存优化器状态。兼顾速度与稳定。 |
| master weights | 主权重 | 以高精度（fp32）保存的权重副本，用于累积微小更新；前向时再 cast 到低精度计算。防止「小更新被低精度吃掉」。 |
| stochastic rounding | 随机舍入 | 以与距离成比例的概率向上/向下取整，使舍入在期望上无偏。低精度累加/更新时用它可缓解系统性偏差。 |

## 知识蒸馏 · Knowledge Distillation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| knowledge distillation (KD) | 知识蒸馏 | Hinton et al. 2015：用一个大的教师模型的输出来训练小的学生模型，使学生学到比硬标签更丰富的信息。是把大模型「压缩」进小模型的主路之一。 |
| teacher / student | 教师 / 学生 | 教师是已训好的（通常更大、更强）模型；学生是待训练的小模型。蒸馏让学生模仿教师的输出分布或内部表示。 |
| soft label / soft target | 软标签 | 教师 softmax 输出的完整概率分布（如「猫 0.7、狗 0.2、车 0.001」），相对只有 0/1 的硬标签携带了类间相似度信息。 |
| hard label | 硬标签 | 数据集里的 one-hot 真值标签。只说「对的是哪个」，不含「其余各类有多像」。 |
| dark knowledge | 暗知识 | 软标签里非目标类的相对概率所编码的隐性结构（如「3 比 8 更像」）。是蒸馏比直接用硬标签更有效的原因。 |
| temperature | 温度 | softmax 里除在 logit 上的系数 `T`：`softmax(z/T)`。`T>1` 软化分布、放大暗知识中的小概率，让学生看清类间结构。 |
| distillation loss | 蒸馏损失 | 学生与教师软标签之间的差异，通常用 KL 散度，并按 `T²` 缩放以平衡梯度量级。常与对硬标签的交叉熵按权重相加。 |
| KL divergence | KL 散度 | `KL(p‖q)=Σ p log(p/q)`，衡量用 q 近似分布 p 的信息损失。蒸馏中 p 是教师软标签、q 是学生分布；最小化它让学生贴近教师。 |
| logit distillation | logit 蒸馏 | 最经典的形式：在输出 logit/概率层面让学生匹配教师（Hinton 的原始方法）。 |
| feature distillation | 特征蒸馏 | 让学生的中间层表示匹配教师的中间层（FitNets）。常需一个投影把学生维度对齐到教师维度。 |
| attention distillation | 注意力蒸馏 | 让学生模仿教师的注意力图/关系（TinyBERT、MiniLM）。在 Transformer 蒸馏里很有效，因为注意力承载了大量结构信息。 |
| self-distillation | 自蒸馏 | 教师与学生同架构（甚至同一模型的不同阶段/不同视角）。如 Born-Again Networks，用上一代自己当教师，常能再涨点。 |
| on-policy distillation | on-policy 蒸馏 | 在学生自己生成的样本上做蒸馏（而非固定数据集），缓解训练/推理分布不匹配，对生成式模型尤为重要。 |

## 剪枝与稀疏 · Pruning & Sparsity

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pruning | 剪枝 | 把模型中不重要的权重置 0（或整块删除），减少参数与计算。可在训练后做（PTQ 式重建）或训练中做。 |
| sparsity | 稀疏度 | 被置 0 的权重比例。50% 稀疏即一半权重为 0。稀疏度越高省得越多，但越易掉点。 |
| magnitude pruning | 幅度剪枝 | 最经典的剪枝准则：按 `\|w\|` 从小到大删，认为绝对值小的权重最不重要。简单有效，是几乎所有方法的基线。 |
| unstructured pruning | 非结构化剪枝 | 任意位置的单个权重都可被剪，得到散乱的 0。压缩率高、掉点少，但稀疏模式不规则，通用硬件难加速。 |
| structured pruning | 结构化剪枝 | 成块地剪：整行/整列、整个注意力头、整个通道或层。稀疏模式规整，直接缩小矩阵、通用硬件就能加速，但同稀疏度下掉点更多。 |
| semi-structured / N:M sparsity | 半结构化 / N:M 稀疏 | 折中：每 M 个连续权重里恰好保留 N 个非零。规整到硬件能加速，又比纯结构化灵活。 |
| 2:4 sparsity | 2:4 稀疏 | N:M 的代表：每 4 个权重保留 2 个。NVIDIA Ampere 起的 Sparse Tensor Core 可对它原生 2× 加速，是当前最实用的稀疏格式（Mishra et al. 2021）。 |
| pruning mask | 剪枝掩码 | 与权重同形的 0/1 矩阵，1 表示保留、0 表示剪掉。前向时权重逐元素乘掩码；训练中保持掩码固定。 |
| global vs layer-wise pruning | 全局 vs 逐层剪枝 | 全局：用一个统一阈值跨所有层比较 `\|w\|`，让各层稀疏度自适应。逐层：每层各剪到同一比例。全局通常更优，因为不同层冗余度不同。 |
| iterative magnitude pruning (IMP) | 迭代幅度剪枝 | 「剪一点→微调恢复→再剪」反复多轮，比一次剪到目标稀疏度掉点小得多。是彩票假说实验的标准流程。 |
| fine-tuning / recovery | 微调恢复 | 剪枝后继续训练剩余权重，让它们补偿被剪掉部分的功能、找回精度。是高稀疏度下保住质量的关键步骤。 |
| SparseGPT | —— | Frantar & Alistarh 2023：把 GPTQ 的逐层逆 Hessian 重建思想用到剪枝上，一次性（one-shot）把大模型剪到 50%+ 稀疏几乎不掉点，无需重训。 |
| lottery ticket hypothesis | 彩票假说 | Frankle & Carlin 2018：稠密网络里存在一个稀疏子网（中奖彩票），用原始初始化单独训练就能达到原网络精度。揭示稀疏子网的可训练性依赖初始化。 |
| winning ticket | 中奖彩票 | 彩票假说里那个「用原初始化单独训也能训好」的稀疏子网。 |
| rewinding | 回卷 | 找到稀疏子网后，把保留权重重置回训练早期（而非最初）的值再训。比回到随机初始化更稳，是后续工作的改进。 |

## 系统与工具 · Systems & Tooling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| LLM.int8() | —— | Dettmers et al. 2022：发现大模型激活有少数离群特征维度，对它们保留 fp16、其余用 int8 做混合精度分解矩阵乘，实现几乎无损的 8-bit 推理。bitsandbytes 的核心。 |
| bitsandbytes | —— | Dettmers 等的库，提供 8-bit/4-bit（NF4）量化与优化器，是 QLoRA 等低显存微调的基础设施。 |
| NF4 (4-bit NormalFloat) | 4 位正态浮点 | QLoRA 用的 4-bit 数据类型：量化级别按正态分布的分位点设置（信息论最优地匹配神经网络权重的近似正态分布），优于均匀 int4。 |
| GPTQ / AutoGPTQ | —— | GPTQ 算法及其开源实现库，把模型一键量化到 int3/int4 并导出可推理的权重。 |
| AWQ / AutoAWQ | —— | AWQ 算法及其实现库，常与 GPTQ 并列为 int4 weight-only 量化的两大主力，推理时反量化开销小、对指令模型友好。 |
| TransformerEngine | —— | NVIDIA 的 fp8 训练库，封装 delayed scaling、amax 历史、fp8 GEMM，让 Transformer 在 Hopper 上用 fp8 训练。 |
| GGUF / llama.cpp | —— | 面向 CPU/边缘推理的量化权重格式与运行时，支持多种 int4/int5 量化方案（Q4_K_M 等），是本地跑大模型的事实标准之一。 |
| KV-cache quantization | KV 缓存量化 | 把自回归推理的 KV cache 量化到 int8/int4，省下长上下文推理的显存大头。是与权重量化互补的一条压缩线。 |
| Sparse Tensor Core | 稀疏张量核心 | NVIDIA Ampere 起支持 2:4 稀疏的硬件单元，对满足 2:4 模式的矩阵乘原生加速约 2×。2:4 稀疏之所以实用就靠它。 |
