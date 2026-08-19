# -*- coding: utf-8 -*-
"""C55 模块 04 · 时序与多帧融合：从单帧检测到稳定输出。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03；C54 模块 01（匈牙利匹配）会被直接复用；C53 模块 05（延迟预算）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_temporal_fusion.ipynb'),
    ("核心参考", "SORT / DeepSORT / ByteTrack / OC-SORT；BEVFormer 与 StreamPETR 的时序传播；卡尔曼滤波与贝叶斯滤波基础"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ── 1 ────────────────────────────────────────────────────────────
    ("approach", "TSR 是一个「接近过程」，不是一次快照", "".join([
        P("绝大多数检测教程默认的场景是「给一张图，输出框」。<strong>TSR 不是这样的任务</strong>。一块限速牌不会突然出现在你面前——它先在一百多米外变成几个像素的斑点，然后随着自车前进逐帧变大、变清晰，最后在车头掠过时离开视野。<em>同一个物理目标，你会看到它 80–120 次。</em>"),
        P("把这件事量化一遍，你会发现「单帧检测」这个提法在 TSR 里有多浪费。用针孔相机模型，一块边长 <code>S</code> 米的标志在距离 <code>Z</code> 米处的像素边长是："),
        MATH("w_{px} \\;=\\; \\frac{f_{px}\\cdot S}{Z}, \\qquad f_{px} \\approx \\frac{W/2}{\\tan(\\mathrm{HFOV}/2)}"),
        P("取一组量产常见的参数：1920×1080、水平 FOV 65°（<code>f≈1500 px</code>）、限速牌边长 0.6 m、车速 100 km/h、30 FPS。于是每帧自车前进 <code>27.8/30 = 0.926 m</code>，而标志的像素尺寸是："),
        TABLE(["距离 Z", "像素边长", "单帧检出概率（典型）", "从这里到 20 m 还剩多少帧"], [
            ["120 m", "<strong>7.5 px</strong>", "≈ 0.18（几乎靠猜）", "108 帧"],
            ["80 m", "11.3 px", "≈ 0.42", "65 帧"],
            ["60 m", "15.0 px", "≈ 0.73", "43 帧"],
            ["40 m", "22.5 px", "≈ 0.95", "22 帧"],
            ["20 m", "45.0 px", "≈ 0.99", "0 帧"],
        ]),
        DUAL(
            "换个角度看这张表：<strong>在标志离开视野之前，系统已经拿到了近百次独立（或准独立）的观测机会</strong>。如果你只用最后一帧、或者每帧独立判断然后直接上报，等于把其中 99 次证据扔掉了。<em>更糟的是，你还把每一次观测的噪声都原样传给了下游</em>——某一帧因为一片树叶挡了半个牌子而漏检，下游就会看到限速值凭空消失一帧。",
            "严格地说，多帧融合把问题从「单样本分类」变成了<span class=\"term\">序贯假设检验</span>（sequential hypothesis testing）：给定一串观测 <code>z_1..z_t</code>，判断假设 <code>H</code>（此处存在类别为 c 的标志）是否成立。序贯检验的经典结论是，<em>在同样的错误率约束下，它需要的样本量显著少于固定样本量检验</em>；反过来说，在同样的样本量下它的错误率显著更低。<strong>这就是多帧融合的理论依据，而不是「多看几眼比较保险」这种朴素直觉。</strong>",
        ),
        P("但「多看几眼」不是免费的，因为 TSR 的输出有<strong>时间窗口</strong>。假设从 100 km/h 降到 60 km/h，用舒适减速度 1.5 m/s²，需要 7.4 秒、走过约 165 米。<em>也就是说，理想情况下限速牌应该在一百多米外就被确认</em>——而那时它只有 7–8 个像素。这构成了本模块要反复回到的张力：<strong>越晚上报越稳，越早上报越有用</strong>。"),
        CALLOUT("intuition", "本模块的一句话心法：<strong>单帧检测器输出的是「证据」，不是「结论」。时序模块的职责是把证据累积成结论，并决定何时公布这个结论。</strong> <em>把这两件事分开，是 TSR 系统设计里最重要的一次切分</em>——它让你可以独立地调「检测器多敏感」和「系统多敢报」，而不必每次都重训模型。面试里如果你能主动说出这句话，基本就绕开了「你只会调 mAP」的判断。"),
    ])),

    # ── 2 ────────────────────────────────────────────────────────────
    ("tracking", "跟踪：把帧间的检测串成同一个物体", "".join([
        P("要累积证据，先得知道<strong>哪些帧的哪个框说的是同一块牌子</strong>。这就是<span class=\"term\">multi-object tracking</span>（多目标跟踪）里的<span class=\"term\">data association</span>（数据关联）问题。TSR 用得上的关联信号有三层，代价与收益递增："),
        TABLE(["关联信号", "怎么算", "代价", "在 TSR 里的表现"], [
            ["<strong>IoU / 框重叠</strong>", "上一帧框（或其预测）与本帧框的 IoU", "≈ 0", "近处极好；<strong>远处小框极差</strong>（见下）"],
            ["<strong>中心距离 / 归一化距离</strong>", "中心点欧氏距离除以框尺寸，或马氏距离", "≈ 0", "对小目标比 IoU 稳健得多，推荐做主信号"],
            ["<strong>外观特征</strong>", "从 crop 提 embedding，算余弦相似度", "一次额外前向（DeepSORT 路线）", "TSR 里性价比低——<em>同类标志长得一模一样，外观根本不可分</em>"],
        ]),
        P("第三行值得展开：<strong>DeepSORT 那套「外观 re-ID」在 TSR 上基本失效</strong>，因为同一条路上的三块限速 60 牌在外观空间里是同一个点。行人跟踪里外观是最强的区分信号，在 TSR 里它几乎没有信息量。<em>反过来说，TSR 的救星是运动模型——这正是下一节的内容。</em>"),
        H3("IoU 关联在小目标上的失效，要用数字说"),
        P("一个 <code>8×8</code> 的框，如果帧间中心位移 2 px（且尺寸不变），重叠区域是 <code>6×6=36</code>，并集是 <code>2×64−36=92</code>，<strong>IoU = 36/92 ≈ 0.39</strong>。位移 3 px 时 IoU = 25/103 ≈ 0.24——已经跌破常用的 0.3 关联阈值。而同样 2 px 的位移放到 <code>64×64</code> 的框上，IoU = (62×64)/(2×4096−3968) = 3968/4224 ≈ <strong>0.94</strong>。"),
        DUAL(
            "所以「IoU 阈值 0.3」这条在行人跟踪里工作良好的默认设置，<strong>搬到 TSR 的远距离场景就会直接把轨迹打断</strong>：明明是同一块牌子，因为框小、抖动 2–3 像素，关联失败，于是新建一条轨迹，之前累积的证据全部作废，确认时间被反复重置。<em>症状是「远处的牌子怎么也确认不了」，而根因在关联层不在检测层</em>——这类误诊在实际项目里非常常见。",
            "正确的做法有两条，通常一起用：① <strong>把 IoU 换成尺度归一化的中心距离</strong>，例如 <code>d = ‖c_t − ĉ_t‖ / max(w, h)</code>，它对框尺寸不敏感；② <strong>把阈值做成尺度的函数</strong>，小框放宽、大框收紧。更彻底的做法是用<span class=\"term\">Mahalanobis distance</span>（马氏距离）——把预测位置的不确定度（卡尔曼滤波的协方差）显式建模进来，<em>远处目标的位置协方差本来就大，马氏距离会自动放宽门限</em>。这是 SORT/DeepSORT 用马氏门控而不是纯 IoU 门控的原因。",
        ),
        H3("贪心 vs 匈牙利：一个两行的反例"),
        P("拿到代价矩阵之后，怎么配对？<strong>贪心</strong>（每次取当前最相似的一对，配上就锁定）实现最简单，但它是局部最优。看这个 2×2 的 IoU 矩阵："),
        ASCII("""            det D0      det D1
track T0     0.60        0.55
track T1     0.58        0.10

贪心：先挑全局最大 0.60 → (T0,D0) 锁定
      剩下只能 (T1,D1) = 0.10          总相似度 = 0.70

匈牙利：全局最优 (T0,D1)=0.55 + (T1,D0)=0.58   总相似度 = 1.13

