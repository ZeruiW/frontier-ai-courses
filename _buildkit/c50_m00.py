# -*- coding: utf-8 -*-
"""C50 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python、numpy；C01/C49 的模型概念；C02 的 SFT/DPO 概念（模块 04 会用到）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 迷你复刻 + 真实 API 对照 + 优雅回退"),
    ("预计时长", "总览 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么", "".join([
        P("欢迎来到 <strong>HuggingFace 生态与 API 实操</strong>。这门课补的是一个非常具体、也非常尴尬的洞：<strong>全课体系「CPU-first、纯 numpy」的铁律，让你把每个算法的原理都吃透了，却没给你「用真实工具干活」的手艺</strong>。"),
        P("这个洞在面试和工作里都会被立刻发现。你能从零推导 LoRA 的低秩分解，但被问到「<code>target_modules</code> 该填什么、为什么 <code>q_proj,v_proj</code> 是默认」时答不上来；你理解 MLM 的 80/10/10，但不知道它在 <code>DataCollatorForLanguageModeling</code> 里就是三行；你会写 Adam，但不知道 <code>TrainingArguments</code> 里哪个参数控制梯度累积、为什么 <code>per_device_train_batch_size</code> 乘上它才是有效 batch。<em>这些都不是深奥的知识，但不知道就是不知道，而且它们是 JD 里明确写着的「Familiarity with Hugging Face libraries and OpenAI APIs」。</em>"),
        DUAL(
            "所以本课的定位很清楚：<strong>不重复讲算法原理（那是其他课的事），只讲「这个原理在生态里叫什么、参数在哪、默认值是什么、坑在哪」</strong>。它是一门<em>接口课</em>与<em>手艺课</em>，不是理论课。你可以把它当成一本带练习的、按「你已经懂原理」组织的生态手册。",
            "但本课不是文档的复述。文档告诉你<code>参数 X 的类型是 int</code>，本课告诉你<strong><code>X</code> 与 <code>Y</code> 相乘才是你真正关心的那个量、默认值在什么场景下会坑你、以及库内部到底做了什么</strong>。为此，每个模块都用<strong>「迷你复刻」</strong>的方式：用一百行 Python 把 <code>AutoModel</code> 的注册-分发机制、fast tokenizer 的 offset 映射、<code>Dataset.map</code> 的批处理语义、<code>Trainer</code> 的训练循环、LoRA 的权重注入、重试退避的客户端<em>自己写一遍</em>。写过之后，真实库对你就不再是黑箱。",
        ),
        CALLOUT("intuition", "学完你应当能回答这类问题（也是实操岗位的高频面试题）：<strong><code>AutoModel</code> 是怎么知道该实例化哪个类的？<code>from_pretrained</code> 到底做了几件事？<code>padding=True</code> 与 <code>padding='max_length'</code> 有什么区别、哪个更省算力？<code>Dataset.map(batched=True)</code> 为什么快十倍、什么时候会出错？<code>gradient_accumulation_steps</code> 与 <code>per_device_train_batch_size</code> 怎么组合成有效 batch？LoRA 的 <code>r</code> 与 <code>lora_alpha</code> 是什么关系？<code>merge_and_unload()</code> 之后还能继续训吗？OpenAI 客户端遇到 429 该怎么退避？</strong>"),
    ])),
    ("layers", "生态地图：五层抽象，各管一件事", "".join([
        ASCII("""你的代码
   │
   ├─ 🤗 transformers ──── 模型定义 + Auto* 分发 + generate()
   │      ├─ tokenizers ── 分词（Rust 实现的 fast tokenizer，带 offsets/word_ids）
   │      └─ safetensors ─ 权重序列化（零拷贝、不执行任意代码）
   │
   ├─ 🤗 datasets ──────── 数据加载与变换（Arrow 后端、内存映射、streaming）
   │
   ├─ 🤗 Trainer ───────── 训练循环的封装（optimizer/scheduler/日志/checkpoint/评估）
   │      └─ 🤗 accelerate ─ 设备与分布式的抽象（把 .to(device) 与 DDP/FSDP 藏起来）
   │
   ├─ 🤗 peft ──────────── 参数高效微调（LoRA / adapter / prefix-tuning）
   │   🤗 trl ──────────── 后训练算法（SFTTrainer / DPOTrainer / GRPOTrainer）
   │
   └─ openai / httpx ───── 调远端模型（OpenAI 兼容协议，见 C48 模块 02）

