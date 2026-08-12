# 术语词典 · Glossary（大规模预训练工程）

> 按主题分组，每条 2–3 句中文释义、英文术语保留原文（论文与工程文档的通用语言）。读 FineWeb / Chinchilla / μP / DoReMi 等论文遇到生词回这里查。本课用 numpy 在 CPU 上复现这些机制的玩具版，但术语与真实万亿 token 管线一一对应。

## 数据流水线与来源 · Data Pipeline & Sources

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| pretraining corpus | 预训练语料 | 用来做无监督下一 token 预测的海量文本（万亿 token 量级）。它的规模与质量，而非模型架构的小修小补，往往是决定基座模型能力上限的第一因素。 |
| CommonCrawl (CC) | —— | 定期抓取整个公开网络的开放数据集，每月一个快照（WARC/WET 格式），是绝大多数开源预训练语料的原始来源。原始 CC 噪声极大（菜单、模板、垃圾页），必须经过重度清洗。 |
| WARC / WET / WAT | —— | CommonCrawl 的三种格式：WARC 是原始 HTTP 响应（含 HTML），WET 是抽取出的纯文本，WAT 是元数据。预训练管线通常从 WET 起步或自行从 WARC 抽正文。 |
| FineWeb | —— | HuggingFace 2024 发布的 15T token 高质量英文网页语料及其完整清洗配方（Penedo 2024）。它把「数据清洗每一步到底带来多少下游收益」做了大规模消融，是当前最透明的开源数据管线参考。 |
| RefinedWeb | —— | Falcon 团队的工作（Penedo 2023），论证「精心清洗的纯网页数据」即可媲美掺了书籍/代码的精选语料，扭转了「网页数据低质」的成见。FineWeb 的前身。 |
| The Pile / C4 / RedPajama | —— | 早期有影响力的开源预训练语料：C4 是清洗过的 CommonCrawl（T5 用），The Pile 是 22 个领域的混合，RedPajama 复现 LLaMA 配方。是数据配比与清洗策略的活教材。 |
| text extraction | 正文抽取 | 从 HTML 里剥离导航/广告/页脚、留下主体文本的步骤（工具如 trafilatura、jusText）。抽取质量直接决定后续所有清洗的输入信噪比。 |
| boilerplate | 模板/样板文本 | 网页里重复出现的非内容片段（菜单、版权声明、cookie 提示）。不去掉会让模型浪费容量记忆这些噪声，也会污染去重与配比统计。 |

## 质量过滤 · Quality Filtering

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| quality filtering | 质量过滤 | 用规则或模型判断一篇文档「像不像值得学的文本」，把低质量页面（垃圾、乱码、SEO 农场）筛掉。是数据管线里收益最直接的一步。 |
| heuristic filter | 启发式过滤 | 一组人工设计的硬规则：文档长度、平均行长、标点比例、停用词比例、非字母字符占比、重复行比例等，超出阈值即丢弃。Gopher（Rae 2021）给出了一套被广泛沿用的规则。 |
| Gopher rules / MassiveText filters | Gopher 过滤规则 | DeepMind Gopher 论文提出的经典启发式集合：去掉停用词太少、符号/单词比过高、重复过多、过短或过长的文档。FineWeb、RedPajama 等都在其基础上调整。 |
| classifier-based filtering | 分类器过滤 | 训练一个轻量分类器（如 fastText 或逻辑回归）区分「高质量参考文本（如维基、书籍）」与「随机网页」，按分数过滤。GPT-3、LLaMA 都用过这招。 |
| fastText filter | —— | 用 Facebook 的 fastText 训练的快速文本分类器（基于 n-gram 词袋），常被用作质量分类器，因为它在亿级文档上仍能秒级打分。 |
| perplexity filter | 困惑度过滤 | 用一个在干净语料上训练的小语言模型给文档打 perplexity，过高（模型很意外）通常意味着乱码或低质，过滤之。CCNet（Wenzek 2019）的核心手段。 |
| precision / recall (of a filter) | 过滤器的精确率/召回率 | 评价过滤器的两个指标：precision = 被留下的里真正高质量的比例；recall = 所有高质量文档中被留下的比例。阈值在两者间权衡——预训练通常宁可错杀（高 precision）。 |
| FLOPs-matched ablation | 算力对齐消融 | 在固定训练 FLOPs（而非固定数据量）下比较不同数据处理方案的下游表现，是 FineWeb 评估清洗步骤价值的标准做法，避免「多喂数据」与「数据更好」的混淆。 |

