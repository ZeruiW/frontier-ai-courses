# -*- coding: utf-8 -*-
"""C55 模块 03 · 失效模式全景：TSR 到底在哪些地方出错。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–02（TSR 任务定义、数据集、两级 vs 端到端）；C18/C53 的检测基础"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_failure_modes.ipynb'),
    ("核心参考", "TT100K / Mapillary 的失效分析、TIDE 误差分解、FMEA 风险优先数、大气散射与卷帘快门模型"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("quadrant", "四象限框架：先把「错了」拆成四种不同的错", "".join([
        P("「模型识别得不准」是一句没有信息量的话。<strong>做失效分析的第一步，是把「错」拆成互不重叠、下游后果不同、修复手段也不同的几类。</strong>检测任务天然有四种错法——它们的成因、代价、对策几乎没有交集，混在一起谈必然得不出行动项。"),
        ASCII("""                        真实世界有这块牌吗？
                          有                 没有
                    ┌──────────────────┬──────────────────┐
   模型报了吗？ 报了 │  ✅ 正确检出      │  ② 误检 FP       │
                    │  （但可能错分/     │  「凭空多出一块牌」│
                    │    定位不准）      │                  │
                    ├──────────────────┼──────────────────┤
              没报  │  ① 漏检 FN        │  ✅ 正确忽略      │
                    │ 「牌在那，没看见」 │                  │
                    └──────────────────┴──────────────────┘

   在「✅ 正确检出」这一格里，还藏着两种错：
     ③ 错分 (misclassification)：框对了，类别错了（限速 60 判成 80）
     ④ 定位不准 (poor localization)：类别对了，框偏了 / 尺度错了
        → 直接影响距离估计 → 影响「什么时候开始生效」

   注意：**这四类的下游后果完全不同**，所以不能用一个 mAP 概括。""")
        ,
        TABLE(["象限", "定义", "下游后果（规控 / VLA 视角）", "典型量级"], [
            ["<strong>① 漏检 FN</strong>",
             "真实标志存在，模型未输出（或分数低于阈值被滤掉）",
             "<strong>最危险</strong>。限速牌漏检 → 超速；停车让行漏检 → 冲入路口。<em>而且是「静默失败」——系统不知道自己漏了</em>",
             "远距离段（&gt;60 m）漏检率可达 30–60%；近距离通常 &lt; 2%"],
            ["<strong>② 误检 FP</strong>",
             "无标志处输出了标志（广告牌、车身贴纸、路面反光）",
             "急减速、幽灵刹车（phantom braking）；用户信任崩塌；<em>但至少是「可观测」的失败——用户会投诉</em>",
             "工程指标要看 <strong>FP/km</strong> 而不是 precision。量产要求常在 0.05–0.5 次/km"],
            ["<strong>③ 错分</strong>",
             "框正确但类别错误",
             "取决于错成什么。限速 60→80 是安全事故；限速 60→40 是体验问题；禁令→指示是行为错误",
             "混淆高度集中在少数「相似对」上（数字类、同形状同色类）"],
            ["<strong>④ 定位不准</strong>",
             "IoU 偏低、尺度估计错、中心偏移",
             "<strong>距离估计错</strong>（尺寸→距离的反演对框宽极敏感）→ 生效时机错；跟踪关联失败 → 时序确认变慢",
             "小目标上 2 px 偏移就能让 IoU 从 1.0 掉到 0.39"],
        ]),
        DUAL(
            "四象限最重要的价值不是分类本身，而是<strong>它强迫你回答「这次改动修的是哪一类」</strong>。提高检测阈值会减少 ②、增加 ①；加更多小目标增强会减少 ①、可能增加 ②；改分类器只动 ③。<em>如果一个改动同时声称「减少漏检又减少误检」，它要么是真的架构改进，要么是评测有问题——多数情况下是后者。</em>",
            "更严格的做法是做<span class=\"term\">error decomposition</span>（误差分解）：把 mAP 的损失按 <em>Cls / Loc / Both / Dupe / Bkg / Miss</em> 六类归因，并算出「修好每一类能涨多少 mAP」——这是 TIDE 的做法（C61 模块 02 会完整实现）。<strong>它把「我该做什么」从争论变成计算。</strong>在 TSR 上做 TIDE 分解，通常会看到一个高度不均衡的结果：<em>Miss（漏检）在远距离桶里占绝对主导，而 Cls（错分）集中在少数几对相似类上</em>——这两条结论直接决定了后面几节的重点。",
        ),
        CALLOUT("danger", "<p>四象限里最容易被忽视的是 <strong>①「静默失败」这个性质</strong>。误检会被用户投诉、会在日志里留下高分记录；<em>漏检什么都不会留下</em>——没有框、没有分数、没有日志条目。你只有拿到带标注的回归集，才知道自己漏了。</p><p><strong>工程含义：漏检必须靠「主动构造的场景化回归集」来监控，不能靠线上指标。</strong>而误检可以靠线上 FP/km 直接监控。这两类失效的<em>可观测性</em>完全不同，因此监控体系也必须不同——这是模块 05 评测体系的核心动机之一。</p>", "漏检是静默失败"),
    ])),

    ("distance", "失效源 1：远距离小目标——先算出物理下界，再谈模型", "".join([
        P("TSR 最大的单一失效源。而它有一个必须先算清楚的前提：<strong>有些距离上的失败不是模型的错，是像素不够。</strong>不先把这条物理下界画出来，你会把大量精力浪费在「优化一个信息论上不可能的任务」上。"),
        MATH("p \\;=\\; f_{px} \\cdot \\frac{S}{Z}, \\qquad f_{px} \\;=\\; \\frac{W_{px}}{2\\tan(\\mathrm{FOV}/2)}"),
        P("其中 <code>p</code> 是标志在图像上的像素边长，<code>S</code> 是标志物理尺寸（米），<code>Z</code> 是距离（米），<code>f_px</code> 是以像素为单位的焦距。代入一组真实参数（1920×1080、水平 FOV 60°、限速牌直径 0.6 m）："),
        TABLE(["距离 Z", "像素边长 p", "能做什么", "主要失效"], [
            ["20 m", "约 50 px", "轻松检出 + 可靠分类", "几乎无失效（除非遮挡）"],
            ["40 m", "约 25 px", "可检出，分类开始吃力", "相似数字混淆开始出现"],
            ["<strong>60 m</strong>", "<strong>约 17 px</strong>", "检出勉强，分类需要高分辨率 crop", "<strong>漏检率明显抬头</strong>"],
            ["80 m", "约 12 px", "检出困难；限速数字几乎不可读", "漏检 + 错分同时恶化"],
            ["100 m", "约 10 px", "<strong>接近信息论下界</strong>", "此距离的失败多数不可修"],
        ]),
        P("再补一个关键的时间账：车速 120 km/h ≈ 33 m/s。<strong>如果 60 m 才检出，你只有 1.8 秒</strong>去完成「多帧确认 → 决策 → 执行」。而多帧确认本身要花 5–8 帧（0.17–0.27 s），留给规控的时间就更少了。<em>这就是为什么「首次检出距离」是 TSR 最重要的工程指标之一（模块 05 会把它做成正式指标）。</em>"),
        TABLE(["成因层次", "具体机制", "对策"], [
            ["<strong>传感器</strong>", "焦距不足、分辨率不足、ISP 在弱纹理小目标上做了过度降噪", "<strong>加长焦相机</strong>（广角负责近距离与大 FOV，长焦负责远距离）；调 ISP 的降噪强度；用 RAW 而非 ISP 后的图训练"],
            ["<strong>模型</strong>", "stride 太大（stride 32 上 16 px 的牌只占 0.5 格）；正样本分配用固定 IoU 阈值 → 小目标几乎分不到正样本", "<strong>加 P2 层（stride 4）</strong>；ATSS/SimOTA 等自适应分配；<strong>NWD</strong> 等对尺度不敏感的度量（详见 C57）"],
            ["<strong>数据</strong>", "训练集中小目标实例少；标注在小尺寸上本身就带噪（±2 px 对 16 px 框是 12% 的相对误差）", "小尺度采样 + Mosaic 制造更多小目标；<strong>copy-paste 稀有小目标</strong>；对极小框做标注复核"],
            ["<strong>推理策略</strong>", "整图一次前向，小目标的相对尺寸太小", "<strong>ROI 裁剪</strong>（只精检消失点附近 / 图像上半部分）；两级级联（低分辨率找 ROI → 高分辨率精检）；SAHI 式切片（车端代价偏高）"],
        ]),
        DUAL(
            "<strong>ROI 裁剪是量产系统里性价比最高的一招，而且几乎没人在论文里写。</strong>交通标志几乎总是出现在图像的特定区域：地平线上方一带、道路两侧、龙门架上。<em>只在这个 ROI 上跑一个高分辨率分支，算力开销可能只有全图的 1/6，却把该区域的有效分辨率翻倍。</em>先验来自车道线、消失点估计，或高精地图。",
            "但要清楚它的失效条件：<strong>ROI 先验错了就是系统性漏检，而且是最难发现的那种</strong>——上坡、下坡、急弯、颠簸时地平线位置会大幅偏移；施工期的临时牌可能放在地面上；匝道汇入处的牌位置不规则。<em>正确做法是 ROI 只用来「分配更多算力」，而不是「排除区域」</em>：全图仍然跑一个低分辨率检测作为兜底，ROI 内额外跑高分辨率。<strong>这个「先验只做加法不做减法」的原则，可以迁移到所有基于先验的加速方案。</strong>",
        ),
        CALLOUT("warn", "一个必须提前建立的判断：<strong>把「不可修的失败」与「可修的失败」分开统计</strong>。100 m 外 10 px 的牌漏检，是物理下界问题，写进 backlog 只会浪费评审时间；而 40 m 处 25 px 的牌漏检，是实实在在的模型问题。<em>做失效分析时，第一件事就是按像素尺寸分桶，把物理下界那一段单独圈出来</em>——否则你的「漏检率 18%」这个数字里，可能有一半是不可修的，导致所有优先级排序都失真。"),
    ])),

    ("occlusion", "失效源 2：遮挡与截断", "".join([
        P("遮挡是第二大失效源，且它有一个让人不舒服的性质：<strong>它无法通过「更好的模型」根本解决</strong>——被树叶盖住一半的限速牌，信息真的少了一半。能做的是让模型在部分信息下仍给出正确判断，并让时序去补齐。"),
        TABLE(["遮挡类型", "典型场景", "特点", "对策"], [
            ["<strong>植被遮挡</strong>", "行道树枝叶在夏季长到牌前", "<strong>季节性</strong>、局部、纹理高频；同一位置的牌在冬天正常、夏天被挡", "训练时合成随机高频遮挡块；<strong>时序累积</strong>（车在移动，遮挡角度变化，总有一帧能看清）；地图先验（这个位置本来就有牌）"],
            ["<strong>车辆遮挡</strong>", "前方大车（卡车/公交）挡住路侧牌", "<strong>大面积、连续多帧</strong>——这是最难的一类，时序也救不了", "换道后重新观测；<strong>依赖地图与车道级先验</strong>；接受「在跟车时降级」并让下游知道（置信度传递）"],
            ["<strong>杆件/结构遮挡</strong>", "龙门架、路灯杆、另一块牌挡住部分", "位置固定、遮挡形状规则", "训练中加入这类样本；<strong>标注规范必须明确「遮挡多少还算有效目标」</strong>"],
            ["<strong>截断</strong>", "牌在图像边缘只露出一部分", "常见于近距离大牌、急弯", "边缘样本单独建桶评测；<strong>不要在训练时无脑丢弃截断样本</strong>——推理时它们真实存在"],
            ["<strong>自遮挡 / 视角</strong>", "牌面与视线夹角大（路口侧向牌、匝道牌）", "透视畸变严重，牌变成窄条", "透视增强（小角度）；<strong>但不要过度</strong>——极端斜视角的牌本来就不该管我方车道（见第 7 节）"],
        ]),
        H3("标注规范：遮挡处的隐形分歧"),
        P("<strong>遮挡最大的坑不在模型，在标注规范。</strong>「牌被挡住 60% 还标不标」这个问题，如果规范没写死，会产生两个后果："),
        UL([
            "<strong>训练标签自相矛盾</strong>：同一种情况一半标了一半没标 → 模型收到互相冲突的监督 → 学出一个「随机决定要不要报」的行为，表现为<em>置信度在阈值附近震荡、时序上闪烁</em>。",
            "<strong>评测口径漂移</strong>：新一批标注的规范略有变化，模型指标就变了，但你以为是模型变了。<em>这是「指标涨了但路测没感觉」的常见成因。</em>",
        ]),
        P("正确做法是把遮挡度做成<strong>显式属性</strong>（如 0–25% / 25–50% / 50–75% / &gt;75% 四档）而不是二元的「标/不标」，评测时按遮挡度分桶。<em>这样规范争议变成了一个可以在评测阶段调整的参数，而不是一个污染训练数据的隐形分歧。</em>"),
        DUAL(
            "遮挡场景里最值得讲的一条工程直觉是：<strong>TSR 的遮挡有一个行人跟踪没有的巨大优势——标志是静止的，自车在动</strong>。这意味着遮挡关系随时间必然变化（除非被前车持续遮挡）。<em>所以「单帧被挡住」不等于「这块牌检不到」，只要时序模块设计得当，一次穿越过程中总有若干帧能看清。</em>",
            "把它形式化：设某帧能看清的概率为 <code>q</code>，且各帧近似独立，则 <code>K</code> 帧内至少看清一次的概率是 <code>1 − (1−q)^K</code>。<em>q = 0.3、K = 10 时已经是 97%。</em><strong>这就是为什么 TSR 的时序融合收益远大于通用检测</strong>（模块 04 的主题）。但要注意独立性假设在<strong>车辆遮挡</strong>下严重失效——前车会连续挡几十帧，此时 K 帧之间高度相关，公式给出的乐观估计是错的。<em>识别「哪些失效模式是时序可救的、哪些不是」，本身就是一个重要的分类维度。</em>",
        ),
        CALLOUT("intuition", "把遮挡的对策排个序，可迁移到很多任务：<strong>① 让单帧更鲁棒（合成遮挡增强）→ ② 让时序补齐（多帧融合）→ ③ 让先验兜底（地图/位置先验）→ ④ 让下游知道（降低置信度并传递）</strong>。<em>注意第 ④ 条常被跳过，但它是安全系统的底线</em>——当感知确实看不清时，正确的行为不是硬猜，而是<strong>诚实地报告不确定</strong>，让下游选择保守策略。"),
    ])),
    ("light", "失效源 3：光照——逆光、隧道口、夜间与眩光", "".join([
        P("光照类失效有一个共同的根因，而且它<strong>不在模型里，在相机与 ISP 里</strong>：车载相机的动态范围有限，而真实道路场景的动态范围经常超出它一到两个数量级。<em>当传感器已经把信息丢掉（过曝为纯白 / 欠曝为纯黑），任何模型都救不回来。</em>"),
        ASCII("""场景动态范围 vs 传感器动态范围（示意，单位：EV 档）

  隧道出口正午:   洞内 |■■■■|                          洞外 |■■■■■■|
                       ← ~14 EV 跨度 ───────────────────────→
  传感器(单次曝光):        |■■■■■■■■■■|  ~10 EV
                              ↑ 曝光锁在这里 → 洞外全白（过曝）
                              ↓ 曝光锁在那里 → 洞内全黑（欠曝）

  夜间对向远光:   路面 |■|                  灯头 |■■■■■■■■|
                        ← ~16 EV，且**灯就在牌旁边** →
                        自动曝光被灯拉低 → 标志沉入噪声

  对策链：
    HDR 多帧合成 ─▶ 局部色调映射 ─▶ 训练数据必须含这些工况的**真实**样本
         ↑                              ↑
      硬件/ISP 层                    数据层（合成只能补一部分）""")
        ,
        TABLE(["工况", "物理机制", "在图上表现为", "成因归属", "对策"], [
            ["<strong>逆光 / 迎着太阳</strong>",
             "太阳在牌后方；标志正面处于阴影，背景极亮",
             "牌变成剪影，颜色信息几乎全丢（红/蓝分不出）",
             "<strong>传感器 + ISP</strong>为主",
             "HDR / 多曝光；训练加入逆光真实样本；<strong>降低对颜色的依赖</strong>（形状 + 内容也要能判）"],
            ["<strong>隧道出入口</strong>",
             "10+ EV 的瞬间跨度；且自动曝光有 0.3–1 s 的收敛延迟",
             "<strong>进洞瞬间全黑、出洞瞬间全白，持续若干帧</strong>",
             "<strong>ISP 曝光控制</strong>（不是模型）",
             "曝光预测（用地图/前视预判即将进洞）；这段时间<strong>主动降级并告知下游</strong>；靠时序在过渡前后的帧上补"],
            ["<strong>夜间</strong>",
             "照度低 → 高 ISO → 噪声大；标志靠反光膜回光，亮度依赖车灯照射角",
             "低信噪比；远处标志几乎不可见；反光膜近距离可能<strong>过曝成一团白</strong>",
             "<strong>传感器 + 数据</strong>",
             "低光合成增强（gamma + 泊松噪声 + 量化）；<strong>夜间数据必须真采</strong>，合成补不全；近距离过曝要单独建样本"],
            ["<strong>眩光 / 光晕</strong>",
             "对向远光、路灯、镜头内反射（lens flare）、雨夜路面反射",
             "大面积光晕覆盖标志；<strong>光斑本身可能被误检成圆形标志</strong>",
             "<strong>传感器 + 模型</strong>",
             "合成 flare 增强；把光斑作为 hard negative 加入 background 类；镜头镀膜/遮光罩（硬件）"],
            ["<strong>斑驳树影</strong>",
             "阳光透过树冠在牌面形成高对比条纹",
             "牌面被切成明暗块，破坏颜色与内容的一致性",
             "<strong>数据 + 模型</strong>",
             "合成条纹阴影增强；局部对比度归一化"],
        ]),
        DUAL(
            "<strong>光照类失效最重要的判断是「这一类到底该谁修」。</strong>如果隧道口的问题是自动曝光收敛慢，那么再多的训练数据也只能缓解症状；正确的修法是<em>让 ISP 团队做曝光预判</em>（甚至用感知输出反过来指导曝光——这在量产系统里叫 perception-in-the-loop AE）。<em>把一个 ISP 问题当成模型问题去解，是感知团队最常见的资源浪费。</em>",
            "而判断归属的方法是可操作的：<strong>看输入图像里信息还在不在。</strong>把失败帧调出来，如果标志区域已经是纯白（像素值饱和到 255）或纯黑（接近 0、方差极小），那就是传感器/ISP 丢了信息，模型不可能恢复；如果人眼在原图上能认出来而模型认不出来，那才是模型或数据的问题。<em>这个「人眼可读性检查」应该成为失效分析的标准第一步</em>——它能在几分钟内把一批 badcase 分成「不可修」「ISP 修」「模型修」三堆。<strong>面试里被问「你怎么分析 badcase」，先讲这个分诊步骤，比直接跳到「加数据」高明得多。</strong>",
        ),
        CALLOUT("warn", "夜间有一个反直觉的失效：<strong>近距离的反光标志会过曝成一团白</strong>。反光膜（retroreflective sheeting）会把车灯几乎原路反射回来，在近距离形成极高亮度。<em>结果是「远处太暗看不见、近处太亮糊成白块」，中间只有一小段窗口可用。</em>训练数据里如果只有白天样本，模型对这两种极端都毫无准备。<strong>这也是「夜间数据必须真采，不能只靠 gamma 变换合成」的直接理由</strong>——合成的低光图像不会产生反光膜过曝。"),
    ])),

    ("weather_motion", "失效源 4：天气与运动——雨雾雪、运动模糊、卷帘快门", "".join([
        P("这一组的共同点是：<strong>它们都在图像形成的物理过程里引入了确定性的退化，因此都可以被相当准确地合成</strong>——这使它们成为「合成增强性价比最高」的一类失效模式。"),
        H3("① 雨雾雪：大气散射模型"),
        P("雾的成像可以用经典的大气散射模型（atmospheric scattering model）描述："),
        MATH("I(x) \\;=\\; J(x)\\,t(x) \\;+\\; A\\bigl(1 - t(x)\\bigr), \\qquad t(x) = e^{-\\beta d(x)}"),
        P("其中 <code>I</code> 是观测图像、<code>J</code> 是无雾的真实场景、<code>A</code> 是大气光（通常接近白色）、<code>t</code> 是透射率、<code>β</code> 是散射系数、<code>d</code> 是深度。<strong>关键结论直接从公式读出来：对比度随距离指数衰减。</strong>"),
        TABLE(["现象", "对 TSR 的具体影响", "对策"], [
            ["<strong>雾/霾</strong>", "<code>t = e^(−βd)</code> ⇒ 远处标志的对比度指数衰减；<strong>颜色向大气光 A 偏移</strong>（红牌变粉、蓝牌变灰）——而颜色是 TSR 的一级语义", "按物理模型合成雾（需要深度先验，可用「y 坐标越靠近地平线越远」的粗估）；<strong>去雾预处理的收益有限且会放大噪声</strong>，通常不如直接用含雾数据训练"],
            ["<strong>雨</strong>", "雨条纹（rain streaks）叠加高频噪声；<strong>雨滴附着在镜头上会形成持续多帧的局部模糊斑</strong>——这一类比雨本身更致命，因为它不随时间变化", "合成雨条纹（有向运动模糊的亮线）；镜头水珠要单独合成（局部径向模糊 + 折射位移）；硬件上靠加热/疏水镀膜"],
            ["<strong>雪</strong>", "雪片遮挡（类似动态遮挡）；<strong>积雪覆盖牌面</strong>——这是真正的信息丢失；地面积雪造成整体高亮，自动曝光被拉低", "雪片合成（随机白斑 + 运动拖尾）；积雪牌需要真实数据；接受在此工况下降级"],
            ["<strong>路面湿滑反射</strong>", "夜雨时路面像镜子，反射的灯光与标志形成<strong>虚像</strong> → 误检", "把反射虚像作为 hard negative；用位置先验（地平线以下的「标志」高度可疑）"],
        ]),
        H3("② 运动模糊与卷帘快门"),
        P("这两个常被混为一谈，但成因与表现完全不同，<strong>面试里能分清是加分项</strong>："),
        TABLE(["", "运动模糊 (motion blur)", "卷帘快门 (rolling shutter)"], [
            ["成因", "曝光时间内目标在成像面上移动 → 能量被涂抹", "CMOS 逐行读出，行与行之间有时间差 → 不同行看到的是不同时刻的场景"],
            ["数学", "与一个有向线段核卷积：<code>I_blur = I ⊛ k(θ, L)</code>，<code>L = v·t_exp</code>（像素/曝光）", "第 <code>r</code> 行的时刻是 <code>t₀ + r·Δt</code> → 目标位置随行号线性偏移 → <strong>几何形变（斜切）</strong>"],
            ["表现", "标志边缘拖尾、数字糊成一团；<strong>低照度下更严重</strong>（曝光时间被拉长）", "垂直杆件变斜、圆牌变椭圆；<strong>快速横向运动或强振动时明显</strong>"],
            ["对 TSR", "细节丢失 → 错分（尤其数字）；边缘模糊 → 定位不准", "<strong>框的形状被扭曲 → 定位不准 + 尺寸估计错 → 距离估计错</strong>"],
            ["对策", "合成有向模糊核增强；<strong>缩短曝光</strong>（代价是更多噪声——这是一个真实的 ISP 取舍）", "合成行相关的位移；<strong>用全局快门传感器</strong>（成本高）；标定 <code>Δt</code> 后做几何校正"],
        ]),
        DUAL(
            "运动模糊有一个容易被忽略的量级问题：<strong>相对运动速度决定模糊长度，而 TSR 的相对速度极高。</strong>120 km/h 时自车 33 m/s，但标志在图像上的移动主要来自「越来越近」造成的尺度变化与横向掠过。<em>正对前方的标志在图像上移动很慢（这是好消息），而路侧近距离掠过的标志移动极快</em>——所以模糊主要伤害「近距离侧向牌」，而近距离本该是最容易的场景。<strong>这解释了一个反直觉的观测：某些系统的错分率在最近的距离桶里反而回升。</strong>",
            "卷帘快门的量级值得亲手算一遍，因为<strong>直觉会严重高估它</strong>。全帧读出确实要 10–30 ms，但<em>一块只占 16 行的小牌，其首末行的时间差只有 <code>T·h/H = 20 ms × 16/1080 ≈ 0.3 ms</code></em>——横向像速 200 px/s 时形变仅 0.06 px，完全可以忽略。<strong>真正让卷帘快门变危险的是另外三种情况</strong>：① <strong>颠簸与俯仰</strong>——角速度 ω 时形变约 <code>f·ω·T·h/H</code>，<em>ω = 2 rad/s（过减速带）时对 16 px 的牌就是约 1 px ≈ 6% 的尺度误差</em>，而 <code>Z = f·S/p</code> 是反比关系 ⇒ <strong>直接变成 6% 的距离误差</strong>；② 近距离大牌跨越大量行；③ <strong>LED 电子牌与逐行读出的相位干扰</strong>（下一节展开）。<em>「先算出量级再决定要不要管」这个习惯，比记住「卷帘快门有害」有用得多。</em>",
        ),
        CALLOUT("intuition", "这一整节可以浓缩成一条判断：<strong>凡是能写出物理模型的退化，都应该用合成增强去覆盖；凡是写不出物理模型的（积雪覆盖、涂鸦、褪色），都必须真采数据。</strong><em>雾、运动模糊、卷帘快门、低光噪声都属于前者——它们的合成成本极低而覆盖收益极高；而后者只能靠数据闭环去挖。</em>这条判据可以直接用来分配你的数据预算。"),
    ])),

    ("appearance_fp", "失效源 5：外观退化与误检源", "".join([
        P("前面几节讲的是「外部条件让牌看不清」，这一节讲两类更麻烦的问题：<strong>牌本身不标准</strong>，以及<strong>不是牌的东西长得像牌</strong>。"),
        H3("① 褪色、破损、涂鸦、非标准牌"),
        TABLE(["现象", "为什么难", "成因归属", "对策"], [
            ["<strong>褪色</strong>", "红色禁令牌褪成橙粉色 → <strong>颜色这个一级判据失效</strong>；而模型往往过度依赖颜色（因为训练集里颜色是最强的捷径特征）", "<strong>数据</strong>（训练集里全是新牌）", "颜色抖动增强（<em>但幅度要保守，过强会破坏语义</em>）；<strong>刻意采集老旧路段数据</strong>；评测时单独建「褪色」桶"],
            ["<strong>破损 / 弯折 / 被撞歪</strong>", "形状先验失效；圆牌变椭圆、三角牌缺角", "<strong>数据</strong>", "少量真实样本 + 几何形变增强；这类频率低，优先级通常不高"],
            ["<strong>涂鸦 / 贴纸覆盖</strong>", "牌面内容被局部改变，<strong>可能被改成另一个类别的样子</strong>（恶意场景下这是安全问题）", "<strong>数据 + 模型</strong>", "局部遮挡增强；<strong>依赖多帧一致性发现异常</strong>；极端情况应拒识而非硬猜"],
            ["<strong>非标准 / 地方性变体</strong>", "同一语义在不同省份/年代有不同版式；小尺寸牌、临时打印牌", "<strong>数据分布</strong>", "层次标签（先判粗类再判细类，粗类更鲁棒）；<strong>拒识 + 回传</strong>"],
        ]),
        H3("② 误检源：长得像牌的东西"),
        P("<strong>误检不是随机的，它高度集中在少数几类「结构性诱因」上。</strong>把它们枚举出来，就能有针对性地构造 hard negative——这比泛泛地「加负样本」有效得多。"),
        TABLE(["误检源", "为什么像", "为什么难以简单过滤", "对策"], [
            ["<strong>广告牌 / 店招</strong>", "矩形、高饱和度、常含数字与箭头；<strong>有些故意模仿交通标志的视觉语言</strong>", "尺寸与位置分布和真牌重叠；单帧上下文不足", "<strong>最有价值的 hard negative 来源</strong>——用当前检测器在路测视频上挖；加入 background 类；位置先验（广告牌通常更大更高或在建筑立面上）"],
            ["<strong>车身贴纸 / 车尾标识</strong>", "限速贴纸（如货车尾部「限速 80」）、危化品标志牌尺寸与真牌接近", "<strong>它们真的是标志，只是不该被遵守</strong>——这是语义问题不是识别问题", "<strong>需要「附着于车辆」这个判据</strong>：与动态目标检测结果做关联，若框落在车辆框内则抑制；这是多任务融合的典型价值"],
            ["<strong>路面标线 / 地面限速数字</strong>", "同样的数字与颜色", "语义上它们确实是限速信息，但位置与生效规则不同", "位置先验（地平线以下）；单独建类而非归为标志"],
            ["<strong>光斑 / 交通灯 / 圆形物体</strong>", "圆形 + 高亮 + 红色", "夜间尤其严重", "作为 hard negative；<strong>用时序稳定性过滤</strong>（光斑随视角剧变，真牌稳定）"],
            ["<strong>反射虚像</strong>", "湿路面、玻璃幕墙上的标志倒影", "外观几乎与真牌相同", "位置先验 + <strong>几何一致性</strong>（虚像的运动模式与真实静止物不符）"],
        ]),
        H3("③ 电子可变限速牌（VMS / 可变情报板）"),
        P("这是一个<strong>独立的、常被漏掉的失效类别</strong>，值得单独讲，因为它同时触碰了四象限里的多个格子："),
        UL([
            "<strong>成像问题</strong>：LED 屏是自发光的，与相机曝光/快门存在<em>频闪（flicker）与相位干扰</em>——某些帧可能拍到熄灭状态或部分扫描，表现为「数字缺笔画」甚至整块变暗。<em>这是纯粹的传感器-显示器同步问题，模型层面几乎无解，需要调整曝光时间使其为 LED 刷新周期的整数倍。</em>",
            "<strong>语义问题</strong>：同一块物理牌在不同时刻显示不同数值 ⇒ <strong>「牌的身份」与「牌的内容」必须分开跟踪</strong>。跟踪 ID 保持不变，但类别属性会变——如果时序模块用「多帧投票决定类别」，遇到真实的变化就会反应迟钝甚至一直投旧值。",
            "<strong>优先级问题</strong>：电子牌通常<em>覆盖</em>固定牌与地图限速（因为它反映实时管控）。这条规则必须显式实现在下游（C59 模块 04 会展开），而 TSR 侧必须<strong>把「这是电子牌」作为一个属性输出</strong>，否则下游无从判断优先级。",
        ]),
        DUAL(
            "把 ② 和 ③ 放在一起会看到一个共同结论：<strong>很多「TSR 失效」根本不是识别错误，而是语义与关联错误。</strong>货车尾部的「限速 80」贴纸，模型「认对了」——它确实是一块写着 80 的限速标志；错的是把它当成了适用于本车的路侧标志。<em>同理，电子牌被正确识别为「限速 60」也可能是错的，如果系统不知道它是电子牌因而没有正确处理优先级。</em>",
            "这引出 TSR 输出契约的一条硬性要求：<strong>除了类别，必须输出属性（是否电子牌、是否附着于车辆、是否临时牌）与关联信息（适用车道/方向）</strong>。<em>只输出「类别 + 框 + 分数」的 TSR 模块，在量产系统里是不合格的</em>——它把大量语义判断的责任推给了没有像素信息的下游。<strong>这也是模块 02 里「TSR 不是一个检测器，是一条链路」那个论断的具体兑现。</strong>",
        ),
        CALLOUT("danger", "<p>车身贴纸这一类值得单独警惕，因为它的失效有<strong>系统性偏差</strong>：跟在货车后面时持续存在、且高度可复现。一旦模型学会了「货车尾部的限速数字也算数」，用户会在每次跟车时被莫名限速。</p><p><strong>对策是跨任务关联而非更多数据</strong>：把 TSR 的框与动态目标检测（车辆）的框求 IoU，落在车辆框内的标志一律抑制或降级。<em>这是「感知模块之间应该互相利用」的最典型例子</em>——单靠 TSR 自己的像素信息，几乎无法可靠区分「贴在卡车上的牌」与「路侧的牌」。</p>", "跟车时被货车贴纸限速"),
    ])),
    ("association", "失效源 6：关联与歧义——「这块牌管不管我」", "".join([
        P("这是<strong>整个模块最容易被低估的一类失效</strong>，因为它在传统检测指标上完全不可见：框对了、类别对了、mAP 满分，系统行为却是错的。<em>它的本质是「检测正确 ≠ 应当采纳」。</em>"),
        ASCII("""俯视图：一个典型的匝道/辅路场景

        对向车道                      本车道                辅路
      ┌────────────┬─────────────────┬──────────────┐
      │  ←         │        ↑        │      ↑       │
      │  [限速40]  │     [限速80]    │   [限速30]   │
      │   ▲ 对向牌 │      ▲ 我的牌   │    ▲ 辅路牌  │
      └────────────┴─────────────────┴──────────────┘
                          🚗 我在这

  单帧图像里这三块牌可能同时出现，而且**对向牌与辅路牌常常更靠近图像中心**
  （因为道路曲率、相机安装角）——**「离图像中心近」不是「适用于我」的证据**。

  正确的关联需要：车道级定位 + 牌的横向位置 + 朝向 + 高精地图先验""")
        ,
        TABLE(["歧义类型", "错误行为", "为什么单帧解决不了", "对策"], [
            ["<strong>对向车道标志</strong>",
             "采纳了对向的限速/禁令",
             "对向牌的<em>背面</em>常常也能看到；分隔带窄时正面也可见。单帧只有一个 2D 框，没有朝向信息",
             "<strong>牌面朝向估计</strong>（背面 = 无内容的灰/白面，应作为独立类别检出并显式忽略）；横向位置 + 车道关联；<strong>时序上对向牌的相对运动速度约为本侧的两倍</strong>——这是一个可用的判据"],
            ["<strong>辅路 / 匝道标志</strong>",
             "主路上采纳了辅路的低限速",
             "几何上非常接近，透视下难以区分",
             "<strong>高精地图 + 车道级定位</strong>是主力；纯视觉需要判断牌所属的道路分支（依赖车道线/路沿的拓扑）"],
            ["<strong>出口/分岔前的方向性标志</strong>",
             "把「出口限速」当成主路限速",
             "标志本身语义正确，错的是适用范围",
             "识别附加的方向箭头/文字附加牌；<strong>与导航路径规划耦合</strong>（我要不要下这个出口）"],
            ["<strong>临时施工牌</strong>",
             "忽略（认为是非标准牌）或位置关联错误",
             "版式非标准、位置不规则（可能放在车道内、地面上、护栏上）；<strong>地图先验此时是错的</strong>",
             "<strong>临时牌必须优先于地图</strong>；专门采集施工场景；把「临时/移动式」作为属性输出"],
            ["<strong>区域性标志歧义</strong>",
             "同一形状在不同国家/地区含义不同",
             "训练集若混合多地区数据而无地区标签，模型会学出一个平均的、两边都不对的解",
             "<strong>把地区作为条件输入</strong>（或按地区训练不同的分类头）；用定位确定当前地区；层次标签让粗类跨地区共享"],
        ]),
        H3("为什么 mAP 完全看不见这一类"),
        P("因为标准检测评测只问「框和类别对不对」，不问「该不该采纳」。<strong>一个把对向车道限速 40 完美检出并上报的系统，在 mAP 上得满分，在路上会莫名其妙地减速。</strong>"),
        UL([
            "这直接推出模块 05 的一个核心主张：<strong>必须有「采纳正确率」这一层指标</strong>——即最终上报给规控的约束里，有多少比例是真正适用于本车的。",
            "也推出一条标注要求：<strong>标注时必须记录「该牌适用于哪条车道/哪个方向」</strong>，否则这个指标根本无法计算。<em>而这项标注成本高、争议大，常常在项目早期被砍掉，然后在量产前被迫补回来。</em>",
        ]),
        DUAL(
            "把关联问题讲透的一个好角度是：<strong>TSR 的输出是「对世界的观测」，而下游需要的是「对我的约束」——这两者之间隔着一次推理，而这次推理需要的信息（车道拓扑、朝向、地图）不在图像的那个小 crop 里。</strong><em>所以试图让检测器自己学会「这块牌管不管我」，通常是走错了方向</em>：它缺少必要的输入。",
            "正确的架构是<strong>把关联做成一个显式的、可测试的模块</strong>，输入是 TSR 的观测（框、类别、属性、朝向、横向位置）+ 车道线/路沿拓扑 + 定位与地图 + 导航路径，输出是「适用范围」。<em>这样它的错误可以被单独度量、单独回归、单独修复</em>，而不是混在检测指标里看不见。<strong>这与模块 02 的分解哲学是同一条：把统计性质不同的子问题拆开，你才获得分别优化它们的自由。</strong>",
        ),
        CALLOUT("warn", "区域性歧义有一个特别隐蔽的形式：<strong>数据集混合导致的「平均化」</strong>。若训练数据同时包含中国 GB 5768 与欧洲 Vienna 体系的样本，而没有地区标签，模型面对一个圆形红边白底的牌时，会在「禁止驶入」与「限速」之间学出一个折中的表示——<em>结果是在两个地区都不够可靠，而整体指标看起来还行</em>。<strong>面试里如果被问「跨国部署 TSR 要注意什么」，先讲这个「无条件混合导致平均化」的坑，再讲条件化（地区作为输入）与层次标签，答案就完整了。</strong>"),
    ])),

    ("priority", "把失效模式排成一张可执行的清单：频率 × 安全后果 × 修复成本", "".join([
        P("到这里我们列了十几类失效模式。<strong>但列清单不是目的，排序才是。</strong>一个团队一个季度只能真正解决 2–3 个问题，剩下的都是噪声。所以必须有一个能把「工程师的直觉」变成「可以在评审会上被质疑与修正的数字」的方法。"),
        H3("风险优先数（借用 FMEA 的思路）"),
        MATH("\\mathrm{Priority} \\;=\\; \\frac{F \\times S \\times D}{C}"),
        P("其中 <code>F</code> = 发生频率（每千公里出现次数，或占里程的比例）、<code>S</code> = 安全后果严重度（1–10）、<code>D</code> = 可检出性的<em>倒数</em>（越难被系统自己发现越高——静默失败要加权）、<code>C</code> = 修复成本（人月，或含硬件改动的折算）。<strong>把除以成本这一步做出来，是这个公式和「拍脑袋排序」的关键区别。</strong>"),
        TABLE(["失效模式", "F 频率", "S 安全后果", "D 静默性", "C 成本", "优先级", "备注"], [
            ["<strong>远距漏检（40–70 m）</strong>", "高", "<strong>高</strong>（超速）", "高（静默）", "中", "<strong>★★★★★</strong>", "可修区间，收益最大"],
            ["<strong>货车贴纸误检</strong>", "中", "中（幽灵刹车）", "低（用户投诉）", "<strong>低</strong>（跨模块关联即可）", "<strong>★★★★★</strong>", "<em>低成本高收益，先做</em>"],
            ["<strong>限速数字混淆 60/80</strong>", "中", "<strong>高</strong>", "高", "低（补数据+改采样）", "<strong>★★★★☆</strong>", "集中在少数相似对上"],
            ["<strong>隧道口过渡帧</strong>", "低-中", "中", "中", "<strong>高</strong>（要 ISP 配合）", "★★★☆☆", "跨团队，周期长"],
            ["<strong>对向车道误采纳</strong>", "中", "中-高", "<strong>高</strong>（mAP 看不见）", "高（需地图+朝向）", "★★★★☆", "架构性问题，要立项"],
            ["<strong>积雪覆盖牌面</strong>", "<strong>极低</strong>（地域性）", "中", "中", "高（只能真采）", "★☆☆☆☆", "<em>接受降级，写进 ODD</em>"],
            ["<strong>100 m 外漏检</strong>", "高", "低（还很远）", "高", "<strong>不可修</strong>（物理下界）", "—", "<em>不该进 backlog</em>"],
        ]),
        DUAL(
            "这张表里最值得学的是<strong>最后两行</strong>。「积雪覆盖」的正确处理不是修，而是<strong>写进 ODD（Operational Design Domain，运行设计域）——明确声明系统在此工况下降级</strong>，并确保降级行为是安全的（提示接管而非硬猜）。<em>「承认做不到」是安全系统设计的一部分，不是失败。</em>而「100 m 外漏检」是物理下界，把它放进 backlog 只会消耗评审带宽。",
            "第二个要点是 <code>D</code>（静默性）这一列，它常被遗漏。<strong>能被用户投诉或线上指标捕获的失效，其实是「便宜」的</strong>——你会知道它、会持续监控它。而漏检、错误关联这类静默失败，只有你主动去构造回归集才能看见，<em>因此在优先级里必须给它们额外的权重</em>。<strong>这也是为什么 D 出现在分子上：越难被发现的失效，越应该优先投入，因为它的真实代价被系统性低估了。</strong>",
        ),
        H3("从优先级到行动：每一类失效对应一条闭环"),
        ASCII("""失效模式          → 触发器（怎么在车队里找到它）      → 数据动作          → 验证方式