关键：**每一层都可以单独替换或跳过**。不喜欢 Trainer 就自己写循环；
不喜欢 datasets 就用 torch Dataset。理解分层，你才知道出问题时该看哪一层。""")
        ,
        TABLE(["层", "解决什么问题", "不用它的代价", "本课模块"], [
            ["<strong>transformers</strong>", "几百种模型的统一接口 + 权重加载 + 生成", "为每个模型手写加载与前向", "01"],
            ["<strong>tokenizers</strong>", "快速分词 + 子词到原文的 offset 映射", "自己实现 BPE 并处理对齐（模块 03 的坑）", "02"],
            ["<strong>datasets</strong>", "大数据集的内存映射、批处理变换、流式", "OOM 或自己写 Arrow/流式加载", "02"],
            ["<strong>Trainer</strong>", "训练循环的所有样板（日志/断点/评估/调度）", "每个项目重写一遍且各有 bug", "03"],
            ["<strong>peft / trl</strong>", "LoRA 注入与后训练算法的标准实现", "手写权重注入与 DPO 损失", "04"],
            ["<strong>accelerate</strong>", "单卡/多卡/混合精度的统一代码", "为每种设备写一套代码", "05"],
            ["<strong>Hub / safetensors</strong>", "模型分发、版本、安全加载", "自己搭权重存储与校验", "05"],
        ]),
        CALLOUT("warn", "分层带来一个很实际的调试原则：<strong>出问题时先定位是哪一层</strong>。「训练 loss 是 nan」——可能是数据层（标签里有 -100 以外的非法值）、模型层（dtype 溢出）、训练层（学习率过大）、或加速层（混合精度的 loss scaling）。<em>盲目改超参之前，先用最小复现把层数减到一层</em>：关掉 <code>fp16</code>、换成单进程、用 10 条数据、不用 Trainer 而手写循环。这条纪律能省掉大量无效调试。"),
    ])),
    ("offline", "方法论：迷你复刻 + 优雅回退", "".join([
        P("本课有一个必须诚实交代的约束：<strong>本环境不联网、没有 GPU、也不预装 <code>transformers</code></strong>。那怎么学一门讲库的课？"),
        P("答案是两条腿走路，而且这个安排其实<em>比直接跑真库学得更透</em>："),
        UL([
            "<strong>① 迷你复刻（主线，必跑）</strong>：用纯 Python 把库的<em>核心机制</em>重写一遍——<code>Auto*</code> 的注册表与分发、fast tokenizer 的 offset 映射与 <code>word_ids()</code>、<code>Dataset.map</code> 的批处理与缓存指纹、<code>Trainer</code> 的完整训练循环、LoRA 的权重注入与合并、令牌桶限流与指数退避。这些实现都在一两百行内，且带 <code>assert</code> 验证语义。<strong>它们不是「玩具」，而是真实库同一套逻辑的最小骨架</strong>。",
            "<strong>② 真实 API 对照（旁注，不跑）</strong>：每个迷你实现旁边紧跟真实库的等价调用，标注「这一步在库里叫什么、参数在哪、默认值是多少、什么时候会坑你」。这些代码是<strong>可以原样复制到有网环境使用的正确写法</strong>。",
        ]),
        P("此外，notebook 里所有涉及真实库的单元格都用 <code>try/except ImportError</code> 包裹并<strong>优雅回退</strong>——有库就跑真的，没库就跑迷你版并打印说明。你把这些 notebook 拷到有网环境，它们会自动升级成真实实验。"),
        CALLOUT("intuition", "为什么说这样学更透？因为<strong>「会调 API」和「知道 API 在做什么」是两回事，而后者才决定你能不能排查问题</strong>。当 <code>Trainer</code> 的 loss 不下降时，只会调 API 的人能做的只有换超参；写过训练循环的人会去看 <code>DataCollator</code> 返回的 <code>labels</code> 里 <code>-100</code> 的比例对不对。<em>本课的目标是把你变成后者</em>——而这恰好不需要 GPU。"),
    ])),
    ("map", "课程地图：从加载一个模型到调一个远端 API", "".join([
        ASCII("""模块 01  transformers 核心抽象
   Auto* 注册与分发 / config-model-tokenizer 三件套 / from_pretrained 的六步 /
   dtype 与 device_map / generate() 的参数全解与常见误用
        ▼
