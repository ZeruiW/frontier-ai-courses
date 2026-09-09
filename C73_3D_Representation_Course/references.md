# 参考资料 · 3D 表示与点云深度学习

> 分为「点云网络」「稀疏卷积」「3D 检测」「数据集与评测」「软件」五部分。
> **本课的所有数值结论都来自 notebook 里可复现的计算**，
> 外部文献用于机制与背景，不用于本课引用的具体数字。

---

## 一 · 点云网络

| 文献 | 年份 | 与本课的关系 |
|---|---|---|
| Qi et al., *PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation*, CVPR | 2017 | **模块 02 的全部内容**。定理 1（临界点集 $\le D$）在 notebook 里被验证到逐位相等；而本课额外量出「临界点数不随 $N$ 增长」（$N$ 涨 64 倍它从 16 到 24）。 |
| Qi et al., *PointNet++*, NeurIPS | 2017 | 模块 02 第 6 节。分层聚合补上的正是「分割头无法使用局部结构」这个数学上界。球查询 vs kNN 的选择理由（密度不均匀）与本课模块 01 的测量一致。 |
| Zaheer et al., *Deep Sets*, NeurIPS | 2017 | 反方向的定理：任何置换不变的连续函数都可以写成「逐点变换 + 对称聚合」。**所以那不是一种设计，是通用形式。** |
| Wang et al., *Dynamic Graph CNN (DGCNN)*, TOG | 2019 | 把分组做成动态图；与 C46 的图卷积同源。本课只指出同源，不重复机制。 |
| Zhao et al., *Point Transformer*, ICCV | 2021 | 注意力替代 max-pool；**它同样是对称的**，所以模块 02 第 1 节的恒等式仍然适用（而临界点集的结构会变）。 |

---

## 二 · 稀疏卷积

| 文献 | 年份 | 与本课的关系 |
|---|---|---|
| Graham, Engelcke &amp; van der Maaten, *3D Semantic Segmentation with Submanifold Sparse Convolutional Networks*, CVPR | 2018 | **模块 03 的核心**。本课把它的动机（避免膨胀）量成 52 倍的累计膨胀与 465× → 8.9× 的 FLOPs 落差，并把它的代价量成「标志碎成 2 个不连通分量」。 |
| Graham &amp; van der Maaten, *Submanifold Sparse Convolutional Networks* | 2017 | 更早的技术报告，规则表（rulebook）的概念来源。 |
| Choy, Gwak &amp; Savarese, *4D Spatio-Temporal ConvNets (MinkowskiNet)*, CVPR | 2019 | 广义稀疏卷积与 MinkowskiEngine；模块 03 第 6b 节提到的「按层自动选算法」。 |
| Yan, Mao &amp; Li, *SECOND: Sparsely Embedded Convolutional Detection*, Sensors | 2018 | 稀疏卷积用于 3D 检测的奠基工作；模块 04 的 direction classifier 也来自这里。 |
| Tang et al., *TorchSparse / SPVNAS*, ECCV | 2020 | 稀疏卷积的实现优化（gather-scatter vs implicit GEMM，模块 03 第 6b 节）。 |

---

## 三 · 3D 检测

| 文献 | 年份 | 与本课的关系 |
|---|---|---|
| Zhou &amp; Tuzel, *VoxelNet*, CVPR | 2018 | VFE（格内特征编码，模块 03 第 6 节）与 anchor-based 3D 检测头（模块 04 第 4 节）。 |
| Lang et al., *PointPillars*, CVPR | 2019 | **模块 01 第 4 节**。本课量出它快的真正原因：同分辨率下柱体的占用率是体素的 **49 倍**，于是可以用密集 2D 卷积。 |
| Zhou &amp; Krähenbühl, *Objects as Points (CenterNet)* | 2019 | 高斯半径公式（模块 04 第 5 节）；本课把它套到交通标志上，得到 0.08 格的退化结果。 |
| Yin, Zhou &amp; Krähenbühl, *Center-based 3D Object Detection and Tracking (CenterPoint)*, CVPR | 2021 | 模块 04 第 5–6 节。它消掉了「45° 目标 0 个正锚」这个问题，**但对薄目标同样退化**。 |
| Shi et al., *PV-RCNN*, CVPR | 2020 | 点-体素混合；两条路线的成本结构差异（模块 02 第 6b 节）在这里被显式地折中。 |
| Carion et al., *DETR*, ECCV | 2020 | 用匈牙利匹配替代锚框——第三条绕开「IoU 阈值定正样本」的路（详见 **C54**）。 |

---

## 四 · 数据集与评测

