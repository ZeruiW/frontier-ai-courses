# -*- coding: utf-8 -*-
"""C51 模块 02 · 回译与释义。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–01；C49 模块 04（seq2seq 与 beam search）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_backtranslation.ipynb'),
    ("核心论文", "Sennrich et al. 2016（回译用于 NMT）★、Edunov et al. 2018（采样回译）★、Xie et al. 2020（UDA 用回译做一致性训练）"),
    ("预计时长", "读 55 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("bt", "回译：用两次翻译换一个新说法", "".join([
        P("<span class=\"term\">back-translation</span>（回译）是语义层增强的代表：<strong>把句子翻译到另一种语言，再翻回来</strong>。得到的句子通常语义相同、措辞不同。"),
        ASCII("""原文 (zh):  这家店的菜非常好吃，服务也不错。
      │
      │  正向翻译 (zh -> en)
      ▼
中间 (en):  The food at this restaurant is delicious, and the service is good.
      │
      │  反向翻译 (en -> zh)
      ▼
回译 (zh):  这家餐厅的食物很美味，服务也很好。      ← 语义相同、措辞全变

为什么能保语义？因为「翻译」这个任务本身的训练目标就是**保持语义**。
为什么措辞会变？因为翻译不是双射——en 的一个句子可以对应多个 zh 表达，
反向模型只是选了其中一个（且解码策略决定选哪个）。""")
        ,
        DUAL(
            "回译相对词面增强的最大优势是<strong>它在「语义空间」而不是「词面空间」操作</strong>。EDA 删掉一个「不」字不会有任何机制阻止它；而翻译模型如果丢掉了否定，正向翻译的 loss 就会很高——<em>「保语义」这个约束是内建在模型里的</em>。所以回译的标签保真度通常比 EDA 高一个档次。",
            "但它的失效方式更<strong>隐蔽</strong>。EDA 破坏标签时你能一眼看出来（句子变得不通顺）；<em>回译产出的句子总是通顺的</em>，即使语义已经漂移。「这家店不太干净」回译成「这家店比较干净」——句子完美，标签反了，而且你不看原文根本发现不了。<strong>通顺性给了它一种虚假的可信度</strong>，这是回译最需要防的一点。所以回译<em>更需要</em>自动的保真度检验（本模块第四节）。",
        ),
        CALLOUT("warn", "回译的第二个代价是<strong>成本</strong>。它需要两次 seq2seq 推理，对每条样本、每个增强副本都要跑一遍。1000 条样本 × 4 个副本 × 2 次翻译 = 8000 次生成。<em>这已经不是「几乎零成本」了</em>——它与「用 LLM 直接改写」的成本进入同一量级（模块 03），而后者可控性更强。所以现实的选择常常是：<strong>要么用便宜的词面增强，要么直接上 LLM；回译处在一个不太经济的中间地带</strong>——除非你恰好有现成的高质量翻译模型且不想调 LLM。"),
    ])),
    ("diversity", "多样性从哪来：解码策略比中间语言更重要", "".join([
        P("一个常见误解是「换中间语言就能增加多样性」。实际上<strong>多样性的主要来源是反向翻译的解码策略</strong>。"),
        TABLE(["多样性来源", "怎么控制", "效果", "代价"], [
            ["<strong>解码策略</strong>", "beam search → 采样（<code>do_sample=True</code>、<code>top_p</code>、温度）", "<strong>最主要</strong>：同一中间句能产出多个不同回译", "温度过高会语义漂移"],
            ["<strong>中间语言（枢轴）</strong>", "zh→en→zh vs zh→de→zh vs zh→ja→zh", "中等：不同语言的表达约束不同", "需要多个翻译模型；小语种质量差"],
            ["<strong>多跳</strong>", "zh→en→de→zh", "较高，但<strong>误差累积</strong>", "每跳都可能丢语义，保真度快速下降"],
            ["<strong>beam 里取第 k 名</strong>", "取 beam 的 top-k 而非 top-1", "低（beam 的候选彼此很像）", "几乎免费"],
        ]),
        DUAL(
            "Edunov et al. 2018 在 NMT 的合成数据场景里给出了一个重要发现：<strong>用采样（或加噪的 beam）做回译，比用纯 beam search 更有效</strong>。原因是 beam search 倾向于产出「最安全」的翻译——所有回译结果都很像，多样性极低，模型学不到新东西。<em>采样引入了多样性，代价是引入了噪声，而在合成数据的场景里这个交易是划算的</em>（因为原文的标签仍然由原始样本给定）。",
            "但注意这个结论<strong>不能直接搬到分类任务的增强上</strong>。在 NMT 里，回译产生的是「合成的源句 + 真实的目标句」，噪声主要影响源侧、而目标侧仍然是干净的人类文本。<em>在分类增强里，回译产生的是「新的输入 + 沿用的旧标签」——一旦语义漂移，标签就错了</em>。所以分类增强应该用<strong>更保守的采样温度</strong>（比 NMT 场景低），并且必须配保真度检验。这是同一个技术在两个任务上取舍不同的好例子。",
        ),
        CALLOUT("intuition", "关于中间语言的选择有一条实用经验：<strong>语言距离越远，回译的措辞变化越大、语义漂移风险也越大</strong>。zh→en→zh 相对稳（英语资源最好、翻译质量最高）；zh→ja→zh 变化中等；zh→某个低资源语言→zh 则变化剧烈但常常已经漂了。<em>先用 en 做枢轴，只有在多样性明显不足时才引入第二个枢轴语言</em>——而且要为每个枢轴单独测保真度，别假设它们一样安全。"),
    ])),
    ("failure", "回译什么时候会毁掉标签：四类高危场景", "".join([
        TABLE(["高危场景", "例子", "为什么危险"], [
            ["<strong>否定与双重否定</strong>", "「不是不好吃」→「还不错」（强度变了）；「没什么问题」→「有问题」（极性翻了）", "翻译模型对否定的处理本就是已知弱点，尤其中英之间否定结构差异大"],
            ["<strong>程度与情感强度</strong>", "「还行」→「很好」；「有点贵」→「太贵了」", "细粒度情感/评分任务上直接改标签；二分类任务上可能还能忍"],
            ["<strong>专业术语与实体</strong>", "「Transformer」→「变压器」→「transformer」（领域错了）；药名、型号、法条", "翻译模型没有领域约束，会按通用语义翻"],
            ["<strong>数字、时间、单位</strong>", "「3 天内」→「within three days」→「三日内」（还行）；但「30%」→「三成」→「30 percent」可能丢精度", "数值型信息抽取任务会直接错"],
        ]),
        P("这四类的共同点是：<strong>它们都是「标签由局部的、语义敏感的片段决定」的情形</strong>。这和模块 01 的结论呼应——<em>无论哪种增强，最危险的都是「标签由少数关键成分决定」的样本</em>。所以模块 01 的保护思路在这里同样适用，只是实现方式不同："),
        UL([
            "<strong>约束解码</strong>：让回译时某些词必须出现（<code>force_words_ids</code>，C50 模块 01 提到过）。可以保护实体与数字。",
            "<strong>占位符替换</strong>：翻译前把实体/数字替换成 <code>&lt;ENT_0&gt;</code>、<code>&lt;NUM_1&gt;</code> 这类占位符，翻译后再换回。<em>这是工业界处理这个问题的标准做法</em>，简单且有效。",
            "<strong>事后过滤</strong>：回译后检查关键成分是否还在（否定词数量、实体、数字），不通过就丢弃这个副本。<strong>丢弃比修正更可靠</strong>。",
        ]),
        CALLOUT("danger", "<p>特别提醒<strong>否定的处理</strong>，因为它是回译最容易翻车的地方且后果最严重。一个可操作的检查是：<em>比较原文与回译的「否定词计数的奇偶性」</em>——如果原文有 1 个否定词、回译有 0 个或 2 个，极性很可能变了，直接丢弃。这个检查极其粗糙，但它能挡住大部分致命案例，而成本几乎为零。<strong>notebook 会实现它并量化它挡住了多少破坏。</strong>「粗糙但零成本的过滤器」在数据管线里往往比「精细但昂贵的修正器」更值得先做。</p>", "否定的奇偶性检查"),
    ])),
    ("check", "自动保真度检验：三个廉价判据", "".join([
        P("既然回译产出的句子总是通顺、无法靠「读起来对不对」判断，就必须有自动判据。三个从便宜到贵的层次："),
        TABLE(["判据", "怎么算", "能抓什么", "成本"], [
            ["<strong>① 关键成分一致性</strong>", "否定词计数、实体集合、数字集合、单位是否保持", "极性翻转、实体错译、数值失真", "<strong>几乎零</strong>"],
            ["<strong>② round-trip 相似度</strong>", "原文与回译的 token 重叠（如 BLEU / chrF / Jaccard）", "语义大幅漂移（相似度过低）与<em>无效增强</em>（相似度过高=没变化）", "低"],
            ["<strong>③ 模型一致性</strong>", "用一个已训练的分类器给原文与回译打分，看预测是否一致", "微妙的语义漂移", "中（需要一个模型）"],
        ]),
        DUAL(
            "判据 ② 有一个反直觉的用法：<strong>它是「双边」过滤器而不是「单边」的</strong>。相似度太低说明语义漂了（要丢），但相似度<em>太高</em>也要丢——因为那意味着回译几乎等于原文，这个副本没有提供任何新信息，只是把数据复制了一遍（还浪费了两次翻译的算力）。<em>所以正确的做法是保留相似度落在一个中间带（如 Jaccard ∈ [0.3, 0.85]）的副本</em>。",
            "判据 ③ 有个链式依赖问题要注意：<strong>你需要一个分类器来筛选增强数据，而这个分类器是用未增强的数据训的</strong>。这引入了一个偏差——被保留的增强样本会偏向「当前模型已经能正确分类的」，也就是<em>信息量较低的那些</em>。这在自训练/伪标签里是个已知问题（confirmation bias）。缓解办法是只用它做「明显不一致」的硬过滤（如两边预测相反且都很自信），而不是按置信度排序取 top-k。",
        ),
        CALLOUT("intuition", "把三个判据组合成一条流水线，顺序很重要：<strong>先跑最便宜的、能挡住最严重问题的</strong>。① 关键成分（挡致命错误，零成本）→ ② 相似度双边带（挡漂移与无效副本，低成本）→ ③ 模型一致性（可选，挡微妙漂移）。<em>这个「先便宜后贵」的多阶段过滤节奏，和 C43 模块 04 的大规模质量过滤是同一个模式</em>——在任何数据管线里都成立。"),
    ])),
    ("paraphrase", "释义模型：回译的更直接替代", "".join([
        P("回译是「用两次翻译间接实现释义」。既然目标是释义，为什么不直接用<strong>释义模型</strong>（paraphrase model）？"),
        TABLE(["", "回译", "专门的释义模型", "LLM 改写（模块 03）"], [
            ["推理次数", "2 次", "<strong>1 次</strong>", "1 次"],
            ["可控性", "低（只能调解码）", "中（可训练成特定风格）", "<strong>高</strong>（prompt 里直接约束）"],
            ["保语义", "✅ 内建（翻译目标）", "✅ 内建（训练目标就是释义）", "🔶 靠 prompt 约束，可能不遵守"],
            ["多样性", "中（靠采样）", "中", "<strong>高</strong>（可以要求「换一种更正式的说法」）"],
            ["模型可得性", "翻译模型很多、质量高", "专门的释义模型较少、质量参差", "任何指令模型都能做"],
            ["成本", "2× 生成", "1× 生成", "1× LLM 调用（更贵但更少次数）"],
        ]),
        P("从这张表可以看出<strong>技术路线的历史演变</strong>：回译在 2016–2020 年是主流，因为当时高质量翻译模型远比高质量释义/指令模型容易得到。<em>而今天，「让 LLM 换一种说法」在可控性、多样性、实现简单度上全面胜出</em>——你可以直接要求「保持情感不变、换成更口语的说法、不要改变任何数字」，这些约束在回译里根本无法表达。"),
        CALLOUT("intuition", "所以本模块的一个诚实结论是：<strong>如果你今天有 LLM 可用，回译在大多数场景下已经不是最优选择</strong>。它仍然值得学，因为①它的思想（在语义空间而非词面空间做增强）是对的且会一直有用；②它的失效模式分析（否定、实体、数字）对 LLM 改写<em>完全适用</em>；③在没有 LLM 预算、但有现成翻译模型或需要完全离线的场景里，它是可行方案。<em>把这一节当成「语义层增强的通用方法论」来学，而不是「回译这个具体技巧」。</em>"),
    ])),
    ("ledger", "算一笔账：保真-多样权衡前沿", "".join([
        P("回译的两个旋钮（<strong>采样温度</strong>与<strong>相似度过滤带</strong>）共同决定你在保真-多样平面上的位置。这是本模块要让你亲手画出的东西。"),
        MATH("\\text{保留率} = \\Pr\\big[\\text{关键成分一致} \\wedge \\text{sim} \\in [\\tau_{lo}, \\tau_{hi}]\\big]"),
        TABLE(["温度", "保真度（过滤前）", "多样性（过滤前）", "过滤后保留率", "过滤后保真度"], [
            ["0.0（贪心/beam）", "高", "<strong>很低</strong>（副本几乎相同）", "低（多数因「太像」被丢）", "高"],
            ["0.7", "中高", "中", "<strong>较高</strong>", "<strong>高</strong>"],
            ["1.3", "低", "高", "低（多数因「漂移」被丢）", "中"],
        ]),
        P("这张表的关键在最后两列：<strong>过滤把不同温度下的「过滤后保真度」拉到接近的水平，代价是保留率不同</strong>。所以温度的作用不再是「保真 vs 多样」的直接权衡，而是「<em>要生成多少候选才能得到一个可用副本</em>」——也就是成本。"),
        MATH("\\text{有效成本/副本} = \\frac{2 \\times \\text{生成成本}}{\\text{保留率}}"),
        P("这个公式让温度选择变成一个纯成本问题：<strong>选让「保留率 × 多样性」最大的那个温度</strong>。notebook 会把这条曲线扫出来。"),
        P("最后给一个与模块 01 对比的成本量级（相对 EDA=1）："),
        TABLE(["方法", "相对算力成本", "典型保真度（过滤后）", "典型多样性", "何时选"], [
            ["EDA + 保护", "1", "0.98+", "低-中", "算力受限；只需要正则化"],
            ["AEDA", "1", "1.00", "低", "要绝对安全的正则化"],
            ["回译 + 过滤", "<strong>~1000</strong>（两次 seq2seq）", "0.97+", "中", "有现成翻译模型且需离线"],
            ["LLM 改写 + 过滤", "~2000（含 API 费）", "0.95–0.99（取决于 prompt）", "<strong>高</strong>", "有 LLM 预算；需要可控性"],
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>语义层增强的可靠性不来自「生成得多好」，而来自「过滤得多严」</strong>。任何生成式增强都会产出一部分坏样本（回译会漂移、LLM 会不遵守约束），而你无法通过调生成来消除它——<em>但你可以用几乎零成本的规则过滤把它们挡掉</em>。「宽松生成 + 严格过滤」几乎总是优于「保守生成 + 不过滤」，因为前者的多样性上限更高而保真度由过滤保证。"),
    ])),
    ("uda", "另一条路：不用增强样本当训练数据，而用它做一致性约束", "".join([
        P("本模块（以及整门课）的默认框架是：<strong>增强样本 + 沿用原标签 → 加进训练集</strong>。这个框架的致命弱点已经反复出现——<em>一旦语义漂移，标签就错了</em>，所以必须投入大量精力在保真度检验上。"),
        P("但还有一条完全不同的用法，它<strong>从根上绕开了保真度问题</strong>：<span class=\"term\">一致性正则</span>（consistency training，Xie et al. 2020 的 UDA）。"),
        MATH("\\mathcal{L} = \\underbrace{\\mathcal{L}_{sup}(x_l, y_l)}_{\\text{有标注数据的常规损失}} + \\lambda \\cdot \\underbrace{\\mathrm{KL}\\big(f(x_u) \\,\\|\\, f(T(x_u))\\big)}_{\\text{无标注数据上：原样本与增强样本的预测要一致}}"),
        DUAL(
            "关键差别：<strong>第二项完全不用标签</strong>。它只要求「模型对 <code>x</code> 和 <code>T(x)</code> 给出一致的预测分布」。所以即使 <code>T</code> 偶尔改变了真实语义，你也没有<em>断言</em>一个错误的标签——你只是（错误地）要求两者一致，这个错误的代价远小于「往训练集里塞一条错标数据」。<em>而且它能吃无标注数据，这在低资源场景下是巨大的优势。</em>",
            "代价有三个。<strong>①需要无标注数据</strong>（通常不是问题——无标注文本几乎总是充足的）。<strong>②需要调 <code>λ</code> 与置信度阈值</strong>（UDA 会只在模型对 <code>x</code> 足够自信时才施加一致性约束，否则会强化错误）。<strong>③训练更复杂</strong>：每步要跑原样本与增强样本两次前向。<em>但对「有大量无标注数据 + 少量标注」的场景，它通常显著优于把增强样本当训练数据。</em>",
        ),
        TABLE(["", "增广式（本课默认框架）", "一致性正则（UDA 式）"], [
            ["增强样本的用法", "当作带标签的训练数据", "只用于「两次预测要一致」的约束"],
            ["<strong>对保真度的依赖</strong>", "<strong>高</strong>（漂移=错标）", "<strong>低</strong>（不断言标签）"],
            ["能否用无标注数据", "❌", "<strong>✅ 这是它的主战场</strong>"],
            ["实现复杂度", "低（改数据即可）", "中（改损失函数与训练循环）"],
            ["适合", "只有标注数据、增强可控", "无标注数据充足、增强不完全可靠"],
        ]),
        CALLOUT("intuition", "这条路线值得知道，因为它体现了一个更一般的设计思路：<strong>当你对某个信号的「正确性」没把握时，不要把它当成硬监督，而要把它降级成一个更弱的约束</strong>。同样的模式在别处反复出现——伪标签用置信度阈值筛（不自信就不用）、RLHF 用偏好序而非绝对分数、弱监督用多个噪声源投票。<em>「把不可靠的信号降级使用」比「努力让它变可靠」往往更划算</em>。"),
    ])),
    ("compare", "三种语义层手段的横向选择", "".join([
        P("把「换个说法」这件事的三种实现放在一起，给一个可执行的选择规则。"),
        TABLE(["维度", "回译", "释义模型", "LLM 改写"], [
            ["最少依赖", "两个方向的翻译模型", "一个释义模型", "一个指令模型（或 API）"],
            ["每副本推理次数", "2", "1", "1"],
            ["能否指定约束", "❌ 只能调解码", "🔶 需要训练成特定风格", "<strong>✅ prompt 里直接写</strong>"],
            ["保语义的机制", "翻译目标内建", "释义目标内建", "靠 prompt，<strong>可能不遵守</strong>"],
            ["失效模式", "否定/实体/数字漂移", "同左 + 释义模型质量参差", "同左 + <strong>不遵守约束</strong>、风格同质化"],
            ["离线可行", "✅", "✅", "🔶（需自建模型）"],
            ["需要的过滤", "关键成分 + 双边相似度", "同左", "同左 + <strong>约束遵守性检查</strong>"],
        ]),
        DUAL(
            "选择规则可以压缩成三句话：<strong>①能调 LLM 且量不大 → 直接 LLM 改写</strong>（可控性碾压，且能表达「保持情感、不改数字、换成更口语」这类约束）；<strong>②必须离线或量极大 → 回译</strong>（翻译模型好找、质量稳定、可自建）；<strong>③有现成的高质量释义模型 → 用它</strong>（少一次推理）。<em>注意三者的过滤流水线是共用的</em>——这就是为什么本模块花最大篇幅讲过滤而不是讲生成。",
            "还有一个跨越三者的实用建议：<strong>不要只用一种</strong>。不同手段的失效模式不同（回译容易丢否定、LLM 容易不遵守约束、释义模型容易风格单一），<em>混合使用能让单一失效模式的影响被稀释，同时提高整体多样性</em>。混合的成本几乎为零（同一套过滤器），收益是实实在在的鲁棒性。这与集成学习「不同错误模式的模型混合更稳」是同一个道理。",
        ),
        CALLOUT("warn", "对 LLM 改写要特别加一条检查：<strong>约束遵守性</strong>。你在 prompt 里写「不要改变任何数字」，模型有相当概率还是改了——而这个失效不会被回译的关键成分检查之外的任何东西发现。<em>所以用 LLM 改写时，prompt 里写的每一条约束，都要有一个对应的自动检查</em>。「写了约束就以为模型会遵守」是 LLM 时代新增的一类天真，模块 03 会再遇到它。"),
    ])),
    ("practice", "一条可直接照抄的回译管线", "".join([
        P("把本模块的结论压成一段伪代码。它的形状对<strong>任何生成式增强</strong>都适用，只需替换第 ② 步的生成器。"),
        CODE("""for x, y in train_only:                     # ⚠️ 只对训练集做（模块 04 的铁律）
    protected = extract_protected(x)         # ① 实体/数字 -> 占位符，翻译前替换
    x_masked  = mask_entities(x, protected)

    for _ in range(n_candidates):            # ② 宽松生成：温度调到甜点区（本模块第 4 节）
        z  = translate(x_masked, src->pivot, temperature=0.8, sample=True)
        x2 = translate(z, pivot->src, temperature=0.8, sample=True)
        x2 = unmask_entities(x2, protected)  # 换回实体与数字

        # ③ 三级过滤：先便宜后贵，任何一级不过就丢弃（**丢弃比修正可靠**）
        if not key_components_match(x, x2):  continue     # 否定词数 / 实体集 / 数字集
        sim = jaccard(x, x2)
        if not (LO <= sim <= HI):            continue     # **双边**：太低=漂移，太高=无效
        if not model_consistent(x, x2):      continue     # 可选：两边预测明显相反则丢

        emit(x2, y)                          # ④ 沿用原标签
        break                                # 每条原样本取 1 个可用副本就够

