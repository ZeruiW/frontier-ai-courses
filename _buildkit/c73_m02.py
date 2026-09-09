# -*- coding: utf-8 -*-
"""C73 模块 02 · 置换不变性与 max-pool。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01 的密度衰减（520 倍）；线性代数"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_pointnet.ipynb'
                       '（对称函数的置换不变性（逐位差 0.0）/ '
                       '<strong>临界点集只有 24/1024，删掉其余 1000 个点输出逐位不变</strong> / '
                       '<strong>临界点数不随 N 增长：N 从 256 到 16384，它一直是 24</strong> / '
                       'max vs sum vs mean 在两种扰动下的对比 / '
                       'PointNet 不是旋转不变的）'),
    ("核心参考", "Qi et al., <em>PointNet</em>（CVPR 2017，"
                 "定理 1 与临界点集）· "
                 "Qi et al., <em>PointNet++</em>（NeurIPS 2017）· "
                 "Zaheer et al., <em>Deep Sets</em>（NeurIPS 2017）· "
                 "本课程 C46（图 ML：分组本质上是在建几何近邻图）"),
    ("预计时长", "读 40 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("symmetric-function", "从「无序」到对称函数：一个只有一步的推导", "".join([
        P("点云是一个<strong>集合</strong>，而神经网络吃的是<strong>张量</strong>。"
          "把集合塞进张量就必须选一个顺序，"
          "<strong>而输出不能依赖这个顺序</strong>。"),
        MATH(r"f(\{x_1,\dots,x_N\}) = f(\{x_{\pi(1)},\dots,x_{\pi(N)}\})"
             r"\quad \forall \pi \in S_N"),
        P("满足这个条件的最简单构造是<strong>「逐点变换 + 对称聚合」</strong>："),
        MATH(r"f(\{x_i\}) = \gamma\Bigl(\underset{i}{\square}\ h(x_i)\Bigr),"
             r"\qquad \square \in \{\max, \textstyle\sum, \text{mean}\}"),
        P(
            "<strong>这就是 PointNet 的全部骨架，而它的正确性是一个恒等式而不是一个实验结果。</strong>"
            "<em>$h$ 逐点作用，所以它不看顺序；"
            "$\\square$ 是对称的，所以它不看顺序；"
            "$\\gamma$ 作用在已经聚合好的向量上</em>。"
            "<strong>notebook 第 1 节用随机置换验证，"
            "而结果里有一个值得注意的区别</strong>："),
        TABLE(["聚合", "20 次随机置换的最大逐位差", "相对量级", "性质"], [
            ["<strong>$\\max$</strong>", "<strong>0.000e+00</strong>", "0",
             "<strong>逐位不变</strong>——它是<em>选择</em>操作，不做算术"],
            ["$\\min$", "<strong>0.000e+00</strong>", "0", "同上"],
            ["$\\sum$", "2.274e-12", "<strong>1.43e-15</strong>",
             "<strong>数学上不变，但不逐位不变</strong>"],
            ["mean", "2.220e-15", "1.43e-15", "同上"],
        ]),
        DUAL(
            "<strong>$\\sum$ 与 mean 的差是浮点加法不满足结合律造成的</strong>——"
            "<em>numpy 用 pairwise summation，累加的配对顺序依赖元素位置</em>。"
            "相对量级 $1.43\\times10^{-15}$ 约等于 $6\\varepsilon$"
            "（$\\varepsilon=2.22\\times10^{-16}$），"
            "<strong>所以它是纯数值噪声，不是逻辑错误。</strong>",
            "<strong>但它有一个实际后果：置换不变性的单元测试不能一律用「恰好相等」。</strong>"
            "<em>max 型模型可以（而且应该）用逐位相等来测——"
            "任何非零差都说明代码里有顺序依赖；"
            "而 sum/mean 型模型必须用相对容差</em>。"
            "<strong>顺带一个推论：基于 max-pool 的点云模型可以做到"
            "「换点序、结果逐位相同」，而基于 mean 的做不到</strong>——"
            "<em>这对需要逐位可复现的场景（回归测试、认证）是一个真实的差别。</em>",
        ),
        P(
            "<strong>而 Deep Sets（Zaheer et al. 2017）证明了反方向："
            "任何置换不变的连续函数都可以写成这个形式。</strong>"
            "<em>所以这不是「一种可行的设计」，而是「这一类函数的通用形式」</em>——"
            "<strong>剩下的全部设计自由度只在 $h$、$\\gamma$ 和 $\\square$ 的选择上。</strong>"
            "<em>而下一节会说明：$\\square$ 的选择不是风格问题，它决定了模型对哪种扰动稳定。</em>",
        ),
    ])),

    # ============================================================== 2
    ("which-aggregation", "$\\max$ / $\\sum$ / mean：选哪个不是风格问题", "".join([
        P("三个都是对称函数，所以三个都<strong>置换不变</strong>。"
          "<strong>而它们对「点集怎么变」的稳定性完全不同。</strong>"
          "notebook 第 2 节做两种扰动："),
        H3("扰动一：随机丢掉一部分点（点数变，密度分布不变）"),
        TABLE(["保留比例", "$\\max$ 的相对变化", "$\\sum$ 的相对变化", "mean 的相对变化"], [
            ["75%", "0.0432", "0.2494", "<strong>0.0249</strong>"],
            ["<strong>50%</strong>", "0.0847", "<strong>0.4979</strong>",
             "<strong>0.0402</strong>"],
            ["25%", "0.1485", "0.7517", "<strong>0.0728</strong>"],
            ["10%", "0.2347", "0.8994", "<strong>0.1207</strong>"],
        ]),
        P("<strong>$\\sum$ 的变化几乎正好等于 $1-\\text{保留比例}$</strong>——"
          "它与点数成正比，所以它<em>不能</em>用在点数会变的场景。"
          "<strong>而 mean 比 max 更稳。</strong>"),
        H3("扰动二：一半点聚成一个小簇（点数不变，密度分布大变）"),
        TABLE(["点集", "$\\max$ 的范数", "mean 的范数"], [
            ["均匀", "46.907", "6.299"],
            ["一半聚成小簇", "41.795（<strong>−11%</strong>）",
             "9.031（<strong>+43%</strong>）"],
        ]),
        DUAL(
            "<strong>两个扰动给出相反的排序，而这正是要点。</strong>"
            "<em>对<strong>点数</strong>变化：mean 最稳（4.0%）> max（8.5%）$\\gg$ sum（49.8%）；"
            "对<strong>密度分布</strong>变化：max 最稳（−11%）$\\gg$ mean（+43%）</em>。"
            "<strong>所以「max 最鲁棒」这个常见说法是不准确的——"
            "它只在「密度不均匀」这一类扰动上最鲁棒。</strong>",
            "<strong>而点云恰好就是密度极不均匀的。</strong>"
            "<em>模块 01 量到面密度从 67.7 掉到 0.13 点/m²（520 倍），"
            "而同一个物体在近处和远处的点数差两个数量级</em>。"
            "<strong>所以对点云，max 是正确的选择——"
            "不是因为它「更好」，而是因为它对这个领域的主要扰动免疫。</strong>"
            "<em>而在点数固定、密度均匀的场景（比如从网格上均匀采样的形状分类），"
            "mean 常常更好——这也确实是一些后续工作的发现。</em>",
        ),
        CALLOUT("intuition",
                "<strong>一条可以直接用的判据</strong>："
                "问「我的输入在部署时会怎么变？」"
                "<em>点数会变（不同距离、不同传感器）→ 不能用 sum；"
                "密度分布会变（近处密远处疏）→ 倾向 max；"
                "两者都不变（合成数据、固定采样）→ mean 通常最准</em>。"
                "<strong>而这个问题必须在选架构<em>之前</em>问，"
                "因为它决定的是模型对什么免疫，而不是模型有多准。</strong>"),
    ])),

    # ============================================================== 2b
    ("probe", "线性探针：三种聚合各自编码了多少「点数」信息", "".join([
        P("第 2 节量的是「输出变了多少」，"
          "<strong>而更直接的问法是：能不能从聚合后的向量<em>读出</em>点数？</strong>"
          "notebook 第 2b 节用一个线性回归探针来量（$N$ 从 128 到 2048，40 次重复）："),
        TABLE(["聚合", "从特征线性回归 $N$ 的 $R^2$", "平均绝对误差", "结论"], [
            ["<strong>$\\sum$</strong>", "<strong>1.0000</strong>",
             "<strong>0.6 点</strong>", "<strong>精确编码点数</strong>"],
            ["<strong>$\\max$</strong>", "<strong>0.7578</strong>", "244.8 点",
             "<strong>部分编码</strong>——<em>而这是一个容易被忽略的事实</em>"],
            ["mean", "0.1465", "471.6 点", "几乎不编码"],
        ]),
        DUAL(
            "<strong>$\\max$ 的 $R^2=0.76$ 值得解释，因为它反直觉。</strong>"
            "<em>直觉上 max 只取极值、与点数无关；"
            "而<strong>极值统计量本身依赖样本量</strong>——"
            "从更多样本里取最大值，期望更大</em>。"
            "<strong>所以 $\\max$ 并没有「完全丢弃点数」，"
            "它通过极值分布的偏移间接泄漏了点数。</strong>"
            "<em>这就是为什么第 2 节里 max 在丢点扰动下变了 8.5% 而不是 0%。</em>",
            "<strong>而 mean 的 $R^2=0.15$ 说明它才是真正对点数免疫的那个。</strong>"
            "<em>两者合起来给出一个更准确的三分法</em>："
            "<strong>$\\sum$ 编码点数 · $\\max$ 编码「极值形状 + 一点点点数」· "
            "mean 编码「平均形状」。</strong>"
            "<em>而如果你的任务不希望模型看到点数（因为点数只是距离的代理），"
            "那么严格来说应该用 mean 而不是 max</em>——"
            "<strong>而实践中用 max 是因为它对密度分布免疫，"
            "这个收益大于它泄漏的那点点数信息。</strong>",
        ),
        H3("那把 $\\max$ 与 mean 拼起来呢"),
        TABLE(["聚合", "丢一半点的相对变化", "一半聚成小簇的相对变化"], [
            ["$\\max$", "0.1025", "0.1478"],
            ["mean", "<strong>0.0396</strong>", "0.7572"],
            ["<strong>拼接 $[\\max, \\text{mean}]$</strong>", "0.1017",
             "<strong>0.1782</strong>"],
        ]),
        P("<strong>拼接的结果不是「兼得两者的优点」，而是「被范数大的那一半支配」。</strong>"
          "<em>丢点扰动下它是 0.1017（几乎等于 max 的 0.1025，而不是 mean 的 0.0396）；"
          "聚簇扰动下它是 0.1782（介于 0.1478 与 0.7572 之间但更靠近 max）</em>。"
          "<strong>原因是 max 的范数远大于 mean（46.9 vs 6.3），"
          "所以拼接向量的相对变化被 max 那一半主导。</strong>"
          "<em>要真正「兼得」，必须先各自归一化——"
          "而那又引入了一个新的超参数。</em>"),
        CALLOUT("intuition",
                "<strong>这一节的方法本身比结论更值得带走：用一个线性探针来问"
                "「这个表示里有没有某个量」。</strong>"
                "<em>它便宜（一次最小二乘）、不需要训练下游任务、"
                "而且结果是可解释的（$R^2$ 就是「能读出多少」）</em>。"
                "<strong>而它在 C71 模块 02 里也出现过</strong>——"
                "<em>那里用「无内容探针」量 prompt 的标签先验，"
                "这里用线性探针量点云特征里的点数信息。同一个思路。</em>"),
    ])),

    # ============================================================== 3
    ("critical-set", "本模块的核心：临界点集", "".join([
        P("max-pool 有一个很强的结构性后果，"
          "而它是 PointNet 原论文的定理 1："),
        CALLOUT("paper",
                "<strong>全局特征的每一维，都恰好来自<em>某一个</em>点。</strong>"
                "所以决定输出的点最多只有 $D$ 个（$D$ = 特征维数）——"
                "<em>而其余 $N-D$ 个点对输出<strong>没有任何影响</strong></em>。"
                "这个集合叫<strong>临界点集（critical point set）</strong>。"),
        P("notebook 第 3 节把它验证到逐位相等——"
          "<strong>但要分清「从同一个特征矩阵里<em>选</em>」与「<em>重算</em>子集的特征」</strong>："
          "<em>前者是恒等式（差恒为 0），"
          "后者只保证到几个 ULP，因为 BLAS 对不同形状的矩阵乘走不同路径</em>"
          "（本课在 $N{=}128,D{=}16$ 上量到 $2\\varepsilon$）。"),
        TABLE(["$N$", "$D$", "临界点数", "占 $N$ 的比例", "删掉其余点后的输出变化"], [
            ["256", "64", "16", "6.25%", "—"],
            ["<strong>1024</strong>", "<strong>64</strong>", "<strong>24</strong>",
             "<strong>2.34%</strong>", "<strong>0.000e+00（选择口径，逐位相等）</strong>"],
            ["4096", "64", "26", "0.63%", "—"],
            ["<strong>16384</strong>", "64", "<strong>24</strong>",
             "<strong>0.15%</strong>", "—"],
            ["1024", "256", "28", "2.73%", "—"],
            ["16384", "256", "34", "0.21%", "—"],
        ]),
        DUAL(
            "<strong>看第一列与第三列：$N$ 从 256 涨到 16384（64 倍），"
            "而临界点数几乎不动（16 → 24）。</strong>"
            "<em>上界是 $D$，但实际值远小于 $D$（24 vs 64），"
            "而且它<strong>由特征空间的几何决定，不由点数决定</strong></em>。"
            "<strong>所以占比从 6.25% 掉到 0.15%——"
            "点越多，被「浪费」的点越多。</strong>",
            "<strong>这一个事实同时解释了 PointNet 的两大性质。</strong>"
            "<em>① <strong>对点丢失极其鲁棒</strong>：随机删掉一半点，"
              "大概率不碰到那 24 个临界点——这与第 2 节 max 只变 8.5% 是同一件事；"
            "② <strong>抓不住细节</strong>：无论输入多少点，"
              "全局特征只「看到」几十个极值点，"
              "所以精细的局部结构在聚合时就丢了</em>。"
            "<strong>而这正是 PointNet++ 要解决的问题——它的答案是「分层聚合」，"
            "让 max-pool 在<em>局部</em>邻域里做，于是临界点集变成"
            "「每个局部邻域各贡献几十个点」。</strong>",
        ),
    ])),

    # ============================================================== 4
    ("max-vs-sum-robustness", "临界点集的另一面：单点删除实验", "".join([
        P("把第 3 节的结论换一个问法：<strong>删掉<em>任意一个</em>点，输出会变吗？</strong>"),
        TABLE(["聚合方式", "删掉单点后输出不变的点数", "最小变化量"], [
            ["<strong>$\\max$</strong>", "<strong>1000 / 1024</strong>", "0（精确）"],
            ["$\\sum$", "0 / 1024", "0.776"],
        ]),
        DUAL(
            "<strong>$\\max$ 有 97.7% 的点是「可删除的」，而 $\\sum$ 一个都没有。</strong>"
            "<em>这不是一个精度问题，而是两种完全不同的信息结构："
            "$\\max$ 把点集压成「若干个极值点的坐标」，"
            "$\\sum$ 把点集压成「所有点的一个加权总量」</em>。"
            "<strong>所以 $\\sum$ 天然编码了「有多少点」这个信息（第 2b 节量到 $R^2=1.00$），而 $\\max$ 只泄漏一部分（$R^2=0.76$）。</strong>",
            "<strong>哪个对，取决于「点数是信号还是噪声」。</strong>"
            "<em>如果点数携带信息（比如「点越多说明物体越大」），$\\sum$ 保留了它；"
            "而在点云里，点数主要由距离决定（模块 01 的 520 倍衰减），"
            "所以它是<strong>噪声</strong></em>——"
            "<strong>于是「丢弃点数信息」从缺点变成了优点。</strong>"
            "<em>这是本课反复出现的模式：一个设计的好坏取决于领域里哪些量是信号。</em>",
        ),
        CALLOUT("warn",
                "<strong>临界点集也是一个安全性质。</strong>"
                "<em>它意味着「只要不动那 24 个点，就无法改变 PointNet 的全局特征」——"
                "但反过来，<strong>动那 24 个点就能大幅改变输出</strong></em>。"
                "所以点云上的对抗攻击通常只需要添加/移动极少数点"
                "（<em>而 C44 讲的对抗样本在这里有一个特别干净的结构</em>）。"
                "<strong>本课不做攻击实现，只指出这个结构。</strong>"),
    ])),

    # ============================================================== 5
    ("not-rotation-invariant", "置换不变 ≠ 旋转不变", "".join([
        P("一个常见的混淆：PointNet 解决了「无序」，"
          "<strong>而它对旋转、平移、缩放全都不是不变的。</strong>"),
        TABLE(["绕 $z$ 旋转", "全局特征的相对变化", "临界点集改变了几个点"], [
            ["0°", "0.0000", "0"],
            ["5°", "0.0226", "6"],
            ["15°", "0.0743", "11"],
            ["45°", "0.1479", "9"],
            ["90°", "0.1386", "10"],
            ["180°", "0.1473", "12"],
        ]),
        DUAL(
            "<strong>15° 的旋转就让全局特征变 7.4%，并且换掉临界点集里 11 个点。</strong>"
            "<em>而这是必然的：$h$ 是逐点的、不知道全局朝向；"
            "而 max 只保证对<strong>置换</strong>不变</em>。",
            "<strong>PointNet 的做法是加一个 T-Net：用一个小网络预测一个 $3\\times3$ 变换，"
            "把输入「摆正」再送进主干。</strong>"
            "<em>这是一个<strong>学出来的</strong>对齐，不是一个不变性保证</em>——"
            "所以它在训练分布内有效、分布外未必。"
            "<strong>而在自动驾驶里通常不需要它</strong>："
            "<em>因为重力方向与车体朝向都是已知的（C72 的外参），"
            "所以点云本来就是「摆正」的</em>——"
            "<strong>这也是 3D 检测网络普遍不用 T-Net 的原因。</strong>",
        ),
        CALLOUT("intuition",
                "<strong>更一般的一条：不变性要么来自结构，要么来自数据，二者代价不同。</strong>"
                "<em>置换不变来自结构（max 的恒等式，零代价、绝对可靠）；"
                "旋转不变如果靠 T-Net 就来自数据（需要学、可能失效）；"
                "而如果靠外参把点云摆正，它就又变成了结构性的</em>。"
                "<strong>所以「先用几何把能定的自由度定掉」几乎总是更便宜</strong>——"
                "<em>而那正是 C72 整门课的内容。</em>"),
    ])),

    # ============================================================== 5b
    ("segmentation-head", "分割头：全局特征回到每个点，但它带不来局部结构", "".join([
        P("分类只要一个全局向量，而<strong>分割要给每个点一个标签</strong>。"
          "PointNet 的做法是把全局特征拼回每个点的逐点特征："),
        MATH(r"\text{seg}(x_i) = \rho\bigl([\,h(x_i)\ \|\ g\,]\bigr),"
             r"\qquad g = \max_j h(x_j)"),
        CALLOUT("danger",
                "<strong>这个式子有一个结构性的后果：$g$ 对所有点是<em>同一个</em>向量。</strong>"
                "<em>所以它无法区分任何两个点——它只能提供一个全局的上下文偏置</em>。"
                "<strong>于是逐点的判别能力<em>全部</em>来自 $h(x_i)$，"
                "而 $h$ 是逐点的 MLP、看不到任何邻域。</strong>"
                "<em>结论：<strong>坐标相同的两个点，无论局部结构多不同，"
                "PointNet 的分割头必然给出相同的预测</strong></em>。"),
        DUAL(
            "<strong>这不是一个实现缺陷，是这个架构的数学上界。</strong>"
            "<em>notebook 第 5b 节把它验证成一个恒等式："
            "构造两个坐标完全相同、但邻域截然不同的点，"
            "它们的逐点特征逐位相等</em>。"
            "<strong>所以 PointNet 的分割本质上是"
            "「逐点分类 + 一个全局偏置」——"
            "它能学到「这个高度的点通常是标志」，"
            "学不到「这个点周围有一个平面所以它是地面」。</strong>",
            "<strong>而这正好定量地说明了 PointNet++ 为什么必要。</strong>"
            "<em>分层聚合让每个点先在自己的邻域里做一次 max-pool，"
            "于是它的特征里带进了局部几何</em>——"
            "<strong>而「局部几何」恰好是分割任务的主要线索</strong>"
            "（<em>平面 → 地面、竖直薄片 → 标志、曲面 → 车身</em>）。"
            "<strong>所以从 PointNet 到 PointNet++ 的改动不是「加深」，"
            "而是「补上一个架构上缺失的能力」。</strong>",
        ),
        H3("一个实践推论：拼接维度的比例"),
        P("常见配置里 $h(x_i)$ 是 64 维、$g$ 是 1024 维，"
          "所以拼接后 <strong>94% 的维度对所有点相同</strong>。"
          "<em>这看起来很浪费，而它其实是必要的——"
          "因为 $\\rho$ 需要足够的全局上下文才能把「这个高度」翻译成「标志还是车顶」</em>。"
          "<strong>但它也解释了为什么 PointNet 的分割对场景整体变化很敏感："
          "换一个场景，那 94% 全变了。</strong>"),
    ])),

    # ============================================================== 6
    ("pointnet-pp", "PointNet++：把 max-pool 搬进局部邻域", "".join([
        ASCII("""
   PointNet：一次全局 max-pool
     N 个点 → 逐点 MLP → [max over N] → 一个全局向量
                                  └── 临界点集只有 ~24 个点（第 3 节）

   PointNet++：分层的局部 max-pool
     N 个点
       │ ① 采样中心点（FPS，M 个）        ← 模块 01 第 5b 节：FPS 有偏倚
       │ ② 分组（球查询 或 kNN）
       │ ③ 组内做 PointNet（局部 max-pool）
       ▼
     M 个「局部特征点」  → 再重复 ①②③ →  更少更抽象的点 → 全局
                            └── 每一层各有自己的临界点集
        """),
        TABLE(["分组方式", "怎么做", "优点", "缺点"], [
            ["<strong>球查询（ball query）</strong>",
             "取半径 $R$ 内的点，最多 $K$ 个",
             "<strong>邻域的物理尺度固定</strong>——"
             "<em>所以不同密度区域学到的是同一尺度的结构</em>",
             "稀疏区域可能凑不满 $K$ 个（要 padding）"],
            ["<strong>kNN</strong>", "取最近的 $K$ 个点",
             "总能拿到 $K$ 个，实现简单",
             "<strong>邻域的物理尺度随密度变化</strong>——"
             "<em>远处的 $K$ 个点可能横跨十几米（模块 01：73 m 处环距 31 m）</em>"],
        ]),
        DUAL(
            "<strong>原论文选球查询，理由正是密度不均匀。</strong>"
            "<em>kNN 在近处的 32 个邻居可能只占 0.3 m，"
            "在远处的 32 个邻居可能横跨 15 m——"
            "于是同一个卷积核在不同距离上「看」的是完全不同尺度的东西</em>。"
            "<strong>而球查询把物理尺度钉死，代价是要处理「点不够」的情形。</strong>",
            "<strong>而分组这一步本质上是在建一个几何近邻图</strong>，"
            "<em>然后在图上做一轮 message passing——"
            "这与 C46 的图卷积是同一个操作</em>。"
            "<strong>区别在于点云的图是<em>动态</em>的（每一层重新采样中心点、重新分组），"
            "而 C46 里的图通常是给定的。</strong>"
            "<em>所以点云网络的很大一部分计算花在「建图」上，而不是「卷积」上</em>——"
            "<strong>这也是它比体素路线慢的主要原因。</strong>",
        ),
    ])),

    # ============================================================== 6b
    ("cost-structure", "点云路线与体素路线的成本结构完全不同", "".join([
        P("PointNet++ 的每一层都要<strong>采样中心点 + 建邻域</strong>，"
          "而这两步的开销与「卷积」本身不在同一个数量级。"),
        TABLE(["配置", "FPS 的距离计算", "球查询（朴素）", "组内 MLP"], [
            ["$M{=}1024$, $K{=}32$", "<strong>105.1 M 次</strong>", "105.1 M 次",
             "<strong>6.29 M FLOP</strong>"],
            ["$M{=}4096$, $K{=}32$", "420.5 M 次", "420.5 M 次", "25.17 M FLOP"],
            ["$M{=}1024$, $K{=}64$", "105.1 M 次", "105.1 M 次", "12.58 M FLOP"],
        ]),
        P("（$N=102{,}668$，即模块 01 那一帧环扫点云。）"
          "<strong>建邻域的操作数比组内 MLP 大 17 倍。</strong>"),
        DUAL(
            "<strong>而体素路线的成本结构恰好相反。</strong>"
            "<em>同一帧点云在 $r{=}0.16$ m 下有 30,478 个非空体素，"
            "子流形稀疏卷积（$3^3$、64→64）是 3,370 M FLOP</em>——"
            "<strong>FLOP 数比点云路线的 MLP 大 500 倍，"
            "但它<em>没有建邻域的开销</em></strong>"
            "（<em>稀疏张量用哈希表，邻居查询是 $O(1)$，而且这张表可以在层间复用</em>）。",
            "<strong>所以两条路线不是「谁更快」，而是「钱花在哪」：</strong>"
            "<em>点云路线花在<strong>建邻域</strong>上——串行、访存密集、难并行"
            "（FPS 的每一步依赖上一步）；"
            "体素路线花在<strong>卷积</strong>上——规则、并行、算力密集</em>。"
            "<strong>而现代加速器擅长后者</strong>，"
            "<em>所以在实际的墙钟时间上，即使 FLOP 数高得多，体素/柱体路线通常更快</em>。"
            "<strong>本课不测墙钟时间（那依赖具体硬件），"
            "但这个成本结构的差异是可以直接算出来的。</strong>",
        ),
        CALLOUT("warn",
                "<strong>所以「FLOPs」在这两条路线之间不是一个可比的指标。</strong>"
                "<em>一个点云模型的 FLOPs 可以比体素模型低两个数量级，而跑得更慢</em>。"
                "<strong>比较必须用同一硬件上的墙钟时间与显存峰值</strong>，"
                "<em>而这与 C66 模块 05 的「成本与 harness 指纹」是同一条纪律："
                "指标必须与它要代理的那个量真正相关。</em>"),
    ])),

    # ============================================================== 7
    ("checklist", "本模块的清单", "".join([
        OL([
            "<strong>选聚合函数之前先问「部署时输入会怎么变」</strong>（第 2 节）——"
            "点数会变就不能用 $\\sum$；密度会变就倾向 $\\max$",
            "<strong>算一次你模型的临界点集大小</strong>（第 3 节）。"
            "<em>它不需要标签、不需要训练完成，随机权重就能算；"
            "而它直接告诉你「全局特征实际上看到了多少个点」</em>",
            "<strong>不要指望全局 max-pool 抓细节</strong>——"
            "<em>无论输入 1024 还是 16384 个点，它只看到 ~24 个</em>。"
            "要细节就得分层（第 6 节）",
            "<strong>分组用球查询而不是 kNN</strong>（第 6 节），"
            "除非你的点云密度确实均匀",
            "<strong>在自动驾驶里不要加 T-Net</strong>（第 5 节）——"
            "<em>外参已经把点云摆正了，学一个对齐只会引入分布外风险</em>",
            "<strong>不要用 FLOPs 比较点云路线与体素路线</strong>（第 6b 节）——"
            "<em>成本结构完全不同（建邻域 vs 卷积），必须比同硬件上的墙钟时间</em>",
            "<strong>记录采样方式与 $K$</strong>（模块 01 第 5b 节），"
            "并在训练/部署间保持一致",
        ]),
        CALLOUT("danger",
                "<strong>最后一条陷阱：临界点集让「点数」这个指标变得误导。</strong>"
                "<em>「我们把输入点数从 1024 提到 4096，效果没变」"
                "常被解读成「模型已经饱和」</em>——"
                "<strong>而真实原因可能只是全局 max-pool 本来就只用 24 个点，"
                "多给的 3072 个点根本没进入计算。</strong>"
                "<em>正确的对照实验是：同时把分层结构加上，再看点数的收益。</em>"),
    ])),
]

# ══════════════════════════════════════════════════════════════════
NB = [
    md("""# 02 · 置换不变性与 max-pool

