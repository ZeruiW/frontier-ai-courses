# 术语词典 · Glossary（大规模数据工程）

> 按主题分组，每条 2–3 句释义。读 FineWeb / Dolma / WebDataset / Mosaic StreamingDataset 文档或去重/去污染论文遇到生词回这里查；英文术语保留原文（社区与论文的通用语言）。本课用小规模真实模拟 + 复杂度/吞吐账理解这些概念，但术语与真实 PB 级管线一一对应。

## 规模与世界观 · Scale & Mindset

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data engineering (for training) | 训练数据工程 | 把原始网页/代码/文献等加工成可直接喂给训练循环的、去重过、过滤过、可溯源的 token 流的全部基础设施工作。与「数据科学」（决定保留什么）互补，本课聚焦「在 PB 规模下怎么把它工程化地做出来」。 |
| petabyte (PB) scale | PB 级 | 1 PB = 10^15 字节。现代预训练语料（CommonCrawl 快照、代码、书籍）原始体量常达数十到数百 TB 乃至 PB，单机内存（GB 级）放不下，逼出流式、分片、外存算法等一切工程手段。 |
| trillion-token (1e12) | 万亿 token | 前沿模型训练消耗 1e12～1.5e13 量级的 token。token 数 × 每 token 的处理成本决定了去重/分词/过滤必须有极高吞吐，纸面上「能跑」的 O(n²) 算法在这个量级会变成几百年。 |
| complexity ledger | 复杂度账 | 本课方法论：对每个数据操作写出其时间/空间复杂度（如暴力配对 O(n²)、LSH 分桶 O(n)），代入真实 n（如 1e12）估算耗时与存储，判断「规模化是否可行」。 |
| throughput ledger | 吞吐账 | 本课方法论：用「条/秒、MB/秒、核数、并行效率」估算一条管线处理完整语料要多久、要多少机器，把抽象的「快/慢」变成可规划的工程数字。 |
| throughput vs latency | 吞吐 vs 延迟 | 吞吐 = 单位时间处理的数据量（管线关心）；延迟 = 单条数据从进到出的耗时（在线服务关心）。数据工程几乎总是优化吞吐，可以容忍单条高延迟。 |
| out-of-core / external-memory | 外存 / 核外算法 | 数据大到放不进内存时，把它留在磁盘/对象存储、分块流式处理的算法范式。本课的流式去重、流式加载、流式分词都是其体现。 |
| embarrassingly parallel | 易并行 | 任务能切成互不依赖的子任务、几乎无需通信即可并行（如逐文档过滤、逐 shard 分词）。数据工程的大部分阶段属此类，是横向扩展（加机器）见效的根本原因。 |
| Amdahl's law | 阿姆达尔定律 | 加速比上限 = 1 / (s + (1−s)/p)，s 为串行占比、p 为并行核数。即便 p→∞，加速比也被串行部分 1/s 卡死，提醒你优化前先量化串行瓶颈（如 tokenizer 的合并步骤、最终的跨分片合并）。 |