log_stage_drop_rates()                       # ⑤ 分阶段丢弃率 = 诊断报告（模块 04）"""),
        TABLE(["这一步", "对应本模块哪一节", "调错了会怎样"], [
            ["① 占位符替换", "四类高危场景", "实体被错译成另一个实体，且关键成分检查也发现不了（因为集合仍是「一个实体」）"],
            ["② 温度", "多样性来自解码策略", "太低 → 副本几乎等于原文（白花两次翻译）；太高 → 保留率崩、成本翻倍"],
            ["③ 三级过滤", "自动保真度检验", "少了双边中的上界 → 大量无效副本混进训练集"],
            ["④ 沿用原标签", "回译的基本假设", "—（这正是保真度检验存在的理由）"],
            ["⑤ 分阶段统计", "模块 04", "只知道「留下了 60%」，不知道该调温度还是该调过滤带"],
        ]),
        DUAL(
            "这段伪代码里有个细节值得点出：<strong>第 ③ 步「任何一级不过就丢弃」而不是「尝试修正」</strong>。修正听起来更省（不浪费已生成的样本），但它有两个问题：<em>①修正逻辑本身可能引入新错误</em>（把回译里丢失的否定词加回去，位置往往不对）；<em>②被修正的样本质量分布与正常样本不同</em>，等于往训练集里塞了一批「人工缝合」的怪样本。<strong>丢弃是干净的，而生成成本远低于「修正错了」的代价。</strong>",
            "另一个细节是 <code>break</code>：<strong>每条原样本只取一个可用副本</strong>。为什么不多取几个？因为同一条原样本的多个回译副本彼此高度相似（它们都受同一个原文约束），<em>边际多样性收益很快趋零</em>，而每一个都要占训练集的一个位置、稀释原始样本的权重。<strong>「宽度优先」（每条原样本 1–2 个副本、覆盖更多原样本）通常优于「深度优先」（少数原样本各造十个副本）。</strong>",
        ),
        CALLOUT("intuition", "把整个模块的方法论提炼成一句可迁移的话：<strong>生成式增强的工程重心不在生成端，而在过滤端与统计端</strong>。生成端你能调的只有温度与枢轴（旋钮很少、效果有限）；过滤端决定了最终数据的保真度（也就是能不能用）；统计端决定了你能不能诊断问题、能不能回答「该改哪一步」。<em>看到一份增强管线的代码，先看它的过滤与日志写了多少行——那才是它的质量水位。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>采样回译的最优噪声水平</strong>：Edunov et al. 2018 在 NMT 上发现「加噪的 beam」最好，但那是合成源句的场景。<em>在分类增强（合成输入 + 沿用标签）里最优噪声应该更低，具体多低缺乏系统研究</em>。这是个边界清晰、容易做的实证问题。",
            "<strong>一致性正则化 vs 数据增广</strong>：UDA（Xie et al. 2020）不是把回译样本当额外训练数据，而是要求「原样本与回译样本的预测分布一致」（KL 项）。<em>这在半监督场景下利用了无标注数据</em>，且不依赖标签保真（因为不用标签）。这条路线与本课主线互补，值得知道它绕开了保真度问题。",
            "<strong>过滤器的偏差</strong>：用模型一致性做过滤会引入 confirmation bias（保留的都是模型已会的）。这与自训练/伪标签的经典问题同源。<em>如何设计不引入这种偏差的过滤器</em>（或量化它的影响）仍是开放的。",
            "<strong>低资源语言的回译</strong>：回译最需要的场景（低资源语言的分类任务）恰恰是翻译模型最差的场景——<em>这是一个结构性的鸡生蛋问题</em>。用多语言模型的零样本翻译、或用高资源语言做枢轴，效果都不理想。",
            "<strong>释义的「语义等价」到底怎么定义</strong>：所有语义层增强都假设存在「保持语义」这个操作，但语义等价在语用层面并不清晰（「还行」与「很好」在评论语境里是否等价？取决于任务）。<em>这个模糊性是保真度检验只能靠任务特定规则的根本原因</em>。",
        ]),
        CALLOUT("paper", "必读：Sennrich, Haddow &amp; Birch 2016 <em>Improving Neural Machine Translation Models with Monolingual Data</em>（回译的出处）、Edunov et al. 2018 <em>Understanding Back-Translation at Scale</em>（**采样 vs beam 的关键消融**，本模块第二节的依据）、Xie et al. 2020 <em>Unsupervised Data Augmentation for Consistency Training</em>（把回译用于一致性正则而非直接增广，绕开保真度问题）。补充：Sugiyama &amp; Yoshinaga 2019 关于回译在文本分类上的消融；Feng et al. 2021 的 NLP 增强综述。相邻课程：C49 模块 04（seq2seq 与解码策略）、C43 模块 04（多阶段过滤的「先便宜后贵」节奏）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 回译与释义（可控失真的模拟翻译器 + 保真-多样权衡前沿）

目标：用**参数可控的模拟翻译器**复现回译的全部性质——保语义的机制、多样性从哪来、
四类高危失效场景、以及「宽松生成 + 严格过滤」为什么优于「保守生成 + 不过滤」。

路线：模拟翻译器（distortion 可控）→ 回译管线 → 解码温度是多样性主源 →
四类高危场景与否定奇偶检查 → 三级过滤流水线 → **保真-多样权衡前沿与最优温度** →
与 EDA 的成本对比 → ✏️ 练习 → 📖 答案 → 🧪 有效成本胶囊。

> 心智模型：**语义层增强的可靠性不来自「生成得多好」，而来自「过滤得多严」。**"""),
    md("""## 0 · 复用检验工具 + 一个可控失真的模拟翻译器

真实翻译模型不可用，但回译的**性质**完全可以用一个带 `distortion` 参数的模拟器复现——
而且参数可控让我们能做真实环境里做不到的实验（比如「把失真从 0 调到 0.5，看过滤器什么时候开始起作用」）。"""),
    code("""import numpy as np, math, collections, itertools
rng = np.random.default_rng(0)

POS_WORDS = {'好吃', '不错', '推荐', '干净', '很好', '满意', '喜欢'}
NEG_WORDS = {'难吃', '差', '脏', '失望', '糟糕'}
NEGATORS  = {'不', '没', '别'}
NEUTRAL   = ['这家', '店', '的', '菜', '服务', '环境', '价格', '味道', '朋友', '下次',
             '我们', '昨天', '一起', '去', '吃', '了', '感觉', '整体']
ENTITIES  = ['海底捞', '西湖', '张三']
NUMBERS   = ['3', '30', '100']

def rule_label(tokens, window=3):
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
    if r.random() < 0.45:
        toks.insert(max(0, pos - int(r.integers(1, 3))), str(r.choice(sorted(NEGATORS))))
    if r.random() < 0.3:
        toks.insert(int(r.integers(0, len(toks))), str(r.choice(ENTITIES)))
    if r.random() < 0.3:
        toks.insert(int(r.integers(0, len(toks))), str(r.choice(NUMBERS)))
    return toks, rule_label(toks)

def fidelity(pairs):
    return 1.0 if not pairs else sum(1 for o, y, a in pairs if rule_label(a) == y)/len(pairs)

def ngrams(t, n):
    return [tuple(t[i:i+n]) for i in range(len(t)-n+1)]

def distinct_n(texts, n=2):
    tot, uniq = 0, set()
    for t in texts:
        g = ngrams(t, n); tot += len(g); uniq.update(g)
    return len(uniq)/tot if tot else 0.0

def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb)/len(sa | sb) if (sa | sb) else 1.0

