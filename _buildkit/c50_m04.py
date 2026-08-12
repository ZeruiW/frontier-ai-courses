# -*- coding: utf-8 -*-
"""C50 模块 04 · PEFT 与 TRL。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–03；C02（SFT/RLHF/DPO 的算法原理）；C27（量化原理，QLoRA 一节会用）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_peft_trl.ipynb'),
    ("核心参考", "Hu et al. 2021（LoRA）、Dettmers et al. 2023（QLoRA）、Rafailov et al. 2023（DPO）；peft / trl 文档"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("lora", "LoRA：四个参数，每个都有明确含义", "".join([
        P("LoRA 的原理一句话：<strong>冻结原权重 <code>W</code>，只训练一个低秩增量 <code>ΔW = BA</code></strong>（<code>A: r×d_in</code>，<code>B: d_out×r</code>，<code>r ≪ min(d_in,d_out)</code>）。原理在 C02 讲过，本模块只讲<strong>参数怎么配、为什么</strong>。"),
        MATH("h = Wx + \\frac{\\alpha}{r}\\,BAx, \\qquad A \\sim \\mathcal{N}(0,\\sigma^2),\\; B = 0"),
        TABLE(["参数", "含义", "常用值", "怎么想"], [
            ["<code>r</code>", "低秩的秩", "8 / 16 / 32 / 64", "<strong>容量旋钮</strong>。任务与预训练分布越远、数据越多，越需要大 <code>r</code>。8 够用于风格/格式适配；领域知识注入常要 32+"],
            ["<code>lora_alpha</code>", "缩放的分子；实际缩放是 <code>α/r</code>", "通常取 <code>2r</code> 或 <code>r</code>", "<strong>它的作用是「让改 r 时不必重调 lr」</strong>。固定 <code>α/r</code> 比值，换 <code>r</code> 时有效步长不变"],
            ["<code>target_modules</code>", "给哪些线性层加 LoRA", "<code>[\"q_proj\",\"v_proj\"]</code>（默认）或全部 <code>q,k,v,o,gate,up,down</code>", "<strong>覆盖面比 <code>r</code> 更重要</strong>——原论文发现同等参数预算下，「小 r + 覆盖更多模块」优于「大 r + 只覆盖 q,v」"],
            ["<code>lora_dropout</code>", "作用在 LoRA 分支输入上的 dropout", "0.0 – 0.1", "小数据集上有用；大数据集通常设 0"],
        ]),
        DUAL(
            "<strong><code>B</code> 初始化为 0 是个关键设计</strong>：这让训练开始时 <code>ΔW = BA = 0</code>，模型输出与原模型<em>逐字节相同</em>。这意味着 LoRA 微调是从「原模型」这个点<strong>连续地</strong>出发的，不会有初始的性能跳崖。<em>如果 <code>A</code> 和 <code>B</code> 都随机初始化，训练一开始模型就被随机扰动破坏，需要先花很多步「修回来」。</em>这个细节在 notebook 里会用数值验证。",
            "<strong><code>α/r</code> 的设计动机</strong>值得说清，因为它常被误解为「另一个学习率」。原论文的意图是：当你把 <code>r</code> 从 8 调到 64 时，<code>BA</code> 的输出尺度会随 <code>r</code> 变化（更多的秩累加），如果不缩放，有效学习率就变了、要重新调 lr。用 <code>α/r</code> 缩放后，<em>固定 <code>α/r</code> 比值扫 <code>r</code></em> 就不用重调 lr。<strong>所以实践中你应该固定比值（如 <code>α=2r</code>）而不是固定 <code>α</code></strong>——固定 <code>α=16</code> 然后把 <code>r</code> 从 8 调到 64，实际上把缩放从 2.0 降到了 0.25。",
        ),
        CALLOUT("warn", "<strong><code>target_modules</code> 的名字是模型特定的</strong>，这是最常见的报错来源。Llama 系是 <code>q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj</code>；BERT 系是 <code>query,key,value,dense</code>；GPT-2 是 <code>c_attn,c_proj</code>（而且 <code>c_attn</code> 是把 QKV 融在一起的一个大矩阵）。填错名字的症状是 <code>ValueError: Target modules not found</code>，或者更糟——<em>只匹配到一部分层而不报错</em>。可靠做法：<code>print([n for n,_ in model.named_modules()])</code> 先看一眼，或者用 <code>target_modules=\"all-linear\"</code> 让 peft 自动找。"),
    ])),
    ("peft_api", "peft 的四个动作：包装、训练、保存、合并", "".join([
        CODE("""from peft import LoraConfig, get_peft_model, PeftModel, TaskType

# ① 包装：冻结原权重、注入 LoRA 分支
cfg = LoraConfig(
    r=16, lora_alpha=32,                 # α/r = 2
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",                          # 通常不训 bias
    task_type=TaskType.CAUSAL_LM,         # ⚠️ 必须与任务匹配，否则头不对
)
model = get_peft_model(base_model, cfg)
model.print_trainable_parameters()
# -> trainable params: 40,370,176 || all params: 8,070,000,000 || trainable%: 0.50

# ② 训练：和普通 Trainer 完全一样（模块 03）
trainer = Trainer(model=model, args=args, ...); trainer.train()

# ③ 保存：只存 adapter（几十 MB，不是几十 GB）
model.save_pretrained("out/adapter")     # adapter_model.safetensors + adapter_config.json

