# -*- coding: utf-8 -*-
"""C53 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "C18（目标检测基础：anchor / IoU / NMS / mAP / FPN）；numpy 基本操作"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("核心参考", "YOLO 系列原论文、RTMDet、RT-DETR / D-FINE；MMDetection 与 Ultralytics 的 benchmark 说明"),
    ("预计时长", "总览 30 分钟 + 跑 25 分钟"),
]

SECTIONS = [
    ("hard", "「实时」到底有多硬：三个不能谈判的约束", "".join([
        P("这门课讲<strong>实时目标检测器</strong>——YOLO 家族、RTMDet、RT-DETR。它们和 Faster R-CNN、Mask R-CNN 那一支的区别不在「精度」，而在<strong>它们是被一个外部给定的延迟预算逼出来的</strong>。理解这一点，后面每一代的设计选择才有解释。"),
        P("「实时」不是一个形容词，它是三个可量化、且<strong>同时成立</strong>的约束。缺任何一个，这门课里的绝大多数设计都会失去动机。"),
        TABLE(["约束", "具体是什么", "违反了会怎样", "谁给定的"], [
            ["<strong>① 延迟预算</strong>", "端到端 <code>p99</code> 必须小于分给你的那几毫秒——注意是 p99 不是均值，也不是 FPS", "帧被丢弃、下游拿到过期的感知结果、控制回路失稳", "<strong>外部硬性给定</strong>：相机帧率 × 感知任务排期"],
            ["<strong>② 显存与带宽</strong>", "车端 SoC 的显存要被十几个任务瓜分；带宽常常比算力更早成为瓶颈", "engine 构建失败、被迫降分辨率、多任务互相抢占", "硬件平台选型（几年前就定死了）"],
            ["<strong>③ 精度</strong>", "在<em>那个延迟预算下</em>能达到的最高精度，而不是不限时间能达到的精度", "漏检 / 误检直接变成安全事件", "产品与安全团队"],
        ]),
        DUAL(
            "三者的关系不是「三个目标做权衡」，而是<strong>「两个是硬约束、一个是优化目标」</strong>。延迟预算与显存是外部给你的，<em>你不能通过「模型再准一点」去和它们谈判</em>；精度才是你唯一能争取的东西。所以实时检测器的整个研究史，可以概括成一句话：<strong>在给定的毫秒数里，把 AP 往上抬</strong>。",
            "这也解释了为什么实时检测领域的论文长得和通用检测不一样：通用检测比的是「在 COCO 上的 AP」，实时检测比的是<strong>一条曲线</strong>——延迟为横轴、AP 为纵轴的帕累托前沿。<em>一个模型「更好」的严格定义是：它把这条前沿往左上方推了</em>。单点比 AP、或者单点比 FPS，都是没有意义的（第 4 节会把这件事讲透，而它是本课最容易在面试里加分的一个点）。",
        ),
        CALLOUT("intuition", "学完这门课你应当能当场回答：<strong>标签分配为什么比换 backbone 更能涨点？结构重参数化凭什么「训练时多分支、推理时单分支」还数值等价？YOLOv10 的一致双分配到底怎么去掉 NMS 的、和 DETR 的一对一匹配是不是一回事？RT-DETR 为什么敢说自己比 YOLO 快——它省掉的到底是哪一部分时间？给你一个 33 ms 的帧周期和一块被十几个任务瓜分的 SoC，你怎么为交通标志检测选型并给出论证？</strong>"),
    ])),
    ("budget", "33 毫秒的账：交通标志检测到底分到多少", "".join([
        P("先把「实时」这个词换成数字。车端前视相机常见 30 FPS，于是有一个不可协商的帧周期："),
        MATH("T_{\\text{frame}} = \\frac{1000}{30} \\approx 33.3\\ \\text{ms}"),
        P("但这 33.3 ms <strong>不是给检测器的</strong>。它要先被一串固定开销切掉，剩下的才是「全部感知任务」的时间窗，然后这个时间窗还要被十几个感知任务瓜分。交通标志检测（<span class=\"term\">TSR, Traffic Sign Recognition</span>）在这里面只是一个中等优先级的任务。"),
        ASCII("""一帧 33.3 ms 的真实去向（量产前视感知的典型量级）

|<--------------------------- 33.3 ms 帧周期 --------------------------->|
|  曝光+ISP+MIPI  |        全部感知任务         | 融合/跟踪/规控/执行 | 裕度 |
|     8.0 ms      |        16.3 ms              |      7.0 ms         | 2.0  |
                  |                             |
                  v                             v
                  +----- 感知的 16.3 ms 再被瓜分 -----+
                  | BEV 障碍物            45%   7.35 ms |
                  | 车道线/可行驶区域     20%   3.27 ms |
                  | **交通标志 TSR**      15%   2.45 ms |  <-- 本课的主角
                  | 红绿灯                10%   1.63 ms |
                  | 其他（静态障碍/占位） 10%   1.63 ms |
                  +-------------------------------------+

                        TSR 的端到端预算 = 2.45 ms

