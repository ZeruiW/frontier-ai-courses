# -*- coding: utf-8 -*-
"""C63 模块 04 · 服务、部署与容量估算（ML 系统设计面试）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "本课模块 00–03（七步框架、需求澄清、数据设计、建模评测）；C53/C60 的延迟与部署基础会被引用但不要求读过"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_serving_capacity.ipynb（容量估算器 / 延迟预算分解器 / 降级决策表 / 监控阈值设定器）'),
    ("核心参考", "《Designing Data-Intensive Applications》第 1 章 · NVIDIA/Google 公开的 GPU 显存带宽白皮书 · C53-05（延迟拆解）· C58-05（回归门禁）· C60（车端部署一致性）"),
    ("预计时长", "读 55 分钟 + 跑 40 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-serving", "为什么「服务与部署」是 system design 面试的第六步而不是可选项", "".join([
        P("很多候选人把 system design 面试等同于「选一个模型架构」，讲完 backbone、损失函数、评测指标就觉得大功告成。"
          "但面试官在评分卡上单独留了一整栏给<strong>服务与部署</strong>——因为这是把一个能跑的模型变成"
          "<strong>能被别人依赖</strong>的系统的最后一公里，也是<em>唯一一段能被数量级心算当场验证真假</em>的内容。"),
        P("这一步要回答的问题很具体：<strong>这套方案需要多少台机器？多少显存？多少延迟？花多少钱？"
          "扛不住流量峰值怎么办？模型突然变差怎么发现？出了事怎么在 5 分钟内回滚？</strong>"
          "每一个问题都有一个数量级答案，而面试官最想看到的，正是你能不能<em>当场心算出这个数量级</em>，"
          "而不是含糊地说「上 K8s 自动扩缩容就行」。"),
        CALLOUT("intuition", "<strong>这一步的隐藏考点是「你是否知道自己的方案值多少钱、跑多快」。</strong>"
                             "一个说得出「TSR 检测模型约 8M 参数，fp16 推理显存占用几十 MB，"
                             "单张 T4 在 batch=1 下大约 8–15ms，一路车规相机 30FPS 只需一张卡的零头算力」的候选人，"
                             "比一个只会说「用 TensorRT 加速一下」的候选人，可信度高一个数量级——"
                             "<em>因为前者展示的是可验证的工程判断，后者只是关键词堆砌</em>。"),
        H3("本节要拆掉的三个误解"),
        TABLE(["误解", "为什么错", "正确的心态"], [
            ["「服务架构就是画个框图」", "框图人人会画，面试官要的是<strong>每条边上的延迟/流量数字</strong>", "每画一条箭头，就要能说出这条边大概几毫秒、每秒几次调用"],
            ["「容量按经验留够余量就行」", "「留够余量」不是数字，面试官会追问「够是多少」——答不出就露馅", "永远用<strong>心算公式</strong>推导一个具体数字，再说「所以我留 X 倍余量」"],
            ["「降级方案是锦上添花」", "车规系统里，<strong>没有降级方案的设计等于没有设计</strong>——模型总会挂，问题只是挂了怎么办", "降级方案要跟主链路一起画，不是面试最后补一句"],
        ]),
        DUAL(
            "换个说法：如果说模块 01–03 是在回答「我们要造一个什么」，那模块 04 是在回答"
            "「<strong>造出来的这个东西，物理上跑得动吗、扛得住吗、坏了怎么办</strong>」。"
            "这三个问题分别对应<em>容量估算</em>、<em>扩缩容</em>、<em>降级与监控</em>——本模块就按这个顺序展开。",
            "更严谨地说，服务与部署要交付的是一份<strong>可验证的资源-延迟-成本三元组</strong>："
            "给定 QPS 目标与延迟 SLA，反推需要多少实例、多少显存、多少预算；"
            "并且这份估算要能<strong>在两条独立路径上互相校验</strong>（例如「按 FLOPs 算」和「按实测吞吐外推」"
            "应该给出同一数量级的答案——见模块 05 的通用脚手架）。这正是本课与 C65-01（Fermi 估算）的分工："
            "C65-01 教你<em>怎么心算</em>，本模块教你<em>ML 服务场景下具体估算什么</em>。",
        ),
        CALLOUT("warn", "<strong>「面试官没问延迟/成本我就不用讲」是常见误区。</strong>七步框架里这一步默认要主动讲，"
                        "因为它是区分「纸上谈兵」和「能上线」的分水岭。如果时间紧张，"
                        "<strong>至少要主动说出一张锚点数字表里的两三个数字</strong>（本模块第 3 节），"
                        "哪怕来不及展开推导，也比完全不提要强得多。"),
    ])),

    # ============================================================== 2
    ("architecture", "架构图怎么画：数据流、控制流与在线/近线/离线三层", "".join([
        P("白板上的架构图，评分标准不是「画得像不像论文插图」，而是<strong>能不能让面试官一眼看出"
          "「数据从哪来、经过谁处理、谁能改变这个流程的走向」</strong>。这需要同时画出两种线，"
          "很多候选人只画了一种就以为完事了。"),
        TABLE(["线的种类", "画的是什么", "TSR 场景的例子", "遗漏的后果"], [
            ["<strong>数据流</strong>（实线）", "数据从产生到被消费的路径：原始信号 → 特征 → 预测 → 下游动作", "相机帧 → 预处理 → 检测模型 → 后处理 → 跟踪 → 规控", "只画数据流会让人以为系统没有反馈与控制"],
            ["<strong>控制流</strong>（虚线）", "谁在监控谁、谁能触发降级/回滚、配置从哪里下发", "监控服务发现延迟超标 → 触发模型降级 → 通知运维 → 人工确认回滚", "遗漏控制流，面试官会追问「模型挂了谁去处理」，答不上来直接露馅"],
        ]),
        P("画完两种线之后，要标出<strong>系统边界</strong>：哪部分在车端、哪部分在云端；"
          "哪部分是我们负责的、哪部分是第三方/上游团队负责的。<strong>边界不标清楚，评测和排障责任就说不清楚</strong>。"),
        H3("在线 / 近线 / 离线三层：分工原则与延迟量级"),
        P("几乎所有工业 ML 系统都能拆成这三层，划分依据只有一个：<strong>这份计算能不能等</strong>。"),
        TABLE(["层", "延迟量级", "谁在用它", "TSR 系统里对应什么", "为什么不能放到别的层"], [
            ["<strong>在线（online）</strong>", "个位数到几十毫秒", "请求路径上，结果直接影响当前这一帧的动作", "单帧检测推理、跟踪关联、置信度合成", "规控要在这一帧做决策，等不了；放慢就是漏检的另一种形式"],
            ["<strong>近线（nearline）</strong>", "秒级到分钟级", "不阻塞当前决策，但要在「不太久」之后生效", "多帧置信度累积的滑窗统计、场景标签打点、触发器判定要不要回传这段片段", "太慢会错过时间窗口（比如已经过了那个路口才判断要不要回传）；但没必要挤占在线预算"],
            ["<strong>离线（offline）</strong>", "小时级到天级", "批处理，允许攒一批再算", "夜间批量重标注难例、模型再训练、大规模回归评测、报表", "在线资源紧张、时效性要求低，硬塞进在线只会拖慢关键路径"],
        ]),
        ASCII("""             在线（车端，个位数~几十 ms）
   相机帧 ──▶ 预处理 ──▶ 检测/分类 ──▶ 跟踪与状态机 ──▶ 输出给规控
                                │                                  │
                                │ 采样/触发（低置信、分歧、规则命中）│ 监控埋点
                                ▼                                  ▼
             近线（车端缓存 / 边缘节点，秒~分钟级）           实时指标流
        置信度滑窗累积、片段打包、场景标签初筛 ───▶ 回传队列（带宽受限）
                                │
                                ▼
             离线（云端，小时~天级）
   数据落库 → 难例挖掘/标注（C58）→ 训练 → 离线评测/回归门禁 → 灰度发布
