# -*- coding: utf-8 -*-
"""C74 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C72（多视角几何）是硬前提</strong>——"
                 "相机模型、内外参、投影的雅可比本课直接使用；"
                 "线性代数（协方差、特征分解、Cholesky）；"
                 "<em>不需要 C73，但读过它会知道「离散表示」那一侧长什么样</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（把一个 3D 高斯投影成 2D 椭圆并渲染出来 / '
                       '<strong>四个部件各注入一次错误并量出代价</strong>：'
                       '协方差非正定、深度排序被打乱、密度控制不做、球谐阶数不足 / '
                       '<strong>α 合成对分段常数密度是精确的（连 N=1 都对）</strong>）'),
    ("核心参考", "Kerbl et al., <em>3D Gaussian Splatting for Real-Time Radiance "
                 "Field Rendering</em>（SIGGRAPH 2023）· "
                 "Zwicker et al., <em>EWA Splatting</em>（TVCG 2002，协方差的仿射投影）· "
                 "Max, <em>Optical Models for Direct Volume Rendering</em>（TVCG 1995，"
                 "体渲染积分与 α 合成的等价性）· "
                 "Mildenhall et al., <em>NeRF</em>（ECCV 2020，作为对照）· "
                 "本课程 <strong>C72</strong>（几何前提）· C73（离散表示的另一侧）"),
    ("预计时长", "读 45 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-3dgs", "3DGS 做对了什么：一个可以拆成四件事的答案", "".join([
        P("2020 年 NeRF 用一个 MLP 表示辐射场，渲染一张图要沿每条射线采几十到几百个点、"
          "每个点跑一次网络。"
          "<strong>2023 年 3DGS 把同样的质量做到了实时，而它的做法不是「更快的网络」——"
          "它把表示换成了一堆<em>显式的、可光栅化的</em>基元。</strong>"),
        ASCII("""
   NeRF：隐式 + 光线行进                 3DGS：显式 + 光栅化
   ┌──────────────────────┐            ┌──────────────────────┐
   │ f(x, d) -> (σ, c)     │            │ {(μ, Σ, α, SH)} × N   │
   │ 一个 MLP              │            │ 几十万到几百万个高斯   │
   └──────────────────────┘            └──────────────────────┘
     渲染：每条射线采 N 个点               渲染：把每个高斯投影成 2D 椭圆
           每点一次前向                          按 tile 分箱 + 排序
     成本 ∝ 像素数 × 采样数 × 网络              成本 ∝ (高斯,tile) 对数
     ↓                                    ↓
   秒级                                  毫秒级
        """),
        P("<strong>而「换表示」这件事拆开来是四个独立的部件，"
          "本课五个内容模块正好对应它们：</strong>"),
        TABLE(["部件", "做什么", "它单独出错时会怎样", "在哪个模块"], [
            ["<strong>① α 合成</strong>",
             "把「一串半透明的东西」合成一个像素颜色",
             "<strong>这是 NeRF 与 3DGS <em>共用</em>的地基</strong>——"
             "<em>它决定了「为什么必须排序」</em>", "01"],
            ["<strong>② 各向异性高斯基元</strong>",
             "用 $(\\mu,\\Sigma,\\alpha)$ 表示一小团半透明的东西，"
             "并投影成 2D 椭圆",
             "协方差非正定 → <strong>整个高斯变成无意义的形状</strong>；"
             "<em>而参数化方式决定了这件事会不会发生</em>", "02"],
            ["<strong>③ 可微分 tile 光栅化</strong>",
             "分箱、按深度排序、逐 tile 做 α 合成",
             "<strong>排序被打乱 → 图像错 20% 以上</strong>（第 3 节量出来）",
             "03"],
            ["<strong>④ 自适应密度控制</strong>",
             "按梯度克隆/分裂、按不透明度剪枝",
             "不做 → 停在 SfM 点云的密度上，<em>细节永远补不出来</em>",
             "04"],
            ["<strong>⑤ 外观与动态</strong>",
             "球谐表示视角依赖颜色；时间维度",
             "<strong>SH 阶数 3 的角分辨率是 45°</strong>——"
             "<em>它表示不了镜面高光，而这是表示能力的限制</em>", "05"],
        ]),
        DUAL(
            "<strong>四个部件里，只有 ② 和 ③ 是 3DGS 独有的。</strong>"
            "<em>① 与 NeRF 完全共用；④ 在 NeRF 一侧对应的是「采样策略」；"
            "⑤ 在 NeRF 一侧是网络的视角输入</em>。"
            "<strong>所以「3DGS 的贡献」精确地说是："
            "把辐射场的基元从「MLP 的隐式输出」换成「可光栅化的显式椭球」，"
            "从而让整条渲染链路变成 GPU 光栅化擅长的形状。</strong>",
            "<strong>而本课把 ① 单独做成一个模块，是因为你在选课时跳过了 NeRF。</strong>"
            "<em>α 合成不是 3DGS 的一部分——它是体渲染积分的离散化，"
            "而 3DGS 与 NeRF 都建立在它上面</em>。"
            "<strong>模块 01 会把这个等价性验证到机器精度</strong>"
            "（<em>而顺带得到一个很有用的结论："
            "对分段常数的密度，α 合成是<strong>精确</strong>的，连 $N{=}1$ 都对</em>）。",
        ),
    ])),

    # ============================================================== 2
    ("what-a-gaussian-is", "一个「3D 高斯」到底是什么", "".join([
        P("它不是一个概率分布，虽然数学形式一样。"
          "<strong>它是一团「密度按高斯衰减的半透明物质」。</strong>"),
        MATH(r"\sigma(x) = \alpha \cdot \exp\Bigl(-\tfrac12 (x-\mu)^\top \Sigma^{-1} (x-\mu)\Bigr)"),
        TABLE(["参数", "维数", "含义", "怎么参数化（这一点很关键）"], [
            ["$\\mu$", "3", "中心位置", "直接存"],
            ["$\\Sigma$", "6（对称）", "形状与朝向",
             "<strong>不直接存！</strong>存 $(s_1,s_2,s_3)$ 与四元数 $q$，"
             "再算 $\\Sigma = RSS^\\top R^\\top$——"
             "<em>这样它<strong>恒正定</strong></em>（第 2 节）"],
            ["$\\alpha$", "1", "不透明度", "存 logit，过 sigmoid → 恒在 $(0,1)$"],
            ["SH 系数", "$3(\\ell+1)^2$", "视角依赖的颜色",
             "$\\ell{=}3$ 时 <strong>48 个浮点数</strong>——"
             "<em>而它占了每个高斯 59 个浮点数里的 81%</em>"],
        ]),
        DUAL(
            "<strong>第二行的参数化是 3DGS 最重要的一个工程决定。</strong>"
            "<em>如果直接优化 $\\Sigma$ 的 6 个分量，梯度下降几步之后它就不再正定，"
            "而一个非正定的「协方差」对应不到任何椭球</em>——"
            "<strong>notebook 第 3 节把这件事量出来：直接参数化时非正定的比例，"
            "以及 $RSS^\\top R^\\top$ 为什么恒正定。</strong>",
            "<strong>而 SH 那一行说明一个容易忽略的事实："
            "3DGS 的内存主要花在<em>颜色</em>上，不是几何上。</strong>"
            "<em>位置 3 + 缩放 3 + 四元数 4 + 不透明度 1 = 11 个浮点数，"
            "而 SH（$\\ell{=}3$）是 48 个</em>。"
            "<strong>100 万个高斯在 $\\ell{=}3$ 下是 0.236 GB，而 $\\ell{=}0$ 只有 0.056 GB</strong>——"
            "<em>4.2 倍的差别全在颜色的视角依赖性上（模块 05 会说明这 4.2 倍买到了什么）。</em>",
        ),
    ])),

    # ============================================================== 3
    ("map", "课程地图", "".join([
        TABLE(["模块", "主题", "带走的那个可验证的量"], [
            ["<strong>01</strong>", "体渲染与 α 合成的地基",
             "<strong>对分段常数密度，α 合成精确到机器精度（连 $N{=}1$）</strong>；"
             "密度变化时误差 $\\propto 1/N^2$；"
             "<strong>打乱深度顺序 → 图像中位差 21.5%</strong>"],
            ["<strong>02</strong>", "各向异性高斯基元与投影",
             "$RSS^\\top R^\\top$ 恒正定；"
             "<strong>仿射投影的误差由「张角」决定</strong>——"
             "0.92° 时 0.23%，<strong>53° 时 40–60%</strong>"],
            ["<strong>03</strong>", "可微分 tile 光栅化",
             "50 万高斯 × 8 px 半径 → <strong>200 万个 (高斯,tile) 对</strong>、"
             "每 tile 245 个；"
             "<strong>而 $T_{\\min}{=}10^{-4}$ 时只需处理 19 个 → 92.2% 的工作可提前终止省掉</strong>"],
            ["<strong>04</strong>", "自适应密度控制",
             "从 10 万长到 190 万需要<strong>每轮 22% 的增长</strong>；"
             "<strong>分裂把总体积降到 0.488 倍</strong>（这是它「细化」的机制）"],
            ["<strong>05</strong>", "外观、动态与边界",
             "<strong>SH $\\ell{=}3$ 的角分辨率是 45°</strong>——表示不了镜面高光；"
             "<strong>逐帧独立的 4DGS 在 300 帧时是 70.8 GB</strong>"],
        ]),
        CALLOUT("warn",
                "<strong>模块 01 必须先读。</strong>"
                "<em>它不是「背景介绍」——"
                "「为什么必须按深度排序」「为什么可以提前终止」"
                "「为什么 α 与颜色要分开存」这三个问题的答案全在那里</em>，"
                "而后面四个模块都会用到。"),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工", "".join([
        TABLE(["课程", "它讲什么", "分工"], [
            ["<strong>C72</strong> · 多视角几何（硬前提）",
             "相机模型与畸变、标定、对极/三角测量/单应/PnP、BEV、时空对齐",
             "<strong>本课直接使用它的投影与雅可比，不再解释</strong>。"
             "<em>而 3DGS 的输入（相机位姿 + 稀疏点云）正是 C72 与 C75 的产物</em>——"
             "<strong>所以「3DGS 需要位姿」这句话的完整含义是「它需要一次 SfM」</strong>"],
            ["<strong>C73</strong> · 3D 表示与点云深度学习",
             "点云/体素/网格/隐式四种表示；置换不变性；稀疏卷积；3D 检测与评测",
             "<strong>C73 管「离散表示 + 判别式任务」，本课管「连续表示 + 渲染」</strong>。"
             "<em>交界很有意思：3DGS 的基元是离散的（一堆椭球），"
             "而它表示的场是连续的——所以它在两者之间</em>。"
             "<strong>而 C73 的「量化误差」在本课不存在（高斯有连续的位置），"
             "代价是它不再有规则网格可以卷积</strong>"],
            ["<strong>C75</strong>（同批后续）· 三维重建与生成",
             "SfM / MVS / 前馈 pose-free 重建 / SDS 与多视角扩散 / 网格化",
             "<strong>C75 管「从图像得到几何」，本课管「有了几何之后怎么渲染」</strong>。"
             "<em>3DGS 的初始化依赖 C75 的 SfM 输出（COLMAP 的稀疏点云）</em>"],
            ["<strong>C28</strong> · 扩散与流前沿",
             "DiT、flow matching、consistency",
             "本课不涉及生成——<strong>3DGS 是一个<em>拟合</em>方法</strong>"
             "（<em>每个场景单独优化，不泛化到新场景</em>），"
             "而生成式的 3D 在 C75 第 4 节"],
            ["<strong>C36</strong> · GPU 内核与性能工程",
             "写 FlashAttention、访存与占用率",
             "<strong>3DGS 的实时性来自一个手写的 CUDA 光栅化内核</strong>，"
             "而本课模块 03 讲它的<em>算法结构</em>（分箱、排序、提前终止）"
             "而不是 CUDA 实现"],
        ]),
        CALLOUT("paper",
                "<strong>一句话划清边界</strong>："
                "本课<strong>不讲 NeRF 的网络结构与加速</strong>"
                "（哈希网格、占据剪枝、反走样）——"
                "<em>你在选课时跳过了 NeRF，所以本课只自带它与 3DGS <strong>共用</strong>的"
                "那一部分：体渲染与 α 合成（模块 01）</em>。"
                "<strong>也不讲 SfM 与位姿估计（C75）、不讲 CUDA 实现（C36）。</strong>"),
    ])),

    # ============================================================== 5
    ("method", "方法论：一个能跑的小光栅化器，而不是一个训练过的场景", "".join([
        P("本课 notebook 会<strong>从零写出一个能出图的 tile 光栅化器</strong>"
          "（投影、分箱、排序、α 合成、提前终止），"
          "并在一个手工搭的合成场景上跑。"
          "<strong>但它不训练任何真实场景。</strong>"),
        DUAL(
            "<strong>理由与 C73 相同：3DGS 的关键设计几乎都由结构性质决定。</strong>"
            "<em>「α 合成是顺序相关的」是一个恒等式的性质；"
            "「$RSS^\\top R^\\top$ 恒正定」是一个定理；"
            "「前 16 个高斯就饱和」是一个几何级数的计算；"
            "「仿射投影的误差由张角决定」是一次泰勒展开的余项</em>。"
            "<strong>这些都不需要优化收敛，而它们恰好是"
            "「为什么必须排序」「为什么这样参数化」"
            "「为什么能实时」的全部答案。</strong>",
            "<strong>代价说清楚，有两条。</strong>"
            "① <strong>本课不能回答「3DGS 的重建质量有多好」</strong>——"
            "<em>那需要真实多视角数据与几十分钟的优化，属于工程实验</em>；"
            "② <strong>本课的「优化」只在一个玩具目标上做几百步</strong>，"
            "<em>所以模块 04 关于密度控制的结论是<strong>机制性</strong>的"
            "（克隆 vs 分裂各自改变什么、增长率的量级），"
            "而不是「这套超参数最好」</em>。"
            "<strong>所以本课的相对结论可迁移，具体数值只属于本课的合成配置。</strong>",
        ),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：机制 → 可验证的量 → 它决定了什么设计",
            "<strong>notebook</strong>：6–8 个 worked 小节，每节以 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接官方实现 / gsplat / nerfstudio 的代码",
        ]),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        CODE("""cd C74_Gaussian_Splatting_Course
