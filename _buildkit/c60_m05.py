# -*- coding: utf-8 -*-
"""C60 模块 05 · 性能剖析与延迟工程。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 02（TensorRT 构建 / 层融合 / 算子回退）、模块 03（INT8）、模块 04（后处理放 GPU 还是 CPU）；C53 模块 05 的延迟-精度权衡"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_profiling_latency.ipynb（纯 numpy：延迟分布 / roofline / 热降频模拟 / 验收门禁）'),
    ("核心参考", "Williams et al., Roofline (CACM 2009) · Dean & Barroso, The Tail at Scale (CACM 2013) · trtexec 与 Nsight Systems 文档 · NVIDIA Orin 平台功耗与热管理指南"),
    ("预计时长", "读 80 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("measure", "测延迟的七宗罪", "".join([
        P("一个数字比它背后的测量方法可信度更低。<strong>面试里报出「我们的模型 8 ms」而说不清测量口径，是减分的；能主动说出「batch=1、含预处理与拷贝、含后处理、FP16、Orin AGX MAXN 模式、warmup 500 次、报 p50 和 p99」，是加分的。</strong>这一节把七种最常见的测错方式列全。"),
        TABLE(["#", "错误", "会得到什么数", "为什么", "怎么做对"], [
            ["<strong>1</strong>", "没有 warmup", "第一帧比稳态慢 <strong>10–100 倍</strong>", "CUDA context 创建、kernel 模块懒加载、cuDNN/cuBLAS handle 初始化、首次显存分配、TRT 的 lazy init 全在第一次调用里发生", "丢弃前 200–500 次；<code>trtexec --warmUp=500</code>"],
            ["<strong>2</strong>", "<strong>没有同步就计时</strong>", "「0.05 ms / 20000 FPS」这种荒谬值", "<code>enqueueV3</code> 是异步的，<em>提交完立刻返回</em>——你测的是 CPU 把 kernel 塞进队列的时间", "计时区间末尾加 <code>cudaStreamSynchronize</code>；或用 CUDA event 夹住"],
            ["3", "用 <code>time.time()</code>", "分辨率不够，短耗时全测成 0 或跳变", "部分平台上 <code>time.time()</code> 的分辨率是毫秒甚至 16 ms 量级", "<code>time.perf_counter()</code> / <code>std::chrono::steady_clock</code>"],
            ["<strong>4</strong>", "只报均值", "看不见尾巴", "延迟是<em>分布</em>，均值对长尾极不敏感", "报 p50 / p99 / p99.9 / max 四个数"],
            ["<strong>5</strong>", "同一张图跑 1000 次", "方差被人为压成 0", "cache 全热、NMS 输入固定 → <strong>所有数据依赖项都被冻结了</strong>", "用真实帧序列跑，且必须包含密集场景帧"],
            ["6", "只测 GPU 推理", "少算一半", "论文与 <code>trtexec</code> 默认口径常常不含预处理、拷贝、后处理", "报「端到端」与「纯推理」两个数并注明"],
            ["<strong>7</strong>", "开着 profiler 测总延迟", "总延迟被抬高，且逐层耗时之和 ≠ 端到端", "per-layer profiling 要在每层后插同步点，<strong>破坏了层间重叠与融合</strong>（观察者效应）", "<code>--separateProfileRun</code>：性能跑一次、profile 跑另一次"],
        ]),
        H3("CUDA event 与墙钟：两个都要报"),
        DUAL(
            "<strong>CUDA event 计时</strong>测的是「GPU 上这段工作花了多久」，不含 CPU 提交开销、不含排队等待。<strong>墙钟计时</strong>（<code>perf_counter</code> 夹住「提交 + 同步」）测的是「用户从发出请求到拿到结果等了多久」。<em>前者是你优化 kernel 时该看的，后者是产品该看的。</em>两者的差就是「提交开销 + 排队 + 同步开销」，如果这个差很大（比如超过 GPU 时间的 20%），说明 CPU 侧成了瓶颈——常见原因是 kernel 太碎、启动开销占比过高。",
            "<code>trtexec</code> 就是这么设计输出的，四个数值必须分清：<em>①<strong>GPU Compute Time</strong></em>——engine 在 GPU 上纯执行的时间；<em>②<strong>Enqueue Time</strong></em>——CPU 把这一次推理提交进 stream 的时间，如果它接近甚至超过 GPU Compute Time，说明 CPU 提交跟不上 GPU 执行，<strong>需要 CUDA Graph 或减少层数</strong>；<em>③<strong>Host Latency</strong></em>——含 H2D/D2H 的端到端；<em>④<strong>Throughput</strong></em>——稳态吞吐，在多流/多 batch 下与延迟的倒数完全不是一回事。<strong>报「FPS」而不说是哪个口径，等于没报。</strong>",
        ),
        H3("要多少个样本才能可靠地估出 p99"),
        P("这是一个可以精确回答的统计问题。$n$ 个独立样本中，$p$ 分位数落在第 $\\lceil pn \\rceil$ 个次序统计量上，而「有多少个样本超过真实 $p$ 分位」服从二项分布 $\\mathrm{Bin}(n, 1-p)$，秩的标准差是："),
        MATH("\\sigma_{\\text{rank}} = \\sqrt{n\\,p\\,(1-p)} \\qquad\\Longrightarrow\\qquad \\text{95\\% 置信区间对应的分位区间约为}\\ \\ p \\pm \\frac{1.96\\sqrt{p(1-p)}}{\\sqrt{n}}"),
        TABLE(["样本数 $n$", "超过 p99 的样本个数", "$\\sigma_{\\text{rank}}$", "p99 估计的 95% 分位区间", "结论"], [
            ["100", "<strong>1 个</strong>", "0.99", "[97.0%, 101.0%]", "<strong>完全不可用</strong>——你的「p99」就是最大值"],
            ["1 000", "10 个", "3.15", "[98.4%, 99.6%]", "勉强可用，是<strong>下限</strong>"],
            ["10 000", "100 个", "9.95", "[98.8%, 99.2%]", "<strong>推荐</strong>（30 FPS 下约 5.5 分钟）"],
            ["100 000", "1 000 个", "31.5", "[99.0%, 99.0%]", "p99.9 也可估（约 55 分钟，正好覆盖热稳态）"],
        ]),
        CALLOUT("danger", "<p><strong>「我跑了 100 次，p99 是 9.1 ms」——这句话在统计上是空的。</strong>100 个样本里只有 1 个超过 p99，你报的「p99」实际上就是这 100 次里的最大值，而最大值的方差极大（一次系统中断就能污染它）。<em>更糟的是，如果你还是「同一张图跑 100 次」，那么数据依赖的那部分方差压根没进入样本。</em><strong>面试里被问「你们的 p99 是多少」，正确的回答要包含三件事：样本量、样本来源（真实帧序列还是重复单帧）、测量时长（是否覆盖热稳态）。</strong>只报一个数字，等于承认没做过。</p>", "样本量不够，p99 就是伪科学"),
        CALLOUT("intuition", "把七宗罪压成一句检查：<strong>「我丢了 warmup 吗？我同步了吗？我用的是真实帧序列吗？我跑够 10000 次了吗？我报的是端到端还是纯推理？」</strong>五个问题全过，这个数字才配写进报告。"),
    ])),

    # ============================================================== 2
    ("tail", "为什么是 p99，不是均值", "".join([
        P("数据中心优化吞吐，车端优化<strong>尾延迟</strong>。这不是偏好差异，是任务性质的差异：网页慢 200 ms 用户皱个眉，感知帧晚 20 ms 到达，下游会按时间戳把它<strong>整帧丢弃</strong>——这一帧的算力白花了，而且这一帧本来可能正好包含那块新出现的限速牌。"),
        H3("超时率的算术：p99 达标 ≠ 安全"),
        P("30 FPS 意味着每小时 $30 \\times 3600 = 108{,}000$ 帧。把「超过延迟预算」的比例记作 $\\epsilon$："),
        MATH("N_{\\text{timeout/h}} \\;=\\; \\epsilon \\cdot f \\cdot 3600, \\qquad \\bar{T}_{\\text{between}} \\;=\\; \\frac{1}{\\epsilon f}"),
        TABLE(["达标水平", "$\\epsilon$", "每小时超时帧数", "平均多久一次", "工程判断"], [
            ["p90 ≤ 预算", "10%", "10 800", "0.33 s", "不可用"],
            ["<strong>p99 ≤ 预算</strong>", "1%", "<strong>1 080</strong>", "<strong>3.3 s</strong>", "<strong>听起来很好，实际每 3 秒丢一帧</strong>"],
            ["p99.9 ≤ 预算", "0.1%", "108", "33 s", "多数量产系统的实际门槛"],
            ["p99.99 ≤ 预算", "0.01%", "10.8", "5.6 min", "安全相关任务的目标"],
        ]),
        DUAL(
            "第二行是本节最该记住的一行。<strong>「我们的 p99 达标」听起来是个很好的结论，翻译成物理事件就是「每 3.3 秒丢一帧」</strong>。对一个 30 FPS 的感知链路，这意味着跟踪器每隔几秒就要处理一次「这一帧没有观测」；如果丢帧还不被上报（模块 04 讲过的静默丢帧），下游的生命周期状态机会误以为目标消失。",
            "更严重的是<strong>超时的相关性</strong>。上面那张表隐含假设「每帧是否超时相互独立」，但真实系统里超时几乎从不独立：<em>热节流会让连续几万帧都变慢；一次内存碎片整理会连累几十帧；另一个感知任务的突发负载会压住 TSR 十几帧</em>。<strong>所以除了 $\\epsilon$，还必须报「最长连续超时段」</strong>——独立假设下 1% 超时率出现连续 5 帧超时的概率是 $10^{-10}$（几乎不可能），而热节流下连续 5000 帧超时是常态。<em>两者的 p99 可以完全一样，但对系统的伤害差着数量级。</em>notebook 里会把这两种分布并排放出来。",
        ),
        H3("各个统计量分别回答什么问题"),
        TABLE(["统计量", "回答的问题", "什么时候看它", "陷阱"], [
            ["<strong>均值</strong>", "总算力消耗是多少", "做容量规划、算功耗", "<strong>对长尾几乎不敏感</strong>；1% 的帧慢 10 倍，均值只涨 9%"],
            ["p50", "典型体验", "对比两个方案的「常规速度」", "两个 p50 相同的系统，p99 可以差 3 倍"],
            ["p90 / p95", "调优时的粗粒度信号", "迭代过程中快速看趋势", "对安全论证不够"],
            ["<strong>p99 / p99.9</strong>", "<strong>会不会超时、多久超一次</strong>", "<strong>验收、安全论证、调度预留</strong>", "样本量不足时不可信（见第 1 节）"],
            ["max", "有没有异常事件", "<strong>发现问题</strong>，不是设指标", "单样本，噪声极大；一次中断就能污染"],
            ["<strong>最长连续超时段</strong>", "会不会「连续失明」", "热/抢占相关的验收", "<strong>最常被漏掉的指标</strong>"],
        ]),
        H3("尾延迟从哪来：四个来源要分开治"),
        UL([
            "<strong>数据依赖</strong>：NMS 的耗时是 $O(NK)$，$N$ 与 $K$ 都随场景复杂度增长（C53 模块 04 实测 log-log 斜率约 1.7）。<em>治法：给 NMS 输入设硬上限，或换无 NMS 架构，或把后处理搬到 GPU（模块 04）。</em>",
            "<strong>系统抖动</strong>：Linux 非实时内核的调度延迟、页错误、中断、锁竞争、内存分配器。<em>治法：关键线程绑核 + <code>SCHED_FIFO</code> + <code>isolcpus</code>；稳态期禁止分配（模块 04 的 C++ 检查单）。</em>",
            "<strong>硬件</strong>：<strong>热节流与功耗墙</strong>（第 7 节）、DRAM refresh、其他任务抢占。<em>治法：长时间测试 + 功耗模式声明 + 时间片预算。</em>",
            "<strong>软件架构</strong>：多余的同步点、动态 shape 触发的 tactic 切换、队列排队。<em>治法：Nsight Systems 看时间线（模块 04）。</em>",
        ]),
        CALLOUT("warn", "<strong>TSR 场景的反相关是最讨厌的地方：延迟尖峰恰好出现在场景最复杂、最需要及时反应的时候。</strong>高速上视野里 2 块标志，候选框少、NMS 快；开进城市路口，龙门架 + 一排限速牌 + 店铺招牌 + 贴满贴纸的货车，候选框涨十倍、NMS 慢十倍——<em>而这正是最容易出现「新标志突然出现、必须尽快识别」的场景</em>。<strong>「平均够快」在这里没有任何安全意义。</strong>"),
    ])),

    # ============================================================== 3
    ("decompose", "端到端延迟分解：推理往往只占一半", "".join([
        P("优化的第一步不是「让模型更快」，是<strong>知道时间花在哪里</strong>。下面是一个典型 TSR 检测器在车端 SoC 上的分解（640×640 输入、200 类、三尺度 8400 个位置、FP16 engine；数字是量级真实的示意值）："),
        ASCII("""朴素实现（14.32 ms）
取帧 ▏0.30
CPU 预处理 ████████▏3.20         ← resize+letterbox+归一化+HWC→CHW，单核
H2D fp32 ▊0.31                   ← 640x640x3x4 = 4.91 MB
推理 FP16 ████████████████████▉8.20
D2H raw ▌0.21                    ← 8400x204xfp16 = 3.43 MB
CPU 解码+NMS █████▎2.10
                                    推理占比 **57.3%**

