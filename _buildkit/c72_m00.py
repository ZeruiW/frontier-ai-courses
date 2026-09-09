# -*- coding: utf-8 -*-
"""C72 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "线性代数（矩阵乘法、最小二乘、SVD 会用就行）；"
                 "读过 C18 模块 01（卷积与感受野）更好但不必需；"
                 "<strong>本课不需要 GPU、不需要真实数据集、不训练任何网络</strong>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（造一个可控的合成路口：相机 + 地面 + 三块标志 / '
                       '把一条完整的投影链跑通并反投影回去 / '
                       '精确推出并穷举验证 <code>d_read = d·H/(H−z)</code> / '
                       '把「1° 外参误差」换算成「多少个像素的定位误差」）'),
    ("核心参考", "Hartley &amp; Zisserman, <em>Multiple View Geometry in Computer Vision</em>"
                 "（2nd ed., 2004）· Zhang, <em>A Flexible New Technique for Camera "
                 "Calibration</em>（TPAMI 2000）· "
                 "本课程 C55 模块 04（单相机时序融合）· C57（小目标与尺度）· "
                 "C59 模块 03（感知接口与 BEV 的上游）· C60（车端部署一致性）"),
    ("预计时长", "读 45 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("geometry-is-a-chain", "几何不是预处理，是一条误差链", "".join([
        P("检测课教的是「框在哪一格像素上」。"
          "而下游要的从来不是像素——是<strong>米</strong>："
          "那块限速牌离我多远、在我车道里还是隔壁车道、"
          "上一帧那块和这一帧这块是不是同一块。"
          "<strong>从像素到米，中间是一条有五个坐标系、每一环都会引入误差的链。"
          "这门课的全部内容就是：把每一环的误差精确换算成米。</strong>"),
        ASCII("""
   一条完整的链（本课的骨架）

   像素 (u,v)  ──①──►  归一化相机坐标  ──②──►  相机坐标 (X,Y,Z)
                 内参 K                   需要深度或一个假设
                 + 畸变                    ← 这一步是链上唯一「信息不够」的地方
                    │                              │
                    │                              ▼
                    │                       车体坐标 ──③──► 世界/BEV
                    │                          外参 R,t         + 自车位姿
                    │                              │
                 模块 01                        模块 02/04       模块 05
                 (相机模型)                     (标定/投影)      (时空对齐)

   每一环的误差都能换算成米：
     ① 畸变没去              → 画幅角 197.7 px 的位移（模块 01 第 4 节）
     ①' 内参没随缩放改       → **静默地报 2 倍距离**（模块 01 第 7 节）
     ② 用错了深度假设         → **成倍**的距离误差（下一节，本课中心结论）
     ③ 外参俯仰角错 1°        → 50m 处 −18m / +70m（模块 02 第 5 节）
     ⑤ 时间戳错 33ms @120km/h → 1.10m（模块 05 第 2 节）
        """),
        DUAL(
            "这条链的关键性质是 <strong>它不对称</strong>："
            "<strong>正向（三维 → 像素）总是唯一确定的，"
            "而反向（像素 → 三维）永远缺一个自由度</strong>。"
            "一个像素对应的是一条射线，不是一个点。"
            "<em>所以「反投影」这个词其实是个陷阱——"
            "你每次做反投影，都在偷偷用一个假设把那个自由度补上</em>，"
            "而这门课一半的内容是在讲：那些假设分别是什么、什么时候崩。",
            "<strong>补上那个自由度的办法只有四种，本课各占一个模块</strong>："
            "① 用<strong>另一个视角</strong>（三角测量，模块 03）；"
            "② 用<strong>一个平面假设</strong>（单应 / IPM，模块 04）；"
            "③ 用<strong>物体的已知尺寸</strong>（标志的物理边长，模块 03 第 6 节）；"
            "④ 用<strong>另一个传感器</strong>（模块 04 第 5 节）。"
            "<em>把它们记成「四种补法」比记公式有用得多——"
            "因为工程里的争论几乎总是「这里该用哪一种补法」</em>。",
        ),
        CALLOUT("intuition",
                "一句话概括本课的方法论："
                "<strong>几何错误不会报错，它只会安静地给出一个错误的米数。</strong>"
                "检测漏检你能在 recall 上看到；"
                "而标定错了 1°、时间戳错了 30ms、"
                "把地面假设用在了一块悬空的标志上——"
                "这些都不会让任何指标变成 NaN，"
                "<em>它们只会让下游的规控在一个错误的位置上做正确的决策</em>。"
                "所以这一层必须靠<strong>可计算的误差预算</strong>来守，"
                "而不是靠看图。"),
    ])),

    # ============================================================== 2
    ("center-result", "本课的中心结论：地面 IPM 对交通标志不适用", "".join([
        P("先把结论摆出来，因为它决定了后面五个模块的组织方式。"
          "<strong>BEV 感知里最常用的一步是「逆透视变换」（IPM）："
          "假设看到的点在地面上（<code>z=0</code>），"
          "于是一个像素唯一对应地面上一个点。</strong>"
          "它对车道线、路面箭头、可行驶区域都很好用。"
          "而<strong>交通标志装在 1.5–3 m 高——"
          "它恰好是这个假设最不成立的一类目标</strong>。"),
        P("代价可以精确算出来。设相机高 $H$、目标真实纵向距离 $d$、目标离地高度 $z$，"
          "用地面假设读出的距离是："),
        MATH(r"d_{\text{read}} = d\cdot\frac{H}{H-z}"),
        P("推导只有两行：目标点相对相机的俯角是 "
          "$\\theta=\\arctan\\frac{H-z}{d}$；"
          "地面假设把同一条射线按 $z=0$ 求交，得到 "
          "$d_{\\text{read}}=H/\\tan\\theta = dH/(H-z)$。"
          "<strong>notebook 第 4 节把它与逐点穷举的数值结果对齐到相对偏差 $2\\times10^{-13}$</strong>（<em>这里必须用相对偏差——$z=1.49$ 时读出值到 18000 m，浮点绝对误差可达 $4\\times10^{-9}$，绝对容差是错的量纲</em>）。"),
        TABLE(["推论", "式子", "它意味着什么"], [
            ["<strong>相对误差与距离无关</strong>",
             "$\\dfrac{d_{\\text{read}}-d}{d}=\\dfrac{z}{H-z}$",
             "<strong>这是最反直觉的一条</strong>："
             "误差不会「远处才严重」——"
             "$H=1.5,z=1$ 时，10m 读成 30m、50m 读成 150m，"
             "<strong>永远是 3 倍</strong>。"
             "<em>所以「近处先上线、远处以后再修」这个常见计划在这里是无效的</em>。"],
            ["<strong>$z=H$ 时发散</strong>", "$d_{\\text{read}}\\to\\infty$",
             "目标正好在相机光心高度时，射线与地面平行。"
             "而<strong>乘用车相机高度就是 1.2–1.5 m</strong>。"],
            ["<strong>$z>H$ 时无解</strong>", "射线在地平线以上",
             "<strong>这是最常见的实际情形</strong>："
             "限速牌中心通常离地 2–2.5 m，高于相机。"
             "此时 IPM 不是「误差大」，而是<strong>根本没有交点</strong>——"
             "代码里表现为负数、`inf`、或者被一个 `clip` 静默吃掉。"],
            ["<strong>只由高度比决定</strong>", "与 $f$、图像分辨率无关",
             "换更高分辨率的相机、换更好的检测器，"
             "<strong>这个误差一点都不会变小</strong>。"],
        ]),
        DUAL(
            "<strong>这条结论的工程含义是：给标志估距离，必须换一种补法。</strong>"
            "notebook 第 5 节把三种可行做法各跑一遍并比较——"
            "用标志的<strong>已知物理边长</strong>（法规规定的，模块 03 第 6 节）、"
            "用<strong>双目/多目三角测量</strong>（模块 03）、"
            "或者<strong>估计每个目标自己的高度</strong>（等价于承认 IPM 不够用）。"
            "<em>而第一种在 TSR 里往往最实用，因为标志尺寸是被法规钉死的</em>。",
            "<strong>反过来说，这条结论也解释了一个常见的困惑</strong>："
            "为什么同一套 BEV 管线在车道线上表现很好、"
            "在标志上「距离总是偏大」。"
            "<em>因为它不是精度问题，是假设问题</em>——"
            "$z/(H-z)$ 这个量里没有任何可以靠调参改善的东西。"
            "<strong>本课的态度是：先把假设写出来，再谈精度。</strong>"
            "而模块 04 第 2 节会给出一张「地面假设何时崩」的清单"
            "（坡道、悬挂标志、路肩、减速带），"
            "每一项都配一个换算成米的代价。",
        ),
    ])),

    # ============================================================== 3
    ("map", "课程地图", "".join([
        P("五个内容模块沿着上一节那条链走，"
          "<strong>每个模块结束时你手里都多一个「把误差换算成米」的工具</strong>。"),
        TABLE(["模块", "主题", "带走的那个可计算的量"], [
            ["<strong>01</strong>", "相机模型与畸变",
             "<strong>去畸变前后的像素位移</strong>：10% 对角处 0.26 px vs 画幅角 197.7 px——"
             "<strong>畸变是纯边缘现象（约 750 倍差距）</strong>，"
             "<em>而标志恰好常出现在画幅边缘</em>；"
             "另一条：<strong>resize 后只改主点、忘改焦距 → 静默地报 2 倍距离</strong>"],
            ["<strong>02</strong>", "标定：内参、外参与验收",
             "<strong>重投影误差</strong>（唯一的验收指标）；"
             "以及 <strong>1° 外参误差 = 24–52 个像素的定位误差</strong>"],
            ["<strong>03</strong>", "多视角几何：对极、单应、三角测量、PnP",
             "<strong>深度误差 $\\propto Z^2/(Bf)$</strong>："
             "0.5 px 视差误差在 10m 是 0.8%、80m 是 6.7%"],
            ["<strong>04</strong>", "BEV 投影与多相机融合",
             "<strong>地面假设的破坏代价</strong>（上一节的公式）；"
             "重叠区一致性作为无真值的自检"],
            ["<strong>05</strong>", "时空对齐与跨镜关联",
             "<strong>时间戳误差 × 车速 = 米</strong>："
             "33 ms @ 120 km/h = 1.10 m；rolling shutter 20 ms = 0.67 m"],
        ]),
        CALLOUT("warn",
                "<strong>顺序是有依赖的，不建议跳。</strong>"
                "模块 04 的 IPM 是模块 01 的反投影加一个平面假设；"
                "模块 03 的三角测量需要模块 02 的外参；"
                "模块 05 的运动补偿需要模块 04 的车体坐标系。"
                "<em>唯一可以先跳读的是模块 03 第 4 节（PnP），"
                "它相对独立。</em>"),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工", "".join([
        P("这门课是<strong>纯几何、无学习</strong>的那一半。"
          "全库里跟三维有关的内容此前散落在几门课的单个小节里，"
          "<strong>而「相机怎么投影、外参怎么标、多路怎么对齐」这条链整体零覆盖</strong>——"
          "这门课补的就是它。"),
        TABLE(["相关课程", "它讲什么", "分工"], [
            ["<strong>C55</strong> · TSR 与自动驾驶感知",
             "模块 04 是<strong>单相机时序融合</strong>："
             "ByteTrack 两阶段关联、卡尔曼、贝叶斯 log-odds 累积、"
             "迟滞双阈值、生命周期状态机",
             "<strong>C55-04 管「同一路相机的时间轴」，本课模块 05 管「多路之间的时空对齐」</strong>。"
             "<em>两者的交界是「时间戳」：C55 假设它是对的，本课量它错了会怎样。</em>"],
            ["<strong>C57</strong> · 小目标检测",
             "IoU 的尺度敏感性、多尺度架构、NWD、切片推理",
             "C57 管<strong>像素域</strong>的尺度问题；"
             "本课管<strong>米域</strong>的尺度问题。"
             "<em>「远处标志只有 12 px」是 C57；"
             "「12 px 对应的距离不确定度是 ±2m」是本课模块 03。</em>"],
            ["<strong>C59</strong> · VLA 与感知接口",
             "模块 03 把 BEV 当作<strong>感知接口的上游</strong>来讲"
             "（全库 BEV 提及最集中的地方，14 次）",
             "C59 讲「BEV 这个接口该长什么样」；"
             "<strong>本课讲「BEV 这张图是怎么算出来的、以及它什么时候是错的」</strong>。"],
            ["<strong>C60</strong> · 车端部署一致性",
             "预处理对齐、TensorRT、INT8 校准、后处理与 C++",
             "C60 管<strong>数值一致性</strong>（训练与部署的同一张图要给同一个数）；"
             "本课管<strong>几何一致性</strong>（同一个世界点在多路里要给同一个米数）。"],
            ["<strong>C18</strong> · 计算机视觉",
             "检测、分割、自监督；`SLAM` 全库仅 1 次提及、"
             "`深度估计` 2 次",
             "本课不重复 C18 的任何网络结构。"
             "<strong>本课全程不训练任何东西。</strong>"],
            ["<strong>C73/C74/C75</strong> · 3D 方向（同批新课，在本课之后）",
             "点云与体素表示、3D 高斯溅泼、三维重建与生成",
             "<strong>本课是它们三门的共同前提</strong>："
             "投影、标定、位姿这套语言在那三门里会被反复使用而不再重讲。"
             "<em>分界线是「有没有学习成分」：本课没有，那三门有。</em>"],
        ]),
        CALLOUT("paper",
                "<strong>一句话划清边界：</strong>"
                "本课不碰 <strong>C11</strong>（检索）、<strong>C19</strong>（贝叶斯滤波的理论）、"
                "<strong>C41</strong>（世界模型），"
                "也不讲 SLAM 的建图与回环——"
                "<em>那是一门独立的课，而本课只用到 SLAM 里「位姿」这一个概念</em>"
                "（模块 05 第 3 节，且只用它的输出不讲它的求解）。"),
    ])),

    # ============================================================== 5
    ("method", "方法论：为什么用合成场景而不是真实数据", "".join([
        P("本课 notebook 里的所有场景都是<strong>自己造的</strong>："
          "一条直路、一个地平面、三块装在不同高度的标志、一到三台相机。"
          "<strong>这不是为了省事——是因为学几何时，合成数据严格优于真实数据。</strong>"),
        DUAL(
            "<strong>理由只有一个：真值。</strong>"
            "几何这一层要回答的问题全都是「误差有多大」，"
            "而<strong>真实数据集里没有一个字段告诉你「这块标志离地 2.13 m」</strong>。"
            "于是你只能比较两个都可能错的东西。"
            "<em>合成场景里我知道每个点的三维坐标、每台相机的精确内外参、"
            "每一帧的精确时间戳——"
            "所以我可以问「把外参故意拧错 1°，读出的米数变了多少」"
            "并得到一个可断言的答案</em>。",
            "<strong>代价也要说清楚，它有两条。</strong>"
            "① 合成场景里<strong>没有真实的噪声结构</strong>："
            "真实的角点检测误差不是独立高斯的，"
            "而这会让「重投影误差 0.3 px」这个数在真实标定里更难达到。"
            "② <strong>没有真实的畸变</strong>："
            "本课用标准的 Brown–Conrady 多项式模型，"
            "而<em>广角/鱼眼镜头在画幅角上会超出这个模型的表达能力</em>"
            "（模块 01 第 6 节给出判别方法与替代模型）。"
            "<strong>所以本课的相对结论可迁移，具体像素数只属于本课的合成配置。</strong>",
        ),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：机制 → 可计算的误差 → 怎么变成一条验收项",
            "<strong>notebook</strong>：6–8 个 worked 小节，每节以 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接 OpenCV / ROS TF / 标定板流程的代码",
        ]),
        CALLOUT("intuition",
                "<strong>一条贯穿全课的纪律</strong>："
                "每次做反投影，<strong>先把用到的假设写成一行注释</strong>。"
                "本课的代码里所有反投影函数都强制传一个 "
                "<code>assumption=</code> 参数（`'ground'` / `'known_height'` / "
                "`'stereo'` / `'known_size'`），"
                "<em>因为把假设变成一个必填参数，是让它不被忘记的最便宜的办法</em>。"),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        P("纯 <code>numpy</code>，CPU，断网可跑。不需要 OpenCV——"
          "<strong>本课要自己写投影、去畸变、DLT、三角测量</strong>，"
          "因为「调 <code>cv2.undistortPoints</code>」学不到误差从哪来。"),
        CODE("""cd C72_MultiView_Geometry_Course
