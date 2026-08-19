# 参考清单 · References（实时检测器架构）

> 分主题列出。**★ = 必读**（读完这些你能覆盖本课 80% 的内容与绝大多数面试提问）。
> 每条注明**它解决了什么问题**，以及要重点看哪一节——论文很多，但每篇真正需要精读的通常只有 1–2 节。
>
> 与相邻课程的分工：**C18** 讲检测基础（IoU/NMS/mAP/FPN/两阶段）；**C54** 讲 DETR 的原理与收敛；
> **C56** 讲数据增强；**C57** 讲小目标；**C60** 讲 TensorRT 与训练-部署一致性；**C61** 讲实验设计与面试实务。
> **本课聚焦「延迟成为一等约束时，检测器的设计取舍」这一段。**

---

## 一 · YOLO 家族 · The YOLO Lineage

- ★ **Redmon et al. 2016, _You Only Look Once: Unified, Real-Time Object Detection_** —
  解决「检测必须两阶段」的路径依赖，把检测变成一次回归。**重点读 §2 的网格设计与 §4.1 的误差分析**：
  它自己就承认了定位误差远高于 Fast R-CNN，而这正是后续所有改进的起点。理解「每格只能出一个目标」这个结构性缺陷，
  你才明白 anchor 到底补的是什么。
- **Redmon & Farhadi 2017, _YOLO9000 / YOLOv2_** — 解决 v1 的召回问题：引入 anchor（且用 **k-means 在 wh 上聚类**而非手工设定）、
  高分辨率微调、passthrough 层。**k-means with IoU distance 这一节值得动手复现**（本课 notebook 里有）。
- ★ **Redmon & Farhadi 2018, _YOLOv3: An Incremental Improvement_** — 解决多尺度问题：三层 FPN 输出 + 多标签分类。
  **这篇只有 6 页且写得很随性，但它定下的三尺度输出结构一直用到今天**。读 §2.3（预测跨尺度的框）就够。
- ★ **Bochkovskiy et al. 2020, _YOLOv4: Optimal Speed and Accuracy of Object Detection_** —
  解决「有效的训练技巧散落各处」的问题。**它最大的价值是 §3 的 Bag-of-Freebies / Bag-of-Specials 分类法**：
  把改进分成「只增加训练成本」和「增加少量推理成本」两类。这个分类框架比论文里任何单个技巧都更有价值，
  也是本课 01「收益归因」一节的思想来源。
- **Jocher et al., _YOLOv5_（官方仓库与 release notes，无论文）** —
  解决工程可用性问题：自适应 anchor、自动 letterbox、导出链路、超参进化。
  **没有论文这件事本身就值得注意**——它说明这一代的贡献主要在工程整合而非算法。读仓库的 `models/yolo.py` 与 `utils/loss.py`。
- ★ **Ge et al. 2021, _YOLOX: Exceeding YOLO Series in 2021_** —
  解决「YOLO 系落后于 anchor-free 与先进分配」的问题。**必读 Table 2 的逐项消融**：
  解耦头 +1.1 AP、anchor-free +0.9 AP、**SimOTA +2.3 AP**。
  这张表是本课「收益归因」最有力的证据，也是面试里能立刻显出水平的引用。
- ★ **Li et al. 2022, _YOLOv6: A Single-Stage Object Detection Framework for Industrial Applications_** —
  解决「学术指标与工业部署脱节」的问题。重点读**重参数化主干（RepBackbone）**与**量化友好性**两节；
  它专门讨论了重参数化模型难以 PTQ 量化的问题及对策（RepOptimizer / 通道级蒸馏），这是别处少见的实战内容。
- ★ **Wang et al. 2023, _YOLOv7: Trainable Bag-of-Freebies Sets New State-of-the-Art_** —
  解决「怎么系统性地加训练期收益」。**必读 §3.2 的 planned re-parameterized convolution**（哪些位置能重参数化、
  为什么带 identity 的 RepConv 不能直接接在有残差的结构上）与 **§3.3 的 coarse-to-fine 辅助头**（主头与辅助头用不同粒度的标签分配）。