差别的来源：T1 只有 D0 能用（对 D1 几乎没有重叠），
            而 T0 对两个都行 —— 贪心先把 T0 的位置占了。"""),
        P("这个结构在 TSR 里天天发生：<strong>门架上并排两块牌子</strong>（限速 + 解除、或限速 + 货车专用），框互相靠近；其中一块被短暂遮挡，剩下的检测同时对两条轨迹都有中等 IoU。<em>贪心会把它配给「更像」的那条，而那条其实有更好的备选</em>——结果是一条轨迹丢帧、另一条 ID 跳变。"),
        P("匈牙利算法（Kuhn–Munkres）在 <code>O(n³)</code> 时间里求出总代价最小的一对一配对，机理与代价矩阵设计在 <strong>C54 模块 01</strong> 里已经完整讲过——<em>那门课里为 DETR 的集合预测写的匈牙利实现，可以原样搬到这里做跟踪关联</em>。这不是巧合：<strong>「一对一分配」是同一个数学问题，只是一边发生在训练时（预测 ↔ GT），一边发生在推理时（轨迹 ↔ 检测）</strong>。"),
        CALLOUT("warn", "匈牙利算法本身<strong>不认识阈值</strong>——它会把每一行都配掉，哪怕最优的那个配对 IoU 只有 0.01。<em>所以必须先做门控（gating）：把不合格的配对代价设成一个大常数（或 <code>inf</code>），匹配完成后再逐对检查、把超过门限的配对拆掉</em>。漏掉这一步的典型症状是「一辆车驶过后，标志的轨迹莫名其妙跳到了车尾灯上」。"),
        H3("ByteTrack 的两阶段思路：为什么它特别适合 TSR"),
        P("<span class=\"term\">ByteTrack</span> 的做法一句话说清：<strong>先用高分检测（&gt; 0.6）做第一轮关联；剩下的低分检测（0.1–0.6）不用来新建轨迹，只用来「续」已有的轨迹</strong>。"),
        DUAL(
            "为什么这个小改动收益巨大？因为<strong>低分框有两种截然不同的来源</strong>：一种是真背景的随机响应（该丢），一种是被遮挡/太远的真目标（该留）。传统做法用一个阈值一刀切，把两种都丢了。ByteTrack 用「有没有一条已经存在的轨迹在预测位置上等着它」来区分这两种——<em>有轨迹接应的低分框，大概率是真目标</em>。",
            "把它翻译成 TSR 的语言：<strong>一块标志从 120 m 接近到 20 m，它的检测分数是单调上升的</strong>。在最有价值的远距离段，分数恰好都在 0.2–0.5 这个「低分区」。如果按 0.5 一刀切，你在 60 m 之外基本什么都拿不到；而用 ByteTrack 的两阶段策略，只要在 40 m 处高分建轨成功，就可以<em>反向</em>用低分框把轨迹维持住——更进一步，配合下一节的运动模型，甚至可以在轨迹建立后<strong>回溯</strong>确认更远处的低分观测。<strong>「用轨迹的存在性给低分证据加权」，是本节最可迁移的一条。</strong>",
        ),
    ])),

    # ── 3 ────────────────────────────────────────────────────────────
    ("motion", "运动补偿：TSR 相对行人跟踪的巨大优势", "".join([
        P("现在讲本模块最该记住的一条领域知识。<strong>交通标志是静止的刚体，自车的运动是自己测出来的。</strong> 这两句合起来意味着：<em>标志在下一帧图像上的位置和大小，可以被解析地预测出来，误差只来自里程计噪声和相机标定误差。</em>"),
        P("推导很短。取相机坐标系（光心为原点、Z 轴指向前方），标志中心在 <code>(X, Y, Z)</code>，像素坐标是 <code>u = c_x + f X/Z</code>、<code>v = c_y + f Y/Z</code>，像素宽度 <code>w = fS/Z</code>。自车沿光轴前进 <code>d</code> 米后，<code>X, Y</code> 不变而 <code>Z → Z−d</code>，于是："),
        MATH("s=\\frac{Z}{Z-d};\\qquad u'=c_x+(u-c_x)\\,s,\\quad v'=c_y+(v-c_y)\\,s,\\quad w'=w\\,s"),
        P("也就是说，<strong>整幅画面里所有静止物体都以「光心为中心」按同一个尺度因子 s 向外放射性膨胀</strong>——这就是所谓的 <span class=\"term\">focus of expansion</span>（扩张中心）。数字感受一下："),
        TABLE(["距离 Z", "每帧尺度因子 s（d = 0.926 m）", "20 px 的框中心位移", "不补偿时的帧间 IoU"], [
            ["100 m", "1.0093", "≈ 2.2 px（若中心离光心 240 px）", "0.80 左右"],
            ["50 m", "1.0189", "≈ 4.5 px", "0.63 左右"],
            ["30 m", "1.0318", "≈ 7.6 px", "0.44 左右"],
            ["20 m", "1.0485", "≈ 11.6 px", "<strong>0.28 左右（已跌破门限）</strong>"],
        ]),
        DUAL(
            "不做运动补偿的后果，在<strong>近距离</strong>反而最严重——这一点和直觉相反。很多人以为「近了框大了，关联肯定更容易」，但 <code>s = Z/(Z−d)</code> 随 Z 减小而快速增大，<em>近距离时框在图像上跑得飞快</em>。于是出现一个经典 badcase：一块牌子在中远距离跟得好好的，快到车头时轨迹突然断掉、ID 跳变、状态回到 tentative——刚好发生在最需要它稳定的时刻。",
            "补偿之后，<strong>预测残差从「几十像素」降到「里程计误差 + 标定误差」的量级</strong>。轮速里程计在 1/30 秒内的误差是毫米级，投影到像素上远小于 1 px；主要残差来自俯仰变化（过减速带、刹车点头）和横向运动（变道、弯道），这两项可以用 IMU 的角速度做一阶补偿。<em>实践中做完补偿，关联门限可以收得很紧（IoU &gt; 0.5 或残差 &lt; 3 px），既不丢真目标又几乎不会错配</em>——而在行人跟踪里你永远不敢把门限收这么紧。",
        ),
        CALLOUT("intuition", "把对比讲透：<strong>行人跟踪难，是因为被跟踪对象是一个有自主意志的 agent——他可以随时停、转、被遮挡后从另一侧出现，运动模型只能给出很宽的先验。TSR 里被跟踪对象是钉在地上的一块铁皮，它的图像运动完全由自车运动决定，而自车运动是你自己的传感器直接测量的。</strong> <em>这是 TSR 工程上最大的一块「免费午餐」，而绝大多数只做过通用检测的候选人不会主动提到它。面试里主动讲这一点，等于告诉面试官你真的想过这个领域的特殊结构。</em>"),
        H3("反过来用：运动一致性是一个免费的误检过滤器"),
        P("既然静止物体的图像膨胀率被 <code>s = Z/(Z−d)</code> 严格约束，那么<strong>凡是膨胀率对不上的，就不是静止物体</strong>。这直接干掉 TSR 里最烦人的一类误检："),
        UL([
            "<strong>前车车身上的贴纸 / 尾门上的限速标识 / 货车尾部的广告</strong>——前车与自车速度接近，相对接近速度只有 2–3 m/s，实际膨胀率远小于「静止假设」的预测。累积十几帧后，观测尺度与预测尺度的对数差会拉开到 0.5 以上，<em>而真标志的这个量是 0.0X 量级</em>，两类完全分开。",
            "<strong>对向车道上的移动广告车 / 公交车身广告</strong>——相对接近速度反而更快，膨胀率高于预测，同样对不上。",
            "<strong>路侧固定广告牌</strong>——它是静止的，运动一致性检验<em>拦不住它</em>。这类只能靠外观与上下文（形状/颜色/位置先验）解决。<strong>诚实地说清楚一个方法的边界，比夸大它的作用重要得多。</strong>",
        ]),
        CALLOUT("warn", "运动补偿的三个隐藏前提，任何一条不成立都会让它变成负收益：<strong>①里程计可用且时间对齐</strong>（图像时间戳与轮速时间戳错开 30 ms，在 100 km/h 下就是 0.8 m 的位置误差）；<strong>②相机内参与俯仰角已标定</strong>（<code>c_x, c_y</code> 用错会让扩张中心偏移，补偿反而制造残差）；<strong>③自车运动近似为沿光轴平移</strong>——转弯、变道、上下坡时必须用完整的 <code>R, t</code> 而不是标量 <code>d</code>。<em>在弯道上用直线模型做补偿，是一个会让你在弯道场景专项掉点、却在整体指标上看不出来的经典坑。</em>"),
    ])),

    # ── 4 ────────────────────────────────────────────────────────────
    ("fusion", "证据累积：滑窗投票 vs 贝叶斯更新", "".join([
        P("轨迹建立起来之后，问题变成：<strong>这条轨迹上一串带分数的观测，该怎么合成一个「有 / 没有 / 是哪一类」的判断？</strong> 工业界的两条主流路线是滑窗投票与贝叶斯累积，它们的差别不是「哪个更准」，而是<em>响应延迟的形状完全不同</em>。"),
        H3("路线 A：滑窗投票（M-of-K）"),
        P("最近 K 帧里有至少 M 帧检出（且类别一致）就上报。实现只要一个环形缓冲区，几十行 C++ 就能写完，<strong>没有任何需要标定的连续量</strong>——这是它在量产系统里长盛不衰的真正原因：<em>可解释、可穷举测试、参数只有两个整数</em>。"),
        H3("路线 B：贝叶斯累积（log-odds 递推）"),
        P("把每帧观测当作独立证据，在对数几率（log-odds）域上做加法："),
        MATH("\\ell_t=\\ell_{t-1}+\\log\\frac{P(z_t\\mid H)}{P(z_t\\mid \\neg H)},\\qquad \\ell_0=\\log\\frac{P(H)}{P(\\neg H)}"),
        P("如果检测器的分数已经<strong>标定</strong>（模块 02 的 ECE/可靠性图讲过怎么验），那么单帧的证据量就是 <code>logit(s) = log(s/(1−s))</code>，未检出帧则加一个负的常数惩罚。上报条件是 <code>ℓ_t &gt; τ_on</code>。"),
        TABLE(["", "滑窗投票 M-of-K", "贝叶斯 log-odds 累积"], [
            ["用到分数大小吗", "<strong>不用</strong>（0.51 与 0.99 同权）", "<strong>用</strong>（证据量正比于 logit）"],
            ["确认延迟", "刚性：<strong>至少 M 帧</strong>，与证据强度无关", "自适应：一帧 0.99 就可能够，弱证据要攒很久"],
            ["对「持续中等分」的反应", "<em>会确认</em>（0.55 也算一票）", "<em>也会确认，但慢得多</em>，且可通过 τ 调节"],
            ["需要标定吗", "不需要", "<strong>需要</strong>——分数不准 = 证据量算错"],
            ["参数", "两个整数 M, K", "τ_on / τ_off / miss 惩罚 / clamp / 衰减"],
            ["可测试性", "<strong>可穷举</strong>（K 帧只有 2^K 种输入）", "连续状态，只能抽样测"],
            ["典型归属", "安全相关的最终判决层", "证据层 / 融合层"],
        ]),
        DUAL(
            "两者最有意思的差别在<strong>「弱但持续」的证据</strong>上。一块被树叶挡了一半的牌子，每帧分数稳定在 0.52。投票法（阈值 0.5）会认为它每帧都「检出」，3 帧后就确认——<em>它把 0.52 当成了 0.99</em>。贝叶斯法算出每帧证据只有 <code>log(0.52/0.48) = 0.08</code>，要攒到 τ_on = 3.0 需要 37 帧。<strong>哪个对？取决于分数标定得好不好</strong>：如果 0.52 真的意味着 52% 的后验概率，贝叶斯是对的；如果检测器在遮挡场景上系统性低估（分数被压低但其实很确定），贝叶斯就过于保守。",
            "反过来在<strong>「强但短暂」的证据</strong>上，结论相反。一块近距离的大牌子第一帧就给出 0.98，贝叶斯当帧证据是 <code>log(0.98/0.02) = 3.9</code>，<em>一帧就越过 τ_on</em>；而 3-of-5 投票<strong>无论如何都要等满 3 帧</strong>（100 km/h 下 = 2.8 m）。<em>在「牌子突然从遮挡后露出、而车已经很近了」这个场景里，那 3 帧的刚性延迟是真实的安全成本。</em> 这就是为什么成熟系统往往<strong>两者串联</strong>：贝叶斯层做连续的证据累积（快、信息利用充分），投票层做最终判决（可穷举验证、给安全评审看）。",
        ),
        CALLOUT("danger", "<p>贝叶斯累积有一个必须处理的实战故障，我称之为「<strong>证据卡死</strong>」：<code>ℓ</code> 是无界累加的，一块牌子跟了 80 帧、每帧 +3.5，<code>ℓ</code> 会累到 280。此后<strong>即使它已经被车头掠过、连续 30 帧完全检不到</strong>（每帧 −0.4），<code>ℓ</code> 仍有 268，远在 τ_off 之上——<em>系统会一直坚称前方有一块限速牌，直到轨迹因为 max_age 被强制删除</em>。如果轨迹还因为运动补偿被「维持」着，它甚至可以卡死几秒钟。</p><p><strong>解法是三件套，缺一不可</strong>：① <code>clamp</code> 把 <code>ℓ</code> 限制在 <code>[−L, +L]</code>（典型 L = 5–8，对应 99.3%–99.9% 的置信上限）；② 加<strong>时间衰减</strong> <code>ℓ ← λℓ</code>（λ≈0.98），让旧证据自然遗忘；③ 对<strong>观测相关性</strong>降权——相邻帧根本不独立（同一个 ISP、几乎相同的视角、相同的遮挡），把它们当独立证据会指数级地高估置信度。<em>一个粗糙但有效的近似：每 n 帧才计入一次证据，或把每帧的 logit 乘以 1/n。</em></p>", "证据卡死：无界累加是会出人命的 bug"),
        CALLOUT("warn", "第 ③ 点值得再强调一次，因为它是<strong>面试里区分「读过贝叶斯滤波」和「用过贝叶斯滤波」的分水岭</strong>。相邻帧的检测结果相关系数常常在 0.9 以上（同一片树叶挡着、同一个曝光设置）。若把 10 帧强相关观测当作 10 个独立样本，<em>有效样本量其实只有 1–2 个</em>，累积出来的置信度会虚高一到两个数量级。<strong>面试官想听的是：你知道「独立」这个前提在时序数据上默认不成立，并且知道至少一种补救办法。</strong>"),
    ])),

    # ── 5 ────────────────────────────────────────────────────────────
    ("hysteresis", "迟滞：用两个阈值消灭闪烁", "".join([
        P("假设融合层已经输出了一个连续的置信量（log-odds 或滑窗命中率），最后一步是把它变成一个<strong>二值的上报状态</strong>。用单阈值会立刻遇到 TSR 最刺眼的用户可见缺陷：<strong>闪烁</strong>。"),
        P("原因是纯统计的。设置信量在阈值附近波动，均值 0.50、标准差 0.10。单阈值 0.50 意味着每一帧都在做一次公平抛硬币，<em>相邻两帧状态不同的概率约 50%</em>——300 帧里会发生大约 150 次上报/撤销翻转。仪表盘上的限速数字会以每秒十几次的频率闪，而下游的限速控制逻辑会收到 150 次「有效/失效」事件。"),
        ASCII("""单阈值 τ = 0.50                       迟滞 τ_on = 0.70 / τ_off = 0.30

conf                                  conf
0.7 ┤     ╭╮   ╭╮                     0.7 ┤─────────────────────  τ_on
0.5 ┼─╮╭─╯╰─╮╭╯╰╮╭─   τ               0.5 ┤ ╮╭─╮╭─╮╭─╮╭─╮╭─╮
0.3 ┤ ╰╯    ╰╯  ╰╯                    0.3 ┤─────────────────────  τ_off
    └──────────────── t                   └──────────────── t

state                                 state
 ON ┤ ▁▄▁▄▁▄▁▄▁▄▁▄▁▄  ← 抖成一片        ON ┤ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁  ← 稳
OFF ┤                                  OFF ┤

翻转次数 ≈ 150 / 300 帧               翻转次数 ≈ 7 / 300 帧
用户体验：仪表盘限速数字在闪            用户体验：稳定显示

代价：撤销也变慢了 —— 一旦误报上去，
      要跌破 τ_off 才撤得掉。"""),
        P("<span class=\"term\">Hysteresis</span>（迟滞）的做法就一句话：<strong>上报用高阈值 τ_on，撤销用低阈值 τ_off，且 τ_on &gt; τ_off</strong>。系统进入 ON 状态后，要一直等到置信量跌破 τ_off 才回到 OFF。这样在 <code>[τ_off, τ_on]</code> 这个「死区」内，噪声再怎么抖也不会引起状态变化。"),
        DUAL(
            "取 τ_on = 0.70、τ_off = 0.30，噪声 σ = 0.10：从 OFF 翻到 ON 需要一次 +2σ 的偏离（概率 2.3%），反向同理。<strong>翻转率从每帧 50% 掉到每帧 2.3%，降了 20 倍</strong>，而且这个降幅是<em>指数级</em>随死区宽度增长的（死区宽 4σ 时约 0.003%）。这是一个几乎不花钱的巨大改善——代价只有一行代码和两个常数。",
            "但迟滞<strong>不是免费的</strong>，它的代价藏在反方向：<em>一旦误报上去了，撤销也要跨越同样宽的死区</em>。一个瞬时误报如果不幸冲到 τ_on 之上，它至少要维持到置信量掉回 τ_off 才消失——<strong>「误报持续时长」这个指标会因为迟滞而系统性变长</strong>。所以 τ_off 不能设得太低，否则你换来的是「不闪，但错得更久」。<em>这两个阈值的正确设法不是拍脑袋，而是把它们连到模块 05 的两个指标上：τ_on 决定 FP/km 与首报距离，τ_off 决定误报持续时长的 p95。</em>",
        ),
        CALLOUT("intuition", "<strong>面试高频追问：「既然有『连续 N 帧才上报』，为什么还需要阈值迟滞？」</strong> 标准答案是：<em>它们作用在两个正交的维度上</em>。「连续 N 帧」是<strong>时间维</strong>的迟滞——要求证据在时间上持续；「τ_on/τ_off」是<strong>幅度维</strong>的迟滞——要求证据在强度上明确。单靠时间维挡不住「持续了 20 帧的 0.51 分误检」，单靠幅度维挡不住「单帧冲到 0.99 的闪光误检」。<strong>成熟系统两个都用，而且还会加第三个维度：状态机的 max_age（撤销也要求持续）。</strong>"),
    ])),

    # ── 6 ────────────────────────────────────────────────────────────
    ("lifecycle", "生命周期状态机：把所有策略收进一张图", "".join([
        P("把前面几节的机制装配起来，就得到 TSR 时序模块的核心数据结构：<strong>每条轨迹一个状态机</strong>。这套状态划分继承自 SORT，但每个转移条件都被 TSR 的领域约束重新解释过。"),
        ASCII("""                    新检测（无轨迹接应）
                            │
                            ▼
                    ┌───────────────┐
                    │  TENTATIVE    │  已建轨，**不向下游上报**
                    │  hits < N_init│  作用：吸收单帧闪光误检
                    └───────┬───────┘
       连续 miss ≥ 2        │  hits ≥ N_init  且  ℓ ≥ τ_on
       ──────────────┐      ▼
                     │  ┌───────────────┐
                     │  │  CONFIRMED    │ ── 向下游上报 ──▶ 限速约束 / HMI / VLA
                     │  │  reported=T   │
                     │  └───┬───────▲───┘
                     │ miss │       │ 重新关联上（低分框也算，ByteTrack）
                     │      ▼       │       且 ℓ 仍 ≥ τ_off
                     │  ┌───────────────┐
                     │  │  LOST(coast)  │  用运动模型**外推**位置，
                     │  │  0<miss<max_age│  仍上报（短暂遮挡不该让输出消失）
                     │  └───────┬───────┘
                     │          │ miss ≥ max_age  或  ℓ < τ_off
                     ▼          ▼
                    ┌───────────────┐
                    │   DELETED     │  释放 ID
                    └───────────────┘

