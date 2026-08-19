# -*- coding: utf-8 -*-
"""C54 模块 04 · 收敛难题与 DETR 家族演进。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03（匈牙利匹配 / 集合损失 / object query）；C53 模块 04（RT-DETR）可后置"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_convergence_family.ipynb'),
    ("核心参考", "Deformable DETR (ICLR&#39;21)、DN-DETR (CVPR&#39;22)、DINO (ICLR&#39;23)、Group DETR / H-DETR / Co-DETR (ICCV&#39;23)"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("roots", "500 epoch 从哪来：把「慢」拆成两个可以分别修的根因", "".join([
        P("原版 DETR 在 COCO 上要训 <strong>500 epoch</strong> 才追平 Faster R-CNN 的 1× 配方（12 epoch）。这是 40 倍的训练成本差距，也是 2020–2022 年整个 DETR 家族演进的唯一驱动力。",
          "但「慢」不是一个可以直接修的东西。<strong>面试里能立刻拉开差距的答法，是把「慢」拆成两个彼此独立的根因</strong>——它们发生在模型的不同部位、用不同的指标度量、由不同的后续工作解决。只会说「DETR 收敛慢」的人和能说出这两条的人，水平差一个档次。"),
        H3("根因 ①：cross-attention 在初期近似均匀，梯度被摊薄到全图"),
        P('decoder 的 <span class="term">cross-attention</span>（交叉注意力）要做的事是：让每个 object query 在 HW 个空间位置里找到自己该负责的那个目标。但在训练刚开始时，Q/K 投影是随机初始化的小权重，点积结果接近 0，softmax 之后<strong>注意力权重近似均匀分布</strong>——每个空间位置分到大约 1/HW 的权重。',
          "这意味着什么？<strong>反向传播时，落在目标区域上的梯度只占总梯度的一个极小比例，其余全部打在背景上。</strong>而且这个比例随目标变小而急剧恶化。"),
        MATH("\\alpha_0 \\;=\\; \\frac{\\text{目标在特征图上占的格子数}}{H \\cdot W} \\;=\\; \\frac{(w/s)\\cdot(h/s)}{H \\cdot W}"),
        TABLE(["场景（1333×800 输入，C5 stride 32）", "目标像素尺寸", "占特征图格子", "初始注意力质量 α₀"], [
            ["大目标（近处车辆）", "256×256", "8×8 = 64", "<strong>6.2%</strong>"],
            ["中目标（行人）", "64×128", "2×4 = 8", "0.78%"],
            ["COCO 平均目标", "≈100×100", "≈9.8", "0.95%"],
            ["<strong>TSR：30 m 外的限速牌</strong>", "<strong>32×32</strong>", "1×1 = 1", "<strong>0.098%</strong>"],
            ["<strong>TSR：60 m 外的限速牌</strong>", "<strong>16×16</strong>", "0.5×0.5 = 0.25", "<strong>0.024%</strong>"],
        ]),
        P("最后两行就是这门课要反复回到的地方：<strong>在交通标志检测里，原版 DETR 的 cross-attention 初期把 99.98% 的梯度打在了背景上。</strong>模型必须靠这 0.02% 的信号慢慢把注意力「拧」到标志上——这就是 500 epoch 的第一半。"),
        DUAL(
            "为什么这不是「学一会儿就好了」？因为注意力要变尖锐，靠的是 Q/K 投影学到「这个 query 的内容和那个位置的特征相似」。可是<em>在注意力还没变尖锐之前，query 拿到的是全图平均特征，根本形不成有区分度的内容</em>——这是一个鸡生蛋的循环。Deformable DETR 论文里画的注意力图显示，要训到约 <strong>10 万次迭代</strong>注意力才明显稀疏化。",
            "更精确地说：<strong>这是一个「初始化处于高熵鞍区」的优化问题</strong>。softmax 注意力的对数几率需要从 0 增长到 ln((HW−n)/n) 才能让目标区域占到一半的注意力质量。目标越小，n 越小，需要的对数几率增量越大——<em>而增长速率由梯度决定，梯度又正比于当前的注意力质量</em>。于是小目标陷入「信号弱→学得慢→信号仍弱」的自锁。notebook 里会用一个玩具模型把这个 epoch 数算出来，并复现「小目标需要的 epoch 数显著多于大目标」。",
        ),
        H3("根因 ②：二分匹配不稳定，优化目标每个 epoch 都在抖"),
        P("模块 01 已经指出了这个问题，这里给它一个精确的说法：<strong>同一张图的同一个 GT，在相邻两个 epoch 里可能被不同的 query 认领。</strong>一旦认领关系翻转，上个 epoch 被训练着去拟合「停车让行标志」的那个 query，这个 epoch 的目标变成了「背景」；而另一个一直在学背景的 query 突然被要求回归出一个精确的框。",
          "<strong>梯度方向不是变小，而是掉头。</strong>这与「学习率太大」的症状完全不同——损失曲线看起来在降，但每个 query 学到的东西被反复覆盖。"),
        TABLE(["", "根因 ① 注意力弥散", "根因 ② 匹配不稳定"], [
            ["发生在哪", "decoder 的 cross-attention", "损失函数的匹配步骤"],
            ["本质是什么", "<strong>梯度打在了错误的空间位置</strong>", "<strong>梯度指向了错误的目标</strong>"],
            ["怎么度量", "注意力落在 GT 框内的质量 α", "相邻 epoch 的匹配翻转率 φ"],
            ["谁修的", "<strong>Deformable DETR</strong>（可变形采样 + 多尺度）", "<strong>DN-DETR / DINO</strong>（去噪 query 绕开匹配）"],
            ["收益", "500 → 50 epoch", "50 → 12 epoch"],
            ["修完另一个还在吗", "<strong>在</strong>（Deformable DETR 的匹配依然会翻转）", "<strong>在</strong>（DN 不改注意力机制）"],
        ]),
        CALLOUT("intuition", "最后一行是这一节的核心：<strong>两个根因彼此正交，所以两次收益可以相乘而不是相加</strong>。这解释了为什么 DINO = Deformable 的多尺度采样 + DN 的稳定监督，能在 12 epoch 拿到 49.0 AP——它同时修好了「往哪看」和「学什么」。<em>面试里如果只答出一个根因，追问「那 DN-DETR 又解决了什么」时就会卡住。</em>"),
        CALLOUT("warn", "有一个常见的错误归因：把 DETR 收敛慢归结为「Transformer 需要大数据 / 缺少归纳偏置」。<strong>这个说法太笼统，而且被后续工作证伪了</strong>——DINO 用的还是 Transformer、还是从 ImageNet 预训练的 ResNet-50、还是 COCO 那 118k 张图，12 epoch 就到了 49 AP。<em>真正被修好的是注意力的空间稀疏性和监督信号的稳定性，不是「归纳偏置」这种不可操作的东西。</em>"),
    ])),
    ("deform", "Deformable Attention：把 O(HW) 的全局搜索换成 K 个可学采样点", "".join([
        P('<span class="term">Deformable attention</span>（可变形注意力）的想法一句话就能说完：<strong>与其让 query 和全图 HW 个 key 做点积再 softmax，不如让 query 直接预测「我要看哪 K 个点」，只在这 K 个点上采样加权。</strong>'),
        MATH("\\text{MSDeformAttn}(z_q, \\hat{p}_q, \\{x^l\\}) = \\sum_{m=1}^{M} W_m \\Bigg[ \\sum_{l=1}^{L} \\sum_{k=1}^{K} A_{mlqk} \\cdot W'_m\\, x^l\\big(\\phi_l(\\hat{p}_q) + \\Delta p_{mlqk}\\big) \\Bigg]")
        ,
        P("符号逐个解释，每一个都对应一个设计决策："),
        TABLE(["符号", "含义", "为什么这么设计"], [
            ["<code>z_q</code>", "query 的内容向量", "偏移与权重<strong>只由它产生</strong>"],
            ["<code>p̂_q</code>", "<strong>reference point</strong>（参考点，归一化 [0,1]²）", "给 query 一个空间先验；两阶段版本里它来自 encoder 提案"],
            ["<code>Δp_mlqk</code>", "第 m 头、第 l 层、第 k 个采样点的偏移", "<strong>由 z_q 线性预测</strong>，可学；双线性插值让它可微"],
            ["<code>A_mlqk</code>", "采样点的注意力权重，对 L·K 做 softmax", "<strong>也由 z_q 线性预测</strong>——不做 Q·K 点积"],
            ["<code>x^l</code>", "第 l 层特征图", "L=4 个尺度共享同一套 query"],
            ["<code>φ_l</code>", "把归一化坐标映射到第 l 层的像素坐标", "让同一个参考点能跨尺度采样"],
        ]),
        CALLOUT("intuition", "<strong>表里最容易被忽略、也最容易在面试里拿分的一行是 <code>A_mlqk</code>：可变形注意力的权重不是 query 和 key 的相似度，而是 query 自己「凭空」输出的一组数。</strong>换句话说它<em>放弃了内容匹配</em>，只保留了「加权求和一小撮位置」这个骨架。这就是它便宜的根本原因（不需要算 HW 个点积），也是它的代价（权重与被采样位置的内容无关，靠采样位置本身来编码「看什么」）。<em>被问到「Deformable attention 还算不算注意力」时，这是标准答案。</em>"),
        ASCII("""DETR cross-attention（每个 query 看全图）
  query ──┬─► key(0,0)   w≈1/1025
          ├─► key(0,1)   w≈1/1025        HW = 25×41 = 1025 个 key
          ├─► ...                        权重来自 Q·K 点积，初期近似均匀
          └─► key(24,40) w≈1/1025        **梯度被摊薄 1025 份**

Deformable attention（每个 query 只看 L×K 个点）
  query z_q ──► 参考点 p̂_q ──► 线性层预测 Δp_1..Δp_K 与 A_1..A_K
                    │
                    ├─► 双线性采样 x(p̂_q + Δp_1)  × A_1
                    ├─► 双线性采样 x(p̂_q + Δp_2)  × A_2     L×K = 16 个点
                    ├─► ...                                 **权重不经过 Q·K**
                    └─► 双线性采样 x(p̂_q + Δp_K)  × A_K
  梯度同时流向两处：
    ① 被采样格点的特征值（4 个格点/采样点，由双线性权重分配）
    ② **采样位置 Δp 自己**（dv/dx, dv/dy 来自双线性插值的解析导数）
       ← 这是「学会往哪看」的直接通道，全局 attention 没有这条路""")
        ,
        DUAL(
            "第 ② 条是整个机制的灵魂。<strong>全局注意力只能间接地学「往哪看」</strong>——它得先把某个位置的特征学得和 query 相似，权重才会上去。<em>而可变形注意力有一条直达的梯度：如果往右挪 3 个像素能让损失变小，<code>dL/dΔp</code> 就直接告诉你往右挪。</em>这就是 500 epoch 变 50 epoch 的机制层解释。",
            "严格地说，这条梯度来自双线性插值的可微性。设采样点落在格点 <code>(x0,y0)</code> 的单元内，<code>dx = x−x0</code>，则 <code>∂v/∂x = (1−dy)(f₁₀−f₀₀) + dy(f₁₁−f₀₁)</code>——<strong>它正比于特征图在该处的局部差分，也就是特征的空间梯度</strong>。<em>推论：在特征平坦的区域（比如纯色天空），<code>∂v/∂Δp ≈ 0</code>，采样点收不到位置梯度，会停在原地不动。</em>notebook 里会把这个解析梯度写出来并用中心差分校验到 1e-7。",
        ),
        H3("计算量账：为什么 DETR 做不了多尺度而 Deformable 可以"),
        P("把与 query 数相乘的那部分算清楚（C=256，N_q=300，1333×800 输入）："),
        TABLE(["方案", "每个 query 的乘加量", "总量（×300 query）", "相对"], [
            ["DETR，单尺度 C5（HW=1025）", "2·1025·256 ≈ 5.2×10⁵", "1.6×10⁸", "1×"],
            ["DETR，若做 4 尺度（HW≈22148）", "2·22148·256 ≈ 1.1×10⁷", "<strong>3.4×10⁹</strong>", "<strong>21.6×</strong>"],
            ["Deformable，4 尺度 K=4", "L·K·C + C·(3·L·K) ≈ 1.6×10⁴", "4.9×10⁶", "<strong>0.03×</strong>"],
        ]),
        P("最后两行放在一起看就明白了：<strong>原版 DETR 不是「忘了」做多尺度，而是全局注意力在多尺度上的复杂度直接不可承受</strong>（encoder 的 self-attention 更是 O((HW)²)，4 尺度下会爆炸）。<em>可变形注意力把复杂度从「与特征图面积成正比」改成「与采样点数成正比」，多尺度才第一次变得免费。</em>这是一个「先有机制，才有能力」的经典例子。"),
        CALLOUT("warn", "别把可变形注意力和 <span class=\"term\">deformable convolution</span>（可变形卷积，DCN）混为一谈。<strong>DCN 是每个输出位置学一组偏移去采样输入，偏移由局部特征产生，本质仍是卷积；可变形注意力是每个 query（不绑定在特征图格点上）学一组偏移，并且带 softmax 权重与多尺度聚合。</strong><em>共同点只有「用双线性插值实现可学采样」这一条实现技巧。</em>面试里被追问区别时，答「query 不绑定空间位置 + 跨尺度 + 带注意力权重」这三点即可。"),
    ])),
    ("deform2", "Deformable DETR 的另外两件事：多尺度与两阶段", "".join([
        P("很多人把 Deformable DETR 的收益全部归给「可变形注意力」，这在面试里会被追问穿。<strong>论文的消融清楚地把收益拆成了四块，而且可变形注意力本身只是打开大门的那一块。</strong>"),
        TABLE(["组件", "做什么", "解决什么", "COCO AP（R50, 50 epoch）"], [
            ["DETR-DC5 基线（500 epoch）", "单尺度全局注意力", "—", "43.3"],
            ["<strong>+ 可变形注意力</strong>", "K 点采样替代全局", "梯度弥散；让多尺度成为可能", "—"],
            ["<strong>+ 多尺度（L=4）</strong>", "stride 8/16/32/64 共享 query", "<strong>小目标</strong>：AP_S 20.5 → 26.4", "43.8（<strong>50 epoch</strong>）"],
            ["<strong>+ 迭代框细化</strong>", "每层 decoder 在上一层框上出增量", "让参考点逐层逼近，采样越来越准", "45.4"],
            ["<strong>+ 两阶段</strong>", "encoder 出提案，top-K 作为参考点", "query 不再从零猜位置", "46.2"],
        ]),
        H3("多尺度：为什么它对 TSR 是生死问题而不是加分项"),
        P("原版 DETR 只用 C5（stride 32）。回到上一节的表：<strong>一个 60 米外、16×16 像素的限速牌，在 stride 32 的特征图上只占 0.25 个格子——它在数值上根本没有独立的特征向量</strong>，被邻域的路面、树木、天空混叠在同一个格子里。任何注意力机制都救不了「信息已经在下采样时被抹掉」这件事。"),
        TABLE(["特征层", "stride", "16×16 标志占几个格子", "32×32 标志占几个格子", "能不能被采样到"], [
            ["<strong>P3</strong>", "8", "<strong>2×2 = 4</strong>", "4×4 = 16", "<strong>能</strong>"],
            ["P4", "16", "1×1 = 1", "2×2 = 4", "勉强"],
            ["P5（DETR 唯一用的层）", "32", "<strong>0.5×0.5 = 0.25</strong>", "1×1 = 1", "<strong>不能</strong>"],
            ["P6", "64", "0.0625", "0.25", "不能"],
        ]),
        CALLOUT("danger", "<p>这张表推出一条对 TSR 项目非常硬的结论：<strong>如果你要用 DETR 系做交通标志检测，多尺度（至少到 stride 8，理想是加 stride 4 的 P2）不是调参选项，是准入条件。</strong><em>「我们用了 DINO，但为了省显存只保留了 P4–P6」这种配置，在远距离小标志上的召回会直接崩掉，而整体 mAP 可能只掉两三个点——因为小标志在数量上并不占多数，平均值把它掩盖了。</em>这也是 C55 会反复强调「必须按像素尺寸分桶评测」的原因。</p>", "多尺度不是选项，是准入条件"),
        H3("两阶段与迭代细化：让参考点从「猜」变成「有依据」"),
        P("原版 Deformable DETR 的 query 仍然是可学嵌入，参考点由 query 线性预测——<strong>它对具体这张图一无所知</strong>。两阶段版本改成：让 encoder 输出的每个特征点都当作一个提案，预测 objectness 与初始框，取 top-K（K = query 数）作为 decoder 的参考点。"),
        ASCII("""单阶段（原始 Deformable DETR）
  可学 query 嵌入 ──► Linear ──► 参考点 p̂_q （与图像无关，只是学到的统计先验）

