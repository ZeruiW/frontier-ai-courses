# -*- coding: utf-8 -*-
"""C60 模块 02 · TensorRT 构建与优化。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（一致性方法论 / 预处理对齐）；C52 模块 03（ONNX 导出与运行时）强烈建议先读"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_tensorrt_pipeline.ipynb（纯 numpy：迷你图 IR + 融合规则引擎）'),
    ("核心参考", "TensorRT Developer Guide / Best Practices · trtexec 文档 · TensorRT OSS plugin 仓库 · ONNX Runtime TensorRT EP"),
    ("预计时长", "读 75 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("pipeline", "链路全景：三次翻译，三类事故", "".join([
        P("从一个 <code>nn.Module</code> 到一个能在车上跑起来的 <code>.plan</code> 文件，中间要过三道关。"
          "<strong>每一道关都是一次「表达力换性能」的翻译，而每一次翻译有它专属的事故形态</strong>——"
          "把这三类事故分清楚，是本模块最实用的收获，也是排查时能不能在半小时内定位问题的分水岭。"),
        ASCII("""① PyTorch nn.Module            ② ONNX graph                ③ TensorRT engine (.plan)
   Python 代码 + autograd         静态图 + opset 版本号        kernel 序列 + 内存计划
   · 任意控制流                    · 算子集被冻结               · 层已融合 / 重排 / 降精度
   · shape 随便变                  · shape 用符号维表达          · tactic 已按目标 GPU 选定
   · 可读、可调试、可微            · 可读、可改、跨后端          · 二进制、不可读、绑定硬件
        │                               │                            │
        │ torch.onnx.export             │ IBuilder::buildSerialized  │  runtime->deserialize
        │ (trace / dynamo)              │ Network()                  │  CudaEngine(...)
        ▼                               ▼                            ▼
 ┌──────────────────┐          ┌──────────────────┐        ┌──────────────────┐
 │ 事故 A：语义错   │          │ 事故 B：不变快   │        │ 事故 C：换机就废 │
 │ 控制流被固化     │          │ 算子回退成子图   │        │ 型号/版本不匹配  │
 │ shape 被写死     │          │ 融合被阻断       │        │ tactic 在别的卡  │
 │ 算子被近似替换   │          │ 精度标志没生效   │        │ 上不是最优       │
 │ → 数值就是错的   │          │ → 数值对，白干了 │        │ → 直接加载失败   │
 └──────────────────┘          └──────────────────┘        └──────────────────┘"""),
        P("这三类事故的<strong>排查手段完全不同</strong>，混着查是新手最大的时间浪费："),
        TABLE(["事故类", "典型症状", "第一手证据", "查错工具", "本课在哪讲"], [
            ["<strong>A · 语义错</strong>", "ONNX 输出和 PyTorch 对不上；换个输入尺寸结果就崩",
             "同一张图，两边 dump 张量逐元素 diff", "<code>onnxruntime</code> 逐节点对拍、<code>polygraphy run --onnxrt --trt</code>",
             "C52 m03 / 本课 m01"],
            ["<strong>B · 不变快</strong>", "「转了 TRT 但只快了 5%」；FP16 开了跟没开一样",
             "engine 的层数、层名、每层精度、子图数", "<code>trtexec --dumpLayerInfo --profilingVerbosity=detailed</code>",
             "<strong>本模块第 4–6、8 节</strong>"],
            ["<strong>C · 换机就废</strong>", "开发机上好好的，刷到车上直接反序列化失败",
             "engine 头里的 TRT 版本 + SM 架构 + 平台标识", "加载时的报错行、<code>trtexec --loadEngine</code>",
             "<strong>本模块第 7 节</strong>"],
        ]),
        DUAL(
            "一句话概括这条链路：<strong>ONNX 是「模型说了什么」，engine 是「这块芯片打算怎么做」</strong>。"
            "ONNX 里一个 <code>Conv</code> 节点在 engine 里可能变成半个层（被融进邻居）、可能变成三个层"
            "（被拆开加了两个格式转换）、也可能根本不存在（被常量折叠掉了）。"
            "<em>所以拿 ONNX 的节点数去猜 engine 的性能，方向就是错的；你必须去看 engine 自己的层信息。</em>",
            "更精确地说，TensorRT 的 <span class=\"term\">builder</span> 做的是一次<strong>目标相关的编译</strong>："
            "输入是网络定义（<code>INetworkDefinition</code>）+ 构建配置（<code>IBuilderConfig</code>）+ <em>目标设备本身</em>，"
            "输出是一个序列化的执行计划。它至少做四件事：①图级重写（常量折叠、死层消除、层融合、concat 消除）；"
            "②为每层枚举候选实现（tactic）并<strong>在真实设备上计时</strong>选最快的；③规划张量的内存复用"
            "（activation memory 是一块被反复覆写的池子，不是每层各占一块）；④插入必要的 reformat 层来对齐"
            "相邻层要求的数据布局与精度。<strong>其中②是「必须在目标硬件上构建」的根本原因，也是构建慢的根本原因。</strong>",
        ),
        CALLOUT("warn", "<p><strong>能不能跳过 ONNX？</strong>可以，路径有 <code>torch-tensorrt</code>（PyTorch 直接编译）、"
                "<code>TF-TRT</code>、以及 ONNX Runtime 的 TensorRT ExecutionProvider。它们的共同特点是"
                "<strong>「分区式集成」：跑得动的子图交给 TRT，跑不动的留给原框架</strong>。"
                "<em>开发期这很省事，但它把「事故 B」变成了默认行为——模型永远能跑，你永远不知道有多少留在了慢路径上。</em>"
                "量产链路上，多数团队仍然走「显式导出 ONNX → 显式 build engine」，理由不是性能，是"
                "<strong>「不支持的算子必须让我在 CI 里当场看到，而不是在车上悄悄变慢」</strong>。</p>",
                "分区式集成 = 把失败变成静默降级"),
    ])),

    # ============================================================== 2
    ("builder", "builder config：那几个真正决定成败的开关", "".join([
        P("<code>IBuilderConfig</code> 上有几十个设置，但决定成败的就那么几个。这一节只讲这几个，并且讲清楚"
          "<strong>「设了会怎样」和「忘了设会怎样」</strong>——后者才是面试和线上真正要命的部分。"),
        H3("① workspace：它不是「engine 会用多少显存」"),
        P("这是被误解最多的一项。<code>config.set_memory_pool_limit(MemoryPoolType.WORKSPACE, N)</code> 设的是"
          "<strong>「构建期允许某个 tactic 临时申请多少显存」</strong>，不是 engine 运行时的显存占用。"
          "很多高性能实现（需要大块中间缓冲的 implicit GEMM、Winograd 变换、某些 FFT 卷积）"
          "会申请可观的 workspace；<strong>你给的额度不够，这些 tactic 直接从候选集里被剔除，"
          "TRT 不报错，只是默默选一个慢的</strong>。"),
        P("典型症状：同一个 ONNX、同一块卡，同事构建出来比你快 20%，唯一差别是他 workspace 给了 4 GB 你给了 64 MB。"
          "TensorRT 8.4 之后默认额度是设备总显存，所以新版本上这个坑变少了；"
          "<em>但在显存紧张的车端 SoC 上，你常常需要主动调小它来避免构建期 OOM，这时候就得亲手做这个权衡。</em>"),
        H3("② 精度标志：这是「许可证」，不是「命令」"),
        P("<code>config.set_flag(BuilderFlag.FP16)</code> 的语义是<strong>「允许 TRT 在它认为划算的地方用 FP16」</strong>。"
          "TRT 仍然按实测耗时选 tactic——如果某层的 FP32 实现恰好更快（小层、或该层的 FP16 kernel 需要额外的 reformat），"
          "它就用 FP32。所以 <strong>「我开了 FP16 但一点没变快」是完全可能的，而且不会有任何警告</strong>。"),
        TABLE(["Flag", "语义", "忘了设会怎样", "设了但没生效的检查方法"], [
            ["<code>FP16</code>", "允许 FP16 tactic（需要硬件支持）", "全 FP32，延迟大约是 FP16 的 1.5–2.5×",
             "<code>--dumpLayerInfo</code> 看每层的 <code>Precision</code> 字段还有多少是 FP32"],
            ["<code>INT8</code>", "允许 INT8 tactic；<strong>还必须提供 scale</strong>（calibrator 或图里的 Q/DQ）",
             "INT8 完全没启用，或只有部分层启用", "同上；再看 <code>Reformat</code> 层数量是否异常多"],
            ["<code>BF16</code>", "允许 BF16（Ampere+ / Orin 之后）", "在动态范围大的模型上更容易 FP16 溢出",
             "同上"],
            ["<code>PREFER_PRECISION_CONSTRAINTS</code>", "尽量遵守你用 <code>setPrecision()</code> 指定的层精度，做不到就回退并 warn",
             "你指定的混合精度方案被无声忽略", "看构建日志里的 warning"],
            ["<strong><code>OBEY_PRECISION_CONSTRAINTS</code></strong>", "<strong>必须遵守，做不到就构建失败</strong>",
             "同上，但失败是显式的", "<strong>做混合精度时应该用这个</strong>——你要的是「不行就告诉我」"],
            ["<code>SPARSE_WEIGHTS</code>", "允许利用 2:4 结构化稀疏", "稀疏化训练的收益拿不到", "看 log 里 sparse tactic 是否被选中"],
            ["<code>REFIT</code>", "构建可重拟合 engine（权重能换而不重建）", "换权重必须完整重建", "—（会略微降低性能，非必要不开）"],
            ["<code>timing cache</code>", "复用上次的 tactic 计时结果", "每次 CI 都要完整重跑 auto-tuning", "对比两次构建耗时"],
        ]),
        DUAL(
            "把精度标志理解成<strong>「我授权你在这些数据类型里挑」</strong>，而不是「把模型转成 FP16」。"
            "同理，<code>INT8</code> 这个 flag 只是授权；<em>没有 scale，TRT 根本不知道怎么把浮点映射到 8 位整数</em>，"
            "所以它会把那些层留在 FP16/FP32。这就是为什么「我开了 INT8 但精度一点没掉」通常不是好消息——"
            "<strong>多半是根本没量化上</strong>（下一模块会展开）。",
            "从优化器的角度看，builder 在做一个受约束的组合优化：对每层 $\\ell$ 选一个 tactic $t_\\ell$（含实现算法、"
            "数据布局、精度），目标是最小化 $\\sum_\\ell \\tau(t_\\ell) + \\sum_{(\\ell,\\ell')} \\rho(t_\\ell, t_{\\ell'})$，"
            "其中 $\\rho$ 是相邻层布局/精度不匹配时插入 reformat 的代价。<strong>精度标志改变的是可行域，不是目标函数</strong>。"
            "这解释了两个反直觉现象：<em>①开了 FP16 反而某些层还是 FP32（因为 reformat 代价 $\\rho$ 超过了该层的收益）；"
            "②手工把某层强制成 FP16 反而整体变慢（因为你在它前后各强加了一次 reformat）。</em>",
        ),
        CALLOUT("danger", "<p><strong>面试高频题：「你开了 FP16，延迟没变，怎么查？」</strong>"
                "标准答法有四步，缺一步就显得没做过：<em>①先确认硬件与 TRT 版本支持（<code>builder.platform_has_fast_fp16</code>）；"
                "②用 <code>--dumpLayerInfo --profilingVerbosity=detailed</code> 导出层信息，统计还有多少层是 FP32——"
                "如果几乎全是 FP32，问题在构建配置；③如果层精度确实是 FP16，看 <code>Reformat</code> 层的数量与耗时占比——"
                "精度在层间反复切换会把收益吃光；④如果层精度对、reformat 也少，那瓶颈根本不在算力，"
                "去看 roofline：模型是 memory-bound 的话，FP16 只把权重读取量减半，激活读写量没变，收益天然有限</em>。"
                "<strong>第④点是拉开差距的地方</strong>——很多人只会答前两步。</p>", "「开了 FP16 没变快」的四步排查"),
    ])),

    # ============================================================== 3
    ("profile", "动态 shape 与 optimization profile：min/opt/max 的性能账", "".join([
        P("TensorRT 的性能来自「为具体的 shape 挑具体的 kernel」。所以<strong>动态 shape 与性能天生是对立的</strong>——"
          "你每放宽一点输入的自由度，就要付出一点性能或一点显存。这一节讲清楚这笔账怎么算。"),
        H3("optimization profile 是什么"),
        P("对每个动态维度，你要给三个数：<code>min</code> / <code>opt</code> / <code>max</code>。它们的作用<strong>各不相同，"
          "别混为一谈</strong>："),
        TABLE(["档位", "它决定什么", "设错的后果"], [
            ["<code>min</code>", "运行时允许的最小 shape（越界直接报错）", "设太大 → 小输入被拒；设太小 → 扩大了搜索范围，可能拖累 tactic 质量"],
            ["<strong><code>opt</code></strong>", "<strong>builder 在这个 shape 上计时并挑 tactic</strong>",
             "<strong>设错 = 你的高频 shape 上跑的是为别的 shape 挑的 kernel，实测可慢 10–30%</strong>"],
            ["<code>max</code>", "允许的最大 shape；<strong>activation 显存按它预分配</strong>",
             "设太大 → 显存被无谓占住（车端 SoC 上很致命）；设太小 → 大输入直接报错"],
        ]),
        ASCII("""shape 分布（比如两级 TSR 里第二级分类器的 crop 数）
   频次
    │        ▄▄█▄▄
    │      ▄███████▄                          ▄
    │    ▄███████████▄▄                  ▄▄  ███
    └────┴──┴───┴────┴──────────────────┴──┴────┴──►  batch
         2  4   8   12                  48  56  64

 方案 A · 单 profile [1, 8, 64]
   ├ opt=8 命中主峰 → 主峰上性能最好
   ├ batch=56 时用的是为 8 挑的 tactic → 慢 15~30%
   └ 显存按 batch=64 预留  ← 主峰只用 8，浪费 8 倍

 方案 B · 双 profile [1,8,16] + [17,56,64]
   ├ 两个峰各自命中 → 两边都快
   ├ 构建时间 ×2，engine 变大
   └ **每个 profile 需要独立的 execution context** → activation 显存 ×2

 方案 C · 分桶（bucketing）：把 batch padding 到 {8, 16, 32, 64}
   ├ 每桶一个**静态 shape** engine → 每个都是最优 tactic
   ├ 显存 = max 桶（可只常驻常用桶，按需加载）
   └ 代价：padding 的算力浪费 + 多个 engine 的管理成本"""),
        P("三个方案的选择依据不是「哪个先进」，而是<strong>你的 shape 分布长什么样、显存有多紧、以及你能承受多少工程复杂度</strong>。"
          "用一个简单的代价模型就能算出来："),
        MATH("\\mathbb{E}[T] \\;=\\; \\sum_{s} p(s)\\, t_0(s)\\,\\Bigl(1 + \\alpha \\bigl|\\ln (s / s_{\\text{opt}})\\bigr|\\Bigr), "
             "\\qquad M \\;=\\; m_{\\text{w}} + n_{\\text{ctx}} \\cdot m_{\\text{act}}(s_{\\max})"),
        P("$t_0(s)$ 是该 shape 在专门为它构建的静态 engine 上的耗时，$\\alpha$ 是「偏离 opt 的惩罚系数」"
          "（实测常在 0.05–0.25 之间，取决于层类型：GEMM 类对 tile 尺寸敏感，$\\alpha$ 大；elementwise 类几乎无所谓）。"
          "<strong>notebook 里会用动态规划求出「给定 $k$ 个 profile，怎么切分 shape 区间使期望延迟最小」的最优解</strong>，"
          "并画出 $k$ 增加时的边际收益——你会看到典型情况下 $k=2$ 就吃掉了绝大部分收益，$k=4$ 以上基本白花构建时间。"),
        DUAL(
            "最省事也最快的方案永远是<strong>静态 shape</strong>：把输入尺寸钉死，一个数都不许动。"
            "车端感知的主链路基本都这么做——相机分辨率是固定的，letterbox 之后也是固定的，"
            "<em>没有任何理由让主检测器接受动态输入</em>。动态 shape 真正不可避免的地方只有少数几处："
            "多相机时激活的相机数会变（batch 维）、两级架构里第二级的 crop 数随场景变、"
            "以及需要多分辨率档位来做算力降级的场景。",
            "值得强调的是 <strong>execution context 与 profile 的绑定关系</strong>：一个 <code>IExecutionContext</code> "
            "同一时刻只能绑定一个 optimization profile，切换 profile 要调 <code>setOptimizationProfileAsync()</code> "
            "并等待同步——<em>在延迟敏感的推理循环里频繁切 profile 是反模式</em>。常见做法是为每个 profile 建一个常驻 context，"
            "但每个 context 都要有自己的 activation 显存（除非用 <code>createExecutionContextWithoutDeviceMemory()</code> "
            "手动共享一块足够大的显存并自己保证不并发使用）。<strong>所以「多 profile」的真实代价是显存乘以 context 数，"
            "这在只有几 GB 可用显存的车规 SoC 上往往才是硬约束，而不是构建时间。</strong>",
        ),
        CALLOUT("intuition", "把这一节压成一句话：<strong><code>opt</code> 决定你有多快，<code>max</code> 决定你占多少显存，"
                "<code>min</code> 只决定你会不会崩。</strong>三个数里最该被认真对待的是 <code>opt</code>，"
                "而它应该来自<em>线上 shape 分布的实际统计</em>，不是拍脑袋写的中位数。"),
    ])),

    # ============================================================== 4
    ("fusion", "层融合：省的不是计算，是访存", "".join([
        P("<strong>层融合是 TensorRT 收益最大、也最容易被误解的一项优化。</strong>误解在于："
          "很多人以为融合省的是 FLOPs。<em>不是。Conv+BN+ReLU 融合之后，乘加次数一次都没少</em>——"
          "省下的是<strong>把中间结果写回显存再读回来</strong>的那几趟，以及两次 kernel launch。"),
        H3("垂直融合的数值基础：Conv + BN 的等价变换"),
        P("推理期的 <span class=\"term\">BatchNorm</span> 是一个逐通道的仿射变换（running stats 已冻结），"
          "而卷积也是线性的，所以两者可以合并成一个卷积。设第 $o$ 个输出通道的卷积核为 $W_o$、偏置 $b_o$，"
          "BN 参数为 $(\\gamma_o, \\beta_o, \\mu_o, \\sigma_o^2, \\epsilon)$："),
        MATH("\\mathrm{BN}\\bigl(W_o * x + b_o\\bigr) \\;=\\; \\gamma_o\\,\\frac{(W_o * x + b_o) - \\mu_o}{\\sqrt{\\sigma_o^2+\\epsilon}} + \\beta_o "
             "\\;=\\; \\underbrace{\\frac{\\gamma_o}{\\sqrt{\\sigma_o^2+\\epsilon}}W_o}_{\\tilde W_o} * x \\;+\\; "
             "\\underbrace{\\frac{\\gamma_o\\,(b_o-\\mu_o)}{\\sqrt{\\sigma_o^2+\\epsilon}} + \\beta_o}_{\\tilde b_o}"),
        P("<strong>这是严格恒等，不是近似</strong>（浮点舍入除外）。notebook 里会用 numpy 从零实现卷积与 BN，"
          "对随机输入验证融合前后 <code>np.allclose</code> 到 $10^{-10}$ 量级。"
          "<em>这个证明值得亲手写一遍：C53 模块 01 讲的结构重参数化（RepVGG 多分支合并）用的是同一套代数，"
          "而下一模块讲 QAT 时的「BN folding 必须在插 fake-quant 之前做」也是同一件事。</em>"),
        H3("收益从哪来：一笔访存账"),
        P("拿一个 640 输入下 S3 层级（80×80）、256 通道的层来算，FP16 每元素 2 字节，激活张量是 3.28 MB："),
        TABLE(["形态", "kernel 数", "FLOPs", "访存字节", "算术强度 FLOP/Byte", "估计耗时（含 launch）"], [
            ["<strong>3×3 标准卷积</strong> 拆成 Conv / BN / ReLU 三个 kernel", "3", "7.55 G", "20.8 MB",
             "整体 <strong>362</strong>（Conv 977 / BN <strong>0.5</strong> / ReLU <strong>0.25</strong>）",
             "760 + 38 + 38 = <strong>835 µs</strong>"],
            ["3×3 标准卷积，<strong>融合成一个</strong>", "1", "7.55 G", "7.7 MB", "977", "<strong>760 µs（省 9%）</strong>"],
            ["<strong>5×5 depthwise</strong> 拆成三个 kernel", "3", "0.087 G", "19.7 MB", "整体 <strong>4.4</strong>（DW 本身只有 12.5）",
             "38 + 38 + 38 = <strong>113 µs</strong>"],
            ["5×5 depthwise，<strong>融合成一个</strong>", "1", "0.087 G", "6.6 MB", "13.2", "<strong>38 µs（省 67%）</strong>"],
        ]),
        P("（假设 10 TFLOPS FP16 + 200 GB/s 带宽 + 每个 kernel 5 µs 启动开销，用 roofline 估计 "
          "$t \\approx \\max(\\text{FLOPs}/P,\\ \\text{Bytes}/B) + t_{\\text{launch}}$；notebook 会把这张表逐格算出来。）"),
        MATH("t_{\\text{layer}} \\;\\approx\\; \\max\\!\\left(\\frac{\\text{FLOPs}}{P_{\\text{peak}}},\\ \\frac{\\text{Bytes}}{B_{\\text{mem}}}\\right) \\;+\\; t_{\\text{launch}}"),
        P("<strong>结论非常尖锐：融合对「厚重的标准卷积」只值 9%，对「轻薄的 depthwise 卷积」值 67%。</strong>"
          "而现代实时检测器（RTMDet 的 CSPNeXt、YOLO 的轻量变体、MobileNet 系 backbone）里 depthwise 遍地都是——"
          "<em>越是为「FLOPs 少」而设计的模型，越是 memory-bound，也就越依赖融合</em>。"
          "这解释了一个常见困惑：<strong>「我换了个 FLOPs 只有一半的轻量 backbone，延迟怎么只降了 15%？」</strong>"
          "因为它本来就不受算力限制，你减的是它不缺的那个东西。"),
        H3("TensorRT 还做哪些图优化"),
        TABLE(["类别", "做什么", "典型收益"], [
            ["常量折叠", "把只依赖常量的子图在构建期算掉（BN 参数、reshape 的 shape 张量）", "去掉一批运行时无用节点"],
            ["<strong>垂直融合</strong>", "Conv+Bias+BN+激活 → 一个 CBR 层；ConvTranspose、FC 同理", "<strong>本节主角</strong>"],
            ["<strong>水平融合</strong>", "同一输入的多个同类卷积（Inception 分支、多头投影）合并成一个大卷积后再切分", "kernel 数下降、GEMM 变大更高效"],
            ["concat 消除", "让上游层直接写进 concat 输出的对应偏移，<strong>concat 本身消失</strong>", "省一整趟读写"],
            ["shuffle / transpose 消除", "相邻的 reshape/transpose 相互抵消或被吸进邻居的布局要求", "去掉纯访存层"],
            ["格式与精度重排（reformat）", "在布局/精度不匹配处<strong>插入</strong>转换层", "<strong>这是负收益</strong>，越少越好"],
        ]),
        CALLOUT("intuition", "一条可迁移的心法：<strong>融合的本质是把 memory-bound 的算子塞进 compute-bound 算子的 epilogue，"
                "让它们免费。</strong>凡是「算术强度低于 1」的算子（BN、激活、逐元素加、scale、cast），"
                "单独成 kernel 就是纯粹的带宽浪费。<em>你自己写模型时也该按这个标准判断："
                "新加的这个逐元素操作能不能被融进上一层？如果不能，它就要付一整趟 3 MB 的读写。</em>"),
    ])),

    # ============================================================== 5
    ("blockers", "什么阻止了融合：图优化的边界与写模型的纪律", "".join([
        P("融合是<strong>有前提的</strong>。前提被破坏时，TensorRT 不会报错、不会警告，只是安静地少融一次。"
          "<em>结果就是「一个看起来毫无问题的改动，让延迟涨了 20%」。</em>这一节把常见的阻断原因和它们的指纹列全。"),
        H3("最根本的一条：中间张量必须「用完即弃」"),
        P("Conv 的输出要能被融进 BN，前提是<strong>这个中间张量除了 BN 没有别的用途</strong>。一旦它有第二个消费者，"
          "或者它被标记成网络输出，TensorRT 就必须把它<em>实体化（materialize）</em>到显存里——"
          "而一旦要写出去，融合就没意义了。"),
        ASCII("""可以融合                              被阻断（中间张量有两个消费者）
