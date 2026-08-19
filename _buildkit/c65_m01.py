# -*- coding: utf-8 -*-
"""C65 模块 01 · 估算题与数量级心算（结构化问题求解与面试沟通）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "会算乘除法、知道对数的定义即可；不需要任何 ML 背景——这是一套通用的数量级心算方法"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_estimation.ipynb'
                       '（Fermi 估算器与误差传播 / 锚点数字表 / 标注-训练-显存-QPS 四个完整案例 / 双路径交叉校验器）'),
    ("核心参考", "Weinstein & Adam《Guesstimation》 · Kaplan et al.《Scaling Laws for Neural Language Models》"
                 "（2020）· Hoffmann et al.《Training Compute-Optimal LLMs》（Chinchilla, 2022）· 本课程 C63 模块 04"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("fermi-method", "Fermi 估算法：分解 → 锚点 → 相乘 → 校验", "".join([
        P("估算题的经典形式是「一个城市里有多少个钢琴调音师」——这类题目故意不给你任何数据，"
          "考的不是你知不知道答案（没人知道），是你<strong>能不能在没有数据的情况下，构造出一个数量级正确的答案，"
          "并且让面试官相信这个构造过程</strong>。这套方法以 Enrico Fermi 命名，因为他擅长在纸巾背面推算出"
          "核爆当量这类量级正确的答案。面试里的版本更实用：把它套在 ML 系统的容量、成本、时长上。"),
        ASCII("""分解 decompose -> 锚点 anchor -> 相乘 multiply -> 校验 verify
     ^                                                    |
     |________________ 换一条独立路径重新走一遍 __________|