## 去重与去污染 · Deduplication & Decontamination

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| deduplication (dedup) | 去重 | 删除语料里重复或近重复的文档/段落。Lee 2021 证明去重能显著降低记忆、提升下游效果、减少训练步数——是性价比极高的一步。 |
| exact dedup | 精确去重 | 用哈希（如对整篇文档求 hash）删掉逐字节相同的副本。简单但只能抓完全一样的，抓不到「改了一个词」的近重复。 |
| near-duplicate | 近重复 | 内容高度相似但非逐字相同的文档（转载、模板填充、轻微改写）。是网页语料里的重灾区，需要 MinHash/SimHash 这类近似方法检测。 |
| Jaccard similarity | Jaccard 相似度 | 两个集合交集大小除以并集大小，$J(A,B)=\frac{|A\cap B|}{|A\cup B|}$。用文档的 n-gram（shingle）集合算 Jaccard，是衡量近重复的标准度量。 |
| shingle / k-gram | shingle | 把文档切成所有长度为 k 的连续 token 片段构成的集合，用于算 Jaccard。k 越大越严格（要求更长的连续重合才算相似）。 |
| MinHash | —— | 用一组随机哈希、每个取集合中的最小哈希值，得到一个签名向量。两个集合签名对应位相等的比例，是其 Jaccard 相似度的无偏估计。把「比集合」变成「比短签名」。 |
| SimHash | —— | 另一种局部敏感哈希：把特征加权投影到随机超平面、按符号生成位串，两个文档的 SimHash 海明距离越小越相似。Google 用它做网页去重。 |
| LSH (Locality-Sensitive Hashing) | 局部敏感哈希 | 一类哈希：相似的输入大概率落进同一个桶。用它把「两两比较」的 $O(n^2)$ 降到「只比同桶的」，是亿级文档去重可行的关键。 |
| banding / band technique | 分带法 | LSH for MinHash 的核心技巧：把签名切成 b 个 band、每个 r 行，只要有一个 band 完全相同就进同一候选桶。调 (b, r) 可精确控制「相似度多高才大概率被抓」的 S 曲线。 |
| S-curve (LSH) | S 曲线 | 两文档成为候选对的概率随其真实 Jaccard 变化的曲线，形状是 $1-(1-s^r)^b$，呈 S 形。拐点（阈值）约在 $(1/b)^{1/r}$，是 banding 调参的依据。 |
| candidate pair | 候选对 | 经 LSH 分桶后落进同一桶、需要进一步精确比对的文档对。LSH 只负责高召回地缩小范围，候选对再算精确 Jaccard 确认。 |
| decontamination | 去污染 | 从训练集中删除与评测基准（benchmark）重叠的内容，防止「考题泄漏进训练集」导致评测虚高。常用 n-gram 重叠检测。 |
| n-gram overlap | n-gram 重叠 | 去污染的判据：若一段训练文本与某条测试样本共享足够长（如 13-gram）的连续片段，判定为污染并删除。GPT-3、PaLM 都报告过此类清洗。 |
| memorization | 记忆 | 模型逐字背下训练样本的现象。重复样本会被加倍记忆（Carlini 2022），既浪费容量又带来隐私/版权风险——去重是直接的缓解手段。 |

