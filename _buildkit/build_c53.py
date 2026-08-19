#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C53 · 实时检测器架构（YOLO 演进 · RTMDet · RT-DETR）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c53_m00, c53_m01, c53_m02, c53_m03, c53_m04, c53_m05

CID = "C53_RealTime_Detectors_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "实时检测的三个硬约束（延迟预算 / 显存 / 精度）与贯穿全课的三条主线——标签分配、无 NMS、结构重参数化 · "
     "延迟-精度曲线要「同延迟比 AP」而不是「同 AP 比延迟」 · 30 FPS 的 33 ms 里感知只分得到十几毫秒 · "
     "帕累托前沿与「被支配」判定：一个模型该不该进候选池是可以算出来的",
     c53_m00),
    ("01_yolo_evolution", "01_讲解.html", "01_yolo_evolution.ipynb",
     "01 · YOLO 家族演进：每一代到底改了什么",
     "v1 网格回归的根本缺陷（每格只认一个目标）· v2/v3 用 anchor + 多尺度 + FPN 补上召回 · "
     "v4/v5 的工程集大成（CSPNet / PAN / Mosaic / 自适应 anchor）· YOLOX 三件套：解耦头 + anchor-free + SimOTA · "
     "v6/v7 的结构重参数化——训练多分支、推理单分支，而且数值完全等价（可 assert）· v8 的 C2f 与 TaskAligned · "
     "v10 的一致双分配让「无 NMS」第一次真的成立 · <strong>每代改动的收益归因：哪些是架构红利、哪些是训练技巧红利</strong>",
     c53_m01),
    ("02_label_assignment", "02_讲解.html", "02_label_assignment.ipynb",
     "02 · 标签分配：检测器真正的胜负手",
     "同一个 backbone 换一套分配策略能差 3–5 AP，比换 backbone 更划算 · 静态 IoU 阈值对不同尺度极不公平"
     "（8×8 的框位移 2 px，IoU 就掉到 0.39）· ATSS 用「均值 + 标准差」把阈值自适应算出来 · "
     "OTA/SimOTA 的最优传输视角与 dynamic-k：正样本数量该由目标自己决定 · TaskAligned 的 t = s^α · u^β 把分类分数与定位质量对齐 · "
     "RTMDet 的 dynamic soft label · <strong>一对一 vs 一对多的本质：一对一是推理需求，不是训练最优</strong>",
     c53_m02),
    ("03_rtmdet", "03_讲解.html", "03_rtmdet.ipynb",
     "03 · RTMDet 解剖：大核、共享头与软标签",
     "用同一套框架做 tiny→x 全尺度，而不是每个尺度重新设计 · CSPNeXt 与 5×5 depthwise 大核："
     "有效感受野远小于理论感受野，而 depthwise 扩核的参数代价小到几乎免费 · 检测头跨尺度共享权重、每层独立 BN"
     "（共享的是「怎么判断」，不共享的是「统计量」）· dynamic soft label 的代价函数与中心先验 · "
     "深度 / 宽度 / 分辨率三者的缩放分配 · RTMDet-Ins 的实例分割扩展与它对 TSR 的启发",
     c53_m03),
    ("04_rtdetr", "04_讲解.html", "04_rtdetr.ipynb",
     "04 · RT-DETR 解剖：DETR 如何跑赢 YOLO",
     "动机不是「更准」而是「更稳」——NMS 的耗时随目标数与阈值波动，是端到端延迟方差的主要来源 · "
     "efficient hybrid encoder：只在最高层 S5 做 self-attention（高层语义才需要全局交互）+ CCFF 用 CNN 做跨尺度融合，FLOPs 账算给你看 · "
     "IoU-aware query selection：按分类分数选 query 会选到定位差的那些 · "
     "<strong>decoder 层数可调 = 同一份权重支持多档速度-精度而无需重训</strong>，这是部署上的大杀器 · "
     "RT-DETRv2 的离散采样与 D-FINE 的细粒度分布优化 · 面试标准答案骨架",
     c53_m04),
    ("05_benchmark", "05_讲解.html", "05_benchmark.ipynb",
     "05 · 延迟-精度权衡与实时检测器选型",
     "端到端延迟的六段拆解（预处理 / H2D / 推理 / NMS / 后处理 / D2H），只报「推理」那一段是最常见的自欺 · "
     "<strong>论文 FPS 为什么基本不可比</strong>：batch 多大、含不含 NMS、含不含预处理、什么精度、什么卡、什么驱动 · "
     "帕累托前沿与被支配判定 · 目标数从 10 涨到 300 时谁的 p99 先崩 · "
     "为 TSR 场景选型的完整推理链（小目标多、类别长尾、延迟预算紧、要求稳定）· "
     "精度之外的工程指标：p99 延迟、显存峰值、engine 构建时间、多硬件一致性、可维护性",
     c53_m05),
]