两条路径的点估计相差在 3-5 倍以内 -> 可信；相差一个数量级以上 -> 回头找错在哪个因子"""),
        TABLE(["步骤", "要做的事", "面试里怎么说", "常见错误"], [
            ["① 分解 decompose", "把目标量写成几个可以独立估计的因子的<strong>乘积</strong>",
             "「我把这个量拆成 A × B × C 三个因子」", "拆成加法而不是乘法；拆出的因子彼此不独立"],
            ["② 锚点 anchor", "给每个因子一个你能背出来、或能现场推出来的量级数字",
             "「A 我用一个锚点：大概是这个量级」", "锚点凭感觉瞎编，不说明它从哪来"],
            ["③ 相乘 multiply", "对齐单位后把几个因子乘起来，得到一个点估计",
             "「乘起来大概是这个量，量级是 10 的几次方」", "单位不对齐（秒和小时混用）导致差 3600 倍"],
            ["④ 校验 verify", "换一条完全独立的路径重新估一遍，两个数量级对上才算数",
             "「我换个角度再算一遍验证」", "<strong>跳过这一步</strong>——没有校验的估算等于没有校验的代码"],
        ]),
        P("这四步其实就是<strong>模块 00 的四步框架</strong>在分解这一步上的专项深化：估算题里的分解必须是"
          "<em>乘法分解</em>而不是普通的子问题拆分，锚点是假设与验证里假设的具体形式，"
          "而校验就是这门课反复强调的用可验证的方式确认假设——只是换了个数字游戏的外壳。见 C65-00。"),
        DUAL(
            "说穿了就是：把一个吓人的大数，拆成几个你能拍脑袋估出来的小数，再乘起来。"
            "比如「TSR 车队一天能采集多少张带标志的图像」，直接想会觉得无从下手，"
            "但拆成「车辆数 × 每车每天行驶里程 × 每公里遇到几个标志」，每个因子都好估得多。",
            "更严谨地说，这是把一个高维未知量表示为若干个可独立估计的因子的乘积："
            "$Q = f_1 \\times f_2 \\times \\cdots \\times f_n$。"
            "只要每个因子的估计<em>量级</em>正确（哪怕数值有 2-3 倍误差），乘积的量级误差也不会剧烈放大——"
            "这正是下一节要严格讲清楚的误差传播机制。",
        ),
    ])),

    # ============================================================== 2
    ("error-propagation", "误差如何传播：为什么要在对数域相加", "".join([
        P("很多人对 Fermi 估算的直觉误解走向两个极端：一种觉得五个粗略猜测乘起来误差肯定爆炸到没法用"
          "（悲观），另一种觉得每个因子误差都不大乘起来也不会差太多（乐观，但不说明道理）。"
          "两者都不对，正确答案在中间，而且是可以算出来的。"),
        P("把每个因子的估计误差表示成<strong>以 2 为底的对数误差</strong>（记作 $\\sigma_i$ 比特）："
          "$\\sigma_i = 1$ 表示这个因子的真实值大概率落在你估计值的 $0.5\\times$–$2\\times$ 之间。"
          "如果 $n$ 个因子的误差<em>相互独立</em>，那么总的对数误差按方差可加性（均方根，RSS）合成，"
          "而不是简单相加："),
        MATH("\\sigma_{\\text{total}} = \\sqrt{\\sigma_1^2 + \\sigma_2^2 + \\cdots + \\sigma_n^2}"
             "\\qquad\\Longrightarrow\\qquad \\text{总误差倍数} \\approx 2^{\\sigma_{\\text{total}}}"),
        P("举一个五因子的估算（每个因子误差都在 $2\\times$ 以内，即 $\\sigma_i=1$）：<strong>最坏情况</strong>"
          "（误差同向叠加）是 $2^{1+1+1+1+1}=2^5=32$ 倍——这是很多人悲观直觉的来源；"
          "但如果五个误差<em>相互独立</em>（这是更现实的假设，因为你不太可能在五个不相关的因子上同时犯同方向的错），"
          "按 RSS 合成是 $\\sigma_{\\text{total}}=\\sqrt{5}\\approx2.24$，总误差倍数只有 "
          "$2^{2.24}\\approx4.7$ 倍。<strong>这个 4.7 倍，才是你在面试里应该报的置信区间量级</strong>，"
          "而不是吓人的 32 倍或盲目乐观的差不多准。"),
        CALLOUT("warn", "<strong>这个公式有一个前提：因子误差相互独立。</strong>如果你的因子之间有强相关"
                        "（比如团队人数和标注速率都被同一个实际到岗率污染），RSS 会低估真实误差，"
                        "这时更接近最坏情况的线性相加。<em>面试里诚实的说法是</em>："
                        "「这几个因子的误差我认为基本独立，所以总误差大概是各自误差的均方根，而不是简单相加」"
                        "——<strong>只要说出独立性假设这四个字，就已经比大多数人多拿一分</strong>。"),
        DUAL(
            "翻译成人话：估算链条不是一步错步步错，也不是反正都是估的无所谓。"
            "五个环节各自准到 2 倍以内，最终答案大概率能准到 5 倍以内——这已经足够回答这是 1 万还是 10 万这类问题了。",
            "这也解释了为什么工程上偏爱多个独立的粗略信号而不是一个精确但脆弱的信号："
            "<em>独立性带来的方差收缩（$\\sqrt{n}$ 而不是 $n$）是估算方法论里最值钱的一条数学事实，"
            "它同样是集成学习方差降低的同一个原理（bagging，见 C64-01）。</em>",
        ),
    ])),

    # ============================================================== 3
    ("anchor-numbers", "可背的锚点数字表：面试前一晚该刻进脑子的那些数", "".join([
        P("Fermi 估算法的第②步锚点，前提是你手里<strong>已经有一批数字可以直接调用</strong>。"
          "下面三张表是 ML / CV 岗面试里最常用得上的锚点——<strong>数量级正确就够，不要求精确到个位</strong>，"
          "硬件更新很快，记住的是这一代 GPU 大概是几百 TFLOPS、几个 TB/s 这个量级，而不是具体某一款的参数表。"),
        TABLE(["硬件", "FP16/BF16 算力（近似）", "显存带宽（近似）", "显存容量（常见配置）"], [
            ["V100", "~125 TFLOPS", "~900 GB/s", "16 / 32 GB"],
            ["A100 (80G)", "~300 TFLOPS", "~2 TB/s", "80 GB"],
            ["H100 (SXM)", "~1000 TFLOPS", "~3.3 TB/s", "80 GB"],
            ["RTX 4090", "~330 TFLOPS（稀疏）", "~1 TB/s", "24 GB"],
            ["车端 Jetson Orin 级", "~275 TOPS（INT8）", "~200 GB/s", "32 / 64 GB"],
        ]),
        TABLE(["标注 / 人力锚点", "量级", "备注"], [
            ["检测框标注单价", "约 0.5–1 元 / 框（简单场景）", "复杂多目标 / 需要属性标注时上浮 2-5 倍"],
            ["检测框标注人天产出", "约 800–1200 框 / 人天", "含正常的核对与休息时间，不是理论峰值"],
            ["语义分割标注人天产出", "约 20–60 张 / 人天", "远低于框标注——这是分割比检测贵得多的直接原因"],
            ["图像分类标注人天产出", "约 2000–5000 张 / 人天", "只判类别，不画框，产出最高"],
        ]),
        TABLE(["数据 / 网络锚点", "量级", "备注"], [
            ["1080p 图像（JPEG 压缩）", "约 200–400 KB", "面试里估存储时最常用的锚点"],
            ["1080p 图像（未压缩 RGB）", "约 6 MB", "= 1920×1080×3 字节"],
            ["千兆以太网", "1 Gbps ≈ 125 MB/s", "车端到云端数据回传常用参照"],
            ["5G / 4G LTE 上行", "5G 约几百 Mbps，LTE 约 10–50 Mbps", "车队回传带宽的现实上限"],
        ]),
        CALLOUT("intuition", "<strong>这三张表怎么用？</strong>面试官报出一个问题（设计一个数据回传方案），"
                             "你不需要精确记得某型号的参数，你需要的是<em>反应速度</em>："
                             "「图像大概几百 KB，网络大概几十到几百 Mbps，除一下就知道回传一张图大概几十到几百毫秒」——"
                             "这个反应速度，才是锚点表真正训练的东西。"),
    ])),

    # ============================================================== 4
    ("labeling", "ML 场景估算 ①：标注成本与工期", "".join([
        P("标注估算是数据闭环（见 C58）里最先要回答的问题：<strong>要多久、要多少钱，能拿到能训练的数据？</strong>"
          "分解方式很直接——先数框数，再除以产出速率，再除以团队人数："),
        MATH("T_{\\text{人天}} = \\frac{N_{\\text{图像}} \\times k_{\\text{框/图}}}"
             "{r_{\\text{框/人天}}}, \\qquad T_{\\text{日历天}} = \\frac{T_{\\text{人天}}}{n_{\\text{团队人数}}}, "
             "\\qquad C = N_{\\text{图像}} \\times k_{\\text{框/图}} \\times p_{\\text{单价}}"),
        P("代入一个 TSR 例子：要标注 10 万张图像用于检测训练，每张图平均 3 个标志框，"
          "按锚点表 1000 框/人天、单价 0.8 元/框、10 人团队算：总框数 $= 10^5 \\times 3 = 3\\times10^5$，"
          "总人天 $= 3\\times10^5 / 1000 = 300$，日历工期 $= 300/10=30$ 天（约一个月），"
          "总成本 $= 3\\times10^5 \\times 0.8 = 24$ 万元。这四个数字——<strong>框数、人天、工期、成本</strong>"
          "——是面试官期待你能一口气报出来的完整答案，而不是只报其中一个。"),
        DUAL(
            "这个公式看起来简单到不需要练习，但<strong>面试里最容易失分的地方恰恰是它</strong>："
            "候选人算出三十天就停了，没有意识到面试官真正想听的是——"
            "你有没有意识到这个数字背后藏着质检返工、标注员流失、标注规范反复修订这些没算进公式的隐藏成本。",
            "更严谨地说，朴素公式给出的是<strong>下界</strong>，而不是期望值。"
            "真实工期通常要乘一个 1.3–1.5 的缓冲系数（buffer factor）来覆盖质检抽检、"
            "标注规范迭代、长尾类别的定向补标（见 C58-03/04）。"
            "<em>面试里主动说出这个缓冲系数，比算出精确的三十天更能体现工程判断力——"
            "这也是本模块最后一节「什么时候估算错得离谱」要专门讲隐藏常数的原因。</em>",
        ),
    ])),

    # ============================================================== 5
    ("training-time", "ML 场景估算 ②：训练时长", "".join([
        P("训练时长的分解方式：把总计算量表示成模型见过多少张图，除以每秒能喂给模型多少张图："),
        MATH("T_{\\text{秒}} = \\frac{N_{\\text{图像}} \\times E_{\\text{epoch 数}}}{\\Phi_{\\text{吞吐（图/秒）}}}"),
        P("代入一个例子：10 万张图，训练 24 个 epoch（检测任务常见的两倍 schedule），"
          "单卡吞吐 300 图/秒（中端卡训练中等规模检测模型的常见量级）：总计看过的图像数 "
          "$=10^5\\times24=2.4\\times10^6$，训练时长 $=2.4\\times10^6/300=8000$ 秒 $\\approx2.22$ 小时。"),
        TABLE(["模型 / 任务量级", "常见 epoch 数锚点", "备注"], [
            ["检测（COCO 类，1x/2x schedule）", "12 / 24 epoch", "两阶段/anchor-based 检测器的经典配置"],
            ["实时检测器（YOLO 系）", "约 300 epoch", "依赖大量数据增强，需要更长训练弥补增强带来的噪声"],
            ["大规模预训练（ViT / LLM 量级）", "1 到几个 epoch", "数据量本身极大，多 epoch 意义不同，见 C64"],
        ]),
        CALLOUT("warn", "<strong>吞吐 $\\Phi$ 是这个公式里最容易被高估的因子。</strong>厂商标称的 TFLOPS "
                        "对应的是理想算力上限，真实训练吞吐往往打 3-5 折——数据增强的 CPU 瓶颈"
                        "（见 C56-04）、数据加载 I/O、GPU 利用率波动都会吃掉理论吞吐。"
                        "<strong>面试里报吞吐数字时，主动说明这是实测量级还是理论峰值，是一个加分的诚实信号。</strong>"),
        DUAL(
            "记住这个公式的最简形式就够了：训练时长 = 模型看图总数 ÷ 每秒能喂多少图。"
            "epoch 数和吞吐都是可以现场问面试官、或者用锚点表现推的两个数。",
            "这个公式隐含一个假设：吞吐 $\\Phi$ 在训练全程恒定。"
            "真实情况里，学习率 warmup 阶段、验证阶段、checkpoint 保存都会让瞬时吞吐低于峰值，"
            "<em>所以用实测的滑动平均吞吐而不是某个 batch 的峰值吞吐来估算，误差会小得多——"
            "这正是本模块最后一节「非线性」要讲的那类坑的一个具体例子。</em>",
        ),
    ])),

    # ============================================================== 6
    ("memory", "ML 场景估算 ③：显存", "".join([
        P("显存估算的分解方式是<strong>参数本身 + 优化器状态 + 激活值</strong>三部分相加——"
          "注意这里是加法而不是乘法，因为三者是同时占用显存的独立空间，不是同一个量的不同视角："),
        MATH("M_{\\text{总}} \\approx N_{\\text{参数}} \\times (b_w + b_{\\text{优化器}}) + A_{\\text{激活}}"
             "(\\text{batch size})"),
        TABLE(["优化器", "每参数额外字节数（混合精度典型配置）", "相对纯 fp16 权重的倍数"], [
            ["SGD（无动量）", "0", "1×（只有权重本身）"],
            ["SGD + Momentum", "+4（一份动量，常存 fp32）", "约 3×"],
            ["Adam / AdamW", "+12（fp32 master 权重 4 + 一阶矩 m 4 + 二阶矩 v 4）",
             "<strong>约 7×</strong>——这是 Adam 系显存占用远高于 SGD 的直接原因"],
        ]),
        P("代入一个 TSR 检测骨干的例子：5 千万参数（中等规模检测骨干 + 头的量级），"
          "fp16 权重 2 字节 + fp32 master 4 字节 + 一阶矩 4 字节 + 二阶矩 4 字节 $=14$ 字节/参数："
          "参数与优化器状态占用 $5\\times10^7\\times14$ 字节 $\\approx0.65$ GB，"
          "再加上激活值（随 batch size 和分辨率变化，这里取一个典型值 2 GB），"
          "总显存量级 $\\approx2.65$ GB——<strong>这解释了为什么同样大小的模型，"
          "用 SGD 训练能塞进更小的卡，换成 AdamW 就可能溢出</strong>。"),
        CALLOUT("intuition", "<strong>激活值才是真正随 batch size 和分辨率暴涨的那一项。</strong>"
                             "参数和优化器状态的显存是常数（不随 batch size 变），激活值大致与 "
                             "batch size × 分辨率 × 层数 成正比——这就是为什么调小 batch size 或用梯度检查点"
                             "（用重计算换显存）能在显存不够时救命，而换更省显存的优化器对激活值毫无帮助。"),
        DUAL(
            "记一个粗糙但好用的心法：<strong>Adam 系优化器的显存大约是纯 fp16 权重的 7 倍</strong>——"
            "参数量差不多的两个模型，一个用 SGD 一个用 AdamW，后者可能因为优化器状态就多占几个 GB。",
            "更完整的账还应该算进梯度本身的显存（通常与权重同精度，再加一份），以及"
            "分布式训练里的通信缓冲区。<em>面试里给出上面这个简化公式再补一句这还没算梯度和通信开销，"
            "真实数字会更高一些，比假装公式已经完备更可信。</em>",
        ),
    ])),

    # ============================================================== 7
    ("serving", "ML 场景估算 ④：QPS、实例数与存储带宽", "".join([
        P("服务容量估算的核心问题是：<strong>要满足目标 QPS，需要几台机器？</strong>"
          "分解方式是先算单实例能扛多少 QPS，再用目标 QPS 去除："),
        MATH("\\text{QPS}_{\\text{单实例}} \\approx \\frac{\\text{并发数}}{\\text{单次推理延迟}}, "
             "\\qquad N_{\\text{实例数}} = \\left\\lceil \\frac{\\text{QPS}_{\\text{目标}}}"
             "{\\text{QPS}_{\\text{单实例}}} \\right\\rceil"),
        ASCII("""目标 QPS = 1000