## Tokenization · 分词

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| tokenizer | 分词器 | 把原始文本切成模型词表里的离散 token（再映射为整数 id）的组件。它决定序列长度、未登录词处理、多语/代码/数字的表示效率，是模型与文本之间的「字节—子词」接口。 |
| subword tokenization | 子词分词 | 介于「整词」与「单字符」之间：常见词整体成 token、罕见词拆成子词片段。兼顾词表大小与未登录词覆盖，是现代 LLM 的标配。 |
| BPE (Byte-Pair Encoding) | 字节对编码 | 从字符开始，反复把语料里出现频率最高的相邻对合并成新 token，直到词表达到目标大小（Sennrich 2016 引入 NLP）。贪心、确定、训练快，是 GPT 系列的分词法。 |
| byte-level BPE | 字节级 BPE | 在 UTF-8 字节（256 个基元）而非 Unicode 字符上做 BPE，保证任何文本都能无损编码、永不出现 unknown token。GPT-2 起的主流做法。 |
| WordPiece | —— | BERT 用的子词算法。与 BPE 类似，但合并准则不是「频率最高」而是「使语料似然增益最大」的对（近似 $\frac{\text{freq}(xy)}{\text{freq}(x)\text{freq}(y)}$）。 |
| Unigram LM tokenizer | Unigram 语言模型分词 | Kudo 2018 提出：先建大候选词表，用 EM 训练一个 unigram 概率模型，反复剪掉对似然贡献最小的 token，直到目标大小。分词时取最大似然切分，并能给出多种切分（支持子词正则）。 |
| SentencePiece | —— | Kudo & Richardson 的分词库，把文本当原始字节流处理（空格也当普通符号 `▁`），语言无关、可逆，支持 BPE 与 Unigram 两种算法。多语模型的常用实现。 |
| merge rules | 合并规则 | BPE 训练产出的有序合并表（如 `('t','h')→'th'`）。编码时按这个顺序贪心地把字符序列合并成 token，顺序不可乱。 |
| vocabulary size | 词表大小 | tokenizer 能输出的不同 token 总数（如 32k、50k、128k、256k）。它与序列长度、embedding 参数量、fertility 之间存在三角权衡。 |
| fertility | 繁殖率 | 平均每个词（或每个字节）被切成多少个 token。fertility 越低，同样文本占的 token 越少（序列更短、推理更省），是衡量 tokenizer 压缩效率的关键指标，尤其影响非英语语言。 |
| compression ratio | 压缩率 | 原始字节数 ÷ token 数，即「平均每个 token 顶多少字节」。越高越好（同样 context 能装更多文本）。词表越大、与语料越匹配，压缩率越高。 |
| OOV (out-of-vocabulary) | 未登录词 | 不在词表里的词。字节级方法从根本上消除了 OOV（任何字节都能编码），这也是它流行的原因之一。 |
| continuation token / `Ġ` `▁` | 续接标记 | 标记一个子词是否处在词首（前面有空格）。GPT 系用 `Ġ`、SentencePiece 用 `▁`，让 tokenizer 能可逆地恢复空格。 |

## 缩放与超参迁移 · Scaling & HP Transfer

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| scaling law | 缩放定律 | 描述模型损失如何随参数量 N、数据量 D、算力 C 幂律下降的经验公式，$L(N,D)=E+\frac{A}{N^\alpha}+\frac{B}{D^\beta}$。用小规模实验拟合、外推到大规模，指导资源分配。 |
| Chinchilla / compute-optimal | Chinchilla / 算力最优 | Hoffmann 2022 的发现：给定算力，参数量 N 与训练 token 数 D 应大致等比例放大（约 20 token/参数），此前的大模型（如 GPT-3）严重「训练不足」。改写了预训练的资源分配观。 |
| parametrization | 参数化方案 | 网络的初始化方差与各层学习率随宽度变化的规则。标准做法（SP）在变宽时会让激活/更新尺度漂移，导致最优超参随宽度移动；μP 修正了这点。 |
| μP (Maximal Update Parametrization) | 最大更新参数化 | Yang 2021 提出的一套 init/lr/logit 缩放规则，使每层激活与每步更新的尺度在变宽时保持 $O(1)$。其直接红利是 hyperparameter transfer：在小模型调好的最优超参，几乎不变地迁移到大模型。 |
| Tensor Programs | —— | Yang 系列工作的理论框架，用「张量程序」统一刻画无限宽神经网络的行为，μP 是其推论。是理解「为什么超参能跨宽度迁移」的数学根基。 |
| hyperparameter transfer (μTransfer) | 超参迁移 | μP 的应用：在一个便宜的小模型（小宽度）上网格搜出最优学习率等超参，直接（按 μP 规则缩放后）用到昂贵的大模型上，省下在大模型上调参的巨额算力。 |
| coordinate check | 坐标检查 | 验证 μP 是否实现正确的诊断：训练几步，画出各层激活/梯度/更新的典型坐标量级随宽度的变化。正确的 μP 下这些量级应与宽度无关（曲线水平）。 |
| width / fan-in | 宽度 / 扇入 | 宽度指隐藏维度 $d$；fan-in 指一层输入的维数。初始化方差通常按 $1/\text{fan-in}$ 设置，μP 进一步规定 lr 也随宽度调整。 |
| abc-parametrization | abc 参数化 | Yang 用三组指数 (a, b, c) 统一描述「乘法因子、初始化、学习率」随宽度的缩放，SP 与 μP 是其中两个特定点。 |
| attention logit scaling (1/d) | 注意力 logit 缩放 | μP 规定注意力分数用 $1/d$（而非标准的 $1/\sqrt d$）缩放，以保证宽度增大时 logit 尺度稳定。是 μP 与标准 Transformer 的一个显式差异。 |