再把这 2.45 ms 拆开（这一层才是你能动的）：
  预处理 resize+letterbox+归一化 ......... 0.35 ms   14%
  H2D 拷贝 ............................... 0.15 ms    6%
  网络前向 backbone+neck+head ............ 1.45 ms   60%   <-- 换模型只能动这一段
  NMS .................................... 0.30 ms   12%   <-- 唯一随场景波动的一项
  解码/坐标还原/阈值 ..................... 0.12 ms    5%
  D2H 拷贝 ............................... 0.05 ms    2%
  ---------------------------------------------------
  合计 2.42 ms，余量 0.03 ms"""),
        TABLE(["这张账单告诉你什么", "推论"], [
            ["<strong>网络前向只占 60%</strong>", "论文里 <code>FPS</code> 那一栏通常只测这 60%。<em>「换个快一倍的 backbone」对端到端最多带来 30% 的收益</em>"],
            ["<strong>预处理 + 后处理占 39%</strong>", "它们在 CPU 上、常常没被优化、且是训练-部署不一致的头号来源（见 C60）"],
            ["<strong>NMS 是唯一「不确定」的一项</strong>", "耗时随候选框数近似 O(n²) 增长。空旷高速 40 个候选 vs 雨夜误检爆炸 900 个候选，<em>端到端延迟能差 40%</em>——这是 RT-DETR 存在的直接理由（模块 04）"],
            ["<strong>余量只有 0.03 ms</strong>", "任何「顺手加一个后处理」的想法都要先算账。<em>「反正只多 0.5 ms」在这里等于超预算 20 倍余量</em>"],
        ]),
        CALLOUT("danger", "<p>notebook 第 4 节会给你一个反直觉的结果：<strong>本课要讲的所有公开模型，没有一个能塞进 2.45 ms</strong>——最快的 YOLOv5-S 在 T4 上也要 4.5 ms。这不是账算错了，而是真实的量产约束长这样。<em>它逼出了三条工程路线</em>：① 用 tiny/nano 档 + INT8 + 更小输入分辨率把延迟压下去（代价是小目标掉点，见 C57）；② 把 TSR 降频到 10–15 Hz 跑（代价是首次检出距离变远、时序稳定性变差，见 C55 模块 04）；③ 只在 ROI（消失点附近的图像上半部）上跑（代价是漏掉侧向标志）。<strong>面试里被问「你怎么把这个模型放进车里」，说得出这三条并说得出各自的代价，就已经区分度很高了。</strong></p>", "预算是硬约束，不是建议值"),
    ])),
    ("threads", "三条主线：这门课其实只讲三件事", "".join([
        P("YOLO 从 v1 到 v10、加上 RTMDet 与 RT-DETR，表面上是十几个模型、上百个改动。但<strong>真正影响精度与延迟的机制只有三条，其余都是围绕它们的工程包装</strong>。把这三条抓住，你就能在面试里对任何一个新模型做出判断，而不是背名字。"),
        TABLE(["主线", "它回答的问题", "关键节点", "本课在哪讲"], [
            ["<strong>① 标签分配<br>label assignment</strong>", "训练时，哪些位置该被当成正样本？<em>这个问题的答案决定了梯度往哪流</em>", "IoU 阈值 → ATSS → OTA/SimOTA → TaskAligned → dynamic soft label", "模块 <strong>02</strong>（全模块）；模块 01 的 YOLOX / v8 / v10"],
            ["<strong>② 无 NMS<br>NMS-free</strong>", "能不能让模型直接吐出不重复的框？<em>NMS 是延迟不确定性的唯一来源</em>", "一对多 + NMS → DETR 的一对一匹配 → YOLOv10 一致双分配", "模块 <strong>01</strong>（v10）、<strong>04</strong>（RT-DETR）；C54 全课"],
            ["<strong>③ 结构重参数化<br>re-parameterization</strong>", "能不能训练时用复杂结构、推理时折叠成简单结构？<em>免费的精度</em>", "Conv+BN 融合 → RepVGG 多分支 → YOLOv6/v7 的 RepBlock", "模块 <strong>01</strong>（含 numpy 数值等价证明）"],
        ]),
        DUAL(
            "为什么是这三条？因为它们分别对应了检测器的三个可独立优化的层面：<strong>① 训练信号（分配）、② 输出形式（去重）、③ 计算形式（重参数化）</strong>。<em>三者互不干扰，可以自由组合</em>——这正是 YOLOv6/v7/v8/v10 能一代一代叠加的原因。反过来，一个「新模型」如果在这三条之外只改了 backbone 的连接方式，它的收益通常在 ±0.5 AP 的噪声里。",
            "更有价值的是它们的<strong>共同结构</strong>：三条主线都是「<em>训练期与推理期解耦</em>」。分配只在训练期存在（推理时没有 GT，也就没有分配）；一对一 vs 一对多的区别也只在训练期（推理时只是要不要跑 NMS）；重参数化更是字面意义上的训练一个结构、推理另一个结构。<strong>「凡是只在训练期付出代价的改动，都是免费的午餐」——这是实时检测领域最重要的一条心法</strong>，也是它区别于「加模块涨点」式研究的根本处。",
        ),
        CALLOUT("intuition", "把这条心法反过来用，就得到一个很好用的判据：<strong>看到一个新的检测器改进，先问「它的代价是落在训练期还是推理期」</strong>。落在训练期（更复杂的分配、更多的辅助头、更强的增强、更长的训练）→ 值得试，因为推理零成本。落在推理期（多一个注意力模块、多一个尺度、TTA）→ 必须先算延迟账，因为你只有 2.45 ms。<em>这个判断你在面试现场就能做，不需要跑实验。</em>"),
    ])),
    ("curve", "怎么读延迟-精度曲线：同延迟比 AP，而不是同 AP 比延迟", "".join([
        P("实时检测的所有论文都会画一张图：横轴延迟、纵轴 AP、一堆点连成几条曲线。<strong>这张图有一种正确读法和两种常见的错误读法</strong>，而分辨它们是这个领域的入门门槛。"),
        P("先给出严格定义。模型 A <span class=\"term\">支配</span>（dominate）模型 B，当且仅当："),
        MATH("A \\succ B \\iff t_A \\le t_B \\ \\wedge\\ \\mathrm{AP}_A \\ge \\mathrm{AP}_B \\ \\wedge\\ (t_A < t_B \\ \\vee\\ \\mathrm{AP}_A > \\mathrm{AP}_B)"),
        P("不被任何模型支配的那些点，构成<span class=\"term\">帕累托前沿</span>（Pareto front）。<strong>被支配的模型可以直接从候选名单里划掉——存在一个又快又准的替代品，没有任何理由选它</strong>。notebook 第 4 节会让你在一组真实量级的数据上把这件事算出来：11 个模型里有 5 个是被支配的。"),
        TABLE(["读法", "长什么样", "为什么对 / 错"], [
            ["<strong>✅ 同延迟比 AP</strong>", "「我有 10 ms 预算，这个预算内 AP 最高的是谁？」", "<strong>延迟预算是外部硬约束、AP 是可争取量</strong>。这个问法直接对应真实的选型决策"],
            ["<strong>❌ 跨延迟点比 AP</strong>", "「我们比 YOLOv8-M 高 4.1 AP」（却慢了 65%）", "把两个不在同一预算档的模型放一起比。<em>论文最常见的话术，也是面试里最容易被追问穿的一句</em>"],
            ["<strong>❌ 同 AP 比延迟</strong>", "「达到 53 AP 我们只要 9.3 ms」", "在<em>研究</em>语境下可以，在<strong>工程</strong>语境下是倒过来的：没有人会先定一个 AP 目标再去找延迟。<em>AP 目标本身就是延迟预算的函数</em>"],
        ]),
        DUAL(
            "为什么「同 AP 比延迟」在工程上是错的？因为<strong>AP 不是一个需求，延迟才是</strong>。产品不会说「我要 53 AP」，产品会说「感知在 33 ms 帧周期里，TSR 只能占 2.45 ms」。<em>于是唯一有意义的问题是：在 2.45 ms 里我能拿到多少 AP</em>。把这个问句反过来，你就会做出「为了达到某个 AP 而超支延迟」的决定——而延迟超支在车端是硬故障，AP 低一点只是性能差一点。",
            "还有一个更隐蔽的错误：<strong>比较不在同一条测量协议下的点</strong>。不同论文的 FPS 可能包含或不包含 NMS、包含或不包含预处理、batch size 是 1 还是 32、精度是 FP32/FP16/INT8、卡是 V100/T4/A100/3090。<em>这些差异合起来能造成 3–5 倍的差距，远大于模型之间的真实差距</em>。所以任何跨论文的曲线对比都只能用来「粗分档」，不能用来做最终选型——<strong>选型必须自己在目标硬件上、用统一协议重测</strong>（模块 05 会给出完整的重测流程与容易踩的坑）。",
        ),
        CALLOUT("warn", "notebook 里那张模型表刻意用了各论文自报的量级数字，于是会得到一个「RT-DETR 系几乎占满前沿、RTMDet 全被支配」的结论。<strong>你应该对这个结论保持怀疑，而不是记住它</strong>——因为 RT-DETR 论文的对比表就是在自己的测量协议下做的（例如 YOLO 那一侧是否用了官方最优的 TensorRT 导出、NMS 用什么实现与阈值）。<em>这正是「论文的 FPS 不可信」的活标本</em>。本课教你的不是「哪个模型最好」，而是<strong>怎么自己把这张表算出来</strong>。"),
    ])),
    ("map", "课程地图与相邻课程的分界", "".join([
        ASCII("""起点：你知道什么是 anchor、IoU、NMS、mAP（C18），但没做过量产实时检测器。

  模块 01  YOLO 家族演进：每一代到底改了什么
     |      v1 网格回归的根本缺陷 -> anchor+多尺度+FPN -> CSP/PAN/Mosaic ->
     |      YOLOX 三件套 -> 结构重参数化 -> C2f/TaskAligned -> v10 一致双分配
     v      「每代改动的收益归因：架构红利还是训练技巧红利」  <- 面试高频
  模块 02  标签分配：检测器真正的胜负手
     |      静态 IoU 阈值的三个病 -> ATSS 自适应阈值 -> OTA/SimOTA 最优传输 ->
     |      TaskAligned -> RTMDet dynamic soft label
     v      「同一份数据、同一个网络，换分配能差 3-5 AP」
  模块 03  RTMDet 解剖：大核、共享头与软标签
     |      CSPNeXt / 5x5 depthwise 大核的有效感受野 / 跨层共享头 /
     |      软标签代价函数 / 全尺度缩放策略
     v      「一套框架覆盖 tiny 到 x 的工程哲学」
  模块 04  RT-DETR 解剖：DETR 如何跑赢 YOLO
     |      NMS 是延迟方差的来源 -> AIFI 只在 S5 做 self-attn + CCFF 跨尺度融合 ->
     |      IoU-aware query selection -> **decoder 层数可调 = 一份权重多档速度**
     v      「端到端无 NMS 在部署上到底买到了什么」
  模块 05  延迟-精度权衡与实时检测器选型
            端到端延迟的完整拆解 / 为什么论文 FPS 不可信 / 帕累托选型 /
            TensorRT fp16-int8 的真实量级 / p99 与显存 / **为 TSR 选型的完整推理**

