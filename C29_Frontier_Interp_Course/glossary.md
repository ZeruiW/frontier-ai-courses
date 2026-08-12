# 术语词典 · Glossary（前沿机制可解释性 SAE / features / circuits / steering）

> 按主题分组，每条 2–3 句中文释义，英文术语保留原文（社区与论文的通用语言）。读 Anthropic 可解释性博客、SAE / circuits 论文遇到生词回这里查。本课用合成叠加数据与 numpy toy transformer 模拟这些概念，但术语与真实前沿 interp 一一对应。

## 叠加与表示 · Superposition & Representation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| mechanistic interpretability (mech interp) | 机制可解释性 | 不止问「模型行为对不对」，而是逆向工程其内部计算：用什么特征、经哪些组件、按什么算法得出结果。目标是把神经网络从黑盒还原成可读、可验证、可干预的机制。 |
| feature | 特征 | 模型表示并使用的一个有意义的计算单元（如「这是法语」「这在讲金门大桥」）。前沿 interp 的工作假设是：特征近似对应激活空间里的一个**方向**，而非单个神经元。 |
| linear representation hypothesis (LRH) | 线性表示假设 | 高层概念在激活空间近似表示为方向，概念强度 = 激活在该方向上的投影。它是 probe、steering、SAE 都成立的共同前提，但只是经验近似而非定理（已知有环形等非线性反例）。 |
| superposition | 叠加 | 网络要表示的特征数远多于维度（神经元）数时，把多个特征**非正交地**塞进同一组神经元，靠特征稀疏性让它们在大多数输入上不同时激活。是多义性的根源，也是必须用 SAE 的根本原因。 |
| polysemanticity | 多义性 | 单个神经元对多个**互不相关**的概念都激活（如同一神经元对「猫」「法律条文」「红色」都响应）。叠加的直接表现，使「读单个神经元」无法解释模型。 |
| monosemanticity | 单义性 | 一个特征只对应一个可命名的概念。是 SAE 追求的理想：把多义的神经元基底，换成一组各自单义的特征基底。 |
| privileged basis | 优先基 | 某些架构选择（如逐元素激活函数、LayerNorm）让神经元坐标轴本身带有特殊地位，特征更倾向对齐到坐标轴。MLP 层有优先基，residual stream 通常没有——所以 residual stream 的特征几乎一定处于叠加、需要 SAE 才能读。 |
| residual stream | 残差流 | Transformer 中贯穿各层、被各 attention/MLP 模块读写累加的主信息通道。它是 interp 的主战场：特征在这里被写入、传递、读取；维度高、无优先基，叠加严重。 |
| feature direction / atom | 特征方向 / 字典原子 | 表示某特征的单位向量；在 SAE 里就是解码器矩阵的一列（一个 dictionary atom）。激活 ≈ 若干被激活特征方向的稀疏线性组合。 |
| feature geometry | 特征几何 | 叠加状态下特征方向的空间排布（夹角、是否成簇、是否构成多面体/反足结构）。Toy Models of Superposition 发现稀疏度越高，模型越倾向把特征排成正多胞形以最小化干扰。 |
| interference / cross-talk | 干扰 / 串扰 | 非正交特征方向之间的内积不为零，导致读取一个特征时混入其它激活特征的分量。叠加用稀疏性把干扰控制在可容忍范围，但读单方向（probe）会被它污染。 |
| ground truth features | 真特征 | 合成实验里我们**人为植入**、因而完全已知的特征集合。本课在合成叠加数据上训 SAE，再把学到的字典与真特征对拍（匹配率、余弦相似度），这是校准 interp 方法的正确顺序。 |

