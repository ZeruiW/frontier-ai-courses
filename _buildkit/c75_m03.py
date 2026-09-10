# -*- coding: utf-8 -*-
"""C75 模块 03 · 前馈回归：单目深度与点图。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 绝对尺度<strong>在原理上</strong>不可观测（图像逐位相同，差 $1.1\\times10^{-13}$）；"
                   "② <strong>评测协议的三个选择各值一到两个数量级</strong>："
                   "对齐<em>域</em>、自由度、逐图还是全局；"
                   "③ 为什么单目深度报的是「仿射不变」而不是「尺度不变」；"
                   "④ <strong>点图（pointmap）能精确反解焦距（$1.9\\times10^{-16}$）</strong>，"
                   "所以它自带内参——代价是恰好 <strong>3.00×</strong> 过参数化；"
                   "⑤ 前馈方法绕开了 SfM 的哪三种失败，又引入了什么新的失败"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_feedforward.ipynb'
                       '（<strong>尺度不可观测的逐位验证</strong> / '
                       '对齐域 × 自由度 × 逐图/全局的完整协议表 / '
                       '<strong>「对齐域必须与模型的不变性所在的域一致」——两个方向都验</strong> / '
                       '点图反解内参 / 过参数化的一致性代价）'),
    ("核心参考", "Ranftl et al., <em>Towards Robust Monocular Depth Estimation</em>（MiDaS, TPAMI 2022）· "
                 "Ranftl et al., <em>Vision Transformers for Dense Prediction</em>（DPT, ICCV 2021）· "
                 "Yang et al., <em>Depth Anything</em>（CVPR 2024）/ <em>V2</em>（NeurIPS 2024）· "
                 "Wang et al., <em>DUSt3R: Geometric 3D Vision Made Easy</em>（CVPR 2024）· "
                 "Leroy et al., <em>MASt3R</em>（ECCV 2024）· "
                 "Eigen et al., <em>Depth Map Prediction from a Single Image</em>（NeurIPS 2014，尺度不变损失的出处）· "
                 "本课程 <strong>C72</strong> 模块 03（四种补齐缺失自由度的办法）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("unobservable", "先把不可能的部分划出去", "".join([
        P("模块 00 已经给过这个式子，这里把它的后果说完："),
        MATH(r"X \to sX,\;\; t \to st \;\Longrightarrow\; \pi(sX) = \pi(X)"),
        TABLE(["$s$", "最大像素差"], [
            ["0.5", "0.000e+00"],
            ["2.0", "0.000e+00"],
            ["$10^{3}$", "$1.14\\times10^{-13}$"],
            ["$10^{-3}$", "$1.14\\times10^{-13}$"],
        ]),
        DUAL(
            "<strong>所以「单目深度估计」这个任务名字里隐含了一个必须交代的问题："
            "它输出的到底是什么？</strong>"
            "<em>如果是米，那么这个米从哪来——不可能来自图像</em>。"
            "<strong>三种真实的答案：</strong>"
            "① <strong>相对深度</strong>（只保证前后关系与比例，不给单位）；"
            "② <strong>仿射不变的视差</strong>（差一个尺度与一个位移，见第 3 节）；"
            "③ <strong>米</strong>——<em>而这个米来自训练数据里的统计规律"
            "（房间大概多大、人大概多高、车道大概多宽）</em>。",
            "<strong>第三种最有用也最脆弱。</strong>"
            "<em>它把一个几何问题换成了一个统计问题："
            "「这张图的场景尺度与训练分布里哪一类最像」</em>。"
            "<strong>所以它在室内数据上训练、拿到航拍图上就会系统性地错，"
            "而错的方式是<em>整体缩放</em>——图看起来完全合理，只是尺度不对</strong>。"
            "<em>这类错误在任何「相对」指标下都看不见，只在绝对指标下暴露</em>。"),
        CALLOUT("intuition",
                "<strong>与 C72 模块 03 对照着看会更清楚。</strong>"
                "<em>C72 列了四种补齐缺失自由度的办法：另一个视角、平面假设、已知尺寸、另一个传感器</em>。"
                "<strong>前馈单目方法用的是<em>第五种</em>：一个从数据里学到的先验。</strong>"
                "<em>而 C72 的那四种都能写出误差传播公式（比如已知尺寸时误差 ∝ 尺寸分类的相对误差），"
                "第五种不能——它的误差取决于分布偏移的程度，而那没有闭式</em>。"),
    ])),

    # ============================================================== 2
    ("protocol", "评测协议的三个选择，每个都值一到两个数量级", "".join([
        P("拿一个**「视差域仿射意义上完美」**的预测器"
          "（即 $\\hat d = a\\,d_{\\text{真}} + b$ 加上 0.2% 噪声，"
          "这正是 MiDaS/DPT 类模型的形式），"
          "然后用不同的协议去评它："),
        H3("选择一：在哪个域对齐"),
        TABLE(["对齐域", "自由度", "视差域 rel-RMSE", "深度域 AbsRel（中位）",
               "$\\delta<1.25$"], [
            ["<strong>视差域</strong>", "仿射（2）", "<strong>0.00240</strong>",
             "<strong>0.00306</strong>", "<strong>1.0000</strong>"],
            ["视差域", "尺度（1）", "0.25459", "0.33928", "0.2978"],
            ["深度域", "仿射（2）", "$1.03\\times10^{6}$", "0.12809", "0.9416"],
            ["深度域", "尺度（1）", "0.48228", "0.20786", "0.5236"],
        ]),
        DUAL(
            "<strong>只有「视差域 + 仿射」能把这个完美预测器还原到 0.3%。</strong>"
            "<em>其余三种组合都差 40–110 倍</em>。"
            "<strong>原因很干净：仿射关系成立的域是视差域，"
            "换到深度域之后 $\\hat z = 1/(a/z + b)$ 不是 $z$ 的仿射函数</strong>——"
            "<em>所以在深度域拟合一条直线，本身就是在拟合一个错的模型</em>。",
            "<strong>而这条规律是对称的。</strong>"
            "<em>notebook 反过来测了一个「深度域仿射完美」的预测器：</em>"
            "<strong>深度域 + 仿射 → AbsRel 0.000304；"
            "视差域 + 仿射 → 0.073561（差 242 倍）</strong>。"
            "<em>所以规则不是「视差域更好」，而是"
            "<strong>「对齐域必须与模型的不变性所在的域一致」</strong></em>。"
            "<strong>而这意味着：评测协议不能独立于模型来定。</strong>"),
        H3("选择二：逐图对齐还是全数据集共享一组参数"),
        P("真实数据里每张图都有自己的未知尺度（不同场景、不同相机）。"
          "200 张图、每张有自己的 $(a_i, b_i)$："),
        TABLE(["协议", "AbsRel 中位", "P90"], [
            ["<strong>逐图 + 仿射</strong>", "<strong>0.00278</strong>", "0.00506"],
            ["逐图 + 尺度", "0.30152", "0.45975"],
            ["<strong>全数据集共享一组仿射参数</strong>", "<strong>0.42713</strong>",
             "<strong>1.30902</strong>"],
        ]),
        H3("选择三：用哪个指标——它们对<em>同一种</em>错误的反应差很多"),
        P("回到第一张表的第二行（视差域 + 只做尺度对齐）："
          "AbsRel 是 0.33928，而 $\\delta<1.25$ 是 0.2978。"
          "**两个指标都说「很差」，但它们差的方式不同**："),
        TABLE(["指标", "定义", "它对什么敏感", "它对什么不敏感"], [
            ["<strong>AbsRel</strong>",
             "$\\mathrm{median}\\,\\vert\\hat z - z\\vert / z$",
             "<em>相对误差的<strong>典型</strong>大小</em>",
             "<strong>尾部</strong>——<em>用中位数时 10% 的极端错误完全不影响它</em>"],
            ["<strong>$\\delta<1.25$</strong>",
             "$\\max(\\hat z/z,\\,z/\\hat z) < 1.25$ 的像素比例",
             "<em>「有多少像素<strong>合格</strong>」——一个通过率</em>",
             "<strong>合格像素错多少、不合格像素错多离谱</strong>，它都不管"],
            ["RMSE / RMSE-log",
             "$\\sqrt{\\mathrm{mean}(\\cdot)^2}$",
             "<strong>尾部</strong>（平方 + 均值）",
             "<em>而它被远处的大深度支配，所以 RMSE-log 更常用</em>"],
        ]),
        DUAL(
            "<strong>三个指标里只有 $\\delta<1.25$ 有一个绝对的解释："
            "「这个像素的深度可以用吗」。</strong>"
            "<em>而 25% 这个阈值是一个约定，它来自 Eigen et al.(2014)——"
            "并不是某个应用需求推出来的</em>。"
            "<strong>所以做一个具体应用时，正确的做法是按需求换阈值</strong>："
            "<em>机器人抓取可能要 $\\delta<1.02$，"
            "而背景虚化只需要 $\\delta<1.5$</em>。",
            "<strong>而组合起来看才有意义。</strong>"
            "<em>AbsRel 小但 $\\delta<1.25$ 也低 → 大部分像素略微超标（系统性偏置）；"
            "AbsRel 大但 $\\delta<1.25$ 高 → 少数像素错得很离谱（离群/遮挡）；"
            "两个都差 → 尺度或对齐口径错了（第一张表的第 2、4 行）</em>。"
            "<strong>只报一个指标，这三种情形无法区分。</strong>"),
        CALLOUT("danger",
                "<strong>三个选择合起来，同一个模型的 AbsRel 可以是 0.003 或 0.427——差 154 倍。</strong>"
                "<em>而三者都是「合理的」协议，只是回答不同的问题</em>："
                "<strong>逐图对齐问「形状对不对」，全局对齐问「形状 + 跨场景的尺度一致性对不对」，"
                "不对齐问「绝对尺度对不对」。</strong>"
                "<em>所以看到一个单目深度的数字时，必须先问三件事："
                "<strong>域、自由度、逐图还是全局</strong>——"
                "缺任何一个，这个数字都不可比</em>。"),
    ])),

    # ============================================================== 3
    ("why-affine", "为什么是「仿射不变」而不是「尺度不变」", "".join([
        P("尺度歧义只有 1 个自由度（第 1 节），"
          "那么第 2 节里那个「位移」$b$ 是从哪来的？"),
        TABLE(["位移 $b$", "尺度对齐的 rel-RMSE", "仿射对齐的 rel-RMSE", "比值"], [
            ["0.00", "0.00234", "0.00234", "1.0×"],
            ["0.05", "0.04034", "0.00234", "17.2×"],
            ["0.42", "0.25265", "0.00234", "<strong>107.9×</strong>"],
            ["2.00", "0.53258", "0.00234", "227.5×"],
        ]),
        DUAL(
            "<strong>$b=0$ 时两种对齐完全相同——所以位移项确实是一个<em>额外</em>的自由度，"
            "不是尺度的一部分。</strong>"
            "<em>它的来源是训练侧而不是几何侧</em>："
            "<strong>MiDaS 类模型在十几个数据集上混合训练，"
            "而这些数据集的「深度」定义各不相同</strong>——"
            "<em>有的是米、有的是视差、有的是相对深度、有的经过未知的重标定；"
            "而且很多只有<strong>相对</strong>标注</em>。"
            "<strong>要在这些数据上共同训练，就必须用一个对「尺度 + 位移」都不变的损失。</strong>",
            "<strong>而选<em>视差</em>而不是深度，有一个独立的理由：$z\\to\\infty$ 时视差 $\\to 0$，是有界的。</strong>"
            "<em>天空、远景在深度域是 $+\\infty$（无法回归），在视差域是 0（可以回归）</em>。"
            "<strong>所以「预测视差 + 仿射不变损失」这个组合是被两件事同时逼出来的："
            "① 混合数据集的标注不一致；② 深度的无界性。</strong>"
            "<em>而代价就是第 2 节那张表——用错口径会让数字差两个数量级</em>。"),
        CALLOUT("warn",
                "<strong>一个由此推出的实践建议：把「模型输出什么」写进接口签名里。</strong>"
                "<em>返回一个裸的 $H\\times W$ 数组时，调用方无法知道它是相对深度、"
                "仿射不变视差、还是米——而这三者的下游用法完全不同</em>。"
                "<strong>而这类混淆在跨团队协作时几乎必然发生一次</strong>："
                "<em>一方按「米」用，另一方按「视差」出，结果是前后关系整体反转"
                "（因为视差与深度是倒数关系）</em>。"),
        CALLOUT("paper",
                "<strong>Depth Anything V2 之后的一个变化值得注意：出现了「metric」分支。</strong>"
                "<em>做法是在仿射不变的骨干上再接一个针对特定域（室内/室外）微调的头，"
                "让它直接输出米</em>。"
                "<strong>这不是解决了第 1 节的不可观测性，而是把那个统计先验<em>显式化</em>了</strong>——"
                "<em>所以它必须按域分开训练与使用，而跨域用就会系统性地缩放错</em>。"),
    ])),

    # ============================================================== 4
    ("pointmap", "点图：把内参也一起回归掉", "".join([
        P("DUSt3R 类方法的输出不是深度图，而是**点图**（pointmap）："
          "每个像素对应一个 3D 点 $(X,Y,Z)$，且**两张图的点图在同一个坐标系里**。"),
        ASCII("""
   深度图 vs 点图：

   深度图：  像素 (u,v) -> z            需要内参 K 才能变成 3D 点
             1 个通道                    -> 所以内参必须已知或另外估计

   点图：    像素 (u,v) -> (X, Y, Z)     **自带**内参信息
             3 个通道                    -> 因为 u = cx + f X/Z 反过来能解出 f

   而「两张图共一个坐标系」意味着相对位姿也自带了：
             对应点的刚体变换 = 相对位姿  -> 所以 SfM 那一步也被吸收了
        """),
        TABLE(["真值 $f$", "从点图最小二乘反解的 $f$", "相对误差"], [
            ["300.0", "300.0000", "$1.9\\times10^{-16}$"],
            ["600.0", "600.0000", "$1.9\\times10^{-16}$"],
            ["1200.0", "1200.0000", "$1.9\\times10^{-16}$"],
        ]),
        DUAL(
            "<strong>焦距是<em>精确</em>可解的（$u - c_x = f\\,X/Z$ 是一个超定线性方程）。</strong>"
            "<em>所以「预测点图」这个输出形式把「标定」这一步也吸收进了网络</em>。"
            "<strong>这就是 pose-free、calibration-free 的真实含义："
            "不是不需要内参，而是内参被<em>输出</em>而不是被<em>输入</em>。</strong>",
            "<strong>而代价是过参数化，且倍数恰好是 3.00：</strong>"
            "<em>点图有 $3HW$ 个自由度，而它要表示的东西只有"
            "（深度 $HW$ + 内参 1~4）个</em>。"),
        TABLE(["分辨率", "点图的自由度", "深度 + 焦距", "<strong>冗余</strong>"], [
            ["48×64", "9,216", "3,073", "<strong>3.00×</strong>"],
            ["384×512", "589,824", "196,609", "<strong>3.00×</strong>"],
        ]),
        DUAL(
            "<strong>冗余的后果是「一致性必须靠网络自己保证，而不是被构造保证」。</strong>"
            "<em>一个合法的深度图 + 内参组合<strong>必然</strong>对应一个「射线一致」的点图"
            "（所有点都落在从光心出发的射线束上）；"
            "但一个任意的 $3HW$ 张量<strong>不必</strong>如此</em>。"
            "<strong>所以网络输出的点图可能是「几何上不自洽」的</strong>——"
            "<em>而这种不自洽在可视化上不明显，但在下游（三角化、位姿求解）会放大</em>。",
            "<strong>实践中的对策有两条，都在真实实现里出现：</strong>"
            "① <strong>后处理投影</strong>——"
            "<em>从点图先解出 $f$，再把每个点投影回它自己的射线上（只保留深度分量），"
            "于是自洽性被强制恢复</em>；"
            "② <strong>全局对齐</strong>（DUSt3R 的第二阶段）——"
            "<em>把多对点图放进一个优化里，同时求各图的位姿与尺度，"
            "而这一步<strong>本质上就是一次束调整</strong>（模块 01）</em>。"
            "<strong>所以 pose-free 方法并没有真的取消 SfM，它把 SfM 从"
            "「必须先做对」变成了「用来收尾」。</strong>"),
    ])),

    # ============================================================== 5
    ("global-align", "全局对齐：它<em>就是</em>一次束调整", "".join([
        P("点图是逐<strong>对</strong>预测的（DUSt3R 一次吃两张图），"
          "而每一对有自己的未知尺度。要把 $N$ 张图拼成一个模型，"
          "就要同时求各图的位姿、各对的尺度、以及公共的 3D 点——"
          "**而这是一个和模块 01 同构的问题**。"),
        TABLE(["$N{=}5$（10 对，60 个点）", "个数"], [
            ["各图位姿", "$5\\times6 = 30$"],
            ["各对尺度", "$10\\times1 = 10$"],
            ["场景点", "$60\\times3 = 180$"],
            ["<strong>参数合计</strong>", "<strong>220</strong>"],
            ["观测（每对两张点图 × 60 点 × 3 维）", "3,600"],
            ["<strong>Hessian 的秩亏</strong>", "<strong>恰好 7</strong>（谱间隙 $3.6\\times10^{12}$）"],
        ]),
        DUAL(
            "<strong>秩亏 7——与模块 01 的束调整<em>完全相同</em>，"
            "因为它是同一个 gauge：世界坐标系的相似变换。</strong>"
            "<em>区别只在残差的形式：模块 01 是 2D 重投影差，这里是 3D 点差</em>。"
            "<strong>所以模块 01 的全套结论直接适用</strong>："
            "<em>需要固定或投影掉 gauge（否则尺度会随机漂移）、"
            "点块是块对角的所以可以用 Schur 补、"
            "协方差依赖 gauge 的选择</em>。",
            "<strong>而这说明「pose-free」并没有取消 SfM，它换了 SfM 的<em>位置</em>：</strong>"
            "<em>传统流程里 SfM 在最前面，必须先做对，做不对整条链就断（模块 01 第 2、6 节）；"
            "前馈流程里前馈网络先给出每对的几何，"
            "然后用一次<strong>已经有很好初值</strong>的全局优化收尾</em>。"
            "<strong>后者的关键优势不是「不需要优化」，而是「优化不会掉进坏的局部解」</strong>——"
            "<em>因为初值不是从零开始的贪心增量，而是网络一次给出的</em>。"),
        H3("而尺度为什么能解出来：靠「点被共享」"),
        P("单看一对，那一对的尺度与全局尺度**不可分**（合并成 1 个自由度，"
          "而它属于第 1 节说的不可观测部分）。"
          "两对一旦共享同一批 3D 点，它们的**相对**尺度就被绑定了。"),
        TABLE(["$N$", "对数", "参数", "观测", "冗余"], [
            ["2", "1", "133", "240", "+107"],
            ["3", "3", "141", "720", "+579"],
            ["5", "10", "160", "2,400", "+2,240"],
            ["8", "28", "196", "6,720", "+6,524"],
        ]),
        CALLOUT("intuition",
                "<strong>顺带一个很实用的调试技巧，我在做这个实验时用上了。</strong>"
                "<em>第一版我把残差写成「只用每对的<strong>参考</strong>视图的点图」，"
                "结果秩亏是 <strong>13</strong> 而不是 7</em>。"
                "<strong>多出来的 6 立刻指出了 bug：相机 4 从来不是任何一对的参考，"
                "所以它的 6 个参数完全没出现在残差里</strong>"
                "（<em>雅可比里那 6 列的范数是 0</em>）。"
                "<strong>所以「数一数零空间的维数」是检查"
                "「我的残差是不是漏了某个变量」最快的办法</strong>——"
                "<em>它比读代码快，而且给出的是<strong>缺了几个自由度</strong>这个精确信息</em>。"),
    ])),

    # ============================================================== 6
    ("outputs", "输出表示的四种选择：各自把哪一部分「构造保证」掉了", "".join([
        P("前馈方法的输出形式不是实现细节——**它决定了哪些一致性是<em>免费</em>的、"
          "哪些必须靠网络自己学会**。用「自由度账」来看最清楚"
          "（以 $H\\times W$ 的图像为单位）："),
        TABLE(["输出表示", "自由度", "真正需要的自由度", "冗余",
               "构造上<strong>免费</strong>保证的", "必须靠网络学会的"], [
            ["<strong>相对深度</strong>（视差图）", "$HW$", "$HW$", "<strong>1.00×</strong>",
             "<em>射线一致性（每个像素只有一个沿射线的量）</em>",
             "尺度与位移（第 3 节：2 个自由度对不上）"],
            ["<strong>度量深度</strong>", "$HW$", "$HW$", "<strong>1.00×</strong>",
             "<em>同上，且尺度已定</em>",
             "<strong>尺度的正确性</strong>——而它来自分布假设（第 1 节）"],
            ["<strong>点图</strong> pointmap", "$3HW$", "$HW+1$",
             "<strong>3.00×</strong>",
             "<em>无需内参；相对位姿隐含在两图的点图里</em>",
             "<strong>射线一致性 + 内参自洽</strong>（第 4 节）"],
            ["<strong>直接出高斯</strong>（Splatter Image 类）",
             "$\\approx 14 HW$ 起（C74 模块 05）", "$HW+1$",
             "<strong>&gt; 14×</strong>",
             "<em>可直接渲染，无需后处理</em>",
             "<strong>几何 + 外观 + 不透明度全部</strong>"],
        ]),
        DUAL(
            "<strong>规律很清楚：冗余越大，网络要自己学会的一致性越多。</strong>"
            "<em>深度图的冗余是 1.00×，所以它<strong>不可能</strong>输出一个"
            "「几何上不自洽」的结果——射线一致性是被表示本身构造保证的</em>。"
            "<strong>点图的 3.00× 冗余买到了「不需要内参」，"
            "代价是它<em>可以</em>输出不自洽的东西（第 4 节）。</strong>",
            "<strong>而这个取舍与 C74 模块 02 的那个是同一类：</strong>"
            "<em>C74 里「不直接存协方差、而存 $(s,q)$ 再算 $RSS^\\top R^\\top$」"
            "把正定性<strong>编码进了参数化</strong>，于是优化器再也不可能违反它</em>。"
            "<strong>这里是反方向的选择：点图<em>放弃</em>了把射线一致性编码进表示，"
            "换来了内参的自由。</strong>"
            "<em>两个课程、两个方向，而判断的依据相同："
            "「这个约束是硬的还是软的？硬的就编码进表示，软的才交给优化」</em>。"),
        CALLOUT("paper",
                "<strong>所以「该选哪种输出」有一个可操作的判据：</strong>"
                "<em>内参已知且可信 → 用深度图（冗余 1.00×，一致性免费）；"
                "内参未知或不可信 → 用点图（多付 3× 冗余，换标定自由）；"
                "要直接渲染且不在乎几何精度 → 直接出高斯</em>。"
                "<strong>而最后一种在几何评测上通常最差</strong>——"
                "<em>因为它把几何、外观、不透明度混在一个 $14HW$ 的张量里，"
                "而只有渲染损失在监督它</em>（C74 模块 05 第 7 节的「要几何准就用 2DGS」是同一件事）。"),
    ])),

    # ============================================================== 7
    ("tradeoff", "前馈绕开了什么，又引入了什么", "".join([
        TABLE(["SfM 的失败模式（模块 01）", "前馈方法还怕它吗", "为什么"], [
            ["<strong>视角太少</strong>（1–2 张）",
             "<strong>不怕</strong>",
             "<em>先验代替了几何约束——这是它最大的卖点</em>"],
            ["<strong>基线太短 / 纯旋转</strong>"
             "（条件数 $4.4\\times10^{17}$）",
             "<strong>不怕</strong>",
             "<em>单目预测根本不依赖基线</em>"],
            ["<strong>无纹理 / 周期纹理</strong>（模块 02）",
             "<strong>基本不怕</strong>",
             "<em>先验会「填」进一个合理的表面，"
             "而不是像 NCC 一样给出噪声（模块 02 第 3 节）</em>"],
            ["<strong>共面场景</strong>（$E$ 退化）", "不怕", "<em>不解 $E$</em>"],
        ]),
        TABLE(["前馈方法<em>新</em>引入的失败模式", "表现", "怎么检测"], [
            ["<strong>尺度分布偏移</strong>",
             "整体缩放错，但图看起来完全合理",
             "<strong>只有绝对指标能抓到</strong>——"
             "<em>而第 2 节说逐图对齐会把它完全掩盖掉</em>"],
            ["<strong>几何不自洽</strong>（第 4 节的过参数化）",
             "点图不落在射线束上；多对点图拼不起来",
             "<em>投影回射线后看残差；或看全局对齐的收敛残差</em>"],
            ["<strong>「合理但错」的补全</strong>",
             "遮挡区、玻璃、镜子处给出一个平滑合理的表面，而它不对",
             "<strong>无法从单张图检测</strong>——"
             "<em>必须用另一个视角或另一个传感器</em>"],
            ["<strong>对分布内的场景过于自信</strong>",
             "不输出不确定度，或输出的不确定度与真实误差不相关",
             "<em>需要专门的校准评估（见 C10）</em>"],
        ]),
        DUAL(
            "<strong>把两张表并排读，结论是「两类方法的失败模式几乎不重叠」。</strong>"
            "<em>几何方法在信息不足时<strong>拒绝回答</strong>（条件数爆掉、代价曲线平）；"
            "前馈方法在信息不足时<strong>照样回答</strong>（先验会填）</em>。"
            "<strong>所以它们是互补的，而不是替代关系。</strong>",
            "<strong>而这就是 2024 年以来的主流做法：<em>混合</em>。</strong>"
            "<em>用前馈方法做初始化与「无纹理区的填充」，"
            "用几何优化（束调整）做收尾与精度</em>。"
            "<strong>MASt3R 就是这个形状：前馈出点图与匹配，再做全局对齐；"
            "而 3DGS/2DGS 的位姿也越来越多地由前馈方法给初值、再联合优化。</strong>"
            "<em>模块 05 会说明这条混合路线对<strong>评测</strong>的影响："
            "当初值来自一个学到的先验时，「重建误差」里混进了「先验有多合适」这一项</em>。"),
    ])),

    # ============================================================== 8
    ("diagnose", "诊断：一个前馈重建能不能用", "".join([
        P("按「花的时间从少到多」排列。前两条不需要任何真值。"),
        OL([
            "<strong>射线一致性检验（点图专用，不需要真值）</strong>——"
            "<em>从点图先解出 $f$（第 4 节：精确可解），"
            "再把每个点投影回它自己的射线上，看残差</em>。"
            "<strong>残差大就说明网络输出的 $3HW$ 张量不自洽，"
            "而这时任何下游几何计算都不可信</strong>",
            "<strong>换视角渲一张（如果有稠密表示）</strong>——"
            "<em>与 C74 模块 05 的浮物检测是同一招。"
            "遮挡区被「合理地填」出来的东西，在新视角下立刻露馅</em>",
            "<strong>全局对齐的收敛残差（第 5 节）</strong>——"
            "<em>把多对点图放进一次优化。残差小说明各对之间自洽；"
            "残差大说明至少有一对是错的，而<strong>看每对的残差就能定位是哪一对</strong></em>",
            "<strong>用一个已知长度做尺度检验</strong>——"
            "<em>这是唯一能抓到第 1 节那个「整体缩放错」的办法。"
            "而它也是 gauge 无关的（模块 01 第 7 节）</em>",
            "<strong>与几何方法交叉验证</strong>——"
            "<em>在纹理充分的区域跑一次 MVS（模块 02），"
            "与前馈结果比。<strong>两者的失败模式几乎不重叠（第 7 节），"
            "所以它们一致的地方基本可信</strong></em>",
        ]),
        CALLOUT("intuition",
                "<strong>这五条的顺序不是随意排的：前两条不需要真值，后三条需要。</strong>"
                "<em>而「不需要真值的自检」在部署时是唯一可用的——"
                "线上没有真值，但射线一致性与「换视角渲一张」随时都能做</em>。"
                "<strong>所以把它们做成一条自动流水线，比事后拿真值评测更有价值</strong>——"
                "<em>后者只能告诉你「上次那批数据上表现如何」，"
                "前者能告诉你「这一次的输出可不可信」</em>。"),
        CALLOUT("danger",
                "<strong>而有一类问题这五条都抓不到：<em>整个场景</em>的尺度先验用错了，"
                "但内部完全自洽。</strong>"
                "<em>射线一致 ✓、新视角合理 ✓、全局对齐收敛 ✓、"
                "与 MVS 一致 ✓（因为 MVS 也只有相对尺度）</em>。"
                "<strong>只有第 4 条（已知长度）能抓到它</strong>——"
                "<em>所以如果你的应用真的需要米，那么「场景里放一个已知尺寸的标定物」"
                "不是可选的工程便利，而是<strong>唯一</strong>的信息来源</em>。"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 03 · 前馈回归：单目深度与点图

本 notebook 把讲解页的五个结论跑出来：

1. **绝对尺度不可观测**（图像逐位相同，差 $1.1\\times10^{-13}$）；
2. **评测协议的三个选择各值一到两个数量级**：对齐**域** × 自由度 × 逐图/全局；
   而规则是「**对齐域必须与模型的不变性所在的域一致**」——两个方向都验；
3. 三个常用指标对**同一种**错误的反应差很多；
4. **点图能精确反解焦距（$1.9\\times10^{-16}$）**，代价是恰好 **3.00×** 过参数化；
5. **全局对齐的 Hessian 秩亏恰好 7** —— 它就是一次束调整；
   而我第一版写成 13，那 6 个多出来的立刻定位了建模 bug。

只用 numpy，CPU，离线。不训练任何网络 —— 用解析构造的「完美预测器」当替身。"""),

