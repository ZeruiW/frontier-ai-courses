# 参考清单 · References（负责任 AI 与社会影响评测）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 numpy/pandas 从零实现的每个量，都能在下列文献里找到它的来源、争议与真实数据上的结果。

## 公平性定义与不可能定理 · Fairness Criteria & Impossibility
- ★ **Hardt, Price & Srebro 2016, _Equality of Opportunity in Supervised Learning_** (NeurIPS) — 提出 equalized odds 与 equal opportunity，并给出仅靠后处理(按组调阈值)满足它们的算法。本课模块 01 的 TPR/FPR 均等、阈值后处理直接源出于此，必读。
- ★ **Kleinberg, Mullainathan & Raghavan 2016, _Inherent Trade-Offs in the Fair Determination of Risk Scores_** — 证明在基率不同时，校准与「均等假阳/假阴率」一般不可兼得的不可能定理(连续分数版)。理解「公平为何必须取舍」的理论基石。
- ★ **Chouldechova 2017, _Fair Prediction with Disparate Impact_** — 从 COMPAS 出发证明：预测均等(PPV)与 FPR/FNR 均等在基率不同时不能同时满足(二元版不可能定理)。把抽象定理钉死在真实再犯预测争议上，极具说服力。
- **Dwork, Hardt, Pitassi, Reingold & Zemel 2012, _Fairness Through Awareness_** — 个体公平的奠基：相似个体应被相似对待，并指出「靠不看敏感属性求公平」(fairness through unawareness)会失败。理解群体公平之外的另一条路与其难点。
- **Barocas, Hardt & Narayanan, _Fairness and Machine Learning_ (fairmlbook.org)** — 公平机器学习的权威免费教材。把 separation/sufficiency/independence 三族定义、不可能性、因果视角讲透。本课术语与框架的主要对标，强烈建议通读前几章。
- **Verma & Rubin 2018, _Fairness Definitions Explained_** — 用一个贷款例子把二十余种公平定义逐个算一遍。当你被各种 parity 绕晕时，这篇是最好的速查与对照表。
- **Corbett-Davies & Goel 2018, _The Measure and Mismeasure of Fairness_** — 批判性梳理各公平定义的统计陷阱(如 infra-marginality)，主张回到决策理论。读它避免把某个公平指标当成万能。

## 毒性与内容审核偏差 · Toxicity & Content Moderation Bias
- ★ **Dixon, Li, Sorensen, Thain & Vasserman 2018, _Measuring and Mitigating Unintended Bias in Text Classification_** — 首次系统刻画毒性模型对身份词的意外偏差(提及 "gay" 即被判毒)，提出按身份词切分、用合成模板度量的方法。本课模块 02 的方法论核心，必读。
- ★ **Borkan, Dixon, Sorensen, Thain & Vasserman 2019, _Nuanced Metrics for Measuring Unintended Bias_** (Jigsaw) — 提出 Subgroup/BPSN/BNSP 三类 AUC，把「偏差」拆成可定位方向的细粒度指标，配套 Civil Comments 数据。模块 02 子群偏差度量的直接来源。
- **Gehman, Gururangan, Sap, Choi & Smith 2020, _RealToxicityPrompts_** — 证明即便给看似无害的提示，LM 也会续写出毒性内容，并提供大规模评测集。理解「生成式毒性」与「分类式毒性」评测的区别。
- **Sap, Card, Gabriel, Choi & Smith 2019, _The Risk of Racial Bias in Hate Speech Detection_** — 揭示毒性/仇恨言论标注本身带种族偏见(非裔英语方言更易被标毒)。提醒「真值」也不中立，是测量学层面的警钟。
- **Pozzobon, Ermis, Lewis & Hooker 2023, _On the Challenges of Using Black-Box APIs for Toxicity Evaluation_** — 指出 Perspective API 随时间漂移，使历史毒性评测不可复现。读它理解「把评测外包给会变的 API」的隐患。

## 多语言公平与分词 · Multilingual Fairness & Tokenization
- ★ **Ahia, Kumar, Gonen, Kasai, Mortensen, Smith & Tsvetkov 2023, _Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models_** — 量化 tokenizer fertility 跨语不均如何直接转成 API 费用与上下文长度的不公(某些语言贵数倍)。模块 03 「token 税」的核心证据，必读。
- ★ **Petrov, La Malfa, Torr & Bibi 2023, _Language Model Tokenizers Introduce Unfairness Between Languages_** (NeurIPS) — 系统测量数十种语言的 token 膨胀，证明这种不公是 tokenizer 固有的、并随之带来延迟与成本歧视。与 Ahia 互补，模块 03 必读。
- **NLLB Team (Meta) 2022, _No Language Left Behind_ + FLORES-200** — 200 语言平行翻译基准与模型。是跨语言性能可比评测的事实标准，模块 03 翻译质量与最差组分析的现实数据基础。
- **Joshi, Santy, Budhiraja, Bali & Choudhury 2020, _The State and Fate of Linguistic Diversity_** — 提出语言资源分层(0–5 类)，论证 NLP 研究高度集中于少数语言。理解「低资源」不是个别现象而是结构性失衡。
- **Blasi, Anastasopoulos & Neubig 2022, _Systematic Inequalities in Language Technology Performance_** — 跨任务量化语言技术效用的全球不均，并与使用人口对照。把多语公平放到全球社会影响尺度。