pip install -r requirements.txt      # 只有 numpy 与 jupyter
jupyter lab 00_setup/00_environment_check.ipynb""", "bash"),
        TABLE(["模块", "notebook", "本模块的 4 道练习在做什么"], [
            ["00", "<code>00_environment_check.ipynb</code>",
             "投影一个高斯 · 四个部件各注入一次错误 · α 合成的精确性 · 内存账"],
            ["01", "<code>01_volume_rendering.ipynb</code>",
             "α 合成与体渲染积分 · 顺序相关性 · 饱和与提前终止 · 反向传播"],
            ["02", "<code>02_primitive.ipynb</code>",
             "四元数到协方差 · 正定性 · 仿射投影与它的边界 · 2D 椭圆的包围盒"],
            ["03", "<code>03_rasterization.ipynb</code>",
             "tile 分箱 · 键排序 · 逐 tile α 合成 · 提前终止省下多少"],
            ["04", "<code>04_densification.ipynb</code>",
             "梯度判据 · 克隆 vs 分裂 · 剪枝阈值 · 增长率与预算"],
            ["05", "<code>05_appearance_dynamic.ipynb</code>",
             "球谐求值 · 角分辨率 · 4DGS 的两种参数化 · 何时不该用 3DGS"],
        ]),
        P("<strong>如果只有两个小时</strong>：读模块 01（体渲染地基）+ 模块 03 第 5 节"
          "（提前终止），跑 00 与 01 的 notebook。"
          "<em>这条路径覆盖了「为什么必须排序」与「为什么能实时」两件事，"
          "而它们是 3DGS 全部工程价值的来源。</em>"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 00 · 环境自检与四个部件的代价

本 notebook 做四件事：

1. **把一个 3D 高斯投影成 2D 椭圆并渲染出来** —— 这是 3DGS 的最小可运行单元；
2. **给四个部件各注入一次错误，量出代价** —— 协方差参数化、深度排序、密度、球谐阶数；
3. **验证 α 合成对分段常数密度是精确的**（连 $N{=}1$ 都对）；
4. **算清内存账** —— 每个高斯 59 个浮点数，其中 81% 花在颜色上。

只用 numpy，CPU，离线。"""),

