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
