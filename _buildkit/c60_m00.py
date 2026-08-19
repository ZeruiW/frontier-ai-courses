# -*- coding: utf-8 -*-
"""C60 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "Python/numpy；C52（模型导出与运行时）、C27（量化原理）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 复现对拍、二分定位、校准与延迟统计"),
    ("预计时长", "总览 35 分钟 + notebook 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("story", "「离线 mAP 0.82，车上跑起来像 0.6」", "".join([
        P("这门课从一个几乎每个感知团队都经历过的场景开始。"),
        P("模型训完了，验证集 mAP 0.82，分尺寸桶看小目标也还行，回归门禁全绿，模型卡签完字。转 ONNX，转 TensorRT，C++ 管线接上相机，装车，上路。<strong>然后测试同学回来说：「感觉不太行，好多牌子看不见，限速 60 有时候报成 80。」</strong>你问他掉了多少，他说不上来——他只有体感。你自己去看录像，估了个数：<em>大概相当于离线 0.6 的水平</em>。"),
        P("这时候有两种工程师。"),
        TABLE(["", "做法", "结果"], [
            ["<strong>A 类</strong>", "「先把训练集里加点夜间数据吧」「要不 QAT 试试」「换个更大的 backbone」", "两周后 mAP 还是 0.6 —— 因为<strong>问题根本不在模型里</strong>"],
            ["<strong>B 类</strong>", "「拿同一张图，两边把每一步的中间张量 dump 出来，逐元素 diff，看第一个对不上的算子是哪个」", "<strong>25 分钟后</strong>：C++ 侧的 <code>cv2.resize</code> 用了 <code>INTER_LINEAR</code>，训练侧用的是 <code>INTER_AREA</code>"],
        ]),
        P("A 类的做法看起来更「像在做算法」，但它是<strong>把一个确定性的软件缺陷当成统计问题去治</strong>。这类改动不但修不好问题，还会污染后面所有的实验——你在一个错误的输入分布上调出来的一切超参，等你修好预处理之后全都要作废。"),
        H3("真实原因的分布"),
        P("综合公开的部署事故复盘、框架 issue 与工程经验，「离线好、上车差」的根因大致是这样分布的。<strong>这张表的排序才是你排查的顺序</strong>："),
        TABLE(["根因层", "占比（经验量级）", "典型表现", "定位成本"], [
            ["<strong>预处理不一致</strong>", "<strong>≈ 40%</strong>", "resize 插值/语义不同、BGR/RGB、letterbox 变体、归一化顺序", "<strong>低</strong>（一张图对拍就能看出来）"],
            ["<strong>后处理 / 坐标变换不一致</strong>", "≈ 25%", "框整体偏移、NMS 语义不同、sigmoid 做了两遍或没做", "低（框的偏移量本身就是线索）"],
            ["数值精度 / 量化", "≈ 15%", "FP16 溢出、INT8 校准集分布不对、敏感层被量化", "中（要逐层敏感度分析）"],
            ["评测口径不一致", "≈ 10%", "离线用 GT crop、离线不含时序、离线的类别表和车上不一样", "中（要重建对齐的评测协议）"],
            ["<strong>真实域差</strong>（模型确实不够好）", "<strong>≈ 10%</strong>", "ISP 输出与 JPEG 训练图的域差、天气/地域分布外", "<strong>高</strong>（要数据闭环，见 C58）"],
        ]),
        DUAL(
            "读这张表最重要的收获是：<strong>你以为的「模型不够好」，十次里有八次不是模型的问题。</strong>但绝大多数团队的默认反应是去改模型——因为改模型是他们熟悉的动作，而对拍中间张量不是。<em>这门课要做的，就是把「对拍」变成和「调参」一样自然的动作。</em>",
            "更严谨地说：前四行的共同特征是<strong>它们都是可判定的（decidable）</strong>——存在一个有限的、确定性的检查过程，能在有限时间内给出「一致 / 不一致，且不一致在第 k 步」的结论。只有最后一行是<em>统计性</em>的，需要收集数据、重新训练、再用假设检验判断。<strong>工程纪律是：把可判定的部分全部排干净，再动统计的部分。</strong>顺序颠倒的代价是：你无法区分「模型不够好」和「模型没吃到你以为的输入」，于是所有实验结论都不可信。",
        ),
        CALLOUT("danger", "<p><strong>面试高频，而且是分水岭题</strong>：「你训好的模型部署到车上掉点了，你怎么查？」<em>初级答案</em>：「加数据 / 做 QAT / 换更大的模型」——面试官立刻知道你没上过线。<em>合格答案</em>：「先确认这不是软件缺陷：拿同一张图，训练侧和部署侧各 dump 一遍逐阶段的中间张量，从输入开始逐元素比对，二分定位到第一个分歧算子。<strong>只有当逐层张量都在容差内、而端到端指标仍然掉，才轮到讨论量化和域差。</strong>」<em>加分答案</em>：再补一句「而且我会先问一个问题：<strong>车上那个 0.6 是怎么测出来的？</strong>如果离线评测和车上评测的口径本身不一致（比如离线用 GT crop 做分类、车上是端到端），那这两个数根本不可比，先对齐评测协议再说」。</p>", "「掉点了怎么查」——不要从模型答起"),
    ])),

    # ============================================================== 2
    ("thesis", "核心主张：一致性是可验证的工程属性，不是运气", "".join([
        P("本课只有一个中心论点，其余五个模块都是它的展开："),
        CALLOUT("intuition", "<strong>训练-部署一致性不是「小心一点就能做到」的品质，而是一个可以被<u>定义、被度量、被自动检查、被写进 CI</u> 的工程属性。</strong>你不应该「希望」两边一致，你应该<em>有一个脚本能证明它一致，并在不一致时告诉你是哪一行代码</em>。"),
        P("这句话的分量在于它的反面。<strong>如果一致性只是「注意事项」，那么它必然会退化</strong>——因为代码会被改、库会升版本、新同事会用他熟悉的写法、C++ 侧的重写会「顺手优化一下」。任何依赖人自觉的约束，在一个 30 人的团队里、在 18 个月的项目周期里，都会归零。"),
        H3("把一致性变成属性，需要三件东西"),
        TABLE(["要素", "具体是什么", "缺了它会怎样"], [
            ["<strong>① 可比较的中间产物</strong>", "两侧管线都能按<em>同一组阶段名</em> dump 中间张量到磁盘（<code>.npy</code>），且 dump 是<strong>默认能力</strong>而不是临时插的 print", "只能比端到端结果。看到「框不对」但不知道错在哪一步，只能猜"],
            ["<strong>② 明确的容差</strong>", "对每个阶段规定「差多少算一致」，并且这个数字有来源（见第 5 节）", "要么把 fp16 的正常抖动当 bug 追一周，要么把真错误当成「正常误差」放过去"],
            ["<strong>③ 自动化的判定</strong>", "一条命令跑完全部阶段，输出 PASS/FAIL + 首个分歧阶段；接到 CI 上，每次改预处理都跑", "人工比对只会做一次。第二次出问题时，那个脚本已经找不到了"],
            ["<strong>④ 黄金样本集</strong>", "10–30 张覆盖极端情况的固定图（最亮、最暗、纯色、边界尺寸、含极小目标），连同期望输出一起入库", "只用一张「正常」图对拍，会漏掉只在边界条件下触发的 bug（如 clip、溢出、奇偶尺寸）"],
        ]),
        DUAL(
            "换个角度：<strong>这四件事加起来，就是给感知管线写「单元测试」</strong>。你不会接受一个没有单元测试的后端服务，但整个行业长期接受没有对拍脚本的感知管线——原因只是「模型是黑盒，没法测」。<em>但预处理不是黑盒，后处理不是黑盒，坐标变换不是黑盒。真正是黑盒的只有中间那一坨卷积，而它恰恰是最不容易出错的部分（因为它由框架保证）。</em>",
            "更精确地说，本课把端到端管线建模成一个有序的算子序列 $g = f_n \\circ \\cdots \\circ f_1$，训练侧与部署侧分别是 $g^{\\text{tr}}$ 与 $g^{\\text{dp}}$。<strong>「一致」的形式化定义是：对黄金样本集里的每个输入 $x$ 和每个阶段 $k$，都有 $\\lVert h_k^{\\text{tr}}(x) - h_k^{\\text{dp}}(x)\\rVert \\le \\tau_k$</strong>，其中 $h_k = f_k \\circ \\cdots \\circ f_1$ 是前 $k$ 阶段的复合，$\\tau_k$ 是该阶段的容差。<em>注意这是一个比「端到端输出接近」强得多的条件</em>——它排除了「两个错误互相抵消」这种最危险的情况（今天抵消了，明天改一行代码就不抵消了）。",
        ),
        CALLOUT("warn", "「端到端结果差不多」<strong>不能</strong>推出「管线一致」。真实案例：训练侧 BGR + 一组 mean/std，部署侧 RGB + 交换过的 mean/std，两个错误互相抵消，端到端完全正确——直到有人「顺手修正」了其中一个。<em>逐阶段比对是唯一能发现这种「稳定的错误」的方法。</em>"),
    ])),

    # ============================================================== 3
    ("layers", "三层鸿沟：预处理 / 模型 / 后处理", "".join([
        P("把一条完整的车端检测管线摊开，它长这样。<strong>左边是训练时 Python 里跑的，右边是车上 C++ 跑的；中间每一条虚线都是一个可能的分歧点</strong>："),
        ASCII("""  训练侧（Python / PyTorch）                       部署侧（C++ / TensorRT）
  ─────────────────────────────                   ─────────────────────────────
                                     ┌ 第 ① 层 ─ 预 处 理 ─────────┐
   JPEG 解码 (PIL / cv2)      ⋯⋯⋯⋯⋯⋯⋯│ ISP 输出 (YUV/Bayer→RGB)    │  ← 域差，不是 bug
   cvtColor BGR→RGB           ⋯⋯⋯⋯⋯⋯⋯│ 通道顺序？                  │  ← **头号杀手之一**
   resize(INTER_AREA)         ⋯⋯⋯⋯⋯⋯⋯│ resize(INTER_LINEAR)?       │  ← **头号杀手**
   letterbox(114, 居中, /32)  ⋯⋯⋯⋯⋯⋯⋯│ letterbox(0, 左上, 全 pad)? │  ← 六个自由度
   uint8 → float32            ⋯⋯⋯⋯⋯⋯⋯│ 何时转？溢出？              │
   (x - mean) / std           ⋯⋯⋯⋯⋯⋯⋯│ 顺序？先 /255 还是先减？    │
   HWC → CHW, NCHW            ⋯⋯⋯⋯⋯⋯⋯│ 布局 / stride / 对齐        │
                                     └─────────────────────────────┘   ← 模块 01
                                     ┌ 第 ② 层 ─ 模 型 ───────────┐
   nn.Module forward          ⋯⋯⋯⋯⋯⋯⋯│ ONNX → TRT engine           │
   fp32                       ⋯⋯⋯⋯⋯⋯⋯│ fp16 / int8                 │  ← 模块 02/03
   BN 在 eval 模式             ⋯⋯⋯⋯⋯⋯⋯│ Conv+BN 已融合              │
   动态 shape                  ⋯⋯⋯⋯⋯⋯⋯│ optimization profile        │
                                     └─────────────────────────────┘
                                     ┌ 第 ③ 层 ─ 后 处 理 ─────────┐
   sigmoid / softmax          ⋯⋯⋯⋯⋯⋯⋯│ 在模型里还是模型外？        │  ← 做两遍 = 全错
   decode (cxcywh→xyxy)       ⋯⋯⋯⋯⋯⋯⋯│ 格式？归一化坐标？          │
   NMS(class-wise, iou .65)   ⋯⋯⋯⋯⋯⋯⋯│ EfficientNMS(agnostic)?     │  ← 模块 04
   letterbox 逆变换            ⋯⋯⋯⋯⋯⋯⋯│ 减 pad 了吗？除以 r 了吗？  │  ← **框整体偏移**
                                     └─────────────────────────────┘
                                            ▼
                                     最终框 → 跟踪 → 融合 → 规控"""),
        P("三层的性质完全不同，<strong>因此排查手段也完全不同</strong>："),
        TABLE(["", "① 预处理", "② 模型", "③ 后处理"], [
            ["错误性质", "<strong>确定性</strong>（同一输入必然同一错误）", "数值性（精度损失，随输入分布变化）", "<strong>确定性</strong>"],
            ["是否可精确对拍", "<strong>可以，可以要求 bit 级或 ≤1 灰阶</strong>", "不行，只能给统计容差", "<strong>可以（除了 NMS 的并列打破）</strong>"],
            ["典型症状", "分数整体偏低、类别系统性错、小目标全丢", "个别样本掉、长尾类先掉、小目标先掉", "<strong>框整体偏移 / 重复框 / 框数不对</strong>"],
            ["定位工具", "逐阶段张量 diff", "逐层敏感度分析 + 校准集检查", "逐阶段中间结果 diff + 反变换单测"],
            ["修复成本", "<strong>几行代码</strong>", "中（可能要重新校准或混合精度）", "<strong>几行代码</strong>"],
            ["本课模块", "<strong>01</strong>", "02（TensorRT）/ 03（INT8）", "<strong>04</strong>"],
        ]),
        DUAL(
            "注意第一行和最后一行的组合意味着什么：<strong>65% 的部署事故（预处理 40% + 后处理 25%，见第 1 节的分布）都是确定性的、可精确对拍的、几行代码就能修的</strong>。它们之所以能拖住团队两周，唯一的原因是<em>没人去查</em>——大家在猜。而猜的成本是：每猜一次要重训一次，一次几天。",
            "从软件工程视角，第 ① ③ 层属于<span class=\"term\">deterministic transformation</span>（确定性变换），可以用<strong>等价性测试</strong>（两个实现对同一输入产生相同输出）来验证，这类测试的判定是完备的；第 ② 层属于<span class=\"term\">numerical approximation</span>（数值近似），只能用<strong>统计性验收</strong>（在一个分布上误差的某个分位数小于阈值）。<em>把统计方法用在确定性问题上是过度宽容（会放过真 bug），把确定性方法用在数值问题上是过度严格（会把 fp16 的正常抖动报成失败）。</em><strong>知道每一层该用哪种判据，是这门课想教会你的最基本的判断力。</strong>",
        ),
        CALLOUT("warn", "别忘了第 ① 层最上面那条虚线——<strong>ISP 输出 vs JPEG 解码图</strong>。这一条<em>不是 bug，而是真实的域差</em>：训练数据是「相机 → ISP → JPEG 编码 → 解码」的产物，车上拿到的是「相机 → ISP」的直出。JPEG 的 8×8 DCT 量化会抹掉高频、引入块效应，而这恰恰改变了小目标的表观。<strong>它不能靠对拍修，只能靠采集端对齐或增强模拟（C56 模块 02）。</strong>把它和真 bug 混在一起查，是很多团队卡住的原因。"),
    ])),

    # ============================================================== 4
    ("bisect", "方法论：逐层二分，30 分钟定位到具体算子", "".join([
        P("本课的核心主张里还有一句更强的断言：<strong>任何一致性问题都能在 30 分钟内定位到具体的算子，只要你有对拍工具。</strong>这不是修辞，它有一个精确的复杂度依据。"),
        H3("为什么是「二分」而不是「从头看到尾」"),
        P("把管线的 $n$ 个阶段编号为 $1..n$。定义指示函数 $D(k) = \\mathbb{1}\\bigl[\\lVert h_k^{\\text{tr}}(x) - h_k^{\\text{dp}}(x)\\rVert > \\tau_k\\bigr]$，即「跑到第 $k$ 阶段为止，两侧是否已经分歧」。关键观察是："),
        MATH("D(k) \\text{ 关于 } k \\text{ 单调}：\\quad D(k)=1 \\;\\Longrightarrow\\; D(k')=1 \\ \\ \\forall k' > k"),
        P("一旦两条管线在某一步产生了实质分歧，后面的算子只会把这个差异传下去或放大，<strong>不会自己愈合</strong>。单调的布尔序列上找第一个 1，就是教科书上的二分查找，代价是："),
        MATH("\\text{探针次数} \\;=\\; \\lceil \\log_2 (n+1) \\rceil \\quad\\Longrightarrow\\quad n=16 \\text{ 阶段只需 } 5 \\text{ 次}, \\ \\ n=1000 \\text{ 只需 } 10 \\text{ 次}"),
        ASCII("""管线 12 个阶段，分歧首次出现在第 7 个（resize）
