# -*- coding: utf-8 -*-
"""C57 模块 01 · 定量分析：小目标到底难在哪。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00；C18 的检测基础（IoU / anchor / FPN / stride）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_why_small_is_hard.ipynb'),
    ("核心参考", "Luo et al. 有效感受野（NeurIPS 2016）；Lin et al. FPN / RetinaNet；Xu et al. NWD / RFLA；COCO 评测协议"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("iou_shift", "IoU 对位移的敏感性：一个可以手推的闭式解", "".join([
        P("先把最重要的一件事算清楚。设两个轴对齐的正方形框，边长都是 <code>s</code>，预测框相对真值框在 x、y 两个方向各偏移 <code>d</code> 像素（<code>0 ≤ d &lt; s</code>）。交集是一个边长 <code>s-d</code> 的正方形，并集是两个面积减去交集："),
        MATH("\\mathrm{IoU}(s,d)=\\frac{(s-d)^2}{2s^2-(s-d)^2}"),
        P("若只在一个方向上偏移（1D 情形，另一轴完全对齐），交集为 <code>(s-d)·s</code>，并集为 <code>s(s+d)</code>："),
        MATH("\\mathrm{IoU}_{1D}(s,d)=\\frac{s-d}{s+d}"),
        P("两个式子都是初等代数，<strong>面试白板上三十秒能推完</strong>。代进去看数字："),
        TABLE(["边长 s", "d=1 px", "<strong>d=2 px</strong>", "d=3 px", "d=4 px", "d=0 处的斜率 dIoU/dd"], [
            ["<strong>8 px</strong>", "0.6203", "<strong>0.3913</strong>", "0.2427", "0.1429", "<strong>−0.500 /px</strong>"],
            ["16 px", "0.7840", "0.6203", "0.4927", "0.3913", "−0.250 /px"],
            ["32 px", "0.8841", "0.7840", "0.6968", "0.6203", "−0.125 /px"],
            ["<strong>64 px</strong>", "0.9399", "<strong>0.8841</strong>", "0.8323", "0.7840", "<strong>−0.0625 /px</strong>"],
            ["128 px", "0.9693", "0.9399", "0.9115", "0.8841", "−0.03125 /px"],
        ]),
        P("<strong>同样偏 2 个像素，8×8 的框 IoU 掉到 0.3913（低于 0.5，会被判成负样本），而 64×64 的框还有 0.8841（毫发无伤）——相差 2.26 倍。</strong>把 IoU 对 <code>d</code> 求导并令 <code>d→0</code>，可以得到一个极其干净的结论："),
        MATH("\\left.\\frac{\\partial \\mathrm{IoU}}{\\partial d}\\right|_{d=0}=-\\frac{4}{s}\\quad(\\text{2D 对角})\\ ,\\qquad -\\frac{2}{s}\\quad(\\text{1D})"),
        DUAL(
            "推导只需两步：记 <code>u=(s-d)²</code>，则 <code>IoU = u/(2s²-u)</code>，<code>dIoU/du = 2s²/(2s²-u)²</code>；在 <code>d=0</code> 处 <code>u=s²</code>，所以 <code>dIoU/du = 2/s²</code>，而 <code>du/dd = -2(s-d) = -2s</code>，两者相乘得 <code>-4/s</code>。<em>结论一句话：<strong>IoU 对绝对位移的敏感度与目标边长成反比</strong></em>——8px 的框每偏 1 个像素就丢掉半个 IoU，64px 的框只丢 6.25%。",
            "但必须补上一个精确的边界条件，否则会得出错误结论：<strong>IoU 本身是尺度不变的</strong>。若把位移写成相对量 <code>d = α·s</code>，则 <code>IoU = (1-α)²/(2-(1-α)²)</code>，与 <code>s</code> 完全无关。<em>也就是说，IoU 惩罚的是「相对误差」，它对尺度是绝对公平的</em>。真正的不公平来自另一侧：<strong>现实中的定位误差绝大部分是<em>绝对像素量级</em>的</strong>——标注员的手抖是 ±1–2 px、特征网格的量化误差是 stride/2、相机抖动与运动模糊是固定的几个像素。<em>把「绝对误差」喂给一把「按相对误差计分」的尺子，尺度不公平就此产生。</em>",
        ),
        CALLOUT("intuition", "这是全课的第一块基石，也是最值得背下来的一句话：<strong>IoU 是尺度不变的度量，但检测系统的误差来源是尺度不变<em>不了</em>的</strong>。所以问题不在 IoU 这个公式本身，而在「用一个相对尺子去量一堆绝对误差」这个组合。<em>后面模块 03 的 NWD 之所以有效，恰恰是因为它换了一把在绝对误差下更平滑的尺子。</em>"),
    ])),
    ("unfair", "同一个 IoU 阈值，对不同尺度极不公平", "".join([
        P("把上式反解，就得到<span class=\"term\">临界位移</span>（critical displacement）：让 IoU 恰好等于阈值 <code>τ</code> 的最大允许偏移。令 <code>(s-d)² = u</code>，由 <code>u/(2s²-u)=τ</code> 得 <code>u = 2τs²/(1+τ)</code>，于是："),
        MATH("d^{*}(s,\\tau)=s\\left(1-\\sqrt{\\tfrac{2\\tau}{1+\\tau}}\\right)"),
        P("这个式子里 <code>s</code> 是一个纯粹的比例因子——<strong>临界位移与目标边长严格成正比</strong>。代入 <code>τ=0.5</code> 得系数 <code>1-√(1/1.5) = 0.18350</code>，即 <strong><code>d* ≈ 0.1835·s</code></strong>；代入 <code>τ=0.75</code> 得 <code>0.07418·s</code>。"),
        TABLE(["目标边长", "τ=0.5 允许偏移", "τ=0.75 允许偏移", "τ=0.9 允许偏移", "翻译成人话"], [
            ["<strong>8 px</strong>（100 m 外的限速牌）", "<strong>1.47 px</strong>", "<strong>0.59 px</strong>", "0.21 px", "<strong>AP@0.75 要求亚像素级定位</strong>——比标注精度还高"],
            ["16 px（60 m）", "2.94 px", "1.19 px", "0.43 px", "刚好卡在人工标注误差的量级上"],
            ["32 px（30 m）", "5.87 px", "2.37 px", "0.85 px", "开始有余量"],
            ["<strong>64 px</strong>（15 m）", "<strong>11.74 px</strong>", "4.75 px", "1.71 px", "随便偏，怎么都过"],
            ["128 px", "23.49 px", "9.50 px", "3.41 px", "定位早已不是瓶颈"],
        ]),
        P("再把真实世界里的误差量级并排放上去，不公平就一目了然："),
        ASCII("""误差来源                                典型量级（绝对像素）  对 8px 目标  对 64px 目标
─────────────────────────────────────────────────────────────────────────
人工标注抖动（每条边）                  ±1 ~ ±2 px            **致命**     可忽略
特征网格量化（stride 8 的中心量化）      ±4 px                 **致命**     可忽略
回归头的固有噪声（≈ 0.3~1 个特征格）     ±2 ~ ±8 px            **致命**     轻微
运动模糊 / 卷帘快门（车速 120km/h）      1 ~ 3 px              **致命**     可忽略
相机标定与时间戳对齐误差                 0.5 ~ 2 px            严重         可忽略
─────────────────────────────────────────────────────────────────────────
IoU@0.5 的容忍度                        1.47 px              11.74 px
IoU@0.75 的容忍度                       0.59 px               4.75 px

结论：**同一条 "IoU >= 0.5" 的判定线，对 8px 目标要求「1.5 像素以内」，
      对 64px 目标要求「12 像素以内」——后者的容忍度是前者的 8 倍。**
      而误差源的量级对两者是一样的。""")
        ,
        DUAL(
            "这解释了一个长期被误读的现象：<strong>COCO 的 AP@[.5:.95] 对小目标格外苛刻</strong>。这个指标在 0.5 到 0.95 之间取十个阈值再平均。对 64px 目标，即使 τ=0.95 也还允许约 0.83 px 的偏移——高阈值段仍然可达；<em>而对 8px 目标，τ 一过 0.7 允许的偏移就跌破 1 个像素，后面几个阈值段的 AP 直接归零</em>。于是 AP_S 天然被压低了近一半，<strong>这一半与模型好坏无关，纯粹是指标定义带来的</strong>。",
            "所以在小目标场景，「用哪个阈值报指标」不是一个可以随便糊弄的细节。<strong>工程上的正确做法有三条</strong>：① 小目标桶只报 AP@0.5 与召回，不报 AP@[.5:.95]（并在文档里写清原因）；② 若必须用统一口径，则把它当成「同一把尺子下的相对比较」，绝不做跨尺寸桶的横向比较；③ 训练阶段用尺度自适应的分配阈值或干脆换度量（模块 03 的 NWD/RFLA）。<em>关键是<strong>把「指标口径造成的差距」与「模型能力造成的差距」分开记账</strong></em>——这两笔账混在一起，后续所有优化决策都会跑偏。",
        ),
        CALLOUT("danger", "<p><strong>面试高频问题：「为什么小目标的 AP 低？」</strong>——如果只回答「因为特征少」，是及格线以下的答案。面试官想听的是分层归因：<em>「其中一部分不是模型的问题，是指标的问题。IoU 阈值按相对误差计分，而真实误差是绝对像素量级的；对 8px 目标 IoU@0.5 只允许 1.47 px 偏移、IoU@0.75 只允许 0.59 px——已经低于标注精度。所以 AP_S 里有一块是天然的、跟模型无关的损失。剩下的才是模型的账：正样本稀缺、特征分辨率不足、标签带噪。」</em></p><p><strong>能把「指标的账」和「模型的账」拆开，是这道题的分水岭。</strong></p>", "别把指标的账算到模型头上"),
    ])),
    ("positive", "正样本稀缺：从「阈值不公平」到「一个正样本都没有」", "".join([
        P("阈值不公平的下一步后果是致命的：<strong>小目标不是「正样本少」，而是在某些配置下「在数学上不可能有正样本」</strong>。"),
        P("看一个最干净的上界。设 anchor 是边长 <code>A</code> 的正方形，目标是边长 <code>s</code> 的正方形，且 <code>s &lt; A</code>。<strong>即使中心完美重合、形状完美匹配</strong>，目标也完全落在 anchor 内部，此时交集就是目标本身，并集就是 anchor："),
        MATH("\\mathrm{IoU}_{\\max}(s,A)=\\frac{s^2}{A^2}\\qquad (s\\le A)"),
        P("这是一个<strong>上界</strong>——中心还没偏、宽高比还没错，就已经封顶了。RetinaNet 的标准 anchor 集合是 base <code>{32,64,128,256,512}</code> 乘以三档 scale <code>{2⁰, 2^(1/3), 2^(2/3)}</code>，<strong>最小的 anchor 边长是 32 px</strong>。代进去："),
        TABLE(["目标边长", "最好可能 IoU（vs 32px anchor）", "0.5 阈值下能否成为正样本", "含义"], [
            ["4 px", "0.0156", "<strong>否</strong>", "差 32 倍"],
            ["<strong>8 px</strong>", "<strong>0.0625</strong>", "<strong>否 —— 数学上不可能</strong>", "= (8/32)²，连 0.1 都到不了"],
            ["12 px", "0.1406", "<strong>否</strong>", "—"],
            ["16 px", "0.2500", "<strong>否</strong>", "—"],
            ["20 px", "0.3906", "<strong>否</strong>", "已经很接近但仍然不够"],
            ["<strong>22.63 px</strong>", "<strong>0.5000</strong>", "<strong>临界线</strong> = 32/√2", "<strong>低于此线的目标全军覆没</strong>"],
            ["24 px", "0.5625", "是（但余量极小）", "中心稍偏就掉出去"],
            ["32 px", "1.0000", "是", "完美匹配档位"],
        ]),
        P("把中心量化也算进去（目标中心均匀落在特征格内，取全图 anchor 里的最大 IoU），蒙特卡洛的结果是："),
        TABLE(["配置", "8 px 目标", "16 px", "24 px", "32 px", "64 px"], [
            ["RetinaNet P3–P7（最小 anchor 32）<br>P(max IoU ≥ 0.5)", "<strong>0.000</strong>", "<strong>0.000</strong>", "1.000", "1.000", "1.000"],
            ["同上，平均 max IoU", "0.063", "0.250", "0.563", "0.787", "0.787"],
            ["加 P2（stride 4）+ anchor 基准缩到 8<br>P(max IoU ≥ 0.5)", "<strong>0.922</strong>", "1.000", "1.000", "1.000", "1.000"],
        ]),
        DUAL(
            "这张表把「正样本稀缺」从一句抱怨变成了一个可执行的检查：<strong>拿你自己的 anchor 配置，对最小的目标尺寸算一次 <code>(s/A_min)²</code>，如果它小于分配阈值，那么这一类目标在整个训练过程中<em>一次监督信号都收不到</em></strong>。模型不是学不好，是<em>从来没被教过</em>。<em>而这个检查只需要一行除法，却是我见过最常被跳过的一步。</em>",
            "解法分三层，成本递增：<strong>① 最便宜——重新聚类 anchor</strong>（YOLOv5 起用 k-means 在自己数据的 wh 上聚类，最小 anchor 常常落在 10 px 附近，同时把匹配判据从 IoU 换成宽高比 <code>max(w/w_a, w_a/w) &lt; 4</code>，天然对尺度公平）；<strong>② 换分配策略</strong>——ATSS 用「每个 GT 的候选 anchor IoU 的均值+标准差」做自适应阈值，小目标的阈值会被自动压低；SimOTA/TaskAligned 用代价矩阵 + dynamic-k，正样本数由数据决定而不是阈值决定；<strong>③ 彻底放弃 IoU 分配</strong>——FCOS 这类 center-based 方法只问「特征点是否落在 GT 框内且在合适的尺度区间」，与框大小无关；RFLA 用感受野高斯与 GT 高斯的 KL 散度分配。<em>三层解法都在模块 03 展开。</em>",
        ),
        CALLOUT("warn", "一个常见的错误修法：<strong>把分配阈值从 0.5 一刀切降到 0.3</strong>。这确实能让小目标拿到正样本，但同时也让<em>大目标</em>吸纳一批质量很差的正样本——大目标本来余量充足，降阈值对它们纯粹是噪声。<em>结果往往是 AP_S 涨一点、AP_M/AP_L 掉更多</em>。<strong>正确的做法是「按尺度自适应」而不是「全局放宽」</strong>：小目标降、大目标不动。这一点在面试里主动提出来，能显著区别于「我把阈值调低了」这种回答。"),
    ])),
    ("stride", "stride 与特征预算：8 像素在 stride 32 上只有 0.25 个格子", "".join([
        P("第三笔账是纯粹的除法，但结论比想象中狠。特征图上一个格子对应输入图像上 <code>stride × stride</code> 的区域，所以边长 <code>s</code> 的目标在 stride 为 <code>r</code> 的特征层上占 <code>s/r</code> 个格子（线性），面积上是 <code>(s/r)²</code> 个格子。"),
        TABLE(["特征层", "stride", "8 px 目标（线性 / 面积）", "64 px 目标（线性 / 面积）", "两者的格子数之比"], [
            ["P2", "4", "2.00 格 / 4.00 格", "16.0 格 / 256 格", "64×"],
            ["P3", "8", "1.00 格 / 1.00 格", "8.0 格 / 64 格", "64×"],
            ["P4", "16", "0.50 格 / 0.25 格", "4.0 格 / 16 格", "64×"],
            ["<strong>P5</strong>", "<strong>32</strong>", "<strong>0.25 格 / 0.0625 格</strong>", "2.0 格 / 4 格", "64×"],
            ["P6", "64", "0.125 格 / 0.0156 格", "1.0 格 / 1 格", "64×"],
        ]),
        P("<strong>stride 32 的特征图上，8 像素的目标只占 0.25 个格子——它连一个格子都填不满，必须和周围 16 倍面积的背景共享同一个特征向量。</strong>而输入侧的账同样悬殊：8×8×3 = 192 个数，64×64×3 = 12288 个数，差 <strong>64 倍</strong>。"),
        ASCII("""同一块 8×8 像素的限速牌，在不同 stride 的特征图上「长什么样」：

  输入图像 (8×8 px)        stride 4 (P2)      stride 8 (P3)     stride 32 (P5)
  ┌────────┐              ┌──┬──┐            ┌──┐              ┌────────────┐
  │▓▓▓▓▓▓▓▓│              │▓▓│▓▓│            │▓▓│              │            │
  │▓░░░░░░▓│    ───►      ├──┼──┤    ───►    └──┘     ───►     │    ·       │ ← 目标只占
  │▓░6░0░░▓│              │▓▓│▓▓│                              │            │   这个格子的
  │▓▓▓▓▓▓▓▓│              └──┴──┘                              └────────────┘   1/16 面积
  └────────┘
   192 个数              2×2 = 4 个格子      1×1 = 1 个格子     0.25×0.25 = 0.0625 格

  同一层上的 64×64 目标：
                         16×16 = 256 格     8×8 = 64 格        2×2 = 4 格
                         ↑ 每一档都是 8px 目标的 **64 倍**

