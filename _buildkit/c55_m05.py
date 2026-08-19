# -*- coding: utf-8 -*-
"""C55 模块 05 · 安全导向的评测体系。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–04（尤其 03 失效模式、04 时序指标）；C18 的 mAP 定义；C61 模块 02（误差分析）互为补充"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_safety_oriented_eval.ipynb'),
    ("核心参考", "COCO detection eval；TIDE 误差分解；LRP error；ISO 21448 (SOTIF)；nuScenes / Waymo Open 的复合指标设计"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ── 1 ────────────────────────────────────────────────────────────
    ("map_limits", "为什么 mAP 不足以衡量 TSR：五个盲区", "".join([
        P("这一节是本模块的地基，也是 <strong>JD 里「Build and maintain evaluation pipelines」那条职责的真正含义</strong>——评测流水线的价值不在于「把 mAP 算出来」，而在于<em>算出一组能让团队做对决策的数字</em>。而 mAP 单独拿出来，会系统性地让团队做错决策。要说清这一点，得逐条拆。"),
        H3("盲区①：平均把关键类稀释掉了"),
        P("mAP 是<strong>按类别取算术平均</strong>。一个 60 类的 TSR 系统里，「停车让行」和「景点指示」的权重完全相同——各占 <code>1/60</code>。假设某次改动让「停车让行」的 AP 从 0.85 掉到 0.65（掉了 20 个点，这是一次严重的安全回退），整体 mAP 只掉 <code>20/60 = 0.33</code> 个点。"),
        CALLOUT("danger", "<strong>0.33 个点在检测任务里落在种子噪声范围内</strong>（C61 模块 01 会讲：同配置不同种子的 mAP 波动典型是 ±0.2–0.5）。也就是说：<em>一次会导致漏检停车让行标志的模型回退，在 mAP 上看起来和「什么都没发生」完全一样，甚至可能被当成正常波动而放行上车</em>。这不是假设，这是用 mAP 做发布门禁的系统必然会遇到的事故模式。"),
        H3("盲区②：与距离/尺寸无关"),
        P("mAP 对所有目标一视同仁。但 TSR 的<strong>全部工程价值集中在远距离</strong>：40 米内的大牌子谁都能检出，真正决定用户体验的是「能不能在 80 米外就稳定报出来」（模块 04 算过：100 km/h 降到 60 km/h 需要 165 米的余量）。而按数量算，数据集里 40 米内的大目标往往占多数——<em>它们主导了 mAP，却几乎不携带任何区分度</em>。"),
        H3("盲区③：完全没有时序"),
        P("mAP 是逐帧独立计算再汇总的。<strong>一个每秒闪 15 次的系统和一个稳定输出的系统，只要每帧的框和分数一样，mAP 一模一样。</strong> 但前者会让仪表盘上的限速数字疯狂跳变、让下游限速控制反复触发与撤销——这是用户第一眼就会抱怨的缺陷，而它在 mAP 上完全隐形。模块 04 花了整整一节讲迟滞，而 mAP 对迟滞的收益<em>一分钱都不给</em>。"),
        H3("盲区④：precision 是相对量，不反映误检的绝对数量"),
        P("这一条最反直觉，值得用数字说透。两个系统的 precision 都是 0.95："),
        TABLE(["", "系统 A", "系统 B"], [
            ["每帧平均检出数", "1.0", "20.0"],
            ["precision", "0.95", "0.95"],
            ["<strong>每帧误检数</strong>", "0.05", "<strong>1.0</strong>"],
            ["每分钟误检数（30 FPS）", "90", "<strong>1800</strong>"],
            ["工程结论", "勉强可用", "<strong>完全不可上车</strong>"],
        ]),
        P("<strong>precision 的分母是系统自己的输出量</strong>，所以它衡量的是「输出的纯度」，而不是「用户被打扰的频率」。TSR 场景下每帧真值目标数常常是 0（大部分路段没有标志），此时 precision 的分母全是误检，指标行为极不稳定。"),
        H3("盲区⑤：与下游动作脱节"),
        DUAL(
            "mAP 的核心是 IoU 阈值。但<strong>对下游而言，把一块限速牌的框画得准 0.05 个 IoU，没有任何价值</strong>——下游要的是「限速值是多少」和「它管哪段路」。反过来，<em>把「限速 60」认成「限速 80」，无论框画得多准，都是一次可能导致超速的严重错误</em>。mAP 对定位误差高度敏感、对语义错误的<strong>代价差异</strong>完全盲目——它只知道「分类错了」，不知道「错成 80 比错成 40 危险得多」。",
            "更精确地说：mAP 隐含的损失函数是 <code>0/1 损失 + IoU 门限</code>，而 TSR 的真实损失函数是一个<span class=\"term\">asymmetric cost matrix</span>（非对称代价矩阵），且这个矩阵的元素跨越好几个数量级。<em>用一个损失函数训练/选型，再用另一个损失函数决定安全，中间的鸿沟就是所有「离线指标很好、路测很差」的根源之一</em>。COCO mAP@[.5:.95] 甚至把这个问题放大了：它把一半的权重压在 IoU 0.75–0.95 这一段<strong>对 TSR 毫无意义</strong>的精细定位上。",
        ),
        CALLOUT("intuition", "本节结论不是「mAP 没用」。<strong>mAP 是一个很好的「模型能力的单一标量摘要」，适合做研究迭代的快速信号；它不是一个「系统是否可以上车」的判据。</strong> <em>把这两件事分开，就是安全导向评测体系的全部出发点。</em> 面试里被问到「你怎么评价一个 TSR 系统」，如果第一句就是 mAP，基本被判定为只做过刷榜；如果能说出「mAP 做迭代信号、分桶 + 代价敏感 + FP/km + 时序稳定性做发布判据」，这一题就满分了。"),
    ])),

    # ── 2 ────────────────────────────────────────────────────────────
    ("buckets", "分桶评测：把平均值拆开", "".join([
        P("盲区①②的直接解药是<strong>分桶（stratified evaluation）</strong>：不要报一个数，报一张表。TSR 需要的分桶维度是固定的几条，每条都对应一类真实失效模式（模块 03 的四象限）："),
        TABLE(["分桶维度", "典型分档", "为什么必须分", "对应的失效模式"], [
            ["<strong>像素尺寸</strong>", "&lt;16 / 16–32 / 32–64 / ≥64 px", "工程价值全在小桶，而小桶样本量最少", "远距离漏检"],
            ["<strong>物理距离</strong>", "&gt;80 / 50–80 / 30–50 / &lt;30 m", "决策余量直接由距离决定", "上报太晚"],
            ["<strong>光照</strong>", "白天 / 黄昏 / 夜间 / 隧道出入口", "ISP 与曝光在这几档行为完全不同", "逆光、眩光、隧道口过曝"],
            ["<strong>天气</strong>", "晴 / 阴 / 雨 / 雾 / 雪", "对比度与散射改变目标外观", "低对比度漏检"],
            ["<strong>遮挡度</strong>", "0 / 1–30% / 30–60% / &gt;60%", "遮挡是最常见的召回损失来源", "树叶、车辆、杆件遮挡"],
            ["<strong>类别组</strong>", "禁令 / 警告 / 指示 / 指路 / 辅助", "安全代价按组差好几个数量级", "关键类被平均掩盖"],
        ]),
        DUAL(
            "分桶最直接的收益是<strong>让「整体 +0.3」这种没有信息量的结论变成可行动的判断</strong>。同一个 +0.3，可能是「夜间 +3.0、白天 −0.5」（增强起效了，但白天有轻微副作用，可以接受），也可能是「大目标 +1.0、小目标 −1.5」（模型学会了偷懒，<em>这是必须回滚的</em>）。<strong>不分桶你永远分不清这两种情况。</strong>",
            "但分桶有一个必须正视的统计代价：<strong>桶越细，每桶的样本量越少，指标方差越大</strong>。AP 是一个比例型统计量，其标准误大致按 <code>1/√n</code> 收缩；一个只有 30 个正样本的桶，AP 的 95% 置信区间宽度可能超过 ±0.15——<em>此时「小桶掉了 0.1」根本不是一个可靠的信号</em>。实践中的两条硬规则：① <strong>每个桶至少 50 个正样本</strong>（关键类放宽到 30，但必须同时报置信区间）；② <strong>所有分桶指标都必须带 bootstrap 置信区间</strong>，否则团队会在噪声上做决策。",
        ),
        CALLOUT("warn", "还有一个更隐蔽的陷阱：<strong>边缘分布掩盖交互效应</strong>。你可能看到「夜间 AP 0.72（还行）」「远距离 AP 0.70（还行）」，但<em>「夜间 ∧ 远距离」这个交叉桶的 AP 只有 0.31</em>——而这恰恰是最危险的场景。一维分桶天然看不到这个。<strong>解法是对「安全上最要命的 3–5 个组合」显式建立交叉桶</strong>（夜间×远距、雨天×小目标、逆光×禁令类），而不是把所有维度做笛卡尔积（那会让每个桶都没样本）。<em>选哪几个交叉桶，本身就是领域知识的体现。</em>"),
        H3("按实例平均 vs 按桶平均：一个会翻转结论的选择"),
        P("分桶之后还要决定<strong>怎么汇总</strong>，而这个选择能直接翻转模型排名。设三个尺寸桶的样本数是 100 / 300 / 600："),
        TABLE(["", "小桶 (100)", "中桶 (300)", "大桶 (600)", "micro（按实例）", "macro（按桶）"], [
            ["模型 A", "<strong>0.80</strong>", "0.90", "0.92", "0.902", "<strong>0.873</strong>"],
            ["模型 B", "<strong>0.50</strong>", "0.95", "0.96", "<strong>0.911</strong>", "0.803"],
            ["结论", "A 好 0.30", "B 好", "B 好", "<em>B 赢</em>", "<em>A 赢</em>"],
        ]),
        CALLOUT("intuition", "<strong>micro 平均（按实例加权）会被样本量最大的桶主导，而数据集里样本量最大的桶通常是「最容易的那一档」</strong>——因为近处的大目标又多又好标。于是 micro 平均系统性地奖励「在容易的地方做得更好」的模型。<em>macro 平均（每桶等权）则强行给稀有而关键的桶同等发言权</em>。<strong>TSR 的正确默认是 macro，并且对安全关键桶再加权。</strong> 面试里能主动指出「micro/macro 的选择会翻转排名」，说明你真的分析过评测代码而不只是读过输出。"),
    ])),

    # ── 3 ────────────────────────────────────────────────────────────
    ("cost", "代价不对称：把安全后果写进指标里", "".join([
        P("盲区①⑤的根本解药，是承认<strong>不同的错误代价差好几个数量级，而且不对称</strong>。TSR 的代价结构有三层，逐层都不对称："),
        OL([
            "<strong>类别之间不对称</strong>：漏检「停车让行」可能导致闯路口；漏检「景点指示」几乎零后果。二者相差 100 倍以上。",
            "<strong>错误方向不对称</strong>：把「限速 60」认成「限速 80」会导致超速；把「80」认成「60」只是保守。<em>同一对类别，两个方向的代价可以差 5–10 倍</em>——这是最常被忽略的一层。",
            "<strong>漏检与误检不对称，且方向随类别翻转</strong>：对「停车让行」，漏检远比误检危险；对「限速 30」（出现在高速上），误检导致的急减速反而更危险。<strong>不存在一个全局的「recall 优先」或「precision 优先」。</strong>",
        ]),
        P("把它形式化：定义代价矩阵 <code>C[c_true][c_pred]</code>（含 <code>c_pred = ∅</code> 表示漏检、<code>c_true = ∅</code> 表示误检），系统的<span class=\"term\">risk score</span>（风险分）就是混淆计数与代价矩阵的内积，再除以里程做归一化："),
        MATH("\\mathcal{R}=\\frac{1}{L_{km}}\\sum_{c,c'} N_{c\\to c'}\\; C[c][c'] \\qquad(\\text{单位：代价 / km})"),
        DUAL(
            "这个数的用法很直接：<strong>它替代 mAP 成为「单一主指标」</strong>。它天然把关键类的权重提上来、把无关类的权重压下去，并且量纲有物理意义（每公里承担多少风险），可以跨版本、跨车型比较。<em>而且它对上一节的 micro/macro 之争免疫</em>——代价加权本身就是一种更有依据的加权方式。",
            "但必须防住一个真实的失败模式：<strong>代价数值不能拍脑袋</strong>，否则它就变成了「用一个更不透明的数掩盖分歧」。工业界的正规做法是从下游后果反推，借用功能安全的方法论：<span class=\"term\">HARA</span>（Hazard Analysis and Risk Assessment）按「暴露频率 × 可控性 × 严重度」给每个危害场景定级，<span class=\"term\">FMEA</span> 则从失效模式出发排优先级。<em>代价矩阵应该是这些分析的产物，有文档、有评审、有版本号</em>——而不是某个工程师在配置文件里改的一个常数。",
        ),
        TABLE(["错误", "典型代价（相对值）", "理由"], [
            ["漏检「停车让行 / 让行」", "<strong>100</strong>", "可能导致不减速通过冲突点"],
            ["漏检「禁止驶入 / 单行道」", "80", "可能进入逆行车道"],
            ["限速类<strong>低值错成高值</strong>（60→80）", "<strong>15</strong>", "直接导致超速"],
            ["漏检限速牌", "8", "维持原速，通常有其他信息源兜底"],
            ["限速类<strong>高值错成低值</strong>（80→60）", "2", "保守，主要是体验问题"],
            ["误检一块不存在的限速牌", "<strong>12</strong>", "可能导致无故减速，后车追尾风险"],
            ["漏检 / 错分指路、景点类", "0.5", "几乎无安全后果"],
        ]),
        CALLOUT("danger", "<strong>用 mAP 选模型会选出「平均好但关键类差」的模型</strong>，这不是理论担忧。notebook 里会构造一个真实存在的场景：模型 A 的 mAP 比模型 B 高 0.003（在噪声内），但 A 的风险分是 B 的 <strong>1.7 倍</strong>——因为 A 在「停车让行」上掉了 25 个点，而这个类只占 60 类里的一个。<em>如果发布门禁只看 mAP，A 会被放行。</em> <strong>这就是「评测流水线」这条职责真正要防的事故。</strong>"),
    ])),

    # ── 4 ────────────────────────────────────────────────────────────
    ("rates", "工程化的率指标：FP per km 与 per-sign recall", "".join([
        P("盲区④的解药是<strong>换分母</strong>。这一节讲两个替换，它们都极其简单，但会立刻改变团队的讨论方式。"),
        H3("替换一：precision → FP per km / per hour"),
        TABLE(["指标", "分母", "能不能被刷", "能不能跨系统比", "对应用户体验吗"], [
            ["precision", "<strong>系统自己的检出数</strong>", "<strong>能</strong>——提高阈值就涨", "不能（分母不同）", "不对应"],
            ["FP / 帧", "标注帧数", "不能", "<em>勉强</em>（依赖数据集构成）", "不直接"],
            ["<strong>FP / km</strong>", "<strong>行驶里程</strong>（物理量）", "<strong>不能</strong>", "<strong>能</strong>", "<strong>直接对应</strong>"],
            ["<strong>FP / hour</strong>", "行驶时长", "不能", "能（但受车速影响）", "直接对应"],
            ["MTBF（误报间隔里程）", "—", "不能", "能", "最直观：「平均多少公里一次」"],
        ]),
        DUAL(
            "「能不能被刷」这一栏是关键。<strong>precision 的分母是系统的输出量，所以只要少输出就能把它拉高</strong>——把阈值从 0.5 提到 0.9，precision 从 0.90 涨到 0.98，看起来是进步，实际上是把召回砍掉了一半。<em>任何以 precision 为主要目标的优化，都会退化成「提高阈值」。</em> 而 FP/km 的分母是里程，是一个和系统行为完全无关的外生物理量，提高阈值会让 FP/km 下降、同时让 recall 下降——<strong>两个数一起动，取舍就暴露出来了，没法自欺欺人。</strong>",
            "量级感也很重要，这是能在面试里立刻显出手感的地方：<strong>FP/km = 0.1 意味着每 10 km 一次误报</strong>。一次 30 km 的通勤会触发 3 次无故减速或错误限速显示——<em>用户会在一周内关掉这个功能</em>。量产 TSR 的目标通常是 <strong>FP per 100 km &lt; 1</strong>，关键类（会触发实际控制动作的）还要再严一到两个数量级。把这个数字记住，比记住任何 mAP 数字都有用。",
        ),
        H3("替换二：per-frame recall → per-sign recall"),
        P("这是 TSR 特有的、也是最容易被忽略的一个替换。考虑一块牌子在视野里存在 90 帧，系统在其中 12 帧检出："),
        ASCII("""帧序号   0 ......... 40 ......... 60 ......... 78 ... 90
