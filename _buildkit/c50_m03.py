# -*- coding: utf-8 -*-
"""C50 模块 03 · Trainer 与 TrainingArguments。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–02；C07 的优化器概念；C49 模块 03 的微调配方"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_trainer.ipynb'),
    ("核心参考", "transformers 文档（Trainer / TrainingArguments / Callbacks）、Trainer 源码 <code>inner_training_loop</code>"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("inside", "Trainer 内部到底跑了什么", "".join([
        P("<code>Trainer</code> 常被当成黑箱，但它其实就是一个<strong>写得很仔细的训练循环</strong>。把它的骨架看清，你才知道出问题时该往哪儿看、以及什么时候该弃用它自己写。"),
        ASCII("""trainer.train() 的骨架（省略了分布式与日志细节）

  ① 准备
     DataLoader(train_dataset, collate_fn=data_collator,
                batch_size=per_device_train_batch_size,
                sampler=按 group_by_length / seed 构造)
     optimizer = AdamW(参数分两组：weight_decay 组 与 no_decay 组)
     scheduler = get_scheduler(lr_scheduler_type, warmup_steps, total_steps)
     ⚠️ total_steps = ceil(len(loader) / grad_accum) * num_train_epochs
        （max_steps 若 >0 则覆盖它）

  ② for epoch in range(epochs):
       for step, batch in enumerate(loader):
           ③ loss = model(**batch).loss              # 模型内部算 loss
           ④ loss = loss / grad_accum               # ← 关键：先除再回传
           ⑤ loss.backward()                        # 累积梯度
           if (step + 1) % grad_accum == 0:
               ⑥ clip_grad_norm_(params, max_grad_norm)   # 默认 1.0
               ⑦ optimizer.step(); scheduler.step(); optimizer.zero_grad()
               ⑧ global_step += 1                   # ← **优化步**，不是 batch 数
               ⑨ 到点则：log / evaluate / save_checkpoint

  ⑩ 结束：load_best_model_at_end 则回载最佳 checkpoint""")
        ,
        DUAL(
            "看清第 ⑧ 步就解开了一个常见困惑：<strong><code>logging_steps</code> / <code>eval_steps</code> / <code>save_steps</code> 数的是<em>优化步</em>（global_step），不是 batch 数</strong>。<code>grad_accum=8</code> 时，跑了 800 个 batch 才是 100 个 global_step。<em>这就是为什么「我设了 <code>logging_steps=10</code> 但半天不打日志」——因为你的 <code>grad_accum</code> 很大。</em>",
            "第 ④ 步也值得注意：<strong>loss 在 backward 之前被除以 <code>grad_accum</code></strong>。这是为了让累积 N 个 micro-batch 的梯度<em>等价于</em>一个 N 倍大 batch 的梯度（因为 loss 默认是 batch 内均值）。如果你自己写循环忘了这一步，有效学习率会被放大 N 倍——<em>症状是「梯度累积一开就发散」</em>。反过来，如果你的 loss 是 <code>reduction='sum'</code>，就<strong>不</strong>该除。这个细节在自定义 <code>compute_loss</code> 时特别容易搞错。",
        ),
        CALLOUT("intuition", "什么时候该弃用 <code>Trainer</code> 自己写循环？判据是：<strong>当你需要在一个训练步内做「非标准」的事情时</strong>——比如多个模型交替更新（GAN、RLHF 的 actor-critic）、需要在 backward 之间插入自定义操作、或者每步的数据依赖上一步的输出（on-policy 采样）。<em>反过来，只要你的训练是「取一个 batch、算一个 loss、更新一次」，<code>Trainer</code> 就够用，而且它处理好的边角（断点续训、分布式、日志、混合精度）你自己写要花很久才能同样可靠。</em>"),
    ])),
    ("effective", "有效 batch：三个数相乘才是你关心的那个量", "".join([
        MATH("B_{eff} = \\texttt{per\\_device\\_train\\_batch\\_size} \\times \\texttt{gradient\\_accumulation\\_steps} \\times n_{devices}"),
        P("这是 <code>TrainingArguments</code> 里<strong>最常被搞混的一组参数</strong>。三个数的组合决定了：优化器看到的实际 batch、显存占用、以及吞吐。"),
        TABLE(["组合", "有效 batch", "显存", "吞吐", "何时选"], [
            ["<code>bs=32, accum=1, dev=1</code>", "32", "高", "<strong>最高</strong>", "显存够时的首选"],
            ["<code>bs=8, accum=4, dev=1</code>", "32", "低", "略低", "<strong>显存不够时的标准换法</strong>"],
            ["<code>bs=1, accum=32, dev=1</code>", "32", "<strong>最低</strong>", "低（GPU 利用率差）", "极端显存受限"],
            ["<code>bs=8, accum=1, dev=4</code>", "32", "每卡低", "<strong>最高</strong>（并行）", "有多卡时"],
        ]),
        P("四行的<strong>有效 batch 完全相同</strong>（都是 32），数学上等价（对 Transformer 而言——用 BatchNorm 的模型不等价，但 Transformer 用 LayerNorm，无此问题）。选哪一行只看显存与吞吐。"),
        CALLOUT("warn", "但有三个<strong>真实的不等价之处</strong>要知道：<strong>①dropout 的随机性</strong>——micro-batch 拆分改变了 dropout mask 的分布，理论上有微小差异（实践中可忽略）。<strong>②<code>eval_accumulation_steps</code> 与评估显存</strong>——评估时默认把所有预测攒在 GPU 上再算指标，大数据集会 OOM；设了它才会分批搬到 CPU。<strong>③日志里的 loss 是 micro-batch 的均值</strong>，不是有效 batch 的——所以梯度累积下日志 loss 的方差会更大，看起来更抖，但这不代表训练不稳。"),
        H3("学习率与有效 batch 的关系"),
        P("有效 batch 变了，学习率通常要跟着变。两条经验规则："),
        UL([
            "<strong>线性缩放</strong>：<code>lr ∝ B_eff</code>。来自 SGD 的理论（Goyal et al. 2017 的 ImageNet in 1 Hour），在<em>大 batch 训练</em>时用得多。",
            "<strong>平方根缩放</strong>：<code>lr ∝ √B_eff</code>。对 Adam 类自适应优化器更常见，因为 Adam 已经对梯度做了归一化。<em>微调场景通常用这条，或者干脆不调</em>（微调的 batch 范围变化不大）。",
        ]),
        P("实践建议：<strong>微调时先固定 <code>lr=2e-5</code> 这类常用值，只在有效 batch 变化超过 4 倍时才按 √ 规则调</strong>。把学习率与 batch 一起扫是个昂贵且常常不必要的做法（C40 有关于实验设计的系统讨论）。"),
    ])),
    ("args", "TrainingArguments：按「你会遇到的问题」重排", "".join([
        P("<code>TrainingArguments</code> 有一百多个参数。文档按字母排，这里按<strong>你会遇到的问题</strong>排。"),
        TABLE(["你的问题", "相关参数", "要点"], [
            ["<strong>显存不够</strong>", "<code>per_device_train_batch_size</code> ↓ + <code>gradient_accumulation_steps</code> ↑<br><code>gradient_checkpointing=True</code><br><code>bf16=True</code><br><code>optim=\"adamw_torch_fused\"</code> / <code>\"adafactor\"</code> / <code>\"paged_adamw_8bit\"</code>", "checkpointing 省激活显存但慢 20–30%；8bit 优化器省 3/4 的优化器状态"],
            ["<strong>训练太慢</strong>", "<code>bf16=True</code>、<code>group_by_length=True</code>、<code>dataloader_num_workers</code>、<code>torch_compile=True</code>", "先确认瓶颈在 GPU 还是数据加载（看 GPU 利用率）"],
            ["<strong>loss 变 nan</strong>", "<code>bf16</code> 替代 <code>fp16</code>、<code>max_grad_norm</code>、<code>learning_rate</code> ↓、<code>warmup_ratio</code> ↑", "<strong>fp16→bf16 是第一反应</strong>（动态范围问题）"],
            ["<strong>过拟合</strong>", "<code>num_train_epochs</code> ↓、<code>weight_decay</code>、<code>label_smoothing_factor</code>、<code>load_best_model_at_end</code>+<code>EarlyStoppingCallback</code>", "微调 2–4 epoch 通常够（C49 模块 03）"],
            ["<strong>要断点续训</strong>", "<code>save_steps</code>、<code>save_total_limit</code>、<code>resume_from_checkpoint</code>", "checkpoint 含优化器与调度器状态，比只存权重大 3–4 倍"],
            ["<strong>要选最好的 checkpoint</strong>", "<code>load_best_model_at_end=True</code>、<code>metric_for_best_model</code>、<code>greater_is_better</code>", "<strong>必须同时设 <code>eval_strategy</code> 与 <code>save_strategy</code> 且两者一致</strong>"],
            ["<strong>可复现</strong>", "<code>seed</code>、<code>data_seed</code>、<code>full_determinism=True</code>", "完全确定性会明显变慢；通常只在排查 bug 时开"],
        ]),
        CALLOUT("danger", "<p><strong>三个高频配置错误</strong>：<strong>①<code>load_best_model_at_end=True</code> 但 <code>eval_strategy=\"no\"</code></strong>——没有评估就没有「最佳」，会报错或静默不生效。<strong>②<code>metric_for_best_model=\"loss\"</code> 但忘了 <code>greater_is_better=False</code></strong>——库会去选 loss <em>最大</em> 的 checkpoint，也就是最差的那个。<em>（注：对以 <code>loss</code> 结尾的指标名，新版本会自动推断方向，但显式写出来永远更安全。）</em><strong>③<code>save_total_limit</code> 太小配上 <code>load_best_model_at_end</code></strong>——最佳 checkpoint 可能已被删掉；库会尽力保留它，但设成 1 仍可能出问题，建议至少 2。</p>", "配置错误三连"),
        H3("学习率调度：三个参数的交互"),
        CODE("""TrainingArguments(
    learning_rate=2e-5,
    lr_scheduler_type="cosine",   # linear / cosine / constant_with_warmup / ...
    warmup_ratio=0.06,            # 占总步数的比例（与 warmup_steps 二选一）
    # warmup_steps=500,           # 绝对步数；**同时设两个时 warmup_steps 优先**
    num_train_epochs=3,
    # max_steps=-1,               # >0 时覆盖 num_train_epochs
)"""),
        P("要注意 <strong>总步数的计算</strong>：<code>total = ceil(len(dataloader) / grad_accum) × epochs</code>。调度器按总步数规划衰减曲线，所以<em>如果你中途改了 <code>grad_accum</code> 或数据量，衰减曲线就变了</em>——这是「同样的超参换个机器结果不一样」的一个隐蔽来源（不同卡数 → 不同 <code>len(dataloader)</code> → 不同总步数）。"),
    ])),
    ("metrics", "compute_metrics 与 Callback：两个扩展点", "".join([
        H3("compute_metrics 的签名与陷阱"),
        CODE("""def compute_metrics(eval_pred):
    logits, labels = eval_pred            # 都是 numpy array（已从 GPU 搬回）
    preds = logits.argmax(-1)
    # ⚠️ token 分类要先过滤 -100
    mask = labels != -100
    return {"accuracy": (preds[mask] == labels[mask]).mean()}

