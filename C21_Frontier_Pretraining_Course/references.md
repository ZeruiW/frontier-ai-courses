# 参考清单 · References（大规模预训练工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy 复现的每个机制，都能在下列文献里找到真实万亿 token 管线上的对应做法与权衡。

## 数据清洗、去重与去污染 · Data Curation, Dedup & Decontamination
- ★ **Penedo et al. 2024, _The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale_** — 当前最透明的开源数据管线。它把「正文抽取 → 启发式过滤 → MinHash 去重 → 质量分类 → 去污染」每一步都做了 FLOPs-matched 消融，量化各步对下游的净贡献，并发布 15T token 语料与 FineWeb-Edu。**本课模块 01 的主线参考**，回答「数据清洗到底值多少」。
- ★ **Lee et al. 2021, _Deduplicating Training Data Makes Language Models Better_** — 证明去重的价值：近重复去除后，模型记忆显著下降、达到同样 loss 所需步数减少、下游略升。给出 ExactSubstr 与 MinHash 两套去重方法。**模块 01 去重一节的奠基文献**，解决「为什么必须去重」。
- ★ **Penedo et al. 2023, _The RefinedWeb Dataset for Falcon LLM_** — 论证「只用精心清洗的网页」即可媲美掺书籍/代码的精选语料，扭转「网页低质」成见，奠定了 FineWeb 路线。读它理解清洗（而非来源）才是质量的关键。
- **Rae et al. 2021, _Scaling Language Models: Methods, Analysis & Insights from Training Gopher_** — 提出被广泛沿用的 MassiveText/Gopher 启发式过滤规则集（停用词、符号比、重复比等）。模块 01 启发式过滤的规则来源。
- **Wenzek et al. 2019, _CCNet: Extracting High Quality Monolingual Datasets from Web Crawl Data_** — 用 KenLM 困惑度过滤 + 语言识别从 CommonCrawl 提多语语料的经典管线。perplexity filter 的代表作。
- **Raffel et al. 2020, _Exploring the Limits of Transfer Learning (T5 / C4)_** — C4 语料的清洗规则（去 javascript 行、去占位符、按句去重等）是后续所有网页清洗的范本之一。
- **Broder 1997, _On the Resemblance and Containment of Documents_** — MinHash 的原始论文，证明「最小哈希相等的概率 = Jaccard 相似度」。**模块 01 MinHash 数学的根源**，解决「如何用短签名无偏估计集合相似度」。
- **Leskovec, Rajaraman & Ullman, _Mining of Massive Datasets_ (MMDS), 第 3 章** — LSH / banding / S 曲线的标准教科书推导。模块 01 的 LSH 分桶与 (b,r) 调参完全对标它，强烈建议精读。
- **Carlini et al. 2022, _Quantifying Memorization Across Neural Language Models_** — 量化「重复次数 → 被逐字记忆的概率」，给去重提供了隐私/版权层面的硬证据。
- **Brown et al. 2020, _Language Models are Few-Shot Learners (GPT-3)_** — 附录详述了用分类器做质量过滤 + 模糊去重 + n-gram 去污染的工程细节，是早期完整数据管线披露的范例。

## Tokenization · 分词
- ★ **Sennrich, Haddow & Birch 2016, _Neural Machine Translation of Rare Words with Subword Units_** — 把 BPE 引入 NLP 的论文，用「反复合并最高频相邻对」解决未登录词与大词表问题。**模块 02 BPE 的奠基**，解决「如何在固定词表下覆盖任意词」。
- ★ **Kudo 2018, _Subword Regularization: Improving NMT Models with Multiple Subword Candidates_（Unigram LM）** — 提出 Unigram 语言模型分词：从大词表用 EM 反向剪枝，分词时取最大似然切分并能采样多种切分。**模块 02 Unigram 一节的主参考**，与 BPE 形成对比。
- ★ **Kudo & Richardson 2018, _SentencePiece: A Simple and Language Independent Subword Tokenizer_** — 把 BPE 与 Unigram 统一进一个语言无关、可逆的工具（空格当符号处理）。多语模型的事实标准，模块 02 的工程对应。
- **Schuster & Nakajima 2012 / Wu et al. 2016 (WordPiece, GNMT)** — WordPiece 的来源：合并准则用「似然增益」而非纯频率。BERT 沿用。模块 02 三法对比中的一极。
- **Gage 1994, _A New Algorithm for Data Compression_** — BPE 最初的数据压缩算法原型，理解 BPE「合并最频繁对」思想的源头。
- **Rust et al. 2021, _How Good is Your Tokenizer? On the Monolingual Performance of Multilingual Language Models_** — 量化 tokenizer 对非英语语言的 fertility 惩罚与下游影响。**模块 02 fertility/多语权衡一节的实证支撑**，解决「为什么 tokenizer 对小语种不公平」。
- **Petrov et al. 2023, _Language Model Tokenizers Introduce Unfairness Between Languages_** — 进一步揭示同一段语义在不同语言上 token 数差几倍，带来成本与 context 的不公平。

