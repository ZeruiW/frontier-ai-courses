# -*- coding: utf-8 -*-
"""C56 模块 03 · 混合类增强：Mosaic / MixUp / CutMix / Copy-Paste。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–02（bbox 变换框架、几何增强与标注同步、光度增强）；C55 模块 01（TSR 长尾）与 C58 模块 01（类别不平衡）会让本模块的 copy-paste 部分更有落点"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_mixing_aug.ipynb'),
    ("核心参考", "Bochkovskiy et al. <em>YOLOv4</em>（Mosaic）；Zhang et al. <em>mixup</em>；Yun et al. <em>CutMix</em>；Ghiasi et al. <em>Simple Copy-Paste</em>；Ultralytics 的 <code>close_mosaic</code> 实现"),
    ("预计时长", "读 65 分钟 + 跑 65 分钟"),
]

SECTIONS = [
    ("why", "混合类增强是另一个物种：它改变的是「一张图 = 一个场景」这个假设", "".join([
        P("模块 01 的几何增强改「框在哪」，模块 02 的光度增强改「像素是什么值」。<strong>混合类增强改的是第三样东西：一张训练图里有几个场景、有多少个目标、目标之间是什么关系</strong>。它把两张或四张图的内容与标注揉进同一个样本里。"),
        P("这一步跨得很大，因为它<strong>同时破坏了两个默认假设</strong>：① 「一张图对应一次真实的相机曝光」——拼接图在物理上不存在；② 「图像内容与标注一一对应」——mixup 之后每个像素同时属于两个目标。<em>正因为跨得大，收益也大；也正因为跨得大，它必须被小心地关掉</em>。"),
        TABLE(["", "几何增强", "光度增强", "<strong>混合类增强</strong>"], [
            ["改什么", "框的位置/形状", "像素数值", "<strong>样本的构成</strong>（几个场景、几个目标）"],
            ["标注变化", "坐标变换", "不变", "<strong>标注集合被合并、裁剪、丢弃</strong>"],
            ["物理可实现性", "✅（换个视角就是）", "✅（换个天气就是）", "<strong>❌ 拼接图不对应任何一次真实曝光</strong>"],
            ["主要收益", "视角/尺度不变性", "成像条件不变性", "<strong>上下文多样性 + 小目标供给 + 长尾补齐</strong>"],
            ["主要代价", "小目标被丢弃", "语义被改掉", "<strong>训练分布偏离部署分布</strong>"],
            ["是否需要「关掉」", "否", "否", "<strong>是 —— close-mosaic 是标配</strong>"],
        ]),
        DUAL(
            "为什么混合类增强这么有效？<strong>因为检测器最缺的从来不是「同一个目标的更多变体」，而是「同一个目标出现在更多上下文里」</strong>。一块限速牌在你的数据集里可能有 2000 个实例，但它们几乎全在「高速公路 + 白天 + 龙门架」这一种上下文里。<em>模型于是学到了一堆和标志本身无关的相关性</em>（有龙门架的地方才有限速牌）。把它拼到城市街景、乡村路口、隧道口旁边，等于强行打断这些相关性。",
            "更精确地说，混合类增强攻击的是<span class=\"term\">spurious correlation</span>（虚假相关）与<span class=\"term\">context bias</span>（上下文偏置）。检测器的一个已知病理是：<strong>它会把「共现的背景」当作证据的一部分</strong>。Mosaic 通过让每张训练图包含四个互不相关的场景，把背景与目标的互信息压下去；Copy-Paste 更彻底，直接把目标搬到任意背景上。<em>但代价是同一枚硬币的另一面</em>——<strong>上下文本身在 TSR 里也是有效信息</strong>（标志有杆件、在路侧、在地平线以上），把上下文彻底打散会丢掉这个先验。<strong>这就是为什么 copy-paste 必须带约束、mosaic 必须在最后关掉。</strong>",
        ),
        CALLOUT("intuition", "本模块的一条总纲：<strong>混合类增强的每一个技巧，都在「打散上下文」和「保留合理性」之间取一个位置</strong>。Mosaic 打散得最狠（但只在训练早期用）；Copy-Paste 打散得最有针对性（但必须满足透视/位置/融合/光照四条约束）；MixUp 在检测里打散得最没有道理（所以它是这四个里争议最大的）。<em>知道每个技巧站在这条轴的哪个位置，比记住它们的实现细节有用。</em>"),
    ])),
    ("mosaic", "Mosaic 解剖：三个作用，以及每一个的量化", "".join([
        P("<span class=\"term\">Mosaic</span>（YOLOv4 引入）把四张图拼成一张，再从拼接画布上随机裁剪/缩放出一张训练图。实现只有几十行，但它同时做了三件事——<strong>面试里要求「说清 Mosaic 有什么用」，答出三个才算完整</strong>。"),
        ASCII("""      画布 2s × 2s，拼接中心 (xc, yc) 在 [0.5s, 1.5s] 内随机
      ┌──────────────────┬──────────────────────┐
      │                  │                      │
      │   img0 (右下角)   │    img1 (左下角)      │   ← 每张图只有靠近中心的
      │                  │                      │      那一部分被保留
      │            (xc,yc)●                     │
      ├──────────────────┼──────────────────────┤
      │                  │                      │
      │   img2 (右上角)   │    img3 (左上角)      │
      │                  │                      │
      └──────────────────┴──────────────────────┘
                    ↓ 缩放 + 裁剪回 s × s（真实实现里还叠加随机仿射）
      ┌────────────┐
      │            │   目标尺寸约为原来的 0.5–1.5 倍
      │            │   目标数量约为原来的 4 倍（减去被裁掉/丢弃的）
      └────────────┘

  三个副产品（不是 bug，是主要收益）：
    ① **每张训练图包含 4 个不相关场景**  → 背景-目标的虚假相关被打断
    ② **目标像素尺寸整体变小**            → 小目标样本供给暴涨
    ③ **大量目标被画布边界截断**          → 强迫模型学「部分可见也要检出」""")
        ,
        TABLE(["作用", "机制", "量化（notebook 里会实测）", "对 TSR 的意义"], [
            ["<strong>① 变相增大 batch 多样性</strong>", "1 张训练图 = 4 个场景", "同 batch size 下，<strong>每步见到的场景数 ×4</strong>；单图目标数 <strong>×3.2</strong>（4 倍减去被过滤规则丢弃的）", "小 batch（车端训练常见）下尤其有用"],
            ["<strong>② 制造更多小目标</strong>", "拼接后整体缩小", "小目标（边长 &lt; 5% 图宽）占比从 <strong>9.8% → 50.9%</strong>", "<strong>TSR 本来就是小目标任务，这是直接命中的收益</strong>"],
            ["<strong>③ 丰富上下文</strong>", "目标周围换成别的场景", "背景-类别互信息下降", "打断「龙门架 ⇒ 限速牌」这类捷径"],
            ["（副作用）截断框暴涨", "画布边界裁剪", "贴边框占比 <strong>3.4% → 11.3%（约 3.3×）</strong><sup>*</sup>", "<strong>这是 close-mosaic 的主要动机之一</strong>"],
        ]),
        P("<sup>*</sup> 这四个数字都来自 notebook 的实测（同一份合成数据，mosaic 前后对比）。<em>截断框那一项与实现方式强相关</em>：本课的实现是「拼成 2s 画布后整体缩放回 s」，YOLOv5 的真实实现是「拼成 2s 画布后<strong>裁剪</strong>回 s（叠加随机仿射）」——<strong>裁剪会切掉更多内容，所以真实实现的截断框比例还要高得多（常见报告在 25–40%）</strong>。<em>方向一致、量级更大，close-mosaic 的必要性只会更强。</em>"),
        H3("实现细节：三个必须写对的地方"),
        OL([
            "<strong>拼接中心随机</strong>。<code>(xc, yc)</code> 在 <code>[0.5s, 1.5s]</code> 内均匀采样，而不是固定在画布正中。<em>固定中心会让「四张图各占一个 1:1 象限」成为定式，模型能学到这个结构</em>（比如「图像正中的十字接缝处从不出现目标」）。随机中心让四个象限的面积比每次都不同。",
            "<strong>越界框裁剪，而不是丢弃</strong>。跨过画布边界的框要 clip 到画布内。<em>直接丢弃会把「被截断的目标」这一整类样本从训练里抹掉</em>，而真实场景里画面边缘的半个标志是常态。",
            "<strong>裁剪后的过滤规则</strong>——这是最容易写错的一环。YOLOv5 的 <code>box_candidates</code> 用三个条件：裁剪后宽高都 &gt; 2 px、长宽比 &lt; 20、<strong>裁剪后面积 / 裁剪前面积 &gt; 0.1</strong>。<em>第三条最关键：只剩 10% 的框，其框内内容与「一个完整目标」已经没什么关系，留着就是错误监督。</em>",
        ]),
        DUAL(
            "第 3 条的阈值选择对 TSR 有特别的含义。<strong><code>area_thr</code> 定得太高（比如 0.5），会把大量小目标误杀</strong>——因为小目标的框本来就小，稍微被裁一点，面积比就掉得快；<em>定得太低（比如 0.02），会留下一堆「只剩一条边」却标着完整类别的框，直接毒化训练</em>。0.1 是一个经验平衡点，但<strong>如果你的数据里小目标占比极高（TSR 正是如此），应该单独验证这个阈值</strong>。",
            "还有一个与模块 01 呼应的细节：<strong><code>wh_thr=2</code> 这个「裁剪后宽高必须大于 2 像素」的硬阈值，在 mosaic 场景下会误杀真正的小目标</strong>。原图里 8×8 的标志，经过 mosaic 的 0.5× 缩放变成 4×4，再被边界裁掉一半就是 4×2——刚好卡在阈值上被丢掉。<em>于是出现一个反直觉的现象：Mosaic 号称「制造更多小目标」，但过滤规则又在系统性地删掉最小的那一批</em>。<strong>正确做法是：把 <code>wh_thr</code> 与训练分辨率、与你关心的最小目标尺寸一起定，而不是抄默认值</strong>——notebook 的练习 1 会把这个误杀量算出来。",
        ),
        CALLOUT("warn", "Mosaic 与<strong>矩形训练（rect training）</strong>互斥：矩形训练靠「同 batch 内图像长宽比接近，减少 padding」省算力，而 mosaic 输出永远是正方形。<em>两个都开的话，rect 那部分是白配置</em>。同理，Mosaic 与「按图像尺寸分桶采样」也冲突。<strong>凡是依赖「输入图与原图有确定对应关系」的机制，遇到 mosaic 都要重新检查。</strong>"),
    ])),
    ("close", "close-mosaic：为什么必须在最后 N 个 epoch 关掉", "".join([
        P("<strong>close-mosaic 是现在所有主流 YOLO 实现的标配</strong>（Ultralytics 默认 <code>close_mosaic=10</code>，即最后 10 个 epoch 关闭）。它的原理很少被讲透，但其实非常干净：<strong>Mosaic 制造的训练分布与部署分布之间有一个可以量化的鸿沟，训练末期必须把这个鸿沟合上，让模型在「真实分布」上完成最后的收敛。</strong>"),
        ASCII("""训练时间线（总 100 epoch，close_mosaic=10）

  epoch  0 ──────────────────────────────── 90 ──────────── 100
         │◄────── Mosaic ON (p=1.0) ──────►│◄─ Mosaic OFF ─►│
         │                                 │                │
  训练分布 │  目标偏小、目标偏多、大量截断框     │  与验证/部署分布一致 │
  优化目标 │  学「在杂乱上下文里找小目标」      │  学「在真实构图上精定位」│
         │                                 │                │
  与部署分布│      W1 距离 ≈ 大               │   W1 距离 ≈ 0    │
  的差距   │                                 │                │

  三个鸿沟（notebook 会把每个都量出来）：
    ① **尺寸分布漂移**：mosaic 下目标像素尺寸整体缩小约 2 倍
    ② **截断框比例漂移**：贴边框从约 3% 涨到 30%+，模型学到「贴边也算完整目标」
    ③ **目标密度漂移**：单图目标数 ×4，NMS/分配的竞争强度与部署时不同""")
        ,
        TABLE(["鸿沟", "Mosaic 开", "Mosaic 关 / 部署", "不关掉的后果"], [
            ["目标像素尺寸中位数", "<strong>0.50×</strong>（W1 距离 ≈ 9 px）", "1.0×", "模型的尺度先验偏小，大目标定位变差"],
            ["贴边（截断）框占比", "<strong>11.3%</strong>（真实实现更高）", "3.4%", "<strong>回归头学会「框可以贴边」→ 部署时产生贴边假阳</strong>"],
            ["单图目标数", "<strong>3.2×</strong>", "1×", "分配与 NMS 的竞争强度不匹配"],
            ["背景-目标互信息", "被打断", "真实存在", "丢掉「标志在路侧、有杆件」这类有效先验"],
            ["图像统计（拼接缝）", "有硬接缝", "无", "模型可能把硬边当特征"],
        ]),
        DUAL(
            "为什么是「最后关掉」而不是「一直不用」或者「一直用」？<strong>因为 Mosaic 在训练早期与晚期的作用完全不同</strong>。早期模型什么都不会，需要的是<em>大量、多样、廉价的监督信号</em>——Mosaic 把每步的有效样本数翻四倍，正好；晚期模型已经会了，需要的是<em>在真实分布上精调定位与置信度</em>——此时 Mosaic 提供的样本反而在把模型往错误的分布上拉。<strong>这本质上是一种课程学习（curriculum）：先学「在困难分布上大致会」，再学「在真实分布上做准」。</strong>",
            "有一个常被误解的点值得澄清：<strong>close-mosaic 的收益主要体现在定位精度（高 IoU 阈值下的 AP）上，而不是召回</strong>。原因是回归头对分布漂移最敏感——它要学的是「框的四个数应该是多少」，而 mosaic 系统性地把框改小、改成截断的。<em>分类头相对不敏感（一块标志在哪个上下文里都还是那块标志）</em>。<strong>所以验证 close-mosaic 是否起作用，要看 AP<sub>75</sub> 和 AP<sub>90</sub> 的变化，而不是 AP<sub>50</sub></strong>；只看 AP<sub>50</sub> 常常看不出差别，然后得出「close-mosaic 没用」的错误结论。",
        ),
        CALLOUT("danger", "<p><strong>面试高频追问：「close-mosaic 关多少个 epoch 合适？」</strong>不要答一个数字，要答一个推理：</p><p>「<strong>关闭的 epoch 数要够模型在真实分布上重新收敛，所以它与学习率调度耦合</strong>。如果关闭窗口落在学习率已经衰减到极小的阶段，模型根本动不了，等于没关；<em>所以实践中要保证关闭窗口内学习率还有可用的量级</em>。10 个 epoch 是 100–300 epoch 训练下的经验值；<strong>短训练（如 50 epoch）下按比例缩到 3–5，长训练下不必线性放大——关键是「窗口内的有效更新步数」而不是 epoch 数</strong>。另外关闭时最好同时关掉 mixup 与强 copy-paste，因为它们制造的是同一类分布漂移。」</p><p><em>这个回答的价值在于：它把一个超参数还原成了它背后的机制（分布漂移 + 有效更新步数），这正是面试官想听的。</em></p>", "别答数字，答机制"),
        CALLOUT("warn", "一个真实的工程坑：<strong>关闭 mosaic 的同时，dataloader 的 collate 逻辑、缓存策略、甚至每个 epoch 的迭代步数都可能变化</strong>（因为 mosaic 会改变有效样本数的计算方式）。Ultralytics 的实现是在 close 时<em>重建 dataloader</em>。<em>自己实现时如果只是把 <code>p_mosaic</code> 设成 0 而没处理这些，可能出现「最后 10 个 epoch 的日志步数对不上」这类诡异现象</em>。"),
    ])),
    ("mixcut", "MixUp 与 CutMix 在检测里：为什么争议最大", "".join([
        P("<span class=\"term\">MixUp</span> 与 <span class=\"term\">CutMix</span> 在图像分类上是公认有效的强正则化，但搬到检测上，它们的<strong>理论基础被抽掉了一半</strong>。理解这一点比记住「YOLOv5 默认 mixup=0.0、YOLOv8-x 才开」更重要。"),
        MATH(r"\text{分类：}\;\tilde{x}=\lambda x_a+(1-\lambda)x_b,\quad \tilde{y}=\lambda y_a+(1-\lambda)y_b \qquad\Big|\qquad \text{检测：}\;\tilde{x}=\lambda x_a+(1-\lambda)x_b,\quad \tilde{\mathcal{B}}=\mathcal{B}_a\cup\mathcal{B}_b"),
        P("<strong>差别就在右半边</strong>：分类的标签是一个概率向量，可以线性插值，混合后的标签在数学上仍然是一个合法的目标分布；<em>检测的标签是一个「框的集合」，集合没有线性结构</em>。工程上的做法是取<strong>并集</strong>——于是每个目标都以 <code>λ</code> 或 <code>1-λ</code> 的不透明度出现，却被要求以 100% 的置信度被检出。<strong>「半透明的目标要按完整目标监督」这件事，在真实世界里没有对应物。</strong>"),
        TABLE(["方法", "在分类里的依据", "在检测里的变体", "主要问题", "实践建议"], [
            ["<strong>MixUp</strong>", "标签可线性插值 → 鼓励线性决策边界", "图像加权平均 + <strong>标注取并集</strong>", "<strong>目标半透明但按完整监督</strong>；与部署分布差异极大", "大模型 + 长训练下小幅使用（p≈0.1–0.15）；<strong>小模型别开</strong>"],
            ["<strong>CutMix</strong>", "剪贴块的标签按面积加权", "剪贴矩形 + 标注并集/按可见度过滤", "<strong>矩形会切断已有目标</strong>：大目标 53% 被部分覆盖，<strong>小目标 27% 变成幽灵框</strong>", "检测里基本被 <strong>Copy-Paste 取代</strong>"],
            ["<strong>Mosaic</strong>", "（无分类对应）", "4 图拼接，标注拼接后裁剪", "分布漂移（见上一节）", "<strong>默认开，最后 N epoch 关</strong>"],
            ["<strong>Copy-Paste</strong>", "（无分类对应）", "实例级抠图粘贴 + 标注追加", "需要实例掩码；需要合理性约束", "<strong>长尾场景的首选</strong>（下一节）"],
        ]),
        DUAL(
            "<strong>CutMix 在检测里的具体害处是可以量化的，而且 TSR 落在更糟的那一侧</strong>。notebook 实测：对大目标为主的分布（COCO 式），一次随机 CutMix 让 <strong>53% 的 GT 被部分覆盖</strong>——半个目标标着完整框；<em>而对小目标为主的分布（TSR 式），主要受损方式变成了「<strong>整体被盖住而标注仍在</strong>」（27.5%）</em>。<strong>后者是幽灵框（phantom box）：模型被告知「这里有一块标志」，而那块区域现在是另一张图的内容——它直接教模型在无关纹理上报警，比部分截断更毒。</strong>两种加起来，小目标分布下有 <strong>41% 的 GT 收到了错误监督</strong>。",
            "这正是 <strong>Copy-Paste 相对 CutMix 的根本优势</strong>：Copy-Paste 粘贴的是<em>带掩码的实例</em>，它知道自己贴了什么、贴在哪；被遮住的已有目标可以按可见度重新计算或直接删除标注。<strong>「有实例掩码」这一个差别，把一个盲目的操作变成了一个可控的操作</strong>。<em>代价是需要实例级掩码——但对交通标志这种形状规整（圆/三角/矩形）的目标，掩码可以从框 + 形状先验近似出来，成本远低于一般实例分割标注。</em><strong>这是 TSR 特别适合 copy-paste 的一个具体理由，面试可以提。</strong>",
        ),
        CALLOUT("warn", "MixUp 在检测里还有一个隐蔽问题：<strong>它与 BN 统计不友好</strong>。混合后的图像其像素分布的方差被压缩（两张图平均后，方差约降到 <code>λ²+(1-λ)²</code> 倍，<code>λ=0.5</code> 时只剩一半）。<em>BN 层在训练时看到的是低方差输入，推理时看到的是正常方差输入</em>——这是另一种训练-部署鸿沟。<strong>症状是「训练 loss 很好看、验证一开始就差」，容易被误判成过拟合。</strong>"),
    ])),
    ("copypaste", "Copy-Paste：长尾类别最直接的解法", "".join([
        P("到这里可以下一个明确的判断：<strong>在 TSR 这类「类别极度长尾 + 目标形状规整 + 上下文有强先验」的任务上，Copy-Paste 是混合类增强里价值最高的一个</strong>，而且高出一大截。理由不复杂——它是<em>唯一一个能直接、定向地增加特定类别样本数</em>的增强。"),
        P("交通标志的长尾有多极端？notebook 里合成的分布（Zipf 指数 1.8、50 类）就是一个真实量级的例子：<strong>头部类 10941 个实例，尾部最稀有的类只有 10 个，比例 1094 : 1；而 37 个尾部类加起来只占实例总数的 5.6%</strong>。对只有 10 个实例的类，任何重采样（C58 模块 01）都只是把同样 10 张图反复喂给模型——<em>模型很快就把这 10 张背下来了，泛化毫无进展</em>。而 Copy-Paste 把这 10 个实例贴到几千个不同的背景、尺度、光照下，虽然实例本身没变多，<strong>「实例 × 上下文 × 尺度 × 光照」的组合数直接放大了几个数量级</strong>。"),
        MATH(r"N^{\text{eff}}_c = n_c + \sum_{i=1}^{M} k_{c,i}\quad\text{（有效样本数）},\qquad D^{\text{eff}}_c = \underbrace{n^{\text{uniq}}_c}_{\text{不变}}\times\underbrace{|\mathcal{C}|\cdot|\mathcal{S}|\cdot|\mathcal{L}|}_{\text{上下文×尺度×光照}}"),
        DUAL(
            "<strong>但必须诚实地讲清楚 copy-paste 到底提升了什么、没提升什么</strong>。它提升的是<em>上下文多样性</em>：同一块「注意落石」牌出现在 5000 种背景、5000 种尺度、5000 种光照下。<em>它没有提升的是「这个类别本身的视觉多样性」</em>——如果那 12 个实例全是同一个厂家、同一个角度、同一种褪色程度拍的，copy-paste 之后模型见到的仍然只是这 12 种外观。<strong>所以 copy-paste 能救「上下文过拟合」，救不了「实例外观过拟合」。</strong>",
            "这个区分在实践中非常重要，因为它决定了<strong>下一步该做什么</strong>：如果 copy-paste 之后尾部类的召回上来了但精度还是差（大量假阳），说明模型学到的是「见到这个特定外观就报」——问题在实例多样性，<em>解法是去采集/挖掘更多真实实例（C58）</em>，而不是继续加 copy-paste 的比例。<strong>反之如果加了 copy-paste 之后召回明显上来了，说明原来的瓶颈确实是上下文，可以继续加</strong>。<em>能说出「copy-paste 提升有效样本数但不提升有效多样性」这句话，并给出下一步的判据，是这个话题上最有分量的回答。</em>",
        ),
        TABLE(["长尾解法", "作用机制", "对 12 个实例的稀有类", "代价"], [
            ["重采样（repeat factor）", "同样的图看更多次", "<strong>过拟合那 12 张</strong>", "低，但收益也低"],
            ["重加权（Focal / EQL / CB Loss）", "调梯度权重", "梯度是大了，但信息量没变", "低；可能压制头部类"],
            ["logit adjustment", "推理时按先验修正", "改善排序，不改善特征", "<strong>零成本</strong>，值得先试"],
            ["<strong>Copy-Paste</strong>", "<strong>上下文/尺度/光照组合爆炸</strong>", "<strong>有效样本数：尾部类中位数 ×7，最稀有类 ×20</strong>（notebook 实测，用 1/√n 加权）", "需实例掩码 + 四条约束"],
            ["定向采集/挖掘", "真正增加实例多样性", "<strong>唯一能根治的办法</strong>", "<strong>最高</strong>（时间以周/月计）"],
        ]),
        CALLOUT("intuition", "决策顺序很清楚：<strong>先做零成本的（logit adjustment）→ 再做低成本的（重采样/重加权）→ 然后做 copy-paste（中成本、高收益）→ 最后才是定向采集（高成本、唯一根治）</strong>。<em>copy-paste 的位置恰好在「便宜的都做完了，贵的还没开始」这个中间地带，所以它常常是投入产出比最高的一步。</em>"),
    ])),
    ("constraints", "Copy-Paste 的四条合理性约束：贴到天上的标志会教坏模型", "".join([
        P("Copy-Paste 的收益完全取决于「贴得合不合理」。<strong>不带约束的随机粘贴，收益会被它制造的错误先验抵消甚至反超</strong>：模型会学到「标志可能出现在任意位置、任意尺度」，而这恰恰否定了 TSR 里最有价值的一条先验。四条约束，按重要性排序。"),
        H3("约束一：尺度必须符合透视"),
        P("这是四条里最能精确表达的一条，而且推导很短。设焦距 <code>f</code>、地平线所在行 <code>y_h</code>、相机高度 <code>h_cam</code>、标志物理直径 <code>S</code>、安装高度（下缘离地）<code>H_m</code>。对距离 <code>Z</code> 处的标志："),
        MATH(r"s_{px}=\frac{fS}{Z},\qquad y_h-y_{bot}=\frac{f\,(H_m-h_{cam})}{Z}\quad\Longrightarrow\quad \boxed{\;s_{px}=\frac{S}{H_m-h_{cam}}\;\bigl(y_h-y_{bot}\bigr)\;}"),
        P("<strong>距离 <code>Z</code> 被消掉了</strong>：标志的像素尺寸与「它的下边缘在地平线以上多少像素」成<em>严格的正比</em>，比例系数只由物理量决定。因为安装高度有一个范围（柱式牌下缘通常 2.0–3.2 m，取 <code>h_cam = 1.5 m</code>），这条直线变成一条<strong>合法带</strong>："),
        ASCII("""       s_px（标志像素尺寸）
         ▲
         │                                    ╱  上界：H_m = 2.0 m（矮杆）
      80 ┤                                 ╱      斜率 = S/0.5 = 1.20
         │                              ╱
      60 ┤                           ╱          ╱
         │                        ╱          ╱
      40 ┤        ✗ 太大        ╱  ✅ 合法带 ╱
         │      （尺寸暗示很近，  ╱        ╱
      20 ┤        位置暗示很远） ╱      ╱      下界：H_m = 3.2 m（高杆/悬臂）
         │                  ╱     ╱             斜率 = S/1.7 = 0.35
       0 ┼───────────────╱───╱────────────────────────►
         0        20        40        60        80    (y_h − y_bot)：下缘在地平线以上多少像素

  两类必须拒绝的粘贴：
    ✗ **贴到天上**：y_bot 很小但 s_px 也很小 → 位置暗示 Z 很近、尺寸暗示 Z 很远，自相矛盾
    ✗ **贴到路面**：y_bot > y_h（地平线以下）→ 柱式标志的下缘不可能低于地平线
  合法性判据（等价说法）：**由尺寸反推的 Z 与由位置反推的 Z，必须在安装高度范围内自洽。**""")
        ,
        H3("约束二：位置必须合法"),
        UL([
            "<strong>地平线以上</strong>——柱式/悬臂式标志的下缘高于相机光心，成像必然在地平线之上。<em>贴到路面上等于教模型「路面中央可能有标志」，会直接制造对地面反光、井盖、路面标线的误检。</em>",
            "<strong>不能压住已有目标</strong>——与已有 GT 的 IoU 超过阈值（经验值 0.15）就换位置；否则被压住的那个目标的标注就成了错误监督（框还在，内容被换掉了）。",
            "<strong>要在图像内完整或近似完整</strong>——贴一个只露出 20% 的实例，等于人为制造截断样本；截断样本应该来自真实截断，而不是粘贴的副产品。",
            "<strong>（可选，更高级）语义合法区域</strong>——用车道线/可行驶区域/天空分割结果，限定只能贴在「路侧带」。<em>这一条在有分割标注时非常有效，没有时用地平线约束近似即可。</em>",
        ]),
        H3("约束三：边缘要融合"),
        P("硬粘贴会留下两种伪影：<strong>① 矩形接缝</strong>（连源背景一起贴过来时最明显）；<strong>② 轮廓锯齿</strong>（缩放时掩码边缘的重采样阶梯）。前者必须消除——它是完全人造的、模型一学一个准的捷径；后者只需要 <strong>1–2 px 的羽化</strong>。"),
        CALLOUT("warn", "<strong>羽化过头是另一个错误。</strong>真实的交通标志在图像上有<em>清晰的边缘</em>；把粘贴实例羽化 5–9 px，它看起来会像半透明的贴纸，制造出一种真实数据里不存在的「软边目标」。<em>症状是：模型在真实硬边标志上的边界回归变差</em>。<strong>羽化半径应该与图像本身的边缘锐度匹配</strong>——notebook 会把「粘贴实例的边缘对比度 vs 图像里真实目标的边缘对比度」量出来作为判据。"),
        H3("约束四：光照要匹配"),
        P("一个在正午阳光下拍的实例，贴到一张黄昏或隧道内的图上，亮度会明显不协调。<strong>正确做法是把实例的亮度与对比度对齐到粘贴处的局部背景统计</strong>——但<em>只对齐亮度与对比度，绝不对齐色相与饱和度</em>。"),
        DUAL(
            "为什么色相不能匹配？<strong>因为模块 02 的结论在这里直接适用：交通标志的颜色就是语义</strong>。做一次完整的 color transfer（把实例的 RGB 均值/方差都对齐到背景），会把一块红牌往背景色调上拉——如果背景偏黄（黄昏），红牌就被拉黄了。<em>这跟色相抖动过强是同一个错误，只是伪装成了「让粘贴更自然」。</em>",
            "严谨的做法是<strong>在亮度通道上做匹配、在色度通道上保持不变</strong>：计算粘贴处局部背景的平均亮度与源实例所在背景的平均亮度之比 <code>g</code>，把实例整体乘以 <code>g</code>（乘性亮度——模块 02 证明过它<em>色相与饱和度都严格不变</em>），再对齐对比度。<strong>「用乘性亮度做光照匹配」这个选择不是随便定的，它有精确的色彩代数依据</strong>。<em>另外 <code>g</code> 要 clip（比如限制在 [0.5, 2.0]），否则从白天贴到夜景时会把实例压成一团黑，反而制造了不存在的样本。</em>",
        ),
        CALLOUT("intuition", "四条约束可以记成一句话：<strong>「尺度对得上距离、位置对得上物理、边缘对得上锐度、亮度对得上光照」</strong>。<em>做不到全部就按顺序做——尺度约束的收益远大于边缘融合，先做对的那个。</em><strong>面试里被问「copy-paste 怎么做」，只答「把目标抠出来贴到别的图上」是不及格的；把这四条说出来，并说清楚「为什么贴到天上会教坏模型」，才是及格线。</strong>"),
    ])),
    ("bank", "实例库工程：抠图、质量筛选与采样策略", "".join([
        P("Copy-Paste 的另一半工作量在<strong>实例库（instance bank）</strong>上。库的质量直接决定收益上限——<em>一个塞满了模糊、截断、遮挡实例的库，贴得越多伤害越大</em>。"),
        TABLE(["筛选维度", "判据", "阈值（经验起点）", "为什么", "不筛的后果"], [
            ["<strong>源尺寸</strong>", "原图里的实例边长", "<strong>≥ 16 px</strong>", "小于这个再放大就是马赛克", "库里全是糊的，模型学到「糊的也算标志」"],
            ["<strong>清晰度</strong>", "Laplacian 方差", "取分布的 p30 以上", "剔除运动模糊/失焦实例", "同上，且会削弱边缘回归"],
            ["<strong>截断</strong>", "框是否贴图像边缘", "<strong>不入库</strong>", "截断实例的掩码不完整", "贴出来是「半块牌标着整框」"],
            ["<strong>遮挡</strong>", "标注的 occluded 标志 / 掩码连通性", "遮挡 &gt; 20% 不入库", "掩码里混入遮挡物", "把树叶、车辆一起贴过去"],
            ["<strong>长宽比</strong>", "w/h 偏离类别典型值", "偏离 &gt; 30% 剔除", "多半是标注错误", "错误标注被复制放大数百倍"],
            ["<strong>类别可信度</strong>", "用现有模型回检的置信度", "&lt; 0.5 人工复核", "库里的标注错误会被指数放大", "<strong>一个错标实例污染上千张训练图</strong>"],
        ]),
        DUAL(
            "最后一行值得单独强调：<strong>实例库是一个「错误放大器」</strong>。普通训练集里一个错标样本影响一个样本；<em>实例库里一个错标实例会被贴进成百上千张训练图，等价于成百上千个错标样本</em>。所以<strong>实例库的标注质量要求比普通训练集高一个数量级</strong>，值得为它单独做一轮人工复核——这是少数几个「人工复核明显划算」的环节。",
            "采样策略上，一个稳健的默认是<strong>按 <code>1/√n_c</code> 加权采样</strong>（<code>n_c</code> 是类 <code>c</code> 的原始实例数），并只对尾部类做粘贴。<em>用 <code>1/n_c</code> 会过度倾斜到最稀有的那一两个类</em>（它们恰好是实例外观多样性最差的），<code>1/√n_c</code> 是一个更温和的平衡。<strong>每张图粘贴的数量用泊松分布（均值 1–3）而不是固定值</strong>，避免模型学到「每张图恰好多 2 个目标」这种结构。<em>另外要留一部分图完全不粘贴（比如 50%），否则「所有训练图都被动过手脚」，验证时反而不匹配。</em>",
        ),
        H3("从框到掩码：TSR 的一个便宜捷径"),
        P("通用 copy-paste（Ghiasi et al.）依赖实例分割掩码，标注成本很高。<strong>但交通标志的形状是被标准规定死的</strong>：禁令/指示是圆形，警告是三角形（中国黄底 / 欧洲白底红边），指路是矩形，停车让行是八边形。<em>于是可以从「框 + 类别 → 形状模板 → 掩码」，不需要任何额外标注</em>。"),
        CALLOUT("intuition", "<strong>「形状先验能替代实例掩码标注」是 TSR 特别适合 copy-paste 的技术理由</strong>，也是一个很好的面试素材：它展示了<em>你会利用领域知识把一个昂贵的需求变便宜</em>。<em>需要注意的边界是：透视会让圆变椭圆、三角变斜三角，所以模板要按框的长宽比做仿射；而严重倾斜（对向车道的侧视标志）用模板会不准，这类实例干脆不入库。</em>"),
    ])),
    ("interaction", "增强强度 × 模型容量 × 训练时长：三者是耦合的", "".join([
        P("本模块所有技巧都有一个共同的超参：<strong>强度</strong>（mosaic 概率、mixup 的 <code>λ</code> 分布、每图粘贴数）。而强度不是一个可以独立调的旋钮——<strong>它与模型容量、训练时长强耦合</strong>。这条规律解释了大量「照抄大模型配置结果掉点」的事故。"),
        TABLE(["", "小模型 + 短训练", "小模型 + 长训练", "大模型 + 长训练"], [
            ["最优增强强度", "<strong>最低</strong>", "中", "<strong>最高</strong>"],
            ["强增强下的症状", "<strong>欠拟合</strong>：训练 loss 高、验证也差", "收敛慢但最终能到", "收益最大"],
            ["弱增强下的症状", "尚可（本来容量就有限）", "<strong>过拟合</strong>", "<strong>严重过拟合</strong>"],
            ["典型配置例子", "YOLOv8n：mixup=0, copy_paste=0", "YOLOv8s/m：轻度", "YOLOv8x：mixup≈0.15, copy_paste≈0.3"],
            ["最容易犯的错", "<strong>抄 x 号模型的增强配置</strong>", "训练轮数不够就下结论", "增强不够，浪费容量"],
        ]),
        DUAL(
            "机制其实很朴素：<strong>增强把训练分布撑宽，而模型能「吸收」多少宽度，取决于它的容量与它被允许训练多久</strong>。撑得比模型能吸收的还宽，模型就在一个学不完的分布上做欠拟合——<em>症状是训练 loss 和验证指标一起差，很容易被误诊成「学习率不对」或「数据有问题」</em>。<strong>「小模型 + 强增强 = 欠拟合」是一个应该形成条件反射的诊断</strong>。",
            "还有一个必须知道的推论：<strong>在短训练下比较两套增强配方是不公平的</strong>。强增强需要更长的训练才能兑现收益，短训练下它一定输给弱增强——<em>于是你会得出「强增强没用」的结论，而这个结论只在你那个训练预算下成立</em>。<strong>正确的消融必须在「每套配方都训到收敛」的前提下比较，或者至少明确声明「在 X epoch 预算下」这个限定条件</strong>。<em>这一条在模块 05 会展开成完整的消融设计方法论；在面试里，能主动指出「这个对比在多少 epoch 下做的」是很强的信号。</em>",
        ),
        CALLOUT("danger", "一个真实且高频的事故：<strong>从 YOLOv8x 的配置文件直接改 <code>model=yolov8n</code> 去训车端模型</strong>。x 号模型的默认增强里带 <code>mixup=0.15</code>、<code>copy_paste=0.3</code>、强 mosaic，n 号模型的容量只有它的 1/40。<em>结果是训练 loss 降不下去、mAP 比默认配置还低，然后花两周去查数据和学习率</em>。<strong>换模型规模时，增强强度必须一起改</strong>——这是 Ultralytics 在不同规模的默认配置里给出不同增强参数的原因，但很多人只改了模型名。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("混合类增强是「工程经验远远跑在理论前面」的典型领域。几个真正开放的问题："),
        UL([
            "<strong>Mosaic 为什么有效，缺少令人满意的解释</strong>。现有说法（增大等效 batch、增加小目标、丰富上下文）都是现象描述，不是机制。<em>特别是「为什么一张物理上不存在的拼接图能提升在真实图上的表现」，与「训练分布必须接近部署分布」这条常识直接冲突</em>——close-mosaic 的存在恰恰说明这个冲突是真实的。<strong>一个可能的方向是把它看作隐式的正则化/课程学习，但目前没有能预测「关多少 epoch 最优」的理论。</strong>",
            "<strong>Copy-Paste 的合理性约束几乎没有被系统研究</strong>。Ghiasi et al. 的 <em>Simple Copy-Paste</em> 的核心发现之一恰恰是「简单地随机粘贴（不做尺度/位置约束）就很有效」——这与本模块强调的四条约束表面矛盾。<em>可能的解释是：COCO 的目标尺度分布本来就宽、上下文先验本来就弱，所以约束的边际收益小；而 TSR 的上下文先验非常强（地平线、路侧、杆件），破坏它的代价就大得多</em>。<strong>「约束的收益随任务的上下文先验强度而变化」这个假设，据我所知还没有被系统验证过</strong>——这是一个很好的小课题。",
            "<strong>合成实例（而非真实抠图）能否用于 copy-paste</strong>。交通标志的样式是标准化的，理论上可以从矢量图直接渲染任意类别、任意视角、任意褪色程度的实例——<em>这能同时解决「有效样本数」和「有效多样性」两个问题</em>。障碍是渲染实例与真实实例之间的域差（反光膜的各向异性反射、脏污、老化），以及模型会不会学到「渲染指纹」。<strong>这条路对极稀有类别（一年遇不到几次的标志）几乎是唯一可行的方案。</strong>",
            "<strong>增强与标签分配的交互被严重低估</strong>。Mosaic 大幅改变目标密度与尺度分布，而 SimOTA / TaskAligned 这类动态分配策略的行为强依赖于这两者（C53 模块 02）。<em>「同一套分配策略在 mosaic 开与关时表现不同」是可观察的，但几乎没有工作把两者联合设计</em>。<strong>close-mosaic 之所以有效，可能有一部分原因就在分配策略上，而不只是回归头。</strong>",
            "<strong>增强强度的自动调节</strong>。既然强度与容量、训练时长耦合，理想做法是让强度<em>在训练中自适应</em>（早期强、后期弱，或按训练/验证 gap 反馈调节）。close-mosaic 是这个思路最粗糙的一个实例（二值开关）。<strong>连续调度、按类别调度（尾部类保持强 copy-paste、头部类早早关掉）目前都还是手工经验。</strong>",
            "<strong>生成模型做 copy-paste 的实例源</strong>。用扩散模型在给定背景上「画出」一个稀有标志，理论上能同时保证上下文合理与实例多样。<em>但与模块 02 提到的问题一样：生成过程可能改变标志的语义内容（把「限速 40」画成「限速 60」）</em>，而这类错误直接制造错标签。<strong>「可控到语义级别的生成 + 自动校验」是这条路的前提，目前还不成熟。</strong>",
        ]),
        CALLOUT("paper", "必读：Bochkovskiy, Wang &amp; Liao, <em>YOLOv4: Optimal Speed and Accuracy of Object Detection</em>（2020，Mosaic 的出处与「bag of freebies」的系统整理）；Ghiasi et al., <em>Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation</em>（CVPR 2021，copy-paste 的关键实证，注意它对「简单随机粘贴」的结论与强上下文先验任务的差异）；Zhang et al., <em>mixup: Beyond Empirical Risk Minimization</em>（ICLR 2018）与 Yun et al., <em>CutMix</em>（ICCV 2019）——读的时候重点想「标签插值这一步在检测里怎么办」；Dwibedi, Misra &amp; Hebert, <em>Cut, Paste and Learn</em>（ICCV 2017，copy-paste 的早期形态，其中关于「融合伪影会成为捷径」的分析至今有效）；Ultralytics YOLOv8/v11 的 <code>close_mosaic</code> 与各规模默认超参（工程上最直接的参照，注意不同规模模型的增强强度差异）。相邻课程：C53 模块 02（标签分配与 mosaic 的交互）、C56 模块 04（流水线与吞吐）、C56 模块 05（消融验证）、C57（小目标）、C58 模块 01（长尾处理谱系）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md(r"""# 03 · 混合类增强（Mosaic / close-mosaic / MixUp / CutMix / Copy-Paste）

