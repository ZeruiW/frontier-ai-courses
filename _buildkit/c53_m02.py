# -*- coding: utf-8 -*-
"""C53 模块 02 · 标签分配：检测器真正的胜负手。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（YOLO 演进、anchor-free、解耦头）；C18 的 IoU / NMS 基础"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_label_assignment.ipynb（纯 numpy 从零实现 ATSS / SimOTA / TaskAligned）'),
    ("核心参考", "ATSS (CVPR20) · OTA (CVPR21) · YOLOX 的 SimOTA · TOOD (ICCV21) · RTMDet 的 DynamicSoftLabelAssigner"),
    ("预计时长", "读 70 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("what", "标签分配：训练开始前的那一步，决定了训练的一切", "".join([
        P("一个检测器在每张图上会吐出成千上万个预测单元——本课的合成设定里是 640×640 输入、stride 8/16/32 三层 FPN，一共 <code>80²+40²+20² = 8400</code> 个格点。而这张图里可能只有 5 个真实目标。<strong>「哪些格点该学成前景、学哪个 GT、哪些该学成背景」——这个决定就叫 <span class=\"term\">label assignment</span>（标签分配）</strong>。它发生在算损失<em>之前</em>，不参与反向传播，却决定了每一步梯度长什么样。"),
        DUAL(
            "分配是<strong>唯一一个「不产生任何参数、却能决定几个点 AP」的环节</strong>。backbone 换一个更大的、neck 加一层 BiFPN，收益通常在 0.5–1 AP；而把 MaxIoU 换成 SimOTA，在 YOLOX 的消融里是 <strong>+2.3 AP</strong>（44.6 → 47.3，YOLOX-L）。原因很直白：<em>分配决定了训练信号的分布本身</em>——你告诉模型「这个位置是正的」，模型就往那个方向走；分配错了，再大的模型也只是把错误学得更牢。",
            "更精确地说：分配定义了损失函数的<strong>作用域</strong>。设格点集合 $A$、真值集合 $G$，分配是一个映射 $\\pi: A \\to G \\cup \\{\\varnothing\\}$。分类损失对所有 $a \\in A$ 计算（正样本目标为 $\\pi(a)$ 的类别，负样本目标为背景），<em>回归损失只对 $\\pi(a) \\neq \\varnothing$ 的格点计算</em>。所以 $\\pi$ 同时决定了：① 正负样本比例（前景-背景不平衡的直接来源）；② 每个 GT 得到多少监督（尺度间的公平性）；③ 回归损失看到的样本分布（决定回归头学到的先验）。<strong>这三件事都不是超参数能补救的。</strong>",
        ),
        ASCII("""一张图的训练信号是怎么来的（分配在最前面）

  图像 ──► backbone ──► neck ──► head ──► 8400 个格点的 (cls, box)
                                              │
                                              ▼
   GT (5 个框) ────────────────────► 【标签分配 π】 ◄── 有时也看预测本身
                                              │           (SimOTA/TaskAligned)
                    ┌─────────────────────────┼──────────────────────┐
                    ▼                         ▼                      ▼
              正样本 (~40 个)            忽略样本 (~0-200)        负样本 (~8300)
              cls=对应类别               不算任何损失             cls=背景
              box=回归到该 GT                                     无 box 损失

  ⇒ 分配 π 一变，上面三个集合全变，梯度的方向与量级全变。
  ⇒ 它不含任何可学参数，却是「同一个网络能不能训出来」的分水岭。"""),
        CALLOUT("intuition", "记住一句话：<strong>网络结构决定了「模型能表达什么」，标签分配决定了「模型实际学到什么」</strong>。<em>面试里如果只会说「我换了个更强的 backbone」，深度就止步于此；能把分配讲清楚的人，面试官会立刻认为你真的调过检测器。</em>"),
    ])),

    ("static", "静态分配：固定 IoU 阈值的三个致命问题", "".join([
        P("<span class=\"term\">static assignment</span>（静态分配）指的是：<strong>分配规则只看 anchor 与 GT 的几何关系，不看模型当前的预测</strong>。Faster R-CNN / SSD / RetinaNet 全是这一套——「IoU ≥ 0.5 为正，&lt; 0.4 为负，中间忽略；此外每个 GT 强制认领它 IoU 最高的那个 anchor」。它简单、可复现、与训练进度无关，也正因如此，它有三个绕不过去的问题。"),
        TABLE(["问题", "机理", "在本课合成实验里的实测", "谁来解"], [
            ["<strong>① 阈值对尺度不公平</strong>",
             "IoU 上界由 <code>min(A_gt,A_anc)/max(A_gt,A_anc)</code> 决定。GT 尺寸与 anchor 尺寸差得多，IoU 天花板就低于阈值",
             "16×16 的标志对 32/64/128 三档 anchor 的<strong>理论最大 IoU 只有 0.25 / 0.063 / 0.016</strong>，全部低于 0.5 —— 它<em>永远</em>拿不到一个正样本",
             "ATSS 的自适应阈值"],
            ["<strong>② 正样本数量与尺度强相关</strong>",
             "大目标覆盖的 anchor 多、IoU 高的也多；小目标只能靠「强制认领」拿到 1 个",
             "MaxIoU 全图只给出 <strong>6 个正样本</strong>（正负比 1:1400），4 个 GT 各只有 1 个；其中 16/18px 那两个<em>完全靠兜底规则硬塞</em>，塞进来的 anchor IoU 只有 0.25 / 0.32",
             "SimOTA 的 dynamic-k"],
            ["<strong>③ 与预测质量脱钩</strong>",
             "几何上最匹配的 anchor，未必是当前模型预测得最好的那个；模型被迫在一个它学不动的位置上硬学",
             "MaxIoU 正样本的<strong>预测框平均 IoU 只有 0.808</strong>，而 TaskAligned 选出的是 0.885",
             "OTA / TaskAligned"],
        ]),
        MATH("\\text{IoU}_{\\max}(\\text{gt}, \\text{anchor}) \\;=\\; \\frac{\\min(A_{gt}, A_{anc})}{\\max(A_{gt}, A_{anc})} \\quad\\Longrightarrow\\quad \\text{IoU} \\ge \\tau \\iff \\sqrt{\\tau}\\, s \\;\\le\\; L_{gt} \\;\\le\\; \\frac{s}{\\sqrt{\\tau}}"),
        P("上式里 $s$ 是 anchor 边长、$L_{gt}$ 是 GT 边长（同宽高比、同心的理想情况）。代入 $\\tau=0.5$、$s=32$：<strong>只有边长落在 [22.6, 45.3] 这个窄带里的目标才可能被 IoU 0.5 匹配上</strong>。这不是一个「小目标稍微吃亏」的问题——<em>它是一道硬门：门外的目标，正样本数恒等于兜底给的那 1 个</em>。"),
        DUAL(
            "很多人以为「小目标难检」是因为像素少、信息不够。<strong>信息不足是原因之一，但在静态分配下，更直接的原因是它<em>根本没有得到训练信号</em></strong>。一个 16 像素的限速牌，整张图 8400 个格点里只有 1 个被标成正样本，回归损失就只在这一个位置算——<em>而同一张图里 96 像素的指示牌可能有十几个正样本</em>。梯度的量级差了一个数量级，模型自然优先学会大目标。",
            "严格说，这是<strong>正样本数量随尺度的系统性偏斜</strong>，它同时污染分类与回归两条支路：分类支路上，小目标类别的正样本极少，等价于人为制造了一个类别不平衡（哪怕数据集里各类样本数一样多）；回归支路上，回归头见到的框尺寸分布被严重偏向大框，<em>学到的回归先验对小框是失配的</em>。<strong>「强制认领最大 IoU 的 anchor」这个兜底规则救不了它</strong>——恰恰相反，它把一个 IoU 只有 0.25 的低质量 anchor 也标成正样本，逼着模型在一个几乎没有目标信息的位置上做回归，<em>引入的是噪声监督</em>。",
        ),
        CALLOUT("danger", "面试高频陷阱：<strong>「为什么小目标 AP 低？」如果只答「分辨率不够、下采样丢信息」，只答了一半。</strong> 完整答案要包含：① IoU 对小框的位移极敏感（8×8 的框偏 2 px，IoU 从 1.0 掉到 0.39）；② <strong>因此固定 IoU 阈值对小目标是系统性歧视，正样本数量极度稀缺</strong>；③ 所以解法有两条独立的路——改架构（P2 层、高分辨率）和<strong>改分配</strong>（ATSS/SimOTA/NWD）。<em>能把「分配」这条路讲出来，是区分「读过论文」和「真的训过小目标检测器」的分水岭。</em>"),
    ])),

    ("atss", "ATSS：让阈值自己从数据里长出来", "".join([
        P("<span class=\"term\">ATSS</span>（Adaptive Training Sample Selection, CVPR 2020）的出发点是一个漂亮的观察实验：把 RetinaNet（anchor-based）和 FCOS（anchor-free）的所有差异逐条对齐后，<strong>唯一还剩下的、真正造成 AP 差距的因素，就是正负样本的选择方式</strong>。anchor 有没有、有几个，都不是关键。"),
        P("ATSS 的规则只有四步，且<strong>没有任何需要手调的 IoU 阈值</strong>："),
        OL([
            "对每个 GT，在<strong>每一层 FPN</strong> 上按「anchor 中心到 GT 中心的 L2 距离」取最近的 <code>k=9</code> 个 anchor，合并成候选集 $\\Omega_g$（三层就是 27 个）。",
            "计算候选集里每个 anchor 与该 GT 的 IoU，得到 $\\{u_i\\}_{i \\in \\Omega_g}$。",
            "<strong>阈值 = 这组 IoU 的均值 + 标准差</strong>：$t_g = m_g + v_g$。",
            "候选集中 IoU ≥ $t_g$ <strong>且中心落在 GT 框内</strong>的 anchor 为正样本；一个 anchor 被多个 GT 选中时，归给 IoU 最大的那个。",
        ]),
        MATH("t_g \\;=\\; m_g + v_g, \\qquad m_g = \\frac{1}{|\\Omega_g|}\\sum_{i \\in \\Omega_g} u_i, \\qquad v_g = \\sqrt{\\frac{1}{|\\Omega_g|-1}\\sum_{i \\in \\Omega_g} (u_i - m_g)^2}"),
        DUAL(
            "为什么 <strong>均值 + 标准差</strong> 这么朴素的统计量管用？因为它把「多好算好」变成了<strong>相对判断</strong>：均值代表「这个 GT 在当前 anchor 配置下大致能匹配到什么程度」，标准差代表「候选集里质量的分散程度」。<em>标准差大 → 说明有一层特别匹配，阈值抬高，只选那一层；标准差小 → 说明各层都差不多，阈值降低，多选一些</em>。<strong>于是「该用哪一层」和「该选几个」这两件原本要手工设计的事，被同一个公式自动解决了。</strong>",
            "本课合成实验里，五个 GT（16/18/24/48/96 像素）算出来的阈值分别是 <strong>0.212 / 0.234 / 0.369 / 0.478 / 0.462</strong>。<em>注意 16 像素的标志阈值只有 0.212，而 48 像素的是 0.478</em>——如果用固定的 0.5，前者一个正样本都拿不到，后者刚好能拿到。<strong>这组数字就是「固定阈值对尺度不公平」的直接证据</strong>。同时也暴露了 ATSS 的边界：$t_g$ 是<em>候选集内部</em>的相对阈值，如果整个候选集质量都很差（小目标就是这样），它选出的正样本绝对质量依然很低；而「中心必须落在 GT 框内」这条硬约束，对 16×16 的目标来说<strong>物理上只有 2 个格点满足</strong>（stride 8 上 1 个、stride 16 上 1 个、stride 32 上 0 个）——<em>阈值再自适应也变不出格点来</em>。",
        ),
        CALLOUT("warn", "两个实现细节，写错了会静默降点：<strong>① 标准差用无偏（ddof=1）还是有偏（ddof=0）</strong>——mmdet 跟随 PyTorch 默认用无偏，候选集只有 27 个样本时两者差约 2%，虽小但会改变边界样本的归属；<strong>② topk 是「每层各取 k 个」而不是「全局取 k 个」</strong>——写成全局的话，高分辨率层（格点密）会垄断候选集，ATSS 的跨层自适应能力就没了。<em>这两个坑在复现 ATSS 时都出现过。</em>"),
    ])),

    ("simota", "OTA / SimOTA：把分配看成最优传输问题", "".join([
        P("ATSS 仍然是<strong>纯几何</strong>的——它只看 anchor 与 GT 的框，不看模型现在预测得怎么样。<span class=\"term\">OTA</span>（Optimal Transport Assignment, CVPR 2021）提出了一个更本质的视角：<strong>分配是一个全局的供需匹配问题</strong>。每个 GT 是一个「供应方」，要把 $k_g$ 单位的正样本标签分发出去；背景是另一个供应方，供应量是剩下的全部；每个格点是一个「需求方」，需求量恒为 1。把「格点 $i$ 领取 GT $g$ 的标签」的成本记为 $c_{ig}$，<strong>整张图的分配就是一个最小代价的运输方案</strong>。"),
        MATH("\\min_{\\pi \\ge 0} \\sum_{g}\\sum_{i} \\pi_{ig}\\, c_{ig} \\quad \\text{s.t.} \\quad \\sum_i \\pi_{ig} = k_g,\\;\\; \\sum_g \\pi_{ig} \\le 1, \\qquad c_{ig} = \\mathcal{L}^{cls}_{ig} + \\lambda\\, \\mathcal{L}^{reg}_{ig}"),
        DUAL(
            "OTA 的关键在于「<strong>全局</strong>」二字。逐个 GT 独立地挑最好的格点（ATSS/TaskAligned 都是这么做的）在目标不重叠时没问题；<em>但当两个标志上下紧贴（TSR 里主牌 + 辅助牌是最常见的构型），同一批格点对两个 GT 都很有吸引力</em>，逐个挑就会打架。最优传输在<strong>全局代价</strong>下同时决定所有 GT 的分配，能自动把有争议的格点分给「更需要它」的那一方。",
            "代价是计算量：精确解要跑 Sinkhorn 迭代，OTA 论文里用了 50 轮，<strong>训练速度慢约 20–25%</strong>。YOLOX 因此提出 <span class=\"term\">SimOTA</span>——<em>去掉 Sinkhorn，用「每个 GT 独立取代价最小的前 $k_g$ 个，再对冲突的格点做一次仲裁」来近似</em>。这是一个<strong>贪心近似</strong>：它放弃了全局最优性，换回几乎全部的速度。YOLOX 的消融显示这个近似在 AP 上的损失可以忽略（OTA 与 SimOTA 差距 &lt; 0.2 AP），<strong>但它的「无冲突」是靠事后仲裁保证的，而不是约束保证的</strong>——所以密集场景下仍会出现「某个 GT 被抢走名额、正样本变少」的现象。",
        ),
        ASCII("""SimOTA 四步（这就是 notebook 里要你从零写出来的东西）

 ① 几何先验筛候选（把 8400 个格点砍到几百个）
    in_box   = 格点中心落在 GT 框内
    in_ctr   = 格点中心落在 GT 中心 ±2.5·stride 的方框内
    候选池 fg_mask = (in_box OR in_ctr).any(gt)          ← 本课实验：8400 → 399
    先验掩码 both  = in_box AND in_ctr                    ← 进代价矩阵当惩罚项

 ② 建代价矩阵 C ∈ R^(G×M)
    C[g,i] = BCE(sqrt(p_i), onehot_g)          分类代价
           + 3.0 · (-log IoU(box_i, gt_g))     定位代价（λ=3）
           + 100000 · (1 - both[g,i])          不满足中心先验 -> 天价惩罚

 ③ dynamic-k：每个 GT 该领几个正样本，由「预测质量」自己说了算
    k_g = clamp( floor( Σ_{i ∈ top10 IoU} IoU(box_i, gt_g) ), min=1 )
    直觉：周围有 9 个格点各预测出 IoU≈1 的框 -> 这个 GT 供得起 9 个正样本
          周围最好的框才 IoU 0.3 -> 只给 1 个，别拿噪声当监督
    本课实验：k = [6, 6, 8, 9, 9]  (GT 尺寸 16/18/24/48/96 px)

 ④ 去冲突：某个格点被多个 GT 选中 -> 归给代价最小的那个 GT
    （被抢走的 GT 就少一个正样本，不补——这是 SimOTA 的已知缺陷）"""),
        P("第 ③ 步的 <span class=\"term\">dynamic-k</span> 是 SimOTA 最值得记住的设计。<strong>它把「每个 GT 分几个正样本」从超参数变成了模型自己的输出</strong>：把该 GT 周围 IoU 最高的 10 个预测框的 IoU 加起来取整，就是配额。这个式子看起来很土，但它编码了一个正确的直觉——<em>能提供 $k$ 个高质量预测的目标，就说得起 $k$ 份监督；提供不出来的，多给就是灌噪声</em>。而且它<strong>随训练自动变化</strong>：训练初期预测都很差，$k$ 普遍为 1–2，相当于自动退化成一对一；训练后期预测变好，$k$ 涨到 8–10，监督密度自动提高。"),
        CALLOUT("warn", "一个几乎没人讲、但你在 notebook 里会亲眼看到的<strong>真实边界行为</strong>：当 $k_g$ 大于「满足中心先验的候选数」时，SimOTA <em>依然会</em>把带 100000 惩罚的格点选进来。本课实验里 16×16 的标志 $k=6$，而满足 <code>in_box AND in_ctr</code> 的格点只有 <strong>2 个</strong>——于是<strong>另外 4 个正样本落在了 GT 框外</strong>。这不是 bug，是 YOLOX 原版代码的行为（那 100000 只影响排序、不构成硬约束）。<em>它意味着：对极小目标，SimOTA 会把框外的格点也标成正样本，回归目标是负数宽度/越界偏移——这正是 RTMDet 用<strong>软中心先验</strong>替换硬先验的动机之一。</em>"),
    ])),

    ("aligned", "TaskAligned：让分类分数与定位质量绑在一起", "".join([
        P("检测器有一个长期存在、却直到 <span class=\"term\">TOOD</span>（Task-aligned One-stage Object Detection, ICCV 2021）才被明确命名的病：<strong>分类分数最高的那个预测，往往不是框最准的那个</strong>。而 NMS 是按分类分数排序的——<em>于是排序第一的框被保留、框最准的框被抑制掉，AP 白白损失</em>。这个现象叫 <span class=\"term\">task misalignment</span>（任务错配）。"),
        DUAL(
            "错配的根源是<strong>两条支路的监督目标不同</strong>：分类支路学的是「这里有没有物体、是什么类」，回归支路学的是「框应该往哪挪」。<em>它们共享特征、却各自优化各自的目标，没有任何机制要求「分数高的地方框也准」</em>。在本课的合成检测器里，同一个 GT 附近，分类分数与预测框 IoU 的相关系数只有 <strong>0.60–0.82</strong>——<em>相关但远不是同一件事</em>。真实检测器上这个数还会更低。",
            "TaskAligned 的解法是引入一个<strong>把两者相乘的对齐度量</strong> $t = s^{\\alpha} \\cdot u^{\\beta}$（$s$ 是该 GT 类别的分类分数，$u$ 是预测框与 GT 的 IoU），并<strong>同时用它做两件事</strong>：① <em>分配</em>——每个 GT 取 $t$ 最高的 top-$k$ 个格点为正样本；② <em>监督</em>——把分类的目标值从 1 换成归一化后的 $t$（即软标签），让「对齐度高的位置分数也高」。<strong>这个「同一个度量既选样本又当标签」的设计是 TOOD 的精髓</strong>，YOLOv8 的 <code>TaskAlignedAssigner</code>（$\\alpha=0.5,\\beta=6$）与 YOLOv6 v3 都直接继承了它。",
        ),
        MATH("t \\;=\\; s^{\\alpha} \\cdot u^{\\beta}, \\qquad \\text{(TOOD: } \\alpha{=}1,\\ \\beta{=}6;\\ \\text{YOLOv8: } \\alpha{=}0.5,\\ \\beta{=}6)"),
        P("$\\beta$ 远大于 $\\alpha$ 这件事本身就是设计意图：<strong>定位质量的权重压倒性地高于分类分数</strong>。取 $\\beta=6$ 时，IoU 从 0.9 掉到 0.8，$u^{\\beta}$ 从 0.53 掉到 0.26——<em>腰斩</em>；而分类分数从 0.9 掉到 0.8，$s^{0.5}$ 只从 0.95 掉到 0.89。<strong>换句话说：TaskAligned 主要是按「框准不准」选样本，分类分数只是一个温和的修正项。</strong>"),
        TABLE(["", "候选池", "选多少", "选择依据", "去冲突规则"], [
            ["<strong>MaxIoU</strong>", "全部 anchor", "阈值决定（不定）", "anchor 与 GT 的几何 IoU", "IoU 最大者胜"],
            ["<strong>ATSS</strong>", "每层最近 9 个", "阈值 $m+v$ 决定", "anchor 与 GT 的几何 IoU", "IoU 最大者胜"],
            ["<strong>SimOTA</strong>", "in_box ∪ in_center", "<strong>dynamic-k（预测决定）</strong>", "分类代价 + 3×定位代价", "<strong>代价最小者胜</strong>"],
            ["<strong>TaskAligned</strong>", "in_box", "固定 top-k（10–13）", "<strong>对齐度 $s^{\\alpha}u^{\\beta}$</strong>", "IoU 最大者胜"],
            ["<strong>RTMDet DSLA</strong>", "全部（靠软先验衰减）", "dynamic-k（top-13 IoU 和）", "<strong>软标签分类代价 + IoU + 软中心先验</strong>", "代价最小者胜"],
        ]),
        CALLOUT("intuition", "把这一列「选择依据」竖着读，就是标签分配十年演进的全部内容：<strong>几何 IoU → 几何 IoU 的自适应统计 → 预测的分类+定位联合代价 → 分类与定位的乘性对齐度</strong>。<em>一句话总结：分配的信息源从「框和框的关系」一路搬到了「模型当前的预测本身」。</em>面试被问到「标签分配的演进」，按这条线讲，比背五篇论文的名字有力得多。"),
    ])),

    ("soft", "RTMDet 的 dynamic soft label：把硬标签换成软标签", "".join([
        P("RTMDet 的 <span class=\"term\">DynamicSoftLabelAssigner</span>（下一模块会完整解剖）把上面几条线索合成了一个代价函数。它值得单独讲，因为<strong>它是目前工业界实时检测器里综合表现最稳的一个分配器</strong>，也是 MMDetection 里默认给 RTMDet / RTMDet-Ins 用的那个。"),
        MATH("C_{ig} \\;=\\; \\underbrace{\\mathrm{BCE}(p_i,\\, y^{soft}_{ig}) \\cdot \\left| y^{soft}_{ig} - p_i \\right|^2}_{\\text{软标签分类代价}} \\;+\\; \\underbrace{3 \\cdot \\big(-\\log u_{ig}\\big)}_{\\text{定位代价}} \\;+\\; \\underbrace{10^{\\,d_{ig}/s_i - 3}}_{\\text{软中心先验}}, \\qquad y^{soft}_{ig} = u_{ig} \\cdot \\mathbf{1}_{c_g}"),
        P("三项各自解决一个具体问题："),
        UL([
            "<strong>软标签分类代价</strong>：分类目标不再是硬 1，而是 <em>该格点预测框与 GT 的 IoU</em>。含义是「你框得多准，就该报多高的分」——这直接把 TaskAligned 的对齐思想写进了代价。后面乘的 $|y-p|^2$ 是一个 focal 式的调制：<em>已经对齐的格点代价接近 0，不再争抢；差得远的格点代价被放大</em>。当 $p_i$ 恰好等于软标签时代价<strong>严格为 0</strong>——这是一个可以在 notebook 里 assert 出来的性质。",
            "<strong>定位代价</strong> $-\\log u$：IoU 越低代价越高，且在 $u \\to 0$ 时发散，天然排除了框离得远的格点。权重 3 与 YOLOX 一致。",
            "<strong>软中心先验</strong> $10^{d/s-3}$：$d$ 是格点到 GT 中心的像素距离、$s$ 是该格点所在层的 stride。<em>距离 = 0 时代价 $10^{-3}$（几乎不惩罚）；距离 = 3·stride 时代价 1（与一个中等的定位代价相当）；距离 = 5·stride 时代价 100（实质排除）</em>。<strong>关键差别：它是连续衰减的，不是 SimOTA 那种 0/100000 的悬崖</strong>——于是不会出现「候选数不够就跳崖去选框外格点」的边界行为。",
        ]),
        DUAL(
            "为什么「软」这么重要？因为<strong>硬标签在数值上撒了谎</strong>。一个格点预测出 IoU 0.62 的框，硬标签告诉它「你的分类目标是 1.0」，等于要求它<em>和一个预测 IoU 0.95 的格点报一样高的分</em>。这个要求在推理时是有害的：NMS 按分数排序，两个分数一样高但一个框准一个框不准的预测，保留哪个就成了掷骰子。<em>软标签把「框的质量」直接编码进了分数的目标值，让分数变成了可用于排序的定位质量估计。</em>",
            "这也解释了为什么现代检测器普遍<strong>去掉了独立的 IoU/centerness 分支</strong>。FCOS 时代要额外学一个 centerness 分数、推理时与分类分数相乘；而软标签把这件事直接融进了分类目标，<em>省掉一个分支、省掉一次乘法、还避免了「两个分支各自校准不一致」的问题</em>。<strong>YOLOv8 去掉 objectness、RTMDet 不用 centerness，本质上都是软标签带来的红利。</strong> 代价是分类分数不再是概率——它是「分类置信度 × 定位质量」的混合物，<em>做置信度标定（calibration）或者把分数传给下游 VLA/融合模块时，必须知道这一点</em>。",
        ),
        CALLOUT("warn", "落到工程上有个真实的坑：<strong>软标签让分类分数的绝对值整体下降</strong>（目标值从 1.0 变成 IoU，通常 0.6–0.9）。如果你把 score 阈值从旧模型（硬标签）原样搬到新模型（软标签），<em>召回会莫名其妙掉一截</em>。<strong>换分配器时，score 阈值必须重新在验证集上扫一遍</strong>——这条在 TSR 这种要求「特定 FP/km 下最大化召回」的系统里尤其致命。"),
    ])),

    ("tsr", "落到交通标志检测：分配策略在这里意味着什么", "".join([
        P("把上面的机制放回 <span class=\"term\">TSR</span>（Traffic Sign Recognition，交通标志检测）场景，会看到两个别的任务上不那么突出、但在这里决定成败的问题。"),
        H3("① 小目标：正样本的绝对上限被 stride 卡死"),
        P("用针孔模型算一笔账：焦距 1200 px（1920×1080、约 60° 水平 FOV 的前视相机）、限速牌物理直径 0.6 m，则 80 米外它在图像上是 <code>1200 × 0.6 / 80 = 9 px</code>，60 米外是 12 px，40 米外是 18 px。<strong>要在 80 米外检出，意味着要在一个 9 像素的目标上做检测</strong>——而 stride 8 的特征图上，9 像素的目标只覆盖约 1 个格点。"),
        ASCII("""16×16 的标志在三层 FPN 上有几个格点中心落在框内（实测）

  stride  8  格点间距 8px   │ ●   ●   ●   ●        框内: 1 个 ← 唯一的天然正样本
                            │   ┌───────┐
  stride 16  格点间距 16px  │ ●─┼─●     ●          框内: 1 个
                            │   │ 16px  │
  stride 32  格点间距 32px  │ ● └───────┘  ●       框内: 0 个
                            │
  ⇒ 全图 8400 个格点，落在这个 GT 里的一共 **2 个**。
  ⇒ ATSS 给 1 个正样本、TaskAligned 给 2 个（被格点数卡死）、
     SimOTA 给 6 个（但其中 4 个在框外，是先验惩罚被 dynamic-k 顶穿的结果）。
  ⇒ 结论：**再聪明的分配器也变不出格点**。小目标的正样本上限
     是由 stride 和输入分辨率决定的物理量，不是分配算法能突破的。"""),
        CALLOUT("danger", "这条结论直接决定架构选型：<strong>TSR 系统必须在「加 P2 层（stride 4）」「提高输入分辨率」「ROI 裁剪只处理消失点附近区域」三者中至少选一个</strong>，否则再换多少个分配器都是在 2 个格点上做文章。<em>面试里如果对方问「你会怎么提升远距离标志的召回」，答「换 SimOTA」是不够的——正确答案要先说清「正样本的物理上限在哪」，再谈分配。</em>这也是 C57（小目标检测）整门课的起点。"),
        H3("② 密集场景：主牌 + 辅助牌的名额争夺"),
        P("中国道路上极常见的构型是「限速牌 + 下方的辅助说明牌」，两个标志上下紧贴、尺寸相近。<strong>它们的候选格点几乎完全重叠</strong>。此时不同分配器的行为差别很大："),
        TABLE(["分配器", "冲突处理", "对密集小目标的后果"], [
            ["<strong>MaxIoU</strong>", "IoU 最大者胜，且「强制认领」可能互相覆写", "两个 GT 各拿 1 个正样本，谁也没学好"],
            ["<strong>ATSS</strong>", "IoU 最大者胜", "阈值按各自候选集算，互不干扰；但被抢走的名额<em>不补</em>"],
            ["<strong>SimOTA</strong>", "<strong>代价最小者胜</strong>（全局代价视角）", "仲裁更合理，但仍<em>不补名额</em>：被抢的 GT 正样本数直接减少"],
            ["<strong>OTA（完整版）</strong>", "最优传输约束里就带 $\\sum_i \\pi_{ig} = k_g$", "理论上每个 GT 都拿满配额，代价是 Sinkhorn 的开销"],
        ]),
        DUAL(
            "所以在 TSR 这种「小 + 密」双重困难的场景里，<strong>「被抢走的名额不补」是一个真实的性能漏洞</strong>：本来就只有 2 个格点的辅助牌，被主牌抢走 1 个，就只剩 1 个正样本。<em>线上表现就是「主牌检得到、辅助牌时有时无」——而辅助牌恰恰携带了「限速仅限雨天」「距离 500 m」这类改变驾驶决策的语义。</em>",
            "工程上的可行对策有三条，按成本递增：① <strong>把中心先验半径调小</strong>（SimOTA 的 <code>center_radius</code> 从 2.5 降到 1.5），减少两个 GT 候选池的重叠；② <strong>换成 RTMDet 的软中心先验</strong>，让距离衰减连续化，仲裁时距离信息不会被 0/100000 的悬崖抹平；③ <strong>在分配后做名额补齐</strong>（被抢名额的 GT 从剩余候选里再补一个），这是若干工业代码库里的私有改动，论文里不常见。<em>面试里能说出第 ① 条就已经很具体了，能说出第 ③ 条说明真的在密集场景上调过。</em>",
        ),
    ])),

    ("o2o", "一对一 vs 一对多：这是推理需求，不是训练最优", "".join([
        P("最后一条主线：<strong>一个 GT 到底该配几个正样本？</strong> 上面讲的全是<span class=\"term\">one-to-many</span>（一对多）；而 DETR 系用的是 <span class=\"term\">one-to-one</span>（一对一，每个 GT 恰好一个预测）。这两者的取舍是本门课与 C54 的接缝，也是面试里区分度极高的一题。"),
        TABLE(["", "一对多（YOLO/RTMDet 系）", "一对一（DETR 系 / YOLOv10 的 o2o 头）"], [
            ["<strong>监督密度</strong>", "每 GT 数个到十几个正样本，梯度密集", "每 GT 仅 1 个正样本，<strong>梯度极稀疏</strong>"],
            ["<strong>收敛速度</strong>", "快（12–300 epoch）", "慢（DETR 原版 500 epoch；Deformable 降到 50）"],
            ["<strong>推理是否需要 NMS</strong>", "<strong>需要</strong>——多个正样本必然产生多个高分重复框", "不需要——训练期就学会了「只有一个该赢」"],
            ["<strong>延迟稳定性</strong>", "NMS 耗时随目标数与阈值波动，<strong>p99 不可控</strong>", "端到端固定，<em>这是车端最看重的性质</em>"],
            ["<strong>密集小目标</strong>", "较强（监督密集）", "较弱（query 数固定、匹配对小框敏感）"],
        ]),
        DUAL(
            "最反直觉、也最值得记住的一点：<strong>一对一是「推理端的需求」，不是「训练端的最优」</strong>。证据非常硬——Group DETR、H-DETR、Co-DETR 这一批工作全都在<em>训练时额外加一个一对多分支</em>提供密集监督，<strong>推理时把它丢掉</strong>，AP 显著提升。也就是说：一对一之所以被采用，唯一的理由是「推理时不想要 NMS」；<em>但它带来的稀疏监督对训练是纯粹的损失，需要额外手段补回来。</em>",
            "YOLOv10 的 <span class=\"term\">consistent dual assignments</span>（一致双分配）把这个洞察做到了极致：<strong>训练时同时挂一对多头（提供密集监督）和一对一头（学会去重），并且要求两个头用<em>同一个</em>度量做匹配</strong>（这就是「一致」的含义——如果两个头各用各的排序标准，一对一头选中的样本在一对多头里排名靠后，两条监督就互相打架）。推理时只留一对一头，<strong>真正做到无 NMS，且不损失一对多的训练收益</strong>。<em>这是 2024 年以来最干净的一个「鱼与熊掌」解法，面试里能完整讲出「一致」二字的含义会很加分。</em>",
        ),
        CALLOUT("intuition", "面试标准答案骨架（背下来）：<strong>「NMS 之所以能被去掉，不是因为发明了更好的后处理，而是因为把去重这件事从<em>推理期</em>搬到了<em>训练期</em>——一对一匹配让模型自己学会「同一个物体只让一个预测出头」。代价是监督信号密度降到 1/k，所以后续所有工作（辅助头、去噪 query、双分配）都在想办法把这份密度补回来。」</strong> <em>能把「代价是什么、后续怎么补」讲出来，比只说「DETR 不需要 NMS」高一个层次。</em>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>分配与损失的界限正在消失</strong>：软标签让「谁是正样本」变成了连续的权重而非 0/1 判定（Generalized Focal Loss、VarifocalNet、RTMDet 的 DSLA 都在这条线上）。<em>极端形态是「全部格点都是带权正样本」——分配退化成一个权重函数</em>。这条路的开放问题是：权重函数的形状能不能学出来，而不是手工设计？",
            "<strong>分配的不稳定性尚无好的度量</strong>：SimOTA / TaskAligned 都依赖模型当前的预测，<em>同一个格点在相邻 epoch 可能一会儿是正一会儿是负</em>，造成梯度方向震荡。DETR 系用 DN-DETR 的去噪 query 缓解匹配不稳定，而一对多分配器这边<strong>连「翻转率」这个指标都还没有标准定义</strong>。这是一个门槛低、价值高的可做方向。",
            "<strong>训练初期的冷启动</strong>：预测感知的分配器在第 0 个 epoch 面对随机预测，代价矩阵基本是噪声。实践里靠「前若干 epoch 用静态分配 warmup」绕过，<em>但这个切换点怎么定、切换是否引入分布突变，缺少系统研究</em>。",
            "<strong>尺度公平性的度量</strong>：AP_S/AP_M/AP_L 只能事后看结果，<strong>缺少一个能在训练期直接监控「各尺度得到的监督量是否公平」的指标</strong>。本模块 notebook 里的「每 GT 正样本数 × 尺度」统计是一个雏形——<em>把它做成训练期的实时诊断，是很实用的工程改进</em>。",
            "<strong>一对一与一对多的统一</strong>：YOLOv10 的一致双分配给出了一个工程解，但「为什么一致性是必要的」尚无理论刻画。<em>更进一步：能否设计一个单一的分配，其正样本数随训练进度从多平滑地退火到一？</em>",
            "<strong>三维与多模态下的分配</strong>：BEV 检测、点云检测里「中心先验」的定义完全不同（BEV 网格没有透视缩放，但有极端稀疏），<em>直接搬 SimOTA 效果并不好</em>。TSR 走向多相机+BEV 融合后，这会是一个直接相关的开放问题。",
        ]),
        CALLOUT("paper", "必读（按阅读顺序）：<em>Bridging the Gap Between Anchor-based and Anchor-free Detection via Adaptive Training Sample Selection</em>（ATSS, CVPR 2020，★ 先读它的对照实验设计，那是全文最有价值的部分）；<em>OTA: Optimal Transport Assignment for Object Detection</em>（CVPR 2021，★ 最优传输的形式化）；<em>YOLOX: Exceeding YOLO Series in 2021</em>（SimOTA 的工程近似与消融表）；<em>TOOD: Task-aligned One-stage Object Detection</em>（ICCV 2021，★ 任务错配的定义与 $t=s^{\\alpha}u^{\\beta}$）；<em>RTMDet: An Empirical Study of Designing Real-Time Object Detectors</em>（DynamicSoftLabelAssigner，下一模块精读）；<em>Generalized Focal Loss</em>（分类-定位联合表示，软标签的理论支撑）；<em>YOLOv10: Real-Time End-to-End Object Detection</em>（一致双分配）。相邻课程：C54（一对一匹配与集合预测）、C57（小目标的分配与 NWD 度量）、C18（IoU/NMS 基础）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 标签分配（ATSS / SimOTA / TaskAligned / dynamic-k / 去冲突）

目标：在**同一组合成 TSR 数据**上，从零实现四种标签分配策略，
并用数字回答一个问题——**它们到底把哪些格点标成了正样本，差别有多大**。

本 notebook 你会亲手实现：

1. 一个 640×640 / stride 8·16·32 的 FPN 格点系统与一组 TSR 风格的 GT（16px→96px）
2. 一个「训练到一半」的**合成检测器**（分类分数与定位质量**部分解耦**——这正是 TaskAligned 要治的病）
3. **MaxIoU 静态分配** + 「可匹配尺寸区间」的解析推导
4. **ATSS**：每层 top-k 候选 + 自适应阈值 `mean + std`
5. **SimOTA 完整版**：几何先验 → 代价矩阵 → **dynamic-k** → **去冲突**
6. **TaskAligned**：$t = s^{\\alpha}u^{\\beta}$ 的选择与仲裁
7. 四种分配的**正样本集合差异**（数量 / 层分布 / 质量 / Jaccard 重叠）

> 心智模型：**网络结构决定模型能表达什么，标签分配决定模型实际学到什么。**"""),

    md("""## 1 · 合成一个 TSR 风格的检测场景

640×640 输入、三层 FPN。GT 按真实交通标志的成像尺寸设计：
远处 16px 的限速牌、紧贴其下的 18px 辅助牌（**密集构型**）、
中距离 24px 警告牌、48px 禁令牌、近处 96px 指示牌。"""),
    code("""import numpy as np
np.set_printoptions(precision=3, suppress=True)

IMG = 640
STRIDES = [8, 16, 32]        # P3 / P4 / P5
ANCHOR_SCALE = 4.0           # 每个格点一个 anchor，边长 = ANCHOR_SCALE * stride

def make_points(img=IMG, strides=STRIDES):
    '''FPN 各层的格点中心（图像像素坐标）+ 每个格点的 stride 与层号。'''
    P, S, L = [], [], []
    for li, s in enumerate(strides):
        n = img // s
        gy, gx = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
        P.append(np.stack([(gx.ravel() + 0.5) * s, (gy.ravel() + 0.5) * s], 1).astype(float))
        S.append(np.full(n * n, float(s)))
        L.append(np.full(n * n, li))
    return np.concatenate(P), np.concatenate(S), np.concatenate(L)

POINTS, PT_S, PT_L = make_points()
ANCHORS = np.concatenate([POINTS - (ANCHOR_SCALE * PT_S[:, None]) / 2,
                          POINTS + (ANCHOR_SCALE * PT_S[:, None]) / 2], 1)   # xyxy

# 一个典型 TSR 场景（尺寸对应 ~80m / ~75m / ~55m / ~28m / ~14m）
GT = np.array([
    [300., 180., 316., 196.],   # 0  16x16  远处限速牌
    [305., 200., 323., 218.],   # 1  18x18  紧贴其下的辅助牌 <- 密集构型
    [352., 172., 376., 196.],   # 2  24x24  警告牌
    [180., 300., 228., 348.],   # 3  48x48  禁令牌
    [ 60., 260., 156., 356.],   # 4  96x96  近处指示牌
])
GT_CLS = np.array([0, 2, 1, 0, 2])      # 0=限速 1=警告 2=指示
N_CLS = 3
GT_WH = GT[:, 2:] - GT[:, :2]

print(f'FPN 格点总数 {len(POINTS)}  = 80^2 + 40^2 + 20^2 = {80**2 + 40**2 + 20**2}')
print(f'各层格点数: ' + ', '.join(f'stride{s}:{int((PT_S == s).sum())}' for s in STRIDES))
print()
print(f'{"GT":>3s} {"类":>3s} {"尺寸":>10s} {"面积":>7s} {"中心":>16s}')
for i, b in enumerate(GT):
    print(f'{i:>3d} {GT_CLS[i]:>3d} {GT_WH[i,0]:>4.0f}x{GT_WH[i,1]:<5.0f} '
          f'{GT_WH[i].prod():>7.0f} ({(b[0]+b[2])/2:>7.1f},{(b[1]+b[3])/2:>6.1f})')

assert len(POINTS) == 8400 and ANCHORS.shape == (8400, 4)
assert (ANCHORS[:, 2] - ANCHORS[:, 0]).min() == 32.0    # stride8 -> 32px anchor
assert (ANCHORS[:, 2] - ANCHORS[:, 0]).max() == 128.0   # stride32 -> 128px anchor
print()
print('✅ 场景就位：5 个 GT，面积跨度 36 倍（16px vs 96px），含一对紧贴的密集标志。')"""),

    md("""## 2 · IoU、中心先验，与一个「训练到一半」的合成检测器

SimOTA 与 TaskAligned 都是**预测感知**的——它们要看模型当前预测得怎么样。
所以我们需要一个合成检测器。合成规则（物理上合理）：

- 格点离某个 GT 中心越近（按 GT 尺寸归一化），该位置的**回归越准、分类分数越高**；
- 额外注入一份**与定位无关**的分类噪声 —— 于是「分数高」与「框准」只是**部分相关**，
  这正是 TaskAligned 要治的 task misalignment。"""),
    code("""def bbox_iou(a, b):
    '''a:(M,4) b:(N,4) xyxy -> (M,N) 的 IoU 矩阵。'''
    area_a = (a[:, 2] - a[:, 0]).clip(0) * (a[:, 3] - a[:, 1]).clip(0)
    area_b = (b[:, 2] - b[:, 0]).clip(0) * (b[:, 3] - b[:, 1]).clip(0)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = (rb - lt).clip(0)
    inter = wh[..., 0] * wh[..., 1]
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-12)

def points_in_boxes(points, boxes):
    '''(G,N) 布尔：格点中心是否严格落在框内。'''
    cx, cy = points[:, 0], points[:, 1]
    return ((cx[None] > boxes[:, 0:1]) & (cx[None] < boxes[:, 2:3]) &
            (cy[None] > boxes[:, 1:2]) & (cy[None] < boxes[:, 3:4]))

# —— IoU 自校验 ——
_t = np.array([[0., 0., 10., 10.], [5., 5., 15., 15.], [100., 100., 110., 110.]])
_m = bbox_iou(_t, _t)
assert np.allclose(np.diag(_m), 1.0)
assert _m[0, 2] == 0.0
assert abs(_m[0, 1] - 25 / 175) < 1e-9        # 交 5x5=25，并 100+100-25=175
print(f'IoU 自校验通过：半重叠框 IoU = {_m[0,1]:.4f} = 25/175')

# —— IoU 对位移的敏感性：小目标为什么这么难（C57 会展开）——
print()
print(f'{"框边长":>8s} {"偏移1px":>9s} {"偏移2px":>9s} {"偏移4px":>9s}')
for L in [8, 16, 32, 64]:
    row = []
    for d in [1, 2, 4]:
        a = np.array([[0., 0., L, L]]); b = np.array([[d, d, L + d, L + d]])
        row.append(bbox_iou(a, b)[0, 0])
    print(f'{L:>6d}px {row[0]:>9.3f} {row[1]:>9.3f} {row[2]:>9.3f}')
assert bbox_iou(np.array([[0., 0., 8., 8.]]), np.array([[2., 2., 10., 10.]]))[0, 0] < 0.40
print('⚠️  8x8 的框偏移 2px，IoU 就掉到 0.39；64x64 的框偏 2px 还有 0.88。')
print('    同一个 IoU 阈值对不同尺度是**极不公平**的 —— 这是本模块所有问题的根。')"""),
    code("""def synth_detector(points, gt, gt_cls, n_cls=N_CLS, seed=7):
    '''合成一个「训练到一半」的检测器输出：(cls_score[N,C], pred_box[N,4])。'''
    rg = np.random.default_rng(seed)
    N = len(points)
    ctr = (gt[:, :2] + gt[:, 2:]) / 2
    sz = np.sqrt((gt[:, 2] - gt[:, 0]) * (gt[:, 3] - gt[:, 1]))
    d = np.linalg.norm(points[:, None, :] - ctr[None, :, :], axis=2) / sz[None, :]
    near, dmin = d.argmin(1), d.min(1)
    q = np.exp(-(dmin / 0.7) ** 2)                # 预测质量 in (0,1]：离中心越近越准
    g = gt[near]
    gcx, gcy = (g[:, 0] + g[:, 2]) / 2, (g[:, 1] + g[:, 3]) / 2
    gw, gh = g[:, 2] - g[:, 0], g[:, 3] - g[:, 1]
    j = 1 - q                                     # 抖动强度
    nz = rg.normal(size=(N, 4))
    pcx = gcx + nz[:, 0] * 0.45 * gw * j
    pcy = gcy + nz[:, 1] * 0.45 * gh * j
    pw = gw * np.exp(nz[:, 2] * 0.40 * j)         # 用 log 空间抖动 -> 框永远合法
    ph = gh * np.exp(nz[:, 3] * 0.40 * j)
    box = np.stack([pcx - pw / 2, pcy - ph / 2, pcx + pw / 2, pcy + ph / 2], 1)
    logit = rg.normal(-3.6, 0.6, size=(N, n_cls))                 # 背景基线 sigmoid≈0.03
    logit[np.arange(N), gt_cls[near]] += 6.6 * q + rg.normal(0, 0.9, N)   # ← 解耦噪声
    return 1 / (1 + np.exp(-logit)), box

CLS_PRED, BOX_PRED = synth_detector(POINTS, GT, GT_CLS)
IOU_PRED = bbox_iou(GT, BOX_PRED)          # (G,N) 预测框 vs GT
IN_GT = points_in_boxes(POINTS, GT)

print(f'{"GT":>3s} {"尺寸":>7s} {"框内格点数":>11s} {"(s8/s16/s32)":>14s} {"最好预测IoU":>12s} {"corr(分数,IoU)":>15s}')
for g in range(len(GT)):
    per_lv = [int((IN_GT[g] & (PT_L == l)).sum()) for l in range(3)]
    near_mask = IN_GT[g] | (bbox_iou(GT[g:g+1], ANCHORS)[0] > 0.05)
    c = np.corrcoef(CLS_PRED[near_mask, GT_CLS[g]], IOU_PRED[g, near_mask])[0, 1]
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {int(IN_GT[g].sum()):>11d} '
          f'{str(per_lv):>14s} {IOU_PRED[g].max():>12.3f} {c:>15.3f}')

assert IOU_PRED.max(1).min() > 0.80, '每个 GT 附近都应有一个近乎完美的预测'
assert IN_GT.sum(1)[0] == 2, '16x16 的 GT 全图只有 2 个格点中心落在框内'
print()
print('⚠️  第 3 列是本 notebook 最重要的一个数字：')
print('    **16x16 的标志，全图 8400 个格点里只有 2 个中心落在框内。**')
print('    正样本的绝对上限被 stride 卡死了 —— 分配算法再聪明也变不出格点。')
print('⚠️  最后一列 0.6~0.8：分类分数与定位质量**相关但不等同** -> task misalignment。')"""),

    md("""## 3 · 静态 MaxIoU 分配：先算清「哪些目标根本没资格」

RetinaNet 式规则：IoU ≥ 0.5 为正、< 0.4 为负、中间忽略，
外加「每个 GT 强制认领它 IoU 最高的 anchor」这条兜底。

**先做一件比跑算法更有价值的事：算理论上界。**"""),
    code("""IOU_ANC = bbox_iou(GT, ANCHORS)     # (G,N)：anchor 与 GT 的几何 IoU（与预测无关）

print('每个 GT 在各层 anchor 上的**理论最大 IoU** = min(A_gt,A_anc)/max(A_gt,A_anc)')
print(f'{"GT":>3s} {"尺寸":>7s} {"s8(32px)":>10s} {"s16(64px)":>10s} {"s32(128px)":>11s} {"实测max":>9s}')
for g in range(len(GT)):
    a_gt = GT_WH[g].prod()
    ub = [min(a_gt, (ANCHOR_SCALE * s) ** 2) / max(a_gt, (ANCHOR_SCALE * s) ** 2) for s in STRIDES]
    mark = '  ← 天花板 < 0.5' if max(ub) < 0.5 else ''
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {ub[0]:>10.3f} {ub[1]:>10.3f} {ub[2]:>11.3f} '
          f'{IOU_ANC[g].max():>9.3f}{mark}')

# 16px / 18px 的 GT：无论哪一层，几何 IoU 上界都低于 0.5
assert IOU_ANC[0].max() < 0.5 and IOU_ANC[1].max() < 0.5
assert IOU_ANC[2].max() >= 0.5
print()
print('⚠️  16px 与 18px 的标志：**在任何一层上都不可能达到 IoU 0.5**。')
print('    不是「难匹配」，是数学上不可能 —— 固定阈值对它们是一道硬门。')"""),
    code("""def maxiou_assign(iou_gt_anchor, pos_thr=0.5, neg_thr=0.4, force_best=True):
    '''RetinaNet 式静态分配。返回 assign[N]（-1=负样本，>=0 是 GT 下标）与 ignore 掩码。'''
    G, N = iou_gt_anchor.shape
    best_gt, best_iou = iou_gt_anchor.argmax(0), iou_gt_anchor.max(0)
    assign = np.full(N, -1)
    hit = best_iou >= pos_thr
    assign[hit] = best_gt[hit]
    ignore = (best_iou >= neg_thr) & (best_iou < pos_thr)
    if force_best:                                # 低质量兜底：每个 GT 至少领一个 anchor
        for g in range(G):
            assign[iou_gt_anchor[g].argmax()] = g
    return assign, ignore

A_MAXIOU, IGNORE = maxiou_assign(IOU_ANC)
n_thr = int((IOU_ANC.max(0) >= 0.5).sum())
print(f'靠阈值 0.5 拿到的正样本: {n_thr} 个')
print(f'加上「强制认领」兜底后:   {int((A_MAXIOU >= 0).sum())} 个')
print(f'忽略样本: {int(IGNORE.sum())} 个,  负样本: {int((A_MAXIOU < 0).sum() - IGNORE.sum())} 个')
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"正样本数":>9s} {"来源":>28s}')
for g in range(len(GT)):
    n = int((A_MAXIOU == g).sum())
    src = '全部来自兜底（阈值一个没中）' if (IOU_ANC[g] >= 0.5).sum() == 0 else '阈值命中'
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {n:>9d} {src:>28s}')

assert (A_MAXIOU >= 0).sum() <= 8, '静态分配在小目标场景下正样本极度稀缺'
assert (A_MAXIOU == 0).sum() == 1 and (A_MAXIOU == 1).sum() == 1
print()
print('⚠️  8400 个格点，只有 6 个正样本，正负比 1:1400。')
print('    16px 与 18px 的两个标志，唯一的正样本**全靠兜底规则硬塞**——')
print(f'    塞进来的 anchor IoU 只有 {IOU_ANC[0].max():.2f} / {IOU_ANC[1].max():.2f}：')
print('    这是**噪声监督**，不是好监督。而 48px / 96px 各只拿到 1 个阈值命中的正样本。')"""),

    md("""## 4 · ATSS：让阈值自己从候选集的统计量里长出来

四步：每层取最近 k=9 个 anchor 当候选 → 算它们与 GT 的 IoU →
**阈值 = mean + std** → 过阈值且中心在框内的为正样本。

注意 `std` 用 **ddof=1**（无偏），与 PyTorch / mmdet 的默认一致。"""),
    code("""def atss_assign(points, pt_level, anchors, gt, topk=9, n_levels=3):
    '''ATSS。返回 assign[N], 每个 GT 的自适应阈值 thr[G], 候选掩码 cand[G,N]。'''
    G, N = len(gt), len(anchors)
    gctr = (gt[:, :2] + gt[:, 2:]) / 2
    dist = np.linalg.norm(points[:, None, :] - gctr[None, :, :], axis=2)   # (N,G)
    iou_anc = bbox_iou(gt, anchors)                                        # (G,N)

    cand = np.zeros((G, N), bool)
    for g in range(G):
        for l in range(n_levels):                     # ← **每层各取 topk**，不是全局 topk
            idx = np.where(pt_level == l)[0]
            cand[g, idx[np.argsort(dist[idx, g])[:min(topk, len(idx))]]] = True

    inside = points_in_boxes(points, gt)
    thr = np.zeros(G)
    pos = np.zeros((G, N), bool)
    for g in range(G):
        v = iou_anc[g, cand[g]]
        thr[g] = v.mean() + v.std(ddof=1)             # ← 自适应阈值
        pos[g] = cand[g] & (iou_anc[g] >= thr[g]) & inside[g]

    assign = np.full(N, -1)                            # 冲突 -> IoU 最大的 GT 胜
    any_pos = pos.any(0)
    assign[any_pos] = np.where(pos, iou_anc, -1.0)[:, any_pos].argmax(0)
    return assign, thr, cand

A_ATSS, ATSS_THR, ATSS_CAND = atss_assign(POINTS, PT_L, ANCHORS, GT)

print(f'{"GT":>3s} {"尺寸":>7s} {"候选数":>7s} {"候选IoU均值":>12s} {"标准差":>8s} '
      f'{"自适应阈值":>11s} {"正样本":>7s}')
iou_anc = bbox_iou(GT, ANCHORS)
for g in range(len(GT)):
    v = iou_anc[g, ATSS_CAND[g]]
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {int(ATSS_CAND[g].sum()):>7d} {v.mean():>12.3f} '
          f'{v.std(ddof=1):>8.3f} {ATSS_THR[g]:>11.3f} {int((A_ATSS == g).sum()):>7d}')

assert ATSS_THR[0] < 0.30, '16px 的 GT 阈值应远低于 0.5'
assert ATSS_THR[3] > 0.45, '48px 的 GT 阈值应接近 0.5'
assert (A_ATSS >= 0).sum() > (A_MAXIOU >= 0).sum(), 'ATSS 应比 MaxIoU 给出更多正样本'
print()
print(f'⚠️  自适应阈值从 {ATSS_THR.min():.3f}（16px）到 {ATSS_THR.max():.3f}（48px）——')
print('    **固定 0.5 相当于对小目标单方面提高了 2.3 倍的门槛。**')
print('✅ ATSS 的全部魔法就是 mean+std：std 大说明某一层特别匹配 -> 抬阈值只选那层；')
print('   std 小说明各层半斤八两 -> 降阈值多选几个。选层与选数量被同一个公式解决了。')"""),

    md("""## 5 · SimOTA：代价矩阵 → dynamic-k → 去冲突

这是本模块的技术核心，也是 YOLOX 相对 YOLOv5 的最大增量。四步逐个实现。"""),
    code("""def simota_assign(points, pt_stride, gt, gt_cls, cls_pred, box_pred,
                  center_radius=2.5, n_candidate_k=10, lam_reg=3.0,
                  soft_label=False, big_penalty=1e5):
    '''SimOTA（YOLOX）。返回 assign[N] 与一份完整的中间结果，便于逐步检查。'''
    G, N, C = len(gt), len(points), cls_pred.shape[1]
    cx, cy = points[:, 0], points[:, 1]

    # ---- ① 几何先验：候选池 = in_box OR in_center；先验掩码 = in_box AND in_center ----
    in_box = points_in_boxes(points, gt)
    gcx, gcy = (gt[:, 0:1] + gt[:, 2:3]) / 2, (gt[:, 1:2] + gt[:, 3:4]) / 2
    r = center_radius * pt_stride[None, :]                 # 半径随层的 stride 放大
    in_ctr = ((cx[None] > gcx - r) & (cx[None] < gcx + r) &
              (cy[None] > gcy - r) & (cy[None] < gcy + r))
    fg = (in_box | in_ctr).any(0)
    idx = np.where(fg)[0]
    M = len(idx)
    both = in_box[:, idx] & in_ctr[:, idx]                 # (G,M)

    # ---- ② 代价矩阵 ----
    ious = bbox_iou(gt, box_pred[idx])                     # (G,M)
    p = np.sqrt(np.clip(cls_pred[idx], 1e-8, 1 - 1e-8))    # YOLOX 的 sqrt（cls×obj 的几何均值）
    y = np.zeros((G, M, C))
    y[np.arange(G), :, gt_cls] = 1.0
    if soft_label:                                         # RTMDet 路线：目标值 = IoU
        y = y * ious[:, :, None]
    cls_cost = -(y * np.log(p)[None] + (1 - y) * np.log(1 - p)[None]).sum(-1)
    reg_cost = -np.log(np.clip(ious, 1e-8, None))
    cost = cls_cost + lam_reg * reg_cost + big_penalty * (~both)

    # ---- ③ dynamic-k：配额由预测质量自己决定 ----
    nk = min(n_candidate_k, M)
    dyn_k = np.clip(np.sort(ious, 1)[:, -nk:].sum(1).astype(int), 1, None)

    matching = np.zeros((G, M), bool)
    for g in range(G):
        matching[g, np.argsort(cost[g])[:dyn_k[g]]] = True

    # ---- ④ 去冲突：一个格点被多个 GT 选中 -> 归给代价最小的 GT ----
    multi = matching.sum(0) > 1
    n_conflict = int(multi.sum())
    if multi.any():
        win = np.where(matching, cost, np.inf)[:, multi].argmin(0)
        matching[:, multi] = False
        matching[win, np.where(multi)[0]] = True

    assign = np.full(N, -1)
    has = matching.any(0)
    assign[idx[has]] = matching[:, has].argmax(0)
    return assign, dict(fg_idx=idx, cost=cost, ious=ious, both=both,
                        dyn_k=dyn_k, n_conflict=n_conflict, matching=matching)

A_SIMOTA, D = simota_assign(POINTS, PT_S, GT, GT_CLS, CLS_PRED, BOX_PRED)

print(f'① 候选池：8400 个格点 -> {len(D["fg_idx"])} 个（in_box OR in_center, r=2.5·stride）')
print(f'② 代价矩阵 shape = {D["cost"].shape}')
print(f'④ 去冲突：有 {D["n_conflict"]} 个格点被多个 GT 同时选中')
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"AND先验内":>10s} {"dynamic-k":>10s} {"最终正样本":>11s} {"其中在框外":>11s}')
for g in range(len(GT)):
    sel = np.where(D['matching'][g])[0]
    out = int((~D['both'][g, sel]).sum())
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {int(D["both"][g].sum()):>10d} {D["dyn_k"][g]:>10d} '
          f'{int((A_SIMOTA == g).sum()):>11d} {out:>11d}')

assert len(D['fg_idx']) < 600, '几何先验应把 8400 砍到几百'
assert D['dyn_k'][4] >= D['dyn_k'][0], '大目标/预测好的目标应拿到更大的配额'
assert D['dyn_k'].min() >= 1, 'dynamic-k 至少为 1'
assert (A_SIMOTA >= 0).sum() > (A_ATSS >= 0).sum()
print()
print('⚠️  看最后一列：16px 的 GT dynamic-k=6，但满足 AND 先验的格点只有 2 个 ——')
print('    于是另外 4 个正样本**落在了 GT 框外**。这不是 bug，是 YOLOX 原版行为：')
print('    那个 100000 只影响排序、不是硬约束。dynamic-k 会把它顶穿。')
print('✅ 这正是 RTMDet 用**连续衰减的软中心先验**替换 0/100000 悬崖的动机之一。')"""),
    code("""# —— dynamic-k 到底在干什么：把「配额」画出来 ——
print('dynamic-k = clamp( floor( 该 GT 周围 top-10 预测框 IoU 之和 ), min=1 )')
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"top-10 预测 IoU":>44s} {"和":>7s} {"k":>4s}')
for g in range(len(GT)):
    top = np.sort(D['ious'][g])[-10:][::-1]
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {" ".join(f"{v:.2f}" for v in top):>44s} '
          f'{top.sum():>7.2f} {D["dyn_k"][g]:>4d}')

# 训练早期（预测很差）时 dynamic-k 会自动退化成一对一
bad_box = BOX_PRED + np.random.default_rng(0).normal(0, 60, BOX_PRED.shape)
_, D_bad = simota_assign(POINTS, PT_S, GT, GT_CLS, CLS_PRED * 0.1, bad_box)
print()
print(f'训练初期（预测框加 60px 噪声、分数压到 1/10）的 dynamic-k: {D_bad["dyn_k"]}')
print(f'训练中期（本例的正常预测）的 dynamic-k:                   {D["dyn_k"]}')
assert D_bad['dyn_k'].sum() < D['dyn_k'].sum(), '预测越差，配额应越小'
print()
print('✅ 这是 dynamic-k 最漂亮的性质：**它随训练进度自动调节监督密度**。')
print('   早期预测烂 -> k 接近 1，等价于一对一，不灌噪声；')
print('   后期预测好 -> k 涨到 8~10，监督变密，收敛加速。无需任何手工 schedule。')"""),
    code("""# —— 去冲突：用一个手算得出来的小矩阵把规则钉死 ——
toy_cost = np.array([
    [0.5, 0.8, 1.0, 3.0, 4.0, 5.0],     # GT0 对 6 个候选格点的代价
    [4.0, 3.0, 1.2, 0.9, 0.6, 5.0],     # GT1
])
toy_k = np.array([3, 3])

def take_topk(cost, k):
    m = np.zeros(cost.shape, bool)
    for g in range(len(cost)):
        m[g, np.argsort(cost[g])[:k[g]]] = True
    return m

def resolve(matching, cost):
    multi = matching.sum(0) > 1
    n = int(multi.sum())
    if multi.any():
        win = np.where(matching, cost, np.inf)[:, multi].argmin(0)
        matching[:, multi] = False
        matching[win, np.where(multi)[0]] = True
    return matching, n

m0 = take_topk(toy_cost, toy_k)
print('去冲突前：')
print('  GT0 选中格点', np.where(m0[0])[0], ' GT1 选中格点', np.where(m0[1])[0])
print('  格点 2 被两个 GT 同时选中：cost[0,2]=1.0 < cost[1,2]=1.2 -> 判给 GT0')
m1, nconf = resolve(m0.copy(), toy_cost)
print('去冲突后：')
print('  GT0 ->', np.where(m1[0])[0], ' GT1 ->', np.where(m1[1])[0], f'  (仲裁了 {nconf} 个格点)')

assert nconf == 1
assert list(np.where(m1[0])[0]) == [0, 1, 2]
assert list(np.where(m1[1])[0]) == [3, 4]
assert m1.sum(0).max() == 1, '去冲突后每个格点最多属于一个 GT'
print()
print('⚠️  注意 GT1 的正样本从 3 个变成了 2 个 —— **被抢走的名额不补**。')
print('    在 TSR 的「主牌 + 辅助牌」构型里，本来只有 2 个格点的辅助牌')
print('    被主牌抢走 1 个就只剩 1 个正样本 -> 线上表现为「辅助牌时有时无」。')
print('✅ 完整 OTA 用约束 Σ_i π[i,g] = k_g 保证每个 GT 拿满配额，代价是 Sinkhorn 迭代。')"""),

    md("""## 6 · TaskAligned：$t = s^{\\alpha} \\cdot u^{\\beta}$

TOOD / YOLOv8 路线。同一个对齐度量既用来**选样本**、也用来当**软标签**。
这里只实现选择部分（软标签部分见模块 03）。"""),
    code("""def task_aligned_assign(points, gt, gt_cls, cls_pred, box_pred,
                        topk=13, alpha=1.0, beta=6.0):
    '''TaskAligned 分配。返回 assign[N], 对齐度矩阵 t[G,N], 冲突数。'''
    G, N = len(gt), len(points)
    inside = points_in_boxes(points, gt)
    ious = bbox_iou(gt, box_pred).clip(0)                 # (G,N)
    s = cls_pred[:, gt_cls].T                             # (G,N) 该 GT 类别上的分数
    t = (s ** alpha) * (ious ** beta)                     # ← 对齐度
    t_masked = np.where(inside, t, 0.0)

    match = np.zeros((G, N), bool)
    for g in range(G):
        k = min(topk, int(inside[g].sum()))
        if k == 0:                                        # 兜底：没有格点落在框内
            d = np.linalg.norm(points - (gt[g, :2] + gt[g, 2:]) / 2, axis=1)
            match[g, d.argmin()] = True
            continue
        sel = np.argsort(-t_masked[g])[:k]
        match[g, sel[t_masked[g, sel] > 0]] = True

    multi = match.sum(0) > 1                              # 去冲突：YOLOv8 用「IoU 最大者胜」
    n_conflict = int(multi.sum())
    if multi.any():
        win = np.where(match, ious, -1.0)[:, multi].argmax(0)
        match[:, multi] = False
        match[win, np.where(multi)[0]] = True

    assign = np.full(N, -1)
    any_m = match.any(0)
    assign[any_m] = match[:, any_m].argmax(0)
    return assign, t, n_conflict

A_TAL, T_ALIGN, TAL_CONF = task_aligned_assign(POINTS, GT, GT_CLS, CLS_PRED, BOX_PRED)

print(f'{"GT":>3s} {"尺寸":>7s} {"框内格点":>9s} {"topk上限":>9s} {"实得正样本":>11s} '
      f'{"正样本平均IoU":>14s}')
for g in range(len(GT)):
    m = A_TAL == g
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {int(IN_GT[g].sum()):>9d} {min(13, int(IN_GT[g].sum())):>9d} '
          f'{int(m.sum()):>11d} {IOU_PRED[g, m].mean():>14.3f}')

# beta 远大于 alpha：定位质量压倒分类分数
print()
print(f'{"":>16s} {"s=0.9,u=0.9":>13s} {"s=0.9,u=0.8":>13s} {"s=0.8,u=0.9":>13s}')
for a, b in [(1.0, 6.0), (0.5, 6.0)]:
    vals = [(0.9 ** a) * (0.9 ** b), (0.9 ** a) * (0.8 ** b), (0.8 ** a) * (0.9 ** b)]
    print(f'alpha={a}, beta={b}  {vals[0]:>13.4f} {vals[1]:>13.4f} {vals[2]:>13.4f}')

t_iou_drop = (0.9 ** 1.0) * (0.8 ** 6.0)
t_cls_drop = (0.8 ** 1.0) * (0.9 ** 6.0)
assert t_cls_drop > t_iou_drop * 1.5, 'IoU 掉 0.1 的惩罚应远重于分数掉 0.1'
assert (A_TAL == 0).sum() <= 2, '16px 的 GT 框内只有 2 个格点，TaskAligned 最多给 2 个'
print()
print(f'⚠️  IoU 从 0.9->0.8，对齐度掉 {(1 - t_iou_drop / ((0.9**1)*(0.9**6))) * 100:.0f}%；')
print(f'    分数从 0.9->0.8，对齐度只掉 {(1 - t_cls_drop / ((0.9**1)*(0.9**6))) * 100:.0f}%。')
print('✅ beta >> alpha 是刻意的：**TaskAligned 主要按「框准不准」选样本**，')
print('   分类分数只是温和的修正项。这也是它对 misalignment 有效的原因。')"""),

    md("""## 7 · 四种分配的正样本集合差异：一张表说完

同一组数据、同一个合成检测器，四种分配给出的正样本集合到底差多少。"""),
    code("""METHODS = {'MaxIoU@0.5': A_MAXIOU, 'ATSS': A_ATSS,
           'SimOTA': A_SIMOTA, 'TaskAligned': A_TAL}

print(f'{"方法":<13s} {"正样本":>7s} {"每GT分布":>22s} {"层分布(s8/s16/s32)":>21s} '
      f'{"平均IoU":>9s} {"平均分数":>9s}')
stats = {}
for name, a in METHODS.items():
    pos = a >= 0
    idxs = np.where(pos)[0]
    per_gt = [int((a == g).sum()) for g in range(len(GT))]
    per_lv = [int((pos & (PT_L == l)).sum()) for l in range(3)]
    m_iou = float(IOU_PRED[a[pos], idxs].mean())
    m_scr = float(CLS_PRED[idxs, GT_CLS[a[pos]]].mean())
    stats[name] = dict(n=int(pos.sum()), per_gt=per_gt, per_lv=per_lv,
                       iou=m_iou, score=m_scr)
    print(f'{name:<13s} {pos.sum():>7d} {str(per_gt):>22s} {str(per_lv):>21s} '
          f'{m_iou:>9.3f} {m_scr:>9.3f}')

# 正样本「质量」：预测感知的分配器挑出的样本定位更准
assert stats['MaxIoU@0.5']['iou'] < stats['TaskAligned']['iou']
assert stats['MaxIoU@0.5']['score'] < stats['TaskAligned']['score']
assert stats['MaxIoU@0.5']['n'] < stats['ATSS']['n'] < stats['SimOTA']['n']
print()
print('✅ 平均 IoU 单调上升 0.808 -> 0.848 -> 0.852 -> 0.885：')
print('   **越是「看着预测选样本」的分配器，挑出的正样本定位质量越高。**')
print('   这不是废话 —— 它意味着回归损失看到的是更容易学的样本，梯度信噪比更好。')"""),
    code("""def jaccard(a, b):
    sa, sb = set(np.where(a >= 0)[0]), set(np.where(b >= 0)[0])
    return len(sa & sb) / max(len(sa | sb), 1)

names = list(METHODS)
print('正样本集合的 Jaccard 重叠：')
print(f'{"":<13s}' + ''.join(f'{n:>13s}' for n in names))
J = np.zeros((4, 4))
for i, ni in enumerate(names):
    row = ''
    for j, nj in enumerate(names):
        J[i, j] = jaccard(METHODS[ni], METHODS[nj])
        row += f'{J[i,j]:>13.3f}'
    print(f'{ni:<13s}{row}')

assert np.allclose(np.diag(J), 1.0)
assert J[2, 3] > J[0, 1], 'SimOTA 与 TaskAligned 更像（都看预测），MaxIoU 与 ATSS 更不像'
assert J[0, 2] < 0.25, 'MaxIoU 与 SimOTA 的正样本集合几乎不重叠'
print()
print(f'⚠️  MaxIoU 与 SimOTA 的重叠只有 {J[0,2]:.1%} —— **它们在训练完全不同的东西**。')
print(f'✅ SimOTA 与 TaskAligned 重叠 {J[2,3]:.1%}：都以「预测质量」为主要依据，殊途同归。')
print()
print('把「选择依据」竖着读，就是标签分配十年演进的全部内容：')
print('  几何 IoU -> 几何 IoU 的自适应统计 -> 分类+定位联合代价 -> 分类×定位的乘性对齐度')
print('  信息源从「框和框的关系」一路搬到了「模型当前的预测本身」。')"""),

    md("""## ✏️ 练习 1：静态阈值的「可匹配尺寸区间」

推导并实现 `matchable_size_range(anchor_side, thr)`：在「同宽高比、同心」的理想情况下，
GT 边长 $L$ 与 anchor 边长 $s$ 的 IoU 上界是 $\\min(L^2,s^2)/\\max(L^2,s^2)$。
求使 IoU $\\ge \\tau$ 的 $L$ 区间，返回 `(lo, hi)`。

再实现 `is_matchable(gt_side, strides, anchor_scale, thr)`：判断某个尺寸的 GT
在**任意一层**上能否被匹配上。"""),
    code("""def matchable_size_range(anchor_side, thr=0.5):
    # TODO: 解 min(L^2,s^2)/max(L^2,s^2) >= thr，返回 (lo, hi)
    raise NotImplementedError

def is_matchable(gt_side, strides=STRIDES, anchor_scale=ANCHOR_SCALE, thr=0.5):
    # TODO: 任意一层能匹配上就返回 True
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
lo, hi = matchable_size_range(32.0, 0.5)
assert abs(lo - 32 / np.sqrt(2)) < 1e-9 and abs(hi - 32 * np.sqrt(2)) < 1e-9, (lo, hi)
assert abs(lo - 22.627) < 1e-3 and abs(hi - 45.255) < 1e-3
lo9, hi9 = matchable_size_range(32.0, 0.9)
assert hi9 - lo9 < hi - lo, '阈值越高，可匹配区间越窄'
assert matchable_size_range(64.0, 0.5)[0] == 2 * lo, '区间随 anchor 边长线性缩放'

assert not is_matchable(16.0) and not is_matchable(18.0), '16/18px 在任何一层都匹配不上'
assert is_matchable(24.0) and is_matchable(48.0) and is_matchable(96.0)
assert not is_matchable(300.0), '超大目标同样会掉出区间'

print(f'{"anchor边长":>10s} {"可匹配GT尺寸区间(τ=0.5)":>26s}')
for s in STRIDES:
    a = ANCHOR_SCALE * s
    r = matchable_size_range(a, 0.5)
    print(f'{a:>9.0f}px {f"[{r[0]:.1f}, {r[1]:.1f}]":>26s}')
print()
print(f'{"GT尺寸":>8s} {"能否被 IoU>=0.5 匹配":>22s}')
for L in [9, 16, 18, 24, 40, 48, 96, 200, 300]:
    print(f'{L:>6d}px {("✅ 可以" if is_matchable(float(L)) else "❌ 不可能"):>22s}')
print()
print('✅ 练习 1 通过：三档 anchor 覆盖 [22.6, 181]，**9~22px 的目标是一片盲区**。')
print('   TSR 里 80m 外的限速牌正好 9px —— 这就是为什么必须加 P2 层或提分辨率。')"""),

    md("""## ✏️ 练习 2：从零实现 dynamic-k 估计器

实现 `dynamic_k(ious, n_candidate_k=10, k_min=1)`：
`ious` 是 `(G, M)` 的「GT × 候选格点」IoU 矩阵，
返回长度 G 的整数配额数组 —— **每个 GT 取自己 top-`n_candidate_k` 个 IoU 求和后向下取整，再 clamp 到 ≥ k_min**。

不许调用上面 `simota_assign` 里的实现，写完与它对拍。"""),
    code("""def dynamic_k(ious, n_candidate_k=10, k_min=1):
    # TODO: 返回 shape (G,) 的 int 数组
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
toy = np.array([
    [0.9, 0.85, 0.8, 0.1, 0.05],      # top-3 和 = 2.55 -> k=2
    [0.3, 0.2,  0.1, 0.05, 0.0],      # top-3 和 = 0.60 -> floor=0 -> clamp 到 1
])
k = dynamic_k(toy, n_candidate_k=3)
assert k.dtype.kind == 'i', '应返回整数数组'
assert list(k) == [2, 1], k
assert list(dynamic_k(toy, n_candidate_k=5)) == [2, 1]
assert list(dynamic_k(np.ones((2, 20)), n_candidate_k=10)) == [10, 10], '全 1 时 k = n_candidate_k'
assert list(dynamic_k(np.zeros((3, 8)), n_candidate_k=4)) == [1, 1, 1], '全 0 时 clamp 到 1'
assert list(dynamic_k(toy, n_candidate_k=3, k_min=2)) == [2, 2]

# 与 worked cell 的 SimOTA 对拍
k_ref = D['dyn_k']
k_mine = dynamic_k(D['ious'], n_candidate_k=10)
assert np.array_equal(k_mine, k_ref), (k_mine, k_ref)
print('与 worked SimOTA 对拍一致:', k_mine)
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"k(正常预测)":>12s} {"k(预测退化50%)":>16s}')
for g in range(len(GT)):
    kd = dynamic_k(D['ious'] * 0.5, 10)[g]
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {k_mine[g]:>12d} {kd:>16d}')
assert dynamic_k(D['ious'] * 0.5, 10).sum() < k_mine.sum()
print()
print('✅ 练习 2 通过：dynamic-k 把「每个 GT 分几个正样本」交给了模型自己。')"""),

    md("""## ✏️ 练习 3：分配诊断报告

线上调检测器时，最有用的不是 AP，而是**分配本身的统计**。实现
`assign_report(assign, gt_wh, pt_level, n_levels=3)`，返回字典：

- `n_pos`：正样本总数
- `per_gt`：每个 GT 的正样本数（list）
- `per_level`：每层的正样本数（list）
- `starved`：正样本数 ≤ 1 的 GT 下标（list）——**这是最该报警的指标**
- `imbalance`：`max(per_gt) / max(min(per_gt), 1)`，尺度公平性的粗略度量"""),
    code("""def assign_report(assign, gt_wh, pt_level, n_levels=3):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
r = assign_report(A_MAXIOU, GT_WH, PT_L)
assert r['n_pos'] == int((A_MAXIOU >= 0).sum())
assert sum(r['per_gt']) == r['n_pos'] and sum(r['per_level']) == r['n_pos']
assert len(r['per_level']) == 3
assert 0 in r['starved'] and 1 in r['starved'], 'MaxIoU 下 16/18px 的 GT 都饿着'
assert r['imbalance'] == max(r['per_gt']) / max(min(r['per_gt']), 1)

r2 = assign_report(A_SIMOTA, GT_WH, PT_L)
assert len(r2['starved']) == 0, 'SimOTA 下没有 GT 只拿到 <=1 个正样本'
assert r2['imbalance'] < r['imbalance'], 'SimOTA 的尺度公平性优于 MaxIoU'

print(f'{"方法":<13s} {"正样本":>7s} {"饿着的GT":>22s} {"不均衡度":>9s} {"层分布":>18s}')
for name, a in METHODS.items():
    rr = assign_report(a, GT_WH, PT_L)
    starve = str([f'#{i}({GT_WH[i,0]:.0f}px)' for i in rr['starved']]) if rr['starved'] else '无'
    print(f'{name:<13s} {rr["n_pos"]:>7d} {starve:>22s} {rr["imbalance"]:>9.2f} '
          f'{str(rr["per_level"]):>18s}')
print()
print('✅ 练习 3 通过：**把这份报告打进训练日志**，比等 mAP 出来再回头猜有效得多。')
print('   线上真实用法：某个类别 AP 突然掉 -> 先看它的 GT 是不是在 starved 名单里。')"""),

    md("""## ✏️ 练习 4：RTMDet 的软中心先验

SimOTA 的中心先验是 0/100000 的悬崖，会被 dynamic-k 顶穿。
RTMDet 换成连续衰减的 $10^{\\,d/s - R}$（$d$ = 格点到 GT 中心的像素距离，
$s$ = 该格点的 stride，$R$ = `soft_center_radius`，默认 3.0）。

实现 `soft_center_prior(points, pt_stride, gt, radius=3.0)`，返回 `(G, N)` 的代价矩阵。"""),
    code("""def soft_center_prior(points, pt_stride, gt, radius=3.0):
    # TODO: 10 ** (归一化距离 - radius)
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
sp = soft_center_prior(POINTS, PT_S, GT)
assert sp.shape == (len(GT), len(POINTS))

# 关键性质：d=0 -> 1e-3；d=radius*stride -> 1；d=5*stride -> 100
one_pt = np.array([[100.0, 100.0]]); one_s = np.array([8.0])
g_at = np.array([[92., 92., 108., 108.]])              # 中心正好是 (100,100)
assert abs(soft_center_prior(one_pt, one_s, g_at)[0, 0] - 1e-3) < 1e-9
g_off = np.array([[68., 92., 84., 108.]])              # 中心 (76,100)，距离 24 = 3*stride
assert abs(soft_center_prior(one_pt, one_s, g_off)[0, 0] - 1.0) < 1e-9
g_far = np.array([[52., 92., 68., 108.]])              # 中心 (60,100)，距离 40 = 5*stride
assert abs(soft_center_prior(one_pt, one_s, g_far)[0, 0] - 100.0) < 1e-6

print(f'{"距离/stride":>12s} {"软中心先验代价":>16s} {"对比 SimOTA 硬先验":>22s}')
soft_curve = np.array([10.0 ** (dn - 3.0) for dn in range(7)])
for dn in range(7):
    hard = '0（框内+中心内）' if dn <= 2.5 else '100000（悬崖）'
    print(f'{dn:>12d} {soft_curve[dn]:>16.4f} {hard:>22s}')
assert np.all(np.diff(soft_curve) > 0), '软先验必须随距离严格单调增'

# 把软先验接进 SimOTA 的代价：拆掉 0/100000 悬崖，换成斜坡
sp_fg = sp[:, D['fg_idx']]
cost_soft = D['cost'] - 1e5 * (~D['both']) + sp_fg
k = dynamic_k(D['ious'], 10)
match_soft = np.zeros_like(D['matching'])
for g in range(len(GT)):
    match_soft[g, np.argsort(cost_soft[g])[:k[g]]] = True

gctr = (GT[:, :2] + GT[:, 2:]) / 2
dnorm = (np.linalg.norm(POINTS[None, D['fg_idx'], :] - gctr[:, None, :], axis=2)
         / PT_S[None, D['fg_idx']])                     # (G,M) 归一化中心距离
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"硬先验:框外数":>13s} {"硬先验:平均d/s":>15s} '
      f'{"软先验:框外数":>13s} {"软先验:平均d/s":>15s}')
for g in range(len(GT)):
    h, s_ = D['matching'][g], match_soft[g]
    print(f'{g:>3d} {GT_WH[g,0]:>4.0f}px {int((~D["both"][g,h]).sum()):>13d} '
          f'{dnorm[g,h].mean():>15.2f} {int((~D["both"][g,s_]).sum()):>13d} '
          f'{dnorm[g,s_].mean():>15.2f}')

assert dnorm[0, match_soft[0]].mean() < dnorm[0, D['matching'][0]].mean(), \
    '对 16px 的 GT，软先验应把正样本拉得离中心更近'
print()
print('✅ 练习 4 通过。诚实地读这张表：')
print('   · 对 16px 的 GT（先验内只有 2 个格点、k=6），软先验把正样本的平均距离从 0.89 拉到 0.74；')
print('   · 但 18px 的 GT 反而多了 2 个框外正样本 —— **软先验不是万能药**。')
print('   它做的事只有一件：把 0/100000 的**悬崖**换成**斜坡**。')
print('   悬崖的问题不是「让框外格点进来」，而是「进来的那些格点之间，距离信息被完全抹平」')
print('   （所有框外格点的惩罚项都是同一个 100000，排序只剩 cls+reg）。')
print('   斜坡则让排序始终携带距离信息 —— 这才是 RTMDet 换掉它的真正理由。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def matchable_size_range(anchor_side, thr=0.5):
    # min(L^2,s^2)/max(L^2,s^2) >= thr  <=>  sqrt(thr)*s <= L <= s/sqrt(thr)
    return anchor_side * np.sqrt(thr), anchor_side / np.sqrt(thr)

def is_matchable(gt_side, strides=STRIDES, anchor_scale=ANCHOR_SCALE, thr=0.5):
    for s in strides:
        lo, hi = matchable_size_range(anchor_scale * s, thr)
        if lo <= gt_side <= hi:
            return True
    return False"""),
    code("""# 练习 2 参考答案
def dynamic_k(ious, n_candidate_k=10, k_min=1):
    nk = min(n_candidate_k, ious.shape[1])
    topk = np.sort(ious, axis=1)[:, -nk:]
    return np.clip(np.floor(topk.sum(1)).astype(int), k_min, None)"""),
    code("""# 练习 3 参考答案
def assign_report(assign, gt_wh, pt_level, n_levels=3):
    G = len(gt_wh)
    pos = assign >= 0
    per_gt = [int((assign == g).sum()) for g in range(G)]
    per_level = [int((pos & (pt_level == l)).sum()) for l in range(n_levels)]
    return {
        'n_pos': int(pos.sum()),
        'per_gt': per_gt,
        'per_level': per_level,
        'starved': [g for g in range(G) if per_gt[g] <= 1],
        'imbalance': max(per_gt) / max(min(per_gt), 1),
    }"""),
    code("""# 练习 4 参考答案
def soft_center_prior(points, pt_stride, gt, radius=3.0):
    gctr = (gt[:, :2] + gt[:, 2:]) / 2                       # (G,2)
    d = np.linalg.norm(points[None, :, :] - gctr[:, None, :], axis=2)   # (G,N) 像素距离
    return 10.0 ** (d / pt_stride[None, :] - radius)"""),

    md("""---
## 🧪 真实工程胶囊：mmdetection 里换分配器的完整配置与排查清单"""),
    code(r"""RECIPE = r'''
# ============ ① mmdetection：三种分配器的配置写法（可直接粘） ============
# ATSS（几何、稳定、无需 warmup，适合从零起训）
train_cfg = dict(assigner=dict(type='ATSSAssigner', topk=9))

# SimOTA（YOLOX；预测感知，密集监督）
train_cfg = dict(assigner=dict(
    type='SimOTAAssigner',
    center_radius=2.5,        # ← 密集小目标场景调小到 1.5，减少候选池重叠
    candidate_topk=10,        # ← dynamic-k 的 n_candidate_k
    iou_weight=3.0, cls_weight=1.0))

# RTMDet 的 DynamicSoftLabelAssigner（软标签 + 软中心先验，工业首选）
train_cfg = dict(assigner=dict(
    type='DynamicSoftLabelAssigner',
    topk=13,                  # dynamic-k 用 top-13 IoU 求和
    iou_weight=3.0,
    soft_center_radius=3.0))  # ← 10^(d/stride - 3)；小目标多可降到 2.5

# ============ ② 换分配器时必须一起改的三件事 ============
# 1. score 阈值要重扫：软标签让分类分数整体下移（目标值从 1.0 变成 IoU≈0.6~0.9）
#    直接沿用旧阈值 -> 召回莫名掉一截。用验证集扫 0.01~0.5 重定工作点。
# 2. 分类损失要配套：软标签必须用 QualityFocalLoss（能吃连续目标），
#    普通 FocalLoss 只接受 0/1 标签，配错会静默降点。
# 3. 预测感知的分配器需要 warmup：前 ~1-5 epoch 预测是噪声，代价矩阵没有意义。
#    RTMDet 的做法是初期整体 loss 权重小 + 用 AdamW 稳住；
#    某些实现直接前 N 个 epoch 用 ATSS，之后切 SimOTA。

# ============ ③ 分配相关的线上排查清单（按顺序做） ============
# [ ] 打印每个 GT 的正样本数（本 notebook 的 assign_report），找 starved 名单
# [ ] 按 GT 尺寸分桶统计正样本数：如果 <32px 桶的均值 < 2，先改架构不要改分配
# [ ] 打印 dynamic-k 的分布随 epoch 的变化：一直贴着 1 = 预测太差或 warmup 不够
# [ ] 统计去冲突仲裁次数：占正样本比例 > 10% 说明场景太密，考虑降 center_radius
# [ ] 检查是否有正样本落在 GT 框外（SimOTA 的已知边界行为）
# [ ] 换分配器后，**必须**重新扫 score 阈值再比 mAP，否则比的是阈值不是分配器

# ============ ④ 诊断代码片段（贴进 assigner 的 forward 末尾） ============
if self.debug and (self.iter % 200 == 0):
    n_pos_per_gt = matching_matrix.sum(1)                       # (G,)
    gt_area = (gt_bboxes[:, 2] - gt_bboxes[:, 0]) * (gt_bboxes[:, 3] - gt_bboxes[:, 1])
    small = gt_area < 32 ** 2
    print(f'[assign] pos={int(matching_matrix.sum())} '
          f'k_mean={dynamic_ks.float().mean():.2f} '
          f'starved={int((n_pos_per_gt <= 1).sum())} '
          f'small_gt_pos_mean={n_pos_per_gt[small].float().mean():.2f}')
'''
print(RECIPE)
for key in ['ATSSAssigner', 'SimOTAAssigner', 'DynamicSoftLabelAssigner',
            'center_radius', 'soft_center_radius', 'QualityFocalLoss',
            'starved', 'score 阈值要重扫']:
    assert key in RECIPE, key
print('✅ 配方覆盖：三种分配器配置 / 换分配器的连带改动 / 线上排查清单 / 诊断代码')"""),

    md("""### 小结

- **标签分配决定训练信号的分布本身**。网络结构决定模型能表达什么，
  分配决定模型实际学到什么 —— 它不含一个参数，却值几个点 AP。
- **静态 IoU 阈值的根本问题是尺度不公平**：可匹配的 GT 尺寸区间是
  $[\\sqrt{\\tau}s,\\ s/\\sqrt{\\tau}]$，落在区间外的目标**数学上不可能**被匹配到，
  只能靠兜底规则塞一个低质量 anchor —— 那是噪声监督。
- **ATSS 用 `mean + std` 把「选哪层」和「选几个」一次解决**。本课实测阈值从
  16px 的 0.21 到 48px 的 0.48，固定 0.5 相当于对小目标单方面提高 2.3 倍门槛。
- **SimOTA 四步：几何先验 → 代价矩阵 → dynamic-k → 去冲突**。dynamic-k 让配额
  随预测质量自动伸缩（早期≈1，后期 8–10），是它最漂亮的性质。
  代价：去冲突时**被抢走的名额不补**，密集场景下会削弱某个 GT。
- **TaskAligned 的 $t=s^{\\alpha}u^{\\beta}$ 中 $\\beta \\gg \\alpha$ 是刻意的**：
  主要按定位质量选样本，分类分数只是修正项。同一个度量既选样本又当软标签。
- **RTMDet 用连续衰减的软中心先验替换 0/100000 悬崖**，避免 dynamic-k 顶穿硬先验
  去选框外格点。软标签的代价：分类分数不再是概率，**score 阈值必须重扫**。
- **TSR 的硬约束：16×16 的标志全图只有 2 个格点中心落在框内。**
  正样本上限是 stride 与输入分辨率决定的物理量，**分配算法突破不了**——
  必须先解决架构（P2 层 / 高分辨率 / ROI 裁剪），再谈分配。
- **一对一是推理端的需求，不是训练端的最优**。Group/H-/Co-DETR 训练时加回一对多分支
  就是证据；YOLOv10 的一致双分配是目前最干净的统一。

下一站：**模块 03 · RTMDet 解剖** —— 大核、共享头，以及本模块埋下的软标签代价函数的完整版。"""),
]
