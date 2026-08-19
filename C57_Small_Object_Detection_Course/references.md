# 参考清单 · References（小目标检测）

> 按主题分组。★ 为**必读**。每条都注明它**解决什么问题**、为什么值得读，以及本课的哪一节用到了它。
> 与相邻课程的分工：**C18** 讲检测基本盘；**C53** 讲实时检测器架构与标签分配总论；
> **C54** 讲 DETR 与集合预测；**C55** 讲 TSR 领域知识与安全评测；**C56** 讲检测数据增强。
> **本课只聚焦「目标很小时，检测流水线的每一环各自坏在哪、各自怎么修」这一条纵深。**

---

## 一 · 定义、基准与综述 · Definitions, Benchmarks & Surveys

- ★ **Lin et al. 2014, _Microsoft COCO: Common Objects in Context_ (ECCV)** —
  **解决的问题：给「小目标」一个可比较的操作性定义。** AP_S / AP_M / AP_L 的面积分桶（32² 与 96²）
  就出自这里，此后所有小目标论文的主指标都基于它。读的时候注意：这个阈值是**绝对像素面积**，
  与图像分辨率强耦合——这正是本课模块 00 讨论「绝对 vs 相对定义」的起点。
- ★ **Cheng et al. 2023, _Towards Large-Scale Small Object Detection: Survey and Benchmarks_ (TPAMI)** —
  **解决的问题：小目标检测这个领域到底有哪些流派、各自在解哪一条难因。**
  同时给出 SODA-D（驾驶场景）与 SODA-A（航拍）两个专为小目标设计的基准，
  把目标按面积细分到 `extremely small / relatively small / generally small` 三档。
  **如果只读一篇综述，读这篇**；SODA-D 与 TSR 场景最接近。
- ★ **Wang et al. 2020, _Tiny Object Detection in Aerial Images_ (ICPR) — AI-TOD** —
  **解决的问题：COCO 的 small 桶太粗，掩盖了 8 px 以下目标的真实难度。**
  AI-TOD 的目标平均只有约 12.8 px，是「tiny」这一档最常被引用的基准。
  读它的尺寸分布统计，你会立刻理解为什么 AP_S 是个被平均掉的指标。
- ★ **Yu et al. 2020, _Scale Match for Tiny Person Detection_ (WACV) — TinyPerson** —
  **解决的问题：预训练数据里几乎没有 10 px 的目标，直接迁移必然错配。**
  Scale Match 把源数据集的目标尺寸分布对齐到目标数据集再预训练——
  这是一个**极少被提及但非常实用**的修正，本课模块 02 会引用它的思路。
- **Zhu et al. 2021, _Detection and Tracking Meet Drones Challenge_ (TPAMI) — VisDrone** —
  **解决的问题：给「密集 + 小 + 视角多变」提供一个公认的战场。**
  几乎所有切片推理与聚类检测方法都在它上面报数，是读切片类论文时的公共坐标系。
- **Xia et al. 2018, _DOTA: A Large-scale Dataset for Object Detection in Aerial Images_ (CVPR)** —
  **解决的问题：小目标 + 任意朝向。** 引出了后面 GWD / KLD 这一支「用高斯建模框」的旋转框工作，
  与本课模块 03 的 NWD 同源。
- **Tong & Wu 2022, _Deep learning-based detection from the perspective of small or tiny objects: A survey_ (Image and Vision Computing)** —
  **解决的问题：方法的分类学。** 把方法归成「数据增强 / 多尺度 / 上下文 / 训练策略 / 超分」五类，
  与本课的分层组织方式可对照阅读，作为查漏补缺的目录用。

---

## 二 · 为什么难：尺度、感受野与混叠 · Why It Is Hard

- ★ **Luo et al. 2016, _Understanding the Effective Receptive Field in Deep Convolutional Neural Networks_ (NeurIPS)** —
  **解决的问题：戳破「理论感受野」这个幻觉。** 证明有效感受野只占理论感受野的一小部分、
  呈高斯衰减、且随深度只按 **O(√n)** 增长。**本课模块 01 与 02 的核心依据之一**，
  也是 RFLA 用高斯建模感受野的直接来源。**这篇必须读，而且要读它的实验图。**
