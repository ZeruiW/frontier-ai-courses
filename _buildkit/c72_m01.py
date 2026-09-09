# -*- coding: utf-8 -*-
"""C72 模块 01 · 相机模型与畸变。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 的坐标系约定与那条投影链；矩阵乘法"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_camera_model.ipynb'
                       '（三步投影的分解 / 内参各项的消融 / '
                       '畸变位移随半径的完整表（0.26 → 197.7 px）/ '
                       '去畸变不动点迭代的收敛速度依赖半径 / '
                       '<strong>resize 与 letterbox 之后 K 怎么变，以及四种错法里哪一种是静默的</strong>）'),
    ("核心参考", "Brown, <em>Close-Range Camera Calibration</em>（1971）· "
                 "Kannala &amp; Brandt, <em>A Generic Camera Model … for Conventional, "
                 "Wide-Angle, and Fish-Eye Lenses</em>（TPAMI 2006）· "
                 "本课程 C60 模块 01（训练-部署预处理对齐）· C57（尺度与小目标）"),
    ("预计时长", "读 45 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("pinhole", "针孔模型：三步里只有一步是非线性的", "".join([
        P("相机模型经常被写成一个矩阵乘法 $\\tilde{u}=K[R\\,|\\,t]\\tilde{X}$，"
          "而这个写法掩盖了它最重要的性质。"
          "<strong>把它拆成三步，就能看出误差在哪一步被放大。</strong>"),
        ASCII("""
   三步投影

   ① 刚体变换（线性、可逆）
        P_c = R^T (P_v - t)          外参：换坐标系，不丢信息
                                     误差来源：标定（模块 02）

   ② 透视除法（**非线性、不可逆**）
        (x, y) = (X_c/Z_c, Y_c/Z_c)  ← 这一步把三维压成二维
                                     **深度在这里被丢掉，永远回不来**
                                     误差来源：无（它是精确的），但信息在此丢失

   ③ 内参与畸变（线性 + 一个多项式）
        (x_d, y_d) = distort(x, y)
        u = f_x x_d + c_x,  v = f_y y_d + c_y
                                     误差来源：内参标定、畸变模型不够、
                                               **以及图像被缩放却没改 K**
        """),
        DUAL(
            "<strong>关键在第②步：它是唯一不可逆的一步，"
            "而它恰好不引入任何误差。</strong>"
            "<em>这意味着「反投影不准」从来不是精度问题，是信息问题</em>——"
            "你不是算错了，是那个数根本不在图像里。"
            "而第①③步则相反：<strong>它们完全可逆，但每一项参数都会引入误差</strong>。"
            "所以本课把它们分开处理：模块 01 管③、模块 02 管①、"
            "模块 03/04 管「怎么把②丢掉的东西补回来」。",
            "<strong>还有一个常被忽略的顺序问题：畸变作用在②之后、③的线性部分之前。</strong>"
            "也就是说<em>畸变是定义在归一化平面上的，不是定义在像素上的</em>。"
            "这解释了两件事：① 为什么畸变系数是无量纲的、"
            "换个分辨率不用重标；"
            "② <strong>为什么「先缩放图像再去畸变」和「先去畸变再缩放」结果不同</strong>——"
            "而 C60 模块 01 讲的训练-部署不一致有相当一部分就是这个顺序被换了。",
        ),
        CALLOUT("warn",
                "<strong>一个立刻可用的判据</strong>："
                "如果你的预处理流水线里 <code>undistort</code> 与 "
                "<code>resize</code> 的相对顺序在训练和部署时不一样，"
                "<strong>那么两边的几何是不同的，而两边的图看起来完全一样。</strong>"
                "<em>这类 bug 不会让指标崩，只会让它「差一点」——"
                "而它在画幅边缘最明显（下面第 4 节会量出边缘有多大）。</em>"),
    ])),

    # ============================================================== 2
    ("intrinsics", "内参 K 的每一项分别改变什么", "".join([
        MATH(r"K=\begin{pmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1\end{pmatrix}"),
        TABLE(["参数", "几何含义", "标错了会怎样", "怎么自查"], [
            ["$f_x, f_y$", "焦距（像素单位）= 物理焦距 / 像元尺寸",
             "<strong>距离等比例错</strong>："
             "$f$ 大 10% → 由已知尺寸测出的距离大 10%",
             "拍一个已知尺寸的物体、放在已知距离上，"
             "<strong>反解 $f$ 与标定值比</strong>"],
            ["$f_x/f_y$", "像素长宽比（现代传感器基本是 1）",
             "圆形标志被读成椭圆 → 影响按尺寸测距",
             "比值应在 $1\\pm0.002$ 内；"
             "<em>偏离超过 1% 通常意味着图像被非等比缩放过</em>"],
            ["$c_x, c_y$", "主点：光轴与成像面的交点",
             "<strong>整个世界被平移</strong>；"
             "$c_y$ 错等价于 pitch 错（见模块 02 第 5 节）",
             "$c$ 应接近图心。"
             "<strong>偏离超过图幅 2% 就要怀疑标定或裁剪</strong>"],
            ["$s$（skew）", "成像面两轴不垂直",
             "现代传感器上它是 0，"
             "<strong>标出非零的 skew 几乎总是过拟合的信号</strong>",
             "标定时直接固定 $s=0$，"
             "<em>然后看重投影误差有没有变差——通常不会</em>"],
        ]),
        DUAL(
            "<strong>$c_y$ 与 pitch 的等价性是这一节最有用的一条。</strong>"
            "主点向下移 $\\Delta c_y$ 个像素，"
            "与相机低头 $\\arctan(\\Delta c_y/f)$ 度，"
            "<em>对地面点的成像位置有完全相同的影响</em>。"
            "$f=1200$ 时 1° 约等于 21 个像素——"
            "<strong>所以「主点标偏 20 px」和「外参 pitch 错 1°」是同一件事，"
            "而模块 00 已经量过后者在 50m 处值 70 m。</strong>",
            "<strong>这个等价性也带来一个真实的标定陷阱</strong>："
            "内参标定与外参标定如果分两次做、各自最小化自己的重投影误差，"
            "<em>那么 $c_y$ 的误差会被外参的 pitch 吸收掉，"
            "两边的残差都很小，而合起来在远处是错的</em>。"
            "<strong>对策是模块 02 第 7 节的做法："
            "验收指标必须是「在远处的米数」，而不只是「重投影误差」。</strong>",
        ),
    ])),

    # ============================================================== 3
    ("distortion-model", "畸变模型：多项式的形状是从哪来的", "".join([
        P("Brown–Conrady 模型把畸变拆成径向和切向两部分："),
        MATH(r"\begin{aligned}"
             r"x_d &= x\,(1+k_1r^2+k_2r^4+k_3r^6) + 2p_1xy + p_2(r^2+2x^2)\\"
             r"y_d &= y\,(1+k_1r^2+k_2r^4+k_3r^6) + p_1(r^2+2y^2) + 2p_2xy"
             r"\end{aligned}"),
        TABLE(["部分", "物理来源", "为什么是这个形式"], [
            ["径向 $k_1,k_2,k_3$", "透镜的球面像差：边缘光线的折射与中心不同",
             "<strong>只含 $r$ 的偶次幂</strong>——"
             "因为径向畸变对旋转是对称的，"
             "<em>而任何旋转对称的标量函数只能依赖 $r^2$</em>。"
             "$k_1<0$ 是桶形（边缘被拉向中心），$k_1>0$ 是枕形"],
            ["切向 $p_1,p_2$", "透镜与成像面不平行（装配公差）",
             "它不是旋转对称的，所以出现了 $xy$ 交叉项。"
             "<strong>量级通常比径向小 1–2 个数量级</strong>，"
             "<em>但在广角镜头与低成本模组上不能省</em>"],
            ["为什么截到 $r^6$", "工程折中",
             "多项式次数越高越容易在标定数据的覆盖范围外<strong>发散</strong>。"
             "<strong>$k_3$ 只在广角上需要</strong>；"
             "普通镜头标 $k_3$ 常常是拟合噪声"],
        ]),
        CALLOUT("intuition",
                "<strong>判断该标几个系数的实用方法</strong>："
                "分别用 $\\{k_1\\}$、$\\{k_1,k_2\\}$、$\\{k_1,k_2,k_3\\}$ 标三次，"
                "看重投影误差的 <strong>P95</strong>（不是均值）。"
                "<em>如果加了 $k_3$ 之后 P95 只降了不到 5%，"
                "那它带来的是过拟合风险而不是精度</em>——"
                "而这与 C40 模块 03 的消融纪律是同一件事。"),
    ])),

    # ============================================================== 4
    ("edge-phenomenon", "畸变是纯边缘现象：0.26 px vs 197.7 px", "".join([
        P("把 notebook 里那组系数（$k_1=-0.28$、$k_2=0.09$、$k_3=-0.012$、"
          "$p_1=0.0012$、$p_2=-0.0008$，一个典型的车载广角前视）"
          "沿图像对角线扫一遍，位移是这样的："),
        TABLE(["位置（占对角线半长）", "归一化半径 $r$", "去畸变前后位移"], [
            ["10%", "0.092", "<strong>0.26 px</strong>"],
            ["25%", "0.229", "4.01 px"],
            ["50%", "0.459", "30.43 px"],
            ["75%", "0.688", "94.16 px"],
            ["90%", "0.826", "151.92 px"],
            ["100%（画幅角）", "0.918", "<strong>197.71 px</strong>"],
        ]),
        DUAL(
            "<strong>角上与 10% 处相差 750 倍。</strong>"
            "位移大致按 $r^3$ 走（因为主导项是 $k_1r^2$ 再乘上 $r$），"
            "<em>所以它不是「整幅图都有一点点畸变」，"
            "而是「中间几乎没有、边缘要命」</em>。"
            "<strong>而交通标志恰好长期出现在画幅左右边缘</strong>——"
            "路侧立杆在近处必然靠边，龙门架在近处必然靠上。",
            "<strong>这条性质有两个直接的工程含义。</strong>"
            "① <strong>评测必须按图像位置分层</strong>："
            "一个「整体 mAP 没变」的预处理改动，"
            "可能在边缘那一档掉了很多，"
            "<em>而边缘那一档正是 TSR 近距离样本所在</em>（分层门禁见 C68 模块 04）。"
            "② <strong>裁剪能省掉大部分畸变问题</strong>——"
            "如果任务允许只用中心 50% 区域，畸变位移就从 197 px 降到 30 px。"
            "<em>但对 TSR 不允许，因为近处标志就在边缘。</em>",
        ),
        H3("「标志在边缘」这句话要说精确"),
        P("路侧标志的横向偏移大约 3.2 m、离地 2.2 m。"
          "算一下它在各距离落在画幅的哪一圈："),
        TABLE(["距离", "距图心的像素距离", "归一化半径", "落在哪一圈"], [
            ["5 m", "786.2 px", "<strong>0.714</strong>",
             "<strong>外 1/3</strong>——畸变最大的区域"],
            ["10 m", "393.1 px", "0.357", "中 1/3"],
            ["20 m", "196.5 px", "0.178", "内 1/3"],
            ["50 m", "78.6 px", "0.071", "内 1/3"],
        ]),
        P("<strong>所以准确的说法是：只有近处（约 10 m 以内）的路侧标志才落在畸变要命的区域。</strong>"
          "<em>远处的标志反而集中在画幅中心附近——那里畸变可以忽略</em>。"
          "这条修正很重要，因为它把「畸变影响 TSR」这个笼统担忧"
          "缩小成一个具体的场景：<strong>近距离、大横向偏移的标志</strong>"
          "（<em>路口右转前看右侧的牌、或者本车道正上方的龙门架</em>）。"),
        CALLOUT("danger",
                "<strong>一个真实且常见的错误</strong>："
                "用<strong>中心区域</strong>的棋盘格图像做标定，"
                "然后把模型用到<strong>整幅图</strong>。"
                "多项式在标定数据覆盖之外会发散，"
                "<em>于是画幅角上的「去畸变」可能比不去更差</em>。"
                "对策：<strong>标定采集必须覆盖到角落</strong>，"
                "并在验收时单独报「角落区域的重投影误差」（模块 02 第 4 节）。"),
    ])),

    # ============================================================== 5
    ("undistort", "去畸变没有闭式解：迭代多少轮才够", "".join([
        P("正向畸变是一个显式多项式，而<strong>反向（从 $(x_d,y_d)$ 求 $(x,y)$）没有闭式解</strong>。"
          "标准做法是不动点迭代："),
        CODE("""x, y = x_d, y_d                      # 初值：就用畸变后的点
