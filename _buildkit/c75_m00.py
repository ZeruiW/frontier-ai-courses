# -*- coding: utf-8 -*-
"""C75 模块 00 · 课程总览：从图像得到几何的四条路线。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C72（多视角几何）是硬前提</strong>——"
                 "相机模型、内外参、对极几何、三角测量、PnP 本课直接使用；"
                 "线性代数（最小二乘、SVD、条件数）；"
                 "<em>C73 与 C74 不是前提，但模块 05（网格化）会用到 C74 的深度口径</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（<strong>把「绝对尺度不可观测」验证到浮点精度</strong>：'
                       '整个场景与相机平移一起乘 $10^3$，图像逐位相同 / '
                       '四条路线各注入一次错误并量出代价 / '
                       '<strong>束调整 Hessian 的秩亏恰好是 7</strong>）'),
    ("核心参考", "Hartley &amp; Zisserman, <em>Multiple View Geometry</em>（2nd ed., 2004）· "
                 "Schönberger &amp; Frahm, <em>Structure-from-Motion Revisited</em>（CVPR 2016，COLMAP）· "
                 "Furukawa &amp; Hernández, <em>Multi-View Stereo: A Tutorial</em>（2015）· "
                 "Wang et al., <em>DUSt3R</em>（CVPR 2024）· "
                 "Poole et al., <em>DreamFusion</em>（ICLR 2023，SDS）· "
                 "Knapitsch et al., <em>Tanks and Temples</em>（SIGGRAPH 2017，F-score 的口径）· "
                 "本课程 <strong>C72</strong>（几何前提）· C74（渲染的一侧）"),
    ("预计时长", "读 45 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("problem", "一个约束先把整门课框定了：绝对尺度不可观测", "".join([
        P("本课的问题是「从图像得到几何」。而在讲任何方法之前，"
          "有一条**原理性**的限制必须先说清，因为它决定了每条路线的形状。"),
        MATH(r"\text{把场景点 } X \to sX \text{、相机平移 } t \to st"
             r"\;\Longrightarrow\; \pi(sX) = \frac{f\,sX}{sZ} = \frac{fX}{Z} = \pi(X)"),
        DUAL(
            "<strong>投影是齐次的，所以整个场景放大 $s$ 倍、相机位置也放大 $s$ 倍，"
            "拍出的图像<em>逐位相同</em>。</strong>"
            "<em>notebook 把 $s$ 取到 $10^3$ 与 $10^{-3}$，最大像素差 "
            "$1.1\\times10^{-13}$——纯浮点舍入</em>。"
            "<strong>所以「从图像得到米」在原理上是不可能的，"
            "无论用多少张图、多好的网络。</strong>",
            "<strong>于是每条路线都必须在某处引入外部信息，而<em>引入的位置</em>"
            "就是这些方法最大的区别。</strong>"
            "<em>已知物体的物理尺寸（C72 模块 03 的做法）· 已标定的双目基线 · "
            "IMU 或轮速 · 或者——一个从数据里<strong>学到</strong>的尺度先验</em>。"
            "<strong>最后那一种是 2024 年以来单目/前馈方法的做法，"
            "而它把一个几何问题换成了一个统计问题</strong>——"
            "<em>好处是不需要标定，代价是尺度的正确性取决于测试场景与训练分布的接近程度</em>。"),
        CALLOUT("warn",
                "<strong>这条限制常被含糊掉，而含糊的代价很具体。</strong>"
                "<em>「我们的方法在 KITTI 上的绝对深度误差是 2.3%」这句话，"
                "如果没说清尺度是怎么定的，它可能在量三件完全不同的事</em>："
                "① <strong>用真值的中位数对齐了尺度</strong>（那么它没有量尺度）；"
                "② <strong>用标定好的基线</strong>（那么尺度来自硬件）；"
                "③ <strong>网络直接输出米</strong>（那么它在量「训练分布覆盖得好不好」）。"
                "<strong>模块 03 会把这三种口径的差别量出来："
                "同一个「仿射意义上完美」的预测，"
                "在不同对齐口径下的相对误差差 <em>108 倍</em>。</strong>"),
    ])),

    # ============================================================== 2
    ("routes", "四条路线与它们的适用区间", "".join([
        TABLE(["路线", "怎么做", "外部信息从哪来", "什么时候用它", "在哪个模块"], [
            ["<strong>① 几何优化</strong><br>SfM + MVS",
             "从图像里找对应 → 解位姿与稀疏点 → 稠密化",
             "<em>需要外部尺度；位姿与内参由数据本身解出</em>",
             "<strong>视角多（几十到几千张）、场景静态、要精度</strong>",
             "01 · 02"],
            ["<strong>② 前馈回归</strong><br>单目深度 / pointmap",
             "一次前向直接输出深度或 3D 点",
             "<strong>训练数据里学到的先验</strong>",
             "<strong>视角极少（1–2 张）、要快、能接受尺度不确定</strong>",
             "03"],
            ["<strong>③ 生成式</strong><br>SDS / 多视角扩散",
             "用一个 2D 生成先验去「雕」一个 3D 表示",
             "<strong>预训练的图像/视频扩散模型</strong>",
             "<strong>只有一张图或只有文字、允许「编」出没观测到的部分</strong>",
             "04"],
            ["<strong>④ 可微渲染拟合</strong><br>NeRF / 3DGS",
             "给定位姿，优化一个表示去拟合图像",
             "<em>位姿来自 ①；尺度也来自 ①</em>",
             "<strong>已有位姿、要高质量新视角</strong>",
             "<strong>C74</strong>（本课不重复）"],
        ]),
        ASCII("""
   四条路线的依赖关系（箭头 = 「用到它的输出」）：

                     ┌──────────────────────────────┐
   图像 ──> ① SfM ───┤ 位姿 + 内参 + 稀疏点 + 尺度基准 │
             │       └───────────┬──────────────────┘
             │                   │
             ├──> ② MVS ──> 稠密深度图 ──┐
             │                          ├──> 模块 05：网格化 + 评测
             └──> ④ 3DGS/NeRF ──> 辐射场 ┘        （C74 的输出接到这里）

   ② 前馈回归：图像 ──> 深度/点图    （**不需要** ① —— 这是它的全部卖点）
   ③ 生成式：  文字/单图 ──> 3D      （**没有** 真实观测可对齐，所以要靠先验）
        """),
        DUAL(
            "<strong>这张图里最重要的一条是「② 不需要 ①」。</strong>"
            "<em>传统流程里 SfM 是<strong>一切的第一步</strong>——"
            "C74 的 3DGS 需要它、MVS 需要它、评测的坐标系也来自它</em>。"
            "<strong>而 SfM 在三种情况下会直接失败</strong>："
            "<em>视角太少、基线太短（模块 01：$B/z$ 趋 0 时条件数从 $10^3$ 跳到 $4.4\\times10^{17}$）、"
            "或者纹理不足（模块 02：无纹理区的匹配代价曲线是平的）</em>。"
            "<strong>「pose-free」这个词的真实含义就是「绕开这个失败模式」。</strong>",
            "<strong>而 ③ 与前三条有一个性质上的差别：它没有真实观测可以对齐。</strong>"
            "<em>① ② ④ 都在拟合<strong>看到过的</strong>图像，所以「对不对」有客观判据；"
            "③ 在生成<strong>没看到过的</strong>部分，所以「对不对」取决于先验</em>。"
            "<strong>模块 04 会把这一点的后果量出来：SDS 的模式内散布比先验收缩 7 倍</strong>——"
            "<em>也就是说同一个提示词跑多次得到的结果几乎一样，"
            "而这不是 bug，是 SDS 的目标函数本来就在找模式而不是采样</em>。"),
    ])),

    # ============================================================== 3
    ("map", "课程地图", "".join([
        TABLE(["模块", "主题", "带走的那个可验证的量"], [
            ["<strong>01</strong>", "SfM：对应、增量重建、束调整",
             "<strong>束调整 Hessian 的秩亏<em>恰好</em>是 7</strong>"
             "（相似变换群），而这 7 个方向有<strong>解析</strong>形式"
             "（$\\Vert JQ\\Vert/\\Vert J\\Vert \\approx 2\\times10^{-11}$）· "
             "<strong>投影掉 gauge 后的条件数 $\\propto (B/z)^{-2}$</strong>，"
             "而 $B/z=0$ 时是 $4.4\\times10^{17}$ 的悬崖 · "
             "Schur 补在 500 相机时快 $10^6$ 倍"],
            ["<strong>02</strong>", "稠密多视图立体",
             "<strong>深度假设必须在<em>视差</em>上均匀</strong>："
             "深度均匀时 $D{=}64$ 在近场的视差步长是 <strong>102.7 px</strong> · "
             "所需 $D = f B(1/z_{\\min}-1/z_{\\max})$ · "
             "<strong>三类失效：弱纹理随噪声渐进失效、周期纹理<em>与噪声无关</em>地结构性失效"
             "（峰-次峰间隔恰为 0）、而倾斜反而<em>修好</em>周期纹理</strong>"],
            ["<strong>03</strong>", "前馈回归：单目深度与点图",
             "<strong>绝对尺度不可观测（图像逐位相同）</strong> · "
             "<strong>仿射对齐 vs 纯尺度对齐差 108 倍</strong>——口径选错会把好模型报成差模型 · "
             "点图能<strong>精确</strong>反解焦距（$1.9\\times10^{-16}$），"
             "代价是它恰好 <strong>3.00×</strong> 过参数化"],
            ["<strong>04</strong>", "3D 生成：SDS 与多视角扩散",
             "<strong>SDS 是模式寻求的：模式内散布比先验收缩 7 倍</strong> · "
             "<strong>而它收敛到的模式系统性内移 22%</strong>（$\\pm1.569$ vs 真值 $\\pm2.0$）"
             "——因为它找的是「对 $t$ 平均后的平滑密度」的模式 · "
             "<strong>Janus 是目标函数的最优解，不是优化失败</strong>"],
            ["<strong>05</strong>", "网格化与 3D 重建评测",
             "<strong>Marching Cubes 的 256 种情形归约为 15 类</strong>"
             "（仅旋转是 23 类），而 <strong>120/256 = 46.9% 含面歧义</strong>（6 类）· "
             "<strong>Chamfer 距离不是度量</strong>（三角不等式反例：20 &gt; 5+5）· "
             "<strong>CD-L1 对离群点线性、CD-L2 平方</strong>（一个离群点让 L2 涨 293 倍）· "
             "同一曲面改采样密度让 CD 变 3.3 倍"],
        ]),
        CALLOUT("intuition",
                "<strong>一条贯穿全课的线：每个模块都有一个「看起来是精度问题、实际是可观测性问题」的地方。</strong>"
                "<em>模块 01 的纯旋转（深度不可观测，不是测不准）；"
                "模块 02 的周期纹理（结构性歧义，不是噪声）；"
                "模块 03 的绝对尺度（原理不可观测，不是模型不够好）；"
                "模块 04 的 Janus（目标的最优解，不是优化失败）；"
                "模块 05 的 Chamfer（不是度量，所以「差 0.1」这句话没有传递性）</em>。"
                "<strong>把这五个分清，比记住任何一个算法都重要。</strong>"),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工", "".join([
        TABLE(["课程", "它讲什么", "分工"], [
            ["<strong>C72</strong> · 多视角几何（硬前提）",
             "相机模型与畸变、标定与验收、对极/三角测量/单应/PnP、BEV、时空对齐",
             "<strong>C72 讲「已知对应关系时怎么算」，本课讲「对应关系从哪来、"
             "以及规模变大之后怎么解」</strong>。"
             "<em>C72 的双目只作为四种测距法之一出现（精度对比），"
             "而本课模块 02 讲<strong>稠密</strong>匹配：代价体、平面扫掠、"
             "窗口大小的取舍</em>"],
            ["<strong>C73</strong> · 3D 表示与点云深度学习",
             "点云/体素/网格/隐式四种表示、置换不变性、稀疏卷积、3D 检测与分割",
             "<strong>C73 管「已经有点云之后怎么处理它」，本课管「点云从哪来」</strong>。"
             "<em>C73 明确声明不碰点云配准（ICP）与 SfM，正好是本课模块 01 的内容</em>"],
            ["<strong>C74</strong> · 3D 高斯溅泼",
             "体渲染与 α 合成、高斯基元与投影、tile 光栅化、密度控制、球谐",
             "<strong>C74 管「有了几何之后怎么渲染」，本课管「几何从哪来」——"
             "而两者在两个点上接口</strong>："
             "<em>① 3DGS 的输入是 SfM 的位姿与稀疏点（本课模块 01）；"
             "② 从 3DGS/2DGS 提网格用的是 C74 模块 01 的三种深度口径"
             "（本课模块 05）</em>"],
            ["<strong>C28</strong> · 扩散与流前沿",
             "DiT、flow matching、consistency、采样器",
             "<strong>C28 讲扩散模型本身，本课模块 04 只讲「怎么把一个已有的 2D 扩散先验"
             "用到 3D 上」</strong>——"
             "<em>即 SDS 的梯度形式、它为什么是模式寻求的、以及多视角一致性</em>"],
            ["<strong>C18</strong> · 计算机视觉",
             "特征、分割、检测的经典方法",
             "<em>本课模块 01 会用到特征匹配，但把它当已知工具</em>——"
             "<strong>SIFT/SuperPoint 的内部不在本课范围</strong>"],
        ]),
        CALLOUT("paper",
                "<strong>一句话划清边界</strong>："
                "本课<strong>不讲</strong> SLAM 的实时性与回环检测（那是另一门课的量级）、"
                "不讲特征提取器的内部（C18）、"
                "不讲扩散模型的训练与采样器（C28）、"
                "不讲可微渲染的实现（C74）。"
                "<em>本课讲的是「几何从图像里被解出来」这一条链，"
                "以及它在四种数据条件下的四种形态</em>。"),
    ])),

    # ============================================================== 5
    ("method", "方法论：这门课有真实优化，但没有神经网络训练", "".join([
        DUAL(
            "<strong>与 C72/C73/C74 不同，本课会真的跑优化</strong>——"
            "<em>模块 01 有一个能收敛的束调整（Levenberg–Marquardt + Schur 补）；"
            "模块 02 有一个能出深度图的平面扫掠；"
            "模块 04 有一个在解析已知的先验上跑的 SDS</em>。"
            "<strong>因为这门课的核心问题<em>就是</em>优化的性质："
            "什么可观测、条件数多大、收敛到哪个不动点。</strong>",
            "<strong>但它<em>不</em>训练任何神经网络。</strong>"
            "<em>模块 03 的单目深度与点图、模块 04 的扩散先验，"
            "都用<strong>解析构造的替身</strong>："
            "一个「仿射意义上完美」的深度预测器、一个高斯混合当扩散先验</em>。"
            "<strong>理由是这两个模块要验证的是<em>口径</em>与<em>目标函数的性质</em>，"
            "而它们与网络权重无关</strong>——"
            "<em>「仿射对齐 vs 尺度对齐差 108 倍」对任何预测器都成立；"
            "「SDS 是模式寻求的」是它梯度形式的直接后果</em>。"),
        H3("代价说清楚"),
        UL([
            "<strong>本课不能回答「哪个单目深度模型更好」</strong>——"
            "<em>那需要真实数据集与训练；本课只能告诉你<strong>用什么口径去比</strong></em>",
            "<strong>本课的 SDS 实验是 1D 的</strong>——"
            "<em>它能证明模式寻求与模式内移，但不能预测真实 3D 生成的视觉质量</em>",
            "<strong>本课的 MVS 是 1D 扫描线</strong>——"
            "<em>代价体的规模、视差采样、窗口取舍都能量准，"
            "但不含真实的多视角聚合与遮挡推理</em>",
            "<strong>模块 01 的束调整规模是几十个相机</strong>——"
            "<em>稀疏结构与 Schur 补的收益按公式外推到几千个相机，而不是实测</em>",
        ]),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：机制 → 可验证的量 → 它决定了什么设计",
            "<strong>notebook</strong>：6–8 个 worked 小节，每节以 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接 COLMAP / OpenMVS / DUSt3R / threestudio 的代码",
        ]),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        CODE("""cd C75_Reconstruction_Generation_Course