这个 notebook 把 PointNet 的四个**结构性事实**验证成恒等式或精确数值：

1. **置换不变**：max/min 的逐位差 **恰好 0.0**（选择操作）；
   而 **sum/mean 只是「数学上」不变**——浮点加法不满足结合律，相对差 1.43e-15。
2. **临界点集**：$N{=}1024$、$D{=}64$ 时只有 **24 个点**决定输出，
   删掉其余 1000 个点，输出**逐位相等**；
   而 $N$ 从 256 涨到 16384（64 倍），临界点数几乎不动（16 → 24）。
3. **三种聚合各自编码什么**：线性探针给出
   $\\sum$ 的 $R^2{=}1.0000$、$\\max$ 的 $0.7578$、mean 的 $0.1465$——
   **max 并没有「完全丢弃点数」**。
4. **分割头的上界**：坐标相同的两个点，无论邻域多不同，
   PointNet 的逐点特征**必然逐位相等**。

> 全程随机权重、不训练。**这些性质与权重取值无关**——
> 所以它们比任何精度数字都稳定。"""),

    md("""## 0 · 环境与一个 30 行的 PointNet"""),

    code("""import numpy as np

print('numpy', np.__version__)
print('本 notebook 全程随机权重，**不训练** —— 验证的是结构性质')

N, D = 1024, 64
rng = np.random.default_rng(0)

def make_mlp(din, dout, seed=0, scale=0.3):
    r = np.random.default_rng(seed)
    return r.normal(size=(din, dout)), r.normal(size=dout) * scale

W, B = make_mlp(3, D, seed=1)

def pointwise(P, W=W, B=B):
    '''逐点 MLP（一层 + ReLU）-> (N, D)。'''
    return np.maximum(np.atleast_2d(P) @ W + B, 0.0)

def aggregate(F, kind='max'):
    return {'max': F.max(0), 'sum': F.sum(0), 'mean': F.mean(0)}[kind]

def pointnet(P, kind='max'):
    return aggregate(pointwise(P), kind)

P = rng.normal(size=(N, 3))
print(f'\\n点数 {N}，特征维 {D}')
print(f'全局特征范数: max {np.linalg.norm(pointnet(P,"max")):.3f}  '
      f'sum {np.linalg.norm(pointnet(P,"sum")):.3f}  '
      f'mean {np.linalg.norm(pointnet(P,"mean")):.3f}')"""),

    md("""## 1 · 置换不变性：一个恒等式

**注意差是恰好 0.0，不是「很小」**——因为 max/sum/mean 对置换是数学上不变的。"""),

    code("""print(f"{'聚合':>6s} {'20 次置换的最大逐位差':>22s} {'相对量级':>12s}")
inv = {}
for kind in ['max', 'min', 'sum', 'mean']:
    F0 = pointwise(P)
    ref = {'max': F0.max(0), 'min': F0.min(0),
           'sum': F0.sum(0), 'mean': F0.mean(0)}[kind]
    worst = 0.0
    for t in range(20):
        perm = np.random.default_rng(t).permutation(N)
        F = pointwise(P[perm])
        got = {'max': F.max(0), 'min': F.min(0),
               'sum': F.sum(0), 'mean': F.mean(0)}[kind]
        worst = max(worst, float(np.abs(got - ref).max()))
    scale = float(np.abs(ref).max())
    rel = worst / scale if scale > 0 else 0.0
    inv[kind] = (worst, rel)
    print(f'{kind:>6s} {worst:21.3e} {rel:11.2e}')

# ① max / min 是**选择**操作，逐位不变
assert inv['max'][0] == 0.0, 'max 必须逐位不变（它不做算术）'
assert inv['min'][0] == 0.0, 'min 同理'
# ② sum / mean 数学上不变，但浮点加法不满足结合律
EPS = np.finfo(np.float64).eps
assert 0 < inv['sum'][1] < 100 * EPS, \
    f"sum 的相对差应当是数值噪声量级，实测 {inv['sum'][1]:.2e}"
assert 0 < inv['mean'][1] < 100 * EPS
print(f'\\n✅ **max / min 逐位不变；sum / mean 只是「数学上」不变**')
print(f'   sum 的相对差 {inv["sum"][1]:.2e} ≈ {inv["sum"][1]/EPS:.1f}ε '
      f'（ε = {EPS:.2e}）—— 纯数值噪声')
print('   原因：numpy 用 pairwise summation，累加的配对顺序依赖元素位置')
print('   → **置换不变性的单元测试不能一律用「恰好相等」**：')
print('     max 型可以（非零差 = 代码里有顺序依赖）；sum/mean 型必须用相对容差')

# 反例：不对称的聚合
def first_k(F, k=8):
    return F[:k].ravel()

g0 = first_k(pointwise(P))
g1 = first_k(pointwise(P[np.random.default_rng(3).permutation(N)]))
print(f'\\n对照：取前 8 个点（不对称）-> 置换后差 = {np.abs(g1-g0).max():.3f}')
assert np.abs(g1 - g0).max() > 0.1, '不对称的聚合必然被置换破坏'
print('✅ 所以「对称」不是一个可选的设计偏好，它是这个问题的硬约束')"""),

    md("""## 2 · 三种聚合在两种扰动下的表现

**两种扰动给出相反的排序**——这是本节的要点。"""),

    code("""def rel_change(a, b):
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))

# 扰动一：随机丢点（点数变，密度分布不变）
print('扰动一：随机丢点\\n')
print(f\"{'保留比例':>9s} {'max':>10s} {'sum':>10s} {'mean':>10s}\")
drop = {}
for frac in [0.75, 0.5, 0.25, 0.1]:
    k = int(N * frac)
    row = {}
    for kind in ['max', 'sum', 'mean']:
        g = pointnet(P, kind)
        ch = [rel_change(pointnet(P[np.random.default_rng(t).choice(N, k, replace=False)],
                                  kind), g) for t in range(20)]
        row[kind] = float(np.mean(ch))
    drop[frac] = row
    print(f'{frac:8.0%} {row["max"]:10.4f} {row["sum"]:10.4f} {row["mean"]:10.4f}')

# sum 的变化 ≈ 1 − 保留比例
for frac in [0.75, 0.5, 0.25]:
    assert abs(drop[frac]['sum'] - (1 - frac)) < 0.05, (frac, drop[frac]['sum'])
print('\\n✅ sum 的变化 ≈ 1 − 保留比例（它与点数成正比）')
assert drop[0.5]['mean'] < drop[0.5]['max'] < drop[0.5]['sum']
print(f'   而 50% 丢点时：mean {drop[0.5]["mean"]:.4f} < '
      f'max {drop[0.5]["max"]:.4f} << sum {drop[0.5]["sum"]:.4f}')

# 扰动二：一半点聚成小簇（点数不变，密度分布大变）
print('\\n扰动二：一半点聚成一个小簇（点数不变）\\n')
P_clump = np.vstack([rng.normal(size=(N//2, 3)),
                     rng.normal(scale=0.05, size=(N//2, 3)) + np.array([2., 0., 0.])])
print(f\"{'聚合':>6s} {'原范数':>10s} {'聚簇后范数':>12s} {'相对变化':>10s}\")
clump = {}
for kind in ['max', 'mean']:
    g = pointnet(P, kind); g2 = pointnet(P_clump, kind)
    clump[kind] = rel_change(g2, g)
    print(f'{kind:>6s} {np.linalg.norm(g):10.3f} {np.linalg.norm(g2):11.3f} '
          f'{clump[kind]:10.4f}')

assert clump['max'] < clump['mean'], '密度扰动下 max 应当更稳'
print(f'\\n✅ **两种扰动的排序相反**：')
print(f'   点数变化 -> mean 最稳（{drop[0.5]["mean"]:.4f}）')
print(f'   密度变化 -> max 最稳（{clump["max"]:.4f} vs mean {clump["mean"]:.4f}）')
print('   → 点云的主要扰动是**密度**（模块 01：520 倍衰减），所以选 max')"""),

    md("""## 2b · 线性探针：哪种聚合编码了「点数」

比「输出变了多少」更直接的问法：**能不能从聚合向量里<em>读出</em> $N$？**"""),

    code("""def probe_count(kind, Ns=(128, 256, 384, 512, 768, 1024, 1536, 2048),
                trials=40, D_=D):
    '''线性回归探针：从聚合特征预测点数 N，返回 (R², MAE)。'''
    X, Y = [], []
    for t in range(trials):
        for n in Ns:
            Q = np.random.default_rng(1000 + t * 100 + n).normal(size=(n, 3))
            X.append(aggregate(pointwise(Q), kind))
            Y.append(float(n))
    A = np.column_stack([np.array(X), np.ones(len(X))])
    Y = np.array(Y)
    w, *_ = np.linalg.lstsq(A, Y, rcond=None)
    pred = A @ w
    r2 = 1 - ((Y - pred) ** 2).sum() / ((Y - Y.mean()) ** 2).sum()
    return float(r2), float(np.abs(Y - pred).mean())

print(f\"{'聚合':>6s} {'R²':>9s} {'平均绝对误差(点)':>17s}\")
pr = {}
for kind in ['max', 'sum', 'mean']:
    r2, mae = probe_count(kind)
    pr[kind] = r2
    print(f'{kind:>6s} {r2:9.4f} {mae:16.1f}')

assert pr['sum'] > 0.999, 'sum 应当精确编码点数'
assert pr['mean'] < 0.3, 'mean 应当几乎不编码点数'
assert 0.5 < pr['max'] < 0.95, f'max 应当**部分**编码点数，实测 {pr["max"]:.4f}'
print(f'\\n✅ sum 精确编码（R²={pr["sum"]:.4f}）· '
      f'max **部分**编码（R²={pr["max"]:.4f}）· mean 几乎不编码（R²={pr["mean"]:.4f}）')
print('   max 的 0.76 不是噪声：**从更多样本里取最大值，期望更大**')
print('   —— 极值统计量本身依赖样本量，所以 max 通过分布偏移间接泄漏了点数')

# 拼接不是「兼得」，是「被范数大的那一半支配」
def cat_agg(Q):
    F = pointwise(Q)
    return np.concatenate([F.max(0), F.mean(0)])

g_cat = cat_agg(P)
ch_drop = np.mean([rel_change(cat_agg(P[np.random.default_rng(t).choice(N, N//2,
                              replace=False)]), g_cat) for t in range(20)])
ch_clump = rel_change(cat_agg(P_clump), g_cat)
print(f'\\n拼接 [max, mean]: 丢一半点 {ch_drop:.4f}（max {drop[0.5]["max"]:.4f} / '
      f'mean {drop[0.5]["mean"]:.4f}）')
print(f'                  一半聚簇 {ch_clump:.4f}（max {clump["max"]:.4f} / '
      f'mean {clump["mean"]:.4f}）')
assert abs(ch_drop - drop[0.5]['max']) < abs(ch_drop - drop[0.5]['mean']), \\
    '拼接的行为应当更靠近 max'
nm, nn = np.linalg.norm(pointnet(P,'max')), np.linalg.norm(pointnet(P,'mean'))
print(f'原因：max 的范数是 mean 的 {nm/nn:.1f} 倍，所以相对变化被它主导')
print('✅ 要真正兼得必须先各自归一化 —— 而那引入一个新超参数')"""),

    md("""## 3 · 临界点集：本模块的核心"""),

    code("""def critical_set(P, W=W, B=B):
    '''返回决定 max-pool 输出的点的下标（去重）。'''
    F = pointwise(P, W, B)
    return np.unique(F.argmax(0))

crit = critical_set(P)
F_all = pointwise(P)
g = F_all.max(0)

# 两种「只用临界点」的算法，而它们的数值行为不同：
g_select = F_all[crit].max(0)                 # ① 从**同一个** F 里选
g_recomp = pointwise(P[crit]).max(0)          # ② **重算**子集的特征再取 max

print(f'N={N}, D={D}: 临界点 {len(crit)} 个（{100*len(crit)/N:.2f}%），'
      f'上界 min(D,N)={min(D,N)}')
print(f'  ① 从同一个 F 里选：最大逐位差 = {np.abs(g - g_select).max():.3e}')
print(f'  ② 重算子集特征  ：最大逐位差 = {np.abs(g - g_recomp).max():.3e}')
assert len(crit) <= min(D, N), '临界点数不可能超过 min(D, N)'
assert np.abs(g - g_select).max() == 0.0, '①「选择」是恒等式，必须逐位相等'
EPS = np.finfo(np.float64).eps
assert np.abs(g - g_recomp).max() <= 8 * EPS, '②「重算」只保证到几个 ULP'
print(f'\\n✅ 删掉其余 {N - len(crit)} 个点（{100*(N-len(crit))/N:.1f}%），输出不变')
print('   但要区分两件事：')
print('   ① **从同一个特征矩阵里选** —— 逐位相等，这是恒等式')
print('   ② **重算子集的特征** —— 只保证到几个 ULP')
print('      因为 BLAS 对不同形状的矩阵乘用不同的分块/向量化路径')
print('      （本课在 N=128, D=16 上量到 2ε 的差）')
print('   → **「逐位相等」的断言必须说清「重算了什么」**')

# 临界点数不随 N 增长
print(f\"\\n{'N':>7s} {'D':>5s} {'临界点数':>9s} {'占 N 的比例':>12s}\")
sizes = {}
for n in [256, 1024, 4096, 16384]:
    for d in [64, 256]:
        Wd, Bd = make_mlp(3, d, seed=6)
        Q = np.random.default_rng(5).normal(size=(n, 3))
        c = len(np.unique(pointwise(Q, Wd, Bd).argmax(0)))
        sizes[(n, d)] = c
        print(f'{n:7d} {d:5d} {c:9d} {100*c/n:11.2f}%')

# N 涨 64 倍，临界点数几乎不动
assert sizes[(16384, 64)] < 3 * sizes[(256, 64)], \\
    f'N 涨 64 倍，临界点数不该按比例涨（{sizes[(256,64)]} -> {sizes[(16384,64)]}）'
assert 100 * sizes[(16384, 64)] / 16384 < 1.0
print(f'\\n✅ N 从 256 到 16384（64 倍），临界点数 '
      f'{sizes[(256,64)]} → {sizes[(16384,64)]}（几乎不动）')
print(f'   占比从 {100*sizes[(256,64)]/256:.2f}% 掉到 '
      f'{100*sizes[(16384,64)]/16384:.2f}%')
print('   → **全局 max-pool 只「看到」几十个极值点，与输入点数无关**')
print('   → 这同时解释了「对点丢失鲁棒」与「抓不住细节」两件事')"""),

    md("""## 4 · 单点删除实验：$\\max$ 与 $\\sum$ 的信息结构"""),

    code("""for kind in ['max', 'sum']:
    g0 = pointnet(P, kind)
    unchanged, min_ch = 0, np.inf
    for i in range(N):
        keep = np.ones(N, bool); keep[i] = False
        d = float(np.abs(pointnet(P[keep], kind) - g0).max())
        if d == 0.0:
            unchanged += 1
        min_ch = min(min_ch, d)
    print(f'{kind:>5s}: 删掉单点后输出**完全不变**的点数 = {unchanged}/{N}'
          f'   最小变化量 = {min_ch:.3e}')
    if kind == 'max':
        assert unchanged == N - len(crit), \\
            f'不变的点数应当恰好等于 N − |临界集| = {N - len(crit)}'
    else:
        assert unchanged == 0 and min_ch > 0.1

print(f'\\n✅ max: {N-len(crit)}/{N} 个点可删除（= N − |临界集|，精确吻合）')
print('   sum: 0/1024 —— 每一个点都影响输出')
print('   → max 把点集压成「若干极值点」，sum 压成「所有点的总量」')
print('   → 而点云里「点数」主要由距离决定（模块 01），所以它是**噪声**')
print('     于是「丢弃点数信息」从缺点变成了优点')"""),

    md("""## 5 · 置换不变 ≠ 旋转不变"""),

    code("""def rot_z(deg):
    t = np.deg2rad(deg); c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])

g0 = pointnet(P, 'max')
crit0 = set(critical_set(P).tolist())
print(f\"{'绕 z 旋转':>10s} {'全局特征相对变化':>18s} {'临界点集变了几个点':>20s}\")
for deg in [0, 5, 15, 45, 90, 180]:
    Q = P @ rot_z(deg).T
    ch = rel_change(pointnet(Q, 'max'), g0)
    c = set(critical_set(Q).tolist())
    print(f'{deg:9d}° {ch:17.4f} {len(crit0 ^ c):19d}')
    if deg == 0:
        assert ch == 0.0 and len(crit0 ^ c) == 0

ch15 = rel_change(pointnet(P @ rot_z(15).T, 'max'), g0)
assert ch15 > 0.03, f'15° 旋转应当明显改变输出，实测 {ch15:.4f}'
print(f'\\n✅ 15° 旋转就让全局特征变 {ch15:.1%} —— **PointNet 不是旋转不变的**')
print('   而在自动驾驶里通常不需要 T-Net：外参已经把点云摆正了（C72）')
print('   → 不变性来自结构（免费、可靠）比来自数据（要学、可能失效）更好')"""),

    md("""## 5b · 分割头的数学上界

全局特征对所有点是**同一个**向量，所以它无法区分任何两个点。
**于是逐点判别力全部来自 $h(x_i)$，而 $h$ 看不到邻域。**"""),

    code("""def seg_features(P, W=W, B=B):
    '''PointNet 分割头的输入：[逐点特征 || 全局特征]。'''
    F = pointwise(P, W, B)
    g = F.max(0)
    return np.concatenate([F, np.broadcast_to(g, (len(F), len(g)))], axis=1)

# 构造两个坐标完全相同、但邻域截然不同的点
TARGET = np.array([0.5, -0.2, 1.1])
scene_a = np.vstack([TARGET, rng.normal(size=(200, 3))])                    # 稀疏邻域
scene_b = np.vstack([TARGET,
                     TARGET + rng.normal(scale=0.02, size=(200, 3))])       # 密集邻域

fa, fb = seg_features(scene_a)[0], seg_features(scene_b)[0]
print(f'同一个坐标 {TARGET}，两种截然不同的邻域：')
print(f'  逐点特征部分（前 {D} 维）最大逐位差 = {np.abs(fa[:D]-fb[:D]).max():.3e}')
print(f'  全局特征部分（后 {D} 维）最大逐位差 = {np.abs(fa[D:]-fb[D:]).max():.3e}')
assert np.abs(fa[:D] - fb[:D]).max() == 0.0, \\
    '逐点特征只依赖坐标，必须**逐位相等**'
assert np.abs(fa[D:] - fb[D:]).max() > 0.0, '而全局特征会变（场景不同）'
print('\\n✅ **逐点特征逐位相等** —— 邻域信息完全没有进入')
print('   所以 PointNet 的分割是「逐点分类 + 一个全局偏置」：')
print('   它能学「这个高度的点通常是标志」，学不到「周围有平面所以是地面」')

# 全局特征对所有点相同 -> 它不能区分点
S = seg_features(P)
assert np.allclose(S[:, D:], S[0, D:]), '全局特征那一半对所有点必须完全相同'
print(f'\\n拼接后的维度: 逐点 {D} + 全局 {D} = {S.shape[1]}')
for d_local, d_global in [(64, 1024), (128, 1024)]:
    print(f'  常见配置 h={d_local}, g={d_global}: '
          f'**{100*d_global/(d_local+d_global):.0f}% 的维度对所有点相同**')
print('   → 这解释了为什么 PointNet 的分割对场景整体变化很敏感')"""),

    md("""## 6 · 小结

| 结论 | 数值 |
|---|---|
| 置换不变 | **max/min 逐位差恰好 0.0**；sum/mean 只到 1.43e-15（≈6ε） |
| $\\sum$ 对点数的敏感性 | 相对变化 ≈ $1-$ 保留比例（50% 丢点 → 0.498） |
| 两种扰动的排序**相反** | 点数变：mean 最稳；密度变：**max 最稳** |
| 线性探针 | $\\sum$ 的 $R^2$ **1.0000** · $\\max$ **0.7578** · mean **0.1465** |
| 拼接 $[\\max,\\text{mean}]$ | 不是兼得，而是被范数大的一半支配（46.9 vs 6.3） |
| **临界点集** | $N{=}1024,D{=}64$ → **24 个点**；删掉其余 1000 个**逐位不变** |
| 临界点数与 $N$ 无关 | $N$ 涨 64 倍，它从 16 → 24；占比 6.25% → **0.15%** |
| 单点删除 | max **1000/1024** 无影响；sum **0/1024** |
| 旋转 | 15° 就让全局特征变 **7.4%** |
| 分割头 | 坐标相同 → 逐点特征**逐位相等**（邻域信息进不来） |""") ,

    # ─────────────────────────────── 练习 1
    md("""## ✏️ 练习 1：对称性检查器

实现 `is_symmetric(agg_fn, n=64, d=8, trials=20, seed=0)`：
给一个作用在 `(N,D)` 特征矩阵上、返回一维向量的函数，
判断它是否置换不变。返回 `(bool, 最大逐位差)`。

要求用**恰好相等**判定。

> 注意：这会让 `sum` / `mean` / `cumsum-last` **判为不对称**——
> 而那是正确的行为。它们在<em>数学上</em>对称，但在浮点下不是逐位不变的
> （第 1 节量到相对差 1.43e-15）。
> **所以这个检查器测的是「逐位置换不变」，它对 max 型模型才是合适的判据。**"""),

    code("""def is_symmetric(agg_fn, n=64, d=8, trials=20, seed=0):
    \"\"\"返回 (是否置换不变, 最大逐位差)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
CANDIDATES = {
    'max':        lambda F: F.max(0),
    'sum':        lambda F: F.sum(0),
    'mean':       lambda F: F.mean(0),
    'min':        lambda F: F.min(0),
    'max+mean':   lambda F: np.concatenate([F.max(0), F.mean(0)]),
    'sorted-top3':lambda F: np.sort(F, axis=0)[-3:].ravel(),
    'first-8':    lambda F: F[:8].ravel(),          # ❌ 不对称
    'cumsum-last':lambda F: np.cumsum(F, axis=0)[-1],
    'diff-first-last': lambda F: F[0] - F[-1],      # ❌ 不对称
}
print(f\"{'候选':>18s} {'置换不变':>9s} {'最大逐位差':>12s}\")
res = {}
for name, fn in CANDIDATES.items():
    ok, dev = is_symmetric(fn)
    res[name] = ok
    print(f'{name:>18s} {str(ok):>9s} {dev:12.3e}')

# 选择型（无算术）-> 逐位不变
assert res['max'] and res['min'], 'max/min 是选择操作，必须逐位不变'
assert res['sorted-top3'], '排序后取 top-k 也是选择操作（Deep Sets 里常用的一族）'
# 算术型 -> 数学上对称但**不逐位**不变
assert not res['sum'], 'sum 在浮点下不逐位不变（第 1 节：相对差 1.43e-15）'
assert not res['mean'], 'mean 同理'
assert not res['cumsum-last'], 'cumsum 的最后一项数学上等于 sum，浮点下同样不逐位'
# 真正不对称的
assert not res['first-8'] and not res['diff-first-last']
# 拼接：max+mean 里含 mean，所以整体也不逐位不变
assert not res['max+mean'], '拼接里只要含算术型聚合，整体就不逐位不变'
print('\\n✅ 练习 1 通过。而这个检查器把候选分成了三类，而不是两类：')
print('   ① **选择型**（max / min / sorted-top-k）—— 逐位置换不变')
print('   ② **算术型**（sum / mean / cumsum）—— 数学上对称，浮点下不逐位')
print('   ③ **不对称**（first-8 / diff-first-last）—— 差是 O(1)，与浮点无关')
print('   区分 ② 与 ③ 要看差的**量级**：1e-15 是数值噪声，1e-1 是逻辑错误')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def is_symmetric(agg_fn, n=64, d=8, trials=20, seed=0):
    r = np.random.default_rng(seed)
    F = r.normal(size=(n, d))
    ref = np.asarray(agg_fn(F), float)
    worst = 0.0
    for t in range(trials):
        perm = np.random.default_rng(seed + 1 + t).permutation(n)
        got = np.asarray(agg_fn(F[perm]), float)
        if got.shape != ref.shape:
            return False, float('inf')
        worst = max(worst, float(np.abs(got - ref).max()))
    return bool(worst == 0.0), worst

assert is_symmetric(lambda F: F.max(0))[0]
assert not is_symmetric(lambda F: F[:8].ravel())[0]
print('✅ 参考答案 1 通过')
print('   用「恰好 0」而不是「< 1e-9」：真正的对称函数在浮点下也是逐位相同的，')
print('   因为它对同一批数做同一批运算 —— 只有顺序变了，而这三种运算与顺序无关。')
print('   （注意 sum 也成立：numpy 的 add.reduce 对同一批数给同一结果。）')"""),

    # ─────────────────────────────── 练习 2
    md("""## ✏️ 练习 2：临界点集分析器

实现 `critical_analysis(P, W, B)`，返回 dict：

- `'idx'` —— 临界点下标（升序去重）
- `'size'`, `'frac'` —— 大小与占比
- `'upper_bound'` —— $\\min(D, N)$
- `'exact_select'` —— bool：从**同一个**特征矩阵里选临界点，输出是否逐位相等
  （**这是恒等式，必须为真**）
- `'exact_recompute'` —— bool：**重算**子集的特征再取 max，是否逐位相等
  （<em>不保证</em>——BLAS 对不同形状用不同路径）
- `'recompute_ulp'` —— 重算路径的最大差，以 $\\varepsilon$ 为单位
- `'deletable'` —— 删掉任意单点后输出不变的点数
- `'consistent'` —— bool：`deletable == N - size`（**这是一个可验证的恒等式**）"""),

    code("""def critical_analysis(P, W, B):
    \"\"\"返回 dict(idx, size, frac, upper_bound, exact_select,
    exact_recompute, recompute_ulp, deletable, consistent)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
for n, d in [(128, 16), (512, 64), (1024, 64)]:
    Wd, Bd = make_mlp(3, d, seed=11)
    Q = np.random.default_rng(12).normal(size=(n, 3))
    a = critical_analysis(Q, Wd, Bd)
    assert set(a) == {'idx', 'size', 'frac', 'upper_bound', 'exact_select',
                      'exact_recompute', 'recompute_ulp', 'deletable',
                      'consistent'}
    assert a['size'] <= a['upper_bound'] == min(d, n)
    assert a['exact_select'] is True, '「选择」是恒等式，必须逐位相等'
    assert a['recompute_ulp'] < 8.0, \\
        f"重算路径的差应当只有几个 ULP，实测 {a['recompute_ulp']:.1f}ε"
    assert a['consistent'] is True, \\
        f"deletable({a['deletable']}) 必须等于 N−size({n - a['size']})"
    print(f'N={n:5d} D={d:4d}: 临界点 {a["size"]:3d}（{a["frac"]:6.2%}）'
          f' 选择逐位 {str(a["exact_select"]):5s} 重算逐位 '
          f'{str(a["exact_recompute"]):5s}（{a["recompute_ulp"]:.1f}ε）'
          f' 可删除 {a["deletable"]:5d}')

# 占比随 N 下降
fr = []
for n in [128, 512, 2048, 8192]:
    Wd, Bd = make_mlp(3, 64, seed=11)
    Q = np.random.default_rng(12).normal(size=(n, 3))
    fr.append(critical_analysis(Q, Wd, Bd)['frac'])
print(f'\\n占比随 N: ' + ' → '.join(f'{f:.2%}' for f in fr))
assert fr == sorted(fr, reverse=True), '占比必须随 N 单调下降'
assert fr[-1] < fr[0] / 10, '涨 64 倍点数，占比应当降一个数量级以上'
print('✅ 练习 2 通过。两个结论：')
print('   ① **deletable == N − |临界集|** 是一个恒等式（一个点可删除 ⟺ 它不是任何一维的 argmax）')
print('   ② 「选择」逐位相等，而「重算」只到几个 ULP —— '
      'BLAS 对不同形状用不同路径')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def critical_analysis(P, W, B):
    P = np.asarray(P, float)
    F = pointwise(P, W, B)
    g = F.max(0)
    idx = np.unique(F.argmax(0))
    # ① 选择：从同一个 F 里取，这是恒等式
    sel_dev = float(np.abs(F[idx].max(0) - g).max())
    # ② 重算：BLAS 对不同形状可能走不同路径
    rec_dev = float(np.abs(pointwise(P[idx], W, B).max(0) - g).max())
    # 可删除性也用「选择」口径判定，才是恒等式
    deletable = 0
    for i in range(len(P)):
        keep = np.ones(len(P), bool); keep[i] = False
        if np.abs(F[keep].max(0) - g).max() == 0.0:
            deletable += 1
    eps = np.finfo(np.float64).eps
    return {'idx': idx, 'size': int(len(idx)), 'frac': float(len(idx)/len(P)),
            'upper_bound': int(min(F.shape[1], len(P))),
            'exact_select': bool(sel_dev == 0.0),
            'exact_recompute': bool(rec_dev == 0.0),
            'recompute_ulp': float(rec_dev / eps),
            'deletable': int(deletable),
            'consistent': bool(deletable == len(P) - len(idx))}

a = critical_analysis(P, W, B)
assert a['exact_select'] and a['consistent']
print(f'✅ 参考答案 2 通过（临界点 {a["size"]}，可删除 {a["deletable"]}，'
      f'N−size = {len(P)-a["size"]}）')
print('   两个实现细节：')
print('   ① `deletable` 必须用「从同一个 F 里选」来判 —— 用「重算」会被 ULP 噪声污染；')
print('   ② 所以恒等式 deletable == N−size 只在「选择」口径下严格成立。')"""),

    # ─────────────────────────────── 练习 3
    md("""## ✏️ 练习 3：聚合函数的信息探针

实现 `agg_probe(agg_name, quantity, Ns=..., trials=20)`，
用线性探针量「聚合特征里能读出多少某个量」。
`quantity` 取 `'count'`（点数）或 `'scale'`（点云的整体尺度，用坐标标准差）。

返回 `(R², MAE)`。然后用它验证：

- `'count'`：$\\sum$ 的 $R^2 \\approx 1$、mean 的 $R^2$ 很低
- `'scale'`：**三种聚合都能读出尺度**（因为 $h$ 是逐点的、尺度直接进特征）"""),

    code("""def agg_probe(agg_name, quantity, Ns=(256, 512, 1024), scales=(0.5, 1.0, 2.0),
              trials=20):
    \"\"\"返回 (R², MAE)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
print(f\"{'聚合':>6s} {'读点数 R²':>11s} {'读尺度 R²':>11s}\")
tab = {}
for kind in ['max', 'sum', 'mean']:
    r2c, _ = agg_probe(kind, 'count')
    r2s, _ = agg_probe(kind, 'scale')
    tab[kind] = (r2c, r2s)
    print(f'{kind:>6s} {r2c:11.4f} {r2s:11.4f}')

# ① 点数：sum 高、mean 低
assert tab['sum'][0] > 0.9, tab['sum'][0]
assert tab['mean'][0] < tab['sum'][0], '(mean 应当比 sum 更难读出点数)'

# ② 尺度：三种都能读出（因为逐点 MLP 直接吃坐标）
for kind in ['max', 'sum', 'mean']:
    assert tab[kind][1] > 0.5, f'{kind} 应当能读出尺度，实测 {tab[kind][1]:.3f}'
print('\\n✅ 练习 3 通过：')
print('   **点数**是聚合方式的函数（sum 保留、mean 丢弃）；')
print('   **尺度**是逐点 MLP 就能编码的量，所以三种聚合都读得出。')
print('   → 所以「换聚合函数」影响的是<集合级>的量，不是<点级>的量')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def agg_probe(agg_name, quantity, Ns=(256, 512, 1024), scales=(0.5, 1.0, 2.0),
              trials=20):
    X, Y = [], []
    for t in range(trials):
        for n in Ns:
            for sc in scales:
                Q = np.random.default_rng(7000 + t*97 + n + int(sc*10)).normal(
                    scale=sc, size=(n, 3))
                X.append(aggregate(pointwise(Q), agg_name))
                Y.append(float(n) if quantity == 'count'
                         else float(Q.std()))
    A = np.column_stack([np.array(X), np.ones(len(X))])
    Y = np.array(Y)
    w, *_ = np.linalg.lstsq(A, Y, rcond=None)
    pred = A @ w
    r2 = 1 - ((Y - pred)**2).sum() / ((Y - Y.mean())**2).sum()
    return float(r2), float(np.abs(Y - pred).mean())

assert agg_probe('sum', 'count')[0] > 0.9
assert agg_probe('mean', 'scale')[0] > 0.5
print('✅ 参考答案 3 通过')
print('   注意训练集里必须同时变 N 与 scale —— 否则两个量相关，探针分不开它们。')
print('   （这与 C10 的「混淆因子」是同一个问题：探针也需要正确的实验设计。）')"""),

    # ─────────────────────────────── 练习 4
    md("""## ✏️ 练习 4：分割头的上界检查

实现 `seg_head_audit(target, scene_a, scene_b, W, B)`：
给同一个坐标 `target` 与两个不同的场景，返回 dict：

- `'local_identical'` —— bool：逐点特征是否**逐位相等**
- `'global_differs'` —— bool：全局特征是否不同
- `'global_shared'` —— bool：同一场景内全局特征对所有点是否相同
- `'global_frac'` —— 拼接后「对所有点相同」的维度占比

这三个 bool 全为真，就证明了「PointNet 的分割头无法使用局部结构」。"""),

    code("""def seg_head_audit(target, scene_a, scene_b, W, B):
    \"\"\"返回 dict(local_identical, global_differs, global_shared, global_frac)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
TGT = np.array([0.5, -0.2, 1.1])
r4 = np.random.default_rng(21)
SA = np.vstack([TGT, r4.normal(size=(200, 3))])                       # 稀疏邻域
SB = np.vstack([TGT, TGT + r4.normal(scale=0.02, size=(200, 3))])     # 密集邻域
SC = np.vstack([TGT, TGT + r4.normal(scale=0.5, size=(200, 3))])      # 中等邻域

a = seg_head_audit(TGT, SA, SB, W, B)
assert set(a) == {'local_identical', 'global_differs', 'global_shared',
                  'global_frac'}
print('稀疏邻域 vs 密集邻域（同一个坐标）:')
for k, v in a.items():
    print(f'  {k:18s} = {v}')

assert a['local_identical'] is True, '逐点特征只依赖坐标 —— 必须逐位相等'
assert a['global_differs'] is True, '而全局特征会变（场景不同）'
assert a['global_shared'] is True, '同一场景内，全局特征对所有点相同'
assert abs(a['global_frac'] - 0.5) < 1e-12, f'D+D 拼接时应为 50%'

# 换第三个场景，结论不变
b = seg_head_audit(TGT, SA, SC, W, B)
assert b['local_identical'] is True and b['global_differs'] is True

print('\\n三个 bool 全为真 -> **PointNet 的分割头在数学上无法使用局部结构**')
print('   它只能做「逐点分类 + 一个全局偏置」')
print('\\n常见配置下「对所有点相同」的维度占比：')
for dl, dg in [(64, 1024), (128, 1024), (64, 64)]:
    print(f'   h={dl:4d}, g={dg:4d} -> {dg/(dl+dg):6.1%}')
print('✅ 练习 4 通过：这就是 PointNet++ 的分层聚合要补的那个能力')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def seg_head_audit(target, scene_a, scene_b, W, B):
    def feats(scene):
        F = pointwise(scene, W, B)
        g = F.max(0)
        return F, g
    Fa, ga = feats(np.asarray(scene_a, float))
    Fb, gb = feats(np.asarray(scene_b, float))
    # target 是每个场景的第 0 个点
    local_same = bool(np.abs(Fa[0] - Fb[0]).max() == 0.0)
    global_diff = bool(np.abs(ga - gb).max() > 0.0)
    # 同一场景内，全局那一半对所有点相同
    S = np.concatenate([Fa, np.broadcast_to(ga, (len(Fa), len(ga)))], axis=1)
    d_local = Fa.shape[1]
    shared = bool(np.allclose(S[:, d_local:], S[0, d_local:]))
    return {'local_identical': local_same, 'global_differs': global_diff,
            'global_shared': shared,
            'global_frac': float(len(ga) / (d_local + len(ga)))}

a = seg_head_audit(TGT, SA, SB, W, B)
assert a['local_identical'] and a['global_differs'] and a['global_shared']
print('✅ 参考答案 4 通过')
print('   这三条一起构成一个**不可能性证明**：')
print('   全局那一半对所有点相同（不能区分点）+ 逐点那一半只看坐标（不含邻域）')
print('   ⇒ 任何依赖局部结构的判别都做不到。而这与权重取值无关。')"""),

    # ─────────────────────────────── 胶囊
    md("""## 🧪 真实工程胶囊

```python
# ── 1) PyTorch 里的 PointNet 骨架（本课的 numpy 版本对应这几行）──
class PointNetEncoder(nn.Module):
    def __init__(self, d=1024):
        super().__init__()
        self.mlp = nn.Sequential(                 # ← 逐点：用 Conv1d(kernel=1) 实现
            nn.Conv1d(3, 64, 1), nn.BatchNorm1d(64), nn.ReLU(),
            nn.Conv1d(64, 128, 1), nn.BatchNorm1d(128), nn.ReLU(),
            nn.Conv1d(128, d, 1), nn.BatchNorm1d(d), nn.ReLU())
    def forward(self, x):                          # x: (B, 3, N)
        f = self.mlp(x)                            # (B, d, N)
        return f.max(dim=2).values, f              # ← 全局特征 + 逐点特征
#   ⚠️ Conv1d(kernel_size=1) 就是「逐点 MLP」——这是保证置换不变的关键写法。
#      任何 kernel_size > 1 都会引入顺序依赖，而它不会报错（只会静默地破坏不变性）。

# ── 2) 临界点集：一行就能算，而且它是免费的诊断 ──
with torch.no_grad():
    _, f = enc(x)                                  # (B, d, N)
    crit = f.argmax(dim=2).unique(dim=-1)          # 每个通道的 argmax
print(f'临界点 {crit.numel()} / {x.shape[-1]}')
#   ↑ 用它回答「我把输入点数翻倍到底有没有用」——如果临界点数没变，就没用

# ── 3) 自动驾驶里不要加 T-Net ──
#   点云已经被外参摆正（C72），所以学一个 3×3 对齐只会引入分布外风险。
#   MMDetection3D 的 PointNet++ backbone 默认就没有 T-Net。

# ── 4) 分组用球查询而不是 kNN（第 6 节）──
from mmcv.ops import ball_query, knn
idx = ball_query(0.0, 0.8, 32, xyz, new_xyz)       # min_r, max_r, K
#   ⚠️ 稀疏区凑不满 K 个时会重复第一个点（padding），
#      所以组内特征里会有重复 —— 而 max-pool 恰好对重复免疫（第 4 节）。
#      这是一个「架构选择恰好兼容工程妥协」的例子，而它不是巧合：
#      球查询与 max-pool 是一起被设计出来的。
```

> **落地顺序建议**：先算一次临界点集（一行，立刻告诉你「加点数有没有用」），
> 再检查你的逐点 MLP 是否真的是 `kernel_size=1`（这是静默破坏不变性的头号写法），
> 最后才考虑换聚合函数——而换之前先用练习 3 的探针确认你想保留/丢弃的是哪个量。"""),
]
