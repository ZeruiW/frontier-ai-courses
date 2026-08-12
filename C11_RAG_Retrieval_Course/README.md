# 检索增强与长上下文评测 · 研究科学家级系统培训

> **不止会调 RAG，而是会从零搭一条「嵌入 → 检索 → 重排 → 生成 → 评测」的全栈，并量化每一环。**
> 讲解中文 + 英文术语，以真实可运行 Jupyter notebook 为主线，每本含 5–6 个 worked 小节 + 3–4 道 ✏️ 练习（TODO 骨架 + assert 自动判分）+ 📖 参考答案 + 🧪 真实数据胶囊。
> **纯 numpy / pandas · CPU 可跑** —— 不训练神经网络、不调用线上大模型；嵌入用确定性玩具向量，真实数据（SQuAD 等）联网下载、失败回退内置真实样本。

## 🗺️ 模块

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [嵌入与语义搜索](01_embeddings_semantic_search/) | `01_embeddings_semantic_search.ipynb` | CPU |
| 02 | [向量检索](02_vector_retrieval/) | `02_vector_retrieval.ipynb` | CPU |
| 03 | [重排](03_reranking/) | `03_reranking.ipynb` | CPU |
| 04 | [RAG 评测](04_rag_evaluation/) | `04_rag_evaluation.ipynb` | CPU |
| 05 | [检索指标](05_retrieval_metrics/) | `05_retrieval_metrics.ipynb` | CPU |
| 06 | [长上下文评测](06_long_context_eval/) | `06_long_context_eval.ipynb` | CPU |

> 也可以直接打开 [`index.html`](index.html) 浏览。

## 你将从零实现
- **嵌入与相似度**：点积/余弦/L2 归一化、玩具 embedding、词法王者 BM25、语义 vs 词法、混合检索（分数加权 / RRF）
- **向量检索**：暴力 kNN、IVF 倒排分桶、HNSW 图导航、PQ 乘积量化、IVF-PQ，以及召回-延迟-内存的不可能三角
- **重排**：bi- vs cross-encoder、两段式检索、MMR 多样性去冗余、RRF 多路融合
- **RAG 评测**：faithfulness/groundedness、answer relevance、context precision/recall、RAGAS 思想、幻觉检测
- **检索指标**：Precision@k / Recall@k / MRR / MAP / nDCG，二元 vs 分级相关性
- **长上下文评测**：NIAH 大海捞针、lost-in-the-middle 位置偏置、多针/多跳、RAG vs 长上下文权衡

## 🚀 快速开始
```bash
pip install -r requirements.txt && jupyter lab
```

## 📚 配套
- [`glossary.md`](glossary.md) 术语词典（按主题分组，英文术语保留）· [`references.md`](references.md) 论文清单（★ 标必读）

*中文讲解，英文术语，真实数据，纯 numpy/pandas，CPU 可跑。*