关键：TENTATIVE 阶段不上报 —— 这一条挡掉了绝大部分单帧误检，
      而它的代价就是首报距离往后退 N_init 帧（100 km/h 下每帧 0.93 m）。"""),
        P("每个参数都直接对应一个可测量的指标，这是设计这套状态机时最该建立的映射："),
        TABLE(["参数", "调大会怎样", "调小会怎样", "对应的评测指标（模块 05）"], [
            ["<strong>N_init</strong>（确认所需命中数）", "误报大幅下降，首报距离后退", "反应快，单帧误检漏出去", "FP / 100 km ↔ 首次检出距离"],
            ["<strong>max_age</strong>（丢失后保留帧数）", "扛得住长遮挡，但误报持续更久", "遮挡一断就丢，输出闪断", "遮挡场景 recall ↔ 误报持续时长 p95"],
            ["<strong>τ_on</strong>", "更保守，只报高置信", "更激进，远处也敢报", "precision ↔ 远距离 recall"],
            ["<strong>τ_off</strong>", "撤销快，但可能闪", "撤销慢，误报赖着不走", "闪烁次数 ↔ 误报持续时长"],
            ["<strong>关联门限</strong>", "不易错配，但易断轨", "轨迹连续，但可能串到别的目标", "ID switch 率 ↔ 轨迹连续性"],
        ]),
        DUAL(
            "<strong>LOST 状态（coasting，惯性滑行）在 TSR 里的价值被严重低估。</strong> 一块牌子被前方大货车挡住 4–8 帧是家常便饭。如果没有 coasting，输出会消失再出现，下游看到的是「限速 60 → 无 → 限速 60」，很多下游逻辑会在「无」的那一刻回落到默认限速，然后再跳回来。<em>有了 coasting，加上上一节的运动模型能<strong>准确</strong>外推位置（因为标志静止），遮挡结束后重关联的成功率非常高</em>——这又是一次运动模型带来的红利。",
            "但 coasting 的危险对称地存在：<strong>它同样会让误报活得更久</strong>。一个被确认的误报进入 LOST 后，还会被继续上报 max_age 帧。所以工程上的处理是<em>非对称的</em>：对已确认的<strong>真实类别</strong>用较大的 max_age（扛遮挡），对<strong>低置信或运动一致性存疑</strong>的轨迹用较小的 max_age（快速丢弃）。<strong>「参数按轨迹质量分档，而不是全局一刀切」是这一层最实用的工程手艺。</strong>",
        ),
        CALLOUT("warn", "一个容易写错的实现细节：<strong>coasting 期间轨迹的位置必须继续用运动模型推进，而不是冻结在最后一次观测的位置上</strong>。冻结会导致遮挡结束时预测位置已经落后真实位置十几个像素（近距离尤其严重），重关联直接失败——<em>于是你既付出了 coasting 的误报代价，又没拿到它的抗遮挡收益</em>。这个 bug 在代码 review 里很难看出来，但在「近距离被遮挡」的专项集上会暴露成一个显著的召回坑。"),
    ])),

    # ── 7 ────────────────────────────────────────────────────────────
    ("map_prior", "与地图和定位的先验融合", "".join([
        P("如果车上有高精地图（或者哪怕只是一份众包的标志图层），它天然就是贝叶斯框架里的<strong>先验</strong> <code>ℓ_0</code>。这在数学上零成本地接进上一节的递推里："),
        MATH("\\ell_0=\\log\\frac{P(H\\mid \\text{map})}{P(\\neg H\\mid \\text{map})}=\\underbrace{\\log\\frac{P(H)}{P(\\neg H)}}_{\\text{无图先验}}+\\underbrace{\\log\\frac{P(\\text{map}\\mid H)}{P(\\text{map}\\mid \\neg H)}}_{\\text{地图证据}}"),
        P("直观后果：<strong>地图说这里有一块限速 60 牌，那么感知只需要更少的观测证据就能确认它</strong>（首报距离可以推远十几米）；反过来，地图说这里没有牌子，那么一个孤立的中等置信检测需要更强的证据才能翻盘。"),
        TABLE(["场景", "地图先验", "感知证据", "系统应有的行为"], [
            ["地图有 + 感知强", "+2.0", "+4.0", "<strong>快速确认</strong>，首报距离最远"],
            ["地图有 + 感知弱", "+2.0", "+0.5", "谨慎确认；<em>这是先验最有价值的一档</em>"],
            ["地图无 + 感知强", "−1.0", "+5.0", "<strong>确认</strong>——感知必须能推翻地图（临时牌/改牌）"],
            ["地图无 + 感知弱", "−1.0", "+0.5", "不报；<em>典型的广告牌误检会落在这一档</em>"],
            ["地图有 + 感知持续无", "+2.0", "−3.0（连续未检出）", "不报，并<strong>触发数据回传</strong>（地图可能过期）"],
        ]),
        DUAL(
            "最后一行才是这一节真正的重点：<strong>地图与感知的分歧本身就是最有价值的数据挖掘触发器</strong>。地图说有、感知连续几十帧说没有，两种可能：地图过期（牌子被拆了/改了）或者感知有系统性漏检（这个位置逆光/被树遮）。<em>无论哪种，这个路段都值得回传</em>——这条正是 C58「主动学习与线上触发」里最高效的规则触发之一，而且它的触发率天然很低（不会撑爆回传带宽）。",
            "而危险在于<strong>先验强度不能无上限</strong>。施工改道、临时限速、可变电子牌，都是「地图错、感知对」的场景，而这些恰恰是安全上最要紧的。<em>如果 ℓ_0 给到 +5，感知需要极强的反向证据才能推翻它，系统就会在临时施工区坚持播报一个已经不存在的限速</em>。工程约束是：<strong>先验只能加速「确认」，不能否决「感知的强证据」</strong>——实现上给 ℓ_0 设一个远小于 clamp 上限的量（如 ±2），并保证单帧强证据（logit ≈ 4）就能翻盘。",
        ),
        CALLOUT("danger", "还有一层常被忽略的耦合：<strong>地图先验依赖定位，而定位误差会让先验作用在错误的位置上</strong>。横向定位偏 1.5 m、纵向偏 10 m 在城市峡谷里并不罕见。纵向偏 10 m 意味着「地图上前方 60 m 有牌」这条先验，实际对应的是 50 m 或 70 m 处——<em>如果匹配逻辑用的是硬距离窗口，先验会被加到错误的轨迹上，甚至加到一个误检上</em>。<strong>正确做法是把定位不确定度显式建模进匹配（用概率关联而非硬窗口），并在定位质量下降时自动削弱先验强度</strong>。「先验的强度必须随它所依赖的信息的质量而变」，是所有先验融合的通则。"),
    ])),

    # ── 8 ────────────────────────────────────────────────────────────
    ("tradeoff", "延迟与稳定性的根本矛盾：把它算成一笔账", "".join([
        P("现在把本模块的所有旋钮收敛到一个问题上：<strong>到底要攒多少帧才上报？</strong> 这是一个真正的取舍，不存在两全的设置。用 M-of-K 投票做载体最容易算清楚。"),
        P("设单帧检出概率 <code>p</code>（真标志）、单帧误检通过概率 <code>q</code>（背景）。误检那一侧是干净的二项尾和；延迟那一侧则要小心："),
        MATH("P(\\text{误检被确认})=\\sum_{i=M}^{K}\\binom{K}{i}q^i(1-q)^{K-i},\\qquad \\mathbb{E}[T_{\\text{confirm}}]\\;\\underset{\\text{仅当 }K\\gg M}{\\approx}\\;\\frac{M}{p}"),
        P("<strong>那个 <code>M/p</code> 是一个会骗人的近似</strong>。它算的是「累计 M 次成功」的期望等待（负二项分布），但 M-of-K 要求这 M 次落在一个<em>长度为 K 的滑窗内</em>——窗口越紧，真实延迟越长。<code>p=0.6</code> 时 3-of-3 的近似值是 5.0 帧，<strong>精确值是 9.07 帧，低估了 45%</strong>。正确做法是把滑窗内容当状态、建一个吸收马尔可夫链解线性方程组（notebook 里会实现，只有十几行）。下表全部用精确值："),
        TABLE(["策略", "期望确认延迟（帧，精确）", "折算距离", "误检被确认的概率", "相对 1-of-1 的 FP 降幅"], [
            ["1-of-1", "1.67", "1.5 m", "5.00×10⁻²", "1×"],
            ["2-of-3", "3.65", "3.4 m", "7.25×10⁻³", "<strong>7×</strong>"],
            ["3-of-5", "5.51", "<strong>5.1 m</strong>", "1.16×10⁻³", "<strong>43×</strong>"],
            ["4-of-7", "7.30", "6.8 m", "1.94×10⁻⁴", "258×"],
            ["5-of-9", "9.06", "8.4 m", "3.32×10⁻⁵", "1505×"],
            ["<em>3-of-3（对照）</em>", "<em>9.07</em>", "<em>8.4 m</em>", "<em>1.25×10⁻⁴</em>", "<em>400×</em>"],
        ]),
        CALLOUT("warn", "看最后一行：<strong>3-of-3（连续三帧）的延迟和 5-of-9 一样，但误检抑制能力却只有它的 1/4</strong>。原因是「连续」这个要求把容错余量全砍掉了——只要中间漏一帧就得从头再来，而真实检出率 0.6 意味着漏帧非常频繁。<em>「连续 N 帧」这种最直觉、最常被写进第一版代码的策略，在 p 不接近 1 的场景下是严格劣于 M-of-K 的</em>。如果用 <code>M/p</code> 近似去做参数搜索，优化器会因为低估了它的延迟而<strong>把你骗到这个劣解上</strong>。"),
        DUAL(
            "这张表里藏着 TSR 领域最重要的一个工程判断：<strong>延迟的代价用「米」衡量之后，其实非常便宜</strong>。从 1-of-1 换到 3-of-5，误检率降了 43 倍，而首报距离只后退了 5.1 米——相对于 60 米的检出距离，这是 <strong>8.5%</strong> 的损失。<em>换句话说：在 TSR 里，多帧融合的性价比高得离谱，理由是「同一目标可观测上百帧」这个领域特性。</em> 这与行人检测形成鲜明对比：一个突然从车间窜出的行人可能只有 5–10 帧的观测窗口，那里每一帧延迟都是真金白银。",
            "但要诚实标注这个结论的<strong>边界条件</strong>，否则它就变成了一句危险的口号。三种情况下延迟的代价会陡增：① <strong>可变电子限速牌切换</strong>——牌面内容在几十毫秒内变化，攒帧会让系统在切换后仍播报旧值；② <strong>临时施工牌</strong>——常常出现在弯道后、被前车遮挡，可观测帧数可能只有十几帧，M 攒不满就已经开过去了；③ <strong>近距离突然露出</strong>（前车变道后牌子才可见）——此时剩余可用距离本来就短。<em>成熟系统的做法是让 M 随「剩余可用观测帧数的估计」而变</em>：远处慢慢攒（帧多，攒得起），近处快速判（帧少，攒不起）。<strong>「把固定参数变成场景自适应的参数」是从「能跑」到「量产」的一个典型跨越。</strong>",
        ),
        P("要把这个取舍变成可优化的量，就得写出一个显式的目标函数。最简单可用的形式是加权和，其中权重来自下游的安全代价（模块 05 会讲怎么定这些代价）："),
        MATH("J(M,K)=w_d\\cdot \\underbrace{\\mathbb{E}[T_{\\text{confirm}}]\\,v\\,\\Delta t}_{\\text{首报距离损失(m)}}\\;+\\;w_{fp}\\cdot \\underbrace{P(\\text{FP确认})\\cdot \\rho_{bg}}_{\\text{单位里程误报数}}"),
        CALLOUT("intuition", "这个式子的实用价值不在于算出一个精确最优解（<code>w_d</code> 和 <code>w_fp</code> 本来就是拍出来的），而在于它<strong>强迫你把两个原本不可比的量放到同一个尺度上</strong>。团队里关于「要不要多攒两帧」的争论，十次有九次是因为一方在谈米、另一方在谈误报数，而没人写下这个式子。<em>写下它之后，争论就变成了「w_fp 该取多少」——这是一个可以拿数据和用户反馈来谈的问题。</em> <strong>面试里被问「你怎么定这些参数」，能给出「先写目标函数、再讨论权重来源」这个回答，比给出任何具体数字都强。</strong>"),
    ])),

    # ── 9 ────────────────────────────────────────────────────────────
    ("frontier", "研究前沿与开放问题", "".join([
        P("时序这一层长期是「工程比论文强」的领域——量产系统里跑的东西往往比学术 SOTA 简单也更可靠。但有几条线值得跟踪。"),
        UL([
            "<strong>跟踪范式的演进</strong>：SORT（卡尔曼 + 匈牙利）→ DeepSORT（加外观）→ <strong>ByteTrack</strong>（低分框二次关联，几乎零成本的大收益）→ OC-SORT（用观测而非估计做重关联，修正卡尔曼在长遮挡后的漂移）→ BoT-SORT（加相机运动补偿——<em>正是本模块第 3 节的思想被写进通用跟踪器</em>）。这条线的启示是：<strong>近几年最有效的改进都不是更强的模型，而是对「什么时候该相信哪种证据」的更细致处理。</strong>",
            "<strong>端到端的时序检测器</strong>：MOTR / TrackFormer 把 track query 跨帧传播，让关联变成模型内部的注意力；StreamPETR 用 object-centric 的时序传播把历史信息压进 query。<em>它们在公开榜单上很漂亮，但车端落地慢</em>——原因是显存与延迟随历史长度增长、失败模式难以定位、以及最要命的：<strong>没有一个可以给安全评审看的、可穷举的判决逻辑</strong>。这是「可解释性作为部署硬约束」的一个真实例子。",
            "<strong>BEV 时序融合</strong>：BEVFormer 的 temporal self-attention 把上一帧的 BEV 特征作为额外的 key/value；SOLOFusion 讨论了「长时序低分辨率 vs 短时序高分辨率」的取舍。<em>对 TSR 的启发是把标志从图像空间提升到 3D/BEV 空间后再做时序融合</em>——一旦标志有了稳定的 3D 位置，跨帧关联就退化成一个平凡问题，还能天然支持多相机之间的关联（广角发现、长焦确认）。",
            "<strong>时序一致性作为自监督信号</strong>：同一条轨迹上的类别跳变（60→80→60）几乎必然意味着至少一帧错了。<em>这可以零标注地生成难例</em>——直接连到 C58 的挖掘触发器，也是「automated data mining workflows」最容易落地的一条规则。开放问题是如何区分「模型错」与「牌面真的变了」（可变电子牌）。",
            "<strong>标定与不确定度</strong>：贝叶斯累积的正确性完全依赖单帧分数的标定质量，而检测器的分数出了名地过自信。<em>conformal prediction 与检测的结合</em>（给出有覆盖率保证的框集合与类别集合）是近两年的热点，但如何在时序累积中保持这种保证，仍是开放的。",
            "<strong>时序稳定性缺少公认指标</strong>：mAP 是逐帧算的，闪烁 50 次与稳定输出得分完全相同。学术界目前没有一个被广泛接受的「输出稳定性」指标，各家量产团队都在用自己的一套（首报距离 / 闪烁次数 / 误报持续时长）。<em>模块 05 会把这套指标完整实现一遍</em>。",
        ]),
        CALLOUT("paper", "必读：<em>Simple Online and Realtime Tracking</em>（SORT, Bewley et al. 2016——先把这 4 页读透，后面所有跟踪器都是它的变体）；<em>Simple Online and Realtime Tracking with a Deep Association Metric</em>（DeepSORT, Wojke et al. 2017，重点看马氏门控与外观度量的融合方式）；★<em>ByteTrack: Multi-Object Tracking by Associating Every Detection Box</em>（Zhang et al. ECCV 2022——本模块第 2 节的核心，对 TSR 远距离低分场景直接适用）；<em>Observation-Centric SORT</em>（Cao et al. CVPR 2023，长遮挡后的重关联）；<em>BoT-SORT</em>（Aharon et al. 2022，相机运动补偿）；<em>BEVFormer</em>（Li et al. ECCV 2022，时序自注意力）与 <em>StreamPETR</em>（Wang et al. ICCV 2023，object-centric 时序传播）。基础读物：Thrun 等 <em>Probabilistic Robotics</em> 第 2 章（贝叶斯滤波与 log-odds 的标准推导）。相邻课程：C54 模块 01（匈牙利匹配的完整实现）、C58 模块 03（一致性触发）、C55 模块 05（时序稳定性指标）。完整清单见 <code>references.md</code>。"),
    ])),
]

# ────────────────────────────────────────────────────────────────────
# notebook
# ────────────────────────────────────────────────────────────────────

NB = [
    md("""# 04 · 时序与多帧融合（IoU 跟踪 / 匈牙利关联 / 运动补偿 / 贝叶斯累积 / 迟滞状态机）