真值     ████████████████████████████████████████████  (90 帧都有)
检出                              ▓▓  ▓▓▓▓  ▓▓ ▓▓▓▓    (12 帧)
                                  ↑
                            首次检出 @ 52 m

per-frame recall  = 12 / 90 = 13.3%    ← 看起来像个失败的系统
per-sign  recall  =  1 /  1 = 100%     ← 用户视角：这块牌子被识别了
首次检出距离       = 52 m               ← 真正决定体验的量
稳定检出距离       = 38 m               ← 从这里起 95% 的帧都能检出

**三个数描述的是同一段数据，但导向完全不同的工程结论。**""")
        ,
        DUAL(
            "<strong>per-frame recall 严重低估了一个有时序融合的系统的真实能力</strong>——模块 04 讲过，只要有几帧检出并且被正确关联累积，系统就能稳定上报。所以只报 per-frame recall 的评测，会让你去优化一个根本不重要的量（每一帧都要检出），而放过真正重要的量（<em>第一次可靠检出发生在多远</em>）。",
            "但反过来也要警惕：<strong>per-sign recall 会掩盖「检出得太晚」</strong>。一块牌子在 15 米处才第一次检出，per-sign recall 仍然是 100%，可那时候已经来不及减速了。<em>所以 per-sign recall 必须和「首次检出距离的分布」一起报</em>，单独看没有意义。<strong>正确的一组是：per-sign recall（有没有）+ 首次检出距离 p50/p90（多远）+ 稳定检出距离（从哪起可信）。</strong> 这三个数一起，才完整描述了 TSR 的召回能力。",
        ),
        CALLOUT("intuition", "把这一节浓缩成一条可迁移的判据：<strong>一个指标是否值得进发布门禁，先问它的分母是什么。分母是系统自己的输出（precision、平均检出置信度），它就可以被优化行为污染；分母是外生的物理量（里程、时长、物理标志个数），它才是诚实的。</strong> <em>这条判据在推荐系统、语音唤醒、异常检测里同样成立——唤醒词检测的行业标准指标就是「误唤醒次数 / 24 小时」，理由完全一样。</em>"),
    ])),

    # ── 5 ────────────────────────────────────────────────────────────
    ("temporal", "时序稳定性指标：mAP 完全看不见的那一半", "".join([
        P("盲区③的解药。模块 04 花了整节讲迟滞、状态机、证据累积，而这些工作在 mAP 上<strong>一分收益都体现不出来</strong>。要让它们可被度量、可被优化、可进门禁，必须显式定义一组时序指标。以下五个是量产 TSR 的最小集合。"),
        TABLE(["指标", "定义", "为什么它重要", "典型目标"], [
            ["<strong>首次检出距离</strong>", "轨迹第一次被<em>上报</em>时的距离（不是第一次检出）", "决定下游有多少决策余量", "p50 ≥ 70 m，p90 ≥ 45 m"],
            ["<strong>稳定检出距离</strong>", "最远的 <code>d</code>，使得从 <code>d</code> 起 ≥95% 的帧都在上报", "「偶尔闪一下」不等于「可用」", "≥ 50 m"],
            ["<strong>闪烁次数</strong>", "单条轨迹生命周期内上报状态的翻转次数", "直接对应用户看到的跳变", "每标志 ≤ 1"],
            ["<strong>误报持续时长</strong>", "一次误报从上报到撤销的时间，报 p50 / p95", "0.1 s 与 3 s 的误报是两种事故", "p95 ≤ 0.5 s"],
            ["<strong>ID switch / 类别跳变率</strong>", "同一物理标志被换 ID 或换类别的次数", "跳变会让下游反复重置约束", "≤ 0.02 次 / 标志"],
        ]),
        DUAL(
            "「首次<strong>上报</strong>距离」而不是「首次<strong>检出</strong>距离」这个措辞是刻意的。<em>检出是检测器的事，上报是整个系统的事</em>——模块 04 的 n_init、τ_on、迟滞都作用在两者之间。只测检出距离，等于把时序模块的全部工作排除在评测之外；<strong>只有测上报距离，模块 04 的参数才有了目标函数</strong>。这也是为什么这两个模块必须连起来读。",
            "「误报持续时长」则是<strong>迟滞的反面账单</strong>。模块 04 里我们用 τ_off &lt; τ_on 换来了闪烁次数的数量级下降，代价正是误报撤销变慢。<em>如果评测里只有「闪烁次数」而没有「误报持续时长」，团队会一路把 τ_off 调到极低——闪烁指标一片绿，而路上的误报会赖着三秒钟不走。</em> <strong>凡是存在此消彼长的一对机制，评测里必须同时有度量两端的指标，否则优化一定会滑向一边。</strong> 这条规律远超 TSR，是设计任何指标体系时的通则。",
        ),
        CALLOUT("warn", "计算这些指标有一个前提常被忽略：<strong>你需要「物理标志级」的真值关联，而不只是逐帧框标注</strong>。也就是说，标注时必须把同一块牌子在连续帧里的框用同一个 instance ID 串起来（类似 MOT 的标注格式）。<em>如果标注规范里没有这一条，上面五个指标一个都算不出来</em>——而等你发现的时候，数据已经标完了。<strong>「评测指标决定标注规范」，这个因果方向必须在项目启动时就想清楚。</strong>"),
        CALLOUT("intuition", "一个把时序稳定性讲给非算法同事听的好比喻性说法（不跨域，就用本领域的话）：<strong>mAP 衡量的是「系统在每一个瞬间是否正确」，时序指标衡量的是「系统作为一个持续运行的服务是否可依赖」。</strong> <em>前者是照片，后者是录像。而用户和下游模块消费的永远是录像。</em>"),
    ])),

    # ── 6 ────────────────────────────────────────────────────────────
    ("regression", "场景化回归集与发布门禁", "".join([
        P("有了指标，下一步是<strong>把它们组织成一个能拦住回退的门禁</strong>。核心思想：<em>把模块 03 的每一个失效模式，都变成一个小而专的回归集</em>。"),
        ASCII("""regression_suite/
├── core/                      通用能力，样本量大，看趋势
│   ├── all_daylight/          3000 帧   —— 主指标（风险分）在这里算
│   └── all_night/             1200 帧
├── failure_modes/             **每个失效模式一个集合，名字就是模式名**
│   ├── small_far_60_100m/      300 帧   门禁：小目标桶 recall 不许跌
│   ├── occlusion_by_vehicle/   240 帧   门禁：遮挡桶 recall 不许跌
│   ├── backlight_tunnel_exit/  180 帧   门禁：观察项（样本少）
│   ├── billboard_fp/           400 帧   门禁：**FP/km 硬上限**
│   ├── rain_night/             200 帧
│   ├── variable_e_sign/        150 帧   门禁：切换响应延迟 ≤ N 帧
│   └── gantry_multi_sign/      160 帧   门禁：ID switch ≤ 阈值
├── critical_class/            **安全关键类专项，样本量小但门禁最硬**
│   ├── stop_yield/             220 帧   门禁：recall **绝对不许跌**（硬门禁）
│   └── no_entry/               140 帧
└── temporal/                  必须带 instance ID 的连续片段
    ├── approach_sequences/      80 段   首报距离 / 稳定距离 / 闪烁
    └── fp_episodes/             60 段   误报持续时长 p95

