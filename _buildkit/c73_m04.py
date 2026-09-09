# -*- coding: utf-8 -*-
"""C73 模块 04 · 3D 检测：从锚框到中心点。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03；C18 的 2D 检测（anchor / NMS / 正负样本分配）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_detection3d.ipynb'
                       '（从零实现旋转框 IoU（多边形裁剪，四个自检精确通过）/ '
                       '<strong>Δθ=45° 时 IoU 只有 0.4254——2 个朝向的锚框让 45° 目标拿到 0 个正锚</strong> / '
                       '正负比 0.0416%，而加到 4 朝向<strong>不改善它</strong> / '
                       '<strong>中心点头对薄目标同样退化：标志的高斯半径 0.08 格</strong> / '
                       '角度的三种编码）'),
    ("核心参考", "Zhou &amp; Tuzel, <em>VoxelNet</em>（CVPR 2018，anchor-based）· "
                 "Yan et al., <em>SECOND</em>（2018）· "
                 "Lang et al., <em>PointPillars</em>（CVPR 2019）· "
                 "Zhou et al., <em>CenterNet</em>（2019，高斯半径）· "
                 "Yin et al., <em>CenterPoint</em>（CVPR 2021）· "
                 "本课程 C54（DETR 与集合预测：第三条路）· C57（小目标）"),
    ("预计时长", "读 45 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("box-params", "3D 框的 7 个自由度，以及一个容易漏掉的对称性", "".join([
        MATH(r"\text{box} = (x,\ y,\ z,\ w,\ l,\ h,\ \theta)"),
        P("自动驾驶里通常只保留绕 $z$ 的偏航角（车辆不会侧翻），所以是 7 而不是 9。"
          "<strong>而 $\\theta$ 这一维带来的问题占了本模块的一半。</strong>"),
        TABLE(["性质", "说明", "后果"], [
            ["<strong>周期性</strong>", "$\\theta$ 与 $\\theta+2\\pi$ 相同",
             "<strong>直接回归 $\\theta$ 会在 $\\pm\\pi$ 处炸</strong>："
             "<em>真值 179°、预测 −179°，几何差 2° 而 L1 损失是 358°——放大 179 倍</em>"],
            ["<strong>中心对称</strong>", "$\\theta$ 与 $\\theta+\\pi$ 给出<em>同一个框</em>",
             "<strong>notebook 验证 IoU(0°, 180°) = 1.000000</strong>；"
             "<em>所以角度只在 $[0,\\pi)$ 内可辨识，"
             "而「车头朝哪」需要额外的方向分类头</em>"],
            ["<strong>与尺寸耦合</strong>", "$w$ 与 $l$ 互换 + $\\theta$ 转 90° 是同一个框",
             "<em>所以「长宽」的定义必须钉死</em>（本课：$l$ 沿车长、$w$ 沿车宽）"],
        ]),
        CALLOUT("intuition",
                "<strong>三条合起来意味着：$\\theta$ 不是一个普通的回归目标。</strong>"
                "<em>它活在一个商空间 $S^1/\\{\\pm1\\}$ 上，"
                "而普通的 L1/L2 损失假设目标活在 $\\mathbb{R}$ 上</em>。"
                "<strong>第 8 节给出三种编码方式与它们各自解决了上面哪一条。</strong>"),
    ])),

    # ============================================================== 2
    ("rotated-iou", "旋转框 IoU：多边形裁剪", "".join([
        P("2D 的轴对齐 IoU 是两行代码。<strong>旋转框需要真正的多边形求交。</strong>"
          "notebook 第 2 节用 Sutherland–Hodgman 裁剪从零实现，并用四个精确自检验证："),
        TABLE(["自检", "期望值", "实测"], [
            ["同一个框", "1", "<strong>1.0</strong>"],
            ["沿长轴平移 $l/2$", "$1/3$", "<strong>0.333333333</strong>"],
            ["沿宽轴平移 $w/2$", "$1/3$", "<strong>0.333333333</strong>"],
            ["<strong>$\\theta$ 转 180°</strong>", "<strong>1</strong>（中心对称）",
             "<strong>1.0</strong>"],
        ]),
        DUAL(
            "<strong>第二、三行那个 $1/3$ 值得记，因为它是一个好用的心算基准。</strong>"
            "<em>两个同尺寸的框沿某轴平移半个边长时，交集是 $1/2$、并集是 $3/2$，"
            "所以 IoU 恰好 $1/3$</em>。"
            "<strong>而它同时说明「IoU 0.5」比想象的严格：它对应的平移小于半个边长。</strong>",
            "<strong>而实现上有一个必须注意的细节：多边形的绕向。</strong>"
            "<em>Sutherland–Hodgman 的「在内侧」判据依赖裁剪多边形是逆时针的；"
            "给成顺时针会让所有 IoU 变成 0</em>——"
            "<strong>而这个 bug 不会报错，它只会让所有匹配失败</strong>"
            "（<em>本课作者第一版就栽在这里，四个自检全变成 0.0</em>）。"
            "<strong>所以用有符号面积检查绕向应当是实现的第一步。</strong>",
        ),
    ])),

    # ============================================================== 3
    ("orientation-cost", "朝向不匹配的代价", "".join([
        P("两个同心、同尺寸的 $4.5\\times1.9$ m 框，只差一个角度："),
        TABLE(["$\\Delta\\theta$", "0°", "5°", "10°", "15°", "22.5°",
               "<strong>30°</strong>", "<strong>45°</strong>", "60°", "90°"], [
            ["BEV IoU", "1.0000", "0.8916", "0.8042", "0.7317", "0.6420",
             "<strong>0.5662</strong>", "<strong>0.4254</strong>", "0.3223",
             "0.2676"],
        ]),
        DUAL(
            "<strong>45° 的朝向误差就把 IoU 压到 0.4254——低于 0.5 的常用阈值。</strong>"
            "<em>而 30° 时是 0.5662，刚刚过线</em>。"
            "<strong>所以「IoU ≥ 0.5」这个阈值隐含了「朝向误差必须小于 37.1°」</strong>"
            "（<em>下一节把它对四种长宽比精确反解出来——差别高达 9 倍</em>）。",
            "<strong>而 90° 时 IoU 还有 0.2676 而不是 0</strong>——"
            "<em>因为两个矩形交叉成一个「十字」，中间那块正方形是共有的</em>。"
            "<strong>所以对长宽比接近 1 的目标（行人），朝向几乎无所谓；"
            "而对细长目标（车、卡车），朝向是主导误差源。</strong>"
            "<em>这也解释了为什么 nuScenes 的朝向误差（AOE）是一个独立上报的指标，"
            "而不是被吸收进 IoU 里。</em>",
        ),
    ])),

    # ============================================================== 3b
    ("iou-threshold", "反解：IoU 阈值隐含了多少朝向精度", "".join([
        P("上一节只算了一种长宽比。"
          "<strong>把它推广到四种目标，就能看出「IoU ≥ 0.5」这个阈值"
          "对不同目标其实是完全不同的要求。</strong>"),
        TABLE(["目标（长宽比）", "10°", "15°", "20°", "30°", "45°", "90°"], [
            ["轿车 $4.5\\times1.9$（2.37:1）", "0.804", "0.732", "0.670",
             "0.566", "0.425", "0.268"],
            ["卡车 $10\\times2.5$（4:1）", "0.705", "0.594", "0.499", "0.333",
             "0.215", "0.143"],
            ["<strong>行人 $0.6\\times0.6$（1:1）</strong>", "0.863", "0.816",
             "0.780", "0.732", "0.707", "<strong>1.000</strong>"],
            ["标志的 BEV 投影 $0.8\\times0.1$（8:1）", "0.486", "0.318",
             "0.224", "0.143", "0.097", "0.067"],
        ]),
        H3("反解出允许的朝向误差"),
        TABLE(["目标", "IoU $\\ge$ 0.5 允许", "IoU $\\ge$ 0.7 允许"], [
            ["轿车（2.37:1）", "<strong>37.1°</strong>", "<strong>17.5°</strong>"],
            ["卡车（4:1）", "19.9°", "10.2°"],
            ["<strong>行人（1:1）</strong>", "<strong>90.0°</strong>",
             "<strong>90.0°</strong>"],
            ["<strong>标志的 BEV 投影（8:1）</strong>", "<strong>9.6°</strong>",
             "<strong>5.1°</strong>"],
        ]),
        DUAL(
            "<strong>同一个阈值 0.5，对轿车允许 37.1° 的朝向误差，"
            "对标志的 BEV 投影只允许 9.6°——差 3.9 倍；"
            "而对行人<em>完全不约束</em>（90°）。</strong>"
            "<em>行人那一行的 90° 不是数值问题："
            "正方形转 90° 就是它自己，所以 IoU 回到 1.000</em>——"
            "<strong>也就是说 IoU 对朝向不是单调的，"
            "对方形目标它以 90° 为周期。</strong>",
            "<strong>这解释了两件常见的评测设计。</strong>"
            "① <strong>KITTI 对车用 0.7、对行人和骑车人用 0.5</strong>——"
            "<em>0.7 对车意味着 17.5° 的朝向要求（合理），"
            "而对近方形的行人，任何 IoU 阈值都管不到朝向</em>；"
            "② <strong>nuScenes 把朝向误差（AOE）作为独立指标上报</strong>，"
            "<em>而不是让它被 IoU 吸收</em>——"
            "<strong>因为上表说明「被吸收的程度」完全取决于长宽比。</strong>"
            "<em>所以「我们的 mAP@0.5 很高」这句话，"
            "在方形目标上并不包含任何朝向信息。</em>",
        ),
    ])),

    # ============================================================== 4
    ("anchors", "锚框：朝向必须离散化，而离散得不够就漏掉整个目标", "".join([
        P("2D 检测的锚框按「尺度 × 长宽比」枚举。"
          "<strong>3D 多了一维：朝向。</strong>"
          "而最常见的做法是只放 0° 与 90° 两个朝向（车道平行或垂直）。"),
        P("notebook 第 4 节在 $80\\times80$ m 的 BEV 网格（$0.2$ m，160,000 个位置）上"
          "扫全部锚框，统计每个目标能拿到几个 IoU ≥ 0.5 的正锚："),
        TABLE(["锚框朝向", "总锚框数", "正锚总数", "正负比",
               "各目标的正锚数（朝向 0° / 22.5° / <strong>45°</strong> / 70°）"], [
            ["<strong>0°, 90°（2 个）</strong>", "320,000", "133",
             "<strong>0.0416%</strong>",
             "53 / 37 / <strong>0</strong> / 43"],
            ["0°, 45°, 90°, 135°（4 个）", "640,000", "258", "0.0403%",
             "53 / 78 / <strong>51</strong> / 76"],
        ]),
        CALLOUT("danger",
                "<strong>第一行第五列：朝向 45° 的那个目标拿到 0 个正锚。</strong>"
                "<em>因为 0° 与 90° 的锚框对它的最好 IoU 只有 0.4254（第 3 节），"
                "低于 0.5 的阈值</em>。"
                "<strong>于是这个目标在训练时<em>完全没有正样本</em>——"
                "它对损失的唯一贡献是「所有锚框都应该说这里没有东西」。</strong>"),
        DUAL(
            "<strong>而第二行说明「加朝向」解决的不是正负比，只是漏掉。</strong>"
            "<em>正锚从 133 涨到 258（约 2 倍），而总锚框也从 32 万涨到 64 万——"
            "正负比几乎不变（0.0416% → 0.0403%）</em>。"
            "<strong>所以锚框方案的两个问题要分开看：</strong>"
            "① <strong>漏掉</strong>（朝向离散得不够）——加朝向能解决；"
            "② <strong>极端的正负不平衡</strong>（万分之四）——加朝框只会更糟。",
            "<strong>而 ② 的常规解法是 focal loss / OHEM（C58 的主题）</strong>，"
            "<em>但那是在治症状</em>。"
            "<strong>真正的结构性修法是放弃「用 IoU 匹配锚框」这件事本身</strong>——"
            "<em>而这正是 CenterPoint 的做法（第 6 节）</em>，"
            "也是 DETR 用匈牙利匹配替代锚框的动机（<strong>C54</strong>）。"
            "<em>三条路的共同点是：让正样本的定义不再依赖一个 IoU 阈值。</em>",
        ),
    ])),

    # ============================================================== 4b
    ("nms", "3D 的 NMS：两个新问题", "".join([
        P("2D 的 NMS 是「按分数排序，抑制掉 IoU 过高的」。"
          "<strong>搬到 3D 会遇到两个新问题，而第二个是真实的失效模式。</strong>"),
        H3("问题一：旋转 IoU 贵 40 倍"),
        TABLE(["候选数 $N$", "最多的配对数", "轴对齐 IoU", "旋转 IoU（多边形裁剪）"], [
            ["100", "4,950", "~0.05 MFLOP", "~2.0 MFLOP"],
            ["1,000", "499,500", "~5.0 MFLOP", "~200 MFLOP"],
            ["5,000", "12,497,500", "~125 MFLOP", "<strong>~5,000 MFLOP</strong>"],
        ]),
        P("<strong>每一对贵约 40 倍</strong>（多边形裁剪 vs 四个 min/max）。"
          "<em>所以实践里普遍先按分数取 top-$k$（第 7b 节）再做 NMS，"
          "而 $k$ 的选择直接决定这一步的耗时。</em>"),
        H3("问题二：BEV NMS 会抑制掉在 $z$ 上分开的目标"),
        P("为了省钱，NMS 常常只在 BEV 平面上做（忽略 $z$）。"
          "<strong>而这会把「上下叠在一起的两个目标」当成重复。</strong>"),
        TABLE(["目标对（$\\delta x{=}0.2$ m）", "$\\Delta z$", "BEV IoU", "3D IoU"], [
            ["轿车 vs 轿车", "0.0 m", "0.915", "0.915"],
            ["轿车 vs 轿车", "0.5 m", "<strong>0.915</strong>", "<strong>0.467</strong>"],
            ["轿车 vs 轿车", "1.0 m", "<strong>0.915</strong>", "0.189"],
            ["标志 vs 标志", "0.5 m", "<strong>0.600</strong>", "0.164"],
            ["<strong>标志 vs 标志</strong>", "<strong>1.0 m</strong>",
             "<strong>0.600</strong>", "<strong>0.000</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>最后一行是 TSR 的一个真实失效：</strong>"
                "<em>一块离地 2.2 m 的限速牌，与它正下方的地面标记（或另一块低位牌），"
                "在 BEV 上完全重叠（IoU 0.600）而在 3D 上毫不相交（IoU 0.000）</em>。"
                "<strong>BEV NMS 会把其中一个抑制掉，而被抑制的通常是分数低的那个——"
                "也就是更远、更小、更需要被检出的那个。</strong>"
                "<em>而这个漏检在「按距离分层的召回」上才看得见，总体 mAP 上看不见。</em>"),
        DUAL(
            "<strong>修法有三条，成本递增。</strong>"
            "① <strong>NMS 时加一个 $z$ 的门</strong>——"
            "<em>只有 $|\\Delta z| <$ 阈值时才允许抑制；零成本，而它解决了绝大多数情形</em>；"
            "② <strong>按类别分组做 NMS</strong>——"
            "<em>标志与地面标记本来就是不同类，不该互相抑制</em>；"
            "③ 真正的 3D IoU NMS——最贵，且对轴对齐的 $z$ 区间其实只需要多算一维。",
            "<strong>而这一节要留下的一般性教训是：为了省钱而降维的操作，"
            "会在「被降掉的那一维上分开」的样本上失效。</strong>"
            "<em>模块 01 的柱体（把 $z$ 压掉）有同样的结构；"
            "C72 模块 04 的 IPM（假设 $z{=}0$）也是</em>。"
            "<strong>三处都是同一个模式：$z$ 是自动驾驶里最容易被压掉、"
            "而对交通标志最关键的那一维。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("centerpoint", "中心点头：把「匹配」换成「峰值 + 回归」", "".join([
        ASCII("""
   锚框头                                中心点头（CenterPoint）
   ┌────────────────────────┐          ┌────────────────────────┐
   │ 每个位置 × 每个朝向     │          │ 每个位置一个「是不是中心」│
   │   → 分类 + 框回归        │          │   → 一张热图（每类一张）  │
   │ 正样本 = IoU ≥ 0.5      │          │ 正样本 = **目标中心那一格**│
   │ 需要 NMS                │          │ 需要局部极大值抑制（3×3）  │
   └────────────────────────┘          └────────────────────────┘
        │                                      │
   正负比 0.0416%                        正样本 4/160,000 = 0.0025%
   45° 目标 → **0 个正样本**              每个目标**恒有** 1 个正样本
        """),
        DUAL(
            "<strong>中心点头的关键性质是「每个目标恒有一个正样本」——"
            "与它的尺寸、朝向、长宽比都无关。</strong>"
            "<em>这直接消掉了第 4 节的问题 ①（漏掉）</em>。"
            "<strong>而朝向从「用来枚举锚框」变成「一个待回归的量」</strong>，"
            "<em>于是离散化的问题也不存在了。</em>",
            "<strong>但正负比看起来更糟了（0.0025% vs 0.0416%）——"
            "而这里有一个关键设计：高斯软标签。</strong>"
            "<em>CenterNet 不是只把中心那一格标成 1，"
            "而是在中心周围画一个高斯，半径由目标尺寸决定</em>"
            "（<strong>让「偏移半径个格子的框」仍有 0.7 的 IoU</strong>）。"
            "<strong>于是有效正样本面积从 1 格涨到 $\\pi r^2$ 格</strong>——"
            "<em>而下一节会说明：这个 $r$ 对薄目标会退化到 0。</em>",
        ),
        TABLE(["目标", "网格尺寸（$0.2$ m 格）", "高斯半径 $r$", "有效正样本面积 $\\pi r^2$"], [
            ["轿车 $1.9\\times4.5$ m", "22.5 × 9.5 格", "1.23 格", "<strong>4.7 格</strong>"],
            ["行人 $0.6\\times0.6$ m", "3.0 × 3.0 格", "0.28 格", "0.2 格"],
            ["<strong>标志 $0.8\\times0.1$ m</strong>", "0.5 × 4.0 格",
             "<strong>0.08 格</strong>", "<strong>0.0 格</strong>"],
        ]),
    ])),

    # ============================================================== 6
    ("thin-degenerate", "中心点头对薄目标同样退化", "".join([
        P("上一节表格的最后一行是这一节的全部内容。"
          "<strong>交通标志在 BEV 里的投影是 $0.8\\times0.1$ m——"
          "在 $0.2$ m 的网格上只有 $4.0\\times0.5$ 格。</strong>"),
        CALLOUT("danger",
                "<strong>它的宽度（0.5 格）小于一个格子。</strong>"
                "<em>于是 CenterNet 的高斯半径公式给出 0.08 格，"
                "有效正样本面积 $\\pi r^2 = 0.02$ 格——四舍五入是 0</em>。"
                "<strong>也就是说：热图上只有<em>恰好那一格</em>是正样本，"
                "而中心落在格边界上时连那一格都可能标错。</strong>"),
        DUAL(
            "<strong>所以「从 anchor 换到 center」并没有解决薄目标的问题，"
            "它只是把问题从「0 个正锚」换成了「1 个孤立正样本、没有软标签」。</strong>"
            "<em>而模块 03 已经从另一个方向给出同样的结论："
            "要让标志连通需要 $r{=}0.8$ m 的分辨率，"
            "而那时量化误差是 IoU-0.5 预算的 20.8 倍</em>。"
            "<strong>两条独立的推理指向同一件事：$0.2$ m 的 BEV 网格对交通标志太粗。</strong>",
            "<strong>三条可行的出路，而它们都不是「换检测头」：</strong>"
            "① <strong>为薄目标单独用更细的网格</strong>"
            "（<em>标志的 $z$ 范围很窄，所以可以只在 1.5–3 m 这一层用 $0.05$ m 的网格，"
            "代价可控</em>）；"
            "② <strong>不在 BEV 里检测标志</strong>——"
            "<em>用图像检测 + C72 模块 03 的已知尺寸测距（50 m 处 ±1.30 m）</em>；"
            "③ <strong>换评测口径</strong>——"
            "<em>用中心距离而不是 IoU（模块 05），"
            "此时 0.2 m 的网格是够用的</em>。"
            "<strong>而实践中 TSR 普遍走 ②，"
            "这不是因为 LiDAR 不好，而是因为上面这条约束链。</strong>",
        ),
    ])),

    # ============================================================== 6b
    ("decode", "热图怎么解码成框：局部极大值 + top-$k$", "".join([
        P("中心点头输出的是一张热图，"
          "<strong>而「取出目标」这一步有两个必须的操作。</strong>"),
        ASCII("""
   热图 (400×400)
     │
     │ ① 3×3 局部极大值抑制（等价于一次 max-pool + 比较）
     │      纯随机热图上保留 11.20% —— 理论值 1/9 = 11.11%
     ▼
   17,924 个局部极大（仍然太多）
     │
     │ ② 按分数取 top-k
     ▼
   k 个候选 → 各自回归 (offset, size, θ) → 框
        """),
        TABLE(["$k$", "占热图格数", "相对 ~50 个真实目标的召回余量"], [
            ["100", "0.062%", "2×"],
            ["<strong>500</strong>", "0.312%", "<strong>10×</strong>"],
            ["1,000", "0.625%", "20×"],
        ]),
        DUAL(
            "<strong>① 那个 11.20% 值得记：它几乎正好是 $1/9$。</strong>"
            "<em>因为在无结构的热图上，$3\\times3$ 窗口里每个格子等可能是最大的</em>。"
            "<strong>所以局部极大值抑制只能把候选降一个数量级，远不够——"
            "top-$k$ 是必需的第二步。</strong>",
            "<strong>而 $k$ 的选择是一个显式的召回-成本取舍。</strong>"
            "<em>$k$ 太小会截掉低分的真目标（而那些正是远处的小目标）；"
            "$k$ 太大会让第 4b 节的旋转 NMS 变贵（成本 $\\propto k^2$）</em>。"
            "<strong>实践里 $k{=}500$ 给约 10 倍余量，是一个常见的默认值</strong>——"
            "<em>而它应当按「场景里最多可能有多少个目标」来定，"
              "而不是抄一个数</em>。"
            "<strong>而 offset 回归这一项解决的是量化误差</strong>："
            "<em>中心落在格子中间时，热图只能指到格心，"
            "而 offset 头把那半个格子（$0.2$ m 网格上是 $\\le0.14$ m）补回来</em>——"
            "<strong>这正好是模块 01 第 7 节量化误差的一个直接补偿手段。</strong>",
        ),
        CALLOUT("intuition",
                "<strong>offset 回归能补偿多少，是可以算的：</strong>"
                "<em>它把量化误差从 $r\\sqrt3/2$（$0.2$ m 网格上是 0.173 m）"
                "降到「offset 头自身的回归误差」</em>。"
                "<strong>所以模块 03 第 5b 节那张「量化误差 vs 允许误差」的表，"
                "在有 offset 头时应当用回归误差而不是 $r\\sqrt3/2$</strong>——"
                "<em>而那个数只能实测，本课给不出。"
                "但结论的方向不变：网格越粗，offset 头要补的越多。</em>"),
    ])),

    # ============================================================== 7
    ("angle-encoding", "角度的三种编码", "".join([
        TABLE(["编码", "怎么做", "解决了哪一条", "残留问题"], [
            ["<strong>直接回归 $\\theta$</strong>", "L1/L2 损失",
             "无",
             "<strong>周期性：179° vs −179° 的 L1 是 358°，"
             "而几何差只有 2°——放大 179 倍</strong>"],
            ["<strong>$(\\sin\\theta,\\cos\\theta)$</strong>",
             "回归两个分量，再 <code>atan2</code>",
             "<strong>周期性</strong>：179° vs −179° 的 L2 = 0.03490，"
             "<em>恰好等于 $2\\sin1°$</em>",
             "<strong>不含中心对称</strong>：0° 与 180° 被当成完全不同"],
            ["<strong>$(\\sin2\\theta,\\cos2\\theta)$</strong>",
             "把角度加倍再编码",
             "<strong>周期性 + 中心对称</strong>："
             "89° 与 −89°（几何差 2°）的 L2 = 0.06980 = $2\\sin2°$",
             "<strong>丢掉了「车头朝哪」</strong>——需要一个额外的二分类头"],
        ]),
        CALLOUT("warn",
                "<strong>第三行的实现里有一个真实的坑：<code>dir_offset</code>。</strong>"
                "<em>方向二分类的标签是「$\\theta$ 落在 $[0,\\pi)$ 还是 $[\\pi,2\\pi)$」，"
                "而这个区间的<strong>起点</strong>是一个超参数</em>"
                "（<code>SECOND</code> 与 <code>CenterPoint</code> 的默认值不同）。"
                "<strong>起点定在训练数据里朝向的密集处，"
                "会让恰好落在边界上的样本标签抖动</strong>——"
                "<em>而车辆朝向在直路场景里恰好密集分布在 0° 与 180° 附近。</em>"
                "所以 <code>dir_offset</code> 通常取 $\\pi/4$ 这类「远离密集处」的值。"),
        DUAL(
            "<strong>第二行那个「恰好等于 $2\\sin1°$」不是巧合：</strong>"
            "<em>单位圆上两点的弦长就是 $2\\sin(\\Delta\\theta/2)$</em>。"
            "<strong>所以 $(\\sin,\\cos)$ 编码把角度差正确地线性化了（小角度下）</strong>——"
            "而这就是它替代直接回归的全部理由。",
            "<strong>而第三行的取舍是真实的：中心对称与方向信息不可兼得。</strong>"
            "<em>$(\\sin2\\theta,\\cos2\\theta)$ 把 $\\theta$ 与 $\\theta+\\pi$ 映到同一点，"
            "所以它<strong>无法</strong>区分车头车尾</em>。"
            "<strong>实践中的标准做法是「$(\\sin2\\theta,\\cos2\\theta)$ 回归朝向"
            "+ 一个二分类头判方向」</strong>——"
            "<em>而这也是 SECOND 引入 direction classifier 的原因</em>。"
            "<strong>它把一个「在商空间上回归」的问题拆成"
            "「在商空间上回归」+「在商上的纤维里分类」，"
            "而这是处理这类对称性的通用套路。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("checklist", "本模块的清单", "".join([
        OL([
            "<strong>实现旋转框 IoU 的第一步是用有符号面积检查绕向</strong>（第 2 节）——"
            "<em>给错绕向会让所有 IoU 变成 0，而它不报错</em>",
            "<strong>统计每个目标的正样本数，而不只是总正负比</strong>（第 4 节）——"
            "<em>「某个目标 0 个正样本」在总比例上看不出来</em>",
            "<strong>报 IoU 阈值时要说明它对<em>这个类别</em>意味着多少朝向精度</strong>"
            "（第 3b 节）——<em>0.5 对轿车是 37.1°，对方形的行人是「不约束」</em>",
            "<strong>加朝向解决漏掉，不解决正负不平衡</strong>（第 4 节）："
            "133 → 258 个正锚，而比例 0.0416% → 0.0403%",
            "<strong>算一次每类目标的高斯半径</strong>（第 5 节）。"
            "<em>$\\pi r^2 < 1$ 就说明这一类在当前网格下没有软标签</em>",
            "<strong>薄目标的问题不能靠换检测头解决</strong>（第 6 节）——"
            "三条出路是更细的局部网格 / 换传感器通路 / 换评测口径",
            "<strong>BEV NMS 必须加一个 $z$ 的门或按类别分组</strong>（第 4b 节）——"
            "<em>否则标志与它正下方的地面标记会互相抑制（BEV IoU 0.600 而 3D 是 0）</em>",
            "<strong>top-$k$ 按「场景里最多多少个目标」定</strong>（第 6b 节），"
            "<em>而不是抄一个数——它同时决定召回余量与旋转 NMS 的成本（$\\propto k^2$）</em>",
            "<strong>角度用 $(\\sin2\\theta,\\cos2\\theta)$ + 方向二分类</strong>（第 7 节），"
            "<em>不要直接回归 $\\theta$</em>",
        ]),
        CALLOUT("paper",
                "<strong>如果只做一条，做第 4 条。</strong>"
                "<em>「每个目标拿到几个正样本」这个数不需要训练，"
                "在数据准备阶段就能算出来</em>；"
                "<strong>而它能抓到一整类「某些朝向/尺寸的目标从来学不会」的问题</strong>——"
                "<em>而那类问题在总体 mAP 上只表现为「差一点」。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 04 · 3D 检测：从锚框到中心点

这个 notebook 从零实现**旋转框 IoU**（Sutherland–Hodgman 多边形裁剪），
然后用它量四件事：

1. **朝向不匹配的代价**：Δθ=45° 时 IoU 只有 **0.4254**（低于 0.5）；
   而反解出的允许朝向误差在四种长宽比上差 **9 倍**（轿车 37.1° vs 标志 9.6° vs 行人 90°）。
2. **锚框分配**：2 个朝向的锚框让 **45° 的目标拿到 0 个正锚**；
   而加到 4 个朝向**不改善正负比**（0.0416% → 0.0403%）。
3. **BEV NMS 的失效**：标志与它正下方的目标 BEV IoU **0.600** 而 3D IoU **0.000**。
4. **中心点头对薄目标同样退化**：标志的高斯半径 **0.08 格**，有效正样本面积 0 格。

> 心智模型：**这些都不是「模型不够好」，而是「正样本的定义本身对某类目标失效」。**"""),

    md("""## 0 · 环境"""),

    code("""import numpy as np

print('numpy', np.__version__)

GRID = 0.2                              # BEV 网格分辨率
XR, YR = (0., 80.), (-40., 40.)
NX = int((XR[1] - XR[0]) / GRID)
NY = int((YR[1] - YR[0]) / GRID)
print(f'BEV 网格 {NX}×{NY} = {NX*NY:,} 个位置')

# 本模块的四个目标（x, y, θ）—— 朝向刻意覆盖 0°/22.5°/45°/70°
CAR_W, CAR_L = 1.9, 4.5
TARGETS = [(20., -3., 0.0), (35., 3., 22.5), (60., -3., 45.0), (75., 3., 70.0)]
print(f'四个目标，朝向 {[t[2] for t in TARGETS]}°')"""),

    md("""## 1 · 旋转框 IoU：Sutherland–Hodgman 裁剪

**实现的第一步是检查绕向**——给成顺时针会让所有 IoU 变成 0，而它不报错。"""),

    code("""def rect_corners(cx, cy, w, l, th):
    '''BEV 旋转矩形的四角，**逆时针**。l 沿车长、w 沿车宽。'''
    c, s = np.cos(th), np.sin(th)
    R = np.array([[c, -s], [s, c]])
    P = np.array([[-l/2, -w/2], [l/2, -w/2], [l/2, w/2], [-l/2, w/2]])
    return P @ R.T + np.array([cx, cy])

def signed_area(P):
    P = np.asarray(P, float)
    return 0.5 * (np.dot(P[:, 0], np.roll(P[:, 1], -1))
                  - np.dot(P[:, 1], np.roll(P[:, 0], -1)))

# ★ 第一步：绕向自检
a = signed_area(rect_corners(0, 0, CAR_W, CAR_L, 0.0))
print(f'rect_corners 的有符号面积 = {a:.4f}  ({"逆时针 ✓" if a > 0 else "顺时针 ✗"})')
assert a > 0, 'Sutherland–Hodgman 的「在内侧」判据要求裁剪多边形逆时针'

def _isect(p1, p2, a_, b_):
    d1, d2 = p2 - p1, b_ - a_
    den = d1[0]*d2[1] - d1[1]*d2[0]
    if abs(den) < 1e-18:
        return p1
    t = ((a_[0]-p1[0])*d2[1] - (a_[1]-p1[1])*d2[0]) / den
    return p1 + t * d1

def poly_clip(subject, clipper):
    '''用凸多边形 clipper 裁 subject（都要逆时针）。'''
    out = [np.asarray(p, float) for p in subject]
    n = len(clipper)
    for i in range(n):
        a_, b_ = np.asarray(clipper[i], float), np.asarray(clipper[(i+1) % n], float)
        e = b_ - a_
        inside = lambda p: e[0]*(p[1]-a_[1]) - e[1]*(p[0]-a_[0]) >= -1e-12
        new = []
        for j in range(len(out)):
            cur, prv = out[j], out[j-1]
            if inside(cur):
                if not inside(prv):
                    new.append(_isect(prv, cur, a_, b_))
                new.append(cur)
            elif inside(prv):
                new.append(_isect(prv, cur, a_, b_))
        out = new
        if not out:
            return []
    return out

def poly_area(P):
    return abs(signed_area(P)) if len(P) >= 3 else 0.0

def bev_iou(b1, b2):
    '''b = (cx, cy, w, l, theta[rad])。'''
    p1, p2 = rect_corners(*b1), rect_corners(*b2)
    I = poly_area(poly_clip(p1, p2))
    A1, A2 = poly_area(p1), poly_area(p2)
    den = A1 + A2 - I
    return I / den if den > 0 else 0.0

# ★ 四个精确自检
BOX = (0., 0., CAR_W, CAR_L, 0.0)
checks = [
    ('同一个框',            bev_iou(BOX, BOX), 1.0),
    ('沿长轴平移 l/2',      bev_iou(BOX, (CAR_L/2, 0., CAR_W, CAR_L, 0.0)), 1/3),
    ('沿宽轴平移 w/2',      bev_iou(BOX, (0., CAR_W/2, CAR_W, CAR_L, 0.0)), 1/3),
    ('θ 转 180°（中心对称）', bev_iou(BOX, (0., 0., CAR_W, CAR_L, np.pi)), 1.0),
]
print()
for tag, got, want in checks:
    print(f'  {tag:22s} 实测 {got:.9f}  期望 {want:.9f}')
    assert abs(got - want) < 1e-9, (tag, got, want)
print('\\n✅ 四个自检精确通过（1 / 1/3 / 1/3 / 1）')
print('   1/3 值得记：同尺寸框平移半个边长 -> 交 1/2、并 3/2 -> IoU = 1/3')"""),

    md("""## 2 · 朝向不匹配的代价，与 IoU 阈值的反解"""),

    code("""SHAPES = {
    '轿车 4.5×1.9 (2.37:1)':   (1.9, 4.5),
    '卡车 10×2.5 (4:1)':       (2.5, 10.0),
    '行人 0.6×0.6 (1:1)':      (0.6, 0.6),
    '标志BEV 0.8×0.1 (8:1)':   (0.1, 0.8),
}
DEGS = [0, 5, 10, 15, 22.5, 30, 45, 60, 90]

def iou_at_angle(w, l, deg):
    return bev_iou((0., 0., w, l, 0.0), (0., 0., w, l, np.deg2rad(deg)))

print(f\"{'目标':>24s} \" + ''.join(f'{d}°'.rjust(8) for d in DEGS))
for name, (w, l) in SHAPES.items():
    row = [iou_at_angle(w, l, d) for d in DEGS]
    print(f'{name:>24s} ' + ''.join(f'{v:7.3f} ' for v in row))

# 轿车在 45° 掉到 0.5 以下
car = SHAPES['轿车 4.5×1.9 (2.37:1)']
assert iou_at_angle(*car, 45) < 0.5 < iou_at_angle(*car, 30)
print(f'\\n轿车: Δθ=30° -> {iou_at_angle(*car,30):.4f}（过线）；'
      f'45° -> {iou_at_angle(*car,45):.4f}（**不过线**）')

# 方形目标：IoU 对朝向非单调，以 90° 为周期
ped = SHAPES['行人 0.6×0.6 (1:1)']
assert abs(iou_at_angle(*ped, 90) - 1.0) < 1e-9, '正方形转 90° 就是它自己'
assert iou_at_angle(*ped, 45) < iou_at_angle(*ped, 90)
print(f'行人: 45° -> {iou_at_angle(*ped,45):.4f}，而 90° -> '
      f'{iou_at_angle(*ped,90):.4f}  → **IoU 对朝向非单调**')

# 反解允许的朝向误差
def max_angle_for(w, l, thr):
    lo, hi = 0.0, 90.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if iou_at_angle(w, l, mid) >= thr:
            lo = mid
        else:
            hi = mid
    return lo

print(f\"\\n{'目标':>24s} {'IoU>=0.5 允许':>14s} {'IoU>=0.7 允许':>14s}\")
allow = {}
for name, (w, l) in SHAPES.items():
    a5, a7 = max_angle_for(w, l, 0.5), max_angle_for(w, l, 0.7)
    allow[name] = (a5, a7)
    print(f'{name:>24s} {a5:13.1f}° {a7:13.1f}°')

assert allow['行人 0.6×0.6 (1:1)'][0] > 89, '方形目标的朝向完全不被 IoU 约束'
ratio = allow['轿车 4.5×1.9 (2.37:1)'][0] / allow['标志BEV 0.8×0.1 (8:1)'][0]
print(f'\\n✅ 同一个阈值 0.5：轿车允许 {allow["轿车 4.5×1.9 (2.37:1)"][0]:.1f}°，'
      f'标志只允许 {allow["标志BEV 0.8×0.1 (8:1)"][0]:.1f}° -> 差 **{ratio:.1f} 倍**')
print('   而行人是 90°（完全不约束）—— 所以 mAP@0.5 在方形目标上不含朝向信息')
print('   → 这解释了 KITTI 车用 0.7 / 行人用 0.5，以及 nuScenes 独立上报 AOE')"""),

    md("""## 3 · 锚框分配：45° 的目标拿到几个正锚"""),

    code("""def count_positive_anchors(target, anchor_degs, thr=0.5, half=6.0):
    '''在目标周围 ±half m 内扫锚框，返回 (正锚数, 最好 IoU)。'''
    cx, cy, th_deg = target
    tgt = (cx, cy, CAR_W, CAR_L, np.deg2rad(th_deg))
    xs = np.arange(max(cx-half, XR[0]), min(cx+half, XR[1]), GRID)
    ys = np.arange(max(cy-half, YR[0]), min(cy+half, YR[1]), GRID)
    cnt, best = 0, 0.0
    for x in xs:
        for y in ys:
            for a in anchor_degs:
                v = bev_iou(tgt, (x, y, CAR_W, CAR_L, np.deg2rad(a)))
                best = max(best, v)
                if v >= thr:
                    cnt += 1
    return cnt, best

for degs, tag in [([0, 90], '2 个朝向 (0°,90°)'), ([0, 45, 90, 135], '4 个朝向')]:
    total = NX * NY * len(degs)
    per, bests = [], []
    for t in TARGETS:
        c, b = count_positive_anchors(t, degs)
        per.append(c); bests.append(b)
    pos = sum(per)
    print(f'{tag}:')
    print(f'  总锚框 {total:,}   正锚 {pos}   正负比 {100*pos/total:.4f}%')
    print(f'  各目标（朝向 {[t[2] for t in TARGETS]}°）正锚数 {per}')
    print(f'  各目标的最好 IoU {[round(b,4) for b in bests]}')
    if degs == [0, 90]:
        two = (pos, total, per, bests)
    else:
        four = (pos, total, per, bests)
    print()

# ① 45° 的目标在 2 朝向下拿到 0 个正锚
i45 = [t[2] for t in TARGETS].index(45.0)
assert two[2][i45] == 0, f'45° 的目标应当拿到 0 个正锚，实测 {two[2][i45]}'
assert two[3][i45] < 0.5, f'它的最好 IoU 只有 {two[3][i45]:.4f}'
print(f'✅ 朝向 45° 的目标：2 朝向锚框下 **0 个正锚**'
      f'（最好 IoU 仅 {two[3][i45]:.4f}）')
print('   → 它在训练时完全没有正样本，只贡献「这里没有东西」')

# ② 加朝向解决漏掉，但不改善正负比
assert four[2][i45] > 0, '4 朝向应当救回它'
r2, r4 = two[0]/two[1], four[0]/four[1]
print(f'\\n✅ 4 朝向救回了它（{four[2][i45]} 个正锚），'
      f'但正负比 {100*r2:.4f}% → {100*r4:.4f}%（几乎不变）')
assert abs(r4 - r2) / r2 < 0.2, '正负比应当基本不变'
print('   → **加朝向解决「漏掉」，不解决「万分之四的正负不平衡」**')"""),

    md("""## 4 · BEV NMS 会抑制掉在 $z$ 上分开的目标"""),

    code("""def iou_axis_aligned(size, delta):
    s = np.asarray(size, float); d = np.abs(np.asarray(delta, float))
    I = np.prod(np.maximum(s - d, 0.0)); V = np.prod(s)
    den = 2 * V - I
    return I / den if den > 0 else 0.0

PAIRS = {'轿车 4.5×1.9×1.5': (4.5, 1.9, 1.5), '标志 0.8×0.1×0.8': (0.8, 0.1, 0.8)}
print(f\"{'目标对 (δx=0.2m)':>20s} {'Δz':>7s} {'BEV IoU':>9s} {'3D IoU':>9s}\")
for name, s in PAIRS.items():
    for dz in [0.0, 0.2, 0.5, 1.0]:
        b = iou_axis_aligned((s[0], s[1]), (0.2, 0.0))
        t = iou_axis_aligned(s, (0.2, 0.0, dz))
        print(f'{name:>20s} {dz:6.1f}m {b:9.3f} {t:9.3f}')

# 标志在 Δz=1.0 时 3D IoU 归零，而 BEV 仍然 0.6
s = PAIRS['标志 0.8×0.1×0.8']
b = iou_axis_aligned((s[0], s[1]), (0.2, 0.0))
t = iou_axis_aligned(s, (0.2, 0.0, 1.0))
assert b > 0.5 and t == 0.0, (b, t)
print(f'\\n✅ 标志 Δz=1.0m：BEV IoU {b:.3f}（会被 NMS 抑制）而 3D IoU {t:.3f}（毫不相交）')
print('   → 一块离地 2.2m 的牌与它正下方的目标，BEV NMS 会抑制掉分数低的那个')
print('     而分数低的通常是更远、更小、更需要被检出的那个')

def nms_bev(boxes, scores, thr=0.5, z_gate=None):
    '''boxes: [(cx,cy,w,l,th,z,h)]。z_gate 不为 None 时，|Δz| 超过它就不抑制。'''
    order = np.argsort(scores)[::-1]
    keep = []
    for i in order:
        ok = True
        for j in keep:
            if bev_iou(boxes[i][:5], boxes[j][:5]) >= thr:
                if z_gate is not None and abs(boxes[i][5] - boxes[j][5]) > z_gate:
                    continue                      # z 上分开 -> 不抑制
                ok = False; break
        if ok:
            keep.append(int(i))
    return keep

# 构造一个「牌在地面标记正上方」的场景
BX = [(30., -5.5, 0.8, 0.1, 0.0, 2.2, 0.8),      # 限速牌（离地 2.2m），分数低
      (30., -5.5, 0.8, 0.1, 0.0, 0.0, 0.1)]      # 地面标记，分数高
SC = np.array([0.55, 0.90])
k_no = nms_bev(BX, SC, z_gate=None)
k_yes = nms_bev(BX, SC, z_gate=0.5)
print(f'\\n无 z 门: 保留 {len(k_no)} 个 {k_no}  ← **牌被抑制了**')
print(f'有 z 门: 保留 {len(k_yes)} 个 {k_yes}')
assert len(k_no) == 1 and len(k_yes) == 2
print('✅ 加一个 z 门是零成本的，而它修掉了这一整类漏检')"""),

    md("""## 5 · 中心点热图与高斯半径"""),

    code("""def gaussian_radius(h, w, min_overlap=0.7):
    '''CenterNet 的高斯半径：让「偏移 r 个格子的框」仍有 min_overlap 的 IoU。'''
    a1, b1 = 1, h + w
    c1 = w * h * (1 - min_overlap) / (1 + min_overlap)
    r1 = (b1 - np.sqrt(b1**2 - 4*a1*c1)) / 2
    a2, b2 = 4, 2 * (h + w)
    c2 = (1 - min_overlap) * w * h
    r2 = (b2 - np.sqrt(b2**2 - 4*a2*c2)) / 2
    a3, b3 = 4 * min_overlap, -2 * min_overlap * (h + w)
    c3 = (min_overlap - 1) * w * h
    r3 = (b3 + np.sqrt(b3**2 - 4*a3*c3)) / 2
    return float(min(r1, r2, r3))

print(f\"{'目标':>18s} {'网格尺寸':>16s} {'高斯半径':>10s} {'有效面积 πr²':>14s}\")
rad = {}
for tag, (w, l) in [('轿车 1.9×4.5', (1.9, 4.5)), ('行人 0.6×0.6', (0.6, 0.6)),
                    ('标志BEV 0.8×0.1', (0.1, 0.8))]:
    hg, wg = l / GRID, w / GRID
    r = gaussian_radius(hg, wg)
    rad[tag] = r
    print(f'{tag:>18s} {f"{hg:.1f}×{wg:.1f} 格":>16s} {r:9.2f} 格 '
          f'{np.pi*r*r:13.2f} 格')

assert rad['轿车 1.9×4.5'] > 1.0, '轿车应当有一个有意义的高斯半径'
assert np.pi * rad['标志BEV 0.8×0.1'] ** 2 < 0.1, \\
    '标志的有效正样本面积应当接近 0'
print(f'\\n✅ 轿车的有效正样本面积 {np.pi*rad["轿车 1.9×4.5"]**2:.1f} 格，'
      f'而标志只有 {np.pi*rad["标志BEV 0.8×0.1"]**2:.3f} 格')
print(f'   标志的 BEV 宽度只有 {0.1/GRID:.1f} 格 —— **小于一个格子**')
print('   → 中心点头对薄目标同样退化：只有恰好那一格是正样本，且没有软标签')

# 正负比对比
n_heat = NX * NY
print(f'\\n正样本占比：')
print(f'  锚框（2 朝向）: {100*two[0]/two[1]:.4f}%')
print(f'  中心点热图（硬标签）: {100*len(TARGETS)/n_heat:.5f}%')
print(f'  中心点热图（轿车的高斯软标签）: '
      f'{100*len(TARGETS)*np.pi*rad["轿车 1.9×4.5"]**2/n_heat:.5f}%')
print('  → 中心点头的正样本更少，但**每个目标恒有一个**（与尺寸朝向无关）')"""),

    md("""## 6 · 热图解码：局部极大值 + top-$k$"""),

    code("""def local_maxima_mask(H, k=3):
    '''3×3 局部极大值（等价于 max-pool 后比较）。'''
    pad = k // 2
    Hp = np.pad(H, pad, constant_values=-np.inf)
    mx = np.max([Hp[i:i+H.shape[0], j:j+H.shape[1]]
                 for i in range(k) for j in range(k)], axis=0)
    return H >= mx

rng = np.random.default_rng(0)
H_rand = rng.random((NX, NY))
m = local_maxima_mask(H_rand)
frac = m.mean()
print(f'纯随机热图 {NX}×{NY}：局部极大 {int(m.sum()):,} 个 = {100*frac:.2f}%')
print(f'  理论值 1/9 = {100/9:.2f}%')
assert abs(frac - 1/9) < 0.01, f'应当接近 1/9，实测 {frac:.4f}'
print('✅ 局部极大值抑制只能把候选降一个数量级 —— top-k 是必需的第二步\\n')

print(f\"{'k':>6s} {'占热图格数':>11s} {'相对 ~50 个目标的召回余量':>26s}\")
for k in [100, 500, 1000]:
    print(f'{k:6d} {100*k/n_heat:10.3f}% {k/50:25.0f}×')

# 成本：旋转 NMS 是 O(k²)
print(f'\\n旋转 NMS 的成本（O(k²)）：')
for k in [100, 500, 1000, 5000]:
    pairs = k * (k - 1) // 2
    print(f'  k={k:5d}: 最多 {pairs:,} 次旋转 IoU'
          f'（每次比轴对齐贵约 40 倍）')
print('  → k 太小截掉低分的真目标（远处小目标），k 太大让 NMS 变贵')

# offset 回归补偿量化误差
print(f'\\noffset 头补偿的量化误差：网格 {GRID} m -> 最大 '
      f'{GRID*np.sqrt(2)/2:.4f} m（BEV 平面内，半格对角）')
print(f'  而模块 03 第 5b 节用的是三维的 r√3/2 = {GRID*np.sqrt(3)/2:.4f} m')"""),

    md("""## 7 · 角度的三种编码"""),

    code("""def enc_direct(th):      return np.array([th])
def enc_sincos(th):      return np.array([np.sin(th), np.cos(th)])
def enc_sincos2(th):     return np.array([np.sin(2*th), np.cos(2*th)])

def dist(enc, d1, d2):
    return float(np.linalg.norm(enc(np.deg2rad(d1)) - enc(np.deg2rad(d2))))

print('情形一：179° vs −179°（几何差 2°，周期性问题）')
print(f'  直接回归 θ  : L1 = {abs(179-(-179))}°  ← 放大 {abs(179-(-179))/2:.0f} 倍')
print(f'  (sinθ, cosθ): L2 = {dist(enc_sincos,179,-179):.5f}'
      f'   而 2·sin(1°) = {2*np.sin(np.deg2rad(1)):.5f}')
assert abs(dist(enc_sincos, 179, -179) - 2*np.sin(np.deg2rad(1))) < 1e-9
print('  ✅ (sin,cos) 把角度差正确线性化了（单位圆上的弦长 = 2·sin(Δθ/2)）\\n')

print('情形二：0° vs 180°（中心对称——它们是同一个框）')
print(f'  实测 IoU = {bev_iou(BOX,(0.,0.,CAR_W,CAR_L,np.pi)):.6f}')
print(f'  (sinθ, cosθ) : L2 = {dist(enc_sincos,0,180):.5f}  ← **被当成完全不同**')
print(f'  (sin2θ,cos2θ): L2 = {dist(enc_sincos2,0,180):.2e}  ← 正确地为 0')
assert dist(enc_sincos, 0, 180) > 1.9
assert dist(enc_sincos2, 0, 180) < 1e-9
print('  ✅ 只有 (sin2θ, cos2θ) 同时处理周期性与中心对称\\n')

print('情形三：89° vs −89°（中心对称下几何差 2°）')
print(f'  直接回归     : L1 = {abs(89-(-89))}°  ← 放大 {abs(89-(-89))/2:.0f} 倍')
print(f'  (sin2θ,cos2θ): L2 = {dist(enc_sincos2,89,-89):.5f}'
      f'   而 2·sin(2°) = {2*np.sin(np.deg2rad(2)):.5f}')
assert abs(dist(enc_sincos2, 89, -89) - 2*np.sin(np.deg2rad(2))) < 1e-9
print('  ✅ 正确\\n')
print('代价：(sin2θ,cos2θ) 丢掉了「车头朝哪」 -> 需要一个额外的方向二分类头')
print('     （这就是 SECOND 引入 direction classifier 的原因）')"""),

    md("""## 8 · 小结

| 结论 | 数值 |
|---|---|
| 旋转框 IoU 的四个自检 | 1 / **1/3** / **1/3** / 1（精确） |
| 朝向不匹配 | Δθ=30° → 0.5662（过线）；**45° → 0.4254（不过线）** |
| IoU=0.5 隐含的朝向精度 | 轿车 **37.1°** · 卡车 19.9° · **行人 90°（不约束）** · 标志 **9.6°** |
| IoU 对朝向**非单调** | 方形目标以 90° 为周期（45° 是 0.707，90° 回到 1.000） |
| 锚框（2 朝向） | 正负比 **0.0416%**，而 **45° 的目标 0 个正锚** |
| 加到 4 朝向 | 救回了它，但正负比 **0.0403%（几乎不变）** |
| **BEV NMS** | 标志 Δz=1.0 m：BEV IoU **0.600** 而 3D IoU **0.000** |
| 高斯半径 | 轿车 1.23 格（πr² = 4.7）· **标志 0.08 格（πr² ≈ 0）** |
| 局部极大值 | 随机热图上 **11.20%**（理论 1/9 = 11.11%） |
| 角度编码 | 只有 $(\\sin2\\theta,\\cos2\\theta)$ 同时处理周期性与中心对称 |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：旋转框 IoU 与绕向自检

实现 `rotated_iou(b1, b2)`，`b = (cx, cy, w, l, theta)`。
**要求内部先检查两个多边形的绕向，不是逆时针就翻转。**

返回 IoU。然后用四个精确自检验证。"""),

    code("""def rotated_iou(b1, b2):
    \"\"\"旋转框 IoU（内部保证绕向正确）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
B = (0., 0., 1.9, 4.5, 0.0)
CASES = [
    ('同一个框',              (0., 0., 1.9, 4.5, 0.0),      1.0),
    ('沿长轴平移 l/2',        (2.25, 0., 1.9, 4.5, 0.0),    1/3),
    ('沿宽轴平移 w/2',        (0., 0.95, 1.9, 4.5, 0.0),    1/3),
    ('θ 转 180°',             (0., 0., 1.9, 4.5, np.pi),    1.0),
    ('完全分离',              (100., 0., 1.9, 4.5, 0.0),    0.0),
]
for tag, b2, want in CASES:
    got = rotated_iou(B, b2)
    print(f'  {tag:18s} 实测 {got:.9f}  期望 {want:.9f}')
    assert abs(got - want) < 1e-9, (tag, got, want)

# 对称性：IoU(a,b) == IoU(b,a)
rng1 = np.random.default_rng(3)
for _ in range(30):
    a = (rng1.uniform(-3, 3), rng1.uniform(-3, 3), 1.9, 4.5, rng1.uniform(0, np.pi))
    b = (rng1.uniform(-3, 3), rng1.uniform(-3, 3), 1.9, 4.5, rng1.uniform(0, np.pi))
    assert abs(rotated_iou(a, b) - rotated_iou(b, a)) < 1e-9

# 与顺时针输入也要给同一个答案（这就是绕向自检的作用）
def rect_cw(cx, cy, w, l, th):
    return rect_corners(cx, cy, w, l, th)[::-1]
assert signed_area(rect_cw(0, 0, 1.9, 4.5, 0.0)) < 0, '这个构造应当是顺时针'
print('\\n✅ 练习 1 通过：四个自检精确、对称性成立')
print('   而绕向自检的价值：给成顺时针会让所有 IoU 变成 0，**且不报错**')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def _ccw(P):
    P = np.asarray(P, float)
    return P if signed_area(P) > 0 else P[::-1]

def rotated_iou(b1, b2):
    p1 = _ccw(rect_corners(*b1))
    p2 = _ccw(rect_corners(*b2))
    I = poly_area(poly_clip(p1, p2))
    A1, A2 = poly_area(p1), poly_area(p2)
    den = A1 + A2 - I
    return I / den if den > 0 else 0.0

assert abs(rotated_iou((0.,0.,1.9,4.5,0.), (2.25,0.,1.9,4.5,0.)) - 1/3) < 1e-9
assert abs(rotated_iou((0.,0.,1.9,4.5,0.), (0.,0.,1.9,4.5,np.pi)) - 1.0) < 1e-9
print('✅ 参考答案 1 通过')
print('   `_ccw` 只有两行，而它防的是一个「不报错、让所有匹配失败」的 bug。')""" ),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：锚框分配审计

