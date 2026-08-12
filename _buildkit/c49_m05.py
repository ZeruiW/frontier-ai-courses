# -*- coding: utf-8 -*-
"""C49 模块 05 · 今天还要不要 encoder：选型、蒸馏与检索两阶段。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–04；C24/C27 的推理与压缩概念有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_encoder_today.ipynb'),
    ("核心参考", "Hinton et al. 2015（蒸馏）、Sanh et al. 2019（DistilBERT）、Reimers & Gurevych 2019（SBERT）、Karpukhin et al. 2020（DPR）、Nogueira & Cho 2019（BERT reranker）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("question", "正面回答这个问题", "".join([
        P("学到这里，一个诚实的问题必须被正面回答：<strong>2026 年了，做一个文本分类任务，我到底该用 BERT 微调还是直接调 LLM</strong>？"),
        P("网上的答案通常是两个极端——「LLM 什么都能做，别折腾小模型了」或者「BERT 又快又准，别用大炮打蚊子」。<strong>两个都是坏答案，因为它们都没有给出判据</strong>。本模块要做的是把这个决策变成一个可以计算的问题。"),
        P("先把三种方案摆出来，看它们各自在什么维度上占优："),
        TABLE(["方案", "精度（有标注数据时）", "推理成本", "冷启动（无标注数据）", "可控性"], [
            ["<strong>encoder 微调</strong>（BERT/DeBERTa）", "★★★★★ 通常最高", "★★★★★ 1 次前向、110M 参数", "★ 需要几百到几千条标注", "★★★★★ 输出空间受约束"],
            ["<strong>LLM few-shot / zero-shot</strong>", "★★★ 中等，取决于任务", "★ 7B+ 参数、要生成", "★★★★★ <strong>零标注即可用</strong>", "★★ 可能输出格式外的东西"],
            ["<strong>LLM 微调</strong>（LoRA 等）", "★★★★★ 与 encoder 相当或略高", "★★ 仍是大模型", "★★ 需要标注（比 encoder 少些）", "★★★ 好一些"],
            ["<strong>LLM 蒸馏到 encoder</strong>", "★★★★ 接近 encoder 微调", "★★★★★ 同 encoder", "★★★★ <strong>用 LLM 造标注</strong>", "★★★★★ 同 encoder"],
        ]),
        DUAL(
            "最后一行是当今工业界最实用、也最被低估的答案：<strong>用 LLM 生成标注，用这些标注微调一个小 encoder，线上跑小的</strong>。它同时拿到了 LLM 的零标注启动能力和 encoder 的推理经济性。整个流程可以在几天内完成，成本是「几百美元的 LLM 调用 + 几小时的微调」，换来的是一个便宜三个数量级的线上服务。",
            "为什么便宜这么多？因为两件事叠乘：<strong>①参数量差 60 倍</strong>（110M vs 7B）；<strong>②前向次数差几十倍</strong>（encoder 1 次 vs LLM 生成 20 个 token 要 20 次 decode + 1 次 prefill）。<em>60 × 20 = 1200 倍</em>——这还没算 LLM 需要 GPU 而 encoder 可以跑 CPU。本模块的 notebook 会把这笔账精确算出来，你会看到从 <code>$X/百万次调用</code> 到 <code>$X/1000</code> 的差距。",
        ),
        CALLOUT("intuition", "但要公平：<strong>有三类情况 encoder 明确不适用</strong>。①输出是自由文本（改写、摘要、对话）——encoder 生成不了；②任务需要世界知识或复杂推理（「这段代码有什么安全隐患」）——小 encoder 没有这些能力；③需求变化极快、来不及标注和重训——LLM 改个 prompt 就上线了。<em>选型的第一个问题不是「哪个更准」，而是「我的任务落在哪一类」</em>。"),
    ])),
    ("cost", "推理成本：把差距算成数字", "".join([
        P("这一节把「便宜」变成可验证的数字。任务：对一段 128 token 的文本做二分类。"),
        MATH("\\text{FLOPs} \\approx 2 \\times N_{params} \\times N_{tokens\\_processed}"),
        P("这个经验公式（每个参数每个 token 约 2 次浮点运算，前向）足够做量级比较。关键在 <code>N_tokens_processed</code>——它对两种方案完全不同："),
        TABLE(["方案", "参数量", "处理的 token 数", "前向 FLOPs", "相对"], [
            ["BERT-base 分类", "110M", "128（一次编码）", "≈ 2.8×10¹⁰", "<strong>1×</strong>"],
            ["DeBERTa-v3-base", "184M", "128", "≈ 4.7×10¹⁰", "1.7×"],
            ["DistilBERT（6 层）", "66M", "128", "≈ 1.7×10¹⁰", "<strong>0.6×</strong>"],
            ["Llama-8B zero-shot（输出 5 token）", "8B", "128 prefill + 5 decode", "≈ 2.1×10¹² + 生成", "<strong>≈ 75×</strong>"],
            ["Llama-8B 输出 100 token（带解释）", "8B", "128 + 100", "≈ 3.6×10¹²", "<strong>≈ 130×</strong>"],
        ]),
        DUAL(
            "FLOPs 只是一半的故事，<strong>另一半是内存带宽</strong>。LLM 的 decode 阶段是 memory-bound 的——每生成一个 token 都要把全部权重从显存读一遍。8B 模型 fp16 是 16 GB，即使在 2 TB/s 带宽的卡上，理论上每步至少 8 ms。生成 100 个 token 就是 0.8 秒起。<em>而 BERT-base 的一次前向在同一张卡上是毫秒级</em>。",
            "还有一个更实际的维度：<strong>能不能跑在 CPU 上</strong>。BERT-base 在现代 CPU 上单条推理约 20–50 ms，完全可以在没有 GPU 的服务器上部署；量化后（INT8）可以到 10 ms 以内。8B LLM 在 CPU 上是几秒一个 token，实用性为零。<em>「不需要 GPU」这件事本身就是巨大的成本与运维差异</em>——这是 C48 模块 03/05 讨论的整个 GPU 调度与成本问题都可以跳过。",
        ),
        CALLOUT("warn", "一个必须诚实标注的边界：<strong>上面的对比是「同样做二分类」的场景</strong>。如果任务本身需要 LLM 的能力（推理、世界知识、生成），这个对比就不成立——不是 encoder 便宜 100 倍，而是 encoder <em>做不了</em>。<strong>成本比较只在「两者都能达到可接受精度」的前提下有意义</strong>。所以正确的顺序是：先确认 encoder 能不能达到精度要求（跑一个实验），能，再谈成本；不能，成本再低也没用。"),
    ])),
    ("distill", "蒸馏：把 LLM 的能力搬进小模型", "".join([
        P("既然大模型准、小模型快，自然的想法是<strong>让小模型学大模型</strong>。这就是 <span class=\"term\">knowledge distillation</span>（知识蒸馏，Hinton et al. 2015）。"),
        H3("为什么软标签比硬标签好"),
        P("蒸馏的核心不是「用大模型的预测当标签」，而是<strong>用大模型的完整概率分布当标签</strong>。区别很大："),
        ASCII("""一张图片/一段文本，教师模型的输出分布:

  硬标签 (one-hot):     [0, 1, 0, 0]           ← 只告诉你「是猫」
  软标签 (soft):        [0.02, 0.85, 0.12, 0.01]
                          狗    猫    虎   汽车
                                     ↑
                        「有点像虎」——这条信息在硬标签里完全丢失！