设计原则：**每个集合都要能回答一个具体问题**，而不是「再多标点数据」。
如果一个集合掉点了你说不出该改什么，这个集合就没设计好。""")
        ,
        P("门禁规则要<strong>分三档</strong>，混在一起会让门禁要么形同虚设、要么天天误报："),
        TABLE(["档位", "适用对象", "规则", "违反后果"], [
            ["<strong>硬门禁（blocking）</strong>", "安全关键类 recall、FP/km 上限、p99 延迟", "<strong>不许跌，容差 = 0（或极小）</strong>", "<strong>直接阻断发布</strong>，必须修复"],
            ["<strong>软门禁（warning）</strong>", "整体风险分、各分桶 AP", "跌幅 &gt; 容差 且统计显著 → 需要书面说明与审批", "阻断，但可由负责人签字覆盖"],
            ["<strong>观察项（tracking）</strong>", "样本量 &lt; 50 的小集合、新加入的场景", "只记录趋势，不阻断", "无，但连续 3 次劣化会自动升级为软门禁"],
        ]),
        DUAL(
            "<strong>容差必须来自种子方差，而不是拍脑袋</strong>。C61 模块 01 会讲：同配置换个随机种子，检测 mAP 的波动典型在 ±0.2–0.5。所以把软门禁的容差设成「跌 0.1 就拦」，结果是<em>门禁天天误报，团队三周内就会学会绕过它</em>——这是门禁系统最常见的死法。<strong>正确做法：先跑 3–5 个种子测出该指标的自然波动，把容差设在 2σ 附近，并要求跌幅同时通过显著性检验。</strong>",
            "而<strong>显著性检验用在几十个切片上时，必须做多重比较校正</strong>。20 个切片各做一次 α=0.05 的检验，即使模型完全没变，也<em>期望有 1 个切片报「显著劣化」</em>（<code>1−0.95²⁰ = 64%</code> 的概率至少出现一个假警报）。<span class=\"term\">Bonferroni</span> 校正（阈值除以切片数）过于保守，会让真实回退也检不出来；<strong><span class=\"term\">Benjamini–Hochberg</span>（BH-FDR）控制的是「被判为显著的结论中假阳性的比例」，是这个场景的正确工具</strong>——notebook 里会完整实现它。",
        ),
        CALLOUT("danger", "门禁设计里有一条必须写进流程的反直觉规则：<strong>门禁必须可以被人为覆盖（override），但每次覆盖都要留下记录、理由和责任人。</strong> <em>一个不能被覆盖的门禁，在遇到「已知原因、可接受的临时劣化」时会阻塞整个团队，于是团队会去修改门禁本身、或者干脆绕开流水线发布——两种结果都比允许覆盖糟糕得多。</em> 而覆盖记录本身就是最有价值的技术债台账：<strong>如果同一条门禁被覆盖了三次，那它要么阈值定错了，要么你们有一个一直没修的真问题。</strong>"),
    ])),

    # ── 7 ────────────────────────────────────────────────────────────
    ("gap", "离线指标与路测体验为什么会背离", "".join([
        P("这是评测工程师最常被问到、也最难回答的问题：<strong>「离线 recall 0.92、FP 很低，为什么车上跑起来一堆误报？」</strong> 原因有七条，按实际发生频率排序。"),
        TABLE(["#", "原因", "机理", "怎么验证 / 怎么修"], [
            ["<strong>1</strong>", "<strong>分母不匹配（最常见、最被忽略）</strong>", "评测集里 80% 的帧含标志，真实道路只有 5%。<em>误检主要发生在无标志的背景帧上，而这类帧在评测集里被严重欠采样</em>", "按真实里程的帧构成重新加权；或直接用连续路测片段做评测"],
            ["2", "帧级 vs 事件级", "离线数 FP 帧数，用户感受的是 FP <em>事件</em>数（一次误报 = 连续若干帧）", "把 FP 帧合并成事件再统计；同时报两者"],
            ["3", "时序被忽略", "离线逐帧算，路上是连续输出；闪烁在离线完全隐形", "用模块 04 / 本模块第 5 节的时序指标"],
            ["4", "工作点不同", "离线扫整条 PR 曲线取 AP，车上是<strong>一个固定阈值</strong>", "永远同时报「固定工作点下的 recall/FP」"],
            ["5", "预处理/后处理不一致", "训练用 PIL、车上用 OpenCV/ISP；resize、BGR/RGB、letterbox 差异", "<strong>逐层对拍</strong>（C60 模块 01/04 的方法论）"],
            ["6", "采集域漂移", "评测集是一年前那批相机采的，车上是新 ISP / 新镜头", "按采集批次分桶评测；新硬件必须新采集"],
            ["7", "标注口径 ≠ 用户口径", "标注把 120 m 外糊成一团的牌子也标了，但用户根本不需要那么远就报", "把评测的有效距离范围与产品需求对齐"],
        ]),
        P("第 1 条值得算一遍账，因为它的量级往往超出所有人的直觉。设背景帧的每帧误检率 <code>q_bg = 0.004</code>、含标志帧 <code>q_sign = 0.001</code>："),
        MATH("\\text{FP/km}=\\frac{f\\cdot t}{L}\\Big[\\pi_{bg}\\,q_{bg}+(1-\\pi_{bg})\\,q_{sign}\\Big],\\qquad \\pi_{bg}=\\text{背景帧占比}"),
        DUAL(
            "评测集里 <code>π_bg = 0.20</code>，真实道路上 <code>π_bg = 0.95</code>。于是评测集报出的「每帧平均 FP 数」是 <code>0.2×0.004 + 0.8×0.001 = 0.0016</code>，而真实道路上是 <code>0.95×0.004 + 0.05×0.001 = 0.00385</code>——<strong>相差 2.4 倍</strong>。如果你天真地拿离线的 0.0016 去外推一小时路测（60 km、108000 帧），会得到 2.9 FP/km，而实际是 <strong>6.9 FP/km</strong>。<em>这个 2.4 倍的低估，足以让一个「离线看起来达标」的版本在路测第一天就被否掉。</em>",
            "而这个偏差是<strong>结构性的、必然发生的</strong>，因为标注是按「有目标的片段」组织的——标注供应商没有动力去标一万帧空旷的高速路。<em>所以评测集天然会过采样含标志帧</em>。两条修法：① <strong>显式保留一批「连续里程片段」</strong>（哪怕大部分帧没有标志），专门用来测 FP/km，这是唯一诚实的做法；② 如果只能用现有集合，就<strong>按真实 π_bg 对两类帧重新加权</strong>再汇总。<strong>面试里能主动讲出「分母不匹配」这一条，基本可以断定你真的做过评测流水线而不只是跑过 <code>cocoeval</code>。</strong>",
        ),
        CALLOUT("intuition", "把这七条压成一句可操作的原则：<strong>离线评测集与线上分布的每一处差异，都会在指标上产生一个可估算的偏差；工程师的职责不是消灭差异（做不到），而是<em>知道每一处差异会往哪个方向、偏多少</em></strong>。<em>一个能说出「我们的离线 FP 率大约低估 2–3 倍，因为背景帧欠采样」的团队，和一个只会说「路测和离线对不上」的团队，能力差距是数量级的。</em>"),
    ])),

    # ── 8 ────────────────────────────────────────────────────────────
    ("scorecard", "记分卡与评测流水线：把这条职责做成工程", "".join([
        P("最后把前七节收成一件可交付的东西：<strong>一张记分卡 + 一条流水线</strong>。这正是 JD 里「Build and maintain evaluation pipelines」的完整答案形态。"),
        H3("记分卡：一个主指标 + 若干护栏"),
        P("多目标优化在工程组织里是不可执行的——<strong>当有五个同等重要的目标时，任何改动都能找到一个变好的目标，于是所有改动都能被论证为「进步」</strong>。唯一的解法是把目标结构化成「一个主 + 若干约束」："),
        TABLE(["层级", "指标", "角色", "规则"], [
            ["<strong>主指标</strong>", "代价加权风险分（/100 km）", "唯一的优化目标，用于排序模型", "越低越好；发布看它的相对变化"],
            ["<strong>护栏</strong>", "FP per 100 km（整体 & 关键类）", "硬约束", "超过上限 → 直接阻断"],
            ["<strong>护栏</strong>", "安全关键类 per-sign recall", "硬约束", "不许跌"],
            ["<strong>护栏</strong>", "端到端 p99 延迟、显存峰值", "硬约束（来自 C53/C60）", "超预算 → 阻断"],
            ["<strong>护栏</strong>", "闪烁次数、误报持续时长 p95", "硬约束", "超过上限 → 阻断"],
            ["<strong>诊断</strong>", "分桶 AP、混淆矩阵、TIDE 分解", "不进门禁，用于<em>解释</em>主指标为什么变化", "必须随每次评测自动产出"],
        ]),
        DUAL(
            "把「诊断指标」和「门禁指标」分开是这张表最重要的设计。<strong>门禁指标要少、要稳、要能被无歧义地判定；诊断指标要多、要细、要能定位原因。</strong> <em>把诊断指标塞进门禁，会让门禁充满噪声并被团队绕过；把门禁指标做得太粗，则拦不住真回退。</em>",
            "还有一条容易被忽略的工程纪律：<strong>评测代码本身必须有单元测试</strong>。指标算错是极其常见的事故——IoU 的 <code>+1</code> 边界、类别 ID 的 0/1 偏移、按类别聚合时把空类算成 0 而不是跳过、AP 的插值方式写错……<em>而这类 bug 的可怕之处在于它不会报错，只会让所有决策基于错误的数字</em>。<strong>标准做法：用「完美预测」（应得 1.0）、「全空预测」（应得 0.0）、「手算过的小例子」（应得某个精确值）三组合成输入做单元测试</strong>——notebook 里的每个指标实现都会配这样的断言。",
        ),
        H3("流水线：让「跑过评测」这件事变成不可跳过的"),
        ASCII("""[数据版本 v]  ──┐
[模型 commit c] ─┼──▶ ① 推理（固定 seed / 关 TTA / 固定后处理参数 / 记录环境）
[配置 hash h] ──┘         │
                          ▼
                   ② 指标计算（评测代码有单测；产出 raw predictions 归档）
                          │
                          ▼
                   ③ 切片报告（分桶 × 类别 × 时序，全部带 bootstrap CI）
                          │
                          ▼
                   ④ 与 baseline 对比（配对检验 + BH-FDR 多重比较校正）
                          │
                          ▼
                   ⑤ 门禁判定（硬 / 软 / 观察三档）
                     ├─ 通过 ──▶ 打包 + 归档 scorecard.json ──▶ 可发布
                     └─ 不通过 ─▶ 阻断（可 override，但记录理由 + 责任人）

不变量：**「存在一份 scorecard.json」本身就编码了「这个版本通过了评测」这个事实。**
        没有 scorecard 的产物一律不允许进入发布流程 —— 用产物的存在性编码验证已通过，
        比依赖人记得跑评测可靠得多。""")
        ,
        CALLOUT("intuition", "<strong>面试里被问「你怎么理解 build and maintain evaluation pipelines」，一个满分的回答骨架是三段</strong>：<em>①「评测的目的不是产出数字，是产出正确的决策」——所以先讲主指标/护栏/诊断的分层，以及为什么 mAP 只能做诊断不能做门禁；②「评测本身是要被测试的软件」——讲评测代码的单元测试、数据版本、可复现性、raw prediction 归档；③「评测要贴着线上分布」——讲分母不匹配、连续里程片段、离线-路测偏差的量化。</em> <strong>能把这三段讲完的候选人，实际比能背出 DETR 结构的候选人稀少得多。</strong>"),
    ])),

    # ── 9 ────────────────────────────────────────────────────────────
    ("frontier", "研究前沿与开放问题", "".join([
        P("评测这个方向的论文远少于模型方向，但正因为如此，它的开放问题密度更高。"),
        UL([
            "<strong>mAP 的替代与补充</strong>：<em>TIDE</em> 把 AP 的损失分解成 Cls/Loc/Both/Dupe/Bkg/Miss 六类，并算出「修好每一类能涨多少 AP」——这是决定下一步做什么的最强工具（C61 模块 02 会完整实现）。<em>LRP error</em>（Localisation-Recall-Precision）把定位误差、漏检、误检合成一个可解释的单一误差量，且不依赖 AP 的插值技巧。<em>Optimal Correction Cost</em> 则从「修正到完美需要多少操作」的角度定义指标——<strong>这个视角和本模块的代价加权风险分是同源的</strong>。",
            "<strong>安全导向的评测框架</strong>：<em>ISO 21448 (SOTIF)</em> 关注「功能本身没故障、但因为性能局限导致的危害」，其核心是把场景空间划分成「已知安全 / 已知不安全 / 未知不安全」三象限，并要求把第三象限持续缩小——<em>这与 C58 的数据闭环是同一件事的两种表述</em>。<em>RSS</em>（Responsibility-Sensitive Safety）则试图给出可形式化验证的安全约束。开放问题：<strong>感知的性能指标如何严格地映射到系统级安全指标</strong>，目前还没有被广泛接受的方法。",
            "<strong>不确定性的严格保证</strong>：<span class=\"term\">conformal prediction</span> 能在很弱的假设下给出有覆盖率保证的预测集合（例如「以 95% 概率，真实类别在这个候选集里」）。把它用到检测上（框的置信区域、类别集合）是活跃方向，<em>但如何在时序累积后仍保持覆盖保证，仍是开放的</em>——而这恰好是模块 04 贝叶斯累积最需要的理论支撑。",
            "<strong>长尾评测的统计功效</strong>：稀有类的测试样本可能只有几十个，AP 的置信区间宽到无法做决策。<strong>「要检出 0.02 的 AP 变化需要多少样本」这类功效分析（power analysis）在检测评测里几乎没人做</strong>，但它决定了你的门禁到底有没有意义。C61 模块 01 会补上这一课。",
            "<strong>仿真与重建闭环评测</strong>：CARLA 类仿真器的域差太大；而基于 NeRF / 3D Gaussian Splatting 的<em>真实场景重建 + 反事实重放</em>（改变天气、光照、增删标志）是近两年的热点——它有望解决「安全关键场景无法在真实道路上重复采集」这个根本困难。开放问题是重建的保真度是否足以支撑安全结论。",
            "<strong>时序稳定性指标没有共识</strong>：MOT 领域有 MOTA/IDF1/HOTA，但它们是为「跟踪质量」设计的，不直接对应「输出稳定性」。<em>各家量产团队各用一套（本模块给的五个指标是一个常见组合），学术界尚无统一定义</em>。这是一个真实存在、且明显有价值的空白。",
            "<strong>离线-在线 gap 的可预测性</strong>：能否从离线数据的分布统计，<em>提前预测</em>某个模型在真实里程上的 FP/km？这本质上是一个分布外泛化的估计问题（unsupervised accuracy estimation 方向），目前的方法在检测任务上都还不够可靠。",
        ]),
        CALLOUT("paper", "必读：★<em>TIDE: A General Toolbox for Identifying Object Detection Errors</em>（Bolya et al. ECCV 2020——先读这篇，它会永久改变你看 mAP 的方式）；<em>Localization Recall Precision (LRP) Error</em>（Oksuz et al. ECCV 2018 与其 TPAMI 扩展）；<em>Microsoft COCO</em>（Lin et al. 2014）的评测协议原文与 <code>cocoeval</code> 源码（<strong>务必读源码</strong>——很多「mAP 算不对」的问题只有读了源码才明白）；<em>nuScenes</em>（Caesar et al. CVPR 2020）的 NDS 复合指标与 <em>Waymo Open Dataset</em>（Sun et al. CVPR 2020）的按距离/难度分桶设计，是「工业界怎么设计评测」的最佳公开范本；<em>ISO 21448:2022 (SOTIF)</em> 的框架章节；<em>HOTA</em>（Luiten et al. IJCV 2021）作为时序指标设计的参考；conformal prediction 入门读 Angelopoulos &amp; Bates 的 <em>A Gentle Introduction to Conformal Prediction</em>。相邻课程：C61 模块 02（TIDE 误差分解实现）、C61 模块 01（种子方差与功效分析）、C58 模块 05（闭环验证与回归门禁）、C55 模块 04（时序指标的来源）。完整清单见 <code>references.md</code>。"),
    ])),
]

# ────────────────────────────────────────────────────────────────────
# notebook
# ────────────────────────────────────────────────────────────────────

NB = [
    md("""# 05 · 安全导向的评测体系（分桶 mAP / 代价敏感风险分 / FP-per-km / 时序稳定性 / 回归门禁）

