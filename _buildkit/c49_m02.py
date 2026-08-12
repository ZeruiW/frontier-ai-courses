# -*- coding: utf-8 -*-
"""C49 模块 02 · 预训练目标与配方的改良。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–01、交叉熵与二元交叉熵、参数量估算"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_pretraining_objectives.ipynb'),
    ("核心论文", "Liu et al. 2019（RoBERTa）★、Clark et al. 2020（ELECTRA）★、He et al. 2021（DeBERTa）★、Lan et al. 2020（ALBERT）"),
    ("预计时长", "读 65 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("roberta", "RoBERTa：一篇「只调配方」却影响深远的论文", "".join([
        P("BERT 发布一年后，RoBERTa 出现了。它<strong>没有改动任何架构</strong>——同样的双向 Transformer、同样的 MLM 目标、同样的层数和维度。它只做了一件事：<em>把训练配方系统地重调了一遍</em>。结果在 GLUE 上大幅超越 BERT，甚至超过了当时一批号称有架构创新的工作。"),
        P("这个结果本身是本模块最重要的一课：<strong>BERT 是严重欠训练的（significantly undertrained）</strong>。它的改动清单值得逐条理解，因为每一条都对应一个可迁移的经验。"),
        TABLE(["改动", "BERT", "RoBERTa", "为什么有效"], [
            ["<strong>去掉 NSP</strong>", "MLM + NSP", "只有 MLM", "NSP 能被主题捷径攻破（模块 01 已验证），还占用算力"],
            ["<strong>动态掩码</strong>", "预处理时掩一次，全程复用（静态）", "每个 epoch 重新采样掩码位置", "同一句话在不同 epoch 被掩的位置不同 → 有效样本量翻倍"],
            ["<strong>更多数据</strong>", "16GB（BooksCorpus + Wiki）", "160GB（+CC-News, OpenWebText, Stories）", "10 倍数据，直接的规模收益"],
            ["<strong>更大 batch</strong>", "256 序列", "8192 序列（配更大 lr）", "MLM 梯度噪声大，大 batch 显著降噪"],
            ["<strong>更长训练</strong>", "1M 步", "最多 500k 步 × 8k batch ≈ 更多 token", "欠训练是主要瓶颈"],
            ["<strong>整句输入</strong>", "句对（为 NSP 服务）", "连续填满 512 的完整文本片段", "去掉 NSP 后没必要凑句对，长片段信息更完整"],
            ["<strong>byte-level BPE</strong>", "WordPiece 30k", "byte-BPE 50k", "无未登录词、跨语言更鲁棒"],
        ]),
        DUAL(
            "<strong>动态掩码</strong>这一条最值得单独说，因为它揭示了一个常被忽略的问题：BERT 在数据预处理阶段就把掩码固定下来了（为了效率，实际做了 10 份不同的副本），于是模型在 40 个 epoch 里会<em>反复看到同一句话的同一个挖空版本</em>。这相当于人为缩小了有效数据量、增加了过拟合风险。动态掩码让每次看到的挖空位置都不同，等于免费扩充了数据。",
            "形式化地看这个收益：静态掩码下，一句长度 <code>L</code> 的话只提供了 <code>k</code>（副本数）种挖空模式；动态掩码下有 <code>C(0.85L, 0.15L)</code> 种可能——天文数字。当然实际收益远小于这个组合数（不同挖空之间高度相关），但方向是明确的：<strong>训练时的随机性是一种免费的数据增强</strong>。这个思想在数据增强（C51）、dropout、SpecAugment 里反复出现。",
        ),
        CALLOUT("intuition", "RoBERTa 给整个领域的教训，用一句话说：<strong>在宣布一个架构创新有效之前，先确认你的 baseline 是充分训练的</strong>。2019–2020 年有相当一批「改进 BERT」的工作，其收益在 RoBERTa 式的充分训练 baseline 下就消失了。这个现象在深度学习里反复上演（后来在推荐系统、图神经网络、时序预测领域都有类似的「baseline 没调好」的复盘论文）。<em>C40（研究方法论）会把这件事作为可复现性的核心案例。</em>"),
    ])),
    ("electra", "ELECTRA：把生成式目标换成判别式", "".join([
        P("RoBERTa 把配方推到了极限，但 MLM 的<strong>结构性缺陷</strong>还在：信号密度只有 15%，且引入了下游不存在的 <code>[MASK]</code>。ELECTRA 换了个思路，把这两个问题一起解决。"),
        H3("RTD：替换 token 检测"),
        ASCII("""原句:      the  chef  cooked  the  meal
             │     │      │      │     │
   ① 用一个**小生成器**（小 BERT，MLM 训练）把 15% 的位置替换成「它认为合理」的词
             ↓
被污染:    the  chef   ate    the  meal        ← cooked 被换成了 ate（很像真的！）
             │     │      │      │     │
   ② **判别器**（真正要的模型）对**每个位置**判断：这个 token 是原始的还是被替换的？
             ↓
标签:      orig  orig  REPLACED orig  orig     ← 每个位置都有信号！

