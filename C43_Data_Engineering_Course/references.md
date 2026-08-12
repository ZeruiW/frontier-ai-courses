# 参考清单 · References（大规模数据工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用小规模模拟 + 复杂度账复现的每个机制，都能在下列文献里找到真实 PB 级管线上的对应实现与权衡。本课与 C21（大规模预训练，讲数据科学）互补：C21 讲「保留什么、怎么配比」，这里讲「PB 规模下怎么工程化地去重/加载/分词/过滤/溯源」。

## 去重：算法与大规模实践 · Deduplication
- ★ **Lee, Ippolito, Nystrom, Zhang, Eck, Callison-Burch & Carlini 2021, _Deduplicating Training Data Makes Language Models Better_** — 本课模块 01 的奠基必读。系统论证训练数据里的重复会让模型记忆、虚高困惑度、降低有效数据量，并给出两套方法：精确子串去重（ExactSubstr，后缀数组找跨文档重复长串）与近似文档去重（MinHash+LSH）。读它理解「为什么去重不是可选项」以及两种粒度的取舍。
- ★ **Broder 1997, _On the Resemblance and Containment of Documents_** — MinHash 的原始论文。提出用「最小哈希一致的概率 = Jaccard」把集合相似度估计变成定长签名比较，是一切大规模近重复去重的数学基石。模块 01 的 MinHash 推导直接来自它。
- ★ **Indyk & Motwani 1998, _Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality_** — LSH 的奠基论文。定义局部敏感哈希族，证明可把近邻搜索的复杂度从线性扫描降到亚线性，是 LSH banding 把 O(n²) 配对变可行的理论来源。
- ★ **Charikar 2002, _Similarity Estimation Techniques from Rounding Algorithms_** — SimHash 的出处。用随机超平面投影把相似度映射到指纹的汉明距离，签名短、比对快。模块 01 的 SimHash 与汉明去重据此实现，Google 网页去重（Manku et al. 2007）即其大规模落地。
- **Manku, Jain & Das Sarma 2007, _Detecting Near-Duplicates for Web Crawling_** — SimHash 在 Google 网页去重的工程化：64 位指纹、汉明距离 ≤3、多索引（按块分桶）加速十亿级检索。读它看 SimHash 怎么真正跑在 web 规模上。
- **Leskovec, Rajaraman & Ullman, _Mining of Massive Datasets_, 第 3 章** — 把 shingling、MinHash、LSH banding、S 形阈值曲线讲得最透的教材章节，含 (b,r) 调参的概率推导。模块 01 的 S-curve 与阈值公式以它为准，强烈建议精读。
- **Penedo et al. 2023, _The RefinedWeb Dataset_** — RefinedWeb 公开了「仅靠 web、靠严格去重+过滤也能媲美精选语料」的配方与消融，含 MinHash 去重的工程参数，是去重在真实语料上效果的有力证据。

## 流式加载与分片 · Streaming & Sharding
- ★ **Aizman, Maltby & Breuel 2019/2022, _WebDataset_（论文与库文档）** — 把样本打包成 tar、顺序流式读取的格式。解决「海量小文件随机寻址拖垮对象存储」的问题，奠定大规模流式加载偏好顺序 IO 的设计哲学。模块 02 的 shard 格式直接对标它。
- ★ **MosaicML, _StreamingDataset_（库与设计文档）** — 生产级流式数据集（MDS 格式）：从对象存储边下边训、确定性断点续训、跨 epoch 的全局确定打乱。读它理解 shuffle 缓冲、shard 分配、可恢复性在真实训练里怎么协同，是模块 02 的现实标杆。
- **HuggingFace Datasets, _IterableDataset / streaming_（文档）** — 最常用的流式数据集 API：`load_dataset(..., streaming=True)`、`shuffle(buffer_size=...)`。模块 02 的 shuffle 缓冲区模拟直接对应它的 `buffer_size` 参数，跑完本课你会确切知道这个参数该设多大。
- **NVIDIA, _DALI（Data Loading Library）文档_** — GPU 加速的数据加载/解码流水，把预取、解码、增广与计算重叠。读它看「pipeline overlap / 预取」在追求极致吞吐时的工业实现。
- **PyTorch, _torch.utils.data.DataLoader / DistributedSampler_（文档）** — 多进程加载、`num_workers` 预取、分布式下的 shard 分配（DistributedSampler）。模块 02 的分片分配与预取流水的最小现实对应，理解 worker/rank 怎么不重不漏地分数据。

## Tokenization 与序列打包 · Tokenization & Packing
- ★ **Sennrich, Haddow & Birch 2016, _Neural Machine Translation of Rare Words with Subword Units_** — BPE 用于 NLP 的奠基论文。理解分词的合并步骤为何偏串行、编码为何可并行，是模块 03 吞吐分析的算法背景。
- **Kudo & Richardson 2018, _SentencePiece_** — 工程化的、语言无关的分词库（BPE/unigram）。生产中大规模分词的常用实现，读它看真实分词器的接口与并行化方式。
- **Raffel et al. 2020, _Exploring the Limits of Transfer Learning (T5/C4)_** — 除了著名的 C4 过滤规则，T5 也是序列 packing 的早期大规模实践者（把多段拼进定长序列）。模块 03 的 packing 思想与 C4 启发式（模块 04 会再用）都源出于此。
- **Krell et al. 2021, _Efficient Sequence Packing without Cross-contamination_** — 专门研究 packing 时如何用注意力掩码避免跨文档污染、以及装箱策略对效率的影响。模块 03 的文档掩码与打包率分析的直接参考。
- **NVIDIA Megatron-LM / GPT-NeoX（代码与文档）** — 真实大规模训练框架里 tokenized 数据的 `.bin/.idx` mmap 格式、序列 packing、按 token 索引的实现。模块 03 的内存映射与 token 存储账的现实对应。