实现 `anchor_audit(targets, anchor_degs, thr=0.5, w=1.9, l=4.5)`，返回 dict：

- `'total_anchors'` —— 全网格的锚框总数
- `'per_target'` —— 每个目标的正锚数（list）
- `'best_iou'` —— 每个目标能拿到的最好 IoU（list）
- `'pos_ratio'` —— 正锚总数 / 锚框总数
- `'starved'` —— **正锚数为 0 的目标的下标**（list）

`'starved'` 非空就说明「有目标在训练时完全没有正样本」。"""),

    code("""def anchor_audit(targets, anchor_degs, thr=0.5, w=1.9, l=4.5, half=6.0):
    \"\"\"返回 dict(total_anchors, per_target, best_iou, pos_ratio, starved)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
a2 = anchor_audit(TARGETS, [0, 90])
a4 = anchor_audit(TARGETS, [0, 45, 90, 135])
for a in (a2, a4):
    assert set(a) == {'total_anchors', 'per_target', 'best_iou',
                      'pos_ratio', 'starved'}

print(f\"{'配置':>10s} {'总锚框':>10s} {'正负比':>10s} {'各目标正锚':>22s} {'饿死的目标':>12s}\")
for tag, a in [('2 朝向', a2), ('4 朝向', a4)]:
    print(f'{tag:>10s} {a["total_anchors"]:10,} {100*a["pos_ratio"]:9.4f}% '
          f'{str(a["per_target"]):>22s} {str(a["starved"]):>12s}')

# ① 2 朝向下，45° 的目标被饿死
i45 = [t[2] for t in TARGETS].index(45.0)
assert a2['starved'] == [i45], (a2['starved'], i45)
assert a2['best_iou'][i45] < 0.5
print(f'\\n2 朝向: 目标 #{i45}（朝向 45°）被饿死，最好 IoU 仅 '
      f'{a2["best_iou"][i45]:.4f}')

# ② 4 朝向救回它，但正负比不变
assert a4['starved'] == []
assert abs(a4['pos_ratio'] - a2['pos_ratio']) / a2['pos_ratio'] < 0.2
print(f'4 朝向: 无饿死目标，而正负比 {100*a2["pos_ratio"]:.4f}% → '
      f'{100*a4["pos_ratio"]:.4f}%（几乎不变）')

# ③ 提高阈值会饿死更多目标
a2_hi = anchor_audit(TARGETS, [0, 90], thr=0.7)
print(f'\\n把阈值提到 0.7（2 朝向）: 饿死的目标 {a2_hi["starved"]}'
      f'（共 {len(TARGETS)} 个）')
assert len(a2_hi['starved']) > len(a2['starved'])
print('✅ 练习 2 通过：**`starved` 这一项在总正负比上完全看不出来**')""" ),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def anchor_audit(targets, anchor_degs, thr=0.5, w=1.9, l=4.5, half=6.0):
    total = NX * NY * len(anchor_degs)
    per, best = [], []
    for (cx, cy, th_deg) in targets:
        tgt = (cx, cy, w, l, np.deg2rad(th_deg))
        xs = np.arange(max(cx-half, XR[0]), min(cx+half, XR[1]), GRID)
        ys = np.arange(max(cy-half, YR[0]), min(cy+half, YR[1]), GRID)
        cnt, b = 0, 0.0
        for x in xs:
            for y in ys:
                for a in anchor_degs:
                    v = rotated_iou(tgt, (x, y, w, l, np.deg2rad(a)))
                    b = max(b, v)
                    if v >= thr:
                        cnt += 1
        per.append(cnt); best.append(float(b))
    return {'total_anchors': int(total), 'per_target': per,
            'best_iou': best, 'pos_ratio': sum(per) / total,
            'starved': [i for i, c in enumerate(per) if c == 0]}

a = anchor_audit(TARGETS, [0, 90])
assert a['starved'] == [[t[2] for t in TARGETS].index(45.0)]
print('✅ 参考答案 2 通过')
print('   `half=6.0` 是一个安全的剪枝：更远的锚框与 4.5m 的框不可能有 0.5 的 IoU。')""" ),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：带 $z$ 门的 NMS