pip install -r requirements.txt      # 只有 numpy 与 jupyter
jupyter lab 00_setup/00_environment_check.ipynb""", "bash"),
        TABLE(["模块", "notebook", "本模块的 4 道练习在做什么"], [
            ["00", "<code>00_environment_check.ipynb</code>",
             "尺度不可观测的逐位验证 · 四条路线各注入一次错误 · "
             "束调整的秩亏 · 规模账"],
            ["01", "<code>01_sfm.ipynb</code>",
             "两视图初始化与退化 · gauge 零空间的解析构造 · "
             "Schur 补 · 增量漂移"],
            ["02", "<code>02_mvs.ipynb</code>",
             "视差域采样 · NCC 与三类失效 · 窗口取舍 · 左右一致性检验"],
            ["03", "<code>03_feedforward.ipynb</code>",
             "三种对齐口径 · 点图反解内参 · 过参数化的代价 · 尺度先验的迁移性"],
            ["04", "<code>04_generation.ipynb</code>",
             "SDS 梯度的闭式 · 不动点与模式内移 · CFG 的两种效应 · Janus 的构造"],
            ["05", "<code>05_mesh_eval.ipynb</code>",
             "Marching Cubes 的 15 类与 6 类歧义 · Chamfer 不是度量 · "
             "L1 vs L2 的离群敏感性 · F-score 的阈值"],
        ]),
        P("<strong>如果只有两个小时</strong>：读模块 01 第 3–4 节（gauge 与条件数）"
          "+ 模块 05 第 3–5 节（评测口径），跑 00 与 05 的 notebook。"
          "<em>这条路径覆盖了「重建问题好不好解」与「重建结果怎么比」两件事，"
          "而它们是这门课里最容易被做错、且后果最大的两处。</em>"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 00 · 环境自检与四条路线的代价

本 notebook 做四件事：

1. **把「绝对尺度不可观测」验证到浮点精度** —— 场景与相机一起乘 $10^3$，图像逐位相同；
2. **四条路线各注入一次错误，量出代价**：
   SfM 的 gauge 没固定 · MVS 的深度均匀采样 · 前馈的对齐口径 · SDS 的学习率；
3. **束调整 Hessian 的秩亏恰好是 7**，且这 7 个方向有解析形式；
4. 算清四条路线的规模账。

只用 numpy，CPU，离线。"""),

