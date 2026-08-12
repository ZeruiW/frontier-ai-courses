#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C49 · 编码器与 Seq2Seq 模型家族。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c49_m00, c49_m01, c49_m02, c49_m03, c49_m04, c49_m05

CID = "C49_Encoder_Seq2Seq_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "Transformer 的三种形态（encoder-only / decoder-only / encoder-decoder）与它们的全部差异源头——一个注意力掩码矩阵的三种画法；纯 numpy 重建 + 与理论/公开量级对拍",
     c49_m00),
    ("01_mlm_bert", "01_讲解.html", "01_mlm_bert.ipynb",
     "01 · MLM 与双向编码器",
     "双向表示与自回归目标为何不可兼得 · MLM 的 80/10/10 补丁 · [CLS] 到底学到了什么 · NSP 被推翻的原因 · BERT 不能生成的三层理由 · 信号密度 0.15× 的代价",
     c49_m01),
    ("02_pretraining_objectives", "02_讲解.html", "02_pretraining_objectives.ipynb",
     "02 · 预训练目标与配方的改良",
     "RoBERTa：零架构改动提升 7 分 · ELECTRA：判别式目标把信号密度拉回 1.0 · DeBERTa：解耦注意力与相对位置 · ALBERT：参数量 ≠ 效率 · 四个正交维度的横向对比",
     c49_m02),
    ("03_finetuning", "03_讲解.html", "03_finetuning.ipynb",
     "03 · 下游微调三范式",
     "序列分类（[CLS] vs mean pooling）· token 分类与 BIO 约束解码（Viterbi）· span 抽取与联合搜索 · 判别式学习率与灾难性遗忘 · 指标陷阱（MCC / 实体级 F1 / EM 归一化）· 种子方差",
     c49_m03),
    ("04_encoder_decoder", "04_讲解.html", "04_encoder_decoder.ipynb",
     "04 · Encoder-Decoder",
     "cross-attention 是唯一的新组件 · T5 的 span corruption 与「万物皆文本」· BART 的五种噪声 · teacher forcing 的 off-by-one 与 exposure bias · beam search、长度惩罚与「beam 诅咒」",
     c49_m04),
    ("05_encoder_today", "05_讲解.html", "05_encoder_today.ipynb",
     "05 · 今天还要不要 encoder",
     "推理成本的千倍差距 · 知识蒸馏与 T² 因子 · LLM 造标注→蒸馏到 encoder · 句嵌入的各向异性与对比学习 · 双塔召回 + 交叉精排的成本-精度前沿 · 一棵可执行的选型决策树",
     c49_m05),
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
        title="编码器与 Seq2Seq 模型家族",
        subtitle="Transformer 不只有 decoder-only：BERT / RoBERTa / ELECTRA / DeBERTa 的双向编码，T5 / BART 的编码-解码，以及「今天到底该用哪个」的成本-精度决策 —— 纯 numpy 从零重建 · 中文讲解 + 英文术语",
        pills=["6 模块", "BERT · RoBERTa · ELECTRA · DeBERTa · T5 · BART",
               "纯 numpy + 与理论/暴力参考对拍", "掩码 · 目标 · 微调 · 生成 · 选型",
               "CPU only · 无需 GPU/预训练权重/联网"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em> 建立「这个设计解决了什么问题、代价是什么、今天还成立吗」的判断力，"
            "再跑 <em>notebook</em> 用纯 numpy <strong>把机制从零实现一遍</strong>——三种注意力掩码、MLM 的 80/10/10、"
            "RTD 判别式目标、解耦注意力、Viterbi 约束解码、span 联合搜索、cross-attention、span corruption、"
            "teacher forcing、beam search、知识蒸馏、InfoNCE——"
            "并对每个实现做<strong>三层对拍</strong>：与可证明的理论性质、与暴力枚举参考、与论文报告的公开量级。"
            "每个练习都有紧跟的 <code>assert</code> 自测判分。配套 <a href=\"glossary.md\">术语词典</a> 与 "
            "<a href=\"references.md\">参考清单</a>。"
            "本课的立场是：<strong>C01 教你从零写一个 decoder-only Transformer，C17 讲神经网络之前的经典 NLP，"
            "C20 讲现代架构组件</strong>；<strong>本课补「另外两种 Transformer 形态」及其独有的预训练目标与任务范式</strong>——"
            "这正是 JD 里 <code>BERT / RoBERTa / sequence-to-sequence models</code> 那几条对应的知识。"
            "<strong>本环境不加载预训练权重、不联网</strong>：因为本课要讲的是<em>设计选择</em>而不是<em>调 API</em>。"
            "「BERT 为什么不能生成」这种问题，读十篇博客不如自己用数值梯度测一遍——本课就让你测。"
            "想把这些概念变成能跑的真实代码（<code>transformers</code> / <code>Trainer</code> / <code>PEFT</code>），"
            "见配套的 <strong>C50</strong>。"
        ),
        tracks=[
            ("双向编码器主线 · Bidirectional Encoders", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "三种形态的全部差异只源于一个注意力掩码矩阵的形状；参数量账、三条对拍纪律，以及为什么「不加载权重」反而学得更透。"),
                ("01_mlm_bert/01_讲解.html", "MODULE 01", "MLM 与双向编码器",
                 "双向表示与自回归目标不可兼得的数值证明；MLM 的 15% 与 80/10/10 补丁在补什么洞；[CLS] 只有被训练过才有意义；NSP 如何被主题捷径攻破；MLM 不定义合法联合分布。"),
                ("02_pretraining_objectives/02_讲解.html", "MODULE 02", "预训练目标与配方的改良",
                 "RoBERTa 零架构改动提升 7 分（配方 > 架构）；ELECTRA 用判别式目标把信号密度从 0.15 拉回 1.0；DeBERTa 解耦内容与位置；ALBERT 证明参数量不是效率。"),
            ]),
            ("任务范式与生成 · Task Paradigms &amp; Generation", [
                ("03_finetuning/03_讲解.html", "MODULE 03", "下游微调三范式",
                 "分类 / token 标注 / span 抽取三种头；BIO 的合法性约束与 Viterbi（对拍暴力枚举）；span 联合搜索；判别式学习率；MCC、实体级 F1、EM 归一化三个指标陷阱；种子方差 2-3 分。"),
                ("04_encoder_decoder/04_讲解.html", "MODULE 04", "Encoder-Decoder",
                 "三种注意力的分工与 cross-attention 的可预计算性；T5 的 span corruption 省下一个数量级解码算力；BART 的五种噪声；teacher forcing 的 off-by-one；exposure bias；beam 越大反而越差。"),
            ]),
            ("今天的选型 · Choosing Today", [
                ("05_encoder_today/05_讲解.html", "MODULE 05", "今天还要不要 encoder",
                 "推理成本的千倍差距与「能不能跑 CPU」；知识蒸馏的 T² 因子；LLM 造标注→蒸馏到 encoder；句向量的各向异性；双塔召回 + 交叉精排的最优 k；一棵可执行的选型决策树。"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), """
# 编码器与 Seq2Seq 模型家族

Transformer 不只有 decoder-only。本课把 **encoder-only（BERT 系）** 与 **encoder-decoder（T5/BART）**
这两种被 LLM 叙事掩盖、但在工业界天天在跑的形态，从注意力掩码开始重建一遍，
并用成本-精度的账回答「今天到底该用哪个」。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | MLM 与双向编码器 | `01_mlm_bert/` |
| 02 | 预训练目标与配方的改良 | `02_pretraining_objectives/` |
| 03 | 下游微调三范式 | `03_finetuning/` |
| 04 | Encoder-Decoder | `04_encoder_decoder/` |
| 05 | 今天还要不要 encoder | `05_encoder_today/` |

## 这门课补什么洞
C01 从零写 decoder-only Transformer；C17 讲神经网络之前的经典 NLP；C20 讲现代架构组件。
中间缺的是 **BERT / RoBERTa / ELECTRA / DeBERTa 这条双向编码器主线**，以及
**T5 / BART 的 encoder-decoder 与 seq2seq 训练-解码全套**——
也就是 JD 里 `hands-on with GPT, BERT, RoBERTa` 与 `expertise in sequence-to-sequence models` 那两条。

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）建立「这个设计解决了什么问题、代价是什么、今天还成立吗」的判断，
再跑 `NN_*.ipynb` 用纯 numpy 从零实现：三种掩码 → MLM 与 80/10/10 → RTD 与解耦注意力 →
Viterbi 约束解码与 span 联合搜索 → cross-attention、span corruption、beam search → 蒸馏与两阶段检索。
每个实现做**三层对拍**：可证明的理论性质、暴力枚举参考、论文报告的公开量级。
先看 worked 示例（print + assert 自检）→ ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 真实量级胶囊。
所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，**不加载预训练权重、不需要 GPU、不联网**。
讲解与 notebook 末尾的「🔧 旁注」会指出每一步在 `transformers` 里叫什么、参数在哪；
想真正加载权重跑起来，见配套的 **C50（HuggingFace 生态与 API 实操）**。

配套：[术语词典](glossary.md) · [参考清单](references.md)
""")

    text_file(os.path.join(DIR, "requirements.txt"), """
# 编码器与 Seq2Seq 模型家族 —— 依赖清单
# 核心实现纯 numpy、CPU 可跑（assert 全过）：用迷你词表与随机初始化的小模型验证**机制**，
# 效果数字引用公开论文报告。本环境不加载预训练权重 / 不需要 GPU / 不联网。

numpy          # 核心：注意力、掩码、Viterbi、beam search、蒸馏、InfoNCE 的全部实现
pandas         # 可选：对比表格的展示
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel
""")

    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


GLOSSARY = r"""
# 术语词典 · Glossary（编码器与 Seq2Seq 模型家族）

> 按主题分组，每条 2–3 句释义。读 BERT / RoBERTa / T5 / BART 论文或 `transformers` 文档遇到生词回这里查；
> 英文术语保留原文。本课用纯 numpy 复现这些机制，但术语与真实模型一一对应。

## 三种形态与注意力 · Architectures & Attention

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| encoder-only | 仅编码器 | 用全 1（双向）注意力掩码，每个位置能看到序列全部位置。代表：BERT/RoBERTa/DeBERTa。表示最强，但**无法自回归生成**。 |
| decoder-only | 仅解码器 | 用下三角（因果）掩码，位置 t 只看 ≤t。代表：GPT/LLaMA。可自回归生成，训练与推理形式统一，预训练数据无限。 |
| encoder-decoder | 编码-解码 | 编码器双向 + 解码器因果 + 交叉注意力。代表：原始 Transformer/T5/BART。**Transformer 最初就是这个形态**，另两种是后来的裁剪。 |
| prefix-LM | 前缀语言模型 | 前缀内部双向、后缀因果的混合掩码（UniLM/GLM）。是 encoder-only 与 decoder-only 之间的连续插值，参数只有一套。 |
| bidirectional attention | 双向注意力 | 每个位置可注意所有位置。它使「预测下一个 token」退化成抄答案——这是 MLM 存在的根本原因。 |
| causal mask | 因果掩码 | 下三角掩码，保证 `∂out[t]/∂in[t+k]=0 (k>0)`。可用数值梯度直接验证（本课模块 00 就这么做）。 |
| cross-attention | 交叉注意力 | Q 来自解码器、K/V 来自**编码器输出**的注意力，矩阵形状是 (输出长, 输入长)。近似**词对齐**；其 K/V 只算一次可缓存。 |
| KV cache | KV 缓存 | 解码时缓存已算过的 K/V 避免重算。enc-dec 的 cross-KV 是固定的（算一次），self-KV 随生成增长；decoder-only 则全部随序列增长。 |

## 预训练目标 · Pretraining Objectives

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| MLM (masked language modeling) | 掩码语言建模 | 挖掉 15% 的 token 让模型据双向上下文恢复。源自语言学的 cloze test（Taylor 1953）。信号密度只有 0.15×，是它的核心代价。 |
| cloze test | 完形填空 | MLM 的智识来源，心理学/语言学用了七十年的阅读理解测试形式。 |
| 80/10/10 | 80/10/10 策略 | 被选中的 15% 位置：80% 换 `[MASK]`、10% 换随机词、10% 保持原样。**是个补丁**，补的是「`[MASK]` 在下游从不出现」这个分布不匹配。 |
| pretrain-finetune mismatch | 预训练-微调不匹配 | 预训练输入里有 `[MASK]`，下游一次都没有。会让模型学到「只在看到 `[MASK]` 时才建模上下文」的偷懒策略。 |
| NSP (next sentence prediction) | 下一句预测 | BERT 的第二个目标：判断句 B 是否紧跟句 A。**后被推翻**——负例来自不同文档，可被「主题匹配」捷径攻破。 |
| SOP (sentence order prediction) | 句序预测 | ALBERT 的替代：正例 A→B，负例 B→A（**同一对句子换顺序**）。主题相同，堵死了主题捷径，被证明比 NSP 有效。 |
| dynamic masking | 动态掩码 | RoBERTa：每个 epoch 重新采样掩码位置，而非预处理时固定。等于免费的数据增强。 |
| RTD (replaced token detection) | 替换 token 检测 | ELECTRA 的目标：小生成器替换部分 token，判别器对**每个位置**判断是否被替换。信号密度 1.0×，且输入无 `[MASK]`。 |
| span corruption | 片段破坏 | T5 的目标：连续片段整体换成一个哨兵 token，解码器只生成被挖内容。**目标序列短约 5 倍**，是 T5 的效率关键。 |
| sentinel token | 哨兵 token | T5 的 `<extra_id_0>`…`<extra_id_99>`，标记「这里挖了第几段」。不指示长度，所以任务不平凡。 |
| denoising autoencoder | 去噪自编码器 | BART 的范式：多种噪声破坏原文，模型重建**完整**原文。与 T5 的「只输出被挖内容」形成对照。 |
| text infilling | 文本填充 | BART 五种噪声中最有效的一项：连续片段换成**单个** mask（长度未知，可为 0）。同时训练恢复内容、判断长度、保持流畅。 |
| signal density | 信号密度 | 每次前向产生多少个训练预测。CLM/RTD 是 1.0×，MLM 只有 0.15×。但要乘上**每次信号的信息量**才是公平比较（MLM 每次 ~15 bit，RTD 只有 1 bit）。 |
| pseudo-perplexity | 伪困惑度 | MLM 的近似困惑度：逐位置掩掉一个 token 用其余上下文预测。**不可与 CLM 的困惑度直接比较**——MLM 的条件分布族互不相容，不存在对应的联合分布。 |

## 模型与改进 · Models & Improvements

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| BERT | BERT | 2018 年的双向编码器：MLM + NSP、WordPiece 30k、学习式绝对位置（**512 硬上限**）、post-LN。今天它的架构已明显过时。 |
| RoBERTa | RoBERTa | **零架构改动**、只重调配方（去 NSP、动态掩码、10× 数据、8k batch、更长训练）即提升 7 分。证明 BERT 严重欠训练。 |
| ELECTRA | ELECTRA | 用 RTD 替代 MLM，算力效率约 4×。生成器要「小」（1/4~1/2）是难度匹配；**不是 GAN**（无对抗梯度）；λ=50 让判别器拿到主要梯度。 |
| DeBERTa | DeBERTa | 解耦注意力（内容→内容、内容→位置、位置→内容三项）+ 相对位置 + EMD。v3 结合 RTD，至今是编码器任务的最强基线之一。 |
| disentangled attention | 解耦注意力 | 把 BERT 中纠缠的「内容+位置」注意力显式拆成三项分别计算。代价约 3× 注意力分数计算，且与 FlashAttention 等标准 kernel 不兼容。 |
| ALBERT | ALBERT | 嵌入分解 + 跨层参数共享 + SOP。**参数少 89% 但 FLOPs 一点不省**——层数没减。持久贡献是 SOP 与「参数量≠效率」这个澄清。 |
| T5 | T5 | 「万物皆文本」：所有任务转成文本到文本，靠任务前缀区分。思想被指令微调与 prompt 范式完全继承。代价是分类/回归失去输出空间约束。 |
| BART | BART | 去噪自编码的 enc-dec；解码器起始 token 用 `</s>` 而非 `<s>`（历史遗留，自己实现易踩坑）。 |
| relative position encoding | 相对位置编码 | 位置项只依赖 `i-j` 而非绝对位置。带来平移不变与小位置表（`2*max_rel+1` 行 vs BERT 的 512 行），也带来长度外推能力。 |

## 下游任务与解码 · Downstream & Decoding

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| sequence classification | 序列分类 | 用 `[CLS]` 或池化向量接一个 C 类 softmax。**要微调用 [CLS]，不微调抽向量用 mean pooling**。 |
| token classification | token 分类 | 每个位置一个标签（NER/POS）。输出空间有**语法约束**，必须做约束解码。 |
| BIO / IOB2 | BIO 标注 | `B-X` 实体开始、`I-X` 实体内部、`O` 非实体。合法性约束：`O→I-X` 非法、`B-PER→I-LOC` 非法。 |
| Viterbi decoding | 维特比解码 | `O(n·K²)` 动态规划求最优合法标签路径。相比一次前向的 1e10 FLOPs 完全可忽略——**零成本的正确性保证**。 |
| CRF layer | 条件随机场层 | 在 Viterbi 基础上把转移分数也变成可学参数。在强预训练模型上增益已明显缩小，但**约束解码本身仍必要**。 |
| entity-level F1 | 实体级 F1 | 按完整实体匹配算 F1（seqeval）。**token 级 F1 会系统性高估**——边界错一个 token，该实体就完全没抽对。 |
| span extraction | span 抽取 | 两个位置分类器给出 start/end logits。必须**联合搜索**（`end≥start`、限长度、限上下文区），否则会产出无效答案。 |
| EM / exact match | 精确匹配 | QA 指标。**必须先归一化**（小写、去标点、去冠词、压空格），否则低估 5-10 个点。 |
| MCC | 马修斯相关系数 | 综合混淆矩阵四格的指标，对类别不平衡鲁棒。GLUE 的 CoLA 用它。可以出现 accuracy 95% 而 MCC 0.00 的情况。 |
| discriminative fine-tuning | 判别式学习率 | 底层学习率更小（逐层 ×0.95）。底层学的是通用特征，改动它们收益小、破坏大。 |
| catastrophic forgetting | 灾难性遗忘 | 学习率过大时，几个 batch 就把预训练知识冲掉。这是微调学习率要比从头训练小 100 倍的原因。 |
| teacher forcing | 教师强制 | 训练时把**真实**目标右移一位喂给解码器，使所有位置并行计算（1 次前向 vs 推理的 m 次）。 |
| exposure bias | 暴露偏差 | 训练时喂真实前缀、推理时喂自己生成的前缀，导致错误累积。RLHF 的 on-policy 采样在解决同一个古老问题。 |
| beam search | 束搜索 | 每步保留 beam 条最优部分序列。分数需**长度归一化**（GNMT 的 `lp(t)=((5+t)/6)^α`），否则系统性偏好短输出。 |
| beam search curse | beam 诅咒 | beam 超过 5–10 后质量反而下降——更大的 beam 更接近真正的最大似然序列，而 MLE 模型的众数往往是退化的（过短/套话）。 |

## 训练与实现细节 · Training & Implementation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| WordPiece | WordPiece 分词 | BERT 的子词切分，未登录词切成 `##` 前缀的片段。30k 词表。RoBERTa 改用 byte-level BPE（无 UNK、跨语言更鲁棒）。 |
| whole word masking | 整词掩码 | 要掩就把一个词的**所有子词**一起掩掉。只掩一个子词会让任务退化成拼写补全（看到 `un` 和 `##able` 就能猜出中间）。实测有稳定提升。 |
| shallow vs deep bidirectional | 浅层 vs 深层双向 | ELMo 是两个独立单向 LSTM 最后拼接（浅层）；BERT 是**每一层的每个位置**都同时注意左右（深层）。这是 BERT 大幅超越 ELMo 的主要来源之一。 |
| warmup | 学习率预热 | 前若干步线性升到峰值 lr。Transformer 训练初期极不稳定（LayerNorm 与残差的相互作用），没有 warmup 常直接发散。 |
| two-stage sequence length | 两阶段序列长度 | BERT：90% 步数用 128 长度、10% 用 512。注意力是 O(L²)，这一招省约 84% 的注意力计算，同时让长位置嵌入得到训练。 |
| `[CLS]` / `[SEP]` | 特殊 token | `[CLS]` 是序列首位的汇总占位符，`[SEP]` 分隔句对与标记结束。`[CLS]` 的表示能力**完全来自有目标在训练它**。 |
| segment embedding | 片段嵌入 | 标记 token 属于句 A 还是句 B。为 NSP 服务；去掉 NSP 后很多模型简化掉了它。 |
| learned position embedding | 学习式位置嵌入 | 每个位置一个可学向量。**512 是物理硬上限**（索引越界，不是效果变差），且无法外推。被相对位置编码与 RoPE 取代。 |
| label smoothing | 标签平滑 | 把 one-hot 目标改成 `(1-ε)` 与均匀分布的混合。原始 Transformer 用 ε=0.1；能提升 BLEU 但会让困惑度变差。 |
| off-by-one (decoder shift) | 解码器错位 | teacher forcing 时 decoder 输入必须是目标**右移一位**。写错则每个位置的输入就是它要预测的目标，loss 迅速趋零但推理全是垃圾。 |
| seed variance | 种子方差 | 小数据集上仅换随机种子，微调分数可波动 2–3 分，甚至训崩。「涨了 1 分」通常需要十几个种子才站得住（Dodge et al. 2020）。 |
| linear probing | 线性探针 | 冻结主干、只训一个线性头。用来度量**表示质量**（而非预训练 loss）——低 loss ≠ 好表示。 |

## 蒸馏与检索 · Distillation & Retrieval

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| knowledge distillation | 知识蒸馏 | 用 teacher 的**完整概率分布**（软标签）训练 student，携带类间相似结构（dark knowledge），信息量远超 one-hot。 |
| temperature (T) | 温度 | `softmax(logits/T)`，T 越大分布越平滑、暴露越多类间结构。典型 2–5。 |
| T² scaling | T² 缩放 | 软标签梯度按 `1/T²` 衰减，必须乘 `T²` 补回。**忘了它，T=4 时蒸馏项梯度只剩 1/16，等于没做蒸馏**。 |
| data distillation | 数据蒸馏 | 用 teacher 在无标注数据上打标签，当普通监督数据训 student。**跨架构唯一可行的路**（LLM→encoder 的 logit 空间根本对不上）。 |
| DistilBERT | DistilBERT | 同架构 logit 蒸馏的标准配方：6 层、小 40%、快 60%、保留约 97% 的 GLUE 性能。 |
| bi-encoder | 双塔编码 | 查询与文档**分别**编码成向量，点积打分。**在线成本与语料规模无关**（文档向量离线预计算）——这是它不可替代的原因。 |
| cross-encoder | 交叉编码 | 查询与文档拼接后一起编码。精度最高但无法预计算，N 个候选就要 N 次前向。 |
| two-stage retrieval | 两阶段检索 | 双塔召回 top-k + 交叉编码精排。最优 k 在 recall 曲线拐点（通常 50–200）。是成本-精度前沿上的正确取点。 |
| anisotropy | 各向异性 | BERT 句向量挤在狭窄锥体里，任意两句余弦相似度都在 0.7+，失去区分度。缓解：白化、对比学习。 |
| InfoNCE | InfoNCE 损失 | 对比学习的标准损失：拉近正例对、推远负例。`τ`（温度）控制难度。 |
| hard negatives | 困难负例 | 用当前模型检索出的、排名靠前但实际不相关的样本。随机负例太容易区分，学不到细粒度。**负例设计决定学到什么**——这是 NSP/SOP/对比学习三次体现的同一条原理。 |
| SBERT / SimCSE | 句嵌入训练 | SBERT 用有监督 NLI 数据、SimCSE 用 dropout 作数据增强做对比学习，把 BERT 变成可用的句嵌入模型。 |
"""

REFERENCES = r"""
# 参考清单 · References（编码器与 Seq2Seq 模型家族）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C01** 从零写 decoder-only Transformer；**C17** 讲神经网络之前的经典 NLP；
> **C20** 讲现代架构组件（RoPE/GQA/MoE/SSM）；**C21** 讲大规模预训练的数据与缩放；
> **本课**补 encoder-only 与 encoder-decoder 这两种形态及其独有的目标与任务范式；
> **C50** 讲怎么用 HuggingFace 生态把它们真正跑起来。

## 三种形态与原始架构 · Architectures
- ★ **Vaswani et al. 2017, _Attention Is All You Need_** — 原始 Transformer，**encoder-decoder** 形态。重新精读一遍会发现很多细节被后来的教程简化掉了：cross-attention 的确切定义、warmup 调度、label smoothing、以及为什么当时选了 post-LN。本课模块 04 的一手来源。
- ★ **Devlin, Chang, Lee & Toutanova 2019, _BERT: Pre-training of Deep Bidirectional Transformers_** — encoder-only 路线的开创。**重点读第 3、5 节的消融**而不是结果表：MLM 的 80/10/10 消融、NSP 的贡献、以及四种下游范式的定义都在那里。
- ★ **Radford et al. 2018/2019, _Improving Language Understanding by Generative Pre-Training_ / _Language Models are Unsupervised Multitask Learners_** — decoder-only 路线。与 BERT 对读，能清楚看到「掩码形状决定一切」这条主线。
- **Dong et al. 2019, _Unified Language Model Pre-training (UniLM)_** — prefix-LM 的代表：用一个模型、三种掩码同时训练。理解三种形态是一个连续谱而非三个孤立点。
- **Tay et al. 2022, _UL2: Unifying Language Learning Paradigms_** — 在同等算力下系统比较 enc-dec / dec-only / prefix-LM，并提出混合去噪目标。目前对「哪种形态更好」这个问题最系统的实证工作。
- **Taylor 1953, _"Cloze Procedure": A New Tool for Measuring Readability_** — MLM 的智识来源。读它你会发现 BERT 的核心想法在语言学里已经用了七十年。

## 预训练目标的改良 · Objectives
- ★ **Liu et al. 2019, _RoBERTa: A Robustly Optimized BERT Pretraining Approach_** — **本课模块 02 的核心必读**。零架构改动、只重调配方即提升 7 分。重点读消融表，它系统地拆开了每一项改动（去 NSP、动态掩码、大 batch、更多数据、更长训练）的边际贡献。这篇论文对整个领域的方法论意义超过它的技术贡献。
- ★ **Clark, Luong, Le & Manning 2020, _ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators_** — 判别式目标把信号密度从 0.15 拉回 1.0，算力效率约 4×。**特别注意读它对「这不是 GAN」的澄清**（文本离散，生成器不接收对抗梯度）以及生成器规模的消融。
- ★ **He, Liu, Gao & Chen 2021, _DeBERTa: Decoding-enhanced BERT with Disentangled Attention_** 与 **He et al. 2023, _DeBERTaV3_** — 解耦注意力的推导与 EMD 的动机；v3 把 RTD 与解耦注意力结合。DeBERTa-v3 至今是编码器任务的最强开源基线之一，做 NLU 任务的起点应该是它而不是 bert-base。
- **Lan et al. 2020, _ALBERT: A Lite BERT_** — SOP 的提出（负例设计的经典案例）与参数共享的真实收益。读它主要为了理解「参数量 ≠ 效率」这个澄清。
- **Wettig, Gao, Zhong & Chen 2023, _Should You Mask 15% in Masked Language Modeling?_** — 推翻了 15% 是普适最优这个默认假设，发现更大模型适合更高掩码率。一个很好的「早期经验值被当成定律」的例子。
- **Wang & Cho 2019, _BERT has a Mouth, and It Must Speak: BERT as a Markov Random Field Language Model_** — 把 MLM 当 MRF 用 Gibbs 采样生成。读它理解「BERT 不能生成」的准确边界：不是不能，是代价很大。

## Encoder-Decoder 与生成 · Seq2Seq
- ★ **Raffel et al. 2020, _Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (T5)_** — **第 3 节是本领域最完整的架构/目标对比实验之一**：形态、目标、破坏率、片段长度、数据集全都做了系统消融。「万物皆文本」的思想被后来的指令微调与 prompt 范式完全继承。
- ★ **Lewis et al. 2020, _BART: Denoising Sequence-to-Sequence Pre-training_** — 五种噪声的消融，结论是 text infilling 最有效。与 T5 对读能看清「重建整句 vs 只输出被挖内容」这个设计分歧。
- ★ **Ranzato, Chopra, Auli & Zaremba 2016, _Sequence Level Training with Recurrent Neural Networks_** — exposure bias 的提出与序列级训练的早期尝试。这个概念在 RLHF 时代依然重要（on-policy 采样解决的是同一个问题）。
- **Wu et al. 2016, _Google's Neural Machine Translation System (GNMT)_** — 长度惩罚公式 `lp(t)=((5+t)/6)^α` 的出处，以及大规模 NMT 的完整工程配方。
- **Koehn & Knowles 2017, _Six Challenges for Neural Machine Translation_** — **beam search 诅咒的实证来源**：beam 增大反而降低 BLEU。它揭示了训练目标（MLE）与真实目标之间的系统性错位。
- **He, Peng et al. 2021, _On Exposure Bias in Neural Machine Translation_（及相关复盘工作）** — 论证 exposure bias 的影响在强模型上可能被高估。与 Ranzato 对读，理解一个被广泛引用的概念如何被后续工作重新审视。
- **Gu et al. 2018, _Non-Autoregressive Neural Machine Translation_** — 一次性并行生成全部输出。enc-dec 天然适合 NAT（编码器已给出完整输入表示），这条线在翻译上有实用价值。

## 下游任务与评估 · Downstream & Evaluation
- ★ **Rajpurkar et al. 2016, _SQuAD_ 与 2018, _Know What You Don't Know (SQuAD 2.0)_** — span 抽取范式的定义，以及「不可回答」如何用 `[CLS]` 作为 (0,0) span 优雅地表达。评估脚本里的答案归一化是本课模块 03 的一手来源。
- ★ **Wang et al. 2019, _GLUE_ 与 _SuperGLUE_** — 多任务基准。重点看它为每个任务选择指标的理由（为什么 CoLA 用 MCC 而不是 accuracy）。
- ★ **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping_** — **做微调实验前必读**。系统研究了种子方差：小数据集上仅换种子波动 2–3 分，甚至有些种子会训崩。它让「我的方法涨了 1 分」这类结论必须重新审视。
- **Howard & Ruder 2018, _Universal Language Model Fine-tuning (ULMFiT)_** — 判别式学习率、逐层解冻、斜三角学习率的提出。虽然写在 BERT 之前，但这些技巧至今有效。
- **Lample et al. 2016, _Neural Architectures for Named Entity Recognition_** — BiLSTM-CRF 与 BIO 约束解码的经典。理解 CRF 层在做什么，以及为什么在强预训练模型上它的增益变小了。
- **Ramshaw & Marcus 1995, _Text Chunking using Transformation-Based Learning_** — IOB 标注体系的起源。

## 蒸馏、句嵌入与检索 · Distillation & Retrieval
- ★ **Hinton, Vinyals & Dean 2015, _Distilling the Knowledge in a Neural Network_** — 软标签与温度的原始推导，**注意 `T²` 因子的来源**（软标签梯度按 `1/T²` 衰减）。dark knowledge 这个概念也出自这里。
- ★ **Sanh, Debut, Chaumond & Wolf 2019, _DistilBERT_** — 同架构蒸馏的标准配方（logit + 隐状态 + cosine 三项损失）：6 层、小 40%、快 60%、保留 97% 性能。
- ★ **Reimers & Gurevych 2019, _Sentence-BERT_** — **为什么原始 BERT 的句向量不能直接用**（比 GloVe 平均还差），以及怎么用孪生网络 + NLI 数据修好它。做检索/相似度前必读。
- ★ **Gao, Yao & Chen 2021, _SimCSE: Simple Contrastive Learning of Sentence Embeddings_** — 用 dropout 作为最小数据增强做无监督对比学习，并对各向异性给出了清晰的分析（alignment 与 uniformity）。
- ★ **Karpukhin et al. 2020, _Dense Passage Retrieval (DPR)_** — 双塔检索的标准做法与 **hard negatives 的重要性**。它把「负例设计决定学到什么」这条原理第三次摆到台面上。
- **Nogueira & Cho 2019, _Passage Re-ranking with BERT_** — 交叉编码精排的开创工作，两阶段检索架构的另一半。
- **Jiao et al. 2020, _TinyBERT_** — 中间层蒸馏（隐状态 + 注意力矩阵），信号比纯 logit 蒸馏更密集，但需要处理层数与维度对齐。
- **Muennighoff et al. 2023, _MTEB: Massive Text Embedding Benchmark_** — 嵌入模型的统一评估。既是选型参考，也提醒你注意「刷榜」与真实检索效果之间的差距。

## 跨课衔接 · Cross-course
- **C01 LLM 内核** — 从零实现 decoder-only Transformer。本课的注意力实现与它是同一套，只是掩码不同。
- **C17 经典 NLP** — word2vec / n-gram / HMM / CRF。本课模块 03 的 Viterbi 与 CRF 在那门课有完整的概率图模型基础。
- **C20 现代架构** — RoPE / GQA / MLA / MoE / SSM。模块 02 末尾讲的「编码器现代化」需要的组件全在那门课。
- **C27 模型压缩** — 量化、剪枝、蒸馏的系统处理。本课模块 05 的蒸馏只讲了与 encoder 选型相关的部分。
- **C11 RAG 与检索** — 向量检索、重排、RAG 评测。本课模块 05 的双塔/交叉编码是它的模型侧基础。
- **C50 HuggingFace 生态实操** — 把本课的每个概念变成能跑的真实代码（`AutoModel`、`Trainer`、`DataCollator`、`PEFT`）。**两课配套使用效果最好**。
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足，请补充")