## 去重 · Deduplication

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| exact deduplication | 精确去重 | 删除字节/哈希完全相同的文档。用内容哈希（如 SHA-1/MD5）当 key、放进集合或排序后扫描即可，复杂度 O(n)，但只能抓到逐字节重复，抓不住「改了一个字」的近重复。 |
| near-duplicate / fuzzy dedup | 近重复去重 | 删除内容高度相似（但非逐字节相同）的文档，如同一文章的不同抓取、模板化页面。需要相似度估计（Jaccard / 汉明），是大规模去重的主战场。 |
| document-level vs substring-level | 文档级 vs 子串级 | 去重粒度：文档级删整篇近重复（MinHash/LSH 擅长）；子串级（Lee 2021 的 ExactSubstr）用后缀数组找并删跨文档重复的长子串，能去掉嵌在不同文档里的同一段落。 |
| shingle / n-gram (for dedup) | shingle / n 元组 | 把文档切成连续 k 个词/字符的集合（如 5-gram），用集合的重叠程度衡量两文档相似度。是 MinHash/SimHash 的输入表示。 |
| Jaccard similarity | Jaccard 相似度 | 两集合交集大小 ÷ 并集大小 ∈ [0,1]，衡量 shingle 集合的重叠。去重的「真值」相似度，但精确计算需两两比较，O(n²) 不可扩展。 |
| MinHash | 最小哈希 | 用 K 个独立哈希函数，取每个哈希下集合元素的最小值，得到一个 K 维签名。两签名对应位置相等的比例 = Jaccard 的无偏估计。把「比集合」变成「比定长签名」，是大规模去重的基石（Broder 1997）。 |
| MinHash signature | MinHash 签名 | 一篇文档的 K 维最小哈希向量。K 越大估计越准（方差 ~ J(1−J)/K），但签名越占空间。常用 K=128～256。 |
| LSH (Locality-Sensitive Hashing) | 局部敏感哈希 | 一族哈希，使相似项以高概率落进同一桶、不相似项以高概率分开。把「和所有人比」变成「只和同桶的人比」，是把 O(n²) 候选生成降到近 O(n) 的关键（Indyk & Motwani 1998）。 |
| LSH banding | LSH 分带 | 对 MinHash 签名的实现：把 K 维签名切成 b 个 band、每 band r 行（K=b·r），band 内全相等才同桶。两文档至少一个 band 碰撞即成候选。命中概率曲线 1−(1−J^r)^b 呈 S 形，调 (b,r) 即调阈值。 |
| S-curve / threshold | S 形曲线 / 阈值 | LSH 命中概率随 Jaccard 变化的曲线，近似阈值 ≈ (1/b)^(1/r)。阈值附近概率陡升，使「高于阈值几乎必中、低于阈值几乎不中」。调 (b,r) 在召回（漏掉真重复）与精度（误判+候选量）间权衡。 |
| candidate pair | 候选对 | LSH 分桶后落入同一桶、需进一步验证的文档对。候选量远小于 C(n,2)，但仍需对每对算真 Jaccard 做精筛，候选爆炸是 LSH 调参的现实约束。 |
| SimHash | —— | 另一种近重复签名（Charikar 2002）：把每个特征的哈希位按权投票，得到一个 b 位指纹；两文档指纹的汉明距离越小越相似。Google 用它做网页去重，签名短、比对快，适合海量。 |
| Hamming distance | 汉明距离 | 两个等长 0/1 串对应位不同的个数。SimHash 用它度量相似度（距离小=相似）；近重复阈值常取 b=64 位指纹下汉明距离 ≤ 3。 |
| banding for Hamming / multi-index | 汉明分块多索引 | 把 b 位指纹切成若干块，按「鸽巢原理」——汉明距离 ≤ k 则至少一块完全相同——只对同块文档比对，是 SimHash 大规模检索的加速法。 |
| cross-shard merge | 跨分片合并 | 语料分成很多 shard 分别去重后，还需把跨 shard 的重复也消掉。常用 union-find（并查集）把所有候选对连成连通分量、每分量留一份，是分布式去重最后一道（也最易成串行瓶颈的）工序。 |
| union-find / connected components | 并查集 / 连通分量 | 把「a 与 b 重复、b 与 c 重复」传递地归并成一个重复簇的数据结构/算法。近 O(α(n)) 近乎线性，是跨分片去重做「保留每簇一份」的标准工具。 |
| collision (hash) | 哈希碰撞 | 不同输入得到相同哈希值。精确去重用强哈希（SHA-1/256）使碰撞概率可忽略；MinHash/SimHash 则刻意利用「相似→碰撞」的受控碰撞。 |

