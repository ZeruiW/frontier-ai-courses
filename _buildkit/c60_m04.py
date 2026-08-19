# -*- coding: utf-8 -*-
"""C60 模块 04 · 后处理对齐与 C++ 推理管线。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（预处理一致性 · letterbox 正变换）、模块 02（TensorRT 构建与算子回退）、模块 03（INT8 校准）；C53 模块 04 的 NMS 代价分析"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_postprocess_cpp.ipynb（纯 numpy，自己实现两种 NMS 与端到端对拍器）'),
    ("核心参考", "Faster R-CNN 的 py_cpu_nms · Detectron2 的 box mode · TensorRT EfficientNMS plugin 文档 · ONNX NonMaxSuppression 算子规范 · COCO/VOC 评测口径差异"),
    ("预计时长", "读 80 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("last-mile", "后处理：训练-部署鸿沟的最后一公里", "".join([
        P("模块 01 处理预处理、模块 02–03 处理模型本身。到这一节，你的 ONNX 已经导出、engine 已经构建、INT8 已经校准到掉点 0.4 mAP。<strong>然后你把它接到车上，框整体往下偏了 420 像素。</strong>"),
        P("后处理之所以是鸿沟里最难守的一段，有一个结构性原因：<strong>它不在 ONNX 里。</strong>预处理和模型至少还有「同一份权重」「同一个 graph」作为锚点，而后处理是<em>两份独立写成的代码</em>——训练框架里那份是研究员两年前写的 Python，车端那份是嵌入式工程师上个月写的 C++。<strong>没有任何机制保证它们语义一致，也没有任何 CI 在检查。</strong>"),
        ASCII("""训练侧（Python）                          部署侧（C++ / TRT）
─────────────────────────────            ─────────────────────────────
cv2.imread → BGR                          nvjpeg / ISP → YUV → BGR?
letterbox(114, 居中, stride 对齐)          resize + pad(0, 左上)         ← 分歧①
/255 → -mean/std → RGB → NCHW             uint8 → GPU kernel 归一化      ← 分歧②
─────────── 同一份 ONNX / engine ────────────  这一段有工具可查
sigmoid(logits)   ← 在模型外                engine 里已经有 Sigmoid?      ← 分歧③
score_thr → topk → NMS(iou, offset=0)     topk → NMS(iou, offset=1)      ← 分歧④
逆 letterbox: (b - pad) / r               逆 letterbox: b / r - pad      ← 分歧⑤
clip 到原图                                clip 到网络输入尺寸            ← 分歧⑥
─────────────────────────────            ─────────────────────────────
              ↑ 这六处，没有一处会报错，全部静默生效"""),
        H3("症状 → 病因速查表"),
        P("后处理 bug 有一个非常好用的性质：<strong>它是系统性的、可复现的、与图像内容无关的</strong>。同一类 bug 在每一帧上都以同样的方式表现。这让它比「模型某些场景不行」好查一个数量级——只要你知道该看什么。"),
        TABLE(["症状", "最可能的病因", "为什么这样表现", "验证方法（30 秒内）"], [
            ["框整体沿某轴平移固定像素", "<strong>letterbox 逆变换写错</strong>（漏减 pad / 顺序反 / pad 减了两遍）", "pad 是常数，除以 $r$ 后仍是常数 → 每个框偏一样多", "取一帧，把 GT 框和预测框的中心差取平均，看是不是一个稳定的常数"],
            ["框整体等比缩放", "归一化坐标 vs 像素坐标混淆；或缩放比 $r$ 用错（stretch vs letterbox）", "错的是乘性因子", "预测框宽高 / GT 宽高的比值是否恒定"],
            ["分数整体被压缩到 [0.5, 0.73]", "<strong>sigmoid 被应用了两次</strong>", "$\\sigma(\\sigma(x))$ 的值域就是这个区间", "看全部分数的 min/max；<strong>mAP 几乎不变</strong>（单调变换不改排序）"],
            ["分数分布合理但阈值筛不掉东西", "模型输出的是 logits，后处理当成概率用了", "logit 0.3 对应概率 0.574", "分数有没有负数、有没有 &gt; 1"],
            ["重复框明显变多 / 变少", "NMS 的 <code>iou_thr</code> 不一致，或 class-wise ↔ class-agnostic 弄反", "抑制强度变了", "统计每个 GT 附近的预测框个数"],
            ["密集场景成片漏检，稀疏场景正常", "<strong>top-k 截断位置放在 NMS 之前</strong>", "300 个候选可能全来自 20 个目标", "统计过阈候选数与最终检出数之比"],
            ["只有小目标掉点，大目标完好", "IoU 的 <code>+1</code> 边界约定不一致；或 1–2 px 的系统性偏移", "两者的影响都与框尺寸成反比", "按像素尺寸分桶看 AP（16px 桶崩、64px 桶正常）"],
            ["x 和 y 互换 / 框转置", "<code>yxyx</code> 与 <code>xyxy</code> 约定不同（TF、部分 TRT plugin 用 yxyx）", "格式约定不带类型信息，全靠文档", "把一帧的框画出来，看是不是沿主对角线镜像"],
            ["类别整体错位一格", "softmax 头有 background 占 index 0，sigmoid 头没有", "类别 ID 偏移 1", "看最高频的预测类别是不是训练集里 ID 差 1 的那个"],
            ["INT8 模型上两侧结果不同，FP16 上相同", "<strong>分数并列时排序不稳定</strong>", "INT8 输出只有 ~256 个离散值 → 并列大量出现", "统计过阈候选里分数的<em>唯一值个数</em>"],
        ]),
        DUAL(
            "后处理 bug 最气人的地方，是它<strong>不会让你的程序崩溃，也不会让 mAP 变成 0</strong>。它让 mAP 从 0.82 掉到 0.71，然后你会花两周去怀疑量化、怀疑校准集、怀疑车端相机的色彩空间——因为「掉 11 个点」看起来太像一个模型问题了。<em>而真相可能只是逆变换里少减了一个 pad。</em>",
            "更准确地说：后处理 bug 制造的是<span class=\"term\">systematic error</span>（系统误差）而非 <span class=\"term\">random error</span>（随机误差）。系统误差在 mAP 这类<em>聚合指标</em>上表现为一个平滑的下降，与「模型能力不足」在数值上不可区分；但在<em>逐样本</em>的对拍上，它表现为一个恒定的偏差项，一眼可辨。<strong>这就是为什么本模块的核心方法论是「逐阶段对拍」而不是「看指标」</strong>——把聚合指标换成逐元素比较，系统误差立刻从伪装中掉出来。这也是模块 00 那句「任何一致性问题都能在 30 分钟内定位到具体层」的兑现方式。",
        ),
        CALLOUT("danger", "<p><strong>面试高频题：「训练和部署结果对不上，你怎么排查？」</strong>差答案是「逐层 dump 看哪层不一样」——这只覆盖了模型层，而模型层恰恰是<em>最不容易出错</em>的那一层（因为它有同一份 ONNX 作锚点）。<strong>满分答案的结构是：①先说三层划分（预处理 / 模型 / 后处理）与各自的典型故障率——业界经验里预处理与后处理合起来占绝大多数；②再说定位方法是「固定输入，逐阶段二分」，而不是「猜」；③然后主动举一两个具体分歧点（letterbox 逆变换的顺序、IoU 的 +1、sigmoid 在模型内外）；④最后说这套对拍工具应该在项目第一天就写好，而不是出事时才写</strong>。<em>第④点是区分「修过 bug 的人」和「负责过交付的人」的分水岭。</em></p>", "别把「排查一致性」答成「dump 每一层」"),
        CALLOUT("intuition", "本节的一句话：<strong>后处理是唯一一段「两份实现、零份约束」的代码。它的 bug 不会报错，只会让你误判成模型问题。</strong>"),
    ])),

    # ============================================================== 2
    ("nms-impl", "NMS 的实现分歧：+1 约定、调用顺序与排序稳定性", "".join([
        P("先看一段几乎每个检测代码库里都出现过的代码——它来自 R-CNN / Fast R-CNN / Faster R-CNN 的 <code>py_cpu_nms.py</code>，被无数项目复制粘贴过："),
        CODE("""# Faster R-CNN 时代的 NMS（Pascal VOC 口径）
areas = (x2 - x1 + 1) * (y2 - y1 + 1)          # ← 注意 +1
...
w = np.maximum(0.0, xx2 - xx1 + 1)             # ← 注意 +1
h = np.maximum(0.0, yy2 - yy1 + 1)
inter = w * h
ovr = inter / (areas[i] + areas[order[1:]] - inter)

# Detectron2 / COCO 时代
areas = (x2 - x1) * (y2 - y1)                  # ← 没有 +1
inter = max(0, xx2 - xx1) * max(0, yy2 - yy1)""", "python"),
        H3("这个 +1 从哪来"),
        P("它不是笔误，是<strong>坐标语义的差别</strong>。<span class=\"term\">Pascal VOC</span> 的标注是「像素索引」：框 <code>[0, 0, 7, 7]</code> 表示<em>从第 0 个像素到第 7 个像素，闭区间，一共 8 个像素</em>，所以宽度是 $7-0+1=8$。<span class=\"term\">COCO</span> 的标注是「连续坐标」：框 <code>[0, 0, 8, 8]</code> 表示<em>从坐标 0 到坐标 8 的半开区间</em>，宽度就是 $8-0=8$。<strong>两种约定各自自洽，但把 VOC 的公式套到 COCO 的坐标上，每个框就凭空胖了一个像素。</strong>"),
        MATH("\\text{IoU}_{+1}(A,B) \\;=\\; \\frac{(w_\\cap+1)(h_\\cap+1)}{(w_A+1)(h_A+1)+(w_B+1)(h_B+1)-(w_\\cap+1)(h_\\cap+1)} \\;\\ne\\; \\frac{w_\\cap h_\\cap}{w_A h_A + w_B h_B - w_\\cap h_\\cap} \\;=\\; \\text{IoU}_{0}(A,B)"),
        H3("差多少：一个可以背下来的数字对"),
        P("取两个边长 $s$、沿对角线错开 $d = s/4$ 像素的正方形框（相对位移固定为 25%，这正是同一目标上两个相邻候选框的典型关系）："),
        TABLE(["框边长 $s$", "$\\text{IoU}_0$", "$\\text{IoU}_{+1}$", "差值 $\\Delta$", "在 <code>iou_thr</code> 附近意味着什么"], [
            ["<strong>8 px</strong>（60 m 外的限速牌）", "36/92 = <strong>0.3913</strong>", "49/113 = <strong>0.4336</strong>", "<strong>+0.0423</strong>", "<code>iou_thr</code> 落在 0.39–0.43 之间时，<strong>一边抑制、一边保留</strong>"],
            ["16 px", "0.3913", "0.4132", "+0.0219", "影响减半"],
            ["32 px", "0.3913", "0.4024", "+0.0111", "基本无感"],
            ["<strong>64 px</strong>（近处的大牌）", "2304/5888 = <strong>0.3913</strong>", "2401/6049 = <strong>0.3969</strong>", "<strong>+0.0056</strong>", "永远不会改变抑制决策"],
        ]),
        P("注意左边那一列：<strong>$\\text{IoU}_0$ 在所有尺度上都恰好是 0.3913——它是尺度不变的</strong>（两个相似形的交并比只取决于相对位移 $d/s$）。而 $\\text{IoU}_{+1}$ 不是：那个 $+1$ 是一个<em>绝对</em>像素量，它相对于 8 px 的框是 12.5% 的膨胀，相对于 64 px 的框只有 1.6%。"),
        MATH("\\Delta(s) \\;=\\; \\text{IoU}_{+1}(s) - \\text{IoU}_{0}(s) \\;\\sim\\; \\mathcal{O}\\!\\left(\\tfrac{1}{s}\\right) \\qquad \\text{（notebook 会用数值扫描验证这个 } 1/s \\text{ 衰减）}"),
        DUAL(
            "所以 <code>+1</code> 是一个<strong>只伤害小目标的 bug</strong>。你在 COCO 上跑，AP 差 0.1，觉得「无所谓」；换到 TSR 数据上，标志普遍只有 10–30 像素，同一个不一致就会让两侧的 NMS 在<em>每一个密集场景</em>上给出不同的保留集。<strong>而它在指标上的表现是「小目标桶掉点」——和「模型对小目标不行」长得一模一样。</strong>",
            "把它放到更一般的框架里：<strong>任何绝对像素量级的约定差异，其相对影响都与目标尺寸成反比</strong>。除了 <code>+1</code>，同类的还有：坐标 <code>round</code> 与 <code>floor</code> 的差别（±0.5 px）、letterbox padding 的奇偶取整（±0.5 px）、resize 时 <code>align_corners</code> 的半像素偏移（±0.5 px，见模块 01）。<em>单个都是亚像素级，看起来可以忽略；但它们会叠加，而且全部只在小目标上放大。</em>一个 12 px 的框累计偏 1.5 px，IoU 就掉到 $(10.5)^2/(2\\cdot144-110.25)=0.62$；再叠一个 <code>+1</code> 约定的差异，抑制决策就可能翻转。<strong>这就是为什么本课坚持「逐元素对拍」而不是「肉眼看框画得对不对」——1.5 px 用眼睛看不出来。</strong>",
        ),
        CALLOUT("warn", "<p><strong>不要试图「统一到有 +1」或「统一到没有 +1」然后就完事。</strong>正确的做法是：<em>①确认你的<u>标注</u>用的是哪种坐标语义（VOC 风格的整数像素索引，还是 COCO 风格的连续坐标）；②让训练时的 IoU、评测时的 IoU、部署时 NMS 的 IoU <strong>三者与标注语义一致</strong></em>。最常见的真实事故是<strong>只改了部署侧</strong>——于是部署和训练一致了，但和评测口径不一致，线下测出来的 AP 不再代表线上行为。<em>一致性是三方的，不是两方的。</em></p>", "一致性是「标注 / 训练+评测 / 部署」三方一致"),
        H3("除了 +1，NMS 还有三处「顺序」分歧"),
        P("IoU 的定义只是第一层。NMS 从来不是孤立调用的，它前后有一串筛选步骤——<strong>而这些步骤的<em>顺序</em>不写在任何接口签名里，却完全决定了输出。</strong>"),
        H3("① top-k 放在 NMS 之前还是之后：一个会吃掉密集场景的坑"),
        ASCII("""方案 A（top-k 在 NMS 之后）                方案 B（top-k 在 NMS 之前）
──────────────────────────────           ──────────────────────────────
8400 个候选                                8400 个候选
   │ score_thr = 0.25                         │ score_thr = 0.25
   ▼                                          ▼
 1600 个过阈                                1600 个过阈
   │                                          │ 按分数取 top-300     ← 截断发生在**去重之前**
   │                                          ▼
   │                                        300 个候选（可能全来自 20 个目标！
   │                                          每个目标 15 个重复框）
   ▼ NMS                                      ▼ NMS
 140 个不同目标                              20 个不同目标            ← **静默漏检 86%**
   │ 取 top-300（不截断）
   ▼
 140 个不同目标  ✅