code("""import numpy as np, math
print('numpy', np.__version__)
F, CX, CY = 600.0, 320.0, 240.0

def project(X, R=None, t=None, f=F):
    X = np.atleast_2d(np.asarray(X, float))
    R = np.eye(3) if R is None else np.asarray(R, float)
    t = np.zeros(3) if t is None else np.asarray(t, float)
    P = (R @ X.T).T + t
    assert np.all(P[:, 2] > 1e-9)
    return np.stack([CX + f*P[:, 0]/P[:, 2], CY + f*P[:, 1]/P[:, 2]], 1)

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

print(f'相机 f={F:.0f} 主点=({CX:.0f},{CY:.0f})')"""),

md("""## 1 · 绝对尺度不可观测"""),

code("""rng = np.random.default_rng(0)
X0 = rng.normal(0, 1, (300, 3)) + np.array([0, 0, 6.0])
R0, t0 = np.eye(3), np.array([0.3, -0.1, 0.0])
uv0 = project(X0, R0, t0)
print(' s          最大像素差')
for s in [0.5, 2.0, 1e3, 1e-3, 1e6]:
    d = np.abs(project(X0*s, R0, t0*s) - uv0).max()
    print(f' {s:9.0e}   {d:.3e}')
    assert d < 1e-8
print('\\n✓ 逐位相同 —— 所以「单目深度输出米」这件事，那个米不可能来自图像')
print('  三种真实的答案：① 相对深度；② 仿射不变的视差；③ 米（而它来自训练分布的统计）')
print('  第三种最有用也最脆弱：换一类场景就会**整体缩放错**，而图看起来完全合理。')"""),

