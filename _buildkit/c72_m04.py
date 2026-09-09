# -*- coding: utf-8 -*-
"""C72 模块 04 · BEV 投影与多相机融合。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的中心公式、模块 01 的反投影、模块 03 第 5 节的单应"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_bev_fusion.ipynb'
                       '（IPM 网格与采样率（过采样 5.4× / 欠采样 27.8×）/ '
                       '<strong>坡度：1% 在 50 m 处值 +50%，临界距离 $H/s$</strong> / '
                       '地面假设破坏清单 / 多相机拼接 / '
                       '<strong>重叠区一致性作为无真值的外参监控</strong>）'),
    ("核心参考", "本课程 C59 模块 03（BEV 作为感知接口）· C55 模块 04（时序传播）· "
                 "Philion &amp; Fidler, <em>Lift, Splat, Shoot</em>（ECCV 2020）· "
                 "Li et al., <em>BEVFormer</em>（ECCV 2022）"),
    ("预计时长", "读 45 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("bev-is-a-camera", "BEV 是一个俯视的虚拟相机", "".join([
        P("「鸟瞰图」听起来像一种表示，"
          "<strong>而在几何上它就是「把地面重新拍一次」——"
          "用一台放在正上方、光轴垂直向下的虚拟相机。</strong>"),
        ASCII("""
   真实相机                                虚拟俯视相机（BEV）
   ┌──────────┐                          ┌──────────┐
   │ 装在 1.5m │  ── 同一个地平面 z=0 ──►  │ 正上方    │
   │ 光轴水平  │                          │ 光轴向下  │
   └──────────┘                          └──────────┘
        │                                      │
        └──────►  两者之间是一个**单应** H_ipm ◄──┘
                  （模块 03 第 5 节：平面场景的两视角关系）

   H_ipm = K_bev · (R_bev - t_bev n^T / d) · K_cam^{-1}
                                    └── 平面：n=(0,0,1), d=H
        """),
        DUAL(
            "<strong>把它当相机来想，两件事立刻清楚了。</strong>"
            "① <strong>BEV 图有自己的「内参」</strong>——"
            "每像素多少米、原点在哪、覆盖多大范围，"
            "<em>这些是设计选择，而它们决定了下游能分辨什么</em>（第 2 节）。"
            "② <strong>这个单应只对 $z=0$ 的点正确</strong>，"
            "<em>而模块 00 已经给出偏离的精确代价</em>。",
            "<strong>还有一个常被忽略的推论：BEV 变换不产生任何新信息。</strong>"
            "<em>它是一次重采样——所以它只会丢信息，不会增加</em>。"
            "它的价值全在于<strong>把「像素域的距离」换成「米域的距离」</strong>，"
            "从而让下游（融合、跟踪、规控）能在一个物理一致的坐标系里工作。"
            "<strong>所以判断 BEV 做得好不好，标准不是「图看起来对不对」，"
            "而是「米数对不对」</strong>——"
            "<em>而这两件事的相关性比想象的低（第 4 节的坡度就是例子）。</em>",
        ),
    ])),

    # ============================================================== 2
    ("grid", "网格分辨率：均匀网格必然一头过采样、一头欠采样", "".join([
        P("先算一个基本量：<strong>一个图像行往下一像素，在地面上覆盖多少米。</strong>"),
        TABLE(["距离", "像素行 $v$", "该行 ±1 px 覆盖的米数"], [
            ["3.33 m（画幅底边）", "1080", "0.006 m"],
            ["10 m", "720", "0.055 m"],
            ["20 m", "630", "0.220 m"],
            ["30 m", "600", "0.492 m"],
            ["50 m", "576", "<strong>1.351 m</strong>"],
            ["80 m", "562.5", "3.404 m"],
        ]),
        P("<strong>可见地面从 3.33 m 开始（$v=1080$ 对应的距离），"
          "到 100 m 一共只占 522 个图像行——画幅 1080 行的 48%。</strong>"
          "而一个均匀的 0.1 m BEV 网格在 0–100 m 需要 1000 格。"
          "把两者对上："),
        TABLE(["距离段", "占多少图像行", "0.1 m 网格的格数", "每格几行", "结论"], [
            ["3.33–10 m", "360.0", "67", "<strong>5.400</strong>",
             "<strong>过采样 5.4×</strong>（同一像素被复制到多格）"],
            ["10–20 m", "90.0", "100", "0.900", "大致匹配"],
            ["20–50 m", "54.0", "300", "0.180", "<strong>欠采样 5.6×</strong>"],
            ["50–100 m", "18.0", "500", "<strong>0.036</strong>",
             "<strong>欠采样 27.8×</strong>——28 格共享一行"],
        ]),
        DUAL(
            "<strong>这张表说明「均匀 BEV 网格」是一个内在矛盾的设计。</strong>"
            "近处它把一个像素摊到 5 格上（<em>制造出不存在的细节</em>），"
            "远处它把 28 格压进一个像素（<em>丢掉本来有的区分度</em>）。"
            "<strong>而 50–100 m 恰好是 TSR 与规控最关心的区间。</strong>",
            "<strong>三种常见应对，代价递增：</strong>"
            "① <strong>限制 BEV 的作用范围</strong>——"
            "只在采样率合适的区间（本例约 10–30 m）用 IPM，"
            "<em>远处走别的通路</em>（模块 03 的已知尺寸）；"
            "② <strong>非均匀网格</strong>——近处粗、远处细，"
            "<em>让每格对应大致相同的图像行数</em>；"
            "③ <strong>学习式提升</strong>（Lift-Splat / BEVFormer 一类）——"
            "不做单应重采样，而是让网络为每个 BEV 格去图像里取特征，"
            "<em>它绕开了「一个像素对应几格」这个问题，代价是需要训练</em>。"
            "<strong>本课只实现①②，因为③有学习成分，属于 C73–C75。</strong>",
        ),
        CALLOUT("intuition",
                "<strong>一条零成本的自查</strong>："
                "算出你的 BEV 网格在最远关心距离处「每格几行」。"
                "<em>如果它远小于 1，那么那个区域的 BEV 图是插值出来的，"
                "而不是观测到的</em>——"
                "<strong>下游对它的任何细节判断都是在读噪声。</strong>"),
    ])),

    # ============================================================== 2b
    ("forward-vs-inverse", "实现细节：IPM 必须用反向映射", "".join([
        P("知道了单应 $H_{\\text{ipm}}$，还有一个方向问题："
          "<strong>是遍历图像像素往 BEV 里填，还是遍历 BEV 格去图像里取？</strong>"
          "<em>两者的结果完全不同。</em>"),
        TABLE(["做法", "怎么写", "问题"], [
            ["<strong>前向映射</strong>", "对每个图像像素算它的 BEV 格并写入",
             "<strong>留下大量空洞</strong>——见下表"],
            ["<strong>反向映射</strong>（正确）",
             "对每个 BEV 格算它的图像坐标并采样（双线性）",
             "无空洞；<em>代价是远处在重复采样同一批像素</em>"],
        ]),
        P("空洞率可以精确算出来——它就是第 2 节采样率的另一种说法："),
        TABLE(["距离段", "图像行数", "BEV 格数", "最多能填", "<strong>空洞率</strong>"], [
            ["3.33–10 m", "360.5", "67", "67", "0.0%"],
            ["10–20 m", "90.0", "100", "90", "10.0%"],
            ["20–50 m", "54.0", "300", "54", "<strong>82.0%</strong>"],
            ["50–100 m", "18.0", "500", "18", "<strong>96.4%</strong>"],
        ]),
        DUAL(
            "<strong>50–100 m 那一档有 96.4% 的格子填不上。</strong>"
            "<em>而前向映射的实现看起来是完全正常的代码——"
            "它不会报错，只会产出一张远处布满黑洞的 BEV 图</em>。"
            "<strong>常见的「修补」是做形态学闭运算或用近邻填洞，"
            "而那等于用插值伪造观测</strong>——"
            "<em>结果与反向映射几乎一样，但多了一层看不见的假设。</em>",
            "<strong>反向映射还顺带解决了横向的问题。</strong>"
            "一个 0.1 m 宽的 BEV 格在 5 m 处对应 24 个图像列、"
            "在 80 m 处只对应 <strong>1.5 列</strong>。"
            "<em>反向映射时这自然变成「在源图上做一次双线性采样」，"
            "而前向映射需要显式处理「多个像素落进同一格」的聚合</em>。"
            "<strong>所以结论很干脆：IPM 一律用反向映射，"
            "并且把插值方式写进配置</strong>——"
            "<em>因为最近邻与双线性在远处（1.5 列/格）会给出可见的差别。</em>",
        ),
        CALLOUT("warn",
                "反向映射有一个必须处理的边界情况：<strong>地平线以上的 BEV 格。</strong>"
                "<em>它们对应的图像坐标在地平线之上，或者干脆在画幅之外</em>。"
                "<strong>必须显式标成「无观测」而不是采样到某个边缘像素</strong>——"
                "否则 BEV 图的远端会填上天空的颜色，"
                "<em>而下游无法区分「那里是空的」与「那里没被观测」。</em>"),
    ])),

    # ============================================================== 3
    ("assumption-breaks", "地面假设何时崩：一张带代价的清单", "".join([
        P("模块 00 给出了偏离地面的精确代价 "
          "$d_{\\text{read}}=d\\cdot H/(H-z)$，相对误差 $z/(H-z)$。"
          "把它套到实际情形上："),
        TABLE(["情形", "等效的 $z$", "50 m 处的读数", "严重程度"], [
            ["路面起伏 / 减速带", "±0.05 m", "51.7 / 48.4 m（±3%）", "可忽略"],
            ["路肩、排水沟", "−0.15 m", "45.5 m（−9%）", "需注意"],
            ["<strong>1% 上坡</strong>（$z=0.5$ m @50 m）", "0.5 m",
             "<strong>75.0 m（+50%）</strong>", "<strong>致命</strong>（第 4 节）"],
            ["低矮施工牌", "1.0 m", "150 m（+200%）", "致命"],
            ["<strong>限速牌</strong>", "2.0–2.5 m",
             "<strong>无解</strong>（$z>H$）", "<strong>不适用</strong>"],
            ["龙门架悬挂标志", "5.5 m", "无解", "不适用"],
            ["车辆顶部 / 卡车尾板", "1.5–3 m", "无解或极大", "不适用"],
        ]),
        DUAL(
            "<strong>这张表的分界线在 $z\\approx0.15$ m。</strong>"
            "<em>低于它的都可以忽略，高于它的很快变成致命</em>——"
            "因为 $z/(H-z)$ 在 $z\\to H$ 时发散。"
            "<strong>所以 IPM 的正确用法是：只用于「贴地」的目标</strong>"
            "（车道线、路面箭头、可行驶区域边界），"
            "<em>而对任何有高度的目标都要换补法</em>（模块 03 第 8 节的选择树）。",
            "<strong>而实践里最常见的错误不是「知道不该用却用了」，"
            "而是「不知道自己在用」。</strong>"
            "<em>一个检测框的底边被当作「接地点」送进 IPM——"
            "这对车辆是近似成立的（轮胎接地），"
            "对交通标志则完全不成立（底边是立杆或牌面下沿）</em>。"
            "<strong>而代码里这两种目标走的是同一个函数。</strong>"
            "所以模块 00 那条纪律在这里落地为一个具体要求："
            "<strong>IPM 函数必须拿到目标类别，"
            "并对「不贴地」的类别直接拒绝，而不是返回一个数</strong>——"
            "<em>而下一节说明「取框的哪个点」这个问题对两类目标有完全不同的答案</em>。",
        ),
    ])),

    # ============================================================== 3c
    ("which-point", "投影检测框的哪个点？", "".join([
        P("上一节说「检测框底边被当作接地点」。"
          "<strong>那就该问清楚：一个框有上边、中心、下边，投哪一个？</strong>"
          "答案对两类目标完全不同。"),
        H3("贴地目标（车辆，轮胎接地）"),
        TABLE(["取的点", "等效 $z$", "真距 30 m 时读出", "真距 50 m 时读出"], [
            ["框下边（接地）", "0.00 m", "<strong>30.0 m ✓</strong>",
             "<strong>50.0 m ✓</strong>"],
            ["框中心", "0.75 m", "<strong>60.0 m（2× 错）</strong>", "100.0 m（2× 错）"],
            ["框上边（车高 1.5 m）", "1.50 m", "<strong>无解</strong>", "无解"],
        ]),
        H3("交通标志（0.8 m 直径的限速牌，牌心离地 2.2 m）"),
        TABLE(["取的点", "等效 $z$", "真距 30 m 时读出", "真距 50 m 时读出"], [
            ["框上边", "2.6 m", "<strong>无解</strong>", "<strong>无解</strong>"],
            ["框中心", "2.2 m", "<strong>无解</strong>", "<strong>无解</strong>"],
            ["框下边", "1.8 m", "<strong>无解</strong>", "<strong>无解</strong>"],
        ]),
        DUAL(
            "<strong>两张表合起来给出一条很干脆的规则。</strong>"
            "<em>对贴地目标：必须取框下边；取框中心会错整整 2 倍</em>"
            "（因为 $H/(H-0.75)=2$，而这正是中心公式）。"
            "<strong>对交通标志：三个点全部无解</strong>——"
            "<em>因为整块牌都在相机高度之上，所以「换一个点」根本救不了</em>。",
            "<strong>而「取框中心会错 2 倍」这个错误特别值得警惕，"
            "因为它是「响的」的反面：它给出一个完全合理的数字。</strong>"
            "<em>60 m 与 30 m 都是一个正常的距离，没有任何 sanity check 会拦它</em>。"
            "<strong>相比之下标志那三行反而是安全的——无解会被立刻发现。</strong>"
            "<em>所以这一节的结论是：真正危险的不是「假设完全不成立」，"
            "而是「假设部分成立」</em>——"
            "这与模块 01 第 7 节「部分正确比全错危险」是同一条。",
        ),
        CALLOUT("intuition",
                "<strong>把这条规则写进类型，而不是写进注释。</strong>"
                "<em>让 IPM 函数接收的不是一个框，而是一个显式的「接地点」</em>："
                "<code>ipm_range(contact_point_v: float, cls: str)</code>，"
                "<strong>并且由目标类别决定「接地点」怎么从框里取</strong>"
                "（贴地类取 <code>y2</code>，非贴地类<strong>直接拒绝</strong>）。"
                "<em>这样「投哪个点」就不再是每个调用点各自决定的事。</em>"),
    ])),

    # ============================================================== 4
    ("slope", "本模块的中心结论：1% 的坡度值 50%", "".join([
        P("道路坡度让地面不再是 $z=0$ 的平面。"
          "距离 $d$ 处的地面高度是 $z=s\\cdot d$（$s$ 为坡度），代入中心公式："),
        MATH(r"d_{\text{read}} = \frac{d\,H}{H - s\,d},\qquad "
             r"\text{临界距离 } d_{\text{crit}} = \frac{H}{s}"),
        TABLE(["坡度", "临界距离 $H/s$", "20 m", "30 m", "50 m", "80 m"], [
            ["0.5%（很平缓）", "300 m", "21.4", "33.3", "60.0（+20%）", "109.1"],
            ["<strong>1%</strong>", "<strong>150 m</strong>", "23.1", "37.5",
             "<strong>75.0（+50%）</strong>", "171.4"],
            ["2%", "<strong>75 m</strong>", "27.3", "50.0", "150.0（+200%）",
             "<strong>无解</strong>"],
            ["3%", "<strong>50 m</strong>", "33.3", "75.0", "<strong>无解</strong>",
             "无解"],
            ["−1%（下坡）", "—", "17.6", "25.0", "37.5（−25%）", "52.2"],
            ["−2%（下坡）", "—", "15.8", "21.4", "30.0（−40%）", "38.7"],
        ]),
        DUAL(
            "<strong>1% 的坡度在 50 m 处造成 50% 的距离误差。</strong>"
            "而 1% 是<em>非常平缓</em>的坡——高速公路的纵坡限值通常在 3–6%，"
            "<strong>城市道路随处都是 1–2%。</strong>"
            "<em>所以「地面是平的」这个假设在真实道路上几乎从不严格成立。</em>"
            "更麻烦的是<strong>临界距离</strong>：2% 的坡度下，"
            "<strong>75 m 之外 IPM 根本无解</strong>——"
            "而这不是「精度下降」，是几何上射线与地面不再相交。",
            "<strong>方向也要注意：上坡高估、下坡低估。</strong>"
            "<em>上坡时地面「迎向」射线，交点被推远；下坡则相反</em>。"
            "<strong>而上坡的误差幅度远大于下坡</strong>"
            "（+50% vs −25% 在同样 1% 坡度下），"
            "因为分母 $H-sd$ 在上坡时变小。"
            "<strong>所以「保守」不是自动的</strong>："
            "<em>上坡时你的系统会认为障碍物比实际更远——这是不安全的方向。</em>"
            "<strong>而下坡时它认为更近，是安全但会造成误刹的方向。</strong>",
        ),
        H3("三种应对"),
        OL([
            "<strong>在线估计坡度</strong>——用车道线在 BEV 里的收敛程度、"
            "或 IMU 的俯仰积分，把 $s$ 估出来代进公式。"
            "<em>这是生产系统的标准做法，而它把坡度从「未建模误差」变成「一个参数」</em>",
            "<strong>限制 IPM 的作用距离</strong>到 $d\\ll H/s$。"
            "取 $s=2\\%$ 的最坏情况，$H/s=75$ m，"
            "<em>那么把 IPM 限制在 25 m 以内（$d<H/3s$）能把误差控制在 50% 以下</em>",
            "<strong>对有高度的目标根本不用 IPM</strong>（第 3 节）——"
            "<em>这条最便宜，而且它同时解决了坡度问题</em>，"
            "因为已知尺寸测距不依赖地面",
        ]),
        CALLOUT("danger",
                "<strong>坡度还有一个隐蔽的耦合：它与外参 pitch 不可分辨。</strong>"
                "<em>相机低头 $\\delta$ 与地面上坡 $s$ 在近处对成像的影响几乎一样</em>——"
                "所以<strong>「在线估计 pitch」实际上估的是「pitch + 坡度」的和</strong>。"
                "这未必是坏事（对 IPM 来说和才是需要的量），"
                "<em>但它意味着你无法用这个估计去校验静态标定</em>——"
                "而模块 02 第 6 节的可辨识性问题在这里又出现了一次。"),
    ])),

    # ============================================================== 5
    ("multicam", "多相机拼接：重叠区是唯一的免费真值", "".join([
        P("多路相机各自做 IPM，再拼到同一张 BEV 图上。"
          "<strong>关键性质是：重叠区里同一个地面点被观测了两次，"
          "而两次的读数应当相等。</strong>"),
        ASCII("""
   俯视图

        侧相机视场          主相机视场
      ╲                 ╱   │   ╲
       ╲     重叠区 ───┼───┐ │ ┌─┼───
        ╲             ╱  │ │ │ │
         ╲___________╱   └─┼─┘ │
                            车

   重叠区里同一个地面点：
     主相机读出  d_main
     侧相机读出  d_side
     **|d_main − d_side| 就是外参误差的直接读数**
     └── 而它不需要任何真值
        """),
        DUAL(
            "<strong>这是本课少有的、完全不需要真值的检查。</strong>"
            "<em>它抓的是「相对」外参误差——两路之间的不一致</em>。"
            "而它抓不住「共同」误差（两路一起偏，"
            "比如车体 $Z=0$ 平面定义错了）——"
            "<strong>这与模块 03 第 9 节三视角一致性的局限是同一条。</strong>",
            "<strong>拼接还有一个必须显式决定的问题：重叠区用谁的值。</strong>"
            "三种做法："
            "① <strong>硬边界</strong>（各管一块）——"
            "<em>简单，但边界上会出现跳变，而跟踪最怕跳变</em>；"
            "② <strong>按距离加权混合</strong>——"
            "平滑，<em>但两路不一致时混出来的是一个「两边都不对」的值</em>；"
            "③ <strong>按不确定度加权</strong>（模块 03 的 $\\sigma$）——"
            "<em>正确的做法，而它要求每路都诚实地报 $\\sigma$</em>。"
            "<strong>本课推荐③，并且在 $|d_{\\text{main}}-d_{\\text{side}}|$ "
            "超过两者 $\\sigma$ 之和时不混合而是报警</strong>——"
            "<em>因为那说明模型（外参）错了，而加权平均无法修复模型错误。</em>",
        ),
    ])),

    # ============================================================== 6
    ("consistency-monitor", "重叠区一致性：把它做成线上监控", "".join([
        P("上一节说重叠区的不一致量是外参误差的读数。这一节量它有多灵敏。"
          "notebook 第 5 节把侧相机的 pitch 故意拧错 0.5°，然后读两路的差："),
        TABLE(["距离", "主相机", "侧相机（pitch 错 0.5°）", "差值", "相对差"], [
            ["10 m", "10.00 m", "9.44 m", "0.56 m", "5.6%"],
            ["20 m", "20.00 m", "17.90 m", "2.10 m", "10.5%"],
            ["30 m", "30.00 m", "25.53 m", "4.47 m", "14.9%"],
            ["<strong>50 m</strong>", "50.00 m", "38.72 m", "<strong>11.28 m</strong>",
             "<strong>22.6%</strong>"],
        ]),
        DUAL(
            "<strong>0.5° 的外参误差在 50 m 处造成 22.6% 的两路不一致——"
            "这是一个非常容易检出的信号。</strong>"
            "<em>而 0.5° 恰好是「静态标定合格但已经开始漂移」的量级</em>"
            "（模块 02 的验收要求 σ(pitch) &lt; 0.05°，"
            "所以 0.5° 是十倍于验收阈值）。"
            "<strong>灵敏度随距离上升，所以监控应当在重叠区的<em>远端</em>取样。</strong>",
            "<strong>做成监控的三个要点：</strong>"
            "① <strong>报分位数而不是均值</strong>——"
            "个别错误关联会污染均值（与模块 02 第 7 节同理）；"
            "② <strong>分距离档报</strong>——"
            "<em>近端一致而远端不一致是外参角度误差的特征；"
            "两端都不一致更可能是相机高度或主点错了</em>；"
            "③ <strong>它是观测量而不是门禁</strong>——"
            "<em>重叠区一致性会随载重、温度正常波动</em>，"
            "<strong>所以设阈值报警、不设阻断</strong>"
            "（与 C70/C71 模块 05 的「观测量 vs 门禁」是同一条原则）。",
        ),
        CALLOUT("intuition",
                "<strong>这一项的价值在于它是「几何层唯一的线上指标」。</strong>"
                "<em>模块 01–03 的检查全都需要标定板或真值，只能离线做；"
                "而重叠区一致性用的是行驶中每一帧都有的数据</em>。"
                "所以它应当是这一层最先接上监控的东西——"
                "<strong>哪怕只在停车时跑一次也比不跑好。</strong>"),
    ])),

    # ============================================================== 7
    ("fusion-level", "融合的层级：在哪一步把多路合起来", "".join([
        TABLE(["层级", "怎么做", "优点", "代价"], [
            ["<strong>像素/图像层</strong>", "先把多路图拼成一张全景，再检测",
             "只跑一次检测器",
             "<strong>拼接缝会切断目标</strong>；"
             "<em>而缝的位置取决于外参，所以外参漂移会改变检测行为</em>"],
            ["<strong>特征层</strong>", "各路提特征，投到共同的 BEV 网格再融合",
             "信息损失最小；<em>能利用两路的互补性</em>",
             "需要训练；<strong>而第 2 节的采样率问题在这里最尖锐</strong>"],
            ["<strong>结果层</strong>", "各路独立检测 + 测距，在 BEV 里做关联与融合",
             "<strong>各路可独立验证</strong>；"
             "<em>而重叠区一致性只有在这一层能算</em>",
             "重复计算；关联可能出错"],
        ]),
        DUAL(
            "<strong>本课的立场是：结果层是唯一能被几何验证的层级。</strong>"
            "<em>因为只有在这一层，「同一个物理目标的两个独立测量」是显式存在的</em>——"
            "而那正是第 6 节那个监控的前提。"
            "<strong>特征层融合把这两个测量在网络内部就合并了，"
            "于是外参漂移变成一个无法从输出观察的内部误差。</strong>",
            "<strong>而实际系统通常两者都要。</strong>"
            "特征层给效果，结果层给可观测性。"
            "<em>一个实用的组合是：主通路走特征层，"
            "同时保留一条轻量的结果层通路专门用于一致性监控</em>——"
            "<strong>后者不需要很准，它只需要「两路用同一套外参各算一遍」。</strong>"
            "<em>这与 C68 模块 05 的「影子指标」是同一个结构："
            "用一条便宜的旁路来观测主通路无法暴露的状态。</em>",
        ),
    ])),

    # ============================================================== 7b
    ("back-projection", "反向校验：把 BEV 的结果投回图像", "".join([
        P("BEV 是正向链路的终点，"
          "<strong>而把 BEV 里的结果<em>投回图像</em>是一条几乎免费的校验通路。</strong>"),
        ASCII("""
   正向（生产）                      反向（校验）
   图像 → 检测 → IPM → BEV 目标   ──►  BEV 目标 → 投影 → 图像上的框
                                          │
                                          ▼
                                  与原检测框比较
                                  ├── 重合   → 几何链路自洽
                                  └── 不重合 → **链路里有一步错了**
        """),
        DUAL(
            "<strong>这个校验能抓的东西，和它抓不到的东西，都很明确。</strong>"
            "<em>它能抓：$K$ 与 BEV 内参不一致、外参用错了一路、"
            "坐标系约定反了（模块 01 第 0 节那个左右镜像）、"
            "以及任何一步的代码 bug</em>。"
            "<strong>它抓不到：假设本身错了。</strong>"
            "<em>把标志当地面点做 IPM，再投回来——它会精确地回到原位</em>，"
            "因为投影和反投影用的是同一个错误假设。",
            "<strong>所以它是「自洽性检查」而不是「正确性检查」</strong>——"
            "与模块 01 练习 4 的闭环断言是同一类工具，"
            "<em>而模块 01 已经说过：闭环抓自洽，交叉检查抓一致</em>。"
            "<strong>在这一层，「交叉检查」的角色由第 6 节的重叠区一致性承担。</strong>"
            "<em>两者合起来覆盖了「代码错」与「外参错」；"
            "而「假设错」只能靠第 3 节的类别拒绝与第 4 节的坡度处理来防。</em>"
            "<strong>三类错误，三种手段，不能互相替代——这是本模块的总结构。</strong>",
        ),
        CALLOUT("intuition",
                "<strong>实践上这条校验最值得跑在标注环节。</strong>"
                "<em>把标注好的 BEV 真值投回图像叠在原图上，"
                "人眼一眼就能看出坐标系或外参是不是接错了</em>——"
                "而这类错误在纯数值检查里可能一直不显形"
                "（<strong>因为它自洽</strong>）。"),
    ])),

    # ============================================================== 8
    ("checklist", "BEV 的验收清单", "".join([
        OL([
            "<strong>BEV 的「内参」写进配置</strong>："
            "每像素多少米、原点、覆盖范围。"
            "<em>并且和相机 $K$ 一样，它与 BEV 图尺寸绑定</em>",
            "<strong>算出最远关心距离处的「每格几行」</strong>（第 2 节）。"
            "<em>远小于 1 就说明那一段是插值出来的</em>",
            "<strong>IPM 函数必须拿到目标类别并拒绝「不贴地」的类别</strong>（第 3 节）——"
            "不要返回一个数",
            "<strong>坡度要么在线估计、要么把 IPM 限制在 $d<H/3s$ 以内</strong>（第 4 节）",
            "<strong>重叠区一致性接监控</strong>，"
            "按距离档报分位数，<strong>设报警不设阻断</strong>（第 6 节）",
            "<strong>重叠区的融合按 $\\sigma$ 加权</strong>，"
            "且不一致超过 $\\sigma$ 之和时报警而不是混合（第 5 节）",
            "<strong>IPM 一律用反向映射</strong>，插值方式写进配置；"
            "地平线以上的格子标成「无观测」而不是采样到边缘像素（第 2b 节）",
            "<strong>把 BEV 结果投回图像做自洽校验</strong>，"
            "并明确它<em>抓不住假设错误</em>（第 7b 节）",
            "<strong>BEV 映射表带标定文件的哈希</strong>（模块 01 第 5 节的同一条纪律）",
        ]),
        CALLOUT("paper",
                "<strong>如果只做两条：第 3 条和第 4 条。</strong>"
                "<em>它们合起来防住了这一层最大的两个误差源——"
                "「把有高度的目标当地面点」与「假设地面是平的」</em>，"
                "而两者的代价分别是「无解」与「50%」。"
                "<strong>其余五条都是在缩小误差，只有这两条是在防止一整类错误。</strong>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 04 · BEV 投影与多相机融合

四件事：

1. **把 IPM 建成一个反向映射**，并验证地面点闭环。
2. **量出均匀网格的采样率崩塌**：3.33–10 m 过采样 5.4×，
   50–100 m 欠采样 **27.8×**；以及前向映射在那一档留下 **96.4% 的空洞**。
3. **坡度：1% 在 50 m 处值 +50%**，临界距离 $H/s$ —— 本模块的中心结论。
4. **重叠区一致性**：侧相机 pitch 错 0.5°，50 m 处两路差 **22.6%** ——
   这是这一层唯一不需要真值、且行驶中每帧都有的指标。"""),

    md("""## 0 · 环境"""),

    code("""import numpy as np

print('numpy', np.__version__)

H_CAM = 1.5
F, CX, CY = 1200.0, 960.0, 540.0
W, HGT = 1920, 1080

def R_vc(pitch_deg=0.0):
    t = np.deg2rad(pitch_deg)
    return np.array([[0., -np.sin(t),  np.cos(t)],
                     [-1.,        0.,        0.],
                     [0., -np.cos(t), -np.sin(t)]])

CAM_T = np.array([0., 0., H_CAM])

def project(P_v, pitch=0.0, cam_t=None):
    cam_t = CAM_T if cam_t is None else np.asarray(cam_t, float)
    P_c = R_vc(pitch).T @ (np.asarray(P_v, float) - cam_t)
    if P_c[2] <= 1e-9:
        return None
    return np.array([CX + F * P_c[0] / P_c[2], CY + F * P_c[1] / P_c[2]])

def ground_from_pixel(uv, pitch=0.0, cam_t=None, plane_z=0.0):
    '''反投影到 z=plane_z 的平面。返回 None 表示无交点。'''
    cam_t = CAM_T if cam_t is None else np.asarray(cam_t, float)
    d_c = np.array([(uv[0] - CX) / F, (uv[1] - CY) / F, 1.0])
    d_v = R_vc(pitch) @ d_c
    if abs(d_v[2]) < 1e-12:
        return None
    s = (plane_z - cam_t[2]) / d_v[2]
    if s <= 0:
        return None
    return cam_t + s * d_v

d_near = H_CAM * F / (HGT - CY)
print(f'画幅内能看到的地面从 {d_near:.2f} m 开始（v={HGT}）')
print(f'地平线在 v={CY:.0f}，对应无穷远')"""),

    md("""## 1 · IPM 是一个单应，而且必须反向映射

BEV 网格的每一格 → 车体坐标 → 图像坐标 → 采样。
**方向是「从 BEV 去图像取」，不是「从图像往 BEV 填」。**"""),

    code("""class BEVGrid:
    '''BEV 的「内参」：每格多少米、覆盖范围。'''
    def __init__(self, x_range=(0., 100.), y_range=(-10., 10.), res=0.1):
        self.x0, self.x1 = x_range
        self.y0, self.y1 = y_range
        self.res = res
        self.nx = int(round((self.x1 - self.x0) / res))
        self.ny = int(round((self.y1 - self.y0) / res))

    def cell_center(self, ix, iy):
        '''格索引 -> 车体坐标 (X前, Y左, 0)。'''
        return np.array([self.x0 + (ix + 0.5) * self.res,
                         self.y0 + (iy + 0.5) * self.res, 0.0])

    def __repr__(self):
        return (f'BEVGrid({self.x0}-{self.x1}m x {self.y0}-{self.y1}m, '
                f'{self.res}m/格, {self.nx}x{self.ny})')

GRID = BEVGrid()
print(GRID)
print(f'共 {GRID.nx * GRID.ny:,} 格')

def inverse_map(grid, pitch=0.0, cam_t=None):
    '''反向映射：为每个 BEV 格算出源图像坐标。返回 (uv, valid)。'''
    ix, iy = np.meshgrid(np.arange(grid.nx), np.arange(grid.ny), indexing='ij')
    X = grid.x0 + (ix + 0.5) * grid.res
    Y = grid.y0 + (iy + 0.5) * grid.res
    P = np.stack([X, Y, np.zeros_like(X)], axis=-1).reshape(-1, 3)
    cam_t = CAM_T if cam_t is None else np.asarray(cam_t, float)
    Pc = (R_vc(pitch).T @ (P - cam_t).T).T
    uv = np.full((len(P), 2), np.nan)
    ok = Pc[:, 2] > 1e-9
    uv[ok, 0] = CX + F * Pc[ok, 0] / Pc[ok, 2]
    uv[ok, 1] = CY + F * Pc[ok, 1] / Pc[ok, 2]
    inside = ok & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < HGT)
    return uv.reshape(grid.nx, grid.ny, 2), inside.reshape(grid.nx, grid.ny)

UVMAP, VALID = inverse_map(GRID)
print(f'\\n反向映射：{VALID.sum():,} / {VALID.size:,} 格有对应的图像像素 '
      f'({100*VALID.mean():.1f}%)')

# 闭环：BEV 格中心 -> 图像 -> 反投影回地面，必须回到原处
for ix, iy in [(50, 100), (200, 100), (500, 50), (900, 150)]:
    Pc = GRID.cell_center(ix, iy)
    uv = project(Pc)
    back = ground_from_pixel(uv)
    assert np.allclose(back, Pc, atol=1e-9), (ix, iy, back, Pc)
print('✅ BEV 格 -> 图像 -> 地面 精确闭环（< 1e-9 m）')

# 地平线以上的格子必须被标成无观测，而不是采样到边缘
far = GRID.cell_center(GRID.nx - 1, GRID.ny // 2)
print(f'最远一格 X={far[0]:.1f}m -> v={project(far)[1]:.2f}'
      f'（地平线 {CY:.0f} 之下 {project(far)[1]-CY:.2f} px）')"""),

    md("""## 2 · 采样率：均匀网格必然一头过采样、一头欠采样"""),

    code("""def v_of(d):
    return CY + F * H_CAM / d

print(f\"{'距离':>7s} {'像素行 v':>10s} {'±1px 覆盖的米数':>17s}\")
for d in [d_near, 10., 20., 30., 50., 80.]:
    v = v_of(d)
    dd = abs(H_CAM * F / (v + 1 - CY) - d)
    print(f'{d:6.2f}m {v:10.1f} {dd:16.3f}m')

print(f'\\n{\"距离段\":>16s} {\"图像行数\":>10s} {\"0.1m 格数\":>10s} '
      f'{\"每格几行\":>10s} {\"倍数\":>10s}')
bands = [(d_near, 10.), (10., 20.), (20., 50.), (50., 100.)]
stats = {}
for lo, hi in bands:
    rows = v_of(lo) - v_of(hi)
    cells = (hi - lo) / GRID.res
    per = rows / cells
    tag = f'过采样 {per:.1f}x' if per > 1 else f'**欠采样 {1/per:.1f}x**'
    stats[(lo, hi)] = (rows, cells, per)
    print(f'{lo:7.2f}–{hi:5.0f}m {rows:9.1f} {cells:10.0f} {per:10.3f} {tag:>14s}')

near = stats[bands[0]][2]
far_ = stats[bands[-1]][2]
assert near > 5.0, f'近处应过采样 5x 以上，实测 {near:.2f}'
assert far_ < 0.05, f'远处应欠采样 20x 以上，实测 1/{1/far_:.1f}'
print(f'\\n✅ 近处过采样 {near:.1f}x，远处欠采样 {1/far_:.1f}x '
      f'—— 相差 {near/far_:.0f} 倍')
print('   → **均匀 BEV 网格是一个内在矛盾的设计**')

# 前向映射的空洞率 = 同一件事的另一种说法
print(f'\\n前向映射（图像 -> BEV）的空洞率：')
holes = {}
for lo, hi in bands:
    rows, cells, _ = stats[(lo, hi)]
    filled = min(rows, cells)
    holes[(lo, hi)] = 1 - filled / cells
    print(f'  {lo:6.2f}–{hi:5.0f}m: 最多能填 {filled:5.0f}/{cells:.0f} 格'
          f'  -> 空洞率 {100*(1-filled/cells):5.1f}%')
assert holes[bands[-1]] > 0.9, '50–100m 的空洞率应超过 90%'
print(f'\\n✅ 50–100 m 有 {100*holes[bands[-1]]:.1f}% 的格子填不上'
      ' —— 所以 IPM 必须反向映射')

# 横向：一格对应多少列
print(f'\\n横向：0.1m 宽的格在各距离对应多少图像列')
for d in [5., 10., 20., 50., 80.]:
    print(f'  {d:5.0f}m: {F*GRID.res/d:6.2f} px')"""),

    md("""## 3 · 地面假设破坏的代价（回收模块 00 的中心公式）"""),

    code("""def ipm_read(d, z, h=H_CAM):
    '''把离地 z 的目标当地面点处理时读出的距离。'''
    return np.inf if z >= h else d * h / (h - z)

CASES = [
    ('路面起伏 / 减速带',  0.05),
    ('路肩、排水沟',      -0.15),
    ('1% 上坡 @50m',       0.50),
    ('低矮施工牌',         1.00),
    ('限速牌',             2.20),
    ('龙门架标志',         5.50),
]
print(f\"{'情形':>18s} {'等效 z':>8s} {'50m 处读出':>12s} {'相对误差':>10s}\")
for name, z in CASES:
    r = ipm_read(50., z)
    rel = 'inf' if not np.isfinite(r) else f'{100*(r-50)/50:+.0f}%'
    rs = '无解' if not np.isfinite(r) else f'{r:.1f} m'
    print(f'{name:>18s} {z:7.2f}m {rs:>12s} {rel:>10s}')

# 分界线在 z ≈ 0.15 m：低于它可忽略
assert abs(ipm_read(50., 0.05) - 50.) / 50. < 0.05, 'z=0.05 应当可忽略'
assert ipm_read(50., 0.5) / 50. > 1.4, 'z=0.5 应当致命'
assert ipm_read(50., 2.2) == np.inf, 'z>H 必须无解'
print('\\n✅ 分界线在 z≈0.15m：低于它可忽略，高于它很快致命（z/(H−z) 在 z→H 时发散）')

# 检测框底边被当接地点：对车辆近似成立，对标志完全不成立
print('\\n同一个函数被用在两类目标上：')
for name, z in [('车辆（轮胎接地）', 0.0), ('交通标志（牌面下沿 1.8m）', 1.8)]:
    r = ipm_read(50., z)
    print(f'  {name:24s} -> {"无解" if not np.isfinite(r) else f"{r:.1f} m"}')
print('  → **IPM 函数必须拿到类别并拒绝「不贴地」的类别**')"""),

    md("""## 4 · 中心结论：1% 的坡度值 50%

坡度让地面高度变成 $z=s\\cdot d$，代入中心公式得
$d_{\\text{read}}=dH/(H-sd)$，临界距离 $H/s$。"""),

    code("""def ipm_read_slope(d, s, h=H_CAM):
    z = s * d
    return np.inf if z >= h else d * h / (h - z)

SLOPES = [0.005, 0.01, 0.02, 0.03, -0.01, -0.02]
DISTS = [20., 30., 50., 80.]
print(f\"{'坡度':>7s} {'临界距离':>9s} \" + ''.join(f'{d:.0f}m'.rjust(11) for d in DISTS))
for s in SLOPES:
    crit = H_CAM / s if s > 0 else np.inf
    cs = 'inf' if not np.isfinite(crit) else f'{crit:.0f} m'
    row = [ipm_read_slope(d, s) for d in DISTS]
    print(f'{s*100:6.1f}% {cs:>9s} ' +
          ''.join(('       无解' if not np.isfinite(v) else f'{v:10.1f}') for v in row))

# ① 1% 坡度在 50m 处 +50%
r1 = ipm_read_slope(50., 0.01)
print(f'\\n1% 上坡 @50m: {r1:.1f} m（真 50 m）→ {100*(r1-50)/50:+.0f}%')
assert abs(r1 - 75.0) < 1e-9, '1% 坡度在 50m 处应精确给出 75 m'

# ② 临界距离 = H/s
for s in [0.01, 0.02, 0.03]:
    crit = H_CAM / s
    assert ipm_read_slope(crit * 0.999, s) < np.inf
    assert ipm_read_slope(crit, s) == np.inf
    print(f'  s={s*100:.0f}%: 临界距离 {crit:.0f} m —— 之外无解')

# ③ 上坡高估远大于下坡低估（分母的不对称）
up, dn = ipm_read_slope(50., 0.01), ipm_read_slope(50., -0.01)
print(f'\\n±1% 在 50m 处：上坡 {up:.1f} m（{100*(up-50)/50:+.0f}%）'
      f' vs 下坡 {dn:.1f} m（{100*(dn-50)/50:+.0f}%）')
assert (up - 50) > 1.9 * (50 - dn), '上坡的误差幅度应远大于下坡'
print('  → **上坡高估（不安全方向），下坡低估（安全但误刹）**')

# ④ 应对②：把 IPM 限制在 d < H/(3s)
s_worst = 0.02
d_limit = H_CAM / (3 * s_worst)
err_at_limit = ipm_read_slope(d_limit, s_worst) / d_limit - 1
print(f'\\n取最坏坡度 {s_worst*100:.0f}%：限制 IPM 在 {d_limit:.0f} m 以内，'
      f'误差 <= {100*err_at_limit:.0f}%')
assert err_at_limit < 0.55
print('✅ 坡度不是小扰动：1% 值 50%，而 2% 的临界距离只有 75 m')"""),

    md("""## 5 · 多相机与重叠区一致性（无真值的外参监控）"""),

    code("""# 主相机在车体中线，侧相机左移 1.0 m（同高度）
CAM_MAIN = np.array([0., 0.,  H_CAM])
CAM_SIDE = np.array([0., 1.0, H_CAM])

def read_range(P_world, cam_t, pitch=0.0):
    '''某一路相机对一个地面点的 IPM 读数（纵向距离）。'''
    uv = project(P_world, pitch=0.0, cam_t=cam_t)      # 真实成像（外参正确）
    if uv is None:
        return None
    g = ground_from_pixel(uv, pitch=pitch, cam_t=cam_t)  # 用（可能错的）pitch 反投影
    return None if g is None else float(g[0])

print('外参正确时，两路读数应当精确相等：')
for d in [10., 20., 30., 50.]:
    Pw = np.array([d, 0.5, 0.])
    a = read_range(Pw, CAM_MAIN, 0.0)
    b = read_range(Pw, CAM_SIDE, 0.0)
    assert abs(a - d) < 1e-9 and abs(b - d) < 1e-9, (d, a, b)
    print(f'  {d:5.0f}m: 主 {a:.6f}  侧 {b:.6f}')
print('✅ 外参正确 -> 两路一致到 1e-9 m（而这不需要任何真值）\\n')

PITCH_ERR = 0.5
print(f'把侧相机的 pitch 拧错 {PITCH_ERR}°：')
print(f\"{'距离':>6s} {'主相机':>9s} {'侧相机':>9s} {'差值':>9s} {'相对差':>8s}\")
rels = []
for d in [10., 20., 30., 50.]:
    Pw = np.array([d, 0.5, 0.])
    a = read_range(Pw, CAM_MAIN, 0.0)
    b = read_range(Pw, CAM_SIDE, PITCH_ERR)
    rel = abs(a - b) / a
    rels.append(rel)
    print(f'{d:5.0f}m {a:8.2f}m {b:8.2f}m {abs(a-b):8.2f}m {100*rel:7.1f}%')

assert rels == sorted(rels), '灵敏度应随距离上升'
assert rels[-1] > 0.20, f'50m 处相对差应超过 20%，实测 {100*rels[-1]:.1f}%'
print(f'\\n✅ 0.5° 外参误差 → 50 m 处 {100*rels[-1]:.1f}% 的两路不一致')
print('   → 灵敏度随距离上升，所以监控应在重叠区的**远端**取样')
print(f'   → 而 0.5° 是模块 02 验收阈值(0.05°)的 {PITCH_ERR/0.05:.0f} 倍')

# 它抓不住「共同」误差
print('\\n两路一起偏（车体 Z=0 定义错了 5cm）：')
WRONG_H = H_CAM - 0.05
for d in [20., 50.]:
    Pw = np.array([d, 0.5, 0.])
    uv_a = project(Pw, cam_t=CAM_MAIN); uv_b = project(Pw, cam_t=CAM_SIDE)
    a = ground_from_pixel(uv_a, cam_t=np.array([0., 0., WRONG_H]))[0]
    b = ground_from_pixel(uv_b, cam_t=np.array([0., 1., WRONG_H]))[0]
    print(f'  {d:5.0f}m: 主 {a:.3f}  侧 {b:.3f}  差 {abs(a-b):.2e}m'
          f'  （都错了 {100*(a-d)/d:+.1f}%，而一致性检查全过）')
    assert abs(a - b) < 1e-9, '共同误差不会造成不一致'
print('  → **一致性检查只抓「相对」错误，抓不住「共同」错误**')"""),

    md("""## 6 · 反向校验：把 BEV 结果投回图像

它抓「代码/外参错」，**抓不住「假设错」**——因为投影与反投影用同一个假设。"""),

    code("""def bev_to_image(P_bev, cam_t=None, pitch=0.0):
    return project(np.asarray(P_bev, float), pitch=pitch, cam_t=cam_t)

print('情形 A：链路自洽（同一套 K/外参）')
for d in [20., 50.]:
    uv0 = project(np.array([d, 0.5, 0.]))
    g = ground_from_pixel(uv0)
    uv1 = bev_to_image(g)
    print(f'  {d:5.0f}m: 原检测 v={uv0[1]:.3f} -> 投回 v={uv1[1]:.3f}'
          f'  差 {abs(uv1[1]-uv0[1]):.2e} px')
    assert abs(uv1[1] - uv0[1]) < 1e-9

print('\\n情形 B：反投影用了错的 pitch（代码/配置错）')
for d in [20., 50.]:
    uv0 = project(np.array([d, 0.5, 0.]))
    g = ground_from_pixel(uv0, pitch=0.5)          # 错
    uv1 = bev_to_image(g, pitch=0.0)               # 投回时用对的
    print(f'  {d:5.0f}m: 原 v={uv0[1]:.2f} -> 投回 v={uv1[1]:.2f}'
          f'  **差 {abs(uv1[1]-uv0[1]):.2f} px**')
    assert abs(uv1[1] - uv0[1]) > 1.0, '不一致的外参应当被抓住'
print('  → ✅ 抓住了')

print('\\n情形 C：假设错了（把 2.2m 高的标志当地面点）')
Pw = np.array([50., -3.2, 2.2])
uv0 = project(Pw)
g = ground_from_pixel(uv0)
if g is None:
    print(f'  z=2.2m > H：反投影直接无解 —— 这一次假设错误是「响的」')
else:
    uv1 = bev_to_image(g)
    print(f'  原 v={uv0[1]:.2f} -> 投回 v={uv1[1]:.2f}  差 {abs(uv1[1]-uv0[1]):.2e} px')

Pw2 = np.array([50., -3.2, 1.0])                   # 换一个 z<H 的
uv0 = project(Pw2); g = ground_from_pixel(uv0); uv1 = bev_to_image(g)
print(f'  改用 z=1.0m 的低矮牌：原 v={uv0[1]:.2f} -> 投回 v={uv1[1]:.2f}'
      f'  差 {abs(uv1[1]-uv0[1]):.2e} px')
print(f'  而它的 BEV 位置错了 {100*(g[0]-50)/50:+.0f}%（读出 {g[0]:.1f} m）')
assert abs(uv1[1] - uv0[1]) < 1e-9, '假设错误时投影仍然精确闭环'
assert abs(g[0] - 50.) / 50. > 1.9
print('  → ❌ **抓不住**：投影与反投影用同一个错误假设，所以它精确闭环')
print('\\n✅ 三类错误、三种手段：闭环抓代码错 · 重叠区抓外参错 · '
      '类别拒绝与坡度处理抓假设错')"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| 可见地面范围 | 从 **3.33 m** 开始，到 100 m 只占 522 个图像行 |
| 均匀网格采样率 | 近处过采样 **5.4×**，远处欠采样 **27.8×**（相差 150 倍） |
| 前向映射空洞率 | 50–100 m 有 **96.4%** 的格填不上 → 必须反向映射 |
| 地面假设的分界线 | $z\\approx0.15$ m；$z\\ge H$ 时**无解** |
| **坡度** | 1% 在 50 m 处 **+50%**；临界距离 $H/s$，2% 时只有 **75 m** |
| 坡度方向 | 上坡高估（不安全），且幅度远大于下坡低估 |
| **重叠区一致性** | 0.5° 外参误差 → 50 m 处 **22.6%**，灵敏度随距离上升 |
| 它的盲区 | **共同误差不产生不一致**（车体 $Z=0$ 定义错了照样全过） |
| 反向校验 | 抓代码/外参错；**抓不住假设错**（精确闭环） |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：非均匀 BEV 网格

均匀网格近处过采样 5.4×、远处欠采样 27.8×。
实现 `log_bev_edges(d_near, d_far, n_cells)`：给出 `n_cells+1` 个纵向网格边界，
使得**每格对应的图像行数大致相同**。

提示：图像行 $v=c_y+fH/d$ 与 $1/d$ 成线性，
所以「等图像行」等价于「$1/d$ 等分」。"""),

    code("""def log_bev_edges(d_near, d_far, n_cells):
    \"\"\"返回长度 n_cells+1 的距离边界数组，使每格占的图像行数相同。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
N = 200
edges = log_bev_edges(d_near, 100., N)
assert len(edges) == N + 1
assert abs(edges[0] - d_near) < 1e-9 and abs(edges[-1] - 100.) < 1e-9
assert np.all(np.diff(edges) > 0), '边界必须单调递增'

rows_per = np.array([v_of(edges[i]) - v_of(edges[i+1]) for i in range(N)])
uni = np.linspace(d_near, 100., N + 1)
rows_uni = np.array([v_of(uni[i]) - v_of(uni[i+1]) for i in range(N)])

print(f\"{'网格':>10s} {'每格行数 min':>13s} {'max':>9s} {'max/min':>9s}\")
print(f'{"非均匀":>10s} {rows_per.min():12.4f} {rows_per.max():9.4f} '
      f'{rows_per.max()/rows_per.min():9.2f}')
print(f'{"均匀":>10s} {rows_uni.min():12.4f} {rows_uni.max():9.4f} '
      f'{rows_uni.max()/rows_uni.min():9.1f}')

assert rows_per.max() / rows_per.min() < 1.01, \\
    f'非均匀网格应当近乎等行数，实测 {rows_per.max()/rows_per.min():.3f}'
assert rows_uni.max() / rows_uni.min() > 100, '均匀网格的比值应当很大'

# 代价：近处格子变粗
print(f'\\n非均匀网格的格宽（米）：'
      f'最近 {edges[1]-edges[0]:.3f}m，最远 {edges[-1]-edges[-2]:.3f}m')
print(f'均匀网格：处处 {uni[1]-uni[0]:.3f}m')
assert (edges[1]-edges[0]) < (uni[1]-uni[0]), '非均匀网格近处更细'
assert (edges[-1]-edges[-2]) > (uni[-1]-uni[-2]) * 5, '而远处更粗'
print('✅ 练习 1 通过：等图像行 = 1/d 等分；代价是远处的格子在米域变粗')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def log_bev_edges(d_near, d_far, n_cells):
    # v = CY + F*H/d 与 1/d 线性，所以在 1/d 上等分即得等行数
    inv = np.linspace(1.0 / d_near, 1.0 / d_far, n_cells + 1)
    return 1.0 / inv

e = log_bev_edges(d_near, 100., 200)
r = np.array([v_of(e[i]) - v_of(e[i+1]) for i in range(200)])
assert r.max() / r.min() < 1.01
print(f'每格 {r.mean():.4f} 行（比值 {r.max()/r.min():.4f}）')
print('✅ 参考答案 1 通过（这也解释了为什么 BEV 里常见「远处格子更大」的设计）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：带坡度的 IPM 与作用距离上限

实现两个函数：

- `ipm_with_slope(v_px, slope)` —— 已知坡度时的正确读数（返回 `None` 表示无解）
- `ipm_max_range(slope_worst, max_rel_err)` —— 给定最坏坡度与可接受的相对误差，
  返回 IPM 的作用距离上限"""),

    code("""def ipm_with_slope(v_px, slope, h=H_CAM):
    \"\"\"射线与斜面 z = slope*x 的交点的纵向距离；无解返回 None。\"\"\"
    # TODO
    raise NotImplementedError

def ipm_max_range(slope_worst, max_rel_err, h=H_CAM):
    \"\"\"未建模坡度为 slope_worst 时，相对误差不超过 max_rel_err 的最大距离。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# ① 坡度已知时，读数应当精确
for d in [20., 50., 80.]:
    for s in [0.0, 0.01, 0.02, -0.01]:
        z = s * d
        uv = project(np.array([d, 0., z]))
        got = ipm_with_slope(uv[1], s)
        assert got is not None and abs(got - d) < 1e-6, (d, s, got)
print('✅ 坡度已知时 ipm_with_slope 精确复原（误差 < 1e-6 m）')

# ② 坡度未建模（按平地读）时的误差，就是中心公式
for s in [0.01, 0.02]:
    for d in [30., 50.]:
        uv = project(np.array([d, 0., s * d]))
        flat = ipm_with_slope(uv[1], 0.0)
        assert abs(flat - ipm_read_slope(d, s)) < 1e-6, (s, d, flat)
print('✅ 按平地读时与 d·H/(H−sd) 一致')

# ③ 作用距离上限
print(f\"\\n{'最坏坡度':>9s} {'容许相对误差':>13s} {'距离上限':>10s} {'在上限处的实际误差':>19s}\")
for s in [0.01, 0.02, 0.03]:
    for tol in [0.2, 0.5]:
        lim = ipm_max_range(s, tol)
        act = ipm_read_slope(lim, s) / lim - 1
        print(f'{s*100:8.0f}% {tol:12.0%} {lim:9.1f}m {act:18.1%}')
        assert abs(act - tol) < 0.02, f'上限处的误差应当接近容许值（{act:.3f} vs {tol}）'

# 上限随坡度反比、随容许误差单调
assert ipm_max_range(0.01, 0.2) > ipm_max_range(0.02, 0.2)
assert ipm_max_range(0.02, 0.5) > ipm_max_range(0.02, 0.2)
lim2 = ipm_max_range(0.02, 0.5)
print(f'\\n2% 最坏坡度 + 容许 50% 误差 -> IPM 上限 {lim2:.1f} m'
      f'（而临界距离是 {H_CAM/0.02:.0f} m）')
assert lim2 < H_CAM / 0.02, '上限必须小于临界距离'
print('✅ 练习 2 通过：坡度从「未建模误差」变成「一个参数」或「一个距离上限」')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def ipm_with_slope(v_px, slope, h=H_CAM):
    # 射线（pitch=0）：X = t, Z = h - t*(v-CY)/F
    # 斜面：Z = slope * X
    # 解得 t*(slope + (v-CY)/F) = h
    k = (v_px - CY) / F
    den = slope + k
    if den <= 1e-12:
        return None
    return h / den

def ipm_max_range(slope_worst, max_rel_err, h=H_CAM):
    # 未建模坡度下 d_read/d = h/(h - s*d)，令它等于 1+tol
    # => h = (1+tol)(h - s*d) => d = tol*h / (s*(1+tol))
    return max_rel_err * h / (slope_worst * (1 + max_rel_err))

uv = project(np.array([50., 0., 0.5]))
assert abs(ipm_with_slope(uv[1], 0.01) - 50.) < 1e-6
lim = ipm_max_range(0.02, 0.5)
assert abs(ipm_read_slope(lim, 0.02) / lim - 1 - 0.5) < 1e-9
print(f'2%/50% -> 上限 {lim:.2f} m')
print('✅ 参考答案 2 通过（注意 ipm_with_slope 的分母 slope+k：'
      '上坡让分母变大 -> 距离变小，与直觉一致）')"""),

    md("""## ✏️ 练习 3：重叠区一致性监控，以及用它区分错哪个参数

实现 `overlap_monitor(pairs)`，`pairs` 是 `[(d_main, d_side), ...]`，返回 dict：

- `'n'`, `'p50'`, `'p90'` —— 相对差 $|d_1-d_2|/\\min$ 的分位数
- `'by_band'` —— `{'0-20m': p90, '20-50m': p90, '50m+': p90}`（按 `d_main` 分档，无样本时 `nan`）
- `'growth'` —— 最远档 p90 / 最近档 p90（近端为 0 时取 `inf`；两端都为 0 时取 `1.0`）
- `'pattern'` —— `'ok'` / `'angular'` / `'scale'`

**判据来自几何，不是拍的**：

| 错的参数 | 读数 | 相对差随距离 |
|---|---|---|
| 相机高度（或 $f$） | $d_{\\text{read}} = d\\cdot h'/h$ | **恒定**（与 $d$ 无关）→ `'scale'` |
| 俯仰角 | $H/\\tan(\\theta+\\delta)$ | **随距离增长** → `'angular'` |

所以 `pattern` 看的是 `growth` 而不是某一档的绝对值：
`p90 < 0.05` 判 `'ok'`；否则 `growth > 2` 判 `'angular'`，反之判 `'scale'`。"""),

    code("""def overlap_monitor(pairs, thresh=0.05):
    \"\"\"返回 dict(n, p50, p90, by_band, growth, pattern)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def make_pairs(pitch_err=0.0, h_side=H_CAM, dists=None):
    dists = np.linspace(8., 70., 60) if dists is None else dists
    out = []
    for d in dists:
        Pw = np.array([d, 0.5, 0.])
        a = read_range(Pw, CAM_MAIN, 0.0)
        uv = project(Pw, cam_t=CAM_SIDE)
        g = ground_from_pixel(uv, pitch=pitch_err,
                              cam_t=np.array([0., 1.0, h_side]))
        out.append((a, None if g is None else float(g[0])))
    return [(a, b) for a, b in out if b is not None]

P_OK   = make_pairs(0.0)
P_TILT = make_pairs(0.5)                       # 角度误差
P_HIGH = make_pairs(0.0, h_side=H_CAM - 0.10)  # 高度误差

for tag, pr in [('外参正确', P_OK), ('pitch 错 0.5°', P_TILT),
                ('侧相机高度错 10cm', P_HIGH)]:
    r = overlap_monitor(pr)
    assert set(r) == {'n', 'p50', 'p90', 'by_band', 'growth', 'pattern'}
    bands = ' '.join(f'{k}={100*v:5.1f}%' if v == v else f'{k}=  nan'
                     for k, v in r['by_band'].items())
    print(f'{tag:20s} p90={100*r["p90"]:5.1f}%  {bands}  '
          f'growth={r["growth"]:5.2f}  -> {r["pattern"]}')

assert overlap_monitor(P_OK)['pattern'] == 'ok'

# ★ 角度误差：相对差随距离增长
r_t = overlap_monitor(P_TILT)
assert r_t['pattern'] == 'angular', r_t
assert r_t['growth'] > 2.0, f"growth 应 > 2，实测 {r_t['growth']:.2f}"

# ★ 高度误差：相对差**精确恒定**（d_read = d·h'/h 与 d 无关）
r_h = overlap_monitor(P_HIGH)
assert r_h['pattern'] == 'scale', r_h
assert abs(r_h['growth'] - 1.0) < 1e-6, \\
    f"高度误差的 growth 必须精确等于 1，实测 {r_h['growth']:.6f}"
vals = [v for v in r_h['by_band'].values() if v == v]
assert max(vals) - min(vals) < 1e-9, '各档的相对差应当逐位相同'
print(f'\\n高度错 10cm：各档相对差都是 {100*vals[0]:.2f}%'
      f'（理论 {100*0.10/(H_CAM-0.10):.2f}%）—— **与距离无关**')
assert abs(vals[0] - 0.10 / (H_CAM - 0.10)) < 1e-9

print('\\n✅ 练习 3 通过：**growth 把「错哪个参数」缩小到两类**')
print('   角度误差远端更糟（growth>2）· 高度/焦距误差处处相同（growth=1）')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def overlap_monitor(pairs, thresh=0.05):
    pairs = [(float(a), float(b)) for a, b in pairs]
    rel = np.array([abs(a - b) / min(a, b) for a, b in pairs])
    dm = np.array([a for a, _ in pairs])
    bands = {'0-20m': (dm < 20), '20-50m': (dm >= 20) & (dm < 50),
             '50m+': (dm >= 50)}
    by = {k: (float(np.percentile(rel[msk], 90)) if msk.sum() else float('nan'))
          for k, msk in bands.items()}
    present = [v for v in by.values() if v == v]
    near, far = present[0], present[-1]
    if near == 0 and far == 0:
        growth = 1.0
    elif near == 0:
        growth = float('inf')
    else:
        growth = far / near
    p90 = float(np.percentile(rel, 90))
    if p90 < thresh:
        pattern = 'ok'
    else:
        pattern = 'angular' if growth > 2.0 else 'scale'
    return {'n': len(pairs), 'p50': float(np.percentile(rel, 50)),
            'p90': p90, 'by_band': by, 'growth': growth, 'pattern': pattern}

assert overlap_monitor(P_OK)['pattern'] == 'ok'
assert overlap_monitor(P_TILT)['pattern'] == 'angular'
assert overlap_monitor(P_HIGH)['pattern'] == 'scale'
assert abs(overlap_monitor(P_HIGH)['growth'] - 1.0) < 1e-6
print('✅ 参考答案 3 通过')
print('   ① 报**分位数**而不是均值（个别错误关联会污染均值）；')
print('   ② growth 是免费的诊断 —— 它的依据是 d_read = d·h′/h 与距离无关，')
print('      而俯仰误差的 H/tan(θ+δ) 随距离非线性放大。')"""),
    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：BEV 验收器