实现 `nms_with_z_gate(boxes, scores, iou_thr=0.5, z_gate=None)`：
`boxes` 每项是 `(cx, cy, w, l, theta, z_center, h)`。

规则：按分数降序，若与已保留框的 **BEV IoU** $\\ge$ `iou_thr`
**且** `|Δz| <=` `z_gate`（`z_gate=None` 表示不看 $z$），则抑制。

返回保留的下标（按分数降序）。"""),

    code("""def nms_with_z_gate(boxes, scores, iou_thr=0.5, z_gate=None):
    \"\"\"返回保留的下标 list。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# 场景：一块离地 2.2m 的牌（分数 0.55），正下方是地面标记（分数 0.90）
SCENE = [(30., -5.5, 0.8, 0.1, 0.0, 2.2, 0.8),
         (30., -5.5, 0.8, 0.1, 0.0, 0.0, 0.1)]
SCORES = np.array([0.55, 0.90])

k_no = nms_with_z_gate(SCENE, SCORES, z_gate=None)
k_yes = nms_with_z_gate(SCENE, SCORES, z_gate=0.5)
print(f'无 z 门: 保留 {k_no}（{len(k_no)} 个）  ← 牌被抑制')
print(f'有 z 门: 保留 {k_yes}（{len(k_yes)} 个）')
assert len(k_no) == 1 and k_no == [1], k_no
assert len(k_yes) == 2, k_yes
assert k_yes[0] == 1, '应当按分数降序返回'