pip install -r requirements.txt      # 只有 numpy 与 jupyter
jupyter lab 00_setup/00_environment_check.ipynb""", "bash"),
        TABLE(["模块", "notebook", "本模块的 4 道练习在做什么"], [
            ["00", "<code>00_environment_check.ipynb</code>",
             "投影链闭环 · 中心公式 · 1° 换算成像素 · 假设必填参数"],
            ["01", "<code>01_camera_model.ipynb</code>",
             "去畸变的迭代解 · 内参改变什么 · 裁剪与缩放后的 K · 边缘误差预算"],
            ["02", "<code>02_calibration.ipynb</code>",
             "DLT 求内参 · 退化配置检测 · 重投影误差的分位数 · 外参扰动实验"],
            ["03", "<code>03_multiview.ipynb</code>",
             "本质矩阵与对极线 · 三角测量与基线 · PnP · 已知尺寸测距"],
            ["04", "<code>04_bev_fusion.ipynb</code>",
             "IPM 与地面假设破坏 · 多相机拼接 · 重叠区一致性 · 融合层级选择"],
            ["05", "<code>05_spatiotemporal.ipynb</code>",
             "时间戳插值 · 运动补偿 · rolling shutter · 跨镜关联的几何门"],
        ]),
        P("<strong>如果只有两个小时</strong>：读本页 + 模块 04 第 2 节（地面假设清单），"
          "跑 00 和 04 的 notebook。"
          "<em>这条最短路径覆盖了本课最容易在生产里咬人的那一类错误。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 00 · 环境自检与一条完整的投影链

这个 notebook 做三件事：

1. **造一个可控的合成路口** —— 一个地平面、三块装在不同高度的标志、一台前视相机。
   每个点的三维真值我都知道，所以每个误差都能被断言。
2. **把投影链正反跑通**，并且把「反投影用了什么假设」做成一个**必填参数**。
3. **推出并穷举验证本课的中心公式** $d_{\\text{read}} = d\\cdot H/(H-z)$，
   然后把「1° 外参误差」换算成「多少个像素的定位误差」。

> 心智模型：**正向投影唯一确定，反向投影永远缺一个自由度。
> 你每次反投影，都在用一个假设补那个自由度——而这门课讲的是那些假设什么时候崩。**"""),

    md("""## 0 · 环境与坐标系约定

坐标系约定是几何代码里第一大 bug 来源，所以先钉死，全课不变：

| 坐标系 | 约定 | 说明 |
|---|---|---|
| 车体 | **X 前 · Y 左 · Z 上** | ROS REP-103，自动驾驶栈的事实标准 |
| 相机 | **x 右 · y 下 · z 光轴向前** | 计算机视觉标准（OpenCV 同款） |
| 图像 | `u` 向右 · `v` 向下 · 原点左上 | 像素 |

**注意车体的 Y 是「左」而相机的 x 是「右」——这两个约定天生反向**，
所以旋转矩阵第一列是 `(0,-1,0)`。忘掉这个符号会得到一个左右镜像的世界，
而它在正前方的目标上**看不出来**。"""),

    code("""import numpy as np
import itertools

print('numpy', np.__version__)
print('本课全程 CPU / 断网 / 不训练任何网络 / 不依赖 OpenCV')

# ── 相机与场景的物理参数（全课通用）──
H  = 1.5       # 相机离地高度 (m)
F  = 1200.0    # 焦距 (px)
W, HGT = 1920, 1080
CX, CY = W / 2, HGT / 2

K = np.array([[F, 0, CX],
              [0, F, CY],
              [0, 0,  1]])

def R_vc(pitch_deg=0.0):
    \"\"\"车体(X前,Y左,Z上) ← 相机(x右,y下,z前) 的旋转矩阵。pitch>0 表示低头。

    列 = 相机三个轴在车体坐标里的方向：
      x_c(图像右)  = (0, -1, 0)            ← 图像右 = 车体右 = -Y
      y_c(图像下)  = (-sinθ, 0, -cosθ)
      z_c(光轴)    = ( cosθ, 0, -sinθ)
    \"\"\"
    t = np.deg2rad(pitch_deg)
    return np.array([[0., -np.sin(t),  np.cos(t)],
                     [-1.,        0.,        0.],
                     [0., -np.cos(t), -np.sin(t)]])

CAM_T = np.array([0., 0., H])   # 相机光心在车体坐标里的位置

# 右手性自检：三个轴必须构成右手系，否则世界会被左右镜像
for p in [0.0, 1.0, -3.0, 12.0]:
    assert abs(np.linalg.det(R_vc(p)) - 1.0) < 1e-12, 'R 必须是旋转矩阵(det=+1)'
    assert np.allclose(R_vc(p) @ R_vc(p).T, np.eye(3), atol=1e-12)
print('✅ 旋转矩阵在各 pitch 下都是正交且 det=+1')"""),

    md("""## 1 · 一个合成路口

地面上一排车道标记（`z=0`），加三块**装在不同高度**的标志。
高度取值不是随便挑的：**限速牌牌面中心通常离地 2.0–2.5 m，
而乘用车前视相机在 1.2–1.5 m** —— 这个高度关系是本课中心结论的全部来源。"""),

    code("""SCENE = {
    # 名字: (X前, Y左, Z上)  —— 单位 m
    'lane_10m':   (10.0,  1.75, 0.00),   # 车道线上的一个标记点
    'lane_30m':   (30.0,  1.75, 0.00),
    'lane_60m':   (60.0,  1.75, 0.00),
    'arrow_20m':  (20.0,  0.00, 0.00),   # 路面箭头
    'sign_low':   (30.0, -3.20, 1.00),   # 一块很低的牌（施工牌）
    'sign_speed': (30.0, -3.20, 2.20),   # 限速牌：**高于相机**
    'sign_gantry':(30.0,  0.00, 5.50),   # 龙门架上的悬挂标志
}

def project(P_v, pitch=0.0):
    \"\"\"车体坐标点 -> 像素。返回 None 表示在相机后方。\"\"\"
    P_c = R_vc(pitch).T @ (np.asarray(P_v, float) - CAM_T)
    if P_c[2] <= 1e-9:
        return None
    return np.array([CX + F * P_c[0] / P_c[2],
                     CY + F * P_c[1] / P_c[2]])

print(f\"{'目标':12s} {'真值 (X,Y,Z)':>22s} {'像素 (u,v)':>18s}  位置\")
for name, P in SCENE.items():
    uv = project(P)
    where = '地平线以上' if uv[1] < CY else '地平线以下'
    print(f'{name:12s} {str(tuple(P)):>22s}  ({uv[0]:7.1f},{uv[1]:7.1f})  {where}')

# 地面点必然成像在地平线（v=CY）**以下**；高于相机的点必然在**以上**
for name, P in SCENE.items():
    v = project(P)[1]
    if P[2] < H:  assert v > CY, f'{name} 低于相机 -> 应在地平线以下'
    if P[2] > H:  assert v < CY, f'{name} 高于相机 -> 应在地平线以上'
print('\\n✅ 地平线把场景分成两半：低于相机高度的在下，高于的在上')"""),

    md("""## 2 · 反投影：把「假设」做成必填参数

一个像素对应**一条射线**，不是一个点。要落到三维必须补一个自由度，
而补法只有四种。**本课所有反投影函数都强制传 `assumption=`** ——
把假设变成必填参数，是让它不被忘记的最便宜的办法。"""),

    code("""def backproject(uv, assumption, pitch=0.0, z=None, size_px=None, size_m=None):
    \"\"\"像素 -> 车体坐标。assumption 必填，取值：

      'ground'        : 假设目标在 z=0 的地面上
      'known_height'  : 已知目标离地高度 z（需要 z=）
      'known_size'    : 已知目标物理尺寸与像素尺寸（需要 size_px=, size_m=）
    \"\"\"
    d_c = np.array([(uv[0] - CX) / F, (uv[1] - CY) / F, 1.0])
    d_v = R_vc(pitch) @ d_c                      # 射线方向（车体坐标）

    if assumption in ('ground', 'known_height'):
        plane_z = 0.0 if assumption == 'ground' else float(z)
        # 求射线与平面 Z=plane_z 的交点： CAM_T[2] + s*d_v[2] = plane_z
        denom = d_v[2]
        if abs(denom) < 1e-12 or (H - plane_z) / denom > 0:
            return None                          # 平行或朝错方向 -> 无交点
        s = (plane_z - H) / denom
        return CAM_T + s * d_v

    if assumption == 'known_size':
        # 相似三角形：真实边长 / 像素边长 = 深度 / 焦距
        depth = F * float(size_m) / float(size_px)
        return CAM_T + (depth / d_v[0]) * d_v if abs(d_v[0]) > 1e-12 else None

    raise ValueError(f'未知假设 {assumption!r} —— 假设必须显式写出来')

# 闭环：地面点用 ground 假设，必须精确回到原处
for name in ['lane_10m', 'lane_30m', 'lane_60m', 'arrow_20m']:
    P = np.array(SCENE[name]); back = backproject(project(P), 'ground')
    assert np.allclose(back, P, atol=1e-9), (name, back, P)
print('✅ 地面点闭环精确（误差 < 1e-9 m）—— 因为假设与真相一致')

# 而高于相机的标志，ground 假设直接**无解**
for name in ['sign_speed', 'sign_gantry']:
    assert backproject(project(SCENE[name]), 'ground') is None
print('✅ 高于相机的标志：ground 假设返回 None，不是「误差大」而是**没有交点**')

# 换成正确的假设就精确了
P = np.array(SCENE['sign_speed'])
back = backproject(project(P), 'known_height', z=P[2])
assert np.allclose(back, P, atol=1e-9)
print('✅ 同一个像素 + 正确的高度假设 -> 精确复原', np.round(back, 6))"""),

    md("""## 3 · 中心公式：地面假设被破坏时读出什么

设相机高 $H$、目标真实纵向距离 $d$、目标离地 $z$。
目标点相对相机的俯角是 $\\theta=\\arctan\\frac{H-z}{d}$；
地面假设沿同一条射线求 $z=0$ 的交点，得到

$$d_{\\text{read}} = \\frac{H}{\\tan\\theta} = d\\cdot\\frac{H}{H-z}$$

下面用逐点数值穷举来验证它。"""),

    code("""def ipm_read_formula(d, z, h=H):
    \"\"\"地面假设读出的纵向距离。z>=h 时无解，返回 inf。\"\"\"
    if z >= h:
        return np.inf
    return d * h / (h - z)

max_dev = 0.0
rows = []
for d in [8, 10, 20, 30, 50, 80, 120]:
    for z in [0.0, 0.3, 0.8, 1.0, 1.2, 1.4, 1.49]:
        bp = backproject(project((d, 0.0, z)), 'ground')
        num = np.inf if bp is None else bp[0]
        pred = ipm_read_formula(d, z)
        if np.isfinite(num) and np.isfinite(pred):
            max_dev = max(max_dev, abs(num - pred) / pred)   # **相对**偏差
        rows.append((d, z, num, pred))

print(f'穷举 {len(rows)} 组 (d,z)，公式与数值的最大**相对**偏差 = {max_dev:.3e}')
assert max_dev < 1e-12, '公式必须与逐点数值一致'
# 注意这里必须用相对偏差：z=1.49 时 d_read 到 18000 m，
# 浮点绝对误差可达 4e-9，而相对误差只有 2e-13——**绝对容差在这里是错的量纲**

print(f\"\\n{'d 真':>6s} {'z':>5s} {'数值读出':>11s} {'公式':>11s}\")
for d, z, num, pred in rows:
    if d in (10, 50) and z in (0.0, 0.3, 1.0, 1.4):
        print(f'{d:6d} {z:5.1f} {num:11.4f} {pred:11.4f}')

# z >= H 无解
for z in [1.5, 2.2, 5.5]:
    assert backproject(project((30.0, 0.0, z)), 'ground') is None
    assert ipm_read_formula(30.0, z) == np.inf
print('\\n✅ 公式与数值一致，且 z >= H 时两者都给「无解」')"""),

    md("""## 4 · 最反直觉的一条推论：相对误差与距离无关

把公式整理一下：

$$\\frac{d_{\\text{read}}-d}{d}=\\frac{z}{H-z}$$

**右边完全不含 $d$。** 所以这个误差不是「远处才严重」——
它在每个距离上都是同一个倍数。
这直接否掉了一个很常见的上线计划：「先做近处，远处以后再修」。"""),

    code("""print(f\"{'z (m)':>6s} {'相对误差':>10s}   \" + ''.join(f'{d}m 读出'.rjust(12) for d in [10,30,50,100]))
for z in [0.0, 0.3, 0.5, 1.0, 1.2, 1.4]:
    rel = z / (H - z)
    reads = [ipm_read_formula(d, z) for d in [10, 30, 50, 100]]
    print(f'{z:6.1f} {rel*100:9.1f}%   ' + ''.join(f'{r:12.2f}' for r in reads))

# 断言：同一个 z 下，各距离的**倍数**完全相同
for z in [0.3, 0.8, 1.0, 1.4]:
    ratios = [ipm_read_formula(d, z) / d for d in [8, 10, 30, 50, 100, 200]]
    assert max(ratios) - min(ratios) < 1e-12, '倍数必须与距离无关'
    assert abs(ratios[0] - H / (H - z)) < 1e-12
print('\\n✅ 倍数 = H/(H−z)，与距离无关（各距离间差异 < 1e-12）')

# 横向也被同一个倍数缩放
P = (30.0, 2.0, 1.0)
bp = backproject(project(P), 'ground')
k = H / (H - P[2])
assert abs(bp[0] - P[0]*k) < 1e-9 and abs(bp[1] - P[1]*k) < 1e-9
print(f'✅ 横向同样被放大 {k:.1f} 倍：真 Y={P[1]} -> 读出 Y={bp[1]:.2f}'
      '  → **整个 BEV 图被径向拉伸，而不是平移**')"""),

    md("""## 5 · 把「1° 外参误差」换算成「多少个像素」

标定误差和检测误差最终都变成米。放到同一把尺子上比，才知道该投入哪一边。"""),

    code("""print(f\"{'距离':>6s} {'1px 定位误差':>14s} {'1° 俯仰误差':>14s} {'1° 相当于':>12s}\")
budget = []
for d in [10, 20, 30, 50, 80]:
    uv = project((d, 0.0, 0.0))
    d0 = backproject(uv, 'ground')[0]
    e_px = abs(backproject(uv + np.array([0.0, 1.0]), 'ground')[0] - d0)
    cands = []
    for sign in (+1.0, -1.0):
        bp = backproject(uv, 'ground', pitch=sign * 1.0)
        cands.append(abs((np.inf if bp is None else bp[0]) - d0))
    e_deg = max(cands)
    budget.append((d, e_px, e_deg))
    print(f'{d:5d}m {e_px:13.3f}m {e_deg:13.2f}m {e_deg/e_px:11.1f} px')

# 两个结论都要成立
assert all(e_deg / e_px > 20 for _, e_px, e_deg in budget), '1° 应远大于 1px'
ratios = [e_deg / e_px for _, e_px, e_deg in budget]
assert ratios == sorted(ratios), '比值应随距离单调上升'
print('\\n✅ 1° 外参误差相当于 24–52 个像素的定位误差，且比值随距离上升')
print('   → **标定的收益远大于同等工程量投在检测器定位精度上**')

# 误差是不对称的：抬头和低头不一样
uv = project((50.0, 0.0, 0.0)); d0 = backproject(uv, 'ground')[0]
up   = backproject(uv, 'ground', pitch=-1.0)[0]
down = backproject(uv, 'ground', pitch=+1.0)[0]
print(f'\\n50m 处：pitch+1°(低头) -> {down:7.2f}m   pitch-1°(抬头) -> {up:7.2f}m')
print(f'   两侧偏差 {abs(down-d0):.2f}m vs {abs(up-d0):.2f}m —— **高度不对称**')
lin = H / np.sin(np.arctan2(H, 50.0))**2 * np.deg2rad(1)
print(f'   一阶近似给 ±{lin:.2f}m —— **两侧都不对**（远处线性化失效）')
assert abs(up - d0) > 3 * abs(down - d0), '抬头一侧的误差应远大于低头一侧'"""),

    md("""## 6 · 小结：本模块建立的东西

| 结论 | 数值 | 在哪个模块被展开 |
|---|---|---|
| 正向投影唯一、反向缺一个自由度 | 补法只有四种 | 全课 |
| 地面假设被破坏 | $d_{\\text{read}}=d\\cdot H/(H-z)$，相对偏差 < 1e-12 | 模块 04 |
| 相对误差与距离无关 | $z/(H-z)$，各距离差异 < 1e-12 | 模块 04 |
| $z\\ge H$ 时 IPM 无解 | 而限速牌就在 2.0–2.5 m | 模块 04 |
| 1° 外参 = 24–52 px | 且比值随距离上升 | 模块 02 |
| 俯仰误差高度不对称 | 50m 处 −18m / +70m | 模块 02 |"""),

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：批量投影