实现 `bev_audit(grid, d_max_care, slope_worst, overlap_pairs)`，
返回 `(是否通过, {检查项: (通过?, 实测值)})`：

| 检查项 | 阈值 |
|---|---|
| `rows_per_cell_at_dmax` | `>= 0.5`（最远关心距离处每格的图像行数） |
| `ipm_range_limit_ok` | `d_max_care <= ipm_max_range(slope_worst, 0.5)` |
| `overlap_p90` | `< 0.05` |
| `overlap_pattern` | `== 'ok'` |

**用本课的默认配置跑一次——它会不通过。**"""),

    code("""def bev_audit(grid, d_max_care, slope_worst, overlap_pairs):
    \"\"\"返回 (bool, {检查项: (通过?, 实测值)})。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def show(tag, res):
    ok, det = res
    print(f'{tag} -> ' + ('通过' if ok else '**不通过**'))
    for k, (p, v) in det.items():
        vs = f'{v:.4f}' if isinstance(v, float) else str(v)
        print(f'   {"OK  " if p else "FAIL"} {k:24s} = {vs}')
    print()

# ① 本课默认：0.1m 均匀网格 + 关心 80m + 最坏 2% 坡
r_default = bev_audit(GRID, 80., 0.02, P_OK)
show('默认配置（0.1m 均匀网格 / 关心 80m / 最坏 2% 坡）', r_default)
assert r_default[0] is False, '默认配置不该通过'
assert r_default[1]['rows_per_cell_at_dmax'][0] is False, '80m 处欠采样'
assert r_default[1]['ipm_range_limit_ok'][0] is False, '80m 超出坡度允许的上限'

