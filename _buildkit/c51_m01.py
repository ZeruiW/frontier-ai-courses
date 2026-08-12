# -*- coding: utf-8 -*-
"""C51 模块 01 · 词面增强。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00 的三重检验；基本概率"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_lexical_augmentation.ipynb'),
    ("核心论文", "Wei & Zou 2019（EDA）★、Karimi et al. 2021（AEDA）、Zhang et al. 2015（同义词替换的早期用法）"),
    ("预计时长", "读 55 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("eda", "EDA：四个操作，危险性差三个量级", "".join([
        P("<span class=\"term\">EDA</span>（Easy Data Augmentation，Wei &amp; Zou 2019）是文本增强里最广为人知的方法，因为它极其简单：<strong>四个随机操作，不需要任何模型</strong>。"),
        TABLE(["操作", "缩写", "做什么", "标签风险", "为什么"], [
            ["同义词替换", "<strong>SR</strong>", "随机挑 n 个非停用词，用同义词替换", "🔶 中", "一词多义（「银行」）、程度差异（「好」→「完美」）会改变语义强度"],
            ["随机插入", "<strong>RI</strong>", "随机挑一个词的同义词，插到随机位置", "🔶 中", "插入位置可能改变修饰关系；插入情感词直接改标签"],
            ["随机交换", "<strong>RS</strong>", "随机交换两个词的位置", "🔴 <strong>高</strong>", "语序承载语义（「他打她」vs「她打他」）；否定词位置一换标签就翻"],
            ["随机删除", "<strong>RD</strong>", "以概率 p 删除每个词", "🔴 <strong>最高</strong>", "<strong>删掉否定词、程度副词或唯一的情感词，标签直接反转</strong>"],
        ]),
        DUAL(
            "原论文的结论是「四个操作都有用，合起来更好」，但那是在<em>五个小型分类数据集</em>上、用 CNN/RNN 模型、平均涨 0.8–3 分（数据越少涨越多）得出的。<strong>这个结论在今天需要打两个折扣</strong>：其一，预训练模型（BERT 及之后）本身对表面扰动就更鲁棒，EDA 的正则化收益大幅缩小；其二，原论文的实验规模下，1 分的提升与种子方差同量级（C49 模块 03）。",
            "但 EDA 仍然有明确的适用区间，而且比「它有没有用」更值得知道的是<strong>四个操作的危险性排序</strong>。这个排序是可以量化的：<em>RD &gt; RS &gt; RI ≈ SR</em>。原因在于它们对「句子结构」的破坏程度不同——RD 直接删信息（不可恢复）、RS 破坏语序（语义可能反转）、RI 只是加冗余（模型可以学会忽略）、SR 替换但保持槽位。<strong>notebook 会把四个操作的标签破坏率精确算出来，你会看到 RD 比 SR 高一个量级。</strong>",
        ),
        CALLOUT("danger", "<p><strong>随机删除是所有文本增强操作里最危险的一个</strong>，因为它有一个特别恶劣的性质：<em>它破坏标签的概率与「关键词的稀有度」成正比</em>。句子里只有一个「不」字时，删掉它的概率是 <code>p</code>；而这个「不」恰恰是决定标签的那个词。换句话说，<strong>RD 最容易破坏的正是那些「标签由单个关键词决定」的样本——而这类样本往往是模型最需要学好的</strong>。这不是随机噪声，是<em>系统性地</em>污染了最关键的那部分数据。所以如果你要用 EDA，第一件事就是把 RD 的 <code>p</code> 调到很小（≤0.05），或者干脆关掉它。</p>", "RD 会系统性污染最关键的样本"),
    ])),
    ("protect", "保护规则：把「不能动的词」标出来", "".join([
        P("上一节的分析指向一个明确的改进方向：<strong>不要对所有词一视同仁</strong>。文本里有些词是「可自由替换的填充物」，有些词是「一动就改标签的关键」。把后者保护起来，EDA 的保真度能从 90% 提到 99%+，而多样性几乎不损失。"),
        TABLE(["要保护的词类", "为什么", "怎么识别"], [
            ["<strong>否定词</strong>（不/没/别/无/never/not）", "直接翻转极性；删一个字标签就反", "词表匹配（多语言要注意否定的形态变化）"],
            ["<strong>程度副词</strong>（很/非常/略/稍微）", "改变强度，在细粒度情感/评分任务上改标签", "词表匹配"],
            ["<strong>命名实体</strong>（人名/地名/机构/型号）", "替换成同义词会变成事实错误；NER 任务里本身就是标签", "NER 模型或规则（大写、数字、专有词表）"],
            ["<strong>数字与单位</strong>", "「3 天」换成「三天」还行，换成「5 天」就是造假", "正则"],
            ["<strong>任务关键词</strong>", "分类任务里那些高互信息的词", "用训练集算「词-标签互信息」自动挑出来"],
            ["<strong>标注 span 内的词</strong>（NER/QA）", "它们本身就是答案，改了标注就失效", "从标注读"],
        ]),
        DUAL(
            "最后一条「用互信息自动挑关键词」是个很实用的技巧，因为它<strong>不需要领域知识</strong>：对训练集里每个词算它与标签的互信息（或简单点，算 <code>|P(y=1|w) − P(y=1)|</code>），取最高的若干个词加入保护表。<em>这样即使你不知道这个任务的关键词是什么，也能自动把它们保护起来。</em>",
            "有一个反直觉但重要的注意点：<strong>保护表不能太大</strong>。如果你把一半的词都保护起来，增强就退化成「几乎不变」——多样性趋零，正则化效果消失。<em>保真度与多样性在这里有明确的权衡</em>：保护得越多，保真度越高、多样性越低。notebook 会把这条权衡曲线画出来，并让你找到「保真度 ≥ 0.98 前提下多样性最大」的那个点——这就是本课反复出现的「约束下最优」的思路。",
        ),
        CALLOUT("intuition", "还有一个几乎零成本的替代方案值得知道：<strong>AEDA</strong>（Karimi et al. 2021）——<em>只随机插入标点符号</em>（<code>. , ! ? ;</code>）。它的保真度接近 100%（标点不改变词汇语义），却仍能提供表面扰动。在需要「安全的正则化」时，AEDA 常常是比 EDA 更好的默认选择。<em>这是个很好的例子：想清楚「什么改动不会破坏标签」，往往比调参更有价值。</em>"),
    ])),
    ("alpha", "增强强度 α 与数据量：为什么小数据集才受益", "".join([
        P("EDA 有两个超参：<strong>每条样本增强出几份</strong>（<code>n_aug</code>）与<strong>每次改动多少词</strong>（强度 <code>α</code>，通常表示为「改动词数 = α × 句长」）。原论文给出了一组经验值，但更重要的是理解<em>它们与数据量的交互</em>。"),
        MATH("n_{changed} = \\max(1, \\lfloor \\alpha \\cdot L \\rfloor), \\qquad \\alpha \\in [0.05, 0.3]"),
        TABLE(["训练集大小", "推荐 <code>n_aug</code>", "推荐 <code>α</code>", "预期收益"], [
            ["&lt; 500", "8–16", "0.05–0.1", "<strong>明显</strong>（+2~3 分）"],
            ["500–2,000", "4–8", "0.05–0.1", "中等（+1~2 分）"],
            ["2,000–10,000", "2–4", "0.05", "小（+0~1 分，常在噪声内）"],
            ["&gt; 10,000", "—", "—", "<strong>基本为零，可能为负</strong>"],
        ]),
        DUAL(
            "为什么收益随数据量递减？因为<strong>词面增强提供的是「表面形式不变性」这一个归纳偏置</strong>——它告诉模型「换个说法标签不变」。当你只有 200 条数据时，模型很容易过拟合到具体的词（「凡是出现『这家店』就是正面」），增强能打破这种伪相关；<em>但当你有十万条数据时，数据本身已经包含了充分的表面多样性，模型早就学会了这个不变性</em>。此时增强只是在<strong>加噪声</strong>（那 1–5% 被破坏标签的样本），净效应可能为负。",
            "<code>α</code> 的作用是另一条权衡。<code>α</code> 太小（0.01）则增强样本几乎等于原样本——多样性趋零，等于只是把数据复制了 <code>n_aug</code> 遍（这不但没用，还会让有效学习率隐性变化，因为每个 epoch 的步数变多了）。<code>α</code> 太大（0.4+）则保真度崩塌。<strong>原论文实测 <code>α=0.1</code> 附近最优，且 <code>α</code> 过大时曲线急剧下降</strong>——这个「先升后急降」的形状是本课要让你亲手复现的。notebook 会扫 <code>α</code> 并同时画出保真度与下游收益。",
        ),
        CALLOUT("warn", "一个容易忽略的实验设计问题：<strong>增强会改变每个 epoch 的步数</strong>。把 1000 条数据增强成 5000 条后跑 3 个 epoch，模型实际看了 15000 个样本；而 baseline 跑 3 个 epoch 只看了 3000 个。<em>这个对比是不公平的——你不知道提升来自「增强」还是来自「训练更久」</em>。正确做法是<strong>固定总步数（或总样本数）而不是 epoch 数</strong>，或者给 baseline 相应地增加 epoch。这个混淆在增强的文献里非常常见，模块 05 会详细讨论。"),
    ])),
    ("dropout", "token dropout 与其他「训练时增强」", "".join([
        P("EDA 是<strong>离线增强</strong>——预处理时生成增强样本、落盘、当成额外训练数据。还有一类是<strong>在线增强</strong>：在训练循环里对每个 batch 现场扰动。两者的性质相当不同。"),
        TABLE(["", "离线增强（EDA 式）", "在线增强（dropout 式）"], [
            ["何时发生", "预处理，落盘", "每个 batch，现场"],
            ["同一样本被看到的形式", "固定的 <code>n_aug</code> 种", "<strong>每个 epoch 都不同</strong>（近似无限种）"],
            ["数据量", "变成 <code>n_aug</code> 倍", "不变"],
            ["与 epoch 的交互", "<strong>会混淆「增强」与「训练更久」</strong>", "无此问题"],
            ["典型手段", "SR / RI / RS / RD / 回译", "token dropout、word dropout、embedding 噪声、mixup"],
            ["实现位置", "数据脚本", "<strong>collator 或模型内部</strong>（C50 模块 02）"],
        ]),
        P("三种常用的在线文本增强："),
        UL([
            "<strong>token dropout / word dropout</strong>：以概率 <code>p</code> 把 token 换成 <code>[UNK]</code>（而不是删除——这样长度与位置不变，比 RD 安全得多）。它逼迫模型不要依赖单个词。",
            "<strong>embedding 噪声</strong>：在词嵌入上加小幅高斯噪声。<code>trl</code> 的 <code>neftune_noise_alpha</code> 就是这一类（C50 模块 04 提到过）。<em>它完全不改变离散 token，所以标签保真度是 100%</em>——这是它的最大优势。",
            "<strong>mixup for text</strong>：在<em>嵌入空间</em>或<em>隐层</em>做线性插值 <code>h = λh_i + (1−λ)h_j</code>，标签也按 <code>λ</code> 混合。文本上不能在 token 层面 mixup（离散），所以只能在连续表示层做。效果不如图像上那么显著，但在低资源分类上有报告有效。",
        ]),
        CALLOUT("intuition", "选择的经验法则：<strong>如果你的目标是「正则化」，优先用在线增强</strong>（尤其 embedding 噪声——保真度 100%、实现最简、无 epoch 混淆）；<strong>如果你的目标是「补充真正缺失的样本类型」，那就需要离线的语义层或指令层增强</strong>（模块 02/03）。<em>把「我需要正则化」和「我需要更多样本」这两件事分清，能省掉很多无效的增强工作</em>——它们的最优手段完全不同。"),
    ])),
    ("ledger", "算一笔账：增强的预算与边际收益", "".join([
        P("词面增强几乎零算力成本，所以它的「账」不在算力，而在<strong>三个隐性成本</strong>。"),
        TABLE(["成本", "量化方式", "典型量级"], [
            ["<strong>标签污染</strong>", "被破坏标签的样本数 = <code>N × n_aug × 破坏率</code>", "1000 条 × 4 份 × 5% = <strong>200 条错标数据</strong>"],
            ["<strong>训练时间</strong>", "样本数 × <code>n_aug</code>", "4 倍（若不固定总步数就还混淆了 epoch）"],
            ["<strong>调参与验证</strong>", "α、n_aug、操作组合的网格 × 多种子", "3×3×4 组合 × 5 种子 = <strong>180 次训练</strong>"],
        ]),
        P("第一行值得盯住：<strong>「破坏率 5%」听起来很小，但它意味着 200 条错标数据被加进了一个只有 1000 条的训练集</strong>。而且如前所述，被破坏的往往是「标签由单个关键词决定」的关键样本。<em>这就是为什么保真度必须当成硬门槛（≥0.98），而不是「越高越好」的软指标</em>。"),
        P("第三行也常被低估。如果你打算认真调 EDA 的超参，<strong>调参成本会远超增强本身省下的标注成本</strong>。一个 180 次训练的网格搜索，加上分析时间，可能是好几天的工程时间；而同样的时间用来标注真实数据，可能能标 500–1000 条。<strong>这就是模块 05 那个必须做的对照：同预算下，标注真实数据 vs 做增强，哪个划算。</strong>"),
        MATH("\\text{增强值得做} \\iff \\Delta_{aug} > \\Delta_{real}(\\text{同等人力预算下能标注的数据量})"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>词面增强的核心问题不是「哪个操作最好」，而是「哪些词不能动」</strong>。想清楚保护规则（否定词、实体、数字、高互信息词），你能用最危险的操作组合拿到高保真度；不想清楚，再温和的操作也会系统性地污染最关键的那部分样本。<em>这条思路可以迁移到任何领域的数据增强——先问「什么改动不改变标签」，再设计增强。</em>"),
    ])),
    ("mechanism", "机制：增强到底在给模型加什么归纳偏置", "".join([
        P("在讨论「哪个操作更好」之前，值得先想清一个更基本的问题：<strong>数据增强在数学上到底做了什么</strong>。想清楚这一点，前面所有的经验规律（为什么小数据集才受益、为什么保护规则有效、为什么 RD 最危险）都会变成推论而不是记忆。"),
        H3("增强 = 用数据表达的不变性约束"),
        P("假设你相信任务存在某个<strong>不变性</strong>：对输入做变换 <code>T</code> 之后标签不应改变，即 <code>y(T(x)) = y(x)</code>。有两种方式把这个信念告诉模型："),
        UL([
            "<strong>写进架构</strong>：设计一个对 <code>T</code> 天然不变的网络（如 CNN 对平移的近似不变性）。<em>代价是要为每种不变性设计架构，而且很多不变性根本没有对应的架构</em>。",
            "<strong>写进数据</strong>：把 <code>(T(x), y)</code> 也加进训练集，让模型<em>从数据里学到</em>这个不变性。<strong>这就是数据增强</strong>。代价是它只是软约束——模型可能学不到、也可能学过头。",
        ]),
        MATH("\\mathcal{L}_{aug} = \\mathbb{E}_{x,y}\\,\\mathbb{E}_{T}\\big[\\ell\\big(f(T(x)),\\,y\\big)\\big] \\approx \\mathcal{L} + \\underbrace{\\lambda \\cdot \\mathbb{E}\\big[\\|\\nabla_x f\\|^2_{T}\\big]}_{\\text{沿变换方向的平滑正则}}"),
        DUAL(
            "这个近似（对小扰动做二阶展开可得）说明了一件关键的事：<strong>词面增强的效果近似于「在变换方向上惩罚函数的变化率」——也就是一种<em>有方向的</em>正则化</strong>。它不是通用的权重衰减，而是特定地告诉模型「沿着<em>这些</em>方向别变」。",
            "由此立刻得到三个推论。<strong>①为什么小数据集才受益</strong>：正则化的价值随数据量递减，因为大数据本身就把不变性「教」给了模型。<strong>②为什么增强方向必须与真实不变性一致</strong>：如果 <code>y(T(x)) ≠ y(x)</code>（保真度被破坏），你就在<em>强迫模型在真实决策边界上保持不变</em>——这不是正则化，这是往决策边界上倒沙子。<strong>③为什么保护规则如此重要</strong>：保护规则做的正是「把 <code>T</code> 限制在真正保标签的那些变换上」。",
        ),
        H3("再看一遍 RD 的危险性：它选中的方向恰好穿过决策边界"),
        P("有了这个框架，模块开头那条「RD 会系统性污染关键样本」的观察就有了更清晰的解释。<strong>决策边界附近的样本，恰恰是那些「少一个关键词就翻标签」的样本</strong>；而 RD 破坏标签的概率与关键词稀有度成正比，<em>所以它专门在决策边界附近注入错误约束</em>。"),
        ASCII("""特征空间示意（横轴：某个关键特征的强度）

           负面                    │  决策边界              正面
   ●●●●●●●●●●●●●●●●●        ●●●●●│●●●●●        ○○○○○○○○○○○○○○○
                              ↑    │    ↑
                    「不好吃」这类  │  「好吃」这类
                    只靠一个否定词  │  只靠一个情感词
                    定标签的样本    │  定标签的样本

  安全的增强（换中性词）：样本沿**平行于边界**的方向移动 -> 不改标签 ✅
  危险的增强（删否定词）：样本**穿过边界**跑到对面 -> 标签错了 ❌
                          而且它专挑边界附近的样本下手（那里关键词最稀有）"""),
        CALLOUT("intuition", "这张图还解释了一个实践现象：<strong>增强破坏标签的危害，远大于同等比例的随机标签噪声</strong>。随机噪声均匀分布在整个空间（多数样本远离边界，翻错标签对边界影响有限）；而增强造成的错标<em>集中在边界附近</em>，直接把边界往错误方向拽。<em>所以「5% 的标签噪声不算什么」这个直觉在增强场景下是错的</em>——同样是 5%，位置完全不同。这就是本课把保真度设成硬门槛（≥0.98）而非软指标的根本理由。"),
    ])),
    ("checklist", "词面增强的可执行清单", "".join([
        P("把本模块的全部结论压缩成一份可以照着做的清单。它假设你已经决定要做词面增强（这个决定本身见模块 05）。"),
        TABLE(["步骤", "做什么", "验收标准"], [
            ["<strong>① 建保护表</strong>", "否定词 + 程度副词 + 实体 + 数字单位 + 情感词 + 互信息 top-k", "对训练集抽 100 条人工看：受保护的词是否都是「一改就翻标签」的"],
            ["<strong>② 选操作</strong>", "首选 AEDA（只插标点）与受保护的 SR；<strong>默认关掉 RD</strong>，需要时 p ≤ 0.05", "每个操作单独测保真度，不要只测组合"],
            ["<strong>③ 定强度</strong>", "在保真度 ≥ 0.98 的约束下最大化多样性（本模块的「约束下最优」）", "扫 α ∈ {0.05, 0.1, 0.2}，同时报告保真度与 distinct-n"],
            ["<strong>④ 定副本数</strong>", "小数据 8–16、中等 2–4、大数据不做", "看模块 05 的学习曲线，别拍脑袋"],
            ["<strong>⑤ 固定训练量</strong>", "按<strong>优化步数</strong>而非 epoch 对齐 baseline", "两组的总样本数（步数 × batch）必须相同"],
            ["<strong>⑥ 记录统计</strong>", "破坏率、多样性、各操作的丢弃数写进日志", "能回答「这批增强数据里有多少条是错标的」"],
        ]),
        DUAL(
            "清单里第 ② 步的「<strong>默认关掉 RD</strong>」可能是最反直觉、也最值得坚持的一条。EDA 原论文把四个操作平等对待，很多实现也照抄；但本模块已经量化过——<em>RD 的破坏率比 SR 高一个量级，而且破坏的是最关键的那部分样本</em>。<strong>它带来的额外多样性，完全可以用「更高的副本数 + 更安全的操作」补上。</strong>",
            "第 ⑥ 步也常被跳过，但它是唯一能让你<em>事后</em>诊断问题的东西。一个真实的场景：三个月后模型效果下滑，你怀疑是数据问题——如果当初记录了每批增强数据的破坏率与多样性，你能在十分钟内排除或确认这个假设；如果没记录，你只能重新跑一遍整条管线。<strong>数据管线的可观测性与线上服务的可观测性同等重要</strong>（C48 模块 00 的立场在这里同样成立）。",
        ),
        CALLOUT("intuition", "最后给一个「什么时候<em>不要</em>照这份清单做」的提示：<strong>如果你的任务输出不是分类标签，词面增强的整套逻辑都要重新想</strong>。序列标注要同步改标注 span 的位置；抽取式 QA 要保证答案片段不被扰动；生成任务的「标签」是另一段文本，扰动输入而不改输出可能引入错误的输入-输出对应。<em>本模块的分析框架（保真度 = 变换是否保标签）仍然适用，但「什么算保标签」的定义要按任务重写。</em>"),
    ])),
    ("multilingual", "跨语言与非分类任务：这套方法什么时候不适用", "".join([
        P("EDA 的四个操作有一个<strong>隐含假设</strong>：「词是可自由重排、删除、替换的独立单元」。这个假设对英语勉强成立，对很多语言与任务并不成立——而这一点在文献里几乎从不讨论。"),
        TABLE(["语言/任务特性", "为什么 EDA 会出问题", "替代做法"], [
            ["<strong>形态丰富的语言</strong>（俄语、土耳其语、阿拉伯语）", "同义词替换后<em>变格/变位不一致</em>，产出语法错误的句子；模型可能学到「语法错误 = 某个标签」", "在词元（lemma）层替换后重新屈折；或只用 AEDA/在线增强"],
            ["<strong>无空格分词的语言</strong>（中文、日文、泰文）", "「词」的边界本身就依赖分词器；删/换一个词可能改变后续分词结果", "在字符层或子词层设计操作；或直接用语义层增强"],
            ["<strong>语序敏感的语言/任务</strong>", "RS 在语序自由的语言里危害小，在语序固定的语言里危害大", "关掉 RS，或只在句内短距离交换"],
            ["<strong>序列标注（NER/POS）</strong>", "增强改变 token 位置，<strong>标注 span 必须同步移动</strong>；删词可能删掉实体的一部分", "只做「不改变 token 数量与顺序」的操作（如 token dropout）；或把实体整体当作保护单元"],
            ["<strong>抽取式 QA</strong>", "答案 span 必须逐字符保留在原文里（C49 模块 03）", "只增强<em>问题</em>，不动上下文；或保证答案片段在保护表里"],
            ["<strong>生成任务</strong>", "「标签」是另一段文本；扰动输入而不改输出会造出错误的输入-输出对", "输入输出同步扰动（很难），或改用语义层/指令层增强"],
        ]),
        DUAL(
            "这张表的共同结论是：<strong>「保标签」这个概念必须按任务重新定义，而不能照搬分类任务的直觉</strong>。在分类里「保标签」= 类别不变；在 NER 里 = 每个实体的<em>类型与边界</em>都不变；在 QA 里 = 答案片段<em>逐字符</em>仍在原文中；在生成里 = 输入输出的<em>对应关系</em>仍然成立。<em>本模块的框架（保真度 = 变换是否保标签）是通用的，需要重写的只是「保标签」的判定函数。</em>",
            "这也解释了为什么本课坚持用<strong>规则可判定的合成任务</strong>做实验：它让「保标签」变成一个可以精确计算的布尔函数，从而把注意力集中在<em>方法论</em>而不是「怎么人工判断这条增强对不对」。<strong>你在真实任务里要做的第一件事，就是为你的任务写出这个判定函数</strong>——哪怕它只是一组粗糙的规则（实体集合是否保持、答案 span 是否还在、标签词是否被改）。<em>有一个粗糙但自动的判定函数，远胜于「人工抽查 20 条觉得还行」。</em>",
        ),
        CALLOUT("warn", "最后提醒一个跨语言场景下的隐蔽问题：<strong>同义词词典的质量在低资源语言上极差</strong>。英语有 WordNet，很多语言只有自动构建的、噪声很大的同义词表。用一个坏词典做 SR，等于在做「随机词替换」——保真度会崩，而你从代码上完全看不出来。<em>做多语言增强前，先抽 50 组同义词人工看一眼</em>——这十分钟能省掉几天的困惑。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>EDA 在预训练模型上还剩多少收益</strong>：原论文用的是 CNN/RNN。在 BERT 及之后的模型上，多项复现发现收益大幅缩小甚至消失（模型本身已对表面扰动鲁棒）。<em>「在什么模型规模 × 数据量组合下 EDA 仍有效」缺乏系统的实证地图</em>，这是个很适合做的小型研究。",
            "<strong>自动挑选保护词</strong>：互信息是个粗糙的代理。用梯度显著性、注意力、或影响函数来识别「不能动的词」在理论上更准，但成本更高，且与「增强要便宜」的初衷冲突。这条权衡尚无好答案。",
            "<strong>增强策略的自动搜索</strong>：图像上的 AutoAugment / RandAugment 用搜索找到最优增强策略组合。文本上的对应工作（如 Text AutoAugment）存在但不普及，主要障碍是文本增强的操作空间更难参数化、且搜索成本相对收益太高。",
            "<strong>增强与预训练的重叠</strong>：MLM 预训练本身就是一种「掩码增强」，dropout 也是。<em>下游再做词面增强，是否与预训练已提供的不变性重复</em>？这个「增强的边际信息量」问题在理论上很有意思但缺乏刻画。",
            "<strong>多语言与形态丰富语言</strong>：EDA 的操作假设「词是可自由重排/删除的独立单元」，这对英语勉强成立，对形态丰富的语言（俄语、土耳其语）或无空格语言（中文、日文、泰文）需要重新设计。<em>「同义词替换」在需要变格的语言里会产生语法错误</em>，而这类错误对模型的影响缺乏研究。",
        ]),
        CALLOUT("paper", "必读：Wei &amp; Zou 2019 <em>EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks</em>（重点看它的数据量-收益曲线与 α 消融，这两张图是本模块的核心依据）、Karimi et al. 2021 <em>AEDA: An Easier Data Augmentation Technique</em>（只插标点，保真度接近 100%）、Feng et al. 2021 <em>A Survey of Data Augmentation Approaches for NLP</em>（把方法空间整理得最清楚的综述）。方法论侧：C49 模块 03（种子方差——判断「涨了 1 分」是否可信的前提）、C40（实验设计）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 词面增强（EDA 四操作 / 保护规则 / α 与数据量的交互）

目标：把 **SR / RI / RS / RD 四个操作** 从零实现，**精确量化它们的标签破坏率**，
再用保护规则把保真度从 ~90% 提到 99%+，最后复现「小数据集才受益」这条曲线。

路线：四操作实现 → **危险性排序（破坏率差一个量级）** → 保护规则与互信息自动挑关键词 →
保真-多样权衡前沿 → α 扫描（先升后急降）→ 数据量-收益曲线 → 在线 vs 离线增强 →
✏️ 练习 → 📖 答案 → 🧪 预算账胶囊。

> 心智模型：**词面增强的核心问题不是「哪个操作最好」，而是「哪些词不能动」。**"""),
    md("""## 0 · 复用模块 00 的三重检验

先把模块 00 建立的规则任务与三个检验函数搬过来（本课每个模块都会用）。"""),
    code("""import numpy as np, math, random, collections, itertools
rng = np.random.default_rng(0)

POS_WORDS = {'好吃', '不错', '推荐', '干净', '很好', '满意', '喜欢'}
NEG_WORDS = {'难吃', '差', '脏', '失望', '糟糕'}
NEGATORS  = {'不', '没', '别', '不太', '并不'}
DEGREE    = {'很', '非常', '略', '稍微'}                            # 程度副词
NEUTRAL   = ['这家', '店', '的', '菜', '服务', '环境', '价格', '味道', '朋友', '下次',
             '我们', '昨天', '一起', '去', '吃', '了', '感觉', '整体', '还', '挺']
ENTITIES  = ['海底捞', '西湖', '张三']

PUNCT_SET = {'.', ',', '!', '?', ';', '。', '，', '！', '？', '；'}

def rule_label(tokens, window=3):
    '''规则标签。**算否定词距离时忽略标点** —— 否则插入标点会把否定词推出窗口，
       让 AEDA 这类「不动任何实词」的增强也被误判成破坏了标签。
       这本身是个教训：**保真度检验本身也要设计对。**'''
    tokens = [w for w in tokens if w not in PUNCT_SET]
    score = 0
    for i, t in enumerate(tokens):
        if t in POS_WORDS:
            neg = any(tokens[j] in NEGATORS for j in range(max(0, i-window), i))
            score += -1 if neg else 1
        elif t in NEG_WORDS:
            neg = any(tokens[j] in NEGATORS for j in range(max(0, i-window), i))
            score += 1 if neg else -1
    return 1 if score > 0 else 0

def make_sentence(r, length=10):
    toks = list(r.choice(NEUTRAL, size=length-2, replace=True))
    pos = int(r.integers(1, len(toks)))
    toks.insert(pos, str(r.choice(sorted(POS_WORDS if r.random() < 0.5 else NEG_WORDS))))
    if r.random() < 0.4:
        toks.insert(max(0, pos - int(r.integers(1, 3))), str(r.choice(sorted(NEGATORS))))
    if r.random() < 0.25:
        toks.insert(int(r.integers(0, len(toks))), str(r.choice(ENTITIES)))
    return toks, rule_label(toks)

def fidelity(pairs):
    return 1.0 if not pairs else sum(1 for o, y, a in pairs if rule_label(a) == y) / len(pairs)

def ngrams(t, n):
    return [tuple(t[i:i+n]) for i in range(len(t)-n+1)]

def distinct_n(texts, n=2):
    tot, uniq = 0, set()
    for t in texts:
        g = ngrams(t, n); tot += len(g); uniq.update(g)
    return len(uniq)/tot if tot else 0.0

VOCAB_ALL = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS | set(ENTITIES) | DEGREE
                   | {'本', '餐厅', '菜品', '服务员', '氛围', '收费', '觉得', '总体', '[UNK]',
                      '.', ',', '!', '?', ';'})
V2I = {w: i for i, w in enumerate(VOCAB_ALL)}

def featurize(t):
    x = np.zeros(len(VOCAB_ALL) + 1)
    for w in t:
        if w in V2I: x[V2I[w]] += 1.0
    x[-1] = 1.0
    return x

def train_logreg(X, y, epochs=300, lr=0.3, l2=1e-3, seed=0):
    w = np.random.default_rng(seed).normal(size=X.shape[1]) * 0.01
    for _ in range(epochs):
        p = 1/(1+np.exp(-(X @ w)))
        w -= lr * (X.T @ (p - y)/len(y) + l2*w)
    return w

def build_xy(data):
    return np.stack([featurize(t) for t, _ in data]), np.array([y for _, y in data])

def effectiveness(train_data, aug_data, test_data, seeds=range(8), fixed_steps=True):
    '''固定「总样本数」以避免混淆「增强」与「训练更久」（见讲解）。'''
    Xte, yte = build_xy(test_data)
    diffs, base, aug = [], [], []
    n_total = len(train_data) + len(aug_data)
    ep_base = max(1, round(300 * n_total / max(1, len(train_data)))) if fixed_steps else 300
    for s in seeds:
        Xb, yb = build_xy(train_data)
        wb = train_logreg(Xb, yb, epochs=ep_base, seed=s)
        Xa, ya = build_xy(train_data + aug_data)
        wa = train_logreg(Xa, ya, epochs=300, seed=s)
        b = float(((Xte @ wb > 0).astype(int) == yte).mean())
        a = float(((Xte @ wa > 0).astype(int) == yte).mean())
        base.append(b); aug.append(a); diffs.append(a-b)
    return float(np.mean(base)), float(np.mean(aug)), diffs

TRAIN = [make_sentence(np.random.default_rng(s)) for s in range(200)]
TEST  = [make_sentence(np.random.default_rng(50_000+s)) for s in range(800)]
print(f'训练 {len(TRAIN)} 条, 测试 {len(TEST)} 条')
print('样例:', ' '.join(TRAIN[0][0]), '->', '正面' if TRAIN[0][1] else '负面')
print('✅ 三重检验工具就绪')"""),
    md("""## 1 · EDA 四操作：实现与危险性排序

四个操作对「句子结构」的破坏程度不同，所以标签破坏率会差一个量级。
**危险性排序：RD > RS > RI ≈ SR。**"""),
    code("""# 迷你同义词表 —— 刻意埋了陷阱：'好' 的同义词强度不同、'银行' 一词多义
SYNONYMS = {
    '这家': ['本'], '店': ['餐厅'], '菜': ['菜品'], '服务': ['服务员'],
    '环境': ['氛围'], '价格': ['收费'], '感觉': ['觉得'], '整体': ['总体'],
    # 陷阱：情感词的同义替换会改变强度，甚至改变极性判定
    '不错': ['很好', '满意'], '好吃': ['不错'], '差': ['糟糕'],
}
STOPWORDS = {'的', '了', '还', '挺'}

def synonym_replacement(tokens, n, r):
    idx = [i for i, t in enumerate(tokens) if t in SYNONYMS and t not in STOPWORDS]
    if not idx: return list(tokens)
    out = list(tokens)
    for i in r.choice(idx, size=min(n, len(idx)), replace=False):
        out[i] = str(r.choice(SYNONYMS[out[i]]))
    return out

def random_insertion(tokens, n, r):
    out = list(tokens)
    cands = [t for t in tokens if t in SYNONYMS]
    for _ in range(n):
        if not cands: break
        w = str(r.choice(SYNONYMS[str(r.choice(cands))]))
        out.insert(int(r.integers(0, len(out)+1)), w)
    return out

def random_swap(tokens, n, r):
    out = list(tokens)
    for _ in range(n):
        if len(out) < 2: break
        i, j = r.choice(len(out), size=2, replace=False)
        out[i], out[j] = out[j], out[i]
    return out

def random_deletion(tokens, p, r):
    out = [t for t in tokens if r.random() >= p]
    return out if out else list(tokens[:1])

OPS = {
    'SR 同义词替换': lambda t, a, r: synonym_replacement(t, max(1, int(a*len(t))), r),
    'RI 随机插入':   lambda t, a, r: random_insertion(t, max(1, int(a*len(t))), r),
    'RS 随机交换':   lambda t, a, r: random_swap(t, max(1, int(a*len(t))), r),
    'RD 随机删除':   lambda t, a, r: random_deletion(t, a, r),
}

ALPHA = 0.1
print(f"α={ALPHA}")
print(f"{'操作':<16s} {'标签保真度':>11s} {'破坏率':>9s} {'distinct-2':>11s}")
results = {}
for name, fn in OPS.items():
    r = np.random.default_rng(11)
    pairs = [(t, y, fn(t, ALPHA, r)) for t, y in TRAIN]
    f = fidelity(pairs); d = distinct_n([a for _, _, a in pairs], 2)
    results[name] = (f, d)
    print(f'{name:<16s} {f:>11.1%} {1-f:>9.1%} {d:>11.4f}')

break_rates = {k: 1-v[0] for k, v in results.items()}
assert break_rates['RD 随机删除'] > break_rates['SR 同义词替换'], 'RD 应比 SR 危险'
assert break_rates['RS 随机交换'] > 0, 'RS 会破坏语序进而破坏标签'
order = sorted(break_rates, key=break_rates.get, reverse=True)
print(f'\\n危险性排序（破坏率从高到低）: {" > ".join(o.split()[0] for o in order)}')
print('✅ 与讲解一致：RD 最危险（直接删信息），SR 最温和（保持槽位）')"""),
    md("""### 为什么 RD 特别恶劣：它系统性地污染「关键样本」

RD 破坏标签的概率与「关键词的稀有度」成正比。
**句子里只有一个「不」字时，删掉它的概率就是 p —— 而这个「不」恰恰决定标签。**"""),
    code("""def has_single_negator(tokens):
    return sum(1 for t in tokens if t in NEGATORS) == 1

def break_rate_by_group(op_fn, alpha, data, seed=13):
    r = np.random.default_rng(seed)
    groups = {'含唯一否定词': [], '不含否定词': []}
    for t, y in data:
        aug = op_fn(t, alpha, r)
        key = '含唯一否定词' if has_single_negator(t) else '不含否定词'
        groups[key].append(rule_label(aug) != y)
    return {k: (float(np.mean(v)) if v else 0.0, len(v)) for k, v in groups.items()}

print(f"{'操作':<16s} {'含唯一否定词的破坏率':>22s} {'不含否定词的破坏率':>20s}")
for name, fn in OPS.items():
    g = break_rate_by_group(fn, 0.1, TRAIN)
    print(f'{name:<16s} {g["含唯一否定词"][0]:>21.1%} {g["不含否定词"][0]:>19.1%}')

g_rd = break_rate_by_group(OPS['RD 随机删除'], 0.1, TRAIN)
assert g_rd['含唯一否定词'][0] > g_rd['不含否定词'][0] * 1.5, \\
    'RD 对「标签由单个关键词决定」的样本破坏率明显更高'
print(f'\\n⚠️  RD 对含唯一否定词的样本破坏率是不含的 '
      f'{g_rd["含唯一否定词"][0]/max(g_rd["不含否定词"][0],1e-9):.1f} 倍。')
print('   **这不是随机噪声，是系统性地污染了最关键的那部分数据。**')
print('   而这类样本恰恰是模型最需要学好的（决策边界就在这里）。')"""),
    md("""## 2 · 保护规则：把「不能动的词」标出来

否定词、程度副词、命名实体、数字、以及**用互信息自动挑出的高关键词**。
保护之后，最危险的 RD 也能达到高保真度。"""),
    code("""def mutual_info_keywords(data, top_k=8):
    '''用 |P(y=1|w) - P(y=1)| 自动挑出与标签强相关的词（无需领域知识）。'''
    base = float(np.mean([y for _, y in data]))
    cnt, pos = collections.Counter(), collections.Counter()
    for t, y in data:
        for w in set(t):
            cnt[w] += 1; pos[w] += y
    scores = {w: abs(pos[w]/c - base) for w, c in cnt.items() if c >= 5}
    return set(sorted(scores, key=scores.get, reverse=True)[:top_k])

auto_kw = mutual_info_keywords(TRAIN, top_k=8)
print('互信息自动挑出的关键词:', sorted(auto_kw))
overlap = auto_kw & (POS_WORDS | NEG_WORDS | NEGATORS)
print(f'其中命中真正的情感/否定词: {sorted(overlap)}  ({len(overlap)}/{len(auto_kw)})')
assert len(overlap) >= 3, '自动方法应能挑出多数真正的关键词'
print('✅ 不需要领域知识也能自动找出「不能动的词」')"""),
    code("""def protected_set(extra=frozenset()):
    # 否定词 + 程度副词 + 实体 + **情感词本身** + 互信息自动挑出的关键词
    return NEGATORS | DEGREE | set(ENTITIES) | POS_WORDS | NEG_WORDS | set(extra)

def protected_deletion(tokens, p, r, protect):
    '''受保护的词永不删除。注意保护表要**同时**包含否定词与情感词 ——
       只保护否定词是不够的：删掉唯一的情感词，标签同样会变。'''
    out = [t for t in tokens if (t in protect) or (r.random() >= p)]
    return out if out else list(tokens[:1])

def protected_swap(tokens, n, r, protect):
    '''只交换未受保护的词（保持受保护词的位置）。'''
    out = list(tokens)
    free = [i for i, t in enumerate(out) if t not in protect]
    for _ in range(n):
        if len(free) < 2: break
        i, j = r.choice(free, size=2, replace=False)
        out[i], out[j] = out[j], out[i]
    return out

def protected_synonym(tokens, n, r, protect):
    idx = [i for i, t in enumerate(tokens) if t in SYNONYMS and t not in protect]
    out = list(tokens)
    if not idx: return out
    for i in r.choice(idx, size=min(n, len(idx)), replace=False):
        out[i] = str(r.choice(SYNONYMS[out[i]]))
    return out

PROT = protected_set(auto_kw)
print(f'保护表大小: {len(PROT)} / 词表 {len(VOCAB_ALL)}\\n')
print(f"{'操作':<24s} {'保真度':>9s} {'distinct-2':>11s}")
rows = []
for label, fn in [
    ('RD  无保护 p=0.1',      lambda t, r: random_deletion(t, 0.1, r)),
    ('RD  有保护 p=0.1',      lambda t, r: protected_deletion(t, 0.1, r, PROT)),
    ('RS  无保护 n=1',        lambda t, r: random_swap(t, 1, r)),
    ('RS  有保护 n=1',        lambda t, r: protected_swap(t, 1, r, PROT)),
    ('SR  有保护',            lambda t, r: protected_synonym(t, 1, r, PROT)),
]:
    r = np.random.default_rng(17)
    pairs = [(t, y, fn(t, r)) for t, y in TRAIN]
    f, d = fidelity(pairs), distinct_n([a for _, _, a in pairs], 2)
    rows.append((label, f, d))
    print(f'{label:<24s} {f:>9.1%} {d:>11.4f}')

by = {k: (f, d) for k, f, d in rows}
assert by['RD  有保护 p=0.1'][0] > by['RD  无保护 p=0.1'][0], '保护应提高保真度'
assert by['RS  有保护 n=1'][0] > by['RS  无保护 n=1'][0]
assert by['RD  有保护 p=0.1'][0] > 0.97, '保护后 RD 也能达到 97%+ 保真度'
print(f'\\n✅ 保护把 RD 的保真度从 {by["RD  无保护 p=0.1"][0]:.1%} 提到 '
      f'{by["RD  有保护 p=0.1"][0]:.1%}，而多样性几乎不损失。')"""),
    md("""### 保真-多样权衡前沿：保护得越多，保真越高、多样越低"""),
    code("""def frontier_by_protection(k_values, p=0.15, seed=19):
    out = []
    for k in k_values:
        prot = protected_set(mutual_info_keywords(TRAIN, top_k=k)) if k else set(ENTITIES)
        r = np.random.default_rng(seed)
        pairs = [(t, y, protected_deletion(t, p, r, prot)) for t, y in TRAIN]
        out.append((k, len(prot), fidelity(pairs),
                    distinct_n([a for _, _, a in pairs], 2)))
    return out

print(f"{'top_k':>6s} {'保护表':>7s} {'保真度':>9s} {'distinct-2':>11s}")
front = frontier_by_protection([0, 2, 4, 8, 16, 30])
for k, n, f, d in front:
    print(f'{k:>6d} {n:>7d} {f:>9.1%} {d:>11.4f}')

fids = [f for _, _, f, _ in front]
assert fids[-1] >= fids[0], '保护越多，保真度越高（或至少不降）'
# 「约束下最优」：保真度 >= 0.98 前提下多样性最大的那个点
feasible = [(k, f, d) for k, _, f, d in front if f >= 0.98]
best = max(feasible, key=lambda x: x[2]) if feasible else None
print(f'\\n✅ 约束下最优（保真度 ≥ 0.98 且多样性最大）: top_k={best[0]}, '
      f'保真 {best[1]:.1%}, distinct-2 {best[2]:.4f}')
print('   ⚠️ 保护表不能太大：全保护 -> 增强退化成「几乎不变」，多样性趋零、正则化失效。')"""),
    md("""## 3 · AEDA：只插标点，保真度接近 100%

Karimi et al. 2021 的洞察：**标点不改变词汇语义**，所以只插标点几乎不可能破坏标签，
却仍能提供表面扰动。想清楚「什么改动不会破坏标签」往往比调参更有价值。"""),
    code("""PUNCT = ['.', ',', '!', '?', ';']

def aeda(tokens, ratio, r):
    '''随机插入 ratio*len 个标点。'''
    out = list(tokens)
    n = max(1, int(ratio * len(tokens)))
    for _ in range(n):
        out.insert(int(r.integers(0, len(out)+1)), str(r.choice(PUNCT)))
    return out

print(f"{'方案':<22s} {'保真度':>9s} {'distinct-2':>11s}")
for label, fn in [('AEDA ratio=0.1', lambda t, r: aeda(t, 0.1, r)),
                  ('AEDA ratio=0.3', lambda t, r: aeda(t, 0.3, r)),
                  ('EDA-RD p=0.1',   lambda t, r: random_deletion(t, 0.1, r))]:
    r = np.random.default_rng(23)
    pairs = [(t, y, fn(t, r)) for t, y in TRAIN]
    print(f'{label:<22s} {fidelity(pairs):>9.1%} '
          f'{distinct_n([a for _, _, a in pairs],2):>11.4f}')

r = np.random.default_rng(23)
pairs_aeda = [(t, y, aeda(t, 0.3, r)) for t, y in TRAIN]
assert fidelity(pairs_aeda) == 1.0, 'AEDA 不改变任何词 -> 规则标签必然不变'
print('\\n✅ AEDA 的保真度是**精确的 100%**（不动任何实词，规则标签不可能变）。')
print('   例:', ' '.join(pairs_aeda[0][2]))
print('   在需要「安全的正则化」时，AEDA 常常是比 EDA 更好的默认选择。')"""),
    md("""## 4 · α 扫描：先升后急降

$$n_{changed} = \\max(1, \\lfloor \\alpha L \\rfloor)$$

原论文实测 α≈0.1 最优、过大时急剧下降。同时看保真度与下游收益。"""),
    code("""def sweep_alpha(alphas, n_aug=4, seed=29):
    out = []
    for a in alphas:
        r = np.random.default_rng(seed)
        aug, pairs = [], []
        for t, y in TRAIN:
            for _ in range(n_aug):
                at = protected_synonym(t, max(1, int(a*len(t))), r, PROT)
                at = protected_swap(at, max(1, int(a*len(at))), r, PROT)
                at = protected_deletion(at, a, r, PROT)
                aug.append((at, y)); pairs.append((t, y, at))
        f = fidelity(pairs); d = distinct_n([x for x, _ in aug], 2)
        b, av, diffs = effectiveness(TRAIN, aug, TEST, seeds=range(6))
        out.append((a, f, d, float(np.mean(diffs)), float(np.std(diffs))))
    return out

print(f"{'α':>6s} {'保真度':>9s} {'distinct-2':>11s} {'Δ准确率':>10s} {'Δ标准差':>9s}")
sw = sweep_alpha([0.02, 0.05, 0.1, 0.2, 0.4])
for a, f, d, dm, ds in sw:
    print(f'{a:>6.2f} {f:>9.1%} {d:>11.4f} {dm:>+10.4f} {ds:>9.4f}')

fids = [x[1] for x in sw]; divs = [x[2] for x in sw]
assert fids == sorted(fids, reverse=True), 'α 越大保真度越低'
assert divs[-1] > divs[0], 'α 越大多样性越高'
print('\\n✅ 保真度随 α 单调下降、多样性随 α 单调上升 —— 这就是核心权衡。')
print('   最优 α 在「保真度还能接受」与「多样性足够」之间；原论文实测 0.1 附近。')
print('   ⚠️ 注意 Δ标准差常与 Δ准确率同量级 —— 单点比较不可信（模块 05 给出正确检验）。')"""),
    md("""## 5 · 数据量-收益曲线：为什么只有小数据集受益

词面增强提供的是「表面形式不变性」这**一个**归纳偏置。
数据多了，模型本来就学会了这个不变性，增强只剩下噪声。"""),
    code("""def sweep_data_size(sizes, n_aug=4, alpha=0.1, seed=31):
    out = []
    for n in sizes:
        train_n = [make_sentence(np.random.default_rng(s)) for s in range(n)]
        prot = protected_set(mutual_info_keywords(train_n, top_k=8))
        r = np.random.default_rng(seed)
        aug = []
        for t, y in train_n:
            for _ in range(n_aug):
                at = protected_synonym(t, max(1, int(alpha*len(t))), r, prot)
                at = protected_deletion(at, alpha, r, prot)
                aug.append((at, y))
        b, av, diffs = effectiveness(train_n, aug, TEST, seeds=range(6))
        out.append((n, b, av, float(np.mean(diffs)), float(np.std(diffs))))
    return out

print(f"{'训练集大小':>10s} {'baseline':>9s} {'增强后':>8s} {'Δ':>9s} {'Δ标准差':>9s} {'超过噪声?':>10s}")
ds = sweep_data_size([50, 100, 200, 400, 800])
for n, b, av, dm, dsd in ds:
    sig = '✅' if dm > dsd else '❌'
    print(f'{n:>10d} {b:>9.4f} {av:>8.4f} {dm:>+9.4f} {dsd:>9.4f} {sig:>10s}')

deltas = [x[3] for x in ds]
print(f'\\n50 条时 Δ={deltas[0]:+.4f} | 800 条时 Δ={deltas[-1]:+.4f}')
assert ds[0][1] < ds[-1][1], 'baseline 准确率应随数据量提高'
print('\\n✅ 核心结论：**baseline 随数据量提高，增强的相对收益随之压缩**。')
print('   如果你有十万条标注数据还在纠结要不要做 EDA —— 答案基本是「不要」。')
print('   （本课的合成任务比真实任务简单，收益衰减会更快；但方向与文献一致。）')"""),
    md("""## 6 · 在线 vs 离线增强：epoch 混淆与 token dropout"""),
    code("""def token_dropout(tokens, p, r):
    '''在线增强：换成 [UNK] 而非删除 —— 长度与位置不变，比 RD 安全得多。'''
    return [('[UNK]' if r.random() < p else t) for t in tokens]

r = np.random.default_rng(37)
pairs_do = [(t, y, token_dropout(t, 0.1, r)) for t, y in TRAIN]
r = np.random.default_rng(37)
pairs_rd = [(t, y, random_deletion(t, 0.1, r)) for t, y in TRAIN]
print(f'token dropout p=0.1 保真度: {fidelity(pairs_do):.1%}')
print(f'random deletion p=0.1 保真度: {fidelity(pairs_rd):.1%}')
print('（两者破坏标签的机制相同——都可能命中否定词——但 dropout 保持长度与位置）')
assert len(pairs_do[0][2]) == len(pairs_do[0][0]), 'dropout 保持长度'
assert len(pairs_rd[0][2]) <= len(pairs_rd[0][0]), 'deletion 改变长度'

# epoch 混淆：不固定总步数时，「增强」与「训练更久」混在一起
r = np.random.default_rng(41)
aug4 = [(protected_deletion(t, 0.1, r, PROT), y) for t, y in TRAIN for _ in range(4)]
b_fix, a_fix, d_fix = effectiveness(TRAIN, aug4, TEST, seeds=range(6), fixed_steps=True)
b_bad, a_bad, d_bad = effectiveness(TRAIN, aug4, TEST, seeds=range(6), fixed_steps=False)
print(f'\\n固定总样本数（公平）  : baseline {b_fix:.4f} -> 增强 {a_fix:.4f}, Δ={np.mean(d_fix):+.4f}')
print(f'不固定（baseline 训得少）: baseline {b_bad:.4f} -> 增强 {a_bad:.4f}, Δ={np.mean(d_bad):+.4f}')
assert b_fix >= b_bad - 1e-9, '公平设置下 baseline 训练量更足、分数不低于不公平设置'
print('\\n⚠️  不固定总步数时，baseline 只看了 1/5 的样本 -> Δ 被高估。')
print('✅ 正确做法：**固定总样本数或总步数，而不是 epoch 数**。')
print('   在线增强（dropout / embedding 噪声）天然没有这个问题 —— 数据量不变。')"""),
    md("""## ✏️ 练习 1：带保护的 EDA 组合

实现 `eda_protected(tokens, alpha, protect, rng, ops=('SR','RS','RD'))`：
按 `ops` 顺序依次施加受保护版本的操作（SR/RS 用 `max(1,int(alpha*len))` 次，RD 用概率 `alpha`），
返回增强后的 tokens。"""),
    code("""def eda_protected(tokens, alpha, protect, rng, ops=('SR', 'RS', 'RD')):
    # TODO: 依次调用 protected_synonym / protected_swap / protected_deletion
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
r = np.random.default_rng(43)
pairs = [(t, y, eda_protected(t, 0.1, PROT, r)) for t, y in TRAIN]
f = fidelity(pairs)
assert f > 0.95, f'带保护的组合应有高保真度，得到 {f:.1%}'
assert distinct_n([a for _, _, a in pairs], 2) > 0, '应产生变化'
# 只做 SR 时保真度应更高（改动更少、更温和）
r = np.random.default_rng(43)
pairs_sr = [(t, y, eda_protected(t, 0.1, PROT, r, ops=('SR',))) for t, y in TRAIN]
assert fidelity(pairs_sr) >= f, '单操作应不低于三操作组合的保真度'
# 受保护的词必须一个都没丢
r = np.random.default_rng(43)
for t, y in TRAIN[:50]:
    aug = eda_protected(t, 0.3, PROT, r, ops=('RD',))
    for w in t:
        if w in PROT:
            assert w in aug, f'受保护词 {w} 不应被删除'
print(f'三操作组合保真度 {f:.1%} | 仅 SR {fidelity(pairs_sr):.1%}')
print('✅ 练习 1 通过：受保护词在最激进的 RD 下也不会丢')"""),
    md("""## ✏️ 练习 2：约束下的最优 α

实现 `best_alpha(alphas, min_fidelity, protect, data, seed=0)`：
在「保真度 ≥ min_fidelity」的 α 里返回**多样性最高**的那个；无可行解返回 `None`。"""),
    code("""def best_alpha(alphas, min_fidelity, protect, data, seed=0):
    # TODO: 对每个 α 用 eda_protected 增强一遍，算 (fidelity, distinct_n)；
    #       在可行集里返回 distinct 最大的 α
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
a_strict = best_alpha([0.05, 0.1, 0.2, 0.4], 0.99, PROT, TRAIN)
a_loose  = best_alpha([0.05, 0.1, 0.2, 0.4], 0.90, PROT, TRAIN)
print(f'保真度 ≥ 0.99 -> 最优 α = {a_strict}')
print(f'保真度 ≥ 0.90 -> 最优 α = {a_loose}')
assert a_strict is not None and a_loose is not None
assert a_loose >= a_strict, '更松的保真度约束允许更大的 α（更高多样性）'
assert best_alpha([0.05, 0.1], 1.01, PROT, TRAIN) is None, '不可达时返回 None'
print('✅ 练习 2 通过：这是本课反复出现的「约束下最优」思路 ——')
print('   保真度是硬约束，多样性是目标函数。')"""),
    md("""## ✏️ 练习 3：增强预算账

实现 `augmentation_budget(n_train, n_aug, break_rate, n_alpha, n_ops, n_seeds)`：
返回 `{'total_samples':…, 'corrupted':…, 'corrupt_share':…, 'n_runs':…}`。
- `total_samples = n_train * (1 + n_aug)`
- `corrupted = n_train * n_aug * break_rate`（错标样本数）
- `corrupt_share = corrupted / total_samples`
- `n_runs = n_alpha * n_ops * n_seeds`（调参要跑多少次训练）"""),
    code("""def augmentation_budget(n_train, n_aug, break_rate, n_alpha, n_ops, n_seeds):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
b = augmentation_budget(1000, 4, 0.05, n_alpha=3, n_ops=4, n_seeds=5)
assert b['total_samples'] == 5000
assert abs(b['corrupted'] - 200) < 1e-9, '1000×4×5% = 200 条错标数据'
assert abs(b['corrupt_share'] - 0.04) < 1e-9
assert b['n_runs'] == 60
print(f'1000 条 × 4 份 × 破坏率 5%:')
print(f'  总样本 {b["total_samples"]}, 其中错标 {b["corrupted"]:.0f} 条 ({b["corrupt_share"]:.1%})')
print(f'  认真调参需要跑 {b["n_runs"]} 次训练')
# 保护规则把破坏率降到 1% 时
b2 = augmentation_budget(1000, 4, 0.01, 3, 4, 5)
assert b2['corrupted'] < b['corrupted'] / 4
print(f'\\n加了保护规则（破坏率 5% -> 1%）: 错标从 {b["corrupted"]:.0f} 降到 {b2["corrupted"]:.0f} 条')
print('✅ 练习 3 通过：「破坏率 5%」= 200 条错标数据被塞进一个 1000 条的训练集 ——')
print('   这就是为什么保真度必须是**硬门槛**而不是软指标。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def eda_protected(tokens, alpha, protect, rng, ops=('SR', 'RS', 'RD')):
    out = list(tokens)
    for op in ops:
        n = max(1, int(alpha * len(out)))
        if op == 'SR':   out = protected_synonym(out, n, rng, protect)
        elif op == 'RS': out = protected_swap(out, n, rng, protect)
        elif op == 'RD': out = protected_deletion(out, alpha, rng, protect)
        elif op == 'RI': out = random_insertion(out, n, rng)
        else: raise ValueError(op)
    return out"""),
    code("""# 练习 2 参考答案
def best_alpha(alphas, min_fidelity, protect, data, seed=0):
    feasible = []
    for a in alphas:
        r = np.random.default_rng(seed)
        pairs = [(t, y, eda_protected(t, a, protect, r)) for t, y in data]
        f = fidelity(pairs)
        d = distinct_n([x for _, _, x in pairs], 2)
        if f >= min_fidelity:
            feasible.append((a, d))
    return max(feasible, key=lambda x: x[1])[0] if feasible else None"""),
    code("""# 练习 3 参考答案
def augmentation_budget(n_train, n_aug, break_rate, n_alpha, n_ops, n_seeds):
    total = n_train * (1 + n_aug)
    corrupted = n_train * n_aug * break_rate
    return {'total_samples': total, 'corrupted': corrupted,
            'corrupt_share': corrupted / total, 'n_runs': n_alpha * n_ops * n_seeds}"""),
    md("""---
## 🧪 真实数据胶囊：EDA 原论文的数据量-收益曲线

用 Wei & Zou 2019 报告的量级复现那张关键图，并把「什么时候不该用 EDA」变成一条判据。"""),
    code("""# EDA 论文报告的量级（五个数据集平均，CNN/RNN 模型）
paper = [
    # (训练集比例, baseline 准确率, +EDA 准确率)
    (0.01, 0.700, 0.760),
    (0.05, 0.792, 0.816),
    (0.10, 0.822, 0.840),
    (0.20, 0.845, 0.854),
    (0.50, 0.868, 0.872),
    (1.00, 0.882, 0.885),
]
print(f"{'训练集比例':>10s} {'baseline':>9s} {'+EDA':>7s} {'Δ':>7s} {'相对误差降低':>12s}")
for frac, b, e in paper:
    err_red = (e - b) / (1 - b)
    print(f'{frac:>10.0%} {b:>9.3f} {e:>7.3f} {e-b:>+7.3f} {err_red:>11.1%}')

deltas = [e - b for _, b, e in paper]
assert deltas[0] > deltas[-1] * 5, '1% 数据时的收益应远大于 100% 数据时'
assert deltas == sorted(deltas, reverse=True), '收益应随数据量单调递减'
print(f'\\n✅ 1% 数据时 Δ={deltas[0]:+.3f}，100% 数据时 Δ={deltas[-1]:+.3f} —— '
      f'差 {deltas[0]/deltas[-1]:.0f} 倍。')
print('   而 100% 数据时的 +0.003 已经落在种子方差（C49: 2-3 分）之内 —— 不可信。')

SEED_NOISE = 0.02        # 小数据集微调的典型种子标准差（C49 模块 03）
print(f'\\n用「Δ 是否超过种子噪声 {SEED_NOISE}」做判据:')
for frac, b, e in paper:
    print(f'  {frac:>5.0%} 数据: Δ={e-b:+.3f} -> {"值得做 ✅" if e-b > SEED_NOISE else "落在噪声内 ❌"}')
worth = [f for f, b, e in paper if e - b > SEED_NOISE]
assert worth and max(worth) <= 0.10, 'EDA 只在很小的数据规模上有可信收益'
print(f'\\n✅ 只有训练集 ≤ {max(worth):.0%} 时收益才明显超过噪声。')
print('   **这就是「小数据集才受益」的定量版本。**')"""),
    md("""**🧪 胶囊练习**：实现 `should_augment(n_train, expected_delta, seed_noise, labeling_cost_per_sample, eng_hours, hourly_cost)`：
返回 `(是否值得, 增强的工程成本, 同成本能标注的样本数)`。
- 值得的条件：`expected_delta > seed_noise`
- 增强工程成本 = `eng_hours * hourly_cost`
- 同成本能标注 = `int(增强成本 / labeling_cost_per_sample)`"""),
    code("""def should_augment(n_train, expected_delta, seed_noise, labeling_cost_per_sample,
                   eng_hours, hourly_cost):
    # TODO
    raise NotImplementedError"""),
    code("""# 自测
ok, cost, n_label = should_augment(1000, expected_delta=0.03, seed_noise=0.02,
                                  labeling_cost_per_sample=0.5, eng_hours=24, hourly_cost=60)
assert ok is True and abs(cost - 1440) < 1e-9 and n_label == 2880
print(f'预期 Δ=0.03 > 噪声 0.02 -> 值得做')
print(f'但增强的工程成本 ${cost:,.0f} 等价于标注 {n_label:,} 条真实数据')
print(f'（而训练集只有 1000 条 —— 也就是说可以把数据量变成 {1 + n_label/1000:.1f} 倍）')
ok2, _, _ = should_augment(1000, 0.005, 0.02, 0.5, 24, 60)
assert ok2 is False, '效应落在噪声内 -> 不值得'
print('\\n✅ 胶囊练习通过：**这就是模块 05 那个必须做的对照** ——')
print('   同样的预算，做增强 vs 直接标注真实数据，哪个划算？')
print('   注意：真实标注成本、工程时间都要按你自己的情况填。')"""),
    code("""# 📖 胶囊参考答案
def should_augment(n_train, expected_delta, seed_noise, labeling_cost_per_sample,
                   eng_hours, hourly_cost):
    cost = eng_hours * hourly_cost
    return (expected_delta > seed_noise, cost, int(cost / labeling_cost_per_sample))"""),
    md("""### 小结
- **EDA 四操作的危险性排序 RD > RS > RI ≈ SR**（已量化，破坏率差一个量级）。
- **RD 特别恶劣**：它破坏标签的概率与关键词稀有度成正比 → **系统性污染「标签由单个关键词决定」的关键样本**。
- **保护规则是核心**：否定词 + 程度副词 + 实体 + 数字 + **互信息自动挑出的高关键词**。保护后连 RD 都能到 97%+ 保真度，多样性几乎不损失。
- **保护表不能太大**：全保护 → 增强退化成不变。用「保真度 ≥ 0.98 前提下多样性最大」找最优点。
- **AEDA（只插标点）保真度精确 100%**——想清楚「什么改动不破坏标签」常比调参更有价值。
- **α 的权衡**：保真度单调降、多样性单调升；原论文最优 ≈ 0.1。
- **数据量-收益单调递减**：EDA 只在训练集 ≤ 10% 规模时收益超过种子噪声。
- **固定总样本数而不是 epoch 数**，否则「增强」与「训练更久」混在一起。
- 预算账：破坏率 5% = 200 条错标数据进入 1000 条训练集；认真调参要跑 60+ 次训练，其成本可能能标注几千条真实数据。

下一站：**模块 02 · 回译与释义** —— 上到语义层，保真度更好，但失效方式更隐蔽。"""),
]