## 缩放定律与超参迁移 · Scaling Laws & HP Transfer
- ★ **Hoffmann et al. 2022, _Training Compute-Optimal Large Language Models (Chinchilla)_** — 重新拟合缩放定律，发现给定算力应让参数量与 token 数等比放大（约 20:1），此前大模型严重训练不足。**改写预训练资源分配的必读**，解决「固定算力下 N 和 D 怎么分」。
- ★ **Kaplan et al. 2020, _Scaling Laws for Neural Language Models_** — 最早系统刻画 loss 随 N/D/C 的幂律。虽被 Chinchilla 修正了 N:D 比例，但其方法论（用小规模拟合外推）是 scaling law 实践的起点。
- ★ **Yang et al. 2021, _Tuning Large Neural Networks via Zero-Shot Hyperparameter Transfer (μP / μTransfer)_** — 提出 maximal update parametrization：让激活/更新尺度不随宽度漂移，从而把小模型调好的超参零样本迁到大模型。**模块 03 的核心论文**，解决「如何不在大模型上调参」。
- ★ **Yang & Hu 2020+, _Tensor Programs IV/V_（Feature Learning in Infinite-Width NNs）** — μP 的理论根基，用张量程序刻画无限宽网络。读它理解「超参为何能跨宽度迁移」的数学，而非只会套缩放公式。
- **Yang et al. 2023, _Tensor Programs VI: Feature Learning in Infinite-Depth NNs (Depth-μP)_** — 把 μP 从「随宽度」推广到「随深度」，是深层模型超参迁移的前沿。
- **Hägele et al. 2024, _Scaling Laws and Compute-Optimal Training Beyond Fixed Durations (WSD)_** — 研究 Warmup-Stable-Decay 调度与可延长训练，连接 scaling law 与学习率调度。模块 04/05 的延伸。
- **Bi et al. 2024, _DeepSeek LLM: Scaling Open-Source LMs with Longtermism_** — 给出在自己数据/tokenizer 上重新拟合 scaling law 与超参 scaling 的工程细节，是「自己跑 scaling law」的实操样本。

## 训练稳定性 · Training Stability
- ★ **Chowdhery et al. 2022, _PaLM: Scaling Language Modeling with Pathways_** — 详述 540B 训练遇到的 loss spike 及对策：发现 spike 与特定数据 batch + 优化器状态相关，用「回滚到 spike 前 + 跳过问题数据」处理，并采用 z-loss 稳定 logit。**模块 04 稳定性的主参考**，解决「真实大训练怎么对付 spike」。
- ★ **Zhang et al. 2022, _OPT: Open Pre-trained Transformer Language Models（及其训练日志 logbook）_** — 罕见地公开了 175B 训练的真实日志：硬件故障、loss 发散、手动调 lr、换优化器的全过程。读它对「大训练有多脆弱」建立现实感。
- **Dehghani et al. 2023, _Scaling Vision Transformers to 22 Billion Parameters_** — 提出并验证 QK-norm（对 query/key 归一化）显著改善大模型注意力稳定性。模块 04 QK-norm 一节的来源。
- **Wortsman et al. 2023, _Small-scale Proxies for Large-scale Transformer Training Instabilities_** — 在小模型上复现大模型的不稳定（如 attention logit 增长、output logit 发散），并测试 z-loss、QK-norm、warmup 等修法的效果。**模块 04 方法论的直接对应**：用小代理研究稳定性。
- **Takase et al. 2023, _Spike No More: Stabilizing the Pre-training of LLMs_** — 从初始化与梯度尺度角度分析 spike 成因，给出缩小 embedding/初始化的稳定方案。
- **Nguyen & Salazar 2019 / Xiong et al. 2020, _On Layer Normalization in the Transformer (Pre-LN vs Post-LN)_** — 解释 Pre-LN 为何比 Post-LN 训练稳定（无需 warmup 也不易发散），是稳定性背后的结构性原因。