单次推理延迟 20ms，每实例并发数 = 4
  -> 单实例 QPS = 并发数(4) / 延迟(0.02s) = 200
  -> 实例数 = ceil(1000 / 200) = 5 台"""),
        P("代入车队/云端 TSR 推理服务的例子：目标 1000 QPS，单次推理延迟 20ms，每实例支持 4 路并发批处理，"
          "单实例 QPS $=4/0.02=200$，需要实例数 $=\\lceil1000/200\\rceil=5$ 台。"),
        CALLOUT("intuition", "<strong>存储与带宽的估算是同一套乘法思路的延伸。</strong>"
                             "存储需求 = 图像数 × 单张大小；带宽需求 = 摄像头数 × 帧率 × 单帧大小 × 8（字节转比特）。"
                             "notebook 的练习会把这两个具体实现出来——这里不重复公式，"
                             "只强调它们和 QPS/显存用的是同一套数一个量乘以单位消耗、再除以单位时间或容量的骨架。"),
        CALLOUT("warn", "<strong>本节只给通用的数量级心算，不是完整的系统设计答案。</strong>"
                        "真实的容量规划还包括降级方案（模型/特征降级）、扩缩容策略、监控告警阈值、"
                        "p99 延迟而非均值——这些属于系统设计的范畴，<strong>完整方法论见 C63-04</strong>，"
                        "本课不重复，需要时直接引用。"),
    ])),

    # ============================================================== 8
    ("recall-and-crosscheck", "数据需求估算与数量级校验：两条独立路径互相验证，以及什么时候会错得离谱", "".join([
        P("面试里经常出现的一类估算是「要让某个稀有类别的召回率从 70% 提到 90%，大概需要多少数据？」——"
          "这类问题没有精确解，但可以用<strong>幂律外推</strong>给出一个数量级合理的答案："
          "经验上，误差率（$1-\\text{recall}$）随数据量大致按幂律下降："),
        MATH("\\frac{1 - R_{\\text{目标}}}{1 - R_0} = \\left(\\frac{N_0}{N_{\\text{目标}}}\\right)^{\\alpha}"
             "\\quad\\Longrightarrow\\quad N_{\\text{目标}} = N_0 \\cdot "
             "\\left(\\frac{1-R_0}{1-R_{\\text{目标}}}\\right)^{1/\\alpha}"),
        P("其中 $\\alpha$（通常在 0.3–0.5 之间，需要用你自己场景的历史数据拟合，这里只是可背的粗略锚点）"
          "刻画了每多一倍数据、错误率下降多少。代入例子：某稀有标志类别用 5000 张图的试点数据达到 70% 召回，"
          "目标 90%，取 $\\alpha=0.4$：比值 $=(1-0.7)/(1-0.9)=3$，"
          "$N_{\\text{目标}}=5000\\times3^{1/0.4}=5000\\times3^{2.5}\\approx7.8\\times10^4$ 张——"
          "也就是说，从 70% 到 90% 召回，数据量大约要变成原来的 <strong>15-16 倍</strong>，"
          "这正是幂律边际收益递减的直观体现：越往后每一个百分点都更贵。"),
        ASCII("""路径 A（幂律外推）                    路径 B（标注预算反推）
