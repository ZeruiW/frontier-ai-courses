# -*- coding: utf-8 -*-
"""C50 模块 01 · transformers 核心抽象。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00；C01/C49 的模型结构概念"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_transformers_core.ipynb'),
    ("核心参考", "transformers 文档（Auto Classes / Model Loading / Generation Strategies）、safetensors 规范"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("triple", "三件套：config / model / tokenizer", "".join([
        P("<code>transformers</code> 的全部设计围绕一个三元组。理解这个三元组的<strong>职责边界</strong>，库就不再是黑箱。"),
        TABLE(["组件", "是什么", "存成什么文件", "谁决定它"], [
            ["<strong>config</strong>", "纯数据：层数、维度、头数、词表大小、激活函数、特殊 token id……", "<code>config.json</code>", "模型作者；<code>model_type</code> 字段是 <code>Auto*</code> 分发的依据"],
            ["<strong>model</strong>", "计算图 + 权重", "<code>model.safetensors</code>（或旧的 <code>pytorch_model.bin</code>）", "由 config 完全确定结构；权重从文件加载"],
            ["<strong>tokenizer</strong>", "文本 ↔ token id 的双向映射 + 特殊 token 规则", "<code>tokenizer.json</code> / <code>vocab.txt</code> / <code>tokenizer_config.json</code>", "与模型<strong>强绑定</strong>——换 tokenizer 等于换语言"],
        ]),
        CALLOUT("danger", "<p>三件套里最容易犯的错、后果也最严重的一个：<strong>tokenizer 与 model 不匹配</strong>。用 <code>bert-base-uncased</code> 的 tokenizer 去喂 <code>roberta-base</code> 的模型，代码<em>完全不会报错</em>——两者词表大小相近，id 都在合法范围内，前向能跑、loss 能降。但每个 id 在两个词表里对应<strong>完全不同的词</strong>，模型看到的是彻底的乱码。<em>症状是「训练正常但效果差得莫名其妙」，且极难排查</em>。铁律：<strong>tokenizer 与 model 必须从同一个 checkpoint 名字加载</strong>，把这个名字写成一个变量，绝不手写两遍。</p>", "tokenizer 与 model 必须同源"),
        P("三件套的另一个重要性质是<strong>config 完全决定结构</strong>。这意味着你可以："),
        CODE("""from transformers import AutoConfig, AutoModel

cfg = AutoConfig.from_pretrained("bert-base-uncased")
cfg.num_hidden_layers = 4          # 只要 4 层
model = AutoModel.from_config(cfg)  # 得到一个 4 层的随机初始化 BERT