- ★ **Singh & Davis 2018, _An Analysis of Scale Invariance in Object Detection – SNIP_ (CVPR)** —
  **解决的问题：多尺度训练到底为什么有效、又为什么常常无效。**
  核心洞察：让每个尺度的目标只在与预训练分布匹配的尺度上参与训练，
  而不是把所有尺度混着学。**「尺度不变性不是免费的」这个结论，是理解小目标的分水岭。**
- **Singh et al. 2018, _SNIPER: Efficient Multi-Scale Training_ (NeurIPS)** —
  **解决的问题：SNIP 太贵。** 只在目标周围采样 chips 训练，把多尺度训练的代价降下来。
  它的 chip 采样思路与模块 04 的切片训练是同一个东西的两个面孔。
- **Li et al. 2019, _Scale-Aware Trident Networks for Object Detection_ (ICCV)** —
  **解决的问题：不同尺度需要不同感受野，但又想共享参数。**
  用不同 dilation 的并行分支 + 权重共享实现「多感受野、单套参数」，是理解「尺度与感受野必须匹配」的好教材。
- **Zhang 2019, _Making Convolutional Networks Shift-Invariant Again_ (ICML)** —
  **解决的问题：stride-2 下采样引入的混叠。** BlurPool 几乎零参数，
  却直接对应本课模块 01 的第四条难因（下采样丢失）。小目标场景值得一试。
- **Hoiem et al. 2012, _Diagnosing Error in Object Detectors_ (ECCV)** 与
  **Bolya et al. 2020, _TIDE: A General Toolbox for Identifying Object Detection Errors_ (ECCV)** —
  **解决的问题：AP 掉了，到底是漏检、误检还是定位不准？**
  做小目标必须按误差类型拆解，否则会把「定位不准」当成「漏检」去治。TIDE 在 C61 详读，这里用它的分解框架。

---

## 三 · 多尺度架构 · Multi-Scale Architectures

- ★ **Lin et al. 2017, _Feature Pyramid Networks for Object Detection_ (CVPR)** —
  **解决的问题：低层有分辨率但没语义，高层有语义但没分辨率。**
  自顶向下 + 横向连接。**层级分配公式 k = ⌊k₀ + log₂(√(wh)/224)⌋ 就出自这篇（§4.2）**，
  本课模块 02 会把 TSR 的尺寸分布代进去看各层负载。必读，而且要读那个公式的上下文。
- ★ **Liu et al. 2018, _Path Aggregation Network for Instance Segmentation_ (CVPR) — PANet** —
  **解决的问题：低层的精确定位信息要穿过整个 backbone 才能到达高层，路径太长。**
  补一条自底向上的短路径。**「信息路径长度」这个视角比「多加一条连接」重要得多。**
- ★ **Tan et al. 2020, _EfficientDet: Scalable and Efficient Object Detection_ (CVPR) — BiFPN** —
  **解决的问题：① 融合时不同来源的贡献不等；② 分辨率/深度/宽度该怎么一起放大。**
  fast normalized fusion（每条边一个标量）+ 复合缩放。
  **复合缩放的结论对小目标特别重要：分辨率的边际收益通常高于深度**，这是模块 02 取舍那一节的依据。
- **Ghiasi et al. 2019, _NAS-FPN_ (CVPR)** —
  **解决的问题：金字塔的连接拓扑该长什么样？** 用搜索给出答案。
  实用价值有限，但它证明了「拓扑本身是可优化的设计维度」。
- **Liu et al. 2019, _Learning Spatial Fusion for Single-Shot Object Detection_ (ASFF)** —
  **解决的问题：融合权重应该逐像素不同。** 与 BiFPN 的标量权重形成粒度上的对照，
  在小目标密集的场景收益更明显。
- **Wang et al. 2020, _Deep High-Resolution Representation Learning for Visual Recognition_ (HRNet, TPAMI)** —
  **解决的问题：「先降后升」本身就是信息瓶颈。** 全程维持高分辨率分支并多分辨率互换。
  代价大，但它是「不要丢掉分辨率」这条路线走得最彻底的一个。
- **Wang et al. 2019, _CARAFE: Content-Aware ReAssembly of FEatures_ (ICCV)** —
  **解决的问题：FPN 里的最近邻上采样太粗糙。** 内容感知的重组核，
  是少数「换个上采样算子就能在小目标上稳定涨点」的改动。