md("""## 2 · 评测协议的三个选择

用一个**「视差域仿射意义上完美」**的预测器（$\\hat d = a\\,d_{\\text{真}} + b$ + 0.2% 噪声，
这正是 MiDaS/DPT 类模型的形式）来量各种协议。"""),

code("""def fit_align(pred, gt, dof):
    '''dof=1 -> 只拟合尺度；dof=2 -> 拟合尺度+位移。返回对齐后的 pred。'''
    p = np.asarray(pred, float); g = np.asarray(gt, float)
    if dof == 1:
        return float((p @ g)/(p @ p))*p
    A = np.stack([p, np.ones_like(p)], 1)
    c, *_ = np.linalg.lstsq(A, g, rcond=None)
    return A @ c

def metrics(z_pred, z_gt):
    '''返回 (AbsRel 中位, delta<1.25 的比例, RMSE-log)。'''
    zp = np.clip(np.asarray(z_pred, float), 1e-6, None)
    zg = np.asarray(z_gt, float)
    absrel = float(np.median(np.abs(zp - zg)/zg))
    thr = np.maximum(zp/zg, zg/zp)
    d1 = float((thr < 1.25).mean())
    rmse_log = float(np.sqrt(np.mean((np.log(zp) - np.log(zg))**2)))
    return absrel, d1, rmse_log

def evaluate(pred_disp, z_gt, domain, dof):
    '''domain ∈ {"disparity","depth"}；返回 (视差域 relRMSE, AbsRel, delta<1.25, RMSElog)。'''
    disp_gt = 1.0/z_gt
    if domain == 'disparity':
        al = fit_align(pred_disp, disp_gt, dof)
        zp = 1.0/np.clip(al, 1e-6, None)
    else:
        z_raw = 1.0/np.clip(pred_disp, 1e-6, None)
        zp = np.clip(fit_align(z_raw, z_gt, dof), 1e-6, None)
        al = 1.0/zp
    rel = float(np.sqrt(np.mean((al - disp_gt)**2)/np.mean(disp_gt**2)))
    return (rel,) + metrics(zp, z_gt)

rg = np.random.default_rng(0)
z_gt = rg.uniform(1.0, 20.0, 5000)
disp_gt = 1.0/z_gt
A_TRUE, B_TRUE = 3.7, 0.42
pred_aff = A_TRUE*disp_gt + B_TRUE + rg.normal(0, 0.002, len(z_gt))   # 视差域仿射完美

print('预测器：视差域仿射意义上完美（真实模型就是这个形式）\\n')
print(' 对齐域      自由度   视差域 relRMSE   AbsRel     δ<1.25    RMSE-log')
RES = {}
for dom in ['disparity', 'depth']:
    for dof in [2, 1]:
        r = evaluate(pred_aff, z_gt, dom, dof)
        RES[(dom, dof)] = r
        nm = {1: '尺度(1)', 2: '仿射(2)'}[dof]
        print(f' {dom:10s}  {nm:8s} {r[0]:13.5f}   {r[1]:.5f}   {r[2]:.4f}   {r[3]:.5f}')

best = RES[('disparity', 2)]
assert best[1] < 0.01, f'视差域+仿射应把完美预测器还原到 <1%，实测 {best[1]:.5f}'
for k, v in RES.items():
    if k != ('disparity', 2):
        assert v[1] > 10*best[1], f'{k} 的 AbsRel 应差一个数量级以上：{v[1]:.5f}'
print(f'\\n✓ **只有「视差域 + 仿射」**能还原到 AbsRel {best[1]:.5f}')
print(f'  其余三种组合：{", ".join(f"{RES[k][1]:.5f}" for k in RES if k != ("disparity",2))}'
      f' —— 差 {min(RES[k][1] for k in RES if k != ("disparity",2))/best[1]:.0f} 倍以上')
print('  原因：仿射关系成立的域是视差域。换到深度域后 ẑ = 1/(a/z + b) 不是 z 的仿射函数，')
print('        所以在深度域拟合一条直线本身就是在拟合一个**错的模型**。')"""),