"""),
        CALLOUT("intuition", "<strong>三层划分的本质是「把等不了的和等得起的分开，不要用离线的思维设计在线，也不要用在线的成本设计离线」。</strong>"
                             "面试里常见的错误是把「多帧投票」直接算进在线延迟预算——"
                             "其实滑窗累积可以放近线异步进行，只要状态机设计得当（见 C55-04），"
                             "在线只需要读最新的累积结果，不需要每帧都重算整个窗口。"),
        DUAL(
            "画图时的顺序建议：<strong>先画在线主链路（这是评分权重最高的部分），再补近线的旁路，最后补离线的回路</strong>。"
            "很多人一上来就画整个数据闭环（近线+离线），结果时间耗在无关紧要的细节上，"
            "反而没时间讲清楚在线路径的延迟预算——本末倒置。",
            "更严谨地说，三层的边界不是绝对的，而是<strong>由 SLA 决定的相对划分</strong>：同一个「置信度更新」计算，"
            "在需要每帧输出的系统里是在线的一部分，在只需要每秒输出一次的系统里可以挪到近线。"
            "画架构图时，<em>先确认 SLA 数字，再决定某个模块该放哪一层</em>，而不是凭直觉分类。",
        ),
    ])),

    # ============================================================== 3
    ("anchors", "可背的锚点数字表：容量估算的地基", "".join([
        P("数量级心算最怕的不是不会算，而是<strong>手里没有可靠的锚点数字</strong>——公式对了，"
          "代入一个错两个数量级的常数，结论照样错。下面这几张表是本模块乃至整个 system design 面试"
          "<strong>唯一需要背下来</strong>的内容，其余都可以现场推导。"),
        TABLE(["硬件", "峰值算力（FP16/BF16, TFLOPS）", "显存带宽（GB/s）", "典型显存容量", "一句话记忆"], [
            ["T4（车规常见推理卡）", "≈ 65", "≈ 320", "16 GB", "「T4 算力几十 T，带宽三百多 G，是入门级推理卡的锚点」"],
            ["A10 / L4（新一代推理卡）", "≈ 125–150", "≈ 300–600", "24 GB", "算力翻倍，带宽相近——推理更吃算力密度而不是纯带宽"],
            ["A100（训练/大模型推理主力）", "≈ 312（不含稀疏）", "≈ 2000", "40/80 GB", "「A100 算力 300+T，带宽 2T，这两个数字是训练侧的锚点」"],
            ["H100", "≈ 990（不含稀疏）", "≈ 3350", "80 GB", "约 A100 的 3 倍算力，1.7 倍带宽"],
            ["车端 SoC（如 Orin 级）", "≈ 100–260（INT8 稀疏峰值，实际可用远低于峰值）", "≈ 200", "共享内存，通常个位数~十几 GB", "车端算力看似接近 A100 峰值，但<strong>实际可用算力常只有峰值的 1–3 成</strong>（多任务分时、功耗墙）"],
        ]),
        CALLOUT("warn", "<strong>「峰值算力」几乎从不是「可用算力」。</strong>实测利用率能到峰值的 30–50% 已经算相当好的核函数；"
                        "车端在多任务抢占、持续负载降频下，实际可用算力可能只有峰值的 10–30%（见 C60-05 的功耗降频实验）。"
                        "<strong>心算时永远用「峰值 × 0.2~0.3」估可用算力，不要直接用峰值代入公式</strong>——"
                        "这一个折扣因子就是很多候选人估算错一个数量级的根源。"),
        TABLE(["模型/量级", "参数量", "FP16 显存占用（仅权重）", "典型单张延迟（推理卡，batch=1）", "备注"], [
            ["TSR 检测器（轻量 anchor-free，如 YOLO-nano 级/RTMDet-tiny 级）", "2–10 M", "4–20 MB", "3–10 ms（T4/A10 级）", "车端 TSR 检测器的常见量级，见 C53"],
            ["中型检测器（RTMDet-m/RT-DETR-R50 级）", "20–50 M", "40–100 MB", "8–20 ms", "云端复检或高精度分支常用"],
            ["ResNet-50 分类/backbone", "≈ 25.6 M", "≈ 51 MB", "2–5 ms（仅前向，224² 输入）", "两级 TSR 方案里分类头的锚点（见 C55-02）"],
            ["ViT-B/16", "≈ 86 M", "≈ 172 MB", "5–15 ms", "注意力 O(n²)，输入分辨率翻倍延迟涨约 4 倍"],
            ["7B 量级 LLM/VLA（fp16）", "7 B", "≈ 14 GB（仅权重，未含 KV cache/激活）", "首 token 常是几十~上百 ms 级，view 场景延迟更高", "云端蒸馏到车端的源模型量级参考，见 C59"],
        ]),
        MATH("\\text{显存(GB)} \\approx \\underbrace{\\frac{P \\times \\text{bytes/param}}{10^9}}_{\\text{权重}} + \\underbrace{k_{\\text{opt}} \\cdot \\frac{P \\times \\text{bytes/param}}{10^9}}_{\\text{优化器状态（仅训练）}} + \\underbrace{\\text{激活} \\times \\text{batch}}_{\\text{与输入分辨率/序列长强相关}}"),
        P("推理场景通常只需要第一项（fp16 下 <span class=\"term\">bytes/param</span> = 2）；"
          "训练场景 Adam 类优化器要再加约 2× 参数量的动量与二阶矩状态（<span class=\"term\">k_opt</span> ≈ 2，"
          "如果算上梯度本身则再加 1×，合计常按「权重的 4–6 倍」这个经验数记）。"),
        TABLE(["资源", "典型量级", "一句话记忆"], [
            ["标注单价（2D 框，简单场景）", "0.1–1 元/框（外包，国内价，量大议价）", "「一张图几十个框，标注一张图大约几毫秒到几十毫秒的人力成本量级换算成钱是几毛到几块」"],
            ["人天标注产出", "500–3000 框/人天（视复杂度）", "复杂场景（遮挡多、类别多）产出打对折"],
            ["单张 1080p 图像大小", "JPEG 压缩后约 200KB–1MB；原始 RGB 约 6MB", "「1080p 原始图 ≈ 6MB，这是带宽估算的基本单位」"],
            ["车规相机典型帧率×路数", "30 FPS × 4–8 路", "「一辆车一秒钟产生 120–240 帧原始图像」"],
            ["车端到云端典型上行带宽", "几 Mbps 到几十 Mbps（蜂窝网络，非连续）", "全量回传不可行，只能回传触发片段——这是 C58-03 触发器存在的根本原因"],
            ["数据中心内网带宽", "10–100 Gbps 量级", "训练集群内部远快于车云链路，不要把两者搞混"],
        ]),
        CALLOUT("intuition", "<strong>背这些表的目的不是精确，是「量级不错」。</strong>面试里没人要求你说出「T4 是 65.13 TFLOPS」，"
                             "但如果你说成「A100 的算力和车端 SoC 差不多」，那是错一个数量级的判断，会被认为完全没有工程手感。"
                             "<em>记忆的颗粒度应该是「个位数 T / 几十 T / 几百 T / 几千 GB/s」这种数量级标签，而不是精确小数点。</em>"),
    ])),

    # ============================================================== 4
    ("capacity-math", "容量估算的数量级心算：QPS → 实例数、参数量 → 显存、FLOPs → 算力、成本/千次推理", "".join([
        P("有了锚点数字，容量估算就是四条可以当场心算的公式。<strong>面试里要按顺序推导，每一步都口算出中间结果</strong>，"
          "而不是直接甩出最终答案——过程比答案值钱。"),
        H3("① QPS → 实例数"),
        MATH("\\text{实例数} = \\left\\lceil \\frac{\\text{QPS} \\times \\text{单请求延迟(s)}}{\\text{单实例并发度}} \\times (1+\\text{余量}) \\right\\rceil"),
        P("其中<strong>单实例并发度</strong>本身也要拆：GPU 推理常见的做法是动态批处理（dynamic batching），"
          "单卡在延迟预算内能吃下的并发请求数 ≈ 延迟预算 ÷ 单请求延迟 × 批处理效率折扣（通常 0.5–0.8）。"
          "<strong>举例</strong>：TSR 云端复检服务 QPS=200，单请求（batch=1）延迟 10ms，SLA 要求 p99 < 50ms，"
          "单卡在 50ms 内可接受批处理后约等效于 3–4 个并发 → 需要实例数 ≈ 200×0.01/3.5×1.3 ≈ 0.74 → 至少 2 台（含余量与高可用最低两台）。"),
        H3("② 参数量 → 显存"),
        P("推理场景的心算三步：<strong>①权重（参数量×2 字节 fp16）②KV cache / 激活（随 batch 与序列长/分辨率线性或更高增长）"
          "③框架与 CUDA context 固定开销（几百 MB 到 1–2GB）</strong>。"
          "举例：一个 8M 参数的 TSR 检测器，权重仅 16MB，即使算上激活与框架开销，单卡显存占用通常在几百 MB 量级——"
          "<strong>这也是为什么车端 SoC 的十几 GB 显存对纯检测模型绰绰有余，真正吃显存的是同时跑的多个感知任务叠加</strong>。"),
        H3("③ FLOPs → 算力（需要多少张卡）"),
        MATH("\\text{所需算力(TFLOPS)} = \\frac{\\text{单次推理 FLOPs} \\times \\text{QPS}}{\\text{硬件利用率} \\times 10^{12}}"),
        P("举例：单帧检测推理 4 GFLOPs（TSR 轻量检测器量级），QPS=1000（多路相机汇总到云端做复检），"
          "利用率按保守的 0.3 算：所需算力 ≈ 4×10⁹×1000 / (0.3×10¹²) ≈ 13.3 TFLOPS——"
          "<strong>不到一张 T4 峰值算力（65 TFLOPS）的四分之一，说明瓶颈很可能不在算力而在延迟/调度开销</strong>，"
          "这个「瓶颈定位」的结论本身就是加分点。"),
        H3("④ 成本 / 千次推理"),
        MATH("\\text{成本/千次} = \\frac{\\text{单卡每小时成本}}{\\text{该卡每小时可处理的请求数}} \\times 1000"),
        P("举例：一张云端推理卡每小时成本按几元到十几元量级估（视厂商与是否包年），若单卡每秒能处理 100 次推理（考虑批处理），"
          "每小时约 36 万次，则每千次成本 ≈ 单卡时价 ÷ 360 ——量级通常在<strong>分钱到一角钱/千次</strong>这个区间。"
          "<strong>这个数字的价值在于横向比较</strong>：如果某个方案算出每千次成本是别的方案的 10 倍，"
          "即使精度更高，也要在设计里主动提出「这是否值得」。"),
        TABLE(["估算目标", "核心公式（口诀）", "最容易出错的常数"], [
            ["实例数", "QPS × 延迟 ÷ 并发度 × 余量", "忘记乘余量系数（通常 1.3–2×，覆盖峰值与容错）"],
            ["显存", "参数量 × 2字节 + 激活 + 固定开销", "只算权重、漏算激活——大分辨率/大 batch 时激活占大头"],
            ["算力", "FLOPs × QPS ÷ (利用率 × 峰值)", "用峰值算力代入而不打利用率折扣（0.2–0.5）"],
            ["成本", "单卡时价 ÷ 单卡吞吐", "用「理论最大吞吐」而非「SLA 约束下的实际吞吐」"],
        ]),
        CALLOUT("danger", "<strong>数量级心算最容易在「单位换算」上翻车</strong>：GB 与 Gb 混淆（差 8 倍）、"
                          "毫秒与秒混淆（差 1000 倍）、TFLOPS 与 GFLOPS 混淆（差 1000 倍）。"
                          "面试里报错一个单位比算错一个系数更致命，因为它暴露「口算习惯不严谨」。"
                          "<strong>推荐做法：每算一步都显式写出单位，并在心里过一遍「这个数字大概是多少个 0」</strong>。"),
        DUAL(
            "怎么在白板上呈现这套心算？<strong>先说公式骨架，再逐项代入锚点数字，最后给一个带「大约」的结论并主动说校验方法</strong>："
            "「QPS 200，单请求 10ms，按并发 3.5 折算，大概需要一台多一点，我会配 2 台留余量。"
            "我可以用另一条路径校验一下：按算力账算出来所需 TFLOPS 远小于单卡峰值，说明瓶颈应该在延迟而不是吞吐，两条路径结论一致。」",
            "这套心算的理论基础是<span class=\"term\">利特尔法则</span>（Little's Law）：<strong>系统内平均请求数 = 到达率 × 平均停留时间</strong>，"
            "即 $L=\\lambda W$。实例数估算本质就是在给定 $\\lambda$（QPS）与 $W$（延迟 SLA）时反推需要多大的服务能力 $L$，"
            "再除以单实例能提供的服务能力。<strong>这是一条比死记硬背公式更可靠的推导起点</strong>——"
            "忘记具体公式时，回到 $L=\\lambda W$ 总能重新推出来。",
        ),
    ])),

    # ============================================================== 5
    ("latency-budget", "延迟预算分解与关键路径", "".join([
        P("延迟预算分解要回答的问题是：<strong>SLA 给的总延迟，怎么分给每一个子系统，谁是瓶颈</strong>。"
          "这一步的方法论只有一句话：<strong>先画出关键路径（critical path），只有关键路径上的延迟才计入端到端延迟</strong>——"
          "并行发生的分支不叠加。"),
        ASCII("""SLA：端到端 P99 < 100 ms（相机曝光到规控收到结构化输出）
