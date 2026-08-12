# -*- coding: utf-8 -*-
"""C51 模块 04 · 增强的质量控制。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–03；C43 模块 05（去污染）与 C10（标注质量）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_quality_control.ipynb'),
    ("核心参考", "Li et al. 2016（distinct-n）、Zhu et al. 2018（self-BLEU）、Lee et al. 2021（去重与去污染）、Shumailov et al. 2024（collapse）"),
    ("预计时长", "读 55 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("why", "为什么质量控制是一条流水线而不是一个指标", "".join([
        P("前三个模块产出了增强数据。这一模块回答：<strong>怎么在把它们喂给模型之前，把坏的挡在外面</strong>。"),
        P("一个常见的错误做法是「算一个多样性分数，看着还行就用」。这行不通，因为<strong>增强数据的失效方式是多维的，而每个维度需要不同的检测手段</strong>："),
        ASCII("""增强数据的四类失效，各需一套检测

① 标签被破坏  (fidelity)      -> 规则检查 / 关键成分一致性 / 模型一致性
   症状: 训练集里混入错标数据；模型在决策边界上变差

② 多样性不足  (diversity)     -> distinct-n / self-BLEU / 嵌入覆盖 / 重复率
   症状: 花了算力却等于把数据复制了几遍；正则化效果为零

③ 测试集泄漏  (contamination) -> n-gram 重叠 / 近重复检索 / 精确子串
   症状: **评测分数虚高**，上线后效果远低于评测——最危险的一类

④ 分布坍塌    (collapse)      -> 多代趋势监测（模块 03 的四个征兆）
   症状: 渐进的、不报错的、几代之后才显现

关键：这四类**互相独立**。①好不代表②好（复制原样本：保真 100%、多样性零）；
      ②好不代表③好（多样性高的合成数据照样可能撞上测试集）。""")
        ,
        DUAL(
            "所以质量控制必须是<strong>一条按顺序执行的流水线</strong>，而不是一个综合分数。顺序遵循两条原则：<strong>①先便宜后贵</strong>（零成本的规则检查在前，需要模型的在后）；<strong>②先致命后次要</strong>（污染与错标是致命的，多样性不足只是浪费）。",
            "还有一个容易被忽略的设计要点：<strong>每个阶段都要记录「丢了多少、为什么丢」</strong>。这不是为了好看——<em>各阶段的丢弃率本身就是最有用的诊断信号</em>。「去重丢了 80%」说明生成器在同质化；「污染检查丢了 5%」说明教师模型见过你的测试集；「保真检查丢了 20%」说明增强强度太大。<strong>没有这份分阶段统计，你只知道「留下了 30%」，不知道该改哪一步。</strong>",
        ),
        CALLOUT("danger", "<p>四类失效里<strong>③ 测试集泄漏最危险</strong>，因为它的症状是「评测分数变好」——这与你期望的结果一致，所以<em>不会引起任何警觉</em>。其他三类都会以某种方式让指标变差或不变，而污染让指标变<strong>好</strong>。这种「奖励错误行为」的失效模式在工程里是最难发现的一类。<strong>所以去污染检查必须是强制的、自动的、每次都跑的，而不是「想起来才做」的。</strong>指令层合成（模块 03）尤其危险，因为教师模型很可能在预训练时见过你的测试集。</p>", "污染让指标变好——所以它最危险"),
    ])),
    ("diversity", "多样性度量：三个视角，各有盲区", "".join([
        TABLE(["度量", "怎么算", "方向", "抓什么", "盲区"], [
            ["<strong>distinct-n</strong>", "不同 n-gram 数 ÷ 总 n-gram 数", "越高越多样", "词面重复", "对长度敏感（短文本天然更高）；只看局部"],
            ["<strong>self-BLEU</strong>", "每条与其余条的 n-gram 精确率均值", "<strong>越低越多样</strong>", "两两相似性", "O(n²) 需采样；对同义改写不敏感"],
            ["<strong>嵌入覆盖</strong>", "嵌入投影后占据的网格/凸包体积", "越高越广", "<strong>语义</strong>覆盖", "依赖嵌入质量；网格划分是人为的"],
            ["<strong>重复率</strong>", "完全相同或近重复的比例", "越低越好", "彻底无效的副本", "只抓最极端的情况"],
            ["<strong>类别/属性熵</strong>", "结构化属性（领域、标签、长度桶）的熵", "越高越均衡", "<strong>可解释的</strong>偏斜", "需要有结构化标注"],
        ]),
        DUAL(
            "为什么需要多个度量？因为<strong>每个都有能被「刷」的盲区</strong>。distinct-n 可以靠随机插入罕见词刷高（但那不是有用的多样性）；self-BLEU 对「换同义词但结构相同」不敏感；嵌入覆盖可以靠生成一些语义离群的垃圾刷高。<em>三个一起看，才能区分「真多样」与「刷出来的多样」</em>。",
            "但更重要的一点是<strong>多样性度量的正确用途</strong>：<em>它们不是用来评价「这批数据好不好」的绝对分数，而是用来</em>①<strong>比较两个增强方案</strong>（同一度量下 A vs B）与 ②<strong>监测趋势</strong>（同一方案逐代/逐批的变化）。<em>「distinct-2 = 0.45」这个绝对数字本身没有意义</em>——它取决于文本长度、词表、n 的取值。模块 00 已经演示过：完全随机的文本多样性最高、而作为训练数据毫无价值。<strong>多样性高 ≠ 有用。</strong>",
        ),
        CALLOUT("intuition", "把多样性度量的定位说得更直白：<strong>它们是「警报器」而不是「评分器」</strong>。你不该问「distinct-2 到多少才算好」，而该问「distinct-2 相对上一批降了多少」。模块 03 的坍塌四征兆就是这个用法——<em>趋势有意义，绝对值没有</em>。这也解释了为什么本课坚持三重检验：多样性只负责报警「数据在同质化」，有效性才负责回答「这批数据有用吗」。"),
    ])),
    ("contamination", "去污染：三层检测，从精确到语义", "".join([
        P("<span class=\"term\">contamination</span>（污染）指训练数据里混入了评测集的内容。增强场景下有三条污染路径："),
        UL([
            "<strong>直接泄漏</strong>：增强的源数据本身包含了测试集样本（划分前就增强了——<em>这是最常见也最愚蠢的错误</em>）。",
            "<strong>间接泄漏</strong>：增强产生了与测试集样本高度相似的文本（回译/释义可能把测试集的近邻造出来）。",
            "<strong>教师泄漏</strong>：LLM 教师在预训练时见过测试集，于是合成数据里出现了测试集的内容或答案。<em>这条路径你完全无法控制，只能检测。</em>",
        ]),
        TABLE(["检测层", "方法", "抓什么", "成本", "假阳性"], [
            ["<strong>① 精确匹配</strong>", "归一化后完全相同（去空格/标点/大小写）", "直接泄漏", "极低（哈希）", "几乎无"],
            ["<strong>② n-gram 重叠</strong>", "共享 ≥1 个 <code>n</code>-gram（<code>n</code>=8~13）或重叠比例超阈值", "间接泄漏、部分复制", "低（倒排索引）", "低（<code>n</code> 越大越低）"],
            ["<strong>③ 近重复检索</strong>", "MinHash/LSH 或嵌入近邻，相似度超阈值", "改写后的泄漏", "中", "中（需人工抽查）"],
        ]),
        DUAL(
            "<code>n</code> 的选择是个经典权衡：<code>n</code> 太小（如 4）会有大量假阳性（常见短语「这家店的服务」在任何餐饮语料里都出现）；<code>n</code> 太大（如 20）会漏掉部分改写。<strong>社区常用 8–13</strong>（GPT-3 用 13-gram，Lee et al. 2021 用 8-gram 的变体）。<em>关键是要在<strong>归一化后</strong>比对</em>——去掉标点、统一空格、小写化，否则「这家店，很好」与「这家店 很好」会被判为不同。",
            "还有一个常被忽略的细节：<strong>检测方向要双向</strong>。你不但要检查「增强数据是否包含测试集内容」，还要检查「<em>增强数据是否与训练集的其他样本重复</em>」——后者不是污染但是浪费（重复数据不提供信息，还会让模型对那部分过拟合，Lee et al. 2021 的核心结论）。<em>所以去污染与去重应该用同一套工具、同一次扫描完成</em>，只是比对的目标集合不同。",
        ),
        CALLOUT("warn", "一条必须写进流程的纪律：<strong>先划分数据集，再做任何增强</strong>。听起来是废话，但「先增强后划分」这个错误极其常见——因为增强脚本和划分脚本常常是分开写的，谁先跑取决于流水线的组织。<em>后果是同一条原样本的不同副本分别落进了训练集与测试集</em>，测试集实际上已经泄漏，而所有指标都会虚高。<strong>防护：把「增强只作用于训练集」写成一个断言，在增强脚本开头检查输入不含测试集 id。</strong>"),
    ])),
    ("pipeline", "组装成流水线：顺序、丢弃率与可追溯", "".join([
        ASCII("""            增强数据（来自模块 01/02/03）
                    │
    ┌───────────────▼────────────────┐
    │ ① 去污染（vs 测试集）          │  ← **必须第一个**，且不可跳过
    │    精确匹配 -> n-gram -> 近重复 │     因为它抓的是「让指标变好」的失效
    └───────────────┬────────────────┘  丢弃率高 => 教师见过你的测试集
    ┌───────────────▼────────────────┐
    │ ② 保真度（标签是否被破坏）      │  ← 零成本的规则检查在前
    │    关键成分 -> 规则标签 -> 模型  │     丢弃率高 => 增强强度太大
    └───────────────┬────────────────┘
    ┌───────────────▼────────────────┐
    │ ③ 去重（vs 训练集 + 增强内部）  │  ← 重复不是污染但是浪费
    │    精确 -> MinHash/相似度带      │     丢弃率高 => 生成器在同质化
    └───────────────┬────────────────┘
    ┌───────────────▼────────────────┐
    │ ④ 多样性与坍塌监测（不丢弃）     │  ← 只报警，不过滤
    │    distinct-n / self-BLEU / 覆盖 │     趋势下降 => 该混真实数据了
    └───────────────┬────────────────┘
                    ▼
              可用的增强数据 + 一份分阶段统计报告