code("""# 规则是对称的：换一个「深度域仿射完美」的预测器
z_gt2 = rg.uniform(1.0, 20.0, 5000)
pred_z = 2.3*z_gt2 + 1.1 + rg.normal(0, 0.01, len(z_gt2))     # 深度域仿射完美
pred_disp_from_z = 1.0/np.clip(pred_z, 1e-6, None)

print('预测器：**深度域**仿射意义上完美\\n')
print(' 对齐域      自由度   AbsRel')
RES2 = {}
for dom in ['depth', 'disparity']:
    for dof in [2, 1]:
        r = evaluate(pred_disp_from_z, z_gt2, dom, dof)
        RES2[(dom, dof)] = r[1]
        print(f' {dom:10s}  {"仿射(2)" if dof==2 else "尺度(1)":8s} {r[1]:.6f}')

assert RES2[('depth', 2)] < 0.01, '深度域仿射应还原它'
assert RES2[('disparity', 2)] > 10*RES2[('depth', 2)], '换域应差一个数量级以上'
print(f'\\n✓ 对称地成立：这次是「深度域 + 仿射」最好（{RES2[("depth",2)]:.6f}），'
      f'而视差域+仿射是 {RES2[("disparity",2)]:.6f}（差 {RES2[("disparity",2)]/RES2[("depth",2)]:.0f} 倍）')
print('\\n✓ 所以规则不是「视差域更好」，而是')
print('  **「对齐域必须与模型的不变性所在的域一致」** ——')
print('  这意味着评测协议**不能独立于模型来定**。')

# 位移项 b 的作用：b=0 时两种自由度等价
print('\\n位移项 b 的作用（视差域）：')
print('  b        尺度对齐 relRMSE   仿射对齐   比值')
for b in [0.0, 0.05, 0.42, 2.0]:
    p = A_TRUE*disp_gt + b + rg.normal(0, 0.002, len(z_gt))
    e1 = evaluate(p, z_gt, 'disparity', 1)[0]
    e2 = evaluate(p, z_gt, 'disparity', 2)[0]
    print(f' {b:5.2f}    {e1:14.5f}   {e2:.5f}   {e1/e2:8.1f}×')
_p0 = A_TRUE*disp_gt + rg.normal(0, 0.002, len(z_gt))
_r1 = evaluate(_p0, z_gt, 'disparity', 1)[0]; _r2 = evaluate(_p0, z_gt, 'disparity', 2)[0]
assert abs(_r1 - _r2)/_r2 < 0.15, 'b=0 时两种自由度应几乎等价'
print(f'\\n✓ b=0 时两者几乎相同（{_r1:.5f} vs {_r2:.5f}）—— 所以位移确实是一个**额外**的自由度')
print('  它的来源是训练侧：MiDaS 类模型在十几个标注定义不一致的数据集上混合训练，')
print('  所以必须用一个对「尺度 + 位移」都不变的损失。')
print('  而选视差而不是深度还有一个独立理由：z→∞ 时视差→0（有界，可回归）。')"""),

code("""# 第三个选择：逐图对齐 vs 全数据集共享一组参数
n_img, per = 200, 50
zz = rg.uniform(1.0, 20.0, (n_img, per)); dd = 1.0/zz
ai = rg.uniform(2.0, 6.0, (n_img, 1))          # 每张图有自己的尺度
bi = rg.uniform(-0.2, 0.8, (n_img, 1))         # 与位移
PP = ai*dd + bi + rg.normal(0, 0.002, (n_img, per))

def protocol_absrel(mode):
    out = []
    if mode == 'global-affine':
        A = np.stack([PP.ravel(), np.ones(PP.size)], 1)
        c, *_ = np.linalg.lstsq(A, dd.ravel(), rcond=None)
    for i in range(n_img):
        if mode == 'per-image-affine':
            al = fit_align(PP[i], dd[i], 2)
        elif mode == 'per-image-scale':
            al = fit_align(PP[i], dd[i], 1)
        elif mode == 'global-affine':
            al = np.stack([PP[i], np.ones(per)], 1) @ c
        zp = 1.0/np.clip(al, 1e-6, None)
        out.append(np.median(np.abs(zp - zz[i])/zz[i]))
    return np.array(out)

print('200 张图、每张有自己的 (a_i, b_i)（真实情况：不同场景的尺度不同）\\n')
print(' 协议                    AbsRel 中位    P90')
PR = {}
for mode in ['per-image-affine', 'per-image-scale', 'global-affine']:
    v = protocol_absrel(mode); PR[mode] = v
    print(f' {mode:22s}  {np.median(v):.5f}    {np.percentile(v,90):.5f}')

_pa = np.median(PR['per-image-affine']); _ga = np.median(PR['global-affine'])
assert _pa < 0.01, f'逐图仿射应 <0.01，实测 {_pa:.5f}'
assert _ga/_pa > 50, f'全局对齐应差 50 倍以上，实测 {_ga/_pa:.0f}'
print(f'\\n✓ 逐图仿射 {_pa:.5f} vs 全数据集共享一组 {_ga:.5f} —— 差 {_ga/_pa:.0f} 倍')
print('\\n三个选择合起来，同一个模型的 AbsRel 可以是 %.5f 或 %.5f —— 差 %.0f 倍。'
      % (_pa, _ga, _ga/_pa))
print('而三者都是「合理的」协议，只是回答不同的问题：')
print('  逐图对齐   -> 问「形状对不对」')
print('  全局对齐   -> 问「形状 + 跨场景的尺度一致性对不对」')
print('  不对齐     -> 问「绝对尺度对不对」')
print('所以看到一个单目深度的数字时必须先问三件事：域、自由度、逐图还是全局。')"""),