code("""import sys, numpy as np, math
print('python', sys.version.split()[0], '| numpy', np.__version__)

# 相机（与 C72 的约定一致：x 右、y 下、z 前）
F, CX, CY, W_IMG, H_IMG = 600.0, 320.0, 240.0, 640, 480
print(f'相机 f={F:.0f}px  主点=({CX:.0f},{CY:.0f})  {W_IMG}x{H_IMG}')
print(f'水平视场 {2*np.degrees(np.arctan(CX/F)):.1f}°')

def project(X, R=None, t=None, f=F):
    '''3D 点 -> 像素。X 是 (n,3)。'''
    X = np.atleast_2d(np.asarray(X, float))
    R = np.eye(3) if R is None else np.asarray(R, float)
    t = np.zeros(3) if t is None else np.asarray(t, float)
    P = (R @ X.T).T + t
    assert np.all(P[:, 2] > 1e-9), '所有点必须在相机前方'
    return np.stack([CX + f*P[:, 0]/P[:, 2], CY + f*P[:, 1]/P[:, 2]], 1)

_X = np.array([[0.1, -0.2, 5.0], [-0.4, 0.3, 8.0]])
print('\\n两个测试点的投影:', np.round(project(_X), 3))
assert project(np.array([[0., 0., 5.]]))[0].tolist() == [CX, CY]
print('✓ 光轴上的点投在主点上')"""),

md("""## 1 · 绝对尺度不可观测：验证到浮点精度

$\\pi(sX) = \\dfrac{f\\,sX}{sZ} = \\dfrac{fX}{Z} = \\pi(X)$。
把整个场景**与相机平移一起**乘 $s$，图像应当逐位相同。"""),

code("""rng = np.random.default_rng(0)
X0 = rng.normal(0, 1, (200, 3)) + np.array([0, 0, 6.0])
R0 = np.eye(3)
t0 = np.array([0.3, -0.1, 0.0])
uv0 = project(X0, R0, t0)

print(' s              最大像素差')
for s in [0.5, 2.0, 1e3, 1e-3, 1e6]:
    uv = project(X0*s, R0, t0*s)
    d = np.abs(uv - uv0).max()
    print(f' {s:10.0e}    {d:.3e}')
    assert d < 1e-8, f's={s} 时差 {d:.3e} 太大'

print('\\n✓ 逐位相同（最大差 < 1e-8，纯浮点舍入）')
print('  所以「从图像得到米」在原理上不可能 —— 无论多少张图、多好的网络。')

# 但**相对**结构是可观测的：形状不变
def shape_signature(X):
    '''一个尺度不变的形状描述：所有点对距离除以最大距离。'''
    d = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    return d / d.max()
sig0 = shape_signature(X0)
for s in [0.5, 1e3]:
    assert np.allclose(shape_signature(X0*s), sig0, atol=1e-12)
print('✓ 而尺度不变的形状描述完全不变 —— 所以「相对深度」是可观测的')

# 旋转与平移也不可观测（整体刚体变换）
def rodrigues(w):
    th = np.linalg.norm(w)
    if th < 1e-12: return np.eye(3)
    k = w/th; K = np.array([[0,-k[2],k[1]],[k[2],0,-k[0]],[-k[1],k[0],0]])
    return np.eye(3) + np.sin(th)*K + (1-np.cos(th))*K@K

Rw = rodrigues(np.array([0.1, -0.2, 0.35])); dt = np.array([1.0, -2.0, 0.5])
X1 = (Rw @ X0.T).T + dt
R1 = R0 @ Rw.T
t1 = t0 - R1 @ dt
print(f'\\n整体刚体变换后的最大像素差 {np.abs(project(X1, R1, t1) - uv0).max():.3e}')
assert np.abs(project(X1, R1, t1) - uv0).max() < 1e-8
print('✓ 旋转(3) + 平移(3) + 尺度(1) = **7 个自由度**完全不可观测')
print('  这 7 个就是第 4 节要在束调整的 Hessian 里找到的零空间')"""),

md("""## 2 · 四条路线各注入一次错误

每条路线的「最容易犯且后果最大」的那一个错。"""),

