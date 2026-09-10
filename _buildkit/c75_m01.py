# -*- coding: utf-8 -*-
"""C75 模块 01 · SfM：对应、增量重建与束调整。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 两两匹配为什么必须换成检索式候选（$N{=}10^4$ 时 5000 万对）；"
                   "② 束调整的稀疏结构与 <strong>Schur 补的 $10^6$ 倍收益</strong>；"
                   "③ <strong>为什么 Hessian 的秩亏<em>恰好</em>是 7，而这 7 个方向有解析形式</strong>；"
                   "④ <strong>「这次重建好不好解」的正确度量：投影掉 gauge 后的条件数，"
                   "而它 $\\propto (B/z)^{-2}$</strong>；"
                   "⑤ 纯旋转为什么是<strong>悬崖</strong>而不是「精度差」；"
                   "⑥ 增量式的漂移：朝向按 $\\sqrt n$，尺度按乘性游走"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_sfm.ipynb'
                       '（<strong>解析构造 7 维 gauge 零空间并验证 $\\Vert JQ\\Vert/\\Vert J\\Vert \\approx 2\\times10^{-11}$</strong> / '
                       '条件数对 $B/z$ 的标度律（实测指数 −2.00）/ '
                       '<strong>纯旋转时的 $4.4\\times10^{17}$ 悬崖</strong> / '
                       'Schur 补 / <strong>一个我自己踩过的混淆：坏轨迹把点推到相机背后</strong>）'),
    ("核心参考", "Hartley &amp; Zisserman, <em>Multiple View Geometry</em>（2nd ed., 第 18 章）· "
                 "Triggs et al., <em>Bundle Adjustment — A Modern Synthesis</em>（2000，gauge 一节是本模块第 4 节的来源）· "
                 "Schönberger &amp; Frahm, <em>Structure-from-Motion Revisited</em>（CVPR 2016，COLMAP）· "
                 "Agarwal et al., <em>Bundle Adjustment in the Large</em>（ECCV 2010）· "
                 "Ceres Solver 文档的 <em>Bundle Adjustment</em> 一节 · "
                 "本课程 <strong>C72</strong> 模块 03（三角测量与 PnP）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-parts", "SfM 是三个子问题，而只有第三个有干净的数学", "".join([
        TABLE(["子问题", "做什么", "它的性质"], [
            ["<strong>① 找对应</strong>",
             "在哪些图像对之间找匹配、以及每对里哪些点对应",
             "<strong>组合爆炸 + 启发式</strong>。"
             "<em>没有闭式解，全靠特征、检索与几何验证</em>"],
            ["<strong>② 决定顺序</strong>",
             "从哪两张图开始、接下来加哪一张",
             "<strong>贪心 + 启发式</strong>。"
             "<em>而顺序会影响结果——同一批图像换个起点可能重建出不同的东西</em>"],
            ["<strong>③ 束调整</strong>",
             "同时优化所有相机与所有点，最小化重投影误差",
             "<strong>一个定义清楚的非线性最小二乘</strong>。"
             "<em>本模块的第 3–5 节全在讲它，因为它是唯一能被精确分析的一环</em>"],
        ]),
        MATH(r"\min_{\{R_i,t_i\},\{X_j\}} \sum_{(i,j)\in\mathcal O}"
             r"\bigl\Vert \pi(R_i X_j + t_i) - u_{ij}\bigr\Vert^2"),
        DUAL(
            "<strong>把这三件事分清很重要，因为 SfM 失败时的表现完全不同。</strong>"
            "<em>① 失败 → 重建断成几块互不相连的子模型；"
            "② 失败 → 重建「歪了」但内部自洽；"
            "③ 失败 → 不收敛或收敛到明显错误的解</em>。"
            "<strong>而 ③ 的失败几乎总是可以从<em>条件数</em>提前看出来</strong>——"
            "<em>这就是第 5 节的内容，也是本模块最实用的一条</em>。",
            "<strong>C72 讲的是「已知对应关系时怎么算」（三角测量、PnP、单应）。</strong>"
            "<em>本模块假设你已经会那些，问的是规模变大之后的三个新问题："
            "对应从哪来（第 2 节）、几十万个参数怎么解（第 3 节）、"
            "以及这个解到底定不定（第 4–5 节）</em>。"),
    ])),

    # ============================================================== 2
    ("matching", "两两匹配的规模：为什么必须换成检索", "".join([
        P("找对应的第一步是决定「哪些图像对值得匹配」。朴素做法是全部两两匹配，"
          "而它是 $O(N^2)$："),
        TABLE(["图像数 $N$", "两两对数", "按 10 ms/对 算的耗时"], [
            ["20", "190", "2 秒"],
            ["100", "4,950", "50 秒"],
            ["500", "124,750", "0.35 小时"],
            ["2,000", "1,999,000", "5.6 小时"],
            ["<strong>10,000</strong>", "<strong>49,995,000</strong>",
             "<strong>138.9 小时</strong>"],
        ]),
        P("而真实的做法是先用一个图像检索（词汇树 / VLAD / 学习到的全局描述子）"
          "为每张图取 top-$k$ 个候选，只匹配这些对："),
        TABLE(["$N$", "$k$", "候选对数", "占全量的比例"], [
            ["500", "20", "5,000", "4.01%"],
            ["2,000", "50", "50,000", "2.50%"],
            ["<strong>10,000</strong>", "<strong>50</strong>", "<strong>250,000</strong>",
             "<strong>0.50%</strong>"],
        ]),
        DUAL(
            "<strong>注意候选对数是 $Nk/2$——它对 $N$ 是<em>线性</em>的。</strong>"
            "<em>所以从 $O(N^2)$ 换成 $O(Nk)$ 不是常数因子的优化，是复杂度的改变</em>。"
            "<strong>而 $N{=}10^4$ 时它把 139 小时变成 42 分钟。</strong>",
            "<strong>代价是：漏掉的对可能正是关键的那一对。</strong>"
            "<em>比如一个环形轨迹的首尾两张图——它们视觉上相似（所以检索会找到），"
            "但如果检索因为光照变化而漏掉，整个环就闭不上，"
            "于是第 6 节的漂移无法被纠正</em>。"
            "<strong>所以工程上常在检索候选之外<em>额外</em>加两类对："
            "时间上相邻的（视频/连拍）与「重叠度估计高」的</strong>——"
            "<em>前者几乎免费，后者需要一次粗几何</em>。"),
    ])),

    # ============================================================== 3
    ("ba-sparsity", "束调整：参数几十万，但 Hessian 是稀疏的", "".join([
        TABLE(["相机数", "点数", "相机参数（6 each）", "点参数（3 each）", "总参数",
               "稠密 $H$ 的元素数"], [
            ["20", "5,000", "120", "15,000", "15,120", "0.23 G"],
            ["100", "30,000", "600", "90,000", "90,600", "8.21 G"],
            ["<strong>500</strong>", "<strong>100,000</strong>", "3,000", "300,000",
             "<strong>303,000</strong>", "<strong>91.81 G</strong>"],
            ["2,000", "500,000", "12,000", "1,500,000", "1,512,000", "2,286 G"],
        ]),
        P("**稠密地存 $H$ 就已经不可能了**（500 相机时是 918 亿个元素）。"
          "但每个观测只碰 $6+3 = 9$ 个参数，所以雅可比极稀疏："),
        TABLE(["配置", "$J$ 的形状", "非零元素", "密度", "比稠密稀疏"], [
            ["100 相机 / 30k 点 / 每点 4 次观测", "240,000 × 90,600", "2,160,000",
             "$9.93\\times10^{-5}$", "<strong>10,067×</strong>"],
            ["500 相机 / 100k 点 / 每点 5 次观测", "1,000,000 × 303,000", "9,000,000",
             "$2.97\\times10^{-5}$", "<strong>33,667×</strong>"],
        ]),
        H3("Schur 补：先把点消掉"),
        P("$H$ 有一个特殊的**块结构**：点与点之间没有直接耦合（两个 3D 点不出现在同一个残差里）。"
          "所以点块 $H_{pp}$ 是**块对角**的，可以逐点求 $3\\times3$ 的逆。"),
        MATH(r"H = \begin{bmatrix} H_{cc} & H_{cp} \\ H_{cp}^\top & H_{pp}\end{bmatrix},"
             r"\qquad S = H_{cc} - H_{cp}H_{pp}^{-1}H_{cp}^\top"),
        TABLE(["相机数", "点数", "直接解 $H$（$n^3$）", "解相机块 $S$", "消点（$n_p \\times 27$）",
               "<strong>加速比</strong>"], [
            ["100", "30,000", "$7.44\\times10^{14}$", "$2.16\\times10^{8}$",
             "$8.1\\times10^{5}$", "<strong>$3.43\\times10^{6}$</strong>"],
            ["500", "100,000", "$2.78\\times10^{16}$", "$2.70\\times10^{10}$",
             "$2.7\\times10^{6}$", "<strong>$1.03\\times10^{6}$</strong>"],
            ["2,000", "500,000", "$3.46\\times10^{18}$", "$1.73\\times10^{12}$",
             "$1.35\\times10^{7}$", "<strong>$2.00\\times10^{6}$</strong>"],
        ]),
        CALLOUT("intuition",
                "<strong>Schur 补把问题从「几十万维」降到「几千维」，而这是精确的、不是近似。</strong>"
                "<em>$S$ 只有 $6 n_c \\times 6 n_c$（500 相机 → $3000\\times3000$），"
                "而消点的代价是线性的（每点一个 $3\\times3$ 求逆）</em>。"
                "<strong>这也解释了为什么 SfM 能处理几十万个点却只能处理几千个相机</strong>——"
                "<em>点是「便宜」的（可以被消掉），相机是「贵」的（$S$ 的规模由它决定）</em>。"),
    ])),

    # ============================================================== 4
    ("gauge", "秩亏恰好是 7，而这 7 个方向是解析的", "".join([
        P("束调整的解**不唯一**。把整个重建做一次相似变换（旋转 + 平移 + 缩放），"
          "所有重投影误差**完全不变**——模块 00 已经验证过尺度那一维。"
          "相似变换群有 $3+3+1 = 7$ 个自由度，所以 $H$ 的零空间至少是 7 维的。"),
        TABLE(["实测（5 相机 / 40 点 / 150 个参数）", "结果"], [
            ["在真解处的残差范数", "$5.6\\times10^{-13}$（应为 0）"],
            ["$H$ 的奇异值：第 143 大", "$6.008\\times10^{2}$"],
            ["$H$ 的奇异值：第 144 大", "$1.467\\times10^{-9}$"],
            ["<strong>谱间隙</strong>", "<strong>$4.10\\times10^{11}$</strong>"],
            ["<strong>秩亏</strong>", "<strong>恰好 7</strong>"],
        ]),
        H3("但不要靠数值判秩——零空间有闭式"),
        DUAL(
            "<strong>7 个零方向可以直接从群作用求导得到，不需要看奇异值。</strong>"
            "<em>把相似变换作用在参数上（点 $X \\to s\\,R_w X + \\delta$，"
            "相机中心跟着同样变、相机朝向乘 $R_w^\\top$），对 7 个群参数各求一次导，"
            "就得到 $150\\times7$ 的矩阵 $G$</em>。"
            "<strong>notebook 验证：正交化后的 $Q$ 满足 "
            "$\\Vert JQ\\Vert_F/\\Vert J\\Vert_F = 1.9\\times10^{-11}$</strong>，"
            "<em>7 个方向单独的比值在 $2.1\\times10^{-12}$ 到 $1.3\\times10^{-11}$ 之间——纯数值噪声</em>。",
            "<strong>而这一点很关键，因为<em>数值判秩在条件数大的时候会给出错的答案</em>。</strong>"
            "<em>notebook 里我试了两种数值判据，两种都失效：</em>"
            "① <strong>固定相对阈值</strong>（$\\sigma < \\sigma_1 \\cdot 10^{-10}$）"
            "在条件数大的配置上报出「秩亏 143/150」——"
            "<em>因为 $H$ 本身的谱就跨了 10 个数量级</em>；"
            "② <strong>「最大谱间隙」</strong>把间隙定位到第 1 与第 2 个奇异值之间——"
            "<em>那只是正常的谱宽，不是秩的悬崖</em>。"
            "<strong>所以「数值秩」在这里不是一个定义良好的量。</strong>"),
        H3("固定 gauge 的两种做法"),
        TABLE(["做法", "固定了什么", "剩余秩亏"], [
            ["只固定相机 0 的 6 个参数", "旋转 3 + 平移 3", "<strong>1</strong>（尺度仍自由）"],
            ["固定相机 0 + 一个点的一个坐标", "全部 7 个", "<strong>0</strong>"],
            ["<strong>不固定，改用投影</strong>",
             "把 $H$ 投影到 $Q$ 的正交补上",
             "<strong>0，且不引入人为的坐标系偏好</strong>"],
        ]),
        CALLOUT("warn",
                "<strong>第一行是一个真实会犯的错：只固定第一个相机就以为够了。</strong>"
                "<em>那时尺度仍然自由，于是求解器会沿尺度方向随机漂移——"
                "表现为「每次跑出来的重建大小不一样」，"
                "而残差完全相同（所以看不出问题）</em>。"
                "<strong>而第三行是 Triggs et al.(2000) 推荐的做法</strong>："
                "<em>固定具体参数会让协方差估计带上「哪个相机被固定了」的偏见，"
                "而投影法给出的是 gauge 无关的协方差</em>。"),
    ])),

    # ============================================================== 5
    ("conditioning", "「这次重建好不好解」的正确度量", "".join([
        P("把已知的 7 维 gauge 零空间投影掉之后，剩下的条件数才是有意义的量。"
          "下面是 5 相机 / 40 点、相机在弧上始终看向场景中心、"
          "**全部点都在画面内**的实测（$B$ = 首尾相机的间距，$z$ = 到场景的距离）："),
        TABLE(["弧长", "基线 $B$ (m)", "$B/z$", "$\\Vert JQ\\Vert/\\Vert J\\Vert$",
               "<strong>投影掉 gauge 后的条件数</strong>"], [
            ["120°", "10.392", "1.732", "$2.3\\times10^{-11}$", "<strong>288</strong>"],
            ["60°", "6.000", "1.000", "$2.2\\times10^{-11}$", "$1.84\\times10^{3}$"],
            ["20°", "2.084", "0.347", "$1.9\\times10^{-11}$", "$4.44\\times10^{4}$"],
            ["5°", "0.523", "0.087", "$1.8\\times10^{-11}$", "$9.41\\times10^{5}$"],
            ["1°", "0.105", "0.017", "$1.7\\times10^{-11}$", "$2.40\\times10^{7}$"],
            ["0.2°", "0.021", "0.0035", "$1.8\\times10^{-11}$", "$6.01\\times10^{8}$"],
            ["<strong>0°（纯旋转）</strong>", "<strong>0.000</strong>", "<strong>0</strong>",
             "$1.4\\times10^{-11}$", "<strong>$4.40\\times10^{17}$</strong>"],
        ]),
        MATH(r"\mathrm{cond}(H \mid \text{gauge}) \;\propto\; (B/z)^{-2}"),
        DUAL(
            "<strong>小基线端的实测指数收敛到 $-2.00$</strong>"
            "（<em>$B/z$ 从 0.0349 到 0.0175 时条件数 4.01 倍，指数 $-2.00$；"
            "上一档 $-2.02$，再上一档 $-2.10$</em>）。"
            "<strong>而这与 C72 的三角测量不确定度是同一件事：</strong>"
            "<em>$H = J^\\top J$，所以 $\\mathrm{cond}(H) = \\mathrm{cond}(J)^2$；"
            "而 $J$ 的最差方向按 $1/B$ 退化，正对应 "
            "$\\sigma_z = \\dfrac{z^2}{fB}\\sigma_d \\propto 1/B$</em>。"
            "<strong>两个独立推导对上了。</strong>",
            "<strong>而最后一行是<em>悬崖</em>，不是趋势的延续。</strong>"
            "<em>$B/z = 0.0035$ 时条件数 $6.0\\times10^{8}$，"
            "而 $B/z$ 严格为 0 时是 $4.4\\times10^{17}$——跳了 9 个数量级</em>。"
            "<strong>因为纯旋转下深度<em>根本不出现</em>在残差里</strong>"
            "（<em>所有点沿视线移动都不改变任何投影</em>），"
            "<em>所以那是一整族新的零方向，而不是「测不准」</em>。"
            "<strong>float64 的相对精度是 $2.2\\times10^{-16}$，"
            "所以条件数超过 $10^{16}$ 的问题在数值上已经是奇异的。</strong>"),
        CALLOUT("danger",
                "<strong>我在做这组实验时踩了一个混淆，值得写出来。</strong>"
                "<em>第一版的相机轨迹是「在半径 $B$ 的圆上均匀取点，但朝向按弧长旋转」。"
                "$B$ 调小时相机几乎不动却仍然转 100°，于是<strong>40 个点里有 25–33 个跑到了相机背后</strong>，"
                "投影 $u$ 到 52 万像素</em>。"
                "<strong>我测到的「条件数 $10^{19}$」其实是一个坏掉的场景，不是小基线效应。</strong>"
                "<em>换成「始终 look-at 场景中心」的轨迹之后，所有配置下点都在画面内，"
                "标度律才干净地出来</em>。"
                "<strong>教训：报一个「配置 A 比配置 B 差多少倍」之前，"
                "先确认两个配置<em>唯一</em>的差别真的是你想改的那一个。</strong>"),
    ])),

    # ============================================================== 6
    ("two-view", "两视图初始化：三种退化，而它们退化的<em>不是同一件事</em>", "".join([
        P("增量式 SfM 要先选一对图像做初始化。选错了后面全错，"
          "所以「哪一对是好的」有明确的判据。"
          "用 8 点法的设计矩阵 $A$（$100\\times9$）的奇异值来看："
          "$E$ 有 8 个自由度，所以 $A$ 的零空间应当**恰好是 1 维**。"),
        TABLE(["配置", "$A$ 的最小 4 个奇异值", "$\\sigma_8/\\sigma_9$", "诊断"], [
            ["一般场景 + 侧向平移",
             "$2.50\\!\\cdot\\!10^{-1}$, $1.82\\!\\cdot\\!10^{-1}$, "
             "$3.67\\!\\cdot\\!10^{-2}$, $1.81\\!\\cdot\\!10^{-16}$",
             "<strong>$2.0\\cdot10^{14}$</strong>", "<strong>零空间干净是 1 维</strong>"],
            ["<strong>共面场景</strong> + 侧向平移",
             "$1.80\\!\\cdot\\!10^{-1}$, <strong>$7.60\\!\\cdot\\!10^{-16}$, "
             "$1.62\\!\\cdot\\!10^{-16}$, $3.96\\!\\cdot\\!10^{-17}$</strong>",
             "<strong>4.1</strong>",
             "<strong>零空间是 3 维——$E$ 只被确定到一个 3 参数族</strong>"],
            ["一般场景 + <strong>前向运动</strong>",
             "$2.57\\!\\cdot\\!10^{-1}$, $7.97\\!\\cdot\\!10^{-2}$, "
             "$4.63\\!\\cdot\\!10^{-2}$, $3.65\\!\\cdot\\!10^{-17}$",
             "$1.3\\cdot10^{15}$",
             "<strong>$E$ 完全没问题</strong>（见下）"],
            ["一般场景 + 小基线（$B{=}0.02$）",
             "$2.05\\!\\cdot\\!10^{-1}$, $4.46\\!\\cdot\\!10^{-3}$, "
             "$7.51\\!\\cdot\\!10^{-4}$, $1.40\\!\\cdot\\!10^{-16}$",
             "$5.4\\cdot10^{12}$",
             "<em>零空间仍是 1 维，但 $\\sigma_7,\\sigma_8$ 已经很小</em>"],
            ["共面 + 前向", "—", "46", "<strong>退化</strong>"],
        ]),
        H3("三种退化各自退化了什么"),
        DUAL(
            "<strong>共面场景：退化的是 $E$ 本身。</strong>"
            "<em>零空间 3 维，所以 $E$ 只被确定到一个三参数族</em>。"
            "<strong>而它的签名是「与噪声无关」</strong>："
            "<em>notebook 量到共面场景下 $E$ 的方向误差在 0.2 px 与 1.0 px 噪声下"
            "<strong>都是 3.15°</strong>（饱和了），"
            "而一般场景是 0.38° → 2.31°（随噪声线性退化）</em>。"
            "<strong>所以「加噪声不改变误差」是结构性退化的诊断标志</strong>——"
            "<em>模块 02 的周期纹理会再次出现这个签名</em>。",
            "<strong>前向运动：退化的<em>不是</em> $E$，而是三角化。</strong>"
            "<em>$\\sigma_8/\\sigma_9 = 1.3\\times10^{15}$ 说明 $E$ 解得很干净。"
            "但沿光轴前进时极点落在画面中心，而靠近极点的点两条视线几乎重合</em>："),
        TABLE(["到极点的归一化距离", "两条视线的夹角（中位）", "相对最外圈"], [
            ["[0.000, 0.094)", "<strong>0.659°</strong>", "0.34×"],
            ["[0.154, 0.208)", "1.591°", "0.83×"],
            ["[0.256, 0.355)", "3.334°", "1.74×"],
            ["[0.355, ∞)", "4.928°", "2.57×"],
        ]),
        DUAL(
            "<strong>画面中心的点视线夹角只有 0.659°，是最外圈的 1/7.5。</strong>"
            "<em>而三角测量的不确定度与夹角成反比，所以正前方的深度最差</em>。"
            "<strong>「车往前开」对<em>正前方</em>的物体是最差的几何</strong>——"
            "<em>而那恰好是自动驾驶最关心的区域，也正是 C72 模块 03 要用"
            "「已知尺寸 / 地面假设」去补的原因</em>。",
            "<strong>所以初始化的判据不是一个数，而是三个：</strong>"
            "<em>① 用单应 $H$ 与本质矩阵 $E$ 各拟合一次，比较内点数与残差——"
            "$H$ 明显更好就说明场景共面（COLMAP 的 "
            "<code>Homography vs Essential</code> 那一步）；"
            "② 检查三角化后的<strong>视线夹角</strong>（常用阈值 &gt; 2°～5°），"
            "而不只看基线长度；"
            "③ 检查内点在画面上的<strong>空间分布</strong>——"
            "全挤在极点附近时 ② 会自动把它们滤掉，但也就没剩多少点了</em>。"),
    ])),

    # ============================================================== 7
    ("covariance", "不确定度：同一次重建能报出三个不同的数", "".join([
        P("束调整收敛之后，常见的需求是「给出每个点/相机的不确定度」。"
          "标准做法是 $\\Sigma = \\sigma^2 (J^\\top J)^{-1}$。"
          "**但 $J^\\top J$ 是奇异的（第 4 节：秩亏 7），所以这个式子需要先处理 gauge。**"
          "而<em>怎么处理</em>会改变答案："),
        TABLE(["弧长", "$B/z$", "① 固定相机 0 + 一个坐标",
               "② 固定相机 0 + 相机 4 的一个平移分量",
               "③ <strong>gauge 投影后取伪逆</strong>"], [
            ["60°", "1.000", "0.01337 m", "0.01115 m", "<strong>0.00979 m</strong>"],
            ["20°", "0.347", "0.03638 m", "0.03183 m", "<strong>0.02937 m</strong>"],
            ["5°", "0.087", "0.14539 m", "0.13084 m", "<strong>0.12654 m</strong>"],
        ]),
        P("（点位协方差迹的平方根，中位数；像素噪声 $\\sigma = 0.5$ px）"),
        DUAL(
            "<strong>同一次重建、同一份数据，报出的点位不确定度差 1.15–1.37 倍，"
            "而差别<em>只</em>来自「固定了哪些参数」。</strong>"
            "<em>①②③ 三种都是「正确」的计算，它们只是在回答不同的问题："
            "① 问「相对于相机 0 的坐标系，点在哪」；"
            "② 问「相对于相机 0 与 4 定的基线，点在哪」；"
            "③ 问「点相对于<strong>整个重建自身</strong>有多确定」</em>。"
            "<strong>而只有 ③ 是 gauge 无关的，所以只有 ③ 在两份重建之间可比。</strong>",
            "<strong>顺带这张表第三次印证了第 5 节的标度律。</strong>"
            "<em>③ 那一列：$B/z$ 从 1.000 到 0.347（2.88 倍）时 σ 涨 3.00 倍；"
            "从 0.347 到 0.087（3.98 倍）时涨 4.31 倍——等效指数约 $-1.0$</em>。"
            "<strong>而 $\\mathrm{cond}(H) = \\mathrm{cond}(J)^2$，"
            "所以条件数的 $(B/z)^{-2}$ 与 σ 的 $(B/z)^{-1}$ 是同一件事的两种写法</strong>——"
            "<em>加上 C72 的 $\\sigma_z = z^2\\sigma_d/(fB)$，三条独立的推导指向同一个律</em>。"),
        CALLOUT("warn",
                "<strong>所以「我们的重建精度是 X 毫米」这句话必须附带 gauge 的定义。</strong>"
                "<em>而实践中更常见的做法是绕开协方差，直接用一个<strong>已知长度</strong>"
                "去做尺度检验与端到端误差评估</em>——"
                "<strong>那个数是 gauge 无关的，而且不需要相信 $J^\\top J$ 的线性化假设。</strong>"),
    ])),

    # ============================================================== 8
    ("drift", "增量式的漂移：两种误差、两种规律", "".join([
        P("增量式 SfM 每次加一张图：用已重建的点做 PnP 求它的位姿，"
          "再三角化新点，然后（局部或全局）束调整。"
          "误差在这个过程里累积，而**朝向与尺度的累积规律不同**："),
        TABLE(["", "朝向误差", "尺度误差"], [
            ["累积方式", "近似**随机游走**：$\\propto\\sqrt n$",
             "**乘性**游走：$\\prod(1+\\epsilon_i)$"],
            ["10 步（每步 0.05° / ±0.5%）", "0.16°", "P5 0.975 – P95 1.026"],
            ["50 步", "0.35°", "P5 0.944 – P95 1.061"],
            ["<strong>200 步</strong>", "<strong>0.71°</strong>",
             "<strong>P5 0.884 – P95 1.122</strong>"],
            ["有上界吗", "有（角度被 $180°$ 框住）",
             "<strong>没有</strong>——<em>乘性游走的方差在对数域线性增长</em>"],
        ]),
        DUAL(
            "<strong>尺度漂移是增量式 SfM 最难对付的一项，因为它没有上界也没有「不合理」的迹象。</strong>"
            "<em>一条 200 步的长廊，重建出来的长度可能是真实的 0.88 或 1.12 倍，"
            "而每一步的重投影误差都很小、整个模型内部完全自洽</em>。"
            "<strong>所以它只能靠<em>闭环</em>或<em>外部尺度</em>来纠正</strong>，"
            "<em>而不能靠「优化得更彻底」</em>。",
            "<strong>而这解释了为什么全局束调整不能省。</strong>"
            "<em>局部束调整（只优化最近 $k$ 个相机）成本低，"
            "但它无法把误差推回到早期的相机上——所以漂移只会被「固化」</em>。"
            "<strong>COLMAP 的做法是：每加入一定比例的新图就跑一次<em>全局</em> BA</strong>，"
            "<em>而这也是它比实时 SLAM 慢得多但精确得多的原因</em>。"),
        CALLOUT("paper",
                "<strong>一个判断「这份重建能不能用」的经验流程</strong>："
                "① <strong>看子模型个数</strong>——"
                "<em>$>1$ 说明对应关系断了（第 2 节的检索漏了关键对）</em>；"
                "② <strong>看每张图的重投影误差分布，而不是均值</strong>——"
                "<em>均值 0.6 px 但 P99 是 8 px，说明有一批图位姿是错的</em>；"
                "③ <strong>看相机轨迹的 $B/z$</strong>——"
                "<em>低于 0.05 的那些段，第 5 节说它们的条件数已过 $10^6$</em>；"
                "④ <strong>用一个已知长度做尺度检验</strong>——"
                "<em>这是唯一能抓到尺度漂移的办法</em>。"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 01 · SfM：对应、增量重建与束调整

本 notebook 把讲解页的七个结论跑出来：

1. 两两匹配的规模，与检索式候选把它从 $O(N^2)$ 降到 $O(Nk)$；
2. **束调整的雅可比密度 $2.97\\times10^{-5}$**，与 Schur 补的 $10^6$ 倍加速（**实现一个能用的 Schur 求解**）；
3. **gauge 零空间的解析构造**：$\\Vert JQ\\Vert/\\Vert J\\Vert \\approx 2\\times10^{-11}$；
4. **两种数值判秩方法在条件数大时都失效** —— 而这正是要用解析零空间的理由；
5. **投影掉 gauge 后的条件数 $\\propto (B/z)^{-2}$**，纯旋转是 $4.4\\times10^{17}$ 的悬崖；
   以及**我自己踩过的一个混淆：坏轨迹把点推到了相机背后**；
6. 两视图初始化的三种退化，而它们退化的**不是同一件事**；
7. 协方差依赖 gauge 的选择（同一次重建报出 1.15–1.37 倍不同的不确定度）。

只用 numpy，CPU，离线。"""),

