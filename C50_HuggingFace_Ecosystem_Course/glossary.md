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