md("""## 3 · 指标本身的选择：它们对同一种错误的反应不同"""),

code("""print('回到「视差域 + 只做尺度对齐」那一档（一个被口径拖累的完美模型）：')
_r = RES[('disparity', 1)]
print(f'  AbsRel {_r[1]:.5f}   δ<1.25 {_r[2]:.4f}   RMSE-log {_r[3]:.5f}')
print('两个指标都说「很差」，但差的方式不同。构造三种**不同**的错误来看：\\n')

def make_error(kind):
    '''三种不同性质的错误，都作用在「完美预测」上。'''
    base = disp_gt.copy()
    r = np.random.default_rng(11)
    if kind == '系统性偏置 8%':
        return base*1.08
    if kind == '5% 的像素错得离谱':
        p = base.copy()
        idx = r.choice(len(p), int(0.05*len(p)), replace=False)
        p[idx] *= r.uniform(0.2, 5.0, len(idx))
        return p
    if kind == '全局尺度错 30%':
        return base*1.30
    raise ValueError(kind)

print(' 错误类型                AbsRel     δ<1.25    RMSE-log   （不对齐）')
for kind in ['系统性偏置 8%', '5% 的像素错得离谱', '全局尺度错 30%']:
    p = make_error(kind)
    zp = 1.0/np.clip(p, 1e-6, None)
    a, d1, rl = metrics(zp, z_gt)
    print(f' {kind:22s}  {a:.5f}   {d1:.4f}   {rl:.5f}')

_e_bias = metrics(1.0/(disp_gt*1.08), z_gt)
_e_out = metrics(1.0/np.clip(make_error('5% 的像素错得离谱'), 1e-6, None), z_gt)
_e_sc = metrics(1.0/(disp_gt*1.30), z_gt)
# 系统性偏置：AbsRel 明确，delta 全过
assert _e_bias[1] > 0.99, '8% 的系统偏置应全部通过 δ<1.25'
# 离群：AbsRel 很小（中位数不受影响）而 delta 掉了
assert _e_out[0] < 0.01, f'5% 离群时 AbsRel 中位数应几乎不受影响，实测 {_e_out[0]:.5f}'
assert _e_out[1] < 0.97, f'而 δ<1.25 应掉下来，实测 {_e_out[1]:.4f}'
print(f'\\n✓ 「5% 的像素错得离谱」：AbsRel（中位）只有 {_e_out[0]:.5f}（几乎不动），'
      f'而 δ<1.25 掉到 {_e_out[1]:.4f}')
print(f'✓ 「8% 系统性偏置」：AbsRel {_e_bias[0]:.5f}（明确反映），'
      f'而 δ<1.25 是 {_e_bias[1]:.4f}（全部通过 —— 完全看不见）')
print('\\n所以组合起来看才有意义：')
print('  AbsRel 小但 δ 也低   -> 少数像素错得离谱（离群/遮挡）')
print('  AbsRel 大但 δ 很高   -> 大部分像素略微超标（系统性偏置）')
print('  两个都差             -> 尺度或对齐口径错了')
print('只报一个指标，这三种情形无法区分。')
print(f'\\n而 δ<1.25 里的 25% 是一个**约定**（来自 Eigen et al. 2014），不是需求推出来的。')
print(' 阈值      「8% 系统偏置」的通过率')
for thr in [1.02, 1.05, 1.10, 1.25, 1.50]:
    zp = 1.0/(disp_gt*1.08)
    t = np.maximum(zp/z_gt, z_gt/zp)
    print(f'  {thr:.2f}    {float((t<thr).mean()):.4f}')
print('  ✓ 换阈值就换结论 —— 机器人抓取可能要 δ<1.02，背景虚化只需 δ<1.5')"""),

md("""## 4 · 点图：把内参也一起回归掉"""),

code("""def focal_from_pointmap(Xc, Yc, Zc, W, H):
    '''从点图（相机系的 3D 点）最小二乘反解焦距。假设主点在图像中心。'''
    hh, ww = Zc.shape
    vv, uu = np.mgrid[0:hh, 0:ww]
    # u - cx = f * X/Z ; v - cy = f * Y/Z
    a = np.concatenate([(Xc/Zc).ravel(), (Yc/Zc).ravel()])
    b = np.concatenate([(uu - W/2).ravel(), (vv - H/2).ravel()])
    return float((a @ b)/(a @ a))

H_, W_ = 48, 64
print(' 真值 f      反解 f          相对误差')
for f_true in [300.0, 600.0, 1200.0, 2400.0]:
    zz2 = rg.uniform(2.0, 10.0, (H_, W_))
    vv, uu = np.mgrid[0:H_, 0:W_]
    Xc = (uu - W_/2)*zz2/f_true; Yc = (vv - H_/2)*zz2/f_true
    f_est = focal_from_pointmap(Xc, Yc, zz2, W_, H_)
    err = abs(f_est - f_true)/f_true
    print(f' {f_true:8.1f}   {f_est:12.6f}   {err:.3e}')
    assert err < 1e-12, f'焦距应精确可解，实测相对误差 {err:.3e}'
print('\\n✓ 焦距**精确**可解（1e-16 量级）—— 因为 u - cx = f·X/Z 是一个超定线性方程')
print('  所以「预测点图」这个输出形式把标定这一步也吸收进了网络。')
print('  pose-free / calibration-free 的真实含义：内参被**输出**而不是被**输入**。')

# 代价：过参数化
print('\\n过参数化的账：')
print(' 分辨率      点图自由度      深度+焦距      冗余')
for hh, ww in [(48, 64), (192, 256), (384, 512)]:
    dof = 3*hh*ww; need = hh*ww + 1
    print(f' {hh}x{ww:<5d} {dof:12,d}  {need:12,d}   {dof/need:.4f}×')
assert abs(3*384*512/(384*512+1) - 3.0) < 1e-4
print('\\n✓ 恰好 3.00× —— 而冗余的后果是「一致性必须靠网络自己保证」')

# 演示：一个不自洽的点图
print('\\n射线一致性检验（不需要真值）：')
zz3 = rg.uniform(2.0, 10.0, (H_, W_))
vv, uu = np.mgrid[0:H_, 0:W_]
Xg = (uu - W_/2)*zz3/600.0; Yg = (vv - H_/2)*zz3/600.0
def ray_residual(Xc, Yc, Zc, W, H):
    '''先解出 f，再把每个点投影回它自己的射线上，返回残差（像素）。'''
    f_ = focal_from_pointmap(Xc, Yc, Zc, W, H)
    hh, ww = Zc.shape
    vv_, uu_ = np.mgrid[0:hh, 0:ww]
    u_pred = W/2 + f_*Xc/Zc; v_pred = H/2 + f_*Yc/Zc
    return float(np.sqrt(np.mean((u_pred-uu_)**2 + (v_pred-vv_)**2))), f_
r_ok, f_ok = ray_residual(Xg, Yg, zz3, W_, H_)
print(f'  自洽的点图: 残差 {r_ok:.3e} px   反解 f = {f_ok:.4f}')
for amp in [0.001, 0.01, 0.05]:
    Xb = Xg + rg.normal(0, amp, Xg.shape)          # 破坏 X 分量（射线不再对）
    r_bad, f_bad = ray_residual(Xb, Yg, zz3, W_, H_)
    print(f'  X 加 {amp:.3f} 的噪声: 残差 {r_bad:6.3f} px   反解 f = {f_bad:.4f}')
assert r_ok < 1e-9, '自洽点图的射线残差应为 0'
_rb, _ = ray_residual(Xg + rg.normal(0, 0.01, Xg.shape), Yg, zz3, W_, H_)
assert _rb > 0.5, '破坏一致性后残差应明显'
print('\\n✓ 射线一致性检验**不需要真值**，所以它是前馈方法最便宜的自检。')
print('  而深度图的冗余是 1.00×，它**不可能**输出一个不自洽的结果 ——')
print('  射线一致性是被表示本身构造保证的（与 C74 模块 02 的 RSSᵀRᵀ 是同一手法）。')"""),

md("""## 5 · 全局对齐：它<em>就是</em>一次束调整"""),