def build():
    install_assets(DIR)
    for i, (folder, html_name, nb_name, h1, subtitle, mod) in enumerate(MODULES):
        prev = nxt = None
        if i > 0:
            p = MODULES[i - 1]; prev = ("../%s/%s" % (p[0], p[1]), p[3])
        if i < len(MODULES) - 1:
            n = MODULES[i + 1]; nxt = ("../%s/%s" % (n[0], n[1]), n[3])
        lesson(os.path.join(DIR, folder, html_name),
               num="%02d" % i, total=TOTAL, h1=h1, subtitle=subtitle,
               meta=mod.META, sections=mod.SECTIONS, prev=prev, nxt=nxt)
        notebook(os.path.join(DIR, folder, nb_name), mod.NB)

    index(
        os.path.join(DIR, "index.html"),
        title="实时检测器架构",
        subtitle="从 YOLOv1 的网格回归到 RT-DETR 的端到端无 NMS："
                 "把「实时检测」拆成三条可以算清楚的主线——<strong>标签分配</strong>决定精度上限、"
                 "<strong>无 NMS</strong>决定延迟方差、<strong>结构重参数化</strong>决定同等精度下能跑多快。"
                 "YOLO 家族 · YOLOX · RTMDet · RT-DETR / v2 / D-FINE 逐个解剖，最后给出一套可复现的选型方法。",
        pills=["6 模块",
               "YOLOv1–v10 · YOLOX · RTMDet · RT-DETR · D-FINE",
               "标签分配 · 无 NMS · 重参数化",
               "同延迟比 AP，而不是同 AP 比延迟",
               "CPU only · 纯 numpy · 无需 GPU / torch / mmdet"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em>，再跑 <em>notebook</em>——后者用纯 numpy 把每个机制从零复现："
            "一个把 Conv+BN 与多分支合并成单个 Conv 的<strong>重参数化数值等价证明</strong>（<code>assert np.allclose</code> 收尾）、"
            "从零实现的 <code>ATSS</code> / <code>SimOTA</code>（代价矩阵 + dynamic-k + 去冲突）/ <code>TaskAligned</code> 三种分配并在同一组合成数据上对比正样本集合、"
            "用梯度回传法实测<strong>有效感受野</strong>（对比 3×3 堆叠与 5×5 depthwise）、"
            "一条随目标数增长的 <code>NMS</code> 耗时曲线与端到端延迟方差对比、"
            "以及一个帕累托前沿筛选器与「给定延迟预算怎么选」的决策脚本。"
            "每个练习都有紧跟的 <code>assert</code> 自测判分。配套 <a href=\"glossary.md\">术语词典</a> 与 "
            "<a href=\"references.md\">参考清单</a>。"
            "<strong>本课的主张是：实时检测这十年的进步，八成不在「网络画得更漂亮」，而在两个可量化的地方</strong>——"
            "<em>训练时哪些位置被判为正样本</em>（标签分配），以及<em>推理时有没有一段耗时不可控的后处理</em>（NMS）。"
            "把这两件事讲清楚，你就能解释为什么 YOLOX 只改了三个地方就涨了 3 AP、"
            "为什么 RT-DETR 敢说自己在同延迟下赢过 YOLO、"
            "也能在面试里把「YOLO 和 DETR 你选哪个」答成一段有数字的推理，而不是一句偏好。"
            "<strong>本环境不需要 GPU，也不需要装 torch / mmdetection / TensorRT</strong>："
            "我们复现的是这些系统的<em>机制与账本</em>（分配规则、融合的代数等价、FLOPs 与访存量、延迟分布），"
            "而这恰恰是可迁移的那部分——版本会变，账不会。"
            "每个模块末尾都有一个 🧪 <strong>真实工程胶囊</strong>，把当天的结论翻译成可以原样复制进 "
            "<code>mmdetection</code> / <code>ultralytics</code> / <code>RT-DETR</code> 仓库的配置与命令。"
        ),
        tracks=[
            ("先把地图摊开 · The Landscape", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "实时检测的三个硬约束；三条贯穿全课的主线（标签分配 / 无 NMS / 重参数化）；"
                 "延迟-精度曲线的正确读法——同延迟比 AP，而不是同 AP 比延迟；"
                 "30 FPS 的 33 ms 预算里，感知实际只分得到十几毫秒，而且还要和其他任务抢；帕累托前沿与「被支配」的判定。"),
                ("01_yolo_evolution/01_讲解.html", "MODULE 01", "YOLO 家族演进：每一代到底改了什么",
                 "v1 的每格一目标是结构性缺陷而非调参问题；v2/v3 用 anchor + 多尺度换回召回；"
                 "v4/v5 是工程集大成（CSPNet 省的是访存不是 FLOPs）；YOLOX 的三件套各贡献多少；"
                 "v6/v7 的重参数化是<em>代数恒等变换</em>，所以推理端一分钱不花；v8 的 C2f 与 TaskAligned；"
                 "v10 的一致双分配让「无 NMS」第一次真的成立。收益归因这一节是面试常问。"),
            ]),
            ("两个真正的胜负手 · Assignment & Architecture", [
                ("02_label_assignment/02_讲解.html", "MODULE 02", "标签分配：检测器真正的胜负手",
                 "标签分配决定了「梯度从哪里来」，所以它比 backbone 更影响精度；"
                 "固定 IoU 阈值对小目标是系统性歧视；ATSS 用统计量把阈值算出来；"
                 "OTA 把分配写成最优传输、SimOTA 用 dynamic-k 做廉价近似；TaskAligned 用 t = s^α·u^β 强迫分类与定位对齐；"
                 "RTMDet 的软标签把「差一点」和「差很多」区分开。密集小目标场景（正是 TSR）对分配最敏感。"),
                ("03_rtmdet/03_讲解.html", "MODULE 03", "RTMDet 解剖：大核、共享头与软标签",
                 "RTMDet 的价值在于「一套设计吃下 tiny→x」，这对要同时上多档硬件的量产团队意义极大；"
                 "5×5 depthwise 大核为什么有效——有效感受野是理论感受野的一小块，而 depthwise 扩核几乎不要钱；"
                 "检测头跨尺度共享权重但每层独立 BN（共享判断逻辑、不共享统计量）；"
                 "dynamic soft label 的代价函数与中心先验；缩放策略与参数量/FLOPs 计算器。"),
            ]),
            ("端到端与选型 · End-to-End & Selection", [
                ("04_rtdetr/04_讲解.html", "MODULE 04", "RT-DETR 解剖：DETR 如何跑赢 YOLO",
                 "先想清楚 RT-DETR 到底在跟谁比：它换掉的不是精度而是<em>延迟的不确定性</em>；"
                 "hybrid encoder 只在 S5 做 self-attention 的 FLOPs 账；"
                 "IoU-aware query selection 修的是「分类分高但框不准」的经典错配；"
                 "decoder 层数可调意味着同一份权重能出多档速度-精度组合而不必重训——这在多硬件平台上是决定性优势；"
                 "RT-DETRv2 与 D-FINE 的后续改进；一份可以直接背的面试答案骨架。"),
                ("05_benchmark/05_讲解.html", "MODULE 05", "延迟-精度权衡与实时检测器选型",
                 "端到端延迟的六段拆解，以及为什么只报「推理」那一段等于自欺；"
                 "论文 FPS 的六个不可比维度；帕累托前沿与被支配判定；"
                 "目标数从 10 涨到 300 时，含 NMS 的方案 p99 会先崩；"
                 "为 TSR 场景选型的完整推理链；以及精度之外真正决定上不上车的工程指标（p99、显存峰值、engine 构建时间、多硬件一致性）。"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), README)
    text_file(os.path.join(DIR, "requirements.txt"), REQUIREMENTS)
    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


README = r"""
# 实时检测器架构（YOLO 演进 · RTMDet · RT-DETR）

这门课回答一个具体问题：**在一块车规算力、一个几十毫秒的预算里，今天应该跑什么检测器，为什么。**

它不是「检测入门」（那是 C18），也不是「DETR 原理」（那是 C54）。
它的落点是**实时**这两个字：当延迟成为一等约束时，检测器的设计取舍会发生什么变化，
以及这些取舍如何被量化、被比较、被写进一份能过评审的选型报告。

课程覆盖 YOLOv1 到 v10 的完整演进、YOLOX、RTMDet 与 RT-DETR / RT-DETRv2 / D-FINE，
但组织方式不是编年史，而是**三条贯穿全课的主线**。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | YOLO 家族演进：每一代到底改了什么 | `01_yolo_evolution/` |
| 02 | 标签分配：检测器真正的胜负手 | `02_label_assignment/` |
| 03 | RTMDet 解剖：大核、共享头与软标签 | `03_rtmdet/` |
| 04 | RT-DETR 解剖：DETR 如何跑赢 YOLO | `04_rtdetr/` |
| 05 | 延迟-精度权衡与实时检测器选型 | `05_benchmark/` |

## 三条主线（贯穿全课）

1. **标签分配 · Label Assignment** — 决定「梯度从哪些位置来」。
   同一个 backbone、同一份数据，换一套分配策略能差 **3–5 AP**，
   这个收益比换 backbone 大得多，也便宜得多。
   从静态 MaxIoU → ATSS → OTA/SimOTA → TaskAligned → dynamic soft label，
   每一步都在回答同一个问题：**一个 GT 该配几个正样本、配哪些。**

2. **无 NMS · NMS-free** — 决定「延迟的方差」。
   NMS 的耗时随目标数与阈值波动，是端到端 p99 延迟最主要的不确定性来源。
   DETR 用一对一匹配在**训练期**解决重复，YOLOv10 用一致双分配把这件事搬回 YOLO 体系。
   注意：无 NMS 换来的首先是**稳定**，其次才可能是快。

3. **结构重参数化 · Re-parameterization** — 决定「同等精度下能跑多快」。
   训练时用多分支拿表达能力与更好的梯度，推理前用**代数恒等变换**合并成单分支。
   这是少数几个「训练收益免费带到推理端」的技巧，
   而它的正确性是可以逐元素 `assert` 出来的——notebook 里就会这么做。

三条主线其实是同一件事的三个侧面：
**在延迟被钉死的前提下，把每一分精度都换成不增加推理成本的东西。**

## 学习路径

- **想快速建立全局观**（约 2 小时）：00 → 01 → 05。
  读完你能画出延迟-精度曲线、说清 YOLO 每一代的改动归因、并给出一个有理有据的选型建议。
- **想把精度做上去**（约 4 小时）：00 → 02 → 03。
  标签分配 + RTMDet 的设计取舍，是当前 CNN 系检测器里性价比最高的两块。
- **面向 DETR / 端到端方向**（约 4 小时）：00 → 04 → 然后直接进 C54。
  本课的 04 讲的是「RT-DETR 怎么做到实时」，C54 讲的是「集合预测为什么成立」。
- **完整路径**：00 → 01 → 02 → 03 → 04 → 05，按顺序读，后面的模块会反复引用前面的结论。

每个模块的 notebook 都可以独立运行，纯 numpy、CPU、几秒到几十秒出结果。
练习都带 `assert` 判分，做错了会立刻告诉你。

## 与相邻课程的分工

| 课程 | 它讲什么 | 与本课的关系 |
|---|---|---|
| **C18 · 计算机视觉** | 检测的基础（IoU / NMS / mAP / anchor / FPN / 两阶段） | **前置**。本课默认你知道 IoU 与 NMS 是什么，直接从「实时约束下怎么改」开始。 |
| **C54 · 端到端集合预测（DETR 家族）** | 匈牙利匹配、集合损失、object query、收敛难题 | **姊妹课**。本课 04 是 RT-DETR 的**工程解剖**（怎么变快），C54 是**原理深挖**（为什么能不用 NMS）。两课交叉引用。 |
| **C56 · 检测数据增强工程** | Mosaic / MixUp / Copy-Paste / 增强流水线 | 本课 01 会提到 Mosaic 与 close-mosaic 对 YOLO 的贡献量，细节在 C56。 |
| **C57 · 小目标检测** | IoU 对位移的敏感性、NWD、FPN 层级、切片推理 | 本课 02 会证明「固定 IoU 阈值对小目标不公平」，C57 把这条线走到底。TSR 是典型小目标任务。 |
| **C60 · 车端部署与一致性** | TensorRT、INT8 校准、后处理对齐、p99 延迟 | 本课 05 给的是**选型层面**的延迟账，C60 给的是**落地层面**的实测与对齐方法。 |
| **C61 · 检测工程实战与面试实务** | 实验设计、误差分析、调试手册、面试题库 | 本课 04/05 给的答案骨架会在 C61 被系统化成题库。 |
| **C27 · 模型压缩** | 量化算法本身 | 本课只用到量化的**误差量级**作为延迟-精度权衡的输入。 |

## 环境

见 `requirements.txt`。**纯 numpy + matplotlib，CPU 可跑，不需要 GPU，也不需要装 torch / mmdetection / ultralytics / TensorRT。**

本课复现的是这些系统的**机制与账本**：

- 分配规则（ATSS 的均值+标准差、SimOTA 的代价矩阵与 dynamic-k、TaskAligned 的 t = s^α·u^β）
- 融合的代数等价（Conv+BN 融合、多分支合并——可逐元素验证）
- FLOPs 与访存量（hybrid encoder vs 全尺度 attention、加大核的真实代价）
- 延迟分布（NMS 随目标数的增长、p50/p99 的模拟）

这些恰恰是可迁移的那部分——框架版本会变，账不会。
每个模块末尾有一个 🧪 **真实工程胶囊**，把当天的结论翻译成可原样复制的
`mmdetection` / `ultralytics` / `RT-DETR` 配置片段与 `trtexec` 命令。

## ⚠️ 关于本课里的数字

讲解中引用的 AP / 延迟数字来自各论文原文与官方仓库的公开表格，**用于说明量级与相对关系，不是复现结果**。
不同的卡、驱动、TensorRT 版本、batch size、是否含 NMS/预处理，都会让绝对数字变化 20%–200%。
模块 05 会专门讲清楚这些数字为什么不可比、以及一份可比的测量报告应该长什么样。
**在面试里引用具体数字时，一定要同时说出测量条件**——这本身就是加分项。

配套：[术语词典](glossary.md) · [参考清单](references.md)
"""

REQUIREMENTS = r"""
# 实时检测器架构 —— 依赖清单
# 纯 numpy + 标准库，CPU 可跑（assert 全过），单个 notebook 通常几秒到几十秒。
# **不需要 GPU，也不需要装 torch / mmdetection / ultralytics / TensorRT**：
# 本课复现的是这些系统的机制与账本（标签分配规则、Conv+BN 与多分支的代数等价、
# FLOPs 与访存量、NMS 的耗时曲线与 p50/p99 分布），而不是调用它们的 API。
# 每个模块末尾的 🧪 胶囊给出真实仓库里的配置片段与命令。

numpy          # 核心：ATSS/SimOTA/TaskAligned 分配、重参数化融合、ERF 数值实验、延迟模型
matplotlib     # 画延迟-精度帕累托前沿、IoU-位移敏感性曲线、ERF 热力图、p50/p99 分布
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel

# —— 可选，只影响展示不影响 assert ——
# pandas       # 选型对比表格的排版

# —— 以下是真机上会用到的（本环境不装，胶囊里给出用法）——
# torch>=2.4                  # 模块 01/03：重参数化与大核卷积的真实实现
# mmdet>=3.0 mmengine         # 模块 02/03：ATSS / SimOTA / RTMDet 的官方实现与配置
# ultralytics                 # 模块 01：YOLOv8/v10 的训练与导出
# onnx onnxruntime            # 模块 04/05：导出与端到端延迟测量
# tensorrt                    # 模块 05：FP16/INT8 engine 与 trtexec profile
# pycocotools                 # 模块 05：mAP 评测（AP50 / AP50-95 / APs-APm-APl）
"""

GLOSSARY = r"""
# 术语词典 · Glossary（实时检测器架构）

> 按主题分组。每条给出：**英文 / 中文 / 一句话定义 / 为什么重要 / 常见误解**。
> 读论文、看 mmdetection 配置、或在面试里被追问时回这里查；英文术语保留原文。
> 与相邻课程的分工见 [README](README.md)：检测基础在 C18、DETR 原理在 C54、小目标在 C57、部署在 C60。

---

## 一 · 检测范式与基础 · Detection Paradigms

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| one-stage detector | 单阶段检测器 | 直接在密集网格上同时预测类别与框，没有单独的候选框生成阶段。 | 少一个阶段就少一次不确定耗时，是实时检测的默认形态。 | 以为单阶段就一定不如两阶段准——自 RetinaNet/FCOS 起这个结论早已不成立，差距来自正负样本失衡而非阶段数。 |
| two-stage detector | 两阶段检测器 | 先出 proposal（RPN），再对每个 proposal 做精细分类与回归。 | 提供了「先粗后精」的思想，Cascade / 两级 TSR 方案都是它的变体。 | 以为它彻底过时了。在**类别极多、需要高分辨率 crop** 的场景（正是 TSR），两级仍是量产首选。 |
| dense prediction | 密集预测 | 在特征图的每个位置都输出预测，位置数 = ΣH·W（×anchor 数）。 | 密集意味着必然有大量重复框，**这才是 NMS 存在的原因**。 | 以为重复框是模型「学不好」。不是——一对多分配在训练时就教会了模型让多个位置认领同一目标。 |
| anchor-based | 基于锚框 | 每个位置预置若干固定长宽比/尺度的先验框，网络回归相对偏移。 | 把「预测框」变成「预测残差」，早期极大降低了回归难度。 | 以为 anchor 是必需品。anchor 的真实作用是**提供尺度先验 + 定义正负样本**，后者可以被更好的分配策略替代。 |
| anchor-free | 无锚框 | 直接从位置回归到框的四边距离（FCOS 式）或中心+宽高（CenterNet 式）。 | 去掉了 anchor 的超参（尺度/比例/数量/匹配阈值），也减少了输出通道数与后处理复杂度。 | 以为 anchor-free 的收益来自「去掉 anchor」。**YOLOX 论文里 anchor-free 本身只涨约 +0.9 AP，真正的大头是 SimOTA**。 |
| FCOS | 全卷积单阶段检测 | anchor-free 的代表：每个位置回归 (l,t,r,b) 四个距离，配 centerness 分支。 | 现代 anchor-free 检测头的模板，RTMDet / YOLOX 的头都是它的后代。 | 以为 centerness 是可有可无的小分支。去掉它会让远离中心的低质量框在 NMS 里排到前面，AP 明显下降。 |
| centerness | 中心度 | 一个 0–1 的分支，度量当前位置距离目标中心有多近，推理时乘进分数。 | 它是**分类分数与定位质量对齐**这条主线的第一个尝试，后续被 TaskAligned 等取代。 | 以为它和 IoU 预测分支等价。centerness 只用几何位置估计，不看实际回归质量，所以更粗糙。 |
| IoU | 交并比 | 两个框交集面积 ÷ 并集面积。 | 检测里几乎所有的匹配、评测、后处理都建立在它上面。 | 以为 IoU 对所有尺度一样敏感。**8×8 的框位移 2 px，IoU 从 1.0 掉到 0.39；64×64 的框同样位移还有 0.88**——这是小目标难的根因之一。 |
| GIoU / DIoU / CIoU | 广义/距离/完备交并比 | IoU 的可导变体：GIoU 补上不相交时的梯度，DIoU 加中心距离项，CIoU 再加长宽比一致性。 | 直接用 IoU 做损失在框不相交时梯度为 0，训练前期无法收敛。 | 以为越"完备"越好。CIoU 的长宽比项在**极端长宽比目标**上可能不稳定，实践中 GIoU/DIoU 常常够用。 |
| objectness | 目标性/前景分 | 一个独立分支预测「这个位置有没有物体」，与类别分数相乘。 | YOLO 系的传统设计，让背景位置能被一票否决。 | 以为它一定存在。**YOLOv8 起就去掉了 objectness 分支**，改为纯分类分数 + DFL，因为 TaskAligned 分配已经承担了对齐职责。 |
| coupled head | 耦合头 | 分类与回归共用同一串卷积，最后一层才分叉。 | 参数少、快，是 YOLOv3–v5 的做法。 | 以为耦合只是省参数。**分类要的是平移不变、回归要的是平移敏感**，两者的最优特征本就冲突，耦合是精度损失的来源。 |
| decoupled head | 解耦头 | 分类与回归各走一条独立的卷积分支。 | YOLOX 的三件套之一，**收敛更快且 AP 有稳定提升**，现已是标配。 | 以为解耦必然增加很多计算。用 1×1 降维后再分叉，代价可以控制在 1–2% FLOPs 以内。 |
| Focal Loss | 焦点损失 | 用 (1-p)^γ 对易分样本降权的交叉熵变体，解决前景-背景极度失衡。 | 单阶段检测器能追平两阶段的关键一步；也是「软性 OHEM」的代表。 | 以为 γ 越大越好。γ 过大会让模型只盯着极难样本，而**难样本里往往混着标注噪声**，反而掉点。 |
| DFL | 分布焦点损失 | 把框的每条边建模成一个离散分布（在若干候选值上的 softmax），而不是一个标量。 | 边界模糊时（遮挡、反光）单点回归会强行给一个值，分布表示能表达不确定性，是 GFL/YOLOv8/D-FINE 的共同选择。 | 以为它只是「换了个损失」。它同时改变了**输出通道数**（每边 reg_max+1 个）与后处理（要做期望），部署侧要跟着改。 |
| mAP / AP50 / AP50-95 | 平均精度 | 各类别 AP 的均值；AP50 用单一 IoU=0.5 阈值，AP50-95 在 0.50:0.05:0.95 上取平均。 | 检测的通用记分牌，也是所有论文表格的横轴。 | 以为 mAP 高就一定好用。mAP 平均掉了关键类别、与距离无关、不含时序，**TSR 场景必须做分桶评测**（C55/C57 展开）。 |
| APs / APm / APl | 小/中/大目标 AP | COCO 按面积 <32²、32²–96²、>96² 分的三档 AP。 | 是唯一在标准指标里能看出小目标表现的入口。 | 以为 APs 低只是「小目标难」。它更可能是**标签分配对小目标不公平**造成的，改分配比改架构更有效。 |
| stride | 步长/下采样率 | 特征图相对原图的缩小倍数（P3=8、P4=16、P5=32）。 | 决定了「多大的目标在这层还剩几个格子」，直接决定可检测尺寸下界。 | 以为加大 stride 只影响速度。stride 32 时一个 8 px 的目标只占 **0.25 个格子**，信息在下采样里已经没了，再好的头也救不回来。 |

---

## 二 · 标签分配 · Label Assignment

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| label assignment | 标签分配 | 决定特征图上哪些位置（或 anchor）在这一步是正样本、对应哪个 GT。 | **它决定梯度从哪里来**，是检测器里性价比最高的改动点：同 backbone 换分配能差 3–5 AP。 | 以为它是训练细节。它是**训练目标的定义**，改分配等于换了一个优化问题。 |
| static assignment | 静态分配 | 分配规则只依赖 GT 与 anchor 的几何关系（如 MaxIoU、中心落在框内），与网络当前预测无关。 | 简单、可复现、无训练不稳定问题。 | 以为「与预测无关」是缺点。静态分配在训练**极早期**反而更稳，很多实现会先静态几个 epoch 再切动态。 |
| dynamic assignment | 动态分配 | 分配规则依赖网络当前的预测质量（分类分、IoU），随训练演化。 | 让模型自己决定「哪些位置更容易学好」，是 ATSS 之后所有 SOTA 的共同选择。 | 以为动态一定更好。训练极早期预测全是噪声，**纯动态分配会放大随机性**，所以都要配中心先验或 warmup。 |
| MaxIoU assignment | 最大 IoU 分配 | 与 GT 的 IoU 超过阈值（如 0.5）的 anchor 为正，低于另一阈值为负，中间忽略。 | Faster R-CNN / RetinaNet 的经典做法，理解它才能理解后面所有改进的动机。 | 以为一个阈值对所有目标公平。**同一个 0.5 阈值下，大目标能匹配到几十个 anchor，小目标可能一个都匹配不到**。 |
| ATSS | 自适应训练样本选择 | 对每个 GT，在每层取中心最近的 k 个候选，用这批候选 IoU 的 **均值 + 标准差** 作为该 GT 的专属阈值。 | 第一次证明了「anchor-based 与 anchor-free 的性能差距其实全部来自分配方式」。 | 以为它是「自适应的复杂算法」。它只有几行统计量计算，**没有任何可学参数**，这正是它优雅的地方。 |
| OTA | 最优传输分配 | 把分配写成最优传输问题：GT 是供给方、anchor 是需求方，用 Sinkhorn 求全局最优的分配方案。 | 提供了**全局视角**：分配不该逐 GT 独立决定，密集重叠场景下必须全局协调。 | 以为 Sinkhorn 很慢所以不实用。慢是真的（每步迭代几十次），**这正是 SimOTA 存在的理由**。 |
| SimOTA | 简化最优传输分配 | OTA 的贪心近似：算代价矩阵 → 每个 GT 按代价取 top-k → k 由 dynamic-k 决定 → 冲突位置归给代价最小的 GT。 | YOLOX 的核心贡献，**三件套里贡献最大的一件（约 +2.3 AP）**，且几乎不增加训练时间。 | 以为它和 OTA 效果差不多所以 OTA 没意义。SimOTA 丢掉了全局最优性，在**极密集场景**下仍逊于 OTA。 |
| dynamic-k | 动态 k | 每个 GT 的正样本数不固定，而是取「该 GT 与候选 anchor 的 top-q 个 IoU 之和」向下取整。 | 大目标/易学目标自然拿到更多正样本，小目标/难目标拿到少但精准的，**比固定 k 公平得多**。 | 以为 k 是超参。它是**从数据里算出来的**；真正的超参是 q（通常 10–20）和 top-k 的候选池大小。 |
| cost matrix | 代价矩阵 | 尺寸 (GT 数 × 候选 anchor 数) 的矩阵，每个元素 = 分类代价 + λ·回归代价（+ 中心先验惩罚）。 | 所有现代分配的共同骨架；改分配策略基本就是改这个矩阵的定义。 | 以为分类代价该用 log 概率。SimOTA/DETR 里常**直接用概率或 focal 形式**，log 会让极低分样本产生巨大代价而主导矩阵。 |
| center prior | 中心先验 | 只允许落在 GT 中心一定半径内的位置成为候选，或对偏离中心的位置加惩罚。 | 训练早期预测不可信时，**几何先验是唯一可靠的信号**，它防止动态分配在初期发散。 | 以为它是 anchor-free 的遗留。RTMDet 的软代价里仍保留了它，且是稳定性的关键。 |
| TaskAligned assignment (TAL) | 任务对齐分配 | 用对齐度 **t = s^α · u^β**（s=分类分，u=预测框与 GT 的 IoU）排序，取 top-k 为正。 | 直接强迫「分数高」和「框准」同时成立，**修的是 NMS 阶段按分数排序却选到定位差的框**这个经典错配。 | 以为 α、β 只是权重。它们控制的是**任务偏好**：β 大更看重定位，α 大更看重分类置信；YOLOv8 默认 α=0.5, β=6.0，是强定位偏好。 |
| TOOD | 任务对齐单阶段检测 | 提出 TAL 与任务对齐头（T-Head）的论文。 | TAL 后来被 YOLOv8 / PP-YOLOE / RT-DETR 系广泛采用，是当前事实标准之一。 | 以为 TOOD 只是分配方法。它的 T-Head（用任务交互特征再分出两支）同样重要，但被采用得少。 |
| dynamic soft label assignment | 动态软标签分配 | RTMDet 的分配：代价里的分类项不再用 0/1 硬标签，而用 **IoU 作为软目标**（如 CE(pred, IoU)）。 | 把「差一点」和「差很多」区分开来，让代价矩阵更平滑、分配更稳定。 | 以为软标签只是标签平滑。它是**用定位质量当分类目标**，本质上和 TAL 同源，都在做质量对齐。 |
| one-to-many | 一对多 | 一个 GT 匹配多个正样本位置。 | 监督信号密集 → 收敛快、梯度稳，**这是训练侧的最优选择**。 | 以为一对多是「落后的」。DETR 系后来集体加回一对多辅助分支（Group/H/Co-DETR）就是为了补监督密度。 |
| one-to-one | 一对一 | 一个 GT 只匹配一个预测。 | **推理侧不需要 NMS 的唯一前提**：训练时就压制了重复，而不是推理时删重复。 | 以为一对一训练效果更好。恰恰相反——它监督稀疏、收敛慢，**一对一是推理需求，不是训练最优**。这句话是面试的关键论点。 |
| consistent dual assignments | 一致双分配 | YOLOv10 的做法：训练时同时挂一个一对多头（提供密集监督）和一个一对一头（推理用），并让两者的分配<em>度量一致</em>。 | 第一次在 YOLO 体系里让「无 NMS」真正可用：既有一对多的收敛速度，又有一对一的推理形态。 | 以为「双头」就够了。**关键在"一致"**：如果两个头用不同的匹配度量，一对一头选中的样本在一对多头里排名靠后，两者会互相打架。 |
| de-conflict | 去冲突 | 当一个 anchor 被多个 GT 同时选中时，归给代价最小（或 IoU 最大）的那个。 | 密集重叠场景必须处理，否则同一位置会收到互相矛盾的梯度。 | 实现时容易漏。**漏了不会报错**，只会让密集场景 AP 莫名其妙低几个点——是从零实现 SimOTA 最常见的 bug。 |
| positive sample scarcity | 正样本稀缺 | 小目标在固定阈值下几乎匹配不到正样本的现象。 | 解释了为什么 APs 总是远低于 APl，也解释了为什么动态分配对小目标收益最大。 | 以为多加 anchor 就能解决。加 anchor 只是提高了命中概率，**阈值的不公平性没变**，改分配才是对症下药。 |

---

## 三 · 结构与算子 · Architecture & Operators

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| backbone / neck / head | 主干 / 颈部 / 头 | 特征提取 / 多尺度融合 / 预测输出的三段式结构。 | 现代检测器的通用骨架，论文的消融表基本按这三段组织。 | 以为 backbone 最重要。在实时检测里，**neck 与 head 的延迟占比常常超过 40%**，优化空间反而更大。 |
| CSPNet | 跨阶段局部网络 | 把特征按通道切成两半，只让一半过密集的残差块，最后 concat。 | YOLOv4/v5/v8 的基础模块。**它省的主要是访存与显存，不只是 FLOPs**。 | 以为 CSP 是为了减 FLOPs。它的原始动机是**减少重复的梯度信息**，实际收益里访存降低占很大比重。 |
| ELAN / E-ELAN | 高效层聚合网络 | YOLOv7 的模块：控制最短/最长梯度路径长度，让更深的网络仍能有效学习。 | 说明「怎么连」与「连多少层」同样重要。 | 以为它只是又一个 CSP 变体。它的设计依据是**梯度路径长度分析**，出发点不同。 |
| C3 / C2f | YOLOv5 / v8 的核心模块 | C3 = 三个卷积 + n 个 Bottleneck；C2f 把所有中间输出都 concat 出来，梯度流更丰富。 | C2f 是 YOLOv8 的主要结构改动，用略高的访存换更好的特征复用。 | 以为 C2f 比 C3 更省。**C2f 的访存更高**，它换来的是精度，在带宽受限的车端硬件上要实测。 |
| SPP / SPPF | 空间金字塔池化 (快速版) | 用多个不同 kernel 的 maxpool 并联（SPP）或串联（SPPF）扩大感受野。 | 几乎零参数地把感受野拉满，是 YOLO 系的标配收尾模块。 | 以为 SPPF 只是「写法优化」。串联三个 5×5 与并联 5/9/13 **数学上等价**，但 SPPF 快 2 倍以上——这是纯工程胜利。 |
| FPN | 特征金字塔网络 | 自顶向下把高层语义传给低层，让每层都有语义又有分辨率。 | 多尺度检测的基础设施，没有它小目标基本无解。 | 以为 FPN 就够了。**FPN 只有自顶向下**，低层的精确定位信息传不上去，所以才有了 PAN。 |
| PAN / PANet | 路径聚合网络 | 在 FPN 之上再加一条自底向上的路径。 | 把低层的定位细节送回高层，YOLOv4 起成为标配 neck。 | 以为 PAN 是 FPN 的替代。它是 **FPN 之后再加一遍**，两条路径都在。 |
| BiFPN | 双向特征金字塔 | 带可学习权重的双向多次融合（EfficientDet）。 | 引入了「不同尺度的贡献不该等权」这个观点。 | 以为它一定更好。BiFPN 的重复堆叠对延迟不友好，**实时检测器很少用**。 |
| re-parameterization | 结构重参数化 | 训练时用多分支结构，推理前用**代数恒等变换**把多分支合并成单个卷积。 | 少数几个「训练收益完全免费带到推理端」的技巧，是 YOLOv6/v7 的核心。 | 以为是近似或蒸馏。它是**精确恒等变换**，可以逐元素 `assert np.allclose` 验证；notebook 里就会做这件事。 |
| RepVGG | 重参数化 VGG | 训练用 3×3 + 1×1 + identity 三分支，推理合并成一个 3×3。 | 重参数化的原型；证明了「推理时的简单结构」与「训练时的复杂结构」可以解耦。 | 以为合并后精度会掉。合并是恒等的，**精度一点不掉**；掉点只可能来自后续量化（多分支合并后数值范围变大）。 |
| Conv+BN fusion | 卷积-批归一化融合 | 把 BN 的 γ/β/μ/σ 折进卷积的 W 和 b：W' = γW/√(σ²+ε)，b' = β - γμ/√(σ²+ε)。 | 推理时省掉一整层的读写，是所有推理引擎的第一个优化。 | 以为它只在部署时做。**重参数化的第一步就是它**，训练框架里也要显式实现。 |
| depthwise conv | 深度可分离卷积 | 每个通道独立卷积，参数量与 FLOPs 是普通卷积的 1/C_out。 | 让「扩大 kernel」变得几乎免费——5×5 depthwise 的参数只比 3×3 多 16/9 倍**的一小部分总量**。 | 以为 depthwise 一定更快。它是**访存受限**算子，算术强度低，在高带宽 GPU 上加速比远低于 FLOPs 比值。 |
| large-kernel conv | 大核卷积 | 用 5×5、7×7 甚至 31×31 的卷积核替代堆叠的 3×3。 | RTMDet 用 5×5 depthwise 显著扩大有效感受野，代价极小。 | 以为「堆叠 3×3 等价于大核」。理论感受野等价，但**有效感受野（ERF）不等价**——堆叠 3×3 的 ERF 呈高斯衰减，中心权重远高于边缘。 |
| ERF | 有效感受野 | 输出对输入的梯度实际非零的区域，通常远小于理论感受野且呈近高斯分布。 | 解释了为什么大核有效、为什么加深不等于扩大视野。**本课 03 用梯度回传法实测它**。 | 以为理论感受野就是模型「能看到」的范围。ERF 常常只有理论值的 **√n 量级**（n 为层数）。 |
| CSPNeXt | RTMDet 的主干 | CSP 骨架 + 5×5 depthwise 大核 block，配 SiLU。 | RTMDet 的主干与颈部使用同一套 block，简化了缩放与实现。 | 以为它只是 CSPDarknet 换核。**主干与颈部结构统一**是它更重要的设计决策，直接影响缩放的可预测性。 |
| shared head + per-level BN | 共享头 + 每层独立 BN | 检测头的卷积权重跨 FPN 各层共享，但 BN 的统计量每层单独一份。 | 共享的是「怎么判断」，不共享的是「各层特征的尺度统计」——**这个拆分是 RTMDet 的关键细节**。 | 以为全共享或全不共享。全共享会因各层激活分布差异大而掉点，全不共享则参数翻数倍。 |
| model scaling | 模型缩放 | 按深度（层数）、宽度（通道）、分辨率三个维度成组放大/缩小同一架构。 | 一套设计覆盖 tiny→x，量产团队可以按硬件档位挑，而不必重新设计。 | 以为等比放大就行。三个维度的**边际收益不同**：小模型加宽度更划算，大模型加深度更划算，分辨率对小目标收益最大但代价是平方级。 |
| deep supervision / aux head | 深监督 / 辅助头 | 训练时在中间层挂额外的检测头算损失，推理时丢掉。 | YOLOv7 的 coarse-to-fine 辅助头；训练成本换精度，推理零成本。 | 以为辅助头和主头该用同一套标签。YOLOv7 特意给辅助头**更宽松的分配**（coarse），主头用严格的（fine）。 |

---

## 四 · DETR 系与端到端 · DETR Family & End-to-End

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| set prediction | 集合预测 | 一次输出一个**不含重复**的目标集合，而不是密集预测再去重。 | DETR 的核心命题；它把去重从推理期挪到了训练期。 | 以为「集合」只是输出形式。它要求损失函数对预测顺序不变，**这才逼出了匈牙利匹配**。 |
| Hungarian matching | 匈牙利匹配 | 在预测与 GT 之间求代价最小的一对一二分匹配（Kuhn-Munkres，O(n³)）。 | 让损失能在无序集合之间定义；是一对一分配的算法实现。 | 以为它慢所以影响推理。**它只在训练时用**，推理时完全不出现。 |
| object query | 目标查询 | decoder 的一组可学习向量，每个负责「认领」一个目标。 | DETR 的输出槽位；数量 N 必须大于单图最大目标数。 | 以为 query 是特征。它更接近**可学习的位置先验**（DAB-DETR 直接把它解释成 4D 框），这也是它和 anchor 的真正联系。 |
| deformable attention | 可变形注意力 | 每个 query 只在少数 K 个可学习采样点上取特征，而不是与全图做 attention。 | 把 attention 的复杂度从 O(HW) 降到 O(K)，是 DETR 能做到多尺度与实时的前提。 | 以为它只是「稀疏 attention」。**采样位置是学出来的且带偏移**，所以它同时提供了空间自适应性。 |
| hybrid encoder | 混合编码器 | RT-DETR 的 encoder：只在最高层做 transformer，跨尺度融合改用 CNN。 | 直接把 encoder 的计算量砍掉一大截，是 RT-DETR 提速的主要来源。 | 以为是「减层数」这种粗暴做法。它的依据是**只有高层语义需要全局交互**，低层的高分辨率 token 做 self-attention 性价比极低。 |
| AIFI | 尺度内特征交互 | RT-DETR 中只作用在 S5（最高层、分辨率最低）的 self-attention 模块。 | S5 的 token 数只有 S3 的 1/16，在这里做 attention 才划得来。 | 以为 AIFI 能搬到低层。搬下去 FLOPs 按 token 数平方增长，**S3 上做 self-attention 的代价是 S5 的 256 倍**。 |
| CCFF | 跨尺度特征融合 | RT-DETR 中用 CNN（RepBlock 等）做多尺度融合的模块，替代 encoder 里的跨尺度 attention。 | 融合这件事 CNN 做得又快又好，没必要用 attention。 | 以为 CCFF 就是 PAN。结构相近但用了重参数化 block，**推理时会被合并**。 |
| query selection | 查询选择 | 用 encoder 输出的 token 初始化 decoder 的 query（两阶段做法），而不是纯随机初始化。 | 给 decoder 一个好起点，显著加快收敛并提升精度。 | 以为随便取 top-k 分类分就行——这正是下一条要修的问题。 |
| IoU-aware query selection | IoU 感知的查询选择 | 训练时在分类目标里注入 IoU 约束，使得高分类分的 token 同时也定位准；选 query 时才不会选错。 | RT-DETR 的关键改进之一：**按分类分选 query 会大量选到「分高但框歪」的 token**。 | 以为它是推理时的重排。它的作用点在**训练目标**上，推理时的选择逻辑没变。 |
| uncertainty-minimal query selection | 不确定性最小的查询选择 | RT-DETR 论文对上述机制的正式表述：选择分类与定位分布差异（不确定性）最小的 token。 | 给了「为什么这样选」一个可度量的定义。 | 以为和 IoU-aware 是两件事。它们是同一机制的两种表述。 |
| NMS-free | 无 NMS | 推理时不需要非极大值抑制。 | **主要收益是延迟方差可控**（NMS 的耗时随目标数与阈值波动），其次才是均值。 | 以为无 NMS = 更快。在目标很少时 NMS 只要零点几毫秒，**无 NMS 甚至可能因 decoder 更慢**；它买的是稳定性。 |
| flexible decoder depth | 可调解码器深度 | 推理时可以只跑前 k 层 decoder（因为每层都有辅助损失，每层输出都可用）。 | **同一份权重直接给出多档速度-精度组合，不用重训、不用重新导出训练流程**——多硬件平台上这是决定性优势。 | 以为砍层就等比掉点。实际上前几层收益最大，**砍掉最后 1–2 层往往只掉 0.2–0.5 AP**。 |
| denoising query (DN) | 去噪查询 | 把加噪的 GT 框作为额外 query 送进 decoder 学去噪，绕开匹配的不稳定性。 | DN-DETR/DINO 的关键加速手段；本课只点到，C54 详讲。 | 以为它是数据增强。它是**优化技巧**——给出一条不经过匈牙利匹配的稳定梯度通路。 |
| RT-DETRv2 | RT-DETR 第二版 | 引入离散采样算子（便于部署）、灵活的采样点数配置、以及一批「免费」训练技巧。 | 主要是**部署友好性**的改进：grid_sample 在某些推理引擎上支持不佳。 | 以为 v2 主要提精度。它的重点是可部署性与训练配方，精度提升相对温和。 |
| D-FINE | 细粒度分布优化检测器 | 把框回归重构成对「边界分布」的迭代细化（FDR），并配自蒸馏（GO-LSD）。 | 在 RT-DETR 基础上继续推进帕累托前沿，是目前实时端到端检测的强基线之一。 | 以为它换了架构。它**沿用 RT-DETR 骨架**，改的是回归的表示与监督方式。 |

---

## 五 · 后处理与延迟 · Post-processing & Latency

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| NMS | 非极大值抑制 | 按分数排序，逐个保留最高分框并抑制与其 IoU 超阈值的框。 | 密集预测的必备后处理；也是端到端延迟里**唯一耗时随场景变化**的一段。 | 以为 NMS 耗时可忽略。目标数从 10 涨到 300 时，朴素实现的耗时可以涨**两个数量级**（O(n²) 比较）。 |
| Soft-NMS | 软化非极大值抑制 | 不直接删除重叠框，而是按 IoU 衰减其分数。 | 密集遮挡场景召回更高。 | 以为可以无脑替换。它**增加了保留框数**，下游（跟踪、融合）的负担变大，且延迟更高。 |
| class-wise vs class-agnostic NMS | 分类别 / 类别无关 NMS | 前者只在同类框之间抑制，后者跨类别一起抑制。 | 直接影响结果：类别无关会删掉「同一位置不同类」的合理预测。 | 以为两者差别很小。在**类别高度相似**的场景（限速 60 / 80）差别巨大，TSR 必须用 class-wise。 |
| batched NMS | 批量 NMS | 用「给每个类别的框加一个巨大的类别偏移」把 class-wise NMS 变成一次 class-agnostic 调用。 | 工程上把循环变成一次调用，是所有主流实现的做法。 | 以为偏移量随便取。偏移必须**大于图像最大边长**，否则不同类的框会意外互相抑制。 |
| top-k pre-filter | top-k 预筛选 | NMS 前先按分数取前 k 个（如 1000）候选。 | 把 NMS 的 O(n²) 上界钉死，是延迟可控的关键。 | 以为它无损。**k 设小了会截断密集场景的真实目标**，TSR 里一屏几十个标志时要实测。 |
| score threshold | 分数阈值 | NMS 前丢弃低于阈值的框。 | 同时影响精度、召回和延迟——阈值越低，进入 NMS 的框越多。 | 以为评测阈值和部署阈值该一样。评测要用极低阈值（0.001）才能画完整 PR 曲线，**部署用 0.25–0.4**，两者必须分开配置。 |
| latency budget | 延迟预算 | 从传感器出图到下游可用之间允许的总时间。 | 30 FPS 意味着 33 ms 一帧，而**感知只是其中一环**，还要留给融合、跟踪、规控。 | 以为「30 FPS」就是给了检测器 33 ms。实际分到检测的常常只有 **10–15 ms**，且要在多任务共享的算力上完成。 |
| end-to-end latency | 端到端延迟 | 预处理 + H2D 拷贝 + 推理 + NMS + 后处理 + D2H 的总和。 | **只报「推理」那一段是最常见的自欺**；预处理与拷贝加起来常占 30%+。 | 以为拷贝可以忽略。1920×1080×3 的 uint8 图 H2D 一次约 6 MB，在 PCIe 上就是毫秒量级。 |
| H2D / D2H | 主机到设备 / 设备到主机 | CPU 内存与 GPU 显存之间的数据拷贝。 | 常常是端到端延迟的隐形大头，零拷贝/统一内存是车端常用优化。 | 以为异步就等于免费。异步只是**重叠**了拷贝与计算，总带宽占用没变。 |
| throughput vs latency | 吞吐 vs 延迟 | 吞吐是单位时间处理量（可用大 batch 提升），延迟是单帧从进到出的时间。 | 车端只关心 **batch=1 的延迟**，论文常报大 batch 的吞吐，两者不可换算。 | 以为 FPS = 1000/延迟。用 batch=32 测出的 FPS 除回去得到的「延迟」在车上根本达不到。 |
| p50 / p99 latency | 中位 / 99 分位延迟 | 延迟分布的分位数。 | **安全系统关心的是尾延迟**：p99 超预算意味着每 100 帧就丢一帧。 | 以为均值够用。含 NMS 的方案均值可能很好看，但 p99 在密集场景会翻倍。 |
| FPS | 每秒帧数 | 吞吐指标。 | 论文表格的通用横轴。 | 以为可以跨论文比较。**batch、是否含 NMS、是否含预处理、精度（fp32/fp16/int8）、GPU 型号、TensorRT 版本**——六个维度任一不同就不可比。 |
| Pareto frontier | 帕累托前沿 | 在「延迟-精度」平面上，不存在另一个点同时更快且更准的那批点。 | 选型的正确起点：**先把被支配的模型全部剔除**，再在前沿上按预算取点。 | 以为前沿上的点都「一样好」。前沿只说明不可比较，**选哪个仍要看预算、可维护性、硬件支持**。 |
| dominated | 被支配 | 存在另一个模型同时更快且更准。 | 被支配的模型没有任何理由被选，直接出局。 | 以为「我的模型某个指标最好」就不会被支配。要**同时**在延迟和精度上都不落后才算不被支配。 |
| memory-bound | 访存受限 | 算子的瓶颈是数据搬运而非算术。 | 解释了为什么 FLOPs 降一半延迟只降 10%——depthwise、逐元素算子、concat 都是访存受限。 | 以为 FLOPs 就是延迟的代理。**在现代 GPU 上 FLOPs 与延迟的相关性可能低于 0.5**，必须实测。 |
| layer fusion | 层融合 | 推理引擎把 Conv+BN+激活等合并成一个 kernel。 | 减少中间张量的读写，是 TensorRT 提速的主要来源之一。 | 以为融合总会发生。**中间有 reshape、非标准激活、或输出被多处引用时融合会失败**，要看引擎的分区日志。 |
| train-deploy consistency | 训练-部署一致性 | 部署侧的预处理/后处理与训练侧数值等价。 | 不一致会让「离线 0.82 的 mAP 在车上像 0.6」；本课只点到，C60 详讲。 | 以为「跑通了」就是一致。BGR/RGB、resize 插值、letterbox padding 值都能不报错地毁掉几个点。 |
"""

REFERENCES = r"""
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
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足，请补充")