# 真正重复的框仍然要被抑制
# 注意标志只有 0.1 m 厚（l=0.1 沿 x），所以偏移必须远小于 0.05 m 才算「重复」：
#   偏移 0.05 m = 半个边长 -> IoU 恰好 1/3，本来就不该被抑制
DUP = [(30.00, -5.5, 0.8, 0.1, 0.0, 2.20, 0.8),
       (30.01, -5.5, 0.8, 0.1, 0.0, 2.25, 0.8)]
print(f'\\n两个抖动框的 BEV IoU = {rotated_iou(DUP[0][:5], DUP[1][:5]):.4f}'
      f'（偏移 0.01 m，而框只有 0.1 m 厚）')
assert rotated_iou(DUP[0][:5], DUP[1][:5]) > 0.5
k_dup = nms_with_z_gate(DUP, np.array([0.9, 0.8]), z_gate=0.5)
assert len(k_dup) == 1, f'z 接近的重复框仍应被抑制，实得 {k_dup}'
print(f'同高度的重复框（Δz=0.05m < 门 0.5m）: 保留 {k_dup}（正确抑制）')

# z 门不能太小，否则同一目标的两个抖动框也不抑制了
k_tight = nms_with_z_gate(DUP, np.array([0.9, 0.8]), z_gate=0.01)
print(f'z 门设成 0.01m（< Δz=0.05m）: 保留 {k_tight}  ← **门太紧，重复框没被抑制**')
assert len(k_tight) == 2
print('\\n✅ 练习 3 通过：z 门要大于「同一目标的 z 抖动」、'
      '小于「不同目标的 z 间距」')