print('✅ 检验工具就绪')"""),
    code("""# ── 可控的模拟翻译器 ──
# 「翻译」= 把词映射到同义变体；temperature 控制选变体的随机性；
# distortion 控制「语义漂移」的概率（丢否定词 / 改情感强度 / 错译实体 / 改数字）
# ⚠️ 释义表必须**扩充词表**：每个词有自己独有的变体。
#    如果多个词映射到同一批变体（多对一），高温反而会**降低**词面多样性 ——
#    这是设计模拟器时踩到的一个真实陷阱，也提醒你真实释义模型也可能有同样的坍缩倾向。
PARAPHRASE = {
    '这家': ['本', '该'], '店': ['餐厅', '饭店'], '菜': ['菜品', '食物'],
    '服务': ['服务员', '接待'], '环境': ['氛围', '装修'], '价格': ['收费', '价位'],
    '味道': ['口味', '风味'], '感觉': ['觉得', '体会'], '整体': ['总体', '总的'],
    '好吃': ['美味', '可口'], '不错': ['优秀', '出色'], '很好': ['极好', '很棒'],
    '难吃': ['糟糕', '难以下咽'], '差': ['不行', '很糟'], '脏': ['不洁', '脏乱'],
    '干净': ['整洁', '清洁'], '推荐': ['值得去', '力荐'],
    '满意': ['满足', '称心'], '失望': ['遗憾', '扫兴'],
}
# 情感词的**所有释义变体也算情感词** —— 这样「合法释义」不改变规则标签，
# 标签破坏就只来自真正的语义漂移（丢否定词等），而不是词表不全的假象。
POS_WORDS = POS_WORDS | {v for w in list(POS_WORDS) for v in PARAPHRASE.get(w, [])}
NEG_WORDS = NEG_WORDS | {v for w in list(NEG_WORDS) for v in PARAPHRASE.get(w, [])}
STRENGTH_SHIFT = {'不错': '很好', '满意': '很好'}   # 强度漂移（危险，但两端都是正面词）