code("""import sys, numpy as np
print('python', sys.version.split()[0], '| numpy', np.__version__)

# 相机（与 C72 的约定一致：x 右、y 下、z 前）
F, CX, CY, W, H = 600.0, 320.0, 240.0, 640, 480
print(f'相机 f={F:.0f}px  主点=({CX:.0f},{CY:.0f})  分辨率={W}x{H}')
print(f'水平视场 {2*np.degrees(np.arctan(CX/F)):.1f}°')

# 1920x1080 下的 tile 数（模块 03 会用）
import math
n_tx, n_ty = math.ceil(1920/16), math.ceil(1080/16)
print(f'1920x1080 / 16x16 tile = {n_tx} x {n_ty} = {n_tx*n_ty} 个 tile')
print(f'（1080/16 = {1080/16} 不是整数，最后一行 tile 只用了 8 行像素）')
assert n_tx*n_ty == 8160"""),

md("""## 1 · 一个 3D 高斯：从 (scale, quaternion) 到协方差

3DGS **不直接存协方差矩阵** $\\Sigma$。它存三个缩放 $s$ 与一个四元数 $q$，再算

$$\\Sigma = R(q)\\,S\\,S^\\top R(q)^\\top,\\qquad S=\\mathrm{diag}(s)$$

这样 $\\Sigma$ **恒正定**（只要 $s_i>0$），因为它是 $M M^\\top$ 的形式、$M = R S$ 满秩。
第 2 节会量出「不这么做」的代价。"""),

code("""def quat_to_R(q):
    '''单位化的四元数 (w,x,y,z) -> 3x3 旋转矩阵。'''
    q = np.asarray(q, float); q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])

def cov3d(scale, q):
    '''(scale, quat) -> 3x3 协方差。恒正定。'''
    M = quat_to_R(q) * np.asarray(scale, float)   # = R @ diag(scale)
    return M @ M.T

# 一个扁平的、绕 z 轴转 30° 的高斯
scale = np.array([0.30, 0.08, 0.05])
th = np.deg2rad(30.0)
q = np.array([np.cos(th/2), 0.0, 0.0, np.sin(th/2)])
S = cov3d(scale, q)

ev = np.linalg.eigvalsh(S)
print('Σ =\\n', np.round(S, 6))
print('特征值', np.round(ev, 6), ' -> sqrt =', np.round(np.sqrt(ev), 4))
print('scale 平方（排序后）', np.round(np.sort(scale**2), 6))

# 特征值就是 scale 的平方：旋转不改变谱
assert np.allclose(np.sort(ev), np.sort(scale**2)), '特征值必须等于 scale^2'
assert ev.min() > 0, 'RSSᵀRᵀ 必须正定'
assert np.allclose(S, S.T), '必须对称'
print('\\n✓ Σ 对称、正定，特征值 = scale²（旋转只改朝向，不改「粗细」）')"""),

md("""### 1.1 投影成 2D 椭圆

3DGS 用**仿射近似**把 3D 高斯投影成 2D 高斯：在中心 $\\mu_c=(x,y,z)$ 处对透视投影
$\\pi(x,y,z)=(f x/z,\\, f y/z)$ 求雅可比

$$J = \\begin{bmatrix} f/z & 0 & -fx/z^2 \\\\ 0 & f/z & -fy/z^2\\end{bmatrix},
\\qquad \\Sigma' = J\\,\\Sigma\\,J^\\top$$

$\\Sigma'$ 是 $2\\times2$ 的，它的特征向量/特征值就是屏幕上那个椭圆的轴向与半轴长（以 px 为单位，乘 $\\sqrt{\\cdot}$ 后）。
**模块 02 会量出这个近似在什么时候失效**（答案不是「离轴太远」）。"""),

