# -*- coding: utf-8 -*-
"""C56 模块 01 · 几何增强与标注同步。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（三判据与标注同步框架）；线性代数（矩阵乘法）；C55（TSR 领域）与 C57（小目标）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_geometric_aug.ipynb'),
    ("核心参考", "YOLOv5 <code>random_perspective</code> / <code>letterbox</code> 源码、Albumentations 的 BboxParams、mmdet 的 <code>gt_bboxes_ignore</code> 语义"),
    ("预计时长", "读 70 分钟 + 跑 65 分钟"),
]

SECTIONS = [
    ("taxonomy", "几何增强谱系：每种变换对应现实中的什么", "".join([
        P("几何增强只有一个共同的形式——<strong>把像素从一个坐标搬到另一个坐标</strong>——但它们注入的先验完全不同。选哪些、幅度多大，取决于<em>你的相机在真实世界里会经历什么</em>。所以下面这张表的最后两列（「对应的物理现象」和「TSR 里的正确幅度」）才是决策依据，第一列只是名字。"),
        TABLE(["变换", "自由度", "对应的物理现象", "TSR 里的合理幅度与理由"], [
            ["<strong>平移 translate</strong>", "2", "标志在画面里的位置随车道、车速、相机安装偏差变化", "<strong>±10% 图宽</strong>。TSR 有强位置先验（标志在画面上部/路侧），平移过大会把先验冲掉"],
            ["<strong>缩放 scale</strong>", "1（或 2）", "<strong>标志的远近</strong>——同一块牌子 20 m 处 50 px、60 m 处 17 px", "<strong>0.5–1.5×，这是 TSR 收益最高的几何增强</strong>；因为它精确对应距离变化，物理上无误差"],
            ["<strong>旋转 rotate</strong>", "1", "车身侧倾（过弯/坑洼）、相机滚转安装误差", "<strong>±5°～±10°</strong>。真实滚转角很少超过 5°；再大就违反判据②，且外接框膨胀迅速（本模块第 4 节）"],
            ["<strong>错切 shear</strong>", "2", "相机与标志平面不平行时的一阶近似", "<strong>±2°</strong>。作用与轻微透视重叠，通常可省"],
            ["<strong>仿射 affine</strong>", "6", "上面四种的组合（保持平行线平行）", "把 translate/scale/rotate/shear 合成<strong>一个矩阵一次采样</strong>——见第 2 节，这不只是省事"],
            ["<strong>透视 perspective</strong>", "8", "<strong>斜视角看标志</strong>：不在正前方的标志、弯道上的标志、侧装相机", "<strong>幅度极小（0.0005 量级）</strong>。YOLOv5 默认 <code>perspective=0.0</code> 就是因为它容易失控"],
            ["<strong>水平翻转 hflip</strong>", "0", "——<strong>现实中不存在</strong>：没有哪台相机会拍出镜像的世界", "<strong>TSR 里默认关闭</strong>；要开必须配类别白名单（本模块第 6 节，面试加分点）"],
            ["<strong>垂直翻转 vflip</strong>", "0", "——现实中更不存在：重力方向是恒定的", "<strong>永远关闭</strong>。它连「变换族 𝒯 该不该包含它」这一问都过不了"],
            ["<strong>letterbox / resize</strong>", "1+2", "不是增强，是<strong>输入尺寸归一化</strong>——但它同样改坐标，同样要写 <code>g_T</code>", "必需，且<strong>推理端必须逐像素一致</strong>（本模块第 7 节，直连 C60）"],
        ]),
        DUAL(
            "读这张表要抓一条线：<strong>「这个变换在部署环境里真的会发生吗？」</strong>缩放会（车在动，距离一直在变）；轻微旋转会（车身有侧倾）；水平翻转<em>永远不会</em>——世界上没有镜像的交通标志系统。<em>一旦某个变换的答案是「不会」，它就不是在注入先验，而是在教模型一条假规律</em>，模块 00 的判据②（贴近部署分布）直接判它出局。",
            "更精细的一层是<strong>幅度</strong>。同一个变换，小幅度是有效先验、大幅度是假规律，中间有一条模糊的边界。判断这条边界的可操作方法是：<em>去问这个物理量的真实分布</em>。车身滚转角在正常驾驶下的 p99 大约在 3°–5°（过弯、路面倾斜），所以 ±10° 的旋转已经覆盖了长尾，±45° 则纯属虚构。<strong>「把增强幅度对齐到物理量的真实分布」比「照抄一份配置」可靠得多</strong>，而且在面试里能立刻显出你是否真的想过。",
        ),
        CALLOUT("intuition", "一个能让你少走很多弯路的观察：<strong>几何增强里真正带来收益的几乎只有「缩放」一项，其余都是锦上添花或负收益</strong>。原因很直接——检测器对平移天然近似不变（卷积的平移等变性 + 全图密集预测），对旋转的需求在车载场景里很小，而翻转在 TSR 里是错的。<em>但缩放不一样：尺度是 CNN 唯一不能自动泛化的维度</em>（这也是 FPN 存在的理由，见 C57 模块 02）。所以「多尺度训练 + 大范围缩放」在 TSR 上的收益，通常抵得过其余所有几何增强之和。"),
    ])),
    ("matrix", "统一框架：齐次坐标、仿射矩阵与算子顺序", "".join([
        P("把上面这些变换<strong>合成一个 3×3 矩阵一次采样</strong>，不只是代码更短——它解决了三个真实问题。"),
        MATH("\\mathbf{M} \\;=\\; \\underbrace{T(c_x, c_y)}_{\\text{移回中心}} \\cdot \\underbrace{T(t_x, t_y)}_{\\text{平移}} \\cdot \\underbrace{R(\\theta)}_{\\text{旋转}} \\cdot \\underbrace{S(s)}_{\\text{缩放}} \\cdot \\underbrace{H(\\phi)}_{\\text{错切}} \\cdot \\underbrace{T(-c_x, -c_y)}_{\\text{移到原点}}"),
        UL([
            "<strong>问题一：重采样次数</strong>。分步做「先旋转、再缩放、再平移」意味着<em>三次插值</em>，每次插值都在抹平高频细节。<strong>对 15 像素的交通标志，三次双线性插值足以把限速数字的笔画糊掉</strong>。合成一个矩阵只插值一次。",
            "<strong>问题二：中心点语义</strong>。「旋转」必须指定绕哪个点转。绕图像左上角 (0,0) 转 10°，画面右下角的目标会被甩出去几百像素；绕图像中心转才是你想要的。<code>T(c) · R · T(-c)</code> 这个三明治结构把「绕某点变换」写清楚了——<em>而这正是自己手写仿射时最常错的地方</em>。",
            "<strong>问题三：标注同步的正确性</strong>。有了矩阵 <code>M</code>，图像用 <code>M</code> 重采样，框的角点用同一个 <code>M</code> 变换——<strong>两条轨道用的是同一个对象，不可能不一致</strong>。分步实现则要求每一步都同步，任何一步漏了就静默出错（模块 00 演示过：图正常、框偏 5 px、IoU 掉到 0.36）。",
        ]),
        DUAL(
            "矩阵相乘<strong>不可交换</strong>，所以顺序是语义的一部分而不是实现细节。「先缩放 0.5 再平移 100 px」与「先平移 100 px 再缩放 0.5」差了 50 像素。约定俗成的写法是<em>从右往左读</em>：最右边的矩阵最先作用在点上。上式从右读就是「移到原点 → 错切 → 缩放 → 旋转 → 平移 → 移回中心」，这也是 YOLOv5 <code>random_perspective</code> 的顺序。",
            "透视（perspective）需要完整的 3×3 而不只是仿射的 2×3：<strong>第三行不再是 <code>[0,0,1]</code></strong>，于是变换后齐次坐标的 <code>w</code> 分量不为 1，必须做<span class=\"term\">透视除法</span>（perspective divide）<code>x' = x_h / w_h</code>。<em>忘记做这个除法是透视增强的头号 bug</em>——幅度小的时候误差也小（因为 <code>w ≈ 1</code>），所以它能在代码库里潜伏很久，直到某天有人把 <code>perspective</code> 从 0.0005 调到 0.005，框开始莫名其妙地偏。<strong>这也是为什么本模块的 notebook 里，角点变换函数无条件做透视除法</strong>：仿射时它是恒等操作，透视时它是必需的。",
        ),
        CALLOUT("warn", "还有一个「顺序」是跨算子的：<strong>几何增强必须排在光度增强之前</strong>。理由不是美学而是数值——几何变换要插值，插值会在<em>已经被加过噪声/改过对比度</em>的像素上二次混合，把光度增强的统计特性搞乱（例如你加了 σ=5 的高斯噪声，双线性插值后实际方差变成了 σ²·Σwᵢ² &lt; 25）。<em>反过来先几何后光度，噪声的统计量就是你设定的那个。</em>模块 04 会把整条流水线的顺序规则讲完。"),
    ])),
    ("bbox", "bbox 如何跟随变换：四角法与它的三重失真", "".join([
        P("水平竖直的 bbox 在旋转/错切/透视下<strong>不是封闭的</strong>——变换后它不再是一个轴对齐矩形。而检测器的输出格式要求轴对齐，所以工业界统一采用<span class=\"term\">四角法</span>（four-corner method）：把框的 4 个角点变换过去，再取它们的<strong>轴对齐外接框</strong>。"),
        MATH("\\mathbf{b}' \\;=\\; \\Big[\\;\\min_k x'_k,\\;\\; \\min_k y'_k,\\;\\; \\max_k x'_k,\\;\\; \\max_k y'_k \\;\\Big], \\qquad (x'_k, y'_k) = \\pi\\big(\\mathbf{M}\\,[x_k, y_k, 1]^\\top\\big)"),
        ASCII("""四角法（four-corner method）：唯一被普遍采用的 bbox 变换方式

  原框（轴对齐）            旋转 30° 后的 4 个角点        取外接框
  (x1,y1)-------(x2,y1)              o                  +-------------+
     |             |               /   \\                |    o        |
     |    目标      |     ==>     o      o      ==>      |  /   \\      |
     |             |               \\   /                | o      o    |
  (x1,y2)-------(x2,y2)              o                  |   \\  /      |
                                                        |    o        |
                                                        +-------------+
                                                        **面积变大了**

  三重失真（按危害排序）：
   ① 膨胀   —— 外接框面积 > 原框面积，框里混进大量背景（第 4 节量化）
   ② 过估计 —— 对**旋转不变的形状**（圆形禁令牌！）四角法给出的框是**错的**，
                真实紧框根本没变，四角法却把它撑大了 41%（45° 时）
   ③ 不可逆 —— 变换回去得不到原框（min/max 丢掉了角点的对应关系）；
                所以「增强 -> 逆增强」不能用来做对拍，必须两边各自独立算""")
        ,
        DUAL(
            "失真② 是 TSR 特别要注意的一条，多数教材完全不提。<strong>四角法隐含假设「目标恰好填满它的框」</strong>——对一辆车、一个行人，这个假设大致成立；但<em>中国的禁令标志是圆形、警告标志是三角形</em>，它们只填了框的 78.5% 和 50%。圆形对旋转是<strong>完全不变</strong>的：把图旋转 45°，圆还是那个圆，它的真实紧框尺寸<em>一点没变</em>。而四角法会把框放大到边长 √2 倍——<strong>这是一个纯粹由算法引入的、错误的标注</strong>，与原框的 IoU 只有 0.50。",
            "为什么工业界仍然接受它？因为<strong>替代方案更贵</strong>：要得到真实紧框，你需要目标的掩码或轮廓（实例分割级标注），而检测数据集通常只有框。少数场景会用<span class=\"term\">有向框</span>（oriented bounding box, OBB，见遥感检测的 DOTA 数据集与 GWD/KLD 损失）彻底绕开这个问题，但代价是检测头、NMS、评测协议全都要换一套。<em>TSR 里通常不值得</em>——因为真实旋转角本来就只有几度，膨胀率在 ±5° 时不到 18%。<strong>「知道这个失真存在、并因此把旋转幅度限制在 ±10° 以内」，就是正确的工程处理。</strong>",
        ),
        CALLOUT("warn", "失真③ 有一个直接的工程后果，容易踩：<strong>不要试图用「增强后再逆增强」来验证增强的正确性</strong>。<code>min/max</code> 是有损的，逆变换回来的框会比原框大，你会看到一个恒定的「误差」并花半天找不存在的 bug。<em>正确的验证方式是模块 00 建立的那条</em>：用目标的掩码/轮廓点在<strong>变换后的图像上</strong>算出真实紧框，与 <code>apply_boxes</code> 的输出比 IoU。notebook 里会把这套断言用在每一个算子上。"),
    ])),
    ("inflate", "旋转的隐性代价：把框膨胀量化到小数点后", "".join([
        P("「旋转增强会让框变大」这句话人人都会说，但<strong>大多少</strong>？这个数字必须算出来，因为它直接决定旋转幅度的上限。设原框宽 <code>w</code> 高 <code>h</code>，绕中心旋转 <code>θ</code>，四角外接框的宽高是 <code>w|cosθ| + h|sinθ|</code> 与 <code>w|sinθ| + h|cosθ|</code>，展开相乘可得一个非常干净的闭式："),
        MATH("\\frac{A'}{A} \\;=\\; 1 \\;+\\; \\frac{1}{2}\\,\\big|\\sin 2\\theta\\big| \\left( \\frac{w}{h} + \\frac{h}{w} \\right)"),
        P("这个式子有三个可以直接拿去用的推论："),
        OL([
            "<strong>膨胀在 45° 达到最大，而不是 90°</strong>（90° 时框只是宽高互换，面积不变）。所以「旋转角越大越糟」是错的，真正最糟的是 45°。",
            "<strong>正方形框（<code>w=h</code>）膨胀最小</strong>：此时 <code>w/h + h/w = 2</code>，比值退化为 <code>1 + |sin 2θ|</code>，<em>45° 时正好是 2.00×，即面积膨胀 100%</em>。这就是本课反复引用的那个数字。",
            "<strong>细长框膨胀得更狠</strong>：一块 3:1 的横向指路牌，<code>w/h + h/w = 3.33</code>，45° 时膨胀到 <strong>2.67×</strong>。<em>所以「旋转对哪些类别伤害最大」是可以按长宽比预测的。</em>",
        ]),
        TABLE(["旋转角 θ", "正方形框面积膨胀", "圆形标志在框内的占比", "四角框 vs 真实紧框的 IoU", "判断"], [
            ["0°", "1.00×", "78.5%", "1.00", "基准（圆内接于方框）"],
            ["±5°", "<strong>1.17×</strong>", "67.0%", "0.85", "✅ 可接受，覆盖真实车身侧倾的 p99"],
            ["±10°", "<strong>1.34×</strong>", "58.5%", "0.75", "⚠️ 上限。已有 1/3 的框是凭空多出来的背景"],
            ["±15°", "<strong>1.50×</strong>", "52.4%", "0.67", "⚠️ 框里前景已不到一半"],
            ["±30°", "1.87×", "42.1%", "0.54", "❌ 真实驾驶中不存在"],
            ["±45°", "<strong>2.00×</strong>", "<strong>39.3%</strong>", "<strong>0.50</strong>", "❌ 面积翻倍；<strong>标注 IoU 只剩 0.5，等于给了一个「半错」的标签</strong>"],
        ]),
        DUAL(
            "第三列「圆形标志在框内的占比」是这张表里最该被记住的一列。<strong>0° 时圆内接于方框，前景占 π/4 = 78.5%；旋转 45° 后四角法把框撑到 2 倍面积，前景只剩 39.3%</strong>。这意味着你在<em>反复告诉模型：一个只有 39% 是标志、61% 是天空和树的框，是「正样本」</em>。定位头就是这样被慢慢教松的——它不会突然崩，只会让所有框都稍微大一点，表现为高 IoU 阈值下的 AP（AP75）明显低于 AP50。<strong>「AP50 正常但 AP75 偏低」是定位质量问题的典型指纹</strong>，而增强里的框膨胀是它的常见成因之一。",
            "第四列「四角框 vs 真实紧框的 IoU」则量化了失真②：<em>对圆形/多边形这类接近旋转不变的标志，四角法产生的框本身就是错的</em>。45° 时 IoU 只有 0.50——恰好卡在大多数评测协议的正样本阈值上。<strong>换句话说：如果拿这个自动生成的标注去和「人重新标一遍」比对，一半的框会被判为「不匹配」。</strong>而这些标签会被当作 ground truth 用于训练几十个 epoch。<em>这不是「增强让任务变难了」（那是好事），这是「增强让标签变错了」（那是坏事）——两者必须分清。</em>",
        ),
        CALLOUT("danger", "<p>由此得到一条可以直接写进配置评审清单的规则：<strong>旋转幅度的上限应由「可接受的框膨胀率」反推，而不是拍脑袋</strong>。若你能接受 ≤35% 的膨胀，正方形框对应 <code>|θ| ≤ 10.2°</code>（解 <code>sin2θ = 0.35</code>），3:1 长框对应 <code>|θ| ≤ 6.1°</code>（解 <code>1.665·sin2θ = 0.35</code>）。<em>取两者的较小值作为全局上限</em>，或者更好——<strong>按类别的长宽比分别设上限</strong>。notebook 里会把这个反解写成函数。顺带一提：这也是一个很好的面试回答结构——<em>「我不是选了个 ±10°，我是从可接受的标注退化反推出来的」</em>。</p>", "旋转幅度应从框膨胀率反推"),
    ])),
    ("oob", "越界处理：keep / ignore / drop，以及丢弃阈值对小目标的生死线", "".join([
        P("平移、缩放、旋转、裁剪都会把目标推到画面外——<strong>可能是完全出去，也可能只出去一半</strong>。后一种情况怎么处理，是整条几何增强流水线里<em>最容易做错、后果最严重</em>的一处决策。"),
        TABLE(["策略", "做什么", "监督信号是什么", "什么时候正确", "做错的后果"], [
            ["<strong>keep（保留裁剪后的框）</strong>", "把框裁到画面内，仍作为正样本", "「这里有一个目标，框是这么大」", "目标可见比例高（&gt;70%），裁剪后的框仍紧贴可见部分", "可见比例低时，模型被要求从一小片边缘去回归一个完整目标 → 定位噪声"],
            ["<strong>ignore（标为忽略区域）</strong>", "既不算正样本，<strong>也不算负样本</strong>；分配阶段跳过、损失不回传", "「这里的情况不明，别学」", "<strong>可见但不足以给出可靠框的目标——这是默认应该选的</strong>", "几乎没有下行风险；唯一代价是少了一点点监督"],
            ["<strong>drop（从标注里删掉）</strong>", "直接删除这条标注", "<strong>「这里没有东西」——因为它成了背景</strong>", "目标<strong>完全</strong>不在画面里（可见比例 = 0）", "<strong>目标仍然可见却被删 → 明确的假负样本监督，模型被训练成漏检</strong>"],
        ]),
        DUAL(
            "三者的差别一句话就能说清：<strong><code>keep</code> 说「有」，<code>ignore</code> 说「不知道」，<code>drop</code> 说「没有」</strong>。而绝大多数实现的默认行为是 <code>drop</code>——因为它最好写（<code>boxes = boxes[keep_mask]</code> 一行），也因为很多框架的标注格式里<em>根本没有「ignore」这个东西</em>。于是「可见比例 40% 的目标被删掉」就成了默认行为，而图像里那 40% 还清清楚楚地留在那里。",
            "<strong>这在 TSR 里是致命的，因为「目标被画面边缘截断」不是异常情况，而是每一次接近标志的必经阶段</strong>：标志从画面上方进入视野，先露出下半截，再逐渐完整。如果流水线把「露出一半」的样本统统标成背景，模型学到的就是「半截标志 = 无」。<em>症状是首次检出距离系统性偏近、图像上边缘区域召回明显低于中心区域</em>——而这两个指标在标准 mAP 里根本看不见（C55 模块 05 的分桶评测就是为了让它们显形）。<strong>正确做法：可见比例 ∈ (0, τ) 的目标一律标为 ignore，绝不 drop。</strong>",
        ),
        H3("丢弃阈值对小目标：一条被算出来的生死线"),
        P("除了「可见比例」阈值，几乎所有实现还有一个<strong>绝对尺寸阈值</strong>（YOLOv5 的 <code>wh_thr=2</code>、albumentations 的 <code>min_area</code>、mmdet 的 <code>min_bbox_size</code>）：变换后宽或高小于 N 像素的框直接丢弃。这个参数看起来无害，实际上<strong>它单方面决定了整个系统的最大检出距离</strong>。"),
        P("用针孔模型算一遍就清楚了。1920 px 宽、60° 水平 FOV 的前视相机，焦距 <code>f = 1920 / (2·tan30°) ≈ 1663 px</code>；一块 0.6 m 的圆形限速牌在距离 <code>Z</code> 处的像素尺寸是 <code>f·S/Z</code>。训练输入 640，缩放比 1/3，于是<strong>网络看到的像素尺寸 ≈ 332.6 / Z</strong>："),
        TABLE(["<code>min_side</code>（丢弃阈值）", "对应的最大检出距离", "高速 120 km/h 下的预留反应时间", "判断"], [
            ["8 px", "<strong>41.6 m</strong>", "<strong>1.2 秒</strong>", "❌ 远处标志在标注阶段就被删光了，模型再强也没用"],
            ["4 px", "83.1 m", "2.5 秒", "⚠️ 勉强；且 4 px 的框标注误差相对量级已达 25%"],
            ["2 px", "166 m", "5.0 秒", "✅ YOLOv5 的默认值，对 TSR 是合理下限"],
            ["1 px", "333 m", "10 秒", "⚠️ 已无实际意义（1 px 目标不可检），只是不再人为设限"],
        ]),
        CALLOUT("danger", "<p>把上面两条合起来，就是几何增强里最贵的一个 bug：<strong>「变换后过小 → drop」+「被截断 → drop」，两条规则叠加，把「远处的、刚进入视野的标志」这一整类样本从训练集里系统性地清除了，并且把它们变成了背景监督</strong>。而这一类恰恰是 TSR 最关键的样本——<em>早发现才有时间反应</em>。<strong>症状极具迷惑性</strong>：训练集/验证集的 mAP 都正常（因为验证集不做增强，但它也用同一份「已清洗」的标注做匹配），只有实车路测时才发现「标志总是到了近处才跳出来」。<em>排查入口：把增强前后的目标尺寸直方图画出来对比，看小尺寸桶是不是整段消失了。</em></p>", "两条 drop 规则叠加 = 远距离样本被系统性清除"),
    ])),
    ("flip", "语义敏感变换的禁区：水平翻转在 TSR 里为什么是错的", "".join([
        P("这是本模块<strong>最值得在面试里主动提</strong>的一节。它足够具体、足够反直觉、又完全不需要复杂知识——面试官能立刻判断你是「跑过 TSR」还是「跑过 COCO 然后把配置抄过来了」。"),
        DUAL(
            "水平翻转在通用检测里是<strong>最安全、性价比最高</strong>的增强：镜像一只猫还是猫，镜像一辆车还是车，标签一个字都不用改，几乎零成本地把数据翻倍。所以它出现在<em>每一份</em>默认配置里（<code>fliplr=0.5</code>）。而交通标志是<strong>人为设计的符号系统</strong>——它的全部意义就在于形状、颜色和<em>朝向</em>所承载的约定。<strong>镜像一个「向左转弯」，它在物理世界里就是「向右转弯」；镜像一个限速 60，你得到的是一个人类从未见过、也不该存在的图案。</strong>",
            "更严重的是<strong>文字与数字</strong>。指路牌上的地名、限速牌上的数字、停车让行牌上的「停 / STOP」，镜像之后全部变成不存在的字形。而这些牌子往往<em>是数据集里占比最大的类别</em>（限速牌在 TT100K 中是绝对的头部类）。于是「翻转 50% 的图」实际效果是：<strong>把一半的头部类样本换成了现实中不存在的假图，同时给方向类标错了标签</strong>。<em>这两件事都属于模块 00 判据①（保标签语义）的硬失败——不是收益小，是学错。</em>",
        ),
        H3("三问判定法：给任意标志类别定档"),
        ASCII("""对每个标志类别问三个问题，得到三档之一。这套流程可以直接写成代码。

  Q1  外观是否左右镜像对称？（几何）
       │
       ├─ 是 ──> Q2  语义是否含方向性（左/右、顺/逆、单向）？
       │              ├─ 否 ──────────────────> 【SAFE】   直接翻
       │              └─ 是 ──────────────────> 走 Q3
       │
       └─ 否 ──> Q2' 语义是否含方向性？
                      ├─ 是 ──────────────────> 走 Q3
                      └─ 否 ──────────────────> 【FORBID】
                             （不对称但无方向语义：含文字/数字、人形图案 ——
                               镜像后是现实中不存在的图案，且没有对应类别）

  Q3  标签集里是否存在它的镜像类别？
       ├─ 是 ──> 【SWAP】  可以翻，**但必须同时把标签换成镜像类**
       └─ 否 ──> 【FORBID】（翻了就没有正确标签可给）""")
        ,
        TABLE(["档位", "判定条件", "TSR 中的典型类别", "正确处理"], [
            ["<strong>SAFE</strong>", "外观左右对称 <strong>且</strong> 语义无方向性", "禁止通行、禁止驶入、禁止鸣笛、注意信号灯、停车检查、圆形无文字禁令牌", "直接翻，标签不变"],
            ["<strong>SWAP</strong>", "语义含方向 <strong>且</strong> 标签集里有镜像类", "向左转弯↔向右转弯、禁止向左转弯↔禁止向右转弯、左侧通行↔右侧通行、向左急弯↔向右急弯、左侧变窄↔右侧变窄、左侧合流↔右侧合流", "翻转 + <strong>同时把标签换成镜像类</strong>"],
            ["<strong>FORBID</strong>", "其余全部", "<strong>所有限速牌（含数字）</strong>、停车让行 STOP、所有指路牌（含地名）、注意行人、注意儿童、注意落石等含不对称图形且无镜像类的警告牌", "<strong>绝不翻转</strong>；若必须翻整图，该目标标为 <code>ignore</code>"],
        ]),
        H3("三个大多数人想不到的推论"),
        OL([
            "<strong>判定是逐目标的，但翻转作用在整张图上——两者是「与」的关系。</strong>一张图里只要有<em>一个</em> FORBID 类目标，整张图就不能翻。TSR 场景里 FORBID 类（限速牌 + 指路牌）本身就占大头——按 TT100K 风格的长尾频率算，<strong>单个目标不可翻的概率就有 61%</strong>；加上一张图常有 2–4 块牌子，<strong>整图可翻转的概率只剩 23%</strong>。notebook 里会把这条链算完：<em>你配置里写的 <code>fliplr=0.5</code>，真正被翻的图只有约 <strong>12%</strong>；而其中真正带来新信息的目标（SWAP 类）只占全部目标的 <strong>2.5%</strong></em>。这个增强基本等于没开，却让你误以为已经做了数据增强。",
            "<strong>对 SAFE 类，翻转的信息增益接近于零。</strong>这一条尤其反直觉：SAFE 的定义就是「外观左右镜像对称」，那么<em>把这个标志的图块镜像之后，它逐像素等于原图</em>。检测器从这个目标身上学到的东西一点没变，唯一变的是它周围的背景（道路走向、杆件位置）。<strong>所以在 TSR 里，翻转要么不安全（FORBID/SWAP），要么安全但没用（SAFE）</strong>——这就是为什么结论是「默认关掉」。",
            "<strong>SWAP 档是真正的加分答案。</strong>大多数人答到「左转会变右转所以不能翻」就停了；能接着说出「<em>但如果标签集里同时有左转和右转两个类，就可以翻转并交换标签，这样反而给稀有的那一侧补了样本</em>」，才说明你真的想过怎么用它。<em>「向左急转弯」这类方向牌在数据集里通常是长尾类，而左右两侧的样本数往往严重不均衡——SWAP 式翻转正好把两边拉平，这是一个免费的类别平衡手段。</em>",
        ]),
        CALLOUT("intuition", "把这一节压缩成一个可以直接在面试里说的段落：<strong>「通用检测里 fliplr=0.5 是白送的，但 TSR 不能直接抄。交通标志是符号系统，镜像会改变语义：向左转弯会变成向右转弯，限速数字和地名会变成不存在的字形。我的做法是按类别分三档——外观对称且无方向语义的可以直接翻；有方向语义且标签集里存在镜像类的，翻转的同时交换标签，这还顺带平衡了左右类的样本数；其余一律禁止翻转，如果整图翻转不可避免，就把这些目标标成 ignore 而不是删掉。另外要注意判定是逐目标的而翻转是整图的，两者是与的关系，所以实际生效率远低于配置里的概率——我们量化过，大概只有百分之几。而且对完全对称的标志，镜像后图块逐像素不变，信息增益本来就接近零。所以我们最后是默认关掉水平翻转的。」</strong> <em>——这段话里有判断、有分类、有量化、有结论，是一个完整的工程答案。</em>"),
    ])),
    ("letterbox", "多尺度训练与 letterbox：正变换、逆变换与部署一致性", "".join([
        P("<span class=\"term\">letterbox</span>（信箱填充）是把任意尺寸的图缩放到网络固定输入尺寸、同时<strong>保持长宽比</strong>的标准做法：按最小比例缩放，剩下的空间用常数值填充。它不是「增强」，但它同样改变坐标，同样需要一个 <code>g_T</code>——<strong>而且是全流水线里唯一一个必须与推理端逐像素一致的算子</strong>。"),
        ASCII("""1920 x 1080  --letterbox 640x640-->  640 x 640

    r = min(640/1920, 640/1080) = min(0.3333, 0.5926) = **0.3333**
    new = (round(1920*r), round(1080*r)) = (640, 360)
    dw, dh = 640-640, 640-360 = (0, 280)
    居中填充: left = dw/2 = 0,  top = dh/2 = **140**

    +--------------------------------------------------+  y=0
    |################ padding (114,114,114) ###########|
    +--------------------------------------------------+  y=140
    |                                                  |
    |              缩放后的图像 640 x 360               |
    |                                                  |
    +--------------------------------------------------+  y=500
    |################ padding ##########################|
    +--------------------------------------------------+  y=640

    正变换  x' = x*r + left        y' = y*r + top
    逆变换  x  = (x' - left)/r     y  = (y' - top)/r     <-- **推理端必须做这一步**

    ⚠️ 如果推理端漏了 "- top"：y 误差 = top/r = 140/0.3333 = **420 像素**
       所有框整体下移 420 px —— 而模型本身完全正确。""")
        ,
        P("<strong>逆变换是 letterbox 存在的全部理由</strong>：网络输出的框在 640×640 的 letterbox 坐标系里，而下游（跟踪、融合、地图匹配、VLA 接口）需要原图坐标。这一步写错，模型再准也白搭。C60 模块 04 把「letterbox 逆变换写错」列为<em>「框整体偏移」类问题的头号成因</em>，本节是它的入口。"),
        TABLE(["分歧点", "YOLOv5 <code>letterbox()</code>", "torchvision / mmdet <code>Resize+Pad</code>", "手写 C++ 版常见做法", "不一致的后果"], [
            ["缩放比", "<code>min(H_t/H, W_t/W)</code>，<code>scaleup=False</code> 时不放大", "同（<code>keep_ratio=True</code>）", "有时误用各轴独立缩放", "<strong>长宽比被拉伸，框全错</strong>"],
            ["填充位置", "<strong>居中</strong>（<code>dw/2, dh/2</code>）", "<strong>右下</strong>（图像贴左上角）", "两种都常见", "<strong>整体偏移 pad/r 像素（本例 420 px）</strong>"],
            ["填充值", "<strong>114</strong>（灰）", "0（黑）", "0 或 128", "边缘特征分布不同；影响小但真实存在"],
            ["stride 对齐", "<code>auto=True</code> 时 pad 到 32 的倍数 → <strong>输出不是 640×640</strong>", "否", "否", "<strong>导出 ONNX/TRT 时必须 <code>auto=False</code></strong>，否则 shape 对不上"],
            ["取整", "<code>int(round(w*r))</code>", "有的实现用 <code>floor</code>", "常用 <code>(int)</code> 截断", "<strong>亚像素偏移；对 8 px 的小标志 IoU 掉到 0.68</strong>——而且<strong>只在源尺寸不整除时暴露</strong>"],
        ]),
        DUAL(
            "最后一行值得单独说，因为它是唯一一个「看起来无害」的分歧，<strong>而且它有一个让人后背发凉的性质：在标准 1920×1080 上它根本不出现</strong>。因为 <code>1080 × (640/1920) = 360.0</code> 恰好整除，<code>round</code> 与 <code>floor</code> 给出同一个数。<em>可一旦换成车端真实用的 ROI 裁剪图</em>（TSR 常把天空与引擎盖切掉，例如 1920×800），<code>800 × 0.33333 = 266.67</code>——<code>round</code> 得 267、<code>floor</code> 得 266，于是 <code>top</code> 一个是 186.5、一个是 187.0。<strong>0.5 个 padding 像素 = 原图 1.5 像素</strong>：对一辆 200 px 的车完全无感，对一块 <strong>8 px 的远处限速牌，IoU 从 1.00 掉到 0.68</strong>（notebook 里会算给你看）。<em>而 0.68 恰好落在很多训练分配策略的阈值附近</em>，足以让这个目标时而被分为正样本、时而被分为负样本。<strong>「在开发机上永远复现不了、一上车就出现」——这正是它能长期存活的原因。</strong>",
            "所以 letterbox 的正确工程做法是<strong>把 <code>(r, left, top)</code> 三元组作为「元数据」跟着图像一路传下去，而不是在推理端重新算一遍</strong>。YOLOv5 的 <code>scale_boxes(img1_shape, boxes, img0_shape, ratio_pad=...)</code> 就提供了这个接口——<em><code>ratio_pad</code> 参数存在的唯一理由，就是让你不要重算</em>。重算的风险在于：Python 端和 C++ 端用的是不同的取整、不同的填充约定、甚至不同的输入尺寸（有没有 stride 对齐）。<strong>「传元数据而不是重算」是消除这类不一致的通用手法</strong>，C60 模块 01 会把同样的思路用在归一化参数与通道顺序上。",
        ),
        H3("多尺度训练：letterbox 的近亲"),
        P("<span class=\"term\">多尺度训练</span>（multi-scale training）每隔若干个迭代随机换一个输入尺寸（如从 <code>{480, 512, …, 800}</code> 里采样），本质上是「把缩放增强做在 letterbox 的目标尺寸上」。它对 TSR 的价值很高——因为<strong>尺度是 CNN 唯一不能自动泛化的维度</strong>——但有两个工程代价必须知道："),
        UL([
            "<strong>同一 batch 内尺寸必须一致</strong>，所以是「每 N 个 iteration 换一次」而不是「每张图换一次」。这让尺度的采样粒度变粗，需要更长的训练才能覆盖。",
            "<strong>推理端只能选一个固定尺寸</strong>（TensorRT 的动态 shape 要配 optimization profile，且多档 profile 会拖慢构建、增加显存）。<em>所以多尺度训练是纯训练期技巧，推理端仍然是单一尺寸</em>——这本身就是一个训练-推理的分布差异，属于模块 00 判据③要显式对齐的东西：<strong>训练时尺度分布的中位数，应该对准推理时那个固定尺寸。</strong>",
        ]),
        CALLOUT("warn", "一个高频面试追问：<strong>「letterbox 的 padding 会不会影响检测？」</strong> 会，而且有两条路径。① <em>感受野污染</em>：padding 区域是常数，靠近边界的目标其感受野里混入大量恒定值，特征统计与图像中心不同——这是靠近画面边缘的目标召回略低的成因之一。② <em>正样本分配</em>：anchor/网格是按 letterbox 后的尺寸铺的，padding 区域也会铺上网格点，这些点永远是负样本，<strong>稀释了正负样本比</strong>（本例中 padding 占 640×640 的 43.75%，接近一半的网格点是纯背景）。<em>这也是 <code>auto=True</code>（只 pad 到 stride 倍数）存在的理由——它把 padding 压到最小。但代价是输出尺寸不固定，导出时必须关掉。</em>"),
    ])),
    ("crop", "随机裁剪家族：它同时解决和制造问题", "".join([
        P("随机裁剪是检测里最有力也最危险的几何增强。它有两个方向相反的变体，很多人把它们混为一谈："),
        TABLE(["算子", "做什么", "对目标像素尺寸的影响", "解决什么", "制造什么问题"], [
            ["<strong>RandomCrop（zoom-in）</strong>", "裁一块小区域，再 resize 回训练尺寸", "<strong>放大</strong>：裁 480×480 再放到 640，目标 ×1.33", "<strong>小目标的最直接解法</strong>——它直接提高了目标的相对尺寸", "<strong>破坏上下文与位置先验</strong>；可能把目标切成半个"],
            ["<strong>Expand / Zoom-out</strong>", "把图贴到一张更大的画布上（其余填均值），再 resize 回来", "<strong>缩小</strong>：贴到 2× 画布，目标 ×0.5", "<strong>制造更多小目标</strong>，补足小尺寸桶的样本", "画布边界是人造的；缩得太小则目标不可检"],
            ["<strong>RandomIoUCrop（SSD 式）</strong>", "随机采 patch，<strong>要求与至少一个 GT 的 IoU ≥ 阈值</strong>（阈值从 {0.1,0.3,0.5,0.7,0.9,∅} 随机选）", "放大，但保证至少一个目标「基本完整」", "在 zoom-in 的同时<strong>避免把所有目标都切碎</strong>", "阈值低时仍会产生大量半截目标 → 回到越界策略问题"],
            ["<strong>Mosaic（模块 03）</strong>", "4 图拼接后整体缩放", "<strong>缩小</strong>：每图只占 1/4 → 目标 ×0.5", "同时给小目标 + 上下文多样性 + 批内多样性", "拼接图不属于真实分布 → 必须 close-mosaic"],
        ]),
        DUAL(
            "「RandomCrop 是小目标的最直接解法」这一条值得记住，它的道理很朴素：<strong>小目标难，是因为它在特征图上占的格子少</strong>（stride 32 时一个 8 px 的目标只占 0.25 个格子，见 C57 模块 01）。裁一块小区域再放大回训练尺寸，等价于<em>提高了这个目标的有效分辨率</em>，它在特征图上占的格子数按面积平方增长。<strong>从 1920×1080 直接 letterbox 到 640，一个 60 m 外的标志只有 5.5 px；先裁 480×480 再 resize 到 640，同一个标志有 22 px</strong>——这是 4 倍的线性尺寸差距，几乎决定了它能不能被检出。",
            "但代价同样具体：<strong>随机裁剪会摧毁位置先验</strong>。交通标志在真实图像里几乎从不出现在画面下半部（那是路面），它们集中在上部与路侧——这是一个免费且极强的先验，模型会自动学到它，用来压制广告牌与车身贴纸的误检。<em>如果裁剪窗口在整张图上均匀采样，标志的归一化纵坐标分布会从「集中在 0.15–0.45」被拉平成「近似均匀」</em>，模型就失去了这条线索。<strong>症状是 FP 明显上升，尤其是画面下半部的广告牌与后车贴纸被误检成标志</strong>（C55 模块 03 把这类误检单独列为一个失效模式）。notebook 会把这个分布的展宽量化出来。",
        ),
        CALLOUT("intuition", "所以 TSR 里裁剪的正确用法不是「关掉」也不是「随便开」，而是<strong>加约束的裁剪</strong>：① <em>限制裁剪窗口的纵向范围</em>（只在图像上部 60% 采样中心），保住位置先验；② <em>用 RandomIoUCrop 而不是纯随机裁剪</em>，保证每次至少有一个目标基本完整；③ <em>被切断的目标一律 <code>ignore</code> 而不是 <code>drop</code></em>（第 5 节）；④ <em>裁剪与 zoom-out 成对使用</em>，让尺度分布同时向两端展开而不是单向偏移。<strong>这四条合起来，就是「既拿到小目标的收益，又不牺牲位置先验」的配方</strong>——而它们全都是从「这个变换在部署环境里对应什么」推出来的，没有一条是靠调参试出来的。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("几何增强看上去是一个「已经做完了」的题目——仿射矩阵是 19 世纪的数学，四角法是十几行代码。但把它放到检测、放到量产系统里，仍有几处真正开放的问题。"),
        UL([
            "<strong>轴对齐框本身就是问题的根源</strong>。四角法的三重失真（膨胀、过估计、不可逆）全部来自「输出必须是轴对齐矩形」这个约束。<span class=\"term\">有向框</span>（OBB）在遥感检测里已经成熟——<em>RoI Transformer</em>（Ding et al., CVPR 2019）、<em>Gaussian Wasserstein Distance loss</em>（Yang et al., ICML 2021，把框建模成 2D 高斯从而绕开角度的周期性问题）——但它们在车载 TSR 上几乎没有采用。<strong>开放问题：在旋转幅度本来就小（±5°）的场景里，OBB 的收益能否覆盖「检测头 + NMS + 评测协议全换一套」的成本？</strong>目前的经验答案是「不能」，但缺少系统的量化。",
            "<strong>增强正确性的自动验证仍是空白</strong>。本模块反复强调「用掩码算真实紧框做断言」，但真实数据集只有框、没有掩码，这条断言在生产环境里跑不起来。<em>能否用一个预训练的分割模型（SAM 之类）自动生成掩码，从而把「增强流水线的几何一致性」变成 CI 里的一条自动检查</em>？这是一个工程价值极高、但还没有标准方案的方向——目前所有团队都靠「画出来看一眼」。",
            "<strong>语义敏感变换的自动发现</strong>。翻转白名单目前完全靠人工维护，而标志类别有成百上千种、还在随法规更新。<em>能否从数据里自动学出镜像对</em>——例如统计「把某类样本镜像后，模型把它判成哪一类」，若稳定地判成另一个已知类，就自动建立 SWAP 关系；若判成一个低置信度的混合分布，就判为 FORBID。<strong>这个思路有明显的鸡生蛋问题（需要一个已经训好的模型），但对「白名单维护」这个长期负担是唯一有希望的自动化路径。</strong>",
            "<strong>可微增强与增强参数的联合优化</strong>。<em>Spatial Transformer Networks</em>（Jaderberg et al., NeurIPS 2015）证明了几何变换可以放进网络里端到端学；<em>Faster AutoAugment</em>、<em>DADA</em> 等把增强策略的搜索变成可微优化。但检测场景下有一个特殊障碍：<strong>标签变换 <code>g_T</code>（四角法 + min/max + 丢弃规则）本身是不可微的</strong>——<code>min/max</code> 有次梯度尚可，「丢弃阈值」则是硬阈值。<em>如何让「增强强度」这个超参可微，是把 AutoAugment 类方法推广到检测的核心障碍之一。</em>",
            "<strong>物理正确的透视增强</strong>。目前的透视增强是在图像平面上随机采一个单应矩阵，与真实的相机-标志几何毫无关系。<em>如果已知相机内参与标志的大致法向，就可以生成物理上正确的视角变化</em>（标志平面绕竖直轴旋转 30° 时图像应该怎么变）。这在自动驾驶里是完全可行的——内参是已知的、标志几乎都是竖直平面——但几乎没有开源实现。<strong>「用已知的物理约束替代随机采样」是增强设计里一个被系统性低估的方向。</strong>",
            "<strong>训练-部署几何一致性的形式化验证</strong>。letterbox 的正逆变换、取整规则、填充约定，目前靠人工对拍（C60 模块 01/04）。<em>能否把这些几何变换写成一份可执行的规范（spec），让 Python 训练端和 C++ 推理端各自实现后自动做属性检查</em>（例如「对任意输入尺寸，forward 后 inverse 的往返误差 &lt; 0.5 px」）？<strong>这类「基于属性的测试」在编译器与数值库里很常见，在感知流水线里却几乎没人做</strong>——而这恰恰是最容易出现静默不一致的地方。",
        ]),
        CALLOUT("paper", "必读：<em>YOLOv5 / YOLOv8 的 <code>random_perspective()</code> 与 <code>letterbox()</code> 源码</em>（ultralytics 仓库 <code>utils/augmentations.py</code>——工业界事实标准的几何增强实现，四角法、<code>wh_thr</code>/<code>ar_thr</code>/<code>area_thr</code> 三重过滤、<code>scale_boxes</code> 的 <code>ratio_pad</code> 接口全在里面）★；<em>Albumentations: Fast and Flexible Image Augmentations</em>（Buslaev et al., Information 2020，<code>BboxParams</code> 的 <code>min_area</code>/<code>min_visibility</code> 语义是本模块第 5 节的直接对应）★；<em>SSD: Single Shot MultiBox Detector</em>（Liu et al., ECCV 2016，附录里的 RandomIoUCrop 与 Expand 是「裁剪家族」的出处）★；<em>Learning Data Augmentation Strategies for Object Detection</em>（Zoph et al., ECCV 2020，含 bbox 级几何算子的搜索空间设计）；<em>Spatial Transformer Networks</em>（Jaderberg et al., NeurIPS 2015，可微几何变换的起点）；<em>Learning RoI Transformer for Oriented Object Detection in Aerial Images</em>（Ding et al., CVPR 2019）与 <em>Rethinking Rotated Object Detection with Gaussian Wasserstein Distance Loss</em>（Yang et al., ICML 2021，有向框绕开四角法失真的两条主线）；<em>Traffic-Sign Detection and Classification in the Wild</em>（Zhu et al., CVPR 2016，TT100K——本模块尺寸分布与长尾频率的依据）★。相邻课程：C55 模块 03（失效模式：边缘截断与广告牌误检）、C57 模块 01/05（小目标的 IoU 敏感性与像素尺寸物理推导）、C60 模块 01/04（预处理一致性与 letterbox 逆变换对拍）、C56 模块 03（Mosaic 的框裁剪与丢弃规则）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 几何增强与标注同步（仿射矩阵 / 四角法 / 框膨胀 / 越界三分法 / letterbox 逆变换 / 翻转白名单）

纯 numpy + 标准库，CPU 可跑，不联网。

**核心命题**：几何增强改的是坐标，而标注也是坐标——所以**两条轨道必须用同一个变换对象**。
本 notebook 把这条纪律落成可执行的代码与断言。

你会亲手实现：

1. **齐次仿射矩阵**（平移/缩放/旋转/错切/透视）与「绕某点变换」的三明治结构
2. **四角法 `warp_boxes`**，以及**无条件的透视除法**（忘了它就是透视增强的头号 bug）
3. **旋转导致的框膨胀**：闭式公式、数值验证、以及**从可接受膨胀率反解最大旋转角**
4. **四角法对圆形标志的过估计**：45° 时标注 IoU 只剩 0.50——这是算法引入的错标注
5. **越界三分法 keep / ignore / drop**，以及 `min_side` 如何单方面锁死最大检出距离
6. **letterbox 正逆变换**，复现 4 种真实世界的逆变换 bug 并量化像素误差
7. **翻转三问判定 + TSR 白名单**，量化「整图可翻率」与「对称类信息增益为零」
8. **RandomIoUCrop** 的 zoom-in 收益与**位置先验被摧毁**的代价

> 心智模型：**bbox 不是图像的一部分，它是图像的一个「投影」。
> 变换图像时，你必须把这个投影重新算一遍——而 min/max 会让它每次都变得更差一点。**"""),

    md("""## 1 · 齐次坐标与仿射矩阵

把所有几何变换合成**一个 3×3 矩阵**，不是为了代码短，而是为了三件事：
① 只插值一次（三次双线性插值足以糊掉 15 px 标志上的限速数字）；
② 「绕某点变换」有明确写法；③ 图像与标注**用的是同一个对象**，不可能不同步。"""),

    code("""import numpy as np, math, collections, itertools
np.set_printoptions(suppress=True, precision=3)
rng = np.random.default_rng(7)

# ── 基本矩阵（齐次坐标，点写成列向量 [x, y, 1]^T）──
def M_T(tx, ty):
    return np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], float)

def M_S(sx, sy=None):
    sy = sx if sy is None else sy
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], float)

def M_R(deg):
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

def M_H(deg_x, deg_y=0.0):                       # 错切 shear
    return np.array([[1, math.tan(math.radians(deg_x)), 0],
                     [math.tan(math.radians(deg_y)), 1, 0],
                     [0, 0, 1]], float)

def M_P(px, py=0.0):                             # 透视：第三行不再是 [0,0,1]
    return np.array([[1, 0, 0], [0, 1, 0], [px, py, 1]], float)

def about(M, cx, cy):
    # **绕 (cx,cy) 做变换** = 移到原点 -> 变换 -> 移回去。手写仿射最常错的地方。
    return M_T(cx, cy) @ M @ M_T(-cx, -cy)

def compose(*Ms):
    out = np.eye(3)
    for M in Ms:
        out = out @ M                            # **从右往左作用**：最右边的先作用在点上
    return out

# ── 顺序是语义的一部分：矩阵乘法不可交换 ──
A = compose(M_T(100, 0), M_S(0.5))               # 先缩放，再平移
B = compose(M_S(0.5), M_T(100, 0))               # 先平移，再缩放
pa = (A @ np.array([0., 0., 1.]))[:2]
pb = (B @ np.array([0., 0., 1.]))[:2]
print('原点 (0,0) 经过')
print(f'  先缩放0.5 再平移100 -> {pa}')
print(f'  先平移100 再缩放0.5 -> {pb}')
assert not np.allclose(A, B), '矩阵乘法不可交换'
assert abs(pa[0] - pb[0] - 50) < 1e-9, '两种顺序差 50 像素'

# ── 「绕中心旋转」的不动点 ──
Mc = about(M_R(90), 5, 5)
fixed = (Mc @ np.array([5., 5., 1.]))[:2]
corner = (M_R(90) @ np.array([5., 5., 1.]))[:2]  # 绕原点转：中心被甩走了
print(f'\\n绕(5,5)转90度: (5,5) -> {fixed}   (不动点 ✅)')
print(f'绕原点转90度  : (5,5) -> {corner}   (整幅图被甩出画面 ❌)')
assert np.allclose(fixed, [5., 5.])
assert not np.allclose(corner, [5., 5.])
print('\\n✅ 矩阵工具就位。记住 T(c) · M · T(-c) 这个三明治结构。')"""),

    md("""## 2 · 四角法 `warp_boxes`：bbox 跟随任意变换

轴对齐 bbox 在旋转/错切/透视下**不是封闭的**，所以统一做法是：
**变换 4 个角点 → 取轴对齐外接框**。

注意 `apply_M` 里**无条件做透视除法** `x' = x_h / w_h`：
仿射时 `w_h = 1`，这是恒等操作；透视时它是必需的。
**忘记这一步是透视增强的头号 bug，且幅度小的时候误差也小，能潜伏很久。**"""),

    code("""def apply_M(M, pts):
    pts = np.asarray(pts, float).reshape(-1, 2)
    h = np.concatenate([pts, np.ones((len(pts), 1))], axis=1) @ M.T
    return h[:, :2] / h[:, 2:3]                  # ← 无条件透视除法

def apply_M_naive(M, pts):                       # ❌ 忘记透视除法的错误版本
    pts = np.asarray(pts, float).reshape(-1, 2)
    h = np.concatenate([pts, np.ones((len(pts), 1))], axis=1) @ M.T
    return h[:, :2]

def warp_boxes(boxes, M):
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    if len(boxes) == 0:
        return boxes.copy()
    x1, y1, x2, y2 = boxes.T
    corners = np.stack([x1, y1, x2, y1, x2, y2, x1, y2], axis=1).reshape(-1, 2)
    p = apply_M(M, corners).reshape(len(boxes), 4, 2)
    return np.concatenate([p.min(axis=1), p.max(axis=1)], axis=1)

def box_area(b):
    b = np.asarray(b, float).reshape(-1, 4)
    return np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)

def box_iou(a, b):
    a = np.asarray(a, float).reshape(-1, 4); b = np.asarray(b, float).reshape(-1, 4)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[..., 0] * wh[..., 1]
    return inter / np.maximum(box_area(a)[:, None] + box_area(b)[None, :] - inter, 1e-12)

BOX = np.array([[0., 0., 40., 40.]])             # 一块 40x40 的方框（圆形标志的外接框）
print('恒等   ', warp_boxes(BOX, np.eye(3))[0])
print('平移+10,-5', warp_boxes(BOX, M_T(10, -5))[0])
print('缩放 2x ', warp_boxes(BOX, M_S(2))[0])
print('绕中心转90度', warp_boxes(BOX, about(M_R(90), 20, 20))[0], '  <- 正方形转 90 度：不变')
assert np.allclose(warp_boxes(BOX, np.eye(3)), BOX)
assert np.allclose(warp_boxes(BOX, M_T(10, -5))[0], [10, -5, 50, 35])
assert np.allclose(warp_boxes(BOX, M_S(2))[0], [0, 0, 80, 80])
assert np.allclose(warp_boxes(BOX, about(M_R(90), 20, 20)), BOX)

RECT = np.array([[0., 0., 20., 10.]])            # 非正方形：转 90 度 -> 宽高互换，面积不变
w90 = warp_boxes(RECT, about(M_R(90), 10, 5))[0]
print('\\n20x10 框绕中心转90度 ->', w90, ' 面积', box_area([w90])[0], '(原', box_area(RECT)[0], ')')
assert np.allclose(box_area([w90]), box_area(RECT))

# ── 忘记透视除法的后果 ──
Mp = M_P(2e-4, 0.0)                              # 一个很温和的透视
pt = np.array([[640., 320.]])
ok, bad = apply_M(Mp, pt)[0], apply_M_naive(Mp, pt)[0]
err = float(np.abs(ok - bad).max())
print(f'\\n透视 px=2e-4，点 (640,320):  正确 {ok}   忘记除法 {bad}   误差 {err:.1f} px')
assert err > 50, '忘记透视除法在图像边缘会造成几十像素的误差'
print('⚠️  幅度小时误差也小（w≈1），所以这个 bug 能在代码库里潜伏很久 ——')
print('    直到有人把 perspective 从 0.0005 调到 0.005，框开始莫名其妙地偏。')
print('✅ 对策：角点变换函数**无条件**做透视除法，仿射时它只是恒等操作。')"""),

    md("""## 3 · 旋转导致的框膨胀：算到小数点后

设原框 `w × h`，绕中心旋转 `θ`，四角外接框的宽高是
`w|cosθ| + h|sinθ|` 与 `w|sinθ| + h|cosθ|`。展开相乘可得一个很干净的闭式：

$$\\frac{A'}{A} = 1 + \\frac{1}{2}\\,|\\sin 2\\theta|\\left(\\frac{w}{h} + \\frac{h}{w}\\right)$$

三个推论：**膨胀在 45° 最大（不是 90°）**；**正方形框膨胀最小**（45° 时正好 2.00×）；
**细长框膨胀更狠**（3:1 的指路牌 45° 时 2.67×）。"""),

    code("""def inflate_ratio(w, h, deg):
    t = math.radians(deg); c, s = abs(math.cos(t)), abs(math.sin(t))
    return ((w * c + h * s) * (w * s + h * c)) / (w * h)

def inflate_closed(w, h, deg):
    return 1 + 0.5 * abs(math.sin(2 * math.radians(deg))) * (w / h + h / w)

# 闭式 vs 展开式 vs 真实 warp_boxes：三者必须一致
for deg in range(0, 181, 5):
    assert abs(inflate_ratio(40, 40, deg) - inflate_closed(40, 40, deg)) < 1e-9
    assert abs(inflate_ratio(60, 20, deg) - inflate_closed(60, 20, deg)) < 1e-9
    got = box_area(warp_boxes(BOX, about(M_R(deg), 20, 20)))[0] / box_area(BOX)[0]
    assert abs(got - inflate_ratio(40, 40, deg)) < 1e-9, deg
print('✅ 闭式公式 / 展开式 / warp_boxes 实测，三者在 0-180 度上完全一致')

print(f"\\n{'θ':>5s} {'正方形40x40':>12s} {'3:1指路牌':>11s} {'圆形标志框内前景占比':>20s} {'与真实紧框IoU':>14s}")
for deg in [0, 5, 10, 15, 30, 45, 60, 90]:
    t = math.radians(deg); c, s = abs(math.cos(t)), abs(math.sin(t))
    fg = (math.pi / 4) / (c + s) ** 2            # 圆内接方框，旋转后四角框被撑大
    iou = 1.0 / (c + s) ** 2                     # 四角框 vs 真实紧框（圆是旋转不变的）
    print(f'{deg:>4d}° {inflate_ratio(40,40,deg):>11.3f}x {inflate_ratio(60,20,deg):>10.3f}x '
          f'{fg:>19.1%} {iou:>14.3f}')

assert abs(inflate_ratio(40, 40, 45) - 2.0) < 1e-9,  '正方形框 45 度 -> 面积翻倍'
assert abs(inflate_ratio(40, 40, 15) - 1.5) < 1e-9,  '正方形框 15 度 -> 已膨胀 50%'
assert abs(inflate_ratio(60, 20, 45) - 8/3) < 1e-9,  '3:1 框 45 度 -> 2.667x'
assert inflate_ratio(40, 40, 90) < inflate_ratio(40, 40, 45), '最糟的是 45 度，不是 90 度'
print('\\n⚠️  仅仅 15 度，正方形框的面积就已经膨胀 50% —— 多出来的全是背景。')
print('    模型被反复告知「框住一半背景也算对」，定位头就这样被慢慢教松：')
print('    典型指纹是 **AP50 正常但 AP75 明显偏低**。')

# ── 从「可接受的膨胀率」反解最大旋转角（写进配置评审清单）──
def max_rot_angle(w, h, max_inflate):
    k = (max_inflate - 1) / (0.5 * (w / h + h / w))
    return 45.0 if k >= 1 else math.degrees(math.asin(k)) / 2

print(f"\\n可接受膨胀 <=35% 时的旋转角上限：")
for (w, h, name) in [(40, 40, '正方形（圆形/方形标志）'), (60, 30, '2:1'), (60, 20, '3:1 横向指路牌')]:
    print(f'  {name:<22s} |θ| <= {max_rot_angle(w, h, 1.35):5.2f}°')
assert abs(max_rot_angle(40, 40, 1.35) - 10.24) < 0.05
assert abs(max_rot_angle(60, 20, 1.35) - 6.06) < 0.05
assert max_rot_angle(60, 20, 1.35) < max_rot_angle(40, 40, 1.35), '细长框上限更严'
print('\\n✅ 「我不是选了个 ±10°，我是从可接受的标注退化反推出来的」—— 面试答案的正确形状。')"""),

    code("""# ── 四角法的过估计：对**旋转不变**的形状（圆形禁令牌！）它给出的框是**错的** ──
def circle_pts(cx, cy, r, n=512):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)

def ngon_pts(cx, cy, r, k, rot_deg=0.0):
    a = np.linspace(0, 2 * np.pi, k, endpoint=False) + math.radians(rot_deg)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)

def tight_bbox(pts):
    pts = np.asarray(pts, float)
    return np.array([pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()])

def poly_area(pts):                              # shoelace
    x, y = np.asarray(pts, float).T
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

SHAPES = {
    '圆形禁令牌(旋转不变)': circle_pts(20, 20, 20),
    '三角警告牌':          ngon_pts(20, 20, 20, 3, rot_deg=-90),
    '方形指示牌(填满框)':   np.array([[0., 0.], [40., 0.], [40., 40.], [0., 40.]]),
}
print(f"{'形状':<22s} {'θ':>4s} {'四角框':>28s} {'真实紧框':>28s} {'标注IoU':>8s} {'框内前景':>9s}")
for name, pts in SHAPES.items():
    orig = tight_bbox(pts)
    cx, cy = (orig[0] + orig[2]) / 2, (orig[1] + orig[3]) / 2
    for deg in [0, 45]:
        M = about(M_R(deg), cx, cy)
        four = warp_boxes([orig], M)[0]
        wpts = apply_M(M, pts)
        true = tight_bbox(wpts)
        iou = box_iou([four], [true])[0, 0]
        fg = poly_area(wpts) / max(box_area([four])[0], 1e-9)
        print(f'{name:<22s} {deg:>3d}° {np.round(four,1)} {np.round(true,1)} {iou:>8.3f} {fg:>9.1%}')
        # 四角框**总是包含**真实紧框（凸形状的性质）
        assert four[0] <= true[0] + 1e-6 and four[1] <= true[1] + 1e-6
        assert four[2] >= true[2] - 1e-6 and four[3] >= true[3] - 1e-6

M45 = about(M_R(45), 20, 20)
c_four = warp_boxes([tight_bbox(SHAPES['圆形禁令牌(旋转不变)'])], M45)[0]
c_true = tight_bbox(apply_M(M45, SHAPES['圆形禁令牌(旋转不变)']))
c_iou = box_iou([c_four], [c_true])[0, 0]
c_fg = poly_area(apply_M(M45, SHAPES['圆形禁令牌(旋转不变)'])) / box_area([c_four])[0]
assert abs(c_iou - 0.5) < 0.01, f'圆形标志 45 度：四角框与真实紧框 IoU 应为 0.50，实得 {c_iou:.3f}'
assert abs(c_fg - math.pi / 8) < 0.01, f'框内前景应为 π/8 = 39.3%，实得 {c_fg:.3f}'

# 对比：**恰好填满框**的形状，四角法是精确的
s_four = warp_boxes([tight_bbox(SHAPES['方形指示牌(填满框)'])], M45)[0]
s_true = tight_bbox(apply_M(M45, SHAPES['方形指示牌(填满框)']))
assert np.allclose(s_four, s_true), '目标填满框时，四角法精确'
print(f'\\n⚠️  圆形禁令牌旋转 45°：真实紧框**一点没变**（圆是旋转不变的），')
print(f'    四角法却把框撑到 √2 倍边长 —— 标注 IoU 只剩 {c_iou:.2f}，框内前景只剩 {c_fg:.1%}。')
print('    **这不是「任务变难了」（那是好事），这是「标签变错了」（那是坏事）。**')
print('✅ 而对「恰好填满框」的目标（车、行人），四角法是精确的 —— 差别就在这里。')"""),

    md("""## 4 · 越界处理：keep / ignore / drop

一句话区分：**`keep` 说「有」，`ignore` 说「不知道」，`drop` 说「没有」**。

大多数实现的默认行为是 `drop`（一行 `boxes = boxes[mask]` 就写完了），
于是「可见比例 40% 的目标被删掉、而图像里那 40% 还清清楚楚留着」成了默认行为——
**模型被明确训练成「看到半个标志 = 这里没有东西」。**"""),

    code("""def clip_split(boxes, labels, W, H, min_visible=0.5, min_side=2.0):
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    labels = np.asarray(labels)
    a0 = np.clip(boxes[:, 2] - boxes[:, 0], 0, None) * np.clip(boxes[:, 3] - boxes[:, 1], 0, None)
    c = boxes.copy()
    c[:, [0, 2]] = np.clip(c[:, [0, 2]], 0, W)
    c[:, [1, 3]] = np.clip(c[:, [1, 3]], 0, H)
    w = np.clip(c[:, 2] - c[:, 0], 0, None); h = np.clip(c[:, 3] - c[:, 1], 0, None)
    vis = np.where(a0 > 0, (w * h) / np.maximum(a0, 1e-9), 0.0)
    keep = (vis >= min_visible) & (w >= min_side) & (h >= min_side)
    drop = vis <= 0                              # 完全出画面 -> 真的没有东西
    ignore = (~keep) & (~drop)                   # 仍可见但给不出可靠框 -> 别学
    return {'keep': keep, 'ignore': ignore, 'drop': drop, 'vis': vis, 'clipped': c}

W = H = 640
DEMO = np.array([
    [100., 100., 140., 140.],     # 完全在内
    [-20., 100.,  20., 140.],     # 左边切掉一半
    [-30., 100.,  10., 140.],     # 左边切掉 3/4
    [600., 300., 660., 360.],     # 右边切掉 1/3
    [660., 300., 700., 360.],     # 完全在外
    [300.,  -4., 304.,   4.],     # 上边界，小目标，露一半
    [500., 500., 501.5, 530.],    # 极细的框（宽 1.5 px）
    [-50., -50., -10., -10.],     # 完全在外
])
LBL = np.arange(len(DEMO))
r = clip_split(DEMO, LBL, W, H, min_visible=0.5, min_side=2.0)
print(f"{'#':>2s} {'原框':>28s} {'可见比例':>8s} {'裁剪后':>28s}  归属")
for i in range(len(DEMO)):
    tag = 'keep' if r['keep'][i] else ('drop' if r['drop'][i] else 'IGNORE')
    print(f'{i:>2d} {np.round(DEMO[i],1)} {r["vis"][i]:>8.2f} {np.round(r["clipped"][i],1)}  {tag}')

assert r['keep'].sum() == 4 and r['ignore'].sum() == 2 and r['drop'].sum() == 2
assert r['ignore'][2] and r['ignore'][6], '可见比例不足、或框过细 -> ignore（不是 drop）'
assert r['drop'][4] and r['drop'][7], '只有完全出画面才 drop'
assert abs(r['vis'][1] - 0.5) < 1e-12 and r['keep'][1], 'vis 恰好等于阈值应保留'
print('\\n✅ 只有 vis == 0（完全出画面）才 drop。**其余一律 ignore，绝不删除。**')
print('   mmdet 的 gt_bboxes_ignore / COCO 的 iscrowd 就是干这个用的。')"""),

    code("""# ── min_side 单方面锁死了整个系统的最大检出距离（针孔模型）──
def focal_px(img_w, hfov_deg):
    return img_w / (2 * math.tan(math.radians(hfov_deg) / 2))

def sign_px(Z, img_w=1920, hfov=60.0, S=0.6, input_w=None):
    px = focal_px(img_w, hfov) * S / Z
    return px if input_w is None else px * input_w / img_w

def max_detect_range(min_side_px, input_w=640, sensor_w=1920, hfov_deg=60.0, sign_m=0.6):
    return focal_px(sensor_w, hfov_deg) * sign_m * (input_w / sensor_w) / min_side_px

f = focal_px(1920, 60)
print(f'相机: 1920px 宽, 60° HFOV -> 焦距 {f:.1f} px；标志物理尺寸 0.6 m；训练输入 640')
print(f"\\n{'距离':>6s} {'全分辨率像素':>13s} {'640输入下像素':>14s}")
for Z in [20, 40, 60, 80, 100]:
    print(f'{Z:>4d} m {sign_px(Z):>12.1f} {sign_px(Z, input_w=640):>14.1f}')
assert abs(sign_px(60) - 16.63) < 0.05 and abs(sign_px(60, input_w=640) - 5.54) < 0.05

SPEED = 120 / 3.6                                # 120 km/h -> m/s
print(f"\\n{'min_side':>9s} {'最大检出距离':>13s} {'120km/h 下的反应时间':>21s}  判断")
VERDICT = {8: '❌ 远处标志在标注阶段就被删光了', 4: '⚠️ 勉强；4px 框标注误差已达 25%',
           2: '✅ YOLOv5 默认值，TSR 的合理下限', 1: '⚠️ 已无实际意义，但不再人为设限'}
for ms in [8, 4, 2, 1]:
    Zmax = max_detect_range(ms)
    print(f'{ms:>7d}px {Zmax:>11.1f} m {Zmax/SPEED:>18.1f} s  {VERDICT[ms]}')

assert abs(max_detect_range(8) - 41.57) < 0.05, max_detect_range(8)
assert abs(max_detect_range(2) - 166.28) < 0.05
assert max_detect_range(2) == 4 * max_detect_range(8)
print('\\n⚠️  一个「看起来无害」的 min_side=8，把最大检出距离锁死在 41.6 米 ——')
print('    高速上只剩 1.2 秒反应时间。**模型再强也没用，样本在标注阶段就没了。**')
print('✅ 排查入口：把增强前后的目标尺寸直方图画出来对比，看小尺寸桶是不是整段消失了。')"""),

    code("""# ── 「drop 而非 ignore」制造了多少假负样本监督 ──
N_SIGNS, P_BORDER = 20000, 0.18                  # TSR 里约 18% 的标志与画面边缘相交
g = np.random.default_rng(2024)
touches = g.random(N_SIGNS) < P_BORDER
vis = np.ones(N_SIGNS)
vis[touches] = g.uniform(0.05, 1.0, touches.sum())   # 被截断的那部分，可见比例近似均匀

print(f"{'min_visible':>11s} {'保留(正样本)':>13s} {'drop策略下变成背景的**可见**目标':>32s} {'ignore策略':>11s}")
bg_counts = {}
for mv in [0.1, 0.25, 0.5, 0.9]:
    keep = vis >= mv
    bg = int(((~keep) & (vis > 0)).sum())        # 仍然可见、却被当成背景
    bg_counts[mv] = bg
    print(f'{mv:>11.2f} {int(keep.sum()):>13d} {bg:>26d} ({bg/N_SIGNS:>5.1%}) {0:>11d}')

assert bg_counts[0.9] > bg_counts[0.5] > bg_counts[0.25] > bg_counts[0.1]
assert bg_counts[0.5] > 0.06 * N_SIGNS, '阈值 0.5 时，超过 6% 的目标变成了假负样本'
per_1k = bg_counts[0.5] / N_SIGNS * 1000 * 2.5   # 按每图约 2.5 个标志换算
print(f'\\n⚠️  min_visible=0.5 + drop：每 1000 张训练图里，约有 {per_1k:.0f} 个**仍然可见**的标志')
print('    被当成了背景。而 TSR 里「目标被画面边缘截断」不是异常，是每次接近标志的必经阶段：')
print('    标志从画面上方进入视野，先露下半截，再逐渐完整。')
print('    症状：**首次检出距离系统性偏近 + 图像上边缘召回明显低于中心** ——')
print('    而这两个都在标准 mAP 里看不见（要靠 C55 模块 05 的分桶评测才显形）。')
print('✅ ignore 策略把这个数字变成 0，代价只是少了一点点监督。**没有理由不用。**')"""),

    md("""## 5 · letterbox：正变换、逆变换与四种真实 bug

`letterbox` 不是增强，是输入尺寸归一化——但它同样改坐标，
而且是**全流水线里唯一必须与推理端逐像素一致的算子**。

**逆变换是它存在的全部理由**：网络输出在 640×640 的 letterbox 坐标系里，
下游（跟踪 / 融合 / 地图匹配 / VLA 接口）要的是原图坐标。这一步写错，模型再准也白搭。
C60 模块 04 把「letterbox 逆变换写错」列为「框整体偏移」类问题的头号成因。"""),

    code("""def letterbox_params(src_hw, dst_hw, center=True, scaleup=False, stride=None, round_fn=None):
    round_fn = round if round_fn is None else round_fn
    (Hs, Ws), (Ht, Wt) = src_hw, dst_hw
    r = min(Ht / Hs, Wt / Ws)
    if not scaleup:
        r = min(r, 1.0)                          # 推理时通常不放大小图
    nw, nh = int(round_fn(Ws * r)), int(round_fn(Hs * r))
    dw, dh = Wt - nw, Ht - nh
    if stride:
        dw, dh = dw % stride, dh % stride        # auto=True：只 pad 到 stride 倍数
    left = dw / 2 if center else 0.0
    top = dh / 2 if center else 0.0
    return {'r': r, 'new': (nh, nw), 'left': left, 'top': top, 'out': (nh + dh, nw + dw)}

def lb_fwd(boxes, p):
    b = np.asarray(boxes, float).reshape(-1, 4).copy()
    b[:, [0, 2]] = b[:, [0, 2]] * p['r'] + p['left']
    b[:, [1, 3]] = b[:, [1, 3]] * p['r'] + p['top']
    return b

def lb_inv(boxes, r, left, top, ry=None):
    b = np.asarray(boxes, float).reshape(-1, 4).copy()
    b[:, [0, 2]] = (b[:, [0, 2]] - left) / r
    b[:, [1, 3]] = (b[:, [1, 3]] - top) / (ry if ry else r)
    return b

SRC, DST = (1080, 1920), (640, 640)
VARIANTS = [
    ('默认（居中 + round）',      dict()),
    ('右下填充（torchvision式）',  dict(center=False)),
    ('auto=True（pad 到 32 倍数）', dict(stride=32)),
    ('floor 取整（C++ 常见）',     dict(round_fn=math.floor)),
]
print(f"{'变体':<26s} {'r':>7s} {'缩放后(h,w)':>13s} {'(left,top)':>15s} {'输出(h,w)':>13s}")
PS = {}
for name, kw in VARIANTS:
    p = letterbox_params(SRC, DST, **kw); PS[name] = p
    print(f'{name:<26s} {p["r"]:>7.4f} {str(p["new"]):>13s} '
          f'{str((p["left"], p["top"])):>15s} {str(p["out"]):>13s}')

p_ok = PS['默认（居中 + round）']
assert p_ok['new'] == (360, 640) and p_ok['top'] == 140.0 and p_ok['left'] == 0.0
assert PS['右下填充（torchvision式）']['top'] == 0.0, '右下填充 -> 整体偏 140/r = 420 px'
assert PS['auto=True（pad 到 32 倍数）']['out'] == (384, 640), '**导出 ONNX/TRT 时必须 auto=False**'

# ⚠️ 取整分歧在 1920x1080 上**看不出来**：1080*(640/1920) 恰好是 360.0
assert PS['floor 取整（C++ 常见）']['top'] == p_ok['top'], '整除时 round 与 floor 一致 —— 所以开发机上永远复现不了'
ROI = (800, 1920)                                # 车端常见：切掉天空与引擎盖后的 ROI
p_roi_r = letterbox_params(ROI, DST)
p_roi_f = letterbox_params(ROI, DST, round_fn=math.floor)
print(f'\\n换成车端 ROI 裁剪图 1920x800（800*(640/1920) = {800*p_roi_r["r"]:.4f}，不整除）：')
print(f'  round -> new={p_roi_r["new"]}, top={p_roi_r["top"]}')
print(f'  floor -> new={p_roi_f["new"]}, top={p_roi_f["top"]}   <- **差了半个 padding 像素**')
assert p_roi_r['new'] == (267, 640) and p_roi_f['new'] == (266, 640)
assert abs(p_roi_f['top'] - p_roi_r['top'] - 0.5) < 1e-12

TRUE24 = np.array([[948., 528., 972., 552.]])    # 画面中心一块 24px 的标志
lb = lb_fwd(TRUE24, p_ok)
print(f'\\n原图框 {TRUE24[0]}  --letterbox-->  {lb[0]}   (24px -> 8px)')
assert np.allclose(lb, [[316., 316., 324., 324.]])
assert np.allclose(lb_inv(lb, p_ok['r'], p_ok['left'], p_ok['top']), TRUE24), '正逆往返必须无损'
print('✅ 正逆变换往返无损。padding 占了 640x640 的 %.1f%% —— 这些网格点永远是负样本。'
      % (100 * (640 * 640 - 640 * 360) / (640 * 640)))"""),

    code("""# ── 三种「灾难性」的逆变换 bug（1920x1080）──
r_, left_, top_ = p_ok['r'], p_ok['left'], p_ok['top']
rx, ry = 640 / 1920, 640 / 1080                  # 各轴独立缩放（错的）
p_str = PS['auto=True（pad 到 32 倍数）']
TRUE8 = np.array([[956., 536., 964., 544.]])     # 同一位置的 8px 远处标志

CASES = [
    ('✅ 正确',                    p_ok,  lambda b: lb_inv(b, r_, left_, top_)),
    ('① 忘记减 padding',           p_ok,  lambda b: lb_inv(b, r_, 0.0, 0.0)),
    ('② 各轴独立缩放 + 无 pad',     p_ok,  lambda b: lb_inv(b, rx, 0.0, 0.0, ry)),
    ('③ 前向 auto=True / 逆用 640', p_str, lambda b: lb_inv(b, r_, left_, top_)),
]
print(f"{'逆变换实现':<28s} {'还原出的框(24px标志)':>30s} {'y误差px':>9s} {'IoU@24px':>9s} {'IoU@8px':>8s}")
res = {}
for name, p_fwd, inv in CASES:
    rec24 = inv(lb_fwd(TRUE24, p_fwd)); rec8 = inv(lb_fwd(TRUE8, p_fwd))
    i24 = box_iou(rec24, TRUE24)[0, 0]; i8 = box_iou(rec8, TRUE8)[0, 0]
    dy = abs(rec24[0, 1] - TRUE24[0, 1])
    res[name] = (i24, i8, dy)
    print(f'{name:<28s} {np.round(rec24[0],1)} {dy:>9.1f} {i24:>9.3f} {i8:>8.3f}')

assert res['✅ 正确'][0] > 0.9999 and res['✅ 正确'][1] > 0.9999
assert res['① 忘记减 padding'][0] == 0.0 and abs(res['① 忘记减 padding'][2] - 420) < 0.5
assert res['③ 前向 auto=True / 逆用 640'][0] == 0.0
assert abs(res['③ 前向 auto=True / 逆用 640'][2] - 384) < 0.5
assert 0.55 < res['② 各轴独立缩放 + 无 pad'][0] < 0.58
print('\\n⚠️  bug ①③ 让框整体偏 420 / 384 像素 —— 灾难性，但**一眼就能看出来**（框飞了）。')

# ── ④ 取整分歧：**只在源尺寸不整除时暴露**，所以最危险 ──
TRUE24_ROI = np.array([[948., 388., 972., 412.]])   # 1920x800 的 ROI 里，一块 24px 标志
TRUE8_ROI  = np.array([[956., 396., 964., 404.]])   # 同一位置的 8px 标志
print(f"\\n{'④ 前向 round / 逆用 floor':<28s} {'源尺寸':>12s} {'y误差px':>9s} {'IoU@24px':>9s} {'IoU@8px':>8s}")
for tag, p_f, p_b, t24, t8 in [
        ('  在 1920x1080 上', p_ok,    PS['floor 取整（C++ 常见）'], TRUE24, TRUE8),
        ('  在 1920x800 ROI 上', p_roi_r, p_roi_f,                  TRUE24_ROI, TRUE8_ROI)]:
    rec24 = lb_inv(lb_fwd(t24, p_f), p_f['r'], p_b['left'], p_b['top'])
    rec8 = lb_inv(lb_fwd(t8, p_f), p_f['r'], p_b['left'], p_b['top'])
    i24 = box_iou(rec24, t24)[0, 0]; i8 = box_iou(rec8, t8)[0, 0]
    dy = abs(rec24[0, 1] - t24[0, 1])
    print(f'{tag:<28s} {str(p_f["new"]):>12s} {dy:>9.2f} {i24:>9.3f} {i8:>8.3f}')
    if 'ROI' in tag:
        i24_4, i8_4, dy4 = i24, i8, dy

assert dy4 > 0, 'ROI 上取整分歧才暴露'
assert abs(dy4 - 1.5) < 1e-6, '半个 padding 像素 -> 原图 1.5 px'
assert abs(i24_4 - 0.882) < 0.005 and abs(i8_4 - 0.684) < 0.005, (i24_4, i8_4)
assert i8_4 < i24_4, '**同样的亚像素误差，小目标受伤远大于大目标**'
print(f'\\n⚠️  bug ④ 在 1920x1080 上**误差为 0**（1080 恰好整除），在开发机上永远复现不了；')
print(f'    一换成车端的 ROI 裁剪图，就偏 {dy4:.1f} 个原图像素 ——')
print(f'    24px 标志 IoU {i24_4:.2f}（还行），**8px 远处标志 IoU 只剩 {i8_4:.2f}**。')
print('    **这种「只低一点点、还只在特定输入下出现」的 bug 才是真正危险的** —— 它像「模型不够好」。')
print('✅ 正确做法：把 (r, left, top) 作为**元数据**跟着图像传下去，不要在推理端重算。')
print('   YOLOv5 的 scale_boxes(..., ratio_pad=...) 参数存在的唯一理由就是这个。')"""),

    md("""## 6 · 翻转白名单：TSR 面试可以主动提的加分点

通用检测里 `fliplr=0.5` 是白送的。**交通标志是人为设计的符号系统**——
它的全部意义就在形状、颜色和**朝向**承载的约定。

**三问判定法**：
1. `Q1` 外观是否左右镜像对称？
2. `Q2` 语义是否含方向性（左/右、顺/逆、单向）？
3. `Q3` 标签集里是否存在它的镜像类别？

→ `Q1 且 非Q2` = **SAFE**；`Q2 且 Q3` = **SWAP**（翻转 + **换标签**）；其余 = **FORBID**。"""),

    code("""def decide_flip(mirror_symmetric, directional, has_mirror_class):
    if mirror_symmetric and not directional:
        return 'SAFE'
    if directional and has_mirror_class:
        return 'SWAP'
    return 'FORBID'

# (key, 中文, 外观左右对称, 语义含方向, 镜像类别)
SIGNS = [
    ('no_entry',            '禁止驶入',      True,  False, None),
    ('no_vehicles',         '禁止通行',      True,  False, None),
    ('no_honking',          '禁止鸣笛',      True,  False, None),
    ('traffic_light_ahead', '注意信号灯',    True,  False, None),
    ('turn_left',           '向左转弯',      False, True,  'turn_right'),
    ('turn_right',          '向右转弯',      False, True,  'turn_left'),
    ('no_left_turn',        '禁止向左转弯',  False, True,  'no_right_turn'),
    ('no_right_turn',       '禁止向右转弯',  False, True,  'no_left_turn'),
    ('keep_left',           '左侧通行',      False, True,  'keep_right'),
    ('keep_right',          '右侧通行',      False, True,  'keep_left'),
    ('curve_left',          '向左急弯路',    False, True,  'curve_right'),
    ('curve_right',         '向右急弯路',    False, True,  'curve_left'),
    ('narrow_left',         '左侧变窄',      False, True,  'narrow_right'),
    ('narrow_right',        '右侧变窄',      False, True,  'narrow_left'),
    ('merge_left',          '左侧合流',      False, True,  None),      # ← 标签集里没有右侧合流
    ('speed_limit_30',      '限速30',        False, False, None),
    ('speed_limit_60',      '限速60',        False, False, None),
    ('speed_limit_120',     '限速120',       False, False, None),
    ('stop',                '停车让行STOP',  False, False, None),
    ('guide_sign',          '指路牌',        False, False, None),
    ('ped_crossing',        '注意行人',      False, False, None),
    ('children',            '注意儿童',      False, False, None),
]
TABLE_ = {k: {'zh': zh, 'kind': decide_flip(sym, d, m is not None), 'mirror': m}
          for k, zh, sym, d, m in SIGNS}

by_kind = collections.defaultdict(list)
for k, v in TABLE_.items():
    by_kind[v['kind']].append(v['zh'])
for kind in ['SAFE', 'SWAP', 'FORBID']:
    print(f'{kind:<7s} ({len(by_kind[kind]):2d} 类)  ' + '、'.join(by_kind[kind]))

assert TABLE_['turn_left']['kind'] == 'SWAP' and TABLE_['turn_left']['mirror'] == 'turn_right'
assert TABLE_['no_entry']['kind'] == 'SAFE'
assert TABLE_['speed_limit_60']['kind'] == 'FORBID', '含数字：镜像后的字形现实中不存在'
assert TABLE_['guide_sign']['kind'] == 'FORBID', '指路牌含地名文字'
assert TABLE_['merge_left']['kind'] == 'FORBID', '**Q3 不过**：有方向语义但标签集里没有镜像类'
assert (len(by_kind['SAFE']), len(by_kind['SWAP']), len(by_kind['FORBID'])) == (4, 10, 8)
print('\\n⚠️  注意「左侧合流」：它有方向语义、外观也不对称，但**标签集里没有「右侧合流」**，')
print('    翻了就没有正确标签可给 -> FORBID。**Q3 不是走过场，它真的会改变结论。**')"""),

    code("""# ── 整图翻转的实现：逐目标判定，但作用在整图上（「与」的关系）──
def hflip_boxes(boxes, W):
    b = np.asarray(boxes, float).reshape(-1, 4).copy()
    x1, x2 = b[:, 0].copy(), b[:, 2].copy()
    b[:, 0], b[:, 2] = W - x2, W - x1            # 注意 x1/x2 会互换
    return b

def flip_scene(W, boxes, labels, table=None):
    table = TABLE_ if table is None else table
    kinds = [table[c]['kind'] for c in labels]
    if 'FORBID' in kinds:
        return None                              # 一个 FORBID -> 整张图都不能翻
    new = [table[c]['mirror'] if table[c]['kind'] == 'SWAP' else c for c in labels]
    return hflip_boxes(boxes, W), new

for scene in [(['no_entry', 'no_vehicles'],), (['turn_left', 'no_entry'],),
              (['turn_left', 'speed_limit_60'],), (['merge_left'],)]:
    labs = scene[0]
    bx = np.array([[10. + 30 * i, 20., 40. + 30 * i, 50.] for i in range(len(labs))])
    out = flip_scene(640, bx, labs)
    txt = ('可翻 -> ' + str(out[1])) if out else '❌ 整图不可翻（含 FORBID）'
    print(f'{str(labs):<40s} {txt}')

bx = np.array([[10., 20., 40., 50.]])
assert flip_scene(640, bx, ['turn_left'])[1] == ['turn_right']
assert np.allclose(flip_scene(640, bx, ['turn_left'])[0], [[600., 20., 630., 50.]])
assert np.allclose(hflip_boxes(hflip_boxes(bx, 640), 640), bx), '翻两次回到原处'
assert flip_scene(640, bx, ['speed_limit_60']) is None
assert flip_scene(640, np.repeat(bx, 2, 0), ['turn_left', 'stop']) is None

# ── 反直觉的一条：对 SAFE 类，翻转的信息增益 ≈ 0 ──
def make_patch(kind, s=17):
    p = np.zeros((s, s), np.uint8); c = s // 2
    yy, xx = np.mgrid[0:s, 0:s]
    p[(xx - c) ** 2 + (yy - c) ** 2 <= c * c] = 60       # 圆形牌面
    if kind == 'no_entry':                               # 中央白横杠：左右镜像对称
        p[c - 1:c + 2, c - 5:c + 6] = 255
    else:                                                # 左向箭头：不对称
        p[c - 1:c + 2, c - 5:c + 3] = 255
        for k in range(4):
            p[c - k:c + k + 1, c - 5 + k] = 255
    return p

sym, asym = make_patch('no_entry'), make_patch('turn_left')
print(f'\\n禁止驶入(SAFE)  翻转后逐像素相同? {np.array_equal(sym[:, ::-1], sym)}   '
      f'不同像素数 {int((sym[:, ::-1] != sym).sum())}')
print(f'向左转弯(SWAP)  翻转后逐像素相同? {np.array_equal(asym[:, ::-1], asym)}   '
      f'不同像素数 {int((asym[:, ::-1] != asym).sum())}')
assert np.array_equal(sym[:, ::-1], sym), 'SAFE 类的定义就是左右镜像对称 -> 翻了等于没翻'
assert not np.array_equal(asym[:, ::-1], asym)
print('\\n⚠️  **在 TSR 里，翻转要么不安全（FORBID/SWAP），要么安全但没用（SAFE）。**')
print('    SAFE 的定义就是外观左右对称 -> 镜像后图块逐像素不变，模型从目标身上学到的东西')
print('    一点没变，唯一变的是背景上下文。这就是「默认关掉水平翻转」的完整理由。')"""),

    code("""# ── 量化：配置里写 fliplr=0.5，实际到底生效多少？──
FREQ = {   # TT100K 风格的长尾频率（限速牌 + 指路牌是绝对头部）
    'speed_limit_60': .16, 'guide_sign': .14, 'speed_limit_30': .09, 'ped_crossing': .08,
    'speed_limit_120': .04, 'children': .03, 'stop': .02, 'merge_left': .02,
    'no_entry': .05, 'traffic_light_ahead': .05, 'no_vehicles': .04, 'no_honking': .03,
    'turn_left': .03, 'turn_right': .03, 'no_left_turn': .025, 'no_right_turn': .025,
    'curve_left': .02, 'curve_right': .02, 'keep_left': .015, 'keep_right': .015,
    'narrow_left': .0125, 'narrow_right': .0125,
}
tot = sum(FREQ.values())
share = {k: collections.Counter() for k in ['SAFE', 'SWAP', 'FORBID']}
p_kind = collections.Counter()
for k, f_ in FREQ.items():
    p_kind[TABLE_[k]['kind']] += f_ / tot
print(f"目标级占比：SAFE {p_kind['SAFE']:.1%} | SWAP {p_kind['SWAP']:.1%} | "
      f"FORBID {p_kind['FORBID']:.1%}")

N_PER_IMG = {1: .45, 2: .28, 3: .15, 4: .08, 5: .04}       # 每图标志数分布
p_ok_obj = 1 - p_kind['FORBID']
p_img = sum(w * p_ok_obj ** n for n, w in N_PER_IMG.items())
P_FLIP_CFG = 0.5
eff_img = p_img * P_FLIP_CFG
eff_info = p_img * P_FLIP_CFG * p_kind['SWAP']             # 只有 SWAP 类真正带来新信息

print(f'\\n单个目标可翻的概率            {p_ok_obj:.1%}')
print(f'**整张图**可翻的概率（每图 1-5 个标志，全都得可翻）  {p_img:.1%}')
print(f'配置写 fliplr={P_FLIP_CFG} -> 实际被翻的图         {eff_img:.1%}')
print(f'其中真正带来新信息的目标（SWAP 类）占全部目标  **{eff_info:.1%}**')

assert .55 < p_kind['FORBID'] < .65
assert .20 < p_img < .27, p_img
assert eff_info < .05, '真正有效的翻转不到 5%'
print('\\n⚠️  你配置里写的 fliplr=0.5，真正被翻的图只有约 12%；')
print('    而其中真正带来新信息的目标只占全部目标的 2.5% —— **这个增强基本等于没开**，')
print('    却让你误以为「已经做了数据增强」。')
print('✅ SWAP 档还有一个附带好处：向左/向右类往往左右样本数不均衡，')
print('   SWAP 式翻转正好把两边拉平 —— 这是一个免费的类别平衡手段（面试加分点）。')"""),

    md("""## 7 · RandomIoUCrop：小目标的最直接解法，也是位置先验的杀手

裁剪家族有两个方向相反的变体，很多人把它们混为一谈：
**RandomCrop（zoom-in）放大目标**、**Expand / Mosaic（zoom-out）缩小目标**。

zoom-in 是小目标最直接的解法（直接提高目标的相对尺寸），
但它会**摧毁位置先验**——交通标志在真实图像里几乎从不出现在画面下半部。"""),

    code("""def random_iou_crop(boxes, W, H, g, min_iou=0.3, tries=60, lo=0.3, hi=0.9,
                    y0_max=None, ch_lo=None, ch_hi=None):
    for _ in range(tries):
        s = g.uniform(lo, hi)
        cw = int(W * s)
        ch = int(H * s) if ch_lo is None else int(g.uniform(ch_lo, ch_hi) * H)
        if cw < 8 or ch < 8 or cw > W or ch > H:
            continue
        x0 = int(g.integers(0, W - cw + 1))
        y0 = int(g.integers(0, (H - ch + 1) if y0_max is None else min(y0_max, H - ch) + 1))
        patch = np.array([[x0, y0, x0 + cw, y0 + ch]], float)
        if len(boxes) == 0 or box_iou(np.asarray(boxes, float), patch).max() >= min_iou:
            return patch[0]
    return np.array([0., 0., float(W), float(H)])

W0, H0, IN = 1920, 1080, 640
px_full = sign_px(60)                                      # 60 m 外的标志，全分辨率像素
print(f'60 m 外的 0.6 m 标志，全分辨率 {px_full:.1f} px')
print(f'  直接 letterbox 到 {IN}          -> {px_full*IN/W0:>5.1f} px   (缩小 {IN/W0:.2f}x)')
for cw in [960, 640, 480]:
    print(f'  先裁 {cw}x{cw} 再 resize 到 {IN} -> {px_full*IN/cw:>5.1f} px   (放大 {IN/cw:.2f}x)')
gain = (px_full * IN / 480) / (px_full * IN / W0)
assert abs(gain - 4.0) < 1e-9, '裁 480 再放大，相对直接 letterbox 是 4 倍线性尺寸'
print(f'\\n✅ 裁 480x480 再 resize，目标线性尺寸是直接 letterbox 的 **{gain:.0f} 倍** ——')
print('   小目标之所以难，就是它在特征图上占的格子太少（stride 32 时 8px 目标只占 0.25 格）。')
print('   zoom-in 直接把这个数按面积平方提上去，这是最便宜的小目标解法。')"""),

    code("""# ── 代价：位置先验被摧毁 ──
g2 = np.random.default_rng(11)
N = 20000
yc = g2.uniform(0.15, 0.45, N) * H0              # 真实：标志集中在画面上部（路侧/龙门架）

def crop_and_renorm(y0_max, ch_lo, ch_hi):
    ch = (g2.uniform(ch_lo, ch_hi, N) * H0).astype(int)
    hi_ = np.minimum(y0_max * H0, H0 - ch)
    y0 = (g2.random(N) * np.maximum(hi_, 0)).astype(int)
    inside = (yc >= y0) & (yc < y0 + ch)
    return (yc[inside] - y0[inside]) / ch[inside], ch[inside].mean()

before = yc / H0
free, ch_free = crop_and_renorm(1.0, 0.25, 0.50)          # 无约束：窗口位置全图均匀（zoom-in 用的小窗口）
cons, ch_cons = crop_and_renorm(0.05, 0.70, 1.00)         # 加约束：贴着画面上沿、窗口更大

def outside_prior(a):                            # 真实先验带是 [0.15, 0.45]
    return float(((a < 0.15) | (a > 0.45)).mean())

print(f"{'策略':<22s} {'归一化纵坐标':>16s} {'落在下半部':>11s} {'跳出先验带':>11s} {'放大倍数':>10s}")
rows = [('原图（真实分布）', before, IN / H0),
        ('无约束随机裁剪',   free,  IN / ch_free),
        ('加约束裁剪(上部)', cons,  IN / ch_cons)]
for name, arr, zoom in rows:
    print(f'{name:<22s} {arr.mean():>7.3f} ± {arr.std():<6.3f} {(arr > 0.5).mean():>10.1%} '
          f'{outside_prior(arr):>11.1%} {zoom:>9.2f}x')

p_before, p_free, p_cons = (before > .5).mean(), (free > .5).mean(), (cons > .5).mean()
o_free, o_cons = outside_prior(free), outside_prior(cons)
assert p_before == 0.0 and outside_prior(before) == 0.0, '真实世界里标志不出现在画面下半部'
assert p_free > 0.30 and o_free > 0.50, '无约束裁剪把位置先验彻底拉平'
assert p_cons < 0.12 and o_cons < 0.25, '加约束后基本保住了位置先验'
assert IN / ch_free > IN / ch_cons > IN / H0, '放大倍数：自由裁剪 > 受约束裁剪 > 直接 letterbox'
print(f'\\n⚠️  现实中「标志出现在画面下半部」的概率是 **0%**；')
print(f'    无约束随机裁剪把它变成 **{p_free:.0%}**，并让 **{o_free:.0%}** 的标志跳出真实先验带 ——')
print('    模型因此失去了压制广告牌 / 车身贴纸误检的最强线索（C55 模块 03 的一个独立失效模式）。')
print(f'    加约束（窗口贴着画面上沿、窗口更大）把它压回 {p_cons:.0%} / {o_cons:.0%}，')
print(f'    同时仍保留 {IN/ch_cons:.2f}x 的放大（直接 letterbox 只有 {IN/H0:.2f}x）。')
print(f'    代价是放大倍数从 {IN/ch_free:.2f}x 降到 {IN/ch_cons:.2f}x —— **这就是那个权衡的具体数字。**')
print('\\n✅ TSR 裁剪配方：① 限制窗口纵向范围保住位置先验；② 用 IoU 约束保证至少一个目标完整；')
print('   ③ 被切断的目标一律 ignore 而非 drop；④ 裁剪与 zoom-out 成对使用让尺度双向展开。')"""),

    md("""## ✏️ 练习 1：`warp_boxes_vis`

实现 `warp_boxes_vis(boxes, M, W, H)`，返回 `(clipped, vis)`：

1. 用**四角法**把 `boxes` 经 `M` 变换（可以直接调用已有的 `warp_boxes`）；
2. 把结果裁到 `[0,W] × [0,H]`；
3. `vis` = 裁剪后面积 / 裁剪前面积（变换后面积为 0 时记 0.0）。"""),

    code("""def warp_boxes_vis(boxes, M, W, H):
    # TODO: 四角法 -> 裁剪 -> 可见比例
    #       返回 (clipped: (N,4) float, vis: (N,) float)
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
B1 = np.array([[0., 0., 40., 40.]])
c, v = warp_boxes_vis(B1, M_T(600, 0), 640, 640)
assert np.allclose(c, [[600., 0., 640., 40.]]) and abs(v[0] - 1.0) < 1e-9
c, v = warp_boxes_vis(B1, M_T(620, 0), 640, 640)
assert np.allclose(c, [[620., 0., 640., 40.]]) and abs(v[0] - 0.5) < 1e-9, v
c, v = warp_boxes_vis(B1, M_T(700, 0), 640, 640)
assert abs(v[0]) < 1e-12, '完全出画面 -> vis=0'

# 旋转 45 度：框膨胀到 2 倍，但仍完全在画面内 -> vis=1
c, v = warp_boxes_vis(np.array([[300., 300., 340., 340.]]), about(M_R(45), 320, 320), 640, 640)
assert abs(box_area(c)[0] / 1600 - 2.0) < 1e-6, '45 度旋转 -> 面积翻倍'
assert abs(v[0] - 1.0) < 1e-9, 'vis 衡量的是「越界损失」，不是「膨胀」'
print('四角法+裁剪的可见比例：', np.round(v, 3))
print('45° 旋转后的框：', np.round(c[0], 1), ' 面积', box_area(c)[0], '(原 1600)')
print('✅ 练习 1 通过：注意 vis 只衡量越界损失，**框膨胀是另一码事，vis 看不见它**。')"""),

    md("""## ✏️ 练习 2：letterbox 逆变换

实现 `letterbox_inverse(boxes_lb, r, left, top)`：把 letterbox 坐标系里的框
还原成原图坐标。**这就是推理端每一帧都要跑的那几行**，也是 C60 模块 04 里
「框整体偏移」的头号成因。"""),

    code("""def letterbox_inverse(boxes_lb, r, left, top):
    # TODO: x = (x' - left)/r ;  y = (y' - top)/r
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
p = letterbox_params((1080, 1920), (640, 640))
true = np.array([[948., 528., 972., 552.], [100., 200., 140., 260.]])
lbv = lb_fwd(true, p)
rec = letterbox_inverse(lbv, p['r'], p['left'], p['top'])
assert np.allclose(rec, true), f'往返必须无损，实得 {rec}'

bad = letterbox_inverse(lbv, p['r'], 0.0, 0.0)          # 忘记减 padding
dy = float(abs(bad[0, 1] - true[0, 1]))
assert abs(dy - 420.0) < 0.5, f'忘记减 pad 应偏 420 px，实得 {dy}'
assert box_iou(bad[:1], true[:1])[0, 0] == 0.0

# 不放大小图：scaleup=False 时 r 被夹到 1.0
p_small = letterbox_params((320, 480), (640, 640))
assert p_small['r'] == 1.0, '推理端默认不放大小图'
p_up = letterbox_params((320, 480), (640, 640), scaleup=True)
assert abs(p_up['r'] - 640 / 480) < 1e-9

print(f'正确逆变换 -> {np.round(rec[0],1)}   ✅')
print(f'忘记减 pad -> {np.round(bad[0],1)}   ❌ y 偏 {dy:.0f} px，IoU=0')
print('✅ 练习 2 通过：**把 (r,left,top) 当元数据传下去，不要在推理端重算。**')"""),

    md("""## ✏️ 练习 3：翻转安全性检查器

实现 `safe_hflip(W, boxes, labels, table)`：

- 若任一 label 的档位是 `FORBID` → 返回 `None`（整图不能翻）；
- 否则返回 `(new_boxes, new_labels)`：框做水平翻转，
  `SWAP` 档的 label 换成它的镜像类，`SAFE` 档保持不变。"""),

    code("""def safe_hflip(W, boxes, labels, table):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
BB = np.array([[10., 20., 40., 50.], [100., 20., 130., 50.]])
out = safe_hflip(640, BB, ['turn_left', 'no_entry'], TABLE_)
assert out is not None
nb, nl = out
assert nl == ['turn_right', 'no_entry'], nl
assert np.allclose(nb, [[600., 20., 630., 50.], [510., 20., 540., 50.]]), nb
assert safe_hflip(640, BB, ['turn_left', 'speed_limit_60'], TABLE_) is None
assert safe_hflip(640, BB[:1], ['merge_left'], TABLE_) is None, 'Q3 不过 -> FORBID'
assert safe_hflip(640, BB, ['no_entry', 'no_honking'], TABLE_)[1] == ['no_entry', 'no_honking']
back = safe_hflip(640, safe_hflip(640, BB, ['turn_left', 'no_entry'], TABLE_)[0],
                  ['turn_right', 'no_entry'], TABLE_)
assert np.allclose(back[0], BB) and back[1] == ['turn_left', 'no_entry'], '翻两次回到原状态'
print('翻转前 ', ['turn_left', 'no_entry'], np.round(BB[:, 0], 0).tolist())
print('翻转后 ', nl, np.round(nb[:, 0], 0).tolist())
print('✅ 练习 3 通过：**翻转 + 换标签**，而且翻两次能完整回到原状态（含标签）。')"""),

    md("""## ✏️ 练习 4：从丢弃阈值反推最大检出距离

实现 `range_from_min_side(min_side_px, input_w, sensor_w, hfov_deg, sign_m)`：
用针孔模型算出「配置里这个 `min_side` 把系统的最大检出距离锁死在多少米」。

`f = sensor_w / (2·tan(hfov/2))`；标志在输入分辨率下的像素尺寸
`= f · sign_m / Z · (input_w / sensor_w)`；令它等于 `min_side_px` 解出 `Z`。"""),

    code("""def range_from_min_side(min_side_px, input_w=640, sensor_w=1920, hfov_deg=60.0, sign_m=0.6):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
assert abs(range_from_min_side(8) - 41.57) < 0.05, range_from_min_side(8)
assert abs(range_from_min_side(2) - 166.28) < 0.05
assert abs(range_from_min_side(4) - 2 * range_from_min_side(8)) < 1e-9, '距离与阈值成反比'
# 换一颗长焦相机（30° FOV）：同样的 min_side 能看得更远
assert range_from_min_side(8, hfov_deg=30) > 2 * range_from_min_side(8, hfov_deg=60)
# 提高输入分辨率同样有效
assert abs(range_from_min_side(8, input_w=1280) - 2 * range_from_min_side(8, input_w=640)) < 1e-9

print(f"{'配置':<40s} {'最大检出距离':>13s} {'120km/h 反应时间':>18s}")
for desc, kw in [('640 输入 / 60° 广角 / min_side=8', dict(min_side_px=8)),
                 ('640 输入 / 60° 广角 / min_side=2', dict(min_side_px=2)),
                 ('1280 输入 / 60° 广角 / min_side=2', dict(min_side_px=2, input_w=1280)),
                 ('640 输入 / 30° 长焦 / min_side=2', dict(min_side_px=2, hfov_deg=30))]:
    Z = range_from_min_side(**kw)
    print(f'{desc:<40s} {Z:>11.1f} m {Z/(120/3.6):>16.1f} s')
print('\\n✅ 练习 4 通过：**增强流水线里的一个整数，等价于一条硬件级的能力上限。**')
print('   面试里被问「怎么提升远距离检出」，这三个旋钮（min_side / 输入分辨率 / 焦距）')
print('   都是可以量化回答的 —— 而第一个是免费的。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def warp_boxes_vis(boxes, M, W, H):
    w = warp_boxes(boxes, M)
    a0 = box_area(w)
    c = w.copy()
    c[:, [0, 2]] = np.clip(c[:, [0, 2]], 0, W)
    c[:, [1, 3]] = np.clip(c[:, [1, 3]], 0, H)
    a1 = box_area(c)
    vis = np.where(a0 > 0, a1 / np.maximum(a0, 1e-12), 0.0)
    return c, vis"""),

    code("""# 练习 2 参考答案
def letterbox_inverse(boxes_lb, r, left, top):
    b = np.asarray(boxes_lb, float).reshape(-1, 4).copy()
    b[:, [0, 2]] = (b[:, [0, 2]] - left) / r
    b[:, [1, 3]] = (b[:, [1, 3]] - top) / r
    return b"""),

    code("""# 练习 3 参考答案
def safe_hflip(W, boxes, labels, table):
    if any(table[c]['kind'] == 'FORBID' for c in labels):
        return None
    new_labels = [table[c]['mirror'] if table[c]['kind'] == 'SWAP' else c for c in labels]
    return hflip_boxes(boxes, W), new_labels"""),

    code("""# 练习 4 参考答案
def range_from_min_side(min_side_px, input_w=640, sensor_w=1920, hfov_deg=60.0, sign_m=0.6):
    f = sensor_w / (2 * math.tan(math.radians(hfov_deg) / 2))
    return f * sign_m * (input_w / sensor_w) / min_side_px"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接用的几何增强配置与验收清单

下面这段可以原样复制进项目（把 numpy 换成 OpenCV / albumentations 即可）。
它的价值在于：**每一个数字都有出处，不是抄来的。**"""),

    code("""RECIPE = r'''
# ============================================================
# TSR 几何增强配置（configs/aug_geometric.yaml）—— 每个数字都写清出处
# ============================================================
geometric:
  # 1) 缩放：TSR 收益最高的几何增强。对应「标志的远近」，物理上精确无误差。
  random_scale:   {range: [0.5, 1.5], p: 1.0}

  # 2) 平移：TSR 有强位置先验（标志在画面上部/路侧），幅度不能大。
  random_translate: {frac: 0.10, p: 0.5}

  # 3) 旋转：**上限由「可接受的框膨胀率」反推**，不是拍脑袋。
  #    A'/A = 1 + 0.5*|sin2θ|*(w/h + h/w)
  #    可接受膨胀 <=35%  ->  正方形框 |θ|<=10.2° ; 3:1 指路牌 |θ|<=6.1°
  #    取较小者，且真实车身滚转角 p99 约 3-5°，故：
  random_rotate:  {deg: 6.0, p: 0.3}

  # 4) 错切/透视：与轻微旋转作用重叠，且透视容易失控。默认关闭。
  random_shear:       {deg: 0.0}
  random_perspective: {scale: 0.0}     # 开启时务必检查角点变换做了透视除法

  # 5) 水平翻转：**TSR 默认关闭**。要开必须配三档白名单（见下）。
  #    量化过：整图可翻率 ~23%，配 p=0.5 实际只翻 ~12% 的图，
  #    其中真正带来新信息的（SWAP 类）只占全部目标的 ~2.5%。
  random_hflip:   {p: 0.0, whitelist: configs/flip_whitelist.yaml}
  random_vflip:   {p: 0.0}             # 永远关闭：重力方向是恒定的

  # 6) 裁剪：小目标最直接的解法，但会摧毁位置先验。**必须加约束**。
  random_iou_crop:
    min_iou_choices: [0.1, 0.3, 0.5, 0.7, 0.9]
    crop_y0_max_frac: 0.05             # 窗口贴着画面上沿 -> 保住位置先验
    crop_h_frac: [0.70, 1.00]          # 窗口不能太小，否则位置分布被拉平
    # 实测：无约束裁剪会让「标志落在画面下半部」的概率从 0% 涨到 ~45%

# ============================================================
# 越界策略：**只有完全出画面才 drop，其余一律 ignore**
# ============================================================
out_of_bound:
  min_visible: 0.5                     # < 0.5 且 > 0 -> ignore（不是 drop！）
  min_side_px: 2                       # **这个数等价于最大检出距离**：
                                       #   min_side=8 -> 41.6 m（120km/h 只剩 1.2 s）
                                       #   min_side=2 -> 166 m
  policy_below_threshold: ignore       # 绝不用 drop：会制造假负样本监督

# ============================================================
# letterbox：全流水线唯一必须与推理端逐像素一致的算子
# ============================================================
letterbox:
  size: [640, 640]
  pad_value: 114
  center: true
  scaleup: false
  auto_stride: null                    # **导出 ONNX/TRT 时必须为 null**，否则输出不是 640x640
  rounding: round                      # round vs floor 差半个 pad 像素 -> 原图 1.5 px
                                       #   -> 8px 标志 IoU 从 1.00 掉到 0.49
  # 逆变换：把 (r, left, top) 作为**元数据**传给推理端，不要重算。
  #   x = (x_lb - left) / r ;  y = (y_lb - top) / r
  #   对应 YOLOv5: scale_boxes(img1_shape, boxes, img0_shape, ratio_pad=(r,(left,top)))

# ============================================================
# 验收清单（每个几何算子合入前必须过）
# ============================================================
# [ ] apply_image 与 apply_boxes 用的是**同一个矩阵 M**
# [ ] 角点变换**无条件**做透视除法（仿射时是恒等操作）
# [ ] 用目标掩码/轮廓算出的真实紧框做断言，IoU >= 0.95（不要靠可视化抽查）
# [ ] 越界目标走 ignore 而非 drop，且单测覆盖「露一半」的情况
# [ ] letterbox forward -> inverse 往返误差 < 0.5 px（含奇数尺寸、非对齐尺寸）
# [ ] 翻转走白名单，且「翻两次回到原状态（含标签）」有单测
# [ ] 增强前后的目标尺寸直方图对比，确认小尺寸桶没有整段消失
'''
print(RECIPE)
for k in ['random_scale', 'random_rotate', 'whitelist', 'min_side_px', 'ignore',
          'auto_stride', 'ratio_pad', 'crop_y0_max_frac', '透视除法']:
    assert k in RECIPE, k
print('✅ 配方覆盖：缩放/平移/旋转(反推上限)/翻转白名单/受约束裁剪/越界策略/'
      'letterbox 正逆变换/验收清单')"""),

    md("""### 小结

- **几何增强的唯一正确形态是「一个矩阵」**：只插值一次、绕某点变换有明确写法、
  图像与标注用同一个对象所以不可能不同步。`T(c)·M·T(-c)` 这个三明治结构要背下来。
- **角点变换必须无条件做透视除法**。仿射时它是恒等操作，透视时它是必需的——
  幅度小的时候误差也小，所以这个 bug 能潜伏很久。
- **旋转会让外接框膨胀**：`A'/A = 1 + ½|sin2θ|(w/h + h/w)`。
  **正方形框 45° 时面积翻倍、15° 时已膨胀 50%**；细长的指路牌更狠（3:1 时 45° 膨胀 2.67×）。
  **旋转幅度上限应从「可接受的膨胀率」反推**，而不是拍脑袋。
- **四角法对旋转不变的形状是错的**：圆形禁令牌旋转 45°，真实紧框一点没变，
  四角法却把框撑到 √2 倍边长——**标注 IoU 只剩 0.50、框内前景只剩 39%**。
  这不是「任务变难」，是「标签变错」。
- **越界三分法**：`keep` 说「有」、`ignore` 说「不知道」、`drop` 说「没有」。
  **只有完全出画面才 drop**；否则可见的目标被删就成了明确的假负样本监督——
  而「标志被画面边缘截断」是 TSR 每次接近标志的必经阶段。
- **`min_side` 等价于一条硬件级能力上限**：640 输入 / 60° FOV 下，
  `min_side=8` 把最大检出距离锁死在 **41.6 m**（120 km/h 只剩 1.2 秒）；`min_side=2` 是 166 m。
- **letterbox 的逆变换是它存在的全部理由**。四种真实 bug：忘记减 pad（偏 420 px）、
  各轴独立缩放、stride 对齐不一致（偏 384 px）、round vs floor（只偏 1.5 px，
  但 **8 px 标志的 IoU 掉到 0.49**）。**把 (r, left, top) 当元数据传下去，不要重算。**
- **水平翻转在 TSR 里默认关闭**。三问判定 → SAFE / SWAP / FORBID；
  判定是逐目标的而翻转是整图的（「与」关系），实际生效率只有约 12%；
  而 **SAFE 类翻转后逐像素不变，信息增益为零**。
  **SWAP 档（翻转 + 换标签）是加分答案**，还顺带平衡了左右类样本数。
- **裁剪是小目标最直接的解法**（裁 480 再放大 = 4 倍线性尺寸），
  但无约束裁剪会把「标志出现在画面下半部」的概率从 **0% 推到 45%**，
  摧毁压制广告牌误检的最强线索。**要用加约束的裁剪。**

下一站：**模块 02 · 光度增强与域鲁棒性** —— HSV/gamma/噪声/模糊、
**「颜色即语义」的红线**（红=禁令、蓝=指示、黄=警告）、大气散射雾化模型、
运动模糊核与卷帘快门。"""),
]