trainer = Trainer(..., compute_metrics=compute_metrics)"""),
        TABLE(["陷阱", "症状", "解法"], [
            ["<strong>忘了过滤 <code>-100</code></strong>", "指标异常低（把 padding 也算进去了）", "<code>mask = labels != -100</code>"],
            ["<strong>模型返回 tuple 而非单个 logits</strong>", "<code>logits</code> 是个 tuple，argmax 报错", "用 <code>preprocess_logits_for_metrics</code> 提前收缩，或在函数里解包"],
            ["<strong>评估时 OOM</strong>", "评估阶段崩溃（训练正常）", "<code>eval_accumulation_steps=N</code> 分批搬到 CPU"],
            ["<strong>生成式任务用 argmax</strong>", "指标毫无意义（BLEU/ROUGE 需要生成的文本）", "<code>Seq2SeqTrainer</code> + <code>predict_with_generate=True</code>"],
        ]),
        H3("Callback：在训练循环的钩子上挂东西"),
        P("<code>TrainerCallback</code> 提供了十几个钩子（<code>on_train_begin</code>、<code>on_step_end</code>、<code>on_evaluate</code>、<code>on_save</code>…）。它<strong>能读状态、能改控制流，但不能改梯度或权重</strong>——那些要靠子类化 <code>Trainer</code> 覆盖 <code>compute_loss</code> / <code>training_step</code>。"),
        UL([
            "<strong>典型用途</strong>：早停（<code>EarlyStoppingCallback</code>）、自定义日志、按条件调整超参、在评估后跑一段自定义分析、把指标推到外部系统。",
            "<strong>控制流</strong>：通过修改 <code>control.should_training_stop</code> / <code>should_evaluate</code> / <code>should_save</code> 来干预。",
            "<strong>边界</strong>：想改 loss 的计算方式 → 覆盖 <code>compute_loss</code>；想改优化器 → 覆盖 <code>create_optimizer</code>；想在 backward 前后插东西 → 覆盖 <code>training_step</code>。<em>Callback 不是万能的扩展点，搞清边界能省很多时间。</em>",
        ]),
        CALLOUT("intuition", "关于 <code>EarlyStoppingCallback</code> 有一个必须知道的依赖：<strong>它需要 <code>load_best_model_at_end=True</code> 才有意义</strong>，否则你停在了「连续 N 次没进步」的那个点，而不是最好的那个点。三个参数要配套出现：<code>eval_strategy=\"steps\"</code>（或 epoch）、<code>load_best_model_at_end=True</code>、<code>metric_for_best_model</code>。<em>缺一个，早停就变成了「提前结束在一个较差的点」。</em>"),
    ])),
    ("checkpoint", "checkpoint 与断点续训：存了什么、恢复了什么", "".join([
        ASCII("""checkpoint-500/