目标：把「mAP 0.85」这种**不足以做决策**的数字，换成一整套**能拦住安全回退**的指标体系，
并把它做成一条可复现、可测试的评测流水线。

本 notebook 你会亲手实现：

1. 从零实现 **AP**（all-point 插值），并用手算过的例子做单元测试
2. **分桶评测**：构造一对「整体 mAP 几乎相同、小目标桶差 0.3」的模型，
   并展示 **micro / macro 平均会给出相反的排名**
3. **代价敏感风险分**：构造 mAP 更高但风险分高 1.8 倍的模型 —— 用 mAP 选型会选错
4. **FP per km / per hour**、**per-sign recall vs per-frame recall**，以及工作点选择
5. **时序稳定性指标**：首次上报距离 / 稳定检出距离 / 闪烁次数 / 误报持续时长
6. **回归门禁判定器**：两比例检验 + **Benjamini–Hochberg 多重比较校正** + 三档门禁
7. **离线-路测背离的量化**：分母不匹配到底让你低估了多少倍

> 心智模型：**mAP 是迭代信号，不是发布判据。
> 评测流水线的产物不是数字，是「能不能发」这个决策。**"""),

    md("""## 1 · 从零实现 AP，并给它写单元测试

**评测代码本身必须有单元测试** —— 指标算错不会报错，只会让所有决策基于错误的数字。
三组标准输入：完美预测（应得 1.0）、全错预测（应得 0.0）、手算过的小例子。"""),
    code("""import numpy as np, math, itertools
from collections import Counter, defaultdict
rng = np.random.default_rng(5)

def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    iw = max(0.0, x2 - x1); ih = max(0.0, y2 - y1)
    inter = iw * ih
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def average_precision(scores, tp, n_gt):
    '''all-point 插值 AP（COCO 风格）。scores/tp 同序，tp 为 0/1。'''
    if n_gt == 0:
        return float('nan')
    if len(scores) == 0:
        return 0.0
    order = np.argsort(-np.asarray(scores, dtype=float), kind='stable')
    t = np.asarray(tp, dtype=float)[order]
    ctp = np.cumsum(t); cfp = np.cumsum(1.0 - t)
    rec = ctp / n_gt
    prec = ctp / np.maximum(ctp + cfp, 1e-12)
    mrec = np.concatenate([[0.0], rec, [rec[-1]]])
    mpre = np.concatenate([[0.0], prec, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):          # 单调递减包络
        mpre[i] = max(mpre[i], mpre[i+1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx+1] - mrec[idx]) * mpre[idx+1]))

# ── 单元测试三件套 ──
assert average_precision([0.9, 0.8, 0.7], [1, 1, 1], 3) == 1.0, '完美预测应得 1.0'
assert average_precision([0.9, 0.8, 0.7], [0, 0, 0], 3) == 0.0, '全错应得 0.0'
# 手算例子：n_gt=3，按分数降序 tp = [1,0,1,1]
#   rec = [1/3,1/3,2/3,1]  prec = [1,.5,.667,.75]
#   包络后 mpre = [1,1,.75,.75,.75,0]
#   AP = 1/3*1 + 1/3*.75 + 1/3*.75 = 0.833333
ap_hand = average_precision([0.9, 0.8, 0.7, 0.6], [1, 0, 1, 1], 3)
assert abs(ap_hand - 5/6) < 1e-9, f'手算应为 0.833333，得到 {ap_hand}'
assert abs(average_precision([0.9], [1], 3) - 1/3) < 1e-9, '只召回 1/3 且 precision=1'
print(f'手算例子 AP = {ap_hand:.6f}   ✅ AP 实现通过三组单元测试')
print('⚠️  评测代码的 bug 不会报错，只会让所有决策基于错误的数字 —— 必须有单测。')"""),
    code("""# ── 逐帧框匹配（按分数降序贪心，一个 GT 只能被认领一次）──
def match_frame(gt_boxes, dets, iou_thr=0.5):
    '''dets: [(box, score), ...]。返回与 dets 同序的 tp 标记。'''
    order = sorted(range(len(dets)), key=lambda i: -dets[i][1])
    used = [False] * len(gt_boxes)
    tp = [0] * len(dets)
    for i in order:
        box = dets[i][0]
        best, best_j = iou_thr, -1
        for j, g in enumerate(gt_boxes):
            if used[j]:
                continue
            v = iou(box, g)
            if v >= best:
                best, best_j = v, j
        if best_j >= 0:
            used[best_j] = True; tp[i] = 1
    return tp

G = [np.array([100., 100., 140., 140.]),
     np.array([300., 300., 320., 320.]),
     np.array([700., 400., 716., 416.])]
Dets = [(np.array([102., 101., 142., 141.]), 0.95),   # 命中 G0
        (np.array([104., 103., 144., 143.]), 0.80),   # **重复检测** G0 -> FP
        (np.array([301., 300., 321., 320.]), 0.70),   # 命中 G1
        (np.array([900., 900., 930., 930.]), 0.60),   # 背景 FP
        (np.array([702., 402., 718., 418.]), 0.40)]   # 命中 G2，但 IoU 只有 0.62
tp = match_frame(G, Dets, iou_thr=0.5)
print('tp 标记:', tp, '  (第 2 个是重复检测 -> FP)')
assert tp == [1, 0, 1, 0, 1], tp
ap = average_precision([d[1] for d in Dets], tp, len(G))
print(f'该帧 AP@0.5 = {ap:.4f}')

# ── 顺手量化一个对 TSR 至关重要的事实：**同样的定位误差，小框吃亏得多** ──
print(f"\\n{'框边长':>8s} {'偏移 2px':>10s} {'偏移 5px':>10s} {'偏移 8px':>10s}")
for s in [16, 40, 96]:
    a = np.array([0., 0., float(s), float(s)])
    row = [iou(a, np.array([d, d, s+d, s+d])) for d in (2., 5., 8.)]
    print(f'{s:>7d}px ' + ' '.join(f'{v:>10.3f}' for v in row))
assert iou(np.array([0.,0.,16.,16.]), np.array([5.,4.,21.,20.])) < 0.5
assert iou(np.array([0.,0.,40.,40.]), np.array([5.,4.,45.,44.])) > 0.6
print('\\n⚠️  **16px 的框偏 (5,4)px 掉到 IoU 0.35（判为「漏检 + 误检」两笔账），')
print('    而 40px 的框偏同样距离仍有 0.65（判为命中）。**')
print('   同一个 IoU 阈值对不同尺度是极不公平的（C57 会严格推导这一点）——')
print('✅ 直接后果：**TSR 的评测必须按像素尺寸分桶**，否则「远处定位差」这件事')
print('   会被记成「远处漏检」，你连改哪儿都定位不到。')

# COCO mAP@[.5:.95] 对定位精度的惩罚有多重？
def ap_over_iou_range(gt_boxes, dets, thrs=None):
    thrs = thrs if thrs is not None else [0.50 + 0.05*i for i in range(10)]
    return float(np.mean([average_precision([d[1] for d in dets],
                                            match_frame(gt_boxes, dets, t),
                                            len(gt_boxes)) for t in thrs]))
print(f'该帧 mAP@[.5:.95] = {ap_over_iou_range(G, Dets):.4f}  '
      f'（比 AP@0.5 低很多 —— 一半权重压在 IoU>0.75 上）')
assert ap_over_iou_range(G, Dets) < ap
print('\\n⚠️  对 TSR 而言，把框画准 0.05 个 IoU **没有任何下游价值** ——')
print('   下游要的是「限速值是多少」和「它管哪段路」。')
print('✅ 所以 TSR 的主指标不该是 mAP@[.5:.95]，而应是代价加权的语义指标（第 3 节）。')"""),

    md("""## 2 · 分桶评测：平均值会说谎

构造一对模型：**整体 AP 几乎相同，但小目标桶差 0.3**。
再看 micro（按实例）与 macro（按桶）平均如何给出**相反的排名**。"""),
    code("""BUCKETS = [('<16px', 0, 16), ('16-32px', 16, 32), ('>=32px', 32, 1e9)]
N_PER_BUCKET = {'<16px': 100, '16-32px': 300, '>=32px': 600}
# 两个模型在各桶的召回上限（刻意设计：A 小目标强、B 大目标强）
RECALL = {'A': {'<16px': 0.80, '16-32px': 0.90, '>=32px': 0.92},
          'B': {'<16px': 0.50, '16-32px': 0.95, '>=32px': 0.96}}

def bucket_of(size_px):
    for name, lo, hi in BUCKETS:
        if lo <= size_px < hi:
            return name
    return BUCKETS[-1][0]

def make_gt(seed=0):
    g = np.random.default_rng(seed)
    gts = []
    for name, lo, hi in BUCKETS:
        hi_ = 96.0 if hi > 1e8 else hi
        for _ in range(N_PER_BUCKET[name]):
            gts.append({'bucket': name, 'size': float(g.uniform(lo + 1, hi_))})
    return gts

def make_preds(gts, model, seed=1, n_fp=200):
    '''每个 GT 按桶召回率被检出，分数从高分布采；再加一批与模型无关的 FP。'''
    g = np.random.default_rng(seed)
    recs = []
    for i, gt in enumerate(gts):
        if g.random() < RECALL[model][gt['bucket']]:
            recs.append({'bucket': gt['bucket'], 'tp': 1,
                         'score': float(np.clip(g.normal(0.75, 0.15), 0.01, 0.999))})
    gfp = np.random.default_rng(999)                    # **两个模型共用同一批 FP**
    for _ in range(n_fp):
        size = float(gfp.uniform(6, 96))
        recs.append({'bucket': bucket_of(size), 'tp': 0,
                     'score': float(np.clip(gfp.normal(0.35, 0.15), 0.01, 0.999))})
    return recs

gts = make_gt()
preds = {m: make_preds(gts, m, seed=2) for m in ['A', 'B']}

def ap_of(recs, n_gt):
    return average_precision([r['score'] for r in recs], [r['tp'] for r in recs], n_gt)

def report(m):
    recs = preds[m]
    per_bucket = {}
    for name, _, _ in BUCKETS:
        sub = [r for r in recs if r['bucket'] == name]
        per_bucket[name] = ap_of(sub, N_PER_BUCKET[name])
    overall = ap_of(recs, len(gts))
    macro = float(np.mean(list(per_bucket.values())))
    return per_bucket, overall, macro

print(f"{'模型':>5s} " + ' '.join(f'{n:>10s}' for n, _, _ in BUCKETS) +
      f" {'整体 AP':>9s} {'macro':>8s}")
