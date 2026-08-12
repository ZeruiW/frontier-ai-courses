# 前沿对齐：CAI · RLAIF · 可扩展监督 · 前沿 AI 系统培训

> 一条主线贯穿全课：**当任务强到人类难以监督时，对齐信号从哪来？** 中文讲解 + 英文术语；纯 numpy/CPU 用玩具模型 + 合成偏好**模拟**前沿对齐方法的逻辑结构，每个机制都用 `assert` 兜住正确性。无需 GPU / 联网 / 大模型。

## 怎么用
每个模块先读 **HTML 讲解**（深度讲动机→直觉→数学→实现→陷阱→前沿），再跑 **notebook**（5–6 个 worked 小节 `print`+`assert` → 3–4 道 ✏️ 练习 `TODO`+自测 → 📖 参考答案 → 🧪 真实数据/配置胶囊）。配 [`glossary.md`](glossary.md) 与 [`references.md`](references.md)。

## 模块
| # | 模块 | 一句话 | Notebook |
|---|------|--------|----------|
| 00 | [课程总览与对齐地图](00_setup/) | RLHF 三道裂缝 → 五模块主线 + 沙盒方法论 | `00_environment_check.ipynb` |
| 01 | [Constitutional AI 与 RLAIF](01_constitutional_ai/) | 人写宪法、AI 自我批判-修订(SL) + AI 标偏好(RLAIF) | `01_constitutional_ai.ipynb` |
| 02 | [奖励建模与过优化](02_reward_modeling/) | Bradley-Terry RM、倒 U 过优化(Goodhart)、KL、集成抗 hacking | `02_reward_modeling.ipynb` |
| 03 | [可扩展监督与辩论](03_scalable_oversight/) | debate、RRM/IDA、sandwiching、self-critique | `03_scalable_oversight.ipynb` |
| 04 | [Weak-to-Strong 泛化](04_weak_to_strong/) | 弱标签训强学生超过老师、PGR、辅助置信损失 | `04_weak_to_strong.ipynb` |
| 05 | [Deliberative Alignment 与规范遵循](05_deliberative/) | 回答前显式推理明文 spec、拒绝校准、抗越狱、一致性 | `05_deliberative.ipynb` |

```bash
pip install -r requirements.txt && jupyter lab
```

## 立场
本课讲前沿实验室真正在用的对齐技术（Anthropic CAI/RLAIF、贯穿 RLHF 的奖励建模、OpenAI/Anthropic 的可扩展监督、OpenAI superalignment 的 weak-to-strong、OpenAI 的 deliberative alignment）。用纯 numpy 在 CPU 上用玩具模型把每个方法的**逻辑骨架与权衡**从零实现、用 `assert` 验证正确——把注意力集中在「为何有效、在哪失效」，而非工程噪声。真实系统的对应做法见 [`references.md`](references.md)。
