# 参考清单 · References（计算机视觉）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 从零实现的每个机制（卷积、Sobel/Canny、HOG、IoU/NMS/mAP、Dice/mIoU、InfoNCE/MAE），都能在下列文献里找到它的原始动机与在真实系统中的完整形态。


## 低层视觉：滤波与边缘 · Filtering & Edges

- ★ **Canny 1986, _A Computational Approach to Edge Detection_** — 边缘检测的奠基论文。把「好的边缘检测」形式化为检测率、定位精度、单一响应三个准则，推导出最优滤波并给出经典五步流程（高斯平滑→梯度→非极大抑制→双阈值→滞后连接）。本课模块 01 全程复现它，至今是边缘基线。
- **Sobel & Feldman 1968, _An Isotropic 3×3 Image Gradient Operator_** — Sobel 算子的出处。在求梯度的同时做一点平滑，比朴素差分抗噪，是离散图像梯度最常用的核。模块 01 的梯度估计直接用它。
- **Marr & Hildreth 1980, _Theory of Edge Detection_** — 用高斯拉普拉斯（LoG）与过零点检测边缘，把边缘与人类视觉的尺度联系起来。理解「为什么求边缘前要先平滑」的理论背景。
- **Serra 1982, _Image Analysis and Mathematical Morphology_** — 数学形态学奠基著作。腐蚀/膨胀/开闭运算的集合论框架，是清理二值掩码、连接断边、去噪点的标准工具。模块 01/04 用到。

## 手工特征与经典识别 · Hand-crafted Features

- ★ **Dalal & Triggs 2005, _Histograms of Oriented Gradients for Human Detection_** — HOG 特征的原始论文。提出分 cell 统计梯度方向直方图 + block 对比度归一化，配 SVM 做行人检测，是深度学习前最有影响力的特征之一。模块 02 从零实现一个 HOG-ish 描述子并用它分类。
- ★ **Lowe 2004, _Distinctive Image Features from Scale-Invariant Keypoints (SIFT)_** — 尺度/旋转不变的局部特征，长期是图像匹配、拼接、三维重建的黄金标准。理解「不变性」如何被工程化地设计进描述子。
- **Viola & Jones 2001, _Rapid Object Detection using a Boosted Cascade of Simple Features_** — 实时人脸检测的里程碑。Haar 特征 + 积分图 + AdaBoost 级联，是「滑窗 + 强分类器」检测范式的经典，模块 03 滑窗思想的前身。
- **Csurka et al. 2004, _Visual Categorization with Bags of Keypoints_** — 视觉词袋（BoVW）表示，把局部描述子聚类成词、用词频表示图像，是深度学习前的主流图像分类管线。

## 深度分类与骨干网络 · Deep Classification & Backbones

- ★ **Krizhevsky, Sutskever & Hinton 2012, _ImageNet Classification with Deep CNNs (AlexNet)_** — 引爆深度学习的论文。在 ImageNet 上以巨大优势夺冠，确立了「大数据 + GPU + 深 CNN + ReLU + dropout + 数据增强」的范式。本课分类/增强/评估的工程直觉源出于此。
- ★ **He et al. 2016, _Deep Residual Learning for Image Recognition (ResNet)_** — 残差连接让网络可训到上百层，几乎是所有现代视觉骨干（含检测/分割的 backbone）的基础。与 C15(CNN 架构) 衔接的核心论文。
- **Simonyan & Zisserman 2014, _Very Deep Convolutional Networks (VGG)_** — 用堆叠 3×3 小核构建深网络，证明深度的价值并给出极简洁的设计，至今是特征提取与教学的常用骨干。
- **Dosovitskiy et al. 2021, _An Image is Worth 16x16 Words (ViT)_** — 把图像切块当 token 喂给 Transformer，在大数据上超越 CNN，是当下视觉骨干与多模态（VLM 视觉编码器）的主流。MAE(模块 05) 即建立在 ViT 上。

## 目标检测 · Object Detection

- ★ **Girshick et al. 2014, _Rich Feature Hierarchies (R-CNN)_** — 把 CNN 引入检测的开山作。用 selective search 出候选区域、各自过 CNN 提特征再分类/回归框，确立「proposal + 分类」范式。理解现代检测器为何这样设计的起点。
- ★ **Girshick 2015, _Fast R-CNN_** — 用 RoI pooling 让整图只过一次 CNN、共享特征，把 R-CNN 的逐区域重复计算去掉，速度与精度同时大涨。理解检测器工程优化的关键一步。
- ★ **Ren et al. 2015, _Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks_** — 用 RPN（基于 anchor 的轻量网络）端到端生成候选，取代 selective search，使检测真正实时。模块 03 的 anchor 思想的权威来源。
- ★ **Redmon et al. 2016, _You Only Look Once (YOLO): Unified, Real-Time Object Detection_** — 把检测重构为单次回归（网格直接预测框+类），开创一阶段检测器，极快且实用。理解 anchor / 网格 / NMS 后处理的经典案例。
- **Liu et al. 2016, _SSD: Single Shot MultiBox Detector_** — 多尺度特征图上密集预测，与 YOLO 并列的一阶段检测器代表，强化了多尺度 anchor 的思想。
- **Lin et al. 2017, _Focal Loss for Dense Object Detection (RetinaNet)_** — 指出一阶段检测器精度落后是因正负样本极端不平衡，提出 focal loss 降低易分负样本权重。检测里类不平衡处理的范本，也启发分割。
- **Everingham et al., _The PASCAL Visual Object Classes (VOC) Challenge_** — 定义了检测的 mAP 评测协议（IoU≥0.5 判命中、PR 曲线下面积、各类平均）。模块 03 的 mAP 实现严格对照它的口径。

