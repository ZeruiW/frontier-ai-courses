# -*- coding: utf-8 -*-
"""C75 模块 05 · 网格化与 3D 重建评测。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① Marching Cubes 的 <strong>256 种情形归约为 15 类</strong>"
                   "（仅旋转是 23 类），而 <strong>120/256 = 46.9% 含面歧义</strong>；"
                   "② TSDF 融合与泊松重建各解决什么、各要求什么；"
                   "③ <strong>Chamfer 距离不是度量</strong>——三角不等式的反例是 $20 > 5+5$；"
                   "④ <strong>CD-L1 对离群点是线性的，CD-L2 是平方的</strong>"
                   "（一个离群点让 L2 涨 293 倍，而 L1 只涨 1.31 倍）；"
                   "⑤ <strong>同一个曲面改采样密度让 CD 变 2.9 倍</strong>，而 F-score 只依赖 $\\tau/s$；"
                   "⑥ accuracy 与 completeness 必须分开报，否则「缺一半」与「多一半」无法区分"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_mesh_eval.ipynb'
                       '（<strong>用立方体的 24 个旋转 + 内外反演算出 15 类，并数出 6 类歧义</strong> / '
                       'Chamfer 的三角不等式反例（手工 + 随机搜索）/ '
                       '<strong>$\\Delta(\\text{L2}) = (d-1)^2/n$ 的理论值与实测精确吻合</strong> / '
                       'F@$\\tau$ 只依赖 $\\tau/s$ 的验证 / 三种「错法」的分解）'),
    ("核心参考", "Lorensen &amp; Cline, <em>Marching Cubes</em>（SIGGRAPH 1987）· "
                 "Chernyaev, <em>Marching Cubes 33</em>（1995，歧义的完整处理）· "
                 "Curless &amp; Levoy, <em>A Volumetric Method for Building Complex Models</em>（SIGGRAPH 1996，TSDF）· "
                 "Kazhdan et al., <em>Poisson Surface Reconstruction</em>（SGP 2006）/ <em>Screened Poisson</em>（TOG 2013）· "
                 "Knapitsch et al., <em>Tanks and Temples</em>（SIGGRAPH 2017，F-score 的口径）· "
                 "Seitz et al., <em>A Comparison and Evaluation of Multi-View Stereo</em>（CVPR 2006，accuracy/completeness 的出处）· "
                 "本课程 <strong>C74</strong> 模块 01（三种深度口径）与模块 02（2DGS）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("pipeline", "从深度图/辐射场到网格：三条路", "".join([
        ASCII("""
   输入形态                    典型路径                           关键要求
   ────────────────────────────────────────────────────────────────────────
   多张深度图（模块 02）  ──>  TSDF 融合 ──> Marching Cubes      需要位姿 + 体素分辨率
   带法向的点云          ──>  泊松重建   ──> 网格                **必须有可靠法向**
   辐射场 / 高斯（C74）  ──>  取深度或密度等值面 ──> MC          需要一个「表面在哪」的定义
        """),
        DUAL(
            "<strong>三条路的分歧点是「表面的定义从哪来」。</strong>"
            "<em>TSDF：表面 = 截断符号距离场的零等值面，而符号来自「相机看得到」这一侧；"
            "泊松：表面 = 一个隐式函数的等值面，而该函数的梯度被拟合到点云法向；"
            "辐射场：<strong>表面没有定义</strong>——必须人为选一个（密度阈值、"
            "或 C74 模块 01 的三种深度口径之一）</em>。",
            "<strong>第三条路的模糊性是 C74 模块 02 第 6 节那个结论的直接后果：</strong>"
            "<em>3DGS 的第三个轴永远压不到 0（$+0.3I$ 挡着），所以「厚度」是假的、法向不明确</em>。"
            "<strong>于是从 3DGS 提网格必然要引入一个额外的约定，而不同的约定给出不同的网格。</strong>"
            "<em>这就是 2DGS 存在的理由——它把法向做成显式参数，"
            "于是第三条路退化成第二条（带法向的点云 → 泊松）</em>。"),
        CALLOUT("warn",
                "<strong>而深度口径的选择在这里有具体后果。</strong>"
                "<em>C74 模块 01 量过：$D_{\\text{raw}} = A\\cdot D_{\\text{norm}}$，"
                "所以未归一化的期望深度<strong>恒定偏小 $(1-A)$ 倍</strong>——"
                "一个 $\\alpha{=}0.9$ 的高斯在 10 m 处给出 9.0 m</em>。"
                "<strong>用 $D_{\\text{raw}}$ 去做 TSDF 融合，整个表面会系统性地"
                "向相机方向偏移，而这在单视角下看不出来</strong>——"
                "<em>只有多视角融合时才表现为「表面糊掉」（各视角的偏移方向不同）</em>。"),
    ])),

    # ============================================================== 2
    ("marching-cubes", "Marching Cubes：256 → 15，而其中 6 类是歧义的", "".join([
        P("Marching Cubes 逐个体素单元处理：8 个角点各有「在内」或「在外」两种状态，"
          "所以有 $2^8 = 256$ 种符号配置。教科书说「只需 15 种模板」——"
          "notebook 把这个归约<strong>算</strong>了一遍："),
        TABLE(["等价关系", "等价类个数"], [
            ["立方体的旋转群（24 个元素）", "<strong>23</strong>"],
            ["旋转 + <strong>内外反演</strong>（$2\\times24 = 48$）",
             "<strong>15</strong>（教科书里的那个数）"],
        ]),
        DUAL(
            "<strong>「15」这个数依赖于把「内外反演」也算成等价。</strong>"
            "<em>而这在几何上是合理的：把所有角点的符号翻转，"
            "得到的等值面是<strong>同一个</strong>曲面，只是内外互换</em>。"
            "<strong>只用旋转的话是 23 类</strong>——"
            "<em>notebook 两个数都算了出来，所以「15」不是一个需要背的数字</em>。",
            "<strong>而更重要的是歧义：</strong>"
            "<em>如果某个<strong>面</strong>上，两个对角的角点同号、另两个反号，"
            "那么这个面上的等值线有<strong>两种</strong>连法</em>。"),
        TABLE(["", "个数", "占比"], [
            ["256 种配置里含<strong>面歧义</strong>的", "<strong>120</strong>",
             "<strong>46.9%</strong>"],
            ["归约到等价类后含歧义的", "<strong>6</strong>", "6/15 = 40%"],
        ]),
        DUAL(
            "<strong>近一半的配置是歧义的，而原始的 Marching Cubes（1987）"
            "对每一类<em>固定</em>选一种连法。</strong>"
            "<em>后果是相邻两个体素可能对<strong>共享的那个面</strong>做出不一致的选择，"
            "于是网格出现<strong>裂缝</strong>（非水密）</em>。"
            "<strong>而这不是罕见情形——46.9% 的配置都有这个风险。</strong>",
            "<strong>修法有两类：</strong>"
            "① <strong>一致的查表</strong>（Marching Cubes 33、"
            "或 asymptotic decider）——"
            "<em>让相邻体素对同一个面必然做出相同的选择，代价是查表更复杂</em>；"
            "② <strong>换成 Dual Contouring / Dual MC</strong>——"
            "<em>在体素的<strong>对偶</strong>网格上生成顶点，"
            "于是「面上怎么连」这个问题不再出现</em>。"
            "<strong>而实践中最常见的第三条路是：不修，然后用一个补洞算法去补。</strong>"
            "<em>它能出水密网格，但补出来的部分不对应任何观测——"
            "所以它会在第 4 节的 completeness 上「白拿分」</em>。"),
    ])),

    # ============================================================== 3
    ("tsdf", "TSDF 融合：占用率恰好是 $12r/L$，而分辨率越高越稀疏", "".join([
        P("TSDF（截断符号距离场）把每个体素存「到最近表面的符号距离」，"
          "但**只存 $\\vert\\text{sdf}\\vert < \\tau$ 的那些**"
          "（$\\tau$ 通常取 3–5 个体素）。"
          "因为表面是 2 维的而体积是 3 维的，所以占用率有一个干净的形式："),
        MATH(r"\text{占用率} \approx \frac{\text{表面积}\times 2\tau}{L^3}"
             r"\;\xrightarrow{\ \text{表面积}\sim 2L^2,\ \tau=3r\ }\;"
             r"\boxed{\frac{12\,r}{L}}"),
        TABLE(["场景边长 $L$", "体素 $r$", "总体素", "占用体素", "<strong>占用率</strong>",
               "$12r/L$"], [
            ["2 m", "0.05 m", "$6.4\\times10^{4}$", "$1.9\\times10^{4}$",
             "<strong>30.00%</strong>", "30.00%"],
            ["2 m", "0.01 m", "$8.0\\times10^{6}$", "$4.8\\times10^{5}$",
             "<strong>6.00%</strong>", "6.00%"],
            ["8 m", "0.01 m", "$5.1\\times10^{8}$", "$7.7\\times10^{6}$",
             "<strong>1.50%</strong>", "1.50%"],
            ["8 m", "0.005 m", "$4.1\\times10^{9}$", "$3.1\\times10^{7}$",
             "<strong>0.75%</strong>", "0.75%"],
        ]),
        DUAL(
            "<strong>关键结论：分辨率翻倍时，总体素数 ×8 而占用体素数只 ×4——"
            "所以占用<em>率</em>减半。</strong>"
            "<em>换句话说：TSDF 在高分辨率下<strong>更</strong>稀疏</em>。"
            "<strong>这就是体素哈希（voxel hashing）能工作的原因</strong>——"
            "<em>8 m 场景、5 mm 体素时只有 0.75% 被占用，"
            "而稠密存要 41 亿个体素（16 GB fp32）、稀疏存只要 3070 万个（0.12 GB）</em>。"
            "<em>与 C73 模块 01 的稀疏点云是同一个道理，只是这里的稀疏性有闭式</em>。",
            "<strong>而 $\\tau$ 的作用不只是省内存——它决定了「能融合多大的观测冲突」。</strong>"
            "<em>两个视角对同一处给出的深度相差 $d$ 时："
            "$d < 2\\tau$ 则两个 SDF 有重叠，被加权平均成一个面；"
            "$d > 2\\tau$ 则它们各自形成一个零等值面 —— <strong>双层墙</strong></em>。"),
        TABLE(["$\\tau$（体素数，$r{=}1$ cm）", "能容纳的深度误差", "超过它会怎样"], [
            ["1", "±1.0 cm", "相差 &gt;2 cm 的两个观测形成两个面"],
            ["<strong>3（常用）</strong>", "±3.0 cm", "相差 &gt;6 cm 时形成双层墙"],
            ["5", "±5.0 cm", "相差 &gt;10 cm 时形成双层墙"],
            ["10", "±10 cm", "容忍度大，但表面被抹厚 —— 细节丢失"],
        ]),
        CALLOUT("warn",
                "<strong>所以 $\\tau$ 是「容忍位姿/深度误差」与「保留细节」之间的直接取舍。</strong>"
                "<em>而模块 01 第 6 节的尺度漂移在这里有具体后果："
                "一条 200 步的轨迹尺度可能漂 12%，"
                "那么在 8 m 处两端的观测相差近 1 m —— 远超任何合理的 $\\tau$</em>。"
                "<strong>「重建出双层墙」几乎总是位姿问题，而不是融合参数问题。</strong>"),
    ])),

    # ============================================================== 4
    ("poisson", "泊松重建：它的全部风险都在法向上", "".join([
        P("泊松重建把「求表面」变成求一个指示函数 $\\chi$，"
          "使它的梯度尽量匹配点云的法向场 $V$："),
        MATH(r"\min_\chi \Vert \nabla\chi - V\Vert^2"
             r"\;\Longleftrightarrow\;"
             r"\nabla\cdot(\nabla\chi) = \nabla\cdot V"
             r"\quad(\text{一个泊松方程})"),
        DUAL(
            "<strong>它的优点是<em>全局</em>求解：一次线性方程解出整个表面，"
            "所以它天然水密、天然平滑、天然能补小洞。</strong>"
            "<em>而这与 Marching Cubes 逐体素独立决策形成对照——"
            "第 2 节那个「相邻体素不一致导致裂缝」的问题在泊松里不存在</em>。",
            "<strong>而它的全部风险都集中在一处：$V$ 必须是可靠的<em>有向</em>法向场。</strong>"
            "<em>而法向估计（PCA、局部平面拟合）给出的是<strong>无向</strong>的方向——"
            "「朝内还是朝外」是另一个问题，通常靠最小生成树传播或视线方向来定</em>。"),
        H3("法向<em>角度</em>误差：影响与尺度成正比"),
        TABLE(["patch 半径 $R$", "法向错 1°", "错 5°", "错 15°", "错 30°"], [
            ["0.05 m", "0.87 mm", "4.37 mm", "13.4 mm", "28.9 mm"],
            ["<strong>0.20 m</strong>", "3.49 mm", "17.5 mm",
             "<strong>53.6 mm</strong>", "<strong>115 mm</strong>"],
        ]),
        P("位置误差 $\\approx R\\tan\\theta$——**与 patch 尺度成正比**。"
          "所以法向误差在小尺度上几乎无害、在大尺度上很致命，"
          "而这正对应「泊松重建出的表面局部干净、整体可能鼓起或塌陷」这个现象。"),
        H3("法向<em>朝向</em>搞错：泊松直接退化"),
        TABLE(["朝反的法向比例", "净通量 $\\langle n\\cdot\\hat r\\rangle$", "后果"], [
            ["0%", "+1.0000", "正常"],
            ["1%", "+0.9800", "局部小洞/凸起"],
            ["5%", "+0.9000", "可见的伪影"],
            ["20%", "+0.6000", "<strong>表面明显失真</strong>"],
            ["<strong>50%</strong>", "<strong>−0.0000</strong>",
             "<strong>梯度场没有净方向，解退化</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>净通量随反向比例<em>线性</em>下降，50% 时归零。</strong>"
                "<em>而通量为 0 意味着指示函数的梯度场没有净方向——"
                "泊松方程的右端项失去了「里外」信息，解不再对应任何闭合表面</em>。"
                "<strong>所以「法向定向」不是一个预处理小步骤，它决定泊松能不能工作。</strong>"
                "<em>而这也解释了为什么 2DGS（C74 模块 02）对几何重建有价值："
                "它的法向是<strong>显式参数</strong>，且朝向由「面向相机」这一侧唯一确定——"
                "于是定向问题被完全绕过</em>。"),
    ])),

    # ============================================================== 5
    ("chamfer-not-metric", "Chamfer 距离不是度量", "".join([
        MATH(r"\mathrm{CD}(A,B) = \frac{1}{|A|}\sum_{a\in A}\min_{b\in B}\Vert a-b\Vert"
             r" + \frac{1}{|B|}\sum_{b\in B}\min_{a\in A}\Vert a-b\Vert"),
        P("它对称、非负、且 $\\mathrm{CD}(A,A)=0$。"
          "**但它不满足三角不等式**，所以它不是度量。最简的反例："),
        TABLE(["集合", "内容"], [
            ["$A$", "$\\{0\\}$"],
            ["$B$", "$\\{0,\\ 10\\}$"],
            ["$C$", "$\\{10\\}$"],
        ]),
        TABLE(["量", "值"], [
            ["$\\mathrm{CD}(A,B)$", "5.0"],
            ["$\\mathrm{CD}(B,C)$", "5.0"],
            ["$\\mathrm{CD}(A,C)$", "<strong>20.0</strong>"],
            ["三角不等式要求", "$20.0 \\le 5.0 + 5.0 = 10.0$"],
            ["结论", "<strong>违反，超出 2 倍</strong>"],
        ]),
        DUAL(
            "<strong>直觉：$B$ 同时「包含」$A$ 和 $C$，所以它到两者都很近；"
            "但 $A$ 与 $C$ 之间没有这种中介。</strong>"
            "<em>notebook 还做了一次随机搜索，在 20 万次里找到更多反例</em>。"
            "<strong>而这个反例的构造方式说明了违反的<em>机制</em>："
            "一个「更完整」的集合可以同时接近两个互相很远的集合。</strong>",
            "<strong>后果很实际：「$\\mathrm{CD}$ 差 0.1」这句话没有传递性。</strong>"
            "<em>如果方法甲比真值差 0.05、方法乙比真值差 0.05，"
            "你<strong>不能</strong>推出甲乙之间差 ≤ 0.1</em>。"
            "<strong>所以 CD 不能用来做「方法之间的距离」，只能用来做「到真值的分数」。</strong>"
            "<em>而这也意味着「在 CD 上做聚类 / 检索 / 三角不等式剪枝」在数学上是不合法的</em>。"),
    ])),

    # ============================================================== 4
    ("cd-variants", "CD-L1 与 CD-L2：一个线性、一个平方", "".join([
        P("论文里两种都在用，而且常常不说明是哪一种。"
          "取真值 = 单位球面 2000 点、预测 = 同一球面 2000 点 + **一个**离群点："),
        TABLE(["离群点距离", "CD-L1", "相对涨幅", "CD-L2", "相对涨幅",
               "理论 $\\Delta(\\text{L2}) = (d-1)^2/n$"], [
            ["（无离群点）", "0.07999", "1.00×", "0.00411", "1.00×", "—"],
            ["2.0", "0.08047", "1.01×", "0.00461", "1.12×", "0.00050"],
            ["5.0", "0.08197", "1.02×", "0.01211", "<strong>2.95×</strong>", "0.00800"],
            ["10.0", "0.08447", "1.06×", "0.04460", "<strong>10.85×</strong>", "0.04048"],
            ["<strong>50.0</strong>", "0.10446", "<strong>1.31×</strong>", "1.20406",
             "<strong>292.96×</strong>", "1.19990"],
        ]),
        DUAL(
            "<strong>一个离群点在 CD-L1 上贡献 $(d-1)/n$（线性），"
            "在 CD-L2 上贡献 $(d-1)^2/n$（平方）。</strong>"
            "<em>最后一列的理论值与实测增量精确吻合："
            "$1.19990$ 对 $1.20406-0.00411 = 1.19995$</em>。"
            "<strong>所以「Chamfer 对离群点敏感」这句话必须说清是哪一种：</strong>"
            "<em>L1 温和（50 倍半径的离群点只让它涨 31%），"
            "L2 灾难（同一个点让它涨 293 倍）</em>。",
            "<strong>而 F-score 对同一个离群点几乎免疫。</strong>"
            "<em>一个离群点（占 0.05%）让 F@0.05 从 0.7100 变到 0.7098——"
            "相对变化 0.03%</em>。"
            "<strong>因为 F-score 是一个<em>计数</em>指标："
            "落在阈值内就算 1、落在外就算 0，距离多远都一样。</strong>"
            "<em>代价是它丢掉了「合格的点有多准」这个信息（第 6 节）</em>。"),
        CALLOUT("danger",
                "<strong>实践含义：报 Chamfer 时必须写清 L1 还是 L2，"
                "而<em>比较</em>两篇论文的 Chamfer 之前必须先确认它们是同一种。</strong>"
                "<em>而如果重建里有任何离群点（几乎必然有——"
                "MVS 的匹配错误、3DGS 的浮物、补洞算法的产物），"
                "那么 L1 与 L2 会给出<strong>完全不同的排名</strong></em>。"),
    ])),

    # ============================================================== 5
    ("sampling", "采样密度会改变 CD，而它与几何无关", "".join([
        P("下面预测与真值是**同一个球面**，只是采样密度不同："),
        TABLE(["真值点数", "预测点数", "CD-L1", "F@0.02", "F@0.05"], [
            ["2000", "200", "<strong>0.17433</strong>", "0.0367", "0.1804"],
            ["2000", "500", "0.12204", "0.0752", "0.3643"],
            ["2000", "2000", "0.07999", "0.1725", "0.7100"],
            ["2000", "5000", "0.06515", "0.2470", "0.8140"],
            ["2000", "8000", "<strong>0.06041</strong>", "0.2654", "0.8280"],
        ]),
        DUAL(
            "<strong>同一个球面，预测点数从 200 到 8000，CD-L1 变了 2.9 倍。</strong>"
            "<em>而几何完全没变</em>。"
            "<strong>所以比较两份重建的 CD 之前<em>必须</em>把它们重采样到同一密度</strong>——"
            "<em>否则比的是采样而不是几何</em>。"
            "<strong>而「网格顶点数」不同的两个方法（比如不同的 MC 分辨率）"
            "天然就有这个问题。</strong>",
            "<strong>F-score 看起来也在变，但它的规律更干净：它只依赖 $\\tau/s$，"
            "其中 $s$ 是点云自身的平均最近邻间距。</strong>"),
        TABLE(["点数", "自身平均最近邻间距 $s$", "F@0.02（固定 $\\tau$）",
               "<strong>F@$s$</strong>", "<strong>F@$2s$</strong>", "<strong>F@$5s$</strong>"], [
            ["200", "0.12614", "0.0067", "<strong>0.5519</strong>", "0.9417", "1.0000"],
            ["500", "0.07970", "0.0410", "<strong>0.5299</strong>", "0.9600", "1.0000"],
            ["2000", "0.03941", "0.1725", "<strong>0.5542</strong>", "0.9470", "1.0000"],
            ["5000", "0.02458", "0.3884", "<strong>0.5180</strong>", "0.9519", "1.0000"],
            ["8000", "0.01967", "<strong>0.5434</strong>", "<strong>0.5322</strong>",
             "0.9506", "1.0000"],
        ]),
        CALLOUT("intuition",
                "<strong>F@$s$ 一列在五个密度下都是 0.52–0.55，F@$2s$ 都是 0.94–0.96，"
                "F@$5s$ 都是 1.0000——完全由 $\\tau/s$ 决定。</strong>"
                "<em>而 F@0.02 那一列从 0.0067 涨到 0.5434（<strong>81 倍</strong>）"
                "——因为固定的 $\\tau$ 相对于 $s$ 的比值在变</em>。"
                "<strong>所以报 F-score 必须同时报 $\\tau$ <em>与</em>采样密度</strong>；"
                "<em>而一个「完美」重建在 $\\tau = s$ 时只有 0.55 分，"
                "这本身说明 $\\tau$ 不能取得太小</em>。"
                "<strong>常见做法：$\\tau$ 取物体尺度的 1%–2%，并把两份点云重采样到同一密度。</strong>"),
    ])),

    # ============================================================== 6
    ("bidirectional", "accuracy 与 completeness 必须分开报", "".join([
        P("CD 与 F-score 都是**双向**量的和/调和平均。"
          "而把两个方向合起来，会让性质完全不同的错误看起来一样："),
        TABLE(["情形", "CD-L1", "<strong>accuracy</strong>（预测→真值）",
               "<strong>completeness</strong>（真值→预测）", "F@0.05"], [
            ["完美（同曲面重采样）", "0.0800", "0.7060", "0.7140", "0.7100"],
            ["<strong>缺一半</strong>（只重建了半球）", "0.3293",
             "<strong>0.6997</strong>", "<strong>0.4685</strong>", "0.5612"],
            ["<strong>多出一半</strong>（多了一层多余结构）", "0.3115",
             "<strong>0.3530</strong>", "<strong>0.7140</strong>", "0.4724"],
        ]),
        DUAL(
            "<strong>「缺一半」与「多出一半」的 CD 几乎相同（0.3293 vs 0.3115），"
            "而它们的含义完全相反。</strong>"
            "<em>缺一半：accuracy 仍是 0.6997（重建出来的部分是对的），"
            "completeness 掉到 0.4685；"
            "多出一半：completeness 仍是 0.7140（真值都被覆盖了），"
            "accuracy 掉到 0.3530</em>。"
            "<strong>只看 CD（或只看 F）无法区分这两种失败。</strong>",
            "<strong>而这两种失败对应完全不同的修法：</strong>"
            "<em>completeness 低 → 观测不足或置信度阈值太严"
            "（模块 02 第 7 节：「标成无效比给一个错的深度好」——"
            "但那会牺牲 completeness）；"
            "accuracy 低 → 有离群点、浮物、或补洞算法编出来的表面（第 2 节）</em>。"
            "<strong>所以 Tanks and Temples 与 DTU 的标准协议都是"
            "「分别报 accuracy 与 completeness，再报 F」</strong>——"
            "<em>而只报 F 的论文丢掉了最有诊断价值的那一半信息</em>。"),
        CALLOUT("intuition",
                "<strong>一个把「双向」用起来的实用技巧：把 accuracy 与 completeness "
                "画成一条随 $\\tau$ 变化的曲线，而不是只报一个 $\\tau$ 处的值。</strong>"
                "<em>两条曲线的<strong>形状</strong>能区分更多情形："
                "accuracy 曲线在小 $\\tau$ 处就很低但很快爬起来 → 有系统性的小偏移（比如深度口径错，"
                "见 C74 模块 01 的 $D_{\\text{raw}}$ vs $D_{\\text{norm}}$）；"
                "accuracy 曲线一直上不去 → 有真正的离群点或浮物</em>。"
                "<strong>而这个区分只从单个 $\\tau$ 的数字上看不出来。</strong>"),
        CALLOUT("paper",
                "<strong>把本模块的五条并成一张检查清单：</strong>"
                "① <strong>报 CD 时写清 L1 还是 L2</strong>（第 4 节：离群点下排名会翻转）；"
                "② <strong>比较前把两份点云重采样到同一密度</strong>（第 5 节：2.9 倍）；"
                "③ <strong>报 F-score 时写清 $\\tau$ 与采样密度</strong>（第 5 节：只依赖 $\\tau/s$）；"
                "④ <strong>accuracy 与 completeness 分开报</strong>（第 6 节）；"
                "⑤ <strong>不要在 CD 上用三角不等式</strong>（第 3 节：它不是度量）。"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 05 · 网格化与 3D 重建评测

本 notebook 把讲解页的六个结论**算**出来（而不是引用）：

1. **Marching Cubes 的 256 种情形归约为 15 类**（仅旋转是 23 类），
   而 **120/256 = 46.9% 含面歧义**（6 个等价类）；
2. TSDF 的占用率恰好是 $12r/L$ —— **分辨率越高越稀疏**；
3. 泊松重建的位置误差 $\\approx R\\tan\\theta$，而**法向定向**搞错会让它退化；
4. **Chamfer 距离不是度量**：三角不等式的反例是 $20 > 5+5$；
5. **CD-L1 对离群点线性、CD-L2 平方**（一个离群点让 L2 涨 293 倍，L1 只涨 1.31 倍）；
6. **同一曲面改采样密度让 CD 变 2.9 倍**，而 F-score 只依赖 $\\tau/s$；
   而 accuracy / completeness 必须分开报。

只用 numpy，CPU，离线。"""),