def translate(tokens, temperature, distortion, r):
    '''模拟一次翻译。temperature 控多样性；distortion 控语义漂移。'''
    out = []
    for t in tokens:
        # 语义漂移：以 distortion 概率触发四类高危失效
        if r.random() < distortion:
            kind = r.random()
            if t in NEGATORS and kind < 0.45:
                continue                                        # ① 丢否定词（最致命）
            if t in STRENGTH_SHIFT and kind < 0.7:
                out.append(STRENGTH_SHIFT[t]); continue          # ② 强度漂移
            if t in ENTITIES and kind < 0.85:
                out.append(str(r.choice([e for e in ENTITIES if e != t]))); continue  # ③ 实体错译
            if t in NUMBERS:
                out.append(str(r.choice([n for n in NUMBERS if n != t]))); continue   # ④ 数字改变
        # 正常释义：temperature 越高越可能换成变体
        if t in PARAPHRASE and r.random() < temperature:
            out.append(str(r.choice(PARAPHRASE[t])))
        else:
            out.append(t)
    return out if out else list(tokens[:1])

def back_translate(tokens, temperature, distortion, r, hops=1):
    '''回译 = 正向 + 反向（hops>1 表示多跳，误差会累积）。'''
    cur = list(tokens)
    for _ in range(hops):
        cur = translate(cur, temperature, distortion, r)   # 正向
        cur = translate(cur, temperature, distortion, r)   # 反向
    return cur