┌───────────┬───────────┬────────────┬───────────┬────────────┬──────────┐
│ 预处理     │ H2D 拷贝   │ 模型推理    │ 后处理NMS  │ 跟踪关联    │ 序列化    │
│  4 ms      │  2 ms      │  12 ms      │  3 ms      │  2 ms       │  1 ms     │
└───────────┴───────────┴────────────┴───────────┴────────────┴──────────┘
   合计 24 ms（关键路径，串行）——            剩余 76 ms 预算去哪了？
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │  并行分支：多帧置信度累积在近线异步进行，不占关键路径 │
                    │  另一并行分支：日志与监控埋点异步写，不阻塞主链路     │
                    └─────────────────────────────────────────────────┘
   → 关键路径 24ms << SLA 100ms，说明这条链路有充分余量应对：
     ① 多相机竞争算力时的排队延迟  ② 偶发的 GC/调度抖动  ③ 后续新增子任务"""),
        P("这张图揭示一个常被忽略的事实：<strong>SLA 留的余量，本质上是给「不在关键路径上但会偶发挤占资源」的东西留的</strong>——"
          "多任务抢占、GC 停顿、温度降频（见 C60-05）、以及未来新增功能。<strong>面试里主动提到「留出的余量准备应对什么」"
          "比只报一个总数更有说服力</strong>。"),
        TABLE(["子系统", "典型延迟量级", "决定它的因素", "优化手段"], [
            ["预处理（resize/归一化/letterbox）", "1–5 ms", "分辨率、是否 GPU 侧处理", "GPU 侧预处理、算子融合，见 C60-01"],
            ["H2D/D2H 拷贝", "0.5–3 ms", "数据量、是否零拷贝/统一内存", "锁页内存、异步流、零拷贝，见 C60-05"],
            ["模型推理", "3–20 ms", "参数量、精度（fp16/int8）、batch", "量化（见 C60-03）、结构裁剪、decoder 层数可调（见 C53-04）"],
            ["后处理（NMS/解码）", "1–5 ms", "候选框数量、是否 GPU 侧 NMS", "class-agnostic NMS、EfficientNMS plugin（见 C60-04）"],
            ["跨进程/网络传输（若跨服务）", "1–10 ms（同机房）；几十~上百 ms（跨地域）", "是否同机部署、序列化格式", "同机部署、二进制序列化替代 JSON"],
        ]),
        CALLOUT("intuition", "<strong>关键路径识别的心法：先问「如果这个子系统突然变成 0 延迟，端到端延迟会不会跟着变」。</strong>"
                             "如果答案是否（因为它和别的东西并行发生，被别的分支盖过），它就不在关键路径上，"
                             "优化它对端到端延迟没有帮助——这是很多人做了「假优化」的根源：优化了一个不在关键路径上的模块，"
                             "端到端延迟纹丝不动，还以为是测量出了问题。"),
        DUAL(
            "延迟预算分解在白板上要<strong>先给总数、再拆分、最后指出瓶颈在哪</strong>，顺序不能反："
            "「总预算 100ms，我先拆到子系统：预处理 4、拷贝 2、推理 12、后处理 3、跟踪 2，关键路径合计 24ms。"
            "推理占了关键路径的一半，如果以后要加功能，优化重点应该先看推理这一块。」",
            "更严谨地说，端到端延迟的<strong>尾延迟（p99）不等于各阶段 p99 之和</strong>——"
            "如果各阶段延迟近似独立，端到端 p99 通常比逐阶段 p99 简单相加更极端（多个阶段同时抖动的概率虽低但影响叠加）。"
            "工程上通常用<strong>各阶段 p50 之和 + 单独测量端到端 p99 做校验</strong>，而不是天真地把逐阶段 p99 相加，"
            "这也是 C60-05 里「测延迟的正确姿势」一节的结论在系统设计层面的应用。",
        ),
    ])),

    # ============================================================== 6
    ("batching-scaling", "批处理与缓存、扩缩容与降级方案", "".join([
        P("扛住流量峰值、扛住模型偶发失效，靠的是三件事：<strong>批处理与缓存（提升吞吐）、扩缩容（应对负载变化）、"
          "降级（应对失效而不是假装它不会发生）</strong>。三者缺一，方案在面试官眼里就是「没考虑生产环境」。"),
        H3("批处理与缓存"),
        TABLE(["技术", "解决什么问题", "TSR 场景怎么用", "代价"], [
            ["动态批处理（dynamic batching）", "GPU 利用率低（batch=1 时算力吃不满）", "多路相机的检测请求在几毫秒窗口内攒批一起推理", "增加排队延迟，窗口设置需要在吞吐与延迟间取舍"],
            ["结果缓存", "重复计算（同一场景短时间内被重复请求）", "同一标志连续帧的分类结果可复用，无需每帧重跑分类器（见 C55-02 两级方案）", "缓存失效策略要设计好，否则会用旧结果掩盖真实变化"],
            ["特征复用", "多任务共享 backbone 特征，避免重复前向", "检测/分割/深度估计共享同一 backbone 输出", "耦合多个任务的发布节奏，一个任务改动可能影响全部"],
        ]),
        H3("扩缩容"),
        P("云端服务用<strong>基于 QPS/延迟指标的自动扩缩容</strong>（当 p99 延迟或队列长度超阈值时加实例），"
          "车端没有「扩容」这个选项——<strong>车端只有一块固定的 SoC，扩缩容变成了「算力预算内的任务调度」</strong>："
          "TSR 只是众多感知任务之一，高优先级任务（避障）挤占算力时，TSR 必须能在更少算力下继续工作，"
          "这直接引出降级方案。"),
        H3("降级方案：模型降级、特征降级、兜底规则"),
        TABLE(["降级层级", "具体做法", "触发条件", "代价与恢复"], [
            ["<strong>模型降级</strong>", "切换到更小/更快的模型（如 decoder 6 层→3 层，见 C53-04；或退回上一个稳定版本）", "延迟超阈值、显存不足、新模型上线后指标异常", "精度下降但仍有输出，优于无输出；需要提前验证降级模型的最低可接受精度"],
            ["<strong>特征降级</strong>", "跳过非必要的增强计算（如关闭多帧融合，只用单帧结果；关闭高分辨率精检分支）", "算力被高优先级任务抢占、近线服务延迟", "稳定性/召回下降，但延迟可控；需要有滞后感知（用户/下游应知道当前是降级状态）"],
            ["<strong>兜底规则</strong>", "模型完全不可用时，用简单规则输出保守结果（如「未识别到限速牌时不解除上一个已知限速约束」）", "模型服务崩溃、推理超时、置信度长期为 0", "规则通常保守但绝不能是「什么都不做」——见 C59-04 的安全兜底层"],
        ]),
        CALLOUT("danger", "<strong>没有降级方案的系统设计，在车规场景里是不及格的，无论模型精度多高。</strong>"
                          "面试官会假设「模型一定会挂」，然后问「挂了怎么办」——如果答案是「不会挂」，"
                          "这个回答本身就是危险信号。<strong>正确的姿势是主动画出降级路径，并说明每一级降级对应的精度/延迟代价</strong>。"),
        ASCII("""正常路径:  相机 → 检测(全精度) → 跟踪 → 多帧融合 → 高置信输出
                            │ 延迟超标/显存不足
                            ▼
