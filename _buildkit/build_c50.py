#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C50 · HuggingFace 生态与 API 实操。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c50_m00, c50_m01, c50_m02, c50_m03, c50_m04, c50_m05

CID = "C50_HuggingFace_Ecosystem_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "从「自己写 numpy」到「用生态干活」——五层抽象地图；「迷你复刻 + 真实 API 对照 + 优雅回退」的学法；本课不装任何库也能学透",
     c50_m00),
    ("01_transformers_core", "01_讲解.html", "01_transformers_core.ipynb",
     "01 · transformers 核心抽象",
     "config/model/tokenizer 三件套与同源铁律 · from_pretrained 的六步与键名匹配 · dtype 与显存账 · labels 右移的两个不对称 · generate() 的参数生效条件与左 padding",
     c50_m01),
    ("02_tokenizers_datasets", "02_讲解.html", "02_tokenizers_datasets.ipynb",
     "02 · tokenizers 与 datasets",
     "fast tokenizer 的 offsets 与 word_ids 才是它的价值 · padding/truncation 的算力浪费 · map 的批处理与指纹缓存 · streaming 的缓冲打乱 · DataCollator 与 -100 的构造",
     c50_m02),
    ("03_trainer", "03_讲解.html", "03_trainer.ipynb",
     "03 · Trainer 与 TrainingArguments",
     "Trainer 内部的训练循环骨架 · 有效 batch 的三个乘数与梯度累积等价性 · 调度器与总步数 · checkpoint 存了什么恢复了什么 · 十个高频坑与一个配置校验器",
     c50_m03),
    ("04_peft_trl", "04_讲解.html", "04_peft_trl.ipynb",
     "04 · PEFT 与 TRL",
     "LoRA 四参数的真实含义（B=0 / α÷r / 覆盖面 > 秩）· merge 的等价性与不可逆 · QLoRA 的四个组件 · SFT 的 chat template 与 completion-only 掩码 · DPO 的 beta 与长度偏差",
     c50_m04),
    ("05_accelerate_hub_api", "05_讲解.html", "05_accelerate_hub_api.ipynb",
     "05 · Accelerate、Hub 与推理 API",
     "prepare 藏起来的分布式切分 · gather_for_metrics 的去重 · unwrap 与 module. 前缀 · safetensors 为何比 pickle 安全 · 客户端四层防护（退避抖动/双限/幂等/超时）与成本归因",
     c50_m05),
]


