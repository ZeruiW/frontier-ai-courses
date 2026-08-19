# -*- coding: utf-8 -*-
"""C57 模块 05 · TSR 小目标实战：从物理量到工程方案。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–04（IoU 位移敏感性、FPN 层级分配、NWD、切片与级联）；C55（TSR 领域知识）与 C53 m05（延迟预算）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_tsr_small_object_case.ipynb'),
    ("核心参考", "针孔相机模型与标定、TT100K / Mapillary Traffic Sign 基准、COCO 分尺度评测协议、量产 ADAS 多相机配置"),
    ("预计时长", "读 70 分钟 + 跑 65 分钟"),
]

SECTIONS = [
    ("pinhole", "针孔模型：一个必须能当场推的换算", "".join([
        P("前四个模块都在讲「小目标为什么难、怎么办」。<strong>这一节要回答一个更基础、也更少人算得清的问题：一个交通标志到底有多少像素？</strong>不知道这个数，前面所有方法的取舍都是空谈。"),
        P("答案来自最基础的<span class=\"term\">pinhole camera model</span>（针孔相机模型）。设物体的物理尺寸为 S（米）、距离相机 Z（米）、相机的<strong>焦距用像素表示</strong>为 f（px），则该物体在图像上的像素尺寸为"),
        MATH("p \\;=\\; f\\cdot\\frac{S}{Z}"),
        P("而 f 不是相机参数表上的「28mm」，它要从<strong>分辨率与视场角</strong>换算出来。设图像宽 W（px）、水平视场角 <span class=\"term\">HFOV</span> 为 θ，则"),
        MATH("f \\;=\\; \\frac{W/2}{\\tan(\\theta/2)}"),
        ASCII("""                    图像平面（宽 W 像素）
                    ┌─────────────┐
                    │      ↕ p px │  ← 标志成的像
       ┌────────────┤             │
       │  θ/2       │             │
   ───●─────────────┼─────────────┼──────────────────  光轴
    针孔│            │             │                  ↕ S 米（标志实际尺寸）
       └────────────┤             │                  █ 标志
                    └─────────────┘
       |←── f 像素 ──→|
       |←──────────────── Z 米 ──────────────────────→|

  相似三角形:   p / f  =  S / Z     =>     **p = f · S / Z**
  焦距换算  :   tan(θ/2) = (W/2) / f  =>   **f = (W/2) / tan(θ/2)**"""),
        H3("代入真实参数：60 米外的 60cm 限速牌是多少像素？"),
        P("取一台典型的前视主摄：<strong>1920×1080、水平 FOV 60°</strong>。中国 GB 5768 的一般道路圆形禁令标志直径 60 cm（高速上是 80–120 cm，城区常见 60 cm）。"),
        MATH("f = \\frac{1920/2}{\\tan 30^\\circ} = \\frac{960}{0.5774} = \\mathbf{1662.8\\ \\text{px}} \\qquad p = 1662.8\\times\\frac{0.6}{60} = \\mathbf{16.6\\ \\text{px}}"),
        TABLE(["距离 Z", "60 cm 标志的像素尺寸", "面积", "COCO 尺度类别", "工程含义"], [
            ["<strong>15 m</strong>", "<strong>66.5 px</strong>", "4422 px²", "medium", "轻松检出并读清内容"],
            ["<strong>30 m</strong>", "<strong>33.3 px</strong>", "1107 px²", "medium（刚过 32² 线）", "可检可分类"],
            ["<strong>60 m</strong>", "<strong>16.6 px</strong>", "276 px²", "<strong>small</strong>", "能检出、<strong>读不清是限速几</strong>"],
            ["<strong>100 m</strong>", "<strong>10.0 px</strong>", "100 px²", "<strong>small（极小）</strong>", "多数检测器已经检不到"],
            ["150 m", "6.7 px", "44 px²", "small（tiny）", "在 640 输入下只剩 2.2 px，无解"],
        ]),
        DUAL(
            "这张表把整门课的所有讨论钉在了地面上。<strong>「TSR 是小目标问题」不是一句修辞——它是 p = f·S/Z 这个双曲线关系的必然结果</strong>：像素尺寸随距离<em>反比</em>衰减，你想早 1 倍距离看到，就要多 1 倍的焦距（或分辨率）。<em>60 m 外 16.6 px、100 m 外 10 px，这两个数字应该像 lr=3e-4 一样刻在脑子里。</em>",
            "严谨地补三点。<strong>① 这里的 p 是「物体在传感器上的成像尺寸」，还没算镜头 MTF、去马赛克、ISP 降噪、JPEG 压缩带来的有效分辨率损失</strong>——真实可用的判别信息通常比理论像素数还少 20–40%。<strong>② 圆形标志的「直径」在有俯仰/偏航角时会投影成椭圆</strong>，短轴会缩短 cos φ 倍；对向车道与路侧大角度的标志尤其明显。<strong>③ 长焦镜头往往有明显畸变</strong>，f 在画面边缘并非常数，严格计算要用标定得到的内参矩阵 K 而不是这个理想公式。<em>但作为工程估算与面试推导，这个公式的精度完全够用。</em>",
        ),
        CALLOUT("intuition", "<strong>这套推导在面试里极有说服力，原因是它把一个「感觉题」变成了「计算题」。</strong>被问「你怎么提升远距离交通标志的检出」时，绝大多数人会开始罗列方法（多尺度、FPN、增强、切片…）。<em>而正确的开场是：先问「要在多远检出？标志多大？相机什么参数？」，当场算出目标只有 16.6 像素，再说方法。</em><strong>因为「16.6 px」这个数字本身就否决了一半的方案</strong>（比如「换更深的 backbone」——16.6 px 的信息量摆在那里，backbone 再深也变不出信息）。<strong>把问题化归到物理量，是资深工程师最容易被识别的特征。</strong>"),
    ])),
    ("budget", "反推配置：要在多远检出，需要什么分辨率与什么 FOV", "".join([
        P("上一节是正向计算。真正有工程价值的是<strong>反向求解</strong>：给定「必须在 Z<sub>target</sub> 米外检出」这个需求，反推需要什么相机、什么输入分辨率。"),
        H3("第一步：定「最小可检像素数」p<sub>min</sub>"),
        P("这是整条推导链里唯一需要经验输入的量。它<strong>不是一个数，而是三个不同任务的三个数</strong>——这一点是本节最重要的洞察："),
        TABLE(["任务", "典型 p<sub>min</sub>", "依据", "在 60° / 1920 主摄上的最大作用距离"], [
            ["<strong>类别无关的提议</strong>（有没有一个牌子）", "<strong>8–10 px</strong>", "只需颜色团块 + 形状轮廓，不需要细节", "<strong>≈ 100–125 m</strong>"],
            ["<strong>检测</strong>（框 + 粗类：禁令/警告/指示）", "<strong>14–16 px</strong>", "红圈/黄三角的边缘要能与背景区分", "<strong>≈ 62–71 m</strong>"],
            ["<strong>细分类</strong>（限速 40 还是 60）", "<strong>24–32 px</strong>", "字形笔画要跨越至少 2–3 个像素才可辨", "<strong>≈ 31–42 m</strong>"],
            ["<strong>可靠细分类</strong>（夜间/逆光/褪色下仍准）", "<strong>40+ px</strong>", "信噪比下降时需要更多冗余像素", "≈ 25 m"],
        ]),
        MATH("Z_{\\max} \\;=\\; \\frac{f\\cdot S}{p_{\\min}} \\qquad\\text{例：}\\; \\frac{1662.8\\times 0.6}{16} = \\mathbf{62.4\\ \\text{m}}, \\qquad \\frac{1662.8\\times 0.6}{24} = \\mathbf{41.6\\ \\text{m}}"),
        DUAL(
            "把这两个数字放在一起会得到一个非常重要、也非常反直觉的结论：<strong>在同一台相机上，「发现一块牌子」的距离（62 m）比「读懂它写什么」的距离（42 m）远了整整 20 米</strong>。100 km/h 时这 20 米只有 0.75 秒。<em>也就是说，系统会有一段「我知道前面有个限速牌，但我还不知道是限速几」的时间窗</em>。<strong>这直接决定了 TSR 必须是两级的、必须有跟踪、必须能表达「已检出但类别未定」这个中间状态</strong>——而不是一个「检测即分类」的单帧模型。",
            "严谨地说，这个「检出距离 &gt; 识别距离」的间隙是所有远距识别任务的共性（车牌、红绿灯读数、路面文字都一样），根源是<strong>检测所需的空间频率低于识别所需的空间频率</strong>：判断「有个红色圆形」只需要低频轮廓，判断「是 6 还是 8」需要笔画级的高频。<em>工程上的正确应对不是把两者硬塞进一个头，而是①让检测头在更早的距离触发跟踪，②让分类头在目标长大到 p ≥ 24 px 时才给出高置信类别，③在这之前向下游输出「未知限速标志 + 位置 + 置信度」</em>——C59 模块 03 讲的感知接口设计里，这个「已检出但类别待定」的状态必须在 schema 里有位置，否则下游只能当它不存在。",
        ),
        H3("第二步：反解相机参数"),
        P("把 Z<sub>max</sub> 的式子倒过来，就得到需要多少焦距、多大分辨率或多窄的 FOV："),
        MATH("f_{\\text{req}} = \\frac{p_{\\min}\\cdot Z_{\\text{target}}}{S}, \\qquad W_{\\text{req}} = 2 f_{\\text{req}}\\tan\\frac{\\theta}{2}, \\qquad \\theta_{\\text{req}} = 2\\arctan\\!\\frac{W}{2 f_{\\text{req}}}"),
        P("代入「要在 <strong>100 米</strong>外检出（p<sub>min</sub>=16）60cm 标志」："),
        TABLE(["约束", "求解", "结果", "工程解读"], [
            ["需要的焦距", "f = 16 × 100 / 0.6", "<strong>2667 px</strong>", "是现有 1663 px 的 1.60 倍"],
            ["若保持 60° FOV，需要多宽", "W = 2 × 2667 × tan30°", "<strong>3079 px</strong>", "<strong>要上 4K（3840×2160）</strong>"],
            ["若保持 1920 宽，需要多窄 FOV", "θ = 2·arctan(960/2667)", "<strong>39.6°</strong>", "<strong>要加一路长焦相机</strong>"],
            ["若两者都不动", "—", "不可能", "只能靠时序累积 + 地图先验兜底"],
        ]),
        CALLOUT("danger", "<p>这里有一个<strong>会在系统设计题里当场翻车的陷阱</strong>：很多人以为「检测距离不够就把输入分辨率调大」。<em>调大网络输入分辨率（比如 640 → 1280）并不能增加信息</em>——如果相机本来就只有 1920 宽，把 letterbox 从 640 改成 1920 确实能把标志从 5.5 px 恢复到 16.6 px（这是真实且巨大的收益，见模块 04），<strong>但它的上限就是 16.6 px，永远到不了 100 米所需的那个尺寸</strong>。<strong>「网络输入分辨率」只能把已有的像素用满，「相机分辨率 × 焦距」才决定像素的天花板。</strong>把这两件事分清楚，是这一节的核心。</p>", "输入分辨率 ≠ 相机分辨率"),
        CALLOUT("warn", "反过来也有一个坑：<strong>算出「需要 4K」之后不能直接下单</strong>。4K 输入意味着 4× 的像素吞吐、4× 的 ISP 与传输带宽、更大的存储与回传成本、以及（如果模型输入也跟着变大）平方级增长的推理耗力。<em>模块 04 已经算过：全图原生 1920×1088 就要 25.5 ms，4K 全图更是不可能</em>。<strong>所以「提高分辨率」的正确形态几乎总是「高分辨率 + ROI 裁剪」或「加一路长焦」，而不是「整幅 4K 全跑」。</strong>"),
    ])),
    ("stride", "stride 与特征层：像素够了，格子还得够", "".join([
        P("有了 16.6 px 还不够。检测头的输出是<strong>离散的特征网格</strong>，目标必须在网格上占到足够多的格子，标签分配才有正样本可给。这是模块 01 讲过的第二重损失，这里把它量化。"),
        MATH("n_{\\text{cells}} \\;=\\; \\frac{p_{\\text{input}}}{\\text{stride}} \\qquad\\text{（目标在该层特征图上横跨的格子数）}"),
        TABLE(["特征层", "stride", "16.6 px 标志（全图 letterbox 640）", "16.6 px 标志（原生分辨率）", "33 px 标志（原生）"], [
            ["P2", "4", "1.4 格", "<strong>4.2 格</strong> ✅", "8.3 格 ✅"],
            ["P3", "8", "<strong>0.7 格</strong> ❌", "2.1 格 ⚠️", "4.2 格 ✅"],
            ["P4", "16", "0.3 格 ❌", "1.0 格 ❌", "2.1 格 ⚠️"],
            ["P5", "32", "0.2 格 ❌", "0.5 格 ❌", "1.0 格 ❌"],
        ]),
        DUAL(
            "读法：<strong>n<sub>cells</sub> &lt; 1 表示目标在该层连一个完整格子都占不满</strong>——它的全部信息被压进一个特征点里，与周围背景混叠，标签分配阶段几乎拿不到正样本。<strong>n<sub>cells</sub> ≈ 2 是勉强可用的下限</strong>（中心点分配能找到 1–4 个候选）。<strong>n<sub>cells</sub> ≥ 4 才谈得上稳定</strong>（ATSS/SimOTA 的 top-k 有足够候选可选、回归目标有足够分辨率）。<em>表里最刺眼的一行是：全图 letterbox 到 640 时，16.6 px 的标志在 P3 上只有 0.7 格——这就是「远处标志检不出」最直接的机理。</em>",
            "再用 FPN 的<strong>标准层级分配规则</strong>验算一遍（模块 02）：<code>k = k₀ + log₂(√(wh)/224)</code>，k₀=4。代入 p=16.6 得 <code>k = 4 + log₂(16.6/224) = 4 − 3.75 = <strong>0.25</strong></code>；代入 p=33.3 得 <strong>k = 1.25</strong>。<strong>也就是说，按 FPN 的原始设计，60 m 外的标志应该被分配到「P0.25 层」——比 P2 还要浅两层，而 P2 已经是绝大多数实现的最浅层。</strong>这不是实现的问题，是 FPN 的层级设计以 224 px 的 ImageNet 尺度为锚点、而交通标志系统性地比它小一个数量级。<em>实践中的应对是把分配规则的 k₀ 或锚点尺度整体下移（例如把 224 换成 64），让 P2/P3 承担主要负载——这是一个只改几行配置、却常常带来 2–4 AP<sub>small</sub> 的改动。</em>",
        ),
        P("<strong>加 P2 层的代价</strong>要算清楚。P2 的空间尺寸是 P3 的 2×2 = 4 倍，检测头在 P2 上的计算量与显存都按这个倍数增长。以典型的 FPN + 共享头结构估算："),
        TABLE(["配置", "检测头覆盖层", "头部 FLOPs（相对）", "特征点总数（640×640 输入）", "小目标召回"], [
            ["P3–P5（YOLO 默认）", "8/16/32", "1.00×", "6400+1600+400 = 8400", "基线"],
            ["<strong>P2–P5</strong>", "<strong>4</strong>/8/16/32", "<strong>≈ 4.0×</strong>", "<strong>25600</strong>+8400 = 34000", "<strong>+3–5 AP<sub>small</sub></strong>"],
            ["P2–P4（去掉 P5）", "4/8/16", "≈ 3.9×", "25600+6400+1600 = 33600", "省一点，大目标略降"],
        ]),
        CALLOUT("warn", "加 P2 还有两个容易忽略的连带成本：<strong>① NMS 与后处理的候选框数量涨了 4 倍</strong>——模块 04 算过，NMS 耗时随候选数超线性增长，且延迟方差变大（C53 m05 的重点）；<strong>② 正负样本比例进一步恶化</strong>，25600 个新增特征点里绝大多数是背景，focal loss 的 α/γ 与分配策略可能需要重调。<em>「加 P2」不是一个开关，它牵动分配、损失、后处理三处。</em>"),
        CALLOUT("intuition", "把前三节串起来，得到 TSR 小目标的<strong>三个独立瓶颈</strong>，任何方案都要说清楚它解的是哪一个：<strong>① 光学瓶颈</strong>（相机 f 与分辨率决定的像素天花板，只能换硬件或换 FOV）；<strong>② 预处理瓶颈</strong>（letterbox 把 16.6 px 压成 5.5 px，靠原生分辨率/ROI/切片解决）；<strong>③ 网络结构瓶颈</strong>（stride 太大导致格子不够，靠加 P2、改分配规则解决）。<em>面试时把方案挂到这三个瓶颈上讲，逻辑会非常清晰；只罗列方法名则显得零散。</em>"),
    ])),
    ("multicam", "多相机分工：广角、主摄与长焦，以及一个漂亮的不变量", "".join([
        P("既然单台相机的「作用距离」被 f·S/p<sub>min</sub> 死死卡住，量产方案的答案就是<strong>用多台不同 FOV 的相机分段覆盖</strong>。这是所有 L2+ 前视方案的标准配置。"),
        TABLE(["相机", "HFOV", "分辨率", "f（px）", "检出距离 p<sub>min</sub>=16", "细分类距离 p<sub>min</sub>=24", "职责"], [
            ["<strong>广角 wide</strong>", "120°", "1920×1080", "<strong>554</strong>", "20.8 m", "13.9 m", "路口大范围、切入车辆、<strong>近处大角度标志</strong>"],
            ["<strong>主摄 main</strong>", "60°", "1920×1080", "<strong>1663</strong>", "62.4 m", "41.6 m", "主力：中距离检测 + 分类"],
            ["<strong>长焦 tele</strong>", "30°", "1920×1080", "<strong>3583</strong>", "<strong>134.4 m</strong>", "89.6 m", "<strong>高速远距早发现</strong>、龙门架标志"],
            ["主摄 4K", "60°", "3840×2160", "3326", "124.7 m", "83.1 m", "长焦的替代方案（带宽/算力代价大）"],
        ]),
        H3("一个漂亮且实用的不变量"),
        P("把「最大作用距离」代回「该距离处的横向覆盖半宽」，会得到一个出人意料的结果。相机在距离 Z 处的横向可视半宽是 X = Z·tan(θ/2)，于是"),
        MATH("X_{\\max} \\;=\\; Z_{\\max}\\tan\\frac{\\theta}{2} \\;=\\; \\frac{f\\,S}{p_{\\min}}\\cdot\\frac{W}{2f} \\;=\\; \\boxed{\\;\\frac{W\\cdot S}{2\\,p_{\\min}}\\;}"),
        P("<strong>f 被完全约掉了。</strong>代入 W=1920、S=0.6、p<sub>min</sub>=16，三台相机<em>在各自最大作用距离处的横向覆盖半宽全都是 36.0 米</em>——广角 20.8 m 处、主摄 62.4 m 处、长焦 134.4 m 处，一个不差。"),
        ASCII("""三台相机的「能检出标志」的作用域（俯视图，半宽 36 m 是不变量）

        横向 ±36 m
    ┌───────────────┐
    │   wide 120°   │  0 ─ 20.8 m
    └───────────────┘
    ┌───────────────┐
    │   main  60°   │  0 ─ 62.4 m
    └───────────────┘
    ┌───────────────┐
    │   tele  30°   │  0 ─ 134.4 m
    └───────────────┘
    ●自车  ──────────────────────────────────────►  纵向距离

  X_max = W·S / (2·p_min)  与 FOV 无关！
  =>  **想同时看得更远 + 看得更宽，唯一的办法是增加像素数 W**
      （4K 主摄把不变量翻倍到 72 m，而换长焦只是把同一块 36 m 的
        覆盖区往远处平移，近处就交给广角）"""),
        DUAL(
            "这个不变量的实用价值在于：<strong>它把「多相机怎么选」从一场关于 FOV 的口水仗，变成了一个只有一个自由度的问题</strong>。FOV 决定的只是「这块 36 m 宽的覆盖区放在多远」，<em>而覆盖区本身的宽度只由传感器像素数与最小可检尺寸决定</em>。所以：<strong>要覆盖更远 → 加长焦（把区间往外挪）；要覆盖更宽 → 只能加像素（换 4K）；两个都要 → 多相机 + 更高分辨率，没有第三条路。</strong>",
            "严谨地说，这个推导假定「可检」的判据只是像素尺寸 p ≥ p<sub>min</sub>，忽略了三个二阶因素：<strong>① 大角度处标志的投影收缩</strong>（cos φ 因子，边缘处 p 实际更小）；<strong>② 镜头畸变与边缘 MTF 下降</strong>（广角尤其严重，边缘的有效分辨率远低于中心）；<strong>③ 长焦对振动与标定误差极其敏感</strong>——f 大 3 倍意味着同样的相机抖动在图像上的位移也大 3 倍，运动模糊与时序抖动都被放大。<em>所以工程上长焦的实际收益通常低于理论值，且必须配合更严格的减振与在线标定。</em>另外，多相机方案的真实成本不只是相机本身，还有<strong>跨相机的目标关联与去重</strong>（同一块牌子会被主摄和长焦同时看到，必须融合成一个航迹）以及标定维护，这部分工程量常被低估。",
        ),
        CALLOUT("intuition", "把不变量与前一节的「检出 62 m / 识别 42 m」合起来，就能推出一套<strong>可以直接讲给面试官的相机分工方案</strong>：<em>长焦负责 60–130 m 的「早发现」，输出「前方有标志、类别未定」，触发跟踪与地图查询；主摄负责 15–62 m 的「检出 + 分类」，是最终类别的主要来源；广角负责 &lt; 20 m 的近处与大角度（路口侧向牌、匝道口），并在主摄被遮挡时兜底。</em><strong>三段的交叠区用于跨相机关联的一致性校验——两台相机同时看到同一块牌且类别一致，置信度可以显著提升；不一致则触发数据回传（C58 的多相机分歧触发器）。</strong>"),
    ])),
    ("roi", "ROI 裁剪：消失点附近的那条窄带", "".join([
        P("模块 04 的结论是「非均匀分辨率是唯一可行的路」，但没说 ROI 该画在哪。<strong>这一节用几何精确地画出来。</strong>"),
        P("设标志中心相对相机光心的高度差为 ΔH（米），距离 Z（米）。它在图像上相对<strong>地平线</strong>（消失点所在的水平线，即主点行 c<sub>y</sub> 在平路上的位置）的垂直偏移为"),
        MATH("\\Delta v \\;=\\; f\\cdot\\frac{\\Delta H}{Z} \\qquad\\text{（像素，向上为正）}"),
        P("这与 p = f·S/Z 是同一个公式——<strong>距离越远，标志既越小、也越靠近地平线</strong>。两件事是同一个双曲线的两个投影。"),
        ASCII("""图像（1920×1080），相机装在 1.3 m 高，标志中心 1.6–4.3 m 高 => ΔH ∈ [0.3, 3.0] m

  y=0   ┌────────────────────────────────────────────┐
        │                天空                        │
        │      ┌──────────────────────────┐          │  Δv = f·ΔH/Z
  ──────┼──────│  远距标志 ROI 带          │──────────┼── 上界 Δv = 1663×3.0/40 = 125 px
        │      │  Z ∈ [40, 200] m         │          │
  地平线├──────┴──────────────────────────┴──────────┤ ← Δv = 0（消失点所在行）
        │           ↑ 俯仰余量 ±40 px               │
        │                                            │
        │            近处大标志 / 路面 / 车辆         │
  y=1080└────────────────────────────────────────────┘

  纵向：Δv ∈ [f·0.3/200, f·3.0/40] = [2.5, 124.7] px，加俯仰余量 -> 高 ≈ 205 px
  横向：|Δu| = f·|X|/Z <= 1663×8/40 = 332.6 px，加余量 -> 宽 ≈ 725 px
  ROI 面积 = 725×205 = 148,625 px  =  全图的 **7.2%**"""),
        TABLE(["距离 Z", "标志像素尺寸 p", "距地平线的偏移 Δv（ΔH=1.2 m）", "落在 ROI 带里吗"], [
            ["200 m", "5.0 px", "<strong>10 px</strong>", "✅（但已经太小，检不出）"],
            ["100 m", "10.0 px", "<strong>20 px</strong>", "✅"],
            ["<strong>60 m</strong>", "<strong>16.6 px</strong>", "<strong>33 px</strong>", "<strong>✅ 关键区间</strong>"],
            ["40 m", "24.9 px", "<strong>50 px</strong>", "✅"],
            ["20 m", "49.9 px", "100 px", "⚠️ 接近下边缘"],
            ["10 m", "99.8 px", "<strong>200 px</strong>", "❌ 已出 ROI —— 但它足够大，全图低分辨率那一路就能检到"],
        ]),
        DUAL(
            "<strong>ROI 带只需要负责「远且小」的目标，这正好和它的几何性质吻合</strong>：远目标既小、又必然靠近地平线；近目标虽然跑出了 ROI，但它大到全图下采样那一路轻松能检。<em>两路的分工是几何自动给出的，不需要额外的调度逻辑。</em>用模块 04 的中心凹公式算账：ROI 占 7.2% 面积、内部用 3× 分辨率（原生），总吞吐 = 0.928 + 0.072×9 = <strong>1.58×</strong>——<strong>用 1.58 倍算力买到了远距目标 3 倍的有效分辨率，而全图原生要 9 倍</strong>。",
            "严谨地说，ROI 的边界必须由<strong>三组参数的最坏组合</strong>决定，而不是典型值：① 标志高度 ΔH 的取值范围（路侧矮牌 0.3 m 到龙门架 4 m 以上）；② 要覆盖的距离区间 [Z<sub>min</sub>, Z<sub>max</sub>]；③ <strong>实时的俯仰角与地平线位置</strong>。第 ③ 项是唯一动态的，也是最危险的：相机俯仰变化 Δφ 会让整条带平移 f·tan(Δφ) ≈ f·Δφ 像素——<em>对 f=1663 的主摄，仅 1° 的俯仰变化就是 29 像素</em>，3° 就是 87 像素，足以把整条 205 px 的带推出去大半。上坡、下坡、急加速点头、重载后仰、过减速带，都会产生这个量级的变化。",
        ),
        CALLOUT("danger", "<p><strong>把 ROI 的垂直位置写成标定常数，是这一节唯一一个会导致真实安全事故的错误。</strong>症状极其典型：平路上一切正常，<em>某段长上坡的限速牌整段全漏</em>——不是偶尔漏一两块，是那段路必然全漏。因为俯仰变化是<strong>系统性的、与地点绑定的、可复现的</strong>，这是最糟糕的失效形态（比随机漏检危险得多，因为它在某些场景下把功能完全清零）。<strong>正确做法三条：① 地平线位置由实时估计给出</strong>（IMU 俯仰角、车道线灭点、或地面平面拟合），<strong>② ROI 上下各留 ±3° 换算成的像素余量</strong>（f=1663 时约 ±87 px），<strong>③ 永远保留一路无 ROI 的全图低分辨率兜底</strong>——ROI 是「在这里多花算力」，不是「只看这里」。</p>", "ROI 必须是软的、动态的"),
        CALLOUT("warn", "横向边界同样不能拍脑袋。上面用了 |X| ≤ 8 m，那是直路的假设。<strong>弯道上，40 m 外的道路中心可能已经横向偏出 10 米以上</strong>（半径 300 m 的弯道，40 m 弧长对应的横向偏移约 40²/(2×300) = 2.7 m；半径 100 m 时是 8 m）。<em>正确做法是用车道线/道路曲率把 ROI 沿道路走廊「掰弯」，而不是画一个固定的矩形</em>——这也是「ROI 应该由感知的其他模块驱动，而不是常数」的又一个理由。"),
    ])),
    ("plan", "把全课方法组合成方案：按收益 / 成本排序", "".join([
        P("到这里，C57 全课的方法都齐了。<strong>面试与真实工作里真正要交付的，不是一个方法列表，而是一份带优先级、带代价、带验证计划的方案。</strong>这一节把它排出来。"),
        TABLE(["方法", "解决哪个瓶颈", "ΔAP<sub>small</sub>（估）", "Δ延迟", "工程量", "风险"], [
            ["<strong>ROI 裁剪（消失点带）</strong>", "预处理", "<strong>+6.0</strong>", "<strong>−1.0 ms</strong>", "2 人周", "俯仰/弯道，需动态地平线"],
            ["<strong>用原生分辨率而非 letterbox 640</strong>", "预处理", "<strong>+8.0</strong>", "+6.0 ms", "1 人周", "延迟涨得多"],
            ["<strong>NWD 分配与损失</strong>（模块 03）", "分配/损失", "+2.5", "0", "2 人周", "大目标可能微降"],
            ["<strong>小目标 copy-paste 增强</strong>（C56 m03）", "数据", "+1.8", "0", "1 人周", "尺度/位置约束要写对"],
            ["<strong>多帧时序融合</strong>（C55 m04）", "时序", "+4.0", "+0.5 ms", "3 人周", "增加上报延迟"],
            ["<strong>增加 P2 层</strong>", "网络结构", "+3.5", "+2.2 ms", "2 人周", "NMS 候选 ×4，正负样本更失衡"],
            ["<strong>两级级联</strong>（模块 04）", "预处理 + 长尾", "+5.5", "+3.2 ms", "4 人周", "召回是乘法，L1 必须高召回"],
            ["<strong>长焦相机（30° FOV）</strong>", "<strong>光学</strong>", "<strong>+12.0</strong>", "+5.0 ms", "8 人周 + BOM", "硬件、标定、跨相机关联"],
            ["<strong>SAHI 切片推理</strong>（模块 04）", "预处理", "+9.0", "<strong>+32 ms</strong>", "1 人周", "<strong>车端装不下</strong>；离线可用"],
        ]),
        H3("排序方法：先取「免费的」，再做背包"),
        P("正确的排序不是按 ΔAP 降序（那会先做最贵的长焦），而是分两步："),
        OL([
            "<strong>先无条件采纳所有 Δ延迟 ≤ 0 且 ΔAP &gt; 0 的方法</strong>——它们是严格占优的（strictly dominant），不需要任何权衡。本表里是 ROI 裁剪（还倒赚 1 ms）、NWD、copy-paste，合计 <strong>+10.3 AP<sub>small</sub>，延迟 −1.0 ms</strong>。<em>这三项应该在任何方案的第一个 sprint 里做完。</em>",
            "<strong>剩下的按延迟预算做 0/1 背包</strong>，最大化总 ΔAP。以 8 ms 的 TSR 预算（模块 04 算过）为例，最优解是「长焦 + 两级级联 + 多帧融合」，共 8.7 ms，加上第一步倒赚的 1 ms，<strong>净 7.7 ms、总收益 +31.8 AP<sub>small</sub></strong>。而 SAHI 切片（+9.0）因为 32 ms 的代价，在任何合理预算下都进不了解集。",
        ]),
        DUAL(
            "<strong>「先取免费午餐，再做背包」这个两步法本身就是面试可以直接说的方法论</strong>，比逐条罗列方法高一个层次。它传达三件事：你知道每个方法的代价、你知道代价的度量单位是延迟预算而不是「感觉贵」、你知道优化问题的结构（有些选项是占优的，不需要权衡）。<em>而且它天然给出了迭代顺序：第一步的三项在两个 sprint 内就能出结果，长焦相机则要跨季度、要拉硬件团队——两者不该放在同一个计划里比较。</em>",
            "严谨地说，这张表里的 ΔAP 数字是<strong>估计值而非测量值</strong>，且它们<em>不可加</em>——这是必须主动说明的一点。三个理由：① 多个方法可能解决同一个瓶颈（ROI 裁剪与原生分辨率输入高度重叠，加起来远不到 +14）；② 有些方法互为前提（两级级联的收益依赖 L1 的召回，而 L1 的召回又依赖 ROI）；③ 收益随基线水平递减。<strong>所以正确的表述是「先按估计排序决定做的顺序，每做完一项重新测量并更新表」——这是一个在线的贪心过程，不是一次性的规划。</strong>这也正好接上下一节的分桶评测：<em>没有可靠的分尺度测量，这张表就无法更新，排序就退化成拍脑袋。</em>",
        ),
        CALLOUT("intuition", "注意表里最有意思的一行：<strong>ROI 裁剪的 Δ延迟是负的</strong>。它同时提高精度和降低延迟，因为它把算力从「处理 93% 无关像素」挪到了「处理 7% 关键像素」。<em>凡是「重新分配已有资源」而不是「增加资源」的改动，都有可能出现这种双赢</em>——而它们在方案里几乎总是被排在「加模型、加分辨率」之后，因为后者更像「在做事」。<strong>先找双赢项，是资源受限系统优化的通用起手式。</strong>"),
    ])),
    ("eval", "按像素尺寸分桶的评测：不分桶就看不见改进", "".join([
        P("上一节的所有排序都依赖一件事：<strong>你能可靠地测出每个改动对「小目标」的影响</strong>。而整体 mAP 做不到这件事。"),
        H3("为什么整体 mAP 会掩盖真相"),
        P("整体 AP 是所有目标混在一起算出来的一个数。它的问题不是「不准」，而是<strong>它把两个完全不同的方案压成了同一个数字</strong>："),
        TABLE(["", "整体 AP", "AP [0,16) px", "AP [16,32) px", "AP [32,64) px", "AP ≥64 px"], [
            ["baseline", "0.293", "<strong>0.005</strong>", "0.534", "0.926", "0.857"],
            ["<strong>方案 A</strong>（P2 + 原生分辨率）", "0.479", "<strong>0.206</strong> ⬆⬆", "0.831 ⬆", "0.842", "0.952"],
            ["<strong>方案 B</strong>（更大的 backbone）", "0.358", "0.047 ⬆", "0.655 ⬆", "<strong>1.000</strong> ⬆", "0.952"],
        ]),
        P("这张表（notebook 里会用物理合理的合成数据完整跑出来）藏了两个结论。<strong>第一：baseline 的整体 AP 是 0.293，看起来「一般般」；但拆开看，&lt;16 px 桶只有 0.005——60 米外的标志基本一个都检不到。</strong><em>一个「一般般」的整体分数，掩盖了某个关键子集上的彻底失效。</em>"),
        P("<strong>第二：A 与 B 的整体 AP 只差 0.12，但在 &lt;16 px 桶上差了 4.4 倍</strong>（0.206 vs 0.047），而在 [32,64) 桶上 B 反而更好（1.000 vs 0.842）。<em>&lt;16 px 桶对应的正是「60 米外能不能检出限速牌」——直接决定 ADAS 的反应时间；B 的提升则集中在已经很好的大目标上，对安全几乎没有贡献。</em><strong>只看整体 AP，你会觉得两者是同一量级的改进；分桶才知道该选 A。</strong>"),
        P("还有一个更严重、也更少被提及的问题：<strong>整体 mAP 跨数据集根本不可比</strong>。notebook 里会验证：同一个 baseline 模型，换一份尺寸分布不同的测试集（远处样本从 60% 降到 13%），<strong>整体 AP 从 0.293 跳到 0.601，而每个尺寸桶的 AP 几乎不变（差 &lt; 0.10）</strong>。<em>也就是说，报告「我们的模型 mAP 0.60」这句话在不给尺寸分布时几乎不含信息量；而分桶 AP 是模型能力的稳定刻画。</em>"),
        DUAL(
            "<strong>分桶评测在 TSR 里不是「更细致的分析」，而是「唯一有效的分析」</strong>。原因回到本模块第一节：标志的像素尺寸分布由 p = f·S/Z 决定，Z 在数据集里大致均匀 → <em>p 的分布密度正比于 1/p²，极度偏向小尺寸</em>。合成一份物理合理的分布会发现：60% 以上的标志实例都在 16 px 以下。<strong>而这些实例恰恰是 AP 最低、改进空间最大、也最影响安全的那一批。</strong>",
            "严谨地说，分桶评测要按 <strong>COCO 的忽略规则</strong>实现，否则会得到错误的数字。评某个尺寸桶 b 时：<em>① 只有落在桶 b 的 GT 计入召回分母；② 匹配到桶外 GT 的检测既不算 TP 也不算 FP，而是被<strong>忽略（ignore）</strong>；③ 匹配不到任何 GT 的检测才算 FP</em>。<strong>如果把「匹配到大目标的检测」当成小目标桶的 FP，小目标 AP 会被系统性低估，且低估幅度取决于大目标的数量</strong>——不同数据集之间就不可比了。这个实现细节在 notebook 里会完整写出来。另外，桶的边界应该按<em>业务含义</em>而不是 COCO 惯例来切：TSR 里更有意义的切法是按<strong>距离</strong>（&gt;80 m / 40–80 m / 15–40 m / &lt;15 m）或按<strong>p<sub>min</sub> 阈值</strong>（&lt;8 / 8–16 / 16–24 / ≥24，对应「不可能 / 可提议 / 可检测 / 可分类」四个语义区间）。",
        ),
        P("配套要报告的还有<strong>三个 mAP 之外的工程指标</strong>（C55 模块 05 会展开）："),
        UL([
            "<strong>首次检出距离的分布</strong>（p50 / p10）——直接对应「留给下游多少反应时间」，比 AP 更贴近产品体验。",
            "<strong>FP per km</strong> 而不是 precision——precision 依赖于测试集里正样本的密度，换个数据集就不可比；每公里误报数是绝对量，可以直接和产品要求对齐。",
            "<strong>按位置分桶</strong>（切片边界带 vs 中心区域、图像边缘 vs 中心）——模块 04 的重叠率下界所刻画的失效模式，只有按位置分桶才看得见。<em>几乎没有公开基准报告这一项。</em>",
        ]),
        CALLOUT("warn", "分桶评测有一个统计上的坑必须防：<strong>桶越小，样本越少，方差越大</strong>。&lt;16 px 桶如果只有 40 个实例，AP 的随机波动可能就有 ±0.05——此时「+0.03 的提升」毫无意义。<em>做法：① 报告每个桶的实例数；② 用 bootstrap 给出置信区间；③ 桶太小就合并或扩充测试集</em>。C61 模块 01 讲的「+0.3 可能是噪声」在分桶后会更严重，因为分母变小了。"),
    ])),
    ("ablation", "消融计划与上线门禁：把方案变成可执行的日程", "".join([
        P("最后一步，把上面的排序变成一份<strong>可以直接放进季度计划的消融与验证方案</strong>。这是面试里「系统设计题」的标准落点，也是真实工作的交付物。"),
        TABLE(["阶段", "改动", "预期收益", "验证方式", "门禁（不过就不合入）"], [
            ["<strong>S0 基线</strong>", "冻结代码/数据/评测集，跑 3 个种子", "—", "确定种子方差（典型 ±0.3 AP）", "三个种子的 AP 极差 &lt; 0.8，否则先修训练稳定性"],
            ["<strong>S1 免费午餐</strong>", "ROI 裁剪 + NWD + copy-paste", "+10 AP<sub>small</sub>，延迟 −1 ms", "分桶 AP + 延迟 p99", "<strong>大目标桶不掉超过 0.5</strong>；延迟不增"],
            ["<strong>S2 结构</strong>", "加 P2 层（含分配规则锚点下移）", "+3.5 AP<sub>small</sub>", "分桶 AP + NMS 耗时分布", "延迟 p99 增量 &lt; 2.5 ms；FP/km 不增"],
            ["<strong>S3 级联</strong>", "两级级联（L1 类别无关 + L2 高分辨率）", "+5.5 AP<sub>small</sub>", "<strong>级联召回拆解 R1 / R2</strong>", "<strong>R1 ≥ 0.95</strong>（否则 L2 再好也没用）"],
            ["<strong>S4 时序</strong>", "多帧融合 + 迟滞状态机", "+4.0，闪烁率下降", "首次检出距离 + 闪烁次数", "上报延迟增量 &lt; 150 ms"],
            ["<strong>S5 硬件</strong>", "长焦相机 + 跨相机关联", "+12.0", "分距离桶 AP（&gt;80 m 段）", "跨相机类别一致率 &gt; 0.98"],
        ]),
        DUAL(
            "<strong>这张表里最值得强调的是「门禁」那一列，而不是「预期收益」那一列。</strong>收益是猜的，门禁是硬的。每一条门禁都对应一个真实会发生的退化：加了 P2 会让 NMS 候选涨 4 倍从而推高 p99 延迟；改了分配偏向小目标会让大目标掉点；级联的 L2 再强也救不了 L1 的漏检；多帧融合会推迟上报。<em>把这些退化写成门禁，等于在开工前就承认了代价，也让每次合入有客观判据。</em>",
            "严谨地说，S3 的门禁「R1 ≥ 0.95」是整张表里最关键的一条，因为<strong>级联的召回是乘法</strong>（模块 04）：R = R1×R2。如果 L1 只有 0.80，那么无论 L2 做到多好，端到端召回上限就是 0.80——<em>而团队很容易把精力全花在 L2 上（因为它更像「模型工作」），却让整个系统被 L1 卡住</em>。<strong>所以级联系统必须把 R1 与 R2 分开测量、分开设门禁</strong>，绝不能只看端到端指标。度量方式：用 GT 框去检查「是否落在某个 L1 提议的 ROI 内（含 padding）」，这就是 R1；再在 L1 命中的子集上测 L2 的召回，这就是 R2。",
        ),
        P("<strong>还有三条容易被漏掉的验证纪律：</strong>"),
        OL([
            "<strong>同 budget 比较</strong>：加了 P2 的模型算力更大，与基线比时必须要么给基线同样的算力（比如加宽通道），要么明确标注「这是算力换精度」。<em>用一个更大的模型去打败小模型然后宣称「方法有效」，是消融里最常见的不诚实。</em>",
            "<strong>回归集必须覆盖失效模式</strong>：每个已知失效模式（夜间、逆光、雨天、上坡、弯道、切片边界）都要有一个几十到几百张的小集合，并单独设门禁。<em>整体指标涨了但某个失效模式集塌了，必须被拦住。</em>",
            "<strong>离线-在线一致性抽查</strong>：每个阶段结束时，用车端真实管线（含 ISP、量化、C++ 后处理）跑一遍同一批数据，与离线结果对拍。<em>C60 整门课在讲这件事；这里只强调它必须是每个阶段的固定动作，而不是上线前的一次性检查。</em>",
        ]),
        CALLOUT("intuition", "把整个 C57 压成一句可迁移的话：<strong>小目标检测的所有方案，本质上都是在回答「信息在哪一步被丢掉了，以及要花多少代价把它捡回来」</strong>。<em>光学（相机 f 与分辨率）决定了信息的上限；预处理（letterbox / ROI / 切片）决定了你有没有把已有信息交给模型；网络结构（stride / FPN 层）决定了模型有没有能力把信息读出来；分配与损失决定了训练时这些信息有没有被有效监督；评测分桶决定了你能不能看见自己的改进。</em><strong>把方案挂在这五个环节上讲，逻辑就永远是清晰的。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>「最小可检像素数」缺少理论刻画</strong>：本模块用的 p<sub>min</sub> ∈ {8,16,24} 全是经验值。它到底由什么决定——目标的形状复杂度？类别数？信噪比？是否存在类似 Johnson 判据（军用光电里的 detection/recognition/identification 线对数准则）的、可从任务复杂度推出的定量规则？<em>这是一个横跨信息论与视觉的开放问题，而它一旦解决，整套相机选型就能从经验变成计算。</em>",
            "<strong>跨相机的联合检测与融合</strong>：目前主流做法仍是「每台相机各跑一个检测器，再在 BEV 或跟踪层融合」。让多相机在<em>特征层</em>就联合推理（共享 backbone、跨视角注意力）在理论上能利用重叠视场的互补信息，但受制于标定误差、曝光差异、以及不同 FOV 之间的尺度鸿沟，<em>量产落地仍很少见</em>。",
            "<strong>可学习的分辨率分配</strong>：ROI 带目前由几何规则给出。让网络端到端地学习「每个区域该用多少分辨率」（延续 FOVEA / Learning-to-Zoom 的路线），在离线基准上有效，但<em>安全关键系统里如何验证「它不会在某类场景下把关键区域降采样」是未解的验证难题</em>。",
            "<strong>事件相机与高动态范围传感器</strong>：小目标在逆光、隧道出入口、夜间眩光下的失效，本质是传感器动态范围不足而非算法问题。event camera 与 HDR 多曝光融合能从根上改善，但<em>与现有检测器的数据表示不兼容</em>，且缺少大规模标注数据。",
            "<strong>物理感知的合成数据</strong>：用 p = f·S/Z 这套几何精确地合成「特定距离、特定光照、特定标志类别」的训练样本，理论上能定向补足长尾的远距小目标。难点是<strong>域差主要来自 ISP 与镜头而非几何</strong>——几何容易仿真，成像链路不容易。<em>「合成远距小目标能否替代真实采集」目前答案仍是否定的，但差距在缩小。</em>",
            "<strong>评测协议的空白</strong>：几乎所有公开基准都按像素面积分 small/medium/large，<em>没有一个按「距离」或按「p<sub>min</sub> 语义区间」分桶</em>，也没有报告首次检出距离分布与按位置分桶的结果。这使得学术方法的提升与产品体验的改善之间常常对不上号。<strong>推动一份「距离感知的 TSR 评测协议」是这个方向上性价比很高的贡献。</strong>",
        ]),
        CALLOUT("paper", "必读：<strong>Zhu et al., <em>Traffic-Sign Detection and Classification in the Wild</em> (CVPR 2016)</strong>——TT100K 数据集，中国交通标志、小目标与长尾的标准基准，务必看它的尺寸分布统计；<strong>Ertler et al., <em>The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale</em> (ECCV 2020)</strong>——全球尺度、区域差异；<strong>Thavamani et al., <em>FOVEA: Foveated Image Magnification for Autonomous Navigation</em> (ICCV 2021)</strong> 与 <strong>Recasens et al., <em>Learning to Zoom</em> (ECCV 2018)</strong>——非均匀分辨率分配；<strong>Akyon et al., <em>SAHI</em> (ICIP 2022)</strong>——切片推理（模块 04）；<strong>Wang et al., <em>NWD: A Normalized Gaussian Wasserstein Distance for Tiny Object Detection</em> (2021)</strong>——模块 03 的度量替换；<strong>Lin et al., <em>Feature Pyramid Networks</em> (CVPR 2017)</strong>——层级分配公式 k = k₀ + log₂(√(wh)/224) 的出处，本模块用它算出「交通标志该去 P0.25 层」；<strong>Hartley &amp; Zisserman, <em>Multiple View Geometry</em>, ch.6</strong>——针孔模型与内参标定的权威出处；<strong>COCO detection evaluation 协议</strong>的官方实现（<code>cocoeval.py</code> 里 <code>areaRng</code> 与 ignore 规则的处理，是本模块分桶评测的参考实现）。相邻课程：C55（TSR 领域知识与安全导向评测）、C56（增强）、C58（长尾数据闭环）、C60（车端部署一致性）、C61（实验设计与误差分析）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · TSR 小目标实战：从物理量到工程方案（针孔模型 / 反推配置 / ROI / 分桶评测）

目标：把「远距离交通标志检不出」这个感觉问题，变成一条**可以当场算出来的推导链**：

    相机参数 (W, HFOV)  ->  f = (W/2)/tan(θ/2)
    物理尺寸 S、距离 Z  ->  **p = f·S/Z**（标志有多少像素）
    最小可检像素 p_min  ->  Z_max = f·S/p_min（能看多远）
    反解                ->  要看到 Z_target，需要多少焦距 / 多宽的传感器 / 多窄的 FOV
    stride              ->  p/stride（特征图上够不够格子）
    几何                ->  Δv = f·ΔH/Z（标志在图像里的垂直位置 -> ROI 带）
    组合                ->  按收益/延迟排序 + 背包求解
    评测                ->  **按像素尺寸分桶**，否则改进不可见

本 notebook 你会亲手实现：
1. **像素尺寸计算器**（含 4 组真实相机参数：广角 120° / 主摄 60° / 主摄 4K / 长焦 30°）
2. **检出距离 vs 识别距离**的双阈值分析，以及它对系统设计的硬性要求
3. **反推求解器**：给定检出距离目标，反解所需焦距 / 分辨率 / FOV
4. **stride 与 FPN 层级**的账（含 `k = k₀ + log₂(√(wh)/224)` 的验算）
5. **横向覆盖不变量** `X_max = W·S/(2·p_min)`（f 会被约掉，这个结论很反直觉）
6. **消失点 ROI 带**的几何推导与算力账，以及俯仰角敏感性
7. **方案组合的收益-成本排序**（免费午餐优先 + 0/1 背包）
8. **按像素尺寸分桶的 AP**（含 COCO 的 ignore 规则），证明整体 mAP 会掩盖什么

> 心智模型：**小目标检测的每一个方案，都是在回答「信息在哪一步丢掉了、
> 花多少代价能捡回来」。而第一步永远是：算出目标到底有多少像素。**"""),
    md("""## 1 · 针孔模型：p = f·S/Z

`f = (W/2)/tan(θ/2)` 把「分辨率 + 视场角」换算成像素焦距；
`p = f·S/Z` 把「物理尺寸 + 距离」换算成像素尺寸。两个公式，整节课的地基。"""),
    code("""import numpy as np, math
from collections import Counter
np.set_printoptions(precision=3, suppress=True)

def focal_px(width_px, hfov_deg):
    '''把「分辨率 + 水平视场角」换算成像素焦距。'''
    return (width_px / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

def obj_px(f, S, Z):
    '''针孔模型：物理尺寸 S（米）在距离 Z（米）处的像素尺寸。'''
    return f * S / Z

def max_range(f, S, p_min):
    '''最小可检像素数 p_min 对应的最大作用距离。'''
    return f * S / p_min

S_SIGN = 0.6      # 中国 GB 5768 城区常见圆形禁令标志直径 60 cm
CAMERAS = {
    'wide  120° 1920': (1920, 1080, 120.0),
    'main   60° 1920': (1920, 1080,  60.0),
    'main   60° 3840': (3840, 2160,  60.0),
    'tele   30° 1920': (1920, 1080,  30.0),
}
print(f"{'相机':<18s} {'W':>6s} {'HFOV':>7s} {'f (px)':>10s} {'p @60m':>9s}")
FOCALS = {}
for name, (w, h, fov) in CAMERAS.items():
    f = focal_px(w, fov)
    FOCALS[name] = f
    print(f'{name:<18s} {w:>6d} {fov:>6.0f}° {f:>10.2f} {obj_px(f, S_SIGN, 60.0):>9.2f}')

F_MAIN = FOCALS['main   60° 1920']
assert abs(F_MAIN - 1662.77) < 0.01, F_MAIN          # 960/tan30° = 960·√3
assert abs(F_MAIN - 960 * math.sqrt(3)) < 1e-6       # 精确闭式：60° FOV 时 f = (W/2)·√3
print(f'\\n主摄 f = 960/tan(30°) = 960·√3 = {F_MAIN:.2f} px')"""),
    code("""# ---- 60 cm 标志在主摄上随距离的像素尺寸 ----
print(f"{'Z (m)':>7s} {'p (px)':>9s} {'面积 (px²)':>12s} {'COCO 尺度':>11s} {'letterbox 640 后':>17s}")
for Z in [10, 15, 20, 30, 40, 60, 80, 100, 150]:
    p = obj_px(F_MAIN, S_SIGN, Z)
    scale = 'small' if p * p < 32 ** 2 else ('medium' if p * p < 96 ** 2 else 'large')
    print(f'{Z:>7d} {p:>9.2f} {p*p:>12.0f} {scale:>11s} {p*640/1920:>17.2f}')

p30, p60, p100 = [obj_px(F_MAIN, S_SIGN, z) for z in (30.0, 60.0, 100.0)]
assert abs(p30 - 33.26) < 0.02 and abs(p60 - 16.63) < 0.02 and abs(p100 - 9.98) < 0.02
print(f'\\n**关键数字**：30 m -> {p30:.1f} px，60 m -> {p60:.1f} px，100 m -> {p100:.1f} px')
print(f'   而 letterbox 到 640 宽之后，60 m 的标志只剩 {p60*640/1920:.2f} px  ->  '
      f'在 stride 8 的 P3 上只有 {p60*640/1920/8:.2f} 个格子')
print('\\n✅ 「TSR 是小目标问题」不是修辞，是 p = f·S/Z 这个双曲线关系的必然结果：')
print('   像素尺寸随距离**反比**衰减 —— 想早一倍距离看到，就要多一倍的焦距或分辨率')"""),
    code("""# ---- 检出距离 vs 识别距离：一个必须知道的 20 米间隙 ----
TASKS = [('类别无关提议（有没有牌子）', 9.0), ('检测（框 + 粗类）', 16.0),
         ('细分类（限速 40 还是 60）', 24.0), ('恶劣光照下可靠细分类', 40.0)]
print(f"{'任务':<26s} {'p_min':>6s} {'main 60°':>10s} {'tele 30°':>10s} {'wide 120°':>10s}")
for task, pm in TASKS:
    row = ''.join(f'{max_range(FOCALS[c], S_SIGN, pm):>10.1f}'
                  for c in ['main   60° 1920', 'tele   30° 1920', 'wide  120° 1920'])
    print(f'{task:<26s} {pm:>6.0f}{row}')

Z_DET = max_range(F_MAIN, S_SIGN, 16.0)
Z_CLS = max_range(F_MAIN, S_SIGN, 24.0)
V = 100 / 3.6                                          # 100 km/h
print(f'\\n主摄：检出距离 {Z_DET:.1f} m，细分类距离 {Z_CLS:.1f} m')
print(f'  -> 存在一段 {Z_DET-Z_CLS:.1f} m = {(Z_DET-Z_CLS)/V:.2f} s 的')
print(f'     「知道前面有牌子、但还不知道写什么」的时间窗')
assert Z_DET > Z_CLS and Z_DET - Z_CLS > 15
print('  ✅ 这直接要求 TSR 必须是两级的、必须有跟踪、')
print('     必须能表达「已检出但类别未定」这个中间状态（C59 m03 的 schema 设计）')

# ---- 制动与降速的距离需求：为什么必须上长焦 ----
d_emerg = V ** 2 / (2 * 6.0) + V * 1.0                 # 6 m/s² 急刹 + 1 s 反应
v2 = 60 / 3.6
t_comf = (V - v2) / 1.5                                # 1.5 m/s² 舒适减速 100 -> 60 km/h
d_comf = (V + v2) / 2 * t_comf
print(f'\\n100 km/h 下的距离需求：')
print(f'  急刹停住（6 m/s² + 1 s 反应）需要 {d_emerg:.0f} m   -> 主摄 {Z_DET:.0f} m **不够**，'
      f'长焦 {max_range(FOCALS["tele   30° 1920"], S_SIGN, 16.0):.0f} m 够')
print(f'  舒适降到 60 km/h（1.5 m/s²）需要 {d_comf:.0f} m  -> **连长焦也不够**')
assert d_emerg > Z_DET and d_comf > max_range(FOCALS['tele   30° 1920'], S_SIGN, 16.0)
print('  ✅ 结论：大幅限速变化的舒适执行**不可能只靠视觉 TSR**，必须有导航/地图先验；')
print('     TSR 的职责是**确认与推翻**地图，而不是从零发现（C55 m04 的先验融合）')"""),
    md("""## 2 · 反推：要在多远检出，需要什么相机

把 `Z_max = f·S/p_min` 倒过来解 f、W、θ。
**注意区分「网络输入分辨率」与「相机分辨率」——前者只能把已有像素用满，后者才决定天花板。**"""),
    code("""def required_focal(S, Z_target, p_min):
    '''要在 Z_target 处让物体有 p_min 像素，需要多少像素焦距。'''
    return p_min * Z_target / S

def required_width(hfov_deg, f):
    '''保持给定 FOV 时，该焦距对应的传感器宽度（像素）。'''
    return 2.0 * f * math.tan(math.radians(hfov_deg) / 2.0)

def required_hfov(width_px, f):
    '''保持给定宽度时，该焦距对应的水平视场角（度）。'''
    return 2.0 * math.degrees(math.atan((width_px / 2.0) / f))

f_req = required_focal(S_SIGN, 100.0, 16.0)
w_req = required_width(60.0, f_req)
h_req = required_hfov(1920, f_req)
print('需求：**在 100 m 外检出 60 cm 标志（p_min = 16 px）**')
print(f'  现有主摄 f = {F_MAIN:.1f} px  ->  100 m 处只有 {obj_px(F_MAIN,S_SIGN,100):.2f} px  ❌')
print(f'  需要 f = 16 × 100 / 0.6 = {f_req:.1f} px   （是现有的 {f_req/F_MAIN:.2f} 倍）')
print(f'  ① 保持 60° FOV -> 传感器要 {w_req:.0f} px 宽  ->  **要上 4K（3840）**')
print(f'  ② 保持 1920 宽 -> FOV 要收到 {h_req:.2f}°   ->  **要加一路长焦**')
assert abs(f_req - 2666.667) < 0.01
assert abs(w_req - 3079.2) < 0.5
assert abs(h_req - 39.60) < 0.05

print(f"\\n{'检出距离目标':>12s} {'需要 f (px)':>12s} {'60°FOV 需要的宽度':>18s} {'1920 宽需要的 FOV':>18s}")
for Zt in [40, 60, 80, 100, 130, 160]:
    fr = required_focal(S_SIGN, float(Zt), 16.0)
    print(f'{Zt:>11d}m {fr:>12.0f} {required_width(60.0, fr):>18.0f} {required_hfov(1920, fr):>17.2f}°')

print('\\n⚠️  **陷阱**：把网络输入从 640 调到 1280，只能把 letterbox 丢掉的像素捡回来')
print(f'    （60 m 的标志从 {obj_px(F_MAIN,S_SIGN,60)*640/1920:.2f} px 恢复到 {obj_px(F_MAIN,S_SIGN,60):.2f} px，'
      f'这是真实且巨大的收益），')
print('    但它的**上限就是相机给的那个数**，永远到不了 100 m 所需的尺寸。')
print('✅ 「网络输入分辨率」把已有像素用满；「相机分辨率 × 焦距」决定像素的天花板。')"""),
    md("""## 3 · stride 与 FPN 层级：像素够了，格子还得够

`n_cells = p_input / stride`。n_cells < 1 = 目标连一个完整格子都占不满，
标签分配拿不到正样本；n_cells ≈ 2 勉强可用；n_cells ≥ 4 才稳定。"""),
    code("""def n_cells(p_input, stride):
    return p_input / stride

STRIDES = [('P2', 4), ('P3', 8), ('P4', 16), ('P5', 32)]
p_native = obj_px(F_MAIN, S_SIGN, 60.0)
p_letter = p_native * 640 / 1920
p_near = obj_px(F_MAIN, S_SIGN, 30.0)

print(f'60 m 标志：原生 {p_native:.2f} px，letterbox 640 后 {p_letter:.2f} px；30 m 标志原生 {p_near:.2f} px')
print(f"\\n{'层':>4s} {'stride':>7s} {'16.6px @letterbox640':>21s} {'16.6px @原生':>14s} {'33.3px @原生':>14s}")
def mark(v):
    return f'{v:.2f} ' + ('✅' if v >= 4 else ('⚠️' if v >= 2 else '❌'))
for lname, st in STRIDES:
    print(f'{lname:>4s} {st:>7d} {mark(n_cells(p_letter, st)):>22s} '
          f'{mark(n_cells(p_native, st)):>15s} {mark(n_cells(p_near, st)):>15s}')
assert n_cells(p_letter, 8) < 1.0, 'letterbox 后 16.6px 标志在 P3 上连一格都占不满'
assert n_cells(p_native, 4) > 4.0, '原生分辨率 + P2 才谈得上稳定'

# ---- 用 FPN 的标准层级分配规则验算 ----
def fpn_level(p, k0=4, canonical=224.0):
    '''Lin et al. FPN: k = k0 + log2(sqrt(w·h)/224)。'''
    return k0 + math.log2(p / canonical)

print(f"\\n{'标志尺寸':>10s} {'FPN 规则给出的层 k':>20s}")
for p in [p_native, p_near, 66.5, 224.0]:
    print(f'{p:>9.1f}px {fpn_level(p):>20.2f}')
k_far = fpn_level(p_native)
assert k_far < 1.0, k_far
print(f'\\n⚠️  按 FPN 原始规则，60 m 外的标志应该去「P{k_far:.2f} 层」—— **比 P2 还浅两层**，')
print('    而 P2 已经是绝大多数实现的最浅层。根因：FPN 以 224 px 的 ImageNet 尺度为锚点，')
print('    而交通标志系统性地比它小一个数量级。')
print(f'✅ 改进：把锚点从 224 下移到 64 -> 60 m 标志的层变成 '
      f'{fpn_level(p_native, canonical=64.0):.2f}（落在 P2 附近，合理）')
print('   这是一个只改几行配置、却常常带来 2–4 AP_small 的改动')

# ---- 加 P2 的代价 ----
print(f"\\n{'配置':<16s} {'特征点总数(640×640)':>20s} {'相对头部 FLOPs':>16s}")
for cfg, sts in [('P3–P5', [8,16,32]), ('P2–P5', [4,8,16,32]), ('P2–P4', [4,8,16])]:
    npt = sum((640 // s) ** 2 for s in sts)
    print(f'{cfg:<16s} {npt:>20d} {npt/8400:>15.2f}×')
assert sum((640//s)**2 for s in [4,8,16,32]) / 8400 > 3.9
print('\\n⚠️  加 P2 的连带成本：NMS 候选数 ×4（延迟与方差都涨）、正负样本比进一步恶化')"""),
    md("""## 4 · 多相机分工与一个漂亮的不变量

`X_max = Z_max·tan(θ/2) = (f·S/p_min)·(W/2f) = **W·S/(2·p_min)**` —— **f 被约掉了**。"""),
    code("""P_DET, P_CLS = 16.0, 24.0
print(f"{'相机':<18s} {'f (px)':>9s} {'检出 Z(m)':>10s} {'分类 Z(m)':>10s} {'@Zmax 横向半宽(m)':>18s}")
for name, (w, h, fov) in CAMERAS.items():
    f = FOCALS[name]
    zd, zc = max_range(f, S_SIGN, P_DET), max_range(f, S_SIGN, P_CLS)
    x = zd * math.tan(math.radians(fov) / 2.0)
    print(f'{name:<18s} {f:>9.1f} {zd:>10.1f} {zc:>10.1f} {x:>18.2f}')

# ---- 验证不变量：X_max = W·S/(2·p_min)，与 FOV 无关 ----
print('\\n验证不变量  X_max = W·S/(2·p_min):')
for name, (w, h, fov) in CAMERAS.items():
    f = FOCALS[name]
    lhs = max_range(f, S_SIGN, P_DET) * math.tan(math.radians(fov) / 2.0)
    rhs = w * S_SIGN / (2 * P_DET)
    print(f'  {name:<18s} 几何算得 {lhs:>7.3f} m   闭式 W·S/(2p) = {rhs:>7.3f} m')
    assert abs(lhs - rhs) < 1e-6, name
print('\\n✅ **三台 1920 宽的相机，在各自最大作用距离处的横向半宽都是 36.00 m —— 一个不差。**')
print('   f 被完全约掉了：FOV 决定的只是「这块 36 m 宽的覆盖区放在多远」，')
print('   而覆盖区的**宽度只由传感器像素数 W 与 p_min 决定**。')
print(f'   4K 主摄把不变量翻倍到 {3840*S_SIGN/(2*P_DET):.1f} m —— **想同时看得更远又更宽，只能加像素**')

print('\\n可以直接讲给面试官的分工方案:')
print('  长焦 30°  : 60–134 m  「早发现」-> 输出「前方有标志、类别未定」，触发跟踪与地图查询')
print('  主摄 60°  : 15–62 m   「检出 + 分类」-> 最终类别的主要来源')
print('  广角 120° : < 21 m    近处与大角度（路口侧向牌、匝道），主摄被遮挡时兜底')
print('  交叠区    : 跨相机类别一致性校验；不一致 -> 触发数据回传（C58 的多相机分歧触发器）')"""),
    md("""## 5 · ROI 裁剪：消失点附近的那条窄带

`Δv = f·ΔH/Z` —— 与 `p = f·S/Z` 是同一个公式：
**距离越远，标志既越小、也越靠近地平线**。两件事是同一条双曲线的两个投影。"""),
    code("""def horizon_offset(f, dH, Z):
    '''标志中心相对地平线（消失点所在行）的垂直像素偏移，向上为正。'''
    return f * dH / Z

IMG_W, IMG_H = 1920, 1080
print(f"{'Z (m)':>7s} {'p (px)':>8s} {'Δv (ΔH=1.2m)':>14s} {'Δv (ΔH=0.3m)':>14s} {'Δv (ΔH=3.0m)':>14s}")
for Z in [200, 150, 100, 60, 40, 20, 10]:
    print(f'{Z:>7d} {obj_px(F_MAIN,S_SIGN,Z):>8.1f} '
          f'{horizon_offset(F_MAIN,1.2,Z):>14.1f} {horizon_offset(F_MAIN,0.3,Z):>14.1f} '
          f'{horizon_offset(F_MAIN,3.0,Z):>14.1f}')

# ---- ROI 带：由「最坏组合」决定，不是典型值 ----
DH_LO, DH_HI = 0.3, 3.0        # 路侧矮牌 ~ 龙门架
Z_LO, Z_HI = 40.0, 200.0       # ROI 带只负责「远且小」的目标
LAT_M = 8.0                    # 横向走廊半宽（直路假设）
PITCH_DEG = 1.4                # 俯仰余量

dv_lo = horizon_offset(F_MAIN, DH_LO, Z_HI)      # 最小偏移（最远 + 最矮）
dv_hi = horizon_offset(F_MAIN, DH_HI, Z_LO)      # 最大偏移（最近 + 最高）
marg_v = F_MAIN * math.tan(math.radians(PITCH_DEG))
top, bot = dv_hi + marg_v, dv_lo - marg_v
roi_h = top - bot
du = horizon_offset(F_MAIN, LAT_M, Z_LO)         # 同一个公式，换成横向
roi_w = 2 * du + 60.0
ratio = roi_h * roi_w / (IMG_W * IMG_H)

print(f'\\n纵向: Δv ∈ [{dv_lo:.1f}, {dv_hi:.1f}] px，俯仰余量 ±{marg_v:.1f} px（±{PITCH_DEG}°）'
      f'  ->  带高 {roi_h:.0f} px')
print(f'横向: |Δu| <= f·{LAT_M:.0f}/{Z_LO:.0f} = {du:.1f} px，加余量  ->  带宽 {roi_w:.0f} px')
print(f'ROI 面积 = {roi_w:.0f}×{roi_h:.0f} = {roi_w*roi_h:,.0f} px = 全图的 **{ratio:.1%}**')
assert 0.05 < ratio < 0.10, ratio

# 中心凹（foveated）吞吐账：ROI 内用原生分辨率（3×），ROI 外仍跑全图下采样
BETA = 3.0
fov_cost = (1 - ratio) * 1.0 + ratio * BETA ** 2
print(f'\\n中心凹吞吐 = (1-{ratio:.3f})·1 + {ratio:.3f}·{BETA:.0f}² = **{fov_cost:.2f}×** 全图下采样')
print(f'  而全图原生分辨率要 {BETA**2:.0f}× —— **用 {fov_cost:.2f} 倍算力买到远距目标 3 倍的有效分辨率**')
assert fov_cost < 2.0
print('✅ 近处大标志跑出 ROI 也没关系 —— 它大到全图下采样那一路轻松能检。分工是几何自动给的。')"""),
    code("""# ---- 俯仰角敏感性：为什么 ROI 的垂直位置**绝不能**写成标定常数 ----
print(f"{'俯仰变化':>9s} {'整条带平移 (px)':>17s} {'占 ROI 带高的比例':>19s}")
for dphi in [0.5, 1.0, 2.0, 3.0, 5.0]:
    shift = F_MAIN * math.tan(math.radians(dphi))
    print(f'{dphi:>8.1f}° {shift:>17.1f} {shift/roi_h:>18.0%}')
s3 = F_MAIN * math.tan(math.radians(3.0))
assert s3 > roi_h * 0.4, '3° 俯仰变化就能把整条带推走近一半'
print(f'\\n⚠️  f = {F_MAIN:.0f} 时，**仅 1° 俯仰变化就是 {F_MAIN*math.tan(math.radians(1)):.0f} 像素**，'
      f'3° 是 {s3:.0f} 像素。')
print('    上坡、下坡、急加速点头、重载后仰、过减速带，都会产生这个量级的变化。')
print('    症状：平路一切正常，**某段长上坡的限速牌整段全漏** —— 系统性、可复现、最糟糕的失效形态。')

# ---- 弯道对横向边界的影响 ----
print(f"\\n{'弯道半径 R (m)':>15s} {'40 m 处的横向偏移 (m)':>22s} {'像素偏移':>10s}")
for R in [1000, 500, 300, 150, 100]:
    lat = 40.0 ** 2 / (2 * R)
    print(f'{R:>15d} {lat:>22.2f} {horizon_offset(F_MAIN, lat, 40.0):>10.0f}')
lat100 = 40.0 ** 2 / (2 * 100)
assert lat100 > LAT_M * 0.9, '半径 100 m 的弯道，40 m 处的横向偏移已经逼近走廊半宽'
print('\\n✅ 三条纪律：① 地平线用**实时估计**（IMU 俯仰 / 车道线灭点 / 地面拟合），不用标定常数；')
print('           ② 上下各留 ±3° 换算的像素余量；')
print('           ③ **永远保留一路无 ROI 的全图低分辨率兜底** —— ROI 是「多花算力」，不是「只看这里」')"""),
    md("""## 6 · 把全课方法组合成方案：按收益 / 成本排序

两步法：**① 先无条件采纳所有 Δ延迟 ≤ 0 且 ΔAP > 0 的方法（严格占优，不需要权衡）；
② 剩下的按延迟预算做 0/1 背包。**"""),
    code("""# (名称, ΔAP_small 估计, Δ延迟 ms, 工程量 人周, 解决的瓶颈)
METHODS = [
    ('ROI 裁剪(消失点带)',   6.0, -1.0, 2, '预处理'),
    ('原生分辨率输入',       8.0,  6.0, 1, '预处理'),
    ('NWD 分配与损失',       2.5,  0.0, 2, '分配/损失'),
    ('小目标 copy-paste',    1.8,  0.0, 1, '数据'),
    ('多帧时序融合',         4.0,  0.5, 3, '时序'),
    ('增加 P2 层',           3.5,  2.2, 2, '网络结构'),
    ('两级级联',             5.5,  3.2, 4, '预处理/长尾'),
    ('长焦相机(30° FOV)',   12.0,  5.0, 8, '**光学**'),
    ('SAHI 切片推理',        9.0, 32.0, 1, '预处理'),
]
BUDGET_MS = 8.0        # 模块 04 算过：TSR 在 33.3 ms 整帧预算里能分到 5–10 ms

def ratio_of(gain, lat):
    return float('inf') if lat <= 0 else gain / lat

print(f"{'方法':<22s} {'ΔAP_s':>7s} {'Δms':>7s} {'人周':>5s} {'收益/ms':>9s} {'瓶颈':<12s}")
for n, g, l, w, b in sorted(METHODS, key=lambda x: -ratio_of(x[1], x[2])):
    r = ratio_of(g, l)
    print(f'{n:<22s} {g:>7.1f} {l:>7.1f} {w:>5d} '
          f'{("  ∞（占优）" if r == float("inf") else f"{r:>9.2f}"):>9s} {b:<12s}')
print('\\n⚠️  注意 ROI 裁剪的 Δ延迟是**负的** —— 它同时提高精度并降低延迟，')
print('    因为它把算力从「处理 93% 无关像素」挪到了「处理 7% 关键像素」。')
print('✅ 凡是「重新分配已有资源」而非「增加资源」的改动，都可能双赢 —— **先找双赢项**')"""),
    code("""def pick_plan(methods, budget_ms):
    '''① 先无条件取所有 Δlat <= 0 且 ΔAP > 0 的（严格占优）
       ② 剩下的在剩余预算里做 0/1 背包（延迟按 0.1 ms 离散化）'''
    free = [m for m in methods if m[2] <= 0 and m[1] > 0]
    rest = [m for m in methods if not (m[2] <= 0 and m[1] > 0)]
    used = sum(m[2] for m in free)
    cap = int(round((budget_ms - used) * 10))
    if cap < 0:
        return [n for n, *_ in free], sum(m[1] for m in free), used
    dp = [0.0] * (cap + 1)
    pick = [[] for _ in range(cap + 1)]
    for name, g, l, *_ in rest:
        w = int(round(l * 10))
        if w > cap:
            continue
        for c in range(cap, w - 1, -1):
            if dp[c - w] + g > dp[c] + 1e-12:
                dp[c] = dp[c - w] + g
                pick[c] = pick[c - w] + [name]
    best = int(np.argmax(dp))
    chosen = [n for n, *_ in free] + pick[best]
    look = {m[0]: m for m in methods}
    return chosen, sum(look[n][1] for n in chosen), sum(look[n][2] for n in chosen)

for b in [4.0, 8.0, 40.0]:
    ch, gain, lat = pick_plan(METHODS, b)
    print(f'预算 {b:>5.1f} ms -> 总收益 {gain:>5.1f} AP_small，用掉 {lat:>5.1f} ms')
    for n in ch:
        print(f'      · {n}')
    print()

ch8, g8, l8 = pick_plan(METHODS, 8.0)
assert abs(g8 - 31.8) < 1e-6 and abs(l8 - 7.7) < 1e-6, (g8, l8)
assert '长焦相机(30° FOV)' in ch8 and '两级级联' in ch8 and 'ROI 裁剪(消失点带)' in ch8
assert 'SAHI 切片推理' not in ch8, '32 ms 的代价让切片在任何合理预算下都进不了解集'
print('✅ 8 ms 预算下的最优解：免费三件套（ROI + NWD + copy-paste，倒赚 1 ms）')
print('   + 长焦 + 两级级联 + 多帧融合，净 7.7 ms、+31.8 AP_small')
print('\\n⚠️  这些 ΔAP 是**估计值且不可加**：方法之间会重叠（ROI 与原生分辨率）、')
print('    互为前提（级联依赖 L1 召回、L1 依赖 ROI）、收益随基线递减。')
print('    正确做法是「按估计排序决定顺序，每做完一项重新测量并更新表」—— 在线贪心，不是一次性规划。')"""),
    md("""## 7 · 按像素尺寸分桶的评测

按 **COCO 的 ignore 规则**实现：评桶 b 时，
① 只有落在桶 b 的 GT 计入召回分母；
② 匹配到**桶外 GT** 的检测既不算 TP 也不算 FP，而是被**忽略**；
③ 匹配不到任何 GT 的检测才算 FP。

漏了 ② 会系统性低估小目标 AP，且低估幅度取决于大目标数量 —— 数据集之间就不可比了。"""),
    code("""def gen_gt(n_img=400, seed=1, S=0.6, z_lo=8.0, z_hi=150.0, f=None):
    '''按物理模型合成评测集：Z 均匀采样 -> p = f·S/Z -> **p 的密度正比于 1/p²**，极度偏小。'''
    f = F_MAIN if f is None else f
    g = np.random.default_rng(seed)
    out = []
    for im in range(n_img):
        for _ in range(int(g.integers(1, 4))):
            Z = g.uniform(z_lo, z_hi)
            s = g.normal(S, 0.04)                     # 标志实际尺寸有个体差异
            p = f * s / Z
            cx, cy = g.uniform(200, 1700), g.uniform(300, 600)
            out.append({'img': im, 'box': (cx-p/2, cy-p/2, cx+p/2, cy+p/2),
                        'size': float(p), 'Z': float(Z)})
    return out

def simulate_detector(gts, n_img=400, p50=20.0, k=0.35, ceil=0.88, fp=0.8,
                      loc=0.05, seed=99, z_lo=8.0, z_hi=150.0):
    '''检出概率 = ceil · sigmoid(k(p-p50))；p50 控制「多小还能检到」，ceil 控制整体上限。'''
    g = np.random.default_rng(seed)
    dets = []
    for gt in gts:
        pr = ceil / (1 + math.exp(-k * (gt['size'] - p50)))
        if g.random() < pr:
            sg = max(0.4, loc * gt['size'])
            dets.append({'img': gt['img'],
                         'box': tuple(np.array(gt['box']) + g.normal(0, sg, 4)),
                         'score': float(np.clip(0.40 + 0.5*pr + g.normal(0, 0.05), 0.01, 0.99))})
    for im in range(n_img):                            # 背景误检
        for _ in range(int(g.poisson(fp))):
            p = F_MAIN * 0.6 / g.uniform(z_lo, z_hi)
            cx, cy = g.uniform(200, 1700), g.uniform(300, 600)
            dets.append({'img': im, 'box': (cx-p/2, cy-p/2, cx+p/2, cy+p/2),
                         'score': float(g.uniform(0.05, 0.60))})
    return dets

BUCKETS = [('[0,16)', 0, 16), ('[16,32)', 16, 32), ('[32,64)', 32, 64),
           ('[64,inf)', 64, 1e9), ('all', 0, 1e9)]
GTS = gen_gt()
cc = Counter(b for g_ in GTS for b, lo, hi in BUCKETS if lo <= g_['size'] < hi)
print('TSR 实车分布 Z~U(8,150) 的尺寸分布:')
for b, lo, hi in BUCKETS:
    print(f'  {b:<10s} {cc[b]:>5d} 实例  ({cc[b]/cc["all"]:>5.1%})')
assert cc['[0,16)'] / cc['all'] > 0.55
print(f'\\n✅ **{cc["[0,16)"]/cc["all"]:.0%} 的标志实例在 16 px 以下** —— 这不是数据集偏差，')
print('   是 p = f·S/Z 的必然结果：Z 均匀 -> p 的密度正比于 1/p²')"""),
    code("""def iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1-ix0) * max(0.0, iy1-iy0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / u if u > 0 else 0.0

def ap_in_bucket(gts, dets, lo, hi, iou_thr=0.5):
    '''COCO 风格的分尺寸 AP：桶外 GT 被匹配上的检测 -> **ignore**（既不是 TP 也不是 FP）。'''
    gin, gout = {}, {}
    for g_ in gts:
        (gin if lo <= g_['size'] < hi else gout).setdefault(g_['img'], []).append(g_['box'])
    npos = sum(len(v) for v in gin.values())
    if npos == 0:
        return float('nan'), 0
    ui = {k: [False]*len(v) for k, v in gin.items()}
    uo = {k: [False]*len(v) for k, v in gout.items()}
    tp, fp = [], []
    for d in sorted(dets, key=lambda x: -x['score']):
        im = d['img']
        best, bi = iou_thr, -1
        for i, gb in enumerate(gin.get(im, [])):                 # ① 先配桶内 GT
            if ui[im][i]:
                continue
            v = iou(d['box'], gb)
            if v >= best:
                best, bi = v, i
        if bi >= 0:
            ui[im][bi] = True; tp.append(1); fp.append(0); continue
        best, bi = iou_thr, -1
        for i, gb in enumerate(gout.get(im, [])):                # ② 再看是不是桶外 GT
            if uo[im][i]:
                continue
            v = iou(d['box'], gb)
            if v >= best:
                best, bi = v, i
        if bi >= 0:
            uo[im][bi] = True; continue                          # -> **ignore**
        tp.append(0); fp.append(1)                               # ③ 谁也配不上 -> FP
    if not tp:
        return 0.0, npos
    tp, fp = np.cumsum(tp), np.cumsum(fp)
    rec, prec = tp / npos, tp / np.maximum(tp + fp, 1e-9)
    mrec = np.concatenate([[0.0], rec, [rec[-1]]])
    mpre = np.concatenate([[0.0], prec, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):                       # all-point 插值
        mpre[i] = max(mpre[i], mpre[i+1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx+1] - mrec[idx]) * mpre[idx+1])), npos

CFG = {'baseline':            dict(p50=20.0, ceil=0.88, fp=0.8,  loc=0.05),
       'A: P2 + 原生分辨率':  dict(p50=13.0, ceil=0.88, fp=0.8,  loc=0.05),
       'B: 更大 backbone':    dict(p50=18.0, ceil=0.99, fp=0.10, loc=0.03)}
RES = {}
print(f"{'':<20s}" + ''.join(f'{b:>11s}' for b, _, _ in BUCKETS))
for n, c in CFG.items():
    d = simulate_detector(GTS, **c)
    RES[n] = {b: ap_in_bucket(GTS, d, lo, hi)[0] for b, lo, hi in BUCKETS}
    print(f'{n:<20s}' + ''.join(f'{RES[n][b]:>11.3f}' for b, _, _ in BUCKETS))

base = RES['baseline']
print(f'\\n① **整体 AP {base["all"]:.3f} 看起来「一般般」，但 [0,16) 桶只有 {base["[0,16)"]:.3f}'
      f' —— 60 m 外的标志基本一个都检不到。**')
assert base['[0,16)'] < 0.05 and base['all'] > 0.25
assert base['[0,16)'] < base['[32,64)'] / 10

A, B = RES['A: P2 + 原生分辨率'], RES['B: 更大 backbone']
print(f'② A 与 B 的整体 AP 差 {abs(A["all"]-B["all"]):.3f}，但在关键的 [0,16) 桶上：'
      f'A {A["[0,16)"]:.3f} vs B {B["[0,16)"]:.3f}（**{A["[0,16)"]/B["[0,16)"]:.1f} 倍**）')
print(f'   而在 [32,64) 桶上 B 反而更好：{B["[32,64)"]:.3f} vs {A["[32,64)"]:.3f}')
assert A['[0,16)'] > 3 * B['[0,16)']
assert B['[32,64)'] > A['[32,64)']
print('   -> 只看整体 AP，你会觉得两者差不多；分桶才知道 **A 才是解决安全问题的那个**')"""),
    code("""# ---- 整体 AP 跨数据集**不可比**，分桶 AP 才可比 ----
GTS_BENCH = gen_gt(seed=2, z_lo=8.0, z_hi=70.0)      # 「公开基准式」分布：远处样本少
cb = Counter(b for g_ in GTS_BENCH for b, lo, hi in BUCKETS if lo <= g_['size'] < hi)
print('同一个 baseline 模型，在两种尺寸分布的测试集上:')
print(f"  TSR 实车分布 : [0,16) 占 {cc['[0,16)']/cc['all']:.0%}")
print(f"  公开基准分布 : [0,16) 占 {cb['[0,16)']/cb['all']:.0%}")

d1 = simulate_detector(GTS, **CFG['baseline'])
d2 = simulate_detector(GTS_BENCH, z_lo=8.0, z_hi=70.0, **CFG['baseline'])
r1 = {b: ap_in_bucket(GTS, d1, lo, hi)[0] for b, lo, hi in BUCKETS}
r2 = {b: ap_in_bucket(GTS_BENCH, d2, lo, hi)[0] for b, lo, hi in BUCKETS}
print(f"\\n{'测试集':<16s}" + ''.join(f'{b:>11s}' for b, _, _ in BUCKETS))
print(f'{"TSR 实车分布":<16s}' + ''.join(f'{r1[b]:>11.3f}' for b, _, _ in BUCKETS))
print(f'{"公开基准分布":<16s}' + ''.join(f'{r2[b]:>11.3f}' for b, _, _ in BUCKETS))

assert r2['all'] - r1['all'] > 0.25, '整体 AP 会随尺寸分布大幅漂移'
for b in ['[16,32)', '[32,64)', '[64,inf)']:
    assert abs(r1[b] - r2[b]) < 0.10, (b, r1[b], r2[b])
print(f'\\n✅ **同一个模型**，整体 AP 从 {r1["all"]:.3f} 跳到 {r2["all"]:.3f}（差 {r2["all"]-r1["all"]:.3f}），')
print('   而每个尺寸桶的 AP 几乎不变（差 < 0.10）。')
print('   -> **整体 mAP 跨数据集不可比；分桶 AP 才是模型能力的稳定刻画。**')
print('\\n⚠️  统计学的坑：桶越小样本越少方差越大。[0,16) 只有几十个实例时，')
print('    AP 的随机波动可能就有 ±0.05 —— 必须报告每桶实例数并给 bootstrap 置信区间。')"""),
    md("""## ✏️ 练习 1：相机配置求解器

实现 `plan_camera(S, Z_target, p_min, width_px, hfov_deg)`，返回 dict：

- `f_now` —— 现有配置的像素焦距
- `p_at_target` —— 现有配置下目标在 `Z_target` 处的像素尺寸
- `ok` —— `p_at_target >= p_min` 是否满足
- `f_req` —— 达标所需的像素焦距
- `width_req_same_fov` —— 保持 FOV 不变时需要的传感器宽度
- `hfov_req_same_width` —— 保持宽度不变时需要收窄到的 FOV（度）"""),
    code("""def plan_camera(S, Z_target, p_min, width_px, hfov_deg):
    # TODO: 用 focal_px / obj_px / required_focal / required_width / required_hfov
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
r = plan_camera(0.6, 100.0, 16.0, 1920, 60.0)
for k, v in r.items():
    print(f'  {k:<22s} {v}')
assert r['ok'] is False
assert abs(r['f_now'] - 1662.77) < 0.01
assert abs(r['p_at_target'] - 9.977) < 0.01
assert abs(r['f_req'] - 2666.667) < 0.01
assert abs(r['width_req_same_fov'] - 3079.2) < 0.5
assert abs(r['hfov_req_same_width'] - 39.598) < 0.05

r2 = plan_camera(0.6, 40.0, 16.0, 1920, 60.0)
assert r2['ok'] is True and r2['p_at_target'] > 16.0
print(f'\\n40 m 目标 -> 现有主摄就够（{r2["p_at_target"]:.1f} px >= 16）  ✅')

print(f"\\n{'目标距离':>9s} {'现有 p':>8s} {'达标?':>6s} {'需要的宽度(60°)':>16s} {'需要的FOV(1920)':>16s}")
for Zt in [40, 60, 80, 100, 130]:
    rr = plan_camera(0.6, float(Zt), 16.0, 1920, 60.0)
    print(f'{Zt:>8d}m {rr["p_at_target"]:>8.1f} {("✅" if rr["ok"] else "❌"):>6s} '
          f'{rr["width_req_same_fov"]:>16.0f} {rr["hfov_req_same_width"]:>15.1f}°')
print('\\n✅ 练习 1 通过：**先算物理量、再谈方法** —— 这套推导在面试里极有说服力')"""),
    md("""## ✏️ 练习 2：消失点 ROI 带

实现 `horizon_band(f, dH_range, Z_range, pitch_deg, lateral_m, img_w, img_h)`，返回 dict：

- `top` / `bottom` —— ROI 带上下边界相对地平线的像素偏移（向上为正），
  由**最坏组合**决定：`top = f·ΔH_max/Z_min + margin`，`bottom = f·ΔH_min/Z_max − margin`
- `margin_px` —— 俯仰余量 `f·tan(pitch)`
- `roi_h` = `top − bottom`；`roi_w` = `2·f·lateral_m/Z_min + 60`
- `area_ratio` = `roi_h·roi_w / (img_w·img_h)`"""),
    code("""def horizon_band(f, dH_range, Z_range, pitch_deg, lateral_m, img_w, img_h):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
b = horizon_band(F_MAIN, (0.3, 3.0), (40.0, 200.0), 1.4, 8.0, 1920, 1080)
for k, v in b.items():
    print(f'  {k:<12s} {v:.2f}')
assert abs(b['margin_px'] - 40.65) < 0.5
assert abs(b['top'] - 165.36) < 0.5 and abs(b['bottom'] + 38.16) < 0.5
assert abs(b['roi_h'] - 203.5) < 1.0 and abs(b['roi_w'] - 725.1) < 1.0
assert 0.05 < b['area_ratio'] < 0.10

b3 = horizon_band(F_MAIN, (0.3, 3.0), (40.0, 200.0), 3.0, 8.0, 1920, 1080)
assert b3['roi_h'] > b['roi_h'] and b3['area_ratio'] < 0.15
print(f'\\n俯仰余量 1.4° -> 带高 {b["roi_h"]:.0f} px，占全图 {b["area_ratio"]:.1%}')
print(f'俯仰余量 3.0° -> 带高 {b3["roi_h"]:.0f} px，占全图 {b3["area_ratio"]:.1%}  '
      f'（**留足余量仍只占 1/10，非常划算**）')

print(f"\\n{'覆盖距离区间':>16s} {'带高(px)':>9s} {'带宽(px)':>9s} {'占全图':>8s} {'中心凹吞吐':>10s}")
for zl, zh in [(20.0, 200.0), (40.0, 200.0), (60.0, 250.0), (80.0, 300.0)]:
    bb = horizon_band(F_MAIN, (0.3, 3.0), (zl, zh), 3.0, 8.0, 1920, 1080)
    a = bb['area_ratio']
    print(f'{f"[{zl:.0f}, {zh:.0f}] m":>16s} {bb["roi_h"]:>9.0f} {bb["roi_w"]:>9.0f} '
          f'{a:>8.1%} {(1-a)+a*9:>9.2f}×')
print('\\n✅ 练习 2 通过：**ROI 只负责「远且小」，近处大标志交给全图那一路 —— 分工由几何自动给出**')"""),
    md("""## ✏️ 练习 3：按**距离**分桶的召回

像素尺寸分桶是通用做法，但 TSR 真正关心的是**距离**。
实现 `distance_recall(gts, dets, edges, iou_thr=0.5, score_thr=0.3)`：

按 GT 的 `Z` 落入 `edges` 给出的区间分桶（`[edges[i], edges[i+1])`），
统计每桶里「被某个 score ≥ score_thr、IoU ≥ iou_thr 的检测匹配上」的 GT 比例。
每个检测最多认领一个 GT（同一张图内贪心，按分数降序）。
返回 `{'[lo,hi)': {'n': …, 'recall': …}}`。"""),
    code("""def distance_recall(gts, dets, edges, iou_thr=0.5, score_thr=0.3):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
EDGES = [0, 20, 40, 60, 90, 150]
LAB = [f'[{EDGES[i]},{EDGES[i+1]})' for i in range(len(EDGES) - 1)]
d_base = simulate_detector(GTS, **CFG['baseline'])
d_a = simulate_detector(GTS, **CFG['A: P2 + 原生分辨率'])
rb, ra = distance_recall(GTS, d_base, EDGES), distance_recall(GTS, d_a, EDGES)

print(f"{'距离桶 (m)':>12s} {'实例数':>7s} {'baseline':>10s} {'方案 A':>10s} {'该距离的像素尺寸':>18s}")
for l, lo, hi in zip(LAB, EDGES[:-1], EDGES[1:]):
    mid = (lo + hi) / 2 if lo > 0 else 14.0
    print(f'{l:>12s} {rb[l]["n"]:>7d} {rb[l]["recall"]:>10.3f} {ra[l]["recall"]:>10.3f} '
          f'{obj_px(F_MAIN, S_SIGN, mid):>17.1f}px')

vals = [rb[l]['recall'] for l in LAB]
assert all(vals[i] >= vals[i+1] - 0.05 for i in range(len(vals) - 1)), vals
assert vals[0] - vals[-1] > 0.70, '召回必须随距离显著衰减'
assert ra['[60,90)']['recall'] > 3 * rb['[60,90)']['recall']
assert sum(rb[l]['n'] for l in LAB) == len(GTS)
print('\\n✅ 练习 3 通过：**按距离分桶才能直接对上产品需求**')
print('   （「80 m 外的限速牌召回是多少」是产品经理会问的问题，「AP_small」不是）')"""),
    md("""## ✏️ 练习 4：首次确认距离（first-confirm distance）

比 AP 更贴近产品体验的指标。模拟一次「接近过程」：自车以 v 匀速逼近一块静止标志，
每帧按 `p = f·S/Z` 算出像素尺寸与检出概率，**连续 `n_confirm` 帧检出才算确认**。

实现 `first_confirm_distance(p50, ceil, k, n_confirm, v_kmh, fps, z_start, z_stop, seed, n_trials)`，
返回长度 `n_trials` 的 numpy 数组（该次仿真的首次确认距离，米；始终未确认记 0.0）。

> 检出概率用 `ceil / (1 + exp(-k·(p - p50)))`，与前面的 `simulate_detector` 一致。"""),
    code("""def first_confirm_distance(p50, ceil=0.88, k=0.35, n_confirm=3, v_kmh=100.0, fps=30.0,
                           z_start=200.0, z_stop=5.0, seed=0, n_trials=300,
                           S=0.6, f=None):
    # TODO: 逐帧从 z_start 逼近到 z_stop，步长 = v/fps；连续 n_confirm 帧检出即确认
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
def summarize(a):
    return float(np.median(a)), float(np.percentile(a, 10)), float((a == 0).mean())

print(f"{'配置':<34s} {'首检距离 中位数':>16s} {'p10':>8s} {'从未确认':>9s}")
rows = {}
for tag, kw in [('baseline (p50=20), 3 帧确认', dict(p50=20.0, n_confirm=3)),
                ('方案A  (p50=13), 3 帧确认', dict(p50=13.0, n_confirm=3)),
                ('方案A  (p50=13), 1 帧确认', dict(p50=13.0, n_confirm=1)),
                ('方案A  (p50=13), 5 帧确认', dict(p50=13.0, n_confirm=5))]:
    a = first_confirm_distance(**kw)
    rows[tag] = a
    m, p10, nz = summarize(a)
    print(f'{tag:<34s} {m:>14.1f}m {p10:>7.1f}m {nz:>9.1%}')

m_base = np.median(rows['baseline (p50=20), 3 帧确认'])
m_a = np.median(rows['方案A  (p50=13), 3 帧确认'])
m_1 = np.median(rows['方案A  (p50=13), 1 帧确认'])
m_5 = np.median(rows['方案A  (p50=13), 5 帧确认'])
assert m_a > m_base + 15.0, (m_a, m_base)
assert m_1 > m_5, '确认帧数越多，确认得越晚（离标志越近）'
assert all((rows[t] <= 200.0).all() for t in rows)
V_MS = 100 / 3.6
print(f'\\n方案 A 把首次确认距离从 {m_base:.0f} m 推到 {m_a:.0f} m'
      f'  =  多出 {(m_a-m_base)/V_MS:.2f} s 的反应时间')
print(f'而把确认帧数从 1 提到 5，首检距离从 {m_1:.0f} m 缩到 {m_5:.0f} m'
      f'  =  少了 {(m_1-m_5)/V_MS:.2f} s')
print('\\n⚠️  别把「1 帧确认的 189 m」当成好事：那个距离上标志只有'
      f' {obj_px(F_MAIN, S_SIGN, 189.0):.1f} px，单帧检出概率只有几个百分点 ——')
print('    1 帧确认换来的「早」是**不可靠的早**，表现为大量闪烁与误报。')
print('    真正要看的是「首次确认距离」与「闪烁率 / 误报持续时长」的联合曲线（C55 m04）。')
print('\\n✅ 练习 4 通过：**多帧确认换稳定性，代价是首检距离 —— 这是 C55 m04 的核心权衡，**')
print('   而它在 mAP 里完全看不见')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def plan_camera(S, Z_target, p_min, width_px, hfov_deg):
    f_now = focal_px(width_px, hfov_deg)
    p_at = obj_px(f_now, S, Z_target)
    f_req = required_focal(S, Z_target, p_min)
    return {'f_now': f_now,
            'p_at_target': p_at,
            'ok': bool(p_at >= p_min),
            'f_req': f_req,
            'width_req_same_fov': required_width(hfov_deg, f_req),
            'hfov_req_same_width': required_hfov(width_px, f_req)}"""),
    code("""# 练习 2 参考答案
def horizon_band(f, dH_range, Z_range, pitch_deg, lateral_m, img_w, img_h):
    dH_lo, dH_hi = dH_range
    Z_lo, Z_hi = Z_range
    margin = f * math.tan(math.radians(pitch_deg))
    top = horizon_offset(f, dH_hi, Z_lo) + margin        # 最近 + 最高 -> 最大偏移
    bottom = horizon_offset(f, dH_lo, Z_hi) - margin     # 最远 + 最矮 -> 最小偏移
    roi_h = top - bottom
    roi_w = 2 * horizon_offset(f, lateral_m, Z_lo) + 60.0
    return {'top': top, 'bottom': bottom, 'margin_px': margin,
            'roi_h': roi_h, 'roi_w': roi_w,
            'area_ratio': roi_h * roi_w / (img_w * img_h)}"""),
    code("""# 练习 3 参考答案
def distance_recall(gts, dets, edges, iou_thr=0.5, score_thr=0.3):
    by_img = {}
    for i, g_ in enumerate(gts):
        by_img.setdefault(g_['img'], []).append(i)
    hit = [False] * len(gts)
    d_by_img = {}
    for d in dets:
        if d['score'] >= score_thr:
            d_by_img.setdefault(d['img'], []).append(d)
    for im, ds in d_by_img.items():
        taken = set()
        for d in sorted(ds, key=lambda x: -x['score']):      # 分数降序贪心
            best, bi = iou_thr, -1
            for gi in by_img.get(im, []):
                if gi in taken:
                    continue
                v = iou(d['box'], gts[gi]['box'])
                if v >= best:
                    best, bi = v, gi
            if bi >= 0:
                taken.add(bi); hit[bi] = True
    out = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        idx = [i for i, g_ in enumerate(gts) if lo <= g_['Z'] < hi]
        n = len(idx)
        out[f'[{lo},{hi})'] = {'n': n,
                               'recall': (sum(hit[i] for i in idx) / n) if n else float('nan')}
    return out"""),
    code("""# 练习 4 参考答案
def first_confirm_distance(p50, ceil=0.88, k=0.35, n_confirm=3, v_kmh=100.0, fps=30.0,
                           z_start=200.0, z_stop=5.0, seed=0, n_trials=300,
                           S=0.6, f=None):
    f = F_MAIN if f is None else f
    g = np.random.default_rng(seed)
    dz = (v_kmh / 3.6) / fps                                   # 每帧前进的距离
    zs = np.arange(z_start, z_stop, -dz)
    probs = ceil / (1.0 + np.exp(-k * (f * S / zs - p50)))      # 每帧的检出概率
    out = np.zeros(n_trials)
    for t in range(n_trials):
        hits = g.random(len(zs)) < probs
        streak = 0
        for i, h in enumerate(hits):
            streak = streak + 1 if h else 0
            if streak == n_confirm:
                out[t] = zs[i]                                 # 确认时刻的距离
                break
    return out"""),
    md("""---
## 🧪 真实工程胶囊：TSR 小目标方案的一页纸"""),
    code("""RECIPE = r'''
# ================== ① 先算物理量（任何讨论的第一步） ==================
f  = (W/2) / tan(radians(HFOV)/2)          # 1920 / 60°  -> 1662.8 px
p  = f * S / Z                              # 0.6 m 标志: 30m→33.3px, 60m→16.6px, 100m→10.0px
Zd = f * S / 16     # 检出距离  (1920/60° -> 62.4 m)
Zc = f * S / 24     # 细分类距离(1920/60° -> 41.6 m)   ← **两者差 20 m，系统必须能表达
                    #                                     「已检出但类别未定」**
X  = W * S / (2*16) # 最大作用距离处的横向半宽 = 36 m，**与 FOV 无关**
                    #  -> 想同时看得更远 + 更宽，只能加像素

# ================== ② 相机分工（L2+ 前视标准配置） ==================
tele  30° : 60–134 m   早发现 -> 「有标志、类别未定」，触发跟踪 + 地图查询
main  60° : 15–62 m    检出 + 分类，最终类别的主要来源
wide 120° : < 21 m     近处 / 大角度 / 主摄被遮挡时兜底
交叠区    : 跨相机类别一致性校验；不一致 -> 触发回传（C58）

# ================== ③ ROI（消失点带）—— 唯一的「双赢」改动 ==================
Δv = f * ΔH / Z                             # 与 p = f·S/Z 是同一个公式
band_top    = f*ΔH_max/Z_min + f*tan(3°)    # 最坏组合 + **±3° 俯仰余量**（f=1663 时 87 px）
band_bottom = f*ΔH_min/Z_max - f*tan(3°)
# 覆盖 40–200 m、ΔH∈[0.3,3.0]、横向 ±8 m -> ROI ≈ 725×297 = 全图的 10%
# 中心凹吞吐 = (1-a) + a·3² ≈ 1.7×，而全图原生要 9×
# 纪律：地平线用**实时估计**（IMU / 车道线灭点 / 地面拟合），**不用标定常数**；
#       弯道要沿道路走廊「掰弯」ROI；**永远保留一路无 ROI 的全图兜底**

# ================== ④ 网络侧 ==================
strides      = [4, 8, 16, 32]               # **必须有 P2**：16.6px/8 = 2.1 格，勉强；/4 = 4.2 格
fpn_canonical = 64                          # 把 k = k0 + log2(sqrt(wh)/224) 的锚点从 224 下移
assigner     = "NWD 或 center-based"         # 模块 03：IoU 对小框的位移过于敏感
loss         = "scale-aware 加权 + GIoU/NWD 混合"

# ================== ⑤ 实施顺序（先免费午餐，再背包） ==================
S1 免费三件套: ROI 裁剪(-1ms) + NWD(0ms) + 小目标 copy-paste(0ms)     ≈ +10 AP_small
S2 结构      : 加 P2 + 锚点下移                        (+2.2ms)      ≈ +3.5
S3 级联      : L1 类别无关/低阈值 + L2 原生分辨率 crop   (+3.2ms)      ≈ +5.5
              **门禁 R1 >= 0.95**（级联召回是乘法 R1×R2）
S4 时序      : 多帧融合 + 迟滞状态机                    (+0.5ms)      ≈ +4.0
S5 硬件      : 长焦相机 + 跨相机关联                    (+5.0ms)      ≈ +12.0

# ================== ⑥ 评测（不这样测就等于没测） ==================
report = {
  "AP_by_size":     ["[0,16)", "[16,32)", "[32,64)", "[64,inf)"],   # **必须带每桶实例数**
  "recall_by_dist": [20, 40, 60, 90, 150],                          # 产品语言
  "first_confirm_distance": "p50 / p10",                            # 反应时间
  "FP_per_km":      "而不是 precision（precision 依赖测试集正样本密度，跨集不可比）",
  "AP_by_position": "切片边界带 / 图像边缘 vs 中心（几乎无人做）",
  "bootstrap_CI":   "小桶必须给置信区间，否则 +0.03 毫无意义",
}
# **整体 mAP 跨数据集不可比**：同一模型换个尺寸分布，整体 AP 能从 0.29 跳到 0.60，
#   而各尺寸桶的 AP 几乎不变。只报整体 mAP 等于什么都没说。
'''
print(RECIPE)
for kk in ['f  = (W/2)', 'X  = W * S', 'tele  30°', 'Δv = f * ΔH / Z', '实时估计',
           'fpn_canonical', 'R1 >= 0.95', 'first_confirm_distance', 'FP_per_km']:
    assert kk in RECIPE, kk
print('✅ 配方覆盖：物理量 / 相机分工 / ROI 几何与纪律 / 网络侧 / 实施顺序 / 评测协议')"""),
    md("""### 小结

- **一切从 `p = f·S/Z` 开始**，`f = (W/2)/tan(θ/2)`。1920×1080 / 60° FOV 下
  **f = 1662.8 px**，60 cm 标志在 **30 / 60 / 100 m 处分别是 33.3 / 16.6 / 10.0 px**。
  这三个数字要能张口就来 —— 它们把「TSR 是小目标问题」从修辞变成了算式。
- **`p_min` 不是一个数而是三个**：提议 ~9 px、检测 ~16 px、细分类 ~24 px。
  于是主摄的**检出距离 62 m、识别距离 42 m**，中间有 20 m / 0.75 s 的
  「知道有牌子但不知道写什么」的窗口 —— 这直接要求两级架构、跟踪、以及
  接口里必须有「类别未定」这个状态。
- **反推是核心技能**：要在 100 m 检出就需要 f = 2667 px，
  等价于「4K（3079 px 宽）」或「收窄到 39.6° 的长焦」。
  **网络输入分辨率只能把已有像素用满，相机分辨率 × 焦距才决定天花板。**
- **像素够了格子还得够**：`n_cells = p/stride`。letterbox 640 后 16.6 px 的标志
  在 P3 上只有 **0.7 格**。按 FPN 原始规则它该去「P0.25 层」——
  **把分配锚点从 224 下移到 64，是一个几行配置换 2–4 AP_small 的改动。**
- **横向覆盖不变量 `X_max = W·S/(2·p_min)`，f 被完全约掉**：
  三台 1920 宽的相机在各自最大作用距离处的横向半宽都是 36 m。
  **换 FOV 只是把同一块覆盖区搬远搬近；想同时更远更宽，只能加像素。**
- **ROI 带是唯一的双赢改动**（+精度、−延迟）：`Δv = f·ΔH/Z` 与 `p = f·S/Z` 同源，
  远目标既小又靠近地平线。ROI 只占全图 7–10%，中心凹吞吐 ~1.6×，而全图原生要 9×。
  **但它必须是软的：地平线用实时估计、留 ±3° 余量、保留全图兜底** ——
  写成标定常数会导致「某段上坡整段漏检」。
- **方案排序两步法**：先无条件取所有 Δ延迟 ≤ 0 的（严格占优），
  剩下的按延迟预算做背包。8 ms 预算下的最优解是
  「ROI + NWD + copy-paste + 长焦 + 级联 + 多帧」，净 7.7 ms。
  **SAHI 切片（+9 AP 但 +32 ms）在任何合理预算下都进不了解集。**
- **不分桶就看不见改进**：整体 AP 0.29 的模型，在 [0,16) 桶上只有 **0.005**。
  而**整体 mAP 跨数据集根本不可比** —— 同一模型换个尺寸分布，
  整体 AP 从 0.29 跳到 0.60，各尺寸桶却几乎不变。
  再配上按距离分桶、首次确认距离、FP/km，才构成一套能对上产品需求的评测。

**整门 C57 的一句话**：小目标检测的每个方案，都是在回答
「信息在**光学 / 预处理 / 网络结构 / 分配损失 / 评测**这五个环节的哪一步被丢掉了，
以及花多少代价能把它捡回来」。把方案挂在这五个环节上讲，逻辑就永远是清晰的。"""),
]
