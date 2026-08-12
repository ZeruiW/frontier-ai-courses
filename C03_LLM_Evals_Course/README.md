# LLM 评测科学 · 研究科学家级系统培训

> 一套从统计严谨性到前沿评测方法的体系化培训教材，主题只有一个：**怎么科学地测量一个语言模型**。
> **讲解中文 + 术语英文**，以**真实可运行的 Jupyter notebook** 实践为主，配深度 HTML 讲解。
> 每本 notebook 都带 **✏️ 练习题**，并用 **`assert` 自动判分** —— 做错跑不过去，做对当场确认。

---

## 🎯 这套教材是什么

不是"跑个 benchmark 看分数"的速成班，而是一条从**方法论 → 测量对象 → 工程实现 → 前沿报告**的完整研究路径。
每个模块都回答三个问题：

1. **这个测量为什么会出错？**（失败模式 / threats to validity）
2. **正确的做法在统计和工程上长什么样？**（推导 + 代码）
3. **怎么把结论负责任地报告出去？**（误差棒、效度、eval card）

读完你应该能：给任意 benchmark 分数挂上正确的误差棒、判断两个模型的差异是否显著、识别 judge 偏差与数据污染、从零写出一个可复现的 eval harness。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   方法论地基        │ 00 环境 → 01 评测分类学 → 02 统计严谨性       │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   测什么与怎么测    │ 03 prompt 敏感性 → 04 LLM-as-a-Judge          │
                    │ → 05 数据污染 → 06 能力引出与 pass@k          │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   工程与前沿        │ 07 从零搭 eval harness → 08 Arena 与评测报告 │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | HTML 讲解 | 算力 |
|---|------|----------|-----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | `00_overview.html` | CPU |
| 01 | [评测分类学与 benchmark 全景](01_benchmark_landscape/) | `01_benchmark_landscape.ipynb` | `01_讲解.html` | CPU |
| 02 | [统计严谨性：误差棒、配对检验与功效](02_statistics/) | `02_statistical_rigor.ipynb` | `02_讲解.html` | CPU |
| 03 | [答案抽取与 prompt 敏感性](03_prompt_sensitivity/) | `03_prompt_sensitivity.ipynb` | `03_讲解.html` | CPU/GPU |
| 04 | [LLM-as-a-Judge 深剖](04_llm_judge/) | `04_llm_judge.ipynb` | `04_讲解.html` | CPU/GPU/API |
| 05 | [数据污染与基准饱和](05_contamination/) | `05_contamination.ipynb` | `05_讲解.html` | CPU |
| 06 | [能力引出与 pass@k](06_elicitation/) | `06_elicitation_passk.ipynb` | `06_讲解.html` | CPU/GPU |
| 07 | [从零搭建 eval harness](07_harness/) | `07_build_harness.ipynb` | `07_讲解.html` | CPU |
| 08 | [Arena、time-horizon 与评测报告](08_frontier/) | `08_arena_horizon.ipynb` | `08_讲解.html` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n evals python=3.11 -y && conda activate evals

# 2. 安装依赖（本课 CPU 即可，torch 装默认 CPU 版就行）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name evals --display-name "Evals Course"

# 4. （可选）配置 API key —— 仅个别对照实验需要，没有也能学完整门课
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export HF_TOKEN=hf_...          # 下载部分 HuggingFace 模型/数据集时需要

# 5. 启动
jupyter lab
```

**算力说明**：本课 **CPU-first** —— 绝大多数 notebook（统计模拟、污染检测、harness 工程、Arena 排序）在笔记本电脑 CPU 上即可完整运行。标 `GPU` 的模块用小模型 **Qwen2.5-1.5B-Instruct** 做真实推理实验，CPU 也能跑、只是慢；标 `API` 的部分是可选对照实验（如用闭源模型当 judge），无 key 可跳过，不影响主线。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键论文清单（按模块组织，含 arXiv 链接）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 08 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手。
- **✏️ 练习题**：每本 notebook 散布若干练习 cell，写完代码直接运行 —— `assert` 全过即正确，报错就是判分反馈，不需要对答案。
- **查漏补缺**：直接挑模块。02（统计）和 04（judge）是被引用最多的方法论模块，可独立学。
- **面试 / 研究准备**：每个 HTML 末尾有「研究前沿与开放问题」，可作为深挖入口。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，真实可运行。*
