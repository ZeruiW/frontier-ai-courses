# 参考清单 · References（图机器学习 / 图神经网络）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制，都能在下列文献里找到完整推导与真实大图上的实现与权衡。

## 谱图理论与图表示学习起点 · Spectral Foundations & Early Graph Embedding
- ★ **Chung 1997, _Spectral Graph Theory_** — 谱图理论的标准参考。讲清图拉普拉斯（组合/归一化）、特征值与连通性、Cheeger 不等式（谱隙 ↔ 图割）。本课模块 01 的所有谱结论（零特征值重数 = 连通分量数、Fiedler 向量谱聚类）都源出于此。
- ★ **von Luxburg 2007, _A Tutorial on Spectral Clustering_** — 谱聚类最清晰的综述。从图割松弛推导出"取最小 $k$ 个特征向量 + k-means"，对比三种拉普拉斯。模块 01 谱聚类实现的直接蓝本，强烈建议配套精读。
- **Shi & Malik 2000, _Normalized Cuts and Image Segmentation_** — 把归一化割与广义特征问题联系起来的经典，谱聚类的源头之一。理解"为什么归一化拉普拉斯比组合型更适合聚类"。
- **Perozzi et al. 2014, _DeepWalk_** 与 **Grover & Leskovec 2016, _node2vec_** — GNN 之前的主流图表示学习：用随机游走 + skip-gram 学节点嵌入。读它理解"邻近即相似"的朴素版本，以及 GraphSAGE 采样思想的前身。
- **Page et al. 1999, _The PageRank Citation Ranking_** — PageRank 原始报告：带重启随机游走的平稳分布做网页排序。模块 01 随机游走/PageRank 的来源，也是 APPNP 等"解耦传播"GNN 的灵感。

## 谱图卷积到 GCN · From Spectral Convolutions to GCN
- ★ **Kipf & Welling 2017, _Semi-Supervised Classification with Graph Convolutional Networks_** — 本课模块 02 的核心。把谱图卷积一阶 + 重整化近似简化成传播规则 $H'=\sigma(\hat A H W)$，$\hat A=\tilde D^{-1/2}\tilde A\tilde D^{-1/2}$。极简、好训、效果强，是所有 GNN 的基线。必读。
- ★ **Bruna et al. 2014, _Spectral Networks and Deep Locally Connected Networks on Graphs_** — 第一篇把卷积用图傅里叶（拉普拉斯特征基）严格定义到图上的工作。读它理解 GCN 是从哪条"谱域逐元素相乘"的路线简化来的，以及其局部性/计算量问题。
- ★ **Defferrard et al. 2016, _ChebNet: Convolutional Neural Networks on Graphs with Fast Localized Spectral Filtering_** — 用切比雪夫多项式逼近谱滤波器，避免显式特征分解、得到 $K$-跳局部卷积。GCN 是它 $K=1$ 的特例；理解谱 → 空间的过渡靠这篇。
- **Wu et al. 2019, _Simplifying Graph Convolutional Networks (SGC)_** — 把 GCN 的非线性全部去掉、预计算 $\hat A^K X$ 再接一个线性分类器，效果几乎不降。它揭示 GCN 大部分威力来自"传播"而非"深度非线性"，是理解过平滑与"传播-变换解耦"的关键反思。

## 空间型 GNN：消息传递、注意力、采样 · Spatial GNNs
- ★ **Gilmer et al. 2017, _Neural Message Passing for Quantum Chemistry (MPNN)_** — 把当时各种图网络统一成"消息 → 聚合 → 更新"的 MPNN 框架，并用于分子性质预测。本课模块 02–03 的总纲：GCN/GAT/SAGE 都是它的实例。必读。
- ★ **Veličković et al. 2018, _Graph Attention Networks (GAT)_** — 给每条边学一个注意力权重，替代 GCN 的固定度归一化，让节点自适应加权邻居 + 多头稳定。模块 03 前半的核心，注意力聚合的代表作。必读。
- ★ **Hamilton et al. 2017, _Inductive Representation Learning on Large Graphs (GraphSAGE)_** — 用"邻居采样 + 可学习聚合器（mean/pool/LSTM）"把 GNN 从直推变归纳，能为新节点/新图生成表示，并扩展到大图。模块 03 后半与模块 05 采样的核心。必读。
- **Xu et al. 2019, _How Powerful are Graph Neural Networks? (GIN)_** — 用 sum 聚合 + MLP 使 GNN 达到 1-WL 表达力上界，并证明 mean/max 聚合会丢失哪些结构信息。理解"GNN 能区分哪些图、为何 sum 最强"必读，模块 05 表达力讨论的依据。
- **Hamilton 2020, _Graph Representation Learning_（书）** — 体系化的 GNN 教材（免费）：从谱方法、节点嵌入到消息传递与理论。作为本课的纸质伴侣，章节顺序与本课高度一致。