阶段:  1   2   3   4   5   6   7   8   9  10  11  12
D(k):  0   0   0   0   0   0   1   1   1   1   1   1
                               ↑ 要找的就是这个位置

探针 1: k=6   D=0  → 分歧在 (6, 12]        区间 12 → 6
探针 2: k=9   D=1  → 分歧在 (6,  9]        区间  6 → 3
探针 3: k=7   D=1  → 分歧在 (6,  7]        区间  3 → 1
                    ⇒ **第 7 个算子 = resize**       共 3 次探针

对照「从头看到尾」：最坏 12 次，且每次都要人眼看数组
对照「凭经验猜」   ：无上界，且猜错时你不知道自己猜错了""")

        ,
        H3("30 分钟是怎么来的"),
        TABLE(["步骤", "内容", "耗时"], [
            ["1", "选一张黄金样本图（不要选「正常」图，选一张有小目标 + 有饱和区的）", "2 min"],
            ["2", "两侧各加一次 dump：<code>np.save(f'{stage}_{side}.npy', t)</code>", "<strong>10 min</strong>（如果 dump 是内建能力则 0）"],
            ["3", "跑一遍二分：$\\lceil\\log_2 n\\rceil \\approx 4$ 次比较", "5 min"],
            ["4", "看首个分歧阶段的两个张量：diff 的<strong>空间结构</strong>就是指纹（见下表）", "<strong>5 min</strong>"],
            ["5", "读那一行代码，改掉，重跑对拍确认全绿", "8 min"],
        ]),
        H3("diff 的形状就是指纹"),
        P("找到分歧阶段之后不要急着读代码，<strong>先看 diff 张量长什么样</strong>——它的空间结构几乎直接告诉你原因："),
        TABLE(["diff 的样子", "几乎可以确定的原因"], [
            ["<strong>只在边缘一圈非零，中间全 0</strong>", "<code>align_corners</code> 语义不同 / padding 值不同 / 卷积 padding 模式不同"],
            ["<strong>棋盘格 / 条纹状高频结构</strong>", "<strong>resize 插值方式不同（混叠）</strong>——见模块 01 第 4 节"],
            ["<strong>通道 0 与通道 2 互换后 diff 变 0</strong>", "<strong>BGR/RGB 弄反</strong>"],
            ["整幅均匀的常数偏移", "mean 不同 / uint8→float 的时机不同"],
            ["整幅按比例缩放（diff/ref 是常数）", "std 不同 / 少除或多除了一次 255"],
            ["全图几乎恒定、动态范围极小", "<strong>归一化顺序错</strong>（先 /255 又减了 0–255 量纲的 mean）"],
            ["整体平移了固定像素", "letterbox 的 pad 位置不同 / 逆变换忘了减 pad"],
            ["零散、无结构、幅值 ~1e-3", "<strong>正常的数值噪声</strong>（fp16 / 定点舍入）——不是 bug"],
        ]),
        DUAL(
            "这张表值得贴在工位上。<strong>它把「调试」从「读代码猜」变成「看图认」</strong>——而人眼识别空间结构的速度远快于阅读代码。<em>实际操作中，第 4 步经常在 30 秒内就结束了：一眼看到条纹，直接去查 resize。</em>",
            "背后的原理是：每一类预处理错误在张量空间里都有<strong>特征性的支撑集（support）与频谱</strong>。插值语义差异的能量集中在高频（因为它改变的是采样相位），padding 差异的支撑集是边界带，通道错误在通道维上是置换，仿射参数错误表现为低秩的常数/线性场。<em>换句话说，diff 张量本身就是一个信道，错误类型是它承载的信号，而你只需要一个粗糙的分类器——你的眼睛。</em><strong>模块 01 的 notebook 会把这个「分类器」写成代码，让它自动输出定位报告。</strong>",
        ),
        CALLOUT("intuition", "把方法论压成一句：<strong>不要问「为什么模型效果差」，要问「第一个对不上的张量在哪」。前者没有终点，后者最多 $\\lceil\\log_2 n\\rceil$ 步。</strong>"),
    ])),

    # ============================================================== 5
    ("tolerance", "容差怎么定：多大的差才算「不一致」", "".join([
        P("对拍工具最容易失败的地方不是写不出来，而是<strong>阈值定错</strong>。定得太严，每次都红，团队很快就把它关掉；定得太松，真 bug 混过去，工具形同虚设。<em>容差必须有来源，不能拍脑袋。</em>"),
        P("好消息是：不同来源的差异，量级相隔一到两个数量级，<strong>所以只要你知道每一档的典型值，阈值就是显然的</strong>。下表的数字都会在 notebook 与模块 01 里被实测出来（归一化用 <code>std=58.395</code>，「tensor 单位」指归一化之后的张量）："),
        TABLE(["差异来源", "性质", "典型量级（tensor 单位）", "该不该报警"], [
            ["fp32 → fp16 的表示误差", "不可避免", "<strong>≈ 5×10⁻⁴</strong>（max）", "❌ 不报"],
            ["定点 resize 的舍入（OpenCV uint8 输出）", "实现细节", "≤ 0.5 灰阶 ≈ <strong>8.6×10⁻³</strong>", "❌ 不报（但要知道它的存在）"],
            ["INT8 量化", "有损，可控", "1×10⁻² ~ 1×10⁻¹（逐层放大）", "⚠️ 用<strong>端到端指标</strong>判，不用张量判"],
            ["<code>align_corners</code> 语义不同", "<strong>语义错误</strong>", "≈ <strong>3.8×10⁻²</strong>（自然图，均值）", "✅ <strong>报</strong>"],
            ["INTER_LINEAR ↔ INTER_AREA", "<strong>语义错误</strong>", "≈ <strong>0.37</strong>（自然图，均值 21 灰阶）", "✅ <strong>报</strong>"],
            ["BGR/RGB 弄反", "<strong>语义错误</strong>", "0.5 ~ 2（取决于图像色彩）", "✅ <strong>报</strong>"],
            ["归一化顺序错", "<strong>灾难</strong>", "动态范围被压缩 <strong>255 倍</strong>", "✅ <strong>报</strong>"],
        ]),
        P("最上面三行和最下面四行之间有<strong>一个数量级以上的空档</strong>，阈值就放在这个空档里。一个在实践中很好用的默认值："),
        CODE("""# 预处理阶段（确定性变换）：严