code("""def make_pairwise_problem(N=5, npt=60, seed=0, mode='both'):
    '''N 张图两两配对，每对给出点图（含自己的未知尺度）。
    mode='both'  -> 每对给**两张**点图（真实的 DUSt3R）
    mode='ref'   -> 只给参考视图的点图（我第一版的写法，有 bug）'''
    r = np.random.default_rng(seed)
    Xw = r.normal(0, 1, (npt, 3)) + np.array([0, 0, 5.0])
    poses = []
    for i in range(N):
        a = np.deg2rad(15.0*i)
        R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        poses.append((R, -R @ np.array([3*np.sin(a), 0.1*r.normal(), 5-5*np.cos(a)])))
    pairs = [(i, j) for i in range(N) for j in range(i+1, N)]
    scales = np.exp(r.normal(0, 0.4, len(pairs)))
    data = {}
    for k, (i, j) in enumerate(pairs):
        d = {}
        for who in ([i, j] if mode == 'both' else [i]):
            R, t = poses[who]
            d[who] = scales[k]*((R @ Xw.T).T + t)
        data[(i, j)] = d
    return Xw, poses, pairs, scales, data

def global_align_rank(N=5, npt=60, mode='both', seed=0, gap_thresh=1e6):
    '''返回 (秩亏, 参数数, 观测数, 谱间隙, 完全未被约束的相机列表)。'''
    Xw, poses, pairs, scales, data = make_pairwise_problem(N, npt, seed, mode)
    npar = 6*N + len(pairs) + 3*npt
    def resid(p):
        ps = [(rodrigues(p[6*i:6*i+3]), p[6*i+3:6*i+6]) for i in range(N)]
        sc = np.exp(p[6*N:6*N+len(pairs)])
        X = p[6*N+len(pairs):].reshape(npt, 3)
        out = []
        for k, (i, j) in enumerate(pairs):
            for who, tgt in data[(i, j)].items():
                R, t = ps[who]
                out.append((sc[k]*((R @ X.T).T + t) - tgt).ravel())
        return np.concatenate(out)
    p0 = np.concatenate([np.concatenate([R_to_w(R), t]) for R, t in poses]
                        + [np.log(scales)] + [Xw.ravel()])
    r0 = resid(p0)
    assert np.linalg.norm(r0) < 1e-8, f'真解处残差应为 0，实测 {np.linalg.norm(r0):.2e}'
    eps = 1e-6
    J = np.zeros((len(r0), npar))
    for m in range(npar):
        a = p0.copy(); a[m] += eps; b = p0.copy(); b[m] -= eps
        J[:, m] = (resid(a) - resid(b))/(2*eps)
    Hm = J.T @ J
    sv = np.linalg.svd(Hm, compute_uv=False)
    rt = sv[:-1]/np.maximum(sv[1:], 1e-300)
    k = int(np.argmax(rt))
    rd = npar - (k+1) if rt[k] >= gap_thresh else 0
    # 哪些相机的参数完全没出现在残差里
    cn = np.linalg.norm(J, axis=0)
    dead = np.where(cn < cn.max()*1e-12)[0]
    dead_cams = sorted({int(d)//6 for d in dead if d < 6*N})
    return rd, npar, len(r0), float(rt[k]), dead_cams

print(' 构造方式                    秩亏   参数   观测   谱间隙     未被约束的相机')
for mode, tag in [('ref', '只给参考视图的点图（bug）'), ('both', '每对给两张点图（真实）')]:
    rd, npar, nobs, gap, dead = global_align_rank(5, 60, mode)
    print(f' {tag:26s} {rd:5d} {npar:6d} {nobs:6d}  {gap:.2e}   {dead}')

_rd_ref = global_align_rank(5, 60, 'ref')[0]
_rd_both, _npar, _nobs, _gap, _dead = global_align_rank(5, 60, 'both')
assert _rd_ref == 13, f'错的构造应给出 13，实测 {_rd_ref}'
assert _rd_both == 7, f'正确构造应给出 7，实测 {_rd_both}'
assert global_align_rank(5, 60, 'ref')[4] == [4], '未被约束的应是相机 4'
print(f'\\n✓ 正确构造的秩亏恰好 **7** —— 与模块 01 的束调整完全相同（世界的相似变换）')
print(f'  区别只在残差是 3D 点差而不是 2D 重投影差。')
print(f'\\n⚠ 而我第一版写成了 13。多出来的 6 立刻定位了 bug：')
print(f'  残差里只出现每对的**参考**相机 i，而相机 4 从来不是任何一对的参考（i<j）。')
print(f'  雅可比里它那 6 列的范数是 0 —— 工具直接指出了是哪个变量漏了。')
print(f'  所以「数一数零空间的维数」是检查「残差是不是漏了变量」最快的办法。')

# 秩亏与规模无关
print('\\n秩亏与场景规模无关（它是群的维数）：')
for N_, npt_ in [(2, 40), (3, 40), (4, 30), (5, 60), (6, 25)]:
    rd, npar, nobs, gap, _ = global_align_rank(N_, npt_, 'both')
    pr = N_*(N_-1)//2
    print(f'  N={N_} ({pr:2d} 对) npt={npt_}: 参数 {npar:4d}  观测 {nobs:5d}  '
          f'冗余 {nobs-npar:+6d}  秩亏 {rd}')
    assert rd == 7
print('\\n✓ N≥2 时观测就远多于未知量。每对的尺度靠「同一批 3D 点必须同时解释两张点图」定下来：')
print('  单看一对，那一对的尺度与全局尺度不可分（合并成 1 个自由度，属于那 7 个）；')
print('  两对共享同一批点时，它们的**相对**尺度就被绑定了 —— 这是全局对齐的核心机制。')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 对齐协议的两个维度

实现 `my_evaluate(pred_disp, z_gt, domain, dof)`，返回
`(视差域相对 RMSE, AbsRel 中位, δ<1.25, RMSE-log)`。

- `domain='disparity'`：在视差域拟合 `pred_disp → 1/z_gt`；
- `domain='depth'`：先把 `pred_disp` 取倒数变成「原始深度」，在深度域拟合到 `z_gt`；
- `dof=1` 只拟合尺度（$\\min_a\\Vert ap-g\\Vert^2$），`dof=2` 拟合尺度+位移。

所有取倒数处都要 `np.clip(·, 1e-6, None)`。"""),

code("""def my_evaluate(pred_disp, z_gt, domain, dof):
    '''返回 (视差域 relRMSE, AbsRel 中位, delta<1.25, RMSE-log)。'''
    # TODO: 1) disp_gt = 1/z_gt
    #       2) domain=='disparity': al = fit(pred_disp -> disp_gt); zp = 1/clip(al)
    #          domain=='depth'    : z_raw = 1/clip(pred_disp); zp = clip(fit(z_raw -> z_gt))
    #                               al = 1/clip(zp)
    #       3) rel = sqrt(mean((al-disp_gt)²)/mean(disp_gt²))
    #       4) 返回 (rel,) + metrics(zp, z_gt)
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_rg1 = np.random.default_rng(0)
_zg = _rg1.uniform(1.0, 20.0, 4000); _dg = 1.0/_zg
_p_aff = 3.7*_dg + 0.42 + _rg1.normal(0, 0.002, len(_zg))    # 视差域仿射完美
_p_z = 2.3*_zg + 1.1 + _rg1.normal(0, 0.01, len(_zg))        # 深度域仿射完美
_p_from_z = 1.0/np.clip(_p_z, 1e-6, None)

# ① 与参考实现一致
for _d in ['disparity', 'depth']:
    for _k in [1, 2]:
        _a = my_evaluate(_p_aff, _zg, _d, _k)
        _b = evaluate(_p_aff, _zg, _d, _k)
        assert len(_a) == 4
        assert all(abs(x-y) < 1e-9 for x, y in zip(_a, _b)), f'{_d},{_k} 与参考不符'

# ② 视差域仿射完美的预测器：只有「视差域+仿射」能还原
_R = {(_d, _k): my_evaluate(_p_aff, _zg, _d, _k)[1]
      for _d in ['disparity', 'depth'] for _k in [1, 2]}
_best = _R[('disparity', 2)]
assert _best < 0.01, f'视差域+仿射应 <0.01，实测 {_best:.5f}'
for _k2, _v in _R.items():
    if _k2 != ('disparity', 2):
        assert _v > 10*_best, f'{_k2} 应差 10 倍以上：{_v:.5f} vs {_best:.5f}'

# ③ **对称性**：深度域仿射完美的预测器，最好的是「深度域+仿射」
_R2 = {(_d, _k): my_evaluate(_p_from_z, _zg, _d, _k)[1]
       for _d in ['disparity', 'depth'] for _k in [1, 2]}
assert _R2[('depth', 2)] < 0.01, f'深度域+仿射应还原它，实测 {_R2[("depth",2)]:.6f}'
assert _R2[('disparity', 2)] > 10*_R2[('depth', 2)], '换域应差 10 倍以上'

# ④ b=0 时两种自由度等价
_p_nob = 3.7*_dg + _rg1.normal(0, 0.002, len(_zg))
_e1 = my_evaluate(_p_nob, _zg, 'disparity', 1)[0]
_e2 = my_evaluate(_p_nob, _zg, 'disparity', 2)[0]
assert abs(_e1-_e2)/_e2 < 0.15, f'b=0 时应几乎等价：{_e1:.5f} vs {_e2:.5f}'

# ⑤ δ<1.25 在 [0,1] 内，且完美预测器在正确口径下应为 1.0
assert 0 <= _R[('disparity', 2)] and my_evaluate(_p_aff, _zg, 'disparity', 2)[2] > 0.999
# ⑥ 无效值被 clip 掉而不是抛错
_p_neg = _dg - 5.0
_ = my_evaluate(_p_neg, _zg, 'disparity', 2)
print(f'✓ 练习 1 通过：视差域仿射完美 -> 最佳口径 AbsRel {_best:.5f}，'
      f'其余 ≥{min(v for k,v in _R.items() if k!=("disparity",2)):.5f}')
print(f'  对称性成立：深度域仿射完美 -> 深度域+仿射 {_R2[("depth",2)]:.6f}，'
      f'视差域+仿射 {_R2[("disparity",2)]:.6f}')"""),

md("""### 📖 参考答案 1"""),

code("""def my_evaluate(pred_disp, z_gt, domain, dof):
    disp_gt = 1.0/np.asarray(z_gt, float)
    if domain == 'disparity':
        al = fit_align(pred_disp, disp_gt, dof)
        zp = 1.0/np.clip(al, 1e-6, None)
    elif domain == 'depth':
        z_raw = 1.0/np.clip(np.asarray(pred_disp, float), 1e-6, None)
        zp = np.clip(fit_align(z_raw, z_gt, dof), 1e-6, None)
        al = 1.0/np.clip(zp, 1e-6, None)
    else:
        raise ValueError(domain)
    rel = float(np.sqrt(np.mean((al - disp_gt)**2)/np.mean(disp_gt**2)))
    return (rel,) + metrics(zp, z_gt)

print('参考答案 1 已定义')
print('要点一：自测 ③ 的**对称性**是这道题的核心。')
print('       规则不是「视差域更好」，而是「对齐域必须与模型的不变性所在的域一致」。')
print('       所以评测协议**不能独立于模型来定** —— 这一点常被忽略。')
print('要点二：clip 不是装饰。对齐后的视差可能为负或零，那时 1/al 会给出负深度或 inf。')
print('       真实评测里这些像素通常被直接剔除，而剔除比例本身就该报出来。')
print('要点三：为什么 MiDaS 类模型报「仿射不变」而不是「尺度不变」——')
print('       混合数据集的标注定义不一致（有的米、有的视差、有的只有相对关系），')
print('       所以必须用对「尺度 + 位移」都不变的损失。')
print('       而选视差而不是深度是因为 z→∞ 时视差→0，有界、可回归。')"""),