优化后（9.03 ms，模型一个字节没改）
取帧(零拷贝) ▏0.05
GPU 预处理 ▉0.35                  ← 融合成一个 kernel
H2D uint8 ▎0.08                   ← **1.23 MB，降到 1/4**（归一化搬到 GPU 上做）
推理 FP16 ████████████████████▉8.20
GPU 解码+NMS ▉0.35
D2H 300 框 ▏0.001                 ← **7.2 KB，降到 1/480**
                                    推理占比 **90.8%**，端到端省 **37%**"""),
        TABLE(["阶段", "朴素", "优化后", "怎么优化的", "收益"], [
            ["取帧", "0.30", "0.05", "相机 dmabuf 直接映射给 CUDA，省掉一次 memcpy", "0.25"],
            ["<strong>预处理</strong>", "<strong>3.20</strong>", "<strong>0.35</strong>", "CPU 单核 → 融合的 GPU kernel（或 VIC 硬件缩放器）", "<strong>2.85</strong>"],
            ["H2D", "0.31", "0.08", "<strong>传 uint8 而不是 float32</strong>，归一化在 GPU 上做", "0.23"],
            ["推理", "8.20", "8.20", "—（本节不碰模型）", "0"],
            ["D2H", "0.21", "0.001", "GPU 侧解码 + NMS，只回传 300 个框", "0.21"],
            ["<strong>后处理</strong>", "<strong>2.10</strong>", "<strong>0.35</strong>", "解码与 NMS 搬到 GPU（模块 04 方案 B/C）", "<strong>1.75</strong>"],
            ["<strong>合计</strong>", "<strong>14.32</strong>", "<strong>9.03</strong>", "", "<strong>5.29 ms（37%）</strong>"],
        ]),
        DUAL(
            "<strong>整整 5.3 ms，比换一个更小的模型划算得多——而且完全不掉精度。</strong>如果你去优化模型，从 8.2 ms 压到 6.5 ms（掉 1.5 mAP）也只省 1.7 ms。<em>新手一上来就想换 backbone，老手先量拷贝和预处理。</em>",
            "两条最容易被忽略的收益值得单独拎出来。<em>①<strong>H2D 传 uint8 而不是 float32，拷贝量直接降 4 倍</strong></em>——归一化本来就是逐元素操作，是访存受限的（见下一节），放在 GPU 上做几乎免费，而在 CPU 上做既慢又把数据撑大 4 倍。<em>②<strong>D2H 只传最终框而不是 raw tensor，降 480 倍</strong></em>——8400×204 的 raw 输出有 3.43 MB，而 300 个框只有 7.2 KB。<strong>这两条加起来省的 0.44 ms 看着不多，但它们的真正价值是把 PCIe/内存总线让出来给别的任务</strong>——车端 SoC 上带宽是所有感知任务共享的稀缺资源，你少占 4 MB/帧，就是每秒少占 120 MB/s。",
        ),
        CALLOUT("intuition", "一条可迁移的心法：<strong>先画分解图，再决定优化什么。</strong>没有分解图的性能优化都是猜。而画分解图的成本是一天，猜错的成本是两周。"),
        CALLOUT("warn", "<p><strong>分解时要小心「逐层耗时之和 ≠ 端到端」。</strong>打开 per-layer profiling 会在每层后插同步点，破坏层间重叠、抑制某些融合，于是<em>逐层之和通常比端到端<strong>大</strong>（10–30% 不等）</em>。反过来，如果你测出「逐层之和明显<strong>小于</strong>端到端」，那差额就是 CPU 提交开销、排队、同步等待——<strong>这个差额本身是一个非常有价值的诊断量</strong>（对应 <code>trtexec</code> 的 Host Latency 减去 GPU Compute Time）。用 <code>--separateProfileRun</code> 把两件事分开测。</p>", "逐层之和与端到端不该相等"),
    ])),

    # ============================================================== 4
    ("roofline", "Roofline：算子到底受什么限制", "".join([
        P("知道「时间花在哪个阶段」之后，下一层问题是「这个阶段为什么慢」。<span class=\"term\">Roofline</span> 模型用两个硬件常数和一个算子属性就能回答它。"),
        MATH("I \\;=\\; \\frac{\\text{FLOPs}}{\\text{Bytes}} \\quad(\\text{算术强度}), \\qquad P_{\\text{attainable}} \\;=\\; \\min\\bigl(P_{\\text{peak}},\\; I \\times BW\\bigr), \\qquad I_{\\text{ridge}} \\;=\\; \\frac{P_{\\text{peak}}}{BW}"),
        P("取一块车端 SoC 的量级（GPU FP16 峰值约 42 TFLOPS、LPDDR5 带宽约 204.8 GB/s）："),
        MATH("I_{\\text{ridge}} \\;=\\; \\frac{42 \\times 10^{12}}{204.8 \\times 10^{9}} \\;\\approx\\; \\mathbf{205}\\ \\text{FLOP/Byte}"),
        P("<strong>205 是一个高得吓人的脊点。</strong>它意味着：一个算子必须每读 1 个字节就做 205 次浮点运算，才配称为「计算受限」。绝大多数算子达不到。逐个算给你看（FP16，40×40 特征图，256 通道）："),
        TABLE(["算子", "FLOPs", "访存 Bytes", "$I$", "判定", "预测耗时", "<strong>比 FLOPs 预测慢几倍</strong>"], [
            ["3×3 conv 256→256", "1.887 G", "2.82 M", "<strong>670</strong>", "<span class=\"badge cpu\">计算受限</span>", "44.9 μs", "1.0×"],
            ["3×3 conv 256→256 <em>@80×80</em>", "7.550 G", "7.73 M", "976", "计算受限", "179.8 μs", "1.0×"],
            ["1×1 conv 256→256", "0.210 G", "1.77 M", "119", "<strong>访存受限</strong>", "8.6 μs", "1.7×"],
            ["<strong>5×5 depthwise 256</strong>", "<strong>0.020 G</strong>", "1.65 M", "<strong>12.4</strong>", "<strong>严重访存受限</strong>", "8.1 μs", "<strong>16.5×</strong>"],
            ["逐元素 Add", "0.0004 G", "2.46 M", "0.17", "极端访存受限", "12.0 μs", "1200×"],
            ["SiLU / 激活", "0.0016 G", "1.64 M", "1.0", "极端访存受限", "8.0 μs", "200×"],
            ["Concat / Transpose / Reformat", "<strong>0</strong>", "≥ 2×数据量", "0", "<strong>纯访存</strong>", "&gt; 8 μs", "∞"],
        ]),
        H3("这张表里最重要的一行"),
        DUAL(
            "<strong>5×5 depthwise 的 FLOPs 只有 3×3 稠密卷积的 1/92，但延迟只快 5.6 倍。</strong>换句话说，它的实际耗时是「按 FLOPs 推算」的 <strong>16.5 倍</strong>。原因很直白：depthwise 卷积每个输出通道只用自己那一个输入通道，<em>数据复用率极低</em>——搬进来的每个字节只被用了 25 次乘加（$k^2$），而稠密卷积用了 $256 \\times 9 = 2304$ 次。",
            "这直接修正了一个常见的误读。C53 模块 03 讲 RTMDet 用 5×5 depthwise 大核时说「参数量代价极小」——<strong>那句话是对的，但它说的是参数量，不是延迟</strong>。$k$ 从 3 涨到 5，depthwise 的 FLOPs 涨 2.78 倍，但访存量几乎不变（权重只占 12.8 KB，可以忽略），于是<em>延迟几乎不涨</em>——从这个角度看大核确实是「便宜」的。<strong>但整个 depthwise 算子本身相对于它的 FLOPs 就是「贵」的</strong>：0.02 GFLOP 的算子花掉 8.1 μs，而 1.887 GFLOP 的稠密卷积才花 44.9 μs。<em>结论是：<strong>FLOPs 不是延迟的好代理，尤其在轻量化架构上</strong>——MobileNet 系、ShuffleNet 系、以及所有大量使用 depthwise 的模型，其「FLOPs 很低」与「延迟很低」之间存在系统性的落差。选型时必须实测，不能查表。</em>",
        ),
        H3("融合为什么收益这么大"),
        P("<code>Conv → BN → SiLU</code> 三个算子串起来，如果不融合："),
        TABLE(["", "FLOPs", "访存", "耗时", "说明"], [
            ["3×3 Conv", "1.887 G", "2.82 M", "<strong>44.9 μs</strong>", "计算受限，这是不可省的部分"],
            ["BN（逐元素仿射）", "0.0008 G", "1.64 M", "8.0 μs", "<strong>纯搬运</strong>：读一遍写一遍"],
            ["SiLU", "0.0016 G", "1.64 M", "8.0 μs", "<strong>纯搬运</strong>"],
            ["<strong>不融合合计</strong>", "", "", "<strong>60.9 μs</strong>", ""],
            ["<strong>融合后</strong>", "", "", "<strong>44.9 μs</strong>", "BN 折进卷积权重（构建期），SiLU 融进 epilogue（不落盘）"],
            ["<strong>收益</strong>", "", "", "<strong>−26%</strong>", "<em>而 FLOPs 只减少了 0.13%</em>"],
        ]),
        CALLOUT("intuition", "<strong>融合省的从来不是计算，是「把中间结果写回显存再读回来」这一趟。</strong>这就是为什么模块 02 里「什么阻止了融合」值得追究——一个多余的 <code>Reshape</code>、一个被别处引用的中间张量、一个不支持的激活函数，都会把两个本可以融合的算子拆开，代价是一趟完整的往返访存。"),
        H3("三种诊断结论与各自的对策"),
        TABLE(["观察到", "判定", "对策"], [
            ["有效算力接近峰值（$I > I_{\\text{ridge}}$）", "<strong>计算受限</strong>", "降精度（FP16→INT8 直接翻倍）、减 FLOPs（剪枝/蒸馏/换结构）、用 Tensor Core 友好的通道数（32 的倍数）"],
            ["有效带宽接近峰值（$I < I_{\\text{ridge}}$）", "<strong>访存受限</strong>", "<strong>融合</strong>、降精度（也减字节！）、改 layout（NHWC / NC32HW32）、增大 batch 复用权重"],
            ["<strong>两个都远低于峰值</strong>", "<strong>并行度不足</strong>", "增大 batch、多流并发、<strong>CUDA Graph 消除启动开销</strong>、检查是不是 tail effect（最后一个 wave 的 SM 没填满）"],
        ]),
        CALLOUT("warn", "<p><strong>第三行最容易被忽略，而它在小模型上是常态。</strong>每个 kernel 的启动开销约 <strong>5–10 μs</strong>（含 CPU 侧提交与 GPU 侧调度）。一个融合后仍有 200 层的网络，光启动开销就是 <strong>1.0–2.0 ms</strong>——对一个 8 ms 的模型是 12–25%。<em>症状是「GPU 利用率只有 40%，但换更大的模型延迟几乎不涨」</em>。<strong>治法是 CUDA Graph</strong>：把整张图的 kernel 序列录制一次，之后每帧只提交一次 graph，把 $N$ 次启动摊成 1 次。<em>代价是 shape 必须固定（动态 shape 要每档录一个 graph），且录制期间不能有 CPU 侧的条件分支——这正好和「稳态期不分配、不同步」的纪律吻合（模块 04）。</em></p>", "小模型上，启动开销可能是最大的一项"),
    ])),

    # ============================================================== 5
    ("fallback", "静默回退：「转了 TRT 但没变快」", "".join([
        P("这是模块 02 埋下的伏笔，在这里给出<strong>可执行的检测方法</strong>。症状永远是同一句话：「我转了 TensorRT / 开了 FP16 / 做了 INT8，但延迟基本没变。」"),
        H3("四种回退，四种检测"),
        TABLE(["回退类型", "发生了什么", "检测方法", "红灯判据"], [
            ["<strong>① 子图切分</strong>", "不支持的算子把图切成多个子图，分别交给不同后端（TRT EP / CUDA EP / 甚至 CPU EP）。<strong>每次子图切换都要一次同步 + 可能的 D2H/H2D</strong>", "ONNX Runtime：日志里的 <code>Number of subgraphs</code>；设 <code>ORT_TENSORRT_DUMP_SUBGRAPHS=1</code> 导出子图查看", "<strong>子图数 &gt; 1 就要追问原因</strong>；&gt; 3 基本等于没提速"],
            ["<strong>② FP16 未生效</strong>", "<code>kFP16</code> 是「<em>允许</em>」不是「强制」。TRT 的 tactic selection 基于实测，某层若 FP16 kernel 更慢或不存在，会自动选 FP32", "<code>IEngineInspector</code> 导出 engine layer 信息（JSON），看每层的 <code>Precision</code> 字段；或 <code>--verbose</code> 日志", "<strong>FP32 层的耗时占比 &gt; 10%</strong> 就要逐层查"],
            ["<strong>③ INT8 缺 dynamic range</strong>", "某层没有校准得到的量化范围 → 退回 FP32/FP16", "同上；构建日志里会有 <code>Missing scale and zero-point</code> 类告警", "任何计算密集层退回 FP32"],
            ["<strong>④ 动态 shape 选错 tactic</strong>", "实际 shape 落在 profile 的边缘，用的是为 <code>opt</code> 那档挑的 kernel", "对 min/opt/max 三档分别测延迟，看是否有反常的凸起", "非 <code>opt</code> 档的延迟 &gt; <code>opt</code> 档的 1.5 倍"],
        ]),
        ASCII("""健康的 engine                        有静默回退的 engine
─────────────────────────           ─────────────────────────────────
subgraphs: 1                        subgraphs: **4**   ← 被切碎了
                                        ├─ TRT   (conv 段)
layer precision 分布:                   ├─ **CUDA** (某个不支持的算子)
  FP16  187 层  96.4%                   ├─ TRT   (conv 段)
  FP32    7 层   3.6%                   └─ **CPU**  (某个 Loop/NMS 变体)
  (都是 LayerNorm/Softmax 等
   已知敏感层，且总耗时 < 3%)       layer precision 分布:
                                      FP16  120 层  61%