──────────────                        ────────────────────────────────
  x                                     x
  │                                     │
 Conv                                  Conv
  │  ← 只有 BN 用它                     │  ← BN 用它，Add 也用它
 BN                                    ├──────────┐
  │                                    BN         │
 ReLU                                   │         │
  │                                   ReLU        │
  y                                     │         │
                                       Add ◄──────┘
 融合成 1 个 CBR 层                     Conv 的输出必须写回显存
 中间张量 0 次落显存                    → Conv+BN 融不了
                                       → 多一趟 3.28 MB 读 + 3.28 MB 写


事故形态：为了 debug 把中间张量 mark 成 output
  builder network 里多写一行 network->markOutput(bn_out)
  → 该张量必须实体化 → 融合链断在这里
  → **延迟涨 15~25%，没有任何报错，忘了删就上线了**"""),
        TABLE(["阻断原因", "指纹（怎么看出来）", "修法"], [
            ["<strong>中间张量有多个消费者</strong>", "layer info 里能看到独立的 <code>BatchNormalization</code> 层名",
             "改结构：把残差加在激活之后；或接受这次不融"],
            ["<strong>中间张量被 mark 成 output</strong>", "engine 的输出张量数比预期多",
             "<strong>发布前检查输出列表</strong>，debug 输出用单独的 debug engine"],
            ["激活函数不在支持列表", "激活成了独立层，或被拆成 <code>Sigmoid</code>+<code>Mul</code> 两层",
             "用标准算子（ReLU / LeakyReLU / Clip / Sigmoid / Tanh / HardSwish）；SiLU 要确认你的 TRT 版本能识别"],
            ["<strong>相邻层精度不同</strong>", "两层之间冒出 <code>Reformat</code> 层", "减少手工精度约束；混合精度按「连续块」划分而不是散点"],
            ["<strong>Q/DQ 位置不对（INT8）</strong>", "Reformat 层数量异常多、INT8 层反而变少",
             "遵循 TRT 的 Q/DQ 放置规则（见下一模块）"],
            ["中间插了 Reshape / Transpose / Slice", "conv 链被打断成多段", "把 shape 操作挪到图的两端；避免在 backbone 中段变换布局"],
            ["<strong>plugin 边界</strong>", "plugin 前后一定有独立层", "plugin 是黑盒，前后不能融——这是写 plugin 的隐性成本"],
            ["group / dilation 等特殊配置", "该融的没融", "查你的 TRT 版本的 fusion 支持矩阵，别想当然"],
        ]),
        DUAL(
            "怎么<em>知道</em>融合成没成？看层名。TensorRT 融合后的层名是把被融的层名拼起来的，"
            "形如 <code>conv1 + conv1/bn + conv1/relu</code>。<strong>所以只要 dump 一次 layer info，"
            "你就能一眼看出哪些层名是「一串」（融了）、哪些是「孤零零一个 BatchNormalization」（没融）。</strong>"
            "命令是 <code>trtexec --loadEngine=m.plan --dumpLayerInfo --profilingVerbosity=detailed "
            "--exportLayerInfo=layers.json</code>，然后写个十行的脚本统计层数、层名里的 <code>+</code> 个数、"
            "以及 <code>Reformat</code> 的占比。<em>这个脚本应该进 CI，作为性能回归的门禁之一。</em>",
            "更严谨地说，TensorRT 的融合是在其内部图上做<span class=\"term\">模式匹配（pattern matching）</span>+"
            "<strong>安全性检查</strong>：模式匹配决定「这几个层在结构上可以合并成哪个融合层」，安全性检查决定"
            "「合并之后语义是否仍然等价、以及中间结果是否真的不需要保留」。<em>后者依赖的是 use-def 分析："
            "只有当中间张量的 fan-out 恰好为 1 且它不在图的输出集合中，融合才被允许。</em>"
            "这与传统编译器里的 <span class=\"term\">operator fusion</span> / loop fusion 是同一套理论，"
            "区别只在于 TensorRT 的融合模式是硬编码的（vendor 手写的 kernel 模板库），"
            "而 TVM/XLA 这类编译器会做更一般的调度搜索。<strong>硬编码的好处是命中时性能极强，"
            "坏处是没命中你完全没法干预——这正是「写模型时就要照着融合规则写」的原因。</strong>",
        ),
        CALLOUT("danger", "<p><strong>真实事故形态，也是很好的面试故事素材</strong>：某次为了排查一个 badcase，"
                "工程师在导出脚本里多加了一个中间特征图作为输出，用完忘了删。"
                "<em>ONNX 对拍通过（数值完全正确）、精度评测通过（数值完全正确）、只有延迟涨了 18%。</em>"
                "因为没有人把「engine 层数」纳入回归门禁，这个改动一路走到了集成测试才被发现。"
                "<strong>教训：一致性检查只能抓「事故 A」，抓不到「事故 B」。你需要一条独立的、"
                "针对 engine 结构本身的门禁——层数、融合层占比、Reformat 层占比、FP32 层数、子图数。</strong></p>",
                "数值全对 + 延迟涨 18% = 融合被阻断"),
    ])),

    # ============================================================== 6
    ("autotune", "kernel auto-tuning：为什么构建要几十分钟", "".join([
        P("第一次跑 <code>trtexec</code> 的人几乎都会问同一个问题：<strong>「转换一个模型而已，为什么要等二十分钟？」</strong>"
          "答案是 TensorRT 根本不是在「转换」，它是在<strong>做实验</strong>。"),
        H3("builder 到底在忙什么"),
        P("对图中的每一个层，TensorRT 会枚举一批候选实现——这些候选叫 <span class=\"term\">tactic</span>，"
          "来源包括自带 kernel 库、cuDNN、cuBLAS、以及针对特定 shape/精度的专用实现。同一个 3×3 卷积，"
          "候选可能包括：implicit GEMM 的若干种 tile 划分、explicit GEMM + im2col、Winograd 变换、"
          "以及不同的数据布局（NCHW / NHWC / NC/32HW32 等 vectorized 格式）。<strong>然后它把每个候选"
          "在目标 GPU 上真的跑几遍、计时、取最快的那个。</strong>"),
        MATH("N_{\\text{timing}} \\;\\approx\\; \\underbrace{L}_{\\text{层数}} \\times \\underbrace{K}_{\\text{每层候选 tactic 数}} "
             "\\times \\underbrace{R}_{\\text{每个候选重复次数}} \\times \\underbrace{|\\mathcal{P}|}_{\\text{profile 数}}"),
        P("一个 200 层的检测器，每层 10–100 个候选，每个候选重复 3–8 次，单 profile——"
          "<strong>就是几万次真实的 kernel 计时</strong>。INT8 还要更多（更多候选 + 校准本身的前向）。"
          "所以构建时间从「小模型 1 分钟」到「大模型 + 多 profile + INT8 半小时以上」都是正常的。"),
        TABLE(["因素", "对构建时间的影响", "能不能省"], [
            ["层数 / 模型大小", "近似线性", "不能"],
            ["<strong>optimization profile 数</strong>", "<strong>近似线性倍增</strong>", "能——少用 profile，优先静态 shape"],
            ["INT8", "显著变慢（更多 tactic + 校准前向）", "校准结果可缓存复用"],
            ["<code>builderOptimizationLevel</code>（0–5）", "级别越高搜得越广、越慢", "<strong>能——CI 用低级别快速验证，发布用高级别</strong>"],
            ["<strong>timing cache</strong>", "命中后跳过计时", "<strong>能——二次构建可快 2–10×，CI 必用</strong>"],
            ["构建机的空闲程度", "不影响时长，<strong>影响结果质量</strong>", "必须用独占机器"],
        ]),
        CALLOUT("warn", "<p><strong>一个反直觉但极其重要的事实：同一个 ONNX，在同一块卡上构建两次，"
                "得到的 engine 性能可能差 3–5%。</strong>因为 tactic 选择依赖的是<em>实测计时</em>，"
                "而计时会被机器上的其他负载、时钟频率波动、温度扰动。如果两个候选的真实耗时只差 2%，"
                "噪声完全可能让 builder 选错。<em>这是 CI 里「性能测试 flaky」最常见的根因，"
                "而团队通常会误以为是测量环节的问题。</em></p>"
                "<p>缓解手段：①构建用独占机器、锁频（<code>nvidia-smi -lgc</code>）；②增加计时重复次数"
                "（<code>trtexec --avgTiming=8</code>）；③<strong>用 timing cache 把「已经选定的 tactic」冻住</strong>——"
                "这不只是省时间，更是<u>保证可复现</u>：同一份 cache + 同一份 ONNX 应当产出行为一致的 engine。</p>",
                "构建是有噪声的过程，engine 不是 ONNX 的确定性函数"),
        DUAL(
            "把 timing cache 想成「实验记录本」：<strong>(层配置的哈希) → (最优 tactic, 实测耗时)</strong>。"
            "下次构建时，遇到同样配置的层就直接查表，不用重跑实验。所以它能把二次构建时间砍掉一大半。"
            "<em>但记录本只在同一个实验室有效</em>——换 GPU 型号、换 TRT 版本、甚至换 CUDA 版本，cache 就该失效"
            "（TensorRT 会做校验并忽略不匹配的条目，不会给你错误结果，只是白建一次）。",
            "从工程流程看，timing cache 把「构建」从<strong>不确定过程</strong>推向<strong>可复现过程</strong>，"
            "这对量产链路是刚需：功能安全要求「同一份输入产出同一份二进制」，而 auto-tuning 天然违背这一点。"
            "<em>实践中的做法是：在一台锁频的构建机上生成 golden timing cache，把它作为构建产物之一"
            "纳入版本管理与签名，之后所有构建（包括 CI 和发布）都必须带上这份 cache。</em>"
            "<strong>这样 engine 就成了 (ONNX, builder config, timing cache, TRT 版本, 设备型号) 的确定性函数，"
            "而不是「那天那台机器碰巧的结果」。</strong>另有 <code>builderOptimizationLevel</code>（TRT 8.6+）"
            "把「搜索广度」显式暴露成一个 0–5 的旋钮：级别 0 构建极快但性能可能差不少，级别 5 反之——"
            "<em>这本质上是把「构建时间 vs 运行性能」的帕累托前沿交给你自己选点</em>。",
        ),
    ])),

    # ============================================================== 7
    ("hardware-lock", "engine 与硬件绑定：车端多平台的组合爆炸", "".join([
        P("上一节说清了 tactic 是在<em>目标设备上实测选出来</em>的，那么下面这条结论就是必然的："
          "<strong>engine 是一个硬件相关的产物，不是一个可移植的模型文件。</strong>"
          "这条性质在单卡的服务器场景里只是个小麻烦，在车端却直接决定了整条发布流水线的形状。"),
        H3("engine 绑定了什么"),
        TABLE(["绑定维度", "变了会怎样", "缓解手段与代价"], [
            ["<strong>GPU 架构（SM 版本）</strong>", "<strong>反序列化直接失败</strong>",
             "<code>HardwareCompatibilityLevel::kAMPERE_PLUS</code>：跨 Ampere+ 可移植，<strong>代价是只用架构通用 tactic，典型损失 5–15%</strong>"],
            ["具体型号（SM 数、带宽、L2 大小）", "通常能加载，但 tactic 不再最优，性能悄悄下降", "为每个型号单独构建（这是默认做法）"],
            ["<strong>TensorRT 版本</strong>", "<strong>反序列化失败</strong>（序列化格式与版本绑定）",
             "<code>BuilderFlag::VERSION_COMPATIBLE</code>：engine 内嵌 lean runtime，可跨版本加载；代价是体积变大、可能略慢"],
            ["CUDA / cuDNN 版本", "多数情况兼容，边缘情况会失败", "冻结整条工具链版本"],
            ["驱动版本", "有最低要求；低于要求则失败", "在车端镜像里固定驱动版本"],
            ["构建时的 builder config", "engine 行为不同（精度、profile 范围）", "配置纳入版本管理并随 engine 一起签名"],
        ]),
        P("<strong>「反序列化直接失败」其实是好事</strong>——这是一个<em>显式</em>的错误，会在集成阶段就被抓到。"
          "真正危险的是「能加载但不是最优」那一类：模型跑得起来、精度也对，只是比应有的慢 20%，"
          "而没有人会因为「慢 20%」去怀疑 engine 用错了。"),
        H3("车端的组合爆炸"),
        ASCII("""engine 矩阵 = 硬件平台 × 精度档 × 分辨率档 × 模型版本 × TRT 版本

  硬件平台     Orin-N (低配)  ·  Orin-X (中配)  ·  双 Orin (高配)  ·  Thor (新平台)
  精度档       FP16  ·  INT8
  分辨率档     960x540(省电)  ·  1280x720(标准)  ·  1920x1080(远距)
  模型版本     同时在路上的灰度版本可能有 2~3 个
  TRT 版本     升级期会有新旧两版并存

     4 × 2 × 3 = 24 个 engine / 每个模型版本
     × 3 个在网模型版本  =  72 个 engine
     × 构建 12 分钟      =  14.4 机器小时（串行）
     ÷ 6 台并行构建机    =  2.4 小时  ← 每次改模型都要付这个
     再 × TRT 一次小版本升级 = **全量重建 + 全量回归**

  存储与分发：72 × ~80 MB ≈ 5.8 GB，OTA 只能下发匹配当前硬件的那一个
  验证：**每一个 engine 都是独立的发布物，都要单独过精度与延迟门禁**""" ),
        P("这张账最重要的一行是最后一行。<strong>「一份权重」不等于「一次验证」</strong>——"
          "engine 是硬件相关的，所以每一个 (平台, 精度, 分辨率) 组合都必须独立跑完整评测："
          "融合结果可能不同、tactic 不同、INT8 的 scale 甚至可能因为校准在不同平台重跑而不同。"
          "<em>这是很多团队在第一次上多硬件平台时严重低估的成本。</em>"),
        DUAL(
            "有没有办法只发 ONNX，让车在首次开机时自己构建？<strong>有团队这么做，但要非常小心。</strong>"
            "构建要十几分钟、要占用显存与算力、结果还带 3–5% 的随机性；"
            "<em>如果构建恰好在用户第一次上车时发生，那就是十几分钟的「感知功能不可用」</em>。"
            "现实做法通常是折中：出厂时预置一份 engine，OTA 下发时优先用云端构建好的匹配版本，"
            "只有在遇到未预见的硬件/驱动组合时才回退到车端构建，并且必须有明确的降级策略与用户提示。",
            "从发布工程的角度看，engine 的硬件绑定把模型交付从「分发一个文件」变成了"
            "<strong>「分发一个按 (硬件指纹, 软件版本) 索引的产物矩阵」</strong>。这需要三件基础设施："
            "<em>①硬件指纹采集</em>（车端上报 SoC 型号、驱动、TRT 版本，服务端据此选包）；"
            "<em>②产物血缘</em>（每个 engine 必须能回溯到 ONNX 哈希、权重哈希、builder config、timing cache、构建机标识）；"
            "<em>③回退路径</em>（匹配不到时用哪个更保守的 engine，或退回到 FP16 版本）。"
            "<strong>值得注意的是，<code>VERSION_COMPATIBLE</code> 与 <code>HardwareCompatibilityLevel</code> "
            "这两个选项本质上是在「用性能买维护性」</strong>——把 24 个 engine 压成 6 个，代价是每个都慢 5–15%。"
            "<em>这个交换划不划算，取决于你的延迟预算还剩多少余量，以及你的发布团队有多大。</em>",
        ),
        CALLOUT("danger", "<p><strong>面试题：「为什么不能把开发机上建好的 engine 直接拷到车上？」</strong>"
                "这题看着简单，但答得完整的人不多。骨架：<em>①engine 是 builder 在<u>目标设备上实测计时</u>后产出的执行计划，"
                "tactic 选择依赖 SM 版本、SM 数量、显存带宽、L2 大小——这些换台机器就变了；"
                "②序列化格式与 TensorRT 版本绑定，跨版本反序列化会失败；"
                "③还绑驱动的最低版本；④即使 TRT 提供了 version-compatible 与 hardware-compatible 模式，"
                "它们是用「只选架构通用 tactic」换来的可移植性，典型要付 5–15% 的性能</em>。"
                "<strong>加分点是主动补上工程后果：所以 engine 是 (硬件, 软件版本) 索引的产物矩阵，"
                "TRT 版本升级 = 全量重建 + 全量回归，这就是为什么量产上 TRT 版本升级频率极低。</strong></p>",
                "答完机制，还要答工程后果"),
    ])),

    # ============================================================== 8
    ("fallback", "静默回退、plugin，与 trtexec 的常用姿势", "".join([
        P("本模块开头的「事故 B」——<strong>转了 TRT 但没变快</strong>——最常见的成因不是融合被阻断，"
          "而是<span class=\"term\">静默回退（silent fallback）</span>：一部分图根本没跑在 TensorRT 上。"),
        H3("静默回退的两种形态"),
        OL([
            "<strong>算子级回退（分区）</strong>：你用的是 <code>torch-tensorrt</code> / <code>TF-TRT</code> / "
            "<code>onnxruntime</code> 的 TensorRT EP 这类<em>分区式集成</em>。它们把图切成"
            "「TRT 能跑的子图」和「交回原框架的子图」。模型能跑、数值也对，"
            "<strong>但每个子图边界都意味着一次同步、可能还有一次内存拷贝与布局转换</strong>。"
            "被切成 30 个子图的模型，比切成 1 个子图的慢一倍毫不稀奇。",
            "<strong>精度级回退</strong>：你开了 FP16/INT8，但因为缺 scale、因为 reformat 代价太高、"
            "或因为该层没有对应精度的实现，TRT 把它留在了更高精度上。"
            "<em>症状是「精度一点没掉」——听起来是好消息，实际是没量化上。</em>",
        ]),
        H3("怎么看：三个必须进 CI 的数字"),
        TABLE(["指标", "健康值", "怎么拿", "不健康说明什么"], [
            ["<strong>子图数</strong>", "<strong>= 1</strong>", "ORT-TRT EP 的日志 / <code>ORT_TENSORRT_DUMP_SUBGRAPHS=1</code>；"
             "torch-tensorrt 的 partitioning 报告", "有算子没被支持，正在走慢路径"],
            ["<strong>非目标精度的层数</strong>", "接近 0（纯 FP16 目标下）",
             "<code>trtexec --dumpLayerInfo --profilingVerbosity=detailed</code> 里每层的 <code>Precision</code>",
             "精度标志没真正生效"],
            ["<strong>Reformat 层占比</strong>", "<strong>&lt; 5% 的耗时</strong>",
             "<code>--dumpProfile --separateProfileRun</code> 逐层耗时", "精度/布局在层间反复切换，收益被吃光"],
            ["融合层占比", "多数层名里含 <code>+</code>", "层名统计脚本", "融合被阻断（第 5 节）"],
            ["engine 层数 vs ONNX 节点数", "engine 层数应<strong>显著少于</strong> ONNX 节点数", "两边分别统计", "几乎没优化发生"],
        ]),
        H3("trtexec 常用姿势"),
        CODE("""# ① 构建（静态 shape，最简）