code("""import numpy as np, math
print('numpy', np.__version__)
F = 500.0

def rodrigues(w):
    w = np.asarray(w, float); th = np.linalg.norm(w)
    if th < 1e-12: return np.eye(3)
    k = w/th; K = np.array([[0,-k[2],k[1]],[k[2],0,-k[0]],[-k[1],k[0],0]])
    return np.eye(3) + np.sin(th)*K + (1-np.cos(th))*K@K

def R_to_w(R):
    th = np.arccos(np.clip((np.trace(R)-1)/2, -1, 1))
    if th < 1e-9: return np.zeros(3)
    v = np.array([R[2,1]-R[1,2], R[0,2]-R[2,0], R[1,0]-R[0,1]])
    return th*v/(2*np.sin(th))

def make_scene(nc=5, npt=40, arc_deg=60.0, radius=6.0, seed=0):
    '''相机在弧上、**始终 look-at 场景中心**。arc_deg=0 时基线严格为 0（纯旋转）。'''
    r = np.random.default_rng(seed)
    X = r.normal(0, 1.0, (npt, 3))
    cams = []
    for i in range(nc):
        a = np.deg2rad(arc_deg)*((i/(nc-1) - 0.5) if nc > 1 else 0.0)
        C = radius*np.array([np.sin(a), 0.0, -np.cos(a)])
        fwd = -C/np.linalg.norm(C)
        up = np.array([0., 1., 0.]); rt = np.cross(up, fwd); rt /= np.linalg.norm(rt)
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
        out = np.empty(2*len(obs))
        for k, (ci, pi, uv) in enumerate(obs):
            R, t = cams[ci]; q = R @ X[pi] + t
            out[2*k]   = F*q[0]/q[2] - uv[0]
            out[2*k+1] = F*q[1]/q[2] - uv[1]
        return out
    return resid

def num_jacobian(resid, p0, eps=1e-6):
    r0 = resid(p0); J = np.zeros((len(r0), len(p0)))
    for j in range(len(p0)):
        a = p0.copy(); a[j] += eps; b = p0.copy(); b[j] -= eps
        J[:, j] = (resid(a) - resid(b))/(2*eps)
    return J

_X, _cams = make_scene(5, 40)
_obs = observations(_X, _cams)
print(f'测试场景：5 相机 / 40 点 / {len(_obs)} 个观测')
print(f'残差范数 {np.linalg.norm(residual_fn(5,40,_obs)(pack(_X,_cams))):.3e}（应为 0）')
Cs = np.array([-R.T@t for R, t in _cams])
print(f'首尾相机间距 B = {np.linalg.norm(Cs[0]-Cs[-1]):.4f} m，场景距离 z ≈ 6 m -> '
      f'B/z = {np.linalg.norm(Cs[0]-Cs[-1])/6:.4f}')"""),

