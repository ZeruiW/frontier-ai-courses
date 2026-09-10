# 推理模型与测试时计算：Reasoning Models & Test-Time Compute · 研究科学家级系统培训

> 一套从 chain-of-thought 的误差复利数学、self-consistency/Best-of-N、verifier/PRM、推理即搜索（beam/ToT/MCTS）到 test-time compute scaling laws 与推理模型评测的体系化培训教材。
> **讲解中文 + 术语英文**，以**真实可运行的 Jupyter notebook** 为主线，每本 notebook 带 ✏️ 练习 + assert 自动判分。
> **全课纯 numpy/matplotlib/pandas，CPU 可跑** —— 无需 torch、无需 API key。这是本课的卖点：用"模拟推理器"（simulated reasoner：步骤级成功率与 verifier 噪声完全可控的生成过程）把 self-consistency、PRM、MCTS、inference scaling law 全部做成有 ground truth 的定量实验，而不是对着 API 黑盒猜。

---

## 🎯 这套教材是什么

这是 RS-Evaluation 技能栈的**第 10 门课（C9）**。前面的课教你评测一般 LLM 与 agent；这门课聚焦 **2025–2026 评测的前沿：推理模型**。o1/R1 范式把"测试时算力"变成预训练规模、后训练质量之外的**第三条 scaling 轴**——模型学会在回答前花更多算力"思考"，评测者必须回答三个新问题：**算力怎么计、CoT 可不可信、基准怎么防污染防饱和**。每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation：这笔测试时算力买到了什么）
2. **它在数学和工程上怎么实现？**（推导 + 纯 numpy 从零手写）
3. **怎么验证你做对了？**（在 ground truth 已知的模拟推理器上复现论文结论 + assert 判分）

读完你应该能：用误差复利模型解释 CoT 为什么有用；推导并模拟 pass@k / consensus@k / Best-of-N 的统计行为；从零实现 ORM 与 PRM 并复现 verifier 不完美时的 Goodhart 过优化曲线；在玩具推理树上手写 beam search、Tree-of-Thoughts 与 MCTS；拟合 inference scaling law 并找出 compute-optimal 的算力分配；量化 overthinking 并设计 budget forcing；用 hint sensitivity 实验测 CoT faithfulness、用 GSM-Symbolic 式扰动设计抗污染评测。

注意分工：[`C02 Post_Training_Course`](../C02_Post_Training_Course/) 05 模块（RLVR/GRPO）讲**怎么训出**推理模型；本课讲训出来之后**怎么花测试时算力、怎么评**。

---

## 🗺️ 学习路径

```
                    ┌──────────────────────────────────────────────┐
   采样与聚合        │ 00 总览 → 01 CoT 与误差复利 → 02 self-        │
                    │    consistency 与 Best-of-N                   │
                    └──────────────────────────────────────────────┘
                                       │
                    ┌──────────────────────────────────────────────┐
   验证与搜索        │ 03 verifier 与 PRM（结果 vs 过程监督）→        │
                    │    04 推理即搜索（beam / ToT / MCTS）          │
                    └──────────────────────────────────────────────┘
                                       │
                    ┌──────────────────────────────────────────────┐
   扩展与效率        │ 05 TTC scaling laws → 06 overthinking        │
                    │    与预算控制                                  │
                    └──────────────────────────────────────────────┘
                                       │
                    ┌──────────────────────────────────────────────┐
   评测             │ 07 评测推理模型（faithfulness·污染·前沿基准）  │
                    └──────────────────────────────────────────────┘
```

| # | 模块 | Notebook | 算力 |
|---|------|----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | CPU |
| 01 | [CoT 与任务分解：误差复利的数学](01_cot_decomposition/) | `01_cot_error_compounding.ipynb` | CPU |
| 02 | [Self-Consistency 与 Best-of-N](02_self_consistency/) | `02_self_consistency_bon.ipynb` | CPU |
| 03 | [Verifier 与 PRM：结果 vs 过程监督](03_verifiers_prm/) | `03_verifiers_prm.ipynb` | CPU |
| 04 | [推理即搜索：beam / ToT / MCTS](04_search_mcts/) | `04_search_mcts.ipynb` | CPU |
| 05 | [测试时计算 Scaling Laws](05_ttc_scaling/) | `05_ttc_scaling_laws.ipynb` | CPU |
| 06 | [Overthinking 与预算控制](06_efficient_reasoning/) | `06_overthinking_budget.ipynb` | CPU |
| 07 | [评测推理模型](07_evaluating_reasoning/) | `07_evaluating_reasoning.ipynb` | CPU |
| 08 | [BONUS · 真模型实验室：用 Gemini 复跑全课实验](08_real_model_lab/)（可选） | `08_real_model_lab.ipynb` | API / CPU |