trtexec --onnx=det.onnx --saveEngine=det.plan --fp16 \\
        --memPoolSize=workspace:2048 \\
        --timingCacheFile=tc.cache --avgTiming=8 \\
        --builderOptimizationLevel=3

# ② 构建（动态 shape：三档必须都给，且要给到每个动态输入）
trtexec --onnx=det.onnx --saveEngine=det.plan --fp16 \\
        --minShapes=images:1x3x640x640 \\
        --optShapes=images:1x3x640x640 \\
        --maxShapes=images:4x3x640x640

# ③ 强制精度约束（做混合精度时用 obey，不满足就构建失败）
trtexec --onnx=det.onnx --saveEngine=det.plan --fp16 --int8 \\
        --precisionConstraints=obey \\
        --layerPrecisions=head_reg.*:fp16,backbone.stem.*:fp16

# ④ 逐层耗时剖析（找瓶颈层、找 Reformat）
trtexec --loadEngine=det.plan --shapes=images:1x3x640x640 \\
        --warmUp=1000 --iterations=2000 --avgRuns=10 \\
        --dumpProfile --separateProfileRun \\
        --exportProfile=prof.json --exportLayerInfo=layers.json \\
        --profilingVerbosity=detailed

# ⑤ 只测 GPU 计算、不含拷贝（注意：这个数字会比端到端好看很多）
trtexec --loadEngine=det.plan --noDataTransfers --useCudaGraph

