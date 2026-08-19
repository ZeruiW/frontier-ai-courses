# -*- coding: utf-8 -*-
"""C53 模块 05 · 延迟-精度权衡与实时检测器选型。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–04（尤其 04 的 NMS 耗时分析）；C27（量化）与 C60（TensorRT）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_benchmark.ipynb（纯 numpy，延迟模型 + 帕累托 + 选型脚本）'),
    ("核心参考", "RT-DETR / RTMDet / YOLOv8-v10 的论文附录测速口径 · TensorRT Developer Guide · trtexec"),
    ("预计时长", "读 70 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("budget", "先算清预算：33 ms 是帧周期，不是延迟预算", "".join([
        P("「车端要 30 FPS」这句话被无数次误读成「检测模型有 33 ms 可用」。<strong>这两件事完全不同，而且差了一个数量级。</strong>"),
        DUAL(
            "<strong>帧周期</strong>（frame period）说的是<em>吞吐</em>：每 33.3 ms 必须消化掉一帧，否则要么丢帧、要么排队积压。它约束的是「平均每帧能花多少算力」。<strong>反应延迟</strong>（end-to-end latency）说的是<em>从光子打到传感器，到刹车片开始动</em>，中间隔了多久。它约束的是安全。<em>一个流水线系统完全可以做到「吞吐 30 FPS 但延迟 150 ms」——每一级都在同时处理不同的帧</em>。",
            "所以两个约束要分别核算：吞吐决定「模型的单帧计算量上限」，延迟决定「整条链路的串行深度上限」。<strong>而检测模型拿到的既不是 33 ms，也不是 145 ms，而是「感知总预算 ÷ 感知任务数」之后剩下的那一小块。</strong>更麻烦的是，感知任务共享同一颗 SoC 的推理单元，多数量产系统里它们是<em>分时串行</em>的（因为要保证每个任务的 WCET 可界定），所以 TSR 拿到的是一个真正意义上的固定时隙。",
        ),
        ASCII("""一帧图像从「光子」到「刹车片」的时间账（量级示意，单位 ms）

 曝光+读出   ISP    传输 ┃        感知（所有任务共享 SoC）        ┃ 融合  预测   规划     控制+执行
 ├───12───┤├──8──┤├─2─┤┃├─────────────45─────────────┤┃├─8─┤├─10─┤├──20──┤├─────40─────┤
 0        12    20   22 ┃22                            67┃67   75    85     105        145

 └──────────────────── 端到端反应延迟 ≈ 145 ms ────────────────────────────────────────┘
                    @120 km/h（= 33.3 m/s）→ 车在这段时间里已经开出 **4.83 米**

 而「感知」这 45 ms 里，TSR 只是众多任务之一：
   ┌────────────┬──────────┬────────┬────────┬────────┬──────┐
   │ BEV 3D 检测 │ 占用栅格  │ 车道线  │ 红绿灯  │ **TSR**│ 其他 │
   │     18     │    10    │   5    │   4    │  **6** │  2   │
   └────────────┴──────────┴────────┴────────┴────────┴──────┘
                                                  ↑
        「30 FPS = 33.3 ms」→ TSR 的真实预算是 **6 ms**，不是 33 ms"""),
        MATH("d_{\\text{travel}} \\;=\\; v \\cdot t_{\\text{lat}} \\;=\\; \\frac{120}{3.6}\\,\\text{m/s} \\times 0.145\\,\\text{s} \\;=\\; 4.83\\ \\text{m} \\qquad\\Longrightarrow\\qquad \\text{每省 10 ms} \\;=\\; \\text{少开 0.33 m}"),
        P("这个换算是你在需求评审里唯一需要的工具：<strong>把毫秒翻译成米</strong>。「把 TSR 从 8 ms 优化到 6 ms」听起来微不足道，翻译成「120 km/h 下决策提前 0.067 米」也确实微不足道——<em>那就说明这个优化不值得做，应该把工程时间花在别处</em>。反过来，「感知总预算从 45 ms 涨到 65 ms」= 多开 0.67 米，在跟车场景里就可能是要不要追尾的差别。"),
        CALLOUT("warn", "<p><strong>一个必须提前问清楚的问题：你的延迟预算是「分配给你的」还是「你占用的」？</strong>如果 TSR 是和其他任务串行分时的，你超时会直接推迟后面所有任务；如果是独立算力单元，你超时只影响自己。<em>这两种架构下，「p99 超预算 20%」的后果完全不同</em>——前者是全系统级联抖动，后者是本任务偶发丢帧。<strong>在没搞清楚这一点之前，任何「我的模型跑 8 ms」的陈述都是没有意义的。</strong></p>", "先问架构，再报数字"),
    ])),

    # ============================================================== 2
    ("pipeline", "端到端延迟的完整拆解：模型推理只是其中一段", "".join([
        P("绝大多数人报的「延迟」只有 $T_{\\text{infer}}$ 那一项。真实系统里它经常连一半都不到。"),
        MATH("T_{\\text{e2e}} \\;=\\; T_{\\text{pre}} \\;+\\; T_{\\text{H2D}} \\;+\\; T_{\\text{infer}} \\;+\\; T_{\\text{decode}} \\;+\\; \\underbrace{T_{\\text{NMS}}(N,K)}_{\\text{依赖场景}} \\;+\\; T_{\\text{D2H}} \\;+\\; \\underbrace{T_{\\text{track}}(K)}_{\\text{依赖场景}}"),
        TABLE(["阶段", "做什么", "车端典型量级", "随什么增长", "常见的坑"], [
            ["<strong>预处理</strong>", "resize / letterbox / BGR→RGB / 归一化 / HWC→CHW", "0.5–5 ms", "输入分辨率（线性于像素数）", "<strong>CPU 上做 fp32 归一化是最大浪费</strong>；OpenCV 与训练端 resize 语义不一致（C60 模块 01）"],
            ["<strong>H2D 拷贝</strong>", "把张量从主机内存搬到设备内存", "0.3–2 ms", "字节数 ÷ PCIe 带宽", "<strong>传 fp32 比传 uint8 贵 4 倍</strong>；未用 pinned memory 会再慢一倍"],
            ["<strong>模型推理</strong>", "卷积 / attention 前向", "2–20 ms", "FLOPs、精度档、算子是否被融合", "算子回退到 CPU 导致「转了 TRT 但没变快」"],
            ["<strong>解码</strong>", "把输出张量变成候选框（sigmoid、anchor 解码、top-k）", "0.05–1 ms", "候选框数", "在 CPU 上遍历 8400 个 anchor 是真实事故"],
            ["<strong>NMS</strong>", "去重", "<strong>0.2–12 ms</strong>", "<strong>$O(NK)$，超线性</strong>", "见模块 04：这是唯一一个方差大到能毁掉 p99 的项"],
            ["<strong>D2H 拷贝</strong>", "把结果搬回主机", "0.02–0.3 ms", "输出大小", "同步点设错会把整条流水线串起来"],
            ["<strong>跟踪与关联</strong>", "IoU/匈牙利关联、状态机、多帧投票", "0.2–3 ms", "目标数", "常被忘记计入「感知延迟」，但它在预算里"],
        ]),
        H3("拷贝的账：一个能立刻省下 1.2 ms 的决定"),
        P("1920×1080×3 的图像，uint8 是 6.22 MB，fp32 是 24.9 MB。按 PCIe 有效带宽 16 GB/s 算："),
        CODE("""uint8 上传:  6,220,800 B / 16e9 B/s = 0.389 ms
fp32  上传: 24,883,200 B / 16e9 B/s = 1.555 ms       ← 贵 4 倍

正确做法: 主机端只传 uint8，**在 GPU 上做 归一化 / HWC→CHW / BGR→RGB**
          （这些都是访存受限的逐元素算子，GPU 上几乎免费）