两阶段（Deformable DETR two-stage / DINO 沿用）
  encoder 特征（所有尺度所有位置，约 2.2 万个）
        │
        ├─► 每个位置预测 (objectness, box)         ← 这一步就是一个密集检测器
        │
        └─► top-K 挑选（K = 300/900）──► 参考点 p̂_q 与初始框
                                             │
                                        decoder 只需要**细化**，不需要**发现**

迭代框细化（look forward once, Deformable DETR）
  layer1: b1 = b0 + Δ1        loss1 ── 梯度 ──► Δ1 的参数
             └─ detach ──► layer2: b2 = b1 + Δ2   loss2 ── 梯度 ──► Δ2 的参数
                              └─ detach ──► layer3: ...
  **detach 切断了 loss2 对第 1 层参数的梯度** ← DINO 的 look forward twice 就是去掉它""")
        ,
        DUAL(
            "两阶段的价值可以用一句话概括：<strong>它把「在整张图里找出目标大概在哪」这件本来要 decoder 从零学的事，交给了一个密集预测头</strong>——而密集预测头本来就擅长这个（它每个位置都有监督）。decoder 于是从「发现 + 细化」的双重任务降级为「细化」的单一任务。<em>这也解释了为什么两阶段对小目标的收益更明显：小目标最难的是「发现」。</em>",
            "代价有三个，都要能说出来：<strong>①</strong> encoder 侧多了一个检测头，训练时要为它单独算一份密集损失（Deformable DETR 复用了同一套 Hungarian 损失做提案监督）；<strong>②</strong> top-K 选择在推理时引入了一次排序，虽然便宜但让计算图多一个数据依赖的算子（C60 会讲这对导出与 TensorRT 的影响）；<strong>③</strong> <em>提案的质量成了新的瓶颈——如果 encoder 的 objectness 对某类目标系统性偏低，那类目标连进入 decoder 的资格都没有</em>。第 ③ 点在长尾场景（TSR 的稀有标志）里是真实风险。",
        ),
    ])),
    ("dn", "DN-DETR：与其修匹配，不如绕开匹配", "".join([
        P("Deformable DETR 把 epoch 从 500 压到 50，但根因 ② 原封不动：<strong>匹配依然在翻转</strong>。DN-DETR 的做法极其漂亮——它没有去改进匈牙利算法，也没有加匹配的稳定性正则，而是<strong>额外塞进一批「不需要匹配」的 query</strong>。"),
        H3("去噪任务：把最后一公里单独拎出来训练"),
        OL([
            "取这张图的 GT 框，加一点噪声（中心平移 + 尺寸缩放），得到一个「差不多但不准」的框；",
            "取这张图的 GT 类别，以概率 γ 翻转成另一个类别；",
            "把 <code>(带噪框, 带噪标签)</code> 编码成额外的 query，和正常的 matching query 一起送进 decoder；",
            "<strong>这些 query 的监督目标是已知的</strong>——把框还原成 GT 框、把标签还原成 GT 标签。<em>完全不经过匈牙利匹配。</em>",
        ]),
        DUAL(
            "为什么这管用？因为<strong>去噪任务恰好就是匹配分支最终要学会的那件事的「最后一公里」</strong>：给你一个大致对的框，把它修准。原来 query 要同时学「找到目标」和「修准框」，而且这两件事的监督还在抖；现在「修准框」这件事有了一份<em>从第一个 iteration 就完全稳定</em>的监督。",
            "更精确地说，DN 把一个不稳定的联合任务分解成了两个子任务的和：<strong>匹配分支继续学「发现 + 认领」，去噪分支专门学「条件重建」</strong>。二者共享同一套 decoder 参数与 cross-attention，所以去噪分支学到的定位能力会<em>直接迁移</em>到匹配分支。<strong>关键是去噪分支的监督密度：每个 GT 在每次迭代都被 G 组去噪 query 各学一遍（G 常取 5~100），而匹配分支每个 GT 只有 1 个 query。</strong>监督信号密度提升了一到两个数量级，而且完全无噪。",
        ),
        H3("attention mask：这个机制的成败全在这里"),
        P("去噪 query 携带了 GT 的信息（框的位置、类别）。<strong>如果匹配 query 能通过 self-attention 读到它们，就是把答案抄给了模型</strong>——训练损失会掉得非常漂亮，验证 AP 一塌糊涂。所以必须用 attention mask 做隔离："),
        TABLE(["谁看谁", "允许？", "理由"], [
            ["匹配 query → 去噪 query", "<strong>❌ 禁止</strong>", "<strong>否则 GT 泄漏</strong>，这是最致命的一条"],
            ["去噪组 g → 去噪组 g&#39;（g≠g&#39;）", "❌ 禁止", "每组是同一批 GT 的不同噪声版本，互看等于抄答案"],
            ["去噪组 g → 同组内部", "✅ 允许", "同组内每个 query 对应不同 GT，互相去重是有意义的"],
            ["去噪 query → 匹配 query", "<strong>✅ 允许</strong>", "匹配 query 不含 GT 信息，看它无害；<em>官方实现确实是不屏蔽的</em>"],
            ["匹配 query → 匹配 query", "✅ 允许", "这就是原本的去重协商"],
        ]),
        CALLOUT("danger", "<p>第四行是个高频考点：<strong>attention mask 不是对称的</strong>。很多人默认「互相看不见」就写成对称矩阵，那样会削弱去噪分支从匹配分支获得的上下文。<em>官方 DINO 实现里，去噪 query 的行只屏蔽其他去噪组的列，匹配 query 的列是开放的。</em></p><p>而忘记加 mask 的症状极具欺骗性：<strong>训练 loss 迅速降到很低、去噪分支的重建误差趋近 0、验证 AP 却比不加 DN 还差</strong>。<em>排查方法：把去噪分支关掉重训一次，如果验证 AP 反而涨了，八成是 mask 写错了。</em></p>", "mask 写错 = 训练时抄答案"),
        H3("噪声强度：一个必须调但很少有人讲清楚的超参"),
        P("噪声太小，去噪任务退化成恒等映射，学不到东西；噪声太大，带噪框和 GT 已经不是同一个目标，去噪变成了「无中生有」，反而制造错误监督。DN-DETR 用两个参数控制："),
        TABLE(["参数", "典型值", "含义", "太大会怎样"], [
            ["<code>box_noise_scale</code> λ", "0.4", "中心平移 ≤ λ/2·w，尺寸缩放 ∈ [1−λ, 1+λ]", "带噪框与 GT 的 IoU 掉到 0.3 以下，重建目标不合理"],
            ["<code>label_noise_ratio</code> γ", "0.2 ~ 0.5", "以 γ 的概率把标签换成另一个类", "分类分支学到「输入标签无所谓」，去噪退化"],
            ["<code>dn_number</code> G", "100（DINO）", "去噪组数", "显存与训练时间线性上升；单图 GT 多时要动态截断"],
        ]),
        P("<strong>标签翻转这一项对 TSR 特别有价值</strong>：它训练的正是「给我一个大致对的框和一个<em>可能是错的</em>类别，请你从图像证据里纠正它」。交通标志里限速 60 / 80 / 100 这类形状完全相同、只有数字不同的类，恰恰最需要这种纠错能力。<em>把 γ 调大一点、并且让翻转优先发生在易混类之间（而不是全类均匀采样），是一个有依据的定制方向。</em>"),
        CALLOUT("intuition", "记住 DN 最漂亮的一点：<strong>它不改任何网络结构、不加任何推理开销。</strong>去噪 query 只在训练时存在，推理时整块拿掉，模型的参数量、FLOPs、延迟完全不变。<em>「零推理成本换 4 倍收敛速度」——这类改动在工业界的采纳率总是最高的，因为它不需要重新做部署验证。</em>面试里主动点出这一点，说明你在用工程视角读论文。"),
    ])),
    ("dino", "DINO：三件小事，各修一个具体短板", "".join([
        P("<span class=\"term\">DINO</span>（DETR with Improved deNoising anchOr boxes，注意与自监督的 DINO 同名不同物）是 DETR 家族第一个在 COCO 榜首击败所有密集检测器的模型（Swin-L 63.3 AP test-dev）。它在 DAB-Deformable-DETR + DN 的基础上只加了三件事，<strong>每件都小到可以在一段话里讲完，但每件都精确地对准了一个具体缺陷</strong>。"),
        H3("① 对比去噪 CDN：教模型说「不」"),
        P("原版 DN 只有正样本：所有去噪 query 的目标都是「还原成这个 GT」。<strong>问题是模型从来没被教过「这个框离得太远，应该判为背景」</strong>——于是它倾向于把任何接近的框都拉向最近的 GT，结果就是重复框与过度自信的低质量预测。"),
        ASCII("""对比去噪 CDN：每个 GT 生成一对 query
                     λ1              λ2
   GT ●───────────────┼───────────────┼──────────────►  离 GT 的噪声尺度
      │   正样本区     │   负样本区     │   （不生成）
      │  noise < λ1   │ λ1<noise<λ2  │
      └─► 目标 = 还原成 GT 的框与类别
                      └─► 目标 = **no-object**（背景）

  λ1 = 1.0, λ2 = 2.0（DINO 默认，单位是框宽高的倍数）
  作用：在 GT 周围划出一圈「近但不够近」的硬负样本，
        直接教模型「什么距离算认领成功」——**这正是 NMS 在推理期做的事，
        被搬到了训练期**，所以 DINO 的重复框显著少于 DN-DETR。""")
        ,
        DUAL(
            "CDN 的作用可以类比成给模型加了一条<strong>决策边界的直接监督</strong>。没有负样本时，模型只知道「往 GT 靠」这个方向，不知道边界在哪；有了负样本，正负两组 query 的噪声尺度之差就明确定义了边界的位置。<em>论文里 CDN 对小目标 AP_S 的提升最明显——因为小目标的「近但不够近」区域相对框尺寸更大，最容易产生重复。</em>",
            "严格看，CDN 是把 <span class=\"term\">hard negative mining</span>（难负样本挖掘）以一种<em>可控且无需搜索</em>的方式引入了 DETR：负样本不是从模型预测里挑出来的（那样会有课程学习的不稳定性），而是<strong>由 GT 按固定噪声尺度构造出来的</strong>。<em>代价是这些负样本的分布由 λ1/λ2 人为决定，不一定匹配模型真实的困难区域</em>——这是 C58「难例挖掘」里会展开讨论的取舍：构造式负样本 vs 挖掘式负样本。",
        ),
        H3("② Mixed query selection：只借位置，不借内容"),
        P("两阶段 Deformable DETR 从 encoder 的 top-K 特征里同时取出了<strong>位置</strong>（初始框）和<strong>内容</strong>（作为 decoder query 的初始特征）。DINO 发现后者是错的："),
        TABLE(["方案", "位置（reference box）", "内容（decoder embedding）", "问题 / 收益"], [
            ["静态（原始 DETR / DAB）", "可学嵌入", "可学嵌入", "与图像无关，decoder 要从零发现"],
            ["纯查询选择（two-stage Deformable）", "encoder top-K 的框", "<strong>encoder top-K 的特征</strong>", "<strong>encoder 特征是「初步的」，可能歧义或含多个目标，用作内容会误导 decoder</strong>"],
            ["<strong>Mixed（DINO）</strong>", "<strong>encoder top-K 的框</strong>", "<strong>仍用可学的静态嵌入</strong>", "位置有图像依据，内容保持中性 → 更稳"],
        ]),
        P("<strong>这个设计的逻辑值得记住：位置先验是安全的（错了后面还能细化），内容先验是危险的（错了会一直误导 cross-attention 去看错地方）。</strong><em>面试里被问「为什么不把 encoder 特征直接当 query」，这就是答案。</em>"),
        H3("③ Look forward twice：让每一层的框预测也为下一层负责"),
        P("Deformable DETR 在层间对参考框做了 <code>detach()</code>（论文里叫 <span class=\"term\">look forward once</span>）：第 i 层预测出的框传给第 i+1 层时切断梯度，所以第 i 层的参数只被第 i 层的辅助损失监督。DINO 去掉这个 detach（<span class=\"term\">look forward twice</span>）——<strong>第 i 层的参数同时被第 i 层和第 i+1 层的损失监督</strong>。"),
        MATH("\\text{LFO}:\\; \\frac{\\partial \\mathcal{L}}{\\partial \\theta_i} = \\frac{\\partial \\mathcal{L}_i}{\\partial \\theta_i} \\qquad\\qquad \\text{LFT}:\\; \\frac{\\partial \\mathcal{L}}{\\partial \\theta_i} = \\frac{\\partial \\mathcal{L}_i}{\\partial \\theta_i} + \\frac{\\partial \\mathcal{L}_{i+1}}{\\partial b_{i+1}}\\cdot\\frac{\\partial b_{i+1}}{\\partial b_i}\\cdot\\frac{\\partial b_i}{\\partial \\theta_i}"),
        P("为什么原来要 detach？因为担心早期层的框预测不准，梯度会互相干扰。<strong>DINO 的论证是：既然有了 DN 提供的稳定监督，早期层的框已经足够好，此时打通梯度带来的「早期层为最终结果负责」收益大于干扰。</strong><em>这是一个典型的「前一个改进让后一个改进变得可行」的例子——顺序不能颠倒。</em>"),
        TABLE(["改动", "修的是哪个具体缺陷", "论文消融量级（R50, 12 epoch）"], [
            ["<strong>CDN 对比去噪</strong>", "重复框多、置信度不校准、小目标误检", "约 +0.7 AP，AP_S 提升最明显"],
            ["<strong>Mixed query selection</strong>", "encoder 特征作内容会误导 cross-attention", "约 +0.2 AP"],
            ["<strong>Look forward twice</strong>", "早期层的框预测缺少下游监督", "约 +0.2 AP"],
            ["三者叠加 + DN + Deformable", "—", "<strong>49.0 AP @ 12 epoch</strong>"],
        ]),
        CALLOUT("warn", "看到「+0.2 AP」不要轻视，也不要迷信。<strong>检测任务里同一配置换随机种子的波动就有 ±0.2~0.5 AP</strong>（C61 模块 01 会详细讲），所以单看一个 +0.2 的消融数字是没有统计意义的。<em>DINO 这三项之所以被普遍接受，是因为它们在多个骨干、多个 epoch 配置、多个后续工作里都稳定复现——而不是因为那张表上的数字。</em>面试里如果对方拿一个 +0.3 的结果问你「这算改进吗」，正确答案是「要看几个种子、方差多大」。"),
    ])),
    ("one2many", "一对多匹配的回归：训练要密集，推理才要唯一", "".join([
        P("2022 年底开始出现一批看似「开倒车」的工作：<strong>Group DETR、H-DETR、Co-DETR 又把一对多匹配加回了训练</strong>。理解它们，等于理解了 DETR 范式最深的一层。"),
        CALLOUT("intuition", "一句话点破：<strong>「一对一匹配」是<em>推理端</em>的需求（输出不能有重复框，才能扔掉 NMS），不是<em>训练端</em>的最优（每个 GT 只有 1 个正样本，监督密度比密集检测器低两个数量级）。</strong>既然如此，正确的做法就是——<em>训练时用一对多拿密集监督，推理时只留一对一分支拿无重复输出</em>。这个「训练与推理不对称」的设计，是近三年检测领域最重要的观念转变之一。"),
        P("先把监督密度的账算清楚。COCO 平均每图 7.3 个标注框："),
        TABLE(["检测器", "每图每次迭代的正样本数", "相对 DETR", "推理端有重复框吗"], [
            ["Faster R-CNN（RPN + head）", "≈ 256（采样后）", "35×", "有 → 需要 NMS"],
            ["RetinaNet / FCOS（密集）", "≈ 数百~上千", "50~150×", "有 → 需要 NMS"],
            ["<strong>DETR（一对一）</strong>", "<strong>7.3</strong>", "<strong>1×</strong>", "<strong>基本没有 → 无需 NMS</strong>"],
            ["Group DETR（G=11 组 query）", "≈ 80", "11×", "推理只用 1 组 → 没有"],
            ["H-DETR（一对多分支 K=6）", "≈ 51", "7×", "推理丢掉一对多分支 → 没有"],
            ["Co-DETR（+ ATSS/RCNN 辅助头）", "≈ 数百", "数十×", "推理丢掉辅助头 → 没有"],
        ]),
        P("这张表把「DETR 为什么慢」的第三个角度也讲清楚了：<strong>密集检测器每个 iteration 从一张图里榨出几百条监督，DETR 只榨出 7 条。</strong>要拿到同样多的梯度更新次数，DETR 自然需要几十倍的 epoch。<em>notebook 里会用这个账反推出「500 epoch ÷ 11 组 ≈ 45 epoch」——和 Group DETR 论文报告的收敛加速惊人地一致。</em>"),
        ASCII("""训练期（要密集监督）                    推理期（要唯一输出）