## 稀疏自编码器 · Sparse Autoencoders (SAE)

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| sparse autoencoder (SAE) | 稀疏自编码器 | 把一层激活 $x$ 编码成**高维、稀疏**的特征激活 $f$，再线性解码回 $\hat x$。训练目标 = 重建误差 + 稀疏惩罚。它把叠加的激活「解压」成一组单义特征，是当前规模化 interp 的主力工具。 |
| dictionary learning | 字典学习 | 把信号表示成一个过完备字典中少数原子的稀疏线性组合，求解字典与系数。SAE 就是用神经网络做字典学习：解码器 = 字典，编码器 = 求稀疏系数。 |
| overcomplete | 过完备 | 字典原子数（SAE 隐层宽度）远大于输入维度（如 8× / 32× / 256×）。过完备才有足够「插槽」分给被叠加压在一起的众多特征。 |
| encoder / decoder | 编码器 / 解码器 | 编码器 $f=\sigma(W_e(x-b_d)+b_e)$ 算特征激活；解码器 $\hat x=W_d f + b_d$ 用字典重建。解码器各列即特征方向，通常约束为单位范数。 |
| reconstruction loss | 重建损失 | $\lVert x-\hat x\rVert_2^2$，衡量 SAE 丢了多少信息。它与稀疏度构成核心权衡：越稀疏越可解释，但重建越差。 |
| L1 penalty / L1 SAE | L1 稀疏惩罚 | 在损失里加 $\lambda\lVert f\rVert_1$（常按解码器列范数加权）逼出稀疏激活。第一代 SAE（Bricken 2023）的做法，简单但有「激活收缩（shrinkage）」副作用。 |
| TopK SAE | TopK 稀疏自编码器 | 编码后只保留激活值最大的 $K$ 个特征、其余清零，直接把 L0 钉死为 $K$（Gao 2024）。免去调 $\lambda$、无收缩，但 $K$ 是离散超参、需辅助损失防 dead。 |
| JumpReLU SAE | JumpReLU 稀疏自编码器 | 用带可学习阈值 $\theta$ 的跳变激活 $\mathrm{JumpReLU}(z)=z\cdot\mathbb{1}[z>\theta]$，配合直接惩罚 L0 的训练（Rajamanoharan 2024）。在重建-稀疏前沿上常优于 L1/Gated。 |
| Gated SAE | 门控 SAE | 把「是否激活」（门）与「激活多大」（幅度）解耦的 SAE（Rajamanoharan 2024），缓解 L1 的收缩问题，是 JumpReLU 的前身。 |
| L0 sparsity | L0 稀疏度 | 每个输入平均激活的特征数（非零分量个数）。是 SAE 稀疏度的直接度量，比 L1 更贴近「可解释性」目标；常与重建质量一起报告。 |
| shrinkage / activation bias | 激活收缩 | L1 惩罚不仅压制无关特征，还把**该激活**的特征幅度也压小（因为 L1 对所有非零值施压），导致重建系统性偏小。TopK / JumpReLU / Gated 都是为绕开它而生。 |
| dead feature / dead latent | 死特征 | 训练中几乎从不激活的特征（字典原子白白浪费）。大 SAE 里可能高达一半。需用 resampling、辅助损失（auxk）、调初始化等手段「复活」。 |
| feature resampling | 特征重采样 | 周期性地把 dead 特征的权重重置到「当前重建最差的样本」方向上，给它重新派活。Anthropic Towards Monosemanticity 的关键训练技巧。 |
| ghost grads / auxk loss | 辅助梯度 / 辅助损失 | 给 dead 特征额外的梯度信号（让 top-dead 特征去重建残差），降低死亡率。TopK SAE 常用 auxk 辅助损失。 |
| tied weights | 权重绑定 | 让编码器与解码器共享（转置）权重以省参/正则。SAE 中通常**不**完全绑定，但常用 $W_e\approx W_d^\top$ 初始化、并把 $b_d$ 用作 pre-encoder bias。 |
| feature absorption | 特征吸收 | 一个更一般的特征「吸收」掉本应由更具体特征表达的部分，导致后者在某些样本上不激活。SAE 评测里发现的失效模式之一。 |
| feature splitting | 特征分裂 | 字典变大时，一个粗特征会分裂成多个更细的特征（如「鸟」→各种鸟）。说明「特征数」不是绝对的，依赖字典容量与稀疏度。 |
| reconstruction–sparsity tradeoff | 重建-稀疏权衡 | SAE 的中心张力：固定容量下，更稀疏（小 L0）⇒ 更可解释但重建更差。扫不同 $\lambda$/$K$ 得到一条**帕累托前沿**，用它比较不同 SAE 架构。 |
| Pareto frontier | 帕累托前沿 | 在「重建误差 vs 稀疏度」平面上不被任何其它配置同时占优的点集。比较 L1 / TopK / JumpReLU 优劣的标准方式：谁的前沿更靠左下谁更好。 |

