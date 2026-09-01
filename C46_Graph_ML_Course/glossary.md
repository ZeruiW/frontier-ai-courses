# 术语词典 · Glossary（图机器学习 / 图神经网络）

> 按主题分组，每条 2–3 句释义。读 Kipf GCN / Veličković GAT / Hamilton GraphSAGE / Gilmer MPNN / 图 Transformer 论文遇到生词回这里查；英文术语保留原文（社区论文与 PyG/DGL 文档的通用语言）。本课用 numpy 在 CPU 上从零实现这些概念，术语与真实框架一一对应。

## 图的基本对象 · Graph Primitives

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| graph $G=(V,E)$ | 图 | 由节点集合 $V$（顶点 vertices）与边集合 $E$ 组成的结构。它显式编码"谁和谁相连"的关系，是社交网络、分子、知识图谱、引文网等非欧数据的自然表示。 |
| node / vertex | 节点 / 顶点 | 图的基本单元，常带一个特征向量 $x_v\in\mathbb{R}^F$（如用户画像、原子类型）。GNN 的目标多是为每个节点学一个表示（embedding）。 |
| edge | 边 | 节点间的连接，可有向/无向、带权/不带权、带类型（关系）。边定义了信息在图上流动的通道——GNN 沿边传递消息。 |
| neighborhood $\mathcal{N}(v)$ | 邻域 | 与节点 $v$ 直接相连的节点集合。GNN 的核心假设是"一个节点由它的邻居刻画"，每层用邻域信息更新节点表示。 |
| degree $d_v$ | 度 | 节点的邻居数（有向图分入度/出度）。度的大小差异巨大（幂律分布）是图数据的常态，也是归一化与采样要处理的核心难点。 |
| adjacency matrix $A$ | 邻接矩阵 | $n\times n$ 矩阵，$A_{ij}=1$（或边权）当 $i,j$ 相连。它把图的结构装进线性代数，使"传播一步"等于一次矩阵乘 $AX$；真实图稀疏，故常用稀疏存储。 |
| degree matrix $D$ | 度矩阵 | 对角矩阵 $D_{ii}=d_i=\sum_j A_{ij}$。它是各种归一化（行归一化 $D^{-1}A$、对称归一化 $D^{-1/2}AD^{-1/2}$）的分母来源。 |
| feature matrix $X$ | 特征矩阵 | $n\times F$ 矩阵，第 $i$ 行是节点 $i$ 的输入特征。GNN 的输入是 $(A, X)$，输出是每节点 $H\in\mathbb{R}^{n\times F'}$ 的表示。 |
| self-loop | 自环 | 节点连到自己的边（$A_{ii}=1$）。GCN 用 $\tilde A=A+I$ 加自环，让节点聚合邻居时也保留自身信息，否则会"忘掉自己"。 |
| sparsity | 稀疏性 | 真实图的边数 $\vert E\vert \ll n^2$，邻接矩阵绝大多数是 0。利用稀疏性（只遍历真实边）是 GNN 能扩展到百万节点的前提。 |

## 谱图理论 · Spectral Graph Theory

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| graph Laplacian $L=D-A$ | 图拉普拉斯（组合型） | 图上的"二阶差分算子"，刻画信号在图上的不光滑程度。它半正定，二次型 $x^\top L x=\tfrac12\sum_{(i,j)\in E}(x_i-x_j)^2$ 度量相邻节点取值的差异。 |
| normalized Laplacian $L_{\text{sym}}$ | 归一化拉普拉斯 | $L_{\text{sym}}=I-D^{-1/2}AD^{-1/2}$，把度的影响标准化，特征值落在 $[0,2]$。它是 GCN 谱卷积推导的出发点，谱性质比组合型更规整。 |
| random-walk Laplacian $L_{\text{rw}}$ | 随机游走拉普拉斯 | $L_{\text{rw}}=I-D^{-1}A$。其与随机游走转移矩阵 $D^{-1}A$ 直接相关，谱聚类与 PageRank 的概率视角由它给出。 |
| eigenvalue / eigenvector | 特征值 / 特征向量 | $L$ 的特征分解 $L=U\Lambda U^\top$ 给出"图的傅里叶基"：特征向量是图上的"频率模式"，特征值是对应频率。低频 = 在图上平滑，高频 = 相邻剧烈变化。 |
| graph Fourier transform | 图傅里叶变换 | 用拉普拉斯特征向量作基，把节点信号 $x$ 变换到谱域 $\hat x=U^\top x$。它把"图上的卷积"定义为谱域逐元素相乘，是谱图卷积网络的理论根基。 |
| spectral gap / algebraic connectivity | 谱隙 / 代数连通度 | 第二小特征值 $\lambda_2$（Fiedler value）。它 $>0$ 当且仅当图连通；其大小度量图"有多难被切开"，与聚类、信息混合速度、过挤压都相关。 |
| Fiedler vector | Fiedler 向量 | $\lambda_2$ 对应的特征向量。按它的符号/取值给节点排序并切分，能得到一个低割（low-cut）的二分——这是谱聚类（spectral clustering）的核心。 |
| multiplicity of zero eigenvalue | 零特征值重数 | $L$ 的特征值 0 的重数等于图的连通分量个数。这是谱与拓扑联系的最干净结论之一，本课会用它从谱"数出"连通块。 |
| spectral clustering | 谱聚类 | 取 $L$ 最小的 $k$ 个特征向量作为节点的低维嵌入，再在该嵌入上跑 k-means。它把"图分割"松弛成连续特征问题，在 SBM 等结构上非常有效。 |
| Rayleigh quotient | 瑞利商 | $\tfrac{x^\top L x}{x^\top x}$。最小化它（在与常向量正交的约束下）即得 Fiedler 向量；它把"找最平滑的非平凡信号"变成可优化的标量目标。 |

## 随机游走与扩散 · Random Walks & Diffusion

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| random walk | 随机游走 | 从一个节点出发、每步按转移概率 $P=D^{-1}A$ 跳到某个邻居的过程。它是 node2vec、PageRank、GraphSAGE 采样、扩散模型的共同基元。 |
| transition matrix $P=D^{-1}A$ | 转移矩阵 | 行随机矩阵，$P_{ij}$ 是从 $i$ 走到 $j$ 的概率。$P^k$ 给出 $k$ 步后的分布，刻画信息/影响如何在图上扩散。 |
| stationary distribution $\pi$ | 平稳分布 | 满足 $\pi P=\pi$ 的分布，随机游走长期停留概率。无向连通图上 $\pi_i\propto d_i$（度越大越常被访问），是 PageRank 的无重启特例。 |
| PageRank | —— | 带重启的随机游走平稳分布：$\pi=(1-\alpha)\pi P+\alpha\,\mathbf{1}/n$。最初为网页排序，现广泛用于节点重要性、个性化传播（如 APPNP/PPNP）。 |
| personalized PageRank (PPR) | 个性化 PageRank | 重启向量集中在单个/一组种子节点，得到"以该节点为中心"的影响力分布。它给出一种不堆很多层就能聚合多跳邻居的传播方式。 |
| node2vec / DeepWalk | —— | 用随机游走生成"节点序列"，再套 word2vec（skip-gram）学节点嵌入的早期图表示学习方法。GNN 之前的主流，思想（邻近=相似）仍贯穿至今。 |
| mixing time | 混合时间 | 随机游走收敛到平稳分布所需步数，由谱隙决定（隙大则混得快）。它与 GNN 需要多少层才能让信息传遍全图直接相关。 |

## 消息传递与 GNN 框架 · Message Passing & GNN Framework

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| message passing (MPNN) | 消息传递（神经网络） | Gilmer 2017 统一框架：每层对每条边算"消息"、对每个节点"聚合"邻居消息、再"更新"节点状态。GCN/GAT/SAGE 都是它的特例，是理解一切空间型 GNN 的总纲。 |
| message function | 消息函数 | 由源节点、目标节点、边特征算出沿边传递信息的函数 $m_{uv}=\phi(h_u,h_v,e_{uv})$。最简形式就是直接传源节点表示。 |
| aggregation / permutation invariance | 聚合 / 置换不变 | 把一个节点收到的多条消息汇成一个向量的操作（sum/mean/max）。它必须对邻居顺序不敏感（置换不变），因为邻居本无次序——这是 GNN 设计的硬约束。 |
| update function | 更新函数 | 用聚合结果和节点旧状态算新状态 $h_v'=\psi(h_v,\text{agg})$，通常是一层 MLP + 非线性。它决定每层如何把邻域信息融进自身。 |
| readout / graph pooling | 读出 / 图池化 | 把所有节点表示汇成一个图级向量（sum/mean/max 或更复杂的池化）的操作，用于图级任务（如分子性质预测）。也必须置换不变。 |
| permutation equivariance | 置换等变 | 重排节点编号，GNN 的每节点输出随之同样重排（而非不变）。节点级任务要等变、图级任务要不变——这是几何深度学习对图模型的对称性要求。 |
| GCN (Graph Convolutional Network) | 图卷积网络 | Kipf & Welling 2017。一阶谱卷积近似得到的传播规则 $H'=\sigma(\hat A H W)$，其中 $\hat A=\tilde D^{-1/2}\tilde A\tilde D^{-1/2}$ 是加自环的对称归一化邻接。最具影响力的 GNN 基线。 |
| symmetric normalization $\hat A$ | 对称归一化邻接 | $\hat A=\tilde D^{-1/2}(A+I)\tilde D^{-1/2}$。它在聚合时按两端度数缩放每条边，防止高度数节点的表示尺度爆炸，让谱半径稳定在 1 附近。 |
| propagation rule | 传播规则 | 一层 GNN 把 $H$ 映射到 $H'$ 的具体公式（如 GCN 的 $\sigma(\hat A H W)$）。它 = 先按图结构混合邻居（$\hat A H$）、再线性变换（$W$）、再非线性（$\sigma$）。 |
| over-smoothing | 过平滑 | 堆太多 GNN 层后，所有节点表示趋同、无法区分的现象。本质是反复用 $\hat A$ 平均，等价于随机游走收敛到与度成正比的平稳分布，丢失了判别信息。 |
| Dirichlet energy | 狄利克雷能量 | $\mathcal{E}(H)=\operatorname{tr}(H^\top L H)=\tfrac12\sum_{(i,j)}\|h_i-h_j\|^2$，度量节点表示的不光滑度。过平滑表现为它随层数指数衰减到 0，是诊断过平滑的定量指标。 |

## 注意力与采样 GNN · Attention & Sampling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| GAT (Graph Attention Network) | 图注意力网络 | Veličković 2018。用注意力机制给每条边算一个可学习权重 $\alpha_{ij}$（而非 GCN 的固定度归一化），让节点自适应地决定"听哪个邻居"。 |
| attention coefficient $\alpha_{ij}$ | 注意力系数 | 边 $(i,j)$ 的归一化权重，由 $\mathrm{softmax}_j(\text{LeakyReLU}(a^\top[Wh_i\Vert Wh_j]))$ 得到。它在节点 $i$ 的邻域内归一化，使聚合是邻居的凸组合。 |
| multi-head attention | 多头注意力 | 并行跑多组独立注意力再拼接/平均，稳定训练、捕捉不同关系子空间。GAT 与图 Transformer 都靠它提升表达力与鲁棒性。 |
| GraphSAGE | —— | Hamilton 2017。核心是"采样固定数目邻居 + 可学习聚合器"，把 GNN 从直推（transductive）推向归纳（inductive），能为训练时未见过的新节点生成表示。 |
| neighbor sampling | 邻居采样 | 每层为每个节点只随机采样固定数目（如 25、10）邻居参与聚合，把计算/显存从随度数爆炸压成可控，是 GNN 扩展到大图的关键。 |
| aggregator (mean/pool/LSTM) | 聚合器 | GraphSAGE 把聚合抽象成可替换组件：mean（平均）、pool（逐元素 max + MLP）、LSTM 等。聚合器的表达力直接影响模型能区分多少种邻域结构。 |
| inductive vs transductive | 归纳 vs 直推 | 直推：训练/测试在同一张固定图上（如 GCN 用整图）；归纳：模型能泛化到新节点甚至新图（如 SAGE 学的是聚合函数而非具体节点的嵌入）。 |
| mini-batch on graphs | 图上的小批量 | 因节点相互依赖，图上无法像 i.i.d. 数据那样随便切 batch。常用做法是采样目标节点 + 其 $k$-跳邻居子图，cluster-GCN 则先把图切块。 |

## 图 Transformer 与位置编码 · Graph Transformers & PE

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| graph transformer | 图 Transformer | 把 Transformer 的全局自注意力搬到图上：每个节点可关注所有节点（而非只邻居），用位置/结构编码注入图拓扑。绕开消息传递的局部性与过挤压。 |
| Laplacian positional encoding (LapPE) | 拉普拉斯位置编码 | 取拉普拉斯最小的若干非平凡特征向量作为每个节点的"坐标"，是图上对应 Transformer 正弦位置编码的自然推广，提供全局位置信息。 |
| sign ambiguity | 符号歧义 | 特征向量 $u$ 与 $-u$ 同为合法特征向量，故 LapPE 有符号不确定性。训练时随机翻转符号做增强，或用对符号不变的编码（如 SignNet）来处理。 |
| structural encoding | 结构编码 | 注入局部结构信息（如度、三角形数、随机游走回到自身的概率 RWSE）的特征，帮助注意力区分结构等价但位置不同的节点。 |
| distance encoding | 距离编码 | 把节点对的最短路径距离 / 随机游走可达概率编入注意力偏置（如 Graphormer 的 spatial bias），让全局注意力仍感知图上的远近。 |
| Graphormer | —— | Ying 2021。用度编码 + 最短路径空间编码 + 边编码把图结构注入标准 Transformer，在分子图基准上取得 SOTA，是图 Transformer 的代表作。 |
| global attention | 全局注意力 | 每个节点与所有节点交互（$O(n^2)$），一步即可建立长程依赖，与 MPNN 的逐跳局部传播互补；代价是计算量与对结构先验的依赖。 |
| GPS / hybrid layer | 混合层 | 同时含一支局部消息传递与一支全局注意力的层（如 GraphGPS），兼得局部归纳偏置与全局长程建模，是当前图 Transformer 的主流范式。 |

## 任务、应用与病理 · Tasks, Applications & Pathologies

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| node classification | 节点分类 | 给图中部分节点带标签，预测其余节点的类别（如引文网里论文的主题）。最常见的直推任务，GCN 的经典 benchmark（Cora/Citeseer/Pubmed）。 |
| link prediction | 链接预测 | 预测两个节点之间是否（将）存在边（如推荐、知识图谱补全）。常用编码器（GNN 得节点嵌入）+ 解码器（点积/MLP 打分）+ 负采样训练。 |
| graph classification | 图分类 | 为整张图预测一个标签（如分子是否有毒）。需 readout 把节点表示汇成图向量，是图级任务的代表。 |
| negative sampling | 负采样 | 链接预测中为没有边的节点对采样作负样本，与正样本（真实边）一起训二分类。采样策略（随机/难负例）显著影响效果。 |
| dot-product decoder | 点积解码器 | 用两节点嵌入的内积 $\sigma(z_i^\top z_j)$ 给边打分的最简解码器。配合 GNN 编码器即得 GAE/VGAE 式链接预测器。 |
| AUC (ROC-AUC) | 曲线下面积 | 链接预测/二分类常用指标，等于"随机一对正负样本，模型给正样本更高分的概率"，对阈值与类别不平衡不敏感。 |
| over-squashing | 过挤压 | 长程信息要穿过狭窄的图瓶颈（低谱隙处）传递时，被压缩进固定维向量而严重失真的现象。它解释了 MPNN 为何难学长程依赖，是图 Transformer/图重连的动机。 |
| graph rewiring | 图重连 | 为缓解过挤压而改动图的连接（加边、按曲率删边、加虚拟节点等），改善信息瓶颈而尽量不破坏原结构。 |
| virtual node | 虚拟节点 | 加一个与所有节点相连的"超级节点"，让任意两点经它两跳可达，廉价地提供全局信息通道，常用于图级任务与缓解过挤压。 |
| WL test (Weisfeiler-Lehman) | WL 同构测试 | 一种用迭代邻域哈希区分图的经典算法。GIN 证明消息传递 GNN 的表达力上界就是 1-WL——这框定了"哪些图 GNN 天生分不开"。 |
| GIN (Graph Isomorphism Network) | 图同构网络 | Xu 2019。用 sum 聚合 + MLP 使 GNN 达到 1-WL 表达力上界的模型，理论上是最具判别力的消息传递 GNN 之一。 |
| homophily / heterophily | 同配 / 异配 | 同配：相连节点常同类（如引文网），GCN 的隐含假设；异配：相连节点常异类（如欺诈网络），此时朴素聚合反而有害，需专门设计。 |