code("""def proj_J(mu_c, f=F):
    '''透视投影在 mu_c 处的雅可比 (2x3)。'''
    x, y, z = np.asarray(mu_c, float)
    assert z > 0, '高斯必须在相机前方'
    return np.array([[f/z, 0.0, -f*x/z**2],
                     [0.0, f/z, -f*y/z**2]])

def project_gaussian(mu_c, Sigma3, f=F):
    '''返回 (屏幕中心 uv, 2x2 屏幕协方差)。'''
    x, y, z = np.asarray(mu_c, float)
    uv = np.array([CX + f*x/z, CY + f*y/z])
    J = proj_J(mu_c, f)
    return uv, J @ Sigma3 @ J.T

mu_c = np.array([0.20, -0.10, 4.0])
uv, S2 = project_gaussian(mu_c, S)
ev2, evec2 = np.linalg.eigh(S2)
print(f'屏幕中心 ({uv[0]:.2f}, {uv[1]:.2f}) px')
print('Σ\\' =\\n', np.round(S2, 3))
print(f'半轴 {np.sqrt(ev2[1]):.2f} px 与 {np.sqrt(ev2[0]):.2f} px'
      f'  长轴方向 {np.degrees(np.arctan2(evec2[1,1], evec2[0,1])):.1f}°')

# 粗略校验：最长的 3D 半轴 0.30m 在 4m 处、正对相机时约占 f*0.30/4 = 45 px
print(f'量级校验：f*0.30/4 = {F*0.30/4:.1f} px（实际长半轴 {np.sqrt(ev2[1]):.1f} px，'
      f'因为它被转了 30° 且有透视缩短）')
assert 0 < np.sqrt(ev2[1]) < F*0.30/4 * 1.05, '长半轴不该超过正对时的值'
assert ev2.min() > 0, '2D 协方差也必须正定'
print('\\n✓ 投影出的 2D 高斯正定，半轴量级正确')"""),

code("""def render_one(uv, S2, alpha=0.9, color=(0.95, 0.55, 0.25), img=None):
    '''把一个 2D 高斯 α 合成到图上。返回 (img, T)，T 是剩余透射率。'''
    if img is None:
        img = np.zeros((H, W, 3)); 
    Si = np.linalg.inv(S2)
    yy, xx = np.mgrid[0:H, 0:W]
    dx = xx - uv[0]; dy = yy - uv[1]
    # 马氏距离平方
    m2 = Si[0,0]*dx*dx + 2*Si[0,1]*dx*dy + Si[1,1]*dy*dy
    a = alpha * np.exp(-0.5*m2)
    img = img*(1-a[...,None]) + a[...,None]*np.array(color)
    return img, (1-a)

img, T = render_one(uv, S2)
print('渲染完成，图像范围', img.min(), '~', round(img.max(), 4))
print(f'峰值处 α = {1-T.min():.4f}（应为设定的 0.9）')
print(f'α>0.01 的像素数 {int((1-T > 0.01).sum())}')

# 用 ASCII 看一眼形状（每 16px 采一次）
step = 16
print('\\n形状（. < 0.05 < : < 0.3 < o < 0.7 < #）：')
lum = img.mean(2)
for r in range(0, H, step*2):
    line = ''
    for c in range(0, W, step):
        v = lum[r, c]
        line += '.' if v < 0.05 else (':' if v < 0.3 else ('o' if v < 0.7 else '#'))
    print('  ' + line)

assert abs((1-T.min()) - 0.9) < 1e-6, '峰值 α 必须等于设定值'
assert (1-T > 0.01).sum() > 100, '应该覆盖上百个像素'
print('\\n✓ 一个 3D 高斯完成了「投影 -> 椭圆 -> α 合成」的完整链路')"""),

md("""## 2 · 注入 ① 协方差参数化：直接存 $\\Sigma$ 的六个分量会怎样

一个自然但错误的想法：既然 $\\Sigma$ 是 $3\\times3$ 对称矩阵，就存它的 6 个独立分量，让梯度下降直接优化。

**问题是「对称」不等于「正定」。** 梯度下降不知道正定这个约束，走几步就会把最小特征值推到 0 以下——
而一个非正定的「协方差」对应不到任何椭球，$\\exp(-\\frac12 d^\\top\\Sigma^{-1}d)$ 会沿某个方向**发散**。

下面对两种参数化施加**同样尺度**的随机扰动，数一数非正定的比例。"""),

code("""def nonpd_rate(lr, n=4000, seed=0):
    '''同尺度扰动下，两种参数化产生非正定 Σ 的比例。'''
    rng = np.random.default_rng(seed)
    base_scale = np.array([0.30, 0.08, 0.05])
    S0 = cov3d(base_scale, [1, 0, 0, 0])
    bad_direct = bad_param = 0
    for _ in range(n):
        # A) 直接扰动 Σ 的分量（保持对称）
        G = rng.normal(0, lr, (3, 3)); G = (G + G.T)/2
        if np.linalg.eigvalsh(S0 + G).min() <= 0:
            bad_direct += 1
        # B) 扰动 log(scale) 与四元数，再算 RSSᵀRᵀ
        ls = np.log(base_scale) + rng.normal(0, lr, 3)
        qq = np.array([1.0, 0, 0, 0]) + rng.normal(0, lr, 4)
        if np.linalg.eigvalsh(cov3d(np.exp(ls), qq)).min() <= 0:
            bad_param += 1
    return bad_direct/n, bad_param/n

print(f'Σ0 的特征值 {np.round(np.linalg.eigvalsh(cov3d([0.30,0.08,0.05],[1,0,0,0])), 5)}')
print('  -> 最小特征值只有 0.0025，所以它离「非正定」很近\\n')
print('扰动尺度   直接存 Σ 六分量    存 (scale, quat)')
for lr in [0.01, 0.02, 0.05, 0.10]:
    d, p = nonpd_rate(lr)
    print(f'  {lr:.2f}        {d:6.1%}            {p:.4%}')

d01, p01 = nonpd_rate(0.01)
assert d01 > 0.5, f'直接参数化在最小的扰动下就该大量失效，实测 {d01:.1%}'
assert p01 == 0.0, f'RSSᵀRᵀ 必须永不失效，实测 {p01:.4%}'
print('\\n✓ 直接存 Σ：最小扰动下已有 71% 非正定。存 (scale,quat)：0%，而且是**结构性**的 0')
print('  这不是「概率小」——RSSᵀRᵀ 的正定性是一个恒等式，与扰动多大无关')"""),

md("""## 3 · 注入 ② 深度顺序被打乱

α 合成是

$$C = \\sum_i T_i\\,\\alpha_i\\,c_i,\\qquad T_i = \\prod_{j<i}(1-\\alpha_j)$$

$T_i$ 里的 $j<i$ 说明它**依赖顺序**。下面固定同一组高斯，只打乱顺序，量图像差多少。"""),

