# -*- coding: utf-8 -*-
"""C50 模块 02 · tokenizers 与 datasets。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–01；C21 的 tokenizer 训练概念、C43 的数据工程概念（有帮助但不必需）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_tokenizers_datasets.ipynb'),
    ("核心参考", "tokenizers 文档（Encoding / offsets / word_ids）、datasets 文档（Process / Stream / Cache）、Apache Arrow"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("fast", "fast tokenizer：offsets 与 word_ids 才是它的价值", "".join([
        P("很多人以为 <code>use_fast=True</code> 的价值只是「快」（Rust 实现，比 Python 版快 10–100 倍）。速度确实是它的名字来源，但<strong>对正确性而言，更重要的是它返回的两组对齐信息</strong>。"),
        TABLE(["返回值", "是什么", "解决什么问题"], [
            ["<code>input_ids</code>", "token id 序列", "喂给模型"],
            ["<code>attention_mask</code>", "1=真实 token，0=padding", "让模型忽略 pad（漏传就会去注意 pad）"],
            ["<strong><code>offset_mapping</code></strong>", "每个 token 在<strong>原始字符串</strong>中的 <code>(start, end)</code> 字符区间", "把模型的 token 级预测<strong>映射回原文字符位置</strong>——span 抽取、NER 高亮、实体链接全靠它"],
            ["<strong><code>word_ids()</code></strong>", "每个 token 属于第几个「词」（特殊 token 为 <code>None</code>）", "把<strong>词级标注</strong>对齐到<strong>子词级</strong>——token 分类的必需品（C49 模块 03 那个坑）"],
            ["<code>token_type_ids</code>", "句 A / 句 B 标记", "句对任务"],
            ["<code>overflowing_tokens</code>", "超长时被切出去的部分", "滑窗处理长文档（配 <code>return_overflowing_tokens=True</code>）"],
        ]),
        ASCII("""text = "Washington is nice"
                 0123456789...

tokens:      [CLS]   Wash   ##ing  ##ton    is    nice   [SEP]
input_ids:     101   6242    2075   2669   2003   3835    102
offsets:     (0,0)  (0,4)  (4,7)  (7,10) (11,13)(14,18)  (0,0)
                     └──── 三个子词的 offset 拼起来 = 原文 [0,10) = "Washington"
word_ids():   None     0      0      0      1      2     None
                     └──── 三个子词都属于**词 0**

用途 ①（NER）：词级标注 ["B-LOC","O","O"] -> 只给每个词的**第一个**子词打标签，
              其余填 -100  ->  [-100, B-LOC, -100, -100, O, O, -100]
