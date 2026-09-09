# -*- coding: utf-8 -*-
"""C73 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C72（多视角几何）是本课的前提</strong>——"
                 "投影、标定、位姿这套语言本课直接使用、不再重讲；"
                 "线性代数；读过 C18 模块 01（卷积与感受野）更好"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（造一个合成路口点云 / 四种表示的内存与精度账 / '
                       '<strong>体素占用率从 9.43% 掉到 0.018%，而平均每格点数掉到 1.03</strong> / '
                       '量化误差的两个精确常数 $r\\sqrt3/2$ 与 $0.4804r$ / '
                       '<strong>三个乘子：为什么 3D 的一切都比 2D 更敏感</strong>）'),
    ("核心参考", "Qi et al., <em>PointNet</em>（CVPR 2017）· "
                 "Graham et al., <em>3D Semantic Segmentation with Submanifold "
                 "Sparse Convolutional Networks</em>（CVPR 2018）· "
                 "Lang et al., <em>PointPillars</em>（CVPR 2019）· "
                 "Yin et al., <em>Center-based 3D Object Detection and Tracking</em>"
                 "（CVPR 2021）· 本课程 <strong>C72</strong>（几何前提）· "
                 "C57（小目标与尺度）· C55（TSR 与自动驾驶感知）"),
    ("预计时长", "读 45 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-multipliers", "三个乘子：为什么 3D 的一切都更难", "".join([
        P("从 2D 到 3D，最常听到的说法是「多了一个维度」。"
          "<strong>而工程上真正的后果是：几乎每一个量都变成了三个因子的积。</strong>"
          "这一条贯穿本课六个模块。"),
        TABLE(["量", "2D", "3D", "后果"], [
            ["<strong>网格规模</strong>", "$(L/r)^2$", "$(L/r)^3$",
             "$100\\times100\\times8$ m 的场景在 $r{=}0.05$ m 下是 "
             "<strong>6.4 亿格 / 640 MB</strong>，"
             "<em>而其中只有 0.018% 非空</em>（模块 01）"],
            ["<strong>卷积代价</strong>", "$k^2$", "$k^3$",
             "$3\\times3\\times3$ 是 27 而不是 9——"
             "<strong>密集 3D 卷积在这个场景上是 283 GFLOP</strong>（模块 03）"],
            ["<strong>IoU</strong>", "两个乘子", "<strong>三个乘子</strong>",
             "每轴 10% 的相对误差：2D IoU 0.681，"
             "<strong>3D 只有 0.574</strong>（模块 05）"],
            ["<strong>锚框数</strong>", "尺度 × 长宽比", "再乘 <strong>朝向</strong>",
             "而<strong>只用 0°/90° 两个朝向时，45° 的目标一个正样本都拿不到</strong>"
             "（最好 IoU 0.425，模块 04）"],
        ]),
        DUAL(
            "<strong>这四行不是四个独立的困难，它们是同一件事的四个面。</strong>"
            "<em>而且它们互相加强：网格规模让你不得不用大体素，"
            "大体素让量化误差变大，量化误差让 IoU 掉下来，"
            "IoU 掉下来让正样本变少，正样本变少让训练更难</em>。"
            "<strong>所以 3D 方法的历史基本上就是「怎么绕开这条链」的历史。</strong>",
            "<strong>而本课的组织方式就是沿着这条链走：</strong>"
            "模块 01 摆出四种表示各自怎么应对「$(L/r)^3$」；"
            "模块 02 讲点云路线（<em>完全绕开网格</em>）为此付出了什么；"
            "模块 03 讲体素路线怎么靠稀疏性把 $k^3$ 拿回来；"
            "模块 04 讲检测头怎么绕开朝向离散化；"
            "模块 05 讲评测指标本身被三个乘子放大了多少。"
            "<em>每一步都有一个可计算的数，而它们全部在 notebook 里被验证。</em>",
        ),
    ])),

    # ============================================================== 2
    ("four-representations", "四种三维表示，四种取舍", "".join([
        ASCII("""
   同一个物体的四种存法

   点云 (point cloud)          体素 (voxel)
     {(x,y,z)} × N               occupancy[i][j][k]
     ✓ 精度只受传感器限制          ✓ 规则网格 -> 能直接用卷积
     ✓ 内存 ∝ 点数                ✗ 内存 ∝ (L/r)³
     ✗ 无序、无邻域结构            ✗ 量化误差 <= r√3/2
     ✗ 密度极不均匀

   网格 (mesh)                  隐式 (implicit / SDF)
     顶点 + 面                    f(x,y,z) -> 距离或占据
     ✓ 表面连续、可渲染            ✓ 分辨率无关、内存 = 参数量
     ✓ 内存小                     ✓ 天然光滑
     ✗ 拓扑难学（面的连接关系）     ✗ 查询需要前向计算
     ✗ 从点云重建本身是个难问题     ✗ 单个网络通常只表示一个物体/场景
        """),
        P("<strong>而「哪一种更好」是个错问题——正确的问法是「这个任务的哪个量是瓶颈」。</strong>"),
        TABLE(["瓶颈是", "该选", "为什么"], [
            ["<strong>精度</strong>（要厘米级的位置）", "点云 / 隐式",
             "体素的量化误差有下界 $r\\sqrt3/2$，而 $r$ 又被内存卡住"],
            ["<strong>要用卷积</strong>", "体素（+ 稀疏化）",
             "规则网格是卷积的前提；<em>而稀疏卷积把 $(L/r)^3$ 的代价降到占用率的倒数</em>"],
            ["<strong>内存 / 带宽</strong>", "点云 / 隐式",
             "$r{=}0.05$ m 的密集体素是 640 MB，而同一场景的点云是 1.44 MB"],
            ["<strong>要渲染或做几何编辑</strong>", "网格",
             "表面显式存在；<em>而这也是 C75（三维重建与生成）的落点</em>"],
            ["<strong>邻域/局部结构</strong>", "体素 / 有 kNN 的点云",
             "<strong>裸点云没有邻域概念</strong>——这正是 PointNet 的限制来源（模块 02）"],
        ]),
        CALLOUT("intuition",
                "<strong>一个常被忽略的事实：精细体素化几乎等于点云。</strong>"
                "notebook 第 3 节量到：$r{=}0.05$ m 时"
                "<strong>平均每格只有 1.03 个点</strong>——"
                "<em>也就是说体素化已经不再压缩任何东西，"
                "它只是给点云套上了 6.4 亿个格子的外壳</em>。"
                "所以「体素分辨率越高越好」在某个点之后是纯浪费，"
                "<strong>而那个点可以用「平均每格点数」这一个数字找出来。</strong>"),
    ])),

    # ============================================================== 3
    ("map", "课程地图", "".join([
        TABLE(["模块", "主题", "带走的那个可验证的量"], [
            ["<strong>01</strong>", "四种表示的代价账",
             "<strong>占用率 9.43% → 0.018%</strong>（$r$ 从 0.5 到 0.05 m）；"
             "量化误差 $\\max=r\\sqrt3/2$、$\\text{mean}_{\\text{均匀}}=0.4804r$"],
            ["<strong>02</strong>", "置换不变性与 max-pool",
             "<strong>临界点集只有 24/1024（2.3%）</strong>，"
             "删掉其余 1000 个点输出<strong>逐位不变</strong>；"
             "<em>而它不随点数增长</em>"],
            ["<strong>03</strong>", "体素化与稀疏卷积",
             "<strong>常规稀疏卷积 4 层膨胀 66.8×</strong>，"
             "占用率 0.897% → 59.9%，"
             "FLOPs 优势从 112× 掉到 <strong>1.7×</strong>"],
            ["<strong>04</strong>", "3D 检测：从锚框到中心点",
             "<strong>Δθ=45° 时 BEV IoU 只有 0.425</strong>——"
             "用 0°/90° 两个朝向的锚框，45° 目标<strong>0 个正样本</strong>"],
            ["<strong>05</strong>", "分割与 3D 评测",
             "达到 IoU=0.5 允许的平移：轿车沿最薄轴 0.5 m，"
             "<strong>限速牌只有 0.0333 m</strong>（差 15 倍）"],
        ]),
        CALLOUT("warn",
                "<strong>模块顺序有依赖。</strong>"
                "模块 03 的稀疏卷积需要模块 01 的占用率；"
                "模块 04 的正样本分配需要模块 05 的 IoU 敏感性"
                "（<em>本课刻意把评测放在最后，"
                "但模块 04 会前向引用它——因为「为什么正样本这么少」的答案在那里</em>）。"),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工", "".join([
        TABLE(["课程", "它讲什么", "分工"], [
            ["<strong>C72</strong> · 多视角几何（本课的前提）",
             "相机模型与畸变、标定、对极/三角测量/单应/PnP、BEV 投影、时空对齐——"
             "<strong>纯几何、无学习</strong>",
             "<strong>分界线是「有没有学习成分」</strong>："
             "C72 没有，本课有。"
             "<em>投影、标定、位姿在本课直接使用而不再解释</em>；"
             "而 C72 模块 04 的 BEV 网格采样率问题在本课模块 03 会以"
             "「体素分辨率」的形式再次出现"],
            ["<strong>C18</strong> · 计算机视觉",
             "2D 检测、分割、自监督；`点云` 全库 5 文件、`PointNet` 0",
             "本课不重复任何 2D 网络结构。"
             "<strong>本课全程 numpy，不训练真实网络</strong>——"
             "<em>而是把「为什么这个结构必须长这样」的性质用几十行代码验证出来</em>"],
            ["<strong>C57</strong> · 小目标检测",
             "2D IoU 的尺度敏感性、多尺度架构、NWD、切片推理",
             "<strong>C57 的核心结论在本课模块 05 被推广到三个乘子</strong>："
             "<em>同样的相对误差，3D IoU 总低于 2D（0.574 vs 0.681）</em>；"
             "而「薄」这个维度在 2D 里不存在"],
            ["<strong>C55</strong> · TSR 与自动驾驶感知",
             "数据集与法规、两级 vs 端到端、失效模式、时序融合、安全评测",
             "C55 讲「TSR 这个任务」，本课讲「三维表示这套工具」。"
             "<em>交界是模块 05：交通标志又小又薄，"
             "所以它是 3D IoU 最不友好的一类目标</em>"],
            ["<strong>C74/C75</strong>（同批新课，在本课之后）",
             "3D 高斯溅泼与实时渲染；三维重建与生成",
             "<strong>本课管「离散表示 + 判别式任务」</strong>（点云/体素/检测/分割），"
             "<strong>C74/C75 管「连续表示 + 生成式任务」</strong>（辐射场/溅泼/重建/生成）。"
             "<em>而 C74 会自带体渲染与 α 合成的地基</em>"],
            ["<strong>C46</strong> · 图机器学习",
             "message passing、GCN/GAT、图 transformer",
             "点云上的 kNN 图与 message passing 在概念上与 C46 同源。"
             "<strong>本课不重复 GNN 的机制</strong>，"
             "<em>只在模块 02 第 6 节指出「PointNet++ 的分组本质上是在建一个几何近邻图」</em>"],
        ]),
        CALLOUT("paper",
                "<strong>一句话划清边界</strong>："
                "本课不碰 NeRF 与神经渲染（<em>用户在选课时跳过了它，"
                "所以体渲染的地基放在 C74</em>）、"
                "不碰 SLAM 的建图与回环、"
                "也不碰点云配准（ICP）——"
                "<em>后者需要一整套优化工具，而它在本课的任务里不是瓶颈。</em>"),
    ])),

    # ============================================================== 5
    ("method", "方法论：不训练网络，怎么学网络结构", "".join([
        P("本课有学习成分，但<strong>全程 numpy、不训练任何真实网络</strong>。"
          "这看起来矛盾，而它其实是这门课最有效的部分。"),
        DUAL(
            "<strong>理由是：3D 网络的关键设计几乎都由<em>结构性质</em>决定，"
            "而结构性质可以在不训练的情况下被精确验证。</strong>"
            "<em>「max-pool 是置换不变的」是一个恒等式，不是一个实验结果；"
            "「临界点集不超过 D 个点」是一个定理，可以逐位验证；"
            "「常规稀疏卷积会膨胀」是一个集合运算的结果</em>。"
            "<strong>这些都不需要训练，而它们恰好是「为什么 PointNet 长这样」"
            "「为什么要子流形稀疏卷积」「为什么从 anchor 走向 center」的全部答案。</strong>",
            "<strong>代价也要说清楚，它有两条。</strong>"
            "① <strong>本课不能回答「哪个模型精度更高」</strong>——"
            "<em>那需要真实数据集与训练，属于工程实验而不是本课</em>。"
            "② <strong>本课的「网络」是随机初始化的</strong>，"
            "所以关于<em>特征质量</em>的一切都无从谈起；"
            "<strong>但关于<em>信息流</em>的一切都成立</strong>——"
            "<em>临界点集、膨胀率、正样本比例都与权重取值无关</em>。"
            "<strong>所以本课的结论是「结构性的」，"
            "而它们比精度数字更稳定：换数据集不变，换年份也不变。</strong>",
        ),
        H3("本课会验证的五个「结构性事实」，以及它们各自是什么"),
        TABLE(["事实", "它是什么", "怎么验证", "在哪个模块"], [
            ["max-pool 置换不变", "<strong>恒等式</strong>",
             "随机置换后逐位比较（差 0.0）", "02"],
            ["临界点集 $\\le D$", "<strong>定理</strong>（PointNet 原论文）",
             "数不同 argmax 的个数，并删掉其余点验证输出不变", "02"],
            ["量化误差 $\\le r\\sqrt3/2$", "<strong>几何上界</strong>",
             "逐点算位移，比上界", "01"],
            ["常规稀疏卷积会膨胀", "<strong>集合运算的结果</strong>",
             "对活跃集反复做 $3^3$ 邻域并集", "03"],
            ["朝向离散化会漏正样本", "<strong>几何计算</strong>",
             "多边形裁剪算旋转框 IoU，扫全部锚框", "04"],
        ]),
        P("<strong>五条里没有一条需要训练，也没有一条依赖权重取值。</strong>"
          "<em>而它们恰好就是「为什么 PointNet 长这样」「为什么要子流形稀疏卷积」"
          "「为什么从 anchor 走向 center」的全部答案</em>。"),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：结构性质 → 可验证的量 → 它决定了什么设计",
            "<strong>notebook</strong>：6–8 个 worked 小节，每节以 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接 PyTorch / spconv / MMDetection3D 的代码",
        ]),
        CALLOUT("danger",
                "<strong>一个必须提前说明的边界。</strong>"
                "本课的合成点云是<em>几何上合理但物理上简化</em>的："
                "没有真实 LiDAR 的<strong>射线模型</strong>"
                "（<em>所以没有遮挡阴影、没有随距离衰减的点密度、没有反射率</em>）。"
                "<strong>因此本课关于「占用率」「膨胀率」的<em>相对</em>结论可迁移，"
                "而具体百分比只属于本课的合成配置。</strong>"
                "<em>真实 64 线 LiDAR 的点密度随距离按 $1/d^2$ 掉，"
                "这会让远处的占用率比本课更低——也就是本课的结论方向不变、幅度更强。</em>"),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        CODE("""cd C73_3D_Representation_Course