code("""# ---- 注入 ①（SfM）：gauge 没固定 -> 尺度随机漂移，而残差完全不变 ----
print('注入 ①（SfM）：束调整不固定 gauge')
print('  沿尺度方向移动整个重建，重投影残差应当**完全不变**：')
scales = [1.0, 1.5, 0.3, 10.0]
res = []
for s in scales:
    uv = project(X0*s, R0, t0*s)
    res.append(float(np.sqrt(np.mean((uv - uv0)**2))))
print('  尺度倍数 ', scales)
print('  残差 RMS ', [f'{r:.2e}' for r in res])
assert max(res) < 1e-8
print('  ✓ 残差全为 0 —— 所以优化器**没有任何理由**停在某个特定尺度上。')
print('    后果：每次跑出来的重建大小不一样，而看残差完全看不出问题。')

# ---- 注入 ②（MVS）：深度假设在深度上均匀而不是在视差上均匀 ----
print('\\n注入 ②（MVS）：深度假设在**深度**上均匀')
f_mvs, B_mvs = 700.0, 0.12
zmin, zmax, D = 0.5, 50.0, 64
z_uni = np.linspace(zmin, zmax, D)
d_at_z = f_mvs*B_mvs/z_uni
step_uni = np.abs(np.diff(d_at_z))
i = int(np.argmax(step_uni))
dmin, dmax = f_mvs*B_mvs/zmax, f_mvs*B_mvs/zmin
d_uni = np.linspace(dmin, dmax, D)
step_disp = abs(d_uni[1] - d_uni[0])
print(f'  f={f_mvs:.0f} B={B_mvs} 深度范围 [{zmin},{zmax}] m, D={D}')
print(f'  深度均匀: 最大视差步长 {step_uni.max():.3f} px @ z={z_uni[i+1]:.2f} m')
print(f'  视差均匀: 视差步长恒为 {step_disp:.3f} px')
assert step_uni.max() > 100, '深度均匀时近场步长应超过 100 px'
assert step_disp < 3.0
print(f'  ✓ 深度均匀时近场的视差步长是 {step_uni.max():.1f} px —— 近场等于**完全没采样**')
print(f'    （相差 {step_uni.max()/step_disp:.0f} 倍）')

# ---- 注入 ③（前馈）：对齐口径选错 ----
print('\\n注入 ③（前馈）：对齐口径选错')
z_gt = rng.uniform(1.0, 20.0, 3000); disp_gt = 1.0/z_gt
a_true, b_true = 3.7, 0.42
pred = a_true*disp_gt + b_true + rng.normal(0, 0.002, len(z_gt))
def align(p, g, mode):
    if mode == 'scale':
        return float((p @ g)/(p @ p))*p
    A = np.stack([p, np.ones_like(p)], 1)
    c, *_ = np.linalg.lstsq(A, g, rcond=None)
    return A @ c
def rel(p, g): return float(np.sqrt(np.mean((p-g)**2)/np.mean(g**2)))
e_s = rel(align(pred, disp_gt, 'scale'), disp_gt)
e_a = rel(align(pred, disp_gt, 'affine'), disp_gt)
print(f'  预测器是「视差域仿射意义上完美」的（真实模型就是这样）')
print(f'  纯尺度对齐: 相对 RMSE {e_s:.5f}')
print(f'  仿射对齐:   相对 RMSE {e_a:.5f}')
print(f'  ✓ 差 {e_s/e_a:.0f} 倍 —— 口径选错会把一个完美的模型报成很差的模型')
assert e_s/e_a > 50

# ---- 注入 ④（SDS）：CFG 大而学习率没跟着缩 ----
print('\\n注入 ④（SDS）：cfg 调大而 lr 不变')
print('  SDS 的梯度幅度随 cfg 近线性增长（模块 04 第 4 节量到 cfg=100 时 66 倍）')
print('  而稳定所需的 lr 上界随之反比缩小：')
for cfg, gmax in [(1.0, 0.994), (7.5, 5.228), (30.0, 19.882), (100.0, 65.475)]:
    print(f'    cfg={cfg:6.1f}: max|g| = {gmax:6.3f}   若 lr 固定为 0.25 -> '
          f'单步位移可达 {0.25*gmax:.2f}')
print('  ✓ cfg=100 时单步位移可达 16.4，而两个模式相距只有 4.0 -> 必然发散')
print('    （我第一次做这个实验时 400 步后 x 是 1e100）')"""),

md("""## 3 · 束调整的 Hessian：秩亏恰好是 7

而这 7 个方向不需要靠数值判秩去找 —— 它们是相似变换群的作用方向，有解析形式。"""),

code("""def R_to_w(R):
    th = np.arccos(np.clip((np.trace(R)-1)/2, -1, 1))
    if th < 1e-9: return np.zeros(3)
    v = np.array([R[2,1]-R[1,2], R[0,2]-R[2,0], R[1,0]-R[0,1]])
    return th*v/(2*np.sin(th))

def make_scene(nc=5, npt=40, arc_deg=60.0, radius=6.0, seed=0):
    '''相机在弧上、始终 look-at 场景中心。返回 (X, cams)。'''
    r = np.random.default_rng(seed)
    X = r.normal(0, 1.0, (npt, 3))
    cams = []
    for i in range(nc):
        a = np.deg2rad(arc_deg)*((i/(nc-1) - 0.5) if nc > 1 else 0.0)
        C = radius*np.array([np.sin(a), 0.0, -np.cos(a)])
        fwd = -C/np.linalg.norm(C)
        up = np.array([0., 1., 0.])
        rt = np.cross(up, fwd); rt /= np.linalg.norm(rt)
        R = np.stack([rt, np.cross(fwd, rt), fwd], 0)
        cams.append((R, -R @ C))
    return X, cams

def pack(X, cams):
    return np.concatenate([np.concatenate([R_to_w(R), t]) for R, t in cams] + [X.ravel()])

def observations(X, cams):
    obs = []
    for ci, (R, t) in enumerate(cams):
        P = (R @ X.T).T + t
        assert np.all(P[:, 2] > 1e-6), '所有点必须在所有相机前方'
        uv = np.stack([F*P[:, 0]/P[:, 2], F*P[:, 1]/P[:, 2]], 1)
        for pi in range(len(X)):
            obs.append((ci, pi, uv[pi]))
    return obs

def residual_fn(nc, npt, obs):
    def resid(p):
        cams = [(rodrigues(p[6*i:6*i+3]), p[6*i+3:6*i+6]) for i in range(nc)]
        X = p[6*nc:].reshape(npt, 3)
        out = []
        for ci, pi, uv in obs:
            R, t = cams[ci]
            q = R @ X[pi] + t
            out += [F*q[0]/q[2] - uv[0], F*q[1]/q[2] - uv[1]]
        return np.array(out)
    return resid

def num_jacobian(resid, p0, eps=1e-6):
    r0 = resid(p0)
    J = np.zeros((len(r0), len(p0)))
    for j in range(len(p0)):
        a = p0.copy(); a[j] += eps
        b = p0.copy(); b[j] -= eps
        J[:, j] = (resid(a) - resid(b))/(2*eps)
    return J

nc, npt = 5, 40
Xs, cams = make_scene(nc, npt)
obs = observations(Xs, cams)
resid = residual_fn(nc, npt, obs)
p0 = pack(Xs, cams)
print(f'参数 {len(p0)}（{nc}×6 相机 + {npt}×3 点）  观测 {len(obs)} 个 -> {2*len(obs)} 个残差')
print(f'在真解处的残差范数 {np.linalg.norm(resid(p0)):.3e}（应为 0）')
assert np.linalg.norm(resid(p0)) < 1e-9

J = num_jacobian(resid, p0)
H = J.T @ J
sv = np.linalg.svd(H, compute_uv=False)
ratios = sv[:-1]/np.maximum(sv[1:], 1e-300)
k = int(np.argmax(ratios))
print(f'\\nH 的形状 {H.shape}')
print(f'最大谱间隙在第 {k+1} 与第 {k+2} 个奇异值之间，比值 {ratios[k]:.3e}')
print(f'  第 {k+1} 个: {sv[k]:.4e}    第 {k+2} 个: {sv[k+1]:.4e}')
print(f'-> 有效秩 {k+1}，**秩亏 {len(p0)-(k+1)}**')
assert len(p0)-(k+1) == 7, f'秩亏应为 7，实测 {len(p0)-(k+1)}'
print(f'\\n✓ 秩亏恰好 7 —— 与第 1 节数出的 7 个不可观测自由度一致')
print(f'  而谱间隙 {ratios[k]:.1e} 说明这个「7」毫无歧义')"""),

