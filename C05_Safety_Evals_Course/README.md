# 前沿模型安全评估与红队 · 研究科学家级系统培训

> 一套面向 **AI safety 研究科学家**（METR / frontier lab safety 团队方向）的体系化培训教材。
> **讲解中文 + 术语英文**，每个模块含**真实可运行的 Jupyter notebook**（带 ✏️ 练习 + `assert` 自动校验）和**深度 HTML 讲解**。
> 主线：**危险能力评估（dangerous capability evals）、红队方法论（red-teaming）、拒绝校准（refusal calibration）、sandbagging 检测、AI control、safety case** —— 前沿实验室安全团队的核心技能栈。

---

## 🛡️ 立场声明（请先读）

**本课程是防御性 / 评测 / 治理视角的教学材料。**

- 全程站在**测量者与治理者**一侧：怎么设计评估、怎么量化风险、怎么写 safety case，而不是怎么实施攻击。
- 所有 notebook 实验均使用**合成数据（synthetic data）与良性占位内容（benign placeholder payloads）**，不包含任何可操作的有害内容、真实攻击载荷或危险知识。
- 红队相关模块教的是**方法论本身**：覆盖率、严重性分级、triage 流程、发现曲线 —— 用无害的占位任务做统计模拟。
- 这正是前沿实验室安全团队的日常工作方式：评估在受控环境中进行，公开材料只讨论框架与测量方法。

---

## 🎯 这套教材是什么

不是"怎么越狱模型"的猎奇材料，而是一条从**风险框架 → 评估设计 → 测量方法 → 控制与治理**的完整研究路径。
每个模块都回答三个问题：

1. **要测什么、为什么测？**（威胁模型 / 政策承诺 → 评估目标）
2. **怎么把它变成可信的测量？**（任务设计 + 统计方法 + 代码）
3. **测出来之后怎么用？**（阈值决策、控制措施、safety case 论证）

读完你应该能：读懂任意前沿实验室的 RSP / Preparedness 框架与 system card、独立设计一项危险能力评估、量化红队覆盖率、检测 sandbagging、为一项部署决策搭出 safety case 骨架。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────────┐
   框架与设计        │ 00 环境 → 01 风险框架 RSP/ASL → 02 危险能力评估   │
                    └─────────────────────────────────────────────────┘
                                        │
                    ┌─────────────────────────────────────────────────┐
   测量方法 ★        │ 03 红队方法论 → 04 拒绝校准 → 05 Sandbagging     │
                    └─────────────────────────────────────────────────┘
                                        │
                    ┌─────────────────────────────────────────────────┐
   控制与治理        │ 06 AI Control 与监控 → 07 Safety Case 与报告     │
                    └─────────────────────────────────────────────────┘
```

| # | 模块 | Notebook | HTML 讲解 | 算力 |
|---|------|----------|-----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | `00_overview.html` | CPU |
| 01 | [风险分类与安全框架](01_risk_frameworks/) | `01_risk_frameworks.ipynb` | `01_讲解.html` | CPU |
| 02 | [危险能力评估设计](02_dangerous_capability_evals/) | `02_dangerous_capability_evals.ipynb` | `02_讲解.html` | CPU |
| 03 | [红队方法论](03_redteam_methodology/) | `03_redteam_methodology.ipynb` | `03_讲解.html` | CPU |
| 04 | [鲁棒性测量与拒绝校准](04_robustness_refusal/) | `04_robustness_refusal.ipynb` | `04_讲解.html` | CPU/GPU |
| 05 | [Sandbagging 与评测完整性](05_sandbagging_integrity/) | `05_sandbagging_integrity.ipynb` | `05_讲解.html` | CPU |
| 06 | [AI Control 与监控](06_ai_control/) | `06_ai_control.ipynb` | `06_讲解.html` | CPU |
| 07 | [Safety Case 与治理报告](07_safety_cases/) | `07_safety_cases.ipynb` | `07_讲解.html` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n safety python=3.11 -y && conda activate safety

# 2. 安装依赖（本课几乎全程 CPU，torch 装 CPU 版即可）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name safety --display-name "Safety Evals Course"

# 4. （可选）配置 API key —— 仅个别对比 cell 用到，跳过不影响主线
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# 5. 启动
jupyter lab
```

**算力说明**：本课以**统计与模拟**为主 —— bootstrap 置信区间、检测功效分析、蒙特卡洛模拟、监控策略博弈 —— 几乎全部 notebook 在笔记本电脑 CPU 上即可完整运行。仅 04 模块的可选小模型实测 cell 标 `GPU`，无 GPU 时可跳过，所有结论用预置的合成结果同样能复现。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键文献清单（RSP / 评估报告 / 论文，按模块组织）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解建立框架，再跑 notebook 做 ✏️ 练习（每个练习配 `assert`，通过即掌握）。
- **查漏补缺**：直接挑模块。03/04/05 是测量方法主线，可独立学。
- **面试 / 研究准备**：每个 HTML 末尾有「研究前沿与开放问题」，是 METR / frontier lab safety 面试的高频深挖入口。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，防御性视角，合成数据，真实可运行。*
