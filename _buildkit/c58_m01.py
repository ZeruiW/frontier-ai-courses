# -*- coding: utf-8 -*-
"""C58 模块 01 · 类别不平衡的处理谱系。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00；C18（检测基础）与 C55 m01（标志分类体系）有帮助；懂 softmax/sigmoid 交叉熵即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_class_imbalance.ipynb'),
    ("核心参考", "LVIS (CVPR 2019)、Class-Balanced Loss (CVPR 2019)、LDAM-DRW (NeurIPS 2019)、EQL/EQLv2 (CVPR 2020/2021)、Logit Adjustment (ICLR 2021)、Decoupling (ICLR 2020)"),
    ("预计时长", "读 70 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("two_kinds", "先分清：检测里有两种完全不同的不平衡", "".join([
        P("「长尾怎么办」这个问题之所以能筛掉大多数候选人，第一关就卡在这里：<strong>检测任务里同时存在两种性质完全不同的不平衡，它们的成因、症状、解法都不一样，而且互不替代。</strong>混为一谈，后面所有方法的选择都会错。"),
        TABLE(["", "<strong>前景-背景不平衡</strong>", "<strong>类别间（长尾）不平衡</strong>"], [
            ["层级", "<strong>位置级</strong>（anchor / grid cell / query）", "<strong>数据集级</strong>（跨图统计实例数）"],
            ["典型比例", "1 : 300 ~ 1 : 10000（每张图都是）", "1 : 100 ~ 1 : 10000（头部类 vs 尾部类）"],
            ["是否与类别有关", "<strong>无关</strong>——只有两类：是目标 / 不是目标", "<strong>核心就是类别</strong>"],
            ["每张图都存在吗", "是。哪怕数据集完全平衡也存在", "否。它是数据集统计属性，单张图看不出来"],
            ["主要症状", "训练早期被背景主导，loss 被背景吃掉；分类头输出全是背景", "尾部类 AP 接近 0；macro 与 micro 指标严重背离"],
            ["主流解法", "采样（RPN 1:3、OHEM）、<strong>Focal Loss</strong>、标签分配（一对一天然正样本少但比例可控）", "重采样（RFS）、重加权（CB Loss/LDAM）、<strong>EQL/EQLv2</strong>、<strong>logit adjustment</strong>、<strong>解耦训练</strong>"],
        ]),
        P("把数字落实一下。一张 640×640 的图，anchor-free 检测器在 P3–P5 三层上一共约 <strong>8400 个预测位置</strong>；一张典型的 TSR 图像里有 1–5 个交通标志，标签分配给出 3–30 个正样本。<strong>正负比大约 1:280 到 1:2800</strong>。这就是前景-背景不平衡，与「限速 40 有 12 万实例、注意落石只有 30 个」没有任何关系。"),
        ASCII("""① 前景-背景不平衡（**位置级**，每张图都有）
   一张 640×640 图 → 8400 个预测位置
   ┌────────────────────────────────────────────────┐
   │ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ │  ■ = 背景位置 ≈ 8380
   │ ■ ■ ■ ■ ● ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ● ■ ■ ■ ■ ■ ■ ■ │  ● = 正样本   ≈ 20
   │ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ │
   └────────────────────────────────────────────────┘
   → Focal Loss / OHEM / 采样比例。**与类别无关。**