代价：NMS 要处理 1600 个框（慢）        代价：几乎不花时间（快），但结果是错的"""),
        P("方案 B 的致命性在于它<strong>只在密集场景发作</strong>：高速上视野里 2 块标志时，过阈候选可能只有 40 个，300 的 top-k 根本不生效，两个方案输出完全一样；开到城市路口龙门架下，8 块标志 + 一排店铺招牌，过阈候选涨到 1600，top-k 开始咬人。<em>而离线评测集里这种极端帧本来就少，AP 上可能只掉零点几，测不出来。</em>"),
        TABLE(["实现", "典型做法", "截断参数", "语义"], [
            ["<code>ultralytics</code> / YOLOv5-v8", "<code>conf_thres</code> → 按分数取 <code>max_nms=30000</code> → NMS → 取 <code>max_det=300</code>", "30000 / 300", "NMS 前的截断阈值设得极大，实际上不会咬到；<strong>真正的截断在 NMS 之后</strong>"],
            ["<code>mmdetection</code>", "<code>nms_pre</code>（每个 FPN 层级独立取 top-k）→ 合并 → NMS → <code>max_per_img</code>", "1000/层 + 100", "<strong>逐层级</strong>取 top-k，这样小目标层不会被大目标层挤掉"],
            ["TRT <code>EfficientNMS_TRT</code>", "内部先按分数取 topK → NMS → 输出定长 <code>max_output_boxes</code>", "构建期常量", "<strong>topK 是 NMS 前的</strong>；设小了就是方案 B"],
            ["ONNX <code>NonMaxSuppression</code>", "算子本身只有 <code>max_output_boxes_per_class</code>（NMS <em>过程中</em>的上限）", "per-class", "语义又不一样：它在抑制循环里计数，不是先截断"],
        ]),
        CALLOUT("danger", "<p><strong>「我只要 300 个框，那我 topK 就设 300」——这句话是本节最贵的一句话。</strong>把 <code>EfficientNMS</code> 的 <code>topK</code> 从默认的几千调到 300，engine 会小一点、快一点，评测集上 mAP 掉 0.2，看起来是个划算的交易。<em>然后在城市路口，你的 TSR 会成片漏掉标志。</em><strong>正确的设置原则是：NMS <u>前</u>的 topK 要按「单帧最大过阈候选数」留 2–3 倍余量（通常几千），NMS <u>后</u>的 max_det 才按「单帧最大目标数」设（通常几百）。这两个参数解决的是完全不同的问题，名字像但不能互相替代。</strong></p>", "topK（NMS 前）≠ max_det（NMS 后）"),
        H3("② per-class 还是 global"),
        P("top-k 是对<em>所有类别的所有框</em>取，还是<em>每个类别各取 k 个</em>？在 TSR 这种 100–300 类的任务上，差别是数量级的。global top-300 在一帧里如果有 200 个「限速 60」的高分候选，就会把其他所有类别挤到 100 个名额里；per-class top-10 则保证每个类别都有代表，但总数会涨到 $300\\times 10=3000$。<strong>mmdetection 的「逐 FPN 层级 top-k」是第三种切法——它保证的是「小目标层不会被大目标层挤掉」，这对 TSR 比按类别切更有价值。</strong>"),
        H3("③ 排序的稳定性：一个只在 INT8 上出现的诡异分歧"),
        DUAL(
            "分数相同的两个框，谁排前面？<strong>Python 的 <code>np.argsort</code> 默认用 quicksort（不稳定），C++ 的 <code>std::sort</code> 也不稳定，而且两者的「不稳定」方式不同。</strong>FP32/FP16 下这不是问题——浮点分数几乎不会精确相等。但 INT8 模型的输出经过反量化后，<em>取值集合是离散的</em>：一个 per-tensor 量化的分类头，输出只有约 256 个可能值。一帧里 1600 个过阈候选，分数的唯一值可能只有 30 几个，平均每个值挤着 50 个框。<strong>于是 NMS 的第一个「保留」是谁，取决于排序算法的实现细节——两侧输出的框集合会不一样，而且不可复现。</strong>",
            "严格地说，NMS 是一个<span class=\"term\">order-dependent</span>（依赖顺序）的贪心算法：保留集 $\\mathcal{K}$ 由遍历顺序唯一决定，而遍历顺序在存在并列分数时是欠定的。<strong>修法有三档</strong>：<em>①最省事——排序用稳定排序（<code>np.argsort(kind='stable')</code> / <code>std::stable_sort</code>），并保证两侧的输入框顺序也一致（这一条常被忘：稳定排序只保证「相等元素保持输入顺序」，如果输入顺序本身不同，稳定也救不了）；②更稳——把索引作为第二排序键，显式定义全序：<code>key = (-score, flat_index)</code>；③最稳——在 NMS 之前对分数做一次微小的确定性扰动打破并列（不推荐，会污染分数语义）。</em><strong>量产项目应该选 ②：它让 NMS 的输出成为输入的确定性函数，与语言、库、优化等级全部无关。</strong>这也是让端到端对拍能用 <code>==</code> 而不是「差不多」的前提。",
        ),
        CALLOUT("intuition", "把三个顺序问题压成一条检查：<strong>写下你这条管线里「筛选」发生的<em>每一个</em>位置，标注它是按什么排序、截断到多少、发生在 NMS 前还是后。两侧各写一份，对着看。</strong>这张表通常只有 5–6 行，但它能提前消灭本模块一半的坑。"),
    ])),

    # ============================================================== 4
    ("classwise", "class-wise / class-agnostic / 层次化 NMS", "".join([
        P("同一块牌子被检成两个类别时，该保留几个框？这不是一个技术问题，是一个<strong>产品语义问题</strong>——而 NMS 的三种模式正好对应三种不同的回答。"),
        TABLE(["模式", "做法", "同位置不同类的两个框", "紧邻的不同类目标", "谁在用"], [
            ["<strong>class-wise</strong>（per-class）", "按类别分组，组内各做一次 NMS，跨类不抑制", "<strong>全部保留</strong>", "全部保留 ✅", "COCO 评测口径、多数检测框架的默认"],
            ["<strong>class-agnostic</strong>", "所有框一起排序、一起抑制，忽略类别", "只留分数最高的", "<strong>会误删</strong> ❌", "两级架构的第一级、类别互斥场景、部分跟踪前置"],
            ["<strong>层次化 / 超类内 agnostic</strong>", "同一超类内 agnostic，跨超类 class-wise", "同超类只留一个；跨超类都留", "跨超类时保留 ✅", "TSR 等「细类高度互斥、粗类可共存」的任务"],
        ]),
        H3("batched NMS 的 offset trick：一次调用做完 class-wise"),
        P("逐类循环调 NMS 在 GPU 上非常糟糕：80 个类就是 80 次 kernel launch，每次只处理几十个框，全是启动开销。<strong>标准技巧是给每个框的坐标加上 <code>class_id × offset</code>，把不同类别的框推到互不相交的坐标区间，然后做<em>一次</em> class-agnostic NMS</strong>——数学上与 class-wise 严格等价（不同类的框永远不重叠，IoU 恒为 0），但只有一次调用。<code>torchvision.ops.batched_nms</code> 就是这么实现的。"),
        MATH("\\tilde{b}_i \\;=\\; b_i \\;+\\; c_i \\cdot \\Delta \\cdot \\mathbf{1}_4, \\qquad \\Delta \\;>\\; \\max_i \\bigl(\\max(x_{2,i},\\, y_{2,i})\\bigr) \\;\\Longrightarrow\\; \\text{IoU}(\\tilde{b}_i, \\tilde{b}_j) = 0 \\ \\ \\forall\\, c_i \\ne c_j"),
        CALLOUT("danger", "<p><strong>offset trick 有一个真实存在的数值悬崖：float32 的精度会在大坐标上崩掉。</strong>float32 的尾数是 24 位，在数值 $v$ 附近的最小间隔（ULP）约为 $v \\cdot 2^{-23} \\approx 1.2\\times10^{-7} v$。取 $\\Delta = 10^6$、类别 ID 到 1000 时，坐标量级是 $10^9$，此时 <strong>ULP ≈ 64 像素</strong>——一个 8 像素宽的框，$x_1$ 和 $x_2$ 会被舍入到<em>同一个浮点数</em>，宽度变成 0，面积变成 0，IoU 变成 NaN 或 0，<strong>NMS 完全失效但不报任何错</strong>。notebook 里会用 <code>np.float32</code> 把这个悬崖打出来给你看。<em>正确做法：$\\Delta$ 取「图像最大边 + 1」而不是一个拍脑袋的大数；或者干脆用 int32/float64 做坐标运算。另一个更稳的做法是把类别偏移加在<u>整数网格</u>上——先把坐标量化到 int32，加完 offset 再算 IoU。</em></p>", "offset 越大越安全？恰恰相反"),
        H3("TSR 场景：为什么这里必须做层次化"),
        P("交通标志有一个别的检测任务少见的性质：<strong>细类之间在视觉上极度相似，但在语义上互斥</strong>。「限速 60」和「限速 80」的牌子形状一样、颜色一样、位置一样，只有中间的数字不同——而那个数字在 14 像素的牌子上只占 5×7 像素。<em>模型在同一个位置同时输出「限速 60，0.52」和「限速 80，0.47」是完全正常的行为，不是 bug。</em>"),
        UL([
            "<strong>用 class-wise</strong>：两个框都送给下游。下游拿到「这里既是限速 60 又是限速 80」，被迫自己做消歧——<em>而下游（跟踪、地图匹配、规控）根本没有做这件事的信息</em>。真实后果是：车会按哪个限速走？如果规控保守地取小值，那么每次「限速 80 误检成 60」都会造成无谓减速。",
            "<strong>用 class-agnostic</strong>：只留 0.52 那个。干净了，但代价是<em>组合牌被误删</em>——中国道路上「限速 40」下面挂「货车」辅助牌、或者「禁止左转 + 时段说明」上下叠放是常见配置，两块牌子的框在图像上高度重叠（IoU 可以到 0.4 以上），class-agnostic 会把辅助牌整个抹掉。<strong>而辅助牌恰恰承载着限定条件——把「7:00–20:00 限行」的辅助牌删掉，剩下的主牌语义就是错的。</strong>",
            "<strong>层次化</strong>：定义超类 <code>{限速类}</code>、<code>{禁令类}</code>、<code>{辅助牌类}</code>、<code>{指路类}</code>。同超类内 agnostic（限速 60 和限速 80 互相抑制，只留一个 + 把落选类别的分数一并上报给下游做消歧），跨超类 class-wise（主牌和辅助牌互不抑制）。<strong>这是唯一同时解决两个问题的模式。</strong>",
        ]),
        DUAL(
            "选哪个模式，取决于你对「这两个框可不可能同时为真」的物理判断。<strong>同一块物理牌子不可能既是限速 60 又是限速 80——所以它们该互相抑制；一块主牌和它下面的辅助牌是两块物理牌子——所以它们不该互相抑制。</strong>NMS 的模式选择本质上是在编码「什么东西在物理世界里能共存」这个先验。",
            "工程上还要多做一件事：<strong>被抑制的框不该直接丢掉，应该把它的类别与分数作为「竞争假设」附在保留框上传给下游</strong>。理由是时序——单帧上「60 得 0.52 / 80 得 0.47」几乎是抛硬币，但连续 10 帧的累积证据可以把它分开（C55 模块 04 的多帧投票）。<em>如果你在 NMS 里就把 0.47 那个丢了，下游永远拿不到这个信息，多帧融合就退化成「对单帧硬判决做投票」，而不是「对单帧似然做累积」——后者的收敛速度和抗噪能力都显著更好。</em><strong>换句话说：NMS 的输出接口不该是「框 + 一个类别」，而该是「框 + 一个超类内的类别分布」。</strong>这一点在把感知结果送进 VLA 时同样关键（C59 模块 03）。",
        ),
    ])),

    # ============================================================== 5
    ("decode", "解码约定：激活函数、坐标格式与归一化", "".join([
        P("模型的输出张量是一堆没有类型信息的浮点数。<strong>「它们是什么」完全靠约定，而约定不在张量里。</strong>这一节把四类约定逐一列出，每类都给「弄错的症状」。"),
        H3("① sigmoid / softmax 在模型内还是模型外"),
        P("把激活放进 ONNX 的好处是 C++ 端不用做、也不会做错；坏处是<strong>如果 Python 侧的后处理仍然按老习惯再做一次，你就得到了 $\\sigma(\\sigma(x))$</strong>。这个 bug 值得单独拿出来讲，因为它是本模块最阴险的一个："),
        MATH("\\sigma(\\sigma(x)) \\in \\bigl(\\sigma(0),\\ \\sigma(1)\\bigr) = (0.500,\\ 0.731) \\qquad \\forall\\, x \\in \\mathbb{R}"),
        UL([
            "<strong>所有分数都被压进 (0.5, 0.731)</strong>。你设的 <code>score_thr = 0.3</code> 于是<em>一个框都筛不掉</em>——8400 个候选全部过阈。",
            "<strong>mAP 几乎不变。</strong>因为 $\\sigma$ 是严格单调的，<em>排序完全不受影响</em>，而 AP 是纯粹基于排序的指标。<strong>所以离线评测报告是绿的。</strong>",
            "线上表现：候选数从 1600 涨到 8400 → NMS 耗时涨一个量级（$O(NK)$，见 C53 模块 04）→ 延迟 p99 爆表；同时误检率暴涨，因为所有背景框都过了阈值。",
            "<strong>诊断只要一行</strong>：打印全部分数的 <code>min()</code>。如果最小值大于 0.5，你就抓到它了。",
        ]),
        CALLOUT("warn", "反过来的错误同样常见：模型输出的是 <strong>logits</strong>（没有做 sigmoid），而 C++ 端直接拿去和 <code>score_thr=0.3</code> 比。logit 0.3 对应的概率是 $\\sigma(0.3)=0.574$——<em>阈值被无意中抬高了近一倍</em>，症状是召回莫名其妙地掉，尤其是远处小目标（它们的置信度本来就低）。<strong>这两个错误的方向相反，但都不会报错。唯一可靠的防线是在对拍框架里把「模型原始输出」和「激活后分数」当成两个独立阶段分别比对</strong>（见第 8 节）。"),
        H3("② softmax 有背景类，sigmoid 没有"),
        P("多类互斥头（softmax）通常有一个 background / no-object 类占据 index 0，前景类别从 1 开始；多标签头（sigmoid）每个通道就是一个前景类，从 0 开始。<strong>换头不改后处理 = 全部类别 ID 偏移 1</strong>——症状是 mAP 恒为 0 或极低，且预测类别的分布整体平移。这是「mAP 恒为 0」的三大成因之一（另两个见 C61 模块 03）。"),
        H3("③ 坐标格式：四种，没有一种自带标签"),
        TABLE(["格式", "含义", "谁在用", "当成 xyxy 用会怎样"], [
            ["<code>xyxy</code>", "$(x_1,y_1,x_2,y_2)$ 左上-右下", "Detectron2、torchvision、评测代码", "—"],
            ["<code>xywh</code>", "$(x_1,y_1,w,h)$ 左上+宽高", "<strong>COCO 标注文件</strong>", "$x_2$ 被当成 $w$：$w &lt; x_1$ 时框变成负面积 → IoU 恒为 0 → <strong>NMS 完全不抑制，满屏重复框</strong>"],
            ["<code>cxcywh</code>", "$(c_x,c_y,w,h)$ 中心+宽高", "<strong>YOLO 标签、DETR 输出</strong>", "像素坐标下 $w \\ll c_x$ → 同样是负面积（与 <code>xywh</code> 同症状）；<strong>归一化坐标下则是框整体挤向左上角</strong>"],
            ["<code>yxyx</code>", "$(y_1,x_1,y_2,x_2)$", "TensorFlow、<strong>部分 TRT plugin</strong>", "框沿主对角线镜像 → 画出来一眼可见，但如果图是近似正方形就不那么明显"],
        ]),
        H3("④ 归一化坐标 vs 像素坐标，以及「相对于谁」"),
        P("这是四类里最容易出「安静失败」的一类。归一化坐标要回答一个额外的问题：<strong>相对于哪张图归一化？</strong>"),
        UL([
            "<strong>相对网络输入（含 padding 的 640×640）</strong>：DETR 系与多数导出脚本的默认。逆变换要先乘 640，再减 pad，再除 $r$。",
            "<strong>相对 letterbox 内的有效区域（640×360）</strong>：少数实现如此。逆变换只要乘原图尺寸。",
            "<strong>相对原图（1920×1080）</strong>：模型内部已经做完逆变换（有些导出脚本会把 $r$ 和 pad 作为常量折进图里）。这时 C++ 端<em>再做一次</em>逆变换就是灾难。",
        ]),
        P("前两者之间只差一个 letterbox 比例——<strong>框会整体偏 10–20%，mAP 掉 5–10 点，看起来完完全全像「模型不行」</strong>。而「归一化当像素用」（框全挤在左上 1×1 像素里）和「像素当归一化用」（框被 clip 成全图一个大框）这两种是<em>响亮失败</em>，反而三秒就能发现。<strong>响亮的 bug 是好 bug；本模块真正要防的是安静的那些。</strong>"),
        H3("完整的坐标变换链"),
        MATH("b_{\\text{orig}} \\;=\\; \\operatorname{clip}_{[0,W]\\times[0,H]}\\Bigl(\\ \\tfrac{1}{r}\\bigl(\\ \\underbrace{T_{\\text{fmt}}(b_{\\text{net}})}_{\\text{③ 格式转换}} \\odot \\underbrace{s}_{\\text{④ 归一化尺度}} \\;-\\; \\underbrace{p}_{\\text{⑤ letterbox pad}}\\ \\bigr)\\ \\Bigr)"),
        DUAL(
            "五个环节：格式（xyxy/cxcywh/…）、尺度（归一化还是像素）、pad、缩放比、clip 范围。<strong>任何一个环节两侧不一致，结果就错；而它们都不会报错。</strong>五个二值/多值选择组合起来是几十种可能的管线，其中只有一种是对的。",
            "工程上唯一可靠的做法是<strong>把这条变换链写成一个显式的、有单元测试的数据结构</strong>，而不是散落在代码里的几行算术。具体地：定义一个 <code>CoordTransform</code> 对象，字段是 $(r, p_x, p_y, W_{\\text{net}}, H_{\\text{net}}, W_{\\text{orig}}, H_{\\text{orig}}, \\text{fmt}, \\text{normalized})$，由预处理阶段<em>生成并随帧传递</em>，后处理阶段直接消费。<strong>关键在于「随帧传递」——它保证了逆变换用的参数一定是这一帧正变换时用的参数</strong>，而不是从配置文件里重新读一遍（配置文件读错、或者动态分辨率下参数变了没同步，都是真实事故）。再给它配一条不变量测试：<code>inverse(forward(b)) ≈ b</code> 对随机框成立到 $10^{-6}$。<em>这条往返测试能在 CI 里挡住本节几乎所有的坑，代价是 20 行代码。</em>",
        ),
    ])),

    # ============================================================== 6
    ("letterbox-inv", "letterbox 逆变换：「框整体偏移」的头号成因", "".join([
        P("上一节把变换链写出来了，这一节把最容易写错的那一环单独拆开——因为它贡献了「框整体偏移」这类症状的绝大多数。"),
        ASCII("""原图 1920 x 1080                       letterbox 到 640 x 640
