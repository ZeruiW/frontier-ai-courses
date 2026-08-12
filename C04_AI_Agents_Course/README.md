# AI 智能体与 Agentic 评测 · 研究科学家级系统培训

> 一套从零构建 AI agent、并用 METR 风格方法论评测 agent 的体系化培训教材。
> **讲解中文 + 术语英文**，以**真实可运行的 Jupyter notebook 实践为主**，每本 notebook 带 ✏️ 练习题 + `assert` 自动判分。
> 强化 **agentic 评测（evaluation）** 与 **agent 安全（safety）** 两条主线 —— 所有安全内容均为**防御视角**，全部在 **toy 环境**中演示。

---

## 🎯 这套教材是什么

不是 "怎么调 agent 框架 API" 的速成班，而是一条从**循环 → 工具 → 沙箱 → 实战形态 → 评测 → 安全**的完整研究路径。
每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation）
2. **它在工程上怎么从零实现？**（不依赖框架，亲手写循环、写 harness）
3. **怎么衡量它好不好、它会怎么坏？**（METR 风格评测 + 失败模式）

读完你应该能：从零写出一个 ReAct agent、搭一套带沙箱和轨迹记录的 agent harness、设计一组 pass@k / time horizon 风格的 agentic 评测、识别 prompt injection 等 agent 安全风险并设计监控防线。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   构建 Agent        │ 00 环境 → 01 Tool Use → 02 ReAct → 03 沙箱   │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   实战形态          │ 04 编码 Agent（SWE-bench） → 05 Computer Use │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   评测与安全 ★      │ 06 Agentic 评测 → 07 多智能体 → 08 安全监控   │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | HTML 讲解 | 算力 |
|---|------|----------|-----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | `00_overview.html` | CPU |
| 01 | [Tool Use 与 function calling](01_tool_use/) | `01_tool_use.ipynb` | `01_讲解.html` | CPU/API |
| 02 | [从零写 ReAct Agent](02_react_agent/) | `02_react_from_scratch.ipynb` | `02_讲解.html` | CPU/GPU |
| 03 | [沙箱、轨迹与 agent harness](03_sandbox_harness/) | `03_sandbox_harness.ipynb` | `03_讲解.html` | CPU |
| 04 | [编码 Agent 解剖：SWE-bench](04_coding_agents/) | `04_coding_agents.ipynb` | `04_讲解.html` | CPU/GPU |
| 05 | [Computer Use：截图→动作](05_computer_use/) | `05_computer_use.ipynb` | `05_讲解.html` | GPU |
| 06 | [Agentic 评测方法论 ★](06_agentic_evals/) | `06_agentic_evals.ipynb` | `06_讲解.html` | CPU/GPU |
| 07 | [多智能体与编排](07_orchestration/) | `07_orchestration.ipynb` | `07_讲解.html` | CPU/API |
| 08 | [Agent 安全与监控 ★](08_agent_safety/) | `08_agent_safety.ipynb` | `08_讲解.html` | CPU/GPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n agents python=3.11 -y && conda activate agents

# 2. 安装依赖（无 GPU 也能装，torch 默认 CPU 版即可）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name agents --display-name "Agents Course"

# 4. （可选）配置 API key —— 没有也能跑，全程可用本地小模型
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# 5. 启动
jupyter lab
```

**算力说明**：本课程 **CPU-first** —— agent 循环、沙箱、harness、评测统计这些核心内容在笔记本电脑上就能跑通。需要模型当 "agent 大脑" 的地方默认用本地小模型 **Qwen2.5-1.5B-Instruct**（CPU 可推理，GPU 更快）；配置了 API key 则自动切换到闭源模型，体验更佳（工具调用更稳、轨迹更长）。唯一的例外是 **模块 05（Computer Use）**：截图理解需要视觉模型 **Qwen2-VL-2B**，建议 GPU（约 8GB 显存）。无 GPU 时模块 05 的代码逻辑仍可阅读，重型 cell 已标注预计资源。

---

## ✏️ 练习与自动判分

每本 notebook 末尾有 **✏️ 练习题**：留出 `# TODO` 让你补全实现，紧跟一组 `assert` 自动判分 cell —— 全部通过即代表该模块达标。不需要对答案，跑通即正确。

---

## 🔒 关于安全内容

模块 08（以及散落在各模块的安全小节）全部采用**防御者视角**：演示 prompt injection、数据外渗（exfiltration）等攻击模式时，环境一律是**本课程自带的 toy 沙箱**（假文件系统、假邮件 API），目的是教你**识别、监控与防御**，不涉及任何真实系统。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键论文与博客清单（按模块组织）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 08 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手、做完练习题。
- **查漏补缺**：直接挑模块。06/08 是评测与安全主线，可独立学。
- **面试 / 研究准备**：06（agentic 评测方法论）+ 08（agent 安全与监控）覆盖 METR / 前沿实验室评测岗的核心话题，建议精读。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，真实可运行。*