终点：给定一个硬件平台、一个延迟预算和一个 TSR 任务，你能独立完成选型、
      给出论证、并说清每个选择的代价。"""),
        TABLE(["相邻课程", "它讲什么", "和本课的分界"], [
            ["<strong>C18 目标检测</strong>", "anchor、IoU、NMS、FPN、mAP 的<em>定义与原理</em>", "本课假设你已经会。<em>本课讲的是「在延迟约束下这些机制该怎么改」</em>"],
            ["<strong>C54 DETR 家族</strong>", "集合预测、匈牙利匹配、object query、收敛难题", "本课模块 04 只讲 <strong>RT-DETR 为了实时做了哪些取舍</strong>；<em>匹配算法本身与 DETR 的收敛机理去 C54</em>"],
            ["<strong>C57 小目标检测</strong>", "IoU 对位移的敏感性、NWD、切片推理、P2 层", "本课在讲分配与架构时会指出「对小目标意味着什么」，<em>但系统解法在 C57</em>"],
            ["<strong>C60 车端部署</strong>", "TensorRT、INT8 校准、预处理一致性、C++ 管线", "本课模块 05 只算<strong>延迟账</strong>；<em>怎么把 engine 真正建出来、怎么排查掉点，去 C60</em>"],
            ["<strong>C56 检测增强</strong>", "Mosaic / copy-paste / 增强流水线", "本课模块 01 会讲 Mosaic 是「训练期红利」的典型，<em>但增强工程本身在 C56</em>"],
        ]),
        CALLOUT("warn", "一个必须提前说清的边界：<strong>本课不讲「怎么训一个更准的检测器」这件事的全部</strong>。数据（C55/C56/C58）通常比模型更能决定 TSR 的最终指标——在一个 badcase 驱动的项目里，把 RTMDet-S 换成 RT-DETR-R18 可能涨 2 AP，而把夜间数据补齐可能涨 8 AP。<em>本课教的是「模型这一侧能榨出多少」，以及更重要的：怎么用可验证的方式说清它到底榨出了多少</em>。"),
    ])),
    ("env", "环境、方法论与这门课的用法", "".join([
        P("本课全程 <strong>纯 numpy + 标准库、CPU 可跑、不联网</strong>。不需要 PyTorch、mmdetection、TensorRT 或任何数据集下载。所有 notebook 在 CPU 上实跑验证，<code>assert</code> 零失败。"),
        CODE("""pip install -r requirements.txt      # numpy / matplotlib / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        TABLE(["真实世界里你需要", "本课怎么处理"], [
            ["GPU + TensorRT 实测延迟", "用<strong>参数化的延迟模型</strong>（含 NMS 的目标数依赖项）+ 各论文自报数字的量级表；真实测量协议写在模块 05 的胶囊里"],
            ["COCO / TT100K 数据集", "用<strong>按针孔相机模型合成</strong>的交通标志尺寸分布（<code>px = f·S/Z</code>），物理上可解释、可复现"],
            ["mmdetection / ultralytics", "把关键机制<strong>从零用 numpy 实现</strong>：Conv+BN 融合、RepVGG 合并、k-means anchor、ATSS/SimOTA、软标签代价矩阵"],
            ["PyTorch 训练循环", "只在需要「证明数值等价」的地方复现前向；<em>本课不训练模型，本课解剖模型</em>"],
        ]),
        P("三条贯穿全课的纪律："),
        UL([
            "<strong>凡是说「更好」，必须说清是在哪个延迟点上更好</strong>。孤立的 AP 数字在这门课里没有意义。每次比较都要能写成「在 X ms 预算下，从 A 换到 B，AP 从 p 变到 q」。",
            "<strong>凡是改动，必须归因到训练期还是推理期</strong>。这决定了它的代价结构，也决定了要不要试。第 3 节的心法要贯穿每一个模块。",
            "<strong>凡是数值等价的声明，必须用 assert 证明</strong>。「重参数化后精度不变」不是一句话，是 <code>np.allclose(y_multi_branch, y_fused)</code>——模块 01 的 notebook 会让你亲手写出这个 assert。",
        ]),
        CALLOUT("intuition", "这门课的用法建议：<strong>模块 01–02 顺着读（它们是后面所有内容的语言），03–04 可以按需求跳读，05 建议在选型前重读一遍</strong>。<em>如果你现在就要为一个具体项目选模型，可以先读 00 + 05，把账算出来，再回头读 01–04 理解每个候选到底做了什么</em>。全课的 notebook 彼此独立，不依赖前一个的变量。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("实时检测在 2023 年之后进入了一个有意思的阶段：<strong>纯 CNN 的 YOLO 系与端到端的 DETR 系在同一条帕累托前沿上正面相遇了</strong>，而且各自都在吸收对方的东西。以下是目前仍然开放的问题。"),
        UL([
            "<strong>无 NMS 的收益到底有多大，仍然没有公认答案。</strong> YOLOv10 与 RT-DETR 都主张「去掉 NMS」，但去掉 NMS 换来的是<em>延迟的确定性</em>（方差变小）而不必然是<em>延迟的均值</em>更低。在候选框不多的场景（高速上的 TSR），NMS 本来就只占 12%。<em>「无 NMS 值不值」是一个和场景强相关的问题，不存在通用答案。</em>",
            "<strong>一对一匹配的训练效率问题没有被真正解决。</strong> 一对一提供的监督信号密度远低于一对多，这是 DETR 系收敛慢的根因之一。目前的主流做法（YOLOv10 的双分配、Co-DETR/Group-DETR 的辅助一对多分支）本质都是「训练时借一对多的密集监督、推理时只用一对一」——<em>这更像是绕过问题而不是解决问题</em>。",
            "<strong>结构重参数化与量化的冲突。</strong> 多分支合并后的等效卷积，其权重分布往往比原生单分支训练出来的更「长尾」，导致 INT8 量化掉点更严重。<em>「重参数化友好的量化」或「量化感知的重参数化」目前还没有干净的解法</em>——这是 C60 模块 03 会重新遇到的问题。",
            "<strong>标签分配的理论仍然缺失。</strong> 从 IoU 阈值到 ATSS 到 SimOTA 到 TaskAligned，每一步都被实验证明有效，但<em>「什么是最优的分配」至今没有一个可优化的形式化目标</em>。OTA 的最优传输视角是最接近的一次尝试，但它的代价函数仍然是手工设计的。",
            "<strong>评测协议的碎片化。</strong> 「同一模型在不同论文里 FPS 差 3 倍」是这个领域的常态。<em>缺少一个像 MLPerf 那样被普遍接受的实时检测端到端 benchmark</em>（含预处理、含 NMS、报 p99、指定硬件与精度），使得跨论文比较基本失效——这是本课模块 05 花整整一个模块讲测量的原因。",
            "<strong>面向车端多任务共享算力的联合优化。</strong> 现实中 TSR 不是独占 SoC，而是和 BEV、车道线、红绿灯抢时间片。<em>「多个感知任务共享 backbone / 联合排期 / 动态分配算力」在工业界已经是标配，在学术界几乎没有对应的 benchmark</em>——这也是学术实时检测与量产实时检测最大的一条鸿沟。",
        ]),
        CALLOUT("paper", "必读（按本课顺序）：<em>You Only Look Once</em>(Redmon 2016) 与 <em>YOLO9000</em>(2017) —— 读它们是为了理解「网格回归」的原始动机与 anchor 被引入的确切原因；<em>YOLOX: Exceeding YOLO Series in 2021</em> —— 解耦头 / anchor-free / SimOTA 三件套的消融表是整个领域最有信息量的一张表；<em>RepVGG: Making VGG-style ConvNets Great Again</em>(2021) —— 结构重参数化的原始论文，公式极简，务必自己推一遍；<em>RTMDet: An Empirical Study of Designing Real-Time Object Detectors</em>(2022) —— 大核与共享头，工程细节写得最实在；<em>DETRs Beat YOLOs on Real-time Object Detection</em>(RT-DETR, 2023) —— 注意读它的 NMS 敏感性分析那一节；<em>YOLOv10: Real-Time End-to-End Object Detection</em>(2024) —— 一致双分配。相邻课程：C18（检测基础）、C54（DETR 家族）、C57（小目标）、C60（车端部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与实时检测的三本账（延迟预算 / NMS 波动 / 帕累托前沿）

本课全程 **纯 numpy + 标准库、CPU、不联网**。这个 notebook 不训练任何模型，
它建立的是**三本你在后面五个模块里会反复用到的账**。

**本 notebook 你会亲手实现：**
1. **帧延迟预算分解器** —— 从 33.3 ms 帧周期一路算到 TSR 分到的 2.45 ms，再拆到六个阶段
2. **NMS 的目标数依赖模型** —— 量化「唯一随场景波动的那一项」，看它怎么在雨夜吃掉整个预算
3. **帕累托前沿与「被支配」判定** —— 11 个模型里划掉 5 个，并给出「谁支配了它」
4. **延迟-精度曲线的正确读法** —— 同延迟比 AP，以及为什么反过来是错的
5. **TSR 的物理约束** —— 针孔模型算出 60 m 外的限速牌只有 16.6 px，以及 IoU 对位移的敏感性

> 心智模型：**延迟预算与显存是外部硬约束，精度是唯一的优化目标。
> 实时检测的整部历史 = 在给定的毫秒数里把 AP 往上抬。**"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math, json, itertools, time
print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
import numpy as np
print('numpy', np.__version__)
for name in ['torch', 'torchvision', 'onnxruntime', 'cv2']:
    try:
        mod = __import__(name)
        print('  %-14s %-10s (有更好，但本课全程不需要)' % (name, getattr(mod, '__version__', '?')))
    except ImportError:
        print('  %-14s %s' % (name, '未安装 -> 走纯 numpy 复现路径'))

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
rng = np.random.default_rng(0)
print('\\n✅ 环境就绪：本课 CPU 可跑、不联网、不下载数据集。')"""),
    md("""## 2 · 第一本账：33.3 ms 到底怎么花的

「实时」不是形容词。把它换成数字，很多设计选择立刻有了解释。

**注意这里的两级瓜分**：先被固定开销切一刀，剩下的时间窗再被十几个感知任务分。"""),
    code("""FPS = 30
FRAME_MS = 1000.0 / FPS

# 第一级：固定开销（TSR 代码改不动的部分）
FIXED = [
    ('传感器曝光 + ISP + MIPI 传输', 8.0, '相机侧固定开销'),
    ('融合/跟踪/地图匹配/规控/执行下发', 7.0, 'TSR 的下游，不能挤压'),
    ('调度抖动与安全裕度', 2.0, '车端看 p99，不是 p50'),
]
fixed_ms = sum(x[1] for x in FIXED)
perception_ms = FRAME_MS - fixed_ms

# 第二级：全部感知任务瓜分剩下的时间窗
TASK_SHARE = [
    ('BEV 障碍物检测', 0.45), ('车道线 / 可行驶区域', 0.20),
    ('交通标志 TSR', 0.15), ('红绿灯', 0.10), ('其他（静态障碍/占位）', 0.10),
]
assert abs(sum(s for _, s in TASK_SHARE) - 1.0) < 1e-9

print('帧周期 @ %d FPS = %.2f ms' % (FPS, FRAME_MS))
for name, ms, why in FIXED:
    print('   - %-36s %5.2f ms   %s' % (name, ms, why))
print('   = 留给「全部感知任务」的时间窗: %.2f ms\\n' % perception_ms)

tsr_budget = None
for name, share in TASK_SHARE:
    ms = perception_ms * share
    mark = '   <-- 本课的主角' if name.startswith('交通标志') else ''
    print('     %-24s %3.0f%%   %5.2f ms%s' % (name, share * 100, ms, mark))
    if name.startswith('交通标志'):
        tsr_budget = ms

assert abs(FRAME_MS - 33.3333) < 1e-3
assert abs(perception_ms - 16.3333) < 1e-3
assert 2.4 < tsr_budget < 2.5, tsr_budget
print('\\n>>> TSR 的端到端延迟预算 = %.2f ms' % tsr_budget)
print('    这个数字在后面每一个模块里都会被拿出来对照。')"""),
    code("""# 把 2.45 ms 拆到阶段级 —— 这一层才是你能动的
STAGES = [
    ('预处理 resize+letterbox+归一化', 0.35, '常在 CPU；训练-部署不一致的头号来源(C60)'),
    ('H2D 拷贝',                       0.15, '可与推理重叠'),
    ('网络前向 backbone+neck+head',    1.45, '唯一能靠换模型优化的一项'),
    ('NMS',                            0.30, '随目标数波动 —— 唯一不确定的一项'),
    ('解码/坐标还原/阈值',             0.12, '写错就是「框整体偏移」(C60)'),
    ('D2H 拷贝',                       0.05, ''),
]
used = sum(x[1] for x in STAGES)

print('%-36s %8s %8s   %s' % ('阶段', '毫秒', '占比', '备注'))
for name, ms, note in STAGES:
    print('%-36s %8.2f %7.1f%%   %s' % (name, ms, 100 * ms / used, note))
print('%-36s %8.2f            预算 %.2f ms，余量 %.2f ms'
      % ('合计', used, tsr_budget, tsr_budget - used))

infer_share = 1.45 / used
assert used <= tsr_budget, '端到端超预算'
assert 0.55 < infer_share < 0.65, infer_share
print('\\n⚠️  网络前向只占 %.0f%%。「换个快一倍的 backbone」对端到端最多带来 %.0f%% 的收益。'
      % (100 * infer_share, 100 * infer_share / 2))
print('    另外 %.0f%% 在预处理/拷贝/NMS/后处理里 —— 而它们几乎不出现在论文的 FPS 表里。'
      % (100 * (1 - infer_share)))"""),
    md("""## 3 · 第二本账：NMS 是唯一「不确定」的一项

其余五项的耗时只和输入分辨率有关（给定模型后是常数）。
**只有 NMS 的耗时随场景变化**——因为它取决于过了分数阈值的候选框数量。

这就是 RT-DETR 存在的直接理由（模块 04 会展开）。"""),
    code("""def nms_cost_ms(n, base=0.05, per_pair=2.2e-6):
    '''朴素 NMS 的代价模型：固定开销 + 成对 IoU 计算。
       真实实现有向量化与早停，常数不同，但 O(n^2) 的形状是一样的。'''
    return base + per_pair * n * (n - 1) / 2

print('%12s %14s %16s' % ('候选框数 n', 'NMS 耗时(ms)', '占 TSR 预算'))
for n in [50, 100, 300, 1000, 3000, 10000]:
    c = nms_cost_ms(n)
    print('%12d %14.3f %15.0f%%' % (n, c, 100 * c / tsr_budget))

assert nms_cost_ms(100) < 0.3
assert nms_cost_ms(3000) > tsr_budget, 'n=3000 时 NMS 单项就该爆掉整个预算'

# 工程上的止血法：NMS 前先做 top-k 预筛
def nms_cost_with_topk(n, topk=300):
    return nms_cost_ms(min(n, topk))

print('\\ntop-k 预筛（topk=300）的效果：')
for n in [300, 1000, 3000, 10000]:
    print('   n=%-6d 无预筛 %9.3f ms   ->  预筛后 %6.3f ms'
          % (n, nms_cost_ms(n), nms_cost_with_topk(n)))
assert nms_cost_with_topk(10000) == nms_cost_ms(300)
print('✅ top-k 把**最坏情况**封住了，但没有消除方差 —— 见下一格。')"""),
    code("""# 同一个模型，不同场景下的端到端延迟
SCENES = [('空旷高速', 40), ('城市主干道', 120), ('施工区门架(一排标志)', 260),
          ('雨夜 + 广告牌误检爆炸', 900)]
base_ms = used - 0.30                       # 扣掉表里那个「典型 NMS」

print('%-26s %10s %14s %10s' % ('场景', '候选框数', '端到端(ms)', '是否超预算'))
lat = {}
for name, n in SCENES:
    t = base_ms + nms_cost_ms(n)
    lat[name] = t
    print('%-26s %10d %14.3f %10s' % (name, n, t, '❌ 超' if t > tsr_budget else '✅'))

p50, p99 = lat['城市主干道'], lat['雨夜 + 广告牌误检爆炸']
print('\\np50 ≈ %.2f ms   p99 ≈ %.2f ms   ->  尾延迟是中位数的 %.2f 倍'
      % (p50, p99, p99 / p50))
assert lat['空旷高速'] < tsr_budget < lat['雨夜 + 广告牌误检爆炸']
assert p99 / p50 > 1.3
print('\\n⚠️  **车端安全关心的是 p99，不是均值**。一个「平均 2.2 ms」的检测器')
print('    如果 p99 是 3.1 ms，它就是超预算的 —— 而论文只会报平均。')
print('✅ 这就是「NMS 是延迟不确定性的唯一来源」这句话的定量含义（模块 04 会重做这个实验）。')"""),
    md("""## 4 · 第三本账：帕累托前沿与「被支配」判定

模型 A **支配** 模型 B，当且仅当 A 不比 B 慢、不比 B 差，且至少有一项严格更好。
被支配的模型可以直接从候选名单划掉——**存在一个又快又准的替代品**。

> ⚠️ 下表的数字取自各论文自报的量级（不同论文测法不同，模块 05 会拆穿这件事）。
> 这里只用来演示**读图的方法**，不要当成选型结论。"""),
    code("""# (名字, 延迟 ms, COCO AP)  —— 量级示意
MODELS = [
    ('YOLOv5-S',      4.5, 37.4), ('YOLOv8-S',      5.1, 44.9),
    ('RTMDet-S',      5.4, 44.5), ('RT-DETR-R18',   6.8, 46.5),
    ('YOLOv5-M',      7.0, 45.4), ('YOLOv8-M',      8.2, 50.2),
    ('RT-DETR-R50',   9.3, 53.1), ('YOLOv5-L',     10.1, 49.0),
    ('RTMDet-L',     10.2, 51.3), ('YOLOv8-L',     12.8, 52.9),
    ('RT-DETR-R101', 13.5, 54.3),
]

def dominates(a, b):
    '''a 支配 b: 不更慢、不更差，且至少一项严格更好。'''
    return a[1] <= b[1] and a[2] >= b[2] and (a[1] < b[1] or a[2] > b[2])

def pareto_front(models):
    out = []
    for i, m in enumerate(models):
        if not any(dominates(o, m) for j, o in enumerate(models) if j != i):
            out.append(m)
    return sorted(out, key=lambda x: x[1])

def dominators(name, models):
    m = [x for x in models if x[0] == name][0]
    return [o[0] for o in models if o[0] != name and dominates(o, m)]

front = pareto_front(MODELS)
names = [m[0] for m in front]
print('帕累托前沿（%d / %d 个模型）：' % (len(front), len(MODELS)))
for nm, t, ap in front:
    print('   %-14s %5.1f ms   AP %.1f' % (nm, t, ap))

print('\\n被支配的模型（可以直接划掉）：')
for nm, t, ap in sorted(MODELS, key=lambda x: x[1]):
    d = dominators(nm, MODELS)
    if d:
        print('   %-14s %5.1f ms AP %.1f   被 %s 支配（更快且更准）' % (nm, t, ap, ' / '.join(d)))

assert len(front) == 6, front
assert 'RTMDet-S' not in names and 'YOLOv5-L' not in names
assert set(dominators('YOLOv5-L', MODELS)) == {'YOLOv8-M', 'RT-DETR-R50'}
print('\\n✅ 11 个模型里 5 个被支配。**选型的第一步永远是先把被支配的划掉。**')"""),
    md("""## 5 · 曲线的正确读法：同延迟比 AP"""),
    code("""def best_under_budget(models, budget_ms):
    ok = [m for m in models if m[1] <= budget_ms]
    return max(ok, key=lambda m: m[2]) if ok else None

print('%12s   %s' % ('预算(ms)', '预算内 AP 最高的模型'))
for b in [tsr_budget, 5.0, 6.0, 9.0, 10.0, 13.0, 14.0]:
    r = best_under_budget(MODELS, b)
    txt = ('%-14s AP %.1f' % (r[0], r[2])) if r else '❌ 没有任何模型放得进来'
    print('%12.2f   %s' % (b, txt))

assert best_under_budget(MODELS, 9.0)[0] == 'YOLOv8-M'
assert best_under_budget(MODELS, 10.0)[0] == 'RT-DETR-R50'
assert best_under_budget(MODELS, tsr_budget) is None

gain = best_under_budget(MODELS, 10.0)[2] - best_under_budget(MODELS, 9.0)[2]
assert abs(gain - 2.9) < 1e-6
print('\\n✅ 正确读法：「预算从 9.0 放宽到 10.0 ms，可拿到的 AP 从 50.2 涨到 53.1（+%.1f）」' % gain)
print('   —— 这句话可以直接拿去和产品谈判：多给我 1 ms，我给你 2.9 AP。')

d = dict((m[0], m) for m in MODELS)
print('\\n❌ 错误读法：「RT-DETR-R101 比 YOLOv8-M 高 %.1f AP」'
      % (d['RT-DETR-R101'][2] - d['YOLOv8-M'][2]))
print('   —— 它同时慢了 %.0f%%（%.1f -> %.1f ms）。跨预算档比 AP 没有选型价值，'
      % (100 * (d['RT-DETR-R101'][1] / d['YOLOv8-M'][1] - 1), d['YOLOv8-M'][1], d['RT-DETR-R101'][1]))
print('      而这是论文里最常见的一句话。')
print('\\n❗ 而 TSR 的 %.2f ms 预算里**一个模型都放不进来** —— 这不是账算错了。' % tsr_budget)
print('   真实工程的三条出路：① tiny 档 + INT8 + 更小输入（代价：小目标掉点，C57）')
print('                     ② TSR 降频到 10-15 Hz（代价：首检距离变远，C55）')
print('                     ③ 只在 ROI/消失点附近跑（代价：漏掉侧向标志）')"""),
    md("""## 6 · TSR 的物理约束：60 米外的限速牌只有 16.6 像素

这门课反复回到交通标志检测，因为它同时踩中了实时检测最难的两点：
**极小的目标** + **极紧的延迟预算**。先把「极小」变成数字。

针孔相机模型：焦距（像素）$f = \\frac{W/2}{\\tan(\\mathrm{HFOV}/2)}$，
物体成像边长 $px = f \\cdot S / Z$（$S$ 物理尺寸，$Z$ 距离）。"""),
    code("""def focal_px(width_px, hfov_deg):
    '''横向分辨率 + 水平 FOV -> 焦距（像素）'''
    return (width_px / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

def sign_px(size_m, dist_m, f_px):
    return f_px * size_m / dist_m

CAMS = [('前视主摄 1920x1080 / 60°', 1920, 60.0),
        ('前视长焦 1920x1080 / 30°', 1920, 30.0),
        ('高分主摄 3840x2160 / 60°', 3840, 60.0)]

print('直径 0.6 m 的圆形限速牌，成像边长（像素）：')
print('%-28s %9s %9s %9s %9s' % ('相机', '30 m', '60 m', '100 m', '150 m'))
for name, wpx, fov in CAMS:
    f = focal_px(wpx, fov)
    row = [sign_px(0.6, z, f) for z in (30, 60, 100, 150)]
    print('%-28s %9.1f %9.1f %9.1f %9.1f' % (name, row[0], row[1], row[2], row[3]))

f_main = focal_px(1920, 60.0)
px60, px100 = sign_px(0.6, 60, f_main), sign_px(0.6, 100, f_main)
assert 1660 < f_main < 1665, f_main
assert 16.0 < px60 < 17.0, px60
assert px100 < 10.5, px100

print('\\n>>> 主摄下 60 m 外只有 %.1f px，100 m 外只有 %.1f px。' % (px60, px100))
for s in (8, 16, 32):
    print('    在 stride %-2d 的特征图上，60 m 的标志只占 %.2f x %.2f 个格子。'
          % (s, px60 / s, px60 / s))
print('⚠️  stride 32 上它连一个格子都占不满 —— 下采样已经把它抹掉了（C57 模块 01）。')"""),
    code("""def iou_shift(size, d):
    '''两个同尺寸正方形框，在 x 与 y 方向**各**偏移 d 像素时的 IoU。'''
    ov = max(0.0, size - d)
    inter = ov * ov
    union = 2.0 * size * size - inter
    return inter / union

print('同一个 IoU 阈值对不同尺度是**极不公平**的：')
print('%10s %10s %10s %10s' % ('框边长', 'd=1px', 'd=2px', 'd=3px'))
for s in (8, 16, 32, 64):
    print('%10d %10.3f %10.3f %10.3f' % (s, iou_shift(s, 1), iou_shift(s, 2), iou_shift(s, 3)))

assert abs(iou_shift(8, 2) - 36.0 / 92.0) < 1e-9
assert iou_shift(64, 2) > 0.88
assert iou_shift(8, 2) < 0.5 < iou_shift(64, 2)
print('\\n>>> 8x8 的框只要各偏 2 px，IoU 就从 1.00 掉到 %.2f；' % iou_shift(8, 2))
print('    而 64x64 的框同样偏 2 px，IoU 还有 %.2f。' % iou_shift(64, 2))
print('⚠️  于是用 IoU>0.5 做正样本分配时，**小目标几乎匹配不到任何 anchor** ——')
print('    这是模块 02（标签分配）与 C57（小目标）共同的出发点。')"""),
    md("""## ✏️ 练习 1：帧预算分解器

实现 `frame_budget(fps, fixed_ms, task_share)`，返回
`(帧周期 ms, 感知总时间窗 ms, 该任务预算 ms)`。

规则：帧周期 = 1000/fps；感知窗口 = 帧周期 − fixed_ms，**若为负则取 0**
（固定开销已经吃光帧周期，感知一点时间都没有）；任务预算 = 感知窗口 × task_share。"""),
    code("""def frame_budget(fps, fixed_ms, task_share):
    # TODO: 返回 (frame_ms, perception_ms, task_ms)，注意 perception_ms 不能为负
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
fm, pm, tb = frame_budget(30, 17.0, 0.15)
assert abs(fm - 1000 / 30) < 1e-9, fm
assert abs(pm - (1000 / 30 - 17.0)) < 1e-9, pm
assert abs(tb - pm * 0.15) < 1e-9, tb
assert abs(tb - tsr_budget) < 1e-9, '应当复现正文里的 2.45 ms'

fm2, pm2, tb2 = frame_budget(10, 17.0, 0.15)
assert abs(fm2 - 100.0) < 1e-9 and pm2 > pm and tb2 > tb, '降帧率 -> 单帧预算变宽'

fm3, pm3, tb3 = frame_budget(60, 20.0, 0.15)
assert pm3 == 0.0 and tb3 == 0.0, '60 FPS 帧周期只有 16.7 ms，20 ms 固定开销已吃光'

print('%6s %10s %14s %14s' % ('FPS', '固定开销', '感知窗口(ms)', 'TSR 预算(ms)'))
for fps, fx in [(10, 17.0), (15, 17.0), (30, 17.0), (30, 25.0), (60, 20.0)]:
    a, b, c = frame_budget(fps, fx, 0.15)
    print('%6d %10.1f %14.2f %14.2f' % (fps, fx, b, c))
print('\\n✅ 练习 1 通过。注意第 4 行：固定开销从 17 涨到 25 ms，TSR 预算直接腰斩还不止 ——')
print('   **感知预算对固定开销的敏感度是非线性的**，这是排期谈判里最有用的一条杠杆。')"""),
    md("""## ✏️ 练习 2：帕累托前沿与「谁支配了它」

实现 `pareto_and_dominators(models)`，返回
`(前沿模型名列表（按延迟升序）, {被支配模型名: [支配它的模型名, ...]})`。

注意：**完全相同的两个点互不支配**（没有任何一项严格更好），两个都在前沿上。
实现时请用**下标**而不是 `is not` 来排除自身，否则重复元组会出错。"""),
    code("""def pareto_and_dominators(models):
    # TODO: 返回 (front_names, dom_map)
    #   front_names: 不被任何其他模型支配的模型名，按延迟升序
    #   dom_map:     只包含被支配的模型；值是支配它的模型名列表
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
front_names, dom = pareto_and_dominators(MODELS)
assert front_names == ['YOLOv5-S', 'YOLOv8-S', 'RT-DETR-R18', 'YOLOv8-M',
                       'RT-DETR-R50', 'RT-DETR-R101'], front_names
assert set(dom['YOLOv5-L']) == {'YOLOv8-M', 'RT-DETR-R50'}, dom['YOLOv5-L']
assert dom['RTMDet-S'] == ['YOLOv8-S'], dom['RTMDet-S']
assert all(n not in dom for n in front_names), '前沿上的模型不该出现在被支配表里'
assert len(dom) == len(MODELS) - len(front_names)

tie = [('A', 1.0, 10.0), ('B', 1.0, 10.0)]
assert pareto_and_dominators(tie)[0] == ['A', 'B'], '完全相同的两点互不支配'
assert pareto_and_dominators(tie)[1] == {}

print('前沿:', ' -> '.join(front_names))
print('被支配:', ', '.join('%s(被%d个)' % (k, len(v)) for k, v in dom.items()))
print('\\n✅ 练习 2 通过：这就是模块 05 选型脚本的内核。')"""),
    md("""## ✏️ 练习 3：从「要在多远检出」反推相机配置

实现 `max_detect_distance(sign_m, min_px, width_px, hfov_deg)`：
给定检测器能稳定工作的**最小像素边长** `min_px`，返回这块标志能被检出的最远距离（米）。

这是 TSR 系统设计里最先要算的一笔账：**「我要在 80 m 外看到限速牌」直接决定了
相机分辨率、FOV，以及检测器的输入分辨率与最细 stride**（C57 模块 05 会展开）。"""),
    code("""def max_detect_distance(sign_m, min_px, width_px, hfov_deg):
    # TODO: 用 focal_px 求焦距，再由 px = f*S/Z 反解 Z
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
d = max_detect_distance(0.6, 16, 1920, 60.0)
assert 62.0 < d < 63.0, d

d2 = max_detect_distance(0.6, 16, 3840, 60.0)
assert abs(d2 - 2 * d) < 1e-6, '横向分辨率翻倍 -> 焦距翻倍 -> 检出距离翻倍'

d3 = max_detect_distance(0.6, 16, 1920, 30.0)
assert d3 > 2 * d, 'FOV 减半带来的焦距增益超过 2 倍（tan 是非线性的）'

assert max_detect_distance(1.2, 16, 1920, 60.0) > d, '大牌子看得更远'
assert max_detect_distance(0.6, 8, 1920, 60.0) > d, '模型能吃更小的目标 -> 看得更远'

print('%-34s %14s' % ('配置（min_px=16, 0.6m 限速牌）', '最远检出距离'))
for label, args in [('1920 / 60° 主摄',      (0.6, 16, 1920, 60.0)),
                    ('3840 / 60° 高分主摄',  (0.6, 16, 3840, 60.0)),
                    ('1920 / 30° 长焦',      (0.6, 16, 1920, 30.0)),
                    ('1920 / 60°, min_px=8', (0.6,  8, 1920, 60.0))]:
    print('%-34s %11.1f m' % (label, max_detect_distance(*args)))
print('\\n✅ 练习 3 通过。三条可换的杠杆：**加分辨率 / 减 FOV / 让模型吃更小的目标**。')
print('   前两条要动硬件（几年前就定死了），只有第三条是算法能做的 —— 这就是 C57 的全部意义。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def frame_budget(fps, fixed_ms, task_share):
    frame_ms = 1000.0 / fps
    perception_ms = max(0.0, frame_ms - fixed_ms)
    return frame_ms, perception_ms, perception_ms * task_share"""),
    code("""# 练习 2 参考答案
def pareto_and_dominators(models):
    front, dom = [], {}
    for i, m in enumerate(models):
        ds = [o[0] for j, o in enumerate(models) if j != i and dominates(o, m)]
        if ds:
            dom[m[0]] = ds
        else:
            front.append(m)
    return [m[0] for m in sorted(front, key=lambda x: x[1])], dom"""),
    code("""# 练习 3 参考答案
def max_detect_distance(sign_m, min_px, width_px, hfov_deg):
    f = focal_px(width_px, hfov_deg)
    return f * sign_m / min_px"""),
    md("""---
## 🧪 真实工程胶囊：一份可直接抄走的延迟测量协议

论文的 FPS 不可信（模块 05 会拆穿这件事）。下面这段是**你自己重测时必须遵守的协议**，
可以原样复制到有 GPU 的机器上。"""),
    code("""RECIPE = r'''
# ============ 实时检测器延迟测量协议（照抄即可） ============
# 原则：报 p99 不报均值；含预处理与 NMS；固定硬件/精度/batch；同一协议测所有候选。

import time, numpy as np

WARMUP, RUNS = 50, 500          # ① warmup 必须有：首次 kernel 选择/显存分配会污染前几次
BATCH = 1                       # ② 车端就是 batch=1。用 batch=32 测出来的 FPS 与你无关

lat = []
for i in range(WARMUP + RUNS):
    torch.cuda.synchronize()    # ③ **必须同步**，否则你测的是 kernel launch 的时间
    t0 = time.perf_counter()

    blob = preprocess(frame)        # ④ 含预处理！论文常常不含
    d_in.copy_(blob)                #    含 H2D 拷贝
    out = engine.infer(d_in)        #    网络前向
    boxes = decode(out)             #    解码
    boxes = nms(boxes, iou=0.65)    # ⑤ **含 NMS**！这是延迟方差的唯一来源
    boxes = to_image_coords(boxes)  #    letterbox 逆变换

    torch.cuda.synchronize()
    if i >= WARMUP:
        lat.append((time.perf_counter() - t0) * 1000)

lat = np.array(lat)
print("p50=%.2f  p90=%.2f  p99=%.2f  max=%.2f ms"
      % (np.percentile(lat,50), np.percentile(lat,90),
         np.percentile(lat,99), lat.max()))

# ⑥ **必须在多种场景下各测一遍** —— NMS 的耗时随候选框数变化
#    空旷高速 / 城市主干道 / 施工区门架 / 雨夜误检爆炸，四组各 500 次
# ⑦ 报告时必须同时给出：GPU 型号、驱动、TRT 版本、精度(fp16/int8)、
#    输入分辨率、score 阈值、iou 阈值、topk。缺一项这个数字就不可复现。

# ============ 选型判据 ============
# 通过条件： p99 <= 预算  且  在四种场景下都成立
#           （p50 达标而 p99 不达标 = 不达标）
'''
print(RECIPE)
for key in ['WARMUP', 'synchronize', 'preprocess', 'nms(', 'p99', 'BATCH = 1', 'topk']:
    assert key in RECIPE, key
print('✅ 协议覆盖：warmup / 同步 / 含预处理 / 含 NMS / batch=1 / p99 / 多场景 / 环境三元组')"""),
    md("""### 小结

- **「实时」= 两个硬约束（延迟预算、显存）+ 一个优化目标（精度）**。
  延迟预算是外部给定的，不能靠「模型更准」去谈判。
- **33.3 ms 的帧周期里，TSR 只分到约 2.45 ms**；这 2.45 ms 里网络前向只占 60%。
  **「换个更快的 backbone」对端到端最多带来 30% 的收益。**
- **NMS 是唯一随场景波动的一项**（O(n²)）。top-k 预筛能封住最坏情况，但消不掉方差。
  **车端安全关心的是 p99，而论文只报均值。**
- **选型第一步是划掉被支配的模型**（本例 11 个里划掉 5 个），第二步是
  **同延迟比 AP**——因为预算是硬约束、AP 是可争取量。跨预算档比 AP 没有选型价值。
- **TSR = 极小目标 + 极紧预算**：60 m 外的限速牌只有 16.6 px，在 stride 32 上占不满一个格子；
  8×8 的框各偏 2 px，IoU 就掉到 0.39 —— 这两个数字是模块 02 与 C57 的共同出发点。

下一站：**模块 01 · YOLO 家族演进** —— 把「每一代到底改了什么」拆成可归因的三条主线。"""),
]
