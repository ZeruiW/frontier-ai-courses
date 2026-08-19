# 参考清单 · References（端到端集合预测检测 · DETR 家族）

> 每条注明**它解决了什么问题**、为什么值得读。先读 ★ 标记的必读。
> DETR 家族论文极多，但真正引入新机制的只有十来篇——本清单按"机制"而不是按时间组织，
> 读完 ★ 的那些，剩下的论文你基本能自己推出来它在改哪一块。
>
> 与相邻课程的分工：**C18** 讲经典检测（IoU / NMS / anchor / Faster R-CNN / FPN，本课的前置）；
> **C53** 讲实时检测器架构与标签分配（YOLO 演进 / RTMDet / RT-DETR 的实时侧）；
> **C57** 讲小目标检测（把本课模块 05 留下的问题彻底量化）；
> **C55** 讲 TSR 领域知识与安全导向评测；**C60** 讲车端部署。

## 集合预测与端到端范式 · The Paradigm

- ★ **Carion et al. 2020, _End-to-End Object Detection with Transformers_ (DETR, ECCV 2020)**
  —— **本课的一手来源，从头到尾都要读，包括附录**。它解决的问题是：检测长期依赖 anchor 与 NMS
  这两个不可微、需手工调参的组件。读法建议：先读 §3（匈牙利匹配 + 集合损失，只有两页但是全课地基），
  再读 §4.2 的**消融表**（辅助损失去掉掉多少、GIoU/L1 各去掉掉多少、decoder self-attention 去掉重复框有多少），
  最后读附录里 query 空间特化的可视化——那张图是回答"query 是什么"最有力的证据。
- ★ **Zhu et al. 2021, _Deformable DETR: Deformable Transformers for End-to-End Object Detection_ (ICLR 2021)**
  —— 解决 DETR 的两个致命问题：收敛要 500 epoch、小目标差。核心是可变形注意力
  （每个 query 只采 K 个可学采样点，**注意力权重直接由 query 回归、不走 Q·K 点积**）
  与多尺度。**读 §3.1 的复杂度分析**，它解释了为什么原始 DETR 用不了多尺度特征。
  两阶段与迭代精修也出自这里。
- ★ **Wang et al. 2021, _End-to-End Object Detection with Fully Convolutional Networks_ (DeFCN, CVPR 2021)**
  —— **证明"端到端不需要 Transformer"的关键论文**：纯 FCN + 一对一分配（POTO）+ 3D Max Filtering
  同样可以无 NMS。读它是为了把"集合预测"从"Transformer"里剥离出来——
  这是本课反复强调的分界线，也是面试里区分"读过论文"和"跟过热点"的地方。
- **Sun et al. 2021, _OneNet: Towards End-to-End One-Stage Object Detection_**
  —— 指出一对一分配里**分类代价必不可少**（只用位置代价做一对一会失败）。
  与 DeFCN 互为补充，一起构成"一对一分配到底需要什么"的答案。
- **Sun et al. 2021, _Sparse R-CNN: End-to-End Object Detection with Learnable Proposals_ (CVPR 2021)**
  —— 用一组可学习 proposal + 一对一匹配做端到端，但完全不用注意力做全局交互。
  读它能看清"可学习 query"这个想法可以有多少种实现形态。
- **Chen et al. 2022, _Pix2Seq: A Language Modeling Framework for Object Detection_ (ICLR 2022)**
  —— 把检测变成序列生成（框坐标离散化成 token 自回归输出）。它给出了集合预测的第三条路，
  也解释了为什么"顺序"在检测里是个人为强加的东西。与 C59 的 VLA 有直接思想联系。
- **Wang et al. 2024, _YOLOv10: Real-Time End-to-End Object Detection_**
  —— 一致双分配（consistent dual assignments）：训练时一对多头与一对一头共存且监督一致，
  推理只用一对一头。**这是"一对一是推理需求"这一结论在 YOLO 系的落地**，C53 有详讲。

## 匹配算法 · Matching

- ★ **Kuhn 1955, _The Hungarian Method for the Assignment Problem_ (Naval Research Logistics Quarterly)**
  —— 匈牙利算法的原始文献，也是 "Hungarian" 这个名字的来历（Kuhn 致敬了 Kőnig 与 Egerváry 的工作）。
  解决的问题：n×n 指派问题的多项式时间求解。**值得真的读一遍**——十几页，
  顶标（对偶变量）与相等子图的思想比任何二手教程都清楚。