## 质量过滤 · Quality Filtering
- ★ **Penedo, Kydlíček, et al. 2024, _The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale_** — 本课工程实践的现实对标必读。公开 15T-token 语料的完整管线：URL 过滤、语言识别、Gopher/C4 启发式、去重、质量分类器，以及每步的消融与留存率。读它把模块 01/04 的小模拟接到真实 PB 级配方。
- ★ **Soldaini et al. 2024, _Dolma: an Open Corpus of Three Trillion Tokens..._** — 与 FineWeb 并列的必读。AI2 不仅放出 3T-token 语料，还开源了完整数据工具包（去重、过滤、去污染、PII、许可处理）与每步决策记录。是「数据工程全流程开源+可审计」的标杆，模块 04/05 的工程化全景以它为范本。
- **Rae et al. 2021, _Scaling Language Models (Gopher)_，附录 A（MassiveText 过滤）** — 经典的启发式质量过滤规则集（文档长度、符号比、重复比、停用词比等），被后续语料广泛沿用。模块 04 的启发式阶段直接对标这套规则。
- **Wenzek et al. 2020, _CCNet_** — 用 fastText 语言识别 + KenLM 困惑度过滤大规模处理 CommonCrawl 的早期范式。模块 04 的「语言识别 + perplexity 过滤」多阶段思想的现实来源。
- **Joulin et al. 2017, _fastText / Bag of Tricks_** — 轻量高效的文本分类（语言识别、质量分类常用）。模块 04 的分类器过滤阶段为何选「便宜的线性/浅层分类器」，答案在它的吞吐优势。

## 溯源、去污染与可复现 · Provenance, Decontamination & Reproducibility
- ★ **Brown et al. 2020, _Language Models are Few-Shot Learners (GPT-3)_，§污染分析** — 大规模 n-gram 重叠去污染的有影响力实践：用 13-gram 重叠从训练集里找出与各评测基准重叠的样本并分析其影响。模块 05 的 n-gram 去污染直接对标这套做法。
- ★ **Carlini, Ippolito, Jagielski, Lee, Tramèr & Zhang 2022/2023, _Quantifying Memorization Across Neural Language Models_ 及相关去污染工作** — 系统量化模型对训练数据的逐字记忆如何随规模、重复次数增长，给「为什么必须去重+去污染」提供硬证据，并讨论去污染的检测方法与陷阱（改写、近重复绕过）。模块 01/05 的动机与方法以它为准。
- **Dodge et al. 2021, _Documenting the English C4_** — 对 C4 语料做事后审计：它到底包含/排除了什么、有哪些来源与偏差、benchmark 污染情况如何。是「数据审计」该长什么样的范例，模块 05 审计报告的现实对照。
- **Gebru et al. 2018/2021, _Datasheets for Datasets_** — 提出给每个数据集配一份记录构成、来源、处理、已知偏差与适用范围的「数据表」。模块 05 的数据集卡片 / 审计报告的方法论来源，数据透明的实践基石。
- **Mitchell et al. 2019, _Model Cards_** — 数据/模型透明的姊妹实践，记录模型的预期用途与局限。与 datasheet 一起构成负责任发布的文档范式，审计章节的延伸阅读。
- **Pineau et al. 2021, _Improving Reproducibility in ML Research_** — 可复现性清单（数据、代码、随机种子、环境）。模块 05 的可复现快照、内容哈希、固定种子的工程纪律的总纲。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 PB 级集群**：全课用**小规模真实模拟 + 复杂度账 + 吞吐账**体现规模问题——用几千条文本跑通 MinHash+LSH 并与暴力 Jaccard **对拍到一致**，再用复杂度公式推演 1e12 文档下 O(n²) 为何不可行、分桶后为何可行；用 shuffle 缓冲模拟器量化打乱质量随缓冲大小的变化；用 Amdahl 定律给并行加速比设上限。每个机制都有 `assert` 兜底，保证你的工程逻辑**正确**且**可规模化推演**。
- **与 C21 的分工**：C21（大规模预训练）讲数据的**科学**——清洗判据、数据配比（DoReMi）、合成数据、tokenizer 训练对下游的影响；本课讲数据的**基础设施手艺**——同样是 MinHash/LSH/n-gram，C21 关心「该不该去重、阈值怎么影响模型」，本课关心「PB 规模下怎么把它工程化跑出来、复杂度/吞吐/正确性怎么保证」。两课配合读最完整。
- **课程衔接**：上游接 C14（深度学习理论与数据，讲数据管线与合成数据的理论）、C21（预训练数据科学）；下游接 C08（训练系统，数据管线喂给训练循环）、C37（MLOps，数据/管线的工程化运维）、C39（分布式训练，分片与数据并行的对齐）。
