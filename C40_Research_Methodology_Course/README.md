# 研究方法论与科学实践

整套课教的是「知识内容」（模型、算法、系统），唯独漏掉了「如何做研究本身」——本课补这块：读论文/复现、实验设计/消融、研究统计、研究工程卫生、科学写作/审稿，每条原则都配一个能跑、能 assert 的小实验。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 读论文与复现 | `01_reading_reproducing/` |
| 02 | 实验设计与消融纪律 | `02_experiment_design/` |
| 03 | 研究统计 | `03_statistics_for_research/` |
| 04 | 研究工程卫生 | `04_research_engineering/` |
| 05 | 科学写作与同行评审 | `05_writing_review/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先把研究方法的「为什么」想透，再跑 `NN_*.ipynb` 用 numpy/pandas 做一遍真实的方法论操作：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。复现一个数字、跑一个受控实验、算 bootstrap 置信区间、固定随机种子核验可复现、从结果生成诚实图表——你会亲眼看到「只跑一个种子」如何骗了你、「一次改两个量」如何让结论作废。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy/pandas、CPU 秒级，无需联网 / GPU / API key。`matplotlib` 用于画诚实图表（误差棒/基线/坐标轴），缺失则跳过画图、不影响任何 assert。

配套：[术语词典](glossary.md) · [参考清单](references.md)
