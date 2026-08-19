# -*- coding: utf-8 -*-
"""C58 模块 02 · 难例挖掘：OHEM、难负样本与难例的类型学。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（长尾与类别不平衡）；C18 检测基础（anchor / proposal / NMS）；交叉熵与梯度的基本直觉"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_hard_example_mining.ipynb'),
    ("核心参考", "Shrivastava et al. <em>Training Region-based Object Detectors with Online Hard Example Mining</em>（CVPR 2016）；Lin et al. <em>Focal Loss for Dense Object Detection</em>（ICCV 2017）；Pleiss et al. <em>Identifying Mislabeled Data using the Area Under the Margin Ranking</em>（NeurIPS 2020）"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ─────────────────────────────────────────────────────────────
    ("budget", "梯度预算是稀缺资源：难例挖掘要解决的到底是什么", "".join([
        P("先把问题摆正。训练一个检测器时，<strong>真正稀缺的不是数据量，而是「有效梯度」</strong>——那些能真的改变模型参数的信号。一张 1920×1080 的图，密集检测器会铺出 <span class=\"term\">anchor</span>（锚框）或候选点 <strong>2 万到 20 万个</strong>；两阶段检测器的 RPN 也会给出 1000–2000 个 <span class=\"term\">proposal</span>（候选框）。其中真正是前景的可能只有 <strong>3 到 30 个</strong>。前景背景比轻松到 <strong>1:1000</strong> 甚至 1:10000。"),
        P("这个比例本身还不是最糟的。最糟的是<strong>绝大多数背景样本是「一眼假」</strong>：天空、路面、纯色墙面。模型训练两个 epoch 之后就能给它们打出 0.999 的背景分。对交叉熵而言，这类样本的梯度是"),
        MATH("\\frac{\\partial \\mathcal{L}_{\\text{CE}}}{\\partial z} = p - y \\quad\\Longrightarrow\\quad p=0.999,\\ y=0 \\;\\Rightarrow\\; |g| = 10^{-3}"),
        P("而一个模型判成 0.4 的难背景（比如广告牌上的红色圆形），梯度是 0.4——<strong>相当于 400 个简单背景</strong>。但在均匀采样的 batch 里，那 400 个简单背景确实会出现，而这个难背景可能一整个 epoch 才出现一次。<em>于是梯度预算的绝大部分被浪费在「模型已经会了的事情」上</em>。"),
        ASCII("""一张图上 anchor 的 loss 分布（典型密集检测器，训练中期）

  数量
   ^
   |  ████████████████████████████  ← 约 98% 的 anchor：简单背景
   |  ████████████████████████████     单个梯度 ~1e-3，加起来却主导了总损失
   |  ████████████████████████████
   |  ███
   |  ██                                 ← 难负样本（高分 FP）：0.5%，梯度 ~0.4
   |  █           ▂  ▁                   ← 前景正样本：0.1%
   +--+-----------+---+-------------> loss
     0.001       0.5  3.0

  总损失 = 98% × 0.001 × N  +  0.5% × 0.4 × N  ≈  简单样本贡献仍然更大
                                              （数量优势压过质量劣势）
  → **不做任何处理，模型会被简单背景「淹死」**：
    它学会的是「什么都判背景」这个 99.9% 正确的退化解。""")
        ,
        P("对这个问题，检测界给出过三代答案，而且这三代<strong>不是替代关系，是同一个思想的三种实现</strong>："),
        TABLE(["代", "方法", "怎么做", "什么时候用它", "代价"], [
            ["第一代", "<strong>Hard negative bootstrapping</strong>（离线自举）", "训一版 → 在大量负样本上推理 → 把判错的高分负样本收集起来 → 加入训练集 → 重训。反复几轮", "负样本集大到装不下内存（HOG+SVM / DPM 时代的标准做法）；<em>今天在「难负样本库」建设里仍然用</em>", "要多轮训练；离线，反馈慢"],
            ["第二代", "<strong>OHEM</strong>（在线难例挖掘）", "一个 batch 内 forward 全部候选 → 按 loss 排序 → 只对 top-k 反传", "两阶段检测器（Fast/Faster R-CNN）；候选数中等（~2000）", "要跑全量 forward；<strong>丢弃了绝大部分样本的梯度</strong>；对标签噪声敏感"],
            ["第三代", "<strong>Focal Loss</strong>（重加权）", "不采样，全部样本都算，但按 <code>(1-p_t)^γ</code> 连续降权", "单阶段密集检测器（RetinaNet 及其后所有 YOLO 变体）", "多两个超参 γ、α；<em>在两阶段检测器上收益很小</em>（下一节讲原因）"],
        ]),
        DUAL(
            "三代方法的共同点是一句话：<strong>把梯度预算从「模型已经会的样本」重新分配到「模型还不会的样本」上</strong>。区别只在「重新分配」这个动作发生在哪一层——第一代在数据集层面（改训练集），第二代在采样层面（改 batch 内谁参与反传），第三代在损失层面（改每个样本的权重）。<em>越往后，粒度越细、反馈越快、工程侵入性越小。</em>",
            "但要注意，三代方法解决的<strong>不完全是同一个不平衡</strong>。第一代针对的是「负样本空间太大无法穷举」；第二代针对的是「batch 内难易混杂，梯度被稀释」；第三代针对的是「前景-背景比极端失衡下损失函数本身的病态」。<em>模块 01 讲的重采样/重加权针对的则是第三种不平衡——类别之间的长尾</em>。<strong>四种不平衡（前景-背景 / 难-易 / 类别间 / 域间）必须分开诊断</strong>，用错工具是最常见的浪费。",
        ),
        CALLOUT("intuition", "一个能一直用下去的判断标准：<strong>看这个样本的梯度还有多大</strong>。梯度接近 0 的样本，无论它是不是「重要类别」，此刻对模型都没有信息量。<em>难例挖掘的全部技巧，都是在用不同的代理量（loss、置信度、模型分歧、不确定性）去逼近「这个样本还剩多少信息量」这一个问题</em>。而它们各自在什么时候会失效——正是本模块要讲的。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("ohem", "OHEM 的机制与四个实现细节（第一个决定成败）", "".join([
        P("<span class=\"term\">OHEM</span>（Online Hard Example Mining，在线难例挖掘）的机制一句话说完：<strong>一个 batch 内先把所有候选样本都 forward 一遍算出 loss，按 loss 从大到小排序，只让 top-k 参与反向传播</strong>。原论文（Shrivastava et al., CVPR 2016）是在 Fast R-CNN 上做的，把 VOC 上的 mAP 提了 4 个点左右。"),
        ASCII("""OHEM 的一轮（原论文的双头实现）

  图像 ──► backbone ──► 特征图
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       RoI Pooling (全部 ~2000 个候选)
              │
        ┌─────┴──────┐
        ▼            ▼
  [read-only head]  [regular head]   ← 两份**共享权重**的检测头
   只做 forward       做 forward+backward
        │                  ▲
        ▼                  │
   每个 RoI 的 loss         │
        │                  │
        ▼                  │
  ① **按 loss 排序**         │
  ② **NMS 去重（IoU 0.7，用 loss 当分数）** ◄── 本节的重点，跳过它 OHEM 会失效
  ③ 取 top-k（如 k=128）    │
        └──────────────────┘
             只把这 k 个送进 regular head 反传

  为什么要两份头？ 因为 2000 个 RoI 一起做 backward 显存放不下。
  今天更简单的等价实现：**一份头，把未选中样本的 loss 直接置 0**
  （loss 为 0 ⇒ 梯度为 0 ⇒ 完全等价，只是省不了显存）。""")
        ,
        H3("细节 ①：必须先 NMS 去重，否则同一个区域被重复计入"),
        P("这是 OHEM 实现里<strong>最容易漏、漏了之后最难查</strong>的一条。原因很直白：候选框在空间上是<strong>高度重叠</strong>的。一个真正难的区域（比如一块被树叶遮住一半的限速牌）周围，会有<strong>几十个 IoU &gt; 0.8 的 proposal</strong>，它们的 loss 几乎一样高。按 loss 排序取 top-128，结果就是——"),
        TABLE(["", "不做 NMS 去重", "做 NMS 去重（IoU 0.7）"], [
            ["top-128 覆盖的<strong>不同区域数</strong>", "<strong>2–4 个</strong>（被一两个热点吃光）", "<strong>60–120 个</strong>"],
            ["实际有效 batch", "<strong>≈ 3</strong>（128 个样本其实是同一件事的 128 份拷贝）", "≈ 100"],
            ["梯度方向", "被单个区域<strong>完全支配</strong>，方差极大", "多样，稳定"],
            ["症状", "loss 剧烈震荡；模型在几个特定区域上过拟合；换一批数据表现骤降", "正常收敛"],
        ]),
        CALLOUT("danger", "<p><strong>不做去重的 OHEM 比不做 OHEM 更差</strong>——这是一个反直觉但确实会发生的结果。因为它把整个 batch 的梯度预算交给了两三个区域，等于用 <code>batch_size≈3</code> 在训练，而且这三个区域可能恰好是标注错误。<em>面试里如果你能主动说出「OHEM 要先用 loss 作为分数做一遍 NMS」，面试官基本可以确认你真的实现过它</em>，因为这条在论文里只是一句话，但在代码里是决定成败的一行。</p>", "OHEM 的头号实现坑"),
        H3("细节 ②：正负样本要分开挖，否则正样本会被挤没"),
        P("如果不分开挖，在 1:1000 的失衡下，top-k 里<strong>可能一个正样本都没有</strong>（因为难负样本的 loss 完全可以比一般正样本高）。结果是回归分支拿不到梯度，框越训越差。<em>标准做法是正负各自排序、各取各的配额</em>，维持 1:3 的正负比——这一步和 Fast R-CNN 原本的采样策略是一致的，OHEM 只是把「随机取」换成了「取最难的」。"),
        H3("细节 ③：loss 除以 k 还是除以 N"),
        P("选出 k 个后，总损失是 <code>Σℓ/k</code> 还是 <code>Σℓ/N</code>？这不是风格问题：<strong>除以 N 相当于把学习率悄悄乘上了 k/N</strong>（比如 128/2000 = 0.064，学习率被打了 1/16 的折）。<em>正确做法是除以实际参与反传的样本数 k</em>，这样梯度幅值不随 k 变化，k 才是一个可独立调的超参。"),
        H3("细节 ④：warmup 期不要开 OHEM"),
        P("模型刚随机初始化时，所有样本的 loss 都是 <code>log(C)</code> 附近的随机噪声，<strong>按 loss 排序等价于随机排序</strong>——但它比随机采样更糟，因为它系统性地偏向那些「初始化恰好不利」的样本。<em>标准做法是前 1–2 个 epoch（或前若干 iteration）用均匀采样，等 loss 分布真正分化了再开挖掘</em>。这一条同样适用于 focal loss 之外的所有基于 loss 的采样策略。"),
        DUAL(
            "把这四条细节合起来看，会发现它们指向同一个问题：<strong>「loss 高」是「难」的一个<em>有偏</em>代理</strong>。loss 高可能因为：真的难（好）、空间重复（细节①）、类别失衡（细节②）、模型还没学（细节④）、<strong>或者标签是错的</strong>（本模块后半部分的主题）。<em>每一条实现细节，本质上都是在剥掉这个代理量里的一层噪声。</em>",
            "从优化的角度还有一个更根本的解释：OHEM 把损失函数从「样本上的均值」换成了「top-k 的均值」，也就是从 <span class=\"term\">ERM</span>（经验风险最小化）换成了 <span class=\"term\">CVaR</span>（条件风险价值 / 尾部风险）目标。<strong>这个目标是非光滑且非凸的</strong>（top-k 集合会随参数跳变），所以它天然带来优化的不稳定性——loss 曲线锯齿、对学习率敏感、对 batch 组成敏感。<em>而 focal loss 用连续权重把这个跳变抹平了</em>，这正是下一节的内容。",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("focal", "Focal Loss 是软性 OHEM：连续加权 vs 硬性截断", "".join([
        P("这是本模块<strong>最值得背下来的一个类比</strong>，也是面试里区分「读过论文」和「想明白了」的分水岭。先把两者写成同一个形式——它们都是<strong>对样本损失的加权和</strong>，区别只在权重函数的形状："),
        MATH("\\mathcal{L}=\\sum_{i} w_i\\,\\ell_i,\\qquad\\quad w_i^{\\text{OHEM}}=\\frac{1}{k}\\mathbb{1}\\!\\left[\\ell_i\\ge \\ell_{(k)}\\right],\\qquad\\quad w_i^{\\text{focal}}=\\frac{(1-p_i)^{\\gamma}}{Z}"),
        P("其中 <code>ℓ_(k)</code> 是 batch 内第 k 大的 loss，<code>p_i</code> 是模型给<em>正确类别</em>的概率（即 <code>p_t</code>），<code>Z</code> 是归一化项。<strong>关键观察：这两个权重都是「模型越错、权重越大」的单调函数</strong>——OHEM 是一个阶跃函数，focal 是一条光滑曲线。"),
        ASCII("""权重 w 随样本难度（loss ℓ）的变化

  w
  ^
