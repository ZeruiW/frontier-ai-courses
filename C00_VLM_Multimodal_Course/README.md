# VLM & Multimodal AI · 研究科学家级系统培训

> 一套从视觉编码器到原生多模态智能体的体系化培训教材。
> **讲解中文 + 术语英文**，每个模块含**真实可运行的 Jupyter notebook** 和**深度 HTML 讲解**。
> 强化 **评测（evaluation）** 与 **安全 / 危险能力评估** 两条主线 —— 面向模型评测方向的研究科学家。

---

## 🎯 这套教材是什么

不是 "怎么调 API" 的速成班，而是一条从**原理 → 架构 → 训练 → 评测 → 前沿**的完整研究路径。
每个模块都回答三个问题：

1. **它解决什么问题？**（动机 / motivation）
2. **它在数学和工程上怎么实现？**（推导 + 代码）
3. **怎么衡量它好不好、它会怎么坏？**（评测 + 失败模式）

读完你应该能：读懂任意 VLM 论文的架构图、复现核心组件、设计一套评测、识别幻觉与安全风险。

---

## 🗺️ 学习路径

```
                    ┌─────────────────────────────────────────────┐
   基础地基          │ 00 环境  → 01 视觉编码器 → 02 对比对齐 CLIP   │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   架构与训练        │ 03 架构演进 → 04 连接器/训练 → 05 指令微调    │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   能力与边界        │ 06 高分辨率/视频 → 07 评测体系 → 08 幻觉/安全 │
                    └─────────────────────────────────────────────┘
                                       │
                    ┌─────────────────────────────────────────────┐
   前沿              │ 09 原生多模态 & 多模态智能体                  │
                    └─────────────────────────────────────────────┘
```

| # | 模块 | Notebook | HTML 讲解 | 算力 |
|---|------|----------|-----------|------|
| 00 | [环境与总览](00_setup/) | `00_environment_check.ipynb` | `00_overview.html` | CPU |
| 01 | [多模态基础与视觉编码器](01_foundations/) | `01_vision_encoders.ipynb` | `01_讲解.html` | CPU/GPU |
| 02 | [对比对齐：CLIP / SigLIP](02_contrastive_clip/) | `02_clip_siglip.ipynb` | `02_讲解.html` | GPU |
| 03 | [VLM 架构演进](03_architectures/) | `03_architectures.ipynb` | `03_讲解.html` | GPU |
| 04 | [连接器与训练范式](04_connectors_training/) | `04_connectors.ipynb` | `04_讲解.html` | GPU |
| 05 | [视觉指令微调与对齐](05_instruction_tuning/) | `05_instruction_tuning.ipynb` | `05_讲解.html` | GPU |
| 06 | [高分辨率、任意分辨率与视频](06_highres_video/) | `06_highres_video.ipynb` | `06_讲解.html` | GPU |
| 07 | [VLM 评测体系](07_evaluation/) | `07_evaluation.ipynb` | `07_讲解.html` | GPU/API |
| 08 | [幻觉、鲁棒性与安全评估](08_hallucination_safety/) | `08_hallucination_safety.ipynb` | `08_讲解.html` | GPU/API |
| 09 | [原生多模态与多模态智能体](09_native_multimodal_agents/) | `09_native_agents.ipynb` | `09_讲解.html` | GPU/API |

> 也可以直接打开 [`index.html`](index.html)，那是带导航的课程主页。

---

## 🚀 快速开始

```bash
# 1. 建议用 conda / venv 隔离环境
conda create -n vlm python=3.11 -y && conda activate vlm

# 2. 先按 PyTorch 官网命令装好对应 CUDA 版本的 torch，再装其余依赖
pip install -r requirements.txt

# 3. 注册 Jupyter kernel
python -m ipykernel install --user --name vlm --display-name "VLM Course"

# 4. （评测/闭源对比模块需要）配置 API key
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export HF_TOKEN=hf_...          # 部分门控模型（如 Llama 系）需要

# 5. 启动
jupyter lab
```

**算力说明**：标 `CPU` 的 notebook 笔记本电脑即可跑；标 `GPU` 的 **Colab 免费 T4（16GB）就够**——课程里的模型多是 2–7B 级，默认 fp16 直接放得下，不需要量化，只有模块 05 的 QLoRA 教学会真正用到 4-bit；标 `API` 的需要闭源模型 key 做对比。无 GPU 时，代码逻辑仍可阅读，重型 cell 已标注预计资源。

---

## 📚 配套资料

- [`glossary.md`](glossary.md) —— 术语词典（中英对照 + 一句话定义）
- [`references.md`](references.md) —— 全部关键论文清单（按模块组织，含 arXiv 链接）

---

## 🧭 怎么用这套教材

- **系统学**：按 00 → 09 顺序，每模块先读 HTML 讲解建立直觉，再跑 notebook 动手。
- **查漏补缺**：直接挑模块。07/08 是评测主线，可独立学。
- **面试 / 研究准备**：每个 HTML 末尾有「研究前沿与开放问题」，可作为深挖入口。

---

*Built as a self-study research curriculum. 中文讲解，英文术语，真实可运行。*
