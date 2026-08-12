# 术语词典 · Glossary（中英对照）

> 按主题分组，每条一句话定义。读论文遇到生词回这里查。

## 基础架构 · Architecture

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Vision Encoder | 视觉编码器 | 把像素图编码成向量序列的网络，VLM 的"眼睛"，常用 ViT。 |
| ViT (Vision Transformer) | 视觉 Transformer | 把图像切成 patch、当作 token 序列送进 Transformer 的视觉骨干。 |
| Patch Embedding | 图块嵌入 | 把 16×16 像素块线性投影成一个 token 向量。 |
| `[CLS]` token | 分类标记 | ViT 中聚合全图信息的特殊 token，常用作图像全局表征。 |
| Modality Gap | 模态鸿沟 | 对比学习后，图像 embedding 和文本 embedding 在同一空间里仍各自聚成一团、并不重合的现象。 |
| Connector / Adapter | 连接器 | 把视觉特征映射到 LLM 词嵌入空间的模块（MLP / Q-Former / Resampler）。 |
| Projector | 投影层 | 最简单的连接器，一个线性层或 MLP，把视觉特征投到 LLM 维度（LLaVA）。 |
| Q-Former | 查询 Transformer | BLIP-2 提出，用一组可学习 query 通过 cross-attention 从图像里"问"出固定数量的视觉 token。 |
| Perceiver Resampler | 感知重采样器 | Flamingo 用的连接器，把变长视觉特征压成固定数量 latent token。 |
| Cross-Attention | 交叉注意力 | query 来自一种模态、key/value 来自另一种模态的注意力，用于模态融合。 |
| Visual Tokens | 视觉 token | 图像被编码后送进 LLM 的那串向量，占据 LLM 的上下文长度。 |

## 训练与对齐 · Training & Alignment

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Contrastive Learning | 对比学习 | 拉近匹配对、推远不匹配对的训练范式（CLIP 的核心）。 |
| InfoNCE | —— | 对比学习的损失函数，本质是把"找出正样本"当成分类问题的交叉熵。 |
| Temperature τ | 温度系数 | InfoNCE 里缩放相似度的标量，控制分布尖锐程度。 |
| Image-Text Matching (ITM) | 图文匹配 | 二分类任务：判断一对图文是否匹配，BLIP 系常用辅助目标。 |
| Visual Instruction Tuning | 视觉指令微调 | 用"图像+指令→回答"的数据微调 VLM，使其能对话（LLaVA 开创）。 |
| Alignment Stage | 对齐阶段 | 预训练第一阶段，只训连接器、冻结视觉编码器和 LLM，对齐两个空间。 |
| Frozen Backbone | 冻结骨干 | 训练时不更新视觉编码器 / LLM 的参数，只训中间连接器。 |
| LoRA | 低秩适配 | 给权重矩阵加一个低秩增量 ΔW=BA 来微调，省显存的主流方法。 |
| QLoRA | 量化 LoRA | 4-bit 量化基座 + LoRA，单卡微调大模型。 |
| DPO (Direct Preference Optimization) | 直接偏好优化 | 不训奖励模型、直接用偏好对优化策略的对齐方法，VLM 常用来抑制幻觉。 |
| RLHF | 人类反馈强化学习 | 用人类偏好训练奖励模型再做 RL 的对齐流程。 |

## 分辨率与视频 · Resolution & Video

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| AnyRes / Any-Resolution | 任意分辨率 | 把高清图切成多个子图分别编码，突破固定 224/336 输入限制（LLaVA-NeXT）。 |
| Native Resolution | 原生分辨率 | 不缩放、按图像原始长宽比和分辨率处理（NaViT、Qwen2-VL）。 |
| Patch n' Pack (NaViT) | —— | 把不同分辨率图像的 patch 打包进一个序列高效训练的技术。 |
| Token Compression | token 压缩 | 减少每张图占用的视觉 token 数（pixel shuffle / pooling），降上下文开销。 |
| M-RoPE | 多模态旋转位置编码 | Qwen2-VL 把位置编码扩展到时间/高/宽三维，统一图像与视频。 |

## 评测 · Evaluation（重点）

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| MMMU | —— | 大学学科级多模态理解基准，覆盖 6 大领域专家级题目。 |
| MMBench | —— | 细粒度能力维度的多模态基准，用 CircularEval 抗位置偏差。 |
| MME | —— | 早期感知/认知二分的 yes/no 基准。 |
| MMStar | —— | 剔除"无需看图就能答对"题目后的精炼基准，衡量真·视觉依赖。 |
| MathVista | —— | 视觉数学推理基准。 |
| LLM-as-a-Judge | 大模型评委 | 用强 LLM 给开放式回答打分，替代人工评测。 |
| CircularEval | 循环评测 | 把选项循环移位多次都答对才算对，抵消选项位置偏差。 |
| Data Contamination | 数据污染 | 测试题（或其答案）泄漏进训练数据，导致虚高分数。 |
| Robustness | 鲁棒性 | 对图像扰动、选项重排、提示改写等的稳定性。 |
| Position Bias | 位置偏差 | 模型倾向选某个固定选项位置（如总选 A）的偏差。 |

## 幻觉与安全 · Hallucination & Safety

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Object Hallucination | 物体幻觉 | 描述图中根本不存在的物体。 |
| POPE | —— | 用 yes/no 问"图里有没有 X"来探测物体幻觉的协议。 |
| HallusionBench | —— | 探测语言先验压过视觉证据导致的幻觉/错觉的基准。 |
| Language Prior | 语言先验 | 模型凭文本常识答题、忽略实际图像内容的倾向。 |
| Sycophancy | 谄媚 | 用户一质疑就改口、附和用户的倾向。 |
| Jailbreak (multimodal) | 多模态越狱 | 借图像通道（如图中嵌文字、对抗扰动）绕过安全对齐。 |
| Dangerous Capability Eval | 危险能力评估 | 评估模型是否具备可被滥用的高风险能力（自主性、网络攻击等）。 |
| Red-teaming | 红队 | 主动构造攻击/诱导输入来暴露模型风险的过程。 |

## 前沿 · Frontier

| 术语 (EN) | 中文 | 一句话定义 |
|-----------|------|-----------|
| Native Multimodal | 原生多模态 | 从预训练起就在多模态数据上联合训练、而非后期拼接（GPT-4o、Gemini）。 |
| Any-to-Any | 任意到任意 | 输入输出都可跨模态（文/图/音）的统一模型（如 Chameleon、Unified-IO）。 |
| Early Fusion | 早融合 | 在输入层就把各模态 token 混进同一序列联合建模（Chameleon）。 |
| Mixture-of-Experts (MoE) | 专家混合 | 每个 token 只激活部分专家网络，扩参数不爆算力，前沿多模态常用。 |
| GUI Grounding | 界面定位 | 把指令对应到屏幕上的具体坐标/控件，computer-use agent 的核心能力。 |
| Computer-Use Agent | 电脑操作智能体 | 看屏幕截图、输出鼠标键盘动作来操作电脑的 VLM 智能体。 |