┌──────────────────────────┐          ┌────────────────────────┐
│                          │          │████████████████████████│ ← pad_h = 140
│      ┌────┐              │          │████████████████████████│
│      │ 牌 │              │   r =    ├────────────────────────┤
│      └────┘              │  1/3     │      ┌──┐              │ 有效区域 640 x 360
│                          │  ────►   │      │牌│              │
│                          │          │      └──┘              │
└──────────────────────────┘          ├────────────────────────┤
   (x, y) 原图坐标                     │████████████████████████│ ← pad_h = 140
                                       │████████████████████████│
                                       └────────────────────────┘
                                          (x', y') 网络坐标

正变换:  x' = r·x + pad_w        逆变换:  x = (x' - pad_w) / r
         y' = r·y + pad_h                 y = (y' - pad_h) / r
                                          ↑ **先减 pad，再除 r。顺序反了就错。**"""),
        MATH("r = \\min\\!\\left(\\tfrac{W_{\\text{net}}}{W},\\ \\tfrac{H_{\\text{net}}}{H}\\right),\\quad p_x = \\tfrac{W_{\\text{net}} - rW}{2},\\quad p_y = \\tfrac{H_{\\text{net}} - rH}{2},\\quad b_{\\text{orig}} = \\frac{b_{\\text{net}} - (p_x,p_y,p_x,p_y)}{r}"),
        H3("五个错误版本与它们各自的偏移量"),
        P("下表取 $1920\\times1080 \\to 640\\times640$，于是 $r=1/3$、$p_x=0$、$p_y=140$。测试框在网络坐标下是 $[100,200,140,240]$，正确还原是 $[300,180,420,300]$："),
        TABLE(["错误版本", "写法", "还原结果", "偏移量（解析式）", "在这组参数下"], [
            ["<strong>E1 · 漏减 pad</strong>", "<code>b / r</code>", "[300, <strong>600</strong>, 420, <strong>720</strong>]", "$+p_y/r$（常数）", "<strong>y 偏 +420 px</strong>"],
            ["<strong>E2 · 顺序反</strong>", "<code>b / r - p</code>", "[300, <strong>460</strong>, 420, <strong>580</strong>]", "$+p_y(1-r)/r$", "<strong>y 偏 +280 px</strong>"],
            ["<strong>E3 · pad 减了两遍</strong>", "<code>(b - 2p) / r</code>", "[300, <strong>-240</strong>, 420, <strong>-120</strong>]", "$-p_y/r$", "<strong>y 偏 -420 px</strong>（框跑到图外）"],
            ["<strong>E4 · 用 stretch 比例</strong>", "<code>b / (W_net/W, H_net/H)</code>", "[300, <strong>337.5</strong>, 420, <strong>405</strong>]", "非线性，宽高比失真", "y 方向被压缩 $r\\cdot H/H_{\\text{net}}$ 倍"],
            ["<strong>E5 · clip 位置错</strong>", "先 clip 到 $[0,640]$ 再逆变换", "pad 区域的框被留下", "边界框被错误保留", "上下 140 px 的假框不会被剔除"],
        ]),
        P("E1 和 E3 偏得太狠（一眼就能看出来），E2 也不算隐蔽。<strong>真正在量产里活很久的是 E4 和 E5，以及第三类：亚像素级的取整分歧。</strong>"),
        H3("亚像素分歧：为什么 1 px 也要管"),
        P("$1080 \\times \\tfrac13 = 360$ 是整数，很干净。但换一个分辨率，比如 $1920\\times1084 \\to 640$：$r = 1/3$，$rH = 361.33$，实现必须取整——<code>round</code> 得 361，<code>floor</code> 得 361，<code>ceil</code> 得 362。于是 $p_y = (640-361)/2 = 139.5$，而 padding 必须是整数像素：一侧 139、另一侧 140。<strong>逆变换该减 139 还是 139.5？两者差 0.5 px；而且实际的垂直缩放比是 $361/1084 = 0.33303$，不是名义的 $0.33333$。</strong>"),
        MATH("\\text{IoU}\\bigl(b,\\ b + (\\delta,\\delta)\\bigr) \\;=\\; \\frac{(s-\\delta)^2}{2s^2 - (s-\\delta)^2} \\qquad\\Longrightarrow\\qquad \\begin{cases} s=12,\\ \\delta=4: & \\text{IoU} = \\tfrac{64}{224} = \\mathbf{0.286} \\\\[2pt] s=100,\\ \\delta=4: & \\text{IoU} = \\tfrac{9216}{10784} = \\mathbf{0.855} \\end{cases}"),
        CALLOUT("danger", "<p><strong>这两个数字是本模块最该背下来的一对。</strong>同样一个 4 像素的系统性偏移：在 100 px 的近处大牌上，IoU 还有 <strong>0.855</strong>，在任何评测口径下都算命中，你<em>永远不会发现</em>；在 12 px 的远处小牌上，IoU 只有 <strong>0.286</strong>，在 IoU=0.5 的口径下<strong>直接算完全漏检</strong>。<em>于是你的报告上写着「小目标 AP 从 0.41 掉到 0.19，大目标 AP 不变」，而你会开始怀疑输入分辨率、怀疑 P2 层、怀疑 anchor 设置——因为这个指标形态和「模型对小目标不行」完全一样。</em><strong>TSR 是这个陷阱的完美受害者：它的目标常年在 10–30 px，而它的评测集里近处大牌又足够多，足以让总体 mAP 只掉几个点而不是崩掉。</strong>结论：<u>凡是「只有小目标桶掉点」，第一个怀疑对象永远是坐标变换，而不是模型能力。</u></p>", "4 px 偏移：大牌 0.855，小牌 0.286"),
        DUAL(
            "所以逆变换的正确性不能靠「画出来看着对」——4 像素在一张 1920 宽的图上是肉眼不可见的。<strong>唯一可靠的验证是往返测试：随机生成原图坐标的框，正变换到网络坐标，再逆变换回来，要求误差 &lt; $10^{-6}$。</strong>这条测试 20 行，能挡住 E1–E4 全部四种错法。",
            "E5 需要单独一条测试，因为它不是数值错误而是<strong>语义</strong>错误：clip 的作用是「把框限制在<em>真实图像</em>范围内」。在网络坐标下 clip 到 $[0, 640]$，等价于允许框延伸到 padding 区域——而 padding 区域在原图上根本不存在。<em>正确顺序是先逆变换回原图坐标，再 clip 到 $[0,W]\\times[0,H]$。</em><strong>更彻底的做法是在 clip 之前先做一次「有效性过滤」：逆变换后宽或高 $\\le 1$ 像素的框直接丢弃</strong>——因为一个被 clip 到只剩 1 px 宽的框，说明它原本几乎完全在图外，属于边缘伪检。<em>在 TSR 里这条过滤特别有用：图像边缘常有半个标志（正在驶出视野），它们的框会被 clip 得很扁，而这类残缺目标的分类结果基本不可信，早点丢掉比送给下游做多帧融合更安全。</em>",
        ),
    ])),

    # ============================================================== 7
    ("gpu-cpu", "后处理放 GPU 还是 CPU：拷贝量、plugin 与可调试性", "".join([
        P("后处理的物理位置有三种选择，它们的差别不在「快多少」，而在<strong>要搬多少字节过 PCIe/内存总线</strong>——这一项常常比计算本身贵得多。"),
        P("先把账算清楚。一个 TSR 检测器，640×640 输入、三尺度 8400 个位置、200 个类别，raw 输出张量是 $8400 \\times (4 + 200) = 1{,}713{,}600$ 个 float16，约 <strong>3.43 MB</strong>（float32 则是 6.85 MB）："),
        TABLE(["方案", "D2H 拷贝量", "GPU 侧做什么", "CPU 侧做什么", "延迟（示意）", "可调试性"], [
            ["<strong>A · 全 CPU</strong>", "<strong>3.43 MB</strong>", "什么都不做", "sigmoid ×168 万、阈值、解码、NMS", "拷贝 0.21 ms + CPU 2–6 ms", "<strong>最好</strong>（每一步都能打印）"],
            ["<strong>B · GPU 解码 + CPU NMS</strong>", "<strong>~24 KB</strong>（1000 个候选 × 6 float）", "sigmoid、阈值、top-k、格式转换", "只做 NMS（输入已经很小）", "拷贝 ~0.002 ms + CPU 0.2 ms", "较好（能 dump 中间的候选集）"],
            ["<strong>C · 全 GPU（EfficientNMS plugin）</strong>", "<strong>~7 KB</strong>（定长 300 框）", "全部，包括 NMS", "只做逆变换", "&lt; 0.3 ms，且<strong>方差极小</strong>", "<strong>最差</strong>（中间量看不见）"],
        ]),
        P("<strong>从 A 到 B，拷贝量降了约 140 倍，而它只需要在 GPU 上写一个几十行的 decode kernel。</strong>这是整条管线里性价比最高的优化之一——比换模型、比调量化都便宜得多。<em>C53 模块 05 和本课模块 05 会反复回到这个主题：新手优化模型，老手先量拷贝。</em>"),
        H3("EfficientNMS plugin：它到底把什么写死了"),
        P("TensorRT 的 <code>EfficientNMS_TRT</code> 把「阈值 + topK + NMS」整个塞进一个 plugin 节点，输出四个定长张量 <code>num_dets / boxes / scores / classes</code>。它的所有语义参数都是<strong>构建期常量</strong>——改任何一个都要重新构建 engine（几分钟到几十分钟）："),
        TABLE(["参数", "含义", "写错的后果"], [
            ["<code>box_coding</code>", "0 = <code>xyxy</code>，1 = <code>cxcywh</code>", "框全部错位（见第 5 节）"],
            ["<code>score_activation</code>", "plugin 内部是否再做一次 sigmoid", "<strong>正是第 5 节的 $\\sigma(\\sigma(x))$ 事故</strong>"],
            ["<code>class_agnostic</code>", "是否跨类抑制", "TSR 的组合牌被误删，或限速类不去重"],
            ["<code>score_threshold</code>", "过阈阈值", "工作点被冻结在 engine 里，调阈值 = 重建 engine"],
            ["<code>iou_threshold</code>", "抑制阈值", "同上"],
            ["<code>max_output_boxes</code>", "输出定长上限（NMS <em>后</em>）", "密集场景截断"],
            ["内部 topK", "NMS <em>前</em>的候选上限（版本相关，常见默认几千）", "<strong>第 3 节那个吃掉密集场景的坑</strong>"],
        ]),
        CALLOUT("warn", "<p><strong>把阈值烧进 engine 是一个经常被低估的代价。</strong>检测器的工作点（score 阈值）不是一次定死的：上线后你会根据路测的 FP/km 反复微调，会为不同车型/不同区域配不同的值，会在雨天动态放宽。<em>如果阈值在 plugin 里，每一次微调都要走「重建 engine → 重新验证 → 重新发版」的完整流程</em>，而 engine 还和 GPU 型号 + 驱动 + TRT 版本绑定（模块 02），意味着每个硬件平台都要重建一遍。<strong>实践中常见的折中是：plugin 里把 <code>score_threshold</code> 设得很低（比如 0.01，只用来控计算量），真正的工作点阈值留在 plugin 之外的 C++ 里做二次过滤。</strong>这样既拿到了 GPU NMS 的延迟收益，又保住了阈值的可运行时调整。</p>", "别把可调参数烧进 engine"),
        DUAL(
            "所以三种方案不是「选一个」，而是<strong>同时保留两条路</strong>：一条 <em>debug engine</em> 输出 raw tensor（方案 A/B），一条 <em>release engine</em> 内含 plugin（方案 C）。发布前用对拍工具验证两条路在同一批图上输出一致；线上跑 release，出问题时切 debug 复现。<em>两个 engine 从同一份 ONNX 构建，多花的只是几分钟构建时间。</em>",
            "更严格的做法是把「后处理」定义成一份<strong>与实现无关的规格（spec）</strong>：明确写下激活函数、阈值顺序、topK 位置与语义、IoU 的边界约定、NMS 模式与超类划分、坐标格式与变换链、clip 与丢弃规则。然后<em>三份实现（Python 参考 / C++ 手写 / TRT plugin 配置）都必须通过同一套 spec 测试用例</em>。<strong>这套测试用例应该包含精心构造的边界样本</strong>：IoU 恰好等于阈值的一对框（测 <code>&gt;</code> vs <code>&gt;=</code>）、分数完全相同的一对框（测排序稳定性）、面积为 0 的退化框、坐标为负的框、超出图像边界的框、单帧候选数超过 topK 的密集帧。<em>这些用例每一个都对应本模块讲过的一个坑，加起来不到 200 行，却是整条部署链路上投入产出比最高的代码。</em>",
        ),
    ])),

    # ============================================================== 8
    ("cpp-pipeline", "C++ 推理管线：内存、流、线程与相机对接", "".join([
        P("到这里语义都对齐了，剩下的是「怎么把它跑起来还跑得稳」。这一节讲 C++ 侧的结构——<strong>面试里问「你写过 C++ 推理管线吗」，考的不是你会不会写 <code>cudaMemcpy</code>，而是你知不知道哪些事在稳态运行期是禁止做的。</strong>"),
        ASCII("""┌─ Camera (30 FPS, 硬件同步) ─► ISP ─► dmabuf ─┐
