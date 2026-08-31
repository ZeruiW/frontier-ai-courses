# 参考清单 · RAG 生产工程

> ★ = 必读。本课不重复 C11 的检索算法文献（HNSW / PQ / ColBERT / RAGAS 等在 C11 的清单里）。
> 每条写明「它解决什么问题」以及「本课在哪里用到它」。

---

## 一 · RAG 的起点与全局

- ★ **Patrick Lewis, Ethan Perez, Aleksandra Piktus, et al.,
  _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_（NeurIPS 2020）** —
  解决「参数化知识不够用时怎么外挂检索」。
  它定义了本课讨论的那条流水线。
  **本课模块 00 的五格图就是这篇的工程展开**，但本课的关注点在它左右两侧的四格。
- **Simon Willison 关于 RAG 工程实践的系列文章** —
  解决「为什么 demo 能跑而生产不行」。
  其中「RAG 的难点几乎都不在向量检索上」这个判断与本课的出发点一致。

---

## 二 · 文档解析与版面理解（模块 01）

- ★ **`unstructured` 的 element 模型与 `pypdf` / `pdfplumber` 的坐标 API（软件文档）** —
  解决「怎么在拿到文字的同时拿到结构与位置」。
  关键是 `Title / NarrativeText / Table / ListItem` 这套 element 类型与 `coordinates`、
  `page_number`、`category_depth`。
  **本课模块 01 第 1 节「解析要同时拿到三样东西」直接对应这套模型**，
  而 `text_as_html` 是行转句的输入。
- **Lukas Blecher, Guillem Cucurull, Thomas Scialom, Robert Stojnic,
  _Nougat: Neural Optical Understanding for Academic Documents_（2023）** —
  解决「扫描版学术文档怎么恢复公式与表格结构」。
  本课不用神经解析，但它的问题设定说明了**为什么结构损失是不可逆的**：
  需要一个专门训练的模型才能部分恢复。
- **Yiheng Xu, Minghao Li, Lei Cui, et al., _LayoutLM_ 系列（KDD 2020 起）** —
  解决「版面信息怎么进模型」。
  同上：它的存在本身说明版面是一种独立的信息，而 `extract_text` 把它投影掉了。
- **XY-cut 版面分割（Nagy 等人 1980s 起的经典方法）** —
  解决「怎么从带坐标的块恢复阅读顺序并得到一棵版面树」。
  **本课模块 01 第 3 节的分栏判定用的是它的简化版**（x 直方图双峰 + 栏内按 y 排）。
- **Andrei Broder, _On the Resemblance and Containment of Documents_（1997）** —
  解决「怎么在大规模语料上判近重复」。
  MinHash 的原始文献；**算法本身在 C43，本课只用它的结论**，
  并讨论 RAG 里的特有后果：近重复占满 top-k。

---

## 三 · 分块（模块 02）

- ★ **`langchain-text-splitters` 的 `RecursiveCharacterTextSplitter`
  与 LlamaIndex 的 `SentenceWindowNodeParser` / `AutoMergingRetriever`（软件文档）** —
  解决「怎么让切点落在语义边界上」以及「怎么把检索粒度与上下文粒度解耦」。
  分隔符优先级列表（`\n## ` → `\n\n` → `\n` → `。` → ``）与父子块是这两个库的核心设计。
  **本课模块 02 第 4/6 节实现了它们的最小版本，并补上两个必做细节**
  （父块去重、归因指向子块）。
- **Greg Kamradt, _5 Levels of Text Splitting_（2023，教程）** —
  解决「分块方案有哪几档、各自的成本」。
  语义分块（相邻句相似度谷点切分）的流行实现来自这里。
  **本课模块 02 第 5 节量出了它的两个退化情形**（分位数阈值在
  「相似度大量为 0」与「相似度全相等」时失效），
  并给出绝对阈值 + 双向硬约束的修法——
  *这一点在原教程里没有讨论。*
- **Nelson F. Liu, Kevin Lin, John Hewitt, et al.,
  _Lost in the Middle: How Language Models Use Long Contexts_（TACL 2024）** —
  解决「上下文里的位置会不会影响利用率」。
  **本课不重复它（C11 模块 06 有）**，但它是「父子块把上下文变长」这个代价的一部分：
  更长的上下文不只更贵，中间位置的利用率也更低。

---

## 四 · 查询侧（模块 03）

- ★ **Luyu Gao, Xueguang Ma, Jimmy Lin, Jamie Callan,
  _Precise Zero-Shot Dense Retrieval without Relevance Labels_（HyDE, ACL 2023）** —
  解决「问句与文档的分布不匹配怎么办」。
  做法是让模型先生成一个假设性文档再用它检索。
  **本课模块 03 第 3 节的实验正是它的机制说明**：
  伪答案不需要正确，只需要在正确的文体与词汇分布里——
  本课量到「连数字写错的伪答案也一样有效」。
- ★ **Gordon V. Cormack, Charles L. A. Clarke, Stefan Buettcher,
  _Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods_（SIGIR 2009）** —
  解决「多路排序怎么合并而不需要对齐分数尺度」。
  $\text{RRF}(d) = \sum_i 1/(k_0 + \text{rank}_i(d))$，$k_0$ 常取 60。
  **本课模块 03 第 4 节直接用它**（定义在 C11 模块 03），
  重点是量出「它降的是方差不是均值」。
- **Xinbei Ma, Yeyun Gong, Pengcheng He, Hai Zhao, Nan Duan,
  _Query Rewriting for Retrieval-Augmented Large Language Models_（EMNLP 2023）** —
  解决「查询该由谁改写、怎么训」。
  **本课只用它的结论（改写有收益、且不能替换原查询）**，不训练改写器。