res = {}
for m in ['A', 'B']:
    pb, ov, ma = report(m); res[m] = (pb, ov, ma)
    print(f'{m:>5s} ' + ' '.join(f'{pb[n]:>10.3f}' for n, _, _ in BUCKETS) +
          f' {ov:>9.3f} {ma:>8.3f}')

pbA, ovA, maA = res['A']; pbB, ovB, maB = res['B']
assert abs(ovA - ovB) < 0.06, f'整体 AP 应几乎相同：{ovA:.3f} vs {ovB:.3f}'
assert pbA['<16px'] - pbB['<16px'] > 0.15, '小目标桶应差一大截'
assert maA > maB, 'macro 平均应给出与整体 AP 相反的排名'
print(f'\\n整体 AP：A={ovA:.3f} vs B={ovB:.3f}  →  差 {abs(ovA-ovB):.3f}（噪声量级）')
print(f'小目标桶：A={pbA["<16px"]:.3f} vs B={pbB["<16px"]:.3f}  →  差 {pbA["<16px"]-pbB["<16px"]:.3f}（灾难级）')
print(f'macro   ：A={maA:.3f} vs B={maB:.3f}  →  **排名与整体 AP 相反**')
print('\\n⚠️  micro（按实例）被样本量最大的桶主导，而那通常是**最容易的一档**。')
print('✅ TSR 的正确默认是 macro，并对安全关键桶再加权。')"""),
    code("""# ── 分桶的统计代价：桶越细，置信区间越宽 ──
def bootstrap_ci(recs, n_gt, n_boot=400, alpha=0.05, seed=0):
    '''对「实例」做 bootstrap 重采样，给出 AP 的置信区间。'''
    g = np.random.default_rng(seed)
    idx = np.arange(len(recs))
    vals = []
    for _ in range(n_boot):
        take = g.choice(idx, size=len(idx), replace=True)
        sub = [recs[i] for i in take]
        vals.append(ap_of(sub, n_gt))
    lo, hi = np.percentile(vals, [100*alpha/2, 100*(1-alpha/2)])
    # 对实例重采样时 TP 数可能超过 n_gt（真值数是固定的），故把区间裁回 [0,1]
    return float(np.clip(lo, 0.0, 1.0)), float(np.clip(hi, 0.0, 1.0))

print(f"{'桶':>10s} {'正样本数':>9s} {'AP(A)':>8s} {'95% CI':>18s} {'CI 宽度':>9s}")
for name, _, _ in BUCKETS:
    sub = [r for r in preds['A'] if r['bucket'] == name]
    n_gt = N_PER_BUCKET[name]
    lo, hi = bootstrap_ci(sub, n_gt, seed=3)
    print(f'{name:>10s} {n_gt:>9d} {pbA[name]:>8.3f} '
          f'{f"[{lo:.3f}, {hi:.3f}]":>18s} {hi-lo:>9.3f}')

# 再切一个只有 30 个正样本的「关键类」桶（按比例下采样，TP 与 FP 都保留）
g_tiny = np.random.default_rng(21)
tiny = [r for r in preds['A'] if r['bucket'] == '<16px' and g_tiny.random() < 0.30]
lo_t, hi_t = bootstrap_ci(tiny, 30, seed=4)
print(f'\\n只有 30 个正样本的桶：AP={ap_of(tiny,30):.3f}  95% CI=[{lo_t:.3f}, {hi_t:.3f}]'
      f'  宽度={hi_t-lo_t:.3f}')
w_small = bootstrap_ci([r for r in preds['A'] if r['bucket']=='<16px'], 100, seed=3)
w_large = bootstrap_ci([r for r in preds['A'] if r['bucket']=='>=32px'], 600, seed=3)
assert (w_small[1]-w_small[0]) > (w_large[1]-w_large[0]), '小样本桶的 CI 必然更宽'
assert (hi_t - lo_t) > 0.10, '30 个正样本的桶，CI 宽度超过 0.10'
print('\\n⚠️  30 个正样本的桶，AP 的 95% CI 宽度 > 0.10 —— 「掉了 0.05」根本不是信号。')
print('✅ 两条硬规则：① 每桶 >= 50 个正样本  ② **所有分桶指标必须带 bootstrap CI**。')"""),

    md("""## 3 · 代价敏感风险分：用 mAP 选型会选错

三层不对称：类别之间、错误方向之间、漏检与误检之间。
把它们写成代价矩阵，风险分就替代 mAP 成为**唯一主指标**。"""),
    code("""CLASSES = ['stop_yield', 'no_entry', 'speed_60', 'speed_80', 'speed_120', 'info']
GT_COUNT = {'stop_yield': 40, 'no_entry': 30, 'speed_60': 300,
            'speed_80': 300, 'speed_120': 200, 'info': 500}

COST_MISS = {'stop_yield': 100.0, 'no_entry': 80.0, 'speed_60': 8.0,
             'speed_80': 8.0, 'speed_120': 6.0, 'info': 0.5}
COST_FP   = {'stop_yield': 20.0, 'no_entry': 25.0, 'speed_60': 12.0,
             'speed_80': 12.0, 'speed_120': 10.0, 'info': 0.5}
# 错分代价**方向不对称**：低值错成高值 = 超速（危险）；高值错成低值 = 保守
COST_CONF = {('speed_60', 'speed_80'): 15.0, ('speed_80', 'speed_60'): 2.0,
             ('speed_80', 'speed_120'): 15.0, ('speed_120', 'speed_80'): 2.0,
             ('speed_60', 'speed_120'): 25.0, ('speed_120', 'speed_60'): 3.0}

def conf_cost(c_true, c_pred):
    if (c_true, c_pred) in COST_CONF:
        return COST_CONF[(c_true, c_pred)]
    return max(COST_MISS[c_true], COST_FP[c_pred]) * 0.6   # 跨组错分：取较重的一侧打折

print(f"{'错误':<34s} {'代价':>7s}")
for k, v in [('漏检 stop_yield', COST_MISS['stop_yield']),
             ('漏检 no_entry', COST_MISS['no_entry']),
             ('speed_60 -> speed_80（超速）', COST_CONF[('speed_60','speed_80')]),
             ('speed_80 -> speed_60（保守）', COST_CONF[('speed_80','speed_60')]),
             ('误检一块不存在的 speed_60', COST_FP['speed_60']),
             ('漏检 info', COST_MISS['info'])]:
    print(f'{k:<34s} {v:>7.1f}')
assert COST_CONF[('speed_60','speed_80')] > 5 * COST_CONF[('speed_80','speed_60')]
print('\\n⚠️  **同一对类别，两个方向的代价差 7.5 倍** —— 这是最常被忽略的一层不对称。')
print('   代价数值不能拍脑袋：正规做法是从 HARA / FMEA 反推，有文档、有评审、有版本号。')"""),
    code("""# ── 构造两个模型：A 的 mAP 更高，但风险分是 B 的 1.8 倍 ──
RECALL_C = {
    'A': {'stop_yield': 0.70, 'no_entry': 0.75, 'speed_60': 0.98,
          'speed_80': 0.98, 'speed_120': 0.97, 'info': 0.99},
    'B': {'stop_yield': 0.95, 'no_entry': 0.93, 'speed_60': 0.91,
          'speed_80': 0.89, 'speed_120': 0.86, 'info': 0.82},
}
# 错分计数（GT 类 -> 预测类），只列限速类之间
CONFUSE = {'A': {('speed_60','speed_80'): 9, ('speed_80','speed_60'): 4,
                 ('speed_80','speed_120'): 5, ('speed_120','speed_80'): 3},
           'B': {('speed_60','speed_80'): 3, ('speed_80','speed_60'): 6,
                 ('speed_80','speed_120'): 2, ('speed_120','speed_80'): 5}}
FP_COUNT = {'A': {'stop_yield': 1, 'no_entry': 1, 'speed_60': 6,
                  'speed_80': 6, 'speed_120': 4, 'info': 30},
            'B': {'stop_yield': 2, 'no_entry': 1, 'speed_60': 5,
                  'speed_80': 5, 'speed_120': 4, 'info': 25}}
DIST_KM = 100.0

def risk_score(model, dist_km=DIST_KM):
    '''代价加权风险分（每 100 km）。'''
    r = 0.0
    for c in CLASSES:
        n_miss = GT_COUNT[c] * (1.0 - RECALL_C[model][c])
        r += n_miss * COST_MISS[c]
        r += FP_COUNT[model][c] * COST_FP[c]
    for (ct, cp), n in CONFUSE[model].items():
        r += n * conf_cost(ct, cp)
    return r / dist_km * 100.0

def macro_recall(model):
    return float(np.mean([RECALL_C[model][c] for c in CLASSES]))

print(f"{'模型':>5s} {'macro recall(≈mAP 代理)':>24s} {'风险分 / 100km':>16s}")
for m in ['A', 'B']:
    print(f'{m:>5s} {macro_recall(m):>24.4f} {risk_score(m):>16.1f}')

mrA, mrB = macro_recall('A'), macro_recall('B')
rA, rB = risk_score('A'), risk_score('B')
print(f'\\nmAP 代理: A 比 B 高 {mrA-mrB:+.4f}（**在种子噪声范围内**，会被判为「无差别」甚至「A 更好」）')
print(f'风险分  : A 是 B 的 {rA/rB:.2f} 倍  ←  **A 是一次严重的安全回退**')
assert mrA > mrB, 'A 的平均召回更高'
assert rA > 1.5 * rB, f'A 的风险分应显著更高：{rA:.1f} vs {rB:.1f}'
print('\\n🚨 如果发布门禁只看 mAP，A 会被放行 —— 而它在 stop_yield 上掉了 25 个点。')
print('✅ 风险分天然把关键类的权重提上来，量纲有物理意义（每 100 km 承担多少风险），')
print('   可以跨版本、跨车型比较，且对 micro/macro 之争免疫。')

# 逐项归因：风险分的钱花在哪里
print(f"\\n{'类别':<12s} {'A 漏检代价':>11s} {'B 漏检代价':>11s} {'差额':>9s}")
for c in CLASSES:
    ca = GT_COUNT[c]*(1-RECALL_C['A'][c])*COST_MISS[c]
    cb = GT_COUNT[c]*(1-RECALL_C['B'][c])*COST_MISS[c]
    print(f'{c:<12s} {ca:>11.0f} {cb:>11.0f} {ca-cb:>+9.0f}')
print('✅ 风险分不只是排序，还能**逐项归因** —— 直接告诉你下一步该修哪个类。')"""),

    md("""## 4 · 换分母：FP per km 与 per-sign recall

判据：**分母是系统自己的输出（precision）→ 可被优化行为污染；
分母是外生物理量（里程、物理标志数）→ 诚实。**"""),
    code("""# ── precision 可以靠提阈值刷高，FP/km 不能 ──
AVG_SPEED_KMH = 60.0
FPS_EVAL = 30.0
DRIVE_KM = 100.0
DRIVE_HOURS = DRIVE_KM / AVG_SPEED_KMH
N_FRAMES = DRIVE_HOURS * 3600 * FPS_EVAL

recs = preds['A']
n_gt_all = len(gts)
print(f'行驶 {DRIVE_KM:.0f} km（{DRIVE_HOURS:.2f} h，{N_FRAMES:.0f} 帧）\\n')
print(f"{'阈值':>6s} {'检出数':>7s} {'TP':>6s} {'FP':>6s} {'precision':>10s} "
      f"{'recall':>8s} {'FP/km':>8s} {'FP/h':>8s}")
rows = []
for thr in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    kept = [r for r in recs if r['score'] >= thr]
    tp_ = sum(r['tp'] for r in kept); fp_ = len(kept) - tp_
    prec = tp_ / len(kept) if kept else 1.0
    rec_ = tp_ / n_gt_all
    fp_km = fp_ / DRIVE_KM; fp_h = fp_ / DRIVE_HOURS
    rows.append((thr, prec, rec_, fp_km))
    print(f'{thr:>6.1f} {len(kept):>7d} {tp_:>6d} {fp_:>6d} {prec:>10.4f} '
          f'{rec_:>8.4f} {fp_km:>8.3f} {fp_h:>8.2f}')

precs = [r[1] for r in rows]; recs_ = [r[2] for r in rows]; fpkms = [r[3] for r in rows]
assert precs == sorted(precs), 'precision 随阈值单调上升 —— **它可以被刷**'
assert recs_ == sorted(recs_, reverse=True), 'recall 随阈值单调下降'
assert fpkms == sorted(fpkms, reverse=True), 'FP/km 随阈值单调下降'
print('\\n⚠️  precision 从 %.3f 涨到 %.3f 看起来是「进步」，实际只是砍掉了一半召回。'
      % (precs[0], precs[-1]))
