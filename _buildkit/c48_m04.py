# -*- coding: utf-8 -*-
"""C48 模块 04 · 发布策略与自动扩缩。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–03、基本假设检验（C03/C10 的统计部分有帮助但不必需）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_rollout_autoscaling.ipynb'),
    ("核心参考", "Argo Rollouts / Flagger 文档、K8s HPA 算法、Google SRE Book 第 27 章、序贯检验（SPRT / always-valid inference）"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("risk", "发布的本质：把风险切成小份", "".join([
        P("集群会自愈了。但自愈只能救「机器挂了」这种<strong>外生</strong>故障，救不了「你自己推了一个坏版本」这种<strong>内生</strong>故障——恰恰后者是生产事故的主要来源。行业数据反复显示，<em>绝大多数线上事故的直接触发点是一次变更</em>。"),
        P("所以发布策略的全部目的，可以用模块 00 的公式概括："),
        MATH("\\text{损失} = \\underbrace{f_{affected}}_{\\text{爆炸半径}} \\times \\underbrace{(T_{detect} + T_{recover})}_{\\text{MTTR}}"),
        P("你只有两个杠杆：<strong>压小 <code>f</code></strong>（渐进发布）和<strong>压小 <code>T</code></strong>（自动检测 + 自动回滚）。而且它们的<em>收益不对称</em>——把 <code>f</code> 从 100% 降到 5% 是 20 倍收益、几乎无成本；把 <code>T_detect</code> 从 5 分钟降到 1 分钟需要完善的可观测性建设，且有下界（统计上你需要足够样本才能判断）。<strong>所以先压 <code>f</code>，再压 <code>T</code></strong>。"),
        TABLE(["策略", "f（爆炸半径）", "额外资源", "回滚速度", "适合"], [
            ["<strong>Recreate</strong> 停机重建", "100%（且有停机）", "0（先停后起）", "重新发一次", "只有开发环境该用"],
            ["<strong>RollingUpdate</strong> 滚动", "随进度 0→100%", "maxSurge 的额外副本", "滚回去，分钟级", "默认策略，适合低风险变更"],
            ["<strong>Blue-Green</strong> 蓝绿", "切换瞬间 0→100%", "<strong>2 倍</strong>（两套全量并存）", "<strong>秒级</strong>（切回去）", "要求瞬间回滚、能承受 2 倍成本"],
            ["<strong>Canary</strong> 金丝雀", "可控（1%→5%→25%→100%）", "少量额外副本", "秒级（把权重归零）", "<strong>LLM 服务的默认选择</strong>"],
            ["<strong>Shadow</strong> 影子流量", "<strong>0</strong>（不返回给用户）", "1 倍（镜像全量流量）", "不需要", "验证性能/正确性，不验证用户反应"],
        ]),
        DUAL(
            "为什么金丝雀是 LLM 服务的默认答案？因为 LLM 变更的<strong>失效模式特别隐蔽</strong>。换个量化精度、换个 prompt 模板、换个采样参数——服务不会崩、错误率不会涨、延迟可能还更好，但<em>输出质量悄悄劣化了</em>。这种问题只能靠「小流量 + 观察质量指标」发现，靠 <code>kubectl rollout status</code> 看到的「全部 Pod Running」毫无意义。",
            "更严格地说，LLM 发布要监控<strong>两类指标</strong>：<em>系统指标</em>（错误率、TTFT/TPOT、GPU 利用率——秒级可得、方差小、几分钟就能判断）和<em>质量指标</em>（人工评分、LLM-judge 胜率、下游任务准确率、<code>finish_reason=length</code> 比例、用户重试率——分钟到小时级、方差大、需要大样本）。<strong>两类指标的检测时间差了 1–2 个数量级</strong>，这直接决定了金丝雀的分阶段设计：先用系统指标快速过一关，再用质量指标慢慢过第二关。",
        ),
        CALLOUT("danger", "<p>一个必须内化的原则：<strong>回滚必须比修复快，且必须是无脑的</strong>。事故当中，人的判断力是下降的。如果回滚需要「先看一下是哪个 commit、再决定要不要 revert、还要重新构建镜像」，那么在压力下这条路径一定会出错。正确的做法是：<em>上一个已知良好的版本始终是可以一键切回的活对象</em>——蓝绿保留旧环境、金丝雀保留旧 ReplicaSet、Deployment 保留 <code>revisionHistoryLimit</code> 个历史。<strong>先回滚、后定位</strong>，永远不要在事故中调试。</p>", "回滚优先于修复"),
    ])),
    ("rolling", "滚动更新的数学：容量为什么会塌", "".join([
        P("滚动更新看起来很温和：一个个换。但它有两个参数，配错了会在更新期间<strong>把容量打到低于流量需求</strong>，制造一次自伤事故。"),
        TABLE(["参数", "含义", "默认值", "调大的后果"], [
            ["<code>maxUnavailable</code>", "更新期间最多有几个副本不可用", "25%", "更新更快，但<strong>容量下探更深</strong>"],
            ["<code>maxSurge</code>", "更新期间最多超出期望副本数几个", "25%", "更新更快、容量不下探，但<strong>要多占资源</strong>（GPU 场景=真金白银）"],
        ]),
        P("更新期间的可用副本数满足："),
        MATH("R_{avail}(t) \\ge R_{desired} - \\texttt{maxUnavailable}, \\qquad R_{total}(t) \\le R_{desired} + \\texttt{maxSurge}"),
        ASCII("""13 副本, maxUnavailable=25%(3), maxSurge=25%(3)

可用副本
 16 │                    ╭──── 新版本全部就绪
 13 │────╮        ╭──────╯     ← 期望容量线
 10 │    ╰────────╯            ← 最深下探 = 13 - 3 = 10
    └────────────────────────────────► 时间
         ↑                ↑
      开始更新        新 Pod 就绪（LLM 要 3 分钟！）

危险：若峰值流量需要 12 个副本，这段时间内 ρ > 1，排队爆炸（模块 02 的死亡地带）。"""),
        DUAL(
            "对普通 web 服务，新 Pod 三秒就绪，这个「凹陷」窄到没人注意。<strong>对 LLM 服务，新 Pod 要三分钟才就绪</strong>，凹陷会持续很久——如果一批要换 3 个，每批 3 分钟，13 个副本换完要 15 分钟，这 15 分钟你都在低于额定容量运行。<em>把 <code>maxUnavailable</code> 设成 0 是 LLM 服务的标准做法</em>：先起新的、就绪了再摘旧的，容量永不下探。",
            "代价是必须有 <code>maxSurge &gt; 0</code>，即要有空闲 GPU 承载额外副本。<code>maxSurge: 1</code> 时更新是完全串行的（起一个、就绪、摘一个、再起一个），13 个副本 × 3 分钟 = 39 分钟。<code>maxSurge: 25%</code>（3 个）能并行三个一批，约 15 分钟。<strong>这就是「更新时长 vs 额外 GPU」的直接权衡</strong>：付 3 张卡的钱，换 2.6 倍的更新速度。notebook 会把这条曲线画出来。",
        ),
        CALLOUT("warn", "滚动更新还有一个 LLM 特有的隐蔽问题：<strong>新旧版本会同时在线</strong>。如果你换的是模型权重，那么在更新的这 15 分钟里，<em>同一个用户的两次请求可能被不同版本处理</em>，得到风格/能力不一致的回答。对多轮对话尤其明显。要避免就得做会话粘性（session affinity）路由，或者干脆用蓝绿（瞬间切换，无混合期）。这是「滚动更新对 LLM 未必最优」的另一个理由。"),
    ])),
    ("canary", "金丝雀：分阶段放量与自动分析", "".join([
        P("金丝雀发布的完整形态不是「切 5% 流量看一眼」，而是一条<strong>带自动判据的流水线</strong>："),
        ASCII("""┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ 部署金丝雀│──▶│ 1% / 5min│──▶│ 5% /10min│──▶│25% /20min│──▶│ 100% 全量│
