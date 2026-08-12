# 大规模数据工程

C21 讲数据的「科学」（保留什么、怎么配比、合成数据怎么造），本课补数据的「基础设施手艺」：去重、流式加载、分词吞吐、质量过滤、溯源去污染——用小规模真实模拟 + 复杂度/吞吐账，把「PB 级会怎样」从纸面推到可验证的数字。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 大规模去重 | `01_dedup_scale/` |
| 02 | 流式加载与分片 | `02_streaming_loaders/` |
| 03 | Tokenization 吞吐 | `03_tokenization_throughput/` |
| 04 | 大规模质量过滤 | `04_quality_filtering/` |
| 05 | 溯源与去污染 | `05_provenance_decontam/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立「规模带来质变」的工程直觉，再跑 `NN_*.ipynb` 用 numpy/pandas/标准库 在小规模真实数据上复现工程机制：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。比如用几千条文本跑通 MinHash+LSH 去重管线、与暴力 Jaccard 对拍，再用复杂度公式推演它在 1e12 文档上为什么 O(n²) 不可行、分桶后为什么可行——每个机制都算一笔复杂度账与吞吐账。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy/pandas + 标准库、CPU 可跑，本环境无需 PB 级集群 / GPU / 联网 / API key——用小规模真实模拟 + 复杂度/吞吐账体现规模问题。

配套：[术语词典](glossary.md) · [参考清单](references.md)