## 数据配比、重复与合成数据 · Mixtures, Repetition & Synthetic Data
- ★ **Xie et al. 2023, _DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining_** — 用小 proxy 模型 + group DRO 自动找域权重，让最差 domain 也学好，再迁到大模型；无需下游标签即可优化配比并加速训练。**模块 05 配比优化的核心论文**，解决「域权重怎么自动定」。
- ★ **Muennighoff et al. 2023, _Scaling Data-Constrained Language Models_** — 系统研究「数据不够、必须重复 epoch」时缩放定律如何修正：约 4 个 epoch 内重复 ≈ 新数据，之后收益迅速衰减；并比较重复 vs 加参数 vs 加代码数据。**模块 05 重复收益与数据墙一节的奠基**。
- ★ **Shumailov et al. 2023/2024, _The Curse of Recursion / AI models collapse when trained on recursively generated data_** — 揭示「用模型生成数据反复训后续模型」导致分布尾部丢失、多样性塌缩的 model collapse。**模块 05 合成数据风险的必读**，解决「合成数据能不能无限用」。
- **Albalak et al. 2024, _A Survey on Data Selection for Language Models_** — 把数据过滤、去重、配比、课程统一成「数据选择」框架的综述。建立模块 01+05 全局视野的好入口。
- **Xie et al. 2023, _Data Selection for Language Models via Importance Resampling (DSIR)_** — 用重要性重采样让训练分布逼近目标（如高质量）分布，是配比/选择的另一条技术路线。
- **Gunasekar et al. 2023, _Textbooks Are All You Need (phi)_** — 用高质量「教科书式」与合成数据训小模型却获得强能力，是合成/高质量数据价值的标志性证据（与 model collapse 的风险互为两面）。
- **Sorscher et al. 2022, _Beyond neural scaling laws: beating power law scaling via data pruning_** — 论证用更好的数据剪枝可以突破幂律 scaling，把「数据质量 > 数据数量」量化，连接模块 01 与 05。

## 综合管线与工程实践 · End-to-End Pipelines
- ★ **Touvron et al. 2023, _LLaMA / Llama 2_** — 公开了一个有竞争力的开源基座的完整数据配方（各 domain 比例）、tokenizer（BPE/SentencePiece）、训练超参与稳定性设置。**把本课五个模块串起来看的最佳整体样本**。
- **Groeneveld et al. 2024, _OLMo: Accelerating the Science of Language Models_（及 Dolma 数据集）** — 开放权重 + 开放数据 + 开放训练代码的「全开源」基座，Dolma 论文详述数据管线。想复现整条流水线的人首选。
- **Workshop et al. 2022, _BLOOM: A 176B-Parameter Open-Access Multilingual LM_（ROOTS 语料）** — 多语预训练的数据治理与 tokenizer 选择范例，模块 02 多语权衡的现实背景。
- **Biderman et al. 2023, _Pythia: A Suite for Analyzing LLMs Across Training and Scaling_** — 提供同一数据、不同规模、带 checkpoint 的模型套件，是研究数据/稳定性/缩放的公共实验台。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境纯 CPU、不训真模型**：全课用 numpy 在玩具规模（小词表、小维度、几百条样本）**从零复现**每个机制——MinHash 估 Jaccard、LSH banding、从零训 BPE merges、μP 坐标检查、loss spike 检测与修复、DoReMi 式配比优化。每个算法都与朴素参考**对拍**、用 `assert` 兜底正确性。
- **可迁移性**：你在 numpy 里验证过的 MinHash/LSH 逻辑、BPE merge 顺序、μP 缩放规则、配比优化迭代，结构上与 datatrove/SentencePiece/mup 等真实库一致，只差规模与并行。
- **课程衔接**：上游接 C01（Transformer 架构）、C14（深度学习理论与数据）；与 C36（GPU 内核）/ C39（分布式训练）互补（它们管「算得快」，本课管「数据对、超参对、不崩」）；下游接 C02（后训练/对齐）——预训练给的是基座，后训练在其上雕刻行为。