目标：把四个「揉图」技巧从「调库参数」变成**可以量化其代价与收益的操作**。
重点是两件事：**close-mosaic 到底在补什么鸿沟**，以及
**带透视约束的 Copy-Paste 如何救长尾类**。

本 notebook 你会亲手实现：
1. **Mosaic**：4 图拼接、随机中心、框平移与裁剪、`box_candidates` 过滤规则；
2. Mosaic 三个作用的量化：**小目标占比 8% → 50%**、单图目标数 ×4、**贴边框 3% → 30%+**；
3. **close-mosaic 的分布漂移**：用 Wasserstein-1 距离量出训练分布与部署分布的鸿沟，
   并画出「关闭后鸿沟归零」的训练时间线；
4. **CutMix 的具体害处**：统计随机矩形会让多少比例的已有 GT 变成「半个目标标着完整框」；
5. **透视约束**：推导并实现 `s_px = S/(H_m - h_cam) · (y_h - y_bot)` 的**合法尺度带**；
6. **Copy-Paste 全流程**：实例库构建 → 质量筛选（Laplacian 清晰度）→ 合法位置采样 →
   羽化融合 → **乘性亮度光照匹配**（色相严格不变）；
7. **长尾提升的量化**，以及一个必须讲清楚的区分：
   **有效样本数涨了几百倍，有效「实例多样性」一点没涨**；