# ⑥ 让 TRT 自己在 fp16/int8 里挑（快速摸上限用，不要直接拿去发布）
trtexec --onnx=det.onnx --best"""),
        CALLOUT("warn", "<p><strong><code>--noDataTransfers</code> 是延迟数字被「美化」的头号来源。</strong>"
                "它测的是纯 GPU 计算，不含 H2D/D2H 拷贝。而在车端，输入是 1920×1080×3 的图，"
                "<em>H2D 拷贝本身就可能占端到端的 10–30%</em>。"
                "供应商与论文报的 FPS 常常就是这个口径，再加上 batch&gt;1、不含预处理、不含 NMS。"
                "<strong>拿这个数字去做延迟预算，上车必然超时。</strong>本课模块 05 会给端到端测量的正确姿势。</p>",
                "别用 --noDataTransfers 的数字做预算"),
        H3("plugin：什么时候不得不自己写"),
        P("当某个算子既不在 ONNX opset 里、TRT 也不原生支持时，你有四条路，<strong>请严格按这个顺序尝试</strong>："),
        OL([
            "<strong>改模型</strong>——用等价的标准算子重写。代价最小，但要重训或至少重新验证数值等价。",
            "<strong>用等价算子组合</strong>——比如把自定义插值拆成 <code>Resize</code>+<code>Slice</code>。"
            "代价：可能引入额外访存，且组合出来的图未必能融合。",
            "<strong>用官方/开源 plugin</strong>——TensorRT OSS 仓库里有 <code>EfficientNMS_TRT</code>、"
            "<code>MultiscaleDeformableAttnPlugin</code>（<em>RT-DETR / Deformable DETR 的救命稻草</em>）、"
            "<code>GroupNorm</code>、<code>InstanceNormalization</code> 等。代价：要确认版本匹配、要自己编译进 runtime。",
            "<strong>自己写</strong>——最后的选择。要实现前向 CUDA kernel、序列化/反序列化、"
            "动态 shape 支持（<code>IPluginV2DynamicExt</code> / 新版 <code>IPluginV3</code>）、"
            "多精度支持、以及 <code>enqueue</code> 的流语义。<em>而且 plugin 是融合黑洞：它前后一定断开，"
            "所以一个写得很快的 plugin 也可能因为打断了融合链而净亏。</em>",
        ]),
        DUAL(
            "TSR 场景里这条决策链非常具体。如果你选了 <strong>RT-DETR</strong>（C53 模块 04），"
            "它的可变形注意力依赖 <code>grid_sample</code>——<em>这在部分后端要 plugin</em>。"
            "RT-DETRv2 把它换成离散采样正是为了绕开这一点。"
            "如果你选了 YOLO/RTMDet 系，主干全是标准卷积，唯一需要考虑的是"
            "<strong>要不要把 NMS 用 <code>EfficientNMS_TRT</code> 塞进 engine</strong>——"
            "塞进去可以省一次 D2H 拷贝和 CPU 后处理，但也把「NMS 的实现细节」冻进了 engine，"
            "以后想改 IoU 阈值语义就得重建。",
            "更一般地，plugin 的真实成本不在写它的那两天，在<strong>它的生命周期</strong>："
            "<em>①跨 TRT 版本的 API 迁移</em>（<code>IPluginV2Ext</code> → <code>IPluginV2DynamicExt</code> → "
            "<code>IPluginV3</code>，每次大版本都可能要改）；<em>②每个目标平台都要交叉编译并验证</em>；"
            "<em>③它是融合边界，会永久性地把图切成两半</em>；<em>④它是数值一致性的额外风险点</em>"
            "（你自己写的 CUDA kernel 与 PyTorch 参考实现的浮点行为未必一致，需要单独对拍）；"
            "<em>⑤功能安全审查时它是一段需要单独论证的自研代码</em>。"
            "<strong>所以「能不写就不写」不是懒，是正确的工程判断——选模型架构时就应该把"
            "「需要几个自定义 plugin」当作一个选型指标。</strong>",
        ),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("TensorRT 代表的是「vendor 手写 kernel 库 + 实测搜索」这条路线。它的边界在哪、会被什么取代，"
          "是一个仍然在演进的问题。"),
        UL([
            "<strong>搜索式编译 vs 手写库。</strong>TVM/Ansor、XLA、Triton、torch.compile+Inductor 走的是"
            "「自动生成 kernel + 代价模型/实测搜索调度」，TensorRT 走的是「手写高度优化的模板库 + 在模板间选」。"
            "<em>前者覆盖面广、能处理新算子，后者在覆盖到的算子上通常更快</em>。"
            "开放问题：随着模型算子越来越多样（各种 attention 变体、状态空间模型），手写库的覆盖率还能撑多久？",
            "<strong>用学习到的代价模型替代实测计时。</strong>TVM 的 AutoTVM/Ansor 已经在做，"
            "TensorRT 的 <code>builderOptimizationLevel</code> 可以看成一个粗粒度的简化版。"
            "<em>如果代价模型足够准，构建时间可以从几十分钟降到几十秒，而且构建结果变成确定性的</em>——"
            "这对量产发布流水线的价值可能比性能本身还大。",
            "<strong>可移植性与性能的根本张力。</strong>hardware-compatible engine 要付 5–15% 的性能。"
            "这个损失是本质的（不同架构的最优 tactic 就是不同）还是可以靠更好的抽象消掉的？"
            "<em>目前没有令人满意的答案，而车端多硬件平台恰恰最需要这个答案。</em>",
            "<strong>融合的粒度正在上移。</strong>FlashAttention 类工作把整个 attention（含 softmax 与在线归一化）"
            "融成一个 kernel，这已经超出了「图级模式匹配」能表达的范围——"
            "<em>它需要算法层面的重写（分块 + 在线 softmax），而不只是把相邻算子合并</em>。"
            "开放问题：如何让编译器自动发现这类需要改变数值算法的融合？这可能需要 kernel 级 DSL 与形式化的重写规则。",
            "<strong>engine 的数值等价性论证。</strong>怎么向功能安全审查证明「这个 engine 与训练时的模型行为一致」？"
            "FP16/INT8 下「等价」本身就没有明确定义。<em>目前的实践是统计性的（大样本上的输出分布对比 + 指标不降），"
            "但形式化的边界证明（如给定输入范围下输出误差的上界）在检测模型上仍然做不到。</em>",
            "<strong>构建即代码（build-as-code）与产物血缘。</strong>engine 是 "
            "(ONNX, config, timing cache, TRT 版本, 设备型号, 构建机状态) 的函数，其中最后一项还是随机的。"
            "<em>如何把这个函数变成可复现、可审计、可签名的流水线</em>，是部署工程里比调 tactic 更重要、"
            "却极少被论文讨论的问题。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读（工程文档优先于论文）</strong>："
                "NVIDIA, <em>TensorRT Developer Guide</em> —— 重点读 “Working with Dynamic Shapes”（optimization profile 的完整语义）、"
                "“How TensorRT Works / Layer Fusion”（融合规则表，注意它随版本变化）、"
                "“Performance Best Practices”（workspace、timing cache、精度约束）。"
                "<strong>★</strong> NVIDIA, <em>trtexec 文档与 TensorRT OSS 仓库</em> —— "
                "plugin 的参考实现（<code>EfficientNMS_TRT</code>、<code>MultiscaleDeformableAttnPlugin</code>）"
                "是理解「plugin 到底要写什么」的最快途径。</p>"
                "<p>编译器视角的背景阅读：Chen et al., <em>TVM: An Automated End-to-End Optimizing Compiler for Deep Learning</em>"
                "（OSDI 2018）——图级 + 算子级两层优化的经典框架；Zheng et al., <em>Ansor: Generating High-Performance "
                "Tensor Programs for Deep Learning</em>（OSDI 2020）——搜索式调度；"
                "Ragan-Kelley et al., <em>Halide</em>（PLDI 2013）——「算法与调度分离」这一思想的源头；"
                "Tillet et al., <em>Triton</em>（MAPL 2019）——kernel 级 DSL；"
                "Dao et al., <em>FlashAttention</em>（NeurIPS 2022）——需要改变数值算法的融合；"
                "Jia et al., <em>TASO</em>（SOSP 2019）——自动生成并验证图重写规则。"
                "相邻课程：C52 模块 03（ONNX 导出与算子不支持的四条出路）、本课模块 01（预处理一致性）、"
                "模块 03（INT8 校准）、模块 04（后处理与 C++ 管线）、模块 05（延迟剖析与 p99）、"
                "C53 模块 05（为什么论文的 FPS 不可信）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · TensorRT 构建与优化（迷你图 IR / 融合规则引擎 / 动态 shape profile / engine 矩阵）

目标：把 TensorRT 里最不透明的三件事——**层融合**、**动态 shape 的代价**、**engine 与硬件的绑定**——
用可运行的数值钉死。全程纯 numpy，不装 TensorRT，也不需要 GPU。

本 notebook 你会亲手实现：
1. **numpy 版 Conv / BN / ReLU**，并给出 **Conv+BN 融合的数值等价证明**（`np.allclose` 到 $10^{-12}$）
2. 一个**迷你图 IR**（Node / Graph / 拓扑执行）+ **融合规则引擎**（模式匹配 + use-def 安全性检查）
3. **什么阻止了融合**：多消费者、debug 输出——两种阻断各构造一个图，跑出来看
4. **roofline 代价模型**：融合前后的 FLOPs / 访存字节 / 算术强度 / 估计耗时
   → 得到关键结论：**融合对标准卷积只值 ~9%，对 depthwise 值 ~67%**
5. **动态 shape 的 optimization profile**：代价模型 + **动态规划求最优 k 档切分**
6. **构建时间 × 硬件矩阵**的组合爆炸计算，以及 engine 兼容性检查器

> 心智模型：**ONNX 说「模型是什么」，engine 说「这块芯片打算怎么做」。两者的节点根本不是一一对应的。**"""),

    md("""## 1 · numpy 版算子与 Conv+BN 融合的数值等价

先把三个算子写出来。卷积用最朴素的七重循环展开（小尺寸够用，胜在一眼能看懂）。

融合公式（模块正文第 4 节）：

$$\\tilde W_o = \\frac{\\gamma_o}{\\sqrt{\\sigma_o^2+\\epsilon}}W_o,\\qquad
  \\tilde b_o = \\frac{\\gamma_o (b_o-\\mu_o)}{\\sqrt{\\sigma_o^2+\\epsilon}} + \\beta_o$$

**这是恒等变换，不是近似。**"""),

    code("""import numpy as np, math, copy
np.set_printoptions(precision=4, suppress=True)
rng = np.random.default_rng(0)

def conv2d(x, w, b, stride=1, pad=1, groups=1):
    \"\"\"x:(C,H,W)  w:(O, C//groups, kh, kw)  b:(O,)  ->  (O,Ho,Wo)\"\"\"
    C, H, W = x.shape
    O, Cg, kh, kw = w.shape
    assert C == Cg * groups and O % groups == 0
    xp = np.pad(x, ((0, 0), (pad, pad), (pad, pad)))
    Ho = (H + 2 * pad - kh) // stride + 1
    Wo = (W + 2 * pad - kw) // stride + 1
    out = np.zeros((O, Ho, Wo))
    ocpg = O // groups
    for o in range(O):
        cs = (o // ocpg) * Cg                      # 该输出通道所属 group 的输入通道起点
        acc = np.zeros((Ho, Wo))
        for c in range(Cg):
            for i in range(kh):
                for j in range(kw):
                    acc += w[o, c, i, j] * xp[cs + c,
                                              i:i + Ho * stride:stride,
                                              j:j + Wo * stride:stride]
        out[o] = acc + b[o]
    return out

def batchnorm(x, gamma, beta, mean, var, eps=1e-5):
    \"\"\"推理期 BN：逐通道仿射，running stats 已冻结\"\"\"
    s = gamma / np.sqrt(var + eps)
    return x * s[:, None, None] + (beta - mean * s)[:, None, None]

def relu(x):
    return np.maximum(x, 0.0)

def fuse_conv_bn(w, b, gamma, beta, mean, var, eps=1e-5):
    \"\"\"把推理期 BN 吸进上一层卷积的权重与偏置里。返回 (w_new, b_new)。\"\"\"
    s = gamma / np.sqrt(var + eps)
    return w * s[:, None, None, None], (b - mean) * s + beta

print('✅ 算子就位：conv2d / batchnorm / relu / fuse_conv_bn')"""),

    code("""# —— 数值等价验证：随机权重 + 随机输入 ——
C_IN, C_OUT, K, HW = 16, 16, 3, 16
x  = rng.standard_normal((C_IN, HW, HW))
W  = rng.standard_normal((C_OUT, C_IN, K, K)) * 0.15
B  = rng.standard_normal(C_OUT) * 0.1
gm = rng.uniform(0.5, 1.8, C_OUT)
bt = rng.standard_normal(C_OUT) * 0.3
mu = rng.standard_normal(C_OUT) * 0.4
va = rng.uniform(0.2, 2.5, C_OUT)

y_ref = batchnorm(conv2d(x, W, B), gm, bt, mu, va)          # Conv 然后 BN
W2, B2 = fuse_conv_bn(W, B, gm, bt, mu, va)
y_fus = conv2d(x, W2, B2)                                   # 融合成一个 Conv

err = np.abs(y_ref - y_fus).max()
print('两条路径的最大逐元素误差 =', err)
assert np.allclose(y_ref, y_fus, atol=1e-11), err
assert err < 1e-11

# 手算一个单通道例子，确认公式方向没搞反
w1 = np.array([[[[2.0]]]]); b1 = np.array([1.0])
g1 = np.array([3.0]); be1 = np.array([0.5]); m1 = np.array([4.0]); v1 = np.array([4.0 - 1e-5])
x1 = np.array([[[5.0]]])
# conv: 2*5+1 = 11 ; bn: 3*(11-4)/2 + 0.5 = 11.0
w1f, b1f = fuse_conv_bn(w1, b1, g1, be1, m1, v1)
print('手算：s=3/2=1.5, W~=2*1.5=%.4f, b~=(1-4)*1.5+0.5=%.4f' % (w1f[0,0,0,0], b1f[0]))
assert abs(w1f[0, 0, 0, 0] - 3.0) < 1e-6
assert abs(b1f[0] - (-4.0)) < 1e-6
assert abs(conv2d(x1, w1f, b1f, pad=0)[0, 0, 0] - 11.0) < 1e-6
print('✅ Conv+BN 融合是**严格恒等**（浮点舍入除外）——这就是 TensorRT 敢无条件做它的原因。')
print('   同一套代数还支撑：RepVGG 的重参数化（C53 m01）与 QAT 里的 BN folding（下一模块）。')"""),

    md("""## 2 · 迷你图 IR：Node / Graph / 拓扑执行

一个能表达 ONNX 子集的最小 IR。关键在于 `Graph` 要显式记住 **outputs**——
后面判断「能不能融合」时，「这个张量是不是图的输出」是决定性条件之一。"""),

    code("""class Node:
    def __init__(self, name, op, inputs, outputs, attrs=None):
        self.name, self.op = name, op
        self.inputs, self.outputs = list(inputs), list(outputs)
        self.attrs = dict(attrs or {})
    def __repr__(self):
        return '<%s %s>' % (self.op, self.name)

class Graph:
    def __init__(self, nodes, inputs, outputs, inits=None):
        self.nodes = list(nodes)          # 假定已是拓扑序
        self.inputs, self.outputs = list(inputs), list(outputs)
        self.inits = dict(inits or {})    # 常量（权重）
    def clone(self):
        return copy.deepcopy(self)
    def op_count(self):
        d = {}
        for n in self.nodes:
            d[n.op] = d.get(n.op, 0) + 1
        return d

def run_graph(g, feed):
    env = dict(g.inits); env.update(feed)
    for n in g.nodes:
        xs = [env[t] for t in n.inputs]
        if n.op == 'Conv':
            y = conv2d(xs[0], xs[1], xs[2], n.attrs.get('stride', 1),
                       n.attrs.get('pad', 1), n.attrs.get('groups', 1))
            if n.attrs.get('act') == 'relu':          # 融合进来的激活
                y = relu(y)
        elif n.op == 'BatchNormalization':
            y = batchnorm(xs[0], xs[1], xs[2], xs[3], xs[4], n.attrs.get('eps', 1e-5))
        elif n.op == 'Relu':
            y = relu(xs[0])
        elif n.op == 'Add':
            y = xs[0] + xs[1]
        else:
            raise ValueError('unknown op ' + n.op)
        env[n.outputs[0]] = y
    return {t: env[t] for t in g.outputs}

def consumers(g, t):
    return [n for n in g.nodes if t in n.inputs]

print('✅ 迷你 IR 就位')"""),

    code("""def make_block(i, tin, tout, inits, c=16, k=3, groups=1):
    \"\"\"造一个 Conv->BN->ReLU 三件套，返回 3 个 Node，并把权重写进 inits\"\"\"
    r = np.random.default_rng(100 + i)
    cg = c // groups
    inits['w%d' % i]  = r.standard_normal((c, cg, k, k)) * 0.12
    inits['b%d' % i]  = r.standard_normal(c) * 0.05
    inits['g%d' % i]  = r.uniform(0.6, 1.6, c)
    inits['be%d' % i] = r.standard_normal(c) * 0.2
    inits['m%d' % i]  = r.standard_normal(c) * 0.3
    inits['v%d' % i]  = r.uniform(0.3, 2.0, c)
    t1, t2 = 'c%d_out' % i, 'bn%d_out' % i
    return [
        Node('conv%d' % i, 'Conv', [tin, 'w%d' % i, 'b%d' % i], [t1],
             {'pad': k // 2, 'groups': groups}),
        Node('bn%d' % i, 'BatchNormalization',
             [t1, 'g%d' % i, 'be%d' % i, 'm%d' % i, 'v%d' % i], [t2]),
        Node('relu%d' % i, 'Relu', [t2], [tout]),
    ]

def make_chain(n_blocks=6, c=16):
    inits, nodes, t = {}, [], 'x'
    for i in range(n_blocks):
        tout = 'y%d' % i
        nodes += make_block(i, t, tout, inits, c=c)
        t = tout
    return Graph(nodes, ['x'], [t], inits)

G = make_chain(6)
X = {'x': rng.standard_normal((16, 16, 16))}
out_ref = run_graph(G, X)['y5']
print('链式图：%d 个节点  %s' % (len(G.nodes), G.op_count()))
print('输出形状', out_ref.shape, ' 均值 %.4f' % out_ref.mean())
assert len(G.nodes) == 18 and G.op_count() == {'Conv': 6, 'BatchNormalization': 6, 'Relu': 6}
print('✅ 一个 6 block 的骨干：ONNX 里是 18 个节点。engine 里应该是几个？下一节见分晓。')"""),

    md("""## 3 · 融合规则引擎：模式匹配 + use-def 安全性检查

规则只有两条，但**安全性检查才是重点**：

- `Conv → BatchNormalization`（且 Conv 尚未吸收激活）→ 合并权重，BN 消失
- `Conv → Relu` → 把激活写进 Conv 的 `act` 属性，Relu 消失

**安全性条件（两条都要满足，缺一不可）**：中间张量的消费者数 == 1，且它不是图的输出。"""),

    code("""def fusible(g, t):
    \"\"\"张量 t 能否被「吃掉」：唯一消费者 且 不是图输出\"\"\"
    return len(consumers(g, t)) == 1 and t not in g.outputs

def blocked_reason(g, t):
    if t not in [o for n in g.nodes for o in n.outputs]:
        return '不是中间张量'
    if t in g.outputs:
        return '是图的输出 -> 必须实体化'
    k = len(consumers(g, t))
    if k > 1:
        return '有 %d 个消费者 -> 必须实体化' % k
    if k == 0:
        return '没有消费者（死张量）'
    return ''

def fuse_graph(g):
    \"\"\"反复应用融合规则直到不动点。返回 (新图, 融合日志)\"\"\"
    g, log = g.clone(), []
    changed, uid = True, 0
    while changed:
        changed = False
        for n in list(g.nodes):
            if n.op != 'Conv' or n.attrs.get('act') is not None:
                continue
            t = n.outputs[0]
            if not fusible(g, t):
                continue
            c = consumers(g, t)[0]
            if c.op == 'BatchNormalization':
                W, B = g.inits[n.inputs[1]], g.inits[n.inputs[2]]
                gm, bt, mu, va = [g.inits[k] for k in c.inputs[1:5]]
                W2, B2 = fuse_conv_bn(W, B, gm, bt, mu, va, c.attrs.get('eps', 1e-5))
                uid += 1
                nw, nb = 'w_f%d' % uid, 'b_f%d' % uid
                g.inits[nw], g.inits[nb] = W2, B2
                n.inputs[1], n.inputs[2] = nw, nb
                n.outputs[0] = c.outputs[0]
                n.name = n.name + ' + ' + c.name
                g.nodes.remove(c); log.append(('Conv+BN', n.name)); changed = True
            elif c.op == 'Relu':
                n.attrs['act'] = 'relu'
                n.outputs[0] = c.outputs[0]
                n.name = n.name + ' + ' + c.name
                g.nodes.remove(c); log.append(('Conv+Act', n.name)); changed = True
    return g, log

print('✅ 融合规则引擎就位（2 条规则 + 2 条安全性条件）')"""),

    code("""GF, log = fuse_graph(G)
out_fus = run_graph(GF, X)['y5']

print('融合前：%2d 个节点  %s' % (len(G.nodes), G.op_count()))
print('融合后：%2d 个节点  %s' % (len(GF.nodes), GF.op_count()))
print()
print('engine 里的层名（TensorRT 就是这样把被融的层名拼起来的）：')
for n in GF.nodes:
    print('   ', n.name)

err = np.abs(out_ref - out_fus).max()
print()
print('融合前后输出的最大误差 =', err)
assert np.allclose(out_ref, out_fus, atol=1e-11), err
assert len(GF.nodes) == 6 and GF.op_count() == {'Conv': 6}
assert len(log) == 12                       # 6 次 Conv+BN + 6 次 Conv+Act
print('✅ 18 个 ONNX 节点 -> 6 个 engine 层，数值完全一致。')
print('   **拿 ONNX 节点数去猜 engine 性能，方向就是错的。**')"""),

    md("""## 4 · 什么阻止了融合：两种阻断，各造一个图

- **阻断 A：中间张量有两个消费者**（残差分支直接接在 BN 输出上）
- **阻断 B：中间张量被 mark 成图的输出**（为了 debug 多导出了一个特征图）

两种都**不会报错**，只会安静地少融一次。"""),

    code("""def make_residual_graph():
    \"\"\"conv0 -> bn0 -> relu0 -> ... 但 bn0 的输出**同时**被 Add 用掉\"\"\"
    inits = {}
    nodes = make_block(0, 'x', 'r0', inits)          # conv0/bn0/relu0，relu0 输出 r0
    nodes.append(Node('add0', 'Add', ['r0', 'bn0_out'], ['y']))
    return Graph(nodes, ['x'], ['y'], inits)

def make_debug_graph():
    \"\"\"完全正常的链，只是有人为了 debug 把 conv0 的输出也 mark 成了图输出\"\"\"
    inits = {}
    nodes = make_block(0, 'x', 'y', inits)
    return Graph(nodes, ['x'], ['y', 'c0_out'], inits)   # ← 多了一个输出

for name, g in [('① 正常链', make_chain(1)),
                ('② 残差接在 BN 输出上', make_residual_graph()),
                ('③ 多 mark 了一个 debug 输出', make_debug_graph())]:
    gf, _ = fuse_graph(g)
    print('%-24s 融合前 %2d 层 -> 融合后 %2d 层   %s'
          % (name, len(g.nodes), len(gf.nodes), gf.op_count()))
    for n in g.nodes:
        t = n.outputs[0]
        r = blocked_reason(g, t)
        print('        %-8s -> %-9s : %s' % (n.name, t, r or '可被下游吃掉 ✅'))
    print()

g1f, _ = fuse_graph(make_chain(1))
g2f, _ = fuse_graph(make_residual_graph())
g3f, _ = fuse_graph(make_debug_graph())
assert len(g1f.nodes) == 1                       # Conv
assert g2f.op_count().get('BatchNormalization', 0) == 0 and g2f.op_count()['Relu'] == 1
assert g3f.op_count()['BatchNormalization'] == 1  # Conv+BN 被 debug 输出挡住了
print('结论：')
print('  ② BN 的输出有 2 个消费者 -> Conv+BN 仍能融，但 **ReLU 融不进去**')
print('  ③ Conv 的输出被 mark 成图输出 -> **Conv+BN 直接融不了**')
print('⚠️  两种情况数值都完全正确、都不报错。**只有延迟会告诉你出事了。**')"""),

    md("""## 5 · roofline 代价模型：融合到底省了多少

$$t_{\\text{layer}} \\approx \\max\\!\\left(\\frac{\\text{FLOPs}}{P_{\\text{peak}}},\\ \\frac{\\text{Bytes}}{B_{\\text{mem}}}\\right) + t_{\\text{launch}}$$

用一个典型边缘 SoC 的参数：**10 TFLOPS FP16 + 200 GB/s 带宽 + 5 µs kernel launch**。"""),

    code("""PEAK   = 10e12      # FLOP/s (FP16)
BW     = 200e9      # B/s
LAUNCH = 5e-6       # s，每个 kernel 的启动开销
DB     = 2          # FP16 每元素字节数

def roofline_us(flops, byts, peak=PEAK, bw=BW, launch=LAUNCH):
    return (max(flops / peak, byts / bw) + launch) * 1e6

def conv_cost(H, W, cin, cout, k, groups=1):
    cg = cin // groups
    flops = 2 * H * W * cout * cg * k * k
    byts  = (H * W * cin + H * W * cout + cout * cg * k * k) * DB
    return flops, byts

def elem_cost(H, W, c, ops_per_elem):
    \"\"\"逐元素算子：算 ops_per_elem 次，读一遍写一遍\"\"\"
    return float(H * W * c * ops_per_elem), float(2 * H * W * c * DB)

H = W = 80; C = 256
cases = {
    '3x3 标准卷积 256->256': conv_cost(H, W, C, C, 3, groups=1),
    '5x5 depthwise  256':    conv_cost(H, W, C, C, 5, groups=C),
}
bn_f, bn_b   = elem_cost(H, W, C, 2)
rl_f, rl_b   = elem_cost(H, W, C, 1)

print('%-24s %10s %10s %10s %12s %12s %8s' %
      ('层', 'GFLOPs', 'MB(拆开)', 'MB(融合)', 'AI(拆开)', 'AI(融合)', '省%'))
saving = {}
for name, (f, b) in cases.items():
    f_un, b_un = f + bn_f + rl_f, b + bn_b + rl_b
    t_un = roofline_us(f, b) + roofline_us(bn_f, bn_b) + roofline_us(rl_f, rl_b)
    t_fu = roofline_us(f_un, b)                       # 融合后：一趟访存，算力照旧
    saving[name] = (t_un, t_fu, 1 - t_fu / t_un)
    print('%-24s %10.3f %10.2f %10.2f %12.1f %12.1f %7.0f%%' %
          (name, f / 1e9, b_un / 1e6, b / 1e6, f_un / b_un, f_un / b, 100 * (1 - t_fu / t_un)))

print()
print('%-24s %14s %14s' % ('层', '拆成 3 个 kernel', '融合成 1 个'))
for name, (t_un, t_fu, s) in saving.items():
    print('%-24s %12.1f µs %12.1f µs' % (name, t_un, t_fu))

s_std = saving['3x3 标准卷积 256->256'][2]
s_dw  = saving['5x5 depthwise  256'][2]
assert 0.05 < s_std < 0.15, s_std
assert 0.60 < s_dw  < 0.75, s_dw
print()
print('⚠️  **同一个融合，对标准卷积值 %.0f%%，对 depthwise 值 %.0f%%。**' % (100 * s_std, 100 * s_dw))
print('   因为 depthwise 本来就是 memory-bound（算术强度只有 %.1f）——'
      % (cases['5x5 depthwise  256'][0] / cases['5x5 depthwise  256'][1]))
print('   它不缺算力，缺带宽，而融合省的正是带宽。')
print('   推论：**越是为「FLOPs 少」设计的轻量模型，越依赖融合，也越怕融合被阻断。**')"""),

    code("""# 把代价模型接到图上：估计整张图的延迟，并量化两种阻断的代价
def graph_latency_us(g, H=80, W=80, C=256, k=3, groups=1):
    ef, eb = elem_cost(H, W, C, 2)          # BN
    af, ab = elem_cost(H, W, C, 1)          # ReLU
    tot = 0.0
    for n in g.nodes:
        if n.op == 'Conv':
            f, b = conv_cost(H, W, C, C, k, groups)
            if n.attrs.get('act') == 'relu':
                f += af                      # 激活融进 epilogue：多算，但不多访存
            tot += roofline_us(f, b)
        elif n.op == 'BatchNormalization':
            tot += roofline_us(ef, eb)
        elif n.op == 'Relu':
            tot += roofline_us(af, ab)
        elif n.op == 'Add':
            tot += roofline_us(af, ab * 1.5)
    return tot

# 事故重演：为了排查一个 badcase，把第 3 个 block 的 conv 输出也 mark 成了图输出
G_dbg = G.clone(); G_dbg.outputs = G_dbg.outputs + ['c3_out']
G_fus, _ = fuse_graph(G)
G_dbf, _ = fuse_graph(G_dbg)
print('层数：原图 %d  ->  正常融合 %d  ->  多一个 debug 输出 %d'
      % (len(G.nodes), len(G_fus.nodes), len(G_dbf.nodes)))
assert len(G_fus.nodes) == 6 and len(G_dbf.nodes) == 8

BACKBONES = [('标准卷积骨干 (3x3, 256->256)', dict(k=3, groups=1)),
             ('depthwise 骨干 (5x5, dw)',      dict(k=5, groups=256))]
print()
print('%-30s %12s %12s %12s %10s' %
      ('骨干类型', '不融合 µs', '正常融合 µs', 'debug输出 µs', '事故代价'))
costs_dbg = {}
for name, kw in BACKBONES:
    t_full = graph_latency_us(G, **kw)
    t_fuse = graph_latency_us(G_fus, **kw)
    t_dbg  = graph_latency_us(G_dbf, **kw)
    costs_dbg[name] = (t_full, t_fuse, t_dbg)
    print('%-30s %12.1f %12.1f %12.1f %9.1f%%'
          % (name, t_full, t_fuse, t_dbg, 100 * (t_dbg / t_fuse - 1)))

(_, f_std, d_std) = costs_dbg['标准卷积骨干 (3x3, 256->256)']
(_, f_dw,  d_dw)  = costs_dbg['depthwise 骨干 (5x5, dw)']
assert d_std > f_std and d_dw > f_dw
assert (d_std / f_std - 1) < 0.05, '标准卷积骨干上，这个事故只值几个百分点'
assert (d_dw / f_dw - 1) > 0.25, 'depthwise 骨干上，同一个事故的代价大一个数量级'
print()
print('⚠️  **同一行代码，在标准卷积骨干上只涨 %.1f%%，在 depthwise 骨干上涨 %.0f%%。**'
      % (100 * (d_std / f_std - 1), 100 * (d_dw / f_dw - 1)))
print('   而现代实时检测器（RTMDet 的 CSPNeXt、轻量 YOLO）恰恰是后者。')
print('   这类事故的共同特征：**数值全对、评测全过、只有延迟涨了**。')
print('   对策：把 engine 层数 / 融合层占比 / 输出张量数做成 CI 门禁 ——')
print('   一致性检查抓不到它，因为数值本来就是对的。')"""),

    md("""## 6 · 动态 shape：optimization profile 的代价模型与最优切分

代价模型（模块正文第 3 节）：

$$\\mathbb{E}[T]=\\sum_s p(s)\\,t_0(s)\\Bigl(1+\\alpha\\bigl|\\ln (s/s_{\\text{opt}})\\bigr|\\Bigr)$$

场景取自**两级 TSR 架构的第二级**：检测器给出的 crop 数随场景剧烈变化，
高速上常常只有 1–2 块标志，城市路口龙门架一次能出十几块。"""),

    code("""ALPHA = 0.15          # 偏离 opt 的惩罚系数（GEMM 类层实测常在 0.05~0.25）

def t0(s):
    \"\"\"batch=s 时，为它专门构建的静态 engine 的耗时（ms）：固定开销 + 线性项\"\"\"
    return 0.80 + 0.25 * s

def t_with_opt(s, s_opt, alpha=ALPHA):
    return t0(s) * (1.0 + alpha * abs(math.log(s / s_opt)))

# 线上 batch 分布：双峰（高速稀疏场景 + 城市密集场景）
SHAPES = list(range(1, 25))
w = np.array([np.exp(-((s - 2) ** 2) / 4.0) * 3.0 + np.exp(-((s - 16) ** 2) / 18.0)
              for s in SHAPES])
PROBS = (w / w.sum()).tolist()

print('batch 分布（截断显示）：')
for s, p in zip(SHAPES, PROBS):
    if p > 0.008:
        print('  batch=%2d  p=%.3f  %s' % (s, p, '#' * int(p * 200)))
assert abs(sum(PROBS) - 1) < 1e-12

def expected_latency(shapes, probs, s_opt, alpha=ALPHA):
    return sum(p * t_with_opt(s, s_opt, alpha) for s, p in zip(shapes, probs))

print()
print('%-28s %12s' % ('单 profile 的 opt 取值', '期望延迟 ms'))
best = min(SHAPES, key=lambda o: expected_latency(SHAPES, PROBS, o))
for o in [1, 2, 4, 8, 12, 16, 24]:
    tag = '  <- 最优' if o == best else ''
    print('%-28s %12.4f%s' % ('opt = %d' % o, expected_latency(SHAPES, PROBS, o), tag))
print('全局最优 opt =', best, ' 期望延迟 %.4f ms' % expected_latency(SHAPES, PROBS, best))
ideal = sum(p * t0(s) for s, p in zip(SHAPES, PROBS))
print('理想（每个 shape 都有专属静态 engine）= %.4f ms' % ideal)
print('单 profile 的代价 = +%.1f%%' % (100 * (expected_latency(SHAPES, PROBS, best) / ideal - 1)))
assert expected_latency(SHAPES, PROBS, best) > ideal"""),

    code("""def best_partition(shapes, probs, k, alpha=ALPHA):
    \"\"\"动态规划：把有序 shape 列表切成 k 段连续区间，每段一个 profile，
       使期望延迟最小。返回 (最小期望延迟, [(区间, opt), ...])。\"\"\"
    n = len(shapes)
    seg = [[(math.inf, None)] * (n + 1) for _ in range(n)]     # seg[i][j] = 区间 [i,j)
    for i in range(n):
        for j in range(i + 1, n + 1):
            bo, bc = None, math.inf
            for o in range(i, j):
                c = sum(probs[t] * t_with_opt(shapes[t], shapes[o], alpha) for t in range(i, j))
                if c < bc:
                    bc, bo = c, shapes[o]
            seg[i][j] = (bc, bo)
    INF = math.inf
    dp = [[INF] * (n + 1) for _ in range(k + 1)]
    bk = [[None] * (n + 1) for _ in range(k + 1)]
    dp[0][0] = 0.0
    for q in range(1, k + 1):
        for j in range(1, n + 1):
            for i in range(q - 1, j):
                if dp[q - 1][i] + seg[i][j][0] < dp[q][j]:
                    dp[q][j] = dp[q - 1][i] + seg[i][j][0]; bk[q][j] = i
    parts, j = [], n
    for q in range(k, 0, -1):
        i = bk[q][j]
        parts.append(((shapes[i], shapes[j - 1]), seg[i][j][1]))
        j = i
    return dp[k][n], parts[::-1]

print('%4s %14s %10s %s' % ('k', '期望延迟 ms', '相对理想', 'profile 切分 (min~max : opt)'))
prev = math.inf
costs = []
for k in range(1, 6):
    c, parts = best_partition(SHAPES, PROBS, k)
    costs.append(c)
    desc = '  '.join('[%d~%d:%d]' % (a, b, o) for (a, b), o in parts)
    print('%4d %14.4f %9.2f%% %s' % (k, c, 100 * (c / ideal - 1), desc))
    assert c <= prev + 1e-12, '增加 profile 不可能变差'
    prev = c
costs = np.array(costs)
gain = (costs[0] - costs) / (costs[0] - ideal)
print()
print('边际收益（相对「单 profile → 理想」这段差距）：', ' '.join('%.0f%%' % (100 * g) for g in gain))
assert costs[1] < costs[0]
assert gain[1] > 0.4, '第 2 个 profile 应吃掉大部分收益'
assert costs[4] - costs[3] > -0.02 * costs[0], '第 5 个 profile 已几乎无收益'
print('✅ **k=2 吃掉大部分收益，k>=4 基本是白花构建时间。**')"""),

    code("""# 另一半账：显存。**每个 profile 需要一个 execution context，各自按自己的 max 预留 activation**
M_WEIGHTS = 90.0                 # MB，权重（所有 context 共享）
M_ACT_PER_UNIT = 8.0             # MB / batch unit，激活显存近似线性于 batch

def memory_mb(parts):
    return M_WEIGHTS + sum(M_ACT_PER_UNIT * b for (_, b), _ in parts), len(parts)

print('%4s %13s %11s %9s %12s' % ('k', '期望延迟 ms', '显存 MB', 'context', '延迟↓ / 显存↑'))
m1 = None
for k in range(1, 5):
    c, parts = best_partition(SHAPES, PROBS, k)
    m, n_ctx = memory_mb(parts)
    if m1 is None:
        c1_, m1 = c, m
    print('%4d %13.4f %11.0f %9d %11s'
          % (k, c, m, n_ctx, '%.1f%% / +%.0f%%' % (100 * (1 - c / c1_), 100 * (m / m1 - 1))))
m_k1 = memory_mb(best_partition(SHAPES, PROBS, 1)[1])[0]
m_k4 = memory_mb(best_partition(SHAPES, PROBS, 4)[1])[0]
assert m_k4 > m_k1, '多 profile 必然多占显存'

# 分桶（bucketing）：把 batch padding 到固定档位，**每档一个静态 shape engine**
def bucket_eval(buckets):
    bo = lambda s: min(b for b in buckets if b >= s)
    t = sum(p * t0(bo(s)) for s, p in zip(SHAPES, PROBS))
    w = sum(p * (bo(s) - s) for s, p in zip(SHAPES, PROBS))
    return t, w

c1, _ = best_partition(SHAPES, PROBS, 1)
print()
print('%-34s %12s %14s %8s' % ('分桶方案（每档一个静态 engine）', '期望延迟 ms', '平均 padding 浪费', 'engine 数'))
for buckets in ([2, 4, 8, 16, 24], [1, 2, 3, 4, 6, 8, 12, 16, 20, 24]):
    t, w = bucket_eval(buckets)
    print('%-34s %12.4f %13.2f 个 %8d' % (str(buckets), t, w, len(buckets)))
t_coarse, _ = bucket_eval([2, 4, 8, 16, 24])
t_fine, _   = bucket_eval([1, 2, 3, 4, 6, 8, 12, 16, 20, 24])
print()
print('单 profile 动态 shape       %.4f ms' % c1)
print('理想（每 shape 专属 engine）%.4f ms' % ideal)
assert t_coarse > c1, '粗分桶：padding 浪费的算力超过了 profile 的偏离惩罚'
assert t_fine < c1,  '细分桶：静态 tactic 的收益压过了 padding 浪费'
print()
print('⚠️  **分桶不是无脑更优——桶的粒度决定成败。**')
print('   粗桶 %s：静态 tactic 很快，但平均要多算 1.89 个样本 -> 反而比单 profile 慢 %.1f%%'
      % ([2, 4, 8, 16, 24], 100 * (t_coarse / c1 - 1)))
print('   细桶（10 档）：padding 浪费降到 0.69 个 -> 比单 profile 快 %.1f%%，代价是 10 个 engine 要管'
      % (100 * (1 - t_fine / c1)))
print()
print('三条路没有普适赢家：')
print('   · 单 profile —— 最省事，主峰之外慢 10~30%')
print('   · 多 profile —— 更快，但**显存 × context 数**，车规 SoC 上这常常才是硬约束')
print('   · 分桶静态   —— 上限最高，但要同时付「padding 算力」和「多 engine 管理」')
print('   TSR 落点：主检测器一律**静态 shape**；只有两级架构的第二级分类器需要算这套账。')"""),

    md("""## 7 · engine 矩阵与硬件绑定：组合爆炸算一遍"""),

    code("""def engine_matrix(platforms, precisions, resolutions, model_versions=1, trt_versions=1):
    n = (len(platforms) * len(precisions) * len(resolutions)
         * model_versions * trt_versions)
    return n

PLATFORMS   = ['Orin-N', 'Orin-X', 'DualOrin', 'Thor']
PRECISIONS  = ['fp16', 'int8']
RESOLUTIONS = ['960x540', '1280x720', '1920x1080']
MODEL_VERS  = 3          # 灰度期同时在网的模型版本
BUILD_MIN   = 12.0
SIZE_MB     = 80
MACHINES    = 6

n_per_ver = engine_matrix(PLATFORMS, PRECISIONS, RESOLUTIONS)
n_total   = engine_matrix(PLATFORMS, PRECISIONS, RESOLUTIONS, MODEL_VERS)
serial_h  = n_total * BUILD_MIN / 60
wall_h    = serial_h / MACHINES
store_gb  = n_total * SIZE_MB / 1024

print('平台 %d × 精度 %d × 分辨率 %d          = %d 个 engine / 每个模型版本'
      % (len(PLATFORMS), len(PRECISIONS), len(RESOLUTIONS), n_per_ver))
print('× 在网模型版本 %d                        = %d 个 engine' % (MODEL_VERS, n_total))
print('× 构建 %.0f 分钟                          = %.1f 机器小时（串行）' % (BUILD_MIN, serial_h))
print('÷ %d 台并行构建机                        = %.1f 小时墙钟' % (MACHINES, wall_h))
print('存储与分发                               = %.1f GB' % store_gb)
print('**独立验证次数（每个 engine 都是一个发布物）= %d 次完整评测**' % n_total)
assert n_per_ver == 24 and n_total == 72
assert abs(serial_h - 14.4) < 1e-9

print()
print('TensorRT 一次小版本升级会发生什么：')
print('  · 序列化格式变了 -> 所有 engine 作废')
print('  · **全量重建 %d 个 + 全量回归 %d 次** -> %.1f 小时墙钟 + 全部评测预算'
      % (n_total, n_total, wall_h))
print('  · 这就是为什么量产系统的 TRT 版本升级频率极低（常常一年一次或更少）')

# 用 hardware/version compatible 模式压缩矩阵：拿性能换维护性
LOSS = 0.10          # 典型 5~15%
n_compat = engine_matrix(['AmperePlus'], PRECISIONS, RESOLUTIONS, MODEL_VERS)
print()
print('如果启用 hardware-compatible（只用架构通用 tactic）：')
print('  engine 数 %d -> %d（少 %.0f%%），但**每个都慢约 %.0f%%**'
      % (n_total, n_compat, 100 * (1 - n_compat / n_total), 100 * LOSS))
budget_ms, base_ms = 12.0, 11.0
print('  延迟预算 %.1f ms、当前 %.1f ms：加 %.0f%% 后 = %.2f ms -> %s'
      % (budget_ms, base_ms, 100 * LOSS, base_ms * (1 + LOSS),
         '仍在预算内，划算' if base_ms * (1 + LOSS) <= budget_ms else '**超预算，不能换**'))
assert n_compat == 18
assert base_ms * (1 + LOSS) > budget_ms
print('  -> 本例中余量不够，只能老老实实维护 %d 个 engine。' % n_total)"""),

    code("""def engine_compatible(engine_meta, runtime_meta):
    \"\"\"返回 (能否加载, 原因)。顺序很重要：先查会**硬失败**的，再查会**静默变慢**的。\"\"\"
    if engine_meta['trt'] != runtime_meta['trt'] and not engine_meta.get('version_compatible'):
        return False, 'TensorRT 版本不匹配 (%s vs %s) -> 反序列化失败' % (
            engine_meta['trt'], runtime_meta['trt'])
    if engine_meta['sm'] != runtime_meta['sm'] and not engine_meta.get('hw_compatible'):
        return False, 'SM 架构不匹配 (%s vs %s) -> 反序列化失败' % (
            engine_meta['sm'], runtime_meta['sm'])
    if runtime_meta['driver'] < engine_meta['min_driver']:
        return False, '驱动版本过低 (%.1f < %.1f)' % (
            runtime_meta['driver'], engine_meta['min_driver'])
    if engine_meta['gpu'] != runtime_meta['gpu']:
        return True, '⚠️ 能加载，但 tactic 是为 %s 挑的，在 %s 上**不是最优**（静默变慢）' % (
            engine_meta['gpu'], runtime_meta['gpu'])
    return True, 'OK'

ENG = dict(trt='8.6.1', sm='sm_87', gpu='Orin-X', min_driver=35.0)
CASES = [
    ('同型号同版本',        dict(trt='8.6.1', sm='sm_87', gpu='Orin-X',  driver=35.4)),
    ('TRT 小版本不同',      dict(trt='8.6.2', sm='sm_87', gpu='Orin-X',  driver=35.4)),
    ('换到 Thor（新架构）', dict(trt='8.6.1', sm='sm_90', gpu='Thor',    driver=36.0)),
    ('同架构不同型号',      dict(trt='8.6.1', sm='sm_87', gpu='Orin-N',  driver=35.4)),
    ('驱动过旧',            dict(trt='8.6.1', sm='sm_87', gpu='Orin-X',  driver=34.1)),
]
for name, rt in CASES:
    ok, why = engine_compatible(ENG, rt)
    print('%-22s %-6s %s' % (name, '✅' if ok else '❌', why))

assert engine_compatible(ENG, CASES[0][1])[0]
assert not engine_compatible(ENG, CASES[1][1])[0]
assert not engine_compatible(ENG, CASES[2][1])[0]
ok, why = engine_compatible(ENG, CASES[3][1])
assert ok and '不是最优' in why           # ← 最危险的一档：不报错，只变慢
assert not engine_compatible(ENG, CASES[4][1])[0]
print()
print('⚠️  **最危险的是第 4 行**：能加载、精度对、只是慢。')
print('   前三种失败是显式的，集成阶段就会被抓到；第 4 种要靠「按硬件指纹选包」的分发机制来防。')"""),

    md("""## ✏️ 练习 1：BN 折叠

实现 `fold_bn(w, b, gamma, beta, mean, var, eps=1e-5)`，返回融合后的 `(w_new, b_new)`：

$$\\tilde W_o = \\frac{\\gamma_o}{\\sqrt{\\sigma_o^2+\\epsilon}}W_o,\\qquad
  \\tilde b_o = \\frac{\\gamma_o (b_o-\\mu_o)}{\\sqrt{\\sigma_o^2+\\epsilon}} + \\beta_o$$

注意 `w` 的形状是 `(O, C//groups, kh, kw)`，缩放要作用在**第 0 维（输出通道）**上。"""),

    code("""def fold_bn(w, b, gamma, beta, mean, var, eps=1e-5):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
# (a) 手算：单通道 1x1 卷积  w=2 b=1 ; gamma=3 beta=0.5 mean=4 var=4-eps
w1 = np.array([[[[2.0]]]]); b1 = np.array([1.0])
g1 = np.array([3.0]); be1 = np.array([0.5]); m1 = np.array([4.0]); v1 = np.array([4.0 - 1e-5])
wf, bf = fold_bn(w1, b1, g1, be1, m1, v1)
assert abs(wf[0, 0, 0, 0] - 3.0) < 1e-6, wf          # 2 * (3/2)
assert abs(bf[0] - (-4.0)) < 1e-6, bf                # (1-4)*1.5 + 0.5
# (b) 随机张量上的严格等价
for gp in (1, 4, 16):
    r = np.random.default_rng(7 + gp)
    xx = r.standard_normal((16, 12, 12))
    ww = r.standard_normal((16, 16 // gp, 3, 3)) * 0.2
    bb = r.standard_normal(16) * 0.1
    gg = r.uniform(0.4, 2.0, 16); be = r.standard_normal(16)
    mm = r.standard_normal(16); vv = r.uniform(0.2, 3.0, 16)
    ref = batchnorm(conv2d(xx, ww, bb, groups=gp), gg, be, mm, vv)
    w2, b2 = fold_bn(ww, bb, gg, be, mm, vv)
    got = conv2d(xx, w2, b2, groups=gp)
    assert np.allclose(ref, got, atol=1e-11), (gp, np.abs(ref - got).max())
    print('groups=%2d  最大误差 %.2e  ✅' % (gp, np.abs(ref - got).max()))
print('✅ 练习 1 通过：BN 折叠对普通卷积与分组/depthwise 卷积同样成立。')"""),

    md("""## ✏️ 练习 2：谁挡住了融合

实现两个函数：

- `absorbable(g, t)` → 张量 `t` 能否被下游「吃掉」：**唯一消费者 且 不是图的输出**
- `blocked_convs(g)` → 返回所有「输出无法被吃掉」的 `Conv` 节点名（排序后的 list）

这两个函数就是 TensorRT 融合安全性检查的最小版本。"""),

    code("""def absorbable(g, t):
    # TODO
    raise NotImplementedError

def blocked_convs(g):
    # TODO: 返回 sorted 的节点名列表
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
g_chain = make_chain(2)
g_res   = make_residual_graph()
g_dbg   = make_debug_graph()

assert absorbable(g_chain, 'c0_out') is True
assert absorbable(g_chain, 'bn0_out') is True
assert absorbable(g_chain, 'y1') is False, '图的输出不能被吃掉'
assert absorbable(g_res, 'bn0_out') is False, 'bn0_out 有 2 个消费者'
assert absorbable(g_dbg, 'c0_out') is False, 'c0_out 被 mark 成了图输出'

assert blocked_convs(g_chain) == [], blocked_convs(g_chain)
assert blocked_convs(g_res) == [], blocked_convs(g_res)      # conv0 的输出只有 bn0 用
assert blocked_convs(g_dbg) == ['conv0'], blocked_convs(g_dbg)

g_mix = make_chain(6); g_mix.outputs = g_mix.outputs + ['c1_out', 'c4_out']
assert blocked_convs(g_mix) == ['conv1', 'conv4'], blocked_convs(g_mix)
print('正常链         被挡住的 conv:', blocked_convs(g_chain))
print('残差图         被挡住的 conv:', blocked_convs(g_res), ' (挡住的是 ReLU，不是 BN)')
print('debug 输出图   被挡住的 conv:', blocked_convs(g_dbg))
print('多 debug 输出  被挡住的 conv:', blocked_convs(g_mix))
print('✅ 练习 2 通过：把这两行逻辑接进 CI，就能在 PR 阶段拦住「多 mark 一个输出」的事故。')"""),

    md("""## ✏️ 练习 3：roofline 与融合收益

实现：

- `roofline_us2(flops, byts, peak=1e13, bw=2e11, launch=5e-6)` → 微秒
- `cbr_saving(H, W, c, k, groups=1)` → `(拆成三个 kernel 的 µs, 融合成一个的 µs, 节省比例)`

约定（与正文一致）：FP16 每元素 2 字节；卷积 FLOPs = `2*H*W*cout*(cin/groups)*k*k`；
BN 每元素 2 次运算、ReLU 1 次，两者都是「读一遍写一遍」；融合后**算力照旧、访存只剩卷积那一趟**。"""),

    code("""def roofline_us2(flops, byts, peak=1e13, bw=2e11, launch=5e-6):
    # TODO
    raise NotImplementedError

def cbr_saving(H, W, c, k, groups=1):
    # TODO: 返回 (t_unfused_us, t_fused_us, saving_frac)
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
# (a) 手算 roofline：compute-bound 与 memory-bound 各一例
assert abs(roofline_us2(1e12, 1e6) - 100005.0) < 1e-6, roofline_us2(1e12, 1e6)   # 0.1s + 5µs
assert abs(roofline_us2(1e6, 1e9) - 5005.0) < 1e-6, roofline_us2(1e6, 1e9)       # 5ms + 5µs
# (b) 正文的两个案例
t_un, t_fu, s_std = cbr_saving(80, 80, 256, 3, 1)
print('3x3 标准卷积 : 拆开 %.1f µs -> 融合 %.1f µs   省 %.1f%%' % (t_un, t_fu, 100 * s_std))
assert 0.08 < s_std < 0.10, s_std
t_un2, t_fu2, s_dw = cbr_saving(80, 80, 256, 5, 256)
print('5x5 depthwise: 拆开 %.1f µs -> 融合 %.1f µs   省 %.1f%%' % (t_un2, t_fu2, 100 * s_dw))
assert 0.65 < s_dw < 0.69, s_dw
assert s_dw > 6 * s_std, 'depthwise 的融合收益应远大于标准卷积'
# (c) 分辨率越高、通道越少，越 memory-bound，融合越值钱
_, _, s_p2 = cbr_saving(160, 160, 64, 3, 1)      # P2 层级：高分辨率 + 少通道
print('P2 层级 3x3 64ch (160x160): 省 %.1f%%' % (100 * s_p2))
assert s_p2 > s_std
print('✅ 练习 3 通过：**融合的价值 = 该层有多 memory-bound**，与它的 FLOPs 无关。')"""),

    md("""## ✏️ 练习 4：optimization profile 的 opt 该选在哪

实现：

- `profile_cost(shapes, probs, s_opt, alpha=0.15)` → 期望延迟
  （用已定义的 `t0(s)` 与惩罚 $1+\\alpha|\\ln(s/s_{opt})|$）
- `pick_opt(shapes, probs, alpha=0.15)` → 在 `shapes` 里挑期望延迟最小的 `s_opt`"""),

    code("""def profile_cost(shapes, probs, s_opt, alpha=0.15):
    # TODO
    raise NotImplementedError

def pick_opt(shapes, probs, alpha=0.15):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
# (a) opt 恰好等于唯一的 shape 时，没有惩罚
assert abs(profile_cost([4], [1.0], 4) - t0(4)) < 1e-12
assert abs(profile_cost([4], [1.0], 4) - 1.8) < 1e-12
# (b) 两点分布：频次一样，但**耗时大的那档应该拿走 opt**
c_lo = profile_cost([2, 8], [0.5, 0.5], 2)
c_hi = profile_cost([2, 8], [0.5, 0.5], 8)
print('shapes=[2,8] 各 50%%:  opt=2 -> %.4f ms   opt=8 -> %.4f ms' % (c_lo, c_hi))
assert c_hi < c_lo, 'opt 应偏向耗时大的一档，而不是频次中位数'
assert pick_opt([2, 8], [0.5, 0.5]) == 8
# (c) 复现第 6 节的结论
assert pick_opt(SHAPES, PROBS) == 15, pick_opt(SHAPES, PROBS)
assert abs(profile_cost(SHAPES, PROBS, 15) - 3.1924) < 1e-3
# (d) alpha=0 时，惩罚消失，任何 opt 都一样
assert abs(profile_cost(SHAPES, PROBS, 1, alpha=0.0)
           - profile_cost(SHAPES, PROBS, 24, alpha=0.0)) < 1e-12
print('全局最优 opt =', pick_opt(SHAPES, PROBS), '  期望延迟 %.4f ms'
      % profile_cost(SHAPES, PROBS, pick_opt(SHAPES, PROBS)))
print('✅ 练习 4 通过：**opt 不是「最常见的 shape」，是「加权后代价最小的 shape」**——')
print('   一个只出现 5% 但耗时是别人 10 倍的大 shape，完全可能把 opt 拉过去。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def fold_bn(w, b, gamma, beta, mean, var, eps=1e-5):
    s = gamma / np.sqrt(var + eps)
    return w * s[:, None, None, None], (b - mean) * s + beta"""),

    code("""# 练习 2 参考答案
def absorbable(g, t):
    return len([n for n in g.nodes if t in n.inputs]) == 1 and t not in g.outputs

def blocked_convs(g):
    return sorted(n.name for n in g.nodes
                  if n.op == 'Conv' and not absorbable(g, n.outputs[0]))"""),

    code("""# 练习 3 参考答案
def roofline_us2(flops, byts, peak=1e13, bw=2e11, launch=5e-6):
    return (max(flops / peak, byts / bw) + launch) * 1e6

def cbr_saving(H, W, c, k, groups=1):
    DBY = 2
    cg = c // groups
    cf = 2 * H * W * c * cg * k * k
    cb = (H * W * c + H * W * c + c * cg * k * k) * DBY
    bf, bb = H * W * c * 2, 2 * H * W * c * DBY      # BN
    af, ab = H * W * c * 1, 2 * H * W * c * DBY      # ReLU
    t_un = roofline_us2(cf, cb) + roofline_us2(bf, bb) + roofline_us2(af, ab)
    t_fu = roofline_us2(cf + af, cb)                 # 算力照旧，访存只剩卷积那一趟
    return t_un, t_fu, 1 - t_fu / t_un"""),

    code("""# 练习 4 参考答案
def profile_cost(shapes, probs, s_opt, alpha=0.15):
    return sum(p * t0(s) * (1 + alpha * abs(math.log(s / s_opt)))
               for s, p in zip(shapes, probs))

def pick_opt(shapes, probs, alpha=0.15):
    return min(shapes, key=lambda o: profile_cost(shapes, probs, o, alpha))"""),

    md("""---
## 🧪 真实工程胶囊：TensorRT 构建脚本 + 必须进 CI 的三条门禁"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 构建：一条可以直接抄的 trtexec 命令（静态 shape 优先！）
# ══════════════════════════════════════════════════════════════════════
trtexec --onnx=det.onnx --saveEngine=det_orinx_fp16.plan \\
        --fp16 \\
        --memPoolSize=workspace:2048 \\
        --timingCacheFile=golden_orinx_trt861.cache \\
        --avgTiming=8 \\
        --builderOptimizationLevel=3 \\
        --profilingVerbosity=detailed \\
        --exportLayerInfo=layers.json \\
        --verbose 2>&1 | tee build.log

# 动态 shape 时三档都要给（**每个动态输入都要给**，漏一个直接报错）：
#   --minShapes=images:1x3x640x640
#   --optShapes=images:1x3x640x640      <- 这个数必须来自**线上 shape 分布统计**
#   --maxShapes=images:4x3x640x640      <- 显存按它预留，别随手写大

# 混合精度（下一模块会用到）：必须用 obey，不满足要它当场失败
#   --precisionConstraints=obey --layerPrecisions=head.reg.*:fp16

# ══════════════════════════════════════════════════════════════════════
# B. 三条必须进 CI 的门禁（一致性检查抓不到它们，因为数值本来就是对的）
# ══════════════════════════════════════════════════════════════════════
# 门禁 1 · 融合率：engine 层数 应显著少于 ONNX 节点数
#   python - <<PY
#   import json; L=json.load(open('layers.json'))['Layers']
#   fused = sum(1 for l in L if '+' in l['Name'])
#   print('layers=%d fused=%d ratio=%.2f' % (len(L), fused, fused/len(L)))
#   assert fused/len(L) > 0.5        # 阈值按你的模型基线定，重点是**不许回退**
#   PY
#
# 门禁 2 · 精度落实率：目标 FP16 时，FP32 层数必须为 0（或在白名单内）
#   grep -o '"Precision": *"[^"]*"' layers.json | sort | uniq -c
#   # 期望：FP16 绝大多数；出现大量 FP32 = 精度标志没生效
#
# 门禁 3 · Reformat 占比：精度/布局反复切换会把收益吃光
#   trtexec --loadEngine=det.plan --dumpProfile --separateProfileRun \\
#           --exportProfile=prof.json --shapes=images:1x3x640x640
#   # 统计 name 里含 'reformat' 的层的耗时占比，应 < 5%
#
# 门禁 4（用分区式集成时必加）· 子图数必须 == 1
#   ORT:            ORT_TENSORRT_DUMP_SUBGRAPHS=1  + 看日志里的 subgraph 数
#   torch-tensorrt: debug=True 打印 partitioning 报告，看 unsupported ops 列表
#   # 子图 > 1 = 有算子在走慢路径 = 「转了 TRT 但没变快」的头号原因

# ══════════════════════════════════════════════════════════════════════
# C. 构建可复现性（功能安全要求「同输入同产物」，而 auto-tuning 天生不是）
# ══════════════════════════════════════════════════════════════════════
#  1. 构建机独占 + 锁频：  nvidia-smi -lgc <freq>   / jetson_clocks
#  2. --avgTiming=8        提高每个 tactic 的计时重复次数
#  3. **golden timing cache 纳入版本管理**，所有构建（CI 与发布）必须带上它
#  4. engine 旁边存一份 manifest（缺一不可，出问题要能回溯）：
#     { onnx_sha256, weights_sha256, builder_flags, workspace_mb,
#       min/opt/max_shapes, trt_version, cuda_version, driver_version,
#       gpu_name, sm_arch, timing_cache_sha256, build_host, build_time }

# ══════════════════════════════════════════════════════════════════════
# D. TSR 专项检查
# ══════════════════════════════════════════════════════════════════════
#  · 主检测器一律**静态 shape**；动态只留给两级架构第二级的 crop 分类器
#  · 第二级用**分桶 padding 到固定 batch**，别用跨度很大的单 profile
#  · RT-DETR 系：确认 grid_sample / MultiscaleDeformableAttn 是否需要 plugin
#    （RT-DETRv2 的离散采样版本可绕开；plugin 会永久切断融合链）
#  · NMS 是否用 EfficientNMS_TRT 塞进 engine：省一次 D2H + CPU 后处理，
#    但把 NMS 语义冻进了 engine，改阈值语义要重建（见模块 04）
#  · engine 矩阵：平台 x 精度 x 分辨率 x 模型版本，**每一个都是独立发布物**，
#    都要单独过精度门禁与延迟门禁。「一份权重」省的是训练，不是验证。
'''
print(RECIPE)
for token in ['--optShapes', 'timingCacheFile', 'builderOptimizationLevel',
              'exportLayerInfo', 'precisionConstraints=obey', '子图数必须 == 1',
              'onnx_sha256', 'EfficientNMS_TRT', 'grid_sample', '静态 shape']:
    assert token in RECIPE, token
print('✅ 覆盖：构建命令 / 动态 shape 三档 / 四条 CI 门禁 / 可复现性 / TSR 专项')"""),

    md("""### 小结

- **ONNX 节点 ≠ engine 层。** 本 notebook 里 18 个 ONNX 节点融成 6 个 engine 层，数值完全一致。
  拿 ONNX 的节点数或 FLOPs 去猜 engine 性能，方向就是错的——去看 `--dumpLayerInfo`。
- **Conv+BN 融合是严格恒等**（$\\tilde W=\\gamma W/\\sqrt{\\sigma^2+\\epsilon}$，$\\tilde b=\\gamma(b-\\mu)/\\sqrt{\\sigma^2+\\epsilon}+\\beta$），
  对分组/depthwise 卷积同样成立。同一套代数还支撑 RepVGG 重参数化与 QAT 的 BN folding。
- **融合省的是访存不是计算**：标准卷积上只值 ~9%，**depthwise 上值 ~67%**。
  越是为「FLOPs 少」设计的轻量骨干，越 memory-bound，越依赖融合。
- **两条安全性条件**：中间张量消费者数 == 1，且不是图的输出。
  破坏任一条，融合安静地失败——**数值全对、评测全过、只有延迟涨了**（depthwise 骨干上实测 +33%）。
  所以你需要一条独立于一致性检查的 engine 结构门禁。
- **动态 shape 的三个数各管一件事**：`opt` 决定多快，`max` 决定占多少显存，`min` 只决定会不会崩。
  `opt` 应取「加权代价最小」而非「最常见」的 shape；多 profile 的 k=2 就吃掉 64% 的收益，k≥4 是浪费；
  **分桶不是无脑更优——粗桶的 padding 浪费会反超 profile 惩罚**。
- **engine 是 (硬件, TRT 版本, 驱动, builder config, timing cache) 的函数，还带 3–5% 的构建噪声。**
  4 平台 × 2 精度 × 3 分辨率 × 3 在网版本 = 72 个 engine，**每一个都是独立发布物**。
  最危险的不是「加载失败」（显式），而是「能加载但 tactic 不最优」（静默变慢）。

下一站：**模块 03 · INT8 校准与精度恢复** —— 本课技术密度最高的一节，也是 JD 里
「quantization accuracy drop」的直接对应。"""),
]