pip install -r requirements.txt      # 只有 numpy 与 jupyter
jupyter lab 00_setup/00_environment_check.ipynb""", "bash"),
        TABLE(["模块", "notebook", "本模块的 4 道练习在做什么"], [
            ["00", "<code>00_environment_check.ipynb</code>",
             "合成点云 · 四种表示的内存账 · 占用率与每格点数 · 三个乘子"],
            ["01", "<code>01_representations.ipynb</code>",
             "体素化与反体素化 · 量化误差的两个常数 · 表示转换的信息损失 · 选型器"],
            ["02", "<code>02_pointnet.ipynb</code>",
             "对称函数 · 临界点集 · max vs sum 的鲁棒性 · T-Net 与对齐"],
            ["03", "<code>03_sparse_voxel.ipynb</code>",
             "稀疏张量的哈希索引 · 常规 vs 子流形卷积 · 膨胀率 · FLOPs 账"],
            ["04", "<code>04_detection3d.ipynb</code>",
             "旋转框 IoU（多边形裁剪）· 锚框分配 · 中心点热图 · 朝向的周期性"],
            ["05", "<code>05_seg_eval.ipynb</code>",
             "3D IoU 的三个乘子 · 按尺寸分层的 mAP · 混淆矩阵 · 评测口径审计"],
        ]),
        P("<strong>如果只有两个小时</strong>：读本页 + 模块 02（临界点集）+ 模块 05 第 2 节"
          "（3D IoU 的三个乘子），跑 00 与 02 的 notebook。"
          "<em>这条路径覆盖了「点云方法为什么这样设计」与"
          "「3D 指标为什么不能照搬 2D 的阈值」两个最容易出错的地方。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 00 · 环境自检与「三个乘子」

这个 notebook 做三件事：

1. **造一个合成路口点云**（地面 + 4 辆车 + 3 块标志 + 散点），全课复用。
2. **把四种表示的代价算成具体数字**：
   $r{=}0.05$ m 的密集体素是 **640 MB**，而同一场景的点云是 **1.44 MB**——
   **而那 640 MB 里只有 0.018% 非空，平均每格 1.03 个点。**
3. **量出「三个乘子」**：网格规模 $(L/r)^3$、卷积核 $k^3$、IoU 的三个因子。
   同样每轴 10% 的相对误差，**2D IoU 是 0.681 而 3D 只有 0.574**。

> 心智模型：**从 2D 到 3D，几乎每个量都从两个因子的积变成三个因子的积。
> 而这四件事互相加强——本课六个模块就是沿着这条链走。**"""),

    md("""## 0 · 环境"""),

    code("""import numpy as np

print('numpy', np.__version__)
print('本课全程 CPU / 断网 / **不训练任何真实网络**')
print('前提：C72（多视角几何）—— 投影、标定、位姿本课直接使用，不再重讲')

# 场景范围（米）：X 前 100、Y 左右各 50、Z 上 8  —— 沿用 C72 的车体坐标约定
SCENE_L = (100.0, 100.0, 8.0)
N_PTS = 120_000                     # 一帧 64 线 LiDAR 的量级"""),

    md("""## 1 · 合成路口点云

**刻意简化但几何上合理**：没有真实 LiDAR 的射线模型（无遮挡阴影、
点密度不随距离衰减、无反射率）。所以本课关于占用率的**相对**结论可迁移，
具体百分比只属于这个配置。"""),

    code("""def synth_scene(n=N_PTS, seed=0):
    \"\"\"合成路口：70% 地面 + 4 辆车 + 3 块标志 + 其余散点。\"\"\"
    r = np.random.default_rng(seed)
    parts = []

    n_g = int(n * 0.70)
    parts.append(np.column_stack([r.uniform(0, 100, n_g),
                                  r.uniform(-50, 50, n_g),
                                  r.normal(0, 0.02, n_g)]))          # 地面

    for cx, cy in [(20, -3), (35, 3), (60, -3), (80, 3)]:             # 车
        m = int(n * 0.05)
        parts.append(np.column_stack([r.uniform(cx - 2.2, cx + 2.2, m),
                                      r.uniform(cy - 0.9, cy + 0.9, m),
                                      r.uniform(0, 1.5, m)]))

    for cx, cy in [(30, -5.5), (55, 5.5), (75, -5.5)]:                # 标志（又小又薄）
        m = int(n * 0.01)
        parts.append(np.column_stack([r.uniform(cx - 0.05, cx + 0.05, m),
                                      r.uniform(cy - 0.4, cy + 0.4, m),
                                      r.uniform(1.8, 2.6, m)]))

    used = sum(len(p) for p in parts)
    k = n - used
    parts.append(np.column_stack([r.uniform(0, 100, k),
                                  r.uniform(-50, 50, k),
                                  r.uniform(0, 8, k)]))               # 散点
    return np.vstack(parts)

P = synth_scene()
print(f'点数 {len(P):,}')
print(f'范围 X [{P[:,0].min():6.2f}, {P[:,0].max():6.2f}]  '
      f'Y [{P[:,1].min():6.2f}, {P[:,1].max():6.2f}]  '
      f'Z [{P[:,2].min():5.2f}, {P[:,2].max():5.2f}]')
assert len(P) == N_PTS
# 地面点占大头，这与真实 LiDAR 一致
near_ground = (np.abs(P[:, 2]) < 0.1).mean()
print(f'|z| < 0.1 m 的点占 {near_ground:.1%}  ← 地面主导，真实点云也是这样')
assert near_ground > 0.6"""),

    md("""## 2 · 四种表示的内存账

$(L/r)^3$ 这个乘子的直接后果。"""),

    code("""def dense_voxel_count(L, r):
    return int(np.prod([l / r for l in L]))

pc_bytes = len(P) * 3 * 4          # float32
print(f'点云:  {len(P):>10,} 点 × 3 × float32 = {pc_bytes/1e6:8.2f} MB\\n')
print(f\"{'r (m)':>7s} {'格数':>15s} {'占据字节(1B/格)':>16s} {'相对点云':>10s}\")
mem = {}
for r in [0.5, 0.2, 0.1, 0.05]:
    n = dense_voxel_count(SCENE_L, r)
    mem[r] = n
    print(f'{r:7.2f} {n:15,} {n/1e6:15.2f} MB {n/pc_bytes:9.1f}×')

assert mem[0.05] / mem[0.1] == 8, '格数应当按 r³ 增长：r 减半 -> 8 倍'
assert abs(mem[0.05] / pc_bytes - 444) < 5
print(f'\\n✅ r 减半 -> 格数 ×8（这就是第一个乘子）')
print(f'   r=0.05 m 的密集体素是点云的 {mem[0.05]/pc_bytes:.0f} 倍内存')

# 网格与隐式表示的量级（对照）
print(f'\\n对照：')
print(f'  网格 mesh:  假设 5 万顶点 + 10 万面 = '
      f'{(50_000*3*4 + 100_000*3*4)/1e6:.2f} MB')
print(f'  隐式 SDF:   一个 8×256 的 MLP ≈ '
      f'{(3*256 + 7*256*256 + 256)*4/1e6:.2f} MB（**与分辨率无关**）')"""),

    md("""## 3 · 占用率：那 640 MB 里有多少是空的

**注意最后一列**——精细体素化之后「平均每格点数」掉到 1.03，
也就是**体素化已经不再压缩任何东西**。"""),

    code("""def voxel_stats(pts, r, L=SCENE_L):
    idx = np.floor(pts / r).astype(np.int64)
    uniq = np.unique(idx, axis=0)
    total = dense_voxel_count(L, r)
    return {'occupied': len(uniq), 'total': total,
            'rate': len(uniq) / total, 'pts_per_voxel': len(pts) / len(uniq)}

print(f\"{'r (m)':>7s} {'非空格':>10s} {'总格数':>15s} {'占用率':>10s} {'平均每格点数':>13s}\")
st = {}
for r in [0.5, 0.2, 0.1, 0.05]:
    s = voxel_stats(P, r)
    st[r] = s
    print(f'{r:7.2f} {s["occupied"]:10,} {s["total"]:15,} '
          f'{100*s["rate"]:9.4f}% {s["pts_per_voxel"]:12.2f}')

assert st[0.5]['rate'] > 0.05 and st[0.05]['rate'] < 0.0005
print(f'\\n占用率从 {100*st[0.5]["rate"]:.2f}% 掉到 {100*st[0.05]["rate"]:.4f}%'
      f' —— 降了 {st[0.5]["rate"]/st[0.05]["rate"]:.0f} 倍')

# 关键：平均每格点数趋于 1
assert st[0.05]['pts_per_voxel'] < 1.1, '精细体素化时每格几乎只有一个点'
print(f'而平均每格点数从 {st[0.5]["pts_per_voxel"]:.2f} 掉到 '
      f'{st[0.05]["pts_per_voxel"]:.2f}')
print('✅ **精细体素化几乎等于点云** —— 它不再压缩，只是套上一层空格子')
print('   → 「体素分辨率越高越好」在某个点之后是纯浪费，'
      '而那个点由「平均每格点数」找出来')"""),

    md("""## 4 · 量化误差的两个精确常数

点被搬到格中心，位移有一个精确上界和一个精确的均匀分布均值。"""),

    code("""def quant_error(pts, r):
    idx = np.floor(pts / r)
    centers = (idx + 0.5) * r
    d = np.linalg.norm(pts - centers, axis=1)
    return d

# 常数一：最大位移 = r√3/2（立方体中心到顶点）
# 常数二：均匀分布在立方体内时的平均距离 = 0.4804 r（数值积分得到）
u = np.random.default_rng(1).uniform(-0.5, 0.5, (400_000, 3))
C_UNIFORM = float(np.linalg.norm(u, axis=1).mean())
print(f'均匀立方体（边长 1）内到中心的平均距离 = {C_UNIFORM:.4f}')
print(f'  最大 = {np.linalg.norm(u,axis=1).max():.4f}   理论 √3/2 = {np.sqrt(3)/2:.4f}')
assert abs(C_UNIFORM - 0.4804) < 0.002, C_UNIFORM

print(f\"\\n{'r (m)':>7s} {'理论上界 r√3/2':>15s} {'实测最大':>10s} \"
      f\"{'实测平均':>10s} {'均匀理论 0.4804r':>17s} {'实测/均匀':>10s}\")
for r in [0.5, 0.2, 0.1, 0.05]:
    d = quant_error(P, r)
    ub = r * np.sqrt(3) / 2
    print(f'{r:7.2f} {ub:14.4f}m {d.max():9.4f}m {d.mean():9.4f}m '
          f'{C_UNIFORM*r:16.4f}m {d.mean()/(C_UNIFORM*r):9.2f}')
    assert d.max() <= ub + 1e-12, '不可能超过上界'

# 实测平均比均匀理论**大**，因为地面点在 z 上集中在格子边界附近
r = 0.5
d = quant_error(P, r)
ratio = d.mean() / (C_UNIFORM * r)
print(f'\\n实测平均是均匀理论的 {ratio:.2f} 倍')
assert ratio > 1.1, '点在体素内不是均匀分布的'
print('✅ 上界 r√3/2 是硬的；而**实测均值大于均匀理论值**——')
print('   因为 70% 的点是地面点，它们在 z 上集中在格子的某个面附近，')
print('   而「贴在一个面上」的平均距离是 0.6246r（> 0.4804r）')
u2 = np.column_stack([np.random.default_rng(2).uniform(-0.5,0.5,200_000),
                      np.random.default_rng(3).uniform(-0.5,0.5,200_000),
                      np.full(200_000, -0.48)])
print(f'   验证：贴面点的平均距离 = {np.linalg.norm(u2,axis=1).mean():.4f} '
      f'（均匀是 {C_UNIFORM:.4f}）')"""),

    md("""## 5 · 三个乘子之三：IoU

$\\text{IoU}$ 在 3D 里是三个因子的积，所以**同样的相对误差在 3D 下更痛**。"""),

    code("""def iou_axis_aligned(size, delta):
    \"\"\"同尺寸轴对齐框，中心相距 delta 时的 IoU（维数由 size 决定）。\"\"\"
    s = np.asarray(size, float); d = np.abs(np.asarray(delta, float))
    inter = np.prod(np.maximum(s - d, 0.0))
    vol = np.prod(s)
    den = 2 * vol - inter
    return inter / den if den > 0 else 0.0

print('单位立方体 / 单位正方形，每轴相对误差都是 rel：\\n')
print(f\"{'rel':>6s} {'2D IoU':>9s} {'3D IoU':>9s} {'3D/2D':>8s}\")
for rel in [0.02, 0.05, 0.10, 0.20]:
    i2 = iou_axis_aligned((1., 1.), (rel, rel))
    i3 = iou_axis_aligned((1., 1., 1.), (rel, rel, rel))
    print(f'{rel:6.0%} {i2:9.3f} {i3:9.3f} {i3/i2:8.3f}')
    assert i3 < i2, '同样的相对误差，3D IoU 必然更低'

i2 = iou_axis_aligned((1., 1.), (0.1, 0.1))
i3 = iou_axis_aligned((1., 1., 1.), (0.1, 0.1, 0.1))
print(f'\\n每轴 10%: 2D {i2:.3f} vs 3D {i3:.3f}')
assert abs(i2 - 0.681) < 0.002 and abs(i3 - 0.574) < 0.002
print('✅ 三个乘子的直接后果：**2D 的 IoU 阈值不能照搬到 3D**')

# 卷积核也是同一个乘子
print(f'\\n卷积核：3×3 = {3**2} vs 3×3×3 = {3**3}  → {3**3/3**2:.0f}×')
Cin = Cout = 64
dense_flops = st[0.1]['total'] * 27 * Cin * Cout
print(f'r=0.1 m 的密集 3³ 卷积（{Cin}→{Cout}）= {dense_flops/1e9:.0f} GFLOP')
print(f'  而其中 {100*(1-st[0.1]["rate"]):.2f}% 的算力花在空格子上（模块 03 会拿回来）')"""),

    md("""## 6 · 小结

| 乘子 | 数值 | 在哪个模块被展开 |
|---|---|---|
| 网格规模 $(L/r)^3$ | $r{=}0.05$ m → 6.4 亿格 / **640 MB**（点云的 444×） | 01 |
| 占用率 | 9.43% → **0.018%**（降 518 倍） | 01 / 03 |
| **平均每格点数** | 1.99 → **1.03**（精细体素化不再压缩） | 01 |
| 量化误差上界 | $r\\sqrt3/2$（硬上界，实测吻合） | 01 |
| 均匀分布均值 | **$0.4804r$**；实测在 $r{=}0.5$ m 时大 1.20 倍，随 $r$ 减小降到 1.00 | 01 |
| 卷积核 $k^3$ | 27 而不是 9；密集 3³ 卷积 **283 GFLOP** | 03 |
| **IoU 的三个乘子** | 每轴 10%：2D **0.681** vs 3D **0.574** | 05 |"""),

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：体素化与统计

