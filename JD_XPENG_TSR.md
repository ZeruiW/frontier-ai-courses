# 目标岗位 JD（逐字存档）· XPENG · TSR 2D Detection

> 本文件是**目标岗位的原始 JD 全文**，用于让所有课程开发 agent 与后续会话随时对齐目标。
> 缺口分析与复习路线见 [`INTERVIEW_PREP_XPENG_TSR.md`](INTERVIEW_PREP_XPENG_TSR.md)。
> 课程开发规范见 `_buildkit/GAPKIT_SPEC.md`（C53–C61）与 `_buildkit/GAPKIT_SPEC2.md`（C62–C65）。

---

## HR 补充的一面形式（2026-08-17）

> "it'll include coding, system design, ML knowledge, etc."
>
> **First Round Interview Format (including but not limited to):
> Technical Knowledge Assessment, Problem-Solving, and Practical (Coding) Exercise**

对应补建课程：C62（Coding Exercise）· C63（System Design）· C64（Technical Knowledge）· C65（Problem-Solving）。

---

## Company

XPENG is a leading smart technology company at the forefront of innovation, integrating advanced AI and autonomous driving technologies into its vehicles, including electric vehicles (EVs), electric vertical take-off and landing (eVTOL) aircraft, and robotics. With a strong focus on intelligent mobility, XPENG is dedicated to reshaping the future of transportation through cutting-edge R&D in AI, machine learning, and smart connectivity.

## About the Role

We are looking for a strong Machine Learning Engineer / Computer Vision Engineer to work on Traffic Sign Recognition (TSR) 2D detection for production autonomous driving systems.

In this role, you will be responsible for the full lifecycle of TSR model development, including scenario analysis, data preparation, model training, evaluation, optimization, quantization, and deployment. You will work closely with perception, data, infrastructure, and deployment teams to improve traffic sign detection performance across diverse real-world driving scenarios.

This role is ideal for candidates who enjoy solving practical computer vision problems, building reliable model iteration pipelines, and bringing perception models from offline training to onboard production systems.

## Job Responsibilities

- Develop and improve traffic sign detection models for autonomous driving perception systems.
- Investigate and Experiment DETR/Transformer-based TSR models for accurate and stable/robust traffic sign detection across diverse driving scenarios.
- Analyze TSR-related scenarios and failure cases, including missed detections, false positives, occlusions, small objects, rare signs, region-specific signs, and adverse weather or lighting conditions.
- Improve VLA models to effectively consume TSR outputs and support traffic-sign-aware instruction following through VLA prompts.
- Prepare, clean, curate, and analyze training and evaluation datasets for TSR model iteration.
- Design and execute model training experiments, including data sampling, augmentation, loss tuning, class imbalance handling, and hard-case mining.
- Build and maintain evaluation pipelines for TSR models, including offline metrics, scenario-based evaluation, regression testing, and error analysis.
- Collaborate with data teams to define mining strategies for long-tail TSR scenarios and improve dataset coverage.
- Optimize models for production deployment, including ONNX / TensorRT / quantization / inference acceleration.
- Work with deployment and platform teams to validate model performance on onboard or edge compute platforms.
- Track model performance across versions and support continuous improvement through data-model-evaluation feedback loops.
- Debug issues across the full stack, including data quality, labeling, model behavior, evaluation mismatch, and deployment consistency.

## Basic Qualifications

- Master's, or PhD degree in Computer Science, Electrical Engineering, Robotics, Computer Vision, Machine Learning, or a related field.
- 3-5 years of strong hands-on experience with computer vision models, especially object detection.
- Experience with detection architectures such as YOLO, Faster R-CNN, DETR/Deformable DETR, RT-DETR, RTMDet, or similar models.
- Proficiency in Python and deep learning frameworks such as PyTorch or TensorFlow.
- Solid understanding of object detection training workflows, including dataset preparation, augmentation, loss functions, evaluation metrics, and model debugging.
- Experience with common detection metrics such as mAP, precision/recall, false positive/false negative analysis, and class-level performance breakdown.
- Strong data analysis and problem-solving skills.
- Ability to work cross-functionally with model, data, infrastructure, and deployment teams.

## Preferred Qualifications

- Experience in autonomous driving, ADAS, robotics, or safety-critical perception systems.
- Experience with traffic sign recognition, traffic light recognition, road object detection, or small-object detection.
- Familiarity with long-tail scenario mining, hard negative mining, class imbalance handling, and dataset curation.
- Experience with ONNX, TensorRT, model quantization, C++ inference pipelines, CUDA, or edge deployment.
- Experience debugging training-to-deployment consistency issues, including preprocessing mismatch, postprocessing mismatch, quantization accuracy drop, or runtime performance bottlenecks.
- Familiarity with large-scale data pipelines, scenario tagging, or automated data mining workflows.
- Strong engineering discipline in experiment tracking, reproducibility, regression testing, and model version management.

## What Success Looks Like

A successful engineer in this role will:

- Improve TSR detection performance across both common and long-tail traffic sign scenarios.
- Build reliable data and evaluation workflows to support fast model iteration.
- Identify and prioritize high-impact failure modes through scenario analysis and data mining.
- Deliver deployable TSR models with strong accuracy, latency, and robust tradeoffs.
- Help establish a scalable data-model-evaluation-deployment loop for production TSR development.

## Why Join Us

- Work on production of autonomous driving perception systems with real-world impact.
- Own an important perception task that directly affects driving safety, rule understanding, and product quality.
- Collaborate with strong teams across model development, data, deployment, and vehicle platforms.
- Gain hands-on experience across the full model lifecycle: from data and training to evaluation, optimization, quantization, and onboard deployment.

---

## JD 条目 → 课程映射（速查）

| JD 条目 | 覆盖课程 |
|---|---|
| DETR/Transformer-based TSR | **C54**（集合预测全家）· **C53-04**（RT-DETR） |
| YOLO / Faster R-CNN / RT-DETR / RTMDet | **C53** 全课 · C18-03（既有） |
| failure cases：漏检/误检/遮挡/小目标/稀有/区域性/恶劣天气 | **C55-03**（失效模式全景）· **C57**（小目标）· **C56-02**（光度与天气） |
| VLA 消费 TSR 输出 + traffic-sign-aware instruction following | **C59**（全课，落点在 03 感知接口、04 规则约束化） |
| 数据准备、清洗、策展、分析 | **C55-01**（数据集与标注体系）· **C58-04**（挖掘基建）· C43（既有） |
| 训练实验：采样/增强/损失调优/类别不平衡/难例挖掘 | **C56**（增强）· **C58-01/02**（不平衡与难例）· **C61-01**（实验设计） |
| 评测流水线：离线指标/场景化评测/回归测试/误差分析 | **C55-05**（安全评测）· **C58-05**（闭环验证）· **C61-02**（TIDE 误差分析） |
| 长尾场景挖掘策略 | **C58-03/04**（触发与挖掘基建） |
| ONNX / TensorRT / 量化 / 推理加速 | **C60-02/03**（TensorRT 与 INT8）· C27（既有量化）· C52-03（既有导出） |
| 车端/边缘平台验证 | **C60-05**（性能剖析与验收） |
| 版本追踪与数据-模型-评测闭环 | **C58-05** · C37（既有 MLOps） |
| 全栈调试：数据质量/标注/模型行为/评测不匹配/部署一致性 | **C61-03**（调试手册）· **C60-01/04**（预处理与后处理一致性） |
| Python 熟练度 + coding exercise | **C62**（算法与数据结构） |
| system design | **C63** |
| ML knowledge assessment | **C64** |
| problem-solving | **C65** |