GPU Compute  8.2 ms                   **FP32   74 层  39%**  ← 红灯
Host Latency 9.0 ms                   (含 3 个 conv 主干层！)
Enqueue      0.9 ms
  → 差额 0.8 ms 合理                GPU Compute  8.4 ms
                                    Host Latency **14.6 ms** ← 差额 6.2 ms
                                      = 子图之间的同步与来回拷贝"""),
        DUAL(
            "右边那一栏是「转了 TRT 但没变快」的完整体检报告。<strong>注意 GPU Compute Time 两边差不多（8.2 vs 8.4），是 Host Latency 差了 5.6 ms</strong>——如果你只看 <code>trtexec</code> 报的 GPU 时间，会得出「engine 没问题」的错误结论。<em>子图切分的代价不在计算里，在同步和拷贝里。</em>",
            "把这套检查<strong>自动化</strong>是本节的落点：解析 <code>IEngineInspector</code> 输出的 layer JSON（每层有 name / LayerType / Precision / TacticValue / 输入输出格式）与 <code>--dumpProfile</code> 的逐层耗时，合并成一张表，然后跑几条规则：<em>①子图数 == 1；②FP32 层耗时占比 &lt; 10%；③没有计算密集层（Conv/MatMul）落在 FP32；④没有出现 <code>Reformat</code> 层占用超过 5% 的耗时（reformat 是纯访存的格式转换，大量出现说明相邻层的 layout 偏好冲突）；⑤动态 shape 三档的延迟单调且无异常凸起。</em><strong>这五条规则跑一次不到一秒，却能挡住绝大多数「优化了但没优化」的发布。</strong>notebook 里会把这个检查器实现出来。",
        ),
        CALLOUT("danger", "<p><strong><code>Reformat</code> 层是最容易被忽略的时间小偷。</strong>TensorRT 在两个 layout 偏好不同的层之间会自动插入 reformat（比如 <code>NCHW</code> ↔ <code>NC32HW32</code>，或 FP32 ↔ FP16 的转换）。这些层<em>不在你的 ONNX 里</em>，是构建器自己加的，所以你在模型结构里看不到它们。<strong>它们的算术强度是 0（纯搬运），却可能占掉 5–15% 的总耗时。</strong><em>治法：让通道数取 32 的倍数、让首尾层的精度与输入输出格式对齐（比如直接用 <code>kHALF</code> 的 NHWC 输入，避免入口处的一次 reformat）、避免在网络中间混用无法融合的精度。</em>面试里能主动提 reformat，说明你真的读过 engine 的 layer 表而不只是跑过 <code>trtexec</code>。</p>", "你的 ONNX 里没有的层，可能占掉 10% 的时间"),
    ])),

    # ============================================================== 6
    ("batch-stream", "批处理、多流与车端多相机", "".join([
        P("批处理是数据中心提升吞吐的第一手段，在车端却<strong>基本用不上——除非你有多相机</strong>。这一节把账算清楚。"),
        H3("批处理的收益来自哪里"),
        P("把一次推理的时间拆成两部分：<em>与 batch 成正比的激活相关部分</em> $T_{\\text{act}}$，和<em>与 batch 无关的权重读取部分</em> $T_w$（权重只需读一次，供整个 batch 复用）："),
        MATH("T(b) \\;=\\; b\\,T_{\\text{act}} + T_w \\qquad\\Longrightarrow\\qquad \\frac{T(b)}{b} \\;=\\; T_{\\text{act}} + \\frac{T_w}{b} \\;\\xrightarrow[b\\to\\infty]{}\\; T_{\\text{act}}"),
        P("所以<strong>吞吐的提升上限是 $\\frac{T_{\\text{act}}+T_w}{T_{\\text{act}}}$，而且完全由权重读取的占比决定</strong>。取 $T_{\\text{act}}=6.0$ ms、$T_w=2.2$ ms（即 batch=1 时 8.2 ms）："),
        TABLE(["batch", "总耗时", "每帧摊薄", "吞吐提升", "<strong>单相机下的端到端延迟</strong>", "多相机（硬件同步）"], [
            ["1", "8.2 ms", "8.20 ms", "—", "<strong>8.2 ms</strong>", "8.2 ms"],
            ["2", "14.2 ms", "7.10 ms", "+15%", "33.3 + 14.2 = <strong>47.5 ms</strong>（等 1 帧）", "14.2 ms"],
            ["<strong>4</strong>", "26.2 ms", "6.55 ms", "<strong>+25%</strong>", "100 + 26.2 = <strong>126.2 ms</strong>（等 3 帧）", "<strong>26.2 ms</strong>（无等待）"],
            ["8", "50.2 ms", "6.28 ms", "+31%", "233 + 50.2 = <strong>283 ms</strong>", "50.2 ms"],
        ]),
        DUAL(
            "第五列是车端否决批处理的理由：<strong>单相机做 batch=4，必须先等齐 4 帧，30 FPS 下就是白等 100 ms</strong>。为了把每帧摊薄从 8.2 压到 6.55 ms（省 1.65 ms），付出 100 ms 的等待——这笔账在任何延迟敏感系统里都不成立。<em>吞吐提升 25% 是真的，延迟恶化 15 倍也是真的。</em>",
            "<strong>但最后一列是车端唯一真正合理的批处理场景</strong>：多相机。前视长焦 + 前视广角 + 左右侧视，四路<em>同一时刻</em>曝光的图像天然构成一个 batch，<strong>不需要任何等待</strong>。串行跑是 $4\\times8.2=32.8$ ms，batch 跑是 26.2 ms，<em>省 20% 且延迟不增加</em>。<strong>前提有两条，缺一不可</strong>：<em>①四路必须硬件同步曝光</em>（否则「等齐」又回来了，而且时间戳还不一致）；<em>②四路必须用同一个模型与同一个输入分辨率</em>——如果长焦用 640×640 而鱼眼用 960×640，或者长焦跑 TSR 模型而侧视跑另一个模型，就没法组 batch。<em>在 TSR 里这一条经常不成立：远处小标志需要长焦的高分辨率，而侧视相机根本不需要跑 TSR。</em><strong>所以多相机 batching 的适用面比听起来窄得多，要具体看你的相机配置。</strong>",
        ),
        H3("多流：填满 SM，但会推高单帧延迟"),
        UL([
            "<strong>多流的收益来自「一个 kernel 填不满 GPU」</strong>。小模型、小分辨率、小 batch 时，单个 kernel 可能只用掉 30% 的 SM，剩下的算力闲置。开 $N$ 条 stream 并发跑 $N$ 帧（或 $N$ 个任务），可以把利用率推上去。",
            "<strong>代价是单帧延迟上升</strong>：多个 kernel 竞争 SM、竞争 L2、竞争带宽。<em>吞吐涨了，但每一帧都变慢了</em>——这又是「吞吐 vs 延迟」的对立（模块 04 的线程模型表是同一个道理）。",
            "<strong>stream priority 不是硬实时保证</strong>。CUDA 的 <code>cudaStreamCreateWithPriority</code> 只影响新 block 的调度倾向，<em>已经在跑的 kernel 不会被抢占</em>。一个长 kernel 可以把高优先级任务堵住几毫秒。<strong>车端要「TSR 优先」，靠的不是 stream priority，而是时间片预算与任务编排（下一节）。</strong>",
            "<strong>MPS / MIG 在车端 SoC 上通常不可用</strong>，别按数据中心的经验做方案。",
        ]),
        CALLOUT("warn", "<strong>动态 batch 的隐藏成本：optimization profile。</strong>如果你想「有几路相机就用几路的 batch」，engine 必须建成动态 batch（min=1, opt=4, max=8）。代价有三：<em>①构建时间显著变长（每档都要 tune）；②非 <code>opt</code> 档的 tactic 不是为它挑的，实测常有 10–30% 的额外损耗；③显存必须按 <code>max</code> 档预留</em>。<strong>如果相机数量是固定的（量产车通常是），就用固定 batch 建 engine，别为了「灵活」白付这三笔钱。</strong>"),
    ])),

    # ============================================================== 7
    ("thermal", "车端特有约束：功耗墙、降频、抢占", "".join([
        P("这一节的内容在数据中心几乎不存在，在车上是决定性的。<strong>桌面 GPU 有 300 W 的风冷预算和 25 °C 的机房；车端 SoC 有 30 W 的被动散热和夏天 60 °C 的舱内环境。</strong>"),
        H3("① 功耗模式：同一个 engine，延迟可以差两倍"),
        P("车端 SoC 通常提供若干档功耗预算（例如 15 W / 30 W / 50 W / 无限制），由整车的电源与热设计决定。<strong>同一个 engine 在不同档下的延迟可以差 1.5–2 倍。</strong>因此："),
        CALLOUT("danger", "<p><strong>任何一个延迟数字，不声明功耗模式就是无效的。</strong>论文里报「Orin 上 8 ms」而不说是哪档，等于没说；你自己的报告也一样。<em>更常见的内部事故是：算法团队在开发板上用 MAXN 模式测出 8.2 ms，写进设计文档；集成到量产域控后实际是 30 W 档，跑出 13 ms，整个时序预算作废。</em><strong>纪律：benchmark 脚本第一行就打印当前功耗模式与时钟频率，并把它写进结果文件。</strong></p>", "不声明功耗模式的延迟数字是无效数字"),
        H3("② 热节流：短 benchmark 全是骗人的"),
        P("持续满负载下结温上升，超过阈值后 SoC 主动降频。一个简化的一阶热模型："),
        MATH("T(t) = T_{\\text{amb}} + P R_{\\text{th}}\\bigl(1 - e^{-t/\\tau}\\bigr), \\qquad \\frac{f}{f_{\\max}} = \\operatorname{clip}\\bigl(1 - k\\,[T - T_{\\text{thr}}]_+,\\ \\ \\tfrac{f_{\\min}}{f_{\\max}},\\ 1\\bigr), \\qquad T_{\\text{lat}} \\propto \\frac{1}{f}"),
        P("代入一组车规量级的参数（$T_{\\text{amb}}=55$ °C 的夏季舱内、$P=40$ W、$R_{\\text{th}}=1.1$ °C/W、$\\tau=300$ s、节流阈值 85 °C、$k=0.02$/°C、最低频比 0.65）："),
        TABLE(["运行时长", "结温", "频率比", "p50 延迟", "<strong>p99 延迟</strong>", "相对第 1 分钟"], [
            ["第 1 分钟", "59 °C", "1.00", "8.4 ms", "<strong>9.2 ms</strong>", "—"],
            ["第 5 分钟", "84 °C", "1.00", "8.4 ms", "9.2 ms", "0%"],
            ["第 10 分钟", "94 °C", "0.83", "10.2 ms", "<strong>11.1 ms</strong>", "<strong>+21%</strong>"],
            ["第 30 分钟", "99 °C", "0.72", "11.7 ms", "<strong>12.7 ms</strong>", "<strong>+38%</strong>"],
            ["稳态（&gt; 45 min）", "99 °C", "0.72", "11.7 ms", "<strong>12.8 ms</strong>", "<strong>+38%</strong>"],
        ]),
        DUAL(
            "<strong>跑一分钟测出 p99 = 9.2 ms，跑 30 分钟是 12.7 ms。</strong>如果你的延迟预算是 12 ms，那么开发板上「余量 23%」的方案，在夏天开了半小时的车上<strong>已经超预算了</strong>（余量 −6%，17% 的帧超时）——<em>而这半小时恰恰是长途驾驶最需要 TSR 稳定工作的时候</em>。",
            "两个必须补充的严谨点。<em>①这个一阶模型是<strong>简化</strong>的</em>：真实系统里降频会同时降低功耗，$P$ 与 $f$ 耦合，达到的是一个自洽的热平衡点，实测曲线通常比模型更早收敛、更平缓。<strong>模型的价值不在预测精确值，而在告诉你「必须测长时间」这件事，以及给你一个外推的形状。</strong><em>②验收要报<strong>分段 p99</strong> 而不是整段 p99</em>——把 30 分钟切成 1 分钟一段，每段各算 p99，看这条曲线是否收敛、收敛到哪。<strong>整段 p99 会把「前 5 分钟很快」和「后 25 分钟很慢」混在一起平均掉，恰好掩盖了你最想看的那个漂移。</strong><em>而且必须在<strong>目标环境温度</strong>下测</em>：实验室 22 °C 空调房里测出的热稳态，和舱内 60 °C 是两个世界。",
        ),
        H3("③ 多任务抢占：TSR 只是众多感知任务之一"),
        ASCII("""一颗共享 SoC 上的感知任务（33 ms 一个周期，30 FPS）
┌──────────────────────────────────────────────────────────────┐
│ BEV 3D 检测      ████████████ 12.0 ms                        │
│ 占用栅格         █████████ 9.0 ms                            │
│ **TSR**          ████████ 8.2 ms   ← 我们                    │
│ 车道线           ████ 4.0 ms                                 │
│ 多目标跟踪(CPU)  ██ 2.0 ms                                   │
├──────────────────────────────────────────────────────────────┤
│ 合计             35.2 ms   >  33.3 ms 的周期预算   ← **超了** │
└──────────────────────────────────────────────────────────────┘

