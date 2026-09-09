# 参考资料 · 多视角几何与多传感器时空对齐

> 分为「教科书与经典论文」「标定」「BEV 与自动驾驶感知」「时间同步」
> 「软件与规范」五部分。**本课的所有数值结论都来自 notebook 里可复现的计算**，
> 外部文献用于机制与背景，不用于本课引用的具体数字。

---

## 一 · 教科书与经典论文

| 文献 | 年份 | 与本课的关系 |
|---|---|---|
| Hartley &amp; Zisserman, *Multiple View Geometry in Computer Vision* (2nd ed.) | 2004 | **本课的主要参照**。第 6 章相机模型（模块 01）、第 9 章对极几何、第 11 章三角测量、第 12 章单应（模块 03）。本课把它的结论重新量成「米」。 |
| Szeliski, *Computer Vision: Algorithms and Applications* (2nd ed.) | 2022 | 第 11 章的结构化综述；对镜头模型与标定流程的工程视角比 H&amp;Z 更实用。 |
| Brown, *Close-Range Camera Calibration* | 1971 | 径向+切向畸变模型的来源（模块 01 第 3 节的 Brown–Conrady）。 |
| Hartley, *In Defense of the Eight-Point Algorithm*, TPAMI | 1997 | 点坐标归一化的经典论证。**本课模块 02 第 4 节量出它的收益在有噪声时被淹没**——这不是反驳该文（它讨论的是数值条件），而是说明它不该被当成精度手段。 |
| Kannala &amp; Brandt, *A Generic Camera Model and Calibration Method for Conventional, Wide-Angle, and Fish-Eye Lenses*, TPAMI | 2006 | 模块 01 第 6 节「多项式模型的表达边界」之外的替代模型。 |
| Lepetit, Moreno-Noguer &amp; Fua, *EPnP: An Accurate O(n) Solution to the PnP Problem*, IJCV | 2009 | 模块 03 第 6 节；本课只实现线性 DLT-PnP，EPnP/SQPnP 是实践起手方案。 |
| Terzakis &amp; Lourakis, *A Consistently Fast and Globally Optimal Solution to the PnP Problem*, ECCV | 2020 | SQPnP；OpenCV 4.x 的 `SOLVEPNP_SQPNP`。 |
| Ait-Aider et al., *Simultaneous Object Pose and Velocity Computation Using a Single View from a Rolling Shutter Camera*, ECCV | 2006 | 模块 05 第 3 节的背景。**本课的结论是对小目标不值得建模**，该文处理的是显著形变的情形。 |

---

## 二 · 标定

| 文献 / 资源 | 与本课的关系 |
|---|---|
| Zhang, *A Flexible New Technique for Camera Calibration*, TPAMI 2000 | 模块 02 第 2 节的全部内容。本课把它的「至少 3 个视角」直接算成约束矩阵的 rank（1/2/3 视角 → rank 2/4/5）。 |
| Zhang, *Camera Calibration with One-Dimensional Objects*, TPAMI 2004 | 一维标定物；本课未涉及，但它说明「需要什么样的多样性」这个问题有多个答案。 |
| OpenCV `calib3d` 文档 | `calibrateCamera` 的 flags 语义（`CALIB_ZERO_TANGENT_DIST`、`CALIB_FIX_K3`）；**注意 `ret` 返回的是均值 RMS，而模块 02 第 7 节说明必须自己算 P95**。 |
| Kalibr（ETH ASL） | 多相机 + IMU 的联合标定工具链；模块 02 第 5b 节提到的外参标定在实践中的主流实现之一。 |
| ROS `camera_calibration` | 棋盘格采集的交互式流程；**它的「进度条」本质上就是模块 02 第 3 节的朝向多样性检查**。 |

---

## 三 · BEV 与自动驾驶感知