关键差异:
  · 判别器**每个位置都产生训练信号** → 信号密度 1.0×（MLM 只有 0.15×）
  · 输入里**没有 [MASK]** → 预训练与下游的输入分布一致，不需要 80/10/10 补丁
  · 生成器是**辅助**的，训练完就扔掉，只保留判别器""")
        ,
        P("这个设计在细节上有几个精妙之处，值得看清："),
        UL([
            "<strong>生成器要「小」而不是「强」</strong>。论文发现生成器规模是判别器的 1/4 到 1/2 时效果最好。太强的生成器会造出几乎无法分辨的替换，判别任务变得过难、信号变噪声；太弱则替换太离谱，任务过易。<em>这是对抗式设置里常见的「难度匹配」问题</em>。",
            "<strong>不是 GAN</strong>。虽然结构上像生成器-判别器，但生成器<em>不接收</em>来自判别器的对抗梯度（文本离散，梯度传不回去）。生成器只是用自己的 MLM 损失独立训练。所以 ELECTRA 是「两个协同训练的模型」，不是对抗博弈——这一点论文特别澄清过，也是常见误解。",
            "<strong>损失加权</strong>。总损失是 <code>L_MLM(生成器) + λ·L_RTD(判别器)</code>，论文取 <code>λ=50</code>。因为二分类损失的数值尺度远小于 30k 类交叉熵，不加权的话判别器几乎不更新。",
        ]),
        DUAL(
            "ELECTRA 的收益有多大？论文报告：<strong>ELECTRA-Small 用 1/30 的算力达到 GPT（同期）的 GLUE 分数；ELECTRA-Base 用 1/4 的算力匹配 RoBERTa</strong>。在小算力区间优势尤其明显——这对「没有大集群但要一个好用的编码器」的团队极有价值。",
            "但要看清它的代价与边界。<strong>①每次信号的信息量小</strong>：二分类最多 1 bit，而 MLM 是 <code>log₂(30522) ≈ 14.9</code> bit。所以 6.7 倍的密度优势换算成实际效率优势约 4 倍，不是 6.7 倍（模块 01 已算过）。<strong>②判别器不学生成</strong>：ELECTRA 的判别器没有语言建模头，不能算词概率、不能做需要生成的任务，比 BERT 更「纯粹地只是个编码器」。<strong>③训练流程更复杂</strong>：要同时维护两个模型、调 λ 与生成器规模比，工程上比 MLM 麻烦。",
        ),
        CALLOUT("intuition", "ELECTRA 体现了一个非常一般的设计模式：<strong>当你的自监督任务只在少数位置产生信号时，考虑把「生成」换成「判别」</strong>——判别任务通常可以在每个位置上定义。同样的思路在对比学习（判别正负样本对）、RLHF 的奖励模型（判别偏好）、以及各种「用一个模型造样本、另一个模型判真伪」的方案里都出现过。<em>记住这个模式，比记住 ELECTRA 的具体结构更有用。</em>"),
    ])),
    ("deberta", "DeBERTa：解耦注意力与相对位置", "".join([
        P("RoBERTa 改配方、ELECTRA 改目标，DeBERTa 改的是<strong>注意力本身怎么用位置信息</strong>。它是这一线里在 GLUE/SuperGLUE 上走得最远的（DeBERTa-v3 至今仍是很多编码器任务的强基线）。"),
        H3("核心洞察：内容与位置应该分开算"),
        P("BERT 的做法是把位置嵌入<strong>加</strong>到词嵌入上，然后一起做注意力。这意味着注意力分数里，内容与位置的贡献被<em>纠缠</em>在一起了。展开 <code>(x_i + p_i)W_q · ((x_j + p_j)W_k)ᵀ</code> 会得到四项："),
        MATH("\\underbrace{x_iW_qW_k^Tx_j^T}_{\\text{内容→内容}} + \\underbrace{x_iW_qW_k^Tp_j^T}_{\\text{内容→位置}} + \\underbrace{p_iW_qW_k^Tx_j^T}_{\\text{位置→内容}} + \\underbrace{p_iW_qW_k^Tp_j^T}_{\\text{位置→位置}}"),
        P("DeBERTa 的 <span class=\"term\">disentangled attention</span>（解耦注意力）做两件事：<strong>①用相对位置替代绝对位置</strong>（<code>p_{i→j}</code> 只依赖 <code>i−j</code>，而非 <code>i</code> 和 <code>j</code> 各自的绝对值）；<strong>②只保留前三项，丢掉「位置→位置」项</strong>（用相对位置后，这一项对所有 <code>(i,j)</code> 只依赖距离，是个常数偏置，信息量很小）。"),
        MATH("A_{ij} = \\underbrace{x_iW_{q,c}(x_jW_{k,c})^T}_{\\text{内容→内容}} + \\underbrace{x_iW_{q,c}(r_{i-j}W_{k,r})^T}_{\\text{内容→位置}} + \\underbrace{r_{j-i}W_{q,r}(x_jW_{k,c})^T}_{\\text{位置→内容}}"),
        DUAL(
            "为什么解耦有用？举个例子：「deep」和「learning」这两个词，它们的注意力权重应该同时取决于<em>它们是什么词</em>（内容）和<em>它们挨得多近</em>（位置）。把两者加在一起再投影，模型必须从一个混合向量里隐式地拆出这两种信息；显式地分开算，等于把这个归纳偏置直接写进架构。<strong>相对位置还带来一个附赠好处：长度外推能力</strong>——绝对位置嵌入表只有 512 行，相对位置只需要覆盖一个距离窗口。",
            "DeBERTa 还有第二个组件：<span class=\"term\">EMD</span>（Enhanced Mask Decoder）。因为相对位置本身不包含绝对位置信息（「第一个词」这个事实丢了），而 MLM 预测某些词时绝对位置是有用的（比如句首更可能是大写词），所以 DeBERTa 在<em>输出层之前</em>把绝对位置信息注入回去。<strong>这是个很聪明的分工：让中间层用相对位置做通用的上下文建模，只在最后需要时才用绝对位置</strong>。DeBERTa-v3 进一步把预训练目标换成了 ELECTRA 的 RTD（并改进了权重共享方式），是「两条改进线合流」的典型。",
        ),
        CALLOUT("warn", "解耦注意力的代价是<strong>计算量与实现复杂度</strong>：三项注意力分数意味着约 2 倍的注意力计算（论文报告约 1.5–2× 的训练开销），而且相对位置的索引计算（<code>clip(i−j)</code> 的分桶）实现起来容易出错。工程上还有一个现实问题：<em>DeBERTa 的注意力实现与 FlashAttention 等标准 kernel 不兼容</em>，因为它不是标准的 <code>QKᵀ</code>。这在需要极致推理速度时是个真实的取舍。"),
    ])),
    ("albert", "ALBERT：参数共享与它的真实代价", "".join([
        P("ALBERT 走的是第四条路：<strong>不改目标、不改配方，改的是参数怎么放</strong>。它想回答一个问题——能不能在参数量小很多的情况下保持性能？它用了三个技术："),
        TABLE(["技术", "做法", "省了多少", "代价"], [
            ["<strong>嵌入分解</strong><br>factorized embedding", "词嵌入先投到低维 <code>E</code>（如 128），再升到 <code>H</code>（如 768）。参数从 <code>V×H</code> 变成 <code>V×E + E×H</code>", "BERT-base 的嵌入表占 23M/110M ≈ 21%，分解后降到约 4M", "多一次投影；表达力略降"],
            ["<strong>跨层参数共享</strong><br>cross-layer sharing", "所有 Transformer 层<strong>共用同一份权重</strong>", "12 层的参数变成 1 层的量，省掉约 85M", "<strong>推理速度完全没变</strong>（层数没少，还是要算 12 次）"],
            ["<strong>SOP 替代 NSP</strong>", "负例改为同一对句子的顺序颠倒", "—", "无（纯改进，模块 01 已验证）"],
        ]),
        CALLOUT("danger", "<p>ALBERT 最容易被误读的一点：<strong>参数少 ≠ 跑得快</strong>。跨层共享把 ALBERT-base 的参数量从 110M 压到 12M（省 89%），听起来惊人；但推理时它仍然要跑 12 层前向，<em>FLOPs 与延迟和 BERT-base 几乎一模一样</em>。省下的只是<strong>显存中存放权重的空间</strong>和<strong>模型文件的大小</strong>。而且 ALBERT 论文中真正涨分的配置是 ALBERT-xxlarge（<code>H=4096</code>），它虽然只有 235M 参数，但<strong>比 BERT-large 慢约 3 倍</strong>——因为每层更宽。<em>「参数量」是个很差的效率代理指标，要看 FLOPs 和实测延迟。</em></p>", "参数量不是效率"),
        DUAL(
            "那跨层共享到底带来了什么？两件事：<strong>①正则化效果</strong>——强制所有层学同一个变换，是很强的约束，能防止过拟合、提升训练稳定性；<strong>②让「更宽但参数可控」成为可能</strong>——因为层间共享，你可以把 <code>H</code> 加到 4096 而参数量还在可控范围，从而在<em>同等参数预算</em>下获得更强的表达力。",
            "但后来的实践并没有大规模采用参数共享，原因是<strong>它优化的是一个不太重要的指标</strong>。在实际部署里，权重占用的显存通常不是瓶颈（KV 缓存和激活才是，见 C08/C24），而推理延迟才是。既然共享不省延迟，那用同样的 FLOPs 预算去训一个参数更多的模型通常更划算。<em>ALBERT 的历史价值更多在于它提出的 SOP（被广泛采纳）和它对「参数量 vs 计算量」这个区分的澄清。</em>",
        ),
    ])),
    ("compare", "四条改进线的横向对比", "".join([
        P("把四个工作放在一起，你会看到它们其实在优化<strong>四个不同的东西</strong>——这才是理解这段历史的正确方式。"),
        TABLE(["工作", "改的是什么", "核心指标改善", "今天的地位"], [
            ["<strong>RoBERTa</strong>", "训练配方（数据、batch、步数、动态掩码）", "同架构下 GLUE +2~3 分", "✅ 仍是标准基线；它的配方经验被普遍继承"],
            ["<strong>ELECTRA</strong>", "预训练目标（生成式 → 判别式）", "<strong>算力效率约 4×</strong>", "✅ RTD 被 DeBERTa-v3 等继承；小算力场景首选"],
            ["<strong>DeBERTa</strong>", "注意力对位置的使用方式", "SuperGLUE 上首次超人类基线", "✅ <strong>v3 至今是编码器任务的最强基线之一</strong>"],
            ["<strong>ALBERT</strong>", "参数放置（共享与分解）", "参数量 −89%（但不省延迟）", "🔶 SOP 被继承；参数共享未成主流"],
        ]),
        P("从这张表里能提炼出三条对<em>今天</em>仍然适用的判断："),
        UL([
            "<strong>配方 &gt; 架构</strong>（在同一代技术内）。RoBERTa 用零架构创新击败了一批有架构创新的工作。做研究时，先确认 baseline 训练充分，否则你的「改进」可能只是在补别人的欠训练。",
            "<strong>目标函数的信号密度是一等公民</strong>。ELECTRA 的收益不来自更聪明的表示，而来自「每个位置都有信号」。设计任何自监督任务时都该问：我的信号密度是多少？",
            "<strong>效率指标要选对</strong>。参数量、FLOPs、延迟、显存是四个不同的东西，优化其中一个可能对另一个毫无帮助（ALBERT）甚至有害。<em>先明确你被什么卡住，再选优化目标。</em>",
        ]),
        CALLOUT("intuition", "还有一条隐含的启示：<strong>这四个工作是「正交」的，所以可以叠加</strong>。DeBERTa-v3 = DeBERTa 的解耦注意力 + ELECTRA 的 RTD + RoBERTa 式的充分训练，效果确实比任何单项都好。<em>当你看到一个领域里出现几个改动不同维度的工作时，「把它们叠起来」往往是一个被低估的、高回报的方向</em>——虽然它不够「新颖」，但工程价值巨大。"),
    ])),
    ("modern", "编码器的现代化：被遗忘的十年", "".join([
        P("这里要说一个容易被忽略的事实：<strong>BERT 的架构停留在 2018 年</strong>。而 2019–2025 年间，decoder-only 那条线积累了大量架构与工程改进，这些改进<em>绝大多数对 encoder 同样适用，但长期没人去做</em>——因为注意力都在 LLM 上。"),
        TABLE(["组件", "BERT (2018)", "现代做法", "对 encoder 的收益"], [
            ["位置编码", "学习式绝对位置，硬上限 512", "RoPE / ALiBi / 相对位置", "支持长文档；可外推"],
            ["归一化位置", "post-LN（残差后归一化）", "pre-LN / RMSNorm", "训练更稳，可去掉 warmup 的一部分"],
            ["激活函数", "GELU + 标准 FFN", "GLU 族（SwiGLU/GeGLU）", "同参数量下效果更好"],
            ["注意力实现", "朴素 <code>QKᵀ</code>", "FlashAttention", "长序列显著提速与省显存"],
            ["注意力模式", "全注意力 O(L²)", "局部+全局交替（Longformer 式）", "长文档从不可行变可行"],
            ["padding", "补齐到定长", "unpadding / 变长序列打包", "batch 内长度差异大时省一半算力"],
            ["分词器", "WordPiece 30k", "BPE 50k+ / 更好的多语言覆盖", "无 UNK；跨语言"],
        ]),
        P("把这些装进 encoder 会发生什么？近两年的 <em>ModernBERT</em> 一类工作给出了答案：<strong>在同等参数量下大幅超越原始 BERT/RoBERTa，同时把上下文长度从 512 提到 8192，推理速度还更快</strong>。这说明 encoder 线的潜力远未被榨干——只是过去几年整个社区的注意力被 decoder 吸走了。"),
        CALLOUT("intuition", "这件事对你的实际意义：<strong>如果你今天要选一个编码器做分类/检索，不要默认选 <code>bert-base-uncased</code></strong>。它是 2018 年的技术，而同等成本下有明显更好的选项（DeBERTa-v3、现代化的 BERT 变体、或者专门的嵌入模型）。<em>「默认选项」的惯性是工程里一个真实的成本来源</em>——很多团队至今在用 BERT-base，不是因为评估后觉得它最好，而是因为教程里都是它。"),
    ])),
    ("ledger", "算一笔账：四种改进的效率对比", "".join([
        P("把四个工作的改进量化到同一个尺度上——<strong>达到同等 GLUE 分数所需的算力</strong>（以 BERT-base 为 1.0）。数字取自各论文报告的量级。"),
        TABLE(["模型", "参数量", "预训练算力（相对）", "GLUE 量级", "备注"], [
            ["BERT-base", "110M", "1.0×", "~79", "基线"],
            ["RoBERTa-base", "125M", "~4×（更多数据与步数）", "~86", "算力换分数，不是效率改进"],
            ["ELECTRA-base", "110M", "<strong>~0.25×</strong>（达到 RoBERTa 分数）", "~86", "<strong>真正的效率改进</strong>"],
            ["ALBERT-base", "12M", "~1.0×", "~80", "参数少但算力不省"],
            ["DeBERTa-base", "140M", "~1.5×（解耦注意力更贵）", "~88", "分数换算力，效果最强"],
        ]),
        P("读这张表的正确方式：<strong>「更好」有两种完全不同的含义</strong>。RoBERTa 和 DeBERTa 是<em>用更多算力换更高分数</em>（帕累托前沿上向右上移动）；ELECTRA 是<em>用更少算力达到同样分数</em>（向左平移）。ALBERT 是<em>用同样算力换更小的权重文件</em>（第三个维度）。<em>它们不在同一个坐标轴上竞争，所以问「谁最好」是个坏问题；正确的问题是「我被什么卡住」</em>。"),
        P("给三种常见约束下的实际建议："),
        UL([
            "<strong>算力受限（个人/小团队要自己预训练）</strong>：ELECTRA 式的 RTD 目标，收益最大。",
            "<strong>只做微调、追求效果</strong>：直接用 DeBERTa-v3 系列的开源权重，不要从 BERT-base 起步。",
            "<strong>推理延迟受限</strong>：先看能不能蒸馏到更小的模型（模块 05），而不是选参数共享的模型——<em>参数共享不省延迟</em>。",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>同一个架构上，「训练配方」「目标函数」「位置信息的用法」「参数放置」是四个几乎正交的改进维度；每个维度的改进优化的是不同的指标，叠加起来往往能得到超过任何单项的结果</strong>。当你面对一个「已经被研究透了」的架构时，先把这四个维度列出来，通常会发现还有没被系统探索的组合。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>判别式目标的信息论上界</strong>：RTD 每个位置只有 1 bit，为什么效果能接近每位置 15 bit 的 MLM？「信号密度 × 信息量」这个朴素乘积显然不是完整故事，缺乏理论刻画。也有工作尝试多分类版本的替换检测（判断被替换成了哪一类），介于两者之间。",
            "<strong>最优生成器-判别器规模比</strong>：ELECTRA 报告 1/4–1/2 最优，但这个比值如何随规模缩放、是否有理论依据，尚不清楚。它与 GAN 中的「判别器不能太强」有相似的味道，但机制不同（无对抗梯度）。",
            "<strong>相对位置编码的统一理解</strong>：DeBERTa 的解耦注意力、T5 的相对位置偏置、RoPE、ALiBi 是四种不同的相对位置方案，它们的表达力与外推能力之间的关系缺乏统一理论。什么任务需要哪种，目前主要靠实验。",
            "<strong>encoder 的缩放律</strong>：decoder-only 有成熟的 Chinchilla 式缩放律（C21），但 encoder + MLM 的最优参数-数据配比缺乏系统研究。掩码率、模型规模、数据量三者的联合缩放律尤其空白。",
            "<strong>编码器的现代化边界</strong>：把现代组件装进 encoder 能带来多大提升，以及是否存在「encoder 特有」的架构改进（而不只是移植 decoder 的），仍在探索。encoder 的双向性是否允许一些 decoder 做不到的结构（如迭代式精化），是个开放方向。",
        ]),
        CALLOUT("paper", "必读：Liu et al. 2019 <em>RoBERTa</em>（重点读消融表，它系统地拆开了每一项改动的贡献）、Clark et al. 2020 <em>ELECTRA</em>（读它的生成器规模消融与「不是 GAN」的澄清）、He et al. 2021 <em>DeBERTa</em> 与 2023 <em>DeBERTa-v3</em>（解耦注意力的推导与 RTD 的结合）、Lan et al. 2020 <em>ALBERT</em>（SOP 的动机与参数共享的真实收益）。补充：Wettig et al. 2023 <em>Should You Mask 15%?</em>、以及 ModernBERT 一类编码器现代化的工作。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 预训练目标与配方的改良（RoBERTa / ELECTRA / DeBERTa / ALBERT）

目标：把 **静态 vs 动态掩码 → RTD 判别式目标 → 解耦注意力 → 参数共享与嵌入分解** 从零实现，
每项改进都**量化它到底改善了什么指标**。

路线：动态掩码的有效样本量 → RTD 的信号密度与信息量 → 生成器规模的「难度匹配」→
DeBERTa 三项注意力分解 → ALBERT 的参数量 vs FLOPs → 四维度对比 → ✏️ 练习 → 📖 答案 → 🧪 效率前沿胶囊。

> 心智模型：**配方 / 目标 / 位置信息 / 参数放置 是四个几乎正交的维度**，
> 每个优化的是不同指标。问「谁最好」是坏问题，问「我被什么卡住」才对。"""),
    md("""## 1 · RoBERTa 的动态掩码：免费的数据增强

BERT 在预处理阶段就固定了掩码（做了 10 份副本），40 个 epoch 里反复看同样的挖空。
RoBERTa 每次现掩。先量化这个差别。"""),
    code("""import numpy as np, math, itertools
rng = np.random.default_rng(0)

L, MASK_RATE = 20, 0.15
K_MASK = int(round(L * MASK_RATE))

def static_patterns(n_copies, seed=0):
    '''BERT：预处理时生成 n_copies 份固定掩码，训练时循环复用。'''
    r = np.random.default_rng(seed)
    return [frozenset(r.choice(L, size=K_MASK, replace=False)) for _ in range(n_copies)]

def dynamic_patterns(n_epochs, seed=0):
    '''RoBERTa：每个 epoch 现场采样。'''
    r = np.random.default_rng(seed)
    return [frozenset(r.choice(L, size=K_MASK, replace=False)) for _ in range(n_epochs)]

N_EPOCHS = 40
static_seen  = set(static_patterns(10))          # BERT 论文：10 份静态副本
dynamic_seen = set(dynamic_patterns(N_EPOCHS))
print(f'序列长度 {L}, 掩 {K_MASK} 个位置, 训练 {N_EPOCHS} 个 epoch')
print(f'静态(10份副本): 模型见过 {len(static_seen)} 种不同的挖空模式')
print(f'动态(每轮现掩): 模型见过 {len(dynamic_seen)} 种不同的挖空模式')
print(f'理论上限 C({L},{K_MASK}) = {math.comb(L, K_MASK):,}')

assert len(static_seen) <= 10, '静态副本数是硬上限'
assert len(dynamic_seen) > len(static_seen), '动态掩码见到的模式更多'
print(f'\\n✅ 动态掩码把有效「样本」数提高了 {len(dynamic_seen)/len(static_seen):.1f} 倍。')
print('   注意：实际收益远小于组合数上限（不同挖空高度相关），但方向明确 ——')
print('   **训练时的随机性是一种免费的数据增强**。')"""),
    md("""### RoBERTa 改动清单的「贡献归因」

论文的价值在消融表。用一个简化模型复现这个归因逻辑：**每项改动的边际贡献**。"""),
    code("""# 数字取自 RoBERTa 论文报告的量级（GLUE 平均分）
ablation = [
    ('BERT-base 复现基线',           79.0),
    ('+ 去掉 NSP、改用整句输入',      80.5),
    ('+ 动态掩码',                    81.2),
    ('+ 更大 batch (256 -> 8k)',      82.4),
    ('+ 更多数据 (16GB -> 160GB)',    84.6),
    ('+ 更长训练',                    86.0),
]
prev = None
print(f"{'配置':<32s} {'GLUE':>6s} {'边际':>6s}")
for name, score in ablation:
    delta = '' if prev is None else f'{score - prev:+.1f}'
    print(f'{name:<32s} {score:>6.1f} {delta:>6s}')
    prev = score

deltas = [ablation[i][1] - ablation[i-1][1] for i in range(1, len(ablation))]
assert all(d > 0 for d in deltas), '每一项都应有正贡献'
biggest = max(range(len(deltas)), key=lambda i: deltas[i])
print(f'\\n最大单项贡献: 「{ablation[biggest+1][0]}」 +{deltas[biggest]:.1f}')
assert ablation[-1][1] - ablation[0][1] > 6, '总提升应超过 6 分'
print(f'✅ 总提升 {ablation[-1][1]-ablation[0][1]:.1f} 分，**零架构改动**。')
print('   教训：宣布架构创新有效之前，先确认 baseline 是充分训练的。')"""),
    md("""## 2 · ELECTRA 的 RTD：每个位置都有信号

生成器（小 MLM）造替换 → 判别器判断每个 token 是否被替换。
**信号密度从 0.15 拉回 1.0，且输入里没有 `[MASK]`。**"""),
    code("""V, D = 40, 24

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x); return e / e.sum(axis=axis, keepdims=True)

def make_generator(strength, seed=0):
    '''一个「玩具生成器」：strength 越大，替换越像真词（越难分辨）。
       用一个随机的 token->token 相似度矩阵模拟。'''
    r = np.random.default_rng(seed)
    sim = r.normal(size=(V, V)) * 0.5
    sim += np.eye(V) * strength          # strength 大 -> 更倾向于生成「接近原词」的替换
    return softmax(sim, axis=-1)

def electra_corrupt(ids, gen_probs, mask_rate=0.15, seed=0):
    '''返回 (被污染的 ids, RTD 标签 1=被替换 0=原始)。**注意：没有 [MASK]**'''
    r = np.random.default_rng(seed)
    ids = ids.copy()
    labels = np.zeros(len(ids), dtype=int)
    k = max(1, int(round(len(ids) * mask_rate)))
    pos = r.choice(len(ids), size=k, replace=False)
    for i in pos:
        new = r.choice(V, p=gen_probs[ids[i]])
        if new != ids[i]:
            ids[i] = new; labels[i] = 1        # 只有真的换掉了才算 replaced
    return ids, labels

seq = rng.integers(0, V, size=20)
gen = make_generator(strength=2.0)
corrupt, rtd_labels = electra_corrupt(seq, gen, seed=1)
print('原始  :', seq[:12])
print('污染后:', corrupt[:12])
print('RTD标签:', rtd_labels[:12], '  (1=被替换)')

# ELECTRA 的输入里根本不存在 [MASK] 这个概念 —— 被换的位置放的是一个真实的词
assert len(rtd_labels) == len(seq), '**每个位置**都有标签 —— 这是 RTD 的核心'
assert rtd_labels.sum() >= 1
assert ((corrupt != seq) == (rtd_labels == 1)).all(), '标签必须与实际替换一致'
print(f'\\n信号密度: RTD 每序列 {len(rtd_labels)} 个标签 vs MLM {int(len(seq)*0.15)} 个')
print(f'✅ {len(rtd_labels) / max(1,int(len(seq)*0.15)):.1f}× 的信号密度，且输入分布与下游一致（无 [MASK]）')"""),
    md("""### 生成器规模的「难度匹配」：太强太弱都不好

ELECTRA 论文发现生成器规模是判别器的 1/4~1/2 时最优。
用「替换的可分辨性」量化：太弱 → 任务过易；太强 → 任务过难，信号变噪声。"""),
    code("""def discriminability(strength, n=400, seed=0):
    '''用一个最简单的判别器（看词频先验）测量任务难度：
       返回 (被替换比例, 一个朴素判别器的准确率)。'''
    r = np.random.default_rng(seed)
    g = make_generator(strength, seed=seed)
    # 朴素判别器：如果该位置的 token 在语料里是「常见搭配」就判原始
    freq = softmax(r.normal(size=V) * 1.5)
    accs, repl = [], []
    for t in range(n):
        s = r.integers(0, V, size=20)
        c, lab = electra_corrupt(s, g, seed=t)
        pred = (freq[c] < np.median(freq)).astype(int)     # 低频 -> 猜是被替换的
        accs.append((pred == lab).mean()); repl.append(lab.mean())
    return float(np.mean(repl)), float(np.mean(accs))

print(f"{'生成器强度':>11s} {'实际替换率':>10s} {'朴素判别器准确率':>16s} {'说明':<16s}")
rows = []
for st, note in [(-2.0, '太弱: 替换很离谱'), (0.0, '中等'), (2.0, '较强'), (6.0, '太强: 几乎不换')]:
    rr, acc = discriminability(st)
    rows.append((st, rr, acc))
    print(f'{st:>11.1f} {rr:>10.1%} {acc:>16.1%}  {note:<16s}')

rates = [r[1] for r in rows]
assert rates == sorted(rates, reverse=True), '生成器越强（越倾向原词），实际替换率越低'
assert rates[-1] < 0.05, '生成器太强时几乎不产生替换 -> 判别器几乎没有正样本可学'
print('\\n✅ 两端都坏：太弱 -> 替换离谱、任务过易、学不到语言知识；')
print('   太强 -> 几乎不替换、正样本稀缺、判别器无信号。中间才是甜点区。')
print('   这与 GAN 里「判别器不能太强」是同一类难度匹配问题 —— 但 ELECTRA **不是** GAN：')
print('   生成器不接收判别器的对抗梯度（文本离散传不回去），两者是协同训练，不是博弈。')"""),
    md("""### 损失加权 λ：为什么必须是 50 量级

`L = L_MLM(生成器) + λ · L_RTD(判别器)`。二分类损失的数值尺度远小于 30k 类交叉熵。"""),
    code("""V_REAL = 30522
loss_mlm_scale = math.log(V_REAL)      # 随机初始化时的 MLM 损失 ≈ ln(V)
loss_rtd_scale = math.log(2)           # 随机初始化时的二分类损失 = ln(2)
print(f'初始损失量级: MLM ≈ {loss_mlm_scale:.2f} | RTD ≈ {loss_rtd_scale:.2f}')
print(f'比值 = {loss_mlm_scale / loss_rtd_scale:.1f}')

for lam in [1, 10, 50, 100]:
    share = lam * loss_rtd_scale / (loss_mlm_scale + lam * loss_rtd_scale)
    print(f'  λ={lam:>3d}: RTD 项占总损失 {share:>5.1%}')

share1  = 1  * loss_rtd_scale / (loss_mlm_scale + 1  * loss_rtd_scale)
share50 = 50 * loss_rtd_scale / (loss_mlm_scale + 50 * loss_rtd_scale)
assert share1 < 0.10, 'λ=1 时判别器几乎收不到梯度'
assert share50 > 0.70, 'λ=50 时判别器主导 —— 这正是我们真正要的模型'
print(f'\\n✅ λ=1 时 RTD 只占 {share1:.0%}（判别器几乎不更新）；λ=50 时占 {share50:.0%}。')
print('   论文取 50 不是玄学，是让「真正要的那个模型」拿到主要梯度。')"""),
    md("""## 3 · DeBERTa：解耦注意力的三项分解

BERT 把位置嵌入**加**到词嵌入上，展开后得到四项。DeBERTa 用相对位置、只保留前三项。
下面把两种实现都写出来，验证分解的正确性。"""),
    code("""def bert_style_attention_scores(X, Pabs, Wq, Wk):
    '''BERT: (x+p)Wq · ((x+p)Wk)^T —— 内容与位置纠缠在一起。'''
    H = X + Pabs
    return (H @ Wq) @ (H @ Wk).T / math.sqrt(Wq.shape[1])

def expand_four_terms(X, Pabs, Wq, Wk):
    '''把上式展开成四项，验证它们之和等于原式。'''
    s = math.sqrt(Wq.shape[1])
    c2c = (X @ Wq) @ (X @ Wk).T / s
    c2p = (X @ Wq) @ (Pabs @ Wk).T / s
    p2c = (Pabs @ Wq) @ (X @ Wk).T / s
    p2p = (Pabs @ Wq) @ (Pabs @ Wk).T / s
    return c2c, c2p, p2c, p2p

n = 8
X = rng.normal(size=(n, D)) * 0.5
Pabs = rng.normal(size=(n, D)) * 0.5
Wq, Wk = rng.normal(size=(D, D)) * 0.2, rng.normal(size=(D, D)) * 0.2

full = bert_style_attention_scores(X, Pabs, Wq, Wk)
c2c, c2p, p2c, p2p = expand_four_terms(X, Pabs, Wq, Wk)
assert np.allclose(full, c2c + c2p + p2c + p2p, atol=1e-10), '四项之和必须等于原式'
print('✅ BERT 注意力 = 内容→内容 + 内容→位置 + 位置→内容 + 位置→位置')
print(f'   各项的分数标准差: c2c {c2c.std():.3f} | c2p {c2p.std():.3f} | '
      f'p2c {p2c.std():.3f} | p2p {p2p.std():.3f}')"""),
    code("""def relative_position_bucket(n, max_rel=4):
    '''相对位置矩阵 rel[i,j] = clip(i-j, -max_rel, max_rel) + max_rel（作为索引）。'''
    idx = np.arange(n)
    rel = np.clip(idx[:, None] - idx[None, :], -max_rel, max_rel) + max_rel
    return rel

def deberta_attention_scores(X, Rel, Wqc, Wkc, Wqr, Wkr, rel_idx):
    '''DeBERTa: 内容→内容 + 内容→位置 + 位置→内容（丢掉 位置→位置）。'''
    s = math.sqrt(Wqc.shape[1]) * math.sqrt(3)      # 论文用 sqrt(3d) 归一化三项
    Qc, Kc = X @ Wqc, X @ Wkc
    Qr, Kr = Rel @ Wqr, Rel @ Wkr
    c2c = Qc @ Kc.T
    c2p = np.take_along_axis(Qc @ Kr.T, rel_idx, axis=1)          # 用相对索引取
    p2c = np.take_along_axis((Kc @ Qr.T), rel_idx.T, axis=1).T
    return (c2c + c2p + p2c) / s

MAX_REL = 4
rel_idx = relative_position_bucket(n, MAX_REL)
Rel = rng.normal(size=(2 * MAX_REL + 1, D)) * 0.5
Wqc, Wkc, Wqr, Wkr = (rng.normal(size=(D, D)) * 0.2 for _ in range(4))
A = deberta_attention_scores(X, Rel, Wqc, Wkc, Wqr, Wkr, rel_idx)
print('DeBERTa 注意力分数矩阵形状:', A.shape)
assert A.shape == (n, n)
assert np.isfinite(A).all()

# 关键性质 ①：相对位置具有平移不变性 —— 距离相同的位置对，位置项贡献相同
print('\\n相对位置索引矩阵 rel[i,j] = clip(i-j):')
print(rel_idx)
assert rel_idx[2, 1] == rel_idx[5, 4], '距离相同 -> 相对位置索引相同（平移不变）'
assert rel_idx[0, n-1] == rel_idx[1, n-1], f'超过 max_rel={MAX_REL} 的距离被截断到同一桶'
print(f'\\n✅ 相对位置的两个关键性质：平移不变 + 远距离截断。')
print(f'   前者是 DeBERTa 的归纳偏置；后者让位置表只需 {2*MAX_REL+1} 行（BERT 需要 512 行）。')"""),
    md("""### 解耦的代价：计算量"""),
    code("""def attn_flops(n, d, mode):
    '''注意力分数的相对计算量（只数矩阵乘）。'''
    base = n * n * d
    return {'bert': base, 'deberta': 3 * base}[mode]

for n_ in [128, 512]:
    b, db = attn_flops(n_, 768, 'bert'), attn_flops(n_, 768, 'deberta')
    print(f'序列长 {n_:>4d}: BERT {b:.2e} | DeBERTa {db:.2e} | {db/b:.1f}×')
assert attn_flops(512, 768, 'deberta') == 3 * attn_flops(512, 768, 'bert')
print('\\n✅ 三项分解 = 约 3× 的注意力分数计算（论文实测端到端约 1.5-2× 训练开销）。')
print('   另一个隐性代价：非标准 QK^T，**与 FlashAttention 等 kernel 不兼容**。')"""),
    md("""## 4 · ALBERT：参数量 ≠ 效率

跨层共享把参数压掉 89%，但**推理 FLOPs 与延迟完全不变**——层数没少。"""),
    code("""def params_and_flops(vocab, H, n_layers, E=None, share_layers=False, seq_len=512):
    '''E: 嵌入分解的中间维度（None 表示不分解）。返回 (参数量, 每序列前向 FLOPs)。'''
    emb = vocab * H if E is None else vocab * E + E * H
    per_layer = 4 * H * H + 2 * H * (4 * H)              # QKVO + FFN
    layer_params = per_layer if share_layers else per_layer * n_layers
    params = emb + layer_params
    # FLOPs 与是否共享**无关**：还是要跑 n_layers 次
    flops = n_layers * (2 * seq_len * per_layer + 2 * seq_len * seq_len * H)
    return params, flops

configs = [
    ('BERT-base',        dict(vocab=30000, H=768,  n_layers=12)),
    ('ALBERT-base',      dict(vocab=30000, H=768,  n_layers=12, E=128, share_layers=True)),
    ('BERT-large',       dict(vocab=30000, H=1024, n_layers=24)),
    ('ALBERT-xxlarge',   dict(vocab=30000, H=4096, n_layers=12, E=128, share_layers=True)),
]
print(f"{'模型':<18s} {'参数(M)':>9s} {'前向GFLOPs':>12s} {'参数/BERT-base':>15s} {'FLOPs/BERT-base':>16s}")
p0, f0 = params_and_flops(vocab=30000, H=768, n_layers=12)
for name, cfg in configs:
    p, f = params_and_flops(**cfg)
    print(f'{name:<18s} {p/1e6:>9.1f} {f/1e9:>12.1f} {p/p0:>15.2f}× {f/f0:>15.2f}×')

p_bert, f_bert = params_and_flops(vocab=30000, H=768, n_layers=12)
p_alb,  f_alb  = params_and_flops(vocab=30000, H=768, n_layers=12, E=128, share_layers=True)
assert p_alb < 0.2 * p_bert, 'ALBERT-base 参数应少 80% 以上'
assert abs(f_alb - f_bert) < 1e-9, '**FLOPs 完全相同** —— 层数没少，还是要算 12 次'
p_xx, f_xx = params_and_flops(vocab=30000, H=4096, n_layers=12, E=128, share_layers=True)
assert f_xx > 3 * f_bert, 'ALBERT-xxlarge 虽然参数不多，但每层更宽 -> 比 BERT-base 慢数倍'
print(f'\\n✅ ALBERT-base: 参数 {p_alb/p_bert:.0%}，FLOPs {f_alb/f_bert:.0%} —— **一点都没省**。')
print(f'   ALBERT-xxlarge: 参数才 {p_xx/1e6:.0f}M，但 FLOPs 是 BERT-base 的 {f_xx/f_bert:.1f}×。')
print('   结论：**参数量是很差的效率代理指标**，要看 FLOPs 与实测延迟。')"""),
    md("""### 嵌入分解省在哪"""),
    code("""V_REAL, H = 30000, 768
plain = V_REAL * H
for E in [64, 128, 256]:
    fact = V_REAL * E + E * H
    print(f'E={E:>4d}: 嵌入参数 {fact/1e6:>5.1f}M (原 {plain/1e6:.1f}M, 省 {(1-fact/plain):.0%})')
assert V_REAL * 128 + 128 * H < 0.25 * plain, 'E=128 应省掉 75% 以上的嵌入参数'
print(f'\\n✅ 嵌入表在 BERT-base 里占 {plain/(plain + 12*(4*H*H+8*H*H)):.0%}，分解后大幅缩小。')
print('   这一项是**真省**（参数与显存都省），只是它省的不是瓶颈。')"""),
    md("""## ✏️ 练习 1：动态掩码的有效样本量

实现 `effective_samples(n_seqs, n_epochs, static_copies=None, L=20, k=3, seed=0)`：
统计模型在整个训练过程中见到的**不同 (序列, 掩码模式) 组合**数量。
`static_copies=None` 表示动态掩码（每 epoch 现采）；给整数表示静态副本数。"""),
    code("""def effective_samples(n_seqs, n_epochs, static_copies=None, L=20, k=3, seed=0):
    # TODO: 静态：每条序列预生成 static_copies 个模式，训练时循环取；
    #       动态：每条序列每个 epoch 现采一个模式。
    #       返回 len({(seq_id, frozenset(mask_positions))})
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s = effective_samples(100, 40, static_copies=10)
d = effective_samples(100, 40, static_copies=None)
assert s <= 100 * 10, '静态：最多 n_seqs × copies 种组合'
assert d > s, '动态应见到更多组合'
assert d <= 100 * 40, '动态：最多 n_seqs × epochs 种组合'
# 副本越多，静态越接近动态
s20 = effective_samples(100, 40, static_copies=20)
assert s20 > s, '更多静态副本 -> 更多组合'
print(f'静态10份: {s:,} 种 | 静态20份: {s20:,} 种 | 动态40轮: {d:,} 种')
print('✅ 练习 1 通过：动态掩码是零成本的数据增强')"""),
    md("""## ✏️ 练习 2：信号密度 × 信息量

实现 `objective_efficiency(objective, L, vocab, mask_rate=0.15)`：
返回 `(每序列预测数, 每次预测的最大信息量bit, 每序列信息上限bit)`。
- `'CLM'`：L 次预测，每次 `log2(vocab)` bit
- `'MLM'`：`L*mask_rate` 次，每次 `log2(vocab)` bit
- `'RTD'`：L 次，每次 1 bit
- `'RTD-multi'`：L 次，每次 `log2(k+1)` bit（k 类替换 + 原始），取 `k=3`"""),
    code("""def objective_efficiency(objective, L, vocab, mask_rate=0.15, k=3):
    # TODO: 返回 (n_pred, bits_per_pred, total_bits)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
L_, VV = 512, 30522
clm = objective_efficiency('CLM', L_, VV)
mlm = objective_efficiency('MLM', L_, VV)
rtd = objective_efficiency('RTD', L_, VV)
rtm = objective_efficiency('RTD-multi', L_, VV)
for name, r in [('CLM', clm), ('MLM', mlm), ('RTD', rtd), ('RTD-multi', rtm)]:
    print(f'{name:<10s} 预测数 {r[0]:>6.0f} | 每次 {r[1]:>5.1f} bit | 合计 {r[2]:>9.0f} bit')
assert clm[0] == L_ and abs(mlm[0] - L_ * 0.15) < 1
assert rtd[1] == 1.0 and rtd[0] == L_
assert mlm[2] > rtd[2], 'MLM 单次信息量大，总信息上限反而更高'
assert rtm[2] > rtd[2], '多分类替换检测的信息量介于两者之间'
assert clm[2] > mlm[2], 'CLM 在两个维度上都不吃亏（但表示是单向的）'
print('\\n✅ 练习 2 通过：ELECTRA 的实际优势 ~4×，而非朴素密度比的 6.7× —— 账要算细')"""),
    md("""## ✏️ 练习 3：相对位置分桶

实现 `rel_bucket(i, j, max_rel)`：返回相对位置 `i-j` 的桶索引，范围 `[0, 2*max_rel]`。
再实现 `bucket_matrix(n, max_rel)` 返回整个 `(n,n)` 索引矩阵。
必须满足：平移不变（`rel_bucket(5,4)==rel_bucket(2,1)`）、超距截断、对角线为 `max_rel`。"""),
    code("""def rel_bucket(i, j, max_rel):
    # TODO
    raise NotImplementedError

def bucket_matrix(n, max_rel):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert rel_bucket(5, 4, 4) == rel_bucket(2, 1, 4), '平移不变'
assert rel_bucket(3, 3, 4) == 4, '对角线（距离 0）应落在中间桶 max_rel'
assert rel_bucket(0, 100, 4) == 0, '极远的左向距离被截断到最小桶'
assert rel_bucket(100, 0, 4) == 8, '极远的右向距离被截断到最大桶'
M = bucket_matrix(6, 4)
assert M.shape == (6, 6)
assert (np.diag(M) == 4).all()
assert M.min() >= 0 and M.max() <= 8, '索引必须落在 [0, 2*max_rel]'
assert np.array_equal(M, bucket_matrix(6, 4)), '应是确定性的'
print(bucket_matrix(6, 3))
print('✅ 练习 3 通过：位置表只需 2*max_rel+1 行，而 BERT 需要 max_position_embeddings 行')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def effective_samples(n_seqs, n_epochs, static_copies=None, L=20, k=3, seed=0):
    r = np.random.default_rng(seed)
    seen = set()
    if static_copies is not None:
        pats = {s: [frozenset(r.choice(L, size=k, replace=False)) for _ in range(static_copies)]
                for s in range(n_seqs)}
        for ep in range(n_epochs):
            for s in range(n_seqs):
                seen.add((s, pats[s][ep % static_copies]))
    else:
        for ep in range(n_epochs):
            for s in range(n_seqs):
                seen.add((s, frozenset(r.choice(L, size=k, replace=False))))
    return len(seen)"""),
    code("""# 练习 2 参考答案
def objective_efficiency(objective, L, vocab, mask_rate=0.15, k=3):
    if objective == 'CLM':        n, bits = L, math.log2(vocab)
    elif objective == 'MLM':      n, bits = L * mask_rate, math.log2(vocab)
    elif objective == 'RTD':      n, bits = L, 1.0
    elif objective == 'RTD-multi': n, bits = L, math.log2(k + 1)
    else: raise ValueError(objective)
    return n, bits, n * bits"""),
    code("""# 练习 3 参考答案
def rel_bucket(i, j, max_rel):
    return int(np.clip(i - j, -max_rel, max_rel)) + max_rel

def bucket_matrix(n, max_rel):
    idx = np.arange(n)
    return np.clip(idx[:, None] - idx[None, :], -max_rel, max_rel) + max_rel"""),
    md("""---
## 🧪 真实数据胶囊：四种改进的效率前沿

把四个工作放到「算力 vs 分数」的平面上。你会看到它们**不在同一个坐标轴上竞争**。
（数字取自各论文报告的量级。）"""),
    code("""models = [
    # (名称, 参数M, 预训练算力(相对BERT-base), GLUE量级, 推理FLOPs(相对))
    ('BERT-base',      110, 1.00, 79.0, 1.00),
    ('RoBERTa-base',   125, 4.00, 86.0, 1.00),
    ('ELECTRA-base',   110, 0.25, 86.0, 1.00),
    ('ALBERT-base',     12, 1.00, 80.0, 1.00),
    ('DeBERTa-base',   140, 1.50, 88.0, 1.60),
]
print(f"{'模型':<16s} {'参数M':>7s} {'预训练算力':>10s} {'GLUE':>6s} {'推理FLOPs':>10s} {'分/算力':>8s}")
for name, p, c, g, f in models:
    print(f'{name:<16s} {p:>7d} {c:>10.2f}× {g:>6.1f} {f:>9.2f}× {g/c:>8.1f}')

by_name = {m[0]: m for m in models}
# ELECTRA：同分数、1/16 算力
assert by_name['ELECTRA-base'][3] == by_name['RoBERTa-base'][3]
assert by_name['ELECTRA-base'][2] < by_name['RoBERTa-base'][2] / 10
# ALBERT：参数少但推理 FLOPs 一样
assert by_name['ALBERT-base'][1] < 0.2 * by_name['BERT-base'][1]
assert by_name['ALBERT-base'][4] == by_name['BERT-base'][4]
# DeBERTa：分数最高但推理更贵
assert by_name['DeBERTa-base'][3] == max(m[3] for m in models)
assert by_name['DeBERTa-base'][4] > 1.0
print('\\n✅ 三种「更好」是三个不同方向：')
print('   RoBERTa/DeBERTa = 用更多算力换更高分数（前沿右上移）')
print('   ELECTRA         = 用更少算力达到同样分数（前沿左移）← 真正的效率改进')
print('   ALBERT          = 用同样算力换更小的权重文件（第三个维度）')
print('   问「谁最好」是坏问题；问「我被什么卡住」才对。')"""),
    md("""**🧪 胶囊练习**：实现 `recommend(constraint)`：给定约束返回推荐方案与理由。
`constraint ∈ {'compute', 'accuracy', 'latency', 'model_size'}`，
分别返回 `'ELECTRA-RTD'` / `'DeBERTa-v3'` / `'distill-to-smaller'` / `'ALBERT-factorized-embedding'`。"""),
    code("""def recommend(constraint):
    # TODO: 按上述映射返回字符串
    raise NotImplementedError"""),
    code("""# 自测
assert recommend('compute')    == 'ELECTRA-RTD'
assert recommend('accuracy')   == 'DeBERTa-v3'
assert recommend('latency')    == 'distill-to-smaller'
assert recommend('model_size') == 'ALBERT-factorized-embedding'
for c in ['compute', 'accuracy', 'latency', 'model_size']:
    print(f'{c:<12s} -> {recommend(c)}')
print('\\n⚠️  注意 latency 的答案**不是** ALBERT —— 参数共享不省延迟（本模块已验证）。')
print('✅ 胶囊练习通过')"""),
    code("""# 📖 胶囊参考答案
def recommend(constraint):
    return {'compute': 'ELECTRA-RTD',
            'accuracy': 'DeBERTa-v3',
            'latency': 'distill-to-smaller',
            'model_size': 'ALBERT-factorized-embedding'}[constraint]"""),
    md("""---
## 🔧 旁注：真实库里这些对应什么

- **动态掩码** → `DataCollatorForLanguageModeling` 在每个 batch 现场掩码（HF 默认就是动态的）。
- **ELECTRA** → `transformers.ElectraForPreTraining`（判别器）+ `ElectraForMaskedLM`（生成器）；下游只用判别器。
- **DeBERTa 解耦注意力** → `DebertaV2Model`；`config.pos_att_type=["p2c","c2p"]` 就是那两项。
- **ALBERT 参数共享** → `AlbertModel` 内部只有一份 `AlbertLayer`，循环调用 `num_hidden_layers` 次。
- **嵌入分解** → `config.embedding_size`（128）与 `config.hidden_size`（768）分离。
- **选型** → 今天做编码器任务，起点建议是 `microsoft/deberta-v3-base` 或现代化的 BERT 变体，**不是** `bert-base-uncased`。

怎么真正加载和微调这些模型，见 **C50**。"""),
    md("""### 小结
- **RoBERTa 零架构改动、只调配方，就提升 7 分**——BERT 是严重欠训练的。教训：宣布架构创新前先确认 baseline 训练充分。
- **动态掩码是免费的数据增强**；训练时的随机性能显著扩充有效样本量。
- **ELECTRA 的 RTD 把信号密度从 0.15 拉回 1.0**，且输入无 `[MASK]`。它不是 GAN（无对抗梯度）；生成器要「小」是难度匹配；λ=50 是为了让判别器拿到主要梯度。
- **DeBERTa 解耦内容与位置**，用相对位置获得平移不变与小位置表，代价是约 3× 注意力分数计算且与 FlashAttention 不兼容。
- **ALBERT 证明了参数量 ≠ 效率**：跨层共享省 89% 参数但 FLOPs 一点不省；它的持久贡献是 SOP 与嵌入分解。
- 四个维度**几乎正交、可以叠加**（DeBERTa-v3 = 解耦注意力 + RTD + 充分训练）。

下一站：**模块 03 · 下游微调三范式** —— 预训练好的表示，怎么接到分类、标注、抽取三类任务上。"""),
]