## 训练稳定性 · Training Stability

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| loss spike | 损失尖峰 | 训练过程中 loss 突然暴涨（有时不再回落）的现象，大模型尤甚。成因包括梯度爆炸、坏 batch、数值溢出、注意力 logit 过大。是大规模训练最头疼的不稳定。 |
| gradient clipping | 梯度裁剪 | 当梯度的全局范数超过阈值时，等比例缩小整个梯度向量，防止单步更新过大引爆训练。是几乎所有大模型训练的标配护栏。 |
| global grad norm | 全局梯度范数 | 所有参数梯度拼成一个向量后的 L2 范数。监控它的曲线能提前发现不稳定（突然飙升常预示即将 spike）。 |
| z-loss | —— | 给 softmax 的归一化项（log-Z）加一个小的辅助惩罚 $\lambda(\log Z)^2$，把 logit 拉回合理量级，抑制输出 logit 漂移导致的不稳定。PaLM（Chowdhery 2022）报告它能减少 spike。 |
| QK-norm (query-key normalization) | QK 归一化 | 在算注意力分数前对 query、key 向量做归一化（如 RMSNorm），防止注意力 logit 过大把 softmax 推向饱和、引发不稳定。被许多前沿模型采用。 |
| warmup | 预热 | 训练初期把学习率从 0 线性升到峰值的阶段。冷启动时参数与 Adam 的二阶矩估计都不可靠，直接用大 lr 极易 spike，warmup 给系统一个稳定期。 |
| learning rate schedule | 学习率调度 | lr 随训练步数变化的曲线，典型为「warmup 上升 + cosine/linear 衰减」。调度形状显著影响最终 loss 与稳定性。 |
| cosine decay / WSD schedule | 余弦衰减 / WSD 调度 | cosine 把 lr 沿余弦曲线降到接近 0；WSD（Warmup-Stable-Decay）则是先恒定一段再快速衰减，便于中途加数据或延长训练，近年流行。 |
| mixed precision (bf16/fp16/fp32) | 混合精度 | 用低精度（bf16/fp16）做大部分计算以省显存提速，关键累加（如 master weights、归一化）保留 fp32。bf16 动态范围大、比 fp16 更不易溢出，是大模型训练首选。 |
| fp32 master weights | fp32 主权重 | 即便前向/反向用 bf16，优化器仍维护一份 fp32 的权重副本来累加微小更新，避免低精度下「小梯度被舍入吞掉」。 |
| initialization scale | 初始化尺度 | 权重初始随机值的标准差。过大→激活/梯度爆炸，过小→信号消失；常按 $1/\sqrt{\text{fan-in}}$ 或更保守的 $1/\sqrt{N_{\text{layers}}}$（深层缩放）设置。 |
| residual scaling / depth scaling | 残差/深度缩放 | 按层数缩小残差分支或初始化（如除以 $\sqrt{2L}$），防止深层网络里残差累加导致激活方差随深度线性增长。GPT-2、megatron 等的稳定技巧。 |