DATA = [make_sentence(np.random.default_rng(s)) for s in range(400)]
r = np.random.default_rng(7)
for t, y in DATA[:3]:
    bt = back_translate(t, 0.7, 0.05, r)
    print(f'原({"正" if y else "负"}): {" ".join(t)}')
    print(f'回译({"正" if rule_label(bt) else "负"}): {" ".join(bt)}\\n')
print('✅ 模拟回译器就绪：temperature 控多样性、distortion 控语义漂移')"""),
    md("""## 1 · 解码温度是多样性的主要来源

常见误解是「换中间语言就能增加多样性」。实际上**多样性主要来自反向翻译的解码策略**。
温度 0（贪心/beam）时所有副本几乎相同——这正是 Edunov et al. 2018 指出的问题。"""),
    code("""def make_copies(data, n_aug, temperature, distortion, seed=0, hops=1):
    r = np.random.default_rng(seed)
    pairs, aug = [], []
    for t, y in data:
        for _ in range(n_aug):
            b = back_translate(t, temperature, distortion, r, hops=hops)
            pairs.append((t, y, b)); aug.append((b, y))
    return pairs, aug

print(f"{'温度':>6s} {'保真度':>9s} {'distinct-2':>11s} {'副本间平均Jaccard':>18s}")
for temp in [0.0, 0.3, 0.7, 1.0]:
    pairs, aug = make_copies(DATA, 4, temp, 0.05, seed=11)
    # 同一原句的 4 个副本之间有多像？（越低越多样）
    sims = []
    for i in range(0, len(pairs), 4):
        grp = [pairs[i+k][2] for k in range(4)]
        sims += [jaccard(grp[a], grp[b]) for a in range(4) for b in range(a+1, 4)]
    print(f'{temp:>6.1f} {fidelity(pairs):>9.1%} {distinct_n([a for a,_ in aug],2):>11.4f} '
          f'{np.mean(sims):>18.3f}')

p0, a0 = make_copies(DATA, 4, 0.0, 0.05, seed=11)
p1, a1 = make_copies(DATA, 4, 1.0, 0.05, seed=11)
sims0 = []
for i in range(0, len(p0), 4):
    grp = [p0[i+k][2] for k in range(4)]
    sims0 += [jaccard(grp[a], grp[b]) for a in range(4) for b in range(a+1, 4)]
sims1 = []
for i in range(0, len(p1), 4):
    grp = [p1[i+k][2] for k in range(4)]
    sims1 += [jaccard(grp[a], grp[b]) for a in range(4) for b in range(a+1, 4)]