8. **增强强度 × 模型容量 × 训练时长**的耦合模拟：证明最优强度随容量与时长单调上升。

> 心智模型：**混合类增强在「打散上下文」与「保留合理性」之间取位置。
> Mosaic 打散得最狠，所以必须最后关掉；Copy-Paste 打散得最有针对性，所以必须带约束。**"""),

    md(r"""## 1 · 玩具检测数据：框、IoU、以及一个长尾类别分布"""),

    code(r"""import numpy as np

rng = np.random.default_rng(20)
np.set_printoptions(precision=4, suppress=True)

S_IMG = 160                      # 源图边长（正方形，便于 mosaic 的四象限算术）
SMALL_THR = 0.05 * S_IMG         # 「小目标」= 边长 < 图像边长的 5%（≈ COCO 的 32/640）

def make_sample(seed):
    # 生成一张玩具图 + 它的框与类别。图像内容用色块，重点在框的统计。
    r = np.random.default_rng(seed)
    img = np.full((S_IMG, S_IMG, 3), 0.35) + r.normal(0, 0.03, (S_IMG, S_IMG, 3))
    n = int(r.integers(2, 5))
    boxes, labels = [], []
    for _ in range(n):
        side = float(np.clip(r.lognormal(np.log(16.0), 0.5), 4, 64))   # 中位数 16 px
        x0 = r.uniform(2, S_IMG - side - 2); y0 = r.uniform(2, S_IMG - side - 2)
        if r.random() < 0.03:            # 少量**真实**截断样本（画面边缘的半个目标）
            e = int(r.integers(0, 4))
            if e == 0:   x0 = -side * r.uniform(0.2, 0.6)
            elif e == 1: y0 = -side * r.uniform(0.2, 0.6)
            elif e == 2: x0 = S_IMG - side * r.uniform(0.4, 0.8)
            else:        y0 = S_IMG - side * r.uniform(0.4, 0.8)
        bx = [max(x0, 0.0), max(y0, 0.0), min(x0 + side, S_IMG), min(y0 + side, S_IMG)]
        boxes.append(bx)
        labels.append(int(r.integers(0, 8)))
        xi0, yi0, xi1, yi1 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
        img[yi0:yi1, xi0:xi1] = r.uniform(0.15, 0.9, 3)
    return np.clip(img, 0, 1), np.array(boxes, dtype=float), np.array(labels)

def box_wh(b):
    return b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]

def iou_matrix(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x0 = np.maximum(a[:, None, 0], b[None, :, 0]); y0 = np.maximum(a[:, None, 1], b[None, :, 1])
    x1 = np.minimum(a[:, None, 2], b[None, :, 2]); y1 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter + 1e-12)

def border_frac(boxes, W, H, tol=1.0):
    # 「贴边框」占比：框的任意一边距画布边界 <= tol
    if len(boxes) == 0:
        return 0.0
    on = ((boxes[:, 0] <= tol) | (boxes[:, 1] <= tol) |
          (boxes[:, 2] >= W - tol) | (boxes[:, 3] >= H - tol))
    return float(on.mean())

SRC = [make_sample(s) for s in range(400)]
all_sides = np.concatenate([box_wh(b)[0] for _, b, _ in SRC])
src_n = np.mean([len(b) for _, b, _ in SRC])
src_small = float((all_sides < SMALL_THR).mean())
src_border = float(np.mean([border_frac(b, S_IMG, S_IMG) for _, b, _ in SRC]))
print(f'源数据：{len(SRC)} 张 {S_IMG}×{S_IMG} 图，共 {len(all_sides)} 个框')
print(f'  单图目标数      {src_n:.2f}')
print(f'  目标边长中位数   {np.median(all_sides):.1f} px')
print(f'  小目标占比(<{SMALL_THR:.0f}px) {src_small:.1%}')
print(f'  贴边框占比       {src_border:.1%}')
assert 2.0 <= src_n <= 5.0 and 0.02 < src_small < 0.20
print('✅ 玩具数据就位（尺寸分布刻意做成 TSR 式的「以小目标为主、带长尾大目标」）')"""),

    md(r"""## 2 · Mosaic：拼接、框平移、裁剪与 `box_candidates` 过滤

严格照 YOLOv5 的四象限算术实现。为了让统计可解释，最后用固定 0.5× 缩放回 `s×s`
（真实实现里是 `[0.5, 1.5]` 的随机仿射 + 裁剪）。"""),

    code(r"""def resize_nn(img, oh, ow):
    H, W = img.shape[:2]
    yi = np.minimum((np.arange(oh) * H / oh).astype(int), H - 1)
    xi = np.minimum((np.arange(ow) * W / ow).astype(int), W - 1)
    return img[yi][:, xi]

def box_candidates(b_old, b_new, wh_thr=2.0, ar_thr=20.0, area_thr=0.10, eps=1e-16):
    # YOLOv5 的过滤规则：裁剪后宽高 > wh_thr、长宽比 < ar_thr、**面积保留率 > area_thr**
    w1, h1 = box_wh(b_old); w2, h2 = box_wh(b_new)
    ar = np.maximum(w2 / (h2 + eps), h2 / (w2 + eps))
    return (w2 > wh_thr) & (h2 > wh_thr) & (w2 * h2 / (w1 * h1 + eps) > area_thr) & (ar < ar_thr)

def mosaic4(samples, s=S_IMG, rng=None, area_thr=0.10, wh_thr=2.0):
    # samples: 4 个 (img, boxes, labels)。返回 (拼接并缩放回 s 的图, boxes, labels, 统计)
    rng = rng or np.random.default_rng()
    canvas = np.full((2 * s, 2 * s, 3), 114 / 255.0)
    xc = int(rng.integers(s // 2, 3 * s // 2))          # ★ 拼接中心随机，不能固定在正中
    yc = int(rng.integers(s // 2, 3 * s // 2))
    ob, ol = [], []
    for i, (img, boxes, labels) in enumerate(samples):
        h, w = img.shape[:2]
        if i == 0:      # 左上：只保留 img 的右下角
            x1a, y1a, x2a, y2a = max(xc - w, 0), max(yc - h, 0), xc, yc
            x1b, y1b, x2b, y2b = w - (x2a - x1a), h - (y2a - y1a), w, h
        elif i == 1:    # 右上
            x1a, y1a, x2a, y2a = xc, max(yc - h, 0), min(xc + w, 2 * s), yc
            x1b, y1b, x2b, y2b = 0, h - (y2a - y1a), min(w, x2a - x1a), h
        elif i == 2:    # 左下
            x1a, y1a, x2a, y2a = max(xc - w, 0), yc, xc, min(2 * s, yc + h)
            x1b, y1b, x2b, y2b = w - (x2a - x1a), 0, w, min(y2a - y1a, h)
        else:           # 右下
            x1a, y1a, x2a, y2a = xc, yc, min(xc + w, 2 * s), min(2 * s, yc + h)
            x1b, y1b, x2b, y2b = 0, 0, min(w, x2a - x1a), min(y2a - y1a, h)
        canvas[y1a:y2a, x1a:x2a] = img[y1b:y2b, x1b:x2b]
        padw, padh = x1a - x1b, y1a - y1b
        if len(boxes):
            b = boxes.copy()
            b[:, [0, 2]] += padw
            b[:, [1, 3]] += padh
            ob.append(b); ol.append(labels)
    b_old = np.concatenate(ob) if ob else np.zeros((0, 4))
    lab = np.concatenate(ol) if ol else np.zeros((0,), int)
    out = resize_nn(canvas, s, s)                                    # 固定 0.5× 缩放回 s×s
    b_scaled = b_old * 0.5                                           # 框跟着缩放
    b_new = b_scaled.copy()
    # ⚠️ 注意：np.clip(a[:, [0,2]], ..., out=a[:, [0,2]]) 是**无效**的 ——
    #    花式索引返回的是副本不是视图，写进去的是临时数组。必须显式赋值回去。
    b_new[:, [0, 2]] = np.clip(b_new[:, [0, 2]], 0, s)               # ★ 越界要裁剪，不是丢弃
    b_new[:, [1, 3]] = np.clip(b_new[:, [1, 3]], 0, s)
    keep = box_candidates(b_scaled, b_new, wh_thr=wh_thr, area_thr=area_thr)
    b_out, lab = b_new[keep], lab[keep]
    return out, b_out, lab, dict(n_before=len(b_old), n_after=int(keep.sum()),
                                 center=(xc, yc), dropped=int((~keep).sum()))

mos = [mosaic4([SRC[int(rng.integers(0, len(SRC)))] for _ in range(4)], rng=rng)
       for _ in range(400)]
mos_sides = np.concatenate([box_wh(b)[0] for _, b, _, _ in mos])
mos_n = np.mean([len(b) for _, b, _, _ in mos])
mos_small = float((mos_sides < SMALL_THR).mean())
mos_border = float(np.mean([border_frac(b, S_IMG, S_IMG) for _, b, _, _ in mos]))
dropped = np.mean([st['dropped'] for _, _, _, st in mos])

print(f"{'指标':<24s} {'源分布':>10s} {'Mosaic':>10s} {'变化'}")
print(f'{"单图目标数":<24s} {src_n:>10.2f} {mos_n:>10.2f}  ×{mos_n/src_n:.2f}')
print(f'{"目标边长中位数(px)":<24s} {np.median(all_sides):>10.1f} {np.median(mos_sides):>10.1f}'
      f'  ×{np.median(mos_sides)/np.median(all_sides):.2f}')
print(f'{f"小目标占比(<{SMALL_THR:.0f}px)":<24s} {src_small:>9.1%} {mos_small:>10.1%}'
      f'  ×{mos_small/src_small:.1f}')
print(f'{"贴边(截断)框占比":<24s} {src_border:>9.1%} {mos_border:>10.1%}'
      f'  ×{mos_border/max(src_border,1e-9):.1f}')
print(f'{"被过滤丢弃的框/图":<24s} {"-":>10s} {dropped:>10.2f}')

assert mos_n > 2.5 * src_n, 'Mosaic 应把单图目标数抬到约 4 倍'
assert mos_small > 3 * src_small, 'Mosaic 应显著提高小目标占比'
assert 0.01 < src_border < 0.08 and mos_border > 2.5 * src_border, 'Mosaic 会制造大量截断框'
print()
print('✅ Mosaic 的三个作用全部量化到位：')
print('   ① 单图场景数 ×4（每步见到的上下文多样性 ×4）')
print('   ② 小目标占比暴涨 —— **对 TSR 这种本来就是小目标的任务是直接命中的收益**')
print('   ③（副作用）截断框占比暴涨 —— **这正是 close-mosaic 的主要动机之一**')"""),

    code(r"""# ── 过滤规则的代价：area_thr / wh_thr 会系统性误杀最小的那批目标 ──
def mosaic_filter_stats(area_thr, wh_thr, n=250, seed=5):
    r = np.random.default_rng(seed)
    kept_sides, dropped_sides = [], []
    for _ in range(n):
        smp = [SRC[int(r.integers(0, len(SRC)))] for _ in range(4)]
        _, b, _, st = mosaic4(smp, rng=r, area_thr=area_thr, wh_thr=wh_thr)
        kept_sides.append(box_wh(b)[0])
        dropped_sides.append(st['dropped'])
    ks = np.concatenate(kept_sides)
    return dict(kept=len(ks), dropped_per_img=float(np.mean(dropped_sides)),
                small_frac=float((ks < SMALL_THR).mean()),
                p05=float(np.percentile(ks, 5)))

# ── 先用一个**最小可复现例子**证明 area_thr 真的会咬 ──
one_old = np.array([[0., 0., 20., 20.]])          # 原框 20×20
one_new = np.array([[0., 0.,  6., 20.]])          # 裁剪后 6×20 → 面积保留比 = 0.30
lab1 = np.array([0])
assert bool(box_candidates(one_old, one_new, area_thr=0.20)[0]) is True,  '0.30 > 0.20 应保留'
assert bool(box_candidates(one_old, one_new, area_thr=0.50)[0]) is False, '0.30 < 0.50 应丢弃'
print('最小例：原框 20×20 裁剪成 6×20（面积保留 30%）→ '
      f'area_thr=0.20 保留 {bool(box_candidates(one_old, one_new, area_thr=0.20)[0])}，'
      f'area_thr=0.50 保留 {bool(box_candidates(one_old, one_new, area_thr=0.50)[0])}')
print()

print(f"{'area_thr':>9s} {'wh_thr':>7s} {'保留框数':>9s} {'丢弃/图':>8s} "
      f"{'小目标占比':>11s} {'保留框边长p05':>13s}")
for at, wt in [(0.02, 2.0), (0.10, 2.0), (0.30, 2.0), (0.50, 2.0), (0.70, 2.0),
               (0.10, 1.0), (0.10, 4.0), (0.10, 8.0)]:
    st = mosaic_filter_stats(at, wt)
    print(f'{at:>9.2f} {wt:>7.1f} {st["kept"]:>9d} {st["dropped_per_img"]:>8.2f} '
          f'{st["small_frac"]:>10.1%} {st["p05"]:>12.1f} px')

area_scan = [mosaic_filter_stats(a, 2.0) for a in (0.02, 0.10, 0.30, 0.50, 0.70)]
w_ref, w_big = mosaic_filter_stats(0.10, 2.0), mosaic_filter_stats(0.10, 8.0)
# area_thr 单调不增（相邻两档可能持平——取决于裁剪比例的分布），但两端必须严格拉开
assert all(area_scan[i]['kept'] >= area_scan[i + 1]['kept'] for i in range(len(area_scan) - 1))
assert area_scan[0]['kept'] > area_scan[-1]['kept'], 'area_thr 从 0.02 到 0.70 必须显著减少保留框'
assert area_scan[-1]['dropped_per_img'] > area_scan[0]['dropped_per_img'] > 0, \
    'Mosaic 必须真的裁到框（dropped 恒为 0 说明 clip 根本没生效）'
assert w_big['p05'] > w_ref['p05'], 'wh_thr 变大直接抬高了保留框的最小尺寸'
assert w_big['small_frac'] < w_ref['small_frac'], 'wh_thr 变大会误杀小目标'
print()
print('💡 一个真实的实现坑（本 notebook 踩过）：')
print('   `np.clip(b[:, [0,2]], 0, W, out=b[:, [0,2]])` 是**无效**的 ——')
print('   花式索引返回副本不是视图，写进去的是临时数组，框根本没被裁剪。')
print('   症状极其隐蔽：面积保留比恒为 1.0 → **area_thr 看起来「没有任何作用」**，')
print('   而贴边框统计又是正常的（框确实压在边界上，只是没被 clip）。')
print('   ⇒ 检查裁剪逻辑是否生效的最快办法：看 dropped_per_img 是不是恒等于 0。')
print('⚠️  一个反直觉的事实：**Mosaic 号称「制造更多小目标」，过滤规则却在系统性删掉最小的那批。**')
print(f'    wh_thr 从 2 提到 8，保留框的边长 p05 从 {w_ref["p05"]:.1f} px 抬到 {w_big["p05"]:.1f} px，')
print(f'    小目标占比从 {w_ref["small_frac"]:.1%} 掉到 {w_big["small_frac"]:.1%}。')
print('✅ 所以 wh_thr / area_thr 必须与「你关心的最小目标尺寸」一起定，不能抄默认值。')"""),

    md(r"""## 3 · close-mosaic：把训练分布与部署分布的鸿沟量出来"""),

    code(r"""def w1_distance(a, b, n=200):
    # Wasserstein-1（用分位数近似）：两个分布对应分位数之差的平均绝对值
    q = (np.arange(n) + 0.5) / n
    return float(np.abs(np.quantile(a, q) - np.quantile(b, q)).mean())

deploy_sides = all_sides                      # 部署/验证分布 = 不做 mosaic 的真实分布
w1_on = w1_distance(mos_sides, deploy_sides)
w1_off = w1_distance(all_sides, deploy_sides)
print('训练分布 vs 部署分布（目标边长）的 Wasserstein-1 距离：')
print(f'  Mosaic ON : {w1_on:8.3f} px')
print(f'  Mosaic OFF: {w1_off:8.3f} px   ← 归零')
assert w1_on > 3.0 and w1_off < 1e-9

print()
print(f"{'鸿沟':<22s} {'Mosaic ON':>12s} {'Mosaic OFF/部署':>16s} {'相对差'}")
rows = [('目标边长中位数(px)', np.median(mos_sides), np.median(deploy_sides)),
        ('小目标占比', mos_small, src_small),
        ('贴边(截断)框占比', mos_border, src_border),
        ('单图目标数', mos_n, src_n)]
for name, on, off in rows:
    print(f'{name:<22s} {on:>12.3f} {off:>16.3f} {on/max(off,1e-9):>8.2f}×')

print()
print('⚠️  第三行是最该被记住的：模型在 mosaic 下学到「框贴边也算完整目标」，')
print('    而部署时贴边框只占 ~3% —— **回归头因此产生贴边假阳**。')
print('✅ close-mosaic 主要修的就是**回归**，所以它的收益体现在 AP75/AP90 上，')
print('   只看 AP50 常常看不出差别 → 然后得出「close-mosaic 没用」的错误结论。')"""),

    code(r"""# ── 训练时间线：close-mosaic 让鸿沟在最后 N 个 epoch 归零 ──
def mosaic_prob(epoch, total, close_last=10, p_max=1.0):
    return 0.0 if epoch >= total - close_last else p_max

TOTAL, CLOSE = 100, 10
timeline = []
for ep in range(TOTAL):
    p = mosaic_prob(ep, TOTAL, CLOSE)
    # 该 epoch 的训练尺寸分布 = p 比例的 mosaic 样本 + (1-p) 比例的原始样本
    k = int(p * len(mos_sides))
    mix = np.concatenate([mos_sides[:k], deploy_sides[:len(deploy_sides) - int(p * len(deploy_sides))]])
    timeline.append((ep, p, w1_distance(mix, deploy_sides)))

print(f"{'epoch':>6s} {'p_mosaic':>9s} {'与部署分布的 W1':>16s}")
for ep, p, d in timeline[::10] + [timeline[-1]]:
    bar = '█' * int(d * 3)
    print(f'{ep:>6d} {p:>9.2f} {d:>15.3f} px  {bar}')

assert timeline[0][2] > 3.0 and timeline[-1][2] < 1e-9
assert all(t[2] > 3.0 for t in timeline[:TOTAL - CLOSE])
assert all(t[2] < 1e-9 for t in timeline[TOTAL - CLOSE:])
print()
print(f'✅ 前 {TOTAL-CLOSE} 个 epoch：训练分布与部署分布有 {timeline[0][2]:.1f} px 的系统性鸿沟；')
print(f'   最后 {CLOSE} 个 epoch：鸿沟归零，模型在**真实分布**上完成收敛。')
print()
print('★ 面试要点：关多少个 epoch 不该答数字，该答机制 ——')
print('  关闭窗口要够模型在真实分布上重新收敛，**所以它与学习率调度耦合**：')
print('  如果窗口落在学习率已衰减到极小的阶段，模型根本动不了，等于没关。')
print('  关键量是「窗口内的有效更新步数」，不是 epoch 数。')"""),

    md(r"""## 4 · MixUp / CutMix 在检测里的代价

MixUp：图像加权、标注取并集 → 每个目标半透明却按完整目标监督。
CutMix：随机矩形不认识已有的框 → **把目标切掉一半，标注却还是完整的**。"""),

    code(r"""def mixup(a, b, lam):
    # 检测版 MixUp：图像加权平均，**标注取并集**（集合没有线性结构，插不了值）
    (ia, ba, la), (ib, bb, lb) = a, b
    img = lam * ia + (1 - lam) * ib
    return img, np.concatenate([ba, bb]), np.concatenate([la, lb])

im_a, im_b = SRC[0], SRC[1]
for lam in [0.5, 0.7, 0.9]:
    img, bx, lb = mixup(im_a, im_b, lam)
    print(f'λ={lam:.1f}  图像方差 {img.var():.5f}  '
          f'（源图 {im_a[0].var():.5f} / {im_b[0].var():.5f}）  框数 {len(bx)}')

img_h, _, _ = mixup(im_a, im_b, 0.5)
var_ratio = img_h.var() / (0.5 * (im_a[0].var() + im_b[0].var()))
print()
print(f'λ=0.5 时图像方差降到源图平均的 {var_ratio:.2f} 倍（理论 λ²+(1-λ)² = 0.50）')
assert 0.35 < var_ratio < 0.75, var_ratio
print('⚠️  **BN 层在训练时看到低方差输入、推理时看到正常方差输入** —— 又一种训练-部署鸿沟。')
print('    症状是「训练 loss 很好看、验证一开始就差」，容易被误判成过拟合。')
print(f'⚠️  而且每个目标都以 λ={0.5} 的不透明度出现，却被要求以 100% 置信度检出 ——')
print('    「半透明目标按完整目标监督」这件事在真实世界里没有对应物。')"""),

    code(r"""# ── CutMix 的具体害处：统计有多少 GT 被「切成半个却标着完整框」 ──
def cutmix_rect(H, W, lam, rng):
    r = np.sqrt(1.0 - lam)
    cw, ch = int(W * r), int(H * r)
    cx, cy = int(rng.integers(0, W)), int(rng.integers(0, H))
    return (max(cx - cw // 2, 0), max(cy - ch // 2, 0),
            min(cx + cw // 2, W), min(cy + ch // 2, H))

def overlap_frac(boxes, rect):
    if len(boxes) == 0:
        return np.zeros(0)
    x0 = np.maximum(boxes[:, 0], rect[0]); y0 = np.maximum(boxes[:, 1], rect[1])
    x1 = np.minimum(boxes[:, 2], rect[2]); y1 = np.minimum(boxes[:, 3], rect[3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + 1e-12)

def cutmix_damage(box_sampler, n=3000, seed=3):
    r = np.random.default_rng(seed)
    intact = partial = covered = total = 0
    for _ in range(n):
        bx = box_sampler(r)
        lam = float(r.beta(1.0, 1.0))
        f = overlap_frac(bx, cutmix_rect(S_IMG, S_IMG, lam, r))
        total += len(f)
        intact += int((f < 0.05).sum())
        partial += int(((f >= 0.05) & (f <= 0.95)).sum())
        covered += int((f > 0.95).sum())
    return dict(total=total, intact=intact / total,
                partial=partial / total, covered=covered / total)

def small_sampler(r):                       # TSR 式：小目标为主
    return SRC[int(r.integers(0, len(SRC)))][1]

def big_sampler(r):                         # COCO 式：大目标为主
    side = float(np.clip(r.lognormal(np.log(60), 0.4), 20, 140))
    x0 = r.uniform(0, S_IMG - side); y0 = r.uniform(0, S_IMG - side)
    return np.array([[x0, y0, x0 + side, y0 + side]])

sm = cutmix_damage(small_sampler)
bg_ = cutmix_damage(big_sampler)
print(f"{'目标尺度':<22s} {'完好(<5%)':>10s} {'部分覆盖(5-95%)':>16s} {'全覆盖(>95%)':>13s} "
      f"{'总受损':>8s}")
for name, d in [('小目标为主（TSR 式）', sm), ('大目标为主（COCO 式）', bg_)]:
    print(f'{name:<22s} {d["intact"]:>10.1%} {d["partial"]:>15.1%} {d["covered"]:>13.1%} '
          f'{d["partial"]+d["covered"]:>7.1%}')

assert sm['partial'] + sm['covered'] > 0.30, '随机 CutMix 会损伤三成以上的已有 GT'
assert sm['covered'] > sm['partial'], '小目标以「整体被盖住但标注还在」为主'
assert bg_['partial'] > bg_['covered'], '大目标以「部分截断」为主'
assert abs(sm['intact'] + sm['partial'] + sm['covered'] - 1.0) < 1e-9
print()
print('★ 两种尺度的受损方式**不一样**，而 TSR 落在更糟的那一侧：')
print(f'  · 大目标：主要是**部分截断**（{bg_["partial"]:.0%}）—— 半个目标标着完整框；')
print(f'  · 小目标：主要是**整体被盖住而标注仍在**（{sm["covered"]:.0%}）——')
print('    模型被告知「这里有一块标志」，而那块区域现在是另一张图的内容。')
print('    **这是幽灵框（phantom box），比部分截断更毒**：它直接教模型在无关纹理上报警。')
print()
print('✅ 这正是 **Copy-Paste 相对 CutMix 的根本优势**：')
print('   Copy-Paste 粘贴的是**带掩码的实例**，它知道自己贴了什么、贴在哪；')
print('   被遮住的已有目标可以按可见度重算标注或直接删除。')
print('   「有实例掩码」这一个差别，把一个盲目的操作变成一个可控的操作。')"""),

    md(r"""## 5 · 透视约束：`s_px = S/(H_m − h_cam) · (y_h − y_bot)`

现在切到真实相机几何。图像是 1920×1080 帧上的一个 **180×320 裁剪**（1:1，不缩放），
`f = 1000 px`，地平线在裁剪内的第 90 行，相机高 1.5 m，标志直径 0.6 m，
柱式标志下缘安装高度 2.0–3.2 m。"""),

    code(r"""H_SC, W_SC = 180, 320       # 场景裁剪尺寸
F_PX = 1000.0               # 焦距（像素）
Y_H = 90.0                  # 地平线所在行
H_CAM = 1.5                 # 相机高度 (m)
S_SIGN = 0.60               # 标志物理直径 (m)
MOUNT = (2.0, 3.2)          # 标志下缘安装高度范围 (m)：柱式 ~2.0，悬臂/门架 ~3.2

def scale_from_position(y_bot, mount, S=S_SIGN, y_h=Y_H, h_cam=H_CAM):
    # s_px = S/(H_m - h_cam) * (y_h - y_bot)  —— 距离 Z 被消掉了
    return S / (mount - h_cam) * (y_h - y_bot)

def legal_scale_band(y_bot, mount=MOUNT, S=S_SIGN, y_h=Y_H, h_cam=H_CAM):
    # 返回 (s_min, s_max)；y_bot 在地平线以下 → None（柱式标志不可能出现在那里）
    if y_bot >= y_h:
        return None
    lo = scale_from_position(y_bot, mount[1], S, y_h, h_cam)   # 高杆 → 同样位置对应更小的牌
    hi = scale_from_position(y_bot, mount[0], S, y_h, h_cam)
    return (float(lo), float(hi))

def implied_Z_from_size(s_px, S=S_SIGN, f=F_PX):
    return f * S / max(s_px, 1e-9)

def implied_Z_from_pos(y_bot, mount, y_h=Y_H, h_cam=H_CAM, f=F_PX):
    return f * (mount - h_cam) / max(y_h - y_bot, 1e-9)

print(f"{'y_bot':>7s} {'地平线以上':>10s} {'合法尺度带 s_px':>18s} {'对应距离 Z 范围':>20s}")
for y_bot in [80, 70, 57, 40, 20, 95]:
    band = legal_scale_band(y_bot)
    if band is None:
        print(f'{y_bot:>7d} {"—":>10s} {"❌ 地平线以下，非法":>18s} {"（柱式标志不可能在此）":>20s}')
        continue
    zlo = implied_Z_from_size(band[1]); zhi = implied_Z_from_size(band[0])
    print(f'{y_bot:>7d} {Y_H-y_bot:>9.0f}px [{band[0]:6.1f}, {band[1]:6.1f}] px '
          f'  [{zlo:6.1f}, {zhi:6.1f}] m')

b57 = legal_scale_band(57)
assert abs(b57[0] - 0.6 / 1.7 * 33) < 1e-9 and abs(b57[1] - 0.6 / 0.5 * 33) < 1e-9
assert legal_scale_band(95) is None
# 自洽性检查：带内的尺度，其「尺寸推的 Z」必落在「位置推的 Z」区间内
for y_bot in [80, 70, 57, 40, 20]:
    lo, hi = legal_scale_band(y_bot)
    for s in [lo + 1e-6, (lo + hi) / 2, hi - 1e-6]:
        z_size = implied_Z_from_size(s)
        z_lo = implied_Z_from_pos(y_bot, MOUNT[0]); z_hi = implied_Z_from_pos(y_bot, MOUNT[1])
        assert z_lo - 1e-6 <= z_size <= z_hi + 1e-6, (y_bot, s, z_size, z_lo, z_hi)
print()
print('✅ 合法带的两个等价说法：')
print('   ① s_px 必须落在 [S/(H_max-h_cam), S/(H_min-h_cam)] × (y_h - y_bot) 之内；')
print('   ② **由尺寸反推的 Z 与由位置反推的 Z 必须自洽**（在安装高度范围内相容）。')
print('⚠️  「贴到天上」的本质就是这两个 Z 互相矛盾：位置说很近，尺寸说很远。')"""),

    code(r"""# ── 把「随机粘贴 vs 带约束粘贴」的合法率量出来 ──
def naive_random_paste(rng, n=4000):
    ys = rng.uniform(5, H_SC - 5, n)
    ss = rng.uniform(6, 60, n)
    return ys, ss

def is_consistent(y_bot, s_px, tol=0.0):
    band = legal_scale_band(y_bot)
    if band is None:
        return False
    return band[0] * (1 - tol) <= s_px <= band[1] * (1 + tol)

r = np.random.default_rng(9)
ys, ss = naive_random_paste(r)
ok = np.array([is_consistent(y, s) for y, s in zip(ys, ss)])
below = (ys >= Y_H)
print(f'完全随机粘贴 {len(ys)} 次：')
print(f'  落在地平线以下（贴到路面上）      {below.mean():6.1%}   ← 教模型「路面上有标志」')
print(f'  尺度与位置自洽（**合法**）        {ok.mean():6.1%}')
print(f'  尺度与位置矛盾（贴到天上/尺寸错） {(~ok & ~below).mean():6.1%}')
assert ok.mean() < 0.35, '随机粘贴的合法率应当很低'
assert below.mean() > 0.4

# 带约束的采样：先采位置，再在合法带内采尺度 → 合法率 100%
def constrained_paste(rng, n=4000):
    out = []
    while len(out) < n:
        y = float(rng.uniform(5, Y_H - 5))
        band = legal_scale_band(y)
        if band is None or band[1] < 6:
            continue
        s = float(rng.uniform(max(band[0], 6.0), band[1]))
        if s <= band[1]:
            out.append((y, s))
    return np.array(out)

cp = constrained_paste(r)
ok2 = np.array([is_consistent(y, s) for y, s in cp])
print(f'\n带透视约束的粘贴 {len(cp)} 次：合法率 {ok2.mean():.1%}')
print(f'  粘贴尺寸分布：中位数 {np.median(cp[:,1]):.1f} px，'
      f'p10={np.percentile(cp[:,1],10):.1f}  p90={np.percentile(cp[:,1],90):.1f}')
print(f'  对应距离 Z：中位数 {implied_Z_from_size(np.median(cp[:,1])):.0f} m')
assert ok2.mean() > 0.999
print()
print('✅ 约束不是「加一层检查」，而是**改采样方式**：先采位置、再在合法带内采尺度，')
print('   合法率直接 100%，而不是采完再拒绝（拒绝法会浪费 70% 的采样）。')"""),

    md(r"""## 6 · 实例库：渲染、质量筛选与「错误放大器」

实例库是一个 **错误放大器**：一个错标实例会被贴进上千张训练图。
所以它的质量门槛必须比普通训练集高一个数量级。"""),

    code(r"""def conv2d_same(img, k):
    a = img[..., None] if img.ndim == 2 else img
    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    pad = np.pad(a, ((ph, ph), (pw, pw), (0, 0)), mode='edge')
    out = np.zeros_like(a, dtype=float)
    H, W = a.shape[:2]
    for i in range(kh):
        for j in range(kw):
            if k[i, j] != 0.0:
                out += k[i, j] * pad[i:i + H, j:j + W]
    return out[..., 0] if img.ndim == 2 else out

LAPLACIAN = np.array([[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]])

MARGIN = 0.35        # 抠图时不可避免会带上一圈**源背景** —— 这正是矩形粘贴的祸根

def render_sign(diam, rim_rgb, blur=0.0, truncate=0.0, src_bg=(0.22, 0.34, 0.18)):
    # 用**形状先验**渲染一个圆形标志实例：TSR 里掩码可以从「框+类别」推出来，
    # 不需要实例分割标注 —— 这是 TSR 特别适合 copy-paste 的技术理由。
    # patch 是一个方形 crop（含一圈源背景），alpha 只在圆盘内为 1。
    d = max(6, int(round(diam)))
    n = int(round(d * (1 + MARGIN)))
    Y, X = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2.0
    rr = np.hypot(Y - c, X - c)
    R = d / 2.0
    alpha = np.clip(R - rr + 0.5, 0.0, 1.0)                # 抗锯齿的软掩码
    patch = np.zeros((n, n, 3))
    patch[:] = src_bg                                      # ★ crop 里带着的源背景
    patch[rr <= R] = (0.93, 0.93, 0.92)
    patch[(rr <= R) & (rr > 0.74 * R)] = rim_rgb
    patch[(rr <= 0.74 * R) & (np.abs(Y - c) <= max(1.0, 0.16 * R))] = (0.12, 0.12, 0.13)
    if blur > 0:
        k = np.ones((3, 3)) / 9.0
        for _ in range(int(blur)):
            patch = conv2d_same(patch, k)
            alpha = conv2d_same(alpha, k)
    if truncate > 0:                                       # 模拟被图像边缘截断的实例
        alpha[:, :int(n * truncate)] = 0.0
    return np.clip(patch, 0, 1), np.clip(alpha, 0, 1)

def laplacian_var(patch, alpha):
    g = patch.mean(-1)
    lap = conv2d_same(g, LAPLACIAN)
    m = alpha > 0.5
    return float(lap[m].var()) if m.sum() > 4 else 0.0

CLASS_RIM = {'禁令(红)': (0.80, 0.10, 0.12), '警告(黄)': (0.95, 0.78, 0.05),
             '指示(蓝)': (0.05, 0.25, 0.65), '指路(绿)': (0.05, 0.45, 0.22)}

def build_bank(rng, n=240):
    bank = []
    for i in range(n):
        cls = list(CLASS_RIM)[int(rng.integers(0, 4))]
        diam = float(np.clip(rng.lognormal(np.log(26), 0.55), 8, 90))
        blur = int(rng.integers(0, 4)) if rng.random() < 0.30 else 0
        trunc = float(rng.uniform(0.15, 0.45)) if rng.random() < 0.15 else 0.0
        p, a = render_sign(diam, CLASS_RIM[cls], blur=blur, truncate=trunc)
        bank.append(dict(cls=cls, patch=p, alpha=a, src_side=diam,
                         blur=blur, truncated=trunc > 0, lap=laplacian_var(p, a)))
    return bank

bank = build_bank(np.random.default_rng(31))
laps = np.array([b['lap'] for b in bank])
LAP_THR = float(np.percentile(laps, 30))

def quality_filter(bank, min_side=16.0, lap_thr=LAP_THR):
    keep, reasons = [], {'尺寸过小': 0, '截断': 0, '模糊': 0}
    for b in bank:
        if b['src_side'] < min_side:
            reasons['尺寸过小'] += 1; continue
        if b['truncated']:
            reasons['截断'] += 1; continue
        if b['lap'] < lap_thr:
            reasons['模糊'] += 1; continue
        keep.append(b)
    return keep, reasons

clean, reasons = quality_filter(bank)
print(f'原始实例库 {len(bank)} 个 → 筛后 {len(clean)} 个（保留 {len(clean)/len(bank):.1%}）')
for k, v in reasons.items():
    print(f'  剔除「{k}」{v} 个')
print(f'Laplacian 方差：清晰实例中位数 {np.median([b["lap"] for b in clean]):.5f}，'
      f'模糊实例中位数 {np.median([b["lap"] for b in bank if b["blur"]>0]):.5f}')

sharp = render_sign(40, CLASS_RIM['禁令(红)'], blur=0)
soft = render_sign(40, CLASS_RIM['禁令(红)'], blur=3)
assert laplacian_var(*sharp) > 3 * laplacian_var(*soft), 'Laplacian 方差必须能区分清晰与模糊'
assert all(not b['truncated'] and b['src_side'] >= 16 for b in clean)
assert len(clean) < len(bank)
print()
print('⚠️  **实例库是错误放大器**：普通训练集里一个错标样本影响一个样本；')
print('    实例库里一个错标实例会被贴进上千张图 = 上千个错标样本。')
print('✅ 所以实例库值得单独做一轮人工复核 —— 这是少数几个「人工复核明显划算」的环节。')"""),

    md(r"""## 7 · 粘贴与融合：矩形 vs 掩码 vs 羽化 vs 光照匹配"""),

    code(r"""def resize_bilinear(a, oh, ow):
    a3 = a[..., None] if a.ndim == 2 else a
    H, W = a3.shape[:2]
    ys = np.clip((np.arange(oh) + 0.5) * H / oh - 0.5, 0, H - 1)
    xs = np.clip((np.arange(ow) + 0.5) * W / ow - 0.5, 0, W - 1)
    y0 = np.floor(ys).astype(int); y1 = np.minimum(y0 + 1, H - 1); wy = (ys - y0)[:, None, None]
    x0 = np.floor(xs).astype(int); x1 = np.minimum(x0 + 1, W - 1); wx = (xs - x0)[None, :, None]
    top = a3[y0][:, x0] * (1 - wx) + a3[y0][:, x1] * wx
    bot = a3[y1][:, x0] * (1 - wx) + a3[y1][:, x1] * wx
    out = top * (1 - wy) + bot * wy
    return out[..., 0] if a.ndim == 2 else out

def make_bg(seed=0):
    r = np.random.default_rng(seed)
    yy = np.arange(H_SC)[:, None, None]
    sky = np.array([0.60, 0.70, 0.86]).reshape(1, 1, 3)
    road = np.array([0.30, 0.29, 0.28]).reshape(1, 1, 3)
    img = np.where(yy > Y_H, road, sky) * np.ones((H_SC, W_SC, 1))
    return np.clip(img + r.normal(0, 0.015, img.shape), 0, 1)

def paste(bg, patch, alpha, x0, y0, mode='mask', feather=0, gain=1.0):
    # mode: 'rect'=连源背景一起贴（最差）| 'mask'=按掩码贴 | 'feather'=掩码 + 羽化
    out = bg.copy()
    h, w = patch.shape[:2]
    p = np.clip(patch * gain, 0, 1)
    a = np.ones((h, w)) if mode == 'rect' else alpha.copy()
    if mode == 'feather' and feather > 0:
        k = np.ones((2 * feather + 1, 2 * feather + 1))
        a = conv2d_same(a, k / k.sum())
    a3 = a[..., None]
    out[y0:y0 + h, x0:x0 + w] = (p * a3 + out[y0:y0 + h, x0:x0 + w] * (1 - a3))
    return out

def rect_seam(img, x0, y0, n, ring=2):
    # 只看 crop **矩形边界那一圈**的梯度：那里是源背景与目标背景的交界，
    # 掩码粘贴根本不动这块区域（alpha=0），只有矩形粘贴会在这里留下人造硬边。
    gray = img.mean(-1)
    g = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    g = g + np.abs(np.diff(gray, axis=0, prepend=gray[:1]))
    m = np.zeros(img.shape[:2], bool)
    m[max(y0 - ring, 0):y0 + n + ring, max(x0 - ring, 0):x0 + n + ring] = True
    m[y0 + ring:y0 + n - ring, x0 + ring:x0 + n - ring] = False
    return float(g[m].mean())

def silhouette_contrast(img, x0, y0, n):
    gray = img.mean(-1)
    g = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    return float(g[y0:y0 + n, x0:x0 + n].max())

bg = make_bg(1)
y_bot = 62.0
band = legal_scale_band(y_bot)
side = int(round((band[0] + band[1]) / 2))              # 圆盘（= 标志本体）的直径
n_t = int(round(side * (1 + MARGIN)))                   # crop 的边长（含一圈源背景）
src = clean[0]
patch = resize_bilinear(src['patch'], n_t, n_t)
alpha = resize_bilinear(src['alpha'], n_t, n_t)
off = (n_t - side) // 2
x0, y0 = 210 - off, int(round(y_bot)) - side - off      # 让**圆盘**落在 (210, y_bot)

res = {}
res['矩形粘贴'] = paste(bg, patch, alpha, x0, y0, mode='rect')
res['掩码粘贴(硬边)'] = paste(bg, patch, alpha, x0, y0, mode='mask')
res['掩码+羽化1px'] = paste(bg, patch, alpha, x0, y0, mode='feather', feather=1)
res['掩码+羽化5px'] = paste(bg, patch, alpha, x0, y0, mode='feather', feather=5)

print(f'粘贴位置 y_bot={y_bot:.0f}（地平线上 {Y_H-y_bot:.0f} px），'
      f'合法带 [{band[0]:.1f}, {band[1]:.1f}] px，取标志直径 {side} px（crop {n_t} px）')
print(f'  → 由尺寸推的距离 Z ≈ {implied_Z_from_size(side):.0f} m')
print()
print(f"{'融合方式':<18s} {'crop 边界接缝':>14s} {'轮廓边缘对比度':>15s}")
for k, v in res.items():
    print(f'{k:<18s} {rect_seam(v, x0, y0, n_t):>14.4f} '
          f'{silhouette_contrast(v, x0, y0, n_t):>15.4f}')

assert (rect_seam(res['矩形粘贴'], x0, y0, n_t)
        > 3 * rect_seam(res['掩码粘贴(硬边)'], x0, y0, n_t)), '矩形粘贴必须留下明显接缝'
assert abs(rect_seam(res['掩码粘贴(硬边)'], x0, y0, n_t)
           - rect_seam(bg, x0, y0, n_t)) < 1e-9, '掩码粘贴不应改动 crop 边界那一圈'
assert (silhouette_contrast(res['掩码+羽化5px'], x0, y0, n_t)
        < silhouette_contrast(res['掩码粘贴(硬边)'], x0, y0, n_t)), '羽化会软化轮廓'
print()
print('✅ 矩形粘贴留下的**人造硬边**是模型一学一个准的捷径 —— 必须用掩码。')
print('⚠️  但**羽化过头也是错的**：真实标志有清晰边缘，羽化 5 px 会让它看起来像半透明贴纸，')
print('    制造出真实数据里不存在的「软边目标」→ 边界回归反而变差。')
print('✅ 羽化半径 1–2 px 足够（只为抹掉重采样锯齿），别再多。')"""),

    code(r"""# ── 光照匹配：只匹配亮度（乘性），**绝不匹配色相/饱和度** ──
def rgb_to_hsv_mean(patch, alpha):
    m = alpha > 0.5
    px = patch[m]
    mx, mn = px.max(1), px.min(1)
    d = mx - mn
    h = np.zeros(len(px)); ok = d > 1e-12
    r_, g_, b_ = px[:, 0], px[:, 1], px[:, 2]
    i = ok & (mx == r_); h[i] = ((g_[i] - b_[i]) / d[i]) % 6.0
    i = ok & (mx == g_); h[i] = (b_[i] - r_[i]) / d[i] + 2.0
    i = ok & (mx == b_); h[i] = (r_[i] - g_[i]) / d[i] + 4.0
    h = (h * 60.0) % 360.0
    rad = np.deg2rad(h)
    hue = float(np.rad2deg(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360.0)
    sat = float(np.where(mx > 1e-12, d / np.maximum(mx, 1e-12), 0).mean())
    return hue, sat, float(mx.mean())

def local_bg_luma(img, x0, y0, h, w, pad=6):
    y1, x1 = min(y0 + h + pad, img.shape[0]), min(x0 + w + pad, img.shape[1])
    ys, xs = max(y0 - pad, 0), max(x0 - pad, 0)
    ring = img[ys:y1, xs:x1].mean(-1)
    inner = img[y0:y0 + h, x0:x0 + w].mean(-1)
    return float((ring.sum() - inner.sum()) / max(ring.size - inner.size, 1))

SRC_BG_LUMA = 0.72                      # 源实例被拍到时，它周围背景的平均亮度
dark_bg = np.clip(make_bg(2) * 0.45, 0, 1)      # 一张黄昏/隧道口的暗背景

no_match = paste(dark_bg, patch, alpha, x0, y0, mode='feather', feather=1)
tgt_luma = local_bg_luma(dark_bg, x0, y0, side, side)
gain = float(np.clip(tgt_luma / SRC_BG_LUMA, 0.5, 2.0))     # ★ clip 防止贴成一团黑
matched = paste(dark_bg, patch, alpha, x0, y0, mode='feather', feather=1, gain=gain)

h0, s0, v0 = rgb_to_hsv_mean(patch, alpha)
h1, s1, v1 = rgb_to_hsv_mean(np.clip(patch * gain, 0, 1), alpha)
print(f'粘贴处局部背景亮度 {tgt_luma:.3f}，源实例背景亮度 {SRC_BG_LUMA:.3f} → 增益 g={gain:.3f}')
print(f'{"":<14s} {"色相":>9s} {"饱和度":>9s} {"明度":>9s}')
print(f'{"源实例":<14s} {h0:>8.2f}° {s0:>9.3f} {v0:>9.3f}')
print(f'{"乘性亮度匹配后":<14s} {h1:>8.2f}° {s1:>9.3f} {v1:>9.3f}')

hue_d = min(abs(h1 - h0), 360 - abs(h1 - h0))
assert hue_d < 1e-6, '乘性亮度必须让色相严格不变（模块 02 的色彩代数）'
assert abs(s1 - s0) < 1e-6, '乘性亮度必须让饱和度严格不变'
assert abs(v1 / v0 - gain) < 1e-6, '明度应当按 g 缩放'

# 对照组：做「完整 color transfer」（连色度一起对齐）会发生什么
warm_bg_mean = np.array([0.42, 0.34, 0.22])                 # 偏暖的黄昏背景
patch_mean = patch[alpha > 0.5].mean(0)
full_transfer = np.clip(patch * (warm_bg_mean / (patch_mean + 1e-9)), 0, 1)
h2, s2, _ = rgb_to_hsv_mean(full_transfer, alpha)
print(f'{"完整color transfer":<14s} {h2:>8.2f}° {s2:>9.3f}       —  ← ❌ 色相被拉走 '
      f'{min(abs(h2-h0), 360-abs(h2-h0)):.1f}°')
assert min(abs(h2 - h0), 360 - abs(h2 - h0)) > 5.0, '完整 color transfer 会破坏颜色语义'
print()
print('✅ **用乘性亮度做光照匹配不是随便定的选择，它有精确的色彩代数依据**（模块 02）：')
print('   乘性缩放保持所有通道比值 → 色相与饱和度严格不变。')
print('❌ 而「完整 color transfer」把 RGB 均值都对齐到背景，会把红牌往暖色调上拉 ——')
print('   这跟色相抖动过强是同一个错误，只是伪装成了「让粘贴更自然」。')
print('⚠️  增益必须 clip（如 [0.5, 2.0]），否则从白天贴到夜景会把实例压成一团黑。')"""),

    md(r"""## 8 · 量化 copy-paste 对长尾的提升 —— 以及它**没有**提升的东西"""),

    code(r"""K_CLS, N_INST, ZIPF_A = 50, 20000, 1.8      # TSR 的类别频次接近 Zipf，指数明显 > 1
zipf = 1.0 / (np.arange(1, K_CLS + 1) ** ZIPF_A)
counts = np.maximum(np.round(zipf / zipf.sum() * N_INST), 3).astype(int)
tail = counts < 100
print(f'合成长尾：{K_CLS} 类 / {counts.sum()} 个实例')
print(f'  头部类最多 {counts.max()} 个，尾部类最少 {counts.min()} 个（比例 '
      f'{counts.max()/counts.min():.0f}:1）')
print(f'  尾部类（<100 实例）共 {tail.sum()} 个，占实例总数 {counts[tail].sum()/counts.sum():.2%}')
assert tail.sum() >= 5 and counts.min() < 30

M_IMG, PASTE_LAM, PASTE_FRAC = 6000, 1.5, 0.5      # 6000 张图，一半参与粘贴，均值 1.5 个
w = np.where(tail, 1.0 / np.sqrt(counts), 0.0)     # ★ 1/√n 加权，只对尾部类粘贴
w = w / w.sum()
r = np.random.default_rng(77)
n_paste_total = int(r.poisson(PASTE_LAM * PASTE_FRAC * M_IMG))
pasted = np.bincount(r.choice(K_CLS, size=n_paste_total, p=w), minlength=K_CLS)
eff = counts + pasted

print(f'\n共粘贴 {n_paste_total} 次（{M_IMG} 张图，{PASTE_FRAC:.0%} 参与，均值 {PASTE_LAM}/图）')
print(f"{'类别':>5s} {'原始实例':>9s} {'粘贴次数':>9s} {'有效样本数':>11s} {'提升':>8s} "
      f"{'唯一实例数':>11s}")
idx = list(range(3)) + list(np.where(tail)[0][:6])
for c in idx:
    print(f'{c:>5d} {counts[c]:>9d} {pasted[c]:>9d} {eff[c]:>11d} '
          f'{eff[c]/counts[c]:>7.1f}× {counts[c]:>11d}')

tail_gain = (eff[tail] / counts[tail])
print(f'\n尾部类的有效样本数提升：中位数 {np.median(tail_gain):.1f}×，'
      f'最小 {tail_gain.min():.1f}×，最大 {tail_gain.max():.1f}×')
print(f'  （1/√n 加权让**最稀有的类拿到最大提升**：最少的 {counts[tail].min()} 个实例 → '
      f'{eff[tail].max() if False else eff[counts.argmin()]} 个有效样本）')
print(f'头部类完全不受影响（粘贴次数 {pasted[~tail].sum()}）')
assert np.median(tail_gain) > 3, 'copy-paste 应把尾部类有效样本数提升数倍'
assert tail_gain.max() > 15, '最稀有的类应当获得一个数量级以上的提升'
assert tail_gain[np.argmin(counts[tail])] == tail_gain.max(), '1/√n 加权应让最稀有类提升最大'
assert pasted[~tail].sum() == 0, '只对尾部类粘贴'
assert (eff[~tail] == counts[~tail]).all()

print()
print('★ 但必须诚实地区分两件事：')
print(f'  · **有效样本数** N_eff = n_c + 粘贴次数        → 尾部类提升 {np.median(tail_gain):.0f}×')
print(f'  · **有效实例多样性** = 唯一源实例数（不变！）  → 尾部类仍然只有 {counts[tail].min()}–'
      f'{counts[tail].max()} 个不同外观')
print('  copy-paste 放大的是「实例 × 上下文 × 尺度 × 光照」的组合数，')
print('  **它能救「上下文过拟合」，救不了「实例外观过拟合」。**')
print()
print('✅ 这个区分决定下一步做什么：')
print('   加了 copy-paste 后 → 召回上来了 ⇒ 瓶颈确实是上下文，可以继续加；')
print('                     → 召回上来但假阳暴涨 ⇒ 瓶颈是实例多样性，')
print('                       **必须去采集/挖掘真实实例（C58），加再多 copy-paste 也没用**。')"""),

    md(r"""## 9 · 增强强度 × 模型容量 × 训练时长：三者耦合

一个**唯象模型**（不是从数据拟合出来的），把三条已知的经验规律写成可检验的形式：
① 增强扩大有效多样性；② 增强引入分布偏移；③ 吸收多样性需要容量与训练步数。"""),

    code(r"""def sim_val_err(strength, capacity, train_len,
                target_div=2.6, k_under=0.25, k_gap=0.30, k_shift=0.35, tau=1.0, base=0.10):
    D_eff = 1.0 + 2.0 * strength                        # ① 增强扩大有效多样性
    absorb = capacity * (1.0 - np.exp(-train_len / tau))  # ③ 能吸收多少，取决于容量×步数
    shift = k_shift * strength ** 2                       # ② 增强引入分布偏移
    return (base + k_under * max(0.0, D_eff - absorb)     # 欠拟合项
                 + k_gap * max(0.0, target_div - D_eff)   # 覆盖不足项
                 + shift)

GRID = np.arange(0.0, 1.0001, 0.02)
SETUPS = [('小模型 + 短训练', 1.6, 0.5), ('小模型 + 长训练', 1.6, 2.0),
          ('大模型 + 短训练', 3.2, 0.5), ('大模型 + 长训练', 3.2, 2.0)]
opt = {}
print(f"{'配置':<18s} {'最优强度':>9s} {'最优验证误差':>13s} {'强度=0.8 时':>13s} {'代价'}")
for name, cap, tl in SETUPS:
    errs = np.array([sim_val_err(s, cap, tl) for s in GRID])
    i = int(errs.argmin())
    opt[name] = float(GRID[i])
    e_strong = sim_val_err(0.8, cap, tl)
    print(f'{name:<18s} {GRID[i]:>9.2f} {errs[i]:>13.4f} {e_strong:>13.4f} '
          f'{"+%.1f%%" % (100*(e_strong/errs[i]-1)):>8s}')

assert opt['小模型 + 短训练'] < opt['小模型 + 长训练'] < opt['大模型 + 长训练'], opt
assert opt['大模型 + 长训练'] > 0.6 and opt['小模型 + 短训练'] < 0.25
print()
print('✅ 最优增强强度随「容量 × 训练时长」单调上升 —— 这解释了两个真实事故：')
print(f'   ① 把 YOLOv8x 的增强配置（强 mosaic + mixup + copy_paste）直接用到 v8n 上：')
print(f'      小模型在强度 0.8 处的误差比它的最优值高 '
      f'{100*(sim_val_err(0.8,1.6,0.5)/min(sil for sil in [sim_val_err(s,1.6,0.5) for s in GRID])-1):.0f}%，')
print('      症状是**训练 loss 和验证指标一起差** → 常被误诊成学习率/数据问题。')
print('   ② 在短训练预算下比较两套增强配方是**不公平的**：')
print(f'      同为大模型，短训练最优强度 {opt["大模型 + 短训练"]:.2f}，'
      f'长训练最优强度 {opt["大模型 + 长训练"]:.2f}。')
print('      强增强需要更长训练才能兑现收益 → 短训练下它一定输 → 得出「强增强没用」的错误结论。')
print()
print('★ 记住这条诊断反射：**小模型 + 强增强 = 欠拟合**（训练与验证一起差）。')"""),

    md(r"""## ✏️ 练习 1：Mosaic 的裁剪与过滤规则

实现 `clip_and_filter(boxes, labels, W, H, wh_thr=2.0, ar_thr=20.0, area_thr=0.10)`：

1. 把框 clip 到 `[0, W] × [0, H]`；
2. 用 `box_candidates` 的三条规则过滤（裁剪后宽高 > `wh_thr`、长宽比 < `ar_thr`、
   **裁剪后面积 / 裁剪前面积 > `area_thr`**）；
3. 返回 `(clipped_boxes, kept_labels, stats)`，`stats` 含
   `{'n_in':…, 'n_out':…, 'dropped_by_area':…, 'dropped_by_wh':…}`。

注意：**先 clip 再算面积比**，顺序反了规则就失效了。"""),

    code(r"""def clip_and_filter(boxes, labels, W, H, wh_thr=2.0, ar_thr=20.0, area_thr=0.10):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 1 自测 ——
bx = np.array([
    [ 10.,  10.,  50.,  50.],     # 完全在内 → 保留
    [-30.,  10.,  10.,  50.],     # 左侧越界，clip 后 10×40 / 40×40 = 0.25 → 保留
    [-74.,  10.,   6.,  90.],     # clip 后 6×80 / 80×80 = 0.075 → **被 area_thr 砍**（宽度仍 >2）
    [ 20., 150.,  60., 200.],     # 贴着下边界但没被裁 → 保留
    [ 20., 198.,  60., 240.],     # clip 后高 2 px → **被 wh_thr 砍**
], dtype=float)
lb = np.array([0, 1, 2, 3, 4])
cb, cl, st = clip_and_filter(bx, lb, 200, 200)
print('裁剪后保留的框：'); print(cb)
print('保留的标签：', cl, '| 统计：', st)

assert st['n_in'] == 5
assert set(cl.tolist()) == {0, 1, 3}, cl
assert st['n_out'] == 3
assert cb[:, 0].min() >= 0 and cb[:, 2].max() <= 200
assert st['dropped_by_area'] == 1 and st['dropped_by_wh'] == 1, st
# 阈值放宽后，被 area 砍掉的那个（label=2）应当回来
cb2, cl2, st2 = clip_and_filter(bx, lb, 200, 200, area_thr=0.01, wh_thr=1.0)
assert st2['n_out'] > st['n_out'], '放宽阈值必须保留更多框'
assert 2 in cl2.tolist(), '放宽 area_thr 后，面积保留 7.5% 的那个框应当回来'
print('\n放宽到 area_thr=0.01, wh_thr=1.0 后保留：', cl2.tolist())
print('✅ 练习 1 通过：**area_thr 太高误杀小目标，太低留下「只剩一条边却标着完整类别」的框。**')
print('   TSR 小目标占比极高，这个阈值必须单独验证，不能抄默认值。')"""),

    md(r"""## ✏️ 练习 2：透视合法尺度带

实现 `perspective_band(y_bot, y_h, f, S, h_cam, mount_range)`，返回
`{'band': (s_min, s_max) 或 None, 'Z_range': (z_min, z_max) 或 None}`；
再实现 `sample_legal_scale(y_bot, rng, **kw)`：在合法带内均匀采一个尺度
（带为空或上界 < 4 px 时返回 `None`）。"""),

    code(r"""def perspective_band(y_bot, y_h=Y_H, f=F_PX, S=S_SIGN, h_cam=H_CAM, mount_range=MOUNT):
    # TODO: band = (S/(H_max-h_cam), S/(H_min-h_cam)) * (y_h - y_bot)
    #       Z_range 由 band 反推：Z = f*S/s_px（注意大尺寸对应小 Z）
    #       y_bot >= y_h → 都返回 None
    raise NotImplementedError

def sample_legal_scale(y_bot, rng, min_px=4.0, **kw):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 2 自测 ——
res = perspective_band(57.0)
print('y_bot=57 →', res)
assert abs(res['band'][0] - 0.6 / 1.7 * 33) < 1e-9
assert abs(res['band'][1] - 0.6 / 0.5 * 33) < 1e-9
assert abs(res['Z_range'][0] - F_PX * S_SIGN / res['band'][1]) < 1e-9
assert res['Z_range'][0] < res['Z_range'][1]
assert perspective_band(95.0)['band'] is None, '地平线以下必须非法'
assert perspective_band(Y_H)['band'] is None

# 采出来的尺度必须全部自洽
r = np.random.default_rng(4)
ok = 0; tried = 0
for _ in range(3000):
    y = float(r.uniform(5, 95))
    s = sample_legal_scale(y, r)
    if s is None:
        continue
    tried += 1
    ok += int(is_consistent(y, s))
print(f'\n采样 {tried} 个合法尺度，自洽率 {ok/tried:.1%}')
assert tried > 1500 and ok == tried, '带内采样必须 100% 自洽'

print(f"\n{'y_bot':>7s} {'合法带 (px)':>18s} {'距离 Z (m)':>18s}")
for y in [85, 70, 55, 30, 10]:
    b = perspective_band(float(y))
    print(f'{y:>7d} [{b["band"][0]:6.1f}, {b["band"][1]:6.1f}] '
          f'  [{b["Z_range"][0]:6.1f}, {b["Z_range"][1]:6.1f}]')
print('\n✅ 练习 2 通过：约束不是「事后检查」，而是**改采样方式** ——')
print('   先采位置、再在合法带内采尺度，合法率直接 100%（拒绝法要浪费 ~70% 的采样）。')"""),

    md(r"""## ✏️ 练习 3：粘贴位置的完整合法性检查

实现 `paste_valid(x0, y_bot, s_px, gt_boxes, img_wh, iou_thr=0.15, **kw)`，
返回 `(bool, reason)`。依次检查（**顺序即优先级**）：

1. `'below_horizon'` —— `y_bot >= y_h`；
2. `'scale_inconsistent'` —— `s_px` 不在合法带内；
3. `'out_of_image'` —— 粘贴框超出图像；
4. `'occludes_gt'` —— 与任一已有 GT 的 IoU > `iou_thr`；
5. 全部通过 → `(True, 'ok')`。"""),

    code(r"""def paste_valid(x0, y_bot, s_px, gt_boxes, img_wh=(W_SC, H_SC), iou_thr=0.15, **kw):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 3 自测 ——
GT = np.array([[100., 40., 130., 70.]])
cases = [
    ('合法',            210, 62.0, 22.0, True,  'ok'),
    ('贴到路面',        210, 120.0, 22.0, False, 'below_horizon'),
    ('尺度矛盾(太大)',  210, 62.0, 80.0, False, 'scale_inconsistent'),
    ('尺度矛盾(太小)',  210, 62.0,  5.0, False, 'scale_inconsistent'),
    ('越出右边界',      315, 62.0, 22.0, False, 'out_of_image'),
    ('压住已有GT',      103, 68.0, 26.0, False, 'occludes_gt'),
]
for name, x, y, s, exp_ok, exp_reason in cases:
    got_ok, got_reason = paste_valid(x, y, s, GT)
    flag = '✅' if (got_ok == exp_ok and got_reason == exp_reason) else '❌'
    print(f'{flag} {name:<16s} → ({got_ok}, {got_reason!r})   期望 ({exp_ok}, {exp_reason!r})')
    assert got_ok == exp_ok and got_reason == exp_reason, (name, got_ok, got_reason)

# 端到端：带约束的采样 + 合法性检查，合法率应当极高
r = np.random.default_rng(12)
acc = 0; tot = 0
for _ in range(2000):
    y = float(r.uniform(10, Y_H - 5))
    s = sample_legal_scale(y, r)
    if s is None or s > 60 or s >= y:     # s >= y 时框顶会跑出画面上边界，先排掉
        continue
    x = float(r.uniform(0, W_SC - s))
    tot += 1
    acc += int(paste_valid(x, y, s, GT)[0])
print(f'\n端到端合法率 {acc/tot:.1%}（{tot} 次尝试，剩下的失败几乎全是「会压住已有 GT」）')
assert acc / tot > 0.85
print('✅ 练习 3 通过：四条约束里，**位置与尺度这两条的收益远大于边缘融合** ——')
print('   做不到全部时，先做对的是这两条。')"""),

    md(r"""## ✏️ 练习 4：close-mosaic 调度器

实现 `aug_schedule(epoch, total, close_last=10, warmup=0, p_max=1.0)`：

- `epoch < warmup` → 线性从 0 升到 `p_max`（避免一开始就上最强增强）；
- `warmup <= epoch < total - close_last` → `p_max`；
- `epoch >= total - close_last` → `0.0`；
- 并实现 `schedule_is_valid(total, close_last, lr_at)`：给一个函数 `lr_at(epoch)`，
  检查关闭窗口内的**平均学习率**是否 ≥ 峰值学习率的 2%（窗口内学习率太小 = 等于没关）。"""),

    code(r"""def aug_schedule(epoch, total, close_last=10, warmup=0, p_max=1.0):
    # TODO
    raise NotImplementedError

def schedule_is_valid(total, close_last, lr_at, min_ratio=0.02):
    # TODO: 返回 (bool, 关闭窗口内平均 lr / 峰值 lr)
    raise NotImplementedError"""),

    code(r"""# —— 练习 4 自测 ——
T, C, WU = 100, 10, 5
ps = [aug_schedule(e, T, C, WU) for e in range(T)]
assert abs(ps[0]) < 1e-9, 'warmup 起点应为 0'
assert abs(ps[WU] - 1.0) < 1e-9 and abs(ps[T - C - 1] - 1.0) < 1e-9
assert all(abs(p) < 1e-9 for p in ps[T - C:]), '关闭窗口内必须为 0'
assert all(ps[i] <= ps[i + 1] + 1e-12 for i in range(WU)), 'warmup 段必须单调不降'
print('调度曲线（每 5 个 epoch 采样一次）：')
for e in range(0, T, 5):
    print(f'  epoch {e:>3d}  p_mosaic={ps[e]:.2f}  {"█"*int(ps[e]*20)}')

linear = lambda e: 0.01 * (0.99 * (1 - e / T) + 0.01)          # YOLOv5 默认 lrf=0.01
cos_floor = lambda e: 0.01 * (0.05 + 0.95 * 0.5 * (1 + np.cos(np.pi * e / T)))
cos_pure = lambda e: 0.01 * 0.5 * (1 + np.cos(np.pi * e / T))  # 无下限，尾部趋近 0
tiny_tail = lambda e: 0.01 * (1 - e / T) ** 4                  # 四次衰减，尾部几乎为 0
for name, f_ in [('linear (lrf=0.01)', linear), ('cosine + 5% floor', cos_floor),
                 ('cosine (无下限)', cos_pure), ('quartic decay', tiny_tail)]:
    ok, ratio = schedule_is_valid(T, C, f_)
    print(f'{name:<20s} 关闭窗口内平均 lr / 峰值 lr = {ratio:.4f}  '
          f'{"✅ 关得动" if ok else "❌ 学习率太小，等于没关"}')

assert schedule_is_valid(T, C, linear)[0] and schedule_is_valid(T, C, cos_floor)[0]
assert not schedule_is_valid(T, C, cos_pure)[0], '无下限 cosine 的尾部学习率太小'
assert not schedule_is_valid(T, C, tiny_tail)[0]
assert schedule_is_valid(T, C, linear)[1] > schedule_is_valid(T, C, tiny_tail)[1]
print('\n✅ 练习 4 通过：**close-mosaic 的有效性与学习率调度耦合。**')
print('   关闭窗口内如果学习率已经衰减到极小，模型根本动不了 —— 关了等于没关。')
print('   面试答「关 10 个 epoch」是背答案；答「窗口内要有足够的有效更新步数」才是懂机制。')"""),

    md(r"""---
### 📖 参考答案（先自己做，再对照）"""),

    code(r"""# 练习 1 参考答案
def clip_and_filter(boxes, labels, W, H, wh_thr=2.0, ar_thr=20.0, area_thr=0.10):
    b_old = np.asarray(boxes, dtype=float)
    if len(b_old) == 0:
        return b_old, np.asarray(labels), dict(n_in=0, n_out=0,
                                               dropped_by_area=0, dropped_by_wh=0)
    b_new = b_old.copy()
    b_new[:, [0, 2]] = np.clip(b_new[:, [0, 2]], 0, W)          # ★ 先 clip（注意花式索引是副本，
    b_new[:, [1, 3]] = np.clip(b_new[:, [1, 3]], 0, H)          #    不能用 np.clip(..., out=...)）
    w1, h1 = box_wh(b_old); w2, h2 = box_wh(b_new)
    eps = 1e-16
    ar = np.maximum(w2 / (h2 + eps), h2 / (w2 + eps))
    m_wh = (w2 > wh_thr) & (h2 > wh_thr)
    m_area = (w2 * h2 / (w1 * h1 + eps)) > area_thr             # ★ 再算面积比
    m_ar = ar < ar_thr
    keep = m_wh & m_area & m_ar
    st = dict(n_in=len(b_old), n_out=int(keep.sum()),
              dropped_by_area=int((~m_area & m_wh).sum()),
              dropped_by_wh=int((~m_wh).sum()))
    return b_new[keep], np.asarray(labels)[keep], st"""),

    code(r"""# 练习 2 参考答案
def perspective_band(y_bot, y_h=Y_H, f=F_PX, S=S_SIGN, h_cam=H_CAM, mount_range=MOUNT):
    if y_bot >= y_h:
        return {'band': None, 'Z_range': None}
    dy = y_h - y_bot
    lo = S / (mount_range[1] - h_cam) * dy
    hi = S / (mount_range[0] - h_cam) * dy
    return {'band': (float(lo), float(hi)),
            'Z_range': (float(f * S / hi), float(f * S / lo))}   # 大尺寸 ↔ 小 Z

def sample_legal_scale(y_bot, rng, min_px=4.0, **kw):
    band = perspective_band(y_bot, **kw)['band']
    if band is None or band[1] < min_px:
        return None
    lo = max(band[0], min_px)
    if lo >= band[1]:
        return None
    return float(rng.uniform(lo, band[1]))"""),

    code(r"""# 练习 3 参考答案
def paste_valid(x0, y_bot, s_px, gt_boxes, img_wh=(W_SC, H_SC), iou_thr=0.15, **kw):
    W, H = img_wh
    band = perspective_band(y_bot, **kw)['band']
    if band is None:
        return False, 'below_horizon'
    if not (band[0] <= s_px <= band[1]):
        return False, 'scale_inconsistent'
    box = np.array([[x0, y_bot - s_px, x0 + s_px, y_bot]], dtype=float)
    if box[0, 0] < 0 or box[0, 1] < 0 or box[0, 2] > W or box[0, 3] > H:
        return False, 'out_of_image'
    gt = np.asarray(gt_boxes, dtype=float).reshape(-1, 4)
    if len(gt) and float(iou_matrix(box, gt).max()) > iou_thr:
        return False, 'occludes_gt'
    return True, 'ok'"""),

    code(r"""# 练习 4 参考答案
def aug_schedule(epoch, total, close_last=10, warmup=0, p_max=1.0):
    if epoch >= total - close_last:
        return 0.0
    if warmup > 0 and epoch < warmup:
        return float(p_max * epoch / warmup)
    return float(p_max)

def schedule_is_valid(total, close_last, lr_at, min_ratio=0.02):
    lrs = np.array([lr_at(e) for e in range(total)], dtype=float)
    peak = float(lrs.max())
    tail = float(lrs[total - close_last:].mean())
    ratio = tail / (peak + 1e-12)
    return bool(ratio >= min_ratio), float(ratio)"""),

    md(r"""---
## 🧪 真实工程胶囊：TSR 的混合类增强配置与 copy-paste 流水线"""),

    code(r"""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
#  TSR 混合类增强：Ultralytics 配置 + 自建 copy-paste 流水线
# ══════════════════════════════════════════════════════════════════════
# ── ① Ultralytics 超参（注意：**增强强度必须随模型规模一起改**）──
# yolo train model=yolov8s.pt data=tsr.yaml epochs=200 \
#      mosaic=1.0 close_mosaic=10 \      # ★ 最后 10 epoch 关掉，修的是回归（AP75/AP90）
#      mixup=0.0 \                       # 检测里争议最大；小模型直接 0
#      copy_paste=0.0 \                  # Ultralytics 的 copy_paste 需要分割标注；
#                                        #   TSR 用下面的自建版本（形状先验生成掩码）
#      scale=0.5 fliplr=0.0 \            # ★ fliplr=0：交通标志禁止水平翻转（模块 01）
#      hsv_h=0.015 hsv_s=0.7 hsv_v=0.4   # ★ hsv_h 保持默认（乘性，仅 ±5.4°，模块 02）
#
# 各规模的建议（照抄 x 号配置去训 n 号 = 经典事故）：
#   n/s : mosaic=1.0 close_mosaic=10  mixup=0     copy_paste(自建)=每图 0-1 个
#   m/l : mosaic=1.0 close_mosaic=10  mixup=0.05  copy_paste(自建)=每图 0-2 个
#   x   : mosaic=1.0 close_mosaic=15  mixup=0.15  copy_paste(自建)=每图 1-3 个

# ── ② 自建 copy-paste：四条约束缺一不可 ──
import numpy as np

CAM = dict(f=1000.0, y_h=540.0, h_cam=1.5)        # ★ 从标定参数来，不要猜
SIGN = dict(S=0.60, mount=(2.0, 3.2))             # 标志物理直径 / 下缘安装高度范围

def legal_band(y_bot):
    # 约束一（尺度）：s_px = S/(H_m - h_cam) * (y_h - y_bot)，Z 被消掉
    if y_bot >= CAM['y_h']:
        return None                                # 约束二：地平线以下 = 贴到路面上，非法
    dy = CAM['y_h'] - y_bot
    return (SIGN['S'] / (SIGN['mount'][1] - CAM['h_cam']) * dy,
            SIGN['S'] / (SIGN['mount'][0] - CAM['h_cam']) * dy)

def copy_paste_one(img, gts, bank, rng, iou_thr=0.15, feather=1):
    for _ in range(20):                            # 拒绝重采样，最多试 20 次
        y_bot = rng.uniform(0.15, 0.95) * CAM['y_h']
        band = legal_band(y_bot)
        if band is None or band[1] < 8:
            continue
        s = rng.uniform(max(band[0], 8), band[1])  # ★ 在合法带内采，不是采完再判
        x0 = rng.uniform(0, img.shape[1] - s)
        box = np.array([x0, y_bot - s, x0 + s, y_bot])
        if len(gts) and iou(box[None], gts).max() > iou_thr:
            continue                               # 约束二：不能压住已有 GT
        inst = sample_instance(bank, rng)          # 按 1/sqrt(n_c) 加权，只采尾部类
        patch = resize_bilinear(inst['patch'], int(s), int(s))
        alpha = resize_bilinear(inst['alpha'], int(s), int(s))
        alpha = box_blur(alpha, feather)           # 约束三：羽化 1-2 px（**不要更多**）
        g = np.clip(local_bg_luma(img, box) / inst['src_bg_luma'], 0.5, 2.0)
        patch = np.clip(patch * g, 0, 1)           # 约束四：**乘性**亮度匹配
        #                                            （色相与饱和度严格不变 —— 模块 02）
        img = alpha_blend(img, patch, alpha, box)
        gts = np.vstack([gts, box]) if len(gts) else box[None]
        return img, gts, inst['cls']
    return img, gts, None

# ── ③ 实例库的质量门槛（实例库是**错误放大器**）──
BANK_FILTERS = dict(
    min_src_side=16,          # 源实例边长 < 16 px 不入库（放大就是马赛克）
    min_laplacian_pct=30,     # Laplacian 方差低于 p30 不入库（模糊/失焦）
    reject_truncated=True,    # 贴图像边缘的实例掩码不完整
    max_occlusion=0.20,       # 遮挡 > 20% 不入库
    ar_tolerance=0.30,        # 长宽比偏离类别典型值 > 30% → 多半是标注错误
    recheck_conf=0.50,        # 用现有模型回检，置信度 < 0.5 的**人工复核**
)
# ★ 一个错标实例会被贴进上千张训练图 = 上千个错标样本。
#   实例库是少数几个「人工复核明显划算」的环节。

# ── ④ 验证方式（不验证 = 不知道有没有用）──
# 1. close-mosaic：看 **AP75 / AP90**，不要只看 AP50（它修的是回归，不是分类）
# 2. copy-paste：**按类别分桶**看尾部类 AP；同时看头部类**不能掉**（回归门禁）
# 3. 记录「有效样本数」与「唯一源实例数」两个数 ——
#    召回上来但假阳暴涨 ⇒ 瓶颈是实例多样性，加再多 copy-paste 也没用，去采集
# 4. 换模型规模时**必须重调增强强度**：小模型 + 强增强 = 欠拟合（训练与验证一起差）
'''
print(RECIPE)
for token in ['close_mosaic', 'fliplr=0.0', 'legal_band', 'iou_thr', 'feather',
              '乘性', 'BANK_FILTERS', 'AP75', '错误放大器']:
    assert token in RECIPE, token
print('✅ 配方覆盖：规模相关的增强强度 / close-mosaic / 四条约束 / 实例库门槛 / 验证方式')"""),

    md(r"""### 小结

- **混合类增强改的是「样本的构成」**，不是位置也不是像素值。它同时破坏两个默认假设：
  一张图对应一次真实曝光、图像内容与标注一一对应。**收益大，所以必须被小心地关掉。**
- **Mosaic 的三个作用要能一口气说全**：① 每张训练图含 4 个不相关场景（打断上下文虚假相关）；
  ② 目标尺寸整体缩小 → 小目标占比 **9.8% → 50.9%**（**TSR 直接受益**）；
  ③ 单图目标数 **×3.2**（4 倍减去被过滤规则丢弃的）。
  副作用是**贴边截断框 3.4% → 11.3%**（真实实现用裁剪而非缩放，比例还要高得多）。
- **过滤规则是隐藏的杀手**：`area_thr` 太高误杀小目标，太低留下「只剩一条边却标着完整类别」
  的框；`wh_thr` 变大会系统性删掉最小的一批目标——**Mosaic 制造小目标，过滤规则又在删小目标**。
- **close-mosaic 修的是分布漂移，主要体现在回归上** → 看 **AP75/AP90**，只看 AP50 会得出
  「没用」的错误结论。关多少 epoch 不该答数字，该答「窗口内要有足够的有效更新步数」，
  **它与学习率调度耦合**。
- **MixUp 在检测里失去了理论依据**（标签是集合，不能插值）：目标半透明却按完整目标监督，
  且图像方差降到一半 → **BN 训练/推理统计错位**。**CutMix 的矩形不认识已有的框**：
  大目标分布下 53% 被部分覆盖（半个目标标着完整框），**小目标分布下 27% 变成幽灵框**
  （整体被盖住而标注仍在，直接教模型在无关纹理上报警）—— 总受损 41%。
  这正是 Copy-Paste 取代它的原因：**有实例掩码 ⇒ 知道自己贴了什么、贴在哪。**
- **Copy-Paste 是长尾最直接的解法**，四条约束按重要性排序：
  **① 尺度符合透视** `s_px = S/(H_m − h_cam)·(y_h − y_bot)`（Z 被消掉，是一条**合法带**）；
  **② 位置合法**（地平线以上、不压 GT、不越界）；**③ 边缘羽化 1–2 px**（多了变半透明贴纸）；
  **④ 乘性亮度匹配**（色相与饱和度严格不变；完整 color transfer 会毁掉颜色语义）。
- **约束要写进采样，而不是写成事后检查**：先采位置、再在合法带内采尺度 → 合法率 100%。
- **必须区分「有效样本数」与「有效实例多样性」**：用 `1/√n` 加权采样，尾部类的有效样本数
  中位数提升 **7×**、最稀有的类提升 **20×**（10 → 199），而**唯一源实例数一个没涨**。
  **它救上下文过拟合，救不了实例外观过拟合**——后者只能靠采集/挖掘（C58）。
- **实例库是错误放大器**：一个错标实例 = 上千个错标样本，值得单独人工复核。
  TSR 可以用**形状先验从框生成掩码**，绕开实例分割标注这个成本。
- **增强强度 × 模型容量 × 训练时长三者耦合**：最优强度随容量与时长单调上升。
  **小模型 + 强增强 = 欠拟合（训练与验证一起差）**；**短训练下比较增强配方是不公平的**。

下一站：**模块 04 · 增强流水线工程** —— 算子顺序与概率、CPU 吞吐瓶颈、
worker RNG 的真实事故，以及 TTA/WBF。""")
,
]