模块 02  tokenizers 与 datasets
   fast tokenizer 的 offsets 与 word_ids / padding-truncation 的四种组合 /
   Dataset.map 的批处理与指纹缓存 / IterableDataset 与 streaming / 动态 padding
        ▼
模块 03  Trainer 与 TrainingArguments
   训练循环拆解（Trainer 内部到底跑了什么）/ 有效 batch 的三个乘数 /
   DataCollator / compute_metrics / Callback / checkpoint 与断点续训 / 十个高频坑
        ▼
模块 04  PEFT 与 TRL
   LoRA 的 r / alpha / target_modules / dropout 到底怎么配 / adapter 的加载与合并 /
   QLoRA 的四个组件 / SFTTrainer 的数据格式 / DPOTrainer 的成对数据与 beta
        ▼
模块 05  Accelerate、Hub 与推理 API
   accelerate 的四行改造 / 混合精度与梯度累积的交互 / Hub 与 safetensors /
   OpenAI 兼容 client：重试退避、限流、流式、tool calling、结构化输出

终点：拿到一个任务，你能直接写出正确的加载、分词、训练、微调、部署与调用代码。""")
        ,
        P("每个模块的 notebook 都遵循同一个节奏：<strong>迷你复刻（带 assert）→ 真实 API 对照 → ✏️ 练习 → 📖 答案 → 🧪 参数账胶囊</strong>。「参数账胶囊」是本课特有的一环——把那些容易搞混的参数组合（有效 batch、LoRA 参数量、限流额度、上下文预算）算成具体数字。"),
        CALLOUT("paper", "本课与其他课的分工：<strong>C01/C20/C49 讲模型结构，C02/C22/C23 讲后训练算法，C21/C43 讲数据，C24/C48 讲部署</strong>；本课讲<em>把这些落到 HuggingFace 生态的具体手艺</em>。遇到「这个参数背后的原理是什么」的问题，本课会给出对应课程的指针而不重复讲解。"),
    ])),
    ("env", "环境与运行", "".join([
        P("本课全程 <strong>纯标准库 + numpy、CPU 可跑、不联网</strong>。所有 notebook 在 CPU 上实跑验证、assert 0 失败。"),
        CODE("""# 本环境（离线）：只需要 numpy
pip install -r requirements.txt