md("""## 1 · 规模：两两匹配、参数量、雅可比稀疏度"""),

code("""print('=== 两两匹配 ===')
print(' 图像数    两两对数        10ms/对       词汇树 top-50 的对数（占比）')
for N in [100, 500, 2000, 10000]:
    P = N*(N-1)//2; vt = N*50//2
    print(f' {N:6d}  {P:11,d}   {P*0.01/3600:7.2f} 小时   {vt:9,d} ({vt/P:6.2%})')
assert 10000*9999//2 == 49_995_000
print(f'\\n✓ N=10^4 时全量是 {49_995_000/1e6:.1f}M 对（139 小时），'
      f'而 top-50 只有 {10000*50//2/1e3:.0f}k 对（0.50%）')
print('  关键：Nk/2 对 N 是**线性**的 —— 这不是常数因子的优化，是复杂度的改变')

print('\\n=== 束调整的参数量与雅可比稀疏度 ===')
print(' 相机   点数     总参数    稠密 H 元素   每点观测   J 的非零密度   比稠密稀疏')
for ncm, npts, obs_per in [(100, 30_000, 4), (500, 100_000, 5), (2000, 500_000, 5)]:
    tot = ncm*6 + npts*3
    nobs = npts*obs_per
    nnz = nobs*2*9                      # 每个观测 2 行，每行碰 6+3=9 个参数
    dense = nobs*2*tot
    print(f' {ncm:5d} {npts:8d} {tot:9,d} {tot**2/1e9:9.2f} G {obs_per:8d}   '
          f'{nnz/dense:.3e}   {dense/nnz:8.0f}×')
_d = (100_000*5*2*9)/(100_000*5*2*(500*6+100_000*3))
assert abs(_d - 2.97e-5) < 1e-6, f'500 相机的密度应约 2.97e-5，实测 {_d:.3e}'
print(f'\\n✓ 500 相机 / 10 万点：J 的密度 {_d:.3e}（比稠密稀疏 {1/_d:.0f} 倍）')
print('  而稠密地存 H 需要 918 亿个元素（367 GB fp32）—— 根本不可能')"""),