模型降级:  相机 → 检测(轻量版) → 跟踪 → 多帧融合 → 输出(精度略降，仍标注"降级中")
                            │ 轻量版仍不可用/推理服务崩溃
                            ▼
特征降级:  相机 → 检测(轻量版) → 跟踪(跳过多帧融合，单帧直出)
                            │ 检测服务完全不可用
                            ▼
兜底规则:  维持上一个已知安全状态（如已生效的限速约束不擅自解除），并触发告警"""),
        DUAL(
            "降级方案在白板上怎么讲？<strong>先说触发条件，再说降级动作，最后说恢复条件</strong>："
            "「如果延迟连续 3 帧超过 SLA，我会自动切到轻量检测模型；如果轻量模型也失败，"
            "跳过多帧融合直接用单帧结果；如果检测服务整体挂了，跟踪与规控维持上一个已知状态而不是清空，"
            "同时打告警。延迟恢复正常 10 秒后，逐级恢复到全精度路径。」",
            "更严谨地说，降级方案的设计要满足<strong>单调保守性</strong>：每一级降级的输出集合应该是"
            "上一级的一个安全子集，而不是引入新的不确定行为。这与 C65-03「不可逆 vs 可逆决策」的原则一致——"
            "降级动作本身应该是可逆的（能自动恢复），但降级期间的每一个决策不能是不可逆的危险动作。",
        ),
    ])),

    # ============================================================== 7
    ("monitoring", "监控与回滚：数据漂移、指标漂移、延迟分布", "".join([
        P("部署上线不是终点，<strong>监控是让「系统正在变差」这件事从「路测时才发现」变成「几分钟内被自动发现」的机制</strong>。"
          "面试里这一节常被压缩成一句「上监控」，但完整的监控体系要覆盖三类完全不同的漂移。"),
        TABLE(["监控对象", "度量什么", "为什么会漂移", "典型告警设计"], [
            ["<strong>数据漂移</strong>", "输入分布是否变化（如夜间占比突增、新地区标志样式变化）", "季节/地域/传感器更新导致输入分布偏离训练分布", "对关键输入特征（亮度均值、目标尺寸分布）设分位数告警，超出训练分布的 P1/P99 区间即报警"],
            ["<strong>指标漂移</strong>", "线上代理指标是否变化（置信度均值、检出率、FP/km，见 C55-05）", "模型退化、上游预处理悄悄改动、新版本模型引入回归", "对每个关键类别设独立的滑窗均值告警，避免被大类平均掩盖小类退化"],
            ["<strong>延迟分布</strong>", "p50/p99 是否漂移、是否出现静默回退（见 C60-05）", "硬件降频、负载升高、TensorRT 引擎与硬件/驱动不匹配", "对 p99 设硬阈值告警；额外监控「分区数」以发现静默回退"],
        ]),
        MATH("\\text{误报率控制}: \\quad \\Pr(\\text{告警} \\mid \\text{系统正常}) \\le \\alpha, \\qquad \\text{通常取 } \\alpha \\in [0.001, 0.01]\\ \\text{（每千/每百次检查允许一次误报）}"),
        P("<strong>阈值设定的核心矛盾</strong>：阈值太紧 → 告警疲劳（误报率高，值班人员开始无视告警）；"
          "阈值太松 → 漏报（真实退化没被发现，直到用户投诉或事故发生）。"
          "工程上常用<strong>训练/验证集上的历史分位数 + 滑窗平滑 + 连续 N 次超阈值才触发</strong>三件套来控制误报率，"
          "而不是对单次观测值设死阈值。"),
        H3("回滚：不是「删掉新版本」，是「验证过的降级路径」"),
        UL([
            "<strong>回滚必须在部署前就验证过，而不是出事时现推演</strong>——把回滚当成降级方案的一种（模型降级到上一个稳定版本）。",
            "<strong>回滚要有明确的触发条件与责任人</strong>：谁能决定回滚、需要多少证据、回滚决定要不要人工确认——"
            "全自动回滚适合有把握的场景（如延迟超标），涉及精度/安全判断的回滚通常要保留人工确认环节。",
            "<strong>灰度发布本身就是回滚成本最低的部署方式</strong>：先在 1% 流量/影子模式验证（见 C58-03），"
            "出问题时只影响很小范围，比全量发布后再回滚代价低得多——这也是为什么模块 03 强调 A/B 与影子模式。",
        ]),
        CALLOUT("warn", "<strong>「监控了平均值」是最常见的监控盲区。</strong>平均值会掩盖尾部退化——"
                        "一个占比 2% 的稀有标志类召回从 90% 掉到 40%，在整体 mAP 上可能只掉 0.5 个点，"
                        "但对下游安全动作是致命的。<strong>关键类别必须有独立的监控线，不能只看聚合指标</strong>——"
                        "这与 C55-05「为什么 mAP 不足以衡量 TSR」是同一个论证在监控层面的应用。"),
        DUAL(
            "白板上讲监控，建议按「三类漂移 + 告警阈值设计 + 回滚触发条件」的顺序过一遍，最后加一句"
            "「关键类别单独监控，不能只看聚合指标」——这一句往往是加分句，因为大部分候选人只会说「上 Grafana 看指标」。",
            "更严谨地说，监控系统本身也要满足<strong>可观测性的三个支柱</strong>（metrics/logs/traces）：\n"
            "指标（metrics）负责「有没有问题」的快速判断，日志（logs）负责「具体哪一条请求出的问题」，"
            "追踪（traces）负责「问题出在链路的哪一段」——延迟预算分解（第 5 节）里的每一段都应该有独立的 trace span，"
            "否则出问题时只能定位到「端到端变慢了」而无法定位到具体子系统。",
        ),
    ])),

    # ============================================================== 8
    ("car-cloud", "车端与云端的分工：为什么不能什么都放车上，也不能什么都放云上", "".join([
        P("TSR 这类车规感知系统的服务架构，本质上是一个<strong>车端-云端的分工问题</strong>，而不是纯粹的云端服务设计。"
          "分工的判据只有一条：<strong>这个计算需不需要在没有网络的情况下也能正确工作</strong>。"),
        TABLE(["维度", "车端", "云端", "分工原则"], [
            ["延迟要求", "个位数到几十毫秒（硬实时）", "可以容忍百毫秒到秒级", "凡是直接影响当前帧决策的，必须在车端"],
            ["算力预算", "固定、共享给多个感知任务（见第 6 节）", "近乎弹性（可加机器）", "算力密集但不紧急的任务（大模型复检、离线训练）放云端"],
            ["网络可用性", "不可假设网络时刻在线", "假设网络可用", "任何「网络断了会导致安全问题」的功能都不能依赖云端"],
            ["模型规模", "受限于车端 SoC 显存与算力，通常是小模型/蒸馏后的模型", "可以跑大模型（VLA 云端大模型，见 C59-01）", "云端大模型的知识蒸馏到车端小模型，而不是车端直接跑大模型"],
            ["数据回传", "受带宽限制，只能回传触发片段（见 C58-03）", "接收车队回传数据，驱动数据闭环（见 C58-05）", "车端做「筛选」，云端做「深加工」"],
        ]),
        CALLOUT("intuition", "<strong>一句话记住车云分工：车端负责「这一帧必须现在决定的事」，云端负责「攒起来一起做更好」。</strong>"
                             "TSR 检测本身必须在车端；但「这个新标志样式我们要不要专门训一版模型」这种决策，"
                             "完全可以云端慢慢做。混淆两者的后果是要么车端算力扛不住，要么因为等云端而错过决策时机。"),
        DUAL(
            "在系统设计面试里，一旦画出「车端-云端」两个框，就要主动说明<strong>网络断开时车端能不能独立工作到「安全」的程度</strong>——"
            "这一句话直接回应了车规系统对「优雅降级」的最高要求：不是「效果好」，而是「网络断了也不会做出危险决策」。",
            "更严谨地说，车云协同架构本质上是一种<strong>分层容错设计</strong>：车端是保证安全下限的「快系统」，"
            "云端是提升体验上限的「慢系统」（呼应 C59-04 的快慢双系统）。评估这类架构时，"
            "要分别验证「快系统单独工作时是否仍安全」与「慢系统失效时快系统是否能优雅接管」两条独立性质，"
            "而不是把两层耦合在一起测试。",
        ),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("服务与容量估算这套心算方法论已经相当成熟，但下面几个方向仍在快速变化，值得知道它们的存在。"),
        UL([
            "<strong>推理服务的成本模型正在被 MoE 与推测解码（speculative decoding）重写。</strong>"
            "传统「参数量 → 显存 → 成本」的线性心算对稀疏激活模型不再直接适用——"
            "MoE 模型的显存占用接近总参数量，但推理算力只对应激活参数量，两者要分开估算。"
            "这对 VLA 云端大模型的成本估算（见 C59-05）影响尤其大。",
            "<strong>车端多任务算力调度缺少公开的量化方法论。</strong>已知「车端算力常被多任务分摊」是共识，"
            "但如何在系统设计阶段就为「TSR 之外还有 N 个感知任务」做出可验证的算力预留，"
            "目前更多是各家的内部工程经验，缺少公开的调度模型与 benchmark。",
            "<strong>降级方案的形式化验证仍是空白。</strong>「降级动作是安全子集」目前主要靠工程规范与人工评审保证，"
            "还没有成熟的自动化工具能验证一条降级路径在所有触发场景下都不会引入新的危险行为——"
            "这与形式化方法（formal verification）在自动驾驶软件栈的应用是同一个更大的开放问题的一角。",
            "<strong>「监控什么」正在从人工设计指标转向自动发现异常模式。</strong>"
            "传统监控依赖工程师预先想好告警规则，而基于无监督异常检测的监控（自动发现「以前没见过的输入分布」"
            "而不需要预先定义规则）正在成为长尾场景漏检的补充手段，但误报率控制仍是主要瓶颈。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Martin Kleppmann, <em>Designing Data-Intensive Applications</em>"
                         "（O'Reilly）第 1 章「Reliable, Scalable, and Maintainable Applications」——"
                         "本模块「关键路径」「尾延迟」「容错设计」的方法论根基。"
                         "<strong>★</strong> NVIDIA, <em>Triton Inference Server</em> 官方文档「Dynamic Batching」一节——"
                         "动态批处理的工程参数与延迟-吞吐权衡的第一手资料。"
                         "<strong>★</strong> Google SRE Book，<em>Monitoring Distributed Systems</em> 一章——"
                         "「四个黄金信号」（延迟/流量/错误/饱和度）是本模块监控体系设计的行业标准起点。</p>"
                         "<p>相邻课程：<strong>C53-04/05</strong>（延迟拆解与选型的原始出处，本模块只引用结论）、"
                         "<strong>C58-03/05</strong>（触发器与闭环验证，本模块的近线/离线分工直接沿用其结论）、"
                         "<strong>C59-04/05</strong>（快慢双系统与云端-车端蒸馏，本模块「车端云端分工」一节的延伸）、"
                         "<strong>C60</strong>（部署一致性与延迟工程，本模块「锚点数字表」里硬件相关数字的技术细节出处）、"
                         "<strong>C65-01</strong>（Fermi 估算的通用方法论，本模块是它在服务容量场景下的专项应用）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 04 · 服务、部署与容量估算（架构分层 / 锚点数字 / 容量心算 / 延迟预算 / 降级 / 监控）

目标：把「容量估算」从「凭感觉说个数」变成**几行可以运行、可以断言的心算工具**。

本 notebook 你会亲手实现：
1. **锚点数字表** —— 硬件算力/带宽、模型参数量/延迟、存储/带宽的量级速查（内置为数据结构）
2. **容量估算器** —— QPS→实例数、参数量→显存、FLOPs→算力、成本/千次推理，并做**两条独立路径互相校验**
3. **延迟预算分解器** —— 给一组子系统延迟，找出关键路径与瓶颈
4. **降级策略决策表** —— 给定触发信号，查表输出该降到哪一级
5. **监控告警阈值设定器** —— 给历史分布，按目标误报率反推告警阈值
6. **一个完整案例**：TSR 云端复检服务的端到端容量估算演示

> 心智模型：**每一个架构框图上的箭头，都要能配一个数量级数字；说不出数字的架构图只是一幅画。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math, random
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'percentile')
print('\\n✅ 环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · 锚点数字表：把「量级」内置成数据结构

背这些表的目的不是精确，是**量级不错**（差一个数量级 = 错；差 2 倍 = 可接受）。"""),

    code("""# 硬件：峰值算力(TFLOPS, fp16/bf16) / 显存带宽(GB/s) / 典型显存(GB)
HW = {
    'T4':        dict(tflops=65,  bw_gb_s=320,  vram_gb=16),
    'A10_L4':    dict(tflops=140, bw_gb_s=450,  vram_gb=24),
    'A100':      dict(tflops=312, bw_gb_s=2000, vram_gb=80),
    'H100':      dict(tflops=990, bw_gb_s=3350, vram_gb=80),
    'car_soc':   dict(tflops=150, bw_gb_s=200,  vram_gb=12),   # 峰值；可用算力见下面的折扣
}
CAR_SOC_USABLE_FRACTION = 0.2   # 车端可用算力常只有峰值的 10-30%，取中间值 0.2 做心算

# 模型：参数量(M) / fp16 权重显存(MB) / 典型单请求延迟(ms, batch=1, 推理卡)
MODELS = {
    'tsr_tiny_det':   dict(params_m=6,    vram_mb=12,   latency_ms=6),
    'rtmdet_m':       dict(params_m=35,   vram_mb=70,   latency_ms=14),
    'resnet50_cls':   dict(params_m=25.6, vram_mb=51,   latency_ms=3),
    'vit_b16':        dict(params_m=86,   vram_mb=172,  latency_ms=10),
    'vla_7b':         dict(params_m=7000, vram_mb=14000, latency_ms=80),
}

# 带宽/存储量级
BANDWIDTH = dict(
    image_1080p_jpeg_mb=0.5,
    image_1080p_raw_mb=6.0,
    camera_fps=30,
    camera_count=6,
    cellular_uplink_mbps=10,     # 车云上行，保守估计
    datacenter_gbps=50,
)

assert HW['T4']['tflops'] < HW['A100']['tflops'] < HW['H100']['tflops']
assert MODELS['tsr_tiny_det']['params_m'] < MODELS['rtmdet_m']['params_m']
print('锚点数字表就位：', len(HW), '种硬件 ·', len(MODELS), '个模型量级 ·', len(BANDWIDTH), '条带宽/存储数字')
for name, d in HW.items():
    print(f'  {name:<10} {d["tflops"]:>6} TFLOPS  {d["bw_gb_s"]:>6} GB/s  {d["vram_gb"]:>3} GB')"""),

    md("""## 2 · 容量估算器：QPS → 实例数

用 Little's Law（$L=\\lambda W$）的变形：实例数 = ⌈QPS × 延迟(s) / 单实例并发度 × 余量⌉。"""),

    code("""def instances_needed(qps, latency_ms, concurrency_per_instance, margin=1.3):
    \"\"\"QPS -> 所需实例数（向上取整，含余量系数）。\"\"\"
    latency_s = latency_ms / 1000.0
    raw = qps * latency_s / concurrency_per_instance
    return math.ceil(raw * margin)

# 案例：TSR 云端复检服务，QPS=200，单请求(batch=1)延迟10ms，
# SLA p99<50ms 下单卡批处理等效并发≈3.5
n = instances_needed(qps=200, latency_ms=10, concurrency_per_instance=3.5, margin=1.3)
assert n == 1, n   # 200*0.01/3.5*1.3 = 0.743 -> ceil = 1
n_hifi = instances_needed(qps=200, latency_ms=10, concurrency_per_instance=3.5, margin=1.3)
print(f'QPS=200, 延迟10ms, 并发3.5, 余量1.3x -> 至少 {n} 台（高可用通常再加 1 台冗余 -> 实际部署 2 台）')

# 反例：QPS 涨到 5000 时
n2 = instances_needed(qps=5000, latency_ms=10, concurrency_per_instance=3.5, margin=1.3)
assert n2 == 19, n2
print(f'QPS=5000 时 -> {n2} 台，说明流量涨 25 倍，实例数也约涨 25 倍（线性关系，符合 Little\\'s Law 直觉）')
assert n2 / n >= 15   # 流量涨25倍，实例数量级也该跟着涨，而不是不变或超线性暴涨
print('\\n✅ 容量估算器（QPS→实例数）就位。')"""),

    md("""## 3 · 容量估算器：参数量 → 显存、FLOPs → 算力"""),

    code("""def vram_gb(params_m, bytes_per_param=2, activation_overhead_mb=200, framework_overhead_mb=500):
    \"\"\"推理场景显存估算(GB)：权重 + 激活开销 + 框架固定开销。\"\"\"
    weight_mb = params_m * 1e6 * bytes_per_param / 1e6   # 参数量(M) * 1e6 -> 个数 * bytes / 1e6 -> MB
    total_mb = weight_mb + activation_overhead_mb + framework_overhead_mb
    return total_mb / 1024

v_tiny = vram_gb(MODELS['tsr_tiny_det']['params_m'])
v_vla = vram_gb(MODELS['vla_7b']['params_m'], activation_overhead_mb=2000, framework_overhead_mb=1000)
assert v_tiny < 1.0, v_tiny        # 几百 MB 量级
assert 13 < v_vla < 18, v_vla      # 7B fp16 权重约 14GB，加上开销略高
print(f'tsr_tiny_det 显存估算 ≈ {v_tiny:.2f} GB  (对应 notebook MODELS 表里的 vram_mb={MODELS["tsr_tiny_det"]["vram_mb"]}MB 权重量级一致)')
print(f'vla_7b       显存估算 ≈ {v_vla:.2f} GB  (单卡 24GB 推理卡装得下，但训练需要数倍显存)')

def tflops_needed(flops_per_infer, qps, utilization=0.3):
    \"\"\"FLOPs -> 所需算力(TFLOPS)，按硬件利用率折扣。\"\"\"
    return flops_per_infer * qps / (utilization * 1e12)

t = tflops_needed(flops_per_infer=4e9, qps=1000, utilization=0.3)
assert 10 < t < 16, t
print(f'\\n单帧4GFLOPs, QPS=1000, 利用率0.3 -> 需要算力 ≈ {t:.1f} TFLOPS')
print(f'  对比 T4 峰值 {HW["T4"]["tflops"]} TFLOPS -> 占用比例 {t/HW["T4"]["tflops"]*100:.0f}%，一张卡绰绰有余')
print('  结论：瓶颈大概率不在算力，而在延迟/调度开销 —— 这个判断本身就是加分点。')
print('\\n✅ 容量估算器（显存/算力）就位。')"""),

    md("""## 4 · 两条独立路径互相校验

数量级校验的核心方法：**用两条独立的估算路径算同一个量，量级应该吻合**。这是 C65-01 双路径校验的服务容量专项应用。"""),

    code("""def cross_check_instances(qps, latency_ms, single_gpu_flops, flops_per_infer, utilization=0.3):
    \"\"\"路径A：按延迟/并发估算；路径B：按FLOPs/算力估算。两条路径应给出同一数量级的实例数。\"\"\"
    # 路径 A：显式并发度心算（假设 SLA 下单卡等效并发 3.5，与上面案例一致）
    n_a = instances_needed(qps, latency_ms, concurrency_per_instance=3.5, margin=1.3)
    # 路径 B：按算力总需求 / 单卡可用算力
    total_tflops_needed = flops_per_infer * qps / (utilization * 1e12)
    usable_tflops_per_gpu = single_gpu_flops * utilization
    n_b = math.ceil(total_tflops_needed / usable_tflops_per_gpu * 1.3)
    return n_a, n_b

na, nb = cross_check_instances(qps=200, latency_ms=10, single_gpu_flops=HW['T4']['tflops'],
                                 flops_per_infer=4e9, utilization=0.3)
print(f'路径A（延迟/并发） -> {na} 台')
print(f'路径B（FLOPs/算力）-> {nb} 台')
# 两条路径量级应该吻合（相差不超过一个数量级，理想情况下相差不超过2-3倍）
ratio = max(na, nb) / max(min(na, nb), 1)
assert ratio <= 5, f'两条路径结论相差过大({ratio:.1f}x)，说明某个估算假设有误，需要回头检查'
print(f'比值 {ratio:.1f}x，在可接受范围内 -> 两条路径互相印证，估算可信')
print('\\n✅ 双路径校验就位：这是面试里「我用另一条路径验证一下」这句话的具体实现。')"""),

    md("""## 5 · 延迟预算分解器：找关键路径与瓶颈"""),

    code("""def critical_path_analysis(stages, sla_ms):
    \"\"\"stages: [(名字, 延迟ms, 是否在关键路径上), ...]
    返回 (关键路径总延迟, 剩余余量, 瓶颈stage名, 占比)\"\"\"
    on_path = [(name, ms) for name, ms, crit in stages if crit]
    total = sum(ms for _, ms in on_path)
    margin = sla_ms - total
    bottleneck = max(on_path, key=lambda x: x[1])
    share = bottleneck[1] / total
    return total, margin, bottleneck[0], share

STAGES = [
    ('预处理', 4, True), ('H2D拷贝', 2, True), ('模型推理', 12, True),
    ('后处理NMS', 3, True), ('跟踪关联', 2, True), ('序列化', 1, True),
    ('多帧滑窗累积(近线,并行)', 50, False),   # 不在关键路径上
    ('日志埋点(异步,并行)', 5, False),
]

total, margin, bn, share = critical_path_analysis(STAGES, sla_ms=100)
assert total == 24, total
assert margin == 76, margin
assert bn == '模型推理'
assert abs(share - 0.5) < 1e-9, share
print(f'关键路径合计 {total} ms，SLA 100ms 剩余余量 {margin} ms')
print(f'瓶颈子系统: {bn}（占关键路径 {share*100:.0f}%）')
print('并行分支（多帧滑窗、日志埋点）不计入端到端延迟，因为它们不在关键路径上。')

# 反直觉检验：如果把不在关键路径上的模块延迟"优化"为0，端到端延迟不应该变化
stages_optimized_wrong_target = [(n, 0 if n == '多帧滑窗累积(近线,并行)' else m, c) for n, m, c in STAGES]
total2, _, _, _ = critical_path_analysis(stages_optimized_wrong_target, sla_ms=100)
assert total2 == total, '优化非关键路径模块不应改变端到端关键路径延迟'
print('\\n✅ 验证「假优化」陷阱：优化不在关键路径上的模块，端到端延迟纹丝不动。')"""),

    md("""## 6 · 降级策略决策表"""),

    code("""DEGRADE_LEVELS = ['normal', 'model_degrade', 'feature_degrade', 'fallback_rule']

def degrade_decision(latency_p99_ms, sla_ms, consecutive_breaches, service_alive, lite_model_alive):
    \"\"\"按触发条件查表返回应处于哪个降级层级。\"\"\"
    if not service_alive:
        return 'fallback_rule'
    if not lite_model_alive and latency_p99_ms > sla_ms:
        return 'feature_degrade'
    if latency_p99_ms > sla_ms and consecutive_breaches >= 3:
        return 'model_degrade'
    return 'normal'

cases = [
    dict(latency_p99_ms=30, sla_ms=100, consecutive_breaches=0, service_alive=True, lite_model_alive=True, want='normal'),
    dict(latency_p99_ms=120, sla_ms=100, consecutive_breaches=3, service_alive=True, lite_model_alive=True, want='model_degrade'),
    dict(latency_p99_ms=120, sla_ms=100, consecutive_breaches=1, service_alive=True, lite_model_alive=True, want='normal'),  # 未连续3次，不降级
    dict(latency_p99_ms=150, sla_ms=100, consecutive_breaches=5, service_alive=True, lite_model_alive=False, want='feature_degrade'),
    dict(latency_p99_ms=999, sla_ms=100, consecutive_breaches=10, service_alive=False, lite_model_alive=False, want='fallback_rule'),
]
for c in cases:
    want = c.pop('want')
    got = degrade_decision(**c)
    assert got == want, (c, got, want)
    print(f'{c} -> {got}')
print('\\n✅ 降级决策表就位：触发条件 -> 降级层级是确定性映射，不是临场发挥。')"""),

    md("""## 7 · 监控告警阈值设定器：按目标误报率反推阈值"""),

    code("""def alert_threshold(history, target_fpr=0.01):
    \"\"\"history: 系统正常时的历史观测值数组。
    返回使得 P(观测值 > 阈值 | 正常) <= target_fpr 的阈值 —— 即 (1-target_fpr) 分位数。\"\"\"
    return float(np.percentile(history, (1 - target_fpr) * 100))

rng = np.random.default_rng(0)
# 模拟正常状态下的 p99 延迟观测（均值30ms，带一些抖动尾巴）
normal_latency = rng.gamma(shape=3.0, scale=10.0, size=10000)

thr_1pct = alert_threshold(normal_latency, target_fpr=0.01)
thr_01pct = alert_threshold(normal_latency, target_fpr=0.001)
assert thr_01pct > thr_1pct, '误报率要求越严格，阈值应该越高（更不容易触发）'

# 验证：用这个阈值反过来算，正常数据里超过阈值的比例应该约等于目标误报率
fpr_actual = float((normal_latency > thr_1pct).mean())
assert abs(fpr_actual - 0.01) < 0.01, fpr_actual   # 允许采样误差
print(f'目标误报率 1%   -> 阈值 {thr_1pct:.1f} ms  (实测误报率 {fpr_actual*100:.2f}%)')
print(f'目标误报率 0.1% -> 阈值 {thr_01pct:.1f} ms')
print('\\n✅ 阈值设定器就位：用历史分位数反推阈值，而不是拍脑袋定一个绝对数字。')"""),

    md("""## ✏️ 练习 1：容量估算的成本账

实现 `cost_per_thousand(gpu_hourly_cost, throughput_per_sec)`，返回每千次推理的成本（元）。

公式：每小时能处理 `throughput_per_sec * 3600` 次；每千次成本 = `gpu_hourly_cost / (throughput_per_sec*3600) * 1000`。"""),

    code("""def cost_per_thousand(gpu_hourly_cost, throughput_per_sec):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
c1 = cost_per_thousand(gpu_hourly_cost=8.0, throughput_per_sec=100)
assert abs(c1 - 8.0/360000*1000) < 1e-9, c1
assert 0.02 < c1 < 0.03, c1     # 量级：几分钱/千次
c2 = cost_per_thousand(gpu_hourly_cost=8.0, throughput_per_sec=10)
assert c2 == c1 * 10           # 吞吐降到1/10，单位成本涨10倍
print(f'吞吐100/s -> {c1:.4f} 元/千次')
print(f'吞吐10/s  -> {c2:.4f} 元/千次  (吞吐降到1/10，成本涨10倍，符合线性直觉)')
print('\\n✅ 练习 1 通过：成本对比的价值在于横向比较不同方案，而不是精确到分。')"""),

    md("""## ✏️ 练习 2：延迟预算的关键路径校验器

实现 `sla_check(stages, sla_ms)`，返回 `(是否达标, 关键路径延迟, 余量)`。
`stages` 格式同第 5 节 `critical_path_analysis`。达标条件：关键路径延迟 <= sla_ms。"""),

    code("""def sla_check(stages, sla_ms):
    # TODO: 复用 critical_path_analysis 的思路（只算 crit=True 的部分）
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
ok, total, margin = sla_check(STAGES, sla_ms=100)
assert ok is True and total == 24 and margin == 76, (ok, total, margin)
ok2, total2, margin2 = sla_check(STAGES, sla_ms=20)
assert ok2 is False and total2 == 24 and margin2 == -4, (ok2, total2, margin2)
print(f'SLA=100ms -> 达标={ok}, 关键路径={total}ms, 余量={margin}ms')
print(f'SLA=20ms  -> 达标={ok2}, 关键路径={total2}ms, 余量={margin2}ms (负余量说明超标)')
print('\\n✅ 练习 2 通过。')"""),

    md("""## ✏️ 练习 3：车端可用算力折扣计算器

实现 `usable_tflops(hw_name, usable_fraction=None)`：返回 `HW[hw_name]['tflops'] * fraction`。
如果 `usable_fraction` 为 `None`，车端（`hw_name=='car_soc'`）用 `CAR_SOC_USABLE_FRACTION`，
其余硬件默认按 `0.35`（推理服务常见实测利用率）。"""),

    code("""def usable_tflops(hw_name, usable_fraction=None):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
u_car = usable_tflops('car_soc')
assert abs(u_car - HW['car_soc']['tflops'] * 0.2) < 1e-9, u_car
u_t4 = usable_tflops('T4')
assert abs(u_t4 - HW['T4']['tflops'] * 0.35) < 1e-9, u_t4
u_custom = usable_tflops('T4', usable_fraction=0.5)
assert abs(u_custom - HW['T4']['tflops'] * 0.5) < 1e-9, u_custom
print(f'car_soc 可用算力 ≈ {u_car:.1f} TFLOPS（峰值 {HW["car_soc"]["tflops"]} 的 20%）')
print(f'T4      可用算力 ≈ {u_t4:.1f} TFLOPS（峰值 {HW["T4"]["tflops"]} 的 35%）')
print('\\n✅ 练习 3 通过：车端峰值看似接近云端小卡，但可用算力折扣完全不同，千万别直接比峰值。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def cost_per_thousand(gpu_hourly_cost, throughput_per_sec):
    per_hour_requests = throughput_per_sec * 3600
    return gpu_hourly_cost / per_hour_requests * 1000"""),

    code("""# 练习 2 参考答案
def sla_check(stages, sla_ms):
    total, margin, _, _ = critical_path_analysis(stages, sla_ms)
    return total <= sla_ms, total, margin"""),

    code("""# 练习 3 参考答案
def usable_tflops(hw_name, usable_fraction=None):
    if usable_fraction is None:
        usable_fraction = CAR_SOC_USABLE_FRACTION if hw_name == 'car_soc' else 0.35
    return HW[hw_name]['tflops'] * usable_fraction"""),

    md("""---
## 🧪 真实工程胶囊：一份完整的容量估算演练模板（TSR 云端复检服务）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# TSR 云端复检服务 —— 完整容量估算演练模板（可直接改数字复用）
# ══════════════════════════════════════════════════════════════════════

# 【第一步：写下已知条件】
# 目标 QPS: 200（车队规模 × 触发率折算而来，见 C58-03）
# 单请求延迟(batch=1): 10ms（rtmdet_m 级别模型）
# SLA: p99 < 50ms
# 模型参数量: 35M -> fp16 权重 70MB

# 【第二步：显存估算】
# 显存 ≈ 70MB(权重) + 200MB(激活,视输入分辨率) + 500MB(框架开销) ≈ 0.75 GB
# 结论：单卡 16GB 显存可同时装载 ~20 个这样的模型实例（显存不是瓶颈）

# 【第三步：实例数估算（路径A：延迟/并发）】
# 50ms SLA 下单卡批处理等效并发 ≈ 3.5
# 实例数 = ceil(200 * 0.01 / 3.5 * 1.3) = 1 台 -> 高可用部署 2 台

# 【第四步：算力估算（路径B：FLOPs/利用率，交叉校验）】
# 单帧 FLOPs ≈ 4e9, QPS=200, 利用率0.3
# 所需算力 ≈ 4e9*200/(0.3*1e12) ≈ 2.7 TFLOPS，远小于 T4 的 65 TFLOPS
# 两条路径都指向"1-2台T4即可" —— 互相印证

# 【第五步：成本估算】
# T4 云端时价约 8 元/小时，单卡吞吐 ~100 req/s -> 成本 ≈ 0.022 元/千次
# 200 QPS * 3600s = 72万次/小时 -> 每小时成本 ≈ 16 元（2台）

# 【第六步：延迟预算分解 + 关键路径】
# 预处理4 + 拷贝2 + 推理12 + 后处理3 + 跟踪2 + 序列化1 = 24ms 关键路径
# SLA 50ms，余量 26ms —— 留给排队延迟与偶发抖动

# 【第七步：降级方案】
# 触发：p99连续3次超50ms -> 切轻量模型(tsr_tiny_det, 6ms)
# 再触发：轻量模型也不可用 -> 跳过近线多帧融合，单帧直出
# 再触发：服务整体不可用 -> 维持上一个已知安全状态 + 告警

# 【第八步：监控】
# 数据漂移：亮度均值/目标尺寸分布 P1/P99 越界告警
# 指标漂移：分类别置信度滑窗均值，误报率控制在1%（连续3次超阈值才触发，抑制抖动）
# 延迟分布：p99硬阈值 + 分区数监控（防静默回退，见C60-05）
'''
print(RECIPE)
for token in ['QPS', 'SLA', 'TFLOPS', '路径A', '路径B', '降级方案', '监控', 'C58-03', 'C60-05']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：显存/实例数/算力/成本/延迟分解/降级/监控 —— 完整八步')"""),

    md("""### 小结

- **服务与部署这一步，考的是「你的方案值多少台机器、多少钱、多快、坏了怎么办」**——
  能不能当场心算出数量级，是区分「纸上谈兵」与「能上线」的分水岭。
- **架构图要同时画数据流与控制流，并按在线/近线/离线三层分工**：
  等不了的放在线，能异步的放近线，能攒批的放离线；划分依据是 SLA，不是直觉。
- **锚点数字表要背，但记的是数量级不是小数点**：T4 几十 T 算力/几百 GB/s 带宽、
  A100 三百多 T/2TB 带宽是训练侧锚点；车端峰值看着高，**可用算力常只有峰值的 1-3 成**。
- **容量估算的四条心算公式**（QPS→实例数、参数量→显存、FLOPs→算力、成本/千次）
  背后是同一个 Little's Law（$L=\\lambda W$），**永远用两条独立路径互相校验**。
- **延迟预算要找关键路径而不是简单相加**：只有串行、阻塞的部分才计入端到端延迟；
  优化不在关键路径上的模块是最常见的「假优化」。
- **降级方案不是可选项**：模型降级/特征降级/兜底规则要形成单调保守的层级，
  监控要覆盖数据漂移/指标漂移/延迟分布三类，且**关键类别必须独立监控，不能只看聚合指标**。

下一站：**模块 05 · 案例库：六个完整设计演练** ——
把七步框架 + 需求澄清 + 数据设计 + 建模评测 + 本模块的容量估算，
串成六个可以照着走一遍的完整 45 分钟演练脚本。"""),
]