实现 `voxelize(pts, r, L=SCENE_L)`，返回 dict：

- `'idx'` —— `(M,3)` 的去重体素索引（按字典序排序）
- `'counts'` —— `(M,)` 每格的点数
- `'rate'` —— 占用率
- `'pts_per_voxel'` —— 平均每格点数
- `'saturated'` —— bool：`pts_per_voxel < 1.1`（**体素化已不再压缩**）

要求不用 Python 循环遍历点。"""),

    code("""def voxelize(pts, r, L=SCENE_L):
    \"\"\"返回 dict(idx, counts, rate, pts_per_voxel, saturated)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
for r in [0.5, 0.2, 0.1, 0.05]:
    v = voxelize(P, r)
    assert set(v) == {'idx', 'counts', 'rate', 'pts_per_voxel', 'saturated'}
    assert v['idx'].shape[1] == 3
    assert len(v['idx']) == len(v['counts'])
    assert v['counts'].sum() == len(P), '每个点必须恰好落进一格'
    # 与第 3 节的独立实现一致
    ref = voxel_stats(P, r)
    assert len(v['idx']) == ref['occupied'], (r, len(v['idx']), ref['occupied'])
    assert abs(v['rate'] - ref['rate']) < 1e-15
    # 索引已排序且去重
    assert len(np.unique(v['idx'], axis=0)) == len(v['idx'])