print('✅ FP/km 与 recall **一起动**，取舍暴露出来，没法自欺欺人。')
print('   量级感：FP/km = 0.1 → 每 10 km 一次误报 → 30 km 通勤每天 3 次 → 用户一周内关掉功能。')
print('   量产目标通常是 **FP per 100 km < 1**，触发实际控制动作的关键类还要再严 1-2 个数量级。')"""),
    code("""# ── 工作点选择：在 FP 预算约束下最大化 recall ──
def select_operating_point(rows, fp_per_100km_budget):
    ok = [r for r in rows if r[3] * 100.0 <= fp_per_100km_budget]
    return max(ok, key=lambda r: r[2]) if ok else None

for budget in [500, 100, 30, 10]:
    op = select_operating_point(rows, budget)
    if op:
        print(f'FP/100km 预算 {budget:>4d} → 阈值 {op[0]:.1f}, '
              f'recall {op[2]:.4f}, FP/100km {op[3]*100:.1f}')
    else:
        print(f'FP/100km 预算 {budget:>4d} → **无可行工作点**（需要改模型，不是改阈值）')
op_loose = select_operating_point(rows, 500)
op_tight = select_operating_point(rows, 100)
assert op_loose[2] >= op_tight[2], '预算越紧，可达 recall 越低'
print('\\n✅ 「阈值取多少」不该由算法工程师拍，而应由 **FP 预算**（产品/安全给的）反解。')

# ── per-frame recall vs per-sign recall ──
def per_sign_metrics(det_flags, ranges):
    '''det_flags: 每帧是否检出；ranges: 每帧对应的距离(m)。'''
    n = len(det_flags)
    per_frame = sum(det_flags) / n
    per_sign = 1.0 if any(det_flags) else 0.0
    first = max((r for f, r in zip(det_flags, ranges) if f), default=None)
    return per_frame, per_sign, first

n_fr = 90
ranges = list(np.linspace(100.0, 15.0, n_fr))
flags = [False]*40 + [True, True] + [False, False] + [True]*4 + [False]*2 + \\
        [True, True] + [False] + [True]*4 + [False]*(n_fr - 55)
flags = (flags + [False]*n_fr)[:n_fr]
pf, ps, fr = per_sign_metrics(flags, ranges)
print(f'\\n一块牌子可见 {n_fr} 帧，检出 {sum(flags)} 帧：')
print(f'  per-frame recall = {pf:.3f}   ← 看起来像个失败的系统')
print(f'  per-sign  recall = {ps:.3f}   ← 用户视角：这块牌子被识别了')
print(f'  首次检出距离     = {fr:.1f} m  ← 真正决定体验的量')
assert abs(pf - sum(flags)/n_fr) < 1e-9 and ps == 1.0 and pf < 0.2
print('\\n⚠️  只报 per-frame recall，会让你去优化一个不重要的量（每帧都要检出）。')
print('⚠️  只报 per-sign recall，会掩盖「15 米才第一次检出」这种来不及减速的情况。')
print('✅ 正确的一组：per-sign recall（有没有）+ 首检距离 p50/p90（多远）+ 稳定检出距离（从哪起可信）。')"""),

    md("""## 5 · 时序稳定性指标：mAP 完全看不见的那一半

五个指标：首次**上报**距离 / 稳定检出距离 / 闪烁次数 / 误报持续时长 p95 / 类别跳变率。
注意是「上报」不是「检出」—— 只有测上报，模块 04 的参数才有目标函数。"""),
    code("""def stability_metrics(report_flags, ranges, stable_ratio=0.95):
    '''report_flags: 每帧是否**上报**；ranges: 每帧距离（单调递减）。'''
    n = len(report_flags)
    first_range = max((r for f, r in zip(report_flags, ranges) if f), default=None)
    # 稳定检出距离：最远的起点 i，使得 [i, n) 内上报比例 >= stable_ratio
    stable_range, suffix = None, 0
    for i in range(n - 1, -1, -1):
        suffix += report_flags[i]
        if suffix / (n - i) >= stable_ratio:
            stable_range = ranges[i]
    flips = sum(1 for i in range(1, n) if report_flags[i] != report_flags[i-1])
    return {'first_range': first_range, 'stable_range': stable_range, 'flips': flips}

def fp_episodes(flags, fps=30.0):
    '''把连续的 FP 帧合并成「事件」，返回每个事件的时长（秒）。'''
    eps, run = [], 0
    for f in list(flags) + [False]:
        if f:
            run += 1
        elif run:
            eps.append(run / fps); run = 0
    return eps

# 三个系统：同样的单帧检测器，不同的时序策略（模块 04 的三种配置）
det = ([False]*30                                     # 太远，检不到
       + [True, False, True, True, False, True]       # 30-35 帧：远距离断续检出
       + [True, True, False, True, True, False, False, True, True, True]   # 36-45：仍有抖动
       + [True]*44)                                   # 46 帧起稳定检出
rng_ = list(np.linspace(100.0, 15.0, len(det)))
sys_raw   = det                                                # 无时序处理
sys_vote  = [sum(det[max(0,i-4):i+1]) >= 3 for i in range(len(det))]      # 3-of-5
sys_hyst  = []                                                 # 3-of-5 + 迟滞(撤销要连续 4 帧 miss)
on, miss = False, 0
for i in range(len(det)):
    w = sum(det[max(0, i-4):i+1])
    miss = 0 if det[i] else miss + 1
    on = (w >= 3) if not on else (miss < 4)
    sys_hyst.append(on)

print(f"{'系统':<20s} {'首次上报':>10s} {'稳定检出':>10s} {'状态翻转':>9s}")
for name, s in [('单帧（无时序）', sys_raw), ('3-of-5 投票', sys_vote),
                ('3-of-5 + 迟滞', sys_hyst)]:
    m = stability_metrics(s, rng_)
    print(f'{name:<20s} {m["first_range"]:>9.1f}m {m["stable_range"]:>9.1f}m {m["flips"]:>9d}')

m_raw = stability_metrics(sys_raw, rng_)
m_vote = stability_metrics(sys_vote, rng_)
m_hyst = stability_metrics(sys_hyst, rng_)
assert m_raw['first_range'] > m_vote['first_range'], '投票让首报距离后退（延迟的代价）'
assert m_hyst['flips'] < m_raw['flips'], '迟滞把翻转次数压下来'
assert m_hyst['flips'] <= m_vote['flips'], '迟滞不应比纯投票更抖'
assert m_hyst['stable_range'] >= m_vote['stable_range'], '迟滞让「可信起点」更远'
print('\\n⚠️  **这三行的 mAP 完全相同** —— 逐帧的框和分数一模一样，只是时序策略不同。')
print('   mAP 对模块 04 的全部工作一分收益都不给。')

# 误报持续时长：迟滞的反面账单
fp_raw  = [False]*20 + [True, False, True] + [False]*20 + [True] + [False]*20
fp_hyst = [False]*20 + [True]*8 + [False]*15 + [True]*6 + [False]*15
e_raw, e_hyst = fp_episodes(fp_raw), fp_episodes(fp_hyst)
print(f'\\n误报事件（帧级 FP 合并成事件）:')
print(f'  无迟滞: {len(e_raw)} 次, 时长 {[round(x,3) for x in e_raw]} s, p95={np.percentile(e_raw,95):.3f}s')
print(f'  有迟滞: {len(e_hyst)} 次, 时长 {[round(x,3) for x in e_hyst]} s, p95={np.percentile(e_hyst,95):.3f}s')
assert np.percentile(e_hyst, 95) > np.percentile(e_raw, 95), '迟滞让误报活得更久'
print('\\n✅ **凡是存在此消彼长的一对机制，评测里必须同时有度量两端的指标** ——')
print('   只测闪烁不测误报时长，团队会一路把 τ_off 调到极低：闪烁一片绿，误报赖着三秒不走。')"""),

    md("""## 6 · 回归门禁：显著性检验 + 多重比较校正 + 三档规则

20 个切片各做一次 α=0.05 的检验，即使模型没变，也有 64% 的概率至少出现一个假警报。
**Benjamini–Hochberg (BH-FDR) 是这个场景的正确工具**（Bonferroni 太保守）。"""),
    code("""def norm_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2.0))

def two_prop_pvalue(x_base, n_base, x_cand, n_cand):
    '''单边检验：candidate 的比例是否**显著低于** baseline。返回 p 值。'''
    if n_base == 0 or n_cand == 0:
        return 1.0
    p1, p2 = x_base / n_base, x_cand / n_cand
    p = (x_base + x_cand) / (n_base + n_cand)
    se = math.sqrt(max(p * (1 - p) * (1/n_base + 1/n_cand), 1e-18))
    return float(norm_cdf((p2 - p1) / se))

def bh_reject(pvals, alpha=0.05):
    '''Benjamini-Hochberg：返回被判为显著的下标集合。'''
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    k = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= alpha * rank / m:
            k = rank
    return sorted(order[:k])

# 教科书例子（Benjamini & Hochberg 1995 的经典 p 值列表）
PV = [0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.074, 0.205, 0.212, 0.216]
assert bh_reject(PV, 0.05) == [0, 1], bh_reject(PV, 0.05)
assert len(bh_reject(PV, 0.20)) == 7, bh_reject(PV, 0.20)
bonf = [i for i, p in enumerate(PV) if p <= 0.05 / len(PV)]
assert bonf == [0], 'Bonferroni 只保留 1 个 —— 过于保守'
print(f'BH (α=0.05) 判为显著: {bh_reject(PV, 0.05)}   '
      f'BH (α=0.20): {bh_reject(PV, 0.20)}   Bonferroni (α=0.05): {bonf}')
print('✅ BH 控制的是「被判显著的结论中假阳性的比例」，比 Bonferroni 更适合几十个切片的场景。')

# 假警报率：20 个切片，模型完全没变
g = np.random.default_rng(17)
n_alarm_naive = n_alarm_bh = 0
for _ in range(300):
    ps = [two_prop_pvalue(int(g.binomial(200, 0.85)), 200,
                          int(g.binomial(200, 0.85)), 200) for _ in range(20)]
    n_alarm_naive += any(p <= 0.05 for p in ps)
    n_alarm_bh += len(bh_reject(ps, 0.05)) > 0
print(f'\\n模型完全没变的 300 次重复实验，20 个切片：')
print(f'  不校正：{n_alarm_naive/300:.1%} 的批次至少出现一个「显著劣化」假警报')
print(f'  BH 校正：{n_alarm_bh/300:.1%}')
assert n_alarm_naive / 300 > 0.4, '不校正时假警报率应很高'
assert n_alarm_bh < n_alarm_naive
print('⚠️  一个天天误报的门禁，团队三周内就会学会绕过它 —— 这是门禁系统最常见的死法。')"""),
    code("""# ── 三档门禁判定器 ──
SLICES = [
    # name,                  级别,      baseline(hit, n),   candidate(hit, n), 容差
    ('critical/stop_yield',  'hard',    (209, 220), (196, 220), 0.00),
    ('critical/no_entry',    'hard',    (131, 140), (131, 140), 0.00),
    ('core/all_daylight',    'soft',    (2640, 3000), (2625, 3000), 0.01),
    ('core/all_night',       'soft',    (960, 1200), (948, 1200), 0.01),
    ('fm/small_far',         'soft',    (670, 1000), (620, 1000), 0.01),
    ('fm/occlusion',         'soft',    (192, 240), (190, 240), 0.01),
    ('fm/backlight',         'track',   (128, 180), (120, 180), 0.02),
    ('fm/rain_night',        'track',   (140, 200), (137, 200), 0.02),
]

def gate(slices, alpha=0.05):
    pvals = [two_prop_pvalue(b[0], b[1], c[0], c[1]) for _, _, b, c, _ in slices]
    sig = set(bh_reject(pvals, alpha))
    out, blocking = [], []
    for i, (name, level, b, c, tol) in enumerate(slices):
        rb, rc = b[0]/b[1], c[0]/c[1]
        drop = rb - rc
        if level == 'hard':
            fail = drop > tol + 1e-12
        elif level == 'soft':
            fail = (drop > tol + 1e-12) and (i in sig)
        else:
            fail = False
        out.append((name, level, rb, rc, drop, pvals[i], i in sig, fail))
        if fail:
            blocking.append(name)
    return out, blocking

rep, blocking = gate(SLICES)
print(f"{'切片':<22s} {'档':<6s} {'base':>7s} {'cand':>7s} {'跌幅':>7s} "
      f"{'p值':>8s} {'BH显著':>7s} {'判定'}")
for name, lv, rb, rc, dr, pv, s, f in rep:
    print(f'{name:<22s} {lv:<6s} {rb:>7.3f} {rc:>7.3f} {dr:>+7.3f} '
          f'{pv:>8.3f} {"是" if s else "否":>7s} {"❌ 阻断" if f else "✅ 通过"}')