1/k|                    ┌────────────────────  OHEM: **硬性截断**
   |                    │                      ℓ < ℓ_(k) 的样本权重恰好为 0
   |                    │                      （梯度被完全丢弃）
   |                    │
   |         ...........│....................  Focal (γ=2): **连续加权**
   |    .....           │                      简单样本权重很小但**永不为 0**
   |....                │
  0+--------------------+--------------------> ℓ
                    ℓ_(k)  ← 这条线的位置由 batch 组成决定，**每步都在跳**

关键推论：
  · 因为 CE loss ℓ = -log p_t 与 focal 权重 (1-p_t)^γ **都是 p_t 的单调减函数**，
    所以 **「按 focal 权重排序」和「按 loss 排序」得到的顺序完全一致**。
    ⇒ focal 的「最重要的 k 个样本」就是 OHEM 会选中的那 k 个。
  · 唯一的差别是：**被排除的那些样本，权重是 0 还是 ε。**""")
        ,
        TABLE(["维度", "OHEM（硬）", "Focal Loss（软）", "工程含义"],[
            ["权重函数", "阶跃：<code>1[rank ≤ k]</code>", "幂律：<code>(1-p_t)^γ</code>", "focal 无跳变，优化更稳"],
            ["简单样本的梯度", "<strong>完全丢弃（=0）</strong>", "保留但缩小 <code>(1-p)^γ</code> 倍", "OHEM 会「忘掉」已学会的东西，需要靠随机采样补"],
            ["超参", "k（或比例 r）", "γ（+ α 平衡正负）", "γ=2、α=0.25 是几乎万能的默认值；k 要随 batch 调"],
            ["是否需要排序", "需要（O(N log N)）+ NMS 去重", "<strong>不需要，逐元素向量化</strong>", "focal 在密集检测器（10⁵ anchor）上是唯一可行的"],
            ["对<strong>标签噪声</strong>", "<strong>很脆弱</strong>：把 100% 权重给最高 loss 那批，而噪声样本恰好永远在那批里", "较稳：权重上界是 1，且大量简单样本仍在分母里稀释", "<strong>数据脏的时候优先选 focal 或降低 k</strong>"],
            ["两阶段检测器上的收益", "明显（+3~4 mAP）", "<strong>很小</strong>", "见下方解释——这条是面试高分点"],
        ]),
        H3("为什么 Focal Loss 在两阶段检测器上几乎没有收益"),
        P("因为 <strong>RPN 已经把前景背景比从 1:10000 粗筛到了 1:3 左右</strong>，focal loss 想解决的「极端失衡下简单负样本淹没损失」这个病根，在第二阶段已经不存在了。<em>反过来，OHEM 在第二阶段仍然有用，因为它解决的是「剩下的 2000 个候选里难易仍然混杂」</em>。<strong>能说清这一条，说明你理解的不是「focal 好」而是「focal 解决什么」</strong>——面试官想听的正是这个。"),
        DUAL(
            "面试标准答案骨架（建议按这个顺序讲）：<strong>① 二者是同一个思想的硬/软两种实现</strong>，都可以写成 <code>Σ w(ℓ)·ℓ</code>；<strong>② 排序完全一致</strong>，因为 focal 权重与 CE loss 都是 p_t 的单调减函数；<strong>③ 差别在被排除样本的权重是 0 还是 ε</strong>——focal 保留全部样本的梯度，OHEM 直接丢；<strong>④ focal 无需排序、无需去重、可完全向量化</strong>，所以密集检测器只能用 focal；<strong>⑤ 对标签噪声，OHEM 明显更脆弱</strong>；<strong>⑥ 两阶段检测器上 focal 收益小，因为 RPN 已经粗筛过了。</strong>",
            "还有一个把两者定量连起来的工具：<strong>有效样本数</strong> <code>n_eff = (Σw)² / Σw²</code>（这就是加权平均的「等效样本量」，与统计里的 <span class=\"term\">effective sample size</span> 同源）。给定一个 γ，算出 focal 的 <code>n_eff</code>，就得到了「这个 γ 相当于 OHEM 的 k 取多少」。<em>notebook 里会把这张换算表算出来</em>：在一个典型的 <code>p_t</code> 分布上，<strong>γ=2 大致相当于只有 20%–25% 的样本在真正贡献梯度</strong>，而 <strong>γ=5 会把这个比例压到 2% 量级</strong>。<strong>这个数字也解释了为什么 γ 从 2 调到 5 常常直接训崩</strong>——等效样本量掉一个数量级，梯度方差爆炸。",
        ),
        CALLOUT("warn", "两个常见的实现错误。<strong>①「focal loss 用在了已经做过难例采样的样本上」</strong>——两个机制叠加，等效样本量被平方级压缩，训练必然不稳。<em>要么 OHEM 要么 focal，不要同时开</em>。<strong>② focal loss 的 <code>α</code> 被当成了类别平衡权重去调</strong>：α 只平衡前景-背景（二分类意义上的正负），它<em>不解决类别间长尾</em>——那是模块 01 的 EQL / Class-Balanced Loss 的活。混用会让两个机制互相打架。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("hardneg", "难负样本：不是「负样本」，是「模型自信地错了」", "".join([
        P("术语要先掐死。<span class=\"term\">hard negative</span>（难负样本）<strong>不是「随便一个负样本」</strong>，而是<strong>模型给了高分的假正例（high-scoring false positive）</strong>——模型不但错了，还很自信。这个定义里的「自信」是全部价值所在：它意味着这个样本<strong>落在当前决策边界的错误一侧且离边界很远</strong>，修正它会带来最大的边界移动。"),
        ASCII("""难负样本挖掘的离线循环（今天仍是「难负样本库」的标准建法）

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │   训练集 v_n  ──►  训练模型 M_n                                │
  │       ▲                 │                                    │
  │       │                 ▼                                    │
  │       │       在**大量未标注/纯背景**素材上推理                  │
  │       │       （车队回传的路测视频、无标志路段）                  │
  │       │                 │                                    │
  │       │                 ▼                                    │
  │       │       收集 score > τ 的检出                            │
  │       │                 │                                    │
  │       │                 ▼                                    │
  │       │       ┌─────────────────────┐                        │
  │       │       │ 人工确认这是不是 FP  │ ◄── **这一步不能省**      │
  │       │       └─────────┬───────────┘                        │
  │       │                 │                                    │
  │       │        ┌────────┴────────┐                           │
  │       │        ▼                 ▼                           │
  │       │   确实是 FP        **其实是漏标的真目标**               │
  │       │   → 加为难负样本    → 补标为正样本                      │
  │       │        │                 │                           │
  │       └────────┴─────────────────┘                           │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  ⚠️ 跳过人工确认、把所有高分检出直接当负样本喂回去 =
     **主动教模型漏检**。这是 TSR 里最容易犯的致命错误。""")
        ,
        P("为什么 TSR 场景里这个陷阱特别致命？因为交通标志的标注天然不全：<strong>远处只有 12×12 像素的标志、被树叶遮住 60% 的标志、对向车道的标志、辅路上的标志</strong>——不同标注员对「这个要不要标」的判断经常不一致。模型在这些地方给出高分检出，从 GT 看是 FP，从物理世界看是<strong>正确的</strong>。把它当难负样本反复加权训练，等于在训练「看到远处的小标志要压住分数」。"),
        TABLE(["TSR 里难负样本的典型来源", "为什么模型会上当", "正确对策", "错误对策"], [
            ["<strong>广告牌 / 商店招牌</strong>上的红圈、蓝底白字", "颜色+形状先验与真标志几乎一致，只有内容和语境不同", "定向采集这类场景补为负样本；提高分类头的分辨率让它看清内容", "只调低全局阈值（会同时压掉真标志的召回）"],
            ["<strong>车尾/卡车车厢上印的标志图案</strong>", "就是标志的图像，只是不在杆上", "把「是否有杆件 / 是否在合理高度」作为上下文特征；补这类负样本", "把所有车辆区域屏蔽（会漏掉车旁边的真标志）"],
            ["<strong>后视镜、挡风玻璃反光</strong>里的标志", "确实是标志的像，但语义上不对自车生效", "作为负样本；下游用几何/关联规则过滤", "在检测端硬删（几何信息在检测端不可靠）"],
            ["<strong>对向车道 / 辅路</strong>的标志", "是真标志，但不该对本车生效", "<strong>不该在检测端解决</strong>——检测出来，交给下游做车道关联", "标成负样本（会破坏检测器对该类的表征）"],
            ["<strong>施工牌背面 / 折叠收起的可变牌</strong>", "轮廓与正面相似", "补为负样本，并加「背面」这个属性类", "忽略（会周期性地在施工路段爆 FP）"],
            ["<strong>漏标的真标志</strong>（伪装成 FP）", "GT 不全", "<strong>回流去补标</strong>，并统计漏标率", "<strong>当难负样本训练 → 主动制造漏检</strong>"],
        ]),
        DUAL(
            "上表的最后两行揭示了一个原则：<strong>「这个检出该不该被抑制」是一个语境问题，而语境常常不在检测器的视野里</strong>。对向车道的标志、反光里的标志，检测器看到的像素与真标志完全一样——<em>要求检测器区分它们，等于要求它做本该由下游（车道关联、几何一致性、跟踪）做的事</em>。硬塞给检测器的结果是：它会用某些脆弱的伪特征（比如位置偏左）去区分，一换场景就崩。",
            "所以难负样本入库前要过一道<strong>「可分性检查」</strong>：<em>把这个负样本的 crop 单独拿给人看，人能不能仅凭这块图像判断它不是标志？</em> 如果人也需要看全图语境才能判断，那它就<strong>不该作为检测端的难负样本</strong>，而应该作为下游过滤规则的测试用例。<strong>这个检查在面试里说出来分量很重</strong>，因为它体现了「知道每个模块该负责什么」——而这正是量产系统与刷榜的分水岭。",
        ),
        CALLOUT("intuition", "难负样本的价值可以定量估计：如果模型给它的分数是 <code>s</code>，那么修正它带来的梯度大约是 <code>s</code>（对 sigmoid 输出的 CE 而言就是 <code>p-y=s-0=s</code>）。<strong>一个 s=0.8 的难负样本 ≈ 800 个 s=0.001 的简单负样本</strong>。<em>这就是为什么「挖 1000 张难负样本」常常比「多标 10 万张普通图」更有效</em>——但前提是这 1000 张确实是 FP，而不是漏标。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("taxonomy", "难例的类型学：四类难例，四种完全不同的解法", "".join([
        P("到这里必须做一个关键切分。<strong>「loss 高」把四类性质完全不同的样本混在了一起</strong>，而它们的正确处理方式互相矛盾——把第四类当第一类处理，模型会被毁掉。"),
        TABLE(["类型", "典型表现（TSR 语境）", "根因", "<strong>正确解法</strong>", "错误解法"], [
            ["<strong>① 相似类混淆</strong>", "限速 60 vs 80（数字形状近）；限速 vs 解除限速（多一道斜杠）；禁止驶入 vs 禁止通行；直行 vs 直行+右转", "细粒度特征不足：分辨率不够 / 感受野不当 / 分类头容量不足", "<strong>提高 crop 分辨率</strong>（两级架构的最大理由）；针对混淆对做 metric learning 或加权 CE；补该对的数据", "笼统地「多加数据」——加的多半还是易分的那些"],
            ["<strong>② 背景误检（难负）</strong>", "广告牌红圈、车身贴纸、反光", "负样本空间没被覆盖到；上下文信息缺失", "定向挖掘并补入难负样本库；引入上下文（杆件、高度、场景标签）", "只降阈值 / 只加 NMS——治标且损召回"],
            ["<strong>③ 边界样本</strong>", "遮挡 50%、运动模糊、逆光过曝、12 像素的远处标志、褪色破损", "<strong>信息真的不足</strong>——有时人也判不了", "增强（模糊/低光/遮挡合成）；时序累积（等它变近）；<strong>接受一个可检测下界</strong>并在评测里按尺寸分桶", "无限加权硬啃——会牺牲正常样本"],
            ["<strong>④ 标注错误</strong>", "类别标错、框位置错、漏标、类别体系变更后的旧标签", "标注流程问题", "<strong>识别并剔除 / 降权 / 回流重标</strong>", "<strong>当难例反复挖掘 —— 这会直接毁掉模型</strong>"],
        ]),
        P("把这四类放到一张图上，就能看清难例挖掘的真实困难所在："),
        ASCII("""按 loss 排序时，四类样本在 top-k 里的分布（典型的真实检测数据集）

  loss 从高到低 ───────────────────────────────────────────────►

  ┌────────────┬────────────┬───────────────┬───────────────────┐
  │ ④ 标注错误  │ ③ 边界样本  │ ① 相似类混淆   │ ② 难负样本        │
  │ **loss 最高** │ 次之        │ 中等           │ 分布很广           │
  │ 因为标签与   │ 因为信息    │ 因为特征相近   │ 因为「多难」取决于  │
  │ **任何**可学 │ 客观不足    │ 但可区分       │ 背景本身           │
  │ 规律都矛盾   │            │               │                   │
  └────────────┴────────────┴───────────────┴───────────────────┘
        ▲
        │
   **挖掘越激进（k 越小 / γ 越大），选中的样本里 ④ 的占比越高。**
   这就是「挖掘过头反而毁掉模型」的机制。

   数量对比（假设噪声率 5%）：
     全体样本中 ④ 占 5%
     top-1% 高 loss 样本中 ④ 可能占 **40–70%**
     ⇒ 噪声放大系数 A = 0.5/0.05 = **10×**""")
        ,
        DUAL(
            "上面这张图给出了一个非常锋利的推论：<strong>「loss 高」和「有价值」在数据干净时高度相关，在数据脏时几乎反相关</strong>。而真实的量产标注数据，类别标注错误率在 <strong>2%–10%</strong> 是常态（细粒度类别越多越高，TSR 的百来个类正好是高发区）。<em>这意味着难例挖掘的收益曲线不是单调的，而是一条倒 U</em>：挖一点有用，挖过头有害。",
            "更精确地说：设噪声率 <code>q</code>，挖掘选中样本中噪声的富集倍数为 <code>A</code>，混合批中难例占比为 <code>r</code>，则 batch 的<strong>有效噪声率</strong> <code>q_eff = (1-r)q + r·q·A</code>。要求 <code>q_eff ≤ q_max</code> 就给出了 <strong>难例比例的安全上界</strong>（下一节展开）。<em>这个式子的实用价值在于：它把「挖多少」从一个凭感觉的超参，变成了一个由「标注质量」决定的可计算量</em>。<strong>换句话说：你的数据有多脏，决定了你能挖多狠。</strong>",
        ),
        CALLOUT("warn", "还有一类容易被忽略的「假难例」：<strong>类别定义本身模糊的样本</strong>。比如「限速 60 的主牌 + 下方『雨雾天』辅助牌」到底算一个目标还是两个？「电子可变限速牌显示 80」算限速 80 还是算电子牌类？<em>这类样本的 loss 会一直高，但它不是标注员的错，是<strong>标注规范没定义清楚</strong></em>。挖它、加权它、重标它都没用——<strong>唯一的解法是回去改规范，然后全量重刷</strong>。所以难例分析的产出之一，永远应该包括「规范需要补的条目」。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("noise_trap", "挖掘过头：噪声标签会被当成最有价值的难例", "".join([
        CALLOUT("danger", "<p><strong>本模块最重要的一句话：难例挖掘是一个噪声放大器。</strong> 它按「模型拟合得最差」来选样本，而<em>标签错误的样本，正是模型永远拟合不好的那一批</em>——因为它的标签与图像中任何可学的规律都矛盾。于是每一轮它都被选中，权重被放大数倍，模型被迫去记住它。<strong>结果是：挖掘越努力，模型越差，而且离线指标可能看不出来</strong>（因为验证集来自同一个标注流程，含有同样的噪声）。</p>", "难例挖掘的头号事故"),
        P("把这个机制拆成三层，每一层都有独立的危害："),
        OL([
            "<strong>权重放大</strong>：噪声样本的 loss 长期位于分布顶端 → 每个 epoch 都进入 top-k → 有效采样权重被放大 <code>A</code> 倍（合成实验里 <code>A</code> 常在 4–10）。<em>这是最直接的一层</em>。",
            "<strong>记忆化（memorization）</strong>：深网络容量足够时可以拟合任意随机标签（Zhang et al., ICLR 2017）。正常训练下，模型会<em>先学规律、后记噪声</em>（这就是「记忆化效应」，也是后面 AUM 方法的基础）。而 OHEM 把梯度预算全部导向噪声样本，<strong>大幅加速了记忆过程</strong>——本来 60 个 epoch 才会开始记的东西，20 个 epoch 就记住了。记住噪声 = 破坏了那一片特征空间的泛化。",
            "<strong>评测污染</strong>：如果验证集与训练集来自同一标注流程，它们的噪声率相同。<em>模型记住训练集噪声，在验证集上并不会变差多少</em>（因为验证集的噪声是另一批），但<strong>在真实路测上会明显变差</strong>。这就是「离线指标没掉、路测体验变糟」的一个真实来源。",
        ]),
        MATH("A \\;=\\; \\frac{P(\\text{noisy}\\mid \\text{selected})}{P(\\text{noisy})},\\qquad q_{\\text{eff}} = (1-r)\\,q + r\\,q\\,A \\;\\le\\; q_{\\max} \\;\\Longleftrightarrow\\; r \\;\\le\\; \\frac{q_{\\max}-q}{q\\,(A-1)}"),
        P("代一组真实的数字：标注噪声率 <code>q = 8%</code>，挖掘的噪声富集倍数 <code>A = 6</code>，能容忍的有效噪声率 <code>q_max = 15%</code>。得到 <code>r ≤ (0.15-0.08)/(0.08×5) = 0.175</code>——<strong>难例最多只能占 batch 的 17.5%</strong>。<em>而很多实现里 OHEM 的比例是 100%（整个 batch 都是挖出来的），这在 8% 噪声率下必然出事。</em>"),
        H3("TSR 场景里标注噪声从哪来"),
        TABLE(["噪声来源", "典型噪声率量级", "为什么难避免"], [
            ["<strong>细粒度类别标错</strong>（限速 60↔80、禁令类内部）", "2–8%", "百来个类，很多类只差一个数字或一道斜杠；标注员疲劳时凭第一印象点"],
            ["<strong>小目标漏标</strong>（&lt; 16 像素）", "10–30%（在小尺寸桶内）", "标注员看不清 / 规范说「太小可以不标」但边界模糊"],
            ["<strong>框位置不准</strong>", "小框上 ±2px 就是 25% 相对误差", "标注工具的最小拖动精度与图像缩放级别"],
            ["<strong>类别体系变更后的旧数据</strong>", "整批系统性错误", "新增细分类后，旧数据仍是粗类标签；版本混用时静默出错"],
            ["<strong>自动预标注（pre-labeling）被直接采纳</strong>", "取决于预标模型质量，5–15%", "为省成本用旧模型预标 + 人工快审，<strong>人工倾向于「看着差不多就过」</strong>——这会把旧模型的偏差固化进新数据"],
        ]),
        DUAL(
            "最后一行值得特别警惕，因为它制造了<strong>一个自我强化的闭环</strong>：旧模型预标 → 人工快审通过 → 新数据带着旧模型的偏差 → 训出的新模型继承这个偏差 → 下一轮预标偏差更强。<em>症状是「模型在某类上的错误怎么加数据都改不掉」</em>，因为你加的数据本身就是模型自己的错误产物。<strong>破解方法：预标注的样本必须有一定比例走「盲标」（不给预标结果，从零标注），并对比两者的差异率作为监控指标。</strong>",
            "从统计角度看，这是一个<span class=\"term\">confirmation bias</span>（确认偏差）在数据管线里的具体化：人类审核者面对一个已有答案时，<em>接受阈值远低于从零判断时</em>。相关研究给出的数字是，预标注会让标注员的「同意率」提高 10–20 个百分点，其中相当一部分是错误的同意。<strong>所以「预标注 + 快审」的真实质量必须用盲标子集去校准，而不能假设它等同于全人工标注。</strong>",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("separate", "怎么把「难例」和「噪声标签」分开", "".join([
        P("既然 loss 本身分不开这两者，就需要引入<strong>额外的信息维度</strong>。有四种方法，成本递增、可靠性也递增。<em>实践中它们是组合使用的：前两种做自动初筛，第三种做校准与验收。</em>"),
        H3("方法一：损失轨迹 / AUM（最便宜，应该默认开）"),
        P("原理是<strong>记忆化效应的时间不对称性</strong>：干净样本被「学会」（依靠可泛化的规律，早期就快速下降），噪声样本被「记住」（依靠模型容量硬背，发生得<strong>晚得多、也突然得多</strong>）。所以——"),
        UL([
            "<strong>只看最终 loss 分不开</strong>：训练足够久后，难例和噪声样本的最终 loss 可能都在 0.8 左右。",
            "<strong>看整条轨迹就分得开</strong>：难例的 loss 是「持续缓慢下降」；噪声的 loss 是「长期高位不动 + 晚期突降」。",
            "<span class=\"term\">AUM</span>（Area Under the Margin，Pleiss et al. 2020）把这件事做成一个标量：<code>AUM_i = mean_t [ z_i,y_i(t) − max_{c≠y_i} z_i,c(t) ]</code>，即<strong>全程「被指派标签的 logit」与「最大其他 logit」之差的均值</strong>。噪声样本的 AUM 显著更低甚至为负；难例的 AUM 低但为正。",
            "<strong>工程成本极低</strong>：只需在训练时每个 epoch 记录每个样本的 margin，存 <code>N×E</code> 个 float32。100 万样本 × 50 epoch = 200 MB。<em>没有理由不开。</em>",
        ]),
        H3("方法二：多模型一致性（最锋利的二维判据）"),
        P("训 K 个种子不同（或结构不同）的模型，看它们在这个样本上的预测。<strong>这给出一个非常干净的二维判据</strong>："),
        ASCII("""            模型间一致性 (consensus)
                    高
                     │
   ┌─────────────────┼─────────────────┐
   │  ④ **标注错误**  │   ✅ 简单样本     │
   │  K 个模型高度一致 │  模型一致，       │
   │  地预测了另一个类 │  且与标签一致      │
   │  → **强烈怀疑标错**│                 │