- ★ **Munkres 1957, _Algorithms for the Assignment and Transportation Problems_ (SIAM J.)**
  —— 给出严格的 O(n³) 实现与复杂度证明，这也是 "Kuhn–Munkres / KM 算法"这个叫法的来源。
  模块 01 的练习实现就照这篇的流程走。
- **Jonker & Volgenant 1987, _A Shortest Augmenting Path Algorithm for Dense and Sparse Linear Assignment Problems_**
  —— `scipy.optimize.linear_sum_assignment` 实际用的算法。常数因子小很多。
  读它是为了知道"库里那个函数到底在做什么"，以及为什么练习里禁止直接调它。
- **Kőnig 1931 / Egerváry 1931（二分图匹配的经典结果）**
  —— Kőnig 定理（最大匹配 = 最小顶点覆盖）是匈牙利算法正确性的组合基础。
  只需要知道结论，但知道它能让"为什么增广路径找不到了就说明已最优"变得显然。
- **Cuturi 2013, _Sinkhorn Distances: Lightspeed Computation of Optimal Transport_**
  —— 指派问题的软化版本。**读它是为了理解 OTA / SimOTA 那条支线**（一个 GT 匹配 k 个预测，
  就从指派问题变成了最优传输问题）；C53 模块 02 详讲。
- **Ge et al. 2021, _OTA: Optimal Transport Assignment for Object Detection_ (CVPR 2021)**
  —— 把标签分配显式建模成最优传输。与本课的一对一匹配是同一数学家族的两端：
  一端要求严格一对一，一端允许可变的一对多。

## 框回归损失 · Box Losses

- ★ **Rezatofighi et al. 2019, _Generalized Intersection over Union: A Metric and A Loss for Bounding Box Regression_ (CVPR 2019)**
  —— GIoU 的原始文献。解决的问题：**IoU 在两框不相交时恒为 0、梯度也为 0**，
  而训练早期不相交是常态。读 §3 的定义与 §4 的梯度分析即可。DETR 的匹配代价与损失都用它。
- ★ **Zheng et al. 2020, _Distance-IoU Loss: Faster and Better Learning for Bounding Box Regression_ (AAAI 2020)**
  —— DIoU 与 CIoU 一次给全。**关键洞察**：GIoU 在"一框包含另一框"时退化成 IoU，
  只能靠慢慢扩大闭包框间接对齐；DIoU 直接惩罚中心距离，收敛快得多。CIoU 再加长宽比项。
  这篇也是 DIoU-NMS 的出处。
- **Zhang et al. 2022, _Focal-EIoU: Focal and Efficient IOU Loss for Accurate Bounding Box Regression_**
  —— EIoU 把 CIoU 的长宽比项拆成宽和高各自的惩罚，避免了 CIoU 在小框上的梯度不稳。
  **小目标 / TSR 场景值得试**，C57 会再提。
- **Lin et al. 2017, _Focal Loss for Dense Object Detection_ (RetinaNet, ICCV 2017)**
  —— Deformable DETR 之后集合损失的分类项普遍换成 focal loss。
  在 DETR 语境里它同时接管了 `eos_coef` 的职责，所以两者不该叠加。C18/C53 有更详细的讨论。
- **Li et al. 2020, _Generalized Focal Loss_ (GFL/GFLv2)**
  —— 分类-定位质量联合表示 + 框的分布式表示。**读它是为了理解 RT-DETR 的 IoU-aware
  query selection 和 D-FINE 的细粒度分布优化在做什么**。

## 收敛加速：注意力这条线 · Faster Convergence (Attention)

- ★ **Meng et al. 2021, _Conditional DETR for Fast Training Convergence_ (ICCV 2021)**
  —— **第一篇把"收敛慢"的根因明确定位到 cross-attention 的论文**：
  内容与位置耦合在一起，逼着注意力同时干两件事。解法是生成条件空间 query，6.7–10× 加速。
  读 §3 的注意力分解推导，它是理解 DAB 的前置。