code("""import numpy as np, itertools, math
print('numpy', np.__version__)

# 立方体的 8 个顶点（0/1 坐标）
VERTS = np.array(list(itertools.product([0, 1], repeat=3)))
print('立方体顶点：'); print(VERTS.T)

def cube_rotations():
    '''立方体的 24 个旋转，以及它们在 8 个顶点上诱导的置换。'''
    mats, perms = [], []
    ctr = np.array([0.5, 0.5, 0.5])
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product([1, -1], repeat=3):
            M = np.zeros((3, 3), int)
            for i, pp in enumerate(perm):
                M[i, pp] = signs[i]
            if round(np.linalg.det(M)) != 1:
                continue
            mats.append(M)
            v2 = np.round((VERTS - ctr) @ M.T + ctr).astype(int)
            perms.append([int(np.where((VERTS == r).all(1))[0][0]) for r in v2])
    return mats, perms

MATS, PERMS = cube_rotations()
print(f'\\n旋转群大小 {len(MATS)}（应为 24）')
assert len(MATS) == 24
# 置换必须是双射
for pp in PERMS:
    assert sorted(pp) == list(range(8))
print('✓ 24 个旋转，每个在顶点上诱导一个置换（都是双射）')""" ),

md("""## 1 · Marching Cubes：256 → 15，而其中 6 类是歧义的"""),