目标：把「单帧检测器」的输出变成**稳定、可被下游信任的时序输出**，
并亲手量化本模块的中心矛盾——**多攒几帧更稳，但上报更晚**。

本 notebook 你会亲手实现：

1. 用针孔模型合成一段物理上自洽的「**接近过程**」检测序列（120 m → 15 m）
2. **IoU 关联**与贪心匹配，并复现贪心在两目标场景下的失败
3. 从零实现 **匈牙利算法**（O(n³) 增广路径版），与暴力枚举对拍
4. **运动补偿**：用自车里程解析预测下一帧框位置，并把它反过来当**误检过滤器**
5. **滑窗投票 vs 贝叶斯 log-odds 累积**：量化两者响应延迟的形状差异 + 复现「证据卡死」
6. **带迟滞的生命周期状态机**（tentative→confirmed→lost），测量**闪烁率**
7. **延迟-稳定性权衡曲线**：M-of-K 扫参，把「米」和「误报数」放到同一个目标函数里

> 心智模型：**单帧检测器输出的是证据，不是结论。
> 时序层的职责是把证据累积成结论，并决定何时公布它。**"""),

    md("""## 1 · 合成一段「接近过程」

一切从物理开始：针孔模型 `w_px = f·S/Z`。参数取量产常见配置，
这样后面所有数字都是**可以拿去和真车对照**的量级。"""),
    code("""import numpy as np, math, itertools
from collections import Counter
rng = np.random.default_rng(7)

# ── 相机与车辆参数（1920x1080, HFOV≈65°, 100 km/h, 30 FPS）──
W_IMG, H_IMG = 1920, 1080
F_PX  = 1500.0            # 焦距（像素）≈ (1920/2)/tan(32.5°)
CX, CY = 960.0, 540.0
SIGN_M = 0.60             # 限速牌物理边长（米）
FPS    = 30.0
V_KMH  = 100.0
V_MS   = V_KMH / 3.6
D_FRAME = V_MS / FPS      # 每帧自车前进距离（米）

def px_size(Z):
    '''距离 Z 米处，标志的像素边长。'''
    return F_PX * SIGN_M / Z

print(f'每帧自车前进 {D_FRAME:.3f} m   (= {V_KMH} km/h / {FPS} FPS)')
print(f"\\n{'距离 Z':>8s} {'像素边长':>10s} {'到 20m 还剩':>12s}")
for Z in [120, 100, 80, 60, 40, 30, 20]:
    n_left = max(0, (Z - 20) / D_FRAME)
    print(f'{Z:>7d}m {px_size(Z):>9.1f}px {n_left:>10.0f} 帧')

assert abs(px_size(120) - 7.5) < 0.01, '120 m 处应约 7.5 px'
assert abs(px_size(20) - 45.0) < 0.01
assert (120 - 20) / D_FRAME > 100, '从 120m 到 20m 应有 100+ 帧观测机会'
print('\\n✅ 同一块牌子会被看到 100+ 次 —— 只用单帧等于扔掉 99% 的证据。')"""),
    code("""# ── 合成一条真实标志的接近轨迹 ──
def approach_track(Z0=120.0, Z1=15.0, X=3.2, Y=-1.8):
    '''标志固定在自车右前方 X 米、光轴上方 |Y| 米处（图像 v 轴向下为正，故 Y<0）。
       返回 [(Z, box_xyxy), ...]，每帧自车前进 D_FRAME。'''
    out, Z = [], float(Z0)
    while Z > Z1:
        w = px_size(Z)
        u = CX + F_PX * X / Z
        v = CY + F_PX * Y / Z
        out.append((Z, np.array([u - w/2, v - w/2, u + w/2, v + w/2])))
        Z -= D_FRAME
    return out

def p_detect(w_px, w50=12.0, k=3.0):
    '''单帧检出概率：像素边长的 logistic 函数（w50 处 50%）。'''
    return 1.0 / (1.0 + math.exp(-(w_px - w50) / k))

def score_mu(w_px):
    '''检出时的分数均值：随尺寸单调上升，上限 0.97。'''
    return 0.32 + 0.65 / (1.0 + math.exp(-(w_px - 14.0) / 4.0))

traj = approach_track()
print(f'轨迹共 {len(traj)} 帧，Z 从 {traj[0][0]:.1f} m 到 {traj[-1][0]:.1f} m')
print(f"\\n{'Z(m)':>7s} {'w(px)':>7s} {'p_det':>7s} {'score_mu':>9s}  框(x1,y1,x2,y2)")
for i in [0, 20, 43, 65, 86, len(traj)-1]:
    Z, b = traj[i]
    w = b[2] - b[0]
    print(f'{Z:>7.1f} {w:>7.1f} {p_detect(w):>7.2f} {score_mu(w):>9.2f}  '
          f'({b[0]:.0f},{b[1]:.0f},{b[2]:.0f},{b[3]:.0f})')

assert p_detect(px_size(120)) < 0.25, '120 m 处应几乎检不到'
assert p_detect(px_size(40)) > 0.90, '40 m 处应基本必检出'
assert all(0 <= b[0] and b[2] < W_IMG for _, b in traj), '框应始终在画面内'
print('\\n✅ 检出概率随距离单调上升 —— 这就是「接近过程」的本质。')"""),

    md("""## 2 · IoU 关联与贪心的失败

关联的第一步是代价矩阵。IoU 最省事，但**在小框上极其脆弱**——先把这件事量化。"""),
    code("""def iou(a, b):
    '''单对框 IoU，xyxy。'''
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    iw = max(0.0, x2 - x1); ih = max(0.0, y2 - y1)
    inter = iw * ih
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def iou_matrix(A, B):
    return np.array([[iou(a, b) for b in B] for a in A]) if len(A) and len(B) \\
           else np.zeros((len(A), len(B)))

# IoU 对位移的敏感性：同样 2 px 位移，8px 框 vs 64px 框
print(f"{'框边长':>8s} {'位移1px':>9s} {'位移2px':>9s} {'位移3px':>9s} {'位移4px':>9s}")
for s in [8, 16, 32, 64]:
    a = np.array([0., 0., s, s])
    row = [iou(a, np.array([d, 0., s+d, s])) for d in [1, 2, 3, 4]]
    print(f'{s:>7d}px ' + ' '.join(f'{r:>9.3f}' for r in row))

a8 = np.array([0., 0., 8., 8.])
assert abs(iou(a8, np.array([2., 0., 10., 8.])) - 6/10) < 1e-9   # 1D 位移: 6/(16-6)
a64 = np.array([0., 0., 64., 64.])
assert iou(a64, np.array([2., 0., 66., 64.])) > 0.93
print('\\n⚠️  8px 框位移 3px → IoU 0.45；再叠加尺寸抖动就会跌破常用的 0.3 关联门限。')
print('✅ TSR 的关联门限必须**随尺度变化**，或干脆换成尺度归一化的中心距离。')"""),
    code("""# ── 贪心匹配的反例（并排两块牌子 + 其中一块被短暂遮挡）──
def greedy_match(sim, thr=0.0):
    '''按相似度从大到小贪心配对。返回 [(i, j), ...]。'''
    S = sim.copy().astype(float)
    pairs = []
    while True:
        i, j = np.unravel_index(np.argmax(S), S.shape)
        if S[i, j] <= thr:
            break
        pairs.append((int(i), int(j)))
        S[i, :] = -1.0; S[:, j] = -1.0
    return sorted(pairs)

SIM = np.array([[0.60, 0.55],
                [0.58, 0.10]])
g = greedy_match(SIM)
g_total = sum(SIM[i, j] for i, j in g)
best, best_total = None, -1
for perm in itertools.permutations(range(2)):
    t = sum(SIM[i, perm[i]] for i in range(2))
    if t > best_total:
        best_total, best = t, [(i, perm[i]) for i in range(2)]

print('IoU 矩阵:\\n', SIM)
print(f'\\n贪心   配对 {g}     总相似度 {g_total:.2f}')
print(f'最优   配对 {best}     总相似度 {best_total:.2f}')
assert g == [(0, 0), (1, 1)] and abs(g_total - 0.70) < 1e-9
assert best == [(0, 1), (1, 0)] and abs(best_total - 1.13) < 1e-9
print('\\n⚠️  贪心先把 T0 配给了 D0，而 T1 其实**只有 D0 可用** —— 局部最优毁了全局。')
print('   TSR 场景：门架上并排的「限速 + 解除」两块牌，一块被短暂遮挡时就长这样。')"""),

    md("""## 3 · 匈牙利算法（从零实现）