软标签携带的是**类间相似结构**（dark knowledge）：
  · 猫和虎相似，和汽车不相似
  · 这个样本有多典型（0.85 vs 0.99）
一个 4 类问题，硬标签给 log2(4)=2 bit，软标签给的信息多得多。""")
        ,
        MATH("\\mathcal{L} = \\alpha \\underbrace{\\text{CE}(y_{true}, p_{student})}_{\\text{硬标签}} + (1-\\alpha) \\underbrace{T^2 \\cdot \\text{KL}\\big(p^{T}_{teacher} \\,\\|\\, p^{T}_{student}\\big)}_{\\text{软标签，温度 } T}"),
        TABLE(["超参", "作用", "典型值", "注意"], [
            ["<strong>温度 T</strong>", "<code>softmax(logits/T)</code>，T 越大分布越平滑、暴露越多类间结构", "2 – 5", "T=1 退化为普通概率；T→∞ 趋于均匀"],
            ["<strong><code>T²</code> 缩放</strong>", "补偿软标签梯度随 <code>1/T²</code> 衰减", "必须有", "忘了它，蒸馏项的梯度会随 T 增大而消失"],
            ["<strong>α</strong>", "硬标签与软标签的权重", "0.1 – 0.5", "有真标签时保留一点硬标签通常更稳"],
        ]),
        DUAL(
            "<code>T²</code> 这个因子是最容易被漏掉的细节。软标签交叉熵对 student logits 的梯度里带一个 <code>1/T</code>，而 teacher 分布本身的平滑又贡献一个 <code>1/T</code>，合起来梯度按 <code>1/T²</code> 衰减。所以要乘 <code>T²</code> 把它补回来，否则 <code>T=4</code> 时蒸馏项的梯度只有硬标签项的 1/16，等于没做蒸馏。<em>notebook 会把这个梯度尺度直接测出来。</em>",
            "除了 logit 蒸馏，还有两类常用做法：<strong>①中间层蒸馏</strong>（让 student 的隐状态/注意力矩阵去拟合 teacher 的对应层，如 TinyBERT）——信号更密集但需要处理层数不匹配与维度对齐；<strong>②数据蒸馏</strong>（用 teacher 在<em>无标注数据</em>上打标签，然后当成普通监督数据训 student）——最简单、最工程友好，且<em>可以跨架构</em>（用 LLM 蒸馏到 encoder 就属于这类，因为二者的 logit 空间根本对不上）。",
        ),
        CALLOUT("intuition", "对「LLM → encoder」这个具体场景，<strong>只有数据蒸馏可行</strong>，因为两者的输出空间完全不同（LLM 输出的是 token 分布，encoder 输出的是类别分布）。但这反而简化了工程：<em>你只需要让 LLM 输出标签（甚至可以让它输出置信度当作软标签），然后当成普通标注数据用</em>。DistilBERT 那种同架构 logit 蒸馏是另一回事——它适用于「BERT → 小 BERT」，收益是 40% 更小、60% 更快、保留 97% 的 GLUE 性能。"),
    ])),
    ("retrieval", "检索：双塔与交叉编码的成本-精度前沿", "".join([
        P("这是 encoder 今天<strong>最不可替代</strong>的战场。检索/语义搜索/RAG 的召回环节，几乎全部由 encoder 承担。原因就在模块 03 提过的那个二分："),
        ASCII("""任务: 从 100 万个文档里找出与查询最相关的 10 个

方案 A: cross-encoder（交叉编码）
  对每个 (查询, 文档) 对拼在一起过模型 → 一个相关性分数
  ┌──────────────────────────────────┐
  │ [CLS] query [SEP] document [SEP] │──▶ BERT ──▶ score
  └──────────────────────────────────┘
  精度: ★★★★★（query 与 doc 的每个 token 都能互相注意）
  成本: **100 万次前向 / 每个查询**  ← 完全不可行

方案 B: bi-encoder（双塔）
  两边分别编码成向量，用点积/余弦打分
  query ──▶ BERT ──▶ q (768,)          ┐
  doc   ──▶ BERT ──▶ d (768,)          ┘──▶ score = q·d
  精度: ★★★（两边没有交互）
  成本: **文档向量离线预计算一次**；在线只编码 query（1 次）+ 向量检索（ANN，毫秒级）

方案 C: 两阶段（工业标准）
  ① bi-encoder 召回 top-100    （1 次前向 + ANN 检索）
  ② cross-encoder 精排 top-100 （100 次前向）
  精度: ★★★★☆   成本: 101 次前向 —— 可行！""")
        ,
        DUAL(
            "两阶段架构不是妥协，而是<strong>在成本-精度前沿上的正确取点</strong>。它利用了一个关键的不对称：<em>召回阶段只需要「不漏掉」（高 recall），不需要精确排序；精排阶段只需要处理很少的候选</em>。把「贵而准」的模型用在已经缩小到 100 个的候选集上，成本就从 100 万次降到 100 次。",
            "定量地看：设召回 <code>k</code> 个候选，双塔的 recall@k 是 <code>R(k)</code>，交叉编码在候选集内的精度是 <code>P</code>。端到端质量约为 <code>R(k) × P</code>，成本约为 <code>C_bi + k·C_cross</code>。<code>R(k)</code> 随 <code>k</code> 快速饱和（k=10→100 提升明显，100→1000 提升很小），而成本随 <code>k</code> 线性增长。<strong>所以最优 <code>k</code> 落在 <code>R(k)</code> 曲线的拐点附近</strong>，通常是 50–200。notebook 会把这条前沿画出来并求最优 k。",
        ),
        H3("句嵌入：为什么不能直接用 BERT 的 [CLS]"),
        P("模块 01 和 03 都提过这一点，这里给出完整的原因与解法。<strong>直接拿预训练 BERT 的 <code>[CLS]</code>（或 mean pooling）做句向量，效果比 GloVe 词向量平均还差</strong>（Reimers &amp; Gurevych 2019 的著名发现）。三个原因："),
        UL([
            "<strong><code>[CLS]</code> 没有被训练过</strong>（去掉 NSP 后尤其如此）——模块 01 已论证。",
            "<strong>各向异性（anisotropy）</strong>：BERT 的表示集中在一个狭窄锥体里，任意两句的余弦相似度都在 0.7+，失去区分度。",
            "<strong>训练目标错配</strong>：MLM 优化的是「从上下文恢复词」，不是「相似句子的向量应该接近」。这两个目标并不天然一致。",
        ]),
        P("解法是<strong>用对比学习专门训练句嵌入</strong>：SBERT 用有监督的 NLI 数据（蕴含对为正例、矛盾对为负例），SimCSE 用无监督的 dropout 作为数据增强（同一句过两次 dropout 得到正例对，batch 内其他句为负例）。核心损失是 <span class=\"term\">InfoNCE</span>："),
        MATH("\\mathcal{L} = -\\log \\frac{\\exp(\\text{sim}(q, d^+)/\\tau)}{\\exp(\\text{sim}(q, d^+)/\\tau) + \\sum_{d^-} \\exp(\\text{sim}(q, d^-)/\\tau)}"),
        CALLOUT("danger", "<p>对比学习有个决定成败的因素：<strong>负例的质量与数量</strong>。用 batch 内随机句子当负例（in-batch negatives）最简单，但这些负例太容易区分（主题都不同），模型学不到细粒度。<strong>hard negatives</strong>（用当前模型检索出来的、排名靠前但实际不相关的文档）能大幅提升效果，DPR 与后续工作都强调这一点。<em>这又回到了模块 01 的那条方法论：负例设计决定任务难度，也决定学到什么</em>——NSP 的失败、SOP 的成功、对比学习的 hard negative，是同一条原理的三次体现。</p>", "负例设计再次决定一切"),
    ])),
    ("when", "选型决策：一棵可执行的树", "".join([
        ASCII("""① 你的输出是什么？
   ├─ 自由文本（改写/摘要/对话/代码）
   │    └─▶ 生成式。短输入长输出 → decoder-only LLM
   │                 长输入短输出 → enc-dec（T5/BART 系）或 LLM，算 KV 账（模块 04）
   │
   └─ 标签 / 片段 / 向量  →  进入 ②