## 数据加载与分片 · Loading & Sharding

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| dataloader | 数据加载器 | 在训练循环旁不断把样本组成 batch 喂给模型的组件。大规模下它必须流式、可并行、能预取，否则 GPU 会饿着等数据（data-starved）。 |
| streaming dataset | 流式数据集 | 不把数据全载入内存、而是边读边吐样本的数据集（如 HF IterableDataset、Mosaic StreamingDataset、WebDataset）。是 PB 级语料的唯一可行加载方式。 |
| shard | 分片 | 把大数据集切成的一个个中等大小（常 100MB～1GB）的文件块。分片让数据能分布存储、并行读取、断点续训，是大规模数据集的标准物理布局。 |
| WebDataset | —— | 把样本打包成 tar 归档、按顺序流式读取的格式/库（Aizman et al.）。顺序 IO 对对象存储/网络文件系统友好，避免海量小文件的随机寻址开销。 |
| StreamingDataset (Mosaic) | —— | MosaicML 的流式数据集格式（MDS）与库，支持从对象存储边下边训、确定性恢复、跨 epoch 的全局确定打乱，是生产级流式加载的代表实现。 |
| shard assignment / sharding | 分片分配 | 把哪些 shard 分给哪个 worker/rank 读取的策略。要保证不重不漏、负载均衡，并在多机多卡（DDP）下与数据并行的 rank 对齐。 |
| shuffle buffer | 打乱缓冲区 | 流式加载里近似全局打乱的手段：维护一个容量 B 的缓冲，每次随机吐一个、再补入下一个流入样本。B 越大越接近真随机，但占内存；B=1 等于不打乱。 |
| global vs local shuffle | 全局 vs 局部打乱 | 全局打乱 = 任意两样本都可能相邻（理想但需全量在手）；流式只能局部打乱（shard 顺序打乱 + 缓冲区打乱）来逼近，本课会量化这个近似的偏差。 |
| prefetch | 预取 | 在模型计算当前 batch 时，后台线程/进程提前把下一批数据读好、解码好，用 IO 与计算的重叠把读数据的延迟藏起来。 |
| pipeline overlap | 流水重叠 | 让「读 IO」「解码/解压」「tokenize」「拷到设备」「计算」各阶段在不同 batch 上并发执行，使整体吞吐受最慢一级（瓶颈级）支配而非各级之和。 |
| backpressure | 背压 | 当下游（如训练）比上游（如读数据）慢时，让上游放慢以免内存被未消费的数据撑爆的机制。流式管线用有界队列实现背压。 |
| data starvation | 数据饥饿 | GPU 算完了却没有下一批数据可算、被迫空转。是数据管线吞吐不足的典型症状，说明瓶颈在数据侧而非计算侧。 |
| epoch / resumption | 轮次 / 断点续训 | 一个 epoch = 完整过一遍数据。大规模训练要能在任意步崩溃后精确恢复到「读到哪了、打乱状态如何」，需要确定性的 shard 顺序与缓冲状态记录。 |

## Tokenization 与打包 · Tokenization & Packing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| tokenization (at scale) | 大规模分词 | 把万亿字符的文本切成 token id 序列。本身易并行（逐文档独立），但万亿量级下吞吐、内存、padding 浪费都成为要工程优化的实打实问题。 |
| BPE / subword | 字节对编码 / 子词 | 主流分词法，把高频字节/字符对反复合并成子词单元。训练 tokenizer 的合并步骤偏串行；推理（编码）则可逐文档并行。 |
| sequence packing | 序列打包 | 把多条短文本拼接进同一个定长训练序列（用分隔符/文档掩码隔开），消除把短序列 padding 到最大长度造成的算力浪费。是提高有效 token 利用率的关键工程手段。 |
| padding waste | padding 浪费 | 为把不等长序列对齐到同一长度而填入的占位 token，它们不产生有用梯度却照样消耗算力。浪费率 = padding token 数 ÷ 总 token 数，packing 的目标就是把它压到接近 0。 |
| document mask / attention mask | 文档掩码 | packing 后用来阻止注意力跨越文档边界（避免一篇文档「看到」拼在它后面的无关文档）的掩码。是 packing 正确性的关键，否则会引入跨文档泄漏。 |
| bin packing | 装箱 | 把不同长度的序列尽量塞满定长「箱子」的组合优化问题（NP 难）。序列 packing 是它的近似版，常用首次适配（first-fit）/贪心策略求得接近最优的打包率。 |
| token id / vocab | token 编号 / 词表 | token 在词表里的整数下标。词表大小决定 id 用几个字节存（如 <65536 用 uint16），直接影响 tokenized 语料的磁盘体量。 |
| tokens-per-second | 每秒 token 数 | 分词吞吐的核心指标。乘以核数与并行效率，即可估算分完整个语料要多久——本课会从零做这笔吞吐账。 |
| memory-mapped (mmap) | 内存映射 | 把磁盘上的 token 数组当内存数组访问、由 OS 按需分页，让训练能随机读取远大于内存的 token 文件（如 GPT-NeoX/Megatron 的 .bin/.idx 格式）。 |
| context length / sequence length | 上下文长度 / 序列长度 | 训练序列的定长（如 2048/8192）。它决定 packing 的箱子大小，也决定 padding 浪费与打包难度。 |