code("""def canonical(code, with_inversion=True):
    '''给定 8 位符号配置（bit i = 顶点 i 是否「在内」），返回等价类的代表元。'''
    bits = [(code >> i) & 1 for i in range(8)]
    cands = []
    for pp in PERMS:
        c = 0
        for i in range(8):
            if bits[pp[i]]:
                c |= (1 << i)
        cands.append(c)
        if with_inversion:
            cands.append(c ^ 0xFF)
    return min(cands)

cls_rot = len({canonical(c, False) for c in range(256)})
cls_full = len({canonical(c, True) for c in range(256)})
print(f' 只用旋转（24 个元素）:            {cls_rot} 个等价类')
print(f' 旋转 + 内外反演（48 个元素）:     {cls_full} 个等价类   <- 教科书里的「15 种」')
assert cls_rot == 23 and cls_full == 15
print('\\n✓ 256 -> 23（仅旋转）-> **15**（加上内外反演）')
print('  「15」这个数依赖把「内外反演」也算成等价 —— 而这在几何上是合理的：')
print('  把所有角点的符号翻转，得到的等值面是**同一个**曲面，只是内外互换。')

# 每一类的大小（轨道大小之和应为 256）
from collections import Counter
orb = Counter(canonical(c, True) for c in range(256))
print(f'\\n15 个等价类的轨道大小: {sorted(orb.values(), reverse=True)}')
assert sum(orb.values()) == 256
print(f'  轨道大小之和 = {sum(orb.values())} ✓')"""),