assert np.abs(a - b).max()  < 0.02      # tensor 单位；fp16 噪声的 20 倍，语义错误的 1/2
assert np.abs(a - b).mean() < 0.005

# 模型输出（数值近似）：用分位数，别用 max —— 单个离群元素说明不了问题
d = np.abs(a - b) / (np.abs(b) + 1e-3)
assert np.percentile(d, 99) < 0.02      # fp16
assert np.percentile(d, 99) < 0.10      # int8

# 最终框（语义等价）：只比语义，不比浮点
#   · 框中心偏移 < 0.5 px  且  IoU > 0.99
#   · 类别完全一致；分数排序的 Kendall tau > 0.99
#   · **框的个数必须完全相等** —— 个数不等通常是 NMS 语义不同，不是数值问题"""),
        DUAL(
            "注意最后一块的思路转变：<strong>到了输出端就不要再比浮点数了，要比「语义」</strong>。两侧 NMS 在分数并列时打破平局的方式不同，会让保留的框换一个（但完全等价）；这时逐元素 diff 会报错，而「框个数相同、IoU>0.99、类别相同」这个判据就正确地放过了它。<em>比什么，比怎么比更重要。</em>",
            "更一般的原则是：<strong>容差应当定义在「该阶段的语义空间」上，而不是统一定义在浮点数上</strong>。预处理阶段的语义空间就是像素张量本身，所以逐元素比对是对的；检测输出的语义空间是「框的集合」，它对元素顺序不敏感、对 1e-6 的坐标抖动不敏感，但对<em>集合的基数</em>极其敏感。<span class=\"term\">metric mismatch</span>（度量错配）——用错误的度量去比较——会同时产生假阳性和假阴性，是对拍工具被团队放弃的最常见原因。",
        ),
        CALLOUT("danger", "<p><strong>一个反直觉但极其重要的点：不要用「端到端 mAP 差不多」作为一致性的通过条件。</strong>原因有二：<em>①灵敏度不够</em>——预处理的中等错误可能只让整体 mAP 掉 2–3 点，落在种子方差的量级里（C61 模块 01），你会判它「没问题」；但同一个错误可能让「限速 60/80」这类<u>细粒度小目标类</u>掉 15 点以上（模块 01 会实测出这个数）。<em>②归因不了</em>——mAP 是一个标量，它告诉不了你错在哪。<strong>正确的关系是：逐阶段张量对拍是<u>门禁</u>，端到端指标是<u>验收</u>，两者不能互相替代。</strong></p>", "别拿 mAP 当一致性检查"),
    ])),

    # ============================================================== 6
    ("map", "课程地图与环境", "".join([
        P("六个模块严格按「三层鸿沟 + 一层工程」的结构排列，<strong>顺序就是排查顺序</strong>——先修概率最高、成本最低的："),
        TABLE(["模块", "主题", "对应的层", "你会带走的东西"], [
            ["<strong>00</strong>", "课程总览与环境（本模块）", "方法论", "三层框架、二分定位、容差表"],
            ["<strong>01</strong>", "预处理一致性", "<strong>第 ① 层（40%）</strong>", "从零实现的 resize 家族、letterbox 变体、<strong>预处理对拍工具</strong>"],
            ["<strong>02</strong>", "TensorRT 构建与优化", "第 ② 层", "层融合、动态 shape profile、<strong>静默回退的识别</strong>"],
            ["<strong>03</strong>", "INT8 校准与精度恢复", "第 ② 层", "KL 熵校准的完整实现、敏感层分析、<strong>掉点排查决策树</strong>"],
            ["<strong>04</strong>", "后处理对齐与 C++ 推理管线", "<strong>第 ③ 层（25%）</strong>", "NMS 变体差异、<strong>letterbox 逆变换</strong>、端到端对拍框架"],
            ["<strong>05</strong>", "性能剖析与延迟工程", "工程", "p99 延迟、roofline、降频漂移、<strong>发布验收清单</strong>"],
        ]),
        H3("与其他课的关系"),
        UL([
            "<strong>C52（模型部署与推理）模块 03</strong> 讲的是「怎么导出 ONNX、有哪些运行时」——那是<em>把模型搬过去</em>；本课讲的是<strong>搬过去之后怎么证明它还是同一个模型</strong>。两者互补，不重叠。",
            "<strong>C27（量化）</strong> 讲量化的原理（scale/zero-point、对称性、PTQ/QAT）；本课模块 03 只讲<strong>检测任务里的校准工程</strong>——校准集怎么构造、敏感层怎么找、掉点怎么排查。",
            "<strong>C53 模块 05</strong> 讲延迟-精度选型（选哪个模型）；本课模块 05 讲<strong>怎么正确地测</strong>（warmup、同步、p99、降频）——选型的前提是测量可信。",
            "<strong>C55（TSR）与 C57（小目标）</strong> 给出本课所有例子的场景：<em>为什么预处理错误对 TSR 特别致命</em>——因为目标只有 10–30 像素，任何采样层面的信息损失都直接打在它身上（模块 01 会量化）。",
            "<strong>C61 模块 03</strong> 是本课的姊妹篇：那里讲训练侧的调试手册（loss 为 NaN、mAP 恒为 0），这里讲部署侧。<em>两边合起来是一份完整的检测工程诊断树。</em>",
        ]),
        H3("环境"),
        P("本课全部 notebook <strong>纯 numpy + 标准库，CPU 即可</strong>，不需要 GPU、不需要 TensorRT、不需要联网。这是刻意的设计："),
        DUAL(
            "你可能会问：讲 TensorRT 的课，为什么 notebook 里没有 TensorRT？因为<strong>本课要教的不是 API，是机制</strong>。<code>trtexec</code> 的参数你随时可以查文档，但「为什么这个 resize 会让小目标消失」「KL 校准到底在最小化什么」，只有自己从零写一遍才会真的懂。<em>而且 API 会过时，机制不会。</em>",
            "更实际的理由是<span class=\"term\">reproducibility</span>（可复现性）：TensorRT 的行为与 GPU 型号、驱动版本、TRT 版本三者绑定（模块 02 会讲这件事本身就是一个部署难题），任何依赖具体硬件的教学代码，半年后就跑不起来了。<strong>纯 numpy 的实现是这门课能长期存在的前提</strong>；而真实的命令、配置与检查单，全部以「🧪 真实工程胶囊」的形式放在每个 notebook 末尾——可以原样复制到你的项目里。",
        ),
        CALLOUT("intuition", "本模块的 notebook 会让你实现三件事：<strong>①一致性度量与容差表</strong>（把上一节的表算出来）；<strong>②二分定位器</strong>（在一条 12 阶段的管线上用 3 次探针找到 bug）；<strong>③排查顺序的最优性证明</strong>（为什么按「概率/成本」降序排是最优的）。第三件事在面试里很有用——它把「凭经验」变成了「有依据」。"),
    ])),

    # ============================================================== 7
    ("frontier", "研究前沿与开放问题", "".join([
        P("训练-部署一致性长期被当作「工程琐事」，但它其实有几个真正开放的问题，而且都在变得更重要："),
        UL([
            "<strong>预处理缺乏规范，而且没人打算制定。</strong>resize 这个最基础的算子，在 OpenCV / PIL / TensorFlow / PyTorch / ONNX Runtime / TensorRT 之间存在<em>至少 6 种互不等价的语义</em>（坐标映射 2–3 种 × 是否抗锯齿 × 定点/浮点）。ONNX 的 <code>Resize</code> 算子把这些差异编码成属性（<code>coordinate_transformation_mode</code> 等），<strong>这是目前唯一严肃的规范化尝试</strong>，但转换器是否正确保留这些属性、后端是否正确实现，仍然要逐个验证。<em>Parmar et al. 的《On Aliased Resizing》指出这个问题连 GAN 评测指标（FID）都被污染了——学术界的数字也不干净。</em>",
            "<strong>「一致性」还没有公认的度量。</strong>本课用的逐阶段 $L_\\infty$/分位数判据是工程实践，不是理论。<em>什么样的度量能同时满足：对不可避免的数值噪声不敏感、对语义错误敏感、且可以在层间给出误差传播的紧界？</em>目前没有好答案——Lipschitz 常数的上界通常松到无用（几个数量级），而经验度量缺乏保证。",
            "<strong>误差传播的可证明界。</strong>神经网络的 Lipschitz 常数估计（谱范数上界、CLEVER、LipSDP 等）本是为对抗鲁棒性发展的，但正好可以回答一个部署问题：<em>输入张量差 $\\epsilon$，输出框最多偏多少？</em>如果这个界足够紧，容差就可以从「经验值」变成「推导值」。<strong>目前对深层检测器还做不到，这是一个有明确工程价值的开放方向。</strong>",
            "<strong>把对拍做进编译器 / 转换器。</strong>理想形态是：转换工具在把 PyTorch 图转成 engine 的同时，<em>自动生成逐层的数值对拍测试</em>，并在 CI 中回归。<code>polygraphy</code> 的 <code>--validate</code> / 逐层比对已经走在这条路上，但它只覆盖模型层，不覆盖预处理与后处理——<strong>而那正是 65% 的问题所在</strong>。",
            "<strong>端到端可微分预处理。</strong>如果预处理本身是网络的一部分（放进图里、一起导出、一起量化），语义分歧从定义上就消失了。<em>代价是灵活性与效率（ISP 与 resize 常常有硬件加速路径，放进网络就用不上了），以及量化时预处理层会成为新的敏感层。</em>这个取舍在车端还没有定论。",
            "<strong>ISP 与感知的联合优化。</strong>训练用 JPEG 解码图、部署用 ISP 直出，这个域差目前靠数据增强模拟。<em>更彻底的思路是把 ISP 参数也纳入优化（「为机器视觉而不是为人眼调 ISP」）</em>——已有若干工作显示可以提升下游检测精度，但它需要感知团队与相机团队的组织级协作，量产落地的很少。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Parmar, Zhang, Zhu, <em>On Aliased Resizing and Surprising Subtleties in GAN Evaluation</em>（CVPR 2022，arXiv:2104.11222）——用最少的篇幅把「不同库的 resize 不等价、且差异大到污染指标」这件事钉死，本课模块 01 的实验设计直接受它启发。<strong>★</strong> ONNX <em>Operators.md · Resize</em> 与 <em>Resize 的 coordinate_transformation_mode 语义表</em>——这是目前唯一把各家 resize 语义写成规范的文档，<strong>建议逐条读完</strong>，它会解释你遇到的绝大多数插值差异。<strong>★</strong> NVIDIA, <em>TensorRT Developer Guide</em> 的「Working with Dynamic Shapes」与「Optimizing for Accuracy」两章，以及 <code>polygraphy</code> 的逐层比对用法（模块 02/04 会大量用到它的思路）。</p><p>配套背景：Krishnamoorthi, <em>Quantizing deep convolutional networks for efficient inference: A whitepaper</em>（arXiv:1806.08342，量化的系统性综述，C27 与本课模块 03 的基础）；Migacz, <em>8-bit Inference with TensorRT</em>（GTC 2017，KL 熵校准的原始出处）；Buckler et al., <em>Reconfiguring the Imaging Pipeline for Computer Vision</em>（ICCV 2017，ISP-感知联合设计的早期工作）。相邻课程：C52（导出与运行时）、C27（量化原理）、C55（TSR 场景）、C57（小目标）、C61 模块 03（训练侧调试手册）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（三层框架 / 二分定位 / 容差表 / 排查顺序）

目标：把本课的**方法论**变成可运行的代码，而不是几张 PPT 上的框图。

本 notebook 你会亲手实现：
1. **一致性度量与容差表**——把「fp16 噪声 / 定点舍入 / 语义错误」三档量级实际算出来，
   证明它们之间隔着一个数量级，因此阈值是可推导的而不是拍脑袋的
2. **三层鸿沟的「指纹」分类器**——给定一个 diff 张量，自动判断错误属于哪一类
3. **逐层二分定位器**——在一条 12 阶段的管线上用 3 次探针找到首个分歧算子，
   并验证探针次数 = ⌈log₂(n+1)⌉
4. **排查顺序的最优性**——证明按「概率 ÷ 成本」降序排查使期望总成本最小
5. **误差放大模型**——输入端 1e-3 的差异如何在 8 层网络里变成分数扰动，
   再变成排序翻转，最后变成 mAP 掉点
6. **环境自检**

> 心智模型：**不要问「为什么模型效果差」，要问「第一个对不上的张量在哪」。**
> 前者没有终点，后者最多 ⌈log₂ n⌉ 步。"""),

    md("""## 1 · 一致性度量与容差表

先把三档差异的量级算出来。归一化用 mmdet 的经典配置
`mean=[123.675, 116.28, 103.53]`、`std=[58.395, 57.12, 57.375]`，
「tensor 单位」指归一化之后的张量（模型真正吃到的东西）。"""),

    code("""import numpy as np, math, sys, platform, time, json
rng = np.random.default_rng(60)
np.set_printoptions(precision=4, suppress=True)

MEAN = np.array([123.675, 116.28, 103.53])
STD  = np.array([58.395, 57.12, 57.375])

# 一张「自然图」：低频结构 + 细纹理（细纹理是后面混叠实验的关键）
yy, xx = np.mgrid[0:240, 0:240]
img = np.clip(np.stack([110 + 40*np.sin(xx/47.), 118 + 35*np.cos(yy/39.),
                        125 + 30*np.sin((xx+yy)/61.)], -1)
              + 18*np.sin(2*np.pi*xx/5.)[..., None], 0, 255)
ten = (img - MEAN) / STD                      # 模型真正吃到的张量

def report(a, b, name):
    d = np.abs(a - b)
    return dict(name=name, max=float(d.max()), mean=float(d.mean()),
                p99=float(np.percentile(d, 99)))

# ① fp16 的表示误差（不可避免）
fp16 = report(ten.astype(np.float32), ten.astype(np.float16).astype(np.float32), 'fp16 表示误差')
# ② 定点 resize 的舍入：uint8 输出四舍五入，误差在 ±0.5 灰阶内均匀分布
err_fix = rng.uniform(-0.5, 0.5, ten.shape) / STD.mean()
fixed = report(ten, ten + err_fix, '定点舍入 ±0.5 灰阶')
# ③ 语义错误：INTER_LINEAR vs INTER_AREA 的典型差（模块 01 会实测出 21.4 灰阶）
sem = report(ten, ten + 21.4/STD.mean(), 'resize 语义错误')

print(f"{'差异来源':<22s}{'max':>12s}{'mean':>12s}")
for r in (fp16, fixed, sem):
    print(f"{r['name']:<22s}{r['max']:>12.6f}{r['mean']:>12.6f}")

ratio_impl = fixed['max'] / fp16['max']
ratio_sem  = sem['mean']  / fixed['max']
print(f"\\n定点舍入(max) / fp16(max)     = {ratio_impl:6.1f} 倍")
print(f"语义错误(mean) / 定点舍入(max) = {ratio_sem:6.1f} 倍")
assert fp16['max'] < 2e-3,  fp16
assert 8e-3 < fixed['max'] < 9e-3 and fixed['mean'] < 5e-3, fixed
assert sem['mean'] > 0.3, sem
assert ratio_sem > 20, '语义错误必须比实现噪声大一个数量级以上，阈值才有空档可放'
print('\\n✅ 三档之间隔着一到两个数量级 —— 所以容差是可推导的，不是拍脑袋的。')"""),

    code("""# 把「阈值放在空档里」这件事写成一个判定器
TOL = dict(preproc_max=0.02, preproc_mean=0.005)   # tensor 单位

def verdict(a, b, tol=TOL):
    \"\"\"预处理阶段的一致性判定：返回 (PASS/FAIL, 细节)\"\"\"
    d = np.abs(np.asarray(a) - np.asarray(b))
    ok = (d.max() <= tol['preproc_max']) and (d.mean() <= tol['preproc_mean'])
    return ('PASS' if ok else 'FAIL'), dict(max=float(d.max()), mean=float(d.mean()))

cases = [
    ('fp16 抖动（不该报警）',      ten.astype(np.float16).astype(np.float32)),
    ('定点舍入 ±0.5 灰阶（不该报）', ten + err_fix),
    ('align_corners 差异（该报）', ten + 0.038),
    ('resize 语义错（该报）',      ten + 21.4/STD.mean()),
]
print(f"{'场景':<26s}{'判定':>6s}{'max':>10s}{'mean':>10s}")
got = []
for name, other in cases:
    v, det = verdict(ten, other)
    got.append(v)
    print(f'{name:<26s}{v:>6s}{det["max"]:>10.4f}{det["mean"]:>10.4f}')
assert got == ['PASS', 'PASS', 'FAIL', 'FAIL'], got
print('\\n✅ 同一组阈值同时做到：放过实现噪声、拦住语义错误。')
print('⚠️  最窄的一道缝：定点舍入的 max(=0.0086) 与 align_corners(=0.038) 只差 4.4 倍，')
print('   阈值 max<=0.02 正好卡在中间 —— 这就是「阈值要有来源」的含义。')"""),

    md("""## 2 · diff 的形状就是指纹

找到分歧阶段后不要急着读代码，**先看 diff 张量长什么样**。
每一类预处理错误在张量空间里都有特征性的支撑集与频谱：

| diff 的样子 | 原因 |
|---|---|
| 只在边缘一圈非零 | `align_corners` / padding |
| 高频条纹、棋盘格 | **resize 插值方式不同（混叠）** |
| 通道置换后归零 | **BGR/RGB 弄反** |
| 全图常数偏移 | mean 不同 |
| 全图按比例缩放 | std 不同 / 少除了 255 |
| 零散无结构、幅值 1e-3 | 正常数值噪声 |

下面把这个「用眼睛认」的过程写成代码。"""),

    code("""def fingerprint(a, b, edge=2, tol=2e-3):
    \"\"\"给定两侧张量，返回最可能的错误类型。a=参考(训练侧)，b=待查(部署侧)。\"\"\"
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    if np.abs(d).max() <= tol:
        return 'noise'                                   # 在噪声档内，不是 bug
    # 通道置换？把 b 的通道反序后再比
    if a.ndim == 3 and a.shape[-1] == 3 and np.abs(b[..., ::-1] - a).max() <= tol:
        return 'channel_swap'
    # 边缘带 vs 内部：能量是否集中在边界
    mask = np.zeros(a.shape[:2], bool)
    mask[:edge] = mask[-edge:] = True; mask[:, :edge] = mask[:, -edge:] = True
    de = np.abs(d[mask]).mean(); di = np.abs(d[~mask]).mean()
    if di < 1e-9 or de / max(di, 1e-12) > 20:
        return 'border'
    # 常数偏移？（逐通道去均值后残差极小）
    ax = tuple(range(d.ndim - 1)) if a.ndim == 3 else None
    if np.abs(d - d.mean(axis=ax, keepdims=True)).max() < 0.05 * np.abs(d).max() + 1e-9:
        return 'const_shift'
    # 比例缩放？（b/a 近似常数）
    r = b / np.where(np.abs(a) < 1e-6, np.nan, a)
    if np.nanstd(r) < 0.02 * abs(np.nanmean(r)):
        return 'scale'
    # 高频结构？（相邻差分的能量占比高）
    hf = np.abs(np.diff(d, axis=1)).mean() / (np.abs(d).mean() + 1e-12)
    return 'high_freq' if hf > 0.8 else 'unknown'

base = ten.copy()
tests = {
    'noise':        base + rng.normal(0, 3e-4, base.shape),
    'channel_swap': base[..., ::-1],
    'const_shift':  base + 0.31,
    'scale':        base * 1.17,
    'high_freq':    base + 0.4*np.sign(np.sin(2*np.pi*xx/2.))[..., None],
}
bd = base.copy(); bd[:2] += 0.4; bd[-2:] += 0.4; bd[:, :2] += 0.4; bd[:, -2:] += 0.4
tests['border'] = bd

for k, v in tests.items():
    got = fingerprint(base, v)
    print(f'{k:<14s} -> {got}')
    assert got == k, (k, got)
print('\\n✅ 6 种指纹全部识别正确 —— 这就是「看图认」的代码化。')"""),

    md("""## 3 · 逐层二分定位

关键性质：`D(k) = 1[前 k 阶段已分歧]` 关于 k **单调**——
分歧一旦产生就不会自己愈合。单调布尔序列上找第一个 1 = 二分查找，
代价 ⌈log₂(n+1)⌉ 次探针。"""),

    code("""def bisect_first_divergence(probe, n):
    \"\"\"probe(k) -> bool，表示「跑到第 k 阶段为止是否已分歧」（k 从 1 到 n）。
       返回 (首个分歧阶段或 None, 探针次数)。
       技巧：把「全程无分歧」编码成虚拟位置 n+1（D(n+1) 定义为 True），
       于是不需要先单独探一次 probe(n) —— 省下的这一次让上界正好等于 ⌈log2(n+1)⌉。\"\"\"
    lo, hi, calls = 0, n + 1, 0      # 不变式：D(lo)=False（lo=0 天然成立），D(hi)=True
    while hi - lo > 1:
        mid = (lo + hi) // 2
        calls += 1
        if probe(mid):
            hi = mid
        else:
            lo = mid
    return (None if hi == n + 1 else hi), calls

# 12 阶段管线，分歧首次出现在第 7 阶段（resize）
STAGES = ['read', 'decode', 'to_rgb', 'crop_roi', 'cast_f32', 'clip',
          'resize', 'letterbox', 'normalize', 'hwc2chw', 'batch', 'contiguous']
FIRST_BAD = 7
def probe_factory(first_bad, counter):
    def probe(k):
        counter[0] += 1
        return k >= first_bad
    return probe

cnt = [0]
k, calls = bisect_first_divergence(probe_factory(FIRST_BAD, cnt), len(STAGES))
print(f'首个分歧阶段 = 第 {k} 个 = {STAGES[k-1]!r}   探针次数 = {calls}')
assert k == FIRST_BAD and calls == cnt[0]
assert calls <= math.ceil(math.log2(len(STAGES) + 1)), (calls,)
print(f'理论上界 ⌈log2({len(STAGES)}+1)⌉ = {math.ceil(math.log2(len(STAGES)+1))}')

# 全部位置都验一遍：正确性 + 探针次数上界
worst = 0
for fb in range(1, len(STAGES) + 1):
    kk, cc = bisect_first_divergence(probe_factory(fb, [0]), len(STAGES))
    assert kk == fb, (fb, kk)
    worst = max(worst, cc)
    assert cc <= math.ceil(math.log2(len(STAGES) + 1)), (fb, cc)
kk, cc = bisect_first_divergence(lambda k: False, len(STAGES))
assert kk is None and cc == math.ceil(math.log2(len(STAGES) + 1)), (kk, cc)
print(f'12 个位置全部定位正确；最坏探针次数 = {worst}（顺序扫描最坏要 {len(STAGES)} 次）')
print('✅ 12 阶段 → 4 次；1000 阶段 → 10 次。这就是「30 分钟」的复杂度依据。')"""),

    code("""# 真实一点：两条管线各自跑，probe 用「张量 diff 是否超容差」实现
def pipeline(x, resize_kernel='area'):
    \"\"\"极简 6 阶段管线；resize 用 1D 盒滤波 / 抽样两种实现来制造分歧。\"\"\"
    out = {}
    out['cast'] = x.astype(np.float64)
    out['clip'] = np.clip(out['cast'], 0, 255)
    s = 2
    if resize_kernel == 'area':                       # 2x2 盒平均
        out['resize'] = out['clip'].reshape(x.shape[0]//s, s, x.shape[1]//s, s, 3).mean((1, 3))
    else:                                             # 抽样（= 无抗锯齿）
        out['resize'] = out['clip'][::s, ::s]
    out['normalize'] = (out['resize'] - MEAN) / STD
    out['chw'] = np.moveaxis(out['normalize'], -1, 0)
    out['batch'] = out['chw'][None]
    return out

ORDER = ['cast', 'clip', 'resize', 'normalize', 'chw', 'batch']
tr = pipeline(img, 'area')          # 训练侧
dp = pipeline(img, 'sample')        # 部署侧（resize 实现不同）

def probe_tensors(k, tol=0.02):
    name = ORDER[k-1]
    a, b = np.asarray(tr[name], float), np.asarray(dp[name], float)
    if a.shape != b.shape:
        return True                  # 形状都不同，必然分歧
    return bool(np.abs(a - b).max() > tol * (STD.mean() if name in ('cast','clip','resize') else 1))

k, calls = bisect_first_divergence(probe_tensors, len(ORDER))
print(f'首个分歧阶段 = 第 {k} 个 = {ORDER[k-1]!r}，探针 {calls} 次')
assert ORDER[k-1] == 'resize'
fp = fingerprint(tr['normalize'], dp['normalize'])
print(f'该阶段 diff 的指纹 = {fp!r}')
print(f'diff: max={np.abs(tr["normalize"]-dp["normalize"]).max():.4f}  '
      f'mean={np.abs(tr["normalize"]-dp["normalize"]).mean():.4f}')
assert fp in ('high_freq', 'unknown')
print('\\n✅ 二分 + 指纹 = 「第 3 个算子 resize，高频结构 → 插值方式不同」。')
print('   从看到现象到给出结论，全程不需要读一行两侧的源码。')"""),

    md("""## 4 · 排查顺序：为什么「概率 ÷ 成本」降序是最优的

第 1 节给了根因的概率分布。但排查顺序不该只看概率——**还要看成本**。
把每个候选原因 i 的「命中概率 pᵢ」和「检查成本 cᵢ」放在一起，
期望总成本在按 **pᵢ/cᵢ 降序** 排查时最小（这是经典的调度不等式 / Smith rule）。"""),

    code("""CAUSES = [
    # (名字, 命中概率 p, 检查成本 c 小时)
    ('预处理不一致',      0.40, 0.5),
    ('后处理/坐标变换',   0.25, 0.5),
    ('数值精度/量化',     0.15, 4.0),
    ('评测口径不一致',    0.10, 2.0),
    ('真实域差(要闭环)',  0.10, 40.0),
]

def expected_cost(order):
    \"\"\"按 order 顺序逐个检查，期望总成本 = Σ_j c_j * P(前 j-1 个都没命中)\"\"\"
    tot, remain = 0.0, 1.0
    for name, p, c in order:
        tot += remain * c            # 无论命中与否，这一项的检查成本都要付
        remain -= p                  # 命中就停
    return tot

by_ratio = sorted(CAUSES, key=lambda z: -z[1]/z[2])
by_prob  = sorted(CAUSES, key=lambda z: -z[1])
by_cost  = sorted(CAUSES, key=lambda z:  z[2])
worst    = sorted(CAUSES, key=lambda z:  z[1]/z[2])

print(f"{'策略':<22s}{'期望总成本(小时)':>18s}")
for nm, o in [('p/c 降序（最优）', by_ratio), ('只按概率降序', by_prob),
              ('只按成本升序', by_cost), ('p/c 升序（最差）', worst)]:
    print(f'{nm:<22s}{expected_cost(o):>18.3f}')

# 穷举验证 p/c 降序确实是最优
import itertools
best = min(itertools.permutations(CAUSES), key=expected_cost)
assert abs(expected_cost(best) - expected_cost(by_ratio)) < 1e-12
assert expected_cost(by_ratio) <= expected_cost(by_prob) + 1e-12
print('\\n穷举 120 种顺序，最优顺序 =')
for i, (n, p, c) in enumerate(by_ratio, 1):
    print(f'  {i}. {n:<18s} p={p:.2f} c={c:>4.1f}h  p/c={p/c:>5.2f}')
print(f'\\n✅ 最优 {expected_cost(by_ratio):.2f}h vs 最差 {expected_cost(worst):.2f}h，'
      f'差 {expected_cost(worst)/expected_cost(by_ratio):.1f} 倍。')
# 「只按成本升序」在这组数上恰好也最优 —— 因为这里概率与成本刚好负相关。这是巧合，不能依赖：
toy = [('A 贵但极可能', 0.90, 2.0), ('B 便宜但几乎不可能', 0.02, 0.1)]
assert expected_cost(sorted(toy, key=lambda z: -z[1]/z[2])) < expected_cost(sorted(toy, key=lambda z: z[2]))
print(f'   反例：{[t[0] for t in toy]} —— 按成本升序 {expected_cost(sorted(toy,key=lambda z:z[2])):.3f}h'
      f' > 按 p/c 降序 {expected_cost(sorted(toy,key=lambda z:-z[1]/z[2])):.3f}h。'
      '「先做便宜的」一般不是最优，只有在 p/c 也高时才是。')
print('⚠️  注意「真实域差」概率不低（10%）但成本极高（40h），永远排最后 ——')
print('   「先怀疑模型」之所以是错的，不是因为它不可能，而是因为它最贵。')"""),

    md("""## 5 · 误差放大：1e-3 的输入差怎么变成 mAP 掉点

一致性问题让人低估的原因是：**输入端的差异看起来很小**。
但网络是有增益的——逐层的 Lipschitz 常数相乘，输入 δ 变成输出 L·δ；
分数扰动会改变**排序**，而 AP 只依赖排序。"""),

    code("""def amplify(delta_in, layer_gains):
    \"\"\"逐层放大：返回每层之后的差异上界\"\"\"
    out, d = [], delta_in
    for g in layer_gains:
        d *= g
        out.append(d)
    return np.array(out)

GAINS = np.array([1.4, 1.3, 1.6, 1.2, 1.5, 1.3, 1.1, 1.2])   # 8 层的经验增益
L = float(np.prod(GAINS))
print(f"{'差异来源':<16s}{'输入 δ':>10s}{'输出 δ':>12s}{'超过 fp16 档的倍数':>20s}")
base_out = None
for name, d0 in [('fp16 噪声', 5e-4), ('align_corners', 3.8e-2), ('resize 语义错', 0.37)]:
    out = amplify(d0, GAINS)[-1]
    base_out = out if base_out is None else base_out
    print(f'{name:<16s}{d0:>10.4g}{out:>12.4g}{out/base_out:>20.1f}')
assert 8.9 < L < 9.1, L
print(f'\\n整网增益 L = Π gᵢ = {L:.2f}（8 层，每层 1.1~1.6）')
print('⚠️  这是**上界**不是实际值 —— 但它说明方向：输入端的差异到输出端不会变小。')
print('   而下一段会看到：输出端 δ 落在 0.05 量级就足以改变 AP。')"""),

    code("""# 分数扰动 -> 排序翻转 -> AP 掉点
def ap_from_scores(scores, labels):
    \"\"\"标准 VOC all-point AP。labels: 1=TP, 0=FP\"\"\"
    o = np.argsort(-scores, kind='stable')
    l = np.asarray(labels)[o]
    tp, fp = np.cumsum(l), np.cumsum(1 - l)
    npos = max(int(l.sum()), 1)
    rec, pre = tp / npos, tp / np.maximum(tp + fp, 1e-9)
    mr = np.concatenate([[0], rec, [1]]); mp = np.concatenate([[0], pre, [0]])
    for i in range(len(mp) - 2, -1, -1):
        mp[i] = max(mp[i], mp[i + 1])
    k = np.where(mr[1:] != mr[:-1])[0]
    return float(((mr[k+1] - mr[k]) * mp[k+1]).sum())

r2 = np.random.default_rng(7)
N = 400
labels = (r2.random(N) < 0.35).astype(int)
scores = np.clip(r2.beta(2.5, 2.0, N) + 0.25*labels, 0, 1)   # TP 分数系统性更高
ap0 = ap_from_scores(scores, labels)

print(f"{'输出端扰动 σ':>14s}{'AP':>9s}{'ΔAP':>9s}{'top-50 排序翻转率':>20s}")
prev = 1.0
for sigma in [0.0, 0.005, 0.02, 0.05, 0.12, 0.30]:
    s = scores + r2.normal(0, sigma, N)
    ap = ap_from_scores(s, labels)
    top0, top1 = set(np.argsort(-scores)[:50]), set(np.argsort(-s)[:50])
    flip = 1 - len(top0 & top1) / 50
    print(f'{sigma:>14.3f}{ap:>9.3f}{ap-ap0:>9.3f}{flip:>19.1%}')
    assert ap <= prev + 1e-9, 'AP 应随扰动单调下降（同一随机流下）'
    prev = ap
print('\\n✅ 关键：AP 只依赖**排序**。分数抖动 0.05 就能换掉 top-50 里的一批，')
print('   而 0.05 在张量空间里是一个「看起来很小」的数。')
print('⚠️  这解释了为什么「张量 diff 只有 0.04，应该没影响吧」是错的直觉。')"""),

    md("""## 6 · 环境自检"""),

    code("""t0 = time.time()
print('Python  :', sys.version.split()[0])
print('平台    :', platform.platform())
print('numpy   :', np.__version__)
ok = True
try:
    a = np.arange(12.).reshape(3, 4)
    assert np.allclose(a @ a.T, np.einsum('ij,kj->ik', a, a))
    assert np.percentile(np.arange(101.), 99) == 99.0
    _ = np.random.default_rng(0).beta(2, 2, 5)          # Generator API
except Exception as e:                                  # pragma: no cover
    ok = False; print('❌', e)
print('numpy 自检 :', 'OK' if ok else 'FAIL')
print('本课全部 notebook 纯 numpy + 标准库，CPU 即可，无需 GPU / TensorRT / 联网。')
print(f'耗时 {time.time()-t0:.3f}s')
assert ok"""),

    md("""## ✏️ 练习 1：带上下界的二分定位器

实现 `bisect_range(probe, lo, hi)`：已知 `D(lo)=False`、`D(hi)=True`，
在开区间 `(lo, hi]` 里找首个分歧位置，返回 `(位置, 探针次数)`。
**要求**：探针次数 ≤ `ceil(log2(hi-lo))`，且不重复调用同一个 k。"""),

    code("""def bisect_range(probe, lo, hi):
    # TODO: 二分不变式 —— D(lo)=False, D(hi)=True，缩到 hi-lo==1 为止
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
for n in [1, 2, 3, 7, 12, 33, 1000]:
    for fb in ({1, n} | set(np.random.default_rng(n).integers(1, n+1, min(n, 8)).tolist())):
        seen = []
        k, c = bisect_range(lambda x: (seen.append(x), x >= fb)[1], 0, n)
        assert k == fb, (n, fb, k)
        assert len(seen) == len(set(seen)), '不能重复探同一个 k'
        assert c <= math.ceil(math.log2(n)) or n == 1, (n, fb, c)
k, c = bisect_range(lambda x: x >= 7, 4, 12)     # 已知前 4 阶段没问题
assert k == 7 and c <= 3, (k, c)
print(f'1000 阶段管线最坏探针次数 ≤ {math.ceil(math.log2(1000))}')
print('✅ 练习 1 通过：知道下界能省探针 —— 现实中「前几步肯定没问题」是常见的先验。')"""),

    md("""## ✏️ 练习 2：最优排查顺序

实现 `optimal_order(causes)`：输入 `[(名字, p, c), ...]`，
返回按**期望总成本最小**排列的列表。（提示：Smith rule，按 p/c 降序。）
再实现 `expected_cost_of(causes)` 返回该顺序下的期望成本。"""),

    code("""def optimal_order(causes):
    # TODO
    raise NotImplementedError

def expected_cost_of(causes):
    # TODO: 用 optimal_order 排完之后算期望成本
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
o = optimal_order(CAUSES)
assert [x[0] for x in o] == [x[0] for x in by_ratio], o
assert abs(expected_cost_of(CAUSES) - expected_cost(by_ratio)) < 1e-12
# 手算小例子：A(p=.5,c=1) 与 B(p=.4,c=.2) -> B 的 p/c=2.0 > A 的 0.5，B 先
toy = [('A', 0.5, 1.0), ('B', 0.4, 0.2)]
assert [x[0] for x in optimal_order(toy)] == ['B', 'A']
# B先: 0.2*1 + 1.0*(1-0.4) = 0.8 ; A先: 1.0*1 + 0.2*(1-0.5) = 1.1
assert abs(expected_cost_of(toy) - 0.8) < 1e-12, expected_cost_of(toy)
assert abs(expected_cost(toy) - 1.1) < 1e-12
# 穷举校验
import itertools as it
assert abs(expected_cost_of(CAUSES) - min(map(expected_cost, it.permutations(CAUSES)))) < 1e-12
print('最优顺序:', [x[0] for x in o])
print(f'期望成本 {expected_cost_of(CAUSES):.3f}h')
print('✅ 练习 2 通过：「先查预处理」不是经验之谈，是 p/c 排序的结论。')"""),

    md("""## ✏️ 练习 3：分阶段容差判定器

实现 `stage_verdict(a, b, kind)`，`kind ∈ {'preproc', 'model_fp16', 'model_int8', 'boxes'}`：

- `'preproc'`：`max ≤ 0.02` 且 `mean ≤ 0.005`
- `'model_fp16'`：相对误差 `|a-b|/(|b|+1e-3)` 的 **99 分位** `≤ 0.02`
- `'model_int8'`：同上但阈值 `0.10`
- `'boxes'`：a、b 是 `(N,4)` 框数组——**个数必须相等**，且逐框 IoU 全 `> 0.99`

返回 `'PASS'` 或 `'FAIL'`。"""),

    code("""def stage_verdict(a, b, kind):
    # TODO: 不同阶段用不同的语义空间去比 —— 这是本练习唯一的考点
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
x = ten
assert stage_verdict(x, x.astype(np.float16).astype(np.float32), 'preproc') == 'PASS'
assert stage_verdict(x, x + 0.038, 'preproc') == 'FAIL'
y = rng.normal(0, 1, (2, 64, 40, 40))
assert stage_verdict(y, y * 1.005, 'model_fp16') == 'PASS'
assert stage_verdict(y, y * 1.05,  'model_fp16') == 'FAIL'
assert stage_verdict(y, y * 1.05,  'model_int8') == 'PASS'
B1 = np.array([[10., 10., 50., 50.], [100., 100., 140., 160.]])
assert stage_verdict(B1, B1 + 0.01, 'boxes') == 'PASS'
assert stage_verdict(B1, B1 + 1.0,  'boxes') == 'FAIL'     # 1px 偏移 -> IoU 约 0.95
assert stage_verdict(B1, B1[:1],    'boxes') == 'FAIL'     # **个数不等，直接 FAIL**
print('✅ 练习 3 通过：比什么，比怎么比更重要。')
print('   框的个数不等几乎总是 NMS 语义不同，而不是数值问题 —— 不要用容差去「容忍」它。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def bisect_range(probe, lo, hi):
    calls = 0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        calls += 1
        if probe(mid):
            hi = mid
        else:
            lo = mid
    return hi, calls"""),

    code("""# 练习 2 参考答案
def optimal_order(causes):
    return sorted(causes, key=lambda z: -z[1] / z[2])

def expected_cost_of(causes):
    tot, remain = 0.0, 1.0
    for _, p, c in optimal_order(causes):
        tot += remain * c
        remain -= p
    return tot"""),

    code("""# 练习 3 参考答案
def _iou_rows(a, b):
    x1 = np.maximum(a[:, 0], b[:, 0]); y1 = np.maximum(a[:, 1], b[:, 1])
    x2 = np.minimum(a[:, 2], b[:, 2]); y2 = np.minimum(a[:, 3], b[:, 3])
    it = np.clip(x2-x1, 0, None) * np.clip(y2-y1, 0, None)
    aa = (a[:, 2]-a[:, 0])*(a[:, 3]-a[:, 1]); bb = (b[:, 2]-b[:, 0])*(b[:, 3]-b[:, 1])
    return it / np.maximum(aa + bb - it, 1e-9)

def stage_verdict(a, b, kind):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if kind == 'boxes':
        if a.shape != b.shape:
            return 'FAIL'
        return 'PASS' if (len(a) == 0 or _iou_rows(a, b).min() > 0.99) else 'FAIL'
    if a.shape != b.shape:
        return 'FAIL'
    if kind == 'preproc':
        d = np.abs(a - b)
        return 'PASS' if (d.max() <= 0.02 and d.mean() <= 0.005) else 'FAIL'
    thr = {'model_fp16': 0.02, 'model_int8': 0.10}[kind]
    rel = np.abs(a - b) / (np.abs(b) + 1e-3)
    return 'PASS' if np.percentile(rel, 99) <= thr else 'FAIL'"""),

    md("""---
## 🧪 真实工程胶囊：一页纸的「上车掉点」排查单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 「离线好、上车差」排查单 —— 按 p/c 顺序，不要跳步
# ══════════════════════════════════════════════════════════════════════

# ── 第 0 步（10 分钟，必做）：先确认这两个数可比 ──────────────────────
#  · 车上的「0.6」是怎么得到的？同一套 GT？同一个 IoU 阈值？同一个类别表？
#  · 离线评测有没有用到车上没有的东西（GT crop / 时序平滑 / 更大分辨率）？
#  · 如果口径不同 —— **先对齐口径，这一步经常直接结案**。

# ── 第 1 步（30 分钟）：预处理对拍  p=0.40  c=0.5h  ★ 最先查 ★ ────────
#  1) 选黄金样本：不要用「正常」图。要 (a) 含 <16px 小目标 (b) 含过曝区
#     (c) 奇数尺寸 (d) 纯色大面积 (e) 极暗帧。10~30 张固定入库。
#  2) 两侧 dump：
#       np.save(f'dump/{side}_{i:02d}_{stage}.npy', tensor)
#     阶段名两边必须一致：read/to_rgb/resize/letterbox/normalize/chw/batch
#  3) 二分 + 指纹：见本 notebook 第 3、2 节
#  4) 容差（tensor 单位）：max<=0.02, mean<=0.005
#  常见结论：INTER_LINEAR vs INTER_AREA / align_corners / BGR / letterbox 变体
#  → 展开见 **模块 01**

# ── 第 2 步（30 分钟）：后处理与坐标对拍  p=0.25  c=0.5h ───────────────
#  · sigmoid/softmax 是否做了两遍或一遍都没做（看分数分布：全在 0.5 附近 = 做了两遍）
#  · 框整体偏移固定像素 = letterbox 逆变换忘了减 pad
#  · 框个数不等 = NMS 语义不同（class-wise vs agnostic / top-k 截断 / IoU 的 +1）
#  · 判据：框个数相等 & 逐框 IoU>0.99 & 类别一致
#  → 展开见 **模块 04**

# ── 第 3 步（0.5 天）：评测口径  p=0.10  c=2h ─────────────────────────
#  · 用**完全相同的图片列表**在两侧各跑一遍，比对最终框；差异应为 0
#  · 若两侧框一致但指标不同 —— 问题在评测代码，不在模型

# ── 第 4 步（0.5~1 天）：数值精度  p=0.15  c=4h ──────────────────────
#  · fp32 engine 先跑通并与 PyTorch 对齐（p99 相对误差 < 2%），**再**开 fp16
#  · fp16 掉点 -> 查溢出（激活值 > 65504）；int8 掉点 -> 查校准集分布
#  · 逐层敏感度分析 -> 混合精度
#  → 展开见 **模块 02 / 03**

# ── 第 5 步（数周）：真实域差  p=0.10  c=40h ─────────────────────────
#  · 只有前四步全绿才走到这里。此时才允许说「模型不够好」。
#  · 触发 -> 挖掘 -> 标注 -> 训练 -> 切片评测 -> 门禁（见 C58）

# ── 固化：把第 1、2 步做成 CI ────────────────────────────────────────
#   pytest tests/test_preproc_parity.py     # 黄金样本 x 逐阶段 x 容差
#   pytest tests/test_postproc_parity.py    # 逆变换 / NMS 语义 / 框个数
#   每次改预处理、换 OpenCV 版本、改 C++ 管线，都必须跑。
#   **一致性不是靠小心，是靠门禁。**
'''
print(RECIPE)
for token in ['黄金样本', 'INTER_AREA', 'align_corners', 'letterbox 逆变换',
              '框个数', '65504', 'CI', 'p=0.40']:
    assert token in RECIPE, token
print('✅ 排查单覆盖：口径对齐 / 预处理 / 后处理 / 评测 / 精度 / 域差 / CI 固化')"""),

    md("""### 小结

- **「离线好、上车差」里约 65% 是确定性的软件缺陷**（预处理 40% + 后处理 25%），
  几行代码就能修；真正「模型不够好」只占 10%，但它最贵（40h vs 0.5h）。
  **按 p/c 降序排查，期望成本比最差顺序低数倍**——这是可证明的，不是经验之谈。
- **一致性是可验证的工程属性**：需要①可比较的中间产物 ②有来源的容差
  ③自动化判定 ④黄金样本集。缺任何一个，它都会随时间退化。
- **二分定位的复杂度是 ⌈log₂(n+1)⌉**：12 阶段 4 次探针，1000 阶段 10 次。
  依据是 `D(k)` 单调——分歧一旦产生不会自己愈合。
- **diff 的形状就是指纹**：边缘带→padding/align_corners；高频条纹→插值方式；
  通道置换→BGR/RGB；常数偏移→mean；比例缩放→std；无结构 1e-3→正常噪声。
- **容差要有来源**：fp16≈1e-3、定点舍入≈8.6e-3、align_corners≈3.8e-2、
  resize 语义错≈0.37。**三档之间隔着一到两个数量级，阈值放在空档里（0.02）。**
- **别拿 mAP 当一致性检查**：它灵敏度不够（中等错误可能只掉 2–3 点，
  淹没在种子方差里），而且归因不了。**张量对拍是门禁，端到端指标是验收。**
- **AP 只依赖排序**：输出分数抖动 0.05 就能换掉 top-50 里的一批框——
  所以「张量只差 0.04，应该没影响」是错的直觉。

下一站：**模块 01 · 预处理一致性** —— 40% 的问题都在那里，而 resize 是头号杀手。"""),
]