- **Jocher et al., _YOLOv8_（Ultralytics 文档与代码）** — 解决「统一多任务框架」：C2f 模块、**去掉 objectness 分支**、
  anchor-free + TaskAligned 分配 + DFL 回归。读 `ultralytics/utils/loss.py` 里的 `TaskAlignedAssigner` 是理解 TAL 最快的路径。
- **Wang et al. 2024, _YOLOv9: Learning What You Want to Learn Using Programmable Gradient Information_** —
  解决深层网络的信息瓶颈问题（PGI + GELAN）。理论论证较重，**实时工程上的增量小于 v10**，可略读。
- ★ **Wang et al. 2024, _YOLOv10: Real-Time End-to-End Object Detection_** —
  解决「YOLO 系仍然离不开 NMS」这个最后的痛点。**必读 §3.1 的 consistent dual assignments**：
  一对多头提供密集监督、一对一头用于推理，且两者的匹配度量必须**一致**（这个"一致"是全篇的关键）。
  §3.2 的效率-精度联合设计（轻量分类头、空间-通道解耦下采样、rank-guided block）也值得看。
- **Khanam & Hussain 2024 / Ultralytics, _YOLO11_ 与后续版本** — 增量迭代，**用来了解当前工程基线的位置**即可，
  不必深读；注意各版本的许可差异（AGPL-3.0 对商用有实质影响，见 C52）。

---

## 二 · Anchor-free 与单阶段基础 · Anchor-free Foundations

- ★ **Tian et al. 2019, _FCOS: Fully Convolutional One-Stage Object Detection_** —
  解决 anchor 带来的超参爆炸与匹配复杂度。**它定义的 (l,t,r,b) 回归 + centerness 是现代 anchor-free 头的模板**，
  RTMDet、YOLOX 的头都是它的后代。读 §3 即可。
- ★ **Lin et al. 2017, _Focal Loss for Dense Object Detection (RetinaNet)_** —
  解决单阶段检测器的前景-背景极度失衡。**Focal Loss 是「软性 OHEM」这个观点是面试好题**；
  同时 RetinaNet 是 ATSS 论文的基准，理解它才能理解 ATSS 的对照实验。
- **Zhou et al. 2019, _Objects as Points (CenterNet)_** — 另一条 anchor-free 路线：预测中心点热图 + 宽高，
  **天然无需 NMS**（用 3×3 maxpool 取局部极大值代替）。它是「无 NMS」这条线最早的实用尝试。
- **Lin et al. 2017, _Feature Pyramid Networks for Object Detection_** — 多尺度的基础设施。
  C18 已详讲，这里只需要它的**层级分配规则**作为后面讨论的前提。
- **Liu et al. 2018, _Path Aggregation Network (PANet)_** — 解决 FPN 只有自顶向下、低层定位信息传不上去的问题。
  **YOLOv4 之后所有 neck 的基础**。读 §3.1 的 bottom-up path augmentation。
- **Li et al. 2020, _Generalized Focal Loss (GFL/GFLv2)_** — 提出 **Distribution Focal Loss**：
  把框的每条边建模成离散分布而非标量。**YOLOv8 与 D-FINE 的回归表示都源自这里**，值得读 §3。

---

## 三 · 标签分配 · Label Assignment（本课的核心章节）

- ★ **Zhang et al. 2020, _ATSS: Bridging the Gap Between Anchor-based and Anchor-free Detection_** —
  **本课模块 02 最重要的一篇**。它证明了「anchor-based 与 anchor-free 的性能差距**全部**来自标签分配方式」，
  并给出一个无可学参数的自适应阈值（候选 IoU 的均值 + 标准差）。**§3 的对照实验设计本身就是实验方法论的范本**（C61 会再引用）。