与 ├─────────────────┼─────────────────┤ 与
标 │  ③ 边界样本      │   ① 相似类混淆    │ 标
签 │  模型互相不一致，│  模型摇摆但       │ 签
不 │  也不同意标签    │  多数同意标签     │ 一
一 │  → **真难例**    │  → **真难例**     │ 致
致 └─────────────────┼─────────────────┘
                     │
                    低

判据（可直接写成代码）：
  is_mislabeled = (多数票类别 ≠ 标签) AND (多数票占比 ≥ 0.8)
  is_hard       = (多数票占比 < 0.6)          ← 模型自己都吵起来了

  ⚠️ 注意 K 个模型必须**独立**：不同种子 + 不同数据顺序，
     最好还有不同架构。**同一个模型的不同 checkpoint 不算独立。**""")
        ,
        H3("方法三：重标注抽检（唯一能给出真值的方法）"),
        P("前两种方法只能给出<em>怀疑</em>，要知道真实噪声率、要给前两种方法定阈值，只能<strong>抽样重标</strong>。关键是样本量：要把噪声率 <code>p≈10%</code> 估计到 <strong>±2%（95% 置信）</strong>，需要"),
        MATH("n \\;\\ge\\; \\frac{z_{0.975}^{2}\\,p(1-p)}{\\varepsilon^{2}} \\;=\\; \\frac{1.96^{2}\\times 0.1\\times 0.9}{0.02^{2}} \\;\\approx\\; 865"),
        P("也就是<strong>大约 900 个样本</strong>——这是一个完全负担得起的数字，而且它换来的是整条挖掘链路的可信度。<em>实操上要做双人独立标注 + 第三方仲裁，并汇报 <span class=\"term\">Cohen's κ</span>（标注一致性系数）</em>：κ &lt; 0.6 说明规范本身有问题，此时讨论噪声率没有意义。"),
        H3("方法四：可疑样本降权而非删除"),
        P("识别出可疑样本后，<strong>默认动作应该是降权（比如权重 ×0.2），而不是删除</strong>。因为：① 前两种方法都有误判，删掉的可能是真难例——而真难例恰恰最宝贵；② 降权是可逆的、可调的；③ 删除会改变数据分布（被删的往往集中在特定类别/场景，等于悄悄做了一次有偏采样）。<em>只有经过重标注确认的错误标签才应该被真正删除或修正。</em>"),
        TABLE(["方法", "需要什么", "成本", "能给出什么", "什么时候用"], [
            ["<strong>损失轨迹 / AUM</strong>", "训练时记录每 epoch 的 per-sample margin", "<strong>几乎为零</strong>（N×E 个 float）", "一个可排序的可疑度分数", "<strong>默认全程开启</strong>"],
            ["<strong>多模型一致性</strong>", "K≥3 个独立训练的模型", "K 倍训练成本（可用已有的消融模型复用）", "二维判据：可疑标注 vs 真难例", "有多个模型时（几乎总是有）"],
            ["<strong>重标注抽检</strong>", "标注人力 + 仲裁流程", "~900 样本 × 单价", "<strong>真值</strong>：噪声率、κ、前两种方法的 PR", "每个数据版本发布前一次"],
            ["<strong>降权而非删除</strong>", "训练管线支持 per-sample weight", "接近零", "风险可控的缓解", "永远（作为默认策略）"],
        ]),
        DUAL(
            "把四种方法串成一条可执行的流程：<strong>① 训练时记 margin → ② 算 AUM，取最低的 2–5% 作为「可疑池」→ ③ 用 K 模型一致性把可疑池分成「疑似标错」和「真难例」→ ④ 从「疑似标错」里抽 900 个去重标，得到这套判据的精确率 → ⑤ 按精确率决定是全量重标、还是降权处理</strong>。<em>整条流程只在第 ④ 步花人力钱，其余全自动。</em>",
            "有一个反直觉但重要的细节：<strong>「真难例」的判定应该比「疑似标错」更保守</strong>。误把标错当难例（假阴性）的代价是模型被污染；误把难例当标错（假阳性）的代价只是少用了一个宝贵样本——<em>但如果你选择的是「降权」而不是「删除」，后一种代价会小得多</em>。<strong>这就是为什么「降权优先」不只是谨慎，而是让整套判据可以调得更激进的前提条件。</strong>",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("pool", "难例池、采样比例与课程学习", "".join([
        P("最后把机制变成可以上线的工程形态。真实系统里没有人每步重新扫全量数据算 loss——那太贵。标准做法是维护一个<strong>难例池（hard example pool）</strong>。"),
        ASCII("""难例池的结构与生命周期

  pool[sample_id] = {
      'loss_ema':   0.83,      # 指数滑动平均，避免单次波动
      'last_seen':  epoch 12,  # 上次被评估的时间
      'n_sampled':  7,         # **被采样次数（用于封顶）**
      'aum':        -0.4,      # 可疑度（来自损失轨迹）
      'bucket':     'night',   # **失效模式分桶**：夜间/遮挡/相似类/小目标
  }

  每个 batch：
    ┌──────────────────────────────────────────────┐
    │  batch = (1-r) × 随机采样   +   r × 池采样     │
    │                                              │
    │  池采样时：                                   │
    │    · 按 loss_ema 加权，但 **每桶有独立配额**   │
    │      （防止「夜间」桶吃掉全部预算）             │
    │    · 跳过 n_sampled > cap 的样本（过采样封顶）  │
    │    · 跳过 aum < τ 的样本（疑似标注错误）        │
    └──────────────────────────────────────────────┘

  老化（aging）：模型在变，三个 epoch 前的难例现在可能已经会了
    · loss_ema 每 epoch 乘衰减因子，强制样本重新证明自己「还难」
    · last_seen 超过 E_max 的样本被踢出池，回到随机采样池
    ⚠️ 不做老化的池会变成一个「化石集合」——
       里面全是模型早期不会、现在早已学会的样本，白白浪费预算。""")
        ,
        TABLE(["超参", "典型取值", "调它的依据", "调错的症状"], [
            ["<strong>难例比例 r</strong>", "0.1 – 0.3", "<strong>由噪声率决定</strong>（第 6 节的公式）", "过大：训练不稳、验证集掉点；过小：与不挖掘无差别"],
            ["<strong>过采样封顶 cap</strong>", "单样本 ≤ 5–10 次/epoch", "防止个别样本被采上百次", "不设：某几个样本变成事实上的「验证集」，模型对它们过拟合"],
            ["<strong>loss EMA 衰减</strong>", "0.9 – 0.95", "模型变化速度（lr 大则衰减快）", "太慢：池变化石；太快：等于每步重扫，噪声大"],
            ["<strong>桶配额</strong>", "每桶 ≤ 30% 池预算", "失效模式的优先级（C55 m03 的打分）", "不设：单一失效模式吃光预算，其他模式永远修不了"],
            ["<strong>AUM 剔除阈值 τ</strong>", "最低 2–5%", "重标注抽检得到的精确率", "太松：噪声进池；太紧：真难例被误剔"],
        ]),
        H3("Curriculum vs anti-curriculum：一个被噪声率决定的选择"),
        P("<span class=\"term\">Curriculum learning</span>（课程学习，Bengio et al. 2009）主张<strong>先易后难</strong>；OHEM 本质上是 <strong>anti-curriculum</strong>（先难后易，甚至永远只学难的）。两派各有大量实验支持，看起来矛盾——但把噪声率放进来，矛盾就消失了："),
        UL([
            "<strong>数据干净（q &lt; 2%）</strong>：难样本几乎都是真难例，anti-curriculum（OHEM / 大 γ）收益最大。",
            "<strong>数据脏（q &gt; 5%）</strong>：难样本里混着大量噪声，<strong>先易后难更安全</strong>——先用干净易学的规律把模型建立起来，再逐步引入难样本，且此时模型已有能力把噪声识别出来（<span class=\"term\">small-loss trick</span> 与 co-teaching 的基础）。",
            "<strong>实操折中</strong>：<em>warmup 阶段均匀采样 → 中期逐渐把 r 从 0 升到目标值 → 后期把 AUM 最低的样本剔除</em>。这条曲线同时满足了两派的诉求。",
        ]),
        DUAL(
            "还要注意难例挖掘与<strong>模块 01 的类别重采样会互相放大</strong>。稀有类样本天然 loss 更高（见得少、学得差），所以难例挖掘<em>本身就在过采样稀有类</em>。如果同时开着 repeat factor sampling（<code>r_c = max(1, √(t/f_c))</code>），一个稀有类样本的总放大倍数可能是 <code>r_c × A</code>——轻松到 20–50 倍。<strong>症状是稀有类训练 loss 极低但验证召回不涨（纯粹过拟合了那几十个样本）。</strong>",
            "正确做法是<strong>把「总放大倍数」当成一个需要显式预算的量</strong>：对每个类别，统计它在实际训练流中出现的期望次数与其原始频率之比，<em>把这个比值封顶</em>（比如 ≤ 10×）。这需要重采样与难例挖掘在同一个采样器里协调，而不是两个独立模块各干各的。<strong>面试里如果被问「长尾和难例挖掘怎么一起用」，这个「总放大倍数封顶」就是标准答案</strong>——它说明你想过两个机制的交互，而不是只会分别背它们。",
        ),
        CALLOUT("intuition", "把整节浓缩成一条可迁移的原则：<strong>难例挖掘不是「找最难的」，而是「在给定的标注质量下，找信息量最大且可信的那批」</strong>。「可信」这个约束是绝大多数教程会漏掉的一半，而它在真实数据上决定了成败。<em>所以任何难例挖掘方案的设计文档里，都应该有一节叫「我们如何确认挖到的不是噪声」——没有这一节，方案就是不完整的。</em>"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("frontier", "研究前沿与开放问题", "".join([
        P("难例挖掘看起来是个 2016 年就解决了的老问题，但它的三个核心假设——「loss 高 = 有价值」「标签是对的」「样本价值可独立评估」——每一条都在被重新审视。"),
        UL([
            "<strong>噪声鲁棒学习（learning with noisy labels）</strong>：<em>Co-teaching</em>（两个网络互相筛选小损失样本喂给对方，利用「两个网络的记忆化偏差不同」）、<em>DivideMix</em>（用 GMM 拟合 loss 分布把数据分成干净/噪声两半，噪声半当无标签做半监督）、噪声鲁棒损失（GCE、SCE、对称交叉熵）。<em>这一支的共同思想是：不要试图区分难例和噪声，而是设计一个对两者都不敏感的训练过程。</em>",
            "<strong>样本价值的理论化</strong>：<em>influence function</em>（去掉这个样本，测试损失会怎么变）、<em>TracIn</em>（沿训练轨迹累计该样本对测试样本损失的影响）、<em>Data Shapley</em>（合作博弈论视角的样本贡献分配）。<strong>它们比 loss 排序本质得多——直接度量「对测试指标的贡献」而不是「模型拟合得多差」</strong>，但计算成本目前还上不了千万级数据集。<em>这是「难例挖掘」这个领域真正的开放问题。</em>",
            "<strong>数据剪枝与 scaling law</strong>：Sorscher et al.（NeurIPS 2022）给出一个反直觉但重要的结论——<strong>数据充足时应保留难样本，数据稀缺时应保留简单样本</strong>；而好的剪枝策略可以把误差-数据量的幂律关系打破成指数关系。<em>这直接反驳了「永远挖难例」的朴素做法：挖难例的正确性取决于你处在数据量的哪一段。</em>",
            "<strong>检测特有的开放问题：难例的粒度</strong>。loss 定义在框/anchor 级，但「这张图值不值得回传/标注」是图级决策。<strong>框级难度如何正确聚合到图级</strong>（max？top-k 均值？考虑框数量的归一化？）目前没有公认答案——这正是下一模块（主动学习触发器）要处理的核心技术点。",
            "<strong>用 VLM 做难例分类</strong>：不再只按 loss 排序，而是用视觉-语言模型直接判断「这个 badcase 属于哪类失效模式」（遮挡？逆光？相似类？标注错？）。<em>这把难例挖掘从一个标量排序问题变成了结构化归因问题</em>，也正是当前「automated data mining workflow」的主流形态（模块 04 展开）。",
            "<strong>标注质量的在线监控</strong>：与其事后检测噪声，不如把 AUM / 模型-标注分歧率做成<strong>标注流水线的实时质控指标</strong>，直接反馈给标注团队。这条工程路线目前缺少公开的最佳实践，但在头部自动驾驶团队里已是标配。",
        ]),
        CALLOUT("paper", "必读：Shrivastava, Gupta, Girshick, <em>Training Region-based Object Detectors with Online Hard Example Mining</em>（CVPR 2016）——OHEM 原文，重点看 3.2 节里关于「用 loss 作为分数做 NMS 去重」的那一段；Lin et al., <em>Focal Loss for Dense Object Detection</em>（ICCV 2017）——重点读第 3 节对 OHEM 的对比实验（表 1(d)），论文自己就把「focal 是 OHEM 的软化」讲清楚了；Pleiss et al., <em>Identifying Mislabeled Data using the Area Under the Margin Ranking</em>（NeurIPS 2020）——AUM 方法与「插入阈值样本」的巧妙定阈技巧；Han et al., <em>Co-teaching</em>（NeurIPS 2018）与 Li et al., <em>DivideMix</em>（ICLR 2020）——噪声鲁棒训练的两条主线；Zhang et al., <em>Understanding Deep Learning Requires Rethinking Generalization</em>（ICLR 2017）——记忆化效应的源头；Sorscher et al., <em>Beyond Neural Scaling Laws: Beating Power Law Scaling via Data Pruning</em>（NeurIPS 2022）——数据剪枝与「什么时候该保留简单样本」。相邻模块：C58 m01（类别不平衡）、C58 m03（主动学习触发器）、C61 m02（误差分析）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 难例挖掘（OHEM / NMS 去重 / Focal 是软性 OHEM / 噪声标签陷阱 / AUM）

目标：把「难例挖掘」从一句口号变成可度量的工程。你会亲手看到
**不去重的 OHEM 为什么比不做 OHEM 更差**、**Focal Loss 与 OHEM 在数学上是同一件事的软硬两版**，
以及本模块最重要的那个实验——**挖掘过头会把噪声标签当难例，把模型毁掉**。

本 notebook 你会亲手实现：
1. **IoU / NMS / OHEM**，并量化「不去重时 top-k 被 2–4 个区域吃光」
2. 正负样本**分开挖**与 loss 归一化（除以 k 还是除以 N）
3. **Focal 权重与 OHEM 掩码的排序一致性证明** + 有效样本数 `n_eff=(Σw)²/Σw²` → γ ↔ 等价 k 换算
4. **噪声放大系数 A** 的测量：top-1% 高 loss 样本里噪声占比 / 总体噪声率
5. **关键实验**：干净 vs 20% 噪声 × {均匀采样, OHEM, Focal}，看清 OHEM 如何记住噪声、毁掉泛化
6. **AUM（损失轨迹）** 区分难例与噪声：证明「只看最终 loss 分不开，看整条轨迹分得开」
7. **多模型一致性**的二维判据 + 重标注抽检的样本量计算
8. **难例池**（EMA / 老化 / 过采样封顶 / 桶配额）与**安全挖掘比例**公式

> 心智模型：**难例挖掘不是「找最难的」，而是「在给定标注质量下，找信息量最大且可信的那批」。
> 「可信」这一半是绝大多数教程会漏掉的，而它在真实数据上决定成败。**"""),

    md("""## 1 · 合成候选框：难例天然「扎堆」

真实检测器一张图上有 10³–10⁵ 个候选框，而且**一个难区域周围会有几十个高度重叠的候选**。
这个性质是下一节 NMS 去重的全部理由，所以先把它造出来。"""),
    code("""import numpy as np

rng = np.random.default_rng(0)

def make_proposals(n_hot=8, per_hot=40, n_scatter=1600, W=640, H=384, seed=0):
    \"\"\"合成一张图的候选框。
       · n_hot 个「难区域热点」，每个周围有 per_hot 个**高度重叠**的候选（loss 都很高）
       · n_scatter 个散落的简单背景候选（loss 接近 0）
       region id: 0..n_hot-1 表示热点；1000+ 表示各自独立的散点区域\"\"\"
    r = np.random.default_rng(seed)
    boxes, loss, region = [], [], []
    centers = r.uniform([80, 80], [W - 80, H - 80], size=(n_hot, 2))
    hot_loss = np.linspace(3.0, 2.0, n_hot)          # 热点之间难度拉开，便于观察 top-k 归属
    for i, (cx, cy) in enumerate(centers):
        for _ in range(per_hot):
            jx, jy = r.normal(0, 1.5, 2)             # 抖动很小 -> 彼此 IoU 很高
            s = 32.0
            boxes.append([cx + jx - s/2, cy + jy - s/2, cx + jx + s/2, cy + jy + s/2])
            loss.append(hot_loss[i] + r.normal(0, 0.03))
            region.append(i)
    for j in range(n_scatter):
        cx, cy = r.uniform([30, 30], [W - 30, H - 30])
        s = r.uniform(20, 60)
        boxes.append([cx - s/2, cy - s/2, cx + s/2, cy + s/2])
        loss.append(r.exponential(0.12))             # 简单背景：梯度 ~1e-3 量级
        region.append(1000 + j)
    return np.asarray(boxes), np.asarray(loss), np.asarray(region)

BOXES, LOSS, REGION = make_proposals()
easy = (LOSS < 0.5).mean()
print(f'候选框总数 {len(BOXES)}（8 个热点 × 40 个重叠候选 + 1600 个散点）')
print(f'loss 分位数  p50={np.percentile(LOSS,50):.3f}  p90={np.percentile(LOSS,90):.3f}  max={LOSS.max():.3f}')
print(f'loss < 0.5 的「简单样本」占比 {easy:.1%}   ← 它们的梯度 |p-y| ~ 1e-3，数量却占绝对多数')
assert easy > 0.78
assert LOSS[REGION < 1000].min() > LOSS[REGION >= 1000].max(), '热点区域的 loss 应全面高于散点'
print('✅ 数据就位：难例天然扎堆 —— 这正是朴素 OHEM 会失效的原因')"""),

    md("""## 2 · OHEM：去重与不去重，差别是「有效 batch = 3」还是「= 100」

OHEM 的机制是「按 loss 排序取 top-k 反传」。
**但候选框高度重叠，直接排序会让 top-k 被一两个热点吃光。**
原论文的做法是：**先用 loss 当分数做一遍 NMS（IoU 0.7），再取 top-k**。"""),
    code("""def iou_1_to_n(box, others):
    x1 = np.maximum(box[0], others[:, 0]); y1 = np.maximum(box[1], others[:, 1])
    x2 = np.minimum(box[2], others[:, 2]); y2 = np.minimum(box[3], others[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    a = (box[2] - box[0]) * (box[3] - box[1])
    b = (others[:, 2] - others[:, 0]) * (others[:, 3] - others[:, 1])
    return inter / (a + b - inter + 1e-9)

def nms(boxes, scores, iou_thr):
    \"\"\"标准贪心 NMS。返回的下标已按 score 降序。\"\"\"
    order = np.argsort(-scores); keep = []
    while order.size:
        i = order[0]; keep.append(i)
        if order.size == 1:
            break
        ious = iou_1_to_n(boxes[i], boxes[order[1:]])
        order = order[1:][ious <= iou_thr]
    return np.asarray(keep, dtype=int)

def ohem(boxes, losses, k, dedup_iou=None):
    \"\"\"dedup_iou=None -> 朴素 OHEM（**错误实现**）
       dedup_iou=0.7   -> 原论文实现：**先用 loss 当分数做 NMS**，再取 top-k\"\"\"
    if dedup_iou is None:
        return np.argsort(-losses)[:k]
    return nms(boxes, losses, dedup_iou)[:k]

K = 128
sel_naive = ohem(BOXES, LOSS, K)
sel_dedup = ohem(BOXES, LOSS, K, dedup_iou=0.7)

def cover(sel):
    reg = REGION[sel]
    uniq, cnt = np.unique(reg, return_counts=True)
    return len(uniq), int(cnt.max())

n_naive, mx_naive = cover(sel_naive)
n_dedup, mx_dedup = cover(sel_dedup)
print(f'{"实现":<26s}{"top-128 覆盖的不同区域数":>24s}{"单区域最多占":>14s}')
print(f'{"朴素 OHEM（不去重）":<24s}{n_naive:>22d}{mx_naive:>14d}')
print(f'{"OHEM + NMS 去重(0.7)":<24s}{n_dedup:>22d}{mx_dedup:>14d}')
assert n_naive <= 6,  '不去重时 top-k 应被极少数热点吃光'
assert n_dedup >= 60, '去重后 top-k 应覆盖大量不同区域'
assert mx_naive >= 30 and mx_dedup <= 12
print(f'\\n⚠️  不去重：128 个样本其实是 {n_naive} 件事的 128 份拷贝 -> **有效 batch ≈ {n_naive}**')
print('    梯度被单个区域完全支配 -> loss 震荡、在几个区域上过拟合、换数据骤降。')
print('✅ 「用 loss 当分数做一遍 NMS」在论文里只是一句话，在代码里是决定成败的一行。')"""),

    code("""# ── 细节 ②：正负样本必须分开挖 ──
n_pos, n_hardneg, n_easyneg = 20, 80, 1820
loss_pos     = rng.gamma(2.0, 0.25, n_pos)          # 正样本：loss 中等
loss_hardneg = rng.uniform(2.0, 4.0, n_hardneg)     # 难负样本：高分假正例
loss_easyneg = rng.exponential(0.10, n_easyneg)     # 简单负样本
all_loss = np.r_[loss_pos, loss_hardneg, loss_easyneg]
is_pos   = np.r_[np.ones(n_pos, bool), np.zeros(n_hardneg + n_easyneg, bool)]

K2 = 64
top_mixed = np.argsort(-all_loss)[:K2]
print(f'不分开挖  -> top-{K2} 里正样本数 = {int(is_pos[top_mixed].sum())}   ← 回归分支拿不到任何梯度')
assert is_pos[top_mixed].sum() == 0

kp = K2 // 4; kn = K2 - kp                           # 维持 1:3 正负比
idx_p = np.where(is_pos)[0];  idx_n = np.where(~is_pos)[0]
sel_p = idx_p[np.argsort(-all_loss[idx_p])[:kp]]
sel_n = idx_n[np.argsort(-all_loss[idx_n])[:kn]]
print(f'正负分开挖 -> 正 {len(sel_p)} 个 + 负 {len(sel_n)} 个（1:3）')
assert len(sel_p) == kp and is_pos[sel_p].all()

# ── 细节 ③：loss 除以 k 还是除以 N ──
sel = np.r_[sel_p, sel_n]
g_over_k = all_loss[sel].sum() / len(sel)
g_over_N = all_loss[sel].sum() / len(all_loss)
print(f'\\n除以 k: {g_over_k:.3f}   除以 N: {g_over_N:.4f}   比值 {g_over_k/g_over_N:.1f}×')
print(f'⚠️  除以 N 相当于把学习率悄悄乘上 k/N = {len(sel)}/{len(all_loss)} = {len(sel)/len(all_loss):.3f}')
assert abs(g_over_k / g_over_N - len(all_loss) / len(sel)) < 1e-6
print('✅ 正确做法：除以**实际参与反传的样本数 k**，这样 k 才是一个可独立调的超参。')"""),

    md("""## 3 · Focal Loss 是软性 OHEM

两者都能写成 $\\mathcal{L}=\\sum_i w_i\\ell_i$：
OHEM 的 $w_i=\\frac{1}{k}\\mathbb{1}[\\ell_i\\ge\\ell_{(k)}]$（**阶跃**），
Focal 的 $w_i=(1-p_i)^\\gamma$（**连续**）。
下面证明两件事：**① 排序完全一致**（所以 focal 的 top-k 就是 OHEM 会选的那 k 个）；
**② 用有效样本数把 γ 翻译成「等价的 k」**。"""),
    code("""p = rng.uniform(0.005, 0.995, 4000)          # 模型给**正确类别**的概率 p_t
ce = -np.log(p)                                 # 交叉熵 loss
focal_w = lambda pt, g: (1.0 - pt) ** g

# ① 排序一致性：CE loss 与 focal 权重都是 p_t 的严格单调减函数
order_ce = np.argsort(-ce)
for g in [0.5, 1.0, 2.0, 5.0]:
    assert np.array_equal(np.argsort(-focal_w(p, g)), order_ce), f'gamma={g}'
print('✅ 对任意 γ，「按 focal 权重排序」与「按 loss 排序」**完全一致**')
print('   ⇒ focal 眼中最重要的 k 个样本，就是 OHEM 会选中的那 k 个。')
print('   ⇒ 二者唯一的差别：**被排除的样本，权重是恰好 0（OHEM）还是很小的 ε（focal）**。\\n')

# ② 两种权重的形状对比
print(f'{"p_t":>7s}{"CE loss":>10s}{"focal w (γ=2)":>15s}{"OHEM w (top-10%)":>19s}')
thr = np.percentile(ce, 90)
for pt in [0.99, 0.9, 0.7, 0.5, 0.3, 0.1, 0.02]:
    l = -np.log(pt)
    print(f'{pt:>7.2f}{l:>10.3f}{(1-pt)**2:>15.4f}{("1.0" if l >= thr else "0.0（丢弃）"):>19s}')
print('\\n⚠️  OHEM 把 p_t=0.7 这类「还没学好但也不算太差」的样本权重直接置 0；')
print('    focal 给它 0.09 的权重 —— **保留但降权**。这是 OHEM「会忘掉已学会的东西」的根源。')"""),

    code("""# ── 有效样本数：把 γ 翻译成「等价的 top-k」──
def n_eff(w):
    \"\"\"加权平均的等效样本量 (Σw)²/Σw²。
       · 对 OHEM（k 个权重为 1，其余为 0）恰好等于 k —— 所以这个量可以直接对齐两种方法\"\"\"
    w = np.asarray(w, dtype=float)
    return float(w.sum() ** 2 / (w ** 2).sum())

# 先验证它在 OHEM 上就是 k
w_ohem = np.zeros(1000); w_ohem[:137] = 1.0
assert abs(n_eff(w_ohem) - 137) < 1e-9
print(f'n_eff(OHEM top-137) = {n_eff(w_ohem):.1f}  ✅ 与 k 完全一致\\n')

# 一个真实感的 p_t 分布：绝大多数样本已经学得很好
p_real = rng.beta(9.0, 1.0, 20000)
N = len(p_real)
print(f'{"γ":>5s}{"n_eff":>12s}{"占全体比例":>14s}{"等价的 OHEM k":>16s}')
prev = None
for g in [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]:
    ne = n_eff(focal_w(p_real, g))
    print(f'{g:>5.1f}{ne:>12.1f}{ne/N:>13.1%}{int(round(ne)):>16d}')
    if prev is not None:
        assert ne < prev, 'γ 越大，等效样本量越小'
    prev = ne
assert abs(n_eff(focal_w(p_real, 0.0)) - N) < 1e-6, 'γ=0 时 focal 退化为 CE，n_eff 应等于 N'
print('\\n✅ γ 不是一个玄学超参：它等价于「只让 n_eff 个样本真正贡献梯度」。')
print('⚠️  这也解释了为什么 γ 从 2 调到 5 常常直接训崩 —— 等效样本量掉一个数量级，梯度方差爆炸。')
print('⚠️  推论：**OHEM 与 Focal 不要同时开**，否则等效样本量被平方级压缩。')"""),

    md("""## 4 · 难例的类型学：loss 排序分不清「难」和「错」

四类样本——① 相似类混淆 ② 背景误检 ③ 边界样本 ④ **标注错误**——的 loss 分布是**重叠**的，
而且 ④ 系统性地排在最前面。下面用一个 AUC 量化「单靠 loss 能不能把 ④ 从 ③ 里分出来」。"""),
    code("""def auc(scores_pos, scores_neg):
    \"\"\"Mann-Whitney U 形式的 AUC：P(score_pos > score_neg)，含并列各算一半。\"\"\"
    s = np.r_[scores_pos, scores_neg]
    r = np.empty(len(s)); order = np.argsort(s, kind='mergesort')
    sr = s[order]; i = 0
    while i < len(s):                                  # 处理并列：取平均秩
        j = i
        while j + 1 < len(s) and sr[j + 1] == sr[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    n1 = len(scores_pos)
    return (r[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * len(scores_neg))

assert abs(auc([3., 2.], [1., 0.]) - 1.0) < 1e-12
assert abs(auc([1., 1.], [1., 1.]) - 0.5) < 1e-12

GROUPS = {
    '① 相似类混淆': rng.gamma(3.0, 0.28, 600),     # 中等 loss
    '② 背景误检':   rng.gamma(2.0, 0.55, 400),     # 分布很宽
    '③ 边界样本':   rng.gamma(6.0, 0.32, 500),     # 偏高
    '④ 标注错误':   rng.gamma(8.0, 0.32, 120),     # **系统性最高**
}
print(f'{"类型":<16s}{"n":>6s}{"loss 均值":>11s}{"loss p90":>10s}')
for kname, v in GROUPS.items():
    print(f'{kname:<14s}{len(v):>6d}{v.mean():>11.2f}{np.percentile(v,90):>10.2f}')

a_noise_vs_hard = auc(GROUPS['④ 标注错误'], GROUPS['③ 边界样本'])
print(f'\\n只用 loss 区分「④ 标注错误」vs「③ 边界样本」的 AUC = {a_noise_vs_hard:.3f}')
assert 0.55 < a_noise_vs_hard < 0.85, 'loss 有一点信号，但远不足以判别'
top1 = np.argsort(-np.concatenate(list(GROUPS.values())))[:int(0.01 * sum(map(len, GROUPS.values())))]
labels = np.concatenate([[k] * len(v) for k, v in GROUPS.items()])
frac4 = (labels[top1] == '④ 标注错误').mean()
enrich = frac4 / (120 / 1620)
print(f'top-1% 最高 loss 里「④ 标注错误」占 {frac4:.0%}（全体里只占 {120/1620:.0%}）-> 富集 {enrich:.1f}×')
assert enrich > 2.5, '挖得越狠，选中样本里标注错误的占比越高'
print('\\n⚠️  loss 有信号但**不足以判别**（AUC 只有 0.6-0.8）——')
print('    而挖掘越激进，选中的样本里「④ 标注错误」的占比越高。这就是下一节的主题。')"""),

    md("""## 5 · 挖掘过头：噪声标签会被当成最有价值的难例

先量化**噪声放大系数** $A=\\dfrac{P(\\text{noisy}\\mid\\text{selected})}{P(\\text{noisy})}$，
再做本模块最重要的实验：**同一份数据、同一个模型，只换采样策略**，看 OHEM 如何在 20% 噪声下把模型毁掉。"""),
    code("""# ── 噪声放大系数 A ──
Nn, q = 5000, 0.08
noisy_flag = rng.random(Nn) < q
loss_mix = np.where(noisy_flag,
                    rng.gamma(6.0, 0.50, Nn),      # 噪声样本：与任何可学规律矛盾 -> loss 长期最高
                    rng.gamma(1.5, 0.35, Nn))      # 干净样本
base_rate = noisy_flag.mean()
print(f'总体噪声率 q = {base_rate:.1%}')
print(f'{"挖掘比例 r":>11s}{"选中样本里的噪声率":>20s}{"放大系数 A":>13s}')
As = {}
for frac in [0.01, 0.02, 0.05, 0.10, 0.30, 1.00]:
    kk = max(1, int(Nn * frac))
    sel = np.argsort(-loss_mix)[:kk]
    rate = noisy_flag[sel].mean()
    As[frac] = rate / base_rate
    print(f'{frac:>11.0%}{rate:>19.1%}{As[frac]:>13.2f}×')
assert As[0.01] > 5.0,  'top-1% 里噪声应被强烈富集'
assert As[0.01] > As[0.10] > As[1.00], '挖得越狠，噪声富集越严重'
assert abs(As[1.00] - 1.0) < 1e-9, '全选 = 不挖掘 -> A=1'
print('\\n⚠️  A 是「难例挖掘的噪声放大器增益」。q=8% 的数据，挖 top-1% 时')
print(f'    实际喂给模型的噪声率高达 {base_rate*As[0.01]:.0%} —— 而你以为自己在喂难例。')"""),

    code("""# ══════════════════════════════════════════════════════════════
# 关键实验：干净 vs 20% 噪声  ×  {均匀采样, OHEM, Focal}
# 同一份数据、同一个模型（2-32-1 的 tanh MLP）、同样的步数，**只换采样策略**
# ══════════════════════════════════════════════════════════════
WARMUP, STEPS, KSEL = 100, 1000, 80

def make_toy(n=800, noise=0.0, seed=1, sep=2.0):
    r = np.random.default_rng(seed)
    y = (r.random(n) < 0.5).astype(float)
    mu = np.where(y[:, None] > 0.5, np.array([sep, 0.0]), np.array([-sep, 0.0]))
    X = mu + r.normal(0, 1.0, size=(n, 2))
    y_obs = y.copy()
    flip = r.random(n) < noise                       # **标签噪声**：随机翻转
    y_obs[flip] = 1.0 - y_obs[flip]
    return X, y, y_obs, flip

def mlp_init(h=32, seed=0):
    r = np.random.default_rng(seed)
    return {'W1': r.normal(0, 0.8, (2, h)), 'b1': np.zeros(h),
            'W2': r.normal(0, 0.8, (h, 1)), 'b2': np.zeros(1)}

def mlp_prob(par, X):
    H = np.tanh(X @ par['W1'] + par['b1'])
    return 1.0 / (1.0 + np.exp(-(H @ par['W2'] + par['b2']).ravel())), H

def fit(X, y, strategy='uniform', k=KSEL, gamma=2.0, steps=STEPS, warmup=WARMUP, lr=0.6, seed=0):
    par = mlp_init(seed=seed)
    hist = []
    for t in range(steps):
        p, H = mlp_prob(par, X)
        ell = -(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
        if t < warmup or strategy == 'uniform':      # **warmup 期一律均匀采样**
            sw = np.ones(len(y))
        elif strategy == 'ohem':
            sw = np.zeros(len(y)); sw[np.argsort(-ell)[:k]] = 1.0
        else:                                        # focal
            pt = np.where(y > 0.5, p, 1 - p); sw = (1 - pt) ** gamma
        sw = sw / (sw.sum() + 1e-12)                 # 归一化：三种策略的总步长可比
        hist.append(sw)
        d = (p - y) * sw
        gW2 = H.T @ d[:, None]; gb2 = np.array([d.sum()])
        dH = (d[:, None] @ par['W2'].T) * (1 - H ** 2)
        par['W1'] -= lr * (X.T @ dH); par['b1'] -= lr * dH.sum(0)
        par['W2'] -= lr * gW2;        par['b2'] -= lr * gb2
    return par, np.asarray(hist)

Xn, _, yn_obs, flip = make_toy(800, noise=0.20, seed=1)        # 20% 标签噪声
Xc, _, yc_obs, _    = make_toy(800, noise=0.00, seed=1)        # 同分布的干净版
Xte, yte, _, _      = make_toy(4000, noise=0.0, seed=99)       # **干净测试集**

rows = []
for tag, (Xd, yd, fl) in {'干净数据 (q=0%)':  (Xc, yc_obs, np.zeros(800, bool)),
                          '含噪数据 (q=20%)': (Xn, yn_obs, flip)}.items():
    for strat in ['uniform', 'ohem', 'focal']:
        par, sws = fit(Xd, yd, strategy=strat, seed=0)
        p_te, _ = mlp_prob(par, Xte)
        acc = float(((p_te > 0.5).astype(float) == yte).mean())      # 干净测试集上的泛化
        p_tr, _ = mlp_prob(par, Xd)
        memo = float(((p_tr[fl] > 0.5).astype(float) == yd[fl]).mean()) if fl.any() else float('nan')
        # 刚开启挖掘后 100 步里，分给噪声样本的梯度预算
        bud = float(sws[WARMUP:WARMUP + 100][:, fl].sum(axis=1).mean()) if fl.any() else float('nan')
        rows.append((tag, strat, acc, memo, bud))

print(f'{"数据":<18s}{"策略":<10s}{"干净测试集准确率":>18s}{"记住噪声标签":>15s}{"梯度预算给噪声":>17s}')
for tag, s, a, mm, bg in rows:
    f = lambda v: '—' if v != v else f'{v:.1%}'
    print(f'{tag:<16s}{s:<10s}{a:>17.1%}{f(mm):>16s}{f(bg):>17s}')

d = {(t, s): (a, mm, bg) for t, s, a, mm, bg in rows}
acc_cu, acc_co = d[('干净数据 (q=0%)', 'uniform')][0], d[('干净数据 (q=0%)', 'ohem')][0]
acc_u, acc_o, acc_f = (d[('含噪数据 (q=20%)', s)][0] for s in ['uniform', 'ohem', 'focal'])
memo_u, memo_o = (d[('含噪数据 (q=20%)', s)][1] for s in ['uniform', 'ohem'])
bud_u, bud_o = (d[('含噪数据 (q=20%)', s)][2] for s in ['uniform', 'ohem'])

assert acc_co > acc_cu - 0.03, '**干净数据上 OHEM 完全没问题** —— 这是对照组'
assert bud_o > 1.5 * bud_u,    'OHEM 把远超基线比例的梯度预算交给了噪声样本'
assert memo_o > memo_u + 0.15, 'OHEM 显著加速了对噪声标签的**记忆化**'
assert acc_o < acc_u - 0.15,   'OHEM 在含噪数据上的泛化崩坏'
assert acc_f > acc_u - 0.03,   'Focal 的软加权对噪声鲁棒得多'
print(f'\\n✅ 对照组：**干净数据上 OHEM 一点问题都没有**（{acc_co:.1%} vs 均匀 {acc_cu:.1%}）。')
print(f'⚠️  换成 20% 噪声：OHEM 把 {bud_o:.0%} 的梯度预算给了噪声样本（基线只有 {bud_u:.0%}，'
      f'放大 {bud_o/bud_u:.1f}×），')
print(f'    对噪声标签的记忆率从 {memo_u:.0%} 飙到 {memo_o:.0%}，')
print(f'    干净测试集准确率从 {acc_u:.1%} **崩到 {acc_o:.1%}** —— 模型被自己的挖掘策略毁掉了。')
print(f'✅ Focal（软加权）{acc_f:.1%}，几乎不受影响 —— 权重上界是 1，且大量简单样本仍在分母里稀释。')
print('✅ 结论：**数据越脏，越不能硬挖。**「挖多狠」由标注质量决定，不由直觉决定。')"""),

    md("""## 6 · 用损失轨迹（AUM）区分难例与噪声

原理是**记忆化效应的时间不对称性**：干净样本被「学会」（早期就快速下降），
噪声样本被「记住」（**晚得多、也突然得多**）。

$\\text{AUM}_i=\\frac{1}{E}\\sum_t\\big[z_{i,y_i}(t)-\\max_{c\\ne y_i}z_{i,c}(t)\\big]$

下面证明关键的一点：**只看最终 margin 分不开，看整条轨迹分得开。**"""),
    code("""E = 60
tt = np.arange(E) / (E - 1)

def sim_traj(kind, n, r):
    \"\"\"模拟 per-sample 的 margin 轨迹（被指派标签的 logit − 最大其他 logit）。\"\"\"
    if kind == 'easy':      base = -0.5 + 4.5 * (1 - np.exp(-5.0 * tt))
    elif kind == 'hard':    base = -0.8 + 1.8 * (1 - np.exp(-2.5 * tt))
    else:                   # noisy：长期为负（与标签矛盾），只在**末期**被硬记住
        base = -2.2 + 3.2 / (1 + np.exp(-(tt - 0.82) / 0.05))
    offset = r.normal(0, 0.50, (n, 1))              # 样本间差异
    return base[None, :] + offset + r.normal(0, 0.35, (n, E))

r2 = np.random.default_rng(7)
M = {'easy': sim_traj('easy', 1500, r2),
     'hard': sim_traj('hard', 300, r2),
     'noisy': sim_traj('noisy', 200, r2)}

aum   = {kk: v.mean(axis=1) for kk, v in M.items()}      # AUM = 全程 margin 的均值
final = {kk: v[:, -1]       for kk, v in M.items()}      # 只看最后一个 epoch

print(f'{"轨迹片段 (epoch)":<18s}' + ''.join(f'{int(e):>8d}' for e in [0, 10, 25, 40, 50, 59]))
for kk in ['easy', 'hard', 'noisy']:
    print(f'{kk:<18s}' + ''.join(f'{M[kk][:, e].mean():>8.2f}' for e in [0, 10, 25, 40, 50, 59]))

auc_aum   = auc(aum['hard'],   aum['noisy'])         # 越高说明越能把 hard 排在 noisy 之上
auc_final = auc(final['hard'], final['noisy'])
print(f'\\n用 **AUM（整条轨迹均值）** 区分 hard vs noisy 的 AUC = {auc_aum:.3f}')
print(f'用 **最终 margin（只看最后一轮）** 的 AUC        = {auc_final:.3f}   ← 几乎等于瞎猜')
assert auc_aum > 0.90, 'AUM 应能很好地分开难例与噪声'
assert auc_final < 0.70, '最终 margin 分不开（因为噪声样本最终也被记住了）'

thr_aum = np.percentile(np.concatenate(list(aum.values())), 10)   # 取最低 10% 作可疑池
susp = {kk: (v < thr_aum).mean() for kk, v in aum.items()}
print(f'\\nAUM 最低 10% 作为「可疑池」时的命中率：'
      f"noisy {susp['noisy']:.0%} | hard {susp['hard']:.0%} | easy {susp['easy']:.0%}")
assert susp['noisy'] > 0.7 and susp['easy'] < 0.05
print('\\n✅ 工程成本几乎为零：训练时每 epoch 记一个 per-sample margin，100 万样本 × 50 epoch = 200 MB。')
print('⚠️  但注意 AUM 只给「怀疑」，不给「真值」—— 真值只能靠重标注（下一节）。')"""),

    md("""## 7 · 多模型一致性：最锋利的二维判据 + 重标注抽检的样本量

判据：**K 个独立模型高度一致地预测了另一个类** → 强烈怀疑标注错；
**模型之间互相不一致** → 真难例。"""),
    code("""K_MODEL, N_CLS = 5, 8
r3 = np.random.default_rng(11)

def sim_votes(kind, n, label=0):
    \"\"\"K 个独立模型对同一样本的预测类别。\"\"\"
    v = np.empty((n, K_MODEL), dtype=int)
    for i in range(n):
        for m in range(K_MODEL):
            u = r3.random()
            if kind == 'easy':                       # 模型一致且同意标签
                v[i, m] = label if u < 0.97 else r3.integers(1, N_CLS)
            elif kind == 'hard':                     # **模型互相吵架**
                v[i, m] = label if u < 0.45 else (1 if u < 0.725 else 2)
            else:                                    # noisy：模型一致地指向**真类别**(=3)
                v[i, m] = 3 if u < 0.90 else label
    return v

V = {'easy': sim_votes('easy', 1500), 'hard': sim_votes('hard', 300),
     'noisy': sim_votes('noisy', 200)}
LABEL = 0

def vote_stats(votes):
    maj, frac = [], []
    for row in votes:
        c = np.bincount(row, minlength=N_CLS)
        maj.append(int(c.argmax())); frac.append(c.max() / len(row))
    return np.asarray(maj), np.asarray(frac)

def mislabel_flag(votes, label, consensus_thr=0.8):
    maj, frac = vote_stats(votes)
    return (maj != label) & (frac >= consensus_thr)

print(f'{"类型":<10s}{"多数票占比均值":>16s}{"多数票≠标签的比例":>20s}{"被判「疑似标错」":>18s}')
flags = {}
for kk in ['easy', 'hard', 'noisy']:
    maj, frac = vote_stats(V[kk])
    flags[kk] = mislabel_flag(V[kk], LABEL)
    print(f'{kk:<10s}{frac.mean():>15.2f}{(maj != LABEL).mean():>19.0%}{flags[kk].mean():>18.0%}')

tp = int(flags['noisy'].sum())
fp = int(flags['hard'].sum() + flags['easy'].sum())
prec = tp / max(tp + fp, 1); rec = tp / len(flags['noisy'])
print(f'\\n判据 (多数票≠标签 且 一致率≥0.8):  精确率 {prec:.1%}   召回率 {rec:.1%}')
assert rec > 0.80 and prec > 0.80
assert flags['hard'].mean() < 0.15, '真难例（模型互相吵架）不应被误判为标注错误'

# ── 重标注抽检需要多少样本？ ──
def n_for_ci(p, eps, z=1.96):
    return int(np.ceil(z ** 2 * p * (1 - p) / eps ** 2))
print(f'\\n{"待估噪声率 p":>14s}{"目标精度 ±ε":>14s}{"需要抽检样本数":>16s}')
for pp, ee in [(0.10, 0.02), (0.10, 0.01), (0.05, 0.02), (0.20, 0.02)]:
    print(f'{pp:>14.0%}{ee:>14.1%}{n_for_ci(pp, ee):>16d}')
assert n_for_ci(0.10, 0.02) == 865
print('\\n✅ 把噪声率估到 ±2% 只需 ~865 个双标样本 —— 完全负担得起，')
print('   而它换来的是整条挖掘链路的可信度（用来给 AUM / 一致性判据定阈值）。')
print('⚠️  同时要汇报 Cohen\\'s κ：κ < 0.6 说明**标注规范本身有问题**，此时讨论噪声率没有意义。')"""),

    md("""## 8 · 难例池与安全挖掘比例

真实系统不会每步重扫全量数据，而是维护一个**难例池**：EMA loss、老化、过采样封顶、按失效模式分桶。
挖掘比例 $r$ 则由标注质量决定：

$q_{\\text{eff}}=(1-r)q+rqA\\le q_{\\max}\\;\\Longleftrightarrow\\; r\\le\\dfrac{q_{\\max}-q}{q(A-1)}$"""),
    code("""class HardPool:
    \"\"\"难例池：EMA loss + 老化 + 过采样封顶 + 按失效模式分桶配额 + AUM 剔除。\"\"\"
    def __init__(self, decay=0.92, cap=5, max_age=8, bucket_quota=0.30):
        self.d = {}                      # sid -> dict
        self.decay, self.cap = decay, cap
        self.max_age, self.bucket_quota = max_age, bucket_quota

    def update(self, sids, losses, buckets, aums, epoch):
        for s, l, b, a in zip(sids, losses, buckets, aums):
            e = self.d.setdefault(s, {'ema': l, 'n': 0, 'bucket': b, 'aum': a, 'seen': epoch})
            e['ema'] = self.decay * e['ema'] + (1 - self.decay) * l
            e['seen'] = epoch; e['aum'] = a

    def age(self, epoch):
        \"\"\"老化：踢掉长期没被重新评估的样本，避免池变成「化石集合」。\"\"\"
        drop = [s for s, e in self.d.items() if epoch - e['seen'] > self.max_age]
        for s in drop:
            del self.d[s]
        return len(drop)

    def sample(self, m, aum_thr=-np.inf, r=None):
        r = r or np.random.default_rng(0)
        cand = [(s, e) for s, e in self.d.items()
                if e['n'] < self.cap and e['aum'] >= aum_thr]     # 封顶 + 剔除疑似标错
        out, per_bucket = [], {}
        quota = max(1, int(self.bucket_quota * m))
        for s, e in sorted(cand, key=lambda kv: -kv[1]['ema']):
            b = e['bucket']
            if per_bucket.get(b, 0) >= quota:                     # **桶配额**
                continue
            per_bucket[b] = per_bucket.get(b, 0) + 1
            e['n'] += 1; out.append(s)
            if len(out) >= m:
                break
        return out, per_bucket

r4 = np.random.default_rng(3)
pool = HardPool()
BUCKETS = ['night', 'occlusion', 'similar_class', 'small']
sids = np.arange(600)
# 「夜间」桶天然 loss 更高 —— 不设配额就会吃光全部预算
bk = [BUCKETS[i % 4] for i in sids]
ls = np.array([2.6 if b == 'night' else r4.gamma(2.0, 0.35) for b in bk])
au = np.where(r4.random(600) < 0.05, -1.5, r4.normal(0.8, 0.4, 600))   # 5% 疑似标错
pool.update(sids, ls, bk, au, epoch=0)

sel_all, dist = pool.sample(60, r=r4)
print('不剔除疑似标错时，各桶占比:', {k: f'{v/60:.0%}' for k, v in dist.items()})
assert max(dist.values()) <= max(1, int(0.30 * 60)), '桶配额生效：单桶不超过 30%'

pool2 = HardPool(); pool2.update(sids, ls, bk, au, epoch=0)
sel_ok, _ = pool2.sample(60, aum_thr=0.0, r=r4)
bad_in = sum(1 for s in sel_ok if au[s] < 0)
print(f'剔除 AUM<0 后，选中样本里疑似标错的个数 = {bad_in}')
assert bad_in == 0
dropped = pool2.age(epoch=20)          # 池里样本上次评估是 epoch 0，max_age=8 -> 全部老化出局
print(f'老化：把 epoch 推到 20 后被踢出池的样本数 = {dropped}')
assert dropped == 600 and len(pool2.d) == 0, '不做老化的池会变成「化石集合」'

# ── 安全挖掘比例 ──
def safe_mining_ratio(q, A, q_max):
    \"\"\"q: 标注噪声率; A: 噪声放大系数; q_max: 可容忍的有效噪声率。\"\"\"
    if A <= 1.0:
        return 1.0
    if q >= q_max:
        return 0.0
    return float(min(1.0, max(0.0, (q_max - q) / (q * (A - 1.0)))))

print(f'\\n{"噪声率 q":>10s}{"放大系数 A":>13s}{"容忍上限 q_max":>16s}{"安全挖掘比例 r*":>17s}')
for qq, AA, qm in [(0.02, 6.0, 0.15), (0.05, 6.0, 0.15), (0.08, 6.0, 0.15),
                   (0.08, 10.0, 0.15), (0.15, 6.0, 0.15)]:
    print(f'{qq:>10.0%}{AA:>13.1f}{qm:>16.0%}{safe_mining_ratio(qq, AA, qm):>17.1%}')
assert abs(safe_mining_ratio(0.08, 6.0, 0.15) - 0.175) < 1e-9
assert safe_mining_ratio(0.15, 6.0, 0.15) == 0.0
assert safe_mining_ratio(0.02, 1.0, 0.15) == 1.0
print('\\n✅ 「挖多狠」不是玄学：q=2% 的干净数据可以挖到 100%，q=8% 就只能挖 17.5%，')
print('   q≥q_max 时**一点都不能挖**——此时该做的是治理标注质量，不是调采样器。')"""),

    md("""## ✏️ 练习 1：带去重的 OHEM

实现 `ohem_select(boxes, losses, k, iou_thr, min_loss=0.0)`：

1. 先丢掉 `losses < min_loss` 的样本（简单样本没必要进排序）
2. **用 loss 作为分数做一遍 NMS**（阈值 `iou_thr`），去掉空间重复
3. 返回 loss 最高的 k 个的**原始下标**（按 loss 降序）"""),
    code("""def ohem_select(boxes, losses, k, iou_thr=0.7, min_loss=0.0):
    # TODO: ① 按 min_loss 过滤 ② 用 loss 当分数做 NMS ③ 取 top-k，返回**原始下标**
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s = ohem_select(BOXES, LOSS, 128, iou_thr=0.7)
assert len(s) == 128 and len(set(s.tolist())) == 128, '不能有重复下标'
assert np.all(np.diff(LOSS[s]) <= 1e-12), '必须按 loss 降序返回'
nreg = len(np.unique(REGION[s]))
assert nreg >= 60, f'去重后应覆盖大量不同区域，实际 {nreg}'
assert np.array_equal(s, ohem(BOXES, LOSS, 128, dedup_iou=0.7)), '应与参考实现一致'
s2 = ohem_select(BOXES, LOSS, 10**9, iou_thr=0.7, min_loss=1.5)
assert LOSS[s2].min() >= 1.5, 'min_loss 过滤未生效'
assert len(s2) <= 40, '只有 8 个热点区域，去重后剩余应很少'
print(f'top-128 覆盖 {nreg} 个不同区域；min_loss=1.5 且去重后只剩 {len(s2)} 个候选')
print('✅ 练习 1 通过：**先 NMS 再 top-k** —— OHEM 的成败就在这一行')"""),

    md("""## ✏️ 练习 2：Focal ↔ OHEM 的换算

实现两个函数：
- `focal_weights(p_t, gamma, alpha=None)`：返回 `(1-p_t)^gamma`；若给了 `alpha` 则再乘上 `alpha`
- `equivalent_k(p_t, gamma)`：返回该 γ 下的**有效样本数**（四舍五入取整），即「等价的 OHEM k」"""),
    code("""def focal_weights(p_t, gamma, alpha=None):
    # TODO
    raise NotImplementedError

def equivalent_k(p_t, gamma):
    # TODO: 用 n_eff(w) = (Σw)² / Σw²
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
pt = rng.beta(9.0, 1.0, 20000)
assert np.allclose(focal_weights(np.array([0.5]), 2.0), np.array([0.25]))
assert np.allclose(focal_weights(np.array([0.5]), 2.0, alpha=0.25), np.array([0.0625]))
assert equivalent_k(pt, 0.0) == len(pt), 'γ=0 退化为 CE，等价 k = N'
ks = [equivalent_k(pt, g) for g in [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]]
assert all(a > b for a, b in zip(ks, ks[1:])), 'γ 越大等价 k 越小'
assert equivalent_k(pt, 2.0) < 0.5 * len(pt)
# alpha 是常数缩放，**不改变有效样本数**（这是 α 与 γ 分工不同的数学体现）
w1, w2 = focal_weights(pt, 2.0), focal_weights(pt, 2.0, alpha=0.25)
assert abs(n_eff(w1) - n_eff(w2)) < 1e-6, 'α 只缩放整体幅值，不改变权重分布形状'
for g, kk in zip([0.0, 0.5, 1.0, 2.0, 3.0, 5.0], ks):
    print(f'γ={g:<4.1f} -> 等价 OHEM k = {kk:>6d}  ({kk/len(pt):.1%} 的样本在真正贡献梯度)')
print('✅ 练习 2 通过：γ 不是玄学 —— 它等价于一个 top-k，且 α 不参与这件事')"""),

    md("""## ✏️ 练习 3：区分难例与噪声标签

实现 `triage(margins, votes, labels, susp_pct=10.0, consensus_thr=0.8)`，
对每个样本返回三种标签之一：

- `'mislabeled'`：AUM 在最低 `susp_pct` 百分位 **且** 多模型一致地投给了另一个类
- `'hard'`：AUM 在最低 `susp_pct` 百分位，但模型之间**不一致**（一致率 < `consensus_thr`）
- `'ok'`：其余

`margins` 形状 `(N, E)`，`votes` 形状 `(N, K)`，`labels` 形状 `(N,)`。"""),
    code("""def triage(margins, votes, labels, susp_pct=10.0, consensus_thr=0.8):
    # TODO: ① AUM = margins.mean(axis=1) ② 低分位阈值 ③ 多数票与一致率 ④ 三分类
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
Mall = np.vstack([M['easy'], M['hard'], M['noisy']])
Vall = np.vstack([V['easy'], V['hard'], V['noisy']])
Lall = np.zeros(len(Mall), dtype=int)
truth = np.array(['easy'] * 1500 + ['hard'] * 300 + ['noisy'] * 200)
tag = triage(Mall, Vall, Lall, susp_pct=15.0)
assert set(np.unique(tag)) <= {'mislabeled', 'hard', 'ok'}
rec_mis = (tag[truth == 'noisy'] == 'mislabeled').mean()
fp_easy = (tag[truth == 'easy'] == 'mislabeled').mean()
rec_hard = (tag[truth == 'hard'] == 'hard').mean()
print(f'{"真值":<10s}{"判为 mislabeled":>18s}{"判为 hard":>12s}{"判为 ok":>10s}')
for t in ['easy', 'hard', 'noisy']:
    sub = tag[truth == t]
    print(f'{t:<10s}{(sub=="mislabeled").mean():>17.0%}{(sub=="hard").mean():>12.0%}{(sub=="ok").mean():>10.0%}')
assert rec_mis > 0.60, f'噪声样本召回过低: {rec_mis:.2f}'
assert fp_easy < 0.03, f'简单样本不应被判为标注错误: {fp_easy:.3f}'
assert rec_hard > 0.15, '部分真难例应被识别为 hard 而不是 mislabeled'
print('✅ 练习 3 通过：**轨迹（AUM）给可疑度，一致性给「是错还是难」** —— 两个维度缺一不可')"""),

    md("""## ✏️ 练习 4：安全挖掘比例与总放大倍数封顶

实现 `mining_plan(q, A, q_max, repeat_factor, amp_cap)`，返回 dict：

- `'r'`：安全挖掘比例（第 8 节的公式，结果裁剪到 `[0, 1]`；`A<=1` 时为 1.0；`q>=q_max` 时为 0.0）
- `'total_amp'`：稀有类样本的**总放大倍数** = `repeat_factor × (1 + r*(A-1))`
- `'ok'`：`total_amp <= amp_cap` 时为 True

（`1 + r(A-1)` 就是「一个噪声/难样本在混合批里相对原始频率的期望放大倍数」。）"""),
    code("""def mining_plan(q, A, q_max, repeat_factor=1.0, amp_cap=10.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
p1 = mining_plan(0.08, 6.0, 0.15)
assert abs(p1['r'] - 0.175) < 1e-9
assert abs(p1['total_amp'] - (1 + 0.175 * 5)) < 1e-9 and p1['ok']
assert mining_plan(0.15, 6.0, 0.15)['r'] == 0.0
assert mining_plan(0.02, 1.0, 0.15)['r'] == 1.0
# 与模块 01 的 repeat factor sampling 叠加 -> 总放大倍数可能爆掉
p2 = mining_plan(0.02, 8.0, 0.20, repeat_factor=6.0, amp_cap=10.0)
assert not p2['ok'], '重采样 6× 叠加激进挖掘应触发封顶告警'
print(f'{"场景":<34s}{"r":>8s}{"总放大":>10s}{"ok":>6s}')
for name, kw in [('干净数据、无重采样', dict(q=0.02, A=6.0, q_max=0.15)),
                 ('脏数据、无重采样', dict(q=0.08, A=6.0, q_max=0.15)),
                 ('干净数据 + 稀有类 6× 重采样', dict(q=0.02, A=8.0, q_max=0.20, repeat_factor=6.0)),
                 ('脏数据 + 稀有类 6× 重采样', dict(q=0.08, A=8.0, q_max=0.15, repeat_factor=6.0))]:
    pl = mining_plan(**kw)
    print(f'{name:<32s}{pl["r"]:>8.1%}{pl["total_amp"]:>10.2f}{("✅" if pl["ok"] else "❌"):>6s}')
print('✅ 练习 4 通过：**长尾重采样 × 难例挖掘会互相放大** —— 要给「总放大倍数」显式封顶')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def ohem_select(boxes, losses, k, iou_thr=0.7, min_loss=0.0):
    cand = np.where(losses >= min_loss)[0]              # ① 过滤简单样本
    if cand.size == 0:
        return cand
    keep_local = nms(boxes[cand], losses[cand], iou_thr) # ② 用 loss 当分数做 NMS
    return cand[keep_local][:k]                          # ③ 取 top-k（nms 已按 loss 降序）"""),
    code("""# 练习 2 参考答案
def focal_weights(p_t, gamma, alpha=None):
    w = (1.0 - np.asarray(p_t, dtype=float)) ** gamma
    return w if alpha is None else alpha * w

def equivalent_k(p_t, gamma):
    w = focal_weights(p_t, gamma)
    return int(round(w.sum() ** 2 / (w ** 2).sum()))"""),
    code("""# 练习 3 参考答案
def triage(margins, votes, labels, susp_pct=10.0, consensus_thr=0.8):
    aum_ = np.asarray(margins, dtype=float).mean(axis=1)
    thr = np.percentile(aum_, susp_pct)
    n_cls = int(max(votes.max(), labels.max())) + 1
    out = np.full(len(aum_), 'ok', dtype=object)
    for i in range(len(aum_)):
        if aum_[i] > thr:
            continue
        c = np.bincount(votes[i], minlength=n_cls)
        maj, frac = int(c.argmax()), c.max() / votes.shape[1]
        if maj != labels[i] and frac >= consensus_thr:
            out[i] = 'mislabeled'          # 模型一致地指向另一个类 -> 强烈怀疑标错
        elif frac < consensus_thr:
            out[i] = 'hard'                # 模型互相吵架 -> 真难例
    return out"""),
    code("""# 练习 4 参考答案
def mining_plan(q, A, q_max, repeat_factor=1.0, amp_cap=10.0):
    if A <= 1.0:
        r = 1.0
    elif q >= q_max:
        r = 0.0
    else:
        r = min(1.0, max(0.0, (q_max - q) / (q * (A - 1.0))))
    total = repeat_factor * (1.0 + r * (A - 1.0))
    return {'r': r, 'total_amp': total, 'ok': total <= amp_cap}"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接抄进项目的难例挖掘配置与自检清单"""),
    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# 难例挖掘 · 生产配置模板（mmdet / 自研训练框架通用）