code("""# 解析地构造那 7 个零方向：把相似变换作用在参数上求导
def apply_similarity(X, cams, om=None, dt=None, s=1.0):
    '''世界的相似变换：X' = s·R(om)·X + dt，相机跟着变使投影不变。'''
    om = np.zeros(3) if om is None else np.asarray(om, float)
    dt = np.zeros(3) if dt is None else np.asarray(dt, float)
    Rw = rodrigues(om)
    X2 = s*(X @ Rw.T) + dt
    out = []
    for R, t in cams:
        C = -R.T @ t
        R2 = R @ Rw.T
        out.append((R2, -R2 @ (s*(Rw @ C) + dt)))
    return X2, out

def gauge_basis(X, cams, h=1e-6):
    '''返回 (n_param, 7) 的正交基 Q，张成 gauge 零空间。'''
    cols = []
    for k in range(3):                      # 平移
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, dt=d))
                     - pack(*apply_similarity(X, cams, dt=-d)))/(2*h))
    for k in range(3):                      # 旋转
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, om=d))
                     - pack(*apply_similarity(X, cams, om=-d)))/(2*h))
    cols.append((pack(*apply_similarity(X, cams, s=1+h))     # 尺度
                 - pack(*apply_similarity(X, cams, s=1-h)))/(2*h))
    G = np.stack(cols, 1)
    Q, _ = np.linalg.qr(G)
    return G, Q

G, Q = gauge_basis(Xs, cams)
print(f'G 的形状 {G.shape}，秩 {np.linalg.matrix_rank(G, tol=1e-8)}')
names = ['平移x', '平移y', '平移z', '旋转x', '旋转y', '旋转z', '尺度']
Jn = np.linalg.norm(J)
print('\\n每个方向的 ||J v|| / ||J||（v 已单位化）：')
for i, nm in enumerate(names):
    print(f'  {nm}: {np.linalg.norm(J @ Q[:, i])/Jn:.3e}')
tot = np.linalg.norm(J @ Q)/Jn
print(f'\\n整个 7 维零空间: ||J Q||_F / ||J||_F = {tot:.3e}')
assert tot < 1e-9, f'解析零空间必须精确，实测 {tot:.3e}'
assert np.linalg.matrix_rank(G, tol=1e-8) == 7
print('\\n✓ 解析构造的 7 个方向精确地在零空间里（1e-11 量级，纯数值噪声）')
print('  所以**不需要**靠数值判秩去找它们 —— 这一点在条件数大时至关重要（模块 01 第 4 节）')

# 判秩：光看「最大谱间隙」是不够的 —— 满秩矩阵的谱里也有最大间隙
def rank_def(Hs, gap_thresh=1e6):
    '''返回 (秩亏, 有效条件数, 最大间隙比值)。
    只有当间隙**同时**足够大（>gap_thresh）时才认为存在秩的悬崖。'''
    s = np.linalg.svd(Hs, compute_uv=False)
    r = s[:-1]/np.maximum(s[1:], 1e-300)
    kk = int(np.argmax(r))
    if r[kk] < gap_thresh:
        return 0, float(s[0]/s[-1]), float(r[kk])      # 没有悬崖 -> 满秩
    return Hs.shape[0]-(kk+1), float(s[0]/s[kk]), float(r[kk])

n = H.shape[0]
print('\\n固定 gauge 的几种做法（判秩用「间隙 > 1e6」）：')
print(' 情形                        秩亏   条件数      最大间隙比值')
_cases = [('不固定', []),
          ('固定相机 0（6 个）', list(range(6))),
          ('固定相机 0 + 一点一坐标（7）', list(range(6))+[6*nc]),
          ('固定两个点的 6 个坐标', [6*nc+i for i in range(6)]),
          ('固定三个点的 9 个坐标', [6*nc+i for i in range(9)]),
          ('固定相机 0 与相机 1（12）', list(range(12)))]
_out = {}
for tag, fx in _cases:
    keep = [i for i in range(n) if i not in set(fx)]
    rd, cond, gap = rank_def(H[np.ix_(keep, keep)])
    _out[tag] = rd
    print(f' {tag:28s} {rd:3d}   {cond:.3e}   {gap:.3e}')

assert _out['不固定'] == 7
assert _out['固定相机 0（6 个）'] == 1, '只固定第一个相机时尺度还自由'
assert _out['固定相机 0 + 一点一坐标（7）'] == 0
assert _out['固定两个点的 6 个坐标'] == 1, '绕两点连线的旋转仍自由'
assert _out['固定三个点的 9 个坐标'] == 0
print('\\n✓ 只固定第一个相机是**不够**的 —— 尺度仍会随机漂移（注入 ① 的机制）')
print('✓ 而「固定两个点的 6 个坐标」也不够：秩亏仍是 1 ——')
print('  因为绕这两点连线的旋转不改变它们的坐标。要用点固定 gauge 需要**三个不共线的点**。')
print()
print('⚠ 注意这里的判秩加了一个「间隙必须 > 1e6」的条件，而这不是可选的：')
print('  满秩矩阵的谱里也有一个「最大间隙」（上表里是 2~4 倍）。')
print('  只取 argmax 而不看间隙大小，会把满秩矩阵误判成有秩亏 ——')
print('  我第一次写这一格时就是这么错的（把「固定 7 个」的情形报成了秩亏 2）。')"""),

md("""## 4 · 四条路线的规模账"""),

code("""print('=== ① SfM ===')
print(' 图像数    两两对数      10ms/对 的耗时     词汇树 top-50 的候选对（占比）')
for N in [100, 500, 2000, 10000]:
    P = N*(N-1)//2
    vt = N*50//2
    print(f' {N:6d}  {P:11,d}   {P*0.01/3600:8.2f} 小时   {vt:9,d} ({vt/P:6.2%})')
assert 500*499//2 == 124750

print('\\n束调整的参数规模：')
print(' 相机   点数      总参数     稠密 H 的元素数   Schur 补的加速比')
for ncm, npts in [(100, 30_000), (500, 100_000), (2000, 500_000)]:
    tot = ncm*6 + npts*3
    full = tot**3; cam = (ncm*6)**3; pts = npts*27
    print(f' {ncm:5d}  {npts:8d}  {tot:9,d}   {tot**2/1e9:8.2f} G       {full/(cam+pts):.2e}')

print('\\n=== ② MVS ===')
print(' 分辨率 × D          代价体元数     fp32 内存')
for W, H_, D in [(640, 480, 64), (1280, 720, 128), (1920, 1080, 256)]:
    print(f' {W}x{H_} x {D:3d}     {W*H_*D/1e6:8.1f} M    {W*H_*D*4/1e9:6.3f} GB')
print('\\n所需深度假设数 D = f·B·(1/zmin - 1/zmax)：')
for f_, B_, z0, z1 in [(700, 0.12, 0.5, 50), (1200, 0.5, 2.0, 80), (500, 6.0, 3.0, 20)]:
    D_ = int(np.ceil(f_*B_*(1/z0 - 1/z1))) + 1
    print(f'  f={f_:5.0f} B={B_:4.2f} [{z0},{z1}] m -> D = {D_}')
assert int(np.ceil(700*0.12*(1/0.5 - 1/50)))+1 == 168

print('\\n=== ③ 前馈 ===')
print(' 输出表示         自由度      真正需要的      冗余')
for HH, WW in [(384, 512)]:
    for tag, dof in [('深度图', HH*WW), ('点图', 3*HH*WW), ('高斯(14/px)', 14*HH*WW)]:
        need = HH*WW + 1
        print(f' {tag:14s} {dof:10,d}  {need:10,d}   {dof/need:6.2f}×')
assert abs(3*384*512/(384*512+1) - 3.0) < 1e-4

print('\\n=== ④ SDS ===')
print(' 每个资产的成本对比（量级，非实测）：')
print('   SDS 逐场景优化      几十分钟（几千次渲染 + 几千次扩散前向）')
print('   多视角扩散 + 重建    一次采样（几十秒）+ 一次快速重建')
print('   前馈重建 (LRM 类)   一次前向（秒级）')
print('\\n✓ 三个数量级的差别 —— 而它们的输入条件与输出质量各不相同（模块 04 第 7 节）')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 相似变换下投影不变

实现 `apply_sim(X, R, t, om, dt, s)`：对世界做相似变换
$X' = s\\,R(om)\\,X + dt$，并**相应地**改变相机 $(R, t)$，使投影完全不变。

提示：相机中心 $C = -R^\\top t$，变换后 $C' = s\\,R(om)\\,C + dt$、$R' = R\\,R(om)^\\top$。"""),