def build():
    install_assets(DIR)
    for i, (folder, html_name, nb_name, h1, subtitle, mod) in enumerate(MODULES):
        prev = nxt = None
        if i > 0:
            p = MODULES[i - 1]; prev = ("../%s/%s" % (p[0], p[1]), p[3])
        if i < len(MODULES) - 1:
            n = MODULES[i + 1]; nxt = ("../%s/%s" % (n[0], n[1]), n[3])
        lesson(os.path.join(DIR, folder, html_name),
               num="%02d" % i, total=TOTAL, h1=h1, subtitle=subtitle,
               meta=mod.META, sections=mod.SECTIONS, prev=prev, nxt=nxt)
        notebook(os.path.join(DIR, folder, nb_name), mod.NB)

    index(
        os.path.join(DIR, "index.html"),
        title="HuggingFace 生态与 API 实操",
        subtitle="你懂原理，但不知道参数在哪、默认值是什么、坑在哪 —— 这门课补上那层手艺：transformers · tokenizers · datasets · Trainer · PEFT · TRL · Accelerate · Hub · OpenAI 兼容 API",
        pills=["6 模块", "transformers · datasets · Trainer · PEFT/TRL · API",
               "迷你复刻 + 真实 API 对照 + 优雅回退", "每层的坑清单 + 可复用配方",
               "CPU only · 不装任何库也能跑通"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em>——它<strong>不重复讲算法原理</strong>（那是其他课的事），"
            "只讲「这个原理在生态里叫什么、参数在哪、默认值是什么、坑在哪」；"
            "再跑 <em>notebook</em> 用一两百行 Python <strong>把库的核心机制自己写一遍</strong>："
            "<code>Auto*</code> 的注册分发、<code>from_pretrained</code> 的键名匹配、fast tokenizer 的 offset 与 word_ids、"
            "<code>Dataset.map</code> 的批处理与指纹缓存、完整的 <code>Trainer</code> 训练循环、LoRA 的注入/缩放/合并、"
            "SFT 的 completion-only 掩码、DPO 损失、以及带退避抖动与双限的 API 客户端。"
            "写过一遍之后，真实库对你就不再是黑箱。每个练习都有紧跟的 <code>assert</code> 自测判分。"
            "配套 <a href=\"glossary.md\">术语词典</a> 与 <a href=\"references.md\">参考清单</a>。"
            "<strong>本环境不联网、没有 GPU、也不预装 transformers</strong>——所以本课走两条腿："
            "<strong>①迷你复刻</strong>（必跑，带 assert 钉死语义）与 <strong>②真实 API 对照</strong>"
            "（旁注不跑，但是可原样复制到有网环境的正确写法）。所有涉及真实库的单元格都用 "
            "<code>try/except ImportError</code> 优雅回退——把这些 notebook 拷到有网环境，它们会自动升级成真实实验。"
            "这样学其实比直接调 API 更透：<em>「会调 API」和「知道 API 在做什么」是两回事，而后者才决定你能不能排查问题</em>。"
            "本课与 <strong>C49</strong> 配套（那门课讲模型形态与目标，本课讲怎么把它跑起来），"
            "并正面回应 JD 里的 <code>Familiarity with Hugging Face libraries and OpenAI APIs</code>。"
        ),
        tracks=[
            ("模型与数据 · Models &amp; Data", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "五层抽象地图与「出问题先定位哪一层」的调试原则；注册表+分发模式；三条纪律（语义对齐 / 参数账 / 坑要显式化）；为什么不装库反而学得透。"),
                ("01_transformers_core/01_讲解.html", "MODULE 01", "transformers 核心抽象",
                 "tokenizer 与 model 必须同源；from_pretrained 六步里唯一会静默出错的那一步；fp16 vs bf16；显存公式为什么用「可训练参数」；labels 右移的两个相反不对称；temperature 只在 do_sample=True 时生效。"),
                ("02_tokenizers_datasets/02_讲解.html", "MODULE 02", "tokenizers 与 datasets",
                 "offsets 与 word_ids 不可替代（QA 不能用 decode 拼答案、NER 必须对齐子词）；padding='max_length' 可能浪费 89% 注意力算力；map 的签名切换与指纹缓存；-100 是全生态约定。"),
            ]),
            ("训练与微调 · Training &amp; Fine-tuning", [
                ("03_trainer/03_讲解.html", "MODULE 03", "Trainer 与 TrainingArguments",
                 "读一遍训练循环骨架胜过读十篇教程；有效 batch = 三个数相乘（已对拍梯度等价）；loss 要先除 grad_accum；换卡数会改变整条 lr 曲线；十个高频坑与一个配置校验器。"),
                ("04_peft_trl/04_讲解.html", "MODULE 04", "PEFT 与 TRL",
                 "B=0 让微调从原模型连续出发；固定 α/r 比值而非固定 α；覆盖面比秩更重要；task_type 填错会冻住新头；QLoRA 四组件与 prepare_model_for_kbit_training；SFT 掩码与 DPO 的长度偏差。"),
            ]),
            ("分发与调用 · Shipping &amp; Calling", [
                ("05_accelerate_hub_api/05_讲解.html", "MODULE 05", "Accelerate、Hub 与推理 API",
                 "prepare 换掉 sampler（有效 batch ×卡数）与累积期跳过同步；gather_for_metrics 的去重；unwrap 否则全部键 missing；pickle 是可执行的；退避必须加抖动；TPM 通常才是真瓶颈。"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), """
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
""")

    text_file(os.path.join(DIR, "requirements.txt"), """
# HuggingFace 生态与 API 实操 —— 依赖清单
# 本课的「迷你复刻」主线只需 numpy + 标准库，CPU 可跑（assert 全过）。
# 真实库全部是「有则更好」：notebook 用 try/except ImportError 优雅回退。

numpy          # 核心：所有迷你复刻的数值部分
pandas         # 可选：参数账表格的展示
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel

# ── 以下为可选（本课不依赖；在有网环境装上后 notebook 会自动走真实路径）──
# transformers>=4.44
# datasets
# accelerate
# peft
# trl
# safetensors
# openai
""")

    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


GLOSSARY = r"""
# 术语词典 · Glossary（HuggingFace 生态与 API 实操）

> 按主题分组。这是一本**参数与接口**词典：每条尽量写清「它是什么、默认值/常用值、坑在哪」。
> 读官方文档或排查报错时回这里查。英文术语保留原文（社区通用语言）。

## 生态分层与通用概念 · Ecosystem

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| Auto classes | Auto 类族 | `AutoModel`/`AutoTokenizer`/`AutoConfig`。机制极简：读 `config.json` 的 `model_type` 字段查一次注册表。不神奇。 |
| `model_type` | 模型类型 | `config.json` 里的字段，是 `Auto*` 分发的**唯一依据**。名字推断（`bert-base-…`→`bert`）只是兜底。 |
| `from_config` vs `from_pretrained` | 建结构 vs 建结构+加载权重 | 前者**随机初始化**、后者加载真实权重。两者都不报错，搞混会得到「能跑但输出全是噪声」的模型。 |
| `output_loading_info` | 加载信息 | `from_pretrained(..., output_loading_info=True)` 返回 `missing_keys`/`unexpected_keys`/`mismatched_keys`。**把读日志变成断言**的钩子。 |
| `missing_keys` | 缺失键 | 模型要但权重文件没有 → **随机初始化**。微调时只应包含分类头；出现大量主干键说明模型类选错。 |
| `unexpected_keys` | 多余键 | 文件有但模型不要 → 丢弃（如预训练的 MLM 头）。通常无害。 |
| `ignore_mismatched_sizes` | 忽略形状不匹配 | 允许「主干加载 + 头重初始化」，改 `num_labels` 时必需。 |
| safetensors | 安全张量格式 | header JSON + 连续张量字节。**不执行代码**、可 mmap 零拷贝、可部分加载、加载快 2–5×。 |
| pickle (`.bin`) | pickle 权重 | PyTorch 旧格式。**反序列化会执行 `__reduce__` 里的任意代码** → 从不可信来源加载等于运行陌生人的脚本。 |
| `trust_remote_code` | 信任远端代码 | 会执行 repo 里的 `modeling_*.py`。只对可信 repo 开。 |
| `revision` | 版本 | Hub 的分支/tag/commit sha。**用 `main` 会在上游更新后静默换模型**；生产钉 commit sha。缓存按 sha 分目录。 |
| model card | 模型卡片 | 至少写清六件事：基座+revision、数据、超参、评测、**输入格式（chat template）**、限制与许可。 |

## transformers 核心 · Loading & Generation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| `torch_dtype` | 权重精度 | `"auto"` 读 config；不指定则一律 fp32（显存 ×2）。 |
| fp16 vs bf16 | 半精度两种 | fp16 精度高但**动态范围小**（易 nan）；bf16 范围与 fp32 相同、更稳。**训练遇 nan 第一反应是换 bf16**。 |
| `device_map="auto"` | 自动设备放置 | 按层贪心填满设备，超出则 offload 到 CPU/磁盘。是「跑得起来」的手段，不是「跑得快」的手段。 |
| `low_cpu_mem_usage` | 低内存加载 | 边加载边放置，不先在 CPU 建整个模型。加载大模型时近乎必需。 |
| `attn_implementation` | 注意力实现 | `"sdpa"`（PyTorch 原生高效）/ `"flash_attention_2"`（需额外安装）/ `"eager"`。 |
| `AutoModelFor*` | 任务头类族 | `SequenceClassification`/`TokenClassification`/`QuestionAnswering`/`MaskedLM`/`CausalLM`/`Seq2SeqLM`。选错头是新手高频错误。 |
| labels 右移 | label shifting | **CausalLM 内部自动右移**（你传 `labels=input_ids`，别自己移）；**Seq2SeqLM 不用你移**（除非手传 `decoder_input_ids`）。两个方向相反的不对称。 |
| `max_new_tokens` | 新生成 token 上限 | **优先用它而非 `max_length`**（后者含 prompt，会随输入变化）。 |
| `do_sample` | 是否采样 | **`temperature`/`top_k`/`top_p` 只在它为 True 时生效**——这是头号误用。`temperature=0` 在 `generate` 里非法，要确定性用 `do_sample=False`。 |
| `padding_side` | padding 方向 | **批量生成必须左 padding**（decoder-only 从末尾续写）；**训练用右 padding**。「单条正常、批量变差」就是这个。 |
| `GenerationConfig` | 生成配置 | 模型自带的默认生成参数（`generation_config.json`）。你传的 kwargs 覆盖它。 |

## 数据层 · Tokenizers & Datasets

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| fast tokenizer | 快速分词器 | Rust 实现。真正的价值不只是快，而是提供 `offset_mapping` 与 `word_ids()`。slow 版调用 `word_ids()` 会抛异常。 |
| `offset_mapping` | 字符偏移映射 | 每个 token 在**原始字符串**中的 `(start,end)`。QA 抽取答案必须用它从原文切——**不能用 decode 拼**（分词非无损可逆）。特殊 token 的 offset 是 `(0,0)` 而非 `None`。 |
| `word_ids()` | 词索引 | 每个 token 属于第几个词，特殊 token 为 `None`。词级标注对齐到子词的唯一可靠来源。 |
| `sequence_ids()` | 句索引 | 区分特殊 token / 句 A / 句 B。QA 里用它把 span 搜索限制在上下文那一句。 |
| whole word masking | 整词掩码 | 掩码时把一个词的所有子词一起掩。只掩一个子词会让任务退化成拼写补全。 |
| `padding=True` vs `'max_length'` | 动态 vs 定长 padding | 前者补到本 batch 最长（省），后者补到上限（**注意力可能浪费 89%**）。 |
| `group_by_length` | 按长度分组 | 把长度接近的样本放同一 batch。**比动态 padding 更大的杠杆**（可省一半以上注意力浪费），代价是牺牲一点随机性。 |
| `truncation='only_second'` | 只截第二句 | QA 用它——问题不能截、上下文可以。 |
| 截断率 vs 信息损失率 | truncation rate vs info loss | 必须分开看。前者高后者低（每条只丢一点）通常可接受；后者高意味着**系统性丢弃某个子群体**。截断是静默的，要统计并告警。 |
| `return_overflowing_tokens` | 返回溢出部分 | 长文档滑窗的标准做法。**会改变样本数量** → 必须配 `remove_columns`。 |
| Arrow / 内存映射 | Arrow backend | `datasets` 的列式存储，可用几百 MB 内存处理几百 GB 数据集。 |
| `map(batched=True)` | 批处理 map | 快 10–100×（走 tokenizer 的批量接口）。**函数签名不同**：`batched=False` 收到字符串，`True` 收到字符串列表。 |
| fingerprint cache | 指纹缓存 | 对（数据状态, 函数字节码, 参数）哈希，命中则读缓存。改函数体会重算；依赖外部可变状态时要 `load_from_cache_file=False`。 |
| `remove_columns` | 删除列 | **只要 map 可能改变行数就必须传** `ds.column_names`，否则报 `Column lengths mismatch`；也显著省磁盘。 |
| `IterableDataset` / streaming | 流式数据集 | 边下边用。没有 `len()`、不能随机索引、`shuffle` 只能**缓冲区近似**。 |
| buffer shuffle | 缓冲区打乱 | 维护大小 N 的缓冲随机吐出。缓冲太小 + 磁盘有序 = 同 batch 高度相关。真实库会同时打乱 shard 顺序（两级打乱）。 |
| DataCollator | 数据整理器 | 每个 batch 调一次：动态 padding + 构造 labels。**MLM 的动态掩码就在这里发生**（HF 默认即动态）。 |
| `-100` | 忽略索引 | 全生态约定（`CrossEntropyLoss(ignore_index=-100)`）。padding、非首子词、SFT 的 prompt 部分都要填它。漏填会让 loss 更好看但效果更差。 |

## 训练层 · Trainer

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 有效 batch | effective batch | `per_device_train_batch_size × gradient_accumulation_steps × n_devices`。**最常被搞混的参数组合**。 |
| `gradient_accumulation_steps` | 梯度累积 | 用多个 micro-batch 凑一个大 batch。**loss 要在 backward 前除以它**，忘了等于学习率放大 N 倍 → 一开就发散。 |
| `global_step` | 优化步 | `logging_steps`/`eval_steps`/`save_steps` 数的都是它，**不是 batch 数**。accum=8 时跑 800 batch 才 100 步。 |
| 总优化步 | total steps | `ceil(len(dataloader)/grad_accum) × epochs`（`max_steps>0` 时覆盖）。**换卡数会改变它 → 改变整条 lr 曲线**。跨卡数可比要固定 `max_steps`。 |
| `warmup_ratio` / `warmup_steps` | 预热 | 同时设时 `warmup_steps` 优先。Transformer 训练初期不稳，没有 warmup 常发散。 |
| `load_best_model_at_end` | 结束时回载最佳 | **三件套依赖**：+`eval_strategy`(≠no) +`save_strategy`(一致) +`metric_for_best_model`(+方向)。`save_total_limit` 建议 ≥2。 |
| `greater_is_better` | 指标方向 | 忘了设且指标是 loss → 会选到**最差**的 checkpoint。永远显式写。 |
| `gradient_checkpointing` | 梯度检查点 | 省激活显存，慢 20–30%。开了要设 `model.config.use_cache=False`。 |
| `eval_accumulation_steps` | 评估累积 | 分批把预测搬到 CPU。不设的话大评估集会 OOM（**训练正常、评估崩**）。 |
| `remove_unused_columns` | 删除未用列 | 默认 True，会吃掉自定义 collator 需要的字段 → 自定义时设 False。 |
| `group_by_length` | 按长度分组 | 见数据层。吞吐提升可达数倍。 |
| `optim` | 优化器 | `adamw_torch_fused`（快）/ `adafactor`（省）/ `paged_adamw_8bit`（QLoRA 标配）。 |
| checkpoint 内容 | checkpoint contents | 权重 + **optimizer.pt（Adam 的 m/v，约权重 4 倍）** + scheduler + rng_state + trainer_state。总计约权重的 3–5 倍。 |
| `resume_from_checkpoint` | 断点续训 | 恢复**全部**状态（含动量与调度器进度）。只 `from_pretrained` 则等于用新优化器重新开始。 |
| `TrainerCallback` | 回调 | 能读状态、改控制流（`should_stop`/`should_evaluate`），**不能改梯度或权重**——那要覆盖 `compute_loss`/`training_step`。 |
| `EarlyStoppingCallback` | 早停 | **必须配 `load_best_model_at_end=True`**，否则停在「连续 N 次没进步」的点而非最好的点。 |

## PEFT / TRL

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| LoRA | 低秩适配 | 冻结 `W`，训练 `ΔW = (α/r)BA`。`B` **初始化为 0** → 训练从原模型连续出发，无初始跳崖。 |
| `r` | 秩 | 容量旋钮。风格/格式适配 8 够用；领域知识注入常要 32+。 |
| `lora_alpha` / `α/r` | 缩放 | 实际缩放是 `α/r`。作用是「换 r 时不必重调 lr」→ **应固定 α/r 比值（如 α=2r），不要固定 α**。 |
| `target_modules` | 目标模块 | **覆盖面比秩更重要**（同预算下「小 r + 全部线性层」优于「大 r + 仅 q,v」）。名字是模型特定的（Llama `q_proj…` / BERT `query…` / GPT-2 `c_attn`）；可用 `"all-linear"`。 |
| `task_type` | 任务类型 | 填错会**冻住新初始化的头**（做分类却填 `CAUSAL_LM`）→ 准确率卡住且怎么调都不动。 |
| `merge_and_unload()` | 合并卸载 | `W ← W + (α/r)BA`。数值等价、推理零开销、可给 vLLM；但**LoRA 分支消失、不能继续 LoRA 训练**。规则：实验期不合并、上线时合并。 |
| multi-adapter | 多适配器 | 一个基座 + N 个几十 MB adapter，服务 N 个任务。`set_adapter()` 切换近乎零成本；vLLM 已支持同 batch 混合。 |
| QLoRA | 4-bit LoRA | **四个组件**：NF4 量化 + 双重量化 + 分页优化器 + LoRA 在量化权重上。显存最低但**训练慢**（60–70% 速度）。 |
| `prepare_model_for_kbit_training` | k-bit 训练准备 | 转 LayerNorm 到 fp32、开 gradient checkpointing、让梯度能流过量化层。**漏掉会 loss 不降或梯度为 None**。 |
| chat template | 对话模板 | 每个指令模型自己的格式（Llama-3 / ChatML / Mistral 各不同）。必须用 `tokenizer.apply_chat_template()`，手写拼接几乎一定出错。 |
| completion-only loss | 只对回答计损失 | SFT 的核心。不掩 prompt 会让模型**同时学生成用户提问**（loss 更低但推理时自己编下一句）。`response_template` 与 template 不一致 → 整条样本零信号且不报错。 |
| `packing` | 序列打包 | 多条短样本拼成定长，吞吐可翻倍。代价：跨样本注意力需正确隔离；**改变样本权重**（长样本权重变大）。长度差异大时别开。 |
| DPO | 直接偏好优化 | 用成对偏好数据直接优化策略。**必须先 SFT**；`ref_model=None`+LoRA 可省一份模型（禁用 adapter 即参考）。 |
| `beta` (DPO) | KL 约束强度 | 常用 0.1（区间 0.01–0.5）。两端梯度都小（太小学不动、太大饱和）。调它时必须同时监控非目标能力。 |
| 长度偏差 | length bias | 偏好数据里 chosen 系统性更长 → DPO 学到「更长 = 更好」。缓解：`loss_type="ipo"`、长度归一化、数据侧平衡。 |

## 分发与调用 · Accelerate, Hub & API

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| `Accelerator.prepare` | 准备 | `.to(device)` + 包 DDP/FSDP + **换掉 dataloader 的 sampler 做分布式切分**（batch_size 是每进程的）。 |
| `accelerator.accumulate` | 累积上下文 | 自动在非同步步用 `no_sync()`，**省掉 (accum−1)/accum 的梯度通信**。自己写 DDP 循环常漏。 |
| `gather_for_metrics` | 收集指标 | 比裸 `gather` 多做一件事：**裁掉分布式采样为整除而重复的样本**。不用它会让多卡评估指标有偏。 |
| `unwrap_model` | 解包 | 保存前必须调用。否则键名带 `module.` 前缀 → **全部 missing** → 模型等于随机初始化。 |
| `wait_for_everyone` | 同步屏障 | 保存/评估/写文件前后需要，否则 rank 0 还没写完别的 rank 就去读。 |
| 指数退避 + 抖动 | exponential backoff + jitter | `min(cap, base·2^k) × U(0.5,1.5)`。**抖动不是可选的**——它防惊群（thundering herd），能把重试峰值降数倍。 |
| `Retry-After` | 重试等待头 | 429 响应里可能带它。**优先尊重它**，没有才用退避。 |
| 可重试 vs 不可重试 | retryable | 可重试：408/429/5xx。**不可重试：400/401/403/404**（重试一万次也一样错，要报出来）。 |
| RPM / TPM | 每分钟请求/token 数 | 双维度限流。**真正的瓶颈通常是 TPM**（RPM=3500 但 TPM 只允许 60 请求/分是常见情形）。 |
| 预扣-结算 | reserve-settle | 按预估 token 预扣、结束后按实际用量退还。让「先限流后知道实际用量」成为可能。 |
| `Idempotency-Key` | 幂等键 | 让重试不产生重复副作用/重复扣费；对 LLM 还能省下一整次生成。 |
| `stream_options.include_usage` | 流式带 usage | **默认流式不返回 usage** → 不开就无法回答「这次花了多少 token」。 |
| 流式增量拼接 | delta accumulation | `delta.content` 可能为 `None`（首个 chunk 只有 role），**必须判 None 再拼**。 |
| tool calling vs 结构化输出 | tool calling vs structured output | 前者是**多轮协议**（模型说要调什么、你执行并回传）；后者只保证输出符合 schema，没有函数要执行。 |
| prompt caching | 前缀缓存 | 固定的系统提示放在最前面可命中缓存、显著省钱。是最便宜的一个优化。 |
| 上下文预算 | context budget | `L_model − L_sys − 历史 − 生成预留`。多轮会越来越紧；四种策略（滑窗/摘要/检索/硬失败）各有代价，但**必须先能算出这个数**。 |
"""

REFERENCES = r"""
# 参考清单 · References（HuggingFace 生态与 API 实操）

> 本课是**接口课与手艺课**，所以参考清单以**官方文档与源码**为主（它们才是权威），论文只列那些参数背后的原始出处。
> 先读 ★ 标记的必读。与相邻课程的分工：**C01/C20/C49** 讲模型结构，**C02/C22/C23** 讲后训练算法，
> **C21/C43** 讲数据，**C24/C48** 讲部署，**C37/C40** 讲实验管理与研究方法；**本课讲这些原理落到生态的具体手艺**。

## transformers 核心 · Loading & Generation
- ★ **transformers 文档，_Auto Classes_** — `Auto*` 的分发机制与自定义注册。读完你会发现它就是「读 `config.json` 的 `model_type` 查一次字典」，不神奇。
- ★ **transformers 文档，_Models_（`from_pretrained` 的完整参数）** — `torch_dtype` / `device_map` / `low_cpu_mem_usage` / `ignore_mismatched_sizes` / `output_loading_info` / `revision` 的准确语义。本模块 01 的一手来源。
- ★ **transformers 源码 `modeling_utils.py::_load_pretrained_model`** — 讲解里「六步」的第 ⑤ 步（权重键名匹配）全部逻辑在这里。**这是本课最推荐读的一段源码**：读完你就再也不会被 `missing_keys` 困惑。
- ★ **transformers 文档，_Generation Strategies_ 与 `GenerationConfig` API** — `do_sample` 与采样参数的生效条件、beam 相关参数、`max_new_tokens` vs `max_length`。头号误用（temperature 不生效）的官方说明在这里。
- **transformers 源码 `generation/utils.py::_sample` 与 `LogitsProcessor` 家族** — 采样与约束解码的实现。想写自定义解码策略必读。
- **PyTorch 文档，_Automatic Mixed Precision_** — fp16 与 bf16 的数值细节、GradScaler 为什么存在。理解「训练 nan 就换 bf16」这条经验的根据。
- **safetensors 格式规范（GitHub 仓库 README + 设计文档）** — header JSON + 张量字节的布局；为什么它能零拷贝、能部分加载、且不执行代码。

## 数据层 · Tokenizers & Datasets
- ★ **tokenizers 文档，_The tokenization pipeline_ 与 _Encoding_** — `offsets` / `word_ids()` / `sequence_ids()` 的准确定义。本课模块 02 的核心依据；做 QA 或 NER 前必读。
- ★ **transformers 文档，_Preprocess_ 与 _Token classification_ / _Question answering_ 任务教程** — 子词标签对齐与 span 后处理的官方标准写法（含滑窗合并）。它们就是模块 02 那两个「用途」的完整版。
- ★ **datasets 文档，_Process_** — `map` 的全部参数，尤其 `batched` / `batch_size` / `num_proc` / `remove_columns` / `fn_kwargs` 的交互。
- ★ **datasets 文档，_Cache management_** — 指纹机制如何计算、什么时候会误命中、`load_from_cache_file` 的作用。解释了「改了函数却没生效」的困惑。
- **datasets 文档，_Stream_** — `IterableDataset` 的能力边界（无 `len()`、缓冲区打乱、多 worker 切分）。
- **transformers 文档，_Data Collator_ API** — 五种 collator 的行为差异。**强烈建议读 `DataCollatorForLanguageModeling` 的源码**：C49 讲的 80/10/10 就是那三行。
- **Apache Arrow 文档（列式格式与内存映射）** — 理解 `datasets` 为什么能用几百 MB 内存处理几百 GB 数据。

## 训练层 · Trainer
- ★ **transformers 文档，_Trainer_ 与 _TrainingArguments_** — 通读一遍参数名（不用记住），建立「遇到问题知道去查哪个」的索引。
- ★ **transformers 源码 `trainer.py::_inner_training_loop`** — **本课最推荐读的第二段源码**。讲解第一节那个骨架就是它；读一遍胜过读十篇教程，尤其能看清 `loss / grad_accum`、`global_step` 的递增位置、以及 checkpoint 的保存时机。
- ★ **transformers 文档，_Callbacks_** — 十几个钩子与 `TrainerControl` 的语义；以及 Callback 的能力边界（不能改梯度/权重）。
- **transformers 文档，_Methods and tools for efficient training on a single GPU_** — 梯度检查点、8-bit 优化器、`torch_compile`、长度分组的官方对比与显存数据。
- **Goyal et al. 2017, _Accurate, Large Minibatch SGD_** — 学习率线性缩放规则的出处，以及 warmup 为什么必要。理解「有效 batch 变了 lr 要不要跟着变」的根据。
- **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models_** — 种子方差的系统研究。它是「跑几个种子才敢说涨了」这条纪律的依据（C49 模块 03 详读）。

## PEFT / TRL
- ★ **Hu et al. 2021, _LoRA: Low-Rank Adaptation of Large Language Models_** — 重点读 **§7.2 的消融**：`r` 的选择与 `target_modules` 的覆盖面对比，「覆盖更多模块优于更大 r」这个结论出自那里。`α/r` 的动机也在论文里。
- ★ **Dettmers et al. 2023, _QLoRA_** — 四个组件（NF4 / 双重量化 / 分页优化器 / LoRA on quantized）的推导与消融。NF4 为什么针对正态分布设计。
- ★ **Rafailov et al. 2023, _Direct Preference Optimization_** — 推导必读，理解 `beta` 从哪来（它是 RLHF 目标里 KL 系数的直接继承）。
- ★ **peft 文档，_LoRA_ / _Quantization_ / _Adapter injection_** — `LoraConfig` 每个字段、`target_modules="all-linear"`、多 adapter 的加载与切换、`merge_and_unload` 的语义。
- ★ **trl 文档，_SFTTrainer_ 与 _DPOTrainer_** — 数据格式（conversational / prompt-completion / text）、`completion_only_loss`、`packing`、`ref_model=None` 的行为。
- **Meng et al. 2024, _SimPO_ 与 Azar et al. 2024, _IPO_** — 长度偏差的两种修正路线。选 `loss_type` 时的依据。
- **Liu et al. 2024, _DoRA_ / Kalajdzievski 2023, _rsLoRA_ / Hayou et al. 2024, _LoRA+_** — LoRA 变体三例。读它们主要为了理解「变体在改什么维度」，而不是为了记住哪个更好（缺乏控制算力预算的公平对比）。

## 分发与调用 · Accelerate, Hub & API
- ★ **accelerate 文档，_Quicktour_ / _Migrating to Accelerate_ / _Distributed Evaluation_** — 四行改造、`prepare` 做了什么、`gather_for_metrics` 与 `gather` 的区别（第三篇讲得最清楚）。
- ★ **accelerate 文档，_Gradient accumulation_** — `accumulate()` 上下文如何配合 `no_sync()` 省通信。配合 C39 的通信量分析读效果最好。
- ★ **huggingface_hub 文档，_Download files_ 与 _Cache system_** — `revision` 的语义、缓存目录布局（按 commit sha 分 snapshot）。可复现性的基础。
- ★ **OpenAI API Reference：_Chat Completions_ / _Streaming_ / _Function calling_ / _Structured Outputs_ / _Rate limits_** — 五节都要读。尤其 Rate limits 一节的 RPM/TPM 双维度说明与响应头字段，以及 Structured Outputs 与 function calling 的区别。
- ★ **AWS Architecture Blog, _Exponential Backoff and Jitter_（Marc Brooker）** — **抖动为什么必需**的量化论证，附「full jitter / equal jitter / decorrelated jitter」的对比。本课模块 05 的惊群实验就是它的复现。
- **Google SRE Book 第 22 章（_Addressing Cascading Failures_）** — 重试放大与雪崩的机制。读它理解为什么「不可重试的错误绝不能重试」。
- **Hugging Face Blog, _Model Cards_ 与 _Model Card Guidebook_** — 模型卡片该写什么。尤其「输入格式/chat template」这一项，是使用者最需要却最常缺失的信息。

## 跨课衔接 · Cross-course
- **C49 编码器与 Seq2Seq 家族** — **与本课配套**：那门课讲三种 Transformer 形态与预训练目标（为什么有 `-100`、为什么要子词对齐、labels 该怎么移），本课讲怎么用生态实现它们。
- **C02 后训练与对齐** — SFT / RLHF / DPO 的算法原理。本课模块 04 只讲参数与数据格式。
- **C27 模型压缩** — 量化的原理（NF4 为什么这样设计、INT8 的误差分析）。本课只讲 `BitsAndBytesConfig` 怎么填。
- **C39 分布式训练工程** — DDP/FSDP/ZeRO 的通信量与分片策略。本课模块 05 的 `accelerate` 是它的用户界面。
- **C48 LLM 生产部署与云原生** — 服务契约、限流、重试、成本归因的**服务端**视角；本课模块 05 是同一套原理的**客户端**镜像。两课合读效果最好。
- **C37 MLOps / C40 研究方法论** — 实验追踪、超参与 revision 的记录、可复现性纪律。本课强调的「钉死 revision、记录 loading_info、跑多种子」在那两门课有系统展开。
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足，请补充")