降级策略（按优先级从低到高牺牲）
  · 车道线      降到 15 Hz（隔帧跑）        省 2.0 ms
  · 占用栅格    输入分辨率 ×0.8             省 2.6 ms
  · **TSR**     decoder 6 层 → 3 层         省 0.9 ms（掉约 1 AP，C53 模块 04）
  · 兜底        丢帧（**最后手段**，且必须上报 frame_id）"""),
        UL([
            "<strong>GPU kernel 默认不可抢占</strong>（或抢占粒度很粗）。一个 3 ms 的长 kernel 会把所有其他任务堵住 3 ms，无论它们优先级多高。<em>所以「给 TSR 设高优先级」并不能保证它准时。</em>",
            "<strong>正确的做法是时间片预算（time-slice budgeting）</strong>：给每个任务分配固定的时间窗口，由一个编排层按周期调度；任务超出窗口就触发<strong>降级</strong>而不是抢占。<em>降级路径必须提前设计好并测试过</em>——这正是 C53 模块 04 里「RT-DETR 的 decoder 层数可调」在部署上的真实价值：它提供了一条<strong>精度可降级</strong>的路径，让系统在算力紧张时优雅退化，而不是直接丢帧。",
            "<strong>DLA 卸载是车端特有的一张牌</strong>。Orin 这类 SoC 带独立的深度学习加速器，可以把部分任务放上去与 GPU 并行。但 DLA 支持的算子有限、精度只有 FP16/INT8、单位算力也低于 GPU，<em>适合放对延迟不那么敏感、结构又规整的任务</em>（比如后处理简单的分割网络），而不是延迟最紧的那个。",
            "<strong>CPU 侧也要治</strong>：非实时 Linux 内核的调度抖动可以到几毫秒。关键线程绑核（<code>sched_setaffinity</code>）+ <code>SCHED_FIFO</code> + <code>isolcpus</code> 隔离出专用核，能把 CPU 侧的尾延迟压下一个量级。",
        ]),
        CALLOUT("intuition", "车端延迟工程与数据中心的根本差别，一句话：<strong>数据中心问「平均每秒能处理多少」，车端问「最坏情况下这一帧会不会晚」。</strong>前者优化吞吐、可以排队；后者优化尾延迟、不能排队，而且要在功耗、温度、共享算力三重约束下证明它。"),
    ])),

    # ============================================================== 8
    ("checklist", "发布前验收清单", "".join([
        P("前面七节的内容，最终要凝结成一张<strong>可以自动化执行的门禁表</strong>。下面这张表是量产 TSR 模型上车前的最小集合——<em>每一项都对应一个真实的事故类型</em>。"),
        TABLE(["#", "维度", "指标", "通过条件（示例）", "怎么测", "不过怎么办"], [
            ["1", "<strong>精度</strong>", "整体 mAP 相对 FP32 baseline 的掉幅", "≤ 1.0 mAP", "全量评测集", "回到模块 03：敏感层分析 + 混合精度"],
            ["2", "<strong>精度·分桶</strong>", "<strong>每一个像素尺寸桶</strong>的 AP 掉幅", "<strong>≤ 2.0 mAP（任意一桶）</strong>", "按 &lt;16 / 16–32 / 32–64 / &gt;64 px 分桶", "<strong>先查坐标变换（模块 04），再怀疑量化</strong>"],
            ["3", "<strong>精度·关键类</strong>", "停车让行 / 限速 等安全关键类的召回", "≥ baseline − 1%", "关键类子集评测", "代价敏感的阈值重标定"],
            ["4", "<strong>延迟</strong>", "端到端 p50 / <strong>p99</strong> / p99.9", "p99 ≤ 预算；p99.9 ≤ 预算 × 1.1", "≥ 10 000 帧真实序列，含密集场景", "第 3–5 节的分解与 roofline"],
            ["5", "<strong>延迟·连续性</strong>", "<strong>最长连续超时段</strong>", "≤ 2 帧", "同上，逐帧标记", "查热节流与抢占（第 7 节）"],
            ["6", "<strong>显存</strong>", "峰值占用", "≤ 分配预算的 80%", "运行时 query，取 max", "减 batch / 减 workspace / 复用 buffer"],
            ["7", "<strong>长时间稳定性</strong>", "<strong>分段 p99 的漂移</strong>；RSS 斜率", "漂移 ≤ 10%；RSS 斜率 ≈ 0（无泄漏）", "<strong>≥ 30 min（推荐 2 h）连续跑，目标环境温度下</strong>", "散热设计 / 降低稳态功耗 / 设计降级路径"],
            ["8", "<strong>多硬件一致性</strong>", "不同 SoC 批次 / 驱动版本上的输出一致性", "框匹配率（IoU ≥ 0.99）≥ 99.9%", "同一批图在 N 个平台上跑，逐帧比对", "查非确定性 kernel 与 engine 重建流程"],
            ["9", "<strong>数值一致性</strong>", "与 Python 参考实现的逐阶段对拍", "<strong>8 个阶段全过</strong>", "模块 04 的对拍工具", "按对拍报告定位到具体阶段"],
            ["10", "<strong>engine 完整性</strong>", "构建环境指纹校验", "GPU 型号 + 驱动 + TRT 版本 + ONNX 哈希全部匹配", "engine 元数据 vs 运行时环境", "<strong>拒绝加载</strong>，走重建流程"],
            ["11", "<strong>冷启动</strong>", "进程启动 → 第一帧可用", "≤ 整车上电预算", "含 engine 反序列化 + warmup", "engine 预加载 / 延迟 warmup / 分级可用"],
            ["12", "<strong>回退方案</strong>", "<strong>降级路径本身被测试过</strong>", "注入「加载失败 / 推理超时 / 输出异常」三种故障，系统行为符合预期", "<strong>故障注入测试</strong>", "补齐降级路径并重测"],
            ["13", "<strong>可观测性</strong>", "分阶段耗时、候选数、检出数、丢帧数打点", "全部字段可上报且有采样策略", "查日志 schema", "补打点——<em>没有打点的系统在车上无法归因</em>"],
        ]),
        CALLOUT("danger", "<p><strong>清单里最容易被跳过的是第 7 项和第 12 项，而它们恰恰是量产事故的主要来源。</strong>第 7 项被跳过是因为<em>慢</em>——跑 30 分钟意味着一次验证要占掉半小时，迭代节奏里没人愿意等；第 12 项被跳过是因为<em>「应该不会发生」</em>——降级路径写了但从没被触发过，于是它本身就是没测过的代码，真出事时降级路径自己崩了。<strong>正确做法：第 7 项进夜间 CI（反正没人等），第 12 项做成故障注入的自动化用例（三种故障各一条）。</strong><em>面试里被问「你们怎么保证上线质量」，能说出「长时间测试进夜间 CI + 降级路径做故障注入」这两条，比背十个指标名字有说服力。</em></p>", "跳过的两项，正好是事故的两大来源"),
        DUAL(
            "这张表看起来很长，但它的执行成本其实很低：<strong>第 1–6、8–11 项都可以脚本化，跑一遍不到一小时；第 7 项进夜间 CI；第 12 项是几条固定的故障注入用例。</strong>真正贵的是「没有这张表」——每次发布靠人回忆该查什么，漏掉的那一项就是下次事故。",
            "更进一步，这张表应该<strong>输出一份结构化的发布报告</strong>而不只是 pass/fail：每一项记录实测值、门限、余量百分比、以及本次相对上次的变化。<em>余量百分比是最有价值的一列</em>——它告诉你哪一项正在悄悄逼近门限。<strong>典型的场景是：连续三个版本 p99 从 9.1 → 9.6 → 10.2 ms，每次都「通过」（门限 12 ms），但趋势明摆着说下一次就要撞墙。</strong><em>门禁只能挡住已经越界的，趋势才能提前告诉你要撞墙了。</em>这也是为什么第 13 项（可观测性）不是可选项——<strong>没有打点的系统，你连趋势都画不出来。</strong>",
        ),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>kernel 启动开销与图执行。</strong>CUDA Graph 把 $N$ 次 kernel 启动摊成一次提交，对小模型能省 10–25%；但它要求 shape 固定、无 CPU 分支。<em>「如何在动态 shape 与控制流下仍然享受图执行」是活跃方向</em>（条件节点、图更新 API、多档预录制），目前仍需要工程上做取舍。",
            "<strong>编译器路线与手写 kernel 的边界。</strong>TVM / TensorRT / Triton / MLIR 各自在自动搜索融合与 schedule；但在检测这类「主干规整、头部零碎」的模型上，自动编译器往往在<em>头部与后处理</em>上做不过手写。<em>「哪些部分该交给编译器、哪些必须手写」目前没有普适答案，只能实测。</em>",
            "<strong>实时 GPU 调度仍是开放问题。</strong>GPU 的抢占粒度粗、优先级不是硬保证，学术界的 kernel 切分（kernel slicing）、持久线程（persistent threads）、SM 分区等方案都在尝试给 GPU 任务提供可界定的 WCET。<em>在车端多任务共享一颗 SoC 的场景下，这是「能不能证明不超时」的关键，也是功能安全论证最薄弱的一环。</em>",
            "<strong>能耗感知的模型设计。</strong>当前几乎所有架构搜索的目标都是 FLOPs 或延迟，而车端真正的硬约束往往是<strong>能耗</strong>（它决定了热稳态，进而决定了持续延迟）。<em>「以 J/frame 为目标的 NAS」还很少见，但它比以 FLOPs 为目标更贴近车端现实</em>——本模块第 4 节已经说明了 FLOPs 与延迟的脱节，而延迟与能耗之间还有第二层脱节（访存的能耗远高于计算）。",
            "<strong>Anytime inference / 可中断推理。</strong>让模型在任意时刻被打断时都能给出一个「当前最好的结果」，质量随允许的时间单调提升。<em>DETR 系的逐层辅助头天然接近这个性质（C53 模块 04），但真正的 anytime 需要调度器与模型协同设计</em>，目前在自动驾驶里还停留在「几档固定降级」的粗粒度形态。",
            "<strong>Roofline 之外的性能模型。</strong>经典 roofline 忽略了 cache 层次、并行度不足、启动开销与 tail effect。ECM（Execution-Cache-Memory）模型、cache-aware roofline 等扩展更贴近真实，<em>但都还没有成为深度学习部署的常规工具</em>——实践中仍然是「先用 roofline 分类，再用 profiler 实测」。",
            "<strong>车规功能安全对延迟可预测性的要求正在收紧。</strong>ISO 26262 / ASIL 与 AUTOSAR Adaptive 对时序确定性有明确诉求，而「一个包含 GPU、共享内存、非实时内核的 AI 推理栈如何给出可论证的 WCET」目前业界还没有令人满意的答案。<em>这也是为什么「无 NMS」「固定 query 数」「层数可裁」这类<strong>把数据依赖项消掉</strong>的架构性质，在车端的价值被系统性低估了。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Williams, Waterman &amp; Patterson, <em>Roofline: An Insightful Visual Performance Model for Multicore Architectures</em>（CACM 2009）——本模块第 4 节的全部理论基础，篇幅不长，值得完整读一遍并自己画一张你目标硬件的 roofline 图。<strong>★</strong> Dean &amp; Barroso, <em>The Tail at Scale</em>（CACM 2013）——尾延迟这个概念在工程界的奠基文本，虽然写的是数据中心，但「为什么均值没有意义」「尾延迟从哪来」「怎么治」这三条对车端同样成立。</p><p><strong>★</strong> NVIDIA 官方文档三份，都要逐字读参数而不是看教程：<em>TensorRT Developer Guide</em> 的 Performance Best Practices 与 <code>IEngineInspector</code> 章节；<em>trtexec</em> 的完整参数表（尤其 <code>--warmUp</code> / <code>--duration</code> / <code>--avgRuns</code> / <code>--dumpProfile</code> / <code>--separateProfileRun</code> / <code>--useCudaGraph</code>）；<em>Nsight Systems User Guide</em> 的时间线判读部分（如何看 CPU 与 GPU 泳道的重叠）。配套：Jetson/Orin 平台的功耗模式与热管理指南——<strong>它是第 7 节所有数字的来源</strong>。</p><p>相邻课程：模块 01（预处理一致性）、模块 02（engine 构建、层融合与算子回退——第 5 节的伏笔在那里埋下）、模块 03（INT8 与精度门禁）、模块 04（后处理放 GPU、C++ 管线的内存与同步纪律、逐阶段对拍）、C53 模块 04（NMS 的数据依赖与「延迟不确定性」的完整论证）、C53 模块 05（延迟-精度权衡与选型）、C55 模块 05（安全导向的评测体系）、C61 模块 05（部署类面试题的答题骨架）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 05 · 性能剖析与延迟工程（p99 / roofline / 热降频 / 验收门禁）

目标：把「这个模型跑多快」从一个含糊的口号，变成一组**有测量口径、有统计依据、有验收门限**的数字。

本 notebook 你会亲手实现：
1. **warmup 效应**与「不同步就计时」造出的假 FPS，量化不丢 warmup 会高估多少
2. **p99 需要多少样本**：从二项分布推出 $\\sigma_{\\text{rank}} = \\sqrt{np(1-p)}$，并用蒙特卡洛验证
3. **超时率的算术**：p99 达标 = 每 3.3 秒丢一帧；以及**最长连续超时段**为什么必须单独报
4. **端到端延迟分解**：推理只占 57% → 优化拷贝与预处理后占 91%，端到端省 37%（模型没动）
5. **Roofline**：算子的算术强度、脊点、瓶颈判定，以及 **depthwise 卷积慢于 FLOPs 预测 16.5 倍**
6. **静默回退检查器**：解析 engine 的逐层精度与耗时，五条规则自动亮红灯
7. **批处理的延迟代价**与多相机场景；**热降频模拟**与分段 p99
8. **发布验收门禁**：13 项检查的自动化实现 + 余量趋势

> 心智模型：**数据中心问「平均每秒处理多少」，车端问「最坏情况下这一帧会不会晚」。**"""),

    md("""## 1 · 测延迟的七宗罪：warmup 与「不同步」

第一次推理里塞满了 CUDA context 创建、kernel 模块懒加载、handle 初始化、首次显存分配。
下面用一个衰减模型模拟它（首次约 95 ms，时间常数 25 次）。"""),

    code("""import numpy as np

STEADY_MS = 8.20                                  # 稳态 GPU 耗时

def simulate_bench(n, steady=STEADY_MS, first=95.0, tau=25.0, jitter=0.12, seed=0):
    # 模拟一次 benchmark：前若干次因 lazy init / kernel 加载 / 显存分配而极慢
    r = np.random.default_rng(seed)
    i = np.arange(n)
    warm = 1.0 + (first / steady - 1.0) * np.exp(-i / tau)
    return steady * warm + r.gamma(2.0, jitter, n)

lat = simulate_bench(1000)
print(f'第 1 次              : {lat[0]:8.2f} ms   ← 稳态的 {lat[0]/STEADY_MS:.1f} 倍')
print(f'前 10 次均值         : {lat[:10].mean():8.2f} ms')
print(f'前 100 次均值        : {lat[:100].mean():8.2f} ms')
print(f'**全部 1000 次均值** : {lat.mean():8.2f} ms   ← 不丢 warmup 就会报这个数')
print(f'**丢弃前 500 次后**  : {lat[500:].mean():8.2f} ms   ← 这才是稳态延迟')

over = lat.mean() / lat[500:].mean() - 1
print(f'\\n不丢 warmup 会**高估 {over:.1%}**')
assert lat[:100].mean() > 2 * STEADY_MS
assert over > 0.15
assert abs(lat[500:].mean() - STEADY_MS - 0.24) < 0.15
print('✅ 规则：至少丢弃前 200-500 次。trtexec 用 --warmUp=500（单位是毫秒，不是次数，注意读文档）。')"""),

    code("""# —— 罪状 2：不同步就计时，会测出荒谬的 FPS ——
ENQUEUE_MS = 0.045          # CPU 把这一次推理提交进 stream 的时间（异步，立刻返回）
GPU_MS = 8.20               # GPU 上真正执行的时间
H2D_D2H_MS = 0.39           # 拷贝
CPU_PRE_POST = 0.70         # CPU 侧预处理尾巴 + 结果整理

fake_fps = 1000.0 / ENQUEUE_MS
gpu_fps = 1000.0 / GPU_MS
e2e_ms = ENQUEUE_MS + GPU_MS + H2D_D2H_MS + CPU_PRE_POST
print(f\"{'口径':<34s} {'延迟 ms':>10s} {'FPS':>10s}\")
print(f\"{'❌ 只测 enqueue（忘了同步）':<34s} {ENQUEUE_MS:>10.3f} {fake_fps:>10.0f}\")
print(f\"{'GPU Compute Time（CUDA event）':<34s} {GPU_MS:>10.3f} {gpu_fps:>10.1f}\")
print(f\"{'Host Latency（含拷贝）':<34s} {GPU_MS+H2D_D2H_MS:>10.3f} {1000/(GPU_MS+H2D_D2H_MS):>10.1f}\")
print(f\"{'✅ 端到端（含预处理与后处理）':<34s} {e2e_ms:>10.3f} {1000/e2e_ms:>10.1f}\")

assert fake_fps > 20000, '不同步测出来的 FPS 会是荒谬的量级'
assert e2e_ms > GPU_MS + 1.0, '端到端必然明显大于纯 GPU 时间'
print(f'\\n⚠️  {fake_fps:.0f} FPS 与 {1000/e2e_ms:.1f} FPS 相差 {fake_fps/(1000/e2e_ms):.0f} 倍 —— '
      '而两者都能被写成「我们测出来的 FPS」。')
print('✅ 报 FPS 必须声明口径。trtexec 的四个数（GPU Compute / Enqueue / Host Latency / Throughput）')
print('   要分清；Enqueue 接近甚至超过 GPU Compute，说明 CPU 提交跟不上 -> 上 CUDA Graph。')"""),

    md("""## 2 · p99 要多少样本才算得准

$n$ 个样本中 $p$ 分位落在第 $\\lceil pn \\rceil$ 个次序统计量上，
「超过真实 $p$ 分位的样本数」服从 $\\mathrm{Bin}(n, 1-p)$，秩的标准差是 $\\sigma_{\\text{rank}}=\\sqrt{np(1-p)}$。"""),

    code("""def rank_sigma(n, p=0.99):
    return float(np.sqrt(n * p * (1 - p)))

print(f\"{'n':>8s} {'秩':>8s} {'超过 p99 的样本数':>18s} {'σ_rank':>9s} {'95% 分位区间':>22s}\")
for n in [100, 1000, 10000, 100000]:
    s = rank_sigma(n)
    lo, hi = (0.99 * n - 1.96 * s) / n, (0.99 * n + 1.96 * s) / n
    print(f'{n:>8d} {int(np.ceil(0.99*n)):>8d} {int(round(n*0.01)):>18d} {s:>9.2f} '
          f'{"[%.2f%%, %.2f%%]" % (lo*100, hi*100):>22s}')
assert int(round(100 * 0.01)) == 1, 'n=100 时只有 1 个样本超过 p99 —— 你的 p99 就是最大值'
print('\\n⚠️  n=100 时「p99」= 最大值，而最大值的方差极大（一次系统中断就能污染它）。')

# —— 蒙特卡洛验证：估计值的离散程度确实按 1/sqrt(n) 收缩 ——
def draw(n, seed):
    return np.random.default_rng(seed).gamma(9.0, 0.9, n) + 4.0

TRUE_P99 = float(np.percentile(draw(2_000_000, 1), 99))
print(f'\\n真实 p99（200 万样本）= {TRUE_P99:.4f} ms')
print(f\"{'n':>8s} {'估计均值':>10s} {'估计标准差':>12s} {'最大偏差':>10s}\")
stds = []
for n in [100, 1000, 10000]:
    est = np.array([np.percentile(draw(n, 5000 + k), 99) for k in range(300)])
    stds.append(est.std())
    print(f'{n:>8d} {est.mean():>10.4f} {est.std():>12.4f} {np.abs(est-TRUE_P99).max():>10.4f}')
assert stds[0] > stds[1] > stds[2], '样本量越大，p99 估计越稳'
assert stds[0] > 3 * stds[2], 'n=100 与 n=10000 的估计离散度应差 3 倍以上'
print(f'\\n✅ n=100 的估计标准差是 n=10000 的 {stds[0]/stds[2]:.1f} 倍。')
print('   30 FPS 下 10000 帧 ≈ 5.5 分钟 —— **这是 p99 的最低采样成本**；')
print('   要估 p99.9 则需要约 10 万帧 ≈ 55 分钟（正好也覆盖了热稳态，一举两得）。')"""),

    md("""## 3 · 尾延迟与超时账：p99 达标 = 每 3.3 秒丢一帧

合成一条真实形态的延迟序列：**固定部分 + 数据依赖的 NMS（超线性）+ 系统抖动 + 罕见尖峰**。"""),

    code("""FPS, N_FRAME = 30, 200_000

def make_latency(n, seed=0, fixed=6.40):
    r = np.random.default_rng(seed)
    n_obj = np.clip(r.lognormal(np.log(8), 0.9, n).astype(int) + 1, 1, 220)   # 重尾：多数帧目标少
    n_cand = n_obj * 22 + 10 + 3 * n_obj                                       # 候选数随场景增长
    nms = 0.25 + 6e-5 * n_cand ** 1.35                                         # **超线性**（C53 m04）
    sysj = r.gamma(1.5, 0.18, n)                                               # 调度抖动
    spike = (r.random(n) < 0.004) * r.uniform(3.0, 12.0, n)                    # 罕见系统尖峰
    return fixed + nms + sysj + spike, n_obj

lat, n_obj = make_latency(N_FRAME, seed=42)
qs = dict(zip(['p50', 'p90', 'p99', 'p99.9'], np.percentile(lat, [50, 90, 99, 99.9])))
print(f\"{'mean':>8s} {'p50':>8s} {'p90':>8s} {'p99':>8s} {'p99.9':>8s} {'max':>8s}\")
print(f'{lat.mean():>8.2f} {qs[\"p50\"]:>8.2f} {qs[\"p90\"]:>8.2f} {qs[\"p99\"]:>8.2f} '
      f'{qs[\"p99.9\"]:>8.2f} {lat.max():>8.2f}')
print(f'\\n场景目标数分布: p50={np.percentile(n_obj,50):.0f}  p99={np.percentile(n_obj,99):.0f}  '
      f'max={n_obj.max()}')

assert lat.mean() < qs['p99'], '均值对长尾几乎不敏感'
assert qs['p99'] - qs['p50'] > 1.5, 'p99 与 p50 之间应有可观差距'
assert lat.max() > qs['p99.9'] + 1.0, 'max 是单样本，噪声远大于 p99.9'

print(f\"\\n{'延迟预算':>10s} {'超时率 ε':>10s} {'超时帧/小时':>12s} {'平均多久一次':>14s}\")
prev = 1e9
for budget in sorted([8.0, 9.0, qs['p99'], 10.0, 11.0, 12.0]):
    eps = float((lat > budget).mean())
    per_h = eps * FPS * 3600
    gap = (1 / (eps * FPS)) if eps > 0 else float('inf')
    tag = '  ← 恰好 p99' if abs(budget - qs['p99']) < 1e-9 else ''
    print(f'{budget:>10.2f} {eps:>10.2%} {per_h:>12.0f} {gap:>13.1f}s{tag}')
    assert eps <= prev; prev = eps

eps99 = float((lat > qs['p99']).mean())
per_h99 = eps99 * FPS * 3600
assert abs(per_h99 - 1080) < 80, per_h99
print(f'\\n⚠️  **「p99 达标」翻译成物理事件 = 每小时 {per_h99:.0f} 帧超时 = 每 {1/(eps99*FPS):.1f} 秒丢一帧。**')
print('   对 30 FPS 的感知链路，这意味着跟踪器每隔几秒就要处理一次「这一帧没有观测」。')
print('   多数量产系统的实际门槛是 p99.9（每 33 秒一次），安全相关任务要到 p99.99。')"""),

    code("""# —— 同一组延迟值，同样的每一个分位数，重排一下顺序，安全性完全不同 ——
def longest_run(mask):
    best = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    return best

BUDGET = float(qs['p99'])
mask_indep = lat > BUDGET
idx_to = np.where(mask_indep)[0]
idx_ok = np.where(~mask_indep)[0]
# 构造「成簇」版本：把所有超时帧连续地排在一起（模拟热节流 / 突发抢占）
clustered = np.concatenate([lat[idx_ok[:50_000]], lat[idx_to], lat[idx_ok[50_000:]]])
mask_clu = clustered > BUDGET

print(f\"{'':<14s} {'mean':>8s} {'p50':>8s} {'p99':>8s} {'p99.9':>8s} {'超时率':>9s} {'最长连续超时':>13s}\")
for nm, x, mk in [('独立抖动', lat, mask_indep), ('成簇（热节流）', clustered, mask_clu)]:
    p = np.percentile(x, [50, 99, 99.9])
    print(f'{nm:<14s} {x.mean():>8.2f} {p[0]:>8.2f} {p[1]:>8.2f} {p[2]:>8.2f} '
          f'{mk.mean():>9.2%} {longest_run(mk):>13d}')

assert np.allclose(np.percentile(lat, [50, 90, 99, 99.9]),
                   np.percentile(clustered, [50, 90, 99, 99.9])), '同一组数值，所有分位数完全相同'
assert abs(mask_indep.mean() - mask_clu.mean()) < 1e-12
r_ind, r_clu = longest_run(mask_indep), longest_run(mask_clu)
assert r_clu > 100 * r_ind, (r_ind, r_clu)
print(f'\\n⚠️  **每一个统计量都完全相同**（因为是同一组数值的重排），')
print(f'    但「最长连续超时段」从 {r_ind} 帧变成 {r_clu} 帧 = 连续 {r_clu/FPS:.0f} 秒失明。')
print('✅ 所以验收必须同时报 p99 **和** 最长连续超时段 —— 后者是最常被漏掉的指标。')
print('   独立抖动 -> 治调度与分配；成簇 -> 治热节流与多任务抢占（第 7 节）。')"""),

    md("""## 4 · 端到端延迟分解：推理往往只占一半"""),

    code("""STAGES = [
    #  阶段            朴素    优化后   优化手段
    ('取帧/解码',       0.30,   0.05,  '相机 dmabuf 直接映射给 CUDA，省一次 memcpy'),
    ('预处理',          3.20,   0.35,  'CPU 单核 -> 融合的 GPU kernel（或 VIC 硬件缩放器）'),
    ('H2D 拷贝',        0.31,   0.08,  '传 uint8 而不是 float32，归一化搬到 GPU 上做'),
    ('推理 FP16',       8.20,   8.20,  '——（本节不碰模型）'),
    ('D2H 拷贝',        0.21,   0.001, 'GPU 侧解码+NMS，只回传 300 个框'),
    ('后处理',          2.10,   0.35,  '解码与 NMS 搬到 GPU（模块 04 方案 B/C）'),
]
base = sum(s[1] for s in STAGES)
opt = sum(s[2] for s in STAGES)
print(f\"{'阶段':<12s} {'朴素 ms':>9s} {'占比':>7s} {'优化后':>8s} {'占比':>7s} {'省下':>7s}\")
for nm, b, o, how in STAGES:
    print(f'{nm:<12s} {b:>9.2f} {b/base:>7.1%} {o:>8.2f} {o/opt:>7.1%} {b-o:>7.2f}')
print(f'{\"合计\":<12s} {base:>9.2f} {1.0:>7.1%} {opt:>8.2f} {1.0:>7.1%} {base-opt:>7.2f}')

infer_b = dict((s[0], s[1]) for s in STAGES)['推理 FP16']
share_b, share_o = infer_b / base, infer_b / opt
print(f'\\n推理占比：{share_b:.1%}  ->  {share_o:.1%}')
print(f'端到端：{base:.2f} ms -> {opt:.2f} ms，**省 {base-opt:.2f} ms（{(base-opt)/base:.0%}），模型一个字节没改**')
assert 0.55 < share_b < 0.60 and share_o > 0.88
assert (base - opt) / base > 0.35

# 对照：如果去优化模型呢？
smaller = base - 8.20 + 6.50            # 换个小模型：8.2 -> 6.5 ms，代价约 -1.5 mAP
print(f'\\n对照组：换更小的模型（8.20 -> 6.50 ms，掉约 1.5 mAP）')
print(f'  端到端 {base:.2f} -> {smaller:.2f} ms，只省 {base-smaller:.2f} ms，**而且掉精度**')
assert base - opt > 3 * (base - smaller)
print(f'✅ 优化拷贝与预处理省的 {base-opt:.2f} ms，是换小模型的 {(base-opt)/(base-smaller):.1f} 倍，且零精度代价。')
print('   新手一上来就想换 backbone；老手先画分解图、先量拷贝。')"""),

    code("""# —— 拷贝量计算器：两条最容易被忽略的收益 ——
BW_GBs = 16.0                              # 有效带宽（GB/s）

def copy_ms(nbytes, bw=BW_GBs):
    return nbytes / (bw * 1e9) * 1e3

H, W, C = 640, 640, 3
N_POS, N_CLS, N_DET = 8400, 200, 300
cases = [
    ('H2D  float32 图像',      H * W * C * 4),
    ('H2D  uint8   图像',      H * W * C * 1),
    ('D2H  raw 输出 (fp16)',   N_POS * (4 + N_CLS) * 2),
    ('D2H  最终 300 框 (fp32)', N_DET * 6 * 4),
]
print(f\"{'':<24s} {'字节':>12s} {'MB':>8s} {'拷贝 ms':>9s} {'30FPS 下带宽占用':>18s}\")
for nm, nb in cases:
    print(f'{nm:<24s} {nb:>12,d} {nb/1e6:>8.3f} {copy_ms(nb):>9.4f} {nb*30/1e6:>15.1f} MB/s')

h2d_ratio = cases[0][1] / cases[1][1]
d2h_ratio = cases[2][1] / cases[3][1]
print(f'\\nH2D 传 uint8 而不是 float32：拷贝量降 **{h2d_ratio:.0f} 倍**')
print(f'D2H 只传最终框而不是 raw ：拷贝量降 **{d2h_ratio:.0f} 倍**')
assert abs(h2d_ratio - 4.0) < 1e-9
assert abs(d2h_ratio - 476.0) < 1e-9
saved_bw = (cases[0][1] - cases[1][1] + cases[2][1] - cases[3][1]) * 30 / 1e6
print(f'\\n✅ 两条加起来每秒少占 {saved_bw:.0f} MB/s 的内存带宽 ——')
print('   车端 SoC 上带宽是所有感知任务**共享**的稀缺资源，你少占一点，别的任务就快一点。')
print('   这也是为什么「拷贝优化」的价值常常被低估：它省的不只是自己的时间。')"""),

    md("""## 5 · Roofline：算子到底受什么限制

$I = \\text{FLOPs}/\\text{Bytes}$，$P = \\min(P_{\\text{peak}}, I\\cdot BW)$，脊点 $I_{\\text{ridge}} = P_{\\text{peak}}/BW$。
车端 SoC 量级：FP16 峰值 42 TFLOPS、LPDDR5 带宽 204.8 GB/s。"""),

    code("""PEAK_FLOPS = 42e12          # FP16 稠密峰值 FLOP/s
BW = 204.8e9                # 内存带宽 B/s
RIDGE = PEAK_FLOPS / BW
print(f'脊点 I_ridge = {PEAK_FLOPS:.3g} / {BW:.4g} = **{RIDGE:.0f} FLOP/Byte**')
print('-> 一个算子必须「每读 1 字节做 205 次浮点运算」才配称计算受限。绝大多数算子达不到。')
assert abs(RIDGE - 205) < 3

DB = 2                      # fp16 每元素 2 字节

def conv_cost(H, W, Cin, Cout, k, groups=1):
    flops = 2.0 * H * W * Cin * Cout * k * k / groups
    byts = (H * W * Cin + H * W * Cout + Cin * (Cout // groups) * k * k) * DB
    return flops, byts

def ew_cost(n_elem, n_read, n_write, flops_per=1.0):
    return flops_per * n_elem, (n_read + n_write) * n_elem * DB

def roofline(flops, byts):
    I = flops / byts if byts else float('inf')
    t_compute = flops / PEAK_FLOPS
    t_memory = byts / BW
    return I, max(t_compute, t_memory) * 1e6, ('计算受限' if t_compute >= t_memory else '访存受限')

OPS = [
    ('3x3 conv 256->256 @40x40', *conv_cost(40, 40, 256, 256, 3)),
    ('3x3 conv 256->256 @80x80', *conv_cost(80, 80, 256, 256, 3)),
    ('1x1 conv 256->256 @40x40', *conv_cost(40, 40, 256, 256, 1)),
    ('5x5 depthwise 256 @40x40', *conv_cost(40, 40, 256, 256, 5, groups=256)),
    ('逐元素 Add @40x40x256',     *ew_cost(40 * 40 * 256, 2, 1, 1.0)),
    ('SiLU 激活 @40x40x256',      *ew_cost(40 * 40 * 256, 1, 1, 4.0)),
    ('Concat/Reformat @40x40x256', *ew_cost(40 * 40 * 256, 1, 1, 0.0)),
]
print(f\"\\n{'算子':<28s} {'GFLOP':>8s} {'MB':>7s} {'I':>8s} {'判定':>9s} {'耗时 μs':>9s} {'比 FLOPs 预测慢':>16s}\")
res = {}
for nm, fl, by in OPS:
    I, us, kind = roofline(fl, by)
    naive_us = fl / PEAK_FLOPS * 1e6
    slow = us / naive_us if naive_us > 0 else float('inf')
    res[nm] = (I, us, kind, slow)
    st = f'{slow:>15.1f}x' if np.isfinite(slow) else f\"{'∞':>16s}\"
    print(f'{nm:<28s} {fl/1e9:>8.4f} {by/1e6:>7.2f} {I:>8.1f} {kind:>9s} {us:>9.1f}{st}')

assert res['3x3 conv 256->256 @40x40'][0] > RIDGE
assert res['5x5 depthwise 256 @40x40'][0] < RIDGE / 10
assert res['5x5 depthwise 256 @40x40'][3] > 15, 'depthwise 的实际耗时远超 FLOPs 预测'
print('\\n⚠️  **最重要的一行是 depthwise**：')
d3 = conv_cost(40, 40, 256, 256, 3)[0]
dd = conv_cost(40, 40, 256, 256, 5, groups=256)[0]
t3 = res['3x3 conv 256->256 @40x40'][1]
td = res['5x5 depthwise 256 @40x40'][1]
print(f'    5x5 depthwise 的 FLOPs 只有 3x3 稠密卷积的 1/{d3/dd:.0f}，但延迟只快 {t3/td:.1f} 倍；')
print(f'    它的实际耗时是「按 FLOPs 推算」的 **{res[\"5x5 depthwise 256 @40x40\"][3]:.1f} 倍**。')
assert 90 < d3 / dd < 95 and 5.0 < t3 / td < 6.5
print('✅ **FLOPs 不是延迟的好代理**，尤其在大量使用 depthwise 的轻量化架构上。')
print('   C53 模块 03 说 RTMDet 的 5x5 大核「参数量代价极小」是对的 —— 但那说的是参数量。')
print('   选型必须实测，不能查 FLOPs 表。')"""),

    code("""# —— Roofline 文本图 ——
print('可达性能 P = min(42 TFLOPS, I x 204.8 GB/s)      脊点 I = 205\\n')
print(f\"{'I (FLOP/B)':>12s} {'可达 P (TFLOPS)':>16s}  {'':<44s}\")
for I in [0.2, 1, 4, 12.4, 40, 119, 205, 400, 670, 976, 3000]:
    P = min(PEAK_FLOPS, I * BW) / 1e12
    bar = '█' * max(1, int(44 * (P / 42.0) ** 0.5))
    tag = ''
    if abs(I - 205) < 1e-9: tag = ' ← 脊点'
    elif abs(I - 12.4) < 0.6: tag = ' ← 5x5 depthwise'
    elif abs(I - 119) < 1.5: tag = ' ← 1x1 conv'
    elif abs(I - 670) < 5: tag = ' ← 3x3 conv'
    print(f'{I:>12.1f} {P:>16.2f}  {bar}{tag}')

# —— 融合为什么收益这么大 ——
conv_f, conv_b = conv_cost(40, 40, 256, 256, 3)
_, t_conv, _ = roofline(conv_f, conv_b)
_, t_bn, _ = roofline(*ew_cost(40 * 40 * 256, 1, 1, 2.0))
_, t_act, _ = roofline(*ew_cost(40 * 40 * 256, 1, 1, 4.0))
unfused, fused = t_conv + t_bn + t_act, t_conv
print(f'\\nConv -> BN -> SiLU')
print(f'  不融合: {t_conv:.1f} + {t_bn:.1f} + {t_act:.1f} = **{unfused:.1f} μs**')
print(f'  融合后: {fused:.1f} μs（BN 折进卷积权重，SiLU 融进 epilogue，中间结果不落显存）')
print(f'  **省 {1-fused/unfused:.0%}，而 FLOPs 只减少了 {(2+4)*40*40*256/conv_f:.2%}**')
assert unfused / fused > 1.2
print('✅ 融合省的从来不是计算，是「把中间结果写回显存再读回来」这一趟。')"""),

    code("""# —— 第三种瓶颈：并行度不足 / kernel 启动开销 ——
LAUNCH_US = 6.0                 # 每个 kernel 的启动开销（CPU 提交 + GPU 调度）
GPU_MS = 8.20

print(f\"{'融合后层数':>10s} {'启动开销 ms':>13s} {'占 8.2ms 的':>12s} {'用 CUDA Graph 后':>17s}\")
for n_layer in [60, 120, 200, 320]:
    ov = n_layer * LAUNCH_US / 1000
    graph_ov = 0.02 + n_layer * 0.15 / 1000        # graph：一次提交 + 极小的 per-node 开销
    print(f'{n_layer:>10d} {ov:>13.2f} {ov/GPU_MS:>11.1%} {graph_ov:>16.2f}')

ov200 = 200 * LAUNCH_US / 1000
assert ov200 / GPU_MS > 0.10, '200 层的启动开销就占了 8.2ms 模型的 10% 以上'
print(f'\\n⚠️  200 层的启动开销 {ov200:.2f} ms = 模型的 {ov200/GPU_MS:.0%}。')
print('    典型症状：「GPU 利用率只有 40%，但换更大的模型延迟几乎不涨」。')
print('✅ 治法是 CUDA Graph：把 kernel 序列录制一次，之后每帧只提交一次。')
print('   代价：shape 必须固定（动态 shape 要每档录一个 graph），录制期间不能有 CPU 侧分支 ——')
print('   这正好和模块 04 的「稳态期不分配、不同步」纪律吻合。')

print('\\n三种诊断结论与对策：')
for cond, verdict, fix in [
        ('有效算力接近峰值 (I > 205)', '计算受限', '降精度 FP16->INT8 / 剪枝蒸馏 / 通道数取 32 的倍数'),
        ('有效带宽接近峰值 (I < 205)', '访存受限', '**融合** / 降精度(也减字节) / 改 layout / 增大 batch 复用权重'),
        ('两个都远低于峰值',           '并行度不足', '增大 batch / 多流 / **CUDA Graph** / 检查 tail effect')]:
    print(f'  {cond:<26s} -> {verdict:<8s} : {fix}')"""),

    md("""## 6 · 静默回退检查器：把「转了 TRT 但没变快」自动化查出来

输入是 engine 的逐层信息（`IEngineInspector` 的 JSON）+ 逐层耗时（`--dumpProfile`）+ 顶层计时。
五条规则跑一次不到一秒，能挡住绝大多数「优化了但没优化」的发布。"""),

    code("""def make_engine_report(n_fp16, n_fp32_light, n_fp32_conv, n_reformat,
                       subgraphs, gpu_ms, host_ms, seed=0):
    r = np.random.default_rng(seed)
    layers = []
    for i in range(n_fp16):
        layers.append(dict(name=f'conv_{i}', type='Convolution', precision='FP16',
                           ms=float(r.uniform(0.01, 0.08))))
    for i in range(n_fp32_light):
        layers.append(dict(name=f'norm_{i}', type='Normalization', precision='FP32',
                           ms=float(r.uniform(0.005, 0.02))))
    for i in range(n_fp32_conv):
        layers.append(dict(name=f'conv_fp32_{i}', type='Convolution', precision='FP32',
                           ms=float(r.uniform(0.20, 0.55))))
    for i in range(n_reformat):
        layers.append(dict(name=f'reformat_{i}', type='Reformat', precision='FP16',
                           ms=float(r.uniform(0.01, 0.05))))
    return dict(layers=layers, subgraphs=subgraphs, gpu_ms=gpu_ms, host_ms=host_ms)

RULES = [
    ('R1 子图数 == 1',                    lambda rep, s: rep['subgraphs'] == 1),
    ('R2 FP32 层耗时占比 < 10%',           lambda rep, s: s['fp32_share'] < 0.10),
    ('R3 无计算密集层落在 FP32',           lambda rep, s: s['n_heavy_fp32'] == 0),
    ('R4 Reformat 耗时占比 < 5%',          lambda rep, s: s['reformat_share'] < 0.05),
    ('R5 Host-GPU 差额 < GPU 的 25%',      lambda rep, s: s['host_gap_share'] < 0.25),
]
HEAVY = {'Convolution', 'MatMul', 'FullyConnected'}

def summarize(rep):
    tot = sum(l['ms'] for l in rep['layers'])
    fp32 = sum(l['ms'] for l in rep['layers'] if l['precision'] == 'FP32')
    rfm = sum(l['ms'] for l in rep['layers'] if l['type'] == 'Reformat')
    heavy32 = [l for l in rep['layers'] if l['precision'] == 'FP32' and l['type'] in HEAVY]
    return dict(total=tot, fp32_share=fp32 / tot, reformat_share=rfm / tot,
                n_heavy_fp32=len(heavy32), heavy_names=[l['name'] for l in heavy32][:3],
                host_gap_share=(rep['host_ms'] - rep['gpu_ms']) / rep['gpu_ms'])

def check(rep, title):
    s = summarize(rep)
    print(f'\\n=== {title} ===')
    print(f\"  层数 {len(rep['layers'])}  子图 {rep['subgraphs']}  \"
          f\"FP32 耗时占比 {s['fp32_share']:.1%}  Reformat 占比 {s['reformat_share']:.1%}\")
    print(f\"  GPU Compute {rep['gpu_ms']:.2f} ms   Host Latency {rep['host_ms']:.2f} ms   \"
          f\"差额 {rep['host_ms']-rep['gpu_ms']:.2f} ms ({s['host_gap_share']:.0%})\")
    fails = []
    for name, fn in RULES:
        ok = fn(rep, s)
        print(f'  [{\"PASS\" if ok else \"**FAIL**\"}] {name}')
        if not ok:
            fails.append(name)
    if s['n_heavy_fp32']:
        print(f\"     ↳ 落在 FP32 的计算密集层示例: {s['heavy_names']}\")
    return fails

healthy = make_engine_report(187, 7, 0, 6, subgraphs=1, gpu_ms=8.20, host_ms=9.00, seed=1)
broken = make_engine_report(120, 71, 3, 24, subgraphs=4, gpu_ms=8.40, host_ms=14.60, seed=2)
f_ok = check(healthy, '健康的 engine')
f_bad = check(broken, '有静默回退的 engine')

assert f_ok == [], f_ok
assert len(f_bad) >= 4, f_bad
print(f'\\n⚠️  注意两者的 **GPU Compute Time 差不多**（8.20 vs 8.40）——')
print('    只看 trtexec 报的 GPU 时间会得出「engine 没问题」的错误结论。')
print('    子图切分的代价不在计算里，在**同步与来回拷贝**里（Host Latency 差了 5.6 ms）。')
print('✅ 五条规则全部可自动化。Reformat 是最容易被忽略的时间小偷 ——')
print('   它不在你的 ONNX 里，是构建器为了对齐 layout/精度自己插的，算术强度为 0。')"""),

    md("""## 7 · 批处理的延迟代价与车端多相机

$T(b) = b\\,T_{\\text{act}} + T_w$，每帧摊薄 $= T_{\\text{act}} + T_w/b$。
收益上限完全由**权重读取占比**决定；代价是必须先等齐 $b$ 帧。"""),

    code("""T_ACT, T_W, FPS = 6.0, 2.2, 30      # 激活相关部分 / 权重读取部分（与 batch 无关）

def batch_time(b):
    return b * T_ACT + T_W

print(f\"{'batch':>6s} {'总耗时':>9s} {'每帧摊薄':>10s} {'吞吐提升':>9s} \"
      f\"{'单相机端到端(含等待)':>22s} {'多相机(硬件同步)':>18s}\")
per_prev = None
for b in [1, 2, 4, 8]:
    tot = batch_time(b); per = tot / b
    gain = batch_time(1) / per - 1
    wait = (b - 1) / FPS * 1000
    print(f'{b:>6d} {tot:>8.1f}ms {per:>9.2f}ms {gain:>8.0%} '
          f'{wait+tot:>19.1f}ms {tot:>16.1f}ms')
    if per_prev is not None:
        assert per < per_prev
    per_prev = per

assert (3 / FPS * 1000 + batch_time(4)) > 100, '单相机 batch=4 的端到端延迟超过 100 ms'
serial4, batched4 = 4 * batch_time(1), batch_time(4)
print(f'\\n单相机 batch=4：每帧摊薄 8.20 -> 6.55 ms（省 1.65 ms），'
      f'代价是等 3 帧 = {3/FPS*1000:.0f} ms -> **端到端 {3/FPS*1000+batch_time(4):.1f} ms**')
print('  吞吐 +25% 是真的，延迟恶化 15 倍也是真的。任何延迟敏感系统都不做这笔交易。')
print(f'\\n**多相机（4 路硬件同步曝光）**：无需等待')
print(f'  串行跑 4 路: {serial4:.1f} ms      batch 跑 4 路: {batched4:.1f} ms      '
      f'省 {1-batched4/serial4:.0%}')
assert batched4 < serial4 and (1 - batched4 / serial4) > 0.15
print('✅ 这是车端唯一真正合理的批处理场景。**前提有两条，缺一不可**：')
print('   ① 四路必须硬件同步曝光（否则「等齐」又回来了，时间戳还不一致）')
print('   ② 四路必须同模型同分辨率 —— 而 TSR 里这条经常不成立：')
print('      远处小标志需要长焦的高分辨率，侧视相机根本不跑 TSR。')"""),

    md("""## 8 · 热降频模拟与分段 p99

一阶热模型 $T(t)=T_{\\text{amb}}+PR_{\\text{th}}(1-e^{-t/\\tau})$，频率随温度线性下调，延迟 $\\propto 1/f$。
**跑 100 帧和跑 30 分钟，是两个不同的世界。**"""),

    code("""T_AMB, P_W, R_TH, TAU = 55.0, 40.0, 1.1, 300.0     # 夏季舱内 55°C，40W，热阻 1.1°C/W
T_THR, K_THR, F_MIN = 85.0, 0.02, 0.65             # 85°C 起节流，每度降 2%，下限 0.65
BASE_MS = 8.20

def junction_temp(t_s):
    return T_AMB + P_W * R_TH * (1.0 - np.exp(-np.asarray(t_s, float) / TAU))

def freq_ratio(T):
    return np.clip(1.0 - K_THR * np.maximum(0.0, np.asarray(T, float) - T_THR), F_MIN, 1.0)

rng = np.random.default_rng(7)
DUR_MIN = 45
t_s = np.arange(DUR_MIN * 60 * FPS) / FPS
f_ratio = freq_ratio(junction_temp(t_s))
lat_th = (BASE_MS + rng.gamma(1.5, 0.18, len(t_s))) / f_ratio

BUDGET_MS = 12.0
print(f\"{'时刻':>10s} {'结温 °C':>9s} {'频率比':>8s} {'p50':>8s} {'p99':>8s} \"
      f\"{'相对第1分钟':>12s} {'超预算率':>9s}\")
seg_p99 = {}
for minute in [0, 5, 10, 20, 30, 44]:
    m = (t_s >= minute * 60) & (t_s < (minute + 1) * 60)
    seg = lat_th[m]
    p50, p99 = np.percentile(seg, [50, 99])
    seg_p99[minute] = p99
    rel = p99 / seg_p99[0] - 1 if minute else 0.0
    print(f'{minute:>7d} min {junction_temp((minute+0.5)*60):>9.1f} '
          f'{freq_ratio(junction_temp((minute+0.5)*60)):>8.2f} {p50:>8.2f} {p99:>8.2f} '
          f'{rel:>11.0%} {(seg>BUDGET_MS).mean():>9.2%}')

assert seg_p99[5] < 1.02 * seg_p99[0], '前 5 分钟还没到节流阈值，看不出问题'
assert seg_p99[30] > 1.25 * seg_p99[0], '30 分钟后 p99 应显著抬升'
print(f'\\n⚠️  第 1 分钟 p99 = {seg_p99[0]:.2f} ms，第 30 分钟 p99 = {seg_p99[30]:.2f} ms，'
      f'**漂移 +{seg_p99[30]/seg_p99[0]-1:.0%}**')
print(f'    延迟预算 {BUDGET_MS} ms：开始时余量 {1-seg_p99[0]/BUDGET_MS:.0%}，'
      f'半小时后余量 {1-seg_p99[30]/BUDGET_MS:.0%}')
print('    **而这半小时恰恰是长途驾驶最需要 TSR 稳定工作的时候。**')
print(f'\\n整段 p99（45 分钟一起算）= {np.percentile(lat_th, 99):.2f} ms ——')
print('    它把「前 5 分钟很快」和「后 40 分钟很慢」平均掉了，恰好掩盖了你最想看的漂移。')
print('✅ 所以验收要报**分段 p99**（1 分钟一段），看它是否收敛、收敛到哪。')
print('   还要注意：真实系统里降频会同时降功耗，P 与 f 耦合，实测曲线通常更早收敛、更平缓；')
print('   这个模型的价值不在预测精确值，而在告诉你「必须测长时间」以及给你一个外推的形状。')"""),

    code("""# —— 多任务时间片预算与降级 ——
TASKS = [('BEV 3D 检测', 12.0), ('占用栅格', 9.0), ('TSR', 8.2),
         ('车道线', 4.0), ('多目标跟踪(CPU)', 2.0)]
PERIOD_MS = 1000.0 / FPS
HEADROOM = 0.90                                  # 留 10% 余量给抖动
BUDGET = PERIOD_MS * HEADROOM

DEGRADE = [   # (任务, 手段, 省下 ms, 代价描述)
    ('车道线',   '降到 15 Hz（隔帧跑）',        2.00, '车道线更新率减半'),
    ('占用栅格', '输入分辨率 x0.8',             2.60, '远处栅格精度下降'),
    ('TSR',      'decoder 6 层 -> 3 层',        0.90, '约 -1 AP（C53 模块 04）'),
    ('全局',     '丢帧（最后手段）',            8.00, '**必须上报 frame_id**'),
]

total = sum(t[1] for t in TASKS)
print(f'周期预算 {PERIOD_MS:.1f} ms（30 FPS），留 10% 余量后可用 {BUDGET:.1f} ms')
for nm, ms in TASKS:
    print(f'  {nm:<18s} {ms:>6.1f} ms')
print(f'  {\"合计\":<18s} {total:>6.1f} ms   -> {\"**超了**\" if total > BUDGET else \"OK\"}')
assert total > BUDGET

applied, cur = [], total
for nm, how, save, cost in DEGRADE:
    if cur <= BUDGET:
        break
    cur -= save
    applied.append((nm, how, save, cost))
    print(f'  降级：{nm:<10s} {how:<24s} 省 {save:.2f} ms -> 合计 {cur:.2f} ms')

print(f'\\n降级 {len(applied)} 项后合计 {cur:.2f} ms <= {BUDGET:.1f} ms ✅')
assert cur <= BUDGET and len(applied) == 3
assert applied[-1][0] == 'TSR' and '丢帧' not in [a[1] for a in applied]
print('⚠️  GPU kernel 默认**不可抢占** —— 一个 3 ms 的长 kernel 会把所有任务堵住 3 ms，')
print('    无论它们优先级多高。CUDA stream priority 只是调度倾向，不是硬实时保证。')
print('✅ 正确做法是时间片预算 + **提前设计好的降级路径**，而不是靠优先级。')
print('   RT-DETR 的「decoder 层数可裁」在这里体现出真实价值：它提供了一条**精度可降级**的路，')
print('   让系统优雅退化而不是直接丢帧 —— 丢帧是最后手段，且必须上报 frame_id。')"""),

    md("""## 9 · 发布验收门禁：13 项检查的自动化实现"""),

    code("""# (编号, 维度, 指标键, 比较符, 门限, 单位)
GATE_SPEC = [
    ('01', '精度·整体',      'map_drop',          '<=', 1.0,   'mAP'),
    ('02', '精度·分桶',      'bucket_drop_max',   '<=', 2.0,   'mAP'),
    ('03', '精度·关键类',    'key_recall_drop',   '<=', 0.01,  '比例'),
    ('04', '延迟 p99',       'p99_ms',            '<=', 12.0,  'ms'),
    ('05', '延迟连续性',     'max_consec_timeout','<=', 2,     '帧'),
    ('06', '显存峰值',       'mem_ratio',         '<=', 0.80,  '占预算'),
    ('07', '长时稳定性',     'p99_drift',         '<=', 0.10,  '比例'),
    ('08', '多硬件一致性',   'hw_match_rate',     '>=', 0.999, '比例'),
    ('09', '数值一致性',     'xdiff_stages_pass', '>=', 8,     '阶段'),
    ('10', 'engine 指纹',    'fingerprint_ok',    '>=', 1,     'bool'),
    ('11', '冷启动',         'cold_start_s',      '<=', 6.0,   's'),
    ('12', '回退方案',       'fault_cases_pass',  '>=', 3,     '用例'),
    ('13', '可观测性',       'telemetry_fields',  '>=', 6,     '字段'),
]

def release_gate(metrics, spec=GATE_SPEC):
    rows, failures = [], []
    for num, dim, key, op, thr, unit in spec:
        v = metrics[key]
        ok = (v <= thr) if op == '<=' else (v >= thr)
        margin = (1 - v / thr) if op == '<=' and thr else ((v / thr - 1) if thr else 0.0)
        rows.append((num, dim, v, op, thr, unit, ok, margin))
        if not ok:
            failures.append((num, dim, v, op, thr))
    return rows, failures

def print_gate(title, metrics):
    rows, fails = release_gate(metrics)
    print(f'\\n═══ {title} ═══')
    print(f\"{'#':>3s} {'维度':<14s} {'实测':>10s} {'门限':>12s} {'余量':>8s} {'判定':>8s}\")
    for num, dim, v, op, thr, unit, ok, margin in rows:
        print(f'{num:>3s} {dim:<14s} {v:>10.4g} {op+\" \"+format(thr, \".4g\"):>12s} '
              f'{margin:>7.0%} {\"PASS\" if ok else \"**FAIL**\":>8s}')
    print(f'  -> {\"✅ 全部通过，可发布\" if not fails else \"❌ %d 项未通过，禁止发布\" % len(fails)}')
    return fails

GOOD = dict(map_drop=0.62, bucket_drop_max=1.35, key_recall_drop=0.004, p99_ms=10.4,
            max_consec_timeout=2, mem_ratio=0.71, p99_drift=0.07, hw_match_rate=0.9995,
            xdiff_stages_pass=8, fingerprint_ok=1, cold_start_s=4.3,
            fault_cases_pass=3, telemetry_fields=9)
BAD = dict(GOOD, bucket_drop_max=4.80, max_consec_timeout=37, p99_drift=0.31)

assert print_gate('候选 A（v2.4.1）', GOOD) == []
fails_b = print_gate('候选 B（v2.5.0-rc1）', BAD)
assert len(fails_b) == 3
assert {f[0] for f in fails_b} == {'02', '05', '07'}
print('\\n候选 B 的三项失败，恰好指向三条不同的排查路径：')
print('  02 分桶掉点 -> **先查坐标变换（模块 04），再怀疑量化**（4px 偏移在 12px 框上是致命的）')
print('  05 最长连续超时 37 帧 -> 成簇超时，查热节流与多任务抢占（第 7、8 节）')
print('  07 分段 p99 漂移 31% -> 长时间稳定性不达标，查散热与稳态功耗')"""),

    code("""# —— 余量趋势：门禁只能挡住已经越界的，趋势才能提前告诉你要撞墙 ——
HISTORY = [('v2.1.0', 9.1), ('v2.2.0', 9.4), ('v2.3.0', 9.6),
           ('v2.4.0', 10.0), ('v2.4.1', 10.4)]
THR = 12.0
print(f\"{'版本':<10s} {'p99 ms':>8s} {'余量':>8s} {'判定':>8s} {'环比':>8s}\")
prev = None
for v, p in HISTORY:
    d = f'{p-prev:+.2f}' if prev is not None else '—'
    print(f'{v:<10s} {p:>8.2f} {1-p/THR:>7.0%} {\"PASS\":>8s} {d:>8s}')
    prev = p

xs = np.arange(len(HISTORY), dtype=float)
ys = np.array([p for _, p in HISTORY])
slope, intercept = np.polyfit(xs, ys, 1)
n_left = (THR - intercept) / slope - (len(HISTORY) - 1)
print(f'\\n线性外推：每个版本 p99 涨 {slope:.3f} ms，'
      f'再过 **{n_left:.1f} 个版本**就会撞上 {THR} ms 的门限')
assert slope > 0 and 0 < n_left < 8
print('⚠️  这五个版本**每一次都「通过」**，但趋势明摆着说下一次就要撞墙。')
print('✅ 所以发布报告必须输出结构化的「实测值 / 门限 / 余量 / 环比」，而不只是 pass/fail。')
print('   而这一切的前提是第 13 项（可观测性）—— **没有打点的系统，你连趋势都画不出来。**')"""),

    md("""## ✏️ 练习 1：延迟报告生成器

实现 `latency_report(lat, budget, fps)`，返回一个 dict，键为：

- `p50` / `p99` / `p999` / `max`：用 `np.percentile`（线性插值，默认行为）
- `eps`：超过 `budget` 的比例（严格大于）
- `per_hour`：`eps * fps * 3600`
- `max_consec`：**最长连续超时段**（连续多少帧都超过 budget）"""),

    code("""def latency_report(lat, budget, fps):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测（数字可口算）——
x = np.arange(1.0, 101.0)                      # 1..100，超过 95 的正好是 96..100 共 5 个
rep = latency_report(x, budget=95.0, fps=10)
print({k: round(v, 4) for k, v in rep.items()})
assert abs(rep['p50'] - 50.5) < 1e-9
assert abs(rep['p99'] - 99.01) < 1e-9
assert abs(rep['max'] - 100.0) < 1e-9
assert abs(rep['eps'] - 0.05) < 1e-12
assert abs(rep['per_hour'] - 1800.0) < 1e-9
assert rep['max_consec'] == 5, '96..100 连在一起'

# 同一组数值重排：所有分位数不变，最长连续超时段变了
y = np.zeros(100)
big = [0, 20, 40, 60, 80]
y[big] = x[95:]
y[[i for i in range(100) if i not in big]] = x[:95]
rep2 = latency_report(y, budget=95.0, fps=10)
assert abs(rep2['p99'] - rep['p99']) < 1e-9 and abs(rep2['eps'] - rep['eps']) < 1e-12
assert rep2['max_consec'] == 1
print(f\"\\n重排前 max_consec={rep['max_consec']}，重排后 max_consec={rep2['max_consec']}，\"
      f\"而 p50/p99/eps 完全相同\")
print('✅ 练习 1 通过：p99 和「最长连续超时段」是两个正交的指标，必须都报。')"""),

    md("""## ✏️ 练习 2：Roofline 判定器

实现 `roofline_us(flops, byts, peak=PEAK_FLOPS, bw=BW)`，返回 `(I, kind, us)`：

- `I = flops / byts`（`byts` 为 0 时返回 `inf`）
- `t_compute = flops/peak`，`t_memory = byts/bw`，耗时取**两者的较大值**
- `kind`：`t_compute >= t_memory` 时是 `'计算受限'`，否则 `'访存受限'`
- `us` 单位是微秒"""),

    code("""def roofline_us(flops, byts, peak=PEAK_FLOPS, bw=BW):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
f3, b3 = conv_cost(40, 40, 256, 256, 3)
I3, k3, u3 = roofline_us(f3, b3)
assert k3 == '计算受限' and abs(u3 - 44.94) < 0.05, (I3, k3, u3)
assert abs(I3 - 669.8) < 0.5

fd, bd = conv_cost(40, 40, 256, 256, 5, groups=256)
Id, kd, ud = roofline_us(fd, bd)
assert kd == '访存受限' and abs(ud - 8.06) < 0.05, (Id, kd, ud)
assert Id < RIDGE / 10

fa, ba = ew_cost(40 * 40 * 256, 2, 1, 1.0)      # 逐元素 Add
Ia, ka, ua = roofline_us(fa, ba)
assert ka == '访存受限' and Ia < 1.0

fc, bc = ew_cost(40 * 40 * 256, 1, 1, 0.0)      # 纯搬运（concat/reformat）
Ic, kc, uc = roofline_us(fc, bc)
assert Ic == 0.0 and kc == '访存受限'

print(f\"{'算子':<22s} {'I':>9s} {'判定':>9s} {'μs':>8s} {'FLOPs 预测 μs':>14s}\")
for nm, fl, by in [('3x3 conv', f3, b3), ('5x5 depthwise', fd, bd),
                   ('逐元素 Add', fa, ba), ('Concat/Reformat', fc, bc)]:
    I, k, u = roofline_us(fl, by)
    print(f'{nm:<22s} {I:>9.1f} {k:>9s} {u:>8.2f} {fl/PEAK_FLOPS*1e6:>14.3f}')
print(f'\\n✅ 练习 2 通过：depthwise 的实际耗时是 FLOPs 预测的 {ud/(fd/PEAK_FLOPS*1e6):.1f} 倍。')
print('   任何以 FLOPs 为唯一目标的架构搜索，都会在这类算子上系统性地骗自己。')"""),

    md("""## ✏️ 练习 3：分段 p99 与漂移

实现两个函数：

- `segment_p99(lat, t_s, seg_seconds)`：把时间轴按 `seg_seconds` 切段，
  返回每段的 p99 组成的数组（时间戳 `t_s` 与 `lat` 一一对应；空段跳过）
- `drift(segs)`：返回 `segs.max() / segs[0] - 1`（相对第一段的最大漂移）"""),

    code("""def segment_p99(lat, t_s, seg_seconds):
    # TODO
    raise NotImplementedError

def drift(segs):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测（构造一个阶跃：前 5 分钟 8ms，后 5 分钟 12ms）——
tt = np.arange(0, 600, 1.0 / 30)
ll = np.where(tt < 300, 8.0, 12.0)
segs = segment_p99(ll, tt, 60)
print('分段 p99:', np.round(segs, 3))
assert len(segs) == 10, len(segs)
assert np.allclose(segs[:5], 8.0) and np.allclose(segs[5:], 12.0)
assert abs(drift(segs) - 0.5) < 1e-9

# 接到第 8 节的热降频序列上
segs_th = segment_p99(lat_th, t_s, 60)
print(f'\\n热降频序列：{len(segs_th)} 段，第 1 段 p99 = {segs_th[0]:.2f} ms，'
      f'最后一段 = {segs_th[-1]:.2f} ms，漂移 = {drift(segs_th):.0%}')
assert len(segs_th) == 45
assert drift(segs_th) > 0.25, '30 分钟以上的漂移应超过 25%'
whole = float(np.percentile(lat_th, 99))
print(f'整段 p99 = {whole:.2f} ms —— 它介于两端之间，把漂移平均掉了。')
assert segs_th[0] < whole < segs_th[-1] + 0.1
print('✅ 练习 3 通过：**整段 p99 会掩盖漂移，分段 p99 才看得见它。**')
print('   验收门槛写「分段 p99 漂移 <= 10%」，而不是「整段 p99 <= X」。')"""),

    md("""## ✏️ 练习 4：时间片降级求解器

实现 `degrade_to_fit(total_ms, degrade_list, budget_ms)`：

- `degrade_list` 是 `[(任务名, 省下 ms), ...]`，**按优先级从低到高排好序**（先牺牲优先级低的）
- 按顺序应用降级，直到 `total <= budget` 或降级手段用完
- 返回 `(applied_names, final_ms)`；一开始就满足预算时返回 `([], total_ms)`"""),

    code("""def degrade_to_fit(total_ms, degrade_list, budget_ms):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
DEG = [('车道线', 2.0), ('占用栅格', 2.6), ('TSR', 0.9), ('丢帧', 8.0)]

a1, f1 = degrade_to_fit(35.2, DEG, 30.0)
assert a1 == ['车道线', '占用栅格', 'TSR'] and abs(f1 - 29.7) < 1e-9, (a1, f1)

a2, f2 = degrade_to_fit(35.2, DEG, 34.0)
assert a2 == ['车道线'] and abs(f2 - 33.2) < 1e-9, (a2, f2)

a3, f3 = degrade_to_fit(29.0, DEG, 30.0)
assert a3 == [] and abs(f3 - 29.0) < 1e-9, '本来就够，不该降级'

a4, f4 = degrade_to_fit(60.0, DEG, 30.0)
assert a4 == ['车道线', '占用栅格', 'TSR', '丢帧'] and f4 > 30.0, '手段用完仍不够，要报警'

for tot, bud in [(35.2, 30.0), (35.2, 34.0), (29.0, 30.0), (60.0, 30.0)]:
    ap, fin = degrade_to_fit(tot, DEG, bud)
    status = 'OK' if fin <= bud else '**仍然超预算 -> 必须报警并回退模型**'
    print(f'负载 {tot:>5.1f} ms / 预算 {bud:>5.1f} ms -> 降级 {str(ap):<44s} 剩 {fin:>5.2f} ms  {status}')
print('\\n✅ 练习 4 通过：降级路径必须**提前设计好并测试过** —— 它本身就是要上车的代码。')
print('   注意最后一行：手段用完仍不够时，系统必须报警而不是默默丢帧。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def latency_report(lat, budget, fps):
    lat = np.asarray(lat, dtype=float)
    over = lat > budget
    best = cur = 0
    for v in over:
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    eps = float(over.mean())
    p50, p99, p999 = np.percentile(lat, [50, 99, 99.9])
    return dict(p50=float(p50), p99=float(p99), p999=float(p999), max=float(lat.max()),
                eps=eps, per_hour=eps * fps * 3600, max_consec=int(best))"""),

    code("""# 练习 2 参考答案
def roofline_us(flops, byts, peak=PEAK_FLOPS, bw=BW):
    I = (flops / byts) if byts else float('inf')
    t_compute = flops / peak
    t_memory = byts / bw
    kind = '计算受限' if t_compute >= t_memory else '访存受限'
    return I, kind, max(t_compute, t_memory) * 1e6"""),

    code("""# 练习 3 参考答案
def segment_p99(lat, t_s, seg_seconds):
    lat = np.asarray(lat, dtype=float); t_s = np.asarray(t_s, dtype=float)
    idx = (t_s // seg_seconds).astype(int)
    out = []
    for k in range(idx.min(), idx.max() + 1):
        m = idx == k
        if m.any():
            out.append(float(np.percentile(lat[m], 99)))
    return np.array(out)

def drift(segs):
    segs = np.asarray(segs, dtype=float)
    return float(segs.max() / segs[0] - 1.0)"""),

    code("""# 练习 4 参考答案
def degrade_to_fit(total_ms, degrade_list, budget_ms):
    applied, cur = [], float(total_ms)
    for name, save in degrade_list:
        if cur <= budget_ms:
            break
        cur -= save
        applied.append(name)
    return applied, cur"""),

    md("""---
## 🧪 真实工程胶囊：benchmark 脚本骨架 + 发布验收流程"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 第一部分：一次「说得清楚」的 benchmark 必须记录什么
#   把它写成脚本头部的元数据，跟结果一起存档 —— 缺任何一项，这个数字都不可比
# ══════════════════════════════════════════════════════════════════════
bench_meta:
  hardware:      Orin AGX 64GB
  power_mode:    MAXN            # ← **必须声明**，不同档延迟可差 1.5-2 倍
  clocks:        "jetson_clocks --show 的输出"
  trt_version:   10.x
  driver:        "…"
  precision:     FP16            # 或 INT8 + 校准集版本
  batch:         1
  input_shape:   [1,3,640,640]
  scope:         end_to_end      # end_to_end | gpu_only  ← 口径
  includes:      [preprocess, h2d, infer, postprocess, d2h]
  warmup:        500             # 次
  frames:        10000           # ← p99 的最低采样量；估 p99.9 要 10 万
  frame_source:  "real_sequence_urban_v3"   # **不是同一张图跑 N 次**
  duration_min:  45              # ← 覆盖热稳态
  ambient_c:     55              # ← 目标环境温度，不是空调房

# ══════════════════════════════════════════════════════════════════════
# 第二部分：trtexec 常用姿势
# ══════════════════════════════════════════════════════════════════════
# ① 稳态延迟（分开性能跑与 profile 跑，避免观察者效应）
#   trtexec --loadEngine=tsr.plan --shapes=images:1x3x640x640 \
#           --warmUp=2000 --duration=120 --avgRuns=100 --percentile=99
# ② 逐层耗时（**单独一次跑**）
#   trtexec --loadEngine=tsr.plan --dumpProfile --separateProfileRun \
#           --exportProfile=layers.json
# ③ 逐层精度与 tactic（查静默回退）
#   trtexec --loadEngine=tsr.plan --dumpLayerInfo --exportLayerInfo=layers_info.json
# ④ CUDA Graph（小模型上常有 10-25% 收益）
#   trtexec --loadEngine=tsr.plan --useCudaGraph
# ⑤ 动态 shape 三档都要测
#   for s in 1x3x480x480 1x3x640x640 1x3x800x800; do trtexec --shapes=images:$s ...; done
#
# 读输出时分清四个数：GPU Compute Time / Enqueue Time / Host Latency / Throughput
#   · Enqueue ≈ GPU Compute      -> CPU 提交跟不上，上 CUDA Graph
#   · Host Latency >> GPU Compute -> 拷贝或子图切换的开销（查静默回退）

# ══════════════════════════════════════════════════════════════════════
# 第三部分：静默回退五条规则（解析 layers_info.json + layers.json）
# ══════════════════════════════════════════════════════════════════════
#   R1 子图数 == 1                              （ORT 用 TRT EP 时尤其要看）
#   R2 FP32 层耗时占比 < 10%
#   R3 无 Convolution/MatMul 落在 FP32
#   R4 Reformat 层耗时占比 < 5%                 ← 它不在你的 ONNX 里，是构建器插的
#   R5 (Host Latency - GPU Compute) / GPU Compute < 25%

# ══════════════════════════════════════════════════════════════════════
# 第四部分：发布验收 13 项（每一项对应一个真实事故类型）
# ══════════════════════════════════════════════════════════════════════
#   01 整体 mAP 掉幅 <= 1.0
#   02 **每一个像素尺寸桶**的 AP 掉幅 <= 2.0     ← 平均会掩盖小目标崩塌
#   03 安全关键类召回 >= baseline - 1%
#   04 端到端 p99 <= 预算；p99.9 <= 预算 x 1.1   （>= 10000 帧真实序列）
#   05 **最长连续超时段 <= 2 帧**                 ← 最常被漏掉
#   06 显存峰值 <= 分配预算的 80%
#   07 **>= 30 min 连续跑，分段 p99 漂移 <= 10%，RSS 斜率 ≈ 0**   ← 进夜间 CI
#   08 多硬件/多驱动一致性：框匹配率 >= 99.9%
#   09 与 Python 参考实现的**逐阶段对拍 8 个阶段全过**（模块 04）
#   10 engine 指纹校验（GPU 型号+驱动+TRT 版本+ONNX 哈希），不匹配拒绝加载
#   11 冷启动（engine 反序列化 + warmup）<= 整车上电预算
#   12 **回退方案本身被测试过**：注入「加载失败/推理超时/输出异常」三种故障 ← 做成自动用例
#   13 可观测性：分阶段耗时、候选数、检出数、丢帧数全部打点
#
# 报告格式：每项输出 [实测值 / 门限 / 余量% / 环比]，不只是 pass/fail
#   余量趋势比单次判定更有价值 —— 连续几个版本 p99 稳定上涨，说明下一版就要撞墙

# ══════════════════════════════════════════════════════════════════════
# 第五部分：车端特有的坑（数据中心经验会骗你）
# ══════════════════════════════════════════════════════════════════════
#   · 批处理只在**多相机硬件同步**时合理；单相机 batch=4 要白等 100 ms
#   · 动态 batch 的三笔额外成本：构建时间、非 opt 档的 tactic 损耗、按 max 预留显存
#   · CUDA stream priority 不是硬实时保证；GPU kernel 默认不可抢占
#   · 用**时间片预算 + 提前设计好的降级路径**排期，而不是靠优先级
#   · 关键线程绑核 + SCHED_FIFO + isolcpus，压住 CPU 侧的调度抖动
#   · MPS / MIG 在车端 SoC 上通常不可用
#   · **任何延迟数字都必须声明功耗模式**；开发板 MAXN 测出的数不代表量产域控
'''
print(RECIPE)
for token in ['power_mode', 'separateProfileRun', 'useCudaGraph', 'Reformat',
              '最长连续超时段', '分段 p99', '逐阶段对拍', '硬件同步', 'SCHED_FIFO']:
    assert token in RECIPE, token
print('✅ 胶囊覆盖：benchmark 元数据 / trtexec 姿势 / 静默回退五规则 / 验收 13 项 / 车端专有坑')"""),

    md("""### 小结

- **测延迟有七宗罪，最贵的两条是「没 warmup」和「没同步」。** 不丢 warmup 会高估 26%；
  不同步测出的是 CPU 提交时间，会得到 22000 FPS 这种荒谬值。
  **报 FPS 必须声明口径**：GPU Compute / Enqueue / Host Latency / Throughput 是四个不同的数。
- **p99 需要样本量。** $\\sigma_{\\text{rank}}=\\sqrt{np(1-p)}$：$n=100$ 时只有 1 个样本超过 p99，
  你报的「p99」就是最大值；**10 000 帧是下限**（30 FPS 下 5.5 分钟），估 p99.9 要 10 万帧。
- **「p99 达标」= 每 3.3 秒丢一帧。** 而且必须同时报**最长连续超时段**——
  同一组延迟值重排一下顺序，所有分位数完全相同，最长连续超时段却能从 2 帧变成 2000 帧
  （连续 67 秒失明）。独立抖动治调度，成簇超时治热与抢占。
- **推理往往只占一半。** 分解后：预处理 3.20 → 0.35、后处理 2.10 → 0.35、
  H2D 传 uint8 降 4 倍、D2H 只传框降 476 倍 —— **端到端省 37%，模型一个字节没改**，
  是换小模型（省 12% 且掉 1.5 mAP）的 3 倍收益。**新手换 backbone，老手先量拷贝。**
- **Roofline 的脊点是 205 FLOP/Byte，绝大多数算子够不着。**
  **5×5 depthwise 的实际耗时是 FLOPs 预测的 16.5 倍**——FLOPs 不是延迟的好代理。
  融合省的不是计算而是「中间结果的一趟往返访存」（Conv+BN+SiLU 省 26%，FLOPs 只减 0.13%）。
  第三种瓶颈是并行度不足：200 层的 kernel 启动开销就占 8.2 ms 模型的 15%，用 CUDA Graph 治。
- **静默回退可以五条规则自动查**：子图数、FP32 耗时占比、计算密集层的精度、Reformat 占比、
  Host−GPU 差额。**注意健康与回退两个 engine 的 GPU Compute Time 几乎一样**——
  只看 GPU 时间会得出「engine 没问题」的错误结论。
- **车端三重约束**：功耗模式（不声明就是无效数字）、热降频（第 1 分钟 p99 9.2 ms，
  第 30 分钟 12.7 ms，**漂移 38%**，整段 p99 会把它平均掉 → 必须报分段 p99）、
  多任务抢占（GPU kernel 不可抢占 → 靠时间片预算 + 提前设计好的降级路径，不是靠优先级）。
- **13 项验收门禁，最容易被跳过的是第 7 项（长时稳定性，因为慢）和第 12 项（回退方案测试，
  因为"应该不会发生"）——而它们正是事故的两大来源。** 报告要输出余量与环比，
  因为门禁只能挡住已经越界的，**趋势才能提前告诉你要撞墙**。

至此 C60 全课结束：一致性（m01–m04）+ 性能（m05）= 一个能上车、能验收、能追溯的推理系统。
下一站建议：**C61 · 检测工程实战与面试实务** —— 把这九门课组织成能讲十分钟的深度故事。"""),
]