## 质量过滤 · Quality Filtering

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| multi-stage filtering | 多阶段过滤 | 把质量过滤排成由便宜到昂贵的多级流水（启发式规则→分类器→perplexity），让最贵的阶段只处理前面筛剩的小部分数据，是大规模过滤的成本控制核心。 |
| heuristic filter | 启发式过滤 | 用廉价规则筛掉明显低质：文档过短/过长、符号比例过高、重复行过多、停用词比例异常等（Gopher/C4 风格规则）。每文档 O(长度)，最便宜，放在管线最前。 |
| classifier filter | 分类器过滤 | 训一个轻量分类器（如逻辑回归/fastText）区分「高质量」（如维基、书籍）与「随机网页」，给每文档打分、按阈值留存。比启发式贵、比 perplexity 便宜，放中间。 |
| perplexity filter | 困惑度过滤 | 用一个语言模型给文档算困惑度（越低越「像自然语言」），筛掉乱码/机器生成/低质文本。需跑模型，最贵，放在管线最后只处理少量候选。 |
| language identification (LID) | 语言识别 | 判定文档语种（常用 fastText langid / CLD3），用于筛出目标语言、做按语言的配比。是多语料管线的早期必备阶段。 |
| PII detection | 个人可识别信息检测 | 识别并脱敏邮箱、电话、身份证号、密钥等敏感信息。常用正则 + 规则（高吞吐）打底，必要时叠 NER 模型。是合规与隐私的硬要求。 |
| retention rate / yield | 留存率 | 某阶段过滤后留下的数据比例。各阶段留存率连乘 = 端到端留存率，是规划「原始要多少数据才够训练目标」的关键账（如 CommonCrawl 过滤后常只剩个位数百分比）。 |
| pipeline orchestration | 管线编排 | 把多个过滤/转换阶段串成可并行、可重试、可监控的工作流（DAG）。决定阶段顺序（便宜在前）、并行度、失败处理，直接决定端到端吞吐。 |
| precision / recall (filtering) | 精度 / 召回（过滤） | 过滤器把「该删的删掉」的能力。精度 = 删掉的里有多少真该删；召回 = 真该删的里删掉了多少。阈值在二者间权衡，宁可错杀还是宁可放过取决于场景。 |
| false positive / negative | 假阳 / 假阴 | 假阳 = 好数据被误删（损失多样性）；假阴 = 坏数据漏网（污染语料）。过滤阈值就是在这两类错误间选点。 |

