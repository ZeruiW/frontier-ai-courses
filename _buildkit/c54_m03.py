# -*- coding: utf-8 -*-
"""C54 模块 03 · Object query 与交叉注意力：模型如何"认领"目标。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（二分匹配）、模块 02（集合损失）；C08/C09（Transformer 与注意力）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_object_queries.ipynb'),
    ("核心参考", "DETR (Carion 2020) §3.2 与附录 A.3/图 7；Conditional DETR (ICCV 2021)；Anchor-DETR (AAAI 2022)；DAB-DETR (ICLR 2022)"),
    ("预计时长", "读 65 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("what-is-query", "Object query 到底是什么：一个可学习的「提问」，不是特征", "".join([
        P("先把最常见的误解正面击碎：<strong>object query 不是「目标的特征」，"
          "也不是「候选框」，更不是从图像里提取出来的东西</strong>。"
          "它是 <code>nn.Embedding(num_queries, d_model)</code> —— "
          "一张 <code>100 × 256</code> 的<strong>可学习参数表</strong>，"
          "在整个数据集上是<em>同一份</em>，与输入图像完全无关。"),
        ASCII("""DETR decoder 的真实输入（PyTorch 官方代码的形状）

  tgt        = torch.zeros(100, B, 256)        ← **内容，初始化为全 0**
  query_pos  = self.query_embed.weight          ← (100, 256) **可学习参数**
  memory     = encoder 输出 (H*W/32^2, B, 256)  ← 图像证据
  mem_pos    = 2D sine positional encoding      ← 图像的位置编码

  每一层 decoder：
    q = k = tgt + query_pos ; v = tgt           ← self-attn：**pos 加在 Q/K，不加在 V**
    tgt = LN(tgt + SelfAttn(q, k, v))
    tgt = LN(tgt + CrossAttn(q = tgt + query_pos,
                             k = memory + mem_pos,
                             v = memory))       ← cross-attn：**V 不加位置编码**
    tgt = LN(tgt + FFN(tgt))

  最终 tgt (100, B, 256) --> 分类头 / 框头""",),
        P("三个必须读懂的细节："),
        OL([
            "<strong><code>tgt</code> 初始化为全 0</strong>。"
            "第一层 self-attention 之前，100 个 query 的「内容」<em>完全相同（都是 0 向量）</em>，"
            "区分它们的<strong>只有 <code>query_pos</code></strong>。"
            "所以「query 是什么」这个问题的答案就是 <code>query_pos</code>——一个位置嵌入。",

            "<strong>位置嵌入只加到 Q 和 K，从不加到 V</strong>。"
            "这是一条贯穿整个 DETR 的设计约定："
            "<em>位置只决定「往哪看 / 谁跟谁配对」，不决定「取回什么内容」</em>。"
            "如果把 pos 加进 V，取回来的向量里就混进了位置信息，"
            "后面的 FFN 无法区分「这是物体的外观」还是「这是我站的位置」。",

            "<strong><code>query_pos</code> 是参数，不是激活值</strong>。"
            "它在所有图像上共享，因此<em>一个 query 不可能编码「本图第 3 个物体」</em>——"
            "它没有这个信息。它能编码的只有一件事：<strong>一种搜索策略</strong>"
            "（「我负责去图像右上方找中等大小的东西」）。",
        ]),
        DUAL(
            "所以最准确的直觉是：<strong>query 是一个「提问模板」，decoder 是「带着问题去图上找答案」的过程</strong>。"
            "<code>tgt</code>（内容）从 0 开始，每过一层 cross-attention 就往里灌一点图像证据，"
            "每过一层 self-attention 就和别的 query 对一次账。"
            "<em>六层之后，<code>tgt</code> 里装的才是「我认领的那个物体长什么样、在哪」。</em>",
            "严格地说，<code>query_pos</code> 学到的是一个<span class=\"term\">learned positional prior</span>"
            "（可学习的位置先验）与一个<span class=\"term\">content template</span>（内容模板）的混合体——"
            "原始 DETR 并不区分这两者，这正是它收敛慢的原因之一。"
            "<strong>Conditional DETR 与 DAB-DETR 的核心改动，就是把这两者显式拆开</strong>"
            "（见第 7 节）：spatial query 只管「看哪里」，content query 只管「找什么」。"
            "<em>拆开之后，「query 是位置嵌入」这句话才真正名副其实。</em>",
        ),
        CALLOUT("warn", "<strong>面试常见翻车点</strong>：被问「object query 是什么」时说"
                "「是 100 个候选目标的特征向量」——这句话在初始状态下是<em>错的</em>"
                "（初始内容是 0 向量），在训练后也只是<em>近似对</em>（decoder 输出才是特征，"
                "query 本身仍是那份不变的参数表）。"
                "<strong>面试官想听的是：query 是与图像无关的可学习位置嵌入，"
                "它编码的是「搜索策略」；真正的目标特征是 decoder 逐层从 memory 里取回来累积在 "
                "<code>tgt</code> 上的。</strong>"),
    ])),

    ("division", "职责分工：self-attention 谈判去重，cross-attention 取证据", "".join([
        P("这一节是<strong>理解 DETR 的钥匙</strong>。"
          "decoder 每层有两个注意力，它们不是「都在做注意力」，"
          "而是<strong>两条完全不同的信息通道，各自承担一个不可替代的职责</strong>。"),
        ASCII("""                     ┌───────────────────────────────┐
   query 0 ────┐      │                               │
   query 1 ────┤      │        SELF-ATTENTION         │  ← **唯一的 query↔query 通道**
   query 2 ────┼──────┤   「你认领哪个？那我换一个」    │     职责：协商、去重、分工
     ...       │      │   信息只在 100 个 query 之间流  │     不看图像
   query 99 ───┘      └───────────────┬───────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
   encoder memory ───→│        CROSS-ATTENTION        │  ← **唯一的 image→query 通道**
   (H*W/1024 个 token)│   「图上哪块区域支持我的假设？」 │     职责：取证据
                      │   信息从图像单向流入 query      │     query 之间**不通信**
                      └───────────────┬───────────────┘
                                      ▼
                                     FFN
                              （逐 query 独立）