print(f'\\n阻断项: {blocking}')
assert 'critical/stop_yield' in blocking, '关键类掉了 13 个样本，硬门禁必须拦住'
assert 'critical/no_entry' not in blocking, '没跌就不该拦（硬门禁不是「一律拦」）'
assert 'fm/small_far' in blocking, '软门禁：跌幅超容差 + BH 显著 -> 阻断'
assert 'core/all_night' not in blocking, '软门禁：跌幅未超容差 -> 通过'
assert 'fm/backlight' not in blocking, '观察项不阻断（哪怕掉了 4.4 个点）'
assert all(not r[7] for r in rep if r[1] == 'track')
print('\\n✅ 三档设计的意义：硬门禁少而绝对（关键类、FP 上限、p99 延迟）；')
print('   软门禁需要**同时满足「跌幅超容差」和「统计显著」**；观察项只记趋势。')
print('⚠️  容差必须来自**种子方差**（跑 3-5 个种子测自然波动，取 2σ），不能拍脑袋。')
print('⚠️  门禁必须可 override，但每次覆盖要记录理由与责任人 ——')
print('   同一条门禁被覆盖三次，要么阈值定错了，要么你们有一个一直没修的真问题。')"""),

    md("""## 7 · 离线-路测背离：分母不匹配到底让你低估了多少

评测集里 80% 的帧含标志，真实道路只有 5%。
而误检主要发生在**无标志的背景帧**上 —— 这类帧在评测集里被严重欠采样。"""),
    code("""Q_BG, Q_SIGN = 0.004, 0.001          # 背景帧 / 含标志帧的每帧误检率
def fp_per_frame(pi_bg):
    return pi_bg * Q_BG + (1 - pi_bg) * Q_SIGN

PI_EVAL, PI_ROAD = 0.20, 0.95        # 评测集 vs 真实道路的背景帧占比
KM, HOURS = 60.0, 1.0
FRAMES_ROAD = HOURS * 3600 * 30

fp_eval_rate = fp_per_frame(PI_EVAL)
fp_road_rate = fp_per_frame(PI_ROAD)
naive_fp = fp_eval_rate * FRAMES_ROAD          # 天真外推
true_fp = fp_road_rate * FRAMES_ROAD

print(f"{'':<26s} {'背景帧占比':>10s} {'FP/帧':>10s} {'外推到 60km 的 FP 数':>20s} {'FP/km':>8s}")
print(f'{"评测集（天真外推）":<26s} {PI_EVAL:>10.2f} {fp_eval_rate:>10.5f} '
      f'{naive_fp:>20.0f} {naive_fp/KM:>8.2f}')
print(f'{"真实道路":<26s} {PI_ROAD:>10.2f} {fp_road_rate:>10.5f} '
      f'{true_fp:>20.0f} {true_fp/KM:>8.2f}')
ratio = true_fp / naive_fp
print(f'\\n低估倍数 = {ratio:.2f}×   ← 「离线看起来达标」的版本会在路测第一天被否掉')
assert ratio > 2.0, f'低估倍数应超过 2 倍，得到 {ratio:.2f}'
assert abs(fp_eval_rate - 0.0016) < 1e-9 and abs(fp_road_rate - 0.00385) < 1e-9

# 修法②：按真实 π_bg 对两类帧重新加权
def reweighted_fp_rate(n_bg_eval, fp_bg, n_sign_eval, fp_sign, pi_bg_road):
    q_bg = fp_bg / max(n_bg_eval, 1); q_sign = fp_sign / max(n_sign_eval, 1)
    return pi_bg_road * q_bg + (1 - pi_bg_road) * q_sign

n_bg_e, n_sg_e = 400, 1600
fp_bg_e, fp_sg_e = n_bg_e * Q_BG, n_sg_e * Q_SIGN
rw = reweighted_fp_rate(n_bg_e, fp_bg_e, n_sg_e, fp_sg_e, PI_ROAD)
print(f'\\n重加权后的估计: {rw:.5f} FP/帧  (真值 {fp_road_rate:.5f})  '
      f'误差 {abs(rw-fp_road_rate)/fp_road_rate:.1%}')
assert abs(rw - fp_road_rate) < 1e-9, '重加权应精确还原真实 FP 率'

# 帧级 vs 事件级：用户感受的是「几次」，不是「几帧」
AVG_EPISODE_FRAMES = 9
print(f'\\n帧级: {true_fp:.0f} 个 FP **帧** / 小时')
print(f'事件级: {true_fp/AVG_EPISODE_FRAMES:.0f} 次 FP **事件** / 小时'
      f'（每次约 {AVG_EPISODE_FRAMES/30:.2f} s）')
assert true_fp / AVG_EPISODE_FRAMES < true_fp / 5
print('\\n✅ 修法①（唯一诚实的做法）：显式保留一批**连续里程片段**，')
print('   哪怕大部分帧没有标志，专门用来测 FP/km。')
print('✅ 修法②：按真实 π_bg 对两类帧重新加权再汇总。')
print('⚠️  这个偏差是**结构性的**：标注是按「有目标的片段」组织的，')
print('   标注供应商没有动力去标一万帧空旷的高速路 —— 评测集天然过采样含标志帧。')"""),

    md("""## ✏️ 练习 1：COCO 风格的 mAP@[.5:.95]

实现 `coco_map(gt_boxes, dets, thrs=None)`：在 IoU 阈值 `0.50, 0.55, ..., 0.95`（共 10 档）
上分别算 AP 再取平均。可以复用 `match_frame` 与 `average_precision`。"""),
    code("""def coco_map(gt_boxes, dets, thrs=None):
    # TODO: thrs 默认 [0.50, 0.55, ..., 0.95]（10 档）
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
g1 = [np.array([0., 0., 100., 100.])]
perfect = [(np.array([0., 0., 100., 100.]), 0.9)]
assert abs(coco_map(g1, perfect) - 1.0) < 1e-9, '完美定位在所有阈值上都应是 1.0'

# 构造 IoU 恰好 = 0.6 的预测：交 = 0.6 * 并
#   宽 100 的框平移 d：IoU = (100-d)/(100+d) = 0.6  ->  d = 25
d = 25.0
iou06 = [(np.array([d, 0., 100. + d, 100.]), 0.9)]
assert abs(iou(g1[0], iou06[0][0]) - 0.6) < 1e-9, iou(g1[0], iou06[0][0])
m = coco_map(g1, iou06)
# 只在 0.50 / 0.55 / 0.60 三档上算命中 -> 3/10 = 0.3
assert abs(m - 0.3) < 1e-9, f'IoU=0.6 的预测 mAP@[.5:.95] 应为 0.3，得到 {m}'
assert abs(coco_map(g1, iou06, thrs=[0.5]) - 1.0) < 1e-9, 'AP@0.5 应为 1.0'
assert abs(coco_map(g1, iou06, thrs=[0.65]) - 0.0) < 1e-9, 'AP@0.65 应为 0.0'
assert coco_map(g1, []) == 0.0, '没有任何预测时应为 0.0'

print(f'完美定位 mAP@[.5:.95] = {coco_map(g1, perfect):.3f}')
print(f'IoU=0.60 mAP@[.5:.95] = {m:.3f}   （AP@0.5 却是 1.000）')
print('✅ 练习 1 通过：**COCO mAP 把一半权重压在 IoU>0.75 上** ——')
print('   对 TSR 而言那段区间没有下游价值，用它做主指标是把优化力气引向错误的方向。')"""),

    md("""## ✏️ 练习 2：代价加权风险分

实现 `risk(confusion, cost_miss, cost_fp, cost_conf, dist_km)`，其中
`confusion` 是 `{(c_true, c_pred): n}`，`c_pred` 为 `None` 表示漏检、
`c_true` 为 `None` 表示误检。返回 **每 100 km 的风险分**。
未在 `cost_conf` 中列出的错分对，代价取 `max(cost_miss[c_true], cost_fp[c_pred]) * 0.6`。"""),
    code("""def risk(confusion, cost_miss, cost_fp, cost_conf, dist_km):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
CM = {'stop': 100.0, 'sp60': 8.0, 'sp80': 8.0}
CF = {'stop': 20.0, 'sp60': 12.0, 'sp80': 12.0}
CC = {('sp60', 'sp80'): 15.0, ('sp80', 'sp60'): 2.0}

assert abs(risk({('stop', None): 1}, CM, CF, CC, 100.0) - 100.0) < 1e-9
assert abs(risk({(None, 'sp60'): 2}, CM, CF, CC, 100.0) - 24.0) < 1e-9
assert abs(risk({('sp60', 'sp80'): 1}, CM, CF, CC, 100.0) - 15.0) < 1e-9
assert abs(risk({('sp80', 'sp60'): 1}, CM, CF, CC, 100.0) - 2.0) < 1e-9, '方向不对称'
# 未列出的错分对：max(100, 12) * 0.6 = 60
assert abs(risk({('stop', 'sp60'): 1}, CM, CF, CC, 100.0) - 60.0) < 1e-9
# 里程归一化：同样的错误跑 50 km，风险分翻倍
assert abs(risk({('stop', None): 1}, CM, CF, CC, 50.0) - 200.0) < 1e-9
# 正确预测不计代价
assert abs(risk({('sp60', 'sp60'): 999}, CM, CF, CC, 100.0)) < 1e-9

mix = {('stop', None): 2, (None, 'sp80'): 3, ('sp60', 'sp80'): 4, ('sp80', 'sp60'): 4}
print(f'混合场景风险分 = {risk(mix, CM, CF, CC, 100.0):.1f} / 100km')
assert abs(risk(mix, CM, CF, CC, 100.0) - (200 + 36 + 60 + 8)) < 1e-9
print('✅ 练习 2 通过：**同一对类别，两个方向的代价可以差 7.5 倍** ——')
print('   这一层不对称是 mAP 结构上无法表达的。')"""),

    md("""## ✏️ 练习 3：时序稳定性指标

实现 `temporal_report(report_flags, ranges, fps=30.0, stable_ratio=0.95)`，返回
`{'first_range', 'stable_range', 'flips', 'on_ratio', 'longest_off_s'}`。
`longest_off_s` 是**已上报之后**出现的最长连续未上报时长（秒）——它度量「输出闪断」。
若从未上报，`first_range` / `stable_range` 为 `None`，其余为 0。"""),
    code("""def temporal_report(report_flags, ranges, fps=30.0, stable_ratio=0.95):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
rg = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0]
f1 = [False, True, False, False, True, True, True, True]
r1 = temporal_report(f1, rg)
assert r1['first_range'] == 90.0, r1
assert r1['stable_range'] == 60.0, f"从 60m 起 4/4 都上报，得到 {r1['stable_range']}"
assert r1['flips'] == 3, r1                       # F->T, T->F, F->T
assert abs(r1['on_ratio'] - 5/8) < 1e-9
assert abs(r1['longest_off_s'] - 2/30) < 1e-9, '首次上报后最长断了 2 帧'

f2 = [False] * 8
r2 = temporal_report(f2, rg)
assert r2['first_range'] is None and r2['stable_range'] is None
assert r2['flips'] == 0 and r2['on_ratio'] == 0.0 and r2['longest_off_s'] == 0.0

f3 = [True] * 8
r3 = temporal_report(f3, rg)
assert r3['first_range'] == 100.0 and r3['stable_range'] == 100.0
assert r3['flips'] == 0 and r3['longest_off_s'] == 0.0

for nm, f in [('闪断型', f1), ('全无', f2), ('完美', f3)]:
    r = temporal_report(f, rg)
    print(f'{nm:<6s} first={r["first_range"]} stable={r["stable_range"]} '
          f'flips={r["flips"]} on={r["on_ratio"]:.2f} longest_off={r["longest_off_s"]:.3f}s')
print('✅ 练习 3 通过：**首报距离、稳定距离、闪断时长三个数必须一起看** ——')
print('   任何一个单独拿出来都能被优化成好看的样子。')"""),

    md("""## ✏️ 练习 4：多重比较校正下的门禁判定

实现 `gate_decide(slices, alpha=0.05)`：`slices` 每项为
`(name, level, (hit_base, n_base), (hit_cand, n_cand), tol)`，`level ∈ {'hard','soft','track'}`。
用 `two_prop_pvalue` + `bh_reject` 做校正，返回 `(报告列表, 阻断项名单)`：
- `hard`：跌幅 > tol 就阻断（**不看显著性**——关键类不能等统计显著）
- `soft`：跌幅 > tol **且** BH 判为显著才阻断
- `track`：永不阻断"""),
    code("""def gate_decide(slices, alpha=0.05):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
S = [('crit/stop',  'hard',  (100, 100), (99, 100), 0.00),   # 跌 0.01 > 0 -> 阻断
     ('crit/entry', 'hard',  (100, 100), (100, 100), 0.00),  # 没跌 -> 通过
     ('core/day',   'soft',  (900, 1000), (880, 1000), 0.005),
     ('core/night', 'soft',  (900, 1000), (897, 1000), 0.005),  # 跌 0.003 < tol -> 通过
     ('fm/backlit', 'track', (50, 100), (30, 100), 0.00)]    # 掉惨了但只是观察项