# ══════════════════════════════════════════════════════════════════

# ── ① 选 OHEM 还是 Focal ───────────────────────────────────────────
#  密集单阶段检测器（YOLO / RetinaNet / RTMDet） -> **Focal**（无需排序，可向量化）
#  两阶段第二阶段（Fast R-CNN head）              -> **OHEM**（RPN 已粗筛，focal 收益很小）
#  ⚠️ 两者**不要同时开**：等效样本量被平方级压缩，训练必然不稳。

sampler = dict(
    type="OHEMSampler",
    num=512, pos_fraction=0.25,      # ② **正负分开挖**，维持 1:3
    dedup_nms_iou=0.7,               # ③ **先用 loss 当分数做 NMS —— 缺这行 OHEM 会失效**
    loss_normalizer="num_selected",  # ④ 除以 k 而不是 N（否则等于偷偷降 lr）
    warmup_iters=1000,               # ⑤ warmup 期均匀采样（初期 loss 排序 = 随机排序）
)
loss_cls = dict(type="FocalLoss", gamma=2.0, alpha=0.25)
#   γ=2 在典型分布下 ≈ 只让 20% 左右的样本真正贡献梯度（用 n_eff=(Σw)²/Σw² 核算）
#   α 只平衡前景-背景，**不解决类别长尾**（那是 EQL / CB-Loss / logit adjustment 的活）

