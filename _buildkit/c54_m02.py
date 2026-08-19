# -*- coding: utf-8 -*-
"""C54 模块 02 · 集合预测损失：匹配之后怎么算账。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（二分匹配与匈牙利算法）；C18（检测基础：IoU/NMS/mAP）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_set_prediction_loss.ipynb'),
    ("核心参考", "DETR (Carion et al. 2020) §3.1–3.2；GIoU (Rezatofighi 2019)；DIoU/CIoU (Zheng 2020)；Deformable DETR / DINO 的 focal 版集合损失"),
    ("预计时长", "读 65 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("cost-vs-loss", "匹配代价与训练损失：两个长得像、职责完全不同的东西", "".join([
        P("模块 01 解决了「哪个预测对哪个 GT」。本模块解决「对上了之后，梯度怎么写」。"
          "这两步之间横着一个<strong>初学者几乎必然踩、面试官几乎必然追问</strong>的区分："
          "<span class=\"term\">matching cost</span>（匹配代价）和 <span class=\"term\">Hungarian loss</span>"
          "（集合损失）<em>不是同一个函数</em>，虽然它们的三个组成项名字一模一样。"),
        P("原因很朴素：匹配代价只用来<strong>排序</strong>（选出总代价最小的那个一一对应），"
          "它在 <code>torch.no_grad()</code> 里算完就扔；而损失要<strong>反向传播</strong>。"
          "一个只需要「谁比谁小」，另一个需要「梯度指向哪」。这两个需求会推出不同的函数形式。"),
        TABLE(["", "匹配代价 C(i, σ(i))", "训练损失 L"], [
            ["用途", "给匈牙利算法排序，决定一一对应", "<strong>产生梯度</strong>，更新参数"],
            ["是否需要可导", "<strong>不需要</strong>（在 <code>no_grad</code> 下计算）", "必须可导"],
            ["分类项形式", "<strong><code>-p̂<sub>σ(i)</sub>(c<sub>i</sub>)</code>（概率，负号取最大）</strong>",
             "<strong><code>-log p̂<sub>σ(i)</sub>(c<sub>i</sub>)</code>（交叉熵）</strong>"],
            ["背景 query 参与吗", "不参与（匹配只在 M 个真实 GT 上做）", "<strong>参与</strong>，且是绝大多数"],
            ["框损失作用范围", "只对候选配对算", "<strong>只对匹配上的 query 算</strong>（背景 query 没有框可比）"],
            ["权重", "λ<sub>cls</sub>=1, λ<sub>L1</sub>=5, λ<sub>giou</sub>=2（DETR 默认）", "同上（<em>可以不同，但通常取同值</em>）"],
        ]),
        DUAL(
            "为什么匹配时用<strong>概率 p 而不是 log p</strong>？因为要和 L1、GIoU 放在同一个代价矩阵里相加。"
            "<code>-log p</code> 是<em>无界</em>的：一个 p=1e-8 的预测会贡献 18.4 的代价，"
            "而 L1 项（归一化坐标下）通常只有 0.05 量级，GIoU 项最多 2。"
            "结果就是<strong>分类项会完全淹没定位项，匹配退化成「只看分类」</strong>——"
            "而分类分数高但框歪到天上的 query 就会抢走 GT。用概率则把分类项压在 [-1, 0]，三项量纲可比。",
            "严格地说，匈牙利算法要求的只是代价矩阵的<em>序结构</em>，任何单调变换都不改变最优匹配——"
            "<strong>但那只在单项时成立</strong>。一旦三项相加，单调变换会改变各项的<em>相对贡献</em>，"
            "从而改变最优匹配。所以「用 p 还是 log p」在这里不是数值技巧而是<strong>设计决策</strong>："
            "DETR 论文明确写了这一点（§3.1 脚注）。而损失端必须用 log，因为 <code>-p</code> 的梯度"
            "在 p→0 时不消失也不放大，收敛远慢于交叉熵。<em>同一件事，排序要有界，优化要陡峭。</em>",
        ),
        CALLOUT("warn", "<strong>面试高频陷阱</strong>：被问「DETR 的匹配代价是什么」时，"
                "如果直接背出 <code>CE + L1 + GIoU</code>，面试官会追问「那你说的 CE 是 <code>-log p</code> 吗？"
                "为什么」。<strong>面试官想听的是：匹配阶段不需要梯度，所以可以（也应该）用无量纲、有界的 <code>-p</code>，"
                "让三项可比；损失阶段需要梯度，所以用 <code>-log p</code>。</strong>"
                "这一句话能立刻把「读过论文」和「看过博客摘要」区分开。", "别把代价和损失混为一谈"),
    ])),

    ("formula", "Hungarian loss 的完整公式：逐项拆开", "".join([
        P("先把整个式子摆出来，再逐项解释每一项为什么长这样。设网络输出 N 个预测 "
          "<code>{(p̂<sub>i</sub>, b̂<sub>i</sub>)}</code>，GT 集合用 ∅ 补齐到 N 个 "
          "<code>{(c<sub>i</sub>, b<sub>i</sub>)}</code>，σ* 是模块 01 求出的最优排列："),
        MATH("\\mathcal{L}_{\\mathrm{Hungarian}}(y,\\hat{y}) \\;=\\; \\sum_{i=1}^{N}\\Big[\\, "
             "-\\lambda_{\\mathrm{cls}}\\,w_{c_i}\\log \\hat{p}_{\\sigma^*(i)}(c_i) "
             "\\;+\\; \\mathbb{1}_{\\{c_i \\neq \\varnothing\\}}\\;\\mathcal{L}_{\\mathrm{box}}"
             "\\big(b_i,\\hat{b}_{\\sigma^*(i)}\\big)\\,\\Big]"),
        MATH("\\mathcal{L}_{\\mathrm{box}}(b,\\hat{b}) \\;=\\; "
             "\\lambda_{\\mathrm{L1}}\\,\\lVert b-\\hat{b}\\rVert_1 \\;+\\; "
             "\\lambda_{\\mathrm{giou}}\\,\\big(1-\\mathrm{GIoU}(b,\\hat{b})\\big)"),
        ASCII("""预测 N=100 个 (p̂, b̂)          GT M=3 个 (c, b)
       │                              │
       └──────────┬───────────────────┘
                  ▼
        [1] 代价矩阵 C  (3 x 100)      ← no_grad，分类项用 -p̂ 而非 -log p̂
                  ▼
        [2] 匈牙利算法 → σ*            ← 一一对应，O(N^3)
                  ▼
        ┌─────────┴──────────────┐
        ▼                        ▼
  匹配上的 3 个 query        其余 97 个 query
  · 分类损失 -log p̂(c)       · 分类损失 -w_∅ · log p̂(∅)   ← eos_coef 降权
  · L1 框损失                 · **没有框损失**（无框可比）
  · GIoU 框损失               ·
        └─────────┬──────────────┘
                  ▼
        [3] 求和 → 反传（每层 decoder 各来一遍 = 辅助损失）"""),
        TABLE(["项", "作用", "去掉它会怎样"], [
            ["分类 CE（前景）", "让被认领的 query 说对类别", "框对了但不知道是什么；分类分数全靠背景项挤出来"],
            ["<strong>分类 CE（∅ 背景）</strong>", "<strong>压制没认领到目标的 query</strong>",
             "<strong>所有 query 都会输出高分前景 → 满屏误检</strong>。这一项是 DETR「不需要 NMS」的另一半原因"],
            ["L1 框损失", "提供<em>处处存在</em>的、方向明确的坐标梯度", "框不相交时 GIoU 梯度很弱，收敛极慢"],
            ["GIoU 框损失", "提供<strong>尺度无关</strong>的重叠度监督", "大框主导梯度，小目标（TSR 的主体）几乎学不动"],
            ["<code>1</code><sub>{c≠∅}</sub> 指示函数", "背景 query 不算框损失", "背景 query 的框会被拉向某个无意义目标，浪费容量还污染梯度"],
        ]),
        CALLOUT("intuition", "把式子读成一句话：<strong>「每个 query 都要回答『我是什么』；"
                "只有被认领的 query 还要回答『在哪、多大』」</strong>。"
                "整个 DETR 的损失就这两句。<em>后面所有 DETR 变体的损失改动，"
                "都只是在这两句话里换零件：把 CE 换成 focal、把 L1 换成分布回归、"
                "把 GIoU 换成别的 IoU 变体、或者给「我是什么」的目标加上定位质量。</em>"),
    ])),

    ("noobject", "no-object 权重：背景 query 占 97%，不降权就废了", "".join([
        P("先算一笔具体的账。DETR 默认 <code>N=100</code>。COCO 一张图平均 7.7 个实例，"
          "所以典型情况下 <strong>92 个 query 被匹配到 ∅</strong>。"
          "而在<strong>交通标志检测（TSR）场景里这个比例更极端</strong>："
          "一张高速公路前视图像上通常只有 1–3 块标志，"
          "意味着 <strong>97–99 个 query 的监督信号全是「你是背景」</strong>。"),
        MATH("\\underbrace{\\frac{97}{100}}_{\\text{背景 query 占比}} \\;\\times\\; "
             "\\underbrace{1.0}_{w_\\varnothing=1 \\text{ 时的权重}} \\;=\\; 0.97 \\quad "
             "\\text{vs} \\quad \\underbrace{\\frac{3}{100}}_{\\text{前景}} \\times 1.0 = 0.03"),
        P("如果不降权，分类损失里 <strong>97% 的信号在说「输出背景」</strong>。"
          "梯度下降的第一件事就是找到那个能立刻把 97% 的损失干掉的解——"
          "<em>所有 query 一律预测背景</em>。这不是理论担忧，是真实的训练崩溃模式："
          "loss 快速下降、mAP 恒为 0。"),
        P("DETR 的做法是给 ∅ 类一个固定权重 <code>eos_coef = 0.1</code>："),
        TABLE(["<code>eos_coef</code>", "有效背景/前景权重比（N=100, M=3）", "症状", "适用场景"], [
            ["<strong>1.0</strong>（不降权）", "97 : 3 ≈ 32:1", "<strong>全部预测背景，mAP≈0</strong>", "❌ 从不"],
            ["<strong>0.1</strong>（DETR 默认）", "9.7 : 3 ≈ 3.2:1", "平衡；标准配置", "✅ softmax CE 版 DETR"],
            ["0.02", "1.94 : 3 ≈ 0.65:1", "误检明显增多，score 普遍偏高", "召回优先、下游有强过滤时"],
            ["0（完全不管背景）", "0 : 3", "<strong>每个 query 都成前景 → 退化回需要 NMS</strong>", "❌ 从不"],
            ["<em>改用 focal loss</em>", "由 γ 自动调节", "无需手调；<strong>后续工作的主流</strong>", "✅ Deformable DETR / DINO"],
        ]),
        DUAL(
            "<code>eos_coef</code> 的调法有个反直觉之处：<strong>它不该按「前景背景比例」精确配平</strong>。"
            "如果真的配成 1:1，模型会变得极其激进——因为「误报一个前景」的代价被压到和「漏掉一个前景」一样低。"
            "<em>实际上 0.1 得到的 9.7:3 仍然是背景占优，这是刻意的</em>："
            "在检测里，<strong>让 query 默认沉默、只在有足够证据时才发声</strong>，才能得到干净的输出集合。",
            "更本质地看，<code>eos_coef</code> 调的是模型输出的<strong>工作点（operating point）</strong>，"
            "而不是「是否学得会」。它和推理时的 score 阈值高度耦合：<em>降低 eos_coef 等价于整体抬高 score，"
            "然后你必须相应提高推理阈值，最终 PR 曲线可能几乎不动</em>。"
            "所以调它之前先问：你要的是 PR 曲线整体外扩（那要改数据/架构），"
            "还是只是换工作点（那调阈值更直接、且不用重训）。"
            "<strong>「调 eos_coef」和「调 score 阈值」的区别，是一个很好的深度探针问题。</strong>",
        ),
        CALLOUT("danger", "在 <strong>TSR 这类误检代价高度不对称</strong>的场景里，"
                "把 <code>eos_coef</code> 调小来「提高召回」是危险的：<em>误检一块限速牌，"
                "下游可能真的去执行一个错误的限速约束</em>。"
                "正确做法是<strong>把召回问题留给数据与架构（小目标增强、多尺度、copy-paste），"
                "把工作点留给标定后的置信度阈值</strong>——而不是用损失权重去偷换工作点。"),
    ])),

    ("l1-giou", "为什么必须 L1 + GIoU 组合：两个互补的洞", "".join([
        P("这是本模块最重要的一节，也是白板题的高频出处。结论先行："
          "<strong>L1 提供尺度敏感但处处存在的梯度，GIoU 提供尺度无关但在远离时衰减的梯度；"
          "它们各自都有一个致命的洞，恰好被对方补上。</strong>"),
        H3("洞一：L1 对尺度敏感 —— 同样的绝对误差，对小框是灾难，对大框无所谓"),
        P("DETR 预测的是归一化坐标 <code>(cx, cy, w, h) ∈ [0,1]<sup>4</sup></code>。"
          "在 640×640 的输入上，一个 <strong>8×8 像素的交通标志</strong>归一化宽高是 0.0125；"
          "一辆 <strong>64×64 像素的车</strong>是 0.1。现在两个框都<strong>对角偏移 2 像素</strong>："),
        TABLE(["目标", "像素尺寸", "对角偏移", "L1 误差（归一化）", "IoU", "1 − IoU"], [
            ["<strong>远处限速牌</strong>", "8 × 8", "2 px", "0.00625（cx+cy 各 0.003125）",
             "<strong>36/92 = 0.391</strong>", "<strong>0.609</strong>"],
            ["近处车辆", "64 × 64", "2 px", "0.00625（完全相同）", "3844/4348 = 0.884", "0.116"],
            ["大型广告牌", "256 × 256", "2 px", "0.00625（完全相同）", "0.969", "0.031"],
        ]),
        P("<strong>三个目标的 L1 损失完全相同，但实际定位质量（1−IoU）差了 20 倍。</strong>"
          "如果只用 L1，网络会认为「把大车的框修准 2 像素」和「把远处限速牌的框修准 2 像素」"
          "同样重要——<em>而后者决定了这块牌子能不能被判定为检出</em>。"
          "反过来，只用 L1 时大目标的绝对误差天然更大（一个 0.5×0.5 的大框偏 10% 就是 0.05 的 L1），"
          "<strong>大目标会主导梯度，小目标被淹没</strong>。这对 TSR 是致命的。"),
        MATH("\\text{1D 情形的解析解：宽 } w \\text{ 的框沿 } x \\text{ 平移 } d\\;(0\\le d< w) "
             "\\;\\Longrightarrow\\; \\mathrm{IoU}(d) = \\frac{w-d}{w+d}, \\qquad "
             "\\left|\\frac{\\partial \\mathrm{IoU}}{\\partial d}\\right|_{d=0} = \\frac{2}{w}"),
        P("最后那个导数是全节的关键：<strong>IoU 对位移的敏感度与框宽成反比</strong>。"
          "8 像素的框，敏感度是 64 像素框的 8 倍。"
          "<em>这正是 IoU 系损失「尺度无关」的数学含义——它自动帮你把小目标的误差放大回来。</em>"),
        H3("洞二：IoU 在两框不相交时梯度恒为零"),
        P("如果两个框完全不重叠，<code>I = 0</code>，于是 <code>IoU = 0</code>，"
          "而且<strong>无论预测框往哪个方向挪、挪多远，IoU 都还是 0</strong>——"
          "梯度精确为零，不是「很小」，是<strong>数学上的零</strong>。"
          "这是一整片<span class=\"term\">plateau</span>（平台区），优化器在上面完全收不到方向信号。"),
        P("这在 DETR 里不是边缘情形而是<strong>常态</strong>："
          "训练初期 100 个 query 的框是随机初始化的，"
          "<em>绝大多数预测框和它被匹配到的 GT 根本不相交</em>。"
          "如果只用 IoU 损失，训练根本启动不了。"),
        ASCII("""       梯度存在吗？
                 不相交              相交但不完美          完美重合
                ┌────────┐         ┌────┬───┐          ┌────────┐
  pred          │        │         │    │▓▓▓│          │▓▓▓▓▓▓▓▓│
  gt                       ┌────┐  └────┼───┤          └────────┘
                           │    │       └───┘
                           └────┘
  IoU          ❌ 梯度 = 0          ✅ 有梯度            ✅ 梯度 = 0（已最优）
  GIoU         ✅ 有梯度（推近）    ✅ 有梯度            ✅ 梯度 = 0
  L1           ✅ 有梯度            ✅ 有梯度            ✅ 梯度 = 0
                 ↑
        **只有这一列出问题，而它恰好是训练初期的常态**"""),
        DUAL(
            "<strong>GIoU 补的就是这个洞</strong>：它在 IoU 之外减去一项「最小外接框中的空白比例」。"
            "两框离得越远，最小外接框 C 越大，空白 <code>(|C| − |U|)/|C|</code> 越接近 1，"
            "<code>GIoU → −1</code>。<em>于是「把两个不相交的框推近」这个动作，"
            "会稳定地降低损失</em>——梯度回来了。GIoU 的值域是 <code>[−1, 1]</code>，"
            "而 IoU 只有 <code>[0, 1]</code>，多出来的负半轴正是用来编码「有多不相交」。",
            "但 GIoU 也有它自己的退化：<strong>当一个框完全包含另一个框时，"
            "最小外接框 C 就等于大框，<code>|C| = |U|</code>，惩罚项归零，GIoU 退化成 IoU</strong>。"
            "此时 GIoU 无法区分「小框在大框中心」和「小框贴在大框边缘」——两者 GIoU 相同。"
            "<em>这正是 DIoU 引入中心点距离项要解决的问题</em>。"
            "另外 GIoU 在框远离时的梯度会随距离衰减（因为 |C| 变大，惩罚项对位移的导数变小），"
            "收敛速度不如 L1 直接——<strong>所以 L1 也不能去掉。</strong>",
        ),
        CALLOUT("intuition", "一句话记住分工：<strong>L1 负责「把框拽到大致位置」（快、方向明确、但对尺度不公平），"
                "GIoU 负责「把框调到形状贴合」（尺度公平、但远处梯度弱）</strong>。"
                "DETR 的权重 <code>λ<sub>L1</sub>=5, λ<sub>giou</sub>=2</code> 也印证了这个分工："
                "<em>归一化坐标下 L1 的数值只有 1e-2 量级，不乘 5 根本发不出声音；"
                "而 (1−GIoU) 本身就有 0.1–2 的量级，乘 2 即可。</em>"
                "<strong>面试被问「为什么是 5 和 2」，答「量纲配平」比答「实验调出来的」高一个层次。</strong>"),
    ])),

    ("iou-family", "IoU 家族：GIoU / DIoU / CIoU 的定义与各自补的洞", "".join([
        P("四个损失是一条清晰的递进链，<strong>每一个都精确地补上前一个的一个失效场景</strong>。"
          "记住这条链，比记住四个公式有用得多。"),
        MATH("\\mathrm{IoU} = \\frac{|A\\cap B|}{|A\\cup B|} \\qquad\\qquad "
             "\\mathrm{GIoU} = \\mathrm{IoU} - \\frac{|C \\setminus (A\\cup B)|}{|C|} "
             "= \\mathrm{IoU} - 1 + \\frac{|A\\cup B|}{|C|}"),
        MATH("\\mathrm{DIoU} = \\mathrm{IoU} - \\frac{\\rho^2(\\mathbf{c}_A,\\mathbf{c}_B)}{d_C^2} "
             "\\qquad\\qquad \\mathrm{CIoU} = \\mathrm{DIoU} - \\alpha v"),
        MATH("v = \\frac{4}{\\pi^2}\\left(\\arctan\\frac{w_B}{h_B} - \\arctan\\frac{w_A}{h_A}\\right)^2, "
             "\\qquad \\alpha = \\frac{v}{(1-\\mathrm{IoU}) + v}"),
        P("其中 <code>C</code> 是两框的<strong>最小外接矩形</strong>，"
          "<code>ρ</code> 是两框<strong>中心点欧氏距离</strong>，"
          "<code>d<sub>C</sub></code> 是 <code>C</code> 的<strong>对角线长度</strong>，"
          "<code>v</code> 度量<strong>宽高比不一致度</strong>，<code>α</code> 是自适应权重"
          "（重叠度越高，宽高比项越重要）。"),
        TABLE(["损失", "补的洞", "新增惩罚项", "退化/失效场景", "典型用途"], [
            ["<strong>IoU</strong>", "—（基准）", "—",
             "<strong>不相交时梯度恒为 0</strong>", "评测指标；一般不直接当损失"],
            ["<strong>GIoU</strong>", "不相交无梯度", "外接框中的空白面积占比",
             "<strong>包含关系时退化回 IoU</strong>；远距离时梯度衰减、收敛慢", "<strong>DETR 系默认</strong>"],
            ["<strong>DIoU</strong>", "包含关系无区分度", "中心点距离 / 外接框对角线",
             "<strong>中心重合但宽高比不同时无区分</strong>", "NMS 的距离感知版（DIoU-NMS）"],
            ["<strong>CIoU</strong>", "宽高比未被约束", "宽高比一致性 <code>αv</code>",
             "<code>α</code> 通常被 detach，梯度非严格；宽高极端时 <code>v</code> 数值不稳",
             "YOLO 系常用（v5/v8 默认）"],
            ["<em>（后续）</em> SIoU / EIoU / MPDIoU", "角度、宽高绝对差、顶点距离", "各自不同",
             "增益边际、依赖数据分布", "调参空间；小目标可考虑 NWD（见 C57）"],
        ]),
        DUAL(
            "<strong>为什么 DETR 选 GIoU 而不是更「先进」的 CIoU？</strong>"
            "两个原因。① DETR 的框损失里已经有 L1 项，而 L1 对 <code>(cx, cy)</code> 和 "
            "<code>(w, h)</code> <em>都</em>直接施加约束——DIoU 的中心项和 CIoU 的宽高比项"
            "在很大程度上被 L1 覆盖了，收益重叠。② GIoU 值域对称、数值最稳，"
            "而 CIoU 的 <code>α</code> 在实现里是 detach 的，"
            "<em>意味着 CIoU 的「梯度」不是它自身的真实梯度</em>——这在需要严格数值验证的场合是个负担。",
            "反过来，<strong>YOLO 系用 CIoU 是因为它们没有 L1 项</strong>（anchor-free 的框回归直接用 IoU 系损失），"
            "所以中心距离与宽高比必须由 IoU 损失自己承担。<em>这是一个很好的例子："
            "损失函数的选择依赖于整个损失组合，脱离上下文比较「哪个 IoU 变体更好」是无意义的。</em>"
            "<strong>面试里如果对方问「GIoU 和 CIoU 哪个好」，最好的回答是先反问「在什么损失组合里」</strong>——"
            "这比直接站队更能显示你真的用过。",
        ),
        CALLOUT("warn", "实现上的三个必查点：① <strong>并集要减掉交集</strong>"
                "（<code>U = A + B − I</code>，写成 <code>A + B</code> 是最常见的低级 bug，"
                "会让 IoU 恒小于真值）；② <strong>交集的宽高必须 clamp 到 ≥0</strong>"
                "（不 clamp 时两个负数相乘会得到<em>正的假交集</em>——这个 bug 极其隐蔽，"
                "因为只在完全不相交时触发，单元测试如果只测相交情形就查不出来）；"
                "③ <strong>除零保护</strong>（退化框 <code>w=0</code> 或 <code>h=0</code> 会让 U=0）。"),
    ])),

    ("gradients", "解析梯度：手推 IoU / GIoU 对四个坐标的导数", "".join([
        P("<strong>「在白板上写出 IoU 的解析梯度」是检测岗最高频的手写题之一</strong>，"
          "因为它同时考察：链式法则、<code>max/min</code> 的次梯度处理、以及你是否真的知道"
          "「不相交时梯度为零」这句话在代码里长什么样。本节把它推完，notebook 里用数值梯度逐项校验。"),
        P("记预测框 <code>a = (x₁, y₁, x₂, y₂)</code>（视为变量），GT 框 <code>b</code>（常量）。"
          "定义交集边界与面积："),
        ASCII("""ix1 = max(a.x1, b.x1)      ix2 = min(a.x2, b.x2)
