# -*- coding: utf-8 -*-
"""C55 模块 02 · TSR 系统设计：两级 vs 端到端。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（TSR 任务定义、数据集与分类体系）；C18/C53 的检测基础；概率与贝叶斯基本功"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_tsr_pipeline_design.ipynb'),
    ("核心参考", "级联检测器（Viola-Jones 起）、GTSRB/TT100K 的两级基线、置信度标定（Guo et al. 2017）、开集识别综述"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("task", "先把任务拆开：TSR 不是「一个检测器」", "".join([
        P("很多人一听「交通标志识别」就想到「训练一个多类检测器」。这个直觉在 demo 上成立，在量产系统里几乎必然崩掉。原因是 <strong>TSR 的输出不是一个框加一个类别，而是一条从像素到可执行约束的链路</strong>——每一段都有自己的失败方式、自己的迭代节奏、自己的算力预算。"),
        ASCII("""图像帧
  │
  ├─[1] 定位  Where?     → 框 (x, y, w, h)          ← 目标常常只有 12×12 px
  │
  ├─[2] 识别  What?      → 细类 (限速60 / 禁止左转 / …)  ← 类别数 200+，极度长尾
  │
  ├─[3] 属性  Which one? → 状态、有效性、附加牌语义
  │                         · 电子牌当前显示值
  │                         · 是否被遮挡 / 褪色 / 破损
  │                         · 「限重 10t」「雨天」这类辅助牌条件
  │
  └─[4] 关联  For me?    → 这块牌管哪条车道 / 哪个方向 / 从哪里开始生效
                            ← 对向车道、辅路、匝道的牌**不该管我**

  最终交付给下游（规控 / VLA）的其实是 [1]+[2]+[3]+[4] 的合成结果：
      「本车道，前方 42 m 起，限速 60，置信度 0.93，已连续确认 7 帧」"""),
        P("把这四段并列写出来，两个工程结论立刻浮现："),
        UL([
            "<strong>它们的难度与数据需求完全不同</strong>。[1] 定位是几何问题，对光照/分辨率敏感，但类别无关，数据可以跨类别共享；[2] 识别是细粒度分类问题，受长尾支配，且新类别会不断出现；[4] 关联几乎是几何+地图问题，和像素关系不大。",
            "<strong>它们的迭代节奏不同</strong>。新增一个标志类别（比如某省新启用的一种警示牌），[2] 需要改；[1] 完全不需要改——因为「一块蓝底白字的矩形牌」在几何上和以前的牌没有区别。<em>如果你把它们塞进同一个多类检测器，加一个类就得重训整个检测器，还要重新验证所有旧类不掉点。</em>",
        ]),
        DUAL(
            "所以「两级 vs 端到端」这个问题的真正含义不是「哪个 mAP 高」，而是 <strong>「[1] 和 [2] 该不该共用同一组参数与同一次训练」</strong>。端到端多类检测器的回答是「该」——一次前向同时输出位置和细类；两级方案的回答是「不该」——先用一个类别无关（class-agnostic）或粗类的检测器找出所有「牌状物」，再把每个 crop 送进一个专门的分类器。",
            "更精确地说，这是一个 <span class=\"term\">factorization</span>（因式分解）选择。端到端建模的是联合分布 <code>p(box, class | image)</code>；两级把它分解成 <code>p(box | image) · p(class | crop(box))</code>。<em>分解的合理性依赖一个条件独立假设：给定 crop，类别与图像的其余部分无关。</em>这个假设在 TSR 里近似成立（标志的语义几乎完全写在牌面上），但不完全成立——比如同一个圆形红边牌在高速与市区含义可能不同，上下文被 crop 丢掉了。<strong>知道这个假设在哪里失效，是这一节最值钱的部分。</strong>",
        ),
        CALLOUT("intuition", "一句话记住整节：<strong>检测器解决「像不像一块牌」，分类器解决「是哪块牌」——这是两个统计性质完全不同的问题，把它们分开，你就获得了分别优化它们的自由。</strong>而这个自由值多少钱，取决于你的类别有多长尾、新类来得有多频繁。"),
    ])),

    ("motivation", "两级方案的四个动机（以及它们各自的适用条件）", "".join([
        P("两级（two-stage / detect-then-classify）方案在 TSR 里几乎是工业界默认答案。它的四个动机不是并列的口号，每一条都对应一个可以量化的收益，也各自有一个「什么时候不成立」的边界。<strong>面试里被问「为什么用两级」，逐条讲清动机 + 边界，比背四个名词强十倍。</strong>"),
        ASCII("""【端到端多类检测】
  1920×1080 ──▶ Detector(200+ 类) ──▶ (box, class, score)
                     ▲
                     └── 每个类别的正样本都要从整图里学：
                         「限速 5」全数据集只有 40 个实例 → 学不动

【两级：检测 → 分类】
  1920×1080 ──▶ Detector(1~5 粗类) ──▶ box ──┐
                  「牌状物」，样本量 = 全部标志之和         │
                                                          ▼
                                            crop + 放大到 96×96
                                                          │
                                                          ▼
                                            Classifier(200+ 细类)
                                            ▲ 输入已归一化：尺度、位置都不再是变量
                                            └─ 长尾在这里单独治，重采样/重加权代价极低""")
        ,
        TABLE(["动机", "具体收益", "为什么两级能做到", "什么时候这条动机不成立"], [
            ["<strong>① 长尾解耦</strong>",
             "检测器的正样本从「某一类的 40 个」变成「全部类的 12 万个」；分类器可以随意重采样而不影响检测",
             "检测器只学「牌状物」这一个概念，所有类别的实例都是它的正样本；分类阶段输入是已裁好的 crop，重采样 = 改 sampler，代价几乎为零",
             "类别本身在<em>几何上</em>差异巨大（如八角形 STOP vs 长条形指路牌）时，粗类合并会让检测器的回归目标变得多模态 → 要拆成 3–5 个粗类而非 1 个"],
            ["<strong>② 增类不重训检测器</strong>",
             "新增一个标志类别只需重训分类器（分钟~小时级），检测器权重与验证结果全部复用",
             "新类的<em>几何外观</em>属于已有粗类（圆形禁令牌），检测器本来就能框到它",
             "新类的几何形态前所未见（如新出现的电子矩阵屏），检测器没见过 → 仍要补检测数据"],
            ["<strong>③ 分类器可用更高分辨率</strong>",
             "远处 16×16 的牌，检测阶段在下采样特征图上只有半个格子；crop 后上采样到 96×96 送分类器，<strong>有效像素密度提升 6×</strong>（后文有账）",
             "分类器的输入是一小块 ROI，全分辨率处理它的算力开销 = 整图的 (96/1920)² ≈ 0.25%",
             "牌本身的物理像素就只有 12×12，上采样不能凭空造信息 —— 提升的是<em>网络能分配给它的计算量</em>，不是信息量"],
            ["<strong>④ 可独立迭代</strong>",
             "定位问题（漏检远处小牌）与识别问题（限速 60/80 混淆）可以由不同的人、不同的数据、不同的评测集并行推进",
             "两级之间的接口是「crop + 框」，这是一个稳定、可版本化、可离线缓存的中间产物",
             "接口本身要改时（如决定给 crop 加更多 padding），两边都要重训 —— 接口设计错了，独立性就是假的"],
        ]),
        P("代价同样要背下来，<strong>只讲收益不讲代价是面试里最典型的减分项</strong>："),
        TABLE(["代价", "量级", "缓解手段"], [
            ["<strong>延迟叠加</strong>", "检测 8 ms + N 个 crop × 分类 0.4 ms。N=20 时分类阶段就是 8 ms，直接翻倍", "batch 化所有 crop 一次前向；上限 N（按分数 top-k 截断）；分类器做得极小（MobileNet 级）"],
            ["<strong>误差级联</strong>", "检测漏掉的，分类器<strong>永远救不回来</strong> —— 这是本模块的核心公式，下一节展开", "检测阶段用低阈值宁滥勿缺，把去伪的责任交给分类器（含 background 类）"],
            ["<strong>工程复杂度</strong>", "两个模型、两套数据、两套评测、两条部署流水线；端到端指标要自己拼", "把两级封成一个 ONNX/TensorRT 图；建立联合评测脚本（见模块 05）"],
            ["<strong>置信度不可比</strong>", "检测分数与分类分数是两个不同尺度的东西，直接相乘会得到一个没有概率语义的数", "分别标定后再合成 —— 第 6 节的主题"],
        ]),
        CALLOUT("warn", "一个高频误解：<strong>「两级 = R-CNN 那种 two-stage 检测器」</strong>。不是。Faster R-CNN 的两阶段（RPN → RoI head）在<em>同一个网络、同一次训练、共享 backbone</em> 里，梯度是打通的；这里说的两级是<strong>两个独立训练、独立部署的模型</strong>，中间隔着一次真实的图像裁剪。<em>面试里如果你把这两个概念混着说，对方会立刻判断你没真的做过量产系统。</em>"),
    ])),

    ("cascade", "核心公式：级联召回 = 检测召回 × 分类准确率", "".join([
        P("这一节是整个模块的心脏。所有关于「两级到底行不行」的争论，最后都会归约到一个乘法。"),
        MATH("R_{\\text{end2end}} \\;=\\; R_{\\text{det}} \\times A_{\\text{cls}}"),
        P("其中 <code>R_det</code> 是检测阶段的召回（有多少真实标志被框到，且 IoU 达标），<code>A_cls</code> 是分类阶段在<em>这些被框到的 crop</em> 上的准确率。<strong>注意这是条件准确率</strong>：分子分母都只统计检测已经框到的样本。更一般地，如果每一级的通过率是 <code>p_i</code>，那么"),
        MATH("R_{\\text{cascade}} \\;=\\; \\prod_{i=1}^{K} p_i \\qquad\\Longrightarrow\\qquad \\log R_{\\text{cascade}} \\;=\\; \\sum_{i=1}^{K} \\log p_i"),
        P("取对数之后，级联的性质变得一目了然：<strong>各级的损失在对数域上是相加的，且没有任何一级能补偿另一级的损失。</strong>这直接推出三条反直觉但极其实用的结论。"),
        TABLE(["结论", "数值示例", "工程含义"], [
            ["<strong>① 90% × 90% = 81%，不是 90%</strong>",
             "检测召回 0.90、分类准确率 0.90 → 端到端 0.81。两个「看起来还行」的模块合起来是「不能用」",
             "<em>永远不要用分级指标去汇报系统性能。</em>汇报必须是端到端的"],
            ["<strong>② 边际收益取决于另一级</strong>",
             "R_det 0.90→0.95（+5.6%），若 A_cls=0.99 则端到端 +5.5%；若 A_cls=0.70 则端到端只 +3.5%",
             "<strong>∂R/∂p_i = R/p_i</strong> —— 改进哪一级收益大，要看当前 R 和该级的 p。<em>短板优先，但短板的定义是「1-p 最大」而不是「p 最小的绝对值」</em>"],
            ["<strong>③ 级数越多越危险</strong>",
             "5 级各 0.98 → 0.98⁵ = 0.904。每加一级，就多一次乘法",
             "这是「不要为了工程优雅而多分几级」的定量理由。TSR 两级已经是甜点，三级（检测→粗类→细类）要有很强的理由"],
        ]),
        DUAL(
            "第 ② 条值得展开，因为它决定你下个季度做什么。假设当前 R_det = 0.92、A_cls = 0.94，端到端 0.865。现在你有两个候选项目：把检测召回提到 0.95（+0.03），或把分类准确率提到 0.97（+0.03）。<strong>两者对端到端的贡献恰好相等吗？</strong>算一下：0.95×0.94 = 0.893（+0.028）；0.92×0.97 = 0.892（+0.027）。几乎相等——因为端到端增量 ≈ Δp_i × (其余各级的乘积)，而两级情况下「其余各级的乘积」就是另一级的 p，两者接近时贡献自然接近。",
            "但真实决策还要乘上<strong>成本</strong>与<strong>天花板</strong>。检测召回的提升往往需要更高分辨率或更大模型（吃算力、影响延迟），而分类准确率的提升常常只需要补数据、改采样、加增强（几乎不增加线上开销）。<em>所以在算力受限的车端，同等收益下优先改分类。</em>另一方面，<span class=\"term\">Bayes error</span>（贝叶斯误差）在两级上不同：远距离 12×12 的牌，信息论上就分不出限速 60 还是 80，A_cls 有硬天花板；而 R_det 的天花板通常更高（「有个牌」比「是哪个牌」容易得多）。<strong>把「当前值、成本、天花板」三个量放在一起排序，才是完整的答案。</strong>",
        ),
        H3("端到端多类检测器是不是就没有这个乘法？"),
        P("这是最容易被绕进去的地方。<strong>端到端检测器并没有消除这个乘法，只是把它藏进了同一次前向里。</strong>一个多类检测器输出的分数本身就是 <code>p(objectness) · p(class | object)</code> 的某种耦合形式（YOLO 系甚至显式地把 objectness 与 class 分数相乘）。区别在于："),
        UL([
            "端到端里两项<strong>共享特征、联合优化</strong>，所以理论上可以学到一个比分解更优的联合解；",
            "但代价是<strong>两项的梯度互相干扰</strong>——分类头的长尾梯度会污染定位特征；而且你<em>无法单独测量</em>「定位错了多少、分类错了多少」，除非另做误差分解（这正是 C61 模块 02 的 TIDE 分析要干的事）。",
        ]),
        CALLOUT("danger", "<p>一个会在生产中真实发生的事故：团队 A 报「检测召回 96%」，团队 B 报「分类准确率 97%」，PM 记下「系统性能 96%+」。上线后路测发现每 10 块牌漏 1 块——因为真实端到端是 0.96×0.97 = <strong>0.931</strong>，而且这还没算 <em>B 的 97% 是在<strong>干净的 GT crop</strong> 上测的</em>，而线上分类器吃的是检测器给的、带偏移带截断的 crop，真实条件准确率只有 0.92 → 端到端 0.883。</p><p><strong>两条铁律：① 分类器必须在「检测器输出的 crop」上评测，不是在 GT crop 上；② 对外汇报只能报端到端。</strong>这两条几乎是面试里检验「有没有做过真系统」的试金石。</p>", "级联指标的谎言"),
    ])),
    ("e2e", "端到端多类检测的适用边界：什么时候两级是过度设计", "".join([
        P("两级不是免费的。上一节的四个代价里，<strong>「工程复杂度」在小团队里往往是决定性的</strong>——两套数据、两套评测、两条流水线，意味着你的迭代速度会慢一半。所以必须知道端到端方案什么时候更好。"),
        TABLE(["判据", "端到端更合适", "两级更合适", "TSR 落在哪一侧"], [
            ["<strong>类别数</strong>", "≤ 30，且每类样本 ≥ 1000", "≥ 100，长尾跨度 ≥ 3 个数量级", "<strong>两级</strong>（GB 5768 细类 200+，TT100K 里 45 类样本 &lt; 100）"],
            ["<strong>新类频率</strong>", "类别表基本冻结", "每季度都可能加类 / 加区域", "<strong>两级</strong>（进新省份、新国标、临时牌）"],
            ["<strong>目标尺寸</strong>", "目标占图 &gt; 5%，细节充分", "目标 &lt; 32 px，细节要靠放大", "<strong>两级</strong>（60 m 外的 60 cm 牌 ≈ 16 px）"],
            ["<strong>类间几何差异</strong>", "各类外形差异大，需分别回归", "各类外形高度同构（都是牌）", "<strong>两级</strong>（圆/三角/矩形，3–5 个粗类足够）"],
            ["<strong>延迟预算</strong>", "极紧（&lt; 5 ms 总预算）", "有 2–3 ms 余量给第二级", "看平台。Orin 级算力 → 两级可行"],
            ["<strong>团队规模</strong>", "1–2 人，要快速出活", "有独立的检测组与分类组", "量产团队 → <strong>两级</strong>"],
        ]),
        DUAL(
            "最诚实的说法是：<strong>如果你只做「限速牌 + 停车让行 + 禁止通行」这十几类，端到端检测器又快又准，两级纯属自找麻烦。</strong>TSR 之所以几乎必然走两级，是因为真实产品要覆盖的类别数从来不是十几类——一个能上量产的 TSR 至少要认 100+ 类，且必须支持「进入新市场时快速加类」。<em>先问清楚「到底要认多少类、加类频率多高」，再决定架构，这是系统设计题的正确开场。</em>",
            "还有一条中间路线值得知道：<strong>共享 backbone 的多头方案</strong>——检测头与分类头共用主干特征，分类头通过 <span class=\"term\">RoIAlign</span> 从特征图上取 ROI 特征而不是从原图裁剪。它保留了「分类可独立重训（冻结主干只训分类头）」的部分好处，又省掉了第二次特征提取的算力。<em>代价是：分类器再也拿不到比主干 stride 更精细的信息</em>——而这恰恰是 TSR 最需要的（12 px 的牌在 stride-8 特征图上只有 1.5 个格子）。<strong>所以在小目标主导的 TSR 里，「从原图重新裁剪并上采样」这个看似浪费的做法，是有信息论理由的。</strong>",
        ),
        H3("算一笔真实的算力账"),
        P("假设输入 1920×1080，检测器在 1280×736 上跑（letterbox 后），分类器输入 64×64，单帧平均 12 个候选 crop："),
        CODE("""检测阶段:  1280 × 736  = 942,080 px            → 设为 1.00 单位算力