code("""# 面歧义：某个面上两个**对角**顶点同号、另两个反号
def cube_faces():
    fs = []
    for ax in range(3):
        for val in [0, 1]:
            fs.append([i for i, v in enumerate(VERTS) if v[ax] == val])
    return fs

FACES = cube_faces()
print(f'立方体的 6 个面，每面 4 个顶点：')
for f in FACES:
    print(f'  {f}')

def has_face_ambiguity(code):
    bits = [(code >> i) & 1 for i in range(8)]
    for f in FACES:
        vs = VERTS[f]
        for a in range(4):
            for b in range(a+1, 4):
                if np.sum(np.abs(vs[a] - vs[b])) == 2:        # 面内对角
                    o = [k for k in range(4) if k not in (a, b)]
                    if (bits[f[a]] == bits[f[b]]
                            and bits[f[o[0]]] == bits[f[o[1]]]
                            and bits[f[a]] != bits[f[o[0]]]):
                        return True
    return False

amb = [c for c in range(256) if has_face_ambiguity(c)]
amb_cls = {canonical(c, True) for c in amb}
print(f'\\n 256 种配置里含面歧义的: {len(amb)} 个 ({len(amb)/256:.1%})')
print(f' 归约到等价类后:          {len(amb_cls)} 类 (共 15 类，占 {len(amb_cls)/15:.0%})')
assert len(amb) == 120 and len(amb_cls) == 6
print('\\n✓ 近一半的配置是歧义的，而原始 Marching Cubes（1987）对每一类**固定**选一种连法。')
print('  后果：相邻两个体素可能对**共享的那个面**做出不一致的选择 -> 网格出现裂缝（非水密）。')
print('  而这不是罕见情形 —— 46.9% 的配置都有这个风险。')
print('\\n修法两类：')
print('  ① 一致的查表（Marching Cubes 33 / asymptotic decider）：让相邻体素对同一个面')
print('     必然做出相同的选择，代价是查表更复杂；')
print('  ② 换成 Dual Contouring：在体素的**对偶**网格上生成顶点，')
print('     于是「面上怎么连」这个问题不再出现。')
print('  而实践中最常见的第三条路是：不修，然后用补洞算法补 ——')
print('  它能出水密网格，但补出来的部分不对应任何观测，会在 completeness 上「白拿分」。')"""),

md("""## 2 · TSDF 的占用率恰好是 $12r/L$"""),

code("""def tsdf_occupancy(L, r, tau_voxels=3, area=None):
    '''返回 (总体素数, 占用体素数, 占用率, 理论值 12r/L)。'''
    n_tot = (L/r)**3
    area = 2.0*L**2 if area is None else area          # 一个「房间」的表面积粗估
    tau = tau_voxels*r
    n_occ = area*(2*tau)/r**3
    return n_tot, n_occ, n_occ/n_tot, 2*area/L**2*tau_voxels*r/L

print(' L(m)   r(m)     总体素        占用体素      占用率     12r/L')
for L in [2.0, 8.0]:
    for r in [0.05, 0.02, 0.01, 0.005]:
        nt, no, occ, theo = tsdf_occupancy(L, r)
        print(f' {L:4.1f}  {r:.3f}  {nt:12.3e}  {no:12.3e}  {occ:8.3%}  {12*r/L:8.3%}')
        assert abs(occ - 12*r/L) < 1e-12, f'占用率应恰为 12r/L'
    print()
print('✓ 占用率恰好是 12r/L（因为表面积取了 2L²、τ=3r）')
print('\\n关键结论：分辨率翻倍时总体素 ×8 而占用体素只 ×4 —— 所以占用**率**减半。')
print(' r 翻倍关系：')
for L in [8.0]:
    for r in [0.02, 0.01, 0.005]:
        nt, no, occ, _ = tsdf_occupancy(L, r)
        print(f'  r={r:.3f}: 总 {nt:.3e}  占用 {no:.3e}  率 {occ:.3%}  '
              f'稀疏存 fp32 {no*4/1e9:.3f} GB  稠密存 {nt*4/1e9:.1f} GB')
_, no8, _, _ = tsdf_occupancy(8.0, 0.005)
nt8, _, _, _ = tsdf_occupancy(8.0, 0.005)
print(f'\\n✓ 8 m 场景 / 5 mm 体素：稠密要 {nt8*4/1e9:.1f} GB，稀疏只要 {no8*4/1e9:.3f} GB'
      f'（{nt8/no8:.0f} 倍）')
print('  这就是体素哈希（voxel hashing）能工作的原因 —— 而稀疏性有闭式，不用猜。')
print('  （与 C73 模块 01 的稀疏点云是同一个道理，只是这里可以算出来。）')

print('\\n截断距离 τ 的第二个作用：它决定能融合多大的观测冲突')
print(' τ(体素, r=1cm)   容忍的深度误差   超过它会怎样')
for k in [1, 3, 5, 10]:
    print(f'  {k:5d}          ±{k*1.0:5.1f} cm       '
          f'相差 >{2*k:.0f} cm 的两个观测形成**两个**零等值面（双层墙）')
print('\\n✓ 所以 τ 是「容忍位姿/深度误差」与「保留细节」之间的直接取舍。')
print('  而模块 01 第 8 节的尺度漂移在这里有具体后果：')
print('  200 步的轨迹尺度可能漂 12%，在 8 m 处两端观测相差近 1 m —— 远超任何合理的 τ。')
print('  所以「重建出双层墙」几乎总是位姿问题，而不是融合参数问题。')"""),

md("""## 3 · 泊松重建：风险全在法向上"""),

code("""print('法向**角度**误差 -> 表面位置误差 ≈ R·tan(θ)（R 是 patch 半径）\\n')
print(' R(m)     θ=1°      θ=5°      θ=15°     θ=30°')
for R in [0.02, 0.05, 0.20, 1.00]:
    row = '  '.join(f'{R*np.tan(np.deg2rad(t))*1000:8.2f}' for t in [1, 5, 15, 30])
    print(f' {R:5.2f}  {row}   (mm)')
_e = 0.20*np.tan(np.deg2rad(15))*1000
assert abs(_e - 53.6) < 0.5
print(f'\\n✓ 位置误差与 patch 尺度**成正比**：R=0.20 m、法向错 15° -> {_e:.1f} mm')
print('  所以法向误差在小尺度上几乎无害、在大尺度上很致命 ——')
print('  这正对应「泊松重建出的表面局部干净、整体可能鼓起或塌陷」这个现象。')

# 法向**定向**：净通量随反向比例线性下降
print('\\n法向**朝向**搞错的代价（单位球面上 2000 个点，正确法向 = 径向朝外）：')
rng = np.random.default_rng(0)
n = 2000
v = rng.normal(size=(n, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
print(' 朝反的比例   净通量 <n·r̂>   理论值 1-2f')
FLUX = {}
for frac in [0.0, 0.01, 0.05, 0.2, 0.5, 0.8]:
    nrm = v.copy()
    k = int(round(frac*n))
    idx = rng.choice(n, k, replace=False)
    nrm[idx] *= -1
    flux = float(np.mean(np.sum(nrm*v, 1)))
    FLUX[frac] = flux
    print(f'  {frac:8.0%}     {flux:+11.4f}     {1-2*frac:+.4f}')
    assert abs(flux - (1-2*frac)) < 0.02, f'净通量应为 1-2f，实测 {flux:.4f}'
assert abs(FLUX[0.5]) < 0.02, '50% 反向时净通量应为 0'
print('\\n✓ 净通量 = 1 - 2f，**线性**下降；50% 反向时归零。')
print('  而通量为 0 意味着指示函数的梯度场没有净方向 ——')
print('  泊松方程的右端项失去了「里外」信息，解不再对应任何闭合表面。')
print('\\n所以「法向定向」不是一个预处理小步骤，它决定泊松能不能工作。')
print('  而法向估计（PCA / 局部平面拟合）给出的是**无向**的方向 ——')
print('  「朝内还是朝外」要靠最小生成树传播或视线方向单独确定。')
print('\\n✓ 这也解释了 2DGS（C74 模块 02）对几何重建的价值：')
print('  它的法向是**显式参数**，且朝向由「面向相机」这一侧唯一确定 —— 定向问题被绕过。')"""),

md("""## 4 · Chamfer 距离不是度量"""),