print('   本例里 0.5m 合适：牌与地面差 2.2m，而同一目标的 z 抖动只有 0.05m')""" ),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def nms_with_z_gate(boxes, scores, iou_thr=0.5, z_gate=None):
    order = list(np.argsort(np.asarray(scores))[::-1])
    keep = []
    for i in order:
        suppressed = False
        for j in keep:
            if rotated_iou(boxes[i][:5], boxes[j][:5]) < iou_thr:
                continue
            if z_gate is not None and abs(boxes[i][5] - boxes[j][5]) > z_gate:
                continue                       # z 上分开 -> 不算重复
            suppressed = True
            break
        if not suppressed:
            keep.append(int(i))
    return keep

assert len(nms_with_z_gate(SCENE, SCORES, z_gate=None)) == 1
assert len(nms_with_z_gate(SCENE, SCORES, z_gate=0.5)) == 2
print('✅ 参考答案 3 通过')
print('   注意 z 门是「不抑制」的条件而不是「抑制」的条件 ——')
print('   写反了会变成「只抑制 z 上分开的框」，那正好是最坏的行为。')""" ),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：热图头的可行性审计

实现 `heatmap_audit(class_sizes, grid, min_overlap=0.7)`，
`class_sizes` 是 `{类名: (w, l)}`（米），返回 `{类名: dict}`，每项含：