print(f\"{'r':>6s} {'非空格':>9s} {'占用率':>10s} {'每格点数':>10s} {'最多点数':>9s} {'饱和?':>7s}\")
for r in [0.5, 0.2, 0.1, 0.05]:
    v = voxelize(P, r)
    print(f'{r:6.2f} {len(v["idx"]):9,} {100*v["rate"]:9.4f}% '
          f'{v["pts_per_voxel"]:9.2f} {v["counts"].max():9d} {str(v["saturated"]):>7s}')

assert voxelize(P, 0.5)['saturated'] is False
assert voxelize(P, 0.05)['saturated'] is True
print('\\n✅ 练习 1 通过：`saturated` 一眼看出「再细分就是纯浪费」的分辨率')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def voxelize(pts, r, L=SCENE_L):
    idx = np.floor(np.asarray(pts, float) / r).astype(np.int64)
    uniq, counts = np.unique(idx, axis=0, return_counts=True)
    total = dense_voxel_count(L, r)
    ppv = len(pts) / len(uniq)
    return {'idx': uniq, 'counts': counts,
            'rate': len(uniq) / total,
            'pts_per_voxel': ppv,
            'saturated': bool(ppv < 1.1)}

v = voxelize(P, 0.05)
assert v['counts'].sum() == len(P) and v['saturated'] is True
print('✅ 参考答案 1 通过（np.unique(axis=0, return_counts=True) 一次拿到去重与计数）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：量化误差的两个常数

实现 `quant_stats(pts, r)`，返回 dict：

- `'max'`, `'mean'` —— 实测的最大/平均位移
- `'upper_bound'` —— 理论上界 $r\\sqrt3/2$
- `'uniform_mean'` —— 均匀分布的理论均值 $0.4804r$
- `'bound_ok'` —— bool：实测最大是否 $\\le$ 上界
- `'nonuniformity'` —— 实测均值 / 均匀理论均值（**> 1 说明点在格内不均匀**）

> 自测会顺带发现一件事：**不均匀度随 $r$ 减小单调下降到 1**（1.22 → 1.00）。
> 它其实是一个免费的探针，度量「体素尺度**以下**还有多少结构」。"""),

    code("""def quant_stats(pts, r, c_uniform=0.4804):
    \"\"\"返回 dict(max, mean, upper_bound, uniform_mean, bound_ok, nonuniformity)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# 参照物：在一个格子里放均匀点，nonuniformity 应当接近 1
rg = np.random.default_rng(7)
UNI = rg.uniform(0, 0.5, (200_000, 3))          # 恰好落在 r=0.5 的一格里
s_uni = quant_stats(UNI, 0.5)
assert set(s_uni) == {'max', 'mean', 'upper_bound', 'uniform_mean',
                      'bound_ok', 'nonuniformity'}
assert s_uni['bound_ok'] is True
assert abs(s_uni['nonuniformity'] - 1.0) < 0.02, \\
    f"均匀点的 nonuniformity 应当接近 1，实测 {s_uni['nonuniformity']:.3f}"
print(f"均匀参照: mean {s_uni['mean']:.4f}  理论 {s_uni['uniform_mean']:.4f}  "
      f"nonuniformity {s_uni['nonuniformity']:.3f}")

RS = [1.0, 0.5, 0.2, 0.1, 0.05, 0.02]
print(f\"\\n{'r':>6s} {'上界':>9s} {'实测max':>9s} {'实测mean':>10s} \"
      f\"{'均匀理论':>10s} {'不均匀度':>9s}\")
nu = []
for r in RS:
    st2 = quant_stats(P, r)
    nu.append(st2['nonuniformity'])
    assert st2['bound_ok'] is True, f'r={r} 超过上界'
    print(f'{r:6.2f} {st2["upper_bound"]:8.4f}m {st2["max"]:8.4f}m '
          f'{st2["mean"]:9.4f}m {st2["uniform_mean"]:9.4f}m '
          f'{st2["nonuniformity"]:8.3f}')

# ① 不均匀度恒 >= 1（点不可能比均匀分布更靠近中心太多），且**随 r 单调下降到 1**
assert all(v > 0.99 for v in nu)
assert nu == sorted(nu, reverse=True), f'不均匀度应随 r 减小而单调下降：{nu}'
assert nu[0] > 1.2 and nu[-1] < 1.01, (nu[0], nu[-1])
print(f'\\n不均匀度 {nu[0]:.3f} (r=1.0m) → {nu[-1]:.3f} (r=0.02m)，单调下降到 1')
print('  → 它度量的是「体素尺度**以下**还有多少结构」：')
print('    粗体素时地面点挤在某个面附近（1.22）；')
print(f'    而 r 小于地面抖动 σ=0.02m 的量级后，格内看起来就是均匀的（{nu[-1]:.3f}）')

# ② 上界随 r 严格线性
s1, s2 = quant_stats(P, 0.5), quant_stats(P, 0.25)
assert abs(s1['upper_bound'] / s2['upper_bound'] - 2.0) < 1e-12
print('\\n✅ 练习 2 通过：上界 r√3/2 是硬的、线性的；'
      '而 nonuniformity 是一个免费的「亚体素结构」探针')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def quant_stats(pts, r, c_uniform=0.4804):
    pts = np.asarray(pts, float)
    centers = (np.floor(pts / r) + 0.5) * r
    d = np.linalg.norm(pts - centers, axis=1)
    ub = r * np.sqrt(3) / 2
    um = c_uniform * r
    return {'max': float(d.max()), 'mean': float(d.mean()),
            'upper_bound': float(ub), 'uniform_mean': float(um),
            'bound_ok': bool(d.max() <= ub + 1e-12),
            'nonuniformity': float(d.mean() / um)}

assert quant_stats(P, 0.1)['bound_ok']
assert quant_stats(UNI, 0.5)['nonuniformity'] < 1.02
print('✅ 参考答案 2 通过')
print('   0.4804 不是随手写的常数：它是均匀立方体内到中心的平均距离，')
print('   本 notebook 第 4 节用 40 万个采样点验证过。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：表示选型器

实现 `pick_representation(need)`，`need` 是一个 dict：

| 键 | 含义 |
|---|---|
| `accuracy_m` | 需要的位置精度（米） |
| `needs_conv` | bool，是否要用卷积 |
| `memory_budget_mb` | 内存预算 |
| `scene_l` | 场景尺寸三元组 |
| `n_points` | 点数 |

返回 `(表示, 理由, 可用的最细体素分辨率或 None)`。规则：

1. `needs_conv` 为真 → 体素；此时算出**内存预算允许的最细 $r$**，
   并检查 $r\\sqrt3/2 \\le$ `accuracy_m`；不满足则返回 `'voxel_infeasible'`
2. 否则若点云内存 $\\le$ 预算 → 点云
3. 否则 → 隐式"""),

    code("""def pick_representation(need):
    \"\"\"返回 (representation, reason, finest_r or None)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
BASE = {'accuracy_m': 0.10, 'needs_conv': True, 'memory_budget_mb': 100.0,
        'scene_l': SCENE_L, 'n_points': N_PTS}

rep, why, r_fin = pick_representation(BASE)
print(f'需要卷积 + 100MB 预算 + 0.10m 精度 -> {rep} ({why}), 最细 r={r_fin}')
assert rep in ('voxel', 'voxel_infeasible')

print(f\"\\n{'精度要求':>9s} {'预算(MB)':>9s} {'要卷积':>7s} {'选择':>18s} {'最细 r':>9s}\")
for acc in [0.30, 0.10, 0.02]:
    for bud in [10.0, 100.0, 2000.0]:
        for conv in [True, False]:
            n = dict(BASE, accuracy_m=acc, memory_budget_mb=bud, needs_conv=conv)
            rep, why, rf = pick_representation(n)
            rs = 'None' if rf is None else f'{rf:.4f}'
            print(f'{acc:8.2f}m {bud:9.0f} {str(conv):>7s} {rep:>18s} {rs:>9s}')

# ① 要卷积、预算够、精度松 -> 体素可行
r1 = pick_representation(dict(BASE, accuracy_m=0.30, memory_budget_mb=100.))
assert r1[0] == 'voxel' and r1[2] is not None
assert r1[2] * np.sqrt(3) / 2 <= 0.30 + 1e-12

# ② 要卷积、精度苛刻 -> 体素不可行（内存撑不住那么细的 r）
r2 = pick_representation(dict(BASE, accuracy_m=0.02, memory_budget_mb=100.))
assert r2[0] == 'voxel_infeasible', r2
print(f'\\n0.02m 精度 + 100MB: {r2[0]} —— 需要 r <= '
      f'{0.02*2/np.sqrt(3):.4f}m，而预算只够 {r2[2]:.4f}m')

# ③ 不要卷积、点云装得下 -> 点云
r3 = pick_representation(dict(BASE, needs_conv=False, memory_budget_mb=100.))
assert r3[0] == 'point_cloud'

# ④ 不要卷积、连点云都装不下 -> 隐式
r4 = pick_representation(dict(BASE, needs_conv=False, memory_budget_mb=0.5))
assert r4[0] == 'implicit', r4
print('✅ 练习 3 通过：选型的关键是**把「精度要求」翻译成 r，再看内存装不装得下**')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def pick_representation(need):
    L = need['scene_l']
    budget_bytes = need['memory_budget_mb'] * 1e6
    # 预算允许的最细 r：(L0/r)(L1/r)(L2/r) * 1 byte <= budget
    finest_r = (np.prod(L) / budget_bytes) ** (1.0 / 3.0)

    if need['needs_conv']:
        if finest_r * np.sqrt(3) / 2 <= need['accuracy_m'] + 1e-12:
            return 'voxel', 'conv_needed_and_affordable', float(finest_r)
        return ('voxel_infeasible',
                'accuracy_requires_finer_r_than_memory_allows', float(finest_r))

    pc_bytes = need['n_points'] * 3 * 4
    if pc_bytes <= budget_bytes:
        return 'point_cloud', 'exact_and_fits', None
    return 'implicit', 'resolution_independent_memory', None

assert pick_representation(dict(BASE, accuracy_m=0.30))[0] == 'voxel'
assert pick_representation(dict(BASE, accuracy_m=0.02))[0] == 'voxel_infeasible'
print('✅ 参考答案 3 通过')
print('   注意 finest_r 的解法：内存约束是 ∏(L_i/r) ≤ B，所以 r ≥ (∏L_i / B)^(1/3)')
print('   —— 而 1/3 次方正是「第一个乘子」的反面：预算翻 8 倍才能把 r 减半。')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：三个乘子的换算器

实现 `multiplier_report(dims, rel_err)`，`dims` 是 2 元或 3 元的尺寸元组，
返回 dict：

- `'iou'` —— 每轴相对误差为 `rel_err` 时的 IoU
- `'grid_cells'` —— `{r: 格数}`，对 `r in (0.5, 0.1)`，场景取 `SCENE_L`
- `'kernel_ops'` —— $3^{\\text{dim}}$
- `'max_rel_err_at_iou50'` —— 反解：IoU 恰好 0.5 时每轴允许的相对误差

然后用它对比 2D 与 3D。"""),

    code("""def multiplier_report(dims, rel_err, L=SCENE_L):
    \"\"\"返回 dict(iou, grid_cells, kernel_ops, max_rel_err_at_iou50)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
r2 = multiplier_report((1., 1.), 0.10)
r3 = multiplier_report((1., 1., 1.), 0.10)
for r in (r2, r3):
    assert set(r) == {'iou', 'grid_cells', 'kernel_ops', 'max_rel_err_at_iou50'}

print(f\"{'维度':>5s} {'IoU@10%':>9s} {'核算子':>7s} {'IoU=0.5 允许的每轴相对误差':>26s}\")
for d, rr in [(2, r2), (3, r3)]:
    print(f'{d:4d}D {rr["iou"]:9.3f} {rr["kernel_ops"]:7d} '
          f'{rr["max_rel_err_at_iou50"]:25.1%}')

assert r3['iou'] < r2['iou'], '同样相对误差下 3D IoU 更低'
assert abs(r2['iou'] - 0.681) < 0.002 and abs(r3['iou'] - 0.574) < 0.002
assert r3['kernel_ops'] == 27 and r2['kernel_ops'] == 9
assert r3['max_rel_err_at_iou50'] < r2['max_rel_err_at_iou50'], \\
    '3D 允许的误差更小'

# 反解出来的阈值代回去，应当正好给 0.5
for rr, dims in [(r2, (1., 1.)), (r3, (1., 1., 1.))]:
    e = rr['max_rel_err_at_iou50']
    got = iou_axis_aligned(dims, tuple([e] * len(dims)))
    assert abs(got - 0.5) < 1e-6, (dims, e, got)
print('\\n反解自洽：把允许误差代回去都给出 IoU = 0.500')

# 网格规模：r 从 0.5 到 0.1 -> 2D 25 倍、3D 125 倍
g2 = r2['grid_cells']; g3 = r3['grid_cells']
print(f'\\nr 0.5 -> 0.1 的格数增长: 2D {g2[0.1]/g2[0.5]:.0f}×  '
      f'3D {g3[0.1]/g3[0.5]:.0f}×')
assert abs(g2[0.1]/g2[0.5] - 25) < 1e-6
assert abs(g3[0.1]/g3[0.5] - 125) < 1e-6
print('✅ 练习 4 通过：三个乘子在一个函数里被同时算出来——')
print('   而它们解释了本课后面五个模块的全部设计动机')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def multiplier_report(dims, rel_err, L=SCENE_L):
    n = len(dims)
    cells = {}
    for r in (0.5, 0.1):
        cells[r] = int(np.prod([L[i] / r for i in range(n)]))
    # 反解：同尺寸框、每轴相对误差 e -> IoU = (1-e)^n / (2 - (1-e)^n)
    # 令它 = 0.5  =>  (1-e)^n = 2/3  =>  e = 1 - (2/3)^(1/n)
    e50 = 1.0 - (2.0 / 3.0) ** (1.0 / n)
    return {'iou': iou_axis_aligned(dims, tuple([rel_err] * n)),
            'grid_cells': cells,
            'kernel_ops': 3 ** n,
            'max_rel_err_at_iou50': float(e50)}

for dims in [(1., 1.), (1., 1., 1.)]:
    rr = multiplier_report(dims, 0.10)
    assert abs(iou_axis_aligned(dims,
               tuple([rr['max_rel_err_at_iou50']] * len(dims))) - 0.5) < 1e-9
print('✅ 参考答案 4 通过')
print('   闭式解值得记：IoU = q/(2−q) 其中 q = (1−e)^n，')
print('   所以 IoU=0.5 ⇔ q=2/3 ⇔ e = 1 − (2/3)^(1/n)：')
print(f'     2D: {1-(2/3)**0.5:.1%}   3D: {1-(2/3)**(1/3):.1%}'
      f'   → **维数越高，允许的相对误差越小**')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) 真实点云的读取（本课用合成场景，因为要知道真值）──
#   KITTI: 每点 4 个 float32 (x, y, z, intensity)
pts = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)
#   nuScenes: 5 个 (x, y, z, intensity, ring_index)
#   ⚠️ 坐标系各家不同 —— 而 C72 模块 00 的第一条纪律是「坐标系约定先钉死」

# ── 2) 体素化：真实实现用哈希而不是 np.unique ──
#   spconv / MinkowskiEngine 内部都是哈希表 + 坐标键
import spconv.pytorch as spconv
voxels, coords, num_pts = spconv.utils.PointToVoxel(
    vsize_xyz=[0.05, 0.05, 0.1],          # ← 注意 z 常用更粗的分辨率
    coors_range_xyz=[0, -50, -3, 100, 50, 5],
    max_num_points_per_voxel=5,           # ← 练习 1 的 counts.max() 告诉你该设多少
    max_num_voxels=120_000,               # ← 由占用率算出来（第 3 节）
)(torch.from_numpy(pts))
#   ↑ 这两个上限设小了会**静默丢点**，而它们的正确值就是本 notebook 算的那两个数

# ── 3) 分辨率选择：把「精度要求」翻译成 r（练习 3）──
#   量化误差上界 = r√3/2，所以 r <= 2 * accuracy / √3
r_max_by_accuracy = 2 * required_accuracy_m / np.sqrt(3)
#   而内存约束给出下界：r >= (scene_volume / byte_budget) ** (1/3)
#   两者交集为空 -> 密集体素方案不可行，必须上稀疏（模块 03）或点云（模块 02）

# ── 4) 评测：3D 的 IoU 阈值不能照搬 2D（第 5 节）──
#   KITTI 用 0.7（车）/ 0.5（行人、骑车人）—— 而这个区分正是因为三个乘子：
#   同样的绝对误差，小目标的 IoU 掉得快得多（模块 05 会精确算出来）
```

> **落地顺序建议**：先用练习 1 算出你数据上的 `pts_per_voxel` 与 `counts.max()`
> （它们直接决定 `max_num_points_per_voxel` 与 `max_num_voxels` 该设多少，
> 而设错会静默丢点），再用练习 3 检查你的分辨率与精度要求是否自相矛盾。"""),
]
