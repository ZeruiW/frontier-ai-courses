# HuggingFace 生态与 API 实操

全课体系「CPU-first、纯 numpy」的铁律让你吃透了原理，却留下一个洞：**用真实工具干活的手艺**。
你能推导 LoRA 的低秩分解，但不知道 `target_modules` 该填什么；理解 MLM 的 80/10/10，
但不知道它在 `DataCollatorForLanguageModeling` 里就是三行。这门课补这个洞。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | transformers 核心抽象 | `01_transformers_core/` |
| 02 | tokenizers 与 datasets | `02_tokenizers_datasets/` |
| 03 | Trainer 与 TrainingArguments | `03_trainer/` |
| 04 | PEFT 与 TRL | `04_peft_trl/` |
| 05 | Accelerate、Hub 与推理 API | `05_accelerate_hub_api/` |

## 这门课补什么洞
它是一门 **接口课与手艺课**，不重复讲算法原理——只讲「这个原理在生态里叫什么、参数在哪、
默认值是什么、坑在哪」。正面回应 JD 里的 `Familiarity with Hugging Face libraries and OpenAI APIs`。
与 **C49** 配套：那门课讲模型形态与预训练目标，本课讲怎么用生态把它跑起来。

## 怎么学（两条腿）
1. **迷你复刻（必跑）**：用一两百行把库的核心机制自己写一遍——`Auto*` 注册分发、
   `from_pretrained` 的键名匹配、fast tokenizer 的 offset/word_ids、`Dataset.map` 的批处理与指纹缓存、
   完整 `Trainer` 循环、LoRA 注入/缩放/合并、SFT 掩码、DPO 损失、带退避抖动与双限的 API 客户端。
   全部带 `assert` 钉死语义。
2. **真实 API 对照（旁注，不跑）**：紧跟在每个迷你实现旁边，标注参数位置、默认值与坑。
   这些代码可原样复制到有网环境使用。

每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）+ `NN_*.ipynb`：
worked 示例（print + assert）→ ✏️ 练习（TODO + assert 判分）→ 📖 参考答案 → 🧪 真实 API 配方胶囊。
所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。**本环境不联网、没有 GPU、也不预装 transformers**——课程不依赖它们。
notebook 里所有涉及真实库的单元格都 `try/except ImportError` 优雅回退：
有库跑真的、没库跑迷你版。把它们拷到有网环境会自动升级成真实实验。

配套：[术语词典](glossary.md) · [参考清单](references.md)