## 数据配比与合成数据 · Data Mixtures & Synthetic Data

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data mixture | 数据配比 | 训练语料里各 domain（网页、代码、书籍、论文、多语…）所占的采样比例。配比直接影响模型在各能力上的强弱，是预训练最重要的「旋钮」之一。 |
| domain weights | 域权重 | 各 domain 的采样概率向量（和为 1）。怎么设定它——靠经验、靠下游验证 loss、还是靠 DoReMi 这类自动优化——是配比研究的核心问题。 |
| DoReMi | —— | Xie 2023 提出的自动配比法：先训一个小 proxy 模型，用 group DRO（分布鲁棒优化）找出让「最差 domain」也学得好的域权重，再用这套权重训大模型。无需下游标签即可优化配比。 |
| group DRO (distributionally robust optimization) | 分组分布鲁棒优化 | 不最小化平均损失，而是最小化「最差一组的损失」。DoReMi 用它来给学得慢的 domain 自动加权，得到更均衡的配比。 |
| curriculum learning | 课程学习 | 按由易到难（或按质量、按 domain）安排训练数据的顺序，而非完全随机。预训练里常见做法是后期提高高质量数据比例（quality annealing）。 |
| epoch / repetition | 轮次 / 重复 | 把同一份数据重复训练多遍。数据有限时不得不重复，但重复的边际收益递减、过多会过拟合与加剧记忆。 |
| data-constrained scaling laws | 数据受限缩放定律 | Muennighoff 2023 的工作：当数据量成为瓶颈、必须重复 epoch 时，缩放定律如何修正。结论包括「重复约 4 个 epoch 内收益接近全新数据，之后迅速衰减」。 |
| token budget | token 预算 | 一次训练计划消耗的总 token 数（含重复）。在数据受限时，要在「重复已有数据」与「参数/算力分配」之间权衡，受 data-constrained scaling law 指导。 |
| synthetic data | 合成数据 | 用（通常更强的）模型生成的训练数据，用于补充稀缺领域、提升质量或做能力蒸馏。是当前突破「数据墙」的热门方向，但有崩溃风险。 |
| model collapse | 模型崩溃 | 反复用模型自己生成的数据训练后续模型，导致分布尾部丢失、多样性塌缩、质量退化的现象（Shumailov 2023）。提示合成数据需与真实数据混合、严控比例。 |
| data wall | 数据墙 | 高质量人类文本即将被训练耗尽的担忧。它推动了去重后重复利用、合成数据、多模态数据等方向的研究，是 data-constrained scaling 的现实背景。 |
| quality annealing | 质量退火 | 训练末期把数据切换为高质量子集（同时常配合 lr 衰减），用少量优质 token 给模型「最后打磨」，被多个前沿模型报告为有效。 |

## 评估与方法论 · Evaluation & Methodology

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| validation loss / perplexity | 验证损失 / 困惑度 | 在留出集上的交叉熵损失（perplexity = exp(loss)）。预训练里它是最直接的优化目标与配比/清洗效果的快速代理，但不完全等同于下游能力。 |
| downstream evaluation | 下游评测 | 在具体任务（如 MMLU、HellaSwag、代码、推理）上测模型能力。数据/超参决策的最终裁判，但比验证 loss 贵得多。 |
| ablation | 消融实验 | 控制其他变量、只改一个因素（如开/关去重）来测它的净贡献。FineWeb 用大量 FLOPs-matched 消融逐步验证每个清洗步骤。 |
| proxy model | 代理模型 | 一个便宜的小模型，用来快速试验数据/配比/超参决策（如 DoReMi 的 proxy、scaling law 拟合点），再把结论迁移到大模型。 |
| differential testing / 对拍 | 对拍 | 用一个朴素但绝对正确的参考实现校验「优化版」实现：要求两者输出一致。本课每个 numpy 算法（MinHash 估 Jaccard、BPE 编码、配比优化）都对拍参考，靠 `assert` 兜底正确性。 |