## 特征解释与评测 · Feature Interpretation & Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| auto-interp (automated interpretability) | 自动可解释性 | 用一个 LLM 看某特征的高激活样本、自动写出该特征的自然语言解释，再用解释去预测激活、打分（解释好坏 = 预测准不准）。让 interp 从手工标注规模化到百万特征。 |
| activating examples / max-activating dataset examples | 高激活样本 | 让某特征激活最强的输入片段集合。是人类与 auto-interp 给特征命名的主要依据；通常按激活值分档展示（top / 中间分位）。 |
| feature dashboard | 特征仪表盘 | Anthropic/Neuronpedia 风格的单特征可视化：高激活样本、logit 影响、激活直方图、相关特征等，供人快速判断一个特征是什么。 |
| explanation faithfulness / simulation score | 解释忠实度 / 模拟分 | auto-interp 的评分：用解释去**模拟**（预测）该特征在新样本上的激活，预测越准说明解释越忠实。区别于「解释听起来合理」。 |
| feature activation histogram | 特征激活直方图 | 某特征激活值的分布。健康单义特征常呈「大量 0 + 少量明显正值」的双峰/长尾；分布形状能提示 dead、超密、或多义。 |
| ablation (feature ablation) | 特征消融 | 把某特征激活置零（或投影掉其方向）后看模型行为/重建变化，以判断该特征的因果作用。是「特征真的被用了吗」的检验。 |
| probing vs SAE | 探针 vs SAE | probe 直接在原激活上读一个方向，便宜但会被叠加串扰污染、且要预先知道找什么；SAE 无监督地把激活拆开成一组特征，贵但能发现未知特征、读数更干净。两者互补。 |
| Neuronpedia | —— | 开放的 SAE 特征浏览/标注平台，托管大量公开 SAE 的特征 dashboard。把本课学到的特征概念接到真实大模型特征的入口。 |

