# -*- coding: utf-8 -*-
"""C73 模块 05 · 分割与 3D 评测。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的三个乘子、模块 04 的旋转框 IoU；"
                 "读过 C57（2D IoU 的尺度敏感性）与 C68 模块 04（分层门禁）更好"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_seg_eval.ipynb'
                       '（3D IoU 的三个乘子 / '
                       '<strong>允许平移误差从卡车 0.796 m 到标志 0.049 m——差 16 倍</strong> / '
                       '<strong>σ=0.2 m 时两种口径在标志上的分歧率 97.2%</strong> / '
                       'mIoU vs 频率加权：<strong>把稀有类从 0.20 提到 0.80，两个指标差 250 倍</strong> / '
                       '按距离与尺寸分层）'),
    ("核心参考", "Caesar et al., <em>nuScenes</em>（CVPR 2020，"
                 "中心距离匹配与 TP/ATE/ASE/AOE 分解）· "
                 "Geiger et al., <em>KITTI</em>（CVPR 2012，IoU 0.7/0.5）· "
                 "Behley et al., <em>SemanticKITTI</em>（ICCV 2019）· "
                 "Kirillov et al., <em>Panoptic Segmentation</em>（CVPR 2019）· "
                 "本课程 C57（2D 的同一问题）· C68 模块 04（分层门禁）· "
                 "C10（测量科学）"),
    ("预计时长", "读 45 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-multipliers-iou", "三个乘子在 IoU 上的确切形式", "".join([
        P("模块 00 提过 3D IoU 是三个因子的积。这里把它写成闭式，"
          "因为后面全部结论都从它推出来。"),
        P("两个<strong>同尺寸</strong>的轴对齐框，中心相距 $\\delta$，"
          "尺寸 $s=(s_1,\\dots,s_n)$："),
        MATH(r"\text{IoU} = \frac{q}{2-q},\qquad "
             r"q = \prod_{i=1}^{n}\Bigl(1-\frac{\delta_i}{s_i}\Bigr)_+"),
        P("于是「$\\text{IoU}\\ge\\tau$」等价于「$q\\ge\\frac{2\\tau}{1+\\tau}$」。"
          "<strong>$\\tau=0.5$ 时就是 $q\\ge2/3$。</strong>"),
        TABLE(["情形", "$q$ 的形式", "IoU $\\ge0.5$ 的条件"], [
            ["每轴相对误差都是 $e$", "$(1-e)^n$",
             "$e \\le 1-(2/3)^{1/n}$：<strong>2D 是 18.4%，3D 是 12.6%</strong>"],
            ["只有一个轴有误差 $\\delta$", "$1-\\delta/s_i$",
             "$\\delta \\le s_i/3$——<strong>只依赖那一个轴的边长</strong>"],
            ["各向同性误差 $\\lVert\\delta\\rVert=d$", "取决于方向",
             "<strong>最坏方向是最短轴</strong>"],
        ]),
        DUAL(
            "<strong>第二行是本模块最有用的一行：单轴误差的容差是 $s_i/3$。</strong>"
            "<em>$1-\\delta/s = 2/3 \\Rightarrow \\delta = s/3$——一个可以心算的结果</em>。"
            "<strong>所以对一块 0.1 m 厚的交通标志，沿厚度方向的容差是 0.033 m。</strong>",
            "<strong>而第一行解释了「为什么 3D 的阈值不能照搬 2D」。</strong>"
            "<em>同样要 IoU 0.5，2D 允许每轴 18.4% 的相对误差，3D 只允许 12.6%</em>。"
            "<strong>而更重要的是第二行：绝对容差 $s_i/3$ 与目标尺寸成正比，"
            "所以同一个阈值对不同尺寸的目标是完全不同的要求</strong>——"
            "<em>下一节把这个差别量出来。</em>",
        ),
    ])),

    # ============================================================== 2
    ("scale-sensitivity", "IoU 的尺度敏感性：从卡车 0.796 m 到标志 0.049 m", "".join([
        P("对四类目标反解「IoU $\\ge0.5$ 时允许的各向同性定位误差」："),
        TABLE(["类别", "尺寸（m）", "最短轴", "IoU$\\ge$0.5 允许的位移",
               "相对卡车"], [
            ["卡车", "$10\\times2.5\\times3.2$", "2.5", "<strong>0.796 m</strong>", "1.00×"],
            ["轿车", "$4.5\\times1.9\\times1.5$", "1.5", "0.459 m", "0.58×"],
            ["行人", "$0.6\\times0.6\\times1.7$", "0.6", "0.166 m", "0.21×"],
            ["<strong>交通标志</strong>", "$0.8\\times0.1\\times0.8$", "<strong>0.1</strong>",
             "<strong>0.049 m</strong>", "<strong>0.06×</strong>"],
        ]),
        DUAL(
            "<strong>16 倍的差距（0.796 vs 0.049 m），而阈值是同一个 0.5。</strong>"
            "<em>也就是说 mAP@0.5 对卡车问的是「定位到 0.8 m」，"
            "对交通标志问的是「定位到 5 厘米」</em>。"
            "<strong>而 5 厘米在 50 m 处对任何车载传感器都不可达</strong>"
            "（<em>C72 模块 03 量到最好的补法是 ±0.68 m</em>）。",
            "<strong>所以「IoU ≥ 0.5」对薄小目标不是一个高标准，是一个<em>不可达</em>的标准。</strong>"
            "<em>而不可达的标准会让指标失去区分能力："
            "所有方法都在 0 附近，于是改进看不出来</em>。"
            "<strong>这与 C67 模块 01 的「可判定性阶梯」是同一件事——"
            "先判断这个问题能不能被回答，再回答。</strong>"
            "<em>而这也解释了 KITTI 为什么对车用 0.7、对行人和骑车人用 0.5："
            "它是在用阈值补偿尺寸差异。而那只是一个粗糙的补偿——下一节给出更彻底的做法。</em>",
        ),
        CALLOUT("intuition",
                "<strong>C57 在 2D 里量过同一件事，而 3D 更严重。</strong>"
                "<em>2D 的 IoU 是两个乘子，3D 是三个；"
                "而「厚度」这个维度在 2D 投影里根本不存在</em>——"
                "<strong>交通标志在图像上是一个 $0.8\\times0.8$ 的近方形，"
                "在 3D 里却是一个 $0.8\\times0.1\\times0.8$ 的薄片。</strong>"
                "<em>所以「2D 检测做得挺好，换成 3D 指标就崩了」是一个可以预期的结果，"
                "而不是模型退化。</em>"),
    ])),

    # ============================================================== 3
    ("disagreement", "本模块的核心：两种口径在薄小目标上几乎完全分歧", "".join([
        P("给定一个各向同性的定位误差（$\\sigma$ 为标准差），"
          "分别用「IoU $\\ge0.5$」与「中心距离 $\\le2$ m」判断是否命中。"
          "<strong>两者的分歧率是这一节的全部内容。</strong>"),
        TABLE(["类别", "$\\sigma$", "IoU$\\ge$0.5 的命中率",
               "中心距离$\\le$2 m 的命中率", "<strong>分歧率</strong>"], [
            ["卡车", "0.2 m", "0.999", "1.000", "0.001"],
            ["轿车", "0.2 m", "0.896", "1.000", "0.104"],
            ["行人", "0.2 m", "0.196", "1.000", "<strong>0.804</strong>"],
            ["<strong>交通标志</strong>", "0.2 m", "<strong>0.028</strong>", "1.000",
             "<strong>0.972</strong>"],
            ["卡车", "0.5 m", "0.645", "0.999", "0.354"],
            ["交通标志", "0.5 m", "0.002", "0.999", "0.997"],
        ]),
        CALLOUT("danger",
                "<strong>在 $\\sigma=0.2$ m（一个现实的 LiDAR 定位精度）下，"
                "IoU-0.5 会拒掉 97.2% 被中心距离-2 m 接受的标志检测。</strong>"
                "<em>两个口径在这一类目标上几乎完全不一致</em>——"
                "<strong>所以「用哪个指标」不是报告风格问题，"
                "它决定了同一个模型是「基本可用」还是「几乎全错」。</strong>"),
        DUAL(
            "<strong>而分歧率随目标变小单调上升：卡车 0.001 → 轿车 0.104 → "
            "行人 0.804 → 标志 0.972。</strong>"
            "<em>这不是两个指标「哪个更对」的问题——"
            "它们量的是不同的东西</em>："
            "<strong>IoU 量「框重合得多好」，中心距离量「位置对不对」。</strong>"
            "<em>而对一块薄片，「框重合」这个概念本身就很脆弱。</em>",
            "<strong>那什么时候该用哪个？本课给出的判据是：</strong>"
            "<em>看下游<strong>怎么用</strong>这个框</em>。"
            "① 下游要<strong>框的形状</strong>（碰撞检测、可行驶区域）→ 用 IoU；"
            "② 下游只要<strong>位置与类别</strong>（TSR：读出限速值 + 距离）→ 用中心距离；"
            "③ 下游要<strong>朝向</strong>（切入预测）→ 单独报 AOE（模块 04 第 3b 节）。"
            "<strong>而 TSR 属于第 ②——所以对它用 IoU 是口径选错了。</strong>",
        ),
    ])),

    # ============================================================== 3b
    ("annotation-ceiling", "口径的天花板：标注噪声决定的 AP 上界", "".join([
        P("上一节比较的是两个口径。"
          "<strong>而更根本的问题是：在给定的标注噪声下，"
          "<em>一个完美的模型</em>最高能拿多少分？</strong>"),
        P("实验：让模型预测<strong>恰好等于真实位置</strong>，"
          "而「真值」标注本身带 $\\sigma_{\\text{ann}}$ 的噪声。"
          "算 IoU $\\ge0.5$ 的命中率——<strong>这就是这个口径的天花板</strong>："),
        TABLE(["类别", "$\\sigma_{\\text{ann}}{=}0.02$ m",
               "$0.05$ m", "$0.10$ m", "$0.20$ m"], [
            ["卡车", "1.000", "1.000", "1.000", "0.999"],
            ["轿车", "1.000", "1.000", "1.000", "0.896"],
            ["行人", "1.000", "0.991", "0.677", "0.200"],
            ["<strong>交通标志</strong>", "0.871", "<strong>0.392</strong>",
             "<strong>0.135</strong>", "<strong>0.028</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>在 5 厘米的标注噪声下，一个<em>完美</em>的模型在交通标志上的 "
                "AP@IoU0.5 上界只有 0.392。</strong>"
                "<em>而同一张表里卡车与轿车都是 1.000</em>。"
                "<strong>也就是说：标志那一列量的不是模型能力，是标注噪声。</strong>"),
        P("而中心距离口径下，同样的实验给出的上界<strong>对四个类别都恒为 1.000</strong>"
          "（$\\sigma_{\\text{ann}}$ 到 0.2 m 都如此）——"
          "<em>因为 5–20 厘米的标注噪声远小于 2 m 的阈值</em>。"),
        DUAL(
            "<strong>把这个结果与第 2 节的容差对上，就完全闭合了：</strong>"
            "<em>标志的 IoU-0.5 各向同性容差是 <strong>0.049 m</strong>，"
            "而典型的标注噪声是 <strong>0.05 m</strong>——比值 <strong>0.98×</strong></em>。"
            "<strong>容差与标注噪声几乎相等，所以这个口径的输出基本上是标注噪声的函数。</strong>"
            "<em>四个类别的比值分别是：卡车 15.93× · 轿车 9.18× · 行人 3.32× · 标志 0.98×</em>。",
            "<strong>这给出一条可以直接用的设计判据：</strong>"
            "$$\\frac{\\text{容差}}{\\sigma_{\\text{ann}}} = \\frac{s_{\\min}/3}"
            "{\\sigma_{\\text{ann}}} \\gtrsim 3$$"
            "<em>小于 3 就说明这个口径在这个类别上没有足够的信噪比</em>。"
            "<strong>而它的三条修法是：换口径（中心距离）· 降阈值（$\\tau$ 从 0.5 到 0.25）· "
            "或提高标注精度</strong>——"
            "<em>而第三条通常最贵，且对薄目标有物理下限（标注者也只能看到几个点）</em>。"
            "<strong>这与 C10 的「测量的分辨率必须优于要测的效应」是同一条原则。</strong>",
        ),
    ])),

    # ============================================================== 4
    ("center-distance", "中心距离口径：nuScenes 的做法与它的代价", "".join([
        P("nuScenes 的检测指标用<strong>中心距离</strong>做匹配"
          "（四档阈值 0.5 / 1 / 2 / 4 m），并把误差拆成独立的分量上报。"),
        TABLE(["它做对了什么", "怎么做", "代价"], [
            ["<strong>匹配判据与尺寸解耦</strong>",
             "中心距离是一个绝对阈值，不含三个乘子",
             "<em>对大目标偏松</em>：2 m 对一辆 10 m 的卡车几乎无约束"],
            ["<strong>把误差分解上报</strong>",
             "ATE（平移）/ ASE（尺寸）/ AOE（朝向）/ AVE / AAE 各自独立",
             "指标变多，<em>不再是一个数</em>"],
            ["<strong>四档阈值</strong>", "0.5/1/2/4 m 的 AP 取平均",
             "<em>阈值仍然是人定的常数</em>"],
        ]),
        DUAL(
            "<strong>「把误差分解」这一条是关键，而它比换阈值更重要。</strong>"
            "<em>IoU 把平移、尺寸、朝向三种误差压成一个数，"
            "而模块 04 第 3b 节量到「压缩比」完全取决于长宽比"
            "（方形目标的朝向根本不进 IoU）</em>。"
            "<strong>分解之后，「我们的尺寸估计变好了但朝向变差了」"
            "这件事才能被看见。</strong>",
            "<strong>而中心距离的代价必须说清：它对大目标太松。</strong>"
            "<em>2 m 对一辆 10 m 长的卡车意味着「差半个车身也算命中」</em>。"
            "<strong>所以正确的做法不是「用中心距离替代 IoU」，"
            "而是「按目标类别选口径」</strong>——"
            "<em>大而规则的目标用 IoU（它此时是可达的、且下游确实要形状），"
            "小而薄的目标用中心距离 + 独立的尺寸/朝向指标</em>。"
            "<strong>而这正是 nuScenes 与 KITTI 并存的原因："
            "它们服务于不同的下游。</strong>",
        ),
    ])),

    # ============================================================== 4b
    ("threshold-sweep", "阈值扫描：降阈值能救回多少", "".join([
        P("既然 $\\tau=0.5$ 对薄目标不可达，那降低它行不行？"
          "<strong>把 $\\sigma_{\\text{ann}}=0.05$ m 下的天花板按 $\\tau$ 扫一遍：</strong>"),
        TABLE(["类别", "$\\tau{=}0.1$", "$\\tau{=}0.25$", "$\\tau{=}0.5$",
               "$\\tau{=}0.7$"], [
            ["卡车", "1.000", "1.000", "1.000", "1.000"],
            ["轿车", "1.000", "1.000", "1.000", "1.000"],
            ["行人", "1.000", "1.000", "0.993", "0.682"],
            ["<strong>交通标志</strong>", "<strong>0.890</strong>",
             "<strong>0.736</strong>", "0.391", "0.139"],
        ]),
        DUAL(
            "<strong>降到 $\\tau=0.25$ 能把标志的天花板从 0.391 提到 0.736，"
            "降到 0.1 是 0.890。</strong>"
            "<em>所以「降阈值」确实有效，而它比换口径的改动小得多</em>。"
            "<strong>但它有一个代价：$\\tau$ 越低，"
            "指标对「框画得对不对」就越不敏感</strong>——"
            "<em>$\\tau=0.1$ 时几乎只在问「有没有大致重合」，"
            "那与中心距离口径的差别已经不大了。</em>",
            "<strong>而更重要的是：单一阈值对不同类别本来就该不同。</strong>"
            "<em>上表里卡车与轿车在 $\\tau=0.7$ 都还是 1.000，"
            "说明它们的天花板远没有被触到——"
            "对它们用 0.7 是合适的，甚至可以更高</em>。"
            "<strong>所以正确的做法是<em>按类别定阈值</em>，"
            "并把「该类别在当前标注噪声下的天花板」一起报出来。</strong>"
            "<em>KITTI 的「车 0.7 / 行人 0.5」正是这个做法的一个粗糙版本；"
            "而本节给出的是定阈值的<strong>依据</strong>——"
            "让天花板保持在 0.9 以上。</em>",
        ),
        CALLOUT("intuition",
                "<strong>一条可以立刻做的检查：算出你每个类别的「天花板」。</strong>"
                "<em>做法是把预测直接设成真值、再给真值加上你估计的标注噪声，"
                "然后跑一遍你的评测代码</em>。"
                "<strong>它不需要模型、不需要训练，跑一次几秒钟；"
                "而它告诉你「这个指标最高能到多少」。</strong>"
                "<em>如果某个类别的天花板低于 0.9，那么该类别的所有排名都不可信。</em>"),
    ])),

    # ============================================================== 5
    ("segmentation-metrics", "分割指标：mIoU 与频率加权差 250 倍", "".join([
        P("点云语义分割的标准指标是 mIoU（各类 IoU 的<strong>等权</strong>平均）。"
          "<strong>而「等权」在类别频率差三个数量级时会产生一个极端的后果。</strong>"),
        P("取一个贴近真实的频率分布（地面 60%、车 8%、"
          "<strong>标志 0.1%</strong>、其余 31.9%）："),
        TABLE(["类别", "频率", "IoU", "在 mIoU 里的权重", "在频率加权里的权重"], [
            ["地面", "60.0%", "0.95", "25%", "60.0%"],
            ["车", "8.0%", "0.75", "25%", "8.0%"],
            ["<strong>标志</strong>", "<strong>0.1%</strong>", "0.20",
             "<strong>25%</strong>", "<strong>0.1%</strong>"],
            ["其他", "31.9%", "0.60", "25%", "31.9%"],
            ["<strong>合计</strong>", "—", "—",
             "<strong>mIoU = 0.6250</strong>",
             "<strong>加权 = 0.8216</strong>"],
        ]),
        H3("把标志的 IoU 从 0.20 提到 0.80"),
        TABLE(["标志 IoU", "mIoU", "mIoU 的增量", "频率加权", "加权的增量"], [
            ["0.20", "0.6250", "—", "0.8216", "—"],
            ["0.40", "0.6750", "+0.0500", "0.8218", "+0.00020"],
            ["0.60", "0.7250", "+0.1000", "0.8220", "+0.00040"],
            ["<strong>0.80</strong>", "<strong>0.7750</strong>",
             "<strong>+0.1500</strong>", "0.8222", "<strong>+0.00060</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>同一个改进：mIoU 涨 0.1500，频率加权涨 0.0006——差 250 倍。</strong>"
                "<em>所以「选哪个指标」直接决定了「改进稀有类值不值得做」</em>。"
                "<strong>而这两个指标都不是错的，它们回答的是不同的问题：</strong>"
                "<em>mIoU 问「各类都做得怎样」，频率加权问「随机取一个点，标对的概率」。</em>"),
        DUAL(
            "<strong>而对自动驾驶，两个都不是真正想问的。</strong>"
            "<em>真正想问的是「按安全后果加权，做得怎样」——"
            "而一块被漏掉的限速牌的后果远大于 1000 个被标错的地面点</em>。"
            "<strong>所以频率加权是明确错的口径（它按频率而不是按后果加权），"
            "而 mIoU 只是一个粗糙的代理</strong>——"
            "<em>它的隐含假设是「所有类别同等重要」，而那至少比「按频率重要」更接近真相。</em>",
            "<strong>本课的建议是三条一起报：</strong>"
            "① <strong>mIoU</strong>（可比性，别人都在报）；"
            "② <strong>逐类 IoU 表</strong>（<em>唯一真正有信息量的东西</em>）；"
            "③ <strong>关键类别的召回</strong>（<em>按下游后果挑出来的那几类</em>）。"
            "<em>而绝不要只报一个数——因为上表说明「一个数」可以被 250 倍地稀释</em>。"
            "<strong>这与 C68 模块 04 的分层门禁、C10 的「聚合会掩盖异质」是同一条纪律。</strong>",
        ),
    ])),

    # ============================================================== 6
    ("panoptic", "点级、实例级、全景：三个层次问的是不同问题", "".join([
        TABLE(["层次", "指标", "它能抓到什么", "它抓不到什么"], [
            ["<strong>点级（语义分割）</strong>", "mIoU / 逐类 IoU",
             "「这个点是什么类」",
             "<strong>两辆挨着的车被当成一辆</strong>——点级全对，实例全错"],
            ["<strong>实例级（检测/实例分割）</strong>", "mAP / 中心距离 AP",
             "「有几个目标、各在哪」",
             "<em>不管「没被任何实例覆盖的点」是什么</em>"],
            ["<strong>全景（panoptic）</strong>",
             "PQ = SQ × RQ（分割质量 × 识别质量）",
             "<strong>两者兼顾，且把「重复检测」与「分割不准」分开</strong>",
             "<em>PQ 把 stuff 与 thing 混在一个数里；仍需分层看</em>"],
        ]),
        DUAL(
            "<strong>PQ 的分解形式值得记，因为它体现了本课反复出现的原则：</strong>"
            "$\\text{PQ} = \\underbrace{\\frac{\\sum_{TP}\\text{IoU}}{|TP|}}_{\\text{SQ：分割多准}}"
            "\\times\\underbrace{\\frac{|TP|}{|TP|+\\frac12|FP|+\\frac12|FN|}}_{\\text{RQ：找得多全}}$"
            "<em>——把「找到没有」与「找得准不准」拆成两个可以分别改进的因子</em>。",
            "<strong>而 PQ 的匹配判据仍然是 IoU &gt; 0.5</strong>，"
            "<em>所以第 2–3 节的尺度敏感性在这里完全适用</em>："
            "<strong>对薄小目标，PQ 的 RQ 部分会被 IoU 阈值压到接近 0，"
            "而那不反映真实的识别能力。</strong>"
            "<em>所以在 TSR 语境里，即使用全景指标也要把匹配判据换成中心距离</em>——"
            "<strong>结论与第 3 节一致：口径的选择要跟着下游，而不是跟着惯例。</strong>",
        ),
    ])),

    # ============================================================== 7
    ("stratify", "分层报告：这一层唯一真正有用的纪律", "".join([
        P("本课五个模块量出的所有问题，都有一个共同特征："
          "<strong>它们在总体指标上表现为「差一点」，"
          "而在某一个分层上表现为「完全不行」。</strong>"),
        TABLE(["模块", "问题", "在总体指标上", "在哪个分层上可见"], [
            ["01", "「最少 N 个点」是常数阈值", "整体召回略低",
             "<strong>按距离分层</strong>（密度衰减 520 倍）"],
            ["02", "全局 max-pool 只看 24 个点", "加点数没收益",
             "<strong>按目标点数分层</strong>"],
            ["03", "标志碎成 2 个不连通分量", "标志类 AP 低",
             "<strong>按目标厚度/连通性分层</strong>"],
            ["04", "45° 的目标 0 个正锚", "整体 mAP 略低",
             "<strong>按朝向分层</strong>"],
            ["04", "BEV NMS 抑制掉上下叠放的目标", "标志召回低",
             "<strong>按「是否有上下叠放」分层</strong>"],
            ["05", "mIoU 被稀有类稀释", "看起来还不错",
             "<strong>逐类表</strong>"],
        ]),
        DUAL(
            "<strong>六行里没有一行能靠「看总体指标」发现。</strong>"
            "<em>而它们都能靠一次分层报告发现——而分层的维度不是随便选的，"
            "它由「你怀疑什么」决定</em>。"
            "<strong>所以本课的最后一条纪律是："
            "每量出一个机制，就顺手加一个对应的分层维度。</strong>",
            "<strong>而本课给出的分层维度清单是：</strong>"
            "<em>距离（密度衰减）· 目标点数（临界点集）· "
            "厚度与长宽比（IoU 的三个乘子）· 朝向（锚框离散化）· "
            "类别（频率稀释）· 是否上下叠放（BEV NMS）</em>。"
            "<strong>六个维度，每一个都对应本课某一节量出的一个具体机制</strong>——"
            "<em>而这正是 C68 模块 04 说的「门禁要按层判」在 3D 感知上的落地形式。</em>",
        ),
    ])),

    # ============================================================== 7b
    ("one-number", "为什么不能只报一个数", "".join([
        P("本课量出的每一个问题都有同一个形状："
          "<strong>在聚合指标上是「差一点」，在某个分层上是「完全不行」。</strong>"
          "而这不是巧合——它是聚合这个操作的性质。"),
        TABLE(["聚合方式", "它的隐含假设", "本课量到的稀释倍数"], [
            ["<strong>mIoU</strong>（等权）", "所有类别同等重要",
             "<em>稀有类的改进被摊成 $1/K$</em>（$K$ = 类别数）"],
            ["<strong>频率加权 IoU</strong>", "按点数重要",
             "<strong>250×</strong>——把稀有类从 0.20 提到 0.80 只涨 0.0006"],
            ["<strong>总体 mAP</strong>", "所有目标同等重要",
             "<em>「45° 的目标 0 个正锚」在总 mAP 上只是「略低」</em>（模块 04）"],
            ["<strong>整体召回</strong>", "所有距离同等重要",
             "<em>而密度衰减 520 倍，远处的召回被近处的样本量淹没</em>（模块 01）"],
        ]),
        DUAL(
            "<strong>四行的共同点是：聚合的权重与「后果的权重」不一致。</strong>"
            "<em>而这不是可以靠「换一个更好的聚合方式」解决的——"
            "任何单一数字都要选一组权重，而没有一组权重对所有问题都对</em>。"
            "<strong>所以本课的立场是：聚合指标用于<em>可比性</em>，"
            "分层报告用于<em>诊断</em>，两者不能互相替代。</strong>",
            "<strong>而分层不是免费的：桶越细，每个桶的样本越少、方差越大。</strong>"
            "<em>练习 4 里 <code>min_n=5</code> 不是可选项——"
            "一个 3 样本的桶报出 0.000 的召回，会让人去修一个不存在的问题</em>。"
            "<strong>所以分层维度要按「你怀疑什么」来选，而不是穷举</strong>——"
            "<em>而本课给出的六个维度，每一个都对应某一节量出的一个具体机制，"
            "所以它们是有依据的假设而不是穷举</em>。"
            "（<strong>与 C10 的「样本量与置信区间」、"
            "C68 模块 04 的「分层门禁」是同一条纪律。</strong>）",
        ),
    ])),

    # ============================================================== 8
    ("checklist", "本模块的清单", "".join([
        OL([
            "<strong>报 IoU 阈值时同时报它对每个类别意味着多少绝对容差</strong>"
            "（第 1–2 节）：$s_i/3$，<em>而这在四个类别上差 16 倍</em>",
            "<strong>先算每个类别的「天花板」</strong>（第 3b 节）——"
            "<em>预测设成真值 + 标注噪声，跑一遍评测；低于 0.9 就说明该类别的排名不可信</em>",
            "<strong>按类别定 IoU 阈值，依据是「让天花板保持在 0.9 以上」</strong>（第 4b 节）",
            "<strong>按下游用途选匹配口径</strong>（第 3–4 节）——"
            "要形状用 IoU，只要位置用中心距离；"
            "<em>而 TSR 属于后者</em>",
            "<strong>把误差分解上报</strong>（平移/尺寸/朝向），"
            "<em>不要让 IoU 把它们压成一个数</em>",
            "<strong>绝不只报 mIoU</strong>（第 5 节）——"
            "<em>同一个改进在 mIoU 与频率加权上差 250 倍</em>；"
            "逐类表是唯一真正有信息量的东西",
            "<strong>用全景指标时也要检查匹配判据</strong>（第 6 节）——"
            "PQ 的 RQ 部分同样受 IoU 阈值支配",
            "<strong>按本课的六个维度分层</strong>（第 7 节）："
            "距离 · 点数 · 厚度/长宽比 · 朝向 · 类别 · 是否上下叠放",
        ]),
        CALLOUT("paper",
                "<strong>如果只做一条，做第 2 条。</strong>"
                "<em>「口径选错」不是一个精度问题，它会让指标完全失去区分能力</em>——"
                "<strong>第 3 节量到：在 $\\sigma=0.2$ m 下，"
                "IoU-0.5 拒掉 97.2% 被中心距离接受的标志检测。</strong>"
                "<em>在这种情形下，任何模型改进都看不出来，"
                "而团队会误以为「这个任务很难」。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 05 · 分割与 3D 评测

这个 notebook 把「评测口径」当成一个可以计算的对象，量四件事：

1. **IoU 的闭式**：$\\text{IoU} = q/(2-q)$，$q=\\prod(1-\\delta_i/s_i)$；
   于是**单轴容差恰好是 $s_i/3$**。
2. **尺度敏感性**：IoU≥0.5 的各向同性容差从卡车 **0.796 m** 到标志 **0.049 m**（差 16 倍）。
3. **两种口径的分歧率**：$\\sigma{=}0.2$ m 时，IoU-0.5 拒掉 **97.2%** 被中心距离-2 m 接受的标志。
4. **口径的天花板**：5 cm 标注噪声下，一个**完美模型**在标志上的 AP@IoU0.5 上界只有 **0.392**
   （而中心距离口径下是 1.000）。

> 心智模型：**指标不是「测量工具」，它是一个有分辨率上限的测量工具。
> 上限低于你要测的效应时，排名就是噪声。**"""),

    md("""## 0 · 环境与四类目标"""),

    code("""import numpy as np

print('numpy', np.__version__)

CLASSES = {
    'truck':      (10.0, 2.5, 3.2),
    'car':        ( 4.5, 1.9, 1.5),
    'pedestrian': ( 0.6, 0.6, 1.7),
    'sign':       ( 0.8, 0.1, 0.8),      # 又小又薄 —— 本课的主角
}
for n, s in CLASSES.items():
    print(f'  {n:12s} {s}  最短轴 {min(s):.2f} m')"""),

    md("""## 1 · IoU 的闭式，与「单轴容差 = $s/3$」"""),

    code("""def iou_same_size(size, delta):
    '''同尺寸轴对齐框，中心相距 delta 时的 IoU（维数由 size 决定）。'''
    s = np.asarray(size, float); d = np.abs(np.asarray(delta, float))
    q = np.prod(np.maximum(1.0 - d / s, 0.0))
    return q / (2.0 - q) if q > 0 else 0.0

def iou_from_q(q):
    return q / (2.0 - q) if q > 0 else 0.0

# ① 闭式与直接算交并比一致
def iou_bruteforce(size, delta):
    s = np.asarray(size, float); d = np.abs(np.asarray(delta, float))
    inter = np.prod(np.maximum(s - d, 0.0)); vol = np.prod(s)
    den = 2 * vol - inter
    return inter / den if den > 0 else 0.0

rng = np.random.default_rng(0)
worst = 0.0
for _ in range(2000):
    s = rng.uniform(0.1, 10.0, 3)
    d = rng.uniform(0.0, 3.0, 3)
    worst = max(worst, abs(iou_same_size(s, d) - iou_bruteforce(s, d)))
print(f'闭式 q/(2−q) 与直接算的最大差 = {worst:.3e}')
assert worst < 1e-12
print('✅ IoU = q/(2−q)，其中 q = ∏(1 − δᵢ/sᵢ)₊\\n')

# ② 单轴容差恰好是 s/3
print(f\"{'类别':>12s} {'最短轴':>8s} {'该轴 IoU=0.5 的容差':>20s} {'s/3':>9s}\")
for n, s in CLASSES.items():
    ax = int(np.argmin(s))
    lo, hi = 0.0, float(s[ax])
    for _ in range(60):
        mid = (lo + hi) / 2
        dd = [0.0, 0.0, 0.0]; dd[ax] = mid
        if iou_same_size(s, dd) >= 0.5:
            lo = mid
        else:
            hi = mid
    print(f'{n:>12s} {s[ax]:7.2f}m {lo:19.4f}m {s[ax]/3:8.4f}m')
    assert abs(lo - s[ax] / 3) < 1e-6, (n, lo, s[ax] / 3)
print('\\n✅ **单轴容差恰好是 s/3** —— 因为 1 − δ/s = 2/3 ⇒ δ = s/3')

# ③ 每轴等相对误差时：2D 18.4% vs 3D 12.6%
for n_dim in [2, 3]:
    e = 1 - (2/3) ** (1/n_dim)
    got = iou_same_size((1.,)*n_dim, (e,)*n_dim)
    print(f'  {n_dim}D 每轴允许的相对误差 = {e:.4f}（{e:.1%}），代回 IoU = {got:.6f}')
    assert abs(got - 0.5) < 1e-9"""),

    md("""## 2 · 尺度敏感性：16 倍的容差差距"""),

    code("""def isotropic_tolerance(size, thr=0.5):
    '''IoU >= thr 时允许的各向同性位移范数。'''
    lo, hi = 0.0, 20.0
    for _ in range(80):
        mid = (lo + hi) / 2
        d = (mid / np.sqrt(len(size)),) * len(size)
        if iou_same_size(size, d) >= thr:
            lo = mid
        else:
            hi = mid
    return lo

print(f\"{'类别':>12s} {'尺寸':>22s} {'最短轴':>8s} {'IoU>=0.5 容差':>14s} {'相对卡车':>9s}\")
tol = {n: isotropic_tolerance(s) for n, s in CLASSES.items()}
base = tol['truck']
for n, s in CLASSES.items():
    print(f'{n:>12s} {str(s):>22s} {min(s):7.2f}m {tol[n]:13.3f}m {tol[n]/base:8.2f}×')

ratio = tol['truck'] / tol['sign']
print(f'\\n卡车 / 标志 = **{ratio:.1f} 倍**，而阈值是同一个 0.5')
assert ratio > 10, f'差距应超过 10 倍，实测 {ratio:.1f}'
print('✅ mAP@0.5 对卡车问「定位到 0.8 m」，对标志问「定位到 5 厘米」')

# 沿最薄轴时更极端
print(f'\\n沿最薄轴 δ=0.1 m 时的 IoU：')
for n, s in CLASSES.items():
    ax = int(np.argmin(s))
    dd = [0.0, 0.0, 0.0]; dd[ax] = 0.1
    print(f'  {n:12s} {iou_same_size(s, dd):.4f}')
assert iou_same_size(CLASSES['sign'], (0., 0.1, 0.)) == 0.0
print('  → 标志沿厚度方向偏 0.1 m 就完全脱靶（IoU = 0）')"""),

    md("""## 3 · 两种口径的分歧率"""),

    code("""def hit_rates(size, sigma, n=20000, iou_thr=0.5, dist_thr=2.0, seed=0):
    d = np.random.default_rng(seed).normal(0, sigma, (n, 3))
    by_iou = np.array([iou_same_size(size, dd) >= iou_thr for dd in d])
    by_dist = np.linalg.norm(d, axis=1) <= dist_thr
    return {'iou': float(by_iou.mean()), 'dist': float(by_dist.mean()),
            'disagree': float((by_iou != by_dist).mean())}

print(f\"{'类别':>12s} {'σ':>6s} {'IoU>=0.5':>10s} {'中心距离<=2m':>13s} {'分歧率':>9s}\")
dis = {}
for sg in [0.2, 0.5]:
    for n, s in CLASSES.items():
        h = hit_rates(s, sg)
        dis[(n, sg)] = h['disagree']
        print(f'{n:>12s} {sg:6.2f} {h["iou"]:10.3f} {h["dist"]:12.3f} '
              f'{h["disagree"]:8.3f}')
    print()

# 分歧率随目标变小单调上升
order = ['truck', 'car', 'pedestrian', 'sign']
d02 = [dis[(n, 0.2)] for n in order]
assert d02 == sorted(d02), f'分歧率应随目标变小单调上升：{d02}'
assert dis[('sign', 0.2)] > 0.9
print(f'σ=0.2 m 时的分歧率: ' +
      ' < '.join(f'{n} {dis[(n,0.2)]:.3f}' for n in order))
print(f'\\n✅ 标志上分歧 **{dis[("sign",0.2)]:.1%}** —— 两个口径几乎完全不一致')
print('   IoU 量「框重合得多好」，中心距离量「位置对不对」——对薄片，前者本身就脆弱')"""),

    md("""## 3b · 口径的天花板：完美模型能拿多少分"""),

    code("""def metric_ceiling(size, sigma_ann, criterion='iou', thr=0.5,
                   n=20000, seed=1):
    '''模型预测 = 真实位置，而「真值」标注带 sigma_ann 噪声。返回命中率上界。'''
    d = np.random.default_rng(seed).normal(0, sigma_ann, (n, 3))
    if criterion == 'iou':
        return float(np.mean([iou_same_size(size, dd) >= thr for dd in d]))
    if criterion == 'center':
        return float((np.linalg.norm(d, axis=1) <= thr).mean())
    raise ValueError(criterion)

SIGMAS = [0.02, 0.05, 0.10, 0.20]
print('IoU >= 0.5 口径下、完美模型的 AP 上界：')
print(f\"{'类别':>12s} \" + ''.join(f'σ={s}m'.rjust(11) for s in SIGMAS))
ceil_iou = {}
for n, s in CLASSES.items():
    row = [metric_ceiling(s, sa, 'iou', 0.5) for sa in SIGMAS]
    ceil_iou[n] = dict(zip(SIGMAS, row))
    print(f'{n:>12s} ' + ''.join(f'{v:10.3f} ' for v in row))

print('\\n中心距离 <= 2 m 口径下的同一个上界：')
print(f\"{'类别':>12s} \" + ''.join(f'σ={s}m'.rjust(11) for s in SIGMAS))
for n, s in CLASSES.items():
    row = [metric_ceiling(s, sa, 'center', 2.0) for sa in SIGMAS]
    print(f'{n:>12s} ' + ''.join(f'{v:10.3f} ' for v in row))
    assert all(v > 0.99 for v in row), '中心距离口径的上界应恒为 1'

# ★ 核心断言
assert ceil_iou['truck'][0.05] > 0.99 and ceil_iou['car'][0.05] > 0.99
assert ceil_iou['sign'][0.05] < 0.45, ceil_iou['sign'][0.05]
print(f'\\n✅ 5 cm 标注噪声下：卡车/轿车的上界 1.000，'
      f'而**标志只有 {ceil_iou["sign"][0.05]:.3f}**')
print('   → 标志那一列量的不是模型能力，是标注噪声')

# 容差 / 标注噪声 的比值
SIGMA_ANN = 0.05
print(f'\\n{"类别":>12s} {"容差":>10s} {"σ_ann":>8s} {"比值":>8s} {"判据(>=3)":>10s}')
for n, s in CLASSES.items():
    r = tol[n] / SIGMA_ANN
    print(f'{n:>12s} {tol[n]:9.3f}m {SIGMA_ANN:7.2f}m {r:7.2f}× '
          f'{"OK" if r >= 3 else "**不足**":>10s}')
assert tol['sign'] / SIGMA_ANN < 1.2, '标志的容差与标注噪声应当几乎相等'
print(f'\\n✅ 标志的比值 {tol["sign"]/SIGMA_ANN:.2f}× —— '
      '容差与标注噪声几乎相等，信噪比不足')
print('   判据：容差 / σ_ann >= 3；小于 3 就说明这个口径在该类别上不可信')"""),

    md("""## 4 · 降阈值能救回多少"""),

    code("""TAUS = [0.1, 0.25, 0.5, 0.7]
print(f'σ_ann = {SIGMA_ANN} m 下，按 τ 扫描完美模型的上界：\\n')
print(f\"{'类别':>12s} \" + ''.join(f'τ={t}'.rjust(9) for t in TAUS))
sweep = {}
for n, s in CLASSES.items():
    row = [metric_ceiling(s, SIGMA_ANN, 'iou', t) for t in TAUS]
    sweep[n] = dict(zip(TAUS, row))
    print(f'{n:>12s} ' + ''.join(f'{v:8.3f} ' for v in row))

# 降阈值确实有效
assert sweep['sign'][0.25] > 2 * sweep['sign'][0.7]
print(f'\\n标志: τ=0.7 → {sweep["sign"][0.7]:.3f}，'
      f'τ=0.5 → {sweep["sign"][0.5]:.3f}，'
      f'τ=0.25 → {sweep["sign"][0.25]:.3f}，'
      f'τ=0.1 → {sweep["sign"][0.1]:.3f}')

# 而卡车/轿车在 τ=0.7 都还没触到天花板
assert sweep['truck'][0.7] > 0.99 and sweep['car'][0.7] > 0.99
print(f'而卡车与轿车在 τ=0.7 仍是 1.000 —— **它们的天花板远没被触到**')

# 按「天花板 >= 0.9」定阈值
print(f'\\n按「天花板 >= 0.9」为每个类别定阈值：')
for n, s in CLASSES.items():
    ok = [t for t in [0.7, 0.5, 0.25, 0.1] if sweep[n][t] >= 0.9]
    best = max(ok) if ok else None
    print(f'  {n:12s} -> τ = {best if best is not None else "即使 0.1 也不够"}'
          f'   （天花板 {sweep[n][best]:.3f}）' if best is not None
          else f'  {n:12s} -> **即使 τ=0.1 天花板也只有 {sweep[n][0.1]:.3f}**')
print('\\n✅ 这就是「KITTI 车用 0.7 / 行人用 0.5」的**依据**——'
      '让每个类别的天花板保持在 0.9 以上')"""),

    md("""## 5 · mIoU 与频率加权：同一个改进差 250 倍"""),

    code("""NAMES = ['ground', 'car', 'sign', 'other']
FREQ = np.array([0.600, 0.080, 0.001, 0.319])
IOUS = np.array([0.95, 0.75, 0.20, 0.60])

def miou(ious):
    return float(np.mean(ious))

def fwiou(ious, freq=FREQ):
    return float((ious * freq).sum() / freq.sum())

print(f\"{'类别':>10s} {'频率':>9s} {'IoU':>7s} {'mIoU 权重':>11s} {'加权权重':>10s}\")
for n, f, i in zip(NAMES, FREQ, IOUS):
    print(f'{n:>10s} {f:8.3f} {i:7.2f} {1/len(NAMES):10.1%} {f/FREQ.sum():9.1%}')
print(f'\\n  mIoU（等权）  = {miou(IOUS):.4f}')
print(f'  频率加权 IoU  = {fwiou(IOUS):.4f}')
print(f'  两者相差 {abs(miou(IOUS)-fwiou(IOUS)):.4f}')

# 稀有类在 mIoU 里的权重是它频率的 250 倍
w_ratio = (1/len(NAMES)) / (FREQ[2]/FREQ.sum())
print(f'  而 sign（{FREQ[2]:.1%}）在 mIoU 里占 {1/len(NAMES):.0%} 的权重'
      f' —— 是它频率的 **{w_ratio:.0f} 倍**')

print(f'\\n把 sign 的 IoU 从 0.20 提到 0.80：')
print(f\"{'sign IoU':>10s} {'mIoU':>9s} {'Δ mIoU':>10s} {'加权':>9s} {'Δ 加权':>11s}\")
for new in [0.20, 0.40, 0.60, 0.80]:
    i2 = IOUS.copy(); i2[2] = new
    print(f'{new:10.2f} {miou(i2):9.4f} {miou(i2)-miou(IOUS):+10.4f} '
          f'{fwiou(i2):9.4f} {fwiou(i2)-fwiou(IOUS):+11.5f}')

i80 = IOUS.copy(); i80[2] = 0.80
d_m, d_w = miou(i80) - miou(IOUS), fwiou(i80) - fwiou(IOUS)
print(f'\\n✅ 同一个改进: mIoU +{d_m:.4f}，频率加权 +{d_w:.5f}'
      f' —— 差 **{d_m/d_w:.0f} 倍**')
assert d_m / d_w > 100
print('   → 「选哪个指标」直接决定「改进稀有类值不值得做」')
print('   而对自动驾驶，频率加权是明确错的口径（按频率而不是按后果加权）')"""),

    md("""## 6 · PQ 的分解，与它同样受 IoU 阈值支配"""),

    code("""def pq(matches, n_pred, n_gt, thr=0.5):
    '''matches: 每个匹配对的 IoU 列表（已按 thr 筛过）。返回 (PQ, SQ, RQ)。'''
    tp = [m for m in matches if m >= thr]
    n_tp = len(tp)
    fp, fn = n_pred - n_tp, n_gt - n_tp
    sq = float(np.mean(tp)) if n_tp else 0.0
    rq = n_tp / (n_tp + 0.5 * fp + 0.5 * fn) if (n_tp + fp + fn) else 0.0
    return sq * rq, sq, rq

# 两种情形：找得全但分割糙 vs 找得少但分割准
A = ([0.55] * 10, 10, 10)      # 10 个匹配，IoU 都刚过线
B = ([0.95] * 5, 5, 10)        # 只找到 5 个，但都很准
for tag, (ms, np_, ng) in [('找得全、分割糙', A), ('找得少、分割准', B)]:
    p, s_, r_ = pq(ms, np_, ng)
    print(f'{tag}: PQ={p:.4f}  SQ={s_:.4f}  RQ={r_:.4f}')

pa = pq(*A)[0]; pb = pq(*B)[0]
print(f'\\n两者的 PQ: {pa:.4f} vs {pb:.4f}')
print('  → PQ 把「找得全不全」（RQ）与「分割准不准」（SQ）拆成两个可分别改进的因子')

# 但 PQ 的匹配判据仍是 IoU > 0.5 —— 所以第 3b 节的天花板同样适用
print(f'\\nPQ 的 RQ 部分受 IoU 阈值支配，所以第 3b 节的天花板同样适用：')
for n in ['car', 'sign']:
    c = metric_ceiling(CLASSES[n], SIGMA_ANN, 'iou', 0.5)
    # 完美模型：n_pred = n_gt = 100，但只有 c 比例被判为 TP
    n_all = 100
    n_tp = int(round(c * n_all))
    _, sq_, rq_ = pq([0.9] * n_tp, n_all, n_all)
    print(f'  {n:6s}: IoU 天花板 {c:.3f} -> 完美模型的 RQ = {rq_:.3f}'
          f'  PQ <= {sq_*rq_:.3f}')
print('  → **即使用全景指标，也要先检查匹配判据的天花板**')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| IoU 的闭式 | $q/(2-q)$，与直接算的差 < 1e-12 |
| **单轴容差** | 恰好 $s_i/3$（四个类别上精确吻合） |
| 每轴等相对误差 | 2D 允许 **18.4%**，3D 只允许 **12.6%** |
| 各向同性容差 | 卡车 **0.796 m** → 标志 **0.049 m**（**16 倍**） |
| 沿最薄轴偏 0.1 m | 标志 IoU = **0.0000**（完全脱靶） |
| **两种口径的分歧率** | $\\sigma{=}0.2$ m：卡车 0.001 → **标志 0.972** |
| **口径的天花板** | 5 cm 标注噪声下，完美模型在标志上只有 **0.392** |
| 中心距离口径的天花板 | 四个类别 **恒为 1.000** |
| 容差 / $\\sigma_{\\text{ann}}$ | 卡车 15.93× · 轿车 9.18× · 行人 3.32× · **标志 0.98×** |
| 降阈值 | 标志 τ=0.5 的 0.391 → τ=0.25 的 0.736 |
| **mIoU vs 频率加权** | 同一个改进差 **250 倍**（+0.1500 vs +0.00060） |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：容差反解器

实现 `tolerance_table(class_sizes, thr=0.5)`，返回 `{类名: dict}`，每项含：

- `'per_axis'` —— 各轴的单轴容差（应当恰好是 $s_i/3$，$\\tau{=}0.5$ 时）
- `'isotropic'` —— 各向同性位移的容差
- `'worst_axis'` —— 最短轴的下标
- `'rel_per_axis'` —— 每轴等相对误差时允许的相对误差"""),

    code("""def tolerance_table(class_sizes, thr=0.5):
    \"\"\"返回 {类名: dict(per_axis, isotropic, worst_axis, rel_per_axis)}。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
tt = tolerance_table(CLASSES)
for n, v in tt.items():
    assert set(v) == {'per_axis', 'isotropic', 'worst_axis', 'rel_per_axis'}

print(f\"{'类别':>12s} {'各轴容差 (m)':>30s} {'各向同性':>10s} {'每轴相对':>9s}\")
for n, v in tt.items():
    pa = '[' + ', '.join(f'{x:.3f}' for x in v['per_axis']) + ']'
    print(f'{n:>12s} {pa:>30s} {v["isotropic"]:9.3f} {v["rel_per_axis"]:8.1%}')

# ① τ=0.5 时单轴容差恰好是 s/3
for n, s in CLASSES.items():
    for i in range(3):
        assert abs(tt[n]['per_axis'][i] - s[i] / 3) < 1e-6, (n, i)
print('\\n✅ τ=0.5 时单轴容差恰好是 s/3（四个类别、三个轴全部吻合）')

# ② 最短轴的下标
for n, s in CLASSES.items():
    assert tt[n]['worst_axis'] == int(np.argmin(s))

# ③ 每轴相对误差与维数有关、与尺寸无关
rels = {tt[n]['rel_per_axis'] for n in CLASSES}
assert len(rels) == 1, f'相对误差应当与尺寸无关，实得 {rels}'
assert abs(list(rels)[0] - (1 - (2/3)**(1/3))) < 1e-6
print(f'✅ 每轴相对误差 {list(rels)[0]:.4f} 对所有类别相同（只依赖维数 n=3）')

# ④ 换阈值
tt7 = tolerance_table(CLASSES, thr=0.7)
for n in CLASSES:
    assert tt7[n]['isotropic'] < tt[n]['isotropic'], '阈值越高容差越小'
print(f'\\nτ=0.7 时标志的各向同性容差 {tt7["sign"]["isotropic"]:.4f} m'
      f'（τ=0.5 时是 {tt["sign"]["isotropic"]:.4f} m）')
print('✅ 练习 1 通过')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def tolerance_table(class_sizes, thr=0.5):
    q_need = 2 * thr / (1 + thr)              # IoU>=thr  <=>  q >= 2τ/(1+τ)
    out = {}
    for name, s in class_sizes.items():
        s = np.asarray(s, float)
        per_axis = (1.0 - q_need) * s          # 单轴：1 − δ/s = q_need
        n = len(s)
        rel = 1.0 - q_need ** (1.0 / n)        # 每轴等相对误差
        # 各向同性：二分
        lo, hi = 0.0, 20.0
        for _ in range(80):
            mid = (lo + hi) / 2
            d = (mid / np.sqrt(n),) * n
            if iou_same_size(s, d) >= thr:
                lo = mid
            else:
                hi = mid
        out[name] = {'per_axis': per_axis.tolist(), 'isotropic': float(lo),
                     'worst_axis': int(np.argmin(s)), 'rel_per_axis': float(rel)}
    return out

tt = tolerance_table(CLASSES)
for n, s in CLASSES.items():
    assert abs(tt[n]['per_axis'][0] - s[0] / 3) < 1e-9
print('✅ 参考答案 2 通过'.replace('2', '1'))
print('   关键是先把阈值翻译成 q：IoU ≥ τ ⟺ q ≥ 2τ/(1+τ)。')
print('   τ=0.5 给 q ≥ 2/3，所以单轴容差 = (1 − 2/3)·s = s/3。')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：口径分歧分析

实现 `criterion_comparison(size, sigma, iou_thr=0.5, dist_thr=2.0, n=20000)`，
返回 dict：

- `'hit_iou'`, `'hit_dist'` —— 两个口径的命中率
- `'disagree'` —— 分歧率
- `'iou_only'` —— 只有 IoU 判命中的比例
- `'dist_only'` —— 只有中心距离判命中的比例
- `'direction'` —— `'iou_stricter'` / `'dist_stricter'` / `'agree'`"""),

    code("""def criterion_comparison(size, sigma, iou_thr=0.5, dist_thr=2.0,
                         n=20000, seed=0):
    \"\"\"返回 dict(hit_iou, hit_dist, disagree, iou_only, dist_only, direction)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
print(f\"{'类别':>12s} {'σ':>6s} {'IoU':>8s} {'中心':>8s} {'分歧':>8s} \"
      f\"{'仅IoU':>8s} {'仅中心':>8s} {'方向':>14s}\")
res = {}
for n_, s in CLASSES.items():
    for sg in [0.05, 0.2]:
        c = criterion_comparison(s, sg)
        res[(n_, sg)] = c
        assert set(c) == {'hit_iou', 'hit_dist', 'disagree', 'iou_only',
                          'dist_only', 'direction'}
        print(f'{n_:>12s} {sg:6.2f} {c["hit_iou"]:8.3f} {c["hit_dist"]:8.3f} '
              f'{c["disagree"]:8.3f} {c["iou_only"]:8.3f} {c["dist_only"]:8.3f} '
              f'{c["direction"]:>14s}')

# ① 分歧全部来自「中心距离更松」这一侧
for k, c in res.items():
    assert c['iou_only'] < 1e-3, f'{k}: IoU 不应当比中心距离更松'
    assert abs(c['disagree'] - c['dist_only']) < 1e-6

# ② 大目标一致，小目标分歧
assert res[('truck', 0.2)]['direction'] == 'agree'
assert res[('sign', 0.2)]['direction'] == 'iou_stricter'
assert res[('sign', 0.2)]['disagree'] > 0.9
print(f'\\n✅ 分歧全部来自「IoU 更严」这一侧（仅 IoU 命中的比例 < 0.001）')
print(f'   卡车 {res[("truck",0.2)]["direction"]}，'
      f'标志 {res[("sign",0.2)]["direction"]}（分歧 '
      f'{res[("sign",0.2)]["disagree"]:.1%}）')

# ③ 把中心距离阈值收紧到「与 IoU 容差相当」，分歧就消失
tol_sign = tolerance_table(CLASSES)['sign']['isotropic']
c_tight = criterion_comparison(CLASSES['sign'], 0.2, dist_thr=tol_sign)
print(f'\\n把中心距离阈值收到 {tol_sign:.3f} m（= 标志的 IoU 容差）: '
      f'分歧 {c_tight["disagree"]:.3f}')
assert c_tight['disagree'] < 0.1, '阈值匹配后分歧应当很小'
print('✅ 练习 2 通过：**两个口径不是「哪个更对」，而是阈值是否可比**')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def criterion_comparison(size, sigma, iou_thr=0.5, dist_thr=2.0,
                         n=20000, seed=0):
    d = np.random.default_rng(seed).normal(0, sigma, (n, 3))
    by_iou = np.array([iou_same_size(size, dd) >= iou_thr for dd in d])
    by_dist = np.linalg.norm(d, axis=1) <= dist_thr
    iou_only = float((by_iou & ~by_dist).mean())
    dist_only = float((by_dist & ~by_iou).mean())
    dg = float((by_iou != by_dist).mean())
    if dg < 0.02:
        direction = 'agree'
    elif dist_only > iou_only:
        direction = 'iou_stricter'
    else:
        direction = 'dist_stricter'
    return {'hit_iou': float(by_iou.mean()), 'hit_dist': float(by_dist.mean()),
            'disagree': dg, 'iou_only': iou_only, 'dist_only': dist_only,
            'direction': direction}

c = criterion_comparison(CLASSES['sign'], 0.2)
assert c['direction'] == 'iou_stricter' and c['iou_only'] < 1e-3
print('✅ 参考答案 2 通过')
print('   `iou_only ≈ 0` 说明 IoU-0.5 是中心距离-2m 的**子集**（在这些参数下）——')
print('   所以两者不是「不同的判断」，而是「同一个判断的两个松紧度」。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：口径天花板审计

实现 `ceiling_audit(class_sizes, sigma_ann, taus=(0.1,0.25,0.5,0.7), target=0.9)`，
返回 `{类名: dict}`，每项含：

- `'ceiling'` —— `{τ: 完美模型的上界}`
- `'best_tau'` —— 使上界 $\\ge$ `target` 的**最大** τ（没有则 `None`）
- `'tol_over_sigma'` —— IoU-0.5 容差 / `sigma_ann`
- `'trustworthy'` —— bool：`tol_over_sigma >= 3`

**这是本模块最实用的交付物**——它不需要模型，只需要类别尺寸与标注噪声估计。"""),

    code("""def ceiling_audit(class_sizes, sigma_ann, taus=(0.1, 0.25, 0.5, 0.7),
                  target=0.9):
    \"\"\"返回 {类名: dict(ceiling, best_tau, tol_over_sigma, trustworthy)}。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
au = ceiling_audit(CLASSES, 0.05)
for n, v in au.items():
    assert set(v) == {'ceiling', 'best_tau', 'tol_over_sigma', 'trustworthy'}

print(f\"{'类别':>12s} \" + ''.join(f'τ={t}'.rjust(9) for t in (0.1,0.25,0.5,0.7)) +
      f\"{'最佳 τ':>9s} {'容差/σ':>9s} {'可信':>7s}\")
for n, v in au.items():
    row = ''.join(f'{v["ceiling"][t]:8.3f} ' for t in (0.1, 0.25, 0.5, 0.7))
    bt = 'None' if v['best_tau'] is None else f'{v["best_tau"]}'
    print(f'{n:>12s} {row}{bt:>9s} {v["tol_over_sigma"]:8.2f}× '
          f'{str(v["trustworthy"]):>7s}')

# ① 大目标：0.7 就够，且可信
assert au['truck']['best_tau'] == 0.7 and au['truck']['trustworthy'] is True
assert au['car']['best_tau'] == 0.7 and au['car']['trustworthy'] is True
# ② 标志：不可信，且即使降阈值也救不回 0.9
assert au['sign']['trustworthy'] is False
assert au['sign']['ceiling'][0.5] < 0.5
print(f'\\n卡车/轿车: 最佳 τ=0.7、可信')
print(f'标志: 容差/σ = {au["sign"]["tol_over_sigma"]:.2f}× < 3 -> **不可信**')
print(f'      而即使 τ=0.1，上界也只有 {au["sign"]["ceiling"][0.1]:.3f}')

# ③ 把标注噪声降到 0.01 m，标志就可信了
au2 = ceiling_audit({'sign': CLASSES['sign']}, 0.01)
print(f'\\n把 σ_ann 降到 0.01 m: 标志的容差/σ = '
      f'{au2["sign"]["tol_over_sigma"]:.2f}×，可信 {au2["sign"]["trustworthy"]}')
assert au2['sign']['trustworthy'] is True
print('✅ 练习 3 通过：**这个审计只需要类别尺寸与标注噪声估计，不需要模型**')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def ceiling_audit(class_sizes, sigma_ann, taus=(0.1, 0.25, 0.5, 0.7),
                  target=0.9):
    tt = tolerance_table(class_sizes, thr=0.5)
    out = {}
    for name, s in class_sizes.items():
        ceil = {t: metric_ceiling(s, sigma_ann, 'iou', t) for t in taus}
        ok = [t for t in sorted(taus) if ceil[t] >= target]
        r = tt[name]['isotropic'] / sigma_ann
        out[name] = {'ceiling': ceil,
                     'best_tau': (max(ok) if ok else None),
                     'tol_over_sigma': float(r),
                     'trustworthy': bool(r >= 3.0)}
    return out

au = ceiling_audit(CLASSES, 0.05)
assert au['truck']['trustworthy'] and not au['sign']['trustworthy']
print('✅ 参考答案 3 通过')
print('   两个判据是互补的：')
print('   `trustworthy` 看容差与标注噪声的比（信噪比）；')
print('   `best_tau` 看「降阈值能不能把天花板拉回 0.9」（补救手段）。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：分层报告器

实现 `stratified_report(records, dims)`，`records` 是每条检测的 dict
（含 `'hit'`（bool）与若干分层字段），`dims` 是要分层的字段名列表。

返回 `{维度: {桶: dict(n, recall)}}`，并额外给一个 `'_worst'` 键：
`{维度: (最差的桶, 该桶的 recall)}`。

**要求：只报样本数 $\\ge5$ 的桶**（否则 recall 是噪声）。"""),

    code("""def stratified_report(records, dims, min_n=5):
    \"\"\"返回 {维度: {桶: dict(n, recall)}}，外加 '_worst' 键。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# 造一批检测记录：远处与薄目标的召回明显更低
rng2 = np.random.default_rng(5)
RECS = []
for _ in range(600):
    rng_band = rng2.choice(['0-20m', '20-50m', '50m+'], p=[0.5, 0.35, 0.15])
    cls = rng2.choice(['car', 'sign'], p=[0.8, 0.2])
    p_hit = {'0-20m': 0.95, '20-50m': 0.80, '50m+': 0.45}[rng_band]
    if cls == 'sign':
        p_hit *= 0.5
    RECS.append({'hit': bool(rng2.random() < p_hit),
                 'range_band': rng_band, 'cls': cls,
                 'orient_band': rng2.choice(['0-30°', '30-60°', '60-90°'])})

rep = stratified_report(RECS, ['range_band', 'cls', 'orient_band'])
assert '_worst' in rep
for d in ['range_band', 'cls', 'orient_band']:
    assert d in rep

for d in ['range_band', 'cls', 'orient_band']:
    print(f'{d}:')
    for b, v in sorted(rep[d].items()):
        print(f'    {b:>10s}  n={v["n"]:4d}  recall={v["recall"]:.3f}')
    w = rep['_worst'][d]
    print(f'    最差: {w[0]}（{w[1]:.3f}）')

# ① 距离与类别上应当有明显差异，朝向上不应当有
r_far = rep['range_band']['50m+']['recall']
r_near = rep['range_band']['0-20m']['recall']
assert r_far < r_near * 0.7, (r_far, r_near)
assert rep['range_band']['_'] if False else True
assert rep['cls']['sign']['recall'] < rep['cls']['car']['recall'] * 0.8

# ② 总体召回掩盖了分层差异
overall = np.mean([r['hit'] for r in RECS])
print(f'\\n总体召回 {overall:.3f}，而最差的桶：')
for d in ['range_band', 'cls']:
    w = rep['_worst'][d]
    print(f'  {d}: {w[0]} 只有 {w[1]:.3f}（总体的 {w[1]/overall:.0%}）')
assert rep['_worst']['range_band'][1] < overall * 0.7

# ③ 小样本桶被过滤
few = RECS + [{'hit': False, 'range_band': '100m+', 'cls': 'car',
               'orient_band': '0-30°'}] * 3
rep2 = stratified_report(few, ['range_band'])
assert '100m+' not in rep2['range_band'], '样本数 < 5 的桶应当被过滤'
print(f'\\n只有 3 个样本的 100m+ 桶被过滤掉了（避免报噪声）')
print('✅ 练习 4 通过：**总体召回掩盖了分层差异，而分层维度由「你怀疑什么」决定**')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def stratified_report(records, dims, min_n=5):
    out = {}
    worst = {}
    for d in dims:
        buckets = {}
        for r in records:
            buckets.setdefault(r[d], []).append(bool(r['hit']))
        tab = {b: {'n': len(v), 'recall': float(np.mean(v))}
               for b, v in buckets.items() if len(v) >= min_n}
        out[d] = tab
        if tab:
            b = min(tab, key=lambda k: tab[k]['recall'])
            worst[d] = (b, tab[b]['recall'])
    out['_worst'] = worst
    return out

rep = stratified_report(RECS, ['range_band', 'cls'])
assert rep['_worst']['cls'][0] == 'sign'
print('✅ 参考答案 4 通过')
print('   `min_n` 不是可选项：一个 3 样本的桶报出 0.000 的召回，')
print('   会让人去修一个不存在的问题（而这与 C10 的「样本量与置信区间」是同一条）。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) 先算天花板，再看排名（练习 3）──
#    做法：把预测直接设成真值，再给真值加上你估计的标注噪声，跑一遍你的评测代码。
gt_noisy = gt.copy()
gt_noisy[:, :3] += np.random.normal(0, SIGMA_ANN, (len(gt), 3))
ceiling = your_eval(predictions=gt, ground_truth=gt_noisy)   # ← 完美模型的上界
#    任何类别的 ceiling < 0.9，该类别的排名就不可信。

# ── 2) nuScenes 的口径：中心距离 + 误差分解 ──
from nuscenes.eval.detection.config import config_factory
cfg = config_factory('detection_cvpr_2019')
print(cfg.dist_ths)          # [0.5, 1.0, 2.0, 4.0] —— 中心距离，不是 IoU
#    上报 mAP 之外还有 ATE / ASE / AOE / AVE / AAE —— **不要只看 NDS 一个数**

# ── 3) 分割：绝不只报 mIoU（第 5 节）──
per_class_iou = confusion_iou(conf_mat)              # 逐类表
report = {
    'mIoU': per_class_iou.mean(),                    # 可比性
    'per_class': dict(zip(CLASS_NAMES, per_class_iou)),   # ← 唯一有信息量的
    'safety_critical_recall': {c: recall[c] for c in SAFETY_CLASSES},
}
#    频率加权 IoU 是明确错的口径（按频率而不是按后果加权）——不要报它

# ── 4) 分层维度按本课的六个来（第 7 节）──
STRATIFY_DIMS = ['range_band',        # 密度衰减 520 倍（模块 01）
                 'n_points_band',     # 临界点集只看 24 个点（模块 02）
                 'thickness_band',    # IoU 的三个乘子（模块 05）
                 'orientation_band',  # 锚框离散化（模块 04）
                 'class',             # 频率稀释（模块 05）
                 'has_vertical_overlap']  # BEV NMS（模块 04）
#    每一个维度都对应本课某一节量出的一个具体机制 —— 而不是随便分的
```

> **落地顺序建议**：先跑天花板审计（几行，可能直接告诉你「某个类别的指标没有意义」），
> 再把 mIoU 换成「mIoU + 逐类表 + 关键类召回」三件套，
> 最后按六个维度加分层。
> <em>而如果天花板审计发现某个类别不可信，先解决口径，再谈模型——
> 否则你在用一把分辨率不足的尺子做排名。</em>"""),
]