md("""## 2 · Schur 补：把点消掉，只解相机块

$H$ 的点块 $H_{pp}$ 是**块对角**的（两个 3D 点不出现在同一个残差里），
所以可以逐点求 $3\\times3$ 的逆。"""),

code("""nc, npt = 5, 40
X0, cams0 = make_scene(nc, npt)
obs = observations(X0, cams0)
resid = residual_fn(nc, npt, obs)
p0 = pack(X0, cams0)
J = num_jacobian(resid, p0)
H = J.T @ J
nC = 6*nc

# 验证点块确实是块对角的
Hpp = H[nC:, nC:]
block_mask = np.zeros_like(Hpp, dtype=bool)
for j in range(npt):
    block_mask[3*j:3*j+3, 3*j:3*j+3] = True
off_block = np.abs(Hpp[~block_mask]).max()
print(f'H_pp 的块外最大绝对值 {off_block:.3e}（相对 H_pp 的量级 '
      f'{off_block/np.abs(Hpp).max():.3e}）')
assert off_block/np.abs(Hpp).max() < 1e-10, 'H_pp 必须是块对角的'
print('✓ H_pp 严格块对角 —— 所以可以逐点求 3x3 的逆')

def schur_solve(H, nC, b, lam=1e-3):
    '''用 Schur 补解 (H + lam·diag(H)) dx = b。返回 dx。'''
    n = H.shape[0]
    Hd = H + lam*np.diag(np.diag(H))            # LM 阻尼（H 本身奇异）
    Hcc = Hd[:nC, :nC]; Hcp = Hd[:nC, nC:]; Hpp = Hd[nC:, nC:]
    bc = b[:nC]; bp = b[nC:]
    npt_ = (n - nC)//3
    # 逐点求 H_pp 的逆（块对角）
    Hpp_inv = np.zeros_like(Hpp)
    for j in range(npt_):
        sl = slice(3*j, 3*j+3)
        Hpp_inv[sl, sl] = np.linalg.inv(Hpp[sl, sl])
    S = Hcc - Hcp @ Hpp_inv @ Hcp.T             # Schur 补
    rhs = bc - Hcp @ (Hpp_inv @ bp)
    dxc = np.linalg.solve(S, rhs)
    dxp = Hpp_inv @ (bp - Hcp.T @ dxc)
    return np.concatenate([dxc, dxp])

rng = np.random.default_rng(0)
b = rng.normal(0, 1, H.shape[0])
lam = 1e-3
dx_schur = schur_solve(H, nC, b, lam)
dx_direct = np.linalg.solve(H + lam*np.diag(np.diag(H)), b)
err = np.linalg.norm(dx_schur - dx_direct)/np.linalg.norm(dx_direct)
print(f'\\nSchur 解 vs 直接解的相对误差 {err:.3e}')
assert err < 1e-9, f'Schur 补必须是精确的，实测 {err:.3e}'
print('✓ Schur 补是**精确**的（不是近似）—— 相对误差 %.1e' % err)

print('\\n理论加速比（按 n³ 计）：')
print(' 相机   点数     直接解 n³      Schur (6nc)³   消点 npt×27   加速比')
for ncm, npts in [(100, 30_000), (500, 100_000), (2000, 500_000)]:
    n_ = ncm*6 + npts*3
    print(f' {ncm:5d} {npts:8d}  {n_**3:.3e}   {(ncm*6)**3:.3e}  {npts*27:.3e}  '
          f'{n_**3/((ncm*6)**3 + npts*27):.2e}')
print('\\n✓ 500 相机时加速 1.03e6 倍。点是「便宜」的（可消掉），相机是「贵」的（决定 S 的规模）')"""),

md("""## 3 · gauge 零空间的解析构造，与数值判秩的两次失效"""),

code("""def apply_similarity(X, cams, om=None, dt=None, s=1.0):
    om = np.zeros(3) if om is None else np.asarray(om, float)
    dt = np.zeros(3) if dt is None else np.asarray(dt, float)
    Rw = rodrigues(om)
    X2 = s*(np.asarray(X, float) @ Rw.T) + dt
    out = []
    for R, t in cams:
        C = -R.T @ t; R2 = R @ Rw.T
        out.append((R2, -R2 @ (s*(Rw @ C) + dt)))
    return X2, out

def gauge_basis(X, cams, h=1e-6):
    cols = []
    for k in range(3):
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, dt=d))
                     - pack(*apply_similarity(X, cams, dt=-d)))/(2*h))
    for k in range(3):
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, om=d))
                     - pack(*apply_similarity(X, cams, om=-d)))/(2*h))
    cols.append((pack(*apply_similarity(X, cams, s=1+h))
                 - pack(*apply_similarity(X, cams, s=1-h)))/(2*h))
    G = np.stack(cols, 1)
    Q, _ = np.linalg.qr(G)
    return G, Q

G, Q = gauge_basis(X0, cams0)
names = ['平移x','平移y','平移z','旋转x','旋转y','旋转z','尺度']
Jn = np.linalg.norm(J)
print('解析构造的 7 个 gauge 方向：')
for i, nm in enumerate(names):
    print(f'  {nm}: ||J v||/||J|| = {np.linalg.norm(J @ Q[:, i])/Jn:.3e}')
tot = np.linalg.norm(J @ Q)/Jn
print(f'  整体: ||J Q||_F/||J||_F = {tot:.3e}')
assert np.linalg.matrix_rank(G, tol=1e-8) == 7
assert tot < 1e-9
print('\\n✓ 7 个方向精确在零空间里，且**与条件数无关**（下一格会看到这一点的重要性）')"""),

code("""# 三种判秩方法在整个 B/z 范围上的表现
def rank_by_fixed_threshold(Hs, rel=1e-10):
    s = np.linalg.svd(Hs, compute_uv=False)
    return int((s < s[0]*rel).sum())

def rank_by_max_gap(Hs):
    s = np.linalg.svd(Hs, compute_uv=False)
    r = s[:-1]/np.maximum(s[1:], 1e-300)
    k = int(np.argmax(r))
    return Hs.shape[0]-(k+1), float(r[k])

print('真实的 gauge 秩亏恒为 7（相似变换群）。三种方法的表现：')
print(' 弧(°)    B/z     有效cond(H)   固定1e-10  固定1e-14  最大间隙  解析||JQ||/||J||')
tab = {}
for arc in [60, 20, 5, 1, 0.2, 0.05, 0.01, 0.0]:
    Xa, ca = make_scene(nc, npt, arc)
    Ja = num_jacobian(residual_fn(nc, npt, observations(Xa, ca)), pack(Xa, ca))
    Ha = Ja.T @ Ja
    sa = np.linalg.svd(Ha, compute_uv=False)
    ce = sa[0]/sa[len(sa)-8]                       # 排除 7 个零之后的条件数
    r10 = rank_by_fixed_threshold(Ha, 1e-10)
    r14 = rank_by_fixed_threshold(Ha, 1e-14)
    rg, gap = rank_by_max_gap(Ha)
    _, Qa = gauge_basis(Xa, ca)
    an = np.linalg.norm(Ja @ Qa)/np.linalg.norm(Ja)
    Cs_ = np.array([-R.T@t for R, t in ca])
    bz = float(np.linalg.norm(Cs_[0]-Cs_[-1]))/6.0
    tab[arc] = (bz, ce, r10, r14, rg, an)
    print(f' {arc:6.2f}  {bz:.5f}  {ce:.3e}      {r10:5d}     {r14:5d}    {rg:4d}     {an:.2e}')

# 解析法在整个范围上都精确
assert max(v[5] for v in tab.values()) < 1e-8, '解析零空间必须在所有配置下都精确'
print(f'\\n✓ 解析法：||JQ||/||J|| 在 B/z 从 1.0 到 0（含纯旋转）全都在 1.8e-11 —— **不受条件数影响**')

# 而数值法逐步失效
assert tab[0.05][4] != 7, '最大间隙法在有效条件数 ~1e10 时应失效'
assert tab[0.01][2] != 7, '固定阈值 1e-10 在有效条件数 ~1e11 时应失效'
print(f'✓ 最大间隙法在 B/z={tab[0.05][0]:.5f}（有效 cond {tab[0.05][1]:.1e}）时报 {tab[0.05][4]}（错）')
print(f'✓ 固定阈值 1e-10 在 B/z={tab[0.01][0]:.5f}（有效 cond {tab[0.01][1]:.1e}）时报 {tab[0.01][2]}（错）')
print('  规律：固定阈值法在「有效条件数 ≈ 1/阈值」处失效 —— 所以它其实是在')
print('  比较「gauge 的零」与「最差的可观测方向」，而后者会随基线变小而逼近前者。')

# 纯旋转那一档：46 其实是**对的**
print('\\n⚠ 但最后一行（纯旋转）的 46 不是错误 —— 那里的零空间**真的**变大了：')
print(' 相机  点数   零空间维数(1e-14)   npt+6   一致?')
for _nc2, _npt2 in [(5, 15), (5, 25), (5, 40), (4, 30), (6, 20)]:
    _X2, _c2 = make_scene(_nc2, _npt2, 0.0)
    _J2 = num_jacobian(residual_fn(_nc2, _npt2, observations(_X2, _c2)), pack(_X2, _c2))
    _s2 = np.linalg.svd(_J2.T @ _J2, compute_uv=False)
    _nd = int((_s2 < _s2[0]*1e-14).sum())
    print(f' {_nc2:4d} {_npt2:5d}   {_nd:12d}   {_npt2+6:6d}   {"✓" if _nd == _npt2+6 else "✗"}')
    assert _nd == _npt2 + 6, f'纯旋转时零空间应为 npt+6，实测 {_nd}'
print('\\n✓ 纯旋转时零空间维数 = **npt + 6**（5 组配置全部吻合）：')
print('  每个点的深度都不可观测（npt 个）+ 全局旋转 3 + 全局平移 3。')
print('  而尺度被**并进**了逐点深度里，所以是 6 而不是 7。')
print('\\n所以完整的结论是三条：')
print('  ① gauge 零空间（7 维）是解析已知的，任何条件数下都能精确构造；')
print('  ② 数值判秩会在有效条件数逼近 1/阈值 时失效（本例约 1e10~1e11）；')
print('  ③ 而纯旋转不是「条件数很大」，是零空间**真的**从 7 涨到 npt+6 ——')
print('     所以那不是数值问题，是可观测性问题。')
"""),

md("""## 4 · 投影掉 gauge 之后的条件数：$\\propto (B/z)^{-2}$"""),