实现 `project_batch(P, pitch=0.0)`：输入形状 `(N,3)` 的车体坐标数组，
返回 `(N,2)` 的像素数组；**相机后方的点对应行填 `np.nan`**。

要求：不许在 Python 里逐点循环（用矩阵运算），且与逐点 `project()` 完全一致。"""),

    code("""def project_batch(P, pitch=0.0):
    \"\"\"(N,3) 车体坐标 -> (N,2) 像素；相机后方的点填 nan。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
PTS = np.array([list(v) for v in SCENE.values()] + [
    [-5.0, 0.0, 0.0],      # 车后
    [0.0, 0.0, 0.0],       # 正下方
    [100.0, -8.0, 3.0],
])

got = project_batch(PTS)
assert got.shape == (len(PTS), 2), got.shape

for i, P in enumerate(PTS):
    ref = project(P)
    if ref is None:
        assert np.all(np.isnan(got[i])), f'第 {i} 点在相机后方，应为 nan'
    else:
        assert np.allclose(got[i], ref, atol=1e-9), (i, got[i], ref)

got_p = project_batch(PTS, pitch=2.5)
for i, P in enumerate(PTS):
    ref = project(P, pitch=2.5)
    if ref is not None:
        assert np.allclose(got_p[i], ref, atol=1e-9), (i, got_p[i], ref)