C54 模块 01 为 DETR 的集合预测写过它；**这里原样复用**——
「一对一分配」在训练时是 预测↔GT，在推理时是 轨迹↔检测，是同一个数学问题。"""),
    code("""def hungarian(cost):
    '''最小化总代价的一对一分配（O(n^3) 增广路径 / JV 变体）。
       cost: (n, m) 数组，可非方阵。返回 (row_ind, col_ind)，长度 min(n, m)。'''
    C = np.asarray(cost, dtype=float)
    n, m = C.shape
    transposed = False
    if n > m:                       # 保证行数 <= 列数
        C = C.T; n, m = m, n; transposed = True
    INF = float('inf')
    u = np.zeros(n + 1); v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int)      # p[j] = 匹配到列 j 的行（1-based），0 = 空
    way = np.zeros(m + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0
        minv = np.full(m + 1, INF)
        used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]; delta = INF; j1 = -1
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = C[i0 - 1, j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur; way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]; j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta; v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:                       # 回溯增广路径
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
    res = sorted((p[j] - 1, j - 1) for j in range(1, m + 1) if p[j] > 0)
    if transposed:
        res = sorted((c, r) for r, c in res)
    return np.array([r for r, _ in res]), np.array([c for _, c in res])

# 与暴力枚举对拍
def brute_force(cost):
    C = np.asarray(cost, float); n, m = C.shape
    if n > m:
        r, c = brute_force(C.T); return c, r
    best, best_p = None, None
    for perm in itertools.permutations(range(m), n):
        t = sum(C[i, perm[i]] for i in range(n))
        if best is None or t < best:
            best, best_p = t, perm
    return np.arange(n), np.array(best_p)

for trial in range(200):
    n, m = rng.integers(1, 6), rng.integers(1, 6)
    C = rng.normal(size=(n, m)).round(3)
    r1, c1 = hungarian(C); r2, c2 = brute_force(C)
    t1 = C[r1, c1].sum(); t2 = C[r2, c2].sum()
    assert abs(t1 - t2) < 1e-9, (C, t1, t2)
    assert len(set(c1.tolist())) == len(c1) and len(set(r1.tolist())) == len(r1)
print('✅ 200 组随机矩阵（含非方阵）与暴力枚举对拍通过 —— 匈牙利实现正确。')

r, c = hungarian(-SIM)                     # 最大化相似度 = 最小化 -相似度
assert sorted(zip(r.tolist(), c.tolist())) == [(0, 1), (1, 0)]
print(f'在上一节的反例上：匈牙利给出 {list(zip(r.tolist(), c.tolist()))}'
      f'，总相似度 {SIM[r, c].sum():.2f}（贪心只有 0.70）')"""),
    code("""# ── 关联 = 门控 + 匈牙利 + 事后拆对 ──
BIG = 1e6

def associate(tracks_boxes, det_boxes, iou_thr=0.2):
    '''返回 (matches, unmatched_tracks, unmatched_dets)。
       **门控必须做两次**：进矩阵前设大代价，出结果后再逐对检查。'''
    nt, nd = len(tracks_boxes), len(det_boxes)
    if nt == 0 or nd == 0:
        return [], list(range(nt)), list(range(nd))
    S = iou_matrix(tracks_boxes, det_boxes)
    C = np.where(S >= iou_thr, 1.0 - S, BIG)     # ① 进矩阵前门控
    r, c = hungarian(C)
    matches, mt, md_ = [], set(range(nt)), set(range(nd))
    for i, j in zip(r.tolist(), c.tolist()):
        if S[i, j] >= iou_thr:                   # ② 出结果后再拆一次
            matches.append((i, j)); mt.discard(i); md_.discard(j)
    return matches, sorted(mt), sorted(md_)

T = [np.array([100., 100., 120., 120.]), np.array([300., 300., 320., 320.])]
D = [np.array([302., 301., 322., 321.]), np.array([800., 800., 820., 820.])]
mt_, ut_, ud_ = associate(T, D, iou_thr=0.2)
print('轨迹0(100,100) 轨迹1(300,300) | 检测0(302,301) 检测1(800,800)')
print('matches:', mt_, ' unmatched_tracks:', ut_, ' unmatched_dets:', ud_)
assert mt_ == [(1, 0)] and ut_ == [0] and ud_ == [1]
print('\\n⚠️  匈牙利**不认识阈值**，它会把每一行都配掉 —— 哪怕最优配对 IoU 只有 0.01。')
print('✅ 所以门控必须做两次。漏掉第②步的症状：「一辆车驶过后轨迹跳到了车尾灯上」。')"""),

    md("""## 4 · 运动补偿：TSR 相对行人跟踪的巨大优势

**标志静止 + 自车运动已知 ⇒ 下一帧位置可解析预测。**
所有静止物体都以光心为中心按 `s = Z/(Z−d)` 放射性膨胀。"""),
    code("""def predict_box(box, Z, d=D_FRAME):
    '''自车沿光轴前进 d 米后，静止标志的新框（针孔模型，精确解）。'''
    s = Z / (Z - d)
    u = (box[0] + box[2]) / 2; v = (box[1] + box[3]) / 2
    w = (box[2] - box[0]) * s;  h = (box[3] - box[1]) * s
    u2 = CX + (u - CX) * s;     v2 = CY + (v - CY) * s
    return np.array([u2 - w/2, v2 - h/2, u2 + w/2, v2 + h/2])

# ① 预测应当**精确**复现下一帧（这是「静止 + 已知自车运动」的直接后果）
max_err = 0.0
for i in range(len(traj) - 1):
    Z, b = traj[i]
    max_err = max(max_err, float(np.abs(predict_box(b, Z) - traj[i+1][1]).max()))
print(f'运动补偿预测 vs 真实下一帧，最大像素误差 = {max_err:.2e} px')
assert max_err < 1e-9, '静止目标 + 已知位移，预测应当是精确的'

# ② 补偿前后的帧间 IoU
print(f"\\n{'Z(m)':>7s} {'w(px)':>7s} {'不补偿 IoU':>11s} {'补偿后 IoU':>11s}")
raw_ious, cmp_ious = [], []
for i in range(len(traj) - 1):
    Z, b = traj[i]; b_next = traj[i+1][1]
    r_ = iou(b, b_next); c_ = iou(predict_box(b, Z), b_next)
    raw_ious.append(r_); cmp_ious.append(c_)
    if i in [0, 43, 65, 86, 100]:
        print(f'{Z:>7.1f} {b[2]-b[0]:>7.1f} {r_:>11.3f} {c_:>11.3f}')

assert min(cmp_ious) > 0.999, '补偿后帧间 IoU 应恒为 1'
assert raw_ious[-1] < 0.45, '近距离不补偿时 IoU 会跌破常用门限'
assert raw_ious[-1] < raw_ious[0], '距离越近，不补偿的 IoU 越差（与直觉相反！）'
print(f'\\n⚠️  不补偿时**近距离反而最糟**（{raw_ious[-1]:.2f}）—— s=Z/(Z-d) 随 Z 减小而暴涨。')
print('   经典 badcase：牌子中远距离跟得好好的，快到车头时轨迹突然断掉。')
print('✅ 补偿后残差只剩里程计噪声 + 标定误差，关联门限可以收得很紧。')"""),
    code("""# ── 反过来用：运动一致性 = 免费的误检过滤器 ──
def motion_drift(w0, w_t, Z0, d_cum):
    '''观测尺度增长 与「静止假设」预测的对数差。静止目标 ≈ 0。'''
    Z_t = max(Z0 - d_cum, 1.0)
    return math.log(w_t / w0) - math.log(Z0 / Z_t)

def synth_object(Z0, n, rel_speed_ratio, w_noise=0.4, seed=0):
    '''rel_speed_ratio=1.0 → 静止标志；0.1 → 前车尾部广告（相对接近速度只有 1/10）。'''
    g = np.random.default_rng(seed)
    ws, drifts, Z = [], [], Z0
    d_cum = 0.0
    for t in range(n):
        w_true = px_size(Z)
        w_obs = w_true + g.normal(0, w_noise)      # 检测框宽度抖动
        ws.append(w_obs)
        d_cum = t * D_FRAME                        # 系统**假设**它是静止的
        if t > 0:
            drifts.append(motion_drift(ws[0], w_obs, Z0, d_cum))
        Z -= D_FRAME * rel_speed_ratio             # 真实的相对接近速度
    return ws, drifts

STATIC, BILLBOARD = 1.0, 0.10                      # 前车 90 km/h vs 自车 100 km/h
ws_s, dr_s = synth_object(40.0, 20, STATIC, seed=1)
ws_b, dr_b = synth_object(40.0, 20, BILLBOARD, seed=2)

print(f"{'帧':>4s} {'静止标志 w':>11s} {'漂移':>8s} | {'前车广告 w':>11s} {'漂移':>8s}")
for t in [4, 9, 14, 19]:
    print(f'{t:>4d} {ws_s[t]:>11.2f} {dr_s[t-1]:>8.3f} | {ws_b[t]:>11.2f} {dr_b[t-1]:>8.3f}')

print(f'\\n累积 19 帧后的 |漂移|:  静止标志 {abs(dr_s[-1]):.3f}   前车广告 {abs(dr_b[-1]):.3f}')
assert abs(dr_s[-1]) < 0.10, '真标志的运动漂移应接近 0'
assert abs(dr_b[-1]) > 0.40, '前车广告的漂移应显著'
assert abs(dr_b[-1]) > 4 * abs(dr_s[-1])
print('\\n✅ 一个 0.25 的漂移门限就能把「前车尾部广告 / 车身贴纸」这类误检干掉，代价为零。')
print('⚠️  但它拦不住**路侧固定广告牌** —— 那是静止的，运动一致性无能为力。')
print('   诚实说清方法的边界，比夸大它的作用重要得多。')"""),

    md("""## 5 · 滑窗投票 vs 贝叶斯累积

两者的差别不是「谁更准」，而是**响应延迟的形状**：
投票是刚性的（至少 M 帧），贝叶斯是自适应的（证据越强越快）。"""),
    code("""def logit(p, eps=1e-6):
    p = min(max(p, eps), 1 - eps)
    return math.log(p / (1 - p))

def sliding_vote(det_flags, K=5, M=3):
    '''最近 K 帧里 >= M 帧检出 → 上报。返回每帧的布尔判决。'''
    out, buf = [], []
    for f in det_flags:
        buf.append(bool(f))
        if len(buf) > K:
            buf.pop(0)
        out.append(sum(buf) >= M)
    return out

def bayes_accumulate(scores, det_flags, tau_on=3.0, tau_off=1.0,
                     miss_llr=-0.40, clamp=6.0, decay=1.0, corr_div=1.0):
    '''log-odds 累积 + 迟滞。corr_div: 观测相关性降权（相邻帧不独立）。
       返回 (每帧 logodds, 每帧上报判决)。'''
    l, ls, rep, on = 0.0, [], [], False
    for s, f in zip(scores, det_flags):
        l *= decay
        l += (logit(s) / corr_div) if f else miss_llr
        l = max(-clamp, min(clamp, l))          # ← clamp 是必须的，见下一个 cell
        on = (l >= tau_on) if not on else (l >= tau_off)
        ls.append(l); rep.append(on)
    return ls, rep

# 对照实验 A：**强但短暂**的证据（近距离大牌子，第一帧就 0.98）
sc_strong = [0.98] * 10
fl_strong = [True] * 10
v = sliding_vote(fl_strong, K=5, M=3)
_, b = bayes_accumulate(sc_strong, fl_strong)
d_vote  = v.index(True) + 1
d_bayes = b.index(True) + 1
print(f'【强证据 0.98】3-of-5 投票 {d_vote} 帧确认   贝叶斯 {d_bayes} 帧确认'
      f'   (差 {(d_vote-d_bayes)*D_FRAME:.1f} m)')
assert d_bayes == 1 and d_vote == 3

# 对照实验 B：**弱但持续**的证据（半遮挡，稳定 0.52）
sc_weak = [0.52] * 60
fl_weak = [True] * 60
v2 = sliding_vote(fl_weak, K=5, M=3)
l2, b2 = bayes_accumulate(sc_weak, fl_weak)
print(f'【弱证据 0.52】3-of-5 投票 {v2.index(True)+1} 帧确认   '
      f'贝叶斯 {b2.index(True)+1} 帧确认（每帧只值 logit={logit(0.52):.3f}）')
assert v2.index(True) + 1 == 3, '投票把 0.52 当成了 0.99'
assert b2.index(True) + 1 == 38, '贝叶斯需要 ceil(3.0/0.0800)=38 帧'
assert not any(b2[:30]), '前 30 帧贝叶斯坚决不确认'
print(f'\\n⚠️  投票**丢弃了分数大小**：0.52 和 0.99 在它眼里一样。')
print(f'✅ 贝叶斯保留了证据强度：logit(0.52)={logit(0.52):.3f} vs logit(0.98)={logit(0.98):.2f}')
print('   代价：它要求分数是**标定过的**（模块 02 的 ECE / 可靠性图）。')"""),
    code("""# ── 「证据卡死」：无界累加是会出人命的 bug ──
sc = [0.97] * 80 + [0.0] * 40          # 跟了 80 帧，然后彻底看不见了
fl = [True] * 80 + [False] * 40

l_noclamp, rep_noclamp = bayes_accumulate(sc, fl, clamp=1e9)
l_clamp,   rep_clamp   = bayes_accumulate(sc, fl, clamp=6.0)
l_decay,   rep_decay   = bayes_accumulate(sc, fl, clamp=6.0, decay=0.98)

def drop_frame(rep):
    '''从第 80 帧起，第几帧撤销上报？None = 一直没撤。'''
    for i in range(80, len(rep)):
        if not rep[i]:
            return i - 80 + 1
    return None

print(f"{'配置':<28s} {'第80帧的 logodds':>18s} {'撤销所需帧数':>14s}")
for name, l_, r_ in [('无 clamp（错误实现）', l_noclamp, rep_noclamp),
                     ('clamp=6', l_clamp, rep_clamp),
                     ('clamp=6 + decay=0.98', l_decay, rep_decay)]:
    df = drop_frame(r_)
    txt = f'{df} 帧 ({df*D_FRAME:.1f} m)' if df else '**永远撤不掉**'
    print(f'{name:<28s} {l_[79]:>18.1f} {txt:>14s}')