## 溯源与去污染 · Provenance & Decontamination

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| data provenance / lineage | 数据溯源 / 谱系 | 记录每份数据从原始来源经哪些处理步骤、用哪个版本的代码/配置得到当前状态的完整链路。让「这条数据哪来的、怎么变的」可回溯，是审计与复现的基础。 |
| benchmark decontamination | 基准去污染 | 从训练集里删除与评测基准（如 MMLU、GSM8K）重叠的样本，防止「考题泄漏进训练集」造成虚高分数。是可信评测的前提，本课模块 05 从零实现。 |
| data contamination / leakage | 数据污染 / 泄漏 | 评测集（或其改写）混进了训练数据，使模型「背过答案」、评测分数失真。规模越大、爬取越广，无意污染的风险越高。 |
| n-gram overlap | n 元组重叠 | 去污染的主力检测法：若训练文档与某基准样本共享足够长（如 13-gram）的连续片段，判为污染。Brown et al.（GPT-3）与 Carlini 等都用此类规则。 |
| contains-check / substring match | 子串包含检测 | 判断基准题面是否作为子串出现在训练文档中。精确但对改写无能，故常与 n-gram 重叠、近重复检测配合。 |
| content hash / checksum | 内容哈希 / 校验和 | 对一份数据算出的定长指纹（如 SHA-256）。相同哈希=相同内容，用于精确去重、快照标识、完整性校验。 |
| reproducible snapshot | 可复现快照 | 给某次训练用的数据集打的不可变版本标签：固定每个 shard 的内容哈希与清单（manifest），使「同一份数据」可被任何人精确取回重建。 |
| manifest | 清单 | 列出数据集所有 shard 及其哈希、大小、来源的元数据文件。是快照、完整性校验、增量更新的索引。 |
| audit / data audit | 审计 | 系统性检查数据集的来源合规、许可、PII 残留、配比、污染等，并产出可查的报告。规模越大越需要自动化审计而非人工抽查。 |
| reproducibility | 可复现性 | 给定相同的数据快照、代码版本、随机种子，能重建出相同的训练输入。是科学严谨与事故排查的底线，靠 lineage + 内容哈希 + 固定种子共同保证。 |
| dataset card / datasheet | 数据集卡片 | 记录数据集的构成、来源、处理、已知偏差与适用范围的文档（Gebru et al. _Datasheets_）。是数据透明与负责任发布的实践，审计报告的人读版。 |

## 真实数据集与工具生态 · Real Corpora & Tooling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| CommonCrawl | —— | 定期抓取的开放网页存档，每月快照达数百 TB。是几乎所有开放预训练语料的原料，也是去重/过滤/去污染工程的主要试炼场。 |
| FineWeb | —— | HuggingFace 基于 CommonCrawl 做的 15T-token 高质量英文语料（Penedo et al. 2024），公开了完整的过滤+去重配方与消融，是本课工程实践的现实对标。 |
| Dolma | —— | AI2 的 3T-token 开放语料与开源数据工具包（Soldaini et al. 2024），公开了管线代码、去重、去污染、许可处理，是「数据工程全流程开源」的标杆。 |
| RefinedWeb / The Pile / RedPajama | —— | 几个有影响力的开放预训练语料。各自公开了不同的过滤/去重/配比取舍，是研究「工程决策如何影响数据」的对照样本。 |
| MDS / WebDataset / Parquet / Arrow | 分片与列式格式 | 大规模数据的物理存储格式：MDS/WebDataset 面向流式训练；Parquet/Arrow 面向列式分析与高效 IO。选格式即选了 IO 模式与生态。 |
| object storage (S3/GCS) | 对象存储 | PB 级数据的事实标准存储（S3、GCS）。高吞吐、按量付费、但高延迟、偏好大对象顺序读——这塑造了 shard 大小与流式读取的设计。 |
| MapReduce / Spark / Ray Data | 分布式数据处理 | 把数据处理切成 map/shuffle/reduce 在集群上并行执行的框架。大规模去重的跨分片合并、过滤的横向扩展常用它们实现，是把本课算法落到集群的工具。 |
| deterministic / seeded | 确定性 / 带种子 | 用固定随机种子让打乱、采样、分片可复现。是断点续训、调试、审计都依赖的工程纪律。 |