② 类别间不平衡（**数据集级**，跨图统计）
   实例数
   80000 ┤██  限速40
         │██
   20000 ┤██ ██  禁止停车
         │██ ██ ██
     500 ┤██ ██ ██ ██ ██ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁ ▁▁
      30 ┤                                        ▁ 注意落石 / 注意牲畜 / 事故易发
         └──────────────────────────────────────────────→ 类别（按频次排序）
   → RFS / CB Loss / LDAM / EQLv2 / logit adjustment / 解耦。**与位置无关。**"""),
        CALLOUT("danger", "<p><strong>面试高频陷阱：问「长尾怎么办」，答「用 Focal Loss」——这是把两个问题混为一谈，会被当场追问到崩。</strong></p><p>Focal Loss 的权重是 <code>(1−p_t)^γ</code>，它按<em>样本难度</em>加权，<strong>完全不看类别频率</strong>。头部类里也有难样本（被遮挡的限速 40），尾部类里也有易样本（画面正中的大号警告牌）。所以 Focal Loss 解决的是「大量简单背景淹没损失」，对「限速 40 有 12 万个而注意落石只有 30 个」这件事几乎无能为力。原论文的实验也是在 COCO（类别相对平衡）上做的。<em>能主动指出这一点，比会背 Focal Loss 公式有价值得多。</em></p>", "Focal Loss 不是长尾解法"),
        DUAL(
            "两种不平衡还有一个关键的<strong>耦合点</strong>：在 sigmoid 多标签检测头里，「背景位置对某个类别的负梯度」与「其他类别的正样本对这个类别的负梯度」是<em>同一种东西</em>——都是 <code>y=0</code> 的 BCE 项。于是前景-背景不平衡的量级（1:2800）会<strong>乘上</strong>类别间不平衡的量级，稀有类的正负梯度比可以低到 <code>1 : 10^5</code>。这正是第 4 节 EQL 要解决的问题，也是<strong>检测的长尾比分类的长尾更难</strong>的技术原因。",
            "还有第三种常被忽略的不平衡：<strong>尺度/难度不平衡</strong>（小目标的正样本天然更稀缺，因为 IoU 阈值对小框极不友好——8×8 的框位移 2 px，IoU 就从 1.0 掉到 0.39）。它属于 C57 的范畴，但在 TSR 里与类别长尾<em>高度纠缠</em>：稀有标志往往也是远处的小标志（稀有 → 采集机会少 → 只在远景里偶然拍到过几次）。<strong>做误差分析时必须按「类别频率 × 像素尺寸」双向分桶</strong>，否则你会把小目标问题误诊成长尾问题，然后用重采样去治，白忙一场。",
        ),
    ])),

    ("resample", "重采样：让稀有类多出现几次", "".join([
        P("最直接的想法：稀有类样本少，那就让它在每个 epoch 里多出现几次。但在<strong>检测</strong>里这件事比分类难，难在一个结构性事实上——<strong>采样的单位是图像，而一张图里可能同时含有头部类和尾部类</strong>。"),
        DUAL(
            "分类任务里，「按类别平衡采样」是干净的：每个样本恰好一个标签，想让每类等频率就按 <code>1/f_c</code> 采。检测里做不到——你为了多看一次「注意落石」而重复了那张图，图里的三块「限速 40」也跟着被重复了。<em>所以检测的重采样只能是「图像级的近似」，永远无法做到类别精确平衡。</em>",
            "更麻烦的是，朴素的 <code>1/f_c</code> 采样会把只有 8 张图的类别重复几百次。模型看到的不是「更多的注意落石」，而是<strong>同样 8 张图的第 300 遍</strong>——它会把这 8 张图的<em>背景</em>、光照、拍摄角度一起背下来。这就是重采样的过拟合风险：<strong>重采样增加的是「看到的次数」，不是「信息量」</strong>。30 张图重复 100 次 ≠ 3000 张图。",
        ),
        H3("Repeat Factor Sampling（RFS）：LVIS 的做法"),
        P("LVIS 提出的 <span class=\"term\">repeat factor sampling</span> 是目前检测长尾里<strong>最常用、最先该试的重采样方法</strong>（mmdet 里就是 <code>ClassBalancedDataset</code>）。它分三步："),
        MATH(r"r_c \;=\; \max\!\left(1,\ \sqrt{\frac{t}{f_c}}\right) \qquad\quad r_i \;=\; \max_{c \,\in\, i} r_c \qquad\quad \hat r_i \;=\; \lfloor r_i \rfloor + \mathbb{1}\!\left[u < r_i - \lfloor r_i \rfloor\right],\ \ u \sim U(0,1)"),
        OL([
            "<strong>类别级 repeat factor</strong> <code>r_c = max(1, √(t/f_c))</code>。<strong><code>f_c</code> 是「包含类别 c 的图像数 ÷ 数据集总图像数」，即<em>图像频率</em>，不是实例数占比</strong>——这个细节面试会问，因为采样的单位是图像。<code>t</code> 是阈值超参（LVIS 用 <code>t = 0.001</code>）：<em>频率高于 t 的类完全不重复</em>。",
            "<strong>图像级 repeat factor</strong> <code>r_i = max_{c ∈ i} r_c</code>——<strong>取最大值而不是平均</strong>。理由：一张图里只要含有任何一个稀有类，这张图就值得被重复；取平均会被图里的常见类稀释掉。",
            "<strong>随机取整</strong>：每个 epoch 开始时，整数部分确定重复，小数部分用伯努利采样决定要不要多来一次。<em>这样期望重复次数正好是 <code>r_i</code>，而且每个 epoch 的重复集合都不同，缓解了固定重复带来的过拟合。</em>",
        ]),
        P("<strong>为什么是平方根，而不是 <code>t/f_c</code>？</strong>这是 RFS 最值得讲的一个设计。<code>1/f_c</code> 会把分布<em>完全拉平</em>到均匀，尾部类的重复倍数直接爆炸（<code>f_c = 1e-5</code> 时重复 10 万次）。平方根相当于在「原始分布」和「均匀分布」之间做<strong>几何插值（指数 0.5）</strong>：既显著抬高尾部，又不至于把 8 张图重复到模型背下来。<em>换句话说，√ 是「过采样强度」这个连续旋钮上一个经验上很好的取值</em>——你完全可以把它换成 <code>(t/f_c)^p</code> 并把 <code>p</code> 当超参调（p=0 不重采样，p=1 完全拉平）。"),
        TABLE(["方案", "尾部重复倍数（f_c=1e-4, t=1e-3）", "过拟合风险", "评价"], [
            ["不重采样", "1×", "无", "尾部类一个 epoch 出现不到一次，学不到"],
            ["<code>1/f_c</code> 完全拉平", "<strong>10 倍于 √ 的量级</strong>（此例 10×→ 但对更稀有的类会到 10³×）", "<strong>极高</strong>", "模型背下尾部类那几张图的背景"],
            ["<strong>RFS <code>√(t/f_c)</code></strong>", "<strong>3.2×</strong>", "中", "<strong>检测长尾的默认起点</strong>"],
            ["RFS + 上界裁剪", "min(3.2×, cap)", "低", "工程上常见的加固：给 r 设上界（如 6）防极端类"],
        ]),
        CALLOUT("warn", "RFS 有两个必须知道的副作用。<strong>① 共现污染</strong>：因为 <code>r_i</code> 取图内最大值，与稀有类经常共现的常见类会被顺带过采样。在 TSR 里这很典型——「注意落石」几乎总和「限速」牌一起出现在山区路段，于是山区的限速牌被过采了一大堆，而城市的限速牌相对被稀释了。<strong>② epoch 长度变化</strong>：重采样后一个 epoch 的迭代数变多（LVIS 上典型 1.5–2×），<em>如果你不同步调整学习率调度和总 iteration，就等于偷偷给重采样组多训了一倍——这是消融实验里最常见的不公平对比</em>。"),
        CALLOUT("intuition", "一句话记住 RFS：<strong>它只回答「每张图该被看几遍」，用的是图像频率、开方、取图内最大、每 epoch 随机取整。</strong>能把这四个设计点逐个说出理由，就说明你读过原文而不是只用过 config。"),
    ])),

    ("reweight", "重加权：不改采样，改损失的权重", "".join([
        P("重采样改的是「数据出现的频率」，重加权改的是「同一份数据在损失里的分量」。两者在理论上有相似的效果，但工程性质差别很大：<strong>重加权不改变 epoch 长度、不制造重复样本、也不会有共现污染</strong>，代价是它对<em>极端</em>不平衡更容易训崩。"),
        H3("① 朴素反频率加权：为什么不能直接用"),
        P("最朴素的做法是 <code>w_c ∝ 1/n_c</code>。它在 <code>n_c = 8</code> 的类上给出比头部类大 <strong>一万倍</strong>的权重，于是一个 batch 里只要出现一个尾部样本，梯度就被它主导，<em>梯度方差爆炸、训练震荡甚至发散</em>。实践中要么加温度 <code>w_c ∝ n_c^{-p}</code>（p=0.5 常用），要么用下面两个更有原则的方案。"),
        H3("② Class-Balanced Loss：有效样本数"),
        P("<span class=\"term\">Class-Balanced Loss</span>（Cui et al., CVPR 2019）的洞察是：<strong>同一类的样本之间存在信息重叠，第 n 个样本带来的边际信息量随 n 递减</strong>。作者用一个简单的覆盖模型形式化它——假设每个新样本有 <code>β</code> 的概率落进已经被覆盖的区域，则 n 个样本的「有效样本数」满足递推 <code>E_n = 1 + β·E_{n−1}</code>，<code>E_1 = 1</code>，解得："),
        MATH(r"E_n \;=\; \frac{1-\beta^{\,n}}{1-\beta}, \qquad w_c \;\propto\; \frac{1}{E_{n_c}} \;=\; \frac{1-\beta}{1-\beta^{\,n_c}}, \qquad \beta \in [0,1)"),
        P("这个公式的价值在于它的<strong>两个极限</strong>："),
        UL([
            "<code>β → 0</code>：<code>E_n → 1</code>，所有类权重相同——<strong>等价于不加权</strong>（假设样本完全冗余）。",
            "<code>β → 1</code>：<code>E_n → n</code>，<code>w_c ∝ 1/n_c</code>——<strong>等价于朴素反频率</strong>（假设样本完全不重叠）。",
        ]),
        P("<strong>所以 β 是一个把「不加权」与「反频率」连成一条连续曲线的旋钮</strong>，而不是二选一。典型取值 <code>β ∈ {0.99, 0.999, 0.9999}</code>；直觉上 <code>1/(1−β)</code> 就是「一个类大约需要多少样本才饱和」——β=0.999 意味着假定约 1000 个样本后边际信息趋零，这与前一模块的边际收益曲线是同一个思想的两种写法。<em>β 该怎么选？看你的头部类样本数：如果头部类有 10 万个而 1/(1−β)=1000，那么头部类被视为「早已饱和」，权重被压得很低。</em>"),
        H3("③ LDAM：不改权重，改间隔"),
        P("<span class=\"term\">LDAM</span>（Label-Distribution-Aware Margin, Cao et al., NeurIPS 2019）走的是另一条路：<strong>稀有类的问题是决策边界离它太近，泛化间隔不够</strong>，所以给稀有类一个更大的分类间隔："),
        MATH(r"\mathcal{L}_{\mathrm{LDAM}} = -\log \frac{e^{\,z_y - \Delta_y}}{e^{\,z_y - \Delta_y} + \sum_{j \neq y} e^{\,z_j}}, \qquad \Delta_c = \frac{C}{n_c^{1/4}}"),
        P("<code>Δ_c ∝ n_c^{−1/4}</code> 这个指数不是拍脑袋的——它来自泛化误差界的优化：在「间隔之和固定」的约束下最小化各类泛化界，最优解就是 <code>n_c^{−1/4}</code>。<strong>LDAM 的实际效果高度依赖它的搭档 DRW（deferred re-weighting）</strong>：前若干 epoch 完全不加权地训练，到学习率第一次衰减时才开启重加权。<em>这个「先按原分布学、后期再平衡」的两段式，已经是下一节要讲的「解耦训练」的雏形</em>——作者当时给的解释是「先学好表示，再调决策边界」，而这正是 Kang 等人后来系统验证的结论。"),
        TABLE(["方法", "改什么", "关键超参", "适用", "失效场景"], [
            ["<strong>Focal Loss</strong>", "按样本难度 <code>(1−p_t)^γ</code> 加权", "γ=2, α=0.25", "<strong>前景-背景不平衡</strong>", "<strong>对类别间长尾几乎无效</strong>；标注有噪时会放大噪声（噪声样本永远是「难例」）"],
            ["<strong>反频率</strong>", "<code>w_c ∝ 1/n_c</code>", "无", "轻度不平衡（<20×）", "极端不平衡下梯度爆炸、训练发散"],
            ["<strong>CB Loss</strong>", "<code>w_c ∝ (1−β)/(1−β^{n_c})</code>", "<strong>β</strong>（0.99~0.9999）", "分类；检测里也常用", "β 选错等于回退到「不加权」或「反频率」两个极端"],
            ["<strong>LDAM(+DRW)</strong>", "给稀有类更大 margin <code>Δ_c ∝ n_c^{−1/4}</code>", "C（max margin）、DRW 起点", "softmax 多分类", "<strong>sigmoid 多标签检测头上不直接适用</strong>；单独用不加 DRW 收益有限"],
        ]),
        CALLOUT("warn", "一个真实的坑：<strong>Focal Loss 与标注噪声是反向作用的</strong>。Focal 给「模型觉得难」的样本更大权重，而<em>标注错误的样本对模型来说永远是最难的</em>——它会被持续放大。所以在标注质量不高的数据上（比如众包标的小目标 TSR 数据），γ 调大反而掉点。<em>这是模块 02「挖掘过头会把噪声当难例」那条主线的第一次出现。</em>"),
    ])),

    ("eql", "EQL / EQLv2：稀有类是被负梯度淹死的", "".join([
        P("这一节是本模块最该讲透的地方，因为它是<strong>检测特有</strong>的机制，也是「长尾在检测里为什么比在分类里更难」的直接答案。<strong>面试里能说清这一段的人极少。</strong>"),
        H3("机制：负梯度的量级差"),
        P("现代检测器的分类头几乎都用 <strong>sigmoid 多标签</strong>（每个类一个独立的二分类），而不是 softmax。对某一个类别 <code>j</code> 而言，一个 batch 里的样本被分成两拨："),
        UL([
            "<strong>正梯度</strong>：来自真实标签是 <code>j</code> 的候选框。BCE 的梯度是 <code>σ(z_j) − 1 < 0</code>，把 <code>z_j</code> <em>推高</em>。",
            "<strong>负梯度</strong>：来自所有<em>其他</em>候选框——包括背景位置，<strong>也包括所有其他前景类的正样本</strong>。梯度是 <code>σ(z_j) > 0</code>，把 <code>z_j</code> <em>压低</em>。",
        ]),
        P("现在算账。一张图 8400 个位置，其中约 20 个正样本。对头部类「限速 40」，一个 batch 里可能有 15 个它的正样本、8385 个负样本，正负梯度比约 <strong>1 : 560</strong>——不好，但还能训。对尾部类「注意落石」，它<em>在 500 个 batch 里才出现一次</em>，而每个 batch 的 8400 个位置都在对它施加负梯度。累积下来正负梯度比可以低到 <strong>1 : 10⁵ 甚至 1 : 10⁶</strong>。"),
        ASCII("""对类别 j 的梯度流（sigmoid 多标签头，累积一个训练周期）

  头部类「限速40」                          尾部类「注意落石」
  ┌──────────────────────────┐             ┌──────────────────────────┐
  │ 正梯度 ↑↑↑↑↑↑↑↑ (推高)   │             │ 正梯度 ↑    (推高)       │
  │ 负梯度 ↓↓↓↓↓↓↓↓↓↓↓↓↓↓    │             │ 负梯度 ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ │
  │        ~1 : 560          │             │        **~1 : 10^5**     │
  └──────────────────────────┘             └──────────────────────────┘
            │                                          │
            ▼                                          ▼
     z_j 稳定在合理区间                    **z_j 被持续压向 -∞**
     σ(z_j) 峰值 0.85                       σ(z_j) 峰值 0.03
            │                                          │
            ▼                                          ▼
     score 0.85 > 阈值 0.3 ✅          score 0.03 < 阈值 0.3 ❌ 被过滤掉
                                       → **框定位得很准，但根本输不出来**

  诊断指纹：把各类分类器权重范数 ||w_c|| 画出来 → 与 log(n_c) 强正相关。
            尾部类的 ||w_c|| 只有头部类的几分之一。"""),
        CALLOUT("intuition", "<strong>把这句话背下来：稀有类的问题往往不是「特征学不好」，而是「分类器的 logit 被海量负梯度压死了」。</strong>证据是：把同一个模型的特征拿出来做最近类均值（NCM）分类，尾部类的准确率会显著高于模型自己的分类头给出的结果——<em>说明表示是好的，坏掉的是最后那一层</em>。这一句能同时串起 EQL、logit adjustment 和解耦训练三节内容，是本模块的枢纽。"),
        H3("EQL v1：屏蔽来自更常见类的负梯度"),
        P("<span class=\"term\">Equalization Loss</span>（Tan et al., CVPR 2020）的做法很直接：<strong>当一个候选框属于某个比 j 更常见的前景类时，屏蔽掉它对 j 的负梯度</strong>。形式上给 BCE 的负样本项乘一个权重："),
        MATH(r"w_j \;=\; 1 - \beta\,T_\lambda(f_j)\,(1-y_j), \qquad T_\lambda(f_j)=\mathbb{1}[f_j<\lambda], \qquad \beta \sim \mathrm{Bernoulli}(p)"),
        P("解读：<code>T_λ(f_j)=1</code> 表示 j 是稀有类（图像频率低于 λ）；<code>(1−y_j)</code> 表示这是个负样本项；<code>β</code> 是一个伯努利随机量，作用是<strong>只屏蔽一部分负梯度</strong>——因为完全屏蔽会让稀有类的 logit 无节制上涨、误检暴增。<em>此外 EQL 只屏蔽来自「其他前景类正样本」的负梯度，保留来自背景的负梯度</em>，否则模型会把背景也当成稀有类。"),
        P("EQL 的问题是<strong>它把类别硬切成「稀有/不稀有」两档</strong>，λ 是个敏感超参，而且要求你事先知道类别频率——在数据持续增长的量产系统里，频率是天天在变的。"),
        H3("EQLv2：把梯度比当作反馈信号在线均衡"),
        P("<span class=\"term\">EQLv2</span>（Tan et al., CVPR 2021）把思路从「屏蔽」升级为「<strong>梯度引导的重加权，目标是把每个类的累积正负梯度比拉到 1:1</strong>」。它在训练中<em>在线</em>维护每个类的累积梯度统计："),
        MATH(r"g_j = \frac{\sum |\nabla^{+}_j|}{\sum |\nabla^{-}_j|}, \qquad q_j = 1 + \alpha\bigl(1 - f(g_j)\bigr), \qquad r_j = f(g_j), \qquad f(x)=\frac{1}{1+e^{-\gamma(x-\mu)}}"),
        P("<code>q_j</code> 放大正梯度、<code>r_j</code> 衰减负梯度（论文默认 <code>α=4, γ=12, μ=0.8</code>）。<code>g_j</code> 越小（说明该类被负梯度压得越狠），<code>f(g_j)</code> 越接近 0，于是正梯度被放大到接近 <code>1+α</code> 倍、负梯度被压到接近 0。<strong>这是一个负反馈控制器</strong>：类别一旦被均衡回来，<code>g_j</code> 上升，加权自动退回中性。"),
        TABLE(["", "EQL v1", "EQLv2"], [
            ["核心操作", "对稀有类<strong>屏蔽</strong>来自常见前景类的负梯度", "按累积梯度比<strong>连续重加权</strong>正/负梯度"],
            ["是否需要类别频率先验", "<strong>需要</strong>（λ 阈值基于 f_c）", "<strong>不需要</strong>——统计量在线累积"],
            ["类别粒度", "二值（稀有 / 不稀有）", "<strong>每类连续</strong>，且随训练自适应"],
            ["超参", "λ、β 的概率 p（敏感）", "α, γ, μ（论文默认值鲁棒，基本不用调）"],
            ["对新增类别", "要重新统计频率、重设 λ", "<strong>天然友好</strong>：新类 g_j 低 → 自动被扶持"],
            ["典型收益（LVIS AP_r）", "+4~6", "<strong>再 +2~3</strong>，且训练更稳"],
        ]),
        DUAL(
            "什么时候<strong>不</strong>该用 EQL 系？<em>如果你的检测头是 softmax 多分类（老式两阶段 R-CNN 的 RoI head），负梯度淹没的机制并不成立</em>——softmax 里各类 logit 是竞争关系，稀有类不会被独立地压到 −∞，问题表现为「被判成头部类」而不是「分数极低」。这时该用的是 BAGS（balanced group softmax）或 logit adjustment，而不是 EQL。<strong>能说出「EQL 是为 sigmoid 头设计的」这个前提，是读懂了机制而不是记住了名字。</strong>",
            "EQLv2 在 TSR 上的价值特别高，原因是<strong>类别数多且持续增长</strong>：一个量产 TSR 系统的类别表通常有 200–500 项（限速 5–120 的每一档、组合牌、区域性标志），且随着法规更新和城市扩展不断加类。<em>每加一批类就重新统计频率、重调 λ 是不现实的</em>；EQLv2 的在线梯度统计恰好绕开了这个运维负担。而且新类刚加进来时样本极少、<code>g_j</code> 极低，正是它被自动扶持得最狠的时候——<strong>这与数据闭环「持续加新类、持续补数据」的节奏天然契合</strong>。",
        ),
    ])),

    ("logit_adj", "Logit adjustment：零训练成本的一行修正", "".join([
        P("前面几节都要改训练。这一节的方法<strong>完全不改训练</strong>，只改推理时的一行代码，却有干净的贝叶斯推导。<strong>它应该是你遇到长尾问题时第一个试的东西</strong>——因为它半小时就能告诉你「先验修正能救回多少」，从而判断值不值得投入去改训练。"),
        H3("推导"),
        P("设训练集的类别先验是 <code>π_c = n_c / N</code>，而你真正关心的评测分布是<strong>类别平衡</strong>的（macro 指标、或者每类同等重要的安全场景）。模型在训练分布上拟合的是"),
        MATH(r"p_{\mathrm{train}}(y=c \mid x) \;\propto\; p(x \mid y=c)\,\pi_c \qquad\Longrightarrow\qquad p_{\mathrm{bal}}(y=c \mid x) \;\propto\; \frac{p_{\mathrm{train}}(y=c\mid x)}{\pi_c}"),
        P("在 logit 空间上，除以 <code>π_c</code> 就是<strong>减去 <code>log π_c</code></strong>。于是平衡分布下的最优决策是："),
        MATH(r"\hat y \;=\; \arg\max_c \ \bigl[\, z_c(x) \;-\; \tau \log \pi_c \,\bigr], \qquad \tau = 1 \ \text{为理论最优}"),
        P("<code>τ</code> 是一个实践中放松出来的温度：<code>τ=0</code> 退回原始预测，<code>τ=1</code> 是完全的先验校正，<code>τ∈(0,1)</code> 是折中。<em>理论最优 τ=1 的前提是模型完美拟合了 <code>p_train(y|x)</code>；实际模型有拟合误差，所以最优 τ 往往落在 0.5–1.0 之间，需要在验证集上扫一遍。</em>"),
        P("还有一个<strong>训练时版本</strong>（logit-adjusted loss）：把修正项<em>加</em>进训练的 softmax 里，推理时什么都不做——"),
        MATH(r"\mathcal{L} = -\log \frac{e^{\,z_y + \tau\log\pi_y}}{\sum_j e^{\,z_j + \tau\log\pi_j}}"),
        P("两者在理想情况下等价，但训练时版本通常更稳（模型有机会自己适应这个偏置），代价是要重训。<strong>工程上的正确顺序是：先用推理时版本白嫖一次，看天花板在哪，再决定要不要花一次训练去做训练时版本。</strong>"),
        TABLE(["", "推理时 logit adjustment", "训练时 logit-adjusted loss", "τ-normalized（下一节）"], [
            ["成本", "<strong>零</strong>——改一行 argmax", "一次完整重训", "<strong>零</strong>——只归一化权重"],
            ["需要什么", "训练集类别先验 <code>π_c</code>", "同左", "训练好的分类器权重"],
            ["能调吗", "<strong>能</strong>，τ 可在验证集上扫", "要重训才能换 τ", "能，τ 可扫"],
            ["典型增益（长尾分类）", "尾部 +5~15 个点", "略优于推理时版", "与推理时版相当"],
            ["主要风险", "<strong>稀有类误检暴增</strong>，score 阈值失效", "同左，但更可控", "同左"],
        ]),
        CALLOUT("danger", "<p><strong>在检测里用 logit adjustment 有三个必须处理的细节，忽略任何一个都会翻车：</strong></p><p>① <strong>π_c 用什么统计？</strong>检测的 <code>π_c</code> 可以是实例数占比，也可以是图像频率，还可以是「被标签分配判为该类正样本的位置数」占比。<em>严格对应推导的是最后一个</em>（因为分类头是在候选位置上做决策的），但实践中实例数占比就够用。写清楚你用的是哪个，否则复现不出来。</p><p>② <strong>sigmoid 头上推导不严格成立。</strong>公式是从 softmax 的贝叶斯规则来的；sigmoid 多标签头里各类独立，减去 <code>log π_c</code> 只是一个启发式（虽然实践中有效）。此时 τ 必须调。</p><p>③ <strong>调完 logit，原来的 score 阈值与 NMS 全部失效。</strong>所有类的分数分布被整体平移，<em>你必须重新标定工作点</em>。在 TSR 里这一步尤其危险：把稀有类的分数抬上去，意味着「注意落石」「事故易发」这类牌的误检率上升——而误报一个「停车让行」会触发不必要的急刹。<strong>正确做法是按类别分别标定阈值，并在安全关键类上用更保守的 τ。</strong></p>", "调 logit = 移动工作点，必须重新标定"),
        CALLOUT("intuition", "面试里的加分说法：<strong>「我会先做 logit adjustment 和 τ-normalize，因为它们零训练成本，半小时就能知道『先验校正』这条路的天花板在哪；如果尾部 AP 因此涨了很多，说明瓶颈在分类器先验而不是表示，那我接下来做 cRT；如果几乎没涨，说明表示本身就分不开，得去补数据或者上层次标签。」</strong>——这段话展示的是「用便宜的实验做诊断，再决定贵的投入」的工程判断，比列举十个方法名有说服力得多。"),
    ])),

    ("decouple", "解耦训练：表示是好的，坏掉的是分类器", "".join([
        P("2020 年 Kang 等人的 <em>Decoupling Representation and Classifier for Long-Tailed Recognition</em>（ICLR 2020）做了一个把整个领域重新定向的实验。<strong>结论反直觉但极其实用</strong>，而且它给上一节那句「坏掉的是最后一层」提供了系统性证据。"),
        H3("那个关键实验"),
        OL([
            "用<strong>原始长尾分布</strong>（instance-balanced sampling，就是什么都不做）训练一个模型。",
            "把 backbone 冻住，只把最后的线性分类器<strong>丢掉重训</strong>，重训时用类别平衡采样。",
            "结果：尾部类准确率大幅提升，<strong>而且整体表现优于「从头就用平衡采样训练」的模型</strong>。",
        ]),
        P("再补一个更强的证据：<strong>用长尾训练出来的特征做最近类均值（NCM）分类</strong>——不训练任何分类器，只算每类特征均值然后按余弦相似度分类——尾部类的准确率也显著高于模型自己的分类头。<em>这说明重采样带来的收益几乎全部作用在分类器上，而重采样对表示学习是<strong>有害</strong>的</em>（因为它让 backbone 反复看同样那几十张尾部图片，多样性下降）。"),
        DUAL(
            "把两件事拆开就清楚了：<strong>backbone 需要的是「多样性」，分类器需要的是「平衡」</strong>。instance-balanced 采样给 backbone 提供了最大的数据多样性（每张图看一遍），而分类器则应该在平衡的分布上决定决策边界。<em>过去所有「从头重采样」的方法都在用一个手段同时干预两个需求，于是在其中一个上做了错事。</em>",
            "这个结论也解释了 LDAM-DRW 里 DRW（延迟重加权）为什么有效：前期不加权 = 让表示在原分布上充分学；后期加权 = 只在末段调整决策边界。<strong>DRW 本质上是解耦的「软」版本</strong>——不冻结 backbone，但通过时间顺序近似达到同样效果。<em>把「解耦」「DRW」「两阶段微调分类头」看成同一个思想的三种实现，是理解这一整块的正确方式。</em>",
        ),
        TABLE(["阶段二方法", "做什么", "训练成本", "备注"], [
            ["<strong>cRT</strong>（classifier re-training）", "冻结 backbone，用类别平衡采样重训最后一层 fc", "<strong>极低</strong>（只有一层，可离线在缓存特征上跑）", "<strong>最实用的一招</strong>；工程上通常几分钟"],
            ["<strong>τ-normalized</strong>", "<code>w_c ← w_c / ‖w_c‖^τ</code>，直接把权重范数拉平", "<strong>零</strong>（不训练）", "τ 在验证集上扫；与 logit adjustment 效果相当"],
            ["<strong>LWS</strong>（learnable weight scaling）", "冻结方向，只学每类一个标量缩放 <code>f_c</code>", "极低（C 个参数）", "介于 cRT 与 τ-norm 之间"],
            ["<strong>NCM</strong>（nearest class mean）", "用每类特征均值 + 余弦相似度分类，完全不用 fc", "零", "主要用作<strong>诊断</strong>：NCM 明显优于 fc ⇒ 问题在分类器"],
        ]),
        H3("检测里怎么落地"),
        UL([
            "<strong>两阶段检测器（Faster R-CNN 系）最容易</strong>：RoI head 的分类分支就是一个独立的小网络，可以单独重训。把训练集过一遍、缓存 RoI 特征，然后用平衡采样重训分类分支——成本是全量训练的 <strong>1/50 量级</strong>。",
            "<strong>BAGS（Balanced Group Softmax, CVPR 2020）</strong>：把类别按频率分组，组内做 softmax，组间不竞争。这样头部类的 logit 不会直接压制尾部类，是「分组解耦」的思路。",
            "<strong>一阶段 sigmoid 头</strong>：分类分支与回归分支共享卷积，冻结更麻烦；实践中常用「只解冻分类分支的最后 1×1 conv + 用平衡采样微调少量 iteration」，或直接用 τ-normalize 这种零成本方案。",
            "<strong>诊断优先</strong>：先算 <code>‖w_c‖ vs log n_c</code> 的相关系数。<em>相关系数高（>0.8）就说明你正处在「分类器被频率带偏」的典型状态，解耦一定有效；相关系数低则说明问题在别处</em>——这个五分钟就能做的检查，能省掉一次白跑的训练。",
        ]),
        CALLOUT("intuition", "本节的可迁移心法：<strong>遇到长尾，先问「是表示的问题还是分类器的问题」，再选药。</strong>诊断工具有两个，都很便宜：① 分类器权重范数 vs log(样本数) 的相关性；② NCM 准确率 vs 模型自身分类头准确率的差。<em>这两个数一算，你就知道该去补数据（表示问题）还是该去重训分类头（分类器问题）——这正是下一节决策树的第一个分叉。</em>"),
    ])),

    ("arch", "架构与数据侧：两级方案、层次标签与 copy-paste", "".join([
        P("前面五节都在「同一份数据、同一个模型」的框架内做文章。但长尾最有效的两类解法其实在框架之外：<strong>换架构</strong>和<strong>真的补数据</strong>。TSR 恰好是这两类解法都特别适用的场景。"),
        H3("两级方案：把长尾从检测器里搬出去"),
        P("C55 m02 讲过 TSR 的两级方案——<strong>第一级做类别无关（或粗类）的标志检测，第二级把 crop 送进一个专门的分类器</strong>。从长尾的角度看，它带来四个结构性好处："),
        OL([
            "<strong>第一级完全没有类别间不平衡</strong>。它只做「是标志 / 不是标志」的二分类，剩下的只有前景-背景不平衡，用 Focal Loss 就够了。<em>把两种不平衡在架构层面分离开——这是本模块第一节那个区分的最优雅的兑现方式。</em>",
            "<strong>第二级是纯分类任务，长尾方法的全部弹药都能用</strong>。而且分类的重采样成本极低（crop 可以缓存成小图，一个 epoch 秒级），CB Loss / LDAM / cRT / logit adjustment 全部直接适用，调参迭代快一两个数量级。",
            "<strong>新增类别不需要重训检测器</strong>。法规更新加了 5 个新标志？只重训第二级分类器，几分钟的事，检测器一行不动。<em>在类别表持续增长的量产系统里，这个性质的价值极高。</em>",
            "<strong>第二级可以用更高分辨率</strong>。把 24×24 的 crop 放大到 64×64 再分类，比在检测特征图上直接分类的信息量大得多——这同时缓解了长尾与小目标两个问题。",
        ]),
        CALLOUT("warn", "两级方案的代价必须一起讲，否则面试官会追问：<strong>① 误差级联</strong>——端到端召回 = 检测召回 × 分类准确率，两个 0.95 相乘就只剩 0.90，<em>第一级漏掉的第二级永远救不回来</em>；<strong>② 延迟叠加</strong>——车端 33ms 的预算里要塞下两次前向；<strong>③ 置信度合成</strong>——两级各有一个分数，怎么合成、怎么标定是个真问题（C55 m02 展开）。<em>能主动说出「级联召回是乘法」这一句，说明你真的算过账。</em>"),
        H3("层次标签：让粗类的梯度帮到细类"),
        P("交通标志天然有层次：<strong>禁令 / 警告 / 指示 / 指路</strong>（粗类，由形状和颜色决定）→ 具体标志（细类）→ 属性（限速值等）。关键观察是：<strong>粗类永远不稀有</strong>——「警告类」加起来有几万个实例，哪怕其中「注意落石」只有 30 个。于是用层次损失（粗类头 + 细类头，或树结构 softmax），<em>稀有细类可以从它所属粗类的海量样本里借到梯度</em>，学会「三角形 + 黄底 + 黑边 = 警告类」这个共享结构，只需要用自己那 30 个样本去学「里面画的是石头」。"),
        H3("copy-paste：真正增加实例数与背景多样性"),
        P("重采样只是把同样 30 张图看更多遍；<strong>copy-paste 是真的在造新样本</strong>——把稀有标志从原图抠出来，贴到大量新背景上（C56 m03 展开）。它同时提升了「实例数」和「背景多样性」两个维度，这是重采样做不到的。合理性约束也要一起记：<em>尺度要符合透视（贴在远处的标志要小）、位置要合法（不能贴到天上或路面上）、边缘要羽化、光照要匹配</em>。"),
        TABLE(["手段", "实例数", "背景多样性", "表示质量", "成本", "一句话"], [
            ["重采样（RFS）", "不变", "<strong>不变</strong>", "略降（过拟合）", "零", "把同样的图多看几遍"],
            ["重加权（CB/LDAM）", "不变", "不变", "中性", "零", "改损失分量，不改数据"],
            ["EQLv2", "不变", "不变", "中性", "零", "修正梯度失衡，检测专用"],
            ["logit adj / τ-norm", "不变", "不变", "<strong>不变</strong>", "零", "只改决策边界，表示一点不碰"],
            ["解耦（cRT）", "不变", "不变", "<strong>保住</strong>（用原分布学表示）", "极低", "表示与分类器分开对待"],
            ["<strong>copy-paste</strong>", "<strong>↑↑</strong>", "<strong>↑↑</strong>", "<strong>↑</strong>", "低（需实例库）", "真的造新样本"],
            ["<strong>定向挖掘补数据</strong>", "<strong>↑↑↑</strong>", "<strong>↑↑↑</strong>", "<strong>↑↑</strong>", "<strong>高</strong>（标注钱）", "唯一能提高信息量上限的手段"],
        ]),
        CALLOUT("intuition", "把这张表读成一句话：<strong>前五行都在「重新分配已有信息」，只有最后两行在「增加信息」。</strong>所以它们不是互斥的选项而是<em>叠加的层次</em>——先用零成本的手段把现有数据榨干（这是本模块），再用挖掘与标注去提高信息量上限（这是模块 03–05）。<em>顺序反过来做，你会花很多标注钱去买本来靠一行 logit adjustment 就能拿到的收益。</em>"),
    ])),

    ("tree", "方法选择决策树：面试里能分层作答的人极少", "".join([
        P("到这里方法已经很多了。<strong>真正的区分度不在「知道多少个方法」，而在「能不能先诊断再开药」。</strong>面试官问「长尾怎么办」，绝大多数人会开始背方法名；能先说「我要先看三个数，再决定用哪一类方法」的人，立刻就分出来了。"),
        H3("第一步：先看这三个数（十分钟）"),
        OL([
            "<strong>逐类 AP 按频率分桶</strong>（frequent / common / rare）。确认问题真的是长尾——<em>如果 rare 桶 AP 不低，你面对的根本不是长尾问题</em>。",
            "<strong>尾部类的 recall 与 score 分布</strong>。recall 也是 0（框根本没出来）还是 recall 尚可但分数低被阈值滤掉？<strong>这两种情况的解法完全相反。</strong>",
            "<strong>分类器权重范数 ‖w_c‖ 与 log(n_c) 的相关系数</strong>，以及 <strong>NCM 准确率 vs 模型分类头准确率</strong>。这两个数直接告诉你「坏的是表示还是分类器」。",
        ]),
        ASCII("""                        ┌──────────────────────────────┐
                        │  尾部类指标差 —— 先诊断       │
                        └──────────────┬───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   ① recall ≈ 0                  ② recall 尚可                  ③ 被错分成
   （框根本没出来）                 但 score 极低                 相似的头部类
        │                              │                              │
   不是分类问题！                 **典型的负梯度淹没**            特征不可分，
   是**检出**问题                 ‖w_c‖ ~ log n_c 强相关          不是先验问题
        │                              │                              │
        ▼                              ▼                              ▼
   · 查标签分配（尾部框是否        零成本先试:                    · 层次标签（借粗类梯度）
     根本分不到正样本）            · **logit adjustment**          · 更高分辨率 crop / 两级
   · 查 anchor / 尺度              · **τ-normalize**               · 难例挖掘（C58 m02）
   · 尾部是否同时是小目标(C57)          ↓ 还不够                    · 混淆矩阵找出具体混淆对
   · 检查这些类是否漏标严重        低成本:                              │
        │                          · **cRT**（只重训分类头）           │
        │                              ↓ 还不够                        │
        │                          改训练:                             │
        │                          · **RFS**（检测默认起点）           │
        │                          · **EQLv2**（sigmoid 头必选）       │
        │                          · CB Loss / LDAM+DRW                │
        └──────────────┬───────────────┴──────────────────────────────┘
                       │            ④ 尾部类训练集只有 10 张图
                       ▼               → 任何重加权都在压榨同样 10 张图
        ┌────────────────────────────────────────────────────┐
        │  数据侧（唯一能提高信息量上限的手段）               │
        │  · **copy-paste** 合成（C56 m03）                   │
        │  · **定向挖掘 + 标注**（C58 m03–m05）               │
        │  · 架构：两级方案把长尾搬出检测器                   │
        └────────────────────────────────────────────────────┘"""),
        TABLE(["症状", "诊断", "首选方法", "为什么不用别的"], [
            ["rare 类 AP=0 且 <strong>recall≈0</strong>", "框都没出来 → 检出问题", "改标签分配 / 查漏标 / 按小目标处理", "<strong>重加权只影响分类分数，框都没出来时它什么也改变不了</strong>"],
            ["rare 类 recall 尚可、<strong>score 极低</strong>", "负梯度淹没 / 分类器先验偏置", "<strong>logit adj → τ-norm → cRT → EQLv2</strong>（按成本递增试）", "先用零成本方案探天花板，别一上来就重训"],
            ["rare 类被<strong>错分成相似头部类</strong>", "特征不可分", "层次标签 / 高分辨率 crop / 两级 / 难例挖掘", "先验校正只会把误分方向反转，不会让特征变得可分"],
            ["rare 类<strong>只有 10 张图</strong>", "信息量根本不够", "<strong>copy-paste + 定向挖掘</strong>", "所有重采样/重加权都在压榨同样 10 张图，天花板锁死"],
            ["整体 mAP 尚可但 <strong>macro 很低</strong>", "指标口径问题", "先改评测：分桶报告 + macro，再谈优化", "优化没有度量的东西 = 白干"],
        ]),
        DUAL(
            "决策树的骨架可以压成一句面试答案：<strong>「先分桶诊断（是不是长尾、是 recall 问题还是 score 问题、是表示问题还是分类器问题），再按成本递增依次试：零成本的 logit adjustment / τ-normalize → 低成本的 cRT → 改训练的 RFS 与 EQLv2 → 最贵但唯一提高上限的 copy-paste 与定向挖掘。每一步都用分桶指标验证，并守住『头部类不许掉』的回归门禁。」</strong>",
            "补一句能显出实战经验的话：<strong>这些方法的收益不是可加的</strong>。RFS + CB Loss + logit adjustment 三个叠起来，往往只比单用最好的那个多一点，甚至更差——因为它们本质上都在做同一件事（把有效类别先验拉平），叠加就是<em>过度校正</em>：尾部类误检暴涨，头部类被压。<em>正确做法是把它们视为同一个旋钮的不同实现，选一个、把它的强度参数（p / β / τ）调好，而不是全都开上。</em>这个认识在消融实验里能省掉一半的无效组合。",
        ),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>长尾方法在强预训练下还剩多少价值。</strong>越来越多的证据表明，用大规模预训练（或自监督）得到的表示已经把尾部类的<em>特征</em>学得足够好，于是长尾专用方法的增益大幅缩水，剩下的几乎全是「分类器先验校正」那一部分。<em>如果这个趋势成立，本模块的重心会进一步向 logit adjustment / 解耦这条线收敛，而重采样与复杂重加权会逐渐退场。</em>这是当前最值得关注的一个方向性问题。",
            "<strong>AP_r 的统计不可靠性。</strong>LVIS 的 rare 类往往只有个位数实例，其 AP 的估计方差极大——<em>不同随机种子之间 AP_r 波动 1–2 个点是常态</em>。于是「某方法 AP_r +1.5」这类结论在统计上常常站不住。领域内缺少公认的、方差可控的长尾评测协议，这直接影响所有方法对比的可信度。",
            "<strong>开放词表检测（open-vocabulary detection）</strong>把长尾推到极限：稀有类干脆不在训练集里，用 CLIP 等视觉-语言模型的文本嵌入做零样本识别。对 TSR 这种<em>类别体系随法规演化、新标志不断出现</em>的任务，吸引力显而易见；但零样本精度距离量产安全阈值仍有明显差距，目前更现实的用法是<strong>用 VLM 做挖掘与打标（模块 04），而不是直接做识别</strong>。",
            "<strong>生成式合成能替代多少真实尾部数据。</strong>扩散模型合成稀有类样本在分类基准上已有可观收益，但在检测上要同时保证「实例真实」与「上下文合理」（一个贴在人行道正中的限速牌会教坏模型）。<em>「合成数据涨的点在真实路测上兑现多少」目前缺少可信的度量</em>——现有共识是合成能救「实例数不足」，救不了「场景多样性不足」。",
            "<strong>梯度均衡与优化器的交互。</strong>EQLv2 这类在线重加权本质上在动态改变每个类的有效学习率，它与 AdamW 的二阶矩估计、与学习率调度、与 EMA 的交互几乎没有被系统研究过。<em>实践中「EQLv2 + 某些优化器配置不稳定」的报告一直存在，但缺少理论解释。</em>",
            "<strong>长尾与安全代价的耦合。</strong>所有现有长尾方法都在优化「每类同等重要」的 macro 指标，但在自动驾驶里<strong>漏检「停车让行」和漏检「景点指示」的代价差几个数量级</strong>。<em>把代价矩阵直接写进重加权/先验校正（而不是事后调阈值），在理论上是自然的（贝叶斯决策），在工程上却几乎没人做</em>——这是一个对 TSR 特别有价值、且相对空白的方向（评测侧见 C55 m05）。",
        ]),
        CALLOUT("paper", "本模块必读（★ 为优先，读的顺序就是这个）：★ <em>LVIS: A Dataset for Large Vocabulary Instance Segmentation</em>（Gupta et al., CVPR 2019）——repeat factor sampling 的原始出处，公式与三个设计选择都在里面；★ <em>Class-Balanced Loss Based on Effective Number of Samples</em>（Cui et al., CVPR 2019）——有效样本数 <code>(1−β^n)/(1−β)</code> 的推导；<em>Learning Imbalanced Datasets with Label-Distribution-Aware Margin Loss</em>（Cao et al., NeurIPS 2019）——LDAM 与 DRW；★ <em>Equalization Loss for Long-Tailed Object Recognition</em>（Tan et al., CVPR 2020）与 ★ <em>Equalization Loss v2: A New Gradient Balance Approach</em>（Tan et al., CVPR 2021）——<strong>检测长尾最该精读的两篇</strong>，负梯度淹没机制与在线梯度均衡；★ <em>Long-tail learning via logit adjustment</em>（Menon et al., ICLR 2021）——推理时先验校正的理论；★ <em>Decoupling Representation and Classifier for Long-Tailed Recognition</em>（Kang et al., ICLR 2020）——cRT / τ-normalize / LWS / NCM 四种阶段二方案；<em>Overcoming Classifier Imbalance for Long-tail Object Detection with Balanced Group Softmax</em>（Li et al., CVPR 2020）——softmax 头的对应解法；<em>Focal Loss for Dense Object Detection</em>（Lin et al., ICCV 2017）——注意它解决的是<strong>前景-背景</strong>不平衡；<em>Simple Copy-Paste is a Strong Data Augmentation Method</em>（Ghiasi et al., CVPR 2021）与 <em>Deep Long-Tailed Learning: A Survey</em>（Zhang et al., TPAMI 2023）。相邻课程：C55（TSR 两级方案与安全评测）、C56（copy-paste）、C57（小目标与长尾的纠缠）、C58 m02（难例挖掘）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 类别不平衡的处理谱系（RFS / CB Loss / LDAM / EQLv2 / logit adjustment / 解耦）

目标：在**同一份合成长尾数据**上把整条方法谱系跑一遍，亲手看到每个方法把尾部类召回抬了多少、
把头部类压了多少——**而不是背方法名**。

本 notebook 你会亲手实现：
1. 幂律长尾分类任务 + 基线 softmax 分类器（以及"平衡数据 oracle"作为上界）
2. **Repeat Factor Sampling**：`r_c = max(1, √(t/f_c))` + 图内取最大 + 每 epoch 随机取整
3. **Class-Balanced Loss** 的有效样本数 `(1-β^n)/(1-β)`（含递推式验证）与 **LDAM** 的间隔
4. **负梯度淹没的复现**：sigmoid 多标签头上，稀有类的累积正负梯度比 → **EQL v1 与 EQLv2**
5. **Logit adjustment**：推理时减 `τ·log π_c`，零训练成本
6. **解耦训练**：`‖w_c‖ vs log n_c` 的相关性、**NCM 诊断**（证明表示是好的）、τ-normalize、cRT
7. **全方法对比表** + **方法选择决策树**的代码化

> 心智模型：**稀有类的问题往往不是"特征学不好"，而是"分类器的 logit 被海量负梯度压死了"。**
> 先诊断是表示问题还是分类器问题，再按成本递增选药。"""),

    md("""## 1 · 合成长尾数据集与基线

合成规则（都写清楚，方便你改参数看规律）：
- `C=12` 个类，第 `r` 名的训练样本数 `n_r = 1500 · r^-2.0`，下限 10 → **头/尾比 150:1**
- 每类一个 24 维球面上的中心（模长 3.0），样本 = 中心 + 各向同性高斯噪声（σ=1）
- **表示层固定**：`h = tanh(x·R + b_R)`，`R` 是固定的随机投影。
  这样所有方法都在同一份表示上比较分类器——**正是本模块要隔离的变量**
- **测试集类别平衡**（每类 300 个），因为我们关心的是 macro 指标"""),

    code(r"""import numpy as np, json, math
rng = np.random.default_rng(58)
np.set_printoptions(precision=3, suppress=True)

C, D, H = 12, 24, 32
ALPHA, N_HEAD, N_FLOOR = 2.0, 1500, 10
ranks = np.arange(1, C + 1)
train_counts = np.maximum(np.round(N_HEAD * ranks ** (-ALPHA)), N_FLOOR).astype(int)

centers = rng.normal(size=(C, D))
centers /= np.linalg.norm(centers, axis=1, keepdims=True)
centers *= 3.0                                   # 类间距离 ≈ 3√2 ≈ 4.24, 噪声 σ=1

def sample(counts, gen):
    X = np.concatenate([centers[c] + gen.normal(size=(n, D)) for c, n in enumerate(counts)])
    y = np.concatenate([np.full(n, c) for c, n in enumerate(counts)])
    return X, y

Xtr, ytr = sample(train_counts, rng)
Xte, yte = sample(np.full(C, 300), np.random.default_rng(7))     # **平衡测试集**

R = rng.normal(size=(D, H)) / np.sqrt(D)
bR = rng.normal(size=H) * 0.1
def feat(X): return np.tanh(X @ R + bR)          # 固定表示层
Htr, Hte = feat(Xtr), feat(Xte)

HEAD, MID, TAIL = slice(0, 4), slice(4, 8), slice(8, 12)
print('每类训练样本数:', train_counts, ' 总计', train_counts.sum())
print(f'头/尾比 = {train_counts[0] / train_counts[-1]:.0f} : 1'
      f'   |  head={train_counts[HEAD].sum()}  mid={train_counts[MID].sum()}'
      f'  tail={train_counts[TAIL].sum()}')

def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)

def train_softmax(Hm, y, sample_w=None, class_w=None, margin=None, prior_logit=None,
                  steps=1500, lr=0.5, wd=1e-4):
    '''全批梯度下降的线性 softmax 分类器。
       sample_w  : 每样本权重（用来模拟重采样 —— 重复 k 次 ≡ 权重 k）
       class_w   : 每类权重（重加权：CB Loss / 反频率）
       margin    : 每类间隔 Δ_c（LDAM：训练时 z_y ← z_y - Δ_y）
       prior_logit: 训练时的先验偏置 τ·log π（logit-adjusted loss）'''
    n = len(y)
    W = np.zeros((Hm.shape[1], C)); b = np.zeros(C)
    Y = np.zeros((n, C)); Y[np.arange(n), y] = 1.0
    w = np.ones(n) if sample_w is None else np.asarray(sample_w, float)
    if class_w is not None:
        w = w * np.asarray(class_w, float)[y]
    w = w / w.mean()
    for _ in range(steps):
        z = Hm @ W + b
        if margin is not None:  z = z - Y * margin           # 只对真值类扣间隔
        if prior_logit is not None: z = z + prior_logit
        G = (softmax(z) - Y) * w[:, None]
        W -= lr * (Hm.T @ G) / n + lr * wd * W
        b -= lr * G.mean(0)
    return W, b

def per_class_acc(W, b, Hm=None, y=None, adj=None):
    Hm = Hte if Hm is None else Hm
    y = yte if y is None else y
    z = Hm @ W + b
    if adj is not None: z = z + adj
    pred = z.argmax(1)
    return np.array([(pred[y == c] == c).mean() for c in range(C)])

RESULTS = {}
def report(name, per, store=True):
    if store: RESULTS[name] = per
    print(f'{name:<26s} head {per[HEAD].mean():.3f}  mid {per[MID].mean():.3f}'
          f'  tail {per[TAIL].mean():.3f}  **macro {per.mean():.3f}**')

W0, b0 = train_softmax(Htr, ytr)
per0 = per_class_acc(W0, b0)
report('① baseline (plain CE)', per0)
print('   逐类准确率:', np.round(per0, 3))

Xb, yb = sample(np.full(C, N_HEAD), np.random.default_rng(3))    # 上界: 每类都有 1500 个
Wb, bb = train_softmax(feat(Xb), yb)
report('⓪ oracle (平衡数据)', per_class_acc(Wb, bb))

assert per0[HEAD].mean() > per0[TAIL].mean() + 0.3, '基线必须呈现明显的头尾差'
assert RESULTS['⓪ oracle (平衡数据)'].mean() > per0.mean() + 0.15, 'oracle 应显著更高'
print('\n⚠️  基线的头尾差 %.3f —— 这不是"特征不够好", 后面第 6 节会证明表示其实没坏。'
      % (per0[HEAD].mean() - per0[TAIL].mean()))"""),

    md("""## 2 · Repeat Factor Sampling（LVIS 的做法）

`r_c = max(1, √(t/f_c))` → `r_i = max_{c∈i} r_c` → 每 epoch 随机取整。

**注意 `f_c` 是图像频率（含该类的图像数 ÷ 总图像数），不是实例数占比**——
因为采样的单位是图像。本 notebook 里每个样本 = 一张只含一个目标的图，两者恰好相同；
练习 1 会让你实现真正的多标签版本（一张图含多个类）。"""),

    code(r"""f_img = train_counts / train_counts.sum()        # 图像频率 f_c

def repeat_factor_c(f_c, t):
    '''类别级 repeat factor: r_c = max(1, sqrt(t / f_c))'''
    return np.maximum(1.0, np.sqrt(t / np.asarray(f_c, float)))

print(f"{'阈值 t':>8s}  " + ' '.join(f'c{c:<4d}' for c in [0, 3, 7, 11]))
for t in [0.01, 0.05, 0.2]:
    r = repeat_factor_c(f_img, t)
    print(f'{t:>8.2f}  ' + ' '.join(f'{r[c]:<5.2f}' for c in [0, 3, 7, 11]))
print('\n对比 **完全拉平** 1/f_c 的重复倍数:', np.round(1 / f_img, 1)[[0, 3, 7, 11]])
print('→ √ 把尾部重复倍数从 %.0f× 压到 %.1f×, 这就是"温和过采样"的含义。'
      % ((1 / f_img)[-1], repeat_factor_c(f_img, 0.2)[-1]))

T_RFS = 0.2
r_c = repeat_factor_c(f_img, T_RFS)

def rfs_epoch(y, r_c, gen):
    '''每 epoch 随机取整: k_i = floor(r_i) + Bernoulli(r_i - floor(r_i))'''
    r = r_c[y]
    k = np.floor(r).astype(int) + (gen.random(len(r)) < (r - np.floor(r))).astype(int)
    return np.repeat(np.arange(len(y)), k)

gen = np.random.default_rng(5)
idx = rfs_epoch(ytr, r_c, gen)
print(f'\nepoch 长度: {len(ytr)} → {len(idx)}  ({len(idx)/len(ytr):.2f}×)'
      '   ← **消融时必须同步调 iteration 数, 否则重采样组偷偷多训了**')

# 期望重复次数 ≈ r_i（随机取整是无偏的）
k_exp = np.zeros(C)
for _ in range(30):
    ii = rfs_epoch(ytr, r_c, gen)
    k_exp += np.bincount(ytr[ii], minlength=C) / train_counts
k_exp /= 30
print('随机取整 30 个 epoch 的平均重复次数:', np.round(k_exp, 2))
assert np.allclose(k_exp, r_c, atol=0.06), '随机取整应当是无偏的'

sw = np.bincount(rfs_epoch(ytr, r_c, gen), minlength=len(ytr)).astype(float)
Wr, br = train_softmax(Htr, ytr, sample_w=sw)
report('② RFS (t=0.2)', per_class_acc(Wr, br))
assert RESULTS['② RFS (t=0.2)'][TAIL].mean() > per0[TAIL].mean() + 0.1, 'RFS 应显著抬高尾部'
print('\n✅ RFS 的四个设计点: **图像频率 / 开方 / 图内取最大 / 每 epoch 随机取整**。')
print('⚠️  它只增加"看到的次数", 不增加信息量 —— 10 张图重复 100 次 ≠ 1000 张图。')"""),

    md("""## 3 · Class-Balanced Loss 的有效样本数，与 LDAM 的间隔

`E_n = (1-β^n)/(1-β)` 来自递推 `E_n = 1 + β·E_{n-1}, E_1 = 1`
（假设每个新样本有 β 的概率落进已被覆盖的区域）。
**β 是把"不加权"与"反频率"连成一条连续曲线的旋钮**，不是二选一。"""),

    code(r"""def effective_num(n, beta):
    n = np.asarray(n, float)
    if beta <= 0: return np.ones_like(n)
    return (1.0 - beta ** n) / (1.0 - beta)

# 递推式验证: E_n = 1 + beta * E_{n-1}
for beta in [0.9, 0.99, 0.999]:
    E = 1.0
    for k in range(2, 60):
        E = 1.0 + beta * E
    assert np.isclose(E, effective_num(59, beta)), f'递推与闭式应一致 (beta={beta})'
print('✅ 递推 E_n = 1 + β·E_{n-1} 与闭式 (1-β^n)/(1-β) 完全一致')

print(f"\n{'β':>8s}{'1/(1-β)':>10s}   " + ''.join(f'{f"E(n={n})":>11s}' for n in [10, 100, 1500]))
for beta in [0.0, 0.9, 0.99, 0.999, 0.9999]:
    E = effective_num([10, 100, 1500], beta)
    sat = f'{1/(1-beta):.0f}' if beta < 1 else '∞'
    print(f'{beta:>8.4f}{sat:>10s}   ' + ''.join(f'{e:>11.1f}' for e in E))
print('→ β=0: E_n≡1(等价不加权)   β→1: E_n→n(等价反频率)。**1/(1-β) ≈ "多少样本算饱和"**')
assert np.allclose(effective_num([10, 100], 0.0), [1, 1])
assert abs(effective_num([50], 0.999999)[0] - 50) < 0.01, 'β→1 时 E_n → n'

def cb_weights(counts, beta):
    w = 1.0 / effective_num(counts, beta)
    return w / w.mean()

print(f"\n{'方案':<22s}" + ''.join(f'{f"w(c{c})":>10s}' for c in [0, 3, 7, 11]))
for name, w in [('不加权', np.ones(C)),
                ('CB β=0.99', cb_weights(train_counts, 0.99)),
                ('CB β=0.999', cb_weights(train_counts, 0.999)),
                ('CB β=0.9999', cb_weights(train_counts, 0.9999)),
                ('反频率 1/n', (1 / train_counts) / (1 / train_counts).mean())]:
    print(f'{name:<22s}' + ''.join(f'{w[c]:>10.3f}' for c in [0, 3, 7, 11]))

for beta in [0.99, 0.999, 0.9999]:
    Wc, bc = train_softmax(Htr, ytr, class_w=cb_weights(train_counts, beta))
    report(f'③ CB Loss β={beta}', per_class_acc(Wc, bc))

# LDAM: Δ_c ∝ n_c^(-1/4)
def ldam_margin(counts, c_max=0.5):
    d = 1.0 / np.asarray(counts, float) ** 0.25
    return d / d.max() * c_max

delta = ldam_margin(train_counts, 0.5)
print('\nLDAM 间隔 Δ_c:', np.round(delta, 3))
Wl, bl = train_softmax(Htr, ytr, margin=delta)
report('④ LDAM (无 DRW)', per_class_acc(Wl, bl))
Wl2, bl2 = train_softmax(Htr, ytr, margin=delta, class_w=cb_weights(train_counts, 0.999))
report('④ LDAM + DRW', per_class_acc(Wl2, bl2))

assert RESULTS['③ CB Loss β=0.999'][TAIL].mean() > per0[TAIL].mean() + 0.15
assert RESULTS['④ LDAM (无 DRW)'][TAIL].mean() < RESULTS['④ LDAM + DRW'][TAIL].mean() - 0.1, \
    'LDAM 单用收益有限, 必须配 DRW —— 这正是原论文的结论'
print('\n⚠️  **LDAM 单独用几乎没涨**（%.3f → %.3f），配上重加权才有效（→ %.3f）。'
      % (per0[TAIL].mean(), RESULTS['④ LDAM (无 DRW)'][TAIL].mean(),
         RESULTS['④ LDAM + DRW'][TAIL].mean()))
print('   这正是 LDAM-DRW 论文的核心：**先按原分布学表示, 后期再平衡决策边界**。')"""),

    md("""## 4 · 负梯度淹没：EQL 与 EQLv2 的机制

现在换成**检测器真正用的 sigmoid 多标签头**：每个类一个独立二分类，
再加进 4000 个**背景候选框**（它们对所有类都只贡献负梯度）。

关键量：类别 j 的**累积正负梯度比** `g_j = Σ|∇⁺| / Σ|∇⁻|`。
稀有类的 `g_j` 会低到头部类的几分之一 → `z_j` 被持续压低 → **score 上不去 → 被阈值滤掉**。"""),

    code(r"""N_BG = 4000
Xbg = rng.normal(scale=1.4, size=(N_BG, D))       # 背景候选框（不属于任何类）
Hall = np.vstack([Htr, feat(Xbg)])
Yall = np.zeros((len(Hall), C)); Yall[np.arange(len(ytr)), ytr] = 1.0
IS_FG = np.zeros(len(Hall), bool); IS_FG[:len(ytr)] = True
n_pos_cnt = Yall.sum(0); n_neg_cnt = len(Hall) - n_pos_cnt

print('每个类的**样本数**正负比（sigmoid 头下, 负样本 = 背景 + 所有其他类的正样本）:')
for c in [0, 3, 7, 11]:
    print(f'  类 {c:2d}  n={int(n_pos_cnt[c]):5d}   正:负 = 1 : {n_neg_cnt[c]/n_pos_cnt[c]:.0f}')

def sig(z): return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))

def train_bce(mode='plain', steps=1500, lr=0.05, alpha=4.0, gamma=12.0, mu=0.8,
              lam=0.02, p_keep=0.0, seed=0):
    '''sigmoid 多标签头 + Adam。
       mode='plain' 普通 BCE / 'eql' EQL v1 / 'eqlv2' EQLv2'''
    W = np.zeros((H, C)); b = np.full(C, -3.0)
    mW = np.zeros_like(W); vW = np.zeros_like(W)
    mb = np.zeros_like(b); vb = np.zeros_like(b)
    acc_pos = np.full(C, 1e-8); acc_neg = np.full(C, 1e-8)
    rare = (train_counts / train_counts.sum()) < lam       # EQL v1 的稀有类判定
    g_gen = np.random.default_rng(seed)
    for it in range(steps):
        Praw = sig(Hall @ W + b)
        Graw = Praw - Yall                                  # BCE 对 logit 的梯度
        if mode == 'eqlv2':
            g = acc_pos / np.maximum(acc_neg, 1e-12)
            fg = 1.0 / (1.0 + np.exp(-gamma * (g - mu)))    # 把 g 映射到 [0,1]
            q, r = 1.0 + alpha * (1.0 - fg), fg             # 放大正梯度 / 衰减负梯度
            wgt = np.where(Yall > 0, q[None, :], r[None, :])
        elif mode == 'eql':
            # 屏蔽"来自其他**前景**类正样本"的负梯度（**保留背景负梯度**）
            mask = (Yall == 0) & IS_FG[:, None] & rare[None, :]
            keep = g_gen.random(Graw.shape) < p_keep        # β~Bernoulli: 只屏蔽一部分
            wgt = np.where(mask & ~keep, 0.0, 1.0)
        else:
            wgt = np.ones_like(Graw)
        G = Graw * wgt
        acc_pos += np.abs(G * (Yall > 0)).sum(0)
        acc_neg += np.abs(G * (Yall == 0)).sum(0)
        gW, gb = (Hall.T @ G) / len(Hall), G.mean(0)
        t_, b1, b2, eps = it + 1, 0.9, 0.999, 1e-8
        mW = b1 * mW + (1 - b1) * gW; vW = b2 * vW + (1 - b2) * gW ** 2
        mb = b1 * mb + (1 - b1) * gb; vb = b2 * vb + (1 - b2) * gb ** 2
        W -= lr * (mW / (1 - b1 ** t_)) / (np.sqrt(vW / (1 - b2 ** t_)) + eps)
        b -= lr * (mb / (1 - b1 ** t_)) / (np.sqrt(vb / (1 - b2 ** t_)) + eps)
    return W, b, acc_pos / np.maximum(acc_neg, 1e-12)

SCORE_THR = 0.3           # 检测器的 score 阈值
def recall_at(W, b, thr=SCORE_THR):
    S = sig(Hte @ W + b)
    return np.array([(S[yte == c, c] >= thr).mean() for c in range(C)])

Wp, bp, g_plain = train_bce('plain')
rec_p = recall_at(Wp, bp)
print(f'\n{"":<20s}{"head":>8s}{"mid":>8s}{"tail":>8s}{"macro":>9s}   g_head / g_tail')
def rep_bce(name, rec, g):
    print(f'{name:<20s}{rec[HEAD].mean():>8.3f}{rec[MID].mean():>8.3f}'
          f'{rec[TAIL].mean():>8.3f}{rec.mean():>9.3f}   {g[HEAD].mean():.3f} / {g[TAIL].mean():.3f}')
rep_bce('BCE 基线', rec_p, g_plain)
print('\n每类累积正负梯度比 g_j:', np.round(g_plain, 3))
assert g_plain[TAIL].mean() < g_plain[HEAD].mean() - 0.15, '尾部类的 g_j 必须明显更低'
assert rec_p[TAIL].mean() < 0.4 * rec_p[HEAD].mean(), '尾部召回应被压得很低'
print(f'\n⚠️  尾部类 g_j = {g_plain[TAIL].mean():.3f} vs 头部 {g_plain[HEAD].mean():.3f}'
      f' —— **稀有类是被负梯度压死的**, 不是特征学不好。')
print(f'    结果: score@{SCORE_THR} 的尾部召回只有 {rec_p[TAIL].mean():.3f}'
      f'（头部 {rec_p[HEAD].mean():.3f}）—— **框可能定位得很准, 但根本输不出来**。')"""),

    code(r"""# EQL v1（屏蔽来自更常见前景类的负梯度）与 EQLv2（在线梯度均衡）
We, be, g_eql = train_bce('eql', lam=0.02, p_keep=0.0)
Wv, bv, g_v2 = train_bce('eqlv2')
rec_e, rec_v = recall_at(We, be), recall_at(Wv, bv)

print(f'{"":<20s}{"head":>8s}{"mid":>8s}{"tail":>8s}{"macro":>9s}   g_head / g_tail')
rep_bce('BCE 基线', rec_p, g_plain)
rep_bce('EQL v1', rec_e, g_eql)
rep_bce('EQLv2', rec_v, g_v2)

RESULTS['⑦ sigmoid: BCE 基线'] = rec_p
RESULTS['⑦ sigmoid: EQL v1'] = rec_e
RESULTS['⑦ sigmoid: EQLv2'] = rec_v

assert rec_e[TAIL].mean() > rec_p[TAIL].mean(), 'EQL v1 应抬高尾部召回'
assert rec_v[TAIL].mean() > rec_e[TAIL].mean(), 'EQLv2 应优于 EQL v1'
assert rec_v[TAIL].mean() > 1.5 * rec_p[TAIL].mean(), 'EQLv2 对尾部的提升应当显著'
assert g_v2[TAIL].mean() > g_plain[TAIL].mean() + 0.15, 'EQLv2 应把尾部的 g_j 拉回来'
assert rec_v[HEAD].mean() >= rec_p[HEAD].mean() - 0.02, 'EQLv2 不应牺牲头部'

print(f'\n✅ EQLv2 把尾部的 g_j 从 {g_plain[TAIL].mean():.3f} 拉到 {g_v2[TAIL].mean():.3f}'
      f'（目标 1.0）, 尾部召回 {rec_p[TAIL].mean():.3f} → {rec_v[TAIL].mean():.3f}'
      f'，**头部没掉**。')
print('   EQLv2 是一个**负反馈控制器**: g_j 低 → 正梯度放大到 (1+α)、负梯度衰减到 ~0;')
print('   一旦均衡回来, 加权自动退回中性。**不需要类别频率先验** —— 对不断新增类别的')
print('   TSR 类别表（200~500 项, 随法规更新）是决定性的优点。')
print('⚠️  前提: 这套机制是为 **sigmoid 多标签头** 设计的。softmax 头上各类 logit 相互竞争,')
print('    稀有类不会被独立压到 -∞, 该用 BAGS / logit adjustment 而不是 EQL。')"""),

    md("""## 5 · Logit adjustment：零训练成本的一行修正

推导：`p_bal(y|x) ∝ p_train(y|x)/π_c` → logit 空间里就是 **减去 `τ·log π_c`**。
`τ=1` 是理论最优（模型完美拟合的前提下），实际最优 τ 常落在 0.5–1.0。"""),

    code(r"""pi = train_counts / train_counts.sum()            # 训练集类别先验 π_c
print('π_c =', np.round(pi, 5))
print('-log π_c =', np.round(-np.log(pi), 2), '  ← 稀有类被抬得更多')

print(f'\n{"τ":>6s}{"head":>9s}{"mid":>9s}{"tail":>9s}{"macro":>10s}')
best_tau, best_macro = 0.0, -1
for tau in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
    per = per_class_acc(W0, b0, adj=-tau * np.log(pi))
    if per.mean() > best_macro: best_tau, best_macro = tau, per.mean()
    mark = ''
    print(f'{tau:>6.2f}{per[HEAD].mean():>9.3f}{per[MID].mean():>9.3f}'
          f'{per[TAIL].mean():>9.3f}{per.mean():>10.3f}{mark}')
print(f'→ 最优 τ = {best_tau}  (macro {best_macro:.3f})')

per_la = per_class_acc(W0, b0, adj=-1.0 * np.log(pi))
report('⑤ logit adjustment τ=1', per_la)
assert np.allclose(per_class_acc(W0, b0, adj=-0.0 * np.log(pi)), per0), 'τ=0 必须退回原预测'
assert per_la[TAIL].mean() > per0[TAIL].mean() + 0.25, '推理时先验校正应大幅抬高尾部'
assert per_la[HEAD].mean() < per0[HEAD].mean(), '代价是头部下降 —— **工作点被移动了**'
print(f'\n⚠️  代价: 头部 {per0[HEAD].mean():.3f} → {per_la[HEAD].mean():.3f}。'
      '**调 logit = 移动 PR 工作点**, 原来的 score 阈值与 NMS 全部失效, 必须重新标定。')
print('    在 TSR 里尤其危险: 把稀有类分数抬上去 = "停车让行"误报增加 = 不必要的急刹。')
print('    正确做法: **按类别分别标定阈值, 安全关键类用更保守的 τ**。')

# 训练时版本: 把 τ·log π 加进训练的 logit（推理时什么都不做）
Wla, bla = train_softmax(Htr, ytr, prior_logit=1.0 * np.log(pi))
report('⑤ logit-adjusted loss', per_class_acc(Wla, bla))
print('\n✅ 两个版本理论上等价; 训练时版本通常更稳（模型能自己适应这个偏置），代价是要重训。')
print('   **工程顺序: 先用推理时版本白嫖一次探天花板, 再决定要不要花一次训练。**')"""),

    md("""## 6 · 解耦训练：表示是好的，坏掉的是分类器

两个五分钟就能做的诊断：
1. **`‖w_c‖` 与 `log n_c` 的相关系数**——高（>0.8）说明分类器被频率带偏
2. **NCM（最近类均值）准确率 vs 模型分类头准确率**——NCM 明显更高 ⇒ 表示没坏

然后是三种阶段二方案：**τ-normalize（零成本）/ cRT（只重训分类头）/ LWS**。"""),

    code(r"""# ── 诊断 ①: 分类器权重范数 vs 样本数 ──────────────────────────
norms = np.linalg.norm(W0, axis=0)
corr = float(np.corrcoef(np.log(train_counts), norms)[0, 1])
print(f"{'类别':>6s}{'n_c':>8s}{'‖w_c‖':>10s}")
for c in range(C):
    print(f'{c:>6d}{train_counts[c]:>8d}{norms[c]:>10.3f}')
print(f'\n**corr(‖w_c‖, log n_c) = {corr:.3f}**  ← >0.75 就是"分类器被频率带偏"的典型指纹')
assert corr > 0.70, f'长尾训练下应当出现强相关, 实际 {corr:.3f}'

# ── 诊断 ②: NCM —— 完全不用分类器, 只用特征均值 ────────────────
mu_c = np.stack([Htr[ytr == c].mean(0) for c in range(C)])
mu_n = mu_c / np.linalg.norm(mu_c, axis=1, keepdims=True)
He_n = Hte / np.linalg.norm(Hte, axis=1, keepdims=True)
pred_ncm = (He_n @ mu_n.T).argmax(1)
per_ncm = np.array([(pred_ncm[yte == c] == c).mean() for c in range(C)])
report('⑥ NCM（只用表示）', per_ncm)
assert per_ncm[TAIL].mean() > per0[TAIL].mean() + 0.15, \
    'NCM 的尾部应显著优于模型自己的分类头 —— 这就是"表示没坏"的证据'
print(f'\n✅ **NCM 尾部 {per_ncm[TAIL].mean():.3f} vs 分类头 {per0[TAIL].mean():.3f}** ——')
print('   同一份特征, 不训练任何分类器就能做得更好 ⇒ **坏掉的是最后那一层**。')

# ── 阶段二 A: τ-normalized（零训练成本）───────────────────────
print(f'\n{"τ-norm τ":>10s}{"head":>9s}{"mid":>9s}{"tail":>9s}{"macro":>10s}')
for tau in [0.0, 0.3, 0.5, 0.7, 1.0]:
    Wn = W0 / (norms ** tau)
    per = per_class_acc(Wn, np.zeros(C))
    print(f'{tau:>10.2f}{per[HEAD].mean():>9.3f}{per[MID].mean():>9.3f}'
          f'{per[TAIL].mean():>9.3f}{per.mean():>10.3f}')
Wn7 = W0 / (norms ** 0.7)
report('⑥ τ-normalized τ=0.7', per_class_acc(Wn7, np.zeros(C)))
per_tau0 = per_class_acc(W0, np.zeros(C))
print(f'\n💡 注意 τ=0 那一行（macro {per_tau0.mean():.3f}）已经比基线（{per0.mean():.3f}）高很多 ——')
print('   因为它把 **bias b 丢掉了**, 而 bias 恰恰编码了类别先验。')
print('   "扔掉 bias" 本身就是一次粗糙的先验校正, 这与第 5 节是同一件事的两种做法。')
assert per_tau0.mean() > per0.mean() + 0.05, '丢掉 bias 本身就有先验校正效果'

# ── 阶段二 B: cRT —— 冻结表示, 用平衡采样重训分类器 ─────────────
bal_w = (1.0 / train_counts)[ytr]                 # 类别平衡采样 ≡ 权重 1/n_c
Wcrt, bcrt = train_softmax(Htr, ytr, sample_w=bal_w)
report('⑥ cRT (重训分类头)', per_class_acc(Wcrt, bcrt))

# 对照: 从头就用平衡采样训练（表示也被重采样"污染"）—— 这里表示层是固定的,
# 所以两者数值相同; 真实网络中 cRT 会更好, 因为 backbone 保住了原分布的多样性。
assert RESULTS['⑥ cRT (重训分类头)'][TAIL].mean() > per0[TAIL].mean() + 0.2
assert RESULTS['⑥ τ-normalized τ=0.7'][TAIL].mean() > per0[TAIL].mean() + 0.2
print('\n✅ 三种阶段二方案（τ-norm 零成本 / cRT 极低成本 / LWS）收益接近 ——')
print('   说明它们做的是**同一件事**: 把被频率带偏的决策边界拉回来。')
print('⚠️  真实网络里 cRT 还有一层额外好处: **表示用原分布学（多样性最大），**')
print('   **分类器用平衡数据学（决策边界正确）** —— 重采样从头训会损害前者。')"""),

    md("""## 7 · 全方法对比：尾部类召回一览

把所有方法放在同一张表里。**注意 sigmoid 组（BCE / EQL / EQLv2）与 softmax 组
不可直接比较**——指标定义不同（前者是 score@0.3 的召回，后者是 argmax 准确率），
所以分两块看各自的 Δ。"""),

    code(r"""def table(keys, title, base_key):
    base = RESULTS[base_key]
    print(f'\n=== {title} ===')
    print(f'{"方法":<26s}{"head":>8s}{"mid":>8s}{"tail":>8s}{"macro":>9s}'
          f'{"Δtail":>9s}{"Δhead":>9s}')
    for k in keys:
        p = RESULTS[k]
        print(f'{k:<26s}{p[HEAD].mean():>8.3f}{p[MID].mean():>8.3f}{p[TAIL].mean():>8.3f}'
              f'{p.mean():>9.3f}{p[TAIL].mean()-base[TAIL].mean():>+9.3f}'
              f'{p[HEAD].mean()-base[HEAD].mean():>+9.3f}')

soft = [k for k in RESULTS if not k.startswith('⑦')]
table(soft, 'softmax 头（指标 = 平衡测试集上的 argmax 准确率）', '① baseline (plain CE)')
table([k for k in RESULTS if k.startswith('⑦')],
      'sigmoid 多标签头（指标 = score@0.3 的召回）', '⑦ sigmoid: BCE 基线')

# 方法不是可加的：叠加会过度校正
Wstack, bstack = train_softmax(Htr, ytr, sample_w=sw,
                               class_w=cb_weights(train_counts, 0.999))
per_stack = per_class_acc(Wstack, bstack, adj=-1.0 * np.log(pi))
best_single = max(RESULTS[k].mean() for k in soft if k != '⓪ oracle (平衡数据)')
print(f'\nRFS + CB Loss + logit adjustment **三个叠加**: '
      f'head {per_stack[HEAD].mean():.3f} tail {per_stack[TAIL].mean():.3f} '
      f'macro {per_stack.mean():.3f}')
print(f'单用最好的方法 macro = {best_single:.3f}')
assert per_stack.mean() < best_single + 0.02, \
    '三个叠加不应显著优于单用最好的 —— 它们本质上在做同一件事'
assert per_stack[HEAD].mean() < per0[HEAD].mean() - 0.1, '叠加会**过度校正**, 头部被压'
print('⚠️  **这些方法的收益不是可加的**: 它们都在把有效类别先验拉平, 叠加 = 过度校正')
print('    （尾部误检暴涨、头部被压）。**选一个, 把它的强度参数 (p/β/τ) 调好**,')
print('    而不是全开 —— 这个认识能在消融实验里省掉一半无效组合。')"""),

    md("""## ✏️ 练习 1：真正的 repeat factor sampling（多标签版）

上面每张图只含一个类，太简单了。现在实现检测里真正的版本：

`rfs_image_factors(image_labels, n_images, t)`
- `image_labels`: `List[Set[int]]`，第 i 张图包含的类别集合
- 先算 **图像频率** `f_c = 含类别 c 的图像数 / n_images`
- `r_c = max(1, sqrt(t / f_c))`
- **`r_i = max_{c ∈ i} r_c`**（图内取最大，不是平均！空集的图 `r_i = 1.0`）
- 返回 `(r_c: np.ndarray[C], r_i: np.ndarray[n_images])`

`C` 由标签里出现过的最大类别 id + 1 决定。"""),

    code(r"""def rfs_image_factors(image_labels, n_images, t):
    # TODO: ① 统计每个类出现在多少张图里 -> f_c
    #       ② r_c = max(1, sqrt(t/f_c))；f_c = 0 的类记 r_c = 1.0（数据里没有它）
    #       ③ r_i = max_{c in i} r_c，空集图 r_i = 1.0
    raise NotImplementedError"""),

    code(r"""# —— 练习 1 自测 ——
imgs = [{0}, {0}, {0}, {0, 1}, {0, 2}, {1}, {2, 3}, {0}, {0}, {0}]   # 10 张图, 4 个类
rc, ri = rfs_image_factors(imgs, len(imgs), t=0.5)
# f = [0.8, 0.2, 0.2, 0.1]
assert rc.shape == (4,) and ri.shape == (10,)
assert np.isclose(rc[0], 1.0), 'f_0=0.8 > t=0.5 -> 不重复'
assert np.isclose(rc[1], np.sqrt(0.5 / 0.2)), rc[1]
assert np.isclose(rc[3], np.sqrt(0.5 / 0.1)), rc[3]
assert np.isclose(ri[3], max(rc[0], rc[1])), '图内取 **最大**'
assert np.isclose(ri[6], max(rc[2], rc[3])) and np.isclose(ri[6], rc[3])
assert np.isclose(ri[0], 1.0)
# **共现污染**: 第 4 张图因为含稀有类 2 而被重复, 里面的常见类 0 也跟着被过采样
assert ri[4] > 1.0 and 0 in imgs[4]
# t 越大, 过采样越强
rc2, _ = rfs_image_factors(imgs, len(imgs), t=2.0)
assert (rc2 >= rc).all() and rc2[3] > rc[3]
print('f_c =', np.round(np.array([sum(c in s for s in imgs) for c in range(4)]) / 10, 2))
print('r_c =', np.round(rc, 3))
print('r_i =', np.round(ri, 3))
print('✅ 练习 1 通过：**图像频率 / 开方 / 图内取最大** —— 三个设计点缺一不可。')
print('   注意第 4 张图（含常见类0 + 稀有类2）被重复 %.2f 次 → **共现污染**。' % ri[4])"""),

    md("""## ✏️ 练习 2：Class-Balanced 权重与"等效 β"

实现 `cb_weight_and_equiv(counts, beta, normalize=True)`，返回
`(w, p_equiv)`：
- `w`：CB 权重 `∝ (1-β)/(1-β^n_c)`；`normalize=True` 时把均值归一到 1
- `p_equiv`：把 CB 权重近似成幂律 `w_c ∝ n_c^(-p)` 时的等效指数 p
  （用 `head` 与 `tail` 两端做两点估计：`p = -(log w_tail - log w_head)/(log n_tail - log n_head)`，
  其中 head/tail 取 `counts` 的最大值与最小值对应的权重）

`p_equiv` 的意义：**p=0 等价不加权，p=1 等价反频率**——它把 β 翻译成人能直觉理解的强度。"""),

    code(r"""def cb_weight_and_equiv(counts, beta, normalize=True):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 2 自测 ——
w_lo, p_lo = cb_weight_and_equiv(train_counts, 0.9)
w_hi, p_hi = cb_weight_and_equiv(train_counts, 0.999999)
w_mid, p_mid = cb_weight_and_equiv(train_counts, 0.999)
assert np.isclose(w_lo.mean(), 1.0) and np.isclose(w_hi.mean(), 1.0)
assert p_lo < 0.15, f'β 很小时几乎等价不加权, p≈0, 实际 {p_lo:.3f}'
assert p_hi > 0.95, f'β→1 时等价反频率, p≈1, 实际 {p_hi:.3f}'
assert p_lo < p_mid < p_hi, '等效强度应随 β 单调递增'
assert (np.diff(w_mid) > 0).all(), 'counts 递减 -> 权重应递增'
w_raw, _ = cb_weight_and_equiv(train_counts, 0.999, normalize=False)
assert np.allclose(w_raw / w_raw.mean(), w_mid), 'normalize 只是整体缩放'
print(f"{'β':>12s}{'等效指数 p':>12s}   解读")
for beta in [0.0, 0.9, 0.99, 0.999, 0.9999, 0.999999]:
    _, p = cb_weight_and_equiv(train_counts, beta)
    tag = '≈不加权' if p < 0.15 else ('≈反频率' if p > 0.9 else '中间强度')
    print(f'{beta:>12.6f}{p:>12.3f}   {tag}')
print('✅ 练习 2 通过：**β 是"不加权 ↔ 反频率"之间的连续旋钮**, 用等效 p 来读它最直观。')"""),

    md("""## ✏️ 练习 3：Logit adjustment（推理版 + 训练版）

实现 `logit_adjust(logits, priors, tau=1.0, mode='infer')`：
- `mode='infer'`：返回 `logits - tau*log(priors)`（推理时先验校正）
- `mode='train'`：返回 `logits + tau*log(priors)`（logit-adjusted loss 用的偏置版）
- `priors` 会被先归一化成概率（允许传入原始计数）
- `tau=0` 时两种模式都必须原样返回 logits"""),

    code(r"""def logit_adjust(logits, priors, tau=1.0, mode='infer'):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 3 自测 ——
z = Hte @ W0 + b0
assert np.allclose(logit_adjust(z, train_counts, tau=0.0), z), 'τ=0 必须原样返回'
assert np.allclose(logit_adjust(z, train_counts, tau=0.0, mode='train'), z)
a1 = logit_adjust(z, train_counts, tau=1.0)
a2 = logit_adjust(z, train_counts / train_counts.sum(), tau=1.0)
assert np.allclose(a1, a2), 'priors 应当被自动归一化（传计数或概率都行）'
assert np.allclose(logit_adjust(z, train_counts, 1.0, 'train'),
                   2 * z - logit_adjust(z, train_counts, 1.0, 'infer')), 'train/infer 反号'
# 校正后尾部类应当被抬起来
acc_before = np.array([(z.argmax(1)[yte == c] == c).mean() for c in range(C)])
acc_after = np.array([(a1.argmax(1)[yte == c] == c).mean() for c in range(C)])
assert acc_after[TAIL].mean() > acc_before[TAIL].mean() + 0.25
assert acc_after[HEAD].mean() < acc_before[HEAD].mean(), '代价是头部下降'
print(f"{'τ':>6s}{'head':>9s}{'tail':>9s}{'macro':>10s}")
for tau in [0.0, 0.5, 1.0, 1.5]:
    aa = logit_adjust(z, train_counts, tau=tau)
    pc = np.array([(aa.argmax(1)[yte == c] == c).mean() for c in range(C)])
    print(f'{tau:>6.1f}{pc[HEAD].mean():>9.3f}{pc[TAIL].mean():>9.3f}{pc.mean():>10.3f}')
print('✅ 练习 3 通过：**零训练成本、一行代码**, 应该是你遇到长尾时第一个试的东西。')"""),

    md("""## ✏️ 练习 4：方法选择决策树

把讲解最后一节的决策树代码化。实现 `choose_method(diag)`，`diag` 含：
- `tail_recall`（尾部类的召回，框有没有出来）
- `tail_score_ok`（bool：尾部类的分数是否够高、能过阈值）
- `tail_confused_with_head`（bool：尾部主要被错分成相似的头部类）
- `tail_min_images`（尾部类最少的训练图像数）
- `w_norm_corr`（‖w_c‖ 与 log n_c 的相关系数）

返回 `{'diagnosis': str, 'actions': [str, ...]}`，`actions` **按成本递增排序**。
判定优先级（从上往下，命中即返回）：
1. `tail_min_images < 30` → `'信息量不足'`，actions = `['copy-paste 合成', '定向挖掘补数据']`
2. `tail_recall < 0.1` → `'检出问题'`，actions = `['检查标签分配', '检查漏标', '按小目标处理']`
3. `tail_confused_with_head` → `'特征不可分'`，actions = `['层次标签', '高分辨率 crop / 两级架构', '难例挖掘']`
4. `not tail_score_ok` 且 `w_norm_corr > 0.75` → `'分类器先验偏置'`，
   actions = `['logit adjustment', 'τ-normalize', 'cRT', 'RFS / EQLv2']`
5. 否则 → `'无明显长尾病征'`，actions = `['先检查评测口径（macro/分桶）']`"""),

    code(r"""def choose_method(diag):
    # TODO: 按 1→5 的优先级判定，命中即返回
    raise NotImplementedError"""),

    code(r"""# —— 练习 4 自测 ——
base_diag = dict(tail_recall=0.55, tail_score_ok=False, tail_confused_with_head=False,
                 tail_min_images=800, w_norm_corr=0.87)
r = choose_method(base_diag)
assert r['diagnosis'] == '分类器先验偏置' and r['actions'][0] == 'logit adjustment', r
assert r['actions'][-1] == 'RFS / EQLv2', '成本递增: 零成本的在前'

d = dict(base_diag, tail_min_images=12)
assert choose_method(d)['diagnosis'] == '信息量不足', '样本太少时一切重加权都无效'
assert choose_method(d)['actions'] == ['copy-paste 合成', '定向挖掘补数据']

d = dict(base_diag, tail_recall=0.03)
assert choose_method(d)['diagnosis'] == '检出问题'
assert '检查标签分配' in choose_method(d)['actions']

d = dict(base_diag, tail_confused_with_head=True)
assert choose_method(d)['diagnosis'] == '特征不可分'

d = dict(base_diag, tail_score_ok=True, w_norm_corr=0.2)
assert choose_method(d)['diagnosis'] == '无明显长尾病征'

# 优先级：样本太少 **压过** 一切
d = dict(tail_recall=0.02, tail_score_ok=False, tail_confused_with_head=True,
         tail_min_images=8, w_norm_corr=0.95)
assert choose_method(d)['diagnosis'] == '信息量不足'

# 用本 notebook 真实测出来的数诊断一次
real = dict(tail_recall=float(rec_p[TAIL].mean()),
            tail_score_ok=bool(rec_p[TAIL].mean() > 0.5),
            tail_confused_with_head=False,
            tail_min_images=int(train_counts.min()),
            w_norm_corr=corr)
print('用本 notebook 的真实诊断量:', json.dumps(
    {k: (round(v, 3) if isinstance(v, float) else v) for k, v in real.items()},
    ensure_ascii=False))
print('→', json.dumps(choose_method(real), ensure_ascii=False, indent=2))
print('✅ 练习 4 通过：**先诊断再开药** —— 面试问"长尾怎么办"时能分层作答的人极少。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code(r"""# 练习 1 参考答案
def rfs_image_factors(image_labels, n_images, t):
    C_ = max((max(s) for s in image_labels if s), default=-1) + 1
    img_cnt = np.zeros(C_, dtype=float)
    for s in image_labels:
        for c in s:
            img_cnt[c] += 1
    f_c = img_cnt / n_images
    with np.errstate(divide='ignore', invalid='ignore'):
        r_c = np.where(f_c > 0, np.maximum(1.0, np.sqrt(t / np.maximum(f_c, 1e-12))), 1.0)
    r_i = np.array([max((r_c[c] for c in s), default=1.0) for s in image_labels])
    return r_c, r_i"""),

    code(r"""# 练习 2 参考答案
def cb_weight_and_equiv(counts, beta, normalize=True):
    n = np.asarray(counts, float)
    En = np.ones_like(n) if beta <= 0 else (1.0 - beta ** n) / (1.0 - beta)
    w = 1.0 / En
    if normalize:
        w = w / w.mean()
    i_hi, i_lo = int(np.argmax(n)), int(np.argmin(n))       # 样本最多 / 最少的类
    dn = np.log(n[i_lo]) - np.log(n[i_hi])
    p = 0.0 if abs(dn) < 1e-12 else -(np.log(w[i_lo]) - np.log(w[i_hi])) / dn
    return w, float(p)"""),

    code(r"""# 练习 3 参考答案
def logit_adjust(logits, priors, tau=1.0, mode='infer'):
    p = np.asarray(priors, float)
    p = p / p.sum()
    delta = tau * np.log(p)
    return logits - delta if mode == 'infer' else logits + delta"""),

    code(r"""# 练习 4 参考答案
def choose_method(diag):
    if diag['tail_min_images'] < 30:
        return {'diagnosis': '信息量不足',
                'actions': ['copy-paste 合成', '定向挖掘补数据']}
    if diag['tail_recall'] < 0.1:
        return {'diagnosis': '检出问题',
                'actions': ['检查标签分配', '检查漏标', '按小目标处理']}
    if diag['tail_confused_with_head']:
        return {'diagnosis': '特征不可分',
                'actions': ['层次标签', '高分辨率 crop / 两级架构', '难例挖掘']}
    if (not diag['tail_score_ok']) and diag['w_norm_corr'] > 0.75:
        return {'diagnosis': '分类器先验偏置',
                'actions': ['logit adjustment', 'τ-normalize', 'cRT', 'RFS / EQLv2']}
    return {'diagnosis': '无明显长尾病征', 'actions': ['先检查评测口径（macro/分桶）']}"""),

    md("""---
## 🧪 真实工程胶囊：长尾问题的十分钟诊断 + 按成本递增的处方"""),

    code(r"""RECIPE = r'''
# ============ 第 0 步：先把评测改对（不然优化的是错的东西）============
# 报告必须包含: macro AP + frequent/common/rare 三桶分项 + 逐类 AP
# LVIS 口径: rare < 10 imgs, common 10-100, frequent > 100（**用图像数, 不是实例数**）

# ============ 第 1 步：十分钟诊断（决定用哪一类方法）============
# ① 尾部类 recall 是不是也 ≈ 0？  -> 是: **检出问题**, 重加权救不了
#    去查: 标签分配（尾部框分到正样本了吗）/ anchor 尺度 / 是否同时是小目标 / 是否漏标严重
# ② ‖w_c‖ 与 log(n_c) 的相关系数
import torch, numpy as np
W = model.bbox_head.cls_convs[-1].weight.detach()      # 或 roi_head.bbox_head.fc_cls.weight
norms = W.flatten(1).norm(dim=1).cpu().numpy()
corr  = np.corrcoef(np.log(class_counts), norms)[0, 1]
print("corr(||w_c||, log n_c) =", corr)                # > 0.8 -> **分类器被频率带偏**
# ③ NCM 诊断: 冻结 backbone, 用每类特征均值做最近邻分类
#    NCM 尾部准确率 >> 模型分类头 -> **表示没坏, 坏的是最后一层**

# ============ 第 2 步：按成本递增开药 ============
# --- 零成本（半小时, 不重训）---
tau = 1.0
logits_adj = logits - tau * torch.log(torch.tensor(class_priors))     # logit adjustment
W_norm = W / W.flatten(1).norm(dim=1).view(-1,1,1,1) ** 0.7           # τ-normalize
# ⚠️ 分数分布整体平移 -> **score 阈值与 NMS 必须重新标定**, 按类别分别定阈值

# --- 低成本（几分钟, 只重训分类头）---
# cRT: 冻结 backbone + neck, 只用 class-balanced sampling 重训分类分支
for p in model.backbone.parameters(): p.requires_grad = False
for p in model.neck.parameters():     p.requires_grad = False

# --- 改训练（一次完整训练）---
# mmdet: repeat factor sampling
dataset = dict(type='ClassBalancedDataset', oversample_thr=1e-3, dataset=dict(...))
#   ⚠️ epoch 变长 1.5~2x -> **必须同步调 max_iters 与 lr schedule**, 否则消融不公平
# EQLv2（sigmoid 头必选; 无需类别频率先验, 对不断新增类别友好）
loss_cls = dict(type='EQLV2Loss', num_classes=NUM_CLASSES, gamma=12, mu=0.8, alpha=4.0)

# --- 最贵但唯一提高信息量上限 ---
# copy-paste 稀有类实例（C56 m03）+ 定向挖掘补数据（C58 m03-m05）
# 架构: 两级方案（类别无关检测 -> 高分辨率 crop 分类），把长尾搬出检测器
#   代价: **级联召回 = 检测召回 x 分类准确率**（0.95 x 0.95 = 0.90）

# ============ 红线 ============
# 1. **Focal Loss 不是长尾解法** —— 它按难度加权, 不看类别频率
# 2. **这些方法收益不可加** —— RFS + CB + logit adj 叠加 = 过度校正, 选一个调好
# 3. **RFS 改了 epoch 长度** —— 不同步调 iteration 数的消融全部无效
# 4. TSR: 抬高稀有类分数 = "停车让行"误报增加 = 急刹。**安全关键类用更保守的 τ**
'''
print(RECIPE)
for k in ['corr(||w_c||', 'NCM', 'logit adjustment', 'τ-normalize', 'cRT',
          'ClassBalancedDataset', 'EQLV2Loss', '级联召回', 'Focal Loss 不是长尾解法']:
    assert k in RECIPE, k
print('✅ 胶囊覆盖: 评测口径 → 十分钟诊断 → 按成本递增的四档处方 → 四条红线。')"""),

    md("""### 小结

- **检测里有两种不平衡，解法互不替代**：前景-背景（位置级，每张图都有，1:280~1:2800，
  用 Focal/OHEM/分配）vs 类别间（数据集级，用 RFS/CB/EQL/logit adj/解耦）。
  **「长尾怎么办」答「用 Focal Loss」是把两个问题混为一谈。**
- **RFS 的四个设计点**：图像频率 `f_c`、开方（温和过采样，不是完全拉平）、
  图内取最大、每 epoch 随机取整。副作用：共现污染 + epoch 长度变化（消融不公平的常见来源）。
- **CB Loss 的 β 是连续旋钮**：`E_n=(1-β^n)/(1-β)`，β→0 等价不加权、β→1 等价反频率，
  `1/(1-β)` 就是「多少样本算饱和」。**LDAM 单用几乎没涨，必须配 DRW。**
- **稀有类是被负梯度淹死的**：sigmoid 头下尾部类累积正负梯度比远低于头部，
  logit 被压 → score 上不去 → 框定位准也输不出来。**EQL 屏蔽、EQLv2 在线均衡到 1:1**，
  后者不需要频率先验，对类别表持续增长的 TSR 特别合适。
- **表示是好的，坏掉的是分类器**：`corr(‖w_c‖, log n_c) > 0.8` + `NCM 尾部远优于分类头`
  是两个五分钟诊断。对应处方：τ-normalize（零成本）、cRT（只重训分类头）、LWS。
- **logit adjustment 是第一个该试的**：推理时减 `τ·log π_c`，零训练成本。
  代价是**工作点被移动**——score 阈值与 NMS 必须重新标定，安全关键类要更保守。
- **这些方法收益不可加**：它们都在拉平有效类别先验，叠加 = 过度校正。**选一个，调好强度。**
- **先诊断再开药**：样本太少（<30 张）→ 只能补数据；recall≈0 → 检出问题；
  被错分成头部类 → 特征不可分；score 低 + 权重范数相关 → 分类器先验偏置。

下一站：**模块 02 · 难例挖掘** —— 在已有数据里找出该重点学的那一小撮，
以及为什么「挖掘过头会把噪声标签当难例，反而毁掉模型」。"""),
]