- `'cells'` —— `(l/grid, w/grid)`
- `'radius'` —— 高斯半径（格）
- `'eff_area'` —— $\\pi r^2$（格）
- `'sub_cell'` —— bool：是否有任一边小于 1 格
- `'degenerate'` —— bool：`eff_area < 1`（**没有软标签**）
- `'grid_for_area1'` —— 让 `eff_area >= 1` 所需的网格分辨率（米）"""),

    code("""def heatmap_audit(class_sizes, grid, min_overlap=0.7):
    \"\"\"返回 {类名: dict(cells, radius, eff_area, sub_cell, degenerate,
    grid_for_area1)}。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
CLASSES = {'car': (1.9, 4.5), 'pedestrian': (0.6, 0.6),
           'sign_bev': (0.1, 0.8), 'truck': (2.5, 10.0)}
au = heatmap_audit(CLASSES, GRID)
for name, v in au.items():
    assert set(v) == {'cells', 'radius', 'eff_area', 'sub_cell',
                      'degenerate', 'grid_for_area1'}

print(f\"{'类别':>12s} {'网格尺寸':>14s} {'半径':>8s} {'πr²':>8s} \"
      f\"{'亚格':>6s} {'退化':>6s} {'需要网格':>10s}\")
for name, v in au.items():
    print(f'{name:>12s} {f"{v["cells"][0]:.1f}×{v["cells"][1]:.1f}":>14s} '
          f'{v["radius"]:7.2f} {v["eff_area"]:7.2f} '
          f'{str(v["sub_cell"]):>6s} {str(v["degenerate"]):>6s} '
          f'{v["grid_for_area1"]:9.3f}m')

# ① 车与卡车不退化
assert au['car']['degenerate'] is False
assert au['truck']['degenerate'] is False
# ② 标志退化，且是亚格的
assert au['sign_bev']['degenerate'] is True
assert au['sign_bev']['sub_cell'] is True
# ③ 让标志不退化需要更细的网格
assert au['sign_bev']['grid_for_area1'] < GRID / 2, \\
    f"标志需要的网格应当细于 {GRID/2} m，实测 {au['sign_bev']['grid_for_area1']:.3f}"
print(f'\\n✅ 标志在 {GRID} m 网格上退化（πr² = '
      f'{au["sign_bev"]["eff_area"]:.3f}），')
print(f'   要让它有软标签需要网格细到 '
      f'{au["sign_bev"]["grid_for_area1"]:.3f} m')

# ④ 用那个网格重算，应当不再退化
au2 = heatmap_audit({'sign_bev': (0.1, 0.8)},
                    au['sign_bev']['grid_for_area1'])
assert au2['sign_bev']['degenerate'] is False
print(f'   用 {au["sign_bev"]["grid_for_area1"]:.3f} m 重算: '
      f'πr² = {au2["sign_bev"]["eff_area"]:.2f}（不再退化）')
print('\\n✅ 练习 4 通过：这个审计只依赖类别尺寸与网格，'
      '**在选架构之前就能算**')""" ),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def heatmap_audit(class_sizes, grid, min_overlap=0.7):
    out = {}
    for name, (w, l) in class_sizes.items():
        hg, wg = l / grid, w / grid
        r = gaussian_radius(hg, wg, min_overlap)
        eff = float(np.pi * r * r)
        # 二分找让 eff_area >= 1 的网格
        lo, hi = 1e-4, grid
        for _ in range(80):
            mid = (lo + hi) / 2
            rr = gaussian_radius(l / mid, w / mid, min_overlap)
            if np.pi * rr * rr >= 1.0:
                lo = mid          # 还能更粗
            else:
                hi = mid
        out[name] = {'cells': (hg, wg), 'radius': float(r), 'eff_area': eff,
                     'sub_cell': bool(min(hg, wg) < 1.0),
                     'degenerate': bool(eff < 1.0),
                     'grid_for_area1': float(lo)}
    return out

a = heatmap_audit({'sign_bev': (0.1, 0.8), 'car': (1.9, 4.5)}, 0.2)
assert a['sign_bev']['degenerate'] and not a['car']['degenerate']
print('✅ 参考答案 4 通过')
print('   二分的方向要想清楚：网格越**细**，格数越多，半径越大 ——')
print('   所以「还能更粗」时把下界往上移。')""" ),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) 旋转 IoU：用现成的（本课自己实现是为了看清语义）──
from mmcv.ops import boxes_iou3d_gpu, nms3d          # 或 iou3d_nms_utils
ious = boxes_iou3d_gpu(boxes_a, boxes_b)              # (N, M)
keep = nms3d(boxes, scores, iou_threshold=0.1)        # ← 3D 检测的 NMS 阈值普遍很低
#   ⚠️ 3D NMS 的阈值常取 0.1–0.25 而不是 2D 常用的 0.5 —— 因为「三个乘子」让
#      同一目标的两个候选框的 IoU 天然更低（模块 05）。抄 2D 的 0.5 会留下大量重复。