assert drop_frame(rep_noclamp) is None, '无 clamp 时 40 帧也撤不掉'
assert drop_frame(rep_clamp) is not None and drop_frame(rep_clamp) < 20
assert drop_frame(rep_decay) <= drop_frame(rep_clamp)
print('\\n🚨 无 clamp 时 logodds 累到 %.0f，40 帧的负证据（每帧 -0.4）根本推不动它 ——'
      % l_noclamp[79])
print('   系统会坚称前方有一块限速牌，直到轨迹被 max_age 强制删除。')
print('✅ 三件套缺一不可：① clamp（±5~8）② 时间衰减 ③ 观测相关性降权。')"""),
    code("""# ── 观测相关性：相邻帧根本不独立 ──
# 若相邻帧相关系数 rho，n 帧的**有效独立样本数** n_eff ≈ n / (1 + 2*sum_{k<n}(1-k/n)*rho^k)
def n_effective(n, rho):
    if rho <= 0:
        return float(n)
    s = sum((1 - k / n) * rho ** k for k in range(1, n))
    return n / (1 + 2 * s)

print(f"{'帧数 n':>7s} " + ' '.join(f'{f"rho={r}":>10s}' for r in [0.0, 0.5, 0.9, 0.95]))
for n in [5, 10, 30, 60]:
    print(f'{n:>7d} ' + ' '.join(f'{n_effective(n, r):>10.2f}'
                                for r in [0.0, 0.5, 0.9, 0.95]))

assert n_effective(10, 0.0) == 10.0
assert n_effective(30, 0.9) < 5.0, '强相关下 30 帧的有效样本量不到 5'
print('\\n⚠️  rho=0.9 时，30 帧观测的有效独立样本量只有 %.1f 个。' % n_effective(30, 0.9))
print('   把它们当 30 个独立证据，置信度会虚高一到两个数量级。')
print('✅ 粗糙但有效的补救：每帧 logit 除以 corr_div（≈ n/n_eff），或每 n 帧才计一次证据。')

# 降权后的效果：同样 30 帧 0.90 的观测
sc30, fl30 = [0.90] * 30, [True] * 30
l_naive, _ = bayes_accumulate(sc30, fl30, clamp=1e9, corr_div=1.0)
l_corr,  _ = bayes_accumulate(sc30, fl30, clamp=1e9, corr_div=30/n_effective(30, 0.9))
print(f'\\n30 帧 score=0.90:  天真累积 logodds={l_naive[-1]:.1f} '
      f'(≈ 1-1e-{int(l_naive[-1]/2.3):d} 的置信度)  vs  相关性降权后 {l_corr[-1]:.1f}')
assert l_corr[-1] < l_naive[-1] / 4"""),

    md("""## 6 · 迟滞 + 生命周期状态机：把闪烁率打下来

单阈值 = 每帧在阈值附近抛一次硬币。迟滞用**两个阈值造一个死区**，
让噪声在死区里怎么抖都不改变状态。"""),
    code("""def flicker_stats(states):
    '''返回 (翻转次数, 每帧翻转率)。'''
    flips = sum(1 for i in range(1, len(states)) if states[i] != states[i-1])
    return flips, flips / max(1, len(states))

def single_threshold(vals, tau):
    return [v >= tau for v in vals]

def hysteresis(vals, tau_on, tau_off):
    out, on = [], False
    for v in vals:
        on = (v >= tau_on) if not on else (v >= tau_off)
        out.append(on)
    return out

N = 600
conf = 0.50 + rng.normal(0, 0.10, N)          # 置信量在阈值附近抖动，sigma=0.10
s_single = single_threshold(conf, 0.50)
s_hyst   = hysteresis(conf, 0.70, 0.30)       # 死区宽 4σ
s_hyst_n = hysteresis(conf, 0.65, 0.35)       # 死区宽 3σ

print(f"{'策略':<26s} {'翻转次数':>10s} {'每帧翻转率':>12s} {'ON 占比':>9s}")
for name, st in [('单阈值 0.50', s_single),
                 ('迟滞 0.65 / 0.35 (3σ)', s_hyst_n),
                 ('迟滞 0.70 / 0.30 (4σ)', s_hyst)]:
    f_, r_ = flicker_stats(st)
    print(f'{name:<26s} {f_:>10d} {r_:>12.4f} {np.mean(st):>9.2f}')

f_s, _ = flicker_stats(s_single)
f_h, _ = flicker_stats(s_hyst)
assert f_s > 200, '单阈值应频繁翻转'
assert f_h * 5 < f_s, '4σ 死区应把翻转次数降一个数量级'
print(f'\\n✅ 翻转次数 {f_s} → {f_h}，降了 {f_s/max(1,f_h):.0f} 倍，代价是一行代码 + 两个常数。')
print('⚠️  但迟滞的代价在反方向：**一旦误报上去，撤销也要跨越同样宽的死区** ——')
print('   「误报持续时长」会系统性变长。所以 τ_off 不能设得太低。')"""),
    code("""# ── 完整的生命周期状态机 + 跟踪器 ──
class Track:
    _next = 0
    def __init__(self, box, score, frame_i):
        Track._next += 1
        self.id = Track._next
        self.box = box.astype(float).copy()
        self.Z = F_PX * SIGN_M / max(box[2] - box[0], 1e-6)
        self.w0 = float(box[2] - box[0]); self.Z0 = self.Z
        self.d_cum = 0.0
        self.logodds = logit(score)
        self.hits = 1; self.misses = 0; self.age = 1
        self.state = 'tentative'; self.reported = False
        self.flips = 0; self.first_report_Z = None
        self.born = frame_i; self.static_ok = True

    def predict(self, d=D_FRAME):
        self.box = predict_box(self.box, self.Z, d)
        self.Z = max(self.Z - d, 1.0); self.d_cum += d; self.age += 1

    def check_static(self, min_obs=8, thr=0.25):
        '''运动一致性门：漂移过大 → 不是静止标志（前车广告/车身贴纸）。'''
        if self.hits < min_obs:
            return
        w_t = float(self.box[2] - self.box[0])
        self.static_ok = abs(motion_drift(self.w0, w_t, self.Z0, self.d_cum)) < thr

class Tracker:
    def __init__(self, n_init=3, max_age=6, tau_on=3.0, tau_off=1.0,
                 miss_llr=-0.5, clamp=6.0, iou_thr=0.2, use_motion_gate=True):
        self.__dict__.update(locals()); del self.self
        self.tracks = []

    def step(self, dets, frame_i):
        '''dets: [(box, score), ...]。返回本帧被上报的轨迹列表。'''
        for t in self.tracks:
            t.predict()
        boxes = [d[0] for d in dets]
        m, ut, ud = associate([t.box for t in self.tracks], boxes, self.iou_thr)
        for ti, di in m:
            t = self.tracks[ti]; box, sc = dets[di]
            t.box = box.astype(float).copy()
            t.Z = F_PX * SIGN_M / max(box[2] - box[0], 1e-6)
            t.logodds = max(-self.clamp, min(self.clamp, t.logodds + logit(sc)))
            t.hits += 1; t.misses = 0
        for ti in ut:
            t = self.tracks[ti]
            t.logodds = max(-self.clamp, min(self.clamp, t.logodds + self.miss_llr))
            t.misses += 1
        for di in ud:
            self.tracks.append(Track(dets[di][0], dets[di][1], frame_i))
        # ── 生命周期 + 迟滞 ──
        alive, reported = [], []
        for t in self.tracks:
            t.check_static()
            if t.state == 'tentative' and t.hits >= self.n_init and t.logodds >= self.tau_on:
                t.state = 'confirmed'
            if t.misses >= self.max_age or t.logodds <= -self.clamp + 1e-9:
                continue                                  # deleted
            if t.state == 'confirmed':
                gate = t.static_ok or not self.use_motion_gate
                new_rep = (t.logodds >= self.tau_on) if not t.reported else \\
                          (t.logodds >= self.tau_off)
                new_rep = new_rep and gate
                if new_rep != t.reported:
                    t.flips += 1; t.reported = new_rep
                    if new_rep and t.first_report_Z is None:
                        t.first_report_Z = t.Z
                if t.reported:
                    reported.append(t)
            alive.append(t)
        self.tracks = alive
        return reported"""),
    code("""# ── 造一个完整场景：2 块真标志 + 随机杂波 + 1 块「前车尾部广告」 ──
def build_scene(seed=11):
    g = np.random.default_rng(seed)
    tr1 = approach_track(Z0=120, Z1=15, X=3.2, Y=-1.8)     # 右侧限速牌
    tr2 = approach_track(Z0=95,  Z1=15, X=-2.6, Y=-2.2)    # 左侧警告牌
    n = max(len(tr1), len(tr2))
    frames = []
    for i in range(n):
        dets = []
        for tr, off in [(tr1, 0), (tr2, 20)]:              # tr2 晚 20 帧入场
            k = i - off
            if 0 <= k < len(tr):
                Z, b = tr[k]; w = b[2] - b[0]
                if g.random() < p_detect(w):
                    sc = float(np.clip(g.normal(score_mu(w), 0.08), 0.05, 0.99))
                    jit = g.normal(0, 0.6, 4)              # 框抖动
                    dets.append((b + jit, sc))
        if g.random() < 0.06:                              # 单帧随机杂波
            cx_, cy_ = g.uniform(200, 1700), g.uniform(200, 800)
            w_ = g.uniform(10, 30)
            dets.append((np.array([cx_-w_/2, cy_-w_/2, cx_+w_/2, cy_+w_/2]),
                         float(g.uniform(0.3, 0.7))))
        if 30 <= i < 75:                                   # 前车尾部广告：持续 45 帧中等分
            Zb = 40.0 - (i - 30) * D_FRAME * 0.10          # 相对接近速度只有 1/10
            wb = px_size(Zb); ub = CX + F_PX * 0.4 / Zb; vb = CY + F_PX * 0.2 / Zb
            dets.append((np.array([ub-wb/2, vb-wb/2, ub+wb/2, vb+wb/2]) + g.normal(0, .5, 4),
                         float(np.clip(g.normal(0.62, 0.05), 0, .95))))
        frames.append(dets)
    return frames, tr1, tr2

frames, tr1, tr2 = build_scene()
print(f'场景共 {len(frames)} 帧，平均每帧 {np.mean([len(f) for f in frames]):.2f} 个检测')

def run(use_gate, **kw):
    Track._next = 0
    tk = Tracker(use_motion_gate=use_gate, **kw)
    ever = Counter()
    for i, dets in enumerate(frames):
        for t in tk.step(dets, i):
            ever[t.id] += 1
    return tk, ever

tk_gate,   ev_g = run(True)
tk_nogate, ev_n = run(False)

def persistent(ever, min_frames=10):
    '''持续上报 >= min_frames 帧的轨迹 —— 这才是下游真正会当真的输出。'''
    return {k: v for k, v in ever.items() if v >= min_frames}

print(f"\\n{'配置':<18s} {'持续上报轨迹数':>14s} {'总上报帧数':>11s}  各轨迹上报帧数")
for nm, ev in [('开运动一致性门', ev_g), ('关运动一致性门', ev_n)]:
    print(f'{nm:<18s} {len(persistent(ev)):>14d} {sum(ev.values()):>11d}  {dict(ev)}')

assert len(persistent(ev_g)) == 2, '开门后只有 2 块真标志被持续上报'
assert len(persistent(ev_n)) == 3, '关门后前车广告也被持续上报了 45 帧'
assert sum(ev_g.values()) < sum(ev_n.values()) - 30
print('\\n✅ 运动一致性门干掉了「持续 45 帧、分数 0.62」的前车广告 ——')
print('   这类误检**贝叶斯累积挡不住**（0.62 累 45 帧必然越过 τ_on），')
print('   必须靠**物理约束**而不是靠调阈值。')
print('⚠️  但它仍漏出了 4 帧：物理门需要 min_obs=8 帧观测才能判定，')
print('   在那之前只能靠 n_init / τ_on 挡。**没有任何单一机制能包打天下。**')"""),
    code("""# ── 首报距离 / 闪烁次数：把状态机参数连到可测指标上 ──
def eval_config(n_init, max_age, tau_on, tau_off):
    Track._next = 0
    tk = Tracker(n_init=n_init, max_age=max_age, tau_on=tau_on, tau_off=tau_off)
    reported_ids, flips = set(), 0
    for i, dets in enumerate(frames):
        for t in tk.step(dets, i):
            reported_ids.add(t.id)
    firsts = [t.first_report_Z for t in tk.tracks if t.first_report_Z is not None]
    flips = sum(t.flips for t in tk.tracks)
    return len(reported_ids), (max(firsts) if firsts else 0.0), flips

print(f"{'配置':<34s} {'上报轨迹数':>10s} {'最远首报距离':>13s} {'状态翻转':>9s}")
rows = []
for n_init, tau_on, tau_off in [(1, 1.0, 0.5), (2, 2.0, 1.0), (3, 3.0, 1.0), (5, 4.0, 1.5)]:
    n_rep, far, fl = eval_config(n_init, 6, tau_on, tau_off)
    rows.append((n_init, tau_on, n_rep, far, fl))
    print(f'{f"n_init={n_init} tau_on={tau_on} tau_off={tau_off}":<34s} '
          f'{n_rep:>10d} {far:>12.1f}m {fl:>9d}')