## 过平滑、过挤压与深层 GNN · Over-smoothing, Over-squashing & Depth
- ★ **Li et al. 2018, _Deeper Insights into Graph Convolutional Networks for Semi-Supervised Learning_** — 首次把 GCN 的"层数越深越糟"诊断为过平滑：反复 $\hat A$ 平均等价于随机游走收敛，节点表示趋同。模块 02/05 过平滑一节的来源。必读。
- ★ **Alon & Yahav 2021, _On the Bottleneck of Graph Neural Networks and its Practical Implications_** — 提出并命名过挤压（over-squashing）：长程信息穿过图瓶颈时被压进固定维向量而失真。解释 MPNN 难学长程依赖、催生图 Transformer/重连。模块 04/05 必读。
- **Topping et al. 2022, _Understanding Over-squashing and Bottlenecks on Graphs via Curvature_** — 用 Ricci 曲率刻画过挤压发生的边，并据此重连图。把"瓶颈"从直觉变成可计算的几何量，是图重连方向的代表。
- **Oono & Suzuki 2020, _Graph Neural Networks Exponentially Lose Expressive Power for Node Classification_** — 从理论证明深层 GCN 的表示按谱隙指数收敛到低维子空间（过平滑的严格版）。想要过平滑的定量结论读它。
- **Rusch et al. 2023, _A Survey on Over-smoothing in GNNs_** — 系统梳理过平滑的定义（含 Dirichlet 能量度量）、成因与各类缓解手段（残差、PairNorm、解耦传播）。模块 05 诊断与对策的总览。

## 图 Transformer 与位置编码 · Graph Transformers & Positional Encoding
- ★ **Dwivedi & Bresson 2021, _A Generalization of Transformer Networks to Graphs_** — 把 Transformer 系统地搬到图上，并首次用拉普拉斯特征向量做位置编码（LapPE）。模块 04 全程在复现它的核心思想。必读。
- ★ **Ying et al. 2021, _Do Transformers Really Perform Bad for Graph Representation? (Graphormer)_** — 用度编码 + 最短路径空间编码 + 边编码把图结构注入标准 Transformer，在分子基准夺冠。证明"全局注意力 + 好的结构编码"可超越 MPNN。必读。
- **Rampášek et al. 2022, _Recipe for a General, Powerful, Scalable Graph Transformer (GraphGPS)_** — 提出"局部消息传递 + 全局注意力"的混合层模板与模块化位置/结构编码。当前图 Transformer 的主流范式，模块 04 混合层一节的依据。
- **Kreuzer et al. 2021, _Rethinking Graph Transformers with Spectral Attention (SAN)_** — 用完整拉普拉斯谱做可学习的位置注意力。深入理解谱信息如何进入注意力。
- **Lim et al. 2023, _Sign and Basis Invariant Networks (SignNet/BasisNet)_** — 正面解决 LapPE 的符号与基歧义，构造对 $u\mapsto -u$ 与同特征值子空间旋转不变的编码。模块 04 符号歧义一节的解法来源。

## 可扩展性与应用 · Scalability & Applications
- ★ **Chiang et al. 2019, _Cluster-GCN_** — 先把大图用图聚类切成子图块、按块做 mini-batch，使全图 GNN 能在有限显存上训练超大图。模块 05 采样/分块训练的代表。
- **Zeng et al. 2020, _GraphSAINT_** — 基于子图采样的 mini-batch 训练，带方差缩减的无偏估计。与 Cluster-GCN 并列的大图训练方案。
- **Kipf & Welling 2016, _Variational Graph Auto-Encoders (VGAE)_** — 用 GCN 编码 + 内积解码做链接预测的奠基工作。模块 05 链接预测（编码器-解码器 + 负采样）的直接蓝本。必读。
- **Zhang & Chen 2018, _Link Prediction Based on Graph Neural Networks (SEAL)_** — 把链接预测建模为对"封闭子图"分类，超越朴素点积解码。理解链接预测的更强范式。
- **Hu et al. 2020, _Open Graph Benchmark (OGB)_** — 大规模、真实、统一评测的图基准（节点/边/图级）。把本课的小图方法接到真实规模评测的入口。
- **Stokes et al. 2020, _A Deep Learning Approach to Antibiotic Discovery_** — 用 GNN（消息传递）筛选出新型抗生素 halicin 的著名应用。读它体会图分类/分子表示在现实科学发现中的威力。

## 综述、几何深度学习与本课定位 · Surveys, GDL & Scope
- ★ **Bronstein et al. 2021, _Geometric Deep Learning: Grids, Groups, Graphs, Geodesics, and Gauges_** — 用对称性/不变性统一 CNN、GNN、Transformer 的纲领性长文（"GDL blueprint"）。它给出本课的世界观：GNN = 对置换群不变/等变的深度学习。强烈建议先读其导论。
- **Wu et al. 2021, _A Comprehensive Survey on Graph Neural Networks_** — GNN 的全景综述（谱/空间/池化/时空），适合查找某一类方法的代表作与脉络。
- ⚠️ **本课定位**：全程用 numpy 在 CPU 上**从零**实现——邻接/拉普拉斯/谱聚类、GCN/GAT/SAGE 的前向与（必要处的）反向、图 Transformer 的 LapPE + 全局注意力、链接预测与图分类。用小图（合成 SBM、Karate club、小 Cora-like 引文图，联网失败回退到内置真实数值）保证**可复现、可对拍**：谱聚类对拍 ground-truth 社区、稀疏 vs 稠密传播对拍、注意力系数对拍手算、训练损失单调下降。
- **可迁移性**：你在 numpy 里验证过的传播规则、注意力归一化、采样与读出逻辑，可几乎一对一改写成 **PyTorch Geometric (PyG)** 或 **DGL** 的层。本课刻意让实现贴近这些框架的语义。
- **课程衔接**：上游接 ML 基础（C07）、深度学习理论（C14）、经典架构（C15，含注意力）；与生成模型（C16，图生成/扩散）、前沿架构（C20）互补；下游可接知识图谱、推荐系统、分子/材料、组合优化等应用方向。