code("""def nn_dists(A, B, chunk=2048):
    '''返回 (A->B 的最近邻距离, B->A 的最近邻距离)。分块以免建整个距离矩阵。'''
    A = np.atleast_2d(np.asarray(A, float)); B = np.atleast_2d(np.asarray(B, float))
    a_min = np.full(len(A), np.inf); b_min = np.full(len(B), np.inf)
    for i in range(0, len(A), chunk):
        blk = A[i:i+chunk]
        d = np.linalg.norm(blk[:, None, :] - B[None, :, :], axis=2)
        a_min[i:i+chunk] = d.min(1)
        np.minimum(b_min, d.min(0), out=b_min)
    return a_min, b_min

def chamfer_l1(A, B):
    a, b = nn_dists(A, B); return float(a.mean() + b.mean())

def chamfer_l2(A, B):
    a, b = nn_dists(A, B); return float((a**2).mean() + (b**2).mean())

# 最简的反例
A = np.array([[0.0]])
B = np.array([[0.0], [10.0]])
C = np.array([[10.0]])
ab, bc, ac = chamfer_l1(A, B), chamfer_l1(B, C), chamfer_l1(A, C)
print('A = {0}   B = {0, 10}   C = {10}')
print(f'  CD(A,B) = {ab:.4f}')
print(f'  CD(B,C) = {bc:.4f}')
print(f'  CD(A,C) = {ac:.4f}')
print(f'  三角不等式要求 CD(A,C) <= CD(A,B) + CD(B,C) = {ab+bc:.4f}')
print(f'  -> {"满足" if ac <= ab+bc+1e-12 else "**违反**"}，超出 {ac-(ab+bc):.4f}')
assert ac > ab + bc + 1e-9, '这个反例必须违反三角不等式'
print(f'\\n✓ {ac:.1f} > {ab:.1f} + {bc:.1f} —— 违反了 2 倍。所以 CD **不是度量**。')
print('  直觉：B 同时「包含」A 与 C，所以它到两者都很近；而 A 与 C 之间没有这种中介。')

# 其他性质仍然成立
print('\\n而它的另外三条性质是成立的：')
_rg = np.random.default_rng(1)
for _ in range(200):
    P = _rg.uniform(0, 10, (_rg.integers(1, 6), 2))
    Q = _rg.uniform(0, 10, (_rg.integers(1, 6), 2))
    assert chamfer_l1(P, Q) >= 0                                  # 非负
    assert abs(chamfer_l1(P, Q) - chamfer_l1(Q, P)) < 1e-12       # 对称
    assert chamfer_l1(P, P) < 1e-12                               # CD(A,A)=0
print('  非负 ✓   对称 ✓   CD(A,A)=0 ✓   而三角不等式 ✗')

# 随机搜索更多反例
cnt = 0; worst = None
for _ in range(200000):
    k = _rg.integers(1, 4, 3)
    P = _rg.uniform(0, 10, (k[0], 1)); Q = _rg.uniform(0, 10, (k[1], 1))
    S = _rg.uniform(0, 10, (k[2], 1))
    pq, qs, ps = chamfer_l1(P, Q), chamfer_l1(Q, S), chamfer_l1(P, S)
    if ps > pq + qs + 1e-9:
        cnt += 1
        if worst is None or ps - (pq+qs) > worst[0]:
            worst = (ps-(pq+qs), P.ravel().copy(), Q.ravel().copy(), S.ravel().copy())
print(f'\\n随机搜索 20 万组（1D、点数≤3）：找到 {cnt} 个反例（{cnt/200000:.2%}）')
print(f'  最严重的一个超出 {worst[0]:.4f}：'
      f'P={np.round(worst[1],3)} Q={np.round(worst[2],3)} S={np.round(worst[3],3)}')
assert cnt > 0
print('\\n后果很实际：「CD 差 0.1」这句话**没有传递性**。')
print('  甲比真值差 0.05、乙比真值差 0.05，**不能**推出甲乙之间差 ≤ 0.1。')
print('  所以 CD 不能用来做「方法之间的距离」，也不能在它上面做聚类/检索/三角不等式剪枝。')"""),

md("""## 5 · CD-L1 线性、CD-L2 平方；而采样密度会改变两者"""),

code("""def sphere(n, seed=0):
    r = np.random.default_rng(seed)
    v = r.normal(size=(n, 3))
    return v/np.linalg.norm(v, axis=1, keepdims=True)

def self_nn(A, chunk=2048):
    '''每个点到**其他**点的最近距离。分块实现。'''
    A = np.asarray(A, float)
    out = np.full(len(A), np.inf)
    for i in range(0, len(A), chunk):
        blk = A[i:i+chunk]
        d = np.linalg.norm(blk[:, None, :] - A[None, :, :], axis=2)
        for r in range(len(blk)):
            d[r, i+r] = np.inf                      # 排除自己
        out[i:i+chunk] = d.min(1)
    return out

def fscore(A, B, tau):
    a, b = nn_dists(A, B)
    prec = float((a < tau).mean())      # accuracy：预测有多少落在真值 tau 内
    rec = float((b < tau).mean())       # completeness：真值有多少被覆盖
    f = 0.0 if prec + rec == 0 else 2*prec*rec/(prec + rec)
    return prec, rec, f

GT = sphere(2000, 0)
BASE = sphere(2000, 1)
c1_0, c2_0 = chamfer_l1(BASE, GT), chamfer_l2(BASE, GT)
print(f'基准（同一球面重采样，无离群点）：CD-L1 {c1_0:.5f}   CD-L2 {c2_0:.5f}\\n')
print(' 离群距离   CD-L1     倍数    CD-L2     倍数     理论 Δ(L2)=(d-1)²/n   F@0.05')
for dist in [2.0, 5.0, 10.0, 50.0]:
    P = np.vstack([BASE, sphere(1, 7)*dist])
    c1, c2 = chamfer_l1(P, GT), chamfer_l2(P, GT)
    theo = (dist-1.0)**2/len(P)
    _, _, f5 = fscore(P, GT, 0.05)
    print(f' {dist:8.1f}   {c1:.5f}  {c1/c1_0:6.2f}×  {c2:.5f}  {c2/c2_0:7.2f}×'
          f'   {theo:16.5f}    {f5:.4f}')
    assert abs((c2 - c2_0) - theo) < 1e-4, \\
        f'L2 的增量应等于 (d-1)²/n：{(c2-c2_0):.5f} vs {theo:.5f}'
_P50 = np.vstack([BASE, sphere(1, 7)*50.0])
_r1 = chamfer_l1(_P50, GT)/c1_0; _r2 = chamfer_l2(_P50, GT)/c2_0
_, _, _f0 = fscore(BASE, GT, 0.05); _, _, _f1 = fscore(_P50, GT, 0.05)
assert _r1 < 1.5 and _r2 > 200, f'L1 应温和（{_r1:.2f}×）而 L2 灾难（{_r2:.0f}×）'
assert abs(_f0-_f1)/_f0 < 0.01, 'F-score 应几乎免疫'
print(f'\\n✓ **一个**离群点（50 倍半径）：CD-L1 涨 {_r1:.2f}×，CD-L2 涨 {_r2:.0f}×，'
      f'F@0.05 变 {(_f0-_f1)/_f0:.2%}')
print('  L1 的贡献是 (d-1)/n（线性），L2 是 (d-1)²/n（平方）—— 理论值与实测精确吻合。')
print('  所以「Chamfer 对离群点敏感」这句话必须说清是哪一种。')
print('  而 F-score 免疫，因为它是一个**计数**指标：落在阈值内算 1、外面算 0。')

# 采样密度
print('\\n采样密度会改变 CD（而几何完全没变）：')
print(' 真值点数  预测点数   CD-L1     F@0.02   F@0.05')
for npr in [200, 500, 2000, 5000, 8000]:
    P = sphere(npr, 1)
    _, _, f2 = fscore(P, GT, 0.02); _, _, f5 = fscore(P, GT, 0.05)
    print(f'  {len(GT):7d}  {npr:8d}   {chamfer_l1(P,GT):.5f}   {f2:.4f}   {f5:.4f}')
_clo = chamfer_l1(sphere(200, 1), GT); _chi = chamfer_l1(sphere(8000, 1), GT)
assert _clo/_chi > 2.5, f'密度从 200 到 8000 应让 CD 变 2.5 倍以上，实测 {_clo/_chi:.2f}'
print(f'\\n✓ 同一个球面，预测点数 200 -> 8000：CD-L1 从 {_clo:.5f} 到 {_chi:.5f}'
      f'（{_clo/_chi:.1f} 倍）')
print('  所以比较两份重建的 CD 之前**必须**重采样到同一密度 —— 否则比的是采样而不是几何。')"""),

code("""# F-score 只依赖 tau/s
print('F-score 只依赖 τ/s（s = 点云自身的平均最近邻间距）：\\n')
print(' 点数    自身间距 s   理论 √(4π/n)   F@0.02    F@s      F@2s     F@5s')
for n in [200, 500, 2000, 5000, 8000]:
    G = sphere(n, 0); P = sphere(n, 1)
    s = float(self_nn(G).mean())
    f = lambda tau: fscore(P, G, tau)[2]
    print(f' {n:6d}   {s:.5f}    {np.sqrt(4*np.pi/n):.5f}     '
          f'{f(0.02):.4f}   {f(s):.4f}  {f(2*s):.4f}  {f(5*s):.4f}')
_ss = []
for n in [200, 2000, 8000]:
    G = sphere(n, 0); P = sphere(n, 1); s = float(self_nn(G).mean())
    _ss.append((fscore(P, G, s)[2], fscore(P, G, 2*s)[2], fscore(P, G, 5*s)[2]))
_at_s = [v[0] for v in _ss]; _at_2s = [v[1] for v in _ss]; _at_5s = [v[2] for v in _ss]
assert max(_at_s)-min(_at_s) < 0.05, f'F@s 应与点数无关，实测 {_at_s}'
assert max(_at_2s)-min(_at_2s) < 0.05, f'F@2s 应与点数无关，实测 {_at_2s}'
assert all(v > 0.999 for v in _at_5s), f'F@5s 应都接近 1，实测 {_at_5s}'
print(f'\\n✓ F@s 在三个密度下都是 {min(_at_s):.4f}~{max(_at_s):.4f}，'
      f'F@2s 都是 {min(_at_2s):.4f}~{max(_at_2s):.4f}，F@5s 都是 1.0000')
_f002 = [fscore(sphere(n, 1), sphere(n, 0), 0.02)[2] for n in [200, 8000]]
print(f'  完全由 τ/s 决定。而固定的 F@0.02 那一列从 {_f002[0]:.4f} 涨到 {_f002[1]:.4f}'
      f'（{_f002[1]/_f002[0]:.0f} 倍）—— 因为固定的 τ 相对于 s 的比值在变。')
assert _f002[1]/_f002[0] > 20, '固定 τ 时 F 应随密度大幅变化'
print('\\n✓ 所以报 F-score 必须同时报 τ **与**采样密度。')
print('  而一个「完美」重建在 τ=s 时只有 0.55 分 —— 这说明 τ 不能取得太小。')
print('  常见做法：τ 取物体尺度的 1%~2%，并把两份点云重采样到同一密度。')"""),

