# 关键论文清单 · References（机制可解释性）

> 按模块组织。`★` = 必读里程碑。教材中 `[作者 年份]` 对应此处。
> 注：Anthropic 的电路系列发表在 transformer-circuits.pub（无 arXiv 号的以链接标注）。

## 00 · 总览：领域地图

- ★ Olah et al. 2020, *Zoom In: An Introduction to Circuits* — distill.pub/2020/circuits/zoom-in — 机制可解释性的宣言：把"特征是方向、电路是子图"立为研究纲领。
- Ferrando et al. 2024, *A Primer on the Inner Workings of Transformer-based Language Models* — arXiv:2405.00208 — 目前最好的方法综述，本课的"地图册"。
- Sharkey et al. 2025, *Open Problems in Mechanistic Interpretability* — arXiv:2501.16496 — 领域自己写的"还有什么没解决"，找研究方向先读它。

## 01 · Linear Probes：表示即向量

- ★ Alain & Bengio 2016, *Understanding Intermediate Layers Using Linear Classifier Probes* — arXiv:1610.01644 — probing 的开山之作：用线性分类器逐层"体检"表示。
- ★ Hewitt & Liang 2019, *Designing and Interpreting Probes with Control Tasks* — arXiv:1909.03368 — 提出 control task 与 selectivity，给 probing 立了方法论规矩。
- Belinkov 2022, *Probing Classifiers: Promises, Shortcomings, and Advances* — arXiv:2102.12452 — probing 十年得失的清醒综述："信息存在 ≠ 信息被使用"。
- Park et al. 2023, *The Linear Representation Hypothesis and the Geometry of Large Language Models* — arXiv:2311.03658 — 把"概念即方向"从经验观察提炼成可检验的数学命题。
- Marks & Tegmark 2023, *The Geometry of Truth* — arXiv:2310.06824 — 真/假陈述在激活空间中线性可分，测谎探针的代表性证据。
- Burns et al. 2022, *Discovering Latent Knowledge in Language Models Without Supervision (CCS)* — arXiv:2212.03827 — 不用标签、靠逻辑一致性约束找出"模型相信什么"。

## 02 · Residual Stream 与 Logit Lens

- ★ nostalgebraist 2020, *interpreting GPT: the logit lens* — LessWrong (lesswrong.com/posts/AcKRB8wDpdaN6v6ru) — 一篇博客开创一个方法：中间层提前解码，预测是逐层精化的。
- ★ Belrose et al. 2023, *Eliciting Latent Predictions from Transformers with the Tuned Lens* — arXiv:2303.08112 — 给每层训练 translator 修正 logit lens 的偏差，更忠实的透镜。
- Geva et al. 2020, *Transformer Feed-Forward Layers Are Key-Value Memories* — arXiv:2012.14913 — MLP 层 = 键值存储，理解"知识在哪"的起点。
- Geva et al. 2022, *Transformer Feed-Forward Layers Build Predictions by Promoting Concepts in the Vocabulary Space* — arXiv:2203.14680 — FFN 通过往 residual stream 里"推词"逐步构造预测，与 logit lens 视角互证。

## 03 · QK/OV 电路与 Induction Heads

- ★ Elhage et al. 2021, *A Mathematical Framework for Transformer Circuits* — transformer-circuits.pub/2021/framework — 全课理论核心：residual stream 是总线、attention head 分解为 QK/OV 两条独立电路、composition 造就深度。
- ★ Olsson et al. 2022, *In-context Learning and Induction Heads* — transformer-circuits.pub/2022/in-context-learning-and-induction-heads (arXiv:2209.11895) — induction heads 与 in-context learning 能力同时相变出现，机制→能力因果链的最强案例。
- Nanda et al. 2023, *Progress Measures for Grokking via Mechanistic Interpretability* — arXiv:2301.05217 — 逆向出模加法的傅里叶电路，用机制指标预测 grokking 何时发生。

## 04 · Activation Patching：因果干预

- ★ Meng et al. 2022, *Locating and Editing Factual Associations in GPT (ROME)* — arXiv:2202.05262 — causal tracing 定位事实存储在中层 MLP，并顺手提出了模型编辑。
- ★ Wang et al. 2022, *Interpretability in the Wild: A Circuit for Indirect Object Identification (IOI)* — arXiv:2211.00593 — 第一个被完整逆向的真实模型电路，约 26 个 head 的分工图谱；也发现了 backup heads。
- Goldowsky-Dill et al. 2023, *Localizing Model Behavior with Path Patching* — arXiv:2304.05969 — 把 patching 细化到"路径"粒度：A 经哪条通道影响 B。
- Heimersheim & Nanda 2024, *How to Use and Interpret Activation Patching* — arXiv:2404.15255 — patching 的实操避坑手册：denoising vs noising、度量选择、常见误读。
- Zhang & Nanda 2023, *Towards Best Practices of Activation Patching in Language Models* — arXiv:2309.16042 — 系统比较 patching 各变体超参的影响，结论：度量与 corruption 方式会改变结论。
- McGrath et al. 2023, *The Hydra Effect: Emergent Self-Repair in Language Model Computations* — arXiv:2307.15771 — 消融一个 head，别的 head 顶上——self-repair 让消融证据天然打折。
- Conmy et al. 2023, *Towards Automated Circuit Discovery (ACDC)* — arXiv:2304.14997 — 把"递归 patching 找电路"自动化成算法。
- Syed et al. 2023, *Attribution Patching Outperforms Automated Circuit Discovery* — arXiv:2310.10348 — 用梯度一阶近似把 patching 成本降到两次前向 + 一次反向。