六路相机: 0.389 × 6 = 2.33 ms  vs  1.555 × 6 = 9.33 ms   ← 差 7 ms，比换模型还多"""),
        DUAL(
            "为什么这个坑这么普遍？因为在 PyTorch 里 <code>transforms.ToTensor()</code> + <code>Normalize()</code> 是默认写法，它们在 CPU 上把图变成 fp32 再 <code>.cuda()</code>。<em>训练时无所谓（DataLoader 有多个 worker 在并行预取，而且 GPU 在算上一个 batch）；推理时是串行的，这 1.2 ms 直接进 p99。</em>",
            "更完整的做法是把整个预处理搬到设备侧：uint8 图像上传 → GPU kernel 完成 resize + letterbox + 归一化 + 通道重排。NVIDIA 的 DALI/CV-CUDA、或直接写一个 CUDA kernel 都行。<strong>但代价是训练-部署一致性的风险上升</strong>——GPU resize 的插值实现与 OpenCV 未必逐像素一致，而这类差异能让 mAP 掉几个点（C60 模块 01 的主题）。<em>所以正确的顺序是：先建立预处理对拍工具，再做设备侧预处理，而不是反过来。</em>",
        ),
        CALLOUT("intuition", "本节的可迁移结论：<strong>报延迟时永远报「端到端」，并且把分解表一起给出。</strong>只报模型前向时间，在任何一个做过量产的人面前都会被追问到底。<em>而分解表本身就是优化的路线图——你会经常发现最大的一块不是模型。</em>"),
    ])),

    # ============================================================== 3
    ("fps-lies", "为什么论文的 FPS 不可信：六个变量", "".join([
        P("论文里那个 FPS 是一个<strong>没有单位定义的数</strong>。同一个模型、同一份权重，把下面六个变量各拨一档，报出来的数字可以差 10 倍以上——而且每一档都不算造假，只是口径不同。"),
        TABLE(["变量", "论文常用口径", "车端真实口径", "影响倍数", "怎么识别"], [
            ["<strong>① batch size</strong>", "batch=32 报吞吐，FPS = batch ÷ 总时间", "<strong>batch=1</strong>（一帧来了就要处理）", "<strong>1.3–3×</strong>", "论文只给 FPS 不给 ms，多半是吞吐；看附录的 <code>--batch</code>"],
            ["<strong>② 含不含 NMS</strong>", "常常只计网络前向", "必须含", "1.1–1.5×（密集场景更多）", "看是否写 “end-to-end” / “including post-processing”"],
            ["<strong>③ 含不含预处理与拷贝</strong>", "几乎从不含", "必须含", "1.2–2×", "看是否从「图像文件」还是从「已在显存里的张量」开始计时"],
            ["<strong>④ 精度档</strong>", "TensorRT <strong>FP16</strong>（有时不写）", "FP16 或 INT8", "FP32→FP16 约 2–3×，FP16→INT8 约 1.3–2×", "没写精度的 FPS 基本可以认为是 FP16"],
            ["<strong>⑤ 什么卡</strong>", "T4 / V100 / A100 / 3090，各不相同", "车端 SoC（Orin / 自研 NPU）", "<strong>2–5×</strong>", "跨代际的卡对比毫无意义；同代不同卡也差 2 倍"],
            ["<strong>⑥ 输入分辨率</strong>", "640×640（COCO 惯例）", "<strong>TSR 常需 1280 以上</strong>", "<strong>3–4×</strong>", "看 <code>imgsz</code> / <code>test_size</code>"],
        ]),
        P("再加一个隐形的第七项：<strong>测量方法</strong>（有没有 warmup、有没有同步、报均值还是 p99、GPU 有没有锁频）——下一节专门讲。"),
        H3("一次完整的折算：108 FPS 变成 14.8 FPS"),
        P("以 RT-DETR-R50 的论文口径（T4 + TensorRT FP16 + batch=1 + 640×640，<strong>只计网络前向</strong>，约 108 FPS = 9.26 ms）为起点，逐项折算到一个 TSR 车端场景："),
        CODE("""  论文口径                                    9.26 ms   (108.0 FPS)
  × 1.90  T4 → 车端 SoC（同精度算力约 0.53×）  17.59 ms
  × 3.40  输入 640 → 1280（TSR 的小目标必需）   59.81 ms
  + 5.40  预处理（1280 下的 resize/归一化）     65.21 ms
  + 1.60  H2D + D2H 拷贝                        66.81 ms
  + 0.80  跟踪与时序关联                        67.61 ms
  ────────────────────────────────────────────────────────
  车端端到端                                   67.61 ms   ( 14.8 FPS)   **差 7.3 倍**"""),
        DUAL(
            "注意这里<strong>没有任何一步是「论文夸大了」</strong>。论文报的 108 FPS 在它自己的口径下是真的、可复现的。差距全部来自「口径不同」——而口径的差异，是<em>你的系统约束</em>造成的，不是作者的问题。<strong>所以正确的心态不是「论文数字不能信」，而是「论文数字必须先折算到你的口径才能比较」</strong>。",
            "这也解释了一个常见的困惑：为什么按论文选了「延迟最低」的模型，上车后反而是另一个模型更快？因为六个变量对不同模型的<strong>敏感度不同</strong>。举例：<em>①分辨率翻倍时，密集预测器的 NMS 代价涨得比推理还快（候选框数正比于像素数），而 RT-DETR 的 query 数固定不变；②INT8 量化时，纯卷积模型几乎不掉点，含 attention 的模型可能掉 1–2 AP 要上混合精度，于是实际能用的精度档不同；③batch=1 时，参数量大但 FLOPs 低的模型（深而窄）比 FLOPs 高但并行度好的模型（浅而宽）吃亏更多，因为 kernel launch 开销占比上升</em>。<strong>结论：排名会随口径改变，所以必须在你自己的口径下重测，不能照抄论文的相对顺序。</strong>",
        ),
        CALLOUT("danger", "<p><strong>面试里最容易翻车的一句话：「YOLOv8-L 是 XX FPS，RT-DETR-R50 是 108 FPS，所以后者更快」。</strong>只要面试官问一句「这两个数是同一口径吗」，你就得当场承认不知道。<em>正确的答法是把口径先说出来：「论文里 RT-DETR 报的是 T4 + TRT FP16 + batch=1 + 640 且不含预处理；YOLOv8 那个数如果是含 NMS 的端到端，两者不可直接比。我会把两个模型在同一台机器、同一份预处理代码、同一 batch、同一精度下重测，报 p50 和 p99 两个数。」</em><strong>这句话本身就是答案的主体——面试官考的是「你知不知道要控制变量」，而不是那两个数字。</strong></p>", "「谁更快」是一个关于口径的问题"),
    ])),

    # ============================================================== 4
    ("measure", "怎么正确地测：五条纪律", "".join([
        P("测延迟比想象的容易做错。下面五条，每一条都对应一个能让结论反转的真实错误。"),
        OL([
            "<strong>必须 warmup 并丢弃。</strong>前几十次调用包含：kernel autotune、显存分配、cache 冷启动、GPU 从低频升到 boost 频率。<em>不丢弃 warmup，200 次循环测出来的均值能比稳态高 20%。</em>",
            "<strong>必须显式同步。</strong>GPU 调用是异步的。<code>t0=time(); model(x); t1=time()</code> 测的是<em>kernel launch 的时间</em>（约 0.15 ms），不是执行时间。<strong>不同步能测出 60 倍的假加速</strong>——这个错误在博客和 issue 里到处都是。正确做法是每次计时前后都 <code>synchronize()</code>，或用 CUDA event。",
            "<strong>报分布，不报均值。</strong>延迟分布是右偏长尾的（抢占、DVFS、内存竞争、NMS 的场景依赖）。<em>均值被尾巴拉高但又低于尾巴，两头不靠</em>。车端安全关心的是 <strong>p99</strong>（甚至 p99.9），因为「100 帧里有 1 帧超时」在 30 FPS 下就是<em>每 3 秒一次</em>。",
            "<strong>测够长，并覆盖热态。</strong>短测试（几秒）跑在 boost 频率上；持续满负载几分钟后 SoC 降频、温度上来，稳态延迟可能高 10–20%。<strong>「实验室 8 ms，车上跑半小时后 10 ms」几乎总是这个原因。</strong>",
            "<strong>用真实的输入分布，不要用同一张图跑 1000 次。</strong>同一张图会让 cache 命中率异常高，而且完全测不出 NMS 的场景依赖。<em>要用一组覆盖「稀疏高速 / 密集路口 / 极端杂波」的真实帧。</em>",
        ]),
        CODE("""# ❌ 三个错误同时犯：没 warmup、没同步、只报均值
t0 = time.time()
for _ in range(100): out = model(x)
print(100 / (time.time() - t0), "FPS")        # 这个数基本是编的

# ✅ 正确姿势
for _ in range(50): model(x)                   # ① warmup（丢弃）
torch.cuda.synchronize()
ts = []
for _ in range(1000):                          # ⑤ 用不同的真实帧，不是同一张
    x = next(real_frames)
    torch.cuda.synchronize(); t0 = time.perf_counter()
    out = model(x)
    torch.cuda.synchronize()                   # ② 同步
    ts.append((time.perf_counter() - t0) * 1e3)
p50, p90, p99, p999 = np.percentile(ts, [50, 90, 99, 99.9])   # ③ 报分布
print(f"p50={p50:.2f} p90={p90:.2f} p99={p99:.2f} p99.9={p999:.2f} ms")