assert rows[0][2] >= rows[-1][2], '越激进的配置上报的轨迹越多（含误报）'
assert rows[0][3] >= rows[-1][3] - 1e-6, '越激进首报距离越远'
print('\\n✅ 每个参数都直接映射到一个评测指标（模块 05 会正式定义它们）：')
print('   n_init / tau_on ↔ FP per km  vs  首次检出距离')
print('   max_age         ↔ 遮挡鲁棒性  vs  误报持续时长')
print('   tau_off         ↔ 闪烁次数    vs  误报持续时长')"""),

    md("""## 7 · 延迟-稳定性权衡：把「米」和「误报数」放进同一个目标函数

这是本模块的落点。**不存在两全的设置**，只有写下目标函数才能停止争论。"""),
    code("""def fp_confirm_prob(q, K, M):
    '''背景误检通过 M-of-K 的概率 = 二项分布尾和。'''
    return sum(math.comb(K, i) * q**i * (1-q)**(K-i) for i in range(M, K+1))

def expected_delay_frames(p, K, M):
    '''M-of-K 滑窗的**精确**期望确认延迟（吸收马尔可夫链 + 线性求解）。
       状态 = 最近 min(t,K) 帧的命中模式；命中数 >= M 即吸收。'''
    states, idx, seen, stack = [], {}, {()}, [()]
    while stack:
        s = stack.pop(); idx[s] = len(states); states.append(s)
        for f in (0, 1):
            ns = (s + (f,))[-K:]
            if sum(ns) >= M or ns in seen:
                continue
            seen.add(ns); stack.append(ns)
    n = len(states)
    A = np.eye(n); b = np.ones(n)           # E[s] = 1 + Σ P(s->s') E[s']
    for s in states:
        i = idx[s]
        for f, pr in ((1, p), (0, 1 - p)):
            ns = (s + (f,))[-K:]
            if sum(ns) < M:                 # 吸收态的 E = 0，无需入方程
                A[i, idx[ns]] -= pr
    return float(np.linalg.solve(A, b)[idx[()]])

def mofk_tradeoff(p, q, K, M, v_ms=V_MS, fps=FPS):
    '''返回 (期望确认延迟帧数, 折算距离 m, 误检被确认的概率)。'''
    df = expected_delay_frames(p, K, M)
    return df, df * v_ms / fps, fp_confirm_prob(q, K, M)

# 先验证 DP 的正确性：K=M=1 是几何分布，K=M=2 是「连续两次成功」
assert abs(expected_delay_frames(0.6, 1, 1) - 1/0.6) < 1e-9
assert abs(expected_delay_frames(0.6, 2, 2) - (1+0.6)/0.6**2) < 1e-9
print('✅ 精确延迟 DP 通过解析解校验（几何分布 / 连续两次成功）\\n')

P_DET, Q_FP = 0.60, 0.05
print(f'p(单帧检出)={P_DET}  q(单帧误检通过)={Q_FP}  {V_KMH} km/h  {FPS:.0f} FPS\\n')
print(f"{'策略':>10s} {'近似 M/p':>9s} {'精确延迟':>9s} {'延迟(m)':>9s} "
      f"{'FP 确认率':>12s} {'相对 1-of-1':>12s}")
base = fp_confirm_prob(Q_FP, 1, 1)
for K, M in [(1, 1), (3, 2), (5, 3), (7, 4), (9, 5), (3, 3), (5, 5)]:
    df, dm, fp = mofk_tradeoff(P_DET, Q_FP, K, M)
    print(f'{f"{M}-of-{K}":>10s} {M/P_DET:>9.2f} {df:>9.2f} {dm:>9.1f} '
          f'{fp:>12.2e} {base/fp:>11.0f}×')

df, dm, fp = mofk_tradeoff(P_DET, Q_FP, 5, 3)
assert abs(fp - 1.1581e-3) < 1e-6, f'3-of-5 的 FP 确认率应为 1.158e-3，得到 {fp}'
assert df > 3 / P_DET, '精确延迟必然大于「M 次成功」的负二项期望'
assert expected_delay_frames(P_DET, 3, 3) > expected_delay_frames(P_DET, 5, 3)
print(f'\\n⚠️  常见的近似 M/p **系统性低估延迟**，且 K 越接近 M 低估越狠')
print(f'   （3-of-3: 近似 {3/P_DET:.2f} vs 精确 {expected_delay_frames(P_DET,3,3):.2f} 帧）——')
print('   用它做优化会把你骗到「连续 M 帧」这类过于保守的配置上去。')
print(f'✅ 1-of-1 → 3-of-5：误检率降 {base/fp:.0f} 倍，首报距离只后退 {dm:.1f} m。')
print(f'   相对 60 m 的检出距离，这是 {dm/60*100:.1f}% 的损失 —— **延迟在 TSR 里非常便宜**。')
print('⚠️  边界条件：可变电子牌切换 / 临时施工牌 / 近距离突然露出，可观测帧数不足，')
print('   此时延迟的代价陡增 —— 成熟系统让 M 随「剩余可观测帧数的估计」自适应。')"""),
    code("""# ── 显式目标函数与帕累托前沿 ──
RHO_BG = 200.0        # 每公里的「误检机会」数（背景框的出现频次，工程实测量）

def objective(p, q, K, M, w_d=1.0, w_fp=300.0):
    '''J = w_d * 首报距离损失(m) + w_fp * 每公里误报数。'''
    _, dist, fp = mofk_tradeoff(p, q, K, M)
    fp_per_km = fp * RHO_BG
    return w_d * dist + w_fp * fp_per_km, dist, fp_per_km

cands = [(K, M) for K in range(1, 10) for M in range(1, K+1)]
res = sorted([(K, M) + objective(P_DET, Q_FP, K, M) for K, M in cands], key=lambda r: r[2])
print(f"{'策略':>10s} {'J':>9s} {'首报损失(m)':>12s} {'FP/km':>10s}")
for K, M, J, dist, fpkm in res[:6]:
    print(f'{f"{M}-of-{K}":>10s} {J:>9.2f} {dist:>11.1f} {fpkm:>10.4f}')
best_K, best_M, J_best = res[0][0], res[0][1], res[0][2]
J_1of1 = objective(P_DET, Q_FP, 1, 1)[0]
print(f'\\n最优: {best_M}-of-{best_K}  J={J_best:.2f}   （1-of-1 的 J={J_1of1:.2f}）')
assert J_best < J_1of1, '最优配置应优于 1-of-1'
assert best_M >= 2 and best_K > best_M, '应该攒帧，且窗口要留出容错余量（K > M）'

# 权重敏感性：w_fp 从 30 扫到 3000
print(f"\\n{'w_fp':>8s} {'最优策略':>10s} {'首报损失(m)':>12s} {'FP/km':>10s}")
prev_M = 0
for w_fp in [30, 100, 300, 1000, 3000]:
    r = sorted([(K, M) + objective(P_DET, Q_FP, K, M, w_fp=w_fp) for K, M in cands],
               key=lambda x: x[2])[0]
    print(f'{w_fp:>8d} {f"{r[1]}-of-{r[0]}":>10s} {r[3]:>11.1f} {r[4]:>10.4f}')
    assert r[1] >= prev_M, 'w_fp 越大，最优策略应越保守'
    prev_M = r[1]
print('\\n✅ 这个式子的价值不在于精确最优解（w_fp 本来就是拍的），')
print('   而在于**把「米」和「误报数」放到同一个尺度上** ——')
print('   团队里关于「要不要多攒两帧」的争论，十次有九次是因为没人写下这个式子。')"""),

    md("""## ✏️ 练习 1：带门控的关联

实现 `associate_gated(track_boxes, det_boxes, iou_thr, max_center_dist)`：
在 IoU 门控之外**再加一层中心距离门控**（尺度归一化：`‖Δc‖ / max(w,h) <= max_center_dist`），
用匈牙利求解，返回 `(matches, unmatched_tracks, unmatched_dets)`。
两层门控都要**在进矩阵前**和**出结果后**各做一次。"""),
    code("""def associate_gated(track_boxes, det_boxes, iou_thr=0.1, max_center_dist=1.0):
    # TODO: ① 算 IoU 矩阵与尺度归一化中心距离矩阵
    #       ② 两个门控都不满足则代价设为 BIG
    #       ③ hungarian 求解，出结果后逐对复查两个门控
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
Tb = [np.array([100., 100., 108., 108.]),      # 8px 小框
      np.array([500., 500., 540., 540.])]      # 40px 大框
Db = [np.array([103., 100., 111., 108.]),      # 与 T0 位移 3px：IoU=0.45，中心距/8=0.375
      np.array([560., 500., 600., 540.])]      # 与 T1 位移 60px：IoU=0，中心距/40=1.5
m1, u1, d1 = associate_gated(Tb, Db, iou_thr=0.1, max_center_dist=1.0)
assert m1 == [(0, 0)], f'小框应关联上（IoU 0.45），大框位移过大应拒绝，得到 {m1}'
assert u1 == [1] and d1 == [1]

# 纯 IoU 门控会漏掉「IoU=0 但其实很近」的小目标；中心距离门控能救回来
Tc = [np.array([100., 100., 106., 106.])]      # 6px 框
Dc = [np.array([107., 100., 113., 106.])]      # 位移 7px：IoU=0，中心距/6=1.17
m2, _, _ = associate_gated(Tc, Dc, iou_thr=0.1, max_center_dist=1.0)
m3, _, _ = associate_gated(Tc, Dc, iou_thr=0.0, max_center_dist=1.5)
assert m2 == [], 'IoU=0 且中心距 1.17 > 1.0，应拒绝'
assert m3 == [(0, 0)], '放宽中心距门限后应关联上'
assert associate_gated([], Db)[2] == [0, 1] and associate_gated(Tb, [])[1] == [0, 1]
print('✅ 练习 1 通过：**小目标上中心距离比 IoU 稳健得多** ——')
print('   IoU 在框不相交时恒为 0，没有任何梯度可用；中心距离仍然有序。')"""),

    md("""## ✏️ 练习 2：安全的贝叶斯更新

实现 `safe_update(l, detected, score, miss_llr=-0.4, clamp=6.0, decay=1.0, corr_div=1.0)`，
返回更新后的 log-odds。要求同时具备**衰减 → 累加 → 截断**三步（注意顺序），
且 `corr_div` 对**检出帧的证据**降权（miss 惩罚不降权）。"""),
    code("""def safe_update(l, detected, score, miss_llr=-0.4, clamp=6.0, decay=1.0, corr_div=1.0):
    # TODO: ① l *= decay  ② 检出则加 logit(score)/corr_div，否则加 miss_llr
    #       ③ clip 到 [-clamp, clamp]
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert abs(safe_update(0.0, True, 0.98) - logit(0.98)) < 1e-9
assert abs(safe_update(0.0, False, 0.0) - (-0.4)) < 1e-9
assert abs(safe_update(0.0, True, 0.98, corr_div=2.0) - logit(0.98)/2) < 1e-9
assert abs(safe_update(0.0, False, 0.0, corr_div=2.0) - (-0.4)) < 1e-9, 'miss 惩罚不降权'
assert abs(safe_update(100.0, True, 0.99, clamp=6.0) - 6.0) < 1e-9, 'clamp 必须生效'
assert abs(safe_update(-100.0, False, 0.0, clamp=6.0) + 6.0) < 1e-9
assert abs(safe_update(4.0, False, 0.0, miss_llr=0.0, decay=0.5) - 2.0) < 1e-9, '衰减在累加前'

# 「证据卡死」不再发生：80 帧强证据后，撤销所需帧数有界
l = 0.0
for _ in range(80):
    l = safe_update(l, True, 0.97, clamp=6.0)
n_drop = 0
while l > 1.0:
    l = safe_update(l, False, 0.0, clamp=6.0); n_drop += 1
assert n_drop <= 15, f'clamp=6 时撤销应在 15 帧内，实际 {n_drop}'
print(f'80 帧强证据后 clamp 到 6.0，撤销只需 {n_drop} 帧 '
      f'({n_drop*D_FRAME:.1f} m) —— 无 clamp 时永远撤不掉。')
print('✅ 练习 2 通过：**顺序是 衰减 → 累加 → 截断**，截断放最后才真正有界。')"""),

    md("""## ✏️ 练习 3：迟滞判决与闪烁率

实现 `hysteresis_report(values, tau_on, tau_off)`，返回
`(每帧布尔判决列表, 翻转次数, 首次上报的下标或 None)`。
要求 `tau_on >= tau_off`，否则抛 `ValueError`。"""),
    code("""def hysteresis_report(values, tau_on, tau_off):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
vals = [0.1, 0.8, 0.5, 0.4, 0.2, 0.9, 0.6]
st, flips, first = hysteresis_report(vals, 0.7, 0.3)
#  0.1→OFF  0.8→ON  0.5→ON(>=0.3)  0.4→ON  0.2→OFF  0.9→ON  0.6→ON
assert st == [False, True, True, True, False, True, True], st
assert flips == 3 and first == 1, (flips, first)

st2, flips2, first2 = hysteresis_report(vals, 0.95, 0.9)
assert first2 is None and flips2 == 0 and not any(st2), '从未越过 τ_on'

try:
    hysteresis_report(vals, 0.3, 0.7); raise AssertionError('τ_on < τ_off 应报错')
except ValueError:
    pass

# 与单阈值对比：600 帧噪声
noise = 0.50 + np.random.default_rng(3).normal(0, 0.10, 600)
_, f_single, _ = hysteresis_report(noise, 0.50, 0.50)
_, f_hyst, _   = hysteresis_report(noise, 0.70, 0.30)
print(f'单阈值 0.50 翻转 {f_single} 次；迟滞 0.70/0.30 翻转 {f_hyst} 次'
      f'（降 {f_single/max(1,f_hyst):.0f} 倍）')