- ★ **Liu et al. 2022, _DAB-DETR: Dynamic Anchor Boxes are Better Queries for DETR_ (ICLR 2022)**
  —— **回答"query 到底是什么"最彻底的一篇**：query 就是 4D anchor box，
  且用 w/h 调制注意力的空间范围（大目标看得宽、小目标看得窄），逐层更新。
  面试被问 "query 和 anchor 有什么区别" 时，这篇是标准答案的来源。
- **Wang et al. 2022, _Anchor DETR: Query Design for Transformer-Based Detector_ (AAAI 2022)**
  —— query = 2D anchor point + 多 pattern（解决同一位置多目标）。
  与 DAB 是同一时期的两种参数化，对比读收获最大。
- **Gao et al. 2021, _Fast Convergence of DETR with Spatially Modulated Co-Attention_ (SMCA)**
  —— 用高斯权重图直接给 cross-attention 加空间先验。思路最简单直接，
  适合作为"给注意力加先验"这类方法的最小示例。
- **Roh et al. 2022, _Sparse DETR: Efficient End-to-End Object Detection with Learnable Sparsity_ (ICLR 2022)**
  —— 只更新 encoder token 的一个子集。解决的问题是 encoder 计算量，
  **在车端算力受限时这条支线仍然有用**。
- **Yao et al. 2021, _Efficient DETR: Improving End-to-End Object Detector with Dense Prior_**
  —— 用密集先验初始化 query，从而把 decoder 从 6 层减到 1 层。
  是"两阶段 query 初始化"这个想法的早期形态。
- ★ **Vaswani et al. 2017, _Attention Is All You Need_**
  —— Transformer 原文。本课只需要 §3.2（多头注意力）与位置编码那部分，
  但模块 03 的 notebook 会从零实现它们，读一遍原始定义能避免很多细节偏差。
- **Dai et al. 2017, _Deformable Convolutional Networks_ / Zhu et al. 2019, _DCNv2_**
  —— 可变形注意力的思想源头（可学习采样偏移 + 双线性插值取值）。
  读它能理解"为什么梯度可以回传到坐标上"这件事最初是怎么被做出来的。

## 收敛加速：监督这条线 · Faster Convergence (Supervision)

- ★ **Li et al. 2022, _DN-DETR: Accelerate DETR Training by Introducing Query DeNoising_ (CVPR 2022)**
  —— **把"匹配不稳定"这个根因量化并解决的论文**。它先用"匹配翻转率"证明不稳定确实存在，
  再用带噪 GT 作为额外 query 绕过匹配。读 §3 的噪声构造与 **attention mask 设计**——
  后者是防信息泄漏的硬条件，实现时最容易写错。
- ★ **Zhang et al. 2023, _DINO: DETR with Improved DeNoising Anchor Boxes for End-to-End Object Detection_ (ICLR 2023)**
  —— 三件套：**对比去噪（CDN）**、**mixed query selection**、**look forward twice**。
  每一件都值得单独理解它解决什么：CDN 给出"多远该放弃"的决策边界；
  mixed query selection 说明不是所有先验都值得注入（内容部分用 encoder 特征反而更差）；
  look forward twice 改的是 detach 与否而不是损失项。**注意与自监督的 DINO 完全无关。**
- ★ **Chen et al. 2023, _Group DETR: Fast DETR Training with Group-Wise One-to-Many Assignment_ (ICCV 2023)**
  —— K 组 query 各自做一对一，等价于一对多但保留无 NMS。
  它与下面两篇一起构成本课最重要的结论：**一对一是推理的需求，不是训练的最优**。
- ★ **Jia et al. 2023, _DETRs with Hybrid Matching_ (H-DETR, CVPR 2023)**
  —— 一对一分支 + 一对多分支联合训练，推理只用前者。最直白地把这个结论摆出来。
- ★ **Zong et al. 2023, _DETRs with Collaborative Hybrid Assignments Training_ (Co-DETR, ICCV 2023)**
  —— 进一步定位到"**encoder 因正样本太少而训练不充分**"，用并联的传统一对多头喂饱它。
  一度是 COCO 榜首。这篇的价值在于它演示了"把稀疏监督的伤害定位到具体部件"的分析方法。