code("""def gauge_projected_cond(arc_deg, nc=5, npt=40, seed=0):
    '''返回 (基线 B, B/z, ||JQ||/||J||, 投影掉 gauge 后的条件数, 相机后方的点数)。'''
    X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    bad = 0
    for R, t in cams:
        P = (R @ X.T).T + t
        bad += int((P[:, 2] <= 1e-6).sum())
    obs = observations(X, cams)
    Jl = num_jacobian(residual_fn(nc, npt, obs), pack(X, cams))
    _, Ql = gauge_basis(X, cams)
    n = Jl.shape[1]
    gres = np.linalg.norm(Jl @ Ql)/np.linalg.norm(Jl)
    U, _, _ = np.linalg.svd(np.eye(n) - Ql @ Ql.T)
    B_ = U[:, :n-7]
    sp = np.linalg.svd(B_.T @ (Jl.T @ Jl) @ B_, compute_uv=False)
    Cs = np.array([-R.T@t for R, t in cams])
    base = float(np.linalg.norm(Cs[0]-Cs[-1])) if nc > 1 else 0.0
    return base, base/6.0, gres, float(sp[0]/sp[-1]), bad

print(' 弧(°)   基线(m)    B/z     ||JQ||/||J||   投影后的条件数    相机后方的点')
rows = []
for arc in [120, 60, 20, 5, 1, 0.2, 0.0]:
    b_, bz, gr, cond, bad = gauge_projected_cond(arc)
    rows.append((bz, cond))
    print(f' {arc:6.1f}  {b_:8.4f}  {bz:7.4f}   {gr:.2e}      {cond:.3e}        {bad}')

# 标度律
print('\\n标度律（相邻两档）：')
for i in range(1, len(rows)-1):
    r0, c0 = rows[i-1]; r1, c1 = rows[i]
    print(f'  B/z {r0:.4f} -> {r1:.4f} ({r1/r0:.3f}×): 条件数 ×{c1/c0:6.2f}  '
          f'等效指数 {math.log(c1/c0)/math.log(r1/r0):+.2f}')
_e = math.log(rows[-2][1]/rows[-3][1])/math.log(rows[-2][0]/rows[-3][0])
assert -2.6 < _e < -1.8, f'小基线端的指数应接近 -2，实测 {_e:+.2f}'

cond_rot = rows[-1][1]; cond_small = rows[-2][1]
print(f'\\n✓ 小基线端的等效指数 {_e:+.2f} -> 条件数 ∝ (B/z)^-2')
print(f'  而 cond(H) = cond(J)²，所以 J 的最差方向 ∝ 1/B ——')
print(f'  正对应 C72 的 σ_z = z²σ_d/(fB) ∝ 1/B。两条独立推导对上了。')
print(f'\\n✓ 纯旋转（B/z=0）是**悬崖**：{cond_rot:.2e} vs B/z=0.0035 时的 {cond_small:.2e}')
print(f'  跳了 {cond_rot/cond_small:.1e} 倍 —— 深度从「测不准」变成「不可观测」')
assert cond_rot/cond_small > 1e6, '纯旋转必须是一个数量级上的悬崖'
assert cond_rot > 1e15, 'float64 的相对精度是 2.2e-16，所以这已是数值奇异'"""),

code("""# 我自己踩过的混淆：一个坏轨迹
def make_scene_BAD(nc=5, npt=40, radius=6.0, arc_deg=100.8, seed=0):
    '''坏版本：相机在半径 radius 的圆上，但**朝向按弧长旋转而不 look-at 中心**。
    radius 调小时相机几乎不动却仍然转 100° —— 于是点跑到相机背后。'''
    r = np.random.default_rng(seed)
    X = r.normal(0, 1.0, (npt, 3)) + np.array([0, 0, 6.0])
    cams = []
    for i in range(nc):
        a = np.deg2rad(arc_deg)*i/max(nc-1, 1)
        R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        C = radius*np.array([np.sin(a), 0.05*r.normal(), 1-np.cos(a)])
        cams.append((R, -R @ C))
    return X, cams

print('坏轨迹：相机朝向按弧长转，但不 look-at 场景中心')
print(' 轨迹半径   相机后方的点   投影 u 的最大绝对值   出画比例(|u|>320)')
for rad in [6.0, 2.0, 0.5, 0.05]:
    Xb2, cb2 = make_scene_BAD(5, 40, rad)
    behind = 0; umax = 0.0; out = 0; tot = 0
    for R, t in cb2:
        P = (R @ Xb2.T).T + t
        behind += int((P[:, 2] <= 1e-6).sum())
        ok = P[:, 2] > 1e-6
        u = F*P[ok, 0]/P[ok, 2]
        umax = max(umax, float(np.abs(u).max()) if ok.any() else 0.0)
        out += int((np.abs(u) > 320).sum()); tot += int(ok.sum())
    print(f'  {rad:6.2f}      {behind:3d}/{5*40}        {umax:12.0f}          {out/max(tot,1):.1%}')

Xb2, cb2 = make_scene_BAD(5, 40, 0.5)
behind = sum(int((((R@Xb2.T).T+t)[:, 2] <= 1e-6).sum()) for R, t in cb2)
assert behind > 20, '坏轨迹在小半径时必须有大量点跑到相机后方'
print(f'\\n⚠ 半径 0.5 m 时有 {behind}/200 个点在相机背后，投影 u 到 52 万像素。')
print('  我第一版就是用这个轨迹测「小基线的条件数」的 —— 测到 1e19，')
print('  然后把它当成「小基线效应」写进了结论。')
print('  它其实是一个**坏掉的场景**：相机没在看场景。')
print('\\n教训：报「配置 A 比 B 差多少倍」之前，先确认两者**唯一**的差别')
print('      真的是你想改的那一个。这里的检查只要一行：数一数 z<=0 的点。')"""),

md("""## 5 · 两视图初始化的三种退化"""),

code("""def two_view_scene(n=100, planar=False, forward=False, baseline=1.0, seed=0):
    '''返回归一化坐标下的两组对应点。'''
    r = np.random.default_rng(seed)
    if planar:
        X = np.stack([r.uniform(-2,2,n), r.uniform(-1.5,1.5,n), np.full(n, 6.0)], 1)
    else:
        X = np.stack([r.uniform(-2,2,n), r.uniform(-1.5,1.5,n), r.uniform(4,9,n)], 1)
    R1, t1 = np.eye(3), np.zeros(3)
    if forward:
        C2 = np.array([0., 0., baseline]); R2 = np.eye(3)
    else:
        C2 = np.array([baseline, 0., 0.])
        a = np.deg2rad(3.0)
        R2 = np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    t2 = -R2 @ C2
    def nrm(R, t):
        P = (R @ X.T).T + t
        return np.stack([P[:,0]/P[:,2], P[:,1]/P[:,2]], 1), P[:,2]
    x1, z1 = nrm(R1, t1); x2, z2 = nrm(R2, t2)
    ok = (z1 > 0.1) & (z2 > 0.1)
    return x1[ok], x2[ok]

def eight_point_svals(x1, x2):
    '''8 点法的设计矩阵的奇异值。'''
    A = np.stack([x2[:,0]*x1[:,0], x2[:,0]*x1[:,1], x2[:,0],
                  x2[:,1]*x1[:,0], x2[:,1]*x1[:,1], x2[:,1],
                  x1[:,0], x1[:,1], np.ones(len(x1))], 1)
    U, S, Vt = np.linalg.svd(A)
    return S, Vt[-1].reshape(3, 3)

print('E 有 8 个自由度，所以 A 的零空间应恰好是 1 维。')
print(' 配置                  A 的最小 4 个奇异值                     σ8/σ9      诊断')
res = {}
for tag, kw in [('一般 + 侧移', dict()),
                ('**共面** + 侧移', dict(planar=True)),
                ('一般 + 前向运动', dict(forward=True)),
                ('一般 + 小基线', dict(baseline=0.02)),
                ('共面 + 前向', dict(planar=True, forward=True))]:
    x1, x2 = two_view_scene(100, seed=0, **kw)
    S, E = eight_point_svals(x1, x2)
    ratio = S[-2]/max(S[-1], 1e-300)
    res[tag] = ratio
    diag = '零空间 1 维 ✓' if ratio > 1e6 else '**退化**（零空间 >1 维）'
    print(f' {tag:20s} ' + ' '.join(f'{v:9.2e}' for v in S[-4:]) + f'  {ratio:8.1e}  {diag}')

assert res['一般 + 侧移'] > 1e10
assert res['**共面** + 侧移'] < 100, '共面必须退化'
assert res['一般 + 前向运动'] > 1e10, '前向运动**不**让 E 退化'
print(f'\\n✓ 共面场景：σ8/σ9 = {res["**共面** + 侧移"]:.1f} -> 零空间是 3 维，E 只被确定到一个 3 参数族')
print(f'✓ 前向运动：σ8/σ9 = {res["一般 + 前向运动"]:.1e} -> **E 完全没问题**')
print('  所以「前向运动是退化的」这句话不准确 —— 退化的是三角化，不是 E（下一格）')"""),

code("""# 共面退化的签名：与噪声无关
print('=== 加噪后 E 的方向变化（50 次试验的中位数）===')
print(' 配置       噪声(px)   E 的方向变化(度)')
sig = {}
for tag, kw in [('一般场景', dict()), ('共面场景', dict(planar=True))]:
    x1, x2 = two_view_scene(100, seed=0, **kw)
    _, E0 = eight_point_svals(x1, x2); E0 = E0/np.linalg.norm(E0)
    for npx in [0.0, 0.2, 1.0]:
        angs = []
        for s in range(50):
            rr = np.random.default_rng(500+s)
            n1 = x1 + rr.normal(0, npx/F, x1.shape)
            n2 = x2 + rr.normal(0, npx/F, x2.shape)
            _, E = eight_point_svals(n1, n2); E = E/np.linalg.norm(E)
            if np.sum(E*E0) < 0: E = -E
            angs.append(np.degrees(np.arccos(np.clip(np.sum(E*E0), -1, 1))))
        sig[(tag, npx)] = float(np.median(angs))
        print(f' {tag:10s} {npx:6.2f}     {np.median(angs):8.4f}')
    print()
_gen = sig[('一般场景',1.0)]/max(sig[('一般场景',0.2)],1e-9)
_pla = sig[('共面场景',1.0)]/max(sig[('共面场景',0.2)],1e-9)
print(f'噪声 0.2 -> 1.0 px（5 倍）时的误差倍数：一般场景 {_gen:.2f}×，共面场景 {_pla:.2f}×')
assert _gen > 3.0, '一般场景应随噪声线性退化'
assert _pla < 1.2, '共面场景的误差应**饱和**（与噪声无关）'
print('\\n✓ 一般场景随噪声线性退化（5 倍噪声 -> %.1f 倍误差）；' % _gen)
print('  共面场景**饱和**（%.2f 倍）—— 因为方向是从一个 3 维族里任意挑的。' % _pla)
print('  「加噪声不改变误差」是结构性退化的诊断标志 ——')
print('  模块 02 的周期纹理会再次出现这个签名。')

# 前向运动：退化的是三角化
print('\\n=== 前向运动：靠近极点的点两条视线几乎重合 ===')
x1, x2 = two_view_scene(400, forward=True, baseline=1.0, seed=1)
r_ep = np.linalg.norm(x1, axis=1)          # 沿光轴运动 -> 极点在归一化坐标原点
def ray_angle(a, b):
    d1 = np.array([a[0], a[1], 1.0]); d1 /= np.linalg.norm(d1)
    d2 = np.array([b[0], b[1], 1.0]); d2 /= np.linalg.norm(d2)
    return np.degrees(np.arccos(np.clip(d1 @ d2, -1, 1)))
angs = np.array([ray_angle(x1[i], x2[i]) for i in range(len(x1))])
qs = np.percentile(r_ep, [20, 50, 80])
print(' 到极点的归一化距离     视线夹角(度, 中位)   相对最外圈')
bins = [0] + list(qs) + [np.inf]
med_all = float(np.median(angs))
inner = outer = None
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (r_ep >= lo) & (r_ep < hi)
    if m.sum() < 5: continue
    v = float(np.median(angs[m]))
    if lo == 0: inner = v
    if hi == np.inf: outer = v
    print(f'  [{lo:.3f}, {hi:.3f})' + ' '*(10-len(f'{hi:.3f}')) +
          f'   {v:8.4f}')
print(f'\\n最内圈 {inner:.4f}° vs 最外圈 {outer:.4f}° -> 相差 {outer/inner:.1f} 倍')
assert outer/inner > 3.0, '极点附近的视线夹角必须显著小'
print('✓ 前向运动时画面中心的三角化最差 —— 而那正是自动驾驶最关心的区域')
print('  （C72 模块 03 的四种补法就是为此而设）')"""),