| 文献 | 年份 | 与本课的关系 |
|---|---|---|
| Philion &amp; Fidler, *Lift, Splat, Shoot*, ECCV | 2020 | 模块 04 第 2 节提到的「学习式提升」——它绕开了「一个像素对应几格」这个问题，代价是需要训练。 |
| Li et al., *BEVFormer*, ECCV | 2022 | 用时空注意力从多相机构建 BEV；模块 04 的对照。**本课只做无学习的 IPM。** |
| Huang et al., *BEVDet* | 2021 | 另一条 BEV 检测路线。 |
| Liu et al., *BEVFusion*, ICRA | 2023 | 模块 04 第 7 节「融合层级」在多模态上的形态。 |
| Ma et al., *Vision-Centric BEV Perception: A Survey* | 2024 | BEV 方法的分类综述；对「几何法 vs 学习法」的边界梳理得比较清楚。 |
| Wang et al., *DETR3D*, CoRL | 2021 | 用 3D query 直接从多视角取特征，避免显式 BEV 网格。 |

---

## 四 · 时间同步

| 资源 | 与本课的关系 |
|---|---|
| IEEE 1588 (PTP) | 精确时间协议；模块 05 第 2 节「时钟漂移」的工业标准解法。 |
| ROS REP-103 | 坐标系与单位约定：**X 前、Y 左、Z 上**（本课全程采用）。 |
| ROS REP-105 | 坐标系命名：`base_link` / `odom` / `map`；模块 02 胶囊里的外参文件遵循它。 |
| ROS `message_filters::ApproximateTimeSynchronizer` | 模块 05 胶囊；**注意它只是丢掉对不上的帧，不修时间**，而 `slop` 的上限应由第 2 节的表反解。 |
| NVIDIA DriveWorks / AUTOSAR 时间同步文档 | 车载多传感器硬同步的实现约束；本课只在机制层提及。 |

---

## 五 · 软件与规范

| 资源 | 与本课的关系 |
|---|---|
| OpenCV `projectPoints` / `undistortPoints` / `initUndistortRectifyMap` | 模块 01 胶囊。**`initUndistortRectifyMap` + `remap` 就是第 5 节说的 LUT。** |
| OpenCV `findFundamentalMat` / `findEssentialMat` / `triangulatePoints` | 模块 03 胶囊。`findFundamentalMat` 的阈值参数是**像素**单位，对应 Sampson 距离。 |
| OpenCV `getPerspectiveTransform` / `warpPerspective` | 模块 04 胶囊。**`warpPerspective` 内部就是反向映射**，而 `WARP_INVERSE_MAP` 控制方向——搞反的症状就是 96.4% 空洞。 |
| USAC / MAGSAC++ (Barath et al., CVPR 2020) | 现代鲁棒估计；`cv2.USAC_MAGSAC` 在实践中优于经典 RANSAC。 |
| pydantic / dataclasses | 模块 01/03 胶囊里「把 $K$ 与图像尺寸绑定」「四元组」的实现方式。 |

---

## 六 · 本课程内的相关模块

| 模块 | 关系 |
|---|---|
| **C55 模块 04**（单相机时序融合） | 交界是「时间戳」这一个字段：C55 假设它对，本课模块 05 量它错了值多少米。**先修本课第 2 节，再谈 C55-04 的滤波调参。** |
| **C57**（小目标检测） | C57 管像素域的尺度问题，本课管米域的。「远处标志只有 12 px」是 C57；「12 px 对应 ±2 m 的距离不确定度」是本课模块 03。 |
| **C59 模块 03**（VLA 与感知接口） | C59 讲「BEV 这个接口该长什么样」，本课讲「这张图是怎么算出来的、什么时候是错的」。模块 03 的四元组是给这个接口用的。 |
| **C60**（车端部署一致性） | C60 管数值一致性，本课管几何一致性。模块 01 第 7 节的 $K$ 同步问题是两者的交集。 |
| **C68 模块 04**（分层门禁） | 模块 01 第 4 节「评测必须按图像位置分层」、模块 02 第 7 节的 P95 与外圈分层，都是它在几何层的形态。 |
| **C70/C71 模块 05**（观测量 vs 门禁） | 模块 04 第 6 节「重叠区一致性设报警不设阻断」用的是同一条原则。 |
| **C40 模块 03**（消融纪律） | 模块 01 第 3 节「该标几个畸变系数」用 P95 而不是均值来判，是同一条纪律。 |