代价的另一面：加一层 P2（stride 4），neck + head 的空间格子总数
  P3..P7 = 1/8² + 1/16² + 1/32² + 1/64² + 1/128²  = 0.01665·HW
  P2..P7 = 上式 + 1/4²                             = 0.06665·HW
  ==> **约 4.00 倍**。这就是「加 P2」这个最直接解法的价目表。""")
        ,
        DUAL(
            "所以 <strong>stride 不是一个「架构超参」，而是「你打算给小目标留几个格子」的直接声明</strong>。工程上有一条粗糙但极好用的经验：<em>目标在最细特征层上至少要有 2×2 个格子，检测头才有可能同时表达「有没有」和「在哪、多大」这两件事</em>。反解一下：最细 stride 为 8 时，可靠工作的最小目标约 16 px；要处理 8 px 目标，最细 stride 必须到 4。<strong>这条经验反过来就是模块 00 里「网络相对定义」的由来。</strong>",
            "但 P2 的代价必须诚实地摆出来：<strong>空间格子数 ×4，而 neck 与 head 的计算量、显存、以及后处理（NMS 前的候选框数）都近似正比于格子数</strong>。更麻烦的是它<em>只帮到小目标</em>——P2 上几乎不会分配到中大目标，所以这 4 倍开销的收益完全集中在最小的那个尺寸桶。<em>在车端延迟预算里，这往往是不可接受的</em>。所以量产系统更常见的是<strong>「不加 P2，改用 ROI 裁剪 / 两级级联 / 切片推理」</strong>——它们同样提高了目标的<em>相对</em>尺寸，但只在需要的区域付出代价（模块 04）。",
        ),
        CALLOUT("intuition", "把 stride 这笔账翻译回 TSR：车端模型为了延迟通常最细只到 <strong>stride 8</strong>。按「2×2 格子」的经验，可靠工作的下限是 16 px；查模块 00 的像素预算表，1920p/60° 相机下 16 px 对应 <strong>62 米</strong>。<em>也就是说，架构一旦定死在 stride 8，「62 米外读不准限速值」就已经被写进系统里了</em>——这不是训练能补回来的。<strong>想突破 62 米，只有三条路：加 P2（贵）、上长焦相机（改硬件）、或对上半幅图做 ROI 高分辨率精检（模块 04/05 的主推方案）。</strong>"),
    ])),
    ("erf", "有效感受野：理论感受野是一张空头支票", "".join([
        P("很多人对小目标的直觉是「感受野不够大」。<strong>这个直觉恰好是反的</strong>，而且原因可以精确算出来。"),
        P("先算理论感受野（<span class=\"term\">theoretical receptive field, TRF</span>）：<code>n</code> 层 stride-1 的 3×3 卷积堆叠，TRF 的半径就是 <code>n</code>（每层向外扩 1）。但 <span class=\"term\">Luo et al. (2016)</span> 证明了：<strong>感受野内各位置对输出的贡献<em>不是均匀的</em>，而是呈近似高斯分布</strong>——中心权重极大、边缘几乎为零。这就是<span class=\"term\">有效感受野</span>（effective receptive field, ERF）。"),
        P("用最简模型可以把它算到底：把 3×3 卷积近似成一个 3 抽头的均匀核，单层在 1D 上的方差是 <code>((-1)²+0²+1²)/3 = 2/3</code>；<code>n</code> 层堆叠等价于 <code>n</code> 次独立卷积，方差可加（中心极限定理）："),
        MATH("\\sigma_{\\mathrm{ERF}}=\\sqrt{\\tfrac{2n}{3}}\\ ,\\qquad R_{\\mathrm{TRF}}=n\\ ,\\qquad \\frac{\\sigma_{\\mathrm{ERF}}}{R_{\\mathrm{TRF}}}=\\sqrt{\\tfrac{2}{3n}}\\xrightarrow[n\\to\\infty]{}0"),
        TABLE(["3×3 卷积层数 n", "理论感受野半径", "ERF 标准差 σ", "含 95% 权重的半径", "占理论感受野的比例"], [
            ["5", "5", "1.83", "3.58", "71.6%"],
            ["10", "10", "2.58", "5.06", "50.6%"],
            ["<strong>20</strong>", "<strong>20</strong>", "<strong>3.65</strong>", "<strong>7.16</strong>", "<strong>35.8%</strong>"],
            ["40", "40", "5.16", "10.12", "25.3%"],
            ["80", "80", "7.30", "14.31", "17.9%"],
        ]),
        P("<strong>理论感受野按 O(n) 增长，有效感受野只按 O(√n) 增长——网络越深，这张支票就越空。</strong>再把它和目标尺寸联系起来：设某个特征位置的 ERF 在输入图像上的标准差是 30 px（一个典型主干中层的量级），那么一个边长 <code>s</code> 的目标能占据这个神经元<em>有效输入</em>的比例是 <code>erf(s/(2σ√2))</code>（1D）与其平方（2D）："),
        TABLE(["目标边长", "占 ERF 的 1D 比例", "占 ERF 的 2D 比例", "解读"], [
            ["<strong>8 px</strong>", "<strong>10.6%</strong>", "<strong>1.1%</strong>", "<strong>该神经元 99% 的有效输入是背景</strong>"],
            ["16 px", "21.0%", "4.4%", "仍被上下文淹没"],
            ["32 px", "40.6%", "16.5%", "开始成为主要信号源"],
            ["<strong>64 px</strong>", "<strong>71.4%</strong>", "<strong>51.0%</strong>", "<strong>目标本身占了一半以上</strong>"],
            ["128 px", "96.7%", "93.5%", "几乎纯信号"],
        ]),
        DUAL(
            "这解释了为什么「小目标需要更大感受野」是个错误的直觉：<strong>问题不是感受野太小，而是感受野相对目标太大</strong>。同一个神经元，看 64px 目标时一半以上的有效输入来自目标本身，看 8px 目标时只有 1%——<em>信号被上下文按 45 倍的比例稀释了</em>。继续加深网络、继续堆大核，只会让 ERF 更大、稀释更严重。<strong>小目标需要的是「与目标尺寸<em>匹配</em>的感受野」，而不是更大的。</strong>",
            "这也给出了多尺度设计的第一性原理：<strong>FPN 的价值不只是「保留高分辨率」，更是「让每个尺度的目标去找一个 ERF 与自己匹配的特征层」</strong>。FPN 的层级分配公式 <code>k = k₀ + log₂(√(wh)/224)</code> 本质上就是在做这件匹配。<em>反过来，RTMDet 用 5×5 depthwise 大核、DETR 系用全局 attention，是在主动<strong>放大</strong> ERF——那是为大目标与长程上下文服务的设计，对小目标是中性甚至负面的</em>。<strong>「大核对小目标好」是一个必须警惕的误传。</strong>",
        ),
        CALLOUT("warn", "ERF 还有一个工程上的坑：<strong>它是随训练变化的</strong>。Luo et al. 观察到训练后的 ERF 通常会比随机初始化时更大（网络学会利用更远的上下文）。<em>所以「用初始化模型测出来的 ERF」会低估真实值</em>。测量的正确姿势是：在<strong>训练好的</strong>模型上，对某个特征位置的输出取梯度回传到输入，看输入端梯度的幅值分布——notebook 里会用一个纯 numpy 的可微堆叠把这个方法完整实现一遍。"),
    ])),
    ("noise", "标注噪声：小目标的标签本身就带噪", "".join([
        P("前四个原因都在讲模型侧。第五个原因在<strong>数据侧</strong>，而且它设定的是<strong>指标的上限</strong>——无论模型多强都突破不了。"),
        P("做一个最保守的假设：标注员画框时，每条边独立地有 <code>U(-2, +2)</code> 像素的误差（这是很温和的估计；真实标注在小目标上通常更差）。<strong>对 8 px 的框，±2 px 就是 25% 的相对误差；对 64 px 的框只有 3.1%。</strong>蒙特卡洛跑十万次："),
        TABLE(["目标边长", "标注 vs 真值的平均 IoU", "P(IoU ≥ 0.5)", "<strong>P(IoU ≥ 0.75)</strong>", "IoU 的 5% 分位"], [
            ["<strong>8 px</strong>", "<strong>0.621</strong>", "0.917", "<strong>0.083</strong>", "0.478"],
            ["16 px", "0.785", "1.000", "0.727", "0.697"],
            ["32 px", "0.885", "1.000", "1.000", "0.834"],
            ["<strong>64 px</strong>", "<strong>0.940</strong>", "1.000", "<strong>1.000</strong>", "0.913"],
            ["128 px", "0.969", "1.000", "1.000", "0.955"],
        ]),
        P("这张表要读出三个结论："),
        OL([
            "<strong>AP@0.75 在 8 px 桶上测的是标注员，不是模型。</strong>一个「完美模型」——它输出的框恰好等于物理真值——在这个桶上的 AP@0.75 上限只有 <strong>8.3%</strong>。<em>你在这个指标上做的任何优化，绝大部分是在拟合标注噪声。</em>",
            "<strong>训练信号本身带噪。</strong>回归头学的是「真值框」，而它拿到的监督是「带 25% 相对误差的框」。<em>小目标的回归分支在很大程度上是在学习噪声</em>——这也解释了为什么小目标的框普遍抖、为什么时序平滑（模块 C55）对 TSR 收益特别大。",
            "<strong>它与前四个原因完全正交。</strong>加 P2、换 NWD、提分辨率——没有任何一个能改善标注质量。<em>唯一的解法在数据侧：收紧标注规范（放大到固定倍数再画框、双人复核、亚像素标注工具）、用软标签降低对边界的确定性假设、以及把评测口径改掉。</em>",
        ]),
        DUAL(
            "工程上最有价值的一个动作，是<strong>定期测量自己数据集的「标注一致性天花板」</strong>：抽 200 个小目标让第二位标注员盲标一遍，算两份标注之间的 IoU 分布。<em>这个分布就是你在该尺寸桶上的指标上限</em>。如果一致性 IoU 的均值只有 0.65，那么「把小目标 AP@0.75 从 12 提到 15」这个 OKR 本身就是不合理的。<strong>我见过团队为一个根本不可能达成的指标烧掉一个季度——只因为没人花两天做这个测量。</strong>",
            "更精细的处理是<strong>把标注不确定性显式建模进损失</strong>：既然小目标的边界本来就不确定，就不该用一个 delta 分布去监督它。<em>把框回归成分布</em>（GFL 的 General Distribution、D-FINE 的细粒度分布优化）或用高斯建模（NWD/KLD），都能让损失对边界的小幅偏差不那么敏感。<strong>这条思路在模块 03 会与 NWD 一起讲——它同时缓解了原因 ②（度量）和原因 ⑤（标签噪声），是少见的「一药医两病」。</strong>",
        ),
        CALLOUT("danger", "<p>还有一个更隐蔽的版本：<strong>标注噪声会污染「难例挖掘」</strong>。按 loss 排序挑难例时，小目标因为标签带噪天然 loss 高，于是<em>难例池被小目标的噪声标签塞满</em>；模型反复在这些噪声上加权训练，越训越歪。<em>症状是「加了 OHEM 之后小目标反而掉点」</em>。</p><p><strong>解法：难例挖掘必须与噪声识别配套</strong>（多模型一致性、损失轨迹、重标注抽检）——这是 C58 模块 02 的核心内容。<em>在这里先埋一个钩子：凡是「按 loss 选样本」的机制，在小目标上都要额外小心。</em></p>", "别让难例挖掘吃进标注噪声"),
    ])),
    ("alias", "特征混叠与上下文依赖：信息不够时，模型在看什么", "".join([
        P("最后补两个不独立成因、但会显著放大前五条的机制。"),
        H3("① 特征混叠：两个小目标共用一个格子"),
        P("在 stride 为 <code>r</code> 的特征图上，两个中心相距 <code>g</code> 像素的目标落进同一个格子的概率（1D，中心均匀分布）是 <code>max(0, 1 - g/r)</code>。对 TSR 这是个真问题——<strong>门架上并排的指路牌、限速牌下面挂的辅助牌、施工区连续摆放的锥形牌，中心间距常常只有 15–30 px</strong>。"),
        TABLE(["中心间距 g", "stride 8 同格概率", "stride 16", "stride 32", "TSR 里的典型场景"], [
            ["10 px", "0.00", "0.375", "0.688", "远处的组合标志（主牌 + 辅助牌）"],
            ["20 px", "0.00", "0.000", "0.375", "门架上并排的两块指路牌"],
            ["30 px", "0.00", "0.000", "0.063", "中距离的两块牌"],
            ["50 px", "0.00", "0.000", "0.000", "已经安全"],
        ]),
        P("同格意味着<strong>一个特征向量必须同时表达两个目标</strong>。anchor-based 方法靠不同 anchor 分担（但小目标本来就匹配不到 anchor）；<span class=\"term\">center-based</span> 方法（FCOS/CenterNet）则会直接冲突——FCOS 用「取面积最小的那个 GT」来消歧，CenterNet 的高斯热图会把两个峰糊成一个。<em>后果是稳定的漏检，而且在指标上表现为「召回天花板」而不是「置信度低」——调阈值救不回来。</em>"),
        H3("② 上下文依赖：先验开始主导后验"),
        P("信息量少的直接后果是<strong>外观证据的似然比变弱，判断被先验主导</strong>。用对数几率写出来最清楚："),
        MATH("\\log\\frac{P(y\\mid x_{\\text{app}},c)}{P(\\bar y\\mid x_{\\text{app}},c)}=\\underbrace{\\log\\frac{P(x_{\\text{app}}\\mid y)}{P(x_{\\text{app}}\\mid \\bar y)}}_{\\text{外观证据}}+\\underbrace{\\log\\frac{P(y\\mid c)}{P(\\bar y\\mid c)}}_{\\text{上下文先验}}"),
        DUAL(
            "目标越小，第一项越接近 0，于是<strong>第二项（上下文）在决策中的权重相对越大</strong>。这不是模型「作弊」，而是贝叶斯最优的行为——<em>在证据不足时，理性的做法就是更依赖先验</em>。实际上小目标检测能工作到今天，很大程度上就是靠上下文：杆件、龙门架、天空-道路交界线、消失点附近的位置先验、以及「限速牌总是成对出现在车道两侧」这类共现规律。<strong>TSR 尤其吃这套——标志的安装位置受法规约束，先验极强。</strong>",
            "危险也正在这里：<strong>上下文先验是与域强绑定的</strong>。换一个城市（杆件样式变了）、换一种路型（高速 → 城区）、换一个国家（安装规范不同）、甚至只是换到夜间（天空-道路交界不可见），先验就失效了。<em>而模型对小目标的判断有很大一块建立在这个先验上，于是<strong>小目标的跨域掉点显著大于大目标</strong></em>。<em>这是一个在面试里很有区分度的观察</em>：「为什么我们的模型换城市后小目标掉得特别多？」——因为小目标的决策里先验占比高，而先验是最不可迁移的那部分。<strong>对策是把上下文先验显式化（用地图/车道/消失点作为独立输入），而不是让它隐式地长在特征里。</strong>",
        ),
        CALLOUT("intuition", "这两个机制的共同点是：<strong>它们不改变前五个原因的存在，但会放大它们的后果，并且让问题在评测上「换一副面孔」出现</strong>。特征混叠表现为召回天花板，上下文依赖表现为跨域崩塌——两者都不像「小目标难」，所以很容易被归错因。<em>诊断口诀：调阈值救不回来的漏检，先怀疑混叠；换域后小目标掉得比大目标多，先怀疑先验依赖。</em>"),
    ])),
    ("synthesis", "归因表：五个原因，五张不同的药方", "".join([
        P("把全部账目合到一张表上。<strong>这张表就是本课的产出，也是面试里「小目标怎么做」这道题的完整答案骨架。</strong>"),
        TABLE(["原因", "病灶", "本模块给出的量化", "解法", "代价", "副作用 / 边界"], [
            ["<strong>① 信息量少</strong>", "物理层", "8×8×3=192 vs 64×64×3=12288（<strong>64×</strong>）；固定 0.8 px 模糊下「60 vs 80」的可分性 d′ 从 32px 的约 90 掉到 8px 的约 6（局部指数 ≈ D<sup>1.95</sup>）", "提分辨率 / 长焦相机 / 切片推理 / ROI 精检", "算力按分辨率<strong>平方</strong>增长；多相机增加硬件与标定成本", "切片推理延迟不可控；长焦牺牲视野覆盖"],
            ["<strong>② IoU 对位移敏感</strong>", "度量层", "偏 2 px：<strong>0.3913 vs 0.8841</strong>；斜率 −4/s；τ=0.5 的临界位移 <strong>0.1835·s</strong>", "换度量：NWD / KLD / 尺度自适应阈值；框回归成分布", "与主流评测指标（IoU）脱钩；多一个超参", "训练用 NWD、评测用 IoU，最优解不一定重合"],
            ["<strong>③ 正样本稀缺</strong>", "分配层", "8 px 对 32 px anchor 的<strong>上界只有 0.0625</strong>；22.63 px 是死线；P(match)=0.000", "缩小/聚类 anchor、ATSS、SimOTA、RFLA、center-based 分配", "几乎零算力代价，<strong>性价比最高</strong>", "全局降阈值会伤大目标；动态分配增加训练不稳定性"],
            ["<strong>④ 下采样丢失</strong>", "架构层", "stride 32 上 8 px 只占 <strong>0.25 格</strong>；ERF 里目标只占 <strong>1.1%</strong>", "FPN/PAN/BiFPN、加 P2、可变形注意力、匹配 ERF", "加 P2 → neck+head 空间代价 <strong>×4.0</strong>", "收益只集中在最小尺寸桶；显存与 NMS 候选数同步上升"],
            ["<strong>⑤ 标注误差相对大</strong>", "数据层", "±2 px 下 8 px 框平均 IoU <strong>0.621</strong>，<strong>只有 8.3%</strong> 能达 0.75", "标注规范、双人复核、软标签/分布回归、<strong>改评测口径</strong>", "标注成本上升；评测口径变更需要跨团队对齐", "改口径会破坏与公开 benchmark 的可比性"],
        ]),
        P("为什么必须拆成五条？因为总损失是<strong>乘性</strong>的。把每个原因对小目标造成的效率折损记作 <code>rᵢ ∈ (0,1]</code>，粗略地："),
        MATH("\\frac{\\mathrm{AP}_S}{\\mathrm{AP}_L}\\ \\approx\\ \\prod_{i=1}^{5} r_i"),
        DUAL(
            "乘性结构解释了两个反复出现的工程现象：<strong>① 单点改进的收益总是低于预期</strong>——把 <code>r₄</code> 从 0.5 修到 0.9，总账只涨 1.8 倍，而其余四项还在乘；<strong>② 修到某一项之后，下一项会立刻成为新瓶颈</strong>，看起来像「怎么改都不涨」。<em>正确的心态是：小目标不存在银弹，只存在「按性价比排序的组合拳」。</em>",
            "所以本课给出的<strong>诊断顺序是有严格依据的</strong>：先查 ③（分配）——因为它几乎零算力代价、且折损常常是最狠的（<code>r₃</code> 可能直接是 0）；再查 ⑤（标注）——因为它决定指标上限，不查清楚后面所有实验都读不懂；再查 ④（架构）——代价约 4 倍，但可预期；最后才是 ①（算力/硬件）——最贵，且往往受产品约束。<em>② 贯穿其中，它既是分配问题也是损失问题，所以和 ③ 一起解决最省事。</em>",
        ),
        H3("回到 TSR：一次完整的诊断"),
        P("目标：<strong>1920×1080 / 60° FOV 主视相机，要在 60 米外读准 0.6 m 的限速牌</strong>。逐条过账："),
        UL([
            "<strong>① 像素预算</strong>：<code>1662.8 × 0.6 / 60 = 16.6 px</code>。分类下限约 16 px（笔画 ≥ 2 px），<em>刚好卡线，没有余量</em> → <strong>r₁ 已经很低，这是硬约束</strong>。",
            "<strong>② 度量</strong>：16.6 px 目标在 τ=0.5 下只容忍 <code>3.05 px</code> 偏移；而回归头的固有噪声就是这个量级 → <strong>必须换尺度自适应阈值或 NWD</strong>。",
            "<strong>③ 分配</strong>：若沿用最小 32 px 的 anchor，<code>(16.6/32)² = 0.269 &lt; 0.5</code>，<strong>这个尺寸的目标一个正样本都拿不到</strong> → <strong>最优先修，且几乎免费</strong>。",
            "<strong>④ 架构</strong>：最细 stride 8 时只有 <code>2.08 × 2.08</code> 个格子，刚好卡在「2×2」经验线上 → <em>勉强可用，但没有余量；加 P2 代价 ×4，车端难以承受</em> → <strong>转而用 ROI 精检（只处理图像上半部分/消失点附近）</strong>。",
            "<strong>⑤ 标注</strong>：16.6 px 框上 ±2 px 是 12% 相对误差，平均一致性 IoU 约 0.79 → <strong>评测必须用 AP@0.5 + 召回，AP@0.75 不可信</strong>。",
        ]),
        CALLOUT("danger", "<p>这次诊断给出的行动顺序是：<strong>改 anchor/分配（免费，收益最大）→ 改评测口径（免费，让后续实验可读）→ ROI 精检（中等代价）→ 才考虑加 P2 或换相机（最贵）</strong>。</p><p><em>而工程上最常见的错误顺序恰好是反的</em>：先换更大的 backbone、再提分辨率、再加 P2——三个动作都在修 ①④，而真正为零的 <code>r₃</code> 一直没人查。<strong>「先算 (s/A_min)² 再动手」这一行除法，能省下的时间以人月计。</strong></p>", "诊断顺序错了，算力就白烧了"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("本模块把「小目标难」拆成了五笔可计算的账。每一笔账的边缘都还有真实的开放问题："),
        UL([
            "<strong>度量该不该整体换掉</strong>：NWD/KLD 在训练侧的收益已被反复验证，但<em>评测侧仍然是 IoU 的天下</em>。于是出现「训练目标与评测目标不一致」的结构性矛盾。有工作提出把评测也换成尺度自适应阈值，但这会破坏与既有 benchmark 的可比性——<strong>这是一个社区协调问题而不是技术问题</strong>，短期内看不到解。",
            "<strong>标注噪声下的可达上限</strong>：既然 8 px 目标的标注一致性 IoU 只有 0.62，「小目标 AP 的理论上限是多少」应当是一个可以严格计算的量，但目前几乎没有论文报告自己数据集的标注一致性分布。<em>「报告指标时同时报告标注噪声水平」应该成为规范</em>，就像报告置信区间一样。",
            "<strong>有效感受野的主动控制</strong>：ERF 目前基本是架构的<em>副产物</em>（由深度、核大小、stride 被动决定）。<em>能否让 ERF 成为可学习/可调度的量</em>——按目标尺度动态选择采样范围（可变形注意力是这个方向的雏形）、或用尺度专属的分支——仍是开放的。RFLA 把感受野建模成高斯并用于分配，是把 ERF 从「隐含假设」变成「显式先验」的一次尝试。",
            "<strong>亚采样极限的信息恢复</strong>：单帧一旦低于奈奎斯特极限，信息就是真的没了。<em>但多帧不是</em>——自车运动带来的亚像素位移在原理上可以支撑超分。TSR 场景对此格外有利（标志静止、自车运动可测），然而<strong>「多帧超分 + 检测」端到端联合优化的公开工作很少，量产落地报道更少</strong>。这可能是本方向最有价值的未开垦地。",
            "<strong>合成小目标的域差</strong>：copy-paste 与渲染可以廉价制造小目标，但合成的「小」与真实的「远」在模糊核、噪声谱、ISP 响应上系统性不同。<em>缺少标准工具去度量这个域差</em>，于是「合成数据加了多少才开始有害」全靠试。",
            "<strong>评测与下游脱节</strong>：AP 不区分「漏掉一块 8 px 的限速牌」与「漏掉一块 8 px 的景点指示牌」，但两者的安全后果差着数量级。<em>代价敏感的、按距离分桶的、与下游动作挂钩的评测体系</em>（C55 模块 05）在学术上讨论很少，却是量产系统真正在用的口径。",
        ]),
        CALLOUT("paper", "必读（按本模块的推导顺序）：<em>Understanding the Effective Receptive Field in Deep Convolutional Neural Networks</em>（Luo et al., NeurIPS 2016 —— ERF 呈高斯、半径按 √n 增长的原始论证，本模块第 5 节的数值实验即复现其核心结论）；<em>Feature Pyramid Networks for Object Detection</em>（Lin et al., CVPR 2017 —— 层级分配与 ERF 匹配的第一性来源）；<em>Focal Loss for Dense Object Detection</em>（Lin et al., ICCV 2017 —— RetinaNet 的 anchor 设置，本模块「最小 anchor 32 px」的出处）；<em>A Normalized Gaussian Wasserstein Distance for Tiny Object Detection</em>（Xu et al., 2021 —— 直接针对本模块原因 ②，模块 03 展开）；<em>RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection</em>（Xu et al., ECCV 2022 —— 把 ERF 显式用于分配，同时针对原因 ③④）；<em>Generalized Focal Loss</em>（Li et al., NeurIPS 2020 —— 把框回归成分布，对应原因 ⑤ 的「软化边界」思路）。数据集侧：<em>TT100K</em>（Zhu et al., CVPR 2016）、<em>AI-TOD</em>（Wang et al., ICPR 2020，平均目标只有 12.8 px 的专门基准）。相邻课程：C18（检测基础）、C53（标签分配全谱）、C55（TSR 系统与安全评测）、C58（难例挖掘与标注噪声）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 定量分析：小目标到底难在哪（IoU-位移闭式解 / 临界位移 / anchor 上界 / stride 预算 / ERF / 标注噪声）

这是全课的**地基**。目标只有一个：把「小目标难」这句定性抱怨，
变成 **五组可以写在白板上的数字**。

**本 notebook 你会亲手实现：**
1. IoU 随位移衰减的 **1D / 2D 闭式解**，并用数值积分校验导数 `dIoU/dd = -4/s`
2. **临界位移** `d* = s(1-sqrt(2t/(1+t)))`，把 IoU 阈值翻译成「允许偏几个像素」
3. anchor 匹配的**上界** `(s/A)^2`，证明 8px 目标在标准配置下**一个正样本都拿不到**
4. stride 上的**格子预算**与两个小目标的**同格（混叠）概率**
5. **有效感受野**的数值实验：验证 `sigma_ERF = sqrt(2n/3)`，理论感受野按 O(n)、有效感受野按 O(sqrt(n))
6. 标注抖动对小框 IoU 分布的影响，以及由它决定的 **AP 上限**
7. 一个**渲染实验**：在固定镜头模糊下，「60」与「80」的可分性 d' 随尺寸怎么塌

> 心智模型：**IoU 是尺度不变的尺子，但检测系统的误差是尺度不变不了的。
> 用相对尺子去量绝对误差 —— 不公平就是这么来的。**"""),
    md("""## 1 · IoU 随位移的衰减：闭式解与数值验证

两个边长为 `s` 的轴对齐正方形，预测框相对真值在 x、y 各偏 `d` 像素：

$$\\mathrm{IoU}(s,d)=\\frac{(s-d)^2}{2s^2-(s-d)^2}\\qquad
\\mathrm{IoU}_{1D}(s,d)=\\frac{s-d}{s+d}$$"""),
    code("""import sys, math, platform, json
import numpy as np

print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
print('numpy ', np.__version__)
rng = np.random.default_rng(0)

def iou_xyxy(a, b):
    '''a, b: (..., 4) 的 [x1, y1, x2, y2]。逐对 IoU。'''
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    ix = np.maximum(0.0, np.minimum(a[..., 2], b[..., 2]) - np.maximum(a[..., 0], b[..., 0]))
    iy = np.maximum(0.0, np.minimum(a[..., 3], b[..., 3]) - np.maximum(a[..., 1], b[..., 1]))
    inter = ix * iy
    aa = (a[..., 2] - a[..., 0]) * (a[..., 3] - a[..., 1])
    bb = (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
    return inter / (aa + bb - inter)

def iou_shift_2d(s, d):
    '''闭式解：边长 s 的正方形，x、y 各偏 d。'''
    inter = max(0.0, s - d) ** 2
    return inter / (2.0 * s * s - inter)

def iou_shift_1d(s, d):
    '''闭式解：只在一个方向偏 d。'''
    return max(0.0, s - d) / (s + d)

# 闭式解 vs 直接用几何算 —— 两条路必须对上
for s in [8.0, 16.0, 64.0]:
    for d in [0.0, 1.0, 2.0, 3.7]:
        g = np.array([0.0, 0.0, s, s])
        p2 = np.array([d, d, s + d, s + d])
        p1 = np.array([d, 0.0, s + d, s])
        assert np.isclose(iou_xyxy(g, p2), iou_shift_2d(s, d)), (s, d)
        assert np.isclose(iou_xyxy(g, p1), iou_shift_1d(s, d)), (s, d)
print('OK 闭式解与几何计算一致（2D 对角 + 1D 单轴，各 12 组）')

# 本课最重要的两个数字
i8, i64 = iou_shift_2d(8, 2), iou_shift_2d(64, 2)
assert np.isclose(i8, 36 / 92) and np.isclose(i64, 3844 / 4348)
print()
print(f'8x8   框对角偏 2px -> IoU = {i8:.6f}   (= 36/92)')
print(f'64x64 框对角偏 2px -> IoU = {i64:.6f}   (= 3844/4348)')
print(f'**相差 {i64/i8:.2f} 倍；8px 的框已经掉到 0.5 阈值以下，会被判成负样本。**')"""),
    code("""# 完整的位移-IoU 表 + d=0 处的斜率
print('IoU(s, d)  —— 2D 对角位移')
print(f"{'边长 s':>9}" + ''.join(f'{("d=" + str(d) + "px"):>10}' for d in [1, 2, 3, 4]) + f"{'斜率 dIoU/dd|0':>16}")
for s in [8, 16, 32, 64, 128]:
    slope = (iou_shift_2d(s, 1e-7) - 1.0) / 1e-7          # 数值导数
    assert abs(slope - (-4.0 / s)) < 1e-3, (s, slope)      # 闭式解 -4/s
    print(f'{s:>7d}px' + ''.join(f'{iou_shift_2d(s, d):>10.4f}' for d in [1, 2, 3, 4]) + f'{slope:>16.5f}')

print()
print('1D 单轴位移（作对照，衰减慢一半）:')
print(f"{'边长 s':>9}" + ''.join(f'{("d=" + str(d) + "px"):>10}' for d in [1, 2, 3, 4]) + f"{'斜率':>16}")
for s in [8, 64]:
    slope1 = (iou_shift_1d(s, 1e-7) - 1.0) / 1e-7
    assert abs(slope1 - (-2.0 / s)) < 1e-3
    print(f'{s:>7d}px' + ''.join(f'{iou_shift_1d(s, d):>10.4f}' for d in [1, 2, 3, 4]) + f'{slope1:>16.5f}')

print()
print('==> **IoU 对绝对位移的敏感度 dIoU/dd|_0 = -4/s（2D）、-2/s（1D），与边长成反比。**')

# 但 IoU 本身是**尺度不变**的：把位移写成相对量 d = alpha*s，结果与 s 无关
print()
print('反面验证：把位移写成相对量 d = alpha*s，IoU 与 s 完全无关 ——')
for alpha in [0.05, 0.10, 0.25]:
    vals = [iou_shift_2d(s, alpha * s) for s in [8, 16, 32, 64, 128, 1000]]
    assert np.allclose(vals, vals[0]), vals
    print(f'  alpha={alpha:.2f}: ' + ' '.join(f'{v:.4f}' for v in vals) + '   <- 全部相同')
print()
print('**所以 IoU 惩罚的是「相对误差」，它对尺度是绝对公平的。**')
print('  不公平来自另一侧：现实中的定位误差绝大部分是**绝对像素量级**的')
print('  （标注手抖 +-1~2px、特征网格量化 stride/2、运动模糊几个像素）。')
print('  **用一把按相对误差计分的尺子，去量一堆绝对误差 —— 尺度不公平就此产生。**')"""),
    md("""## 2 · 临界位移：把 IoU 阈值翻译成「允许偏几个像素」

由 `(s-d)^2 / (2s^2-(s-d)^2) = t` 反解：

$$d^{*}(s,t)=s\\left(1-\\sqrt{\\frac{2t}{1+t}}\\right)$$

`s` 只是一个比例因子 —— **临界位移与目标边长严格成正比**。"""),
    code("""def critical_displacement(s, tau):
    '''让 2D 对角 IoU 恰好等于 tau 的最大允许偏移。'''
    return s * (1.0 - math.sqrt(2.0 * tau / (1.0 + tau)))

# 系数验证
k50, k75 = critical_displacement(1.0, 0.5), critical_displacement(1.0, 0.75)
print(f'tau=0.50 -> d* = {k50:.6f} * s      (即 d* ~ 0.1835 * s)')
print(f'tau=0.75 -> d* = {k75:.6f} * s')
assert abs(k50 - 0.183503) < 1e-5 and abs(k75 - 0.074180) < 1e-5

# 自洽性：把 d* 代回去必须恰好得到 tau
for s in [8, 16, 32, 64]:
    for tau in [0.3, 0.5, 0.75, 0.9]:
        assert abs(iou_shift_2d(s, critical_displacement(s, tau)) - tau) < 1e-9
print('OK 反解自洽（16 组 s x tau 代回闭式解均命中阈值）')

print()
print('「IoU 阈值」翻译成「允许偏几个像素」:')
print(f"{'边长':>8}" + ''.join(f'{("tau=" + str(t)):>12}' for t in [0.5, 0.75, 0.9]))
for s in [8, 16, 32, 64, 128]:
    print(f'{s:>6d}px' + ''.join(f'{critical_displacement(s, t):>11.2f}px' for t in [0.5, 0.75, 0.9]))

d8, d64 = critical_displacement(8, 0.5), critical_displacement(64, 0.5)
assert abs(d8 - 1.4680) < 1e-3 and abs(d64 - 11.7442) < 1e-3
assert abs(d64 / d8 - 8.0) < 1e-9, '临界位移与边长严格成正比 -> 比值就是尺寸比'
print()
print(f'**同一条 IoU>=0.5 的判定线：对 8px 目标要求「{d8:.2f}px 以内」，')
print(f'  对 64px 目标要求「{d64:.2f}px 以内」—— 后者的容忍度是前者的 {d64/d8:.0f} 倍。**')
print(f'  而 AP@0.75 对 8px 目标只允许 {critical_displacement(8, 0.75):.2f}px —— **亚像素级，比标注精度还高。**')"""),
    code("""# 把真实误差源的量级并排放上去
ERROR_SOURCES = [
    ('人工标注抖动（每条边）',        2.0),
    ('特征网格量化（stride 8 中心）',  4.0),
    ('回归头固有噪声（~0.5 格）',      4.0),
    ('运动模糊 / 卷帘快门 @120km/h',   2.0),
    ('相机标定与时间戳对齐',           1.5),
]
print(f"{'误差来源':<30}{'典型量级':>10}{'8px 目标':>14}{'64px 目标':>14}")
tol8, tol64 = critical_displacement(8, 0.5), critical_displacement(64, 0.5)
for name, mag in ERROR_SOURCES:
    v8 = '致命' if mag > tol8 else ('临界' if mag > 0.6 * tol8 else '可忽略')
    v64 = '致命' if mag > tol64 else ('临界' if mag > 0.6 * tol64 else '可忽略')
    print(f'{name:<30}{mag:>9.1f}px{v8:>14}{v64:>14}')
print(f"{'—— IoU@0.5 的容忍度':<30}{'':>10}{tol8:>13.2f}px{tol64:>13.2f}px")

n_fatal_8 = sum(1 for _, m in ERROR_SOURCES if m > tol8)
n_fatal_64 = sum(1 for _, m in ERROR_SOURCES if m > tol64)
assert n_fatal_8 == 5 and n_fatal_64 == 0, (n_fatal_8, n_fatal_64)
print()
print(f'**5 个误差源里，对 8px 目标有 {n_fatal_8} 个是致命的；对 64px 目标是 {n_fatal_64} 个。**')
print()
print('推论（面试可直接讲）: COCO 的 AP@[.5:.95] 对小目标天然不利 ——')
for tau in [0.5, 0.75, 0.85, 0.95]:
    print(f'  tau={tau:.2f}: 8px 允许 {critical_displacement(8, tau):.2f}px，'
          f'64px 允许 {critical_displacement(64, tau):.2f}px')
print('  tau 一过 0.75，8px 目标的容忍度就跌破 1 个像素 -> 高阈值段的 AP 直接归零。')
print('  **AP_S 里有一块是「指标定义造成的」，与模型好坏无关。要和「模型的账」分开记。**')"""),
    md("""## 3 · 正样本稀缺：anchor 匹配的**上界**

设 anchor 边长 `A`、目标边长 `s < A`。**即使中心完美重合、形状完美匹配**，
目标也完全落在 anchor 内部，此时

$$\\mathrm{IoU}_{\\max}(s,A)=\\frac{s^2}{A^2}$$

这是**上界** —— 中心还没偏就已经封顶了。"""),
    code("""# RetinaNet 标准 anchor：base {32,64,128,256,512} x scales {2^0, 2^(1/3), 2^(2/3)}
SCALES = [2 ** 0, 2 ** (1 / 3), 2 ** (2 / 3)]
BASES = [32, 64, 128, 256, 512]
ANCHORS = sorted(b * sc for b in BASES for sc in SCALES)
print('最小的 6 个 anchor 边长:', [round(a, 2) for a in ANCHORS[:6]])
print('最小 anchor A_min =', ANCHORS[0], 'px')

def best_possible_iou(obj_s, anchors=ANCHORS):
    '''中心完美对齐、方形目标，能拿到的最好 IoU（上界）。'''
    return max(min(obj_s, a) ** 2 / max(obj_s, a) ** 2 for a in anchors)

print()
print(f"{'目标边长':>10}{'最好可能 IoU':>16}   0.5 阈值下能否成为正样本")
for s in [4, 8, 12, 16, 20, 22.63, 24, 32, 64]:
    b = best_possible_iou(s)
    tag = '是' if b >= 0.5 else '**否 —— 数学上不可能**'
    print(f'{s:>8.5g}px{b:>16.4f}   {tag}')

assert np.isclose(best_possible_iou(8), 0.0625)
assert np.isclose(best_possible_iou(16), 0.25)
assert best_possible_iou(22.62) < 0.5 <= best_possible_iou(22.64)
s_dead = 32 / math.sqrt(2)
print()
print(f'**8px 目标对 32px anchor 的最好可能 IoU 只有 {best_possible_iou(8):.4f} = (8/32)^2。**')
print(f'  能达到 IoU 0.5 的最小目标边长 = 32/sqrt(2) = {s_dead:.4f} px —— **这是一条死线**。')
print('  低于它的目标，在整个训练过程中一次监督信号都收不到。模型不是学不好，是从来没被教过。')"""),
    code("""# 把「中心量化」也算进去：目标中心均匀落在图上，取全图 anchor 的最大 IoU（蒙特卡洛）
def max_iou_over_grid(obj_s, levels, n=20000, rng=rng):
    '''levels: [(stride, [anchor 边长, ...]), ...]。方形目标，中心均匀分布。'''
    best = np.zeros(n)
    cx = rng.uniform(0, 256, n); cy = rng.uniform(0, 256, n)
    for stride, sizes in levels:
        ax0 = (np.floor(cx / stride) + 0.5) * stride     # 所在格的 anchor 中心
        ay0 = (np.floor(cy / stride) + 0.5) * stride
        for ox in (-1, 0, 1):                            # 搜 3x3 邻域，取最好
            for oy in (-1, 0, 1):
                dx = np.abs(cx - (ax0 + ox * stride))
                dy = np.abs(cy - (ay0 + oy * stride))
                for A in sizes:
                    iw = np.clip((obj_s + A) / 2 - dx, 0, min(obj_s, A))
                    ih = np.clip((obj_s + A) / 2 - dy, 0, min(obj_s, A))
                    inter = iw * ih
                    best = np.maximum(best, inter / (obj_s ** 2 + A * A - inter))
    return best

RETINA = [(8, [32 * t for t in SCALES]), (16, [64 * t for t in SCALES]),
          (32, [128 * t for t in SCALES]), (64, [256 * t for t in SCALES]),
          (128, [512 * t for t in SCALES])]
WITH_P2 = [(4, [8 * t for t in SCALES]), (8, [16 * t for t in SCALES]),
           (16, [32 * t for t in SCALES]), (32, [64 * t for t in SCALES])]

print(f"{'目标':>7}{'RetinaNet P(>=0.5)':>21}{'平均 maxIoU':>14}"
      f"{'加P2+小anchor P(>=0.5)':>26}{'平均':>9}")
rows = {}
for s in [8, 16, 24, 32, 64]:
    a = max_iou_over_grid(s, RETINA)
    b = max_iou_over_grid(s, WITH_P2)
    rows[s] = (a, b)
    print(f'{s:>5d}px{np.mean(a >= 0.5):>21.3f}{a.mean():>14.3f}'
          f'{np.mean(b >= 0.5):>26.3f}{b.mean():>9.3f}')

assert np.mean(rows[8][0] >= 0.5) == 0.0, 'RetinaNet 配置下 8px 目标匹配率必须是 0'
assert np.mean(rows[16][0] >= 0.5) == 0.0, '16px 同样是 0'
assert np.mean(rows[32][0] >= 0.5) == 1.0
assert np.mean(rows[8][1] >= 0.5) > 0.85, '把 anchor 缩到 8 并加 P2 后应当大幅回升'
print()
print('**RetinaNet 的标准配置下，8px 与 16px 目标的正样本匹配率精确地是 0.000。**')
print(f'  把 anchor 基准缩到 8 并加上 P2（stride 4）后，8px 目标的匹配率回到 '
      f'{np.mean(rows[8][1] >= 0.5):.1%}。')
print()
print('==> 检查清单里最该加的一行（一次除法就能算）:')
print('    (最小目标尺寸 / 最小 anchor 边长)^2  <  分配阈值 ?  -> 是，则该尺寸永远拿不到正样本')
print('    修法三层: (1) 重新聚类 anchor / 换宽高比判据  (2) ATSS / SimOTA 自适应')
print('             (3) 彻底放弃 IoU 分配（FCOS 的 center sampling、RFLA 的感受野高斯）')
print('    **注意别用「全局把阈值从 0.5 降到 0.3」—— 那会让大目标吸进一堆劣质正样本。**')"""),
    md("""## 4 · stride 与特征预算：8 像素在 stride 32 上只有 0.25 个格子

边长 `s` 的目标在 stride 为 `r` 的特征层上占 `s/r` 个格子（线性）、`(s/r)^2` 个格子（面积）。
纯除法，但结论比想象中狠。"""),
    code("""print('特征格子预算')
print(f"{'层':>4}{'stride':>8}{'8px(线性/面积)':>20}{'64px(线性/面积)':>22}{'格子数之比':>12}")
for lvl, r in [('P2', 4), ('P3', 8), ('P4', 16), ('P5', 32), ('P6', 64)]:
    a_lin, b_lin = 8 / r, 64 / r
    ratio = (b_lin ** 2) / (a_lin ** 2)
    print(f'{lvl:>4}{r:>8d}'
          f'{f"{a_lin:.3g} / {a_lin**2:.4g}":>20}'
          f'{f"{b_lin:.3g} / {b_lin**2:.4g}":>22}'
          f'{ratio:>11.0f}x')

assert np.isclose(8 / 32, 0.25) and np.isclose((8 / 32) ** 2, 0.0625)
print()
print(f'**stride 32 的特征图上，8 像素的目标只占 {8/32:.2f} 个格子（面积 {(8/32)**2:.4f} 格）——')
print('  它连一个格子都填不满，必须和周围 16 倍面积的背景共享同一个特征向量。**')

# 输入侧的像素预算
print()
for s in [8, 16, 32, 64]:
    print(f'  {s:>3d}x{s:<3d} RGB patch = {s*s*3:>6d} 个数')
assert (64 * 64 * 3) / (8 * 8 * 3) == 64.0
print(f'  ==> 64px 目标的原始像素预算是 8px 目标的 {(64*64*3)//(8*8*3)} 倍。')

# 「2x2 格子」经验线 -> 最细 stride 决定了可靠工作的最小目标
print()
print('经验线：目标在最细特征层上至少要有 2x2 个格子，检测头才能同时表达「有没有」与「在哪多大」')
for finest in [4, 8, 16]:
    print(f'  最细 stride {finest:>2d}  ->  可靠工作的最小目标约 {2*finest:>3d} px')

# 加 P2 的代价：neck/head 的空间格子总数
base = sum(1.0 / (r ** 2) for r in [8, 16, 32, 64, 128])       # P3..P7
withp2 = base + 1.0 / (4 ** 2)                                  # P2..P7
print()
print(f'加 P2 的代价:  P3..P7 = {base:.5f}*HW 格   ->   P2..P7 = {withp2:.5f}*HW 格')
print(f'  ==> **约 {withp2/base:.2f} 倍**。这就是「加 P2」这个最直接解法的价目表。')
assert 3.95 < withp2 / base < 4.05
print('  而且这 4 倍开销的收益**完全集中在最小的那个尺寸桶**（P2 上几乎不分配中大目标），')
print('  显存与 NMS 前的候选框数也同步上升 —— 车端往往不可接受。')"""),
    code("""# 特征混叠：两个小目标落进同一个格子的概率（1D，中心均匀分布）
def same_cell_prob(gap, stride):
    return max(0.0, 1.0 - gap / stride)

print('两个目标中心相距 gap 时，落进同一个特征格的概率')
print(f"{'gap':>7}" + ''.join(f'{("stride " + str(r)):>13}' for r in [8, 16, 32]))
for gap in [10, 20, 30, 50]:
    print(f'{gap:>5d}px' + ''.join(f'{same_cell_prob(gap, r):>13.3f}' for r in [8, 16, 32]))

assert np.isclose(same_cell_prob(10, 16), 0.375)
assert np.isclose(same_cell_prob(20, 32), 0.375)
assert same_cell_prob(50, 32) == 0.0

# 蒙特卡洛校验闭式解
n = 200000
cx = rng.uniform(0, 320, n)
for gap, r in [(10, 16), (20, 32), (30, 32)]:
    same = (np.floor(cx / r) == np.floor((cx + gap) / r)).mean()
    assert abs(same - same_cell_prob(gap, r)) < 0.01, (gap, r, same)
print()
print('OK 闭式解 max(0, 1-gap/stride) 与蒙特卡洛一致')

# center-based 头的冲突消歧（FCOS：同格冲突时取面积最小的 GT）
print()
print('同格冲突时 center-based 头会发生什么（FCOS 用「取面积最小的 GT」消歧）:')
gts = [('主限速牌 60', 18.0), ('下挂辅助牌 货车', 12.0)]   # (名字, 边长)
winner = min(gts, key=lambda t: t[1] ** 2)
loser = max(gts, key=lambda t: t[1] ** 2)
print(f'  两块牌中心相距 10px，stride 16 -> 同格概率 {same_cell_prob(10, 16):.1%}')
print(f'  同格时只有「{winner[0]}」能被这个特征点认领，「{loser[0]}」**直接漏掉**')
assert winner[0] == '下挂辅助牌 货车'
print()
print('==> 后果是**召回天花板**而不是「置信度低」—— 调 score 阈值救不回来。')
print('    诊断口诀：**调阈值救不回来的漏检，先怀疑特征混叠。**')
print('    TSR 里的高发场景：门架上并排的指路牌、限速牌下挂的辅助牌、连续摆放的施工锥牌。')"""),
    md("""## 5 · 有效感受野：理论感受野是一张空头支票

`n` 层 stride-1 的 3x3 卷积，理论感受野半径 `R = n`（每层向外扩 1）。
但把 3x3 近似成 3 抽头均匀核，单层 1D 方差 `((-1)^2+0^2+1^2)/3 = 2/3`，
`n` 层方差可加（中心极限定理）：

$$\\sigma_{\\mathrm{ERF}}=\\sqrt{\\frac{2n}{3}},\\qquad
\\frac{\\sigma_{\\mathrm{ERF}}}{R_{\\mathrm{TRF}}}=\\sqrt{\\frac{2}{3n}}\\ \\to\\ 0$$

**理论感受野按 O(n) 增长，有效感受野只按 O(sqrt(n)) 增长。**"""),
    code("""def erf_profile(n_layers, half=400):
    '''把一个 delta 连续通过 n 层 3 抽头均匀核，得到 1D 的有效感受野权重分布。'''
    x = np.zeros(2 * half + 1); x[half] = 1.0
    k = np.ones(3) / 3.0
    for _ in range(n_layers):
        x = np.convolve(x, k, mode='same')
    return x

print(f"{'层数 n':>7}{'理论RF半径':>12}{'ERF std(实测)':>15}{'公式 sqrt(2n/3)':>17}"
      f"{'std/RF':>9}{'95%质量半径':>13}{'占RF比例':>10}")
for n_layers in [5, 10, 20, 40, 80]:
    p = erf_profile(n_layers)
    half = (len(p) - 1) // 2
    idx = np.arange(len(p)) - half
    var = (p * idx ** 2).sum() / p.sum()
    std = math.sqrt(var)
    formula = math.sqrt(2 * n_layers / 3)
    r95 = 1.96 * std
    assert abs(std - formula) < 1e-6, (n_layers, std, formula)     # 精确命中闭式解
    print(f'{n_layers:>7d}{n_layers:>12d}{std:>15.3f}{formula:>17.3f}'
          f'{std/n_layers:>9.3f}{r95:>13.2f}{r95/n_layers:>9.1%}')

p20 = erf_profile(20); h20 = (len(p20) - 1) // 2
idx20 = np.arange(len(p20)) - h20
std20 = math.sqrt((p20 * idx20 ** 2).sum() / p20.sum())
assert abs(std20 - 3.651) < 1e-3
assert 1.96 * std20 / 20 < 0.40, 'n=20 时 95% 权重只落在理论感受野不到 40% 的半径内'
print()
print(f'**n=20 时：理论感受野半径 20，但 95% 的权重只落在半径 {1.96*std20:.2f} 之内'
      f'（理论值的 {1.96*std20/20:.1%}）。**')
print('  网络越深，这张支票就越空 —— TRF 按 O(n) 涨，ERF 只按 O(sqrt(n)) 涨。')
print()
print('注：真实网络还有 ReLU/BN/跳连，ERF 会更集中；且训练后的 ERF 通常比初始化时更大。')
print('    所以「用初始化模型测 ERF」会低估真实值 —— 要在**训练好的**模型上用梯度回传法测。')"""),
    code("""# 目标在 ERF 里的「信噪比」：目标本身占该神经元有效输入的多少
def frac_in_erf_1d(obj_px, sigma_px):
    '''高斯 ERF 下，宽度 obj_px 的目标覆盖的权重比例（1D）。'''
    return math.erf(obj_px / (2.0 * sigma_px * math.sqrt(2.0)))

SIGMA = 30.0     # 某个主干中层的 ERF 在输入图像上的标准差（典型量级）
print(f'设该特征位置的 ERF 在输入上 sigma = {SIGMA:.0f} px')
print(f"{'目标边长':>10}{'占ERF(1D)':>12}{'占ERF(2D)':>12}   解读")
vals = {}
for s in [8, 16, 32, 64, 128]:
    f1 = frac_in_erf_1d(s, SIGMA); f2 = f1 * f1
    vals[s] = f2
    note = ('该神经元 99% 的有效输入是背景' if f2 < 0.02 else
            '仍被上下文淹没' if f2 < 0.10 else
            '开始成为主要信号源' if f2 < 0.40 else
            '目标本身占了一半以上' if f2 < 0.90 else '几乎纯信号')
    print(f'{s:>8d}px{f1:>12.4f}{f2:>12.4f}   {note}')

assert abs(frac_in_erf_1d(8, SIGMA) - 0.1061) < 1e-3
assert abs(frac_in_erf_1d(64, SIGMA) - 0.7139) < 1e-3
assert vals[64] / vals[8] > 40, '2D 上 64px 与 8px 的信噪比应差 40 倍以上'
print()
print(f'**同一个神经元，看 64px 目标时 {vals[64]:.1%} 的有效输入来自目标本身，')
print(f'  看 8px 目标时只有 {vals[8]:.2%} —— 信号被上下文按 {vals[64]/vals[8]:.0f} 倍的比例稀释。**')
print()
print('==> 所以「小目标需要更大感受野」是**反的**：问题不是感受野太小，是感受野相对目标太大。')
print('    继续加深、继续堆大核 -> ERF 更大 -> 稀释更严重。')
print('    小目标需要的是**与目标尺寸匹配**的感受野 —— 这正是 FPN 层级分配的第一性原理')
print('    （k = k0 + log2(sqrt(wh)/224) 就是在做这件匹配）。')
print('    反面例子：RTMDet 的 5x5 大核、DETR 的全局 attention 都在**放大** ERF，')
print('    那是为大目标与长程上下文服务的设计，**「大核对小目标好」是必须警惕的误传**。')"""),
    md("""## 6 · 标注噪声：小目标的标签本身就带噪

前五节都在讲模型侧。这一节在**数据侧**，而且它设定的是**指标的上限** ——
无论模型多强都突破不了。

保守假设：标注员画框时每条边独立有 `U(-2, +2)` px 误差。
**对 8px 框这是 25% 的相对误差；对 64px 框只有 3.1%。**"""),
    code("""def annotation_iou_samples(s, jitter=2.0, n=100000, kind='uniform', rng=rng):
    '''真值框 vs 带噪标注框的 IoU 分布。'''
    gt = np.tile(np.array([0.0, 0.0, s, s]), (n, 1))
    e = (rng.uniform(-jitter, jitter, size=(n, 4)) if kind == 'uniform'
         else rng.normal(0.0, jitter, size=(n, 4)))
    nb = gt + e
    nb[:, 2] = np.maximum(nb[:, 2], nb[:, 0] + 0.5)      # 防止退化成负宽高
    nb[:, 3] = np.maximum(nb[:, 3], nb[:, 1] + 0.5)
    return iou_xyxy(gt, nb)

print('每条边 U(-2, +2) px 抖动下，标注 vs 真值的 IoU')
print(f"{'边长':>7}{'相对误差':>10}{'平均IoU':>10}{'P(>=0.5)':>11}{'P(>=0.75)':>12}{'5%分位':>9}")
res = {}
for s in [8, 16, 32, 64, 128]:
    v = annotation_iou_samples(s); res[s] = v
    print(f'{s:>5d}px{2/s:>10.1%}{v.mean():>10.4f}{np.mean(v>=0.5):>11.4f}'
          f'{np.mean(v>=0.75):>12.4f}{np.percentile(v,5):>9.4f}')

assert 0.60 < res[8].mean() < 0.65, res[8].mean()
assert np.mean(res[8] >= 0.75) < 0.15
assert np.mean(res[64] >= 0.75) > 0.99
assert abs(2 / 8 - 0.25) < 1e-12, '+-2px 对 8px 框正好是 25% 的相对误差'
print()
print(f'**+-2px 对 8px 框是 {2/8:.0%} 的相对误差；对 64px 框只有 {2/64:.1%}。**')

# 这就是「完美模型」的 AP 上限：模型输出等于物理真值，但标签是带噪的
print()
print('推论：一个「完美模型」（输出恰好等于物理真值）在各尺寸桶上的 AP 上限')
print(f"{'边长':>7}{'AP@0.5 上限':>14}{'AP@0.75 上限':>15}")
for s in [8, 16, 32, 64]:
    print(f'{s:>5d}px{np.mean(res[s]>=0.5):>14.1%}{np.mean(res[s]>=0.75):>15.1%}')
print()
print(f'**8px 桶上 AP@0.75 的天花板只有 {np.mean(res[8]>=0.75):.1%} —— 这个指标测的是标注员，不是模型。**')

# 抖动模型换成高斯，结论不变
vg = annotation_iou_samples(8, jitter=1.0, kind='normal')
assert 0.65 < vg.mean() < 0.72, vg.mean()
print(f'  换成每边 N(0,1) 的更温和抖动：8px 框平均 IoU 仍只有 {vg.mean():.3f}，'
      f'达到 0.75 的比例 {np.mean(vg>=0.75):.1%}')
print()
print('三条结论:')
print(' 1) AP@0.75 在小目标桶上测的是标注员 -> 小目标只报 AP@0.5 + 召回')
print(' 2) **训练信号本身带噪** -> 小目标回归分支很大程度在学噪声（框抖、时序平滑收益大）')
print(' 3) 与前四个原因**完全正交** -> 加 P2 / 换 NWD / 提分辨率都改善不了标注质量')
print()
print('工程动作：抽 200 个小目标让第二位标注员盲标，算两份标注的 IoU 分布 ——')
print('**那个分布就是你在该尺寸桶上的指标上限。** 不做这个测量就定 OKR，很可能在追一个不可能的数。')"""),
    code("""# 可分性 d'：在**固定的镜头/传感器模糊**下，「60」与「80」随尺寸还能不能分开
FONT5x7 = {
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '3': ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
}

def render_sign(text, R=96):
    '''高分辨率渲染一块圆形限速牌：白底 + 暗环（红环的灰度替身）+ 黑数字。'''
    img = np.ones((R, R))
    yy, xx = np.mgrid[0:R, 0:R]
    rad = np.sqrt((xx - (R - 1) / 2) ** 2 + (yy - (R - 1) / 2) ** 2) / (R / 2)
    img[rad > 1.0] = 0.35                       # 牌外背景
    img[(rad <= 1.0) & (rad > 0.80)] = 0.25     # 环，厚度 = 直径的 10%
    gw, gh = int(0.20 * R), int(0.40 * R)       # 每个数字：宽 0.20R，高 0.40R
    for k, ch in enumerate(text):
        bm = FONT5x7[ch]
        x0 = int(R / 2 - 0.24 * R + k * 0.24 * R); y0 = int(R / 2 - 0.20 * R)
        for i in range(gh):
            for j in range(gw):
                if bm[i * 7 // gh][j * 5 // gw] == '1' and 0 <= y0 + i < R and 0 <= x0 + j < R:
                    img[y0 + i, x0 + j] = 0.0
    return img

def area_downsample(img, D):
    R = img.shape[0]; e = np.linspace(0, R, D + 1).astype(int); out = np.zeros((D, D))
    for i in range(D):
        for j in range(D):
            out[i, j] = img[e[i]:e[i + 1], e[j]:e[j + 1]].mean()
    return out

def blur(img, sig):
    '''可分离高斯模糊。sig 的单位是**成像后的像素** —— 镜头/ISP 的模糊是绝对量级的。'''
    r = max(1, int(3 * sig)); x = np.arange(-r, r + 1)
    k = np.exp(-x ** 2 / (2 * sig * sig)); k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 0, img)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 1, out)

sign60, sign80 = render_sign('60'), render_sign('80')
SENSOR_NOISE = 4 / 255.0        # 典型车载相机的读出噪声量级
BLUR_PX = 0.8                   # 镜头 + ISP 的模糊，单位是像素（**与目标大小无关**）

print(f'固定 {BLUR_PX} px 的镜头模糊 + sigma={SENSOR_NOISE:.4f} 的传感器噪声')
print(f"{'牌子直径 D':>12}{'笔画宽 D/8':>12}{'可分性 d(60 vs 80)':>22}")
dp = {}
for D in [4, 6, 8, 12, 16, 24, 32, 48, 64]:
    a = blur(area_downsample(sign60, D), BLUR_PX)
    b = blur(area_downsample(sign80, D), BLUR_PX)
    dp[D] = float(np.linalg.norm(a - b) / SENSOR_NOISE)
    print(f'{D:>10d}px{D/8:>12.2f}{dp[D]:>22.2f}')

ks = [4, 6, 8, 12, 16, 24, 32, 48, 64]
assert all(dp[x] < dp[y] for x, y in zip(ks[:-1], ks[1:])), '可分性必须随尺寸单调上升'
assert dp[32] > 5 * dp[8], (dp[8], dp[32])
expo = math.log(dp[32] / dp[8]) / math.log(32 / 8)
assert expo > 1.4, expo
print()
print(f'**尺寸从 8px 到 32px（4 倍），可分性 d 从 {dp[8]:.1f} 涨到 {dp[32]:.1f}'
      f'（{dp[32]/dp[8]:.1f} 倍）—— 局部指数约 D^{expo:.2f}，比线性还快。**')
print('  原因：模糊是**绝对像素量级**的，它抹掉的细节量固定，')
print('        但这个固定量对小目标是致命比例、对大目标可忽略 —— 又一个「绝对 vs 相对」。')
print()
print('奈奎斯特判据（限速牌的数字笔画宽约为直径的 1/8，环厚约 1/10）:')
print(f'  要读出数字，笔画需 >= 2px -> D >= {8*2} px')
print(f'  要检出牌子，环需 >= 2px   -> D >= {10*2} px')
f60 = (1920 / 2) / math.tan(math.radians(30))
print(f'  1920p/60deg 相机、0.6m 的牌: 16px 对应 {f60*0.6/16:.1f} m，20px 对应 {f60*0.6/20:.1f} m')
print('  **这是物理极限，不是模型能力问题** —— 唯一的解法是给更多像素。')"""),
    md("""## ✏️ 练习 1：构造一个「尺度公平」的 IoU 阈值

现在的问题是：**同一个 IoU 阈值对不同尺度不公平**。反过来想 ——
如果我们规定所有尺度都享有**同一个绝对位移容忍度** `d_tol`（像素），
那么每个尺寸对应的 IoU 阈值应该是多少？

实现 `scale_fair_threshold(s, d_tol)`：返回边长 `s` 的目标在容忍 `d_tol` 像素
对角位移时对应的 IoU 阈值。

这正是模块 03「尺度自适应阈值」的构造方法 —— **一行代码，但它把不公平消掉了。**"""),
    code("""def scale_fair_threshold(s, d_tol):
    # TODO: 返回边长 s、容忍 d_tol 像素对角位移时等价的 IoU 阈值
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
assert abs(scale_fair_threshold(8, 2) - 36 / 92) < 1e-9
assert abs(scale_fair_threshold(64, 2) - 3844 / 4348) < 1e-9

# 单调性：同样容忍 2px，目标越大要求的阈值越高
taus = [scale_fair_threshold(s, 2) for s in [8, 16, 32, 64, 128, 512]]
assert all(a < b for a, b in zip(taus[:-1], taus[1:])), taus
assert taus[-1] > 0.98, '目标足够大时阈值趋近 1'

# **核心自洽性**：用这套阈值反推临界位移，所有尺度必须得到同一个 d_tol
for d_tol in [1.0, 2.0, 3.5]:
    for s in [8, 16, 32, 64, 128]:
        back = critical_displacement(s, scale_fair_threshold(s, d_tol))
        assert abs(back - d_tol) < 1e-8, (s, d_tol, back)
print('OK 自洽：这套阈值下，所有尺度的绝对位移容忍度**完全相同**')

print()
print(f"{'边长':>7}{'固定阈值 0.5':>14}{'尺度公平阈值(d_tol=2px)':>26}")
for s in [8, 16, 32, 64, 128]:
    print(f'{s:>5d}px{0.5:>14.4f}{scale_fair_threshold(s, 2):>26.4f}')
print()
print('对比：固定 0.5 阈值下，8px 目标只容忍 1.47px、64px 容忍 11.74px（差 8 倍）；')
print('      尺度公平阈值下，所有尺度都容忍 2.00px。')
print('✅ 练习 1 通过：**不公平不在 IoU 公式里，在「所有尺度共用一个阈值」这个约定里。**')"""),
    md("""## ✏️ 练习 2：anchor 覆盖诊断器

实现 `anchor_coverage(anchor_sizes, obj_sizes, thr=0.5)`，返回

```python
{'best_iou': [...],            # 每个目标的最好可能 IoU（上界）
 'impossible': [...],          # 布尔列表：该尺寸是否「数学上不可能」成为正样本
 'impossible_frac': float,     # 不可能的比例
 'min_anchor_needed': float}   # 要让**最小**的目标也能达到 thr，最小 anchor 应该 <= 多少
```

提示：`IoU_max(s, A) = min(s,A)^2 / max(s,A)^2`；要让边长 `s_min` 的目标达到 `thr`，
需要 `A <= s_min / sqrt(thr)`。"""),
    code("""def anchor_coverage(anchor_sizes, obj_sizes, thr=0.5):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r = anchor_coverage(ANCHORS, [8, 16, 24, 32], thr=0.5)
assert abs(r['best_iou'][0] - 0.0625) < 1e-12, r['best_iou'][0]
assert abs(r['best_iou'][1] - 0.25) < 1e-12
assert r['impossible'] == [True, True, False, False], r['impossible']
assert abs(r['impossible_frac'] - 0.5) < 1e-12
assert abs(r['min_anchor_needed'] - 8 / math.sqrt(0.5)) < 1e-9, r['min_anchor_needed']

# 用求出来的 min_anchor_needed 作为最小 anchor 重算 -> 应当全部可行
fixed = sorted([r['min_anchor_needed'] * t for t in SCALES] + ANCHORS)
r2 = anchor_coverage(fixed, [8, 16, 24, 32], thr=0.5)
assert r2['impossible_frac'] == 0.0, r2['impossible']

# 阈值更严时，需要的 anchor 更小
assert (anchor_coverage(ANCHORS, [8], thr=0.75)['min_anchor_needed']
        < anchor_coverage(ANCHORS, [8], thr=0.5)['min_anchor_needed'])

print(f"{'目标':>7}{'最好可能IoU':>14}{'是否不可能':>12}")
for s, b, imp in zip([8, 16, 24, 32], r['best_iou'], r['impossible']):
    print(f'{s:>5d}px{b:>14.4f}{("是" if imp else "否"):>12}')
print()
print(f"当前配置下 {r['impossible_frac']:.0%} 的尺寸档「数学上不可能」成为正样本")
print(f"要救回 8px 目标，最小 anchor 必须 <= {r['min_anchor_needed']:.2f} px"
      f"（当前是 {min(ANCHORS):.0f} px）")
print('✅ 练习 2 通过：**这一行除法应该出现在每个检测项目的启动检查清单里。**')"""),
    md("""## ✏️ 练习 3：标注噪声决定的 AP 上限

实现 `ap_ceiling(s, jitter=2.0, tau=0.5, n=50000)`：
返回「一个完美模型（输出恰好等于物理真值）」在该尺寸桶上能达到的 **AP 上限** ——
也就是「带噪标注框与真值框的 IoU ≥ tau」的比例。

（可以直接复用上面的 `annotation_iou_samples`。）"""),
    code("""def ap_ceiling(s, jitter=2.0, tau=0.5, n=50000):
    # TODO: 返回 0~1 的上限
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
c8_75 = ap_ceiling(8, 2.0, 0.75)
c8_50 = ap_ceiling(8, 2.0, 0.50)
c64_75 = ap_ceiling(64, 2.0, 0.75)
assert c8_75 < 0.15, c8_75
assert c8_50 > 0.85, c8_50
assert c64_75 > 0.99, c64_75
assert 0.0 <= c8_75 <= 1.0

# 单调性：目标越大上限越高；阈值越严上限越低；抖动越大上限越低
seq = [ap_ceiling(s, 2.0, 0.75) for s in [8, 16, 32, 64]]
assert all(a <= b + 1e-9 for a, b in zip(seq[:-1], seq[1:])), seq
assert ap_ceiling(16, 2.0, 0.9) < ap_ceiling(16, 2.0, 0.5)
assert ap_ceiling(16, 4.0, 0.75) < ap_ceiling(16, 1.0, 0.75)

print(f"{'边长':>7}{'AP@0.5 上限':>14}{'AP@0.75 上限':>15}{'AP@0.9 上限':>14}")
for s in [8, 16, 32, 64, 128]:
    print(f'{s:>5d}px{ap_ceiling(s,2.0,0.5):>14.1%}'
          f'{ap_ceiling(s,2.0,0.75):>15.1%}{ap_ceiling(s,2.0,0.9):>14.1%}')
print()
print('**表里凡是明显低于 100% 的格子，那个指标测的都是标注员而不是模型。**')
print('✅ 练习 3 通过：定 OKR 之前先把这张表算出来 —— 别去追一个不可能的数')"""),
    md("""## ✏️ 练习 4：可检测尺寸下界与最远作用距离（本模块的收官题）

把物理层（奈奎斯特）与架构层（stride）两个下界合起来，求出系统真正的作用距离。

实现 `min_size_and_range(width_px, hfov_deg, size_m, finest_stride,
stroke_ratio=1/8, nyquist_px=2.0, cells_needed=2.0)`，返回

```python
{'min_px_nyquist': …,   # 物理下界：stroke = D*stroke_ratio >= nyquist_px
 'min_px_stride':  …,   # 架构下界：D >= cells_needed * finest_stride
 'min_px':         …,   # 两者取大 —— **谁大谁是瓶颈**
 'bottleneck':     'physics' 或 'architecture',
 'max_range_m':    …}   # f*S/min_px
```

**做完之后请特别留意 `bottleneck` 这个字段随 `finest_stride` 的变化 ——
它演示了「修好一个原因之后，瓶颈会立刻换到下一个原因」。**"""),
    code("""def min_size_and_range(width_px, hfov_deg, size_m, finest_stride,
                       stroke_ratio=1/8, nyquist_px=2.0, cells_needed=2.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
r8 = min_size_and_range(1920, 60.0, 0.6, finest_stride=8)
assert abs(r8['min_px_nyquist'] - 16.0) < 1e-9, r8['min_px_nyquist']
assert abs(r8['min_px_stride'] - 16.0) < 1e-9
assert abs(r8['min_px'] - 16.0) < 1e-9
assert abs(r8['max_range_m'] - 62.35) < 0.1, r8['max_range_m']

r16 = min_size_and_range(1920, 60.0, 0.6, finest_stride=16)
assert abs(r16['min_px'] - 32.0) < 1e-9 and r16['bottleneck'] == 'architecture'
assert abs(r16['max_range_m'] - 31.18) < 0.1

r4 = min_size_and_range(1920, 60.0, 0.6, finest_stride=4)      # 加 P2
assert abs(r4['min_px'] - 16.0) < 1e-9, '加 P2 后架构下界降到 8px，物理下界 16px 成为瓶颈'
assert r4['bottleneck'] == 'physics'
assert abs(r4['max_range_m'] - r8['max_range_m']) < 1e-6, '**加 P2 一米都没多看到**'

r4k = min_size_and_range(3840, 60.0, 0.6, finest_stride=4)      # 加 P2 + 换 4K
assert r4k['max_range_m'] > 1.9 * r4['max_range_m']

print(f"{'配置':<28}{'物理下界':>10}{'架构下界':>10}{'实际下界':>10}{'瓶颈':>14}{'最远距离':>11}")
for label, kw in [('1080p, stride 16', dict(width_px=1920, finest_stride=16)),
                  ('1080p, stride 8 (基线)', dict(width_px=1920, finest_stride=8)),
                  ('1080p, stride 4 (加 P2)', dict(width_px=1920, finest_stride=4)),
                  ('4K,    stride 4 (P2+4K)', dict(width_px=3840, finest_stride=4))]:
    v = min_size_and_range(hfov_deg=60.0, size_m=0.6, **kw)
    print(f"{label:<28}{v['min_px_nyquist']:>9.1f}px{v['min_px_stride']:>9.1f}px"
          f"{v['min_px']:>9.1f}px{v['bottleneck']:>14}{v['max_range_m']:>10.1f}m")
print()
print('**注意第 2 行到第 3 行：加了 P2（代价 4 倍算力），最远距离一米都没多。**')
print('  因为瓶颈已经从架构层（stride）换到了物理层（奈奎斯特）——')
print('  此时该做的是换相机/提分辨率（第 4 行），而不是继续在架构上加码。')
print('✅ 练习 4 通过：**这就是「五个原因互相正交」在工程上的真实样子。**')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def scale_fair_threshold(s, d_tol):
    '''容忍 d_tol 像素对角位移时，边长 s 对应的等价 IoU 阈值。'''
    inter = max(0.0, s - d_tol) ** 2
    return inter / (2.0 * s * s - inter)          # 就是 iou_shift_2d(s, d_tol)"""),
    code("""# 练习 2 参考答案
def anchor_coverage(anchor_sizes, obj_sizes, thr=0.5):
    best = [max(min(s, a) ** 2 / max(s, a) ** 2 for a in anchor_sizes) for s in obj_sizes]
    imp = [b < thr for b in best]
    return {
        'best_iou': best,
        'impossible': imp,
        'impossible_frac': sum(imp) / len(imp),
        # 要让最小的目标也达到 thr: (s_min/A)^2 >= thr  =>  A <= s_min/sqrt(thr)
        'min_anchor_needed': min(obj_sizes) / math.sqrt(thr),
    }"""),
    code("""# 练习 3 参考答案
def ap_ceiling(s, jitter=2.0, tau=0.5, n=50000):
    v = annotation_iou_samples(s, jitter=jitter, n=n)
    return float(np.mean(v >= tau))"""),
    code("""# 练习 4 参考答案
def min_size_and_range(width_px, hfov_deg, size_m, finest_stride,
                       stroke_ratio=1/8, nyquist_px=2.0, cells_needed=2.0):
    f = (width_px / 2.0) / math.tan(math.radians(hfov_deg / 2.0))
    min_px_nyquist = nyquist_px / stroke_ratio          # 笔画 = D*ratio >= nyquist
    min_px_stride = cells_needed * finest_stride        # 至少 cells_needed 个格子
    min_px = max(min_px_nyquist, min_px_stride)
    return {
        'min_px_nyquist': min_px_nyquist,
        'min_px_stride': min_px_stride,
        'min_px': min_px,
        'bottleneck': 'physics' if min_px_nyquist >= min_px_stride else 'architecture',
        'max_range_m': f * size_m / min_px,
    }"""),
    md("""---
## 🧪 真实工程胶囊：小目标专项的「五笔账」诊断脚本

可原样复制到项目里。**任何「小目标不行」的工单，先把这五笔账跑一遍再讨论方案。**"""),
    code("""RECIPE = r'''
# ── 小目标五因诊断（开工前必跑）─────────────────────────────────────────
import math, numpy as np

CFG = dict(
    # A 物理层
    width_px=1920, hfov_deg=60.0, target_m=0.60, required_range_m=60.0,
    # B 度量 / 分配层
    finest_stride=8, min_anchor=32, assign_thr=0.5,
    # C 数据层（**必须实测，不要拍脑袋**：抽 200 个小目标让第二人盲标）
    anno_jitter_px=2.0,
)

f = (CFG["width_px"]/2) / math.tan(math.radians(CFG["hfov_deg"]/2))
s = f * CFG["target_m"] / CFG["required_range_m"]           # 该距离上的像素边长

# ① 信息量：奈奎斯特下界（笔画宽约为直径 1/8，环厚约 1/10）
min_px_cls, min_px_det = 2/(1/8), 2/(1/10)                  # 16 px / 20 px
r1 = "PASS" if s >= min_px_cls else "FAIL(像素预算不够，改模型没用 -> 换相机/提分辨率/ROI)"

# ② 度量：该尺寸在 assign_thr 下的绝对位移容忍度
d_tol = s * (1 - math.sqrt(2*CFG["assign_thr"]/(1+CFG["assign_thr"])))
r2 = "PASS" if d_tol >= 3.0 else "FAIL(容忍度低于回归噪声 -> 尺度自适应阈值 / NWD)"

# ③ 分配：**最重要的一行除法**
best_iou = 1.0 if s >= CFG["min_anchor"] else (s/CFG["min_anchor"])**2
r3 = "PASS" if best_iou >= CFG["assign_thr"] else "FAIL(一个正样本都拿不到 -> 先修这个，几乎免费)"
min_anchor_needed = s / math.sqrt(CFG["assign_thr"])

# ④ 架构：特征格子数（经验线 >= 2x2）
cells = s / CFG["finest_stride"]
r4 = "PASS" if cells >= 2.0 else "FAIL(格子不够 -> 加 P2(代价x4) 或 ROI 精检)"

# ⑤ 数据：标注相对误差与指标上限
rel_err = CFG["anno_jitter_px"] / s
r5 = "PASS" if rel_err <= 0.15 else "FAIL(标签带噪 -> 小目标只报 AP@0.5+召回，别报 AP@0.75)"

for tag, val, verdict in [
    ("① 信息量  像素边长",      f"{s:.1f}px (下界 {min_px_cls:.0f})", r1),
    ("② 度量    位移容忍度",    f"{d_tol:.2f}px",                     r2),
    ("③ 分配    最好可能 IoU",  f"{best_iou:.4f} (需 {CFG['assign_thr']})", r3),
    ("④ 架构    特征格子数",    f"{cells:.2f}x{cells:.2f}",           r4),
    ("⑤ 数据    标注相对误差",  f"{rel_err:.1%}",                     r5),
]:
    print(f"{tag:<22}{val:<22}{verdict}")
print(f"\n若 ③ FAIL: 最小 anchor 必须 <= {min_anchor_needed:.1f} px（当前 {CFG['min_anchor']}）")

# ── 动手顺序（严格按此，别跳步）────────────────────────────────────────
# 1) ③ 分配   —— 几乎零算力代价，折损常常直接是 0，**性价比最高，先修**
# 2) ⑤ 数据   —— 决定指标上限；不查清楚，后面所有实验都读不懂
# 3) ② 度量   —— 与 ③ 一起改最省事（尺度自适应阈值 / NWD）
# 4) ④ 架构   —— 加 P2 代价约 4x，但可预期
# 5) ① 物理   —— 最贵（换相机/提分辨率），且常受产品约束，放最后
#
# 反模式：先换更大 backbone -> 再提分辨率 -> 再加 P2。三个动作都在修 ①④，
#         而真正为零的 ③ 一直没人查。**先算 (s/A_min)^2，能省下的时间以人月计。**
'''
print(RECIPE)
for kw in ['min_anchor_needed', 'd_tol', 'best_iou', 'rel_err', '动手顺序', '反模式']:
    assert kw in RECIPE, kw
print()
print('✅ 胶囊覆盖：五笔账的可执行版本 + 动手顺序 + 最常见的反模式')"""),
    md("""### 小结

- **IoU 是尺度不变的尺子，但检测系统的误差是尺度不变不了的。**
  `IoU(s,d) = (s-d)²/(2s²-(s-d)²)`，斜率 `dIoU/dd|₀ = -4/s`。
  同样偏 2px：**8×8 框 0.3913，64×64 框 0.8841**。把位移写成相对量 `d=αs` 时 IoU 与 `s` 无关 ——
  **不公平来自「用相对尺子量绝对误差」，不来自 IoU 公式本身。**
- **临界位移 `d* = s(1-√(2τ/(1+τ)))`，τ=0.5 时 ≈ 0.1835·s。**
  同一条 IoU≥0.5，对 8px 目标要求 1.47px、对 64px 要求 11.74px。
  AP@0.75 对 8px 目标只允许 **0.59px** —— 亚像素，比标注精度还高。
  **AP_S 里有一块是「指标定义造成的」，必须与「模型的账」分开记。**
- **正样本稀缺不是「少」，是「零」。** `IoU_max(s,A) = (s/A)²` 是上界；
  RetinaNet 最小 anchor 32px 下，**8px 目标上界只有 0.0625，22.63px 是死线**，
  蒙特卡洛匹配率精确地是 **0.000**。修法优先级最高且几乎免费。
- **stride 32 上 8px 目标只占 0.25 个格子（面积 0.0625 格）**，输入像素预算差 64 倍；
  加 P2 让 neck+head 空间代价 **×4.0**，且收益只落在最小的桶。
- **有效感受野 σ = √(2n/3)，理论感受野按 O(n)、有效感受野按 O(√n)。**
  σ=30px 时 8px 目标只占该神经元有效输入的 **1.1%**、64px 占 **51.0%**（差 45 倍）。
  所以**「小目标需要更大感受野」是反的** —— 需要的是**匹配**的感受野。
- **±2px 标注抖动对 8px 框是 25% 相对误差**：平均一致性 IoU 只有 **0.62**，
  **AP@0.75 的天花板只有 8.3%**。这一条与前四条**完全正交**，模型侧怎么改都无效。
- **五个原因是乘性的**：`AP_S/AP_L ≈ Πrᵢ`。所以单点改进收益总低于预期，
  且修好一项后瓶颈会立刻换到下一项（练习 4 里「加 P2 后一米都没多看到」就是活例）。
  **诊断顺序：③分配 → ⑤数据 → ②度量 → ④架构 → ①物理。**

下一站：**模块 02 · 架构层面的解法** —— 把原因 ④ 这笔账花在刀刃上。"""),
]