└──────────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┘
                    │              │              │
              自动分析 ✓     自动分析 ✓     自动分析 ✓
                    │              │              │
                    ✗ 任一失败 ─────┴──────────────┴──▶ 【自动回滚：权重归零】

每个阶段的自动分析（analysis run）检查：
  · 系统指标：错误率 ≤ baseline+0.1%、P95 TTFT ≤ baseline×1.2
  · 质量指标：LLM-judge 胜率 ≥ 0.45（非劣性）、finish_reason=length 比例无显著上升
  · 样本量门槛：本阶段至少 N 个请求，否则延长而非放行""")
        ,
        P("这里最容易被做错的一步是<strong>「看一眼」的那个判据</strong>。工程师的直觉是「错误率没涨就放行」，但这在统计上是站不住的——5% 流量跑 5 分钟可能只有几百个请求，这点样本下「错误率 0.1% vs 0.15%」的差异完全在噪声里。<em>你需要的是一个有明确统计意义的判据，而不是一眼</em>。"),
        H3("三种判据，从粗到细"),
        TABLE(["判据", "怎么做", "样本需求", "适合"], [
            ["<strong>阈值判据</strong>", "错误率 &lt; 0.5%、P95 &lt; 800ms", "小", "系统指标的第一道粗筛（能挡住「彻底坏了」）"],
            ["<strong>对照判据</strong>（A/B）", "金丝雀 vs 基线同时段对比，做假设检验", "中等", "系统指标的精筛，排除环境波动"],
            ["<strong>非劣性检验</strong>", "检验「新版本不比旧版本差超过 δ」而非「新版本更好」", "大", "质量指标（这是正确的问法）"],
        ]),
        DUAL(
            "为什么质量指标要用<strong>非劣性</strong>而不是普通的显著性检验？因为发布的问题不是「新版本更好吗」，而是「<em>新版本会不会更差</em>」。普通检验的原假设是「两者相同」，检验不显著只能说「没证据表明不同」——但这也可能是样本太少。非劣性检验把原假设反过来设成「新版本差了至少 δ」，拒绝它才放行。<em>这个方向的翻转是发布决策的正确姿势</em>。",
            "还有一个必须处理的统计陷阱：<span class=\"term\">peeking</span>（偷看）。金丝雀天然是「持续监控、随时可能叫停」，这等价于反复做检验。固定样本量的 p 值在反复偷看下会严重膨胀假阳性率——每 10 秒看一次，跑 10 分钟就是 60 次检验，即使新旧版本完全相同，「至少有一次 p&lt;0.05」的概率也接近 95%。正确做法是用<strong>序贯检验</strong>（SPRT）或<strong>always-valid 置信序列</strong>，它们在任意停止时刻都保持名义错误率。notebook 会把「朴素反复检验」的假阳性率跑出来给你看。",
        ),
        CALLOUT("intuition", "工程上的务实折中：<strong>系统指标用阈值 + 短窗口（快，几分钟就能挡住灾难性 bug），质量指标用序贯检验 + 长窗口（慢，但避免误判）</strong>。两条腿分开走。绝大多数坏发布是灾难性的（服务起不来、错误率飙升），会被第一条腿在 5 分钟内挡下；剩下的隐蔽劣化交给第二条腿慢慢判。<em>不要试图用一个判据同时解决两件事</em>。"),
    ])),
    ("hpa", "自动扩缩：控制律与震荡", "".join([
        P("流量涨了要加副本，跌了要减。听起来简单，实现起来是个<strong>控制系统</strong>问题——而控制系统会震荡。"),
        P("K8s HPA 的算法是一个朴素的比例控制器，公式短到可以背下来："),
        MATH("R_{desired} = \\left\\lceil R_{current} \\times \\frac{M_{current}}{M_{target}} \\right\\rceil"),
        P("配一个<strong>容差带（tolerance）</strong>：当比值落在 <code>[1−0.1, 1+0.1]</code> 内时不动作，避免在目标点附近反复抖动。这个死区是 HPA 稳定性的第一道保险。"),
        ASCII("""HPA 的反馈回路（以及它为什么会震荡）

   流量 λ ──▶ [ 服务 R 个副本 ] ──▶ 指标 M（利用率/队列深度/QPS）
                    ▲                        │
                    │                        ▼
              扩缩动作 ◀── [ HPA 控制器 ] ◀── 指标采集（15s 一次，且滞后！）
                              每 15s 算一次

三个致命延迟：
  ① 指标采集与聚合滞后        ~30 s
  ② HPA 同步周期              ~15 s
  ③ 新副本冷启动（模块 01）   ~60-180 s  ← LLM 的这一项是普通服务的 30 倍