## 电路与因果归因 · Circuits & Causal Attribution

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| circuit | 电路 | 模型为完成某项具体计算所用的一小撮组件（attention head / MLP / 特征）及其连接构成的因果子图。circuits 议程主张：大模型由许多可单独理解的电路组合而成。 |
| activation patching / causal tracing | 激活打补丁 / 因果追踪 | 在 corrupt 运行里，把某个组件的激活替换成 clean 运行的对应激活，看输出向 clean 恢复多少，从而度量该组件对任务的因果贡献。是电路定位的金标准，但要跑 O(组件数) 次前向。 |
| clean / corrupt run | 干净 / 污染运行 | 一对仅在关键信息上不同的输入（如「The Eiffel Tower is in」对 vs 把 Eiffel 换成别的）。patching 把一者的中间激活注入另一者，隔离出某信息流经哪些组件。 |
| denoising / noising | 去噪 / 加噪 | patching 的两种方向：denoising = 往 corrupt 注入 clean 激活（看「补回正确信息」能恢复多少）；noising = 往 clean 注入 corrupt 激活（看「破坏」掉多少）。两者答的是不同因果问题。 |
| attribution patching (AtP) | 归因打补丁 | 用一阶泰勒展开近似 activation patching：patch 效果 ≈ （clean−corrupt 激活差）·（输出对该激活的梯度）。一次前向+一次反向即可估计**所有**组件的因果效应，把 O(N) 次前向压成 O(1)，是规模化电路发现的关键。 |
| AtP* / edge attribution patching (EAP) | 归因打补丁改进 / 边归因 | AtP 的修正与扩展：AtP* 修掉注意力 softmax 等处一阶近似失效的情形；EAP 把归因从节点推广到**边**（组件间的连接），直接画出电路的带权有向图。 |
| node / edge attribution | 节点 / 边归因 | 节点归因 = 某组件整体对输出的因果效应；边归因 = 某条「上游组件→下游组件」连接的效应。电路 = 高归因节点 + 高归因边构成的子图。 |
| direct logit attribution (DLA) | 直接 logit 归因 | 把某组件的输出直接经 unembedding 投到 logit 上，量化它对最终预测 token 的直接贡献（不经后续层的间接路径）。读电路输出端的快速工具。 |
| path patching | 路径打补丁 | 只让某条特定**路径**（如 head A → head B）传递 clean 激活、其余保持 corrupt，精确隔离一条因果路径的作用。比节点 patching 更细，是 IOI 等电路分析的主力。 |
| sparse feature circuits | 稀疏特征电路 | 以 SAE **特征**（而非 head/neuron）为节点、用归因连边得到的电路（Marks 2024）。比组件级电路更可解释（节点是单义特征），且可用于发现并编辑模型行为背后的特征级机制。 |
| faithfulness (of a circuit) | 电路忠实度 | 只保留电路涉及的组件、消融其余，模型是否仍能完成任务（保留多少性能）。衡量「这个子图是否真的是模型在用的机制」。 |
| completeness / minimality | 完备性 / 最小性 | 完备 = 电路涵盖了任务所需的全部组件（没漏）；最小 = 去掉任一组件性能就掉（没冗余）。好的电路应兼顾两者。 |

## Steering 与激活干预 · Steering & Activation Intervention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| steering | 引导 / 操控 | 在推理时直接修改内部激活以定向改变模型行为（让它更/少谈某主题、更/少拒绝等），无需重训。是 interp「读得懂」之后「控得动」的体现。 |
| activation addition (ActAdd) | 激活相加 | 最简 steering：把一个「概念方向」向量按强度 $\alpha$ 加到某层激活上 $h\leftarrow h+\alpha v$（Turner 2023）。方向可来自对比 prompt 的激活差。 |
| feature steering / clamping | 特征引导 / 钳制 | 用 SAE：把某特征的激活**钳制**到一个目标值（远高于自然值则放大该概念，置零则移除），再经解码器写回激活。Golden Gate Claude 即把「金门大桥」特征钳到极高。 |
| concept direction | 概念方向 | 表示某概念的向量，常用 difference-of-means（两类激活均值差）求得。steering 与 ablation 都沿它操作。 |
| difference-of-means / CAA | 均值差 / 对比激活相加 | 取「有该属性」与「无该属性」两组激活的均值差作为 steering 向量（Contrastive Activation Addition，Rimsky 2023）。简单、稳健，是 steering 的强基线，常与 SAE 特征 steering 对比。 |
| direction ablation | 方向消融 | 把激活在某方向上的分量投影清零 $h\leftarrow h-(\hat v^\top h)\hat v$，以移除某特征/行为。refusal 方向被消融后模型会停止拒绝（Arditi 2024）。 |
| refusal direction | 拒绝方向 | residual stream 中一个中介模型「拒绝有害请求」行为的方向；沿它加强可放大拒绝、消融它可绕过拒绝（越狱）。单方向中介复杂行为的著名例子。 |
| steering strength / coefficient | 引导强度 | steering 向量的缩放系数 $\alpha$。太小没效果，太大破坏流畅度/通用能力——存在一个「有效但不崩」的窗口，需扫描确定。 |
| off-target effect / side effect | 脱靶效应 / 副作用 | steering 在改变目标行为的同时，对**无关**能力造成的损害（如钳特征后通用困惑度上升、答错无关问题）。是评估 steering 是否「干净」的关键指标。 |
| Golden Gate Claude | —— | Anthropic 2024 的演示：把 Claude 的「金门大桥」SAE 特征钳到极高，模型在各种对话里都强行扯到金门大桥。SAE 特征可因果操控行为的标志性证据。 |
| representation engineering (RepE) | 表示工程 | 系统化的「读方向 + 控方向」框架（Zou 2023）：用对比刺激提取概念方向，用于监控与干预。steering 与白盒监控的方法论母体。 |