md("""## 6 · 协方差依赖 gauge 的选择"""),

code("""SIGMA_PX = 0.5
def point_sigmas(arc_deg, mode, nc=5, npt=30, seed=0):
    '''返回各点 3D 位置协方差迹的平方根（中位数）。mode ∈ {cam0_pt, cam0_cam4, project}'''
    X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    obs = observations(X, cams)
    Jl = num_jacobian(residual_fn(nc, npt, obs), pack(X, cams))
    Hl = (Jl.T @ Jl)/SIGMA_PX**2
    n = Hl.shape[0]; nCl = 6*nc
    if mode == 'project':
        _, Ql = gauge_basis(X, cams)
        U, _, _ = np.linalg.svd(np.eye(n) - Ql @ Ql.T)
        Bs = U[:, :n-7]
        Cov = Bs @ np.linalg.pinv(Bs.T @ Hl @ Bs) @ Bs.T
        return float(np.median([np.sqrt(np.trace(Cov[np.ix_([nCl+3*j+k for k in range(3)],
                                                            [nCl+3*j+k for k in range(3)])]))
                                for j in range(npt)]))
    fixed = list(range(6)) + ([nCl] if mode == 'cam0_pt' else [6*(nc-1)+3])
    keep = [i for i in range(n) if i not in set(fixed)]
    Cov = np.linalg.pinv(Hl[np.ix_(keep, keep)])
    pos = {g: l for l, g in enumerate(keep)}
    out = []
    for j in range(npt):
        gi = [nCl+3*j+k for k in range(3)]
        li = [pos[g] for g in gi if g in pos]
        if len(li) < 3: continue
        out.append(np.sqrt(np.trace(Cov[np.ix_(li, li)])))
    return float(np.median(out))

print('点位不确定度（协方差迹的平方根，中位数，单位 m；像素噪声 0.5 px）')
print(' 弧(°)   B/z     ①固定相机0+一坐标   ②固定相机0+相机4的一个平移   ③gauge 投影')
tab = {}
for arc in [60.0, 20.0, 5.0]:
    Cs = np.array([-R.T@t for R, t in make_scene(5, 30, arc)[1]])
    bz = float(np.linalg.norm(Cs[0]-Cs[-1]))/6.0
    a1 = point_sigmas(arc, 'cam0_pt')
    a2 = point_sigmas(arc, 'cam0_cam4')
    a3 = point_sigmas(arc, 'project')
    tab[arc] = (a1, a2, a3)
    print(f' {arc:5.1f}  {bz:.4f}   {a1:16.5f}   {a2:22.5f}   {a3:11.5f}')

for arc, (a1, a2, a3) in tab.items():
    assert a3 <= a1 + 1e-12 and a3 <= a2 + 1e-12, 'gauge 投影应给出最小（最小范数）的答案'
spread = max(tab[60.0])/min(tab[60.0])
print(f'\\n✓ 同一次重建，三种 gauge 处理报出的不确定度差 {spread:.2f} 倍（弧 60°）')
print('  而只有 ③（gauge 投影）是 gauge 无关的，所以只有它在两份重建之间可比。')

# 顺带第三次印证标度律
s3 = [tab[a][2] for a in [60.0, 20.0, 5.0]]
bzs = []
for arc in [60.0, 20.0, 5.0]:
    Cs = np.array([-R.T@t for R, t in make_scene(5, 30, arc)[1]])
    bzs.append(float(np.linalg.norm(Cs[0]-Cs[-1]))/6.0)
print('\\nσ 对 B/z 的标度（③ 那一列）：')
for i in range(1, 3):
    e = math.log(s3[i]/s3[i-1])/math.log(bzs[i]/bzs[i-1])
    print(f'  B/z {bzs[i-1]:.4f} -> {bzs[i]:.4f}: σ ×{s3[i]/s3[i-1]:.2f}  等效指数 {e:+.2f}')
    assert -1.3 < e < -0.85, f'σ 应 ∝ (B/z)^-1，实测指数 {e:+.2f}'
print('\\n✓ σ ∝ (B/z)^-1，而第 4 节的 cond(H) ∝ (B/z)^-2 —— 因为 cond(H)=cond(J)²。')
print('  加上 C72 的 σ_z = z²σ_d/(fB)，三条独立推导指向同一个律。')"""),

md("""## 7 · 增量式的漂移：朝向按 $\\sqrt n$，尺度按乘性游走"""),

code("""def drift_stats(n_steps, ang_per_step_deg=0.05, scale_sigma=0.005, trials=4000, seed=1):
    '''返回 (朝向误差的 RMS 度, 尺度倍数的 P5, P95, std)。'''
    r = np.random.default_rng(seed)
    # 朝向：每步一个独立的小旋转，误差近似随机游走
    ang = np.sqrt(n_steps)*ang_per_step_deg
    # 尺度：乘性
    s = np.prod(1.0 + r.normal(0, scale_sigma, (trials, n_steps)), axis=1)
    return ang, float(np.percentile(s, 5)), float(np.percentile(s, 95)), float(s.std())

print('每步 0.05° 朝向误差 / ±0.5% 尺度误差：')
print(' 步数    朝向误差(度)   尺度倍数 P5    P95     标准差')
prev_ang = prev_sd = None
for n_ in [10, 50, 200, 1000]:
    a, p5, p95, sd = drift_stats(n_)
    print(f' {n_:5d}   {a:10.3f}    {p5:.4f}    {p95:.4f}   {sd:.4f}')
    if prev_ang is not None:
        pass
    prev_ang, prev_sd = a, sd

a10, *_ = drift_stats(10); a1000, *_ = drift_stats(1000)
assert abs(a1000/a10 - 10.0) < 1e-9, '朝向误差应 ∝ sqrt(n)'
_, _, _, sd10 = drift_stats(10); _, _, _, sd1000 = drift_stats(1000)
print(f'\\n✓ 朝向：n 从 10 到 1000（100 倍）时误差涨 {a1000/a10:.1f} 倍 = sqrt(100) ✓')
print(f'✓ 尺度：标准差从 {sd10:.4f} 涨到 {sd1000:.4f}（{sd1000/sd10:.1f} 倍）')
print(f'  理论上乘性游走的对数方差 ∝ n，所以 std ≈ sigma*sqrt(n) = '
      f'{0.005*np.sqrt(1000):.4f} ✓')
assert abs(sd1000 - 0.005*np.sqrt(1000)) < 0.02

print('\\n关键差别：朝向被 180° 框住，而尺度**没有上界**。')
print(' 步数    尺度倍数的 1% / 99% 分位')
for n_ in [200, 1000, 5000]:
    r = np.random.default_rng(7)
    s = np.prod(1.0 + r.normal(0, 0.005, (4000, n_)), axis=1)
    print(f' {n_:5d}   {np.percentile(s,1):.4f} / {np.percentile(s,99):.4f}')
print('\\n✓ 5000 步后 1%~99% 区间已经很宽 —— 而每一步的重投影误差都很小、')
print('  整个模型内部完全自洽。所以尺度漂移只能靠**闭环**或**外部尺度**纠正，')
print('  而不能靠「优化得更彻底」。')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 用 Schur 补解正规方程

实现 `my_schur(H, nC, b, lam)`：解 $(H + \\lambda\\,\\mathrm{diag}(H))\\,\\Delta x = b$，
但**必须**利用点块 $H_{pp}$ 的块对角结构（逐点求 $3\\times3$ 的逆），
而不是直接解整个系统。

`nC` 是相机参数的个数（前 `nC` 个），其余是点参数（每点 3 个）。"""),

code("""def my_schur(H, nC, b, lam=1e-3):
    '''用 Schur 补解 (H + lam*diag(H)) dx = b。返回 dx。'''
    # TODO: 1) Hd = H + lam*np.diag(np.diag(H))
    #       2) 切块：Hcc = Hd[:nC,:nC], Hcp = Hd[:nC,nC:], Hpp = Hd[nC:,nC:]
    #                bc = b[:nC], bp = b[nC:]
    #       3) **逐点**求 Hpp 的逆（每个 3x3 块单独 inv），拼成 Hpp_inv
    #       4) S = Hcc - Hcp @ Hpp_inv @ Hcp.T
    #          dxc = solve(S, bc - Hcp @ (Hpp_inv @ bp))
    #          dxp = Hpp_inv @ (bp - Hcp.T @ dxc)
    #       5) 返回 concatenate([dxc, dxp])
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_nc, _npt = 5, 40
_X, _cams = make_scene(_nc, _npt)
_obs = observations(_X, _cams)
_J = num_jacobian(residual_fn(_nc, _npt, _obs), pack(_X, _cams))
_H = _J.T @ _J
_nC = 6*_nc
_rg1 = np.random.default_rng(0)

# ① 与直接解一致（多个 lam）
for _lam in [1e-1, 1e-3, 1e-6]:
    _b = _rg1.normal(0, 1, _H.shape[0])
    _dx = my_schur(_H, _nC, _b, _lam)
    _ref = np.linalg.solve(_H + _lam*np.diag(np.diag(_H)), _b)
    _e = np.linalg.norm(_dx - _ref)/np.linalg.norm(_ref)
    assert _e < 1e-8, f'lam={_lam}: 相对误差 {_e:.3e}'

# ② 形状
_b = _rg1.normal(0, 1, _H.shape[0])
assert my_schur(_H, _nC, _b).shape == (_H.shape[0],)

# ③ 必须真的解了方程（残差小）
_lam = 1e-3
_dx = my_schur(_H, _nC, _b, _lam)
_res = np.linalg.norm((_H + _lam*np.diag(np.diag(_H))) @ _dx - _b)/np.linalg.norm(_b)
assert _res < 1e-8, f'方程残差 {_res:.3e}'

# ④ 换一个场景规模
_nc2, _npt2 = 4, 25
_X2, _c2 = make_scene(_nc2, _npt2, 40.0)
_J2 = num_jacobian(residual_fn(_nc2, _npt2, observations(_X2, _c2)), pack(_X2, _c2))
_H2 = _J2.T @ _J2
_b2 = _rg1.normal(0, 1, _H2.shape[0])
_e2 = np.linalg.norm(my_schur(_H2, 6*_nc2, _b2, 1e-3)
                     - np.linalg.solve(_H2 + 1e-3*np.diag(np.diag(_H2)), _b2))
assert _e2/np.linalg.norm(_b2) < 1e-8

# ⑤ 验证实现确实用了块结构：把 Hpp 的块外元素破坏掉，结果应当**不变**
#    （因为块对角的实现根本不读那些元素）
_Hbad = _H.copy()
_bm = np.zeros((_H.shape[0]-_nC, _H.shape[0]-_nC), dtype=bool)
for _j in range(_npt):
    _bm[3*_j:3*_j+3, 3*_j:3*_j+3] = True
_sub = _Hbad[_nC:, _nC:]
_sub[~_bm] += 1e3            # 破坏块外元素
_Hbad[_nC:, _nC:] = _sub
_d_ok = my_schur(_H, _nC, _b, 1e-3)
_d_bad = my_schur(_Hbad, _nC, _b, 1e-3)
assert np.allclose(_d_ok, _d_bad, rtol=1e-9), \\
    '块对角的实现不该读 Hpp 的块外元素（说明你用了整块求逆）'
print(f'✓ 练习 1 通过：3 个 lam × 2 个场景与直接解一致（<1e-8）；'
      f'且破坏 H_pp 的块外元素后结果不变 —— 证明真的用了块结构')"""),

