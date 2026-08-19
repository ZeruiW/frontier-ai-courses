# -*- coding: utf-8 -*-
"""C53 模块 04 · RT-DETR 解剖：DETR 如何跑赢 YOLO。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（YOLO 演进 / 重参数化）、模块 02（标签分配）、模块 03（RTMDet）；C54 的匈牙利匹配可先不看"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_rtdetr.ipynb（纯 numpy，实测 NMS 耗时曲线）'),
    ("核心参考", "RT-DETR (CVPR 2024) · RT-DETRv2 · D-FINE (ICLR 2025) · Deformable DETR · VarifocalNet"),
    ("预计时长", "读 75 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("nms-variance", "动机：NMS 不是「慢」，是「不确定」", "".join([
        P("先把一个常见的误解拆掉。<strong>RT-DETR 的卖点不是「去掉 NMS 所以平均更快」——平均省下的那 1–3 ms 并不惊人。真正的卖点是：它把一个<em>依赖输入数据</em>的耗时项变成了常数</strong>。这对一个要过功能安全审查的车端系统来说，是量变到质变的差别。"),
        P("把一个实时检测器的单帧延迟拆开看："),
        MATH("T_{\\text{e2e}} \\;=\\; \\underbrace{T_{\\text{pre}} + T_{\\text{H2D}} + T_{\\text{infer}} + T_{\\text{decode}} + T_{\\text{D2H}}}_{\\text{给定模型与分辨率后是常数}} \\;+\\; \\underbrace{T_{\\text{NMS}}(N, K)}_{\\text{依赖这一帧里有什么}}"),
        P("前面那一堆都是常数：卷积做多少次乘加，跟图里有 2 个目标还是 200 个目标毫无关系。<strong>只有 NMS 这一项，耗时是「这一帧的内容」的函数</strong>。$N$ 是过了 score 阈值的候选框数，$K$ 是最终保留数。朴素 NMS 的代价是："),
        MATH("T_{\\text{NMS}} \\;\\approx\\; c_1 \\, N\\log N \\;+\\; c_2 \\sum_{j=1}^{K}\\Bigl(N - (j-1)\\bar{m}\\Bigr) \\;=\\; O\\!\\left(N K\\right)"),
        P("排序是 $N\\log N$，抑制循环是「每保留一个框，就要和剩下所有框比一次 IoU」。$\\bar m$ 是每轮平均抑制掉的框数。<strong>关键在于 $N$ 和 $K$ 都随场景复杂度增长，所以 NMS 的耗时是<em>超线性</em>的</strong>——notebook 里会实测出 log-log 斜率约 1.7，也就是目标数翻 10 倍，NMS 耗时涨约 50 倍。"),
        H3("两个超参把精度和速度死死绑在一起"),
        TABLE(["超参", "调低会怎样", "调高会怎样", "为什么这是个陷阱"], [
            ["<code>score_thr</code>", "$N$ 暴涨 → NMS 变慢；但低分的小目标能保住 → 召回涨", "$N$ 骤减 → NMS 变快；但低分目标全丢 → 召回掉", "<strong>你没法独立地调精度和延迟</strong>。想提召回就得接受延迟涨"],
            ["<code>iou_thr</code>", "抑制更狠 → $K$ 变小、更快；但密集排列的相邻目标会被误删", "抑制更松 → $K$ 变大、更慢；重复框留下来", "密集场景（连续限速牌）逼你调高，而密集场景恰恰是 $N$ 最大的时候"],
        ]),
        DUAL(
            "直觉上「NMS 就 1 ms 而已，能有多大事」。问题在于这 1 ms 是<em>平均值</em>。同一个模型、同一块芯片，在高速公路上视野里只有 2 块标志时 NMS 可能只要 0.2 ms；开到城市路口，龙门架 + 多块限速牌 + 一整排店铺招牌 + 一辆贴满贴纸的货车，过阈候选框从 200 涨到 4000，NMS 就要 4 ms。<strong>延迟的尖峰恰好出现在场景最复杂、最需要及时反应的时候</strong>——这个「反相关」才是致命的。",
            "更严谨的说法：NMS 让检测模块的 <span class=\"term\">WCET</span>（worst-case execution time，最坏执行时间）<strong>无法静态确定</strong>。实时系统的调度分析要求每个任务有可界定的 WCET；一个耗时依赖输入数据、且没有硬上界的模块，只能按经验上的最坏值预留时隙。于是两件坏事同时发生：<em>①平均算力被大量浪费</em>（多数帧只用掉预留时隙的一半）；<em>②仍然无法证明不会超时</em>（因为「最坏」是估出来的，不是推出来的）。RT-DETR 把 $T_{\\text{NMS}}$ 项直接删掉，$T_{\\text{e2e}}$ 变成常数，WCET 就成了一个可以写进设计文档的数字。",
        ),
        CALLOUT("danger", "<p>面试高频翻车点。被问「RT-DETR 为什么快」时，只答「因为没有 NMS」会立刻被追问「省了多少毫秒？那 YOLO 加个 GPU NMS 不就行了？」——然后你就答不上来了。<strong>正确的答法是把「快」和「稳」拆开</strong>：<em>①论文口径下 NMS 大约占 1–3 ms，对一个 9 ms 的模型是 10–30%，这部分确实可以靠 GPU NMS / EfficientNMS plugin 压缩；②但压不掉的是<u>方差</u>——NMS 的耗时是场景的函数，p99 与 p50 的差距无法通过换实现消除，只能通过限制候选框数上限来「截断」，而截断的代价是密集场景漏检</em>。<strong>面试官想听的就是你知道「延迟均值」和「延迟分布」是两件事</strong>。</p>", "只说「没有 NMS」= 没答到点上"),
        CALLOUT("intuition", "把本节压成一句话：<strong>NMS 让「这一帧有多难」变成了「这一帧要跑多久」。实时安全系统不能接受这种耦合。</strong>"),
    ])),

    # ============================================================== 2
    ("overview", "RT-DETR 全景：四个部件与它们各自解决的问题", "".join([
        P("<span class=\"term\">RT-DETR</span>（Real-Time DEtection TRansformer，百度，CVPR 2024，论文标题就叫 <em>DETRs Beat YOLOs on Real-time Object Detection</em>）是第一个在<strong>同等延迟下</strong> COCO AP 超过同期 YOLO 的 DETR 系检测器。R50 版本在 T4 + TensorRT FP16 + batch=1 下约 <strong>53.1 AP / 108 FPS</strong>，R101 约 54.3 AP / 74 FPS。"),
        ASCII("""输入 640×640
   │
   ▼
┌─ Backbone (ResNet-50 / HGNetv2) ───────────────────────────────┐
│   S3  80×80×512   (stride  8)   ← 细节多、语义弱、token 最多    │
│   S4  40×40×1024  (stride 16)                                  │
│   S5  20×20×2048  (stride 32)   ← 语义强、分辨率低、token 最少  │
└────────────────────────────────────────────────────────────────┘
   │  1×1 conv 全部降到 d=256
   ▼
┌─ Efficient Hybrid Encoder ─────────────────────────────────────┐
│                                                                │
│   ┌─ AIFI ─────────────────────────────┐                       │
│   │  **只对 S5** 做 self-attention      │  400 个 token        │
│   │  尺度**内**的全局语义交互           │  代价可以忽略        │
│   └────────────────┬───────────────────┘                       │
│                    ▼ F5                                        │
│   ┌─ CCFF ─────────────────────────────┐                       │
│   │  S3 ↕ S4 ↕ F5  的 PAN 式融合        │  **全是卷积**        │
│   │  fusion block = 1×1 + N×RepBlock    │  代价线性于 token 数 │
│   └────────────────┬───────────────────┘                       │
└────────────────────┼───────────────────────────────────────────┘
                     ▼  8400 个位置，每个都有 (类别分数, 框)
┌─ Uncertainty-minimal Query Selection ──────────────────────────┐
│   按「分类置信 **与** 定位质量一致」的分数取 top-300           │
│   → 300 个 decoder query 的初始内容 + 初始参考框               │
└────────────────────┬───────────────────────────────────────────┘
                     ▼