- **Ori Ram, Yoav Levine, Itay Dalmedigos, et al.,
  _In-Context Retrieval-Augmented Language Models_（TACL 2023）** —
  解决「检索该多频繁、该不该检索」。
  它对「不是所有生成步骤都需要检索」的讨论是本课路由一节的背景。

---

## 五 · 迭代与图检索（模块 04）

- ★ **Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, Ashish Sabharwal,
  _Interleaving Retrieval with Chain-of-Thought Reasoning for
  Knowledge-Intensive Multi-Step Questions_（IRCoT, ACL 2023）** —
  解决「多跳问题怎么把检索与推理交错起来」。
  **本课模块 04 第 2 节的 `next_query` 结构来自这条线**，
  而「锚定原问题的目标谓词」是本课对漂移问题的补充。
- ★ **Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi,
  _Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection_（ICLR 2024）** —
  解决「模型能不能自己决定何时检索、检索到的有没有用」。
  **本课模块 04 第 3 节的停止准则是它的规则化替身**；
  本课强调的一点是：*停止判断只能看结构性信号，不能看答案对不对——线上没有真值*。
- **Zhengbao Jiang, Frank F. Xu, Luyu Gao, et al.,
  _Active Retrieval Augmented Generation_（FLARE, EMNLP 2023）** —
  解决「什么时候触发下一次检索」（按生成中的低置信 token 触发）。
  与 Self-RAG 一起构成「自适应检索」这条线。
- **Darren Edge, Ha Trinh, Newman Cheng, et al.,
  _From Local to Global: A Graph RAG Approach to Query-Focused Summarization_（2024）** —
  解决「关系类与全局摘要类问题怎么答」（实体图 + 社区检测 + 分层摘要）。
  **本课模块 04 第 5 节只实现最便宜的一档（实体→块倒排）**，
  并指出图检索的两个真实风险：三元组抽取的召回率决定上限，以及**图会腐烂**。
- **Mark Chen, Jerry Tworek, Heewoo Jun, et al., _Evaluating Large Language Models
  Trained on Code_（2021）** —
  pass@k 的无偏估计量出自这里。
  **本课模块 04 第 8 节的 fact-recall 借用了「全或无」这个思路**，
  但它是一个确定性量，不需要无偏估计。

---

## 六 · 索引运维（模块 05）

- ★ **Martin Kleppmann, _Designing Data-Intensive Applications_（O'Reilly 2017，
  第 4 章「Encoding and Evolution」与第 11 章「Stream Processing」）** —
  解决「双写、原子切换、变更数据捕获该怎么做」。
  **本课模块 05 第 5 节的影子索引 + 双写 + 原子切换是这套模式在向量索引上的直接应用**；
  「中途状态必须不可达」也来自这里。
- ★ **向量库的 collection alias / 别名机制
  （Chroma、Qdrant、Milvus、Elasticsearch 的软件文档）** —
  解决「怎么把索引切换做成一次配置变更而不是一次数据迁移」。
  **本课模块 05 第 5 节的 `Router` 就是它的最小模型**，
  重点是那条容易违反的要求：*读取方每次请求重新读那个指针，不要在进程启动时缓存*。
- **Google, _Site Reliability Engineering_（第 4 章「SLO」）** —
  解决「新鲜度该怎么定成一个可执行的目标」。
  **本课模块 05 第 3 节把「重建周期」从拍脑袋变成从 $p$ 与目标过期率反解**，
  而 SLA 要报最坏滞后、估过期率要用平均滞后——混用这两个数是一个常见错误。
- **Gebru, Morgenstern, Vecchione, et al., _Datasheets for Datasets_（2018 / CACM 2021）** —
  解决「一份数据集该附带哪些信息」。
  **本课模块 05 第 8 节的「索引运维卡」是它在索引侧的对应物**，
  而其中最重要的一行是回滚指针。
- **GDPR 第 17 条「被遗忘权」及相关合规讨论** —
  解决「删除意味着什么」。
  **本课模块 05 第 2 节「删除的三层」（索引 / 派生资产 / 日志）与
  「删除必须可验证」是这条要求的工程落地**；
  隐私技术本身（DP、机器遗忘）在 C45。

---

## 七 · 本课程内部的依赖

| 课程模块 | 本课在哪里用到 |
|---|---|
| **C11 全课** | 检索算法与检索/RAG 指标。本课复用它的全部指标定义，一个都不重新定义 |
| **C33 模块 01/02/05** | 本课到「组装上下文」为止；预算分配、compaction、prompt 缓存交给 C33 |
| **C43** | 模块 01 的去重算法（MinHash / SimHash） |
| **C46** | 模块 04 若要把实体倒排升级成图神经网络，从这里接 |
| **C66 模块 05** | `$/success` 这个成本口径；模块 04 第 6 节直接用 |
| **C68 模块 01** | 版本语义、稳定 ID、交集重算；本课模块 01/05 全程遵循 |
| **C68 模块 02** | 缓存键必须含完整指纹；本课模块 03 第 7 节是它在查询侧的对应物 |
| **C68 模块 04** | 门禁分级（确定性阻断 / 统计报警）与阈值从方差推；本课五个模块的门禁都按这条做 |
| **C68 模块 05** | PSI/KS、漂移、数据闭环；本课模块 05 第 8 节只补检索层特有的四个指标 |
| **C69 模块 01** | 摄取边界与不可信内容；本课模块 01 提醒「不要在摄取时用 LLM 清洗全文」 |
| **C12 / C45** | 模块 05 删除要求的合规背景 |