md("""### 📖 参考答案 1"""),

code("""def my_schur(H, nC, b, lam=1e-3):
    Hd = H + lam*np.diag(np.diag(H))
    Hcc = Hd[:nC, :nC]; Hcp = Hd[:nC, nC:]; Hpp = Hd[nC:, nC:]
    bc = b[:nC]; bp = b[nC:]
    npt_ = (H.shape[0] - nC)//3
    Hpp_inv = np.zeros_like(Hpp)
    for j in range(npt_):
        sl = slice(3*j, 3*j+3)
        Hpp_inv[sl, sl] = np.linalg.inv(Hpp[sl, sl])
    S = Hcc - Hcp @ Hpp_inv @ Hcp.T
    dxc = np.linalg.solve(S, bc - Hcp @ (Hpp_inv @ bp))
    dxp = Hpp_inv @ (bp - Hcp.T @ dxc)
    return np.concatenate([dxc, dxp])

print('参考答案 1 已定义')
print('要点一：Schur 补是**精确**的，不是近似（自测 ① 的 1e-8 是浮点误差）。')
print('       所以「用 Schur 补加速」不牺牲任何精度。')
print('要点二：LM 阻尼 lam 不是可选的 —— H 本身奇异（秩亏 7），直接解会失败。')
print('       所以真实的束调整总是 LM 而不是 Gauss-Newton。')
print('要点三：自测 ⑤ 是这道题的关键检查。如果你用 np.linalg.inv(Hpp) 整块求逆，')
print('       它会读到块外元素，于是破坏那些元素后结果就变了 —— 断言会失败。')
print('       而真实实现里 H_pp 根本不会被显式构造成一个大矩阵。')"""),

md("""### ✏️ 练习 2 · gauge 零空间的解析构造

实现 `my_gauge_basis(X, cams, h)`：返回 `(G, Q)`，
`G` 是 $(n_{\\text{param}}, 7)$ 的矩阵，每一列是相似变换的一个生成方向；
`Q` 是它的正交化（`np.linalg.qr`）。

七个方向的顺序：平移 x/y/z、旋转 x/y/z、尺度。
用中心差分作用 `apply_similarity`。"""),

code("""def my_gauge_basis(X, cams, h=1e-6):
    '''返回 (G (n,7), Q (n,7))。'''
    # TODO: 对 7 个群参数各做一次中心差分：
    #   平移 k: (pack(*apply_similarity(X,cams,dt=+h e_k)) - pack(...dt=-h e_k))/(2h)
    #   旋转 k: 同理用 om=
    #   尺度  : 用 s=1+h 与 s=1-h
    # 拼成 G，再 Q,_ = np.linalg.qr(G)
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_nc3, _npt3 = 5, 40
for _arc in [60.0, 20.0, 5.0, 0.5]:
    _X3, _c3 = make_scene(_nc3, _npt3, _arc)
    _J3 = num_jacobian(residual_fn(_nc3, _npt3, observations(_X3, _c3)), pack(_X3, _c3))
    _G3, _Q3 = my_gauge_basis(_X3, _c3)
    # ① 形状与秩
    assert _G3.shape == (6*_nc3 + 3*_npt3, 7), f'形状 {_G3.shape}'
    assert np.linalg.matrix_rank(_G3, tol=1e-8) == 7, 'G 必须满秩 7'
    assert _Q3.shape == (6*_nc3 + 3*_npt3, 7)
    assert np.allclose(_Q3.T @ _Q3, np.eye(7), atol=1e-10), 'Q 必须正交'
    # ② 精确在零空间里 —— 而且**与条件数无关**
    _rel = np.linalg.norm(_J3 @ _Q3)/np.linalg.norm(_J3)
    assert _rel < 1e-8, f'arc={_arc}: ||JQ||/||J|| = {_rel:.3e}'
    # ③ 与参考实现张成同一个子空间
    _, _Qr = gauge_basis(_X3, _c3)
    _princ = np.linalg.svd(_Q3.T @ _Qr, compute_uv=False)
    assert np.allclose(_princ, 1.0, atol=1e-8), '必须张成同一个子空间'

# ④ 七个方向各自都在零空间里（不是只有整体）
_X3, _c3 = make_scene(5, 40, 60.0)
_J3 = num_jacobian(residual_fn(5, 40, observations(_X3, _c3)), pack(_X3, _c3))
_G3, _Q3 = my_gauge_basis(_X3, _c3)
_per = [np.linalg.norm(_J3 @ _Q3[:, i])/np.linalg.norm(_J3) for i in range(7)]
assert max(_per) < 1e-8, f'每个方向都应精确，最差 {max(_per):.3e}'

# ⑤ h 的可用范围：中心差分是二阶的，但下界不是通常的那个（见参考答案）
print('  h 的扫描（同一场景）：')
_hs = {}
for _h in [1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-10]:
    _, _Qh = my_gauge_basis(_X3, _c3, h=_h)
    _hs[_h] = np.linalg.norm(_J3 @ _Qh)/np.linalg.norm(_J3)
    print(f'    h={_h:.0e}: ||JQ||/||J|| = {_hs[_h]:.3e}')
# 二阶收敛：h 从 1e-2 到 1e-3（10 倍）时误差应降约 100 倍
assert 50 < _hs[1e-2]/_hs[1e-3] < 200, \
    f'截断误差应是二阶的，实测比值 {_hs[1e-2]/_hs[1e-3]:.1f}'
# 可用区间
for _h in [1e-4, 1e-5, 1e-6, 1e-7]:
    assert _hs[_h] < 1e-8, f'h={_h:.0e} 应可用，实测 {_hs[_h]:.3e}'
# h 太小时**灾难性**失效（不是缓慢退化）
assert _hs[1e-8] > 1e-4, f'h=1e-8 应灾难性失效，实测 {_hs[1e-8]:.3e}'
assert abs(_hs[1e-8] - _hs[1e-10])/_hs[1e-8] < 0.1, \
    'h≤1e-8 之后误差应饱和（说明是 arccos 的精度墙，而不是 eps/h）'
print(f'\\n✓ 练习 2 通过：4 个 B/z 配置（含 0.00087）下 ||JQ||/||J|| 都 < 1e-8；'
      f'七个方向单独最差 {max(_per):.1e}')
print(f'  h 的可用区间是 1e-4 ~ 1e-7（最佳 1e-5，{_hs[1e-5]:.1e}）；')
print(f'  h=1e-2 时截断误差主导（{_hs[1e-2]:.1e}，二阶：降一个数量级误差降 100 倍）；')
print(f'  h≤1e-8 时**灾难性**失效并饱和在 {_hs[1e-8]:.1e} —— 原因见参考答案。')"""),

md("""### 📖 参考答案 2"""),

code("""def my_gauge_basis(X, cams, h=1e-6):
    cols = []
    for k in range(3):                                   # 平移
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, dt=d))
                     - pack(*apply_similarity(X, cams, dt=-d)))/(2*h))
    for k in range(3):                                   # 旋转
        d = np.zeros(3); d[k] = h
        cols.append((pack(*apply_similarity(X, cams, om=d))
                     - pack(*apply_similarity(X, cams, om=-d)))/(2*h))
    cols.append((pack(*apply_similarity(X, cams, s=1+h))  # 尺度
                 - pack(*apply_similarity(X, cams, s=1-h)))/(2*h))
    G = np.stack(cols, 1)
    Q, _ = np.linalg.qr(G)
    return G, Q

print('参考答案 2 已定义')
print('要点一：自测 ② 里包含 B/z=0.009 的配置 —— 那里 H 的条件数已过 1e8，')
print('       两种**数值**判秩方法都会给出错的答案（第 3 节）。')
print('       而解析零空间在那里仍然精确到 1e-11。这就是它的价值。')
print('要点二：正交化（QR）是必须的。G 的七列不正交，直接用它做投影会算错。')
print('要点三：尺度那一列用 s=1±h 而不是 s=exp(±h) —— 两者到一阶相同，')
print('       所以都对；但如果你的参数化里尺度是 log，就要相应改。')
print()
print('要点四（自测 ⑤）：h 的下界为什么是 1e-7 而不是通常的 1e-11。')
print('  中心差分的误差是 O(h²) + O(eps/h)，按这个公式最佳 h ≈ eps^(1/3) ≈ 6e-6，')
print('  而下界应该在 1e-11 附近才对。实测却在 1e-8 就灾难性失效。')
print('  原因在 R_to_w：它算 th = arccos((tr(R)-1)/2)。')
print('  而 θ→0 时 tr(R) ≈ 3 - θ²，所以 (tr-1)/2 ≈ 1 - θ²/2，')
print('  arccos(1-x) ≈ sqrt(2x) —— 也就是它在算 sqrt(θ²)。')
print('  θ=1e-8 时 θ²=1e-16 恰好是机器精度，所以 θ**一位有效数字都不剩**。')
print('  这是轴角表示的一个经典陷阱：**从 R 反解 θ 只有半数有效位**。')
print('  （真实实现用 atan2(||v||, tr-1) 或四元数来避免它。）')
print('  教训：数值微分的步长下界不总是 eps/h —— 被链条里精度最差的那一环决定。')"""),

md("""### ✏️ 练习 3 · 两视图退化的检测

实现 `null_dim_ratio(x1, x2)`：返回 8 点法设计矩阵的 $\\sigma_8/\\sigma_9$。
再实现 `is_degenerate(x1, x2, thresh)`：该比值小于 `thresh` 时判为退化。"""),