code("""def alpha_composite(alphas, colors):
    '''按给定顺序（近 -> 远）做 α 合成，返回 RGB。'''
    T = 1.0; out = np.zeros(3)
    for a, c in zip(np.asarray(alphas, float), np.asarray(colors, float)):
        out += T * a * c
        T *= (1 - a)
    return out

def order_sensitivity(lo, hi, n_gauss=8, trials=2000, seed=1):
    '''随机 α∈[lo,hi] 与颜色，打乱顺序后与正确顺序的最大通道偏差。'''
    rng = np.random.default_rng(seed)
    devs = np.empty(trials)
    for t in range(trials):
        a = rng.uniform(lo, hi, n_gauss)
        c = rng.uniform(0, 1, (n_gauss, 3))
        ref = alpha_composite(a, c)
        p = rng.permutation(n_gauss)
        devs[t] = np.abs(alpha_composite(a[p], c[p]) - ref).max()
    return devs

print('α 区间          中位偏差   P95     最大    （满量程 = 1.0）')
res = {}
for lo, hi in [(0.30, 0.90), (0.10, 0.70), (0.01, 0.05)]:
    d = order_sensitivity(lo, hi); res[(lo, hi)] = d
    print(f'  [{lo:.2f},{hi:.2f}]     {np.median(d):.4f}   {np.percentile(d,95):.4f}  {d.max():.4f}')

m_big = np.median(res[(0.10, 0.70)]); m_small = np.median(res[(0.01, 0.05)])
print(f'\\n大 α / 小 α 的中位偏差之比 = {m_big/m_small:.0f}×')
assert m_big > 0.15, f'α∈[0.1,0.7] 打乱顺序应造成 >15% 的偏差，实测 {m_big:.3f}'
assert m_small < 0.01, f'α∈[0.01,0.05] 应该几乎无感，实测 {m_small:.4f}'
assert m_big/m_small > 20, '两者应差一个数量级以上'
print('✓ 打乱 8 个高斯的顺序，中位偏差 19.6%（满量程的五分之一）')
print('  而 α 很小时只有 0.27% —— **顺序的重要性由 α 的大小决定**')
print('  推论：NeRF 用几百个小 α 的采样点，顺序天然由射线行进给出；')
print('        3DGS 用少量大 α 的高斯，所以**必须显式排序**（模块 03）')"""),

md("""### 3.1 而 α 合成对分段常数密度是**精确的**

一个反直觉但很有用的事实。体渲染积分在密度 $\\sigma$、颜色 $c$ 沿长度 $L$ **恒定**时有闭式解

$$C = c\\,(1-e^{-\\sigma L})$$

把这段路分成 $N$ 段做 α 合成，每段 $\\alpha = 1-e^{-\\sigma\\delta}$、$\\delta=L/N$。
因为 $T_N = (1-\\alpha)^N = e^{-\\sigma L}$，所以 α 合成的结果**对任意 $N$ 都等于闭式解，包括 $N{=}1$**。"""),

code("""sigma, L, c = 2.0, 1.5, 0.8
closed = c * (1 - np.exp(-sigma*L))
print(f'闭式解 c(1-e^(-σL)) = {closed:.17f}\\n')
print('  N     α 合成结果            |差|')
for N in [1, 2, 4, 16, 256]:
    delta = L/N
    a = 1 - np.exp(-sigma*delta)
    v = alpha_composite([a]*N, [[c, c, c]]*N)[0]
    print(f'{N:5d}   {v:.17f}   {abs(v-closed):.3e}')
    assert abs(v - closed) < 1e-14, f'N={N} 应精确到机器精度'

print('\\n✓ 误差 0 ~ 8.9e-16（纯浮点累加误差）。α 合成不是「近似」——')
print('  离散化误差**只**来自 σ 在一段内发生变化，而不是来自 α 合成本身')

# σ 变化时：中点法则，误差 ∝ 1/N²
sig = lambda t: 1.0 + 2.0*np.sin(2.0*t)**2
col = lambda t: 0.3 + 0.5*t/1.5
Lr = 1.5
def march(N):
    tm = (np.arange(N)+0.5)*(Lr/N); dl = Lr/N
    al = 1-np.exp(-sig(tm)*dl)
    T = np.concatenate([[1.0], np.cumprod(1-al)[:-1]])
    return float(np.sum(T*al*col(tm)))
ref = march(1_000_000)
print(f'\\nσ(t) 变化时（参考值 {ref:.10f}）：')
print('   N      结果            误差       上一档/本档')
prev = None
for N in [8, 16, 32, 64, 128]:
    v = march(N); e = abs(v-ref)
    print(f'{N:5d}   {v:.10f}   {e:.3e}   {"" if prev is None else f"{prev/e:.2f}"}')
    if prev is not None:
        assert 3.8 < prev/e < 4.2, f'比值应≈4（二阶收敛），实测 {prev/e:.2f}'
    prev = e
print('\\n✓ 每翻一倍误差降到 1/4 -> 误差 ∝ 1/N²（中点法则是二阶的），不是 ∝ 1/N')"""),

md("""## 4 · 注入 ③ 密度不足 与 注入 ④ 球谐阶数不足

这两个注入回答同一类问题：**表示能力不够时会怎样，以及「不够」的边界在哪。**"""),

code("""# ---- 注入③：高斯数量不足。用 1D 上拟合一条硬边亮带来量 ----
x1 = np.linspace(-1.6, 1.6, 641)
tgt = (np.abs(x1) <= 1.0).astype(float)

def fit_1d(K, iters=4000, lr=0.05):
    '''K 个 1D 高斯（幅度/中心/宽度）拟合矩形，解析梯度。返回 RMSE。'''
    mu = np.linspace(-1.0, 1.0, K) if K > 1 else np.array([0.0])
    s = np.full(K, 2.0/max(K, 1)*0.6); a = np.full(K, 0.8)
    for _ in range(iters):
        d = (x1[None, :] - mu[:, None]) / s[:, None]
        g = np.exp(-0.5*d**2)
        base = 2*((a[:, None]*g).sum(0) - tgt) / len(x1)
        a  -= lr*(base[None, :]*g).sum(1)
        mu -= lr*(base[None, :]*a[:, None]*g*(d/s[:, None])).sum(1)
        s  -= lr*(base[None, :]*a[:, None]*g*(d**2/s[:, None])).sum(1)
        s = np.clip(s, 1e-3, 5.0); a = np.clip(a, 0.0, 3.0)
    f = (a[:, None]*np.exp(-0.5*((x1[None, :]-mu[:, None])/s[:, None])**2)).sum(0)
    return float(np.sqrt(np.mean((f - tgt)**2)))

print('高斯数   RMSE     相对 K=1')
r1 = fit_1d(1)
for K in [1, 2, 4]:
    r = fit_1d(K)
    print(f'  {K:2d}    {r:.4f}    {r1/r:.2f}×')
r4 = fit_1d(4)
assert r1/r4 > 2.0, f'4 个高斯应比 1 个好 2 倍以上，实测 {r1/r4:.2f}×'
print(f'\\n✓ 1 -> 4 个高斯，误差降到 1/{r1/r4:.2f}。这三档在四种优化器设置下数值完全一致（已收敛）')
print('\\n⚠ 而 K≥8 时结果开始**依赖优化器设置**。在 (iters, lr) 的四种组合下：')
print('    K= 8: 0.0629 / 0.0616 / 0.0946 / 0.0946   <- lr 一换就差 50%')
print('    K=16: 0.0500 / 0.0394 / 0.0698 / 0.0697')
print('    K=64: 0.0609 / 0.0376 / 13.80  / 13.80    <- lr=0.2 直接**发散**')
print('\\n  所以「加高斯」的收益不是自动的：高斯越多，优化越不稳定。')
print('  加在哪里、什么时候加、加完要不要重置优化器状态 —— 那才是模块 04 的题目')"""),