## 语义与实例分割 · Segmentation

- ★ **Long, Shelhamer & Darrell 2015, _Fully Convolutional Networks for Semantic Segmentation (FCN)_** — 把分类网络的全连接层换成卷积，实现任意尺寸输入的逐像素预测，是深度语义分割的开山作。模块 04 编解码思想的起点。
- ★ **Ronneberger, Fischer & Brox 2015, _U-Net: Convolutional Networks for Biomedical Image Segmentation_** — 对称编解码 + 跳连融合高分辨率细节，在极少标注下取得优异分割，是医学影像与一切稠密预测的奠基结构。模块 04 的 U-Net 思想直接来自它。
- **Chen et al. 2017, _DeepLab: Semantic Segmentation with Atrous Convolution and CRFs_** — 用空洞卷积扩大感受野而不损分辨率、用 CRF 精修边界，是语义分割长期的强基线。
- **He et al. 2017, _Mask R-CNN_** — 在 Faster R-CNN 上加一条掩码分支，统一了检测与实例分割，是实例分割的标准方法。理解「检测 + 逐实例掩码」如何结合。
- **Milletari et al. 2016, _V-Net (Dice Loss)_** — 提出直接优化 Dice 系数作为损失，正面解决分割中前景小、类不平衡的问题。模块 04 的 Dice 指标与类不平衡讨论的依据。

## 自监督表示学习 · Self-supervised Learning

- ★ **Chen et al. 2020, _A Simple Framework for Contrastive Learning (SimCLR)_** — 对比学习的集大成者。证明强数据增强 + 投影头 + 大批量 NT-Xent 损失即可让无监督表示逼近监督预训练，无需特殊结构或记忆库。模块 05 的 InfoNCE 实现与增强设计直接复现它。
- **He et al. 2020, _Momentum Contrast (MoCo)_** — 用动量编码器 + 队列维护大量负样本，让对比学习不依赖超大批量。理解对比学习里「负样本从哪来」的另一条工程路线。
- **Oord et al. 2018, _Representation Learning with Contrastive Predictive Coding (CPC)_** — InfoNCE 损失的出处，从互信息下界的角度推导对比目标。理解 NT-Xent 为何长这样的理论根。
- ★ **He et al. 2022, _Masked Autoencoders Are Scalable Vision Learners (MAE)_** — 生成式自监督的代表。随机掩掉 75% 图块、只编码可见块、轻量解码器重建像素，预训练高效且下游强。模块 05 的掩码重建直接来自它。
- **Grill et al. 2020, _Bootstrap Your Own Latent (BYOL)_** — 无需负样本、靠在线/目标网络 + 停梯度避免坍缩，挑战了「对比必须有负对」的认知。理解表示坍缩与如何规避。
- **Caron et al. 2021, _Emerging Properties in Self-Supervised ViT (DINO)_** — 自蒸馏式自监督，学到的注意力天然分割前景，展示 SSL 表示的涌现性质。SSL 前沿的重要一站。

## 本课定位与衔接 · Scope & Cross-links

- ⚠️ **本课全部纯 numpy / CPU 从零**：卷积/Sobel/Canny、HOG、IoU/NMS/mAP、Dice/mIoU/连通域、InfoNCE/MAE/linear probe 都不依赖深度学习框架，玩具规模，追求「看懂机制」。每个算法都在已知真值的合成数据上用 `assert` 验证逻辑正确（如 IoU 对称、NMS 去重、mAP 单调、Dice∈[0,1]）。
- **真实数据**：分类/检测/分割/自监督用 UCI **optdigits**(8×8 手写数字)，滤波/边缘用 **Grace Hopper** 照片（matplotlib 示例）。联网下载失败时自动回退到逻辑等价的合成图，保证 notebook 离线也能跑通、assert 不变。
- **课程衔接**：与 **C15（CNN 架构）** 互补——C15 讲卷积层/骨干网络怎么搭，本课聚焦把这些骨干用到的**CV 任务与评测口径**（分类→检测→分割→自监督）；上接图像基础，下游接多模态/VLM 的视觉编码器。你在这里写对的 IoU/NMS/mAP/Dice/InfoNCE，正是读检测/分割/SSL 论文与评测代码的硬通货。