iy1 = max(a.y1, b.y1)      iy2 = min(a.y2, b.y2)
iw  = max(0, ix2 - ix1)    ih  = max(0, iy2 - iy1)
I   = iw * ih
Aa  = (a.x2-a.x1)(a.y2-a.y1)      Ab = (b.x2-b.x1)(b.y2-b.y1)
U   = Aa + Ab - I
IoU = I / U

外接框：cx1 = min(a.x1,b.x1)  cx2 = max(a.x2,b.x2)   （y 同理）
Ac  = (cx2-cx1)(cy2-cy1)
GIoU = IoU - (Ac - U)/Ac = IoU - 1 + U/Ac"""),
        H3("第一步：交集面积 I 对 a 的导数（关键在指示函数）"),
        MATH("\\frac{\\partial I}{\\partial a_{x_1}} = -\\,ih \\cdot \\mathbb{1}[a_{x_1} > b_{x_1}] "
             "\\cdot \\mathbb{1}[iw>0]\\mathbb{1}[ih>0], \\qquad "
             "\\frac{\\partial I}{\\partial a_{x_2}} = +\\,ih \\cdot \\mathbb{1}[a_{x_2} < b_{x_2}] "
             "\\cdot \\mathbb{1}[iw>0]\\mathbb{1}[ih>0]"),
        P("解释：<code>ix1 = max(a.x1, b.x1)</code>，只有当 <code>a.x1</code> 是那个较大者时，"
          "动它才会改变 <code>ix1</code>——这就是指示函数 <code>1[a.x1 > b.x1]</code> 的来源。"
          "而 <code>iw = ix2 − ix1</code>，所以 <code>∂iw/∂a.x1 = −1[a.x1 > b.x1]</code>，"
          "再乘上 <code>ih</code> 得到面积导数。<strong>最外层的 <code>1[iw>0]1[ih>0]</code> "
          "就是「不相交时梯度为零」在代码里的样子</strong>——也是白板题最容易漏的一项。"),
        H3("第二步：并集与 IoU"),
        MATH("\\frac{\\partial A_a}{\\partial a} = (-h_a,\\; -w_a,\\; +h_a,\\; +w_a), \\qquad "
             "\\frac{\\partial U}{\\partial a} = \\frac{\\partial A_a}{\\partial a} - \\frac{\\partial I}{\\partial a}"),
        MATH("\\frac{\\partial\\, \\mathrm{IoU}}{\\partial a} = "
             "\\frac{\\frac{\\partial I}{\\partial a}\\,U - I\\,\\frac{\\partial U}{\\partial a}}{U^2}"),
        H3("第三步：GIoU 的额外一项"),
        MATH("\\frac{\\partial\\, \\mathrm{GIoU}}{\\partial a} = "
             "\\frac{\\partial\\, \\mathrm{IoU}}{\\partial a} + "
             "\\frac{\\frac{\\partial U}{\\partial a}A_c - U\\,\\frac{\\partial A_c}{\\partial a}}{A_c^2}, "
             "\\qquad \\frac{\\partial A_c}{\\partial a_{x_1}} = -\\,c_h\\cdot\\mathbb{1}[a_{x_1} < b_{x_1}]"),
        P("注意外接框的指示函数<strong>方向和交集相反</strong>："
          "<code>cx1 = min(...)</code>，所以只有 <code>a.x1</code> 更<em>小</em>时它才起作用。"
          "<em>这个「一个取 max 一个取 min，指示函数方向相反」的对称性，是手推时最容易写反的地方。</em>"),
        CALLOUT("danger", "<strong>白板题评分要点（面试官在心里的 checklist）</strong>："
                "① 有没有写出 <code>U = Aa + Ab − I</code> 而不是 <code>Aa + Ab</code>；"
                "② 有没有对 <code>iw, ih</code> 做 clamp，并且<strong>在梯度里体现出 clamp 的截断</strong>；"
                "③ 有没有意识到 <code>max/min</code> 会产生指示函数（而不是当成常数）；"
                "④ 能否说出「不相交 ⇒ 梯度恒 0 ⇒ 所以要 GIoU」；"
                "⑤ 加分项：主动说「实际训练中预测的是 <code>(cx,cy,w,h)</code>，"
                "还要再套一层从 <code>(x1,y1,x2,y2)</code> 到 <code>(cx,cy,w,h)</code> 的链式法则」——"
                "<em>notebook 的练习 4 就是这一步。</em>",
                "白板题：IoU 的解析梯度"),
        DUAL(
            "为什么要手推而不是「反正 autograd 会算」？三个实际理由。"
            "① <strong>调试</strong>：训练中出现 NaN 时，你需要知道 <code>U=0</code>（退化框）和 "
            "<code>Ac=0</code> 是唯二的除零来源，才能定位。"
            "② <strong>部署</strong>：车端 C++ 侧如果要做在线的框精修或跟踪滤波，autograd 不在了。"
            "③ <strong>理解</strong>：只有把 <code>1[iw>0]</code> 这一项写出来，"
            "「IoU 不相交无梯度」才从一句口号变成一个你亲眼见过的乘子。",
            "数值上还有一处必须注意：<code>max/min</code> 在<strong>相等点不可导</strong>"
            "（<code>a.x1 == b.x1</code>），此时任何一侧的次梯度都合法。"
            "PyTorch 的 <code>torch.max</code> 在 tie 时把梯度全给第一个参数，"
            "<em>这个约定与你手写的实现可能不一致，从而导致极小概率的对拍失败</em>。"
            "所以<strong>数值梯度校验时要避开退化配置</strong>（用随机连续坐标即可，"
            "tie 是零测集）；反过来，如果你的对拍在随机输入上就有 1% 的失败率，"
            "那多半不是 tie 而是真 bug。",
        ),
    ])),

    ("aux-loss", "辅助损失：为什么「每层 decoder 都算一遍」能把收敛砍掉一大半", "".join([
        P("DETR 的 decoder 有 6 层。默认配置下，<strong>每一层的输出都接同一套（共享权重的）"
          "分类头与框头，各自独立做一次匈牙利匹配、各自算一份完整的 Hungarian loss，"
          "最后全部相加</strong>。这叫 <span class=\"term\">auxiliary decoding losses</span>（辅助损失），"
          "是 DETR 里性价比最高的一个设计——论文的消融显示去掉它 AP 掉约 2 点，且收敛显著变慢。"),
        ASCII("""            ┌──── decoder L1 ──→ head ──→ 匹配 σ1 ──→ loss1  ┐
 queries ──→ ├──── decoder L2 ──→ head ──→ 匹配 σ2 ──→ loss2  │
             ├──── decoder L3 ──→ head ──→ 匹配 σ3 ──→ loss3  │  Σ → 反传
             │        ...                                     │
             └──── decoder L6 ──→ head ──→ 匹配 σ6 ──→ loss6  ┘
                                    ↑              ↑
                          **权重共享的同一个头**   **每层独立匹配**
                          （所以中间层的输出       （所以 σ 可能层间不同，
                            与最终输出可比）         这本身就是个诊断信号）""",),
        TABLE(["收益", "机制", "证据/数字"], [
            ["<strong>梯度直达浅层</strong>", "第 1 层 decoder 不必等梯度穿过 5 层才收到信号",
             "深度监督（deep supervision）的标准论证；ResNet/GoogLeNet 时代就验证过"],
            ["<strong>逼出「逐层精修」的归纳偏置</strong>",
             "每层都被要求输出一个<em>可用的</em>框 → 后层只需在前层基础上改进",
             "这直接催生了 DAB-DETR / DINO 的 <em>iterative box refinement</em>（见模块 03/04）"],
            ["<strong>正则化</strong>", "6 份损失相当于 6 个「早停点」，抑制最后一层过拟合", "论文消融：AP +2.0 左右"],
            ["<strong>免费的诊断信号</strong>", "对比各层的匹配 σ，可算<em>层间匹配翻转率</em>",
             "翻转率高 ⇒ 各层「认领」的目标不一致 ⇒ 优化目标在抖（连到模块 04）"],
        ]),
        P("代价也要说清楚：<strong>匈牙利匹配是在 CPU 上做的 O(N³) 运算</strong>，"
          "6 层就是 6 次。当 <code>N=900</code>（DINO）时这已经不可忽略，"
          "是 DETR 系训练吞吐的一个真实瓶颈。"
          "显存方面，需要保留 6 层的中间输出用于反传——<em>这也是 DETR 系显存占用偏高的原因之一</em>。"),
        DUAL(
            "<strong>推理时辅助头全部丢掉，只用最后一层</strong>。"
            "这带来一个非常实用的部署性质：<em>既然每一层的输出都是「可用的」，"
            "那就可以在推理时只跑前 k 层</em>。RT-DETR 正是靠这一点做到"
            "<strong>「同一份权重支持多档速度-精度，无需重训」</strong>——"
            "车端算力紧张时跑 3 层，空闲时跑 6 层。<em>辅助损失从一个训练技巧变成了部署能力。</em>",
            "更细的一点：DINO 等两阶段变体还会给 <strong>encoder 输出</strong>加一份损失"
            "（把 encoder 的 top-k 提议当作「第 0 层」的预测来监督）。"
            "此时损失项变成 <code>6 × decoder + 1 × encoder + DN 分支</code>，"
            "<em>总共可能有十几份 Hungarian loss 在同时反传</em>。"
            "这时候<strong>各份损失的权重就不再能靠直觉，必须做敏感性分析</strong>——"
            "而一个常被忽略的事实是：辅助层的权重通常直接取 1.0（与最后一层同权），"
            "这是个从未被认真消融过的默认值。",
        ),
        CALLOUT("intuition", "把辅助损失理解成<strong>「把一个 6 步的推理过程，改造成 6 个各自可评分的 1 步」</strong>。"
                "这个模式在 Transformer 之外也到处出现（扩散模型的每步去噪损失、"
                "级联检测器 Cascade R-CNN 的每级损失）。"
                "<em>共同的心法是：当你有一个深的、串行的精修过程，"
                "而每个中间状态本身也有明确语义时，就应该给每个中间状态配一份监督。</em>"),
    ])),

    ("weights-focal", "损失权重配比，以及从 CE 到 focal 的演进", "".join([
        H3("DETR 的默认配比与它的量纲逻辑"),
        TABLE(["项", "权重", "典型数值量级（训练中期）", "加权后贡献", "为什么是这个权重"], [
            ["分类 CE", "λ<sub>cls</sub> = 1", "0.2 – 1.5", "0.2 – 1.5", "基准，其余项向它对齐"],
            ["<strong>L1 框损失</strong>", "<strong>λ<sub>L1</sub> = 5</strong>",
             "<strong>0.02 – 0.15</strong>（归一化坐标）", "0.1 – 0.75",
             "<strong>不放大 5 倍就淹没在分类项里</strong>"],
            ["<strong>GIoU 框损失</strong>", "<strong>λ<sub>giou</sub> = 2</strong>", "0.1 – 1.0", "0.2 – 2.0",
             "本身量级已可比，2 倍是为了让它略压过 L1（尺度公平性优先）"],
            ["no-object 权重", "<code>eos_coef</code> = 0.1", "—", "—", "见第 3 节"],
        ]),
        P("<strong>记住这个「量纲配平」的思路，比记住 1/5/2 这三个数字重要得多。</strong>"
          "如果你把坐标从 <code>[0,1]</code> 归一化改成像素坐标（0–640），"
          "L1 的量级会放大 640 倍，<code>λ<sub>L1</sub>=5</code> 立刻变成灾难。"
          "<em>损失权重从来不是绝对的，它是相对于「你的表示」的。</em>"),
        H3("为什么后续工作把 CE 换成了 focal loss"),
        MATH("\\mathrm{FL}(p_t) = -\\alpha_t\\,(1-p_t)^{\\gamma}\\log(p_t), \\qquad "
             "\\alpha = 0.25,\\; \\gamma = 2 \\;(\\text{Deformable DETR / DINO 默认})"),
        TABLE(["", "DETR（softmax CE）", "Deformable DETR / DINO（sigmoid focal）"], [
            ["输出层", "softmax over <code>K+1</code> 类（含显式 ∅ 类）",
             "<strong>K 个独立 sigmoid，无 ∅ 类</strong>（全部低 = 背景）"],
            ["类间关系", "互斥竞争", "<strong>互相独立</strong>"],
            ["背景抑制", "靠手调 <code>eos_coef=0.1</code>", "<strong>靠 <code>(1−p)<sup>γ</sup></code> 自动降权易分样本</strong>"],
            ["典型 query 数", "100", "<strong>300 / 900</strong>"],
            ["匹配代价的分类项", "<code>−p̂(c)</code>", "<strong>focal 形式的代价</strong>（正负项之差）"],
            ["推理取框", "argmax 后按 score 排序", "<strong>所有 (query, 类) 对里取 top-k</strong>（一个 query 可出多类）"],
        ]),
        DUAL(
            "换 focal 的<strong>根本理由是 softmax 与一对一匹配的哲学不兼容</strong>。"
            "softmax 强迫 <code>K+1</code> 个类互相抢概率质量，"
            "但集合预测里每个 query 是<em>独立地</em>在回答「我认领的这个东西是什么」——"
            "它和别的 query 认领什么无关，也不该和「我是不是背景」做零和竞争。"
            "<em>sigmoid + focal 把「是不是前景」和「是哪一类」解耦，正好匹配这个语义。</em>",
            "实践收益也很直接：① <strong>省掉 <code>eos_coef</code> 这个超参</strong>"
            "（focal 的 <code>(1−p)<sup>γ</sup></code> 自动把大量「已经预测得很低的背景 query」的梯度压下去）；"
            "② <strong>支持把 N 从 100 提到 900</strong>——softmax 版在 N 增大时背景项会失控，"
            "而 focal 版几乎不受影响；③ 推理时在 <code>N×K</code> 个 (query, 类) 对里取 top-100，"
            "<em>允许同一个 query 在两个易混类上都出框</em>，这对 <strong>TSR 里「限速 60 / 限速 80」"
            "这类极易混淆的标志对是有实际价值的</strong>——下游可以拿到第二候选做时序投票，"
            "而 softmax 版的第二候选被压得几乎没有分数。",
        ),
        CALLOUT("warn", "换成 focal 后有一个必须同步改的地方：<strong>推理阈值的语义变了</strong>。"
                "softmax 版的 score 是「在所有类里的相对份额」，天然归一化；"
                "sigmoid 版的 score 是「这一类的独立置信度」，"
                "<em>多个类可以同时是 0.9，也可以全部是 0.1</em>。"
                "把 softmax 时代的阈值（如 0.7）原样搬到 sigmoid 版上，"
                "召回会莫名其妙地掉一大截。<strong>对 TSR 这种需要把置信度传给下游做时序融合的系统，"
                "换损失之后必须重新做置信度标定（calibration），否则下游的贝叶斯累积会全盘失准。</strong>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("集合损失看起来只是「三项加权和」，但它其实是 DETR 系近五年改动最密集的地方。"
          "下面几条是<strong>目前仍未收敛的问题</strong>，也是读论文时值得盯的方向。"),
        UL([
            "<strong>匹配代价与损失不一致的理论缺口</strong>：匹配用 <code>−p</code>、损失用 <code>−log p</code>，"
            "这意味着<em>「谁被选中」和「选中后往哪优化」用的不是同一个目标</em>。"
            "Stable-DINO / position-supervised loss 一类工作指出这会导致训练不稳定，"
            "并提出把<strong>定位质量直接写进分类目标</strong>（分类标签不再是 0/1 而是 IoU）来弥合。"
            "这条线与 Varifocal Loss、Quality Focal Loss（GFL）是同一个思想的不同分支。",

            "<strong>一对多辅助分支的回归</strong>：Group DETR / H-DETR / Co-DETR 在训练时"
            "额外挂一条一对多监督的分支（推理时丢弃），显著加速收敛并提点。"
            "<em>这在理论上很值得玩味：它说明「一对一」是<strong>推理端的需求</strong>（去 NMS），"
            "而不是<strong>训练端的最优</strong>（监督太稀疏）。</em>"
            "把训练目标和推理约束解耦，可能是这条线最重要的启示。",

            "<strong>框回归的表示之争</strong>：L1 直接回归四个数是最朴素的做法。"
            "GFL / D-FINE 改为<strong>预测每条边的概率分布</strong>（把回归变成分类），"
            "既能表达定位不确定性，又能提供更丰富的梯度。"
            "<em>对 TSR 这种需要把定位不确定性传给时序融合的系统，分布式表示的价值可能被低估了。</em>",

            "<strong>IoU 变体的长尾</strong>：SIoU（角度感知）、EIoU（宽高绝对差）、"
            "WIoU（动态聚焦）、α-IoU（幂次调节）、MPDIoU（顶点距离）……"
            "<em>大多数只在特定数据集上有零点几个点的增益，缺少跨数据集的一致结论</em>。"
            "更值得注意的是<strong>为小目标专门设计的度量</strong>——"
            "NWD（把框建模成 2D 高斯，用 Wasserstein 距离）在不相交时仍有平滑梯度、"
            "且对尺度不敏感，<strong>这正是 TSR 远距离小标志最需要的性质</strong>（详见 C57 模块 03）。",

            "<strong>匹配的可微化</strong>：匈牙利匹配是离散的、不可导的。"
            "有工作尝试用 Sinkhorn 迭代做<em>软匹配</em>（可微的最优传输），"
            "或用 top-k 软选择替代硬匹配。<em>目前尚未证明比硬匹配更好</em>，"
            "但它触及一个根本问题：<strong>「先匹配再算损失」这个两阶段结构本身是不是必要的？</strong>",

            "<strong>开放问题：什么才是「正确」的集合损失？</strong>"
            "现有损失都是「先建立对应，再逐对算距离」。"
            "而集合之间本来有更自然的距离（Chamfer、Wasserstein、最优传输）。"
            "<em>为什么检测里几乎没人用这些？主要障碍是：它们不强制一一对应，"
            "于是无法在训练期压制重复框——而这恰恰是 DETR 去掉 NMS 的全部依据。</em>",
        ]),
        CALLOUT("paper", "<p><strong>必读（按顺序）</strong>：</p>"
                "<ul>"
                "<li>★ <em>End-to-End Object Detection with Transformers</em>（DETR, Carion et al. ECCV 2020）——"
                "读 §3.1「Object detection set prediction loss」全节 + 附录 A.1 的损失权重表。"
                "<strong>解决什么问题：把检测变成集合预测，并给出第一个可用的集合损失。</strong></li>"
                "<li>★ <em>Generalized Intersection over Union</em>（Rezatofighi et al. CVPR 2019）——"
                "读 §3 与算法 1（GIoU 的解析形式）。<strong>解决什么问题：IoU 在不相交时梯度为零。</strong></li>"
                "<li>★ <em>Distance-IoU Loss</em>（Zheng et al. AAAI 2020）——DIoU 与 CIoU 同一篇。"
                "<strong>解决什么问题：GIoU 在包含关系下退化、收敛慢。</strong></li>"
                "<li><em>Focal Loss for Dense Object Detection</em>（Lin et al. ICCV 2017）——"
                "理解 Deformable DETR / DINO 为何弃用 <code>eos_coef</code>。</li>"
                "<li><em>DINO: DETR with Improved DeNoising Anchor Boxes</em>（Zhang et al. ICLR 2023）——"
                "看它的完整损失组合（decoder 辅助 + encoder + DN 分支）。</li>"
                "<li><em>Detection Transformer with Stable Matching</em>（Stable-DINO, ICCV 2023）——"
                "匹配-损失不一致问题的代表作。</li>"
                "</ul>"
                "<p>相邻课程：模块 01（匈牙利匹配）、模块 04（收敛与 DETR 家族）、"
                "C53 模块 02（标签分配）、C57 模块 03（小目标的 NWD 度量）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · 集合预测损失（IoU 家族 / 解析梯度 / Hungarian loss / no-object 权重）

目标：把 DETR 的集合损失**从零手写一遍**，并用数值梯度证明你推的公式是对的。

**本 notebook 你会亲手实现：**
1. `IoU / GIoU / DIoU / CIoU` —— 四个函数，从坐标算起，含全部退化情形保护
2. **它们的解析梯度**，并用中心差分数值梯度逐项校验（白板高频题）
3. **IoU 梯度死区实验**：把预测框推开，看 IoU 梯度精确变成 0 而 GIoU 不会
4. **L1 的尺度敏感性**：同样 2 px 偏移，8×8 框与 256×256 框的 L1 完全相同、1−IoU 差 20 倍
5. **匈牙利匹配 + 完整 Hungarian loss**（分类 CE + L1 + GIoU + no-object）
6. **no-object 权重的消融**：在合成数据上看前景召回随 `eos_coef` 变化
7. 四道练习：向量化 IoU 矩阵 / DETR 代价矩阵 / 辅助损失与层间翻转率 / cxcywh 参数化的梯度

> 心智模型：**L1 把框拽到大致位置（快但对尺度不公平），
> GIoU 把框调到形状贴合（尺度公平但远处梯度弱）。缺一个都不行。**"""),

    md("""## 1 · IoU 从零实现：三个必查点

① `U = Aa + Ab - I`（不是 `Aa + Ab`）
② 交集宽高必须 clamp 到 ≥0（**不 clamp 时两个负数相乘会得到正的假交集**）
③ 除零保护"""),
    code("""import numpy as np, math, itertools, json
np.set_printoptions(precision=4, suppress=True)
rng = np.random.default_rng(0)

EPS = 1e-12

def box_wh(b):
    '''b = (x1, y1, x2, y2) -> (w, h)'''
    return b[2] - b[0], b[3] - b[1]

def inter_union(a, b):
    '''返回 (I, U, Aa, Ab, iw, ih)。iw/ih 已 clamp。'''
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)   # ← ② clamp，缺了就有「假交集」
    I = iw * ih
    Aa = (a[2] - a[0]) * (a[3] - a[1])
    Ab = (b[2] - b[0]) * (b[3] - b[1])
    U = Aa + Ab - I                                      # ← ① 减掉交集
    return I, U, Aa, Ab, iw, ih

def iou(a, b):
    I, U, *_ = inter_union(a, b)
    return I / (U + EPS)                                 # ← ③ 除零保护

# --- 自校验 ---
g = (0.0, 0.0, 8.0, 8.0)
assert abs(iou(g, g) - 1.0) < 1e-9, '同一个框 IoU 必须是 1'
assert iou(g, (100., 100., 108., 108.)) == 0.0, '完全不相交必须是 0'

# 规范里的关键数字：8x8 的框对角偏移 2 px
shift = (2.0, 2.0, 10.0, 10.0)
I, U, *_ = inter_union(g, shift)
print('8x8 框对角偏移 2px:  I=%.0f  U=%.0f  IoU=%.4f' % (I, U, I / U))
assert abs(iou(g, shift) - 36 / 92) < 1e-9, 'I=6*6=36, U=64+64-36=92'

# 对照：64x64 的框同样偏移 2px
g64 = (0., 0., 64., 64.); s64 = (2., 2., 66., 66.)
print('64x64 框对角偏移 2px: IoU=%.4f' % iou(g64, s64))
assert abs(iou(g64, s64) - 3844 / 4348) < 1e-9

# ② 的反面教材：不 clamp 会怎样
def iou_buggy(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    I = (ix2 - ix1) * (iy2 - iy1)          # ← 没有 clamp！
    Aa = (a[2]-a[0])*(a[3]-a[1]); Ab = (b[2]-b[0])*(b[3]-b[1])
    return I / (Aa + Ab - I)

far = (14., 14., 22., 22.)          # 与 g 完全不相交（间隔 6 px）
print('\\n完全不相交的两个框:  正确 IoU=%.4f   有 bug 的 IoU=%.4f  ← **假交集**'
      % (iou(g, far), iou_buggy(g, far)))
assert iou_buggy(g, far) > 0.3, '两个负数相乘造出了一个虚假的高 IoU'
print('    有 bug 的实现给出 0.391 —— 和「重叠良好的 8x8 框偏移 2px」**一模一样**。')
print('⚠️  这个 bug 只在**完全不相交**时触发 —— 如果单元测试只测相交情形，永远查不出来。')
print('✅ 而在 DETR 训练初期，随机初始化的框和 GT **绝大多数是不相交的**。')"""),

    md("""## 2 · GIoU / DIoU / CIoU：每一个都补上一个具体的洞"""),
    code("""def enclosing(a, b):
    '''最小外接框 C 及其宽高、面积、对角线平方。'''
    cx1, cy1 = min(a[0], b[0]), min(a[1], b[1])
    cx2, cy2 = max(a[2], b[2]), max(a[3], b[3])
    cw, ch = cx2 - cx1, cy2 - cy1
    return cx1, cy1, cx2, cy2, cw, ch, cw * ch, cw * cw + ch * ch

def giou(a, b):
    I, U, *_ = inter_union(a, b)
    *_, Ac, _ = enclosing(a, b)
    return I / (U + EPS) - (Ac - U) / (Ac + EPS)

def center(b):
    return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0

def diou(a, b):
    I, U, *_ = inter_union(a, b)
    *_, _, dc2 = enclosing(a, b)
    (cax, cay), (cbx, cby) = center(a), center(b)
    rho2 = (cax - cbx) ** 2 + (cay - cby) ** 2
    return I / (U + EPS) - rho2 / (dc2 + EPS)

def aspect_v(a, b):
    wa, ha = box_wh(a); wb, hb = box_wh(b)
    d = math.atan2(wb, hb) - math.atan2(wa, ha)
    return (4.0 / math.pi ** 2) * d * d

def ciou(a, b):
    v = aspect_v(a, b)
    i = iou(a, b)
    alpha = v / (1.0 - i + v + EPS)          # 实现里 alpha 通常被 detach
    return diou(a, b) - alpha * v

# --- 性质自校验 ---
for _ in range(200):
    a = np.sort(rng.uniform(-3, 3, 2)); c = np.sort(rng.uniform(-3, 3, 2))
    b = np.sort(rng.uniform(-3, 3, 2)); d = np.sort(rng.uniform(-3, 3, 2))
    A = (a[0], b[0], a[1] + 0.1, b[1] + 0.1)
    B = (c[0], d[0], c[1] + 0.1, d[1] + 0.1)
    i_, g_, di_, ci_ = iou(A, B), giou(A, B), diou(A, B), ciou(A, B)
    assert -1.0 - 1e-9 <= g_ <= i_ + 1e-9, 'GIoU <= IoU 且 >= -1'
    assert di_ <= i_ + 1e-9, 'DIoU <= IoU（多减了一个非负的中心距离项）'
    assert ci_ <= di_ + 1e-9, 'CIoU <= DIoU（多减了一个非负的宽高比项）'

print('%-34s %8s %8s %8s %8s' % ('配置', 'IoU', 'GIoU', 'DIoU', 'CIoU'))
CASES = [
    ('完全重合',              (0,0,4,4),  (0,0,4,4)),
    ('相邻但不相交',          (0,0,4,4),  (5,0,9,4)),
    ('**很远的不相交**',      (0,0,4,4),  (40,0,44,4)),
    ('**包含：小框在中心**',  (0,0,10,10),(4,4,6,6)),
    ('**包含：小框贴左上**',  (0,0,10,10),(0,0,2,2)),
    ('中心重合、宽高比不同',  (0,0,10,10),(2.5,0,7.5,10)),
]
for name, A, B in CASES:
    A = tuple(map(float, A)); B = tuple(map(float, B))
    print('%-30s %8.4f %8.4f %8.4f %8.4f' % (name, iou(A,B), giou(A,B), diou(A,B), ciou(A,B)))

# 关键性质 1：不相交越远，GIoU 越接近 -1（IoU 恒为 0，毫无区分度）
assert iou((0.,0.,4.,4.), (5.,0.,9.,4.)) == iou((0.,0.,4.,4.), (40.,0.,44.,4.)) == 0.0
assert giou((0.,0.,4.,4.), (40.,0.,44.,4.)) < giou((0.,0.,4.,4.), (5.,0.,9.,4.))
# 关键性质 2：包含关系下 GIoU 退化成 IoU（外接框 C == 大框，惩罚项归零）
A, B1, B2 = (0.,0.,10.,10.), (4.,4.,6.,6.), (0.,0.,2.,2.)
assert abs(giou(A,B1) - iou(A,B1)) < 1e-9 and abs(giou(A,B2) - iou(A,B2)) < 1e-9
assert abs(giou(A,B1) - giou(A,B2)) < 1e-9, 'GIoU 对这两种包含关系**完全无区分度**'
print('\\n⚠️  「小框在中心」与「小框贴左上」的 IoU/GIoU **完全相同** —— GIoU 分不出来。')
print('    IoU: %.4f vs %.4f   GIoU: %.4f vs %.4f   **DIoU: %.4f vs %.4f  ← 分开了**'
      % (iou(A,B1), iou(A,B2), giou(A,B1), giou(A,B2), diou(A,B1), diou(A,B2)))
assert diou(A,B1) > diou(A,B2) + 1e-3, 'DIoU 的中心距离项恰好补上这个洞'"""),

    md("""## 3 · 解析梯度：手推 + 数值校验（白板高频题）

`max/min` 会产生**指示函数**；`clamp(·, 0)` 会产生**截断乘子** `1[iw>0]1[ih>0]` ——
这个乘子就是「不相交时梯度恒为 0」在代码里的样子，也是白板题最容易漏的一项。"""),
    code("""def _grad_I_U(a, b):
    '''返回 (I, U, dI/da, dU/da)，a=(x1,y1,x2,y2) 为变量，b 为常量。'''
    I, U, Aa, Ab, iw, ih = inter_union(a, b)
    if iw > 0 and ih > 0:
        dI = np.array([
            -ih * (a[0] > b[0]),      # d I / d x1   （ix1 = max -> 指示 a.x1 更大）
            -iw * (a[1] > b[1]),      # d I / d y1
            +ih * (a[2] < b[2]),      # d I / d x2   （ix2 = min -> 指示 a.x2 更小）
            +iw * (a[3] < b[3]),      # d I / d y2
        ], dtype=float)
    else:
        dI = np.zeros(4)              # ← **截断：不相交则梯度精确为 0**
    wa, ha = box_wh(a)
    dAa = np.array([-ha, -wa, ha, wa], dtype=float)
    dU = dAa - dI
    return I, U, dI, dU

def grad_iou(a, b):
    I, U, dI, dU = _grad_I_U(a, b)
    return (dI * U - I * dU) / (U * U + EPS)

def grad_giou(a, b):
    I, U, dI, dU = _grad_I_U(a, b)
    g_iou = (dI * U - I * dU) / (U * U + EPS)
    _, _, _, _, cw, ch, Ac, _ = enclosing(a, b)
    dAc = np.array([                  # ← 外接框取 min/max，**指示函数方向与交集相反**
        -ch * (a[0] < b[0]),
        -cw * (a[1] < b[1]),
        +ch * (a[2] > b[2]),
        +cw * (a[3] > b[3]),
    ], dtype=float)
    # GIoU = IoU - 1 + U/Ac
    return g_iou + (dU * Ac - U * dAc) / (Ac * Ac + EPS)

def num_grad(f, a, b, eps=1e-6):
    '''中心差分数值梯度。'''
    a = np.asarray(a, float); out = np.zeros(4)
    for k in range(4):
        ap = a.copy(); ap[k] += eps
        am = a.copy(); am[k] -= eps
        out[k] = (f(tuple(ap), b) - f(tuple(am), b)) / (2 * eps)
    return out

# --- 逐项校验：随机框（tie 是零测集，不会踩到 max/min 的不可导点）---
bad = 0
for _ in range(300):
    a = (float(rng.uniform(-2, 2)), float(rng.uniform(-2, 2)), 0., 0.)
    a = (a[0], a[1], a[0] + float(rng.uniform(.3, 3)), a[1] + float(rng.uniform(.3, 3)))
    b = (float(rng.uniform(-2, 2)), float(rng.uniform(-2, 2)), 0., 0.)
    b = (b[0], b[1], b[0] + float(rng.uniform(.3, 3)), b[1] + float(rng.uniform(.3, 3)))
    for f, gf in [(iou, grad_iou), (giou, grad_giou)]:
        if not np.allclose(gf(a, b), num_grad(f, a, b), atol=2e-6):
            bad += 1
assert bad == 0, '解析梯度与数值梯度不一致，共 %d 例' % bad
print('✅ 300 组随机框 x 2 个函数：解析梯度与中心差分数值梯度全部吻合（atol=2e-6）')

a0 = (0.0, 0.0, 4.0, 4.0); b0 = (1.0, 1.5, 6.0, 5.0)
print('\\n示例 a=%s  b=%s' % (a0, b0))
print('  d IoU /d(x1,y1,x2,y2) 解析 =', grad_iou(a0, b0))
print('  d IoU /d(x1,y1,x2,y2) 数值 =', num_grad(iou, a0, b0))
print('  d GIoU/d(x1,y1,x2,y2) 解析 =', grad_giou(a0, b0))
print('  d GIoU/d(x1,y1,x2,y2) 数值 =', num_grad(giou, a0, b0))"""),
    code("""# DIoU / CIoU 的解析梯度（CIoU 按标准实现把 alpha 视作常数 detach）
def grad_diou(a, b):
    I, U, dI, dU = _grad_I_U(a, b)
    g_iou = (dI * U - I * dU) / (U * U + EPS)
    _, _, _, _, cw, ch, _, dc2 = enclosing(a, b)
    (cax, cay), (cbx, cby) = center(a), center(b)
    rho2 = (cax - cbx) ** 2 + (cay - cby) ** 2
    # d rho2 / d x1 = 2(cax-cbx) * d cax/d x1 = 2(cax-cbx) * 0.5
    drho2 = np.array([(cax - cbx), (cay - cby), (cax - cbx), (cay - cby)], float)
    ddc2 = np.array([                          # dc2 = cw^2 + ch^2
        -2 * cw * (a[0] < b[0]),
        -2 * ch * (a[1] < b[1]),
        +2 * cw * (a[2] > b[2]),
        +2 * ch * (a[3] > b[3]),
    ], float)
    return g_iou - (drho2 * dc2 - rho2 * ddc2) / (dc2 * dc2 + EPS)

def grad_ciou(a, b, detach_alpha=True):
    wa, ha = box_wh(a); wb, hb = box_wh(b)
    v = aspect_v(a, b)
    i = iou(a, b)
    alpha = v / (1.0 - i + v + EPS)
    d = math.atan2(wb, hb) - math.atan2(wa, ha)
    # dv/dwa = -(8/pi^2) d * ha/(wa^2+ha^2) ;  dv/dha = +(8/pi^2) d * wa/(wa^2+ha^2)
    k = 8.0 / math.pi ** 2 * d / (wa * wa + ha * ha + EPS)
    dv_dw, dv_dh = -k * ha, k * wa
    dv = np.array([-dv_dw, -dv_dh, dv_dw, dv_dh], float)   # w = x2-x1, h = y2-y1
    g = grad_diou(a, b) - alpha * dv
    if not detach_alpha:                                   # 完整梯度还要过 alpha 里的 IoU
        dalpha_di = v / (1.0 - i + v + EPS) ** 2
        g = g - v * dalpha_di * grad_iou(a, b)
        dalpha_dv = (1.0 - i) / (1.0 - i + v + EPS) ** 2
        g = g - v * dalpha_dv * dv
    return g

bad = 0
for _ in range(300):
    a = (float(rng.uniform(-2, 2)), float(rng.uniform(-2, 2)), 0., 0.)
    a = (a[0], a[1], a[0] + float(rng.uniform(.3, 3)), a[1] + float(rng.uniform(.3, 3)))
    b = (float(rng.uniform(-2, 2)), float(rng.uniform(-2, 2)), 0., 0.)
    b = (b[0], b[1], b[0] + float(rng.uniform(.3, 3)), b[1] + float(rng.uniform(.3, 3)))
    if not np.allclose(grad_diou(a, b), num_grad(diou, a, b), atol=2e-6):
        bad += 1
    if not np.allclose(grad_ciou(a, b, detach_alpha=False), num_grad(ciou, a, b), atol=2e-5):
        bad += 1
assert bad == 0, 'DIoU/CIoU 梯度校验失败 %d 例' % bad
print('✅ DIoU 与 CIoU（完整梯度版）同样通过数值校验')

a0 = (0.0, 0.0, 4.0, 2.0); b0 = (0.5, 0.2, 3.0, 3.5)
print('\\nCIoU 在 a=%s b=%s 处：' % (a0, b0))
print('  detach alpha（**标准实现**）:', grad_ciou(a0, b0, True))
print('  完整梯度（数值可校验）      :', grad_ciou(a0, b0, False))
print('  中心差分数值梯度            :', num_grad(ciou, a0, b0))
print('\\n⚠️  标准 CIoU 实现里 alpha 被 detach，所以它反传的**不是 CIoU 的真实梯度**。')
print('    这在工程上没问题（alpha 只是个自适应权重），但做数值验证时必须知道，')
print('    否则你会以为自己写错了。')"""),

    md("""## 4 · IoU 的梯度死区：把框推开，看梯度精确变成 0

**这是「为什么必须有 GIoU」的直接证据。**"""),
    code("""gt = (0.0, 0.0, 8.0, 8.0)          # 一块 8x8 像素的远处限速牌
print('%8s %8s %10s %14s %14s' % ('平移 dx', 'IoU', 'GIoU', '|grad IoU|', '|grad GIoU|'))
rows = []
for dx in [1.0, 2.0, 4.0, 6.0, 7.9, 8.0, 10.0, 20.0, 50.0]:
    pred = (dx, 0.0, dx + 8.0, 8.0)
    gi = np.abs(grad_iou(pred, gt)).sum()
    gg = np.abs(grad_giou(pred, gt)).sum()
    rows.append((dx, iou(pred, gt), giou(pred, gt), gi, gg))
    print('%8.1f %8.4f %10.4f %14.6f %14.6f'
          % (dx, iou(pred, gt), giou(pred, gt), gi, gg))

# 断言：一旦不相交（dx >= 8），IoU 梯度**精确为 0**，而 GIoU 仍有梯度
for dx, i_, g_, gi, gg in rows:
    if dx >= 8.0:
        assert gi == 0.0, 'dx=%.1f 时 IoU 梯度必须精确为 0' % dx
        assert gg > 1e-4, 'dx=%.1f 时 GIoU 必须仍有梯度' % dx
print('\\n⚠️  dx>=8 之后 IoU 梯度**精确等于 0**（不是「很小」，是数学上的零）——')
print('    优化器在这片 plateau 上完全收不到方向信号。')
print('✅ GIoU 的梯度随距离衰减但**永不为零**：|grad| 从 %.4f 衰减到 %.6f'
      % (rows[5][4], rows[-1][4]))
print('   衰减是因为外接框 Ac 随距离平方增长 —— **所以 L1 也不能去掉**，')
print('   L1 的梯度不随距离衰减，负责「快速把框拽回来」。')

# L1 对照：梯度大小与距离无关
def l1_grad_x(dx):
    return 1.0 if dx > 0 else -1.0
print('\\n对照 L1: dx=8 时 |grad|=%.1f, dx=50 时 |grad|=%.1f  ← **完全不衰减**'
      % (abs(l1_grad_x(8.)), abs(l1_grad_x(50.))))"""),

    md("""## 5 · L1 的尺度敏感性：为什么「只用 L1」对 TSR 是灾难

DETR 预测归一化坐标 `(cx,cy,w,h) ∈ [0,1]^4`。
**同样 2 像素的对角偏移，L1 完全相同，而实际定位质量（1−IoU）差 20 倍。**"""),
    code("""IMG = 640.0        # 输入分辨率

def px_to_cxcywh(x1, y1, x2, y2, img=IMG):
    '''DETR 预测的就是这个：归一化的 (cx, cy, w, h)。'''
    return np.array([(x1 + x2) / 2 / img, (y1 + y2) / 2 / img,
                     (x2 - x1) / img, (y2 - y1) / img])

print('%-16s %9s %14s %10s %10s %10s'
      % ('目标', '像素尺寸', 'L1(cxcywh)', 'IoU', '1-IoU', '1-GIoU'))
recs = []
for name, s in [('远处限速牌', 8), ('中距离标志', 16), ('近处车辆', 64), ('大型广告牌', 256)]:
    gt_px   = (0.0, 0.0, float(s), float(s))
    pred_px = (2.0, 2.0, float(s) + 2, float(s) + 2)      # 对角偏移 2 px
    l1 = float(np.abs(px_to_cxcywh(*pred_px) - px_to_cxcywh(*gt_px)).sum())
    recs.append((name, s, l1, iou(gt_px, pred_px), 1 - giou(gt_px, pred_px)))
    print('%-12s %9s %14.6f %10.4f %10.4f %10.4f'
          % (name, '%dx%d' % (s, s), l1, iou(gt_px, pred_px),
             1 - iou(gt_px, pred_px), 1 - giou(gt_px, pred_px)))

l1s = [r[2] for r in recs]
assert max(l1s) - min(l1s) < 1e-12, '四个目标的 L1 损失**完全相同**'
assert abs(l1s[0] - 2 * 2 / 640) < 1e-12, 'cx 与 cy 各偏 2/640'
ious = [r[3] for r in recs]
print('\\n⚠️  四行的 L1 损失完全相同 (%.6f)，但 1-IoU 从 %.4f 到 %.4f，**差 %.0f 倍**。'
      % (l1s[0], 1 - ious[-1], 1 - ious[0], (1 - ious[0]) / (1 - ious[-1])))
assert (1 - ious[0]) / (1 - ious[-1]) > 15

# 反过来：大目标的绝对误差天然更大 -> 只用 L1 时大目标主导梯度
print('\\n反方向的问题：按「相对误差 10%」缩放时，L1 谁大？')
print('%-12s %9s %16s' % ('目标', '像素尺寸', 'L1(相对偏移10%)'))
big_l1 = []
for name, s in [('远处限速牌', 8), ('近处车辆', 64), ('大型广告牌', 256)]:
    d = 0.1 * s
    v = float(np.abs(px_to_cxcywh(d, d, s + d, s + d) - px_to_cxcywh(0, 0, s, s)).sum())
    big_l1.append(v)
    print('%-12s %9s %16.6f' % (name, '%dx%d' % (s, s), v))
assert big_l1[-1] > 30 * big_l1[0], '同样的相对误差，大目标的 L1 大 32 倍 -> 主导梯度'
print('\\n✅ 结论（**TSR 场景的核心论证**）：')
print('   · 只用 L1 -> 小目标的定位错误被严重低估，大目标主导梯度；')
print('   · 只用 IoU 系 -> 训练初期框不相交，梯度为 0，根本启动不了；')
print('   · **L1 + GIoU 恰好互补**：L1 提供处处存在的方向，GIoU 提供尺度公平的形状约束。')
print('   · 交通标志绝大多数落在 8-32 px 区间 —— 这正是 L1 最不公平、GIoU 最关键的区间。')"""),

    md("""## 6 · 匈牙利匹配 + 完整 Hungarian loss

匹配算法在模块 01 讲过，这里给一个紧凑的 O(n³) 实现（含暴力对拍），
重点是**代价矩阵与损失是两个不同的函数**。"""),
    code("""def hungarian(cost):
    '''O(n^3) 匈牙利算法（JV 势函数版），支持 n <= m 的矩形代价矩阵。
       返回 (row_ind, col_ind)，使总代价最小。'''
    C = np.asarray(cost, dtype=float)
    n, m = C.shape
    assert n <= m, '行数必须 <= 列数'
    INF = float('inf')
    u = np.zeros(n + 1); v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int); way = np.zeros(m + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0
        minv = np.full(m + 1, INF); used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]; delta = INF; j1 = -1
            for j in range(1, m + 1):
                if not used[j]:
                    cur = C[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur; way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]; j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta; v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
    col = np.zeros(n, dtype=int)
    for j in range(1, m + 1):
        if p[j]:
            col[p[j] - 1] = j - 1
    return np.arange(n), col

# 与暴力枚举对拍
for trial in range(60):
    n, m = int(rng.integers(1, 5)), int(rng.integers(1, 6))
    n = min(n, m)
    C = rng.uniform(-2, 4, size=(n, m))
    r, c = hungarian(C)
    got = C[r, c].sum()
    best = min(sum(C[i, perm[i]] for i in range(n))
               for perm in itertools.permutations(range(m), n))
    assert abs(got - best) < 1e-9, (C, got, best)
    assert len(set(c.tolist())) == n, '必须是一一对应'
print('✅ 匈牙利算法与暴力枚举对拍通过（60 组随机矩形代价矩阵）')"""),
    code("""def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def cxcywh_to_xyxy(b):
    cx, cy, w, h = b
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

W_CLS, W_L1, W_GIOU = 1.0, 5.0, 2.0        # DETR 默认
EOS_COEF = 0.1

def detr_cost_matrix(logits, boxes, tgt_labels, tgt_boxes):
    '''**匹配代价**：分类项用 -p（概率，有界），不用 -log p。M x N。'''
    prob = softmax(logits, -1)             # (N, K+1)，最后一列是 no-object
    M, N = len(tgt_labels), len(boxes)
    C = np.zeros((M, N))
    for i in range(M):
        for j in range(N):
            c_cls = -prob[j, tgt_labels[i]]
            c_l1 = np.abs(np.asarray(boxes[j]) - np.asarray(tgt_boxes[i])).sum()
            c_gi = 1.0 - giou(cxcywh_to_xyxy(boxes[j]), cxcywh_to_xyxy(tgt_boxes[i]))
            C[i, j] = W_CLS * c_cls + W_L1 * c_l1 + W_GIOU * c_gi
    return C

def hungarian_loss(logits, boxes, tgt_labels, tgt_boxes, eos_coef=EOS_COEF):
    '''**训练损失**：分类项用 -log p，且背景 query 全部参与。'''
    N, Kp1 = logits.shape
    K = Kp1 - 1                            # 最后一类是 no-object
    C = detr_cost_matrix(logits, boxes, tgt_labels, tgt_boxes)
    rows, cols = hungarian(C)              # rows 索引 GT，cols 索引 query
    logp = np.log(softmax(logits, -1) + 1e-12)

    target = np.full(N, K, dtype=int)      # 默认全是 no-object
    weight = np.full(N, eos_coef)
    for gi, qi in zip(rows, cols):
        target[qi] = tgt_labels[gi]; weight[qi] = 1.0

    # 与 PyTorch 的 weighted cross_entropy 一致：sum(w*l) / sum(w)
    l_cls = -(weight * logp[np.arange(N), target]).sum() / weight.sum()
    l_l1 = l_gi = 0.0
    for gi, qi in zip(rows, cols):         # **只对匹配上的 query 算框损失**
        l_l1 += np.abs(np.asarray(boxes[qi]) - np.asarray(tgt_boxes[gi])).sum()
        l_gi += 1.0 - giou(cxcywh_to_xyxy(boxes[qi]), cxcywh_to_xyxy(tgt_boxes[gi]))
    nb = max(len(tgt_labels), 1)
    total = W_CLS * l_cls + W_L1 * l_l1 / nb + W_GIOU * l_gi / nb
    return dict(total=total, cls=l_cls, l1=l_l1 / nb, giou=l_gi / nb,
                match=dict(zip(rows.tolist(), cols.tolist())))

# --- 合成一张 TSR 风格的场景：3 块标志，全部小而偏上 ---
K, N = 5, 20
tgt_boxes = [(0.22, 0.30, 0.030, 0.030),   # 远处限速牌 ~ 19x19 px @640
             (0.55, 0.26, 0.018, 0.018),   # 更远的警告牌 ~ 12x12 px
             (0.80, 0.40, 0.055, 0.055)]   # 较近的指示牌 ~ 35x35 px
tgt_labels = [0, 2, 1]

def jitter(b, s_pos, s_wh, rg=None):
    '''给框加噪声，并保证 w, h 恒为正（否则 GIoU 无定义）。'''
    rg = rg or rng
    out = np.asarray(b, float) + np.concatenate([rg.normal(0, s_pos, 2),
                                                 rg.normal(0, s_wh, 2)])
    out[2:] = np.clip(out[2:], 0.005, None)
    return tuple(out)

pred_boxes = [tuple(rng.uniform([0.05, 0.05, 0.01, 0.01], [0.95, 0.7, 0.12, 0.12]))
              for _ in range(N)]
logits = rng.normal(0, 1.0, size=(N, K + 1))
# 让 3 个 query 明显更靠近对应 GT（模拟训练到一半的状态）
for k, (gi, qi) in enumerate([(0, 3), (1, 11), (2, 17)]):
    pred_boxes[qi] = jitter(tgt_boxes[gi], 0.008, 0.002)
    logits[qi, tgt_labels[gi]] += 3.0

out = hungarian_loss(logits, pred_boxes, tgt_labels, tgt_boxes)
print('匹配结果 (GT -> query):', out['match'])
print('损失分解: cls=%.4f  L1=%.4f  GIoU=%.4f  ->  total=%.4f'
      % (out['cls'], out['l1'], out['giou'], out['total']))
print('加权后各项贡献: cls=%.4f  L1=%.4f  GIoU=%.4f'
      % (W_CLS * out['cls'], W_L1 * out['l1'], W_GIOU * out['giou']))
assert out['match'] == {0: 3, 1: 11, 2: 17}, '刻意放近的 3 个 query 应该被匹配上'
assert out['total'] > 0
print('\\n✅ 注意加权后三项在同一个量级 —— 这就是 lambda=(1,5,2) 的**量纲配平**作用。')
print('   若把 lambda_L1 设成 1，L1 项贡献只有 %.4f，在分类项面前几乎没有声音。'
      % (1.0 * out['l1']))"""),

    md("""## 7 · no-object 权重消融：`eos_coef` 到底在调什么

合成一个「93% 背景 / 7% 前景」的二分类问题（对应 N=100、M=7 的典型场景），
用加权交叉熵训练一个小分类器，看**前景召回**与**误检**如何随 `eos_coef` 变化。"""),
    code("""def make_query_features(n_fg=70, n_bg=930, seed=1):
    '''合成 query 特征：前景与背景**有重叠**（真实情况就是这样）。'''
    r = np.random.default_rng(seed)
    Xf = r.normal([1.2, 0.0], 1.0, size=(n_fg, 2))
    Xb = r.normal([-0.3, 0.0], 1.0, size=(n_bg, 2))
    X = np.vstack([Xf, Xb])
    y = np.concatenate([np.zeros(n_fg, int), np.ones(n_bg, int)])   # 1 = no-object
    X = np.hstack([X, np.ones((len(X), 1))])                        # bias
    return X, y

def train_weighted_ce(X, y, eos_coef, iters=800, lr=0.5):
    '''2 类 softmax + 对 no-object 类降权的交叉熵，全批量梯度下降。'''
    W = np.zeros((X.shape[1], 2))
    w_sample = np.where(y == 1, eos_coef, 1.0)
    for _ in range(iters):
        P_ = softmax(X @ W, -1)
        onehot = np.zeros_like(P_); onehot[np.arange(len(y)), y] = 1.0
        grad = X.T @ ((P_ - onehot) * w_sample[:, None]) / w_sample.sum()
        W -= lr * grad
    return W

X, y = make_query_features()
print('数据: 前景 %d / 背景 %d  ->  背景占比 %.1f%%'
      % ((y == 0).sum(), (y == 1).sum(), 100 * (y == 1).mean()))
print('\\n%-12s %14s %14s %14s' % ('eos_coef', '前景召回', '前景精确率', '误检数(FP)'))
res = {}
for eos in [1.0, 0.5, 0.2, 0.1, 0.05, 0.02]:
    W = train_weighted_ce(X, y, eos)
    pred_fg = (X @ W).argmax(1) == 0
    tp = int((pred_fg & (y == 0)).sum()); fp = int((pred_fg & (y == 1)).sum())
    rec = tp / (y == 0).sum()
    prec = tp / max(tp + fp, 1)
    res[eos] = (rec, prec, fp)
    tag = '   <- DETR 默认' if eos == 0.1 else ''
    print('%-12.2f %13.3f %14.3f %14d%s' % (eos, rec, prec, fp, tag))

assert res[1.0][0] < res[0.1][0], 'eos_coef=1.0 时前景召回必须显著低于 0.1'
assert res[0.02][2] > res[0.1][2], 'eos_coef 越小误检越多'
print('\\n⚠️  eos_coef=1.0（不降权）时前景召回只有 %.3f —— 模型学到的最优解是「几乎全说背景」，'
      % res[1.0][0])
print('    因为那样能立刻消掉 93% 的损失。这就是 DETR 不降权时 mAP≈0 的机理。')
print('✅ eos_coef=0.1 把有效背景权重降到 %.1f（等效样本数 %d），召回回到 %.3f。'
      % (0.1, int(0.1 * 930), res[0.1][0]))
print('⚠️  但继续调小到 0.02，误检从 %d 涨到 %d —— **这不是「更好」，只是换了工作点**。'
      % (res[0.1][2], res[0.02][2]))
print('   对 TSR 这类误检代价高度不对称的场景，工作点应该由**标定后的阈值**决定，')
print('   而不是由损失权重偷换。')"""),

    md("""## ✏️ 练习 1：向量化的 IoU / GIoU 矩阵

实现 `iou_matrix(A, B)` 与 `giou_matrix(A, B)`：
`A` 是 `(N,4)`、`B` 是 `(M,4)` 的 xyxy 数组，返回 `(N,M)` 矩阵。
**不许用 Python 循环**（用 numpy 广播）。这是代价矩阵的性能瓶颈，实际项目里必须向量化。"""),
    code("""def iou_matrix(A, B):
    # TODO: 用广播算 (N,M) 的 IoU 矩阵
    #  提示: lt = np.maximum(A[:, None, :2], B[None, :, :2])
    #        rb = np.minimum(A[:, None, 2:], B[None, :, 2:])
    raise NotImplementedError

def giou_matrix(A, B):
    # TODO: 在 iou_matrix 基础上加最小外接框的惩罚项
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
A = np.array([[0., 0., 4., 4.], [5., 5., 9., 9.], [0., 0., 10., 10.]])
B = np.array([[0., 0., 4., 4.], [2., 2., 6., 6.], [40., 0., 44., 4.]])
Mi, Mg = iou_matrix(A, B), giou_matrix(A, B)
assert Mi.shape == (3, 3) and Mg.shape == (3, 3)
# 与逐对的标量实现对拍
for i in range(3):
    for j in range(3):
        assert abs(Mi[i, j] - iou(tuple(A[i]), tuple(B[j]))) < 1e-9, (i, j)
        assert abs(Mg[i, j] - giou(tuple(A[i]), tuple(B[j]))) < 1e-9, (i, j)
assert abs(Mi[0, 0] - 1.0) < 1e-9 and Mi[0, 2] == 0.0
assert Mg[0, 2] < -0.8, '很远的不相交，GIoU 应接近 -1'
assert (Mg <= Mi + 1e-9).all(), 'GIoU <= IoU 处处成立'
# 大规模性能形状检查
big = iou_matrix(rng.uniform(0, 1, (100, 4)).cumsum(1),
                 rng.uniform(0, 1, (30, 4)).cumsum(1))
assert big.shape == (100, 30)
print('IoU 矩阵:\\n', Mi)
print('GIoU 矩阵:\\n', Mg)
print('✅ 练习 1 通过：DETR 的代价矩阵是 M x N 的，N 可以到 900 —— **必须向量化**')"""),

    md("""## ✏️ 练习 2：完整的 DETR 匹配代价矩阵（含权重）

实现 `cost_matrix(prob, boxes, tgt_labels, tgt_boxes, w_cls, w_l1, w_giou)`：
- `prob` 是 `(N, K+1)` 的**概率**（已 softmax），`boxes` 是 `(N,4)` 的 cxcywh
- 分类项必须用 `-prob[:, c]`（**不是** `-log`）
- 返回 `(M, N)` 代价矩阵，且要向量化（至少 IoU 部分）"""),
    code("""def cost_matrix(prob, boxes, tgt_labels, tgt_boxes, w_cls=1.0, w_l1=5.0, w_giou=2.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
probs = softmax(logits, -1)
Bp = np.asarray(pred_boxes); Bt = np.asarray(tgt_boxes)
Cm = cost_matrix(probs, Bp, tgt_labels, Bt)
Cref = detr_cost_matrix(logits, pred_boxes, tgt_labels, tgt_boxes)
assert Cm.shape == (3, N)
assert np.allclose(Cm, Cref, atol=1e-9), '与逐元素参考实现必须一致'
r_, c_ = hungarian(Cm)
assert dict(zip(r_.tolist(), c_.tolist())) == {0: 3, 1: 11, 2: 17}
print('默认权重 (1,5,2) 的匹配:', dict(zip(r_.tolist(), c_.tolist())))
print('代价矩阵三项的典型量级: cls in [%.3f,%.3f], L1 ~ %.3f, 1-GIoU ~ %.3f'
      % (-probs.max(), -probs.min(),
         float(np.abs(Bp[0] - Bt[0]).sum()),
         1 - giou(cxcywh_to_xyxy(Bp[0]), cxcywh_to_xyxy(Bt[0]))))

# —— 权重敏感性：构造一个「分类好但框差」vs「框好但分类差」的对峙 ——
Bt2 = np.array([[0.30, 0.30, 0.04, 0.04], [0.70, 0.30, 0.04, 0.04]])
Bp2 = np.array([[0.30, 0.30, 0.04, 0.04],    # q0: 框完美，分类平庸
                [0.34, 0.30, 0.04, 0.04]])   # q1: 框略差，分类极自信
pr2 = np.array([[0.34, 0.33, 0.33], [0.97, 0.02, 0.01]])   # (N=2, K+1=3)
lab2 = [0, 1]
for wc in [1.0, 20.0]:
    C2 = cost_matrix(pr2, Bp2, lab2, Bt2, w_cls=wc)
    _, cc = hungarian(C2)
    print('w_cls=%-5.1f -> GT0 认领 q%d, GT1 认领 q%d' % (wc, cc[0], cc[1]))
m_low = hungarian(cost_matrix(pr2, Bp2, lab2, Bt2, w_cls=1.0))[1]
m_high = hungarian(cost_matrix(pr2, Bp2, lab2, Bt2, w_cls=20.0))[1]
assert not np.array_equal(m_low, m_high), '权重改变了最优匹配'
print('⚠️  **同一组预测，只改分类权重，匹配就翻了** —— 匹配代价的权重不是无关紧要的超参。')
print('✅ 练习 2 通过：**匹配代价用概率、损失用 log** —— 这是最常被问的细节')"""),

    md("""## ✏️ 练习 3：辅助损失与「层间匹配翻转率」

实现 `aux_total_loss(per_layer, tgt_labels, tgt_boxes, eos_coef)`：
- `per_layer` 是 `[(logits_l, boxes_l), ...]`，长度 = decoder 层数
- 每层**独立做一次匈牙利匹配**、算一份完整 Hungarian loss，等权相加
- 同时返回 `flip_rate`：相邻两层之间，**同一个 GT 被换了 query 认领**的比例
  （所有相邻层对上求平均）"""),
    code("""def aux_total_loss(per_layer, tgt_labels, tgt_boxes, eos_coef=0.1):
    # TODO: 返回 dict(total=..., per_layer=[...], flip_rate=...)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
# 造 6 层输出：模拟「逐层精修」—— 越靠后的层框越准、分类越自信
per_layer = []
for L in range(6):
    s = 0.05 * (6 - L) / 6
    bl = [jitter(b, s, s * 0.2) for b in pred_boxes]
    ll = logits.copy() + rng.normal(0, 0.3, logits.shape)
    for k, (gi, qi) in enumerate([(0, 3), (1, 11), (2, 17)]):
        bl[qi] = jitter(tgt_boxes[gi], 0.02 * (6 - L) / 6, 0.004 * (6 - L) / 6)
        ll[qi, tgt_labels[gi]] += 1.0 + 0.6 * L
    per_layer.append((ll, bl))

r = aux_total_loss(per_layer, tgt_labels, tgt_boxes)
assert set(r) >= {'total', 'per_layer', 'flip_rate'}
assert len(r['per_layer']) == 6
assert abs(r['total'] - sum(r['per_layer'])) < 1e-9, '等权相加'
assert 0.0 <= r['flip_rate'] <= 1.0
print('逐层损失:', ['%.3f' % v for v in r['per_layer']])
print('总损失 %.4f   层间匹配翻转率 %.3f' % (r['total'], r['flip_rate']))
assert r['per_layer'][-1] < r['per_layer'][0], '越靠后的层损失应更低（逐层精修）'
print('✅ 练习 3 通过：**翻转率是免费的诊断信号** —— 高翻转率意味着各层「认领」的目标不一致，')
print('   优化目标在抖。这正是 DN-DETR 用去噪 query 绕过匹配的动机（模块 04）。')"""),

    md("""## ✏️ 练习 4：把梯度换到 `(cx, cy, w, h)` 参数化

DETR 的框头输出的是 `(cx, cy, w, h)`，而我们的 GIoU 梯度是对 `(x1,y1,x2,y2)` 的。
实现 `grad_giou_cxcywh(a_cxcywh, b_xyxy)`：用链式法则转换，并保证数值梯度校验通过。

> 提示：`x1 = cx - w/2, y1 = cy - h/2, x2 = cx + w/2, y2 = cy + h/2`，
> 所以雅可比是一个 4x4 常数矩阵。**面试里主动提到这一步是加分项。**"""),
    code("""def grad_giou_cxcywh(a_cxcywh, b_xyxy):
    # TODO: 先转 xyxy 求 grad_giou，再乘 d(xyxy)/d(cxcywh) 的雅可比
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
def giou_cxcywh(a_cxcywh, b_xyxy):
    return giou(cxcywh_to_xyxy(a_cxcywh), b_xyxy)

bad = 0
for _ in range(200):
    a = (float(rng.uniform(-1, 1)), float(rng.uniform(-1, 1)),
         float(rng.uniform(.3, 2)), float(rng.uniform(.3, 2)))
    bx = float(rng.uniform(-1, 1)); by = float(rng.uniform(-1, 1))
    b = (bx, by, bx + float(rng.uniform(.3, 2)), by + float(rng.uniform(.3, 2)))
    ga = grad_giou_cxcywh(a, b)
    gn = num_grad(giou_cxcywh, a, b)
    if not np.allclose(ga, gn, atol=2e-6):
        bad += 1
assert bad == 0, 'cxcywh 参数化的梯度校验失败 %d 例' % bad

a = (0.0, 0.0, 2.0, 1.0); b = (-0.5, -0.6, 1.5, 0.9)
print('d GIoU / d(cx, cy, w, h) 解析 =', grad_giou_cxcywh(a, b))
print('d GIoU / d(cx, cy, w, h) 数值 =', num_grad(giou_cxcywh, a, b))
print('✅ 练习 4 通过：真实训练里梯度还要再过一层 sigmoid（因为 cxcywh 被约束在 [0,1]），')
print('   所以完整链条是: GIoU -> xyxy -> cxcywh -> sigmoid -> 网络输出。')
print('   **白板题主动说出这一层，比只写 IoU 梯度高一个档次。**')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def iou_matrix(A, B):
    A = np.asarray(A, float); B = np.asarray(B, float)
    lt = np.maximum(A[:, None, :2], B[None, :, :2])
    rb = np.minimum(A[:, None, 2:], B[None, :, 2:])
    wh = np.clip(rb - lt, 0.0, None)                 # ← clamp
    I = wh[..., 0] * wh[..., 1]
    aA = (A[:, 2] - A[:, 0]) * (A[:, 3] - A[:, 1])
    aB = (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1])
    U = aA[:, None] + aB[None, :] - I
    return I / (U + 1e-12)

def giou_matrix(A, B):
    A = np.asarray(A, float); B = np.asarray(B, float)
    lt = np.maximum(A[:, None, :2], B[None, :, :2])
    rb = np.minimum(A[:, None, 2:], B[None, :, 2:])
    wh = np.clip(rb - lt, 0.0, None)
    I = wh[..., 0] * wh[..., 1]
    aA = (A[:, 2] - A[:, 0]) * (A[:, 3] - A[:, 1])
    aB = (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1])
    U = aA[:, None] + aB[None, :] - I
    clt = np.minimum(A[:, None, :2], B[None, :, :2])
    crb = np.maximum(A[:, None, 2:], B[None, :, 2:])
    cwh = np.clip(crb - clt, 0.0, None)
    Ac = cwh[..., 0] * cwh[..., 1]
    return I / (U + 1e-12) - (Ac - U) / (Ac + 1e-12)"""),
    code("""# 练习 2 参考答案
def cost_matrix(prob, boxes, tgt_labels, tgt_boxes, w_cls=1.0, w_l1=5.0, w_giou=2.0):
    prob = np.asarray(prob, float)
    Bp = np.asarray(boxes, float); Bt = np.asarray(tgt_boxes, float)
    tgt_labels = np.asarray(tgt_labels, int)
    # 分类项：**用概率，不用 log** —— (M, N)
    c_cls = -prob[:, tgt_labels].T
    # L1 项：(M, N)
    c_l1 = np.abs(Bt[:, None, :] - Bp[None, :, :]).sum(-1)
    # GIoU 项：先转 xyxy 再用矩阵版
    def to_xyxy(B):
        return np.stack([B[:, 0] - B[:, 2] / 2, B[:, 1] - B[:, 3] / 2,
                         B[:, 0] + B[:, 2] / 2, B[:, 1] + B[:, 3] / 2], -1)
    c_gi = 1.0 - giou_matrix(to_xyxy(Bt), to_xyxy(Bp))
    return w_cls * c_cls + w_l1 * c_l1 + w_giou * c_gi"""),
    code("""# 练习 3 参考答案
def aux_total_loss(per_layer, tgt_labels, tgt_boxes, eos_coef=0.1):
    losses, matches = [], []
    for lg, bx in per_layer:
        r = hungarian_loss(lg, bx, tgt_labels, tgt_boxes, eos_coef)
        losses.append(r['total']); matches.append(r['match'])
    flips = 0; pairs = 0
    for k in range(len(matches) - 1):
        for gi in matches[k]:
            pairs += 1
            if matches[k][gi] != matches[k + 1].get(gi, -1):
                flips += 1
    return dict(total=float(sum(losses)), per_layer=losses,
                flip_rate=flips / max(pairs, 1))"""),
    code("""# 练习 4 参考答案
def grad_giou_cxcywh(a_cxcywh, b_xyxy):
    g_xyxy = grad_giou(cxcywh_to_xyxy(a_cxcywh), b_xyxy)
    # x1=cx-w/2, y1=cy-h/2, x2=cx+w/2, y2=cy+h/2
    # J[k, m] = d xyxy[k] / d cxcywh[m]
    J = np.array([[1., 0., -0.5, 0.],
                  [0., 1., 0., -0.5],
                  [1., 0., +0.5, 0.],
                  [0., 1., 0., +0.5]])
    return g_xyxy @ J"""),

    md("""---
## 🧪 真实工程胶囊：可直接抄进项目的集合损失实现要点"""),
    code("""RECIPE = r'''
# ============ DETR 集合损失：工程 checklist（PyTorch 伪代码 + 真实参数） ============

# ---- 1. 匹配（no_grad！分类项用概率） ----
@torch.no_grad()
def matcher(outputs, targets, w_cls=1.0, w_l1=5.0, w_giou=2.0):
    bs, nq = outputs["pred_logits"].shape[:2]
    out_prob = outputs["pred_logits"].flatten(0, 1).softmax(-1)   # <- 概率，不是 log
    out_bbox = outputs["pred_boxes"].flatten(0, 1)                # cxcywh, 归一化
    tgt_ids  = torch.cat([t["labels"] for t in targets])
    tgt_bbox = torch.cat([t["boxes"]  for t in targets])
    cost_cls  = -out_prob[:, tgt_ids]                             # (bs*nq, sum_M)
    cost_l1   = torch.cdist(out_bbox, tgt_bbox, p=1)
    cost_giou = -generalized_box_iou(box_cxcywh_to_xyxy(out_bbox),
                                     box_cxcywh_to_xyxy(tgt_bbox))
    C = (w_l1*cost_l1 + w_cls*cost_cls + w_giou*cost_giou).view(bs, nq, -1).cpu()
    sizes = [len(t["boxes"]) for t in targets]
    return [linear_sum_assignment(c[i]) for i, c in enumerate(C.split(sizes, -1))]
    # ^ 官方用 scipy.optimize.linear_sum_assignment；**匹配在 CPU 上做，是训练吞吐瓶颈之一**

# ---- 2. 损失（可导！分类项用 log；只对匹配上的算框损失） ----
empty_weight = torch.ones(num_classes + 1); empty_weight[-1] = 0.1   # eos_coef
loss_ce = F.cross_entropy(src_logits.transpose(1, 2), target_classes, empty_weight)
loss_bbox = F.l1_loss(src_boxes, target_boxes, reduction="sum") / num_boxes
loss_giou = (1 - torch.diag(generalized_box_iou(
        box_cxcywh_to_xyxy(src_boxes), box_cxcywh_to_xyxy(target_boxes)))).sum() / num_boxes
# num_boxes = 全 GPU 上的 GT 总数（**必须 all_reduce，否则多卡不等价**）

# ---- 3. 权重（DETR 官方 detr/main.py 默认值） ----
WEIGHT_DICT = {"loss_ce": 1, "loss_bbox": 5, "loss_giou": 2}
EOS_COEF    = 0.1
AUX_LOSS    = True     # 6 层 decoder 各来一份，权重与最后一层相同
# 辅助损失展开: {"loss_ce_0": 1, "loss_bbox_0": 5, ...} 共 6 组

# ---- 4. 换成 focal 版（Deformable DETR / DINO / RT-DETR 的主流） ----
# · 输出层: K 个 sigmoid，**没有 no-object 类**
# · cls loss: sigmoid_focal_loss(alpha=0.25, gamma=2.0)，weight = 2.0
# · 匹配代价的分类项也换成 focal 形式:
#     neg = (1-a) * p**g * (-log(1-p));  pos = a * (1-p)**g * (-log p)
#     cost_cls = pos[:, tgt_ids] - neg[:, tgt_ids]
# · num_queries: 100 -> 300 (Deformable) / 900 (DINO)
# · 推理: 在 N*K 个 (query, class) 对里取 top-k，**同一 query 可出多类**

# ---- 5. 上线前必查的 5 个数值 bug ----
# [ ] U = Aa + Ab - I，不是 Aa + Ab
# [ ] 交集 wh 必须 clamp(min=0)（不 clamp -> 不相交时出现「假交集」）
# [ ] 框在算 GIoU 前必须满足 x2>=x1, y2>=y1（否则 GIoU 无定义，官方代码里有 assert）
# [ ] num_boxes 要跨卡 all_reduce 并 clamp(min=1)
# [ ] 归一化坐标 vs 像素坐标：换表示必须同步改 lambda_L1（差 640 倍！）
'''
print(RECIPE)
for key in ['no_grad', 'softmax(-1)', 'empty_weight', 'eos_coef', 'all_reduce',
            'clamp(min=0)', 'sigmoid_focal_loss', 'loss_giou']:
    assert key in RECIPE, key
print('✅ 配方覆盖：匹配(no_grad/概率) / 损失(log/eos_coef) / 权重 / focal 版 / 5 个数值 bug')"""),

    md("""### 小结

- **匹配代价 ≠ 训练损失**。匹配只需排序 → 用有界的 `-p` 让三项量纲可比；
  损失需要梯度 → 用 `-log p`。**这是 DETR 损失最常被追问的细节。**
- **背景 query 占 97%**（TSR 场景更极端）。不给 no-object 降权，
  模型会立刻收敛到「全说背景」。`eos_coef=0.1` 是刻意保留背景优势的工作点，
  **不是配平**。而 focal loss 版把这个超参彻底消掉了。
- **L1 与 GIoU 各补一个洞**：L1 对尺度不公平（8×8 和 256×256 的框，2px 偏移的 L1 完全相同，
  1−IoU 却差 20 倍），IoU 在不相交时梯度**精确为 0**。
  8–32 px 的交通标志正好落在「L1 最不公平、GIoU 最关键」的区间。
- **IoU 解析梯度的三个得分点**：`U = Aa+Ab−I`、clamp 产生的截断乘子 `1[iw>0]1[ih>0]`、
  `max/min` 产生的指示函数（外接框方向相反）。加分项：再链式到 `(cx,cy,w,h)` 和 sigmoid。
- **GIoU→DIoU→CIoU 是一条补洞链**：不相交无梯度 → 包含关系退化 → 宽高比无约束。
  DETR 用 GIoU 而非 CIoU，是因为它已经有 L1 项覆盖了中心与宽高。
- **辅助损失**（每层 decoder 各算一份）值约 +2 AP，还顺带给出两个红利：
  层间匹配翻转率这个免费诊断信号，以及 RT-DETR「同一份权重多档速度」的部署能力。

下一站：**模块 03 · Object query 与交叉注意力** —— 谁在认领目标，以及它们怎么互相协商去重。"""),
]
