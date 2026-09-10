# XPENG TSR（交通标志识别）ML/CV 工程师 · 面试复习计划

> 对照 JD：Machine Learning Engineer / Computer Vision Engineer — Traffic Sign Recognition (TSR) 2D Detection
> 基于本课程库当时的全部内容（C00–C52，53 门课）逐项扫描后的结论。
> 生成日期：2026-08-17。**此后课程库已扩到 C00–C77（78 门）**——
> 下面 §三 的「缺口」是相对 2026-08-17 那 53 门课说的，§六 记录了其中 9 个缺口后来是怎么补的。

---

## 目录

1. [JD 核心要求拆解](#一jd-核心要求拆解)
2. [快速复习清单（按优先级）](#二快速复习清单按优先级)
3. [JD 要求但课程库未覆盖的缺口](#三jd-要求但课程库未覆盖的缺口需课外补)
4. [建议复习时间表](#四建议复习时间表)
5. [高概率面试题清单](#五高概率面试题清单)

---

## 一、JD 核心要求拆解

把 JD 的职责与资格要求归纳为 7 个能力块，并标注课程库覆盖情况：

| # | 能力块 | JD 原文关键词 | 课程覆盖 |
|---|--------|--------------|----------|
| 1 | **2D 目标检测算法** | YOLO, Faster R-CNN, DETR/Deformable DETR, RT-DETR, RTMDet | 🟡 部分（C18；RT-DETR/RTMDet 缺失） |
| 2 | **检测评测与误差分析** | mAP, precision/recall, FP/FN analysis, class-level breakdown | 🟢 覆盖好（C18-03 从零实现） |
| 3 | **数据工作** | dataset curation, augmentation, class imbalance, hard-case mining, long-tail mining | 🟡 部分（图像增强与检测语境挖掘缺失） |
| 4 | **训练实验设计** | data sampling, loss tuning, experiment design | 🟢 基本覆盖（C18 + C07 + C37） |
| 5 | **部署优化** | ONNX, TensorRT, quantization, edge deployment, C++ inference, CUDA | 🟡 概念层覆盖（C27/C52/C36；实操深度不足） |
| 6 | **工程闭环** | experiment tracking, reproducibility, regression testing, version management, data-model-eval loop | 🟢 覆盖好（C37 全课） |
| 7 | **VLA 集成** | improve VLA models to consume TSR outputs, VLA prompts | 🔴 未覆盖（C00 VLM 是最近的近亲） |

---

## 二、快速复习清单（按优先级）

### 🥇 第一梯队 —— JD 靶心，务必精读

#### 1. C18 计算机视觉 · `C18_Computer_Vision_Course/03_detection/`（最高优先级）

**为什么**：整个 JD 的核心。基本资格里的 "detection architectures"、"mAP, precision/recall, FP/FN analysis, class-level performance breakdown" 全部对应这个模块。

**讲解 HTML（`03_讲解.html`）覆盖**：
- 两阶段：Faster R-CNN（RPN → RoI）
- 单阶段：YOLO、SSD、RetinaNet + Focal Loss
- Transformer 检测：DETR、Deformable DETR（注意：只到 Deformable，RT-DETR 见缺口清单）
- anchor-based vs anchor-free 范式
- 小目标与长尾问题（有提及，但技术手段不深，见缺口清单）

**Notebook（`03_detection.ipynb`）从零实现**：
- IoU（交并比）
- 贪心 NMS
- TP/FP 匹配逻辑
- Precision-Recall 曲线（累积计数法）
- AP（单调包络 + 面积）与 mAP
- anchor 的 IoU 正负样本判定
- 4 道带 assert 的练习 + optdigits 玩具检测胶囊

**复习动作**：
- [ ] 手写 IoU 和 NMS（面试白板题概率极高），注意边界情况（无交集、包含关系、score 相同）
- [ ] 能口头完整推导 mAP 计算流程：置信度排序 → TP/FP 判定（IoU 阈值 + 每个 GT 只匹配一次）→ 累积 P/R → 单调包络 → 面积
- [ ] 能对比 anchor-based vs anchor-free vs set-prediction（DETR）三种正负样本分配方式
- [ ] 想清楚 Focal Loss 的公式和它解决什么问题（one-stage 的极端前景/背景不平衡）——这直接对应 JD 的 "class imbalance handling"

**配套快速过**：`02_classification/`（backbone、训练流程）、`04_segmentation/`（了解即可，TSR 不是分割任务但可能被问到全景感知）

---

#### 2. C27 模型压缩 · `C27_Model_Compression_Course/`

**为什么**：对应 JD 的 "quantization / inference acceleration" 与加分项 "quantization accuracy drop" 调试。

**重点模块**：
- `01_quantization/` —— 核心。PTQ vs QAT、校准（calibration）、scale/zero-point、per-tensor vs per-channel
- `05_pruning/` —— 结构化剪枝与延迟的关系
- `04_distillation/` —— 蒸馏（大模型 → 车端小模型是自动驾驶常见套路）
- `02_gptq_awq/`、`03_fp8_training/` —— 选读，LLM 语境，可跳过

**⚠️ 注意**：本课语境偏 LLM（GPTQ/AWQ/SmoothQuant）。复习时主动把概念映射回 CNN/DETR 检测模型：
- LLM 的 outlier channel 问题 ↔ 检测模型 BN 融合后的激活分布
- 校准集选择 ↔ 用什么驾驶场景图像做 INT8 校准
- 逐层精度回退定位（layer-wise sensitivity analysis）—— 这个方法论是通用的，面试讲"量化掉点怎么查"时直接可用

**复习动作**：
- [ ] 能写出对称/非对称量化公式，解释 scale 和 zero-point
- [ ] 能讲清 PTQ 掉点排查流程：先确认预处理一致 → 逐层替换定位敏感层 → 敏感层保留 FP16 / 换 per-channel → 必要时 QAT
- [ ] 了解 QAT 的 fake quantization + STE（straight-through estimator）

---

#### 3. C52 工业研究工程实务 · `C52_Industrial_Research_Practice_Course/`

**为什么**：对应 JD 的 "ONNX / TensorRT / edge deployment" 与 "CUDA" 加分项。

**重点模块**：
- `03_export_runtime/` —— ONNX 导出、opset 版本、onnxruntime、TensorRT、TFLite/CoreML 对比
- `04_gpu_workflow/` —— 真机 GPU 工作流、CUDA 环境诊断

**复习动作**：
- [ ] 能讲清 PyTorch → ONNX → TensorRT 的完整链路，以及每一步会出什么问题（不支持的算子、动态 shape、opset 不匹配）
- [ ] 知道导出后要做数值一致性校验（对齐输入 → 比较输出 atol/rtol）——课程里有提及但不深，结合缺口清单第 8 条扩展
- [ ] 了解 FP16/INT8 engine build 的基本概念

---

### 🥈 第二梯队 —— 支撑「工程闭环」叙事，面试讲系统设计时用

#### 4. C37 MLOps · `C37_MLOps_Course/`（全课 5 模块都相关）

**为什么**：JD 的 "What Success Looks Like" 几乎就是这门课的目录——"scalable data-model-evaluation-deployment loop"。加分项 "experiment tracking, reproducibility, regression testing, model version management" 逐条对应。

| 模块 | 对应 JD 条目 |
|------|-------------|
| `01_experiment_tracking/` | experiment tracking, reproducibility |
| `02_versioning/` | model version management, dataset versioning |
| `03_cicd_gates/` | regression testing（模型准入门禁） |
| `04_monitoring_drift/` | track model performance across versions |
| `05_feedback_retraining/` | data-model-evaluation feedback loops |

**复习动作**：
- [ ] 准备一个完整叙事："我如何设计 TSR 的模型迭代闭环"——数据挖掘 → 标注 → 训练（tracking）→ 场景化评测 + 回归测试门禁 → 部署 → 线上 badcase 回流
- [ ] 能解释回归测试在模型迭代中的形态：固定评测集 + 分场景切片（scenario-based slices）+ 不允许旧场景掉点的门禁

#### 5. C15 经典架构 · `01_convolution_pooling/` + `02_cnn_architectures/`

**为什么**：CNN 是检测面试的地基。**专门想清楚：感受野/stride/下采样与小目标检测的关系**（为什么 stride 32 的特征图检测不了 20px 的交通标志）——这是把基础知识连到 TSR 业务的关键一环。

#### 6. C01 LLM 内核（attention 部分）· `C01_LLM_Internals_Course/`

**为什么**：JD 明确要 "DETR/Transformer-based TSR models"。DETR = CNN backbone + transformer encoder-decoder + object queries。把 self-attention / cross-attention 的实现过一遍，支撑你讲清：
- object query 如何通过 cross-attention 从图像特征里「认领」目标
- Deformable attention 为什么能加速收敛（稀疏采样点 vs 全局注意力）

#### 7. C10 评测测量 · `01_annotation_label_noise/` + `06_calibration_uncertainty/`

**为什么**：对应 JD 的 "debug issues across data quality, labeling" 与评测管道设计。标注噪声的检测与处理（置信学习思路）在 TSR 这种大规模标注场景很实用。

#### 8. C07 ML 基础 · `06_generalization_metrics/` + `07_ml_interview_drills/`

**为什么**：面试数学保底。过拟合/正则化/偏差方差、常见 loss 的梯度推导。

---

### 🥉 第三梯队 —— 有时间再看

| 课程 | 模块 | 与 JD 的关系 |
|------|------|-------------|
| C00 VLM 多模态 | `04_connectors_training/`, `05_instruction_tuning/` | JD 的 VLA 条目的最近背景知识：视觉特征如何接入语言模型、指令微调怎么做 |
| C43 数据工程 | `04_quality_filtering/`, `05_provenance_decontam/` | "large-scale data pipelines" 加分项 |
| C36 GPU Kernels | `01_execution_model/` | CUDA 加分项，了解执行模型即可，不必深入写 kernel |
| C24 推理服务 | `01`–`02` 概念部分 | latency/throughput 权衡的语言，语境偏 LLM |
| C14 DL 理论与数据 | 数据评测部分 | 数据集分析方法论 |

---

## 三、JD 要求但课程库未覆盖的缺口

> **更新（2026-08-17）**：下列 9 个缺口已各自开发成一门完整课程 **C53–C61**，
> 规格与既有课程一致（每门 6 模块，每模块 = 深度 HTML 讲解 + 可运行 numpy notebook + 练习 assert 判分）。
> 缺口 ↔ 课程对照表见本文 [§六](#六缺口--新增课程对照)。
> 本节保留原始缺口分析，它解释了「**为什么**要学这些」——面试时这套归因本身就是可讲的内容。

> 按面试风险从高到低排序。这些是 JD 里最有区分度、最可能被追问的部分。

### 🔴 缺口 1：RT-DETR 与 RTMDet（JD 点名，全库零覆盖）

JD 原文："DETR/Deformable DETR, **RT-DETR**, **RTMDet**, or similar models"。

**补法**：精读 RT-DETR 论文（*DETRs Beat YOLOs on Real-time Object Detection*, 2023）。核心要点：
- **Efficient hybrid encoder**：只对最高层（S5）特征做 attention（AIFI），跨尺度融合用 CNN（CCFF）——把 encoder 计算量打下来
- **IoU-aware query selection**：用 IoU 感知的分类分数选初始 query，提升初始化质量
- **无 NMS**：end-to-end set prediction，延迟稳定（YOLO 的 NMS 耗时随目标数波动——这对车端实时性是卖点）
- 可调 decoder 层数做速度/精度权衡，无需重训

RTMDet 要点：anchor-free 单阶段、CSPNeXt backbone、动态软标签分配（dynamic soft label assignment）、大 kernel 深度卷积。

### 🔴 缺口 2：DETR 的匈牙利匹配 / set prediction loss（全库无）

DETR 面试标配问题，C18 讲了 DETR 概览但没讲匹配机制。

**补法**：搞懂三件事：
1. **二分图匹配**：N 个 prediction ↔ M 个 GT 的一对一最优匹配（scipy `linear_sum_assignment`），匹配代价 = 分类代价 + L1 box 代价 + GIoU 代价
2. **为什么不需要 NMS**：一对一匹配训练迫使每个 GT 只有一个 query 负责，重复预测在训练中被压制
3. **DETR 收敛慢的原因与解法**：全局 attention 稀疏梯度 → Deformable（稀疏采样）、DN-DETR（去噪训练）、DINO（对比去噪 + 混合匹配）

### 🔴 缺口 3：TSR / 自动驾驶领域知识（完全没有）

**补法**：
- **数据集**：GTSRB/GTSDB（德国，经典）、TT100K（清华腾讯，中国标志，典型小目标+长尾）、Mapillary Traffic Sign（全球，region-specific 的代表）
- **TSR 典型架构**：检测与分类常解耦——检测器找"这是个标志"（类别无关或粗类别），第二级分类器细分几百类。想清楚为什么：细类别极度长尾 + 新增标志类别时不必重训检测器
- **TSR 特有难点**（对应 JD 的 failure cases 列举）：小目标（远距离标志常 <32px）、遮挡（树木/车辆）、光照（逆光/夜晚/隧道口）、雨雾雪、褪色/破损标志、电子可变标志、区域差异（限速单位、颜色规范）
- **了解 XPENG 背景**：XNGP/图灵芯片、端到端大模型 + VLA 的技术路线（面试前搜一下小鹏最新的技术分享）

### 🟠 缺口 4：检测专用图像数据增强（C51 是纯文本增强，不对口）

JD 明确要求 "augmentation" 设计。全库无 Mosaic/MixUp/copy-paste 内容。

**补法**：掌握每种增强的机制和适用性判断：
- **Mosaic**（4 图拼接）：变相增大 batch 多样性 + 产生更多小目标——对 TSR 友好
- **MixUp / CutMix**：正则化，检测里效果依场景
- **Copy-paste**：把稀有类别标志抠出来贴到新背景——**长尾类别的直接解法**，面试值得主动提
- **多尺度训练**、随机裁剪、色彩抖动（注意：交通标志颜色是语义！色相抖动要谨慎——这是个能体现领域思考的好观点）
- **几何增强的坑**：水平翻转对文字类/箭头类标志是错的（左转标志翻转变右转）——主动讲这个能加分

### 🟠 缺口 5：小目标检测技术（C18 只提问题没给手段）

TSR 本质是小目标问题，JD 把 "small objects" 列进 failure cases。

**补法**：
- **高分辨率输入 / 切片推理（SAHI）**：大图切块检测再合并
- **FPN 层级分配**：小目标分到高分辨率层（P2/P3）；必要时给检测头加 P2 层
- **anchor/label assignment 对小目标的偏见**：IoU 对小框极敏感（偏移 2px IoU 掉一半）→ 小目标正样本少 → 可用 center-based 分配或放宽小目标的 IoU 阈值
- **上采样/超分特征**、拷贝粘贴增强（连到缺口 4）

### 🟠 缺口 6：检测语境的 hard-case mining / 长尾挖掘（库里只有检索/推荐语境）

JD："hard-case mining"、"long-tail scenario mining"、"mining strategies"。

**补法**：准备一套完整方法论叙事：
1. **训练时**：OHEM（在线难例挖掘）、Focal Loss（软性难例加权）、类别重采样（class-balanced sampling / repeat factor sampling）
2. **数据闭环挖掘**：车队影子模式 → 模型不确定性/低置信度触发回传；用大模型（VLM）做场景自动标签（scenario tagging）；用嵌入相似度检索"和这个 badcase 长得像的数据"
3. **评测切片**：按场景（夜晚/雨天/小目标/稀有类）分桶评测，定位掉点桶 → 定向挖数据 → 回归验证——把这个和 C37 的闭环叙事拼起来就是完整答案

### 🟡 缺口 7：VLA（vision-language-action）模型（全库零覆盖）

JD 独特条目："Improve VLA models to effectively consume TSR outputs and support traffic-sign-aware instruction following through VLA prompts."

**补法**：
- 概念层：RT-2、OpenVLA 的基本思路（VLM backbone + 动作输出）；小鹏自己在推 "VLA 大模型" 上车，面试前搜其公开技术分享
- 准备设计题思路："TSR 输出如何喂给 VLA"——结构化感知结果（类别/位置/置信度）序列化为 prompt token vs 特征级融合；限速/禁行等标志如何转化为可被指令跟随消费的约束；感知错误时 VLA 的鲁棒性（置信度也要传进去）
- 你的优势：C00 VLM 课的 connector/instruction tuning 知识可以直接迁移到这个话题

### 🟡 缺口 8：TensorRT/C++ 实操与训练-部署一致性调试（概念有、实操浅）

JD 加分项："debugging training-to-deployment consistency issues, including preprocessing mismatch, postprocessing mismatch, quantization accuracy drop, or runtime performance bottlenecks"；"C++ inference pipelines"。

**补法**：准备一套排查 checklist 叙事（面试官要的是方法论不是 API 背诵）：
1. **预处理不一致**：resize 插值算法（bilinear vs bicubic vs nearest）、BGR/RGB、归一化 mean/std、letterbox padding 方式——逐项 diff，用同一张图 dump 两边预处理后的张量比对
2. **模型本体**：ONNX 导出后先用 onnxruntime 对齐 PyTorch（atol/rtol），再上 TensorRT；FP16 溢出层排查（逐层输出范围统计）
3. **后处理不一致**：NMS 阈值/实现差异、坐标系（归一化 vs 像素）、score 是否过了 sigmoid
4. **性能瓶颈**：trtexec profile、layer-wise 耗时、是否掉回 FP32 fallback、内存拷贝 vs 计算占比

### 🟡 缺口 9：3-5 年检测经验对应的「实战细节」

课程库是原理型的，JD 要的是 production 手感。面试前把你自己过往项目（哪怕课程项目）整理成 STAR 故事，每个故事覆盖：badcase 分析 → 假设 → 数据/模型改动 → 指标变化 → 回归验证。**没有真实车载项目不要紧，方法论完整、指标意识强就能弥补大半。**

---

## 四、建议复习时间表

假设距面试约一周（可按实际压缩/拉伸）：

| 天 | 内容 |
|----|------|
| **D1** | C18-03 全模块精读 + 手写 IoU/NMS/AP 三件套（不看答案重写一遍） |
| **D2** | 缺口 1+2：RT-DETR 论文 + DETR 匈牙利匹配 + Deformable/DINO 演进线 |
| **D3** | 缺口 3+5：TSR 领域知识 + 小目标技术；C15-01/02 快速过（感受野 ↔ 小目标） |
| **D4** | C27-01 量化 + C52-03/04 导出部署 + 缺口 8 的一致性排查 checklist |
| **D5** | C37 全课快速过 + 缺口 6，拼出「数据-模型-评测-部署闭环」完整叙事 |
| **D6** | 缺口 4（检测增强）+ 缺口 7（VLA）+ C00 connector 部分；C07-07 面试题热身 |
| **D7** | 模拟面试：白板 IoU/NMS、讲一遍 RT-DETR、讲一遍闭环设计、过 STAR 故事 |

---

## 五、高概率面试题清单

**白板/编码**
1. 手写 IoU（含边界情况）
2. 手写 NMS；追问：soft-NMS 是什么？DETR 为什么不需要 NMS？
3. 解释并手推 mAP 计算流程；追问：COCO mAP@[.5:.95] 和 VOC mAP 的区别
4. 手写 Focal Loss；追问：γ 和 α 各控制什么

**架构与算法**
5. Faster R-CNN vs YOLO vs DETR 的正负样本分配对比
6. DETR 匈牙利匹配怎么做？匹配代价包含哪几项？
7. Deformable DETR 解决了 DETR 什么问题？怎么解决的？
8. RT-DETR 为什么能 beat YOLO？（hybrid encoder + 无 NMS 稳定延迟）
9. 小目标为什么难？你会从哪几个方向改进？

**数据与评测**
10. 交通标志类别极度长尾，你怎么处理？（采样/loss/增强/两级架构/数据挖掘，多层次回答）
11. 线上出现某类标志漏检，你的排查流程是什么？
12. 怎么设计 TSR 的评测体系？（分场景切片 + 回归门禁 + 关键类别单独看）
13. 水平翻转增强对交通标志有什么坑？

**部署**
14. INT8 量化后 mAP 掉了 3 个点，怎么排查？
15. 车端和离线训练结果不一致，可能的原因？（预处理/后处理/精度/算子 fallback）
16. PyTorch → ONNX → TensorRT 各环节常见的坑

**系统设计**
17. 设计一个 TSR 的数据-模型-评测-部署迭代闭环（把 C37 + 缺口 6 的叙事完整讲出来）
18. TSR 输出如何接入 VLA / 下游规控？置信度如何传递？

---

## 六、缺口 ↔ 新增课程对照

> 2026-08-17 新增。§三 识别的 9 个缺口已各自开发成一门完整课程（C53–C61），
> 规格与既有 53 门课一致：每门 6 模块，每模块 = 深度 HTML 讲解（可见字符 8600+）
> + 可运行 numpy notebook（30+ cells，含 ✏️ 练习 assert 判分与 📖 参考答案）
> + 每门配 glossary（12KB+）与 references（8KB+）。全部纯 CPU、无需 GPU/联网。

| 缺口（§三） | 新增课程 | 关键模块 |
|---|---|---|
| 1. RT-DETR / RTMDet | **C53 实时检测器架构** | `04_rtdetr` 含专设的「面试标准答案骨架」一节 |
| 2. 匈牙利匹配 / set prediction | **C54 端到端集合预测检测** | `01_hungarian` 从零实现 KM 算法 |
| 3. TSR / 自动驾驶领域知识 | **C55 交通标志识别与自动驾驶感知** | `03_failure_modes` 失效模式全景 |
| 4. 检测专用图像增强 | **C56 检测数据增强工程** | `03_mixing` Mosaic / Copy-Paste |
| 5. 小目标检测技术 | **C57 小目标检测** | `01_why_hard` 定量分析 + `05_tsr_case` 物理推导 |
| 6. hard-case / 长尾挖掘 | **C58 难例挖掘与长尾数据闭环** | `03_triggers` + `05_close_loop` |
| 7. VLA | **C59 VLA 与感知接口** | `03_perception_interface`（全课落点） |
| 8. TensorRT / C++ / 一致性调试 | **C60 车端部署与训练-部署一致性** | `01_preprocess` + `03_int8` |
| 9. production 手感 | **C61 检测工程实战与面试实务** | `02_error_analysis` TIDE + `05_drills` 题库 |

### 面试前一周的推荐路线（结合新课）

| 天 | 内容 |
|----|------|
| **D1** | C18-03（既有）复习 mAP/NMS/IoU → **C54-01** 匈牙利匹配从零实现（手写一遍） |
| **D2** | **C53-01/02/04** YOLO 演进 → 标签分配 → RT-DETR（缺口 1+2 的主攻日） |
| **D3** | **C55-00/03/05** TSR 领域、失效模式、安全评测（本岗位最独特的知识） |
| **D4** | **C57-01/05** 小目标定量分析与 TSR 物理推导 → **C56-03** 混合增强 |
| **D5** | **C60-01/03** 预处理一致性 + INT8 校准（部署题的主要来源） |
| **D6** | **C58-03/05** 挖掘触发与闭环验证 → **C59-03** VLA 感知接口 |
| **D7** | **C61-04/05** 项目叙事模板 + 面试题库演练（白板题手写一遍） |

时间更紧的话，最小集是：**C54-01 · C53-04 · C55-03 · C57-01 · C60-03 · C61-05**。

---

*本文档基于课程库实际内容扫描生成：C18-03 覆盖 DETR/Deformable/Faster R-CNN/YOLO/Focal Loss/mAP-NMS-IoU 从零实现；RT-DETR、RTMDet、匈牙利匹配、Mosaic/MixUp/copy-paste、VLA 经全库关键词检索确认为零覆盖 —— 这 9 项已于 2026-08-17 补建为 C53–C61。*