code("""def apply_sim(X, R, t, om=None, dt=None, s=1.0):
    '''返回 (X_new, R_new, t_new)，使 project(X_new, R_new, t_new) == project(X, R, t)。'''
    # TODO: Rw = rodrigues(om)（om 为 None 时是单位阵）
    #       X_new = s*(X @ Rw.T) + dt
    #       C = -R.T @ t ;  C_new = s*(Rw @ C) + dt ;  R_new = R @ Rw.T
    #       t_new = -R_new @ C_new
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_rg = np.random.default_rng(3)
_X = _rg.normal(0, 1, (150, 3)) + np.array([0, 0, 7.0])
_R = rodrigues(np.array([0.05, -0.1, 0.02]))
_t = np.array([0.2, -0.3, 0.1])
_uv0 = project(_X, _R, _t)

# ① 恒等变换
_Xa, _Ra, _ta = apply_sim(_X, _R, _t)
assert np.allclose(_Xa, _X) and np.allclose(_Ra, _R) and np.allclose(_ta, _t)

# ② 七个方向各自单独作用，投影都不变
_cases = [('平移', dict(dt=np.array([1.0, -2.0, 0.5]))),
          ('旋转', dict(om=np.array([0.1, -0.2, 0.35]))),
          ('尺度', dict(s=3.7)),
          ('尺度(小)', dict(s=0.02)),
          ('组合', dict(om=np.array([-0.3, 0.1, 0.2]), dt=np.array([-1.0, 4.0, 2.0]), s=0.4))]
for _tag, _kw in _cases:
    _Xn, _Rn, _tn = apply_sim(_X, _R, _t, **_kw)
    _d = np.abs(project(_Xn, _Rn, _tn) - _uv0).max()
    assert _d < 1e-7, f'{_tag}: 最大像素差 {_d:.3e}'

# ③ R_new 必须还是旋转矩阵
_Xn, _Rn, _tn = apply_sim(_X, _R, _t, om=np.array([0.4, 0.1, -0.3]), s=2.0)
assert np.allclose(_Rn @ _Rn.T, np.eye(3), atol=1e-12)
assert abs(np.linalg.det(_Rn) - 1.0) < 1e-12

# ④ 尺度确实改变了 3D 结构（不是什么都没做）
_Xn, _, _ = apply_sim(_X, _R, _t, s=5.0)
assert abs(np.linalg.norm(_Xn - _Xn.mean(0))/np.linalg.norm(_X - _X.mean(0)) - 5.0) < 1e-9

# ⑤ 大尺度跨度下仍然精确
for _s in [1e-4, 1e4]:
    _Xn, _Rn, _tn = apply_sim(_X, _R, _t, s=_s)
    assert np.abs(project(_Xn, _Rn, _tn) - _uv0).max() < 1e-6, f's={_s}'
print(f'✓ 练习 1 通过：5 类变换 + 尺度跨 8 个数量级，投影差都 < 1e-6')
print(f'  而 3D 结构确实被改变了（尺度 5.0 时点云直径变 5.0 倍）')"""),

md("""### 📖 参考答案 1"""),

code("""def apply_sim(X, R, t, om=None, dt=None, s=1.0):
    om = np.zeros(3) if om is None else np.asarray(om, float)
    dt = np.zeros(3) if dt is None else np.asarray(dt, float)
    Rw = rodrigues(om)
    X_new = s*(np.asarray(X, float) @ Rw.T) + dt
    C = -np.asarray(R, float).T @ np.asarray(t, float)
    C_new = s*(Rw @ C) + dt
    R_new = np.asarray(R, float) @ Rw.T
    return X_new, R_new, -R_new @ C_new

print('参考答案 1 已定义')
print('要点一：`X @ Rw.T` 与 `Rw @ X.T` 是转置关系 —— 写反了会得到逆旋转。')
print('       自测 ② 的「组合」那一项专门抓这个：单独的旋转写反可能仍然通过，')
print('       但与平移组合时顺序错就会暴露。')
print('要点二：相机要变的是**中心** C 而不是 t。直接对 t 做相似变换是错的，')
print('       因为 t = -R·C 里的 R 也在变。')
print('要点三：这 7 个方向就是束调整 Hessian 的零空间（第 3 节）。')
print('       所以这道题写对了，就等于会构造 gauge 零空间了（模块 01 练习 2）。')"""),

md("""### ✏️ 练习 2 · 深度假设的两种采样

实现 `hypotheses(f, B, zmin, zmax, D, mode)`：返回 `D` 个深度假设（升序）。
`mode='depth'` 在深度上均匀，`mode='disparity'` 在视差上均匀。
再实现 `max_disp_step(f, B, hyps)`：相邻假设之间**视差**步长的最大值。"""),

code("""def hypotheses(f, B, zmin, zmax, D, mode='disparity'):
    '''返回 D 个深度假设（升序的 ndarray）。'''
    # TODO: mode=='depth'     -> np.linspace(zmin, zmax, D)
    #       mode=='disparity' -> 在 [f*B/zmax, f*B/zmin] 上均匀取 D 个视差，
    #                            再换回深度 z = f*B/d，注意结果要升序
    raise NotImplementedError

def max_disp_step(f, B, hyps):
    '''相邻假设之间视差步长的最大值。'''
    # TODO: d = f*B/hyps ; 返回 np.abs(np.diff(d)).max()
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_f, _B, _z0, _z1 = 700.0, 0.12, 0.5, 50.0
for _D in [16, 64, 256]:
    _hd = hypotheses(_f, _B, _z0, _z1, _D, 'depth')
    _hp = hypotheses(_f, _B, _z0, _z1, _D, 'disparity')
    # ① 形状与范围
    for _h in (_hd, _hp):
        assert _h.shape == (_D,), f'形状 {_h.shape}'
        assert np.all(np.diff(_h) > 0), '必须升序'
        assert abs(_h[0]-_z0) < 1e-9 and abs(_h[-1]-_z1) < 1e-9, '端点必须是 zmin/zmax'
    # ② 深度均匀：深度步长恒定
    assert np.allclose(np.diff(_hd), (_z1-_z0)/(_D-1)), 'depth 模式的深度步长应恒定'
    # ③ 视差均匀：视差步长恒定
    _dp = _f*_B/_hp
    assert np.allclose(np.abs(np.diff(_dp)), np.abs(_dp[1]-_dp[0])), \\
        'disparity 模式的视差步长应恒定'

# ④ 关键对比：D=64 时深度均匀的近场步长应超过 100 px
_hd64 = hypotheses(_f, _B, _z0, _z1, 64, 'depth')
_hp64 = hypotheses(_f, _B, _z0, _z1, 64, 'disparity')
_s_d = max_disp_step(_f, _B, _hd64)
_s_p = max_disp_step(_f, _B, _hp64)
assert _s_d > 100.0, f'深度均匀的最大步长应 >100 px，实测 {_s_d:.2f}'
assert _s_p < 3.0, f'视差均匀的步长应 <3 px，实测 {_s_p:.3f}'
assert _s_d/_s_p > 30, f'两者应差 30 倍以上，实测 {_s_d/_s_p:.1f}'

# ⑤ 视差均匀时，D 翻倍步长减半
_a = max_disp_step(_f, _B, hypotheses(_f, _B, _z0, _z1, 64, 'disparity'))
_b = max_disp_step(_f, _B, hypotheses(_f, _B, _z0, _z1, 128, 'disparity'))
assert abs(_a/_b - (127/63)) < 0.05, '视差均匀时步长应 ∝ 1/(D-1)'

# ⑥ 与闭式公式一致：视差跨度 / (D-1)
_span = _f*_B*(1/_z0 - 1/_z1)
assert abs(_s_p - _span/63) < 1e-9, '应等于视差跨度/(D-1)'
print(f'✓ 练习 2 通过：D=64 时深度均匀 {_s_d:.1f} px vs 视差均匀 {_s_p:.3f} px'
      f'（差 {_s_d/_s_p:.0f} 倍）；闭式核对通过')"""),