assert np.mean(sims0) > np.mean(sims1), '温度越高，副本之间越不像（越多样）'
assert np.mean(sims0) > 0.95, '温度 0 时 4 个副本几乎完全相同 —— 等于只增强了 1 份'
print(f'\\n⚠️  温度 0 时副本间 Jaccard = {np.mean(sims0):.3f}（几乎相同）——')
print('   生成 4 个副本，实际只得到 1 份新数据，两次翻译的算力全浪费了。')
print('✅ 这就是 Edunov et al. 2018 的核心发现：**回译要用采样，不要用纯 beam**。')"""),
    md("""### 多跳的误差累积：多样性涨了，保真度崩了"""),
    code("""print(f"{'跳数':>5s} {'保真度':>9s} {'distinct-2':>11s} {'与原文Jaccard':>14s}")
for hops in [1, 2, 3]:
    pairs, aug = make_copies(DATA, 2, 0.7, 0.08, seed=13, hops=hops)
    sim2orig = np.mean([jaccard(o, a) for o, _, a in pairs])
    print(f'{hops:>5d} {fidelity(pairs):>9.1%} {distinct_n([a for a,_ in aug],2):>11.4f} '
          f'{sim2orig:>14.3f}')

f1 = fidelity(make_copies(DATA, 2, 0.7, 0.08, seed=13, hops=1)[0])
f3 = fidelity(make_copies(DATA, 2, 0.7, 0.08, seed=13, hops=3)[0])
assert f3 < f1, '多跳会累积误差，保真度下降'
print(f'\\n✅ 1 跳保真 {f1:.1%} -> 3 跳保真 {f3:.1%}。多跳是「用保真度换多样性」的坏交易 ——')
print('   因为同样的多样性可以用「提高温度 + 严格过滤」更便宜地拿到（见第 4 节）。')"""),
    md("""## 2 · 四类高危场景与否定奇偶检查

回译产出的句子**总是通顺的**，即使语义已经漂移。「通顺性给了它虚假的可信度」。
一个粗糙但零成本的检查：**否定词计数的变化**。"""),
    code("""def negation_count(tokens):
    return sum(1 for t in tokens if t in NEGATORS)

def entity_set(tokens):
    return {t for t in tokens if t in ENTITIES}

def number_set(tokens):
    return {t for t in tokens if t in NUMBERS}

def key_component_check(orig, aug):
    '''判据 ①：关键成分一致性（零成本，挡致命错误）。'''
    return (negation_count(orig) == negation_count(aug)
            and entity_set(orig) == entity_set(aug)
            and number_set(orig) == number_set(aug))

pairs, _ = make_copies(DATA, 4, 0.7, 0.12, seed=17)     # 故意用较高 distortion
broken = [(o, y, a) for o, y, a in pairs if rule_label(a) != y]
print(f'总副本 {len(pairs)}, 标签被破坏 {len(broken)} ({len(broken)/len(pairs):.1%})')
print('\\n被破坏的例子（注意句子仍然「通顺」）:')
for o, y, a in broken[:3]:
    print(f'  原({"正" if y else "负"}): {" ".join(o)}')
    print(f'  译({"正" if rule_label(a) else "负"}): {" ".join(a)}')
    print(f'    否定词数 {negation_count(o)} -> {negation_count(a)} | '
          f'关键成分一致? {key_component_check(o, a)}\\n')

# 量化：关键成分检查挡住了多少破坏？
caught = sum(1 for o, y, a in broken if not key_component_check(o, a))
kept_ok = sum(1 for o, y, a in pairs if rule_label(a) == y and key_component_check(o, a))
print(f'关键成分检查抓住了 {caught}/{len(broken)} = {caught/len(broken):.1%} 的破坏样本')
assert caught / len(broken) > 0.5, '关键成分检查应能抓住多数破坏'
filtered = [(o, y, a) for o, y, a in pairs if key_component_check(o, a)]
print(f'过滤后: 保留 {len(filtered)}/{len(pairs)} ({len(filtered)/len(pairs):.1%}), '
      f'保真度 {fidelity(pairs):.1%} -> {fidelity(filtered):.1%}')
assert fidelity(filtered) > fidelity(pairs), '过滤应提升保真度'
print('\\n✅ 一个几乎零成本的规则过滤器，把保真度从 '
      f'{fidelity(pairs):.1%} 提到 {fidelity(filtered):.1%}。')
print('   「粗糙但零成本的过滤器」往往比「精细但昂贵的修正器」更值得先做。')"""),
    md("""## 3 · 三级过滤流水线：先便宜后贵

① 关键成分（零成本，挡致命）→ ② 相似度**双边**带（挡漂移 + 挡无效副本）→ ③ 模型一致性（可选）。

**判据 ② 是双边的**：相似度太低=语义漂了；太高=副本等于原文，白花了两次翻译。"""),
    code("""def similarity_band_check(orig, aug, lo=0.30, hi=0.85):
    '''判据 ②：双边过滤。太低=漂移；太高=没变化（无效副本）。'''
    s = jaccard(orig, aug)
    return lo <= s <= hi, s

def build_classifier(train_data, seed=0):
    VOCAB = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS | set(ENTITIES)
                   | set(NUMBERS) | {v for vs in PARAPHRASE.values() for v in vs}
                   | set(STRENGTH_SHIFT.values()))
    v2i = {w: i for i, w in enumerate(VOCAB)}
    def feat(t):
        x = np.zeros(len(VOCAB)+1)
        for w in t:
            if w in v2i: x[v2i[w]] += 1
        x[-1] = 1; return x
    X = np.stack([feat(t) for t, _ in train_data]); y = np.array([l for _, l in train_data])
    w = np.random.default_rng(seed).normal(size=X.shape[1])*0.01
    for _ in range(400):
        p = 1/(1+np.exp(-(X @ w)))
        w -= 0.3*(X.T @ (p-y)/len(y) + 1e-3*w)
    return (lambda t: int(feat(t) @ w > 0)), (lambda t: float(feat(t) @ w))

clf, score_fn = build_classifier(DATA)

def model_consistency_check(orig, aug, min_conf=0.5):
    '''判据 ③：两边预测相反且都较自信 -> 丢弃。'''
    so, sa = score_fn(orig), score_fn(aug)
    if (so > 0) == (sa > 0):
        return True
    return not (abs(so) > min_conf and abs(sa) > min_conf)

def pipeline(pairs, use_key=True, use_sim=True, use_model=False, lo=0.30, hi=0.85):
    kept, stage_drop = [], collections.Counter()
    for o, y, a in pairs:
        if use_key and not key_component_check(o, a):
            stage_drop['①关键成分'] += 1; continue
        if use_sim:
            ok, s = similarity_band_check(o, a, lo, hi)
            if not ok:
                stage_drop['②相似度太低' if s < lo else '②相似度太高'] += 1; continue
        if use_model and not model_consistency_check(o, a):
            stage_drop['③模型不一致'] += 1; continue
        kept.append((o, y, a))
    return kept, stage_drop

pairs, _ = make_copies(DATA, 4, 0.7, 0.10, seed=19)
print(f'过滤前: {len(pairs)} 个副本, 保真度 {fidelity(pairs):.1%}, '
      f'distinct-2 {distinct_n([a for _,_,a in pairs],2):.4f}\\n')
for label, kw in [('仅 ①', dict(use_sim=False)),
                  ('① + ②', dict()),
                  ('① + ② + ③', dict(use_model=True))]:
    kept, drops = pipeline(pairs, **kw)
    print(f'{label:<12s} 保留 {len(kept):>4d} ({len(kept)/len(pairs):>5.1%}) | '
          f'保真度 {fidelity(kept):>6.1%} | distinct-2 {distinct_n([a for _,_,a in kept],2):.4f}')
    print(f'{"":12s} 各阶段丢弃: {dict(drops)}')

k1, _ = pipeline(pairs, use_sim=False)
k12, _ = pipeline(pairs)
k123, _ = pipeline(pairs, use_model=True)
assert fidelity(k12) >= fidelity(k1), '加相似度过滤应不降保真度'
assert fidelity(k123) >= fidelity(k12), '加模型一致性应进一步提升'
assert len(k123) <= len(k12) <= len(k1), '过滤越多保留越少'
print('\\n✅ 「先便宜后贵」的多阶段过滤 —— 与 C43 模块 04 的大规模质量过滤是同一个模式。')"""),
    code("""# 双边过滤为什么必要：单边（只挡太低）会留下大量「等于原文」的无效副本
pairs_low_temp, _ = make_copies(DATA, 4, 0.15, 0.05, seed=23)
one_sided = [(o, y, a) for o, y, a in pairs_low_temp if jaccard(o, a) >= 0.30]
two_sided = [(o, y, a) for o, y, a in pairs_low_temp if 0.30 <= jaccard(o, a) <= 0.85]
identical = sum(1 for o, y, a in pairs_low_temp if o == a)
print(f'低温度(0.15)下 {len(pairs_low_temp)} 个副本里，与原文**完全相同**的有 {identical} 个')
print(f'单边过滤(只挡太低): 保留 {len(one_sided)}，其中无效副本仍在')
print(f'双边过滤:           保留 {len(two_sided)}')
assert len(two_sided) < len(one_sided), '双边过滤会额外丢掉「太像」的副本'
assert identical > 0, '低温度必然产生一批与原文完全相同的副本'
print('\\n✅ 相似度太高的副本没有提供任何新信息，只是把数据复制了一遍 ——')
print('   还白花了两次翻译的算力。**双边过滤，不是单边。**')"""),
    md("""## 4 · 保真-多样权衡前沿与最优温度

过滤把不同温度下的「过滤后保真度」拉到接近水平，代价是**保留率不同**。
于是温度选择变成一个纯成本问题：

$$\\text{有效成本/可用副本} = \\frac{2\\times\\text{生成成本}}{\\text{保留率}}$$"""),
    code("""def sweep_temperature(temps, distortion=0.10, n_aug=4, seed=29):
    rows = []
    for temp in temps:
        pairs, _ = make_copies(DATA, n_aug, temp, distortion, seed=seed)
        kept, _ = pipeline(pairs)
        keep_rate = len(kept)/len(pairs)
        div = distinct_n([a for _, _, a in kept], 2) if kept else 0.0
        fid = fidelity(kept)
        eff_cost = (2.0 / keep_rate) if keep_rate > 0 else float('inf')
        rows.append((temp, fidelity(pairs), keep_rate, fid, div, eff_cost, keep_rate*div))
    return rows

print(f"{'温度':>6s} {'过滤前保真':>10s} {'保留率':>8s} {'过滤后保真':>10s} "
      f"{'过滤后多样':>10s} {'有效成本':>9s} {'保留×多样':>10s}")
rows = sweep_temperature([0.1, 0.3, 0.5, 0.7, 0.9, 1.1])
for t, f0, kr, f1_, d, ec, score in rows:
    print(f'{t:>6.1f} {f0:>10.1%} {kr:>8.1%} {f1_:>10.1%} {d:>10.4f} {ec:>9.1f} {score:>10.4f}')

fids_after = [r[3] for r in rows]
print(f'\\n过滤后保真度的跨度: {min(fids_after):.1%} ~ {max(fids_after):.1%}'
      f'（比过滤前的 {min(r[1] for r in rows):.1%} ~ {max(r[1] for r in rows):.1%} 窄）')
best = max(rows, key=lambda r: r[6])
print(f'✅ 让「保留率 × 多样性」最大的温度 = {best[0]}（有效成本 {best[5]:.1f} 次生成/可用副本）')
assert best[0] > 0.1, '最优温度不应是最低的那个（那样多样性太低）'
print('\\n**结论：有了过滤器之后，温度的作用从「保真 vs 多样」变成「要生成多少候选」**——')
print('  即纯成本问题。所以「宽松生成 + 严格过滤」优于「保守生成 + 不过滤」。')"""),
    code("""# 验证核心论断：宽松生成+严格过滤 vs 保守生成+不过滤
loose_pairs, _ = make_copies(DATA, 4, 0.9, 0.10, seed=31)
loose_kept, _ = pipeline(loose_pairs)
cons_pairs, _ = make_copies(DATA, 4, 0.2, 0.10, seed=31)

# ⚠️ 比较两组「多样性」时要小心指标的可比性：
#    distinct-n 依赖**集合大小**（集合越大、总 n-gram 越多、比值越低），
#    所以两个大小不同的集合直接比 distinct-n 是不公平的。
#    这里用一个**逐样本、与集合大小无关**的指标：
#        新意 novelty = 1 - Jaccard(原文, 增强)   —— 「这个副本相对原文变了多少」
def mean_novelty(prs):
    return float(np.mean([1 - jaccard(o, a) for o, _, a in prs])) if prs else 0.0

print(f'可用副本数: 宽松+过滤 {len(loose_kept)} vs 保守不过滤 {len(cons_pairs)}\\n')
print(f"{'策略':<28s} {'保真度':>9s} {'平均新意':>9s} {'distinct-2':>11s}")
print(f'{"宽松生成(T=0.9)+严格过滤":<28s} {fidelity(loose_kept):>9.1%} '
      f'{mean_novelty(loose_kept):>9.3f} {distinct_n([a for _,_,a in loose_kept],2):>11.4f}')
print(f'{"保守生成(T=0.2)+不过滤":<28s} {fidelity(cons_pairs):>9.1%} '
      f'{mean_novelty(cons_pairs):>9.3f} {distinct_n([a for _,_,a in cons_pairs],2):>11.4f}')

assert fidelity(loose_kept) >= fidelity(cons_pairs) - 0.01, '过滤后的保真度不应更差'
assert mean_novelty(loose_kept) > mean_novelty(cons_pairs) * 1.5, \\
    '宽松生成的副本相对原文变化明显更大（每个副本携带更多新信息）'
print('\\n✅ 宽松生成 + 严格过滤：**保真度相当（由过滤保证），而每个副本的「新意」明显更高**。')
print(f'   新意 {mean_novelty(cons_pairs):.3f} -> {mean_novelty(loose_kept):.3f} '
      f'（{mean_novelty(loose_kept)/max(mean_novelty(cons_pairs),1e-9):.1f}×）')
print('   ⚠️ 注意 distinct-2 这一列**不能直接跨集合大小比较** —— 这也是模块 04 会展开的一个点：')
print('      多样性指标只适合「同尺寸对比」与「同方案的趋势监测」。')
print('   这条「宽松生成 + 严格过滤」的结论对所有生成式增强都成立（含模块 03 的 LLM 合成）。')"""),
    md("""## 5 · 与 EDA 的成本对比：回译处在不太经济的中间地带"""),
    code("""# 相对算力成本（以 EDA = 1 为单位）
COST = {'EDA': 1, 'AEDA': 1, '回译(2次seq2seq)': 1000, 'LLM改写': 2000}

def eda_like(tokens, r, p=0.1):
    protect = NEGATORS | set(ENTITIES) | set(NUMBERS)
    out = [t for t in tokens if (t in protect) or (r.random() >= p)]
    return out if out else list(tokens[:1])

r = np.random.default_rng(37)
eda_pairs = [(t, y, eda_like(t, r)) for t, y in DATA for _ in range(4)]
bt_pairs, _ = make_copies(DATA, 4, 0.7, 0.10, seed=37)
bt_kept, _ = pipeline(bt_pairs)

print(f"{'方法':<22s} {'相对成本':>9s} {'保真度':>9s} {'多样性':>9s} {'成本/多样性':>12s}")
for name, cost, prs in [('EDA + 保护', COST['EDA'], eda_pairs),
                        ('回译 + 三级过滤', COST['回译(2次seq2seq)'], bt_kept)]:
    f = fidelity(prs); d = distinct_n([a for _, _, a in prs], 2)
    print(f'{name:<22s} {cost:>9d} {f:>9.1%} {d:>9.4f} {cost/max(d,1e-9):>12.0f}')

d_eda = distinct_n([a for _,_,a in eda_pairs], 2)
d_bt = distinct_n([a for _,_,a in bt_kept], 2)
print(f'\\n回译的多样性是 EDA 的 {d_bt/d_eda:.2f} 倍，但成本是 {COST["回译(2次seq2seq)"]}倍。')
assert fidelity(bt_kept) > 0.95 and fidelity(eda_pairs) > 0.95, '两者过滤/保护后都应高保真'
print('\\n✅ 诚实的结论：**回译处在一个不太经济的中间地带** ——')
print('   便宜要正则化 -> 用 EDA/AEDA；要真正的多样性与可控性 -> 直接上 LLM（模块 03）。')
print('   回译仍值得学，因为它的**方法论**（语义空间增强 + 严格过滤）对 LLM 改写完全适用。')"""),
    md("""## ✏️ 练习 1：关键成分检查的通用版

实现 `component_check(orig, aug, checks)`：`checks` 是一个 `{名称: 提取函数}` 字典
（提取函数返回可比较的值，如计数或集合）。返回 `(是否全部一致, 不一致的名称列表)`。"""),
    code("""def component_check(orig, aug, checks):
    # TODO: 对每个 (name, fn)，比较 fn(orig) == fn(aug)；返回 (全一致?, 不一致名单)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
CHECKS = {'否定词数': negation_count, '实体集': entity_set, '数字集': number_set,
          '长度比': lambda t: len(t) // 5}
o = ['这家', '店', '不', '好吃', '海底捞', '3']
a1 = ['本', '餐厅', '不', '美味', '海底捞', '3']              # 全部一致
a2 = ['本', '餐厅', '美味', '海底捞', '3']                    # 丢了否定词
a3 = ['本', '餐厅', '不', '美味', '西湖', '3']                 # 实体错译
ok1, bad1 = component_check(o, a1, CHECKS)
assert ok1 and bad1 == [], (ok1, bad1)
ok2, bad2 = component_check(o, a2, CHECKS)
assert not ok2 and '否定词数' in bad2
ok3, bad3 = component_check(o, a3, CHECKS)
assert not ok3 and '实体集' in bad3
print(f'一致    : {ok1}, 不一致项 {bad1}')
print(f'丢否定词: {ok2}, 不一致项 {bad2}')
print(f'实体错译: {ok3}, 不一致项 {bad3}')
print('✅ 练习 1 通过：把「哪些成分必须保持」写成可配置的检查表 ——')
print('   换任务只需换 checks，管线不变。')"""),
    md("""## ✏️ 练习 2：双边相似度带的最优区间

实现 `best_band(pairs, lo_candidates, hi_candidates, min_fidelity)`：
在所有 `(lo, hi)` 组合里，找**过滤后保真度 ≥ min_fidelity** 且
**保留率 × 多样性最大**的那一组。返回 `(lo, hi, 保留率, 保真度, 多样性)`；无可行解返回 `None`。"""),
    code("""def best_band(pairs, lo_candidates, hi_candidates, min_fidelity):
    # TODO: 枚举 (lo, hi)（要求 lo < hi）；先过 key_component_check，再过相似度带；
    #       计算 keep_rate / fidelity / distinct_n；在满足 min_fidelity 的组合里最大化 keep_rate*distinct
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
pairs_t, _ = make_copies(DATA, 4, 0.8, 0.10, seed=41)
res = best_band(pairs_t, [0.1, 0.2, 0.3, 0.4], [0.7, 0.8, 0.9, 1.0], min_fidelity=0.97)
assert res is not None
lo, hi, kr, fid, div = res
print(f'最优带 [{lo}, {hi}]: 保留率 {kr:.1%}, 保真度 {fid:.1%}, 多样性 {div:.4f}')
assert lo < hi and fid >= 0.97
# 要求极高保真度时可能无解
assert best_band(pairs_t, [0.1], [1.0], min_fidelity=1.01) is None
# 更严的保真要求 -> 保留率不会更高
res_strict = best_band(pairs_t, [0.1, 0.2, 0.3, 0.4], [0.7, 0.8, 0.9, 1.0], 0.99)
if res_strict:
    assert res_strict[2] <= kr + 1e-9, '更严的保真要求通常保留率更低'
print('✅ 练习 2 通过：过滤带也是「约束下最优」——保真度是约束，保留率×多样性是目标')"""),
    md("""## ✏️ 练习 3：有效成本

实现 `effective_cost(gen_cost_per_call, calls_per_copy, keep_rate)`：
返回**每个可用副本**的成本。`keep_rate = 0` 时返回 `float('inf')`。
再实现 `pick_temperature(rows)`：`rows` 是 `[(temp, keep_rate, diversity)]`，
返回让 `keep_rate * diversity` 最大的温度。"""),
    code("""def effective_cost(gen_cost_per_call, calls_per_copy, keep_rate):
    # TODO
    raise NotImplementedError

def pick_temperature(rows):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert effective_cost(0.001, 2, 0.5) == 0.004, '保留率 50% -> 每个可用副本要生成 2 组'
assert effective_cost(0.001, 2, 0.0) == float('inf')
assert effective_cost(0.001, 1, 1.0) == 0.001
rows_t = [(t, kr, d) for t, _, kr, _, d, _, _ in sweep_temperature([0.1, 0.5, 0.9])]
best_t = pick_temperature(rows_t)
assert best_t in [t for t, _, _ in rows_t]
print(f'候选: {[(round(t,1), round(kr,3), round(d,4)) for t, kr, d in rows_t]}')
print(f'最优温度: {best_t}')
print(f'该温度下每可用副本成本: '
      f'{effective_cost(0.001, 2, dict((t, kr) for t, kr, _ in rows_t)[best_t]):.5f}')
print('✅ 练习 3 通过：有了过滤器，温度选择就是纯成本优化')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def component_check(orig, aug, checks):
    bad = [name for name, fn in checks.items() if fn(orig) != fn(aug)]
    return (not bad), bad"""),
    code("""# 练习 2 参考答案
def best_band(pairs, lo_candidates, hi_candidates, min_fidelity):
    best = None
    for lo in lo_candidates:
        for hi in hi_candidates:
            if lo >= hi: continue
            kept = [(o, y, a) for o, y, a in pairs
                    if key_component_check(o, a) and lo <= jaccard(o, a) <= hi]
            if not kept: continue
            kr = len(kept)/len(pairs)
            fid = fidelity(kept)
            div = distinct_n([a for _, _, a in kept], 2)
            if fid >= min_fidelity:
                score = kr * div
                if best is None or score > best[0]:
                    best = (score, lo, hi, kr, fid, div)
    return None if best is None else (best[1], best[2], best[3], best[4], best[5])"""),
    code("""# 练习 3 参考答案
def effective_cost(gen_cost_per_call, calls_per_copy, keep_rate):
    if keep_rate <= 0: return float('inf')
    return gen_cost_per_call * calls_per_copy / keep_rate

def pick_temperature(rows):
    return max(rows, key=lambda r: r[1] * r[2])[0]"""),
    md("""---
## 🧪 真实数据胶囊：回译 vs LLM 改写的成本对比

用公开的量级数字算清「回译到底贵在哪」，以及什么时候它仍然是对的选择。"""),
    code("""# 公开量级（可改成你自己的数字）
MT_MODEL_PARAMS = 300e6          # 一个 MarianMT/NLLB 量级的翻译模型
LLM_PARAMS = 8e9                 # 一个 8B 指令模型
AVG_TOKENS = 40                  # 平均句长
GPU_TFLOPS_EFF, GPU_USD_H = 150, 4.0

def local_gen_cost(params, n_tokens):
    '''自建生成成本：自回归逐 token，每 token 约 2*params FLOPs。'''
    flops = 2 * params * n_tokens
    return flops / (GPU_TFLOPS_EFF * 1e12) / 3600 * GPU_USD_H

bt_cost = 2 * local_gen_cost(MT_MODEL_PARAMS, AVG_TOKENS)          # 两次翻译
llm_local = local_gen_cost(LLM_PARAMS, AVG_TOKENS)
# API 计价：输入 $0.15/1M token、输出 $0.60/1M token（公开量级）
llm_api = (AVG_TOKENS * 2 / 1_000_000) * 0.15 + (AVG_TOKENS / 1_000_000) * 0.60

print(f"{'方法':<24s} {'每副本成本$':>13s} {'1000条×4副本 总成本$':>22s}")
for name, c in [('回译（自建 MT ×2）', bt_cost),
                ('LLM 改写（自建 8B）', llm_local),
                ('LLM 改写（API）', llm_api)]:
    print(f'{name:<24s} {c:>13.8f} {c*4000:>22.4f}')

assert bt_cost < llm_local, '同为自建时，300M 模型跑两次仍便宜于 8B 跑一次'
print(f'\\n① 自建对比: 回译(2×300M) 比 LLM(1×8B) 便宜 {llm_local/bt_cost:.1f} 倍')
print(f'② 但 API 版 LLM 只要 ${llm_api*4000:.4f} 总成本 —— 绝对值极低，')
print('   而且不需要你部署与维护两个翻译模型（运维成本远超算力成本）。')
print('\\n✅ 回译仍然是对的选择的三种情形：')
print('   · 必须完全离线（合规/内网），不能调 API')
print('   · 已有现成的高质量翻译模型与推理服务')
print('   · 需要处理的量极大（几百万条），API 费用累积起来才是主导项')"""),
    md("""**🧪 胶囊练习**：实现 `augmentation_plan(n_samples, n_aug, keep_rate, cost_per_call, calls_per_copy)`：
返回 `{'calls':…, 'usable_copies':…, 'total_cost':…, 'cost_per_usable':…}`。
注意：要拿到 `n_samples*n_aug` 个**可用**副本，需要生成 `n_samples*n_aug/keep_rate` 组。"""),
    code("""def augmentation_plan(n_samples, n_aug, keep_rate, cost_per_call, calls_per_copy):
    # TODO: attempts = ceil(n_samples*n_aug / keep_rate)
    #       calls = attempts * calls_per_copy
    #       usable = n_samples*n_aug；total_cost = calls*cost_per_call
    raise NotImplementedError"""),
    code("""# 自测
plan = augmentation_plan(1000, 4, keep_rate=0.6, cost_per_call=bt_cost/2, calls_per_copy=2)
assert plan['usable_copies'] == 4000
assert plan['calls'] == math.ceil(4000/0.6) * 2
assert abs(plan['cost_per_usable'] - plan['total_cost']/4000) < 1e-12
print(f'要 4000 个可用副本（保留率 60%）:')
print(f'  需生成 {plan["calls"]:,} 次调用, 总成本 ${plan["total_cost"]:.4f}, '
      f'每可用副本 ${plan["cost_per_usable"]:.8f}')
# 保留率越低成本越高
plan_low = augmentation_plan(1000, 4, 0.2, bt_cost/2, 2)
assert plan_low['total_cost'] > plan['total_cost'] * 2
print(f'保留率降到 20%: 总成本涨到 ${plan_low["total_cost"]:.4f} '
      f'（{plan_low["total_cost"]/plan["total_cost"]:.1f}×）')
print('\\n✅ 胶囊练习通过：**过滤器的严格程度直接乘进成本** ——')
print('   所以「宽松生成+严格过滤」要配合「保留率别太低」，第 4 节的最优温度就是这个平衡点。')"""),
    code("""# 📖 胶囊参考答案
def augmentation_plan(n_samples, n_aug, keep_rate, cost_per_call, calls_per_copy):
    usable = n_samples * n_aug
    attempts = math.ceil(usable / keep_rate)
    calls = attempts * calls_per_copy
    total = calls * cost_per_call
    return {'calls': calls, 'usable_copies': usable,
            'total_cost': total, 'cost_per_usable': total / usable}"""),
    md("""### 小结
- 回译在**语义空间**而非词面空间操作，「保语义」是内建约束 → 保真度比 EDA 高一档。
- 但它的失效**更隐蔽**：产出句子总是通顺的，即使语义已漂移。**通顺性给了它虚假的可信度**。
- **多样性主要来自解码温度，不是中间语言**。温度 0 时 4 个副本几乎相同（Jaccard>0.95）——白花算力。
- **多跳会累积误差**，是「用保真换多样」的坏交易；同样多样性可用「高温 + 严格过滤」更便宜地拿到。
- **四类高危场景**：否定、程度、实体、数字。零成本的**关键成分检查**（否定词计数 + 实体集 + 数字集）能抓住多数破坏。
- **相似度过滤必须是双边的**：太低=漂移，太高=副本等于原文（无效且浪费）。
- **核心论断（对所有生成式增强都成立）：宽松生成 + 严格过滤 > 保守生成 + 不过滤。** 有了过滤器，温度就变成纯成本问题。
- 诚实的结论：**回译处在不太经济的中间地带**——便宜要正则化用 EDA/AEDA，要多样性与可控性直接上 LLM。学它是为了那套方法论。

下一站：**模块 03 · LLM 驱动的指令数据合成** —— 唯一能真正增加信息量的增强层次。"""),
]