# 若你在有网环境想跑真实实验（可选，本课不依赖）：
pip install "transformers>=4.44" datasets accelerate peft trl safetensors openai"""),
        TABLE(["你需要", "本课怎么处理"], [
            ["<code>transformers</code>", "迷你复刻 <code>Auto*</code> 注册分发、config/model/tokenizer 三件套、<code>generate()</code> 的采样逻辑"],
            ["预训练权重", "用几十参数的迷你模型；真实权重的加载流程用「六步」讲清并模拟"],
            ["<code>tokenizers</code>", "手写一个带 <code>offsets</code> 与 <code>word_ids</code> 的迷你 fast tokenizer"],
            ["<code>datasets</code>", "手写 <code>map/filter/批处理/指纹缓存/IterableDataset</code> 的最小实现"],
            ["<code>Trainer</code>", "手写完整训练循环（含梯度累积、调度器、评估、checkpoint）"],
            ["<code>peft</code>", "用 numpy 实现 LoRA 注入、缩放、合并与参数量统计"],
            ["OpenAI API", "手写带令牌桶限流、指数退避、幂等键的客户端；用可控的假服务端驱动"],
        ]),
        P("还有一条关于怎么用这门课的建议：<strong>不要按顺序通读，要按问题查</strong>。这门课的六个模块本质上是六张「问题 → 参数」的映射表：模型加载不对劲查 01、数据形状与对齐出问题查 02、训练循环的参数关系查 03、显存不够或要微调大模型查 04、要分发或调远端模型查 05。<em>把它当手册用，遇到具体问题时回来查对应那一节</em>——这比通读一遍然后忘掉有效得多。但每个模块的 notebook 建议至少完整跑一遍，因为「亲手写过一遍」与「读过一遍」在排错能力上的差别非常大。"),
        P("最后要说清一个本课刻意<strong>不</strong>做的事：<strong>它不追新</strong>。生态每周都在变——新的量化后端、新的 DPO 变体、新的解码策略、参数改名与默认值调整。本课选的是那些<em>三年后大概率还在、且理解它们能让你自己读懂新东西</em>的部分：三件套的职责边界、权重键名匹配、-100 的约定、有效 batch 的乘法关系、LoRA 的四个参数、退避与限流的模式。<em>这些是生态的「语法」，而不断变化的库版本只是「词汇」</em>——语法学会了，新词汇查文档十分钟就懂。"),
        P("最后一句关于心态：<strong>这门课里没有任何「难」的东西，只有「不知道」的东西</strong>。所有内容都在文档里，但文档是按 API 组织的、不是按「你会遇到的问题」组织的。本课的价值就是把它重排成后者，并让你亲手把每个机制写一遍——<em>写过一遍之后，你对这些库的信心和排错能力会有质变。</em>"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与「迷你复刻」热身

本课全程 **纯标准库 + numpy、CPU、不联网**。学一门讲库的课而不装那些库，靠两条腿：
① **迷你复刻**——把库的核心机制用一两百行自己写一遍（必跑、带 assert）；
② **真实 API 对照**——旁边给出等价的真实调用（可原样复制到有网环境）。

这个 notebook 做三件事：① 环境自检与「优雅回退」模式；② 用一个最小例子体会 **注册表 + 分发** 这个贯穿全课的模式；③ 立下本课的三条纪律。"""),
    md("""## 1 · 环境自检与优雅回退

本课所有涉及真实库的单元格都用 `try/except ImportError` 包裹。
**有库就跑真的，没库就跑迷你版**——把这些 notebook 拷到有网环境，它们会自动升级。"""),
    code("""import sys, platform, math, json, hashlib, time, random
print('Python', sys.version.split()[0], '|', platform.system())
import numpy as np; print('numpy', np.__version__)

HAVE = {}
for name in ['torch', 'transformers', 'datasets', 'accelerate', 'peft', 'trl', 'openai']:
    try:
        mod = __import__(name)
        HAVE[name] = getattr(mod, '__version__', 'unknown')
    except ImportError:
        HAVE[name] = None

print('\\n真实库可用性:')
for k, v in HAVE.items():
    print(f'  {k:<14s} {v if v else "未安装 -> 走迷你复刻路径"}')
print('\\n环境就绪 ✅  —— 本课**不依赖**上述任何库，它们只是「有则更好」')"""),
    md("""### 优雅回退的标准写法

本课每个真实 API 对照都长这样。**注意它不是 try 一个大 block，而是先探测、再分支**——
这样错误信息清晰，且不会把真正的 bug 藏进 except 里。"""),
    code("""def with_fallback(real_fn, mini_fn, lib_name, *args, **kwargs):
    '''有库就跑真的，没库就跑迷你版。返回 (结果, 走的哪条路)。'''
    if HAVE.get(lib_name):
        try:
            return real_fn(*args, **kwargs), 'real'
        except Exception as e:                 # 库在但调用失败：**要报出来**，不要静默回退
            print(f'⚠️  {lib_name} 可用但调用失败: {type(e).__name__}: {e}')
            raise
    return mini_fn(*args, **kwargs), 'mini'

def real_tokenize(text):
    from transformers import AutoTokenizer          # 只有真装了才会执行到这
    return AutoTokenizer.from_pretrained('bert-base-uncased')(text)['input_ids']

def mini_tokenize(text):
    return [hash(w) % 30000 for w in text.lower().split()]

ids, path = with_fallback(real_tokenize, mini_tokenize, 'transformers', 'Hello world')
print(f'分词结果（走 {path} 路径）: {ids}')
assert isinstance(ids, list) and len(ids) >= 2
print('\\n✅ 优雅回退模式：**探测在前、分支在后**，绝不用 except 吞掉真正的 bug')""" ),
    md("""## 2 · 贯穿全课的模式：注册表 + 分发

`AutoModel` / `AutoTokenizer` / `AutoConfig` 看起来很神奇——你给一个名字，它就知道该实例化哪个类。
其实机制极简：**一张 `model_type -> 类` 的注册表，加一次字典查找**。

先把它写出来。理解了这个，模块 01 就没有黑箱了。"""),
    code("""# ── 迷你复刻：Auto* 的注册表与分发 ──
MODEL_REGISTRY = {}          # model_type -> 具体类
CONFIG_REGISTRY = {}

def register(model_type):
    '''装饰器：把一个类注册到表里。真实库用的是 OrderedDict + lazy import。'''
    def deco(cls):
        MODEL_REGISTRY[model_type] = cls
        return cls
    return deco

class MiniConfig:
    def __init__(self, model_type, **kw):
        self.model_type = model_type
        for k, v in kw.items(): setattr(self, k, v)
    def __repr__(self):
        return f'MiniConfig({self.__dict__})'

@register('bert')
class MiniBertModel:
    def __init__(self, config): self.config = config
    def kind(self): return 'encoder-only'

@register('gpt2')
class MiniGPT2Model:
    def __init__(self, config): self.config = config
    def kind(self): return 'decoder-only'

@register('t5')
class MiniT5Model:
    def __init__(self, config): self.config = config
    def kind(self): return 'encoder-decoder'

class MiniAutoModel:
    @staticmethod
    def from_config(config):
        mt = config.model_type
        if mt not in MODEL_REGISTRY:
            raise ValueError(f'Unrecognized model_type {mt!r}. '
                             f'Registered: {sorted(MODEL_REGISTRY)}')
        return MODEL_REGISTRY[mt](config)

for mt in ['bert', 'gpt2', 't5']:
    m = MiniAutoModel.from_config(MiniConfig(mt, hidden_size=768))
    print(f'{mt:<6s} -> {type(m).__name__:<16s} ({m.kind()})')

assert isinstance(MiniAutoModel.from_config(MiniConfig('bert')), MiniBertModel)
assert isinstance(MiniAutoModel.from_config(MiniConfig('t5')), MiniT5Model)
try:
    MiniAutoModel.from_config(MiniConfig('mystery-net'))
    raise RuntimeError('不该到这')
except ValueError as e:
    print(f'\\n未知类型的报错: {e}')
print('\\n✅ Auto* 不神奇：就是 `config.model_type` 查一次字典。')
print('   真实库的 config.json 里就有 "model_type" 字段 —— 它才是分发的依据。')"""),
    md("""**真实 API 对照**（不在本环境运行，可原样复制到有网环境）：

```python
from transformers import AutoConfig, AutoModel, AutoTokenizer

cfg = AutoConfig.from_pretrained("bert-base-uncased")
print(cfg.model_type)          # 'bert'  ← 这就是分发依据
model = AutoModel.from_config(cfg)              # 只建结构，不加载权重
model = AutoModel.from_pretrained("bert-base-uncased")   # 建结构 + 加载权重

# 注册自定义模型（写自己的模型时用）
AutoConfig.register("my-net", MyConfig)
AutoModel.register(MyConfig, MyModel)
```

**坑**：`from_config` 只建结构不加载权重（随机初始化）；`from_pretrained` 才加载。
把两者搞混会得到一个「能跑但输出全是噪声」的模型——这个错误极其常见且难以察觉。"""),
    md("""## 3 · 三条纪律

本课每个迷你复刻都要满足：

1. **语义对齐** —— 实现要与真实库的**契约**一致（同样的输入给同样的输出形状与边界行为），用 assert 钉死。
2. **参数账** —— 把容易搞混的参数组合算成具体数字（有效 batch、LoRA 参数量、上下文预算、限流额度）。
3. **坑要显式化** —— 每个模块都列出该层最高频的错误，并用一个可运行的反例演示它。

把第二条封装成一个小工具，后面每个模块都会用。"""),
    code("""def effective_batch(per_device, grad_accum, n_devices=1):
    '''有效 batch = 三个数的乘积。这是最常被搞混的参数组合，没有之一。'''
    return per_device * grad_accum * n_devices

print(f"{'per_device':>11s} {'accum':>6s} {'devices':>8s} {'有效batch':>9s}")
for pd, ga, nd in [(8, 1, 1), (8, 4, 1), (2, 16, 1), (8, 4, 8), (1, 32, 4)]:
    print(f'{pd:>11d} {ga:>6d} {nd:>8d} {effective_batch(pd, ga, nd):>9d}')

assert effective_batch(8, 4, 1) == effective_batch(2, 16, 1) == 32
assert effective_batch(8, 4, 8) == 256
print('\\n✅ per_device=8,accum=4 与 per_device=2,accum=16 的**有效 batch 相同**（都是 32）。')
print('   前者更快（GPU 利用率高），后者更省显存。这就是显存不够时的标准换法。')
print('   ⚠️  但注意：BatchNorm 类的算子对 per_device 敏感，换了不等价（Transformer 用 LayerNorm，无此问题）。')"""),
    md("""### 坑要显式化：一个可运行的反例

本课每个模块都会这样演示坑。先来一个：**`from_config` 与 `from_pretrained` 搞混**。"""),
    code("""class MiniWeights:
    def __init__(self, vals): self.vals = np.array(vals, dtype=float)

def mini_from_config(config):
    '''只建结构：权重随机初始化。'''
    rng = np.random.default_rng(0)
    return MiniWeights(rng.normal(size=8) * 0.02)

PRETRAINED_STORE = {'bert-base': np.arange(8, dtype=float) + 100}   # 模拟 Hub 上的权重

def mini_from_pretrained(name):
    '''建结构 + **加载权重**。'''
    m = mini_from_config(None)
    m.vals = PRETRAINED_STORE[name].copy()
    return m

a = mini_from_config(None)
b = mini_from_pretrained('bert-base')
print('from_config   权重前三个:', a.vals[:3].round(4), ' <- 随机初始化')
print('from_pretrained 权重前三个:', b.vals[:3].round(4), ' <- 真实预训练权重')
assert not np.allclose(a.vals, b.vals)
assert np.abs(a.vals).max() < 1.0, 'from_config 是小随机数'
assert b.vals[0] == 100.0, 'from_pretrained 加载了真实权重'
print('\\n⚠️  两者都能「跑通」，都不会报错 —— 但 from_config 得到的是个**随机模型**。')
print('   症状：训练能跑、loss 会降，但效果远低于预期，且没有任何报错。')
print('✅ 记住：`from_config` = 只建结构；`from_pretrained` = 结构 + 权重。')"""),
    md("""## 4 · ✏️ 练习：实现 Auto* 的「按名字前缀推断」

真实库在 `config.json` 缺失时，会退而用**模型名字**猜类型（如 `bert-base-uncased` → `bert`）。
实现 `infer_model_type(name, registry)`：把名字小写后，返回 registry 里**最长的**匹配前缀所对应的 key；
无匹配返回 `None`。

（用「最长匹配」是为了让 `gpt2-medium` 匹配 `gpt2` 而不是 `gpt`。）"""),
    code("""def infer_model_type(name, registry):
    # TODO: 小写化；在 registry 的 key 里找所有「是 name 前缀」的，返回最长的那个；无则 None
    raise NotImplementedError"""),
    code("""# —— 练习自测 ——
REG = {'bert': 1, 'gpt': 2, 'gpt2': 3, 't5': 4, 'deberta': 5, 'deberta-v2': 6}
assert infer_model_type('bert-base-uncased', REG) == 'bert'
assert infer_model_type('gpt2-medium', REG) == 'gpt2', '最长匹配：应是 gpt2 而不是 gpt'
assert infer_model_type('GPT2-XL', REG) == 'gpt2', '应大小写不敏感'
assert infer_model_type('deberta-v2-xlarge', REG) == 'deberta-v2', '最长匹配'
assert infer_model_type('deberta-base', REG) == 'deberta'
assert infer_model_type('t5-small', REG) == 't5'
assert infer_model_type('mystery-net', REG) is None
print('✅ 练习通过：这就是「名字猜类型」的全部逻辑 —— 但**优先用 config.json 的 model_type**，')
print('   名字推断只是兜底（名字可以随便改，config 不会）。')"""),
    md("""---
### 📖 参考答案"""),
    code("""def infer_model_type(name, registry):
    n = name.lower()
    hits = [k for k in registry if n.startswith(k)]
    return max(hits, key=len) if hits else None"""),
    md("""## 5 · 🧪 胶囊：本课会算的几笔「参数账」

预告一下后面每个模块会算清的数字。它们都是「文档里有、但组合起来才有意义」的量。"""),
    code("""ledgers = [
    ('模块 03', '有效 batch',
     'per_device × grad_accum × n_devices', effective_batch(4, 8, 2)),
    ('模块 02', '上下文预算',
     'max_length − 特殊token − 生成预留', 512 - 3 - 128),
    ('模块 04', 'LoRA 可训练参数占比',
     '2·r·(d_in+d_out) / (d_in·d_out)  [r=8, 768×768]',
     round(2 * 8 * (768 + 768) / (768 * 768) * 100, 3)),
    ('模块 04', 'LoRA 缩放因子',
     'lora_alpha / r  [alpha=16, r=8]', 16 / 8),
    ('模块 05', '限流下的最大吞吐',
     'min(RPM, TPM / 平均token数)  [RPM=60, TPM=60k, 均500]',
     min(60, 60000 // 500)),
]
print(f"{'模块':<8s} {'量':<22s} {'公式':<48s} {'值':>10s}")
for m, name, formula, val in ledgers:
    print(f'{m:<8s} {name:<22s} {formula:<48s} {str(val):>10s}')

assert effective_batch(4, 8, 2) == 64
assert abs(2 * 8 * 1536 / (768 * 768) * 100 - 0.0417 * 100) < 1.0
print('\\n✅ 这五个数字覆盖了实操中最常被算错的地方。本课会逐个把它们讲清并让你自己算一遍。')"""),
    md("""✅ 检查全部通过即环境就绪、方法论到位。

**本课的契约**：每个机制你都会 ① 用一两百行**迷你复刻**并用 assert 钉死语义，
② 对照**真实 API** 的等价写法与参数位置，③ 算清相关的**参数账**，④ 见到一个可运行的**反例**演示坑。

**接下来五个模块**：01 transformers 核心抽象 → 02 tokenizers 与 datasets →
03 Trainer 与 TrainingArguments → 04 PEFT 与 TRL → 05 Accelerate、Hub 与推理 API。

下一站：**模块 01 · transformers 核心抽象** —— `from_pretrained` 这一行到底做了什么？"""),
]