┌─ Decoder × 6 ──────────────────────────────────────────────────┐
│   每层 = self-attn(query 之间去重) + 可变形 cross-attn + FFN    │
│   **每层都有自己的预测头 + 辅助损失**                          │
│   → 推理时可以只跑前 k 层  ← 「一份权重多档速度」的机制所在    │
└────────────────────┬───────────────────────────────────────────┘
                     ▼
        300 个框 + 类别        **没有 NMS，直接输出**"""),
        P("四个部件，四个问题，一一对应："),
        TABLE(["部件", "解决什么问题", "不用它会怎样", "本课在哪节展开"], [
            ["<strong>AIFI</strong>", "DETR 系的 encoder 太贵（Deformable DETR 的 encoder 占了大头）", "把三尺度拼成 8400 长的序列做 attention，二次项直接爆炸", "第 3 节"],
            ["<strong>CCFF</strong>", "跨尺度融合必须做，但不能用 attention 做", "小目标掉点（S3 拿不到高层语义）或延迟爆炸", "第 4 节"],
            ["<strong>Query selection</strong>", "decoder 的初始参考框质量决定了它要花几层才能收敛", "选到「分类自信但框很差」的位置，可变形采样一开始就采不到目标", "第 5 节"],
            ["<strong>逐层辅助头</strong>", "部署时要多档速度，但不想训多个模型", "每档速度训一次，$N$ 份权重、$N$ 套评测、$N$ 份 engine", "第 6 节"],
        ]),
        DUAL(
            "从 YOLO 视角看，RT-DETR 的 backbone + hybrid encoder 其实<strong>就是一个 YOLO</strong>：CNN 主干 + PAN 颈部，只不过在最高层插了一个 self-attention 块。真正不一样的只有后半段——YOLO 在颈部输出上直接密集预测再 NMS，RT-DETR 挑 300 个位置送进 decoder 做稀疏细化。<em>所以「RT-DETR 是 DETR 还是 YOLO」这个问题的答案是：前半段是 YOLO，后半段是 DETR。</em>",
            "更精确地说，RT-DETR 的谱系是 <span class=\"term\">Deformable DETR</span> 的 two-stage 变体 → <span class=\"term\">DINO</span> → RT-DETR，它继承了：多尺度可变形注意力（decoder 的 cross-attention）、two-stage 的 encoder 提议机制（query selection）、逐层辅助损失（deep supervision）、以及一对一匈牙利匹配（因此无需 NMS）。<strong>它砍掉的是 Deformable DETR 的重型 encoder</strong>——原版 encoder 要在所有尺度的 8400 个 token 上跑 6 层可变形 self-attention，RT-DETR 把它换成「1 层 S5 attention + 一个卷积 PAN」，这是延迟下降的最大来源。",
        ),
        CALLOUT("warn", "别把 RT-DETR 的 encoder 和「Transformer encoder」画等号。<strong>RT-DETR 的 encoder 里 95% 以上的计算量是卷积</strong>（notebook 会算给你看：AIFI 约 0.4 GMACs，CCFF 约 5 GMACs）。「hybrid」这个词是字面意思，不是修辞。<em>如果你在面试里把 hybrid encoder 描述成「一个高效的 Transformer 编码器」，说明你没看懂它的取舍。</em>"),
    ])),

    # ============================================================== 3
    ("aifi", "AIFI：为什么 self-attention 只放在 S5", "".join([
        P("<span class=\"term\">AIFI</span>（Attention-based Intra-scale Feature Interaction，基于注意力的尺度<em>内</em>特征交互）是 RT-DETR 最容易被复述、也最容易被复述错的设计。它就是一层标准的 Transformer encoder block（multi-head self-attention + FFN），<strong>但只作用在 backbone 的最高层 S5 上</strong>。理由有两条，一条是算账，一条是语义。"),
        H3("① 算账：token 数的平方"),
        P("640×640 输入下三个尺度的 token 数是 $80^2=6400$、$40^2=1600$、$20^2=400$。self-attention 的代价里有一个 $O((HW)^2 d)$ 的二次项，于是："),
        TABLE(["做法", "token 数", "self-attention MACs（d=256，含 QKVO 投影）", "相对 AIFI"], [
            ["三尺度拼成一条序列做全局 attention", "8400", "<strong>38.3 GMACs</strong>", "<strong>205×</strong>"],
            ["三尺度各自做 attention 再融合", "6400 + 1600 + 400", "24.6 GMACs", "131×"],
            ["只在 S4 做", "1600", "1.73 GMACs", "9.3×"],
            ["<strong>只在 S5 做（= AIFI）</strong>", "<strong>400</strong>", "<strong>0.187 GMACs</strong>", "<strong>1×</strong>"],
        ]),
        P("<strong>205 倍</strong>。这个数字值得背下来，因为它一句话解释了「为什么 Deformable DETR 的 encoder 那么贵，而 RT-DETR 的不贵」。而 0.187 GMACs 是什么概念？一个 ResNet-50 backbone 在 640 输入下大约是 20–25 GMACs，AIFI 连它的 1% 都不到——<em>基本是白送的</em>。"),
        H3("② 语义：低层特征做全局交互没有意义"),
        P("论文给的理由是：<strong>高层特征包含关于「实体」的丰富语义概念，对它们做全局交互能建立起目标之间的关系；而低层特征缺乏语义概念，对它们做尺度内交互既冗余，又容易与高层特征的交互结果重复、互相混淆</strong>。论文的消融也支持这一点——把 attention 从 S5 挪到 S3/S4 或加到所有尺度，AP 不涨反而略降，同时延迟大幅增加。"),
        DUAL(
            "换个说法：S5 上一个 token 对应原图 32×32 的区域，400 个 token 就是整张图的一个粗粒度摘要。在这个粒度上做 self-attention，模型问的是「画面左边那个东西和右边那个东西是什么关系」——<strong>这是全局语义问题，attention 正好擅长</strong>。而 S3 上一个 token 只对应 8×8 像素，让 6400 个这样的小块两两算相关性，问的是「这个 8×8 的纹理块和那个 8×8 的纹理块像不像」——<em>这既不是模型需要的信息，也是卷积用几层堆叠就能覆盖的局部关系</em>。",
            "从<span class=\"term\">有效感受野</span>（effective receptive field）的角度看更清楚：stride 32 的特征图上，一个 3×3 卷积核已经覆盖原图 96×96；再堆几层，理论感受野就接近全图，只是有效感受野仍然是高斯衰减的。<strong>self-attention 在这里补的正是「有效感受野的尾部」——把衰减掉的远距离依赖直接拉成 $O(1)$ 的连接</strong>。而在 stride 8 上，卷积的有效感受野本来就远小于目标间距，attention 补上去的是一堆低信噪比的相关性，还要付 40 倍的代价（$6400^2 / 400^2 \\cdot$ 修正 ≈ 121 倍的二次项）。这也解释了模块 03 里 RTMDet 用 5×5 depthwise 大核的思路是同一个问题的另一种答案：<em>都是在给高层特征扩有效感受野，只是一个用注意力、一个用大核</em>。",
        ),
        CALLOUT("intuition", "一条可迁移的心法：<strong>attention 放在 token 少的地方，卷积放在 token 多的地方。</strong>这不是 RT-DETR 独有的洞察——MobileViT、EfficientViT、EdgeNeXt、以及几乎所有成功的 CNN-Transformer 混合架构，都是这个结构。<em>下一节会给出这条心法的精确交叉点。</em>"),
        CALLOUT("warn", "<p><strong>TSR 场景的重要澄清：AIFI 对小目标几乎没有直接帮助。</strong>640 输入下 S5 是 20×20，一个 token 覆盖原图 32×32 像素。一个 80 米外的限速牌在 1920×1080 相机上大约 15–20 像素，缩到 640 输入后只剩 5–7 像素——<em>它在 S5 上连一个 token 都占不满，早就被下采样抹掉了</em>。所以在 TSR 里，AIFI 贡献的是「这是城市路口还是高速公路」这类场景级先验；<strong>小标志的检出能力来自 S3、CCFF 的自顶向下语义注入、以及 decoder 的可变形采样</strong>。面试里如果有人说「RT-DETR 用了 attention 所以小目标好」，那是没算过账。</p>", "AIFI ≠ 小目标解法"),
    ])),

    # ============================================================== 4
    ("ccff", "CCFF：跨尺度融合为什么必须交给卷积", "".join([
        P("<span class=\"term\">CCFF</span>（CNN-based Cross-scale Feature Fusion，基于卷积的跨尺度特征融合）承担的是另一半工作：把 AIFI 处理过的 F5 与原始的 S3、S4 融合起来。拓扑上它就是一个 <span class=\"term\">PAN</span>（自顶向下 + 自底向上双路径），每条融合边上放一个 <strong>fusion block</strong>："),
        CODE("""fusion block（RT-DETR）
  输入 (C=256)
    ├─ 1×1 conv  → hidden=128 ──┐
    └─ 1×1 conv  → hidden=128 ──┤
                                ├─ N × RepBlock(3×3, 128→128)   ← 训练多分支、推理单分支
                                │      （重参数化，见模块 01）
    ┌───────────────────────────┘
    └─ concat / add → 1×1 conv → 256"""),
        H3("交叉点在哪：一个可以手算的判据"),
        P("把 self-attention 和一个 3×3 卷积（同为 $d\\to d$ 通道）的乘加次数写出来，就能算出「多少个 token 以下 attention 更便宜」："),
        MATH("\\underbrace{2(HW)^2 d + 4\\,HW\\,d^2}_{\\text{self-attention：}QK^\\top,\\ \\text{attn}\\cdot V,\\ QKVO\\ \\text{投影}} \\;<\\; \\underbrace{9\\,HW\\,d^2}_{3\\times3\\ \\text{conv}} \\quad\\Longleftrightarrow\\quad HW \\;<\\; \\tfrac{5}{2}\\,d"),
        P("代入 $d=256$：交叉点是 <strong>640 个 token，约 25×25 的特征图</strong>。于是三个尺度的归属一目了然（notebook 会逐项验证，包括 $HW=640$ 时两边<em>严格相等</em>）："),
        TABLE(["层级", "token 数", "self-attention", "3×3 conv", "谁更便宜", "RT-DETR 的选择"], [
            ["S5 (20×20)", "400", "0.187 GMACs", "0.236 GMACs", "<strong>attention</strong>（0.79×）", "<strong>AIFI</strong> ✅"],
            ["S4 (40×40)", "1600", "1.730 GMACs", "0.944 GMACs", "conv（attention 是 1.83×）", "CCFF ✅"],
            ["S3 (80×80)", "6400", "22.65 GMACs", "3.775 GMACs", "conv（attention 是 6.0×）", "CCFF ✅"],
        ]),
        P("<strong>这不是拍脑袋的设计，是算出来的。</strong>640 输入 + $d=256$ 这组配置下，交叉点恰好落在 S5 和 S4 之间——AIFI 只在 S5 做，正是这个不等式的直接结论。"),
        DUAL(
            "跨尺度融合到底在做什么？两件事：<em>①把高层的语义往下送</em>（S3 知道「这里有个 8 像素的红色圆形块」，但不知道它是限速牌还是车尾灯，这个判断要 S5 的上下文）；<em>②把低层的定位精度往上送</em>（S5 知道「这附近有个限速牌」，但它的 token 粒度是 32 像素，框不准）。<strong>这两件事的本质都是「把对应位置的信息对齐后相加」——是一个局部的、有明确空间对应关系的操作，卷积的归纳偏置正好合适</strong>，用 attention 去学「哪个位置对应哪个位置」纯属浪费。",
            "反事实算一笔：如果把 S3→S4 这条融合边换成 cross-attention（6400 个 query 对全部 8400 个 key），代价是 $2\\times 6400\\times 8400\\times 256 \\approx 27.5$ GMACs。而同一条边用 fusion block（1×1 降到 128 + 3 个 RepBlock + 1×1 升回）只要约 <strong>3.25 GMACs</strong>——<strong>卷积版便宜 8.5 倍，而且解决的是同一个问题</strong>。整个 CCFF 加起来约 5 GMACs，AIFI 约 0.4 GMACs，hybrid encoder 总共约 5.5 GMACs。<em>对照 Deformable DETR 的 encoder（六层多尺度可变形 attention，几十 GMACs 起步），这就是 RT-DETR 能跑到 108 FPS 的结构性原因。</em>",
        ),
        CALLOUT("intuition", "RepBlock 在这里出现不是巧合。模块 01 讲的<strong>结构重参数化</strong>让 CCFF 在训练时是多分支（表达力强、梯度好），推理时融合成单个 3×3 卷积（延迟低、对 TensorRT 友好）。<em>「训练期换表达力、推理期换延迟」这条思路在 RT-DETR 里被用到了两个地方：CCFF 的 RepBlock，和下一节要讲的逐层辅助头。</em>"),
    ])),

    # ============================================================== 5
    ("query-selection", "IoU-aware / uncertainty-minimal query selection", "".join([
        P("这一节讲的东西最抽象，但它是 RT-DETR 相对于「一个装了 attention 的 YOLO」真正多出来的智力。"),
        H3("query selection 是什么"),
        P("DETR 原版的 <span class=\"term\">object query</span> 是纯学出来的嵌入向量，与图像内容无关，所以 decoder 第一层要从零开始猜「目标在哪」。<span class=\"term\">two-stage</span> 的做法（Deformable DETR / DINO / RT-DETR）是：让 encoder 输出的每个位置都过一个轻量检测头，得到 8400 组 (类别分数, 框)，<strong>然后挑 top-300 作为 decoder query 的初始内容特征和初始参考框</strong>。这相当于给 decoder 一个热启动。"),
        P("问题出在「怎么挑」。"),
        H3("按分类分数挑，会挑到定位很差的位置"),
        DUAL(
            "分类头和回归头是两个独立分支，训练时<strong>没有任何机制强制它们一致</strong>。分类分数回答的是「这里像不像一个限速牌」，回归输出回答的是「框应该画在哪」。<em>一个位置完全可以在语义上非常像限速牌（分类 0.95），但因为它落在标志的边缘，回归出来的框和真值 IoU 只有 0.25</em>。按分类分数排序取 top-300，就会大量选中这种「自信但框歪」的位置。",
            "为什么这比「框不准」更严重？因为 decoder 的 cross-attention 是<strong>可变形注意力</strong>——它只在参考框附近采样 $K$ 个点取特征，不是对全图做 attention。<em>参考框歪了，采样点就落在目标外面，decoder 拿到的证据里根本没有目标</em>。假设参考框与真值面积相当、IoU 为 $u$，则参考框内落在真值上的面积比例是 $2u/(1+u)$：$u=0.8$ 时是 0.89（采样点基本都命中），$u=0.25$ 时只有 0.40（六成采样点是背景），$u<0.2$ 时基本等于让 decoder 从零重新定位——<strong>而这正是它最不擅长的事，因为 decoder 只有 6 层</strong>。",
        ),
        H3("两种修法：IoU-aware 与 uncertainty-minimal"),
        P("RT-DETR 论文的 arXiv 早期版本叫 <strong>IoU-aware query selection</strong>，CVPR 正式版改称 <strong>uncertainty-minimal query selection</strong>。两者是同一件事的两种表述，面试里都可能被问到，建议都能说："),
        TABLE(["表述", "机制", "损失形式", "直觉"], [
            ["<strong>IoU-aware</strong>", "训练时把正样本的<em>分类目标</em>从 1 改成「预测框与 GT 的 IoU」（<span class=\"term\">VarifocalNet</span> / <span class=\"term\">TOOD</span> 的 task-alignment 思路）", "$\\mathcal{L}_{\\text{cls}}$ 用 IoU 作软标签（VFL）", "让分数同时编码「像不像」和「准不准」，于是按分数排序 = 按联合质量排序"],
            ["<strong>uncertainty-minimal</strong>", "把定位分支 $\\mathcal{P}$ 与分类分支 $\\mathcal{C}$ 对同一特征的判断差异定义为不确定性，显式最小化它", "见下方公式", "不是「让分类去追 IoU」，而是「让两个头互相校准」——对齐是目标本身"],
        ]),
        MATH("\\mathcal{U}(\\hat{X}) \\;=\\; \\bigl\\lVert\\, \\mathcal{P}(\\hat{X}) \\;-\\; \\mathcal{C}(\\hat{X}) \\,\\bigr\\rVert \\,, \\qquad \\mathcal{L}(\\hat{X},\\hat{Y},Y) \\;=\\; \\mathcal{L}_{\\text{box}}(\\hat{b}, b) \\;+\\; \\mathcal{L}_{\\text{cls}}\\bigl(\\mathcal{U}(\\hat{X}),\\, \\hat{c},\\, c\\bigr)"),
        P("效果（notebook 会用一组可控相关性的合成数据复现）：把两个头的一致性从 $\\rho\\approx0.35$ 提到 $\\rho\\approx0.90$，选出来的 query 的<strong>平均初始 IoU 从 0.50 涨到 0.77</strong>，「IoU ≥ 0.5 的 query 占比」从 48% 涨到 99.8%，「IoU < 0.2 的灾难性 query」从 4.2% 降到 0，可变形采样点的命中率从 64% 涨到 87%。论文报告这一项单独带来约 <strong>+0.8 AP</strong>，并且收敛更快。"),
        CALLOUT("warn", "<p><strong>TSR 的两难，也是一个很好的追问预案。</strong>小目标的 IoU 天生低——一个 8×8 像素的框沿对角线位移 2 像素，IoU 就从 1.0 掉到 <strong>0.39</strong>（交 6×6=36，并 64+64−36=92）。IoU-aware 训练会把这类位置的分类目标压到 0.39 附近，<em>于是小目标的 query 分数系统性地低于大目标</em>，在全局 top-300 里更容易落选。<strong>结果是：一个为「分数与 IoU 对齐」而设计的机制，反过来加剧了小目标的正样本稀缺。</strong>实践上的对策是按特征层级分配 query 配额（S3 保底多少个）、或用尺度归一化的定位质量度量（如 C57 会讲的 NWD）替代裸 IoU。<em>能在面试里主动提出这个副作用，比背对公式有价值得多。</em></p>", "IoU-aware 在小目标上的副作用"),
        CALLOUT("intuition", "把本节浓缩：<strong>query selection 的质量 = decoder 的起跑线。起跑线歪了，6 层 decoder 也拉不回来，因为可变形注意力只在参考框附近取证据。</strong>"),
    ])),

    # ============================================================== 6
    ("decoder-scaling", "一份权重，多档速度：decoder 层数可调", "".join([
        P("这是 RT-DETR 在<strong>部署工程上</strong>最被低估、也最好用的性质，而且它几乎是白送的。"),
        H3("机制：每一层 decoder 都有自己的预测头"),
        P("DETR 家族从初代起就用 <span class=\"term\">auxiliary loss</span>（辅助损失 / deep supervision）：decoder 的每一层输出后都接一个（共享参数的）预测头，每层都独立做一次匈牙利匹配并计算完整的集合损失。这本来是为了加速收敛——<em>让梯度能直接到达浅层，而不用穿过 6 层 attention</em>。"),
        P("但它顺带带来一个副产品：<strong>第 $k$ 层的输出本身就是一个完整、可用、已经被训练过的检测结果。</strong>于是推理时你可以只跑前 $k$ 层，直接拿第 $k$ 层的头的输出，<em>不需要重训、不需要改训练代码、不需要重新标数据</em>——只需要重新导出一次 ONNX 并重建 engine。"),
        ASCII("""训练（6 层全跑，每层都算损失）
  query₀ ─► L1 ─► L2 ─► L3 ─► L4 ─► L5 ─► L6
             │     │     │     │     │     │
            头₁   头₂   头₃   头₄   头₅   头₆
             ▼     ▼     ▼     ▼     ▼     ▼
            loss  loss  loss  loss  loss  loss     ← 6 次匈牙利匹配 + 集合损失