# 补充：trtexec 已经把这些做对了，优先用它作为交叉验证
#   trtexec --loadEngine=m.engine --iterations=2000 --avgRuns=1 --percentile=99 \\
#           --useCudaGraph --noDataTransfers=false --dumpProfile"""),
        DUAL(
            "第 3 条值得再算一次账。假设 p50=8 ms、p99=13 ms、预算 12 ms。<strong>按均值看，你「有 4 ms 余量」；按 p99 看，你已经超预算了。</strong>而 p99 意味着 30 FPS 下每 3.3 秒就有一帧超时——如果 TSR 与其他任务串行共享 SoC，这一帧的超时会推迟后面所有任务，产生级联抖动。<em>「偶尔慢一点」在实时系统里不是「偶尔」，是一个可以按秒数出来的周期性事件。</em>",
            "更严格地说，实时系统关心的是 <span class=\"term\">WCET</span>（worst-case execution time）而不是任何分位数——<strong>p99 也不是上界</strong>，它只是一个「99% 的情况下不会超过」的经验统计量。$p_{99}$ 之上还有 $p_{99.9}$ 和真正的 max，而后者可能被一次页错误、一次驱动重试、一次热节流拉到 3 倍。<em>可以做的事有三件：①把数据依赖项（NMS）删掉或封顶，让 WCET 可以被结构性地界定；②给整个任务加超时保护与降级路径（比如模块 04 讲的 decoder 层数动态下调）；③在验收里明确写出 p99 与 max 两个门槛，而不是只写均值。</em>",
        ),
        CALLOUT("warn", "还有一个隐形变量：<strong>同一份 engine 在不同驱动 / TensorRT 版本 / GPU 频率策略下的延迟不同</strong>。所以延迟数字必须和「硬件型号 + 驱动版本 + TRT 版本 + 频率模式（是否锁频）」一起记录，否则三个月后没人能复现。<em>这与 C60 讲的「engine 与硬件绑定」是同一件事的两面：绑定意味着结果不可跨环境比较。</em>"),
    ])),

    # ============================================================== 5
    ("precision", "精度档的真实数量级：FP16 几乎白送，INT8 要算总账", "".join([
        P("换精度是延迟优化里性价比最高的一步，但它的收益经常被误报，代价也经常被误算。"),
        TABLE(["精度档", "相对 FP32 延迟", "典型 AP 变化", "需要什么", "对检测器的特殊风险"], [
            ["<strong>FP32</strong>", "1.00×", "基线", "无", "—"],
            ["<strong>FP16</strong>", "<strong>约 0.35–0.50×</strong>", "≈ 0（−0.1 以内）", "Tensor Core 硬件；检查激活是否溢出（fp16 上限 65504）", "极少数归一化中间量溢出 → inf/nan；用极端输入验证"],
            ["<strong>INT8 (PTQ)</strong>", "约 0.22–0.35×", "−0.5 ~ −2.0 AP", "<strong>几百到上千张有代表性的校准集</strong>", "<strong>回归头比分类头更敏感；小目标掉得更多；attention/softmax 掉得更多</strong>"],
            ["<strong>INT8 (QAT)</strong>", "同 PTQ", "−0.2 ~ −0.6 AP", "重新训练（几个 GPU-天）", "工程成本高，只在 PTQ 掉点无法用混合精度救回时才做"],
            ["混合精度（敏感层保 FP16）", "约 0.28–0.42×", "−0.2 ~ −0.8 AP", "逐层敏感度分析", "分区变多可能反而变慢，要实测"],
        ]),
        DUAL(
            "<strong>FP16 基本是白送的</strong>：在有 Tensor Core 的硬件上延迟降到 40% 左右，AP 几乎不动，不需要任何数据。<em>如果你的部署还在跑 FP32，这是第一件该做的事，而且不需要开会讨论。</em>唯一要做的验证是用极端输入（超大幅值、超长曝光的过曝图）跑一遍看有没有 inf/nan——这个问题在训练时被 loss scaling 掩盖，只在纯 FP16 推理时暴露。",
            "<strong>INT8 要算的是「总账」而不是「掉了多少 AP」。</strong>假设 FP16 下 RT-DETR-R50 是 12.0 ms / 53.1 AP，INT8 PTQ 变成 3.2 ms / 51.9 AP——掉 1.2 AP 看起来不小。但你省下了 8.8 ms，<em>这 8.8 ms 足够把模型从 R50 换成 R101（+1.2 AP），甚至还能把输入分辨率提一档</em>。<strong>所以正确的问法不是「INT8 掉多少点」，而是「在同一延迟预算下，INT8 的大模型 vs FP16 的小模型，谁的 AP 更高」</strong>——这正是下一节帕累托前沿要回答的问题。多数情况下答案是前者，尤其在 TSR 这种「提分辨率就直接见效」的小目标任务上。",
        ),
        CALLOUT("danger", "<p><strong>INT8 校准集是最容易毁掉一切的一步。</strong>它的作用是统计每层激活的数值范围。<em>用训练集的前 500 张（很可能全是晴天白天的高速路段）做校准，会得到一组只对晴天白天正确的量化范围</em>——离线评测（同分布）看不出问题，上车遇到夜间隧道口、雨天逆光就大幅掉点。<strong>校准集必须是线上分布的一个有代表性的小样本：覆盖夜间、逆光、雨雾、隧道出入口、以及各类标志的长尾类别，几百到上千张，且预处理必须与线上完全一致。</strong>这是 C60 模块 03 的核心内容，也是「离线 0.82、车上像 0.6」这类故事的常见原因之一。</p>", "校准集分布不匹配 = 静默掉点"),
        CALLOUT("warn", "另一个必须实测而不能推断的点：<strong>「更少的 FLOPs」不等于「更低的延迟」</strong>。depthwise 卷积、极窄的通道数、大量小算子都是访存受限的，FLOPs 很低但延迟不降；相反，宽而浅的结构 FLOPs 高却能把 Tensor Core 喂饱。<em>所以模型选型的排序必须用「实测延迟」，FLOPs 只能用来做粗筛。</em>"),
    ])),

    # ============================================================== 6
    ("pareto", "帕累托前沿：选型的正确姿势是「同延迟比 AP」", "".join([
        P("有了同口径的实测数据后，选型就变成一个二维问题：<strong>延迟越低越好、AP 越高越好</strong>。一个模型如果存在另一个模型「不更慢<em>且</em>不更差」，它就被<span class=\"term\">支配</span>（dominated），可以直接从候选集里删掉。剩下的构成<span class=\"term\">帕累托前沿</span>（Pareto front）。"),
        MATH("i \\ \\text{被支配} \\iff \\exists\\, j \\neq i:\\ t_j \\le t_i \\ \\wedge\\ \\text{AP}_j \\ge \\text{AP}_i \\ \\wedge\\ (t_j < t_i \\ \\vee\\ \\text{AP}_j > \\text{AP}_i)"),
        ASCII("""AP
 55 ┤
 54 ┤                        ●             ●               ○
    │                    D-FINE-L        R-101           v8-X
 53 ┤                     ●        ○
    │                    R-50    v8-L
 52 ┤             ●
    │          D-FINE-M
 51 ┤               ○
    │           RTMDet-L
 50 ┤                 ○
    │              v8-M
 49 ┤        ●  ○
    │  RTMDet-M R-34
 48 ┤    ●
    │ D-FINE-S
 47 ┤
 46 ┤   ●
    │  R-18
 45 ┤       ○
    │     v8-S
 44 ┤●
    │RTMDet-S
    └┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴──►
     4    5    6    7    8    9   10   11   12   13   14   15  16
                        端到端延迟 ms（同口径：batch=1 / FP16 / 含 NMS 1.4 ms）

  ● 在帕累托前沿上（8 个）    ○ 被支配（6 个）：存在一个「不更慢且不更差」的替代品"""),
        H3("两条容易搞反的规则"),
        UL([
            "<strong>同延迟比 AP，而不是同 AP 比延迟。</strong>因为你的延迟预算是系统给的<em>硬约束</em>，AP 是你要最大化的目标。「达到 53 AP 谁最快」是个假问题——你根本不需要恰好 53 AP，你需要「在 9 ms 内 AP 最高」。",
            "<strong>前沿是口径的函数，不是模型的固有属性。</strong>notebook 会演示：只把 NMS 的计入方式从 1.4 ms 改成 0.5 ms（比如上了 EfficientNMS plugin 并做了 top-k 截断），<em>前沿的成员立刻从 8 个变成 10 个</em>，YOLOv8-S 和 RTMDet-L 重新进入。<strong>所以「谁在前沿上」这个结论必须和口径一起被引用。</strong>",
        ]),
        DUAL(
            "被支配 ≠ 没用。一个被支配的模型可能在<em>其他维度</em>上更好：工具链成熟、算子全支持、量化友好、团队熟悉、社区活跃。<strong>帕累托前沿只是筛掉「在这两个维度上都没有理由选它」的候选，它不是最终答案，是候选集的第一道过滤。</strong>",
            "而且这张二维图隐藏了一个致命简化：<strong>AP 是 COCO 的 AP</strong>。TSR 关心的是 8–30 像素目标的 AP，两者的排序可能完全不同。<em>一个在 COCO 上被支配的模型，加上 P2 层与高分辨率输入后，在「小目标 AP vs 延迟」这张图上可能反而在前沿上</em>。<strong>所以正确的流程是：先定义你自己的评测指标（分尺寸桶的 AP、关键类别的召回），在你自己的数据上重测，再画前沿。照抄 COCO 的前沿是最常见的选型错误。</strong>",
        ),
        CALLOUT("intuition", "把选型压成三步：<strong>①用硬约束（p99 预算、显存上限、算子支持）过滤掉不可行的；②在可行集里按你自己的指标画帕累托前沿；③在前沿上按工程维度（可维护性、量化友好、多档速度）加权排序。</strong><em>顺序不能反——先加权打分再看约束，会得到一个分数很高但根本上不了车的方案。</em>"),
    ])),

    # ============================================================== 7
    ("stability", "延迟稳定性：p99 才是决定能不能上车的那个数", "".join([
        P("这一节把模块 04 的结论落到可操作的层面。"),
        P("同一个 YOLO 式检测器，在一段真实路测里的延迟分布是<strong>右偏长尾</strong>的，因为 $T_{\\text{NMS}}$ 与 $T_{\\text{track}}$ 都依赖目标数，而目标数本身是重尾分布（多数帧只有几个标志，少数城市路口帧有几十个）。notebook 会用同一套延迟模型跑出这样一组数（量级示意）："),
        TABLE(["方案", "p50", "p90", "p99", "p99 − p50", "结论"], [
            ["YOLO 式（含 NMS）", "<strong>7.21 ms</strong>", "8.31 ms", "12.28 ms", "<strong>5.07 ms</strong>", "中位数最快，但尾巴很长"],
            ["RT-DETR 式（无 NMS）", "8.97 ms", "9.33 ms", "10.18 ms", "<strong>1.21 ms</strong>", "中位数慢 1.8 ms，<strong>p99 反而快 2.1 ms</strong>"],
            ["YOLO + top-k 封顶(1000)", "7.21 ms", "7.82 ms", "<strong>9.02 ms</strong>", "1.81 ms", "两头都好，<strong>但约 35% 的帧被截断</strong>"],
        ]),
        P("<strong>三行读出三个不同的结论，取决于你看哪一列。</strong>按 p50 选 → YOLO；按 p99 选 → RT-DETR；按「p99 且愿意承担密集场景召回风险」选 → YOLO + 封顶。<em>而「按均值选」会给出和「按 p50 选」一样的答案，然后上车在城市路口掉帧。</em>"),
        H3("给 NMS 加硬上限：一个实用但有代价的折中"),
        P("如果因为其他原因（工具链、小目标、算力）必须用密集预测器，有一个标准手段可以把 WCET 钉死：<strong>在进 NMS 之前，先按 score 取 top-$N_{\\max}$</strong>（典型 300–1000）。这样 $T_{\\text{NMS}}$ 的最坏值变成一个可计算的常数。"),
        DUAL(
            "代价是：<strong>在候选框数超过 $N_{\\max}$ 的帧里，被截掉的都是低分候选</strong>——而低分候选恰恰主要是<em>远处的小目标</em>和<em>部分遮挡的目标</em>。也就是说，这个优化在最需要召回的场景里牺牲召回。TSR 场景里这尤其危险：一块 80 米外刚进视野的限速牌，分数天然低，在拥挤路口很可能就是被截掉的那一个。",
            "所以封顶必须配三件事：<em>①统计你的数据里「候选框数 > $N_{\\max}$」的帧占比（notebook 里是 34.8%，这些帧平均被截掉 33% 的候选、最坏的一帧被截掉 88%），这个数太高说明 $N_{\\max}$ 设小了；②在<strong>分场景评测</strong>里专门建一个「密集路口」切片，对比封顶前后的召回；③把截断事件打点上报，作为线上监控指标</em>。<strong>「加了个 top-k 就上线」而不做②，是一个会在几个月后以「某些路口漏检」的形式浮出水面的技术债。</strong>",
        ),
        CALLOUT("warn", "<p>还有一个更隐蔽的数据依赖项经常被忽略：<strong>跟踪与关联</strong>。匈牙利关联是 $O(n^3)$，IoU 矩阵是 $O(n^2)$，目标多时同样会涨。<em>notebook 的模型里即使删掉 NMS，p99 − p50 仍有 1.2 ms，全部来自跟踪</em>。<strong>所以「无 NMS = 延迟恒定」是一个近似说法</strong>——严格地说是「删掉了方差最大的那一项，剩下的项方差小一个数量级」。面试里能主动补这一句，说明你是自己测过而不是背的。</p>", "无 NMS ≠ 延迟完全恒定"),
    ])),

    # ============================================================== 8
    ("tsr-choice", "为 TSR 选型的完整推理链（含精度之外的工程指标）", "".join([
        P("把前面所有东西串起来，走一遍真实的选型推理。<strong>这一节的结构本身就是一个可以在面试里复述的系统设计答案骨架。</strong>"),
        H3("第一步：把场景需求翻译成约束"),
        TABLE(["TSR 的场景特征", "翻译成什么约束", "对选型的直接影响"], [
            ["目标极小（80 m 外的限速牌约 10–20 px）", "输入分辨率 ≥ 1280；需要 stride 8 甚至 stride 4 的特征", "<strong>计算量按分辨率平方涨</strong> → 挤压模型规模的空间"],
            ["类别多且长尾（含限速 5–120 的变体、组合牌）", "分类头大；或采用两级架构解耦", "端到端多类检测器的类别数上升会抬高 NMS 的 $N$（class-wise NMS）"],
            ["延迟预算紧（共享 SoC，约 6 ms）", "端到端 <strong>p99</strong> ≤ 6 ms（不是 p50）", "直接砍掉一半候选；<strong>逼你必须上 INT8 或降分辨率</strong>"],
            ["输出必须稳定（时序融合、迟滞状态机在下游）", "p99 − p50 要小；帧间抖动会污染跟踪", "偏好无 NMS，或必须给 NMS 封顶"],
            ["多硬件平台（高中低三配车型）", "一份权重覆盖多档速度，或接受多次训练", "<strong>RT-DETR 系的 decoder 层数可调是实打实的优势</strong>"],
            ["功能安全要求", "WCET 可界定；要有优雅降级路径", "数据依赖项必须可封顶；要能动态降精度换延迟"],
        ]),
        H3("第二步：精度之外的工程指标（这些常常才是决定因素）"),
        TABLE(["指标", "为什么重要", "怎么量", "典型硬门槛"], [
            ["<strong>p99 延迟</strong>", "决定会不会周期性掉帧与级联抖动", "真实帧序列 + 长时间热态测量", "≤ 预算，且 max ≤ 1.5× 预算"],
            ["<strong>峰值显存</strong>", "SoC 显存由所有感知任务共享，超了直接 OOM", "<code>trtexec</code> 报告 + 运行时峰值", "硬上限，无商量余地"],
            ["<strong>engine 构建时间 × 硬件种类</strong>", "决定 CI 时长与发布节奏", "单次构建时间 × 平台数 × 精度档数", "构建 30 min × 3 平台 × 2 档 = 3 小时/次发布"],
            ["<strong>算子支持度 / 是否需要 plugin</strong>", "plugin 要跟着 TRT 版本维护，是长期负债", "<code>trtexec --verbose</code> 看子图数与 unsupported", "尽量为 0；每个 plugin 都要有 owner"],
            ["<strong>量化友好度</strong>", "决定能不能用 INT8，进而决定能用多大模型", "逐层敏感度分析 + PTQ 掉点", "PTQ 掉点 > 2 AP 就要重新评估"],
            ["<strong>收敛成本与数据需求</strong>", "决定迭代速度（一年能试多少次）", "达到目标 AP 所需 epoch × GPU-天", "DETR 系通常更贵"],
            ["<strong>可调试性</strong>", "出了 badcase 能不能定位到具体环节", "能否逐阶段 dump 中间结果", "端到端模型更难，要提前设计日志"],
            ["<strong>多档速度支持</strong>", "决定多平台的维护成本", "一份权重能出几档", "RT-DETR 原生支持；YOLO 需训多个尺寸"],
        ]),
        H3("第三步：过滤 → 打分 → 敏感性分析"),
        P("notebook 里实现了完整的决策脚本。它的关键设计是<strong>把「硬约束过滤」和「加权打分」严格分开</strong>，并且强制做敏感性分析。三个场景的结果："),
        TABLE(["场景", "硬约束", "权重", "胜出", "读法"], [
            ["S1 保守", "p99 ≤ 12 ms、显存 ≤ 1024 MB、<strong>不允许 plugin</strong>", "小目标 AP 0.45 / 余量 0.20 / 多档 0.20 / 工具链 0.15", "<strong>RT-DETRv2-S</strong>", "4 个候选被硬约束直接淘汰，根本轮不到打分"],
            ["S2 放开 plugin 与显存", "p99 ≤ 12 ms、显存 ≤ 1280 MB、允许 plugin", "同 S1", "<strong>RT-DETRv2-S</strong>（不变）", "放开约束没改变结论 → 说明这两条不是瓶颈"],
            ["S3 强调小目标", "同 S2", "<strong>小目标 AP 0.70</strong> / 余量 0.10 / 多档 0.10 / 工具链 0.10", "<strong>RT-DETR-R50</strong>", "<strong>权重一改结论就变</strong> → 说明决策对「多看重小目标」高度敏感"],
        ]),
        CALLOUT("intuition", "<p><strong>选型脚本的价值不是给出答案，而是把假设摆到台面上。</strong>S2 → S3 只改了权重，胜出者就换了——这说明真正需要开会讨论的不是「选哪个模型」，而是「小目标 AP 到底值多少权重」。<em>而这个问题只能用数据回答：统计你的数据集里各尺寸桶的目标占比，以及各桶漏检对应的安全后果。</em></p><p>面试里能把这层意思讲出来，比背出任何一个模型的 AP 都有价值：<strong>「我会先把硬约束列清楚，多数候选在这一步就被淘汰了；剩下的按我自己数据上的分桶指标画帕累托前沿；最后做权重敏感性分析，如果结论对某个权重特别敏感，那说明真正要确定的是那个权重而不是模型。」</strong></p>"),
        CALLOUT("danger", "<p>最后一个必须说的坑：<strong>不要在「论文口径的 COCO AP」上做 TSR 的选型决策。</strong>COCO 的 AP 由中大目标主导，而 TSR 的目标绝大多数落在 small 桶里，两者的模型排序可以完全不同。<em>正确的做法是先在自己的数据上按像素尺寸分桶评测（&lt;16 / 16–32 / 32–64 / &gt;64），拿到分桶 AP 之后再画前沿</em>。<strong>「用 COCO AP 排序 + 用论文 FPS 排序」这两个错误叠加起来，得出的选型结论可以和实测完全相反</strong>——而这两个错误都极其常见。</p>", "COCO AP + 论文 FPS = 双重误导"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>延迟基准的标准化仍未解决。</strong>目前每篇论文自定口径，导致跨论文的 FPS 不可比。MLPerf Inference 在服务器/边缘场景做了标准化（固定 batch、固定精度、报 p99 而非均值、含端到端后处理），<em>但检测领域的学术论文几乎不用它</em>。「实时检测器论文应该报哪些数字」是一个社区级的开放问题，也是读论文时必须自己补的功课。",
            "<strong>延迟感知的架构搜索（latency-aware NAS）。</strong>用实测延迟而非 FLOPs 作为搜索目标已经是共识（因为访存受限的算子 FLOPs 低但不快），但<em>延迟查找表与目标硬件强绑定</em>，换一颗 SoC 就要重建。「如何让延迟模型跨硬件泛化」尚无好解。",
            "<strong>动态推理与自适应计算。</strong>模块 04 讲的 decoder 层数可调是最粗粒度的一种；更细的做法（early exit、token 剪枝、区域自适应分辨率）能省更多，<em>但它们都把延迟重新变成输入的函数</em>——正好抵消了无 NMS 带来的可预测性。<strong>「如何在自适应计算与 WCET 可界定之间取得平衡」是实时感知的一个真问题</strong>，目前的工程答案是「自适应但有硬上界」。",
            "<strong>量化对检测器各部件的差异化影响。</strong>已知回归头比分类头敏感、小目标比大目标敏感、attention 比卷积敏感，但<em>缺少可预测的先验规则</em>，实践上仍靠逐层敏感度分析穷举。对 DETR 系（含 softmax、LayerNorm、可变形采样）的低比特量化尤其缺少成熟配方。",
            "<strong>共享 SoC 上的多任务调度。</strong>TSR 只是十几个感知任务之一，它们竞争同一份算力、显存带宽与内存。<em>单任务的 p99 测得再准，多任务并发下的实际 p99 也可能翻倍</em>。「多模型共存时的延迟保证」在学术界基本没人研究，但在量产里是天天要面对的问题。",
            "<strong>评测指标与下游行为的脱节。</strong>AP 涨了不等于路测体验变好；延迟降了不等于反应更快（可能被时序融合的窗口吃掉）。<em>「什么样的离线指标能预测闭环表现」是自动驾驶感知评测的核心开放问题</em>（C55 模块 05 与 C58 模块 05 会分别从安全评测与数据闭环的角度继续讨论）。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Zhao et al., <em>DETRs Beat YOLOs on Real-time Object Detection</em>（RT-DETR，CVPR 2024，arXiv:2304.08069）——重点看附录里对测速口径的说明（batch、精度、是否含后处理），这是学习「怎么报延迟」的正面样本。<strong>★</strong> Lyu et al., <em>RTMDet: An Empirical Study of Designing Real-Time Object Detectors</em>（arXiv:2212.07784）——它的延迟对比表明确写了测量条件，值得当模板。<strong>★</strong> NVIDIA, <em>TensorRT Developer Guide</em>——重点读 “Performance Best Practices”（warmup、CUDA graph、锁频、多流）与 “Working with INT8”（校准算法与校准集要求）两章；配合 <code>trtexec</code> 的 <code>--percentile</code>、<code>--dumpProfile</code>、<code>--useCudaGraph</code> 三个参数动手跑一遍。</p><p>配套背景：Reddi et al., <em>MLPerf Inference Benchmark</em>（ISCA 2020，标准化推理基准的设计原则，尤其是「为什么要报 p99 而不是均值」）；Wang et al., <em>YOLOv10: Real-Time End-to-End Object Detection</em>（NeurIPS 2024，无 NMS 的另一条路）；Peng et al., <em>D-FINE</em>（ICLR 2025）；Cai et al., <em>Once-for-All</em>（ICLR 2020，一份权重多档速度的另一种实现思路，可与模块 04 的 decoder 截断对照阅读）。相邻课程：模块 04（RT-DETR 与 NMS 方差）、C57 模块 05（TSR 小目标的物理推导与分桶评测）、C60 模块 02/03/05（TensorRT 构建、INT8 校准、性能剖析与 p99）、C61 模块 01（实验设计与「+0.3 算不算提升」）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 05 · 延迟-精度权衡与实时检测器选型（延迟预算 / 端到端模型 / FPS 折算 / 帕累托 / p99）

目标：把「选哪个检测器」从一个凭感觉的问题，变成一个**有硬约束、有可复算数字、有敏感性分析**的问题。

本 notebook 你会亲手实现：
1. **延迟预算分解器**：帧周期 vs 反应延迟，以及「毫秒 → 米」的换算
2. **端到端延迟模型**：预处理 / H2D / 推理 / 解码 / **NMS（依赖目标数）** / D2H / 跟踪
3. **论文 FPS 折算器**：把 108 FPS 一步步折算到车端的真实数字
4. **测量方法学**：warmup 的影响、异步计时的假加速、**p50/p90/p99/p99.9**、热态降频
5. **精度档的总账**：为什么「INT8 掉 1.2 AP」这个说法本身就是错的问法
6. **帕累托前沿筛选**，以及「改一个测量约定，前沿成员就变了」的演示
7. **延迟稳定性**：含 NMS / 无 NMS / top-k 封顶 三种方案的 p50-p99 对比
8. **TSR 选型决策脚本**：硬约束过滤 → 加权打分 → **权重敏感性分析**

> 心智模型：**延迟不是一个数，是一个分布；「谁更快」不是一个关于模型的问题，是一个关于口径的问题。**"""),

    md("""## 1 · 延迟预算：33 ms 是帧周期，不是预算"""),

    code("""import numpy as np, math

def frame_period_ms(fps):
    \"\"\"帧周期：吞吐约束。每 T 毫秒必须消化一帧，否则丢帧或积压。\"\"\"
    return 1000.0 / fps

def travel_m(speed_kmh, latency_ms):
    \"\"\"把毫秒翻译成米 —— 需求评审里唯一需要的换算工具。\"\"\"
    return speed_kmh / 3.6 * latency_ms / 1000.0

REACTION = [('相机曝光+读出', 12.0), ('ISP', 8.0), ('传输到 SoC', 2.0),
            ('感知（全部任务）', 45.0), ('融合与跟踪', 8.0),
            ('预测', 10.0), ('规划', 20.0), ('控制+执行器', 40.0)]

tot, acc = sum(v for _, v in REACTION), 0.0
print(f\"{'阶段':<18s} {'耗时 ms':>9s} {'累计 ms':>9s} {'累计行驶 m @120km/h':>21s}\")
for name, v in REACTION:
    acc += v
    print(f'{name:<18s} {v:>9.1f} {acc:>9.1f} {travel_m(120, acc):>21.2f}')

print(f'\\n帧周期 @30 FPS   = {frame_period_ms(30):>6.1f} ms   ← 吞吐约束')
print(f'端到端反应延迟   = {tot:>6.1f} ms   ← 安全约束（**是帧周期的 4.4 倍**）')
print(f'@120 km/h 车已开出 {travel_m(120, tot):.2f} m；每省 10 ms = 少开 {travel_m(120, 10):.2f} m')
assert abs(frame_period_ms(30) - 33.3333) < 1e-3
assert tot == 145.0
assert abs(travel_m(120, tot) - 4.8333) < 1e-3
assert abs(travel_m(120, 10) - 0.3333) < 1e-3
print('\\n✅ 吞吐与延迟是两个独立约束：流水线系统可以「30 FPS 吞吐 + 150 ms 延迟」。')"""),

    code("""# 感知的 45 ms 里，TSR 只是任务之一（多数量产系统分时串行，因为要保证各自 WCET 可界定）
PERCEPTION = [('BEV 3D 检测', 18.0), ('占用栅格', 10.0), ('车道线', 5.0),
              ('红绿灯', 4.0), ('TSR', 6.0), ('其他', 2.0)]
p_tot = sum(v for _, v in PERCEPTION)
print(f\"{'感知任务':<14s} {'时隙 ms':>9s} {'占感知预算':>11s}\")
for n, v in PERCEPTION:
    mark = '   ← 本课的主角' if n == 'TSR' else ''
    print(f'{n:<14s} {v:>9.1f} {v/p_tot:>10.1%}{mark}')
tsr = dict(PERCEPTION)['TSR']
print(f'\\n感知总预算 {p_tot:.0f} ms（与反应链里的 45 ms 对齐）')
print(f'**TSR 的真实预算 = {tsr:.0f} ms**，而不是帧周期的 {frame_period_ms(30):.1f} ms —— 差 {frame_period_ms(30)/tsr:.1f} 倍')
assert p_tot == 45.0
assert abs(tsr / p_tot - 0.13333) < 1e-4
assert tsr < frame_period_ms(30) / 5
print('\\n⚠️  在没搞清楚「你的预算是分配给你的还是你占用的」之前，')
print('    任何「我的模型跑 8 ms」的陈述都是没有意义的。')"""),

    md("""## 2 · 端到端延迟的完整拆解

只有 **NMS** 与 **跟踪** 依赖这一帧里有什么；其余各项在给定模型与分辨率后是常数。"""),

    code("""def pipeline(n_obj, model_ms=4.20, use_nms=True, topk=None,
             h=1080, w=1920, bytes_per=1, bw_gbps=16.0):
    \"\"\"端到端延迟模型。n_obj = 这一帧里的真实目标数。
       n_cand = 过 score 阈值后进 NMS 的候选框数（随目标数增长，上限 8400 个 anchor）。\"\"\"
    n_obj = int(n_obj)
    n_cand = min(300 + 60 * n_obj, 8400)
    if topk is not None:
        n_cand = min(n_cand, topk)                     # ← 硬上限：把 WCET 钉死
    st = {
        '预处理(resize/归一化)': 1.80,
        'H2D 拷贝':             h * w * 3 * bytes_per / (bw_gbps * 1e9) * 1e3,
        '模型推理':             model_ms,
        '解码(anchor/sigmoid)':  0.05 + 2e-5 * n_cand,
        'NMS':                  (3.5e-4 * n_cand + 1.0e-5 * n_cand * n_obj) if use_nms else 0.0,
        'D2H 拷贝':             0.06,
        '跟踪与关联':            0.20 + 0.02 * n_obj,
    }
    return st, sum(st.values()), n_cand

print(f\"{'阶段':<22s} {'稀疏场景 n=8':>13s} {'密集路口 n=140':>15s} {'涨幅':>8s}\")
s8, t8, c8 = pipeline(8)
s140, t140, c140 = pipeline(140)
for k in s8:
    ratio = s140[k] / s8[k] if s8[k] > 0 else float('inf')
    print(f'{k:<22s} {s8[k]:>13.3f} {s140[k]:>15.3f} {ratio:>7.1f}x')
print(f'{\"合计\":<22s} {t8:>13.3f} {t140:>15.3f} {t140/t8:>7.1f}x')
print(f'{\"候选框数 n_cand\":<22s} {c8:>13d} {c140:>15d}')
print(f'\\nNMS 占比: 稀疏场景 {s8[\"NMS\"]/t8:.1%}  ->  密集路口 **{s140[\"NMS\"]/t140:.1%}**')
assert t140 > 2.5 * t8
assert s8['NMS'] / t8 < 0.10 and s140['NMS'] / t140 > 0.50
print('✅ 同一个模型、同一块芯片，延迟差 3.4 倍 —— 差别全部来自「这一帧里有什么」。')"""),

    code("""# 拷贝的账：一个能立刻省下毫秒的决定
def copy_ms(h, w, c, bytes_per, bw_gbps=16.0):
    return h * w * c * bytes_per / (bw_gbps * 1e9) * 1e3

u8  = copy_ms(1080, 1920, 3, 1)
f32 = copy_ms(1080, 1920, 3, 4)
print(f'1920x1080x3  uint8 上传: {u8:.3f} ms   ({1080*1920*3:,} B)')
print(f'1920x1080x3  fp32  上传: {f32:.3f} ms   ({1080*1920*3*4:,} B)   <- 贵 {f32/u8:.0f} 倍')
print(f'\\n六路相机: uint8 {u8*6:.2f} ms  vs  fp32 {f32*6:.2f} ms   -> 白白多花 {(f32-u8)*6:.2f} ms')
assert abs(u8 - 0.38880) < 1e-5
assert abs(f32 / u8 - 4.0) < 1e-12
assert abs((f32 - u8) * 6 - 6.9984) < 1e-3
print('\\n⚠️  `transforms.ToTensor()+Normalize()` 在 CPU 上把图变成 fp32 再 .cuda()')
print('    —— 训练时无所谓（worker 并行预取），**推理时是串行的，直接进 p99**。')
print('✅ 正确做法：只传 uint8，归一化/通道重排/letterbox 都放到设备侧做。')
print('   代价：GPU 的 resize 插值与 OpenCV 未必逐像素一致 -> **先建对拍工具，再搬**（C60 模块 01）。')"""),

    md("""## 3 · 论文 FPS 的六个变量：为什么 108 FPS 会变成 14.8 FPS"""),

    code("""VARS = [
    ('① batch size',       'batch=32 报吞吐', 'batch=1',        1.70),
    ('② 含不含 NMS',        '常常不含',        '必须含',          1.20),
    ('③ 含不含预处理/拷贝',  '几乎从不含',      '必须含',          1.35),
    ('④ 精度档',            'TRT FP16(常不写)', 'FP16 或 INT8',   1.00),
    ('⑤ 什么卡',            'T4 / V100',       '车端 SoC',        2.60),
    ('⑥ 输入分辨率',        '640x640',         '1280+ (TSR 必需)', 3.40),
]
print(f\"{'变量':<20s} {'论文常用口径':<18s} {'车端真实口径':<16s} {'倍数':>6s}\")
compound = 1.0
for name, a, b, f in VARS:
    compound *= f
    print(f'{name:<20s} {a:<18s} {b:<16s} {f:>5.2f}x')
print(f'\\n六项复合 = {compound:.2f}x   ← 全部对不上时，论文数字与实测能差 **一个数量级以上**')
assert abs(compound - 24.34536) < 1e-4
assert compound > 20
print('\\n⚠️  这里没有一项是「论文造假」。论文数字在它自己的口径下是真的、可复现的。')
print('✅ 正确心态：**论文数字必须先折算到你的口径才能比较**，而不是「论文不可信」。')"""),

    code("""def derate(paper_fps, steps):
    \"\"\"把论文口径的 FPS 逐步折算到目标系统。steps: [(名字, 'mul'|'add', 值)]\"\"\"
    t = 1000.0 / paper_fps
    rows = [('论文口径', '', t)]
    for name, kind, v in steps:
        t = t * v if kind == 'mul' else t + v
        rows.append((name, ('x %.2f' % v) if kind == 'mul' else ('+ %.2f ms' % v), t))
    return rows, t, 1000.0 / t

RTDETR_STEPS = [
    ('T4 -> 车端 SoC（同精度算力约 0.53x）',      'mul', 1.90),
    ('输入 640 -> 1280（TSR 小目标必需）',        'mul', 3.40),
    ('预处理（1280 下 resize/letterbox/归一化）', 'add', 5.40),
    ('H2D + D2H 拷贝',                            'add', 1.60),
    ('跟踪与时序关联',                            'add', 0.80),
]
rows, ms, fps = derate(108, RTDETR_STEPS)
print('RT-DETR-R50：论文 108 FPS (T4 / TRT FP16 / batch=1 / 640 / 只计网络前向)\\n')
print(f\"{'折算步骤':<42s} {'操作':>10s} {'累计 ms':>10s}\")
for name, op, t in rows:
    print(f'{name:<42s} {op:>10s} {t:>10.2f}')
print(f'\\n车端端到端 = {ms:.2f} ms = **{fps:.1f} FPS**   （论文 108 FPS 的 1/{108/fps:.1f}）')
assert abs(ms - 67.61481481) < 1e-6
assert abs(fps - 14.7896) < 1e-3
assert 108 / fps > 7.0"""),

    code("""# 第二条链：一个「batch=32 吞吐」口径的 YOLO 数字
YOLO_STEPS = [
    ('batch=32 吞吐 -> batch=1 单帧', 'mul', 1.70),
    ('V100 -> 车端 SoC',              'mul', 2.60),
    ('NMS',                           'add', 1.40),
    ('预处理',                        'add', 1.80),
    ('H2D + D2H 拷贝',                'add', 0.45),
]
rows2, ms2, fps2 = derate(500, YOLO_STEPS)
print('某 YOLO：论文 500 FPS (V100 / FP16 / batch=32 / 只计网络前向)\\n')
print(f\"{'折算步骤':<34s} {'操作':>10s} {'累计 ms':>10s}\")
for name, op, t in rows2:
    print(f'{name:<34s} {op:>10s} {t:>10.2f}')
print(f'\\n车端端到端 = {ms2:.2f} ms = **{fps2:.1f} FPS**   （论文 500 FPS 的 1/{500/fps2:.1f}）')
assert abs(ms2 - 12.49) < 1e-9
assert abs(fps2 - 80.064) < 1e-2
print('\\n⚠️  两条链的**折算比例不同**（7.3x vs 6.2x），因为六个变量对不同模型的敏感度不同：')
print('    · 分辨率翻倍时，密集预测器的候选框数正比于像素数 -> NMS 涨得比推理还快')
print('    · RT-DETR 的 query 数固定，分辨率只影响 backbone/encoder')
print('    · batch=1 时，深而窄的模型比浅而宽的吃亏更多（kernel launch 开销占比上升）')
print('✅ **所以模型排名会随口径改变，不能照抄论文的相对顺序。**')"""),

    md("""## 4 · 怎么正确地测：warmup / 同步 / 分布 / 热态"""),

    code("""def simulate_runs(n, steady=9.30, warm=40, spike_p=0.03, seed=0):
    \"\"\"模拟一次真实的延迟测量：
       · 前 warm 次包含 autotune / 显存分配 / GPU 升频 -> 显著偏慢
       · 稳态有小噪声
       · spike_p 的概率发生抢占/页错误/热节流 -> 右偏长尾\"\"\"
    r = np.random.default_rng(seed)
    lat = np.full(n, steady, dtype=float)
    w = min(warm, n)
    lat[:w] *= np.linspace(3.0, 1.03, w)
    lat += r.normal(0, 0.15, n)
    m = r.random(n) < spike_p
    lat[m] += r.gamma(2.0, 1.8, int(m.sum()))
    return np.maximum(lat, 0.5)

runs = simulate_runs(200, warm=40, seed=1)
mean_all, mean_after = runs.mean(), runs[40:].mean()
LAUNCH_MS = 0.15                                   # kernel launch 本身的耗时

print(f'{\"❌ 不丢 warmup 的 200 次均值\":<32s} {mean_all:>8.2f} ms  -> {1000/mean_all:>6.1f} FPS')
print(f'{\"✅ 丢掉前 40 次的稳态均值\":<32s} {mean_after:>8.2f} ms  -> {1000/mean_after:>6.1f} FPS')
print(f'{\"❌ 不同步（只测到 kernel launch）\":<32s} {LAUNCH_MS:>8.2f} ms  -> {1000/LAUNCH_MS:>6.1f} FPS')
print(f'\\n不丢 warmup 高估延迟 {mean_all/mean_after-1:.0%}；不同步「加速」了 {mean_after/LAUNCH_MS:.0f} 倍（全是假的）')
assert mean_all > mean_after * 1.10
assert mean_after / LAUNCH_MS > 40
print('\\n✅ 纪律 ①：warmup 后丢弃。   纪律 ②：每次计时前后都 synchronize()（或用 CUDA event）。')"""),

    code("""big = simulate_runs(20000, warm=40, seed=7)[40:]
p50, p90, p99, p999 = np.percentile(big, [50, 90, 99, 99.9])
print(f\"{'统计量':<10s} {'延迟 ms':>10s} {'折成 FPS':>10s}\")
for lbl, v in [('mean', big.mean()), ('p50', p50), ('p90', p90),
               ('p99', p99), ('p99.9', p999), ('max', big.max())]:
    print(f'{lbl:<10s} {v:>10.2f} {1000/v:>10.1f}')
assert p99 > p50 * 1.12
assert p999 >= p99
assert p50 < big.mean() < p99, '均值被尾巴拉高但又低于尾巴 —— 两头不靠'

BUDGET = 12.0
over = float((big > BUDGET).mean())
print(f'\\n预算 {BUDGET:.0f} ms：p50={p50:.2f} 看起来「有 {BUDGET-p50:.1f} ms 余量」，'
      f'但 p99={p99:.2f} **已经超预算**')
print(f'超时帧占比 {over:.2%} -> 30 FPS 下平均每 {1/(over*30):.1f} 秒一次')
assert 0.005 < over < 0.06
print('\\n✅ 纪律 ③：报分布不报均值。车端安全关心 p99（甚至 p99.9）。')
print('⚠️  但 **p99 也不是上界** —— 它之上还有 p99.9 和真正的 max。')
print('    实时系统真正要的是 WCET：要么删掉数据依赖项，要么给它封顶。')"""),

    code("""def with_thermal(lat, drift_start=0.35, max_slow=1.18):
    \"\"\"持续满负载后 SoC 降频：延迟缓慢漂移。短测试完全看不出来。\"\"\"
    n = len(lat); k = np.ones(n); i0 = int(n * drift_start)
    k[i0:] = np.linspace(1.0, max_slow, n - i0)
    return lat * k

long_run = with_thermal(simulate_runs(20000, warm=40, seed=3))[40:]
early, late = long_run[:2000], long_run[-2000:]
e50, e99 = np.percentile(early, [50, 99])
l50, l99 = np.percentile(late,  [50, 99])
print(f\"{'':<22s} {'p50':>8s} {'p99':>8s}\")
print(f'{\"开测前 2000 帧（冷）\":<22s} {e50:>8.2f} {e99:>8.2f}')
print(f'{\"持续负载后 2000 帧（热）\":<22s} {l50:>8.2f} {l99:>8.2f}')
print(f'\\n热态 p50 比冷态高 {l50/e50-1:.0%} —— 「实验室 8 ms，车上跑半小时后 10 ms」就是这么来的')
assert l50 > e50 * 1.10
assert l99 > e99
print('\\n✅ 纪律 ④：测够长并覆盖热态。   纪律 ⑤：用真实帧序列，不要同一张图跑 1000 次')
print('   （同一张图 cache 命中异常高，而且完全测不出 NMS 的场景依赖）。')"""),
    md("""## 5 · 精度档的总账：「INT8 掉多少点」是个错的问法"""),

    code("""BASE_MS_FP32, BASE_AP = 12.00, 53.10          # 某模型的 FP32 端到端延迟与 AP
PRECISION = [
    ('FP32',       1.00,  0.00, '基线'),
    ('FP16',       0.42, -0.05, 'Tensor Core，几乎白送；只需查 inf/nan'),
    ('INT8 (PTQ)', 0.27, -1.20, '需要**有代表性的**校准集'),
    ('INT8 (QAT)', 0.27, -0.40, '要重训，几个 GPU-天'),
    ('混合精度',    0.34, -0.50, '敏感层保 FP16；分区变多可能反而慢，要实测'),
]
print(f\"{'精度档':<12s} {'相对延迟':>8s} {'延迟 ms':>9s} {'AP':>7s} {'说明'}\")
for name, mul, dap, note in PRECISION:
    print(f'{name:<12s} {mul:>8.2f} {BASE_MS_FP32*mul:>9.2f} {BASE_AP+dap:>7.2f}  {note}')
fp16_ms = BASE_MS_FP32 * 0.42
int8_ms = BASE_MS_FP32 * 0.27
assert fp16_ms < BASE_MS_FP32 * 0.50
assert int8_ms < fp16_ms * 0.70
print(f'\\n✅ FP16 基本白送：延迟降到 {0.42:.0%}，AP 几乎不动，不需要任何数据。')
print('   唯一要做的验证：用极端输入（过曝、超大幅值）跑一遍查 inf/nan')
print('   —— 这个问题在训练时被 loss scaling 掩盖，只在纯 FP16 推理时暴露。')"""),

    code("""# 关键实验：**在同一延迟预算下**，INT8 的大模型 vs FP16 的小模型，谁的 AP 高？
FAMILY_FP16 = [('RT-DETR-R18', 46.5, 4.6), ('RT-DETR-R34', 48.9, 6.2),
               ('RT-DETR-R50', 53.1, 9.3), ('RT-DETR-R101', 54.3, 13.5)]
FAMILY = [(n, ap, ms / 0.42) for n, ap, ms in FAMILY_FP16]      # 反推 FP32 端到端
BUDGET_MS, INT8_AP_COST = 6.0, 1.20

def best_in_budget(family, mul, ap_cost, budget):
    ok = [(ap - ap_cost, n, ms * mul) for n, ap, ms in family if ms * mul <= budget]
    if not ok:
        return None
    ap, n, ms = max(ok)
    return n, ap, ms

bf16 = best_in_budget(FAMILY, 0.42, 0.00, BUDGET_MS)
bi8  = best_in_budget(FAMILY, 0.27, INT8_AP_COST, BUDGET_MS)
print(f'延迟预算 {BUDGET_MS:.1f} ms 下能选的最大模型：\\n')
print(f\"{'精度档':<12s} {'能上的最大模型':<16s} {'实际延迟 ms':>12s} {'实际 AP':>9s}\")
print(f'{\"FP16\":<12s} {bf16[0]:<16s} {bf16[2]:>12.2f} {bf16[1]:>9.2f}')
print(f'{\"INT8 (PTQ)\":<12s} {bi8[0]:<16s} {bi8[2]:>12.2f} {bi8[1]:>9.2f}')
assert bf16[0] == 'RT-DETR-R18' and bi8[0] == 'RT-DETR-R50'
assert bi8[1] > bf16[1] + 4.0
print(f'\\n**INT8 本身掉 {INT8_AP_COST:.1f} AP，但让你在同一预算下从 {bf16[1]:.1f} AP 提到 {bi8[1]:.1f} AP（+{bi8[1]-bf16[1]:.1f}）。**')
print('✅ 所以正确的问法不是「INT8 掉多少点」，而是')
print('   「在同一延迟预算下，INT8 的大模型 vs FP16 的小模型，谁的 AP 更高」。')
print('⚠️  前提是校准集必须是**线上分布的有代表性样本**（含夜间/逆光/雨雾/隧道口/长尾类别），')
print('    用训练集前 500 张（很可能全是晴天白天）会得到只对晴天正确的量化范围。')"""),

    md("""## 6 · 帕累托前沿：被支配的模型直接删掉

下表是**教学用近似值**（口径：batch=1 / TRT FP16 / 640 / 含预处理）。
`needs_nms=True` 的模型要额外加上 NMS 时间 —— 这个「加多少」正是要演示的口径变量。"""),

    code("""MODELS = [   # (名字, COCO AP, 不含 NMS 的端到端 ms, 是否需要 NMS)
    ('RTMDet-S',     44.5,  2.6, True),
    ('RTMDet-M',     49.1,  4.4, True),
    ('RTMDet-L',     51.3,  6.1, True),
    ('YOLOv8-S',     44.9,  4.0, True),
    ('YOLOv8-M',     50.2,  6.5, True),
    ('YOLOv8-L',     52.9,  9.5, True),
    ('YOLOv8-X',     53.9, 15.0, True),
    ('RT-DETR-R18',  46.5,  4.6, False),
    ('RT-DETR-R34',  48.9,  6.2, False),
    ('RT-DETR-R50',  53.1,  9.3, False),
    ('RT-DETR-R101', 54.3, 13.5, False),
    ('D-FINE-S',     48.5,  4.8, False),
    ('D-FINE-M',     52.3,  7.1, False),
    ('D-FINE-L',     54.0,  9.8, False),
]

def end_to_end(models, nms_ms):
    return [(n, ap, round(base + (nms_ms if need else 0.0), 3)) for n, ap, base, need in models]

def pareto_front(pts):
    \"\"\"i 被支配 <=> 存在 j: lat_j <= lat_i 且 ap_j >= ap_i，且至少一项严格更好。\"\"\"
    out = []
    for i, (n, a, l) in enumerate(pts):
        dominated = any(l2 <= l and a2 >= a and (l2 < l or a2 > a)
                        for j, (_, a2, l2) in enumerate(pts) if j != i)
        if not dominated:
            out.append((n, a, l))
    return sorted(out, key=lambda r: r[2])

ptsA = end_to_end(MODELS, 1.4)
frontA = pareto_front(ptsA)
nameA = [n for n, _, _ in frontA]
print('口径 A：NMS 计 1.4 ms（朴素实现，密集场景更慢）\\n')
print(f\"{'模型':<14s} {'AP':>6s} {'端到端 ms':>10s} {'前沿?':>7s}\")
for n, a, l in sorted(ptsA, key=lambda r: r[2]):
    print(f'{n:<14s} {a:>6.1f} {l:>10.2f} {(\"● 是\" if n in nameA else \"○ 被支配\"):>7s}')
print(f'\\n前沿成员 {len(frontA)} 个: {nameA}')
assert len(frontA) == 8, frontA
assert 'RT-DETR-R50' in nameA and 'D-FINE-L' in nameA and 'RT-DETR-R101' in nameA
assert 'YOLOv8-L' not in nameA and 'YOLOv8-S' not in nameA and 'RTMDet-L' not in nameA
print('✅ 6 个模型被支配 —— 存在一个「不更慢且不更差」的替代品，可以直接从候选集删掉。')"""),

    code("""# **前沿是口径的函数**：只把 NMS 的计入方式改成 0.5 ms（EfficientNMS plugin + top-k 截断）
ptsB = end_to_end(MODELS, 0.5)
frontB = pareto_front(ptsB)
nameB = [n for n, _, _ in frontB]
print('口径 B：NMS 计 0.5 ms\\n')
print(f'前沿成员 {len(frontB)} 个: {nameB}\\n')
entered = [n for n in nameB if n not in nameA]
left    = [n for n in nameA if n not in nameB]
print(f'口径 A -> B **新进入前沿**: {entered}')
print(f'口径 A -> B **退出前沿**  : {left}')
assert len(frontB) == 10, frontB
assert set(entered) == {'YOLOv8-S', 'RTMDet-L'}, entered
assert left == []
print('\\n⚠️  **同一批模型、同一批 AP，只改一个测量约定，前沿成员就从 8 个变成 10 个。**')
print('✅ 所以「谁在前沿上」这个结论必须和口径一起被引用，否则没有意义。')"""),

    code("""def best_under_budget(pts, budget_ms):
    \"\"\"选型的核心动作：**同延迟比 AP**，而不是同 AP 比延迟。\"\"\"
    ok = [(a, n, l) for n, a, l in pts if l <= budget_ms]
    if not ok:
        return None
    a, n, l = max(ok)
    return n, a, l

print(f\"{'延迟预算 ms':>12s} {'最优选择':<16s} {'AP':>7s} {'实际延迟':>9s}\")
for bud in [3.0, 5.0, 6.5, 8.0, 10.0, 14.0]:
    r = best_under_budget(ptsA, bud)
    if r is None:
        print(f'{bud:>12.1f} {\"无可行方案\":<16s} {\"—\":>7s} {\"—\":>9s}')
    else:
        print(f'{bud:>12.1f} {r[0]:<16s} {r[1]:>7.1f} {r[2]:>9.2f}')
assert best_under_budget(ptsA, 3.0) is None
assert best_under_budget(ptsA, 5.0)[0] == 'D-FINE-S'
assert best_under_budget(ptsA, 8.0)[0] == 'D-FINE-M'
assert best_under_budget(ptsA, 10.0)[0] == 'D-FINE-L'
print('\\n✅ 「达到 53 AP 谁最快」是假问题 —— 你不需要恰好 53 AP，')
print('   你需要「在预算内 AP 最高」。延迟是系统给的硬约束，AP 是要最大化的目标。')"""),

    md("""## 7 · 延迟稳定性：p99 才是决定能不能上车的那个数

用第 2 节的端到端模型，跑一段「真实路测」的目标数分布（重尾：多数帧目标少，少数路口帧目标极多）。"""),

    code("""rng = np.random.default_rng(7)
N_SCENE = 4000
n_obj_s = np.clip(rng.lognormal(np.log(8), 0.9, N_SCENE).astype(int) + 1, 1, 220)
print(f'场景目标数分布: p50={np.percentile(n_obj_s,50):.0f}  p90={np.percentile(n_obj_s,90):.0f}  '
      f'p99={np.percentile(n_obj_s,99):.0f}  max={n_obj_s.max()}')

t_yolo = np.array([pipeline(n, model_ms=4.20, use_nms=True)[1]  for n in n_obj_s])
t_detr = np.array([pipeline(n, model_ms=6.30, use_nms=False)[1] for n in n_obj_s])
t_cap  = np.array([pipeline(n, model_ms=4.20, use_nms=True, topk=1000)[1] for n in n_obj_s])

def q(t):
    a, b, c = np.percentile(t, [50, 90, 99])
    return a, b, c, c - a

print(f\"\\n{'方案':<24s} {'p50':>8s} {'p90':>8s} {'p99':>8s} {'p99-p50':>9s}\")
for lbl, t in [('YOLO 式（含 NMS）', t_yolo), ('RT-DETR 式（无 NMS）', t_detr),
               ('YOLO + top-k 封顶(1000)', t_cap)]:
    a, b, c, d = q(t)
    print(f'{lbl:<24s} {a:>8.2f} {b:>8.2f} {c:>8.2f} {d:>9.2f}')

y50, _, y99, ygap = q(t_yolo)
d50, _, d99, dgap = q(t_detr)
c50, _, c99, cgap = q(t_cap)
assert y50 < d50,  'YOLO 的中位延迟更低'
assert y99 > d99,  '但 YOLO 的 p99 反超'
assert ygap > 3 * dgap
assert c99 < y99 - 2.0
print(f'\\n⚠️  **按 p50 选 -> YOLO；按 p99 选 -> RT-DETR。同一份数据，两个相反的结论。**')
print(f'    而「按均值选」会给出和「按 p50 选」一样的答案，然后上车在城市路口掉帧。')
print(f'\\n注意 RT-DETR 式的 p99-p50 也不是 0（{dgap:.2f} ms）—— 那是**跟踪与关联**的目标数依赖。')
print('    所以严格说法是「删掉了方差最大的那一项」，不是「延迟完全恒定」。')"""),

    code("""# top-k 封顶的代价：哪些帧被截断，截掉了多少候选
n_cand_full = np.minimum(300 + 60 * n_obj_s, 8400)
truncated = n_cand_full > 1000
frac = float(truncated.mean())
dropped = np.where(truncated, (n_cand_full - 1000) / n_cand_full, 0.0)
print(f'候选框数超过上限 1000 的帧占比: **{frac:.1%}**')
print(f'这些帧平均被截掉 {dropped[truncated].mean():.1%} 的候选（全部是低分候选）')
print(f'最坏的一帧被截掉 {dropped.max():.1%}')
assert 0.20 < frac < 0.45
assert dropped[truncated].mean() > 0.15
print('\\n⚠️  被截掉的低分候选，主要就是**远处的小目标**与**部分遮挡的目标**')
print('    —— 这个优化恰好在最需要召回的场景里牺牲召回。TSR 里尤其危险：')
print('    一块 80 m 外刚进视野的限速牌分数天然低，在拥挤路口很可能就是被截掉的那个。')
print('\\n✅ 封顶必须配三件事：')
print('   ① 统计「候选数 > N_max」的帧占比（太高说明 N_max 设小了）')
print('   ② 建一个「密集路口」评测切片，对比封顶前后的召回')
print('   ③ 把截断事件打点上报，作为线上监控指标')"""),

    md("""## 8 · TSR 选型决策脚本：硬约束过滤 → 加权打分 → 敏感性分析

关键设计：**硬约束过滤和加权打分严格分开**。先打分再看约束，会得到一个分数很高但根本上不了车的方案。"""),

    code("""CANDIDATES = [
    dict(name='YOLOv8-M',    ap_small=28.4, p99=12.6, mem=740,  plugin=False, menu=False, tool=0.95),
    dict(name='RTMDet-M',    ap_small=29.1, p99=11.8, mem=690,  plugin=False, menu=False, tool=0.85),
    dict(name='RT-DETR-R50', ap_small=34.8, p99=11.9, mem=1180, plugin=True,  menu=True,  tool=0.70),
    dict(name='RT-DETRv2-S', ap_small=31.6, p99= 8.4, mem=820,  plugin=False, menu=True,  tool=0.70),
    dict(name='D-FINE-M',    ap_small=33.2, p99= 9.9, mem=960,  plugin=True,  menu=True,  tool=0.50),
    dict(name='YOLOv8-X',    ap_small=31.9, p99=19.4, mem=1420, plugin=False, menu=False, tool=0.95),
]
# ap_small = 在**自己数据上按像素尺寸分桶**得到的小目标 AP（不是 COCO 总 AP！）
# menu     = 是否原生支持「一份权重多档速度」   tool = 工具链成熟度 0~1

HARD_STRICT = dict(p99_max=12.0, mem_max=1024, allow_plugin=False)
HARD_RELAX  = dict(p99_max=12.0, mem_max=1280, allow_plugin=True)
W_BALANCED  = dict(ap=0.45, head=0.20, menu=0.20, tool=0.15)
W_SMALLOBJ  = dict(ap=0.70, head=0.10, menu=0.10, tool=0.10)

def reject_reasons(c, hard):
    r = []
    if c['p99'] > hard['p99_max']:
        r.append('p99 %.1f > %.1f ms' % (c['p99'], hard['p99_max']))
    if c['mem'] > hard['mem_max']:
        r.append('显存 %d > %d MB' % (c['mem'], hard['mem_max']))
    if c['plugin'] and not hard['allow_plugin']:
        r.append('需要 TRT plugin')
    return r

def score(c, hard, w):
    return (w['ap']   * (c['ap_small'] / 40.0)
          + w['head'] * ((hard['p99_max'] - c['p99']) / hard['p99_max'])
          + w['menu'] * (1.0 if c['menu'] else 0.0)
          + w['tool'] * c['tool'])

def select_detector(cands, hard, w):
    ranked, rejected = [], []
    for c in cands:
        r = reject_reasons(c, hard)
        if r:
            rejected.append((c['name'], r))
        else:
            ranked.append((score(c, hard, w), c['name']))
    ranked.sort(reverse=True)
    return ranked, rejected

def show(tag, ranked, rejected):
    print(f'—— {tag} ——')
    for s, n in ranked:
        print(f'   {n:<14s} 得分 {s:.4f}')
    for n, r in rejected:
        print(f'   {n:<14s} ❌ 淘汰: {\"; \".join(r)}')
    print()

r1, x1 = select_detector(CANDIDATES, HARD_STRICT, W_BALANCED)
show('S1 保守：p99<=12ms / 显存<=1024MB / 不允许 plugin，均衡权重', r1, x1)
assert r1[0][1] == 'RT-DETRv2-S', r1
assert len(x1) == 4 and len(r1) == 2
print('读法：**4 个候选在硬约束这一步就被淘汰了，根本轮不到打分。**')"""),

    code("""r2, x2 = select_detector(CANDIDATES, HARD_RELAX, W_BALANCED)
show('S2 放开 plugin 与显存，权重不变', r2, x2)
assert r2[0][1] == 'RT-DETRv2-S', r2
assert len(x2) == 2 and len(r2) == 4
print('读法：放开两条约束后候选从 2 个变 4 个，但**胜出者没变**')
print('      -> 说明 plugin 与显存不是这次决策的瓶颈，不用在这两件事上开会。\\n')

r3, x3 = select_detector(CANDIDATES, HARD_RELAX, W_SMALLOBJ)
show('S3 同 S2 的约束，但把小目标 AP 的权重从 0.45 提到 0.70', r3, x3)
assert r3[0][1] == 'RT-DETR-R50', r3
assert r2[0][1] != r3[0][1]
print('读法：**只改权重，胜出者就换了。**')
print('      -> 真正需要开会讨论的不是「选哪个模型」，而是「小目标 AP 到底值多少权重」。')
print('      -> 而这个问题只能用数据回答：统计各尺寸桶的目标占比 + 各桶漏检的安全后果。')
print('\\n✅ 选型脚本的价值不是给出答案，是**把假设摆到台面上并做敏感性分析**。')"""),
    md("""## ✏️ 练习 1：毫秒 → 米

实现两个互逆的函数：
- `travel_distance_m(speed_kmh, latency_ms)`：这段延迟里车开出多少米
- `latency_budget_ms(speed_kmh, meters)`：要把「多开的距离」控制在 `meters` 以内，延迟上限是多少毫秒"""),

    code("""def travel_distance_m(speed_kmh, latency_ms):
    # TODO
    raise NotImplementedError

def latency_budget_ms(speed_kmh, meters):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测（手算）——
assert abs(travel_distance_m(120, 150) - 5.0) < 1e-12          # 33.3333 m/s * 0.15 s
assert abs(travel_distance_m(60, 100) - 60/3.6*0.1) < 1e-12
assert abs(travel_distance_m(120, 0) - 0.0) < 1e-12
assert abs(latency_budget_ms(120, 1.0) - 30.0) < 1e-9          # 1.0 m / 33.3333 m/s = 30 ms
assert abs(latency_budget_ms(36, 0.5) - 50.0) < 1e-9           # 36 km/h = 10 m/s
for v, t in [(120, 145.0), (80, 33.3), (36, 6.0)]:             # 互逆性
    assert abs(latency_budget_ms(v, travel_distance_m(v, t)) - t) < 1e-9
print(f\"{'车速 km/h':>10s} {'145 ms 开出 m':>14s} {'控制在 1 m 内的延迟上限 ms':>26s}\")
for v in [36, 60, 80, 120, 150]:
    print(f'{v:>10d} {travel_distance_m(v, 145):>14.2f} {latency_budget_ms(v, 1.0):>26.1f}')
print('\\n✅ 练习 1 通过：把毫秒翻译成米，是判断「这个优化值不值得做」的唯一工具。')"""),

    md("""## ✏️ 练习 2：论文 FPS 折算器

实现 `derate_chain(paper_fps, steps)` 返回 `(final_ms, real_fps)`。
`steps` 是 `[(名字, 'mul'|'add', 值)]`，按顺序依次应用：`'mul'` 乘在当前毫秒数上，`'add'` 加上去。"""),

    code("""def derate_chain(paper_fps, steps):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（手算）——
ms_, fps_ = derate_chain(100, [('a', 'mul', 1.5), ('b', 'mul', 2.0), ('c', 'add', 2.0)])
assert abs(ms_ - 32.0) < 1e-9, ms_          # 10 -> 15 -> 30 -> 32
assert abs(fps_ - 31.25) < 1e-9, fps_
ms0, fps0 = derate_chain(50, [])
assert abs(ms0 - 20.0) < 1e-12 and abs(fps0 - 50.0) < 1e-12
ms1, fps1 = derate_chain(108, RTDETR_STEPS)
assert abs(ms1 - 67.61481481) < 1e-6 and abs(fps1 - 14.7896) < 1e-3
ms2, fps2 = derate_chain(500, YOLO_STEPS)
assert abs(ms2 - 12.49) < 1e-9 and abs(fps2 - 80.064) < 1e-2
print(f'RT-DETR-R50 : 论文 108 FPS -> 车端 {fps1:5.1f} FPS  ({ms1:.2f} ms)')
print(f'某 YOLO     : 论文 500 FPS -> 车端 {fps2:5.1f} FPS  ({ms2:.2f} ms)')
print('\\n✅ 练习 2 通过：报延迟必须报口径，否则「谁更快」这个问题没有答案。')"""),

    md("""## ✏️ 练习 3：帕累托前沿

实现 `pareto(pts)`：`pts` 是 `[(名字, AP, 延迟ms)]`，返回**未被支配**的点，按延迟升序。

支配定义：`i` 被支配 ⟺ 存在 `j != i` 使得 `lat_j <= lat_i` 且 `ap_j >= ap_i`，且至少一项严格更好。"""),

    code("""def pareto(pts):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测（手算）——
toy = [('A', 40, 5.0), ('B', 45, 5.0), ('C', 44, 7.0), ('D', 50, 9.0)]
f = pareto(toy)
assert [n for n, _, _ in f] == ['B', 'D'], f
#  A 被 B 支配（同延迟但 AP 更低）；C 被 B 支配（更慢且 AP 更低）
assert pareto([('X', 50, 5.0)]) == [('X', 50, 5.0)]
# 在真实表上复现主结论
fa = [n for n, _, _ in pareto(end_to_end(MODELS, 1.4))]
fb = [n for n, _, _ in pareto(end_to_end(MODELS, 0.5))]
assert len(fa) == 8 and len(fb) == 10
assert 'YOLOv8-L' not in fa and 'RT-DETR-R50' in fa
assert set(fb) - set(fa) == {'YOLOv8-S', 'RTMDet-L'}
print(f'口径 A (NMS 1.4 ms) 前沿 {len(fa)} 个: {fa}')
print(f'口径 B (NMS 0.5 ms) 前沿 {len(fb)} 个: {fb}')
print('\\n✅ 练习 3 通过：**前沿是口径的函数，不是模型的固有属性。**')"""),

    md("""## ✏️ 练习 4：TSR 选型决策脚本

实现 `select_tsr(cands, hard, w)` 返回 `(ranked, rejected)`：
- `ranked`：通过全部硬约束的候选，`[(得分, 名字)]`，按得分降序
- `rejected`：`[(名字, [淘汰理由, ...])]`

直接复用上面已定义的 `reject_reasons(c, hard)` 与 `score(c, hard, w)`。"""),

    code("""def select_tsr(cands, hard, w):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
ra, xa = select_tsr(CANDIDATES, HARD_STRICT, W_BALANCED)
assert ra[0][1] == 'RT-DETRv2-S' and len(ra) == 2 and len(xa) == 4
assert abs(ra[0][0] - 0.7205) < 1e-6, ra[0]     # 0.45*0.79 + 0.20*0.30 + 0.20 + 0.15*0.70
rb, xb = select_tsr(CANDIDATES, HARD_RELAX, W_BALANCED)
assert rb[0][1] == 'RT-DETRv2-S' and len(rb) == 4 and len(xb) == 2
rc, xc = select_tsr(CANDIDATES, HARD_RELAX, W_SMALLOBJ)
assert rc[0][1] == 'RT-DETR-R50', rc
assert [s for s, _ in ra] == sorted([s for s, _ in ra], reverse=True), '必须按得分降序'
assert dict(xa)['RT-DETR-R50'], 'R50 在严格约束下应被淘汰并给出理由'
print(f\"{'场景':<28s} {'胜出':<16s} {'候选数':>7s} {'被淘汰':>7s}\")
for tag, (r, x) in [('S1 严格 / 均衡权重', (ra, xa)),
                    ('S2 放开约束 / 均衡权重', (rb, xb)),
                    ('S3 放开约束 / 重小目标', (rc, xc))]:
    print(f'{tag:<28s} {r[0][1]:<16s} {len(r):>7d} {len(x):>7d}')
print('\\n✅ 练习 4 通过：硬约束过滤与加权打分必须分开，且**必须做权重敏感性分析**。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def travel_distance_m(speed_kmh, latency_ms):
    return speed_kmh / 3.6 * latency_ms / 1000.0

def latency_budget_ms(speed_kmh, meters):
    return meters / (speed_kmh / 3.6) * 1000.0"""),

    code("""# 练习 2 参考答案
def derate_chain(paper_fps, steps):
    t = 1000.0 / paper_fps
    for _, kind, v in steps:
        t = t * v if kind == 'mul' else t + v
    return t, 1000.0 / t"""),

    code("""# 练习 3 参考答案
def pareto(pts):
    out = []
    for i, (n, a, l) in enumerate(pts):
        dominated = any(l2 <= l and a2 >= a and (l2 < l or a2 > a)
                        for j, (_, a2, l2) in enumerate(pts) if j != i)
        if not dominated:
            out.append((n, a, l))
    return sorted(out, key=lambda r: r[2])"""),

    code("""# 练习 4 参考答案
def select_tsr(cands, hard, w):
    ranked, rejected = [], []
    for c in cands:
        r = reject_reasons(c, hard)
        if r:
            rejected.append((c['name'], r))
        else:
            ranked.append((score(c, hard, w), c['name']))
    ranked.sort(reverse=True)
    return ranked, rejected"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接照抄的测速与选型协议"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 实时检测器测速与选型协议（把它写进团队 wiki，每次选型照着走）
# ══════════════════════════════════════════════════════════════════════

# ─── 0. 先写死口径（Benchmark Contract），所有模型必须用同一份 ───────────
BENCH_CONTRACT = dict(
    device        = "Orin-X / driver 535.x / TensorRT 10.x",   # 换任何一项都要重测
    precision     = "fp16",              # 或 int8 + 校准集哈希
    batch         = 1,                   # 车端就是 1，不要用吞吐口径
    input_size    = (1280, 1280),        # TSR 的真实分辨率，不是 COCO 的 640
    includes      = ["preprocess", "H2D", "infer", "decode", "NMS", "D2H", "track"],
    clock_locked  = True,                # nvidia-smi -lgc / jetson_clocks
    warmup_iters  = 200,                 # 丢弃
    measure_iters = 2000,
    frames        = "real_route_mix_v3", # **真实帧序列**，含稀疏高速/密集路口/夜间
    report        = ["p50", "p90", "p99", "p99.9", "max", "peak_mem_MB"],
)
# 铁律：报 p50 和 p99 **两个数**。只报一个的对比无效。

# ─── 1. 用 trtexec 做交叉验证（它已经把 warmup/同步/分位数做对了）─────────
#   trtexec --loadEngine=m.engine --iterations=2000 --avgRuns=1 \
#           --percentile=99 --useCudaGraph --dumpProfile --separateProfileRun
#   看三件事：① Latency 的 median/percentile ② 逐层耗时找瓶颈
#             ③ 有没有 "unsupported"/多子图（静默回退 -> 转了但没变快）

# ─── 2. Python 侧的正确计时骨架 ─────────────────────────────────────────
#   for _ in range(200): model(next(frames))          # warmup 丢弃
#   torch.cuda.synchronize()
#   ts = []
#   for _ in range(2000):
#       x = next(frames)                              # 真实帧，不是同一张
#       torch.cuda.synchronize(); t0 = time.perf_counter()
#       out = model(x)
#       torch.cuda.synchronize()                      # ← 少了这句测的是 kernel launch
#       ts.append((time.perf_counter() - t0) * 1e3)
#   p50, p90, p99, p999 = np.percentile(ts, [50, 90, 99, 99.9])

# ─── 3. 热态验证（短测试测不出降频）────────────────────────────────────
#   连续满负载跑 >= 10 分钟，对比「前 2000 帧」与「后 2000 帧」的 p50
#   通过条件：漂移 < 10%；超过就要在预算里预留降频余量

# ─── 4. 选型三步（顺序不能反）──────────────────────────────────────────
HARD_CONSTRAINTS = dict(          # ① 硬约束过滤：多数候选在这一步就没了
    p99_ms_max   = 6.0,           # 你的时隙，不是帧周期
    max_ms_max   = 9.0,           # 最坏值也要有门槛
    peak_mem_MB  = 1024,          # SoC 显存由所有感知任务共享
    allow_plugin = False,         # 每个 TRT plugin 都是长期维护负债
    ptq_ap_drop_max = 2.0,        # PTQ 掉点超过这个就要重新评估
)
METRIC = "AP_small(<32px) on our_val_v7"   # ② **不是 COCO AP**，按像素尺寸分桶
WEIGHTS = dict(ap=0.45, headroom=0.20, speed_menu=0.20, toolchain=0.15)  # ③ 打分
# ④ **必须做敏感性分析**：把主要权重 ±50% 各跑一次。
#    结论变了 -> 真正要定的是那个权重，而不是模型。

# ─── 5. 发布前的验收清单 ───────────────────────────────────────────────
#   [ ] 端到端 p99 <= 时隙，max <= 1.5 x 时隙
#   [ ] 热态 10 分钟后 p50 漂移 < 10%
#   [ ] 峰值显存 <= 上限（与其他感知任务并发时实测，不是单跑）
#   [ ] TRT 子图数 == 1（无静默回退）
#   [ ] 分尺寸桶 AP 全部不低于 baseline（回归门禁）
#   [ ] 密集路口切片的召回不低于 baseline（如果上了 top-k 封顶，这条是硬门槛）
#   [ ] 记录 engine 的构建环境（GPU 型号 + 驱动 + TRT 版本 + 精度 + 校准集哈希）
'''
print(RECIPE)
for token in ['BENCH_CONTRACT', 'p99', 'trtexec', 'synchronize', 'clock_locked',
              'HARD_CONSTRAINTS', 'AP_small', '敏感性分析', '子图数']:
    assert token in RECIPE, token
print('✅ 协议覆盖：口径契约 / trtexec 交叉验证 / 计时骨架 / 热态 / 选型三步 / 验收清单')"""),

    md("""### 小结

- **33 ms 是帧周期，不是延迟预算。** 吞吐与延迟是两个独立约束。端到端反应链约 145 ms，
  感知只占 45 ms，而 TSR 在共享 SoC 上只分到约 **6 ms**。
  换算工具只有一个：**毫秒 → 米**（120 km/h 下每 10 ms = 0.33 m）。
- **端到端延迟 = 预处理 + H2D + 推理 + 解码 + NMS + D2H + 跟踪。**
  只有 NMS 与跟踪依赖场景；同一个模型在稀疏场景与密集路口能差 3.4 倍。
  一个立刻能拿的收益：**只上传 uint8，归一化放设备侧**（fp32 上传贵 4 倍）。
- **论文 FPS 不可信的六个变量**：batch / 含不含 NMS / 含不含预处理与拷贝 / 精度档 / 什么卡 /
  输入分辨率。复合起来能差 **24 倍**。108 FPS 折到车端 TSR 场景是 **14.8 FPS**。
  而且**六个变量对不同模型的敏感度不同 → 排名会随口径改变**，不能照抄论文的相对顺序。
- **五条测量纪律**：warmup 后丢弃 / 每次计时都同步 / 报分布不报均值 / 测够长覆盖热态 /
  用真实帧序列。不同步能测出 **60 倍的假加速**；不丢 warmup 高估约 **20%**。
- **精度档的正确问法**不是「INT8 掉多少点」，而是「同一预算下 INT8 的大模型 vs FP16 的小模型
  谁 AP 高」——本例里 INT8 掉 1.2 AP，却让同预算下的 AP 从 46.5 涨到 51.9。
  前提是**校准集必须覆盖夜间/逆光/雨雾/长尾类别**。
- **帕累托前沿**：同延迟比 AP，不是同 AP 比延迟。**前沿是口径的函数**——只把 NMS 从
  1.4 ms 改成 0.5 ms，前沿成员就从 8 个变成 10 个。
- **p50 与 p99 会给出相反的结论**：YOLO 式 p50 更快但 p99 更慢。
  top-k 封顶能把 p99 压下来，代价是约 1/3 的帧被截断（截掉的正是远处小目标）。
  另外「无 NMS」也不等于延迟恒定——**跟踪与关联同样依赖目标数**。
- **选型三步**：硬约束过滤 → 用**自己数据上的分桶指标**画前沿 → 加权打分 + 敏感性分析。
  顺序不能反。**用 COCO AP 排序 + 用论文 FPS 排序，两个错误叠加能得出与实测完全相反的结论。**

本课到此结束。下一站：**C54（DETR 集合预测的完整推导）** 与 **C57（小目标）** ——
它们分别补上本课里两个被反复引用但没有展开的东西：匈牙利匹配，和「为什么小目标这么难」。"""),
]