md("""### ✏️ 练习 2 · 逐图对齐 vs 全局对齐

实现 `my_protocol(P, dd, zz, mode)`：`P` 是 `(n_img, per)` 的预测视差，
`dd`/`zz` 是同形状的真值视差/深度。返回每张图的 AbsRel 中位数（长度 `n_img` 的数组）。

- `'per-image-affine'`：每张图单独做二自由度拟合；
- `'per-image-scale'`：每张图单独做一自由度拟合；
- `'global-affine'`：把**所有**图拉平成一个向量拟合一组 $(a,b)$，再用它对每张图。"""),

code("""def my_protocol(P, dd, zz, mode):
    '''返回长度 n_img 的 AbsRel 中位数数组。'''
    # TODO: mode=='global-affine' 时先在 P.ravel() -> dd.ravel() 上拟合一组 (a,b)
    #       然后逐图：按 mode 得到对齐后的视差 al
    #                 zp = 1/clip(al, 1e-6, None)
    #                 记录 median(|zp - zz[i]|/zz[i])
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_rg2 = np.random.default_rng(5)
_ni, _pe = 120, 40
_zz = _rg2.uniform(1.0, 20.0, (_ni, _pe)); _dd = 1.0/_zz
_ai = _rg2.uniform(2.0, 6.0, (_ni, 1)); _bi = _rg2.uniform(-0.2, 0.8, (_ni, 1))
_P = _ai*_dd + _bi + _rg2.normal(0, 0.002, (_ni, _pe))

_res = {m: my_protocol(_P, _dd, _zz, m)
        for m in ['per-image-affine', 'per-image-scale', 'global-affine']}
for _m, _v in _res.items():
    assert _v.shape == (_ni,), f'{_m}: 形状 {_v.shape}'
    assert np.all(_v >= 0)

# ① 逐图仿射应还原到 <1%
_pa = float(np.median(_res['per-image-affine']))
assert _pa < 0.01, f'逐图仿射应 <0.01，实测 {_pa:.5f}'
# ② 逐图尺度差很多（因为每张图有自己的 b_i）
_ps = float(np.median(_res['per-image-scale']))
assert _ps > 20*_pa, f'逐图尺度应差 20 倍以上：{_ps:.5f} vs {_pa:.5f}'
# ③ 全局对齐最差（因为每张图有自己的 a_i, b_i）
_ga = float(np.median(_res['global-affine']))
assert _ga > 20*_pa, f'全局对齐应差 20 倍以上：{_ga:.5f} vs {_pa:.5f}'
# ④ 而如果所有图**共享**同一组 (a,b)，全局对齐就不再吃亏
_Pshared = 3.7*_dd + 0.42 + _rg2.normal(0, 0.002, (_ni, _pe))
_r2 = {m: float(np.median(my_protocol(_Pshared, _dd, _zz, m)))
       for m in ['per-image-affine', 'global-affine']}
assert _r2['global-affine'] < 5*_r2['per-image-affine'], \\
    f'共享参数时全局对齐不该吃亏：{_r2}'
# ⑤ P90 也要合理
assert np.percentile(_res['per-image-affine'], 90) < 0.02
print(f'✓ 练习 2 通过：逐图仿射 {_pa:.5f} / 逐图尺度 {_ps:.5f} / 全局仿射 {_ga:.5f}')
print(f'  （逐图仿射 vs 全局仿射差 {_ga/_pa:.0f} 倍）')
print(f'  而当所有图共享同一组 (a,b) 时，全局对齐 {_r2["global-affine"]:.5f} '
      f'≈ 逐图 {_r2["per-image-affine"]:.5f} —— 说明差距来自「每图尺度不同」这个事实')"""),

md("""### 📖 参考答案 2"""),

code("""def my_protocol(P, dd, zz, mode):
    P = np.asarray(P, float); dd = np.asarray(dd, float); zz = np.asarray(zz, float)
    n_img, per = P.shape
    if mode == 'global-affine':
        A = np.stack([P.ravel(), np.ones(P.size)], 1)
        c, *_ = np.linalg.lstsq(A, dd.ravel(), rcond=None)
    out = []
    for i in range(n_img):
        if mode == 'per-image-affine':
            al = fit_align(P[i], dd[i], 2)
        elif mode == 'per-image-scale':
            al = fit_align(P[i], dd[i], 1)
        elif mode == 'global-affine':
            al = np.stack([P[i], np.ones(per)], 1) @ c
        else:
            raise ValueError(mode)
        zp = 1.0/np.clip(al, 1e-6, None)
        out.append(float(np.median(np.abs(zp - zz[i])/zz[i])))
    return np.array(out)

print('参考答案 2 已定义')
print('要点：自测 ④ 说明了差距的来源。')
print('  当每张图有自己的 (a_i, b_i) 时，全局对齐差 ~100 倍；')
print('  而当所有图共享同一组 (a,b) 时，全局对齐几乎不吃亏。')
print('  所以「全局对齐的分数低」不一定说明模型差 —— 它可能只是说明')
print('  「这个模型的尺度在不同场景之间不一致」，而那是一个**不同的**性质。')
print('  两种协议回答的是两个不同的问题，而论文里常常只报一个。')"""),

md("""### ✏️ 练习 3 · 从点图反解焦距，并做射线一致性检验

实现 `my_focal(Xc, Yc, Zc, W, H)`：最小二乘反解焦距（主点假设在图像中心）。
再实现 `my_ray_residual(Xc, Yc, Zc, W, H)`：先解出 $f$，
再把每个点按 $u = W/2 + fX/Z$ 投影回去，返回 (RMS 像素残差, 解出的 $f$)。"""),

code("""def my_focal(Xc, Yc, Zc, W, H):
    '''最小二乘反解焦距。'''
    # TODO: hh, ww = Zc.shape ; vv, uu = np.mgrid[0:hh, 0:ww]
    #       a = concat([(Xc/Zc).ravel(), (Yc/Zc).ravel()])
    #       b = concat([(uu - W/2).ravel(), (vv - H/2).ravel()])
    #       返回 (a @ b)/(a @ a)
    raise NotImplementedError

def my_ray_residual(Xc, Yc, Zc, W, H):
    '''返回 (RMS 像素残差, 解出的 f)。'''
    # TODO: f = my_focal(...) ; u_pred = W/2 + f*Xc/Zc ; v_pred = H/2 + f*Yc/Zc
    #       残差 = sqrt(mean((u_pred-uu)² + (v_pred-vv)²))
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_rg3 = np.random.default_rng(3)
_h, _w = 48, 64
_vv, _uu = np.mgrid[0:_h, 0:_w]

# ① 精确可解（4 个焦距）
for _ft in [300.0, 600.0, 1200.0, 2400.0]:
    _z = _rg3.uniform(2.0, 10.0, (_h, _w))
    _X = (_uu - _w/2)*_z/_ft; _Y = (_vv - _h/2)*_z/_ft
    _fe = my_focal(_X, _Y, _z, _w, _h)
    assert abs(_fe - _ft)/_ft < 1e-12, f'f={_ft}: 相对误差 {abs(_fe-_ft)/_ft:.3e}'

# ② 与参考实现一致
_z = _rg3.uniform(2.0, 10.0, (_h, _w))
_X = (_uu - _w/2)*_z/600.0; _Y = (_vv - _h/2)*_z/600.0
assert abs(my_focal(_X, _Y, _z, _w, _h) - focal_from_pointmap(_X, _Y, _z, _w, _h)) < 1e-9

# ③ 自洽点图的射线残差为 0
_r, _f = my_ray_residual(_X, _Y, _z, _w, _h)
assert _r < 1e-9, f'自洽点图的射线残差应为 0，实测 {_r:.3e}'
assert abs(_f - 600.0) < 1e-9

# ④ 破坏一致性后残差明显，且随破坏幅度单调增长
_prev = 0.0
for _amp in [0.001, 0.01, 0.05]:
    _Xb = _X + np.random.default_rng(7).normal(0, _amp, _X.shape)
    _rb, _fb = my_ray_residual(_Xb, _Y, _z, _w, _h)
    assert _rb > _prev, f'残差应随破坏幅度单调增：{_prev:.4f} -> {_rb:.4f}'
    _prev = _rb
assert _prev > 0.5, f'0.05 的破坏应给出 >0.5 px 的残差，实测 {_prev:.4f}'

# ⑤ 深度缩放不改变反解的 f（因为 X/Z 不变）
for _s in [0.1, 10.0]:
    assert abs(my_focal(_X*_s, _Y*_s, _z*_s, _w, _h) - 600.0) < 1e-9, \\
        '整体缩放点图不该改变 f（尺度不可观测，但 f 可观测）'

# ⑥ 而只缩放 X（不缩放 Z）会改变 f —— 说明它真的在测 X/Z 的斜率
assert abs(my_focal(_X*2.0, _Y*2.0, _z, _w, _h) - 300.0) < 1e-9
print(f'✓ 练习 3 通过：4 个焦距全部精确可解（<1e-12）；自洽点图残差 {_r:.1e} px；'
      f'破坏 0.05 后残差 {_prev:.3f} px')
print(f'  整体缩放点图不改变 f（尺度不可观测而 f 可观测）；只缩放 XY 时 f 减半 ✓')"""),

md("""### 📖 参考答案 3"""),