- ★ **Ge et al. 2021, _OTA: Optimal Transport Assignment for Object Detection_** —
  解决「逐 GT 独立分配在密集重叠场景下会打架」的问题，把分配写成最优传输并用 Sinkhorn 求解。
  **重点看它对「全局视角」的论证**；算法本身因为慢而被 SimOTA 取代，但论证是核心。
- ★ **Feng et al. 2021, _TOOD: Task-aligned One-stage Object Detection_** —
  提出 **t = s^α · u^β** 的任务对齐度量，直接修「分类分高但框不准」的错配。
  **YOLOv8 / PP-YOLOE / RT-DETR 的分配都源自这里**，是当前事实标准之一。读 §3.2 的 TAL。
- ★ **Lyu et al. 2022, _RTMDet: An Empirical Study of Designing Real-Time Object Detectors_** —
  **本课模块 03 的主文献**。除了架构（CSPNeXt、5×5 depthwise 大核、共享头 + 独立 BN），
  它的 **dynamic soft label assignment**（代价的分类项用 IoU 作软目标）是分配这条线的重要一站。
  **§4 的逐项消融表非常完整**，是「怎么做一份可信的架构消融」的范本。
- **Kim & Lee 2020, _Probabilistic Anchor Assignment (PAA)_** — 用高斯混合模型把 anchor 的分数分布拟合成
  「正样本簇 + 负样本簇」，自动定阈值。思路优雅，**是理解「分配本质上是个聚类/分类问题」的好材料**。
- **Zhu et al. 2020, _AutoAssign: Differentiable Label Assignment_** — 把分配本身变成可微的、可学习的。
  代表了这条线的极端，实践中因训练不稳定用得少，但**用来界定「分配可以做到多自动」很有价值**。
- **Zhang et al. 2021, _VarifocalNet (VFNet)_** — IoU-aware 分类分数（varifocal loss）：
  让分类分直接回归 IoU。**RT-DETR 的 IoU-aware query selection 与它同源**，读这篇能把两条线接上。

---

## 四 · 结构与重参数化 · Architecture & Re-parameterization

- ★ **Ding et al. 2021, _RepVGG: Making VGG-style ConvNets Great Again_** —
  **重参数化的原型，本课模块 01 notebook 的直接依据**。核心是「训练结构与推理结构可以解耦」，
  且合并是**精确的代数恒等变换**（可 `assert np.allclose` 验证）。读 §3.2 的融合推导，务必自己推一遍。
- ★ **Wang et al. 2020, _CSPNet: A New Backbone that can Enhance Learning Capability of CNN_** —
  解决重复梯度信息导致的计算浪费。**注意它的收益里访存降低占很大比重，不只是 FLOPs**——
  这解释了为什么 CSP 在带宽受限的车端硬件上收益更明显。
- **Ding et al. 2022, _RepLKNet: Scaling Up Your Kernels to 31×31_** —
  解决「大核到底有没有用」的争论，给出**有效感受野（ERF）的可视化证据**。
  **本课模块 03 的 ERF 数值实验受它启发**；读 §3 的 ERF 分析。
- **Luo et al. 2016, _Understanding the Effective Receptive Field in Deep CNNs_** —
  ERF 概念的原始出处：证明 ERF 呈近高斯分布且**远小于理论感受野**（约为 √n 量级）。
  **这是「堆叠 3×3 不等价于一个大核」的理论依据**，一定要读。
- **Howard et al. 2017 / Sandler et al. 2018, _MobileNets v1/v2_** — depthwise separable conv 的出处。
  本课只需要它的**参数量与访存特性**：depthwise 是访存受限算子，FLOPs 降低不等比例转化为延迟降低。
- **Tan & Le 2019, _EfficientNet_ 与 Tan et al. 2020, _EfficientDet_** —
  复合缩放（depth/width/resolution 联合放大）的出处，以及 BiFPN。
  **RTMDet 的缩放策略是对它的实用化简化**；读 EfficientNet §3 的复合缩放公式即可。

---

## 五 · DETR 系与实时端到端 · DETR Family & Real-Time End-to-End

