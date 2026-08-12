#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C51 · 文本数据增强与合成数据工程。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c51_m00, c51_m01, c51_m02, c51_m03, c51_m04, c51_m05

CID = "C51_Data_Augmentation_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "文本增强的三个层次（词面/语义/指令）与本课的核心方法论——每个增强都过「保真度 × 多样性 × 有效性」三重检验；用规则可判定的任务让标签保真度可精确计算",
     c51_m00),
    ("01_lexical", "01_讲解.html", "01_lexical_augmentation.ipynb",
     "01 · 词面增强",
     "EDA 四操作的危险性排序（RD > RS > RI ≈ SR）· RD 为何系统性污染关键样本 · 保护规则与互信息自动挑关键词 · AEDA 的 100% 保真 · α 与数据量的交互 · 在线 vs 离线增强",
     c51_m01),
    ("02_backtranslation", "02_讲解.html", "02_backtranslation.ipynb",
     "02 · 回译与释义",
     "在语义空间而非词面空间操作 · 通顺性带来的虚假可信度 · 多样性主要来自解码温度 · 四类高危失效与否定奇偶检查 · 三级过滤流水线 · 「宽松生成 + 严格过滤」为何优于反过来",
     c51_m02),
    ("03_instruction_synthesis", "03_讲解.html", "03_instruction_synthesis.ipynb",
     "03 · LLM 驱动的指令数据合成",
     "唯一能真正增加信息量的增强层次 · Self-Instruct 的四步循环与 ROUGE-L 去重（命门）· 输出优先防标签倾斜 · Evol-Instruct 的算子与难度伪装 · Magpie · 教师偏差传递与模式坍塌的四个早期征兆",
     c51_m03),
    ("04_quality_control", "04_讲解.html", "04_quality_control.ipynb",
     "04 · 增强的质量控制",
     "四类失效互相独立 · 多样性度量是警报器不是评分器（且可以被刷）· 三层去污染与「先增强后划分」的灾难 · 流水线顺序与分阶段丢弃率就是诊断报告 · 坍塌看板用相对变化告警",
     c51_m04),
    ("05_evaluation_ablation", "05_讲解.html", "05_evaluation_ablation.ipynb",
     "05 · 增强的评测与消融",
     "为什么增强的文献结论普遍不可信 · 四个必须有的对照组（复制对照 + 真实数据对照）· 配对 bootstrap 与功效分析 · 学习曲线与「等价真实数据量」· 三条预算决策规律",
     c51_m05),
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
        title="文本数据增强与合成数据工程",
        subtitle="标注不够时怎么「造」数据，以及——更重要的——怎么证明造得有用：词面增强 · 回译与释义 · LLM 指令合成 · 质量控制 · 能证伪自己的实验设计",
        pills=["6 模块", "EDA · 回译 · Self-Instruct · Evol · Magpie",
               "保真度 × 多样性 × 有效性 三重检验", "规则可判定任务 -> 保真度可精算",
               "CPU only · 无需 GPU/翻译模型/LLM API"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em>——它不只讲「怎么造」，更讲<strong>「怎么判断造得有没有用」</strong>；"
            "再跑 <em>notebook</em> 用纯 numpy 把每种增强与每套检验从零实现："
            "EDA 四操作与保护规则、可控失真的模拟回译器、完整的 Self-Instruct 循环与 ROUGE-L 去重、"
            "三层去污染检测、多样性度量、模式坍塌看板、配对 bootstrap 与功效分析。"
            "每个增强都必须过<strong>三重检验</strong>：<strong>保真度</strong>（标签有没有被破坏）、"
            "<strong>多样性</strong>（新样本有多新）、<strong>有效性</strong>（下游指标真的涨了且超过噪声）。"
            "每个练习都有紧跟的 <code>assert</code> 自测判分。配套 <a href=\"glossary.md\">术语词典</a> 与 "
            "<a href=\"references.md\">参考清单</a>。"
            "本课的立场是<strong>「有条件的怀疑」</strong>：增强在小数据、低资源、长尾与零标注冷启动场景确实有用，"
            "但增强的文献里充满了「在小数据集上涨了 1 分」这类不可靠结论（种子方差本身就有 2–3 分）。"
            "<strong>所以本课给你的不是「增强很棒」的信念，而是「怎么在自己的数据上判断它到底有没有用」的能力</strong>——"
            "包括接受「没用」这个答案。"
            "<strong>本环境没有 GPU / 翻译模型 / LLM API</strong>：我们用<em>参数可控的模拟增强器</em>"
            "（带 <code>distortion</code> 的假翻译器、带 <code>bias</code>/<code>collapse</code> 的假教师），"
            "并用<strong>规则可判定的合成任务</strong>让「标签保真度」变成一个可精确计算的数字——"
            "这让本课能做真实环境里做不到的实验，比如「把教师偏差从 0 调到 0.5，看学生的偏差怎么变」。"
        ),
        tracks=[
            ("造数据 · Generating", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "三个层次（词面/语义/指令）与它们的信息量上限；三重检验的实现；为什么「多样性高 ≠ 有用」；用规则可判定任务让保真度可精算。"),
                ("01_lexical/01_讲解.html", "MODULE 01", "词面增强",
                 "四操作的危险性差一个量级；RD 破坏标签的概率与关键词稀有度成正比（系统性污染关键样本）；保护规则把保真度从 90% 提到 99%+；AEDA 的精确 100%；「小数据集才受益」的定量版本。"),
                ("02_backtranslation/02_讲解.html", "MODULE 02", "回译与释义",
                 "语义空间操作让保真度高一档，但失效更隐蔽（句子总是通顺的）；多样性主要来自解码温度而非中间语言；四类高危场景；「宽松生成 + 严格过滤」优于反过来。"),
                ("03_instruction_synthesis/03_讲解.html", "MODULE 03", "LLM 指令数据合成",
                 "唯一能真正增加信息量的层次；ROUGE-L 去重是打断「模式惯性正反馈」的唯一机制；「输出优先」防标签倾斜；难度伪装与可验证难度代理；教师偏差传递与坍塌的四个早期征兆。"),
            ]),
            ("筛数据 · Filtering", [
                ("04_quality_control/04_讲解.html", "MODULE 04", "增强的质量控制",
                 "四类失效互相独立；多样性度量可以被刷（插罕见词就能拉高 distinct-n）；去污染必须第一个跑（它抓唯一「让指标变好」的失效）；「先增强后划分」的灾难；分阶段丢弃率就是诊断报告。"),
            ]),
            ("验证有用 · Proving It Works", [
                ("05_evaluation_ablation/05_讲解.html", "MODULE 05", "增强的评测与消融",
                 "固定优化步数而非 epoch；四个对照组（复制对照分离「多样性」、真实数据对照回答「预算该花哪」）；配对 bootstrap 与功效分析；学习曲线与「等价真实数据量」这个最有用的换算。"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), """
# 文本数据增强与合成数据工程

标注数据不够时怎么「造」出更多数据——以及**更重要的**——怎么证明造得有用。

文本增强与图像增强有个根本区别：旋转一张猫的照片它还是猫，但**删掉一个「不」字，标签就反了**。
文本的离散性与组合性让「增强」与「破坏」之间的界限非常薄。所以本课的核心不是「十种增强技巧」，
而是**「怎么判断一个增强是不是真的有用」**。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 词面增强 | `01_lexical/` |
| 02 | 回译与释义 | `02_backtranslation/` |
| 03 | LLM 驱动的指令数据合成 | `03_instruction_synthesis/` |
| 04 | 增强的质量控制 | `04_quality_control/` |
| 05 | 增强的评测与消融 | `05_evaluation_ablation/` |

## 三重检验（贯穿全课）
每个增强都必须过三关，缺一个结论就不可信：

1. **保真度** — 增强后标签是否仍然正确（本课用**规则可判定**的任务，所以这是个精确数字）
2. **多样性** — 新样本有多新（distinct-n / self-BLEU / 嵌入覆盖；**它是警报器不是评分器**）
3. **有效性** — 下游指标真的涨了，且涨幅超过种子噪声（多种子 + 配对 bootstrap + 四个对照组）

## 这门课的立场
**有条件的怀疑。** 增强在小数据、低资源、长尾、零标注冷启动场景确实有用；
但增强文献里充满了「小数据集上涨 1 分」这类不可靠结论——种子方差本身就有 2–3 分。
本课给你的不是「增强很棒」的信念，而是**在自己的数据上判断它到底有没有用的能力**，
包括接受「没用」这个答案。最实用的产出是一个换算：
**把增强的收益变成「等价真实数据量」**——有了它，增强 vs 标注就可比了。

## 环境
见 `requirements.txt`。纯 numpy / CPU，**不需要 GPU、翻译模型、LLM API 或联网**。
用参数可控的模拟增强器（带 `distortion` 的假翻译器、带 `bias`/`collapse_rate` 的假教师），
并用规则可判定的合成任务让保真度可精确计算。
**这让本课能做真实环境里做不到的实验**——比如「把教师偏差从 0 调到 0.5，看学生的偏差怎么变」。

## 与相邻课程的分工
C21 讲预训练语料配比与合成数据在预训练中的角色；C43 讲 PB 级去重/过滤/流式的工程手艺；
C14 讲合成数据理论与生成媒体评测；C10/C03 讲测量科学与评测统计。
**本课聚焦「有标注任务的训练集不够用时，怎么造与怎么验」这个具体问题。**

配套：[术语词典](glossary.md) · [参考清单](references.md)
""")

    text_file(os.path.join(DIR, "requirements.txt"), """
# 文本数据增强与合成数据工程 —— 依赖清单
# 纯 numpy + 标准库、CPU 可跑（assert 全过）：
# 用参数可控的模拟增强器 + 规则可判定的合成任务，让保真度/多样性/有效性都可精确计算。
# 本环境不需要 GPU / 翻译模型 / LLM API / 联网。

numpy          # 核心：所有增强、度量、统计检验的实现
pandas         # 可选：对比表格与实验报告的展示
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel
""")

    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


GLOSSARY = r"""
# 术语词典 · Glossary（文本数据增强与合成数据工程）

> 按主题分组，每条 2–3 句释义。读增强/合成数据的论文或搭数据管线时遇到生词回这里查；英文术语保留原文。

## 世界观与三重检验 · Mindset & Three Checks

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data augmentation | 数据增强 | 从已有数据造出更多训练样本。文本上与图像的根本区别：**离散且组合**——删一个「不」字标签就反了，「增强」与「破坏」界限极薄。 |
| fidelity (label preservation) | 保真度 / 标签保持性 | 增强后标签仍正确的比例。本课把它当**硬门槛**（≥0.98）而非软指标，因为破坏的往往是「标签由单个关键词决定」的关键样本。 |
| diversity | 多样性 | 新样本相对已有样本的新颖程度。**它是警报器不是评分器**：绝对值取决于长度/词表/领域，且可以被刷（插罕见词就能拉高 distinct-n）。只看趋势。 |
| effectiveness | 有效性 | 下游指标真的提升且超过噪声。**唯一能回答「有没有用」的检验**；前两个是内在指标。 |
| 三个层次 | lexical / semantic / instructional | 词面（扰动字词）、语义（换表达）、指令（LLM 造新样本）。**前两者不增加信息量**（是正则化），只有指令层能真正增加（上限是教师）。 |
| 等价真实数据量 | equivalent real data | 「增强 4× ≈ 多 300 条真实数据」。**本课最实用的换算**——有了它，增强 vs 标注就可比了。 |
| 证伪性设计 | falsifiable design | 主动加入最强对照组（复制对照、真实数据对照、多种子、固定训练量）的实验设计；对立面是只选对增强有利条件的「确认性设计」。 |

## 词面增强 · Lexical

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| EDA | 简易数据增强 | Wei & Zou 2019 的四操作：SR/RI/RS/RD。危险性排序 **RD > RS > RI ≈ SR**（破坏率差一个量级）。 |
| SR (synonym replacement) | 同义词替换 | 替换非停用词的同义词。风险来自一词多义与程度差异（「好」→「完美」）。最温和（保持槽位）。 |
| RI (random insertion) | 随机插入 | 插入某词的同义词。风险中等（只是加冗余，模型可学会忽略）。 |
| RS (random swap) | 随机交换 | 交换两个词位置。**高风险**：语序承载语义，否定词位置一换极性就翻。 |
| RD (random deletion) | 随机删除 | 以概率 p 删词。**最危险**：破坏标签的概率与关键词稀有度成正比 → **系统性污染「标签由单关键词决定」的样本**，而这类样本恰是决策边界所在。 |
| AEDA | 更简易的增强 | Karimi et al. 2021：**只随机插入标点**。保真度精确 100%（不动任何实词），仍提供表面扰动。需要「绝对安全的正则化」时的首选。 |
| 保护规则 | protection rules | 把不能动的词标出来：否定词、程度副词、命名实体、数字单位、**互信息自动挑出的高关键词**、标注 span。保护后连 RD 也能到 97%+ 保真度。 |
| α（增强强度） | augmentation strength | 改动词数 = α × 句长。保真度随 α 单调降、多样性单调升；EDA 原论文最优 ≈ 0.1，过大时急剧下降。 |
| 互信息挑关键词 | MI-based keyword selection | 用 \|P(y=1\|w) − P(y=1)\| 自动找出与标签强相关的词加入保护表。**不需要领域知识**。 |
| 离线 vs 在线增强 | offline / online | 离线：预处理落盘、数据变 N 倍、**会混淆「增强」与「训练更久」**。在线：每 batch 现场扰动、数据量不变、无此混淆。 |
| token dropout | token 丢弃 | 在线增强：把 token 换成 `[UNK]`（不是删除——保持长度与位置，比 RD 安全）。 |
| NEFTune / embedding 噪声 | 嵌入噪声 | 在词嵌入上加高斯噪声。**完全不动离散 token，保真度 100%**；`trl` 的 `neftune_noise_alpha`。 |

## 语义增强 · Semantic

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| back-translation | 回译 | 译到另一语言再译回。优势：在**语义空间**操作，「保语义」是内建约束。劣势：**失效更隐蔽**（句子总是通顺的，即使语义已漂移）。 |
| 枢轴语言 | pivot language | 回译的中间语言。语言距离越远措辞变化越大、漂移风险也越大。先用 en（质量最高），不足时再加第二枢轴并**单独测保真度**。 |
| 采样回译 | sampled back-translation | Edunov et al. 2018：用采样（或加噪 beam）而非纯 beam。**多样性主要来自解码策略，不是中间语言**——温度 0 时多个副本几乎相同（白花算力）。 |
| 多跳回译 | multi-hop BT | zh→en→de→zh。多样性升但**误差累积**、保真度快降。是坏交易（同样多样性可用「高温 + 严格过滤」更便宜地拿到）。 |
| round-trip 相似度 | 往返相似度 | 原文与回译的重叠（BLEU/chrF/Jaccard）。**必须双边过滤**：太低=漂移，**太高=副本等于原文**（无效且浪费两次翻译）。 |
| 占位符替换 | placeholder masking | 翻译前把实体/数字换成 `<ENT_0>`/`<NUM_1>`，译后换回。工业界处理实体错译的标准做法。 |
| 否定奇偶检查 | negation parity check | 比较原文与增强的否定词计数。极其粗糙但**零成本**，能挡住大部分致命案例。「粗糙但零成本的过滤器」常优于「精细但昂贵的修正器」。 |

## 指令合成 · Instruction Synthesis

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Self-Instruct | 自指令 | Wang et al. 2023：175 条种子 → 52k 条指令数据。四步循环：采样 few-shot → 生成 → **过滤（去重是命门）** → 生成实例 → 自举。 |
| ROUGE-L 去重 | dedup by ROUGE-L | 与池中任一条相似度 >0.7 则丢弃。**打断「模式惯性正反馈」的唯一机制**（池子越单一 → few-shot 越单一 → 更单一）。阈值收紧 → 丢弃率超线性上升 → **成本直接翻倍**。 |
| 模式惯性 | mode inertia | LLM 在 few-shot 下倾向继续生成同类任务。给 8 个翻译例子它就继续生成翻译——这是同质化的机制来源。 |
| 输出优先 | output-first | 分类数据合成时**先定标签再造输入**。反之（输入优先）会得到教师的先验（不平衡、安全、常见）。**凡是让 LLM 生成带标签数据，都要问「标签分布由谁决定」**。 |
| Evol-Instruct | 演化指令 | WizardLM：用演化算子（加约束/深化/具体化/增加推理步/复杂化输入 + **广度演化**）迭代提升难度。深度演化**必须配广度演化**。 |
| 消除步骤 | elimination | 过滤演化失败的（与原指令等价、不可回答、已重复）。 |
| 难度伪装 | fake difficulty | 约束变多但**实际推理难度没变**。症状：合成数据的长度与约束数在涨，学生在真实难基准上没提升。防护：用**可验证的难度代理**（基座答对率）而非表观指标。 |
| Magpie | 无种子生成 | 只给「用户回合的起始模板」，让指令模型自己续写用户会问什么——本质是**反演对齐训练数据分布**。零种子、多样性高、**可控性最差**。 |
| 数据蒸馏 | data distillation | 用教师在无标注数据上打标签，当普通监督数据训学生。**跨架构唯一可行的路**（LLM→encoder，C49 模块 05）。 |
| 教师偏差传递 | teacher bias inheritance | 长度偏好、格式偏好、安全过度、**知识错误**、文化偏斜全部完整传递。其中知识错误最危险——它把错的当对的写进训练目标。 |
| 学生 ≤ 教师 | student ceiling | 合成数据的质量上限是教师。**不是「造更多数据」能绕过的**。所以正确用途是蒸馏而非创造知识（除弱到强泛化等特殊设置）。 |
| model collapse | 模式坍塌 | Shumailov et al. 2024：递归用上一代输出训练下一代 → 分布丢失尾部、向众数收缩。两个成因：统计误差（有限采样欠采尾部）+ 模型误差。 |
| 坍塌四征兆 | collapse symptoms | ①多样性降 ②长度分布收窄 ③高频模式占比升 ④嵌入覆盖收缩。**它们在下游指标崩溃之前就出现**——这是多样性指标真正的价值。 |

## 质量控制 · Quality Control

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| distinct-n | 独特 n-gram 比 | 不同 n-gram 数 ÷ 总数。越高越多样。盲区：对长度敏感、只看局部、**可被插入罕见词刷高**。 |
| self-BLEU | 自 BLEU | 每条与其余条的 n-gram 精确率均值。**越低越多样**。盲区：O(n²) 需采样、对同义改写不敏感。 |
| 嵌入覆盖 | embedding coverage | 嵌入投影后占据的网格/体积。抓**语义**覆盖。盲区：依赖嵌入质量、网格划分人为。 |
| contamination | 污染 | 训练数据混入评测集内容。**唯一「让指标变好」的失效** → 不会引起警觉 → **最危险**，所以去污染必须强制、自动、每次都跑。 |
| 三层去污染 | 3-layer decontamination | ①精确匹配（归一化后）②n-gram 重叠（n=8–13）③近重复检索（MinHash/嵌入）。**归一化是前提**；先用「故意注入」验证检测器本身。 |
| 先划分再增强 | split-before-augment | 铁律。「先增强后划分」会让同一原样本的副本分落训练与测试集 → 测试集已泄漏 → 所有指标虚高。把它写成断言。 |
| 流水线顺序 | pipeline order | 污染 → 保真 → 去重 → 多样性监测（**只报警不过滤**，因为多样性是集合属性，不能靠逐条过滤改善）。原则：先便宜后贵、先致命后次要。 |
| 分阶段丢弃率 | per-stage drop rate | **比最终保留率有用得多的诊断信号**：污染>1% → 教师见过测试集；保真>20% → 强度太大；去重>70% → 生成器同质化。可诊断性来自分解不来自汇总。 |

## 评测与消融 · Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 固定优化步数 | fixed training steps | 增强实验必须固定优化步数而非 epoch 数，否则「增强」与「训练更久」分不开（增强组会多跑数倍步数）。 |
| 复制对照 | duplication control | 同样把数据变成 N 倍但**不做任何扰动**。**C > B 才说明「多样性」有贡献**。这个对照几乎免费却能淘汰一大批假结论。 |
| 真实数据对照 | real-data control | 同预算下标注真实数据会怎样。**C > D 才说明这笔预算花在增强上更值**。几乎总被省略，且常给出否定答案。 |
| 配对比较 | paired comparison | A/B 用同一种子 → 结果高度正相关 → **差值方差显著更小** → 同样种子数能检出更小效应。**免费的方差削减**。 |
| 配对 bootstrap | paired bootstrap | 对每个种子的差值重采样，给出「无效」的经验概率。不假设正态，适合小样本小效应。先做 **A/A 检验**验证方法本身。 |
| 功效分析 | power analysis | 跑实验**之前**算「以这个种子数能检出多大效应」。若要 30 个种子而你只跑 3 个，实验从设计上就无法得出结论。**最省时间也最常被跳过的一步**。 |
| MDE | 最小可检出效应 | 给定种子数与噪声，能可靠检出的最小效应 ≈ (z_α+z_β)σ/√n。 |
| 混淆变量 | confounder | 增强天然同时改变了多个东西：样本数、优化步数、正则化强度、lr 调度的实际长度。**不固定这些，测到的「增强收益」里混着「训练更久的收益」**。 |
| A/A 检验 | A/A test | 用两组**相同**配置（只换种子）跑一遍统计流程，看它会不会报出显著。**先验证方法本身不会假阳性**，再拿它去测真实差异。这一步几乎免费却常被跳过。 |
| 种子方差 | seed variance | 只改随机种子带来的指标波动。小数据集微调上常达 2–3 分——**比大多数增强论文报告的效应还大**，这是「增强文献不可信」的直接原因。 |
| 效应量 vs 显著性 | effect size vs significance | 显著只说明「不太可能是噪声」，不说明「值得做」。**增强决策要看效应量与等价真实数据量，不是 p 值**。 |
| 学习曲线 | learning curve | 在多个数据量上比较。能读出**等价真实数据量**（水平位移）、收益消失点、以及是否改变斜率（平移 vs 真正提高样本效率）。 |
"""

REFERENCES = r"""
# 参考清单 · References（文本数据增强与合成数据工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C21** 讲预训练语料配比与合成数据在预训练中的角色；**C43** 讲 PB 级去重/过滤/流式的工程手艺；
> **C14** 讲合成数据理论与生成媒体评测；**C10/C03** 讲测量科学与评测统计；**C40** 讲研究方法论。
> **本课聚焦「有标注任务的训练集不够用时，怎么造与怎么验」。**

## 词面增强 · Lexical Augmentation
- ★ **Wei & Zou 2019, _EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks_** — 四操作的出处。**重点看两张图**：数据量-收益曲线（1% 数据涨 6 分、100% 数据涨 0.3 分）与 α 消融（0.1 附近最优、过大急降）。本课模块 01 的核心依据。
- ★ **Karimi, Rossi & Prakash 2021, _AEDA: An Easier Data Augmentation Technique for Text Classification_** — 只插标点，保真度精确 100%。它是「想清楚什么改动不破坏标签，比调参更有价值」的最好例子。
- **Zhang, Zhao & LeCun 2015, _Character-level Convolutional Networks for Text Classification_** — 同义词替换用于文本分类的早期实践（附录里的 thesaurus 方法）。
- **Feng et al. 2021, _A Survey of Data Augmentation Approaches for NLP_** — 把方法空间整理得最清楚的综述。适合快速定位「有哪些手段」，但要配合怀疑性复现工作一起读。
- **Jain et al. 2023, _NEFTune: Noisy Embeddings Improve Instruction Finetuning_** — 嵌入噪声这一类在线增强的代表：完全不动离散 token，保真度 100%。

## 语义增强 · Semantic Augmentation
- ★ **Sennrich, Haddow & Birch 2016, _Improving Neural Machine Translation Models with Monolingual Data_** — 回译的出处（原本用于 NMT 的合成源句）。
- ★ **Edunov, Ott, Auli & Grangier 2018, _Understanding Back-Translation at Scale_** — **本课模块 02 第二节的依据**：采样/加噪 beam 优于纯 beam。注意它的场景是「合成源句 + 真实目标句」，与分类增强的取舍不同（后者一旦漂移标签就错了）。
- ★ **Xie, Dai, Hovy, Luong & Le 2020, _Unsupervised Data Augmentation for Consistency Training_** — 把回译用于**一致性正则**而非直接增广（要求原样本与回译样本的预测分布一致）。它**绕开了保真度问题**（不用标签），是与本课主线互补的重要路线。
- **Sugiyama & Yoshinaga 2019, _Data Augmentation using Back-translation for Context-aware NMT_** — 回译在具体任务上的消融与失效分析。
- **Longpre, Wang & DuBois 2020, _How Effective is Task-Agnostic Data Augmentation for Pretrained Transformers?_** — **怀疑性复现的代表**：在预训练模型上，任务无关的增强收益大幅缩小。读它校准你对增强收益的预期。

## 指令数据合成 · Instruction Synthesis
- ★ **Wang et al. 2023, _Self-Instruct: Aligning Language Models with Self-Generated Instructions_** — 175 条种子 → 52k 数据。**重点读 §2 的四步循环、ROUGE-L 0.7 去重、以及分类任务的「输出优先」设计**（后者是防标签倾斜的关键，常被忽略）。
- ★ **Xu et al. 2023, _WizardLM: Empowering Large Language Models to Follow Complex Instructions_** — Evol-Instruct 的算子集与「消除」步骤。注意它同时有深度算子与广度算子——这个组合不是可选的。
- ★ **Xu et al. 2024, _Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing_** — 无种子生成，思路极其简洁（只给用户回合模板前缀）。理解它就理解了「合成数据本质是在反演模型分布」。
- ★ **Shumailov, Shumaylov, Zhao, Papernot, Anderson & Gal 2024, _AI models collapse when trained on recursively generated data_ (Nature)** — 模式坍塌的现象与机制（统计误差 + 模型误差）。**混入真实数据是主要缓解手段**这一结论出自这里。
- **Taori et al. 2023, _Stanford Alpaca_（技术报告与代码）** — Self-Instruct 的第一个大规模复现，工程细节最完整。
- **Burns et al. 2023, _Weak-to-Strong Generalization_** — 挑战「学生 ≤ 教师」的朴素结论：在某些设置下学生能超过弱监督。理解「合成数据的能力上限」这个问题的边界（C23 详读）。
- **Gunasekar et al. 2023, _Textbooks Are All You Need_（phi 系列）** — 高质量合成数据用于预训练的代表工作。与本课的下游增强场景不同，但「合成数据的质量比数量重要」这个结论互通。

## 多样性、去污染与质量控制 · QC
- ★ **Li, Galley, Brockett, Gao & Dolan 2016, _A Diversity-Promoting Objective Function for Neural Conversation Models_** — distinct-n 的出处。
- ★ **Zhu et al. 2018, _Texygen: A Benchmarking Platform for Text Generation Models_** — self-BLEU 的提出与多样性度量的系统讨论；也是「多样性度量可以被刷」这个问题的早期警示。
- ★ **Lee et al. 2021, _Deduplicating Training Data Makes Language Models Better_** — 去重与去污染的方法（精确子串 + MinHash）与必要性论证。**去污染与去重用同一套工具**这个观点出自它。C43 模块 01/05 有完整的工程实现。
- **Dodge et al. 2021, _Documenting Large Webtext Corpora: A Case Study on the Colossal Clean Crawled Corpus_** — 数据文档与污染审计的实践范例。
- **Sainz et al. 2023, _NLP Evaluation in Trouble: On the Need to Measure LLM Data Contamination_** — 污染检测的方法学与困难；理解「什么程度的相似算污染」为何没有客观定义。

## 在增强之外：用无标注数据的另外几条路 · Alternatives
> 增强不是「标注不够」的唯一解法。**决定用增强之前，先确认这几条路不适用**——它们常常更便宜、上限更高。
- ★ **Chen et al. 2020, _A Simple Framework for Contrastive Learning (SimCLR)_ 与 Gao et al. 2021, _SimCSE_** — 自监督对比学习：**用无标注数据学表示，再用少量标注微调**。SimCSE 的「dropout 即最小增强」是个漂亮的结果，也说明「增强越复杂越好」是错觉。
- ★ **Lee 2013, _Pseudo-Label_ 与 Xie et al. 2020, _Self-training with Noisy Student_** — 自训练：用模型自己在无标注数据上的预测当标签。**与本课模块 03 的蒸馏是同一族**，区别是教师就是自己的前一代。注意它同样有确认偏误与坍塌风险。
- **Sohn et al. 2020, _FixMatch_** — 半监督的强基线：弱增强产生伪标签、强增强上要求一致。**它把「增强」用作一致性约束而非样本扩增**，绕开了标签保真度问题（与 UDA 同源）。
- **Settles 2009, _Active Learning Literature Survey_** — 主动学习：**不造数据，而是挑最值得标注的数据**。在标注单价高的领域（本课模块 05 的「医疗」场景），它通常比增强的性价比更高，且两者可叠加。
- **Ratner et al. 2017, _Snorkel: Rapid Training Data Creation with Weak Supervision_** — 弱监督：用一组带噪的标注函数（规则、词典、远程监督）合成标签。**与本课模块 01 的「保护规则」思路相通**，但目标是造标签而不是造输入。

## 评测、统计与实验设计 · Evaluation
- ★ **Card, Henderson, Khandelwal, Jia, Mahowald & Jurafsky 2020, _With Little Power Comes Great Responsibility_** — **做任何小效应实验前必读**。系统论证大量 NLP 论文的统计功效不足（无法可靠检出它们报告的效应）。本课模块 05 的功效分析纪律出自这里。
- ★ **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping_** — 种子方差的系统研究（小数据集上仅换种子波动 2–3 分）。它让「涨了 1 分」这类结论必须重新审视。C49 模块 03 详读。
- ★ **Koehn 2004, _Statistical Significance Tests for Machine Translation Evaluation_** — bootstrap 重采样检验的经典。本课的配对 bootstrap 实现以它为准。
- **Reimers & Gurevych 2018, _Why Comparing Single Performance Scores Does Not Allow to Draw Conclusions About Machine Learning Approaches_** — 标题就是结论。与 Dodge 2020 对读。
- **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_** — 把方差来源（初始化、数据顺序、数据划分、超参）系统分解，并给出正确的比较协议。
- **Kaplan et al. 2020 / Hoffmann et al. 2022（缩放律）** — 真实数据有缩放律，合成数据没有。读它们理解「为什么合成数据缺乏可预测的收益曲线」是个真问题（C21 详读）。
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足，请补充")