# ② 收缩到 IPM 真正能工作的范围
r_fixed = bev_audit(BEVGrid((0., 25.), (-10., 10.), 0.2), 25., 0.02, P_OK)
show('收缩后（0.2m 网格 / 只关心 25m / 同样 2% 坡）', r_fixed)
assert r_fixed[0] is True, r_fixed[1]

# ③ 外参漂移时被抓住
r_tilt = bev_audit(BEVGrid((0., 25.), (-10., 10.), 0.2), 25., 0.02, P_TILT)
assert r_tilt[0] is False
assert r_tilt[1]['overlap_pattern'][0] is False
print('外参漂移 0.5° -> overlap_pattern =',
      r_tilt[1]['overlap_pattern'][1], '（被抓住）')
print()
print('✅ 练习 4 通过。而最值得记的是①：'
      '**本课默认的 BEV 配置通不过自己的验收**——')
print('   0.1m 均匀网格 + 关心 80m，在采样率和坡度两项上同时不合格。')
print('   而修法不是调参数，是**缩小 IPM 的适用范围**，远处交给别的补法（模块 03）。')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def bev_audit(grid, d_max_care, slope_worst, overlap_pairs):
    # 最远关心距离处，一格对应多少图像行
    rows = abs(v_of(d_max_care) - v_of(d_max_care + grid.res))
    limit = ipm_max_range(slope_worst, 0.5)
    mon = overlap_monitor(overlap_pairs)
    checks = {
        'rows_per_cell_at_dmax': (rows >= 0.5, float(rows)),
        'ipm_range_limit_ok':    (d_max_care <= limit, float(limit)),
        'overlap_p90':           (mon['p90'] < 0.05, mon['p90']),
        'overlap_pattern':       (mon['pattern'] == 'ok', mon['pattern']),
    }
    return all(p for p, _ in checks.values()), checks