md("""### 📖 参考答案 2"""),

code("""def hypotheses(f, B, zmin, zmax, D, mode='disparity'):
    if mode == 'depth':
        return np.linspace(zmin, zmax, D)
    if mode == 'disparity':
        d = np.linspace(f*B/zmax, f*B/zmin, D)     # 视差升序 = 深度降序
        return (f*B/d)[::-1].copy()                # 反过来得到深度升序
    raise ValueError(mode)

def max_disp_step(f, B, hyps):
    d = f*B/np.asarray(hyps, float)
    return float(np.abs(np.diff(d)).max())

print('参考答案 2 已定义')
print('要点一：视差与深度是**反序**的（视差升序 = 深度降序），所以要 [::-1]。')
print('       忘了这一步会得到降序的深度，而下游的 assert 会立刻抓到。')
print('要点二：视差均匀时步长有闭式 = f·B·(1/zmin - 1/zmax)/(D-1)（自测 ⑥）。')
print('       所以「要 ≤1 px 的步长需要多少个假设」可以直接反解 —— 不用试。')
print('要点三：为什么必须在视差上均匀 —— 因为视差是被**测量**的量，')
print('       让每个假设承担相同的视差跨度 = 让每个假设承担相同的信息量。')"""),

md("""### ✏️ 练习 3 · 三种对齐口径

实现 `align_and_score(pred, disp_gt, mode)`：
`mode ∈ {'none', 'scale', 'affine'}`，返回 `(视差域相对 RMSE, 深度域 AbsRel 中位数)`。

`'scale'` 用最小二乘的单参数拟合 $\\min_a \\Vert a\\,p - g\\Vert^2$；
`'affine'` 用两参数 $\\min_{a,b}\\Vert a\\,p + b - g\\Vert^2$。"""),

code("""def align_and_score(pred, disp_gt, mode):
    '''返回 (视差域相对 RMSE, 深度域 AbsRel 中位数)。'''
    # TODO: 1) 按 mode 求对齐后的视差 al
    #          none   -> al = pred
    #          scale  -> a = (pred·gt)/(pred·pred); al = a*pred
    #          affine -> lstsq 拟合 [pred, 1] -> al
    #       2) e_disp = sqrt(mean((al-gt)²) / mean(gt²))
    #       3) z_pred = 1/clip(al, 1e-6, None) ; z_gt = 1/disp_gt
    #          e_depth = median(|z_pred - z_gt| / z_gt)
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_r3 = np.random.default_rng(0)
_zg = _r3.uniform(1.0, 20.0, 3000); _dg = 1.0/_zg
_p_af = 3.7*_dg + 0.42 + _r3.normal(0, 0.002, len(_zg))     # 视差域仿射完美
_p_sc = 3.7*_dg + _r3.normal(0, 0.002, len(_zg))            # 只差一个尺度

_res = {m: align_and_score(_p_af, _dg, m) for m in ['none', 'scale', 'affine']}
for _m, (_ed, _ez) in _res.items():
    assert _ed >= 0 and _ez >= 0

# ① 仿射对齐应把「仿射完美」的预测器还原到 <1%
assert _res['affine'][0] < 0.01, f'仿射对齐应 <0.01，实测 {_res["affine"][0]:.5f}'
# ② 而纯尺度对齐差 50 倍以上
assert _res['scale'][0] / _res['affine'][0] > 50, \\
    f'比值应 >50，实测 {_res["scale"][0]/_res["affine"][0]:.1f}'
# ③ 不对齐最差
assert _res['none'][0] > _res['scale'][0] > _res['affine'][0]

# ④ 对「只差尺度」的预测器，两种对齐应几乎相同
_r2 = {m: align_and_score(_p_sc, _dg, m) for m in ['scale', 'affine']}
assert abs(_r2['scale'][0] - _r2['affine'][0]) / _r2['affine'][0] < 0.1, \\
    '没有位移项时两种对齐应接近'

# ⑤ 位移项越大，纯尺度对齐越糟（单调）
_prev = 0.0
for _b in [0.0, 0.05, 0.42, 2.0]:
    _p = 3.7*_dg + _b + _r3.normal(0, 0.002, len(_zg))
    _e = align_and_score(_p, _dg, 'scale')[0]
    assert _e >= _prev - 1e-9, '应随 b 单调变差'
    _prev = _e
# ⑥ 深度域指标同向
assert _res['affine'][1] < _res['scale'][1] < _res['none'][1]
print(f'✓ 练习 3 通过：仿射 {_res["affine"][0]:.5f} vs 尺度 {_res["scale"][0]:.5f}'
      f'（差 {_res["scale"][0]/_res["affine"][0]:.0f} 倍）；'
      f'深度域 AbsRel {_res["affine"][1]:.5f} vs {_res["scale"][1]:.5f}')"""),

md("""### 📖 参考答案 3"""),

code("""def align_and_score(pred, disp_gt, mode):
    p = np.asarray(pred, float); g = np.asarray(disp_gt, float)
    if mode == 'none':
        al = p
    elif mode == 'scale':
        al = float((p @ g)/(p @ p)) * p
    elif mode == 'affine':
        A = np.stack([p, np.ones_like(p)], 1)
        c, *_ = np.linalg.lstsq(A, g, rcond=None)
        al = A @ c
    else:
        raise ValueError(mode)
    e_disp = float(np.sqrt(np.mean((al - g)**2) / np.mean(g**2)))
    z_pred = 1.0/np.clip(al, 1e-6, None)
    z_gt = 1.0/g
    e_depth = float(np.median(np.abs(z_pred - z_gt)/z_gt))
    return e_disp, e_depth

print('参考答案 3 已定义')
print('要点一：clip(al, 1e-6, None) 不是装饰 —— 对齐后的视差可能为负或零，')
print('       而那时 1/al 会给出负深度或 inf。真实评测里这些像素通常被直接剔除。')
print('要点二：`none` 那一档的意义是「如果一个模型声称直接输出米」。')
print('       它的误差是 4.2（420%）—— 所以任何报「相对指标很好」的模型，')
print('       都不能推断它的绝对尺度也好。')
print('要点三：这道题只测了「视差域」这一个维度。模块 03 会加上另外两个：')
print('       对齐**域**（视差 vs 深度）与**逐图还是全局** —— 三者各值一到两个数量级。')"""),

md("""### ✏️ 练习 4 · 数出 gauge 的维数

实现 `gauge_rank_deficiency(nc, npt, arc_deg, fixed)`：
构造一个场景、算数值雅可比、返回 `(秩亏, 谱间隙)`。
`fixed` 是要**从参数里去掉**的全局索引列表（模拟「固定这些参数」）。

判秩请用**最大谱间隙**（相邻奇异值比值最大处），不要用固定阈值。"""),