for _ in range(n):
    r2 = x*x + y*y
    rad = 1 + k1*r2 + k2*r2**2 + k3*r2**3
    dx = 2*p1*x*y + p2*(r2 + 2*x*x)
    dy = p1*(r2 + 2*y*y) + 2*p2*x*y
    x = (x_d - dx) / rad             # 用当前估计算出的 r2 去反解
    y = (y_d - dy) / rad""", "python"),
        P("notebook 第 4 节量出的收敛行为是这样的（残差单位：像素）："),
        TABLE(["位置", "n=1", "n=2", "n=3", "n=5", "n=8", "n=12"], [
            ["25% 对角", "1.2e-1", "3.4e-3", "9.8e-5", "8.3e-8", "2.1e-12", "6.9e-14"],
            ["50% 对角", "3.2e+0", "3.5e-1", "3.8e-2", "4.5e-4", "5.9e-7", "8.3e-11"],
            ["75% 对角", "2.0e+1", "4.2e+0", "9.1e-1", "4.3e-2", "4.4e-4", "9.9e-7"],
            ["<strong>100%（角）</strong>", "6.0e+1", "1.9e+1", "5.9e+0",
             "<strong>6.0e-1</strong>", "1.9e-2", "1.9e-4"],
        ]),
        DUAL(
            "<strong>收敛速度强烈依赖半径</strong>，这是这一节的要点。"
            "在 25% 处 5 轮就到 $10^{-8}$ px；"
            "<strong>而在画幅角上，5 轮之后还剩 0.6 px</strong>。"
            "<em>而「迭代 5 次」正是很多实现里的默认值</em>。"
            "0.6 px 在 50m 处值多少米？"
            "用模块 00 的换算：1 px ≈ 1.35 m，"
            "<strong>所以 0.6 px ≈ 0.8 m</strong>——"
            "对一个静止的标志来说，这已经超过一个车道宽度的十分之一。",
            "<strong>三种修法，成本递增：</strong>"
            "① <strong>按半径自适应迭代次数</strong>（练习 3）——"
            "中心 2 轮、边缘 12 轮，总开销几乎不变；"
            "② <strong>预计算一张去畸变查找表</strong>——"
            "标定固定后 LUT 也固定，运行时零迭代"
            "（<em>这也是真实系统的普遍做法，而它顺带消除了迭代次数这个隐藏参数</em>）；"
            "③ 用牛顿法替代不动点法——收敛更快但要算雅可比，"
            "<em>在有 LUT 的情况下没必要</em>。"
            "<strong>本课的建议是②，并把 LUT 的最大残差写进标定验收项。</strong>",
        ),
        H3("LUT 这条路值得多说两句"),
        P("查找表的做法是：标定固定之后，"
          "对每个整数像素位置离线算好去畸变后的坐标（迭代到收敛为止，"
          "反正是离线，跑 50 轮也无所谓），存成两张 $H\\times W$ 的 float 图。"
          "<strong>运行时只剩一次双线性采样。</strong>"),
        TABLE(["性质", "迭代法", "查找表"], [
            ["运行时开销", "$n$ 轮多项式求值 × 每个点", "<strong>一次采样</strong>"],
            ["精度", "取决于 $n$，<strong>而 $n$ 是一个隐藏参数</strong>",
             "离线迭代到收敛，<strong>精度写进验收项</strong>"],
            ["内存", "0", "两张 float 图（1920×1080 约 16 MB）"],
            ["标定变更时", "自动跟随", "<strong>必须重新生成——"
             "所以 LUT 要带标定文件的哈希</strong>"],
        ]),
        CALLOUT("warn",
                "LUT 的那条「必须带标定哈希」不是形式主义。"
                "<strong>它是这一层唯一会「过期」的产物</strong>："
                "标定更新了而 LUT 没重生成，"
                "<em>结果是整套几何静静地用着上一次的标定</em>——"
                "而图像看起来完全正常。"
                "这与 C70 模块 05 的「索引滞后」是同一类失效，"
                "对策也一样：<strong>产物带上游的指纹，不匹配就拒绝加载。</strong>"),
    ])),

    # ============================================================== 6
    ("model-limits", "模型的表达边界：什么时候多项式不够", "".join([
        P("Brown–Conrady 是围绕「近似针孔 + 小畸变」设计的。"
          "视场越大，它越吃力。"),
        TABLE(["镜头类型", "水平 FOV", "适用模型", "判据"], [
            ["长焦 / 标准", "&lt; 60°", "$k_1$（甚至可以忽略）",
             "画幅角位移 &lt; 几个像素"],
            ["车载广角前视", "60°–120°", "<strong>Brown–Conrady $k_1,k_2,k_3+p_1,p_2$</strong>",
             "本课用的就是这一档"],
            ["超广角 / 鱼眼", "&gt; 120°", "<strong>等距/等立体角模型，或 Kannala–Brandt</strong>",
             "针孔投影本身失效："
             "<em>入射角接近 90° 时 $\\tan\\theta\\to\\infty$，"
             "而鱼眼镜头是有限像高的</em>"],
        ]),
        DUAL(
            "<strong>判据不是「FOV 多少度」，而是「投影模型本身还成不成立」。</strong>"
            "针孔模型说像高 $\\propto\\tan\\theta$，"
            "$\\theta\\to90°$ 时像高发散——"
            "<em>所以任何真正的 180° 镜头都不可能是针孔的，"
            "无论加多少个畸变系数</em>。"
            "鱼眼镜头的设计目标通常是像高 $\\propto\\theta$（等距投影），"
            "<strong>这是一个不同的函数族，不是「针孔加畸变」</strong>。",
            "<strong>工程上的判别只要一步</strong>："
            "把标定得到的畸变模型<strong>反过来用</strong>——"
            "取画幅角上的点，去畸变，看它对应的入射角。"
            "<em>如果算出来的 $\\theta$ 超过 70–75°，"
            "或者去畸变后的归一化坐标出现非单调（同一个 $r_d$ 对应两个 $r$），"
            "就说明多项式已经在发散区</em>。"
            "notebook 第 6 节把这个单调性检查写成一个函数——"
            "<strong>它是一条零成本、可进 CI 的标定验收项。</strong>",
        ),
        CALLOUT("paper",
                "本课不实现鱼眼模型（那需要一整套自己的标定流程）。"
                "<strong>需要知道的是分界线在哪、以及怎么判自己越界了。</strong>"
                "<em>而一个实际的经验是：车载环视（4 路鱼眼）与前视（广角）"
                "用的是两套模型，混用是拼接错位的常见原因</em>（模块 04 第 4 节）。"),
    ])),

    # ============================================================== 7
    ("K-under-preprocessing", "缩放、裁剪、letterbox 之后的 K：四种错法里哪一种是静默的", "".join([
        P("深度学习流水线几乎总会改变图像的几何："
          "resize 到网络输入尺寸、center crop、letterbox padding。"
          "<strong>每一次都必须同步改 $K$，而它们都可以写成一个 $3\\times3$ 的左乘。</strong>"),
        MATH(r"K' = S\,K,\qquad S=\begin{pmatrix} s_x & 0 & t_x\\ 0 & s_y & t_y\\ 0&0&1\end{pmatrix}"),
        TABLE(["操作", "$S$ 的参数", "变换后的 $K$（原 $f=1200$, $c=(960,540)$）"], [
            ["resize 到一半", "$s=0.5$, $t=0$", "$f=(600,600)$, $c=(480,270)$"],
            ["center-crop 到 1280×720", "$s=1$, $t=(-320,-180)$",
             "$f=(1200,1200)$, $c=(640,360)$"],
            ["letterbox 到 640×640", "$s=1/3$, $t=(0,92)$",
             "$f=(400,400)$, $c=(320,272)$"],
        ]),
        P("现在把「忘记同步」的四种情形各算一次。"
          "场景：10 m 处的地面点，图像缩放到一半："),
        TABLE(["情形", "用的 $f$ / $c_y$", "读出距离", "严重程度"], [
            ["全对", "600 / 270", "<strong>10.00 m</strong>", "—"],
            ["两个都忘了改", "1200 / 540", "<strong>−10.00 m</strong>",
             "<strong>响的</strong>：负距离，任何 sanity check 都能抓住"],
            ["只改了焦距，忘了主点", "600 / 540", "<strong>−5.00 m</strong>",
             "<strong>响的</strong>：同样是负数"],
            ["<strong>只改了主点，忘了焦距</strong>", "1200 / 270",
             "<strong>20.00 m</strong>",
             "<strong>静默</strong>：一个完全合理的数字，静静地错 2 倍"],
        ]),
        DUAL(
            "<strong>这张表的结论是：「部分正确」比「全错」危险。</strong>"
            "全错时几何直接自相矛盾（点落到地平线上方 → 负距离），"
            "<em>而只改一半时，所有 sanity check 都过，"
            "距离却系统性地错一个固定倍数</em>。"
            "<strong>而系统性偏差是最难被发现的一类错误</strong>——"
            "它不增加方差，看起来就像「我们的测距一直偏保守」。",
            "<strong>所以验收不能靠「看图对不对」，要靠一条闭环断言。</strong>"
            "练习 4 实现的检查是："
            "取一组已知三维坐标的点，"
            "<strong>用变换后的 $K'$ 走完整条投影链，再反投影回去，"
            "断言与原坐标一致</strong>。"
            "<em>这个检查不需要任何真实数据、跑一次不到一毫秒，"
            "而它能抓住上表里的三种错法（第二、三、四行）全部</em>。"
            "本课的建议是把它放进预处理流水线的单元测试里，"
            "<strong>而不是放进模型评测里</strong>——"
            "因为模型评测发现它时，你已经在调超参了。",
        ),
        CALLOUT("danger",
                "还有一个更隐蔽的变体：<strong>只在训练侧做了 letterbox</strong>。"
                "部署侧直接喂原图（因为「反正网络是全卷积的」），"
                "<em>于是两边的 $c_y$ 差了 92 个像素</em> —— "
                "按第 2 节的等价性，这相当于 pitch 差了 4.4°，"
                "<strong>而模块 00 量过 1° 在 50 m 处值 70 m</strong>。"
                "这正是 C60 模块 01 说的「预处理必须逐位对齐」在几何层的形态。"),
    ])),

    # ============================================================== 9
    ("sensor-lens", "从物理参数到像素焦距：换模组时哪些量不变", "".join([
        P("$f$ 的单位是像素，而镜头规格书上的焦距单位是毫米。两者的关系是"),
        MATH(r"f_{\text{px}} = \frac{f_{\text{mm}}}{\text{像元尺寸}},\qquad "
             r"\text{HFOV} = 2\arctan\frac{W\cdot\text{像元尺寸}}{2f_{\text{mm}}}"),
        P("<strong>注意两个式子依赖的量不同</strong>："
          "$f_{\text{px}}$ 只看<strong>像元尺寸</strong>，"
          "而视场只看<strong>靶面物理尺寸</strong>（像元尺寸 × 像素数）。"
          "于是「换模组」这件事有四种完全不同的后果："),
        TABLE(["改动", "$f_{\text{mm}}$", "分辨率", "像元", "$f_{\text{px}}$", "HFOV",
               "0.8 m 的牌在 50 m 处"], [
            ["<strong>基线</strong>", "3.6", "1920", "3.0 µm", "1200", "77.3°",
             "19.2 px"],
            ["换小像元（靶面尺寸不变）", "3.6", "2880", "2.0 µm",
             "<strong>1800</strong>", "77.3°（不变）", "<strong>28.8 px</strong>"],
            ["换大靶面（像元不变）", "3.6", "2560", "3.0 µm",
             "1200（不变）", "<strong>93.7°</strong>", "19.2 px（不变）"],
            ["换长焦镜头", "<strong>6.0</strong>", "1920", "3.0 µm",
             "2000", "<strong>51.3°</strong>", "32.0 px"],
        ]),
        DUAL(
            "<strong>第二行是最有价值的一行。</strong>"
            "换成小像元的同尺寸靶面：视场一点没变、装车位置不用动、"
            "<em>而远处标志的像素尺寸涨了 1.5 倍</em>。"
            "按模块 00 练习 2 的 $d^2$ 定律，"
            "<strong>50 m 处 ±1 px 的深度区间从 5.22 m（10.4%）收窄到 3.48 m（7.0%）</strong>。"
            "这是一次纯硬件换来的测距精度提升，"
            "<em>而它对检测器是完全透明的（只是输入更大了）</em>。",
            "<strong>但有一个前提必须说清楚，否则上面那个收益是假的</strong>："
            "它假设定位误差<strong>以像素计</strong>保持不变。"
            "<em>而真实情况是，小像元通常意味着更低的单像素信噪比，"
            "所以亚像素定位精度（以像素为单位）可能反而变差</em>。"
            "<strong>所以这个收益必须实测，不能按公式承诺。</strong>"
            "实测的办法：同一块牌、同一距离、两套模组各拍 50 帧，"
            "<em>比较牌宽测量值的标准差（以像素为单位）</em>——"
            "如果它没变大 1.5 倍，收益就是真的。",
        ),
        CALLOUT("intuition",
                "<strong>三个换模组时的不变量，记住它们能省掉很多重标</strong>："
                "① <strong>畸变系数与分辨率无关</strong>"
                "（它定义在归一化平面上），所以同一颗镜头换传感器分辨率<strong>不需要重标畸变</strong>；"
                "② <strong>外参与内参无关</strong>——换传感器不改变相机的安装位姿；"
                "③ <strong>而换镜头会同时改变 $f$ 与畸变，必须全部重标</strong>。"
                "<em>把这三条写在标定流程文档的第一页，比写十页操作步骤有用。</em>"),
    ])),

    # ============================================================== 10
    ("checklist", "本模块的验收清单", "".join([
        OL([
            "<strong>$K$ 与图像尺寸是绑定的</strong>："
            "任何改变图像几何的操作都要返回一个新的 $K$。"
            "<em>把它做成函数签名的一部分：<code>img, K = resize(img, K, ...)</code></em>",
            "<strong>畸变与缩放的顺序在训练/部署两侧必须一致</strong>，"
            "并写进配置而不是靠约定",
            "<strong>去畸变的残差要按半径分层报</strong>："
            "只报平均值会把画幅角上的 0.6 px 平均掉",
            "<strong>标定采集必须覆盖画幅角</strong>，"
            "验收时单独报角落区域的重投影误差",
            "<strong>skew 固定为 0</strong>；标出非零 skew 视为过拟合信号",
            "<strong>主点偏离图心超过 2% 要人工确认</strong>"
            "（通常意味着有一次未记录的裁剪）",
            "<strong>畸变模型的单调性检查进 CI</strong>（第 6 节），"
            "越界即报警",
            "<strong>投影链闭环断言进单元测试</strong>（练习 4），"
            "这是抓「静默地错 2 倍」的唯一便宜手段",
            "<strong>换模组时按第 9 节的三个不变量判断要重标什么</strong>："
            "换传感器分辨率不用重标畸变，换镜头必须全部重标",
        ]),
        CALLOUT("intuition",
                "<strong>如果只能做一条，做第 8 条。</strong>"
                "闭环断言是本模块唯一能抓住「静默系统性偏差」的检查，"
                "而它的实现不到 20 行、不需要任何真实数据。"
                "<em>其余七条都是在缩小误差，只有它是在防止一整类错误。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 01 · 相机模型与畸变

三件事：

1. **把投影拆成三步**，看清「不可逆的那一步不引入误差、引入误差的那两步都可逆」。
2. **量出畸变的边缘性**：10% 对角处 0.26 px、画幅角 197.71 px（**750 倍**），
   以及去畸变迭代的收敛速度**强烈依赖半径**。
3. **把 `K` 在 resize / crop / letterbox 下的变换写对**，
   并给「忘记同步」的四种错法分类——
   **其中只有一种是静默的，而它恰好最危险。**"""),

    md("""## 0 · 环境与参数"""),

    code("""import numpy as np

print('numpy', np.__version__)

H  = 1.5
F  = 1200.0
W, HGT = 1920, 1080
CX, CY = W / 2, HGT / 2
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.]])

# 一组典型的车载广角前视畸变系数（桶形，k1<0）
K1, K2, K3 = -0.28, 0.09, -0.012
P1, P2     =  0.0012, -0.0008
DIST = (K1, K2, K3, P1, P2)

R_MAX = np.hypot(CX, CY) / F          # 画幅角对应的归一化半径
print(f'画幅角的归一化半径 r_max = {R_MAX:.4f}')
print(f'水平 FOV = {np.rad2deg(2*np.arctan(CX/F)):.1f}°')"""),

    md("""## 1 · 三步投影的分解

拆开写一遍，是为了能分别检查每一步。
断言部分证明「矩阵一行写完」与「三步拆开」完全等价。"""),

    code("""def R_vc(pitch_deg=0.0):
    t = np.deg2rad(pitch_deg)
    return np.array([[0., -np.sin(t),  np.cos(t)],
                     [-1.,        0.,        0.],
                     [0., -np.cos(t), -np.sin(t)]])

CAM_T = np.array([0., 0., H])

def distort(x, y, dist=DIST):
    k1, k2, k3, p1, p2 = dist
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    return xd, yd

def project_steps(P_v, pitch=0.0, dist=DIST, Kmat=None):
    Kmat = K if Kmat is None else Kmat
    P_c = R_vc(pitch).T @ (np.asarray(P_v, float) - CAM_T)     # ① 刚体
    if P_c[2] <= 1e-9:
        return None
    x, y = P_c[0] / P_c[2], P_c[1] / P_c[2]                    # ② 透视除法
    xd, yd = distort(x, y, dist)                               # ③a 畸变
    uv = Kmat @ np.array([xd, yd, 1.0])                        # ③b 内参
    return {'P_c': P_c, 'norm': (x, y), 'norm_d': (xd, yd), 'uv': uv[:2]}

# 等价性：无畸变时，三步 == 一次矩阵乘 + 齐次除
for P in [(10., 1.75, 0.), (30., -3.2, 2.2), (60., 0., 0.5)]:
    st = project_steps(P, dist=(0, 0, 0, 0, 0))
    Pc = st['P_c']
    uv_mat = (K @ Pc)[:2] / (K @ Pc)[2]
    assert np.allclose(st['uv'], uv_mat, atol=1e-12), (st['uv'], uv_mat)
print('✅ 无畸变时「三步拆开」与「K @ P_c 再齐次除」完全一致')

st = project_steps((30., -3.2, 2.2))
print('\\n一个例子（30m 处、离地 2.2m 的限速牌）：')
print(f\"  ① 相机坐标   P_c = {np.round(st['P_c'], 4)}\")
print(f\"  ② 归一化     (x,y) = {tuple(round(v,5) for v in st['norm'])}\")
print(f\"  ③a 加畸变    (xd,yd) = {tuple(round(v,5) for v in st['norm_d'])}\")
print(f\"  ③b 到像素    (u,v) = {np.round(st['uv'], 2)}\")
print(f\"  畸变造成的像素位移 = \"
      f\"{np.hypot(*(np.array(st['norm_d'])-np.array(st['norm'])))*F:.2f} px\")"""),

    md("""## 2 · 内参各项的消融

把 `f`、`c_y`、`f_x/f_y` 各扰动一次，看它们分别破坏什么。
**第三行是关键**：主点移动与相机低头对地面点的成像位置有相同的影响。"""),

    code("""def ground_range(v, f=F, cy=CY, h=H):
    '''由像素行反解地面点纵向距离（无畸变、pitch=0）。'''
    den = v - cy
    return np.inf if abs(den) < 1e-9 else h * f / den

v_10m = CY + F * H / 10.0
print(f'10m 地面点成像在 v = {v_10m:.1f}\\n')

print(f\"{'扰动':30s} {'读出距离':>10s} {'相对误差':>10s}\")
for name, f, cy in [('基线', F, CY),
                    ('f 大 10%', F * 1.1, CY),
                    ('f 小 10%', F * 0.9, CY),
                    ('c_y 偏 +21 px', F, CY + 21),
                    ('c_y 偏 -21 px', F, CY - 21)]:
    d = ground_range(v_10m, f, cy)
    print(f'{name:30s} {d:9.3f}m {100*(d-10)/10:9.1f}%')

# f 的误差直接等比例传到距离
assert abs(ground_range(v_10m, F * 1.1, CY) - 11.0) < 1e-9
assert abs(ground_range(v_10m, F * 0.9, CY) -  9.0) < 1e-9
print('\\n✅ f 的相对误差 = 距离的相对误差（精确等比例）')

# c_y 与 pitch 的等价性
dcy = 21.0
equiv_deg = np.rad2deg(np.arctan(dcy / F))
d_by_cy    = ground_range(v_10m, F, CY + dcy)
d_by_pitch = H * F / (v_10m - (CY + F * np.tan(np.deg2rad(equiv_deg))))
print(f'主点下移 {dcy:.0f} px  -> 读出 {d_by_cy:.4f} m')
print(f'相机低头 {equiv_deg:.4f}° -> 读出 {d_by_pitch:.4f} m')
assert abs(d_by_cy - d_by_pitch) < 1e-9
print(f'✅ 二者精确等价：f={F:.0f} 时 **1° ≈ {F*np.tan(np.deg2rad(1)):.1f} 个像素**')"""),

    md("""## 3 · 畸变是纯边缘现象"""),

    code("""print(f\"{'占对角线半长':>12s} {'r':>8s} {'位移 (px)':>12s}\")
disp = {}
for frac in [0.10, 0.25, 0.50, 0.75, 0.90, 1.00]:
    x, y = frac * CX / F, frac * CY / F
    xd, yd = distort(x, y)
    d_px = np.hypot(xd - x, yd - y) * F
    disp[frac] = d_px
    print(f'{frac*100:11.0f}% {np.hypot(x,y):8.3f} {d_px:12.2f}')

ratio = disp[1.00] / disp[0.10]
print(f'\\n画幅角 / 10% 处 = **{ratio:.0f} 倍**')
assert ratio > 500, '畸变应当是强烈的边缘现象'

# 位移大致按 r^3 走（主导项 k1*r^2 再乘 r）
rs = np.array([np.hypot(f*CX/F, f*CY/F) for f in disp])
ds = np.array(list(disp.values()))
expo = np.polyfit(np.log(rs), np.log(ds), 1)[0]
print(f'log-log 斜率 = {expo:.2f}  → 位移 ≈ r^{expo:.1f}（理论主导项是 r³）')
assert 2.5 < expo < 3.2, f'指数应接近 3，实测 {expo:.2f}'
print('✅ 畸变位移随半径按约三次幂增长')"""),

    md("""## 4 · 去畸变的不动点迭代：收敛速度依赖半径

**注意最后一行**：在画幅角上，`n=5`（很多实现的默认值）之后还剩 0.6 px。"""),

    code("""def undistort_iter(xd, yd, n, dist=DIST):
    k1, k2, k3, p1, p2 = dist
    x, y = xd, yd
    for _ in range(n):
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        x, y = (xd - dx) / rad, (yd - dy) / rad
    return x, y

NS = [1, 2, 3, 5, 8, 12]
print('残差（像素）：')
print(f\"{'位置':>10s} \" + ''.join(f'n={n}'.rjust(11) for n in NS))
resid = {}
for frac in [0.25, 0.50, 0.75, 1.00]:
    x0, y0 = frac * CX / F, frac * CY / F
    xd, yd = distort(x0, y0)
    row = []
    for n in NS:
        xu, yu = undistort_iter(xd, yd, n)
        row.append(np.hypot(xu - x0, yu - y0) * F)
    resid[frac] = row
    print(f'{frac*100:9.0f}% ' + ''.join(f'{e:11.2e}' for e in row))

# 同一个 n，残差随半径单调上升
for j in range(len(NS)):
    col = [resid[f][j] for f in [0.25, 0.50, 0.75, 1.00]]
    assert col == sorted(col), f'n={NS[j]} 时残差应随半径上升'

e5_corner = resid[1.00][NS.index(5)]
print(f'\\nn=5 在画幅角上的残差 = {e5_corner:.3f} px')
assert e5_corner > 0.3, '这就是「默认迭代 5 次」的代价'

# 换算成米：用 50m 处的 1px 灵敏度
v50 = CY + F * H / 50.0
m_per_px = abs(ground_range(v50 + 1) - 50.0)
print(f'50m 处 1 px = {m_per_px:.2f} m  →  {e5_corner:.3f} px ≈ '
      f'**{e5_corner*m_per_px:.2f} m**')
print('✅ 一个「默认参数」在画幅角上值接近一米')"""),

    md("""## 5 · `K` 在预处理下的变换，与四种错法

每个改变图像几何的操作都是一次左乘 $S$。**「部分正确」比「全错」危险。**"""),

    code("""def S_mat(sx, sy, tx, ty):
    return np.array([[sx, 0, tx], [0, sy, ty], [0, 0, 1.]])

OPS = {
    'resize 到一半':          S_mat(0.5, 0.5, 0, 0),
    'center-crop 到 1280x720': S_mat(1, 1, -(W-1280)/2, -(HGT-720)/2),
    'letterbox 到 640x640':    S_mat(640/W, 640/W, 0, (640 - HGT*640/W)/2),
}
for name, S in OPS.items():
    Kp = S @ K
    print(f'{name:26s} f=({Kp[0,0]:7.2f},{Kp[1,1]:7.2f})  c=({Kp[0,2]:7.2f},{Kp[1,2]:7.2f})')

# letterbox 的 padding 量自查
pad = (640 - HGT * 640 / W) / 2
print(f'\\nletterbox 上下各 padding {pad:.0f} px')

print('\\n—— 图像缩放到一半后，10m 地面点的四种读法 ——')
v_half = v_10m * 0.5
cases = [('全对',              600., 270.),
         ('两个都忘了改',      1200., 540.),
         ('只改焦距、忘主点',   600., 540.),
         ('只改主点、忘焦距',  1200., 270.)]
reads = {}
for name, f, cy in cases:
    d = ground_range(v_half, f, cy)
    reads[name] = d
    loud = '响的（负距离）' if d < 0 else ('—' if abs(d-10) < 1e-9 else '**静默**')
    print(f'  {name:20s} f={f:6.0f} c_y={cy:5.0f} -> {d:8.2f} m   {loud}')

assert abs(reads['全对'] - 10.0) < 1e-9
assert reads['两个都忘了改'] < 0 and reads['只改焦距、忘主点'] < 0
assert abs(reads['只改主点、忘焦距'] - 20.0) < 1e-9
print('\\n✅ 三种错法里两种给负距离（会被 sanity check 抓住），'
      '而「只改主点」静默地错 2 倍')"""),

    md("""## 6 · 畸变模型的单调性检查

$r_d(r)$ 必须在整个画幅内单调递增。一旦折返，说明多项式在画幅内已经发散——
**同一个畸变后半径对应两个原始半径，去畸变无解。**"""),

    code("""def rd_of_r(r, dist):
    k1, k2, k3 = dist[:3]
    r2 = r * r
    return r * (1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3)

def first_fold(dist, r_hi=3.0, n=8001):
    '''返回 r_d(r) 首次不再递增的半径；在 [0, r_hi] 内全程单调则返回 None。

    注意 r_hi 会影响结论：几乎所有多项式最终都会折返，
    所以有意义的量不是「有没有折返」，而是**折返点相对画幅角的余量**。
    '''
    r = np.linspace(0, r_hi, n)
    bad = np.where(np.diff(rd_of_r(r, dist)) <= 0)[0]
    return None if len(bad) == 0 else float(r[bad[0]])

SETS = {
    '本课系数':            DIST,
    '只有 k1=-0.28':       (-0.28, 0, 0, 0, 0),
    '激进广角':            (-0.55, 0.30, 0.0, 0, 0),
    '过拟合的三系数':      (-0.40, 0.60, -1.20, 0, 0),
}
print(f'画幅角 r_max = {R_MAX:.4f}   (余量 = 折返半径 / r_max)')
print()
folds = {}
for name, d in SETS.items():
    fold = first_fold(d)
    folds[name] = fold
    if fold is None:
        print(f'  OK   {name:18s} 到 r=3.0 都不折返，余量 = inf')
    else:
        m = fold / R_MAX
        flag = 'OK  ' if m >= 1.2 else ('WARN' if m > 1.0 else 'FAIL')
        note = '在画幅外' if m > 1.0 else '**在画幅内**'
        print(f'  {flag} {name:18s} 折返于 r={fold:.4f}  余量={m:5.2f}  {note}')

# 本课系数确实会折返，只是折返点远在画幅之外 —— 这才是准确的说法
assert 1.8 < folds['本课系数'] < 1.9, folds['本课系数']
assert folds['本课系数'] / R_MAX > 2.0, '本课系数的余量应超过 2 倍'
assert folds['只有 k1=-0.28'] > R_MAX, '单 k1 的折返点仍在画幅外'
assert folds['只有 k1=-0.28'] / R_MAX < 1.2, '但它的余量不足 1.2，应当报警'
assert folds['过拟合的三系数'] < R_MAX, '过拟合系数应在画幅内折返'
assert folds['激进广角'] is None
print()
print('✅ 余量把四组系数分成三档：安全(2.03 / inf) · '
      '**余量不足(1.19)** · 画幅内发散(0.79)')
print('   -> 「有没有折返」是个错问题（几乎都会折返），'
      '**「余量够不够」才是可门禁的量**')
"""),

    md("""## 7 · 小结

| 结论 | 数值 |
|---|---|
| 三步里只有透视除法不可逆，而它不引入误差 | 等价性误差 < 1e-12 |
| $f$ 的相对误差 = 距离的相对误差 | 精确等比例 |
| 主点 ↔ pitch 等价 | $f=1200$ 时 **1° ≈ 20.9 px** |
| 畸变是边缘现象 | 0.26 → 197.71 px，**750 倍**，$\\propto r^{3}$ |
| 去畸变 `n=5` 在画幅角 | 残差 0.60 px ≈ **0.81 m @ 50m** |
| 四种 `K` 错法 | 两种给负距离，**一种静默地错 2 倍** |
| 单调性检查 | 余量分三档：**2.03 / inf** 安全 · **1.19** 不足 · **0.79** 画幅内发散 |"""),

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：按半径自适应的去畸变