关键不对称：cross-attn 与 FFN 都是**逐 query 独立**的（pointwise），
            所以**如果拿掉 self-attention，整个 decoder 就是 100 条互不相干的流水线**。"""),
        TABLE(["", "<strong>self-attention</strong>", "<strong>cross-attention</strong>"], [
            ["Q 来自", "query（<code>tgt + query_pos</code>）", "query（<code>tgt + query_pos</code>）"],
            ["K / V 来自", "<strong>query 自己</strong>", "<strong>encoder memory（图像）</strong>"],
            ["序列长度", "N = 100（很短）", "H·W/1024 ≈ 850–1000（很长）"],
            ["职责", "<strong>协商：谁认领谁、去掉重复</strong>", "<strong>取证：这个假设有没有像素支持</strong>"],
            ["拿掉它会怎样", "<strong>出现大量重复框</strong>（退化回需要 NMS）", "query 拿不到任何图像信息，输出与输入无关"],
            ["计算量", "O(N²·d) = 100²·256，可忽略", "<strong>O(N·HW·d)</strong>，是 decoder 的主要开销"],
            ["第一层是否必要", "<strong>几乎不必要</strong>（此时 tgt 全 0，没什么可谈判）", "必要"],
        ]),
        P("表格最后一行是 DETR 论文附录里一个很有说服力的消融："
          "<strong>去掉<em>第一层</em>的 self-attention，AP 几乎不掉</strong>——"
          "因为那时 <code>tgt</code> 还是 0，所有 query 的内容一模一样，"
          "「谈判」没有任何信息可谈。"
          "<strong>但去掉后面几层的 self-attention，AP 掉约 <em>3 个点</em>，"
          "并且失效模式非常特征化：同一个物体上冒出多个高分框。</strong>"
          "<em>这个「哪一层可以去掉、哪一层不能」的差异，正好证明了 self-attention 的职责是去重而不是别的。</em>"),
        DUAL(
            "为什么<strong>只有</strong> self-attention 能做去重？因为 cross-attention 和 FFN "
            "都是<span class=\"term\">pointwise</span>（逐 query 独立）的运算："
            "query <em>i</em> 的输出<strong>只依赖 query <em>i</em> 自己的输入</strong>，"
            "和 query <em>j</em> 在干什么<em>数学上无关</em>。"
            "<em>notebook 第 3 节会用一个扰动实验精确验证这一点：改动 query 5，"
            "在无 self-attention 的 decoder 里其余 query 的输出<strong>逐比特不变</strong>；"
            "加上 self-attention 后立刻改变。</em>",
            "把这件事和模块 02 的一对一匹配连起来，DETR 的去重机制就完整了："
            "<strong>一对一匹配提供了「压力」（一个 GT 只有一个 query 能拿到正标签，"
            "其余全被推向 ∅），self-attention 提供了「执行这个压力的通道」</strong>。"
            "<em>两者缺一不可</em>：只有匹配没有通道，query 之间无法协调，"
            "只能各自靠静态先验碰运气；只有通道没有匹配（一对多监督），"
            "则根本没有「你退我进」的训练信号。"
            "<strong>面试里能把「压力」和「通道」拆开讲，是很强的信号。</strong>",
        ),
        CALLOUT("danger", "<strong>高频面试题：「DETR 为什么不需要 NMS？」</strong>"
                "只答「因为一对一匹配」<em>只答对了一半</em>，而且是容易被追问穿的一半。"
                "追问会是：「一对一匹配只是损失函数，推理时又不算损失，凭什么推理时不出重复框？」"
                "<strong>完整答案：一对一匹配在<em>训练期</em>制造了「重复必被惩罚」的压力，"
                "而 decoder 的 self-attention 提供了 query 之间互相观察、互相抑制的<em>通道</em>，"
                "使模型能把这种抑制学进权重里；推理时抑制行为已经内化在注意力权重中，"
                "所以不需要外挂 NMS。</strong>", "面试必答：一对一匹配是「压力」，self-attention 是「通道」"),
    ])),

    ("cross-mechanics", "Cross-attention 的机制细节：Q/K/V 从哪来，位置编码加在哪", "".join([
        MATH("\\mathrm{CrossAttn}(\\mathbf{q}_i) = \\sum_{k=1}^{HW} "
             "\\underbrace{\\mathrm{softmax}_k\\!\\left(\\frac{"
             "(\\mathbf{t}_i + \\mathbf{p}^{q}_i)^\\top W_Q^\\top W_K (\\mathbf{m}_k + \\mathbf{p}^{m}_k)}"
             "{\\sqrt{d_h}}\\right)}_{\\text{注意力权重 } a_{ik}} \\; W_V\\,\\mathbf{m}_k"),
        P("把这个式子逐块读一遍，每一块都有一个「为什么」："),
        TABLE(["符号", "是什么", "为什么这样设计"], [
            ["<code>t<sub>i</sub></code>", "query <em>i</em> 的当前内容（初始 0，逐层累积）",
             "承载「我目前认为我认领的是什么」"],
            ["<code>p<sup>q</sup><sub>i</sub></code>", "query <em>i</em> 的可学习位置嵌入",
             "<strong>提供空间先验：「我大概往哪块区域看」</strong>"],
            ["<code>m<sub>k</sub></code>", "encoder 输出的第 <em>k</em> 个空间位置特征", "图像证据"],
            ["<code>p<sup>m</sup><sub>k</sub></code>", "图像的 2D sine 位置编码",
             "让 attention 能表达「左上角 / 右下角」这类空间关系"],
            ["<strong>V 里没有 <code>p<sup>m</sup></code></strong>", "value 用的是纯 <code>m<sub>k</sub></code>",
             "<strong>位置只决定「看哪里」，不该混进「取回什么」</strong>"],
            ["<code>HW</code>", "≈ 850–1000（800×1066 输入 / stride 32）",
             "<strong>key 的数量决定了初始注意力有多「稀」</strong>"],
        ]),
        H3("初始注意力近似均匀 —— 这是 DETR 收敛慢的第一个根因"),
        P("训练开始时，<code>t<sub>i</sub> = 0</code>，<code>p<sup>q</sup></code> 随机初始化，"
          "于是 attention logits 的方差很小，<strong>softmax 之后近似均匀分布在 ~1000 个 key 上</strong>。"
          "用<span class=\"term\">effective span</span>（有效关注范围，定义为 <code>exp(H(a))</code>，"
          "<code>H</code> 为注意力分布的熵）来量化："),
        MATH("\\text{effective span} = \\exp\\big(H(a_i)\\big) = "
             "\\exp\\Big(-\\sum_k a_{ik}\\log a_{ik}\\Big) "
             "\\;\\;\\xrightarrow[\\;\\text{均匀}\\;]{}\\;\\; HW \\approx 1000, "
             "\\qquad \\xrightarrow[\\;\\text{收敛后}\\;]{}\\;\\; O(10)"),
        P("<strong>初始 span 动辄好几百（notebook 实测约占全部 key 的 60%），意味着每个 key 只分到几百分之一的梯度</strong>。"
          "模型必须先花掉大量 epoch 把注意力「收窄」到目标区域，才谈得上学定位。"
          "<em>这正是 DETR 需要 500 epoch 的核心机理之一</em>，"
          "也是 Deformable DETR 用「每个 query 只采样 K=4 个点」来根治它的原因（模块 04）。"
          "notebook 的练习 4 会实测这个数字。"),
        DUAL(
            "多头的作用在 cross-attention 里特别直观。DETR 论文的可视化显示："
            "<strong>不同的 head 会去关注同一物体的<em>不同极值点</em></strong>"
            "（左边缘、右边缘、上沿、下沿）。这非常合理——"
            "<em>要预测一个框的四条边，最自然的分工就是让几个 head 各负责一条边</em>。"
            "所以 cross-attention 的注意力图在收敛后往往<strong>不是一个团，而是几个点</strong>。",
            "这个观察有个直接的工程推论：<strong>cross-attention 的注意力图是 DETR 最好用的调试工具</strong>。"
            "把 <code>a<sub>ik</sub></code> reshape 回 <code>H×W</code> 画出来，可以一眼看出："
            "① query 有没有找到目标（注意力是否聚焦在目标上）；"
            "② 是不是几个 query 聚焦到了同一个目标（重复框的前兆）；"
            "③ 注意力是否还是弥散的（收敛不足）。"
            "<em>在 <strong>TSR</strong> 里这尤其有用：远处 8–16 px 的标志在 stride-32 特征图上"
            "只占不到半个格子，如果注意力图显示 query 关注的是杆件而不是牌面，"
            "就说明特征分辨率不够，该加 P2 层或用多尺度可变形注意力，而不是继续调超参。</em>",
        ),
        CALLOUT("intuition", "记住这条位置编码的规则，它在所有 DETR 变体里都成立："
                "<strong>位置编码进 Q 和 K，永远不进 V</strong>。"
                "推论：<em>凡是看到某个实现把 pos 加进了 V，基本可以判定是 bug</em>。"
                "同样的规则也解释了为什么 encoder 的位置编码要<strong>每一层都重新加一次</strong>"
                "（而不是像 ViT 那样只在输入加一次）——因为它只影响配对，不进入残差流。"),
    ])),

    ("dedup", "Self-attention 如何实现「训练期的 NMS」", "".join([
        P("上一节说了 self-attention 是去重的<em>通道</em>。这一节把「它到底怎么去的重」讲透，"
          "并说明<strong>它比 NMS 强在哪、弱在哪</strong>。"),
        H3("机制：一对一匹配把「重复」变成了可导的损失"),
        P("假设 query 3 和 query 7 都锁定了同一块限速牌。匹配阶段只有一个能拿到这个 GT"
          "（比如 query 3），<strong>query 7 被匹配到 ∅，它的分类目标变成「背景」</strong>。"
          "于是梯度会同时做两件事：① 压低 query 7 的前景分数；"
          "② 通过 self-attention 的连接，让 query 7 <strong>学会「当我看到 query 3 已经在认领这块牌子时，我就该退让」</strong>。"),
        P("第 ② 点才是关键——它把「退让」变成了一个<strong>输入条件（input-conditional）的函数</strong>："
          "query 7 不是永远沉默，而是<em>在检测到冲突时</em>沉默。"
          "<strong>这正是 self-attention 相比「静态先验」的根本优势</strong>："
          "如果 query 只有静态的位置先验、没有互相通信的能力，"
          "那么当一张图里两个目标恰好都落进 query 7 的偏好区域时，它无法动态调整。"),
        TABLE(["", "NMS（推理期、手工规则）", "<strong>self-attention 去重（训练期学到）</strong>"], [
            ["何时生效", "推理后处理", "<strong>内化在权重里，推理时零额外开销</strong>"],
            ["判据", "<strong>只看 IoU 阈值</strong>", "<strong>可用外观、语义、上下文、相对位置</strong>"],
            ["超参", "IoU 阈值（0.5/0.6/0.7，需按数据集调）", "<strong>无</strong>"],
            ["延迟", "<strong>随目标数波动</strong>（O(n²)，是 p99 延迟的不确定来源）", "固定（已在 O(N²) 的 self-attn 里）"],
            ["密集/重叠场景", "<strong>两难</strong>：阈值高则重复多，阈值低则误删真目标", "可学会「这是两个物体」而不是「重复」"],
            ["失败模式", "同类相邻目标被误删", "<strong>训练不足时重复框仍会出现</strong>（去重没学会）"],
            ["可解释性", "高（规则明确）", "低（藏在注意力权重里）"],
        ]),
        DUAL(
            "「判据可以不只是 IoU」这一条在 <strong>TSR 里有非常具体的价值</strong>。"
            "中国高速上很常见的一种排布是<em>同一根立杆上下挂两块牌</em>"
            "（上面「限速 100」，下面「解除限速」的辅助牌），或者<em>组合标志牌</em>"
            "（一个大蓝底牌里嵌着几个小图标）。"
            "<strong>这些框的 IoU 天然很高</strong>——NMS 阈值设 0.5 会把下面那块牌当重复删掉，"
            "设 0.7 又会在别处放出重复框。<em>而 self-attention 可以学到"
            "「这两个框虽然重叠，但颜色/形状/语义不同，是两个物体」</em>。",
            "反过来也要诚实说清 self-attention 去重的<strong>代价与失效场景</strong>："
            "① 它是<em>学出来的</em>，所以在训练不足、数据分布外的场景上会失效——"
            "<strong>DETR 训练早期最典型的现象就是满屏重复框</strong>；"
            "② 它<em>不可调</em>：NMS 的阈值可以在部署时按场景改，"
            "而学到的抑制行为要改就得重训；"
            "③ 它<em>不可解释</em>：出了重复框，你没有一个「把阈值调一下」的旋钮。"
            "<strong>所以量产系统里常见的做法是「主要靠模型去重，但仍保留一个非常宽松的 NMS 兜底」</strong>"
            "（IoU 阈值 0.9 左右，只删几乎完全重合的框），"
            "<em>用极小的延迟代价买一个保险</em>——这是模块 05 会展开的工程取舍。",
        ),
        CALLOUT("warn", "训练诊断技巧：<strong>统计「同一个 GT 附近出现 ≥2 个高分预测」的比例</strong>，"
                "把它作为一个训练期指标画出来。"
                "<em>如果这个「重复率」随 epoch 稳定下降，说明 self-attention 的去重正在学到；"
                "如果它长期不降，通常意味着 ① query 数量太少（query 之间竞争过于激烈）、"
                "② 匹配不稳定（模块 04 的 DN-DETR 就是治这个的）、"
                "或 ③ self-attention 被错误地加了 mask。</em>"),
    ])),

    ("specialization", "Query 的空间特化：训练完之后，它们各自变成了什么", "".join([
        P("DETR 论文图 7 是这门课里最值得反复看的一张图："
          "作者把 100 个 query 中的 20 个挑出来，"
          "<strong>把它们在 COCO val 上预测出的所有框的中心点画在同一张图上</strong>。"
          "结果是：<em>每个 query 都形成了一个清晰的、与其他 query 不同的分布</em>。"),
        ASCII("""query #12 的框中心分布            query #47 的框中心分布
  ┌─────────────────────┐          ┌─────────────────────┐
  │  · ·                │          │              ·  ··· │
  │ ····                │          │             ······  │
  │ ·····               │          │              ····   │
  │  ···                │          │                     │
  │                     │          │                     │
  │ ══════════════════  │ ← 几乎每个 │ ══════════════════  │ ← 这条横线是
  └─────────────────────┘   query 都 └─────────────────────┘   「大的、横跨全图的框」
   偏好：左上、中小目标      有的模式    偏好：右上、小目标        （COCO 的分布偏差）