- ★ **Carion et al. 2020, _End-to-End Object Detection with Transformers (DETR)_** —
  **范式的起点**：集合预测 + 匈牙利匹配 + 无 NMS。本课只需要它的**结论与代价**（500 epoch、小目标弱），
  原理与收敛问题在 **C54** 详讲。读 §2–3。
- ★ **Zhu et al. 2021, _Deformable DETR_** —
  解决 DETR 收敛慢与小目标弱：可变形注意力（每个 query 只采样 K 个点）+ 多尺度 + 两阶段 query 初始化。
  **RT-DETR 的 decoder 直接建立在它之上**，所以这篇是读 RT-DETR 的前置。
- ★ **Zhao et al. 2024 (CVPR), _DETRs Beat YOLOs on Real-time Object Detection (RT-DETR)_** —
  **本课模块 04 的主文献**。三个必读点：
  ① **§4.1 对 NMS 的实测分析**——耗时随目标数与置信度阈值波动，这是全篇的动机；
  ② **§4.2 efficient hybrid encoder**（AIFI 只在 S5 + CCFF 用 CNN）及其 FLOPs 账；
  ③ **§4.3 IoU-aware query selection** 与 **decoder 层数可调**（同一份权重多档速度-精度，无需重训）。
  第三点在部署上的价值常被低估，**面试里主动提这一点会很加分**。
- ★ **Lv et al. 2024, _RT-DETRv2: Improved Baseline with Bag-of-Freebies_** —
  解决 v1 的**部署友好性**问题：离散采样算子替代 grid_sample（某些推理引擎支持不佳）、
  各尺度可配置的采样点数、以及一批零成本训练技巧。**上车前必读**。
- ★ **Peng et al. 2024, _D-FINE: Redefine Regression Task of DETRs as Fine-grained Distribution Refinement_** —
  沿用 RT-DETR 骨架，把框回归改成对边界分布的**迭代细化**（FDR），并配自蒸馏（GO-LSD）。
  当前实时端到端检测的强基线之一。读 §3。
- **Meng et al. 2021, _Conditional DETR_ / Liu et al. 2022, _DAB-DETR_** —
  把 query 显式解释为空间条件或 4D anchor box。**理解「query 与 anchor 的本质异同」的最佳材料**（高频面试题），
  详见 C54。
- **Li et al. 2022, _DN-DETR_ / Zhang et al. 2023, _DINO_** —
  去噪 query 与对比去噪，解决匹配不稳定导致的收敛慢。**DINO 是长期 SOTA 骨架**，C54 详讲。
- **Chen et al. 2023, _Group DETR_ / Jia et al. 2023, _H-DETR_ / Zong et al. 2023, _Co-DETR_** —
  训练时加一对多分支提供密集监督、推理时丢掉。
  **这三篇合起来证明了一个关键论点：一对一是推理需求，不是训练最优**——
  这正是 YOLOv10 一致双分配的思想来源，也是本课模块 02 的核心结论之一。

---

## 六 · 后处理、NMS 与其替代 · Post-processing

- **Bodla et al. 2017, _Soft-NMS_** — 解决密集遮挡下 NMS 误删真目标：按 IoU 衰减分数而非直接删除。
  **注意它增加保留框数**，下游负担与延迟都会上升。
- **He et al. 2019, _Bounding Box Regression with Uncertainty (Softer-NMS)_** — 让 NMS 感知定位不确定性。
  思路值得知道，实践中用得少。
- **Solovyev et al. 2021, _Weighted Boxes Fusion (WBF)_** — 多模型/多尺度结果融合时**加权合并**而非删除。
  TTA 与模型集成的正确做法（C56 详讲），车端因延迟代价通常不可用。
- **Rezatofighi et al. 2019, _Generalized IoU_ / Zheng et al. 2020, _Distance-IoU & CIoU_** —
  解决 IoU 在不相交时无梯度的问题。**做框回归损失时的默认选择**，两篇加起来读半小时。