code("""def my_focal(Xc, Yc, Zc, W, H):
    hh, ww = Zc.shape
    vv, uu = np.mgrid[0:hh, 0:ww]
    a = np.concatenate([(Xc/Zc).ravel(), (Yc/Zc).ravel()])
    b = np.concatenate([(uu - W/2).ravel(), (vv - H/2).ravel()])
    return float((a @ b)/(a @ a))

def my_ray_residual(Xc, Yc, Zc, W, H):
    f = my_focal(Xc, Yc, Zc, W, H)
    hh, ww = Zc.shape
    vv, uu = np.mgrid[0:hh, 0:ww]
    u_pred = W/2 + f*Xc/Zc
    v_pred = H/2 + f*Yc/Zc
    return float(np.sqrt(np.mean((u_pred-uu)**2 + (v_pred-vv)**2))), f

print('参考答案 3 已定义')
print('要点一：自测 ⑤⑥ 一起说明了这个反解在测什么 ——')
print('       它测的是 X/Z 对 (u-cx) 的斜率。所以整体缩放点图（X,Y,Z 一起乘 s）')
print('       不改变 f（尺度不可观测），而只缩放 XY 会让 f 反比变化。')
print('要点二：射线一致性检验**不需要真值**，所以它是前馈方法最便宜的自检。')
print('       而它能查的正是那 3.00× 过参数化带来的风险：网络可以输出一个')
print('       「几何上不自洽」的张量，而那在可视化上不明显。')
print('要点三：深度图的冗余是 1.00×，所以它**不可能**不自洽 ——')
print('       射线一致性被表示本身构造保证了。')
print('       这与 C74 模块 02 的「把正定性编码进 RSSᵀRᵀ」是同一个手法，')
print('       只是点图做了**相反**的选择：放弃构造保证，换取内参的自由。')"""),

md("""### ✏️ 练习 4 · 数出全局对齐的零空间

实现 `my_align_rank(N, npt, mode, seed, gap_thresh)`：
构造两两点图问题 → 算数值雅可比 → 返回 `(秩亏, 完全未被约束的相机列表)`。

判秩用**最大谱间隙**，且要求间隙 > `gap_thresh`（否则报 0）；
「完全未被约束」= 雅可比里该列的范数近似为 0。"""),

code("""def my_align_rank(N=5, npt=60, mode='both', seed=0, gap_thresh=1e6):
    '''返回 (秩亏, 未被约束的相机编号列表)。'''
    # TODO: 1) Xw, poses, pairs, scales, data = make_pairwise_problem(N, npt, seed, mode)
    #       2) 参数打包顺序：[各相机的 (w,t)] + [log(各对尺度)] + [点坐标]
    #          残差：对每对 (i,j) 的每张点图 who：sc[k]*(R_who X + t_who) - data[(i,j)][who]
    #       3) 数值雅可比 -> H = JᵀJ -> 最大谱间隙判秩（间隙 < gap_thresh 时返回 0）
    #       4) 未被约束的相机：J 的列范数 < max*1e-12，且列号 < 6N
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
# ① 正确构造：秩亏 7，无未约束相机
_rd, _dead = my_align_rank(5, 60, 'both')
assert _rd == 7, f'正确构造的秩亏应为 7，实测 {_rd}'
assert _dead == [], f'不该有未约束的相机，实测 {_dead}'

# ② 与参考实现一致
for _m in ['both', 'ref']:
    assert my_align_rank(5, 60, _m)[0] == global_align_rank(5, 60, _m)[0]

# ③ 错的构造：秩亏 13，且能定位到相机 4
_rd_b, _dead_b = my_align_rank(5, 60, 'ref')
assert _rd_b == 13, f'只用参考视图时秩亏应为 13，实测 {_rd_b}'
assert _dead_b == [4], f'未约束的应是相机 4，实测 {_dead_b}'
assert _rd_b - _rd == 6, '多出来的正好是一个相机的 6 个自由度'

# ④ 秩亏与规模无关（群的维数）
for _N, _npt in [(2, 40), (3, 40), (4, 30), (6, 25)]:
    _r, _d = my_align_rank(_N, _npt, 'both')
    assert _r == 7, f'N={_N} npt={_npt}: 秩亏 {_r}'
    assert _d == []

# ⑤ 错的构造下，未约束的相机总是编号最大的那个（它永远不是参考）
for _N in [3, 4, 6]:
    _r, _d = my_align_rank(_N, 30, 'ref')
    assert _d == [_N-1], f'N={_N}: 未约束的应是相机 {_N-1}，实测 {_d}'
    assert _r == 13 if _N == 5 else _r == 7 + 6

# ⑥ 间隙阈值：设得极大时应报 0（满秩），因为找不到「悬崖」
assert my_align_rank(5, 60, 'both', gap_thresh=1e30)[0] == 0
print(f'✓ 练习 4 通过：正确构造 秩亏 {_rd}；错的构造 秩亏 {_rd_b} 且定位到相机 {_dead_b}')
print(f'  多出来的 {_rd_b-_rd} 正好是一个相机的 6 个自由度')
print(f'  N=2/3/4/6 时秩亏恒为 7（群的维数，与规模无关）')"""),

md("""### 📖 参考答案 4"""),

code("""def my_align_rank(N=5, npt=60, mode='both', seed=0, gap_thresh=1e6):
    Xw, poses, pairs, scales, data = make_pairwise_problem(N, npt, seed, mode)
    npar = 6*N + len(pairs) + 3*npt
    def resid(p):
        ps = [(rodrigues(p[6*i:6*i+3]), p[6*i+3:6*i+6]) for i in range(N)]
        sc = np.exp(p[6*N:6*N+len(pairs)])
        X = p[6*N+len(pairs):].reshape(npt, 3)
        out = []
        for k, (i, j) in enumerate(pairs):
            for who, tgt in data[(i, j)].items():
                R, t = ps[who]
                out.append((sc[k]*((R @ X.T).T + t) - tgt).ravel())
        return np.concatenate(out)
    p0 = np.concatenate([np.concatenate([R_to_w(R), t]) for R, t in poses]
                        + [np.log(scales)] + [Xw.ravel()])
    r0 = resid(p0)
    eps = 1e-6
    J = np.zeros((len(r0), npar))
    for m in range(npar):
        a = p0.copy(); a[m] += eps; b = p0.copy(); b[m] -= eps
        J[:, m] = (resid(a) - resid(b))/(2*eps)
    sv = np.linalg.svd(J.T @ J, compute_uv=False)
    rt = sv[:-1]/np.maximum(sv[1:], 1e-300)
    k = int(np.argmax(rt))
    rd = npar - (k+1) if rt[k] >= gap_thresh else 0
    cn = np.linalg.norm(J, axis=0)
    dead = sorted({int(d)//6 for d in np.where(cn < cn.max()*1e-12)[0] if d < 6*N})
    return rd, dead

print('参考答案 4 已定义')
print('要点一：这道题的价值在自测 ③ —— 一个建模 bug 被「秩亏多了 6」直接暴露，')
print('       而列范数进一步定位到了具体是哪个相机。')
print('       所以数零空间维数比读代码快，而且给出的是「缺了几个自由度」这个精确信息。')
print('要点二：秩亏 7 与模块 01 的束调整完全相同 —— 同一个 gauge（世界的相似变换）。')
print('       所以模块 01 的全套结论直接适用：需要固定或投影掉 gauge、')
print('       点块可用 Schur 补、协方差依赖 gauge 的选择。')
print('要点三：所以 pose-free 方法并没有取消 SfM，它换了 SfM 的**位置**：')
print('       从「必须先做对，做不对整条链就断」变成「用来收尾，且初值很好」。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 单目深度：MiDaS / Depth Anything ----
import torch
model = torch.hub.load("intel-isl/MiDaS", "DPT_Large")      # 输出**仿射不变的视差**
prediction = model(input_batch)      # 越大 = 越近；没有单位
# 评测时必须做逐图仿射对齐（练习 1/2）：
#   A = np.stack([pred.ravel(), np.ones(pred.size)], 1)
#   a, b = np.linalg.lstsq(A, gt_disp.ravel(), rcond=None)[0]
# 而 Depth Anything V2 有一个 "metric" 分支（室内/室外分别微调），
# 它直接输出米 —— 但那个米来自训练分布，跨域用会系统性地缩放错（第 1 节）

# ---- 点图：DUSt3R / MASt3R ----
from dust3r.inference import inference
from dust3r.cloud_opt import global_aligner, GlobalAlignerMode
output = inference(pairs, model, device, batch_size=1)
scene = global_aligner(output, device=device, mode=GlobalAlignerMode.PointCloudOptimizer)
loss = scene.compute_global_alignment(init="mst", niter=300, schedule="cosine", lr=0.01)
# compute_global_alignment 就是第 5 节那次「秩亏 7」的优化 ——
# 所以它同样需要固定 gauge（DUSt3R 里是把第一帧设为参考 + 归一化尺度）
focals = scene.get_focals()          # 内参是**输出**（练习 3）
pts3d = scene.get_pts3d()            # 点图
# 自检：把 pts3d 投影回射线看残差（练习 3 的 my_ray_residual）——
# 不需要真值，而它查的正是那 3.00× 冗余带来的风险

# ---- 评测协议要交代的三件事（第 2 节）----
# ① 域：视差 / 深度 / 对数深度
# ② 自由度：1（尺度）/ 2（仿射）/ 0（不对齐）
# ③ 逐图还是全数据集共享
# 缺任何一个，数字都不可比 —— 三者合起来能让同一个模型的 AbsRel 差 100 倍以上
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 相对指标很好但绝对深度差很多 | 对齐口径的三件事 | 三者合起来差 100 倍以上 |
| 换一篇论文的协议数字就变 | **正常** —— 协议不同 | 逐图 vs 全局差 ~100 倍 |
| 报的 AbsRel 很好但 δ<1.25 很低 | 有少数像素错得离谱 | AbsRel 用中位数，尾部完全不影响它 |
| AbsRel 差但 δ<1.25 很高 | 系统性偏置 | 8% 的偏置下 δ<1.25 仍是 1.0000 |
| 换一类场景（室内→航拍）整体缩放错 | 尺度先验的分布偏移 | 绝对尺度不可观测，米来自训练分布 |
| 点图拼不起来 / 三角化发散 | 射线一致性残差 | 点图 3.00× 过参数化，可以不自洽 |
| 全局对齐不收敛或尺度乱漂 | gauge 是否固定 | 秩亏恰好 7，与束调整同一个群 |
| 遮挡区/玻璃处深度「合理但错」 | 无法从单图检测 | 必须用另一个视角或另一个传感器 |"""),
]