## 05 · 叠加假说与稀疏自编码器

- ★ Elhage et al. 2022, *Toy Models of Superposition* — transformer-circuits.pub/2022/toy_model (arXiv:2209.10652) — 用可完全控制的 toy model 证明：特征稀疏时模型必然叠加存储，多义性是压缩的代价。本课 05 模块逐图复现它。
- ★ Bricken et al. 2023, *Towards Monosemanticity: Decomposing Language Models With Dictionary Learning* — transformer-circuits.pub/2023/monosemantic-features — 在一层 transformer 上用 SAE 拆出数千个单义特征，确立 SAE 范式。
- ★ Templeton et al. 2024, *Scaling Monosemanticity: Extracting Interpretable Features from Claude 3 Sonnet* — transformer-circuits.pub/2024/scaling-monosemanticity — SAE 规模化到前沿模型，找到 Golden Gate Bridge 等可 steering 的特征，包括安全相关特征。
- Cunningham et al. 2023, *Sparse Autoencoders Find Highly Interpretable Features in Language Models* — arXiv:2309.08600 — 与 Anthropic 同期独立验证 SAE 路线的开源工作。
- Gao et al. 2024, *Scaling and Evaluating Sparse Autoencoders* — arXiv:2406.04093 — TopK SAE 与 SAE 的 scaling law；dead feature 的工程修法。
- Rajamanoharan et al. 2024, *Jumping Ahead: Improved Reconstruction Fidelity with JumpReLU SAEs* — arXiv:2407.14435 — JumpReLU 激活改善 L0–重建权衡，Gemma Scope 所用方案。

## 06 · Steering Vectors 与表示工程

- ★ Turner et al. 2023, *Activation Addition: Steering Language Models Without Optimization* — arXiv:2308.10248 — 一对 prompt 的激活差就能当方向盘：steering 的最简形态。
- ★ Panickssery et al. 2023, *Steering Llama 2 via Contrastive Activation Addition (CAA)* — arXiv:2312.06681 — 用成百上千对行为对比样本平均出干净的行为方向，steering 走向可靠。
- ★ Arditi et al. 2024, *Refusal in Language Models Is Mediated by a Single Direction* — arXiv:2406.11717 — 拒绝行为 = 一根方向；投影掉它即"白盒越狱"，安全行为脆弱性的机制证据。
- ★ Zou et al. 2023, *Representation Engineering: A Top-Down Approach to AI Transparency* — arXiv:2310.01405 — RepE 纲领：直接在表示层读取与控制诚实、情绪、危害性等高层概念。
- Li et al. 2023, *Inference-Time Intervention: Eliciting Truthful Answers from a Language Model (ITI)* — arXiv:2306.03341 — probe 找真实性方向、推理时平移激活，TruthfulQA 显著提升。

## 07 · Interp × 评测与安全审计

- ★ Marks et al. 2024, *Sparse Feature Circuits: Discovering and Editing Interpretable Causal Graphs in Language Models* — arXiv:2403.19647 — 用 SAE 特征当电路节点；SHIFT 方法手术移除分类器的虚假关联，interp 直接修模型的首例。
- ★ Lindsey et al. 2025, *On the Biology of a Large Language Model* — transformer-circuits.pub/2025/attribution-graphs/biology — 用 attribution graph 追踪 Claude 的多步推理、提前规划、幻觉与拒绝的内部机制；circuit tracing 的展示性大作。
- Ameisen et al. 2025, *Circuit Tracing: Revealing Computational Graphs in Language Models* — transformer-circuits.pub/2025/attribution-graphs/methods — 上文的方法论篇：replacement model + 归因图怎么造。
- Lindsey et al. 2024, *Sparse Crosscoders for Cross-Layer Features and Model Diffing* — transformer-circuits.pub/2024/crosscoders — crosscoder 让"比较 base 与 fine-tuned 模型的特征差异"成为可能，model diffing 的核心工具。
- Hubinger et al. 2024, *Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training* — arXiv:2401.05566 — 植入后门的模型能扛住安全训练；行为评测查不出，是 interp 审计的动机性反例。
- MacDiarmid et al. 2024, *Simple Probes Can Catch Sleeper Agents* — anthropic.com/research/probes-catch-sleeper-agents — 线性 probe 能高准确率识别 sleeper agent 的后门状态：白盒证据补上行为评测的盲区。
- Marks et al. 2025, *Auditing Language Models for Hidden Objectives* — arXiv:2503.10965 — 盲审演习：多支队伍用 interp + 行为工具找植入的隐藏目标，检验 interp 的实战审计能力。