┌─────────────────────────────┐        ┌─────────────────────────────┐
│ one-to-one 分支   N=300      │───────►│ one-to-one 分支   N=300      │
│   每图 7.3 个正样本           │        │   直接 top-k 输出，无 NMS    │
├─────────────────────────────┤        └─────────────────────────────┘
│ one-to-many 分支  N=1500     │                 ▲
│   GT 复制 K=6 份再匹配        │──── 整块丢弃 ───┘
│   每图 44 个正样本            │
├─────────────────────────────┤        推理开销：**完全为 0**
│ 去噪分支（DN/CDN） G×2M      │        参数量/FLOPs/延迟：**完全不变**
│   每图 100×2×7.3 个稳定样本   │        训练开销：显存 +30%~100%，
└─────────────────────────────┘                  单步时间 +20%~60%""")
        ,
        TABLE(["方法", "怎么加密集监督", "参数是否共享", "关键实现细节"], [
            ["<strong>Group DETR</strong>", "G 组独立 query，每组各自做一次一对一匹配", "decoder 全共享", "<strong>组间 self-attention 必须隔离</strong>（否则组间会互相去重，退化成一对一）"],
            ["<strong>H-DETR</strong>", "额外一批 query 与「GT 复制 K 份」做一对多匹配", "decoder 共享，query 分开", "两分支的 self-attention 分开跑；损失加权求和"],
            ["<strong>Co-DETR</strong>", "在 encoder 输出上挂 ATSS / Faster-RCNN 等成熟密集头", "backbone+encoder 共享", "还会把密集头的正样本反过来变成 decoder 的「定制正 query」"],
        ]),
        DUAL(
            "三者的差别在于「密集监督加在哪一层」：<strong>Group DETR 加在 query 层（复制 query）</strong>，<strong>H-DETR 加在匹配层（复制 GT）</strong>，<strong>Co-DETR 加在 encoder 层（直接挂密集头）</strong>。<em>越靠近底层，对 backbone/encoder 表征的监督越直接，收益越大，但工程侵入性也越强</em>——Co-DETR 相当于把一个完整的密集检测器缝在了 DETR 上，训练代码复杂度显著上升。",
            "有一个共同的隐性约束必须说清楚：<strong>一对多分支绝不能与一对一分支共享同一次 self-attention</strong>。self-attention 的作用是让 query 互相协商去重；如果一对多的 query 和一对一的 query 在同一次 attention 里，一对多那些「本来就该重复」的 query 会把去重信号搅乱，<em>结果是一对一分支也开始输出重复框，NMS-free 的性质丢失</em>。<strong>Group DETR 用分组 mask、H-DETR 用两次独立前向来保证这一点——这与 DN 的 attention mask 是同一类设计约束。</strong>",
        ),
        CALLOUT("warn", "这一节还有一个反向的工程结论：<strong>如果你在推理端仍然要加 NMS，那你就没必要坚持一对一匹配。</strong><em>「训练慢了几倍、部署还是要 NMS」是最糟糕的组合。</em>选 DETR 系的唯一硬理由是「无 NMS 带来的延迟确定性」（C53 模块 04 / 本课模块 05 会算这笔账）；如果这个理由对你的系统不成立，密集检测器在同等算力下几乎总是更省心。"),
    ])),
    ("thread", "一条主线：每一步都在解决「监督信号太稀疏」", "".join([
        P("这一节是本模块的核心，也是<strong>面试里能一击命中的总结</strong>。前面五节看起来是五个互不相干的技巧，其实它们全部在回答同一个问题：<strong>怎么让每一次前向传播产生更多、更准、更稳的监督信号？</strong>"),
        MATH("\\rho \\;\\propto\\; \\underbrace{N_{\\text{pos}}}_{\\text{每次迭代被监督的 query 数}} \\;\\times\\; \\underbrace{\\alpha}_{\\text{注意力落在目标上的质量}} \\;\\times\\; \\underbrace{(1-\\phi)}_{\\text{匹配未翻转的比例}}"),
        P("这不是论文里的公式，是一个<strong>用来组织记忆的粗糙模型</strong>：三个因子分别对应「监督有多少」「监督打在哪」「监督稳不稳」。<em>DETR 家族的每一步演进，都可以定位到它抬高了哪个因子。</em>"),
        TABLE(["工作", "抬高哪个因子", "怎么抬的", "epoch"], [
            ["<strong>DETR</strong> (2020)", "—", "基线：N_pos=7.3, α≈0.001, 1−φ≈0.5", "<strong>500</strong>"],
            ["<strong>Deformable DETR</strong> (2021)", "<strong>α</strong> ↑↑↑", "K 点采样让注意力从一开始就集中；多尺度让小目标有独立特征", "<strong>50</strong>"],
            ["Conditional / DAB-DETR (2022)", "α ↑", "把 query 显式解释为空间锚点/4D 框，给 cross-attention 空间先验", "50"],
            ["<strong>DN-DETR</strong> (2022)", "<strong>N_pos ↑↑, (1−φ) → 1</strong>", "去噪 query 绕开匹配，提供 G 倍且完全无噪的监督", "<strong>12</strong>"],
            ["<strong>DINO</strong> (2023)", "N_pos ↑, α ↑", "CDN 加负样本教决策边界；mixed query selection 让参考点有图像依据；LFT 让梯度多走一层", "<strong>12（49.0 AP）</strong>"],
            ["<strong>Group / H- / Co-DETR</strong> (2023)", "<strong>N_pos ↑↑↑</strong>", "训练期恢复一对多，直接把正样本数提高一到两个数量级", "12（+1~2 AP）"],
        ]),
        ASCII("""                     监督信号太稀疏
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   打在哪（α）          有多少（N_pos）      稳不稳（1−φ）
        │                   │                   │
  Deformable Attn      Group DETR           DN-DETR
  多尺度 P3~P6         H-DETR                （去噪绕开匹配）
  两阶段/查询选择       Co-DETR               CDN 负样本
  DAB 4D anchor        DN 的 G 组去噪         （稳定决策边界）
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    DINO = 三条线的合流
                    12 epoch / 49.0 AP / 长期 SOTA 骨架""")
        ,
        H3("面试答法骨架"),
        OL([
            "<strong>先给结论</strong>：DETR 收敛慢有两个正交根因——注意力初期弥散、匹配不稳定；后续工作按这两条线分头解决。",
            "<strong>再讲第一条线</strong>：Deformable DETR 用 K 点可学采样把注意力从一开始就集中，顺带让多尺度在算力上变得可行，小目标 AP_S 从 20.5 到 26.4，500→50 epoch。",
            "<strong>再讲第二条线</strong>：DN-DETR 加一批带噪 GT 作为额外 query，监督目标已知、不经匹配，从第一步就稳定；关键实现是 attention mask 防泄漏；50→12 epoch，且<strong>推理零开销</strong>。",
            "<strong>再讲合流</strong>：DINO = Deformable + DAB + CDN（正负噪声对，教决策边界）+ mixed query selection（只借位置不借内容）+ look forward twice，12 epoch 到 49.0 AP，成为之后三年的默认骨架。",
            "<strong>最后给洞察</strong>：Group/H-/Co-DETR 又把一对多加回训练，说明「一对一是推理需求而非训练最优」——<em>这一句能显著抬高对方对你的评价，因为它说明你理解的是范式而不是模型列表</em>。",
            "<strong>如果对方追问「那你会怎么用」</strong>：接模块 05 的选型论证（数据量、迭代周期、部署工具链、延迟稳定性）。",
        ]),
        CALLOUT("intuition", "把整条线压缩成一句可迁移的心法：<strong>当一个模型「收敛慢」时，不要先去调学习率，先去数「每次前向产生了多少条有效监督」，再去看「这些监督打在了正确的位置吗」「它们在相邻 iteration 之间稳定吗」。</strong><em>这个三问在任何用了匹配 / 采样 / 稀疏监督的系统上都成立</em>——分割的 mask2former、跟踪的 MOTR、姿态的 PETR，走的是完全一样的演进路径。"),
    ])),
    ("tsr", "回到 TSR：这条演进线对交通标志检测意味着什么", "".join([
        P("这一节把前面所有结论翻译成 TSR 项目里的具体决定。<strong>四条，每条都有可执行的动作。</strong>"),
        H3("① 多尺度是准入条件，而且要往下加而不是往上加"),
        P("交通标志的像素尺寸分布与 COCO 完全不同：<strong>绝大多数有效检出发生在 12~48 像素区间</strong>（因为要在 40~80 米外就报出来，留给下游决策的时间才够）。按前面的 stride 表，这意味着 <strong>P3（stride 8）是主力层，P2（stride 4）值得认真评估</strong>，而 P6/P7 几乎没有负载。<em>直接照抄 COCO 配置（P3–P7 均匀分配）会把大量算力浪费在没有目标的高层上。</em>"),
        UL([
            "动作：统计自己数据集的标志像素尺寸直方图，按 FPN 层级分配规则算出各层负载，据此裁剪层数（C57 模块 02 会给完整方法）。",
            "动作：可变形注意力的采样点数 K 可以按层设置——<strong>低层（小目标）给更多采样点</strong>，高层减少。",
        ]),
        H3("② 去噪的标签翻转应该按混淆结构定制，而不是全类均匀"),
        P("默认实现里，标签翻转是在全部类别中均匀采样。<strong>但 TSR 的错分是高度结构化的</strong>：限速 60/80/100 互相错分的概率远高于「限速 60 错成禁止掉头」。把翻转分布改成按混淆矩阵采样，相当于让去噪分支专门练易混类。"),
        CALLOUT("intuition", "这是一个「读懂机制之后才能想到」的定制点，<strong>在面试里作为「你会怎么改进」的回答非常有力</strong>：它不是换个 backbone 那种谁都能说的答案，而是说明你理解 DN 的监督到底在训练什么。<em>配套的验证方式也要说出来：看易混类对的混淆矩阵非对角元是否下降，而不是只看总 mAP。</em>"),
        H3("③ 收敛速度的真实价值不是省 GPU，是缩短数据闭环周期"),
        P("量产 TSR 的工作方式是<strong>每周甚至每天都有新挖掘的难例进来</strong>（C58 讲的数据闭环）。在这种节奏下，「一次训练要 500 epoch」意味着数据改进和模型验证之间隔了一两周——<strong>闭环转不动，数据飞轮就不存在</strong>。"),
        TABLE(["方案", "COCO 规模的一次训练", "TSR 数据（约 15 万图）估算", "一周能迭代几次"], [
            ["DETR（500 ep, 8×V100）", "≈ 6 天", "≈ 8 天", "<strong>&lt; 1</strong>"],
            ["Deformable DETR（50 ep）", "≈ 1.5 天", "≈ 2 天", "3"],
            ["<strong>DINO（12 ep）</strong>", "<strong>≈ 10 小时</strong>", "<strong>≈ 14 小时</strong>", "<strong>7+</strong>"],
            ["YOLO 系（300 ep 但单步极快）", "≈ 1 天", "≈ 1.5 天", "4"],
        ]),
        P("<strong>「12 epoch」才是让 DETR 系真正进入量产候选名单的门票。</strong><em>在此之前，无论 AP 多高，工程团队都不会选一个改一次数据要等一周的模型。</em>"),
        H3("④ 密集同类场景要特别小心一对一匹配"),
        P("高速龙门架上一排 5 个方向指示牌、施工区连续摆放的同款锥形警示牌——<strong>这类「多个同类目标紧邻」的场景是一对一匹配的天然弱区</strong>：query 之间的去重协商可能把相邻的真目标误判为重复而抑制掉。"),
        CALLOUT("danger", "<p>症状是<strong>「密集排列时少检一两个，而且总是少中间那几个」</strong>。这不是分类问题也不是定位问题，是 self-attention 的去重把真目标当成了重复。<em>排查方法：把 decoder self-attention 关掉重新推理一次（或者看该场景下 query 之间的注意力矩阵），如果漏检消失，就确认是去重过度。</em></p><p>对策：<strong>①</strong> 训练期加一对多分支（Group/H-DETR），让模型见过「相邻的多个同类目标都是正样本」；<strong>②</strong> 增大 query 数并检查前景 query 占比（模块 05 的诊断指标）；<strong>③</strong> 数据侧用 copy-paste 合成密集同类场景（C56 模块 03）。</p>", "密集同类目标：一对一匹配的天然弱区"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("DETR 家族在 2023 年之后进入了「细化与统一」阶段。下面这些是仍然开放、且与 TSR 直接相关的方向。"),
        UL([
            "<strong>匹配稳定性的理论仍不完整</strong>：Stable-DINO 指出问题的根源是<em>分类分数与定位质量不对齐</em>——匹配代价里分类项用的是与位置无关的分数，导致「分类高但框差」的 query 赢得匹配。它用位置监督（position-supervised loss）修正，在 12 epoch 上再涨约 +1.5 AP。<em>但「什么样的匹配代价能保证稳定」尚无理论刻画。</em>",
            "<strong>去噪超参缺少原则</strong>：λ1/λ2/G/γ 四个超参都靠经验，且与数据集的目标尺寸分布强耦合。<em>小目标数据集上「噪声尺度按框宽高的倍数」这个定义本身就可疑——16 像素的框加 0.4 倍噪声只有 6 像素，可能小于标注误差本身。</em>这在 TSR 上是真实问题，值得做消融。",
            "<strong>一对一与一对多的统一</strong>：DEIM（2025）提出 Dense O2O——用 mosaic/mixup 提高单图目标密度，从而在保持一对一匹配的前提下提高正样本数，再配合 Matchability-Aware Loss。<em>这条路线试图不引入额外分支就拿到密集监督</em>，方向很干净，但对增强策略的依赖使它与「贴近部署分布」的增强原则（C56）存在张力。",
            "<strong>极小目标仍是 DETR 系的短板</strong>：即使 DINO + P2，在 8~16 像素区间的 AP 依然明显低于专门设计的密集检测器 + 切片推理（C57 模块 04）。<em>核心矛盾是采样点数固定：K=4 个点对一个只占 2×2 格子的目标已经饱和，加点无益；而全局注意力又太贵。</em>「稀疏采样如何在极小目标上不丢信息」没有好答案。",
            "<strong>NMS-free 在边缘部署的实证仍少</strong>：论文报告的是 GPU 上的端到端延迟，而车端 SoC 上 top-k、多尺度采样（grid_sample 类算子）的支持度与效率都不同。<em>「去掉 NMS 换来的延迟确定性，是否足以抵消可变形采样算子在边缘芯片上的低效」是一个需要在具体硬件上测的问题</em>，C60 会给方法。",
            "<strong>query 数与场景密度的耦合</strong>：N 是超参且固定。密集场景需要大 N，稀疏场景大 N 浪费且降低正样本比例。<em>自适应 query 数（按图像内容动态决定）会破坏静态图导出</em>——这是一个算法与部署直接冲突的开放问题。",
        ]),
        CALLOUT("paper", "必读（按阅读顺序）：★ <em>Deformable DETR: Deformable Transformers for End-to-End Object Detection</em>（Zhu et al., ICLR 2021）——重点看 Fig.2 的注意力可视化与 Table 关于多尺度/两阶段的消融；★ <em>DN-DETR: Accelerate DETR Training by Introducing Query DeNoising</em>（Li et al., CVPR 2022）——重点看 attention mask 的构造与不稳定性度量的定义；★ <em>DINO: DETR with Improved DeNoising Anchor Boxes</em>（Zhang et al., ICLR 2023）——重点看 CDN 与 mixed query selection 两节；<em>DAB-DETR</em>（Liu et al., ICLR 2022，4D anchor query）与 <em>Conditional DETR</em>（Meng et al., ICCV 2021）补足第一条线的中间环节；<em>Group DETR</em>（Chen et al., ICCV 2023）、<em>DETRs with Hybrid Matching</em>（Jia et al., CVPR 2023）、<em>DETRs with Collaborative Hybrid Assignments</em>（Zong et al., ICCV 2023）看一对多的回归；<em>Detection Transformer with Stable Matching</em>（Liu et al., ICCV 2023）看匹配稳定性的最新解释。相邻课程：本课模块 01（匈牙利匹配）、模块 03（object query）、C53 模块 04（RT-DETR 如何把这条线做到实时）、C57（小目标）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 收敛难题与 DETR 家族演进（可变形注意力 / 双线性梯度 / 匹配翻转 / DN 去噪 query）

目标：把「DETR 为什么要 500 epoch」拆成**两个可度量的根因**，然后亲手实现
Deformable / DN / DINO 各自用来修它们的机制，并用数值证明每一步确实抬高了监督信号密度。

**本 notebook 你会亲手实现：**
1. **双线性插值 + 它对采样坐标的解析梯度**（中心差分校验到 1e-7）——可变形采样的数学地基
2. **多尺度可变形注意力**的完整前向（参考点 + 可学偏移 + softmax 权重 + 跨尺度采样）
3. **计算量账**：全局 attention vs K 点采样，解释「为什么 DETR 做不了多尺度」
4. **根因①**：初始注意力质量 α 的计算与「注意力变尖锐需要多少 epoch」的玩具模型
5. **根因②**：从零写匈牙利算法（暴力对拍），量化**匹配翻转率 φ**
6. **DN 去噪 query 构造**：噪声框生成、标签翻转、**attention mask 隔离**（防 GT 泄漏）
7. **CDN 对比去噪**：正负噪声对的构造与它们与 GT 的 IoU 分布
8. **look forward once vs twice** 的梯度路径差异
9. **一对多监督密度**的账，反推 Group DETR 的收敛加速倍数

> 心智模型：**每一步演进都在抬高同一个量——
> ρ ∝ (每次迭代被监督的 query 数) × (注意力落在目标上的质量) × (匹配未翻转的比例)。**"""),
    md("""## 1 · 双线性插值与它对采样坐标的解析梯度

可变形注意力的采样点 `p + Δp` 是**连续坐标**，必须用双线性插值取值才可微。
这一节实现插值、实现解析梯度，并用中心差分校验——
**梯度里最关键的是 `∂v/∂Δp`：它是「学会往哪看」的唯一直接通道。**"""),
    code("""import numpy as np, math, itertools
rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)

def bilinear_sample(feat, pts):
    '''feat:(H,W,C) 特征图; pts:(N,2) 连续像素坐标 (x,y)。返回 (N,C)。
       越界坐标 clamp 到边界（等价 grid_sample(padding_mode="border")）。'''
    H, W, C = feat.shape
    x = np.clip(pts[:, 0], 0.0, W - 1.0)
    y = np.clip(pts[:, 1], 0.0, H - 1.0)
    x0 = np.clip(np.floor(x).astype(int), 0, W - 2); x1 = x0 + 1
    y0 = np.clip(np.floor(y).astype(int), 0, H - 2); y1 = y0 + 1
    dx = (x - x0)[:, None]; dy = (y - y0)[:, None]
    f00 = feat[y0, x0]; f10 = feat[y0, x1]      # (x0,y0) 与 (x1,y0)
    f01 = feat[y1, x0]; f11 = feat[y1, x1]      # (x0,y1) 与 (x1,y1)
    return (1-dx)*(1-dy)*f00 + dx*(1-dy)*f10 + (1-dx)*dy*f01 + dx*dy*f11

def bilinear_grad_xy(feat, pts):
    '''对采样坐标的解析梯度 (dv/dx, dv/dy)，各 (N,C)。越界处梯度为 0（clamp 让函数变常数）。'''
    H, W, C = feat.shape
    ix = (pts[:, 0] >= 0) & (pts[:, 0] <= W - 1)
    iy = (pts[:, 1] >= 0) & (pts[:, 1] <= H - 1)
    x = np.clip(pts[:, 0], 0.0, W - 1.0); y = np.clip(pts[:, 1], 0.0, H - 1.0)
    x0 = np.clip(np.floor(x).astype(int), 0, W - 2); x1 = x0 + 1
    y0 = np.clip(np.floor(y).astype(int), 0, H - 2); y1 = y0 + 1
    dx = (x - x0)[:, None]; dy = (y - y0)[:, None]
    f00 = feat[y0, x0]; f10 = feat[y0, x1]
    f01 = feat[y1, x0]; f11 = feat[y1, x1]
    # dv/dx = (1-dy)(f10-f00) + dy(f11-f01)   ← **正比于特征图在该处的局部差分**
    gx = ((1-dy)*(f10-f00) + dy*(f11-f01)) * ix[:, None]
    gy = ((1-dx)*(f01-f00) + dx*(f11-f10)) * iy[:, None]
    return gx, gy

H, W, C = 12, 16, 3
feat = rng.normal(size=(H, W, C))
pts = np.stack([rng.uniform(1.2, W-2.2, 40), rng.uniform(1.2, H-2.2, 40)], axis=1)
v = bilinear_sample(feat, pts)
gx, gy = bilinear_grad_xy(feat, pts)

eps = 1e-5
gx_num = (bilinear_sample(feat, pts + [eps, 0]) - bilinear_sample(feat, pts - [eps, 0])) / (2*eps)
gy_num = (bilinear_sample(feat, pts + [0, eps]) - bilinear_sample(feat, pts - [0, eps])) / (2*eps)
print('采样值 shape', v.shape)
print('dv/dx 解析 vs 中心差分  最大误差 %.2e' % np.abs(gx - gx_num).max())
print('dv/dy 解析 vs 中心差分  最大误差 %.2e' % np.abs(gy - gy_num).max())
assert np.allclose(gx, gx_num, atol=1e-7) and np.allclose(gy, gy_num, atol=1e-7)
print()
print('✅ 采样坐标是可微的 —— 这就是「偏移 Δp 可学」的全部理由。')
print('⚠️  推论：特征平坦处 (f10-f00)≈0 -> dv/dΔp≈0 -> 采样点收不到位置梯度，会停在原地。')"""),
    code("""# 梯度回传到特征图：每个采样点只把梯度写到 **4 个格点**
def bilinear_scatter_grad(feat_shape, pts, grad_out):
    '''把上游梯度 (N,C) 按双线性权重散射回特征图 (H,W,C)。'''
    H, W, C = feat_shape
    x = np.clip(pts[:, 0], 0.0, W - 1.0); y = np.clip(pts[:, 1], 0.0, H - 1.0)
    x0 = np.clip(np.floor(x).astype(int), 0, W - 2); x1 = x0 + 1
    y0 = np.clip(np.floor(y).astype(int), 0, H - 2); y1 = y0 + 1
    dx = (x - x0)[:, None]; dy = (y - y0)[:, None]
    g = np.zeros((H, W, C))
    np.add.at(g, (y0, x0), (1-dx)*(1-dy)*grad_out)
    np.add.at(g, (y0, x1), dx*(1-dy)*grad_out)
    np.add.at(g, (y1, x0), (1-dx)*dy*grad_out)
    np.add.at(g, (y1, x1), dx*dy*grad_out)
    return g

go = np.ones((len(pts), C))
g_feat = bilinear_scatter_grad((H, W, C), pts, go)
touched = int((np.abs(g_feat).sum(-1) > 0).sum())
print('采样点数 %d -> 收到梯度的特征格点数 %d / %d 个格点' % (len(pts), touched, H*W))
assert np.allclose(g_feat.sum(), len(pts) * C), '每个采样点的 4 个双线性权重之和恒为 1'
assert touched <= 4 * len(pts)
print()
print('对比两种「梯度分布」：')
print('  全局 attention : HW 个位置各拿 1/HW 的权重 -> 方向由近似均匀的权重决定，**极弱且无指向**')
print('  可变形采样     : 4K 个位置拿到集中的梯度，**而且采样位置本身也收梯度**')
print('✅ 后者多出来的那条 dv/dΔp 通道，是 500 epoch -> 50 epoch 的机制层解释。')"""),
    md("""## 2 · 多尺度可变形注意力：完整前向

`MSDeformAttn(z_q, p̂_q, {x_l}) = Σ_l Σ_k A_lqk · x_l(φ_l(p̂_q) + Δp_lqk)`

三个要点：① 参考点 `p̂_q` 归一化到 [0,1]²，同一个点可以映射到任意尺度；
② 偏移 `Δp` 与权重 `A` **都由 query 单独线性预测**（不做 Q·K 点积）；
③ `A` 对 **L×K 个点整体** softmax，所以跨尺度是竞争关系。"""),
    code("""LEVELS = [(100, 167), (50, 84), (25, 42), (13, 21)]   # 1333x800 输入的 stride 8/16/32/64
CH = 16
feats = [rng.normal(size=(h, w, CH)) for h, w in LEVELS]
L, K, NQ = len(LEVELS), 4, 6

def softmax(z, axis=-1):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)

def ms_deform_attn(ref_pts, offsets, attn_logits, feats):
    '''ref_pts:(Nq,2) 归一化 (x,y) in [0,1]; offsets:(Nq,L,K,2) 归一化偏移;
       attn_logits:(Nq,L*K)。返回 out:(Nq,C), locs:(Nq,L,K,2), vals:(Nq,L*K,C)'''
    Nq = ref_pts.shape[0]; Kk = offsets.shape[2]; Cc = feats[0].shape[2]
    A = softmax(attn_logits, axis=-1)                    # 对 L*K 个点整体归一化
    out = np.zeros((Nq, Cc)); locs = []; vals = []
    for l, f in enumerate(feats):
        h, w, _ = f.shape
        p = ref_pts[:, None, :] + offsets[:, l, :, :]    # (Nq,K,2) 仍是归一化坐标
        pix = p * np.array([w - 1.0, h - 1.0])           # -> 该层的像素坐标
        v = bilinear_sample(f, pix.reshape(-1, 2)).reshape(Nq, Kk, Cc)
        out += (A[:, l*Kk:(l+1)*Kk][:, :, None] * v).sum(axis=1)
        locs.append(p); vals.append(v)
    return out, np.stack(locs, 1), np.concatenate(vals, axis=1), A

ref = rng.uniform(0.2, 0.8, size=(NQ, 2))
off = rng.normal(scale=0.03, size=(NQ, L, K, 2))         # 初始化时偏移很小
logits = rng.normal(scale=0.1, size=(NQ, L*K))
out, locs, vals, A = ms_deform_attn(ref, off, logits, feats)

print('输出 shape', out.shape, '| 采样点总数/query =', L*K)
print('注意力权重每行之和 =', np.round(A.sum(1), 8))
assert np.allclose(A.sum(1), 1.0)
# 输出是采样值的凸组合 -> 必须落在采样值的逐通道 min/max 之间
assert (out <= vals.max(1) + 1e-9).all() and (out >= vals.min(1) - 1e-9).all()
print()
print('query 0 的 16 个采样点（归一化坐标，按尺度分组）:')
for l in range(L):
    print('  level %d (stride %2d): ' % (l, 8 << l),
          np.round(locs[0, l], 3).tolist())
print()
print('✅ 同一个参考点被映射到 4 个尺度 -> **一套 query 同时看多尺度**，这是 DETR 做不到的。')"""),
    code("""# 计算量账：为什么 DETR 做不了多尺度，而可变形注意力可以
Cdim, Nq_real = 256, 300
hw_per_level = [(800 // s) * (1333 // s) for s in (8, 16, 32, 64)]
hw_c5 = hw_per_level[2]
hw_all = sum(hw_per_level)

detr_single = 2 * hw_c5 * Cdim                     # QK^T + AV，每 query
detr_multi  = 2 * hw_all * Cdim
deform      = L*K*Cdim + Cdim*(2*L*K) + Cdim*(L*K)  # 采样加权 + 预测偏移 + 预测权重

rows = [('DETR 单尺度 C5 (HW=%d)' % hw_c5, detr_single),
        ('DETR 若做 4 尺度 (HW=%d)' % hw_all, detr_multi),
        ('Deformable 4 尺度 K=4', deform)]
print('%-32s %16s %16s %8s' % ('方案', '每 query 乘加', '总量(x300)', '相对'))
for name, per_q in rows:
    print('%-32s %16.2e %16.2e %7.3fx' % (name, per_q, per_q*Nq_real, per_q/detr_single))
assert detr_multi / detr_single > 20, '多尺度全局注意力比单尺度贵 20 倍以上'
assert deform < detr_single / 20, '可变形注意力比单尺度全局注意力便宜一个数量级以上'
print()
print('⚠️  原版 DETR 不是「忘了」做多尺度 —— 是全局注意力在多尺度上算不起。')
print('    （encoder 的 self-attention 更是 O((HW)^2)，4 尺度下 %.1e 次乘加，直接爆炸）'
      % (hw_all**2 * Cdim))
print('✅ 把复杂度从「正比于特征图面积」改成「正比于采样点数」，多尺度才第一次变得免费。')"""),
    md("""## 3 · 根因①：初始注意力质量 α，以及「注意力要多久才变尖锐」

训练刚开始时 Q/K 投影接近 0，softmax 近似均匀 -> 每个空间位置分到 1/HW 的权重。
**落在 GT 框内的注意力质量 α₀ = 目标占的格子数 / HW。**
这一节把 α₀ 算出来，并用一个玩具模型估计「α 要涨到 50% 需要多少 epoch」。"""),
    code("""def alpha0(box_px, stride, img_hw=(800, 1333)):
    '''初始（均匀）注意力落在 GT 框内的质量。'''
    Hf, Wf = img_hw[0] // stride, img_hw[1] // stride
    cells = (box_px[0] / stride) * (box_px[1] / stride)
    return cells, Hf * Wf, cells / (Hf * Wf)

CASES = [('大目标 近处车辆', (256, 256)), ('中目标 行人', (64, 128)),
         ('COCO 平均目标', (100, 100)),
         ('TSR 30m 限速牌', (32, 32)), ('TSR 60m 限速牌', (16, 16))]
print('%-20s %10s %12s %14s %12s' % ('场景 (stride 32)', '像素', '占格子数', 'HW', 'alpha0'))
alphas = {}
for name, wh in CASES:
    cells, hw, a = alpha0(wh, 32)
    alphas[name] = a
    print('%-20s %10s %12.3f %14d %11.4f%%' % (name, '%dx%d' % wh, cells, hw, a*100))
assert alphas['TSR 60m 限速牌'] < alphas['大目标 近处车辆'] / 200
print()
print('⚠️  60 米外的限速牌：**99.976%% 的 cross-attention 梯度打在背景上**。')
print('    这就是「DETR 收敛慢」在小目标上被放大的那一半原因。')"""),
    code("""# 玩具模型：注意力对数几率随训练线性增长，问「alpha 涨到 50% 要多少 epoch」
def mass_at_sharpness(n_in, n_tot, s):
    '''框内格点的 logit 抬高 s 之后的注意力质量。'''
    a = n_in * math.exp(s)
    return a / (a + (n_tot - n_in))

def epochs_to_half(n_in, n_tot, rate=0.02):
    '''logit 每 epoch 抬高 rate；解 mass=0.5 -> exp(s) = (n_tot-n_in)/n_in。'''
    return math.log((n_tot - n_in) / n_in) / rate

print('%-20s %10s %14s %16s' % ('场景', '占格子', 'alpha0', 'alpha->50% 需要 epoch'))
ep = {}
for name, wh in CASES:
    cells, hw, a = alpha0(wh, 32)
    e = epochs_to_half(cells, hw)
    ep[name] = e
    print('%-20s %10.3f %13.4f%% %16.0f' % (name, cells, a*100, e))
assert ep['TSR 60m 限速牌'] > ep['大目标 近处车辆'], '小目标需要更多 epoch 才能把注意力拧过去'
print()
print('（这是一个刻意简化的玩具模型，只用来说明「目标越小，注意力越难聚焦」的**量级关系**）')
print('✅ 它复现了两件事：① 500 epoch 这个量级 ② 小目标比大目标慢得多。')
print()
# 可变形注意力：参考点在框中心，采样点落在框内的比例就是它的 alpha0
def deform_alpha(box_px, mode, k=4, fixed_px=16.0, trials=4000, seed=1):
    '''mode="box-scaled": 偏移 ~ N(0,(0.25w)^2)，**按框宽高缩放**（Deformable/DINO 的做法）
       mode="fixed-px" : 偏移 ~ N(0,fixed_px^2)，与框大小无关（错误做法）'''
    r = np.random.default_rng(seed)
    w, h = box_px
    if mode == 'box-scaled':
        o = r.normal(size=(trials, k, 2)) * np.array([0.25*w, 0.25*h])
    else:
        o = r.normal(size=(trials, k, 2)) * fixed_px
    inside = (np.abs(o[..., 0]) <= w/2) & (np.abs(o[..., 1]) <= h/2)
    return inside.mean()

print()
print('%-20s %14s %18s %18s' % ('场景', '全局 alpha0', '可变形(按框缩放)', '可变形(固定±16px)'))
for name, wh in CASES:
    print('%-20s %13.4f%% %17.1f%% %17.1f%%'
          % (name, alpha0(wh, 32)[2]*100,
             deform_alpha(wh, 'box-scaled')*100, deform_alpha(wh, 'fixed-px')*100))
assert deform_alpha((16, 16), 'box-scaled') > 0.85
assert deform_alpha((16, 16), 'fixed-px') < 0.25
assert deform_alpha((256, 256), 'fixed-px') > 0.95
print()
print('✅ 可变形注意力把 alpha0 从 0.02% 拉到 ~90% —— 它不是「学会去看」，')
print('   而是**一开始就只看参考点附近**。这是根因① 的完整解法。')
print('⚠️  但前提是**偏移必须按参考框的宽高缩放**：用固定像素尺度时，')
print('    16x16 的标志只有 %.0f%% 的采样点落在框内，而 256x256 的车辆是 %.0f%%。'
      % (deform_alpha((16, 16), 'fixed-px')*100, deform_alpha((256, 256), 'fixed-px')*100))
print('    这就是 DAB-DETR / DINO 把 query 显式解释为 4D 框、并用 (w,h) 调制偏移的原因。')"""),
    md("""## 4 · 根因②：匹配翻转率 φ

先从零实现匈牙利算法（用暴力枚举对拍），再模拟训练噪声下**同一个 GT 被不同 query 认领**的频率。
**φ 高 = 优化目标在抖 = 梯度方向掉头。**"""),
    code("""def hungarian(cost):
    '''O(n^3) 匈牙利算法（JV 势函数版本），要求 行数 <= 列数。返回 (rows, cols)。'''
    a = np.asarray(cost, dtype=float)
    n, m = a.shape
    assert n <= m, '要求行数 <= 列数'
    INF = float('inf')
    u = np.zeros(n + 1); v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int); way = np.zeros(m + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0
        minv = np.full(m + 1, INF); used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]; delta = INF; j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = a[i0 - 1, j - 1] - u[i0] - v[j]
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
    rows = np.arange(n); cols = np.zeros(n, dtype=int)
    for j in range(1, m + 1):
        if p[j]:
            cols[p[j] - 1] = j - 1
    return rows, cols

# 与暴力枚举对拍（含矩形情形）
for _ in range(30):
    n_ = int(rng.integers(2, 6)); m_ = n_ + int(rng.integers(0, 3))
    Cm = rng.random((n_, m_))
    r, c = hungarian(Cm)
    best = min(sum(Cm[i, pm[i]] for i in range(n_))
               for pm in itertools.permutations(range(m_), n_))
    assert len(set(c.tolist())) == n_, '一对一约束'
    assert abs(Cm[r, c].sum() - best) < 1e-9, (Cm[r, c].sum(), best)
print('✅ 匈牙利算法与暴力枚举在 30 组随机矩阵（含矩形）上完全一致')"""),
    code("""def flip_rate(n_epochs, Nq, M, noise, rng, base=None):
    '''同一张图连续 n_epochs 次匹配，统计「GT 换了认领 query」的比例。'''
    base = rng.random((M, Nq)) if base is None else base
    prev = None; flips = []
    for _ in range(n_epochs):
        cost = base + noise * rng.normal(size=(M, Nq))
        _, cols = hungarian(cost)
        if prev is not None:
            flips.append(float((cols != prev).mean()))
        prev = cols
    return float(np.mean(flips))

Nq, M = 100, 8
base = rng.random((M, Nq))
print('%-16s %14s' % ('代价噪声 sigma', '匹配翻转率 phi'))
res = {}
for s in [0.0, 0.02, 0.05, 0.1, 0.2, 0.4]:
    f = flip_rate(30, Nq, M, s, np.random.default_rng(7), base=base)
    res[s] = f
    print('%-16.2f %13.1f%%' % (s, f*100))
assert res[0.0] == 0.0, '无噪声时匹配完全稳定'
assert res[0.4] > res[0.05] > 0, '噪声越大翻转越多'
print()
print('⚠️  训练早期，分类分数几乎随机、框预测也差 -> 代价矩阵基本被噪声主导 -> phi 接近随机重排。')
print('    被翻转的那个 query 上个 epoch 在学「停车让行」，这个 epoch 目标变成了背景。')
print('    **梯度不是变小，是掉头。**')
print('✅ 这与「学习率太大」的症状完全不同：loss 曲线看着在降，但每个 query 学到的东西被反复覆盖。')"""),
    code("""# 训练推进 = 代价矩阵的「信号」变强（真实匹配越来越明显）-> phi 自然下降
print('%-14s %14s %16s' % ('训练阶段', '信噪比 (signal/noise)', '匹配翻转率 phi'))
stages = [('第 1 epoch', 0.3), ('第 10 epoch', 1.0), ('第 50 epoch', 3.0), ('第 200 epoch', 10.0)]
prev_f = 1.0
for name, snr in stages:
    f = flip_rate(30, Nq, M, 1.0/snr, np.random.default_rng(11), base=base)
    print('%-14s %20.1f %15.1f%%' % (name, snr, f*100))
    assert f <= prev_f + 1e-9
    prev_f = f
print()
print('这就是 DETR 的「自锁」：phi 高 -> 学不动 -> 信噪比涨不上去 -> phi 还是高。')
print('✅ DN-DETR 的做法是**绕开它**：额外塞一批监督目标已知、根本不经过匹配的 query，')
print('   让模型从第一个 iteration 就有一份 phi=0 的干净监督。')"""),
    md("""## 5 · DN 去噪 query 的构造：噪声框 + 标签翻转

`box_noise_scale` λ：中心平移 ≤ λ/2·w，尺寸缩放 ∈ [1−λ, 1+λ]；
`label_noise_ratio` γ：以 γ 概率把标签换成**另一个**类。
这些 query 的监督目标是已知的 GT，**完全不经过匈牙利匹配**。"""),
    code("""def cxcywh_to_xyxy(b):
    cx, cy, w, h = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([cx - w/2, cy - h/2, cx + w/2, cy + h/2], axis=1)

def iou_pairwise(a, b):
    '''a,b: (N,4) cxcywh，逐行配对求 IoU。'''
    A, B = cxcywh_to_xyxy(a), cxcywh_to_xyxy(b)
    x1 = np.maximum(A[:, 0], B[:, 0]); y1 = np.maximum(A[:, 1], B[:, 1])
    x2 = np.minimum(A[:, 2], B[:, 2]); y2 = np.minimum(A[:, 3], B[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    sa = (A[:, 2]-A[:, 0]) * (A[:, 3]-A[:, 1])
    sb = (B[:, 2]-B[:, 0]) * (B[:, 3]-B[:, 1])
    return inter / (sa + sb - inter + 1e-12)

def add_box_noise(boxes, lam, rng, lo=0.0):
    '''中心平移幅度 ∈ [lo/2, lam/2]·wh（随机符号），尺寸缩放 ∈ [1-lam, 1+lam]。'''
    cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    n = len(boxes)
    mag_x = rng.uniform(lo/2, lam/2, n) * np.where(rng.random(n) < 0.5, -1.0, 1.0)
    mag_y = rng.uniform(lo/2, lam/2, n) * np.where(rng.random(n) < 0.5, -1.0, 1.0)
    sw = np.clip(1 + (rng.random(n)*2 - 1) * lam, 0.15, 3.0)   # 防止 lam>1 时宽高变负
    sh = np.clip(1 + (rng.random(n)*2 - 1) * lam, 0.15, 3.0)
    return np.stack([cx + mag_x*w, cy + mag_y*h, w*sw, h*sh], axis=1)

def flip_labels(labels, num_classes, ratio, rng):
    m = rng.random(len(labels)) < ratio
    out = labels.copy()
    step = rng.integers(1, num_classes, size=len(labels))   # 1..C-1 -> 保证换成**别的**类
    out[m] = (labels[m] + step[m]) % num_classes
    return out, m

NUM_CLASSES = 45                        # TSR 常见量级：几十个标志细类
M_GT = 6
gt_boxes = np.stack([rng.uniform(0.25, 0.75, M_GT), rng.uniform(0.25, 0.75, M_GT),
                     rng.uniform(0.04, 0.20, M_GT), rng.uniform(0.04, 0.20, M_GT)], axis=1)
gt_labels = rng.integers(0, NUM_CLASSES, M_GT)

print('%-8s %14s %14s' % ('lambda', '带噪框与GT的min IoU', 'mean IoU'))
for lam in [0.1, 0.2, 0.4, 0.8, 1.2]:
    nb = add_box_noise(np.repeat(gt_boxes, 200, axis=0), lam, np.random.default_rng(3))
    io = iou_pairwise(nb, np.repeat(gt_boxes, 200, axis=0))
    print('%-8.1f %18.3f %14.3f' % (lam, io.min(), io.mean()))
nb04 = add_box_noise(np.repeat(gt_boxes, 500, axis=0), 0.4, np.random.default_rng(3))
assert iou_pairwise(nb04, np.repeat(gt_boxes, 500, axis=0)).min() > 0.3, 'lam=0.4 的带噪框仍与 GT 大幅重叠'
print()
print('✅ lambda=0.4（DN-DETR 默认）时 IoU 下界约 0.36 —— 「差不多但不准」，正好是去噪任务想要的。')
print('⚠️  lambda 太大（>0.8）时带噪框与 GT 已不是同一个目标，去噪变成「无中生有」，制造错误监督。')"""),
    code("""# 标签翻转 + 完整的 DN 组构造
GAMMA, GROUPS = 0.3, 50

def build_dn_queries(gt_boxes, gt_labels, num_classes, groups, lam, gamma, rng):
    dnb, dnl, tb, tl, gid = [], [], [], [], []
    for g in range(groups):
        dnb.append(add_box_noise(gt_boxes, lam, rng))
        nl, _ = flip_labels(gt_labels, num_classes, gamma, rng)
        dnl.append(nl); tb.append(gt_boxes); tl.append(gt_labels)
        gid.append(np.full(len(gt_boxes), g))
    return (np.concatenate(dnb), np.concatenate(dnl), np.concatenate(tb),
            np.concatenate(tl), np.concatenate(gid))

dn_b, dn_l, tgt_b, tgt_l, gid = build_dn_queries(
    gt_boxes, gt_labels, NUM_CLASSES, GROUPS, 0.4, GAMMA, np.random.default_rng(5))
flipped = (dn_l != tgt_l)
print('GT 数 %d  x  去噪组数 %d  =  %d 个去噪 query' % (M_GT, GROUPS, len(dn_b)))
print('实际标签翻转率 %.3f （设定 gamma=%.2f）' % (flipped.mean(), GAMMA))
print('翻转后的标签都与原标签不同: ', bool((dn_l[flipped] != tgt_l[flipped]).all()))
assert abs(flipped.mean() - GAMMA) < 0.06
assert (dn_l[flipped] != tgt_l[flipped]).all()
assert len(dn_b) == M_GT * GROUPS
print()
print('监督密度对比（单张图、单次迭代）：')
print('  匹配分支   : %2d 个正样本，且认领关系每个 epoch 都可能翻转 (phi>0)' % M_GT)
print('  去噪分支   : %d 个正样本，监督目标已知、**phi = 0**' % len(dn_b))
print('  密度提升   : %.0f 倍' % (len(dn_b)/M_GT))
print('✅ 这就是 DN 把 50 epoch 压到 12 epoch 的全部秘密：**又多又稳的监督**。')"""),
    md("""## 6 · attention mask 隔离：这个机制的成败全在这里

去噪 query 携带 GT 信息。**匹配 query 若能读到它们 = 训练时抄答案**。
注意官方实现里 mask **不是对称的**：去噪 query 可以看匹配 query，反过来不行。"""),
    code("""def dn_attention_mask(n_per_group, n_groups, n_match):
    '''True = 屏蔽。布局：[去噪 query (n_groups x n_per_group)] + [匹配 query (n_match)]'''
    n_dn = n_per_group * n_groups
    T = n_dn + n_match
    mask = np.zeros((T, T), dtype=bool)
    mask[n_dn:, :n_dn] = True                      # ① 匹配 query 看不见任何去噪 query
    g = np.repeat(np.arange(n_groups), n_per_group)
    mask[:n_dn, :n_dn] = g[:, None] != g[None, :]  # ② 去噪组之间互相看不见
    return mask                                    # ③ 去噪 -> 匹配 的列**不屏蔽**（非对称！）

n_per, n_g, n_m = 3, 3, 5
mk = dn_attention_mask(n_per, n_g, n_m)
n_dn = n_per * n_g
print('mask (True=屏蔽)，前 %d 行/列是去噪 query，后 %d 是匹配 query:' % (n_dn, n_m))
print('     ' + ' '.join('%2d' % j for j in range(mk.shape[1])))
for i, row in enumerate(mk):
    tag = 'DN%d' % (i // n_per) if i < n_dn else 'MAT'
    print('%-4s ' % tag + ' '.join(' X' if x else ' .' for x in row))

assert mk[n_dn:, :n_dn].all(), '① 匹配 query 必须完全看不见去噪 query（否则 GT 泄漏）'
gg = np.repeat(np.arange(n_g), n_per)
assert (mk[:n_dn, :n_dn] == (gg[:, None] != gg[None, :])).all(), '② 组间屏蔽、组内可见'
assert not mk[:n_dn, n_dn:].any(), '③ 去噪 query 可以看匹配 query —— **mask 是非对称的**'
assert not mk[n_dn:, n_dn:].any(), '匹配 query 之间照常做去重协商'
print()
print('✅ 三条规则全部成立。')
print('⚠️  忘记 ① 的症状极具欺骗性：训练 loss 掉得非常漂亮、去噪重建误差趋近 0，')
print('    但**验证 AP 比不加 DN 还差**。排查法：关掉 DN 重训一次，若 AP 反而涨了，八成是 mask 写错。')"""),
    code("""# 量化「泄漏」：如果 mask 写错（或忘了写），有多少条 GT 信息通道被打开
def leak_channels(mask, n_dn, n_match):
    '''匹配 query 能读到去噪 query 的 (query, dn) 对数。'''
    return int((~mask[n_dn:, :n_dn]).sum())

no_mask = np.zeros_like(mk)
sym_mask = mk | mk.T                    # 常见错误：想当然写成对称
print('%-28s %14s %22s' % ('mask 写法', '泄漏通道数', '去噪能否看到匹配上下文'))
for name, m_ in [('① 完全不加 mask', no_mask),
                 ('② 写成对称矩阵（常见错误）', sym_mask),
                 ('③ 官方写法（非对称）', mk)]:
    leak = leak_channels(m_, n_dn, n_m)
    ctx = '否' if m_[:n_dn, n_dn:].any() else '是'
    print('%-28s %14d %22s' % (name, leak, ctx))
assert leak_channels(no_mask, n_dn, n_m) == n_dn * n_m
assert leak_channels(sym_mask, n_dn, n_m) == 0 and sym_mask[:n_dn, n_dn:].any()
assert leak_channels(mk, n_dn, n_m) == 0 and not mk[:n_dn, n_dn:].any()
print()
print('✅ ② 虽然不泄漏，但**削弱了去噪分支从匹配分支获得的上下文**——')
print('   而去噪分支学到的定位能力本来是要迁移给匹配分支的。所以官方选了非对称。')"""),
    md("""## 7 · CDN 对比去噪：正负噪声对

DINO 的关键补充：**只有正样本时，模型只被教「往 GT 靠」，从没被教「离太远就判背景」**——
于是重复框多、置信度不校准。CDN 在 λ1 与 λ2 之间造一圈**硬负样本**，目标是 no-object。"""),
    code("""LAM1, LAM2 = 0.4, 1.2
NO_OBJECT = NUM_CLASSES          # 背景类的类别 id

def build_cdn_queries(gt_boxes, gt_labels, num_classes, groups, lam1, lam2, gamma, rng):
    '''每组 2M 个 query：前 M 正（噪声<lam1，目标=GT），后 M 负（噪声∈(lam1,lam2)，目标=背景）。'''
    qb, ql, tb, tl, is_pos, gid = [], [], [], [], [], []
    M = len(gt_boxes)
    for g in range(groups):
        pb = add_box_noise(gt_boxes, lam1, rng, lo=0.0)
        pl, _ = flip_labels(gt_labels, num_classes, gamma, rng)
        nb = add_box_noise(gt_boxes, lam2, rng, lo=lam1)
        nl, _ = flip_labels(gt_labels, num_classes, gamma, rng)
        qb += [pb, nb]; ql += [pl, nl]
        tb += [gt_boxes, gt_boxes]
        tl += [gt_labels, np.full(M, num_classes)]      # 负样本的目标 = no-object
        is_pos += [np.ones(M, bool), np.zeros(M, bool)]
        gid += [np.full(M, g), np.full(M, g)]
    return (np.concatenate(qb), np.concatenate(ql), np.concatenate(tb),
            np.concatenate(tl), np.concatenate(is_pos), np.concatenate(gid))

qb, ql, tb2, tl2, ispos, gid2 = build_cdn_queries(
    gt_boxes, gt_labels, NUM_CLASSES, 200, LAM1, LAM2, GAMMA, np.random.default_rng(9))
io = iou_pairwise(qb, tb2)
print('正样本 IoU  中位数 %.3f  均值 %.3f  最小 %.3f' % (np.median(io[ispos]), io[ispos].mean(), io[ispos].min()))
print('负样本 IoU  中位数 %.3f  均值 %.3f  最大 %.3f' % (np.median(io[~ispos]), io[~ispos].mean(), io[~ispos].max()))
print('负样本的监督目标全部是 no-object(id=%d): %s' % (NO_OBJECT, bool((tl2[~ispos] == NO_OBJECT).all())))
assert io[ispos].mean() > io[~ispos].mean() + 0.15
assert np.median(io[ispos]) > np.median(io[~ispos])
assert (tl2[~ispos] == NO_OBJECT).all() and (tl2[ispos] == np.tile(gt_labels, 200)).all()
print()
print('✅ 正负两组的噪声尺度之差，**直接定义了「多近算认领成功」这条决策边界**。')
print('   这正是 NMS 在推理期做的事，被搬到了训练期 —— 所以 DINO 的重复框显著少于 DN-DETR。')
print('⚠️  注意负样本不是「完全不重叠」，而是「近但不够近」——太远的负样本是简单负样本，没有信息量。')"""),
    md("""## 8 · look forward once vs twice：一次 detach 的代价

Deformable DETR 在层间对参考框 `detach()`（LFO）：第 i 层参数只被第 i 层的损失监督。
DINO 去掉这个 detach（LFT）：第 i 层参数同时被第 i、i+1 层的损失监督。"""),
    code("""def refine_chain(theta, b0, y, detach):
    '''3 层框细化：b_i = b_{i-1} + theta_i；每层都有辅助损失 (b_i - y)^2。
       返回 (总损失, dL/dtheta)。detach=True 时切断层间梯度（look forward once）。'''
    b = [b0]
    for t in theta:
        b.append(b[-1] + t)
    loss = sum((bi - y)**2 for bi in b[1:])
    g = np.zeros(len(theta))
    for i in range(len(theta)):
        if detach:
            g[i] = 2 * (b[i+1] - y)                       # 只有第 i 层自己的损失
        else:
            g[i] = sum(2 * (b[j+1] - y) for j in range(i, len(theta)))
    return loss, g

def curve(detach, steps=40, lr=0.02):
    theta = np.zeros(3); b0, y = 0.0, 1.0
    hist = []
    for _ in range(steps):
        loss, g = refine_chain(theta, b0, y, detach)
        hist.append(loss)
        theta -= lr * g
    return np.array(hist), theta

h_lfo, t_lfo = curve(True)
h_lft, t_lft = curve(False)
print('%-26s %9s %9s %9s %9s' % ('总损失', 'step 1', 'step 5', 'step 10', 'step 20'))
print('%-26s %9.4f %9.4f %9.4f %9.4f'
      % ('look forward once (detach)', h_lfo[0], h_lfo[4], h_lfo[9], h_lfo[19]))
print('%-26s %9.4f %9.4f %9.4f %9.4f'
      % ('look forward twice (DINO)', h_lft[0], h_lft[4], h_lft[9], h_lft[19]))
_, g_lfo = refine_chain(np.zeros(3), 0.0, 1.0, True)
_, g_lft = refine_chain(np.zeros(3), 0.0, 1.0, False)
print()
print('初始梯度对比 dL/dtheta:')
print('  LFO %s   <- 第 1 层只从 loss1 拿梯度' % np.round(g_lfo, 3))
print('  LFT %s   <- 第 1 层从 loss1+loss2+loss3 拿梯度' % np.round(g_lft, 3))
assert abs(g_lft[0]) > abs(g_lfo[0]), '第 1 层在 LFT 下拿到更多监督'
assert g_lft[-1] == g_lfo[-1], '最后一层两者相同'
assert h_lft[9] < h_lfo[9] and h_lft[19] < h_lfo[19], '同样步数下 LFT 下降更快'
print()
print('✅ 一次 detach 的代价：**早期层的框预测不为最终结果负责**。')
print('⚠️  代价也要说清楚：LFT 让早期层拿到 L 倍的梯度，等于给它们加了更大的有效学习率。')
print('    把 lr 从 0.02 提到 0.05 再跑一遍，LFT 反而会震荡到比 LFO 更差 —— ')
print('    **换 LFT 时学习率要相应保守**，这在真实训练里同样成立。')
print('⚠️  而且顺序不能颠倒 —— Deformable DETR 当初 detach 是因为早期框太差、梯度互相干扰；')
print('    是 DN 先让早期层的框变准了，去掉 detach 才划算。「前一个改进让后一个可行」。')"""),
    md("""## 9 · 一对多监督密度的账：反推 Group DETR 的加速倍数

**一对一是推理端的需求，不是训练端的最优。**
这一节把「每图每次迭代的正样本数」算清楚，并反推收敛 epoch。"""),
    code("""COCO_IMGS, GT_PER_IMG = 118287, 7.3
METHODS = [
    ('Faster R-CNN (采样后)', 256.0, '有 -> 需 NMS'),
    ('RetinaNet / FCOS (密集)', 600.0, '有 -> 需 NMS'),
    ('DETR (一对一)', GT_PER_IMG, '基本没有'),
    ('Group DETR (G=11)', GT_PER_IMG * 11, '推理只留 1 组'),
    ('H-DETR (一对多 K=6)', GT_PER_IMG * 7, '推理丢一对多分支'),
    ('Co-DETR (+密集辅助头)', GT_PER_IMG * 40, '推理丢辅助头'),
]
BUDGET = COCO_IMGS * GT_PER_IMG * 500          # DETR 训 500 epoch 累计的正样本梯度更新数
print('%-26s %14s %10s %12s %s' % ('检测器', '正样本/图/迭代', '相对DETR', '等效epoch', '推理端重复框'))
eps = {}
for name, npos, dup in METHODS:
    e = BUDGET / (COCO_IMGS * npos)
    eps[name] = e
    print('%-26s %14.1f %9.1fx %11.0f  %s' % (name, npos, npos/GT_PER_IMG, e, dup))
assert eps['DETR (一对一)'] == 500
assert 40 < eps['Group DETR (G=11)'] < 50, 'Group DETR 论文报告的加速正是这个量级'
assert eps['Co-DETR (+密集辅助头)'] < eps['H-DETR (一对多 K=6)'] < eps['DETR (一对一)']
print()
print('✅ 「500 / 11 ≈ 45 epoch」—— 与 Group DETR 论文报告的收敛加速惊人地一致。')
print('✅ 密集检测器每次迭代从一张图榨出几百条监督，DETR 只榨 7.3 条。')
print('   要拿到同样多的梯度更新，DETR 自然需要几十倍 epoch —— 这是根因的第三个角度。')"""),
    code("""# 一对多分支必须与一对一分支**分开做 self-attention**，否则去重信号被搅乱
def dedup_signal(n_o2o, n_o2m, shared):
    '''粗糙模型：self-attention 里若混入 n_o2m 个「本来就该重复」的 query，
       去重信号被稀释的比例。'''
    if not shared:
        return 1.0
    return n_o2o / (n_o2o + n_o2m)

print('%-34s %16s' % ('配置', '一对一分支的去重信号强度'))
for name, shared in [('分开 self-attention（Group/H-DETR 的做法）', False),
                     ('混在同一次 self-attention（错误做法）', True)]:
    print('%-34s %15.1f%%' % (name, dedup_signal(300, 1500, shared)*100))
assert dedup_signal(300, 1500, True) < 0.25 < dedup_signal(300, 1500, False)
print()
print('⚠️  混着做的后果：**一对一分支也开始输出重复框，NMS-free 的性质直接丢失。**')
print('    这与 DN 的 attention mask 是同一类设计约束 —— 训练期加进来的额外 query，')
print('    必须用 mask 把它们与主分支的协商过程隔开。')
print()
print('工程结论：如果推理端仍然要加 NMS，就没必要坚持一对一匹配。')
print('  「训练慢了几倍、部署还是要 NMS」是最糟糕的组合。')"""),
    md("""## ✏️ 练习 1：按参考框缩放采样偏移

实现 `scale_offsets_by_box(ref_boxes, raw_offsets, factor=0.5)`：
`ref_boxes` 是 `(Nq,4)` 的 cxcywh 归一化框，`raw_offsets` 是 `(Nq,L,K,2)` 的原始预测。
返回 `(sampling_locations, scaled_offsets)`——**偏移要乘以 `factor * (w,h)`**，
采样点 = 框中心 + 缩放后的偏移。这是 DAB-DETR / DINO 让采样范围随目标尺度自适应的做法。"""),
    code("""def scale_offsets_by_box(ref_boxes, raw_offsets, factor=0.5):
    # TODO: ① 从 ref_boxes 取出中心 (cx,cy) 与宽高 (w,h)
    #       ② scaled = raw_offsets * factor * (w,h)，注意广播到 (Nq,L,K,2)
    #       ③ locations = (cx,cy) + scaled
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
rb = np.array([[0.5, 0.5, 0.02, 0.02],      # 小框（约 27x16 px）
               [0.5, 0.5, 0.40, 0.40]])     # 大框
raw = np.ones((2, 2, 3, 2))                 # 全 1 偏移，方便手算
loc, sc = scale_offsets_by_box(rb, raw, factor=0.5)
assert loc.shape == (2, 2, 3, 2) and sc.shape == (2, 2, 3, 2)
assert np.allclose(sc[0], 0.5*0.02), '小框：偏移应被缩放到 0.01'
assert np.allclose(sc[1], 0.5*0.40), '大框：偏移应被缩放到 0.20'
assert np.allclose(loc[0], 0.5 + 0.01) and np.allclose(loc[1], 0.5 + 0.20)
raw2 = np.repeat(np.random.default_rng(0).normal(size=(1, 2, 3, 2)), 2, axis=0)  # 两行共用同一组原始偏移
loc2, sc2 = scale_offsets_by_box(rb, raw2)
spread = np.abs(sc2).mean(axis=(1, 2, 3))
print('小框采样点平均散布 %.4f  |  大框 %.4f  |  比值 %.1f'
      % (spread[0], spread[1], spread[1]/spread[0]))
assert abs(spread[1]/spread[0] - 20.0) < 1e-6, '散布之比应等于宽高之比 0.40/0.02 = 20'
print('✅ 练习 1 通过：**采样范围随目标尺度自适应** —— 小目标不会把点撒到框外去。')"""),
    md("""## ✏️ 练习 2：DN 的 attention mask

实现 `build_dn_attn_mask(n_per_group, n_groups, n_match)`，返回 `(T,T)` 的布尔矩阵，
`True = 屏蔽`。布局是 `[去噪 query] + [匹配 query]`。三条规则：
① 匹配 query 看不见任何去噪 query；② 去噪组之间互不可见（组内可见）；
③ **去噪 query 可以看匹配 query（非对称！）**。"""),
    code("""def build_dn_attn_mask(n_per_group, n_groups, n_match):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
for npg, ng, nm in [(3, 3, 5), (2, 5, 10), (1, 1, 4), (4, 2, 1)]:
    mm = build_dn_attn_mask(npg, ng, nm)
    nd = npg * ng
    assert mm.shape == (nd + nm, nd + nm) and mm.dtype == bool
    assert mm[nd:, :nd].all(), '① 匹配 query 必须看不见去噪 query'
    gg_ = np.repeat(np.arange(ng), npg)
    assert (mm[:nd, :nd] == (gg_[:, None] != gg_[None, :])).all(), '② 组间屏蔽、组内可见'
    assert not mm[:nd, nd:].any(), '③ 去噪 query 可以看匹配 query'
    assert not mm[nd:, nd:].any(), '匹配 query 之间照常协商'
mm = build_dn_attn_mask(2, 3, 4)
print('屏蔽率 %.1f%%（%d/%d 个注意力对被切断）'
      % (mm.mean()*100, mm.sum(), mm.size))
assert not (mm == mm.T).all(), 'mask 必须是**非对称**的'
print('✅ 练习 2 通过：mask 写错 = 训练时抄答案，是 DN 最容易踩的坑。')"""),
    md("""## ✏️ 练习 3：CDN 的监督目标

实现 `cdn_targets(query_boxes, gt_boxes, gt_labels, is_positive, num_classes)`：
返回 `(target_labels, target_boxes, box_loss_mask)`。
规则：正样本 → 目标类别是 GT 类别、要算框损失；
**负样本 → 目标类别是 `num_classes`（no-object）、不算框损失**（背景没有框可回归）。"""),
    code("""def cdn_targets(query_boxes, gt_boxes, gt_labels, is_positive, num_classes):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
gb = np.array([[0.3, 0.3, 0.1, 0.1], [0.7, 0.6, 0.2, 0.15]])
gl = np.array([4, 11])
qb_ = np.concatenate([gb + 0.01, gb + 0.15])
gtl = np.concatenate([gb, gb])
gll = np.concatenate([gl, gl])
pos = np.array([True, True, False, False])
tl_, tb_, bm_ = cdn_targets(qb_, gtl, gll, pos, num_classes=45)
assert tl_.tolist() == [4, 11, 45, 45], tl_.tolist()
assert np.allclose(tb_[pos], gb) and bm_.tolist() == [True, True, False, False]
assert (tl_[~pos] == 45).all(), '负样本必须是 no-object'
print('target labels:', tl_.tolist())
print('参与框损失的 query 数: %d / %d' % (bm_.sum(), len(bm_)))
print('✅ 练习 3 通过：**负样本只贡献分类损失** —— 忘了 mask 掉框损失会把背景框拉向 GT，')
print('   等于把 CDN 的负样本又变回了正样本。')"""),
    md("""## ✏️ 练习 4：监督密度台账

实现 `supervision_density(n_pos, alpha, phi)`：返回 `rho = n_pos * alpha * (1-phi)`，
以及 `rank_methods(table)`：给定 `{名字: (n_pos, alpha, phi)}`，
按 rho 从小到大返回名字列表。用它复现 DETR → Deformable → DN → DINO → Co-DETR 的演进顺序。"""),
    code("""def supervision_density(n_pos, alpha, phi):
    # TODO
    raise NotImplementedError

def rank_methods(table):
    # TODO: 返回按 rho 升序排列的名字列表
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
LEDGER = {                       # (每图每次迭代正样本数, 注意力落在目标上的质量, 匹配翻转率)
    'DETR':            (7.3,   0.0010, 0.50),
    'Deformable DETR': (7.3,   0.9000, 0.45),
    'DN-DETR':         (7.3 + 5*7.3,  0.9000, 0.10),
    'DINO':            (7.3 + 100*2*7.3, 0.9200, 0.08),
    'Co-DETR':         (7.3 + 100*2*7.3 + 300.0, 0.9200, 0.08),
}
assert abs(supervision_density(10, 0.5, 0.2) - 4.0) < 1e-9
order = rank_methods(LEDGER)
print('%-18s %12s %10s %8s %14s' % ('方法', 'n_pos', 'alpha', 'phi', 'rho'))
for k in order:
    n, a, p = LEDGER[k]
    print('%-18s %12.1f %10.4f %8.2f %14.2f' % (k, n, a, p, supervision_density(n, a, p)))
assert order == ['DETR', 'Deformable DETR', 'DN-DETR', 'DINO', 'Co-DETR'], order
assert supervision_density(*LEDGER['Deformable DETR']) / supervision_density(*LEDGER['DETR']) > 500
print()
print('✅ 练习 4 通过：**一条主线** —— 每一步演进都在抬高 rho 的某一个因子。')
print('   面试里把这张台账口述出来，比背模型列表有效得多。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def scale_offsets_by_box(ref_boxes, raw_offsets, factor=0.5):
    ctr = ref_boxes[:, None, None, :2]                 # (Nq,1,1,2)
    wh = ref_boxes[:, None, None, 2:]                  # (Nq,1,1,2)
    scaled = raw_offsets * factor * wh
    return ctr + scaled, scaled"""),
    code("""# 练习 2 参考答案
def build_dn_attn_mask(n_per_group, n_groups, n_match):
    n_dn = n_per_group * n_groups
    T = n_dn + n_match
    mask = np.zeros((T, T), dtype=bool)
    mask[n_dn:, :n_dn] = True                                  # ① 匹配看不见去噪
    g = np.repeat(np.arange(n_groups), n_per_group)
    mask[:n_dn, :n_dn] = g[:, None] != g[None, :]              # ② 组间屏蔽
    return mask                                                # ③ 去噪->匹配 不屏蔽"""),
    code("""# 练习 3 参考答案
def cdn_targets(query_boxes, gt_boxes, gt_labels, is_positive, num_classes):
    is_positive = np.asarray(is_positive, dtype=bool)
    target_labels = np.where(is_positive, gt_labels, num_classes)
    target_boxes = gt_boxes.copy()
    box_loss_mask = is_positive.copy()                         # 负样本不算框损失
    return target_labels, target_boxes, box_loss_mask"""),
    code("""# 练习 4 参考答案
def supervision_density(n_pos, alpha, phi):
    return n_pos * alpha * (1.0 - phi)

def rank_methods(table):
    return sorted(table, key=lambda k: supervision_density(*table[k]))"""),
    md("""---
## 🧪 真实工程胶囊：DINO 风格的训练配置与去噪模块骨架"""),
    code("""RECIPE = r'''
# ============ 1) mmdetection / detrex 风格的 DINO 配置要点 ============
model = dict(
    type='DINO',
    num_queries=900,                     # DINO 用 900（DETR 是 100）；密集场景要更多
    num_feature_levels=4,                # **多尺度是准入条件**；TSR 建议把 P2(stride4) 也评估进来
    with_box_refine=True,                # 迭代框细化
    as_two_stage=True,                   # encoder 出提案 -> top-K 作参考点
    dn_cfg=dict(                         # ---- 去噪（DN / CDN）----
        label_noise_scale=0.5,           # gamma：标签翻转比例
        box_noise_scale=1.0,             # lambda1：正样本噪声上界（DINO 用 1.0）
        group_cfg=dict(dynamic=True, num_groups=None, num_dn_queries=100),
    ),                                   # dynamic=True: GT 多的图自动减组数，防显存爆
    encoder=dict(num_layers=6, layer_cfg=dict(
        self_attn_cfg=dict(embed_dims=256, num_levels=4, dropout=0.0))),
    decoder=dict(num_layers=6, return_intermediate=True,   # 每层都算辅助损失
                 layer_cfg=dict(cross_attn_cfg=dict(num_levels=4, num_points=4))),
)

# ============ 2) 去噪 query 的构造（核心 20 行）============
def prepare_dn(gt_boxes, gt_labels, num_classes, num_groups,
               lam1=1.0, lam2=2.0, gamma=0.5):
    # 返回 (dn_query_boxes, dn_query_labels, targets, attn_mask)
    # 每组 2M 个 query：前 M 正（噪声<lam1），后 M 负（lam1<噪声<lam2）
    M = len(gt_boxes)
    known = gt_boxes.repeat(2 * num_groups, 1)            # 正负各一份 x G 组
    labels = gt_labels.repeat(2 * num_groups)
    # -- 标签翻转（只对正样本组或全部，看实现）--
    flip = torch.rand_like(labels.float()) < gamma
    labels[flip] = torch.randint_like(labels[flip], 0, num_classes)
    # -- 框噪声：中心平移 + 尺寸缩放，负样本用更大的噪声尺度 --
    neg = torch.zeros(2 * num_groups * M, dtype=torch.bool)
    neg[M::2 * M] = True                                  # 具体索引按 layout 定
    scale = torch.where(neg, lam2, lam1)
    delta = (torch.rand_like(known) * 2 - 1) * scale[:, None] * 0.5
    known[:, :2] += delta[:, :2] * known[:, 2:]           # **平移按框宽高缩放**
    known[:, 2:] *= 1 + delta[:, 2:]
    known = known.clamp(min=1e-4, max=1.0)
    return known, labels, neg

# ============ 3) attention mask：非对称，写错就是抄答案 ============
def dn_attn_mask(pad_size, num_groups, num_queries, single_pad):
    T = pad_size + num_queries
    m = torch.zeros(T, T, dtype=torch.bool)
    m[pad_size:, :pad_size] = True                        # 匹配 query 看不见去噪 query
    for i in range(num_groups):                           # 去噪组之间互不可见
        s, e = single_pad * 2 * i, single_pad * 2 * (i + 1)
        m[s:e, e:pad_size] = True
        m[s:e, :s] = True
    return m                                              # 去噪 -> 匹配 的列**不屏蔽**

# ============ 4) 上线前的三条自检 ============
# [1] 关掉 DN 重训一次：若验证 AP 反而更高 -> attention mask 写错了（GT 泄漏）
# [2] 打印去噪分支与匹配分支各自的 loss 曲线：去噪 loss 应在前 1000 iter 内快速下降
# [3] 按**像素尺寸分桶**看 AP：只看总 mAP 会掩盖「小目标层没接上」这类严重问题
'''
print(RECIPE)
for key in ['num_feature_levels=4', 'dn_cfg', 'box_noise_scale', 'attn_mask',
            'm[pad_size:, :pad_size] = True', '按框宽高缩放', '分桶']:
    assert key in RECIPE, key
print('✅ 配方覆盖：多尺度 / 去噪超参 / 动态组数 / 非对称 mask / 上线自检')"""),
    md("""### 小结

- **「DETR 收敛慢」要拆成两个正交根因**：① cross-attention 初期近似均匀，梯度打在错误的**空间位置**；
  ② 二分匹配翻转，梯度指向错误的**目标**。修一个另一个还在，所以两次收益可以相乘。
- **根因① 在小目标上被放大**：60 米外 16×16 的限速牌在 stride 32 特征图上占 0.25 格，
  初始注意力质量只有 **0.024%**。→ **对 TSR，多尺度不是调参选项，是准入条件。**
- **可变形注意力的两个关键点**：① 权重由 query 单独产生，**不做 Q·K 点积**（所以便宜）；
  ② 双线性插值让**采样位置本身可微**，模型有一条「学会往哪看」的直达梯度通道。
  偏移必须**按参考框宽高缩放**，否则小目标的采样点全撒到框外。
- **DN 的本质是「绕开匹配」而不是「改进匹配」**：带噪 GT 作为额外 query，监督目标已知、
  φ=0、密度高几十倍，而且**推理零开销**（去噪 query 训练时才存在）。
- **attention mask 是 DN 的成败所在，而且是非对称的**：匹配 query 看不见去噪 query，
  去噪组之间互不可见，但**去噪 query 可以看匹配 query**。写错的症状是
  「train loss 极漂亮、val AP 反而更差」。
- **DINO 的三件事各修一个短板**：CDN 用负样本教决策边界（把 NMS 的职责搬到训练期）；
  mixed query selection **只借位置不借内容**；look forward twice 让早期层为最终结果负责。
- **一对一是推理端的需求，不是训练端的最优**——Group/H-/Co-DETR 把一对多加回训练，
  推理时整块丢掉。「500 epoch ÷ 11 组 ≈ 45 epoch」这笔账值得记住。
- **一句话主线**：ρ ∝ (被监督的 query 数) × (注意力落在目标上的质量) × (匹配未翻转比例)，
  **每一步演进都在抬高其中一个因子**。

下一站：**模块 05 · DETR 工程实践** —— 学习率分组、诊断树、以及给 TSR 到底该选 DETR 还是 YOLO。"""),
]