md("""## 6 · accuracy 与 completeness 必须分开报"""),

code("""def half_sphere(n, seed=1):
    v = sphere(2*n, seed)
    return v[v[:, 2] > 0]

CASES = {
    '完美（同曲面重采样）': sphere(2000, 1),
    '缺一半（只重建半球）': half_sphere(2000, 1),
    '多出一半（多余结构）': np.vstack([sphere(2000, 1), sphere(2000, 3)*1.5]),
}
print(' 情形                    CD-L1    accuracy(P→G)  completeness(G→P)   F@0.05')
STAT = {}
for tag, P in CASES.items():
    p, r, f = fscore(P, GT, 0.05)
    STAT[tag] = (chamfer_l1(P, GT), p, r, f)
    print(f' {tag:22s} {STAT[tag][0]:.4f}     {p:.4f}         {r:.4f}          {f:.4f}')

_perf = STAT['完美（同曲面重采样）']
_miss = STAT['缺一半（只重建半球）']
_extra = STAT['多出一半（多余结构）']
# 两种失败的 CD 几乎相同
assert abs(_miss[0] - _extra[0])/_miss[0] < 0.15, \\
    f'两种失败的 CD 应接近：{_miss[0]:.4f} vs {_extra[0]:.4f}'
# 但方向完全相反
assert _miss[1] > 0.6 and _miss[2] < 0.55, '缺一半：accuracy 高、completeness 低'
assert _extra[2] > 0.6 and _extra[1] < 0.45, '多出一半：completeness 高、accuracy 低'
print(f'\\n✓ 「缺一半」的 CD {_miss[0]:.4f} 与「多出一半」的 {_extra[0]:.4f} 几乎相同，'
      f'而它们的含义完全相反：')
print(f'  缺一半：  accuracy {_miss[1]:.4f}（重建出来的部分是对的）'
      f'  completeness {_miss[2]:.4f}（只覆盖了一半）')
print(f'  多出一半：accuracy {_extra[1]:.4f}（一半是编出来的）'
      f'  completeness {_extra[2]:.4f}（真值都被覆盖了）')
print('\\n只看 CD（或只看 F）无法区分这两种失败 —— 而它们的修法完全不同：')
print('  completeness 低 -> 观测不足，或置信度阈值太严（模块 02 第 7 节）')
print('  accuracy 低     -> 有离群点、浮物，或补洞算法编出来的表面（第 1 节）')

# 单调性检查：三个口径在「几何真的变差」时是否一致
print('\\n单调性：三个口径在几何真的变差时是否一致（预测 = 真值 + 法向噪声）')
print('  σ        CD-L1     CD-L2     accuracy  completeness   F@2s')
_s0 = float(self_nn(GT).mean())
for sg in [0.0, 0.005, 0.02, 0.05, 0.1, 0.3]:
    r_ = np.random.default_rng(5)
    P = sphere(2000, 1)*(1 + r_.normal(0, sg, (2000, 1)))
    p, rc, f = fscore(P, GT, 2*_s0)
    print(f'  {sg:5.3f}   {chamfer_l1(P,GT):.5f}   {chamfer_l2(P,GT):.5f}   '
          f'{p:.4f}    {rc:.4f}       {f:.4f}')
_prev_c1 = _prev_f = None
for sg in [0.0, 0.02, 0.05, 0.1, 0.3]:
    r_ = np.random.default_rng(5)
    P = sphere(2000, 1)*(1 + r_.normal(0, sg, (2000, 1)))
    c1 = chamfer_l1(P, GT); f = fscore(P, GT, 2*_s0)[2]
    if _prev_c1 is not None:
        assert c1 > _prev_c1 and f < _prev_f, f'σ={sg} 时应单调变差'
    _prev_c1, _prev_f = c1, f
print('\\n✓ 三个口径都单调 —— 它们在「几何变差」这件事上是一致的。')
print('  分歧只出现在离群点（第 5 节）与采样密度（第 5 节）上，以及双向性（本节）。')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 数出 Marching Cubes 的等价类

实现 `my_canonical(code, with_inversion)`：给定 8 位符号配置，返回等价类的代表元
（在 24 个旋转、可选地加上「全部取反」下取最小值）。
再实现 `my_count_classes(with_inversion)`：返回等价类的个数。

顶点置换用已有的 `PERMS`。"""),

code("""def my_canonical(code, with_inversion=True):
    '''返回等价类的代表元（最小的等价配置）。'''
    # TODO: bits = [(code >> i) & 1 for i in range(8)]
    #       对每个 pp in PERMS：把 bits 按 pp 重排成一个新的 8 位数 c
    #          （c 的第 i 位 = bits[pp[i]]）
    #       候选里加上 c；with_inversion 时再加上 c ^ 0xFF
    #       返回 min(候选)
    raise NotImplementedError

def my_count_classes(with_inversion=True):
    '''返回 256 种配置的等价类个数。'''
    # TODO: len({my_canonical(c, with_inversion) for c in range(256)})
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
# ① 两个经典的数
assert my_count_classes(False) == 23, f'仅旋转应是 23 类，实测 {my_count_classes(False)}'
assert my_count_classes(True) == 15, f'旋转+反演应是 15 类，实测 {my_count_classes(True)}'

# ② 与参考实现一致
for _c in range(256):
    assert my_canonical(_c, True) == canonical(_c, True)
    assert my_canonical(_c, False) == canonical(_c, False)

# ③ 代表元必须是等价类里最小的，且幂等
for _c in range(256):
    _r = my_canonical(_c, True)
    assert _r <= _c, f'code={_c}: 代表元 {_r} 应 <= 原码'
    assert my_canonical(_r, True) == _r, '代表元的代表元应是它自己（幂等）'

# ④ 全内/全外应属于同一类（反演等价），而仅旋转时不同
assert my_canonical(0x00, True) == my_canonical(0xFF, True)
assert my_canonical(0x00, False) != my_canonical(0xFF, False)

# ⑤ 轨道大小之和 = 256
from collections import Counter as _C
_orb = _C(my_canonical(c, True) for c in range(256))
assert sum(_orb.values()) == 256 and len(_orb) == 15
# 每个轨道大小必须整除群阶 48
for _sz in _orb.values():
    assert 48 % _sz == 0, f'轨道大小 {_sz} 必须整除 48'

# ⑥ 单个顶点在内的 8 种配置应全部同类（旋转可以把任一角点换到任一角点）
_single = {my_canonical(1 << i, False) for i in range(8)}
assert len(_single) == 1, f'8 个「单顶点」配置应同类，实测 {len(_single)} 类'
print(f'✓ 练习 1 通过：仅旋转 {my_count_classes(False)} 类 / '
      f'加反演 {my_count_classes(True)} 类；'
      f'轨道大小 {sorted(_orb.values(), reverse=True)}（和为 {sum(_orb.values())}）')"""),

md("""### 📖 参考答案 1"""),

code("""def my_canonical(code, with_inversion=True):
    bits = [(code >> i) & 1 for i in range(8)]
    cands = []
    for pp in PERMS:
        c = 0
        for i in range(8):
            if bits[pp[i]]:
                c |= (1 << i)
        cands.append(c)
        if with_inversion:
            cands.append(c ^ 0xFF)
    return min(cands)

def my_count_classes(with_inversion=True):
    return len({my_canonical(c, with_inversion) for c in range(256)})

print('参考答案 1 已定义')
print('要点一：「15 种」这个教科书数字依赖把「内外反演」也算成等价（自测 ④）。')
print('       只用旋转是 23 类。而反演等价在几何上合理：翻转全部符号得到同一个曲面。')
print('要点二：自测 ⑤ 的「轨道大小整除 48」是一个免费的正确性检查（轨道-稳定子定理）。')
print('       如果你的置换写错了，轨道大小会出现不能整除 48 的数。')
print('要点三：置换的方向容易写反 —— c 的第 i 位应取 bits[pp[i]] 而不是把 bits[i] 放到')
print('       第 pp[i] 位。两者是互逆的置换，而因为我们对整个群取 min，')
print('       结果碰巧相同 —— 所以这个 bug 在这里不暴露，换个用法就会。')"""),

md("""### ✏️ 练习 2 · 找出含面歧义的配置

实现 `my_has_ambiguity(code)`：判断该配置是否含「面歧义」——
即存在某个**面**，它的一对**对角**顶点同号、另一对同号，而两对之间反号。
再实现 `my_count_ambiguous()`：返回 `(含歧义的配置数, 归约后的等价类数)`。

面用已有的 `FACES`、顶点坐标用 `VERTS`（面内对角 = 曼哈顿距离为 2）。"""),

