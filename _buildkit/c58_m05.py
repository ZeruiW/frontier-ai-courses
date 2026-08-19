# -*- coding: utf-8 -*-
"""C58 模块 05 · 闭环验证：证明数据真的有用。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–04（不平衡 / 难例挖掘 / 触发 / 挖掘基础设施）；C55 模块 05（安全导向评测）与 C61 模块 01（实验设计）强相关"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_closed_loop_validation.ipynb'),
    ("核心参考", "Benjamini–Hochberg FDR、bootstrap 置信区间、continual learning 的遗忘度量、A/B 测试与序贯分析"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("three_q", "加了数据之后，必须回答的三个问题", "".join([
        P("模块 04 结束时，1200 张隧道口施工牌已经标完入库了。现在有人把它加进训练集，重训，跑了一遍评测，说「<strong>mAP 从 0.612 涨到 0.618，有效</strong>」。<em>这句话里至少有三处站不住脚</em>。本模块就是把这三处补上——这也是数据闭环里唯一真正难的一环：<strong>挖数据和标数据都有明确的产出物，只有「证明它有用」没有</strong>。"),
        TABLE(["必须回答的问题", "不回答的后果", "本模块对应的工具"], [
            ["<strong>① 目标场景涨了吗？</strong>", "整体 mAP 涨了 0.6 点，可能全部来自晴天城区；<em>你花钱修的隧道场景纹丝不动</em>", "分场景切片评测（第 2 节）"],
            ["<strong>② 其他场景掉了吗？</strong>", "隧道 +4.1，夜间城区 −2.3。整体看是涨的，<strong>但你刚刚让一个更常见的场景变差了</strong>", "回归门禁 + 数据配比（第 4、5 节）"],
            ["<strong>③ 涨的部分是数据的功劳，还是噪声？</strong>", "换个随机种子重训，+0.6 变成 −0.2。<em>你把一次抽样波动写进了周报</em>", "显著性与多重比较（第 3 节）"],
        ]),
        DUAL(
            "这三个问题有一个共同的形状：<strong>它们都在追问「这个数字还能不能再被解释成别的东西」</strong>。① 追问平均值掩盖了什么；② 追问收益的另一面代价是什么；③ 追问随机性能不能单独解释它。<em>能把这三问自动化成一套流程，数据闭环才算真正闭上；否则每一轮迭代都是在赌博。</em>",
            "更精确地说，这是一个<strong>因果归因问题</strong>：我们想知道「加这批数据」这个干预（treatment）对「目标场景 AP」这个结果的因果效应。理想实验是同一模型、同一超参、同一评测集，只改训练数据这一个变量，重复多次取分布。<em>而实践中几乎所有的「数据有效性结论」都是在单次训练、单个种子、单个整体指标上下的</em>——<strong>这就是为什么「加了数据没效果」在工业界如此普遍：不是数据没用，是验证方法压根没有能力检出效果，或者反过来，把噪声当成了效果。</strong>",
        ),
        CALLOUT("danger", "<p>一个真实且极其常见的翻车路径：<strong>目标场景的数据既进了训练集，又（因为是同一批回传、同一段路）进了评测集</strong>。于是目标场景 AP 从 0.34 涨到 0.71，看起来是本季度最大的胜利，实际是数据泄漏。</p><p><em>模块 04 已经给过防线：划分必须按 clip / 路段 / 日期，而不是按帧。</em>但闭环里还有第二道必须做的检查：<strong>新加入的训练 batch 与评测集做一次 ID 与近重复的交集检查，非空就直接拒绝这次实验</strong>——不是警告，是拒绝。<em>因为泄漏产生的指标提升足够大、足够稳定，稳定到没人会怀疑它。</em></p>", "泄漏产生的提升，稳定到没人会怀疑"),
    ])),

    ("slices", "分场景切片评测：平均值是用来骗人的", "".join([
        P("整体 mAP 是一个<strong>按样本数加权的平均</strong>。而车队数据的分布是极度长尾的——晴天白天城区可能占了评测集的 40%，雾天隧道占 1.5%。<strong>于是「雾天隧道 AP 掉 8 个点」在整体 mAP 上只体现为 −0.12，被任何一个其他场景的小幅波动淹没</strong>。这不是统计学的缺陷，是加权平均的定义。"),
        ASCII("""同一次实验，两种读法

  整体 mAP:  0.612 -> 0.618   (+0.6 点)   "有效，合入"
  ─────────────────────────────────────────────────────────────
  按场景切片看：
    切片                 n_eval   base    new    Δ        判定
    day_clear_urban       2400    .861   .869   +0.8      涨（但这不是我们花钱的地方）
    night_urban            720    .774   .751   -2.3  ◄── **回归！而且是常见场景**
    rain_highway           310    .706   .712   +0.6      涨
    fog_tunnel              95    .341   .682  +34.1  ◄── 目标场景，确实修好了
    snow_any                48    .559   .554   -0.5      噪声范围内
  ─────────────────────────────────────────────────────────────
  加权平均 = (2400*.869 + 720*.751 + ...) / 3573 = 0.618
             ↑ fog_tunnel 的 +34 点，被 95/3573 = 2.7% 的权重压成了 +0.9 点的贡献
             ↑ night_urban 的 -2.3 点，被 20% 的权重放大成 -0.46 点

  结论：整体 +0.6 点里，**目标场景的贡献和一个未被发现的回归，恰好互相抵消了一部分**""")
        ,
        H3("切片该怎么设计"),
        P("切片不是随便切的。一个能用的切片体系要同时满足三条："),
        OL([
            "<strong>切片来自失效模式，而不是来自数据字段</strong>。有 <code>weather</code> 字段就按天气切，是把工具当目的。<em>正确的顺序是：先列出模块 03 的失效模式清单（远距离小目标、隧道逆光、广告牌误检……），每一个对应一个切片</em>。<strong>切片是失效模式的可度量化身。</strong>",
            "<strong>每个切片有足够的样本量</strong>。切片太细会让每个切片只有二三十张图，此时 AP 的抽样噪声大到任何结论都不可信。经验下界：<em>目标类别的实例数 ≥ 200，或图片数 ≥ 100</em>；不够就先合并，或者专门去补评测数据。",
            "<strong>切片要正交且可组合</strong>，并且<strong>必须包含一个「整体/常见场景」切片作为回归哨兵</strong>。只盯着目标切片是本模块要反复强调的错误。",
        ]),
        TABLE(["切片维度", "TSR 上的典型取值", "为什么这一维必须切"], [
            ["<strong>像素尺寸 / 距离</strong>", "&lt;16px / 16–32px / 32–64px / &gt;64px", "<strong>TSR 的核心难点</strong>；不切开就看不见小目标的改进（C57 全课都在讲这个）"],
            ["光照 / 天气", "day / night / dusk / tunnel × clear / rain / fog", "退化类型完全不同，模型对它们的鲁棒性也完全不同"],
            ["遮挡度", "none / partial / heavy", "遮挡样本的 AP 通常比无遮挡低 20+ 点，混在一起看不出改进"],
            ["<strong>标志类别</strong>", "按 GB 5768 大类，稀有类单列", "长尾类的 AP 波动极大，且<strong>安全权重差异巨大</strong>"],
            ["<strong>安全关键子集</strong>", "stop / yield / 限速下调 / 施工", "<em>这一组必须单独设门禁</em>——漏检代价与其他类不是一个量级"],
        ]),
        DUAL(
            "<strong>切片评测最直接的价值是把「模型变好了吗」变成一个有结构的答案</strong>：它在哪里变好了、哪里变差了、代价换在了哪。<em>面试里被问「你怎么验证你的改动有效」，如果回答只有「mAP 涨了 0.8」，基本就到此为止了；如果回答是「整体 +0.8，其中目标切片 +34、夜间城区 −2.3，我们发现后者是数据配比导致的，调整后 −0.4 落在容差内」，这是完全不同的层次。</em>",
            "但要警惕切片评测的<strong>反向失效</strong>：切片一多，「至少有一个切片显著变差」就成了必然事件——这是第 3 节要处理的多重比较问题。<em>更隐蔽的是切片本身的漂移</em>：如果切片的标签由 VLM 打（模块 04），而 VLM 换了版本，那么「fog 切片的 AP 变化」里就混进了「哪些图算 fog」的变化。<strong>评测集的切片标签必须冻结、版本化、且尽量人工核过</strong>——评测集是尺子，尺子不能跟着被测物一起变。",
        ),
        CALLOUT("warn", "还有一个必须做但常被忘的切片：<strong>「新加入数据所属的场景」与「新数据<em>没有</em>覆盖的场景」要分开报</strong>。前者是你期望涨的，后者是回归风险最高的地方。<em>把它们混在一张大表里，人眼会自动只看涨的那几行</em>——所以报告模板要把「预期收益切片」和「回归哨兵切片」物理分成两块，并且回归块放在前面。"),
    ])),

    ("significance", "涨了多少才不是噪声：配对检验与多重比较", "".join([
        P("检测任务在<strong>同一配置、只换随机种子</strong>时，mAP 的波动典型在 ±0.2–0.5 个点。<strong>这意味着「+0.3 的提升」本身没有任何信息量</strong>——它落在噪声带里。这是面试里最能立刻显出水平的一个点，也是模块 05 与 C61 模块 01 共享的核心方法论。"),
        H3("三个层次的随机性，来源不同、对策不同"),
        TABLE(["随机性来源", "怎么表现", "怎么处理"], [
            ["<strong>评测集抽样噪声</strong>", "换一批评测图，AP 就变", "<strong>bootstrap 置信区间</strong>（对图像重采样）"],
            ["<strong>训练随机性（种子）</strong>", "同配置重训，AP 变 ±0.2–0.5", "<strong>多种子重复</strong>（3–5 个），报均值 ± 标准差"],
            ["<strong>多重比较</strong>", "切片一多，总有几个「显著」", "<strong>Bonferroni / BH-FDR 校正</strong>"],
        ]),
        P("最容易被跳过的是第二行。<em>但它的代价最大</em>：评测集噪声可以靠 bootstrap 量化（不用重训，几乎免费），种子噪声却必须真的重训 3–5 次。<strong>于是绝大多数团队的做法是「单种子 + 单次评测」，然后把 ±0.4 的随机波动当成结论——这是行业里最普遍的方法论债务。</strong>"),
        H3("配对（paired）比较：免费拿回大量统计功效"),
        P("baseline 和新模型是在<strong>同一批图</strong>上评测的，所以两者的误差高度相关：一张本来就很难的图，两个模型都会做得差。<strong>对每张图算差值 <code>d_i = s_new,i − s_base,i</code>，再对 <code>d</code> 做统计，而不是分别对两组分数做统计</strong>——图像固有难度这一大块方差被直接抵消掉了。"),
        MATH("\\bar{d} = \\frac{1}{n}\\sum_i d_i, \\quad \\mathrm{SE} = \\frac{s_d}{\\sqrt{n}}, \\quad z = \\frac{\\bar{d}}{\\mathrm{SE}}, \\quad p = 2\\left(1 - \\Phi(|z|)\\right)"),
        P("配对能把所需样本量降低一个数量级。notebook 里会实测：同一组数据上，<strong>非配对检验说「不显著」，配对检验说「p &lt; 0.001」——而后者才是对的</strong>，因为前者把「有些图天生就难」也算进了噪声。"),
        H3("多重比较：切片一多，假阳性是必然的"),
        P("假设你有 20 个切片，且新模型其实<strong>完全没有变化</strong>。在 α = 0.05 下，每个切片有 5% 的概率被误判为「显著变化」，那么<strong>至少出现一个假阳性的概率是 1 − 0.95²⁰ ≈ 64%</strong>。也就是说：<em>只要你切片够多，每次实验都能「发现」一个回归或一个提升，而它们都是假的</em>。"),
        MATH("\\text{FWER} = 1 - (1-\\alpha)^m \\xrightarrow{\\ m=20,\\ \\alpha=0.05\\ } 0.64, \\qquad \\text{Bonferroni: } \\alpha' = \\frac{\\alpha}{m}"),
        TABLE(["校正方法", "控制什么", "怎么算", "什么时候用"], [
            ["<strong>不校正</strong>", "什么也不控制", "—", "<em>只有一个预先声明的主指标时</em>"],
            ["<strong>Bonferroni</strong>", "FWER（一个假阳性都不要）", "阈值除以 m", "<strong>回归门禁</strong>——宁可漏报也别乱报警"],
            ["<strong>Benjamini–Hochberg</strong>", "FDR（假阳性占比 ≤ q）", "按 p 排序，找最大的 k 使 p₍k₎ ≤ k·q/m", "<strong>探索性分析</strong>——找「哪些切片值得深挖」"],
        ]),
        DUAL(
            "选哪个取决于<strong>你更怕哪种错</strong>。回归门禁怕的是「误报」——每次误报都会浪费一个工程师半天去查一个不存在的回归，久了就没人看门禁了，那才是真正的灾难。<em>所以门禁用 Bonferroni（保守）</em>。而在探索阶段，你想知道「哪几个切片可能有问题、值得看看」，漏掉真问题比多查两个更亏，<strong>所以探索用 BH-FDR（宽松但可控）</strong>。",
            "还有一个更本质的做法可以避开整个多重比较问题：<strong>预注册（pre-registration）</strong>——在跑实验<em>之前</em>就声明「这次实验的主指标是 fog_tunnel 切片的 AP，回归哨兵是 day_clear_urban 和 night_urban 两个切片」。<em>预先声明的少数几个指标不需要重校正，事后翻遍 20 个切片找亮点才需要</em>。<strong>「先声明再看数」这个纪律，比任何统计校正都有效</strong>——它把 p-hacking 从源头上堵住了。这条在 C61 模块 01 里会展开。",
        ),
        CALLOUT("intuition", "一句能直接用的话：<strong>「我们要求提升必须同时满足三条：① 效应量超过预设容差；② 配对检验在多重比较校正后仍显著；③ 在 3 个种子上方向一致」</strong>。这三条互相独立地排除了三类假象（太小、随机、种子运气）。<em>面试里说出这句，比说任何一个具体的统计量都有说服力。</em>"),
    ])),

    ("gate", "回归门禁：旧场景不掉点是硬门槛", "".join([
        P("闭环的最后一道闸门是<span class=\"term\">regression gate</span>（回归门禁）：<strong>一个自动运行、输出 PASS/FAIL、且 FAIL 就不允许发布的判定器</strong>。它存在的意义不是「监控」，而是<strong>把「不掉点」这件事从人的自觉变成流程的强制</strong>——因为每一轮迭代都有交付压力，而「先合进去、回归下轮再修」在感知系统上是不可接受的。"),
        ASCII("""回归门禁的判定逻辑（每个切片独立跑，全部通过才 PASS）

  对每个切片 s:
    Δ_s = AP_new(s) - AP_base(s)
    p_s = paired_test(per_image_scores)         ← 配对检验，不是两组独立比
    ┌──────────────────────────────────────────────────────────────┐
    │  Δ_s >= -tol_s                     -> PASS  (在容差内)         │
    │  Δ_s <  -tol_s  且  p_s > α'       -> WARN  (掉了但不显著)      │
    │  Δ_s <  -tol_s  且  p_s <= α'      -> **FAIL**                │
    └──────────────────────────────────────────────────────────────┘
      α' = α / m   (Bonferroni, m = 切片数)   ← 不校正会天天误报

  容差 tol_s 的分层设置：
    安全关键切片 (stop / yield / 施工 / 限速下调)  tol = 0.000   ← **零容忍**
    常见场景切片 (day_clear_urban, night_urban)   tol = 0.005
    长尾/小样本切片 (snow, n<100)                 tol = 0.015   ← 噪声本来就大
    目标切片 (本轮要修的)                          不设下限，但要求 Δ > +预期收益

  额外的**全局**门禁（不分切片）：
    · FP/km 不得上升超过 5%          ← 工程指标，比 precision 更贴近体验
    · p99 端到端延迟不得上升          ← 模型换了可能变慢
    · 安全关键类的召回不得下降        ← 与 mAP 无关的独立约束""")
        ,
        TABLE(["门禁设计的选择", "宽松的后果", "严格的后果", "实践取法"], [
            ["<strong>容差 tol</strong>", "真回归被放过去", "噪声天天触发 FAIL，门禁被绕过", "<strong>按切片样本量与安全等级分层</strong>（见上图）"],
            ["<strong>显著性 α</strong>", "误报多", "真回归漏报", "门禁用 Bonferroni 校正后的 α；探索用 BH"],
            ["<strong>种子数</strong>", "结论不稳", "算力翻几倍", "关键发布 3 种子；日常迭代 1 种子 + 更大容差"],
            ["<strong>WARN 怎么处理</strong>", "WARN 变成没人看的噪音", "WARN 等同 FAIL，迭代停滞", "<strong>WARN 允许发布但强制建单跟踪</strong>，连续两轮 WARN 升级为 FAIL"],
        ]),
        DUAL(
            "门禁最大的敌人不是统计学，是<strong>人</strong>。一个天天误报的门禁，三周内就会演化出「加 <code>--skip-gate</code> 参数」的文化，然后它就等于不存在了。<em>所以门禁的第一设计目标是「误报率足够低，低到 FAIL 出现时所有人都相信它是真的」</em>——这比「不漏报」更重要。<strong>宁可容差设宽一点、只守住真正要命的几个切片，也不要建一个覆盖 50 个切片但天天红的门禁。</strong>",
            "第二个要提前想清楚的是<strong>门禁的可解释输出</strong>。FAIL 之后，工程师需要在几分钟内知道「哪个切片、掉了多少、置信区间多宽、有多少张图变差了、变差的是哪几张」。<em>一个只输出 FAIL 的门禁，会把定位成本推给下游，最终还是没人用</em>。所以门禁的产物应该是一份结构化报告：<strong>切片表 + 置信区间 + 变差样本的 top-20 列表 + 与上一版的 diff</strong>。<em>这份报告本身就是模块 04 里下一轮挖掘的输入</em>——闭环在这里真正闭上了。",
        ),
        CALLOUT("danger", "<p><strong>门禁必须跑在一个「不参与本轮挖掘」的评测集上。</strong>如果评测集也在按「当前模型最弱的场景」持续补充（模块 04 的缺口矩阵驱动），那么评测集会和训练集一起漂移，门禁就在<em>自己给自己出题</em>。</p><p>规范做法：维护<strong>两套评测集</strong>——① <strong>固定基准集</strong>（按部署真实分布随机采样，冻结，只在版本升级时整体替换，是回归门禁的唯一依据）；② <strong>失效模式集</strong>（每个失效模式一个小集合，随挖掘持续扩充，用来看目标场景有没有修好）。<em>把这两套混用，是数据闭环最常见的系统性错误。</em></p>", "门禁的尺子不能跟着被测物一起变"),
    ])),

    ("forgetting", "灾难性遗忘与新旧数据配比", "".join([
        P("上一节的门禁会 FAIL，最常见的原因不是新数据有问题，而是<strong>新数据太多了</strong>。加进 1200 张隧道场景，如果训练时对它们做了 10× 的重采样（因为「稀有类要加权」），那这一个场景就占了每个 batch 的相当比例，模型会以牺牲其他场景为代价去拟合它。"),
        H3("两种不同的机制，别混为一谈"),
        TABLE(["机制", "发生条件", "表现", "对策"], [
            ["<strong>数据饥饿（starvation）</strong>", "总训练量固定，新数据挤占了旧数据的采样份额", "旧场景 AP <em>缓慢</em>下降，且与被挤占的比例成正比", "<strong>加总训练量</strong>，或按饱和度分配采样权重"],
            ["<strong>灾难性遗忘（catastrophic forgetting）</strong>", "顺序训练 / 微调，只用新数据更新权重", "旧场景 AP <em>断崖式</em>下降（可以掉 10+ 点）", "<strong>混合重放（rehearsal）</strong>：新旧数据混在同一个 batch 里"],
            ["<strong>特征竞争</strong>", "新旧场景的最优特征互相冲突（如低光增强 vs 正常光）", "两边都不到位，容量不足的小模型尤其明显", "扩容 / 分支 / 场景条件化"],
        ]),
        P("<strong>最关键的一条实践结论：不要「拿新数据微调」，要「把新数据混进全量重训」。</strong> 前者省算力但会触发真正的灾难性遗忘（旧场景断崖下跌）；后者贵，但旧场景只会因为采样份额被稀释而<em>缓慢</em>下降，而且这个下降是可以用配比精确控制的。<em>在量产感知系统里，全量重训几乎总是默认选项——除非算力实在不允许，此时也必须做重放（rehearsal），即把旧数据的一个代表性子集混进微调。</em>"),
        H3("配比的最优点是内点，不是端点"),
        P("把新场景数据的比例记为 <code>p</code>（占每个 batch 的比例）。<strong>新场景 AP 随 <code>p</code> 单调上升但很快饱和；旧场景 AP 随 <code>p</code> 单调下降且加速下降</strong>。于是「在旧场景不掉超过 tol 的前提下最大化新场景 AP」这个约束优化问题，答案<strong>几乎总是一个内点</strong>——典型落在 10%–30%。"),
        MATH("p^{\\star} = \\arg\\max_{p\\in[0,1]} \\ \\mathrm{AP}_{\\text{new}}(p) \\quad \\text{s.t.} \\quad \\mathrm{AP}_{\\text{old}}(p) \\ \\ge\\ \\mathrm{AP}_{\\text{old}}(0) - \\text{tol}"),
        DUAL(
            "为什么「几乎总是内点」值得单独强调？因为两个端点都对应着一种常见的错误直觉：<strong><code>p</code> 很小（比如按自然分布，隧道场景占 1.5%）= 「加了数据但没效果」的头号原因</strong>；<strong><code>p</code> = 1（只用新数据微调）= 灾难性遗忘</strong>。<em>而中间那一段有一个明确的最优点，它由「新场景的饱和速度」和「旧场景的容差」共同决定，是可以算出来的，不需要猜。</em>",
            "工程上实现配比有三种粒度，效果和代价递增：① <strong>重复采样（oversampling）</strong>——把新数据在采样列表里重复 k 次，最简单，但会加剧对这几百张图的过拟合；② <strong>加权采样器（weighted sampler）</strong>——按场景标签给采样概率，等价于连续可调的 <code>p</code>，<em>是推荐做法</em>；③ <strong>损失加权</strong>——不改采样，改 loss 权重，梯度效果类似但对 BN 统计量的影响不同（<em>BN 看到的仍是原分布</em>，这个细微差别在小模型上有时会显现）。<strong>面试里能说清「重采样和损失加权不完全等价，差别在 BN 与数据增强的暴露次数」，是一个不错的加分点。</strong>",
        ),
        CALLOUT("warn", "别忘了<strong>评测集的配比不能跟着训练集动</strong>。有人在调 <code>p</code> 的同时，也把评测集里目标场景的比例调高了「以便看得更清楚」——于是整体 mAP 的含义变了，与历史版本不可比。<em>训练分布可以随便调，评测分布必须冻结</em>。要「看得更清楚」就去看切片 AP，而不是改评测集的构成。"),
    ])),

    ("marginal", "边际收益曲线：还值不值得继续标", "".join([
        P("这是本模块、也可以说是整门课最有实用价值的一个工具。问题非常具体：<strong>隧道场景已经标了 1200 张，AP 从 0.34 涨到 0.68。要不要再标 2000 张？</strong>「再标标看」不是答案，「标到 AP 0.85 为止」也不是答案——<em>因为你并不知道 0.85 是否可达</em>。"),
        H3("把 AP 对数据量的关系拟合成一条饱和曲线"),
        P("在同一场景内，AP 随该场景训练样本数 <code>n</code> 的增长，经验上非常接近一条<strong>指数饱和曲线</strong>（也有用幂律的，工程上两者都够用，指数式的参数更好解释）："),
        MATH("\\mathrm{AP}(n) = A_\\infty - (A_\\infty - A_0)\\,e^{-n/\\tau}"),
        P("三个参数各有明确的工程含义，<strong>这才是这个模型真正的价值</strong>："),
        TABLE(["参数", "含义", "它回答什么问题"], [
            ["<strong><code>A∞</code>（渐近线）</strong>", "数据加到无穷时这个场景能达到的 AP", "<strong>「继续标数据的天花板在哪」</strong>——这是最重要的一个数"],
            ["<code>τ</code>（时间常数）", "每积累 τ 张样本，与天花板的差距衰减到 1/e", "「还要多久才能接近饱和」"],
            ["<code>A₀</code>", "零样本（只靠其他场景泛化）时的 AP", "「这个场景的迁移基线有多高」"],
        ]),
        ASCII("""边际收益曲线：三个决策区间

  AP
  0.85 ┤                                        目标线（产品要求）
       │╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
  0.79 ┤                        ┄┄┄┄┄┄┄┄┄┄  A∞ = 0.79  **天花板**
       │                 ●━━━━━━━━━━━━━━━━━━━━━━━
  0.70 ┤          ●━━━━━━
       │     ●━━━━
  0.60 ┤  ●━━
       │ ●
  0.50 ┤●
       └─┬─────┬─────┬─────┬─────┬─────┬─────┬────► n（该场景样本数）
         0    1k    2k    3k    4k    5k    6k

   ├─── 陡峭区 ───┤├─ 递减区 ─┤├──── 饱和区 ────┤
    每 1k 张 +8AP   每 1k +2AP   每 1k +0.3AP
    **继续标**      **算成本**    **停止标注，改方法**

  关键判读：目标线 0.85 **在 A∞ 之上** ->
     再标 10 万张也到不了 0.85。此时继续标注是纯浪费，
     必须换手段：改架构 / 加分辨率 / 换传感器 / 拆成两级 / 重新定义任务。""")
        ,
        H3("三个可以直接拿去用的决策规则"),
        P("有了拟合的 <code>(A∞, τ, A₀)</code>，下面三个量都是闭式的："),
        MATH("\\Delta_{\\text{next}}(n, B) = \\big(A_\\infty - \\mathrm{AP}(n)\\big)\\left(1 - e^{-B/\\tau}\\right), \\qquad n^{\\star}(\\text{target}) = -\\tau \\ln\\!\\frac{A_\\infty - \\text{target}}{A_\\infty - A_0}"),
        OL([
            "<strong>下一批还能涨多少</strong>：<code>Δ_next(n, B)</code>。这直接给出「再标 B 张的预期收益」，可以和成本对比：<em>每提升 1 个 AP 点要花多少钱</em>。",
            "<strong>达到目标要标多少</strong>：<code>n*(target)</code>。如果 <code>target ≥ A∞</code>，公式返回无穷——<strong>这就是「不可达」的数学表达</strong>，也是最有价值的一个输出。",
            "<strong>什么时候停</strong>：当「每千张样本的预期 AP 提升」低于阈值（例如 0.3 点/千张），或者「每 AP 点的成本」超过预算上限时，停止标注。<em>把这条写成自动判据，就不会有人凭感觉说「再标点吧」。</em>",
        ]),
        DUAL(
            "<strong>这条曲线最大的作用是把「还标不标」从一个立场之争变成一个算术题。</strong> 数据团队说「再标」、算法团队说「该改模型」，两边其实在争论同一个未知数 <code>A∞</code>。<em>拟合出来一看：A∞ = 0.79，产品目标 0.85，那就没什么可争的了——继续标注不可能达标，讨论应该立刻转向「换什么方法」。</em>反过来，如果 A∞ = 0.88 而当前 0.68，那就闭嘴接着标。",
            "拟合本身有几个必须注意的地方。<strong>① 至少要 4–5 个数据点，且要横跨一个数量级</strong>（比如 200 / 500 / 1200 / 3000 张），只有两个点拟合不出饱和形状。<em>这意味着标注必须分批进行、每批都重训并评测——「一次标 5000 张」不但风险高，还让你永远拿不到这条曲线。</em>② <strong>每个点的 AP 本身带噪声</strong>（种子 + 评测抽样），所以要给拟合出的 <code>A∞</code> 一个置信区间，用区间下界做决策更稳。③ <strong>曲线只在「其他条件不变」时成立</strong>——中途换了 backbone 或改了增强，曲线就得重拟。",
        ),
        CALLOUT("intuition", "把这一节压成面试答案：<strong>「我们对每个重点场景维护一条边际收益曲线。标注分批做，每批重训后测该切片 AP，拟合 <code>AP(n) = A∞ − (A∞ − A₀)e^{−n/τ}</code>。用 <code>A∞</code> 判断天花板是否够得着目标，用 <code>ΔAP/千张</code> 与标注单价换算出「每个 AP 点多少钱」，低于阈值就停止标注、转向方法改进。」</strong> <em>这段话同时体现了三件事：数据决策是量化的、你知道数据不是万能的、你会算成本。</em>"),
    ])),

    ("shadow", "影子评测与 A/B：离线指标之外的最后一道关", "".join([
        P("离线指标全绿了，就能上车吗？<strong>不能</strong>。离线评测集是历史数据的一个快照，而车上跑的是<em>此刻的、连续的、有时序的、经过完整软件栈的</em>真实世界。这两者之间有一条系统性的鸿沟，需要两种额外的验证方式来跨越。"),
        TABLE(["验证方式", "怎么做", "能发现什么", "代价 / 局限"], [
            ["<strong>离线切片评测</strong>", "历史数据 + 标注", "精度类问题、回归", "<em>看不到时序稳定性、看不到与下游的交互</em>"],
            ["<strong>影子模式（shadow mode）</strong>", "新模型在车上<strong>与旧模型并行推理，但输出不接管控制</strong>，只记录分歧", "<strong>真实分布下的差异、分歧场景、算力与延迟的真实表现</strong>", "占额外算力；<em>只能看到分歧，没有真值</em>"],
            ["<strong>回灌 / 重放（replay）</strong>", "用录制的原始传感器流重跑完整软件栈", "端到端一致性、时序行为、与跟踪/融合的交互", "需要完整的回放基础设施"],
            ["<strong>灰度 A/B</strong>", "小比例车辆用新模型，对比业务指标", "<strong>接管率、误报投诉、真实体验</strong>", "<em>周期长、样本量要求高、有安全风险</em>"],
        ]),
        H3("影子模式为什么是数据闭环的枢纽"),
        P("影子模式常被当成「上车前的最后一道保险」，但它更大的价值在别处：<strong>它是一个高质量的触发器</strong>。新旧模型的<em>分歧</em>本身就是极好的挖掘信号——<strong>两个模型意见不一致的地方，几乎必然是难例、边界样本、或标注规范有歧义的地方</strong>。这些帧回传去标，就是下一轮的高价值数据。<em>于是「验证」和「挖掘」在这里合成了同一个动作</em>（这也呼应模块 03 讲的一致性触发）。"),
        DUAL(
            "<strong>影子模式的核心限制必须说清楚：它没有真值。</strong> 你只知道「新模型说有牌、旧模型说没有」，不知道谁对。<em>所以影子模式的输出永远是「分歧率」和「分歧样本」，不是「新模型更好」</em>。要把分歧变成结论，必须再走一次人工标注（抽样即可）。<strong>把「分歧率下降」当成「模型变好」是一个典型的误读</strong>——分歧率下降也可能是新模型变得更像旧模型了。",
            "A/B 测试在自动驾驶上有两个和互联网产品完全不同的约束。<strong>① 指标极度稀疏</strong>：接管、误刹这类事件的发生率可能是 10⁻⁵/km 量级，<em>要检出 10% 的相对变化需要天文数字的里程</em>——所以实践中会用代理指标（perception-level 的误报率、规控的介入次数）而不是最终安全指标。<strong>② 有真实安全风险</strong>：不能像做推荐系统那样「先上 5% 流量看看」。<em>所以行业标准路径是「影子 → 内部车队 → 有限 ODD 灰度 → 全量」的分阶段放开</em>，每一阶段都有独立的退出准则与回滚预案。",
        ),
        CALLOUT("warn", "一个反复出现的现象：<strong>离线指标涨了，路测体验反而变差</strong>。最常见的三个原因是——① <em>离线评测是逐帧的、路测体验是时序的</em>（模型变「敏感」了，AP 涨但检测框闪烁，下游状态机反复跳变）；② <em>离线用 mAP、体验取决于某个工作点的 FP 率</em>（PR 曲线整体右移，但你实际用的那个 score 阈值处反而变差）；③ <em>评测集与真实分布脱节</em>。<strong>对策：评测里必须包含时序稳定性指标（闪烁率、首检距离）与固定工作点的 FP/km——这两个是 C55 模块 05 的重点。</strong>"),
    ])),

    ("pipeline", "把闭环做成流水线：产物、门禁与周期时间", "".join([
        P("前面所有环节，如果靠人工串联，实际会变成「工程师 A 挖数据 → 邮件给标注 → 三周后收到 → 工程师 B 训练 → 忘了跑切片评测 → 合入」。<strong>闭环的价值不在于每个环节多聪明，而在于它是否真的能一圈一圈自动转起来</strong>。所以最后一步是把它做成一条有明确产物与门禁的流水线。"),
        ASCII("""数据闭环流水线：每一步的**产物**与**门禁条件**

  阶段            产物 (artifact)                     门禁 (gate)                典型耗时
  ─────────────────────────────────────────────────────────────────────────────────
  ① 触发       badcase ticket + seed frames        必须有 ticket & 失效模式分类     0.5 天
      │        （来自路测/影子分歧/规则触发）          否则不予排期
      ▼
  ② 挖掘       candidate_set (10^4)                 检索 precision@k >= 3x 随机     1 天
      │        + mining_job.yaml（可复现）           索引与嵌入版本匹配
      ▼
  ③ 精选       label_task (10^3)                    去重后重复率 <= 3%              0.5 天
      │        含 core-set / 分层配额参数            与评测集**交集必须为空**
      ▼
  ④ 标注       batch_YYYYwWW (带 QC 报告)           QC 通过率 >= 0.92              **7~14 天** ◄ 瓶颈
      │        + 血缘记录                            标注一致性 kappa >= 0.7
      ▼
  ⑤ 训练       model_rNN + dataset_vX.Y.Z           训练 loss 收敛；配比 p 已记录     2~3 天
      │        （配比 p 作为超参显式记录）
      ▼
  ⑥ 评测       切片报告 + 置信区间 + 变差样本 top-20   评测集与训练集无泄漏             0.5 天
      │
      ▼
  ⑦ 门禁       PASS / WARN / FAIL + 结构化原因       **回归门禁**（第 4 节）          0.2 天
      │                                             FAIL -> 退回 ③ 或 ⑤（调配比）
      ▼
  ⑧ 发布       影子 -> 灰度 -> 全量                   影子分歧率 & 灰度指标达标        3~7 天
      │
      └─────► ⑥ 的「变差样本」与 ⑧ 的「影子分歧」**回流成 ① 的新 ticket**
              —— 这条回边才是「闭环」这个词的真正含义""")
        ,
        H3("闭环的核心度量：周期时间（cycle time）"),
        P("<strong>闭环系统真正该被优化的指标，不是任何一个模型指标，而是「从发现问题到修复上线」的天数</strong>。因为长尾问题是源源不断的——你永远不可能一次修完，能决定竞争力的是<em>转一圈要多久</em>。"),
        TABLE(["度量", "定义", "典型值", "为什么关注它"], [
            ["<strong>cycle time (p50 / p90)</strong>", "ticket 创建 → 修复版本上线", "<strong>3–8 周</strong>", "<em>看 p90 而不是均值</em>：偶发的长尾拖延才是痛点"],
            ["<strong>瓶颈阶段占比</strong>", "各阶段耗时 / 总周期", "标注通常占 40–60%", "<strong>优化非瓶颈阶段的收益接近零</strong>"],
            ["<strong>返工率</strong>", "门禁 FAIL 导致回退的比例", "20–40%", "每次返工把周期时间乘以一个系数——<em>提高一次通过率的杠杆极大</em>"],
            ["<strong>ticket 消化率</strong>", "每轮关闭 ticket 数 / 新增数", "&gt; 1 才是在收敛", "&lt; 1 说明长尾问题在积压，闭环转速不够"],
        ]),
        DUAL(
            "<strong>「返工率」这一行值得特别注意，因为它的影响是乘性的而不是加性的。</strong> 假设一轮 25 天、门禁通过率 60%，那么期望轮数是 1/0.6 ≈ 1.67 轮 → 期望周期 ≈ 42 天。<em>把通过率从 60% 提到 85%，期望周期直接降到 29 天——效果比把标注速度提升 30% 还大，而且便宜得多</em>。<strong>提高一次通过率的手段很具体：在训练前就先跑一遍「配比预演」、在标注前先小批量试标验证规范、在门禁前先跑轻量的自检。</strong>",
            "另一个反直觉但重要的点：<strong>缩短周期时间往往要靠「减少每轮的雄心」，而不是靠加速每个环节</strong>。一轮同时修 5 个失效模式，任何一个出问题整轮都卡住，且归因困难（到底是哪批数据导致夜间回归？）。<em>拆成 5 个独立的小轮次，每轮只改一件事，周期更短、归因更清晰、返工代价更低</em>。<strong>这与软件工程里「小批量、快反馈」的结论完全一致，而且在数据闭环上更成立——因为数据的因果归因比代码难得多。</strong>",
        ),
        CALLOUT("intuition", "把整个 C58 压成一句：<strong>「模型架构会趋同，数据飞轮不会。而数据飞轮的竞争力不在于你挖到了多好的数据，在于你转得有多快、每一圈都真的证明了自己有用。」</strong> <em>面试里被问「你怎么看数据闭环」，从「周期时间」和「一次通过率」切入，比罗列一堆挖掘算法更有说服力——因为前者说明你理解这是一个系统工程问题。</em>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("闭环验证是工程与统计的交界地带，也正因为如此，它有一批既没有理论答案也没有工程共识的问题。"),
        UL([
            "<strong>数据缩放律在检测与长尾上的形式</strong>。语言模型的 scaling law 已经很成熟，但「某个<em>子分布</em>的性能随该子分布样本数如何增长」缺少同等严谨的刻画。<em>本模块用的指数饱和曲线是经验拟合，幂律形式（<code>AP ≈ A∞ − c·n^{−α}</code>）在有些场景拟合得更好</em>——两者对「天花板」的外推差别很大，而外推恰恰是我们要用它做的事。<strong>「用几个点外推 A∞ 的置信区间」目前没有好方法。</strong>",
            "<strong>数据贡献的因果估计</strong>。「这 1200 张让 AP 涨了多少」严格说是一个反事实问题，现在的答案靠「训两次做对比」，成本极高且被种子噪声污染。<em>influence functions、datamodels、data Shapley 试图给出更便宜的估计</em>，但在检测任务、非凸优化、千万级数据上仍不实用。",
            "<strong>持续学习的评测标准</strong>。灾难性遗忘的度量（backward transfer、forgetting measure）来自持续学习文献，但工业场景是「全量重训 + 配比」，与学术设定（严格顺序、不能回看旧数据）不同。<em>「工业配比式持续更新」缺少标准的评测协议与基准</em>，导致各家的「不遗忘」都是自己定义的。",
            "<strong>离线-在线指标的鸿沟</strong>。为什么离线 mAP 涨了路测体验会变差，目前的解释是零散的（时序稳定性、工作点、分布脱节）。<em>「什么样的离线指标能可靠预测在线体验」是一个开放问题</em>，也是自动驾驶评测领域最有价值的研究方向之一。相邻领域（推荐系统的离线-在线一致性）有一些可借鉴的方法论，但迁移得并不好。",
            "<strong>门禁的自动化与自适应</strong>。容差与显著性阈值目前都是手工设定的常数。<em>能否根据历史波动自动标定每个切片的容差、能否用序贯检验（sequential testing）在样本积累过程中动态决策</em>，是一个明确可做但少有系统工作的方向。序贯分析（always-valid p-values、e-values）在 A/B 领域已有成熟工具，尚未系统进入感知闭环。",
            "<strong>合成数据与真实数据的等价性度量</strong>。如果一张合成的雪夜施工牌能顶 0.3 张真实数据，边际收益曲线该怎么算？<em>「合成数据的有效样本数」缺少可操作的定义</em>，而这直接影响标注预算该不该花。",
            "<strong>闭环的长期稳定性</strong>。每一轮都按「当前最弱场景」补数据，长期迭代后训练分布会持续偏离真实分布。<em>这个反馈系统会收敛、震荡、还是发散？</em>目前只有工程上的经验对冲（固定比例随机采样、冻结基准集），缺少理论刻画。<strong>这可能是数据闭环里最深、也最少被讨论的问题。</strong>",
        ]),
        CALLOUT("paper", "必读：Benjamini &amp; Hochberg, <em>Controlling the False Discovery Rate</em>（1995，BH 校正原文，本模块多重比较一节的基础）；Efron &amp; Tibshirani, <em>An Introduction to the Bootstrap</em>（置信区间与配对重采样）；Hoiem et al., <em>Diagnosing Error in Object Detectors</em> 与 Bolya et al., <em>TIDE: A General Toolbox for Identifying Object Detection Errors</em>（切片与误差分解，C61 模块 02 会深入）；Kirkpatrick et al., <em>Overcoming catastrophic forgetting in neural networks</em>（EWC）与 Lopez-Paz &amp; Ranzato, <em>GEM</em>（遗忘度量与重放）；Hestness et al., <em>Deep Learning Scaling is Predictable, Empirically</em>（数据缩放律的经验形式）；Mahajan et al., <em>Exploring the Limits of Weakly Supervised Pretraining</em>（大规模数据的边际收益递减实证）；Kohavi et al., <em>Trustworthy Online Controlled Experiments</em>（A/B 实践中的陷阱，稀疏指标一节尤其相关）；Johari et al., <em>Always Valid Inference</em>（序贯检验）。相邻课程：C55 模块 05（安全导向评测与分桶）、C61 模块 01–02（实验设计与误差分析）、C58 模块 03–04（触发与挖掘）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 闭环验证：证明数据真的有用（切片评测 / 显著性 / 回归门禁 / 配比 / **边际收益曲线** / 周期时间）

目标：把「加了 1200 张隧道口施工牌，模型变好了吗」这个问题，变成一套**可以自动跑、
会输出 PASS/FAIL、并且能告诉你还该不该继续标**的流程。

路线：合成评测集与「配比 → 分场景 AP」模拟器 → **切片评测**（平均值怎么骗人）→
配对检验 vs 非配对 + bootstrap → **多重比较**（20 个切片必然出假阳性）→
**回归门禁** → 数据配比扫描找 p\\* → **边际收益曲线拟合与停标决策** → 闭环周期时间 →
✏️ 练习（功效分析 / BH 校正 / 停标规则 / 周期时间分解）→ 📖 答案 → 🧪 工程胶囊。

本 notebook 你会亲手实现：
- 一个「训练配比 → 各切片 AP」的模拟器（含**重复采样的信息上限**）
- 逐图配对检验（正态近似）与 bootstrap 置信区间，量化**配对能省多少样本量**
- 多重比较的家族错误率仿真：20 个切片、无真实差异时，**64% 的实验会「发现」假回归**
- 带容差分层 + Bonferroni 校正的**回归门禁**，输出 PASS / WARN / FAIL 与原因
- 新旧数据配比 p 的约束优化，找出可行域与 p\\*
- **边际收益曲线** `AP(n) = A∞ − (A∞ − A₀)e^{−n/τ}` 的拟合、A∞ 的置信区间、
  「再标 B 张能涨多少 / 每个 AP 点多少钱 / 目标可不可达」
- 闭环流水线的周期时间仿真：p50/p90、瓶颈定位、**一次通过率的乘性杠杆**

> 心智模型：**整体 mAP 是加权平均，而加权平均就是用来掩盖长尾的。
> 闭环验证要做的，是把这个平均值拆回它掩盖掉的那些东西。**"""),

    md("""## 1 · 合成评测集与「配比 → 分场景 AP」模拟器

模拟器的规则（**简化但方向正确**，先说清楚再用）：

1. 每个切片的 AP 由它在训练中的**有效样本量** `e` 决定：`AP = A∞ − (A∞ − A₀)·exp(−e/τ)`；
2. 训练的总曝光预算 `T` 固定（算力有限），各切片按采样配比瓜分；
3. **重复采样有上限**：把同 2100 张图重复 20 遍不会产生 20 倍的信息，
   所以 `e = min(唯一样本数 × REPEAT_CAP, 该切片的曝光量)`。第 3 条会带来一个很有意思的结论。"""),
    code("""import numpy as np, math, collections, json
rng = np.random.default_rng(2026)

# 切片定义：n_eval 评测图数 / n_tr 当前训练样本数 / 饱和曲线三参数 / 门禁容差 / 是否安全关键
SLICES = {
    'day_clear_urban': dict(n_eval=520, n_tr=42000, a_inf=0.90, tau=5000, a0=0.20, tol=0.005, crit=False),
    'night_urban':     dict(n_eval=260, n_tr=16000, a_inf=0.84, tau=2600, a0=0.15, tol=0.005, crit=False),
    'rain_highway':    dict(n_eval=150, n_tr=9000,  a_inf=0.83, tau=1800, a0=0.15, tol=0.005, crit=False),
    'dusk_ramp':       dict(n_eval=110, n_tr=7000,  a_inf=0.81, tau=1600, a0=0.15, tol=0.005, crit=False),
    'fog_tunnel':      dict(n_eval=95,  n_tr=900,   a_inf=0.78, tau=2500, a0=0.30, tol=0.005, crit=True),
    'snow_any':        dict(n_eval=60,  n_tr=3000,  a_inf=0.76, tau=900,  a0=0.15, tol=0.015, crit=False),
}
TARGET = 'fog_tunnel'          # ← 本轮要修的失效场景：雾天隧道口的施工牌（模块 04 挖来的）
NEW_LABELS = 1200              # 新标注的样本数
REPEAT_CAP = 4                 # 同一张图重复超过 4 遍，基本不再带来新信息
T_TOTAL = sum(v['n_tr'] for v in SLICES.values())

def ap_curve(n, a_inf, tau, a0):
    return a_inf - (a_inf - a0) * np.exp(-np.asarray(n, float) / tau)

def effective_n(p):
    '''p = 目标切片在训练采样中的配比；其余切片按原比例瓜分 (1-p)。'''
    base_share = {s: v['n_tr'] / T_TOTAL for s, v in SLICES.items()}
    others = 1 - base_share[TARGET]
    out = {}
    for s, v in SLICES.items():
        if s == TARGET:
            out[s] = min((v['n_tr'] + NEW_LABELS) * REPEAT_CAP, p * T_TOTAL)   # ← 信息上限
        else:
            out[s] = base_share[s] * (1 - p) / others * T_TOTAL
    return out

def model_ap(p=None):
    '''p=None 表示 baseline（没加新数据）。'''
    if p is None:
        return {s: float(ap_curve(v['n_tr'], v['a_inf'], v['tau'], v['a0'])) for s, v in SLICES.items()}
    e = effective_n(p)
    return {s: float(ap_curve(e[s], v['a_inf'], v['tau'], v['a0'])) for s, v in SLICES.items()}

ap_base = model_ap(None)
print(f'总曝光预算 T = {T_TOTAL}，目标切片 {TARGET} 当前只有 {SLICES[TARGET]["n_tr"]} 张训练样本\\n')
print(f'{"切片":<18s} {"评测图":>7s} {"训练样本":>9s} {"baseline AP":>12s}')
for s, v in SLICES.items():
    star = '  ← 目标切片（惨不忍睹）' if s == TARGET else ''
    print(f'{s:<18s} {v["n_eval"]:>7d} {v["n_tr"]:>9d} {ap_base[s]:>12.4f}{star}')
assert ap_base[TARGET] < 0.5 and ap_base['day_clear_urban'] > 0.88
print('\\n✅ 典型的长尾格局：常见场景已经深度饱和，目标场景连 0.5 都不到。')"""),

    md("""## 2 · 分场景切片评测：整体 mAP 是用来骗人的

先造两个候选模型：
- **候选 A**：把新数据配比拉到 `p = 0.30`（「稀有场景要加权」的朴素做法）；
- **候选 B**：`p = 0.08`（第 6 节会算出这个数字怎么来的）。

评测用**逐图分数**（可以理解为每张图的检测质量），baseline 与新模型在**同一批图**上评测，
共享「图像固有难度」——这一点在第 3 节做配对检验时至关重要。"""),
    code("""DIFF = {s: rng.normal(0, 0.10, v['n_eval']) for s, v in SLICES.items()}   # 图像固有难度（两模型共享）

def make_scores(apd, seed):
    r = np.random.default_rng(seed)
    return {s: np.clip(apd[s] + DIFF[s] + r.normal(0, 0.03, SLICES[s]['n_eval']), 0, 1) for s in SLICES}

S_base = make_scores(ap_base, 11)
S_A    = make_scores(model_ap(0.30), 12)      # 激进配比
S_B    = make_scores(model_ap(0.08), 13)      # 保守配比

def overall_map(S):
    return float(np.concatenate([S[s] for s in SLICES]).mean())   # 按图数加权 = 整体 mAP

print(f'整体 mAP:  baseline {overall_map(S_base):.4f}  ->  候选A {overall_map(S_A):.4f} '
      f'({100 * (overall_map(S_A) - overall_map(S_base)):+.2f} 点)')
print('「涨了 1.7 点，合入！」—— 现在把它拆开看：\\n')
print(f'{"切片":<18s} {"n_eval":>7s} {"baseline":>9s} {"候选A":>9s} {"Δ(点)":>8s} {"权重":>7s}')
n_all = sum(v['n_eval'] for v in SLICES.values())
for s, v in SLICES.items():
    d = (S_A[s].mean() - S_base[s].mean()) * 100
    flag = '  ◄── **回归**' if d < -0.4 else ('  ◄── 目标切片' if s == TARGET else '')
    print(f'{s:<18s} {v["n_eval"]:>7d} {S_base[s].mean():>9.4f} {S_A[s].mean():>9.4f} '
          f'{d:>+8.2f} {v["n_eval"] / n_all:>7.1%}{flag}')

n_reg = sum(1 for s in SLICES if (S_A[s].mean() - S_base[s].mean()) * 100 < -0.4)
assert overall_map(S_A) > overall_map(S_base), '整体是涨的'
assert n_reg >= 3, '同时有多个切片在回归'
print(f'\\n⚠️  整体 +{100 * (overall_map(S_A) - overall_map(S_base)):.2f} 点的背后，'
      f'是 **{n_reg} 个切片在回归**，其中一个是占 22% 权重的常见场景。')
print('    目标切片 +32 点乘以 8% 的权重 = +2.6 点的贡献，恰好把几个回归的坑填平了。')
print('✅ **整体 mAP 是按样本数加权的平均，而加权平均就是用来掩盖长尾的。**')
print('   报告模板必须把「预期收益切片」和「回归哨兵切片」物理分成两块，回归块放前面。')"""),

    md("""## 3 · 配对检验：免费拿回一个数量级的统计功效

baseline 与新模型在**同一批图**上评测 → 误差高度相关。
对每张图算差值 `d_i = s_new,i − s_base,i` 再做统计，
「图像固有难度」这一大块方差被直接抵消掉。"""),
    code("""def norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

def norm_ppf(q, lo=-12.0, hi=12.0):
    for _ in range(200):                       # 二分求逆（不用 scipy）
        m = (lo + hi) / 2
        if norm_cdf(m) < q: lo = m
        else:               hi = m
    return (lo + hi) / 2

def paired_test(d):
    '''配对检验：对逐图差值做单样本 z 检验（n 大时正态近似足够）。'''
    d = np.asarray(d, float); n = len(d)
    mean, sd = float(d.mean()), float(d.std(ddof=1))
    se = sd / math.sqrt(n) if sd > 0 else 1e-12
    z = mean / se
    return dict(mean=mean, sd=sd, se=se, z=z, p=2 * (1 - norm_cdf(abs(z))), n=n)

def unpaired_test(a, b):
    '''非配对：把两组当成独立样本 —— 图像固有难度被算进了噪声。'''
    a, b = np.asarray(a, float), np.asarray(b, float)
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = (b.mean() - a.mean()) / se
    return dict(mean=float(b.mean() - a.mean()), se=se, z=z, p=2 * (1 - norm_cdf(abs(z))))

s = 'night_urban'
pt = paired_test(S_A[s] - S_base[s])
ut = unpaired_test(S_base[s], S_A[s])
print(f'切片 {s}（n={pt["n"]}），同一个 Δ = {pt["mean"] * 100:+.2f} 点：')
print(f'  配对检验     SE={pt["se"]:.5f}  z={pt["z"]:+.2f}  p={pt["p"]:.4f}')
print(f'  非配对检验   SE={ut["se"]:.5f}  z={ut["z"]:+.2f}  p={ut["p"]:.4f}')
print(f'  -> 配对把标准误缩小了 {ut["se"] / pt["se"]:.1f}×，等价于样本量放大 {(ut["se"] / pt["se"]) ** 2:.0f}×')
assert pt['se'] < ut['se'] / 2 and pt['p'] < ut['p']
print('\\n⚠️  非配对检验说「p=0.46，不显著」—— 但那是**错的结论**：')
print('    它把「有些图天生就难」也算进了噪声。评测集是固定的，那部分方差本该被消掉。')
print('✅ 只要两个模型评的是同一批图，就**必须**用配对统计。这是零成本的功效提升。')"""),

    code("""def bootstrap_ci(d, B=4000, alpha=0.05, seed=0):
    '''对图像重采样，给出 Δ 的置信区间（不依赖正态假设）。'''
    d = np.asarray(d, float); r = np.random.default_rng(seed); n = len(d)
    means = np.array([d[r.integers(0, n, n)].mean() for _ in range(B)])
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))

print(f'{"切片":<18s} {"Δ(点)":>8s} {"95% CI(点)":>20s} {"p(配对)":>10s} {"结论"}')
for s in SLICES:
    d = S_A[s] - S_base[s]
    lo, hi = bootstrap_ci(d, seed=hash(s) % 9999)
    t = paired_test(d)
    concl = '显著变化' if hi < 0 or lo > 0 else '落在噪声带内'
    print(f'{s:<18s} {t["mean"] * 100:>+8.2f} [{lo * 100:>+7.2f}, {hi * 100:>+7.2f}] '
          f'{t["p"]:>10.2e} {concl}')

d_day = S_A['day_clear_urban'] - S_base['day_clear_urban']
lo, hi = bootstrap_ci(d_day, seed=1)
assert lo < 0 < hi, 'day_clear_urban 的变化应落在噪声带内（区间跨 0）'
print('\\n✅ 置信区间比「p 值 + 一句显著/不显著」信息量大得多：')
print('   它同时告诉你**方向、幅度、以及不确定性**。周报里只写 Δ 不写 CI 是不合格的。')
print('⚠️  这里的 CI 只覆盖了**评测集抽样噪声**。训练种子的噪声（检测任务典型 ±0.2~0.5 点）')
print('    必须靠真的重训 3~5 次才能量化 —— 这是行业里最普遍的方法论债务。')"""),

    md("""## 4 · 多重比较：切片一多，假阳性是必然的

假设新模型**完全没有变化**。20 个切片、α=0.05 时，
至少出现一个「显著」的概率是 `1 − 0.95²⁰ ≈ 64%`。
也就是说：只要切片够多，每次实验都能「发现」一个回归——**而它是假的**。"""),
    code("""def fwer_sim(m=20, n=150, trials=300, alpha=0.05, seed=5):
    '''仿真：m 个切片、真实差异全为 0，看「至少一个假阳性」的概率。'''
    r = np.random.default_rng(seed)
    raw = bonf = 0
    for _ in range(trials):
        ps = np.array([paired_test(r.normal(0, 0.042, n))['p'] for _ in range(m)])
        raw  += int((ps < alpha).any())
        bonf += int((ps < alpha / m).any())
    return raw / trials, bonf / trials

print(f'{"切片数 m":>8s} {"理论 FWER":>11s} {"仿真 不校正":>13s} {"仿真 Bonferroni":>16s}')
for m in [1, 5, 20]:
    f_raw, f_bonf = fwer_sim(m=m, trials=250, seed=5 + m)
    print(f'{m:>8d} {1 - 0.95 ** m:>11.1%} {f_raw:>13.1%} {f_bonf:>16.1%}')

f_raw20, f_bonf20 = fwer_sim(m=20, trials=300, seed=25)
assert f_raw20 > 0.4, '不校正时假阳性率应该很高'
assert f_bonf20 < 0.15, 'Bonferroni 应把家族错误率压回 α 附近'
print('\\n⚠️  **「我们切了 20 个维度，发现夜间场景显著回归了」—— 这句话在统计上什么也没说。**')
print('✅ 两条对策，用途不同：')
print('   · Bonferroni（阈值除以 m）控制 FWER —— **回归门禁用它**，宁可漏报也别乱报警。')
print('   · Benjamini-Hochberg 控制 FDR —— 探索性分析用它（练习 2 会实现）。')
print('   · 最有效的其实是**预注册**：跑实验前先声明主指标与哨兵切片，事后翻表才需要校正。')"""),

    md("""## 5 · 回归门禁：把「不掉点」从自觉变成强制

判定逻辑（每个切片独立跑）：

| 条件 | 判定 |
|---|---|
| `Δ ≥ −tol` | PASS（在容差内） |
| `Δ < −tol` 且 `p > α/m` | WARN（掉了但不显著） |
| `Δ < −tol` 且 `p ≤ α/m` | **FAIL** |

容差按切片分层：安全关键切片 `tol = 0`，常见切片 `0.005`，小样本切片 `0.015`。"""),
    code("""def regression_gate(S_base, S_new, alpha=0.05, verbose=True):
    m = len(SLICES)
    rows = []
    for s, v in SLICES.items():
        t = paired_test(S_new[s] - S_base[s])
        tol = 0.0 if v['crit'] else v['tol']
        if   t['mean'] >= -tol:        verdict = 'PASS'
        elif t['p'] > alpha / m:       verdict = 'WARN'
        else:                          verdict = 'FAIL'
        rows.append(dict(slice=s, delta=t['mean'], p=t['p'], tol=tol,
                         n=t['n'], verdict=verdict))
    overall = ('FAIL' if any(r['verdict'] == 'FAIL' for r in rows) else
               'WARN' if any(r['verdict'] == 'WARN' for r in rows) else 'PASS')
    if verbose:
        print(f'{"切片":<18s} {"Δ(点)":>8s} {"容差(点)":>9s} {"p":>10s} {"判定":>6s}')
        for r in sorted(rows, key=lambda r: r['delta']):
            print(f'{r["slice"]:<18s} {r["delta"] * 100:>+8.2f} {r["tol"] * 100:>9.1f} '
                  f'{r["p"]:>10.2e} {r["verdict"]:>6s}')
        print(f'  -> 总判定 **{overall}**   (Bonferroni α\\' = {alpha / m:.4f})')
    return rows, overall

print('== 候选 A（p = 0.30，激进配比）==')
rows_A, ver_A = regression_gate(S_base, S_A)
assert ver_A == 'FAIL'
n_fail = sum(1 for r in rows_A if r['verdict'] == 'FAIL')
n_warn = sum(1 for r in rows_A if r['verdict'] == 'WARN')
print(f'\\n❌ 整体 mAP 涨 1.8 点的候选 A 被门禁拦下：{n_fail} 个切片 FAIL、{n_warn} 个 WARN。')
print('⚠️  门禁最大的敌人不是统计学，是**人**：一个天天误报的门禁，三周内就会长出')
print('    `--skip-gate` 参数。所以第一设计目标是「误报率低到 FAIL 出现时所有人都信」，')
print('    这比「不漏报」更重要 —— 宁可只守住真正要命的几个切片。')
print('⚠️  门禁必须跑在**不参与本轮挖掘**的固定基准集上，否则就是自己给自己出题。')"""),

    md("""## 6 · 数据配比：最优点是内点，而且有一个「天花板」

扫描配比 `p`，看两件事：目标切片能涨到多少、旧切片最多掉多少。
约束优化：**在所有旧切片都不超过各自容差的前提下，最大化目标切片 AP**。"""),
    code("""def scan_ratio(ps):
    out = []
    for p in ps:
        a = model_ap(p)
        viol = max((ap_base[s] - a[s]) - v['tol'] for s, v in SLICES.items() if s != TARGET)
        worst = max(((ap_base[s] - a[s]) / max(v['tol'], 1e-9), s)
                    for s, v in SLICES.items() if s != TARGET)[1]
        out.append(dict(p=p, ap_target=a[TARGET], viol=viol, worst=worst, feasible=viol <= 0))
    return out

grid = scan_ratio(np.linspace(0.005, 0.40, 160))
feas = [r for r in grid if r['feasible']]
best_ap = max(r['ap_target'] for r in feas)
p_star = min(r['p'] for r in feas if r['ap_target'] >= best_ap - 1e-9)

print(f'{"p":>8s} {"目标切片 AP":>12s} {"最差旧切片超额":>15s} {"绑定的切片":>14s} {"可行":>6s}')
for r in scan_ratio([0.02, 0.05, 0.08, 0.11, 0.13, 0.20, 0.30]):
    print(f'{r["p"]:>8.3f} {r["ap_target"]:>12.4f} {r["viol"] * 100:>+15.2f} '
          f'{r["worst"]:>14s} {"yes" if r["feasible"] else "**NO**":>6s}')
print(f'\\n可行域内的最优配比 p* = {p_star:.3f}，目标切片 AP = {best_ap:.4f}')

cap = (SLICES[TARGET]['n_tr'] + NEW_LABELS) * REPEAT_CAP
print(f'\\n💡 注意 p >= {cap / T_TOTAL:.3f} 之后目标切片 AP **完全不再上升** ——')
print(f'   因为有效样本量被 唯一样本数×REPEAT_CAP = {cap} 卡死了。')
print('   **重复采样不创造信息。** 再往上调配比，只剩下对旧场景的伤害。')
assert 0.02 < p_star < 0.30, '最优配比是内点，不是端点'
assert abs(model_ap(0.20)[TARGET] - model_ap(0.30)[TARGET]) < 1e-9, '超过上限后目标 AP 不再变化'

print('\\n== 候选 B（p = 0.08，取可行域内侧留安全余量）==')
rows_B, ver_B = regression_gate(S_base, S_B)
assert ver_B == 'PASS'
print(f'\\n✅ 候选 B 拿到了 {(S_B[TARGET].mean() - S_base[TARGET].mean()) * 100:+.1f} 点的目标切片提升，')
print('   而所有旧切片都在容差内 —— 同样一批数据，只是配比不同。')
print('⚠️  为什么取 0.08 而不是算出来的 p*？因为 p* 是在**无噪声的模型上**算的，')
print('    而门禁用的是**带噪声的观测值**。卡在可行域边界上，会随机地 WARN。')
print('    工程实践：**约束优化给上界，实际取内侧留 20~30% 余量。**')"""),

    md("""## 7 · 边际收益曲线：还值不值得继续标

$$\\mathrm{AP}(n) = A_\\infty - (A_\\infty - A_0)e^{-n/\\tau}$$

拟合方法：对 τ 做一维网格搜索，固定 τ 后模型对 $(A_\\infty, A_0)$ 是**线性**的，
用最小二乘闭式求解。这样只用 numpy 就能拟合三参数曲线。"""),
    code("""TRUE_CURVE = dict(a_inf=0.78, tau=2500, a0=0.30)     # 真实曲线（现实中当然不知道）
EVAL_NOISE = 0.005                                   # 每个点的评测+种子噪声

# **分批标注**：这就是为什么必须小批多轮 —— 一次标 5000 张，你永远拿不到这条曲线
ns_obs = np.array([0, 300, 700, 1400, 2600, 4500])
ap_obs = ap_curve(ns_obs, **TRUE_CURVE) + rng.normal(0, EVAL_NOISE, len(ns_obs))

def fit_saturating(ns, aps, n_tau=600):
    ns, aps = np.asarray(ns, float), np.asarray(aps, float)
    best = None
    for tau in np.exp(np.linspace(math.log(100), math.log(200000), n_tau)):
        e = np.exp(-ns / tau)
        A = np.stack([1 - e, e], axis=1)              # 固定 tau 后对 (a_inf, a0) 线性
        coef, *_ = np.linalg.lstsq(A, aps, rcond=None)
        sse = float(((A @ coef - aps) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, float(coef[0]), float(coef[1]), float(tau))
    return dict(sse=best[0], a_inf=best[1], a0=best[2], tau=best[3])

fit = fit_saturating(ns_obs, ap_obs)
print(f'{"n(该场景训练样本)":>18s} {"实测 AP":>9s} {"拟合值":>9s}')
for n_, a_ in zip(ns_obs, ap_obs):
    print(f'{n_:>18d} {a_:>9.4f} {float(ap_curve(n_, fit["a_inf"], fit["tau"], fit["a0"])):>9.4f}')
print(f'\\n拟合: A∞={fit["a_inf"]:.4f}  τ={fit["tau"]:.0f}  A₀={fit["a0"]:.4f}')
print(f'真值: A∞={TRUE_CURVE["a_inf"]:.4f}  τ={TRUE_CURVE["tau"]:.0f}  A₀={TRUE_CURVE["a0"]:.4f}')
assert abs(fit['a_inf'] - TRUE_CURVE['a_inf']) < 0.06, 'A∞ 应被大致恢复'
assert 0.5 < fit['tau'] / TRUE_CURVE['tau'] < 2.0

# **A∞ 必须带置信区间**：用它做决策时要用区间下界，别用点估计
boot = np.array([fit_saturating(ns_obs, ap_obs + rng.normal(0, EVAL_NOISE, len(ns_obs)),
                                n_tau=200)['a_inf'] for _ in range(150)])
lo, hi = np.percentile(boot, [5, 95])
print(f'A∞ 的 90% 区间: [{lo:.4f}, {hi:.4f}]   -> 决策时用下界 {lo:.4f}')
assert lo < fit['a_inf'] < hi and hi - lo > 0.005, 'A∞ 的不确定性不该被忽略'
print(f'\\n⚠️  注意：拟合的 A∞ 比真值高了 {(fit["a_inf"] - TRUE_CURVE["a_inf"]) * 100:+.1f} 点，'
      f'而 90% 区间甚至没盖住真值。')
print(f'    原因很具体：最大观测点 n={ns_obs[-1]} 只有 {ns_obs[-1] / TRUE_CURVE["tau"]:.1f}τ，'
      '**还没真正进入饱和区**，')
print('    此时外推天花板会**系统性偏乐观**。这正是本模块最后一节列的开放问题之一。')
print('    工程对策：① 决策用区间下界；② 天花板越关键，越要在大 n 处再补一个点。')
print('\\n⚠️  拟合至少要 4~5 个点、且横跨一个数量级（300 / 700 / 1400 / 2600 / 4500），')
print('    只有两个点拟合不出饱和形状。**这意味着标注必须分批做、每批重训并评测。**')
print('⚠️  曲线只在「其他条件不变」时成立：中途换 backbone 或改增强，曲线要重拟。')"""),

    code("""def predict(f, n):
    return f['a_inf'] - (f['a_inf'] - f['a0']) * math.exp(-n / f['tau'])

def marginal(f, n, batch):
    '''再标 batch 张的预期 AP 提升（闭式）。'''
    return (f['a_inf'] - predict(f, n)) * (1 - math.exp(-batch / f['tau']))

def n_for_target(f, target):
    '''达到 target 需要多少样本；target >= A∞ 时返回 inf（**不可达**）。'''
    if target >= f['a_inf']:
        return float('inf')
    return -f['tau'] * math.log((f['a_inf'] - target) / (f['a_inf'] - f['a0']))

PRICE = 2.6            # 元 / 张（夜间+遮挡的标注单价）
n_now = int(ns_obs[-1])
print(f'当前该场景已有 {n_now} 张，AP = {predict(fit, n_now):.4f}\\n')
print(f'{"再标":>8s} {"预期 ΔAP(点)":>13s} {"每千张(点)":>12s} {"花费(元)":>10s} {"每 AP 点(元)":>13s} {"建议":>10s}')
for B in [1000, 2000, 5000, 20000]:
    g = marginal(fit, n_now, B) * 100
    rec = '继续标' if g / B * 1000 >= 0.5 else '**停止**'
    print(f'{B:>8d} {g:>+13.2f} {g / B * 1000:>12.2f} {B * PRICE:>10.0f} '
          f'{B * PRICE / max(g, 1e-9):>13.0f} {rec:>10s}')

print(f'\\n{"产品目标":>10s} {"需要样本数":>12s} {"结论"}')
for t in [0.70, 0.75, 0.78, 0.85]:
    n_ = n_for_target(fit, t)
    txt = f'{n_:,.0f} 张' if math.isfinite(n_) else '**不可达**'
    concl = '' if math.isfinite(n_) else '  ← 加再多数据也到不了，必须换方法'
    print(f'{t:>10.2f} {txt:>12s}{concl}')
assert not math.isfinite(n_for_target(fit, 0.85)), '目标高于 A∞ 时必须判定为不可达'
assert n_for_target(fit, 0.75) > n_for_target(fit, 0.70) > 0

print('\\n✅ 这条曲线最大的作用：**把「还标不标」从立场之争变成算术题**。')
print(f'   A∞ = {fit["a_inf"]:.3f}，产品目标 0.85 -> 没什么可争的，继续标注不可能达标，')
print('   讨论应该立刻转向「换什么方法」：改架构 / 提分辨率 / 拆两级 / 换传感器。')
print('   （对 TSR 的雾天隧道口小目标而言，最可能有效的是提高输入分辨率与切片推理，见 C57。）')"""),

    md("""## 8 · 闭环流水线：周期时间、瓶颈与「一次通过率」的乘性杠杆

闭环系统真正该被优化的指标，不是任何一个模型指标，
而是**从发现问题到修复上线的天数**——因为长尾问题是源源不断的。"""),
    code("""STAGES = [('触发', 0.5, 0.2), ('挖掘', 1.0, 0.4), ('精选', 0.5, 0.2), ('标注', 9.0, 3.5),
          ('训练', 2.5, 0.8), ('评测', 0.6, 0.2), ('门禁', 0.3, 0.1)]
RELEASE = ('发布', 4.0, 1.5)
MAX_ATTEMPTS = 3

def simulate_cycles(gate_pass_rate, trials=2000, seed=3):
    '''门禁 FAIL -> 退回「挖掘/精选/标注」重来一轮（返工）。'''
    r = np.random.default_rng(seed)
    totals, per_stage = [], collections.defaultdict(float)
    reworks = 0
    for _ in range(trials):
        t, attempts = 0.0, 0
        while True:
            attempts += 1
            for nm, mu, sd in STAGES:
                dt = max(0.05, r.normal(mu, sd)); t += dt; per_stage[nm] += dt
            if r.random() < gate_pass_rate or attempts >= MAX_ATTEMPTS:
                break
        reworks += (attempts > 1)
        dt = max(0.05, r.normal(*RELEASE[1:])); t += dt; per_stage[RELEASE[0]] += dt
        totals.append(t)
    totals = np.array(totals)
    tot_time = sum(per_stage.values())
    return dict(p50=float(np.percentile(totals, 50)), p90=float(np.percentile(totals, 90)),
                mean=float(totals.mean()), rework_rate=reworks / trials,
                share={k: v / tot_time for k, v in per_stage.items()})

r60 = simulate_cycles(0.60)
print(f'门禁一次通过率 60%:  p50 {r60["p50"]:.1f} 天   p90 {r60["p90"]:.1f} 天   '
      f'均值 {r60["mean"]:.1f} 天   返工率 {r60["rework_rate"]:.0%}')
print(f'\\n{"阶段":<8s} {"占总耗时":>9s}')
for k, v in sorted(r60['share'].items(), key=lambda kv: -kv[1]):
    bar = '█' * int(v * 60)
    print(f'{k:<8s} {v:>9.1%}  {bar}')
bottleneck = max(r60['share'], key=r60['share'].get)
assert bottleneck == '标注', '标注通常是闭环的瓶颈'
assert r60['p90'] > r60['p50'] * 1.3, 'p90 才是真正的痛点'

print(f'\\n{"一次通过率":>10s} {"均值周期":>10s} {"p90":>8s} {"返工率":>8s}')
for pr in [0.45, 0.60, 0.85]:
    r_ = simulate_cycles(pr, seed=3)
    print(f'{pr:>10.0%} {r_["mean"]:>10.1f} {r_["p90"]:>8.1f} {r_["rework_rate"]:>8.0%}')
r85 = simulate_cycles(0.85, seed=3)
assert r85['mean'] < r60['mean'], '提高一次通过率能显著缩短周期'
print(f'\\n✅ 一次通过率 60% -> 85%，均值周期从 {r60["mean"]:.1f} 天降到 {r85["mean"]:.1f} 天。')
print('   **返工的影响是乘性的**：期望轮数 = 1/通过率。提高通过率的杠杆，')
print('   比把标注速度提升 30% 还大，而且便宜得多。')
print('   具体手段：训练前先跑配比预演、标注前小批试标验规范、门禁前先跑轻量自检。')
print('⚠️  另一个反直觉的结论：**缩短周期常常要靠「减少每轮的雄心」**。')
print('   一轮同时修 5 个失效模式，任何一个出问题整轮都卡住，且归因困难。')"""),

    md("""## ✏️ 练习 1：功效分析 —— 「要检出 +0.3 点，需要多少样本」

实现 `n_needed(delta, sd, alpha=0.05, power=0.8)`：配对设计下，
要以 `power` 的概率检出大小为 `delta` 的真实差异，需要多少个配对样本。

$$n = \\left\\lceil \\frac{(z_{1-\\alpha/2} + z_{\\text{power}})^2\\, s_d^2}{\\delta^2} \\right\\rceil$$

其中 `sd` 是**逐图差值 d 的标准差**（不是分数本身的标准差）。用上面写好的 `norm_ppf`。"""),
    code("""def n_needed(delta, sd, alpha=0.05, power=0.8):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
SD_D = float((S_A['night_urban'] - S_base['night_urban']).std(ddof=1))
n1 = n_needed(0.003, 0.042)
n2 = n_needed(0.006, 0.042)
n3 = n_needed(0.003, 0.042, power=0.9)
assert 1490 <= n1 <= 1590, n1
assert abs(n2 - n1 / 4) <= 3, (n1, n2)            # delta 翻倍 -> 样本量降到 1/4
assert n3 > n1 and isinstance(n1, int)
assert n_needed(0.003, 0.021) < n1                # 噪声减半 -> 样本量降到 1/4
print(f'逐图差值的实测标准差 sd_d = {SD_D:.4f}\\n')
print(f'{"要检出的 Δ(点)":>14s} {"power=0.8":>11s} {"power=0.9":>11s}')
for dpt in [0.1, 0.3, 0.5, 1.0, 2.0]:
    print(f'{dpt:>14.1f} {n_needed(dpt / 100, SD_D):>11d} {n_needed(dpt / 100, SD_D, power=0.9):>11d}')
print('\\n✅ 练习 1 通过：**「+0.3 点算不算提升」的答案，取决于你的评测集有多大。**')
print('   把这张表贴在评测集设计文档里，比事后争论有用得多。')"""),

    md("""## ✏️ 练习 2：Benjamini–Hochberg FDR 校正

实现 `benjamini_hochberg(pvals, q=0.05)`：返回与 `pvals` 等长的**布尔数组**，
表示每个假设是否被拒绝（判为显著）。

算法：把 p 值升序排列得到 `p₍₁₎ ≤ … ≤ p₍ₘ₎`，
找出**最大**的 `k` 使得 `p₍ₖ₎ ≤ k·q/m`，然后拒绝排名前 `k` 的全部假设
（注意：是「前 k 个全拒」，不是「逐个比较」——这是最容易写错的地方）。
若不存在这样的 `k`，一个都不拒。"""),
    code("""def benjamini_hochberg(pvals, q=0.05):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
ps = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.500])
rej = benjamini_hochberg(ps, 0.05)
assert list(rej) == [True, True, False, False, False, False, False], list(rej)
assert benjamini_hochberg(ps, 0.05).sum() > (ps < 0.05 / len(ps)).sum(), 'BH 应比 Bonferroni 宽松'
assert benjamini_hochberg(np.ones(10), 0.05).sum() == 0
assert benjamini_hochberg(np.full(10, 0.001), 0.05).all()
assert benjamini_hochberg(np.array([0.02, 0.03, 0.04]), 0.05).all(), '「前 k 个全拒」：逐个比会漏掉 0.02'

p_slices = np.array([r['p'] for r in rows_A])
names = [r['slice'] for r in rows_A]
bh = benjamini_hochberg(p_slices, 0.05)
bonf = p_slices < 0.05 / len(p_slices)
print(f'{"切片":<18s} {"p":>10s} {"Bonferroni":>11s} {"BH(q=.05)":>11s}')
for nm, p_, b1, b2 in zip(names, p_slices, bonf, bh):
    print(f'{nm:<18s} {p_:>10.2e} {str(bool(b1)):>11s} {str(bool(b2)):>11s}')
print('\\n✅ 练习 2 通过：**门禁用 Bonferroni（怕误报），探索用 BH（怕漏掉线索）** ——')
print('   选哪个取决于你更怕哪种错，而不是哪个更「先进」。')"""),

    md("""## ✏️ 练习 3：停标决策 —— 边际收益曲线的直接应用

实现 `label_more(fit, n_now, batch, price, min_gain_per_1k, target=None)`，返回一个 dict：

- `gain_points`：再标 `batch` 张的预期 AP 提升（**单位是「点」，即 ×100**）
- `gain_per_1k`：每千张的预期提升（点）
- `cost` / `cost_per_point`：花费与每个 AP 点的成本（元）
- `decision` ∈ `'continue'` / `'stop_diminishing'` / `'stop_unreachable'`

判定顺序（**先判天花板**）：① `target` 给定且 `target ≥ fit['a_inf']` → `stop_unreachable`；
② `gain_per_1k < min_gain_per_1k` → `stop_diminishing`；③ 否则 `continue`。"""),
    code("""def label_more(fit, n_now, batch, price, min_gain_per_1k, target=None):
    # TODO: 复用上面的 predict / marginal
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
FIT_DEMO = dict(a_inf=0.78, tau=2500, a0=0.30)
r1 = label_more(FIT_DEMO, 2000, 2000, 2.6, min_gain_per_1k=0.5)
assert abs(r1['gain_points'] - 11.88) < 0.15, r1['gain_points']
assert abs(r1['gain_per_1k'] - 5.94) < 0.10 and r1['decision'] == 'continue'
assert abs(r1['cost'] - 5200) < 1e-6 and abs(r1['cost_per_point'] - 437.7) < 6
r2 = label_more(FIT_DEMO, 12000, 2000, 2.6, min_gain_per_1k=0.5)
assert r2['decision'] == 'stop_diminishing', r2
r3 = label_more(FIT_DEMO, 2000, 2000, 2.6, min_gain_per_1k=0.5, target=0.80)
assert r3['decision'] == 'stop_unreachable', '天花板要先判：目标高于 A∞ 时，涨得再快也没用'
print(f'{"已有样本":>9s} {"再标":>7s} {"ΔAP(点)":>9s} {"每千张":>8s} {"每 AP 点(元)":>13s} {"决策":>18s}')
for n_ in [500, 2000, 5000, 12000, 30000]:
    r = label_more(FIT_DEMO, n_, 2000, 2.6, 0.5)
    print(f'{n_:>9d} {2000:>7d} {r["gain_points"]:>9.2f} {r["gain_per_1k"]:>8.2f} '
          f'{r["cost_per_point"]:>13.0f} {r["decision"]:>18s}')
print('\\n✅ 练习 3 通过：**「先判天花板，再判边际」这个顺序是关键** ——')
print('   目标不可达时，边际收益再高也应该停下来换方法，而不是接着标。')"""),

    md("""## ✏️ 练习 4：周期时间分解与瓶颈定位

实现 `cycle_time_breakdown(events)`：`events` 是 `(ticket, stage, start_day, end_day)` 的列表。
返回 dict，包含：

- `cycle_time`：`{ticket: 该 ticket 的最大 end − 最小 start}`
- `p50` / `p90`：所有 ticket 周期时间的分位数（用 `np.percentile`）
- `stage_share`：`{stage: 该阶段总耗时 / 全部阶段总耗时}`
- `bottleneck`：占比最大的阶段名
- `rework_rate`：**有任一阶段出现超过一次**的 ticket 占比"""),
    code("""EVENTS = [
    ('T1', '触发', 0, 1), ('T1', '挖掘', 1, 2), ('T1', '标注', 2, 12),
    ('T1', '训练', 12, 15), ('T1', '门禁', 15, 15.5), ('T1', '发布', 15.5, 20),
    ('T2', '触发', 0, 1), ('T2', '挖掘', 1, 3), ('T2', '标注', 3, 17),
    ('T2', '训练', 17, 20), ('T2', '门禁', 20, 20.5),
    ('T2', '标注', 20.5, 28), ('T2', '训练', 28, 31),        # ← 门禁 FAIL 后的返工
    ('T2', '门禁', 31, 31.5), ('T2', '发布', 31.5, 36),
    ('T3', '触发', 0, 0.5), ('T3', '挖掘', 0.5, 1.5), ('T3', '标注', 1.5, 9),
    ('T3', '训练', 9, 11), ('T3', '门禁', 11, 11.5), ('T3', '发布', 11.5, 14),
    ('T4', '触发', 0, 1), ('T4', '挖掘', 1, 2), ('T4', '标注', 2, 20),
    ('T4', '训练', 20, 24), ('T4', '门禁', 24, 24.5), ('T4', '发布', 24.5, 30),
]

def cycle_time_breakdown(events):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
br = cycle_time_breakdown(EVENTS)
assert br['cycle_time'] == {'T1': 20.0, 'T2': 36.0, 'T3': 14.0, 'T4': 30.0}, br['cycle_time']
assert abs(br['p50'] - 25.0) < 1e-6 and abs(br['p90'] - 34.2) < 1e-6, (br['p50'], br['p90'])
assert br['bottleneck'] == '标注'
assert abs(br['stage_share']['标注'] - 0.57) < 1e-6, br['stage_share']['标注']
assert abs(br['rework_rate'] - 0.25) < 1e-9
assert abs(sum(br['stage_share'].values()) - 1.0) < 1e-9
print(f'周期时间: p50 {br["p50"]:.1f} 天   p90 {br["p90"]:.1f} 天   返工率 {br["rework_rate"]:.0%}\\n')
print(f'{"阶段":<8s} {"占比":>8s}')
for k, v in sorted(br['stage_share'].items(), key=lambda kv: -kv[1]):
    print(f'{k:<8s} {v:>8.1%}  {"█" * int(v * 50)}')
print(f'\\n瓶颈: **{br["bottleneck"]}**')
print('✅ 练习 4 通过：**优化非瓶颈阶段的收益接近零** —— 训练加速 2× 只省 0.6 天，')
print('   而把标注周期缩短 30% 能省 5 天以上。先测量，再优化。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def n_needed(delta, sd, alpha=0.05, power=0.8):
    z_a = norm_ppf(1 - alpha / 2)
    z_b = norm_ppf(power)
    return int(math.ceil((z_a + z_b) ** 2 * sd ** 2 / delta ** 2))"""),
    code("""# 练习 2 参考答案
def benjamini_hochberg(pvals, q=0.05):
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p)                       # 升序
    thresh = (np.arange(1, m + 1) * q) / m
    passing = np.where(p[order] <= thresh)[0]
    rej = np.zeros(m, dtype=bool)
    if len(passing):
        k = passing.max() + 1                   # **最大的 k**，然后前 k 个全拒
        rej[order[:k]] = True
    return rej"""),
    code("""# 练习 3 参考答案
def label_more(fit, n_now, batch, price, min_gain_per_1k, target=None):
    gain_points = marginal(fit, n_now, batch) * 100
    gain_per_1k = gain_points / batch * 1000
    cost = batch * price
    out = dict(gain_points=gain_points, gain_per_1k=gain_per_1k, cost=cost,
               cost_per_point=cost / max(gain_points, 1e-12))
    if target is not None and target >= fit['a_inf']:
        out['decision'] = 'stop_unreachable'    # ← 先判天花板
    elif gain_per_1k < min_gain_per_1k:
        out['decision'] = 'stop_diminishing'
    else:
        out['decision'] = 'continue'
    return out"""),
    code("""# 练习 4 参考答案
def cycle_time_breakdown(events):
    by_ticket = collections.defaultdict(list)
    for t, st, s0, s1 in events:
        by_ticket[t].append((st, float(s0), float(s1)))
    cycle = {t: max(e[2] for e in v) - min(e[1] for e in v) for t, v in by_ticket.items()}
    stage = collections.defaultdict(float)
    for t, st, s0, s1 in events:
        stage[st] += float(s1) - float(s0)
    total = sum(stage.values())
    rework = sum(1 for v in by_ticket.values()
                 if max(collections.Counter(e[0] for e in v).values()) > 1)
    ct = np.array(list(cycle.values()), dtype=float)
    return dict(cycle_time=cycle,
                p50=float(np.percentile(ct, 50)), p90=float(np.percentile(ct, 90)),
                stage_share={k: v / total for k, v in stage.items()},
                bottleneck=max(stage, key=stage.get),
                rework_rate=rework / len(by_ticket))"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接照搬的闭环验证配置与报告模板"""),
    code("""RECIPE = r'''
# ===================== closed_loop.yaml =====================
experiment_id: exp_2026w32_tunnel_construction
ticket:        TSR-4471                 # 与模块 04 的挖掘任务同源，全程可追溯

# ---- ① 预注册（跑实验**之前**填，之后不许改）----
preregistration:
  primary_metric:   fog_tunnel.AP       # 主指标：只此一个，不需要多重比较校正
  expected_gain:    ">= +8.0 点"        # 预期效应量。没达到 = 假设被证伪，也是有效结论
  regression_sentinels:                 # 哨兵切片：只有这几个进 Bonferroni 家族
    - day_clear_urban
    - night_urban
    - rain_highway
  exploratory: "其余切片仅作探索，用 BH(q=0.05)，结论需再验证"

# ---- ② 数据与配比 ----
data:
  base_dataset:   v1.7.2
  new_batches:    [b_tunnel_2026w31]    # 1204 帧
  mix_ratio_p:    0.08                  # **约束优化给上界 0.11，实际取内侧留余量**
  leakage_check:  {frame_id: strict, phash_thresh: 6, split_key: clip_id}
                                        # 与评测集交集非空 -> **直接终止实验**，不是警告
  seeds: [0, 1, 2]                      # 关键发布 3 种子；日常迭代 1 种子 + 更大容差

# ---- ③ 评测：两套集合，用途不能混 ----
eval_sets:
  benchmark:   tsr_bench_v6      # **固定基准集**：按部署真实分布随机采样，冻结
                                 #   -> 回归门禁的唯一依据
  failure_modes: tsr_fm_v12      # 失效模式集：随挖掘扩充 -> 只看目标场景修好没有
  slice_labels_version: 2026.03  # **切片标签冻结** —— 尺子不能跟着被测物一起变

# ---- ④ 回归门禁 ----
gate:
  test: paired_bootstrap         # 同一批图 -> 必须配对
  correction: bonferroni         # 门禁怕误报
  alpha: 0.05
  tolerance:
    safety_critical: 0.000       # stop / yield / 施工 / 限速下调 -> **零容忍**
    common:          0.005
    small_sample:    0.015       # n < 100 的切片，噪声本来就大
  global_gates:
    - fp_per_km_increase <= 5%   # 工程指标，比 precision 更贴近路测体验
    - p99_latency_increase <= 0% # 模型换了可能变慢
    - flicker_rate_increase <= 0%# 时序稳定性：AP 涨但框闪烁 = 体验变差
  on_warn:  "允许发布，但强制建单跟踪；连续两轮 WARN 升级为 FAIL"
  on_fail:  "退回调配比或补数据；**不允许 --skip-gate**"

# ---- ⑤ 边际收益曲线（每个重点场景维护一条）----
marginal_curve:
  model: "AP(n) = A_inf - (A_inf - A0) * exp(-n / tau)"
  points: [[0, 0.301], [300, 0.352], [700, 0.410], [1400, 0.494],
           [2600, 0.593], [4500, 0.679]]
  fitted:  {A_inf: 0.785, tau: 2543, A0: 0.291, A_inf_ci90: [0.762, 0.809]}
  stop_rule:
    min_gain_per_1k_labels: 0.5   # 点/千张，低于此值停止标注
    max_cost_per_ap_point:  800   # 元，超过此值停止标注
    unreachable_if: "target >= A_inf_ci90_low"   # **用区间下界判天花板**

# ---- ⑥ 发布与闭环回流 ----
rollout: [shadow_7d, internal_fleet_14d, limited_odd_30d, full]
shadow:
  log: disagreement_frames        # 新旧模型分歧帧 -> **直接回流成下一轮挖掘的种子**
  note: "影子模式没有真值：分歧率下降 != 模型变好"
cycle_time_slo:
  p50_days: 21
  p90_days: 35
  gate_first_pass_rate: ">= 0.80"  # 返工是乘性成本：期望轮数 = 1/通过率
'''
print(RECIPE)
for token in ['preregistration', 'mix_ratio_p', 'leakage_check', 'split_key',
              'safety_critical', 'fp_per_km_increase', 'A_inf_ci90',
              'min_gain_per_1k_labels', 'disagreement_frames', 'gate_first_pass_rate']:
    assert token in RECIPE, token
print('✅ 配方覆盖：预注册 / 配比 / 泄漏检查 / 双评测集 / 分层容差 / 全局工程门禁 / '
      '边际收益曲线与停标规则 / 分阶段放开 / 影子回流 / 周期时间 SLO')"""),

    md("""### 小结

- **加数据之后必须回答三个问题**：目标场景涨了吗？其他场景掉了吗？涨的部分是数据的功劳还是噪声？
  三问分别对应切片评测、回归门禁、显著性检验。
- **整体 mAP 是按样本数加权的平均，而加权平均就是用来掩盖长尾的**。
  实测：整体 +1.7 点的候选，背后是 3 个切片在回归，其中一个占 22% 的评测权重。
- **两个模型评的是同一批图 -> 必须用配对统计**。实测配对把标准误缩小 3.4×，
  等价于样本量放大 11×；非配对检验会给出「不显著」这个错误结论。
- **切片一多，假阳性是必然的**：20 个切片、无真实差异时，64% 的实验会「发现」假回归。
  门禁用 Bonferroni（怕误报），探索用 BH（怕漏线索），最有效的是**预注册**。
- **回归门禁的第一设计目标是「误报率低到 FAIL 出现时所有人都信」**，这比不漏报更重要。
  容差按样本量与安全等级分层；安全关键切片零容忍；门禁必须跑在**不参与挖掘的固定基准集**上。
- **新旧数据配比的最优点是内点**（典型 10%–30%）。两个端点都错：按自然比例 = 「加了没效果」，
  只用新数据微调 = 灾难性遗忘。而且**重复采样不创造信息**——超过 `唯一样本数 × 重复上限`
  之后，再提高配比只剩下对旧场景的伤害。
- **边际收益曲线 `AP(n) = A∞ − (A∞ − A₀)e^{−n/τ}` 是数据决策的核心工具**：
  `A∞` 回答「天花板够不够得着目标」（**先判这个**），`ΔAP/千张 × 单价`回答「每个 AP 点多少钱」。
  拟合要 4–5 个横跨一个数量级的点 -> **标注必须小批多轮**，且 `A∞` 要带置信区间、用下界决策。
- **闭环该被优化的指标是周期时间，不是任何模型指标**。瓶颈通常在标注（占 50%+），
  而**返工的影响是乘性的**（期望轮数 = 1/通过率）：一次通过率 60%→85%，均值周期少 5 天以上。
- **离线全绿不等于能上车**：影子模式 → 内部车队 → 有限 ODD 灰度 → 全量，
  每阶段有独立退出准则；影子的分歧帧**直接回流成下一轮挖掘的种子**——这条回边才是「闭环」。

C58 到此结束。下一站：**C59 · VLA 与感知接口** —— 把 TSR 的输出送进下游决策。"""),
]