# ── 2) BEV NMS 的 z 门（第 4 节，零成本）──
#    mmdet3d 的 nms_bev 不看 z；如果你的类别里有「上下叠放」的（标志 vs 地面标记），
#    要么按类别分组 NMS，要么自己加门：
keep = [i for i in keep if not any(
    abs(boxes[i, 2] - boxes[j, 2]) <= Z_GATE and bev_iou(i, j) >= THR
    for j in kept_before)]

# ── 3) 角度：SECOND / CenterPoint 的做法 ──
#    回归 (sin, cos)，另加一个 direction classifier 判方向：
rot_sine = pred[..., 6:7]; rot_cosine = pred[..., 7:8]
theta = torch.atan2(rot_sine, rot_cosine)
dir_cls = pred_dir.argmax(-1)                        # 0/1
theta = theta + dir_cls * np.pi                      # 把方向补回来
#   ⚠️ 训练时 direction 的标签要用「θ 是否落在 [0, π)」，
#      而这个边界的定义（dir_offset）是一个真实的、容易搞错的超参数。

# ── 4) 上线前先跑两个审计（练习 2 与 4）──
#    a) anchor_audit：有没有类别/朝向的目标「一个正样本都拿不到」
#    b) heatmap_audit：有没有类别的 πr² < 1（没有软标签）
#    两者都只需要类别尺寸与网格配置，**不需要训练**。
```

> **落地顺序建议**：先跑 `heatmap_audit`（几行，立刻告诉你哪些类别在当前网格下退化），
> 再检查 3D NMS 的阈值是不是从 2D 抄来的 0.5，
> 最后才是给 BEV NMS 加 z 门（它只在你的类别里真有上下叠放时才需要）。"""),
]