- ★ **Zhu et al. 2021, _Deformable DETR_ (ICLR)** —
  **解决的问题：DETR 单尺度 + 全局 attention 对小目标极弱、收敛极慢。**
  多尺度可变形注意力用少量可学习采样点替代全图 attention。
  **本课模块 02 解释「为什么 Transformer 检测器能对小目标友好」时的一手来源**；DETR 家族本身在 C54 详读。
- **Liu et al. 2016, _SSD: Single Shot MultiBox Detector_ (ECCV)** —
  **解决的问题（以及它没解决的）：** 多尺度预测但**不融合**。
  拿它与 FPN 对读，就能明白「多尺度预测」和「多尺度融合」是两回事——这是模块 02 的经典对照组。

---

## 四 · 标签分配与度量 · Assignment & Metrics

- ★ **Zhang et al. 2020, _Bridging the Gap Between Anchor-based and Anchor-free Detection via Adaptive Training Sample Selection_ (ATSS, CVPR)** —
  **解决的问题：固定 IoU 阈值对不同尺度极不公平。**
  用候选 IoU 的「均值 + 标准差」给每个 GT 算专属阈值。
  **几乎零成本、几乎无超参，是小目标分配的第一优先级尝试项。** 注意：ATSS 动态的是阈值，不是 k。
- ★ **Wang et al. 2021, _A Normalized Gaussian Wasserstein Distance for Tiny Object Detection_ (arXiv 2110.13389)** —
  **解决的问题：IoU 对小框的位移极度敏感，且两框不相交时梯度恒为 0。**
  把框建成 2D 高斯、用二阶 Wasserstein 距离度量、再指数归一化。
  **本课模块 03 的核心文献**，公式简单到可以在白板上推完，面试极佳的谈资。
  注意归一化常数 C 需按数据集平均目标尺寸标定。
- ★ **Xu et al. 2022, _RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection_ (ECCV)** —
  **解决的问题：分配时用「框与框的重叠」本身就不对——特征点感知的是一个高斯衰减的感受野。**
  用 ERF 高斯与 GT 高斯的 KL 散度（RFD）做匹配，再用分层 top-k（HLA）保证每个 GT 都有正样本。
  **与 NWD 是不同环节，可以叠加**——这一点在面试里说清楚会显得很扎实。
- **Xu et al. 2022, _Detecting Tiny Objects in Aerial Images: A Normalized Wasserstein Distance and a New Benchmark_ (ISPRS Journal)** —
  NWD 的期刊扩展版，实验更完整（含 AI-TOD-v2）。想看消融细节读这篇。
- ★ **Tian et al. 2019, _FCOS: Fully Convolutional One-Stage Object Detection_ (ICCV)** —
  **解决的问题：anchor 的尺度先验对小目标是个负担。**
  center sampling + centerness + 按尺度分层回归。
  **center-based 分配对尺度天然公平**——这是模块 03「解法一」的原型。
- **Ge et al. 2021, _OTA: Optimal Transport Assignment for Object Detection_ (CVPR)** 与
  **Ge et al. 2021, _YOLOX_ (arXiv) 中的 SimOTA** —
  **解决的问题：分配应该是全局最优的分派，而不是逐 GT 的贪心。**
  dynamic-k 让难目标拿更多正样本。注意本课模块 03 指出的陷阱：
  小目标 IoU 普遍低 → 算出的 k 也小 → 反而更稀缺。
- **Feng et al. 2021, _TOOD: Task-aligned One-stage Object Detection_ (ICCV)** —
  **解决的问题：分类分高但定位差。** t = s^α · u^β 的对齐度量，
  对小目标尤其有用（小目标最容易出现「分类对了框歪了」）。
- ★ **Rezatofighi et al. 2019, _Generalized Intersection over Union_ (GIoU, CVPR)** —
  **解决的问题：两框不相交时 IoU 梯度为 0。** 必读，但也必须知道它的局限：
  一旦重叠就退化成 IoU，**尺度敏感性一点没解决**——这正是 NWD 存在的理由。