推理（按目标平台裁到 k 层）
  低配 SoC :  query₀ ─► L1 ─► L2 ─► L3 ─┤ 头₃ → 输出      ~8.4 ms
  中配     :  query₀ ─► L1 ─► ... ─► L4 ─┤ 头₄ → 输出      ~8.7 ms
  高配     :  query₀ ─► L1 ─► ... ─► L6 ─┤ 头₆ → 输出      ~9.3 ms
              └────────── 完全同一份权重文件 ──────────┘"""),
        TABLE(["decoder 层数", "AP（示意）", "延迟 ms（示意）", "相对 6 层的 AP 代价", "每多一层换来的 AP/ms"], [
            ["1", "44.9", "7.8", "−8.2", "—"],
            ["2", "50.5", "8.1", "−2.6", "<strong>18.7</strong>"],
            ["3", "52.1", "8.4", "−1.0", "5.3"],
            ["4", "52.8", "8.7", "−0.3", "2.3"],
            ["5", "53.0", "9.0", "−0.1", "0.7"],
            ["6", "<strong>53.1</strong>", "9.3", "0", "0.3"],
        ]),
        P("（表中数字是教学用示意值，量级与论文消融一致：<strong>边际收益急剧递减，砍掉最后两层几乎不掉点</strong>。）三个直接可用的结论："),
        UL([
            "<strong>去掉最后 2 层，AP 掉 0.3、延迟省 0.6 ms（约 6%）</strong>。多数量产场景会毫不犹豫地做这个交换。",
            "<strong>前 2 层贡献了绝大部分精度</strong>（44.9 → 50.5，+5.6 AP）。这反过来说明 query selection 给的起跑线确实好——第 1 层就已经有 44.9 AP。",
            "<strong>延迟随层数几乎线性</strong>（每层约 0.3 ms），因为每层的计算量固定（300 个 query，与场景无关）——这又回到第 1 节：<em>RT-DETR 的整条链路上没有任何一项依赖输入数据</em>。",
        ]),
        DUAL(
            "YOLO 系做不到这件事。YOLO 只有一个检测头挂在颈部末端，砍掉网络的一部分就没有对应的头，输出直接无效。<strong>所以 YOLO 要提供多档速度，只能训 n/s/m/l/x 五个不同宽深的模型</strong>——五套训练、五套超参、五份评测报告、五份权重、五份 engine，而且它们的行为特性各不相同（同一个 badcase 在 s 上和在 l 上可能表现完全不同，调试时要分别复现）。<em>RT-DETR 是一次训练 → 六档速度，且六档共享完全相同的 backbone/encoder 行为。</em>",
            "对一家同时要在高中低三配 SoC 上出货的车企，这个差别是<strong>组织层面</strong>的而不只是技术层面的：一份权重意味着一条数据管线、一次训练预算、一套 badcase 归因、一份模型卡、一次安全评审的模型证据链。<em>更进一步，还可以做<strong>运行时自适应</strong></em>——TSR 只是感知任务之一，当同一颗 SoC 上的其他任务（BEV 检测、占用栅格、车道线）负载升高时，调度器可以临时把 TSR 的 decoder 从 6 层降到 3 层，用 1 个 AP 换 1 ms。<strong>这类「精度可降级」的能力在功能安全设计里是加分项，因为它给了系统一个优雅降级路径而不是直接丢帧。</strong>",
        ),
        CALLOUT("danger", "<p><strong>面试陷阱：「那我直接训一个 3 层 decoder 的模型，不是更好吗？」</strong>不要不假思索地说「一样」。诚实的答法是：<em>①从<u>部署灵活性</u>看，6 层训练 + 截断严格更优，因为一份权重覆盖所有档位，而专门训的 3 层模型只覆盖一档；②从<u>该档精度</u>看，理论上深监督下的浅层可能优于同深度独立训练的模型（浅层同时受到来自后续层的表示压力），但这<strong>依赖具体配置，必须自己做消融验证</strong>，不能当作定论去背</em>。<strong>面试官想听的是你区分得开「工程上确定成立的收益」和「听起来合理但需要验证的假设」</strong>——把后者说成前者是减分的。</p>", "别把「合理猜想」说成「已知结论」"),
    ])),

    # ============================================================== 7
    ("family", "RT-DETR 家族与横向取舍", "".join([
        P("RT-DETR 之后这条线走得很快，面试里问「你知道后续工作吗」是常见的深度探针。"),
        TABLE(["工作", "年份", "核心改动", "为什么重要"], [
            ["<strong>RT-DETR</strong>", "CVPR 2024", "hybrid encoder（AIFI + CCFF）+ uncertainty-minimal query selection + 层数可调", "第一个在同延迟下 AP 超过 YOLO 的 DETR"],
            ["<strong>RT-DETRv2</strong>", "2024", "① <strong>离散采样算子</strong>替代 <code>grid_sample</code>；② 每尺度独立的采样点数；③ 动态数据增强 + 尺度自适应超参", "<strong>①是纯部署动机</strong>：<code>grid_sample</code> 在部分推理后端要写 plugin，换成离散采样后导出即用，代价是极小的 AP 损失"],
            ["<strong>D-FINE</strong>", "ICLR 2025", "① <strong>FDR</strong>：把框回归从「回归 4 个数」改成「逐层细化四条边的概率分布」；② <strong>GO-LSD</strong>：把末层的定位分布自蒸馏回浅层", "定位精度显著提升（L 约 54.0 AP、X 约 55.8 AP），且<strong>浅层自蒸馏让截断到少层时掉点更少</strong>——与上一节的多档速度是互补的"],
            ["<strong>DEIM</strong>", "CVPR 2025", "Dense O2O（训练时用密集一对一增加正样本）+ MAL（matchability-aware loss）", "针对 DETR 系「监督信号稀疏 → 收敛慢」的根因，训练成本大幅下降"],
            ["<strong>YOLOv10</strong>", "NeurIPS 2024", "一致的双分配（consistent dual assignments）：训练时一对多 + 一对一双头，推理只留一对一", "<strong>说明「无 NMS」不是 DETR 的专利</strong>——CNN 密集预测器也能做到，只是路径不同"],
        ]),
        CALLOUT("intuition", "<strong>YOLOv10 这一行是面试里的高价值信息。</strong>它证明了「端到端 / 无 NMS」和「Transformer 架构」是<em>两件正交的事</em>：无 NMS 来自<strong>一对一标签分配</strong>（训练期就压制重复），跟你用 CNN 还是 attention 无关。<em>能把这两件事拆开讲，说明你理解的是机制而不是模型名字。</em>"),
        H3("RT-DETR vs YOLO/RTMDet：一张取舍表"),
        TABLE(["维度", "RT-DETR 系", "YOLO / RTMDet 系", "谁赢"], [
            ["同延迟 AP（COCO，中大模型段）", "略优", "略劣", "RT-DETR"],
            ["<strong>延迟稳定性（p99 − p50）</strong>", "<strong>≈ 0（无数据依赖项）</strong>", "受 NMS 影响，密集场景显著抬升", "<strong>RT-DETR（差距最大的一项）</strong>"],
            ["极小模型段（&lt; 4 ms）", "decoder 与 query selection 的固定开销占比高", "结构更纯，缩到很小仍高效", "YOLO/RTMDet"],
            ["<strong>小目标 AP</strong>", "依赖 S3 与可变形采样；query 数固定是天花板", "密集预测天然覆盖每个位置，加 P2 直接见效", "<strong>看配置，YOLO 系更容易调</strong>"],
            ["收敛成本 / 数据需求", "较高（DETR 系通病，DEIM 等在改善）", "低，配方成熟", "YOLO/RTMDet"],
            ["部署算子友好度", "可变形注意力 / <code>grid_sample</code> 可能要 plugin（v2 已改善）", "全是标准卷积算子", "YOLO/RTMDet"],
            ["<strong>一份权重多档速度</strong>", "<strong>原生支持</strong>", "需训多个尺寸", "<strong>RT-DETR</strong>"],
            ["INT8 量化友好度", "attention 与 softmax 对量化更敏感，常需混合精度", "卷积为主，PTQ 通常够用", "YOLO/RTMDet"],
            ["调试与归因", "端到端匹配，失败原因更难定位到具体环节", "密集预测 + NMS，每一步都可单独 dump", "YOLO/RTMDet"],
        ]),
        DUAL(
            "所以选型不是「谁更强」，而是「<strong>你的约束里哪一栏是硬的</strong>」。如果硬约束是 p99 延迟必须可静态界定（安全相关任务、共享 SoC 上要排期）——选 RT-DETR 系。如果硬约束是极小算力 + 8–20 像素的远处标志 + 工具链必须零 plugin——选 RTMDet/YOLO 加高分辨率输入与 P2 层。",
            "而<strong>量产 TSR 系统的现实形态往往是混合的</strong>：一个类别无关（或粗类）的高分辨率小目标检测器负责「哪里有牌子」，后接一个高分辨率 crop 分类器负责「是什么牌子」（这是 C55 模块 02 的主题）。<em>在这种两级架构里，第一级的类别数很少（1–5 类），NMS 的 $N$ 天然小得多，YOLO 系的延迟方差问题被大幅削弱</em>；而第二级的延迟正比于检出个数，又引入了新的数据依赖项。<strong>换句话说：架构选择会改变「延迟不确定性」的位置，但不会自动消灭它——你要做的是把它挪到一个可以设硬上限的地方。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("interview", "面试标准答案骨架", "".join([
        P("这一节请当作可背诵材料。每题给<strong>面试官想听什么</strong>、<strong>30 秒骨架</strong>、<strong>加分点</strong>、<strong>踩雷点</strong>。骨架的组织原则是：<em>先给判断，再给机制，最后给数字和代价</em>。"),
        H3("Q1 · RT-DETR 凭什么能跑赢 YOLO？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你能不能把「快」拆成「计算量更省」和「延迟更稳」两件独立的事，并各自说清机制"],
            ["<strong>30 秒骨架</strong>", "「四点。<strong>①无 NMS</strong>——一对一匈牙利匹配在训练期就压重复，推理端删掉了唯一一个耗时依赖场景的模块，端到端延迟变成常数。<strong>②efficient hybrid encoder</strong>——self-attention 只在 S5 的 400 个 token 上做（AIFI），跨尺度融合全交给卷积（CCFF）；如果三尺度拼成 8400 token 做全局 attention，光二次项就贵 205 倍。<strong>③uncertainty-minimal query selection</strong>——按「分类与定位一致」的分数选 300 个 query，给 decoder 一个准的起跑线，因为可变形注意力只在参考框附近采样，起跑线歪了后面救不回来。<strong>④decoder 层数可调</strong>——每层都有辅助头，推理时截断到 k 层即可，一份权重出多档速度。」"],
            ["加分点", "主动补一句「而且无 NMS 不是 DETR 专利，YOLOv10 用一致双分配也做到了——本质是<strong>一对一标签分配</strong>，跟架构无关」"],
            ["<strong>踩雷点</strong>", "只说「去掉了 NMS 所以快」；把 hybrid encoder 说成「一个高效 Transformer 编码器」（它 90%+ 是卷积）"],
        ]),
        H3("Q2 · 为什么 AIFI 只在最高层做 self-attention？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你算过账，而且知道另有一个语义层面的理由"],
            ["<strong>30 秒骨架</strong>", "「两个理由。<strong>算账</strong>：attention 的代价含 $O((HW)^2 d)$ 项，640 输入下 S3/S4/S5 是 6400/1600/400 token，三尺度拼一起做全局 attention 是只在 S5 做的 205 倍；把 attention 和 3×3 卷积的乘加数写出来解不等式，交叉点是 $HW = 2.5d$，$d=256$ 时是 640 token，S5 的 400 刚好在下面、S4 的 1600 在上面。<strong>语义</strong>：高层特征才有『实体』级的语义概念，全局交互才有意义；低层特征做尺度内 attention 既冗余又会和高层的交互结果互相混淆，论文消融里 AP 不涨反降。」"],
            ["加分点", "「一条可迁移的心法是：<strong>attention 放 token 少的地方，卷积放 token 多的地方</strong>，MobileViT/EfficientViT 都是这个结构。」"],
            ["<strong>踩雷点</strong>", "说「因为 S5 语义强所以效果好」但给不出计算量的数量级；反过来说「AIFI 帮助小目标」（S5 一个 token 覆盖 32×32 像素，小标志早被抹掉了）"],
        ]),
        H3("Q3 · 为什么不能按分类分数选 query？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你知道分类与定位不对齐是个通用问题（不只在 DETR 里），并且知道后果为什么严重"],
            ["<strong>30 秒骨架</strong>", "「因为分类头和回归头是两个独立分支，训练时<strong>没有任何机制强制它们一致</strong>——分类分数只回答『像不像』，不回答『框准不准』。按它排序会大量选中『自信但框歪』的位置。后果比想象的严重：decoder 用的是<strong>可变形注意力</strong>，只在参考框附近采 K 个点，参考框歪了采样点就落在背景上，decoder 拿到的证据里根本没有目标——参考框 IoU 0.25 时，框内只有 40% 的面积落在目标上。修法是训练时把正样本的分类目标设成 IoU（VarifocalNet/TOOD 的思路），或者显式最小化两个头的判断差异（论文的 uncertainty-minimal 表述），让分数成为联合质量的估计。论文里这一项约 +0.8 AP。」"],
            ["加分点", "主动提副作用：「但在小目标上这是把双刃剑——8×8 的框位移 2 像素 IoU 就掉到 0.39，IoU-aware 会把小目标的分数系统性压低，反而更容易在全局 top-K 里落选，实践上要按层级配 query 配额。」"],
            ["<strong>踩雷点</strong>", "只说「分类和定位要对齐」但说不出「为什么参考框差会让可变形采样失效」"],
        ]),
        H3("Q4 · 无 NMS 到底省了多少？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你把延迟的<strong>均值</strong>和<strong>分布</strong>分开谈"],
            ["<strong>30 秒骨架</strong>", "「均值上大概 1–3 ms，对一个 9 ms 的模型是 10–30%，而且这部分确实可以靠 GPU NMS 或 TensorRT 的 EfficientNMS plugin 压缩。<strong>压不掉的是方差</strong>：NMS 是 $O(NK)$，$N$ 是过阈候选数、$K$ 是保留数，两者都随场景复杂度增长，实测 log-log 斜率约 1.7——目标数翻 10 倍，NMS 耗时涨约 50 倍。于是延迟尖峰恰好出现在场景最难的时候。对实时系统这意味着 <strong>WCET 无法静态确定</strong>，调度只能按经验最坏值预留，平均算力被浪费而且仍然不能证明不超时。RT-DETR 把这一项删成 0，端到端延迟成为常数。」"],
            ["加分点", "「如果必须用 YOLO，实用的折中是<strong>给 NMS 输入加硬上限</strong>——先按 score 取 top-1000 再进 NMS，把最坏耗时钉死；代价是极端密集场景会漏，要在评测里专门覆盖。」"],
            ["<strong>踩雷点</strong>", "报一个精确的「省了 X ms」而说不清测量口径（含不含预处理？batch 多少？什么卡？）——见模块 05"],
        ]),
        H3("Q5 · 「一份权重多档速度」是怎么做到的？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你知道它依赖的是<strong>逐层辅助损失</strong>这个训练机制，而不是什么推理技巧"],
            ["<strong>30 秒骨架</strong>", "「DETR 家族每层 decoder 后都接一个预测头并独立算集合损失（deep supervision，本来是为了加速收敛）。副产品是<strong>第 k 层的输出本身就是一个训练过的完整检测结果</strong>，推理时截断到前 k 层直接取第 k 层的头即可，不用重训、不用改训练代码，只需重新导出与重建 engine。典型的边际收益是急剧递减的——砍掉最后 2 层 AP 掉 0.3 左右、延迟省 6%。工程价值是：高中低三配 SoC 共用一份权重、一条数据管线、一次安全评审证据链；甚至可以做<strong>运行时降级</strong>，其他感知任务负载高时把 decoder 从 6 层降到 3 层，用 1 AP 换 1 ms，而不是直接丢帧。YOLO 做不到，因为只有一个末端头，要多档只能训 n/s/m/l/x 五个模型。」"],
            ["加分点", "提 D-FINE 的 GO-LSD——把末层定位分布自蒸馏回浅层，正好让「截断到少层」掉点更少，与多档速度互补"],
            ["<strong>踩雷点</strong>", "把「6 层截断到 3 层」和「直接训一个 3 层模型」说成显然等价（见第 6 节的 danger 框）"],
        ]),
        H3("Q6 · 那你什么时候<em>不</em>选 RT-DETR？"),
        P("这是成熟度探针，答不好前五题的分会被扣回去。<strong>骨架</strong>：「至少四种情况我会换。<strong>①算力极紧</strong>（&lt;4 ms 档）——decoder 与 query selection 的固定开销占比太高，RTMDet/YOLO 缩得更好。<strong>②目标极小且极密</strong>——query 数是硬天花板（300 个 query 就是最多 300 个目标），密集预测器加 P2 层更直接。<strong>③工具链要求零 plugin</strong>——可变形注意力和 <code>grid_sample</code> 在部分后端要写插件（RT-DETRv2 的离散采样正是为此，但要确认目标后端支持）。<strong>④数据量小或迭代速度优先</strong>——DETR 系收敛成本高，YOLO 的配方成熟、badcase 归因链路更短。<em>而在 TSR 这个具体场景里，很多量产系统的选择其实是『两级架构』：第一级用密集预测器做类别无关的小目标检出（类别少，NMS 的 N 天然小），第二级做高分辨率 crop 分类——这样延迟不确定性被挪到了『检出个数』上，而那个是可以设硬上限的。</em>」"),
        CALLOUT("intuition", "六道题的共同结构：<strong>判断 → 机制 → 数字 → 代价</strong>。缺「数字」显得没做过；缺「代价」显得没上线过。<em>把每题的那个关键数字（205 倍 / 2.5d / 0.39 / +0.8 AP / 斜率 1.7）背下来，比背整篇论文有效。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>「截断的浅层」到底比不比「原生浅模型」强？</strong>深监督下第 3 层的表示同时承受来自第 4–6 层的压力，直觉上应当学得更好；但公开消融很少做这个对照实验（因为要额外训 5 个模型）。<em>这是一个成本不高、结论有实用价值的开放问题，也是很好的自研课题。</em>",
            "<strong>无 NMS 的两条路会不会合流？</strong>DETR 系靠一对一匈牙利匹配，YOLOv10 靠一致的双分配。前者匹配不稳定导致收敛慢，后者靠一对多分支补密集监督。<em>「一对一是推理需求、一对多是训练最优」已经成为共识（见 Group DETR / Co-DETR / DEIM），但两者如何最优地组合仍无定论。</em>",
            "<strong>query 数量的自适应。</strong>固定 300 个 query 在稀疏场景是浪费（高速上只有 2 块标志），在极密集场景是天花板。<em>能否让 query 数随场景自适应？——但这会重新引入「延迟依赖场景」，把 RT-DETR 最大的优势还回去。这个取舍目前没有好的解。</em>",
            "<strong>定位的分布式表示。</strong>D-FINE 的 FDR 把「回归 4 个数」改成「细化四条边的概率分布」，本质是把定位从点估计变成分布估计。<em>这条路（源头是 Generalized Focal Loss 的 DFL）对小目标与模糊边界特别有价值——TSR 里被树叶遮挡一半的标志，边界本来就该是分布而不是一个数。</em>",
            "<strong>DETR 系的量化。</strong>attention 的 softmax 与 LayerNorm 对 INT8 敏感，掉点比纯卷积模型大，通常需要混合精度或 QAT。<em>「Transformer 检测器的 PTQ 何时够用」目前仍靠逐层敏感度分析试出来，缺少可靠的先验规则</em>（C60 模块 03 会展开）。",
            "<strong>小目标仍是 DETR 系的结构性弱区。</strong>query 数固定、匹配对小框的 IoU 极敏感、可变形采样点数有限。<em>RT-DETR 靠 S3 与多尺度采样缓解，但在 TSR 这种「目标常年在 10–30 像素」的任务上，是否值得为 DETR 的延迟稳定性付出小目标的代价，需要在你自己的分尺寸评测上回答，不能照搬 COCO 结论</em>（C57 模块 05 给方法）。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Zhao et al., <em>DETRs Beat YOLOs on Real-time Object Detection</em>（RT-DETR，CVPR 2024，arXiv:2304.08069）——重点读 §3.2 对 NMS 的分析（超参如何同时影响精度与速度）、§4.2 hybrid encoder 的逐步消融（变体 A→D 的演化路径最能说明设计动机）、以及 query selection 的散点图。<strong>★</strong> Lv et al., <em>RT-DETRv2: Improved Baseline with Bag-of-Freebies</em>（arXiv:2407.17140）——看离散采样算子那一节，这是纯粹的部署驱动改动。<strong>★</strong> Peng et al., <em>D-FINE: Redefine Regression Task of DETRs as Fine-grained Distribution Refinement</em>（ICLR 2025，arXiv:2410.13842）——FDR 与 GO-LSD。</p><p>配套背景：Zhu et al., <em>Deformable DETR</em>（ICLR 2021，可变形注意力与 two-stage）；Zhang et al., <em>DINO</em>（ICLR 2023，RT-DETR 的直接前身骨架）；Zhang et al., <em>VarifocalNet</em>（CVPR 2021）与 Feng et al., <em>TOOD</em>（ICCV 2021，IoU-aware 分类分数的源头）；Wang et al., <em>YOLOv10</em>（NeurIPS 2024，无 NMS 的另一条路）；Huang et al., <em>DEIM</em>（CVPR 2025，DETR 收敛加速）。相邻课程：模块 02（标签分配）、模块 03（RTMDet）、模块 05（延迟-精度选型）、C54（集合预测与匈牙利匹配的完整推导）、C57（小目标）、C60（车端部署与量化）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 04 · RT-DETR 解剖（NMS 耗时曲线 / hybrid encoder 计算量 / query selection / 层数可调）

目标：用**可运行的数值**把 RT-DETR 的四个设计决策各自钉死，而不是背结论。

本 notebook 你会亲手实现：
1. **numpy 版 NMS**（含确定性的 IoU 比较次数计数），实测耗时随目标数的增长曲线 → 证明 NMS 是超线性的
2. **score 阈值的精度-延迟耦合**：同一帧，阈值一变，候选数、耗时、目标覆盖率一起变
3. **端到端延迟分布**：YOLO 式（含 NMS）vs RT-DETR 式（常数），对比 p50 与 **p99**
4. **hybrid encoder 的计算量账**：attention 与 3×3 conv 的交叉点 $HW = 2.5d$，逐项验证
5. **CCFF vs 跨尺度 attention** 的反事实对比
6. **IoU-aware query selection**：可控相关性的合成实验，量化选中 query 的初始框质量
7. **decoder 层数可调**：边际收益、按预算选层数、多硬件平台的维护成本账

> 心智模型：**RT-DETR 的核心不是「更快」，是「延迟不再依赖这一帧里有什么」。**"""),

    md("""## 1 · NMS 的代价：先把它写出来

用**IoU 比较次数**（确定性）而不是墙钟时间（有噪声）作为主要断言依据。"""),

    code("""import numpy as np, time, math
rng = np.random.default_rng(0)

def iou_1_to_n(box, boxes):
    \"\"\"box: (4,) xyxy;  boxes: (N,4)  ->  (N,) IoU\"\"\"
    x1 = np.maximum(box[0], boxes[:, 0]); y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2]); y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    a0 = (box[2] - box[0]) * (box[3] - box[1])
    a1 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(a0 + a1 - inter, 1e-9)

def nms(boxes, scores, iou_thr=0.5):
    \"\"\"标准贪心 NMS。返回 (保留下标, IoU 比较次数)。
       **比较次数是确定性的**，所以它比墙钟时间更适合做断言。\"\"\"
    order = np.argsort(-scores, kind='stable')
    keep, ops = [], 0
    while order.size > 0:
        i = order[0]; keep.append(int(i))
        rest = order[1:]
        if rest.size == 0:
            break
        ious = iou_1_to_n(boxes[i], boxes[rest])
        ops += int(rest.size)
        order = rest[ious <= iou_thr]           # 只留下与当前框不重叠的
    return np.array(keep, dtype=int), ops

# —— 手算校验（三个框，答案可以口算）——
B = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=float)
S = np.array([0.9, 0.8, 0.7])
k, ops = nms(B, S, 0.5)
iou_ab = float(iou_1_to_n(B[0], B[1:2])[0])
print('IoU(A,B) = 81/119 =', round(iou_ab, 4), '  > 0.5 -> B 被抑制')
print('keep =', k.tolist(), '  IoU 比较次数 =', ops)
assert k.tolist() == [0, 2], k
assert abs(iou_ab - 81 / 119) < 1e-12
assert ops == 2
print('\\n✅ NMS 就位：交 9x9=81，并 100+100-81=119')"""),

    md("""## 2 · 耗时随目标数怎么长：合成场景 + 实测

合成规则（贴近真实检测器的输出分布）：
- 每个真实目标周围 **22 个抖动候选框**，抖动幅度与框尺寸成比例（σ = 6% 边长）
- 每个目标有一个「峰值分数」（Beta 分布），22 个候选的分数是峰值的随机折扣
- **背景误检数随场景复杂度增长**（`10 + 3·目标数`）——现实里目标多的场景杂波也多"""),

    code("""def make_scene(n_obj, rng, props_per_obj=22, bg_base=10, bg_per_obj=3, W=1920, H=1080):
    n_bg = bg_base + bg_per_obj * n_obj
    if n_obj > 0:
        ctr = rng.uniform([60, 60], [W - 60, H - 60], size=(n_obj, 2))
        sz  = rng.uniform(18, 90, size=(n_obj, 1))                  # 交通标志的典型像素尺寸
        c = np.repeat(ctr, props_per_obj, axis=0)
        s = np.repeat(sz,  props_per_obj, axis=0)
        c = c + rng.normal(0, 0.06, size=c.shape) * s               # 抖动 ∝ 框尺寸
        s = s * np.exp(rng.normal(0, 0.06, size=s.shape))
        fb = np.concatenate([c - s / 2, c + s / 2], axis=1)
        peak = rng.beta(2.2, 1.4, size=(n_obj, 1))                  # 每个目标的最高分
        fs = (peak * rng.uniform(0.25, 1.0, size=(n_obj, props_per_obj))).ravel()
        oid = np.repeat(np.arange(n_obj), props_per_obj)
    else:
        fb = np.zeros((0, 4)); fs = np.zeros(0); oid = np.zeros(0, dtype=int)
    bc = rng.uniform([0, 0], [W, H], size=(n_bg, 2))
    bs = rng.uniform(15, 60, size=(n_bg, 1))
    bb = np.concatenate([bc - bs / 2, bc + bs / 2], axis=1)
    bsc = rng.uniform(0.02, 0.35, size=n_bg)                        # 背景误检分数低
    return (np.vstack([fb, bb]), np.concatenate([fs, bsc]),
            np.concatenate([oid, np.full(n_bg, -1)]))

b0, s0, o0 = make_scene(10, np.random.default_rng(1))
print('n_obj=10 ->', len(s0), '个候选框（220 个目标候选 + 40 个背景误检）')
assert len(s0) == 10 * 22 + 40
print('✅ 场景生成器就位')"""),

    code("""N_OBJ = [2, 5, 10, 20, 40, 80, 160]
rows = []
for n in N_OBJ:
    b, s, o = make_scene(n, np.random.default_rng(100 + n))
    keep, ops = nms(b, s, 0.5)
    R = 5
    t0 = time.perf_counter()
    for _ in range(R):
        nms(b, s, 0.5)
    dt = (time.perf_counter() - t0) / R * 1000
    rows.append((n, len(s), len(keep), ops, dt))

print(f\"{'目标数':>7s} {'候选框 N':>10s} {'保留 K':>8s} {'IoU 比较次数':>14s} {'numpy 耗时 ms':>15s}\")
for n, N, K, ops, dt in rows:
    print(f'{n:>7d} {N:>10d} {K:>8d} {ops:>14d} {dt:>15.3f}')

n_arr   = np.array([r[0] for r in rows], dtype=float)
ops_arr = np.array([r[3] for r in rows], dtype=float)
t_arr   = np.array([r[4] for r in rows], dtype=float)
slope = float(np.polyfit(np.log(n_arr), np.log(ops_arr), 1)[0])
print(f'\\n目标数 {N_OBJ[0]} -> {N_OBJ[-1]}（{N_OBJ[-1]//N_OBJ[0]} 倍），'
      f'IoU 比较次数涨了 {ops_arr[-1]/ops_arr[0]:.0f} 倍')
print(f'log-log 斜率 = {slope:.2f}    （1.0 = 线性；**> 1 就是超线性**）')
assert ops_arr[-1] > 20 * ops_arr[0]
assert slope > 1.1, slope
assert t_arr[-1] > t_arr[0]
print('\\n⚠️  NMS 是 O(N·K)，而 N 和 K **都**随场景复杂度增长 -> 超线性。')
print('   TSR 场景对应：高速上 2 块标志 vs 城市路口龙门架+多块限速牌+一排店铺招牌。')""" ),

    md("""## 3 · score 阈值：精度和延迟被绑在同一个旋钮上

同一帧，只改 `score_thr`。看候选数、耗时、**目标覆盖率**（有多少真实目标还留着至少一个候选）一起变。"""),

    code("""b, s, o = make_scene(60, np.random.default_rng(7))
n_gt = len(set(o[o >= 0].tolist()))
print(f'固定场景：{n_gt} 个真实目标，{len(s)} 个原始候选\\n')
print(f\"{'score_thr':>10s} {'过阈 N':>9s} {'保留 K':>8s} {'IoU 比较':>10s} {'耗时 ms':>10s} {'目标覆盖率':>12s}\")
covs, Ns = [], []
for thr in [0.001, 0.05, 0.15, 0.25, 0.40]:
    m = s >= thr
    bb, ss, oo = b[m], s[m], o[m]
    keep, ops = nms(bb, ss, 0.5)
    t0 = time.perf_counter()
    for _ in range(5):
        nms(bb, ss, 0.5)
    dt = (time.perf_counter() - t0) / 5 * 1000
    cov = len(set(oo[oo >= 0].tolist())) / n_gt
    covs.append(cov); Ns.append(int(m.sum()))
    print(f'{thr:>10.3f} {int(m.sum()):>9d} {len(keep):>8d} {ops:>10d} {dt:>10.3f} {cov:>11.1%}')

assert Ns == sorted(Ns, reverse=True), '阈值升高，过阈候选数必须单调下降'
assert covs[0] > covs[-1] + 0.05, '阈值升高必须付出召回代价'
print('\\n⚠️  **这是一个旋钮，不是两个**：想提召回就得调低阈值 -> N 暴涨 -> NMS 变慢。')
print('   你没法「只降延迟不掉精度」。RT-DETR 的做法是把这个旋钮整个拆掉。')"""),

    md("""## 4 · 端到端延迟分布：p50 好看，p99 才决定能不能上车

先把 NMS 的比较次数写成闭式模型（避免跑几千次真 NMS），再用它做分布模拟。"""),

    code("""def nms_ops_model(n_obj, props=22, bg_base=10, bg_per_obj=3):
    \"\"\"闭式估计：目标阶段每保留 1 个框就抑制掉 props 个；背景阶段互不重叠、逐个保留。\"\"\"
    n_obj = int(n_obj)
    n_bg = bg_base + bg_per_obj * n_obj
    N = n_obj * props + n_bg
    obj_ops = sum(N - 1 - k * props for k in range(n_obj))
    bg_ops  = n_bg * (n_bg - 1) // 2
    return N, obj_ops + bg_ops

print(f\"{'n_obj':>6s} {'实测比较次数':>14s} {'模型估计':>10s} {'比值':>7s}\")
for n in [10, 40, 160]:
    b, s, o = make_scene(n, np.random.default_rng(200 + n))
    _, real = nms(b, s, 0.5)
    N, mdl = nms_ops_model(n)
    print(f'{n:>6d} {real:>14d} {mdl:>10d} {real/mdl:>7.2f}')
    assert 0.4 < real / mdl < 2.5, (n, real, mdl)
print('\\n✅ 闭式模型与实测同量级，可以用来做上万帧的分布模拟。')"""),

    code("""# 场景目标数：重尾分布（多数帧目标少，少数城市路口帧目标极多）
rng2 = np.random.default_rng(11)
n_scene = 4000
n_obj_s = np.clip(rng2.lognormal(np.log(8), 0.9, n_scene).astype(int) + 1, 1, 220)
ops_s = np.array([nms_ops_model(int(n))[1] for n in n_obj_s], dtype=float)

nms_ms = 0.20 + 5.0e-5 * ops_s          # 标定到 GPU NMS 的量级
YOLO_FIXED = 8.30                        # 预处理 + H2D + 推理 + decode + D2H
DETR_FIXED = 11.20                       # RT-DETR：**整条链路没有依赖场景的项**
t_yolo = YOLO_FIXED + nms_ms
t_detr = np.full(n_scene, DETR_FIXED)

def stats(t):
    return dict(p50=np.percentile(t, 50), p90=np.percentile(t, 90),
                p99=np.percentile(t, 99), mean=t.mean(), mx=t.max())

sy, sd = stats(t_yolo), stats(t_detr)
print(f\"{'':<16s} {'mean':>8s} {'p50':>8s} {'p90':>8s} {'p99':>8s} {'max':>8s}\")
for name, st in [('YOLO 式(含NMS)', sy), ('RT-DETR 式', sd)]:
    print(f'{name:<16s} {st[\"mean\"]:>8.2f} {st[\"p50\"]:>8.2f} {st[\"p90\"]:>8.2f} '
          f'{st[\"p99\"]:>8.2f} {st[\"mx\"]:>8.2f}')
print(f'\\n目标数分布: p50={np.percentile(n_obj_s,50):.0f}  p99={np.percentile(n_obj_s,99):.0f}  '
      f'max={n_obj_s.max()}')
assert sy['p50'] < sd['p50'] - 1.0, 'YOLO 的中位延迟应明显更低'
assert sy['p99'] > sd['p99'] + 0.3,  'YOLO 的 p99 应反超 RT-DETR'
assert sy['p99'] - sy['p50'] > 2.0
assert sd['p99'] == sd['p50'], 'RT-DETR 的延迟是常数'
print('\\n⚠️  **中位数上 YOLO 快 2.6 ms，p99 上反而更慢。**')
print('   按均值选型 -> 上线后在城市路口掉帧；按 p99 选型 -> 结论相反。')"""),

    code("""# 文本直方图 + 「按 p99 预留」浪费掉多少算力
lo, hi = np.percentile(t_yolo, [0.2, 99.8])
edges = np.linspace(lo, hi, 25)
h, _ = np.histogram(t_yolo, bins=edges)
print('YOLO 式端到端延迟分布（ms，条长按 count^0.4 缩放以便看清长尾）')
for i in range(len(h)):
    n = 0 if h[i] == 0 else max(1, int(60 * (h[i] / h.max()) ** 0.4))
    print(f'{edges[i]:6.2f} | {"█" * n}')
print(f'\\nRT-DETR 式：全部集中在 {DETR_FIXED:.2f} ms 一根柱子上（方差为 0）')

waste = 1 - sy['p50'] / sy['p99']
print(f'\\n调度器必须按 p99={sy[\"p99\"]:.2f} ms 预留时隙，而中位帧只用掉 {sy[\"p50\"]:.2f} ms')
print(f'-> **中位帧浪费了预留时隙的 {waste:.0%}**，而且仍然不能证明不超时（p99 不是上界）')
assert 0.15 < waste < 0.6
print('✅ 这就是「WCET 无法静态确定」在算力账上的样子。')"""),

    md("""## 5 · Hybrid encoder 的计算量账

`attn_macs` 含 QKVO 四个投影 + $QK^\\top$ + $\\text{attn}\\cdot V$；`conv_macs` 是同通道数的 $k\\times k$ 卷积。
单位统一用 **MAC**（乘加），不是 FLOPs。"""),

    code("""D = 256
G = 1e9

def attn_macs(n_tok, d=D):
    proj = 4 * n_tok * d * d          # Q, K, V, O 四个线性投影
    sim  = n_tok * n_tok * d          # QK^T
    agg  = n_tok * n_tok * d          # attn @ V
    return proj + sim + agg

def conv_macs(n_tok, cin=D, cout=D, k=3):
    return n_tok * cin * cout * k * k

def ffn_macs(n_tok, d=D, r=4):
    return 2 * n_tok * d * (r * d)

LEVELS = [('S3 (stride 8)', 80, 80), ('S4 (stride 16)', 40, 40), ('S5 (stride 32)', 20, 20)]
print(f\"{'层级':<16s} {'token':>7s} {'self-attn GMACs':>17s} {'3x3 conv GMACs':>16s} {'attn/conv':>10s}\")
for name, h, w in LEVELS:
    n = h * w
    a, c = attn_macs(n), conv_macs(n)
    print(f'{name:<16s} {n:>7d} {a/G:>17.3f} {c/G:>16.3f} {a/c:>10.2f}')

n_all = sum(h * w for _, h, w in LEVELS)
assert n_all == 8400
r_all = attn_macs(n_all) / attn_macs(400)
r_sep = sum(attn_macs(h * w) for _, h, w in LEVELS) / attn_macs(400)
print(f'\\n三尺度拼成一条序列({n_all} token)做全局 attention : {attn_macs(n_all)/G:8.2f} GMACs  '
      f'= AIFI 的 {r_all:.0f} 倍')
print(f'三尺度各自做 attention 再融合              : {sum(attn_macs(h*w) for _,h,w in LEVELS)/G:8.2f} GMACs  '
      f'= AIFI 的 {r_sep:.0f} 倍')
print(f'**只在 S5(400 token)做 = AIFI**            : {attn_macs(400)/G:8.3f} GMACs  = 1 倍')
assert 200 < r_all < 210, r_all
assert 128 < r_sep < 135, r_sep
print('\\n✅ 205 倍。这一个数字就解释了「为什么 Deformable DETR 的 encoder 贵、RT-DETR 的不贵」。')"""),

    code("""def crossover_tokens(d=D):
    \"\"\"2*(HW)^2*d + 4*HW*d^2  <  9*HW*d^2   <=>   HW < 5d/2\"\"\"
    return 5 * d // 2

hw = crossover_tokens(256)
side = int(round(hw ** 0.5))
print(f'd={D} 时的交叉点: HW = 5d/2 = {hw} 个 token  (约 {side}x{side} 的特征图)')
assert hw == 640
assert attn_macs(640) == conv_macs(640), '交叉点处两边严格相等'
assert attn_macs(639) < conv_macs(639)
assert attn_macs(641) > conv_macs(641)
print(f'  HW=639: attn {attn_macs(639):,} < conv {conv_macs(639):,}')
print(f'  HW=640: attn {attn_macs(640):,} = conv {conv_macs(640):,}   <- 严格相等')
print(f'  HW=641: attn {attn_macs(641):,} > conv {conv_macs(641):,}')

print('\\n每个层级该归谁：')
for name, h, w in LEVELS:
    n = h * w
    who = '**attention 更便宜 -> AIFI**' if attn_macs(n) < conv_macs(n) else 'conv 更便宜 -> CCFF'
    print(f'  {name:<16s} {n:>5d} token   {who}')
assert attn_macs(400) < conv_macs(400)
assert attn_macs(1600) > conv_macs(1600) and attn_macs(6400) > conv_macs(6400)
print('\\n✅ 「AIFI 只在 S5」不是拍脑袋，是这个不等式的直接结论。')
print('   心法：**attention 放 token 少的地方，conv 放 token 多的地方。**')"""),

    md("""## 6 · CCFF vs 跨尺度 attention：反事实对比"""),

    code("""def fusion_block_macs(n_tok, cin=D, hidden=D // 2, n_rep=3):
    \"\"\"RT-DETR 的 fusion block: 1x1 降维 -> N 个 RepBlock(3x3) -> 1x1 升维\"\"\"
    down = n_tok * cin * hidden
    rep  = n_rep * n_tok * hidden * hidden * 9
    up   = n_tok * hidden * cin
    return down + rep + up

EDGES = [('S5->S4 (自顶向下)', 1600), ('S4->S3 (自顶向下)', 6400),
         ('S3->S4 (自底向上)', 1600), ('S4->S5 (自底向上)', 400)]
tot = 0
print(f\"{'融合边':<20s} {'目标层 token':>13s} {'fusion block GMACs':>20s}\")
for e, n in EDGES:
    m = fusion_block_macs(n); tot += m
    print(f'{e:<20s} {n:>13d} {m/G:>20.3f}')
aifi = attn_macs(400) + ffn_macs(400)
print(f'\\nCCFF 合计                      {tot/G:8.2f} GMACs')
print(f'AIFI (1 层 attn + FFN, 400 tok) {aifi/G:8.3f} GMACs')
print(f'**Hybrid encoder 合计**         {(tot+aifi)/G:8.2f} GMACs   '
      f'(其中 attention 占 {aifi/(tot+aifi):.1%})')
assert aifi / (tot + aifi) < 0.10, 'hybrid encoder 里 attention 占比应远小于 10%'

# 反事实：把 S4->S3 这条边换成 cross-attention（6400 query 对 8400 key）
edge_conv = fusion_block_macs(6400)
edge_attn = 2 * 6400 * 8400 * D
print(f'\\n反事实（S4->S3 这条边）：')
print(f'  fusion block (卷积版) : {edge_conv/G:7.2f} GMACs')
print(f'  cross-attention 版    : {edge_attn/G:7.2f} GMACs   -> **贵 {edge_attn/edge_conv:.1f} 倍**')
assert edge_attn > 5 * edge_conv
print('\\n✅ 「hybrid」是字面意思：encoder 里 90%+ 的计算量是卷积。')
print('   跨尺度融合本质是「把对应位置的信息对齐后相加」——卷积的归纳偏置正好合适。')"""),

    md("""## 7 · IoU-aware query selection：起跑线有多重要

设定：encoder 输出 40000 个候选位置。每个位置有一个**真实定位质量** `iou`（与训练方式无关，固定），
和一个**分类分数** `cls`。两者的相关性 ρ 就是「分类头与定位头有多一致」：
- vanilla 训练：两个头独立优化，ρ ≈ 0.35
- IoU-aware / uncertainty-minimal 训练：显式对齐，ρ ≈ 0.90"""),

    code("""rng3 = np.random.default_rng(2024)
N_FEAT, K_QUERY = 40000, 500

z_loc = rng3.standard_normal(N_FEAT)                 # 定位质量的隐变量（固定）
iou_true = np.clip(0.34 + 0.19 * z_loc, 0.0, 1.0)    # 该位置的框与 GT 的真实 IoU

def cls_head(rho, seed):
    \"\"\"分类分数：与定位质量相关性为 rho。rho 越高 = 两个头越一致。\"\"\"
    r = np.random.default_rng(seed)
    z = rho * z_loc + math.sqrt(1 - rho ** 2) * r.standard_normal(N_FEAT)
    return 1.0 / (1.0 + np.exp(-(1.1 * z - 2.2)))    # 多数位置分数很低（背景）

def selection_report(cls, iou, k=K_QUERY):
    idx = np.argsort(-cls)[:k]
    u = iou[idx]
    return dict(mean_iou=float(u.mean()),
                frac_good=float((u >= 0.5).mean()),
                n_bad=int((u < 0.2).sum()),
                hit=float(np.mean(2 * u / (1 + u))))   # 参考框内落在 GT 上的面积比例

van = selection_report(cls_head(0.35, 1), iou_true)
awa = selection_report(cls_head(0.90, 1), iou_true)
print(f\"{'':<26s} {'vanilla (ρ=0.35)':>18s} {'IoU-aware (ρ=0.90)':>20s}\")
print(f\"{'选中 query 的平均初始 IoU':<26s} {van['mean_iou']:>18.3f} {awa['mean_iou']:>20.3f}\")
print(f\"{'IoU >= 0.5 的占比':<26s} {van['frac_good']:>17.1%} {awa['frac_good']:>19.1%}\")
print(f\"{'IoU < 0.2 的灾难性 query':<26s} {van['n_bad']:>18d} {awa['n_bad']:>20d}\")
print(f\"{'可变形采样点命中率 2u/(1+u)':<26s} {van['hit']:>17.1%} {awa['hit']:>19.1%}\")
assert awa['mean_iou'] > van['mean_iou'] + 0.10
assert awa['frac_good'] > van['frac_good'] + 0.20
assert awa['n_bad'] < van['n_bad']
assert awa['hit'] > van['hit'] + 0.08
print('\\n⚠️  vanilla 下有一批 query 从第一层开始就采不到目标 ——')
print('    可变形注意力只在参考框附近采 K 个点，参考框歪了，证据里根本没有目标。')
print('✅ 这就是「起跑线」的含义：decoder 只有 6 层，它救不回一个从零开始的定位。')"""),

    code("""# ρ 扫描：一致性 -> 起跑线质量 的完整曲线
print(f\"{'ρ (两个头的一致性)':>18s} {'平均初始 IoU':>14s} {'IoU>=0.5 占比':>15s} {'采样命中率':>12s}\")
prev = -1.0
for rho in [0.0, 0.2, 0.35, 0.5, 0.7, 0.9, 0.98]:
    rep = selection_report(cls_head(rho, 5), iou_true)
    print(f'{rho:>18.2f} {rep[\"mean_iou\"]:>14.3f} {rep[\"frac_good\"]:>14.1%} {rep[\"hit\"]:>11.1%}')
    assert rep['mean_iou'] > prev - 0.02, '起跑线质量应随一致性单调提升'
    prev = rep['mean_iou']
print('\\n✅ 论文报告这一项单独约 +0.8 AP，并且收敛更快 —— 因为 decoder 少花几层去纠错。')
print('⚠️  TSR 副作用：8x8 的框沿对角线位移 2px，IoU 就掉到 36/92 = 0.391，')
print(f'   IoU-aware 会把小目标的分数系统性压低 -> 全局 top-{K_QUERY} 里更容易落选。')
assert abs(36 / 92 - 0.3913) < 1e-3
print('   对策：按特征层级给 query 配额，或用尺度归一化的定位度量（C57 的 NWD）。')"""),

    md("""## 8 · decoder 层数可调：一份权重，多档速度"""),

    code("""DEPTHS  = [1, 2, 3, 4, 5, 6]
DEC_AP  = [44.9, 50.5, 52.1, 52.8, 53.0, 53.1]     # 教学用示意值，量级同论文消融
DEC_LAT = [7.8, 8.1, 8.4, 8.7, 9.0, 9.3]           # ms，每层约 +0.3

print(f\"{'层数':>5s} {'AP':>7s} {'延迟 ms':>9s} {'相对 6 层':>10s} {'本层新增 AP':>13s} {'AP/ms':>8s}\")
gains = []
for i, d in enumerate(DEPTHS):
    dap = DEC_AP[i] - DEC_AP[i - 1] if i else float('nan')
    dms = DEC_LAT[i] - DEC_LAT[i - 1] if i else float('nan')
    per = dap / dms if i else float('nan')
    if i:
        gains.append(per)
    g1 = f'{dap:>13.1f}' if i else f\"{'—':>13s}\"
    g2 = f'{per:>8.1f}' if i else f\"{'—':>8s}\"
    print(f'{d:>5d} {DEC_AP[i]:>7.1f} {DEC_LAT[i]:>9.1f} {DEC_AP[i]-DEC_AP[-1]:>10.1f}{g1}{g2}')

assert all(gains[i] > gains[i + 1] for i in range(len(gains) - 1)), '边际收益必须递减'
print(f'\\n砍掉最后 2 层：AP {DEC_AP[-1]:.1f} -> {DEC_AP[3]:.1f}（-{DEC_AP[-1]-DEC_AP[3]:.1f}），'
      f'延迟 {DEC_LAT[-1]:.1f} -> {DEC_LAT[3]:.1f} ms（省 {(1-DEC_LAT[3]/DEC_LAT[-1]):.0%}）')
print('✅ 边际收益急剧递减（18.7 -> 0.3 AP/ms），多数量产场景会毫不犹豫做这个交换。')"""),

    code("""def pick_depth(aps, lats, budget_ms):
    \"\"\"给定延迟预算，返回 (层数, AP)；预算太紧则返回 (None, None)。\"\"\"
    ok = [(a, i + 1) for i, (a, l) in enumerate(zip(aps, lats)) if l <= budget_ms]
    if not ok:
        return None, None
    a, d = max(ok)
    return d, a

print('同一份权重，按平台预算裁层：')
print(f\"{'平台':<20s} {'延迟预算 ms':>12s} {'选用层数':>9s} {'AP':>7s}\")
for plat, bud in [('低配 SoC (共享算力)', 8.5), ('中配 SoC', 8.8),
                  ('高配 SoC', 9.5), ('极紧预算（不可行）', 7.0)]:
    d, a = pick_depth(DEC_AP, DEC_LAT, bud)
    txt = f'{d:>9d} {a:>7.1f}' if d else f\"{'不可行':>9s} {'—':>7s}\"
    print(f'{plat:<20s} {bud:>12.1f}{txt}')
assert pick_depth(DEC_AP, DEC_LAT, 8.5) == (3, 52.1)
assert pick_depth(DEC_AP, DEC_LAT, 9.5) == (6, 53.1)
assert pick_depth(DEC_AP, DEC_LAT, 7.0) == (None, None)
print('\\n✅ 三档全部来自**同一个权重文件**，只是导出时截断到不同层数。')"""),

    code("""# 多硬件平台的工程成本账
def program_cost(n_platforms, per_train_gpu_days=8, per_eval_days=1.5, engines_per_plat=1):
    return dict(trainings=n_platforms, gpu_days=n_platforms * per_train_gpu_days,
                eval_days=n_platforms * per_eval_days,
                weights=n_platforms, engines=n_platforms * engines_per_plat)

N_PLAT = 3
yolo = program_cost(N_PLAT)                       # 每档速度训一个尺寸
rtdetr = dict(trainings=1, gpu_days=8, eval_days=N_PLAT * 1.5,
              weights=1, engines=N_PLAT)          # 一次训练；评测仍要每档跑一遍
print(f\"{'':<22s} {'YOLO 系(训 3 个尺寸)':>22s} {'RT-DETR(截断 3 档)':>22s}\")
for k, label in [('trainings', '训练次数'), ('gpu_days', 'GPU-天'),
                 ('eval_days', '评测人天'), ('weights', '权重文件数'), ('engines', 'engine 数')]:
    print(f'{label:<22s} {yolo[k]:>22} {rtdetr[k]:>22}')
assert rtdetr['gpu_days'] * 3 == yolo['gpu_days']
assert rtdetr['weights'] == 1 and yolo['weights'] == N_PLAT
print('\\n✅ 一份权重 = 一条数据管线、一次训练预算、一套 badcase 归因、一份安全评审证据链。')
print('   注意：**评测人天并没有省** —— 每一档都必须独立评测，这一点常被忽略。')"""),

    md("""## ✏️ 练习 1：NMS 代价的闭式模型

实现 `nms_cost(n_obj, props=22, bg_base=10, bg_per_obj=3)` 返回 `(N, ops)`：
- `n_bg = bg_base + bg_per_obj * n_obj`；`N = n_obj*props + n_bg`
- 目标阶段：第 k 轮（k 从 0 起）比较 `N - 1 - k*props` 次，共 `n_obj` 轮
- 背景阶段：`n_bg` 个互不重叠的框，比较次数 `n_bg*(n_bg-1)//2`"""),

    code("""def nms_cost(n_obj, props=22, bg_base=10, bg_per_obj=3):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert nms_cost(0) == (10, 45), nms_cost(0)                    # 10*9//2 = 45
assert nms_cost(1) == (35, 34 + 78), nms_cost(1)               # 22+13=35; 34; 13*12//2=78
assert nms_cost(8) == (210, 1056 + 561), nms_cost(8)           # 8*209-22*28=1056; 34*33//2=561
_, o10 = nms_cost(10)
_, o80 = nms_cost(80)
assert o10 == 1600 + 780, o10
assert o80 / o10 > 8, '目标数 x8，比较次数应涨远超 8 倍（超线性）'
print(f'n_obj=10 -> ops={o10};  n_obj=80 -> ops={o80};  倍数 {o80/o10:.1f}（目标数只涨了 8 倍）')
print('✅ 练习 1 通过：NMS 是 O(N·K)，而 N 与 K 都随场景增长。')"""),

    md("""## ✏️ 练习 2：attention / conv 的归属判定

实现三个函数：
- `crossover_tokens(d)` → `5*d//2`
- `attention_cheaper(n_tok, d)` → `attn_macs(n_tok,d) < conv_macs(n_tok,...)`（**严格小于**）
- `plan_encoder(levels, d)` → `{层级名: 'AIFI' 或 'CCFF'}`，`levels` 是 `{名字: token 数}`"""),

    code("""def crossover_tokens(d=256):
    # TODO
    raise NotImplementedError

def attention_cheaper(n_tok, d=256):
    # TODO
    raise NotImplementedError

def plan_encoder(levels, d=256):
    # TODO: attention 更便宜的层 -> 'AIFI'，否则 -> 'CCFF'
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
assert crossover_tokens(256) == 640
assert crossover_tokens(128) == 320
assert attention_cheaper(400) and attention_cheaper(639)
assert not attention_cheaper(640), '交叉点处两边相等，严格小于应为 False'
assert not attention_cheaper(1600) and not attention_cheaper(6400)
plan = plan_encoder({'S3': 6400, 'S4': 1600, 'S5': 400})
assert plan == {'S3': 'CCFF', 'S4': 'CCFF', 'S5': 'AIFI'}, plan
# d 变大 -> 交叉点右移 -> 更多层适合 attention
plan_big = plan_encoder({'S3': 6400, 'S4': 1600, 'S5': 400}, d=1024)
assert plan_big['S4'] == 'AIFI', 'd=1024 时交叉点=2560 token，S4(1600) 也该归 attention'
print('d=256  ->', plan)
print('d=1024 ->', plan_big, '  （交叉点 =', crossover_tokens(1024), 'token）')
print('✅ 练习 2 通过：AIFI 的层级归属是一个不等式，不是设计者的偏好。')"""),

    md("""## ✏️ 练习 3：query selection 的质量评估

实现 `selection_quality(cls, iou, k)` 返回 `(mean_iou, frac_good, n_bad)`：
按 `cls` 降序取 top-k，统计这 k 个位置的平均 `iou`、`iou>=0.5` 的比例、`iou<0.2` 的个数。"""),

    code("""def selection_quality(cls, iou, k):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测（手算）——
c = np.array([0.90, 0.20, 0.80, 0.10, 0.55])
u = np.array([0.30, 0.90, 0.70, 0.95, 0.15])
m, g, nb = selection_quality(c, u, 3)          # top3 by cls -> idx 0,2,4 -> iou 0.30,0.70,0.15
assert abs(m - (0.30 + 0.70 + 0.15) / 3) < 1e-12, m
assert abs(g - 1 / 3) < 1e-12, g               # 只有 0.70 >= 0.5
assert nb == 1, nb                             # 只有 0.15 < 0.2
m5, g5, nb5 = selection_quality(c, u, 5)
assert abs(m5 - u.mean()) < 1e-12
assert abs(g5 - 0.6) < 1e-12 and nb5 == 1
# 用第 7 节的合成数据复现主结论
mv, gv, bv = selection_quality(cls_head(0.35, 3), iou_true, 500)
ma, ga, ba = selection_quality(cls_head(0.90, 3), iou_true, 500)
print(f'vanilla   mean_iou={mv:.3f}  good={gv:.1%}  bad={bv}')
print(f'IoU-aware mean_iou={ma:.3f}  good={ga:.1%}  bad={ba}')
assert ma > mv + 0.10 and ga > gv + 0.20 and ba < bv
print('✅ 练习 3 通过：起跑线质量可以直接量化，不用等 AP 出来。')"""),

    md("""## ✏️ 练习 4：速度菜单与预算选层

实现 `speed_menu(aps, lats, budgets)`：对每个预算返回 `(budget, depth, ap)`，
不可行时 `(budget, None, None)`。规则同 `pick_depth`：在满足 `lat <= budget` 的层数里取 AP 最大的。"""),

    code("""def speed_menu(aps, lats, budgets):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
menu = speed_menu(DEC_AP, DEC_LAT, [7.0, 8.0, 8.5, 9.0, 12.0])
expect = [(7.0, None, None), (8.0, 1, 44.9), (8.5, 3, 52.1), (9.0, 5, 53.0), (12.0, 6, 53.1)]
assert menu == expect, menu
for b, d, a in menu:
    line = f'{d} 层 -> AP {a}' if d else '不可行（连 1 层都超预算）'
    print(f'预算 {b:>5.1f} ms : {line}')
# 一份权重覆盖了几档？
covered = len({d for _, d, _ in menu if d is not None})
assert covered == 4
print(f'\\n✅ 练习 4 通过：同一份权重覆盖了 {covered} 档不同的速度-精度工作点。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def nms_cost(n_obj, props=22, bg_base=10, bg_per_obj=3):
    n_obj = int(n_obj)
    n_bg = bg_base + bg_per_obj * n_obj
    N = n_obj * props + n_bg
    obj_ops = sum(N - 1 - k * props for k in range(n_obj))
    bg_ops = n_bg * (n_bg - 1) // 2
    return N, obj_ops + bg_ops"""),

    code("""# 练习 2 参考答案
def crossover_tokens(d=256):
    return 5 * d // 2

def attention_cheaper(n_tok, d=256):
    return attn_macs(n_tok, d) < conv_macs(n_tok, cin=d, cout=d, k=3)

def plan_encoder(levels, d=256):
    return {name: ('AIFI' if attention_cheaper(n, d) else 'CCFF')
            for name, n in levels.items()}"""),

    code("""# 练习 3 参考答案
def selection_quality(cls, iou, k):
    idx = np.argsort(-np.asarray(cls))[:k]
    u = np.asarray(iou)[idx]
    return float(u.mean()), float((u >= 0.5).mean()), int((u < 0.2).sum())"""),

    code("""# 练习 4 参考答案
def speed_menu(aps, lats, budgets):
    out = []
    for b in budgets:
        ok = [(a, i + 1) for i, (a, l) in enumerate(zip(aps, lats)) if l <= b]
        if ok:
            a, d = max(ok)
            out.append((b, d, a))
        else:
            out.append((b, None, None))
    return out"""),

    md("""---
## 🧪 真实工程胶囊：RT-DETR 上车前的检查单与配置片段"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# RT-DETR 上车检查单（按顺序做，每一步都有明确的通过条件）
# ══════════════════════════════════════════════════════════════════════

# ① 导出：确认 decoder 层数可裁，并为每一档单独导出
#    mmdet/ultralytics/lyuwenyu 各家实现的字段名不同，但都是同一个开关
#    (lyuwenyu/RT-DETR 的 yaml，字段名以你用的实现为准)
#
#    RTDETRTransformer:
#      num_decoder_layers: 6      # 训练用 6
#      eval_idx: -1               # ← **推理时取第几层的头**：-1=最后一层, 2=第3层
#      num_queries: 300           # 上限：单帧最多能检出 300 个目标
#      feat_strides: [8, 16, 32]  # S3/S4/S5
#    HybridEncoder:
#      use_encoder_idx: [2]       # ← **AIFI 只作用在索引 2（=S5）**，别改成 [0,1,2]
#      num_encoder_layers: 1
#      expansion: 1.0             # CCFF fusion block 的宽度
#
# 通过条件：改 eval_idx 后重新导出，ONNX 的节点数应显著减少；AP 掉幅符合预期消融表

# ② 算子检查（DETR 系最容易在这里卡住）
#    grid_sample / MultiScaleDeformableAttention 在部分后端需要 plugin
#    RT-DETRv2 的离散采样版本可以绕开，但要确认你用的是哪个分支
#   $ polygraphy inspect model rtdetr.onnx --show layers | grep -i -E "grid|deform"
#   $ trtexec --onnx=rtdetr.onnx --fp16 --verbose 2>&1 | grep -i -E "unsupported|plugin|subgraph"
# 通过条件：子图数 == 1（没有静默回退），无 unsupported layer

# ③ **延迟稳定性验证**（这是选 RT-DETR 的理由，必须验证它真的成立）
#    用一组目标数差异极大的真实帧跑，而不是同一张图跑 1000 次
#   for img in [highway_2signs.jpg, gantry_8signs.jpg, urban_40boxes.jpg]:
#       latencies = [timed_infer(img) for _ in range(500)]   # 含 warmup 丢弃
#       p50, p99 = np.percentile(latencies, [50, 99])
# 通过条件：**不同帧之间的 p50 差异 < 3%**（RT-DETR 应该做到）
#           如果差异大，说明你的预处理或后处理里混进了数据依赖项

# ④ 与 YOLO baseline 的公平对比（同口径！见模块 05）
#    必须统一：batch=1 / 含预处理与拷贝 / 含 NMS / 同精度 / 同卡 / 同 warmup
#    报 **p50 和 p99 两个数**，只报一个的对比无效

# ⑤ TSR 特有检查
#    · num_queries=300 是硬天花板 -> 统计你的数据集里单帧最大标志数，留 3x 余量
#    · 按**像素尺寸分桶**评测（<16px / 16-32 / 32-64 / >64），COCO 口径的 AP 会掩盖小目标退化
#    · IoU-aware 会压低小目标分数 -> 检查 top-300 里小目标 query 的占比是否够
#      selected_small_ratio = (选中 query 的 GT 面积 < 32^2 的比例) / (数据集里小目标占比)
#      这个比值明显 < 1 就说明小目标在 query selection 阶段就被挤掉了

# ⑥ 多档速度的发布纪律
#    每一档 (eval_idx) 都是一个**独立的发布物**，必须各自：
#    过完整评测集 / 过分场景切片 / 过回归门禁 / 记录到模型卡
#    「一份权重」省的是训练，不是评测。
'''
print(RECIPE)
for token in ['eval_idx', 'use_encoder_idx', 'num_queries', 'grid_sample',
              'p50 和 p99', '分桶', 'subgraph']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：层数可裁 / AIFI 层级 / 算子回退 / 延迟稳定性 / 公平对比 / TSR 专项 / 发布纪律')"""),

    md("""### 小结

- **RT-DETR 的卖点不是「平均更快」，是「延迟不再依赖这一帧里有什么」。**
  NMS 是 $O(NK)$，实测 log-log 斜率约 1.7；目标数翻 10 倍，比较次数涨约 50 倍。
  于是 **p50 上 YOLO 更快，p99 上反而更慢**——按均值选型会上线才发现掉帧。
- **AIFI 只在 S5**：三尺度拼成 8400 token 做全局 attention，代价是只在 400 token 上做的 **205 倍**。
  更精确的判据是 $2(HW)^2d + 4HWd^2 < 9HWd^2 \\iff HW < \\tfrac52 d$，$d=256$ 时交叉点 **640 token**，
  S5 的 400 在下面、S4 的 1600 在上面。**心法：attention 放 token 少的地方，conv 放 token 多的地方。**
- **CCFF 全用卷积**：跨尺度融合是「对齐后相加」的局部操作，卷积的归纳偏置正合适；
  换成 cross-attention 单是 S4→S3 一条边就贵 8 倍。hybrid encoder 里 attention 占比 < 10%。
- **query selection 是 decoder 的起跑线**：可变形注意力只在参考框附近采样，
  参考框 IoU 0.25 时只有 40% 的采样面积落在目标上。把两个头的一致性从 0.35 提到 0.90，
  选中 query 的平均初始 IoU 从 0.51 涨到 0.79。**副作用：小目标分数被系统性压低。**
- **逐层辅助头 = 一份权重多档速度**：边际收益急剧递减（18.7 → 0.3 AP/ms），
  砍最后 2 层掉 0.3 AP、省 6% 延迟。**省的是训练与权重管理，不省评测**。
- **选型没有普适答案**：硬约束是「p99 可静态界定」就选 RT-DETR 系；
  硬约束是「极小算力 + 极小目标 + 零 plugin」就选 RTMDet/YOLO。
  TSR 量产系统常见的第三条路是两级架构——把延迟不确定性挪到一个能设硬上限的地方。

下一站：**模块 05 · 延迟-精度权衡与实时检测器选型** —— 为什么论文的 FPS 不可信，以及怎么自己测。"""),
]
