# 后训练与对齐 · SFT → RLHF/DPO → RLVR

> 一套从监督微调到推理强化学习的完整后训练（post-training）管线教材。
> **讲解中文 + 术语英文**，每个模块含**真实可运行的 Jupyter notebook** 和**深度 HTML 讲解**。
> 每本 notebook 带 **✏️ 练习 + assert 自动判分**，核心算法全部**纯 PyTorch 玩具规模实现，CPU 即可跑通**。

---

## 🎯 这套教材是什么

不是 "怎么调 TRL API" 的速成班，而是一条从**SFT → 奖励建模 → RLHF/PPO → DPO → RLVR/GRPO**的完整后训练研究路径。
每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation）
2. **它在数学和工程上怎么实现？**（推导 + 代码）
3. **怎么衡量它好不好、它会怎么坏？**（评测 + 失败模式）

读完你应该能：从 Bradley-Terry 推到 DPO 损失、手写一个能跑的 PPO/GRPO 训练循环、解释 reward hacking 与 alignment tax、读懂任意后训练论文的方法节。

**CPU-first 设计**：核心算法（PPO、DPO、GRPO 等）全部用纯 PyTorch 在玩具规模上实现，笔记本电脑即可完整跑通推导与训练曲线；涉及真实模型的环节统一用 **Qwen2.5-0.5B-Instruct**，有 GPU 更快，没有也能跑。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   监督阶段          │ 00 环境  →  01 SFT 与 loss masking          │
                    │          →  02 奖励模型（Bradley-Terry）     │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   强化对齐          │ 03 RLHF/PPO → 04 DPO 家族 → 05 RLVR/GRPO    │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   评测与前沿        │ 06 对齐的评测 ★ → 07 CAI / weak-to-strong   │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | HTML 讲解 | 算力 |
|---|------|----------|-----------|------|
| 00 | [课程总览与环境](00_setup/) | `00_environment_check.ipynb` | `00_overview.html` | CPU |
| 01 | [SFT 与 loss masking](01_sft/) | `01_sft_loss_masking.ipynb` | `01_讲解.html` | CPU/GPU |
| 02 | [奖励模型：Bradley-Terry 与 reward hacking](02_reward_models/) | `02_reward_model.ipynb` | `02_讲解.html` | CPU |
| 03 | [RLHF 与 PPO](03_rlhf_ppo/) | `03_rlhf_ppo.ipynb` | `03_讲解.html` | CPU |
| 04 | [DPO 家族：推导与实跑](04_dpo_family/) | `04_dpo_family.ipynb` | `04_讲解.html` | CPU/GPU |
| 05 | [推理模型与 RLVR/GRPO](05_rlvr_grpo/) | `05_rlvr_grpo.ipynb` | `05_讲解.html` | CPU |
| 06 | [对齐的评测 ★](06_alignment_evals/) | `06_alignment_evals.ipynb` | `06_讲解.html` | CPU/GPU |
| 07 | [前沿：CAI、self-play 与 weak-to-strong](07_frontier_alignment/) | `07_frontier_alignment.ipynb` | `07_讲解.html` | CPU |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n posttrain python=3.11 -y && conda activate posttrain

# 2. 安装依赖（CPU 版 torch 即可；有 GPU 先按 PyTorch 官网装对应 CUDA 版本）
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name posttrain --display-name "Post-Training Course"

# 4. （可选）配置 API key —— 仅个别评测/对比 cell 需要
export OPENAI_API_KEY=sk-...
export HF_TOKEN=hf_...          # 部分门控模型需要

# 5. 启动
jupyter lab
```

**算力说明**：所有核心算法 notebook 标 `CPU`，玩具规模纯 PyTorch 实现，笔记本电脑几分钟跑完；标 `CPU/GPU` 的模块包含真实模型（Qwen2.5-0.5B-Instruct）微调环节，CPU 能跑但慢，有单卡 GPU 体验更佳。每本 notebook 的 ✏️ 练习都配 assert 自动判分，做完即知对错。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键论文清单（按模块组织，含 arXiv 链接）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 07 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手做练习。
- **查漏补缺**：直接挑模块。03/04/05 是算法主线，06 评测可独立学。
- **面试 / 研究准备**：每个 HTML 末尾有「研究前沿与开放问题」，可作为深挖入口；DPO 推导与 GRPO 对比是高频面试题。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，真实可运行。*