总环路延迟 L ≈ 2-4 分钟。**控制回路的延迟越大，越容易震荡。**""")
        ,
        DUAL(
            "震荡是这么来的：流量涨 → 指标涨 → HPA 扩容 → <em>但新副本三分钟后才生效</em> → 这三分钟里指标还在涨 → HPA 继续扩 → 三分钟后一大批副本同时就绪 → 指标暴跌 → HPA 缩容 → 缩完流量又上来……<strong>系统在一个周期约等于 2 倍环路延迟的极限环里来回摆</strong>，副本数忽高忽低，成本和延迟双输。",
            "控制论的标准结论：对于带纯延迟 <code>L</code> 的反馈系统，比例增益过大会失稳。HPA 的缓解手段有三个：<strong>①稳定窗口（stabilization window）</strong>——缩容前看过去 5 分钟的最大建议值（默认 300s），扩容前看过去 0s（默认立刻扩）。<em>这个不对称是刻意的</em>：扩容要快（用户在等），缩容要慢（省钱不急，且防抖）。<strong>②扩缩速率限制</strong>（<code>behavior.scaleDown.policies</code>：每分钟最多缩 10%）。<strong>③选对指标</strong>——见下。",
        ),
        H3("按什么指标扩缩：LLM 的正确答案不是 GPU 利用率"),
        TABLE(["指标", "问题", "适合吗"], [
            ["CPU 利用率", "LLM 推理的瓶颈在 GPU，CPU 几乎不动", "❌ 完全无效"],
            ["GPU 利用率", "<code>nvidia-smi</code> 的 utilization 只表示「有 kernel 在跑」，不表示「跑满了」；且 continuous batching 下它长期接近 100%，几乎没有区分度", "❌ 误导性强"],
            ["<strong>队列深度 / 等待请求数</strong>", "直接反映供需缺口，且<strong>领先于</strong>延迟劣化", "✅ <strong>最佳</strong>"],
            ["P95 TTFT", "直接对应 SLO，但是<strong>滞后</strong>指标——它涨的时候已经在伤害用户了", "🔶 作为兜底触发器"],
            ["QPS / 并发数", "简单可靠，但需要知道单副本容量（模块 02 的 μ）", "✅ 好，尤其配合预测"],
        ]),
        CALLOUT("warn", "<strong>队列深度胜过延迟</strong>，理由值得记住：队列深度是<em>领先指标</em>（leading indicator），延迟是<em>滞后指标</em>（lagging indicator）。当队列开始堆积时，延迟还没恶化（因为请求还在排队没超时），此时扩容还来得及；等到 P95 TTFT 破线，你已经欠了用户三分钟的债，而扩容还要三分钟才生效。<em>用滞后指标做反馈控制，等于闭着眼睛开车看后视镜</em>。KEDA 的价值就在于它能按队列长度这类外部指标扩缩，而原生 HPA 需要配自定义指标适配器。"),
        P("最后一条对 LLM 至关重要：<strong>当冷启动 &gt; 环路能容忍的延迟时，反应式扩容在数学上就是不够的</strong>。三分钟的冷启动意味着你永远在追赶三分钟前的流量。解法有三：<em>预测式扩容</em>（按日周期/预约流量提前扩）、<em>保留热备</em>（多养 N 个空闲副本作缓冲，用钱买时间）、<em>缩短冷启动</em>（模块 01 的全部内容）。生产上通常三管齐下。"),
    ])),
    ("scaletozero", "冷启动、热备与 scale-to-zero", "".join([
        P("上一节的结论逼出一个具体的工程量：<strong>你需要养多少热备副本</strong>？这可以算出来。"),
        P("设流量上升速率为 <code>dλ/dt</code>（QPS/秒）、单副本容量 <code>μ</code>、冷启动时间 <code>T_cold</code>。在扩容生效之前，你需要用现有余量吃掉这段时间涨上来的流量："),
        MATH("R_{buffer} \\ge \\frac{1}{\\mu} \\cdot \\frac{d\\lambda}{dt} \\cdot T_{cold}"),
        TABLE(["场景", "dλ/dt", "T_cold", "μ", "需要热备"], [
            ["平缓日周期", "0.05 QPS/s", "180 s", "2.5", "≈ 4 个副本"],
            ["营销活动开闸", "2 QPS/s", "180 s", "2.5", "≈ 144 个副本（不现实！）"],
            ["同上，但冷启动压到 30 s", "2 QPS/s", "30 s", "2.5", "≈ 24 个副本"],
        ]),
        DUAL(
            "第二行说明了一个残酷事实：<strong>面对陡峭的流量尖峰，靠热备是买不起的</strong>。这时候只能靠别的手段：提前预约扩容（知道活动几点开始就几点前扩好）、排队+降级（承认扛不住，优雅地限流而不是崩）、或者让上游做流量整形。<em>「自动扩缩能解决一切突发」是个危险的幻觉</em>。",
            "第三行说明了模块 01 的价值：<strong>冷启动时间是热备成本的乘数</strong>。把 <code>T_cold</code> 从 180 秒压到 30 秒，热备需求降到 1/6，直接省下 120 个副本的钱。这就是为什么镜像瘦身、权重本地缓存、CUDA graph 缓存这些「看起来是小优化」的事情，在自动扩缩场景下有放大的收益。",
        ),
        H3("scale-to-zero：省钱的极限与它的代价"),
        P("对低频服务（内部工具、长尾模型），最省钱的做法是<strong>没有流量时缩到 0 个副本</strong>。Knative/KEDA 支持这个。代价是第一个请求要等完整的冷启动——对 LLM 就是几十秒到几分钟，用户体验极差。"),
        UL([
            "<strong>什么时候值得</strong>：请求间隔远大于冷启动时间（如每天几十次调用的内部工具），且调用方能容忍首次延迟（异步/批处理场景）。",
            "<strong>什么时候不值得</strong>：任何面向终端用户的交互式服务。宁可养一个最小副本（<code>minReplicas: 1</code>），那点钱远比丢失用户便宜。",
            "<strong>折中方案</strong>：<em>缩到 0 但保留权重在节点本地缓存</em>（模块 01），把冷启动从「拉镜像+下权重+加载」压缩到「加载」；或者用一个极小的常驻模型兜底首个请求，同时后台唤醒大模型。",
        ]),
        CALLOUT("intuition", "关于扩缩的成本直觉：<strong>自动扩缩省下的是「波谷时段的闲置」，买单的是「波峰时段的响应速度」和「工程复杂度」</strong>。如果你的流量日夜比是 1.3:1，自动扩缩几乎不值得做（省不了多少，还引入震荡风险）；如果是 10:1（典型的 to-B 工作日流量），它能省掉一大半账单，非常值得。<em>先看你的流量曲线，再决定要不要上这套东西</em>。"),
    ])),
    ("rollback", "自动回滚：错误预算驱动的决策", "".join([
        P("最后一块拼图：<strong>什么时候必须自动回滚，而不是等人来看</strong>。"),
        P("答案应该由<span class=\"term\">错误预算消耗速率</span>（burn rate）决定，而不是由固定阈值决定。burn rate 定义为：当前错误率相对于「刚好用完预算」的错误率的倍数。"),
        MATH("\\text{burn rate} = \\frac{\\text{实际错误率}}{1 - \\text{SLO}}"),
        TABLE(["burn rate", "含义", "多久烧完 30 天预算", "应该做什么"], [
            ["1×", "刚好按计划消耗", "30 天", "正常"],
            ["6×", "快 6 倍", "5 天", "告警，人来看"],
            ["14.4×", "快 14 倍", "2 天", "<strong>紧急告警</strong>"],
            ["&gt; 100×", "灾难", "&lt; 7 小时", "<strong>自动回滚，不等人</strong>"],
        ]),
        DUAL(
            "为什么用 burn rate 而不是「错误率 &gt; 1% 就回滚」？因为固定阈值不知道你的 SLO 是多少。对 99% 的服务，1% 错误率是刚好达标；对 99.99% 的服务，1% 错误率是 100 倍超支、七小时烧光一个月的预算。<strong>burn rate 自动把阈值归一化到你的 SLO 上</strong>，一套告警规则适用于所有服务。",
            "工程实现上要用<strong>多窗口多燃烧率</strong>（multi-window multi-burn-rate）告警：短窗口（5 分钟）高倍率（14×）用于快速捕捉灾难，长窗口（1 小时）低倍率（6×）用于捕捉持续的小幅劣化。两者取或。单一窗口要么太敏感（一个瞬时抖动就告警）要么太迟钝（缓慢劣化发现不了）。这是 Google SRE Book 第 5 章给出的标准配方。",
        ),
        CALLOUT("danger", "<p>自动回滚有一个必须防的失败模式：<strong>回滚风暴</strong>。如果回滚判据太敏感，一次瞬时抖动就触发回滚；回滚本身又是一次变更，可能再次触发判据；系统在两个版本间来回横跳，比不回滚更糟。防护措施：<em>①回滚后强制冷却期</em>（如 30 分钟内不再自动发布）；<em>②回滚次数上限</em>（同一天自动回滚 2 次后转人工）；<em>③判据要求持续性</em>（不是「某一刻超阈值」而是「连续 N 个窗口超阈值」）。这三条缺一不可。</p>", "防回滚风暴"),
    ])),
    ("ledger", "算一笔账：发布策略的真实成本对比", "".join([
        P("把四种策略在同一场景下的账并排放。场景：13 副本、每副本 2 卡、$4/卡·h、一次发布、假设新版本有 bug（错误率 5%）。"),
        TABLE(["策略", "额外资源成本", "受影响请求比例 × 时长", "错误预算消耗", "总代价"], [
            ["Recreate", "$0", "100% × 15 min（含停机）", "15.0 min", "<strong>最差</strong>"],
            ["RollingUpdate (25%)", "3 副本 × 15 min ≈ $6", "渐进 0→100%，均值 50% × 15 min", "7.5 min", "中"],
            ["Blue-Green", "13 副本 × 20 min ≈ $35", "100% × 3 min（发现即切回）", "3.0 min", "低（但贵）"],
            ["Canary (5%→自动分析)", "1 副本 × 25 min ≈ $3", "5% × 8 min", "<strong>0.4 min</strong>", "<strong>最优</strong>"],
        ]),
        P("金丝雀在这个对比里几乎是碾压性的：<strong>额外成本最低（只多一个副本），错误预算消耗最低（比 Recreate 少 37 倍）</strong>。它唯一的代价是<em>工程复杂度</em>——需要能按权重分流的网关、需要自动分析的指标管线、需要定义判据。这些是一次性投入，之后每次发布都受益。"),
        P("再算自动扩缩的账。假设日流量曲线波峰 200 QPS、波谷 20 QPS（10:1），单副本 μ=2.5，目标 ρ=0.7："),
        UL([
            "<strong>固定容量</strong>（按峰值配）：<code>⌈200/(2.5×0.7)⌉ = 115</code> 副本全天候 → 230 卡 × $4 × 720h = <strong>$662,400/月</strong>",
            "<strong>自动扩缩</strong>（假设平均需求 ≈ 峰值的 40%）：约 46 副本平均 → <strong>$265,000/月</strong>，省 60%",
            "<strong>但要加上</strong>：热备 4 副本（$23,000）+ 震荡带来的超配（约 10%）→ 实际约 <strong>$315,000/月</strong>，仍省约 52%",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>发布与扩缩都是「用确定的小成本，买不确定的大风险的下界」——而且这两件事的最优解都取决于一个你在模块 01 就决定了的数字：冷启动时间</strong>。冷启动快，则滚动更新的凹陷窄、金丝雀迭代快、扩容跟得上、热备可以少养；冷启动慢，则每一项都变难变贵。<em>部署链路的上游决策，会以你意想不到的方式支配下游的全部经济性。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>LLM 质量指标的在线检测</strong>：系统指标秒级可判，质量指标却需要人工或 LLM-judge、成本高延迟大。如何用廉价代理指标（输出长度分布、拒答率、重试率、logprob 分布漂移）在线近似质量劣化，且给出可靠的统计判据，是当前最缺工具的一环。",
            "<strong>always-valid inference 的工程化</strong>：置信序列（confidence sequences）、e-value、SPRT 在理论上完美解决了 peeking 问题，但主流发布工具（Flagger、Argo Rollouts）默认仍是固定窗口 + 简单阈值。把序贯方法做进发布流水线、并让工程师能理解和调参，仍有距离。",
            "<strong>预测式扩缩</strong>：用时序模型预测未来 T_cold 时间后的流量，提前扩容。难点在预测误差的<em>不对称代价</em>（少扩=用户受损、多扩=烧钱）和突发事件的不可预测性。把预测不确定性正确地转化为扩容决策（而不是只用点估计），是个开放的决策论问题。",
            "<strong>模型级别的渐进发布</strong>：不只是「新旧版本按流量分流」，而是「同一个请求，简单的给小模型、难的给大模型」，并渐进调整这个路由。这把发布策略和模型路由（model cascading）融合了，判据也从「哪个版本更好」变成「哪类请求该给谁」。",
            "<strong>无中断的权重热更新</strong>：目前换模型必须换 Pod（几分钟冷启动）。能否在进程内原地替换权重（保留 CUDA 上下文、KV 缓存、编译缓存），把发布从「分钟级 Pod 轮换」变成「秒级权重切换」？技术上可行但工程复杂，正在成为大规模服务的追求目标。",
        ]),
        CALLOUT("paper", "必读：Google SRE Book 第 5 章（多窗口多燃烧率告警的原始配方）与第 27 章（渐进发布）；Argo Rollouts 与 Flagger 的 <em>Analysis</em> 文档（工业界金丝雀判据的实际形态）；Kubernetes HPA 的 <em>Horizontal Pod Autoscaling</em> 官方算法说明（含稳定窗口与 behavior 的精确语义）；Howard & Ramdas 等关于 <em>time-uniform confidence sequences</em> 的工作（peeking 问题的正确解）；KEDA 文档（事件驱动扩缩与 scale-to-zero）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 发布策略与自动扩缩（滚动容量曲线、序贯检验、HPA 震荡，全部从零仿真）

目标：把 **滚动更新的容量凹陷 → 金丝雀判据的统计学 → HPA 控制律与震荡 → 热备容量** 从零写出来，
每个机制都**对拍**朴素参考、每个策略都**算一笔账**。

路线：容量曲线仿真 → peeking 的假阳性灾难 → 序贯检验修复 → HPA 闭环仿真（震荡/阻尼）→ 热备公式 → ✏️ 练习 → 📖 答案 → 🧪 发布策略成本胶囊。

> 心智模型：**发布 = 压小「爆炸半径 × MTTR」；扩缩 = 一个带纯延迟的反馈控制系统**。
> 两者的最优解都被同一个数字支配：**冷启动时间**。"""),
    md("""## 1 · 滚动更新：容量凹陷有多深、多久

`maxUnavailable` 决定凹陷**多深**，`maxSurge` 决定更新**多快**、要多付多少 GPU。
LLM 的新 Pod 要 3 分钟才就绪，所以这个凹陷不是理论问题。"""),
    code("""import math, random
from dataclasses import dataclass, field

def rolling_update(desired, max_unavailable, max_surge, ready_delay_s, tick_s=10, horizon_s=1800):
    '''仿真滚动更新，返回每个时刻的 (可用旧副本+可用新副本) 列表。'''
    old_ready, new_pending, new_ready = desired, [], 0
    avail_trace, total_trace, t = [], [], 0
    while t < horizon_s and (old_ready > 0 or new_ready < desired):
        # 新 Pod 到点就绪
        arrived = [p for p in new_pending if p <= t]
        new_pending = [p for p in new_pending if p > t]
        new_ready += len(arrived)
        avail = old_ready + new_ready
        total = old_ready + new_ready + len(new_pending)
        # 摘旧：在不违反 maxUnavailable 的前提下
        while old_ready > 0 and avail - 1 >= desired - max_unavailable and new_ready + old_ready > desired - max_unavailable:
            if new_ready + old_ready - 1 < desired - max_unavailable:
                break
            old_ready -= 1; avail -= 1; total -= 1
            if new_ready >= desired: break
        # 起新：在不违反 maxSurge 的前提下
        while total < desired + max_surge and new_ready + len(new_pending) < desired:
            new_pending.append(t + ready_delay_s); total += 1
        avail_trace.append(avail); total_trace.append(total)
        t += tick_s
    return avail_trace, total_trace, t

DESIRED, READY_DELAY = 13, 180
for mu_, ms_ in [(3, 3), (0, 3), (0, 1), (3, 0)]:
    av, tot, dur = rolling_update(DESIRED, mu_, ms_, READY_DELAY)
    print(f'maxUnavailable={mu_}, maxSurge={ms_}: '
          f'最深容量 {min(av):>3d}/{DESIRED}, 峰值占用 {max(tot):>3d}, 更新耗时 {dur/60:>5.1f} 分钟')

av0, _, dur0 = rolling_update(DESIRED, 0, 3, READY_DELAY)
av3, _, dur3 = rolling_update(DESIRED, 3, 3, READY_DELAY)
assert min(av0) >= DESIRED, 'maxUnavailable=0 时容量不应下探'
assert min(av3) < DESIRED,  'maxUnavailable=3 时容量会下探'
print('\\n✅ maxUnavailable=0 是 LLM 服务的标准做法：容量永不下探，代价是必须有 maxSurge 的空闲卡')"""),
    md("""### maxSurge 的定价：付多少张卡换多快的更新"""),
    code("""print(f"{'maxSurge':>9s} {'更新耗时(min)':>14s} {'额外GPU·小时':>14s} {'额外成本$':>11s}")
GPU_PER_REPLICA, GPU_HOURLY = 2, 4.0
rows = []
for ms_ in [1, 2, 3, 5, 8, 13]:
    av, tot, dur = rolling_update(DESIRED, 0, ms_, READY_DELAY)
    extra_gpu_h = ms_ * GPU_PER_REPLICA * (dur / 3600)
    rows.append((ms_, dur / 60, extra_gpu_h * GPU_HOURLY))
    print(f'{ms_:>9d} {dur/60:>14.1f} {extra_gpu_h:>14.2f} {extra_gpu_h*GPU_HOURLY:>11.2f}')

durs = [r[1] for r in rows]
assert durs == sorted(durs, reverse=True), 'maxSurge 越大更新越快'
assert rows[0][1] > 3 * rows[-1][1], 'maxSurge=1（串行）应比全量并行慢 3 倍以上'
print(f'\\n✅ maxSurge 1→13: 更新从 {rows[0][1]:.0f} 分钟压到 {rows[-1][1]:.0f} 分钟，'
      f'额外成本仅 ${rows[-1][2]:.1f}。')
print('   更新速度在这里是**极其便宜**的 —— 前提是集群有空闲卡放得下 surge。')"""),
    md("""## 2 · 金丝雀判据的统计学：peeking 会毁掉你的判断

金丝雀天然是「持续监控、随时可能叫停」= **反复做检验**。
固定样本量的 p 值在反复偷看下会严重膨胀假阳性率。先把灾难跑出来。"""),
    code("""def two_prop_z(x1, n1, x2, n2):
    '''两比例 z 检验，返回 |z|。'''
    if n1 == 0 or n2 == 0: return 0.0
    p1, p2 = x1/n1, x2/n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1-p) * (1/n1 + 1/n2))
    return 0.0 if se == 0 else abs(p1 - p2) / se

def naive_peeking_trial(err_rate_base, err_rate_canary, n_total=4000, peek_every=100, z_crit=1.96, seed=0):
    '''模拟一次金丝雀：每 peek_every 个样本看一次，一旦 |z|>z_crit 就叫停。'''
    rng = random.Random(seed)
    x1 = x2 = n1 = n2 = 0
    for i in range(1, n_total + 1):
        n1 += 1; x1 += rng.random() < err_rate_base
        n2 += 1; x2 += rng.random() < err_rate_canary
        if i % peek_every == 0 and two_prop_z(x1, n1, x2, n2) > z_crit:
            return True          # 叫停（判定为「有差异」）
    return False

# A/A 测试：新旧版本**完全相同**，任何「发现差异」都是假阳性
RATE = 0.01
fp_peek = sum(naive_peeking_trial(RATE, RATE, seed=s) for s in range(500)) / 500
# 对照：只在最后看一次（固定样本量，正确的 5%）
fp_once = sum(naive_peeking_trial(RATE, RATE, peek_every=4000, seed=s) for s in range(500)) / 500
print(f'A/A 测试（两版本完全相同）的假阳性率:')
print(f'  每 100 样本偷看一次: {fp_peek:.1%}   ← 名义上应该是 5%')
print(f'  只在结束时看一次  : {fp_once:.1%}')
assert fp_peek > 2 * fp_once, 'peeking 应显著抬高假阳性率'
print(f'\\n⚠️  偷看把假阳性率抬高了 {fp_peek/max(fp_once,1e-9):.1f} 倍 ——')
print('   意味着大量**完全正常的发布**会被误判为坏版本而自动回滚。')"""),
    md("""### 修复一：序贯概率比检验（SPRT）

SPRT 在**任意停止时刻**都保持名义错误率。它维护一个对数似然比，
越过上界判 H1、越过下界判 H0，中间继续观察。"""),
    code("""def sprt_trial(p0, p1, err_base, err_canary, alpha=0.05, beta=0.20, n_max=4000, seed=0):
    '''SPRT: H0 = 金丝雀错误率 p0（没变差）, H1 = p1（变差了）。
       返回 ('reject_h0' | 'accept_h0' | 'inconclusive', 用了多少样本)。'''
    rng = random.Random(seed)
    A = math.log((1 - beta) / alpha)        # 上界：判 H1
    B = math.log(beta / (1 - alpha))        # 下界：判 H0
    llr = 0.0
    for i in range(1, n_max + 1):
        x = 1 if rng.random() < err_canary else 0
        llr += math.log(p1/p0) if x else math.log((1-p1)/(1-p0))
        if llr >= A: return 'reject_h0', i      # 确认变差 -> 回滚
        if llr <= B: return 'accept_h0', i      # 确认没变差 -> 放行
    return 'inconclusive', n_max

P0, P1 = 0.01, 0.03      # H0: 1% 错误率（正常）; H1: 3%（明显变差）
aa = [sprt_trial(P0, P1, P0, P0, seed=s) for s in range(500)]      # A/A：真的没变差
ab = [sprt_trial(P0, P1, P0, P1, seed=s) for s in range(500)]      # A/B：真的变差了

fp = sum(1 for r, _ in aa if r == 'reject_h0') / len(aa)
tp = sum(1 for r, _ in ab if r == 'reject_h0') / len(ab)
n_ab = sum(n for r, n in ab if r == 'reject_h0') / max(1, sum(1 for r, _ in ab if r == 'reject_h0'))
print(f'SPRT（允许任意时刻停止）:')
print(f'  A/A 假阳性率 {fp:.1%}  (名义 α=5%)')
print(f'  A/B 检出率   {tp:.1%}  (名义 1-β=80%)')
print(f'  检出坏版本平均只需 {n_ab:.0f} 个样本')
assert fp < 0.10, f'SPRT 应把假阳性控制在名义水平附近，得到 {fp:.1%}'
assert tp > 0.75, f'SPRT 应有足够检出力，得到 {tp:.1%}'
assert fp < fp_peek, 'SPRT 的假阳性应远低于朴素 peeking'
print(f'\\n✅ SPRT 把假阳性从 {fp_peek:.0%} 压回 {fp:.0%}，同时保留了「随时可以停」的能力')"""),
    md("""### 修复二：质量指标要用**非劣性**检验

发布要问的不是「新版本更好吗」，而是「**新版本会不会更差**」。
非劣性检验把原假设设成「差了至少 δ」，拒绝它才放行。"""),
    code("""def non_inferiority(wins_new, n, delta=0.05, z_crit=1.645):
    '''检验 H0: p <= 0.5 - delta（新版本明显更差） vs H1: p > 0.5 - delta。
       返回 (是否通过, z)。'''
    p = wins_new / n
    p0 = 0.5 - delta
    se = math.sqrt(p0 * (1 - p0) / n)
    z = (p - p0) / se
    return z > z_crit, z

for wins, n, label in [(500, 1000, '完全打平 (50%)'),
                       (470, 1000, '略差 (47%)'),
                       (430, 1000, '明显更差 (43%)'),
                       (48,  100,  '打平但样本太少')]:
    ok, z = non_inferiority(wins, n, delta=0.05)
    print(f'{label:<20s} 胜率 {wins/n:>5.1%}  z={z:>6.2f}  -> {"放行 ✅" if ok else "拦截 ❌"}')

assert non_inferiority(500, 1000)[0],  '打平应放行'
assert not non_inferiority(430, 1000)[0], '明显更差应拦截'
assert not non_inferiority(48, 100)[0], '样本太少时应拦截（不是「没发现问题」就放行）'
print('\\n✅ 关键：样本不足时非劣性检验会**拦截**，而普通显著性检验会「没发现差异」而放行。')
print('   这个方向的翻转，是发布决策与科研检验最本质的区别。')"""),
    md("""## 3 · HPA：控制律、纯延迟与震荡

$$R_{desired} = \\lceil R_{current} \\times M_{current} / M_{target} \\rceil$$

带纯延迟的反馈系统会震荡。先把震荡跑出来，再用**稳定窗口**把它阻尼掉。"""),
    code("""def hpa_sim(traffic, mu=2.5, target_util=0.7, cold_start_ticks=12,
            count_pending=False, tolerance=0.0, stabilize_down_ticks=0,
            max_scale_down_frac=1.0, max_scale_up_frac=None, r0=8):
    '''闭环仿真。traffic: 每 tick 的 QPS 序列。返回 (副本轨迹, 过载 tick 数)。
       count_pending=False 复现最常见的失稳来源：**控制器无视正在启动的副本，持续重复下单**。'''
    ready, pending = r0, []            # pending: [就绪时刻]
    recent_desired, trace, overload = [], [], 0
    for t, lam in enumerate(traffic):
        arrived = [p for p in pending if p <= t]
        pending = [p for p in pending if p > t]
        ready += len(arrived)
        capacity = ready * mu
        util = lam / capacity if capacity else 10.0
        if util > 1.0:
            overload += 1
        ratio = util / target_util
        desired = ready if abs(ratio - 1.0) <= tolerance else math.ceil(ready * ratio)
        desired = max(1, desired)
        recent_desired.append(desired)
        # 已在路上的副本算不算数？这一行就是稳定与失稳的分水岭
        committed = ready + len(pending) if count_pending else ready
        if desired > committed:                                   # 扩容：立刻
            add = desired - committed
            if max_scale_up_frac is not None:
                add = min(add, max(1, math.ceil(ready * max_scale_up_frac)))
            for _ in range(add):
                pending.append(t + cold_start_ticks)
        elif desired < ready:                                     # 缩容：看稳定窗口
            safe = max(recent_desired[-(stabilize_down_ticks + 1):])
            if safe < ready:
                floor_ = math.ceil(ready * (1 - max_scale_down_frac))
                ready = max(1, max(safe, floor_))
        trace.append(ready + len(pending))
    return trace, overload

# 阶跃流量：20 QPS 突然涨到 100 QPS，再回落
traffic = [20]*20 + [100]*60 + [20]*40
naive,  ov_n = hpa_sim(traffic, count_pending=False, tolerance=0.0,
                       stabilize_down_ticks=0, max_scale_down_frac=1.0)
damped, ov_d = hpa_sim(traffic, count_pending=True, tolerance=0.10,
                       stabilize_down_ticks=20, max_scale_down_frac=0.10,
                       max_scale_up_frac=1.0)

def oscillation(tr):
    return sum(abs(tr[i] - tr[i-1]) for i in range(1, len(tr)))   # 总变动量

need = math.ceil(100 / (2.5 * 0.7))       # 峰值真正需要的副本数
print(f'峰值真实需求 = {need} 副本\\n')
print(f'{"配置":<30s} {"峰值副本":>8s} {"总变动量":>9s} {"过载tick":>9s}')
print(f'{"无视 pending / 无容差 / 无窗口":<30s} {max(naive):>8d} {oscillation(naive):>9d} {ov_n:>9d}')
print(f'{"计入 pending+容差+窗口+限速":<30s} {max(damped):>8d} {oscillation(damped):>9d} {ov_d:>9d}')

assert max(naive) > 2 * need, f'朴素控制器应严重过冲（需要 {need}，下单 {max(naive)}）'
assert max(damped) < max(naive), '阻尼配置的过冲应明显更小'
assert oscillation(damped) < oscillation(naive), '阻尼配置应显著降低总变动量'
print(f'\\n✅ 朴素控制器把 {need} 个副本的需求下成了 {max(naive)} 个 —— 因为它在冷启动的 3 分钟里'
      f'\\n   一直看到「容量不足」，于是每个采样周期都重复下单。这就是经典的**积分饱和**。')
print(f'   计入 pending + 容差带 + 稳定窗口 + 限速后，过冲降到 {max(damped)}，'
      f'总变动量降低 {(1-oscillation(damped)/oscillation(naive)):.0%}')"""),
    md("""### 冷启动是震荡的放大器

同样的控制器，冷启动越长越不稳定 —— 这是纯延迟反馈系统的普遍规律。"""),
    code("""print(f"{'冷启动(s)':>10s} {'峰值副本':>8s} {'总变动量':>9s} {'过载tick':>9s}")
prev_osc = 0
for cs_ticks in [1, 4, 12, 24]:      # tick=15s -> 15s / 60s / 180s / 360s
    tr, ov = hpa_sim(traffic, cold_start_ticks=cs_ticks, stabilize_down_ticks=0)
    print(f'{cs_ticks*15:>10d} {max(tr):>8d} {oscillation(tr):>9d} {ov:>9d}')
    if cs_ticks == 1: prev_osc = oscillation(tr)

tr_fast, ov_fast = hpa_sim(traffic, cold_start_ticks=1,  stabilize_down_ticks=0)
tr_slow, ov_slow = hpa_sim(traffic, cold_start_ticks=24, stabilize_down_ticks=0)
assert max(tr_slow) > max(tr_fast), '冷启动越长，过冲越严重'
assert ov_slow > ov_fast, '冷启动越长，过载时间越久'
print(f'\\n✅ 冷启动 15s vs 360s：峰值副本 {max(tr_fast)} -> {max(tr_slow)}，'
      f'过载时长 {ov_fast} -> {ov_slow} tick')
print('   **模块 01 压缩的每一秒冷启动，都在这里变成更稳的扩缩和更少的超配。**')"""),
    md("""## 4 · 热备容量：反应式扩容够不够？

$$R_{buffer} \\ge \\frac{1}{\\mu}\\cdot\\frac{d\\lambda}{dt}\\cdot T_{cold}$$

这个公式回答一个很实际的问题：**要养几个空闲副本，才能在扩容生效前撑住**。"""),
    code("""def buffer_replicas(dlambda_dt, t_cold_s, mu):
    return math.ceil(dlambda_dt * t_cold_s / mu)

print(f"{'场景':<22s} {'dλ/dt':>8s} {'T_cold':>8s} {'需要热备':>9s} {'月成本$':>10s}")
GPU_PER_REPLICA, GPU_HOURLY, MU = 2, 4.0, 2.5
for name, rate, tc in [('平缓日周期', 0.05, 180), ('中等推广', 0.5, 180),
                       ('营销开闸', 2.0, 180), ('营销开闸(冷启动30s)', 2.0, 30)]:
    b = buffer_replicas(rate, tc, MU)
    cost = b * GPU_PER_REPLICA * GPU_HOURLY * 24 * 30
    print(f'{name:<22s} {rate:>8.2f} {tc:>8d} {b:>9d} {cost:>10,.0f}')

b180 = buffer_replicas(2.0, 180, MU)
b30  = buffer_replicas(2.0, 30,  MU)
assert b180 == 6 * b30, '冷启动缩短 6 倍，热备需求也降到 1/6'
assert b180 > 100, '陡峭尖峰下热备需求不现实 —— 说明必须换手段'
print(f'\\n✅ 两条结论：')
print(f'   ① 陡峭尖峰（{b180} 个热备）靠热备买不起 -> 必须预约扩容 / 限流降级 / 上游整形。')
print(f'   ② 冷启动是热备成本的**乘数**：180s->30s 让热备从 {b180} 降到 {b30} 个。')"""),
    md("""## ✏️ 练习 1：错误预算燃烧率与自动回滚

实现 `burn_rate(error_rate, slo)` 和 `rollback_decision(burn, windows_exceeded, cooldown_active)`。
- `burn_rate = error_rate / (1 - slo)`
- 回滚规则：`cooldown_active` 为真 → 永不自动回滚（返回 `'manual'`）；
  否则 `burn >= 100 且 windows_exceeded >= 2` → `'auto_rollback'`；
  `burn >= 14.4` → `'page'`；`burn >= 6` → `'alert'`；否则 `'ok'`。"""),
    code("""def burn_rate(error_rate, slo):
    # TODO
    raise NotImplementedError

def rollback_decision(burn, windows_exceeded, cooldown_active):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
assert abs(burn_rate(0.01, 0.999) - 10.0) < 1e-9, '1% 错误率 / 0.1% 预算 = 10 倍'
assert abs(burn_rate(0.01, 0.99) - 1.0) < 1e-9,   '同样 1%，对 99% SLO 只是 1 倍'
assert rollback_decision(150, 2, False) == 'auto_rollback'
assert rollback_decision(150, 1, False) == 'page', '只超一个窗口不自动回滚（防抖）'
assert rollback_decision(150, 5, True)  == 'manual', '冷却期内绝不自动回滚（防回滚风暴）'
assert rollback_decision(20, 3, False)  == 'page'
assert rollback_decision(8,  3, False)  == 'alert'
assert rollback_decision(1,  9, False)  == 'ok'
print('✅ 练习 1 通过：burn rate 把阈值归一化到 SLO，一套规则适配所有服务')"""),
    md("""## ✏️ 练习 2：金丝雀阶段规划

实现 `canary_plan(stages, qps, min_samples)`：`stages` 是 `[(流量比例, 计划分钟数), ...]`。
对每个阶段计算实际样本量 `qps * 60 * minutes * frac`；
若不足 `min_samples`，**延长该阶段**到刚好够（分钟数向上取整）。
返回 `[(frac, actual_minutes, samples), ...]`。"""),
    code("""def canary_plan(stages, qps, min_samples):
    # TODO: 对每个 (frac, minutes)：
    #   need_min = ceil(min_samples / (qps*60*frac))；actual = max(minutes, need_min)
    #   samples = int(qps*60*actual*frac)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
plan = canary_plan([(0.01, 5), (0.05, 10), (0.25, 20)], qps=50, min_samples=1000)
for frac, mins, n in plan:
    print(f'  {frac:>5.0%} 流量, {mins:>3d} 分钟, {n:>7,d} 样本')
assert all(n >= 1000 for _, _, n in plan), '每个阶段都必须达到最小样本量'
assert plan[0][1] > 5, '1% 流量 × 50 QPS，5 分钟只有 150 个样本，必须延长'
assert plan[2][1] == 20, '25% 流量下 20 分钟已足够，不该延长'
total_min = sum(m for _, m, _ in plan)
print(f'总耗时 {total_min} 分钟')
assert total_min > 35, '样本量约束会让金丝雀比「计划表」更慢 —— 这是对的'
print('✅ 练习 2 通过：金丝雀的真实时长由**样本量**决定，不是由计划表决定')"""),
    md("""## ✏️ 练习 3：HPA 的期望副本数

实现 `hpa_desired(current_replicas, current_metric, target_metric, tolerance=0.1,
min_r=1, max_r=100)`：按 K8s 原始算法返回期望副本数。
规则：`ratio = current/target`；若 `|ratio - 1| <= tolerance` 返回 `current_replicas`（死区）；
否则 `ceil(current_replicas * ratio)`，最后夹到 `[min_r, max_r]`。"""),
    code("""def hpa_desired(current_replicas, current_metric, target_metric, tolerance=0.1, min_r=1, max_r=100):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert hpa_desired(10, 0.70, 0.70) == 10, '正中目标：不动'
assert hpa_desired(10, 0.73, 0.70) == 10, '偏差 4% 在容差带内：不动'
assert hpa_desired(10, 0.90, 0.70) == 13, 'ceil(10 * 0.9/0.7) = 13'
assert hpa_desired(10, 0.35, 0.70) == 5,  '利用率减半 -> 副本减半'
assert hpa_desired(10, 0.01, 0.70, min_r=2) == 2, '受 minReplicas 约束'
assert hpa_desired(10, 9.99, 0.70, max_r=50) == 50, '受 maxReplicas 约束'
# 容差带的价值：在目标附近抖动时不产生动作
noisy = [hpa_desired(10, 0.70 + d, 0.70) for d in (-0.05, -0.02, 0.02, 0.05)]
assert all(r == 10 for r in noisy), '目标附近的噪声不应触发扩缩'
print('✅ 练习 3 通过：容差带（死区）是 HPA 稳定性的第一道保险')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def burn_rate(error_rate, slo):
    return error_rate / (1 - slo)

def rollback_decision(burn, windows_exceeded, cooldown_active):
    if cooldown_active:                             return 'manual'
    if burn >= 100 and windows_exceeded >= 2:       return 'auto_rollback'
    if burn >= 14.4:                                return 'page'
    if burn >= 6:                                   return 'alert'
    return 'ok'"""),
    code("""# 练习 2 参考答案
def canary_plan(stages, qps, min_samples):
    out = []
    for frac, minutes in stages:
        need_min = math.ceil(min_samples / (qps * 60 * frac))
        actual = max(minutes, need_min)
        out.append((frac, actual, int(qps * 60 * actual * frac)))
    return out"""),
    code("""# 练习 3 参考答案
def hpa_desired(current_replicas, current_metric, target_metric, tolerance=0.1, min_r=1, max_r=100):
    ratio = current_metric / target_metric
    if abs(ratio - 1.0) <= tolerance:
        return current_replicas
    return max(min_r, min(max_r, math.ceil(current_replicas * ratio)))"""),
    md("""---
## 🧪 真实数据胶囊：四种发布策略的总代价

场景：13 副本 × 2 卡 × $4/卡·h，新版本有 bug（错误率 5%），SLO=99.9%。
把「额外资源成本」与「错误预算消耗」放在一张表上比。"""),
    code("""REPLICAS, GPU_PER_REPLICA, GPU_HOURLY, SLO = 13, 2, 4.0, 0.999
BUDGET_MIN = (1 - SLO) * 30 * 24 * 60      # 月度错误预算（分钟）

def strategy_cost(extra_replicas, duration_min, affected_frac, impact_min):
    gpu_cost = extra_replicas * GPU_PER_REPLICA * GPU_HOURLY * (duration_min / 60)
    budget_min = affected_frac * impact_min
    return gpu_cost, budget_min, budget_min / BUDGET_MIN

strategies = [
    ('Recreate',            0,        15, 1.00, 15),
    ('RollingUpdate 25%',   3,        15, 0.50, 15),
    ('Blue-Green',          REPLICAS, 20, 1.00, 3),
    ('Canary 5% + 自动分析', 1,        25, 0.05, 8),
]
print(f'月度错误预算: {BUDGET_MIN:.1f} 分钟\\n')
print(f"{'策略':<22s} {'额外$':>8s} {'预算消耗(min)':>14s} {'占月度预算':>11s}")
res = {}
for name, er, dm, af, im in strategies:
    g, b, pct = strategy_cost(er, dm, af, im)
    res[name] = (g, b)
    print(f'{name:<22s} {g:>8.2f} {b:>14.2f} {pct:>10.1%}')

canary_g, canary_b = res['Canary 5% + 自动分析']
recreate_b = res['Recreate'][1]
bg_g = res['Blue-Green'][0]
assert canary_b < recreate_b / 20, '金丝雀的预算消耗应比 Recreate 低一个数量级以上'
assert canary_g < bg_g / 5, '金丝雀的额外资源成本应远低于蓝绿'
print(f'\\n✅ 金丝雀：预算消耗比 Recreate 低 {recreate_b/canary_b:.0f} 倍，'
      f'额外成本比蓝绿低 {bg_g/canary_g:.0f} 倍。')
print('   它唯一的代价是**工程复杂度**（按权重分流的网关 + 自动分析管线）——一次投入，长期受益。')"""),
    md("""**🧪 胶囊练习**：实现 `autoscale_savings(peak_qps, trough_qps, mu, target_rho, hours_at_peak)`：
对比「按峰值固定容量」与「自动扩缩」的月成本。
自动扩缩假设：峰值时段用峰值副本、其余时段用波谷副本。
返回 `(fixed_monthly, autoscale_monthly, saving_frac)`。"""),
    code("""def autoscale_savings(peak_qps, trough_qps, mu, target_rho, hours_at_peak):
    # TODO: r_peak = ceil(peak/(mu*rho)); r_trough = ceil(trough/(mu*rho))
    #   fixed = r_peak * GPU_PER_REPLICA * GPU_HOURLY * 24 * 30
    #   auto  = (r_peak*hours_at_peak + r_trough*(24-hours_at_peak)) * GPU_PER_REPLICA * GPU_HOURLY * 30
    #   返回 (fixed, auto, 1 - auto/fixed)
    raise NotImplementedError"""),
    code("""# 自测
fixed, auto, saving = autoscale_savings(200, 20, mu=2.5, target_rho=0.7, hours_at_peak=8)
print(f'固定容量 ${fixed:>10,.0f}/月')
print(f'自动扩缩 ${auto:>10,.0f}/月')
print(f'节省 {saving:.1%}')
assert auto < fixed, '自动扩缩应更便宜'
assert 0.4 < saving < 0.8, f'10:1 的日夜比应省 40%~80%，得到 {saving:.1%}'
# 波峰波谷差距小时，收益也小
_, _, small = autoscale_savings(100, 80, 2.5, 0.7, 8)
assert small < saving / 3, '流量曲线越平，自动扩缩越不值得做'
print(f'\\n对比：日夜比 10:1 省 {saving:.0%}；日夜比 1.25:1 只省 {small:.0%}')
print('✅ 胶囊练习通过：**先看流量曲线，再决定要不要上自动扩缩**')"""),
    code("""# 📖 胶囊参考答案
def autoscale_savings(peak_qps, trough_qps, mu, target_rho, hours_at_peak):
    r_peak   = math.ceil(peak_qps   / (mu * target_rho))
    r_trough = math.ceil(trough_qps / (mu * target_rho))
    unit = GPU_PER_REPLICA * GPU_HOURLY
    fixed = r_peak * unit * 24 * 30
    auto  = (r_peak * hours_at_peak + r_trough * (24 - hours_at_peak)) * unit * 30
    return fixed, auto, 1 - auto / fixed"""),
    md("""---
## 🔧 旁注：真实系统里这些对应什么

- **滚动更新参数** → `spec.strategy.rollingUpdate.{maxSurge,maxUnavailable}`；LLM 服务标准配置是 `maxUnavailable: 0`。
- **金丝雀 + 自动分析** → Argo Rollouts 的 `Rollout` + `AnalysisTemplate`，或 Flagger 的 `Canary` CRD。判据写成 Prometheus 查询。
- **序贯检验** → 目前主流工具还没内置；实践中的近似是「多窗口 + 要求连续 N 次超阈值」。要严格做需自己实现 analysis provider。
- **非劣性检验** → 离线评测管线（C03/C10）的判据，在发布流水线里作为质量门禁。
- **HPA 控制律** → `autoscaling/v2` 的 `HorizontalPodAutoscaler`，`behavior.scaleDown.stabilizationWindowSeconds: 300` 是默认阻尼。
- **按队列深度扩缩** → KEDA 的 `ScaledObject`（支持 Prometheus/Kafka/SQS 等外部触发器），原生 HPA 需配 prometheus-adapter。
- **burn rate 告警** → Prometheus 多窗口多燃烧率规则；Sloth / Pyrra 能从 SLO 定义自动生成这些规则。

你在这里仿真出的震荡曲线，和真实集群 `kubectl get hpa -w` 看到的副本数抖动是同一个现象。"""),
    md("""### 小结
- 发布的全部目的是压小 **爆炸半径 × MTTR**；先压爆炸半径（便宜、收益大），再压 MTTR。
- **maxUnavailable=0** 是 LLM 服务的标准配置（容量永不下探）；maxSurge 是「用少量 GPU 买更新速度」的极便宜交易。
- 金丝雀判据必须处理 **peeking**：朴素反复检验会把假阳性率抬到 20%+，SPRT 能压回名义水平；质量指标要用**非劣性**检验（样本不足时应拦截而非放行）。
- HPA 是带纯延迟的比例控制器，**冷启动是震荡的放大器**；用稳定窗口+容差带+缩容限速阻尼，用**队列深度**（领先指标）而非 GPU 利用率或延迟（滞后指标）触发。
- **热备容量 = dλ/dt × T_cold / μ**：陡峭尖峰买不起热备，必须预约扩容/限流降级；而冷启动是这笔账的乘数。
- 自动回滚由 **burn rate** 驱动，并且必须有冷却期与次数上限来防回滚风暴。

下一站：**模块 05 · 云平台、集群调度与成本** —— 这一切跑在谁家的机器上，一个月到底多少钱？"""),
]