结论：query = **一种「区域 + 尺度」的操作模式（operating mode）**
      而不是一个固定的框，也不是一个固定的类别。""",),
        UL([
            "<strong>空间特化是自发涌现的</strong>，没有任何损失项要求 query 分工。"
            "它是一对一匹配的必然结果：<em>如果两个 query 的偏好完全一样，"
            "它们会永远争夺同一批 GT，其中一个总是拿到 ∅ 标签、被压成背景——"
            "于是「分开」才是损失更低的解。</em>",

            "<strong>特化的维度是「位置 + 尺度」，不是「类别」</strong>。"
            "论文里没有观察到「某个 query 专门检测人」这类语义特化。"
            "<em>原因很直接：query 的先验是通过 cross-attention 的空间项起作用的，"
            "而空间项天然只能表达「看哪里、看多大」。</em>",

            "<strong>几乎每个 query 都保留了一个「大横框」模式</strong>（图里那条横线）。"
            "这是 COCO 数据集的偏差（大量图像有一个占满画面的主体）被 query 学了进去。"
            "<em>这直接说明：query 的特化是<strong>数据分布的镜像</strong>。</em>",
        ]),
        DUAL(
            "「query 特化是数据分布的镜像」这句话在 <strong>TSR 上有非常实际的后果</strong>。"
            "中国高速的交通标志分布是极度有结构的：<em>竖直方向集中在地平线上方一条窄带里，"
            "水平方向偏向道路右侧（右行 + 立杆在右），龙门架标志则集中在画面正上方</em>。"
            "在这样的数据上训练，<strong>query 会强烈特化到「右上 + 正上」这两块区域</strong>——"
            "notebook 第 5 节会用一个真训练的合成实验把这个现象复现出来。",
            "而这就带来一个<strong>容易在实车上炸、离线却看不出的失效模式</strong>："
            "一旦分布变了——<em>换到左行国家、换到城市道路（标志更低更近）、"
            "换到匝道或环岛（标志出现在画面左侧）</em>——"
            "<strong>那些从没被训练到过的区域没有任何 query 负责，召回会成片掉下去</strong>，"
            "而整体 mAP 可能只掉一两个点（因为主分布还在）。"
            "<em>对策：① 评测必须按「标志在画面中的位置」分桶（C55 模块 05）；"
            "② 数据要覆盖各类道路几何；③ 慎用水平翻转增强——它能补左侧分布，"
            "但会把「左转」翻成「右转」、把文字镜像（C56 模块 01 的禁区）。</em>"
            "<strong>「用翻转增强补 query 的空间偏置」是个陷阱，能主动指出来是加分项。</strong>",
        ),
        CALLOUT("intuition", "一个可迁移的心法：<strong>凡是「一组并行的、可学习的槽位（slot）」"
                "配上「一对一分配」的结构，都会自发产生特化</strong>。"
                "这个模式在 Slot Attention（无监督物体发现）、"
                "MoE 的专家路由、Perceiver 的 latent array 里反复出现。"
                "<em>反过来，如果你观察到槽位<strong>没有</strong>特化（都长得差不多），"
                "通常意味着分配机制失效了——比如 MoE 的路由崩塌、或者 DETR 的匹配极不稳定。</em>"),
    ])),

    ("num-queries", "Query 数量 N 怎么选：一笔必须算清的账", "".join([
        P("<code>N</code> 是 DETR 系最显眼的超参之一，"
          "而关于它的直觉<strong>有一半是错的</strong>。先立三条硬约束："),
        OL([
            "<strong><code>N</code> 必须严格大于单图最大目标数</strong>——"
            "否则那张图上必然有 GT 匹配不到 query，形成<em>结构性漏检</em>（无论怎么训练都救不回来）。"
            "COCO 单图最多 63 个实例，DETR 取 100。",

            "<strong>但 <code>N</code> 大于最大目标数还不够</strong>。"
            "DETR 论文做过一个尖锐的实验：合成一张有 100 个小目标的图，"
            "<em>模型在检出约 50 个之后开始饱和</em>。"
            "说明 query 之间并非完全对称、可互换——"
            "<strong>「N=100 就能检 100 个」是错的，实际可用容量大约只有一半</strong>。",

            "<strong><code>N</code> 越大，正样本比例越低</strong>："
            "<code>M/N</code> 直接决定了分类损失里前景与背景的比例（模块 02 的 <code>eos_coef</code> 问题）。"
            "<em>这也是为什么把 N 从 100 提到 900 的工作（DINO）必须同时把 CE 换成 focal loss</em>——"
            "softmax + <code>eos_coef</code> 那套在 N=900 时会失控。",
        ]),
        MATH("\\text{正样本比例} = \\frac{\\mathbb{E}[M]}{N}: \\quad "
             "\\underbrace{\\frac{7.7}{100} = 7.7\\%}_{\\text{COCO, DETR}} \\quad "
             "\\underbrace{\\frac{7.7}{900} = 0.86\\%}_{\\text{COCO, DINO}} \\quad "
             "\\underbrace{\\frac{1.8}{100} = 1.8\\%}_{\\textbf{TSR, N=100}} \\quad "
             "\\underbrace{\\frac{1.8}{900} = 0.2\\%}_{\\textbf{TSR, N=900}}"),
        TABLE(["N", "代表模型", "正样本比例（COCO）", "self-attn 计算", "匈牙利匹配", "分类损失"], [
            ["<strong>100</strong>", "DETR / Conditional DETR", "7.7%", "10<sup>4</sup>（可忽略）",
             "O(M²N)，很快", "softmax CE + <code>eos_coef</code>=0.1"],
            ["<strong>300</strong>", "Deformable DETR / DAB-DETR", "2.6%", "9×10<sup>4</sup>",
             "3× 于 N=100", "<strong>sigmoid focal</strong>"],
            ["<strong>900</strong>", "DINO / Co-DETR", "0.86%", "8×10<sup>5</sup>",
             "<strong>9× 于 N=100，CPU 上开始可见</strong>", "<strong>sigmoid focal（必须）</strong>"],
            ["<em>N &lt; max objects</em>", "—", "—", "—", "—",
             "<strong>❌ 结构性漏检，任何训练都救不回</strong>"],
        ]),
        DUAL(
            "一个<strong>极常见的误解</strong>：「DINO 用 900 个 query 是因为它要检更多目标」。"
            "<em>不是。</em> COCO 单图最多 63 个实例，100 早就够了。"
            "<strong>把 N 提到 300/900 的真实动机是「增加监督密度、加快收敛」</strong>："
            "query 越多，encoder 提议（two-stage 里 query 由 encoder 的 top-k 初始化）覆盖越密，"
            "每张图能产生的有效梯度路径越多。<em>这与「一对多辅助分支」（Group DETR / Co-DETR）"
            "是同一个动机的两种做法——都在解决「一对一监督太稀疏」。</em>",
            "对 <strong>TSR</strong> 来说，这个账要重新算。"
            "一张高速前视图像通常只有 <strong>1–5 块标志</strong>，极端情况（复杂互通、多杆并列）也就十几块。"
            "<em><code>N=100</code> 已经远远超过需求，继续加到 900 不会提升召回，"
            "只会让正样本比例从 1.8% 掉到 0.2%、并增加匹配与 self-attn 开销</em>。"
            "<strong>但也不该激进地把 N 砍到 20</strong>——"
            "① query 的实际可用容量只有名义值的一半左右；"
            "② N 太小会让 query 之间竞争过于激烈，加剧匹配不稳定；"
            "③ 车端的 self-attn 开销在 N=100 时本来就可忽略（10<sup>4</sup> 量级）。"
            "<strong>结论：TSR 场景 <code>N</code> 取 50–100 是合理区间，"
            "这个「按目标数分布反推 N」的推理过程本身就是很好的面试素材</strong>——"
            "notebook 练习 3 会把它写成一个决策脚本。",
        ),
        CALLOUT("warn", "改 <code>N</code> 时有两个必须同步改的地方，忘了就会「换个数字模型就废」："
                "① <strong>分类损失的配置</strong>（N 大幅增加时 softmax + <code>eos_coef</code> 必须换成 focal）；"
                "② <strong>推理端的 top-k</strong>（DETR 取所有 query 的 argmax；"
                "focal 版在 <code>N×K</code> 个 (query, 类) 对里取 top-100——"
                "<em>N 变了而 top-k 没变，会直接改变召回上限</em>）。"),
    ])),

    ("spatial-prior", "给 query 装上空间先验：Conditional / Anchor / DAB-DETR", "".join([
        P("原始 DETR 的 query 是一个「什么都混在一起」的 256 维向量："
          "既要编码「看哪里」，又要编码「找什么」，还要参与去重协商。"
          "<strong>这一系列工作的共同思路，就是把「看哪里」这件事从向量里<em>拆出来、显式化</em></strong>，"
          "让它有明确的空间语义。"),
        TABLE(["工作", "query 变成什么", "关键机制", "收敛加速"], [
            ["<strong>DETR</strong>", "一个 256-d 可学习向量", "什么都混在一起", "基准（500 epoch）"],
            ["<strong>Conditional DETR</strong>",
             "<strong>content query + spatial query 分开</strong>",
             "cross-attn logits 拆成 <code>c<sub>q</sub>·c<sub>k</sub> + p<sub>q</sub>·p<sub>k</sub></code>；"
             "<code>p<sub>q</sub></code> 由参考点生成", "<strong>6.7×</strong>（→ 50–75 epoch）"],
            ["<strong>Anchor-DETR</strong>", "<strong>2D 锚点 (x, y)</strong>",
             "query 直接由锚点的位置编码生成，完全可解释", "~10×"],
            ["<strong>DAB-DETR</strong>", "<strong>4D anchor box (x, y, w, h)</strong>",
             "<strong>用 w, h 调制位置注意力的宽窄</strong> + <strong>逐层精修 anchor</strong>", "~10×（50 epoch）"],
            ["<strong>DINO</strong>", "4D anchor + 混合初始化",
             "encoder top-k 提议初始化位置部分，content 部分仍可学", "12 epoch 即 SOTA"],
        ]),
        H3("Conditional DETR：把 attention logits 拆成内容项 + 空间项"),
        MATH("(\\mathbf{c}_q + \\mathbf{p}_q)^\\top(\\mathbf{c}_k + \\mathbf{p}_k) \\;\\;\\longrightarrow\\;\\; "
             "\\underbrace{\\mathbf{c}_q^\\top \\mathbf{c}_k}_{\\text{内容：找什么}} \\;+\\; "
             "\\underbrace{\\mathbf{p}_q^\\top \\mathbf{p}_k}_{\\text{空间：看哪里}}"),
        P("原始 DETR 把 pos 直接<em>加</em>进 Q/K，展开后会多出两个交叉项 "
          "<code>c<sub>q</sub>·p<sub>k</sub></code> 和 <code>p<sub>q</sub>·c<sub>k</sub></code>——"
          "<strong>这两项让「内容」和「位置」互相污染，谁也说不清 attention 到底在响应什么</strong>。"
          "Conditional DETR 把它们去掉（等价于把 content 与 spatial 拼接后做单次点积，"
          "notebook 练习 1 会验证这个等价性），"
          "<em>于是空间项可以独立地把注意力「拉」到参考点附近，内容项独立地负责匹配外观</em>。"),
        H3("DAB-DETR：用 w, h 调制位置注意力的「窗口宽度」"),
        P("Conditional DETR 的空间项是<strong>各向同性</strong>的：注意力窗口是个固定大小的圆斑。"
          "但目标有大有小、有宽有扁——<em>一块 8×8 的远处限速牌和一块跨越整个画面的龙门架指路牌，"
          "需要的注意力窗口差了两个数量级</em>。DAB-DETR 的做法非常漂亮："),
        MATH("\\mathrm{PosAttn}(x_q, x_k) = \\mathrm{PE}\\!\\left(\\frac{x_q}{w_q}\\right)^{\\!\\top} "
             "\\mathrm{PE}\\!\\left(\\frac{x_k}{w_q}\\right), \\qquad "
             "\\mathrm{PE}(x)^\\top \\mathrm{PE}(x') = \\sum_{j} \\cos\\big(\\omega_j (x - x')\\big)"),
        P("右边那个恒等式是关键：<strong>正弦位置编码的点积只依赖于两点的<em>距离</em>，"
          "并且是一个以 0 为峰的钟形核</strong>。"
          "所以把坐标除以 <code>w<sub>q</sub></code>，"
          "<strong>就等于把这个核在空间上<em>拉宽</em> <code>w<sub>q</sub></code> 倍</strong>——"
          "宽目标得到宽窗口，小目标得到窄窗口。"
          "<em>notebook 第 6 节会把这个核画出来并实测半宽，验证它精确地正比于 w。</em>"),
        DUAL(
            "DAB-DETR 还带来第二个红利：<strong>既然 query 就是一个框 <code>(x,y,w,h)</code>，"
            "那它就可以被<em>逐层精修</em></strong>——"
            "第 <em>l</em> 层预测一个增量 <code>Δ</code>，"
            "在 inverse-sigmoid 空间累加后得到第 <em>l+1</em> 层的 anchor。"
            "<em>这与模块 02 讲的辅助损失是天生一对</em>："
            "辅助损失要求每层都输出可用的框，逐层精修则提供了「在前一层基础上改进」的结构。"
            "<strong>DINO 的 look-forward-twice 正是在这条链上的进一步优化</strong>（模块 04）。",
            "从更高的视角看，这一整条线做的事情可以概括成一句话："
            "<strong>把「隐式的、纠缠的」query 逐步改造成「显式的、可解释的、可精修的」空间假设</strong>。"
            "<em>而它的终点非常有意思：当 query 变成一个 4D 框、并且逐层精修时，"
            "它已经在结构上极其接近一个「可学习的、动态的 anchor」了</em>——"
            "这正好把我们带到下一节那个高频面试题。",
        ),
        CALLOUT("intuition", "这条演进线还有一个可迁移的启发："
                "<strong>当一个模块「什么都能表示」但收敛很慢时，"
                "往往是因为它需要先<em>学会</em>一个本可以直接<em>写死</em>的结构</strong>。"
                "<em>DETR 的 query 要从随机向量里学出「空间局部性」这个先验，"
                "而 CNN 的卷积核天生就有。给 query 装上 <code>(x,y,w,h)</code> 的显式语义，"
                "本质上是把这个先验直接送给它。</em>"
                "这与「加归纳偏置 vs 让模型自己学」的经典权衡是同一件事——"
                "<strong>数据量不够时，送先验；数据量足够时，先验反而是天花板。</strong>"),
    ])),

    ("query-vs-anchor", "Query 与 anchor 的本质异同（面试爱问）", "".join([
        P("这是 DETR 相关面试里<strong>区分度最高的问题之一</strong>，"
          "因为它同时考察你对两代检测器的理解深度。"
          "很多人会给出一个非黑即白的答案（「query 是学出来的，anchor 是设计的」），"
          "<em>而好答案应该指出：它们在「提供空间先验」这个功能上是同构的，"
          "真正的差别在<strong>监督方式</strong>和<strong>是否可动</strong></em>。"),
        TABLE(["维度", "Anchor（Faster R-CNN / YOLO / RetinaNet）",
               "<strong>Object query（DETR 系）</strong>"], [
            ["本质", "预设的参考框（尺度 × 长宽比 × 位置）", "可学习的 <code>d</code> 维嵌入（DAB 后：4D 框）"],
            ["来源", "<strong>人工设计</strong>（或对训练集 wh 做 k-means 聚类）",
             "<strong>随机初始化 + 反向传播学出来</strong>"],
            ["数量", "<strong>密集</strong>：每个特征图格点 ×A 个，总量 10<sup>4</sup>–10<sup>5</sup>",
             "<strong>稀疏</strong>：100–900 个"],
            ["与位置的绑定", "<strong>硬绑定到特征图格点</strong>（anchor 不能离开自己的格子）",
             "<strong>不绑定</strong>：一个 query 可以在任意位置出框（有偏好但无硬约束）"],
            ["跨图共享", "是（同一套 anchor 用于所有图）", "是（同一份参数表用于所有图）"],
            ["<strong>监督方式</strong>", "<strong>一对多</strong>（一个 GT 匹配多个 anchor）",
             "<strong>一对一</strong>（一个 GT 只匹配一个 query）"],
            ["<strong>是否需要 NMS</strong>", "<strong>需要</strong>", "<strong>不需要</strong>（模块 02 + 本模块第 4 节）"],
            ["能否逐层精修", "两阶段可以（RPN→RCNN），单阶段一般不", "<strong>可以</strong>（DAB/DINO 的 iterative refinement）"],
            ["query 之间是否通信", "<strong>否</strong>（anchor 之间完全独立）", "<strong>是</strong>（self-attention）"],
            ["需要调的先验超参", "尺度、长宽比、每格 anchor 数、匹配 IoU 阈值", "<strong>只有 N</strong>"],
        ]),
        H3("三句话的标准答案骨架"),
        OL([
            "<strong>相同点</strong>：两者在功能上都是<em>「空间假设的载体」</em>——"
            "先摆出一批候选位置，再让网络去修正它们。"
            "<em>DAB-DETR 把 query 显式写成 <code>(x,y,w,h)</code> 之后，"
            "这个同构关系已经变成字面意义上的相同了。</em>",

            "<strong>关键差别一：监督方式</strong>。anchor 是一对多（所以必须 NMS 去重），"
            "query 是一对一（所以训练期就压制了重复）。"
            "<em>这是「需不需要 NMS」的根本原因，也是两者最本质的分野。</em>",

            "<strong>关键差别二：query 之间能通信，anchor 不能</strong>。"
            "self-attention 让 query 可以互相观察、动态分工；"
            "anchor 各自独立，只能靠推理后的 NMS 收拾残局。"
            "<em>加一句：正因为 query 是稀疏的（100 vs 10<sup>5</sup>），"
            "两两通信的 O(N²) 才付得起。</em>",
        ]),
        DUAL(
            "如果面试官继续追问「那 query 到底比 anchor 好在哪」，"
            "<strong>不要说「更好」，要说「换了一组取舍」</strong>："
            "<em>query 换来了「无 NMS、端到端、延迟稳定、少调超参」，"
            "代价是「收敛慢、需要更多数据、小目标弱、失效不可解释」</em>。"
            "<strong>能主动说出代价，比只背优点更能体现工程判断力。</strong>",
            "还有一个更深的观察值得放在结尾："
            "<strong>「一对一」是<em>推理端</em>的需求（要输出一个不含重复的集合），"
            "而不是<em>训练端</em>的最优（一对一提供的监督信号太稀疏）</strong>。"
            "<em>Group DETR / H-DETR / Co-DETR 的做法正是承认了这一点："
            "训练时额外挂一条一对多的分支来加密监督，推理时把它丢掉。</em>"
            "换句话说，检测器的演进不是「从 anchor 走向 query」，"
            "而是<strong>「把训练目标和推理约束解耦」</strong>——"
            "这个视角能把 C53（YOLO/RTMDet 的标签分配）和 C54（DETR 的集合预测）串成一条线。",
        ),
        CALLOUT("danger", "<strong>面试陷阱</strong>：「DETR 是 anchor-free 的吗？」"
                "答「是」会被追问 DAB-DETR，答「不是」又和大众说法冲突。"
                "<strong>正确答法：原始 DETR 没有显式 anchor，"
                "但它的 query 起了同样的空间先验作用；而 DAB-DETR 把 query 显式参数化成 4D anchor box 之后，"
                "DETR 系实际上重新引入了 anchor——只不过是<em>可学习的、稀疏的、逐层精修的、"
                "一对一监督的</em> anchor。</strong>"
                "<em>「anchor-free vs anchor-based」这个二分法本身在 2022 年后已经不再是好的分类维度，"
                "更有信息量的分类维度是「一对一 vs 一对多」。</em>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("Query 的设计是 DETR 系目前<strong>仍在快速变化</strong>的部分。"
          "下面几条是值得持续关注的方向与尚未解决的问题。"),
        UL([
            "<strong>query 的初始化：静态参数 vs 内容感知</strong>。"
            "DINO 的 <em>mixed query selection</em> 用 encoder 的 top-k 提议初始化 query 的<em>位置</em>部分，"
            "但保留 content 部分为可学习参数——<em>因为实验发现用 encoder 特征初始化 content 反而更差</em>"
            "（提议特征还不够精炼，会误导 decoder）。"
            "<strong>「位置该由数据给、内容该由参数给」这个不对称结论目前只有经验解释，缺少理论。</strong>",

            "<strong>query 数量的自适应</strong>。现在 N 是固定超参，"
            "而实际场景的目标数分布方差极大（<em>TSR 里空旷高速 0 块标志，复杂互通 15 块</em>）。"
            "<em>能否让 N 随图像内容动态调整（早退、稀疏化、级联扩展）？</em>"
            "这既是精度问题也是<strong>延迟问题</strong>——固定 N 意味着为最坏情况付费。",

            "<strong>query 与多尺度的关系</strong>。Deformable DETR 让每个 query 在多个尺度上采样，"
            "但<em>「哪个 query 该负责哪个尺度」仍然是隐式学出来的</em>，"
            "不像 FPN 有明确的层级分配规则（<code>k = k₀ + log₂(√(wh)/224)</code>）。"
            "<strong>对小目标为主的 TSR，显式的尺度分配可能仍有价值</strong>（详见 C57 模块 02）。",

            "<strong>self-attention 去重的可解释性与可控性</strong>。"
            "去重行为藏在注意力权重里，<em>既无法在部署时调整，也无法在出问题时定位</em>。"
            "有工作尝试从注意力图里读出「抑制关系图」，但尚无成熟工具。"
            "<strong>这对安全攸关的量产系统是个真实的痛点</strong>——"
            "「为什么这一帧多出一个框」目前没有可审计的答案。",

            "<strong>query 作为跨任务的通用接口</strong>。"
            "Mask2Former 用同一套 query 统一了语义/实例/全景分割，"
            "MOTR / TrackFormer 把 query 延续到下一帧做<em>跟踪</em>"
            "（track query 与 detect query 分工）。"
            "<em>对 TSR 而言这条线特别有吸引力：标志是静止的、自车运动可预测，"
            "「用 query 携带跟踪状态跨帧传播」在理论上比「检测完再关联」更自然</em>（对照 C55 模块 04）。",

            "<strong>开放问题：query 的容量瓶颈</strong>。"
            "DETR 论文的合成实验显示 100 个 query 实际只能稳定检出约 50 个目标。"
            "<em>这个「一半」是从哪来的？是 self-attention 的竞争？是匹配的不稳定？"
            "还是位置嵌入的表达能力？</em> 目前没有令人满意的解释，"
            "而它直接限制了 DETR 系在密集场景（人群、货架、密集车流）的上限。",
        ]),
        CALLOUT("paper", "<p><strong>必读（按顺序）</strong>：</p>"
                "<ul>"
                "<li>★ <em>End-to-End Object Detection with Transformers</em>（DETR, ECCV 2020）——"
                "重点读 §3.2（decoder 结构）、附录 A.3（消融：去掉 self-attention 会出重复框）、"
                "<strong>图 7（query 的空间特化）与图 6（cross-attention 关注物体极值点）</strong>。"
                "<strong>解决什么问题：把检测变成集合预测，并给出 query + 匈牙利匹配这套骨架。</strong></li>"
                "<li>★ <em>Conditional DETR for Fast Training Convergence</em>（ICCV 2021）——"
                "读 §3 的 attention 分解。<strong>解决什么问题：content 与 spatial 纠缠导致收敛慢。</strong></li>"
                "<li>★ <em>DAB-DETR: Dynamic Anchor Boxes are Better Queries for DETR</em>（ICLR 2022）——"
                "读 §3.2 的 modulated positional attention 与 §3.3 的逐层精修。"
                "<strong>解决什么问题：query 缺少尺度先验；顺带把「query 就是 anchor」讲透。</strong></li>"
                "<li><em>Anchor DETR: Query Design for Transformer-Based Detector</em>（AAAI 2022）——"
                "最简洁的「query = 锚点」实现，适合先读它建立直觉。</li>"
                "<li><em>DINO</em>（ICLR 2023）——看 mixed query selection 为何只用位置不用内容。</li>"
                "<li><em>Masked-attention Mask Transformer</em>（Mask2Former, CVPR 2022）——"
                "看 query 如何被推广成通用的分割接口。</li>"
                "</ul>"
                "<p>相邻课程：模块 02（集合损失提供去重的「压力」）、"
                "模块 04（收敛难题与 Deformable/DN/DINO）、模块 05（工程实践与选型）、"
                "C55 模块 04（时序关联，可与 track query 对照）、C57 模块 02（小目标的多尺度架构）。"
                "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · Object query 与交叉注意力（注意力实现 / 职责分工 / 空间特化 / DAB 调制）

目标：把 DETR decoder **从零手写一遍**，并用可证伪的实验回答三个问题——
**query 是什么？self-attention 和 cross-attention 各干什么？query 训练完变成了什么？**

**本 notebook 你会亲手实现：**
1. `attention` / `mha` —— 单头与多头缩放点积注意力（numpy），并证明 `h=1` 时二者等价
2. **decoder 一层**：self-attn + cross-attn + FFN，位置编码只加 Q/K 不加 V
3. **关键扰动实验**：拿掉 self-attention 后，改动 query 5 对其余 query 的输出
   **逐比特没有影响** —— 精确证明「self-attention 是 query 之间唯一的通道」
4. **去重实验**：静态输出 vs 输入条件抑制，量化重复率与召回的变化
5. **query 空间特化**：用匈牙利匹配 + 梯度下降真训练一批 query 先验，
   看它们如何自发分工；再换成 **TSR 风格的偏置分布**，复现「query 特化 = 数据分布的镜像」
6. **DAB-DETR 的宽高调制**：证明正弦位置编码的点积是一个钟形核，
   且把坐标除以 `w` 会精确地把核**拉宽 w 倍**
7. 四道练习：Conditional 分解 / 逐层框精修 / N 的选择 / 注意力有效范围

> 心智模型：**一对一匹配提供「不许重复」的压力，self-attention 提供执行这个压力的通道。
> 缺任何一个，DETR 都得重新装回 NMS。**"""),

    md("""## 1 · 注意力从零实现：单头 → 多头

先把工具造出来。两个必须验证的性质：**每行权重和为 1**、**mask 掉的 key 权重为 0**。"""),
    code("""import numpy as np, math, itertools
np.set_printoptions(precision=4, suppress=True)
rng = np.random.default_rng(0)

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def attention(Q, K, V, mask=None):
    '''缩放点积注意力。Q (nq,d), K (nk,d), V (nk,dv) -> (out (nq,dv), A (nq,nk))'''
    d = Q.shape[-1]
    logits = Q @ K.T / np.sqrt(d)              # 除以 sqrt(d)：防止 d 大时 softmax 饱和
    if mask is not None:
        logits = np.where(mask, logits, -1e9)  # mask=False 的位置被压到 -inf
    A = softmax(logits, -1)
    return A @ V, A

d, nq, nk = 16, 5, 9
Q = rng.normal(size=(nq, d)); K = rng.normal(size=(nk, d)); V = rng.normal(size=(nk, d))
out, A = attention(Q, K, V)
print('out', out.shape, '| A', A.shape)
assert np.allclose(A.sum(-1), 1.0), '每行注意力权重必须和为 1'
assert (A >= 0).all()

# mask：被屏蔽的 key 权重必须是 0（DN-DETR 的去噪分组隔离就靠它，见模块 04）
mask = np.ones((nq, nk), dtype=bool); mask[:, 3:6] = False
_, Am = attention(Q, K, V, mask)
assert Am[:, 3:6].max() < 1e-9, 'mask 掉的 key 权重必须≈0'
assert np.allclose(Am.sum(-1), 1.0)
print('mask 后被屏蔽列的最大权重 = %.2e  ✅' % Am[:, 3:6].max())

# 温度效应：logits 放大 -> 注意力从「弥散」走向「聚焦」
print('\\n%-10s %14s %14s' % ('logits 缩放', '最大权重', '有效关注范围'))
for t in [0.0, 0.5, 1.0, 4.0, 16.0]:
    _, At = attention(Q * t, K, V)
    H = -(At * np.log(At + 1e-12)).sum(-1)
    print('%-10.1f %14.4f %14.2f' % (t, At.max(1).mean(), np.exp(H).mean()))
print('\\n⚠️  t=0（等价于训练刚初始化）时有效关注范围 = %d = 全部 key —— ' % nk)
print('    **每个 key 只分到 1/%d 的梯度**。这就是 DETR 收敛慢的第一个根因（第 3 节展开）。' % nk)"""),
    code("""def mha(Xq, Xk, Xv, W, h):
    '''多头注意力。W = {q,k,v,o} 四个 (d,d) 投影矩阵。返回 (out (nq,d), A (h,nq,nk))'''
    nq, dm = Xq.shape
    nk = Xk.shape[0]
    dh = dm // h
    assert dm % h == 0, 'd_model 必须能被头数整除'
    Qh = (Xq @ W['q']).reshape(nq, h, dh).transpose(1, 0, 2)   # (h, nq, dh)
    Kh = (Xk @ W['k']).reshape(nk, h, dh).transpose(1, 0, 2)
    Vh = (Xv @ W['v']).reshape(nk, h, dh).transpose(1, 0, 2)
    logits = np.einsum('hid,hjd->hij', Qh, Kh) / np.sqrt(dh)   # 注意是除 sqrt(dh) 不是 sqrt(d)
    A = softmax(logits, -1)
    O = np.einsum('hij,hjd->hid', A, Vh).transpose(1, 0, 2).reshape(nq, dm)
    return O @ W['o'], A

W = {k: rng.normal(0, 0.5, (d, d)) for k in 'qkvo'}
Xq = rng.normal(size=(nq, d)); Xk = rng.normal(size=(nk, d))

# h=1 时多头必须退化成「先投影再单头注意力再输出投影」
o1, A1 = mha(Xq, Xk, Xk, W, h=1)
o_ref, A_ref = attention(Xq @ W['q'], Xk @ W['k'], Xk @ W['v'])
assert np.allclose(o1, o_ref @ W['o']), 'h=1 必须与单头等价'
assert np.allclose(A1[0], A_ref)
print('✅ h=1 与单头实现逐元素一致（最大差 %.2e）' % np.abs(o1 - o_ref @ W['o']).max())

# 多头：不同 head 会关注不同的 key —— 这正是 DETR 里「不同 head 负责框的不同边」的机制基础
o4, A4 = mha(Xq, Xk, Xk, W, h=4)
assert A4.shape == (4, nq, nk) and np.allclose(A4.sum(-1), 1.0)
print('\\n每个 head 对 query#0 的 top-1 key:',
      [int(A4[hh, 0].argmax()) for hh in range(4)])
n_distinct = len({int(A4[hh, 0].argmax()) for hh in range(4)})
print('4 个 head 关注了 %d 个不同的 key  ← **多头 = 多个并行的关注模式**' % n_distinct)
assert o4.shape == (nq, d)"""),

    md("""## 2 · Decoder 一层：self-attn + cross-attn + FFN

严格按 DETR 官方实现的连接方式（post-LN）：

- `tgt` 初始化为**全 0**（内容），`query_pos` 是**可学习位置嵌入**
- **位置编码只加到 Q 和 K，绝不加到 V** —— 位置决定「往哪看」，不决定「取回什么」"""),
    code("""def layer_norm(x, eps=1e-5):
    return (x - x.mean(-1, keepdims=True)) / np.sqrt(x.var(-1, keepdims=True) + eps)

def ffn(x, W1, b1, W2, b2):
    return np.maximum(x @ W1 + b1, 0.0) @ W2 + b2

def make_params(d=32, dff=64, h=4, seed=0):
    r = np.random.default_rng(seed)
    def proj():
        return {k: r.normal(0, 1 / np.sqrt(d), (d, d)) for k in 'qkvo'}
    return {'h': h, 'self': proj(), 'cross': proj(),
            'ffn': (r.normal(0, 1 / np.sqrt(d), (d, dff)), np.zeros(dff),
                    r.normal(0, 1 / np.sqrt(dff), (dff, d)), np.zeros(d))}

def decoder_layer(tgt, query_pos, memory, mem_pos, Pm, use_self_attn=True):
    '''返回 (tgt_out, A_self, A_cross)。'''
    A_self = None
    if use_self_attn:
        q = k = tgt + query_pos                                  # pos 进 Q/K
        sa, A_self = mha(q, k, tgt, Pm['self'], Pm['h'])         # **V = tgt，不加 pos**
        tgt = layer_norm(tgt + sa)
    ca, A_cross = mha(tgt + query_pos,                            # Q：query + 位置先验
                      memory + mem_pos,                           # K：图像特征 + 2D 位置编码
                      memory,                                     # **V：纯图像特征**
                      Pm['cross'], Pm['h'])
    tgt = layer_norm(tgt + ca)
    tgt = layer_norm(tgt + ffn(tgt, *Pm['ffn']))
    return tgt, A_self, A_cross

D, H, NQ, HW = 32, 4, 8, 40
Pm = make_params(D, 64, H)
memory   = rng.normal(0, 1, (HW, D))          # encoder 输出（图像证据）
mem_pos  = rng.normal(0, 0.5, (HW, D))        # 2D sine 位置编码（这里用随机向量替代）
query_pos = rng.normal(0, 1, (NQ, D))         # **可学习的 object query**
tgt0 = np.zeros((NQ, D))                      # **内容初始化为全 0**

out1, A_self_demo, A_cross_demo = decoder_layer(tgt0, query_pos, memory, mem_pos, Pm)
print('tgt  ', tgt0.shape, ' -> ', out1.shape)
print('A_self ', A_self_demo.shape, '  (h, N, N)      ← query 之间')
print('A_cross', A_cross_demo.shape, '  (h, N, HW)     ← query -> 图像')
assert np.allclose(A_cross_demo.sum(-1), 1.0) and np.allclose(A_self_demo.sum(-1), 1.0)

# 初始化时 cross-attention 有多「弥散」？
Hc = -(A_cross_demo * np.log(A_cross_demo + 1e-12)).sum(-1)
span0 = float(np.exp(Hc).mean())
print('\\n初始化时 cross-attention 的有效关注范围 = %.1f / %d 个 key（%.0f%%）'
      % (span0, HW, 100 * span0 / HW))
assert span0 > 0.4 * HW, '随机初始化时注意力应远未聚焦'
print('⚠️  真实 DETR 的 HW ≈ 850–1000，初始 span 同样占全部 key 的一半以上 ——')
print('    **每个 key 只分到几百分之一的梯度**，模型要先花几百个 epoch 把注意力收窄。')
print('    Deformable DETR 让每个 query 只采样 K=4 个点，就是直接根治这一条（模块 04）。')

# tgt 全 0 时，第一层 self-attention 的 V 也全 0 -> 输出全 0 -> **第一层 self-attn 几乎无用**
sa_out = mha(tgt0 + query_pos, tgt0 + query_pos, tgt0, Pm['self'], H)[0]
assert np.abs(sa_out).max() < 1e-12
print('\\n✅ 第一层 self-attention 的输出恒为 0（因为 V = tgt = 0）——')
print('   这正好解释了 DETR 论文的消融：**去掉第一层 self-attn，AP 几乎不掉**。')""",),

    md("""## 3 · 关键实验：只有 self-attention 能让 query 之间互相看见

**可证伪的断言**：cross-attention 与 FFN 都是逐 query 独立（pointwise）的运算。
所以拿掉 self-attention 后，改动 query 5 的位置嵌入，
**其余 query 的输出必须逐比特不变**。"""),
    code("""# 第一层 tgt=0 时 self-attn 的 V 也是 0（上一节已证），所以这里模拟**第 2 层及以后**：
# tgt 已经通过 cross-attention 积累了内容。tgt_mid 在整个实验里保持不变。
tgt_mid = rng.normal(0, 1, (NQ, D))

def probe(use_self_attn, victim=5, scale=3.0):
    '''扰动 query[victim] 的位置嵌入，测量其余 query 输出的变化幅度。'''
    base, _, _ = decoder_layer(tgt_mid, query_pos, memory, mem_pos, Pm, use_self_attn)
    qp2 = query_pos.copy()
    qp2[victim] = qp2[victim] + scale * rng2.normal(0, 1, D)
    pert, _, _ = decoder_layer(tgt_mid, qp2, memory, mem_pos, Pm, use_self_attn)
    others = [i for i in range(NQ) if i != victim]
    return (float(np.abs(pert[others] - base[others]).max()),
            float(np.abs(pert[victim] - base[victim]).max()))

rng2 = np.random.default_rng(7)
d_other_no, d_self_no = probe(use_self_attn=False)
rng2 = np.random.default_rng(7)                      # 同一个扰动，保证可比
d_other_sa, d_self_sa = probe(use_self_attn=True)

print('%-26s %22s %20s' % ('decoder 配置', '其余 query 输出变化', '被扰动 query 自己'))
print('%-24s %22.3e %20.4f' % ('❌ 无 self-attention', d_other_no, d_self_no))
print('%-24s %22.3e %20.4f' % ('✅ 有 self-attention', d_other_sa, d_self_sa))

assert d_other_no < 1e-12, '无 self-attn 时，其余 query 的输出必须**逐比特不变**'
assert d_self_no > 1e-3,   '被扰动的 query 自己当然会变'
assert d_other_sa > 1e-3,  '有 self-attn 时，其余 query 必须受影响'
print('\\n✅ **数学证明级别的结论**：')
print('   拿掉 self-attention 后，decoder 就是 %d 条互不相干的流水线 ——' % NQ)
print('   query 之间**没有任何通信通道**，于是两个偏好相近的 query 会输出几乎相同的框，')
print('   而且谁也没办法「知道对方已经认领了」从而退让。→ **重复框，必须外挂 NMS**。')
print('\\n⚠️  面试标准答案：一对一匹配提供「不许重复」的**压力**（模块 02），')
print('    self-attention 提供执行这个压力的**通道**（本节）。**缺一不可。**')"""),

    md("""## 4 · 去重：静态输出 vs 输入条件抑制

上一节证明了「通道」的必要性。这一节量化「有通道」能带来什么：
把 self-attention 学到的行为写成一个显式的**输入条件抑制**（被更自信的邻居压制），
对比它与「各自为战」的重复率和召回。

> 注意：下面的抑制函数是**手写的替身**，用来展示 self-attention *必须学会做什么*；
> 真实 DETR 里这个行为是从一对一匹配的梯度里学出来的，且判据可以远比距离丰富。"""),
    code("""def make_scene(rg, n_query=20):
    '''合成一帧：m 个目标，每个被 2-3 个 query 认领（=重复），其余 query 输出低分背景。'''
    m = int(rg.integers(2, 5))
    gts = rg.uniform(0.10, 0.90, size=(m, 2))
    centers, scores, owner = [], [], []
    for j in range(m):
        for _ in range(int(rg.integers(2, 4))):
            centers.append(gts[j] + rg.normal(0, 0.008, 2))
            scores.append(float(rg.uniform(0.45, 0.95)))
            owner.append(j)
    while len(centers) < n_query:
        centers.append(rg.uniform(0, 1, 2)); scores.append(float(rg.uniform(0.0, 0.25)))
        owner.append(-1)
    return gts, np.array(centers), np.array(scores), np.array(owner)

def self_attn_inhibition(centers, scores, lam=1.0, sigma=0.03):
    '''self-attention 学到的行为：**只被比自己更自信的邻居抑制**（不对称）。'''
    D2 = ((centers[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
    Wk = np.exp(-D2 / (2 * sigma ** 2))          # 距离核（真实模型里是学出来的相似度）
    np.fill_diagonal(Wk, 0.0)
    stronger = (scores[None, :] > scores[:, None]).astype(float)
    inhib = (Wk * stronger * scores[None, :]).max(1)
    return scores - lam * inhib

def evaluate(rg, use_inhibition, n_scene=400, thr=0.30):
    dup, rec = [], []
    for _ in range(n_scene):
        gts, ctr, sc, own = make_scene(rg)
        s = self_attn_inhibition(ctr, sc) if use_inhibition else sc
        keep = s > thr
        fg = own[keep][own[keep] >= 0]
        dup.append(len(fg) - len(set(fg.tolist())))          # 重复框数
        rec.append(len(set(fg.tolist())) / len(gts))         # 召回
    return float(np.mean(dup)), float(np.mean(rec))

dup_no, rec_no = evaluate(np.random.default_rng(3), False)
dup_sa, rec_sa = evaluate(np.random.default_rng(3), True)
print('%-30s %14s %12s' % ('', '每帧重复框数', '召回'))
print('%-28s %14.3f %12.3f' % ('❌ 各自为战（无通信）', dup_no, rec_no))
print('%-28s %14.3f %12.3f' % ('✅ 输入条件抑制（self-attn）', dup_sa, rec_sa))
assert dup_no > 2.0, '没有通信时应有大量重复'
assert dup_sa < 0.2 * dup_no, '抑制后重复框应下降一个数量级'
assert rec_sa > 0.90 * rec_no, '召回不应被显著牺牲'
print('\\n✅ 重复框 %.2f -> %.2f（降低 %.0f%%），召回 %.3f -> %.3f（几乎不变）'
      % (dup_no, dup_sa, 100 * (1 - dup_sa / dup_no), rec_no, rec_sa))
print('\\n⚠️  与 NMS 的关键差别：NMS 的判据**只有 IoU**，且阈值是手调的全局常数。')
print('    self-attention 的判据可以是外观 / 语义 / 上下文 —— 所以它能学会')
print('    「同一根立杆上下两块牌虽然框高度重叠，但是两个物体」，')
print('    而 IoU 阈值在这种 TSR 场景里怎么设都是错的（设高放重复，设低删真目标）。')"""),

    md("""## 5 · Query 的空间特化：用匈牙利匹配真训练一遍

**没有任何损失项要求 query 分工**，但一对一匹配会让它们自发分开：
两个偏好相同的 query 会永远争夺同一批 GT，其中一个必然拿到 ∅ 标签 —— 分开才是损失更低的解。

下面用一个极小的可训练模型复现这个现象：每个 query 只有一个 2D 位置先验 `p_i`，
损失是「匹配上的 (query, GT) 的 L2 距离平方」，用匈牙利匹配 + 梯度下降训练。"""),
    code("""def hungarian(cost):
    '''O(n^3) 匈牙利算法（模块 01/02 已实现，这里直接复用）。要求 n <= m。'''
    C = np.asarray(cost, dtype=float)
    n, m = C.shape
    assert n <= m
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

def scene_uniform(rg):
    '''目标均匀散布在整张图上。'''
    return rg.uniform(0.05, 0.95, size=(int(rg.integers(2, 7)), 2))

def scene_tsr(rg):
    '''**TSR 风格的偏置分布**：竖直方向集中在地平线上方一条窄带，
       水平方向 75% 落在道路右侧（右行 + 立杆在右）。'''
    m = int(rg.integers(1, 5))
    y = rg.normal(0.30, 0.05, m)
    right = rg.random(m) < 0.75
    x = np.where(right, rg.normal(0.80, 0.08, m), rg.normal(0.22, 0.08, m))
    return np.clip(np.stack([x, y], -1), 0.02, 0.98)

def train_query_priors(scene_fn, n_query=12, steps=800, lr=0.08, seed=0):
    '''每个 query 一个 2D 位置先验；一对一匹配 + SGD。'''
    rg = np.random.default_rng(seed)
    Pq = rg.uniform(0.45, 0.55, size=(n_query, 2))      # 初始：**全挤在画面中央**
    hits = np.zeros(n_query)
    for _ in range(steps):
        gts = scene_fn(rg)
        C = ((Pq[:, None, :] - gts[None, :, :]) ** 2).sum(-1)     # (N, M)
        r, c = hungarian(C.T)                                      # 行=GT，列=query
        for gi, qi in zip(r, c):
            Pq[qi] -= lr * 2.0 * (Pq[qi] - gts[gi])                # d/dp ||p-g||^2
            hits[qi] += 1
        Pq = np.clip(Pq, 0.02, 0.98)
    return Pq, hits

def coverage(Pq, scene_fn, seed=99, n=400):
    '''平均「GT 到最近 query 先验」的距离 —— 越小说明 query 覆盖越好。'''
    rg = np.random.default_rng(seed); tot = []
    for _ in range(n):
        g = scene_fn(rg)
        tot.append(np.sqrt(((g[:, None, :] - Pq[None, :, :]) ** 2).sum(-1)).min(1).mean())
    return float(np.mean(tot))

P_init = np.random.default_rng(0).uniform(0.45, 0.55, size=(12, 2))
P_uni, hits_uni = train_query_priors(scene_uniform)
c0, c1 = coverage(P_init, scene_uniform), coverage(P_uni, scene_uniform)
print('均匀分布数据：覆盖距离 %.4f（训练前，全挤在中央） -> %.4f（训练后）' % (c0, c1))
assert c1 < 0.6 * c0, '训练后 query 应显著铺开'
print('\\n训练后 12 个 query 的位置先验（x, y）与被认领次数：')
for i in np.argsort(-hits_uni):
    print('  query %2d  (%.3f, %.3f)   认领 %4d 次' % (i, P_uni[i, 0], P_uni[i, 1], hits_uni[i]))
spread = P_uni.std(0)
assert (spread > 0.15).all(), 'query 在两个方向上都应该铺开'
print('\\n✅ **没有任何损失项要求它们分工，但它们自发分开了**（std = %.3f, %.3f）。'
      % (spread[0], spread[1]))
print('   机理：两个偏好相同的 query 会永远争同一批 GT，输的那个拿 ∅ 标签 —— 分开才更优。')"""),
    code("""# 换成 **TSR 风格的偏置分布**：看 query 特化如何变成「数据分布的镜像」
P_tsr, hits_tsr = train_query_priors(scene_tsr, seed=1)
active = hits_tsr >= 20
print('被有效训练到的 query: %d / %d' % (active.sum(), len(hits_tsr)))
print('\\n%-10s %10s %10s %10s' % ('query', 'x（左右）', 'y（上下）', '认领次数'))
for i in np.argsort(-hits_tsr):
    tag = ''
    if hits_tsr[i] >= 20:
        tag = '  ← 右侧带' if P_tsr[i, 0] > 0.5 else '  ← 左侧带'
    print('%-10d %10.3f %10.3f %10d%s' % (i, P_tsr[i, 0], P_tsr[i, 1], hits_tsr[i], tag))

ya = P_tsr[active, 1]; xa = P_tsr[active, 0]
print('\\n有效 query 的 y 均值 = %.3f（数据集中在 0.30 附近）' % ya.mean())
print('有效 query 中落在右半边的比例 = %.2f（数据里 75%% 的标志在右侧）'
      % (xa > 0.5).mean())
assert ya.mean() < 0.45, 'query 应集中到「地平线上方」那条窄带'
assert (xa > 0.5).mean() >= 0.5, '多数 query 应特化到道路右侧'
cov_tsr = coverage(P_tsr, scene_tsr)
print('TSR 分布上的覆盖距离 = %.4f' % cov_tsr)

# **关键的失效实验**：把这批 query 直接拿去跑「左行国家 / 城市道路」分布
def scene_shifted(rg):
    '''分布外场景：标志出现在画面左侧、且位置更低（城市道路 / 左行）。'''
    m = int(rg.integers(1, 5))
    y = rg.normal(0.55, 0.08, m)
    x = np.where(rg.random(m) < 0.75, rg.normal(0.22, 0.08, m), rg.normal(0.80, 0.08, m))
    return np.clip(np.stack([x, y], -1), 0.02, 0.98)

cov_ood = coverage(P_tsr, scene_shifted)
print('\\n分布外（左行 / 城市道路）上的覆盖距离 = %.4f  ← 恶化 %.1f 倍'
      % (cov_ood, cov_ood / cov_tsr))
assert cov_ood > 2.0 * cov_tsr, '分布外场景上 query 覆盖应显著变差'
print('\\n⚠️  **这是一个离线 mAP 看不出、实车上会成片掉召回的失效模式**：')
print('    query 的特化是数据分布的镜像；没被训练覆盖的区域没有任何 query 负责。')
print('✅ 对策：① 评测按「标志在画面中的位置」分桶（C55 模块 05）；')
print('        ② 数据要覆盖各类道路几何（匝道 / 环岛 / 城市 / 龙门架）；')
print('        ③ **慎用水平翻转增强** —— 它能补左侧分布，但会把「左转」翻成「右转」、')
print('           把牌面文字镜像（C56 模块 01 的语义禁区）。主动指出这一点是面试加分项。')"""),

    md("""## 6 · DAB-DETR：为什么「除以 w」就等于把注意力窗口拉宽 w 倍

正弦位置编码有一个漂亮的性质：**两点位置编码的点积只依赖于它们的距离**，
并且是一个以 0 为峰的钟形核：

$$\\mathrm{PE}(x)^\\top \\mathrm{PE}(x') = \\sum_j \\cos\\big(\\omega_j (x-x')\\big)$$

所以把坐标除以 `w`，就等于把这个核在空间上**精确地拉宽 w 倍** —— 这就是 DAB-DETR
用 anchor 的宽高调制位置注意力的全部原理。"""),
    code("""def sinusoidal_pe(x, d=128, temperature=20.0):
    '''DETR 风格的 1D 正弦位置编码。x: (n,) -> (n, d)'''
    i = np.arange(d // 2)
    omega = 1.0 / (temperature ** (2 * i / d))
    ang = x[:, None] * omega[None, :] * 2 * np.pi
    return np.concatenate([np.sin(ang), np.cos(ang)], -1)

# 性质 1：点积只依赖距离（平移不变）
def pe_dot(x, y):
    return float(sinusoidal_pe(np.array([x]))[0] @ sinusoidal_pe(np.array([y]))[0])

a, b = 0.31, 0.77
lhs, rhs = pe_dot(a, b), pe_dot(0.0, b - a)
assert abs(lhs - rhs) < 1e-9, 'PE(a)·PE(b) 必须只依赖 b-a'
print('PE(%.2f)·PE(%.2f) = %.4f ;  PE(0)·PE(%.2f) = %.4f   ✅ 平移不变'
      % (a, b, lhs, b - a, rhs))

def pe_kernel(deltas, w=1.0, d=128, T=20.0):
    '''把坐标除以 w 之后的位置注意力核 k(delta)。'''
    K0 = sinusoidal_pe(np.array([0.0]) / w, d, T)[0]
    return sinusoidal_pe(deltas / w, d, T) @ K0

def half_width(deltas, ker):
    '''核降到峰值一半时的 delta —— 即「注意力窗口的半宽」。'''
    below = np.where(ker < ker[0] / 2.0)[0]
    return float(deltas[below[0]]) if len(below) else float('nan')

deltas = np.linspace(0, 1.2, 2401)
print('\\n%-14s %12s %14s' % ('anchor 宽度 w', '核峰值', '注意力半宽'))
hw = {}
for w in [0.25, 0.5, 1.0, 2.0]:
    ker = pe_kernel(deltas, w)
    hw[w] = half_width(deltas, ker)
    print('%-14.2f %12.1f %14.4f' % (w, ker[0], hw[w]))

for w in [0.25, 0.5, 2.0]:
    ratio = hw[w] / hw[1.0]
    assert abs(ratio - w) < 0.05 * w, 'w=%.2f 时半宽比应≈%.2f，实得 %.3f' % (w, w, ratio)
print('\\n✅ 半宽与 w **精确成正比**（误差 < 5%）——')
print('   宽目标得到宽窗口，8x8 的远处限速牌得到窄窗口。')

# 画一下核的形状（ASCII）
print('\\n位置注意力核 k(delta) 的形状（w=0.5 窄 vs w=2.0 宽）：')
for w, mark in [(0.5, '#'), (2.0, '=')]:
    ker = pe_kernel(deltas, w)
    line = ''.join(mark if ker[int(t / 1.2 * 2400)] > ker[0] / 2 else '.'
                   for t in np.linspace(0, 1.19, 60))
    print('  w=%.1f |%s|  半宽=%.3f' % (w, line, hw[w]))
print('        0%s1.2   (delta)' % (' ' * 57))
print('\\n⚠️  Conditional DETR 的空间项是**各向同性**的固定圆斑；')
print('    DAB-DETR 用 (w, h) 分别调制 x / y 两个方向 —— 于是窗口能变成扁的、长的、小的。')
print('✅ 顺带的第二个红利：既然 query 就是一个 (x,y,w,h) 的框，它就能被**逐层精修**')
print('   （练习 2），这与模块 02 的辅助损失是天生一对。')"""),

    md("""## 7 · Query 数量 N 的账：覆盖率 / 正样本比例 / 计算量"""),
    code("""counts_coco = rng.poisson(7.7, 40000)      # COCO 风格：单图平均 7.7 个实例
counts_tsr  = rng.poisson(1.8, 40000)      # **TSR 风格：一张高速前视图通常 1-5 块标志**

for name, cnt in [('COCO 风格', counts_coco), ('TSR 风格', counts_tsr)]:
    print('%-10s mean=%.2f  p99=%d  max=%d' % (name, cnt.mean(),
                                               np.percentile(cnt, 99), cnt.max()))
print('\\n%-6s %10s %12s %14s %16s %16s'
      % ('N', '覆盖率(TSR)', '覆盖率(COCO)', '正样本比例(TSR)', 'self-attn O(N^2)', '匹配 O(M^2 N)'))
rows = []
for N in [10, 30, 100, 300, 900]:
    cov_t = float((counts_tsr <= N).mean()); cov_c = float((counts_coco <= N).mean())
    pos_t = counts_tsr.mean() / N
    rows.append((N, cov_t, cov_c, pos_t))
    print('%-6d %10.5f %12.5f %14.4f %16.1e %16.1e'
          % (N, cov_t, cov_c, pos_t, N * N, (counts_coco.mean() ** 2) * N))

covs_t = [r[1] for r in rows]; poss = [r[3] for r in rows]
assert all(covs_t[i] <= covs_t[i + 1] for i in range(len(covs_t) - 1)), '覆盖率随 N 单调不减'
assert all(poss[i] > poss[i + 1] for i in range(len(poss) - 1)), '正样本比例随 N 单调下降'
assert rows[2][1] > 0.9999, 'TSR 场景 N=100 早已 100% 覆盖'

print('\\n⚠️  常见误解：「DINO 用 900 个 query 是为了检更多目标」—— **不是**。')
print('    本合成分布单图最多 %d 个实例（真实 COCO 是 63），100 早就够了（覆盖率 %.5f）。'
      % (counts_coco.max(), rows[2][2]))
print('    提到 300/900 的真实动机是 **加密监督信号、加快收敛**，代价是正样本比例暴跌，')
print('    所以必须同时把 softmax CE 换成 sigmoid focal loss（模块 02 第 8 节）。')
print('\\n✅ **TSR 场景的推理**：目标数分布 mean=%.2f、max=%d，N=100 覆盖率已是 %.5f。'
      % (counts_tsr.mean(), counts_tsr.max(), rows[2][1]))
print('   继续加到 900 不会提升召回，只会把正样本比例从 %.2f%% 压到 %.2f%%。'
      % (100 * rows[2][3], 100 * rows[4][3]))
print('   但也不该砍到 20：① DETR 论文的合成实验显示 query 的**实际可用容量只有名义值的一半**；')
print('   ② N 太小会加剧 query 之间的竞争与匹配不稳定；③ N=100 的 self-attn 开销本就可忽略。')
print('   → **N 取 50-100 是合理区间**（练习 3 把这个推理写成决策脚本）。')"""),

    md("""## ✏️ 练习 1：Conditional DETR 的「内容项 + 空间项」分解

原始 DETR 把位置编码**相加**进 Q/K，展开后会多出两个交叉项
`c_q·p_k` 和 `p_q·c_k` —— 内容与位置互相污染。
Conditional DETR 改成只保留 `c_q·c_k + p_q·p_k`。

实现 `conditional_logits(cq, ck, pq, pk)`：返回 `(nq, nk)` 的 attention logits
`= (cq·ck + pq·pk) / sqrt(d_c + d_p)`。"""),
    code("""def conditional_logits(cq, ck, pq, pk):
    # TODO: 内容项与空间项各自点积后相加，再除以 sqrt(总维度)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
d16 = 16
cq = rng.normal(size=(6, d16)); ck = rng.normal(size=(20, d16))
pq = rng.normal(size=(6, d16)); pk = rng.normal(size=(20, d16))
L = conditional_logits(cq, ck, pq, pk)
assert L.shape == (6, 20)

# 性质 1：等价于把 [content; spatial] **拼接**后做一次点积
cat_q = np.concatenate([cq, pq], -1); cat_k = np.concatenate([ck, pk], -1)
assert np.allclose(L, cat_q @ cat_k.T / np.sqrt(2 * d16)), '分解 == 拼接后单次点积'

# 性质 2：原始 DETR 的「相加」会引入两个交叉项，且量级与正题相当（= 严重污染）
wanted = cq @ ck.T + pq @ pk.T
cross  = cq @ pk.T + pq @ ck.T
assert np.allclose((cq + pq) @ (ck + pk).T, wanted + cross)
ratio = float(np.abs(cross).mean() / np.abs(wanted).mean())
print('交叉项 / 正题 的平均幅值比 = %.2f  ← **交叉项一点都不小**' % ratio)
assert ratio > 0.5

# 性质 3：内容项置零时，空间项能把注意力精确拉到参考点上
grid = np.linspace(0, 1, 64)
pk_s = sinusoidal_pe(grid, d=128); refs = np.array([0.20, 0.50, 0.85])
pq_s = sinusoidal_pe(refs, d=128)
A_s = softmax(conditional_logits(np.zeros((3, 128)), np.zeros((64, 128)), pq_s, pk_s), -1)
peaks = grid[A_s.argmax(1)]
print('参考点 %s -> 注意力峰值位置 %s' % (refs, np.round(peaks, 3)))
assert np.abs(peaks - refs).max() < 0.05, '空间项应把注意力拉到参考点'
print('✅ 练习 1 通过：**把「看哪里」和「找什么」拆开**，是 Conditional DETR 收敛快 6.7x 的核心。')"""),

    md("""## ✏️ 练习 2：DAB/DINO 的逐层框精修（iterative box refinement）

框被约束在 `[0,1]`，所以增量要加在 **inverse-sigmoid 空间**里再映射回来：
`b_{l+1} = sigmoid(inverse_sigmoid(b_l) + Δ_l)`。

实现 `inverse_sigmoid` 与 `apply_delta`。要求：**零增量必须是恒等变换**。"""),
    code("""def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

def inverse_sigmoid(x, eps=1e-5):
    # TODO: sigmoid 的反函数；先把 x clip 到 [eps, 1-eps] 防 log(0)
    raise NotImplementedError

def apply_delta(box, delta):
    # TODO: 在 inverse-sigmoid 空间累加增量，再 sigmoid 回 [0,1]
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
def iou_cxcywh(a, b):
    ax1, ay1, ax2, ay2 = a[0]-a[2]/2, a[1]-a[3]/2, a[0]+a[2]/2, a[1]+a[3]/2
    bx1, by1, bx2, by2 = b[0]-b[2]/2, b[1]-b[3]/2, b[0]+b[2]/2, b[1]+b[3]/2
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    I = iw * ih
    return I / (a[2] * a[3] + b[2] * b[3] - I + 1e-12)

z = np.array([-2.0, 0.0, 3.0])
assert np.allclose(inverse_sigmoid(sigmoid(z)), z, atol=1e-4)
box = np.array([0.40, 0.50, 0.20, 0.20])
assert np.allclose(apply_delta(box, np.zeros(4)), box, atol=1e-5), '零增量必须是恒等变换'

# 模拟 6 层 decoder 的逐层精修（每层把 logit 空间的残差消掉 60%）
gt = np.array([0.78, 0.30, 0.05, 0.05])      # 一块远处的小标志
b = box.copy(); ious = []
print('%-8s %28s %10s' % ('decoder 层', 'anchor (cx, cy, w, h)', 'IoU'))
for l in range(7):
    ious.append(iou_cxcywh(b, gt))
    print('%-8s %28s %10.4f'
          % ('anchor' if l == 0 else 'L%d' % l, np.round(b, 4), ious[-1]))
    if l < 6:
        b = apply_delta(b, 0.6 * (inverse_sigmoid(gt) - inverse_sigmoid(b)))

assert ious[0] == 0.0, '初始 anchor 与 GT 不相交 —— IoU 恒为 0（模块 02 的梯度死区！）'
assert all(ious[i] <= ious[i + 1] + 1e-12 for i in range(len(ious) - 1)), 'IoU 应单调不降'
assert ious[-1] > 0.85
print('\\n✅ 练习 2 通过：**query 一旦被解释成框，就能被逐层精修** ——')
print('   这与模块 02 的辅助损失（每层都要输出可用的框）是天生一对，')
print('   也是 RT-DETR「同一份权重支持多档速度」的结构基础（跑前 k 层即可）。')
print('⚠️  注意前两层 IoU 恒为 0（框还不相交）—— 此时 GIoU 才是唯一有梯度的项。')"""),

    md("""## ✏️ 练习 3：给定目标数分布，选一个 N

实现 `choose_num_queries(counts, candidates, target_coverage=0.9999)`：
- `rows`：每个候选 N 一条 `(N, coverage, pos_ratio, selfattn_cost)`
  （`coverage = P(M <= N)`，`pos_ratio = E[M]/N`，`selfattn_cost = N*N`）
- `recommend`：**满足覆盖率要求的最小 N**；若都不满足则取最大候选"""),
    code("""def choose_num_queries(counts, candidates, target_coverage=0.9999):
    # TODO: 返回 dict(rows=[...], recommend=N)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
CANDS = [10, 20, 50, 100, 300, 900]
r_tsr = choose_num_queries(counts_tsr, CANDS)
r_coco = choose_num_queries(counts_coco, CANDS)
print('%-6s %12s %14s %14s' % ('N', '覆盖率', '正样本比例', 'self-attn'))
for N, cov, pos, cost in r_tsr['rows']:
    print('%-6d %12.5f %14.4f %14.0f' % (N, cov, pos, cost))
print('\\nTSR  分布推荐 N =', r_tsr['recommend'])
print('COCO 分布推荐 N =', r_coco['recommend'])

covs = [r[1] for r in r_tsr['rows']]
poss = [r[2] for r in r_tsr['rows']]
assert all(covs[i] <= covs[i + 1] for i in range(len(covs) - 1)), '覆盖率随 N 单调不减'
assert all(poss[i] > poss[i + 1] for i in range(len(poss) - 1)), '正样本比例随 N 单调下降'
assert r_tsr['recommend'] <= 20, 'TSR 分布下 N=20 已足够覆盖'
assert r_coco['recommend'] > r_tsr['recommend'], 'COCO 目标更多，需要更大的 N'
# 极端情况：候选都不够时退化为最大候选
assert choose_num_queries(counts_coco, [2, 3])['recommend'] == 3
print('\\n✅ 练习 3 通过：**覆盖率只是下界**。实际取 N 还要考虑：')
print('   ① query 的实际可用容量只有名义值的一半（DETR 论文的 100 目标合成实验）；')
print('   ② N 太小加剧竞争与匹配不稳定；③ N 太大压低正样本比例、逼你换 focal loss。')
print('   → 工程上的合理做法：**从 p99.99 目标数出发，乘 2-4 倍安全系数，再向上取整到常用档位**。')"""),

    md("""## ✏️ 练习 4：注意力的「有效关注范围」——DETR 收敛慢的量化诊断

定义 `effective_span(A) = exp(H(A))`，`H` 是每行注意力分布的熵。
它的含义是「这一行实际上在看多少个 key」：均匀分布 → `K`，one-hot → `1`。

实现 `attn_entropy(A)` 与 `effective_span(A)`（支持任意前置维度，最后一维是 key）。"""),
    code("""def attn_entropy(A):
    # TODO: 沿最后一维算熵，注意 log(0) 保护
    raise NotImplementedError

def effective_span(A):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
Kk = 850                                   # 800x1066 输入 / stride 32 的典型 key 数
A_uni = np.full((4, Kk), 1.0 / Kk)
assert np.allclose(effective_span(A_uni), Kk), '均匀分布的有效范围 = K'
A_one = np.zeros((4, Kk)); A_one[:, 3] = 1.0
assert np.allclose(effective_span(A_one), 1.0, atol=1e-6), 'one-hot 的有效范围 = 1'

logits = rng.normal(size=(4, Kk))
print('%-14s %16s %14s' % ('logits 缩放', '有效关注范围', '占全部 key'))
spans = []
for t in [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]:
    s = float(effective_span(softmax(logits * t, -1)).mean())
    spans.append(s)
    print('%-14.1f %16.1f %13.1f%%' % (t, s, 100 * s / Kk))
assert spans[0] > 0.99 * Kk, 't=0（等价随机初始化）时应几乎均匀'
assert all(spans[i] > spans[i + 1] for i in range(len(spans) - 1)), '越尖越小'

# 用第 2 节真实跑出来的 cross-attention 量一下
span_real = float(effective_span(A_cross_demo.reshape(-1, A_cross_demo.shape[-1])).mean())
print('\\n第 2 节 decoder 初始化时的 cross-attn 有效范围 = %.1f / %d 个 key（%.0f%%）'
      % (span_real, HW, 100 * span_real / HW))
assert span_real > 0.4 * HW
print('\\n✅ 练习 4 通过：**这是 DETR 需要 500 epoch 的第一个根因的量化指标**。')
print('   初始 span ≈ K ≈ 1000 -> 每个 key 只分到千分之一的梯度；')
print('   模型必须先花掉大量 epoch 把注意力「收窄」，才谈得上学定位。')
print('⚠️  训练时把这个指标画出来：**如果它长期不下降，说明 cross-attention 没在聚焦**，')
print('   继续调学习率是没用的 —— 要换结构（可变形注意力 / 空间先验），见模块 04。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def conditional_logits(cq, ck, pq, pk):
    d_total = cq.shape[-1] + pq.shape[-1]
    return (cq @ ck.T + pq @ pk.T) / np.sqrt(d_total)"""),
    code("""# 练习 2 参考答案
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

def inverse_sigmoid(x, eps=1e-5):
    x = np.clip(np.asarray(x, dtype=float), eps, 1.0 - eps)
    return np.log(x / (1.0 - x))

def apply_delta(box, delta):
    return sigmoid(inverse_sigmoid(box) + np.asarray(delta, dtype=float))"""),
    code("""# 练习 3 参考答案
def choose_num_queries(counts, candidates, target_coverage=0.9999):
    counts = np.asarray(counts)
    rows, rec = [], None
    for N in sorted(candidates):
        cov = float((counts <= N).mean())
        rows.append((N, cov, float(counts.mean() / N), float(N * N)))
        if rec is None and cov >= target_coverage:
            rec = N
    return {'rows': rows, 'recommend': rec if rec is not None else max(candidates)}"""),
    code("""# 练习 4 参考答案
def attn_entropy(A):
    A = np.asarray(A, dtype=float)
    return -(A * np.log(A + 1e-12)).sum(-1)

def effective_span(A):
    return np.exp(attn_entropy(A))"""),

    md("""---
## 🧪 真实工程胶囊：DETR decoder 的配置、调试与常见 bug"""),
    code("""RECIPE = r'''
# ============ Object query / decoder：工程 checklist（PyTorch 伪代码 + 真实参数） ============

# ---- 1. query 的定义（DETR 官方 models/detr.py） ----
self.query_embed = nn.Embedding(num_queries, hidden_dim)     # 100 x 256，**可学习参数**
tgt = torch.zeros_like(query_embed)                          # **内容初始化为全 0**
# 注意：query_embed 与图像无关，在所有图上共享 —> 它编码的是「搜索策略」，不是「某个物体」

# ---- 2. decoder 一层（位置编码的加法规则，**记死**） ----
def forward(tgt, memory, pos, query_pos):
    q = k = tgt + query_pos                                  # self-attn: pos 进 Q/K
    tgt = tgt + self.self_attn(q, k, value=tgt)[0]           # **value 不加 pos**
    tgt = self.norm1(tgt)
    tgt = tgt + self.cross_attn(query=tgt + query_pos,       # cross-attn: pos 进 Q
                                key=memory + pos,            #             pos 进 K
                                value=memory)[0]             # **value 不加 pos**
    tgt = self.norm2(tgt)
    tgt = self.norm3(tgt + self.ffn(tgt))
    return tgt
# 规则：位置编码进 Q 和 K，**永远不进 V**。看到实现把 pos 加进 V，基本可判定是 bug。

# ---- 3. 典型超参 ----
NUM_QUERIES  = 100      # DETR;  300 (Deformable/DAB);  900 (DINO)
D_MODEL      = 256
NHEADS       = 8
DEC_LAYERS   = 6        # 每层都算辅助损失（模块 02）
PRE_NORM     = False    # DETR 用 post-LN；部分变体用 pre-LN（更稳但需调 lr）

# ---- 4. DAB-DETR 风格的 anchor query（把 query 显式写成 4D 框） ----
self.refpoint_embed = nn.Embedding(num_queries, 4)           # (x, y, w, h)，sigmoid 前
ref = self.refpoint_embed.weight.sigmoid()                   # -> [0,1]^4
query_pos = gen_sineembed_for_position(ref[..., :2])         # 位置编码由 (x,y) 生成
pos_x = pos_x * (ref_w_h[..., 0] / obj_w).unsqueeze(-1)      # **用 w/h 调制注意力窗口宽度**
# 逐层精修：
new_ref = (inverse_sigmoid(ref) + self.bbox_head[l](tgt)).sigmoid()
# **梯度要 detach 上一层的 ref**（不然会跨层耦合出不稳定），DINO 的 look-forward-twice 改了这点

# ---- 5. 四个必看的调试信号 ----
# [A] cross-attention 热力图: A[h, i].reshape(H, W) —— query 有没有找到目标？
#     TSR 里如果 query 关注的是杆件而不是牌面 -> 特征分辨率不够，该加 P2 / 多尺度
# [B] **重复率**: 同一 GT 附近出现 >=2 个高分预测的比例。长期不降 =>
#     query 太少 / 匹配不稳定 / self-attn 被错误 mask
# [C] **query 使用直方图**: 每个 query 被匹配的次数。出现大量「死 query」=>
#     N 偏大，或数据分布过窄（query 特化到了训练集的偏置上）
# [D] **effective span** = exp(H(attn)): 长期 ≈ K 说明 cross-attn 没在聚焦 -> 换结构

# ---- 6. 五个常见 bug ----
# [ ] 把 query_pos 加进了 value（位置污染内容）
# [ ] tgt 用随机初始化而不是 0（DETR 官方是 0；随机初始化会破坏「第一层无需 self-attn」的性质）
# [ ] 改了 num_queries 却没改推理端的 top-k -> 直接改变召回上限
# [ ] N 从 100 提到 900 却仍用 softmax CE + eos_coef -> 背景项失控，必须换 sigmoid focal
# [ ] 逐层精修时忘了 detach 上一层的 reference -> 训练发散
'''
print(RECIPE)
for key in ['nn.Embedding(num_queries, hidden_dim)', 'torch.zeros_like',
            'value=tgt', 'value=memory', 'refpoint_embed', 'inverse_sigmoid',
            'effective span', 'sigmoid focal']:
    assert key in RECIPE, key
print('✅ 配方覆盖：query 定义 / pos 加法规则 / 超参 / DAB anchor / 4 个调试信号 / 5 个常见 bug')"""),

    md("""### 小结

- **query 不是特征，是可学习的位置嵌入**（`nn.Embedding(100, 256)`），与图像无关、跨图共享。
  内容 `tgt` 初始化为**全 0**，靠 cross-attention 逐层灌进图像证据。
  **位置编码只进 Q/K，永远不进 V。**
- **职责分工是理解 DETR 的钥匙**：cross-attention 是 image→query 的唯一通道（取证据），
  self-attention 是 query↔query 的唯一通道（协商去重）。
  本 notebook 用扰动实验精确证明了：**拿掉 self-attn，decoder 就是 N 条互不相干的流水线**
  （改动 query 5，其余 query 输出逐比特不变）。
- **「DETR 为什么不需要 NMS」的完整答案 = 压力 + 通道**：一对一匹配在训练期制造
  「重复必被惩罚」的压力（模块 02），self-attention 提供执行这个压力的通道（本模块）。
  只答前者会被追问穿。
- **query 的空间特化是自发涌现的，且是数据分布的镜像**。在 TSR 偏置分布上训练后，
  query 会集中到「地平线上方 + 道路右侧」；换到左行/城市道路，覆盖距离恶化 2 倍以上——
  **这是离线 mAP 看不出、实车成片掉召回的失效模式**。评测必须按画面位置分桶。
- **N 的选择**：必须 > 单图最大目标数，且实际可用容量只有名义值的一半。
  把 N 提到 300/900 的动机是**加密监督、加快收敛**，不是「检更多目标」；
  代价是正样本比例暴跌，必须同步换 focal loss。**TSR 场景 50–100 足够。**
- **DAB-DETR 的调制原理**：正弦位置编码的点积是只依赖距离的钟形核，
  把坐标除以 `w` 就精确地把核**拉宽 w 倍** —— 宽目标宽窗口，小标志窄窗口。
  query 一旦成为 4D 框，就能被逐层精修，与辅助损失天生一对。
- **query vs anchor**：功能同构（都是空间假设的载体），
  本质差别只有两条——**一对一 vs 一对多监督**（决定要不要 NMS），
  以及**query 之间能通信、anchor 不能**。
  「anchor-free vs anchor-based」已不是好的分类维度，**「一对一 vs 一对多」才是**。

下一站：**模块 04 · 收敛难题与 DETR 家族演进** —— 500 epoch 到底慢在哪，
Deformable / DN / DINO 各自砍掉了哪一刀。"""),
]