assert bev_audit(GRID, 80., 0.02, P_OK)[0] is False
assert bev_audit(BEVGrid((0., 25.), (-10., 10.), 0.2), 25., 0.02, P_OK)[0] is True
print('✅ 参考答案 4 通过')
print('   前两项只依赖配置（不需要跑数据），所以它们可以在设计评审时就算出来；')
print('   后两项需要行驶数据，属于线上监控。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) OpenCV 的 IPM ──
H_ipm = cv2.getPerspectiveTransform(src_quad, dst_quad)   # 四对点
bev   = cv2.warpPerspective(img, H_ipm, (bev_w, bev_h),
                            flags=cv2.INTER_LINEAR)        # ← 内部就是反向映射
#   ⚠️ warpPerspective 默认用 H 的**逆**去源图取值（WARP_INVERSE_MAP 控制方向）。
#      自己写循环时最容易搞反 —— 而搞反的症状就是第 2b 节那张 96.4% 空洞的图。

# ── 2) 地平线以上必须标成「无观测」，不是采样到边缘 ──
bev = cv2.warpPerspective(img, H_ipm, size, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=0)
valid_mask = cv2.warpPerspective(np.ones_like(img[..., 0]), H_ipm, size,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)
#   ↑ 下游必须拿到 valid_mask，否则无法区分「那里是空的」与「那里没被观测」

# ── 3) IPM 函数拿类别，并拒绝不贴地的类别（第 3 节）──
GROUND_CLASSES = {'lane_marking', 'road_arrow', 'drivable_edge'}
def ipm_range(det, calib):
    if det.cls not in GROUND_CLASSES:
        raise NotGroundError(f'{det.cls} 不贴地，请用 known_size 通路')
    ...
#   ↑ 抛异常而不是返回一个数 —— 因为返回值会被静静地用下去

# ── 4) 坡度：在线估计，或写死一个作用距离上限（第 4 节）──
slope = estimate_slope_from_lane_convergence(lanes)   # 或 IMU 积分
d_limit = 0.5 * CAM_H / (WORST_SLOPE * 1.5)           # 练习 2 的公式
assert det.range_m <= d_limit, 'IPM 超出坡度允许的作用距离'

# ── 5) 重叠区一致性打点（第 6 节，唯一的线上几何指标）──
metrics.histogram('geom/overlap_rel_diff', rel, tags={'band': band})
#   报 p50/p90 + 分档；**设报警不设阻断**（它会随载重、温度正常波动）
```

> **落地顺序建议**：先加 `valid_mask`（不加它，下游的一切远处判断都在读插值），
> 再把 IPM 函数改成拿类别并抛异常，最后接重叠区一致性打点。
> <em>而「非均匀网格」放最后——它是优化，前三条是防错。</em>"""),
]