rep_, block_ = gate_decide(S)
assert 'crit/stop' in block_ and 'crit/entry' not in block_
assert 'fm/backlit' not in block_, '观察项永不阻断'
assert 'core/night' not in block_, '跌幅在容差内不阻断'
assert len(rep_) == len(S)

# hard 档不看显著性：只跌 1 个样本，p 值远不显著，但仍必须阻断
p_stop = two_prop_pvalue(100, 100, 99, 100)
assert p_stop > 0.05, f'该切片统计上不显著（p={p_stop:.3f}），但硬门禁仍要拦'
print(f'crit/stop 的 p 值 = {p_stop:.3f}（不显著），但硬门禁仍然阻断 ✅')

# soft 档：同样的跌幅，样本量大才会被判显著
big = [('a', 'soft', (8500, 10000), (8400, 10000), 0.005)]
small = [('a', 'soft', (85, 100), (84, 100), 0.005)]
assert gate_decide(big)[1] == ['a'], '大样本 -> 显著 -> 阻断'
assert gate_decide(small)[1] == [], '小样本 -> 不显著 -> 不阻断'
print('大样本切片跌 0.01 -> 阻断；小样本切片跌 0.01 -> 不阻断（证据不足）✅')
print(f'\\n本次阻断项: {block_}')
print('✅ 练习 4 通过：**关键类的硬门禁不能等统计显著** ——')
print('   等到 40 个 stop 样本里的差异「统计显著」，事故已经发生很多次了。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def coco_map(gt_boxes, dets, thrs=None):
    if thrs is None:
        thrs = [0.50 + 0.05 * i for i in range(10)]
    aps = []
    for t in thrs:
        tp = match_frame(gt_boxes, dets, iou_thr=t)
        aps.append(average_precision([d[1] for d in dets], tp, len(gt_boxes)))
    return float(np.mean(aps))"""),
    code("""# 练习 2 参考答案
def risk(confusion, cost_miss, cost_fp, cost_conf, dist_km):
    total = 0.0
    for (ct, cp), n in confusion.items():
        if ct == cp:
            continue                                   # 正确预测
        if cp is None:                                 # 漏检
            total += n * cost_miss[ct]
        elif ct is None:                               # 误检
            total += n * cost_fp[cp]
        elif (ct, cp) in cost_conf:                    # 显式列出的错分对
            total += n * cost_conf[(ct, cp)]
        else:                                          # 未列出：取较重一侧打折
            total += n * max(cost_miss[ct], cost_fp[cp]) * 0.6
    return total / dist_km * 100.0"""),
    code("""# 练习 3 参考答案
def temporal_report(report_flags, ranges, fps=30.0, stable_ratio=0.95):
    n = len(report_flags)
    on_idx = [i for i, f in enumerate(report_flags) if f]
    if not on_idx:
        return {'first_range': None, 'stable_range': None,
                'flips': 0, 'on_ratio': 0.0, 'longest_off_s': 0.0}
    first_range = max(ranges[i] for i in on_idx)
    stable_range, suffix = None, 0
    for i in range(n - 1, -1, -1):                     # 从后往前找最远的稳定起点
        suffix += report_flags[i]
        if suffix / (n - i) >= stable_ratio:
            stable_range = ranges[i]
    flips = sum(1 for i in range(1, n) if report_flags[i] != report_flags[i-1])
    longest, run = 0, 0
    for i in range(on_idx[0], n):                      # 只统计首次上报之后
        run = 0 if report_flags[i] else run + 1
        longest = max(longest, run)
    return {'first_range': first_range, 'stable_range': stable_range,
            'flips': flips, 'on_ratio': len(on_idx) / n,
            'longest_off_s': longest / fps}"""),
    code("""# 练习 4 参考答案
def gate_decide(slices, alpha=0.05):
    pvals = [two_prop_pvalue(b[0], b[1], c[0], c[1]) for _, _, b, c, _ in slices]
    sig = set(bh_reject(pvals, alpha))
    report_, blocking = [], []
    for i, (name, level, b, c, tol) in enumerate(slices):
        rb, rc = b[0] / b[1], c[0] / c[1]
        drop = rb - rc
        if level == 'hard':
            fail = drop > tol + 1e-12                  # 关键类不等统计显著
        elif level == 'soft':
            fail = (drop > tol + 1e-12) and (i in sig)
        else:
            fail = False
        report_.append({'name': name, 'level': level, 'base': rb, 'cand': rc,
                        'drop': drop, 'p': pvals[i], 'significant': i in sig,
                        'blocked': fail})
        if fail:
            blocking.append(name)
    return report_, blocking"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接落地的 TSR 评测记分卡与流水线"""),
    code("""RECIPE = r'''
# ═══════════════════════════════════════════════════════════════════
# TSR 评测记分卡 scorecard.json —— 结构模板
# 不变量：**「存在一份 scorecard.json」本身就编码了「该版本通过了评测」**
#         没有 scorecard 的产物一律不允许进入发布流程。
# ═══════════════════════════════════════════════════════════════════
{
  "provenance": {                       # ← 可复现性的全部输入，缺一不可
    "model_commit": "a3f9c1e", "config_hash": "sha256:8c21...",
    "dataset_version": "tsr_eval_v7.2", "eval_code_commit": "b71d0aa",
    "seed": 0, "tta": false, "postproc": {"score_thr": 0.35, "nms_iou": 0.6},
    "runtime": "trt-8.6 / orin-x / fp16", "timestamp": "2026-08-17T09:12:03Z"
  },

  "primary": {                          # ← **唯一的优化目标**，用于排序模型
    "risk_score_per_100km": 21.4, "baseline": 23.9, "delta": -2.5
  },

  "guardrails": [                       # ← 硬约束，任一超限直接阻断发布
    {"name": "fp_per_100km_overall",      "value": 0.62, "limit": 1.0,  "ok": true},
    {"name": "fp_per_100km_critical",     "value": 0.004,"limit": 0.01, "ok": true},
    {"name": "per_sign_recall_stop_yield","value": 0.968,"min": 0.965,  "ok": true},
    {"name": "first_report_range_p50_m",  "value": 72.4, "min": 70.0,   "ok": true},
    {"name": "flicker_per_sign",          "value": 0.31, "limit": 1.0,  "ok": true},
    {"name": "fp_episode_p95_s",          "value": 0.43, "limit": 0.5,  "ok": true},
    {"name": "latency_p99_ms",            "value": 11.8, "limit": 15.0, "ok": true}
  ],

  "slices": [                           # ← 诊断层：不进门禁，用于**解释**主指标
    {"name": "size/<16px",  "n_pos": 412, "ap": 0.512, "ci95": [0.471, 0.556]},
    {"name": "size/16-32px","n_pos": 1180,"ap": 0.804, "ci95": [0.788, 0.821]},
    {"name": "dist/>80m",   "n_pos": 290, "ap": 0.441, "ci95": [0.392, 0.489]},
    {"name": "light/night", "n_pos": 860, "ap": 0.712, "ci95": [0.690, 0.735]},
    {"name": "night x >80m","n_pos": 96,  "ap": 0.310, "ci95": [0.230, 0.395]}
  ],

  "gate": {"alpha": 0.05, "correction": "benjamini-hochberg",
           "blocking": [], "overrides": []},   # override 必须记录理由 + 责任人
  "verdict": "PASS"
}

# ═══════════════════════════════════════════════════════════════════
# 评测流水线（每一步的产物与门禁条件）
# ═══════════════════════════════════════════════════════════════════
# ① 推理     固定 seed / 关 TTA / 固定后处理参数 / 记录 runtime
#            产物: raw_predictions.jsonl（**必须归档** —— 指标口径变了要能重算）
# ② 指标     评测代码有单元测试（完美预测=1.0 / 全空=0.0 / 手算例子）
#            产物: metrics_raw.json
# ③ 切片     分桶 x 类别 x 时序，**全部带 bootstrap CI**
#            规则: 每桶 >= 50 正样本，否则降级为「观察项」
# ④ 对比     配对检验 + BH-FDR 多重比较校正（20 个切片不校正 = 64% 假警报率）
#            容差来自**种子方差**：跑 3-5 个种子测自然波动，取 2σ
# ⑤ 门禁     hard（不等显著性）/ soft（跌幅+显著性）/ track（只记趋势）
#            产物: scorecard.json  → 通过才允许打包发布
#
# ═══════════════════════════════════════════════════════════════════
# 连续里程片段（唯一诚实测 FP/km 的方式）
# ═══════════════════════════════════════════════════════════════════
# continuous_drives/          **大部分帧没有标志，这正是重点**
#   ├── highway_day_120km/    背景帧占比 ~0.96，接近真实分布
#   ├── urban_night_40km/     广告牌密集，FP 主战场
#   └── tunnel_series_15km/   出入口过曝/欠曝
# 用途：只算 FP/km、FP/hour、误报事件数与持续时长；**不算 mAP**（正样本太少）
#
# ⚠️ 常规评测集会过采样含标志帧（π_bg≈0.2 vs 真实 0.95）
#    -> 天真外推会把 FP/km 低估约 2.4 倍
#    -> 修法①用连续里程片段  修法②按真实 π_bg 重加权
'''
print(RECIPE)
for key in ['provenance', 'risk_score_per_100km', 'fp_per_100km_critical',
            'first_report_range_p50_m', 'fp_episode_p95_s', 'benjamini-hochberg',
            'ci95', 'raw_predictions.jsonl', 'continuous_drives', '2σ']:
    assert key in RECIPE, key
print('✅ 配方覆盖：可复现性字段 / 主指标 / 7 条护栏 / 分桶+CI / BH 校正 / '
      '三档门禁 / 连续里程片段 / 分母不匹配')"""),

    md("""### 小结

- **mAP 有五个盲区**：①按类别平均把关键类稀释（一个类掉 20 点，60 类 mAP 只掉 0.33，
  落在种子噪声内）②与距离/尺寸无关 ③完全没有时序（闪 15 次/秒和稳定输出的 mAP 一样）
  ④precision 是相对量，分母是系统自己的输出、**可以靠提阈值刷** ⑤与下游动作脱节
  （框准 0.05 IoU 没价值，60 认成 80 是灾难）。
  **mAP 是迭代信号，不是发布判据。**
- **分桶是解药，但有统计代价**：每桶 ≥50 正样本、所有分桶指标必须带 bootstrap CI；
  显式建立 3–5 个安全关键的**交叉桶**（夜间×远距）；
  **micro/macro 的选择会翻转模型排名**，TSR 默认用 macro。
- **代价三层不对称**：类别之间、错误方向之间（60→80 比 80→60 危险 7.5 倍）、
  漏检与误检之间。写成代价矩阵后，**风险分（代价/100km）替代 mAP 成为唯一主指标**，
  且能逐项归因。代价数值要从 HARA/FMEA 反推，有文档有版本号。
- **换分母**：precision → **FP per km**（分母是里程，不可刷、可跨系统比、直接对应体验，
  量产目标 FP/100km < 1）；per-frame recall → **per-sign recall + 首检距离分布**。
  判据：分母是系统自己的输出就会被污染，分母是外生物理量才诚实。
- **时序稳定性五指标**：首次**上报**距离 / 稳定检出距离 / 闪烁次数 / 误报持续时长 p95 /
  类别跳变率。**凡是存在此消彼长的一对机制，评测里必须同时度量两端**，否则优化会滑向一边。
  前提：标注必须有物理标志级的 instance ID —— **评测指标决定标注规范**。
- **门禁三档**：hard（关键类、FP 上限、p99 延迟——**不等统计显著**）/
  soft（跌幅 + BH 显著）/ track（只记趋势）。容差来自种子方差（2σ）；
  20 个切片不做多重比较校正会有 64% 的假警报率；**门禁必须可 override 但要留记录**。
- **离线-路测背离七因**，头号是**分母不匹配**：评测集 π_bg≈0.2 而真实道路 ≈0.95，
  天真外推把 FP/km **低估约 2.4 倍**。唯一诚实的修法是保留一批**连续里程片段**。
- **「Build and maintain evaluation pipelines」的满分答案骨架**：
  ①评测产出的是决策不是数字（主指标/护栏/诊断的分层）
  ②评测本身是要被测试的软件（单测、数据版本、raw prediction 归档）
  ③评测要贴着线上分布（分母不匹配、连续里程片段、偏差的量化）。

本课到此结束。回看整门课：模块 01 定义了数据与类别体系，02 定了系统架构，
03 列全了失效模式，04 把单帧变成稳定输出，05 给出了判断这一切好坏的尺子。
**下一步去 C57（小目标）与 C58（数据闭环）—— 它们回答的是「指标不够好时该做什么」。**"""),
]