# 或者：加载预训练权重但改掉分类头的类别数
from transformers import AutoModelForSequenceClassification
m = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased",
        num_labels=5,                       # 覆盖 config
        ignore_mismatched_sizes=True)       # 头的形状不匹配 -> 重新随机初始化头"""),
        P("<code>ignore_mismatched_sizes=True</code> 这个参数值得记住：<strong>它允许「主干加载预训练权重、头随机初始化」</strong>，这正是微调的标准情形。不加它，加载一个 <code>num_labels</code> 不同的分类模型会直接报错。"),
    ])),
    ("frompretrained", "from_pretrained 的六步：这一行到底做了什么", "".join([
        ASCII("""AutoModelForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=3)

  ① 解析来源
     是本地目录？是 Hub repo id？带 revision（分支/tag/commit）吗？
     -> 决定去 HF_HOME 缓存里找，还是走网络下载

  ② 下载/命中缓存
     config.json → 解析出 model_type="bert"
     缓存路径 ~/.cache/huggingface/hub/models--bert-base-uncased/snapshots/<sha>/
     ⚠️ 缓存按 **commit sha** 分目录，所以 revision 变了会重新下载

  ③ 分发到具体类
     MODEL_FOR_SEQUENCE_CLASSIFICATION_MAPPING["bert"] -> BertForSequenceClassification

  ④ 按 config 构建结构（此时权重是随机的）
     kwargs 里的 num_labels=3 覆盖 config 中的值

  ⑤ 加载权重文件并做 **键名匹配**
     model.safetensors 里的 state_dict 与模型的 named_parameters() 对齐
     ├─ missing_keys      : 模型要但文件里没有 → **随机初始化**（分类头就在这里）
     ├─ unexpected_keys   : 文件里有但模型不要 → 丢弃（如预训练的 MLM 头）
     └─ mismatched_keys   : 名字对但形状不对 → 报错，除非 ignore_mismatched_sizes=True

  ⑥ 后处理
     tie_weights（嵌入与输出层共享）/ dtype 转换 / device_map 放置 / eval() 模式""")
        ,
        DUAL(
            "第 ⑤ 步是<strong>整个加载过程里唯一会静默出问题的地方</strong>，必须学会读它的输出。<code>transformers</code> 会打印一段警告，告诉你哪些键 missing、哪些 unexpected。<em>微调时看到「分类头被随机初始化」的警告是<strong>正常且期望</strong>的</em>；但如果看到大量主干权重 missing（比如所有 <code>encoder.layer.*</code>），说明键名对不上——通常是模型类选错了或 checkpoint 结构不同，<strong>这时模型基本等于随机初始化</strong>。",
            "怎么显式检查而不依赖读日志？用 <code>output_loading_info=True</code>：<code>model, info = AutoModel.from_pretrained(..., output_loading_info=True)</code>，<code>info</code> 是一个含 <code>missing_keys / unexpected_keys / mismatched_keys / error_msgs</code> 的字典。<strong>把它写进你的加载函数里做断言</strong>——比如「missing_keys 里只允许出现 <code>classifier</code>」。这一个 assert 能挡住一整类难查的 bug。",
        ),
        CALLOUT("warn", "关于安全的一条硬规矩：<strong>优先用 <code>safetensors</code>，避免 <code>.bin</code></strong>。PyTorch 的 <code>.bin</code> 是 pickle 格式，<em>加载时会执行任意代码</em>——从不可信来源加载 <code>.bin</code> 等于运行陌生人的脚本。<code>safetensors</code> 是纯数据格式（header JSON + 张量字节），零拷贝、可 mmap、不执行代码。现代 <code>transformers</code> 默认优先选 safetensors；若必须加载 <code>.bin</code>，至少确认来源可信。另外 <code>trust_remote_code=True</code> 同理——它会执行 repo 里的 Python 代码，只对可信 repo 使用。"),
    ])),
    ("dtype", "dtype 与设备放置：三个最常混的参数", "".join([
        TABLE(["参数", "作用", "常见值", "坑"], [
            ["<code>torch_dtype</code>", "权重的数值精度", "<code>torch.float16</code> / <code>bfloat16</code> / <code>\"auto\"</code>", "<code>\"auto\"</code> 读 config 里的 <code>torch_dtype</code>；不指定则一律 fp32（显存 ×2）"],
            ["<code>device_map</code>", "把层分配到哪些设备", "<code>\"auto\"</code> / <code>\"cuda:0\"</code> / 字典", "<code>\"auto\"</code> 需要 <code>accelerate</code>；会做跨 GPU/CPU/磁盘的自动切分"],
            ["<code>low_cpu_mem_usage</code>", "边加载边放置，不先在 CPU 建整个模型", "<code>True</code>", "加载 70B 时几乎必需；否则先吃 140GB 内存"],
            ["<code>attn_implementation</code>", "选注意力 kernel", "<code>\"sdpa\"</code> / <code>\"flash_attention_2\"</code> / <code>\"eager\"</code>", "FA2 需要额外安装且只支持部分 dtype/架构"],
        ]),
        DUAL(
            "<strong>fp16 vs bf16</strong> 是最该搞清的一对。两者都是 16 位，但指数位/尾数位分配不同：fp16 有 10 位尾数、5 位指数（精度高、<em>动态范围小</em>），bf16 有 7 位尾数、8 位指数（精度低、<em>动态范围与 fp32 相同</em>）。<strong>训练时 bf16 明显更稳</strong>（不需要 loss scaling，不容易溢出为 inf）；推理时两者差别不大，但要看硬件支持（bf16 需要 Ampere 及以上）。<em>如果你在 fp16 训练里遇到 loss 变 nan，第一反应应该是换 bf16。</em>",
            "<strong><code>device_map=\"auto\"</code> 的行为值得知道细节</strong>：它按层顺序贪心地填满第一个设备、再填下一个，超出所有 GPU 就放 CPU（<code>offload</code>），再超出就放磁盘。这让你能在小卡上跑大模型，但<em>跨设备的层间传输会让推理慢好几倍</em>。所以它是「跑得起来」的手段，不是「跑得快」的手段。真要快就得靠张量并行（C39）或换更小的模型/量化（C27）。",
        ),
        CALLOUT("intuition", "显存的粗算公式值得背下来：<strong>推理显存 ≈ 参数量 × 每参数字节数 × 1.2</strong>（那 20% 是激活与碎片）。7B 模型 fp16 = 7e9 × 2 × 1.2 ≈ 17 GB；int4 量化 ≈ 4.2 GB。<strong>训练显存 ≈ 参数 × (2 权重 + 2 梯度 + 8 优化器状态) = 参数 × 12 字节</strong>（Adam fp32 状态），7B 训练要 84 GB——这就是为什么全量微调 7B 需要多卡，而 LoRA 只需一张卡（模块 04）。notebook 会把这个公式实现成工具。"),
    ])),
    ("heads", "任务头：AutoModelFor* 家族", "".join([
        P("同一个主干可以接不同的头，<code>transformers</code> 用 <code>AutoModelFor&lt;Task&gt;</code> 系列表达这件事。选错头是新手最常见的错误之一。"),
        TABLE(["类", "输出", "对应 C49 的范式", "labels 的形状"], [
            ["<code>AutoModel</code>", "隐状态 <code>(B, L, H)</code>，<strong>无头</strong>", "—（自己接头）", "不接受 labels"],
            ["<code>AutoModelForSequenceClassification</code>", "<code>(B, C)</code>", "序列分类（模块 03①）", "<code>(B,)</code> 类别 id，或 <code>(B,C)</code> 多标签"],
            ["<code>AutoModelForTokenClassification</code>", "<code>(B, L, K)</code>", "token 分类（模块 03②）", "<code>(B, L)</code>，忽略位置填 <code>-100</code>"],
            ["<code>AutoModelForQuestionAnswering</code>", "两个 <code>(B, L)</code>", "span 抽取（模块 03③）", "<code>start_positions</code> + <code>end_positions</code>"],
            ["<code>AutoModelForMaskedLM</code>", "<code>(B, L, V)</code>", "MLM（C49 模块 01）", "<code>(B, L)</code>，未掩位置填 <code>-100</code>"],
            ["<code>AutoModelForCausalLM</code>", "<code>(B, L, V)</code>", "CLM / 生成", "<code>(B, L)</code>，<strong>内部自动右移</strong>"],
            ["<code>AutoModelForSeq2SeqLM</code>", "<code>(B, L_tgt, V)</code>", "encoder-decoder（C49 模块 04）", "<code>(B, L_tgt)</code>，内部生成 <code>decoder_input_ids</code>"],
        ]),
        CALLOUT("danger", "<p><strong><code>AutoModelForCausalLM</code> 的 labels 会被内部自动右移</strong>——你传 <code>labels = input_ids</code>，库内部会做 <code>logits[..., :-1, :]</code> 对 <code>labels[..., 1:]</code>。<em>如果你自己先右移一遍再传进去，就等于移了两位，模型学的是「预测下下个 token」</em>。这个错误的症状是：loss 能降但生成完全不通顺。<strong>反过来，<code>AutoModelForSeq2SeqLM</code> 的 <code>labels</code> 不需要你右移</strong>（库会据它生成 <code>decoder_input_ids</code>），但如果你手动传了 <code>decoder_input_ids</code>，库就<em>不</em>再帮你移。这两个不对称是最容易踩的实现坑之一，notebook 会用 assert 把它钉死。</p>", "labels 的右移到底谁做"),
    ])),
    ("generate", "generate()：参数全解与最常见的误用", "".join([
        P("<code>model.generate()</code> 是一个参数极多的方法，但它们分成几个正交的组："),
        TABLE(["组", "参数", "作用"], [
            ["<strong>长度</strong>", "<code>max_new_tokens</code> / <code>min_new_tokens</code>", "<strong>用 <code>max_new_tokens</code> 而不是 <code>max_length</code></strong>——后者包含 prompt，会随输入变化"],
            ["<strong>解码策略</strong>", "<code>do_sample</code> / <code>num_beams</code>", "<code>do_sample=False, num_beams=1</code> 是贪心；<code>num_beams&gt;1</code> 是 beam search；<code>do_sample=True</code> 是采样"],
            ["<strong>采样形状</strong>", "<code>temperature</code> / <code>top_k</code> / <code>top_p</code> / <code>min_p</code>", "<strong>只在 <code>do_sample=True</code> 时生效</strong>——这是最高频的误用"],
            ["<strong>重复控制</strong>", "<code>repetition_penalty</code> / <code>no_repeat_ngram_size</code>", "缓解退化（C49 模块 04）"],
            ["<strong>停止</strong>", "<code>eos_token_id</code> / <code>stop_strings</code>", "多个 eos 可传列表；<code>stop_strings</code> 需要传 tokenizer"],
            ["<strong>beam 相关</strong>", "<code>length_penalty</code> / <code>early_stopping</code>", "只在 <code>num_beams&gt;1</code> 时有意义"],
            ["<strong>输出</strong>", "<code>return_dict_in_generate</code> / <code>output_scores</code>", "要 logprob 或注意力时必须开"],
        ]),
        CALLOUT("warn", "<strong>头号误用：设了 <code>temperature=0.7</code> 但没设 <code>do_sample=True</code></strong>。此时 <code>temperature</code> 被完全忽略，你得到的是贪心解码——但代码不报错，你会以为「temperature 没什么用」。新版本 <code>transformers</code> 会给警告，旧版本静默忽略。<em>反过来，<code>temperature=0</code> 在 <code>generate</code> 里是非法的（除零），要确定性输出应该用 <code>do_sample=False</code></em>。这与 OpenAI API 的 <code>temperature=0</code> 语义不同（那里是服务端把它翻译成贪心），是自建服务与 API 之间的一个常见混淆点。"),
        H3("三个还需要知道的细节"),
        UL([
            "<strong>batch 生成必须左 padding</strong>。decoder-only 模型生成时从序列末尾续写，如果用右 padding，pad token 会夹在 prompt 和生成之间。所以批量生成前要 <code>tokenizer.padding_side = 'left'</code>。<em>这个坑的症状是「单条生成正常、批量生成变差」</em>——极其常见。",
            "<strong><code>attention_mask</code> 必须传</strong>。padding 位置若不 mask，模型会去注意 pad token。<code>tokenizer(...)</code> 返回的字典里已经有它了，直接 <code>**inputs</code> 展开传进去就行——手写参数时容易漏。",
            "<strong>Llama 系没有 pad token</strong>。它们的 tokenizer 里 <code>pad_token</code> 是 <code>None</code>，批量处理会报错。标准做法是 <code>tokenizer.pad_token = tokenizer.eos_token</code>。<em>但注意：如果同时把 eos 当 pad 又要在 labels 里忽略 pad，就必须小心不要把真正的 eos 也忽略掉</em>（模块 03 会处理这个）。",
        ]),
        CODE("""# 一段可直接用的批量生成骨架
tok.padding_side = "left"                       # ① decoder-only 批量生成必须左 padding
if tok.pad_token is None:
    tok.pad_token = tok.eos_token               # ② Llama 系没有 pad token

inputs = tok(prompts, return_tensors="pt", padding=True, truncation=True,
             max_length=1024).to(model.device)  # ③ attention_mask 在返回的字典里

out = model.generate(
    **inputs,                                   # ④ 一定要展开传，别只传 input_ids
    max_new_tokens=256,                         # ⑤ 不用 max_length
    do_sample=True, temperature=0.7, top_p=0.9, # ⑥ 采样参数只在 do_sample=True 时生效
    repetition_penalty=1.05,
    pad_token_id=tok.pad_token_id,
)
# ⑦ 只解码新生成的部分（切掉 prompt）
gen = out[:, inputs["input_ids"].shape[1]:]
texts = tok.batch_decode(gen, skip_special_tokens=True)"""),
    ])),
    ("ledger", "算一笔账：显存与上下文预算", "".join([
        P("把本模块的参数变成两个必须会算的数字。"),
        MATH("\\text{推理显存} \\approx N_{params} \\times b_{dtype} \\times 1.2 + \\underbrace{2 \\cdot n_{layers} \\cdot n_{kv} \\cdot d_{head} \\cdot L \\cdot b_{dtype}}_{\\text{KV 缓存}}"),
        TABLE(["模型", "dtype", "权重", "KV(L=4096, B=1)", "合计（约）"], [
            ["Llama-3-8B", "fp16", "16.0 GB", "0.5 GB（GQA 8 组）", "≈ 20 GB"],
            ["Llama-3-8B", "int4", "4.5 GB", "0.5 GB", "≈ 6 GB"],
            ["Llama-3-70B", "fp16", "140 GB", "1.3 GB", "≈ 170 GB（多卡）"],
            ["Llama-3-70B", "int4", "35 GB", "1.3 GB", "≈ 44 GB（单 A100 80G 可跑）"],
        ]),
        P("训练侧的账更重要，因为它决定你能不能在手上的卡上训："),
        MATH("\\text{训练显存} \\approx N_{params}\\times\\underbrace{2}_{\\text{fp16权重}} + N_{params}\\times\\underbrace{2}_{\\text{梯度}} + N_{trainable}\\times\\underbrace{8}_{\\text{Adam fp32 状态}} + \\text{激活}"),
        P("注意第三项用的是 <code>N_trainable</code> 而不是 <code>N_params</code>——<strong>这正是 LoRA 省显存的根本原因</strong>：全量微调 7B 的优化器状态是 56 GB，LoRA（可训练参数 0.1%）只有 56 MB。模块 04 会把这个对比算完整。"),
        P("第二个必须会算的是<strong>上下文预算</strong>。它经常被忽略，直到线上出现「长输入被静默截断」的 bug："),
        MATH("L_{prompt}^{max} = \\underbrace{L_{model}}_{\\text{模型上限}} - \\underbrace{n_{special}}_{\\text{特殊token}} - \\underbrace{L_{gen}}_{\\text{生成预留}}"),
        CALLOUT("intuition", "把本模块浓缩成一句话：<strong><code>transformers</code> 的复杂度几乎全在「加载」与「生成」这两个动作的参数上，而它们的坑几乎全是「静默失败」——不报错、能跑、结果错</strong>。tokenizer 不匹配不报错、权重没加载上只给个警告、<code>temperature</code> 不生效只是被忽略、右 padding 批量生成只是变差一点。<em>所以本模块最该带走的不是参数表，而是一套显式检查的习惯</em>：加载后断言 <code>missing_keys</code>、生成前断言 <code>padding_side</code>、始终从同一个变量取 checkpoint 名字。"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>加载与量化的融合</strong>：<code>from_pretrained</code> 正在吸收越来越多的量化后端（bitsandbytes、GPTQ、AWQ、FP8、torchao），通过 <code>quantization_config</code> 统一接口。但不同后端支持的架构、dtype、是否可训练差异很大，「哪个量化在我的场景可用」目前只能靠试。",
            "<strong><code>generate</code> 的可组合性</strong>：解码策略从少数几种膨胀到几十种（对比解码、投机解码、DoLa、约束解码、结构化输出）。<code>LogitsProcessor</code> 与 <code>StoppingCriteria</code> 提供了扩展点，但组合多个策略时的交互（谁先谁后、是否互斥）缺乏统一规范。",
            "<strong>结构化输出与约束解码</strong>：让模型必须输出合法 JSON/正则/语法，做法有 grammar-constrained decoding、outlines/xgrammar 类库、以及服务端的 JSON mode。哪种在质量-速度上最优、约束是否会损害推理能力，仍在讨论。",
            "<strong>模型代码的分发方式</strong>：<code>trust_remote_code</code> 让新架构无需等库更新即可发布，但它是个真实的安全面。社区正在探索更安全的中间形态（声明式 config、受限执行环境），尚无定论。",
            "<strong>版本兼容与可复现</strong>：<code>transformers</code> 迭代极快，默认行为（如 <code>generate</code> 的默认参数、tokenizer 的特殊 token 处理）会变。<em>钉死版本 + 记录 revision commit sha</em> 是目前唯一可靠的复现手段（C40 有系统讨论）。",
        ]),
        CALLOUT("paper", "必读：transformers 文档的 <em>Auto Classes</em>、<em>Models（from_pretrained 的完整参数）</em>、<em>Generation Strategies</em> 与 <em>GenerationConfig</em> 四篇；safetensors 的格式规范（理解为什么它比 pickle 安全）；PyTorch 的 <em>Automatic Mixed Precision</em> 文档（fp16 vs bf16 的数值细节）。源码上建议读 <code>modeling_utils.py</code> 的 <code>_load_pretrained_model</code>（第 ⑤ 步的键名匹配全在那里）与 <code>generation/utils.py</code> 的 <code>_sample</code>。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · transformers 核心抽象（迷你复刻 Auto* / from_pretrained / generate）

目标：把 **config-model-tokenizer 三件套 → from_pretrained 的六步 → 权重键名匹配 → dtype/显存账 → generate 的采样逻辑** 从零写一遍，
并用 assert 钉死那些**静默失败**的坑。

路线：三件套与同源检查 → 六步加载与 loading_info → 键名匹配的三类差异 → 显存账 →
labels 右移的不对称 → generate 的解码策略 → 左 padding → ✏️ 练习 → 📖 答案 → 🧪 上下文预算胶囊。

> 心智模型：**这一层的坑几乎全是「静默失败」**——不报错、能跑、结果错。
> 所以要带走的不是参数表，而是一套**显式检查的习惯**。"""),
    md("""## 1 · 三件套与「同源检查」

`config` 是纯数据、`model` 由 config 完全确定、`tokenizer` 与 model **强绑定**。
先把三件套写出来，再实现一个能挡住「tokenizer/model 不匹配」的检查。"""),
    code("""import numpy as np, math, json, hashlib, random
rng = np.random.default_rng(0)

class Config:
    '''纯数据。model_type 是 Auto* 分发的依据。'''
    def __init__(self, model_type, vocab_size, hidden_size, num_layers, num_labels=2, **kw):
        self.model_type, self.vocab_size = model_type, vocab_size
        self.hidden_size, self.num_layers, self.num_labels = hidden_size, num_layers, num_labels
        for k, v in kw.items(): setattr(self, k, v)
    def to_dict(self): return dict(self.__dict__)
    @classmethod
    def from_dict(cls, d):
        d = dict(d); return cls(d.pop('model_type'), d.pop('vocab_size'),
                                d.pop('hidden_size'), d.pop('num_layers'), **d)

class Tokenizer:
    def __init__(self, name, vocab):
        self.name, self.vocab = name, vocab
        self.itos = {i: s for s, i in vocab.items()}
    @property
    def vocab_size(self): return len(self.vocab)
    def __call__(self, text):
        return [self.vocab.get(w, self.vocab['[UNK]']) for w in text.lower().split()]
    def decode(self, ids): return ' '.join(self.itos.get(i, '[UNK]') for i in ids)

class Model:
    def __init__(self, config, name='<random>'):
        self.config, self.name = config, name
        r = np.random.default_rng(abs(hash(name)) % (2**32))
        self.params = {f'layer.{l}.weight': r.normal(size=(config.hidden_size, config.hidden_size)) * 0.02
                       for l in range(config.num_layers)}
        self.params['embeddings.weight'] = r.normal(size=(config.vocab_size, config.hidden_size)) * 0.02
        self.params['classifier.weight'] = r.normal(size=(config.hidden_size, config.num_labels)) * 0.02

VOCAB_A = {w: i for i, w in enumerate(['[UNK]', '[CLS]', '[SEP]', 'good', 'bad', 'movie', 'film'])}
VOCAB_B = {w: i for i, w in enumerate(['[UNK]', '[CLS]', '[SEP]', 'film', 'movie', 'bad', 'good'])}
tok_a, tok_b = Tokenizer('model-a', VOCAB_A), Tokenizer('model-b', VOCAB_B)
cfg = Config('bert', vocab_size=len(VOCAB_A), hidden_size=8, num_layers=2)

text = 'good movie'
print(f'tok_a("{text}") = {tok_a(text)}  -> 解回: {tok_a.decode(tok_a(text))}')
print(f'tok_b("{text}") = {tok_b(text)}  -> 解回: {tok_b.decode(tok_b(text))}')
# 两个词表**大小相同、id 都合法**，但含义完全不同
ids_a = tok_a(text)
print(f'\\n⚠️  把 tok_a 的 id {ids_a} 交给 model-b 的词表解读 -> "{tok_b.decode(ids_a)}"')
assert tok_a.vocab_size == tok_b.vocab_size, '词表大小相同 -> 不会有任何越界报错'
assert tok_a(text) != tok_b(text), '但同一句话的 id 完全不同'
assert tok_b.decode(tok_a(text)) != text, '交叉使用会得到彻底的乱码'
print('   代码完全不报错、前向能跑、loss 会降 —— 但模型看到的是乱码。')"""),
    code("""def load_pair(checkpoint, registry):
    '''从**同一个变量**取名字加载 tokenizer 与 model —— 这就是防错的全部秘诀。'''
    tok, cfg_ = registry[checkpoint]
    model = Model(cfg_, name=checkpoint)
    # 显式同源检查
    assert tok.name == checkpoint, f'tokenizer 来源 {tok.name} != {checkpoint}'
    assert model.config.vocab_size == tok.vocab_size, \\
        f'词表大小不一致: model {model.config.vocab_size} vs tokenizer {tok.vocab_size}'
    return tok, model

REGISTRY = {
    'model-a': (tok_a, Config('bert', len(VOCAB_A), 8, 2)),
    'model-b': (tok_b, Config('bert', len(VOCAB_B), 8, 2)),
}
CKPT = 'model-a'                      # ← 只写一次，绝不手写两遍
t, m = load_pair(CKPT, REGISTRY)
print(f'加载成功: tokenizer={t.name}, model.vocab_size={m.config.vocab_size}')

# 反例：词表大小对不上时必须报错
bad_reg = {'x': (tok_a, Config('bert', vocab_size=999, hidden_size=8, num_layers=2))}
try:
    load_pair('x', bad_reg); raise RuntimeError('不该到这')
except AssertionError as e:
    print(f'✅ 同源检查拦住了: {e}')
print('\\n✅ 铁律：**把 checkpoint 名字写成一个变量**，tokenizer 与 model 都从它加载。')"""),
    md("""## 2 · from_pretrained 的六步与键名匹配

第 ⑤ 步（权重键名匹配）是**唯一会静默出问题**的地方。它产生三类差异：
`missing_keys`（模型要但文件没有 → **随机初始化**）、`unexpected_keys`（文件有但模型不要 → 丢弃）、
`mismatched_keys`（名字对但形状不对 → 报错，除非显式忽略）。"""),
    code("""# 模拟 Hub 上的一个「预训练 checkpoint」：有 MLM 头，没有分类头
PRETRAINED = {
    'embeddings.weight':  np.full((7, 8), 1.0),
    'layer.0.weight':     np.full((8, 8), 2.0),
    'layer.1.weight':     np.full((8, 8), 3.0),
    'mlm_head.weight':    np.full((8, 7), 4.0),      # 下游分类任务不需要它
}

def from_pretrained(config, state_dict, ignore_mismatched_sizes=False, output_loading_info=False):
    '''复刻第 ④~⑤ 步：先按 config 建结构（随机），再用 state_dict 覆盖能对上的键。'''
    model = Model(config, name='<random>')
    model_keys, file_keys = set(model.params), set(state_dict)
    missing = sorted(model_keys - file_keys)
    unexpected = sorted(file_keys - model_keys)
    mismatched, loaded = [], []
    for k in sorted(model_keys & file_keys):
        if model.params[k].shape != state_dict[k].shape:
            mismatched.append((k, tuple(state_dict[k].shape), tuple(model.params[k].shape)))
            if not ignore_mismatched_sizes:
                raise RuntimeError(
                    f'size mismatch for {k}: checkpoint {state_dict[k].shape} '
                    f'vs model {model.params[k].shape}. 传 ignore_mismatched_sizes=True 可跳过')
        else:
            model.params[k] = state_dict[k].copy(); loaded.append(k)
    info = {'missing_keys': missing, 'unexpected_keys': unexpected,
            'mismatched_keys': mismatched, 'loaded_keys': loaded}
    return (model, info) if output_loading_info else model

cfg3 = Config('bert', vocab_size=7, hidden_size=8, num_layers=2, num_labels=3)
model, info = from_pretrained(cfg3, PRETRAINED, output_loading_info=True)
for k, v in info.items():
    print(f'{k:<18s}: {v}')

assert info['missing_keys'] == ['classifier.weight'], '分类头是新的 -> 随机初始化（**这是期望行为**）'
assert info['unexpected_keys'] == ['mlm_head.weight'], '预训练的 MLM 头被丢弃'
assert 'layer.0.weight' in info['loaded_keys']
assert model.params['layer.0.weight'][0, 0] == 2.0, '主干权重必须真的被加载了'
assert abs(model.params['classifier.weight'][0, 0]) < 1.0, '分类头是小随机数'
print('\\n✅ 微调时看到「分类头随机初始化」是正常的；')
print('   但若 missing_keys 里出现大量 layer.* ，说明键名对不上 —— 模型基本等于随机初始化。')"""),
    code("""def assert_loaded_properly(info, allowed_missing_prefixes=('classifier',)):
    '''把「读日志」变成「断言」——这一个函数能挡住一整类难查的 bug。'''
    bad = [k for k in info['missing_keys']
           if not any(k.startswith(p) for p in allowed_missing_prefixes)]
    assert not bad, f'意外的 missing_keys（主干权重没加载上！）: {bad}'
    assert not info['mismatched_keys'], f'形状不匹配: {info["mismatched_keys"]}'
    return True

assert assert_loaded_properly(info)
print('✅ 正常加载通过检查')

# 反例：模型类选错，键名前缀完全不同
WRONG_PREFIX = {k.replace('layer.', 'encoder.layer.'): v for k, v in PRETRAINED.items()}
_, info_bad = from_pretrained(cfg3, WRONG_PREFIX, output_loading_info=True)
print(f'\\n键名前缀不匹配时 missing_keys = {info_bad["missing_keys"]}')
try:
    assert_loaded_properly(info_bad); raise RuntimeError('不该到这')
except AssertionError as e:
    print(f'✅ 断言拦住了: {str(e)[:90]}…')
print('\\n真实库里对应: model, info = AutoModel.from_pretrained(..., output_loading_info=True)')

# mismatched：改了 num_labels
cfg5 = Config('bert', vocab_size=7, hidden_size=8, num_layers=2, num_labels=5)
STORE_WITH_HEAD = dict(PRETRAINED); STORE_WITH_HEAD['classifier.weight'] = np.zeros((8, 3))
try:
    from_pretrained(cfg5, STORE_WITH_HEAD); raise RuntimeError('不该到这')
except RuntimeError as e:
    print(f'\\n改 num_labels(3->5) 时: {str(e)[:100]}…')
m5, i5 = from_pretrained(cfg5, STORE_WITH_HEAD, ignore_mismatched_sizes=True, output_loading_info=True)
assert i5['mismatched_keys'] and m5.params['classifier.weight'].shape == (8, 5)
print('✅ ignore_mismatched_sizes=True 允许「主干加载 + 头重初始化」——微调的标准情形')"""),
    md("""## 3 · 显存账：为什么全量微调 7B 要 84GB

$$\\text{推理} \\approx N \\cdot b_{dtype} \\cdot 1.2 \\qquad
\\text{训练} \\approx N\\cdot 2 + N\\cdot 2 + N_{trainable}\\cdot 8 + \\text{激活}$$

注意训练的第三项用的是 **可训练参数量**——这正是 LoRA 省显存的根本原因（模块 04）。"""),
    code("""BYTES = {'fp32': 4, 'fp16': 2, 'bf16': 2, 'int8': 1, 'int4': 0.5}

def inference_gb(n_params, dtype='fp16', overhead=1.2):
    return n_params * BYTES[dtype] * overhead / 1e9

def kv_cache_gb(n_layers, n_kv_heads, head_dim, seq_len, batch=1, dtype='fp16'):
    return 2 * n_layers * n_kv_heads * head_dim * seq_len * batch * BYTES[dtype] / 1e9

def training_gb(n_params, n_trainable=None, weight_dtype='fp16', activations_gb=4.0):
    n_trainable = n_params if n_trainable is None else n_trainable
    w = n_params * BYTES[weight_dtype]
    g = n_trainable * BYTES[weight_dtype]
    opt = n_trainable * 8                 # Adam: fp32 的 m 与 v
    return (w + g + opt) / 1e9 + activations_gb

print(f"{'模型':<16s} {'dtype':>6s} {'权重GB':>8s} {'KV(4k)GB':>9s} {'推理合计':>9s}")
for name, n, nl, nkv, hd in [('Llama-3-8B', 8.0e9, 32, 8, 128),
                             ('Llama-3-70B', 70.0e9, 80, 8, 128)]:
    for dt in ['fp16', 'int4']:
        kv = kv_cache_gb(nl, nkv, hd, 4096, 1, 'fp16')
        print(f'{name:<16s} {dt:>6s} {inference_gb(n, dt):>8.1f} {kv:>9.2f} {inference_gb(n,dt)+kv:>9.1f}')

assert inference_gb(8e9, 'fp16') < 21 and inference_gb(8e9, 'int4') < 6
assert inference_gb(70e9, 'int4') < 50, '70B int4 能进单张 80G 卡'
print(f'\\n训练 7B（全量）: {training_gb(7e9):.0f} GB   <- 单卡放不下')
print(f'训练 7B（LoRA, 可训练 0.1%）: {training_gb(7e9, n_trainable=7e6):.0f} GB   <- 单卡可以')
assert training_gb(7e9) > 70 and training_gb(7e9, n_trainable=7e6) < 35
print('✅ 优化器状态只按**可训练参数**算 —— 这就是 LoRA 的省显存原理（模块 04 展开）')"""),
    md("""## 4 · labels 的右移：两个方向相反的不对称

- `AutoModelForCausalLM`：你传 `labels = input_ids`，**库内部自动右移**。自己先移一遍 = 移了两位。
- `AutoModelForSeq2SeqLM`：`labels` **不需要**你右移（库据它生成 `decoder_input_ids`）；
  但你若手动传了 `decoder_input_ids`，库就**不再**帮你移。

用 assert 把这两个契约钉死。"""),
    code("""def causal_lm_loss(logits, labels):
    '''复刻 AutoModelForCausalLM 的内部右移：logits[:-1] 对 labels[1:]'''
    shift_logits = logits[:-1]
    shift_labels = labels[1:]
    m = shift_labels != -100
    if m.sum() == 0: return 0.0
    lp = shift_logits - shift_logits.max(-1, keepdims=True)
    lp = lp - np.log(np.exp(lp).sum(-1, keepdims=True))
    return float(-lp[np.arange(len(shift_labels))[m], shift_labels[m]].mean())

V, L = 10, 6
rng2 = np.random.default_rng(1)
ids = rng2.integers(0, V, size=L)
logits = rng2.normal(size=(L, V))
# 让 logits 在「预测下一个」的位置上正确
correct = np.full((L, V), -5.0)
for t in range(L - 1):
    correct[t, ids[t + 1]] = 5.0
correct[L - 1, ids[L - 1]] = 5.0

loss_right = causal_lm_loss(correct, ids)                    # ✅ 传原始 ids
manually_shifted = np.concatenate([ids[1:], [-100]])         # ❌ 自己先移了一遍
loss_double = causal_lm_loss(correct, manually_shifted)
print(f'labels=input_ids（正确）      : loss = {loss_right:.4f}')
print(f'labels=手动右移后（错误）      : loss = {loss_double:.4f}')
assert loss_right < 0.05, '正确用法下 loss 应接近 0'
assert loss_double > loss_right * 10, '自己再移一遍 -> 学的是「预测下下个 token」'
print('\\n⚠️  症状：loss 能降、不报错，但生成完全不通顺。')
print('✅ CausalLM: `labels = input_ids`，**不要自己移**。')

def seq2seq_prepare(labels, bos=0):
    '''复刻 Seq2SeqLM：据 labels 生成 decoder_input_ids（右移并前置 bos）。'''
    return np.concatenate([[bos], labels[:-1]])

tgt = np.array([3, 4, 5, 2])
dec_in = seq2seq_prepare(tgt)
print(f'\\nSeq2Seq: labels={tgt.tolist()} -> 库自动生成 decoder_input_ids={dec_in.tolist()}')
assert dec_in[0] == 0 and dec_in[1:].tolist() == tgt[:-1].tolist()
print('✅ Seq2SeqLM: labels **不用**你移；但你若手动传 decoder_input_ids，库就不帮你移了。')"""),
    md("""## 5 · generate()：解码策略与采样参数的生效条件

**头号误用：设了 `temperature` 却没设 `do_sample=True`** —— 参数被完全忽略，你得到的是贪心。
把三种策略都实现一遍，并验证参数的生效条件。"""),
    code("""def softmax(x):
    x = x - x.max(); e = np.exp(x); return e / e.sum()

def apply_warpers(logits, temperature=1.0, top_k=None, top_p=None):
    '''采样前的 logits 处理（真实库里叫 LogitsWarper）。'''
    lg = logits / max(temperature, 1e-8)
    if top_k:
        thresh = np.sort(lg)[-top_k]
        lg = np.where(lg >= thresh, lg, -np.inf)
    if top_p:
        order = np.argsort(-lg)
        p = softmax(lg[order]); cum = np.cumsum(p)
        keep = order[:max(1, int(np.searchsorted(cum, top_p)) + 1)]
        mask = np.full_like(lg, -np.inf); mask[keep] = lg[keep]; lg = mask
    return lg

def generate(logit_fn, max_new_tokens, do_sample=False, num_beams=1,
             temperature=1.0, top_k=None, top_p=None, eos=None, seed=0):
    '''三种策略：贪心 / 采样 / beam。**采样参数只在 do_sample=True 时生效**。'''
    r = np.random.default_rng(seed)
    if num_beams > 1:
        beams = [([], 0.0)]
        for _ in range(max_new_tokens):
            cands = []
            for seq, sc in beams:
                lg = logit_fn(tuple(seq)); lp = np.log(softmax(lg) + 1e-12)
                for t in np.argsort(lp)[-num_beams:]:
                    cands.append((seq + [int(t)], sc + float(lp[t])))
            beams = sorted(cands, key=lambda x: x[1], reverse=True)[:num_beams]
        return beams[0][0]
    seq = []
    for _ in range(max_new_tokens):
        lg = logit_fn(tuple(seq))
        if do_sample:
            lg = apply_warpers(lg, temperature, top_k, top_p)      # ← 只在这里生效
            t = int(r.choice(len(lg), p=softmax(lg)))
        else:
            t = int(np.argmax(lg))                                  # 贪心：忽略一切采样参数
        seq.append(t)
        if eos is not None and t == eos: break
    return seq

VOC = 8
def make_logit_fn(seed=0):
    def fn(prefix):
        r = np.random.default_rng((hash(prefix) ^ seed) % (2**32))
        return r.normal(size=VOC)
    return fn
fn = make_logit_fn(7)

greedy1 = generate(fn, 6, do_sample=False)
greedy2 = generate(fn, 6, do_sample=False, temperature=0.1, top_p=0.5, seed=99)
print(f'贪心                       : {greedy1}')
print(f'贪心 + temperature/top_p   : {greedy2}   ← 完全相同！参数被忽略了')
assert greedy1 == greedy2, '⚠️ do_sample=False 时，temperature/top_k/top_p 全部无效'

s1 = generate(fn, 6, do_sample=True, temperature=1.0, seed=1)
s2 = generate(fn, 6, do_sample=True, temperature=1.0, seed=2)
print(f'\\n采样 seed=1                : {s1}')
print(f'采样 seed=2                : {s2}   ← 不同（有随机性）')
assert s1 != s2, '采样应有随机性'

b = generate(fn, 6, num_beams=3)
print(f'beam=3                     : {b}')
print('\\n✅ 这就是最高频的误用：**temperature 只在 do_sample=True 时生效**。')
print('   注意与 OpenAI API 的语义差异：那里 temperature=0 被服务端翻译成贪心，')
print('   而 generate() 里 temperature=0 是非法的（除零）—— 要确定性请用 do_sample=False。')"""),
    md("""### 温度与 top-p 的效果：用熵量化"""),
    code("""def entropy_after(logits, **kw):
    return float(-(lambda p: (p * np.log(p + 1e-12)).sum())(softmax(apply_warpers(logits, **kw))))

lg = np.random.default_rng(3).normal(size=32) * 2
print(f'{"设置":<30s} {"熵(nat)":>9s} {"有效候选数":>11s}')
for label, kw in [('原始 (T=1)', dict()),
                  ('T=0.5 (更尖)', dict(temperature=0.5)),
                  ('T=2.0 (更平)', dict(temperature=2.0)),
                  ('top_k=5', dict(top_k=5)),
                  ('top_p=0.9', dict(top_p=0.9)),
                  ('T=0.7 + top_p=0.9', dict(temperature=0.7, top_p=0.9))]:
    h = entropy_after(lg, **kw)
    print(f'{label:<30s} {h:>9.3f} {math.exp(h):>11.2f}')

h1, h_low, h_high = entropy_after(lg), entropy_after(lg, temperature=0.5), entropy_after(lg, temperature=2.0)
assert h_low < h1 < h_high, '温度越低分布越尖（熵越小），越高越平'
assert entropy_after(lg, top_k=5) < h1, 'top-k 截断降低熵'
assert entropy_after(lg, top_p=0.9) < h1, 'top-p 截断降低熵'
print('\\n✅ exp(熵) 是「有效候选数」的直观度量。T 调分布形状，top-k/top-p 做硬截断。')
print('   实践：先用 top_p=0.9 截尾（去掉长尾垃圾），再用 T 微调多样性。')"""),
    md("""## 6 · 批量生成必须左 padding

decoder-only 从序列末尾续写。**右 padding 会把 pad token 夹在 prompt 与生成之间。**"""),
    code("""PAD = -1

def pad_batch(seqs, side='right', pad=PAD):
    L = max(len(s) for s in seqs)
    out, mask = [], []
    for s in seqs:
        n = L - len(s)
        if side == 'right': out.append(list(s) + [pad] * n); mask.append([1]*len(s) + [0]*n)
        else:              out.append([pad] * n + list(s)); mask.append([0]*n + [1]*len(s))
    return np.array(out), np.array(mask)

prompts = [[1, 2, 3], [4, 5], [6]]
for side in ['right', 'left']:
    ids_, mask_ = pad_batch(prompts, side)
    last_real = [int(np.where(m == 1)[0][-1]) for m in mask_]
    print(f'{side:>5s} padding:')
    for row, lr in zip(ids_, last_real):
        print(f'   {row.tolist()}   最后一个真实 token 在下标 {lr}')

_, mask_left = pad_batch(prompts, 'left')
_, mask_right = pad_batch(prompts, 'right')
left_last = [int(np.where(m == 1)[0][-1]) for m in mask_left]
right_last = [int(np.where(m == 1)[0][-1]) for m in mask_right]
assert len(set(left_last)) == 1, '左 padding: 所有序列的「最后一个真实 token」都在同一列 -> 可以统一续写'
assert len(set(right_last)) > 1, '右 padding: 位置各不相同 -> 续写会从 pad 之后开始'
print(f'\\n左 padding 的最后真实位置: {left_last}  ← 全部相同 ✅')
print(f'右 padding 的最后真实位置: {right_last}  ← 各不相同 ❌')
print('\\n⚠️  症状：**单条生成正常，批量生成变差** —— 极其常见且容易归因错误。')
print('✅ 批量生成前：tokenizer.padding_side = "left"')
print('   注意：**训练时用右 padding**（labels 对齐更自然），只有生成才要左 padding。')"""),
    md("""## ✏️ 练习 1：显存可行性判断

实现 `fits_in_gpu(n_params, gpu_gb, mode, dtype='fp16', n_trainable=None, activations_gb=4.0)`：
`mode ∈ {'inference','train'}`，返回 `(是否放得下, 需要的GB)`。
推理用 `inference_gb`，训练用 `training_gb`。"""),
    code("""def fits_in_gpu(n_params, gpu_gb, mode, dtype='fp16', n_trainable=None, activations_gb=4.0):
    # TODO: 按 mode 选公式；返回 (need <= gpu_gb, need)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
ok, need = fits_in_gpu(8e9, 24, 'inference', 'fp16')
assert ok and 18 < need < 22, f'8B fp16 推理约 19GB，得到 {need:.1f}'
ok2, _ = fits_in_gpu(70e9, 80, 'inference', 'fp16')
assert not ok2, '70B fp16 放不进单张 80G'
ok3, _ = fits_in_gpu(70e9, 80, 'inference', 'int4')
assert ok3, '70B int4 可以'
ok4, need4 = fits_in_gpu(7e9, 80, 'train')
assert not ok4, f'7B 全量训练需要 {need4:.0f}GB，单张 80G 放不下'
ok5, need5 = fits_in_gpu(7e9, 80, 'train', n_trainable=7e6)
assert ok5, f'7B LoRA 训练只需 {need5:.0f}GB'
print(f'8B fp16 推理 {need:.1f}GB | 7B 全量训练 {need4:.0f}GB | 7B LoRA 训练 {need5:.0f}GB')
print('✅ 练习 1 通过：这个函数应该成为你每次选型的第一步')"""),
    md("""## ✏️ 练习 2：解码配置校验

实现 `validate_generation_config(cfg)`：接收一个 dict，返回**警告列表**（字符串）。要检出：
1. 设了 `temperature`/`top_k`/`top_p` 之一但 `do_sample` 不为 True → `'sampling params ignored'`
2. `num_beams > 1` 且 `do_sample` 为 True → `'beam sample is rarely what you want'`
3. 设了 `length_penalty` 但 `num_beams <= 1` → `'length_penalty ignored'`
4. 用了 `max_length` 而没用 `max_new_tokens` → `'prefer max_new_tokens'`
5. `temperature == 0` → `'temperature=0 is invalid; use do_sample=False'`"""),
    code("""def validate_generation_config(cfg):
    # TODO: 返回警告字符串列表（顺序不限）
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
w = validate_generation_config({'temperature': 0.7, 'max_new_tokens': 128})
assert 'sampling params ignored' in w, w
w2 = validate_generation_config({'do_sample': True, 'temperature': 0.7, 'max_new_tokens': 128})
assert w2 == [], f'正确配置不应有警告，得到 {w2}'
w3 = validate_generation_config({'do_sample': True, 'num_beams': 4, 'max_new_tokens': 64})
assert 'beam sample is rarely what you want' in w3
w4 = validate_generation_config({'length_penalty': 1.0, 'max_new_tokens': 64})
assert 'length_penalty ignored' in w4
w5 = validate_generation_config({'max_length': 512, 'do_sample': False})
assert 'prefer max_new_tokens' in w5
w6 = validate_generation_config({'do_sample': True, 'temperature': 0.0, 'max_new_tokens': 8})
assert 'temperature=0 is invalid; use do_sample=False' in w6
print('✅ 练习 2 通过：把这个校验函数放进你的推理封装里，能挡住最高频的一类误用')"""),
    md("""## ✏️ 练习 3：上下文预算

实现 `context_budget(model_max, n_special, reserve_for_generation, prompt_tokens)`：
返回 `(是否放得下, 可用于 prompt 的最大 token 数, 需要截掉多少)`。
若放得下，截掉量为 0。"""),
    code("""def context_budget(model_max, n_special, reserve_for_generation, prompt_tokens):
    # TODO: usable = model_max - n_special - reserve_for_generation
    #       返回 (prompt_tokens <= usable, usable, max(0, prompt_tokens - usable))
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
ok, usable, cut = context_budget(512, 3, 128, 300)
assert ok and usable == 381 and cut == 0
ok2, usable2, cut2 = context_budget(512, 3, 128, 500)
assert not ok2 and cut2 == 119, f'应截掉 119，得到 {cut2}'
# 生成预留越多，可用 prompt 越短
_, u_small, _ = context_budget(512, 3, 32, 100)
_, u_large, _ = context_budget(512, 3, 256, 100)
assert u_small > u_large
print(f'model_max=512, special=3: 预留 128 -> prompt 上限 {usable}；预留 256 -> 上限 {u_large}')
print('✅ 练习 3 通过：**长输入被静默截断**是线上最隐蔽的一类 bug —— 显式算预算并报警')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def fits_in_gpu(n_params, gpu_gb, mode, dtype='fp16', n_trainable=None, activations_gb=4.0):
    if mode == 'inference':
        need = inference_gb(n_params, dtype)
    elif mode == 'train':
        need = training_gb(n_params, n_trainable, dtype, activations_gb)
    else:
        raise ValueError(mode)
    return need <= gpu_gb, need"""),
    code("""# 练习 2 参考答案
def validate_generation_config(cfg):
    w = []
    sampling = [k for k in ('temperature', 'top_k', 'top_p') if k in cfg]
    if sampling and not cfg.get('do_sample'):
        w.append('sampling params ignored')
    if cfg.get('num_beams', 1) > 1 and cfg.get('do_sample'):
        w.append('beam sample is rarely what you want')
    if 'length_penalty' in cfg and cfg.get('num_beams', 1) <= 1:
        w.append('length_penalty ignored')
    if 'max_length' in cfg and 'max_new_tokens' not in cfg:
        w.append('prefer max_new_tokens')
    if cfg.get('temperature') == 0:
        w.append('temperature=0 is invalid; use do_sample=False')
    return w"""),
    code("""# 练习 3 参考答案
def context_budget(model_max, n_special, reserve_for_generation, prompt_tokens):
    usable = model_max - n_special - reserve_for_generation
    return prompt_tokens <= usable, usable, max(0, prompt_tokens - usable)"""),
    md("""---
## 🧪 真实 API 对照胶囊（不在本环境运行，可原样复制）

把本模块的每个检查写成一个**可复用的加载函数**。这段代码就是本模块的交付物。"""),
    code("""RECIPE = r'''
import torch
from transformers import (AutoConfig, AutoTokenizer,
                          AutoModelForSequenceClassification)

CKPT = "microsoft/deberta-v3-base"      # ① 只写一次，两边都从它加载
REVISION = "main"                        # 生产上建议钉 commit sha

def load_classifier(ckpt=CKPT, num_labels=3, revision=REVISION):
    tok = AutoTokenizer.from_pretrained(ckpt, revision=revision, use_fast=True)
    model, info = AutoModelForSequenceClassification.from_pretrained(
        ckpt, revision=revision,
        num_labels=num_labels,
        ignore_mismatched_sizes=True,     # ② 允许「主干加载 + 头重初始化」
        torch_dtype="auto",               # ③ 读 config 里的 dtype，别一律 fp32
        low_cpu_mem_usage=True,           # ④ 边加载边放置
        attn_implementation="sdpa",       # ⑤ 用 PyTorch 原生高效注意力
        output_loading_info=True,         # ⑥ 拿到 loading_info 做断言
    )
    # ⑦ 把「读日志」变成「断言」
    bad = [k for k in info["missing_keys"]
           if not k.startswith(("classifier", "pooler", "score"))]
    assert not bad, f"主干权重未加载: {bad[:5]}"
    assert model.config.vocab_size == len(tok), "tokenizer 与 model 词表不一致"
    return tok, model

# 批量生成（decoder-only）的正确姿势
def batch_generate(tok, model, prompts, max_new_tokens=256):
    tok.padding_side = "left"                       # ⑧ 生成必须左 padding
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token               # ⑨ Llama 系没有 pad token
    enc = tok(prompts, return_tensors="pt", padding=True,
              truncation=True, max_length=1024).to(model.device)
    with torch.inference_mode():
        out = model.generate(**enc,                 # ⑩ 一定要展开传（含 attention_mask）
                             max_new_tokens=max_new_tokens,
                             do_sample=True, temperature=0.7, top_p=0.9,
                             pad_token_id=tok.pad_token_id)
    gen = out[:, enc["input_ids"].shape[1]:]        # ⑪ 只解码新生成的部分
    return tok.batch_decode(gen, skip_special_tokens=True)
'''
print(RECIPE)
checks = ['只写一次', 'ignore_mismatched_sizes', 'output_loading_info',
          'padding_side = "left"', 'pad_token = tok.eos_token', '断言']
for c in checks:
    assert c in RECIPE, c
print(f'✅ 这段配方包含本模块的全部 {len(checks)} 项检查 —— 建议直接放进你的项目工具库')"""),
    md("""### 小结
- **三件套**：config 是纯数据、model 由 config 完全确定、tokenizer 与 model **强绑定**。把 checkpoint 名字写成变量，两边都从它加载。
- **`from_pretrained` 六步**里，第 ⑤ 步的键名匹配是唯一会静默出问题的地方。用 `output_loading_info=True` + 断言把它显式化。
- **优先 safetensors**（`.bin` 是 pickle，加载会执行任意代码）；`trust_remote_code` 同理。
- **显存账**：推理 ≈ N×dtype×1.2 + KV；训练 ≈ N×2 + N×2 + **N_trainable**×8 + 激活。最后一项用可训练参数量——这是 LoRA 省显存的根源。
- **labels 右移的两个不对称**：CausalLM 内部帮你移（别自己移）；Seq2SeqLM 不用你移（除非你手传 `decoder_input_ids`）。
- **`temperature` 只在 `do_sample=True` 时生效**；批量生成必须**左 padding**（训练用右 padding）。
- 这一层的坑几乎全是**静默失败**——所以要带走的是**显式检查的习惯**，不是参数表。

下一站：**模块 02 · tokenizers 与 datasets** —— 数据进模型之前的那两层，坑同样多。"""),
]