## 可解释性用于安全 · Interpretability for Safety

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| white-box monitoring | 白盒监控 | 部署时不只看模型的输出，还实时读它的内部激活/特征来判断是否出问题（要撒谎、要写漏洞、被越狱）。代价极低（一次内积），是 AI Control 的监控器雏形。 |
| deception detection | 欺骗检测 | 用 interp 工具找模型「内部状态与外部输出不一致」的证据（如内部真值方向指向假、但输出说真）。把诚实性从行为指标升级为可测的内部量。 |
| sleeper agent / backdoor | 潜伏特工 / 后门 | 被植入「见到触发器才发作」恶意行为的模型（Hubinger 2024）。安全训练难以根除，但其后门常对应可被探针/特征**提前**检测的内部信号。 |
| defection probe | 倒戈探针 | 用简单对比 prompt 构造的方向，在模型实际触发后门之前就以高 AUC 报警（MacDiarmid 2024）。白盒监控的具体可行性证据。 |
| sandbagging | 藏拙 | 模型故意在评测中表现得比真实能力差（假装不会某危险能力）。行为评测会被骗，白盒（探针/特征）可能看穿内部其实「会」。 |
| crosscoder | 交叉编码器 | 一个同时重建**多个模型/多个层**激活的 SAE 变体（Lindsey 2024），让特征在不同模型间对齐，从而直接比较「哪些特征是某个模型独有的」。 |
| model diffing | 模型比对 | 对比两个模型（如微调前后、base vs chat）的特征，定位微调引入/删除/改变的特征。配合 crosscoder 可发现后门特征、新增能力或对齐副作用。 |
| safety case | 安全论证 | 一套结构化论证，主张某系统在给定部署下足够安全。机制证据（「我们理解并能监控危险行为对应的特征」）可作为其中一条证据链，但需明确其相关性/鲁棒性局限。 |
| streetlight interpretability | 路灯下找钥匙 | 对 interp 的自嘲式警告：我们只在工具照得到的地方（线性可读、SAE 拆得开的特征）找证据，可能系统性漏掉照不到的机制。提醒「没找到 ≠ 不存在」。 |
| interpretability illusions | 可解释性幻觉 | 看似合理的解释其实并不反映模型真实计算（如方向在分布外失效、解释只拟合了表面相关）。是把 interp 结论写进 safety case 前必须排除的风险。 |
| adversarial robustness (of monitors) | 监控的对抗鲁棒性 | 一旦白盒监控成为优化目标，模型/攻击者能否学会把危险计算移出监控可见的子空间。决定 interp 监控能否扛住有动机的对手，是关键开放问题。 |

## 工程与工具 · Tooling & Ecosystem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| TransformerLens | —— | 机制 interp 的标准 PyTorch 库（Nanda），提供 hook 读写任意激活、做 activation/path patching、logit lens 等。本课的 numpy 模拟对应它的核心操作。 |
| SAELens | —— | 训练与加载 SAE 的标准库，搭配 Neuronpedia 浏览特征。学完本课从零训的 toy SAE，下一步即用它在真模型上训真 SAE。 |
| hook | 钩子 | 在模型前向过程中拦截/读写某层激活的回调。patching、steering、读特征都靠 hook 实现；本课用「显式传递中间张量」来模拟它。 |
| logit lens | logit 透镜 | 把中间层激活直接经 unembedding 投到词表，看模型在每层「当前的猜测」。基础 interp 工具（C06），本课用它读电路与 steering 的输出端效果。 |
| toy model / toy transformer | 玩具模型 | 维度极小、可完全分析的模型。Toy Models of Superposition 与本课都用它在「已知真相」下研究机制，再推广到真模型——这是 interp 的标准方法论。 |