# ── ⑥ 挖掘比例的安全上界（由标注质量决定，不是拍脑袋）────────────────
#   q      = 标注噪声率（**必须靠重标注抽检得到**，~865 样本可估到 ±2%）
#   A      = 噪声放大系数 = P(noisy|selected)/P(noisy)（在自己数据上实测，常见 4–10）
#   r <= (q_max - q) / (q * (A - 1))
#   例: q=8%, A=6, q_max=15%  ->  r <= 17.5%   （**不是 100%**）

# ── ⑦ 训练时**免费**记录 AUM（强烈建议默认开启）──────────────────────
#   每个 epoch 存一次 per-sample margin = z[y] - max(z[c!=y])
#   100 万样本 × 50 epoch × float32 = 200 MB
#   AUM 最低 2–5% 进「可疑池」-> 用多模型一致性二次判别 -> 抽样重标验收
aum_log = dict(enable=True, every_n_epochs=1, out="aum_margins.npy")

# ── ⑧ 可疑样本：**降权而不是删除** ─────────────────────────────────
#   删除的风险是删掉真难例（最宝贵）且悄悄改变数据分布
per_sample_weight = dict(suspicious=0.2, normal=1.0)

# ── ⑨ 难负样本入库前的「可分性检查」───────────────────────────────
#   把 crop 单独给人看：**仅凭这块图像**能否判断它不是标志？
#   不能 -> 它不该做检测端的难负样本，而应作为下游（车道关联/跟踪）的测试用例
#   ⚠️ TSR 里最致命的错误：把**漏标的真标志**当难负样本 = 主动教模型漏检