分类阶段:  64 × 64 × 12 = 49,152 px  ≈ 0.052 单位 (按像素数线性估)
           实际因分类网络更浅更窄, 通常 ≈ 0.03–0.08 单位

结论: 第二级的算力开销约为检测的 3%–8%,  却换来:
      · 200+ 类的细粒度识别能力
      · 长尾类可任意重采样
      · 加类不动检测器
  ⇒ 这个交换在几乎所有量产 TSR 里都是划算的"""),
        CALLOUT("intuition", "把上面的账反过来读更有启发：<strong>之所以两级在 TSR 里划算，根本原因是「标志很小」</strong>。目标越小，crop 的总面积相对整图越小，第二级越便宜；同时目标越小，检测器在下采样特征图上能分给它的计算越少，第二级的增益越大。<em>「小目标 + 长尾 + 频繁加类」这三件事同时成立时，两级几乎是唯一合理选择——而 TSR 正好三条全中。</em>"),
    ])),

    ("crop", "接口设计：crop 策略是两级方案里最被低估的一环", "".join([
        P("两级方案的接口就是那个 crop。<strong>接口设计错了，前面所有的解耦优势都会变成「两个模块互相甩锅」。</strong>crop 有三个必须定死并写进契约的参数：padding 比例、对齐方式、输出分辨率。"),
        H3("① padding 比例：为什么不能是 0"),
        P("直觉上，检测框就是牌的边界，直接裁就好。但这在实践中会出两个问题："),
        UL([
            "<strong>检测框本身有误差</strong>。小目标上这个误差是致命的：一个 16×16 的牌，检测框位移 2 px，IoU 从 1.0 掉到约 0.60；若直接按框裁剪，牌的边缘（红圈、外框——恰恰是最有判别力的部分）会被切掉。",
            "<strong>上下文有信息</strong>。牌的杆件、背板、周围是天空还是树，都是判别「这是真牌还是广告牌」的线索。padding 把这些一起带进来。",
        ]),
        TABLE(["padding 比例", "效果", "适用"], [
            ["0%", "边缘常被切；对检测框误差极不鲁棒", "只有当检测框极准（大目标）时"],
            ["<strong>10%–20%</strong>", "<strong>常用甜点</strong>。覆盖典型框误差，保留完整牌面 + 一圈背景", "绝大多数 TSR 系统"],
            ["30%–50%", "上下文丰富，对误检判别（广告牌）帮助大；但小牌在 crop 里占比下降", "背景误检是主要痛点时"],
            ["按框尺寸自适应", "小框给更大比例 padding（因为小框的相对误差更大）", "<strong>更优</strong>：<code>pad = max(0.15, 3px / min(w,h))</code>"],
        ]),
        H3("② 对齐：正方形化与长宽比"),
        P("标志的原始长宽比多样（圆牌 1:1、指路牌 3:1、附加牌 2:1）。分类器需要固定输入尺寸，处理长宽比有三种做法，<strong>而它们对精度的影响远大于直觉</strong>："),
        TABLE(["做法", "做什么", "问题"], [
            ["<strong>直接 resize 到方形</strong>", "拉伸", "长宽比信息被销毁 —— 而<em>形状本身是 TSR 的一级语义</em>（圆=禁令、三角=警告）。<strong>这是一个真实的、常见的、代价很大的错误</strong>"],
            ["<strong>扩成方形再裁</strong>", "取 max(w,h) 为边长，以框中心扩成正方形后裁剪", "会带入更多背景，但<strong>保长宽比</strong>。多数系统的选择"],
            ["<strong>letterbox 填充</strong>", "保比例缩放 + 灰边填充", "保比例且不引入真实背景；但填充区域是无信息的死像素，浪费算力"],
        ]),
        H3("③ 输出分辨率：上采样有意义吗"),
        P("一个 16×16 的 crop 上采样到 64×64，<strong>并没有增加任何信息</strong>——这是显然的。但它仍然有意义，原因有三个，<strong>面试里能把这三条说清楚就已经超过大多数候选人</strong>："),
        OL([
            "<strong>计算量分配</strong>。CNN 分给一个输入的计算量正比于输入面积。16×16 输入在一个 stride-32 的网络里连一个格子都不到；上采样到 64×64 后，网络有足够的层数与空间维度去提取特征。<em>信息没增加，但「能用来处理这些信息的计算」增加了 16 倍。</em>",
            "<strong>批处理统一</strong>。所有 crop 归一到同一尺寸才能 batch 化前向——这是延迟能压下来的前提。",
            "<strong>与训练分布对齐</strong>。分类器在固定尺寸上训练，推理必须同尺寸。<em>而这引出一个真实的坑：训练时如果用 GT 框裁剪并 resize，推理时用检测框，两者的「牌在 crop 中的占比分布」不同 → 训练-推理分布漂移。</em>",
        ]),
        CALLOUT("danger", "<p>接上面第 3 条：<strong>分类器的训练数据必须用「模拟检测器输出的框」来裁剪，而不是 GT 框。</strong>具体做法是给 GT 框加上与检测器误差分布一致的扰动（中心偏移 + 尺度抖动），再裁剪。</p><p>不这么做的后果是可测量的：某些系统上，在 GT crop 上 97% 准确率的分类器，换成检测框 crop 后掉到 91%——<strong>6 个点凭空消失，而离线评测完全看不出来</strong>。这是「离线指标好、路测差」最常见的成因之一，也是本模块 notebook 要你亲手复现的实验。</p>", "训练用 GT crop、推理用检测 crop = 隐形的域差"),
        DUAL(
            "把这一节浓缩：<strong>crop 是两级方案的 API，而 API 一旦定下来，两边的模型都是围绕它训练的。</strong>改 padding 比例 = 破坏性变更，两个模型都要重训重验。所以这几个参数应该在项目早期就定死、写进配置、纳入版本管理——像对待接口契约一样对待它。",
            "更严谨地说，crop 策略定义了第二级看到的<span class=\"term\">条件分布</span> <code>p(crop | box, image)</code>。两级分解的正确性依赖训练与推理时这个分布一致。<em>任何改变这个分布的东西——padding、对齐、插值方式（bilinear vs bicubic）、是否做 letterbox、填充值——都是分布漂移的来源。</em><strong>与 C60 讲的「训练-部署一致性」是同一个问题的不同外衣：预处理必须逐位对齐。</strong>",
        ),
    ])),

    ("confidence", "置信度合成与标定：两个分数怎么变成一个可信的概率", "".join([
        P("两级系统输出两个分数：检测分数 <code>s_det</code>（这里有个牌吗）与分类分数 <code>s_cls</code>（是哪个牌）。下游（跟踪、决策、VLA）需要<strong>一个</strong>数，而且需要它是<strong>真的概率</strong>——「0.9」应该意味着「这样的 100 次里约 90 次是对的」。"),
        H3("合成：为什么是乘法"),
        MATH("p(\\text{class}=c \\,\\wedge\\, \\text{object} \\mid \\text{image}) = \\underbrace{p(\\text{object} \\mid \\text{image})}_{s_{det}} \\cdot \\underbrace{p(c \\mid \\text{object}, \\text{crop})}_{s_{cls}}"),
        P("乘法来自链式法则，前提是 <code>s_det</code> 与 <code>s_cls</code> <strong>都是标定过的概率</strong>。这个前提在实践中几乎从不满足："),
        TABLE(["分数", "实际语义", "典型偏差"], [
            ["<strong>检测分数</strong>", "经过 focal loss / 正负样本极度不均衡训练出的分数", "<strong>系统性偏低</strong>（focal loss 压低了所有分数），且与 IoU 相关性弱 —— 高分不代表框准"],
            ["<strong>分类分数</strong>", "softmax 输出", "<strong>系统性过度自信</strong>（现代深网络的典型症状），尤其在长尾尾部类上"],
            ["<strong>乘积</strong>", "两个未标定分数的乘积", "<strong>没有任何概率语义</strong>；偏差方向甚至可能互相抵消，制造「看起来还行」的假象"],
        ]),
        H3("标定：ECE 与可靠性图"),
        P("<span class=\"term\">calibration</span>（标定）要回答的问题是：把所有预测按置信度分桶，每个桶里「平均置信度」与「实际准确率」是否相等。差距的加权平均就是 <span class=\"term\">ECE</span>（Expected Calibration Error，期望标定误差）："),
        MATH("\\mathrm{ECE} \\;=\\; \\sum_{m=1}^{M} \\frac{|B_m|}{n} \\bigl| \\mathrm{acc}(B_m) - \\mathrm{conf}(B_m) \\bigr|"),
        P("其中 <code>B_m</code> 是第 m 个置信度区间里的样本集合，<code>acc</code> 是该桶实际准确率，<code>conf</code> 是该桶平均预测置信度。把 <code>(conf, acc)</code> 画出来就是<span class=\"term\">reliability diagram</span>（可靠性图）：<strong>完美标定的模型落在对角线上；过度自信的模型落在对角线下方</strong>。"),
        TABLE(["标定方法", "做法", "参数量", "适用"], [
            ["<strong>Temperature scaling</strong>", "logits 除以一个标量 T 后再 softmax，在验证集上最小化 NLL 求 T", "1 个", "<strong>首选</strong>。单参数、不改变 argmax（即不影响准确率）、效果好得出奇"],
            ["<strong>Vector / Matrix scaling</strong>", "每类一个缩放/完整线性变换", "K / K²", "类间偏差差异大时；有过拟合风险"],
            ["<strong>Histogram binning</strong>", "分桶后用桶内经验准确率替换置信度", "M 个", "非参数，样本足够时稳；但输出离散"],
            ["<strong>Isotonic regression</strong>", "拟合单调映射", "非参", "比 histogram 平滑；小样本易过拟合"],
        ]),
        DUAL(
            "<strong>Temperature scaling 有一个性质在工程上特别重要：它不改变预测的排序，因此不改变准确率、不改变 mAP，只改变置信度的数值。</strong>这意味着你可以在模型冻结、评测通过之后，作为一个纯后处理步骤加上去——不需要重训、不需要重跑检测评测、风险极低。<em>它几乎是「白拿」的改进，而很多团队从来没做过。</em>",
            "但有两个陷阱。① <strong>标定是在特定分布上做的</strong>：用晴天数据标出来的 T，在夜间/雨天分布上依然过度自信。<em>严谨做法是分场景标定（按天气/光照/距离分桶各标一个 T），或至少在标定集里保证场景配比与线上一致。</em>② <strong>检测分数的标定要按 IoU 定义「正确」</strong>：一个 score 0.9 的框如果 IoU 只有 0.4，它算对还是错？定义变了，标定结果就变了。<em>TSR 里更该关心的是「这个框对应一块真牌」而非「IoU ≥ 0.5」，所以标定的正确性判据应该按下游需求定，而不是照抄 COCO。</em>",
        ),
        CALLOUT("warn", "常见错误：<strong>在训练集上做标定</strong>。训练集上模型近乎完美，标出来的 T 接近 1，等于没做。<em>标定必须用独立的、未参与训练的验证集</em>，而且这个集合要足够大（每个置信度桶至少几十个样本，否则 ECE 估计本身噪声极大）。另一个错误是<strong>只报一个 ECE 数字</strong>——ECE 会把「低置信度区过度保守」与「高置信度区过度自信」互相抵消。<strong>必须看可靠性图，尤其是高置信度区间那几个桶</strong>，因为下游只会用高置信度的检测。"),
    ])),
    ("reject", "拒识与未知类：softmax 一定会给你一个答案，哪怕输入是垃圾", "".join([
        P("两级方案有一个结构性风险：<strong>分类器的 softmax 在任何输入上都会输出一个和为 1 的分布</strong>。检测器误检了一块广告牌，分类器不会说「这不是标志」，它会说「这是限速 40，置信度 0.87」。<em>这不是 bug，是 softmax 的定义决定的。</em>"),
        ASCII("""            输入 crop
                │
      ┌─────────┴─────────┐
      │                   │
   真标志              广告牌 / 车身贴纸 / 树叶缝隙
      │                   │
      ▼                   ▼
  softmax over 200 类   softmax over 200 类
      │                   │
      ▼                   ▼
  「限速60, 0.95」    「限速40, 0.87」  ← 一样自信！
                          ▲
                          └─ 闭集分类器的根本缺陷:
                             它只会回答「200 类里最像哪个」
                             从不回答「是不是这 200 类之一」""")
        ,
        TABLE(["拒识方案", "机制", "优点", "代价 / 坑"], [
            ["<strong>① 加 background 类</strong>",
             "训练时把检测器的误检（hard negative）作为第 201 类",
             "最简单、最有效；直接复用现有训练框架",
             "background 类的样本必须来自<strong>真实检测器的误检</strong>，随机负样本没用；且检测器一改，负样本分布就变了"],
            ["<strong>② 阈值 + margin</strong>",
             "要求 top1 &gt; τ 且 top1 − top2 &gt; δ",
             "零成本，可在线调",
             "过度自信的模型上 top1 阈值几乎不起作用 —— <strong>必须先标定</strong>"],
            ["<strong>③ 能量 / logit 范数</strong>",
             "用 <code>-T·logsumexp(logits/T)</code> 作为 OOD 分数（能量越低越像已知类）",
             "不需重训，比 max-softmax 更能分开 OOD",
             "阈值仍需在 OOD 验证集上定；对分布偏移敏感"],
            ["<strong>④ 开集识别 / 原型距离</strong>",
             "在特征空间量测到各类原型的距离，太远则拒识",
             "有几何解释，可增量加类",
             "特征空间的度量需要专门训练（metric learning）；实现复杂度高"],
        ]),
        DUAL(
            "在 TSR 里，<strong>方案 ① 几乎总是第一步，而且它的效果取决于负样本的来源</strong>。正确做法是：用<em>当前版本的检测器</em>在大量无标注路测视频上跑一遍，把所有「检测器给了高分但不在 GT 里」的 crop 收集起来，人工快速筛掉真漏标的，剩下的就是最有价值的 background 训练样本。<em>这就是 C58 讲的难例挖掘在两级系统里的具体形态。</em>",
            "更深一层的问题是：<strong>拒识阈值应该按「代价」而不是按「准确率」来定</strong>。漏检一块「停车让行」与误报一块「景点指示」的代价差好几个数量级。所以正确的做法是给每个类别定义误报代价 <code>c_FP(k)</code> 与漏检代价 <code>c_FN(k)</code>，然后最小化期望代价：<em>当 <code>p(c) · c_FN(c) &gt; (1-p(c)) · c_FP(c)</code> 时上报，否则拒识</em>——这就是逐类别的最优决策阈值 <code>τ_c = c_FP / (c_FP + c_FN)</code>。<strong>这也是为什么第 6 节的标定是必须的：只有标定过的 p 才能代进这个不等式。</strong>模块 05 会把它扩展成完整的代价敏感评测。",
        ),
        CALLOUT("intuition", "把拒识放进级联公式里看会更清楚：拒识<strong>降低 A_cls 的分子（有些对的也被拒了），但同时降低误报率</strong>。所以它不是「白拿的改进」，而是一个可调的工作点。<em>本质上你是在用召回换精度，而换的比例由阈值控制。</em><strong>系统设计题里被问「怎么处理未知标志」，正确的答案结构是：先说 softmax 的闭集缺陷 → 再给两三个方案 → 最后说阈值该按代价定而不是按准确率定。</strong>"),
    ])),

    ("production", "量产落地：在算力与组织约束下会怎么选", "".join([
        P("到这里技术选项已经讲完了。真实的架构决策还要过三关：<strong>算力预算、迭代组织、可验证性</strong>。这一节把它们串起来，给出一个可以直接在系统设计面试里复述的推理链。"),
        H3("推理链（可直接背）"),
        OL([
            "<strong>先确定输出契约</strong>：下游要的是「本车道、多少米外、什么标志、置信度多少、稳定了几帧」。<em>这决定了必须有 [4] 关联环节，也决定了必须传置信度。</em>",
            "<strong>再确定类别规模与加类频率</strong>：200+ 类、每季度加类 → <strong>检测与分类必须解耦</strong>。这一条就基本判定了两级。",
            "<strong>再确定尺寸分布</strong>：要在 60–80 m 检出 → 目标 12–20 px → <strong>检测器需要高分辨率输入 + 浅层特征（P2），分类器需要独立的高分辨率 crop</strong>。",
            "<strong>再算延迟</strong>：33 ms 一帧里，TSR 大概只分到 8–12 ms（还有 BEV、动态目标、车道线在抢）。检测 6–8 ms + 分类 1–2 ms（batch 化 top-k crop）+ 后处理 1 ms。<strong>关键是给 crop 数设硬上限</strong>（如 16），否则复杂路口延迟会爆。",
            "<strong>再定置信度与拒识</strong>：分别标定 → 乘法合成 → 逐类代价阈值 → 拒识。",
            "<strong>最后接时序</strong>：单帧输出进跟踪器做多帧确认（模块 04），下游拿到的永远是时序稳定后的结果，不是单帧结果。",
        ]),
        TABLE(["约束", "对架构的具体影响", "常见的妥协"], [
            ["<strong>算力（Orin / 自研 NPU）</strong>", "检测器输入分辨率与 backbone 宽度是最大开销；第二级几乎免费", "牺牲检测输入分辨率 → 直接损失远距召回。<em>宁可砍 backbone 也别砍分辨率</em>（小目标场景的通用结论）"],
            ["<strong>延迟 p99 而非均值</strong>", "crop 数随场景波动（空旷路段 2 个，复杂路口 30 个）→ 第二级延迟方差大", "<strong>固定 batch 大小（padding 到 16）</strong>，用确定的延迟换掉方差 —— 车端偏好确定性"],
            ["<strong>存储与带宽</strong>", "两个模型两份权重；难例回传要带 crop", "crop 很小（64×64），回传成本低 —— <strong>这反而是两级的一个隐性优势</strong>"],
            ["<strong>组织</strong>", "检测组与分类组可并行；但接口变更要跨组同步", "把 crop 契约冻结成配置文件 + 版本号，变更走评审"],
            ["<strong>可验证性</strong>", "端到端失败要能定位到是哪一级", "<strong>日志必须同时记录 s_det、s_cls、crop 坐标</strong>，否则线上 badcase 无法归因"],
        ]),
        CALLOUT("intuition", "<p>最后一行值得单独强调，因为它是<strong>把「两级」的好处兑现的关键</strong>：如果日志里只有最终结果，那么「这个漏检是检测没框到，还是分类判成 background 了」就永远说不清，两级的可调试性优势直接归零。</p><p><strong>正确做法：每一帧的每个候选都记录 (box, s_det, top3 类别与分数, 是否被拒识, 拒识原因)。</strong>这份日志的体积很小（每帧几百字节），却是整个数据闭环的地基 —— 模块 05 的分桶评测、C58 的难例触发，全都建立在它上面。<em>「先设计日志，再设计模型」在量产感知里不是玩笑。</em></p>"),
        DUAL(
            "如果面试官追问「小鹏这种量产系统会怎么做」，一个稳妥且真实的回答是：<strong>类别无关或粗类检测器（3–5 个粗类：圆形禁令 / 三角警告 / 矩形指示 / 电子屏 / 附加牌）+ 一个小分类器 + 强时序确认</strong>，检测阶段阈值放得很低（宁滥勿缺），把精度责任交给分类器的 background 类与时序确认。<em>因为漏检一旦发生就是永久损失，而误检可以被后面两道关卡过滤掉。</em>",
            "背后的原理是<strong>级联系统的阈值应该「前松后紧」</strong>：早期阶段的漏检不可恢复（乘法里的 0 吞掉一切），而早期阶段的误检可以被后续阶段以更低的代价滤除（因为后续阶段看到的是放大后的高分辨率 crop，判别力更强）。<em>这与经典的 Viola-Jones 级联分类器是同一个设计原则</em>——每一级都追求极高召回、只做温和的精度提升，把难判的样本留给后面算力更贵的阶段。<strong>这个「前松后紧」的原则可以迁移到任何级联系统，值得记死。</strong>",
        ),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("两级 vs 端到端并没有被「解决」，只是在当前的算力与数据条件下有一个工程上的最优解。下面几个方向正在改变这个平衡点。"),
        UL([
            "<strong>开放词汇检测（open-vocabulary detection）冲击「加类」这个动机</strong>。GLIP / Grounding DINO / OWL-ViT 这类模型用文本描述作为类别定义，理论上「加一个新标志」只需要加一句文本描述，不需要任何训练。<em>如果这条路成熟，两级方案的动机 ② 就消失了。</em>目前的现实是：这些模型在小目标与细粒度区分（限速 60 vs 80）上还远不够，且推理开销大；但作为<strong>数据挖掘工具</strong>（在无标注视频里找出「黄色菱形警告牌」）已经非常实用。",
            "<strong>端到端可微的级联</strong>。把 crop 操作写成可微的 RoIAlign / STN（spatial transformer），让分类损失的梯度回传到检测器 —— 理论上能得到「解耦的结构 + 联合的优化」。<em>难点是：可微 crop 只能从特征图取，而 TSR 需要的是原图分辨率的 crop，两者矛盾。</em>",
            "<strong>置信度标定的分布偏移问题</strong>。现有标定方法都假设标定集与测试集同分布，而自动驾驶恰恰是分布持续偏移的场景（新城市、新季节、新天气）。<em>「在线自适应标定」（用时序一致性作为无监督信号来重标定）是一个活跃且尚未有定论的方向。</em>",
            "<strong>不确定性的分解</strong>。<span class=\"term\">aleatoric</span>（数据固有的，如 12 px 的牌本来就分不清）与 <span class=\"term\">epistemic</span>（模型没见过，如新型电子屏）不确定性对下游的含义完全不同：前者应该等更近再判，后者应该触发数据回传。<em>把它们分开估计并分别驱动不同的下游动作，目前还是研究问题。</em>",
            "<strong>与 VLA 的接口</strong>。如果下游是一个 VLA 模型（C59），它到底需要「结构化的 TSR 结果」还是「原始特征」？<em>结构化输出可解释、省 token，但有信息损失；特征级注入信息全但不可调试。</em>这个取舍目前没有定论，且直接决定 TSR 模块的输出契约该怎么设计。",
            "<strong>级联系统的联合评测理论</strong>。多级系统的置信区间、显著性检验该怎么做（各级误差不独立）；如何在固定标注预算下分配「标检测数据」与「标分类数据」的比例 —— 后者是一个实际的、几乎每个团队都在拍脑袋决定的问题。",
        ]),
        CALLOUT("paper", "必读：<em>Viola & Jones, Rapid Object Detection using a Boosted Cascade of Simple Features</em>（2001，级联「前松后紧」原则的源头，读第 4 节的级联训练即可）；<em>Guo et al., On Calibration of Modern Neural Networks</em>（ICML 2017，temperature scaling 与 ECE 的原始论文，必读，短且实用）；<em>Hendrycks & Gimpel, A Baseline for Detecting Misclassified and Out-of-Distribution Examples</em>（ICLR 2017，max-softmax 基线）与 <em>Liu et al., Energy-based Out-of-distribution Detection</em>（NeurIPS 2020）；<em>Zhu et al., Traffic-Sign Detection and Classification in the Wild</em>（CVPR 2016，TT100K 数据集与两级基线，TSR 必读）；<em>Liu et al., Grounding DINO</em>（开放词汇检测的当前代表）。相邻课程：C57（小目标）、C58（长尾与难例挖掘）、C60（训练-部署一致性）、C61（误差分解）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · TSR 系统设计：两级 vs 端到端（级联误差 / 延迟 p99 / crop 契约 / 置信度标定）

目标：把「两级方案好不好」这个含糊的架构问题，变成**四个可以算出数字的问题**——
级联召回怎么乘、延迟的 p99 怎么控、crop 契约错了会丢多少点、置信度怎么才算「真概率」。

本 notebook 你会亲手实现：

1. **级联误差传播计算器** + 边际收益/成本的改进优先级排序（∂R/∂p 的实际用法）
2. **两级 vs 端到端的延迟模型**：crop 数随场景波动 → p50/p99 → 固定 batch 如何用均值换掉方差
3. **长尾下的精度模拟**：为什么两级赢在尾部而不是头部
4. **crop 契约实验**：在 GT crop 上训练、在检测 crop 上推理，凭空损失多少准确率（本模块最重要的实验）
5. **ECE + 可靠性图 + temperature scaling**：把两个分数变成一个可信的概率
6. **代价敏感的拒识阈值**：τ = c_FP / (c_FP + c_FN)

> 心智模型：**级联系统的性能在对数域上是相加的，没有任何一级能补偿另一级的损失。
> 所以「前松后紧」，并且永远只汇报端到端。**"""),

    md("""## 1 · 级联误差传播计算器

`R_end2end = R_det × A_cls`。先把这个乘法的后果算出来。"""),

    code("""import numpy as np, math, json
rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)

def cascade_recall(rates):
    '''级联通过率 = 各级通过率之积。整个模块的核心公式。'''
    r = 1.0
    for p in rates:
        r *= p
    return r

CASES = [
    ('两级 · 各 0.90',        [0.90, 0.90]),
    ('两级 · 汇报值 0.96/0.97', [0.96, 0.97]),
    ('两级 · 真实条件准确率',   [0.96, 0.92]),
    ('三级 · 各 0.95',        [0.95, 0.95, 0.95]),
    ('五级 · 各 0.98',        [0.98] * 5),
]
print(f"{'配置':<22s}{'各级通过率':<28s}{'端到端':>9s}{'最弱一级':>10s}")
for name, r in CASES:
    print(f"{name:<22s}{str(r):<28s}{cascade_recall(r):>9.3f}{min(r):>10.3f}")

assert abs(cascade_recall([0.9, 0.9]) - 0.81) < 1e-12
assert abs(cascade_recall([0.98] * 5) - 0.98 ** 5) < 1e-12
assert cascade_recall([0.96, 0.92]) < 0.90, '两个 90+ 的模块合起来掉到 90 以下'

print()
print('⚠️  0.90 × 0.90 = 0.81 —— 两个「还行」的模块合起来是「不能用」。')
print('⚠️  0.96 × 0.97 = 0.931，而不是 PM 记下的「96%+」。')
print('✅ 对外只能汇报端到端；分级指标永远系统性高估。')
print('✅ 每加一级就多一次乘法 —— 五级各 0.98 也只剩 %.3f。' % cascade_recall([0.98] * 5))"""),

    code("""def others_product(rates, i):
    '''除第 i 级之外所有级的乘积 —— 它就是第 i 级的「边际收益系数」。'''
    p = 1.0
    for j, v in enumerate(rates):
        if j != i:
            p *= v
    return p

def marginal_gain(rates, i, delta):
    '''把第 i 级提升 delta 个绝对点，端到端涨多少。'''
    new = list(rates)
    new[i] = min(1.0, new[i] + delta)
    return cascade_recall(new) - cascade_recall(rates)

rates = [0.92, 0.94]                      # [R_det, A_cls]
names = ['检测召回 R_det', '分类准确率 A_cls']
print(f'当前端到端 = {cascade_recall(rates):.4f}')
for i in range(2):
    g = marginal_gain(rates, i, 0.03)
    print(f'  {names[i]:<18s} +0.03  ->  端到端 +{g:.4f}   ( = 0.03 × {others_product(rates, i):.3f} )')

# 严格恒等式：∂R/∂p_i = 其余各级之积  =>  ΔR = Δp_i × others_product
for i in range(2):
    assert abs(marginal_gain(rates, i, 0.03) - 0.03 * others_product(rates, i)) < 1e-12

print()
print('✅ 两级情况下「其余各级之积」就是另一级的通过率 —— 两者接近时，')
print('   同样 +0.03 的收益几乎相同。**所以光看收益无法决策，必须引入成本与天花板。**')"""),

    code("""# 真实决策：收益 / 成本 / 天花板 三者一起排序
base = cascade_recall(rates)
PLAN = [
    # (方案, 作用于第几级, 天花板, 成本(人月), 线上算力代价)
    ('提高检测输入分辨率', 0, 0.970, 2.0, '延迟 +3.0 ms'),
    ('分类器补长尾数据',   1, 0.985, 1.0, '延迟 +0.0 ms'),
]
print(f"{'方案':<20s}{'可涨到':>8s}{'端到端增量':>12s}{'每人月收益':>12s}{'线上代价':>14s}")
rec = {}
for name, i, ceil_, cost, lat in PLAN:
    r2 = list(rates); r2[i] = ceil_
    gain = cascade_recall(r2) - base
    rec[name] = (gain, gain / cost)
    print(f'{name:<20s}{ceil_:>8.3f}{gain:>12.4f}{gain / cost:>12.4f}{lat:>14s}')

g_det, roi_det = rec['提高检测输入分辨率']
g_cls, roi_cls = rec['分类器补长尾数据']
assert g_det > g_cls, '按绝对增量：检测的空间更大'
assert roi_cls > roi_det, '按每人月收益：补分类数据更划算'

print()
print('⚠️  按「绝对增量」排 -> 先做检测；按「每人月收益」排 -> 先做分类。**排序会反转。**')
print('✅ 车端还要再乘一个约束：检测方案要吃 3 ms 延迟，而分类方案是 0。')
print('   ⇒ 算力受限时，同等收益优先改分类。这就是模块讲解里那条结论的来源。')"""),

    md("""## 2 · 两级 vs 端到端：延迟模型与 p99

车端真正在意的不是均值，是 **p99**。而两级方案的第二级延迟正比于 crop 数，
**crop 数随场景剧烈波动**（空旷路段 2 个，复杂路口 30 个）—— 这是方差的来源。"""),

    code("""T_DET, T_CLS, T_OVH, T_POST = 7.0, 0.22, 0.4, 1.0    # ms：检测/单 crop 分类/batch 开销/后处理
T_E2E = 9.6                                            # 端到端多类检测器（无第二级）

def lat_dynamic(n, cap=None):
    '''动态 batch：延迟正比于实际 crop 数（cap 为 top-k 截断上限）。'''
    k = n if cap is None else min(n, cap)
    return T_DET + T_OVH + T_CLS * k + T_POST

def lat_fixed(n, batch=12):
    '''固定 batch：不足补 padding，超出截断 -> 延迟恒定。'''
    return T_DET + T_OVH + T_CLS * batch + T_POST

# 场景混合：55% 空旷 / 35% 城区 / 10% 复杂路口
n_frames = 40000
scene = rng.choice([0, 1, 2], size=n_frames, p=[0.55, 0.35, 0.10])
n_crops = rng.poisson(np.array([2.0, 8.0, 25.0])[scene])

variants = {
    'A 动态 batch，无上限': np.array([lat_dynamic(n) for n in n_crops]),
    'B 动态 + top-12 截断': np.array([lat_dynamic(n, cap=12) for n in n_crops]),
    'C 固定 batch = 12':   np.array([lat_fixed(n) for n in n_crops]),
    'D 端到端（无第二级）':  np.full(n_frames, T_E2E),
}
print(f"{'方案':<22s}{'均值':>8s}{'p50':>8s}{'p99':>8s}{'max':>8s}{'标准差':>9s}")
S = {}
for k, v in variants.items():
    S[k] = (v.mean(), np.percentile(v, 50), np.percentile(v, 99), v.max(), v.std())
    print(f'{k:<22s}' + ''.join(f'{x:>8.2f}' for x in S[k][:4]) + f'{S[k][4]:>9.2f}')

assert S['A 动态 batch，无上限'][2] > S['B 动态 + top-12 截断'][2], 'top-k 截断压住了 p99'
assert S['C 固定 batch = 12'][4] < 1e-12, '固定 batch 的延迟方差应为 0'
assert S['A 动态 batch，无上限'][0] < S['C 固定 batch = 12'][0], '固定 batch 用均值换方差'
assert S['B 动态 + top-12 截断'][2] <= S['C 固定 batch = 12'][2] + 1e-9

print()
print('✅ 车端偏好 C：**用更高的均值换掉方差**，因为调度器按最坏情况分配时间片。')
print('⚠️  A 的均值最低（%.2f ms）却最危险：p99 是 %.2f ms，复杂路口会掉帧。'
      % (S['A 动态 batch，无上限'][0], S['A 动态 batch，无上限'][2]))
print('✅ 两级相比端到端多付 %.2f ms（固定 batch），换来 200+ 类细粒度识别 + 加类不重训。'
      % (S['C 固定 batch = 12'][0] - T_E2E))"""),

    code("""# 截断的代价：top-k 会丢掉真标志吗？
def truncation_recall(k, trials=6000, seed=3):
    '''真标志的检测分数偏高（Beta(6,2)），误检偏低（Beta(2,6)）。'''
    g = np.random.default_rng(seed)
    tot, kept = 0, 0.0
    for _ in range(trials):
        n_true = int(g.integers(1, 4))
        n_false = int(g.poisson(8))
        s = np.concatenate([g.beta(6, 2, size=n_true), g.beta(2, 6, size=n_false)])
        lab = np.concatenate([np.ones(n_true), np.zeros(n_false)])
        idx = np.argsort(-s)[:k]
        tot += n_true
        kept += lab[idx].sum()
    return kept / tot

print(f"{'top-k 上限':>10s}{'真标志召回':>12s}{'分类阶段延迟':>14s}")
recs = {}
for k in [2, 4, 8, 12, 20, 40]:
    r = truncation_recall(k)
    recs[k] = r
    print(f'{k:>10d}{r:>12.4f}{T_OVH + T_CLS * k:>13.2f} ms')

assert recs[12] > recs[4] > recs[2], 'k 越大召回越高'
assert recs[12] > 0.99, 'k=12 已经几乎无损 —— 因为真标志的分数偏高'
assert recs[40] - recs[12] < 0.01, '再往上是纯粹的延迟浪费'

print()
print('✅ 关键洞察：**截断的代价取决于真标志分数是否偏高**。')
print('   在 TSR 里真标志的检测分数系统性高于广告牌误检 -> top-12 几乎无损。')
print('⚠️  但这依赖检测分数「排序正确」。如果检测器过度自信地把广告牌排到前面，')
print('   截断就会开始吃真标志 —— 这又回到了第 5 节的标定问题。')"""),

    md("""## 3 · 长尾下的精度模拟：两级赢在尾部，不在头部

用一条学习曲线 `acc(n) = ceiling · (1 − e^(−n/n₀))` 建模「样本量 → 精度」，
两级的两个优势体现为：**检测器的 n 是全类之和**，**分类器的任务更简单（n₀ 更小）且可重采样**。"""),

    code("""def learn_curve(n, n0=350.0, ceiling=0.985):
    '''样本量 -> 精度的经验学习曲线。n0 越小表示任务越「样本高效」。'''
    return ceiling * (1.0 - np.exp(-np.asarray(n, float) / n0))

K_CLS = 120                                  # 细类数
ranks = np.arange(1, K_CLS + 1)
w = ranks ** -1.4                            # Zipf 型长尾
counts = np.maximum(8, np.round(w / w.sum() * 120000)).astype(int)
N_total = counts.sum()
print(f'类别数 {K_CLS} | 实例总数 {N_total} | 最多的类 {counts.max()} | 最少的类 {counts.min()}'
      f' | 头尾比 {counts.max() / counts.min():.0f}:1')

# ── 端到端：每一类都要从自己的 counts[c] 个实例里同时学「定位 + 识别」
acc_e2e = learn_curve(counts, n0=350.0)

# ── 两级：
#   检测器只学「牌状物」，正样本 = 全部类之和
R_det = float(learn_curve(N_total, n0=350.0))
#   分类器任务更简单（输入已归一化，不用学定位）-> n0 更小；且可重采样（LVIS 式 repeat factor）
f = counts / N_total
repeat = np.clip(np.sqrt(0.001 / f), 1.0, 4.0)          # 上限 4，避免过拟合
acc_cls = learn_curve(counts * repeat, n0=110.0)
r_two = R_det * acc_cls

head, tail = slice(0, 10), slice(K_CLS - 30, K_CLS)
print(f'\\n检测器召回 R_det = {R_det:.4f}（全类样本共享的好处）')
print(f"{'':<10s}{'端到端 macro':>14s}{'两级 macro':>14s}{'差':>9s}")
for nm, sl in [('全部类', slice(None)), ('头部 10 类', head), ('尾部 30 类', tail)]:
    a, b = acc_e2e[sl].mean(), r_two[sl].mean()
    print(f'{nm:<10s}{a:>14.4f}{b:>14.4f}{b - a:>+9.4f}')

d_head = r_two[head].mean() - acc_e2e[head].mean()
d_tail = r_two[tail].mean() - acc_e2e[tail].mean()
assert r_two.mean() > acc_e2e.mean(), '两级的 macro 更高'
assert abs(d_head) < 0.02, '头部类几乎没差别 —— 数据都够，谁都学得会'
assert d_tail > 0.15, '尾部类差距巨大 —— 这才是两级的真正价值'
assert d_tail > 5 * abs(d_head)

print()
print('✅ **两级的收益几乎全部来自尾部**。头部类样本充足，两种架构都学得会。')
print('⚠️  所以用 micro / 实例加权指标去评估两级 vs 端到端，会**看不见**这个收益')
print('   （尾部类实例少，加权后被淹没）。**必须看 macro 与逐类召回。**')
print('⚠️  注意这是一个「模型」不是「测量」：learn_curve 与 repeat 上限都是假设。')
print('   它的价值是给出**趋势与量级**，用来做决策，而不是预测具体数字。')"""),

    md("""## 4 · crop 契约：GT crop 上训练、检测 crop 上推理 = 隐形的域差

**本模块最重要的实验。** 我们造一个可控的合成 TSR：
类别 = 圆形外圈（各类相同）+ 类别专属的内部低频图案；
分类器 = 最近邻 exemplar bank（在裁好的 crop 特征上做匹配）。

然后对比两种训练方式：**用 GT 框裁剪** vs **用带扰动的框裁剪**（模拟检测器输出）。"""),

    code("""K = 8            # 合成细类数
R = 32           # 模板与分类器输入分辨率

def resize(img, out=32):
    '''双线性缩放（纯 numpy）。'''
    H, W = img.shape
    ys = np.linspace(0, H - 1, out); xs = np.linspace(0, W - 1, out)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, H - 1); x1 = np.minimum(x0 + 1, W - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    top = img[y0][:, x0] * (1 - wx) + img[y0][:, x1] * wx
    bot = img[y1][:, x0] * (1 - wx) + img[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy

def make_templates(K=8, R=32, seed=1):
    '''外圈（所有类共有，像红边）+ 内部 4×4 低频类别图案。'''
    ax = np.arange(R); yy, xx = np.meshgrid(ax, ax, indexing='ij')
    c = (R - 1) / 2
    r = np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / (R / 2)
    ring = ((r > 0.80) & (r <= 1.0)).astype(float)
    inner = (r <= 0.72).astype(float)
    g = np.random.default_rng(seed)
    return np.stack([ring * 1.5 + inner * np.kron(g.normal(size=(4, 4)),
                                                  np.ones((R // 4, R // 4)))
                     for _ in range(K)])

TPL = make_templates(K, R)

def render(k, s, canvas=120, noise=0.35, g=None):
    '''把第 k 类模板缩放到 s×s 贴到带噪背景上，返回 (图, GT框)。'''
    g = g if g is not None else rng
    img = g.normal(0, noise, size=(canvas, canvas))
    y0 = int(g.integers(10, canvas - s - 10)); x0 = int(g.integers(10, canvas - s - 10))
    img[y0:y0 + s, x0:x0 + s] += resize(TPL[k], s)
    return img, (float(x0), float(y0), float(s), float(s))

def perturb(box, j, g):
    '''模拟检测器输出：中心偏移 ±j·边长，尺度抖动 ±j。'''
    x, y, w, h = box
    cx, cy = x + w / 2 + g.uniform(-j, j) * w, y + h / 2 + g.uniform(-j, j) * h
    sc = 1 + g.uniform(-j, j)
    return (cx - w * sc / 2, cy - h * sc / 2, w * sc, h * sc)

def crop_box(img, box, pad=0.15):
    '''正方形化 + padding + 边界裁剪 —— 这就是两级方案的 API。'''
    x, y, w, h = box
    s = max(w, h); cx, cy = x + w / 2, y + h / 2
    x0 = int(round(cx - s / 2 - pad * s)); y0 = int(round(cy - s / 2 - pad * s))
    x1 = int(round(cx + s / 2 + pad * s)); y1 = int(round(cy + s / 2 + pad * s))
    H, W = img.shape
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
    if x1 <= x0 + 2 or y1 <= y0 + 2:
        return np.zeros((4, 4))
    return img[y0:y1, x0:x1]

def feat(crop, out=32):
    '''归一化的 crop 特征（去均值 + L2 归一）—— 相关系数即余弦相似度。'''
    z = resize(crop, out).ravel()
    z = z - z.mean()
    return z / (np.linalg.norm(z) + 1e-9)

img0, box0 = render(3, 24, g=np.random.default_rng(5))
print('场景', img0.shape, '| GT 框', box0, '| crop', crop_box(img0, box0).shape,
      '| 特征维度', feat(crop_box(img0, box0)).shape)
assert abs(np.linalg.norm(feat(crop_box(img0, box0))) - 1.0) < 1e-6
print('✅ 合成 TSR 就位：8 类、圆形外圈共有、内部图案区分类别。')"""),

    code("""def build_bank(jitter, n_per=40, seed=7):
    '''构建 exemplar bank（= 用某种裁剪方式「训练」分类器）。'''
    g = np.random.default_rng(seed)
    X, Y = [], []
    for k in range(K):
        for _ in range(n_per):
            img, box = render(k, s=int(g.integers(18, 34)), g=g)
            b = perturb(box, jitter, g) if jitter > 0 else box
            X.append(feat(crop_box(img, b))); Y.append(k)
    return np.stack(X), np.array(Y)

def evaluate(bank, jitter, n=400, seed=99):
    X, Y = bank
    g = np.random.default_rng(seed); ok = 0
    for _ in range(n):
        k = int(g.integers(0, K))
        img, box = render(k, s=int(g.integers(18, 34)), g=g)
        b = perturb(box, jitter, g) if jitter > 0 else box
        ok += int(Y[int(np.argmax(X @ feat(crop_box(img, b))))] == k)
    return ok / n

bank_gt  = build_bank(0.00)      # ❌ 用 GT 框裁剪训练（最常见的做法）
bank_jit = build_bank(0.18)      # ✅ 用带扰动的框裁剪训练（模拟检测器输出）

print(f"{'推理时的框扰动':>14s}{'GT-crop 训练':>16s}{'扰动-crop 训练':>16s}{'差':>8s}")
res = {}
for J in [0.00, 0.10, 0.18, 0.25]:
    a, b = evaluate(bank_gt, J), evaluate(bank_jit, J)
    res[J] = (a, b)
    tag = '   <- 离线评测看到的' if J == 0 else ('  <- 线上真实工况' if J == 0.18 else '')
    print(f'{J:>14.2f}{a:>16.3f}{b:>16.3f}{b - a:>+8.3f}{tag}')

assert res[0.00][0] > 0.98, '在 GT crop 上评测，一切完美'
assert res[0.18][0] < res[0.00][0] - 0.25, '换成检测框 crop，准确率断崖式下跌'
assert res[0.18][1] > res[0.18][0] + 0.08, '训练时模拟检测框扰动，能把大部分损失赚回来'

print()
print('⚠️  第一行 vs 第三行就是那个「离线 97%、路测像 91%」的故事：')
print('    在 GT crop 上评测 %.3f -> 真实工况 %.3f，**离线评测完全看不出来**。'
      % (res[0.00][0], res[0.18][0]))
print('✅ 修法只有一条：**分类器的训练数据必须用「模拟检测器输出的框」裁剪**')
print('   （给 GT 框加上与检测器误差分布一致的中心偏移 + 尺度抖动）。')
print('✅ 同样重要：**分类器的验证集也必须用检测框裁**，否则你根本测不到这个问题。')"""),

    code("""# padding 该给多少？用**几何量**来算，比跑分类器更干净：
#   ① 完整包住率 = 带误差的框 + padding 后，crop 仍然完整包住真实牌面的比例（越高越好）
#   ② 牌面占比   = 牌在 crop 中的面积份额（padding 越大越小 —— 这是代价）
def containment_rate(pad, jitter, n=200000, seed=4):
    '''归一化到 GT 边长 = 1：中心偏移 ~ U(-j, j)，尺度 ~ 1 + U(-j, j)。'''
    g = np.random.default_rng(seed)
    dx = g.uniform(-jitter, jitter, n); dy = g.uniform(-jitter, jitter, n)
    half = (1 + g.uniform(-jitter, jitter, n)) * (1 + 2 * pad) / 2
    return float(np.mean((np.abs(dx) + 0.5 <= half) & (np.abs(dy) + 0.5 <= half)))

def sign_occupancy(pad, jitter, n=200000, seed=4):
    g = np.random.default_rng(seed)
    half = (1 + g.uniform(-jitter, jitter, n)) * (1 + 2 * pad) / 2
    return float(np.mean(1.0 / (2 * half) ** 2))

print(f"{'padding':>8s}" + ''.join(f'{f"包住率 j={j:.2f}":>16s}' for j in [0.05, 0.12, 0.20])
      + f"{'牌面占比 j=0.12':>16s}")
C = {}
for pad in [0.00, 0.05, 0.10, 0.15, 0.20, 0.35]:
    C[pad] = [containment_rate(pad, j) for j in [0.05, 0.12, 0.20]]
    print(f'{pad:>8.2f}' + ''.join(f'{v:>16.3f}' for v in C[pad])
          + f'{sign_occupancy(pad, 0.12):>16.3f}')

assert C[0.00][0] < 0.30, 'padding=0：只要框有一点误差，牌面（含最有判别力的外圈）就被切掉'
assert C[0.20][1] > C[0.10][1] > C[0.00][1], '完整包住率随 padding 单调上升'
assert C[0.35][2] > 0.95, '框误差越大，需要的 padding 越大'
assert sign_occupancy(0.35, 0.12) < sign_occupancy(0.10, 0.12), 'padding 的代价：牌在 crop 里变小'

need = min(p for p in C if C[p][1] > 0.98)
print(f'\\n在 j=0.12 的框误差下，要 98% 完整包住，至少需要 padding = {need:.2f}')
print('✅ padding 的本质是**吸收检测框误差的余量**：0% 时框一偏，外圈就被切掉 —— 而')
print('   外圈（红边 / 形状）恰恰是 TSR 最有判别力的部分。')
print('✅ 自适应：pad = max(0.15, 3px / min(w,h))。小框的**相对**误差更大，要给更多余量；')
print('   同时 padding 越大牌面占比越小，所以不能无脑加 —— 这是一个可以算出来的取舍。')
print('⚠️  padding 一旦定下来就是**破坏性接口**：改它 = 两个模型都要重训重验。')"""),

    md("""## 5 · 置信度合成与标定：ECE、可靠性图、temperature scaling

`s_det × s_cls` 只有在两者**都是标定过的概率**时才有意义。
现实是：检测分数被 focal loss 压低、分类分数系统性过度自信。"""),

    code("""def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))

def ece(conf, correct, n_bins=10, return_bins=False):
    '''Expected Calibration Error：按置信度分桶，|准确率 − 平均置信度| 的加权平均。'''
    conf = np.asarray(conf, float); correct = np.asarray(correct, float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=False), 0, n_bins - 1)
    e, rows = 0.0, []
    for b in range(n_bins):
        m = idx == b
        if m.sum() == 0:
            rows.append((edges[b], edges[b + 1], 0, float('nan'), float('nan')))
            continue
        acc, cf = correct[m].mean(), conf[m].mean()
        e += m.sum() / len(conf) * abs(acc - cf)
        rows.append((edges[b], edges[b + 1], int(m.sum()), cf, acc))
    return (e, rows) if return_bins else e

def reliability(conf, correct, n_bins=10, title=''):
    '''文本版可靠性图：★=实际准确率，│=完美标定应在的位置。'''
    e, rows = ece(conf, correct, n_bins, return_bins=True)
    print(f'{title}  ECE = {e:.4f}')
    print(f"{'区间':<12s}{'样本':>7s}{'平均置信':>9s}{'实际准确':>9s}   {'差':>7s}  图")
    for lo, hi, n, cf, acc in rows:
        if n == 0:
            continue
        bar = [' '] * 42
        bar[min(41, int(cf * 41))] = '|'
        bar[min(41, int(acc * 41))] = '*'
        print(f'[{lo:.1f},{hi:.1f}){n:>9d}{cf:>9.3f}{acc:>9.3f}{acc - cf:>+8.3f}  ' + ''.join(bar))
    return e

n = 30000
p_true = rng.beta(3.0, 1.2, size=n)                 # 每个样本「真正的」正确概率
correct = (rng.random(n) < p_true).astype(float)
conf_raw = sigmoid(logit(p_true) * 2.0)             # 模型报出的分数：logit 被放大 -> 过度自信

e_oracle = ece(p_true, correct)
e_raw = reliability(conf_raw, correct, title='【未标定】高分桶里 * 在 | 左边 = 过度自信')
assert e_oracle < 0.02, '真概率本身几乎完美标定（验证 ECE 实现正确）'
assert e_raw > 0.08, '过度自信的分数 ECE 明显偏大'
assert e_raw > 8 * e_oracle
print()
print('⚠️  看**高置信度那几个桶**：★ 落在 │ 左边 = 实际准确率低于宣称置信度 = 过度自信。')
print('    这是现代深网络的典型症状，在长尾尾部类上更严重。')
print('⚠️  但注意低置信度桶里方向是**反的**（★ 在 │ 右边 = 偏保守）——')
print('    因为「logit 被整体放大」会把 p<0.5 推低、把 p>0.5 推高。')
print('    ⇒ **这两半会在单个 ECE 数字里互相抵消**，所以永远不能只看 ECE。')"""),

    code("""# Temperature scaling：单参数、不改变排序（不影响准确率/mAP）、纯后处理
def nll(conf, correct):
    c = np.clip(conf, 1e-6, 1 - 1e-6)
    return float(-(correct * np.log(c) + (1 - correct) * np.log(1 - c)).mean())

def fit_temperature(conf, correct, grid=np.linspace(0.4, 3.0, 261)):
    '''在**独立的标定集**上最小化 NLL 求 T。'''
    losses = [nll(sigmoid(logit(conf) / T), correct) for T in grid]
    return float(grid[int(np.argmin(losses))])

cal, tst = slice(0, 12000), slice(12000, n)          # 标定集 / 测试集必须分开
T_star = fit_temperature(conf_raw[cal], correct[cal])
conf_cal = sigmoid(logit(conf_raw) / T_star)

e_before = ece(conf_raw[tst], correct[tst])
e_after = ece(conf_cal[tst], correct[tst])
print(f'拟合出的温度 T = {T_star:.3f}   （数据生成时用的是 2.0 -> 应当被恢复出来）')
print(f'测试集 ECE:  标定前 {e_before:.4f}  ->  标定后 {e_after:.4f}   ({e_after / e_before:.1%})')

assert abs(T_star - 2.0) < 0.15, 'temperature scaling 应恢复出真实的过度自信系数'
assert e_after < e_before / 2, '标定后 ECE 至少减半'
order = np.argsort(conf_raw)
assert np.all(np.diff(conf_cal[order]) >= -1e-12), \\
    'T>0 是单调变换 -> **排序不变 -> 准确率/mAP 完全不变**'

_ = reliability(conf_cal[tst], correct[tst], title='\\n【标定后】')
print()
print('✅ temperature scaling 的三个工程优点：①单参数②不改排序（准确率/mAP 不动）③纯后处理。')
print('⚠️  两个陷阱：① **不能在训练集上标定**（模型在训练集上近乎完美，T≈1，等于没做）；')
print('   ② **标定依赖分布** —— 晴天标出的 T，夜间/雨天依然过度自信 -> 应分场景各标一个 T。')
print('⚠️  别只报一个 ECE 数字：它会让「低分区偏保守」和「高分区过自信」互相抵消。')
print('   **必须看可靠性图，尤其是最高的那两三个桶** —— 下游只用高置信度的检测。')"""),

    code("""# 合成：两个未标定分数相乘 vs 各自标定后相乘
m = 30000
pd_true = rng.beta(3.0, 1.2, size=m)     # 真·「这里有个牌」的概率
pc_true = rng.beta(2.5, 1.2, size=m)     # 真·「类别判对」的条件概率
det_ok = rng.random(m) < pd_true
cls_ok = rng.random(m) < pc_true
joint = (det_ok & cls_ok).astype(float)  # 端到端正确 = 两级都对

sd_raw = sigmoid(logit(pd_true) * 1.5)   # 检测分数：过度自信
sc_raw = sigmoid(logit(pc_true) * 1.9)   # 分类分数：更过度自信

c2 = slice(0, 12000); t2 = slice(12000, m)
Td = fit_temperature(sd_raw[c2], det_ok[c2].astype(float))
Tc = fit_temperature(sc_raw[c2], cls_ok[c2].astype(float))
sd_cal = sigmoid(logit(sd_raw) / Td)
sc_cal = sigmoid(logit(sc_raw) / Tc)

rows = [
    ('未标定相乘  s_det × s_cls', sd_raw[t2] * sc_raw[t2]),
    ('各自标定后相乘',            sd_cal[t2] * sc_cal[t2]),
    ('理论上界（用真概率相乘）',   pd_true[t2] * pc_true[t2]),
    ('只用 s_det（忽略分类）',    sd_raw[t2]),
]
print(f"{'合成方式':<26s}{'ECE(端到端正确)':>16s}")
E = {}
for nm, v in rows:
    E[nm] = ece(v, joint[t2])
    print(f'{nm:<26s}{E[nm]:>16.4f}')

assert E['理论上界（用真概率相乘）'] < 0.02, '链式法则成立：真概率相乘就是端到端的真概率'
assert E['各自标定后相乘'] < E['未标定相乘  s_det × s_cls'] / 2, '分别标定后再相乘，ECE 大幅下降'
assert E['只用 s_det（忽略分类）'] > E['各自标定后相乘'], '丢掉分类置信度会严重高估'
print(f'\\n拟合温度：T_det = {Td:.2f}, T_cls = {Tc:.2f}（分类器更过度自信，符合预期）')
print()
print('✅ **乘法只在两者都标定后才有概率语义**。链式法则要求的是概率，不是「分数」。')
print('⚠️  最后一行：只把检测分数传给下游 = 假装分类永远是对的 -> 系统性高估。')
print('   **感知→决策接口最常见的设计错误就是不传或传错置信度**（C59 模块 03 会再讲一次）。')"""),

    md("""## 6 · 拒识：阈值按「代价」定，而不是按「准确率」定

softmax 在任何输入上都会给一个答案。拒识就是给它加一道闸门 ——
而闸门的高度应该由 **误报代价 vs 漏检代价** 决定：`τ = c_FP / (c_FP + c_FN)`。"""),

    code("""COST = {                       # (误报代价, 漏检代价) —— 数量级差异是真实的
    '停车让行 STOP': (2.0, 200.0),
    '限速 60':      (8.0, 40.0),
    '禁止掉头':      (15.0, 25.0),
    '景点指示':      (25.0, 1.0),
}

def opt_tau(c_fp, c_fn):
    '''最小期望代价的决策阈值：上报 iff (1−p)·c_FP < p·c_FN。'''
    return c_fp / (c_fp + c_fn)

def realized_cost(p, y, c_fp, c_fn, tau):
    '''p: 标定后的置信度; y: 是否真的是该类; tau: 上报阈值。'''
    report = p > tau
    return float(((report & (y == 0)) * c_fp + ((~report) & (y == 1)) * c_fn).sum())

g = np.random.default_rng(21)
N = 60000
p_hat = g.beta(2.0, 2.0, size=N)
y = (g.random(N) < p_hat).astype(int)

print(f"{'类别':<16s}{'c_FP':>7s}{'c_FN':>7s}{'最优 τ':>9s}{'τ=0.5 代价':>12s}{'最优 τ 代价':>13s}{'省':>8s}")
tot_fixed = tot_opt = 0.0
for name, (cfp, cfn) in COST.items():
    t = opt_tau(cfp, cfn)
    c_fixed = realized_cost(p_hat, y, cfp, cfn, 0.5)
    c_opt = realized_cost(p_hat, y, cfp, cfn, t)
    tot_fixed += c_fixed; tot_opt += c_opt
    print(f'{name:<16s}{cfp:>7.1f}{cfn:>7.1f}{t:>9.3f}{c_fixed:>12.0f}{c_opt:>13.0f}'
          f'{1 - c_opt / c_fixed:>7.1%}')
    assert c_opt <= c_fixed + 1e-9, f'{name}: 代价最优阈值不应比 0.5 差'

assert opt_tau(2.0, 200.0) < 0.05, '漏检代价极高 -> 阈值极低 -> 宁滥勿缺'
assert opt_tau(25.0, 1.0) > 0.90, '误报代价高、漏检无所谓 -> 阈值极高 -> 宁缺勿滥'
assert tot_opt < tot_fixed * 0.85, '逐类阈值显著优于全局 0.5'

print(f'\\n总代价：全局 τ=0.5 -> {tot_fixed:.0f}  |  逐类最优 τ -> {tot_opt:.0f}'
      f'  （降低 {1 - tot_opt / tot_fixed:.1%}）')
print()
print('✅ 「停车让行」阈值 %.3f（几乎不拒），「景点指示」阈值 %.3f（几乎全拒）——'
      % (opt_tau(*COST['停车让行 STOP']), opt_tau(*COST['景点指示'])))
print('   **同一个模型，不同类别用完全不同的工作点**，这就是代价敏感决策。')
print('⚠️  前提：p 必须是**标定过的概率**。未标定的分数代进这个不等式，阈值全是错的。')
print('   ⇒ 第 5 节的标定不是「锦上添花」，它是代价敏感决策的**前置条件**。')"""),

    md("""## ✏️ 练习 1：改进优先级排序器

实现 `improvement_plan(rates, ceilings, costs)`：

- `rates`：各级当前通过率；`ceilings`：各级能提升到的天花板；`costs`：各级提升到天花板的成本
- 返回 `{'base':…, 'gains':[…], 'roi':[…], 'best_gain':idx, 'best_roi':idx}`
- `gains[i]` = 只把第 i 级提到天花板时的**端到端**增量；`roi[i] = gains[i] / costs[i]`

**这是「下个季度做什么」的决策器**，也是级联公式最直接的工程用途。"""),
    code("""def improvement_plan(rates, ceilings, costs):
    # TODO: ① base = cascade_recall(rates)
    #       ② 对每个 i：把 rates[i] 换成 ceilings[i]，算端到端增量
    #       ③ roi = gain / cost；返回按 gain 与按 roi 的最优下标
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
pl = improvement_plan([0.92, 0.94], [0.970, 0.985], [2.0, 1.0])
assert abs(pl['base'] - 0.8648) < 1e-9
assert abs(pl['gains'][0] - (0.97 * 0.94 - 0.8648)) < 1e-9
assert abs(pl['gains'][1] - (0.92 * 0.985 - 0.8648)) < 1e-9
assert pl['best_gain'] == 0, '按绝对增量：检测'
assert pl['best_roi'] == 1, '按每单位成本收益：分类'
pl3 = improvement_plan([0.90, 0.95, 0.98], [0.96, 0.97, 0.99], [1.0, 1.0, 1.0])
assert pl3['best_gain'] == 0 and pl3['best_roi'] == 0, '三级时最弱的一级空间最大'
assert abs(sum(pl3['gains']) - sum(pl3['roi'])) < 1e-9, '成本全为 1 时 gain == roi'
print(f"{'级':<6s}{'gain':>10s}{'roi':>10s}")
for i, (g_, r_) in enumerate(zip(pl['gains'], pl['roi'])):
    print(f'{i:<6d}{g_:>10.4f}{r_:>10.4f}')
print('✅ 练习 1 通过：**排序会因为「除以成本」而反转** —— 这正是决策的价值所在。')"""),

    md("""## ✏️ 练习 2：自适应 padding 的 crop 契约

实现 `adaptive_crop(box, min_pad=0.15, min_pad_px=3.0)`：

1. **正方形化**：以框中心为心，边长取 `max(w, h)`
2. **自适应 padding**：`pad = max(min_pad, min_pad_px / side)`（小框需要更大的相对余量）
3. 返回 `(x0, y0, x1, y1, pad)`，均为 float，不做边界裁剪

这就是两级方案的 API 契约 —— **一旦定下就不能随便改**。"""),
    code("""def adaptive_crop(box, min_pad=0.15, min_pad_px=3.0):
    # TODO: box = (x, y, w, h) -> 正方形化 -> 自适应 padding -> (x0, y0, x1, y1, pad)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
x0, y0, x1, y1, pad = adaptive_crop((100.0, 100.0, 60.0, 40.0))
assert abs(pad - 0.15) < 1e-9, '大框用 min_pad'
assert abs((x0 + x1) / 2 - 130.0) < 1e-9 and abs((y0 + y1) / 2 - 120.0) < 1e-9, '中心不变'
assert abs((x1 - x0) - (y1 - y0)) < 1e-9, '必须是正方形'
assert abs((x1 - x0) - 60.0 * 1.30) < 1e-9, '边长 = side × (1 + 2·pad)'

_, _, _, _, pad_small = adaptive_crop((10.0, 10.0, 12.0, 12.0))
assert abs(pad_small - 0.25) < 1e-9, '12 px 的框：3/12 = 0.25 > 0.15'
assert pad_small > pad, '**小框必须得到更大的相对 padding**'

_, _, _, _, pad_tiny = adaptive_crop((0.0, 0.0, 8.0, 8.0))
assert abs(pad_tiny - 0.375) < 1e-9
print(f"{'原始框 (w×h)':<16s}{'边长':>8s}{'pad':>8s}{'crop 边长':>12s}")
for b in [(0, 0, 8, 8), (0, 0, 12, 12), (0, 0, 32, 32), (0, 0, 60, 40)]:
    a, b_, c_, d_, p = adaptive_crop(tuple(float(v) for v in b))
    print(f'{f"{b[2]}×{b[3]}":<16s}{max(b[2], b[3]):>8d}{p:>8.3f}{c_ - a:>12.2f}')
print('✅ 练习 2 通过：**小框的检测误差相对量级更大 -> 需要更大的 padding 比例。**')"""),

    md("""## ✏️ 练习 3：高置信度区的标定审计

单个 ECE 数字会让「低分区偏保守」与「高分区过自信」**互相抵消**。
而下游只会使用高置信度的检测 —— 所以必须单独审计高分区。

实现 `calibration_audit(conf, correct, n_bins=10, hi=0.8)`，返回：
- `'ece'`：整体 ECE（可直接调用上面已实现的 `ece`）
- `'hi_gap'`：`conf >= hi` 的样本上 `平均置信度 − 实际准确率`（**正数 = 过度自信**）
- `'hi_n'`：该区间样本数
- `'worst_bin'`：`|acc − conf|` 最大且样本数 ≥ 30 的桶的 `(lo, hi, gap)`"""),
    code("""def calibration_audit(conf, correct, n_bins=10, hi=0.8):
    # TODO: 返回 {'ece':…, 'hi_gap':…, 'hi_n':…, 'worst_bin': (lo, hi, gap)}
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
au_raw = calibration_audit(conf_raw[tst], correct[tst])
au_cal = calibration_audit(conf_cal[tst], correct[tst])
assert abs(au_raw['ece'] - ece(conf_raw[tst], correct[tst])) < 1e-12
assert au_raw['hi_gap'] > 0.05, '未标定：高置信度区严重过度自信'
assert abs(au_cal['hi_gap']) < au_raw['hi_gap'] / 2, '标定后高置信度区的缺口大幅收窄'
assert au_raw['hi_n'] > 1000 and au_cal['hi_n'] > 500

# 构造一个「整体 ECE 很小、但高分区很糟」的例子 —— 说明为什么必须分区看
g = np.random.default_rng(5)
c_lo = np.full(6000, 0.30); y_lo = (g.random(6000) < 0.42).astype(float)   # 低分区偏保守
c_hi = np.full(6000, 0.95); y_hi = (g.random(6000) < 0.83).astype(float)   # 高分区过自信
cc = np.concatenate([c_lo, c_hi]); yy = np.concatenate([y_lo, y_hi])
au = calibration_audit(cc, yy)
assert au['hi_gap'] > 0.10, '高分区缺口 ≈ 0.95 − 0.83 = 0.12'
assert au['worst_bin'][2] > 0.10
print(f"整体 ECE = {au['ece']:.4f}   高分区(≥0.8) gap = {au['hi_gap']:+.4f}"
      f"   最差桶 = [{au['worst_bin'][0]:.1f},{au['worst_bin'][1]:.1f}) gap={au['worst_bin'][2]:.3f}")
print('✅ 练习 3 通过：**别只报一个 ECE 数字，必须看高置信度那几个桶。**')"""),

    md("""## ✏️ 练习 4：标注预算怎么在两级之间分配

一个几乎每个团队都在拍脑袋决定的真问题：**有 B 条标注预算，
多少给「检测数据」、多少给「分类数据」？**

实现 `allocate_budget(budget, r_fn, a_fn, step=100)`：网格搜索所有划分，
返回 `{'n_det':…, 'n_cls':…, 'recall':…}`，使 `r_fn(n_det) * a_fn(n_cls)` 最大。"""),
    code("""def allocate_budget(budget, r_fn, a_fn, step=100):
    # TODO: 对 n_det 从 0 到 budget 按 step 网格搜索，最大化 r_fn(n_det) * a_fn(budget - n_det)
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
R_of = lambda n: 0.99 * (1 - np.exp(-n / 2000.0))     # 检测：样本效率低（n0 大）
A_of = lambda n: 0.99 * (1 - np.exp(-n / 800.0))      # 分类：任务简单（n0 小），更快饱和

al = allocate_budget(6000, R_of, A_of, step=100)
assert al['n_det'] + al['n_cls'] == 6000
assert 3000 < al['n_det'] < 5000, f"最优解应在内部，得到 {al['n_det']}"
assert al['n_det'] > al['n_cls'], '饱和更慢的一级（检测）应该分到更多预算'
assert al['recall'] > R_of(3000) * A_of(3000), '最优划分优于 50/50 均分'
assert al['recall'] > R_of(6000) * A_of(0), '全给一级 = 另一级为 0 = 端到端为 0'

print(f"{'n_det':>8s}{'n_cls':>8s}{'R_det':>9s}{'A_cls':>9s}{'端到端':>9s}")
for nd in [1000, 3000, al['n_det'], 5000]:
    nc = 6000 - nd
    tag = '   <- 最优' if nd == al['n_det'] else ''
    print(f'{nd:>8d}{nc:>8d}{R_of(nd):>9.4f}{A_of(nc):>9.4f}{R_of(nd) * A_of(nc):>9.4f}{tag}')
print('✅ 练习 4 通过：**最优解总在内部** —— 因为乘积里任何一项为 0 都会毁掉全部。')
print('   这也是「短板优先」的严格版本：短板由 1−p 与该级的**边际斜率**共同决定。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def improvement_plan(rates, ceilings, costs):
    base = cascade_recall(rates)
    gains = []
    for i, c in enumerate(ceilings):
        r2 = list(rates); r2[i] = c
        gains.append(cascade_recall(r2) - base)
    roi = [g / c for g, c in zip(gains, costs)]
    return {'base': base, 'gains': gains, 'roi': roi,
            'best_gain': int(np.argmax(gains)), 'best_roi': int(np.argmax(roi))}"""),
    code("""# 练习 2 参考答案
def adaptive_crop(box, min_pad=0.15, min_pad_px=3.0):
    x, y, w, h = box
    side = max(w, h)
    cx, cy = x + w / 2.0, y + h / 2.0
    pad = max(min_pad, min_pad_px / side)          # 小框 -> 更大的相对余量
    half = side * (1.0 + 2.0 * pad) / 2.0
    return (cx - half, cy - half, cx + half, cy + half, pad)"""),
    code("""# 练习 3 参考答案
def calibration_audit(conf, correct, n_bins=10, hi=0.8):
    conf = np.asarray(conf, float); correct = np.asarray(correct, float)
    e, rows = ece(conf, correct, n_bins, return_bins=True)
    m = conf >= hi
    hi_gap = float(conf[m].mean() - correct[m].mean()) if m.sum() else float('nan')
    worst = (float('nan'), float('nan'), -1.0)
    for lo, hi_, n_, cf, acc in rows:
        if n_ >= 30 and abs(acc - cf) > worst[2]:
            worst = (lo, hi_, abs(acc - cf))
    return {'ece': e, 'hi_gap': hi_gap, 'hi_n': int(m.sum()), 'worst_bin': worst}"""),
    code("""# 练习 4 参考答案
def allocate_budget(budget, r_fn, a_fn, step=100):
    best = {'n_det': 0, 'n_cls': budget, 'recall': -1.0}
    for n_det in range(0, budget + 1, step):
        n_cls = budget - n_det
        r = float(r_fn(n_det) * a_fn(n_cls))
        if r > best['recall']:
            best = {'n_det': n_det, 'n_cls': n_cls, 'recall': r}
    return best"""),

    md("""---
## 🧪 真实工程胶囊：两级 TSR 的接口契约 + 标定 + 日志 schema

下面这段可以原样复制进真实项目。三样东西缺一不可：
**冻结的 crop 契约**、**分场景的标定表**、**能归因到具体一级的日志**。"""),
    code("""RECIPE = r'''
# ─────────────────────────────────────────────────────────────
# ① crop 契约（configs/tsr_crop_contract.yaml）—— 改它 = 破坏性变更，两个模型都要重训
# ─────────────────────────────────────────────────────────────
crop_contract:
  version: "v3"                  # 每次变更 +1，模型权重文件名里带上它
  squarify: true                 # 以框中心扩成正方形（**保长宽比：形状是 TSR 的一级语义**）
  pad_ratio_min: 0.15            # 基础 padding
  pad_ratio_min_px: 3.0          # 自适应：pad = max(0.15, 3px / side)
  out_size: [64, 64]
  interp: bilinear               # 训练与车端必须**同一种插值**（见 C60 模块 01）
  border_mode: replicate         # 越界时的填充方式，也必须一致
  # 训练时对 GT 框施加的扰动 —— 必须与检测器的真实误差分布一致
  train_jitter: {center: 0.12, scale: 0.15}   # 从检测器验证集统计出来，不是拍脑袋

# 检测器输出的统计脚本（用来标定上面的 train_jitter）：
#   for gt, pred in matched_pairs(det_val_set):
#       dcx.append((pred.cx - gt.cx) / gt.w); dsc.append(pred.w / gt.w - 1)
#   train_jitter.center = np.percentile(np.abs(dcx), 90)
#   train_jitter.scale  = np.percentile(np.abs(dsc), 90)

# ─────────────────────────────────────────────────────────────
# ② 分场景 temperature scaling（纯后处理，不改排序 -> 不动 mAP）
# ─────────────────────────────────────────────────────────────
# 在**独立验证集**上按场景各拟合一个 T；线上按当前场景标签查表
CALIB = {
    "day_clear":  {"T_det": 1.42, "T_cls": 1.86},
    "night":      {"T_det": 1.95, "T_cls": 2.41},   # 夜间更过度自信
    "rain_fog":   {"T_det": 2.10, "T_cls": 2.28},
    "tunnel":     {"T_det": 2.35, "T_cls": 2.55},
}
def calibrated_score(s, T):
    z = np.log(np.clip(s, 1e-6, 1 - 1e-6) / (1 - np.clip(s, 1e-6, 1 - 1e-6)))
    return 1.0 / (1.0 + np.exp(-z / T))

p = calibrated_score(s_det, CALIB[scene]["T_det"]) * calibrated_score(s_cls, CALIB[scene]["T_cls"])

# ─────────────────────────────────────────────────────────────
# ③ 逐类代价阈值（拒识）：tau = c_FP / (c_FP + c_FN)
# ─────────────────────────────────────────────────────────────
COST = {"stop": (2, 200), "speed_limit": (8, 40), "no_uturn": (15, 25), "poi": (25, 1)}
TAU  = {k: cfp / (cfp + cfn) for k, (cfp, cfn) in COST.items()}
emit = p > TAU[cls_name]          # 上报 iff 期望代价更低

# ─────────────────────────────────────────────────────────────
# ④ 日志 schema —— **没有它，两级的可调试性优势直接归零**
# ─────────────────────────────────────────────────────────────
LOG_FIELDS = [
    "frame_id", "ts_ns", "camera_id",
    "det_box_xywh", "s_det_raw", "s_det_cal",     # 第一级：框 + 原始/标定分数
    "crop_box_xywh", "crop_pad", "contract_ver",  # 接口：实际用了什么 crop
    "cls_top3", "cls_top3_scores", "s_cls_cal",   # 第二级：top-3 而不只是 top-1
    "p_joint", "tau_used", "emitted", "reject_reason",
    "track_id", "n_frames_confirmed", "scene_tag",
]
# 体积：每帧每候选约 200–300 B。**这份日志是整个数据闭环的地基**
# （模块 05 的分桶评测、C58 的难例触发，全部建立在它上面）。

# ─────────────────────────────────────────────────────────────
# ⑤ 评测铁律（写进 CI）
# ─────────────────────────────────────────────────────────────
# 1) 分类器的验证集**必须用检测器输出的框**裁剪，不是 GT 框
# 2) 对外只报端到端 recall = R_det × A_cls，不报分级指标
# 3) 逐类 macro + 分尺寸分桶，micro 会淹没尾部类
# 4) 延迟报 p99 不报均值；crop 数固定 batch，方差比均值更重要
'''
print(RECIPE)
for key in ['crop_contract', 'train_jitter', 'calibrated_score', 'TAU', 'LOG_FIELDS',
            'cls_top3', 'contract_ver', 'p99']:
    assert key in RECIPE, key
print('✅ 配方覆盖：crop 契约 / 扰动统计 / 分场景标定 / 代价阈值 / 可归因日志 / 评测铁律')"""),

    md("""### 小结

- **级联召回 = 检测召回 × 分类准确率**。对数域上各级损失相加，**没有任何一级能补偿另一级**。
  0.90 × 0.90 = 0.81 —— 两个「还行」的模块合起来是「不能用」。**对外只能汇报端到端。**
- **边际收益 ΔR = Δp_i × (其余各级之积)**。两级时两者往往接近 ⇒ 光看收益无法决策，
  必须引入**成本**与**天花板**；车端还要再乘一条**延迟代价**。
- **两级的收益几乎全部来自尾部类**（头部类谁都学得会）⇒ 评测必须看 **macro 与逐类**，
  micro 会把这个收益完全淹没。
- **crop 是两级方案的 API**。用 GT 框训练、用检测框推理会凭空损失十几个点，而**离线评测看不出来**。
  修法：训练时按检测器的真实误差分布扰动 GT 框；**验证集也必须用检测框裁**。
- **padding 要自适应**：`pad = max(0.15, 3px / side)`。小框的相对框误差更大。
  正方形化时**必须保长宽比**——形状本身是 TSR 的一级语义。
- **乘法只在两个分数都标定后才有概率语义**。temperature scaling 单参数、不改排序、纯后处理，
  几乎是白拿的改进；但**不能在训练集上标定**，且**必须分场景标定**。
- **别只报一个 ECE**：它会让低分区的保守与高分区的自信互相抵消。**看高置信度那几个桶。**
- **拒识阈值 τ = c_FP / (c_FP + c_FN)**，逐类不同。这要求 p 是标定过的概率 ——
  标定不是锦上添花，是代价敏感决策的前置条件。
- **级联的阈值应「前松后紧」**：早期漏检不可恢复（乘法里的 0 吞掉一切），
  早期误检可被后续更强的判别力低成本滤除。这条原则可迁移到任何级联系统。

下一站：**模块 03 · 失效模式全景** —— 把「哪里会错」拆成四象限并逐一深挖，
这是 JD 里「Analyze TSR-related scenarios and failure cases」的直接对应。"""),
]