─────────────────────────────────────────────────────────────────────────────
远距漏检          跟踪回溯：近处确认的牌，回放前 N 帧     定向采集+小目标增强   按像素尺寸分桶的召回
                  看它最早在哪一帧才被检出                 copy-paste 小牌      「首次检出距离」中位数

货车贴纸误检      检测框与车辆框 IoU > 0.5 的标志         加入 background 类    FP/km（跟车场景切片）
                                                          + 跨模块抑制规则

限速数字混淆      多帧类别跳变（60↔80）                   相似对定向标注        逐对混淆矩阵
                  + top1−top2 margin 小                    + 难例挖掘

对向车道误采纳    上报的约束与地图/导航不一致              标注「适用车道」      采纳正确率（新指标）

隧道口            场景标签=tunnel 的帧上分数骤降          真采隧道数据          分场景切片指标
                                                          + ISP 曝光预判        + 过渡帧数统计""")
        ,
        P("<strong>这张图是本模块的最终产物</strong>：它把「失效模式」从一个描述性的清单，变成了一套「触发器 → 数据动作 → 验证指标」的可执行流程。<em>每一行都可以直接变成一个季度的工作项，并且完成时有明确的验收标准。</em>"),
        CALLOUT("intuition", "<p>面试里遇到「<strong>你怎么分析 TSR 的 failure case</strong>」这个问题（JD 里那条职责的直接考法），一个能立刻拉开差距的答案结构是：</p><p><strong>① 先分诊</strong>——四象限 + 人眼可读性检查，把 badcase 分成「不可修 / 传感器修 / 数据修 / 模型修 / 关联修」；<strong>② 再分桶</strong>——按距离、光照、天气、遮挡度切片，找出集中的那一两个桶；<strong>③ 再归因</strong>——用误差分解算出「修好每一类能涨多少」；<strong>④ 再排序</strong>——频率 × 后果 × 静默性 ÷ 成本；<strong>⑤ 最后给闭环</strong>——每一类配一个触发器、一个数据动作、一个验证指标。</p><p><em>大多数候选人会直接跳到「加数据」，而这五步里「加数据」只是第四步之后的一个可能动作。</em></p>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("失效分析这件事本身正在从「人工看 badcase」变成「自动化的挖掘与归因」。下面几个方向值得跟踪。"),
        UL([
            "<strong>用 VLM 做失效模式的自动标注与聚类</strong>。给定一批 badcase，让视觉-语言模型描述「这张图为什么难」（逆光/遮挡/模糊/褪色），再对描述做聚类，就能自动得到失效模式的分布。<em>这是 JD 里「automated data mining workflows」最现实的落点</em>，也是目前工业界推进最快的方向（C58 模块 04 会实现一个简化版）。开放问题是：VLM 的描述本身有偏差与幻觉，如何验证它的归因是对的。",
            "<strong>失效预测（failure prediction / introspection）</strong>：让模型输出「我现在可能不可靠」而不是等到错了再发现。与不确定性估计相关，但目标不同——它要预测的是<em>系统级</em>失败而不是单个预测的置信度。对静默失败（漏检）尤其重要，因为漏检没有任何输出可供打分。",
            "<strong>对抗性与物理攻击</strong>：在标志上贴特定图案就能让识别翻转（Eykholt et al. 的 <em>Robust Physical Perturbations</em> 是经典工作）。<em>与「涂鸦」失效的边界是模糊的</em>——一个足够像涂鸦的攻击很难与自然退化区分。目前的现实防御主要靠时序一致性与多传感器/地图交叉验证，而非模型本身的鲁棒性。",
            "<strong>合成数据与仿真的域差</strong>：雾、雨、低光可以物理建模，但 ISP 处理链（去噪、锐化、色调映射、局部对比度增强）会把物理上正确的合成图变成与真实相机输出不同的东西。<em>「在 ISP 之前还是之后做增强」是一个尚无定论但影响很大的工程问题。</em>",
            "<strong>失效模式的因果归因</strong>：目前的分桶分析只能给出相关性（「夜间桶指标低」），但夜间同时意味着低照度、眩光、车流少、路段类型不同。<em>如何把这些混杂因素解开，从而知道「到底是哪一个因素导致了下降」，是失效分析里最缺方法论的一环。</em>反事实/干预式的评测设计（在同一段路上只改变一个因素）是一个方向。",
            "<strong>长尾失效的评测统计学</strong>：某个失效模式一年只出现十几次，如何在统计上判断一次改动是否真的修好了它？<em>小样本 + 高代价场景的显著性判定，目前普遍靠「构造放大该场景比例的回归集」这一权宜之计</em>，其偏差如何校正尚无标准做法。",
        ]),
        CALLOUT("paper", "必读：<em>Bolya et al., TIDE: A General Toolbox for Identifying Object Detection Errors</em>（ECCV 2020，误差分解的标准工具，本模块四象限的定量化版本，必读）；<em>Hoiem et al., Diagnosing Error in Object Detectors</em>（ECCV 2012，误差分析方法论的开山之作）；<em>Zhu et al., Traffic-Sign Detection and Classification in the Wild</em>（CVPR 2016，TT100K，含小目标与长尾的失效讨论）；<em>Eykholt et al., Robust Physical-World Attacks on Deep Learning Visual Classification</em>（CVPR 2018，标志上贴纸即可翻转识别）；<em>He et al., Single Image Haze Removal Using Dark Channel Prior</em>（CVPR 2009，大气散射模型的经典应用）；卷帘快门可读 <em>Meingast et al., Geometric Models of Rolling-Shutter Cameras</em>。相邻课程：C56（增强，含天气与模糊合成）、C57（小目标）、C58（难例挖掘与触发器）、C61（误差分析工程）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · 失效模式全景（四象限归因 / 物理下界 / 退化曲线 / 混淆对 / 优先级打分）

目标：把「TSR 哪里会错」从一份描述性清单，变成**一套能算出数字、能排出顺序、能落成工作项**的分析流程。
这正是 JD 里「Analyze TSR-related scenarios and failure cases」那条职责的日常形态。

本 notebook 你会亲手实现：

1. **四象限归因器**：把每个错误归入 漏检 / 误检 / 错分 / 定位不准，并按**像素尺寸分桶**
2. **物理下界计算器**：针孔模型 `p = f·S/Z` → 最远可检距离 → **留给决策的时间**
3. **退化影响曲线**：遮挡 / 运动模糊 / 低光 / 雾 对检测分数的影响，找出**临界退化强度**
4. **卷帘快门的量级核算**：证明「直觉高估」，并找出它真正危险的工况
5. **混淆矩阵分析**：找出最容易互相错分的标志对，并用**安全后果加权**重排（60→80 vs 60→40）
6. **车身贴纸抑制器**：跨模块关联，量化 FP 下降与误伤的取舍
7. **失效模式优先级打分器**：`F × S × D / C`，含「不可修」与「写进 ODD」的判定，以及预算约束下的选择

> 心智模型：**先分诊（可修吗？谁修？）→ 再分桶（集中在哪？）→ 再归因（修好能涨多少？）
> → 再排序（除以成本）→ 最后给闭环（触发器 + 数据动作 + 验证指标）。**"""),

    md("""## 1 · 四象限归因器：把「错了」拆成四种不同的错

标准检测评测只给一个 mAP。要行动，必须知道**是哪一类错**。"""),

    code("""import numpy as np, math, json
rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)

def iou_xyxy(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def attribute(gts, preds, iou_hi=0.5, iou_lo=0.1):
    '''四象限 + 细分归因。
       gts:   [(x1,y1,x2,y2,cls)]
       preds: [(x1,y1,x2,y2,cls,score)]  —— 按 score 降序贪心匹配
       返回 (counts, gt_status, pred_status)
       gt_status[i]   ∈ tp / cls_err / loc_err / both / fn
       pred_status[j] ∈ tp / cls_err / loc_err / both / fp_bkg'''
    order = sorted(range(len(preds)), key=lambda j: -preds[j][5])
    gt_status = ['fn'] * len(gts)
    pred_status = [None] * len(preds)
    used = [False] * len(gts)
    for j in order:
        p = preds[j]
        best, best_iou = -1, 0.0
        for i, g in enumerate(gts):
            if used[i]:
                continue
            v = iou_xyxy(p[:4], g[:4])
            if v > best_iou:
                best, best_iou = i, v
        if best < 0 or best_iou < iou_lo:
            pred_status[j] = 'fp_bkg'                      # ② 背景误检
            continue
        same = (p[4] == gts[best][4])
        if best_iou >= iou_hi:
            st = 'tp' if same else 'cls_err'               # ✅ 正确 / ③ 错分
        else:
            st = 'loc_err' if same else 'both'             # ④ 定位不准 / 两者都错
        pred_status[j] = st
        gt_status[best] = st
        used[best] = True
    keys = ['tp', 'cls_err', 'loc_err', 'both', 'fp_bkg', 'fn']
    counts = {k: 0 for k in keys}
    for s in pred_status:
        counts[s] += 1
    counts['fn'] = sum(1 for s in gt_status if s == 'fn')
    return counts, gt_status, pred_status

# 手工构造一个能逐项验算的小例子
gts = [(100, 100, 140, 140, 0),      # -> TP
       (200, 100, 240, 140, 1),      # -> 错分（框完全重合，类别错）
       (300, 100, 340, 140, 2),      # -> 定位不准（IoU=0.333，类别对）
       (400, 100, 440, 140, 3)]      # -> 漏检
preds = [(100, 100, 140, 140, 0, 0.90),
         (200, 100, 240, 140, 2, 0.80),
         (320, 100, 360, 140, 2, 0.70),
         (700, 700, 740, 740, 1, 0.60)]   # -> 背景误检

cnt, gst, pst = attribute(gts, preds)
print('四象限归因：', json.dumps(cnt, ensure_ascii=False))
print('GT   状态：', gst)
print('Pred 状态：', pst)
assert abs(iou_xyxy((320, 100, 360, 140), (300, 100, 340, 140)) - 1 / 3) < 1e-9
assert cnt == {'tp': 1, 'cls_err': 1, 'loc_err': 1, 'both': 0, 'fp_bkg': 1, 'fn': 1}, cnt
print()
print('✅ 同一份预测，拆开看是：1 正确 / 1 错分 / 1 定位不准 / 1 背景误检 / 1 漏检。')
print('   **这五个数字对应五种完全不同的修法**，而 mAP 只会给你一个数。')"""),

    md("""### 按像素尺寸分桶：找出失效到底集中在哪

失效分析的第二步永远是**分桶**。TSR 最重要的分桶维度就是像素尺寸（≈ 距离）。"""),

    code("""def simulate_dataset(n_frames=3000, seed=1):
    '''合成一批「检测器输出」：
       · 检出概率随尺寸增大而上升（小目标漏检是主导失效）
       · 框误差的**绝对**像素量近似恒定 -> 小目标的相对误差更大 -> 定位不准更多
       · 分类正确率随尺寸上升（远处数字不可读）
       · 每帧有少量背景误检'''
    g = np.random.default_rng(seed)
    frames = []
    for _ in range(n_frames):
        gts, preds = [], []
        for _ in range(int(g.integers(1, 4))):
            s = float(np.clip(g.lognormal(mean=math.log(20), sigma=0.55), 7, 90))
            x, y = g.uniform(50, 1800), g.uniform(100, 600)
            cls = int(g.integers(0, 6))
            gts.append((x, y, x + s, y + s, cls))
            p_det = 1 / (1 + math.exp(-(s - 15.0) / 3.5))          # 尺寸->检出概率
            if g.random() < p_det:
                off = g.normal(0, 1.6, size=2)                      # 绝对像素误差 ~ 常数
                sc = 1 + g.normal(0, 0.09)
                s2 = s * sc
                px, py = x + off[0], y + off[1]
                p_cls = 1 / (1 + math.exp(-(s - 12.0) / 5.0))       # 尺寸->分类正确率
                c2 = cls if g.random() < p_cls else int(g.integers(0, 6))
                preds.append((px, py, px + s2, py + s2, c2, float(g.uniform(0.3, 1.0))))
        for _ in range(int(g.poisson(0.25))):                       # 背景误检
            x, y = g.uniform(0, 1800), g.uniform(0, 900)
            s = float(g.uniform(10, 40))
            preds.append((x, y, x + s, y + s, int(g.integers(0, 6)), float(g.uniform(0.3, 0.7))))
        frames.append((gts, preds))
    return frames

frames = simulate_dataset()
EDGES = [0, 12, 16, 24, 32, 48, 1e9]
LABEL = ['<12px', '12-16', '16-24', '24-32', '32-48', '>48px']

tot = {k: 0 for k in ['tp', 'cls_err', 'loc_err', 'both', 'fn']}
buck = {i: {k: 0 for k in tot} for i in range(len(LABEL))}
n_fp = 0
for gts, preds in frames:
    cnt, gst, pst = attribute(gts, preds)
    n_fp += cnt['fp_bkg']
    for g_, st in zip(gts, gst):
        s = g_[2] - g_[0]
        b = int(np.digitize(s, EDGES[1:-1]))
        buck[b][st] += 1
        tot[st] += 1

N = sum(tot.values())
print(f"{'尺寸桶':<9s}{'GT 数':>7s}{'漏检%':>8s}{'错分%':>8s}{'定位不准%':>10s}{'正确%':>8s}")
miss = {}
for b in range(len(LABEL)):
    n = sum(buck[b].values())
    if n == 0:
        continue
    miss[b] = buck[b]['fn'] / n
    print(f'{LABEL[b]:<9s}{n:>7d}{buck[b]["fn"] / n:>8.1%}'
          f'{buck[b]["cls_err"] / n:>8.1%}{(buck[b]["loc_err"] + buck[b]["both"]) / n:>10.1%}'
          f'{buck[b]["tp"] / n:>8.1%}')
print(f'\\n整体：GT {N} 个，漏检 {tot["fn"] / N:.1%}，背景误检 {n_fp} 个'
      f'（{n_fp / len(frames):.3f} 个/帧）')

assert miss[0] > 0.5, '最小的桶漏检超过一半'
assert miss[5] < 0.02, '大目标几乎不漏'
assert all(miss[i] >= miss[i + 1] - 0.02 for i in range(5)), '漏检率随尺寸单调下降'
assert buck[0]['cls_err'] / max(1, sum(buck[0].values())) > \\
       buck[5]['cls_err'] / max(1, sum(buck[5].values())), '小目标也更容易错分'

print()
print('✅ **Miss 在小尺寸桶里占绝对主导** —— 这就是「先做远距漏检」这个结论的来源。')
print('⚠️  整体漏检率 %.1f%% 这个数字本身没有行动价值：它混合了「不可修的物理下界」'
      % (100 * tot['fn'] / N))
print('    与「可修的模型问题」。**必须先分桶，再决定修哪个桶。**')"""),

    md("""## 2 · 物理下界：先算出「哪些距离本来就不可能」

针孔模型 `p = f_px · S / Z`，`f_px = W / (2·tan(FOV/2))`。
**不先画出这条线，你会把精力浪费在信息论上不可能的任务上。**"""),

    code("""def focal_px(width_px, fov_deg):
    return width_px / (2.0 * math.tan(math.radians(fov_deg) / 2.0))

def sign_px(S, Z, f):
    '''标志在图像上的像素边长。S: 物理尺寸(m)，Z: 距离(m)。'''
    return f * S / Z

def max_range(S, p_min, f):
    '''要求至少 p_min 像素时，最远能看到多少米。'''
    return f * S / p_min

CAMS = [('广角 1920×1080 / FOV 60°', 1920, 60.0),
        ('长焦 1920×1080 / FOV 30°', 1920, 30.0)]
S_SIGN = 0.60                       # 限速牌直径 0.6 m

for nm, W, fov in CAMS:
    f = focal_px(W, fov)
    print(f'{nm}   f_px = {f:.1f}')
    print('   ' + ''.join(f'{f"{Z}m":>9s}' for Z in [20, 40, 60, 80, 100, 120]))
    print('   ' + ''.join(f'{sign_px(S_SIGN, Z, f):>9.1f}' for Z in [20, 40, 60, 80, 100, 120]))

f_wide = focal_px(1920, 60.0); f_tele = focal_px(1920, 30.0)
assert abs(sign_px(S_SIGN, 60, f_wide) - 16.6) < 0.3, '60 m 外约 17 px —— 记住这个数'
assert abs(max_range(S_SIGN, 16.0, f_wide) - 62.4) < 0.5
assert sign_px(S_SIGN, 60, f_tele) > 2.0 * sign_px(S_SIGN, 60, f_wide), '长焦把像素翻倍'

print(f'\\n{"检出所需最小像素":>18s}' + ''.join(f'{f"{p}px":>12s}' for p in [10, 12, 16, 24]))
for nm, W, fov in CAMS:
    f = focal_px(W, fov)
    print(f'{nm[:6]:>18s}' + ''.join(f'{max_range(S_SIGN, p, f):>11.0f}m' for p in [10, 12, 16, 24]))
print()
print('✅ 「广角相机在 100 m 外只有 10 px」是物理事实，不是模型缺陷。')
print('✅ 想在更远处检出，**加长焦相机比换模型有效得多** —— 这是硬件层面的对策。')"""),

    code("""# 时间账：60 m 检出，留给系统多少时间？
def time_budget(Z_detect, v_kmh, confirm_frames=6, fps=30.0, Z_act=10.0):
    '''从检出到「必须完成动作」还剩多少秒；扣掉多帧确认的开销。'''
    v = v_kmh / 3.6
    t_total = (Z_detect - Z_act) / v
    t_confirm = confirm_frames / fps
    return t_total, t_confirm, t_total - t_confirm

print(f"{'车速':>7s}{'检出距离':>10s}{'总时间':>9s}{'多帧确认':>10s}{'留给规控':>10s}")
rows = {}
for v_kmh in [60, 90, 120]:
    for Zd in [40, 60, 80]:
        t, tc, left = time_budget(Zd, v_kmh)
        rows[(v_kmh, Zd)] = left
        flag = '   <- 危险' if left < 0.8 else ''
        print(f'{v_kmh:>5d}km/h{Zd:>9d}m{t:>8.2f}s{tc:>9.2f}s{left:>9.2f}s{flag}')

assert rows[(120, 40)] < rows[(120, 60)] < rows[(120, 80)]
assert rows[(120, 40)] < 1.0, '120 km/h 下 40 m 才检出，留给规控不到 1 秒'
assert rows[(60, 80)] > 3.0

print()
print('✅ **首次检出距离**是 TSR 最重要的工程指标之一（模块 05 会正式定义它）。')
print('⚠️  多帧确认（这里假设 6 帧 = 0.2 s）是稳定性的代价 ——')
print('    帧数越多越稳定但越晚，这个取舍在模块 04 会被量化。')
print('⚠️  注意 120 km/h + 40 m 检出这一格：留给规控 0.7 s。**这不是感知指标问题，')
print('    这是安全边界问题** —— 应当直接写进 ODD 与限速策略。')"""),

    md("""## 3 · 退化影响曲线：遮挡 / 运动模糊 / 低光 / 雾

给检测分数造一个可控的代理（模板归一化相关 → sigmoid），
然后逐一施加物理退化，**找出每种退化的「临界强度」**（分数跌破工作阈值的那一点）。"""),

    code("""R = 48

def make_sign(R=48, seed=2):
    '''合成一块标志：外圈（红边）+ 内部图案。'''
    ax = np.arange(R); yy, xx = np.meshgrid(ax, ax, indexing='ij')
    c = (R - 1) / 2
    r = np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / (R / 2)
    ring = ((r > 0.78) & (r <= 1.0)).astype(float)
    inner = (r <= 0.70).astype(float)
    g = np.random.default_rng(seed)
    pat = np.kron(g.normal(size=(4, 4)), np.ones((R // 4, R // 4)))
    img = 0.5 + 0.35 * ring + 0.25 * inner * pat
    return np.clip(img, 0.0, 1.0)

SIGN = make_sign(R)
TPL = (SIGN - SIGN.mean()) / (np.linalg.norm(SIGN - SIGN.mean()) + 1e-9)

def score(img):
    '''检测分数代理：与干净模板的归一化相关 -> sigmoid。'''
    z = img - img.mean()
    z = z / (np.linalg.norm(z) + 1e-9)
    ncc = float(np.dot(z.ravel(), TPL.ravel()))
    return 1.0 / (1.0 + math.exp(-12.0 * (ncc - 0.55)))

def occlude(img, ratio, g):
    '''随机矩形遮挡：覆盖 ratio 比例的面积。'''
    out = img.copy()
    if ratio <= 0:
        return out
    h = int(round(R * math.sqrt(ratio))); w = h
    y0 = int(g.integers(0, max(1, R - h))); x0 = int(g.integers(0, max(1, R - w)))
    out[y0:y0 + h, x0:x0 + w] = 0.15
    return out

def conv2d_same(img, k):
    kh, kw = k.shape; ph, pw = kh // 2, kw // 2
    pad = np.pad(img, ((ph, ph), (pw, pw)), mode='edge')
    out = np.zeros_like(img, dtype=float)
    for i in range(kh):
        for j in range(kw):
            out += k[i, j] * pad[i:i + img.shape[0], j:j + img.shape[1]]
    return out

def motion_kernel(length, angle_deg=15.0):
    '''有向线段核：长度 L = 相对速度 × 曝光时间（像素）。'''
    L = max(1, int(round(length)))
    k = np.zeros((2 * L + 1, 2 * L + 1))
    th = math.radians(angle_deg)
    for t in np.linspace(-L / 2.0, L / 2.0, 8 * L + 1):
        y = int(round(L + t * math.sin(th))); x = int(round(L + t * math.cos(th)))
        k[y, x] += 1.0
    return k / k.sum()

def lowlight(img, gain, g, read_noise=0.012):
    '''低光：整体压暗 + 光子噪声(泊松) + 读出噪声 + 8bit 量化。'''
    lam = np.clip(img * gain, 0, None) * 255.0
    photons = g.poisson(lam) / 255.0
    out = photons / max(gain, 1e-6) + g.normal(0, read_noise / max(gain, 1e-6), img.shape)
    return np.clip(np.round(out * 255) / 255.0, 0, 1)

def fog(img, beta, d=1.0, A=0.92):
    '''大气散射：I = J·t + A(1−t)，t = exp(−β d)。'''
    t = math.exp(-beta * d)
    return img * t + A * (1 - t)

g = np.random.default_rng(4)
print('干净分数 =', round(score(SIGN), 4))
assert score(SIGN) > 0.98

# **精确性质**：雾把对比度乘以 t —— 这是可以逐位验证的
for beta in [0.3, 0.8, 1.5]:
    t = math.exp(-beta * 1.0)
    assert abs(fog(SIGN, beta).std() - t * SIGN.std()) < 1e-12
print('✅ 验证大气散射模型：std(I) = t·std(J) 精确成立，t = exp(−βd)')
print('   ⇒ **对比度随距离指数衰减** —— 这就是远处标志在雾天先消失的原因。')"""),

    code("""def curve(fn, levels, n=40, seed=7):
    g = np.random.default_rng(seed)
    return [float(np.mean([score(fn(SIGN, lv, g)) for _ in range(n)])) for lv in levels]

OCC = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
BLUR = [0, 2, 4, 6, 9, 12, 16]
GAIN = [1.0, 0.5, 0.25, 0.12, 0.06, 0.03, 0.015]
BETA = [0.0, 0.3, 0.6, 1.0, 1.5, 2.2, 3.0]

c_occ = curve(lambda im, lv, gg: occlude(im, lv, gg), OCC)
c_blur = [float(score(conv2d_same(SIGN, motion_kernel(L)))) if L > 0 else score(SIGN) for L in BLUR]
c_low = curve(lambda im, lv, gg: lowlight(im, lv, gg), GAIN, n=12)
c_fog = [float(score(fog(SIGN, b))) for b in BETA]

def show(name, levels, scores, unit=''):
    print(f'{name:<14s}' + ''.join(f'{f"{lv}{unit}":>9s}' for lv in levels))
    print(f'{"  分数":<14s}' + ''.join(f'{s:>9.3f}' for s in scores))

show('遮挡比例', OCC, c_occ)
show('模糊核长', BLUR, c_blur, 'px')
show('光照增益', GAIN, c_low, '×')
show('雾 β', BETA, c_fog)

def critical(levels, scores, thr=0.5):
    '''分数首次跌破工作阈值的退化强度 —— 「临界退化强度」。'''
    for lv, s in zip(levels, scores):
        if s < thr:
            return lv
    return None

crit = {'遮挡': critical(OCC, c_occ), '模糊': critical(BLUR, c_blur),
        '低光': critical(GAIN, c_low), '雾': critical(BETA, c_fog)}
print('\\n临界退化强度（分数跌破 0.5）:', crit)

assert c_occ[0] > c_occ[-1] and c_occ[0] > 0.9
assert c_blur[0] > c_blur[-1], '模糊越强分数越低'
assert c_fog[0] > c_fog[-1], '雾越浓分数越低'
assert crit['遮挡'] is not None and crit['遮挡'] <= 0.5, '遮挡超过一半基本必失效'
assert c_low[-1] < c_low[0], '光照越暗分数越低'

print()
print('✅ **临界强度**才是可以写进需求的东西：「遮挡 < 30%% 时必须检出」比')
print('   「提高鲁棒性」可验证得多，也可以直接变成一条回归门禁。')
print('⚠️  注意雾曲线的形状：前段平缓、后段陡降 —— 因为 sigmoid 的工作点在中段。')
print('    **这意味着「轻雾几乎无影响，浓雾断崖式失效」**，中间几乎没有过渡区。')"""),

    code("""# 卷帘快门：先算量级，再决定要不要管（直觉会严重高估它）
def rs_shift_px(h_px, T_readout=0.020, H=1080, v_img=0.0, f_px=1663.0, omega=0.0):
    '''目标自身跨越的行所对应的时间 dt = T·h/H；
       形变 = 横向像速 × dt   +   俯仰角速度引起的 f·ω·dt。'''
    dt = T_readout * (h_px / H)
    return abs(v_img) * dt + abs(f_px * omega * dt), dt

print(f"{'工况':<30s}{'牌高':>7s}{'dt(ms)':>9s}{'形变(px)':>10s}{'尺度误差':>10s}{'距离误差':>10s}")
CASES = [
    ('平稳行驶 · 横向 200 px/s', 16, 200.0, 0.0),
    ('平稳行驶 · 横向 800 px/s', 16, 800.0, 0.0),
    ('过减速带 · ω = 2 rad/s',   16, 200.0, 2.0),
    ('剧烈颠簸 · ω = 5 rad/s',   16, 200.0, 5.0),
    ('近距大牌 · ω = 2 rad/s',   120, 200.0, 2.0),
]
res = {}
for nm, h, v_img, om in CASES:
    d, dt = rs_shift_px(h, v_img=v_img, omega=om)
    rel = d / h
    res[nm] = rel
    print(f'{nm:<30s}{h:>6d}px{dt * 1000:>9.3f}{d:>10.3f}{rel:>9.1%}{rel:>10.1%}')

assert res['平稳行驶 · 横向 200 px/s'] < 0.01, '平稳行驶时卷帘快门对小牌的影响 < 1% —— 可忽略'
assert res['过减速带 · ω = 2 rad/s'] > 5 * res['平稳行驶 · 横向 200 px/s'], '颠簸才是主因'
assert res['剧烈颠簸 · ω = 5 rad/s'] > 0.10, '剧烈颠簸下尺度误差超过 10%'

print()
print('✅ Z = f·S/p 是**反比**关系 ⇒ 像素宽度错 x%%，距离就错约 x%%。')
print('✅ 结论（值得在面试里主动提）：**卷帘快门对小牌的横向形变可以忽略**')
print('   （因为一块 16 px 的牌只跨越 16 行，dt 只有全帧读出的 1.5%%）；')
print('   **真正危险的是颠簸/俯仰**，以及近距离跨越大量行的大牌，还有 LED 电子牌的相位干扰。')
print('⚠️  「先算量级再决定要不要管」比「记住卷帘快门有害」有用得多。')"""),

    md("""## 4 · 混淆矩阵分析：找出最容易互相错分的标志对

错分不是均匀分布的，它**高度集中在少数几对**上。
更重要的是：**混淆的频次排序 ≠ 风险排序**（限速 60→80 与 60→40 频次相近，后果天差地别）。"""),

    code("""CLASSES = ['限速30', '限速40', '限速50', '限速60', '限速80', '限速100',
           '禁止驶入', '禁止左转', '禁止掉头', '停车让行', '注意行人', '注意学校']
NC = len(CLASSES)
LIMIT = {0: 30, 1: 40, 2: 50, 3: 60, 4: 80, 5: 100}       # 限速类的数值

def confusability():
    '''可混淆度矩阵 M[i][j]：越小越容易混。由「同组」+「数字形状相似」构成。'''
    M = np.full((NC, NC), 6.0)
    np.fill_diagonal(M, 0.0)
    speed, forbid, warn = list(range(6)), [6, 7, 8, 9], [10, 11]
    for grp, d in [(speed, 3.0), (forbid, 3.2), (warn, 2.6)]:
        for i in grp:
            for j in grp:
                if i != j:
                    M[i, j] = d
    # 数字形状相似：3/8、6/8、0/8 的笔画接近 -> 更容易混
    for i, j, d in [(3, 4, 1.6), (0, 4, 2.3), (1, 0, 2.4), (2, 1, 2.6), (4, 5, 2.5)]:
        M[i, j] = M[j, i] = d
    for i, j, d in [(7, 8, 2.0)]:                          # 禁止左转 / 禁止掉头
        M[i, j] = M[j, i] = d
    return M

M = confusability()

def simulate_confusion(M, n_per=4000, T=1.0, seed=3):
    g = np.random.default_rng(seed)
    cm = np.zeros((NC, NC), dtype=int)
    for c in range(NC):
        p = np.exp(-M[c] / T); p /= p.sum()
        cm[c] = np.bincount(g.choice(NC, size=n_per, p=p), minlength=NC)
    return cm

cm = simulate_confusion(M)
acc = np.trace(cm) / cm.sum()
print(f'整体准确率 = {acc:.4f}')
print(f"{'':<9s}" + ''.join(f'{c[-3:]:>7s}' for c in CLASSES))
for i, c in enumerate(CLASSES):
    print(f'{c:<9s}' + ''.join(f'{cm[i, j]:>7d}' for j in range(NC)))

def top_pairs(cm, k=6):
    '''按「双向混淆总数」排序的混淆对。'''
    out = []
    for i in range(NC):
        for j in range(i + 1, NC):
            out.append((int(cm[i, j] + cm[j, i]), i, j))
    return sorted(out, reverse=True)[:k]

print(f'\\n{"最易混淆的标志对（按频次）":<28s}{"次数":>7s}')
tp = top_pairs(cm)
for n_, i, j in tp:
    print(f'{CLASSES[i] + " <-> " + CLASSES[j]:<28s}{n_:>7d}')

assert acc > 0.5, '大部分样本还是分对了'
assert (tp[0][1], tp[0][2]) == (3, 4), '最易混的应是「限速60 <-> 限速80」'
assert cm[3, 4] > cm[3, 6], '同组内的混淆远多于跨组'
print()
print('✅ 混淆**高度集中**：前 3 对就占了错分的很大一块 -> 定向补数据的性价比极高。')"""),

    code("""# 但频次不等于风险：把「安全后果」加权进去
def severity(i, j):
    '''把 i 错分成 j 的安全后果（1–10）。'''
    if i == j:
        return 0.0
    if i in LIMIT and j in LIMIT:
        # **判高了 = 超速 = 危险；判低了 = 保守 = 体验问题**
        return 9.0 if LIMIT[j] > LIMIT[i] else 2.5
    if i == 9:                    # 停车让行被判成别的 -> 冲入路口
        return 10.0
    if i in (6, 7, 8) and j not in (6, 7, 8):
        return 7.0                # 禁令被判成非禁令 -> 违规行为
    return 4.0

risk = np.zeros((NC, NC))
for i in range(NC):
    for j in range(NC):
        risk[i, j] = cm[i, j] * severity(i, j)

flat = sorted(((risk[i, j], i, j) for i in range(NC) for j in range(NC) if i != j), reverse=True)
print(f'{"最危险的错分方向（频次 × 后果）":<34s}{"次数":>7s}{"后果":>6s}{"风险":>9s}')
for r, i, j in flat[:8]:
    print(f'{CLASSES[i] + " -> " + CLASSES[j]:<34s}{cm[i, j]:>7d}{severity(i, j):>6.1f}{r:>9.0f}')

r_up = risk[3, 4]      # 限速60 -> 限速80（判高了，超速）
r_dn = risk[4, 3]      # 限速80 -> 限速60（判低了，保守）
print(f'\\n限速60->80  次数 {cm[3, 4]:>5d}  风险 {r_up:>7.0f}')
print(f'限速80->60  次数 {cm[4, 3]:>5d}  风险 {r_dn:>7.0f}')

assert abs(cm[3, 4] - cm[4, 3]) / max(cm[3, 4], cm[4, 3]) < 0.15, '两个方向的频次相近（混淆是对称的）'
assert r_up > 3.0 * r_dn, '但风险差 3 倍以上 —— **方向不同，后果完全不同**'
assert flat[0][1] == 9 or severity(*flat[0][1:]) >= 9.0, '风险榜首必是高后果类'

print()
print('✅ **混淆矩阵必须看方向，而且必须加权。** 60->80 与 80->60 频次几乎相同，')
print('   但前者是超速（安全事故），后者只是过于保守（体验问题）。')
print('✅ 工程含义：① 评测要报**有向**的混淆而不是对称的「易混对」；')
print('   ② 分类器的决策可以**非对称**——在限速类上，判低比判高安全，')
print('      因此可以给「判高」施加额外的阈值代价（回到模块 02 的代价敏感决策）。')"""),

    md("""## 5 · 误检源：用跨模块关联抑制「货车贴纸」

这是**低成本高收益**的典型：单靠 TSR 自己的像素信息几乎无法区分
「贴在卡车上的限速牌」与「路侧的限速牌」，但和车辆检测求一次交集就能解决。"""),

    code("""def contain_ratio(sign, veh):
    '''标志被车辆框包含的比例 = area(∩) / area(sign) —— 比 IoU 更合适。'''
    x1 = max(sign[0], veh[0]); y1 = max(sign[1], veh[1])
    x2 = min(sign[2], veh[2]); y2 = min(sign[3], veh[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a = (sign[2] - sign[0]) * (sign[3] - sign[1])
    return inter / a if a > 0 else 0.0

def simulate_sticker_scene(n=6000, seed=5):
    '''每帧：一辆前车 + 可能的车尾贴纸(应抑制) + 路侧真牌(不应抑制，但可能与车框在 2D 上重叠)。'''
    g = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        vw = g.uniform(200, 500); vh = vw * 0.8
        vx = g.uniform(600, 1100); vy = g.uniform(350, 500)
        veh = (vx, vy, vx + vw, vy + vh)
        if g.random() < 0.45:                              # 车尾贴纸：完全在车框内
            s = g.uniform(14, 34)
            sx = g.uniform(vx + 0.15 * vw, vx + 0.85 * vw - s)
            sy = g.uniform(vy + 0.45 * vh, vy + 0.9 * vh - s)
            rows.append(((sx, sy, sx + s, sy + s), veh, 1))
        if g.random() < 0.75:                              # 路侧真牌
            s = g.uniform(12, 40)
            # 多数在车框外；少部分因透视恰好**跨在车框边缘上** -> 这是「误伤」的来源
            if g.random() < 0.18:
                sx = vx - s * g.uniform(0.15, 0.85)         # 横跨车框左边界，部分重叠
                sy = g.uniform(vy, vy + vh - s)
            else:
                sx = g.choice([g.uniform(50, max(60, vx - 60)), g.uniform(vx + vw + 40, 1850)])
                sy = g.uniform(120, 420)
            rows.append(((sx, sy, sx + s, sy + s), veh, 0))
    return rows

scene = simulate_sticker_scene()
n_sticker = sum(r[2] for r in scene); n_real = len(scene) - n_sticker
KM = 3000.0                                                 # 假设这批帧来自约 3000 km 的车队数据
print(f'样本：车身贴纸 {n_sticker} 个，路侧真牌 {n_real} 个；假设来自 {KM:.0f} km 车队数据')
print(f"{'抑制阈值':>9s}{'贴纸抑制率':>12s}{'真牌误伤率':>12s}{'残余 FP/km':>13s}{'真牌损失/km':>13s}")
best = None
for thr in [0.30, 0.50, 0.70, 0.85, 0.95, 1.01]:
    sup_bad = sum(1 for s, v, lab in scene if lab == 1 and contain_ratio(s, v) >= thr)
    sup_good = sum(1 for s, v, lab in scene if lab == 0 and contain_ratio(s, v) >= thr)
    fp_km = (n_sticker - sup_bad) / KM
    loss_km = sup_good / KM
    print(f'{thr:>9.2f}{sup_bad / n_sticker:>12.1%}{sup_good / n_real:>12.1%}'
          f'{fp_km:>13.3f}{loss_km:>13.3f}')
    if thr <= 1.0 and (best is None or (fp_km + 3 * loss_km) < best[1]):
        best = (thr, fp_km + 3 * loss_km)

base_fp = n_sticker / KM
sup95 = sum(1 for s, v, lab in scene if lab == 1 and contain_ratio(s, v) >= 0.95)
hurt95 = sum(1 for s, v, lab in scene if lab == 0 and contain_ratio(s, v) >= 0.95)
print(f'\\n不做抑制：FP/km = {base_fp:.3f}；阈值 0.95 抑制后 = {(n_sticker - sup95) / KM:.3f}')
assert sup95 / n_sticker > 0.95, '完全包含判据能抑制绝大多数车身贴纸'
assert hurt95 / n_real < 0.03, '误伤率很低（真牌很少被车框完全包住）'
assert (n_sticker - sup95) / KM < base_fp * 0.1, 'FP/km 下降一个数量级'
print(f'最优工作点（代价 FP + 3×误伤）：阈值 = {best[0]:.2f}')

print()
print('✅ 一条跨模块规则把这类 FP 降了一个数量级，**成本几乎为零**（不需要重训任何模型）。')
print('✅ 这就是优先级表里「货车贴纸误检」排在最前面的原因：**低成本 × 中高收益**。')
print('⚠️  用「包含比例」而不是 IoU：贴纸远小于车框，IoU 永远很小，用 IoU 会完全失效。')
print('   **度量选错，一个正确的想法也会失败** —— 这类细节是工程与 demo 的分界线。')"""),

    md("""## 6 · 失效模式优先级打分器

`Priority = F × S × D / C`：频率 × 安全后果 × 静默性 ÷ 修复成本。
**「除以成本」和「把不可修的剔除」这两步，是它和拍脑袋排序的分界。**"""),

    code("""FAILURES = [
    # name,                    F 频率, S 后果, D 静默性, C 成本(人月), fixable, note
    ('远距漏检 40-70m',            8, 9, 3, 3.0, True,  '可修区间'),
    ('远距漏检 >90m',              9, 4, 3, 99.0, False, '物理下界，不可修'),
    ('货车贴纸误检',                5, 6, 1, 0.5, True,  '跨模块关联即可'),
    ('限速数字混淆 60/80',          5, 9, 3, 1.0, True,  '集中在少数相似对'),
    ('对向车道误采纳',              9, 9, 3, 8.0, True,  'mAP 看不见，架构性工作'),
    ('隧道口过渡帧',                3, 6, 2, 8.0, True,  '需 ISP 配合'),
    ('夜间眩光漏检',                4, 7, 3, 4.0, True,  '真采 + 合成'),
    ('雨雾对比度下降',              4, 6, 2, 2.0, True,  '物理可合成'),
    ('积雪覆盖牌面',                1, 6, 2, 10.0, True,  '地域性极低频'),
    ('电子牌频闪缺笔画',            2, 7, 3, 5.0, True,  '曝光与刷新同步'),
    ('临时施工牌漏检',              2, 8, 3, 4.0, True,  '地图先验此时是错的'),
]

def priority(f):
    return f[1] * f[2] * f[3] / f[4]

rank = sorted([f for f in FAILURES if f[5]], key=priority, reverse=True)
print(f"{'失效模式':<20s}{'F':>3s}{'S':>3s}{'D':>3s}{'C':>6s}{'优先级':>9s}  {'星级':<7s}备注")
for f in rank:
    p = priority(f)
    stars = '★' * min(5, max(1, int(round(p / max(priority(x) for x in rank) * 5))))
    print(f'{f[0]:<20s}{f[1]:>3d}{f[2]:>3d}{f[3]:>3d}{f[4]:>6.1f}{p:>9.1f}  {stars:<7s}{f[6]}')

dropped = [f[0] for f in FAILURES if not f[5]]
print(f'\\n已剔除（不可修，不进 backlog）：{dropped}')

names = [f[0] for f in rank]
assert '远距漏检 >90m' not in names, '物理下界必须先被剔除'
assert names.index('货车贴纸误检') < 3, '低成本高收益应排在最前'
assert names.index('积雪覆盖牌面') >= len(names) - 3, '极低频 + 高成本 -> 垫底（写进 ODD）'
assert priority(('x', 5, 9, 3, 1.0)) > priority(('x', 5, 9, 3, 8.0)), '成本越高优先级越低'

print()
print('✅ 「积雪覆盖」的正确处理不是修，而是**写进 ODD 并确保降级行为安全**。')
print('✅ D（静默性）在分子上：**越难被发现的失效，其真实代价被系统性低估**，')
print('   所以要额外加权。漏检、错误关联都属于这一类。')"""),

    code("""# 预算约束下的选择：按风险 vs 贪心 ROI vs 0/1 背包最优
def risk(f):
    return f[1] * f[2] * f[3]            # 未除以成本的绝对风险

def greedy(failures, budget, key):
    cand = sorted([f for f in failures if f[5]], key=key, reverse=True)
    chosen, spent, gained = [], 0.0, 0.0
    for f in cand:
        if spent + f[4] <= budget + 1e-9:
            chosen.append(f[0]); spent += f[4]; gained += risk(f)
    return chosen, spent, gained

def select_optimal(failures, budget, unit=0.5):
    '''0/1 背包 DP：在预算内最大化风险削减总量。'''
    cand = [f for f in failures if f[5]]
    W = int(round(budget / unit))
    w = [int(round(f[4] / unit)) for f in cand]
    v = [risk(f) for f in cand]
    dp = [0] * (W + 1)
    keep = [[] for _ in range(W + 1)]
    for i in range(len(cand)):
        for cap in range(W, w[i] - 1, -1):
            if dp[cap - w[i]] + v[i] > dp[cap]:
                dp[cap] = dp[cap - w[i]] + v[i]
                keep[cap] = keep[cap - w[i]] + [cand[i][0]]
    names_ = keep[W]
    spent = sum(f[4] for f in cand if f[0] in names_)
    return names_, spent, float(dp[W])

BUDGET = 8.0
c_risk, s_risk, g_risk = greedy(FAILURES, BUDGET, risk)         # ❌ 忽略成本
c_roi, s_roi, g_roi = greedy(FAILURES, BUDGET, priority)        # ✅ 按 ROI 贪心
c_opt, s_opt, g_opt = select_optimal(FAILURES, BUDGET)          # ✅✅ 0/1 背包最优

print(f'预算 {BUDGET} 人月')
for tag, c, s_, g_ in [('① 按绝对风险排（常见错误）', c_risk, s_risk, g_risk),
                       ('② 按 ROI = 风险/成本 贪心', c_roi, s_roi, g_roi),
                       ('③ 0/1 背包最优解', c_opt, s_opt, g_opt)]:
    print(f'\\n{tag}：花费 {s_:.1f} 人月，削减风险 {g_:.0f}')
    for nm in c:
        print(f'     · {nm}')

assert g_roi > g_risk, '同样预算下，按 ROI 选远优于按绝对风险选'
assert g_opt >= g_roi, '贪心 ROI 只是近似；0/1 背包才是最优'
assert len(c_roi) > len(c_risk), '忽略成本会一头扎进一个昂贵项目，把预算吃光'
assert '货车贴纸误检' in c_roi and '货车贴纸误检' not in c_risk

print(f'\\n✅ 同样 {BUDGET} 人月：按风险选削减 {g_risk:.0f}，按 ROI 选削减 {g_roi:.0f}'
      f'（+{g_roi / g_risk - 1:.0%}），最优解 {g_opt:.0f}。')
print('✅ **「按风险从高到低做」是最常见也最昂贵的排序错误** ——')
print('   它会让团队一头扎进一个高风险但极贵的问题（这里是「对向车道误采纳」，')
print('   8 人月吃光全部预算），而放着三四个便宜的修复不做。')
print('⚠️  但也别迷信贪心 ROI：它对 0/1 选择只是近似（这里 %.0f vs 最优 %.0f）。'
      % (g_roi, g_opt))
print('   **真正的排序问题是一个背包问题**，规模小的时候直接 DP 求最优即可。')"""),

    md("""## ✏️ 练习 1：可修漏检报告

失效分析的第一步是**分诊**：把「不可修的物理下界」从统计里剔除，否则所有优先级都会失真。

实现 `fixable_miss_report(gt_sizes, statuses, edges, min_px)`：

- `gt_sizes`：每个 GT 的像素边长；`statuses`：对应的 `attribute()` 输出的 gt_status
- `edges`：分桶边界（左闭右开，首尾为 0 与 ∞）；`min_px`：物理可检下界（小于它的漏检视为不可修）
- 返回 `{'buckets': [(label_idx, n, n_miss, miss_rate)], 'fixable_miss': …, 'unfixable_miss': …, 'worst': label_idx}`
- `worst` = **可修漏检数量最多**的桶（不是漏检率最高的桶——率最高的往往是不可修的那个）"""),
    code("""def fixable_miss_report(gt_sizes, statuses, edges, min_px):
    # TODO: ① 按 edges 分桶统计 n / n_miss / miss_rate
    #       ② 把 size < min_px 的漏检记为 unfixable，其余记为 fixable
    #       ③ worst = 可修漏检**数量**最多的桶下标
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
sizes, sts = [], []
for gts, preds in frames:
    _, gst, _ = attribute(gts, preds)
    for g_, st in zip(gts, gst):
        sizes.append(g_[2] - g_[0]); sts.append(st)

rep = fixable_miss_report(sizes, sts, EDGES, min_px=12.0)
print(f"{'桶':<9s}{'GT':>7s}{'漏检':>7s}{'漏检率':>9s}")
for b, n_, nm_, mr in rep['buckets']:
    print(f'{LABEL[b]:<9s}{n_:>7d}{nm_:>7d}{mr:>9.1%}')
print(f"\\n可修漏检 {rep['fixable_miss']}  |  不可修（<12px）{rep['unfixable_miss']}"
      f"  |  最该修的桶 = {LABEL[rep['worst']]}")

assert rep['fixable_miss'] + rep['unfixable_miss'] == sum(1 for s in sts if s == 'fn')
assert rep['unfixable_miss'] > 0, '一定有一批漏检落在物理下界之下'
assert rep['worst'] != 0, '**漏检率最高的桶是 <12px，但它不可修** —— worst 不应指向它'
assert rep['buckets'][0][3] > rep['buckets'][-1][3], '漏检率随尺寸下降'
tiny = rep['buckets'][0]
assert tiny[2] > 0 and rep['fixable_miss'] < sum(1 for s in sts if s == 'fn')
print('✅ 练习 1 通过：**先剔除不可修的部分，再决定修哪个桶** —— 这一步不做，')
print('   「整体漏检率 18%」这种数字会把团队引向一个根本无法完成的任务。')"""),

    md("""## ✏️ 练习 2：反推相机配置

「要在 80 m 检出限速牌」是一个产品需求。**把它翻译成相机参数，是感知工程师的基本功。**

实现 `plan_camera(S, p_min, Z_target, width_px)`，返回 `{'f_px':…, 'fov_deg':…}`：
使得物理尺寸 `S` 的标志在距离 `Z_target` 处至少占 `p_min` 像素。

提示：`f = p_min · Z / S`，`FOV = 2·arctan(W / (2f))`。"""),
    code("""def plan_camera(S, p_min, Z_target, width_px):
    # TODO: 由 p = f·S/Z 反解 f，再由 f 反解 FOV
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r80 = plan_camera(0.60, 16.0, 80.0, 1920)
r60 = plan_camera(0.60, 16.0, 60.0, 1920)
assert abs(r80['f_px'] - 2133.33) < 0.1, 'f = 16 × 80 / 0.6'
assert abs(r80['fov_deg'] - 48.46) < 0.2, r80
assert r60['fov_deg'] > r80['fov_deg'], '要求的距离越近，允许的 FOV 越宽'
assert abs(sign_px(0.60, 80.0, r80['f_px']) - 16.0) < 1e-6, '闭环校验：反推出来的配置确实给出 16 px'

print(f"{'目标检出距离':>12s}{'所需 f_px':>11s}{'所需 FOV':>10s}{'与广角 60° 的比较'}")
for Z in [40, 60, 80, 100]:
    r = plan_camera(0.60, 16.0, float(Z), 1920)
    cmp = '广角够用' if r['fov_deg'] >= 60.0 else f'需长焦（窄 {60 - r["fov_deg"]:.0f}°）'
    print(f'{Z:>11d}m{r["f_px"]:>11.0f}{r["fov_deg"]:>9.1f}°   {cmp}')
print('✅ 练习 2 通过：**产品需求 -> 相机参数**的翻译只有两行公式，')
print('   但它能在项目最早期就否掉「用一个广角相机做全部 TSR」这种方案。')"""),

    md("""## ✏️ 练习 3：有向风险混淆表

**混淆的频次排序 ≠ 风险排序**，而且混淆是**有方向**的。

实现 `risky_confusions(cm, severity_fn, k)`：返回按 `cm[i][j] × severity(i,j)` 降序的
前 `k` 个 `(i, j, count, sev, risk)`（跳过 `i == j`）。
再用它证明：**两个排序会发生反转** —— 存在一对混淆 A、B，A 的频次高于 B，但风险低于 B。"""),
    code("""def risky_confusions(cm, severity_fn, k=5):
    # TODO: 枚举所有 i != j，按 count × severity 降序返回前 k 个五元组
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
top_risk = risky_confusions(cm, severity, k=5)
by_count = sorted(((int(cm[i, j]), i, j) for i in range(NC) for j in range(NC) if i != j),
                  reverse=True)

print(f"{'按风险排':<24s}{'次数':>7s}{'后果':>6s}{'风险':>9s}")
for i, j, c_, sv, rk in top_risk:
    print(f'{CLASSES[i] + " -> " + CLASSES[j]:<24s}{c_:>7d}{sv:>6.1f}{rk:>9.0f}')
rank_count = [(i, j) for _, i, j in by_count]
rank_risk = [(i, j) for i, j, _, _, _ in risky_confusions(cm, severity, k=NC * NC)]
A, B = (8, 7), (0, 4)          # 禁止掉头->禁止左转（高频低后果） vs 限速30->限速80（低频高后果）
print(f'\\n{"":<24s}{"频次名次":>10s}{"风险名次":>10s}{"次数":>7s}{"后果":>6s}')
for pr in [A, B]:
    print(f'{CLASSES[pr[0]] + " -> " + CLASSES[pr[1]]:<24s}'
          f'{rank_count.index(pr) + 1:>10d}{rank_risk.index(pr) + 1:>10d}'
          f'{int(cm[pr]):>7d}{severity(*pr):>6.1f}')

assert len(top_risk) == 5 and all(len(t) == 5 for t in top_risk)
assert top_risk[0][4] >= top_risk[1][4] >= top_risk[2][4], '必须按风险降序'
assert all(t[0] != t[1] for t in top_risk), '不能包含对角线'
assert abs(top_risk[0][4] - cm[top_risk[0][0], top_risk[0][1]] * severity(*top_risk[0][:2])) < 1e-9
# 关键结论：两个排序会**反转**
assert rank_count.index(A) < rank_count.index(B), '按频次：A 排在 B 前面'
assert rank_risk.index(A) > rank_risk.index(B), '按风险：B 反超 A —— **排序反转**'
print('✅ 练习 3 通过：A 的次数更多，但 B 的风险更高 —— **只看频次会把资源投错地方**。')
print('   评测要报**有向、加权**的混淆，而不是对称的「易混对」列表。')"""),

    md("""## ✏️ 练习 4：预算-收益曲线（还值不值得再投）

有了打分器，下一个问题是「**该投多少人月**」。
对一系列预算求最优风险削减，画出边际收益曲线，就能回答它。

实现 `budget_curve(failures, budgets)`：对每个预算调用 `select_optimal`，返回
`[(budget, gained, marginal)]`，其中 `marginal = (gained_i − gained_{i−1}) / (budget_i − budget_{i−1})`
（第一项的 marginal = `gained_0 / budget_0`）。"""),
    code("""def budget_curve(failures, budgets):
    # TODO: 对每个 budget 调用 select_optimal，算累计收益与相邻两点之间的边际收益
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
BUDGETS = [1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0]
curve_ = budget_curve(FAILURES, BUDGETS)
print(f"{'预算(人月)':>10s}{'累计风险削减':>14s}{'边际收益/人月':>15s}")
for b, g_, mg in curve_:
    print(f'{b:>10.1f}{g_:>14.0f}{mg:>15.1f}')

gains = [g_ for _, g_, _ in curve_]
assert all(gains[i] <= gains[i + 1] + 1e-9 for i in range(len(gains) - 1)), '预算越多收益不会下降'
assert curve_[0][2] > curve_[-1][2], '**边际收益整体递减** —— 后面的钱越来越不值'
assert abs(curve_[0][1] - curve_[0][2] * BUDGETS[0]) < 1e-6, '第一点的 marginal = gained / budget'
assert gains[-1] > gains[0] * 3

half = next(b for b, g_, _ in curve_ if g_ >= 0.8 * gains[-1])
print(f'\\n用 {half:.0f} 人月即可拿到最终收益的 80%%（总共 {BUDGETS[-1]:.0f} 人月）。')
print('✅ 练习 4 通过：**边际收益曲线是「还值不值得再投」的唯一可信依据。**')
print('   同样的曲线在 C58 会以「还值不值得再标数据」的形式再出现一次。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def fixable_miss_report(gt_sizes, statuses, edges, min_px):
    nb = len(edges) - 1
    n = [0] * nb; nmiss = [0] * nb; fixable = [0] * nb
    unfix = 0
    for s, st in zip(gt_sizes, statuses):
        b = int(np.digitize(s, edges[1:-1]))
        n[b] += 1
        if st == 'fn':
            nmiss[b] += 1
            if s < min_px:
                unfix += 1
            else:
                fixable[b] += 1
    buckets = [(b, n[b], nmiss[b], (nmiss[b] / n[b] if n[b] else 0.0))
               for b in range(nb) if n[b] > 0]
    return {'buckets': buckets, 'fixable_miss': sum(fixable),
            'unfixable_miss': unfix, 'worst': int(np.argmax(fixable))}"""),
    code("""# 练习 2 参考答案
def plan_camera(S, p_min, Z_target, width_px):
    f = p_min * Z_target / S                                   # 由 p = f·S/Z 反解
    fov = 2.0 * math.degrees(math.atan(width_px / (2.0 * f)))  # 由 f 反解 FOV
    return {'f_px': f, 'fov_deg': fov}"""),
    code("""# 练习 3 参考答案
def risky_confusions(cm, severity_fn, k=5):
    out = []
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if i == j:
                continue
            sv = severity_fn(i, j)
            out.append((i, j, int(cm[i, j]), float(sv), float(cm[i, j] * sv)))
    return sorted(out, key=lambda t: -t[4])[:k]"""),
    code("""# 练习 4 参考答案
def budget_curve(failures, budgets):
    out, prev_b, prev_g = [], 0.0, 0.0
    for b in budgets:
        _, _, g_ = select_optimal(failures, b)
        out.append((b, g_, (g_ - prev_g) / (b - prev_b)))
        prev_b, prev_g = b, g_
    return out"""),

    md("""---
## 🧪 真实工程胶囊：失效模式台账 + 触发器 + 场景化回归门禁

可以原样复制进真实项目。三样东西缺一不可：
**一份带 ODD 边界的失效台账**、**每类失效的线上触发器**、**一套能挡住回退的场景化门禁**。"""),
    code("""RECIPE = r'''
# ─────────────────────────────────────────────────────────────
# ① 失效模式台账（configs/tsr_failure_modes.yaml）—— 评审用的唯一事实来源
# ─────────────────────────────────────────────────────────────
failure_modes:
  - id: FM-001
    name: far_range_miss_40_70m
    quadrant: FN                    # FN / FP / CLS / LOC
    cause_layer: [model, data]      # sensor / isp / model / data / association
    F: 8            # 频率  1-10（用车队日志估，不要拍脑袋）
    S: 9            # 安全后果 1-10
    D: 3            # 静默性 1-3（3 = 线上完全观测不到，必须靠回归集）
    C: 3.0          # 修复成本（人月）
    fixable: true
    odd_note: null
  - id: FM-002
    name: truck_sticker_fp
    quadrant: FP
    cause_layer: [association]
    F: 5, S: 6, D: 1, C: 0.5, fixable: true
  - id: FM-009
    name: snow_covered_sign
    quadrant: FN
    cause_layer: [sensor]
    F: 1, S: 6, D: 2, C: 10.0
    fixable: true
    odd_note: "积雪覆盖牌面时系统降级并提示接管；不承诺识别"   # <- 写进 ODD
  - id: FM-000
    name: beyond_90m_miss
    fixable: false
    reason: "物理下界：1920/60° 相机在 90m 外 0.6m 标志 < 11px"   # <- 不进 backlog

# 优先级 = F × S × D / C；不可修的**先剔除**再排序
# 预算分配是一个 0/1 背包问题，规模小时直接 DP 求最优

# ─────────────────────────────────────────────────────────────
# ② 线上触发器（每一类失效配一个，否则台账只是一张纸）
# ─────────────────────────────────────────────────────────────
TRIGGERS = {
  # 远距漏检：近处已确认的 track，回放它最早在哪一帧被检出
  "far_range_miss": lambda tr: tr.confirmed and tr.first_det_px < 14,
  # 货车贴纸：标志框被车辆框「包含」（用 containment 而不是 IoU！）
  "truck_sticker":  lambda d, vehs: any(contain_ratio(d.box, v.box) > 0.9 for v in vehs),
  # 数字混淆：多帧类别在同组内跳变，或 top1-top2 margin 过小
  "digit_confuse":  lambda tr: tr.class_switches >= 2 or tr.margin < 0.15,
  # 对向车道误采纳：上报的约束与地图/导航不一致
  "wrong_lane":     lambda out, hd: out.speed_limit != hd.lane_speed_limit,
  # 隧道/夜间：场景标签 + 分数骤降
  "scene_drop":     lambda f: f.scene in ("tunnel_in", "tunnel_out", "night_glare")
                              and f.mean_score < 0.55 * f.baseline_score,
}
# 触发率必须可控（回传带宽有限）：给每个触发器做 PR 分析，见 C58 模块 03

# ─────────────────────────────────────────────────────────────
# ③ 场景化回归门禁（CI 里跑，任何一条不过就不允许发布）
# ─────────────────────────────────────────────────────────────
GATES = [
  # (切片,                       指标,               门槛,   容差)
  ("size_16_24px",              "recall",           0.82,  -0.005),   # 不许回退
  ("size_lt_12px",              "recall",           None,   None),    # 物理下界，不设门槛
  ("night",                     "recall",           0.75,  -0.010),
  ("tunnel_transition",         "recall",           0.60,  -0.020),
  ("rain_fog",                  "recall",           0.78,  -0.010),
  ("occlusion_25_50",           "recall",           0.70,  -0.015),
  ("all",                       "FP_per_km",        0.30,  +0.02),    # 越低越好
  ("speed_limit_pairs",         "risky_confusion",  0.010, +0.002),   # 有向、加权
  ("adopted_constraints",       "adoption_acc",     0.95,  -0.005),   # 「该不该采纳」
]
# 铁律：**每个失效模式都必须对应至少一条门禁**，否则修好了也会悄悄退回去。

# ─────────────────────────────────────────────────────────────
# ④ badcase 分诊清单（每个 badcase 花 30 秒，先分堆再深挖）
# ─────────────────────────────────────────────────────────────
# 1. 四象限：漏检 / 误检 / 错分 / 定位不准？
# 2. 人眼可读性：原图上人能认出来吗？
#      不能 + 像素饱和/接近全黑  -> 传感器/ISP 问题（不是模型问题）
#      不能 + 像素太少          -> 物理下界（不可修，别进 backlog）
#      能                       -> 模型/数据问题（可修）
# 3. 是不是「认对了但不该采纳」？-> 关联问题，mAP 看不见，要单独立项
# 4. 时序上其他帧能看清吗？      -> 时序可救 -> 优先做多帧融合而不是单帧鲁棒性
'''
print(RECIPE)
for key in ['failure_modes', 'fixable: false', 'odd_note', 'TRIGGERS', 'GATES',
            'containment', 'adoption_acc', '人眼可读性']:
    assert key in RECIPE, key
print('✅ 配方覆盖：失效台账（含 ODD 与不可修剔除）/ 线上触发器 / 场景化门禁 / badcase 分诊清单')"""),

    md("""### 小结

- **先把「错了」拆成四象限**：漏检 / 误检 / 错分 / 定位不准。四类的成因、代价、修法几乎没有交集，
  混在一个 mAP 里谈必然得不出行动项。**漏检是静默失败**，只能靠主动构造的回归集监控。
- **先算物理下界再谈模型**。`p = f·S/Z`：1920/60° 相机在 60 m 外只有约 17 px，100 m 外只有 10 px。
  **不可修的失败不该进 backlog**；想看更远，加长焦相机比换模型有效得多。
- **分桶是失效分析的第二步**。TSR 的漏检高度集中在小尺寸桶；整体漏检率这个数字本身没有行动价值。
- **能写出物理模型的退化（雾、模糊、低光、卷帘快门）都该用合成增强覆盖**；
  写不出模型的（积雪、涂鸦、褪色）只能真采。这条判据可以直接用来分配数据预算。
- **临界退化强度**（分数跌破工作阈值的那一点）才是能写进需求与门禁的东西。
- **卷帘快门的直觉会严重高估它**：16 px 的牌只跨越 16 行，横向形变 < 1%；
  真正危险的是**颠簸/俯仰**（尺度误差直接变成同比例的距离误差）与 LED 相位干扰。
- **混淆必须看方向并加权**：限速 60→80 与 80→60 频次相同，风险差 3 倍以上。
  由此推出：**分类器的决策可以非对称**（在限速类上给「判高」加额外阈值代价）。
- **很多「TSR 失效」不是识别错误，而是语义与关联错误**——货车贴纸、对向车道、辅路牌。
  它们在 mAP 上完全不可见，必须有「采纳正确率」这一层指标，并把关联做成显式可测的模块。
- **优先级 = F × S × D / C**，先剔除不可修的，把极低频高成本的写进 **ODD**。
  **「按风险从高到低做」是最常见也最昂贵的排序错误**；预算分配本质是一个背包问题。
- **每个失效模式都要配一个触发器 + 一个数据动作 + 一条门禁**，否则修好了也会悄悄退回去。

下一站：**模块 04 · 时序与多帧融合** —— 本模块反复出现的「时序可救 / 时序救不了」，
到那里会变成可以量化的跟踪、投票与迟滞设计。"""),
]
