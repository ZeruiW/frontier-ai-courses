#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C52 · 工业研究工程实务。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c52_m00, c52_m01, c52_m02, c52_m03, c52_m04, c52_m05

CID = "C52_Industrial_Research_Practice_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "五项「没有归属却天天要用」的技能，与贯穿全课的三条纪律——数值对拍、版本即环境、边界要显式；交付契约对象与环境指纹工具",
     c52_m00),
    ("01_tensorflow", "01_讲解.html", "01_tensorflow_mental_model.ipynb",
     "01 · TensorFlow / Keras 心智模型",
     "静态图 vs 动态图 · Python 只在追踪时执行一次（能解释 80% 的诡异行为）· 重追踪是头号性能杀手 · Keras 三种 API · 与 PyTorch 逐概念对照 · 三个「不报错但数值错」的默认值差异",
     c52_m01),
    ("02_weight_porting", "02_讲解.html", "02_weight_porting.ipynb",
     "02 · 框架迁移与权重对齐",
     "迁移的价值是把模糊的性能问题变成可二分定位的数值问题 · reshape ≠ transpose · 方阵层让形状检查失效 · RNN 门顺序 · 漏参数比映射错更危险 · 八步 checklist 与逐层对拍",
     c52_m02),
    ("03_export_runtime", "03_讲解.html", "03_export_runtime.ipynb",
     "03 · 模型导出与推理运行时",
     "ONNX 的图/opset/动态轴/权重四要素 · 不设动态轴就被写死 · 算子不支持的四条出路 · 静默回退（转了但没变快）· 多形状对拍与边界测试 · 量化容差要按量化误差设",
     c52_m03),
    ("04_gpu_workflow", "04_讲解.html", "04_gpu_workflow.ipynb",
     "04 · 真机 GPU 工作流",
     "显存是算术题（优化器状态 12N 比参数还大）· OOM 诊断树按成本排序 · 「跑了 500 步才 OOM」是长样本不是泄漏 · 四层版本链与 CUDA_LAUNCH_BLOCKING · 看利用率的波动模式 · MFU 双向估算",
     c52_m04),
    ("05_research_output", "05_讲解.html", "05_research_output_ip.ipynb",
     "05 · 研究产出与知识产权",
     "公开即丧失新颖性（不可逆）· 算法 + 技术效果 · 「非预期效果」是最有力论据 · 权利要求宽窄与绕过分析 · AGPL 打破「不分发就没义务」· 内部演示 ≠ 学术报告（结论先行 + 明确 ask）",
     c52_m05),
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
        title="工业研究工程实务",
        subtitle="一批「没有归属、却在工业界天天要用」的技能：TensorFlow/Keras 心智模型 · 跨框架权重迁移 · 模型导出与推理运行时 · 真机 GPU 工作流 · 研究产出与知识产权",
        pills=["6 模块", "tf.function · ONNX · TensorRT · nvidia-smi · 专利与许可",
               "数值对拍 · 版本即环境 · 边界要显式",
               "把「靠试」变成「可算」", "CPU only · 无需 GPU/TF/ONNX"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em>，再跑 <em>notebook</em>——后者用纯 numpy 把每个机制从零复现："
            "一个几十行的 tracing 编译器（复刻 <code>tf.function</code> 的追踪与重追踪语义）、"
            "一套权重布局转换与逐层对拍工具、一个迷你 ONNX（图 IR + 形状推断 + opset + 算子覆盖检查）、"
            "一个显存分解器与 OOM 诊断树、以及可专利性自检与许可兼容矩阵。"
            "每个练习都有紧跟的 <code>assert</code> 自测判分。配套 <a href=\"glossary.md\">术语词典</a> 与 "
            "<a href=\"references.md\">参考清单</a>。"
            "<strong>本课的主张是：这些看起来「玄学」或「琐碎」的问题，绝大部分是可计算、可验证的</strong>——"
            "显存能算、时间能算、版本兼容能查表、数值等价能逐层证明、许可冲突能沿依赖树扫出来。"
            "<em>把它们从「跑一下看看」变成「先算出来」，你的迭代速度会有数量级的提升</em>，"
            "因为你不再需要用一次昂贵的试错去获取一个「行/不行」的比特。"
            "<strong>本环境不需要 GPU、不需要装 TensorFlow / ONNX Runtime / TensorRT</strong>："
            "我们复现的是它们的<em>语义与账本</em>（追踪规则、算子集与版本约束、显存公式、驱动矩阵），"
            "而这恰恰是可迁移的那部分——API 会变，语义不会。"
            "每个模块末尾都有一个 🧪 <strong>真实 API / 命令对照胶囊</strong>，把当天学到的东西"
            "翻译成可以原样复制到真机上的代码与命令。"
        ),
        tracks=[
            ("跨框架 · Across Frameworks", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "五项孤儿技能的定位；三条纪律（数值对拍 / 版本即环境 / 边界要显式）；交付契约对象与环境指纹工具——它们贯穿后面每个模块。"),
                ("01_tensorflow/01_讲解.html", "MODULE 01", "TensorFlow / Keras 心智模型",
                 "「Python 只在追踪时执行一次」这一句能解释静态图框架里 80% 的诡异行为；重追踪的缓存 key 与诊断技巧（跨框架通用）；形状每次都变时编译是纯亏损；Conv 布局 / LayerNorm eps / BatchNorm momentum 三个不报错的默认值差异。"),
                ("02_weight_porting/02_讲解.html", "MODULE 02", "框架迁移与权重对齐",
                 "迁移几乎总优于重训，但真正的价值是把「效果差 2 分」变成「第 7 层 eps 不对」；reshape 不能替代 transpose；方阵层让形状检查彻底失效；RNN 要转置 + 门重排；漏掉 buffer 会在 eval 模式才崩。"),
            ]),
            ("交付出去 · Shipping It", [
                ("03_export_runtime/03_讲解.html", "MODULE 03", "模型导出与推理运行时",
                 "导出 = 把 Python 程序编译成受限 IR 上的静态图，所以追踪的坑在这里变成正确性问题；不设动态轴就被写死；算子不支持的四条出路（第一条最有效却常被跳过）；静默回退让「转了 TensorRT 但没变快」；量化容差要按量化误差设。"),
                ("04_gpu_workflow/04_讲解.html", "MODULE 04", "真机 GPU 工作流",
                 "显存五项分解——AdamW 的优化器状态 12N 比参数本身还大；OOM 诊断树按成本排序（多数在第 3–4 步就解决）；「跑了 500 步才 OOM」是长样本不是泄漏；四层版本链与 CUDA_LAUNCH_BLOCKING；看利用率的波动模式而非平均值；MFU 正向估时长、反向判优化空间。"),
            ]),
            ("变成资产 · Turning It Into Assets", [
                ("05_research_output/05_讲解.html", "MODULE 05", "研究产出与知识产权",
                 "公开即丧失新颖性且不可逆；把算法创新翻译成「技术问题 + 技术手段 + 技术效果」；「非预期的效果」是非显而易见性最有力的论据；权利要求过窄则竞争者稍改就绕过；AGPL 打破「不分发就没义务」；内部演示必须结论先行且有明确 ask。"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), """
# 工业研究工程实务

这门课收拢的是一批**没有归属、却在工业界天天要用**的技能。
它们不属于任何一个「算法方向」，所以在课程体系里总是被漏掉，但在工作里几乎每周都会遇到：
读一份 TensorFlow 实现、把权重搬到另一个框架、把模型导出给一个不认识 Python 的运行时、
在一台真实的 8 卡机器上诊断为什么跑不起来、以及——把做出来的东西变成公司的资产。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | TensorFlow / Keras 心智模型 | `01_tensorflow/` |
| 02 | 框架迁移与权重对齐 | `02_weight_porting/` |
| 03 | 模型导出与推理运行时 | `03_export_runtime/` |
| 04 | 真机 GPU 工作流 | `04_gpu_workflow/` |
| 05 | 研究产出与知识产权 | `05_research_output/` |

## 三条纪律（贯穿全课）

1. **数值对拍** — 任何「迁移」「导出」「优化」都要给出*逐层的数值等价证明*，
   而不是「跑通了、输出看起来对」。
2. **版本即环境** — GPU 栈是硬件 → 驱动 → CUDA runtime → 框架 → 编译扩展的四层依赖链。
   这条链**无法靠 `requirements.txt` 复现**，要锁进容器镜像。
3. **边界要显式** — 交付时必须写清「在什么输入范围、什么 dtype、什么容差下成立」。
   否则三个月后会有一场关于「这算不算 bug」的无谓讨论。

三条其实是同一件事的三个侧面：**「交出去」意味着你不再控制运行环境，
所以必须用可验证的断言代替「我这边是好的」。**

## 这门课的主张

**这些看起来「玄学」或「琐碎」的问题，绝大部分是可计算、可验证的。**
显存能算（优化器状态 12N、激活的平方项）、时间能算（MFU 反推）、
版本兼容能查表（驱动矩阵、compute capability）、数值等价能逐层证明、
许可冲突能沿依赖树扫出来。

把它们从「跑一下看看」变成「先算出来」，迭代速度会有数量级的提升——
因为你不再需要用一次昂贵的试错去获取一个「行/不行」的比特。

## 环境

见 `requirements.txt`。纯 numpy / CPU，**不需要 GPU，也不需要装 TensorFlow / ONNX Runtime / TensorRT**。
我们复现的是它们的**语义与账本**（追踪规则、算子集与版本约束、显存公式、驱动矩阵），
而这恰恰是可迁移的那部分——API 会变，语义不会。
每个模块末尾有一个 🧪 **真实 API / 命令对照胶囊**，把当天学到的东西翻译成可原样复制到真机上的代码与命令。

## ⚠️ 关于模块 05

**模块 05 关于专利与开源许可的内容是工程视角的实用指南，不是法律意见。**
真实的专利申请、许可合规判断与合同解释必须由公司法务/IP 部门或执业律师做。
本模块的目标是让你**知道该在什么时候找他们、带什么材料去、以及不要做什么**——
这些恰恰是最常出错的地方，而且出错的代价通常不可逆。

## 与相邻课程的分工

C36 讲 GPU 与 kernel 的原理；C38 讲框架内部（autograd 与编译）；C39 讲分布式训练；
C24 讲推理引擎内部；C27 讲量化算法；C48 讲容器化与云上部署；C50 讲 HuggingFace 生态。
**本课聚焦「跨框架、跨运行时、跨环境地把东西交出去」这一段，以及交出去之后怎么变成资产。**

配套：[术语词典](glossary.md) · [参考清单](references.md)
""")

    text_file(os.path.join(DIR, "requirements.txt"), """
# 工业研究工程实务 —— 依赖清单
# 纯 numpy + 标准库、CPU 可跑（assert 全过）。
# **不需要 GPU，也不需要装 TensorFlow / ONNX Runtime / TensorRT**：
# 本课复现的是它们的语义与账本（追踪规则、算子集与版本约束、显存公式、驱动矩阵），
# 而不是调用它们的 API。每个模块末尾的 🧪 胶囊给出真机上的真实命令与代码。

numpy          # 核心：tracing 编译器、权重转换、迷你 ONNX、显存账本的实现
pandas         # 可选：对比表格的展示
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel

# —— 以下是真机上会用到的（本环境不装，胶囊里给出用法）——
# tensorflow>=2.15          # 模块 01：tf.function / Keras
# torch>=2.4                # 模块 02/03/04
# onnx onnxruntime          # 模块 03：导出与验证
# onnxruntime-gpu           # 模块 03：CUDA / TensorRT execution provider
# nvidia-ml-py              # 模块 04：以 Python 读取 nvidia-smi 的信息
""")

    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


GLOSSARY = r"""
# 术语词典 · Glossary（工业研究工程实务）

> 按主题分组，每条 2–3 句释义。读框架文档、导出报错、GPU 日志或专利材料时遇到生词回这里查；英文术语保留原文。

## 图与追踪 · Graphs & Tracing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| eager execution | 动态图 / 即时执行 | Python 逐行执行，每个算子立刻算出结果。好调试，但无法整图优化、无法脱离 Python 部署。PyTorch 与 TF2 的默认模式。 |
| graph mode | 静态图 | Python 只是**构图脚本**，跑一遍产出一张图；之后执行的是图。可整图优化、可序列化、可脱离 Python。代价是调试困难与控制流被固化。 |
| tracing | 追踪 | 用**符号张量**（tracer）代替真实数组跑一遍 Python 函数，把每个算子记成图节点。`tf.function`/`jax.jit`/`torch.compile`/`torch.onnx.export` 的共同机制。 |
| tracer | 符号张量 | 追踪期代替真实张量的对象，只持有 (图, 节点 id, 形状, dtype)。JAX 的 tracer 在被当作具体值使用时**直接报错**（宁可报错也不静默固化）。 |
| retracing | 重追踪 | 输入签名变化导致重新追踪。**头号性能杀手**：追踪一次约等于跑几十到几百次前向。诊断技巧：在函数里放一个 Python 副作用，数它执行几次。 |
| cache key（签名） | 缓存键 | `(每个输入的 dtype, 形状, 所有 Python 参数的值)`。传 Python 标量而非 tensor 会让每个取值各占一张图。 |
| `input_signature` | 输入签名声明 | TF 里把可变维标成 `None`，让一张图接受任意形状。对应 `torch.compile(dynamic=True)` 与 ONNX 的动态轴。 |
| AutoGraph | 自动图改写 | TF 把一部分 Python 控制流自动改写成图算子（`if`→`tf.cond`）。**只在条件依赖 tensor 时改写**——「有时改写有时不改写」是 TF 最难懂的地方。 |
| graph break | 图打断 | `torch.compile` 遇到不支持的 Python 时静默回退 eager。不报错但性能损失大；用 `TORCH_LOGS=graph_breaks` 诊断。 |
| 构图时的量 vs 运行时的量 | static vs dynamic values | 静态图的第一性原理。构图时的量（Python int、静态形状）追踪时确定；运行时的量（tensor 值）只有执行图时才知道。**依赖后者的控制流必须用图算子表达**。 |
| Functional API | 函数式 API | Keras 构建「可被检查的数据结构」：定义时就知道拓扑与形状，所以能 `summary()`、能画图、能直接序列化。PyTorch 只有 subclassing，故导出必须靠追踪。 |
| MFU | 模型 FLOPs 利用率 | 实际达到的算力 ÷ 峰值算力。调好的单卡 40–55%；有数据瓶颈时可低至 5%。**双向可用**：正向估时长、反向判还有多少优化空间。 |

## 权重迁移 · Weight Porting

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| reshape vs transpose | 重解释 vs 换排列 | `reshape` 只重新解释同一块连续内存（元素顺序不变）；`transpose` 改变元素排列。两者常得到**相同形状但完全不同的内容**，而代码不报错。 |
| Conv 权重布局 | conv layout | PyTorch `(out, in, kH, kW)` ↔ TF `(kH, kW, in, out)`，需 `transpose(2,3,1,0)`。ConvTranspose 的 in/out 本身就是反的，更易错。 |
| 方阵陷阱 | square-matrix trap | `d_model→d_model` 的层（Transformer 的 q/k/v/o 投影）忘了转置时**形状检查完全无法区分**——模型会跑、结果全错。唯一可靠的防线是数值对拍。 |
| 门顺序 | gate order | PyTorch GRU 是 `[r, z, n]`、Keras 是 `[z, r, h]`（**前两个门反的**）；LSTM 各实现也不同。错了模型仍能跑、loss 仍能降，只有用**预训练权重**时才暴露。 |
| buffer vs parameter | 缓冲区 vs 参数 | BatchNorm 的 `running_mean`/`running_var` 是 buffer，遍历 `parameters()` 看不到。**漏掉它训练模式正常、一到 eval 就崩**——最难定位的一类迁移 bug。 |
| 逐层对拍 | layer-wise numeric check | 喂同一输入，按执行顺序比较每层激活，**在第一个失配处停下**（后面全错只是它的后果）。把「效果差 2 分」变成「第 7 层 eps 不对」。 |
| 全 1 / 阶梯探针 | ones / ramp probe | 五分钟排除所有布局错误：全 1 输入让维度错误表现为数量级差异；阶梯输入打破对称性以抓方阵的转置错误。 |
| 容差 | tolerance | fp32 单层 ~1e-6、96 层 ~1e-5；fp16 放宽两个数量级；int8 量化约 2/127。**太紧则假警报、太松则真错误被放过**。 |
| eps / momentum 默认值差异 | default mismatch | `keras.LayerNormalization` 的 eps 是 **1e-3**、PyTorch 是 1e-5（差 100 倍）；BatchNorm 的 momentum **语义相反**（torch 0.1 ⟺ keras 0.9）。都不报错。 |

## 导出与运行时 · Export & Runtime

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| ONNX | 开放神经网络交换格式 | 事实上的交换格式。四要素：静态拓扑、**opset 版本**、符号形状（动态轴）、内联权重（initializer）。 |
| opset version | 算子集版本 | 每个算子记录「自哪个 opset 起可用/语义变更」。**不是越新越好**——目标运行时可能只支持到某个版本。要先查上限再导出。 |
| dynamic axes | 动态轴 | 把会变的维度声明为符号（`"batch"`）而非常数。**不设就被写死**，「用 batch=1 导出、线上来 batch=8」是最常见的导出事故。 |
| shape inference | 形状推断 | 从输入形状推出每个中间张量的形状。`NonZero`/`Unique`/`masked_select` 的输出形状**依赖输入数值**，推断不出来。 |
| 静默回退 | silent fallback | TensorRT/CoreML/TFLite 遇到不支持的算子不报错，而是切子图交给别的后端（甚至 CPU）。**症状是「转了但没变快」**，要看分区日志而非端到端延迟。 |
| execution provider | 执行提供者 | ONNX Runtime 的后端插件（CUDA/TensorRT/CPU/DirectML），按优先级回退。用 `get_providers()` 确认实际用了哪个。 |
| engine（TensorRT） | 引擎 | TensorRT 构建产物。**与 GPU 型号与驱动绑定**——换卡要重建，构建要几分钟到几十分钟。直接影响镜像与冷启动策略。 |
| ANE | Apple 神经引擎 | 极省电极快，但只支持有限算子与精度。模型会「成功转换」却实际跑在 CPU/GPU 上——要看 Xcode 性能报告里每层的计算单元。 |
| 校准集 | calibration set | 静态 int8 量化用来统计激活范围的数据。**必须是线上分布的有代表性小样本**（几百条）；分布不对量化范围就是错的。 |
| 异常层 | outlier layer | 量化误差比其他层大一个数量级的层——通常因激活有长尾离群值。**一个离群值就能撑爆整层的量化范围**。 |
| 交付契约 | delivery contract | 明确写出「在什么输入范围、什么 dtype、什么容差下成立」。缺了它就会有关于「差 1e-4 算不算 bug」的无谓讨论。 |

## 真机 GPU · GPU Workflow

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 显存五项 | memory breakdown | 参数 + 梯度 + 优化器状态 + 激活 + 杂项。**每一项都能算**，所以 OOM 是算术题不是运气问题。 |
| 优化器状态 | optimizer states | AdamW 混合精度下 **12 字节/参数**（fp32 主权重 4 + m 4 + v 4）——**比参数本身还大**。8bit Adam 6B、SGD 4B。这是最大的一项。 |
| 激活显存 | activation memory | 常常是主导项。线性项随 `B×L` 增长；朴素注意力的矩阵随**序列长平方**增长（FlashAttention 把它变成线性）。 |
| 梯度检查点 | gradient checkpointing | 只存部分中间结果、反向时重算。激活显存大降，代价约 +30% 计算。**单卡上性价比最高的一招**。 |
| token-budget 分批 | token-budget batching | 「每批 8192 token」而不是「每批 32 条」。让每批 token 数有硬上界 → 显存有硬上界 → 不会突然 OOM，同时减少 padding 浪费。 |
| 缓存分配器 | caching allocator | PyTorch 保留已释放的显存块。**`nvidia-smi` 显示的占用高于真实占用**——要看 `memory_allocated()` 与 `max_memory_allocated()`。 |
| `expandable_segments` | 可扩展段 | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`，缓解碎片。免费的第一招。 |
| compute capability | 计算能力 | GPU 的架构版本（A100=8.0、H100=9.0、RTX4090=8.9）。二进制没编译对应的 `sm_XX` 时报 **`no kernel image is available`**——听起来像找不到文件，实际是「这个二进制不认识你的卡」。 |
| 四层版本链 | version chain | 硬件 → 驱动 → CUDA runtime → 框架 → 编译扩展。最脆弱的是编译扩展（绑定 torch×CUDA×Python×ABI 四元组）。**这条链无法靠 requirements.txt 复现**。 |
| `CUDA_LAUNCH_BLOCKING` | 同步执行 | **GPU 调试的第一招**。kernel 异步启动，报错时 Python 栈已跑到别处；设了它错误就出现在真正出问题的那一行。 |
| `nvidia-smi topo -m` | 拓扑查询 | 看卡间是 NVLink 还是 PCIe。NVLink 带宽是 PCIe 的 5–10 倍，直接决定多卡训练效率的上限。 |
| 利用率的波动模式 | utilization pattern | **数据瓶颈周期性掉到 0，计算瓶颈稳定在高位**。平均值一样但处方完全不同——要看 `dmon` 的时间序列。诊断顺序：数据 → 通信 → 计算。 |

## 研究产出与知识产权 · Output & IP

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 新颖性 | novelty | 此前没有任何公开披露。**公开即丧失，且多数辖区不可逆**——论文、arXiv、博客、开源、公开演讲、公开 commit、客户 demo 都算。 |
| 非显而易见性 | non-obviousness | 对该领域普通技术人员不是显然的。「把 A 方法用到 B 任务」常被认为显而易见；**「非预期的效果」是最有力的论据**。 |
| 可专利主题 | subject-matter eligibility | 不能是抽象概念或数学公式本身。**纯算法难，「算法 + 具体技术改进」容易**——要把创新翻译成「技术问题 + 技术手段 + 技术效果」。 |
| 独立/从属权利要求 | independent / dependent claim | 独立要求最宽（限定越少范围越宽）；从属逐层收缩，作用是「独立要求被无效时还有它顶着」。 |
| 绕过分析 | design-around | 自问「竞争者绕过我的最小改动是什么」。若答案是「把 ReLU 换成 GELU」，说明权利要求过窄。 |
| 发明披露书 | invention disclosure | 你实际要写的东西（不是专利本身）。六节：问题 / 现有技术 / 方案 / 为何有效 / **变体** / **时间线与公开状态**。最后两节最易跳过也最关键。 |
| permissive license | 宽松许可 | MIT/BSD/Apache-2.0。保留声明即可用于闭源产品。Apache-2.0 还带专利授权条款。 |
| copyleft | 传染性许可 | GPL：**分发**衍生作品时必须同样开源。LGPL 是弱 copyleft（动态链接通常可以）。 |
| AGPL | 网络 copyleft | **「通过网络提供服务」即触发开源义务**——打破了「不分发就没义务」的直觉，而这正是所有 AI 服务的形态。SaaS 场景下最危险的一个。 |
| CC-BY-NC | 非商业许可 | 禁止商业使用。**大量数据集是这个许可**——训练商业模型即违约。 |
| 自定义模型许可 | custom model license | Llama 等的许可不是 OSI 认可的开源许可（用户数阈值、禁止改进竞品、可接受使用政策）。**必须逐条读**。 |
| 依赖树传染 | transitive license risk | 问题常藏在**二级依赖**里（某库自己是 MIT，但依赖一个 AGPL 的组件）。所以要遍历整棵树。 |
| 结论先行 | conclusion-first | 内部演示的第一张幻灯片就给结论。听众可能只听前五分钟。标题应是**断言**（「显存降 40%」）而非章节名（「结果」）。 |
| ask | 明确请求 | 演示结尾必须说清「谁 在 什么时候 做 什么决定 / 需要什么资源」。**把演示的成功定义为「产生了一个决定」而非「讲清楚了」**。 |
"""

REFERENCES = r"""
# 参考清单 · References（工业研究工程实务）

> 本课的参考大量是**官方文档而非论文**——因为这些是工程问题，权威定义在文档里。
> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C36** 讲 GPU 与 kernel 原理；**C38** 讲框架内部（autograd 与编译）；
> **C39** 讲分布式训练；**C24** 讲推理引擎内部；**C27** 讲量化算法；**C48** 讲容器化与云上部署；
> **C50** 讲 HuggingFace 生态。**本课聚焦「跨框架、跨运行时、跨环境地把东西交出去」这一段。**

## TensorFlow / Keras 与追踪语义 · Tracing Semantics
- ★ **TensorFlow 指南 _Better performance with tf.function_** — **本课模块 01 第三节的一手来源**。重追踪的准确规则、`input_signature` 的用法、以及诊断方法。重点读「Rules of tracing」与「Retracing」两节。
- ★ **TensorFlow 指南 _Introduction to graphs and tf.function_** — 静态图与 Python 副作用的关系讲得最清楚的一篇。读完就理解了「Python 只在追踪时执行一次」的全部后果。
- ★ **JAX 文档 _JAX — The Sharp Bits_** — **强烈推荐即使你不用 JAX 也读一遍**。它把追踪的坑（纯函数要求、tracer 不能做 Python 判断、随机数要显式传 key）列得最清楚，因为 JAX「宁可报错也不静默固化」。
- **JAX 文档 _How to think in JAX_** — 三种范式差别的最佳入门（状态放哪、图从哪来）。
- **TensorFlow 指南 _The Keras functional API_** — Functional 与 Subclassing 的差别，以及为什么前者「是可被检查的数据结构」。
- **PyTorch 文档 _torch.compile_ 与 _TorchDynamo_** — 对照阅读会发现与 `tf.function` 语义高度同构。重点看 graph break 的诊断（`TORCH_LOGS`）与 `dynamic=True`。
- **Abadi et al. 2016, _TensorFlow: A System for Large-Scale Machine Learning_** — 数据流图这个设计的原始论证。历史价值大于实用价值，但能解释 TF 为什么长成这样。
- **Bradbury et al. 2018, _JAX: composable transformations of Python+NumPy programs_** — 可组合函数变换（`jit`/`grad`/`vmap`/`pmap`）的设计出处。

## 权重迁移与数值等价 · Porting
- ★ **PyTorch 文档中 `nn.Linear` / `nn.Conv2d` / `nn.GRU` / `nn.LSTM` 的 _Shape_ 与 _Variables_ 小节** — **权重形状与门顺序的权威定义**。做迁移时这几页要开着。特别注意 `nn.Linear` 计算的是 `y = xWᵀ + b`（所以存 `(out, in)`）。
- ★ **Keras 对应层的文档（`Dense` / `Conv2D` / `GRU` / `LayerNormalization` / `BatchNormalization`）** — 与上一条对读。**注意 `LayerNormalization` 的默认 epsilon 是 1e-3，`BatchNormalization` 的 momentum 语义与 PyTorch 相反**。
- ★ **HuggingFace `transformers` 里任意一个 `convert_*_original_checkpoint_to_pytorch.py`** — **读一遍真实的迁移脚本，胜过读十篇教程**。重点看它怎么做命名映射、怎么逐项断言、怎么处理权重共享（tied embeddings）。
- **cuDNN 文档中 RNN 的权重布局说明** — PyTorch 的门顺序源自它。理解「为什么门顺序是这个」而不只是「它是这个」。
- **NumPy 文档 _Indexing on ndarrays_ 与 `reshape` / `transpose` 的说明** — 「重新解释内存」与「改变排列」的区别，本课模块 02 第一节的基础。

## 导出与推理运行时 · Export & Runtime
- ★ **ONNX 官方 _Operators_ 文档** — 每个算子的「since version」与语义变更。**兼容性问题的一手来源**，查 opset 就查这里。
- ★ **ONNX _IR specification_** — 模型结构（graph / node / initializer / opset_import）与符号形状的定义。一页纸能读完，值得读。
- ★ **PyTorch 文档 _torch.onnx_，尤其 _Limitations_ 与 _FAQ_ 两节** — 把追踪的坑（控制流固化、形状写死、不支持的算子）列得很清楚。**导出前应该先读这两节**。也关注新的 `torch.export`/Dynamo 导出路径。
- ★ **NVIDIA _TensorRT Developer Guide_** — 重点看 layer fusion、INT8 calibration、以及 **engine 与硬件绑定**的说明（后者影响镜像与冷启动策略）。
- **ONNX Runtime 文档 _Execution Providers_ 与 _Performance Tuning_** — provider 的优先级与回退规则；怎么确认实际用了哪个后端。
- **Apple _Core ML Tools_ 文档** — ANE 支持的算子与精度约束，以及怎么在 Xcode 里看每层实际跑在哪个计算单元（诊断静默回退）。
- **TensorFlow Lite 文档 _Operator compatibility_ 与 _Delegates_** — 算子集最受限的运行时，也是 delegate 回退机制的好例子。
- **Jacob et al. 2018, _Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference_** — 训练后量化与量化感知训练的经典。量化的算法侧在 C27 详读，这里只需要它的误差量级作为容差依据。

## 真机 GPU 工作流 · GPU
- ★ **NVIDIA _CUDA Compatibility_ 指南** — **驱动与 runtime 的版本规则的权威来源**。本课模块 04 的版本矩阵出自这里。也讲清了 forward compatibility 的适用条件。
- ★ **`nvidia-smi` 手册** — `dmon`（时间序列监控，诊断数据瓶颈的关键）与 `topo -m`（卡间拓扑）两个子命令值得精读。多数人只用了它 10% 的功能。
- ★ **PyTorch 文档 _CUDA semantics_** — 异步执行与 `CUDA_LAUNCH_BLOCKING`。**理解「为什么报错的栈总是无关的」就靠这一页**。
- ★ **PyTorch 文档 _Memory management_** — 缓存分配器的行为、`expandable_segments`、以及为什么 `nvidia-smi` 的数字高于 `memory_allocated()`。
- ★ **Korthikanti et al. 2022, _Reducing Activation Recomputation in Large Transformer Models_** — **激活显存的精确建模**，本课模块 04 公式的来源。也是选择性重算这一思路的出处。
- ★ **Chowdhery et al. 2022, _PaLM: Scaling Language Modeling with Pathways_** — **MFU 这个指标的常用出处**（§5）。注意各家对 MFU 的口径不完全一致，跨论文比较前要先确认。
- **PyTorch 文档 _PyTorch Profiler_ 与 _torch.profiler_** — 从 kernel 时间分布定位计算瓶颈。配合 `record_shapes` 与 `profile_memory` 用。
- **Dao et al. 2022, _FlashAttention_** — 为什么注意力的激活显存能从平方变成线性。算法细节在 C36，这里只需要它对显存账本的影响。
- **Rajbhandari et al. 2020, _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_** — 优化器状态/梯度/参数分片。OOM 诊断树第 ⑦ 步的原理（C39 详读）。
- **Dettmers et al. 2022, _8-bit Optimizers via Block-wise Quantization_** — 8bit Adam 把优化器状态从 12N 降到 ~6N 的做法。诊断树第 ⑤ 步。

## 研究产出与知识产权 · Output & IP
> ⚠️ **以下均为工程视角的参考，不构成法律意见。** 真实判断请交给法务/IP 部门或执业律师。

- ★ **USPTO _Subject Matter Eligibility_ 指南（含 AI 相关示例）** — **理解「算法 + 技术效果」为什么重要的最直接材料**。它的示例部分把「什么样的软件权利要求能通过」讲得很具体。
- ★ **EPO _Guidelines for Examination_, G-II 3.3（计算机实现发明）** — 欧洲标准，与美国不同（更强调「技术特征」）。**多辖区申请时两边都要看**。
- ★ **choosealicense.com 与 SPDX 许可清单** — 日常查许可的两个入口。前者给决策建议、后者给规范标识符（工具链认这个）。
- ★ **GNU _License Compatibility and Relicensing_ 页面** — copyleft 的传染规则、GPL 与 AGPL 的差别、以及各许可之间的兼容性。**AGPL 的网络触发条款在这里说得最清楚**。
- **OSI _Open Source AI Definition_** — 理解「开源模型」这个词为什么已经失去精确性，以及社区试图怎么收敛。
- **各主流模型许可原文（Llama Community License、Gemma Terms of Use 等）** — **必须逐条读而不是靠印象**。用户数阈值、禁止改进竞品、可接受使用政策都写在里面。
- ★ **Barbara Minto, _The Pyramid Principle_** — 「结论先行」的出处。本课模块 05 的内部演示模板基于它。读第一部分就够。
- **Simon Peyton Jones, _How to Give a Great Research Talk_** — 学术演讲的经典。**注意本课讲的内部演示模板与它不同**（目标不同），但两者都值得会。
- **各会议的 artifact evaluation 与 reproducibility checklist（NeurIPS / ACL / MLSys）** — 了解「工业界论文在不能开源数据的前提下怎么提供可信的可复现性」这个现实张力。
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足，请补充")