assert f_hyst * 5 < f_single
print('✅ 练习 3 通过：迟滞是**幅度维**的去抖，「连续 N 帧」是**时间维**的去抖，两者正交。')"""),

    md("""## ✏️ 练习 4：延迟-稳定性的最优 M-of-K

实现 `best_mofk(p, q, k_max, w_d, w_fp, rho_bg, v_ms, fps)`：
在 `1 <= M <= K <= k_max` 中枚举，返回使
`J = w_d * 首报距离损失(m) + w_fp * (FP确认率 * rho_bg)` 最小的 `(K, M, J)`。
平局时取 **K 更小**的（同样效果下更省缓冲区、更好测试）。"""),
    code("""def best_mofk(p, q, k_max=9, w_d=1.0, w_fp=300.0, rho_bg=200.0, v_ms=V_MS, fps=FPS):
    # TODO: 用上面的 expected_delay_frames / fp_confirm_prob
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
K_, M_, J_ = best_mofk(0.60, 0.05)
K1, M1, J1 = best_mofk(0.60, 0.05, k_max=1)
assert (K1, M1) == (1, 1)
assert J_ <= J1, '允许攒帧后目标函数不应变差'
assert M_ >= 2, f'在这组权重下应该攒帧，得到 {M_}-of-{K_}'

# 单调性：w_fp 越大越保守
Ms = [best_mofk(0.60, 0.05, w_fp=w)[1] for w in [10, 100, 1000, 10000]]
assert Ms == sorted(Ms), f'w_fp 增大时 M 应单调不减，得到 {Ms}'
# 单帧检出率越低，攒同样多帧的距离代价越大 → 最优 M 不应更大
assert best_mofk(0.30, 0.05)[1] <= best_mofk(0.90, 0.05)[1] + 1

print(f"{'p':>6s} {'q':>7s} {'w_fp':>7s} {'最优':>10s} {'J':>8s}")
for p_, q_, w_ in [(0.6, 0.05, 300), (0.6, 0.20, 300), (0.9, 0.05, 300), (0.6, 0.05, 30)]:
    K2, M2, J2 = best_mofk(p_, q_, w_fp=w_)
    print(f'{p_:>6.2f} {q_:>7.2f} {w_:>7d} {f"{M2}-of-{K2}":>10s} {J2:>8.2f}')
print('\\n✅ 练习 4 通过：**写下目标函数，争论就从「感觉」变成「w_fp 该取多少」** ——')
print('   而后者是可以拿数据和用户反馈来谈的问题。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def associate_gated(track_boxes, det_boxes, iou_thr=0.1, max_center_dist=1.0):
    nt, nd = len(track_boxes), len(det_boxes)
    if nt == 0 or nd == 0:
        return [], list(range(nt)), list(range(nd))

    def ok(a, b):
        ca = np.array([(a[0]+a[2])/2, (a[1]+a[3])/2])
        cb = np.array([(b[0]+b[2])/2, (b[1]+b[3])/2])
        scale = max(a[2]-a[0], a[3]-a[1], 1e-6)
        return (iou(a, b) >= iou_thr) or \\
               (float(np.linalg.norm(ca - cb)) / scale <= max_center_dist)

    C = np.empty((nt, nd))
    for i, a in enumerate(track_boxes):
        for j, b in enumerate(det_boxes):
            if ok(a, b):
                ca = np.array([(a[0]+a[2])/2, (a[1]+a[3])/2])
                cb = np.array([(b[0]+b[2])/2, (b[1]+b[3])/2])
                scale = max(a[2]-a[0], a[3]-a[1], 1e-6)
                C[i, j] = (1.0 - iou(a, b)) + float(np.linalg.norm(ca-cb)) / scale
            else:
                C[i, j] = BIG
    r, c = hungarian(C)
    matches, mt, md_ = [], set(range(nt)), set(range(nd))
    for i, j in zip(r.tolist(), c.tolist()):
        if ok(track_boxes[i], det_boxes[j]):          # 出结果后复查
            matches.append((i, j)); mt.discard(i); md_.discard(j)
    return sorted(matches), sorted(mt), sorted(md_)"""),
    code("""# 练习 2 参考答案
def safe_update(l, detected, score, miss_llr=-0.4, clamp=6.0, decay=1.0, corr_div=1.0):
    l = l * decay                                     # ① 先衰减
    l = l + (logit(score) / corr_div if detected else miss_llr)   # ② 再累加
    return max(-clamp, min(clamp, l))                 # ③ 最后截断"""),
    code("""# 练习 3 参考答案
def hysteresis_report(values, tau_on, tau_off):
    if tau_on < tau_off:
        raise ValueError('必须 tau_on >= tau_off，否则迟滞退化甚至产生振荡')
    states, on, flips, first = [], False, 0, None
    for v in values:
        new = (v >= tau_on) if not on else (v >= tau_off)
        if new != on:
            flips += 1
            if new and first is None:
                first = len(states)
        on = new
        states.append(on)
    return states, flips, first"""),
    code("""# 练习 4 参考答案
def best_mofk(p, q, k_max=9, w_d=1.0, w_fp=300.0, rho_bg=200.0, v_ms=V_MS, fps=FPS):
    best = None
    for K in range(1, k_max + 1):
        for M in range(1, K + 1):
            dist = expected_delay_frames(p, K, M) * v_ms / fps
            J = w_d * dist + w_fp * fp_confirm_prob(q, K, M) * rho_bg
            key = (round(J, 9), K)                    # 平局取 K 更小
            if best is None or key < best[0]:
                best = (key, K, M, J)
    return best[1], best[2], best[3]"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接落地的 TSR 时序融合配置与骨架"""),
    code("""RECIPE = r'''
# ═══════════════════════════════════════════════════════════════════
# TSR 时序融合模块 —— 量产配置模板（YAML 风格，可直接改写成项目配置）
# ═══════════════════════════════════════════════════════════════════
temporal_fusion:

  # ── 1. 运动补偿（TSR 的免费午餐，必开）────────────────────────────
  motion_compensation:
    enabled: true
    source: [wheel_odometry, imu]      # 必须与图像时间戳对齐！错 30ms @100km/h = 0.8m
    model: full_se3                    # 直线段可退化为标量 d；**弯道必须用完整 R,t**
    max_time_skew_ms: 5                # 超过就降级为「不补偿 + 放宽门限」
    intrinsics: from_calib             # cx,cy 用错 -> 扩张中心偏移 -> 补偿制造残差

  # ── 2. 数据关联 ────────────────────────────────────────────────
  association:
    solver: hungarian                  # 不要用贪心：并排双牌场景会错配
    cost: 1 - IoU + lambda * center_dist_norm
    lambda: 0.5
    gate:                              # **门控做两次：进矩阵前 + 出结果后**
      iou_min: 0.10                    # 小目标要放低；配合中心距门控
      center_dist_norm_max: 1.0        # ||dc|| / max(w,h)
      scale_ratio_range: [0.7, 1.45]   # 框尺寸突变 -> 多半是错配
    bytetrack_two_stage: true          # 高分建轨，低分只用于**续**轨（远距离救命）
    high_score_thr: 0.55
    low_score_thr: 0.15

  # ── 3. 证据累积（贝叶斯 log-odds）───────────────────────────────
  evidence:
    prior_logodds: 0.0                 # 地图先验在这里注入，**上限 ±2.0**
    map_prior_max: 2.0                 # 先验只能「加速确认」，不能否决强证据
    miss_logodds: -0.50
    clamp: 6.0                         # 🚨 必须有！否则「证据卡死」
    decay_per_frame: 0.98              # 旧证据自然遗忘
    correlation_divisor: 4.0           # 相邻帧不独立：rho~0.9 时 n_eff ≈ n/4
    require_calibrated_scores: true    # 未标定的分数会让 logit 完全失真

  # ── 4. 生命周期状态机 ──────────────────────────────────────────
  lifecycle:
    n_init: 3                          # tentative 阶段不上报（挡单帧闪光误检）
    max_age_confirmed: 8               # 抗遮挡：前车挡 8 帧内仍 coasting
    max_age_low_quality: 2             # **按轨迹质量分档**，不要一刀切
    coast_uses_motion_model: true      # 🚨 coasting 期间必须继续推进位置，不能冻结

  # ── 5. 迟滞判决 ────────────────────────────────────────────────
  hysteresis:
    tau_on: 3.0                        # ↔ FP/km、首次检出距离
    tau_off: 1.0                       # ↔ 闪烁次数、误报持续时长
    min_on_frames: 2                   # 时间维迟滞，与幅度维正交
    min_off_frames: 3

  # ── 6. 物理合理性过滤（几乎零成本，收益极高）────────────────────
  physics_gate:
    static_drift_max: 0.25             # |log(w_t/w_0) - log(Z_0/Z_t)| 超了 = 非静止
    min_obs_for_gate: 8
    # 干掉：前车尾部广告、车身贴纸、对向移动广告车
    # 干不掉：路侧固定广告牌（静止的）—— 需要外观/上下文，别高估这一条

  # ── 7. 自适应策略（从「能跑」到「量产」的分水岭）──────────────────
  adaptive:
    reduce_n_init_when_close: true     # 近处剩余可观测帧数少，攒不起
    close_range_m: 35
    n_init_close: 1
    boost_on_variable_sign: true       # 可变电子牌切换时必须快速响应

# ═══════════════════════════════════════════════════════════════════
# 每帧主循环骨架（伪代码，与本 notebook 的 Tracker.step 一一对应）
# ═══════════════════════════════════════════════════════════════════
def step(frame, dets, ego_motion):
    for t in tracks:
        t.predict(ego_motion)              # 1) 运动补偿：静止假设下的精确外推
    M, UT, UD = associate(tracks, dets)    # 2) 门控 + 匈牙利 + 出结果后复查
    for ti, di in M:  tracks[ti].update(dets[di])          # 3) 证据累积（clamp!）
    for ti in UT:     tracks[ti].miss()
    for di in UD:     tracks.append(Track(dets[di]))
    for t in tracks:
        t.check_physics()                  # 4) 运动一致性门
        t.step_lifecycle()                 # 5) tentative/confirmed/lost + 迟滞
    return [t for t in tracks if t.reported]

# ═══════════════════════════════════════════════════════════════════
# 上线前必测的 6 个专项集（每个 100-300 帧，名字就是失效模式）
# ═══════════════════════════════════════════════════════════════════
#   occlusion_by_truck/     前车遮挡 4-10 帧，考 coasting + 重关联
#   gantry_two_signs/       门架并排双牌，考匈牙利 vs 贪心
#   leading_vehicle_ad/     前车尾部广告，考运动一致性门
#   variable_speed_sign/    可变电子牌切换，考自适应 n_init
#   curve_entry/            弯道入口，考完整 R,t 补偿（直线模型会掉点）
#   map_mismatch/           地图过期 / 临时施工牌，考先验强度上限
'''
print(RECIPE)
for key in ['clamp: 6.0', 'coast_uses_motion_model', 'static_drift_max',
            'bytetrack_two_stage', 'correlation_divisor', 'map_prior_max',
            'gate:', 'tau_off', 'n_init_close', 'gantry_two_signs']:
    assert key in RECIPE, key
print('✅ 配方覆盖：运动补偿 / 两次门控 / 两阶段关联 / clamp+衰减+相关性 / '
      '生命周期 / 迟滞 / 物理门 / 自适应 / 6 个专项集')"""),

    md("""### 小结

- **TSR 是一个「接近过程」**：同一块牌子会被观测 100+ 帧。单帧检测器输出的是**证据**，
  不是**结论**；时序层负责把证据累积成结论，并决定何时公布。把这两件事分开，
  是 TSR 系统设计里最重要的一次切分。
- **关联层**：IoU 在小目标上极其脆弱（8px 框位移 3px → IoU 0.24），必须换成尺度归一化的
  中心距离或马氏距离；匈牙利胜过贪心（并排双牌场景）；**门控要做两次**，
  因为匈牙利本身不认识阈值。ByteTrack 的「低分框只用来续轨」对远距离低分段直接适用。
- **运动补偿是 TSR 相对行人跟踪的巨大优势**：标志静止 + 自车运动已测 ⇒
  `s = Z/(Z−d)` 给出**精确**预测。不补偿时**近距离反而最糟**。
  反过来用，它还是一个零成本的误检过滤器（干掉前车广告，但干不掉路侧固定广告牌）。
- **投票 vs 贝叶斯**：投票丢弃分数大小（0.52 当 0.99），延迟刚性；贝叶斯利用分数强度，
  延迟自适应但**要求分数标定**。贝叶斯必须配 **clamp + 衰减 + 相关性降权**，
  否则会「证据卡死」——一个真实会出人命的 bug。
- **迟滞是幅度维去抖，「连续 N 帧」是时间维去抖，两者正交**，成熟系统都用。
  4σ 死区把翻转次数降一个数量级，代价是误报撤销也变慢（τ_off 不能太低）。
- **状态机的每个参数都映射到一个评测指标**：n_init/τ_on ↔ FP per km vs 首检距离；
  max_age ↔ 抗遮挡 vs 误报持续时长；τ_off ↔ 闪烁 vs 误报持续时长。
- **延迟与稳定性的矛盾必须写成目标函数**。1-of-1 → 3-of-5：误检率降 43 倍，
  首报距离只后退 4.6 m（占 60 m 检出距离的 7.7%）——**在 TSR 里延迟很便宜**，
  因为可观测帧数多。但可变电子牌 / 临时施工牌 / 近距离突然露出是例外，
  此时应让 M 随「剩余可观测帧数」自适应。

下一站：**模块 05 · 安全导向的评测体系** —— 本模块调出来的这些参数，
到底该用什么指标来评判？（剧透：不是 mAP。）"""),
]