5000 张 @ 70% 召回，目标 90%           预算 8 万元 / 单价 0.8 元/框 / 3 框/图
  用幂律公式，alpha=0.4                  = 33,333 张图
  得 N ≈ 78,000 张                       若不够，说明预算需要翻倍
          \\                                   /
           \\_________________________________/
                        |
        两条路径量级接近（同为万级）-> 估计可信
        若相差 10 倍以上 -> 回头检查 alpha 或预算假设"""),
        CALLOUT("intuition", "<strong>这就是数量级校验的完整含义</strong>：不是重新算一遍同一个公式，"
                             "是<em>换一条完全独立、依赖不同假设的路径</em>再算一遍。"
                             "上面的例子里，路径 A 依赖幂律指数 $\\alpha$，路径 B 依赖标注预算与单价——"
                             "两者共用的信息几乎为零，如果它们的答案量级接近，可信度会大幅提高；"
                             "如果差了一个数量级，说明至少有一个假设是错的，<strong>面试里主动说"
                             "「让我换个角度再验证一下」，这个动作本身就是加分项，无论结果一致与否</strong>。"),
        DUAL(
            "两条腿走路：一条腿崴了还有另一条腿撑着，两条腿的结果差不多，你才敢往前走。",
            "更严谨地说，如果两条估算路径的误差来源不相关（假设 A 依赖模型的统计规律，假设 B 依赖商业约束），"
            "它们同时犯同向错误的概率远低于各自单独犯错的概率——这与第二节的独立误差 RSS 合成是同一个原理，"
            "<em>只是这里用的是两条路径而不是多个因子，粒度更粗、但逻辑完全一致。</em>",
        ),
        H3("什么时候估算错得离谱：隐藏常数、非线性、长尾"),
        P("Fermi 估算法不是万能的。有三类系统性原因会让一个步骤正确、逻辑自洽的估算，"
          "结果照样离谱地错——认清它们，比会套公式更重要。"),
        TABLE(["失效模式", "典型例子", "为什么公式测不出来", "怎么防"], [
            ["<strong>隐藏常数</strong>", "「标注一张图 5 分钟」没算质检返工、界面加载、标注规范反复修订",
             "朴素公式只算了理想操作时间，真实数字常常是估算的 1.5–3 倍",
             "主动乘一个缓冲系数（见模块 04 标注成本一节），并说出来"],
            ["<strong>非线性</strong>", "GPU 利用率超过 80% 后延迟不是线性增长，是接近指数增长",
             "线性外推在临界点附近会系统性低估——排队论里这叫利用率趋近 1 时队长发散",
             "只在远离临界点的区域做线性外推，接近临界点要单独讨论"],
            ["<strong>长尾</strong>", "用整体平均的每公里遇到几个标志去估某个稀有标志类别需要多少数据",
             "平均值被头部类别主导，稀有类的真实出现频率可能比平均值低 1-2 个数量级",
             "长尾类别必须单独估算，不能用整体均值代替（见 C58）"],
        ]),
        CALLOUT("danger", "<strong>长尾是三者中最容易被忽视、也最容易让估算离谱的一个。</strong>"
                          "如果你用整体平均每公里 5 个标志去估计多久能采够限速为 100 的稀有限速牌，"
                          "答案可能差出两个数量级——因为那类标志在整体分布里占比可能只有万分之一，"
                          "而平均这个统计量恰恰是被高频类别主导的。<em>正确做法是先问这个类别在整体分布里"
                          "占比大概多少，再单独对它做 Fermi 估算，而不是套用整体的锚点数字。</em>"),
        DUAL(
            "三类坑总结成一句话：<strong>公式没错，是你喂给公式的数字里，有一个悄悄假设了平均、线性、理想情况，"
            "而现实在某个角落恰好不是这样</strong>。",
            "形式化地说，Fermi 估算的乘法分解 $Q=\\prod f_i$ 隐含假设每个 $f_i$ 是<em>场景无关的常数</em>——"
            "隐藏常数是这个常数本身被低估，非线性是 $f_i$ 其实依赖 $Q$ 本身（正反馈），"
            "长尾是 $f_i$ 的真实分布方差极大，用期望值代替具体场景是错的。<strong>三者是同一个假设"
            "（因子稳定且具有代表性）在三个不同维度上的失效。</strong>",
        ),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("Fermi 估算是一门手艺，长期以来靠经验传承而不是系统研究。但它和现代 ML 的两个前沿方向"
          "有意外的交集，值得知道。"),
        UL([
            "<strong>数据量与性能的幂律关系，最近几年才被严格量化。</strong>"
            "Kaplan et al.（2020）系统研究了语言模型的 scaling law，Hoffmann et al. 的 Chinchilla（2022）"
            "进一步指出：给定算力预算，模型规模和数据量应该按什么比例分配。"
            "<em>本模块「达到目标召回需要多少数据」用的幂律外推，是这类工作在检测任务上的粗糙类比——"
            "检测任务的 scaling 指数 $\\alpha$ 目前没有像语言模型那样被系统测过，这是一个开放的实证问题。</em>",
            "<strong>面试里估算对不对的评判标准，各家公司没有统一 rubric。</strong>"
            "有的面试官关心过程是否显式、误差是否被讨论，有的更在意最终数量级是否落在他心里的范围内，"
            "容忍度可以从 2-3 倍到 10 倍不等。<em>目前没有公开的、跨公司一致的评分标准，"
            "这使得练习估算本身的收益，很大程度上依赖候选人对具体公司文化的了解。</em>",
            "<strong>LLM 正在改变记锚点数字这件事本身的价值。</strong>如果面试允许查资料，"
            "锚点数字可以现查，稀缺的能力变成知道该拆成哪几个因子、该用哪条独立路径校验——"
            "这与 C62 frontier 里 coding 面试重心从解出来转向验证是同一个趋势在估算题上的版本。",
            "<strong>长尾场景下的估算方法学还很不成熟。</strong>"
            "如何量化用整体均值估计稀有类别这类错误的期望危害、如何设计对长尾稳健的估算流程，"
            "目前更多是工程经验（见 C58），还没有形成教材化的方法论。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Lawrence Weinstein &amp; John A. Adam, "
                         "<em>Guesstimation: Solving the World's Problems on the Back of a Cocktail Napkin</em>"
                         "（2008）——Fermi 估算法的经典入门读物，本模块「分解-锚点-相乘-校验」四步"
                         "直接脱胎于这本书的方法论。<strong>★</strong> Jared Kaplan et al., "
                         "<em>Scaling Laws for Neural Language Models</em>（2020）——数据/算力/模型规模的"
                         "幂律关系，本模块「数据需求估算」一节的理论源头。<strong>★</strong> "
                         "Jordan Hoffmann et al., <em>Training Compute-Optimal Large Language Models</em>"
                         "（Chinchilla，2022）——给定算力预算下模型规模与数据量的联合估算，"
                         "训练时长估算的进阶参考。</p><p>相邻课程：<strong>C63 模块 04</strong>"
                         "（系统设计里的完整容量估算，含降级方案与监控，本课不重复）、"
                         "<strong>C58</strong>（长尾数据与定向采集策略）、"
                         "<strong>C56 模块 04</strong>（数据增强的吞吐瓶颈，训练时长估算里吞吐打折的成因）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 01 · 估算题与数量级心算（Fermi 估算 / 误差传播 / 标注-训练-显存-QPS 四案例 / 双路径校验）

目标：把"拍脑袋估一个数"变成**几个可以运行、可以断言的小工具**。

本 notebook 你会亲手实现：
1. **环境自检**
2. **Fermi 估算器** —— 把因子列表相乘得到点估计
3. **对数域误差传播器** —— 用 RSS 合成多个独立因子的误差，对比"最坏情况"与"独立情况"
4. **锚点数字表** —— 内置一份可查、可断言的锚点常数
5. **四个完整估算案例** —— 标注成本与工期 / 训练时长 / 显存 / QPS 与实例数，逐步实现
6. **达到目标召回需要多少数据** —— 幂律外推
7. **双路径交叉校验器** —— 判定两条独立估算是否互相印证

> 心智模型：**分解 → 锚点 → 相乘 → 校验，四步都做到，比算得精确更重要。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'sqrt')

print('\\n环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · Fermi 估算器：分解 → 锚点 → 相乘

把因子列表相乘，得到一个点估计。因子本身的选取（分解 + 锚点）是人做的事，
这个函数只负责"相乘"这一步——但正是这一步最容易因为单位不对齐而出错，所以我们还顺手做单位检查。"""),

    code("""def fermi_estimate(factors):
    \"\"\"factors: 一串已经对齐单位的因子。返回它们的乘积（点估计）。\"\"\"
    p = 1.0
    for f in factors:
        p *= f
    return p

# 例子：一支 500 辆车的测试车队，每车每天跑 320 公里，平均每公里遇到 5 个交通标志，
# 一天总共会记录到多少个标志实例？
fleet_size, km_per_day, signs_per_km = 500, 320, 5
total_signs = fermi_estimate([fleet_size, km_per_day, signs_per_km])
assert total_signs == 800_000.0, total_signs

print(f'车队 {fleet_size} 辆 × {km_per_day} 公里/天 × {signs_per_km} 标志/公里 = {total_signs:,.0f} 个标志/天')
print('\\n三个因子里换任何一个数量级都会让结果差 10 倍——这就是为什么锚点数字要背对量级，而不是背对具体数值。')"""),

    md("""## 2 · 对数域误差传播：为什么不是简单相加

每个因子的误差用"以 2 为底的对数误差" $\\sigma_i$ 表示（$\\sigma=1$ 表示落在 0.5x-2x 之间）。
独立因子的误差按方差可加性（RSS）合成，而不是线性相加。"""),

    code("""def log_error_rss(sigmas_bits):
    \"\"\"sigmas_bits: 每个因子的对数误差（比特，以2为底）。假设相互独立，返回合成后的总误差（比特）。\"\"\"
    return math.sqrt(sum(s * s for s in sigmas_bits))

def uncertainty_factor(sigma_bits):
    \"\"\"把比特数的误差换算成"乘除倍数"。\"\"\"
    return 2 ** sigma_bits

sigmas = [1, 1, 1, 1, 1]                      # 五个因子，各自误差在 2x 以内
worst_case = 2 ** sum(sigmas)                 # 最坏情况：误差同向叠加，线性相加
independent = uncertainty_factor(log_error_rss(sigmas))   # 独立假设：RSS 合成

assert worst_case == 32
assert abs(log_error_rss(sigmas) - math.sqrt(5)) < 1e-9
assert 4.5 < independent < 5.0, independent

print(f'五个因子各自误差 2x 以内：')
print(f'  最坏情况（同向叠加）  -> 总误差 ×{worst_case}')
print(f'  独立假设（RSS 合成）  -> 总误差 ×{independent:.1f}')
print('\\n面试里该报的是后一个数字（连同"假设独立"这句话），而不是前一个吓人的 32 倍。')"""),

    md("""## 3 · 锚点数字表

数量级正确就够，不要求精确到个位。内置一份可查的常数表，并用"排序关系"而不是"精确数值"做断言——
因为这些数字本身就是近似值，断言排序关系比断言小数点后几位更符合它的本质。"""),

    code("""ANCHORS_GPU_TFLOPS = {'V100': 125, 'A100_80G': 300, 'H100_SXM': 1000}
ANCHORS_GPU_BANDWIDTH_GBs = {'V100': 900, 'A100_80G': 2000, 'H100_SXM': 3300}
ANCHORS_LABELING = {
    'price_per_box_cny': 0.8,
    'boxes_per_person_day': 1000,
    'seg_images_per_person_day': 40,
}
ANCHORS_DATA = {
    'image_1080p_jpeg_kb': 300,
    'image_1080p_raw_mb': 6.2,
    'gigabit_eth_mbps': 1000,
    'lte_uplink_mbps': 30,
}

# 断言的是数量级关系，而不是精确到个位的数值——这才是锚点数字该有的用法
assert ANCHORS_GPU_TFLOPS['H100_SXM'] > ANCHORS_GPU_TFLOPS['A100_80G'] > ANCHORS_GPU_TFLOPS['V100']
assert ANCHORS_GPU_BANDWIDTH_GBs['H100_SXM'] > ANCHORS_GPU_BANDWIDTH_GBs['A100_80G']
assert ANCHORS_LABELING['boxes_per_person_day'] > ANCHORS_LABELING['seg_images_per_person_day']
assert ANCHORS_DATA['image_1080p_raw_mb'] * 1024 > ANCHORS_DATA['image_1080p_jpeg_kb']   # 未压缩确实比压缩大

for name, d in [('GPU 算力 (TFLOPS)', ANCHORS_GPU_TFLOPS), ('GPU 显存带宽 (GB/s)', ANCHORS_GPU_BANDWIDTH_GBs)]:
    print(name, '->', d)
print('\\n✅ 锚点表就位：记的是量级和排序（H100 > A100 > V100），不是精确到个位的参数表。')"""),

    md("""## 4 · 案例①：标注成本与工期

$T_{\\text{人天}} = N_{\\text{图像}} \\times k_{\\text{框/图}} / r_{\\text{框/人天}}$，
$T_{\\text{日历天}} = T_{\\text{人天}} / n_{\\text{团队人数}}$，
$C = N_{\\text{图像}} \\times k_{\\text{框/图}} \\times p_{\\text{单价}}$。"""),

    code("""def labeling_estimate(n_images, boxes_per_image, team_size,
                      boxes_per_person_day=ANCHORS_LABELING['boxes_per_person_day'],
                      price_per_box=ANCHORS_LABELING['price_per_box_cny']):
    \"\"\"返回 (总框数, 总人天, 日历工期天数, 总成本元)。\"\"\"
    total_boxes = n_images * boxes_per_image
    person_days = total_boxes / boxes_per_person_day
    calendar_days = person_days / team_size
    cost = total_boxes * price_per_box
    return total_boxes, person_days, calendar_days, cost

# TSR 例子：10 万张图，每图 3 个标志框，10 人团队
boxes, person_days, days, cost = labeling_estimate(100_000, 3, 10)
assert boxes == 300_000
assert person_days == 300.0
assert days == 30.0
assert cost == 240_000.0

print(f'总框数 {boxes:,.0f}，总人天 {person_days:,.0f}，日历工期 {days:.0f} 天，总成本 ¥{cost:,.0f}')
print('\\n四个数字缺一不可：面试官期待的是完整的一套答案，不是只报其中一个。')"""),

    md("""## 5 · 案例②：训练时长

$T_{\\text{秒}} = N_{\\text{图像}} \\times E_{\\text{epoch}} / \\Phi_{\\text{吞吐}}$。"""),

    code("""def training_hours(n_images, epochs, throughput_img_per_sec):
    total_images_seen = n_images * epochs
    seconds = total_images_seen / throughput_img_per_sec
    return seconds / 3600

hours = training_hours(100_000, 24, 300)
assert abs(hours - 2.2222222) < 1e-4, hours
print(f'10 万张图 × 24 epoch ÷ 300 图/秒 = {hours:.2f} 小时')

# 吞吐打七折(真实训练常见的 IO/增强瓶颈)会怎样？
hours_derated = training_hours(100_000, 24, 300 * 0.7)
assert hours_derated > hours
print(f'吞吐打七折后：{hours_derated:.2f} 小时（约变成 {hours_derated/hours:.2f} 倍）')
print('\\n✅ 吞吐是最容易被高估的因子——报数字时说清是实测还是理论峰值。')"""),

    md("""## 6 · 案例③：显存

$M_{\\text{总}} \\approx N_{\\text{参数}} \\times (b_w + b_{\\text{优化器}}) + A_{\\text{激活}}$。
AdamW 混合精度典型配置：fp16 权重 2 字节 + fp32 master 4 字节 + 一阶矩 4 字节 + 二阶矩 4 字节 = 14 字节/参数。"""),

    code("""def gpu_memory_gb(n_params, bytes_per_param=14, activation_gb=2.0):
    param_bytes = n_params * bytes_per_param
    return param_bytes / 1024**3 + activation_gb

mem_adamw = gpu_memory_gb(50_000_000)                          # AdamW: 14 字节/参数
mem_sgd = gpu_memory_gb(50_000_000, bytes_per_param=2)         # 纯 fp16 SGD 无动量: 2 字节/参数

assert abs(mem_adamw - 2.6519) < 1e-3, mem_adamw
assert abs(mem_sgd - 2.0931) < 1e-3, mem_sgd
assert mem_adamw > mem_sgd

print(f'5 千万参数模型，AdamW 混合精度显存 ≈ {mem_adamw:.2f} GB')
print(f'同样模型，纯 SGD（无动量）显存    ≈ {mem_sgd:.2f} GB')
print(f'仅优化器状态差异就多占了 {(mem_adamw - mem_sgd):.2f} GB。')"""),

    md("""## 7 · 案例④：QPS 与实例数

$\\text{QPS}_{\\text{单实例}} = \\text{并发数} / \\text{单次延迟}$，
$N_{\\text{实例}} = \\lceil \\text{QPS}_{\\text{目标}} / \\text{QPS}_{\\text{单实例}} \\rceil$。"""),

    code("""def instances_needed(target_qps, latency_sec, concurrency_per_instance=1):
    qps_per_instance = concurrency_per_instance / latency_sec
    return math.ceil(target_qps / qps_per_instance)

n = instances_needed(1000, 0.02, concurrency_per_instance=4)
assert n == 5, n
print(f'目标 1000 QPS，单次延迟 20ms，每实例并发 4 -> 需要 {n} 台实例')

# 延迟翻倍(比如换成更大的模型)会怎样？
n2 = instances_needed(1000, 0.04, concurrency_per_instance=4)
assert n2 == 10
print(f'延迟翻倍到 40ms -> 需要 {n2} 台实例（翻倍关系，符合公式里延迟和实例数成正比）')"""),

    md("""## 8 · 达到目标召回需要多少数据：幂律外推

$(1-R_{\\text{目标}})/(1-R_0) = (N_0/N_{\\text{目标}})^{\\alpha}$，
解出 $N_{\\text{目标}} = N_0 \\cdot ((1-R_0)/(1-R_{\\text{目标}}))^{1/\\alpha}$。"""),

    code("""def data_needed_for_recall(n0, r0, target_recall, alpha=0.4):
    ratio = (1 - r0) / (1 - target_recall)
    return n0 * ratio ** (1 / alpha)

n_target = data_needed_for_recall(5000, 0.70, 0.90, alpha=0.4)
assert 77_000 < n_target < 79_000, n_target
print(f'试点 5000 张 @ 70% 召回，目标 90% 召回，alpha=0.4 -> 需要约 {n_target:,.0f} 张')
print(f'数据量要变成原来的 {n_target/5000:.1f} 倍——这就是幂律边际收益递减的直观体现。')"""),

    md("""## 9 · 双路径交叉校验器

两条完全独立、依赖不同假设的路径，如果答案量级接近，可信度大幅提高；
差一个数量级以上，说明至少有一个假设错了，要回头检查。"""),

    code("""def cross_check(estimate_a, estimate_b, tolerance=3.0):
    \"\"\"返回 (是否可信, 两者比值)。比值 <= tolerance 判定为可信。\"\"\"
    lo, hi = min(estimate_a, estimate_b), max(estimate_a, estimate_b)
    ratio = hi / lo if lo > 0 else float('inf')
    return ratio <= tolerance, ratio

# 路径 A：上面幂律外推得到的 n_target ≈ 78,000 张
# 路径 B：按标注预算反推，预算 8 万元，单价 0.8 元/框，每图 3 个框
budget_cny, price_per_box, boxes_per_image = 80_000, 0.8, 3
path_b = budget_cny / price_per_box / boxes_per_image

ok, ratio = cross_check(n_target, path_b, tolerance=3.0)
assert ok is True, (n_target, path_b, ratio)
print(f'路径 A（幂律外推）≈ {n_target:,.0f} 张，路径 B（预算反推）≈ {path_b:,.0f} 张')
print(f'比值 {ratio:.2f} <= 3.0 -> 可信：两条独立路径互相印证。')

# 如果路径 B 是一个数量级偏差很大的错误估计呢？
ok_bad, ratio_bad = cross_check(n_target, 900_000, tolerance=3.0)
assert ok_bad is False
print(f'\\n若路径 B 给出 900,000 张，比值 {ratio_bad:.1f} > 3.0 -> 不可信，需要回头检查假设。')"""),

    md("""## ✏️ 练习 1：存储需求估算器

实现 `storage_needed_tb(n_images, avg_size_kb)`：返回存储 N 张图像需要多少 TB
（$1\\,\\text{TB} = 1024^3\\,\\text{KB}$）。"""),

    code("""def storage_needed_tb(n_images, avg_size_kb):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
s1 = storage_needed_tb(1_000_000, 300)
assert 0.27 < s1 < 0.29, s1

s2 = storage_needed_tb(10_000_000, 300)
assert abs(s2 - 10 * s1) < 1e-9, (s1, s2)      # 图片数变 10 倍，存储线性变 10 倍

print(f'100 万张 1080p 压缩图 ≈ {s1:.3f} TB')
print(f'1000 万张同样的图     ≈ {s2:.3f} TB（10 倍关系）')
print('\\n✅ 练习 1 通过：存储需求 = 图像数 × 单张大小，和 QPS/显存用的是同一套"数量 × 单位消耗"骨架。')"""),

    md("""## ✏️ 练习 2：车载多摄像头带宽估算器

实现 `bandwidth_mbps(n_cameras, fps, image_size_kb)`：返回 N 路摄像头、每路 fps 帧/秒、
每帧 image_size_kb 大小时，总共需要多少 Mbps 带宽（$1\\,\\text{KB}=1024\\,\\text{字节}=8192\\,\\text{比特}$）。"""),

    code("""def bandwidth_mbps(n_cameras, fps, image_size_kb):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
bw = bandwidth_mbps(6, 30, 200)
assert abs(bw - 294.912) < 1e-6, bw

bw2 = bandwidth_mbps(6, 60, 200)
assert abs(bw2 - 2 * bw) < 1e-6      # 帧率翻倍，带宽线性翻倍

print(f'6 路摄像头 × 30fps × 200KB/帧 = {bw:.1f} Mbps')
print(f'帧率翻倍到 60fps            = {bw2:.1f} Mbps')
print('\\n✅ 练习 2 通过：这正是本模块「存储与带宽」一节说的——和 QPS/显存同一套心算骨架。')"""),

    md("""## ✏️ 练习 3：把点估计换算成置信区间

实现 `estimate_range(midpoint, sigma_bits)`：给定一个 Fermi 点估计 `midpoint` 和它的对数误差
`sigma_bits`（以 2 为底），返回 `(low, high) = (midpoint / 2**sigma_bits, midpoint * 2**sigma_bits)`。"""),

    code("""def estimate_range(midpoint, sigma_bits):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert estimate_range(100, 1) == (50.0, 200.0)
assert estimate_range(1000, 2) == (250.0, 4000.0)

lo, hi = estimate_range(total_signs, log_error_rss([1, 1, 1]))
print(f'车队每日标志数点估计 {total_signs:,.0f}，三因子各 2x 误差、独立假设下的区间：'
      f'[{lo:,.0f}, {hi:,.0f}]')
print('\\n✅ 练习 3 通过：把第 2 节的"误差比特数"落地成一个真正能报给面试官的区间。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def storage_needed_tb(n_images, avg_size_kb):
    return n_images * avg_size_kb / 1024 ** 3"""),

    code("""# 练习 2 参考答案
def bandwidth_mbps(n_cameras, fps, image_size_kb):
    bits_per_sec = n_cameras * fps * image_size_kb * 1024 * 8
    return bits_per_sec / 1e6"""),

    code("""# 练习 3 参考答案
def estimate_range(midpoint, sigma_bits):
    factor = 2 ** sigma_bits
    return midpoint / factor, midpoint * factor"""),

    md("""---
## 🧪 真实工程胶囊：面试估算心算清单 + 锚点速查（中英对照）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 面试中读到一个估算题后的心算顺序
# ══════════════════════════════════════════════════════════════════════
# □ 先分解：这个量能不能写成 2-5 个可独立估计因子的乘积？
# □ 再锚点：每个因子有没有一个你能背出来的量级数字？
# □ 再相乘：口算乘出点估计，先对齐单位（尤其是时间单位：秒/小时/天）
# □ 最后校验：换一条独立路径重新算一遍，两者相差在 3-5 倍内才算通过

# ══════════════════════════════════════════════════════════════════════
# B. 常背锚点（数量级，不是精确值）
# ══════════════════════════════════════════════════════════════════════
# GPU FP16 算力：V100 ~125TFLOPS，A100 ~300TFLOPS，H100 千 TFLOPS 量级
# 标注：检测框约 1000 框/人天，单价约 0.5-1 元/框
# 图像：1080p 压缩约 300KB，未压缩约 6MB
# 网络：千兆网 1Gbps=125MB/s，5G 约百 Mbps 到 1Gbps

# ══════════════════════════════════════════════════════════════════════
# C. 口播模板（中 / EN）
# ══════════════════════════════════════════════════════════════════════
# CN: 「我先把这个问题分解成三个因子，每个我给一个锚点估计，乘起来大概是这个量级，
#      我再换一条路径校验一下。」
# EN: "Let me break this into three factors, anchor each with a rough number,
#      multiply them to get a point estimate, then sanity-check with an independent path."

# ══════════════════════════════════════════════════════════════════════
# D. 与其他模块 / 课程的分工
# ══════════════════════════════════════════════════════════════════════
# · 系统设计里的完整容量估算（降级方案/监控）-> C63 模块 04，本课只给通用估算方法与锚点表
# · 长尾数据的定向采集策略 -> C58，本课「数据需求估算」只给数量级方法
'''
print(RECIPE)
for token in ['分解', '锚点', '相乘', '校验', 'C63 模块 04', 'C58']:
    assert token in RECIPE, token
print('检查单覆盖：估算心算顺序 / 常背锚点 / 中英口播 / 与其他课程的分工')"""),

    md("""### 小结

- **Fermi 估算法四步**：分解（写成因子乘积）→ 锚点（给每个因子一个量级数字）→
  相乘（对齐单位）→ 校验（换一条独立路径重算一遍）。跳过校验，等于跳过测试。
- **误差在对数域按方差可加性合成**：五个因子各自误差 2x 以内，最坏情况是 32 倍，
  但独立假设下只有约 4.7 倍——**面试里该报的是后一个数字，并说明"假设独立"**。
- **锚点数字只需要记量级和排序**（H100 > A100 > V100 的算力，检测框标注约 1000 框/人天，
  1080p 压缩图约 300KB），不需要精确到个位。
- **四类 ML 场景估算共用同一套"数量 × 单位消耗 ÷ 单位时间/容量"骨架**：
  标注（框数 ÷ 人天产出）、训练（图像总数 ÷ 吞吐）、显存（参数 × 字节数 + 激活）、
  QPS（目标 QPS ÷ 单实例 QPS）——存储和带宽也是同一个骨架的延伸。
- **达到目标召回需要多少数据，可以用幂律外推给出量级**，但更重要的是用第二条独立路径
  （比如标注预算反推）交叉校验——两条路径吻合，估计才可信。
- **三类系统性错误会让估算离谱**：隐藏常数（真实成本常是理论值的 1.5-3 倍）、
  非线性（临界点附近线性外推会系统性低估）、长尾（整体均值会被头部类别主导，稀有类必须单独估）。
- **与 C63-04 的分工**：本课是通用 Fermi 估算方法论，C63-04 是系统设计里的完整容量估算
  （含降级方案与监控），两者互补，不重复。

下一站：**模块 02 · 诊断与归因推理** —— 把"假设与验证"这一步做深，
学会用信息增益最大的策略，把"可能是数据问题"这类模糊猜测，变成可以被系统性排除的假设树。"""),
]