用途 ②（QA）：模型预测 span = token 3..5 -> 用 offsets 换算成原文字符 [7,18)
              -> 直接从原始字符串切出答案，**不用 detokenize**（避免空格/大小写失真）""")
        ,
        DUAL(
            "为什么不能靠 <code>decode()</code> 把答案还原？因为<strong>分词不是无损可逆的</strong>。<code>decode(encode(text))</code> 常常与 <code>text</code> 不同——空格被规范化、大小写被 lowercase 模型改掉、某些 Unicode 被归一化。抽取式 QA 的答案必须<strong>逐字符来自原文</strong>（这是它相对生成式的核心优势，C49 模块 03 说过），所以只能靠 <code>offset_mapping</code> 从原始字符串切。<em>用 decode 拼答案是个常见错误，症状是「答案基本对但标点/空格有细微差异」，然后 EM 分数莫名偏低。</em>",
            "<code>word_ids()</code> 的作用同理不可替代。你有词级标注 <code>[('Washington','B-LOC'), ('is','O'), ('nice','O')]</code>，模型输出是子词级的。要计损失就必须知道「哪些子词属于哪个词」。手工做这个对齐（按空格切、再逐个匹配子词）在有标点、有连字符、有多语言的真实数据上极易出错。<strong><code>word_ids()</code> 是唯一可靠的来源</strong>，而它<em>只有 fast tokenizer 才有</em>——slow tokenizer 调用它会直接抛异常。",
        ),
        CALLOUT("warn", "两个具体的 gotcha：<strong>①<code>offset_mapping</code> 需要显式开启</strong>（<code>return_offsets_mapping=True</code>），而且它<em>只对 fast tokenizer 可用</em>。<strong>②特殊 token 的 offset 是 <code>(0,0)</code></strong>，不是 <code>None</code>——如果你用 <code>offset[0] == 0</code> 判断「是不是序列开头」，会把 <code>[CLS]</code> 和真正的第一个 token 混起来。正确做法是用 <code>sequence_ids()</code>（区分特殊 token / 句 A / 句 B）或 <code>word_ids()</code> 里的 <code>None</code> 来识别特殊 token。"),
    ])),
    ("padding", "padding / truncation：四种组合与算力浪费", "".join([
        P("这两个参数看起来平淡，但组合起来直接决定你浪费多少算力。"),
        TABLE(["<code>padding</code>", "行为", "每 batch 的序列长度", "算力浪费"], [
            ["<code>False</code>（默认）", "不 padding", "各不相同（不能直接组 batch）", "—"],
            ["<code>True</code> / <code>'longest'</code>", "补到<strong>本 batch</strong>最长", "随 batch 变化", "<strong>最省</strong>（动态 padding）"],
            ["<code>'max_length'</code>", "补到 <code>max_length</code>（或模型上限）", "固定", "<strong>可能浪费巨大</strong>"],
            ["<code>'do_not_pad'</code>", "同 <code>False</code>", "—", "—"],
        ]),
        DUAL(
            "为什么 <code>padding='max_length'</code> 可能浪费巨大？因为注意力是 <code>O(L²)</code>。假设你的数据平均长度 60、最长 500，设 <code>max_length=512</code> 全补齐：每条都按 512 算，<strong>而实际有效计算只占 (60/512)² ≈ 1.4%</strong>。改成动态 padding（补到本 batch 最长），如果 batch 内长度接近，浪费就很小。",
            "更进一步的优化是<strong>按长度分组（length grouping）</strong>：把长度接近的样本放进同一个 batch，让每个 batch 的最长值尽量接近其平均值。<code>Trainer</code> 里就是 <code>group_by_length=True</code>（配 <code>length_column_name</code>）。它的代价是<em>破坏了随机性</em>（同 batch 的样本长度相关），对某些任务可能有轻微影响，但对大多数任务是纯赚。notebook 会把三种策略的 padding 浪费率算出来对比，你会看到几倍的差距。",
        ),
        H3("truncation 的三种策略"),
        UL([
            "<strong><code>truncation=True</code>（=<code>'longest_first'</code>）</strong>：句对时优先截长的那句，逐 token 交替截直到达标。<em>默认，通常是对的。</em>",
            "<strong><code>'only_second'</code></strong>：只截第二句。QA 任务用这个——<em>问题不能截，上下文可以</em>。这是个具体且重要的选择。",
            "<strong><code>'only_first'</code></strong>：只截第一句。少见。",
        ]),
        CALLOUT("danger", "<p><strong>截断是静默的</strong>——超长输入被砍掉一半，不会有任何警告，训练照常进行，你只会看到「效果不如预期」。这是数据侧最隐蔽的 bug 之一。防护做法：<em>预处理时统计长度分布与截断率</em>，并把「截断率 &gt; X%」当作告警。notebook 会实现这个统计。另外 <code>return_overflowing_tokens=True</code> 可以把溢出部分作为额外样本返回（滑窗），这是长文档 QA 的标准做法，但要注意它会<strong>改变样本数量</strong>——<code>Dataset.map</code> 里用它必须配 <code>remove_columns</code>，否则新旧列长度不一致会报错。</p>", "截断是静默的"),
    ])),
    ("dataset", "datasets：Arrow、map 与指纹缓存", "".join([
        P("<code>datasets</code> 的三个核心设计决定了它的全部行为特征。"),
        TABLE(["设计", "是什么", "带来什么"], [
            ["<strong>Arrow 后端</strong>", "数据存成列式的 Arrow 文件，<strong>内存映射</strong>访问", "可以用几百 MB 内存处理几百 GB 数据集；多进程共享零拷贝"],
            ["<strong>指纹缓存</strong>", "对 <code>(数据集状态, 函数字节码, 参数)</code> 做哈希，命中则直接读缓存文件", "重跑脚本时 <code>map</code> 秒完成；但也带来「改了函数却没生效」的困惑"],
            ["<strong>惰性/流式</strong>", "<code>IterableDataset</code> 边下边用，不落盘", "TB 级数据集无需下载完；但不支持随机索引与 <code>len()</code>"],
        ]),
        H3("map 的四个关键参数"),
        CODE("""ds = ds.map(
    tokenize_fn,
    batched=True,            # ① 一次传一批（dict of lists）而不是一条 -> 快 10-100 倍
    batch_size=1000,         # ② 每批多少条
    num_proc=8,              # ③ 多进程；⚠️ 与 batched 一起用时注意函数必须可 pickle
    remove_columns=ds.column_names,   # ④ 删掉原始列
)"""),
        DUAL(
            "<strong><code>batched=True</code> 是最重要的一个</strong>。它让你的函数一次收到一批数据（<code>{'text': [...1000 条...]}</code>），于是可以调用 fast tokenizer 的<em>批量接口</em>——Rust 侧并行处理，比逐条调用快一到两个数量级。代价是函数签名变了：<code>batched=False</code> 时 <code>example['text']</code> 是字符串，<code>batched=True</code> 时是<strong>字符串列表</strong>。<em>这个签名切换是新手最常犯的错。</em>",
            "<strong><code>remove_columns</code> 什么时候必需？</strong>当你的函数<em>改变了样本数量</em>（如 <code>return_overflowing_tokens</code> 产生更多行）或者新列与旧列长度不一致时。<code>datasets</code> 会把返回的新列与保留的旧列拼在一起，长度不一致就报错 <code>Column lengths mismatch</code>。<em>规则：只要你的 map 可能改变行数，就必须 <code>remove_columns=ds.column_names</code></em>。另外它还能显著省磁盘——不删原始 <code>text</code> 列，缓存文件会大好几倍。",
        ),
        H3("指纹缓存：省时间也制造困惑"),
        P("<code>map</code> 会算一个指纹：<strong>数据集当前状态的哈希 + 你的函数的字节码/闭包哈希 + 所有参数</strong>。指纹相同就直接读缓存文件，不重新计算。这让「改一行代码重跑脚本」从几分钟变成几秒。"),
        P("但它也带来两类困惑："),
        UL([
            "<strong>改了函数却没生效</strong>：极少见但会发生——如果你的函数依赖外部可变状态（全局变量、文件内容、随机数），指纹没变但行为变了。<em>解法：把依赖显式作为参数传入（<code>fn_kwargs=</code>），或 <code>load_from_cache_file=False</code> 强制重算。</em>",
            "<strong>缓存文件堆积</strong>：每次不同的 map 都生成一个缓存文件，一个大数据集反复处理会吃掉几十 GB 磁盘。<em>解法：用 <code>keep_in_memory=True</code>（小数据集）或定期清理 <code>~/.cache/huggingface/datasets</code>。</em>",
        ]),
        CALLOUT("intuition", "关于指纹缓存有一条实用经验：<strong>调试预处理函数时先在小切片上跑</strong>（<code>ds.select(range(100))</code>），确认正确后再跑全量。这样既快，又避免生成一堆无用的大缓存文件。<em>而且能让你在几秒内迭代，而不是每次等几分钟</em>——这个习惯对数据预处理的开发效率影响很大。"),
    ])),
    ("streaming", "streaming：什么时候用、代价是什么", "".join([
        P("<code>load_dataset(..., streaming=True)</code> 返回 <code>IterableDataset</code>：边下边用，不落盘。对 TB 级数据集（C43 的场景）是唯一可行方案。"),
        TABLE(["能力", "<code>Dataset</code>（内存映射）", "<code>IterableDataset</code>（流式）"], [
            ["随机索引 <code>ds[42]</code>", "✅", "❌ 只能顺序迭代"],
            ["<code>len(ds)</code>", "✅", "❌（有些数据集有元信息，多数没有）"],
            ["<code>shuffle()</code>", "✅ 全局精确打乱", "🔶 <strong>缓冲区近似打乱</strong>（<code>buffer_size</code>）"],
            ["<code>map()</code>", "✅ 提前算好并缓存", "✅ 但是<strong>惰性</strong>的（迭代时才算）"],
            ["磁盘占用", "需要完整下载", "<strong>几乎为零</strong>"],
            ["多 epoch", "✅", "🔶 需要重新迭代（配 <code>set_epoch</code> 换 shuffle 种子）"],
        ]),
        DUAL(
            "<strong>缓冲区打乱</strong>是流式的核心妥协，值得理解清楚。它维护一个大小 <code>N</code> 的缓冲区：先填满，然后每次随机吐一个、再补一个进来。<code>N</code> 越大越接近全局打乱，但内存占用也越大。<em>如果数据集在磁盘上是按某种顺序排列的（比如按来源、按时间），而 <code>buffer_size</code> 远小于一个「块」的大小，那么同一个 batch 里的样本会高度相关</em>——这会显著伤害训练。",
            "解决办法是两级打乱：<strong>①先打乱 shard 顺序</strong>（<code>datasets</code> 的流式 shuffle 会同时做这个），<strong>②再在缓冲区内打乱</strong>。这样即使 <code>buffer_size</code> 只有一万，样本也来自随机的不同 shard，相关性大幅降低。<em>C43 模块 02 有对这个近似质量的完整量化</em>——那门课让你算出「缓冲要多大才够」，本课只讲参数在哪。",
        ),
        CALLOUT("warn", "流式的一个实操坑：<strong>它与 <code>num_proc</code> / <code>DataLoader(num_workers=N)</code> 的交互</strong>。多 worker 各自迭代同一个流会导致<em>重复数据</em>，除非数据集支持按 shard 切分给不同 worker（<code>datasets</code> 会尽力处理，但对 shard 数少于 worker 数的情况会警告并降级）。<em>规则：流式训练时确保 shard 数 ≥ worker 数 × 进程数</em>，否则要么重复要么有 worker 空转。"),
    ])),
    ("collator", "DataCollator：动态 padding 与标签构造", "".join([
        P("<code>map</code> 之后每条样本还是变长的（如果你用了动态 padding）。<strong>把它们组成一个矩形张量、并构造 labels，是 collator 的职责</strong>。它在 <code>DataLoader</code> 里每个 batch 被调用一次。"),
        TABLE(["Collator", "做什么", "用在哪"], [
            ["<code>DataCollatorWithPadding</code>", "补齐到本 batch 最长 + 生成 <code>attention_mask</code>", "分类任务（labels 已是标量）"],
            ["<code>DataCollatorForTokenClassification</code>", "同上 + 把 labels 也补齐（用 <code>-100</code>）", "NER / 序列标注"],
            ["<code>DataCollatorForLanguageModeling</code>", "<strong>现场做 MLM 掩码</strong>（<code>mlm_probability=0.15</code>，就是 C49 模块 01 的 80/10/10）", "MLM 预训练"],
            ["<code>DataCollatorForLanguageModeling(mlm=False)</code>", "CLM：<code>labels = input_ids.clone()</code>，pad 位置置 <code>-100</code>", "CLM 预训练 / SFT"],
            ["<code>DataCollatorForSeq2Seq</code>", "补齐 input 与 labels + 生成 <code>decoder_input_ids</code>", "翻译 / 摘要"],
        ]),
        DUAL(
            "<strong>「动态掩码」就是在这里发生的</strong>。C49 模块 02 讲的 RoBERTa 相对 BERT 的一大改进——每个 epoch 重新采样掩码位置——在 HF 生态里是<em>默认行为</em>，因为 collator 在每个 batch 被调用时都会重新掩一次。你不需要做任何事就得到了动态掩码。<em>反过来，如果你想要静态掩码（复现 BERT 原始设置），得在 <code>map</code> 阶段就掩好并禁用 collator 的掩码。</em>",
            "collator 里最容易出错的是 <strong><code>-100</code> 的处理</strong>。PyTorch 的 <code>CrossEntropyLoss(ignore_index=-100)</code> 是全生态的约定：labels 里为 <code>-100</code> 的位置不计损失。padding 位置、未被掩的位置、SFT 里的 prompt 部分——都要填 <code>-100</code>。<strong>漏填的后果是模型在学「预测 pad token」或「背诵 prompt」</strong>，loss 看起来正常（甚至更低，因为 pad 很容易预测）但效果差。<em>这是 SFT 里最经典的一个 bug</em>，模块 04 会再遇到它。",
        ),
        CALLOUT("intuition", "一个能救命的调试习惯：<strong>训练开始前，取一个 batch 打印出来看</strong>。检查四件事——<code>input_ids</code> 解码回文本是否通顺、<code>attention_mask</code> 的 0 是否只在该在的位置、<code>labels</code> 里 <code>-100</code> 的比例是否符合预期、以及 <code>labels</code> 与 <code>input_ids</code> 的对齐关系是否正确。<em>这四个检查能在三十秒内发现 80% 的数据侧 bug</em>，而不用等训练跑完看效果。notebook 会把这个检查封装成一个函数。"),
    ])),
    ("ledger", "算一笔账：padding 浪费与截断率", "".join([
        MATH("\\text{padding 浪费率} = 1 - \\frac{\\sum_i L_i}{B \\cdot \\max_i L_i} \\quad(\\text{按 token}), \\qquad 1 - \\frac{\\sum_i L_i^2}{B\\cdot(\\max_i L_i)^2}\\quad(\\text{按注意力})"),
        P("两个公式的区别很重要：<strong>线性部分（FFN、embedding）按第一个算，注意力按第二个算</strong>。因为注意力是平方的，长度不齐时它的浪费被放大。"),
        TABLE(["策略", "batch 内长度", "token 浪费", "注意力浪费"], [
            ["<code>padding='max_length'</code>（512）", "[60, 80, 55, 500] → 全补 512", "≈ 66%", "<strong>≈ 75%</strong>"],
            ["<code>padding=True</code>（动态）", "[60, 80, 55, 500] → 补到 500", "≈ 65%", "≈ 74%"],
            ["<code>padding=True</code> + 按长度分组", "[55, 60, 80, …] 与 [500, …] 分开", "≈ 10%", "<strong>≈ 20%</strong>"],
        ]),
        P("读这张表：<strong>动态 padding 在长度差异大的 batch 里帮助有限，真正的杠杆是「按长度分组」</strong>。这也解释了为什么 <code>group_by_length=True</code> 在长度分布长尾的数据上能带来 2–4 倍的吞吐提升。"),
        P("第二笔账是<strong>截断率</strong>，它是数据质量的隐形杀手："),
        MATH("\\text{截断率} = \\frac{|\\{i : L_i > L_{max}\\}|}{N}, \\qquad \\text{信息损失率} = \\frac{\\sum_i \\max(0, L_i - L_{max})}{\\sum_i L_i}"),
        P("这两个数要分开看：<strong>截断率高但信息损失率低</strong>（很多样本只超出一点）通常可以接受；<strong>截断率低但信息损失率高</strong>（少数极长样本被砍掉大半）意味着你在丢弃某个特定子群体的数据——<em>这可能是系统性偏差，比随机丢失更危险</em>。"),
        CALLOUT("intuition", "把本模块浓缩成一句话：<strong>数据层的坑几乎全是「形状与对齐」的坑——padding 补在哪边、labels 里哪些位置填 -100、子词怎么对齐到词、offset 怎么映射回原文字符</strong>。它们全都不报错，只让效果变差。<em>所以本模块最该带走的是那个「打印一个 batch 检查四件事」的习惯</em>，以及「统计截断率并告警」的纪律。"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>序列打包（packing）</strong>：把多条短样本拼进一个定长序列以消除 padding 浪费，用 attention mask 或 <code>position_ids</code> 防止跨样本注意（cross-contamination）。<code>trl</code> 的 <code>SFTTrainer(packing=True)</code> 与 FlashAttention 的变长接口都支持，但「打包是否损害效果」在不同任务上结论不一，尤其对短样本任务。",
            "<strong>tokenizer 的多语言公平性</strong>：同样一句话，不同语言的 token 数差异可达数倍（中文、泰语、部分非洲语言尤其吃亏）。这直接转化为<em>相同信息量下更高的 API 费用与更小的有效上下文</em>。如何在有限词表下做到跨语言公平，是活跃的研究与工程问题。",
            "<strong>字节级与无分词模型</strong>：完全去掉 tokenizer（ByT5、MegaByte、以及近年的动态分块方案），从根上消除词表偏差与 OOV。代价是序列变长数倍，需要架构层面的补偿。目前尚未在通用场景胜出，但在多语言与代码上有吸引力。",
            "<strong>数据集格式的收敛</strong>：Arrow/Parquet 正在成为事实标准，但流式训练下的确定性打乱、断点续训的精确恢复（跑到第几个样本）、以及多 worker 的无重复切分，各家实现仍有差异。Mosaic StreamingDataset 与 <code>datasets</code> 的流式在这些语义上不完全一致。",
            "<strong>预处理的可复现性</strong>：指纹缓存让重跑变快，但也让「预处理版本」变成一个隐式状态。把 tokenizer 版本、预处理函数、参数一起写进数据集卡片与实验记录，是 C40/C37 强调但生态尚未强制的实践。",
        ]),
        CALLOUT("paper", "必读：tokenizers 文档的 <em>The tokenization pipeline</em> 与 <em>Encoding</em>（offsets/word_ids/sequence_ids 的准确语义）；datasets 文档的 <em>Process</em>（map 的全部参数）、<em>Stream</em>（IterableDataset 的限制）与 <em>Cache management</em>（指纹机制）；transformers 的 <em>Data Collator</em> API 文档（尤其 <code>DataCollatorForLanguageModeling</code> 的源码，80/10/10 就在那三行）。原理侧：C21（tokenizer 训练与数据配比）、C43（PB 级流式与吞吐）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · tokenizers 与 datasets（迷你复刻 offsets / word_ids / map / streaming / collator）

目标：把 **fast tokenizer 的 offset 与 word_ids → padding/truncation 的四种组合 → Dataset.map 的批处理与指纹缓存 →
IterableDataset 与缓冲打乱 → DataCollator 的 -100 构造** 从零写一遍。

路线：迷你 fast tokenizer（带 offsets）→ 子词到词的对齐 → span 用 offsets 映射回原文 →
padding 浪费与按长度分组 → 截断率统计 → map 的批处理与指纹 → 缓冲打乱 →
collator 与 -100 → 「打印一个 batch」检查器 → ✏️ 练习 → 📖 答案 → 🧪 浪费率胶囊。

> 心智模型：**数据层的坑几乎全是「形状与对齐」的坑**——全都不报错，只让效果变差。"""),
    md("""## 1 · 迷你 fast tokenizer：offsets 与 word_ids

`offset_mapping` 让你把 token 级预测映射回**原始字符串的字符位置**；
`word_ids()` 让你把**词级标注**对齐到子词级。这两个是 fast tokenizer 真正不可替代的地方。"""),
    code("""import numpy as np, math, re, json, hashlib, random
rng = np.random.default_rng(0)

CLS, SEP, UNK, PAD = '[CLS]', '[SEP]', '[UNK]', '[PAD]'
# 一个迷你 WordPiece 风格词表（含 ## 续接片）
VOCAB = [PAD, CLS, SEP, UNK, 'wash', '##ing', '##ton', 'is', 'nice', 'new', 'york',
         'city', 'the', 'capital', 'of', 'usa', '.', 'very', 'good']
STOI = {w: i for i, w in enumerate(VOCAB)}

class MiniFastTokenizer:
    '''迷你 fast tokenizer：返回 input_ids / attention_mask / offset_mapping / word_ids。'''
    def __init__(self, vocab):
        self.stoi = {w: i for i, w in enumerate(vocab)}
        self.itos = {i: w for w, i in self.stoi.items()}
        # 按长度降序，贪心最长匹配（WordPiece 的经典做法）
        self.pieces = sorted([w for w in vocab if not w.startswith('[')],
                             key=len, reverse=True)

    def _split_words(self, text):
        '''返回 [(词, 起始字符, 结束字符)]，标点独立成词。'''
        out = []
        for m in re.finditer(r"\\w+|[^\\w\\s]", text):
            out.append((m.group(0).lower(), m.start(), m.end()))
        return out

    def _wordpiece(self, word, w_start):
        '''把一个词切成子词，返回 [(piece, start_char, end_char)]。'''
        pieces, i = [], 0
        while i < len(word):
            matched = None
            for L in range(len(word) - i, 0, -1):
                cand = word[i:i + L]
                key = cand if i == 0 else '##' + cand
                if key in self.stoi:
                    matched = (key, w_start + i, w_start + i + L); i += L; break
            if matched is None:
                return [(UNK, w_start, w_start + len(word))]
            pieces.append(matched)
        return pieces

    def __call__(self, text, max_length=None, truncation=False,
                 return_offsets_mapping=True, add_special_tokens=True):
        words = self._split_words(text)
        ids, offs, wids = [], [], []
        if add_special_tokens:
            ids.append(self.stoi[CLS]); offs.append((0, 0)); wids.append(None)
        for wi, (w, s, e) in enumerate(words):
            for piece, ps, pe in self._wordpiece(w, s):
                ids.append(self.stoi.get(piece, self.stoi[UNK]))
                offs.append((ps, pe)); wids.append(wi)
        if add_special_tokens:
            ids.append(self.stoi[SEP]); offs.append((0, 0)); wids.append(None)
        if truncation and max_length and len(ids) > max_length:
            keep = max_length - (1 if add_special_tokens else 0)
            ids, offs, wids = ids[:keep], offs[:keep], wids[:keep]
            if add_special_tokens:
                ids.append(self.stoi[SEP]); offs.append((0, 0)); wids.append(None)
        enc = {'input_ids': ids, 'attention_mask': [1] * len(ids)}
        if return_offsets_mapping:
            enc['offset_mapping'] = offs
        enc['_word_ids'] = wids
        return enc

    def tokens(self, ids): return [self.itos[i] for i in ids]

tok = MiniFastTokenizer(VOCAB)
TEXT = 'Washington is nice'
enc = tok(TEXT)
print(f'{"token":<8s} {"id":>4s} {"offset":>10s} {"word_id":>8s} {"原文切片":>10s}')
for t, i, o, w in zip(tok.tokens(enc['input_ids']), enc['input_ids'],
                      enc['offset_mapping'], enc['_word_ids']):
    slice_ = TEXT[o[0]:o[1]] if o != (0, 0) else ''
    print(f'{t:<8s} {i:>4d} {str(o):>10s} {str(w):>8s} {slice_!r:>12s}')

assert tok.tokens(enc['input_ids'])[1:4] == ['wash', '##ing', '##ton']
assert enc['_word_ids'][1:4] == [0, 0, 0], '三个子词都属于词 0'
assert enc['_word_ids'][0] is None and enc['_word_ids'][-1] is None, '特殊 token 的 word_id 是 None'
# 关键：把词 0 的三个子词的 offset 拼起来 = 原文的完整词
w0 = [o for o, w in zip(enc['offset_mapping'], enc['_word_ids']) if w == 0]
assert TEXT[w0[0][0]:w0[-1][1]] == 'Washington', '子词 offset 拼起来应还原原词'
print(f"\\n✅ 词 0 的 offset 区间 [{w0[0][0]}, {w0[-1][1]}) -> {TEXT[w0[0][0]:w0[-1][1]]!r}")
print('   注意特殊 token 的 offset 是 (0,0) 而**不是 None** —— 用 word_ids 的 None 来识别它们。')"""),
    md("""### 用途 ①：词级标注 → 子词级 labels（C49 模块 03 那个坑）"""),
    code("""LABELS = ['O', 'B-LOC', 'I-LOC', 'B-PER', 'I-PER']
L2I = {l: i for i, l in enumerate(LABELS)}

def align_word_labels(word_ids, word_labels, label_all_subwords=False):
    '''每个词的**第一个**子词取标签，其余填 -100（除非 label_all_subwords）。'''
    out, prev = [], None
    for wid in word_ids:
        if wid is None:
            out.append(-100)
        elif wid != prev:
            out.append(word_labels[wid])
        else:
            if label_all_subwords:
                lab = LABELS[word_labels[wid]]
                out.append(L2I['I-' + lab[2:]] if lab.startswith('B-') else word_labels[wid])
            else:
                out.append(-100)
        prev = wid
    return out

word_labels = [L2I['B-LOC'], L2I['O'], L2I['O']]     # Washington / is / nice
labs = align_word_labels(enc['_word_ids'], word_labels)
print('word_ids:', enc['_word_ids'])
print('labels  :', labs, ' (-100 = 不计损失)')
assert labs == [-100, L2I['B-LOC'], -100, -100, L2I['O'], L2I['O'], -100]
n_signal = sum(1 for x in labs if x != -100)
assert n_signal == len(word_labels), '每个词只贡献一个训练信号'
print(f'✅ {len(enc["input_ids"])} 个 token 里只有 {n_signal} 个产生损失（= 词数）')

# 反面：不做对齐，直接把词级标签按位置铺开
naive = word_labels + [0] * (len(enc['input_ids']) - len(word_labels))
print(f'\\n❌ 不做对齐: {naive}')
print('   -> 模型会学到「把 Washington 的第 2、3 个子词标成 O」，实体级 F1 莫名很低')
assert naive != labs
print('✅ 这就是 word_ids() 不可替代的原因 —— 手工按空格切在真实数据上极易出错')"""),
    md("""### 用途 ②：span 预测 → 用 offsets 映射回原文字符

**不能用 decode 拼答案**——分词不是无损可逆的（空格规范化、lowercase、Unicode 归一化）。"""),
    code("""TEXT2 = 'New York City is the capital of USA.'
enc2 = tok(TEXT2)
toks2 = tok.tokens(enc2['input_ids'])
print('tokens:', toks2)

# 假设模型预测 span = token 下标 1..3（"new york city"）
start_tok, end_tok = 1, 3
cs = enc2['offset_mapping'][start_tok][0]
ce = enc2['offset_mapping'][end_tok][1]
answer_from_offsets = TEXT2[cs:ce]
answer_from_decode = ' '.join(toks2[start_tok:end_tok + 1])
print(f'\\n用 offsets 从原文切  : {answer_from_offsets!r}   ← 逐字符来自原文 ✅')
print(f'用 tokens 拼接      : {answer_from_decode!r}   ← 大小写丢了 ❌')
assert answer_from_offsets == 'New York City', '大小写、空格都保持原样'
assert answer_from_decode != answer_from_offsets
print('\\n⚠️  症状：「答案基本对但标点/空格/大小写有细微差异」-> EM 分数莫名偏低。')
print('✅ 抽取式 QA 的答案必须用 offset_mapping 从**原始字符串**切。')

def span_to_text(text, offsets, i, j):
    return text[offsets[i][0]:offsets[j][1]]
for i, j in [(1, 1), (1, 2), (5, 5), (5, 7)]:
    print(f'  token[{i}..{j}] -> {span_to_text(TEXT2, enc2["offset_mapping"], i, j)!r}')
assert span_to_text(TEXT2, enc2['offset_mapping'], 5, 5) in TEXT2"""),
    md("""## 2 · padding / truncation：算力浪费与静默截断

$$\\text{token 浪费} = 1 - \\frac{\\sum L_i}{B\\max L_i},\\qquad
\\text{注意力浪费} = 1 - \\frac{\\sum L_i^2}{B(\\max L_i)^2}$$

**注意力是平方的，所以长度不齐时它的浪费被放大。**"""),
    code("""def waste_rates(lengths, pad_to=None):
    B = len(lengths); target = pad_to or max(lengths)
    tok_used = sum(lengths); tok_total = B * target
    att_used = sum(l * l for l in lengths); att_total = B * target * target
    return 1 - tok_used / tok_total, 1 - att_used / att_total

batch = [60, 80, 55, 500]
print(f"{'策略':<34s} {'补到':>6s} {'token浪费':>10s} {'注意力浪费':>11s}")
for label, pad_to in [("padding='max_length' (512)", 512), ("padding=True (动态)", None)]:
    tw, aw = waste_rates(batch, pad_to)
    print(f'{label:<34s} {pad_to or max(batch):>6d} {tw:>10.1%} {aw:>11.1%}')

# 按长度分组：把长度接近的放一批
all_lens = [60, 80, 55, 500, 62, 75, 58, 490]
def grouped_waste(lengths, bs=4):
    s = sorted(lengths); tws, aws = [], []
    for i in range(0, len(s), bs):
        g = s[i:i + bs]
        tw, aw = waste_rates(g)
        tws.append(tw); aws.append(aw)
    return float(np.mean(tws)), float(np.mean(aws))

tw_dyn, aw_dyn = waste_rates(all_lens)
tw_grp, aw_grp = grouped_waste(all_lens)
print(f'\\n8 条混合长度: 动态 padding    token浪费 {tw_dyn:.1%} / 注意力浪费 {aw_dyn:.1%}')
print(f'              按长度分组     token浪费 {tw_grp:.1%} / 注意力浪费 {aw_grp:.1%}')
assert aw_grp < aw_dyn / 2, '按长度分组应把注意力浪费减半以上'
tw512, aw512 = waste_rates(batch, 512)
assert aw512 > 0.70, "padding='max_length' 在这个 batch 上浪费 70%+ 的注意力计算"
print(f'\\n✅ 真正的杠杆是**按长度分组**（Trainer 的 group_by_length=True），')
print(f'   而不只是动态 padding。这里注意力浪费从 {aw_dyn:.0%} 降到 {aw_grp:.0%}。')"""),
    code("""def truncation_stats(lengths, max_length):
    '''截断率与信息损失率必须**分开看**。'''
    n_trunc = sum(1 for l in lengths if l > max_length)
    lost = sum(max(0, l - max_length) for l in lengths)
    return {'截断率': n_trunc / len(lengths),
            '信息损失率': lost / sum(lengths),
            'p50': int(np.percentile(lengths, 50)),
            'p95': int(np.percentile(lengths, 95)),
            'p99': int(np.percentile(lengths, 99)),
            'max': max(lengths)}

r = np.random.default_rng(5)
# 场景 A：多数样本略超（截断率高、损失率低）
lens_a = list(r.integers(120, 160, size=1000))
# 场景 B：少数极长样本（截断率低、损失率高）
lens_b = list(r.integers(30, 100, size=950)) + list(r.integers(2000, 4000, size=50))
MAXLEN = 128
for name, lens in [('A: 多数略超', lens_a), ('B: 少数极长', lens_b)]:
    s = truncation_stats(lens, MAXLEN)
    print(f'{name}: 截断率 {s["截断率"]:>6.1%} | 信息损失率 {s["信息损失率"]:>6.1%} | '
          f'p50={s["p50"]} p95={s["p95"]} p99={s["p99"]} max={s["max"]}')

sa, sb = truncation_stats(lens_a, MAXLEN), truncation_stats(lens_b, MAXLEN)
assert sa['截断率'] > sb['截断率'], 'A 的截断率更高'
assert sb['信息损失率'] > sa['信息损失率'], '但 B 的信息损失率更高'
print('\\n⚠️  两个数要分开看：')
print('   A（截断率高、损失率低）通常可接受 —— 每条只丢一点。')
print('   B（截断率低、损失率高）意味着你在**系统性丢弃某个子群体** —— 比随机丢失更危险。')
print('✅ 建议：预处理时统计这两个数，把「信息损失率 > 5%」当作告警。')"""),
    md("""## 3 · Dataset.map：批处理、指纹缓存与 remove_columns"""),
    code("""class MiniDataset:
    '''迷你 Dataset：列式存储 + map 的批处理语义 + 指纹缓存。'''
    def __init__(self, columns, _cache=None):
        self.columns = {k: list(v) for k, v in columns.items()}
        self._cache = {} if _cache is None else _cache
        self.map_calls = 0                      # 统计真正执行的次数（用于验证缓存）
    @property
    def column_names(self): return list(self.columns)
    def __len__(self): return len(next(iter(self.columns.values())))
    def __getitem__(self, i):
        if isinstance(i, int): return {k: v[i] for k, v in self.columns.items()}
        return MiniDataset({k: v[i] for k, v in self.columns.items()}, self._cache)
    def select(self, idxs):
        return MiniDataset({k: [v[i] for i in idxs] for k, v in self.columns.items()}, self._cache)

    def _fingerprint(self, fn, batched, batch_size, remove_columns, fn_kwargs):
        payload = json.dumps({
            'data': hashlib.sha1(json.dumps(self.columns, sort_keys=True,
                                            ensure_ascii=False).encode()).hexdigest(),
            # 函数字节码 + 常量表 —— 改函数体或改里面的常量，指纹都会变
            'fn': fn.__code__.co_code.hex() + repr(fn.__code__.co_consts),
            'batched': batched, 'bs': batch_size,
            'rm': sorted(remove_columns or []), 'kw': sorted((fn_kwargs or {}).items()),
        }, sort_keys=True)
        return hashlib.sha1(payload.encode()).hexdigest()[:12]

    def map(self, fn, batched=False, batch_size=1000, remove_columns=None,
            fn_kwargs=None, load_from_cache_file=True):
        fp = self._fingerprint(fn, batched, batch_size, remove_columns, fn_kwargs)
        if load_from_cache_file and fp in self._cache:
            return MiniDataset(self._cache[fp], self._cache)     # 缓存命中：不执行 fn
        self.map_calls += 1
        kw = fn_kwargs or {}
        keep = {k: v for k, v in self.columns.items() if k not in (remove_columns or [])}
        new = {}
        if batched:
            for i in range(0, len(self), batch_size):
                batch = {k: v[i:i + batch_size] for k, v in self.columns.items()}
                out = fn(batch, **kw)            # ← 收到的是 dict of **lists**
                for k, v in out.items(): new.setdefault(k, []).extend(v)
        else:
            for i in range(len(self)):
                out = fn(self[i], **kw)          # ← 收到的是 dict of **scalars**
                for k, v in out.items(): new.setdefault(k, []).append(v)
        merged = dict(keep); merged.update(new)
        lens = {k: len(v) for k, v in merged.items()}
        if len(set(lens.values())) > 1:
            raise ValueError(f'Column lengths mismatch: {lens} '
                             f'-> 你的 map 改变了行数，必须传 remove_columns=ds.column_names')
        self._cache[fp] = merged
        return MiniDataset(merged, self._cache)

TEXTS = ['Washington is nice', 'New York City is the capital of USA .',
         'the city is very good', 'Washington .']
ds = MiniDataset({'text': TEXTS, 'label': [1, 0, 1, 0]})
print(f'原始数据集: {len(ds)} 行, 列 = {ds.column_names}')
print('第 0 行:', ds[0])"""),
    code("""# batched=False vs True：**函数签名不同**，这是最常犯的错
def tok_single(example):
    e = tok(example['text'], max_length=12, truncation=True)
    return {'input_ids': e['input_ids'], 'n_tok': len(e['input_ids'])}

def tok_batched(batch):
    ids = [tok(t, max_length=12, truncation=True)['input_ids'] for t in batch['text']]
    return {'input_ids': ids, 'n_tok': [len(x) for x in ids]}

d1 = ds.map(tok_single, batched=False)
d2 = ds.map(tok_batched, batched=True, batch_size=2)
assert d1.columns['input_ids'] == d2.columns['input_ids'], '两种写法结果必须一致'
print(f'batched=False 与 batched=True 结果一致 ✅  n_tok = {d1.columns["n_tok"]}')

# 反例：把 batched=True 的函数当 batched=False 用
try:
    ds.map(tok_batched, batched=False)
    print('⚠️ 没报错，但结果是错的（tok 收到的是字符串而非列表）')
except Exception as e:
    print(f'✅ 签名不匹配报错: {type(e).__name__}')
print('\\n记住：batched=False 时 example["text"] 是**字符串**；batched=True 时是**字符串列表**。')"""),
    code("""# 指纹缓存：同样的 (数据, 函数, 参数) -> 不重新执行
ds2 = MiniDataset({'text': TEXTS, 'label': [1, 0, 1, 0]})
before = ds2.map_calls
_ = ds2.map(tok_batched, batched=True)
after_first = ds2.map_calls
_ = ds2.map(tok_batched, batched=True)          # 第二次：应命中缓存
after_second = ds2.map_calls
print(f'实际执行次数: 首次 {after_first - before} | 再调一次 {after_second - after_first}')
assert after_first - before == 1 and after_second - after_first == 0, '第二次应命中缓存'
print('✅ 指纹命中 -> 不执行函数（真实库里是直接读缓存的 arrow 文件）')

# 改了函数体 -> 指纹变 -> 重新执行
def tok_batched_v2(batch):
    ids = [tok(t, max_length=8, truncation=True)['input_ids'] for t in batch['text']]
    return {'input_ids': ids, 'n_tok': [len(x) for x in ids]}
_ = ds2.map(tok_batched_v2, batched=True)
assert ds2.map_calls == after_second + 1, '改了函数体应重新执行'
print('✅ 改函数体 -> 字节码变 -> 指纹变 -> 重新计算')

# load_from_cache_file=False 强制重算（依赖外部可变状态时需要）
n = ds2.map_calls
_ = ds2.map(tok_batched, batched=True, load_from_cache_file=False)
assert ds2.map_calls == n + 1
print('✅ load_from_cache_file=False 强制重算（函数依赖全局变量/文件/随机数时用它）')"""),
    code("""# remove_columns：当 map **改变行数**时必需
def sliding_window(batch, window=6, stride=3):
    '''长文本切成多个重叠窗口 —— 行数会变多！'''
    out_ids, out_src = [], []
    for src_i, t in enumerate(batch['text']):
        ids = tok(t, add_special_tokens=False)['input_ids']
        for s in range(0, max(1, len(ids) - window + 1), stride):
            out_ids.append(ids[s:s + window]); out_src.append(src_i)
    return {'input_ids': out_ids, 'src': out_src}

try:
    ds.map(sliding_window, batched=True)
    raise RuntimeError('不该到这')
except ValueError as e:
    print(f'❌ 不删旧列: {str(e)[:110]}…')

d3 = ds.map(sliding_window, batched=True, remove_columns=ds.column_names)
print(f'\\n✅ 删掉旧列后: {len(ds)} 行 -> {len(d3)} 行（滑窗产生更多样本）')
assert len(d3) > len(ds)
assert d3.column_names == ['input_ids', 'src']
print('   规则：**只要你的 map 可能改变行数，就必须 remove_columns=ds.column_names**')"""),
    md("""## 4 · IterableDataset 与缓冲区打乱

流式只能顺序迭代、没有 `len()`、`shuffle` 只能靠**缓冲区近似**。
缓冲太小 + 数据在磁盘上有序 = 同 batch 样本高度相关，显著伤害训练。"""),
    code("""class MiniIterableDataset:
    def __init__(self, gen_fn): self.gen_fn = gen_fn
    def __iter__(self): return self.gen_fn()
    def map(self, fn):
        outer = self.gen_fn
        return MiniIterableDataset(lambda: (fn(x) for x in outer()))    # 惰性
    def shuffle(self, buffer_size, seed=0):
        outer = self.gen_fn
        def gen():
            r = random.Random(seed); buf = []
            for x in outer():
                buf.append(x)
                if len(buf) >= buffer_size:
                    j = r.randrange(len(buf)); yield buf.pop(j)
            r.shuffle(buf)
            yield from buf
        return MiniIterableDataset(gen)
    def take(self, n):
        outer = self.gen_fn
        def gen():
            for i, x in enumerate(outer()):
                if i >= n: return
                yield x
        return MiniIterableDataset(gen)

# 磁盘上按「来源」有序排列：前 500 条来自源 A，后 500 条来自源 B
def sorted_stream():
    for i in range(1000):
        yield {'src': 'A' if i < 500 else 'B', 'i': i}

stream = MiniIterableDataset(sorted_stream)
try:
    len(stream); raise RuntimeError('不该到这')
except TypeError:
    print('✅ IterableDataset 没有 len() —— 只能顺序迭代')

def batch_purity(ds, batch=16, n_batches=20):
    '''每个 batch 里「同一来源」的占比。1.0 = 完全同源（最差）。'''
    it, purities, cur = iter(ds), [], []
    for x in it:
        cur.append(x['src'])
        if len(cur) == batch:
            purities.append(max(cur.count('A'), cur.count('B')) / batch)
            cur = []
            if len(purities) >= n_batches: break
    return float(np.mean(purities))

print(f"\\n{'buffer_size':>12s} {'batch 内同源占比':>16s}")
for bs in [1, 16, 128, 1024]:
    pur = batch_purity(stream.shuffle(buffer_size=bs, seed=1))
    print(f'{bs:>12d} {pur:>16.2f}')

p_small = batch_purity(stream.shuffle(buffer_size=1, seed=1))
p_large = batch_purity(stream.shuffle(buffer_size=1024, seed=1))
assert p_small > 0.95, '缓冲=1 等于不打乱 -> 每个 batch 完全同源'
assert p_large < p_small, '缓冲越大越接近全局打乱'
print(f'\\n✅ 缓冲 1 时同源占比 {p_small:.2f}（完全没打乱）；缓冲 1024 时 {p_large:.2f}。')
print('   若数据在磁盘上按来源/时间有序，小缓冲会让同 batch 样本高度相关 —— 显著伤害训练。')
print('   真实库的流式 shuffle 会**同时打乱 shard 顺序**，这是两级打乱的第一级。')
print('   「缓冲要多大才够」的完整量化见 C43 模块 02。')"""),
    md("""## 5 · DataCollator：-100 的构造与「打印一个 batch」检查器

`-100` 是全生态约定（`CrossEntropyLoss(ignore_index=-100)`）：
padding、未被掩的位置、SFT 里的 prompt 部分——**都要填 -100**。漏填会让模型学错东西。"""),
    code("""PAD_ID = STOI[PAD]

def collate_with_padding(features, pad_id=PAD_ID):
    '''对应 DataCollatorWithPadding：动态补齐 + attention_mask。'''
    L = max(len(f['input_ids']) for f in features)
    return {
        'input_ids': np.array([f['input_ids'] + [pad_id] * (L - len(f['input_ids'])) for f in features]),
        'attention_mask': np.array([[1]*len(f['input_ids']) + [0]*(L-len(f['input_ids'])) for f in features]),
        'labels': np.array([f['label'] for f in features]),
    }

def collate_token_classification(features, pad_id=PAD_ID):
    '''对应 DataCollatorForTokenClassification：labels 也要补齐，用 **-100**。'''
    L = max(len(f['input_ids']) for f in features)
    return {
        'input_ids': np.array([f['input_ids'] + [pad_id]*(L-len(f['input_ids'])) for f in features]),
        'attention_mask': np.array([[1]*len(f['input_ids']) + [0]*(L-len(f['input_ids'])) for f in features]),
        'labels': np.array([f['labels'] + [-100]*(L-len(f['labels'])) for f in features]),
    }

def collate_clm(features, pad_id=PAD_ID):
    '''对应 DataCollatorForLanguageModeling(mlm=False)：labels=input_ids，pad 位置置 -100。'''
    L = max(len(f['input_ids']) for f in features)
    ids = np.array([f['input_ids'] + [pad_id]*(L-len(f['input_ids'])) for f in features])
    labels = ids.copy(); labels[ids == pad_id] = -100
    return {'input_ids': ids, 'attention_mask': (ids != pad_id).astype(int), 'labels': labels}

feats = [{'input_ids': tok(t)['input_ids'], 'label': i % 2} for i, t in enumerate(TEXTS)]
b = collate_with_padding(feats)
print('分类 batch 形状:', {k: v.shape for k, v in b.items()})
assert b['input_ids'].shape[0] == len(feats)
assert (b['attention_mask'].sum(1) == [len(f['input_ids']) for f in feats]).all()

feats_tc = [{'input_ids': tok(t)['input_ids'],
             'labels': align_word_labels(tok(t)['_word_ids'],
                                         [L2I['O']] * 20)} for t in TEXTS]
btc = collate_token_classification(feats_tc)
assert (btc['labels'] == -100).sum() > 0, 'padding 与非首子词位置必须是 -100'
bclm = collate_clm(feats)
assert (bclm['labels'][bclm['input_ids'] == PAD_ID] == -100).all(), 'CLM: pad 位置必须 -100'
print('✅ 三种 collator 的 -100 处理正确')

# 反例：忘记把 pad 位置置 -100
bad_labels = np.array([f['input_ids'] + [PAD_ID]*(bclm['input_ids'].shape[1]-len(f['input_ids']))
                       for f in feats])
n_pad = int((bad_labels == PAD_ID).sum())
print(f'\\n❌ 忘记置 -100: 有 {n_pad} 个位置在教模型「预测 [PAD]」')
print('   pad 极易预测 -> loss 看起来更低（甚至下降更快）-> 但效果变差。')
assert n_pad > 0"""),
    code("""def inspect_batch(batch, tokenizer, max_rows=2):
    '''训练开始前必做的四项检查。三十秒发现 80% 的数据侧 bug。'''
    print('=' * 68)
    print('① 形状:', {k: tuple(v.shape) for k, v in batch.items()})
    ids, am = batch['input_ids'], batch.get('attention_mask')
    labels = batch.get('labels')
    for r in range(min(max_rows, ids.shape[0])):
        n_real = int(am[r].sum()) if am is not None else ids.shape[1]
        print(f'\\n② 第 {r} 行解码（前 {n_real} 个真实 token）:')
        print('   ', ' '.join(tokenizer.tokens(list(ids[r][:n_real]))))
        if am is not None:
            zeros = np.where(am[r] == 0)[0]
            ok = len(zeros) == 0 or (zeros[0] == n_real and (np.diff(zeros) == 1).all())
            print(f'③ attention_mask 的 0 是否只在尾部连续: {"✅" if ok else "❌"}')
        if labels is not None and labels.ndim == 2:
            frac = float((labels[r] == -100).mean())
            print(f'④ labels 中 -100 占比: {frac:.1%}')
    print('=' * 68)
    if labels is not None and labels.ndim == 2:
        overall = float((labels == -100).mean())
        assert overall < 0.95, f'-100 占比 {overall:.1%} 过高 —— 几乎没有训练信号！'
    return True

assert inspect_batch(bclm, tok)
print('\\n✅ 把这个函数放在训练循环前跑一次 —— 它检查形状、解码通顺性、mask 位置、-100 比例。')"""),
    md("""## ✏️ 练习 1：sequence_ids —— 区分特殊 token / 句 A / 句 B

实现 `sequence_ids(word_ids, sep_positions)`：返回同长度列表，
特殊 token 位置为 `None`，属于第一句的为 `0`，第二句的为 `1`。
`sep_positions` 是所有特殊 token 的下标集合；第一个特殊 token 之后到第一个 SEP 之前是句 A，
第一个 SEP 之后到最后一个 SEP 之前是句 B。

简化规则：遍历，遇到特殊 token 填 `None` 并把「当前句号」在**遇到第一个 SEP 之后**加一。"""),
    code("""def sequence_ids(word_ids, sep_positions):
    # TODO: 遍历 word_ids；下标在 sep_positions 里 -> None（且若不是第 0 个特殊 token 则句号+1）
    #       否则填当前句号
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
#  [CLS] a b [SEP] c d [SEP]
wids = [None, 0, 1, None, 2, 3, None]
seps = {0, 3, 6}
out = sequence_ids(wids, seps)
assert out == [None, 0, 0, None, 1, 1, None], out
# 单句：[CLS] a b [SEP]
assert sequence_ids([None, 0, 1, None], {0, 3}) == [None, 0, 0, None]
# 全特殊
assert sequence_ids([None, None], {0, 1}) == [None, None]
print('sequence_ids:', out)
print('✅ 练习 1 通过：QA 任务用它把 span 搜索限制在**上下文那一句**（C49 模块 03）')"""),
    md("""## ✏️ 练习 2：按长度分组的 batch 采样器

实现 `length_grouped_batches(lengths, batch_size, mega_batch_mult=4, seed=0)`：
Trainer 的 `group_by_length` 就是这个思路——
① 把索引按 `mega_batch = batch_size * mega_batch_mult` 分块（块内先随机）；
② 每块内按长度排序；③ 切成 batch；④ 最后把所有 batch 的顺序打乱（保留随机性）。
返回 batch 的索引列表（`List[List[int]]`）。"""),
    code("""def length_grouped_batches(lengths, batch_size, mega_batch_mult=4, seed=0):
    # TODO: 见上述四步
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
lens = list(np.random.default_rng(2).integers(20, 500, size=64))
batches = length_grouped_batches(lens, batch_size=8, mega_batch_mult=4, seed=1)
flat = sorted(i for b in batches for i in b)
assert flat == list(range(64)), '必须覆盖每个样本恰好一次'
assert all(len(b) <= 8 for b in batches)
# 分组后 batch 内长度应比随机分组更接近
def mean_pad_waste(bs):
    return float(np.mean([waste_rates([lens[i] for i in b])[0] for b in bs]))
rnd = np.random.default_rng(3).permutation(64)
random_batches = [list(rnd[i:i+8]) for i in range(0, 64, 8)]
w_grp, w_rnd = mean_pad_waste(batches), mean_pad_waste(random_batches)
print(f'按长度分组的平均 padding 浪费: {w_grp:.1%}')
print(f'随机分组的平均 padding 浪费  : {w_rnd:.1%}')
assert w_grp < w_rnd * 0.7, '分组应显著降低浪费'
print('✅ 练习 2 通过：这就是 Trainer 的 group_by_length=True（代价是牺牲一点随机性）')"""),
    md("""## ✏️ 练习 3：SFT 的 prompt 掩码

SFT 时只应对**回答部分**计损失，prompt 部分要填 `-100`（否则模型在背诵 prompt）。
实现 `mask_prompt_labels(input_ids, prompt_len, pad_id)`：
返回 labels —— 前 `prompt_len` 个位置为 `-100`，pad 位置为 `-100`，其余等于 `input_ids`。"""),
    code("""def mask_prompt_labels(input_ids, prompt_len, pad_id):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
ids = np.array([1, 5, 6, 7, 8, 9, PAD_ID, PAD_ID])
labs = mask_prompt_labels(ids, prompt_len=3, pad_id=PAD_ID)
assert labs.tolist() == [-100, -100, -100, 7, 8, 9, -100, -100], labs.tolist()
n_signal = int((labs != -100).sum())
assert n_signal == 3, f'只有回答的 3 个 token 计损失，得到 {n_signal}'
# prompt 很长时几乎没有信号 -> 应该被 inspect_batch 的断言抓住
labs2 = mask_prompt_labels(np.arange(1, 21), prompt_len=19, pad_id=PAD_ID)
assert float((labs2 == -100).mean()) > 0.9
print(f'labels = {labs.tolist()}  (只有回答部分计损失)')
print('✅ 练习 3 通过：**忘记掩 prompt 是 SFT 最经典的 bug** —— loss 好看但模型在背诵输入')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def sequence_ids(word_ids, sep_positions):
    out, seq, seen_special = [], 0, 0
    for i, w in enumerate(word_ids):
        if i in sep_positions:
            out.append(None)
            if seen_special > 0:      # 第一个特殊 token（CLS）之后才开始计句号
                seq += 1
            seen_special += 1
        else:
            out.append(seq)
    return out"""),
    code("""# 练习 2 参考答案
def length_grouped_batches(lengths, batch_size, mega_batch_mult=4, seed=0):
    r = np.random.default_rng(seed)
    idx = list(r.permutation(len(lengths)))
    mega = batch_size * mega_batch_mult
    batches = []
    for i in range(0, len(idx), mega):
        chunk = sorted(idx[i:i + mega], key=lambda j: lengths[j])
        for k in range(0, len(chunk), batch_size):
            batches.append(chunk[k:k + batch_size])
    order = r.permutation(len(batches))
    return [batches[i] for i in order]"""),
    code("""# 练习 3 参考答案
def mask_prompt_labels(input_ids, prompt_len, pad_id):
    labels = np.array(input_ids).copy()
    labels[:prompt_len] = -100
    labels[np.array(input_ids) == pad_id] = -100
    return labels"""),
    md("""---
## 🧪 真实 API 对照胶囊（不在本环境运行，可原样复制）"""),
    code("""RECIPE = r'''
from datasets import load_dataset
from transformers import AutoTokenizer, DataCollatorForTokenClassification

CKPT = "microsoft/deberta-v3-base"
tok = AutoTokenizer.from_pretrained(CKPT, use_fast=True)   # ① 必须 fast，否则没有 word_ids

ds = load_dataset("conll2003")            # 大数据集加 streaming=True

def prepare(batch):
    enc = tok(batch["tokens"],
              is_split_into_words=True,    # ② 输入已是词列表
              truncation=True, max_length=256,
              return_offsets_mapping=False)
    labels = []
    for i, tags in enumerate(batch["ner_tags"]):
        wids, prev, row = enc.word_ids(batch_index=i), None, []
        for w in wids:
            if w is None:      row.append(-100)      # ③ 特殊 token
            elif w != prev:    row.append(tags[w])   # ④ 每个词的第一个子词
            else:              row.append(-100)      # ⑤ 后续子词不计损失
            prev = w
        labels.append(row)
    enc["labels"] = labels
    return enc

# ⑥ batched=True 快 10-100 倍；⑦ 改变列 -> 必须 remove_columns
tokenized = ds.map(prepare, batched=True, batch_size=1000,
                   remove_columns=ds["train"].column_names)

# ⑧ 动态 padding（labels 用 -100 补齐）
collator = DataCollatorForTokenClassification(tok, padding=True)

# ⑨ 训练前必做：打印一个 batch 检查四件事
import torch
batch = collator([tokenized["train"][i] for i in range(4)])
print({k: tuple(v.shape) for k, v in batch.items()})
print(tok.decode(batch["input_ids"][0]))
print("labels -100 占比:", (batch["labels"] == -100).float().mean().item())

# ⑩ 统计截断率（放进预处理脚本，超阈值就告警）
lens = [len(tok(" ".join(x["tokens"]))["input_ids"]) for x in ds["train"].select(range(2000))]
import numpy as np
print("p50/p95/p99:", np.percentile(lens, [50, 95, 99]),
      "截断率:", np.mean(np.array(lens) > 256))
'''
print(RECIPE)
for c in ['use_fast=True', 'word_ids', '-100', 'batched=True', 'remove_columns', '截断率']:
    assert c in RECIPE, c
print('✅ 配方覆盖本模块全部要点')"""),
    md("""### 小结
- **fast tokenizer 的真正价值是 `offset_mapping` 与 `word_ids()`**：前者把 token 预测映射回原文字符（QA 必需，**不能用 decode 拼**），后者把词级标注对齐到子词（NER 必需）。特殊 token 的 offset 是 `(0,0)` 不是 `None`。
- **`padding='max_length'` 可能浪费 89% 的注意力计算**；动态 padding 帮助有限，真正的杠杆是 **按长度分组**（`group_by_length=True`）。
- **截断是静默的**。要分开统计**截断率**与**信息损失率**——后者高意味着系统性丢弃某个子群体。
- **`map(batched=True)` 快 10–100 倍，但函数签名不同**（字符串 vs 字符串列表）；**改变行数就必须 `remove_columns`**；指纹缓存按函数字节码算，依赖外部可变状态时要 `load_from_cache_file=False`。
- **流式没有 `len()`、只能缓冲区近似打乱**；缓冲太小 + 磁盘有序 = 同 batch 高度相关。
- **`-100` 是全生态约定**：padding、非首子词、SFT 的 prompt 部分都要填它。漏填让 loss 更好看但效果更差。
- 带走那个 **「打印一个 batch 检查四件事」** 的习惯：形状、解码通顺性、mask 位置、-100 比例。

下一站：**模块 03 · Trainer 与 TrainingArguments** —— 训练循环里那些相乘才有意义的参数。"""),
]