n_nan = int(np.isnan(got[:, 0]).sum())
print(f'{len(PTS)} 个点：{len(PTS)-n_nan} 个成像、{n_nan} 个在相机后方')
print('✅ 练习 1 通过：批量与逐点完全一致，且后方点被标成 nan')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def project_batch(P, pitch=0.0):
    P = np.atleast_2d(np.asarray(P, float))
    P_c = (P - CAM_T) @ R_vc(pitch)            # (N,3) @ (3,3) == (R.T @ v).T
    out = np.full((len(P), 2), np.nan)
    ok = P_c[:, 2] > 1e-9
    out[ok, 0] = CX + F * P_c[ok, 0] / P_c[ok, 2]
    out[ok, 1] = CY + F * P_c[ok, 1] / P_c[ok, 2]
    return out

for i, P in enumerate(PTS):
    ref = project(P)
    g = project_batch(PTS)[i]
    assert (np.all(np.isnan(g)) if ref is None else np.allclose(g, ref, atol=1e-9))
print('✅ 参考答案 1 通过（注意 (P-t) @ R 等价于 R.T @ (P-t) 的批量写法）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：已知尺寸测距

法规把交通标志的物理尺寸钉死了（例如圆形限速牌直径 0.6 / 0.8 / 1.2 m）。
于是「已知尺寸」是 TSR 里最实用的一种补法。

实现 `dist_from_size(size_px, size_m)`：由像素边长与真实边长求**沿光轴的深度**，
并实现 `dist_from_size_err(size_px, size_m, px_err)`：
给定像素测量误差 `px_err`，返回 `(深度下界, 深度上界)`。

> 自测里会顺带验证一条定律：**不确定度 $\\propto d^2$** ——
> 这与模块 03 的三角测量 $Z^2/(Bf)$ 是同一条，只是把基线 $B$ 换成了物体尺寸 $S$。"""),

    code("""def dist_from_size(size_px, size_m):
    \"\"\"相似三角形测距：返回沿光轴深度 (m)。\"\"\"
    # TODO
    raise NotImplementedError

def dist_from_size_err(size_px, size_m, px_err):
    \"\"\"返回 (下界, 上界)：像素边长在 ±px_err 内变动时深度的范围。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
SIGN_M = 0.8                      # 直径 0.8m 的限速牌
TRUE_D = [10.0, 30.0, 50.0, 80.0]
sizes  = [F * SIGN_M / d for d in TRUE_D]

for d, s in zip(TRUE_D, sizes):
    assert abs(dist_from_size(s, SIGN_M) - d) < 1e-9, (d, s)

lo, hi = dist_from_size_err(sizes[1], SIGN_M, 1.0)
assert lo < 30.0 < hi
assert abs(hi - lo) > abs(dist_from_size_err(sizes[0], SIGN_M, 1.0)[1]
                          - dist_from_size_err(sizes[0], SIGN_M, 1.0)[0]), \\
    '远处同样的像素误差应造成更大的深度不确定度'

print(f\"{'真距':>6s} {'像素边长':>10s} {'±1px 的深度区间':>24s} {'相对宽度':>9s} {'宽度/d²':>12s}\")
rel_w, norm_w = [], []
for d, s in zip(TRUE_D, sizes):
    lo, hi = dist_from_size_err(s, SIGN_M, 1.0)
    rel_w.append((hi - lo) / d)
    norm_w.append((hi - lo) / d ** 2)
    print(f'{d:5.0f}m {s:9.2f}px   [{lo:8.2f}, {hi:8.2f}] {100*(hi-lo)/d:8.1f}% {(hi-lo)/d**2:12.4e}')

assert rel_w == sorted(rel_w), '相对宽度应随距离单调上升'
# 关键定律：不确定度 ∝ d²   （宽度 ≈ 2·e_px·d²/(f·S)）
# 所以「宽度/d²」应当近乎常数——这与模块 03 三角测量的 Z²/(B·f) 是**同一条定律**，
# 只是把「基线 B」换成了「物体的物理尺寸 S」
assert (max(norm_w) - min(norm_w)) / min(norm_w) < 0.01, '宽度/d² 应在 1% 内恒定'
print(f'\\n宽度/d² 的波动只有 {100*(max(norm_w)-min(norm_w))/min(norm_w):.2f}%'
      '  → **不确定度 ∝ d²**')
print('✅ 练习 2 通过：已知尺寸能给出距离**和**不确定度，且服从 d² 定律')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def dist_from_size(size_px, size_m):
    return F * float(size_m) / float(size_px)

def dist_from_size_err(size_px, size_m, px_err):
    s_hi = size_px + px_err        # 看起来更大 -> 更近
    s_lo = max(size_px - px_err, 1e-9)
    return (dist_from_size(s_hi, size_m), dist_from_size(s_lo, size_m))

for d, s in zip(TRUE_D, sizes):
    assert abs(dist_from_size(s, SIGN_M) - d) < 1e-9
lo, hi = dist_from_size_err(sizes[3], SIGN_M, 1.0)
print(f'80m 处 ±1px -> [{lo:.2f}, {hi:.2f}] m，宽度 {hi-lo:.2f} m')
print('✅ 参考答案 2 通过（注意区间不对称：深度是像素边长的倒数关系）')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：把中心公式的三条推论写成检查

实现 `ipm_audit(h)`，返回一个 dict，逐条验证：

- `'rel_bias_at'` —— `{z: 相对误差}`，对 `z in (0.0, 0.5, 1.0)`
- `'dist_free'` —— bool：相对误差是否与距离无关（在 `d in (10,50,200)` 上验证）
- `'diverges_at'` —— float：发散点（读出趋于无穷的 z）
- `'no_solution_above'` —— float：从哪个 z 起无解

这四项就是模块 04 的验收清单。"""),

    code("""def ipm_audit(h):
    \"\"\"返回 dict(rel_bias_at, dist_free, diverges_at, no_solution_above)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
for h in [1.2, 1.5, 2.4]:
    a = ipm_audit(h)
    assert set(a) == {'rel_bias_at', 'dist_free', 'diverges_at', 'no_solution_above'}
    assert a['dist_free'] is True, '相对误差必须与距离无关'
    assert abs(a['diverges_at'] - h) < 1e-12
    assert abs(a['no_solution_above'] - h) < 1e-12
    assert abs(a['rel_bias_at'][0.0]) < 1e-12
    assert abs(a['rel_bias_at'][1.0] - 1.0 / (h - 1.0)) < 1e-12

a = ipm_audit(1.5)
print('h=1.5m 的审计结果：')
for z, r in a['rel_bias_at'].items():
    print(f'  离地 {z:.1f}m -> 相对误差 {r*100:8.1f}%')
print(f\"  与距离无关: {a['dist_free']}   发散于 z={a['diverges_at']}m\"
      f\"   z>={a['no_solution_above']}m 无解\")
print('\\n✅ 练习 3 通过：三条推论都成立，且对任意相机高度都成立')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def ipm_audit(h):
    rel = {}
    for z in (0.0, 0.5, 1.0):
        rel[z] = z / (h - z)
    free = True
    for z in (0.0, 0.5, 1.0):
        rs = [ipm_read_formula(d, z, h) / d for d in (10.0, 50.0, 200.0)]
        if max(rs) - min(rs) > 1e-12:
            free = False
    return {'rel_bias_at': rel, 'dist_free': free,
            'diverges_at': float(h), 'no_solution_above': float(h)}

for h in [1.2, 1.5, 2.4]:
    a = ipm_audit(h)
    assert a['dist_free'] and abs(a['diverges_at'] - h) < 1e-12
print('✅ 参考答案 3 通过')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：误差预算表

实现 `error_budget(d, *, px=1.0, pitch_deg=1.0, dt_ms=33.0, speed_kmh=120.0)`，
返回一个 dict，把四个来源都换算成**米**，并给出 `'dominant'`（最大的那一项的名字）：

- `'pixel'` —— `px` 个像素的定位误差
- `'pitch'` —— `pitch_deg` 度俯仰误差（取抬头/低头两侧的**最大**值）
- `'latency'` —— `dt_ms` 毫秒时间戳误差 × 车速
- `'assumption'` —— 把一块离地 1.0 m 的标志当地面点处理

这张表是本课的核心交付物：**它让「该修哪一个」变成一个可计算的问题。**"""),

    code("""def error_budget(d, *, px=1.0, pitch_deg=1.0, dt_ms=33.0, speed_kmh=120.0):
    \"\"\"把四个误差源都换算成米，并指出主导项。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
b30 = error_budget(30.0)
assert set(b30) == {'pixel', 'pitch', 'latency', 'assumption', 'dominant'}
assert b30['dominant'] in ('pixel', 'pitch', 'latency', 'assumption')

# 时间戳一项与距离无关，纯运动学
assert abs(error_budget(10.0)['latency'] - error_budget(80.0)['latency']) < 1e-12
assert abs(b30['latency'] - 120/3.6*0.033) < 1e-9

# 像素与俯仰两项都随距离增长
for k in ('pixel', 'pitch'):
    vals = [error_budget(d)[k] for d in (10, 20, 30, 50, 80)]
    assert vals == sorted(vals), f'{k} 应随距离单调上升'

print(f\"{'距离':>6s} {'像素':>9s} {'俯仰1°':>10s} {'时延33ms':>10s} {'假设破坏':>10s}  主导项\")
for d in [10, 20, 30, 50, 80]:
    b = error_budget(d)
    print(f\"{d:5d}m {b['pixel']:8.3f}m {b['pitch']:9.2f}m \"
          f\"{b['latency']:9.3f}m {b['assumption']:9.2f}m  {b['dominant']}\")

assert error_budget(10.0)['dominant'] == 'assumption', '近处：假设破坏最致命'
assert error_budget(80.0)['dominant'] == 'pitch', '远处：标定误差反超'
print('\\n✅ 练习 4 通过：主导项随距离切换——'
      '近处「假设用错」最致命，远处「标定」反超')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def error_budget(d, *, px=1.0, pitch_deg=1.0, dt_ms=33.0, speed_kmh=120.0):
    uv = project((d, 0.0, 0.0))
    d0 = backproject(uv, 'ground')[0]

    e_px = abs(backproject(uv + np.array([0.0, px]), 'ground')[0] - d0)

    e_pitch = 0.0
    for sign in (+1.0, -1.0):
        bp = backproject(uv, 'ground', pitch=sign * pitch_deg)
        v = np.inf if bp is None else bp[0]
        e_pitch = max(e_pitch, abs(v - d0))

    e_lat = speed_kmh / 3.6 * (dt_ms / 1000.0)
    e_ass = abs(ipm_read_formula(d, 1.0) - d)

    out = {'pixel': e_px, 'pitch': e_pitch, 'latency': e_lat, 'assumption': e_ass}
    out['dominant'] = max(out, key=out.get)
    return out

assert error_budget(10.0)['dominant'] == 'assumption'
assert error_budget(80.0)['dominant'] == 'pitch'
print('✅ 参考答案 4 通过')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊：把这一层接到真实栈上

本课自己实现投影是为了看清误差从哪来。真实项目里对应的东西：

```python
# ── 1) OpenCV：投影与去畸变（模块 01 会自己实现一遍）──
import cv2
uv, _ = cv2.projectPoints(P_obj, rvec, tvec, K, dist)      # 正向
xy_n  = cv2.undistortPoints(uv, K, dist)                    # 去畸变到归一化平面

# ── 2) ROS TF2：外参不该写在代码里，应该来自变换树 ──
#   坐标系命名遵循 REP-105：base_link / camera_link / map
tf = tf_buffer.lookup_transform('base_link', 'camera_front',
                                stamp, timeout=rospy.Duration(0.05))
#   ↑ 关键是 stamp：**用哪一时刻的外参**，而不是「当前」的
#     悬挂动态让 pitch 在行驶中变化，模块 02 第 6 节量它的幅度

# ── 3) 把「假设」写进接口，而不是写在注释里 ──
@dataclass(frozen=True)
class Detection3D:
    uv: tuple
    range_m: float
    assumption: Literal['ground', 'known_height', 'known_size', 'stereo']
    sigma_m: float          # ← 与 range 一起给，否则下游无法融合
#   下游（规控）必须能读到「这个米数是怎么来的」
#   而 sigma 的算法就是练习 4 的误差预算表

# ── 4) 标定件的版本化（模块 02 第 7 节）──
#   intrinsics.yaml / extrinsics.yaml 必须带：
#     标定日期 · 重投影误差的中位数与 P95 · 标定板规格 · 采集张数
#   **没有重投影误差的标定文件不允许上车**
```

> **一条可以立刻用的检查**：把你现有栈里所有「像素 → 米」的调用点找出来，
> 逐个回答「这里用的是哪一种补法」。
> 本课的经验是：**总有几处答不上来，而它们通常就是「距离总是偏大」的来源。**"""),
]