├── model.safetensors            模型权重（fp16 时约 N×2 字节）
├── optimizer.pt                 **优化器状态**（Adam 的 m 与 v，约 N×8 字节）← 最大的一块
├── scheduler.pt                 调度器状态（当前 step）
├── rng_state.pth                随机数状态（Python/numpy/torch/CUDA）
├── trainer_state.json           global_step / epoch / 日志历史 / best_metric
├── training_args.bin            当次训练的全部参数
└── (可选) scaler.pt              fp16 的 GradScaler 状态

⚠️ 所以一个 checkpoint 约是权重大小的 **3-5 倍**。7B 模型 fp16 全量训练的
   单个 checkpoint 约 14(权重) + 56(优化器) = 70 GB。save_total_limit 不设会撑爆磁盘。

resume_from_checkpoint 恢复的是**全部**上述状态 -> 训练可以逐 step 复现；
只加载 model.safetensors（from_pretrained）则**丢掉优化器动量与调度器进度**
-> 「继续训练」实际上是「用一个新的优化器重新开始」，曲线会有明显跳变。""")
        ,
        DUAL(
            "这个区别在实践中很重要。<strong>「我想在别人的 checkpoint 上继续训练」有两种完全不同的含义</strong>：如果你要<em>接着他的训练进度往下跑</em>，必须有完整的 checkpoint 目录（含 <code>optimizer.pt</code>）；如果你只是要<em>在他的权重上做一次新的微调</em>，那 <code>from_pretrained</code> 就够了，而且你<strong>应该</strong>用新的优化器（旧动量对新任务是噪声）。",
            "还有一个容易忽略的点：<strong>恢复训练要求数据顺序也能恢复</strong>。<code>Trainer</code> 通过保存 <code>rng_state</code> 与 <code>global_step</code> 来跳过已消费的 batch，但这依赖 <code>Dataset</code> 支持索引与确定性采样。<em>流式数据集（<code>IterableDataset</code>）的精确恢复要复杂得多</em>——需要数据集本身支持「从第 N 个样本继续」，这在 <code>datasets</code> 的流式实现里支持有限（Mosaic StreamingDataset 在这方面做得更完善，C43 有讨论）。",
        ),
        CALLOUT("warn", "一条实用的磁盘纪律：<strong><code>save_total_limit=2</code> + <code>save_steps</code> 设得别太密</strong>。见过太多次「训练跑了两天，磁盘满了，最后一个 checkpoint 写坏了」。另外如果你只需要最终权重（不需要续训），可以在训练后手动删掉各 checkpoint 里的 <code>optimizer.pt</code>——能省掉 2/3 的空间。"),
    ])),
    ("pitfalls", "十个高频坑（附症状）", "".join([
        TABLE(["#", "坑", "症状", "解法"], [
            ["1", "<code>logging_steps</code> 数的是优化步不是 batch", "「设了 10 但半天不打日志」", "除以 <code>grad_accum</code> 来理解"],
            ["2", "自定义 <code>compute_loss</code> 忘了除 <code>grad_accum</code>", "梯度累积一开就发散", "<code>loss / self.args.gradient_accumulation_steps</code>（或用 <code>return_outputs</code> 约定）"],
            ["3", "<code>remove_unused_columns=True</code>（默认）吃掉了你的自定义列", "自定义 collator 收不到某个字段", "设 <code>remove_unused_columns=False</code>"],
            ["4", "<code>labels</code> 列名不叫 <code>labels</code>", "loss 是 None，训练不动", "重命名列，或在模型 forward 里接受你的名字"],
            ["5", "评估阶段 OOM（训练正常）", "跑到第一次 eval 就崩", "<code>eval_accumulation_steps</code> + <code>per_device_eval_batch_size</code> ↓"],
            ["6", "<code>fp16</code> 下 loss nan", "训练几百步后变 nan", "换 <code>bf16</code>；或降 lr、加 warmup"],
            ["7", "<code>load_best_model_at_end</code> 没配套 <code>eval_strategy</code>", "报错或不生效", "三个参数配套出现"],
            ["8", "<code>gradient_checkpointing</code> 与 <code>use_cache</code> 冲突", "警告 + 变慢或报错", "<code>model.config.use_cache=False</code>"],
            ["9", "多卡下 <code>per_device</code> 被误当成总 batch", "有效 batch 是预期的 N 倍", "记住要乘卡数"],
            ["10", "<code>Trainer</code> 会把模型移到 GPU，但你的自定义模块没跟着", "device mismatch 报错", "所有子模块都注册为 <code>nn.Module</code> 的属性"],
        ]),
        CALLOUT("intuition", "这十个坑里有个共同规律：<strong>它们大多来自「参数之间的隐式依赖」</strong>——<code>logging_steps</code> 依赖 <code>grad_accum</code>、<code>load_best_model_at_end</code> 依赖 <code>eval_strategy</code>、<code>gradient_checkpointing</code> 依赖 <code>use_cache</code>。<em>所以本模块最实用的产出是一个「配置校验函数」</em>：把这些依赖写成断言，在 <code>Trainer</code> 构造之前跑一遍。notebook 会让你实现它。"),
    ])),
    ("ledger", "算一笔账：训练时长与 checkpoint 磁盘", "".join([
        MATH("\\text{总优化步} = \\left\\lceil \\frac{N_{samples}}{B_{eff}} \\right\\rceil \\times E, \\qquad T \\approx \\text{总优化步} \\times \\frac{B_{eff}}{\\text{吞吐(样本/秒)}}"),
        TABLE(["配置", "N", "B_eff", "epochs", "总优化步", "checkpoint 数（save_steps=500）"], [
            ["小数据微调", "5,000", "32", "3", "≈ 471", "0（跑不到 500 步！）"],
            ["中等微调", "50,000", "32", "3", "≈ 4,689", "9"],
            ["大规模 SFT", "500,000", "128", "2", "≈ 7,813", "15"],
        ]),
        P("第一行揭示了一个很常见的困惑：<strong><code>save_steps=500</code> 但训练只有 471 步 → 一个 checkpoint 都不会存</strong>（除非 <code>save_strategy=\"epoch\"</code>）。同理 <code>eval_steps=500</code> 会导致「从头到尾没有评估」，进而让 <code>load_best_model_at_end</code> 失效。<em>小数据集上应该用 <code>save_strategy=\"epoch\"</code> 而不是 steps。</em>"),
        P("磁盘账："),
        MATH("\\text{单 checkpoint} \\approx N_{params}\\times b_{w} + N_{trainable}\\times(b_{w} + 8), \\qquad \\text{总磁盘} = \\text{单个} \\times \\texttt{save\\_total\\_limit}"),
        TABLE(["模型", "训练方式", "单 checkpoint", "<code>save_total_limit=3</code>"], [
            ["BERT-base (110M)", "全量 fp16", "≈ 1.3 GB", "≈ 4 GB"],
            ["Llama-8B", "全量 bf16", "≈ 96 GB", "<strong>≈ 288 GB</strong>"],
            ["Llama-8B", "LoRA (r=16)", "≈ 0.2 GB", "≈ 0.6 GB"],
        ]),
        P("这张表解释了 LoRA 在工程上的另一个巨大好处（除了显存）：<strong>checkpoint 从 96 GB 变成 0.2 GB</strong>。这让「保存二十个不同实验的 checkpoint」从不可能变成毫无压力，直接改变了实验迭代的方式。模块 04 会详细讲。"),
        CALLOUT("intuition", "把本模块浓缩成一句话：<strong><code>Trainer</code> 的复杂度不在任何单个参数，而在参数之间的<em>乘法关系</em>与<em>隐式依赖</em></strong>。乘法关系（有效 batch = 三个数相乘、总步数 = 样本数 ÷ 有效 batch × epochs）决定了训练的实际规模；隐式依赖（logging 依赖 accum、best model 依赖 eval）决定了配置对不对。<em>写一个配置校验函数把这些关系显式化，是本模块最值钱的产出。</em>"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>Trainer 与更底层框架的分层</strong>：<code>Trainer</code> 之下是 <code>accelerate</code>（模块 05），旁边有 <code>lightning</code>、<code>composer</code>、以及各家自研循环。抽象边界仍在移动——比如 FSDP/DeepSpeed 的配置到底该在哪一层表达，目前分散在 <code>TrainingArguments</code>、<code>accelerate config</code> 与 JSON 配置文件里，是实际的痛点。",
            "<strong>优化器的显存创新</strong>：8-bit Adam、Adafactor、Lion、以及 GaLore / LoMo 这类「低秩梯度投影」方法都在压缩优化器状态。哪些在什么规模下无损，缺乏系统对比；<code>optim=</code> 的选项还在增加。",
            "<strong>确定性与可复现的代价</strong>：<code>full_determinism=True</code> 会关掉一批快速 kernel、显著变慢。在多卡+混合精度下做到逐 bit 复现基本不现实（浮点归约顺序不定）。<em>「可复现」在实践中只能是「统计上可复现」</em>，这与 C40 强调的实验纪律有张力，尚无好答案。",
            "<strong>流式数据的精确恢复</strong>：断点续训要能「从第 N 个样本继续」，这对内存映射数据集容易、对流式数据集很难。规范尚未统一，各家实现语义不同。",
            "<strong>训练过程的可观测性</strong>：现在的日志主要是 loss 与 lr，但真正有诊断价值的是梯度范数分布、各层更新幅度、激活统计、以及 token 级的 loss 分布。这些需要自己写 Callback 采集，缺少开箱方案（C37 的实验追踪与此互补）。",
        ]),
        CALLOUT("paper", "必读：transformers 文档的 <em>Trainer</em>、<em>TrainingArguments</em>（通读一遍参数名，不用记住）、<em>Callbacks</em> 三篇；源码上强烈建议读 <code>trainer.py</code> 的 <code>_inner_training_loop</code>——它就是讲解第一节那个骨架，读一遍胜过读十篇教程。原理侧：C07（优化器）、C21（大规模训练的稳定性）、C49 模块 03（微调配方与种子方差）、C37（实验追踪与 CI 门禁）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · Trainer 与 TrainingArguments（手写完整训练循环 + 配置校验器）

目标：把 **Trainer 的训练循环 → 梯度累积的等价性 → 学习率调度 → checkpoint 与恢复 → 配置的隐式依赖** 从零写一遍，
并产出一个**配置校验函数**（本模块最值钱的交付物）。

路线：手写训练循环 → 梯度累积等价性对拍 → 忘除 grad_accum 的后果 → 调度器与总步数 →
global_step vs batch 数 → checkpoint 存了什么/恢复了什么 → 配置校验器 → ✏️ 练习 → 📖 答案 → 🧪 时长与磁盘胶囊。

> 心智模型：**Trainer 的复杂度不在单个参数，而在参数之间的「乘法关系」与「隐式依赖」。**"""),
    md("""## 1 · 手写训练循环：Trainer 的骨架

一个能跑的最小 Trainer 只需要这些。**注意第 ④ 步的 `loss / grad_accum`** 与
**第 ⑧ 步 `global_step` 只在优化时递增**——这两点解释了大量困惑。"""),
    code("""import numpy as np, math, json, os, copy
rng = np.random.default_rng(0)

# ── 一个极简的可训练模型：线性 + softmax（足够验证训练循环的语义）──
class TinyModel:
    def __init__(self, d_in, n_cls, seed=0):
        r = np.random.default_rng(seed)
        self.W = r.normal(size=(d_in, n_cls)) * 0.1
        self.b = np.zeros(n_cls)
        self.grads = {'W': np.zeros_like(self.W), 'b': np.zeros_like(self.b)}
    def zero_grad(self):
        self.grads['W'][:] = 0; self.grads['b'][:] = 0
    def forward_backward(self, X, y, loss_scale=1.0):
        '''返回 loss；梯度**累加**到 self.grads（乘上 loss_scale）。'''
        z = X @ self.W + self.b
        z = z - z.max(1, keepdims=True)
        p = np.exp(z); p /= p.sum(1, keepdims=True)
        n = len(y)
        loss = float(-np.log(p[np.arange(n), y] + 1e-12).mean())
        dz = p.copy(); dz[np.arange(n), y] -= 1; dz /= n
        self.grads['W'] += loss_scale * (X.T @ dz)
        self.grads['b'] += loss_scale * dz.sum(0)
        return loss
    def grad_norm(self):
        return math.sqrt(float((self.grads['W']**2).sum() + (self.grads['b']**2).sum()))
    def clip_grad_norm_(self, max_norm):
        gn = self.grad_norm()
        if gn > max_norm:
            s = max_norm / (gn + 1e-12)
            self.grads['W'] *= s; self.grads['b'] *= s
        return gn
    def params(self): return {'W': self.W, 'b': self.b}

class SGDOpt:
    def __init__(self, model, lr): self.model, self.lr = model, lr
    def step(self, lr=None):
        lr = self.lr if lr is None else lr
        self.model.W -= lr * self.model.grads['W']
        self.model.b -= lr * self.model.grads['b']

def make_data(n=256, d=8, n_cls=3, seed=1):
    r = np.random.default_rng(seed)
    X = r.normal(size=(n, d))
    w = r.normal(size=(d, n_cls))
    y = (X @ w).argmax(1)
    return X, y

X, Y = make_data()
print(f'数据: X{X.shape}, y{Y.shape}, 类别 {len(set(Y.tolist()))}')"""),
    code("""def get_scheduler(name, total_steps, warmup_steps, base_lr):
    '''返回 step -> lr 的函数。'''
    def fn(step):
        if warmup_steps > 0 and step < warmup_steps:
            return base_lr * (step + 1) / warmup_steps
        prog = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        prog = min(max(prog, 0.0), 1.0)
        if name == 'linear':   return base_lr * (1 - prog)
        if name == 'cosine':   return base_lr * 0.5 * (1 + math.cos(math.pi * prog))
        if name == 'constant_with_warmup': return base_lr
        raise ValueError(name)
    return fn

def train_loop(X, Y, per_device_bs, grad_accum, epochs, lr=0.5,
               lr_scheduler_type='linear', warmup_ratio=0.0, max_grad_norm=1.0,
               logging_steps=10, seed=0, verbose=False):
    '''复刻 Trainer._inner_training_loop 的骨架。'''
    model = TinyModel(X.shape[1], int(Y.max()) + 1, seed=seed)
    n_batches_per_epoch = math.ceil(len(X) / per_device_bs)
    # ⚠️ 总优化步 = ceil(每 epoch 的 batch 数 / grad_accum) * epochs
    total_steps = math.ceil(n_batches_per_epoch / grad_accum) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    sched = get_scheduler(lr_scheduler_type, total_steps, warmup_steps, lr)

    global_step, logs, r = 0, [], np.random.default_rng(seed)
    model.zero_grad()
    for ep in range(epochs):
        order = r.permutation(len(X))
        micro = 0
        for i in range(0, len(X), per_device_bs):
            idx = order[i:i + per_device_bs]
            # ④ 关键：loss 在 backward 前除以 grad_accum
            model.forward_backward(X[idx], Y[idx], loss_scale=1.0 / grad_accum)
            micro += 1
            if micro % grad_accum == 0 or i + per_device_bs >= len(X):
                gn = model.clip_grad_norm_(max_grad_norm)        # ⑥
                cur_lr = sched(global_step)
                SGDOpt(model, cur_lr).step()                     # ⑦
                model.zero_grad()
                global_step += 1                                  # ⑧ **优化步**
                if global_step % logging_steps == 0:
                    z = X @ model.W + model.b
                    z = z - z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
                    full_loss = float(-np.log(p[np.arange(len(Y)), Y] + 1e-12).mean())
                    logs.append({'step': global_step, 'lr': cur_lr,
                                 'loss': full_loss, 'grad_norm': gn})
                    if verbose:
                        print(f'  step {global_step:>4d} lr {cur_lr:.4f} loss {full_loss:.4f}')
    return model, {'total_steps': total_steps, 'global_step': global_step, 'logs': logs}

m, st = train_loop(X, Y, per_device_bs=32, grad_accum=1, epochs=3, verbose=True)
print(f'\\n预计总优化步 {st["total_steps"]} | 实际 {st["global_step"]}')
assert st['global_step'] == st['total_steps'], '实际步数应等于预算'
assert st['logs'][-1]['loss'] < st['logs'][0]['loss'], 'loss 应下降'
print('✅ 训练循环工作正常')"""),
    md("""## 2 · 梯度累积的等价性：三个数相乘才是有效 batch

$$B_{eff} = \\text{per\\_device} \\times \\text{grad\\_accum} \\times n_{devices}$$

**四种组合的有效 batch 相同、数学上等价。** 用「同一批数据下的梯度」对拍验证。"""),
    code("""def accumulated_grad(X, Y, per_device_bs, grad_accum, seed=0):
    '''在同一批 B_eff 个样本上，用 micro-batch 累积出的总梯度。'''
    m = TinyModel(X.shape[1], int(Y.max()) + 1, seed=seed)
    B_eff = per_device_bs * grad_accum
    Xb, Yb = X[:B_eff], Y[:B_eff]
    m.zero_grad()
    for i in range(0, B_eff, per_device_bs):
        m.forward_backward(Xb[i:i + per_device_bs], Yb[i:i + per_device_bs],
                           loss_scale=1.0 / grad_accum)
    return m.grads['W'].copy()

g_full = accumulated_grad(X, Y, per_device_bs=32, grad_accum=1)
for pd, ga in [(16, 2), (8, 4), (4, 8), (1, 32)]:
    g = accumulated_grad(X, Y, pd, ga)
    diff = float(np.abs(g - g_full).max())
    print(f'per_device={pd:>3d}, accum={ga:>3d} -> B_eff={pd*ga:>3d}, 与整批梯度的最大差 {diff:.2e}')
    assert diff < 1e-10, f'有效 batch 相同时梯度必须一致（差 {diff}）'
print('\\n✅ 对拍通过：**四种组合的梯度完全相同** —— 只是显存与吞吐不同。')
print('   （对 Transformer 成立；用 BatchNorm 的模型不等价，但 Transformer 用 LayerNorm。）')"""),
    code("""# 忘了除 grad_accum 会怎样：有效学习率被放大 N 倍
def accumulated_grad_forgot_divide(X, Y, per_device_bs, grad_accum, seed=0):
    m = TinyModel(X.shape[1], int(Y.max()) + 1, seed=seed)
    B_eff = per_device_bs * grad_accum
    m.zero_grad()
    for i in range(0, B_eff, per_device_bs):
        m.forward_backward(X[i:i + per_device_bs], Y[i:i + per_device_bs],
                           loss_scale=1.0)          # ❌ 忘了 / grad_accum
    return m.grads['W'].copy()

g_ok = accumulated_grad(X, Y, 8, 4)
g_bad = accumulated_grad_forgot_divide(X, Y, 8, 4)
ratio = float(np.abs(g_bad).sum() / np.abs(g_ok).sum())
print(f'忘除 grad_accum 后梯度放大倍数: {ratio:.2f}×  (accum=4)')
assert abs(ratio - 4.0) < 0.01, '梯度会被放大 grad_accum 倍'
print('⚠️  相当于学习率被放大 4 倍 -> **症状：梯度累积一开就发散**。')
print('✅ 自定义 compute_loss 时必须 loss / self.args.gradient_accumulation_steps')
print('   （除非你的 loss 用的是 reduction="sum"，那时不该除。）')"""),
    md("""### `logging_steps` 数的是优化步，不是 batch 数"""),
    code("""for ga in [1, 4, 16]:
    _, s = train_loop(X, Y, per_device_bs=8, grad_accum=ga, epochs=2, logging_steps=5)
    n_batches = math.ceil(len(X) / 8) * 2
    print(f'grad_accum={ga:>2d}: 跑了 {n_batches} 个 batch, 但只有 '
          f'{s["global_step"]} 个 global_step, 打了 {len(s["logs"])} 条日志')

_, s1 = train_loop(X, Y, 8, 1, 2, logging_steps=5)
_, s16 = train_loop(X, Y, 8, 16, 2, logging_steps=5)
assert s1['global_step'] > s16['global_step'] * 8, 'accum 越大，global_step 越少'
assert len(s16['logs']) < len(s1['logs']), '日志条数也随之减少'
print('\\n✅ 这就是「我设了 logging_steps=10 但半天不打日志」的原因 ——')
print('   要打一条日志，需要跑 logging_steps × grad_accum 个 batch。')"""),
    md("""## 3 · 学习率调度：总步数变了，曲线就变了

`total_steps = ceil(len(dataloader) / grad_accum) × epochs`。
**换个卡数 → `len(dataloader)` 变 → 总步数变 → 衰减曲线变** —— 这是「同样超参换机器结果不同」的隐蔽来源。"""),
    code("""def lr_curve(name, total_steps, warmup_ratio, base_lr=1.0):
    ws = int(total_steps * warmup_ratio)
    f = get_scheduler(name, total_steps, ws, base_lr)
    return [f(s) for s in range(total_steps)]

for name in ['linear', 'cosine', 'constant_with_warmup']:
    c = lr_curve(name, 100, 0.1)
    print(f'{name:<24s} 起点 {c[0]:.3f} | 峰值 {max(c):.3f}@step{c.index(max(c))} | 末尾 {c[-1]:.3f}')

lin = lr_curve('linear', 100, 0.1)
cos = lr_curve('cosine', 100, 0.1)
assert lin[0] < lin[10] and abs(lin[9] - 1.0) < 1e-9, 'warmup 期线性升到峰值'
assert lin[-1] < 0.05 and cos[-1] < 0.05, '两者末尾都接近 0'
assert cos[30] > lin[30], 'cosine 在前中段衰减比 linear 慢（两者在中点相交）'
print('\\n✅ warmup 后 linear 匀速降、cosine 先慢后快。微调常用 linear，预训练常用 cosine。')

# 同样的 warmup_ratio，总步数不同 -> 绝对 warmup 步数不同
for nd in [1, 4, 8]:
    n_batches = math.ceil(len(X) / 8 / nd)          # 卡越多，每卡的 batch 数越少
    total = math.ceil(n_batches / 4) * 3
    print(f'{nd} 卡: 每卡 {n_batches} batch/epoch -> 总优化步 {total} -> warmup {int(total*0.06)} 步')
t1 = math.ceil(math.ceil(len(X)/8/1)/4)*3
t8 = math.ceil(math.ceil(len(X)/8/8)/4)*3
assert t1 > t8, '卡数变化会改变总步数 -> 改变整条衰减曲线'
print('\\n⚠️  同样的 TrainingArguments，1 卡与 8 卡的**总步数与衰减曲线完全不同**。')
print('   想要跨卡数可比，应该固定 max_steps 而不是 num_train_epochs。')"""),
    md("""## 4 · checkpoint：存了什么、恢复了什么

完整 checkpoint 含**优化器状态**（Adam 的 m/v，约权重的 4 倍）。
只加载权重 = 丢掉动量与调度器进度 = 「用新优化器重新开始」。"""),
    code("""class AdamOpt:
    def __init__(self, model, lr, b1=0.9, b2=0.999, eps=1e-8):
        self.m = {k: np.zeros_like(v) for k, v in model.params().items()}
        self.v = {k: np.zeros_like(v) for k, v in model.params().items()}
        self.t, self.lr, self.b1, self.b2, self.eps = 0, lr, b1, b2, eps
    def step(self, model, lr=None):
        lr = self.lr if lr is None else lr
        self.t += 1
        for k, p in model.params().items():
            g = model.grads[k]
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * g
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * g * g
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            p -= lr * mh / (np.sqrt(vh) + self.eps)
    def state_dict(self): return {'m': {k: v.copy() for k, v in self.m.items()},
                                  'v': {k: v.copy() for k, v in self.v.items()}, 't': self.t}
    def load_state_dict(self, sd):
        self.m = {k: v.copy() for k, v in sd['m'].items()}
        self.v = {k: v.copy() for k, v in sd['v'].items()}; self.t = sd['t']

def save_checkpoint(model, opt, sched_step, rng_state):
    '''对应 checkpoint-N/ 目录里的五个文件。'''
    return {
        'model.safetensors': {k: v.copy() for k, v in model.params().items()},
        'optimizer.pt': opt.state_dict(),
        'scheduler.pt': {'step': sched_step},
        'rng_state.pth': rng_state,
        'trainer_state.json': {'global_step': sched_step},
    }

def checkpoint_bytes(ck):
    def sz(o):
        if isinstance(o, np.ndarray): return o.nbytes
        if isinstance(o, dict): return sum(sz(v) for v in o.values())
        return 8
    return {k: sz(v) for k, v in ck.items()}

model = TinyModel(8, 3, seed=0)
opt = AdamOpt(model, lr=0.1)
for _ in range(20):
    model.zero_grad(); model.forward_backward(X[:32], Y[:32]); opt.step(model)
ck = save_checkpoint(model, opt, 20, {'seed': 0})
sizes = checkpoint_bytes(ck)
print('checkpoint 各部分字节数:')
for k, v in sizes.items(): print(f'  {k:<24s} {v:>8d}')
w = sizes['model.safetensors']; o = sizes['optimizer.pt']
print(f'\\n优化器状态是权重的 {o/w:.1f} 倍 (Adam 存 m 与 v 两份)')
assert o >= 2 * w, 'Adam 的 m+v 至少是权重的 2 倍（fp32 状态时是 4 倍）'"""),
    code("""def continue_with_full_checkpoint(ck, steps=20):
    '''resume_from_checkpoint：恢复权重 + 优化器 + 调度器。'''
    m = TinyModel(8, 3, seed=0)
    for k, v in ck['model.safetensors'].items(): setattr(m, k, v.copy())
    o = AdamOpt(m, lr=0.1); o.load_state_dict(ck['optimizer.pt'])
    losses = []
    for _ in range(steps):
        m.zero_grad(); losses.append(m.forward_backward(X[:32], Y[:32])); o.step(m)
    return losses

def continue_with_weights_only(ck, steps=20):
    '''只 from_pretrained：**丢掉动量与调度器进度**。'''
    m = TinyModel(8, 3, seed=0)
    for k, v in ck['model.safetensors'].items(): setattr(m, k, v.copy())
    o = AdamOpt(m, lr=0.1)                       # 全新的优化器，m=v=0, t=0
    losses = []
    for _ in range(steps):
        m.zero_grad(); losses.append(m.forward_backward(X[:32], Y[:32])); o.step(m)
    return losses

full = continue_with_full_checkpoint(ck)
weights = continue_with_weights_only(ck)
print(f'完整恢复  前 5 步 loss: {[round(x,4) for x in full[:5]]}')
print(f'仅权重恢复 前 5 步 loss: {[round(x,4) for x in weights[:5]]}')
jump_full = abs(full[1] - full[0]); jump_w = abs(weights[1] - weights[0])
print(f'\\n第 1→2 步的 loss 跳变: 完整恢复 {jump_full:.5f} | 仅权重 {jump_w:.5f}')
assert full != weights, '两者轨迹不同'
print('\\n✅ 「在别人的 checkpoint 上继续训练」有两种含义：')
print('   接着他的进度往下跑 -> 必须有完整 checkpoint（含 optimizer.pt）；')
print('   在他的权重上做新的微调 -> from_pretrained 就够，而且**应该**用新优化器')
print('   （旧动量对新任务是噪声）。')"""),
    md("""## 5 · 配置校验器：把隐式依赖变成断言

本模块最值钱的产出。把 `Trainer` 的隐式依赖写成检查，在构造之前跑一遍。"""),
    code("""def validate_training_args(args, n_train_samples=None, n_devices=1):
    '''返回 (errors, warnings)。errors 会让训练必然出问题，warnings 是可能的坑。'''
    E, W = [], []
    pd = args.get('per_device_train_batch_size', 8)
    ga = args.get('gradient_accumulation_steps', 1)
    b_eff = pd * ga * n_devices

    # ① load_best_model_at_end 的三件套依赖
    if args.get('load_best_model_at_end'):
        if args.get('eval_strategy', 'no') == 'no':
            E.append('load_best_model_at_end=True 需要 eval_strategy != "no"')
        if args.get('save_strategy', 'steps') != args.get('eval_strategy', 'no'):
            E.append('load_best_model_at_end 要求 save_strategy 与 eval_strategy 一致')
        if not args.get('metric_for_best_model'):
            W.append('未设 metric_for_best_model，将默认用 loss')
        if args.get('save_total_limit', 3) is not None and args.get('save_total_limit', 3) < 2:
            W.append('save_total_limit < 2 时最佳 checkpoint 可能被删，建议 >= 2')

    # ② metric 方向
    mfb = args.get('metric_for_best_model')
    if mfb and 'greater_is_better' not in args:
        if mfb.endswith('loss'):
            W.append(f'metric_for_best_model="{mfb}" 建议显式设 greater_is_better=False')
        else:
            W.append(f'metric_for_best_model="{mfb}" 建议显式设 greater_is_better=True')
    if mfb and mfb.endswith('loss') and args.get('greater_is_better') is True:
        E.append('loss 类指标配 greater_is_better=True 会选到**最差**的 checkpoint')

    # ③ 步数 vs save/eval 间隔
    if n_train_samples:
        total = math.ceil(math.ceil(n_train_samples / (pd * n_devices)) / ga) \\
                * args.get('num_train_epochs', 3)
        for key in ('save_steps', 'eval_steps'):
            if args.get(key) and args[key] > total:
                W.append(f'{key}={args[key]} > 总优化步 {total} -> 一次都不会触发；'
                         f'小数据集建议用 strategy="epoch"')

    # ④ 精度
    if args.get('fp16') and args.get('bf16'):
        E.append('fp16 与 bf16 不能同时为 True')
    if args.get('fp16') and not args.get('bf16'):
        W.append('fp16 动态范围小、易 nan；若硬件支持优先 bf16')

    # ⑤ gradient_checkpointing 与 use_cache
    if args.get('gradient_checkpointing') and args.get('use_cache', True):
        W.append('gradient_checkpointing=True 时应设 model.config.use_cache=False')

    # ⑥ 有效 batch 与日志密度
    if args.get('logging_steps') and ga > 1:
        W.append(f'logging_steps 数的是**优化步**：每条日志需跑 '
                 f'{args["logging_steps"] * ga} 个 batch')
    if b_eff < 8:
        W.append(f'有效 batch 只有 {b_eff}，梯度噪声大，考虑增大 grad_accum')
    return E, W

bad = {'load_best_model_at_end': True, 'eval_strategy': 'no',
       'metric_for_best_model': 'eval_loss', 'greater_is_better': True,
       'fp16': True, 'bf16': True, 'save_steps': 500,
       'per_device_train_batch_size': 2, 'gradient_accumulation_steps': 1,
       'num_train_epochs': 3}
E, W = validate_training_args(bad, n_train_samples=5000)
print('❌ ERRORS:');  [print('   -', e) for e in E]
print('⚠️  WARNINGS:'); [print('   -', w) for w in W]
assert len(E) >= 3 and len(W) >= 1
print()
good = {'load_best_model_at_end': True, 'eval_strategy': 'epoch', 'save_strategy': 'epoch',
        'metric_for_best_model': 'eval_f1', 'greater_is_better': True,
        'bf16': True, 'save_total_limit': 2,
        'per_device_train_batch_size': 16, 'gradient_accumulation_steps': 2,
        'num_train_epochs': 3}
E2, W2 = validate_training_args(good, n_train_samples=5000)
print(f'✅ 正确配置: {len(E2)} errors, {len(W2)} warnings')
assert E2 == [], f'正确配置不应有 error: {E2}'
print('\\n✅ 把这个函数放在 Trainer(...) 之前调用 —— 它能挡住本模块列的大部分坑。')"""),
    md("""## ✏️ 练习 1：总优化步与 checkpoint 数

实现 `training_plan(n_samples, per_device_bs, grad_accum, n_devices, epochs, save_steps)`：
返回 `(总优化步, 会产生的 checkpoint 数, 有效batch)`。
checkpoint 数 = `总优化步 // save_steps`（`save_steps` 为 None 时返回 0）。"""),
    code("""def training_plan(n_samples, per_device_bs, grad_accum, n_devices, epochs, save_steps):
    # TODO: b_eff = per_device_bs * grad_accum * n_devices
    #       batches/epoch = ceil(n_samples / (per_device_bs * n_devices))
    #       总优化步 = ceil(batches/epoch / grad_accum) * epochs
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
total, n_ck, beff = training_plan(5000, 8, 4, 1, 3, 500)
assert beff == 32
assert total == math.ceil(math.ceil(5000/8)/4)*3, total
assert n_ck == total // 500
print(f'5000 样本, bs=8, accum=4, 1卡, 3 epoch -> 总步 {total}, checkpoint {n_ck} 个, B_eff={beff}')
assert n_ck == 0, 'save_steps=500 但总步数不足 500 -> 一个 checkpoint 都不会存！'
# 多卡会减少总步数
t8, _, b8 = training_plan(5000, 8, 4, 8, 3, 500)
assert t8 < total and b8 == 256, '8 卡：总步数减少、有效 batch 变 8 倍'
print(f'同样配置换 8 卡 -> 总步 {t8}, B_eff={b8}  ← 有效 batch 变了 8 倍！')
assert training_plan(5000, 8, 4, 1, 3, None)[1] == 0
print('✅ 练习 1 通过：小数据集上 save_steps 常常一次都触发不了 —— 用 strategy="epoch"')"""),
    md("""## ✏️ 练习 2：compute_metrics 的 -100 过滤

实现 `compute_metrics(logits, labels)`：`logits` 形状 `(N, L, K)`、`labels` 形状 `(N, L)`
（token 分类）。返回 `{'accuracy': ..., 'n_eval': ...}`，**必须过滤 -100**。"""),
    code("""def compute_metrics(logits, labels):
    # TODO: preds = logits.argmax(-1)；mask = labels != -100
    #       accuracy = (preds[mask] == labels[mask]).mean()；n_eval = mask.sum()
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r = np.random.default_rng(4)
N, L, K = 4, 10, 5
labels = r.integers(0, K, size=(N, L))
labels[:, 7:] = -100                      # 后 3 个位置是 padding
logits = np.zeros((N, L, K));
for i in range(N):
    for j in range(L):
        logits[i, j, labels[i, j] if labels[i, j] != -100 else 0] = 5.0
res = compute_metrics(logits, labels)
assert abs(res['accuracy'] - 1.0) < 1e-9, f'非 -100 位置全对，准确率应为 1.0，得到 {res}'
assert res['n_eval'] == N * 7, f'只应评估 {N*7} 个位置，得到 {res["n_eval"]}'
# 不过滤会怎样：把 padding 也算进去（label=-100 永远预测不对）
naive = (logits.argmax(-1) == labels).mean()
print(f'正确（过滤 -100）: accuracy {res["accuracy"]:.3f}, 评估 {res["n_eval"]} 个位置')
print(f'错误（不过滤）    : accuracy {naive:.3f}   ← 被 padding 拉低')
assert naive < res['accuracy']
print('✅ 练习 2 通过：忘了过滤 -100 是 compute_metrics 的头号坑')"""),
    md("""## ✏️ 练习 3：早停 Callback

实现 `EarlyStopper`：`__init__(self, patience, greater_is_better)`、
`should_stop(self, metric)` —— 每次评估调用一次，返回是否应停止。
逻辑：维护最佳值；若连续 `patience` 次没有改善则返回 True。"""),
    code("""class EarlyStopper:
    def __init__(self, patience, greater_is_better=True):
        # TODO
        raise NotImplementedError
    def should_stop(self, metric):
        # TODO
        raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
es = EarlyStopper(patience=2, greater_is_better=True)
seq = [0.70, 0.75, 0.74, 0.73]          # 第 2 次是最佳，之后连续 2 次没改善
stops = [es.should_stop(x) for x in seq]
assert stops == [False, False, False, True], stops
# loss 场景（越小越好）
es2 = EarlyStopper(patience=1, greater_is_better=False)
assert [es2.should_stop(x) for x in [1.0, 0.9, 0.95]] == [False, False, True]
# 一直在改善就不该停
es3 = EarlyStopper(patience=2, greater_is_better=True)
assert not any(es3.should_stop(x) for x in [0.1, 0.2, 0.3, 0.4, 0.5])
print('✅ 练习 3 通过：注意 EarlyStopping **必须配 load_best_model_at_end=True**，')
print('   否则你停在了「连续 N 次没进步」的那个点，而不是最好的那个点。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def training_plan(n_samples, per_device_bs, grad_accum, n_devices, epochs, save_steps):
    b_eff = per_device_bs * grad_accum * n_devices
    batches_per_epoch = math.ceil(n_samples / (per_device_bs * n_devices))
    total = math.ceil(batches_per_epoch / grad_accum) * epochs
    n_ck = 0 if not save_steps else total // save_steps
    return total, n_ck, b_eff"""),
    code("""# 练习 2 参考答案
def compute_metrics(logits, labels):
    preds = logits.argmax(-1)
    mask = labels != -100
    return {'accuracy': float((preds[mask] == labels[mask]).mean()),
            'n_eval': int(mask.sum())}"""),
    code("""# 练习 3 参考答案
class EarlyStopper:
    def __init__(self, patience, greater_is_better=True):
        self.patience, self.gib = patience, greater_is_better
        self.best, self.bad = None, 0
    def should_stop(self, metric):
        improved = (self.best is None or
                    (metric > self.best if self.gib else metric < self.best))
        if improved:
            self.best, self.bad = metric, 0
        else:
            self.bad += 1
        return self.bad >= self.patience"""),
    md("""---
## 🧪 真实 API 对照胶囊：一份带校验的训练配置"""),
    code("""RECIPE = r'''
from transformers import (TrainingArguments, Trainer, EarlyStoppingCallback,
                          DataCollatorWithPadding)

N_TRAIN, N_DEVICES = len(train_ds), 1
PD, GA = 16, 2                                  # 有效 batch = 16*2*1 = 32

args = TrainingArguments(
    output_dir="out",
    # ── 有效 batch 的三个乘数 ──
    per_device_train_batch_size=PD,
    gradient_accumulation_steps=GA,
    per_device_eval_batch_size=32,
    # ── 学习率与调度 ──
    learning_rate=2e-5,                         # 微调常用值（比从头训练小 100 倍）
    lr_scheduler_type="linear",
    warmup_ratio=0.06,
    num_train_epochs=3,
    max_grad_norm=1.0,
    weight_decay=0.01,
    # ── 精度与显存 ──
    bf16=True,                                  # 优先 bf16 而非 fp16
    gradient_checkpointing=False,                # 开了要设 model.config.use_cache=False
    optim="adamw_torch_fused",
    group_by_length=True,                       # 长度分组：省 padding（模块 02）
    dataloader_num_workers=4,
    # ── 评估与保存：**三件套必须配套** ──
    eval_strategy="epoch",
    save_strategy="epoch",                      # 与 eval_strategy 一致
    load_best_model_at_end=True,
    metric_for_best_model="eval_f1",
    greater_is_better=True,                     # 显式写出方向
    save_total_limit=2,                         # >= 2，否则最佳可能被删
    eval_accumulation_steps=8,                  # 防评估 OOM
    # ── 日志与复现 ──
    logging_steps=20,                           # 注意：数的是**优化步**
    seed=42,
    report_to=["tensorboard"],
)

# 上线前先跑校验（本 notebook 里实现的那个函数）
E, W = validate_training_args(vars(args), n_train_samples=N_TRAIN, n_devices=N_DEVICES)
assert not E, E
for w in W: print("WARN:", w)

trainer = Trainer(
    model=model, args=args,
    train_dataset=train_ds, eval_dataset=eval_ds,
    data_collator=DataCollatorWithPadding(tok),
    compute_metrics=compute_metrics,             # 记得过滤 -100
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)
trainer.train(resume_from_checkpoint=True)       # 有 checkpoint 就续训
'''
print(RECIPE)
for c in ['gradient_accumulation_steps', 'greater_is_better', 'save_total_limit',
          'eval_accumulation_steps', 'group_by_length', 'validate_training_args']:
    assert c in RECIPE, c
print('✅ 配方覆盖本模块全部要点')"""),
    md("""### 小结
- `Trainer` 就是**一个写得很仔细的训练循环**；读一遍 `_inner_training_loop` 胜过读十篇教程。
- **有效 batch = per_device × grad_accum × n_devices**，四种组合梯度完全相同（已对拍），只差显存与吞吐。
- **loss 要在 backward 前除以 grad_accum**；忘了等于学习率放大 N 倍 → 一开就发散。
- **`logging_steps`/`eval_steps`/`save_steps` 数的是优化步**；小数据集上 `save_steps=500` 常常一次都触发不了 → 用 `strategy="epoch"`。
- **总步数 = ceil(batches/grad_accum) × epochs**，换卡数会改变它 → 改变整条 lr 曲线。跨卡数可比要固定 `max_steps`。
- **checkpoint 含优化器状态**（约权重的 4 倍）；只加载权重 = 用新优化器重新开始。
- **`load_best_model_at_end` 是三件套依赖**（+`eval_strategy`+`metric_for_best_model`+方向）；`EarlyStopping` 也依赖它。
- 交付物：一个**配置校验函数**，把隐式依赖变成断言，在 `Trainer(...)` 之前跑。

下一站：**模块 04 · PEFT 与 TRL** —— 让 7B 在单卡上微调，以及后训练算法的数据格式。"""),
]