## 记忆化、提取与成员推断 · Memorization, Extraction & MIA
- ★ **Carlini, Tramèr, Wallace, ... Raffel 2021, _Extracting Training Data from Large Language Models_** — 证明可从 GPT-2 提取出逐字训练数据(含 PII)，提出 k-eidetic 记忆定义。开创 LLM 记忆/隐私攻击领域，模块 04 提取攻击的奠基，必读。
- ★ **Carlini, Liu, Erlingsson, Kos & Song 2019, _The Secret Sharer_** — 提出 canary 与 exposure 指标，给出无关分布的可测量记忆探针。本课模块 04 的 canary 暴露度实现直接照它，必读。
- ★ **Shokri, Stronati, Song & Shmatikov 2017, _Membership Inference Attacks Against Machine Learning Models_** — MIA 的开山之作，提出影子模型框架。理解「模型是否泄露了谁在训练集」这一隐私基本威胁，模块 04 必读。
- ★ **Carlini, Chien, Nasr, Song, Terzis & Tramèr 2022, _Membership Inference Attacks From First Principles_ (LiRA)** — 指出旧 MIA 评测用平均指标掩盖真实风险，应看低 FPR 区的 TPR；提出强似然比攻击 LiRA。重塑了 MIA 评测标准，必读。
- **Carlini, Ippolito, Jagielski, Lee, Tramèr & Zhang 2022, _Quantifying Memorization Across Neural Language Models_** — 量化记忆随模型规模、数据重复次数、上下文长度单调上升的规律。模块 04 「去重为何有效」的实证依据。
- **Lee, Ippolito, ... Carlini 2022, _Deduplicating Training Data Makes Language Models Better_** — 证明训练数据去重既提性能又大幅降记忆/提取风险。模块 04 去重缓解练习的来源。
- **Nasr, Carlini, ... 2023, _Scalable Extraction of Training Data from (Production) Language Models_** — 用「发散攻击」从对齐后的生产模型(含 ChatGPT)提取训练数据，破除「对齐=安全」的错觉。读它了解记忆风险在前沿模型上依然存在。

## 危害分类、红队与社会影响 · Taxonomy, Red-Teaming & Societal Impact
- ★ **Weidinger, Mellor, ... Gabriel 2021, _Ethical and Social Risks of Harm from Language Models_** (DeepMind) — 提出语言模型危害的六大类分类学。是把危害「列全、不漏项」的标准骨架，本课模块 05 的核心框架，必读。
- ★ **Weidinger, Uesato, ... 2022, _Taxonomy of Risks posed by Language Models_** (FAccT) — 上文的精炼与操作化版本。读它把六类危害落到可评测的条目。
- ★ **Parrish, Chen, Nangia, ... Bowman 2022, _BBQ: A Hand-Built Bias Benchmark for Question Answering_** — 手工构造的问答偏见基准，在「信息不足」与「信息充分」两种语境下测模型是否落入社会刻板印象。模块 01/05 的真实偏见数据来源，必读。
- **Ganguli, Lovitt, ... (Anthropic) 2022, _Red Teaming Language Models to Reduce Harms_** — 大规模人类红队的方法、发现与数据。理解红队怎么做、覆盖了哪些危害、如何量化，模块 05 红队覆盖度的现实参照。
- **Perez, Huang, ... (DeepMind) 2022, _Red Teaming Language Models with Language Models_** — 用 LM 自动生成对抗测试用例。是把红队规模化、提升覆盖度的代表性工作。
- **Bender, Gebru, McMillan-Major & Shmitchell 2021, _On the Dangers of Stochastic Parrots_** — 系统论证大模型的环境、财务、偏见与表征危害。Weidinger 分类学中多个类别的思想前身，建立社会影响的批判视角。
- **Blodgett, Barocas, Daumé III & Wallach 2020, _Language (Technology) is Power: A Survey of "Bias" in NLP_** — 梳理 NLP「偏见」研究的概念混乱，呼吁明确「对谁、何种伤害」。读它把模糊的「有偏见」翻译成可测量的具体危害(分配性/表征性)。
- **Weidinger, Rauh, ... 2023, _Sociotechnical Safety Evaluation of Generative AI Systems_** — 主张评测须覆盖能力层、人机交互层、系统性影响层三层。本课「评测要超越孤立基准」总立场的来源。

## 度量方法与统计 · Measurement & Statistics
- **Mitchell, Wu, ... Gebru 2019, _Model Cards for Model Reporting_** — 提出按子群分项报告模型表现的「模型卡」。本课 slice-based 评测、分子群报指标的工程实践来源。
- **Gebru, Morgenstern, ... Crawford 2018, _Datasheets for Datasets_** — 为数据集建立「成分与局限」文档规范。提醒评测前先问清数据从哪来、谁被代表/缺席，是负责任评测的上游。
- **Efron & Tibshirani 1993, _An Introduction to the Bootstrap_** — bootstrap 置信区间的经典出处。子群样本少时，本课所有「这个差距是真的还是噪声」都靠它回答。
- ⚠️ **本课定位**：全程用 **numpy/pandas 在 CPU 上从零实现** 上述每个量(公平指标、子群 FPR、fertility、canary exposure、MIA ROC、风险矩阵)，玩具规模、追求看懂机制。真实数据(Civil Comments、BBQ、FLORES 等)通过 **联网下载 + 失败回退到内置真实数值/合成** 接入；合成数据的统计结构(基率差、身份词伪相关、fertility 比、成员/非成员损失分布)都按文献真实现象设定，使结论方向与真实一致。