每一步都记录：丢了多少条、为什么、样例。**这份报告比最终的保留率有用得多。**""")
        ,
        TABLE(["顺序", "为什么在这个位置"], [
            ["污染在最前", "它抓的是「让指标变好」的失效——最危险且最需要早发现；而且它的丢弃率是关于教师/数据来源的重要诊断"],
            ["保真度在污染之后", "它比污染便宜但不那么致命；先污染是因为「污染样本即使保真也不能用」"],
            ["去重在保真之后", "重复样本浪费算力但不致命；且没必要对已被丢弃的样本算去重"],
            ["多样性最后且不过滤", "它是<strong>报警器不是过滤器</strong>——你无法通过丢弃单条样本来提高整批的多样性"],
        ]),
        CALLOUT("intuition", "最后一行值得强调，因为它常被搞错：<strong>多样性是集合层面的属性，不能靠逐条过滤来改善</strong>。你可以丢掉「与已保留样本太像」的单条（那是去重），但「整批多样性不够」的解决办法是<em>改生成器</em>（提高温度、收紧去重阈值、加广度算子、混入真实数据），不是继续过滤。<em>把「过滤能解决的问题」与「只能靠改生成解决的问题」分清，能省掉很多无效的过滤器调参。</em>"),
    ])),
    ("collapse", "坍塌监测：把四个征兆做成看板", "".join([
        P("模块 03 演示了递归使用合成数据会坍塌，并给出四个早期征兆。这一节讲怎么把它<strong>工程化成一个持续运行的监测</strong>。"),
        TABLE(["征兆", "指标", "告警条件（示例）", "对应的动作"], [
            ["多样性下降", "distinct-2、唯一样本比", "相对上一批下降 &gt; 10%", "收紧去重阈值 / 提高生成温度"],
            ["长度分布收窄", "输出长度的标准差", "相对下降 &gt; 15%", "检查是否被教师的长度偏好主导"],
            ["高频模式占比上升", "最常见开头/句式/属性组合的占比", "相对上升 &gt; 10%", "加广度算子 / 换 few-shot 示例池"],
            ["语义覆盖收缩", "嵌入覆盖 / 聚类数", "相对下降 &gt; 10%", "<strong>混入更多真实数据</strong>"],
        ]),
        DUAL(
            "四个征兆里<strong>最后一个的动作最重要也最难接受</strong>：混入更多真实数据意味着「你需要去标注」，而这恰恰是你做合成数据想避免的事。<em>但这是坍塌唯一可靠的解药</em>（Shumailov et al. 2024）。所以正确的心态是：<strong>合成数据是真实数据的乘数，不是替代品</strong>——它能把 1000 条真实数据的价值放大到 3000 条的效果，但不能让你完全不要真实数据。",
            "工程上还要注意一个细节：<strong>告警要用「相对变化」而不是「绝对阈值」</strong>。因为多样性指标的绝对值取决于文本长度、词表、领域——同一个 <code>distinct-2 = 0.4</code> 在不同任务上含义完全不同。<em>相对变化才是可跨任务复用的信号</em>。这与 C48 模块 04 用 burn rate（相对 SLO 归一化）而非绝对错误率做告警是同一个思路：<strong>把指标归一化到「相对自己的基线」，告警规则才能复用。</strong>",
        ),
        CALLOUT("warn", "坍塌监测有个反直觉的时序问题：<strong>你必须在坍塌造成损害<em>之前</em>发现它，但那时下游指标还没变差</strong>。也就是说，<em>你要基于「内在指标恶化」而不是「下游指标恶化」来采取行动</em>——这需要一点纪律，因为「下游指标还好着呢，为什么要停下来加真实数据？」是很自然的反驳。<strong>这正是把四个征兆做成自动看板而不是「偶尔看一眼」的理由</strong>：让它变成流程的一部分，而不是每次都要论证的决定。"),
    ])),
    ("ledger", "算一笔账：分阶段丢弃率就是诊断报告", "".join([
        P("本模块最有价值的产出不是「保留了多少」，而是<strong>分阶段的丢弃率</strong>——它直接告诉你该改哪一步。"),
        TABLE(["观察到的现象", "诊断", "该做什么"], [
            ["<strong>污染阶段丢弃率 &gt; 1%</strong>", "教师模型见过你的测试集，或数据划分有问题", "换测试集 / 检查划分顺序 / 换教师"],
            ["污染阶段丢弃率 = 0 且检测很松", "可能是检测没生效（n 太大、忘了归一化）", "先用「故意注入的测试集样本」验证检测器本身"],
            ["<strong>保真阶段丢弃率 &gt; 20%</strong>", "增强强度太大（α 太高、温度太高、教师偏差大）", "降强度 / 加保护规则 / 换教师"],
            ["保真阶段丢弃率 ≈ 0", "增强太保守（可能等于没增强）", "看多样性——若也很低，说明白花了算力"],
            ["<strong>去重阶段丢弃率 &gt; 70%</strong>", "生成器在同质化（模式惯性）", "提高温度 / 加广度算子 / 换 few-shot 池"],
            ["多样性趋势连续 3 批下降", "开始坍塌", "<strong>混入真实数据</strong>"],
        ]),
        P("把这张表当成一张<strong>诊断流程图</strong>用：每次跑完增强管线，先看分阶段丢弃率，对照表格找到对应的动作。<em>这比盯着「最终保留了 35%」这个数字有用得多</em>——后者不告诉你该改什么。"),
        MATH("\\text{有效产出率} = \\prod_{i} (1 - d_i), \\qquad \\text{有效成本/可用条} = \\frac{c_{gen}}{\\prod_i (1-d_i)}"),
        P("这个乘积形式有一个重要含义：<strong>各阶段的丢弃率是乘起来的，所以任何一个阶段过严都会让总成本爆炸</strong>。三个阶段各丢 50%，总保留率只有 12.5%——成本是 8 倍。<em>所以「把每个过滤器都调到最严」是错的；应该让每个过滤器只挡它该挡的那类问题，且尽量减少假阳性。</em>"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>质量控制不是「算一个分数」，而是「一条记录了每一步为什么丢弃的流水线」</strong>——而那份分阶段的丢弃记录，比任何综合指标都更能告诉你该改什么。这条思路在数据工程（C43）、评测（C03/C10）、生产监控（C48）里是完全一样的：<em>可诊断性来自分解，不来自汇总</em>。"),
    ])),
    ("fidelity", "保真度检验：三层判据与「怎么为你的任务写一个」", "".join([
        P("多样性与污染前面讲过了，这里补上第三块：<strong>怎么自动判断「这条增强样本的标签还对不对」</strong>。真实任务里没有模块 00 那种规则可判定的标签，所以需要一套可落地的近似。"),
        TABLE(["层", "判据", "适用", "成本", "假阴（漏判）"], [
            ["<strong>① 结构不变量</strong>", "关键成分集合是否保持：否定词计数、实体集、数字集、标注 span 是否仍在", "所有任务", "<strong>几乎零</strong>", "抓不住「换了个近义词但语义变了」"],
            ["<strong>② 任务特定规则</strong>", "为你的任务手写的判定函数（如 NER：每个实体的类型与边界都在；QA：答案 span 逐字符仍在原文）", "结构化输出任务", "低", "规则覆盖不到的情形"],
            ["<strong>③ 模型一致性</strong>", "已训练模型对原样本与增强样本的预测是否一致（只在「明显相反且都自信」时才判失败）", "分类/排序", "中", "模型自己就错的样本"],
            ["<strong>④ 人工抽查</strong>", "每批随机抽 50–100 条人工判", "全部（作为前三层的校准）", "高", "—"],
        ]),
        DUAL(
            "第 ④ 层不是可选的，但它的用途常被误解：<strong>人工抽查不是用来「筛数据」的（量太小），而是用来<em>校准前三层</em>的</strong>。做法是：对同一批 100 条样本，同时记录自动判据的结论与人工结论，算出自动判据的假阳/假阴率。<em>知道了「我的自动检查漏掉了 15% 的破坏」，你才知道该把保真度门槛设在哪</em>——如果自动测出 0.98，真实可能只有 0.95。<strong>没有校准的自动判据，给出的数字不知道该怎么读。</strong>",
            "第 ③ 层的 confirmation bias 问题值得再强调一次（模块 02 提过）：<strong>用模型筛数据会系统性地保留「模型已经会的」样本</strong>，也就是信息量最低的那些。所以它<em>只能做硬过滤</em>（两边预测相反且都很自信 → 丢），<strong>绝不能做排序筛选</strong>（按一致性打分取 top-k）。后者会让增强数据退化成「模型的自我复述」，与模块 03 的模式坍塌是同一类问题的不同表现。",
        ),
        H3("为你的任务写一个判定函数：三个问题"),
        UL([
            "<strong>标签由输入的哪些部分决定？</strong> 把它们列出来 → 这就是「结构不变量」的检查清单（也是模块 01 的保护表）。",
            "<strong>什么改动一定会改标签？</strong> 写成断言（如「否定词数量改变 → 判失败」）。宁可保守（多丢一些），因为丢弃便宜、错标昂贵。",
            "<strong>什么改动一定不会改标签？</strong> 这些可以放行（如只插标点、只换确定的中性同义词）。<em>把它们显式列出来能提高保留率、降低成本。</em>",
        ]),
        CALLOUT("intuition", "这三个问题的顺序很重要：<strong>先想「什么一定会破坏」，再想「什么一定安全」，中间地带交给相似度带与人工抽查</strong>。很多人一上来就试图写一个「完美的判定函数」，结果卡在中间地带的模糊案例上。<em>而实际上两端的规则就能覆盖绝大多数样本，中间地带丢掉也不心疼</em>——因为生成新样本比精确判定单个样本便宜得多。这是「丢弃优于修正」在检验环节的又一次体现。"),
    ])),
    ("ops", "把质量控制变成流程：谁在什么时候跑它", "".join([
        P("前面讲的检测与流水线，只有变成<strong>默认执行的流程</strong>才有价值。一次性手动跑一遍、然后忘掉，等于没做——因为增强管线会被反复重跑（换教师、调参数、加数据），而每一次重跑都可能引入新问题。"),
        TABLE(["时机", "跑什么", "失败时做什么", "对应 C37/C48 的什么"], [
            ["<strong>增强脚本启动时</strong>", "<code>assert_no_test_ids()</code>：输入不含测试集", "<strong>直接崩</strong>（这是 bug 不是警告）", "前置断言"],
            ["<strong>每批增强产出后</strong>", "完整 QC 流水线 + 分阶段丢弃率 + 一行摘要", "丢弃率超阈值 → 阻断入库并告警", "CI 门禁（C37 模块 03）"],
            ["<strong>每次训练前</strong>", "抽一个 batch 打印检查（C50 模块 02 的四项检查）", "人工确认后才继续", "冒烟测试"],
            ["<strong>每代/每批之间</strong>", "坍塌看板的四个征兆（相对变化）", "告警 → 混入真实数据", "指标趋势告警（C48 模块 04）"],
            ["<strong>每次评测前</strong>", "重跑一次去污染（测试集可能换了）", "<strong>阻断评测</strong>", "评测门禁（C03/C10）"],
        ]),
        DUAL(
            "最后一行值得强调：<strong>去污染要在「每次评测前」而不是「每次增强后」重跑</strong>。因为测试集本身会变（换了评测基准、加了新的评测集、或者用了公开基准）——<em>今天干净的数据，换个测试集就可能是污染的</em>。把去污染绑定在「评测」这个动作上而不是「数据生成」上，才是正确的耦合方式。",
            "另一条流程设计原则：<strong>区分「阻断」与「告警」</strong>。污染与保真度是<em>阻断级</em>（数据不能入库，因为它会让所有后续结论失效）；多样性与坍塌是<em>告警级</em>（数据仍可用，但趋势不对需要人来决策）。<em>把两者混在一起，要么阻断太多导致流程被绕过（工程师会关掉检查），要么全是告警导致没人看</em>。这与 C48 模块 04 区分「自动回滚」与「人工告警」是同一个设计问题。",
        ),
        H3("一份最小可行的 QC 配置"),
        CODE("""qc:
  contamination:              # 阻断级
    enabled: true             # ← 永远不要关
    ngram_n: 8
    max_drop_rate: 0.01       # 超过 1% 说明教师见过测试集，阻断并人工查
  fidelity:                   # 阻断级
    min_rate: 0.98            # 硬门槛（模块 01 论证过为什么这么严）
    checks: [negation_count, entity_set, number_set, task_specific]
  dedup:                      # 阻断级（但阈值宽松）
    against: [test_set, train_set, within_batch]
    similarity: 0.85
  diversity:                  # 告警级
    metrics: [distinct_2, self_bleu_2, embedding_coverage]
    alert_on: relative_drop   # **相对变化**，不是绝对阈值
    threshold: 0.10
  collapse:                   # 告警级
    window: 3
    symptoms: [diversity, length_std, top_mode_share, coverage]
  human_audit:
    sample_per_batch: 50      # 用来**校准**自动判据，不是用来筛数据"""),
        CALLOUT("intuition", "这份配置里最容易被删掉的是 <code>human_audit</code>——因为它是唯一需要人的一项。但删掉它的后果是：<strong>你的所有自动指标都失去了标定</strong>，「保真度 0.98」这个数字不知道对应真实的多少。<em>每批 50 条、十分钟的人工抽查，换来的是「所有自动数字都可信」——这是整条流水线里投入产出比最高的一项</em>。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>多样性度量的可刷性</strong>：distinct-n、self-BLEU 都可以被针对性地刷高而不带来真实收益。<em>是否存在「不可刷」的多样性度量</em>（如与下游收益单调相关的）是个开放问题；目前只能靠多个度量交叉验证。",
            "<strong>去污染的语义层</strong>：n-gram 重叠抓不住「同一道题换个说法」。用嵌入近邻或 LLM 判断能抓到，但假阳性高且昂贵。<em>「什么程度的相似算污染」本身没有客观定义</em>——这与 C03 讲的基准污染是同一个开放问题。",
            "<strong>坍塌的可预测性</strong>：目前只能监测不能预测。「给定真实数据量、合成比例、代数，能否预测坍塌的时点」缺乏理论。Shumailov et al. 2024 给了简化模型但离可操作的预测还远。",
            "<strong>过滤器的联合优化</strong>：各阶段阈值是独立调的，但它们的效果不独立（严格的保真过滤会顺带提高多样性，因为破坏标签的样本往往也是离群的）。<em>联合调参的搜索空间大、且目标函数需要下游实验</em>，实践中几乎无人做。",
            "<strong>质量与数量的兑换率</strong>：「1000 条高质量 vs 5000 条含 10% 噪声」哪个更好？这在标注学习（learning with noisy labels）里有理论，但在增强数据的具体场景下缺乏可操作的判据。<em>本课的立场（保真度是硬门槛）是保守的，可能在某些任务上过于保守。</em>",
        ]),
        CALLOUT("paper", "必读：Li et al. 2016 <em>A Diversity-Promoting Objective Function for Neural Conversation Models</em>（distinct-n 的出处）、Zhu et al. 2018 <em>Texygen</em>（self-BLEU 的提出与多样性度量的系统讨论）、Lee et al. 2021 <em>Deduplicating Training Data Makes Language Models Better</em>（去重与去污染的方法与必要性，C43 模块 01/05 详读）、Shumailov et al. 2024 <em>AI models collapse…</em>（坍塌的机制）、Dodge et al. 2021 <em>Documenting Large Webtext Corpora</em>（数据文档与污染审计的实践）。相邻课程：C43（PB 级去重与去污染的工程实现）、C03/C10（基准污染与测量科学）、C14（合成数据与生成媒体评测）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 增强的质量控制（去污染 / 多样性度量 / 坍塌看板，组装成一条可诊断的流水线）

目标：把 **四类失效的检测**（保真、多样、污染、坍塌）实现成一条**按顺序执行、记录每步丢弃原因**的流水线，
并证明「分阶段丢弃率」比「最终保留率」有用得多。

路线：三个多样性度量与它们的盲区 → **多样性可以被刷高**（反例）→ 三层去污染检测 →
**先增强后划分的灾难**（可运行的反例）→ 组装流水线与分阶段统计 →
坍塌看板（相对变化告警）→ ✏️ 练习 → 📖 答案 → 🧪 诊断报告胶囊。

> 心智模型：**可诊断性来自分解，不来自汇总。** 分阶段的丢弃记录比任何综合指标都有用。"""),
    md("""## 0 · 数据与工具"""),
    code("""import numpy as np, math, collections, hashlib, re, itertools
rng = np.random.default_rng(0)

POS_WORDS = {'好吃', '不错', '推荐', '干净', '很好'}
NEG_WORDS = {'难吃', '差', '脏', '失望'}
NEGATORS  = {'不', '没', '别'}
NEUTRAL   = ['这家', '店', '的', '菜', '服务', '环境', '价格', '味道', '朋友',
             '我们', '昨天', '一起', '去', '吃', '了', '感觉', '整体']
RARE      = ['嗯', '呃', '啊', '哦', '唔', '嘿', '哈', '咦']      # 罕见词（用于刷多样性）

def rule_label(t, window=3):
    s = 0
    for i, w in enumerate(t):
        if w in POS_WORDS:
            neg = any(t[j] in NEGATORS for j in range(max(0, i-window), i))
            s += -1 if neg else 1
        elif w in NEG_WORDS:
            neg = any(t[j] in NEGATORS for j in range(max(0, i-window), i))
            s += 1 if neg else -1
    return 1 if s > 0 else 0

def make_sentence(r, length=10):
    t = list(r.choice(NEUTRAL, size=length-2, replace=True))
    p = int(r.integers(1, len(t)))
    t.insert(p, str(r.choice(sorted(POS_WORDS if r.random() < 0.5 else NEG_WORDS))))
    if r.random() < 0.4:
        t.insert(max(0, p - int(r.integers(1, 3))), str(r.choice(sorted(NEGATORS))))
    return t, rule_label(t)

def ngrams(t, n):
    return [tuple(t[i:i+n]) for i in range(len(t)-n+1)]

ALL = [make_sentence(np.random.default_rng(s)) for s in range(1200)]
TRAIN, TEST = ALL[:800], ALL[800:]          # ⚠️ 先划分，再增强（本模块会演示反例）
print(f'训练 {len(TRAIN)} 条, 测试 {len(TEST)} 条')
print('样例:', ' '.join(TRAIN[0][0]))"""),
    md("""## 1 · 三个多样性度量与它们的盲区

**每个度量都有能被「刷」的盲区** —— 所以要三个一起看。"""),
    code("""def distinct_n(texts, n=2):
    tot, uniq = 0, set()
    for t in texts:
        g = ngrams(t, n); tot += len(g); uniq.update(g)
    return len(uniq)/tot if tot else 0.0

def self_bleu(texts, n=2, sample=80, seed=0):
    '''越低越多样。O(n²) -> 采样。'''
    r = np.random.default_rng(seed)
    idx = r.choice(len(texts), size=min(sample, len(texts)), replace=False)
    scores = []
    for i in idx:
        gi = collections.Counter(ngrams(texts[i], n))
        if not gi: continue
        others = collections.Counter()
        for j in idx:
            if j != i: others.update(ngrams(texts[j], n))
        overlap = sum(min(c, others[g]) for g, c in gi.items())
        scores.append(overlap/sum(gi.values()))
    return float(np.mean(scores)) if scores else 0.0

VOCAB = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS | set(RARE))
_PROJ = np.random.default_rng(1).normal(size=(len(VOCAB), 24))
_V2I = {w: i for i, w in enumerate(VOCAB)}

def cheap_embed(t):
    v = np.zeros(24)
    for w in t:
        if w in _V2I: v += _PROJ[_V2I[w]]
    n = np.linalg.norm(v)
    return v/n if n > 0 else v

def embedding_coverage(texts, n_bins=10):
    E = np.stack([cheap_embed(t) for t in texts])[:, :2]
    lo, hi = E.min(0), E.max(0)
    span = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    cells = set(map(tuple, np.floor((E - lo)/span*(n_bins-1e-9)).astype(int)))
    return len(cells)/(n_bins*n_bins)

def dup_rate(texts):
    keys = [tuple(t) for t in texts]
    return 1 - len(set(keys))/len(keys)

def diversity_report(texts):
    return {'distinct-2': distinct_n(texts, 2), 'self-BLEU-2': self_bleu(texts, 2),
            '嵌入覆盖': embedding_coverage(texts), '重复率': dup_rate(texts)}

base = [t for t, _ in TRAIN]
dup4 = [t[:] for t in base[:200] for _ in range(4)]

def _inject(texts, k, seed=0):
    r = np.random.default_rng(seed); out = []
    for t in texts:
        s_ = list(t)
        for _ in range(k):
            s_.insert(int(r.integers(0, len(s_)+1)), str(r.choice(RARE)))
        out.append(s_)
    return out
rand_rare = _inject(base, 3, seed=2)      # 在原句里插入无意义语气词 -> 刷高 distinct-n

print(f"{'语料':<18s} {'distinct-2':>11s} {'self-BLEU':>10s} {'嵌入覆盖':>9s} {'重复率':>8s}")
for name, ts in [('原始训练集', base), ('4× 复制', dup4), ('插入罕见词', rand_rare)]:
    r_ = diversity_report(ts)
    print(f'{name:<18s} {r_["distinct-2"]:>11.4f} {r_["self-BLEU-2"]:>10.4f} '
          f'{r_["嵌入覆盖"]:>9.3f} {r_["重复率"]:>8.1%}')

rb, rd, rr = diversity_report(base), diversity_report(dup4), diversity_report(rand_rare)
assert rd['重复率'] > 0.7, '4× 复制的重复率应很高'
assert rd['self-BLEU-2'] > rb['self-BLEU-2'], '复制让 self-BLEU 升高（更不多样）'
assert rr['distinct-2'] > rb['distinct-2'], '插入罕见词就能刷高 distinct-n —— 但它毫无价值'
print('\\n✅ 三个度量方向一致，但**只是插入无意义语气词就能让 distinct-2 最高**——')
print('   这正是「多样性高 ≠ 有用」。所以多样性只能当**警报器**，不能当评分器。')"""),
    md("""### 多样性是可以被「刷」的：一个可运行的反例

在每条样本里插入几个罕见词，distinct-n 立刻上升——**而这不带来任何真实收益**。"""),
    code("""def inject_rare(texts, k, seed=0):
    r = np.random.default_rng(seed)
    out = []
    for t in texts:
        s = list(t)
        for _ in range(k):
            s.insert(int(r.integers(0, len(s)+1)), str(r.choice(RARE)))
        out.append(s)
    return out

print(f"{'插入罕见词数':>13s} {'distinct-2':>11s} {'self-BLEU':>10s} {'嵌入覆盖':>9s}")
for k in [0, 1, 2, 4]:
    ts = inject_rare(base, k, seed=3)
    r_ = diversity_report(ts)
    print(f'{k:>13d} {r_["distinct-2"]:>11.4f} {r_["self-BLEU-2"]:>10.4f} {r_["嵌入覆盖"]:>9.3f}')

d0 = distinct_n(base, 2)
d4 = distinct_n(inject_rare(base, 4, seed=3), 2)
assert d4 > d0 * 1.1, '插入罕见词能显著刷高 distinct-n'
print(f'\\n⚠️  只是插入无意义的语气词，distinct-2 就从 {d0:.4f} 升到 {d4:.4f}（+{(d4/d0-1):.0%}）。')
print('   **标签没变、信息量没变、下游收益没变** —— 纯粹是指标被刷了。')
print('✅ 这就是「多个度量交叉验证」的必要性，也是「只看趋势不看绝对值」的理由。')"""),
    md("""## 2 · 三层去污染检测

① 精确匹配（归一化后）→ ② n-gram 重叠（n=8~13）→ ③ 近重复检索。
**归一化是关键**：否则「这家店，很好」与「这家店 很好」会被判为不同。"""),
    code("""def normalize(tokens):
    '''归一化：去标点、统一空格、小写。**不归一化的检测几乎无效。**'''
    s = ' '.join(tokens).lower()
    s = re.sub(r'[，。！？、,.!?;：:]', ' ', s)
    return tuple(s.split())

def exact_index(texts):
    return {hashlib.sha1(' '.join(normalize(t)).encode()).hexdigest() for t in texts}

def exact_hit(t, index):
    return hashlib.sha1(' '.join(normalize(t)).encode()).hexdigest() in index

def ngram_index(texts, n=8):
    idx = set()
    for t in texts:
        idx.update(ngrams(normalize(t), n))
    return idx

def ngram_hit(t, idx, n=8, min_overlap=1):
    g = ngrams(normalize(t), n)
    if not g: return False
    return sum(1 for x in g if x in idx) >= min_overlap

def minhash_sig(t, k=32, seed=0):
    r = np.random.default_rng(seed)
    a = r.integers(1, 2**31-1, size=k); b = r.integers(0, 2**31-1, size=k)
    gs = ngrams(normalize(t), 3) or [tuple(normalize(t))]
    xs = np.array([int(hashlib.sha1(str(g).encode()).hexdigest()[:8], 16) for g in gs])
    return ((np.outer(xs, a) + b) % (2**31-1)).min(axis=0)

def minhash_sim(s1, s2):
    return float((s1 == s2).mean())

def near_dup_hit(t, sigs, thresh=0.7):
    s = minhash_sig(t)
    return any(minhash_sim(s, s2) >= thresh for s2 in sigs)

test_texts = [t for t, _ in TEST]
EXACT_IDX = exact_index(test_texts)
NGRAM_IDX = ngram_index(test_texts, n=8)
TEST_SIGS = [minhash_sig(t) for t in test_texts[:150]]

# 先验证检测器本身有效：故意注入测试集样本
injected = test_texts[:5]
print('注入 5 条测试集样本，看三层检测能否抓到:')
for i, t in enumerate(injected):
    print(f'  #{i}: 精确={exact_hit(t, EXACT_IDX)} '
          f'n-gram={ngram_hit(t, NGRAM_IDX)} 近重复={near_dup_hit(t, TEST_SIGS)}')
assert all(exact_hit(t, EXACT_IDX) for t in injected), '精确匹配必须抓到原样注入'
# 干净的训练样本不该被误报
fp = sum(1 for t in base[:200] if exact_hit(t, EXACT_IDX))
print(f'\\n干净训练样本的精确匹配假阳性: {fp}/200')
assert fp == 0, '精确匹配应无假阳性'
print('✅ 先用「故意注入」验证检测器本身 —— 否则你不知道「0 命中」是安全还是检测失效。')"""),
    code("""# n 的选择：太小假阳性高，太大漏检改写
print(f"{'n':>4s} {'注入样本检出率':>15s} {'干净样本假阳性率':>17s}")
for n in [3, 5, 8, 13]:
    idx = ngram_index(test_texts, n=n)
    tp = np.mean([ngram_hit(t, idx, n=n) for t in test_texts[:100]])
    fp_ = np.mean([ngram_hit(t, idx, n=n) for t in base[:300]])
    print(f'{n:>4d} {tp:>15.1%} {fp_:>17.1%}')

idx3 = ngram_index(test_texts, n=3)
idx13 = ngram_index(test_texts, n=13)
fp3 = np.mean([ngram_hit(t, idx3, n=3) for t in base[:300]])
fp13 = np.mean([ngram_hit(t, idx13, n=13) for t in base[:300]])
assert fp3 > fp13, 'n 越小假阳性越高'
print(f'\\n✅ n=3 的假阳性 {fp3:.1%} vs n=13 的 {fp13:.1%}。社区常用 8-13。')

# 不归一化的后果
def naive_hit(t, texts):
    return ' '.join(t) in {' '.join(x) for x in texts}
punct_variant = [list(t) + ['。'] for t in test_texts[:50]]      # 只多了一个标点
naive_caught = np.mean([naive_hit(t, test_texts) for t in punct_variant])
norm_caught = np.mean([exact_hit(t, EXACT_IDX) for t in punct_variant])
print(f'\\n只多一个标点的测试集变体: 不归一化检出 {naive_caught:.0%} | 归一化检出 {norm_caught:.0%}')
assert norm_caught > naive_caught, '归一化是去污染的前提'
print('✅ **归一化是前提**，不归一化的检测几乎无效。')"""),
    md("""## 3 · 「先增强后划分」的灾难：一个可运行的反例

这个错误极其常见（增强脚本与划分脚本分开写，谁先跑取决于流水线组织），
后果是**同一条原样本的副本分落训练与测试集**，所有指标虚高。"""),
    code("""def simple_augment(data, n_aug=3, seed=0):
    '''一个温和的增强：只替换中性词。'''
    SYN = {'这家': '本', '店': '餐厅', '菜': '菜品', '服务': '服务员', '环境': '氛围'}
    r = np.random.default_rng(seed)
    out = []
    for t, y in data:
        for _ in range(n_aug):
            out.append(([SYN.get(w, w) if (w in SYN and r.random() < 0.6) else w
                         for w in t], y))
    return out

# ❌ 错误顺序：先增强，再划分
all_aug = list(ALL) + simple_augment(ALL, 3, seed=5)
r_ = np.random.default_rng(7)
perm = r_.permutation(len(all_aug))
split = int(len(all_aug)*0.7)
bad_train = [all_aug[i] for i in perm[:split]]
bad_test = [all_aug[i] for i in perm[split:]]

# ✅ 正确顺序：先划分，再只增强训练集
good_train = list(TRAIN) + simple_augment(TRAIN, 3, seed=5)
good_test = list(TEST)

def leak_rate(train_data, test_data, n=8):
    idx = ngram_index([t for t, _ in test_data], n=n)
    return float(np.mean([ngram_hit(t, idx, n=n) for t, _ in train_data]))

lr_bad = leak_rate(bad_train, bad_test)
lr_good = leak_rate(good_train, good_test)
print(f'❌ 先增强后划分: 训练集里有 {lr_bad:.1%} 的样本与测试集共享 8-gram')
print(f'✅ 先划分后增强: {lr_good:.1%}')
assert lr_bad > lr_good * 3, '先增强后划分会造成大规模泄漏'
print('\\n⚠️  而且这个泄漏会让评测分数**虚高** —— 与你期望的结果一致，所以不会引起警觉。')
print('✅ 防护：把「增强只作用于训练集」写成断言，在增强脚本开头检查输入不含测试集 id。')"""),
    code("""def assert_no_test_ids(inputs_ids, test_ids):
    '''把纪律写成断言 —— 放在每个增强脚本的开头。'''
    overlap = set(inputs_ids) & set(test_ids)
    assert not overlap, f'增强输入包含 {len(overlap)} 个测试集样本！先划分再增强。'
    return True

train_ids = list(range(len(TRAIN)))
test_ids = list(range(len(TRAIN), len(ALL)))
assert assert_no_test_ids(train_ids, test_ids)
try:
    assert_no_test_ids(list(range(len(ALL))), test_ids)
    raise RuntimeError('不该到这')
except AssertionError as e:
    print(f'✅ 断言拦住了: {e}')"""),
    md("""## 4 · 组装流水线：顺序、丢弃率、可追溯

**① 去污染（最前、不可跳过）→ ② 保真度 → ③ 去重 → ④ 多样性监测（只报警不过滤）**"""),
    code("""def key_component_check(orig, aug):
    def negc(t): return sum(1 for w in t if w in NEGATORS)
    return negc(orig) == negc(aug)

def qc_pipeline(aug_pairs, test_texts, train_texts,
                ngram_n=8, dup_thresh=0.85, verbose=True):
    '''aug_pairs: [(原tokens, 标签, 增强tokens)]。返回 (通过的, 分阶段报告)。'''
    exact_idx = exact_index(test_texts)
    ng_idx = ngram_index(test_texts, n=ngram_n)
    train_keys = {tuple(normalize(t)) for t in train_texts}
    seen = set()
    report = collections.Counter()
    samples = collections.defaultdict(list)
    kept = []
    for orig, y, aug in aug_pairs:
        report['输入'] += 1
        # ① 去污染（vs 测试集）
        if exact_hit(aug, exact_idx):
            report['①污染-精确'] += 1; samples['①污染-精确'].append(aug); continue
        if ngram_hit(aug, ng_idx, n=ngram_n):
            report['①污染-ngram'] += 1; samples['①污染-ngram'].append(aug); continue
        # ② 保真度
        if not key_component_check(orig, aug):
            report['②保真-关键成分'] += 1; samples['②保真-关键成分'].append(aug); continue
        if rule_label(aug) != y:
            report['②保真-标签翻转'] += 1; samples['②保真-标签翻转'].append(aug); continue
        # ③ 去重（vs 训练集 + 增强内部）
        k = tuple(normalize(aug))
        if k in train_keys:
            report['③去重-与训练集重复'] += 1; continue
        if k in seen:
            report['③去重-增强内部重复'] += 1; continue
        seen.add(k); kept.append((aug, y)); report['通过'] += 1
    # ④ 多样性监测（不过滤，只报警）
    div = diversity_report([t for t, _ in kept]) if kept else {}
    if verbose:
        print(f'{"阶段":<22s} {"丢弃数":>7s} {"占输入":>8s}')
        for k_, v in report.items():
            if k_ in ('输入', '通过'): continue
            print(f'{k_:<22s} {v:>7d} {v/report["输入"]:>8.1%}')
        print(f'{"通过":<22s} {report["通过"]:>7d} {report["通过"]/report["输入"]:>8.1%}')
        print(f'\\n④ 多样性监测（不过滤）: '
              f'distinct-2={div.get("distinct-2",0):.4f}, '
              f'self-BLEU={div.get("self-BLEU-2",0):.4f}, 覆盖={div.get("嵌入覆盖",0):.3f}')
    return kept, report, div, samples

# 构造一批「有各种问题」的增强数据
def messy_augment(data, test_texts, seed=0):
    r = np.random.default_rng(seed)
    out = []
    SYN = {'这家': '本', '店': '餐厅', '菜': '菜品'}
    for t, y in data:
        out.append(([SYN.get(w, w) for w in t], y, [SYN.get(w, w) for w in t]))  # 正常
        out.append((t, y, [w for w in t if w not in NEGATORS or r.random() > 0.5]))  # 可能丢否定
        out.append((t, y, list(t)))                                              # 与训练集重复
    for tt in test_texts[:8]:
        out.append((tt, rule_label(tt), list(tt)))                               # 污染
    return [(o, y, a) for o, y, a in out]

messy = messy_augment(TRAIN[:200], test_texts, seed=11)
kept, rep, div, samp = qc_pipeline(messy, test_texts, [t for t, _ in TRAIN])
assert rep['①污染-精确'] + rep['①污染-ngram'] >= 8, '注入的污染样本必须被抓到'
assert rep['②保真-标签翻转'] + rep['②保真-关键成分'] > 0, '丢否定词的样本应被保真检查抓到'
assert rep['③去重-与训练集重复'] > 0, '与训练集相同的副本应被去重'
print('\\n✅ 四个阶段各自抓到了它该抓的问题，且每一步都有记录与样例。')"""),
    md("""### 分阶段丢弃率就是诊断报告"""),
    code("""DIAGNOSIS = [
    (lambda r: (r['①污染-精确'] + r['①污染-ngram'])/r['输入'] > 0.01,
     '污染丢弃 >1%', '教师见过你的测试集，或数据划分有问题 -> 换测试集/检查划分顺序'),
    (lambda r: (r['②保真-关键成分'] + r['②保真-标签翻转'])/r['输入'] > 0.20,
     '保真丢弃 >20%', '增强强度太大 -> 降 α/温度、加保护规则、换教师'),
    (lambda r: (r['②保真-关键成分'] + r['②保真-标签翻转'])/r['输入'] < 0.001,
     '保真丢弃 ≈0', '增强可能太保守（等于没增强）-> 看多样性是否也很低'),
    (lambda r: (r['③去重-与训练集重复'] + r['③去重-增强内部重复'])/r['输入'] > 0.70,
     '去重丢弃 >70%', '生成器在同质化 -> 提高温度、加广度算子、换 few-shot 池'),
]

def diagnose(report):
    return [(name, action) for cond, name, action in DIAGNOSIS if cond(report)]

print('诊断结果:')
for name, action in diagnose(rep):
    print(f'  ⚠️  {name}: {action}')
found = diagnose(rep)
assert found, '这批 messy 数据应触发至少一条诊断'
print(f'\\n最终保留率 {rep["通过"]/rep["输入"]:.1%} —— 但**这个数字不告诉你该改什么**。')
print('✅ 分阶段丢弃率才是诊断报告。这就是「可诊断性来自分解，不来自汇总」。')

# 各阶段丢弃率是**乘起来**的：任何一个过严都会让总成本爆炸
print(f'\\n{"各阶段保留率":>14s} {"总保留率":>9s} {"相对成本":>9s}')
for rates in [(0.99, 0.95, 0.90), (0.95, 0.80, 0.60), (0.90, 0.50, 0.50)]:
    prod = float(np.prod(rates))
    print(f'{str(rates):>14s} {prod:>9.1%} {1/prod:>9.1f}×')
assert abs(np.prod((0.9, 0.5, 0.5)) - 0.225) < 1e-9
print('\\n✅ 三个阶段各丢一半 -> 总保留率 12.5% -> 成本 8 倍。')
print('   **别把每个过滤器都调到最严**；让每个只挡它该挡的，并尽量减少假阳性。')"""),
    md("""## 5 · 坍塌看板：用「相对变化」而不是「绝对阈值」告警

绝对值取决于长度/词表/领域，**相对变化才是可跨任务复用的信号**
（与 C48 用 burn rate 而非绝对错误率告警是同一思路）。"""),
    code("""def batch_metrics(texts):
    d = diversity_report(texts)
    lens = [len(t) for t in texts]
    top = collections.Counter(tuple(t[:2]) for t in texts).most_common(1)
    return {'distinct-2': d['distinct-2'],
            '长度标准差': float(np.std(lens)),
            '最高频开头占比': (top[0][1]/len(texts)) if top else 0.0,
            '嵌入覆盖': d['嵌入覆盖']}

ALERT_RULES = [
    ('distinct-2',      'down', 0.10),
    ('长度标准差',       'down', 0.15),
    ('最高频开头占比',   'up',   0.10),
    ('嵌入覆盖',        'down', 0.10),
]

def collapse_dashboard(history, window=3):
    '''对比 window 代前与最新一代的**相对变化**。'''
    if len(history) < 2: return []
    a = history[max(0, len(history)-window-1)]
    b = history[-1]
    alerts = []
    for key, direction, thresh in ALERT_RULES:
        if a[key] <= 0: continue
        rel = (a[key]-b[key])/a[key] if direction == 'down' else (b[key]-a[key])/a[key]
        if rel > thresh:
            alerts.append(f'{key}{"↓" if direction=="down" else "↑"} {rel:.0%}')
    return alerts

def simulate_generations(n_gen=6, size=300, real_ratio=0.0, seed=0):
    '''模拟递归生成：模式惯性随同质化上升（正反馈）。'''
    r = np.random.default_rng(seed)
    real = [make_sentence(np.random.default_rng(9000+i))[0] for i in range(size)]
    cur, hist, inertia = list(real), [], 0.1
    for g in range(n_gen):
        n_syn = int(size*(1-real_ratio))
        syn = []
        for _ in range(n_syn):
            if r.random() < inertia:
                syn.append(list(cur[int(r.integers(0, len(cur)))]))      # 直接抄（坍塌）
            else:
                base_t = list(cur[int(r.integers(0, len(cur)))])
                if len(base_t) > 3 and r.random() < 0.5:
                    base_t[int(r.integers(0, len(base_t)))] = str(r.choice(NEUTRAL))
                syn.append(base_t)
        fresh = [real[int(r.integers(0, len(real)))] for _ in range(size-n_syn)]
        cur = syn + fresh
        hist.append(batch_metrics(cur))
        uniq = len({tuple(t) for t in cur})/len(cur)
        inertia = min(0.95, inertia + 0.5*(1-uniq))
    return hist

print('=== 纯合成（不混真实数据）===')
h0 = simulate_generations(6, real_ratio=0.0, seed=13)
print(f"{'代':>3s} {'distinct-2':>11s} {'长度σ':>7s} {'最高频开头':>11s} {'覆盖':>7s} {'告警':<30s}")
for i, m in enumerate(h0, 1):
    al = collapse_dashboard(h0[:i])
    print(f'{i:>3d} {m["distinct-2"]:>11.4f} {m["长度标准差"]:>7.2f} '
          f'{m["最高频开头占比"]:>11.1%} {m["嵌入覆盖"]:>7.3f} {", ".join(al):<30s}')

assert collapse_dashboard(h0), '纯合成 6 代应触发告警'
h5 = simulate_generations(6, real_ratio=0.5, seed=13)
print(f'\\n混 50% 真实数据的告警: {collapse_dashboard(h5)}')
assert len(collapse_dashboard(h5)) <= len(collapse_dashboard(h0)), '混真实数据应减少告警'
print('\\n✅ 用相对变化告警 -> 规则可跨任务复用（与 C48 的 burn rate 同一思路）。')
print('   ⚠️ 注意告警出现时**下游指标可能还没变差** —— 这正是它的价值，也需要一点纪律。')"""),
    md("""## ✏️ 练习 1：双向去重/去污染

实现 `scan_overlap(candidates, reference_texts, n=8)`：返回
`{'exact':…, 'ngram':…, 'clean':…}` 三个列表（分别是精确命中、仅 n-gram 命中、干净的候选）。
注意一个候选只能落在一个桶里（精确优先）。"""),
    code("""def scan_overlap(candidates, reference_texts, n=8):
    # TODO: 建 exact_index 与 ngram_index；对每个候选分桶
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
cands = test_texts[:5] + [list(t) + ['嗯'] for t in test_texts[5:10]] + base[:20]
res = scan_overlap(cands, test_texts, n=8)
assert len(res['exact']) + len(res['ngram']) + len(res['clean']) == len(cands)
assert len(res['exact']) >= 5, '原样注入的应被精确匹配抓到'
assert len(res['clean']) >= 15, '干净的训练样本应通过'
print(f'精确命中 {len(res["exact"])} | 仅 n-gram 命中 {len(res["ngram"])} | 干净 {len(res["clean"])}')
# 同一套工具换比对目标就是去重（vs 训练集）而不是去污染（vs 测试集）
res2 = scan_overlap(base[:50], base, n=8)
assert len(res2['clean']) == 0, '与自己比对时全部命中 —— 说明工具是通用的'
print('✅ 练习 1 通过：**去污染与去重用同一套工具**，只是比对目标不同')"""),
    md("""## ✏️ 练习 2：流水线报告的诊断

实现 `qc_diagnose(report)`：给定 `qc_pipeline` 的 report（Counter），
返回 `[(问题, 建议)]`。至少覆盖：污染>1%、保真>20%、去重>70%、通过率<10%。"""),
    code("""def qc_diagnose(report):
    # TODO: 用 report['输入'] 做分母算各阶段占比；按阈值返回 (问题, 建议)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r_bad = collections.Counter({'输入': 1000, '①污染-精确': 30, '①污染-ngram': 5,
                             '②保真-标签翻转': 250, '②保真-关键成分': 20,
                             '③去重-与训练集重复': 100, '③去重-增强内部重复': 50,
                             '通过': 545})
d = qc_diagnose(r_bad)
names = [x[0] for x in d]
print('诊断:')
for n_, a_ in d: print(f'  ⚠️  {n_}: {a_}')
assert any('污染' in n_ for n_ in names), '污染 3.5% > 1% 应告警'
assert any('保真' in n_ for n_ in names), '保真 27% > 20% 应告警'
r_ok = collections.Counter({'输入': 1000, '①污染-精确': 0, '①污染-ngram': 2,
                            '②保真-标签翻转': 30, '②保真-关键成分': 10,
                            '③去重-与训练集重复': 50, '③去重-增强内部重复': 60,
                            '通过': 848})
assert len(qc_diagnose(r_ok)) < len(d), '健康的报告应更少告警'
print(f'\\n健康报告的告警数 {len(qc_diagnose(r_ok))} < 问题报告的 {len(d)}')
print('✅ 练习 2 通过：把「分阶段丢弃率 -> 该改什么」写成代码，每次跑完自动出诊断')"""),
    md("""## ✏️ 练习 3：有效成本与过滤器松紧

实现 `pipeline_cost(stage_keep_rates, gen_cost_per_item)`：
返回 `{'total_keep_rate':…, 'cost_per_usable':…}`。
再实现 `loosest_feasible(stage_options, min_total_keep)`：
`stage_options` 是 `[[(阈值, 保留率), …], …]`（每阶段的候选），
返回让**总保留率 ≥ min_total_keep** 且各阶段阈值尽量严（保留率乘积最小但仍达标）的组合；无解返回 `None`。"""),
    code("""def pipeline_cost(stage_keep_rates, gen_cost_per_item):
    # TODO
    raise NotImplementedError

def loosest_feasible(stage_options, min_total_keep):
    # TODO: 枚举所有组合；在总保留率 >= min_total_keep 的组合里，
    #       返回**总保留率最小**的那个（即过滤最严但仍达标），形如 [(阈值, 保留率), ...]
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
c = pipeline_cost([0.99, 0.80, 0.60], gen_cost_per_item=0.001)
assert abs(c['total_keep_rate'] - 0.4752) < 1e-6
assert abs(c['cost_per_usable'] - 0.001/0.4752) < 1e-9
print(f'三阶段保留率 (0.99, 0.80, 0.60) -> 总 {c["total_keep_rate"]:.1%}, '
      f'每可用条 ${c["cost_per_usable"]:.6f}')

opts = [[(0.5, 0.95), (0.7, 0.99)],          # 污染阈值
        [(0.90, 0.70), (0.98, 0.85)],        # 保真阈值
        [(0.7, 0.55), (0.85, 0.80)]]         # 去重阈值
best = loosest_feasible(opts, min_total_keep=0.40)
assert best is not None
prod = float(np.prod([kr for _, kr in best]))
assert prod >= 0.40 - 1e-9
print(f'总保留率 ≥ 40% 的最严组合: {[th for th, _ in best]} -> 总保留率 {prod:.1%}')
assert loosest_feasible(opts, 0.95) is None, '要求过高时无解'
print('✅ 练习 3 通过：各阶段保留率是**乘起来**的 —— 任何一个过严都会让成本爆炸')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def scan_overlap(candidates, reference_texts, n=8):
    eidx = exact_index(reference_texts)
    nidx = ngram_index(reference_texts, n=n)
    out = {'exact': [], 'ngram': [], 'clean': []}
    for t in candidates:
        if exact_hit(t, eidx):      out['exact'].append(t)
        elif ngram_hit(t, nidx, n): out['ngram'].append(t)
        else:                       out['clean'].append(t)
    return out"""),
    code("""# 练习 2 参考答案
def qc_diagnose(report):
    n = max(1, report['输入'])
    contam = (report['①污染-精确'] + report['①污染-ngram'])/n
    fid = (report['②保真-关键成分'] + report['②保真-标签翻转'])/n
    dedup = (report['③去重-与训练集重复'] + report['③去重-增强内部重复'])/n
    passed = report['通过']/n
    out = []
    if contam > 0.01:
        out.append((f'污染丢弃 {contam:.1%} >1%', '教师见过测试集或划分有问题 -> 换测试集/检查划分顺序'))
    if fid > 0.20:
        out.append((f'保真丢弃 {fid:.1%} >20%', '增强强度太大 -> 降 α/温度、加保护规则'))
    if fid < 0.001:
        out.append((f'保真丢弃 {fid:.2%} ≈0', '增强可能太保守 -> 检查多样性是否也很低'))
    if dedup > 0.70:
        out.append((f'去重丢弃 {dedup:.1%} >70%', '生成器同质化 -> 提高温度/加广度算子'))
    if passed < 0.10:
        out.append((f'通过率 {passed:.1%} <10%', '过滤器整体过严 -> 成本会爆炸，逐个放松'))
    return out"""),
    code("""# 练习 3 参考答案
def pipeline_cost(stage_keep_rates, gen_cost_per_item):
    total = float(np.prod(stage_keep_rates))
    return {'total_keep_rate': total,
            'cost_per_usable': gen_cost_per_item/total if total > 0 else float('inf')}

def loosest_feasible(stage_options, min_total_keep):
    best = None
    for combo in itertools.product(*stage_options):
        prod = float(np.prod([kr for _, kr in combo]))
        if prod >= min_total_keep:
            if best is None or prod < best[0]:
                best = (prod, list(combo))
    return None if best is None else best[1]"""),
    md("""---
## 🧪 真实数据胶囊：一份完整的 QC 诊断报告

把本模块的一切串成一个「每次跑增强都输出」的报告。这就是本模块的交付物。"""),
    code("""def full_qc_report(aug_pairs, test_texts, train_texts, history=None):
    kept, rep, div, samples = qc_pipeline(aug_pairs, test_texts, train_texts, verbose=False)
    n = max(1, rep['输入'])
    print('=' * 66)
    print('增强数据质量控制报告')
    print('=' * 66)
    print(f'\\n【输入】{rep["输入"]} 条增强样本\\n')
    print('【分阶段丢弃】')
    for k in ['①污染-精确', '①污染-ngram', '②保真-关键成分', '②保真-标签翻转',
              '③去重-与训练集重复', '③去重-增强内部重复']:
        v = rep[k]
        bar = '█' * int(v/n*40)
        print(f'  {k:<22s} {v:>6d} ({v/n:>5.1%}) {bar}')
    print(f'  {"通过":<22s} {rep["通过"]:>6d} ({rep["通过"]/n:>5.1%})')
    print('\\n【多样性监测（不过滤，只报警）】')
    for k, v in div.items():
        print(f'  {k:<16s} {v:.4f}')
    if history:
        al = collapse_dashboard(history)
        print(f'\\n【坍塌看板】{"、".join(al) if al else "无告警 ✅"}')
    print('\\n【诊断与建议】')
    diag = qc_diagnose(rep)
    if diag:
        for name, action in diag:
            print(f'  ⚠️  {name}\\n      -> {action}')
    else:
        print('  ✅ 各阶段丢弃率均在正常范围')
    print('\\n【被丢弃的样例（用于人工抽查）】')
    for k in ['①污染-精确', '②保真-标签翻转']:
        if samples[k]:
            print(f'  {k}: {" ".join(samples[k][0])}')
    print('=' * 66)
    return kept, rep, div

kept_f, rep_f, div_f = full_qc_report(messy, test_texts, [t for t, _ in TRAIN], history=h0)
assert rep_f['输入'] == len(messy)
assert len(kept_f) == rep_f['通过']
print(f'\\n✅ 报告生成完毕。**把这份报告写进你的增强脚本的输出**——')
print('   它比「最终保留了 X%」有用得多，因为它直接告诉你该改哪一步。')"""),
    md("""**🧪 胶囊练习**：实现 `qc_summary_line(report, div)`：把报告压缩成**一行**可写进日志的摘要，
格式 `in=N keep=X% contam=X% fid=X% dup=X% d2=X.XXXX`（百分比保留一位小数）。
这一行是给自动化流水线/看板用的。"""),
    code("""def qc_summary_line(report, div):
    # TODO: 返回形如 'in=1000 keep=54.5% contam=3.5% fid=27.0% dup=15.0% d2=0.4123' 的字符串
    raise NotImplementedError"""),
    code("""# 自测
line = qc_summary_line(rep_f, div_f)
print(line)
assert line.startswith('in=') and 'keep=' in line and 'contam=' in line
assert 'fid=' in line and 'dup=' in line and 'd2=' in line
# 可解析性：能被 split 成键值对
kv = dict(p.split('=') for p in line.split())
assert set(kv) == {'in', 'keep', 'contam', 'fid', 'dup', 'd2'}
assert int(kv['in']) == rep_f['输入']
print('\\n✅ 胶囊练习通过：一行摘要用于日志与看板，完整报告用于人工诊断。')
print('   把摘要行接进 C37 的实验追踪，你就有了「增强数据质量」的时间序列。')"""),
    code("""# 📖 胶囊参考答案
def qc_summary_line(report, div):
    n = max(1, report['输入'])
    contam = (report['①污染-精确'] + report['①污染-ngram'])/n
    fid = (report['②保真-关键成分'] + report['②保真-标签翻转'])/n
    dup = (report['③去重-与训练集重复'] + report['③去重-增强内部重复'])/n
    return (f'in={report["输入"]} keep={report["通过"]/n*100:.1f}% '
            f'contam={contam*100:.1f}% fid={fid*100:.1f}% dup={dup*100:.1f}% '
            f'd2={div.get("distinct-2", 0.0):.4f}')"""),
    md("""### 小结
- **四类失效互相独立**：保真、多样、污染、坍塌。①好不代表②好（复制原样本保真 100% 多样性零）；②好不代表③好。
- **多样性度量是警报器不是评分器**：绝对值取决于长度/词表/领域；而且**可以被刷**（插入罕见词就能拉高 distinct-n）。只看趋势、多度量交叉。
- **去污染必须第一个跑且不可跳过**，因为它抓的是唯一「让指标变好」的失效——不会引起警觉。归一化是前提；n=8–13；**先用故意注入验证检测器本身**。
- **「先增强后划分」是常见灾难**（已可运行地复现）。把「增强只作用于训练集」写成断言。
- **去污染与去重用同一套工具**，只是比对目标不同。
- **流水线顺序**：污染 → 保真 → 去重 → 多样性监测（**只报警不过滤**，因为多样性是集合属性，不能靠逐条过滤改善）。
- **分阶段丢弃率就是诊断报告**：污染>1% → 教师见过测试集；保真>20% → 强度太大；去重>70% → 生成器同质化。**最终保留率不告诉你该改什么。**
- **各阶段保留率是乘起来的**：三个各丢一半 → 总 12.5% → 成本 8 倍。别把每个过滤器都调到最严。
- **坍塌看板用相对变化告警**（与 C48 的 burn rate 同思路）；告警出现时下游指标可能还没变差——这正是它的价值。

下一站：**模块 05 · 增强的评测与消融** —— 怎么设计一个能证伪「增强有效」的实验。"""),
]