- **Jiang et al. 2018, _IoU-Net_** — 最早提出「用预测的 IoU 来指导 NMS 排序」，
  **是 centerness → IoU 分支 → TaskAligned → IoU-aware query selection 这条完整脉络的源头**。

---

## 七 · 延迟、评测与部署 · Latency, Evaluation & Deployment

- ★ **Lin et al. 2014, _Microsoft COCO: Common Objects in Context_** — mAP / APs-APm-APl 的定义出处。
  **重点是理解 APs 的面积阈值（<32²）与它对 TSR 的含义**：绝大多数交通标志在 COCO 的口径下都属于「小目标」。
- ★ **NVIDIA _TensorRT Developer Guide_** — 本课模块 05 引用的延迟数字与优化机制的一手来源。
  重点看 **layer fusion**（什么阻止了融合）、**INT8 calibration**、以及 **engine 与硬件绑定**（换卡必须重建）。
  详细展开在 **C60**。
- ★ **`trtexec` 的官方文档与常用参数** — 实测延迟的标准工具。
  **必须知道的三件事**：要 warmup、要看 p99 而非均值、`--fp16`/`--int8` 与 `--shapes` 的组合会显著改变结论。
- ★ **Ultralytics 与 mmdetection/mmyolo 的官方 benchmark 表格** —
  **不是用来引用数字，而是用来看「他们是怎么测的」**：batch 多大、含不含 NMS、含不含预处理、什么卡什么版本。
  本课模块 05 的「论文 FPS 为什么不可比」一节就是照着这些表格的脚注写的。
- **Ma et al. 2018, _ShuffleNet V2: Practical Guidelines for Efficient CNN Architecture Design_** —
  **「FLOPs 不是延迟的好代理」这个论点最经典的出处**，给出了四条实用准则（等通道数最小化 MAC、
  谨慎用分组卷积、减少网络碎片化、减少逐元素操作）。**做实时检测器设计必读**。
- **Williams et al. 2009, _Roofline: An Insightful Visual Performance Model_** —
  计算受限 vs 访存受限的判定框架。理解为什么 depthwise 卷积「FLOPs 很低但没那么快」。
- **Dollár et al. 2021, _Fast and Accurate Model Scaling_** — 缩放策略的系统研究，
  指出**按 flops 等比缩放不是最优**，activation 才是与延迟更相关的量。RTMDet 的缩放决策可与之对照。

---

## 八 · 实现与工程资料 · Code & Engineering

- ★ **`open-mmlab/mmdetection` 与 `open-mmlab/mmyolo`** —
  **ATSS / SimOTA / TaskAligned / RTMDet 的参考实现都在这里**，且配置文件把每个超参都显式写了出来。
  读 `mmdet/models/task_modules/assigners/` 这一个目录，胜过读三篇分配论文的伪代码。
- ★ **`lyuwenyu/RT-DETR` 官方仓库** — RT-DETR / v2 的训练与导出链路。
  **重点看 ONNX 导出脚本与 TensorRT 转换说明**，那里能看到哪些算子是部署痛点。
- **`Megvii-BaseDetection/YOLOX`** — SimOTA 的原始实现，`yolox/models/yolo_head.py` 里的
  `get_assignments` 是本课 notebook 复现的对照物。**注意它的去冲突逻辑很容易被漏掉**。
- **`ultralytics/ultralytics`** — YOLOv8/v10/v11 的统一实现。
  `utils/loss.py` 与 `utils/tal.py` 是理解 TaskAligned + DFL 的最短路径。
  **⚠️ 许可是 AGPL-3.0，商用前务必确认**（见 C52 模块 05）。
- **`Peterande/D-FINE`** — D-FINE 官方实现，含与 RT-DETR 的对照配置。
- **各仓库的 `issues` 里关于「导出后精度对不上」「trt 比 pytorch 慢」的讨论** —
  **这些是最真实的工程知识来源**，比任何教程都接近实际。按关键词 `export`、`tensorrt`、`nms`、`fp16` 检索。