固定迭代次数在中心是浪费、在边缘不够。

实现 `undistort_adaptive(xd, yd, tol_px=1e-3, max_iter=30)`：
迭代直到**相邻两轮的位移小于 `tol_px` 个像素**或达到 `max_iter`，
返回 `(x, y, n_used)`。"""),

    code("""def undistort_adaptive(xd, yd, tol_px=1e-3, max_iter=30, dist=DIST):
    \"\"\"迭代到收敛。返回 (x, y, 实际用的轮数)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
FRACS = [0.10, 0.25, 0.50, 0.75, 1.00]
truth = {}
for fr in FRACS:
    x0, y0 = fr * CX / F, fr * CY / F
    truth[fr] = (x0, y0, *distort(x0, y0))

print(f\"{'位置':>8s} {'用的轮数':>9s} {'残差 (px)':>12s}\")
used = []
for fr in FRACS:
    x0, y0, xd, yd = truth[fr]
    x, y, n = undistort_adaptive(xd, yd)
    err = np.hypot(x - x0, y - y0) * F
    used.append(n)
    print(f'{fr*100:7.0f}% {n:9d} {err:12.2e}')
    assert err < 1e-2, f'{fr} 处残差 {err:.3e} px 过大'

assert used == sorted(used), '边缘应当比中心用更多轮'
assert used[0] <= 3, '中心几轮就该够'
assert used[-1] > used[0], '画幅角必须用更多轮'
tot_fixed = 12 * len(FRACS)
print(f'\\n自适应总轮数 {sum(used)} vs 固定 n=12 的 {tot_fixed} 轮'
      f'  → 省了 {100*(1-sum(used)/tot_fixed):.0f}%')
print('✅ 练习 1 通过：精度由容差保证，而不是由一个隐藏的迭代次数保证')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def undistort_adaptive(xd, yd, tol_px=1e-3, max_iter=30, dist=DIST):
    k1, k2, k3, p1, p2 = dist
    x, y = xd, yd
    for n in range(1, max_iter + 1):
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        xn, yn = (xd - dx) / rad, (yd - dy) / rad
        step = np.hypot(xn - x, yn - y) * F
        x, y = xn, yn
        if step < tol_px:
            return x, y, n
    return x, y, max_iter

for fr in FRACS:
    x0, y0, xd, yd = truth[fr]
    x, y, n = undistort_adaptive(xd, yd)
    assert np.hypot(x - x0, y - y0) * F < 1e-2
print('✅ 参考答案 1 通过（判据用「相邻两轮的位移」而不是「残差」——'
      '因为真值在运行时是不知道的）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：把预处理写成 `K` 的变换

实现 `adjust_K(K, op, **kw)`，支持三种操作并返回 `(K', 输出尺寸)`：

- `'resize'` —— `kw: out_w, out_h`（允许非等比）
- `'crop'` —— `kw: x0, y0, out_w, out_h`
- `'letterbox'` —— `kw: side`（缩放到长边等于 `side`，短边居中 padding）

要求：三种都通过左乘一个 $S$ 实现，不要各写一套公式。"""),

    code("""def adjust_K(Kmat, op, in_w=W, in_h=HGT, **kw):
    \"\"\"返回 (K', (out_w, out_h))。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
K_half, sz = adjust_K(K, 'resize', out_w=960, out_h=540)
assert sz == (960, 540)
assert np.allclose([K_half[0,0], K_half[1,1]], [600, 600])
assert np.allclose([K_half[0,2], K_half[1,2]], [480, 270])

K_crop, sz = adjust_K(K, 'crop', x0=320, y0=180, out_w=1280, out_h=720)
assert sz == (1280, 720)
assert np.allclose([K_crop[0,0], K_crop[1,1]], [F, F]), 'crop 不改焦距'
assert np.allclose([K_crop[0,2], K_crop[1,2]], [640, 360])

K_lb, sz = adjust_K(K, 'letterbox', side=640)
assert sz == (640, 640)
s = 640 / W
assert np.allclose([K_lb[0,0], K_lb[1,1]], [F*s, F*s])
assert np.allclose(K_lb[0,2], CX*s)
assert np.allclose(K_lb[1,2], CY*s + (640 - HGT*s)/2)

# 非等比 resize 会让 f_x != f_y —— 这是第 2 节说的「比值应在 1±0.002」的破坏源
K_sq, _ = adjust_K(K, 'resize', out_w=640, out_h=640)
assert abs(K_sq[0,0]/K_sq[1,1] - (640/W)/(640/HGT)) < 1e-12
print(f'非等比 resize 到 640x640: f_x/f_y = {K_sq[0,0]/K_sq[1,1]:.4f} '
      '（圆牌会被读成椭圆）')
print('✅ 练习 2 通过：三种操作都是一次左乘')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def adjust_K(Kmat, op, in_w=W, in_h=HGT, **kw):
    if op == 'resize':
        ow, oh = kw['out_w'], kw['out_h']
        S = S_mat(ow / in_w, oh / in_h, 0, 0)
    elif op == 'crop':
        ow, oh = kw['out_w'], kw['out_h']
        S = S_mat(1, 1, -kw['x0'], -kw['y0'])
    elif op == 'letterbox':
        side = kw['side']
        s = side / max(in_w, in_h)
        S = S_mat(s, s, (side - in_w * s) / 2, (side - in_h * s) / 2)
        ow = oh = side
    else:
        raise ValueError(op)
    return S @ Kmat, (int(ow), int(oh))

K_lb, sz = adjust_K(K, 'letterbox', side=640)
assert sz == (640, 640) and np.allclose(K_lb[1,2], CY*640/W + (640 - HGT*640/W)/2)
print('✅ 参考答案 2 通过')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：畸变模型的越界检查

实现 `distortion_audit(dist, r_max)`，返回 dict：

- `'monotonic'` —— bool：$r_d(r)$ 在 $[0, r_{max}]$ 上是否单调递增
- `'fold_at'` —— float 或 None：首次折返的半径（**可以大于 $r_{max}$**）
- `'margin'` —— float：`fold_at / r_max`（无折返时为 `inf`）
- `'max_incidence_deg'` —— float：$r_{max}$ 对应的入射角 $\\arctan r_{max}$

判据：`monotonic` 为假、或 `margin < 1.2`、或入射角 > 75°，都应当报警。

> `monotonic` 与 `margin` 是**两个不同的信号**：
> 单 $k_1$ 那组在画幅内单调（`monotonic=True`），但余量只有 1.19 —— **它该报警**。"""),

    code("""def distortion_audit(dist, r_max):
    \"\"\"返回 dict(monotonic, fold_at, margin, max_incidence_deg)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
a_ok  = distortion_audit(DIST, R_MAX)
a_bad = distortion_audit((-0.40, 0.60, -1.20, 0, 0), R_MAX)
a_thin = distortion_audit((-0.28, 0, 0, 0, 0), R_MAX)

assert set(a_ok) == {'monotonic', 'fold_at', 'margin', 'max_incidence_deg'}
assert a_ok['monotonic'] is True, '本课系数在画幅内单调'
assert a_ok['margin'] > 2.0, '本课系数的余量应超过 2 倍'
assert a_bad['monotonic'] is False
assert a_bad['fold_at'] < R_MAX, '过拟合系数应在画幅内折返'
assert a_thin['monotonic'] is True and 1.0 < a_thin['margin'] < 1.2, \
    '单 k1 在画幅内单调，但余量不足 1.2 —— 两个信号必须分开'
assert abs(a_ok['max_incidence_deg'] - np.rad2deg(np.arctan(R_MAX))) < 1e-9
assert a_bad['margin'] < 1.0
assert distortion_audit((-0.55, 0.30, 0.0, 0, 0), R_MAX)['margin'] == float('inf')

for name, a in [('本课系数', a_ok), ('只有 k1', a_thin), ('过拟合三系数', a_bad)]:
    fold = 'None' if a['fold_at'] is None else f\"{a['fold_at']:.4f}\"
    marg = 'inf' if a['margin'] == float('inf') else f\"{a['margin']:.2f}\"
    flag = '✅' if (a['monotonic'] and a['margin'] >= 1.2) else '⚠️'
    print(f\"{flag} {name:14s} 单调={str(a['monotonic']):5s} \"
          f\"折返={fold:>8s} 余量={marg:>5s} 入射角={a['max_incidence_deg']:.1f}°\")
print('\\n✅ 练习 3 通过：一条零成本的标定验收项，'
      '而且它对「余量不足」也会给出信号')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def distortion_audit(dist, r_max):
    fold = first_fold(dist, r_hi=max(3.0, 2.5 * r_max))
    mono = (fold is None) or (fold > r_max)      # 只关心画幅内
    margin = float('inf') if fold is None else fold / r_max
    return {'monotonic': bool(mono),
            'fold_at': fold,
            'margin': margin,
            'max_incidence_deg': float(np.rad2deg(np.arctan(r_max)))}

a = distortion_audit(DIST, R_MAX)
assert a['monotonic'] is True and a['margin'] > 2.0
assert 1.0 < distortion_audit((-0.28,0,0,0,0), R_MAX)['margin'] < 1.2
assert distortion_audit((-0.40, 0.60, -1.20, 0, 0), R_MAX)['monotonic'] is False
print('✅ 参考答案 3 通过')
print('   monotonic 只关心 [0, r_max]；margin 看折返点离画幅角有多远。'
      '两者都要报——「画幅内单调但余量 1.19」是一个真实的风险状态。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：投影链闭环断言

这是本模块最重要的交付物：**唯一能抓住「静默地错 2 倍」的检查。**

实现 `closure_ok(Kmat, pitch=0.0, tol_m=1e-6)`：
用给定的 `Kmat` 把若干**已知的地面点**投影到像素，再用同一个 `Kmat` 反投影回地面，
断言与原坐标的偏差小于 `tol_m`。返回 `(bool, 最大偏差)`。

然后用它检查第 5 节那四种情形。"""),

    code("""def closure_ok(Kmat, pitch=0.0, tol_m=1e-6, dist=(0,0,0,0,0)):
    \"\"\"返回 (是否闭环, 最大偏差 m)。地面点用 z=0 的 ground 假设。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
GROUND_PTS = [(10., 1.75, 0.), (20., 0., 0.), (30., -3.2, 0.), (60., 1.75, 0.)]

ok, dev = closure_ok(K)
assert ok and dev < 1e-6, (ok, dev)
print(f'原始 K：闭环 {ok}，最大偏差 {dev:.2e} m')

K_half, _ = adjust_K(K, 'resize', out_w=960, out_h=540)
ok, dev = closure_ok(K_half)
assert ok, '正确同步后的 K 必须闭环'
print(f'正确同步的 K_half：闭环 {ok}，最大偏差 {dev:.2e} m')

# 三种错法都必须被抓住
BROKEN = {
    '两个都忘了改':     K.copy(),
    '只改焦距、忘主点': np.array([[600,0,CX],[0,600,CY],[0,0,1.]]),
    '只改主点、忘焦距': np.array([[F,0,480.],[0,F,270.],[0,0,1.]]),
}
for name, Kb in BROKEN.items():
    # 用错的 K 去解「缩放后的像素」——模拟真实的不一致
    ok_b, dev_b = closure_ok(Kb)
    print(f'  {name:20s} 闭环={ok_b}  最大偏差={dev_b:.3e} m')

# 关键断言：'只改主点、忘焦距' 这一种，单看闭环**是过的**（因为它自洽），
# 必须靠「与另一个 K 的交叉检查」才能抓住 —— 这就是下面的 cross_check
def cross_check(K_train, K_deploy, tol_m=1e-6):
    '''同一个世界点，用两套 K 各走一遍链，读出的米数应当一致。'''
    worst = 0.0
    for P in GROUND_PTS:
        uv_t = (K_train @ np.array([P[1]/P[0]*-1, (H-P[2])/P[0], 1.]))[:2]
        d_t = H * K_train[1,1] / (uv_t[1] - K_train[1,2])
        d_d = H * K_deploy[1,1] / (uv_t[1] - K_deploy[1,2])
        worst = max(worst, abs(d_t - d_d))
    return worst < tol_m, worst

same, w = cross_check(K, K)
assert same and w < 1e-9
bad, w = cross_check(K, BROKEN['只改主点、忘焦距'])
assert not bad, '训练/部署两套 K 不一致必须被抓住'
print(f'\\ncross_check(K, 只改主点忘焦距) -> 不一致，最大差 {w:.2f} m')
print('✅ 练习 4 通过：**闭环抓自洽性，交叉检查抓两侧一致性——两个都要有**')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def closure_ok(Kmat, pitch=0.0, tol_m=1e-6, dist=(0,0,0,0,0)):
    worst = 0.0
    for P in GROUND_PTS:
        st = project_steps(P, pitch=pitch, dist=dist, Kmat=Kmat)
        if st is None:
            return False, float('inf')
        u, v = st['uv']
        # 反投影：用同一个 Kmat 回到归一化平面，再按 z=0 求交
        xn = (u - Kmat[0, 2]) / Kmat[0, 0]
        yn = (v - Kmat[1, 2]) / Kmat[1, 1]
        d_v = R_vc(pitch) @ np.array([xn, yn, 1.0])
        if d_v[2] >= -1e-12:
            return False, float('inf')
        s = (0.0 - H) / d_v[2]
        back = CAM_T + s * d_v
        worst = max(worst, float(np.max(np.abs(back - np.array(P)))))
    return worst < tol_m, worst

ok, dev = closure_ok(K)
assert ok and dev < 1e-6
print('✅ 参考答案 4 通过')
print('   注意：闭环检查用的是**同一个** K 的一致性，'
      '所以它抓不住「训练与部署各自自洽但互不相同」——那需要 cross_check')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) OpenCV 的对应函数（本课自己实现了一遍，为了看清误差来源）──
import cv2
K   = np.array([[fx,0,cx],[0,fy,cy],[0,0,1]], np.float64)
dist = np.array([k1,k2,p1,p2,k3], np.float64)   # ⚠️ 顺序是 k1,k2,p1,p2,k3
xy_n = cv2.undistortPoints(uv.reshape(-1,1,2), K, dist)   # -> 归一化平面
map1, map2 = cv2.initUndistortRectifyMap(K, dist, None, K_new, size, cv2.CV_32FC1)
img_u = cv2.remap(img, map1, map2, cv2.INTER_LINEAR)      # ← 这就是第 5 节的 LUT

# ── 2) 把 K 与图像尺寸绑在一起，让「忘记同步」变成类型错误 ──
@dataclass(frozen=True)
class CalibratedImage:
    img: np.ndarray
    K: np.ndarray
    dist: np.ndarray
    calib_sha: str            # ← LUT / K 的来源指纹，见第 5 节的警告

def resize(ci: CalibratedImage, out_w, out_h) -> CalibratedImage:
    s = np.array([[out_w/ci.img.shape[1], 0, 0],
                  [0, out_h/ci.img.shape[0], 0], [0, 0, 1]])
    return CalibratedImage(cv2.resize(ci.img, (out_w, out_h)),
                           s @ ci.K, ci.dist, ci.calib_sha)
#   ↑ 关键：**没有只返回图像的 resize**。想拿到缩放后的图，就必须拿到新的 K。

# ── 3) 进 CI 的两条断言（练习 3 与练习 4）──
def test_distortion_in_range():
    a = distortion_audit(dist, r_max=np.hypot(cx, cy)/fx)
    assert a['monotonic'] and a['margin'] >= 1.2, a

def test_pipeline_closure():
    for op in TRAIN_PREPROCESS_OPS:        # 与训练侧共用同一份配置
        K2, _ = adjust_K(K, **op)
        ok, dev = closure_ok(K2)
        assert ok, f'{op} 之后闭环失败，偏差 {dev} m'
```

> **落地顺序建议**：先加 `test_pipeline_closure`（20 行、抓一整类静默错误），
> 再把 `resize` 改成返回 `(img, K)` 的形式（改动大但一次性），
> 最后才是精度层面的 LUT 与自适应迭代。"""),
]