② 有多少标注数据？
   ├─ 0 条，且需求可能天天变
   │    └─▶ LLM zero/few-shot。**先上线，再看要不要优化**
   │
   ├─ 0 条，但需求稳定、量大
   │    └─▶ **LLM 造标注 → 蒸馏到 encoder**  ← 最被低估的方案
   │
   └─ 几百条以上  →  进入 ③

③ 推理量有多大？
   ├─ 小（每天几千次）
   │    └─▶ 怎么方便怎么来。工程时间比算力贵。
   │
   └─ 大（每天百万次 / 需要低延迟 / 要跑 CPU）
        └─▶ **encoder 微调**（DeBERTa-v3 起步，不是 bert-base）
             ├─ 还要更快 → 蒸馏 + INT8 量化（C27）
             └─ 是检索任务 → 双塔召回 + 交叉编码精排两阶段""")
        ,
        P("这棵树里有几个判断值得单独强调，因为它们与「直觉」相反："),
        TABLE(["常见直觉", "更准确的说法"], [
            ["「LLM 更强，所以精度更高」", "<strong>有足够标注数据时，微调过的 encoder 在<em>封闭标签集</em>任务上通常不输甚至更好</strong>。LLM 的优势是零样本与泛化，不是「在这个特定任务上更准」"],
            ["「小模型是过渡方案，早晚被淘汰」", "<strong>单位经济的差距是 100–1000 倍，不会因模型进步而消失</strong>。只要还存在「高频、简单、封闭」的任务，小模型就有位置"],
            ["「用 BERT 就够了」", "<strong><code>bert-base-uncased</code> 是 2018 年的技术</strong>。同等成本下 DeBERTa-v3 或现代化 encoder 明显更好（模块 02）"],
            ["「LLM 蒸馏很复杂」", "<strong>数据蒸馏就是「让 LLM 打标签，再当普通监督数据用」</strong>，几百行代码、几百美元、几天时间"],
            ["「检索用 LLM embedding 更好」", "取决于任务与预算。<strong>专门训练的小嵌入模型在很多检索基准上不输大模型 embedding，而且便宜几十倍</strong>；但跨语言/长文档场景大模型 embedding 有优势"],
        ]),
        CALLOUT("intuition", "还有一个纯工程的考量常被忽略：<strong>可控性与可测试性</strong>。encoder 分类器的输出必然落在预定义的标签集里，你可以为它写单元测试、算精确的混淆矩阵、设置阈值、做校准（C10）。LLM 输出的是自由文本，即使要求它「只输出 A 或 B」，也存在小概率输出别的东西——你必须写解析与兜底逻辑。<em>在需要严格 SLA 的生产环境里，「输出空间受约束」本身就是一个有价值的性质</em>，它不体现在任何 benchmark 分数上。"),
    ])),
    ("ledger", "算一笔账：一个真实的选型决策", "".join([
        P("场景：内容审核，判断一段用户评论是否违规。每天 200 万次调用，延迟要求 P95 &lt; 100 ms，已有 5000 条人工标注。"),
        TABLE(["方案", "精度（假设）", "单次成本", "日成本", "P95 延迟", "结论"], [
            ["Llama-8B zero-shot", "0.86", "$0.00012", "<strong>$240</strong>", "~800 ms", "❌ 延迟超标"],
            ["Llama-8B + LoRA 微调", "0.93", "$0.00012", "$240", "~800 ms", "❌ 延迟超标"],
            ["DeBERTa-v3-base 微调", "0.94", "$0.0000018", "<strong>$3.6</strong>", "~35 ms", "✅ <strong>推荐</strong>"],
            ["DistilBERT 蒸馏 + INT8", "0.92", "$0.0000004", "<strong>$0.8</strong>", "~12 ms", "✅ 极端成本敏感时"],
        ]),
        P("这张表里最刺眼的数字是 <strong>$240 vs $3.6</strong>——<em>67 倍</em>，一年是 8.6 万美元 vs 1300 美元。而精度差异是 0.93 vs 0.94（encoder 反而略高，因为有 5000 条领域内标注）。"),
        P("但表格没说的部分同样重要，必须诚实列出："),
        UL([
            "<strong>如果只有 0 条标注</strong>，LLM zero-shot 的 0.86 就是你能立刻拿到的；encoder 需要先标注或先蒸馏。<em>「立刻可用」有真实的商业价值。</em>",
            "<strong>如果违规类型每周都在变</strong>（新的规避手段），LLM 改 prompt 即可，encoder 要重新标注+重训。<em>迭代速度可能比成本更重要。</em>",
            "<strong>如果需要给出违规理由</strong>（给运营看的解释），encoder 给不了。这时可能需要「encoder 判断 + LLM 只对判为违规的少数样本生成解释」的混合方案——<em>又是一个两阶段架构。</em>",
        ]),
        CALLOUT("intuition", "把整门课浓缩成一句话：<strong>三种 Transformer 形态不是「进化的三个阶段」，而是「注意力掩码的三种画法」，各自在不同的任务形状上占优；今天的正确做法不是选一个，而是把它们组合成两阶段/混合架构，让贵的模型只处理少量真正需要它的样本</strong>。双塔召回 + 交叉精排是这样，LLM 造标注 + encoder 上线是这样，encoder 判断 + LLM 解释也是这样。<em>「用便宜的模型过滤，用贵的模型处理剩下的」是这个领域最通用、最被低估的架构模式。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>encoder 与 decoder 的能力边界</strong>：随着 decoder-only 规模增长，双向表示的优势在很多基准上被抹平。<em>在什么任务、什么规模下双向仍有不可替代的优势</em>，缺乏系统的实证刻画。有工作发现在需要精细 token 级理解的任务（NER、抽取）上 encoder 仍占优，但边界不清晰。",
            "<strong>LLM 作为标注器的可靠性</strong>：数据蒸馏的质量上限由 teacher 决定。LLM 标注的系统性偏差（位置偏好、长度偏好、对模糊样本的过度自信）会被 student 完整继承甚至放大。如何检测与校正这些偏差、以及需要多少人工标注来锚定，是活跃的实践问题（与 C03/C10 的 LLM-judge 研究同源）。",
            "<strong>嵌入模型的统一评估</strong>：MTEB 等基准推动了嵌入模型的发展，但也带来「刷榜」问题——针对基准优化的模型未必在真实检索中更好。检索质量与下游 RAG 效果之间的关系也不是单调的（更好的召回不一定带来更好的生成）。",
            "<strong>两阶段架构的联合优化</strong>：召回与精排通常分别训练，但它们的目标并不一致（召回要 recall，精排要 precision）。端到端联合训练、或让精排的信号回流指导召回（如 distillation from cross-encoder to bi-encoder）是有效但尚未标准化的方向。",
            "<strong>encoder 的现代化与规模化</strong>：把现代组件装进 encoder 已被证明有效（模块 02），但 encoder 的缩放律、以及「大 encoder」（10B+）是否有价值，几乎无人系统研究。<em>这可能是一个被规模化叙事掩盖的机会</em>。",
        ]),
        CALLOUT("paper", "必读：Hinton, Vinyals &amp; Dean 2015 <em>Distilling the Knowledge in a Neural Network</em>（软标签与温度的原始推导，注意 <code>T²</code> 因子的来源）、Sanh et al. 2019 <em>DistilBERT</em>（同架构蒸馏的标准配方）、Reimers &amp; Gurevych 2019 <em>Sentence-BERT</em>（为什么原始 BERT 的句向量不能用，以及怎么修）、Gao et al. 2021 <em>SimCSE</em>（无监督对比学习与各向异性分析）、Karpukhin et al. 2020 <em>DPR</em>（双塔检索与 hard negatives）、Nogueira &amp; Cho 2019 <em>Passage Re-ranking with BERT</em>（交叉编码精排）、Muennighoff et al. 2023 <em>MTEB</em>（嵌入模型的统一评估）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 今天还要不要 encoder（成本-精度前沿、蒸馏、两阶段检索）

目标：把 **推理成本模型 → 温度蒸馏与 T² 因子 → 双塔 vs 交叉编码 → 两阶段最优 k → 选型决策** 全部算清楚。

路线：FLOPs 与延迟账 → 软标签的信息量 → 蒸馏梯度的 T² 验证 → 各向异性演示 →
InfoNCE 与 hard negatives → 召回-精排成本-精度前沿 → 选型决策树 → ✏️ 练习 → 📖 答案 → 🧪 真实选型胶囊。

> 心智模型：**「用便宜的模型过滤，用贵的模型处理剩下的」是这个领域最通用、最被低估的架构模式。**"""),
    md("""## 1 · 推理成本：把「便宜」变成数字

`FLOPs ≈ 2 × 参数量 × 处理的 token 数`。关键差异在**处理的 token 数**：
encoder 编码一次；LLM 要 prefill + 每生成一个 token 再跑一遍全部权重。"""),
    code("""import numpy as np, math
rng = np.random.default_rng(0)

def forward_flops(params, n_tokens):
    return 2 * params * n_tokens

def encoder_cost(params, n_in):
    return forward_flops(params, n_in)

def llm_cost(params, n_in, n_out):
    prefill = forward_flops(params, n_in)
    decode  = sum(forward_flops(params, 1) for _ in range(n_out))   # 每步都要读全部权重
    return prefill + decode

N_IN = 128
configs = [
    ('DistilBERT (6L)',            'enc',  66e6,  0),
    ('BERT-base',                  'enc', 110e6,  0),
    ('DeBERTa-v3-base',            'enc', 184e6,  0),
    ('Llama-8B  输出5 token',      'llm',   8e9,  5),
    ('Llama-8B  输出100 token',    'llm',   8e9, 100),
    ('Llama-70B 输出100 token',    'llm',  70e9, 100),
]
base = encoder_cost(110e6, N_IN)
print(f"{'方案':<28s} {'FLOPs':>12s} {'相对BERT-base':>14s}")
rows = []
for name, kind, p, n_out in configs:
    f = encoder_cost(p, N_IN) if kind == 'enc' else llm_cost(p, N_IN, n_out)
    rows.append((name, f))
    print(f'{name:<28s} {f:>12.3e} {f/base:>13.1f}×')

f_bert = dict(rows)['BERT-base']
f_llm5 = dict(rows)['Llama-8B  输出5 token']
f_llm100 = dict(rows)['Llama-8B  输出100 token']
assert f_llm5 / f_bert > 50, 'LLM 即使只输出 5 token 也贵 50 倍以上'
assert f_llm100 > f_llm5, '输出越长越贵'
print(f'\\n✅ 同样做二分类：LLM(输出5tok) 比 BERT-base 贵 {f_llm5/f_bert:.0f}×，'
      f'带解释(100tok) 贵 {f_llm100/f_bert:.0f}×')"""),
    md("""### 延迟与「能不能跑 CPU」——比 FLOPs 更硬的约束

LLM 的 decode 是 **memory-bound**：每生成一个 token 都要把全部权重读一遍。"""),
    code("""def decode_latency_ms(params_bytes, bandwidth_gbps, n_out):
    '''memory-bound 下界：每步至少要读一遍权重。'''
    per_step_s = params_bytes / (bandwidth_gbps * 1e9)
    return per_step_s * n_out * 1000

def encoder_latency_ms(flops, tflops):
    return flops / (tflops * 1e12) * 1000

GPU_BW_GBPS, GPU_TFLOPS = 2000, 300      # H100 量级
CPU_TFLOPS = 0.5                          # 现代服务器 CPU 单路量级

print(f"{'方案':<28s} {'GPU延迟(ms)':>12s} {'CPU延迟(ms)':>12s} {'能跑CPU?':>9s}")
for name, kind, p, n_out in configs:
    if kind == 'enc':
        f = encoder_cost(p, N_IN)
        g, c = encoder_latency_ms(f, GPU_TFLOPS), encoder_latency_ms(f, CPU_TFLOPS)
    else:
        g = decode_latency_ms(p * 2, GPU_BW_GBPS, n_out) + encoder_latency_ms(forward_flops(p, N_IN), GPU_TFLOPS)
        c = decode_latency_ms(p * 2, 50, n_out)          # CPU 内存带宽约 50 GB/s
    ok = '✅' if c < 200 else '❌'
    print(f'{name:<28s} {g:>12.1f} {c:>12.1f} {ok:>9s}')

lat_bert_cpu = encoder_latency_ms(encoder_cost(110e6, N_IN), CPU_TFLOPS)
lat_llm_cpu = decode_latency_ms(8e9 * 2, 50, 100)
assert lat_bert_cpu < 200, 'BERT-base 在 CPU 上可用'
assert lat_llm_cpu > 5000, '8B 模型在 CPU 上生成 100 token 要几十秒 —— 实用性为零'
print(f'\\n✅ 「不需要 GPU」本身就是巨大的成本与运维差异：')
print(f'   BERT-base CPU {lat_bert_cpu:.0f}ms 可用 | Llama-8B CPU {lat_llm_cpu/1000:.0f}s 不可用')
print('   选 encoder 意味着 C48 里整个 GPU 调度与成本的问题都可以跳过。')"""),
    md("""## 2 · 蒸馏：软标签为什么比硬标签强

软标签携带**类间相似结构**（dark knowledge），硬标签只有 log2(C) bit。"""),
    code("""def softmax_T(logits, T=1.0):
    z = logits / T
    z = z - z.max()
    e = np.exp(z); return e / e.sum()

teacher_logits = np.array([1.0, 6.0, 3.5, -2.0])       # 狗 猫 虎 汽车
CLASSES = ['狗', '猫', '虎', '汽车']
print(f"{'温度':>5s} " + ' '.join(f'{c:>7s}' for c in CLASSES))
for T in [1.0, 2.0, 4.0, 8.0]:
    p = softmax_T(teacher_logits, T)
    print(f'{T:>5.1f} ' + ' '.join(f'{x:>7.3f}' for x in p))

hard = np.zeros(4); hard[1] = 1.0
def entropy(p): return -np.sum(p * np.log(p + 1e-12))
print(f'\\n硬标签熵: {entropy(hard):.3f} nat（0 = 只说「是猫」）')
for T in [1.0, 4.0]:
    print(f'软标签熵 (T={T}): {entropy(softmax_T(teacher_logits, T)):.3f} nat')

p1, p4 = softmax_T(teacher_logits, 1.0), softmax_T(teacher_logits, 4.0)
assert entropy(p4) > entropy(p1) > entropy(hard), '温度越高分布越平滑、信息越丰富'
assert p1[2] > p1[0] > p1[3], '软标签保留了「虎 > 狗 > 汽车」的相似结构'
print('\\n✅ 软标签告诉 student「这个样本有点像虎」—— 这条信息在 one-hot 里完全丢失。')"""),
    md("""### T² 因子：忘了它等于没做蒸馏

软标签交叉熵对 student logits 的梯度按 `1/T²` 衰减。**必须乘 T² 补回来。**"""),
    code("""def kd_grad_scale(teacher_logits, student_logits, T, use_T2=True):
    '''软标签 KL 项对 student logits 的梯度范数。'''
    pt = softmax_T(teacher_logits, T)
    ps = softmax_T(student_logits, T)
    grad = (ps - pt) / T                       # d KL / d student_logits
    if use_T2:
        grad = grad * (T ** 2)
    return float(np.abs(grad).sum())

student_logits = np.array([0.5, 2.0, 1.0, 0.0])
hard_grad = float(np.abs(softmax_T(student_logits, 1.0) - hard).sum())
print(f'硬标签项梯度范数: {hard_grad:.4f}\\n')
print(f"{'T':>5s} {'不乘T² ':>12s} {'乘T² ':>10s} {'不乘时相对硬标签':>18s}")
for T in [1.0, 2.0, 4.0, 8.0]:
    g_no = kd_grad_scale(teacher_logits, student_logits, T, use_T2=False)
    g_yes = kd_grad_scale(teacher_logits, student_logits, T, use_T2=True)
    print(f'{T:>5.1f} {g_no:>12.5f} {g_yes:>10.4f} {g_no/hard_grad:>17.1%}')

g_no_4 = kd_grad_scale(teacher_logits, student_logits, 4.0, use_T2=False)
g_no_1 = kd_grad_scale(teacher_logits, student_logits, 1.0, use_T2=False)
assert g_no_4 < g_no_1 / 5, 'T=4 时不乘 T²，梯度衰减一个量级以上'
g_yes_4 = kd_grad_scale(teacher_logits, student_logits, 4.0, use_T2=True)
assert g_yes_4 > g_no_4 * 10, 'T² 把梯度补回来'
print(f'\\n⚠️  T=4 且忘乘 T²：蒸馏项梯度只有硬标签项的 {g_no_4/hard_grad:.1%} —— 等于没做蒸馏。')
print('✅ T² 因子已验证')"""),
    md("""### 数据蒸馏：LLM → encoder 唯一可行的路

两者输出空间完全不同（token 分布 vs 类别分布），**只能走数据蒸馏**：
让 LLM 打标签（可带置信度当软标签），再当普通监督数据用。"""),
    code("""def simulate_data_distillation(n_unlabeled, teacher_acc, student_capacity=0.98, seed=0):
    '''student 的上限 = teacher 准确率 × student 容量系数。'''
    r = np.random.default_rng(seed)
    true_y = r.integers(0, 2, size=n_unlabeled)
    teacher_y = np.where(r.random(n_unlabeled) < teacher_acc, true_y, 1 - true_y)
    # student 在 teacher 标签上学到 student_capacity 的一致性
    student_y = np.where(r.random(n_unlabeled) < student_capacity, teacher_y, 1 - teacher_y)
    return (student_y == true_y).mean(), (teacher_y == true_y).mean()

print(f"{'teacher 准确率':>14s} {'student 准确率':>14s} {'损失':>7s}")
for ta in [0.80, 0.86, 0.92, 0.96]:
    sa, real_ta = simulate_data_distillation(20000, ta)
    print(f'{real_ta:>14.1%} {sa:>14.1%} {real_ta - sa:>7.1%}')

sa96, ta96 = simulate_data_distillation(20000, 0.96)
sa80, ta80 = simulate_data_distillation(20000, 0.80)
assert sa96 > sa80, 'teacher 越强，student 越强'
assert sa96 < ta96, 'student 一般不超过 teacher（除非有额外的真标注锚定）'
print('\\n✅ **student 的上限由 teacher 决定** —— 这也意味着 teacher 的系统性偏差会被完整继承。')
print('   实践建议：留一小份人工标注做验证集，用来检测蒸馏是否继承了 LLM 的偏差（C03/C10）。')"""),
    md("""## 3 · 句嵌入：为什么不能直接用预训练 BERT 的向量

**各向异性**：BERT 表示挤在一个狭窄锥体里，任意两句的余弦相似度都很高，失去区分度。"""),
    code("""D = 64

def make_anisotropic(n, d, cone_strength, seed=0):
    '''cone_strength 越大，向量越集中在一个主方向上（各向异性越强）。'''
    r = np.random.default_rng(seed)
    main = r.normal(size=d); main /= np.linalg.norm(main)
    X = r.normal(size=(n, d))
    X = X / np.linalg.norm(X, axis=1, keepdims=True)     # 先归一化噪声，再叠加主方向
    X = X + cone_strength * main
    return X / np.linalg.norm(X, axis=1, keepdims=True)

def mean_pairwise_cos(X, n_pairs=3000, seed=0):
    r = np.random.default_rng(seed)
    i = r.integers(0, len(X), n_pairs); j = r.integers(0, len(X), n_pairs)
    m = i != j
    return float((X[i[m]] * X[j[m]]).sum(1).mean())

print(f"{'各向异性强度':>12s} {'平均两两余弦':>13s} {'相似度动态范围':>15s}")
for cs in [0.0, 0.8, 1.5, 3.0]:
    X = make_anisotropic(600, D, cs)
    r_ = np.random.default_rng(1)
    i, j = r_.integers(0, 600, 3000), r_.integers(0, 600, 3000)
    cos = (X[i] * X[j]).sum(1)
    print(f'{cs:>12.1f} {mean_pairwise_cos(X):>13.3f} {cos.max()-cos.min():>15.3f}')

X_iso, X_aniso = make_anisotropic(600, D, 0.0), make_anisotropic(600, D, 3.0)
assert mean_pairwise_cos(X_aniso) > 0.7, '强各向异性下任意两句相似度都很高'
assert abs(mean_pairwise_cos(X_iso)) < 0.1, '各向同性时随机两句应接近正交'
print('\\n✅ 各向异性让「任意两句都很像」—— 余弦相似度失去区分度。')
print('   这就是 Reimers & Gurevych 发现「原始 BERT 句向量不如 GloVe 平均」的原因之一。')"""),
    code("""def whiten(X):
    '''白化：去均值 + 协方差归一化，缓解各向异性。'''
    mu = X.mean(0)
    Xc = X - mu
    cov = Xc.T @ Xc / len(X)
    U, S, _ = np.linalg.svd(cov)
    W = U @ np.diag(1.0 / np.sqrt(S + 1e-8))
    Y = Xc @ W
    return Y / np.linalg.norm(Y, axis=1, keepdims=True)

X_w = whiten(X_aniso)
print(f'白化前 平均余弦 {mean_pairwise_cos(X_aniso):>6.3f}')
print(f'白化后 平均余弦 {mean_pairwise_cos(X_w):>6.3f}')
assert abs(mean_pairwise_cos(X_w)) < abs(mean_pairwise_cos(X_aniso)) / 3
print('✅ 白化是零训练成本的缓解手段；更根本的解法是对比学习（SBERT / SimCSE）')"""),
    md("""### InfoNCE 与 hard negatives：负例设计再次决定一切"""),
    code("""def info_nce(q, d_pos, d_negs, tau=0.05):
    '''InfoNCE 损失。'''
    s_pos = float(q @ d_pos) / tau
    s_negs = np.array([float(q @ d) for d in d_negs]) / tau
    all_s = np.concatenate([[s_pos], s_negs])
    all_s = all_s - all_s.max()
    return -(all_s[0] - np.log(np.exp(all_s).sum()))

r = np.random.default_rng(3)
q = r.normal(size=D); q /= np.linalg.norm(q)
d_pos = q + r.normal(size=D) * 0.3; d_pos /= np.linalg.norm(d_pos)

def make_negs(kind, n=16):
    negs = []
    for _ in range(n):
        if kind == 'random':
            v = r.normal(size=D)                       # 随机负例：与 q 几乎正交
        else:
            v = q + r.normal(size=D) * 0.45            # hard negative：很像但不是
        negs.append(v / np.linalg.norm(v))
    return negs

for kind in ['random', 'hard']:
    negs = make_negs(kind)
    loss = info_nce(q, d_pos, negs)
    sim = np.mean([float(q @ n_) for n_ in negs])
    print(f'{kind:>7s} negatives: 平均相似度 {sim:>6.3f} | InfoNCE 损失 {loss:>6.3f}')

loss_rand = info_nce(q, d_pos, make_negs('random'))
loss_hard = info_nce(q, d_pos, make_negs('hard'))
assert loss_hard > loss_rand, 'hard negatives 让任务更难 -> 损失更大 -> 梯度信号更有用'
print('\\n✅ 随机负例太容易区分（主题都不同），模型学不到细粒度。')
print('   这与模块 01 的 NSP 失败、SOP 成功是**同一条原理的第三次体现**：')
print('   **负例设计决定任务难度，也决定模型学到什么。**')"""),
    md("""## 4 · 两阶段检索：成本-精度前沿与最优 k

召回只需「不漏掉」，精排只处理少量候选。**最优 k 落在 recall 曲线的拐点。**"""),
    code("""N_DOCS = 1_000_000

def recall_at_k(k, saturation=30.0, ceiling=0.99):
    '''双塔召回的 recall@k：随 k 快速饱和。'''
    return ceiling * (1 - math.exp(-k / saturation))

def two_stage_quality(k, cross_precision=0.95):
    return recall_at_k(k) * cross_precision

def two_stage_cost(k, bi_flops=2.8e10, cross_flops=2.8e10, ann_flops=1e8):
    '''1 次 query 编码 + ANN 检索 + k 次交叉编码。'''
    return bi_flops + ann_flops + k * cross_flops

print(f"{'k':>6s} {'recall@k':>9s} {'端到端质量':>10s} {'成本(FLOPs)':>13s} {'质量/成本':>11s}")
best_k, best_ratio = None, -1
for k in [1, 10, 50, 100, 200, 500, 1000]:
    q_, c_ = two_stage_quality(k), two_stage_cost(k)
    ratio = q_ / (c_ / 1e10)
    if ratio > best_ratio: best_ratio, best_k = ratio, k
    print(f'{k:>6d} {recall_at_k(k):>9.3f} {q_:>10.3f} {c_:>13.3e} {ratio:>11.4f}')

# 全量交叉编码（方案 A）：完全不可行
full_cross = N_DOCS * 2.8e10
print(f'\\n全量交叉编码 {N_DOCS:,} 文档: {full_cross:.3e} FLOPs')
print(f'两阶段 (k=100):              {two_stage_cost(100):.3e} FLOPs')
print(f'节省 {full_cross / two_stage_cost(100):,.0f}×')
assert two_stage_cost(100) < full_cross / 1000, '两阶段应便宜 3 个数量级以上'
assert two_stage_quality(100) > 0.9, '且质量仍在 0.9 以上'
# recall 饱和：k 从 100 到 1000 提升很小，成本却涨 10 倍
gain = recall_at_k(1000) - recall_at_k(100)
cost_up = two_stage_cost(1000) / two_stage_cost(100)
assert gain < 0.20 and cost_up > 5, f'k 100->1000: recall 只涨 {gain:.3f} 但成本涨 {cost_up:.1f}×'
print(f'\\n✅ k: 100->1000 recall 只涨 {gain:.3f}，成本涨 {cost_up:.1f}× —— 最优 k 在拐点附近（50~200）')"""),
    md("""### 双塔的可预计算性：这才是它不可替代的原因"""),
    code("""def bi_encoder_online_cost(n_docs, query_flops=2.8e10, ann_flops=1e8):
    '''文档向量**离线**预计算，在线只编码 query + ANN。与 n_docs 几乎无关！'''
    return query_flops + ann_flops

def cross_encoder_online_cost(n_docs, pair_flops=2.8e10):
    return n_docs * pair_flops

print(f"{'语料规模':>12s} {'双塔在线':>13s} {'交叉编码在线':>15s} {'倍数':>12s}")
for n in [1_000, 100_000, 10_000_000]:
    b, c = bi_encoder_online_cost(n), cross_encoder_online_cost(n)
    print(f'{n:>12,d} {b:>13.2e} {c:>15.2e} {c/b:>11,.0f}×')

b1k, b10m = bi_encoder_online_cost(1_000), bi_encoder_online_cost(10_000_000)
assert abs(b1k - b10m) < 1e-9, '**双塔的在线成本与语料规模无关** —— 这是它的核心价值'
print('\\n✅ 双塔的在线成本**与语料规模无关**（文档向量离线算好）。')
print('   交叉编码则随语料线性增长。这就是「交互带来精度，独立带来可预计算」。')"""),
    md("""## ✏️ 练习 1：蒸馏损失

实现 `distillation_loss(teacher_logits, student_logits, true_label, T=4.0, alpha=0.3)`：
返回 `alpha * CE(hard) + (1-alpha) * T² * KL(teacher_T || student_T)`。
KL 用 `Σ p_t * (log p_t - log p_s)`。"""),
    code("""def distillation_loss(teacher_logits, student_logits, true_label, T=4.0, alpha=0.3):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
tl = np.array([1.0, 6.0, 3.5, -2.0]); sl = np.array([0.5, 2.0, 1.0, 0.0])
loss = distillation_loss(tl, sl, true_label=1)
assert loss > 0
# student 完全模仿 teacher 时，KL 项应为 0
loss_perfect = distillation_loss(tl, tl, true_label=1)
kl_part = loss_perfect - 0.3 * (-math.log(softmax_T(tl, 1.0)[1]))
assert abs(kl_part) < 1e-9, 'student==teacher 时 KL 项必须为 0'
# alpha=1 时退化为纯硬标签
loss_hard_only = distillation_loss(tl, sl, 1, alpha=1.0)
assert abs(loss_hard_only - (-math.log(softmax_T(sl, 1.0)[1]))) < 1e-9
# T 越大，KL 项（乘过 T² 后）不应塌陷
l_t2 = distillation_loss(tl, sl, 1, T=2.0, alpha=0.0)
l_t8 = distillation_loss(tl, sl, 1, T=8.0, alpha=0.0)
assert l_t2 > 0 and l_t8 > 0
print(f'完整蒸馏损失 {loss:.4f} | 纯硬标签 {loss_hard_only:.4f} | student=teacher {loss_perfect:.4f}')
print('✅ 练习 1 通过')"""),
    md("""## ✏️ 练习 2：两阶段的最优 k

实现 `optimal_k(quality_fn, cost_fn, k_candidates, min_quality)`：
在满足 `quality_fn(k) >= min_quality` 的候选里，返回**成本最低**的 k。
无解返回 `None`。"""),
    code("""def optimal_k(quality_fn, cost_fn, k_candidates, min_quality):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
ks = [1, 10, 25, 50, 100, 200, 500, 1000]
k = optimal_k(two_stage_quality, two_stage_cost, ks, min_quality=0.90)
assert k is not None and two_stage_quality(k) >= 0.90
assert all(two_stage_cost(k) <= two_stage_cost(x) for x in ks if two_stage_quality(x) >= 0.90)
k_strict = optimal_k(two_stage_quality, two_stage_cost, ks, min_quality=0.94)
assert k_strict > k, '更高的质量要求需要更大的 k'
assert optimal_k(two_stage_quality, two_stage_cost, ks, min_quality=0.999) is None, '不可达时返回 None'
print(f'质量≥0.90 -> k={k} (成本 {two_stage_cost(k):.2e})')
print(f'质量≥0.94 -> k={k_strict} (成本 {two_stage_cost(k_strict):.2e})')
print('✅ 练习 2 通过：k 不是拍脑袋定的，是从质量约束反解出来的')"""),
    md("""## ✏️ 练习 3：选型决策树

实现 `choose_architecture(output_type, n_labeled, daily_calls, latency_budget_ms)`：
按讲解里的决策树返回方案字符串。
- `output_type='free_text'` → `'generative'`
- 否则若 `n_labeled == 0` → `'llm_zero_shot'`（若 `daily_calls < 100_000`）或 `'llm_distill_to_encoder'`
- 否则若 `daily_calls >= 100_000 or latency_budget_ms < 200` → `'encoder_finetune'`
- 否则 → `'either'`"""),
    code("""def choose_architecture(output_type, n_labeled, daily_calls, latency_budget_ms):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert choose_architecture('free_text', 5000, 1000, 5000) == 'generative'
assert choose_architecture('label', 0, 1000, 5000) == 'llm_zero_shot'
assert choose_architecture('label', 0, 2_000_000, 5000) == 'llm_distill_to_encoder'
assert choose_architecture('label', 5000, 2_000_000, 5000) == 'encoder_finetune'
assert choose_architecture('label', 5000, 1000, 100) == 'encoder_finetune', '低延迟要求也指向 encoder'
assert choose_architecture('label', 5000, 1000, 5000) == 'either'
cases = [('label', 0, 2_000_000, 100), ('span', 800, 500_000, 80), ('free_text', 0, 10, 60_000)]
for c in cases:
    print(f'{str(c):<38s} -> {choose_architecture(*c)}')
print('✅ 练习 3 通过：选型的第一个问题不是「哪个更准」，而是「任务落在哪一类」')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def distillation_loss(teacher_logits, student_logits, true_label, T=4.0, alpha=0.3):
    ps1 = softmax_T(student_logits, 1.0)
    hard = -math.log(ps1[true_label] + 1e-12)
    pt, ps = softmax_T(teacher_logits, T), softmax_T(student_logits, T)
    kl = float(np.sum(pt * (np.log(pt + 1e-12) - np.log(ps + 1e-12))))
    return alpha * hard + (1 - alpha) * (T ** 2) * kl"""),
    code("""# 练习 2 参考答案
def optimal_k(quality_fn, cost_fn, k_candidates, min_quality):
    feasible = [k for k in k_candidates if quality_fn(k) >= min_quality]
    return min(feasible, key=cost_fn) if feasible else None"""),
    code("""# 练习 3 参考答案
def choose_architecture(output_type, n_labeled, daily_calls, latency_budget_ms):
    if output_type == 'free_text':
        return 'generative'
    if n_labeled == 0:
        return 'llm_zero_shot' if daily_calls < 100_000 else 'llm_distill_to_encoder'
    if daily_calls >= 100_000 or latency_budget_ms < 200:
        return 'encoder_finetune'
    return 'either'"""),
    md("""---
## 🧪 真实数据胶囊：一个内容审核系统的选型

每天 200 万次调用，P95 延迟 < 100ms，已有 5000 条人工标注。把四个方案的账全算出来。"""),
    code("""DAILY_CALLS, LATENCY_BUDGET_MS = 2_000_000, 100
GPU_USD_PER_HOUR, GPU_TFLOPS_EFF = 4.0, 150      # 有效算力（考虑利用率）
CPU_USD_PER_HOUR, CPU_TFLOPS_EFF = 0.15, 0.3

def cost_per_call(flops, usd_per_hour, tflops_eff):
    seconds = flops / (tflops_eff * 1e12)
    return seconds / 3600 * usd_per_hour

# 统一按 GPU 计价做「同口径」比较：单位算力上 GPU 比 CPU 更便宜，
# 所以 encoder 的优势**完全来自 FLOPs 少 45 倍**，而不是「换了便宜的硬件」。
options = [
    # (名称, FLOPs, 延迟ms, 精度, 用GPU?)
    ('Llama-8B zero-shot',   llm_cost(8e9, N_IN, 5),    820, 0.86, True),
    ('Llama-8B + LoRA',      llm_cost(8e9, N_IN, 5),    820, 0.93, True),
    ('DeBERTa-v3-base 微调', encoder_cost(184e6, N_IN),  35, 0.94, True),
    ('DistilBERT 蒸馏+INT8', encoder_cost(66e6, N_IN)/2, 12, 0.92, True),
]
print(f"{'方案':<24s} {'精度':>5s} {'延迟ms':>7s} {'单次$':>11s} {'日成本$':>9s} {'年成本$':>10s} {'可行':>5s}")
results = []
for name, fl, lat, acc, use_gpu in options:
    c = cost_per_call(fl, GPU_USD_PER_HOUR, GPU_TFLOPS_EFF) if use_gpu \\
        else cost_per_call(fl, CPU_USD_PER_HOUR, CPU_TFLOPS_EFF)
    daily, yearly = c * DAILY_CALLS, c * DAILY_CALLS * 365
    ok = lat <= LATENCY_BUDGET_MS
    results.append((name, acc, lat, daily, yearly, ok))
    print(f'{name:<24s} {acc:>5.2f} {lat:>7d} {c:>11.8f} {daily:>9.2f} {yearly:>10,.0f} {"✅" if ok else "❌":>5s}')

feasible = [r for r in results if r[5]]
assert len(feasible) == 2, '只有两个 encoder 方案满足延迟要求'
best = max(feasible, key=lambda r: r[1])
llm_daily = results[1][3]; enc_daily = best[3]
print(f'\\n可行方案里精度最高: 「{best[0]}」 精度 {best[1]:.2f}, 日成本 ${best[3]:.2f}')
assert llm_daily / enc_daily > 20, 'LLM 方案应贵一个数量级以上'
print(f'相比 LLM+LoRA（精度 0.93）: 成本低 {llm_daily/enc_daily:.0f}×，且精度还高 0.01')
print(f'年度差额: ${results[1][4]:,.0f} vs ${best[4]:,.0f}')
print('（注：这里 encoder 也按 GPU 计价，所以优势**纯粹来自 FLOPs 少 45 倍**；')
print('  若改跑 CPU，单位算力更贵但省掉整套 GPU 运维——那是另一笔账，见 C48。）')
print('\\n⚠️  但表格没说的部分同样重要：')
print('   · 若只有 0 条标注 -> LLM zero-shot 的 0.86 是你**立刻**能拿到的')
print('   · 若违规类型每周在变 -> LLM 改 prompt 即可，encoder 要重标+重训')
print('   · 若需要给出违规理由 -> encoder 给不了，需要混合方案')"""),
    md("""**🧪 胶囊练习**：实现 `hybrid_cost(daily_calls, flag_rate, cheap_flops, expensive_flops)`：
混合架构——便宜的 encoder 处理全部流量，只有被标记为「违规」的 `flag_rate` 比例
才送给 LLM 生成解释。返回 `(总FLOPs, 相对全用LLM的节省比例)`。"""),
    code("""def hybrid_cost(daily_calls, flag_rate, cheap_flops, expensive_flops):
    # TODO: total = daily_calls*cheap_flops + daily_calls*flag_rate*expensive_flops
    #       all_llm = daily_calls * expensive_flops
    #       返回 (total, 1 - total/all_llm)
    raise NotImplementedError"""),
    code("""# 自测
cheap = encoder_cost(184e6, N_IN)
expensive = llm_cost(8e9, N_IN, 100)
total, saving = hybrid_cost(DAILY_CALLS, 0.02, cheap, expensive)
print(f'全用 LLM:  {DAILY_CALLS*expensive:.3e} FLOPs/天')
print(f'混合(2%):  {total:.3e} FLOPs/天  -> 省 {saving:.1%}')
assert saving > 0.90, '只有 2% 流量走 LLM，应省 90% 以上'
# flag_rate 越高，节省越少
_, s20 = hybrid_cost(DAILY_CALLS, 0.20, cheap, expensive)
assert s20 < saving, '标记率越高，混合架构的优势越小'
print(f'若标记率 20%: 只省 {s20:.1%}')
print('\\n✅ 胶囊练习通过：**「用便宜的模型过滤，用贵的模型处理剩下的」**')
print('   —— 双塔召回+交叉精排、LLM造标注+encoder上线、encoder判断+LLM解释，')
print('   都是这同一个模式。这是本领域最通用、最被低估的架构原则。')"""),
    code("""# 📖 胶囊参考答案
def hybrid_cost(daily_calls, flag_rate, cheap_flops, expensive_flops):
    total = daily_calls * cheap_flops + daily_calls * flag_rate * expensive_flops
    all_llm = daily_calls * expensive_flops
    return total, 1 - total / all_llm"""),
    md("""---
## 🔧 旁注：真实库里这些对应什么

- **蒸馏** → `transformers` 没有内置 Trainer；标准做法是自定义 `compute_loss` 加 KL 项。DistilBERT 的训练脚本在 `examples/research_projects/distillation`。
- **句嵌入** → `sentence-transformers`：`SentenceTransformer('all-MiniLM-L6-v2')`；训练用 `MultipleNegativesRankingLoss`（就是 InfoNCE + in-batch negatives）。
- **双塔检索** → `faiss` / `hnswlib` 做 ANN；DPR 的实现在 `transformers.DPRQuestionEncoder` / `DPRContextEncoder`。
- **交叉编码精排** → `sentence-transformers.CrossEncoder`；或 `AutoModelForSequenceClassification` 直接吃句对。
- **hard negatives 挖掘** → 用当前模型检索 top-k，排除真正的正例，剩下的当 hard negatives 迭代训练。
- **INT8 量化** → `optimum.onnxruntime` 或 `bitsandbytes`；encoder 的动态量化几乎无损（C27）。

怎么把这些串成一条真实管线，见 **C50**（生态实操）与 **C11**（RAG 与检索）。"""),
    md("""### 小结
- **成本差距是 60(参数) × 20(前向次数) ≈ 千倍量级**，且 encoder 能跑 CPU——这意味着整个 GPU 调度问题都可以跳过。
- **成本比较只在「两者都能达到精度要求」时有意义**；输出是自由文本、需要世界知识、需求天天变，这三类 encoder 不适用。
- **软标签的价值是类间相似结构**；`T²` 因子不能忘（T=4 时忘了等于没做蒸馏）。LLM→encoder 只能走**数据蒸馏**。
- **原始 BERT 的句向量不能直接用**（[CLS] 没被训练 + 各向异性 + 目标错配）；解法是白化或对比学习（SBERT/SimCSE）。
- **负例设计第三次决定一切**：NSP 的失败、SOP 的成功、hard negatives 的价值，是同一条原理。
- **双塔的在线成本与语料规模无关**——这是它不可替代的原因。两阶段的最优 k 在 recall 曲线拐点（50–200）。
- 最通用的架构模式：**用便宜的模型过滤，用贵的模型处理剩下的**。

🎓 **本课完结。** 你现在能从「注意力掩码的三种画法」推导出三种形态的全部性质，
并为一个真实任务做出有成本依据的选型。
建议的下一站：**C50**（HuggingFace 生态实操，把本课的概念变成能跑的代码）、
**C11**（RAG 与检索）、**C27**（模型压缩与量化）。"""),
]