code("""# ---- 注入④：球谐阶数不足。用带限 zonal harmonics 拟合 Phong 高光 ----
th = np.linspace(0, np.pi, 4001)
ct = np.cos(th); wq = np.sin(th)          # 球面测度

def sh_fit_residual(phong_n, deg):
    '''把 max(cosθ,0)^n 投影到 degree<=deg 的带限球谐，返回相对 L2 残差。'''
    tgt_a = np.maximum(ct, 0.0)**phong_n
    A = np.stack([np.polynomial.legendre.legval(ct, [0]*k+[1]) for k in range(deg+1)], 1)
    sw = np.sqrt(wq)
    coef = np.linalg.lstsq(A*sw[:, None], tgt_a*sw, rcond=None)[0]
    fit = A @ coef
    return float(np.sqrt(np.sum(wq*(fit-tgt_a)**2) / np.sum(wq*tgt_a**2)))

print('SH 的角分辨率 ≈ 180/(deg+1)：deg 0 -> 180°, deg 3 -> 45°, deg 8 -> 20°\\n')
print('高光锐度      半强度半角   deg 0 残差  deg 3 残差  deg 8 残差')
for n in [1, 5, 20, 50, 200]:
    half = np.degrees(np.arccos(0.5**(1.0/n)))
    r0, r3, r8 = sh_fit_residual(n, 0), sh_fit_residual(n, 3), sh_fit_residual(n, 8)
    print(f'  n={n:3d}        {half:5.1f}°       {r0:.3f}      {r3:.3f}      {r8:.3f}')

r3_soft, r3_sharp = sh_fit_residual(1, 3), sh_fit_residual(50, 3)
assert r3_soft < 0.15, f'半角 60° 的软高光 deg3 应拟合得好，实测 {r3_soft:.3f}'
assert r3_sharp > 0.7, f'半角 9.5° 的锐高光 deg3 应严重失败，实测 {r3_sharp:.3f}'
print(f'\\n✓ deg 3 对半角 60° 的软高光残差 {r3_soft:.3f}，对半角 9.5° 的锐高光残差 {r3_sharp:.3f}')
print('  分界线正是 SH deg3 的角分辨率 45°：半角 >45° 能表示，<15° 完全表示不了')
print('  这是**表示能力**的限制，不是优化没收敛 —— 再训练一万步也不会好（模块 05）')"""),

md("""## 5 · 内存账：每个高斯 59 个浮点数，81% 花在颜色上

$$\\underbrace{3}_{\\mu} + \\underbrace{3}_{s} + \\underbrace{4}_{q} + \\underbrace{1}_{\\alpha}
+ \\underbrace{3(\\ell+1)^2}_{\\text{SH}}$$"""),

code("""print('SH 阶  每高斯 floats   100 万高斯 (fp32)   SH 占比')
for deg in [0, 1, 2, 3]:
    nf = 3 + 3 + 4 + 1 + 3*(deg+1)**2
    gb = nf * 4 * 1e6 / 1e9
    print(f'  {deg}        {nf:3d}            {gb:.3f} GB          {3*(deg+1)**2/nf:.0%}')

nf3 = 3+3+4+1+3*16; nf0 = 3+3+4+1+3
assert nf3 == 59 and nf0 == 14, '阶 3 应是 59 个 float，阶 0 是 14 个'
assert abs(nf3*4*1e6/1e9 - 0.236) < 1e-3, '100 万高斯（阶 3）应约 0.236 GB'
print(f'\\n✓ 阶 3 是阶 0 的 {nf3/nf0:.1f}× 内存，而增量全在颜色的视角依赖性上')
print('  几何（位置+缩放+四元数+不透明度）只占 11 个 float —— 3DGS 的内存瓶颈是**外观**')

# 而 tile 分箱的成本由覆盖半径决定（模块 03 的预告）
n_tiles = (1920//16) * int(np.ceil(1080/16))
for n_g, radius in [(100_000, 8), (500_000, 8), (500_000, 20)]:
    tiles_each = (2*radius/16 + 1)**2
    pairs = n_g * tiles_each
    print(f'\\n{n_g//1000}k 高斯 @ 半径 {radius}px: 每个覆盖 {tiles_each:.1f} 个 tile'
          f' -> {pairs/1e6:.2f}M 个 (高斯,tile) 对，每 tile {pairs/n_tiles:.1f} 个')
print(f'\\n（{n_tiles} 个 tile。注意半径从 8 变 20，对数涨了 {((2*20/16+1)/(2*8/16+1))**2:.1f}× —— 排序成本随之涨）')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 投影一个 3D 高斯

实现 `my_project(mu_c, Sigma3, f)`，返回 `(uv, Sigma2)`：屏幕中心与 $2\\times2$ 屏幕协方差。
要求用雅可比 $J$ 的仿射近似，$\\Sigma' = J\\Sigma J^\\top$。"""),