# ④ 加载 / 合并
m = PeftModel.from_pretrained(base_model, "out/adapter")   # 可继续训练或推理
merged = m.merge_and_unload()             # W <- W + (α/r)BA，得到普通模型
merged.save_pretrained("out/merged")      # 完整权重，可直接给 vLLM 用"""),
        TABLE(["动作", "产出", "大小", "能继续训练吗"], [
            ["<code>save_pretrained</code>（adapter）", "<code>adapter_model.safetensors</code>", "<strong>几十 MB</strong>", "✅ 用 <code>PeftModel.from_pretrained</code> 加载后可以"],
            ["<code>merge_and_unload()</code>", "普通 <code>nn.Module</code>（权重已融合）", "与基座相同（几十 GB）", "❌ <strong>LoRA 分支已消失</strong>，只能当普通模型全量训"],
            ["多 adapter 共存", "多个 adapter 目录", "每个几十 MB", "✅ <code>set_adapter(name)</code> 切换；可同时加载"],
        ]),
        DUAL(
            "<strong><code>merge_and_unload()</code> 的取舍</strong>：合并后推理零额外开销（不用算 LoRA 分支，也不影响 kernel 融合），且能直接喂给 vLLM/TensorRT 这类只认标准权重的引擎。代价是<em>失去了「多 adapter 动态切换」的能力</em>，而且合并是<strong>不可逆</strong>的（除非你留着原基座和 adapter）。<em>规则：训练与实验期不合并（保留灵活性），最终上线时合并（换取推理效率）。</em>",
            "多 adapter 共存是 LoRA 一个被低估的能力：<strong>一个基座 + N 个几十 MB 的 adapter，可以服务 N 个不同任务/客户</strong>。显存里只有一份基座权重，切换 adapter 几乎零成本。这在多租户场景下的成本优势是巨大的（对比 N 份完整模型）。生产上 vLLM 等引擎已支持 multi-LoRA 服务（同一 batch 里不同请求用不同 adapter）。<em>这也是「不合并」的一个强理由。</em>",
        ),
        CALLOUT("danger", "<p><strong><code>task_type</code> 填错是个静默陷阱</strong>。<code>TaskType.CAUSAL_LM</code> 与 <code>SEQ_CLS</code> 的区别在于：后者会把分类头（<code>score</code>/<code>classifier</code>）也标记为可训练（因为它是新初始化的，必须训）。如果你做分类却填了 <code>CAUSAL_LM</code>，<em>分类头会被冻结在随机初始化状态</em>——训练能跑、loss 会降一点（LoRA 在适应那个随机头），但效果永远上不去。<strong>症状：准确率卡在一个远低于预期的水平且怎么调超参都不动。</strong></p>", "task_type 填错 = 分类头被冻在随机状态"),
    ])),
    ("qlora", "QLoRA：四个组件，缺一个就不是 QLoRA", "".join([
        P("QLoRA 让 65B 模型在单张 48GB 卡上微调。它不是一个技巧，而是<strong>四个组件的组合</strong>："),
        TABLE(["组件", "做什么", "省了什么", "参数"], [
            ["<strong>4-bit NF4 量化</strong>", "把冻结的基座权重量化到 4 bit（NormalFloat4，针对正态分布优化的量化格点）", "权重显存 ÷4（16 GB → 4.5 GB）", "<code>load_in_4bit=True, bnb_4bit_quant_type=\"nf4\"</code>"],
            ["<strong>双重量化</strong>", "把量化用的 scale 常数本身再量化一次", "额外省约 0.4 bit/参数", "<code>bnb_4bit_use_double_quant=True</code>"],
            ["<strong>分页优化器</strong>", "优化器状态在显存不足时分页到 CPU", "避免峰值 OOM", "<code>optim=\"paged_adamw_8bit\"</code>"],
            ["<strong>LoRA 在量化权重上</strong>", "基座 4-bit 冻结，LoRA 分支用 bf16 训练", "梯度与优化器状态只按 LoRA 参数算", "<code>bnb_4bit_compute_dtype=torch.bfloat16</code>"],
        ]),
        CODE("""from transformers import BitsAndBytesConfig
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,   # 计算时反量化到 bf16
)
base = AutoModelForCausalLM.from_pretrained(CKPT, quantization_config=bnb,
                                           device_map="auto")
base = prepare_model_for_kbit_training(base)   # ⚠️ 别忘：转 LayerNorm 到 fp32、
                                                #    开 gradient checkpointing、
                                                #    让 embedding 输出 requires_grad
model = get_peft_model(base, LoraConfig(r=64, lora_alpha=16, ...))"""),
        CALLOUT("warn", "<strong><code>prepare_model_for_kbit_training</code> 常被漏掉</strong>，而它做的三件事都是必需的：①把 LayerNorm 转成 fp32（量化模型里 LN 用低精度会不稳）；②开启 gradient checkpointing；③给 embedding 的输出挂一个 hook 让梯度能流过（量化层不可导，梯度必须绕过它到 LoRA 分支）。<em>漏掉它的症状是「loss 不降」或「梯度为 None」</em>。另外 QLoRA 论文用的是 <code>r=64</code> 且覆盖<strong>所有</strong>线性层——比常规 LoRA 激进得多，因为 4-bit 基座本身有量化误差，需要更大的 LoRA 容量来补偿。"),
        P("最后一条必须知道的边界：<strong>QLoRA 训练慢</strong>。每次前向都要把 4-bit 权重反量化到 bf16，这个开销让训练速度约为 bf16 LoRA 的 60–70%。<em>所以 QLoRA 是「显存不够时的解法」，不是「更快的解法」</em>。如果你的卡放得下 bf16 LoRA，就别用 QLoRA。"),
    ])),
    ("sft", "TRL 的 SFTTrainer：数据格式与 prompt 掩码", "".join([
        P("<code>trl</code> 把后训练算法包成了几个 Trainer。<code>SFTTrainer</code> 是最常用的，它的核心工作是<strong>把「对话」变成「带正确 labels 的 token 序列」</strong>。"),
        H3("三种数据格式"),
        CODE("""# 格式 ① conversational（推荐）—— SFTTrainer 会自动套 chat template
{"messages": [{"role": "system",    "content": "You are helpful."},
              {"role": "user",      "content": "什么是 LoRA？"},
              {"role": "assistant", "content": "LoRA 是……"}]}

# 格式 ② prompt-completion
{"prompt": "什么是 LoRA？", "completion": "LoRA 是……"}

# 格式 ③ 纯文本（自己拼好，SFTTrainer 直接用）
{"text": "<|user|>什么是 LoRA？<|assistant|>LoRA 是……<|end|>"}"""),
        DUAL(
            "格式 ① 的好处是<strong>让 tokenizer 的 chat template 决定拼接方式</strong>。每个指令模型都有自己的对话格式（Llama-3 的 <code>&lt;|start_header_id|&gt;</code>、ChatML 的 <code>&lt;|im_start|&gt;</code>、Mistral 的 <code>[INST]</code>），<em>格式必须与该模型预训练/指令微调时一致</em>，否则模型看到的是陌生的分隔符。用 <code>tokenizer.apply_chat_template()</code>（或让 <code>SFTTrainer</code> 自动做）是唯一可靠的做法——手写拼接几乎一定会在某个特殊 token 上出错。",
            "<strong>最关键的语义是 prompt 掩码</strong>：SFT 只应对 <em>assistant 的回答</em> 计损失，system/user 部分要填 <code>-100</code>（模块 02 讲过）。<code>SFTTrainer</code> 通过 <code>DataCollatorForCompletionOnlyLM</code>（配 <code>response_template</code>）或对 conversational 格式的自动处理来做这件事。<strong>如果不掩，模型会同时学习「生成用户提问」</strong>——loss 看起来更低（用户提问也是可预测的文本），但模型在推理时可能自己接着编用户的下一句话。<em>这是 SFT 最经典的 bug。</em>",
        ),
        TABLE(["<code>SFTConfig</code> 参数", "作用", "注意"], [
            ["<code>max_length</code>", "序列长度上限", "超出被截断——注意<strong>回答被截断</strong>比 prompt 被截断更糟"],
            ["<code>packing</code>", "把多条短样本拼进一个定长序列", "消除 padding 浪费（模块 02），但需要正确的跨样本掩码；短样本任务上可能有害"],
            ["<code>completion_only_loss</code> / <code>DataCollatorForCompletionOnlyLM</code>", "只对回答计损失", "<strong>必须开</strong>；<code>response_template</code> 要与 chat template 完全一致"],
            ["<code>dataset_text_field</code>", "纯文本格式时指定字段名", "与 conversational 格式互斥"],
            ["<code>neftune_noise_alpha</code>", "在 embedding 上加噪声做正则", "小数据集上有时有效，非必需"],
        ]),
        CALLOUT("intuition", "<strong><code>packing=True</code> 的取舍</strong>值得单独想清楚。它把 padding 浪费降到接近 0（吞吐可能翻倍），但引入两个问题：①跨样本的注意力污染（需要 <code>position_ids</code> 或变长 attention 正确隔离，否则一条样本会「看到」另一条）；②<em>短样本被拼在一起后，每条样本的相对权重变了</em>——原来每条样本贡献一个梯度，现在长样本贡献更多 token 因此权重更大。<em>对指令数据（长度差异大）这个偏移是真实的</em>。规则：数据量大且长度接近时开 packing；数据少或长度差异大时别开。"),
    ])),
    ("dpo", "DPOTrainer：成对数据与 beta", "".join([
        P("DPO 的算法原理在 C02/C23 讲过（用偏好对直接优化策略，不需要显式奖励模型）。本模块讲<strong>数据格式与三个关键参数</strong>。"),
        CODE("""# DPO 的数据格式：每条是一个「偏好对」
{"prompt":   [{"role": "user", "content": "什么是 LoRA？"}],
 "chosen":   [{"role": "assistant", "content": "LoRA 是一种低秩适配方法……"}],
 "rejected": [{"role": "assistant", "content": "我不知道。"}]}

from trl import DPOConfig, DPOTrainer
trainer = DPOTrainer(
    model=policy,                    # 要训练的策略（通常是 SFT 后的模型）
    ref_model=None,                  # None -> 自动用 policy 的初始副本；
                                     #        用 LoRA 时可以直接禁用 adapter 当参考
    args=DPOConfig(beta=0.1,         # KL 约束强度：**最重要的参数**
                   loss_type="sigmoid",   # sigmoid(标准DPO)/ipo/hinge/kto_pair
                   max_length=1024,
                   max_prompt_length=512),
    train_dataset=pref_ds,
    processing_class=tok,
)"""),
        MATH("\\mathcal{L}_{DPO} = -\\log\\sigma\\!\\left(\\beta\\left[\\log\\frac{\\pi(y_w|x)}{\\pi_{ref}(y_w|x)} - \\log\\frac{\\pi(y_l|x)}{\\pi_{ref}(y_l|x)}\\right]\\right)"),
        TABLE(["参数", "含义", "调大会怎样", "调小会怎样"], [
            ["<code>beta</code>", "隐式 KL 约束的强度", "更保守，贴近参考模型，学得慢", "更激进，可能<strong>偏离太远导致退化</strong>（重复、乱码、能力下降）"],
            ["<code>ref_model</code>", "参考策略", "—", "<strong>用 LoRA 时可以省掉一份模型</strong>：禁用 adapter 即得参考"],
            ["<code>loss_type</code>", "损失变体", "<code>ipo</code> 对长度偏差更鲁棒；<code>hinge</code> 更硬", "—"],
        ]),
        DUAL(
            "<strong><code>ref_model=None</code> + LoRA 是个漂亮的组合</strong>。DPO 需要同时算策略与参考的 logprob，通常意味着显存里要放两份模型。但用 LoRA 时，「参考模型」= 「禁用 LoRA 分支的同一个模型」——<em>因为 LoRA 的 <code>B</code> 初始化为 0，禁用它就精确回到 SFT 后的模型</em>。<code>trl</code> 会自动利用这一点，显存直接省一半。这是 LoRA 与 DPO 的一个非平凡协同。",
            "<strong><code>beta</code> 的实践区间是 0.01–0.5，常用 0.1</strong>。它的作用类似 PPO 里的 KL 系数：太小则策略跑得太远，出现「reward hacking」式的退化（输出变长、变重复、通用能力下降）；太大则几乎学不动。<em>调 <code>beta</code> 时必须同时监控「非目标能力」</em>——DPO 很容易在提升偏好胜率的同时损害通用能力（C23 有系统讨论）。另外要警惕<strong>长度偏差</strong>：偏好数据里若 chosen 系统性更长，DPO 会学到「更长 = 更好」，这是文献中反复出现的问题，<code>loss_type=\"ipo\"</code> 或显式长度归一化是缓解手段。",
        ),
        CALLOUT("warn", "<strong>DPO 之前必须先 SFT</strong>。DPO 假设策略已经在目标分布上有合理的概率质量——直接在基座模型上跑 DPO，效果通常很差且不稳定。标准流程是 <strong>基座 → SFT → DPO</strong>（C02 的完整链路）。另一个常见错误是<em>把 SFT 数据直接当 DPO 数据</em>（把 SFT 答案当 chosen、随机答案当 rejected）——这样的 rejected 太容易区分，学不到细粒度偏好，<em>这与 C49 反复出现的「负例设计决定学到什么」是同一条原理。</em>"),
    ])),
    ("ledger", "算一笔账：LoRA 到底省了多少", "".join([
        MATH("N_{LoRA} = \\sum_{\\text{目标层}} r\\,(d_{in} + d_{out}), \\qquad \\text{占比} = \\frac{N_{LoRA}}{N_{total}}"),
        TABLE(["配置", "可训练参数", "占比", "优化器状态", "checkpoint", "训练显存（7B）"], [
            ["全量微调", "7.0 B", "100%", "56 GB", "≈ 84 GB", "<strong>≈ 84 GB</strong>"],
            ["LoRA r=8, 仅 q,v", "≈ 4.2 M", "0.06%", "34 MB", "≈ 8 MB", "≈ 18 GB"],
            ["LoRA r=16, 全部线性层", "≈ 40 M", "0.57%", "320 MB", "≈ 80 MB", "≈ 20 GB"],
            ["QLoRA r=64, 全部线性层", "≈ 160 M", "2.3%", "1.3 GB", "≈ 320 MB", "<strong>≈ 8 GB</strong>"],
        ]),
        P("三个观察："),
        UL([
            "<strong>省显存的主力是「优化器状态按可训练参数算」</strong>（模块 01 的公式），不是权重本身。全量微调的 56 GB 优化器状态直接变成几百 MB。",
            "<strong>checkpoint 从几十 GB 变成几十 MB</strong>，这改变了实验方式——你可以毫无压力地保存二十个实验的 adapter，而全量微调时连三个 checkpoint 都要考虑磁盘。",
            "<strong>QLoRA 的显存最低但训练最慢</strong>（反量化开销，约为 bf16 LoRA 的 60–70% 速度）。它是「放不下时的解法」，不是「更快的解法」。",
        ]),
        P("还有一个常被忽略的账：<strong>推理开销</strong>。未合并的 LoRA 每层多两次小矩阵乘（<code>x→A→B</code>），FLOPs 增加约 <code>2r/d</code>（<code>r=16, d=4096</code> 时约 0.8%），但<em>因为是两个小 kernel，实际延迟增加可能到 10–20%</em>（kernel 启动开销与显存往返占主导）。<strong>合并后开销归零</strong>——这就是上线前该合并的理由。"),
        CALLOUT("intuition", "把本模块浓缩成一句话：<strong>LoRA 的价值不只是「省显存」，而是把「微调」从一件重工程变成一件轻工程</strong>——几十 MB 的产物、可以同时保留几十个版本、一个基座服务多个任务、切换成本接近零。<em>这个「轻」带来的实验速度提升，可能比省下的显存更有价值。</em>"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>LoRA 变体的丛林</strong>：DoRA（分解幅度与方向）、rsLoRA（改缩放为 <code>α/√r</code>）、LoRA+（给 A、B 不同学习率）、VeRA（共享随机基）、PiSSA（用 SVD 主成分初始化）——各自报告了改进，但缺乏统一的、控制了算力预算的对比。「该用哪个变体」目前主要靠试。",
            "<strong><code>r</code> 与任务的关系</strong>：普遍经验是「风格适配小 <code>r</code>、知识注入大 <code>r</code>」，但缺乏可操作的先验判据。<em>LoRA 到底能学到多少「新知识」（而非只是重新组合已有能力）是个尚未澄清的问题</em>，也直接关系到「什么时候必须全量微调」。",
            "<strong>多 adapter 的服务与组合</strong>：同 batch 混合不同 adapter（S-LoRA、vLLM 的 multi-LoRA）已工程化，但<em>多个 adapter 的语义组合</em>（同时应用两个 adapter、或按权重混合）效果不可预测，缺乏理论。",
            "<strong>DPO 家族的爆炸</strong>：IPO、KTO、ORPO、SimPO、CPO……各自修正 DPO 的某个缺陷（长度偏差、需要成对数据、需要 SFT 阶段）。<em>在什么数据条件下哪个更优</em>缺乏系统结论，且很多对比没有控制超参搜索预算（C40 会说这是典型的可复现性问题）。",
            "<strong>偏好数据的长度偏差</strong>：几乎所有偏好数据集里 chosen 都系统性更长，导致对齐后的模型输出越来越长。显式长度归一化、长度控制的解码、以及在数据侧平衡长度，都是缓解手段，但没有干净的解法。",
        ]),
        CALLOUT("paper", "必读：Hu et al. 2021 <em>LoRA</em>（重点读 §7.2 关于 <code>r</code> 与 target modules 的消融——「覆盖更多模块优于更大 r」这个结论出自那里）、Dettmers et al. 2023 <em>QLoRA</em>（四个组件与 NF4 的推导）、Rafailov et al. 2023 <em>DPO</em>（推导必读，理解 beta 的来源）、Meng et al. 2024 <em>SimPO</em> 与 Azar et al. 2024 <em>IPO</em>（长度偏差的两种修正）。文档侧：peft 的 <em>LoRA</em> 与 <em>Quantization</em>、trl 的 <em>SFTTrainer</em> 与 <em>DPOTrainer</em>。原理侧：C02（后训练全链路）、C23（对齐前沿）、C27（量化）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · PEFT 与 TRL（用 numpy 实现 LoRA 注入/缩放/合并 + SFT 掩码 + DPO 损失）

目标：把 **LoRA 的四个参数 → B=0 初始化的意义 → α/r 缩放 → 合并的等价性 → 参数量账 →
SFT 的 prompt 掩码 → DPO 损失与 beta** 从零写一遍。

路线：LoRA 层实现 → B=0 的连续性验证 → α/r 与「换 r 不用重调 lr」→ target_modules 的覆盖面 →
merge 的数值等价 → 参数量与显存账 → chat template 与 completion-only 掩码 →
DPO 损失与 beta 的作用 → ✏️ 练习 → 📖 答案 → 🧪 选型胶囊。

> 心智模型：**LoRA 把「微调」从重工程变成轻工程**——几十 MB 的产物、可以同时留几十个版本。"""),
    md("""## 1 · LoRA 层：`h = Wx + (α/r)·BAx`，且 `B = 0`

`B = 0` 让训练开始时输出与原模型**逐字节相同**——微调从「原模型」这个点连续出发，没有初始跳崖。"""),
    code("""import numpy as np, math, json
rng = np.random.default_rng(0)

class Linear:
    def __init__(self, d_in, d_out, seed=0):
        r = np.random.default_rng(seed)
        self.W = r.normal(size=(d_in, d_out)) / math.sqrt(d_in)
        self.d_in, self.d_out = d_in, d_out
        self.frozen = False
    def __call__(self, x): return x @ self.W
    def n_params(self): return self.W.size

class LoRALinear:
    '''包装一个 Linear：冻结 W，只训练 A(r×d_in) 与 B(d_out×r)。'''
    def __init__(self, base: Linear, r=8, lora_alpha=16, lora_dropout=0.0, seed=0):
        self.base = base; base.frozen = True
        rg = np.random.default_rng(seed)
        self.r, self.alpha = r, lora_alpha
        self.scaling = lora_alpha / r                     # ← 实际缩放
        self.A = rg.normal(size=(base.d_in, r)) / math.sqrt(base.d_in)   # 随机初始化
        self.B = np.zeros((r, base.d_out))                # ← **零初始化**
        self.dropout = lora_dropout
        self.merged = False
    def __call__(self, x, training=False):
        out = self.base(x)
        if self.merged:
            return out                                     # 已合并进 W，不再走分支
        z = x
        if training and self.dropout > 0:
            keep = (np.random.default_rng(1).random(z.shape) > self.dropout) / (1 - self.dropout)
            z = z * keep
        return out + self.scaling * ((z @ self.A) @ self.B)
    def n_trainable(self): return self.A.size + self.B.size
    def merge(self):
        '''W <- W + scaling * A @ B。合并后 LoRA 分支消失（不可逆）。'''
        self.base.W = self.base.W + self.scaling * (self.A @ self.B)
        self.merged = True
    def unmerge(self):
        self.base.W = self.base.W - self.scaling * (self.A @ self.B)
        self.merged = False

D_IN, D_OUT = 64, 64
base = Linear(D_IN, D_OUT, seed=1)
lora = LoRALinear(base, r=8, lora_alpha=16, seed=2)
x = rng.normal(size=(4, D_IN))

out_base = base(x)                          # 注意：base 已被冻结但仍可前向
out_lora = lora(x)
print('B 初始化为零 -> 输出差异:', float(np.abs(out_lora - out_base).max()))
assert np.allclose(out_lora, out_base, atol=1e-14), 'B=0 时输出必须与原模型逐字节相同'
assert base.frozen and lora.n_trainable() == 8 * (D_IN + D_OUT)
print(f'可训练参数: A({lora.A.shape}) + B({lora.B.shape}) = {lora.n_trainable()}')
print(f'原权重参数: {base.n_params()} (冻结)')
print(f'占比: {lora.n_trainable()/base.n_params():.1%}')

# 反例：A、B 都随机初始化 -> 训练一开始就把模型打乱
lora_bad = LoRALinear(Linear(D_IN, D_OUT, seed=1), r=8, lora_alpha=16, seed=3)
lora_bad.B = np.random.default_rng(4).normal(size=lora_bad.B.shape) * 0.1
dev = float(np.abs(lora_bad(x) - out_base).max())
print(f'\\n❌ B 也随机初始化 -> 初始输出偏移 {dev:.4f}')
assert dev > 0.01
print('   模型一开始就被随机扰动破坏，需要先花很多步「修回来」。')
print('✅ B=0 是 LoRA 能「连续地从原模型出发」的关键设计。')"""),
    md("""## 2 · α/r 缩放：它到底在补偿什么

常见误解：`lora_alpha` 是另一个学习率。**真实意图**：让 `BA` 的输出尺度不随 `r` 剧烈变化，
从而「换 r 时不必重调 lr」。

下面把三种缩放放在一起量化。你会看到一个有意思的事实：
**固定 `α`（scaling=α/r）与固定比值（scaling=常数）都不能真正让幅度对 r 不变**——
真正做到的是 `α/√r`。这正是 rsLoRA 的贡献（见讲解「研究前沿」）。
但原论文的 `α/r` 至少把「换 r 的影响」从 √r 倍压到了 1/√r 倍，方向是对的。"""),
    code("""def branch_output_scale(r, scaling, d=64, n=256, seed=0):
    '''测量 LoRA 分支输出 scaling*(xA)B 的典型幅度（用「已训练」的非零 B 模拟）。'''
    rg = np.random.default_rng(seed)
    A = rg.normal(size=(d, r)) / math.sqrt(d)
    B = rg.normal(size=(r, d)) * 0.05
    x = rg.normal(size=(n, d))
    return float(np.abs(scaling * ((x @ A) @ B)).mean())

RS = [4, 8, 16, 32, 64]
ALPHA = 16.0
schemes = {
    '无缩放 (scaling=1)':        lambda r: 1.0,
    'LoRA:  α/r  (α=16)':        lambda r: ALPHA / r,
    'rsLoRA: α/√r (α=16)':       lambda r: ALPHA / math.sqrt(r),
}
print(f"{'r':>4s} " + ' '.join(f'{k:<22s}' for k in schemes))
mags = {k: [] for k in schemes}
for r in RS:
    row = []
    for k, f in schemes.items():
        m = branch_output_scale(r, f(r)); mags[k].append(m)
        row.append(f'{m:<22.5f}')
    print(f'{r:>4d} ' + ' '.join(row))

spreads = {k: max(v) / min(v) for k, v in mags.items()}
print('\\n幅度对 r 的跨度（越接近 1 越好）:')
for k, v in spreads.items():
    print(f'  {k:<24s} {v:>6.2f}×')

assert spreads['rsLoRA: α/√r (α=16)'] < 1.15, 'α/√r 才真正让幅度对 r 不变'
assert spreads['LoRA:  α/r  (α=16)'] < spreads['无缩放 (scaling=1)'], \
    'α/r 至少比不缩放更稳（把 √r 倍的漂移压成 1/√r 倍）'
print('\\n✅ 三条结论：')
print('   ① 不缩放时幅度 ∝ √r —— 换 r 必须重调 lr。')
print('   ② LoRA 的 α/r 过度补偿了（幅度变成 ∝ 1/√r），但漂移方向反转、幅度相同，仍是改进。')
print('   ③ α/√r（rsLoRA）才真正做到幅度与 r 无关。')
print('\\n实践建议：用 LoRA 默认的 α/r 时**固定 α/r 比值**（如 α=2r）而不是固定 α ——')
print('   固定 α=16 把 r 从 8 调到 64，等于把缩放从 2.0 降到 0.25，**悄悄降了 8 倍学习率**。')
for r in [8, 64]:
    print(f'     r={r:>2d}, α=16 固定 -> scaling={ALPHA/r:.3f}')"""),
    md("""## 3 · target_modules：覆盖面比 r 更重要

LoRA 原论文的消融结论：**同等参数预算下，「小 r + 覆盖更多模块」优于「大 r + 只覆盖 q,v」**。
用参数量账验证这个「同等预算」是怎么算的。"""),
    code("""# 一个迷你 Transformer 层的线性模块（仿 Llama 命名）
LAYER_MODULES = {
    'q_proj': (4096, 4096), 'k_proj': (4096, 1024), 'v_proj': (4096, 1024),
    'o_proj': (4096, 4096), 'gate_proj': (4096, 11008),
    'up_proj': (4096, 11008), 'down_proj': (11008, 4096),
}
N_LAYERS = 32

def lora_params(target_modules, r, n_layers=N_LAYERS):
    total = 0
    for name in target_modules:
        if name not in LAYER_MODULES:
            raise ValueError(f'Target modules {name!r} not found. '
                             f'可选: {sorted(LAYER_MODULES)}')
        d_in, d_out = LAYER_MODULES[name]
        total += r * (d_in + d_out)
    return total * n_layers

def base_params(n_layers=N_LAYERS, vocab=128256, d=4096):
    per_layer = sum(a * b for a, b in LAYER_MODULES.values())
    return per_layer * n_layers + vocab * d

QV = ['q_proj', 'v_proj']
ALL = list(LAYER_MODULES)
BASE = base_params()
print(f'基座参数量 ≈ {BASE/1e9:.2f} B\\n')
print(f"{'配置':<34s} {'可训练参数':>12s} {'占比':>8s}")
configs = [('r=8,  仅 q,v', QV, 8), ('r=64, 仅 q,v', QV, 64),
           ('r=8,  全部线性层', ALL, 8), ('r=16, 全部线性层', ALL, 16),
           ('r=64, 全部线性层', ALL, 64)]
for label, tm, r in configs:
    n = lora_params(tm, r)
    print(f'{label:<34s} {n/1e6:>10.1f} M {n/BASE:>8.2%}')

n_qv64 = lora_params(QV, 64); n_all8 = lora_params(ALL, 8)
print(f'\\n「r=64 仅 q,v」= {n_qv64/1e6:.1f}M   vs   「r=8 全部层」= {n_all8/1e6:.1f}M')
print('两者参数量接近，但论文报告**后者效果更好** —— 覆盖面比秩更重要。')
assert 0.5 < n_qv64 / n_all8 < 2.0, '两种配置的参数量应在同一量级（可公平比较）'

# target_modules 名字填错的报错
try:
    lora_params(['query', 'value'], 8); raise RuntimeError('不该到这')
except ValueError as e:
    print(f'\\n❌ 名字填错: {str(e)[:80]}…')
print('   Llama 系是 q_proj/k_proj/...；BERT 系是 query/key/value/dense；GPT-2 是 c_attn/c_proj。')
print('✅ 可靠做法：先 print 一遍 named_modules()，或用 target_modules="all-linear"')"""),
    md("""## 4 · merge_and_unload：数值等价与不可逆"""),
    code("""base2 = Linear(D_IN, D_OUT, seed=5)
lora2 = LoRALinear(base2, r=16, lora_alpha=32, seed=6)
# 模拟「训练过」的 A、B
lora2.A = rng.normal(size=lora2.A.shape) / math.sqrt(D_IN)
lora2.B = rng.normal(size=lora2.B.shape) * 0.05

x2 = rng.normal(size=(8, D_IN))
before = lora2(x2)
W_before = base2.W.copy()
lora2.merge()
after = lora2(x2)
print('合并前后输出最大差:', float(np.abs(after - before).max()))
assert np.allclose(before, after, atol=1e-12), '合并必须数值等价'
assert not np.allclose(base2.W, W_before), '基座权重已被修改'
print('✅ merge 数值等价：W <- W + (α/r)·A@B')

# 合并后 LoRA 分支「消失」：改 A/B 不再影响输出
out1 = lora2(x2)
lora2.A = lora2.A * 100
out2 = lora2(x2)
assert np.allclose(out1, out2), '合并后 LoRA 分支已不参与前向 -> 无法继续训练'
print('✅ 合并后改 A/B 不再影响输出 -> **不能继续 LoRA 训练**（只能当普通模型全量训）')

# unmerge 可以还原（前提是你没改过 A/B）
lora2.A = lora2.A / 100
lora2.unmerge()
assert np.allclose(base2.W, W_before, atol=1e-12), 'unmerge 应还原基座权重'
print('✅ unmerge 能还原 —— 但生产上 merge_and_unload 后 adapter 就丢了，实际不可逆')
print('\\n规则：**训练与实验期不合并**（保留多 adapter 切换）；**上线时合并**（推理零开销）。')"""),
    md("""### 未合并的推理开销：FLOPs 只涨 0.8%，但延迟可能涨 10-20%"""),
    code("""def lora_flops_overhead(r, d_in, d_out):
    '''LoRA 分支的额外 FLOPs 相对原矩阵乘的比例。'''
    base = 2 * d_in * d_out
    extra = 2 * d_in * r + 2 * r * d_out
    return extra / base

print(f"{'r':>4s} {'d=4096':>10s} {'d=1024':>10s}")
for r in [8, 16, 32, 64]:
    print(f'{r:>4d} {lora_flops_overhead(r,4096,4096):>10.2%} {lora_flops_overhead(r,4096,1024):>10.2%}')
o16 = lora_flops_overhead(16, 4096, 4096)
assert o16 < 0.01, 'r=16, d=4096 时额外 FLOPs 不到 1%'
print(f'\\n✅ FLOPs 只涨 {o16:.2%}，但因为是**两个小 kernel**（启动开销 + 显存往返占主导），')
print('   实测延迟增加常在 10-20%。这就是上线前该 merge 的理由。')"""),
    md("""## 5 · 参数量与显存账：LoRA 到底省了什么"""),
    code("""BYTES = {'fp32': 4, 'bf16': 2, 'fp16': 2, 'int8': 1, 'nf4': 0.5}

def train_memory_gb(n_total, n_trainable, weight_dtype='bf16', opt_bytes=8, activations_gb=6.0):
    w = n_total * BYTES[weight_dtype]
    g = n_trainable * BYTES[weight_dtype]
    o = n_trainable * opt_bytes
    return {'权重': w/1e9, '梯度': g/1e9, '优化器': o/1e9,
            '激活': activations_gb, '合计': (w+g+o)/1e9 + activations_gb}

N7B = 7.0e9
rows = [
    ('全量微调 bf16',        N7B, N7B,                     'bf16', 8),
    ('LoRA r=8 仅q,v',      N7B, lora_params(QV, 8),       'bf16', 8),
    ('LoRA r=16 全部层',     N7B, lora_params(ALL, 16),     'bf16', 8),
    ('QLoRA r=64 全部层',    N7B, lora_params(ALL, 64),     'nf4', 8),
]
print(f"{'配置':<24s} {'可训练':>10s} {'权重':>7s} {'梯度':>7s} {'优化器':>8s} {'合计GB':>8s}")
mems = {}
for label, nt, ntr, dt, ob in rows:
    m = train_memory_gb(nt, ntr, dt, ob)
    mems[label] = m['合计']
    print(f'{label:<24s} {ntr/1e6:>8.1f}M {m["权重"]:>7.1f} {m["梯度"]:>7.2f} '
          f'{m["优化器"]:>8.2f} {m["合计"]:>8.1f}')

assert mems['全量微调 bf16'] > 70, '全量微调 7B 需 70GB+'
assert mems['LoRA r=16 全部层'] < 30, 'LoRA 单卡可行'
assert mems['QLoRA r=64 全部层'] < mems['LoRA r=16 全部层'], 'QLoRA 显存最低'
print(f'\\n✅ 省显存的主力是**优化器状态按可训练参数算**：')
print(f'   全量的 {train_memory_gb(N7B,N7B)["优化器"]:.0f} GB -> LoRA 的 '
      f'{train_memory_gb(N7B, lora_params(ALL,16))["优化器"]:.2f} GB')
print('   ⚠️ 但 QLoRA 训练**更慢**（反量化开销，约为 bf16 LoRA 的 60-70% 速度）——')
print('      它是「放不下时的解法」，不是「更快的解法」。')"""),
    code("""def checkpoint_gb(n_trainable, weight_dtype='bf16', opt_bytes=8, save_optimizer=True):
    b = n_trainable * BYTES[weight_dtype]
    if save_optimizer: b += n_trainable * opt_bytes
    return b / 1e9

print(f"{'配置':<24s} {'单 checkpoint':>15s} {'save_total_limit=3':>20s}")
for label, ntr in [('全量微调', N7B), ('LoRA r=8 仅q,v', lora_params(QV, 8)),
                   ('LoRA r=16 全部层', lora_params(ALL, 16))]:
    c = checkpoint_gb(ntr)
    print(f'{label:<24s} {c:>13.2f} GB {c*3:>18.2f} GB')
c_full, c_lora = checkpoint_gb(N7B), checkpoint_gb(lora_params(ALL, 16))
assert c_full / c_lora > 80, 'LoRA 的 checkpoint 应小两个数量级'
print(f'\\n✅ checkpoint 小 {c_full/c_lora:.0f} 倍 —— 这改变了实验方式：')
print('   你可以毫无压力地保存二十个实验的 adapter，而全量微调时连三个都要考虑磁盘。')
print('   **LoRA 的价值不只是省显存，而是把微调从重工程变成轻工程。**')"""),
    md("""## 6 · SFT：chat template 与 completion-only 掩码

**SFT 只应对 assistant 的回答计损失**，system/user 部分填 `-100`。
不掩的话模型会同时学「生成用户提问」——loss 更低但推理时会自己编下一句用户话。"""),
    code("""# 一个迷你 chat template（真实模型各有不同，必须用 tokenizer.apply_chat_template）
TEMPLATE = {
    'system': ('<|system|>', '<|end|>'),
    'user': ('<|user|>', '<|end|>'),
    'assistant': ('<|assistant|>', '<|end|>'),
}
SPECIALS = ['<|system|>', '<|user|>', '<|assistant|>', '<|end|>']

def apply_chat_template(messages, add_generation_prompt=False):
    parts = []
    for m in messages:
        o, c = TEMPLATE[m['role']]
        parts.append(f'{o}{m["content"]}{c}')
    if add_generation_prompt:
        parts.append(TEMPLATE['assistant'][0])
    return ''.join(parts)

def tokenize(text):
    '''把特殊 token 当整体，其余按字符切（迷你实现）。'''
    toks, i = [], 0
    while i < len(text):
        hit = next((s for s in SPECIALS if text.startswith(s, i)), None)
        if hit: toks.append(hit); i += len(hit)
        else:   toks.append(text[i]); i += 1
    return toks

msgs = [{'role': 'system', 'content': 'be nice'},
        {'role': 'user', 'content': 'hi'},
        {'role': 'assistant', 'content': 'hello'}]
text = apply_chat_template(msgs)
toks = tokenize(text)
print('拼接结果:', text)
print('token 数:', len(toks))
assert text.startswith('<|system|>') and text.endswith('<|end|>')
print('\\n✅ 必须用模型自己的 chat template —— 手写拼接几乎一定在某个特殊 token 上出错。')"""),
    code("""def completion_only_labels(toks, response_template='<|assistant|>', ignore=-100):
    '''对应 DataCollatorForCompletionOnlyLM：只对 response_template 之后的 token 计损失。'''
    labels = [ignore] * len(toks)
    try:
        start = toks.index(response_template) + 1
    except ValueError:
        return labels                                 # 找不到模板 -> 全部忽略（要告警！）
    for i in range(start, len(toks)):
        labels[i] = i                                  # 用下标代替真实 token id（示意）
    return labels

labs = completion_only_labels(toks)
n_signal = sum(1 for x in labs if x != -100)
print(f'总 token {len(toks)}, 计损失的 {n_signal} 个 ({n_signal/len(toks):.0%})')
print('计损失的部分:', ''.join(toks[len(toks)-n_signal:]))
assert n_signal == len('hello') + 1, '只有 assistant 的回答（含结尾 <|end|>）计损失'
assert labs[0] == -100, 'system 部分必须忽略'

# 反例：全部计损失
all_labels = list(range(len(toks)))
print(f'\\n❌ 全部计损失: {len(all_labels)} 个 token 都在学 -> 模型也在学「生成用户提问」')
print(f'   信号占比 100% vs 正确做法的 {n_signal/len(toks):.0%}')
assert len(all_labels) > n_signal
print('   症状：loss 更低（用户提问也可预测），但推理时模型会自己接着编用户的下一句。')

# 找不到 response_template 时必须告警（否则整条样本零信号）
weird = tokenize('<|user|>hi<|end|>')
labs_bad = completion_only_labels(weird)
assert all(x == -100 for x in labs_bad)
print('\\n⚠️  response_template 与 chat template 不一致时，整条样本**零训练信号**且不报错。')
print('   防护：统计「零信号样本」的比例，>1% 就告警。')"""),
    md("""### packing 的取舍：吞吐翻倍，但改变样本权重"""),
    code("""def pack_sequences(lengths, max_len):
    '''贪心装箱：把多条短样本拼进定长序列。'''
    bins, cur = [], []
    for L in lengths:
        if sum(cur) + L > max_len:
            bins.append(cur); cur = []
        cur.append(L)
    if cur: bins.append(cur)
    return bins

r = np.random.default_rng(7)
lens = list(r.integers(20, 200, size=200))
MAXL = 512
bins = pack_sequences(lens, MAXL)
padded_tokens = len(lens) * MAXL                      # 每条单独 padding 到 512
packed_tokens = len(bins) * MAXL
print(f'200 条样本（长 20-200），max_len={MAXL}:')
print(f'  不 packing: {len(lens)} 个序列 -> {padded_tokens:,} token（含大量 padding）')
print(f'  packing   : {len(bins)} 个序列 -> {packed_tokens:,} token')
print(f'  吞吐提升: {padded_tokens/packed_tokens:.1f}×')
assert packed_tokens < padded_tokens / 2, 'packing 应至少省一半'

# 但样本权重变了：长样本贡献更多 token -> 梯度权重更大
w_nopack = [1.0 / len(lens)] * len(lens)              # 每条样本等权
w_pack = [L / sum(lens) for L in lens]                # 按 token 数加权
print(f'\\n最短样本权重: 不packing {w_nopack[int(np.argmin(lens))]:.5f} | '
      f'packing {w_pack[int(np.argmin(lens))]:.5f}')
print(f'最长样本权重: 不packing {w_nopack[int(np.argmax(lens))]:.5f} | '
      f'packing {w_pack[int(np.argmax(lens))]:.5f}')
ratio = max(w_pack) / min(w_pack)
assert ratio > 5, 'packing 下长短样本的权重差异显著'
print(f'\\n⚠️  packing 下长/短样本的梯度权重差 {ratio:.1f}× —— 原来是等权的。')
print('✅ 规则：数据量大且长度接近 -> 开 packing；数据少或长度差异大 -> 别开。')"""),
    md("""## 7 · DPO：损失、beta 与长度偏差

$$\\mathcal{L} = -\\log\\sigma\\!\\left(\\beta\\left[\\log\\frac{\\pi(y_w|x)}{\\pi_{ref}(y_w|x)}
- \\log\\frac{\\pi(y_l|x)}{\\pi_{ref}(y_l|x)}\\right]\\right)$$"""),
    code("""def sigmoid(z): return 1.0 / (1.0 + np.exp(-z))

def dpo_loss(logp_pol_w, logp_ref_w, logp_pol_l, logp_ref_l, beta=0.1):
    '''标准 DPO（sigmoid）损失。四个都是「整条回答的 log 概率」。'''
    margin = (logp_pol_w - logp_ref_w) - (logp_pol_l - logp_ref_l)
    return float(-np.log(sigmoid(beta * margin) + 1e-12)), float(margin)

# 场景：参考模型对两个回答的 logprob 固定，策略在往「偏好 chosen」的方向移动
ref_w, ref_l = -20.0, -22.0
print(f"{'策略偏移':>10s} {'margin':>9s} " + ' '.join(f'β={b:<8.2f}' for b in [0.01, 0.1, 0.5]))
for shift in [-2.0, 0.0, 1.0, 3.0, 6.0]:
    pol_w, pol_l = ref_w + shift, ref_l - shift
    row = []
    for b in [0.01, 0.1, 0.5]:
        L, m = dpo_loss(pol_w, ref_w, pol_l, ref_l, beta=b)
        row.append(f'{L:<10.4f}')
    _, m = dpo_loss(pol_w, ref_w, pol_l, ref_l)
    print(f'{shift:>10.1f} {m:>9.1f} ' + ' '.join(row))

L0, _ = dpo_loss(ref_w, ref_w, ref_l, ref_l, beta=0.1)
assert abs(L0 - math.log(2)) < 1e-6, '策略=参考时 margin=0，损失应为 ln2'
L_good, _ = dpo_loss(ref_w + 3, ref_w, ref_l - 3, ref_l, beta=0.1)
L_bad, _ = dpo_loss(ref_w - 2, ref_w, ref_l + 2, ref_l, beta=0.1)
assert L_good < L0 < L_bad, '朝偏好方向移动损失下降，反向则上升'
print(f'\\n✅ 策略=参考时损失恰为 ln2={math.log(2):.4f}（DPO 的自然起点）')

# beta 的作用：同样的 margin，beta 越大梯度越饱和（更保守）
print('\\nbeta 的作用（同样 margin=6）:')
for b in [0.01, 0.1, 0.5, 1.0]:
    L, _ = dpo_loss(ref_w + 3, ref_w, ref_l - 3, ref_l, beta=b)
    grad_mag = b * (1 - sigmoid(b * 6.0))          # dL/dmargin 的绝对值
    print(f'  β={b:<5.2f} loss {L:.4f}  |dL/dmargin| {grad_mag:.5f}')
g_small = 0.01 * (1 - sigmoid(0.01 * 6))
g_large = 1.0 * (1 - sigmoid(1.0 * 6))
assert g_small < 0.01 and g_large < 0.01, '两端梯度都小（原因不同）'
print('\\n✅ β 太小 -> 梯度小、几乎学不动；β 太大 -> 很快饱和、且策略被强约束在参考附近。')
print('   实践区间 0.01-0.5，常用 0.1。调 β 时**必须同时监控非目标能力**（C23）。')"""),
    code("""# 长度偏差：偏好数据里 chosen 系统性更长 -> DPO 学到「更长 = 更好」
def seq_logprob(n_tokens, per_token_lp=-2.0):
    '''整条回答的 logprob ≈ token 数 × 每 token 平均 logprob（负数）。'''
    return n_tokens * per_token_lp

print(f"{'chosen长':>8s} {'rejected长':>10s} {'ref margin':>11s} {'说明':<30s}")
for nw, nl, note in [(50, 50, '长度相同：margin 只反映质量'),
                     (100, 50, 'chosen 更长'),
                     (200, 50, 'chosen 长得多')]:
    m = (seq_logprob(nw) - seq_logprob(nw)) - (seq_logprob(nl) - seq_logprob(nl))
    # 策略略微提高每 token 概率时，长回答的 logprob 变化更大
    d_w = seq_logprob(nw, -1.9) - seq_logprob(nw, -2.0)
    d_l = seq_logprob(nl, -1.9) - seq_logprob(nl, -2.0)
    print(f'{nw:>8d} {nl:>10d} {d_w - d_l:>11.2f}  {note:<30s}')

d_eq = (seq_logprob(50,-1.9)-seq_logprob(50,-2.0)) - (seq_logprob(50,-1.9)-seq_logprob(50,-2.0))
d_uneq = (seq_logprob(200,-1.9)-seq_logprob(200,-2.0)) - (seq_logprob(50,-1.9)-seq_logprob(50,-2.0))
assert abs(d_eq) < 1e-9 and d_uneq > 10
print(f'\\n⚠️  长度相同时「整体提高每 token 概率」对 margin 无贡献（{d_eq:.2f}）；')
print(f'   chosen 长 4 倍时，同样的改动让 margin 涨 {d_uneq:.1f} —— ')
print('   **模型只要「学着输出更长」就能降低 DPO 损失**，不需要真的变好。')
print('✅ 这就是文献中反复出现的长度偏差。缓解：loss_type="ipo"、长度归一化、数据侧平衡长度。')"""),
    md("""## ✏️ 练习 1：LoRA 参数量与占比

实现 `lora_summary(target_modules, r, n_layers, base_total)`：
返回 `{'trainable': N, 'pct': 占比, 'checkpoint_mb': adapter 大小(bf16, 不含优化器)}`。"""),
    code("""def lora_summary(target_modules, r, n_layers, base_total):
    # TODO: trainable = Σ r*(d_in+d_out) * n_layers（用 LAYER_MODULES 查维度）
    #       pct = trainable / base_total
    #       checkpoint_mb = trainable * 2 / 1e6
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s = lora_summary(['q_proj', 'v_proj'], 8, 32, base_params())
assert abs(s['trainable'] - lora_params(['q_proj','v_proj'], 8)) < 1
assert 0.0001 < s['pct'] < 0.01
assert 5 < s['checkpoint_mb'] < 50, f'adapter 应是几十 MB，得到 {s["checkpoint_mb"]:.1f}'
s2 = lora_summary(list(LAYER_MODULES), 64, 32, base_params())
assert s2['trainable'] > s['trainable'] * 20
print(f"r=8 仅q,v : {s['trainable']/1e6:>7.1f}M ({s['pct']:.3%}), adapter {s['checkpoint_mb']:.0f} MB")
print(f"r=64 全部 : {s2['trainable']/1e6:>7.1f}M ({s2['pct']:.3%}), adapter {s2['checkpoint_mb']:.0f} MB")
print('✅ 练习 1 通过：这个函数应该在你配 LoraConfig 之后立刻跑一遍')"""),
    md("""## ✏️ 练习 2：completion-only 掩码的通用版

实现 `mask_until(tokens, response_template, ignore=-100)`：
返回 `(labels, n_signal, found)`。
支持**多轮对话**——每次出现 `response_template` 之后到下一个非 assistant 段之前都计损失。
简化规则：遇到 `response_template` 开启计损失，遇到 `<|user|>` 或 `<|system|>` 关闭。"""),
    code("""def mask_until(tokens, response_template='<|assistant|>', ignore=-100):
    # TODO: 遍历；遇到 response_template -> 之后开启；遇到 <|user|>/<|system|> -> 关闭
    #       返回 (labels, 计损失的个数, 是否找到过 response_template)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
multi = tokenize(apply_chat_template([
    {'role': 'user', 'content': 'a'},
    {'role': 'assistant', 'content': 'bb'},
    {'role': 'user', 'content': 'c'},
    {'role': 'assistant', 'content': 'ddd'},
]))
labs, n, found = mask_until(multi)
assert found and n == (len('bb') + 1) + (len('ddd') + 1), f'两轮回答共 {n} 个 token'
# 用户段必须被忽略
i_user = multi.index('<|user|>')
assert labs[i_user] == -100
# 没有 assistant 段时 found=False
_, n0, f0 = mask_until(tokenize('<|user|>hi<|end|>'))
assert n0 == 0 and not f0
print(f'多轮对话 {len(multi)} token，计损失 {n} 个（{n/len(multi):.0%}）')
print('✅ 练习 2 通过：多轮 SFT 时**每一轮的回答都要计损失**，用户段全部忽略')"""),
    md("""## ✏️ 练习 3：DPO 的 beta 选择

实现 `dpo_gradient_magnitude(margin, beta)`：返回 `|dL/dmargin| = beta * (1 - sigmoid(beta*margin))`。
再实现 `best_beta(margin, candidates)`：返回让梯度幅度**最大**的 beta（即学习信号最强的那个）。"""),
    code("""def dpo_gradient_magnitude(margin, beta):
    # TODO
    raise NotImplementedError

def best_beta(margin, candidates):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert abs(dpo_gradient_magnitude(0.0, 0.1) - 0.05) < 1e-9, 'margin=0 时 = beta/2'
cands = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
b_small = best_beta(margin=1.0, candidates=cands)
b_large = best_beta(margin=20.0, candidates=cands)
print(f'margin=1  时梯度最大的 beta: {b_small}')
print(f'margin=20 时梯度最大的 beta: {b_large}')
assert b_large < b_small or b_large <= 0.5, 'margin 大时应选更小的 beta（避免饱和）'
# 两端都小：beta→0 或 beta→∞ 时梯度都趋于消失
assert dpo_gradient_magnitude(6.0, 0.001) < 0.01
assert dpo_gradient_magnitude(6.0, 10.0) < 0.01
print('✅ 练习 3 通过：beta 太小梯度小、太大饱和 —— 中间才有最强学习信号（常用 0.1）')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def lora_summary(target_modules, r, n_layers, base_total):
    trainable = sum(r * (LAYER_MODULES[m][0] + LAYER_MODULES[m][1])
                    for m in target_modules) * n_layers
    return {'trainable': trainable, 'pct': trainable / base_total,
            'checkpoint_mb': trainable * 2 / 1e6}"""),
    code("""# 练习 2 参考答案
def mask_until(tokens, response_template='<|assistant|>', ignore=-100):
    labels, on, found = [], False, False
    for t in tokens:
        if t == response_template:
            on, found = True, True
            labels.append(ignore); continue          # 模板本身不计损失
        if t in ('<|user|>', '<|system|>'):
            on = False; labels.append(ignore); continue
        labels.append(len(labels) if on else ignore)
    return labels, sum(1 for x in labels if x != ignore), found"""),
    code("""# 练习 3 参考答案
def dpo_gradient_magnitude(margin, beta):
    return beta * (1.0 - sigmoid(beta * margin))

def best_beta(margin, candidates):
    return max(candidates, key=lambda b: dpo_gradient_magnitude(margin, b))"""),
    md("""---
## 🧪 真实 API 对照胶囊：完整的 QLoRA + SFT + DPO 配方"""),
    code("""RECIPE = r'''
import torch
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from trl import SFTTrainer, SFTConfig, DPOTrainer, DPOConfig

CKPT = "meta-llama/Meta-Llama-3-8B-Instruct"
tok = AutoTokenizer.from_pretrained(CKPT)
if tok.pad_token is None: tok.pad_token = tok.eos_token   # Llama 系没有 pad token

# ── ① QLoRA 的四个组件 ──
bnb = BitsAndBytesConfig(load_in_4bit=True,
                         bnb_4bit_quant_type="nf4",
                         bnb_4bit_use_double_quant=True,
                         bnb_4bit_compute_dtype=torch.bfloat16)
base = AutoModelForCausalLM.from_pretrained(CKPT, quantization_config=bnb,
                                            device_map="auto",
                                            attn_implementation="sdpa")
base = prepare_model_for_kbit_training(base)        # ⚠️ 别漏！否则梯度流不过来
base.config.use_cache = False                        # 与 gradient checkpointing 冲突

lora = LoraConfig(
    r=64, lora_alpha=128,                            # α/r = 2，改 r 时不用重调 lr
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"],   # 覆盖面 > 秩
    lora_dropout=0.05, bias="none",
    task_type=TaskType.CAUSAL_LM,                    # ⚠️ 填错会冻住新初始化的头
)
model = get_peft_model(base, lora)
model.print_trainable_parameters()                   # 立刻确认可训练占比合理

# ── ② SFT：只对回答计损失 ──
sft = SFTTrainer(
    model=model,
    args=SFTConfig(output_dir="out/sft", max_length=2048,
                   packing=False,                    # 长度差异大时别开
                   completion_only_loss=True,        # 只对 assistant 计损失
                   per_device_train_batch_size=2,
                   gradient_accumulation_steps=8,    # B_eff = 16
                   learning_rate=2e-4,               # LoRA 的 lr 比全量微调大 10x
                   lr_scheduler_type="cosine", warmup_ratio=0.03,
                   num_train_epochs=2, bf16=True,
                   optim="paged_adamw_8bit",
                   logging_steps=10, save_strategy="epoch"),
    train_dataset=sft_ds,                            # {"messages":[...]} 格式
    processing_class=tok,
)
sft.train(); sft.model.save_pretrained("out/sft/adapter")   # 只存 adapter（几十 MB）

# ── ③ DPO：ref_model=None + LoRA -> 省一份模型 ──
dpo = DPOTrainer(
    model=sft.model,
    ref_model=None,                                  # 禁用 adapter 即得参考策略
    args=DPOConfig(output_dir="out/dpo", beta=0.1,
                   loss_type="sigmoid",              # 长度偏差严重时试 "ipo"
                   max_length=1024, max_prompt_length=512,
                   learning_rate=5e-6,               # DPO 的 lr 要比 SFT 小得多
                   per_device_train_batch_size=2,
                   gradient_accumulation_steps=8, bf16=True),
    train_dataset=pref_ds,                           # {"prompt","chosen","rejected"}
    processing_class=tok,
)
dpo.train()

# ── ④ 上线前合并（推理零开销，可直接给 vLLM）──
merged = dpo.model.merge_and_unload()
merged.save_pretrained("out/merged", safe_serialization=True)
tok.save_pretrained("out/merged")
'''
print(RECIPE)
for c in ['prepare_model_for_kbit_training', 'task_type', 'completion_only_loss',
          'ref_model=None', 'merge_and_unload', 'lora_alpha=128']:
    assert c in RECIPE, c
print('✅ 配方覆盖本模块全部要点（QLoRA 四组件 / task_type / 掩码 / ref_model / 合并）')"""),
    md("""### 小结
- **LoRA 四参数**：`r` 是容量、`α/r` 是缩放（**固定比值扫 r**，不要固定 α）、`target_modules` 的**覆盖面比秩更重要**、`lora_dropout` 小数据集才用。
- **`B=0` 初始化**让训练从原模型连续出发（已数值验证）；`A`、`B` 都随机会先破坏模型。
- **`task_type` 填错会冻住新初始化的头** → 准确率卡住且怎么调都不动。
- **`merge_and_unload` 数值等价但不可逆**；合并后不能继续 LoRA 训练。规则：实验期不合并、上线时合并。
- **QLoRA 是四个组件的组合**，`prepare_model_for_kbit_training` 不能漏；它显存最低但**训练更慢**（60–70% 速度）。
- **省显存的主力是优化器状态按可训练参数算**；checkpoint 小两个数量级 → 微调从重工程变轻工程。
- **SFT 必须只对回答计损失**；`response_template` 与 chat template 不一致会导致整条样本零信号且不报错。
- **packing 提升吞吐但改变样本权重**（长样本权重变大）；长度差异大时别开。
- **DPO 的 `beta`** 两端梯度都小，常用 0.1；`ref_model=None`+LoRA 省一份模型；警惕**长度偏差**。

下一站：**模块 05 · Accelerate、Hub 与推理 API** —— 把训练好的模型送出去、以及怎么调远端模型。"""),
]