# ── ⑩ 与长尾重采样的交互：给总放大倍数封顶 ───────────────────────────
#   total_amp = repeat_factor(类别) × (1 + r*(A-1))   <= 10
#   症状：稀有类训练 loss 极低但验证召回不涨 = 纯粹过拟合了那几十个样本

# ── 上线前自检清单 ────────────────────────────────────────────────
#   [ ] OHEM 里有 NMS 去重吗？（打印 top-k 覆盖的不同区域数，应 >= 0.5*k）
#   [ ] 正负分开挖了吗？（打印 top-k 里的正样本数，不能为 0）
#   [ ] warmup 期关掉挖掘了吗？
#   [ ] 噪声率 q 是**测出来的**还是猜的？
#   [ ] 挖掘比例 r 满足安全上界吗？
#   [ ] AUM 记录开了吗？可疑池是降权还是删除？
#   [ ] 难负样本库里有没有混进漏标的真目标？（抽 100 个人工过一遍）
'''
print(RECIPE)
for key in ['dedup_nms_iou', 'pos_fraction', 'num_selected', 'warmup_iters',
            'FocalLoss', 'aum_log', 'suspicious', 'total_amp', '可分性检查']:
    assert key in RECIPE, key
print('✅ 配方覆盖：算法选型 / 四个实现细节 / 安全比例 / AUM / 降权 / 可分性检查 / 总放大封顶')"""),

    md("""### 小结

- **难例挖掘解决的是「梯度预算分配」**：98% 的 anchor 梯度只有 1e-3 量级，一个 s=0.8 的难负样本
  抵得上 800 个简单负样本。三代方法（bootstrapping → OHEM → Focal）是同一思想在数据/采样/损失
  三个层面的实现。
- **OHEM 的成败在「先用 loss 当分数做一遍 NMS」**：不去重时 128 个样本其实是 2–4 件事的拷贝，
  有效 batch ≈ 3，**比不做 OHEM 更差**。另外三条细节：正负分开挖、除以 k 而不是 N、warmup 期不挖。
- **Focal Loss 是软性 OHEM**：都能写成 `Σ w(ℓ)·ℓ`；**排序完全一致**（focal 权重与 CE 都是 p_t 的
  单调减函数）；差别只在被排除样本的权重是 0 还是 ε。用 `n_eff=(Σw)²/Σw²` 可把 γ 翻译成等价的 k。
  **两阶段检测器上 focal 收益小，因为 RPN 已经把前景背景比粗筛到 1:3。**
- **难例有四类，只有前三类值得挖**：相似类混淆 / 背景误检 / 边界样本 / **标注错误**。
  而 loss 排序把它们混在一起，且**挖得越狠，第四类占比越高**（噪声放大系数 A 常在 4–10）。
- **挖掘过头会毁掉模型**：噪声样本的 loss 永远最高 → 每轮都被选中 → 梯度预算被它们吃掉 →
  加速记忆化 → 泛化崩坏。而验证集同源同噪，**离线指标看不出来**。
  安全上界：`r ≤ (q_max − q) / (q(A−1))`。
- **区分难例与噪声的三件套**：**AUM/损失轨迹**（几乎零成本，默认开；只看最终 loss 分不开，
  看整条轨迹分得开）+ **多模型一致性**（一致地指向另一个类 = 疑似标错；互相吵架 = 真难例）
  + **重标注抽检**（~865 样本可把噪声率估到 ±2%，这是唯一的真值来源）。
- **可疑样本默认降权而不是删除**，因为误删的可能是最宝贵的真难例；也因为降权可逆、不改变分布。
- **TSR 落地**：难负样本要过「可分性检查」；**漏标的真标志伪装成 FP** 是最致命的陷阱
  （当负样本训练 = 主动教模型漏检）；难例池要按失效模式分桶并给每桶配额。

下一站：**模块 03 · 主动学习与线上触发策略** —— 车队数据无限、标注预算有限，
问题从「怎么挖」变成「**回传什么**」。"""),
]