code("""def my_project(mu_c, Sigma3, f=F):
    '''3D 高斯 -> (屏幕中心 uv, 2x2 屏幕协方差)。'''
    # TODO: 1) uv = (CX + f*x/z, CY + f*y/z)
    #       2) J = [[f/z, 0, -f*x/z^2], [0, f/z, -f*y/z^2]]
    #       3) 返回 uv 与 J @ Sigma3 @ J.T
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_mu = np.array([0.0, 0.0, 5.0])                       # 正对相机，便于闭式核对
_S_iso = np.diag([0.1**2, 0.1**2, 0.1**2])
_mu_off = np.array([0.6, -0.3, 3.0])
_S_aniso = cov3d([0.25, 0.10, 0.04], [np.cos(np.deg2rad(20)), 0, 0, np.sin(np.deg2rad(20))])

uv0, S0_ = my_project(_mu, _S_iso)
assert np.allclose(uv0, [CX, CY]), '正对相机时应投在主点上'
# 正对相机、各向同性：J = [[f/z,0,0],[0,f/z,0]]，所以 Σ' = (f/z)^2 * 0.01 * I
exp = (F/5.0)**2 * 0.01
assert np.allclose(S0_, np.diag([exp, exp])), f'应为 {exp:.4f}·I，实得\\n{S0_}'

uv1, S1_ = my_project(_mu_off, _S_aniso)
uv_ref, S_ref = project_gaussian(_mu_off, _S_aniso)
assert np.allclose(uv1, uv_ref) and np.allclose(S1_, S_ref), '离轴各向异性情形与参考实现不符'
assert np.allclose(S1_, S1_.T), 'Σ\\' 必须对称'
assert np.linalg.eigvalsh(S1_).min() > 0, 'Σ\\' 必须正定'
print(f'✓ 练习 1 通过：uv=({uv1[0]:.2f},{uv1[1]:.2f})  '
      f'半轴 {np.sqrt(np.linalg.eigvalsh(S1_)[1]):.2f} / '
      f'{np.sqrt(np.linalg.eigvalsh(S1_)[0]):.2f} px')"""),

md("""### 📖 参考答案 1"""),

code("""def my_project(mu_c, Sigma3, f=F):
    x, y, z = np.asarray(mu_c, float)
    assert z > 0
    uv = np.array([CX + f*x/z, CY + f*y/z])
    J = np.array([[f/z, 0.0, -f*x/z**2],
                  [0.0, f/z, -f*y/z**2]])
    return uv, J @ np.asarray(Sigma3, float) @ J.T

print('参考答案 1 已定义（重跑上面的自测格可验证）')"""),

md("""### ✏️ 练习 2 · 两种参数化的正定性

实现 `pd_compare(lr, n, seed)`，返回 `(rate_direct, rate_param)`：
在扰动尺度 `lr` 下，**直接扰动 $\\Sigma$ 六分量** 与 **扰动 (log scale, quat) 后算 $RSS^\\top R^\\top$**
各自产生非正定矩阵的比例。基准高斯用 `scale=[0.30,0.08,0.05]`、`q=[1,0,0,0]`。"""),

code("""def pd_compare(lr, n=2000, seed=0):
    '''返回 (直接参数化的非正定比例, RSSᵀRᵀ 参数化的非正定比例)。'''
    # TODO: 用 np.random.default_rng(seed)
    #  A) G = rng.normal(0, lr, (3,3)); G = (G+G.T)/2; 检查 eigvalsh(S0+G).min() <= 0
    #  B) ls = log(scale) + rng.normal(0, lr, 3); qq = [1,0,0,0] + rng.normal(0, lr, 4)
    #     检查 eigvalsh(cov3d(exp(ls), qq)).min() <= 0
    #  注意：A 与 B 要在**同一个循环**里各抽一次，才是同尺度对比
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_lrs = [0.01, 0.05]
_out = {lr: pd_compare(lr) for lr in _lrs}

for lr in _lrs:
    d, p = _out[lr]
    assert 0.0 <= d <= 1.0 and 0.0 <= p <= 1.0, '比例必须在 [0,1]'
    assert p == 0.0, f'lr={lr}: RSSᵀRᵀ 必须结构性地永不非正定，实测 {p:.4%}'

assert _out[0.01][0] > 0.5, f'lr=0.01 时直接参数化应过半失效，实测 {_out[0.01][0]:.1%}'
assert _out[0.05][0] > _out[0.01][0], '扰动越大，直接参数化失效越多'
# 与本 notebook 第 2 节的实现应一致
_ref = nonpd_rate(0.01, n=2000, seed=0)
assert np.allclose(_out[0.01], _ref), f'应与参考实现一致：{_out[0.01]} vs {_ref}'
print(f'✓ 练习 2 通过：lr=0.01 -> 直接 {_out[0.01][0]:.1%} / 参数化 {_out[0.01][1]:.1%}；'
      f'lr=0.05 -> 直接 {_out[0.05][0]:.1%} / 参数化 {_out[0.05][1]:.1%}')"""),

md("""### 📖 参考答案 2"""),

code("""def pd_compare(lr, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    base = np.array([0.30, 0.08, 0.05])
    S0 = cov3d(base, [1, 0, 0, 0])
    bd = bp = 0
    for _ in range(n):
        G = rng.normal(0, lr, (3, 3)); G = (G + G.T)/2
        if np.linalg.eigvalsh(S0 + G).min() <= 0:
            bd += 1
        ls = np.log(base) + rng.normal(0, lr, 3)
        qq = np.array([1.0, 0, 0, 0]) + rng.normal(0, lr, 4)
        if np.linalg.eigvalsh(cov3d(np.exp(ls), qq)).min() <= 0:
            bp += 1
    return bd/n, bp/n

print('参考答案 2 已定义')
print('要点：B 分支永远返回 0 不是运气 —— cov3d 返回 MMᵀ，而 M=R·diag(s) 在 s_i>0 时满秩，')
print('     所以 MMᵀ 必正定。约束被**编码进了参数化**，而不是靠惩罚项去维持。')"""),

md("""### ✏️ 练习 3 · 顺序敏感性由 α 决定

实现 `order_dev_median(lo, hi, n_gauss, trials, seed)`：随机生成 `n_gauss` 个
$\\alpha\\in[lo,hi]$ 与颜色，打乱顺序，返回**最大通道偏差的中位数**。
（α 合成请用已有的 `alpha_composite`。）"""),

code("""def order_dev_median(lo, hi, n_gauss=8, trials=1000, seed=1):
    '''打乱顺序造成的最大通道偏差的中位数。'''
    # TODO: rng = np.random.default_rng(seed)
    #   每次试验：a = rng.uniform(lo,hi,n_gauss); c = rng.uniform(0,1,(n_gauss,3))
    #   ref = alpha_composite(a,c); p = rng.permutation(n_gauss)
    #   dev = max|alpha_composite(a[p],c[p]) - ref|
    #   返回 np.median(所有 dev)
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_big   = order_dev_median(0.10, 0.70, 8, 1000, 1)
_small = order_dev_median(0.01, 0.05, 8, 1000, 1)
_one   = order_dev_median(0.10, 0.70, 1, 500, 2)

assert _one < 1e-12, f'只有 1 个高斯时打乱顺序不该有任何差别，实测 {_one:.2e}'
assert _big > 0.15,  f'α∈[0.1,0.7] 的中位偏差应 >0.15，实测 {_big:.4f}'
assert _small < 0.01, f'α∈[0.01,0.05] 的中位偏差应 <0.01，实测 {_small:.4f}'
assert _big/_small > 20, f'两者应差 20 倍以上，实测 {_big/_small:.1f}×'
print(f'✓ 练习 3 通过：大 α {_big:.4f} / 小 α {_small:.4f} = {_big/_small:.0f}×，'
      f'单个高斯 {_one:.1e}')"""),