│                                              │  ← 零拷贝：dmabuf/EGLImage 直接映射给 CUDA
│  ┌───────────────────────────────────────────▼──────────────────┐
│  │  Frame ring buffer  (N = 3~4)   {ptr, stride, ts_exposure}   │  队列满 → **丢最老的**
│  └───────────────────────────────────┬──────────────────────────┘
│                                      │
│   [stage 1] 预处理 (GPU kernel / VIC / DLA)                        stream_0
│     letterbox + BGR→RGB + uint8→fp16 + HWC→CHW  融合成 1 个 kernel
│                                      ▼
│  ┌── device in_buf [2] ──┐  双缓冲：第 k 帧在算时，第 k+1 帧在填
│  └───────────────────────┘
│                                      │
│   [stage 2] context->enqueueV3(stream_0)   ← **异步返回，不阻塞**
│                                      ▼
│  ┌── device out_buf [2] ─┐
│  └───────────────────────┘
│                                      │
│   [stage 3] 后处理 kernel (decode + NMS) ──► D2H(7 KB, pinned, async)
│                                      ▼
│                        cudaStreamSynchronize(stream_0)   ← **每帧唯一的同步点**
│                                      ▼
│  └─► 结果队列 {boxes, scores, classes, ts_exposure, frame_id}
│           │
│           └─► 跟踪 ─► 时序融合 ─► 地图匹配 ─► 规控 / VLA
└─────────────────────────────────────────────────────────────────"""),
        H3("① 内存：稳态期不许分配"),
        UL([
            "<strong><code>cudaMalloc</code> 在稳态运行期是禁止的。</strong>它不只是慢——它会<em>隐式同步整个 device</em>，把你精心搭的异步流水线拦腰截断，制造几毫秒的延迟尖峰。所有 device buffer 必须在初始化阶段一次性分配好。",
            "<strong>动态 shape 下按 max profile 分配。</strong>模块 02 讲的 min/opt/max 三档，内存要按 max 那档算，运行时只改 <code>setInputShape</code>，不重新分配。",
            "<strong>Host 侧必须用 pinned memory</strong>（<code>cudaHostAlloc</code>）。这一条最常被忽略：<em><code>cudaMemcpyAsync</code> 作用在 pageable memory 上时，实际行为是<strong>同步的</strong></em>——driver 必须先把数据搬到一个内部的 staging buffer。<strong>「我明明用了 Async 为什么还是阻塞」的标准答案就是这个。</strong>",
            "<strong>输出 buffer 双缓冲。</strong>第 $k$ 帧的结果还在被后处理消费时，第 $k+1$ 帧的推理已经在写输出了——单缓冲会数据竞争，而这种竞争在低负载时不会发作，只在延迟抖动大时偶发，是最难查的一类 bug。",
        ]),
        H3("② 流与同步：每帧只允许一个同步点"),
        P("一条 CUDA stream 内部是严格顺序的，所以「预处理 kernel → enqueue → 后处理 kernel → D2H」放同一条 stream 就<strong>不需要任何显式同步</strong>，GPU 会自己保证顺序。<em>整帧唯一需要 <code>cudaStreamSynchronize</code> 的地方，是 CPU 要读取最终结果的那一刻。</em>"),
        CALLOUT("danger", "<p><strong>中间插同步 = 流水线断流。</strong>最常见的写法错误是「为了调试方便」在每个阶段后面加一句 <code>cudaDeviceSynchronize()</code>，然后忘了删。症状是：单帧延迟没变多少（因为工作量没变），但<strong>吞吐掉一半</strong>——因为 CPU 与 GPU 完全串行了，CPU 提交下一帧的时间无法与 GPU 执行当前帧重叠。<em>更隐蔽的同步点还有：<code>cudaMemcpy</code>（非 Async 版）、<code>cudaMalloc/cudaFree</code>、对 device memory 的 <code>cudaMemset</code>（非 Async）、以及 profiler 工具本身。</em><strong>排查方法：用 Nsight Systems 看时间线上 CPU 与 GPU 的重叠度；如果两条泳道是交替而不是重叠的，就有多余的同步。</strong></p>", "多余的同步：延迟没变，吞吐减半"),
        H3("③ 零拷贝：在车端 SoC 上不是「一定更好」"),
        DUAL(
            "Jetson/Orin 这类 SoC 上 CPU 和 GPU 共享同一块物理 DRAM，理论上完全不需要 H2D 拷贝——用 <code>cudaHostAllocMapped</code> 或统一内存，GPU 直接读 CPU 写的那块内存就行。相机的 dmabuf 也可以直接映射给 CUDA，省掉「ISP 输出 → CPU buffer → GPU buffer」这两跳。<strong>省下的是每帧 1–4 MB 的搬运。</strong>",
            "但零拷贝有两个真实代价，忽略它们会得到反效果。<em>①<strong>缓存一致性</strong></em>：mapped pinned memory 在 Orin 上通常是 uncached 或 write-combined 的，<strong>CPU 读它会非常慢</strong>（每次都要走 DRAM，没有 cache 命中）。如果你的 CPU 侧还要遍历这块内存做点什么，代价可能远超省下的拷贝。<em>②<strong>访问带宽</strong></em>：GPU 访问 mapped host memory 的有效带宽低于访问 device memory，如果这块数据要被 kernel 反复读取（比如预处理 kernel 多次采样输入图），零拷贝反而更慢。<strong>正确的判据是「这块数据被读几次」</strong>：只读一次（比如从相机 buffer 读一遍做 letterbox）→ 零拷贝划算；要反复读 → 老老实实拷到 device memory。<em>这也是为什么典型管线里「相机 → 预处理输入」用零拷贝，而「预处理输出 → 推理输入」用普通 device memory。</em>",
        ),
        H3("④ 线程模型：吞吐优化和延迟优化是对立的"),
        TABLE(["模型", "结构", "吞吐", "<strong>单帧延迟</strong>", "适用"], [
            ["单线程串行", "预处理 → 推理 → 后处理，一帧走完再下一帧", "低", "<strong>最低</strong>", "<strong>车端首选</strong>：延迟可预测，无排队"],
            ["双缓冲 2 线程", "线程 A 填下一帧输入，线程 B 等当前帧结果", "中", "略高（+ 一次锁）", "预处理在 CPU 上很重时"],
            ["3 阶段流水线", "预处理 / 推理 / 后处理各一线程，队列串联", "<strong>最高</strong>", "<strong>最高</strong>（约 3× 单阶段最大值）", "离线批处理、数据挖掘"],
            ["多流并发", "N 条 stream 同时跑 N 帧", "高", "高且抖动大", "多相机、多模型共享 GPU"],
        ]),
        P("<strong>这张表的核心是第四列。</strong>3 阶段流水线把吞吐提到接近「最慢那一级的倒数」，但每一帧要依次穿过三个队列，端到端延迟变成三段之和（还要加排队）。<em>数据中心要吞吐，车端要延迟——所以数据中心的最佳实践搬到车端常常是错的。</em>面试里能主动指出「这两个目标是对立的，我们优化的是哪一个」，比会背 CUDA API 有价值。"),
        H3("⑤ 与相机管线对接的四个细节"),
        UL([
            "<strong>时间戳必须是「曝光中点」而不是「帧到达时刻」。</strong>下游的时序融合、运动补偿、与 IMU/定位的对齐全都依赖这个时间戳。用到达时刻会引入一个随系统负载波动的偏差——<em>而这个偏差直接变成标志位置的估计误差</em>：车速 100 km/h 时，10 ms 的时间戳误差就是 0.28 m 的纵向位置误差。",
            "<strong>队列满时丢最老的帧，不能丢最新的。</strong>感知的价值随时间衰减，一帧 100 ms 前的图像对规控几乎无用。反直觉的是很多默认队列实现是「满了就阻塞」或「丢新的」。",
            "<strong>丢帧必须被计数并上报。</strong>静默丢帧会让下游的多帧融合逻辑（C55 模块 04）误以为目标消失了，触发错误的「lost」状态转移。正确做法是把 <code>frame_id</code> 传下去，让下游知道中间跳过了几帧。",
            "<strong>多相机要么硬件同步，要么在下游按时间戳重采样。</strong>前视长焦和前视广角如果差 15 ms，同一块标志在两路上的位置差可达十几像素，跨相机关联会失败。",
        ]),
        CALLOUT("intuition", "C++ 管线的一句话心法：<strong>初始化时把所有能分配的都分配掉，稳态期只做「算」不做「管」。</strong>凡是运行期还在 malloc / 同步 / 创建对象的地方，都是未来延迟尖峰的来源。"),
    ])),

    # ============================================================== 9
    ("e2e-diff", "端到端对拍：从图像文件到最终框", "".join([
        P("前面八节列出了大约二十个可能的分歧点。<strong>你不需要记住它们——你需要一个能在 30 分钟内把任意一个揪出来的工具。</strong>这一节讲这个工具怎么设计。"),
        H3("核心原则：固定输入，逐阶段比对，二分定位"),
        P("对拍不是「跑一遍看框对不对」，而是把管线切成有序的阶段，<strong>每个阶段 dump 一个张量，两侧逐元素比</strong>。第一个超出容差的阶段，就是 bug 所在。八个阶段用二分只要 3 步。"),
        TABLE(["#", "阶段", "张量 / 内容", "容差", "超差时最可能的病因"], [
            ["1", "图像解码", "<code>uint8 [H,W,3]</code>", "<code>max_abs_diff ≤ 1</code> 且失配率 ≤ 0.1%", "JPEG 解码器不同（libjpeg-turbo vs nvjpeg 的 IDCT 实现）；<strong>BGR/RGB 顺序</strong>"],
            ["2", "resize / letterbox 后", "<code>uint8 [640,640,3]</code>", "<code>max_abs_diff ≤ 2</code>", "<strong>插值方式（INTER_LINEAR vs INTER_AREA）、<code>align_corners</code>、pad 值与位置</strong>（模块 01）"],
            ["3", "归一化后", "<code>fp32 [1,3,640,640]</code>", "相对误差 ≤ 1e-5", "mean/std 数值、除 255 的时机、通道顺序、NCHW 转置"],
            ["4", "模型 raw 输出", "<code>fp16 [1,8400,204]</code>", "余弦相似度 ≥ 0.999 且 <code>max_abs</code> 按量化档设", "量化误差（正常）；<strong>超出预期则是 engine 或输入不同</strong>"],
            ["5", "激活后分数", "<code>fp32 [8400,200]</code>", "相对误差 ≤ 1e-4", "<strong>sigmoid 做了几次 / softmax vs sigmoid / 背景类偏移</strong>"],
            ["6", "过阈候选集", "<code>(N,6)</code> + <strong>N 本身</strong>", "N 完全相等；框 ≤ 1e-4", "<strong>score_thr 数值、topK 位置与大小、per-class vs global</strong>"],
            ["7", "NMS 保留集", "<code>(K,6)</code> + <strong>K 本身</strong>", "<strong>集合完全相等</strong>", "<strong>IoU 的 +1、iou_thr、class-wise/agnostic、排序稳定性</strong>"],
            ["8", "逆变换到原图", "<code>(K,6)</code>", "坐标 ≤ 0.5 px", "<strong>letterbox 逆变换、clip 范围与顺序、坐标格式</strong>"],
        ]),
        CALLOUT("warn", "<p><strong>第 4 阶段的容差是整套工具里最需要动脑的一格。</strong>如果你的 Python 侧跑 PyTorch、C++ 侧跑 INT8 engine，那么第 4 阶段的差异里<em>混进了量化误差</em>——它本来就该有差异，你无法据此判断后面的分歧是谁造成的。<strong>正确做法是让 Python 侧也通过 TRT 的 Python API 加载<u>同一个 engine</u> 跑推理</strong>。这样第 4 阶段的两侧应当逐位相同（或只差非确定性 kernel 的 $10^{-6}$），<em>模型层被彻底排除，剩下的差异必然来自预处理或后处理</em>。这一步是把「三层鸿沟」压缩成「两层」的关键操作，也是很多团队的对拍工具用不起来的原因——他们比的是两个不同的模型。</p>", "对拍必须让模型层完全相同"),
        H3("工具的工程形态"),
        UL([
            "<strong>C++ 侧编译一个 <code>--dump-stage=N</code> 的 debug 模式</strong>，把指定阶段的张量写成 <code>.npy</code>。<em>不需要依赖任何库——npy 格式的写入器自己实现只要约 100 行</em>（一个固定的魔数头 + shape/dtype 描述 + 裸数据）。",
            "<strong>Python 侧一个脚本读进来逐阶段比</strong>，输出一张表：阶段名 / 是否通过 / 最大差异 / 失配元素占比 / 定位提示。",
            "<strong>把它接进 CI</strong>：每次改动后处理代码，用固定的 5–10 张回归图跑一遍对拍，全绿才允许合并。<em>这是本模块所有内容里唯一能<strong>防止</strong>问题（而不是修复问题）的一条。</em>",
            "<strong>回归图要精心选</strong>：一张稀疏帧、一张密集帧（候选数逼近 topK）、一张有并列分数的 INT8 帧、一张目标贴边缘的帧、一张极端长宽比的帧（触发 letterbox 的非对称 pad）。<em>每一张都对应本模块的一个坑。</em>",
        ]),
        DUAL(
            "为什么是「逐阶段」而不是「最后比框」？因为<strong>最后比框只能告诉你「不一样」，不能告诉你「哪里不一样」</strong>。而后处理有二十个可能的分歧点，靠猜的期望代价是十次尝试；靠二分是三次。<em>更重要的是：某些分歧在最终框上会互相抵消或被掩盖</em>——比如 topK 截断掉了一批低分框，而这些框本来也会被 NMS 抑制，最终框完全相同；但换一帧密集图它就发作了。<strong>逐阶段对拍能抓到这种「潜伏的」不一致。</strong>",
            "这套方法的理论基础是把管线看成函数复合 $f = f_8 \\circ \\cdots \\circ f_1$，两侧的差异 $\\|f^{\\text{py}}(x) - f^{\\text{cpp}}(x)\\|$ 是各级差异沿链条传播与放大的结果。<strong>逐阶段比对等价于对每个 $f_i$ 单独做等价性检验，把一个复合函数的调试问题分解成 8 个独立的单元测试。</strong><em>容差的设定要考虑传播</em>：第 3 阶段 $10^{-5}$ 的相对误差，经过模型可能被放大到第 4 阶段的 $10^{-3}$（取决于网络的 Lipschitz 常数），再经过 NMS 这种<strong>不连续</strong>的算子可能变成第 7 阶段的「保留集完全不同」。<em>所以第 6、7 阶段的容差必须是「离散的相等」而不是「数值接近」</em>——候选数 N 差 1 个就是不通过，因为 NMS 之后它可能变成几十个框的差别。<strong>这个「在不连续算子处收紧容差」的原则，适用于任何含有排序、阈值、argmax 的管线。</strong>",
        ),
        CALLOUT("intuition", "本模块的终极结论：<strong>后处理一致性不是靠「小心」保证的，是靠「工具 + CI + spec 测试用例」保证的。</strong>一个新人写 C++ 后处理时会踩本模块的每一个坑——这不是他的问题，是流程的问题。<em>对拍工具应该在项目第一天就存在，而不是第一次出事之后。</em>"),
    ])),

    # ============================================================== 10
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>端到端检测器把后处理一致性问题「结构性地」消掉了一大半。</strong>RT-DETR / YOLOv10 这类无 NMS 的模型，后处理只剩「top-k + 阈值 + 逆变换」，本模块第 2、3、4 节的坑（IoU 约定、topK 位置、class-wise 模式）全部消失。<em>这是「无 NMS」被严重低估的部署价值——它省下的不只是几毫秒，还有一整类难以自动检测的一致性风险。</em>C53 模块 04 从延迟角度讲了同一件事，两个角度加起来才是完整的论证。",
            "<strong>后处理算子的标准化仍然没做成。</strong>ONNX 从 opset 10 起有 <code>NonMaxSuppression</code> 算子，但它的语义（per-class、<code>max_output_boxes_per_class</code> 的计数方式、center_point_box 的坐标约定）与各框架、各推理后端的原生实现都对不齐；TRT 的 <code>EfficientNMS</code> 是自己一套；各家 NPU/DSP 的 NMS 加速器又是另一套。<em>「同一个 ONNX 在两个后端上给出不同框」目前仍是常态，而不是 bug。</em>",
            "<strong>差分测试（differential testing）与变形测试（metamorphic testing）应用到后处理。</strong>自动生成大量随机框-分数组合，喂给两份实现找分歧——这在编译器和数据库领域是成熟技术，在推理管线上还很少见。<em>难点在于生成「有意义的」测试用例：完全随机的框很少触发边界条件，需要有导向地生成 IoU 恰在阈值附近、分数并列、面积退化的样本。</em>这是一个门槛不高、工程价值很直接的方向。",
            "<strong>从单一 spec 生成多份实现（single source of truth）。</strong>用一份声明式的后处理描述（激活 / 阈值顺序 / NMS 模式 / 坐标约定）codegen 出 Python 参考实现、C++ 实现和 plugin 配置，让「两份实现不一致」在结构上不可能发生。<em>已有零星尝试（如把后处理写进 ONNX 图、或用 MLIR 描述），但没有形成通用方案——主要障碍是不同后端的算子能力差异太大。</em>",
            "<strong>数值可复现性与非确定性 kernel。</strong>TRT 的部分 kernel 使用 atomic 累加，浮点加法不满足结合律，同一输入两次运行可能差 $10^{-6}$。<em>这个量级本身无害，但经过 NMS 这种不连续算子后可能被放大成「保留集不同」</em>——尤其当分数并列时。「如何让整条推理管线逐位可复现」在功能安全场景（需要可重放、可取证）是个真问题，目前只能靠 <code>--deterministic</code> 类开关牺牲性能换取。",
            "<strong>可学习的去重。</strong>Learnable NMS、Relation Networks for Object Detection 等工作试图把去重变成网络的一部分而非手写规则。<em>它们在精度上没有决定性优势，但在<strong>工程属性</strong>上很有吸引力：去重逻辑进了模型，也就进了 ONNX，也就自动一致了。</em>这条路和端到端检测器殊途同归。",
            "<strong>TSR 特有的开放问题：超类划分该由谁定义？</strong>层次化 NMS 需要一个超类体系（哪些细类互斥、哪些可共存），目前是人工维护的表。<em>类别一多（几百类、还在增长）这张表就会腐化——新增一个「可变电子限速牌」类别时，有没有人记得把它加进限速超类？</em>能否从数据里自动学出「哪些类别对在物理上不可能共存」（比如从标注中统计同位置共现频率），是一个小而实用的问题。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>（都是短文档或代码，不是长论文，但每一份都能直接改变你写后处理的方式）：<em>Detectron2 的 <code>structures/boxes.py</code> 与 <code>BoxMode</code> 定义</em>——把坐标格式做成显式类型而不是隐式约定，是本模块第 5 节的最佳工程答案；<em>TensorRT <code>EfficientNMS</code> plugin 文档</em>（<code>plugin/efficientNMSPlugin/README.md</code>）——逐字读参数表，尤其 <code>score_activation</code> 与 <code>box_coding</code>；<em>ONNX <code>NonMaxSuppression</code> 算子规范</em>（Operators.md）——注意它的 <code>center_point_box</code> 与 <code>max_output_boxes_per_class</code> 语义和你想的可能不一样。</p><p><strong>★</strong> Girshick et al., <em>Rich feature hierarchies (R-CNN)</em> 与其 <code>py_cpu_nms.py</code>——<code>+1</code> 约定的历史源头；Lin et al., <em>Microsoft COCO</em>（ECCV 2014）——连续坐标语义的来源，两者对读就能明白 <code>+1</code> 之争的本质。<strong>★</strong> Bodla et al., <em>Soft-NMS</em>（ICCV 2017）——理解硬抑制的局限；Hosang et al., <em>Learning Non-Maximum Suppression</em>（CVPR 2017）——可学习去重的代表作；Hu et al., <em>Relation Networks for Object Detection</em>（CVPR 2018）——把去重变成注意力。</p><p>配套背景：Zhao et al., <em>RT-DETR</em>（CVPR 2024）与 Wang et al., <em>YOLOv10</em>（NeurIPS 2024）——无 NMS 如何顺带解决一致性问题。相邻课程：模块 01（预处理一致性，对拍的前四个阶段）、模块 02（engine 与算子回退）、模块 03（INT8 与分数并列问题的来源）、模块 05（延迟剖析与验收清单）、C53 模块 04–05（NMS 的延迟代价与选型）、C55 模块 04（多帧融合为什么需要类别分布而非硬判决）、C61 模块 03（数据管线 bug 的诊断树）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 04 · 后处理对齐与 C++ 推理管线（NMS 变体 / letterbox 逆变换 / 端到端对拍）

目标：把「训练侧 Python 后处理」与「车端 C++ 后处理」之间**每一处会静默生效的分歧**
变成可以运行、可以断言、可以自动定位的东西。

本 notebook 你会亲手实现：
1. **两种 IoU 约定**（COCO 的 `offset=0` 与 VOC/Faster R-CNN 的 `offset=1`），
   量化差异并验证它按 $\\mathcal{O}(1/s)$ 衰减 —— **只伤小目标**
2. **确定性 NMS**（排序键 = `(-score, index)`，消除并列歧义），
   并量化两种 IoU 约定给出的保留集差异
3. **top-k 位置实验**：截断放在 NMS 之前 vs 之后，密集帧上检出目标数的塌陷
4. **letterbox 正/逆变换**与**五个错误版本**，逐一算出偏移量
5. **class-wise / class-agnostic / 层次化 NMS**，含 `batched_nms` 的 offset trick
   与它的 **float32 数值悬崖**
6. **解码约定**：$\\sigma(\\sigma(x))$ 为什么「mAP 不变但线上炸」、坐标格式弄错的量化后果
7. **端到端对拍框架**：8 个阶段 + 逐阶段容差 + 自动定位第一个失配阶段，
   注入三种真实 bug 并验证每次都定位正确

> 心智模型：**后处理 bug 不会报错、不会崩溃、只会让你误判成模型问题。
> 防线不是「小心」，是「逐阶段对拍 + CI」。**"""),

    md("""## 1 · IoU 的两种约定：`+1` 从哪来，差多少

`offset=1` 来自 Pascal VOC 的「像素索引闭区间」语义（框 `[0,0,7,7]` 覆盖 8 个像素）；
`offset=0` 是 COCO 的连续坐标半开区间语义。两者各自自洽，**混用就出事**。"""),

    code("""import numpy as np

def iou_pair(a, b, offset=0):
    # 两个 xyxy 框的 IoU。offset=0 → COCO 口径；offset=1 → VOC / Faster R-CNN 口径
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw = max(0.0, ix2 - ix1 + offset)
    ih = max(0.0, iy2 - iy1 + offset)
    inter = iw * ih
    aa = (a[2] - a[0] + offset) * (a[3] - a[1] + offset)
    ab = (b[2] - b[0] + offset) * (b[3] - b[1] + offset)
    return inter / (aa + ab - inter)

print('两个边长 s 的正方形框，沿对角线错开 d = s/4（相对位移固定 25%）\\n')
print(f\"{'边长 s':>8s} {'IoU(offset=0)':>15s} {'IoU(offset=1)':>15s} {'差值':>9s}\")
for s in [8, 16, 32, 64]:
    d = s / 4
    A = [0, 0, s, s]
    B = [d, d, s + d, s + d]
    i0, i1 = iou_pair(A, B, 0), iou_pair(A, B, 1)
    print(f'{s:>8d} {i0:>15.4f} {i1:>15.4f} {i1 - i0:>9.4f}')

# —— 手算校验（分数都能口算）——
assert abs(iou_pair([0, 0, 8, 8], [2, 2, 10, 10], 0) - 36 / 92) < 1e-12    # 交 6x6, 并 64+64-36
assert abs(iou_pair([0, 0, 8, 8], [2, 2, 10, 10], 1) - 49 / 113) < 1e-12   # 交 7x7, 并 81+81-49
assert abs(iou_pair([0, 0, 64, 64], [16, 16, 80, 80], 0) - 36 / 92) < 1e-12
assert abs(iou_pair([0, 0, 64, 64], [16, 16, 80, 80], 1) - 2401 / 6049) < 1e-12
print('\\n✅ 注意左列：offset=0 的 IoU 在所有尺度上**恒等于 0.3913** —— 它是尺度不变的。')
print('   offset=1 不是：那个 +1 是**绝对**像素量，对 8px 框是 12.5% 的膨胀，对 64px 框只有 1.6%。')"""),

    code("""# Δ(s) 到底怎么衰减：log-log 拟合
sizes = np.array([4, 8, 16, 32, 64, 128, 256], dtype=float)
deltas = []
for s in sizes:
    d = s / 4
    deltas.append(iou_pair([0, 0, s, s], [d, d, s + d, s + d], 1)
                  - iou_pair([0, 0, s, s], [d, d, s + d, s + d], 0))
deltas = np.array(deltas)

print(f\"{'边长 s':>8s} {'Δ = IoU1 - IoU0':>17s} {'相对上一行':>11s}\")
for i, s in enumerate(sizes):
    ratio = deltas[i - 1] / deltas[i] if i else float('nan')
    tail = f'{ratio:>11.2f}' if i else f\"{'—':>11s}\"
    print(f'{int(s):>8d} {deltas[i]:>17.5f}{tail}')

slope = float(np.polyfit(np.log(sizes), np.log(deltas), 1)[0])
print(f'\\nlog-log 斜率 = {slope:.3f}   （-1 = 严格 1/s 衰减）')
assert -1.10 < slope < -0.85, slope
assert deltas[0] > 25 * deltas[-1], '4px 与 256px 的差异应相差一个数量级以上'
print('✅ Δ(s) ~ O(1/s)：**+1 约定是一个只伤害小目标的 bug**。')
print('   TSR 的标志常年 10-30 px —— 这正好是 Δ 最大的区间。')
print('   同类的还有 round/floor(±0.5px)、letterbox pad 奇偶(±0.5px)、align_corners(±0.5px)，会叠加。')"""),

    md("""## 2 · 确定性 NMS，以及两种 IoU 约定造成的保留集差异

先把 NMS 写成一个**确定性函数**：排序键取 `(-score, index)`，这样并列分数不再有歧义。
（模块正文第 3 节：INT8 输出只有约 256 个离散值，并列是常态，
不做这一步的话 Python 与 C++ 的输出就不可复现。）"""),

    code("""def iou_1_to_n(box, boxes, offset=0):
    # box: (4,) xyxy;  boxes: (N,4)  ->  (N,) IoU
    x1 = np.maximum(box[0], boxes[:, 0]); y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2]); y2 = np.minimum(box[3], boxes[:, 3])
    w = np.clip(x2 - x1 + offset, 0, None); h = np.clip(y2 - y1 + offset, 0, None)
    inter = w * h
    a0 = (box[2] - box[0] + offset) * (box[3] - box[1] + offset)
    a1 = (boxes[:, 2] - boxes[:, 0] + offset) * (boxes[:, 3] - boxes[:, 1] + offset)
    return inter / np.maximum(a0 + a1 - inter, 1e-12)

def score_order(scores):
    # **确定性全序**：先按分数降序，分数相同时按原始下标升序。
    # np.lexsort 的最后一个键是主键。
    return np.lexsort((np.arange(len(scores)), -np.asarray(scores, dtype=float)))

def nms(boxes, scores, iou_thr=0.5, offset=0):
    order = score_order(scores)
    keep = []
    while order.size:
        i = order[0]; keep.append(int(i))
        rest = order[1:]
        if rest.size == 0:
            break
        ious = iou_1_to_n(boxes[i], boxes[rest], offset)
        order = rest[ious <= iou_thr]          # 抑制条件是 > thr（保留 <= thr）
    return np.array(keep, dtype=int)

# —— 手算校验 ——
B = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=float)
S = np.array([0.9, 0.8, 0.7])
assert nms(B, S, 0.5).tolist() == [0, 2]
assert abs(iou_1_to_n(B[0], B[1:2], 0)[0] - 81 / 119) < 1e-12
# 并列分数：确定性排序保证结果与输入顺序无关地可复现
tie_b = np.array([[0, 0, 8, 8], [1, 1, 9, 9], [40, 40, 48, 48]], dtype=float)
tie_s = np.array([0.5, 0.5, 0.5])
assert nms(tie_b, tie_s, 0.5).tolist() == [0, 2], '并列时应按 index 决胜，保留 0 号'
print('✅ 确定性 NMS 就位：排序键 = (-score, index)，并列不再有歧义。')""" ),

    code("""# —— 决定性演示：同一对框，阈值卡在两种约定之间 ——
A, Bx = [0, 0, 8, 8], [2, 2, 10, 10]
THR = 0.41                                   # 0.3913 < 0.41 < 0.4336
bb = np.array([A, Bx], dtype=float)
ss = np.array([0.9, 0.8])
k0 = nms(bb, ss, THR, offset=0)
k1 = nms(bb, ss, THR, offset=1)
print(f'iou_thr={THR}:  IoU0={iou_pair(A,Bx,0):.4f}  IoU1={iou_pair(A,Bx,1):.4f}')
print(f'  offset=0 -> keep {k0.tolist()}   (0.3913 <= 0.41，**不抑制**，输出 2 个框)')
print(f'  offset=1 -> keep {k1.tolist()}      (0.4336 >  0.41，**抑制**，输出 1 个框)')
assert k0.tolist() == [0, 1] and k1.tolist() == [0]
print('\\n⚠️  同一份权重、同一张图、同一个阈值 —— 两侧输出的框数不同。没有任何报错。')"""),

    code("""def tsr_scene(n_sign, rng, props=14, px_lo=8, px_hi=28, W=1920, H=1080):
    # 合成一帧 TSR 检测器的原始候选：
    #   每块牌子周围 props 个抖动候选（抖动幅度 ∝ 框尺寸），外加随场景变多的背景误检
    ctr = rng.uniform([80, 80], [W - 80, H - 80], size=(n_sign, 2))
    sz = rng.uniform(px_lo, px_hi, size=(n_sign, 1))
    c = np.repeat(ctr, props, axis=0); s = np.repeat(sz, props, axis=0)
    c = c + rng.normal(0, 0.10, size=c.shape) * s
    s = s * np.exp(rng.normal(0, 0.08, size=s.shape))
    fb = np.concatenate([c - s / 2, c + s / 2], axis=1)
    peak = rng.beta(2.5, 1.5, size=(n_sign, 1))
    fs = (peak * rng.uniform(0.30, 1.0, size=(n_sign, props))).ravel()
    gid = np.repeat(np.arange(n_sign), props)
    n_bg = 20 + 4 * n_sign
    bc = rng.uniform([0, 0], [W, H], size=(n_bg, 2)); bs = rng.uniform(8, 30, size=(n_bg, 1))
    bb = np.concatenate([bc - bs / 2, bc + bs / 2], axis=1)
    return (np.vstack([fb, bb]),
            np.concatenate([fs, rng.uniform(0.02, 0.30, n_bg)]),
            np.concatenate([gid, np.full(n_bg, -1)]))

# 20 个种子上统计两种约定的保留集差异
tot_sym, tot_keep = 0, 0
for seed in range(20):
    b, s, g = tsr_scene(40, np.random.default_rng(seed))
    m = s >= 0.25
    k0 = set(nms(b[m], s[m], 0.42, 0).tolist())
    k1 = set(nms(b[m], s[m], 0.42, 1).tolist())
    tot_sym += len(k0 ^ k1); tot_keep += len(k0)
print(f'20 帧合计：offset=0 保留 {tot_keep} 个框，两种约定的对称差 {tot_sym} 个')
print(f'-> 约 {tot_sym / tot_keep:.1%} 的保留框会因为一个 +1 而不同')
assert tot_sym > 0, '小框密集场景下两种约定必然给出不同的保留集'
print('✅ 这就是「小目标桶掉点、大目标桶不掉」的一种真实成因。')"""),

    md("""## 3 · top-k 的位置：截断放在 NMS 之前会吃掉密集场景

同一个 `top-k`，放在 NMS **之前**是「从未去重的候选里取 k 个」，
放在 **之后**是「从已去重的目标里取 k 个」。前者在密集帧上会静默漏掉大批目标。"""),

    code("""def n_covered(keep_idx, gid):
    # 保留集覆盖了多少个不同的真实目标
    g = gid[keep_idx]
    return len(set(g[g >= 0].tolist()))

def pipeline(boxes, scores, gid, score_thr=0.25, topk_before=None,
             iou_thr=0.5, max_det=300, offset=0):
    m = scores >= score_thr
    b, s, g = boxes[m], scores[m], gid[m]
    n_pass = len(s)
    if topk_before is not None:                        # 方案 B：NMS **之前**截断
        sel = score_order(s)[:topk_before]
        b, s, g = b[sel], s[sel], g[sel]
    keep = nms(b, s, iou_thr, offset)[:max_det]        # 方案 A：只在 NMS **之后**截断
    return n_pass, len(keep), n_covered(keep, g)

DENSE = tsr_scene(60, np.random.default_rng(7), props=20)     # 城市路口：60 块牌子
SPARSE = tsr_scene(4, np.random.default_rng(7), props=20)     # 高速：4 块牌子

for name, scene, n_gt in [('密集帧（60 块牌子）', DENSE, 60), ('稀疏帧（4 块牌子）', SPARSE, 4)]:
    print(f'\\n{name}')
    print(f\"{'NMS 前 topK':>13s} {'过阈 N':>8s} {'输出框数':>9s} {'覆盖目标数':>11s} {'召回':>8s}\")
    prev_cov = -1
    for tk in [100, 200, 300, 600, 1200, None]:
        n_pass, n_out, cov = pipeline(*scene, topk_before=tk)
        label = 'None(不截断)' if tk is None else str(tk)
        print(f'{label:>13s} {n_pass:>8d} {n_out:>9d} {cov:>11d} {cov / n_gt:>7.1%}')
        assert cov >= prev_cov, 'topK 越大，覆盖的目标数必须单调不减'
        prev_cov = cov

n_pass_d, _, cov_d100 = pipeline(*DENSE, topk_before=100)
_, _, cov_dinf = pipeline(*DENSE, topk_before=None)
n_pass_s, _, cov_s100 = pipeline(*SPARSE, topk_before=100)
_, _, cov_sinf = pipeline(*SPARSE, topk_before=None)
assert cov_d100 < 0.65 * cov_dinf, (cov_d100, cov_dinf)
assert cov_s100 == cov_sinf, '稀疏帧上 topK=100 根本不生效 -> 两方案完全一致'
print(f'\\n⚠️  密集帧：topK=100 时覆盖 {cov_d100}/60，不截断时 {cov_dinf}/60 —— **静默丢了一大半**')
print(f'✅ 稀疏帧：topK=100 时覆盖 {cov_s100}/4，不截断时 {cov_sinf}/4 —— **完全一样**')
print('   -> 这个 bug **只在密集场景发作**，而离线评测集里这种帧本来就少 -> mAP 上看不出来。')
print('   记住：NMS 前的 topK 按「最大过阈候选数」留 2-3 倍余量（几千）；')
print('         NMS 后的 max_det 才按「单帧最大目标数」设（几百）。两者不能互相替代。')"""),

    code("""# per-class 还是 global：TSR 的 200 类会怎么被挤
rng = np.random.default_rng(3)
N_CLS = 200
b, s, g = tsr_scene(50, np.random.default_rng(11), props=20)
# 让类别高度不均衡：多数候选集中在 3 个常见类（限速 60/80/100），其余是长尾
cls = np.where(rng.random(len(s)) < 0.75,
               rng.integers(0, 3, len(s)),
               rng.integers(3, N_CLS, len(s)))
m = s >= 0.25
b, s, g, cls = b[m], s[m], g[m], cls[m]

def topk_global(s, k):
    return score_order(s)[:k]

def topk_per_class(s, cls, k_per):
    out = []
    for c in np.unique(cls):
        idx = np.where(cls == c)[0]
        out.append(idx[score_order(s[idx])[:k_per]])
    return np.concatenate(out)

gsel = topk_global(s, 300)
psel = topk_per_class(s, cls, 5)
print(f'过阈候选 {len(s)} 个，覆盖 {len(np.unique(cls))} 个类别')
print(f'global top-300      : 选中 {len(gsel):4d} 个，覆盖 {len(np.unique(cls[gsel])):3d} 个类别')
print(f'per-class top-5     : 选中 {len(psel):4d} 个，覆盖 {len(np.unique(cls[psel])):3d} 个类别')
assert len(np.unique(cls[psel])) > len(np.unique(cls[gsel])), 'per-class 应覆盖更多类别'
assert len(psel) != len(gsel)
print('\\n⚠️  global top-k 会被头部类别吃掉名额 —— TSR 的 200 类里，长尾类先出局。')
print('   mmdetection 的做法是第三种切法：**按 FPN 层级**各取 top-k，')
print('   保证小目标层（stride 8）不会被大目标层挤掉 —— 对 TSR 比按类别切更有价值。')"""),

    md("""## 4 · letterbox 正/逆变换：五个错误版本各偏多少

$1920\\times1080 \\to 640\\times640$：$r = 1/3$，$p_x = 0$，$p_y = 140$。
测试框在网络坐标下是 `[100, 200, 140, 240]`，正确还原是 `[300, 180, 420, 300]`。"""),

    code("""def letterbox_params(src_hw, dst_hw):
    (H, W), (Hn, Wn) = src_hw, dst_hw
    r = min(Wn / W, Hn / H)
    new_w, new_h = round(W * r), round(H * r)
    return dict(r=r, pad_x=(Wn - new_w) / 2.0, pad_y=(Hn - new_h) / 2.0,
                new_w=new_w, new_h=new_h, W=W, H=H, Wn=Wn, Hn=Hn)

def lb_forward(box, p):
    # 原图 xyxy -> 网络输入 xyxy
    r, px, py = p['r'], p['pad_x'], p['pad_y']
    return np.array([box[0] * r + px, box[1] * r + py, box[2] * r + px, box[3] * r + py])

def lb_inverse(box, p):
    # 网络输入 xyxy -> 原图 xyxy   ** 先减 pad，再除 r **
    r, px, py = p['r'], p['pad_x'], p['pad_y']
    return np.array([(box[0] - px) / r, (box[1] - py) / r,
                     (box[2] - px) / r, (box[3] - py) / r])

P640 = letterbox_params((1080, 1920), (640, 640))
print('letterbox 参数:', {k: round(v, 4) if isinstance(v, float) else v for k, v in P640.items()})
assert abs(P640['r'] - 1 / 3) < 1e-12
assert P640['new_w'] == 640 and P640['new_h'] == 360
assert P640['pad_x'] == 0.0 and P640['pad_y'] == 140.0

gt = np.array([300.0, 180.0, 420.0, 300.0])
net = lb_forward(gt, P640)
print('\\n原图框', gt, ' -> 网络坐标', net)
assert np.allclose(net, [100, 200, 140, 240])
assert np.allclose(lb_inverse(net, P640), gt)

# —— 往返不变量测试：20 行代码挡住 E1~E4 全部四种错法 ——
rng = np.random.default_rng(0)
for _ in range(2000):
    x1, y1 = rng.uniform(0, 1800), rng.uniform(0, 1000)
    box = np.array([x1, y1, x1 + rng.uniform(4, 100), y1 + rng.uniform(4, 100)])
    assert np.allclose(lb_inverse(lb_forward(box, P640), P640), box, atol=1e-9)
print('✅ 往返一致性 inverse(forward(b)) == b 在 2000 个随机框上成立（atol=1e-9）')"""),

    code("""# —— 五个错误版本 ——
def inv_E1(box, p):    # 漏减 pad
    return box / p['r']

def inv_E2(box, p):    # 顺序反：先除 r 再减 pad
    r, px, py = p['r'], p['pad_x'], p['pad_y']
    return np.array([box[0] / r - px, box[1] / r - py, box[2] / r - px, box[3] / r - py])

def inv_E3(box, p):    # pad 减了两遍（把「单边 pad」当成「总 pad」）
    r, px, py = p['r'], p['pad_x'], p['pad_y']
    return np.array([(box[0] - 2 * px) / r, (box[1] - 2 * py) / r,
                     (box[2] - 2 * px) / r, (box[3] - 2 * py) / r])

def inv_E4(box, p):    # 用了 stretch（非等比）缩放比
    sx, sy = p['Wn'] / p['W'], p['Hn'] / p['H']
    return np.array([box[0] / sx, box[1] / sy, box[2] / sx, box[3] / sy])

print(f\"{'版本':<26s} {'还原结果':<34s} {'Δy (中心)':>11s} {'与真值 IoU':>11s}\")
def iou_np(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    it = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - it
    return it / ua if ua > 0 else 0.0

for name, fn in [('✅ 正确', lb_inverse), ('E1 漏减 pad', inv_E1), ('E2 顺序反', inv_E2),
                 ('E3 pad 减两遍', inv_E3), ('E4 stretch 比例', inv_E4)]:
    out = fn(net, P640)
    dy = (out[1] + out[3]) / 2 - (gt[1] + gt[3]) / 2
    print(f'{name:<26s} {str(np.round(out, 1)):<34s} {dy:>11.1f} {iou_np(out, gt):>11.3f}')

r, py = P640['r'], P640['pad_y']
assert np.allclose(inv_E1(net, P640), [300, 600, 420, 720])
assert np.allclose(inv_E2(net, P640), [300, 460, 420, 580])
assert np.allclose(inv_E3(net, P640), [300, -240, 420, -120])
assert np.allclose(inv_E4(net, P640), [300, 337.5, 420, 405])
assert abs(py / r - 420.0) < 1e-9                     # E1 的偏移量 = p_y / r
assert abs(py * (1 - r) / r - 280.0) < 1e-9           # E2 的偏移量 = p_y(1-r)/r
print('\\n✅ 每个错误版本的偏移量都有闭式解：E1=+p/r=420, E2=+p(1-r)/r=280, E3=-p/r=-420。')
print('⚠️  E1/E3 偏得太狠一眼可见；**真正能在量产里活很久的是 E4 和亚像素级的取整分歧**。')"""),

    code("""# —— E5：clip 的位置 ——
def clip_wrong(box, p):        # 先在网络坐标下 clip 到 [0, 640]，再逆变换，然后当成有效检测输出
    b = np.clip(box, 0, [p['Wn'], p['Hn'], p['Wn'], p['Hn']])
    b = lb_inverse(b, p)
    return np.clip(b, 0, [p['W'], p['H'], p['W'], p['H']])     # 最终仍要落回图像范围

def clip_right(box, p):        # 先逆变换，再 clip 到原图，最后**丢弃退化框**
    b = lb_inverse(box, p)
    b = np.clip(b, 0, [p['W'], p['H'], p['W'], p['H']])
    return b if (b[2] - b[0] > 1 and b[3] - b[1] > 1) else None

edge = np.array([300.0, 20.0, 340.0, 100.0])          # 完全落在上方 padding 区（y < pad_y = 140）
wrong = clip_wrong(edge, P640)
print('一个完全落在 padding 区里的候选框（网络坐标）:', edge)
print('  错误顺序（网络坐标下 clip）:', np.round(wrong, 1),
      f' -> 高度 {wrong[3]-wrong[1]:.1f} px，**作为一个贴在图像上边缘的假检测被上报**')
print('  正确顺序（原图坐标下 clip + 退化过滤）:', clip_right(edge, P640), ' -> 直接丢弃')
assert clip_right(edge, P640) is None
assert wrong[3] - wrong[1] < 1e-9, '错误顺序会产出一个零高度的退化框，而它仍然进入了输出'
print('\\n✅ clip 的语义是「限制在**真实图像**范围内」。')
print('   在网络坐标下 clip = 允许框延伸到 padding 区 —— 而 padding 区在原图上根本不存在。')"""),

    code("""# —— 亚像素偏移的代价：为什么 4px 在 TSR 里是灾难 ——
def iou_shift(s, d):
    # 边长 s 的框沿对角线整体偏移 d 像素后，与真值的 IoU
    inter = max(0.0, s - d) ** 2
    return inter / (2 * s * s - inter)

print(f\"{'框边长':>8s} {'偏 1px':>9s} {'偏 2px':>9s} {'偏 4px':>9s} {'IoU=0.5 口径下偏 4px 算命中?':>28s}\")
for s in [12, 20, 32, 64, 100]:
    hits = 'YES' if iou_shift(s, 4) >= 0.5 else '**NO -> 算完全漏检**'
    print(f'{s:>8d} {iou_shift(s,1):>9.3f} {iou_shift(s,2):>9.3f} {iou_shift(s,4):>9.3f} {hits:>28s}')

assert abs(iou_shift(12, 4) - 64 / 224) < 1e-12
assert abs(iou_shift(100, 4) - 9216 / 10784) < 1e-12
assert iou_shift(12, 4) < 0.5 and iou_shift(100, 4) > 0.8
print(f'\\n⚠️  同一个 4 px 的系统性偏移：')
print(f'   100 px 的近处大牌 -> IoU {iou_shift(100,4):.3f}，任何口径下都算命中，**你永远不会发现**')
print(f'    12 px 的远处小牌 -> IoU {iou_shift(12,4):.3f}，IoU=0.5 口径下**直接算完全漏检**')
print('✅ 报告上会写「小目标 AP 掉一半，大目标不变」—— 和「模型对小目标不行」形态完全一样。')
print('   结论：凡是「只有小目标桶掉点」，第一怀疑对象永远是坐标变换，不是模型能力。')"""),

    md("""## 5 · class-wise / class-agnostic / 层次化 NMS

`batched_nms` 的 offset trick：给每个框加上 `class_id × Δ`，把不同类别推到互不相交的坐标区间，
再做**一次** class-agnostic NMS —— 与逐类循环严格等价，但只有一次 kernel launch。
**前提是 Δ 选得对：选大了会掉进 float32 的数值悬崖。**"""),

    code("""def nms_classwise(boxes, scores, cls, iou_thr=0.5, offset=0):
    # 朴素版：逐类循环
    keep = []
    for c in np.unique(cls):
        idx = np.where(cls == c)[0]
        keep.append(idx[nms(boxes[idx], scores[idx], iou_thr, offset)])
    return np.sort(np.concatenate(keep))

def nms_batched(boxes, scores, cls, iou_thr=0.5, offset=0, delta=None):
    # offset trick：一次调用做完 class-wise
    if delta is None:
        delta = float(boxes.max()) + 1.0          # **Δ = 图像最大坐标 + 1，不是一个拍脑袋的大数**
    shifted = boxes + (cls.astype(np.float64) * delta)[:, None]
    return np.sort(nms(shifted, scores, iou_thr, offset))

def nms_agnostic(boxes, scores, cls, iou_thr=0.5, offset=0):
    return np.sort(nms(boxes, scores, iou_thr, offset))

rng = np.random.default_rng(21)
b, s, g = tsr_scene(30, np.random.default_rng(5), props=12)
cls = rng.integers(0, 8, len(s))
m = s >= 0.25
b, s, cls = b[m], s[m], cls[m]

kc = nms_classwise(b, s, cls, 0.5)
kb = nms_batched(b, s, cls, 0.5)
ka = nms_agnostic(b, s, cls, 0.5)
print(f'候选 {len(s)} 个 / {len(np.unique(cls))} 类')
print(f'  class-wise（逐类循环）: {len(kc)} 个框，调用 NMS {len(np.unique(cls))} 次')
print(f'  batched（offset trick）: {len(kb)} 个框，调用 NMS 1 次')
print(f'  class-agnostic         : {len(ka)} 个框')
assert np.array_equal(kc, kb), 'offset trick 必须与逐类循环**严格等价**'
assert len(ka) < len(kc), 'agnostic 跨类抑制，保留框必然更少'
print('\\n✅ offset trick 与逐类循环逐元素相同（不是「差不多」，是严格相等）。')"""),

    code("""# —— float32 的数值悬崖：Δ 选大了会静默摧毁 IoU ——
box32 = np.array([100.0, 100.0, 108.0, 108.0], dtype=np.float32)     # 一个 8x8 的小标志框
print(f\"{'Δ':>12s} {'类别 ID':>8s} {'偏移后坐标量级':>15s} {'ULP(px)':>9s} {'偏移后框宽':>11s}\")
for delta, cid in [(1921.0, 0), (1921.0, 199), (1e6, 199), (1e6, 1000)]:
    off = np.float32(delta * cid)
    shifted = (box32 + off).astype(np.float32)
    w = float(shifted[2] - shifted[0])
    mag = float(shifted[0])
    ulp = float(np.spacing(np.float32(max(mag, 1.0))))
    print(f'{delta:>12.0f} {cid:>8d} {mag:>15.3e} {ulp:>9.3f} {w:>11.3f}')

bad = (box32 + np.float32(1e6 * 1000)).astype(np.float32)
assert float(bad[2] - bad[0]) == 0.0, 'Δ=1e6、类别 1000 时，8px 的框宽度被舍入成 0'
good = (box32 + np.float32(1921.0 * 199)).astype(np.float32)
assert abs(float(good[2] - good[0]) - 8.0) < 0.01
print('\\n⚠️  Δ=1e6 且类别 ID=1000 时坐标到 1e9，float32 的 ULP ≈ 64 px：')
print('    x1 和 x2 被舍入到**同一个浮点数** -> 框宽 0 -> 面积 0 -> IoU 恒为 0 -> **NMS 完全失效**')
print('    而且不报任何错，输出的框数会莫名其妙地暴涨。')
print('✅ 正确做法：Δ = 图像最大边 + 1；或者把坐标量化到 int32 再加偏移。')"""),

    code("""# —— TSR 的层次化 NMS：超类内 agnostic，跨超类 class-wise ——
# 场景：一块「限速 60」牌同时被检成 限速60(0.52) / 限速80(0.47)；
#       它下方紧贴一块「货车」辅助牌（与主牌 IoU 约 0.45）
CLS_NAME = {0: '限速60', 1: '限速80', 2: '禁止左转', 3: '辅助牌·货车'}
SUPER = {0: 'speed', 1: 'speed', 2: 'prohibit', 3: 'plate'}     # 超类划分表

boxes_t = np.array([[100, 100, 118, 118],      # 限速60
                    [101,  99, 119, 117],      # 限速80（同一块物理牌子）
                    [100, 116, 118, 128],      # 辅助牌（在主牌下方，IoU 与主牌 ~0.14）
                    [400, 200, 424, 224]],     # 另一处的禁止左转
                   dtype=float)
scores_t = np.array([0.52, 0.47, 0.61, 0.80])
cls_t = np.array([0, 1, 3, 2])

def nms_hierarchical(boxes, scores, cls, super_map, iou_thr=0.5, offset=0):
    sup = np.array([super_map[int(c)] for c in cls])
    keep = []
    for u in np.unique(sup):                        # 超类之间互不抑制
        idx = np.where(sup == u)[0]
        keep.append(idx[nms(boxes[idx], scores[idx], iou_thr, offset)])   # 超类内 agnostic
    return np.sort(np.concatenate(keep))

for name, k in [('class-wise ', nms_classwise(boxes_t, scores_t, cls_t, 0.5)),
                ('agnostic   ', nms_agnostic(boxes_t, scores_t, cls_t, 0.5)),
                ('层次化      ', nms_hierarchical(boxes_t, scores_t, cls_t, SUPER, 0.5))]:
    names = [CLS_NAME[int(cls_t[i])] for i in k]
    print(f'{name}: {len(k)} 个框  ->  {names}')

kw = nms_classwise(boxes_t, scores_t, cls_t, 0.5)
ka2 = nms_agnostic(boxes_t, scores_t, cls_t, 0.5)
kh = nms_hierarchical(boxes_t, scores_t, cls_t, SUPER, 0.5)
assert set(kw.tolist()) == {0, 1, 2, 3}, 'class-wise 什么都不抑制：把消歧责任甩给下游'
assert 1 not in kh, '层次化：限速80 被同超类的限速60 抑制'
assert 2 in kh and 3 in kh, '层次化：辅助牌与禁止左转跨超类，必须保留'
assert len(kh) == 3
print('\\n⚠️  class-wise：下游拿到「这里既是限速60又是限速80」，而下游没有消歧所需的信息。')
print('⚠️  agnostic ：本例阈值下辅助牌侥幸活着，但只要主辅牌贴得更近就会被整块抹掉 ——')
print('    而辅助牌承载的是限定条件（「7:00-20:00」「货车」），删掉它，主牌语义就是错的。')
print('✅ 层次化是唯一同时解决两个问题的模式。')
print('   工程补充：**被抑制的类别与分数不该丢**，要作为「竞争假设」附在保留框上传给下游 ——')
print('   单帧上 0.52 vs 0.47 几乎是抛硬币，连续 10 帧的贝叶斯累积才能把它分开（C55 模块 04）。')"""),

    md("""## 6 · 解码约定：$\\sigma(\\sigma(x))$ 与坐标格式

本节两个实验，都是「不报错、不崩溃、指标还挺好看」的那一类 bug。"""),

    code("""def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

rng = np.random.default_rng(2024)
logits = rng.normal(-2.0, 2.0, size=8400)               # 一个典型的检测头 logit 分布
single = sigmoid(logits)                                # 正确：只做一次
double = sigmoid(single)                                # bug：模型里已经有 Sigmoid，外面又做了一次

print(f\"{'':<18s} {'min':>8s} {'max':>8s} {'>=0.30 的比例':>14s}\")
print(f\"{'σ(x)   正确':<18s} {single.min():>8.4f} {single.max():>8.4f} {(single>=0.3).mean():>13.1%}\")
print(f\"{'σ(σ(x)) 出事了':<18s} {double.min():>8.4f} {double.max():>8.4f} {(double>=0.3).mean():>13.1%}\")

assert double.min() > 0.5 and double.max() < 0.7311
assert (double >= 0.3).mean() == 1.0, '所有候选全部过阈 -> 一个框都筛不掉'
assert (single >= 0.3).mean() < 0.40

# **排序完全不变** —— 所以基于排序的指标（AP）几乎不动
o1 = np.argsort(-single, kind='stable'); o2 = np.argsort(-double, kind='stable')
assert np.array_equal(o1, o2), 'σ 是严格单调的，排序必然不变'

labels = (rng.random(8400) < sigmoid(logits * 0.9)).astype(int)      # 与 logit 相关的伪标签
def average_precision(order, y):
    y = y[order]; tp = np.cumsum(y); prec = tp / np.arange(1, len(y) + 1)
    return float((prec * y).sum() / max(y.sum(), 1))
ap1, ap2 = average_precision(o1, labels), average_precision(o2, labels)
print(f'\\nAP(正确) = {ap1:.6f}    AP(σ∘σ) = {ap2:.6f}    差 = {abs(ap1-ap2):.2e}')
assert abs(ap1 - ap2) < 1e-12, 'AP 是纯排序指标，对单调变换免疫'
print('\\n⚠️  **离线评测报告是绿的，线上却炸了**：')
print('    候选数从几百涨到 8400 -> NMS 是 O(NK) -> 延迟 p99 爆表；同时背景框全部过阈 -> FP 暴涨。')
print('✅ 诊断只要一行：`print(scores.min())`。最小值 > 0.5 就抓到它了。')
print('   反向错误同样常见：模型输出 logits 却拿去和 0.3 比 —— 等于把阈值悄悄抬到 σ(0.3)=0.574。')"""),

    code("""# —— 坐标格式：四种，没有一种自带标签 ——
def cxcywh_to_xyxy(b):
    cx, cy, w, h = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)

def xywh_to_xyxy(b):
    x, y, w, h = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([x, y, x + w, y + h], axis=1)

rng = np.random.default_rng(9)
n = 500
cx = rng.uniform(200, 1700, n); cy = rng.uniform(150, 950, n)
w = rng.uniform(10, 40, n); h = w * rng.uniform(0.9, 1.1, n)
gt_xyxy = cxcywh_to_xyxy(np.stack([cx, cy, w, h], axis=1))
gt_cxcywh = np.stack([cx, cy, w, h], axis=1)
gt_xywh = np.stack([gt_xyxy[:, 0], gt_xyxy[:, 1], w, h], axis=1)

def mean_iou(a, b):
    return float(np.mean([iou_np(a[i], b[i]) for i in range(len(a))]))

def frac_degenerate(b):
    return float(np.mean((b[:, 2] <= b[:, 0]) | (b[:, 3] <= b[:, 1])))

print(f\"{'把它当成 xyxy 用':<24s} {'与真值平均 IoU':>15s} {'退化框(负/零面积)占比':>22s}\")
print(f\"{'✅ 真的是 xyxy':<24s} {mean_iou(gt_xyxy, gt_xyxy):>15.4f} {frac_degenerate(gt_xyxy):>21.1%}\")
print(f\"{'cxcywh 当 xyxy':<24s} {mean_iou(gt_cxcywh, gt_xyxy):>15.4f} {frac_degenerate(gt_cxcywh):>21.1%}\")
print(f\"{'xywh   当 xyxy':<24s} {mean_iou(gt_xywh, gt_xyxy):>15.4f} {frac_degenerate(gt_xywh):>21.1%}\")
print(f\"{'yxyx   当 xyxy':<24s} {mean_iou(gt_xyxy[:, [1,0,3,2]], gt_xyxy):>15.4f} \"
      f\"{frac_degenerate(gt_xyxy[:, [1,0,3,2]]):>21.1%}\")

assert mean_iou(gt_cxcywh, gt_xyxy) < 0.05, 'cxcywh 当 xyxy 用，小目标 IoU 直接归零'
assert frac_degenerate(gt_xywh) > 0.95, 'xywh 当 xyxy 用：w << x1，几乎全是负面积框'
assert mean_iou(gt_xyxy[:, [1, 0, 3, 2]], gt_xyxy) < 0.05
print('\\n⚠️  `xywh / cxcywh 当 xyxy` 的症状特别值得记：像素坐标下 w << x1，')
print('    框全是负面积 -> IoU 恒为 0 -> **NMS 一个都不抑制** -> 满屏重复框。')
print('    看起来像「NMS 坏了」，其实是坐标格式。（归一化坐标下则是框整体挤向左上角。）')
print('    `yxyx 当 xyxy` 不产生退化框，只是沿主对角线镜像 —— 更隐蔽，近方形图上尤其难看出来。')
print('✅ 最佳工程答案是 Detectron2 的做法：把坐标格式做成**显式类型**（BoxMode），')
print('   而不是靠注释和口头约定。类型系统能挡住的 bug，就别靠人挡。')"""),

    md("""## 7 · 端到端对拍框架：8 个阶段，自动定位第一个失配

下面搭一条**完整的迷你检测管线**（合成图 → letterbox → 归一化 → 迷你「模型」→ 解码 → NMS → 逆变换），
然后往里注入四种真实 bug，验证对拍器每次都能定位到**正确的阶段**。

管线参数：原图 $320\\times180$ → 网络 $128\\times128$，于是 $r=0.4$、$p_x=0$、$p_y=28$。"""),

    code("""# ── 合成图像：暗背景上贴几块「标志」（BGR uint8）──
#    紫色块 = 同时触发两个类别头（正是「限速60 / 限速80」那种细类互斥的情形）
PLANTED = [(60,  60, 30, 'red'), (200,  50, 26, 'blue'),
           (120, 120, 30, 'purple'), (250, 130, 22, 'red')]
BGR = {'red': (40, 40, 220), 'blue': (220, 60, 40), 'purple': (200, 40, 200)}

def make_image(seed=0, W=320, H=180):
    r = np.random.default_rng(seed)
    img = r.integers(30, 70, size=(H, W, 3)).astype(np.uint8)
    for cx, cy, s, col in PLANTED:
        img[cy - s // 2:cy + s // 2, cx - s // 2:cx + s // 2, :] = np.array(BGR[col], np.uint8)
    return img

def lb_image(img, p):
    H, W = img.shape[:2]
    out = np.full((p['Hn'], p['Wn'], 3), 114, np.uint8)
    ys = np.clip((np.arange(p['new_h']) / p['r']).astype(int), 0, H - 1)
    xs = np.clip((np.arange(p['new_w']) / p['r']).astype(int), 0, W - 1)
    y0, x0 = int(p['pad_y']), int(p['pad_x'])
    out[y0:y0 + p['new_h'], x0:x0 + p['new_w']] = img[np.ix_(ys, xs)]
    return out

def patch_mean(ch, stride=4, k=8):
    # ch: (Hn, Wn) -> (Hn/stride, Wn/stride) 的滑窗均值（k x k 窗口，stride 步长）
    Hn, Wn = ch.shape
    ny, nx = Hn // stride, Wn // stride
    out = np.zeros((ny, nx))
    for i in range(ny):
        for j in range(nx):
            y0, x0 = min(i * stride, Hn - k), min(j * stride, Wn - k)
            out[i, j] = ch[y0:y0 + k, x0:x0 + k].mean()
    return out

P128 = letterbox_params((180, 320), (128, 128))
print('letterbox:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in P128.items()})
assert abs(P128['r'] - 0.4) < 1e-12 and P128['pad_y'] == 28.0 and P128['pad_x'] == 0.0
img0 = make_image(0)
lb0 = lb_image(img0, P128)
print('原图', img0.shape, ' letterbox 后', lb0.shape,
      ' 上下 padding 值 =', int(lb0[0, 0, 0]), '(应为 114)')
assert lb0[0, 0, 0] == 114 and lb0[64, 64, 0] != 114
print('✅ 迷你管线的图像部分就位。')"""),

    code("""STRIDE, KWIN, NET = 4, 8, 128
MEAN, STD = 0.45, 0.25
BOX_W = 12.0                      # 迷你模型预测的固定框宽（30px 原图 x r=0.4 = 12px）

def run_pipeline(img, p, cfg):
    # 返回 8 个阶段的张量。cfg 里的每个开关对应一种真实世界的 bug。
    st = {}
    st['1_img_u8'] = img
    st['2_lb_u8'] = lb_image(img, p)

    x = st['2_lb_u8'].astype(np.float32) / 255.0
    x = x if cfg.get('bgr_swap') else x[:, :, ::-1]        # 正确：BGR -> RGB
    x = ((x - MEAN) / STD).transpose(2, 0, 1).astype(np.float32)
    st['3_input_f32'] = x

    respR, respB = patch_mean(x[0], STRIDE, KWIN), patch_mean(x[2], STRIDE, KWIN)
    logits = np.stack([5.0 * respR - 4.0, 5.0 * respB - 4.0], axis=-1)     # (ny,nx,2)
    ny, nx, _ = logits.shape
    gy, gx = np.meshgrid(np.arange(ny), np.arange(nx), indexing='ij')
    cxs = (gx * STRIDE + KWIN / 2).astype(np.float64)
    cys = (gy * STRIDE + KWIN / 2).astype(np.float64)
    bx = np.stack([cxs - BOX_W / 2, cys - BOX_W / 2,
                   cxs + BOX_W / 2, cys + BOX_W / 2], axis=-1)             # (ny,nx,4)
    st['4_raw'] = np.concatenate([bx, logits], axis=-1).reshape(-1, 6).astype(np.float32)

    sc = sigmoid(st['4_raw'][:, 4:6].astype(np.float64))
    if cfg.get('double_sigmoid'):
        sc = sigmoid(sc)                                   # bug：模型内外各做了一次
    st['5_scores'] = sc.astype(np.float32)

    B = st['4_raw'][:, :4].astype(np.float64)
    bb = np.repeat(B, 2, axis=0)
    ss = sc.reshape(-1)
    cc = np.tile(np.array([0, 1]), len(B))
    m = ss >= cfg.get('score_thr', 0.35)
    bb, ss, cc = bb[m], ss[m], cc[m]
    if cfg.get('topk_before'):                             # bug：截断放在 NMS **之前**
        sel = score_order(ss)[:cfg['topk_before']]
        bb, ss, cc = bb[sel], ss[sel], cc[sel]
    ordr = score_order(ss)
    st['6_cands'] = np.concatenate([bb, ss[:, None], cc[:, None]], axis=1)[ordr]

    bb, ss, cc = st['6_cands'][:, :4], st['6_cands'][:, 4], st['6_cands'][:, 5]
    mode = cfg.get('nms_mode', 'classwise')
    io = cfg.get('iou_offset', 0)
    k = (nms_agnostic(bb, ss, cc, 0.5, io) if mode == 'agnostic'
         else nms_classwise(bb, ss, cc, 0.5, io))
    st['7_keep'] = st['6_cands'][k]

    out = st['7_keep'].copy()
    inv = inv_E1 if cfg.get('inverse_no_pad') else lb_inverse     # bug：逆变换漏减 pad
    out[:, :4] = np.stack([inv(row[:4], p) for row in st['7_keep']]) if len(out) else out[:, :4]
    st['8_final'] = out
    return st

REF = run_pipeline(img0, P128, {})
for k, v in REF.items():
    print(f'{k:<14s} shape={str(v.shape):<16s} dtype={v.dtype}')
print('\\n最终检出（原图坐标 x1,y1,x2,y2,score,cls）:')
print(np.round(REF['8_final'], 1))
assert len(REF['7_keep']) >= 4, '4 块标志至少应检出 4 个框（紫色块占两类）'
gt_centers = np.array([[c[0], c[1]] for c in PLANTED], dtype=float)
det_centers = (REF['8_final'][:, :2] + REF['8_final'][:, 2:4]) / 2
for gc in gt_centers:
    assert np.min(np.linalg.norm(det_centers - gc, axis=1)) < 12.0, gc
print('\\n✅ 参考管线跑通：每块标志都被检出，且还原到原图坐标后中心误差 < 12 px。')"""),

    code("""# ── 对拍器：逐阶段比对 + 自动定位第一个失配阶段 ──
TOL = [('1_img_u8',    'int',   1,     'JPEG 解码器实现 / BGR-RGB 顺序'),
       ('2_lb_u8',     'int',   2,     'resize 插值方式 / align_corners / pad 值与位置'),
       ('3_input_f32', 'float', 1e-5,  'mean-std 数值 / 除 255 时机 / 通道顺序 / NCHW 转置'),
       ('4_raw',       'float', 1e-3,  'engine 不同 / 输入不同（量化误差应在此容差内）'),
       ('5_scores',    'float', 1e-4,  'sigmoid 做了几次 / softmax-vs-sigmoid / 背景类偏移'),
       ('6_cands',     'set',   1e-4,  'score_thr 数值 / topK 位置与大小 / per-class vs global'),
       ('7_keep',      'set',   1e-4,  'IoU 的 +1 / iou_thr / class-wise-vs-agnostic / 排序稳定性'),
       ('8_final',     'set',   0.5,   'letterbox 逆变换 / clip 范围与顺序 / 坐标格式')]

def stage_diff(a, b, kind):
    if a.shape != b.shape:
        return float('inf'), f'shape {a.shape} vs {b.shape}'
    if a.size == 0:
        return 0.0, 'empty'
    d = float(np.abs(a.astype(np.float64) - b.astype(np.float64)).max())
    return d, f'max_abs_diff={d:.3e}'

def locate(ref, test, verbose=True):
    # 返回第一个超出容差的阶段名；全过则返回 None
    first = None
    for name, kind, tol, hint in TOL:
        d, msg = stage_diff(ref[name], test[name], kind)
        ok = d <= tol
        if verbose:
            flag = 'PASS' if ok else 'FAIL'
            print(f'  [{flag}] {name:<13s} tol={tol:<7g} {msg:<28s}' + ('' if ok else f'-> {hint}'))
        if not ok and first is None:
            first = name
            if verbose:
                continue
            break
    return first

print('自检：参考管线与自己对拍，应当全过')
assert locate(REF, run_pipeline(img0, P128, {}), verbose=False) is None
print('  [PASS] 全部 8 个阶段\\n')

BUGS = [('通道顺序弄反（BGR/RGB）',   {'bgr_swap': True},        '3_input_f32'),
        ('sigmoid 做了两次',          {'double_sigmoid': True},  '5_scores'),
        ('topK 放在 NMS 之前',        {'topk_before': 6},        '6_cands'),
        ('NMS 用了 class-agnostic',   {'nms_mode': 'agnostic'},  '7_keep'),
        ('逆变换漏减 letterbox pad',  {'inverse_no_pad': True},  '8_final')]

for title, cfg, expect in BUGS:
    print(f'注入 bug：{title}')
    got = locate(REF, run_pipeline(img0, P128, cfg))
    print(f'  -> 定位到「{got}」，期望「{expect}」  {"✅" if got == expect else "❌"}\\n')
    assert got == expect, (title, got, expect)

print('✅ 五种 bug，五次定位全部正确 —— 而且**不需要知道 bug 是什么**，')
print('   只需要按顺序走一遍 8 个阶段。八个阶段用二分只要 3 步。')
print('⚠️  最关键的一条纪律：第 4 阶段两侧必须跑**同一个 engine**（Python 也用 TRT Python API 加载），')
print('    否则量化误差混进来，你就分不清后面的分歧是模型造成的还是后处理造成的。')"""),

    md("""## ✏️ 练习 1：IoU 约定何时会翻转抑制决策

实现 `will_flip(s, d, thr)`：两个边长 `s` 的正方形框沿对角线错开 `d` 像素，
判断 `offset=0` 与 `offset=1` 两种约定在阈值 `thr` 下是否给出**不同的抑制决策**。

- 抑制条件是 `IoU > thr`（等于阈值时保留）
- 返回 `True` 当且仅当两种约定一个抑制、一个保留"""),

    code("""def will_flip(s, d, thr):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert will_flip(8, 2, 0.41) is True,  '0.3913 <= 0.41 < 0.4336 -> 一边保留一边抑制'
assert will_flip(8, 2, 0.30) is False, '两种约定都 > 0.30 -> 都抑制'
assert will_flip(8, 2, 0.45) is False, '两种约定都 <= 0.45 -> 都保留'
assert will_flip(64, 16, 0.41) is False, '大框上 Δ 太小，翻不动'

flips = [s for s in range(4, 65) if will_flip(s, s / 4, 0.41)]
print('thr=0.41、相对位移 25% 时，会因为一个 +1 而翻转决策的框边长：', flips)
assert 8 in flips and 16 in flips
assert 32 not in flips and 64 not in flips
assert max(flips) < 25, '超过 ~20px 之后 Δ 就不足以跨过阈值了'
print(f'-> 临界边长约 {max(flips)} px。**TSR 的标志常年 10-30 px，正好全在危险区。**')
print('✅ 练习 1 通过：+1 约定是一个只在小目标上发作的 bug。')"""),

    md("""## ✏️ 练习 2：逆变换 + clip + 退化过滤

实现 `inverse_and_clean(boxes_net, p, min_size=1.0)`，返回 `(boxes_orig, keep_mask)`：

1. 用**正确顺序**逆变换回原图坐标（先减 pad，再除 r）
2. clip 到 `[0, W] × [0, H]`（`W`/`H` 取自 `p`）
3. 宽或高 `<= min_size` 的框标记为丢弃（`keep_mask[i] = False`）

返回的 `boxes_orig` 是**全部**框（clip 后），`keep_mask` 标记哪些有效。"""),

    code("""def inverse_and_clean(boxes_net, p, min_size=1.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（数字可口算：r=1/3, pad_y=140）——
tests = np.array([[100.0, 200.0, 140.0, 240.0],   # 正常框      -> [300, 180, 420, 300]
                  [300.0,  20.0, 340.0, 100.0],   # 全在上 pad  -> clip 后零高度 -> 丢弃
                  [ -5.0, 200.0,  20.0, 260.0],   # 左侧越界    -> x1 被 clip 到 0
                  [600.0, 200.0, 640.0, 260.0]])  # 右侧贴边    -> [1800, 180, 1920, 360]
out, mask = inverse_and_clean(tests, P640, min_size=1.0)
print('逆变换 + clip 结果：')
for i in range(len(tests)):
    print(f'  {tests[i]} -> {np.round(out[i],1)}   keep={bool(mask[i])}')

assert np.allclose(out[0], [300, 180, 420, 300])
assert np.allclose(out[1], [900, 0, 1020, 0])
assert np.allclose(out[2], [0, 180, 60, 360])
assert np.allclose(out[3], [1800, 180, 1920, 360])
assert mask.tolist() == [True, False, True, True]
assert out[:, 0].min() >= 0 and out[:, 2].max() <= P640['W']
assert out[:, 1].min() >= 0 and out[:, 3].max() <= P640['H']
print('\\n✅ 练习 2 通过：padding 区里的假框被正确丢弃，越界框被 clip 到原图内。')
print('   注意第 2 行 —— 如果 clip 发生在**网络坐标**下，这个框会作为「贴在图像上边缘的检测」被上报。')"""),

    md("""## ✏️ 练习 3：层次化 NMS

实现 `nms_hier(boxes, scores, cls, super_map, iou_thr=0.5, offset=0)`：

- `super_map` 是 `{类别 id: 超类名}`
- **同一超类内**做 class-agnostic NMS（细类互相抑制）
- **跨超类**互不抑制
- 返回升序排列的保留下标数组

两个退化情形必须自动成立：所有类同一超类 ⇒ 等价于 agnostic；每类各成一超类 ⇒ 等价于 class-wise。"""),

    code("""def nms_hier(boxes, scores, cls, super_map, iou_thr=0.5, offset=0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
kh = nms_hier(boxes_t, scores_t, cls_t, SUPER, 0.5)
print('层次化保留：', [CLS_NAME[int(cls_t[i])] for i in kh])
assert kh.tolist() == [0, 2, 3], kh.tolist()

all_same = {c: 'one' for c in range(4)}
assert np.array_equal(nms_hier(boxes_t, scores_t, cls_t, all_same, 0.5),
                      nms_agnostic(boxes_t, scores_t, cls_t, 0.5)), '退化情形 1'
each_own = {c: f's{c}' for c in range(4)}
assert np.array_equal(nms_hier(boxes_t, scores_t, cls_t, each_own, 0.5),
                      nms_classwise(boxes_t, scores_t, cls_t, 0.5)), '退化情形 2'

# 大场景上：层次化的保留数必须夹在 agnostic 与 class-wise 之间
b2, s2, _ = tsr_scene(30, np.random.default_rng(5), props=12)
c2 = np.random.default_rng(21).integers(0, 8, len(s2))
m2 = s2 >= 0.25
b2, s2, c2 = b2[m2], s2[m2], c2[m2]
SUP8 = {c: ('A' if c < 4 else 'B') for c in range(8)}      # 8 个细类归成 2 个超类
n_a = len(nms_agnostic(b2, s2, c2, 0.5))
n_h = len(nms_hier(b2, s2, c2, SUP8, 0.5))
n_c = len(nms_classwise(b2, s2, c2, 0.5))
print(f'\\nagnostic {n_a} 个  <  层次化(2 超类) {n_h} 个  <  class-wise(8 类) {n_c} 个')
assert n_a < n_h < n_c
print('✅ 练习 3 通过：层次化是 agnostic 与 class-wise 之间的连续谱，由「什么能共存」这个物理先验决定。')"""),

    md("""## ✏️ 练习 4：对拍定位器

实现 `first_mismatch(ref, test, spec)`：

- `spec` 是 `[(阶段名, 容差), ...]`，**按管线顺序排列**
- 逐阶段比较 `ref[name]` 与 `test[name]`：
  - shape 不同 → 直接判失配
  - 否则算 `max(|a - b|)`，`> 容差` 则判失配
- 返回**第一个**失配的阶段名；全部通过返回 `None`"""),

    code("""def first_mismatch(ref, test, spec):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
spec = [('a', 1.0), ('b', 1e-6), ('c', 0.5)]
ref_d = {'a': np.zeros(3), 'b': np.zeros((2, 2)), 'c': np.zeros(4)}
t1 = {'a': np.zeros(3), 'b': np.zeros((2, 2)), 'c': np.zeros(4)}
assert first_mismatch(ref_d, t1, spec) is None

t2 = dict(t1); t2['b'] = np.full((2, 2), 1e-3)
assert first_mismatch(ref_d, t2, spec) == 'b'

t3 = dict(t1); t3['b'] = np.zeros((3, 2))                  # shape 不同也算失配
assert first_mismatch(ref_d, t3, spec) == 'b'

t4 = dict(t1); t4['a'] = np.full(3, 0.5); t4['c'] = np.full(4, 9.0)
assert first_mismatch(ref_d, t4, spec) == 'c', 'a 在容差内，应跳过；第一个失配是 c'

# 接到真实管线上：五种 bug，五次定位
real_spec = [(name, tol) for name, kind, tol, hint in TOL]
for title, cfg, expect in BUGS:
    got = first_mismatch(REF, run_pipeline(img0, P128, cfg), real_spec)
    print(f'{title:<28s} -> {got}')
    assert got == expect, (title, got, expect)
assert first_mismatch(REF, run_pipeline(img0, P128, {}), real_spec) is None
print('\\n✅ 练习 4 通过：不到 15 行代码，把「后处理为什么对不上」从猜谜变成了查表。')
print('   把它接进 CI，用 5-10 张精选回归图跑 —— 这是本模块唯一能**防止**问题的一条。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def will_flip(s, d, thr):
    A = [0, 0, s, s]
    B = [d, d, s + d, s + d]
    sup0 = iou_pair(A, B, 0) > thr          # 抑制条件：IoU > thr
    sup1 = iou_pair(A, B, 1) > thr
    return bool(sup0 != sup1)"""),

    code("""# 练习 2 参考答案
def inverse_and_clean(boxes_net, p, min_size=1.0):
    b = np.asarray(boxes_net, dtype=float).copy()
    b[:, [0, 2]] = (b[:, [0, 2]] - p['pad_x']) / p['r']      # 先减 pad，再除 r
    b[:, [1, 3]] = (b[:, [1, 3]] - p['pad_y']) / p['r']
    b[:, [0, 2]] = np.clip(b[:, [0, 2]], 0, p['W'])          # clip 在**原图**坐标下
    b[:, [1, 3]] = np.clip(b[:, [1, 3]], 0, p['H'])
    keep = (b[:, 2] - b[:, 0] > min_size) & (b[:, 3] - b[:, 1] > min_size)
    return b, keep"""),

    code("""# 练习 3 参考答案
def nms_hier(boxes, scores, cls, super_map, iou_thr=0.5, offset=0):
    sup = np.array([super_map[int(c)] for c in cls])
    keep = []
    for u in np.unique(sup):                                 # 跨超类互不抑制
        idx = np.where(sup == u)[0]
        keep.append(idx[nms(boxes[idx], scores[idx], iou_thr, offset)])   # 超类内 agnostic
    return np.sort(np.concatenate(keep)) if keep else np.zeros(0, dtype=int)"""),

    code("""# 练习 4 参考答案
def first_mismatch(ref, test, spec):
    for name, tol in spec:
        a, b = np.asarray(ref[name]), np.asarray(test[name])
        if a.shape != b.shape:
            return name
        if a.size and float(np.abs(a.astype(np.float64) - b.astype(np.float64)).max()) > tol:
            return name
    return None"""),

    md("""---
## 🧪 真实工程胶囊：后处理对齐 spec + C++ 管线检查单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 第一部分：后处理 SPEC（这份文件是三方实现的唯一真相源）
#   把它放进仓库，Python 参考实现 / C++ 实现 / TRT plugin 配置都必须对齐到它
# ══════════════════════════════════════════════════════════════════════
postprocess_spec:
  activation:      sigmoid          # 在**模型外**做；ONNX 里禁止出现 Sigmoid 节点
  background_class: none            # sigmoid 头无背景类，class_id 从 0 开始
  box_format:      cxcywh           # 模型原始输出格式
  box_normalized:  false            # 像素坐标，**相对于网络输入 640x640（含 padding）**
  score_threshold: 0.05             # 只用于控计算量；真正的工作点阈值在 spec 之外二次过滤
  topk_before_nms: 4096             # ← 按「单帧最大过阈候选数」留 2-3 倍余量
  nms:
    iou_threshold: 0.55
    iou_offset:    0                # ← **COCO 连续坐标语义，不加 +1**
    mode:          hierarchical     # 超类内 agnostic，跨超类不抑制
    superclass_map: superclass_v3.yaml
    suppress_cond: "iou > thr"      # 等于阈值时**保留**
    sort_key:      "(-score, flat_index)"   # ← 确定性全序，INT8 下并列分数不再有歧义
  max_det:         300              # ← NMS **之后**的截断，与 topk_before_nms 是两回事
  inverse:
    order:         "subtract_pad_then_divide_r"     # ← 顺序写死在 spec 里
    clip_space:    original_image                   # 不是网络输入！
    min_box_size:  1.0                              # 退化框直接丢弃
  emit_competing_hypotheses: true   # 被同超类抑制掉的 (类别, 分数) 随框上报给下游

# ══════════════════════════════════════════════════════════════════════
# 第二部分：SPEC 测试用例（每一条对应本模块讲过的一个坑）
# ══════════════════════════════════════════════════════════════════════
# T1  IoU 恰好等于阈值的一对框            -> 验证 ">" 而不是 ">="
# T2  分数完全相同的一对框                -> 验证确定性排序（INT8 必测）
# T3  面积为 0 / 坐标为负 / 超出边界的框   -> 验证退化过滤
# T4  单帧候选数 > topk_before_nms 的密集帧 -> 验证截断位置（NMS 前 vs 后）
# T5  同位置双类高分（限速60/80）          -> 验证层次化 NMS 与竞争假设上报
# T6  主牌 + 紧贴的辅助牌                  -> 验证跨超类不抑制
# T7  完全落在 letterbox padding 区的候选  -> 验证 clip 在原图坐标下做
# T8  非对称长宽比输入（如 1920x1084）     -> 验证亚像素取整一致
#
# ══════════════════════════════════════════════════════════════════════
# 第三部分：端到端对拍工具（项目第一天就要有，不是出事之后）
# ══════════════════════════════════════════════════════════════════════
# C++ 侧编译 debug 模式：./tsr_infer --image a.jpg --dump-stage=all --dump-dir=/tmp/cpp
#   写 .npy 不需要任何依赖，格式很简单（魔数 \x93NUMPY + header + 裸数据），约 100 行
# Python 侧：python tools/xdiff.py --ref /tmp/py --test /tmp/cpp --spec stages.yaml
#
# **纪律 1**：两侧第 4 阶段必须跑同一个 engine（Python 用 tensorrt 的 Python API 加载）
#             否则量化误差混进来，模型层与后处理层就分不开了
# **纪律 2**：第 6/7 阶段的容差是「个数完全相等」，不是「数值接近」
#             因为 NMS 是不连续算子，1 个候选的差别会放大成几十个框的差别
# **纪律 3**：回归图要精选 —— 稀疏帧 / 密集帧 / INT8 并列帧 / 贴边缘帧 / 极端长宽比帧
#
# ══════════════════════════════════════════════════════════════════════
# 第四部分：C++ 推理管线检查单
# ══════════════════════════════════════════════════════════════════════
# [内存]
#   □ 稳态运行期**零** cudaMalloc / cudaFree（它们会隐式同步整个 device）
#   □ 动态 shape 下按 max profile 一次性分配
#   □ host 侧全部用 cudaHostAlloc（pinned）—— pageable 上的 MemcpyAsync 实际是同步的
#   □ 输入/输出 buffer 双缓冲，避免第 k 帧后处理与第 k+1 帧推理竞争
# [流与同步]
#   □ 预处理 kernel / enqueueV3 / 后处理 kernel / D2H 全部挂同一条 stream
#   □ **每帧只允许一次 cudaStreamSynchronize**（在读取最终结果时）
#   □ 全局搜一遍 cudaDeviceSynchronize / 非 Async 的 Memcpy / Memset，确认没有漏网的
#   □ 用 Nsight Systems 看 CPU 与 GPU 泳道是否重叠；交替 = 有多余同步
# [零拷贝]
#   □ 判据是「这块数据被读几次」：只读一次 -> 零拷贝划算；反复读 -> 拷到 device memory
#   □ mapped pinned memory 在 Orin 上通常 uncached，**CPU 读它非常慢**
# [线程模型]
#   □ 车端选延迟不选吞吐：单线程 + GPU 预处理 或 双缓冲 2 线程
#   □ 3 阶段流水线吞吐最高但延迟约等于三段之和 —— 那是数据中心的最佳实践，不是车端的
# [相机对接]
#   □ 时间戳用**曝光中点**，不是帧到达时刻（100 km/h 下 10 ms = 0.28 m 纵向误差）
#   □ 队列满时丢**最老**的帧，且丢帧必须计数并把 frame_id 传给下游
#   □ 多相机硬件同步，否则跨相机关联会失败
# [错误处理]
#   □ CUDA 错误是粘性的：每次调用都 check，一次 error 之后所有调用返回同一个 error
#   □ 对拍用容差不用 ==：TRT 部分 kernel 用 atomic 累加，浮点加法不满足结合律
'''
print(RECIPE)
for token in ['iou_offset', 'topk_before_nms', 'max_det', 'sort_key',
              'subtract_pad_then_divide_r', 'clip_space', 'cudaHostAlloc',
              '曝光中点', '同一个 engine']:
    assert token in RECIPE, token
print('✅ 胶囊覆盖：SPEC / 测试用例 / 对拍工具纪律 / C++ 管线（内存·流·零拷贝·线程·相机·错误）')"""),

    md("""### 小结

- **后处理是唯一一段「两份实现、零份约束」的代码。** 预处理和模型至少有同一份 ONNX 作锚点，
  后处理只有口头约定。它的 bug 不报错、不崩溃，只把 mAP 从 0.82 磨到 0.71，
  **然后你会花两周去怀疑量化。**
- **IoU 的 `+1` 是尺度相关的**：$\\Delta(s) \\sim \\mathcal{O}(1/s)$，8 px 框差 0.042，64 px 框只差 0.006。
  `thr=0.41`、相对位移 25% 时，**临界边长约 18 px** —— TSR 的标志正好全在危险区。
  一致性是「标注 / 训练+评测 / 部署」**三方**一致，不是两方。
- **NMS 前的 topK ≠ NMS 后的 max_det。** 前者作用在未去重的候选上：密集帧里 topK=100 只覆盖了
  26/60 个目标，而不截断能覆盖 54/60；**稀疏帧上两者完全一样**——所以离线评测测不出来。
- **`σ(σ(x))` 是最阴险的 bug**：分数全被压进 (0.5, 0.731)，阈值彻底失效、候选数暴涨、
  线上 FP 爆炸，而 **AP 一个字节都不变**（单调变换不改排序）。诊断只要 `print(scores.min())`。
- **4 px 的系统性偏移**：100 px 大牌 IoU 还有 **0.855**（永远发现不了），
  12 px 小牌只剩 **0.286**（IoU=0.5 口径下算完全漏检）。
  **凡是「只有小目标桶掉点」，第一怀疑对象永远是坐标变换，不是模型能力。**
- **NMS 模式在编码「什么在物理世界里能共存」**：同一块牌子不能既是限速 60 又是限速 80（该抑制），
  主牌和辅助牌是两块物理牌子（不该抑制）→ **层次化 NMS**。
  而且被抑制的类别与分数应作为「竞争假设」上报，让下游做多帧贝叶斯累积而不是对硬判决投票。
- **防线不是「小心」，是「spec + 逐阶段对拍 + CI」**：8 个阶段、逐阶段容差、二分定位；
  五种注入 bug 全部一次命中。关键纪律是**两侧第 4 阶段必须跑同一个 engine**，
  以及**在不连续算子处（阈值、排序、NMS）把容差收紧成「完全相等」**。

下一站：**模块 05 · 性能剖析与延迟工程** —— 语义都对齐了，接下来是它跑得够不够快、够不够稳。"""),
]