> 08 为可选 BONUS：设好 `GEMINI_API_KEY` 即用真实 Gemini API（纯标准库 urllib，依赖不变）；无 key 自动回退内置 MockGemini，整本照样跑通。也可在 4090 远程机上把 `llm_generate` 的后端换成本地模型（vLLM / Ollama 的 OpenAI 兼容端点）复跑全部实验。
> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n ttc python=3.11 -y && conda activate ttc

# 2. 安装依赖（纯 numpy 技术栈，无需 CUDA、无需 torch）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name ttc --display-name "Reasoning TTC Course"

# 4. 启动
jupyter lab
```

**无需任何 API key，也无需 torch。** 全部 8 个模块都用 numpy 在"模拟推理器"上做实验：每一步以可控概率 p 正确、verifier 以可控噪声打分、推理树的 ground truth 完全已知。这样做的代价是没有真实模型的语言能力，收益是每个统计结论都可以与解析解对照、每条 scaling 曲线都能在几秒内重跑一万次——这正是研究测试时计算该有的实验台。学完后迁移到真实模型只是把模拟器换成 API 调用。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（约 50 个核心术语，中英对照，每条 2–3 句释义）
- [`references.md`](references.md) —— 关键论文清单（按模块组织，含 arXiv 链接与一句话点评）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手写代码、过 assert。
- **查漏补缺**：直接挑模块。01/02 可独立学；03 的 PRM 是 04 搜索的打分函数；05 综合 02–04 的所有"花算力的方式"做统一核算；07 只依赖 01 的 CoT 概念。
- **面试准备**：02（pass@k 统计）、03（ORM vs PRM、Goodhart）、05（compute-optimal TTC）是 reasoning 方向评测面试的高频考点。

---

## 🔗 与其他课程的衔接

本课是技能栈中的**前沿评测专题**：推理模型怎么花测试时算力、这笔算力怎么核算、产出的 CoT 怎么审计。

| 课程 | 关系 |
|------|------|
| [`C02 Post_Training_Course`](../C02_Post_Training_Course/) | **同一枚硬币的两面**。其 05 模块（RLVR/GRPO）讲"怎么训出推理模型"——训练时把 verifiable reward 灌进权重；本课讲"训出来之后怎么花测试时算力与怎么评"。两课在 verifier/RLVR 处会师：同一个 verifier，训练时是 reward，测试时是 reranker。 |
| [`C03 LLM_Evals_Course`](../C03_LLM_Evals_Course/) | **前置**。其 06 模块的 pass@k 与能力引出是本课 02/05 的统计学起点；本课把"采样次数 k"从评测超参数升级为需要优化的算力预算变量。其 02 模块的统计严谨性（CI、paired test）默认贯穿本课所有实验。 |
| [`C06 Interpretability_Course`](../C06_Interpretability_Course/) | **CoT faithfulness 的另一半证据**。本课 07 用行为实验（hint sensitivity、扰动一致性）测 CoT 是否忠实——黑盒证据；interp 课的 probing/patching 提供激活级的白盒证据。审计一个推理模型两者都要。 |
| [`C01 LLM_Internals_Course`](../C01_LLM_Internals_Course/) | **地基**。其 04 模块（解码策略）是本课一切采样方法的机制基础；其 05 模块（训练 scaling laws）与本课 05（推理 scaling laws）是同一种幂律方法论用在两条轴上。 |
| [`C05 Safety_Evals_Course`](../C05_Safety_Evals_Course/) | CoT monitoring 是 AI control 的核心手段之一——前提是 CoT 足够 faithful（本课 07 教你测这个前提成不成立）。 |
| [`C04 AI_Agents_Course`](../C04_AI_Agents_Course/) | agent 的长 horizon 任务成功率与多步推理的误差复利（本课 01）是同一个数学；其 06 模块的 pass@k vs pass^k 与本课 02 互为镜像。 |

一句话：**post-training 决定推理能力的上限，test-time compute 决定单次任务上你兑现多少，评测科学决定你对这两者的测量可不可信。**

---

*Built as a self-study research curriculum. 中文讲解，英文术语，纯 numpy 模拟推理器，CPU 可跑。*