- **Ouyang-Zhang et al. 2022, _NMS Strikes Back_ (DETA)**
  —— 反方向证据：把一对一换回 IoU 阈值一对多 + NMS，收敛极快且精度不掉。
  **读它是为了不把"端到端"当信仰**——端到端的收益在部署侧，训练侧是净成本。
- **Liu et al. 2023, _Detection Transformer with Stable Matching_ (Stable-DINO)**
  —— 用位置度量参与分类损失来稳住匹配。对"匹配不稳定"这条线的进一步收敛。
- **Zhang et al. 2023, _Dense Distinct Query for End-to-End Object Detection_ (DDQ, CVPR 2023)**
  —— 指出 query 既要"密"（覆盖率）又要"互不重复"（去重），并给出显式的 query 去重设计。

## 实时与部署 · Real-Time & Deployment

- ★ **Zhao et al. 2024, _DETRs Beat YOLOs on Real-time Object Detection_ (RT-DETR, CVPR 2024)**
  —— 首个在实时区间打赢 YOLO 的 DETR。两个设计要点：
  **efficient hybrid encoder**（只在最高层做 self-attention，跨尺度融合用 CNN）与
  **IoU-aware query selection**（按分类分数选会挑到定位差的）。
  外加一个部署上的大杀器：**decoder 层数可调，一份权重支持多档速度-精度而无需重训**。
  C53 模块 04 从延迟预算的角度再讲一遍，两边对照读。
- **Lv et al. 2024, _RT-DETRv2_ / Peng et al. 2024, _D-FINE_ / Chen et al. 2024, _LW-DETR_**
  —— RT-DETR 之后的三条延续：离散采样与灵活缩放 / 细粒度分布优化 /
  纯 ViT 的轻量实时 DETR。选型时值得各扫一眼 benchmark 表。
- **Zheng et al. 2023, _Less is More: Focus Attention for Efficient DETR_ (Focus-DETR)**
  —— 前景 token 打分 + 稀疏化，兼顾精度与效率。车端算力紧时的候选方案。
- **facebookresearch/detr（官方代码库）**
  —— ★ **`models/matcher.py` 与 `models/detr.py` 的 `SetCriterion` 这两个文件必须逐行读**，
  加起来不到 300 行，本课模块 01–02 的全部内容都在里面。
  特别注意 matcher 里分类项用的是 `-out_prob[:, tgt_ids]`（概率）而不是 log 概率。
- **IDEA-Research/detrex 与 IDEA-Research/DINO（代码库）**
  —— DETR 家族最全的统一复现（DAB / DN / DINO / Group / H-DETR 都有）。
  **要看 DN 的 attention mask 怎么写、去噪组怎么分，直接读这里最快。**
- **open-mmlab/mmdetection（代码库）**
  —— Deformable DETR / DINO / RT-DETR 的配置文件是查超参的最快途径
  （学习率分组、num_queries、去噪组数、损失权重都在配置里一目了然）。

## 相关扩展 · Beyond Detection

- **Cheng et al. 2022, _Masked-attention Mask Transformer for Universal Image Segmentation_ (Mask2Former)**
  —— 集合预测在分割上的形态：query = 一个 mask。读它能看到"一对一匹配 + 集合损失"
  这套东西的通用性远超检测。
- **Li et al. 2023, _Mask DINO_** —— DINO 的检测+分割统一版本，说明这套骨架可以直接扩展。
- **Liu et al. 2024, _Grounding DINO: Marrying DINO with Grounded Pre-Training for Open-Set Object Detection_ (ECCV 2024)**
  —— 开放词表检测的代表作。对 TSR 长尾类别的价值目前主要在**数据挖掘与自动预标注**（C58），
  而不是直接上车。
- **Wang et al. 2022, _DETR3D_ / Liu et al. 2022, _PETR_**
  —— 把 object query 搬到 3D / BEV 空间（query 直接在 3D 里定义并投影回多相机图像取特征）。
  **这是自动驾驶感知的主流范式**，也是本课内容在量产系统里的真正落点；C55 会再接上。
- **Zhang et al. 2021, _Deep Sets_ / Lee et al. 2019, _Set Transformer_**
  —— 集合上的置换不变函数该怎么构造。想把"为什么必须匹配"这件事从第一性原理讲清楚时，
  这两篇是理论背景。