code("""def gauge_rank_deficiency(nc, npt, arc_deg=60.0, fixed=(), seed=0, gap_thresh=1e6):
    '''返回 (秩亏, 最大谱间隙的比值)。'''
    # TODO: 1) X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    #       2) obs = observations(X, cams); resid = residual_fn(nc, npt, obs)
    #       3) J = num_jacobian(resid, pack(X, cams)); H = J.T @ J
    #       4) 若 fixed 非空，把这些行列从 H 里去掉
    #       5) sv = svd(H); ratios = sv[:-1]/sv[1:]; k = argmax(ratios)
    #       6) **关键**：只有 ratios[k] > gap_thresh 时才算存在秩亏；
    #          否则返回 (0, ratios[k])。满秩矩阵的谱里也有「最大间隙」（2~4 倍）。
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
# ① 不固定任何参数 -> 秩亏 7
_rd, _gap = gauge_rank_deficiency(5, 40)
assert _rd == 7, f'秩亏应为 7，实测 {_rd}'
assert _gap > 1e8, f'谱间隙应很大，实测 {_gap:.2e}'

# ② 换场景规模，秩亏仍是 7（它是群的维数，与规模无关）
for _nc, _npt in [(4, 25), (6, 50), (5, 80)]:
    _r, _g = gauge_rank_deficiency(_nc, _npt)
    assert _r == 7, f'nc={_nc} npt={_npt}: 秩亏 {_r}'
    assert _g > 1e6

# ③ 固定相机 0 的 6 个参数 -> 秩亏 1（尺度还自由）
_rd1, _ = gauge_rank_deficiency(5, 40, fixed=list(range(6)))
assert _rd1 == 1, f'只固定相机 0 时秩亏应为 1，实测 {_rd1}'

# ④ 再固定一个点坐标 -> 秩亏 0
_rd0, _ = gauge_rank_deficiency(5, 40, fixed=list(range(6)) + [5*6])
assert _rd0 == 0, f'固定 7 个自由度后秩亏应为 0，实测 {_rd0}'

# ⑤ 固定 6 个**点**坐标（而不是相机）也能去掉 6 个自由度吗？
_rd_pts, _ = gauge_rank_deficiency(5, 40, fixed=[5*6 + i for i in range(6)])
print(f'  固定两个点的全部 6 个坐标 -> 秩亏 {_rd_pts}')
assert _rd_pts == 1, '两个点定不了旋转的第三个自由度（绕两点连线的旋转仍自由）'

# ⑥ 固定三个点（9 个坐标）应当足够
_rd_p3, _ = gauge_rank_deficiency(5, 40, fixed=[5*6 + i for i in range(9)])
assert _rd_p3 == 0, f'固定三个点应去掉全部 7 个，实测秩亏 {_rd_p3}'
print(f'✓ 练习 4 通过：自由 7 / 固定相机0 → 1 / 再固定一坐标 → 0 /'
      f' 固定两点 → {_rd_pts} / 固定三点 → 0')"""),

md("""### 📖 参考答案 4"""),

code("""def gauge_rank_deficiency(nc, npt, arc_deg=60.0, fixed=(), seed=0, gap_thresh=1e6):
    X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    obs = observations(X, cams)
    resid = residual_fn(nc, npt, obs)
    J = num_jacobian(resid, pack(X, cams))
    Hm = J.T @ J
    if len(fixed):
        keep = [i for i in range(Hm.shape[0]) if i not in set(fixed)]
        Hm = Hm[np.ix_(keep, keep)]
    sv = np.linalg.svd(Hm, compute_uv=False)
    ratios = sv[:-1]/np.maximum(sv[1:], 1e-300)
    k = int(np.argmax(ratios))
    if ratios[k] < gap_thresh:
        return 0, float(ratios[k])
    return Hm.shape[0] - (k+1), float(ratios[k])

print('参考答案 4 已定义')
print('要点一：秩亏 7 与场景规模无关（自测 ②）—— 因为它是**群的维数**，')
print('       而不是某个矩阵的偶然性质。')
print('要点二：自测 ⑤ 是这道题最有意思的一档。固定两个点（6 个坐标）只去掉 6 个')
print('       自由度里的 6 个吗？不 —— 绕这两点连线的旋转仍然自由，所以秩亏是 1。')
print('       要用点来固定 gauge，需要**三个不共线的点**（自测 ⑥）。')
print('要点三：判秩需要**两个**条件，而不是一个。')
print('       ① 用谱间隙而不是固定阈值 —— 模块 01 第 4 节会说明为什么：')
print('          在条件数大的配置上，固定相对阈值会报出「秩亏 143/150」这种荒谬结果；')
print('       ② 而间隙本身也要够大（这里用 1e6）—— 否则满秩矩阵谱里那个 2~4 倍的')
print('          「最大间隙」会被误判成秩的悬崖。')
print('       我第一次写第 3 节那一格时漏了 ②，于是把「已固定 7 个自由度」的满秩情形')
print('       报成了秩亏 2。所以这两个条件都不是可选的。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- ① SfM：COLMAP ----
# colmap feature_extractor --database_path db.db --image_path images/
# colmap exhaustive_matcher --database_path db.db          # 或 vocab_tree_matcher（第 4 节）
# colmap mapper --database_path db.db --image_path images/ --output_path sparse/
# 产物 sparse/0/{cameras,images,points3D}.bin 就是 C74 的 3DGS 的输入
#
# gauge：COLMAP 内部固定第一个相机 + 一个尺度基准（对应练习 4 的 fixed=range(6)+[...]）
# 而导出的位姿是任意 gauge 下的 —— 所以两次运行的重建可以相差一个相似变换

# ---- ② MVS：COLMAP 的稠密阶段 / OpenMVS ----
# colmap image_undistorter --image_path images/ --input_path sparse/0 --output_path dense/
# colmap patch_match_stereo --workspace_path dense/     # PatchMatch（斜面假设，模块 02 第 4 节）
# colmap stereo_fusion --workspace_path dense/ --output_path dense/fused.ply
# 注意 patch_match_stereo 的 --PatchMatchStereo.depth_min/max 就是练习 2 的 zmin/zmax

# ---- ③ 前馈：DUSt3R / MASt3R ----
# pip install "dust3r @ git+https://github.com/naver/dust3r"
from dust3r.inference import inference
from dust3r.cloud_opt import global_aligner, GlobalAlignerMode
output = inference(pairs, model, device, batch_size=1)
scene = global_aligner(output, device=device, mode=GlobalAlignerMode.PointCloudOptimizer)
scene.compute_global_alignment(init="mst", niter=300, schedule="cosine", lr=0.01)
# compute_global_alignment 就是模块 03 第 5 节那次「秩亏 7」的束调整
focals = scene.get_focals()      # 内参是**输出**而不是输入（模块 03 第 4 节）

# ---- ④ 生成：threestudio ----
# python launch.py --config configs/dreamfusion-if.yaml --train \
#   system.prompt_processor.prompt="a DSLR photo of a corgi"
# 关键超参（模块 04 第 4、5 节）：
#   system.guidance.guidance_scale=100        <- CFG，注意配合 lr
#   system.guidance.min_step_percent=0.02     <- t 的下界，**必须小**
#   system.guidance.max_step_percent=0.98     <- t 的上界，通常退火
```

**四条路线的第一诊断**

| 现象 | 哪条路线 | 先查什么 | 依据 |
|---|---|---|---|
| 每次跑重建大小都不一样 | ① | gauge 是否固定了全部 7 个 | 只固定第一个相机时秩亏还是 1 |
| 近处的深度全是噪声 | ② | 深度假设是否在视差上均匀 | 深度均匀时近场步长 102.7 px |
| 相对指标很好但绝对深度差很多 | ③ | 对齐口径（域 / 自由度 / 逐图） | 三者各值一到两个数量级 |
| 训练几百步后 NaN | ④ | cfg 与 lr 是否配套 | 梯度幅度随 cfg 近线性增长 |
| 重建断成几块 | ① | 匹配候选是否漏了关键对 | 词汇树 top-50 只覆盖 0.5% 的对 |
| 生成的东西「太中庸」 | ④ | $t$ 的采样范围与 $w(t)$ | 不动点内移 21.7% |"""),
]