- ★ **Zheng et al. 2020, _Distance-IoU Loss: Faster and Better Learning for Bounding Box Regression_ (DIoU / CIoU, AAAI)** —
  **解决的问题：GIoU 收敛慢（只给方向不给距离）。** 加中心距项与长宽比项。
  同时给出 DIoU-NMS。**读它的收敛轨迹图**，能直观理解各项的作用。
- **Gevorgyan 2022, _SIoU Loss: More Powerful Learning for Bounding Box Regression_** —
  **解决的问题：回归轨迹「绕远路」。** 引入中心连线的角度代价，先对齐轴向再收敛。
- **Zhang et al. 2022, _Focal and Efficient IOU Loss for Accurate Bounding Box Regression_ (EIoU, Neurocomputing)** —
  **解决的问题：CIoU 的长宽比项是耦合量，梯度方向不直接。** 拆成宽、高独立惩罚 + Focal 加权。
  在小框上差异可测（宽高的量化误差在小框上被放大）。
- ★ **Lin et al. 2017, _Focal Loss for Dense Object Detection_ (RetinaNet, ICCV)** —
  **解决的问题：前景-背景极度不平衡。** 小目标场景负样本更多、正样本更难，
  (α, γ) 的最优点会偏离默认值。**注意本课强调的坑：γ 过大会把噪声标签当难样本重点学，
  而小目标的标注噪声恰恰最大。**
- **Yang et al. 2021, _Rethinking Rotated Object Detection with Gaussian Wasserstein Distance Loss_ (GWD, ICML)** 与
  **Yang et al. 2021, _Learning High-Precision Bounding Box for Rotated Object Detection via Kullback-Leibler Divergence_ (KLD, NeurIPS)** —
  **解决的问题：旋转框的角度周期性与 IoU 不可微。**
  与 NWD 同属「把框建成高斯」这一族。**读它们是为了理解这个建模范式的普适性**，
  而不是为了做旋转框——TSR 用水平框就够。

---

## 五 · 切片、高分辨率与级联 · Slicing, High Resolution & Cascades

- ★ **Akyon et al. 2022, _Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection_ (SAHI, ICIP)** —
  **解决的问题：不改模型、不重训，怎么大幅提升小目标召回。**
  切片推理 + 切片微调 + 跨片合并，且是**开箱即用的开源库**。
  **本课模块 04 的主文献**。读的时候特别注意两点：① 切片微调的贡献占比不小；
  ② 合并用的不是普通 NMS。
- ★ **Yang et al. 2022, _QueryDet: Cascaded Sparse Query for Accelerating High-Resolution Small Object Detection_ (CVPR)** —
  **解决的问题：想要 P2 的精度，但付不起 P2 的全图计算量。**
  低分辨率层预测粗位置 → 只在这些位置稀疏计算高分辨率层。
  **这是「两级级联」思路在单模型内部的实现**，与模块 04 的级联方案互为参照。
  注意工程上的保留意见：稀疏算子在部署后端未必快。
- **Yang et al. 2019, _Clustered Object Detection in Aerial Images_ (ClusDet, ICCV)** 与
  **Li et al. 2020, _Density Map Guided Object Detection in Aerial Images_ (DMNet, CVPRW)** —
  **解决的问题：均匀切片浪费算力（大部分切片是空的）。**
  先预测目标聚集区域 / 密度图，只在有目标的地方精检。
  **这就是 ROI 先验的通用版本**；TSR 里我们有更强的先验（消失点、车道、地图），所以可以做得更省。
- **Ünel et al. 2019, _The Power of Tiling for Small Object Detection_ (CVPRW)** —
  **解决的问题：切片这件事到底值不值。** 早期但很干净的实证，
  给出了切片大小与重叠率的实用取值范围，是模块 04 参数讨论的对照。
- **Gao et al. 2018, _Dynamic Zoom-in Network for Fast Object Detection in Large Images_ (CVPR)** 与
  **Najibi et al. 2019, _AutoFocus: Efficient Multi-Scale Inference_ (ICCV)** —
  **解决的问题：把「在哪里放大」变成一个可学习的决策。**
  AutoFocus 的 focus pixels 思路对「动态分辨率」这一节很有启发。
- **Ruan et al. / 各家 _GigaDet_ 类工作（十亿像素级检测）** —
  **解决的问题：当图像大到 100 MP 时，切片的组合爆炸怎么办。**
  作为极端案例读，能把模块 04 的代价模型推到边界。