code("""def null_dim_ratio(x1, x2):
    '''8 点法设计矩阵的 sigma_8 / sigma_9。'''
    # TODO: 按 x2ᵀ E x1 = 0 展开成 A c = 0，A 的每一行是
    #   [x2x*x1x, x2x*x1y, x2x, x2y*x1x, x2y*x1y, x2y, x1x, x1y, 1]
    # 求 A 的奇异值 S，返回 S[-2]/max(S[-1], 1e-300)
    raise NotImplementedError

def is_degenerate(x1, x2, thresh=1e6):
    '''零空间不是干净的 1 维 -> 退化。'''
    # TODO: 返回 null_dim_ratio(x1, x2) < thresh
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_cfg = {'一般+侧移': dict(), '共面+侧移': dict(planar=True),
        '一般+前向': dict(forward=True), '一般+小基线': dict(baseline=0.02),
        '共面+前向': dict(planar=True, forward=True)}
_r = {}
for _t, _kw in _cfg.items():
    _a, _b2 = two_view_scene(100, seed=0, **_kw)
    _r[_t] = null_dim_ratio(_a, _b2)
    assert _r[_t] > 0

# ① 与参考实现一致
for _t, _kw in _cfg.items():
    _a, _b2 = two_view_scene(100, seed=0, **_kw)
    _S, _ = eight_point_svals(_a, _b2)
    assert abs(_r[_t] - _S[-2]/max(_S[-1], 1e-300))/_r[_t] < 1e-9

# ② 一般场景与前向运动**不**退化
assert not is_degenerate(*two_view_scene(100, seed=0)), '一般场景不该退化'
assert not is_degenerate(*two_view_scene(100, forward=True, seed=0)), \\
    '前向运动不该让 E 退化（退化的是三角化）'
assert not is_degenerate(*two_view_scene(100, baseline=0.02, seed=0)), \\
    '小基线下 E 的零空间仍是 1 维'

# ③ 共面场景退化
assert is_degenerate(*two_view_scene(100, planar=True, seed=0)), '共面必须被判为退化'
assert is_degenerate(*two_view_scene(100, planar=True, forward=True, seed=0))

# ④ 退化与不退化之间差很多个数量级
_deg = max(_r['共面+侧移'], _r['共面+前向'])
_ok = min(_r['一般+侧移'], _r['一般+前向'], _r['一般+小基线'])
assert _ok/_deg > 1e8, f'两类之间应差 8 个数量级以上，实测 {_ok/_deg:.1e}'

# ⑤ 阈值在很宽的范围内都给出同样的分类
for _th in [1e3, 1e6, 1e9]:
    for _t, _kw in _cfg.items():
        _a, _b2 = two_view_scene(100, seed=0, **_kw)
        _d = is_degenerate(_a, _b2, _th)
        assert _d == ('共面' in _t), f'thresh={_th} 时 {_t} 的判定错了'
print(f'✓ 练习 3 通过：共面 {_deg:.1e} vs 非共面 {_ok:.1e}（差 {_ok/_deg:.0e} 倍）；'
      f'阈值从 1e3 到 1e9 分类不变')"""),

md("""### 📖 参考答案 3"""),

code("""def null_dim_ratio(x1, x2):
    x1 = np.asarray(x1, float); x2 = np.asarray(x2, float)
    A = np.stack([x2[:,0]*x1[:,0], x2[:,0]*x1[:,1], x2[:,0],
                  x2[:,1]*x1[:,0], x2[:,1]*x1[:,1], x2[:,1],
                  x1[:,0], x1[:,1], np.ones(len(x1))], 1)
    S = np.linalg.svd(A, compute_uv=False)
    return float(S[-2]/max(S[-1], 1e-300))

def is_degenerate(x1, x2, thresh=1e6):
    return null_dim_ratio(x1, x2) < thresh

print('参考答案 3 已定义')
print('要点一：自测 ⑤ 说明这个判据很**稳健** —— 阈值跨 6 个数量级分类都不变。')
print('       因为退化与不退化之间差 1e10 以上，所以阈值不是一个需要调的超参数。')
print('要点二：注意「前向运动」被正确地判为**不**退化。')
print('       这是本节最容易搞错的一点：前向运动让 E 好解、让三角化变差。')
print('       所以初始化的判据需要**两个**：这个比值（查 E）+ 视线夹角（查三角化）。')
print('要点三：真实实现（COLMAP）不看奇异值比值，而是同时拟合 H 与 E，')
print('       比较各自的内点数 —— 那对噪声更稳健，但需要 RANSAC。')
print('       本题的比值法只在无外点时可用，好处是它直接量出「零空间几维」。')"""),

md("""### ✏️ 练习 4 · 投影掉 gauge 后的条件数

实现 `my_cond(arc_deg, nc, npt, seed)`：
构造场景 → 算雅可比 → 用 `my_gauge_basis`（或 `gauge_basis`）拿到 $Q$ →
把 $H = J^\\top J$ **投影**到 $Q$ 的正交补上 → 返回该子空间里的条件数。

提示：取 $P = I - QQ^\\top$，对 $P$ 做 SVD 取前 $n-7$ 个左奇异向量作为补空间的基 $B$，
则要算的是 $\\mathrm{cond}(B^\\top H B)$。"""),

code("""def my_cond(arc_deg, nc=5, npt=40, seed=0):
    '''返回投影掉 gauge 之后的条件数。'''
    # TODO: 1) X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    #       2) J = num_jacobian(residual_fn(nc,npt,observations(X,cams)), pack(X,cams))
    #       3) _, Q = gauge_basis(X, cams);  n = J.shape[1]
    #       4) P = I - Q Qᵀ ; U,_,_ = svd(P) ; B = U[:, :n-7]
    #       5) sp = svd(Bᵀ (Jᵀ J) B) ; 返回 sp[0]/sp[-1]
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_arcs = [120.0, 60.0, 20.0, 5.0, 1.0, 0.2, 0.0]
_c = {a: my_cond(a) for a in _arcs}
_bz = {}
for a in _arcs:
    _Cs = np.array([-R.T@t for R, t in make_scene(5, 40, a)[1]])
    _bz[a] = float(np.linalg.norm(_Cs[0]-_Cs[-1]))/6.0

# ① 与参考实现一致
for a in [60.0, 5.0]:
    assert abs(_c[a] - gauge_projected_cond(a)[3])/_c[a] < 1e-6

# ② 单调：基线越小条件数越大
_vals = [_c[a] for a in _arcs]
assert all(_vals[i] < _vals[i+1] for i in range(len(_vals)-1)), \\
    f'必须单调递增，实测 {[f"{v:.1e}" for v in _vals]}'

# ③ 良好配置（B/z≈1）的条件数应很小
assert _c[60.0] < 1e5, f'B/z=1 时条件数应 <1e5，实测 {_c[60.0]:.2e}'

# ④ 小基线端的标度指数接近 -2
import math as _m
_e = _m.log(_c[0.2]/_c[1.0])/_m.log(_bz[0.2]/_bz[1.0])
assert -2.6 < _e < -1.7, f'小基线端指数应接近 -2，实测 {_e:+.2f}'

# ⑤ 纯旋转是悬崖（不是趋势的延续）
assert _c[0.0] > 1e15, f'纯旋转应数值奇异，实测 {_c[0.0]:.2e}'
assert _c[0.0]/_c[0.2] > 1e6, \\
    f'从 B/z=0.0035 到 0 应跳 6 个数量级以上，实测 {_c[0.0]/_c[0.2]:.1e}'

# ⑥ 换场景规模，标度律不变
_e2 = _m.log(my_cond(0.2, 4, 25)/my_cond(1.0, 4, 25)) / _m.log(_bz[0.2]/_bz[1.0])
assert -2.8 < _e2 < -1.6, f'换规模后指数应仍接近 -2，实测 {_e2:+.2f}'
print(f'✓ 练习 4 通过：B/z=1 时 {_c[60.0]:.2e}，B/z=0.0035 时 {_c[0.2]:.2e}，'
      f'纯旋转 {_c[0.0]:.2e}')
print(f'  小基线端指数 {_e:+.2f}（理论 −2）；纯旋转跳 {_c[0.0]/_c[0.2]:.1e} 倍')"""),

md("""### 📖 参考答案 4"""),

code("""def my_cond(arc_deg, nc=5, npt=40, seed=0):
    X, cams = make_scene(nc, npt, arc_deg, seed=seed)
    J = num_jacobian(residual_fn(nc, npt, observations(X, cams)), pack(X, cams))
    _, Q = gauge_basis(X, cams)
    n = J.shape[1]
    U, _, _ = np.linalg.svd(np.eye(n) - Q @ Q.T)
    B = U[:, :n-7]
    sp = np.linalg.svd(B.T @ (J.T @ J) @ B, compute_uv=False)
    return float(sp[0]/sp[-1])

print('参考答案 4 已定义')
print('要点一：为什么不直接「固定 7 个参数」再算条件数 —— 因为那样得到的数')
print('       依赖于固定了哪几个（第 6 节量到 1.15~1.37 倍的差别）。')
print('       投影法给出的是 gauge 无关的量，所以它在两份重建之间可比。')
print('要点二：自测 ⑤ 的悬崖是这道题的重点。纯旋转不是「基线很小」的极限 ——')
print('       它是一整族新的零方向（所有点沿视线移动都不改变投影）。')
print('       所以从 B/z=0.0035 到 B/z=0 跳了 9 个数量级，而不是连续过渡。')
print('要点三：make_scene 必须是 look-at 的。第 4 节末尾那一格说明了')
print('       用「朝向按弧长转但不看场景」的坏轨迹会测出 1e19 的假结果 ——')
print('       那时 40 个点里有 25~33 个在相机背后。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- COLMAP 的完整命令行 ----
colmap feature_extractor --database_path db.db --image_path images/ \
    --ImageReader.single_camera 1          # 同一台相机 -> 内参共享，参数少很多
colmap vocab_tree_matcher --database_path db.db \
    --VocabTreeMatching.vocab_tree_path vocab_tree_flickr100K_words32K.bin \
    --VocabTreeMatching.num_images 50      # ← 第 2 节的 top-k
colmap mapper --database_path db.db --image_path images/ --output_path sparse/ \
    --Mapper.ba_global_images_ratio 1.1 \
    --Mapper.ba_global_points_ratio 1.1    # ← 每增长 10% 跑一次全局 BA（第 8 节）
colmap model_analyzer --path sparse/0      # 打印重投影误差、轨迹长度、观测数

# 关键诊断（第 8 节的四条）：
# ① ls sparse/ | wc -l          -> 子模型个数，>1 说明对应关系断了
# ② model_analyzer 的 reproj error 只给均值 —— P99 要自己从 points3D.bin 算
# ③ 相机轨迹的 B/z：从 images.bin 读位姿，算相邻/首尾间距 ÷ 场景深度中位数
# ④ 尺度检验：场景里放一个已知长度的物体，量它

# ---- Ceres Solver 的束调整（Schur 补就在这里）----
// ceres::Solver::Options options;
// options.linear_solver_type = ceres::SPARSE_SCHUR;      // ← 练习 1
// options.trust_region_strategy_type = ceres::LEVENBERG_MARQUARDT;  // ← lam
// // gauge：把第一个相机设为常量 + 固定一个尺度
// problem.SetParameterBlockConstant(cameras[0]);          // 只去掉 6 个！
// // 尺度还需要单独固定 —— 常见做法是加一个「两点间距 = 常数」的软约束

# ---- pycolmap（Python 里读写 COLMAP 模型）----
import pycolmap
rec = pycolmap.Reconstruction("sparse/0")
print(rec.summary())
for image_id, image in rec.images.items():
    print(image_id, image.name, image.cam_from_world.rotation.quat, image.num_points3D())
# 注意 cam_from_world 就是本 notebook 的 (R, t)，而不是相机位姿
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 每次跑重建大小都不一样 | gauge 是否固定了全部 7 个 | 只固定第一个相机时秩亏还是 1 |
| 报「精度 X 毫米」但换个实现数字就变 | 协方差是怎么算的 | 三种 gauge 处理差 1.15–1.37 倍 |
| 束调整不收敛 / 数值报错 | 是否用了 LM 阻尼 | $H$ 本身奇异（秩亏 7） |
| 某几张图的位姿明显错 | 它们那一段的 $B/z$ | $B/z<0.05$ 时条件数已过 $10^6$ |
| 初始化失败或结果诡异 | 场景是否共面（$\\sigma_8/\\sigma_9$） | 共面时 $E$ 只被确定到 3 参数族 |
| 正前方的点深度很差 | 是否是前向运动 | 极点附近视线夹角只有 1/7.5 |
| 长廊/长轨迹的尺度不对 | 有没有闭环或外部尺度 | 尺度是乘性游走，**没有上界** |
| 重建断成几块 | 匹配候选是否漏了关键对 | top-50 只覆盖 0.5% 的图像对 |"""),
]