code("""def my_has_ambiguity(code):
    '''该配置是否含面歧义。'''
    # TODO: bits = [(code >> i) & 1 for i in range(8)]
    #       对每个面 f in FACES：取 vs = VERTS[f]
    #         对面内每一对 (a,b)：若 sum(|vs[a]-vs[b]|) == 2 则它们是对角
    #           另两个顶点 o = 剩下的两个下标
    #           若 bits[f[a]]==bits[f[b]] 且 bits[f[o0]]==bits[f[o1]]
    #              且 bits[f[a]] != bits[f[o0]]  ->  返回 True
    #       都不满足则 False
    raise NotImplementedError

def my_count_ambiguous():
    '''返回 (含歧义的配置数, 归约后的等价类数)。'''
    # TODO: amb = [c for c in range(256) if my_has_ambiguity(c)]
    #       返回 (len(amb), len({my_canonical(c, True) for c in amb}))
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_n, _k = my_count_ambiguous()
assert _n == 120, f'含歧义的配置应是 120 个，实测 {_n}'
assert _k == 6, f'归约后应是 6 类，实测 {_k}'
assert abs(_n/256 - 0.469) < 0.002

# ② 与参考实现一致
for _c in range(256):
    assert my_has_ambiguity(_c) == has_face_ambiguity(_c), f'code={_c}'

# ③ 全内/全外/单顶点都**不**含歧义
assert not my_has_ambiguity(0x00) and not my_has_ambiguity(0xFF)
for _i in range(8):
    assert not my_has_ambiguity(1 << _i), f'单顶点配置 {1<<_i} 不该有歧义'

# ④ 一个具体的歧义配置：面 z=0 的两个对角顶点在内、另两个在外
#    面 z=0 的顶点是 VERTS 里 z==0 的那四个
_f0 = [i for i, v in enumerate(VERTS) if v[2] == 0]
_vs = VERTS[_f0]
_diag = [(a, b) for a in range(4) for b in range(a+1, 4)
         if np.sum(np.abs(_vs[a]-_vs[b])) == 2]
assert len(_diag) == 2, f'一个面应有 2 对对角，实测 {len(_diag)}'
_a, _b = _diag[0]
_code = (1 << _f0[_a]) | (1 << _f0[_b])
assert my_has_ambiguity(_code), f'配置 {_code} 应含歧义'

# ⑤ 歧义性在等价类内是一致的（它是几何性质，不依赖具体编号）
_by_cls = {}
for _c in range(256):
    _by_cls.setdefault(my_canonical(_c, True), []).append(my_has_ambiguity(_c))
for _rep, _vals in _by_cls.items():
    assert len(set(_vals)) == 1, f'类 {_rep} 内的歧义性不一致：{set(_vals)}'

# ⑥ 歧义配置的等价类必须是那 15 类的子集
assert {my_canonical(c, True) for c in range(256) if my_has_ambiguity(c)} \
       <= {my_canonical(c, True) for c in range(256)}
print(f'✓ 练习 2 通过：{_n}/256 = {_n/256:.1%} 含面歧义，归约为 {_k}/15 类')
print(f'  歧义性在等价类内一致（它是几何性质）；全内/全外/单顶点都无歧义')"""),

md("""### 📖 参考答案 2"""),

code("""def my_has_ambiguity(code):
    bits = [(code >> i) & 1 for i in range(8)]
    for f in FACES:
        vs = VERTS[f]
        for a in range(4):
            for b in range(a+1, 4):
                if np.sum(np.abs(vs[a] - vs[b])) == 2:
                    o = [k for k in range(4) if k not in (a, b)]
                    if (bits[f[a]] == bits[f[b]]
                            and bits[f[o[0]]] == bits[f[o[1]]]
                            and bits[f[a]] != bits[f[o[0]]]):
                        return True
    return False

def my_count_ambiguous():
    amb = [c for c in range(256) if my_has_ambiguity(c)]
    return len(amb), len({my_canonical(c, True) for c in amb})

print('参考答案 2 已定义')
print('要点一：46.9% 是一个很高的比例 —— 面歧义不是罕见的边界情形。')
print('       而原始 Marching Cubes（1987）对每一类**固定**选一种连法，')
print('       所以相邻体素可能对共享的面做出不一致的选择 -> 网格出现裂缝。')
print('要点二：自测 ⑤ 是一个结构性检查：歧义性必须在等价类内一致，')
print('       因为它是一个几何性质而不是编号性质。如果不一致，说明面的定义写错了。')
print('要点三：「面内对角」的判据是曼哈顿距离为 2 —— 在单位立方体的一个面上，')
print('       相邻顶点距离 1、对角顶点距离 2。用欧氏距离也行（1 vs √2），')
print('       但整数比较更稳。')"""),

md("""### ✏️ 练习 3 · Chamfer 的两个变体与它们的离群敏感性

实现 `my_cd(A, B, p)`：`p=1` 返回 CD-L1、`p=2` 返回 CD-L2
（都是双向最近邻距离的均值之和，L2 用距离的**平方**）。
再实现 `my_outlier_delta(n, d, p)`：**理论**预测「在 $n-1$ 个点的基础上
加一个距离 $d$（到单位球面的距离是 $d-1$）的离群点」会让 CD 增加多少。"""),

code("""def my_cd(A, B, p=1):
    '''p=1 -> CD-L1；p=2 -> CD-L2。'''
    # TODO: a, b = nn_dists(A, B)
    #       p==1: 返回 a.mean() + b.mean()
    #       p==2: 返回 (a**2).mean() + (b**2).mean()
    raise NotImplementedError

def my_outlier_delta(n, d, p=1):
    '''加一个离群点（到球面距离 d-1）后 CD 的**理论**增量。n 是加完之后的总点数。'''
    # TODO: p==1 -> (d-1)/n ; p==2 -> (d-1)**2/n
    #       （只有 P->G 方向受影响：那一个点贡献 (d-1) 或 (d-1)²，再除以 n）
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_G = sphere(2000, 0); _B = sphere(2000, 1)

# ① 与参考实现一致
assert abs(my_cd(_B, _G, 1) - chamfer_l1(_B, _G)) < 1e-12
assert abs(my_cd(_B, _G, 2) - chamfer_l2(_B, _G)) < 1e-12

# ② 基本性质
assert my_cd(_B, _B, 1) < 1e-12 and my_cd(_B, _B, 2) < 1e-12
assert abs(my_cd(_B, _G, 1) - my_cd(_G, _B, 1)) < 1e-12, '必须对称'

# ③ 三角不等式的反例（CD 不是度量）
_A1 = np.array([[0.0]]); _B1 = np.array([[0.0], [10.0]]); _C1 = np.array([[10.0]])
assert my_cd(_A1, _C1, 1) > my_cd(_A1, _B1, 1) + my_cd(_B1, _C1, 1) + 1e-9

# ④ **理论增量与实测精确吻合**
_c1_0 = my_cd(_B, _G, 1); _c2_0 = my_cd(_B, _G, 2)
for _d in [2.0, 5.0, 10.0, 50.0]:
    _P = np.vstack([_B, sphere(1, 7)*_d])
    for _p, _base in [(1, _c1_0), (2, _c2_0)]:
        _meas = my_cd(_P, _G, _p) - _base
        _theo = my_outlier_delta(len(_P), _d, _p)
        assert abs(_meas - _theo) < 2e-4, \
            f'd={_d} p={_p}: 实测增量 {_meas:.6f} vs 理论 {_theo:.6f}'

# ⑤ L1 线性、L2 平方
_r1 = [my_cd(np.vstack([_B, sphere(1,7)*d]), _G, 1)/_c1_0 for d in [2.0, 50.0]]
_r2 = [my_cd(np.vstack([_B, sphere(1,7)*d]), _G, 2)/_c2_0 for d in [2.0, 50.0]]
assert _r1[1] < 1.5, f'L1 应温和，50 倍半径的离群点只涨 {_r1[1]:.2f}×'
assert _r2[1] > 200, f'L2 应灾难，实测 {_r2[1]:.0f}×'
# 距离翻 25 倍（从 1 到 49 的超出量）时 L2 的增量应涨约 25² 倍
_d2 = my_outlier_delta(2001, 50.0, 2)/my_outlier_delta(2001, 2.0, 2)
assert abs(_d2 - 49.0**2/1.0**2) < 1e-6, f'L2 的增量应 ∝ (d-1)²，实测比 {_d2:.1f}'

# ⑥ 采样密度改变 CD（几何不变）
_lo = my_cd(sphere(200, 1), _G, 1); _hi = my_cd(sphere(8000, 1), _G, 1)
assert _lo/_hi > 2.5, f'密度从 200 到 8000 应让 CD 变 2.5 倍以上，实测 {_lo/_hi:.2f}'
print(f'✓ 练习 3 通过：理论增量 (d-1)^p/n 与实测在 4 个距离 × 2 个变体上全部吻合')
print(f'  50 倍半径的一个离群点：L1 涨 {_r1[1]:.2f}×，L2 涨 {_r2[1]:.0f}×')
print(f'  同一球面改采样密度（200 → 8000）：CD-L1 变 {_lo/_hi:.1f} 倍')"""),

md("""### 📖 参考答案 3"""),

code("""def my_cd(A, B, p=1):
    a, b = nn_dists(A, B)
    if p == 1:
        return float(a.mean() + b.mean())
    if p == 2:
        return float((a**2).mean() + (b**2).mean())
    raise ValueError(p)

def my_outlier_delta(n, d, p=1):
    e = d - 1.0                      # 离群点到单位球面的最近距离
    return (e/n) if p == 1 else (e**2/n)

print('参考答案 3 已定义')
print('要点一：自测 ④ 是这道题的核心 —— 理论增量与实测精确吻合（<2e-4）。')
print('       所以「Chamfer 对离群点敏感」这句话可以量化到一个闭式：')
print('       L1 的增量是 (d-1)/n，L2 是 (d-1)²/n。')
print('       前者线性、后者平方 —— 两者会给出**完全不同的排名**。')
print('要点二：只有 P→G 方向受离群点影响（G→P 方向几乎不变，因为真值点仍有近邻）。')
print('       这也是为什么 accuracy 与 completeness 要分开报（第 6 节）。')
print('要点三：自测 ⑥ 提醒一件容易忘的事 —— CD 依赖采样密度。')
print('       所以两份重建的 CD 只有在同一密度下才可比，')
print('       而不同的 Marching Cubes 分辨率天然给出不同的顶点数。')"""),