---

## 六 · 数据侧的小目标解法 · Data-Side Remedies（与 C56 衔接）

- ★ **Kisantal et al. 2019, _Augmentation for Small Object Detection_** —
  **解决的问题：小目标实例太少，且每个实例贡献的正样本也少。**
  提出对小目标做过采样与**复制粘贴**，是「copy-paste 治小目标」最早的系统性实证。
  **它同时给出了小目标在 COCO 中的占比统计，是很好的动机材料。**
- **Chen et al. 2020, _Stitcher: Feedback-driven Data Provider for Object Detection_** —
  **解决的问题：如何按训练反馈动态制造小目标。**
  监控小目标的 loss 占比，不够就把图缩小拼接。比固定概率的 Mosaic 更有针对性。
- **Ghiasi et al. 2021, _Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation_ (CVPR)** —
  **解决的问题：copy-paste 到底要多复杂。** 结论是简单粘贴就很强。
  **注意 TSR 的额外约束**：尺度必须符合透视、位置必须合法，否则模型会学到贴图伪影这个捷径（详见 C56）。
- **Bochkovskiy et al. 2020, _YOLOv4_（Mosaic 部分）** —
  **解决的问题：一次前向见到更多样的上下文与更多小目标。**
  Mosaic 是工业界默认；也要知道 close-mosaic（训练末期关闭）为什么是标配。

---

## 七 · TSR 与自动驾驶落地 · TSR & Deployment（与 C55 / C60 衔接）

- ★ **Zhu et al. 2016, _Traffic-Sign Detection and Classification in the Wild_ (TT100K, CVPR)** —
  **解决的问题：给中国路况下的 TSR 一个真实的、小目标为主的基准。**
  10 万张全景图、3 万个标志实例，**绝大多数标志只占图像面积的极小比例**，长尾也极严重。
  **本课模块 05 讨论「TSR 的尺寸分布」时的一手数据来源**，也是回答「你在什么数据上验证过小目标方法」的标准答案。
- **Houben et al. 2013, _Detection of Traffic Signs in Real-World Images_ (GTSDB, IJCNN)** 与
  **Stallkamp et al. 2012, _Man vs. computer: Benchmarking machine learning algorithms for traffic sign recognition_ (GTSRB, Neural Networks)** —
  **解决的问题：TSR 的检测与分类两个子任务各自的经典基准。**
  规模小、场景单一，今天主要作为历史参照与快速原型验证用。
- **Ertler et al. 2020, _The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale_ (ECCV)** —
  **解决的问题：跨国家、跨地区的标志体系差异与域偏移。**
  它的目标尺寸分布同样以小目标为主，且提供了「同一形状在不同国家含义不同」的真实样本。
- ★ **Hartley & Zisserman, _Multiple View Geometry in Computer Vision_（第 6 章，相机模型）** —
  **解决的问题：把像素与物理量严格地联系起来。**
  本课模块 05 的 px = f·S/Z 与 f = (W/2)/tan(FOV/2) 都是它的直接推论。
  **只需要读第 6 章的前几节**，但读过之后你在系统设计题里的回答会立刻不一样。
- **Szeliski, _Computer Vision: Algorithms and Applications_（第 2 章「Image formation」）** —
  **解决的问题：除了几何，成像链路上还有什么在限制「看多远」。**
  MTF、镜头衍射极限、传感器噪声、ISP——**这些是「提高分辨率就能看更远」这个直觉的现实边界**。
- **Caesar et al. 2020, _nuScenes_ (CVPR)** 与 **Yu et al. 2020, _BDD100K_ (CVPR)** —
  **解决的问题：给多传感器、多天气、多时段的驾驶场景提供公共基准。**
  本课主要用它们的**尺寸与距离分布统计**，作为分桶评测设计的参考。
- **NVIDIA _TensorRT Developer Guide_（Dynamic Shapes 与 Layer Fusion 两节）** —
  **解决的问题：模块 02–04 里算出来的分辨率 / P2 / 切片决策，最后能不能塞进车端预算。**
  高分辨率输入与多档动态分辨率会直接影响 optimization profile 与显存峰值。部署侧的完整讨论在 **C60**。