| 文献 / 资源 | 与本课的关系 |
|---|---|
| Geiger, Lenz &amp; Urtasun, *KITTI*, CVPR 2012 | IoU 阈值 0.7（车）/ 0.5（行人、骑车人）。**模块 04 第 3b 节与模块 05 第 4b 节给出这个区分的依据**：让每个类别的天花板保持在 0.9 以上。 |
| Caesar et al., *nuScenes*, CVPR 2020 | **中心距离匹配（0.5/1/2/4 m）与 TP 误差分解（ATE/ASE/AOE/AVE/AAE）**。模块 05 第 3–4 节说明为什么这个选择对薄目标是必需的而不是风格。 |
| Sun et al., *Waymo Open Dataset*, CVPR 2020 | 按距离分层的评测（0–30 / 30–50 / 50m+）——模块 05 第 7 节六个分层维度里的第一个。 |
| Behley et al., *SemanticKITTI*, ICCV 2019 | 点云语义分割的 mIoU 口径；模块 05 第 5 节量出它与频率加权的 250 倍差别。 |
| Kirillov et al., *Panoptic Segmentation*, CVPR 2019 | PQ = SQ × RQ 的分解（模块 05 第 6 节）；**而它的匹配判据仍是 IoU > 0.5**。 |
| Velodyne HDL-64E 数据手册 | 垂直 FOV（−24.9°..2.0°）与角分辨率（0.2°）——模块 01 环扫模型的参数来源。 |

---

## 五 · 软件

| 资源 | 与本课的关系 |
|---|---|
| spconv（traveller59） | 模块 03 胶囊。`SubMConv3d` vs `SparseConv3d` 就是本课两种稀疏卷积；`indice_key` 相同的层**复用规则表**——忘了传它就每层重算一次。 |
| MinkowskiEngine（NVIDIA） | 广义稀疏张量；按层自动选算法并缓存规则表。 |
| MMDetection3D | 模块 01/04 胶囊。`PointSample` 的 `sample_method`（`'random'` / `'fps'`）**偏倚相反**，train/test pipeline 里用了不同的值是一个真实的静默 bug。 |
| `mmcv.ops.ball_query` / `knn` | 模块 02 第 6 节。稀疏区凑不满 $K$ 个时会重复第一个点，**而 max-pool 恰好对重复免疫**——架构选择与工程妥协恰好兼容。 |
| `mmcv.ops.boxes_iou3d_gpu` / `nms3d` | 模块 04 胶囊。**3D NMS 的阈值普遍取 0.1–0.25 而不是 2D 的 0.5**——因为三个乘子让同一目标的两个候选框 IoU 天然更低。 |
| nuscenes-devkit | 模块 05 胶囊。`config_factory('detection_cvpr_2019').dist_ths` 就是中心距离的四档阈值。 |

---

## 五点五 · 本课刻意没有覆盖的方向，以及原因

| 方向 | 为什么不在本课 | 在哪里 |
|---|---|---|
| **NeRF 与神经渲染** | 用户在选课时跳过了它；而体渲染与 α 合成的地基放在下一门 | **C74** 模块 01 |
| **3D 高斯溅泼（3DGS）** | 它是连续表示 + 生成式任务，与本课的「离散表示 + 判别式任务」是两个方向 | **C74** |
| **SfM / MVS / 前馈重建** | 同上；而它们的几何前提在 C72 | **C75** |
| **3D 生成（SDS / 多视角扩散 / LRM）** | 生成式；而本课的评测口径讨论对它不适用（没有「真值框」） | **C75** |
| **点云配准（ICP / GICP）** | 需要一整套优化工具，而它在本课的任务里不是瓶颈 | 未覆盖 |
| **SLAM 的建图与回环** | 本课只用到「位姿」这一个概念，且只用它的输出 | 未覆盖（C72 同样只用输出） |
| **多帧 4D 检测（时序骨干）** | 需要真实序列与位姿；本课模块 01 只量了「多帧累积」这一个最简形式 | C55 模块 04（单相机时序） |
| **量化与部署** | 本课不训练，所以没有权重可量化 | C27（压缩）· C60（车端部署） |

> **把「决定不做什么」记录下来，与记录「做了什么」同等重要**——
> 因为「为什么没做」是最容易丢失、也最容易被重新踩的知识
> （这条纪律来自 C72 模块 05 第 9 节）。

---

## 六 · 本课程内的相关模块

| 模块 | 关系 |
|---|---|
| **C72**（本课的前提） | 投影、标定、位姿、BEV、时空对齐。**分界线是「有没有学习成分」。** C72 模块 04 的「均匀 BEV 网格必然一头过采样一头欠采样」在本课模块 01/03 以「体素分辨率」的形式再次出现。 |
| **C57** 小目标检测 | 2D IoU 的尺度敏感性。本课模块 05 把它推广到三个乘子，并指出「厚度」这一维在 2D 投影里根本不存在。 |
| **C58** 难例与长尾 | OHEM / focal loss 治的是模块 04 第 4 节那个「万分之四」的症状；而本课给出它的结构性来源。 |
| **C55** TSR 与自动驾驶感知 | C55 讲任务，本课讲工具。交界是模块 05：交通标志又小又薄，是 3D IoU 最不友好的一类目标。 |
| **C54** DETR 与集合预测 | 第三条绕开「IoU 阈值定正样本」的路（匈牙利匹配）。 |
| **C46** 图机器学习 | PointNet++ 的分组本质上是在建几何近邻图，然后做一轮 message passing。 |
| **C68** 模块 04 | 分层门禁。本课模块 05 第 7 节的六个分层维度是它在 3D 感知上的落地形式。 |
| **C10** 测量科学 | 「测量的分辨率必须优于要测的效应」——模块 05 第 3b 节的天花板判据就是这条原则。 |
| **C71** 模块 02 | 「无内容探针」与本课模块 02 第 2b 节的「线性探针」是同一个思路：用一次便宜的测量问「这个表示里有没有某个量」。 |