md("""### ✏️ 练习 4 · F-score 与双向分解

实现 `my_fscore(A, B, tau)`：返回 `(accuracy, completeness, F)`。
- accuracy = A 中最近邻距离 < τ 的比例（「预测有多少是对的」）；
- completeness = B 中最近邻距离 < τ 的比例（「真值有多少被覆盖」）；
- F = 两者的调和平均（都为 0 时返回 0）。

再实现 `my_tau_from_density(B, k)`：返回 `k` 倍于 `B` 自身平均最近邻间距的 τ。"""),

code("""def my_fscore(A, B, tau):
    '''返回 (accuracy, completeness, F)。'''
    # TODO: a, b = nn_dists(A, B)
    #       prec = (a < tau).mean() ; rec = (b < tau).mean()
    #       F = 0 if prec+rec == 0 else 2*prec*rec/(prec+rec)
    raise NotImplementedError

def my_tau_from_density(B, k=2.0):
    '''返回 k * (B 自身的平均最近邻间距)。'''
    # TODO: 用 self_nn(B).mean()
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_G = sphere(2000, 0)

# ① 与参考实现一致
for _t in [0.02, 0.05, 0.2]:
    assert all(abs(x-y) < 1e-12 for x, y in
               zip(my_fscore(sphere(2000, 1), _G, _t), fscore(sphere(2000, 1), _G, _t)))

# ② 自己对自己：三项都是 1
_p, _r, _f = my_fscore(_G, _G, 0.01)
assert _p == 1.0 and _r == 1.0 and _f == 1.0

# ③ 完全不相交：三项都是 0
_far = _G + np.array([100.0, 0, 0])
assert my_fscore(_far, _G, 0.05) == (0.0, 0.0, 0.0)

# ④ **只依赖 τ/s**：三个密度下 F@2s 应几乎相同
_vals = []
for _n in [200, 2000, 8000]:
    _Gn = sphere(_n, 0); _Pn = sphere(_n, 1)
    _tau = my_tau_from_density(_Gn, 2.0)
    _vals.append(my_fscore(_Pn, _Gn, _tau)[2])
assert max(_vals)-min(_vals) < 0.05, f'F@2s 应与密度无关，实测 {_vals}'
# 而固定 τ 时差很多
_fixed = [my_fscore(sphere(_n, 1), sphere(_n, 0), 0.02)[2] for _n in [200, 2000, 8000]]
assert max(_fixed)/max(min(_fixed), 1e-9) > 20, f'固定 τ 时应差很多，实测 {_fixed}'

# ⑤ 双向分解：「缺一半」与「多出一半」的 CD 接近而方向相反
_miss = half_sphere(2000, 1)
_extra = np.vstack([sphere(2000, 1), sphere(2000, 3)*1.5])
_pm, _rm, _fm = my_fscore(_miss, _G, 0.05)
_pe, _re, _fe = my_fscore(_extra, _G, 0.05)
assert _pm > 0.6 and _rm < 0.55, f'缺一半：accuracy 高 completeness 低，实测 {_pm:.3f}/{_rm:.3f}'
assert _re > 0.6 and _pe < 0.45, f'多出一半：反过来，实测 {_pe:.3f}/{_re:.3f}'
assert abs(chamfer_l1(_miss, _G) - chamfer_l1(_extra, _G))/chamfer_l1(_miss, _G) < 0.15, \
    '两者的 CD 应接近（所以单看 CD 分不开）'

# ⑥ 对离群点几乎免疫
_b = sphere(2000, 1)
_f0 = my_fscore(_b, _G, 0.05)[2]
_f1 = my_fscore(np.vstack([_b, sphere(1, 7)*50.0]), _G, 0.05)[2]
assert abs(_f0-_f1)/_f0 < 0.01, f'F 应几乎免疫离群点，实测变 {(_f0-_f1)/_f0:.2%}'
# ⑦ τ 单调
_mono = [my_fscore(_b, _G, t)[2] for t in [0.01, 0.03, 0.1, 0.3]]
assert all(_mono[i] <= _mono[i+1] for i in range(3)), f'F 应随 τ 单调，实测 {_mono}'
print(f'✓ 练习 4 通过：F@2s 在三个密度下 {[f"{v:.4f}" for v in _vals]}（几乎相同）')
print(f'  而固定 τ=0.02 时 {[f"{v:.4f}" for v in _fixed]}（差 {max(_fixed)/min(_fixed):.0f} 倍）')
print(f'  缺一半 acc/comp = {_pm:.4f}/{_rm:.4f}；多出一半 = {_pe:.4f}/{_re:.4f}'
      f'（而 CD 几乎相同）')"""),

md("""### 📖 参考答案 4"""),

code("""def my_fscore(A, B, tau):
    a, b = nn_dists(A, B)
    prec = float((a < tau).mean())
    rec = float((b < tau).mean())
    f = 0.0 if prec + rec == 0 else 2*prec*rec/(prec + rec)
    return prec, rec, f

def my_tau_from_density(B, k=2.0):
    return float(k*self_nn(np.asarray(B, float)).mean())

print('参考答案 4 已定义')
print('要点一：自测 ④ 把「F-score 只依赖 τ/s」变成了断言。')
print('       所以报 F-score 必须同时报 τ **与**采样密度 —— 缺一个数字就不可比。')
print('       而一个「完美」重建在 τ=s 时只有 0.55 分，说明 τ 不能取得太小。')
print('要点二：自测 ⑤ 是本模块最实用的一条。「缺一半」与「多出一半」的 CD 几乎相同，')
print('       但 accuracy/completeness 的方向完全相反 ——')
print('       而它们的修法也完全不同（观测不足 vs 有浮物/补洞）。')
print('       所以 Tanks and Temples 与 DTU 的标准协议都是分别报两者，再报 F。')
print('要点三：F 对离群点几乎免疫（自测 ⑥），因为它是**计数**指标。')
print('       代价是它丢掉了「合格的点有多准」这个信息 ——')
print('       所以 CD 与 F 是互补的，不该只报一个。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- Marching Cubes ----
from skimage.measure import marching_cubes
verts, faces, normals, values = marching_cubes(sdf_volume, level=0.0,
                                               spacing=(r, r, r))
# skimage 用的是 Lewiner 变体（Lewiner et al. 2003）——
# 它是本模块第 1 节说的「一致的查表」那一类，所以输出是水密的。
# 而如果你自己实现 1987 年的原版，46.9% 的配置会有裂缝风险。

# ---- TSDF 融合 ----
# Open3D 的稀疏实现（体素哈希，对应第 2 节的 12r/L）
import open3d as o3d
vol = o3d.pipelines.integration.ScalableTSDFVolume(
    voxel_length=0.005,                              # ← r
    sdf_trunc=0.015,                                 # ← τ = 3r（第 2 节）
    color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
for rgbd, pose in zip(rgbds, poses):
    vol.integrate(rgbd, intrinsic, np.linalg.inv(pose))
mesh = vol.extract_triangle_mesh()
# sdf_trunc 太小 -> 位姿误差直接变成双层墙；太大 -> 细节被抹平

# ---- 泊松重建 ----
pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
pcd.orient_normals_consistent_tangent_plane(k=30)    # ← **第 3 节的定向**，不能省
# 或者用视线方向定向（有相机位姿时更可靠）：
# pcd.orient_normals_towards_camera_location(camera_location=cam_center)
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=9, width=0, scale=1.1, linear_fit=False)
# densities 可以用来剪掉「支撑不足」的区域 —— 那些正是泊松「编」出来的部分
# 不剪的话它们会在 completeness 上白拿分（第 1 节末尾）

# ---- 评测：三件必须交代的事 ----
# ① CD 是 L1 还是 L2（第 5 节：离群点下排名会翻转）
# ② 两份点云是否重采样到了同一密度（第 5 节：2.9 倍）
# ③ F-score 的 τ **与**采样密度（第 5 节：只依赖 τ/s）
#
# Tanks and Temples 的官方脚本就是这么做的：
#   - 用 crop volume 限定评测区域
#   - 两侧都下采样到固定的 voxel size
#   - 分别报 precision（accuracy）与 recall（completeness），再报 F
# DTU 的官方脚本同样分开报 accuracy 与 completeness（单位 mm）
```

**评测检查清单（本模块的五条）**

| # | 要交代的事 | 不交代的后果 |
|---|---|---|
| ① | CD 是 **L1 还是 L2** | 一个离群点让 L2 涨 293 倍而 L1 只涨 1.31 倍 —— 排名会翻转 |
| ② | 两份点云是否**同密度** | 同一曲面改采样密度让 CD 变 2.9 倍 |
| ③ | F-score 的 **τ 与采样密度** | F 只依赖 τ/s；完美重建在 τ=s 时只有 0.55 分 |
| ④ | **accuracy 与 completeness 分开** | 「缺一半」与「多出一半」的 CD 几乎相同 |
| ⑤ | **不要**在 CD 上用三角不等式 | 它不是度量（$20 > 5+5$）—— 没有传递性 |

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 网格有裂缝 / 非水密 | Marching Cubes 的变体是否处理了面歧义 | 46.9% 的配置有歧义 |
| 重建出双层墙 | **位姿**（不是融合参数） | 尺度漂移 12% 在 8 m 处是 1 m，远超 τ |
| 表面整体鼓起或塌陷 | 法向的**角度**误差 | 位置误差 ≈ R·tanθ，与尺度成正比 |
| 泊松出来一团乱 | 法向的**朝向**（定向） | 净通量 = 1−2f，50% 反向时归零 |
| 补洞后 completeness 变好 | 补出来的部分不对应观测 | 它在 completeness 上「白拿分」 |
| 两篇论文的 CD 差很多 | L1/L2、采样密度 | 两者各值一个数量级 |
| F-score 很低但图看起来对 | τ 相对采样间距太小 | 完美重建在 τ=s 时只有 0.55 |"""),
]