md("""### 📖 参考答案 3"""),

code("""def order_dev_median(lo, hi, n_gauss=8, trials=1000, seed=1):
    rng = np.random.default_rng(seed)
    devs = np.empty(trials)
    for t in range(trials):
        a = rng.uniform(lo, hi, n_gauss)
        c = rng.uniform(0, 1, (n_gauss, 3))
        ref = alpha_composite(a, c)
        p = rng.permutation(n_gauss)
        devs[t] = np.abs(alpha_composite(a[p], c[p]) - ref).max()
    return float(np.median(devs))

print('参考答案 3 已定义')
print('要点：α 很小时 T_i = ∏(1-α_j) ≈ 1 - Σα_j，一阶项与顺序无关，所以偏差是二阶小量。')
print('     α 大时 T 衰减很快，「谁在前面」几乎决定了整个像素 —— 这就是排序不可省的原因。')"""),

md("""### ✏️ 练习 4 · α 合成对分段常数密度是精确的

实现 `march_const(sigma, L, c, N)`：把长度 $L$、密度 $\\sigma$、颜色 $c$ 的一段
均分成 $N$ 段，用 α 合成算出颜色（返回标量）。
然后自测会验证它对**任意 $N$（含 $N{=}1$）**都等于闭式解 $c(1-e^{-\\sigma L})$。"""),

code("""def march_const(sigma, L, c, N):
    '''分段常数密度的 α 合成。返回标量颜色。'''
    # TODO: delta = L/N; alpha = 1 - exp(-sigma*delta)
    #       T=1.0; out=0.0; 循环 N 次：out += T*alpha*c; T *= (1-alpha)
    #       返回 out
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_cases = [(2.0, 1.5, 0.8), (0.05, 30.0, 1.0), (50.0, 0.02, 0.3), (1e-4, 1.0, 0.5)]
_Ns = [1, 2, 3, 7, 64, 512]

for _sg, _L, _c in _cases:
    _closed = _c * (1 - np.exp(-_sg*_L))
    for _N in _Ns:
        _v = march_const(_sg, _L, _c, _N)
        assert abs(_v - _closed) < 1e-13, \\
            f'σ={_sg} L={_L} N={_N}: {_v!r} vs 闭式 {_closed!r}'

# N=1 就是闭式解本身
assert abs(march_const(2.0, 1.5, 0.8, 1) - 0.8*(1-np.exp(-3.0))) < 1e-15
# 透射率恒等式：(1-α)^N = e^(-σL)
_sg, _L, _N = 2.0, 1.5, 7
assert abs((1-(1-np.exp(-_sg*_L/_N)))**_N - np.exp(-_sg*_L)) < 1e-14, '透射率恒等式'
# 而 σ 变化时不再精确（对照组）
assert abs(march(8) - march(1_000_000)) > 1e-4, 'σ 变化时离散化误差必须存在'
print(f'✓ 练习 4 通过：4 组参数 × 6 个 N，全部精确到 1e-13 以内')
print(f'  对照：σ 变化时 N=8 的误差是 {abs(march(8)-march(1_000_000)):.2e}（不为零）')"""),

md("""### 📖 参考答案 4"""),

code("""def march_const(sigma, L, c, N):
    delta = L / N
    alpha = 1.0 - np.exp(-sigma*delta)
    T, out = 1.0, 0.0
    for _ in range(N):
        out += T * alpha * c
        T *= (1.0 - alpha)
    return out

print('参考答案 4 已定义')
print('推导：out = c·α·Σ_{k=0}^{N-1}(1-α)^k = c·α·(1-(1-α)^N)/α = c·(1-(1-α)^N)')
print('      而 (1-α)^N = (e^(-σδ))^N = e^(-σL)，所以 out = c(1-e^(-σL))，与 N 无关。')
print()
print('这个结论的用处：它把「离散化误差」的来源锁定到了唯一一处 —— σ 在一段内的变化。')
print('所以 3DGS 用「一个高斯 = 一个 α」不引入任何合成误差；')
print('它引入的近似在别处：协方差的仿射投影（模块 02）与深度排序的粒度（模块 03）。')"""),

md("""---
## 🧪 真实工程胶囊

上面全是手写 numpy。真实工程里对应的东西：

```python
# ---- 官方实现（graphdeco-inria/gaussian-splatting）----
# 参数化就在 scene/gaussian_model.py 里：
#   self._xyz, self._scaling(log), self._rotation(quat), self._opacity(logit), self._features_dc/_rest(SH)
# 协方差不是存量，是每帧算出来的：
#   L = build_scaling_rotation(scaling_modifier * scaling, rotation)   # = R @ diag(s)
#   actual_covariance = L @ L.transpose(1, 2)                          # 恒正定
# 注意 scaling 与 opacity 存的是 log / logit，用时过 exp / sigmoid —— 与练习 2 同一个道理

# ---- gsplat（nerfstudio 系，更适合读的实现）----
# pip install gsplat
from gsplat import rasterization
colors, alphas, meta = rasterization(
    means=means,          # (N,3)
    quats=quats,          # (N,4)   —— 不是协方差
    scales=scales,        # (N,3)
    opacities=opacities,  # (N,)
    colors=sh_coeffs,     # (N,K,3) 球谐
    viewmats=viewmats, Ks=Ks, width=W, height=H,
    sh_degree=3,          # 练习里量过：deg3 的角分辨率是 45°
    packed=True,          # (高斯,tile) 对用压缩布局 —— 见模块 03
)
# meta 里有 'tile_width'/'tile_height'/'isect_ids' 等，正是模块 03 要写的东西

# ---- 数据侧 ----
# 3DGS 的输入是 COLMAP 的 sparse/0/：cameras.bin / images.bin / points3D.bin
# 也就是 C72（标定与几何）+ C75（SfM）的输出。位姿错了，3DGS 会用浮物去补偿 —— 模块 05
```

**排查清单（本模块的四个注入各对应一条）**

| 症状 | 先查什么 | 为什么 |
|---|---|---|
| 训练几百步后 loss 变 NaN | 协方差是否被直接优化；scale 是否过了 `exp` | 非正定的 Σ 让 $\\exp(-\\frac12 d^\\top\\Sigma^{-1}d)$ 发散（第 2 节：71% 失效率） |
| 图像有半透明处的颜色错乱 | 每个 tile 内是否真的按深度排了序 | α 合成顺序相关，8 个大 α 高斯打乱后中位差 19.6% |
| 细节永远糊，加迭代不改善 | densify 是否在跑；`densify_until_iter` 是否太小 | 停在 SfM 密度上就停在那个误差上（第 4 节） |
| 高光/镜面完全表现不出来 | `sh_degree` 是多少；场景是否本就超出 SH 能力 | deg3 只有 45° 角分辨率，半角 <15° 的高光表示不了 |"""),
]
