# -*- coding: utf-8 -*-
"""C60 模块 03 · INT8 校准与精度恢复。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（预处理一致性）、模块 02（builder config 与精度标志）；C27（量化原理）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_int8_calibration.ipynb（纯 numpy：完整实现 TensorRT 的 KL 熵校准）'),
    ("核心参考", "Migacz «8-bit Inference with TensorRT» (GTC 2017) · Nagel et al. «A White Paper on Neural Network Quantization» · NVIDIA «Integer Quantization for DL Inference»"),
    ("预计时长", "读 90 分钟 + 跑 75 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("basics", "INT8 回顾：scale、对称性，以及为什么权重能 per-channel 而激活不能", "".join([
        P("先把地基打牢。<strong>量化就是用一个仿射映射把浮点张量塞进 8 位整数</strong>，"
          "推理时在整数域做乘加、在需要的地方再映射回浮点："),
        MATH("r \\;\\approx\\; S\\,(q - Z), \\qquad q \\;=\\; \\mathrm{clip}\\Bigl(\\mathrm{round}\\bigl(\\tfrac{r}{S}\\bigr) + Z,\\; q_{\\min},\\; q_{\\max}\\Bigr)"),
        P("$S$ 是 <span class=\"term\">scale</span>（步长），$Z$ 是 <span class=\"term\">zero-point</span>（零点偏移）。"
          "<strong>TensorRT 只用对称量化</strong>：$Z=0$，$q\\in[-127,127]$（<em>不用 $-128$，为的是让正负范围严格对称</em>），"
          "于是 $S = T/127$，其中 $T$ 就是我们要通过校准确定的<strong>阈值（threshold）</strong>。"),
        H3("对称量化的代价，以及 TensorRT 为什么还是选了它"),
        DUAL(
            "对称量化有一个显而易见的浪费：<strong>ReLU 之后的激活全是非负的，而 $[-127,-1]$ 这半边永远用不到</strong>——"
            "8 位里白白丢掉 1 位，有效精度只剩 7 位。非对称量化（带 zero-point）可以把整个 $[0,T]$ 映射到 $[-128,127]$，"
            "分辨率直接翻倍。<em>那为什么不用？</em>",
            "因为 zero-point 会在矩阵乘里制造<strong>交叉项</strong>。展开 $y=\\sum_c w_c x_c$，"
            "若 $x_c = S_x(q^x_c - Z_x)$、$w_c = S_w q^w_c$，则"
            "$y = S_wS_x\\bigl(\\sum_c q^w_c q^x_c - Z_x\\sum_c q^w_c\\bigr)$。"
            "多出来的 $Z_x\\sum_c q^w_c$ 虽然可以预计算（因为权重是常数），"
            "<em>但一旦两边都非对称，就会出现 $Z_wZ_x$ 与 $Z_w\\sum q^x$ 两项，后者依赖运行时输入、必须现算</em>。"
            "<strong>在 INT8 张量核上，这些额外的规约会打断最紧的 GEMM 内循环</strong>。"
            "TensorRT 的取舍是：宁可丢掉 ReLU 后的那 1 位，也要保住 GEMM 的峰值吞吐。"
            "<em>这也解释了为什么很多网络在 TRT 上更喜欢用 ReLU6 / Clip 这类<u>有界</u>激活，"
            "或者干脆用带负半轴的激活（LeakyReLU、SiLU）——对称量化在它们身上不浪费。</em>",
        ),
        H3("per-tensor 与 per-channel：一个可以严格推导的边界"),
        P("<strong>这是本节最值得背下来的一段，面试里能立刻显出水平。</strong>"
          "把量化后的卷积/GEMM 完整展开，看 scale 能不能提到求和号外面："),
        MATH("y_o \\;=\\; \\sum_{c,k} w_{o,c,k}\\, x_{c,k} \\;\\approx\\; \\sum_{c,k} \\bigl(S_w^{(o)} q^w_{o,c,k}\\bigr)\\bigl(S_x\\, q^x_{c,k}\\bigr) "
             "\\;=\\; \\underbrace{S_w^{(o)}\\,S_x}_{\\text{每个输出通道一个标量}} \\cdot \\underbrace{\\sum_{c,k} q^w_{o,c,k}\\,q^x_{c,k}}_{\\text{纯 INT32 累加}}"),
        P("<strong>权重的 scale 带下标 $o$（输出通道）却仍然能提出来</strong>，因为对固定的 $o$，$S_w^{(o)}$ 是一个常数，"
          "和求和变量 $c,k$ 无关——所以 <span class=\"term\">per-channel</span> 权重量化是<em>免费</em>的："
          "INT32 累加照常做，最后每个输出通道乘一个标量即可。"),
        P("但如果激活也想 per-channel，$S_x$ 就变成 $S_x^{(c)}$，它<strong>在求和号里面</strong>："),
        MATH("y_o \\;\\approx\\; S_w^{(o)} \\sum_{c} S_x^{(c)} \\sum_{k} q^w_{o,c,k}\\,q^x_{c,k} \\quad\\Longrightarrow\\quad "
             "\\text{每个 } c \\text{ 都要单独乘一次再累加，INT32 累加器废了}"),
        TABLE(["张量", "粒度", "为什么", "不这么做的后果"], [
            ["<strong>权重</strong>", "<strong>per-channel（输出通道）</strong>",
             "scale 与求和变量无关，可提到累加之外；且权重是静态的，离线算好即可",
             "per-tensor 权重在 depthwise 卷积上是灾难——各通道的动态范围可以差 10× 以上"],
            ["<strong>激活</strong>", "<strong>per-tensor</strong>",
             "per-channel scale 落在求和号内，破坏 INT32 累加；且激活在运行时才存在",
             "—（做不到，不是不想做）"],
            ["偏置", "跟随 $S_w^{(o)}S_x$，用 INT32", "偏置直接加在累加器上，尺度必须匹配", "偏置尺度错 = 系统性偏移"],
        ]),
        CALLOUT("intuition", "<p>这条推导还顺手解释了一整个研究方向。既然<strong>激活不能 per-channel、而权重可以</strong>，"
                "那面对「某些激活通道天生比别的大 10 倍」（Transformer 里普遍存在的 outlier channel）这个问题，"
                "自然的解法就是：<em>用一个对角矩阵把激活的通道差异「搬」到权重上去</em>——"
                "$y = (x\\,\\mathrm{diag}(s)^{-1})\\,(\\mathrm{diag}(s)\\,W)$，数学上完全等价，"
                "但搬完之后激活变平了（好量化），权重变陡了（无所谓，因为它可以 per-channel）。"
                "<strong>这就是 SmoothQuant 的全部思想</strong>，AWQ 是它的加权变体。"
                "<em>能把「per-channel 的可行性边界」和「SmoothQuant 为什么有效」串起来讲，是很强的信号。</em></p>",
                "从 per-channel 的边界推出 SmoothQuant"),
    ])),

    # ============================================================== 2
    ("calibration", "校准：静态的权重不需要它，动态的激活离不开它", "".join([
        P("<strong>校准（calibration）要解决的问题只有一个：每个激活张量的阈值 $T$ 该取多少。</strong>"
          "权重不需要校准——它是常数，直接取 $\\max|w|$（还能 per-channel 取）就完事了。"
          "<em>激活是输入数据的函数，你不跑数据就永远不知道它的范围</em>。这就是全部的动机。"),
        ASCII("""PTQ（训练后量化）的完整流程

  ① 拿到 FP32/FP16 模型              ② 准备**校准集**（本模块第 5 节的重点）
        │                                  │  几百到上千张，覆盖部署分布
        │                                  │  **预处理必须与线上完全一致**
        ▼                                  ▼
  ③ 在每个待量化张量上挂 observer，前向 N 个 batch
        │      收集：直方图 / running max / 分位数
        ▼
  ④ 按校准算法算出每个张量的阈值 T      ← MinMax / Percentile / **Entropy(KL)**
        │
        ▼
  ⑤ 写 calibration cache（层名 -> scale 的十六进制文本）
        │      · **可以跨硬件复用**（scale 与 GPU 型号无关）
        │      · **不能跨预处理复用**（预处理一改，激活分布就变了）
        ▼
  ⑥ builder 用这些 scale 构建 INT8 engine
        │      TRT 会决定哪些层真的用 INT8（隐式量化模式下你控制不了）
        ▼
  ⑦ **按尺寸/场景分桶评测** ← 只看整体 mAP 会漏掉小目标的塌方"""),
        H3("隐式量化 vs 显式量化：TRT 8.x 之后请优先用后者"),
        TABLE(["", "<strong>隐式量化</strong>（<code>IInt8Calibrator</code>）", "<strong>显式量化</strong>（图里带 Q/DQ 节点）"], [
            ["scale 从哪来", "TRT 在构建期跑校准算出来", "ONNX 图里就带着（来自 PTQ 工具或 QAT）"],
            ["<strong>哪些层被量化</strong>", "<strong>TRT 自己决定</strong>（按它认为划算）", "<strong>你决定</strong>——Q/DQ 放哪儿就量化到哪儿"],
            ["跨 TRT 版本稳定性", "<strong>差</strong>：版本一升，量化的层集合可能变，精度跟着变", "好：图不变，行为不变"],
            ["混合精度控制", "只能靠 <code>setPrecision</code> 事后覆盖", "自然支持：某层不插 Q/DQ 就是不量化"],
            ["与 QAT 的关系", "无关", "<strong>统一</strong>：QAT 产出的就是 Q/DQ 图"],
            ["上手成本", "低", "中（要懂 Q/DQ 放置规则）"],
        ]),
        DUAL(
            "两者的差别用一句话说清：<strong>隐式量化是「我把数据给你，你看着办」，显式量化是「我把每个量化点都写在图里，你照做」</strong>。"
            "前者省事，但你无法回答「为什么这次升级 TRT 之后 mAP 掉了 0.4」——因为量化的层集合悄悄变了。"
            "<em>量产链路上这种不可复现性是不可接受的。</em>",
            "显式量化的核心纪律是 <strong>Q/DQ 的放置规则</strong>：TensorRT 会把 <code>DQ → op → Q</code> 这个模式"
            "整体折叠成一个 INT8 算子（所谓 <em>Q/DQ propagation</em>），"
            "所以 Q/DQ 必须成对地夹住你希望跑 INT8 的算子；<strong>放错位置的后果不是「不量化」，"
            "而是「量化了但插满了 reformat」——延迟不降反升</strong>（见模块 02 第 5 节）。"
            "此外还有几条容易踩的：<em>①残差 Add 的两个输入应共用同一个 scale，否则要额外 requantize；"
            "②concat 的所有分支应共用 scale，否则 TRT 会插入转换层；"
            "③MaxPool、Relu 这类保序算子的前后可以只放一处 Q/DQ</em>。"
            "<strong>这些规则不是学术细节，它们直接决定你的 INT8 engine 到底快不快。</strong>",
        ),
        CALLOUT("warn", "<p><strong>calibration cache 的复用边界，是个很实际的问题。</strong>"
                "cache 里存的是「层名 → scale」，<em>scale 是数据的性质，不是硬件的性质</em>，"
                "所以<strong>同一份 cache 可以在 Orin-X / Orin-N / Thor 上分别重建 engine 而不用重跑校准</strong>——"
                "这在模块 02 的 engine 矩阵里能省下大量时间。</p>"
                "<p>但它<strong>与三件事强绑定</strong>，任一改变都必须重新校准："
                "<em>①预处理管线</em>（resize 插值、letterbox padding 值、归一化、通道序——改一个数值分布就变了）；"
                "<em>②模型结构与权重</em>（层名对不上就静默失效，TRT 只会 warn）；"
                "<em>③校准集本身</em>。"
                "<strong>所以 cache 必须和「预处理版本号 + 权重哈希 + 校准集版本」一起签名存档</strong>，"
                "否则半年后没人知道这份 scale 是怎么来的。</p>", "cache 能跨硬件，不能跨预处理"),
    ])),

    # ============================================================== 3
    ("algorithms", "三种校准算法：它们最小化的根本不是同一个东西", "".join([
        P("给定一个激活张量的样本分布，怎么定阈值 $T$？三种主流做法，"
          "<strong>关键在于理解它们各自在最小化什么——而且没有一个是在最小化 mAP</strong>。"),
        TABLE(["算法", "阈值怎么定", "隐含的目标函数", "对离群值", "成本", "典型适用"], [
            ["<strong>MinMax</strong>", "$T=\\max|x|$", "最小化<strong>最大</strong>误差（$\\ell_\\infty$），保证不裁剪",
             "<strong>被毁灭</strong>", "极低", "权重；有界且无长尾的张量（sigmoid/softmax 输出）；<strong>BERT 类模型的激活</strong>"],
            ["<strong>Percentile</strong>", "$T=$ 第 $p$ 分位（99.9 / 99.99）", "在「裁掉 $1-p$ 的质量」这个约束下最小化步长",
             "鲁棒，<strong>但分位点必须和离群比例匹配</strong>", "低", "快速 baseline；离群比例已知时"],
            ["<strong>Entropy / KL</strong>", "扫描候选阈值，最小化量化前后<strong>分布</strong>的 KL 散度",
             "最小化<strong>信息损失</strong>（而不是数值误差）", "鲁棒且自适应", "中（要建 2048-bin 直方图 + 扫 1920 个候选）",
             "<strong>TensorRT 的默认（CNN 检测/分类）</strong>"],
            ["MSE / MinMSE", "网格搜索 $T$ 最小化 $\\lVert x-\\hat x\\rVert^2$", "最小化 $\\ell_2$ 误差", "较鲁棒", "中",
             "<code>pytorch-quantization</code> 的可选项；对权重很好用"],
        ]),
        H3("一个具体到刺眼的数值例子"),
        P("取一个典型的 ReLU 后激活：主体是半正态分布（99% 的值 &lt; 2.6），另有 <strong>0.02% 的离群值落在 30–60</strong>"
          "（现实中它们来自过曝像素、某个特殊通道、或数值不稳定的 normalization）。notebook 会算出这张表："),
        TABLE(["算法", "阈值 $T$", "步长 $S=T/127$", "<strong>主体占多少个电平</strong>", "主体 SQNR", "有效位数 ENOB", "裁剪率"], [
            ["MinMax", "59.95", "0.472", "<strong>5.5</strong> 个（127 个里）", "17.0 dB", "<strong>2.5 bit</strong>", "0"],
            ["Percentile 99.9%", "3.34", "0.026", "98 个", "42.1 dB", "6.7 bit", "0.10%"],
            ["<strong>Percentile 99.99%</strong>", "<strong>46.3</strong>", "0.365", "7.1 个", "19.2 dB", "2.9 bit", "0.01%"],
            ["<strong>Entropy (KL)</strong>", "<strong>4.76</strong>", "0.037", "<strong>69</strong> 个", "<strong>39.0 dB</strong>", "<strong>6.2 bit</strong>", "0.02%"],
        ]),
        P("<strong>MinMax 把一个 8 位量化器变成了 2.5 位。</strong>这不是修辞——SQNR 与有效位数的换算是"
          "$\\mathrm{ENOB} = (\\mathrm{SQNR}_{\\text{dB}} - 1.76)/6.02$，17.0 dB 对应的就是 2.5 位。"
          "<em>你以为你在做 INT8，实际上主体信息只剩 2–3 位。</em>"),
        CALLOUT("danger", "<p><strong>注意表里的第三行——这是 Percentile 最阴险的坑。</strong>"
                "这个分布的离群比例是 0.02%，而 99.99% 分位切掉的是 0.01%，"
                "<em>于是分位点直接落在了离群值的population 里面</em>，算出 46.3 的阈值，结果比 99.9% 差了整整一个数量级。"
                "<strong>「分位点越高越保守」是错的——分位点必须跟你的离群比例匹配</strong>，"
                "而离群比例是逐层不同的、也是随数据变化的。<em>这正是 KL 校准的价值：它不需要你事先知道离群比例，"
                "它是从数据的形状里把截断点找出来的。</em></p>", "Percentile 选错分位点比 MinMax 还糟"),
        DUAL(
            "所以选哪个？<strong>先跑三个都跑一遍</strong>——这不是偷懒，是最省时间的做法。"
            "MinMax 和 Percentile 各只要几行代码，KL 是 TRT 默认，三个 engine 建出来在你的分桶评测集上各跑一遍，"
            "半天就能有结论，比任何先验推理都可靠。<em>然后再决定要不要往混合精度和 QAT 走。</em>",
            "但有一个 <strong>必须知道的反直觉事实</strong>，notebook 会把它算出来："
            "如果你用<strong>整个张量的 MSE / SQNR</strong> 作为评判标准，"
            "<em>MinMax 往往赢</em>（在上面的例子里 MinMax 全张量 SQNR 18.9 dB，KL 只有 6.1 dB）——"
            "因为 KL 把那 0.02% 的离群值裁掉了，而离群值的平方误差极大，直接主导了 MSE。"
            "<strong>这说明「哪个校准算法好」这个问题本身依赖于「你认为张量的哪部分信息重要」</strong>。"
            "KL 校准的立场是：<em>那 0.02% 的极值多半是噪声或饱和，把 99.98% 的主体分辨率提高十倍更划算</em>。"
            "<strong>而这个立场对不对，只能由下游任务指标回答，不能由张量级指标回答。</strong>"
            "<em>——这也是为什么本模块反复强调：校准算法的选择必须落到分桶评测上。</em>",
        ),
    ])),

    # ============================================================== 4
    ("kl", "TensorRT 的熵校准：完整算法", "".join([
        P("这是本模块技术密度最高的一节，也是面试里区分「用过」和「懂」的地方。"
          "<strong>熵校准（<code>IInt8EntropyCalibrator2</code>）的问题设定是：把 2048 个 bin 的浮点分布压成 128 个量化级，"
          "选哪个截断点能让「信息损失」最小。</strong>信息损失用 KL 散度度量："),
        MATH("D_{\\mathrm{KL}}(P \\,\\Vert\\, Q) \\;=\\; \\sum_{j} P(j)\\,\\log\\frac{P(j)}{Q(j)}"),
        P("其中 $P$ 是<strong>参考分布</strong>（截断后的真实分布），$Q$ 是<strong>候选分布</strong>"
          "（经过「量化再反量化」之后的分布）。整个算法就是在候选截断点上扫描这个量。"),
        ASCII("""① 一次全量前向，收集 |x| 的直方图：2048 个 bin，范围 [0, max|x|]
       hist[0..2047]

② for i = 128, 129, ..., 2048:                      ← 候选截断点（至少要 128 个 bin）

     (a) 构造参考分布 P（长度 i）
         P = hist[0:i]
         P[i-1] += sum(hist[i:])       ← **所有离群值并进最后一个 bin**
                                          这就是「clip 到阈值」的分布语义

     (b) 构造候选分布 Q（长度 i）—— 模拟「量化再反量化」
         · 把 [0, i) 均分成 128 组（每组 nm = i // 128 个 bin，余数并入最后一组）
         · 每组求和  ->  quantized[j]          ← 这一步是「量化」：128 个电平
         · 摊回原 bin：quantized[j] 在组内**按非零 bin 的个数均分**
                       原本是 0 的 bin 保持 0   ← 这一步是「反量化」
                       （为什么保持 0：那里本来就没数据，
                         把质量分给它们会虚假地降低 KL）
         · Q[P == 0] = 0

     (c) 归一化 P、Q（并做平滑，避免 Q 出现 0 导致 KL 发散）
     (d) divergence[i] = KL(P || Q)

③ i* = argmin divergence
④ **threshold = (i* + 0.5) * (max|x| / 2048)**,   scale = threshold / 127"""),
        H3("三个容易讲错的细节"),
        OL([
            "<strong>为什么离群值要并进最后一个 bin，而不是丢掉。</strong>因为参考分布 $P$ 要表达的是"
            "「如果我在这里截断，真实数据会变成什么样」——被截断的值不会消失，它们会被 clip 成阈值本身。"
            "<em>丢掉它们等于假装它们不存在，那 KL 就衡量不到裁剪的代价了</em>，"
            "算法会一路往小的阈值跑。",
            "<strong>为什么反量化时零 bin 要保持零。</strong>如果把组内的质量平均摊给组内<em>所有</em> bin（包括空的），"
            "$Q$ 会在原本没有数据的地方凭空长出概率质量，"
            "<em>这会让 $Q$ 的支撑集与 $P$ 不一致，KL 被人为抬高，而抬高的量与「这一组里有多少空 bin」有关</em>——"
            "那是直方图分辨率的伪影，不是量化的真实损失。",
            "<strong>为什么从 128 开始扫。</strong>候选分布只有 128 个电平，"
            "如果 $i &lt; 128$，「把 $i$ 个 bin 压成 128 个级」就不是压缩而是插值，问题失去意义。",
        ]),
        TABLE(["TensorRT calibrator", "算法", "推荐场景", "为什么"], [
            ["<strong><code>IInt8EntropyCalibrator2</code></strong>", "上面这套 KL 扫描", "<strong>CNN 分类 / 检测（默认首选）</strong>",
             "卷积激活的离群多半是噪声，裁掉换主体分辨率是划算的"],
            ["<strong><code>IInt8MinMaxCalibrator</code></strong>", "$T=\\max|x|$",
             "<strong>BERT / Transformer 类</strong>（NVIDIA 官方就是这么推荐的）",
             "<em>attention 的 softmax 输出与 LayerNorm 前后的激活，尾部携带真实信息；"
             "而且 Transformer 有结构性的 outlier channel，KL 会把它们当噪声切掉，掉点很惨</em>"],
            ["<code>IInt8LegacyCalibrator</code>", "早期版本的 KL 变体（可调 cutoff/regression）", "兼容旧流程", "一般不用"],
        ]),
        DUAL(
            "把整个算法压成一句能在面试里说的话：<strong>「TensorRT 默认用熵校准。它把激活的绝对值打成 2048 个 bin 的直方图，"
            "然后从第 128 个 bin 开始逐个试截断点：每个候选截断点下，把被截掉的质量并到最后一个 bin 得到参考分布 P，"
            "再把前 i 个 bin 压成 128 个级、按非零 bin 摊回去得到候选分布 Q，算 KL(P‖Q)；取 KL 最小的那个截断点，"
            "阈值就是 (i+0.5)×bin 宽，scale = 阈值/127。」</strong>"
            "<em>加分点：主动说明它为什么对 CNN 好而对 Transformer 不好。</em>",
            "从统计的角度看，这个算法在做的是<strong>在「量化器」这个受限的信道上最小化信息损失</strong>——"
            "$D_{\\mathrm{KL}}(P\\Vert Q)$ 恰好是「用 $Q$ 来编码服从 $P$ 的数据所付出的额外比特数」。"
            "<em>所以熵校准的立场不是「让数值误差小」，而是「让量化后的分布尽可能像量化前的分布」。</em>"
            "两者在有重尾时给出截然不同的答案：数值误差准则会保留极值（因为它们的平方误差大），"
            "信息准则会牺牲极值（因为它们的概率质量小）。<strong>值得注意的是，这个算法有几个从未被严格论证的选择："
            "2048 这个 bin 数、128 这个起点、以及「按非零 bin 均摊」这个反量化模型，都是工程经验值。</strong>"
            "<em>后续研究（AdaRound、BRECQ 等）干脆放弃了「先定阈值再量化」这个两段式框架，"
            "改成直接以「逐块输出重建误差」为目标做优化——见最后一节。</em>",
        ),
    ])),

    # ============================================================== 5
    ("calibset", "校准集的构造：整条链路上最容易做错的一步", "".join([
        P("<strong>如果 INT8 掉点了，八成问题在这一节，而不在算法。</strong>"
          "校准算法只有三四种、每种几十行代码；校准集却有无数种做错的方式，而且做错了不报错。"),
        H3("五条铁律"),
        OL([
            "<strong>预处理必须与线上完全一致，一个字节都不能差。</strong>"
            "校准时用 PIL 的 <code>BILINEAR</code>、线上用 OpenCV 的 <code>INTER_LINEAR</code>，"
            "两边的像素值就已经不同（见模块 01）；letterbox 的 padding 值取 114 还是 0、归一化是先除 255 还是先减均值——"
            "<em>每一处差异都会平移激活分布，进而平移阈值</em>。"
            "<strong>正确做法：校准脚本直接调用线上推理用的同一个预处理函数，不许重写一份。</strong>",
            "<strong>绝对不能开训练增强。</strong>Mosaic 会把四张图拼在一起、强色彩抖动会把红色禁令牌变成粉色、"
            "RandomErasing 会造出训练里才有的纯色块。<em>校准集要代表的是<u>部署分布</u>，不是训练分布。</em>"
            "开了增强的直接后果是激活范围被人为拉大 → 阈值偏大 → 有效电平被浪费。"
            "<strong>这是最常见、也最容易被忽视的一条，因为大多数人是直接复用训练 dataloader 的。</strong>",
            "<strong>必须覆盖长尾与极端场景。</strong>夜间、逆光、隧道出入口、雨雪雾、迎面车灯眩光、强反光——"
            "<em>这些场景的激活范围最大</em>。校准集里没有它们，阈值就按晴天白天定；"
            "上线遇到时激活整片超出阈值被 clip 成饱和值，特征被压平。"
            "<strong>于是最难的场景掉点最多——这个「反相关」正是它危险的原因。</strong>",
            "<strong>但也不能只放极端。</strong>全放夜间，阈值被夜间的大动态范围决定，"
            "白天正常场景的分辨率反而被稀释。<em>正确做法是<u>分层采样</u>：按部署分布的比例配额，"
            "同时给每个关键场景设一个下限（比如「隧道出口至少 30 张」），两者取较大值。</em>",
            "<strong>去重。</strong>视频数据里相邻帧几乎相同。"
            "1000 张连续帧的信息量可能还不如 50 张跨场景采样。<em>按序列采样：每个片段取 1–2 帧，而不是取一整段。</em>",
        ]),
        CALLOUT("danger", "<p><strong>「用训练集头 500 张」——这个经典错误值得单独说清楚为什么它这么容易发生。</strong>"
                "写校准脚本时最自然的一行就是 <code>for i, batch in enumerate(train_loader): if i &gt;= 500: break</code>。"
                "问题在于：<em>①数据集通常按采集时间/序列排序，头 500 张很可能来自同一次采集、同一段路、同一个天气；"
                "②它们还可能是连续帧，实际独立样本数只有十几个；"
                "③train_loader 带着完整的训练增强</em>。"
                "<strong>三个错误叠加，你得到的阈值几乎必然是「晴天白天、被 Mosaic 拉宽过」的。</strong></p>"
                "<p>notebook 里会把这个实验做出来：一个只用白天数据校准的 INT8 模型，"
                "在夜间场景上的<strong>激活裁剪率高达 49%</strong>，下游分类准确率从 0.90 掉到 <strong>0.67</strong>（掉 23 个点）；"
                "而按部署分布分层采样（白天 90% + 夜间 10%）的校准集，夜间准确率保持在 0.90。"
                "<em>——同样的模型、同样的算法、同样的 512 张图，只是选图的方式不同。</em></p>",
                "三个错误叠在一行代码里"),
        H3("TSR 场景：极值到底来自哪里"),
        DUAL(
            "交通标志有一个别的目标没有的物理特性：<strong>它们贴着反光膜（retroreflective sheeting）</strong>，"
            "设计目的就是把车灯的光原路反射回驾驶员眼睛。<em>白天它只是个普通的彩色牌子，"
            "夜间被近光灯一照，它在图像里就是一块接近饱和的高亮区域</em>。"
            "再加上夜间相机会自动提高增益和曝光时间，整张图的激活幅度都会被抬上去。"
            "<strong>所以「TSR 的激活极值主要来自夜间的反光标志本身」——恰恰是你最关心的那个目标。</strong>"
            "校准集里没有夜间数据，等于专门把你最在乎的信号裁掉。",
            "更完整的极值来源清单，可以直接当作校准集的场景配额表来用："
            "<em>①夜间反光膜 + 近光/远光灯（高亮饱和）；②隧道出入口（&gt;100 dB 的场景动态范围，"
            "ISP 的 HDR 融合会在这里产生非典型的像素统计）；③迎面车灯直射与湿路面镜面反射；"
            "④逆光（太阳低角度时标志成为剪影，激活反而异常低）；⑤雨雪造成的大面积高频噪声；"
            "⑥曝光切换的瞬间帧（自动曝光还没收敛）</em>。"
            "<strong>还有一条工程手段值得强烈推荐：在车端记录关键层的<u>裁剪率</u>（激活超过阈值的比例）并按场景标签统计。</strong>"
            "<em>如果某类场景的裁剪率显著高于校准时的水平，说明校准集缺这个场景——"
            "这是一个可以在线上直接观测、不需要标注、也不需要重新评测的早期告警信号。</em>",
        ),
        TABLE(["常见错误", "症状", "怎么发现", "修法"], [
            ["复用训练 dataloader（带增强）", "阈值系统性偏大，整体掉点但说不清哪儿", "对比开/关增强算出的阈值差异", "校准专用 loader，只做部署侧预处理"],
            ["<strong>预处理与线上不一致</strong>", "掉点，且 FP16 版本也可能有小差异", "<strong>逐张 dump 预处理后的张量做 diff（模块 01）</strong>", "共用同一个预处理函数"],
            ["只用晴天白天", "<strong>夜间/隧道场景塌方，整体 mAP 只掉一点</strong>", "<strong>按场景分桶评测</strong> + 车端裁剪率监控", "分层采样 + 每场景配额"],
            ["连续帧", "校准结果方差大，换一段视频就变", "统计独立序列数而不是帧数", "每序列取 1–2 帧"],
            ["校准集太小（&lt;100）", "阈值不稳，重跑一次就变", "跑 3 个不同随机种子看阈值离散度", "加到 500–1000"],
            ["校准集太大（&gt;5000）", "校准很慢，收益早已饱和", "画「张数 vs 指标」曲线", "取饱和点"],
        ]),
    ])),

    # ============================================================== 6
    ("sensitivity", "敏感层分析与混合精度：把掉点还回来", "".join([
        P("校准集和算法都做对了，还是掉点，怎么办？<strong>下一步是找出「是哪几层在掉点」，把它们放回 FP16。</strong>"
          "这就是敏感层分析（sensitivity analysis）+ 混合精度（mixed precision）。"),
        H3("两种扫描方向，而且它们不等价"),
        TABLE(["方向", "做法", "回答的问题", "评测次数", "何时用"], [
            ["<strong>孤立量化</strong>（isolate）", "只把第 $i$ 层量化成 INT8，其余保持 FP16", "「量化这一层要付多少代价」", "$L$ 次", "快速定位问题层"],
            ["<strong>恢复到 FP16</strong>（restore）", "全 INT8，只把第 $i$ 层放回 FP16", "「救这一层能拿回多少」", "$L$ 次",
             "<strong>更贴近最终配置，做混合精度方案时用这个</strong>"],
        ]),
        P("<strong>两者给出的排序常常不同</strong>，因为量化误差在层间是<em>相互作用</em>的："
          "第 3 层的误差可能被第 4 层放大，也可能被后面的 ReLU 或归一化吸收掉。"
          "notebook 里会构造一个 6 层的玩具网络复现这个现象——"
          "<strong>甚至会出现「把某一层从 INT8 恢复成 FP16，整体精度反而略降」的情况</strong>"
          "（误差之间部分抵消，一方消失反而暴露了另一方）。"
          "<em>这不是 bug，这是量化误差非线性传播的正常表现，也是「混合精度方案必须整体验证、不能逐层加总」的原因。</em>"),
        H3("便宜的代理指标：SQNR"),
        P("逐层扫描要跑 $2L$ 次评测。如果 $L=200$、每次评测半小时，那就是一周。"
          "实践里的做法是<strong>先用张量级代理指标粗筛，再对候选层做真评测</strong>。最常用的代理是逐层输出的 SQNR："),
        MATH("\\mathrm{SQNR}_{\\text{dB}} \\;=\\; 10\\log_{10}\\frac{\\sum_i x_i^2}{\\sum_i (x_i - \\hat x_i)^2}, "
             "\\qquad \\mathrm{ENOB} \\;=\\; \\frac{\\mathrm{SQNR}_{\\text{dB}} - 1.76}{6.02}"),
        P("同一批输入下，跑 FP32 和 INT8 两条路径，逐层比对该层输出的 SQNR（或余弦相似度）。"
          "<strong>经验阈值：SQNR &lt; 20 dB（约 3 位有效）的层值得进候选名单。</strong>"
          "代理指标与最终指标的相关性不完美（它衡量的是张量误差，不是任务误差），"
          "<em>但它便宜 $N$ 倍，用来把 200 层筛成 10 层再做真评测，是标准做法</em>。"),
        H3("典型的敏感层清单"),
        TABLE(["层类型", "为什么敏感", "处理"], [
            ["<strong>第一层卷积</strong>", "输入是原图，动态范围大且分布特殊（尤其归一化之后）；且它的误差会被整个网络放大",
             "常规做法就是<strong>保 FP16</strong>，代价很小（第一层通道少）"],
            ["<strong>检测头，尤其回归分支</strong>", "输出直接是坐标，误差直接变成像素偏移（见下一节）", "回归分支保 FP16，分类分支可以量化"],
            ["<strong>多尺度特征 concat 的前后</strong>", "<strong>P3/P4/P5 的激活范围可以差 5–10 倍，共用一个 per-tensor scale 时小的那个被压死</strong>",
             "分支各自量化后再 concat；或对齐各分支 scale（Q/DQ 显式量化下可控）"],
            ["depthwise 卷积", "各通道的动态范围差异极大", "<strong>权重必须 per-channel 量化</strong>（这条是硬要求，不是优化）"],
            ["element-wise Add（残差）", "两路输入的 scale 不同，需要 requantize；scale 差得多时小的那路被淹没", "让两路共用 scale"],
            ["attention 的 softmax / LayerNorm", "输出分布极不均匀，且尾部含信息", "保 FP16；或改用 MinMax 校准"],
            ["网络最后的分类/回归线性层", "误差无处可被后续层吸收", "视情况保 FP16"],
        ]),
        CALLOUT("warn", "<p><strong>混合精度不是「越多层放回 FP16 越好」。</strong>"
                "每一处精度切换点，TensorRT 都要插入一个 <code>Reformat</code> 层做 INT8↔FP16 转换，"
                "而 reformat 是纯访存操作。<em>把 200 层里散落的 30 层挑出来放 FP16，"
                "可能要插 50 个 reformat，最终比全 INT8 慢、比全 FP16 也快不了多少——两头不讨好。</em></p>"
                "<p><strong>正确的做法是按「连续块」划分而不是按「散点」：</strong>"
                "比如「整个 backbone 的 stem + 整个检测头」保 FP16，中间全 INT8。"
                "notebook 会把 reformat 代价放进搜索的目标函数里，"
                "你会看到<em>同样是 3 层 FP16，连续的方案比散落的方案更快</em>。"
                "<strong>这也是为什么敏感层分析的输出不应该是「一个层的列表」，而应该是「若干个连续区间」。</strong></p>",
                "散点式混合精度 = 两头不讨好"),
    ])),

    # ============================================================== 7
    ("detection", "量化对检测的特殊影响：分类头、回归头、小目标", "".join([
        P("通用的量化文献几乎都以分类任务为背景。<strong>检测有三个额外的敏感点，"
          "而它们恰好都指向 TSR 最在乎的东西。</strong>"),
        H3("① 分类头 vs 回归头：容错能力差一个数量级"),
        DUAL(
            "分类头的输出只要<strong>排序</strong>不变、阈值附近不翻转，量化误差就基本无害。"
            "而且检测器的分类 logit 分布很宽（focal loss 训出来的，绝大多数位置是强负），"
            "<em>量化噪声相对于 top-1 与 top-2 的间距通常小得多</em>。"
            "回归头就完全不同：<strong>它的输出直接是坐标，误差直接变成像素偏移</strong>，没有任何「排序容错」可言。",
            "把它量化一下就很清楚。设量化在框的每条边上引入标准差 $\\sigma$ 像素的独立误差，"
            "一个边长 $s$ 的正方形框沿对角线整体位移 $d$ 时，"
            "$\\mathrm{IoU} = (s-d)^2 / \\bigl(2s^2 - (s-d)^2\\bigr)$。代入数字："
            "<strong>$s=8$、$d=1$ 时 IoU $=49/79=0.62$；$d=2$ 时 IoU $=36/92=0.39$，直接低于 0.5 阈值判为漏检。"
            "而 $s=64$、$d=2$ 时 IoU 仍有 $0.884$。</strong>"
            "<em>同样 2 像素的量化误差，对 8×8 的目标是致命的，对 64×64 的目标几乎无感——差了 40 倍的容错度。</em>"
            "这直接推出实践结论：<strong>回归分支优先保 FP16，分类分支可以量化</strong>；"
            "如果回归用的是 DFL 这类分布式表示（输出经 softmax 后取期望），容错会好一些，因为期望值对分箱噪声不敏感。",
        ),
        H3("② 小目标为什么更敏感——三个独立原因"),
        OL([
            "<strong>IoU 对位移的敏感性</strong>（上面那笔账）：同样的坐标误差，小框的 IoU 惩罚是大框的几十倍。",
            "<strong>小目标的特征来自高分辨率浅层（P2/P3），而浅层激活的动态范围更大、离群更多</strong>"
            "（浅层还没被多层归一化「驯服」）。同一个 per-tensor scale 下，浅层被量化得更粗。",
            "<strong>小目标本身的信噪比就低</strong>（8×8 像素只有 64 个像素点的信息），"
            "量化噪声占信号的比例天然更高。",
        ]),
        CALLOUT("danger", "<p><strong>由此得到本节最重要的工程结论：INT8 之后<u>必须</u>按目标尺寸分桶评测。</strong>"
                "一个非常典型的数字组合是：<em>整体 mAP 掉 0.6，看起来完全可以接受；"
                "但拆开看是「小目标（&lt;32²）掉 3.2、中目标掉 0.5、大目标掉 0.1」</em>。"
                "<strong>整体指标把最要命的退化平均掉了。</strong></p>"
                "<p>对 TSR 这尤其致命，因为<em>TSR 几乎全是小目标</em>——"
                "一块 60 cm 的限速牌在 60 米外、1920×1080 / 60° FOV 的相机上只有约 20 像素，"
                "缩放到 640 输入后剩 7 像素。<strong>「远处标志的首次检出距离」是 TSR 最核心的产品指标之一，"
                "而它恰好是量化最先破坏的东西。</strong>"
                "<em>所以 TSR 的量化验收标准不该是「mAP 掉 &lt; 1」，而应该是「按像素尺寸分桶后，"
                "最小的那一桶掉 &lt; X」+「首次检出距离退化 &lt; Y 米」。</em></p>", "整体 mAP 会掩盖小目标塌方"),
        H3("③ 两个容易被忽略的二阶效应"),
        UL([
            "<strong>分数量化导致 NMS 排序不稳定。</strong>INT8 之后大量候选框的分数会落在同一个量化电平上，"
            "变成并列。<em>NMS 的贪心顺序依赖排序，并列时的顺序取决于实现（<code>argsort</code> 是否稳定）</em>，"
            "于是同一份输入在 Python 与 C++ 两边可能输出不同顺序的框。"
            "<strong>这通常不掉点，但会让端到端对拍失败</strong>——排查时容易被误导成「后处理写错了」（见模块 04）。",
            "<strong>多尺度 concat 的 scale 共享灾难。</strong>P3 的激活最大值可能是 2，P5 是 20。"
            "如果它们 concat 之后用一个 per-tensor scale（$T=20$），"
            "<em>P3 的全部信息被压进 127 个电平里的前 16 个，等于只剩 4 位</em>。"
            "notebook 会把这个实验做出来。<strong>解法是各分支独立量化后再 concat</strong>，"
            "这在显式 Q/DQ 图里是可控的，在隐式校准里则要靠 TRT 自己判断——这也是推荐显式量化的一个具体理由。",
        ]),
    ])),

    # ============================================================== 8
    ("qat-tree", "QAT 何时值得，与量化掉点排查决策树", "".join([
        P("先说结论：<strong>QAT 是最后一招，不是第一招。</strong>"
          "在我见过的 INT8 掉点里，绝大多数最终定位到校准集或预处理，"
          "<em>而这两类问题 QAT 一个都解决不了</em>——你只会得到一个「在错误分布上训练过的量化模型」。"),
        H3("量化掉点排查决策树"),
        ASCII("""INT8 掉点了
│
├─【第 0 步】先确认这真的是量化问题       ← **跳过这步是最常见的时间浪费**
│    · FP16 engine 的指标 == PyTorch 的指标吗？
│    · 不等 -> 这不是量化问题，是导出/预处理/后处理一致性问题（回模块 01 / 04）
│    · 评测集够大吗？同一 engine 跑两次结果一致吗？（mAP 本身有 ±0.2 的抖动）
│
├─【第 1 步】校准集         ← **命中率最高，先查这里**
│    ├ 预处理与线上完全一致？（逐张 dump 张量对拍，不要靠读代码确认）
│    ├ 关掉训练增强了吗？（Mosaic / 色彩抖动 / RandomErasing）
│    ├ 覆盖度：场景标签分布 vs 部署分布；夜间/隧道/逆光/雨雪各有多少张？
│    ├ 独立序列数是多少？（不是帧数）
│    └ 大小扫描：128 / 512 / 1024 / 2048 各跑一遍，看指标是否饱和
│
├─【第 2 步】校准算法       ← 便宜，三个都跑
│    Entropy / Percentile(99.9, 99.99, 99.999) / MinMax
│    每个建一个 engine，在**分桶评测集**上比较
│
├─【第 3 步】找到底是哪几层
│    ├ 逐层 SQNR（FP32 vs INT8 同层输出），标出 < 20 dB 的层
│    ├ 逐层扫描（恢复方向）确认 top-k 敏感层
│    └ 检查结构性问题：
│        · depthwise 是否用了 per-channel 权重量化
│        · 多尺度 concat 是否共用了一个 per-tensor scale
│        · 残差 Add 两路 scale 差多少
│        · Q/DQ 位置是否制造了大量 Reformat（看 layer info）
│
├─【第 4 步】混合精度
│    按敏感度把 top-k 层放回 FP16，**按连续块划分而不是散点**
│    画出「FP16 层数 - 精度 - 延迟」三维曲线，在延迟预算内取最优点
│
├─【第 5 步】还不行 -> QAT
│    前提：① PTQ 掉点 > 1~2 mAP  ② 混合精度救不回来或延迟代价太大
│          ③ **你有完整的训练数据与训练管线**（这常常才是真正的门槛）
│
└─【贯穿全程】每一步都按尺寸/场景分桶评测
     否则你不知道自己到底修好了什么，也不知道有没有按下葫芦浮起瓢"""),
        TABLE(["步骤", "耗时", "命中率（经验）", "为什么值这个顺序"], [
            ["0 · 确认是量化问题", "1 小时", "—（门禁）", "跳过它，后面所有工作都可能白做"],
            ["<strong>1 · 校准集</strong>", "半天", "<strong>最高</strong>", "错误最多、修复最便宜、且修好之后其他步骤的结论才可信"],
            ["2 · 换校准算法", "半天", "中", "三个 engine 而已，几乎零成本"],
            ["3 · 敏感层定位", "1–2 天", "中", "SQNR 粗筛 + 真评测细筛"],
            ["4 · 混合精度", "1–2 天", "中高", "多数情况到这一步就够了"],
            ["<strong>5 · QAT</strong>", "<strong>1–3 周</strong>", "高但昂贵", "需要训练数据、训练管线、以及导出成 TRT 认得的 Q/DQ 图"],
        ]),
        H3("QAT 到底做了什么，以及它的三个隐性要求"),
        P("<span class=\"term\">QAT</span>（Quantization-Aware Training，量化感知训练）在训练图里插入"
          "<strong>伪量化（fake quantization）</strong>节点：前向做「量化再反量化」让网络<em>感受到</em>量化误差，"
          "反向用 <span class=\"term\">STE</span>（Straight-Through Estimator，直通估计器）把 round 的零梯度替换成恒等梯度。"
          "典型配方是：<em>用 PTQ 的 scale 做初始化 → 用原学习率的 1%–10% → fine-tune 原训练轮数的 5%–10%</em>。"),
        UL([
            "<strong>要求一：BN 必须先折叠再插伪量化。</strong>部署时 BN 会被融进卷积（模块 02 第 4 节），"
            "所以 QAT 里量化的必须是<em>折叠后的权重</em>。"
            "<em>如果你在未折叠的权重上做伪量化，训练时看到的量化误差和部署时的根本不是一回事——"
            "这是 QAT 最经典的实现错误，症状是「QAT 训得好好的，导出后掉点」。</em>",
            "<strong>要求二：产物必须是 TensorRT 认得的 Q/DQ 布局。</strong>"
            "QAT 的输出是一张带 <code>QuantizeLinear</code>/<code>DequantizeLinear</code> 的 ONNX 图，"
            "<em>Q/DQ 放错位置，TRT 要么不量化、要么插满 reformat</em>。"
            "<code>pytorch-quantization</code> / TensorRT Model Optimizer 这类工具存在的意义就是保证这一点。",
            "<strong>要求三：你得有训练数据和训练管线。</strong>听起来废话，但在很多真实项目里"
            "（用了供应商模型、数据在别的团队、训练环境已经不可复现）<em>这一条直接把 QAT 判了死刑</em>。"
            "<strong>这也是 AdaRound / BRECQ 这类「只要几百张无标注数据、逐块重建」的方法价值所在</strong>——"
            "它们介于 PTQ 与 QAT 之间。",
        ]),
        CALLOUT("danger", "<p><strong>面试高频题：「INT8 掉了 3 个点，你怎么排查？」</strong>"
                "这题的评分点<em>不在你能列出多少方法，而在你的顺序对不对</em>。"
                "<strong>直接回答「上 QAT」是明确的减分项</strong>——它说明你没做过，因为做过的人知道 QAT 要一到三周，"
                "而 80% 的掉点在校准集上半天就能解决。</p>"
                "<p>满分骨架：<em>「先确认 FP16 engine 和 PyTorch 对得上，否则这不是量化问题；"
                "然后查校准集——预处理是否与线上一致、有没有误开训练增强、场景覆盖够不够、独立序列数多少；"
                "接着把三种校准算法各跑一遍；再用逐层 SQNR 粗筛出敏感层、用恢复方向的扫描确认；"
                "然后做连续块式的混合精度并画出精度-延迟曲线；"
                "只有在混合精度也救不回来、且我有训练数据和管线的前提下才上 QAT。"
                "全程按尺寸和场景分桶评测，因为整体 mAP 会把小目标的塌方平均掉。」</em></p>", "顺序比方法更重要"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>离群值是结构性的，不是偶然的。</strong>LLM.int8() 与 SmoothQuant 发现 Transformer 的激活离群"
            "集中在<em>少数固定通道</em>上，且随模型规模增大而加剧。"
            "CNN 检测器里也有类似现象（某些通道长期承担「亮度/对比度」这类全局量）。"
            "<em>开放问题：能否在训练期就抑制这种通道级离群（正则化、归一化设计），而不是事后补救？</em>",
            "<strong>更低比特与新的数值格式。</strong>FP8（E4M3 / E5M2，Hopper / Ada / Thor 原生支持）的动态范围远大于 INT8，"
            "<em>对离群值天然鲁棒，校准也简单得多（很多情况下 per-tensor MinMax 就够）</em>；"
            "代价是同等位宽下的精度密度略低。INT4 在检测任务上目前仍不成熟。"
            "<strong>「车端下一代 SoC 上是选 INT8 还是 FP8」会是未来两三年的实际选型问题。</strong>",
            "<strong>学习式舍入（learned rounding）：PTQ 的新范式。</strong>"
            "AdaRound 指出「四舍五入」并非最优——<em>逐权重地学习「向上还是向下取整」，"
            "能在不改动网络结构、只用几百张无标注数据的情况下显著缩小 PTQ 与 QAT 的差距</em>。"
            "BRECQ 把它扩展成逐块重建，QDrop 引入随机丢弃量化以提升泛化。"
            "<strong>这条线的实用价值极高，因为它绕开了 QAT 的「必须有训练管线」这个门槛。</strong>",
            "<strong>敏感度的理论化。</strong>目前的逐层扫描本质是暴力搜索。"
            "HAWQ 系列用 Hessian 的迹或最大特征值作为层敏感度的理论代理，把混合精度分配变成一个可求解的优化问题。"
            "<em>但它在检测任务上的有效性（尤其考虑到 reformat 代价与硬件约束）仍缺少系统验证。</em>",
            "<strong>校准集选择本身是一个主动学习问题。</strong>「哪 500 张图能让量化误差最小」"
            "和 C58 讲的「哪 500 张图值得标注」在形式上是同一类问题（子集选择 + 覆盖度目标），"
            "<em>但目前几乎所有实践都停留在手工分层采样。用 core-set / 嵌入聚类来选校准集，是一个成本很低、"
            "收益可能不小的方向。</em>",
            "<strong>量化模型的安全论证。</strong>如何向功能安全审查证明「INT8 模型的行为边界是已知的」？"
            "<em>目前的做法完全是统计性的（大样本上指标不降），"
            "而形式化的误差上界（给定输入范围，输出偏差不超过多少）在检测网络上做不到。</em>"
            "<strong>这是部署工程里最缺理论、也最需要理论的地方。</strong>",
            "<strong>量化-架构协同设计。</strong>与其事后救量化不友好的结构（大量 depthwise、"
            "带极端离群的 attention），不如在架构搜索阶段就把「INT8 友好度」作为目标之一。"
            "<em>这在车端尤其合理，因为部署精度是先验已知的约束，不是事后才发现的。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Migacz, <em>8-bit Inference with TensorRT</em>（NVIDIA GTC 2017）——"
                "熵校准算法的原始出处，本模块第 4 节的算法就来自这份 slides，<u>建议对着 notebook 的实现读一遍</u>。"
                "<strong>★</strong> Jacob et al., <em>Quantization and Training of Neural Networks for Efficient "
                "Integer-Arithmetic-Only Inference</em>（CVPR 2018）——定点推理的完整代数（zero-point 交叉项就出自这里）。"
                "<strong>★</strong> Nagel et al., <em>A White Paper on Neural Network Quantization</em>（Qualcomm, 2021）——"
                "目前最好的量化综述，PTQ/QAT 的决策流程写得极清楚。"
                "<strong>★</strong> Wu et al., <em>Integer Quantization for Deep Learning Inference: Principles and "
                "Empirical Evaluation</em>（NVIDIA, 2020）——per-channel、校准算法、敏感层的大规模实证对比。</p>"
                "<p>进阶：Nagel et al., <em>Up or Down? Adaptive Rounding for Post-Training Quantization</em>"
                "（AdaRound, ICML 2020）；Li et al., <em>BRECQ</em>（ICLR 2021）；Wei et al., <em>QDrop</em>（ICLR 2022）；"
                "Xiao et al., <em>SmoothQuant</em>（ICML 2023）与 Dettmers et al., <em>LLM.int8()</em>（NeurIPS 2022）——"
                "结构性离群通道；Lin et al., <em>AWQ</em>（MLSys 2024）；Dong et al., <em>HAWQ / HAWQ-V2</em>——"
                "Hessian 驱动的混合精度；Micikevicius et al., <em>FP8 Formats for Deep Learning</em>（2022）；"
                "Krishnamoorthi, <em>Quantizing deep convolutional networks: A whitepaper</em>（2018）。"
                "相邻课程：本课模块 01（预处理一致性——校准集的第一条铁律）、模块 02（builder config 与融合）、"
                "模块 04（后处理与 NMS 排序稳定性）、模块 05（延迟与 p99）；"
                "C57（小目标为什么对位移敏感）、C58（数据挖掘与分层采样）、C55 模块 05（分桶评测体系）。"
                "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · INT8 校准与精度恢复（KL 熵校准 / 校准集分布不匹配 / 敏感层与混合精度）

目标：**从零实现 TensorRT 的熵校准算法**，并用可控实验量化三件事——
不同校准算法的差别、校准集选错的代价、以及混合精度能救回多少。全程纯 numpy。

本 notebook 你会亲手实现：
1. **对称量化的基本件**：`quantize/dequantize`、SQNR、ENOB、per-tensor vs **per-channel**
2. **三种校准算法**：MinMax / Percentile / **完整的 KL 熵校准**（2048-bin 直方图、
   参考分布构造、候选分布的「量化-反量化」重建、KL 扫描）
3. 三者在含离群值分布上的对比 —— 包括一个**反直觉结论**：
   按全张量 SQNR 评判，MinMax 反而赢
4. **校准集分布不匹配实验**：只用白天数据校准 → 夜间裁剪率 50%、下游准确率 0.79 → 0.51
5. **采样策略对比**：「训练集头 500 张」 vs 随机 vs **分层采样**
6. **逐层敏感度分析**（孤立量化 / 恢复到 FP16 两个方向，并证明它们不等价）
   + **含 reformat 代价的混合精度方案搜索**
7. 检测专属：**IoU 对坐标误差的尺寸依赖**、多尺度 concat 共用 scale 的灾难

> 心智模型：**校准算法决定「保留哪部分信息」，校准集决定「哪部分信息存在」。
> 后者错了，前者再对也没用。**"""),

    md("""## 1 · 对称量化的基本件

TensorRT 的约定：对称（zero-point = 0）、有符号、$q\\in[-127,127]$、$S=T/127$。

$\\mathrm{ENOB}=(\\mathrm{SQNR}_{\\mathrm{dB}}-1.76)/6.02$ —— 把「信噪比」翻译成「实际用上了几位」。"""),

    code("""import numpy as np, math
np.set_printoptions(precision=4, suppress=True)
rng = np.random.default_rng(0)

N_LEVELS = 127          # TRT 用 [-127,127]，放弃 -128 以保证严格对称

def quantize(x, thr, n=N_LEVELS):
    \"\"\"对称量化：返回整数码 q 与 scale\"\"\"
    s = thr / n
    return np.clip(np.round(np.asarray(x) / s), -n, n), s

def quant_dequant(x, thr, n=N_LEVELS):
    q, s = quantize(x, thr, n)
    return q * s, s

def sqnr_db(x, xq):
    x = np.asarray(x, dtype=float); xq = np.asarray(xq, dtype=float)
    sig = float((x ** 2).sum()); noi = float(((x - xq) ** 2).sum())
    return 10 * math.log10(sig / max(noi, 1e-30))

def enob(sqnr):
    return (sqnr - 1.76) / 6.02

# —— 手算校验 ——
thr = 127.0                                   # 于是 scale = 1.0，量化码就是四舍五入
xq, s = quant_dequant([0.0, 1.0, 2.4, 2.6, -3.5, 200.0], thr)
print('scale =', s, ' 量化-反量化结果 =', xq)
assert s == 1.0
assert np.allclose(xq, [0., 1., 2., 3., -4., 127.])   # 200 被 clip 到 127；-3.5 银行家舍入到 -4
print()

x = np.abs(rng.normal(0, 1.0, 100000))
for t in [x.max(), 4.0, 3.0, 2.0]:
    xq, s = quant_dequant(x, t)
    d = sqnr_db(x, xq)
    print('thr=%6.3f  step=%.5f  SQNR=%6.2f dB  ENOB=%.2f bit  裁剪率=%.3f%%'
          % (t, s, d, enob(d), 100 * np.mean(x > t)))
print()
print('✅ 半正态分布上，阈值从 max 降到 3σ：SQNR 反而上升 —— 因为步长变小的收益')
print('   超过了裁掉 0.3% 尾巴的代价。**这就是所有校准算法在权衡的东西。**')"""),

    code("""# per-tensor vs per-channel：depthwise 卷积的权重是最典型的场景
C = 32
W = rng.normal(0, 1, (C, 25))                                  # 32 个通道，每通道 5x5 核
chan_gain = np.exp(rng.normal(0, 1.1, (C, 1)))                 # **通道间尺度差异极大**
W = W * chan_gain
print('各通道 max|w| 的最小/中位/最大 = %.4f / %.4f / %.4f  （相差 %.0f 倍）'
      % (np.abs(W).max(1).min(), np.median(np.abs(W).max(1)),
         np.abs(W).max(1).max(), np.abs(W).max(1).max() / np.abs(W).max(1).min()))

Wq_pt, _ = quant_dequant(W, np.abs(W).max())                   # per-tensor：一个 scale 走天下
s_pc = np.abs(W).max(axis=1, keepdims=True) / N_LEVELS         # per-channel：每个输出通道一个
Wq_pc = np.clip(np.round(W / s_pc), -N_LEVELS, N_LEVELS) * s_pc

d_pt, d_pc = sqnr_db(W, Wq_pt), sqnr_db(W, Wq_pc)
print('per-tensor  SQNR = %6.2f dB  (ENOB %.2f bit)' % (d_pt, enob(d_pt)))
print('per-channel SQNR = %6.2f dB  (ENOB %.2f bit)' % (d_pc, enob(d_pc)))
worst = int(np.argmin(np.abs(W).max(1)))
print('最弱通道（#%d）的 SQNR: per-tensor %.2f dB -> per-channel %.2f dB'
      % (worst, sqnr_db(W[worst], Wq_pt[worst]), sqnr_db(W[worst], Wq_pc[worst])))
assert d_pc > d_pt + 6, (d_pt, d_pc)
assert sqnr_db(W[worst], Wq_pc[worst]) > sqnr_db(W[worst], Wq_pt[worst]) + 10
print()
print('✅ **权重 per-channel 是免费的**（scale 与求和变量无关，可提到 INT32 累加之外），')
print('   所以它不是「优化」，是 depthwise / 分组卷积的硬要求。')
print('⚠️  而激活的 per-channel scale 落在求和号<内>，会破坏 INT32 累加 —— 做不到。')
print('   SmoothQuant 的思路正是：把激活的通道差异用对角矩阵「搬」到权重上去。')"""),

    md("""## 2 · 造一个真实感的激活分布，先跑两个便宜的算法

规则（贴近 ReLU 后的卷积激活）：
- 主体：**半正态** $|N(0,1)|$，20 万个样本
- 离群：**0.02%**（40 个）落在 30–60 —— 来自过曝像素 / 某个特殊通道 / 数值不稳定的归一化

**注意这个 0.02%：它决定了 Percentile 的分位点该怎么选。**"""),

    code("""def make_activation(n_bulk=200000, n_out=40, lo=30.0, hi=60.0, seed=0):
    r = np.random.default_rng(seed)
    bulk = np.abs(r.normal(0, 1.0, n_bulk))
    out = r.uniform(lo, hi, n_out)
    return np.concatenate([bulk, out])

def minmax_threshold(x):
    return float(np.abs(x).max())

def percentile_threshold(x, p=99.9):
    return float(np.percentile(np.abs(x), p))

def clip_rate(x, thr):
    return float(np.mean(np.abs(x) > thr))

def effective_levels(x, thr, q=99.0):
    \"\"\"主体（q 分位以内）占用了 127 个电平里的几个\"\"\"
    return float(np.percentile(np.abs(x), q) / (thr / N_LEVELS))

X = make_activation()
print('样本数 %d   max=%.2f   99%%=%.3f   99.9%%=%.3f   99.99%%=%.3f'
      % (len(X), X.max(), np.percentile(X, 99), np.percentile(X, 99.9), np.percentile(X, 99.99)))
print('离群比例 = %.4f%%  （%d 个）' % (100 * np.mean(X > 20), int((X > 20).sum())))
assert abs(np.mean(X > 20) - 40 / 200040) < 1e-6
print()
print('MinMax        阈值 %.3f' % minmax_threshold(X))
print('Percentile99.9  阈值 %.3f' % percentile_threshold(X, 99.9))
print('Percentile99.99 阈值 %.3f   <- **分位点落进了离群值里**' % percentile_threshold(X, 99.99))
assert percentile_threshold(X, 99.99) > 10 * percentile_threshold(X, 99.9)
print()
print('⚠️  离群比例是 0.02%，而 99.99% 分位切掉的是 0.01% —— 分位点直接落在离群 population 内。')
print('   **「分位点越高越保守」是错的。分位点必须跟离群比例匹配，而离群比例逐层不同。**')"""),

    md("""## 3 · 完整实现 TensorRT 的 KL 熵校准

对每个候选截断点 `i`（从 128 扫到 2048）：

1. **参考分布 P**：`P = hist[:i]`，然后 `P[i-1] += sum(hist[i:])`
   —— 被截掉的质量并进最后一个 bin，这就是「clip 到阈值」的分布语义
2. **候选分布 Q**：把 `[0,i)` 均分成 128 组求和（= 量化），
   再**按组内非零 bin 的个数**摊回去（= 反量化），**原本是 0 的 bin 保持 0**
3. 归一化 + 平滑，算 `KL(P‖Q)`

取 KL 最小的 `i*`，**threshold = (i* + 0.5) × bin 宽**。"""),

    code("""def _smooth(p, eps=1e-4):
    \"\"\"把一点点质量从非零 bin 挪给零 bin，避免 KL 因 Q 出现 0 而发散\"\"\"
    p = np.asarray(p, dtype=np.float64)
    z = (p == 0); nz = ~z
    if not nz.any():
        return None
    out = p.copy()
    out[z] = eps
    out[nz] = out[nz] - eps * z.sum() / nz.sum()
    return np.maximum(out, eps * 1e-3)          # 数值保护，防止减成负数

def quantize_hist(h, n_levels=128):
    \"\"\"把长度为 i 的直方图压成 n_levels 个电平，再摊回长度 i。
       这是熵校准里「量化-反量化」的分布版本。\"\"\"
    h = np.asarray(h, dtype=np.float64)
    i = len(h)
    nm = i // n_levels                                   # 每组多少个 bin（余数并入最后一组）
    starts = np.arange(n_levels) * nm
    sums = np.add.reduceat(h, starts)                    # 每组求和  = 量化
    nzc = np.add.reduceat((h > 0).astype(np.float64), starts)
    gid = np.repeat(np.arange(n_levels), np.diff(np.append(starts, i)))
    q = np.where(h > 0,                                  # **零 bin 保持零**
                 np.where(nzc[gid] > 0, sums[gid] / np.maximum(nzc[gid], 1.0), 0.0),
                 0.0)
    return q

def kl_divergence(p, q):
    p = np.asarray(p, dtype=np.float64); q = np.asarray(q, dtype=np.float64)
    p = p / p.sum(); q = q / q.sum()
    m = p > 0
    return float(np.sum(p[m] * np.log(p[m] / q[m])))

def entropy_threshold(x, n_bins=2048, n_levels=128, return_curve=False):
    a = np.abs(np.asarray(x).ravel())
    amax = float(a.max())
    hist, _ = np.histogram(a, bins=n_bins, range=(0.0, amax))
    hist = hist.astype(np.float64)
    best_i, best_kl, curve = n_levels, math.inf, []
    for i in range(n_levels, n_bins + 1):
        h = hist[:i]
        p = h.copy()
        p[-1] += hist[i:].sum()                          # ① 离群值并进最后一个 bin
        q = quantize_hist(h, n_levels)                   # ② 量化-反量化
        q[p == 0] = 0.0
        ps, qs = _smooth(p), _smooth(q)                  # ③ 平滑
        if ps is None or qs is None:
            continue
        kl = kl_divergence(ps, qs)
        curve.append((i, kl))
        if kl < best_kl:
            best_kl, best_i = kl, i
    thr = (best_i + 0.5) * (amax / n_bins)
    return (thr, best_i, best_kl, curve) if return_curve else thr

# —— 手算校验 quantize_hist ——
h = np.array([4, 0, 2,  0, 6, 0,  3, 3, 0,  1, 0, 0], dtype=float)   # 12 个 bin -> 4 个电平
q = quantize_hist(h, n_levels=4)
print('h =', h.astype(int))
print('q =', q)
# 组1 [4,0,2] 和=6 非零=2 -> [3,0,3]；组2 [0,6,0] 和=6 非零=1 -> [0,6,0]
# 组3 [3,3,0] 和=6 非零=2 -> [3,3,0]；组4 [1,0,0] 和=1 非零=1 -> [1,0,0]
assert np.allclose(q, [3, 0, 3, 0, 6, 0, 3, 3, 0, 1, 0, 0]), q
assert abs(q.sum() - h.sum()) < 1e-12, '总质量必须守恒'
assert np.all((h == 0) == (q == 0)), '零 bin 必须保持零'
assert abs(kl_divergence(h + 1e-9, h + 1e-9)) < 1e-12, 'KL(P||P) = 0'
print('✅ quantize_hist / kl_divergence 手算通过')"""),

    code("""# —— 三个 sanity check：算法在「没有离群」时应该几乎不裁剪 ——
u = rng.uniform(0, 1, 100000)
t_u = entropy_threshold(u)
print('均匀分布  : KL 阈值 %.4f   max %.4f   -> 比值 %.3f' % (t_u, u.max(), t_u / u.max()))
assert 0.97 < t_u / u.max() < 1.05, t_u

g = np.abs(rng.normal(0, 1, 200000))
t_g = entropy_threshold(g)
print('半正态分布: KL 阈值 %.4f   max %.4f   -> 比值 %.3f' % (t_g, g.max(), t_g / g.max()))
assert 0.85 < t_g / g.max() < 1.05, t_g
print()
print('✅ **KL 校准只在有离群时才裁剪。**干净的分布上它给出接近 max 的阈值 ——')
print('   这说明它不是「无脑收紧」，而是从分布形状里把该不该截断算出来的。')"""),

    code("""# —— 主实验：四种算法在含离群分布上的完整对比 ——
t_mm  = minmax_threshold(X)
t_p9  = percentile_threshold(X, 99.9)
t_p99 = percentile_threshold(X, 99.99)
t_kl, best_i, best_kl, curve = entropy_threshold(X, return_curve=True)
print('KL 扫描：最优 bin i* = %d / 2048，KL = %.3e，阈值 = %.4f' % (best_i, best_kl, t_kl))
print()

inl = np.abs(X) <= np.percentile(np.abs(X), 99.0)          # 「主体」= 99% 分位以内
hdr = '%-18s %8s %9s %10s %10s %9s %9s'
print(hdr % ('算法', '阈值T', '步长S', '主体电平数', '主体SQNR', 'ENOB', '裁剪率'))
res = {}
for name, t in [('MinMax', t_mm), ('Percentile 99.9', t_p9),
                ('Percentile 99.99', t_p99), ('Entropy (KL)', t_kl)]:
    xq, s = quant_dequant(X, t)
    d_all, d_in = sqnr_db(X, xq), sqnr_db(X[inl], xq[inl])
    res[name] = dict(thr=t, sqnr_all=d_all, sqnr_in=d_in,
                     lv=effective_levels(X, t), clip=clip_rate(X, t))
    print('%-18s %8.3f %9.5f %10.1f %9.2f dB %8.2f b %8.3f%%'
          % (name, t, s, effective_levels(X, t), d_in, enob(d_in), 100 * clip_rate(X, t)))

assert res['Entropy (KL)']['thr'] < res['MinMax']['thr'] / 5
assert res['Entropy (KL)']['sqnr_in'] > res['MinMax']['sqnr_in'] + 15
assert res['Entropy (KL)']['lv'] > 8 * res['MinMax']['lv']
assert res['Percentile 99.99']['sqnr_in'] < res['Percentile 99.9']['sqnr_in'] - 15
print()
print('⚠️  **MinMax 把一个 8 位量化器变成了 %.1f 位。**' % enob(res['MinMax']['sqnr_in']))
print('   主体只占 %.1f 个电平（127 个里），而 KL 让它占 %.0f 个。'
      % (res['MinMax']['lv'], res['Entropy (KL)']['lv']))
print('⚠️  Percentile 99.99 比 99.9 差了整整 %.1f dB —— 分位点选错比 MinMax 还糟。'
      % (res['Percentile 99.9']['sqnr_in'] - res['Percentile 99.99']['sqnr_in']))"""),

    code("""# —— 反直觉的一格：如果用**全张量** SQNR 评判，谁赢？——
print('%-18s %12s %12s' % ('算法', '全张量 SQNR', '主体 SQNR'))
for name in ['MinMax', 'Percentile 99.9', 'Percentile 99.99', 'Entropy (KL)']:
    r = res[name]
    print('%-18s %9.2f dB %9.2f dB' % (name, r['sqnr_all'], r['sqnr_in']))

assert res['MinMax']['sqnr_all'] > res['Entropy (KL)']['sqnr_all'] + 5
assert res['MinMax']['sqnr_in'] < res['Entropy (KL)']['sqnr_in'] - 15
print()
print('⚠️  **按全张量 SQNR，MinMax 赢；按主体 SQNR，KL 赢 20+ dB。**')
print('   原因：KL 裁掉了那 0.02% 的离群值，而离群值的平方误差极大，直接主导了全张量 MSE。')
print()
print('   这说明「哪个校准算法好」这个问题本身依赖于**你认为张量的哪部分信息重要**：')
print('   · MSE 准则会保留极值（它们的平方误差大）')
print('   · 信息（KL）准则会牺牲极值（它们的概率质量小）')
print('   **而这个立场对不对，只能由下游任务指标回答，不能由张量级指标回答。**')
print('   -> 所以校准算法的选择必须落到**分桶评测**上，这不是形式主义。')"""),

    code("""# —— 离群规模扫描：三种算法各自怎么反应 ——
print('%-12s %10s %10s %10s %10s %11s' %
      ('离群占比', '离群幅度', 'MinMax', 'P99.9', 'KL', 'KL/MinMax'))
ratios = {}
for n_out, lo, hi in [(1, 4.0, 4.01), (10, 10.0, 20.0), (40, 30.0, 60.0),
                      (200, 30.0, 60.0), (1000, 30.0, 60.0)]:
    Xo = make_activation(n_out=n_out, lo=lo, hi=hi, seed=5)
    tm, tp, tk = minmax_threshold(Xo), percentile_threshold(Xo, 99.9), entropy_threshold(Xo)
    ratios[n_out] = tk / tm
    print('%-12s %10.1f %10.3f %10.3f %10.3f %11.3f'
          % ('%.3f%%' % (100.0 * n_out / len(Xo)), hi, tm, tp, tk, tk / tm))
assert ratios[1] > 0.8, '几乎没有离群时，KL 不该裁剪'
assert ratios[40] < 0.15, '0.02% 的极端离群 -> KL 把阈值压到 MinMax 的十分之一以下'
assert ratios[1000] > 0.9, '离群占到 0.5% 时，它们已经不算离群了，KL 会保留'
print()
print('✅ 三段行为，三个结论：')
print('   · 没有离群         -> KL ≈ MinMax（它不是无脑收紧）')
print('   · 极少量极端离群   -> KL 只有 MinMax 的 %.0f%%（阈值跟着**主体**走）'
      % (100 * ratios[40]))
print('   · 离群多到 0.5%    -> KL 又回到 MinMax 附近')
print('     **因为占 0.5% 质量的东西已经不是「离群」，是分布的一部分。**')
print()
print('⚠️  顺带一个工程结论：**MinMax 的结果不可复现** —— 阈值完全由最极端的')
print('   那一个样本决定，换一批校准数据就变。KL 与 Percentile 都稳定得多。')"""),

    md("""## 4 · 校准集分布不匹配：把危害量化出来

场景：一个「特征 → 分类头」的最小检测器切片。

- **白天**：激活 `relu(M[y] + N(0,1))`，最大值约 6
- **夜间**：同样的特征，但整体乘一个 **3–12 倍的增益**
  （夜间相机自动提高 ISO 与曝光；交通标志的反光膜被车灯照射后接近饱和）
  → 最大值约 57

关键：**夜间的 float 精度和白天一样好**（正缩放不改变 argmax）。
所以接下来看到的一切掉点，**全部来自校准集选错**。"""),

    code("""D_FEAT, K_CLS = 64, 8
M_PROTO = np.abs(rng.normal(0, 1.0, (K_CLS, D_FEAT))) * 0.9      # 每类的原型向量

def gen_scene(n, kind, seed):
    r = np.random.default_rng(seed)
    y = r.integers(0, K_CLS, n)
    f = np.maximum(M_PROTO[y] + r.normal(0, 1.0, (n, D_FEAT)), 0)
    if kind == 'night':
        f = f * r.uniform(3.0, 12.0, (n, 1))       # 夜间高增益：整体放大
    elif kind == 'tunnel':
        f = f * r.uniform(4.0, 15.0, (n, 1))       # 隧道出口：更极端
    return f, y

def head_acc(f, y):
    return float((np.argmax(np.asarray(f) @ M_PROTO.T, axis=1) == y).mean())

day,   y_day   = gen_scene(4000, 'day',   1)
night, y_night = gen_scene(1000, 'night', 2)
print('白天激活 max=%.2f  99.9%%=%.2f' % (day.max(), np.percentile(day, 99.9)))
print('夜间激活 max=%.2f  99.9%%=%.2f   <- 大一个数量级' % (night.max(), np.percentile(night, 99.9)))
print('**FP 精度**：白天 %.3f   夜间 %.3f   （夜间本身没有更难）'
      % (head_acc(day, y_day), head_acc(night, y_night)))
assert abs(head_acc(day, y_day) - head_acc(night, y_night)) < 0.05
print('✅ 基线确认：夜间的困难**完全来自量化**，不来自任务本身。')"""),

    code("""CAL_SETS = {
    '❌ 只用白天 512 张':        np.concatenate([gen_scene(512, 'day', 11)[0]]),
    '✅ 白天+10%夜间（分层）':   np.concatenate([gen_scene(460, 'day', 13)[0],
                                                gen_scene(52,  'night', 14)[0]]),
    '⚠️ 只用夜间 512 张':        np.concatenate([gen_scene(512, 'night', 12)[0]]),
}
print('%-26s %8s %9s %9s %9s %9s %10s' %
      ('校准集', '阈值T', 'SQNR白天', 'SQNR夜间', 'acc白天', 'acc夜间', '夜间裁剪率'))
out = {}
for name, cal in CAL_SETS.items():
    t = percentile_threshold(cal, 99.9)
    dq, _ = quant_dequant(day, t)
    nq, _ = quant_dequant(night, t)
    out[name] = dict(thr=t, sd=sqnr_db(day, dq), sn=sqnr_db(night, nq),
                     ad=head_acc(dq, y_day), an=head_acc(nq, y_night),
                     clip=clip_rate(night, t))
    r = out[name]
    print('%-26s %8.2f %8.1fdB %8.1fdB %9.3f %9.3f %9.1f%%'
          % (name, r['thr'], r['sd'], r['sn'], r['ad'], r['an'], 100 * r['clip']))

bad, good, nite = out['❌ 只用白天 512 张'], out['✅ 白天+10%夜间（分层）'], out['⚠️ 只用夜间 512 张']
assert bad['an'] < good['an'] - 0.2, (bad['an'], good['an'])
assert bad['clip'] > 0.3, bad['clip']
assert good['ad'] > bad['ad'] - 0.02
assert bad['sd'] > good['sd'] > nite['sd'], '校准集越偏夜间，白天的分辨率被稀释得越多'
print()
print('⚠️  **只用白天校准：夜间准确率 %.3f -> %.3f（掉 %.1f 个点），裁剪率 %.0f%%。**'
      % (good['an'], bad['an'], 100 * (good['an'] - bad['an']), 100 * bad['clip']))
print('   同样的模型、同样的算法、同样的 512 张图 —— **只是选图的方式不同**。')
print()
print('⚠️  反过来「只用夜间」也有代价：白天 SQNR 从 %.1f dB 掉到 %.1f dB'
      % (bad['sd'], nite['sd']))
print('   （ENOB %.1f bit -> %.1f bit）。本例中分类头的间距够大所以准确率没塌，'
      % (enob(bad['sd']), enob(nite['sd'])))
print('   但**回归头没有这种容错**（下一节会看到）。所以要按部署分布分层，不是走极端。')"""),

    code("""# —— 采样策略：「训练集头 500 张」到底错在哪 ——
N_SEQ, FR_PER_SEQ = 500, 20                       # 500 个采集片段，每段 20 帧
SCENES = ['day', 'dusk', 'night', 'rain', 'tunnel']
SCENE_P = [0.62, 0.12, 0.14, 0.08, 0.04]          # 部署分布
r0 = np.random.default_rng(42)
seq_scene = list(r0.choice(SCENES, N_SEQ, p=SCENE_P))
for i in range(80):                               # **前 80 个片段是同一次白天采集**
    seq_scene[i] = 'day'                          #   （现实里数据集就是按采集时间排的）

GAIN = {'day': (1.0, 1.0), 'dusk': (1.6, 2.4), 'night': (3.0, 12.0),
        'rain': (1.2, 1.8), 'tunnel': (4.0, 15.0)}
frames = []
for si, sc in enumerate(seq_scene):
    rr = np.random.default_rng(1000 + si)
    lo, hi = GAIN[sc]
    g = rr.uniform(lo, hi)                        # 同一片段内增益几乎不变 -> 帧间高度冗余
    y = rr.integers(0, K_CLS, FR_PER_SEQ)
    f = np.maximum(M_PROTO[y] + rr.normal(0, 1.0, (FR_PER_SEQ, D_FEAT)), 0) * g
    for k in range(FR_PER_SEQ):
        frames.append((si, sc, f[k]))
print('数据集：%d 个片段 × %d 帧 = %d 帧' % (N_SEQ, FR_PER_SEQ, len(frames)))

def take(idx):
    return ([frames[i][0] for i in idx], [frames[i][1] for i in idx],
            np.stack([frames[i][2] for i in idx]))

rs = np.random.default_rng(9)
strategies = {}
strategies['❌ 头 500 帧'] = list(range(500))
strategies['△ 随机 500 帧'] = list(rs.choice(len(frames), 500, replace=False))
# 分层：每个场景按部署比例配额，且**保底每个场景 40 帧**，每片段最多取 1 帧
quota = {sc: max(40, int(500 * p)) for sc, p in zip(SCENES, SCENE_P)}
seq_first = {}
for i, (si, sc, _) in enumerate(frames):
    seq_first.setdefault((sc, si), i)
strat = []
for sc in SCENES:
    cand = [i for (s, _), i in seq_first.items() if s == sc]
    rs.shuffle(cand)
    strat += cand[:quota[sc]]
strategies['✅ 分层 + 每片段 1 帧'] = strat

print()
print('%-24s %7s %10s %10s %9s %9s %9s' %
      ('采样策略', '帧数', '独立片段数', '夜间+隧道占比', '阈值T', 'acc夜间', '夜间裁剪率'))
picked = {}
for name, idx in strategies.items():
    seqs, scs, feats = take(idx)
    t = percentile_threshold(feats, 99.9)
    nq, _ = quant_dequant(night, t)
    tail = np.mean([s in ('night', 'tunnel') for s in scs])
    picked[name] = dict(nseq=len(set(seqs)), tail=tail, thr=t,
                        acc=head_acc(nq, y_night), clip=clip_rate(night, t))
    p = picked[name]
    print('%-24s %7d %10d %11.1f%% %9.2f %9.3f %8.1f%%'
          % (name, len(idx), p['nseq'], 100 * tail, t, p['acc'], 100 * p['clip']))

h, rnd, st = picked['❌ 头 500 帧'], picked['△ 随机 500 帧'], picked['✅ 分层 + 每片段 1 帧']
assert h['nseq'] == 25, h['nseq']                       # 500 帧 / 20 帧每段 = 25 段
assert h['tail'] == 0.0, '头 500 帧全是白天'
assert h['acc'] < st['acc'] - 0.15
assert st['tail'] > rnd['tail'], '分层采样的尾部场景覆盖应高于随机'
assert st['nseq'] > rnd['nseq'] * 0.9
print()
print('⚠️  **「头 500 帧」的三重错误：**')
print('   ① 只有 %d 个独立片段（500 帧的信息量 ≈ 25 张图）' % h['nseq'])
print('   ② 尾部场景（夜间/隧道）覆盖率 0%% —— 阈值只有 %.2f，夜间裁剪率 %.0f%%'
      % (h['thr'], 100 * h['clip']))
print('   ③ 现实里它还带着训练增强（本实验没模拟，但那是第三个独立错误）')
print('   随机采样能解决 ①②，**分层采样还能保证稀有场景有下限配额**（隧道只占 4%，')
print('   随机 500 帧只给约 20 帧，统计上不稳）。')"""),

    md("""## 5 · 逐层敏感度分析与混合精度

造一个 6 层的玩具网络，其中 **L1 与 L3 带「离群通道」**（3 个输出通道的权重放大 28 倍，
模拟 Transformer / 深层 CNN 里常见的 outlier channel）。
激活故意用 **MinMax 校准**（最脆弱的那种），好让量化误差足够大、现象足够清楚。

两个扫描方向：
- **孤立量化**：只把第 i 层设成 INT8，其余 FP16 → 「量化这层要付多少」
- **恢复到 FP16**：全 INT8，只把第 i 层放回 FP16 → 「救这层能拿回多少」"""),

    code("""D_NET, K_NET, L_NET = 48, 10, 6
rn = np.random.default_rng(3)
NET_W = []
for i in range(L_NET):
    Wl = rn.normal(0, 1.0 / np.sqrt(D_NET), (D_NET, D_NET))
    if i in (1, 3):
        idx = rn.choice(D_NET, 3, replace=False)
        Wl[:, idx] *= 28.0                      # **离群通道**
    NET_W.append(Wl)
NET_OUT = rn.normal(0, 1.0 / np.sqrt(D_NET), (D_NET, K_NET))
XN = np.maximum(rn.normal(0, 1, (3000, D_NET)), 0)

def qw_perchannel(W, n=N_LEVELS):
    s = np.abs(W).max(axis=0, keepdims=True) / n
    return np.clip(np.round(W / s), -n, n) * s

# 校准激活阈值（MinMax）
_h, ACT_THR = XN, []
for i in range(L_NET):
    _h = np.maximum(_h @ NET_W[i], 0)
    ACT_THR.append(float(np.abs(_h).max()))
print('各层激活阈值(MinMax):', ' '.join('%.1f' % t for t in ACT_THR))

def net_forward(x, bits):
    h = x
    for i in range(L_NET):
        W = qw_perchannel(NET_W[i]) if bits[i] == 8 else NET_W[i]
        h = np.maximum(h @ W, 0)
        if bits[i] == 8:
            h, _ = quant_dequant(h, ACT_THR[i])
    return h @ NET_OUT

REF = np.argmax(net_forward(XN, [16] * L_NET), axis=1)
def net_acc(bits):
    return float((np.argmax(net_forward(XN, bits), axis=1) == REF).mean())

ACC_FP16, ACC_INT8 = net_acc([16] * L_NET), net_acc([8] * L_NET)
print('全 FP16 = %.4f   全 INT8 = %.4f   -> 掉 %.1f 个点'
      % (ACC_FP16, ACC_INT8, 100 * (ACC_FP16 - ACC_INT8)))
assert ACC_FP16 == 1.0
assert ACC_INT8 < 0.85, ACC_INT8
print()
print('%6s %14s %16s' % ('层', '孤立量化的代价', '从全INT8恢复的收益'))
iso, restore = [], []
for i in range(L_NET):
    b1 = [16] * L_NET; b1[i] = 8
    b2 = [8] * L_NET;  b2[i] = 16
    c = ACC_FP16 - net_acc(b1)
    g = net_acc(b2) - ACC_INT8
    iso.append((c, i)); restore.append((g, i))
    print('%6s %14.4f %16.4f%s' % ('L%d' % i, c, g, '   <- 恢复反而略降' if g < 0 else ''))

rank_iso = [i for _, i in sorted(iso, reverse=True)]
rank_res = [i for _, i in sorted(restore, reverse=True)]
print()
print('孤立量化排序（最敏感在前）:', ' '.join('L%d' % i for i in rank_iso))
print('恢复收益排序（最值得救在前）:', ' '.join('L%d' % i for i in rank_res))
assert rank_iso != rank_res, '两个方向给出的排序应当不同'
assert min(g for g, _ in restore) < 0.01
print()
print('⚠️  **两个方向不等价**，因为量化误差在层间相互作用：')
print('   某层的误差可能被后一层放大，也可能被后面的 ReLU 吸收，甚至与别层的误差部分抵消。')
print('   （表里出现「恢复某层反而略降」正是抵消的表现 —— 这不是 bug。）')
print('   工程结论：**做混合精度方案时用「恢复」方向的排序，它更贴近最终配置；')
print('   而且任何方案都必须整体验证，不能把逐层收益加总。**')"""),

    code("""# —— 混合精度方案搜索：把 reformat 代价放进目标函数 ——
import itertools
T_INT8, T_FP16, T_REFORMAT = 1.0, 1.9, 0.2      # ms/层，以及每个精度切换点的代价

def mp_latency(bits, t8=T_INT8, t16=T_FP16, tr=T_REFORMAT):
    t = sum(t8 if b == 8 else t16 for b in bits)
    t += tr * sum(1 for a, b in zip(bits, bits[1:]) if a != b)
    return t

# 先看一眼 reformat 为什么重要：同样 2 层 FP16，连续 vs 散落
c_cont = [16, 16, 8, 8, 8, 8]
c_scat = [16, 8, 16, 8, 8, 8]
print('连续 2 层 FP16 %s -> %.2f ms' % (c_cont, mp_latency(c_cont)))
print('散落 2 层 FP16 %s -> %.2f ms  (**贵 %.2f ms，纯粹是 reformat**)'
      % (c_scat, mp_latency(c_scat), mp_latency(c_scat) - mp_latency(c_cont)))
assert mp_latency(c_scat) > mp_latency(c_cont)

ALL = [list(c) for c in itertools.product([8, 16], repeat=L_NET)]
table = [(mp_latency(c), net_acc(c), c) for c in ALL]
print()
print('%9s %10s %10s %s' % ('延迟预算', '最优精度', '延迟', '配置(8=INT8, 16=FP16)'))
best_by_budget = {}
for budget in [6.0, 7.0, 8.0, 9.0, 12.0]:
    feas = [(a, -t, c) for t, a, c in table if t <= budget + 1e-9]
    if not feas:
        print('%9.1f %10s' % (budget, '不可行')); continue
    a, nt, c = max(feas)
    best_by_budget[budget] = (a, -nt, c)
    print('%9.1f %10.4f %10.2f %s' % (budget, a, -nt, c))

assert best_by_budget[6.0][0] == ACC_INT8            # 预算只够全 INT8
assert best_by_budget[12.0][0] == ACC_FP16           # 预算充裕 -> 全 FP16
assert best_by_budget[8.0][0] > best_by_budget[6.0][0] + 0.05

# 贪心：从全 INT8 出发，每次挑「每毫秒收益最大」的层放回 FP16
def greedy(budget):
    bits = [8] * L_NET
    while True:
        cand = []
        for i in range(L_NET):
            if bits[i] == 16:
                continue
            b = list(bits); b[i] = 16
            if mp_latency(b) > budget + 1e-9:
                continue
            gain = net_acc(b) - net_acc(bits)
            cost = mp_latency(b) - mp_latency(bits)
            cand.append((gain / max(cost, 1e-9), i))
        if not cand:
            break
        g, i = max(cand)
        if g <= 0:
            break
        bits[i] = 16
    return net_acc(bits), mp_latency(bits), bits

print()
print('%9s %12s %12s %s' % ('延迟预算', '穷举最优', '贪心结果', '贪心配置'))
for budget in [7.0, 8.0, 9.0]:
    ga, gt, gb = greedy(budget)
    print('%9.1f %12.4f %12.4f %s' % (budget, best_by_budget[budget][0], ga, gb))
    assert best_by_budget[budget][0] >= ga - 1e-12, '穷举不可能输给贪心'
print()
print('✅ 贪心通常够用，但**不保证最优** —— 因为 reformat 代价让层与层之间产生了耦合')
print('   （放回相邻的两层比放回不相邻的两层便宜），这破坏了贪心所需的可分性。')
print('   实践建议：层数少时直接穷举；层数多时按「连续区间」枚举而不是按单层枚举。')"""),

    md("""## 6 · 检测专属：回归头、小目标、以及 concat 的 scale 灾难"""),

    code("""def iou_shift(s, d):
    \"\"\"边长 s 的正方形框，沿对角线整体位移 d 后与原框的 IoU\"\"\"
    inter = max(s - d, 0.0) ** 2
    return inter / (2.0 * s * s - inter)

print('手算校验：')
print('  8x8  框位移 2px : IoU = 36/92   = %.4f  <- **已低于 0.5 阈值，判为漏检**' % iou_shift(8, 2))
print('  8x8  框位移 1px : IoU = 49/79   = %.4f' % iou_shift(8, 1))
print('  64x64框位移 2px : IoU = 3844/4348 = %.4f  <- 几乎无感' % iou_shift(64, 2))
assert abs(iou_shift(8, 2) - 36 / 92) < 1e-12
assert abs(iou_shift(64, 2) - 3844 / 4348) < 1e-12
assert iou_shift(8, 2) < 0.5 < iou_shift(64, 2)
print()

def iou_mc(s, sigma, n=40000, seed=0):
    \"\"\"四条边各加 **独立** N(0,sigma) 误差后的 IoU 分布。

    注意这与上面的 iou_shift 是**两个不同的误差模型**：
      · iou_shift(s, d)  = 整框沿对角线**整体位移** d  -> 误差单向累积，最悲观
      · iou_mc(s, sigma) = 四条边**独立**加噪         -> 约一半情况下互相抵消
    同样的数值下，独立模型温和得多（σ=1 时 8x8 还有 96%，而整体位移 1px 只剩 IoU 0.62）。
    **量化引入的坐标误差更接近独立模型**，所以估计敏感性、定容差时要用它；
    拿整体位移的直觉去套，会把危险高估一个档位。\"\"\"
    r = np.random.default_rng(seed)
    e = r.normal(0, sigma, (n, 4))
    x1, y1 = e[:, 0], e[:, 1]
    x2, y2 = s + e[:, 2], s + e[:, 3]
    iw = np.clip(np.minimum(x2, s) - np.maximum(x1, 0.0), 0, None)
    ih = np.clip(np.minimum(y2, s) - np.maximum(y1, 0.0), 0, None)
    inter = iw * ih
    ap = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    return inter / np.maximum(s * s + ap - inter, 1e-9)

SIZES = [8, 16, 32, 64, 128]
SIGMAS = [0.5, 1.0, 2.0, 3.0]
print('P(IoU >= 0.5)  —— 行=框边长(px)，列=量化引入的坐标误差 σ(px)')
print('%8s' % '边长', ''.join('%12s' % ('σ=%.2f' % g) for g in SIGMAS))
recall = {}
for s in SIZES:
    row = []
    for g in SIGMAS:
        p = float((iou_mc(s, g, seed=s * 10 + int(g * 100)) >= 0.5).mean())
        recall[(s, g)] = p; row.append(p)
    print('%8d' % s, ''.join('%11.3f ' % v for v in row))

assert recall[(8, 2.0)] < 0.60, recall[(8, 2.0)]              # 实测 ≈ 0.446
assert recall[(64, 2.0)] > 0.999, recall[(64, 2.0)]           # 实测 = 1.000
assert recall[(8, 2.0)] < recall[(64, 2.0)] - 0.30
assert recall[(8, 1.0)] < 0.999 and recall[(32, 1.0)] > 0.999
print()
print('⚠️  **同样 2 px 的坐标误差：8x8 框的召回掉到 %.1f%%，64x64 框仍是 %.1f%%。**'
      % (100 * recall[(8, 2.0)], 100 * recall[(64, 2.0)]))
print('   即便只有 1 px，8x8 也已经掉 %.1f%%，而 32x32 以上完全无感。'
      % (100 * (1 - recall[(8, 1.0)])))
print('   这就是「回归头必须优先保 FP16」的定量依据 —— 它没有任何排序容错。')
print()
print('⚠️  **别把两个误差模型混着用**：整体位移 1px 就让 8x8 的 IoU 掉到 %.3f，'
      % iou_shift(8, 1))
print('   而四边独立加噪 σ=1px 时 8x8 的召回还有 %.1f%% —— 独立误差会互相抵消。'
      % (100 * recall[(8, 1.0)]))
print('   量化引入的坐标误差接近**独立模型**；系统性偏移（letterbox 逆变换写错、')
print('   坐标系差半个像素）才是**位移模型**。定容差时用错模型会差一个档位。')"""),

    code("""# —— 分类头有多能扛？对比一下 ——
rc = np.random.default_rng(5)
scores = rc.beta(1.5, 6.0, 20000)                 # 检测器的分数分布：绝大多数很低
print('%10s %14s %16s' % ('分数噪声 σ', '过阈(0.3)翻转率', 'top-100 集合变动率'))
top100 = set(np.argsort(-scores)[:100].tolist())
for g in [0.005, 0.01, 0.03, 0.10]:
    noisy = np.clip(scores + rc.normal(0, g, scores.shape), 0, 1)
    flip = float(np.mean((scores >= 0.3) != (noisy >= 0.3)))
    t2 = set(np.argsort(-noisy)[:100].tolist())
    churn = 1 - len(top100 & t2) / 100
    print('%10.3f %13.3f%% %15.1f%%' % (g, 100 * flip, 100 * churn))
    if g == 0.03:
        flip03 = flip
        assert flip < 0.06, flip

print()
print('✅ 分类头的分数噪声 0.03（约满量程的 3%%）只造成 %.1f%% 的过阈翻转 ——' % (100 * flip03))
print('   因为它只影响**恰好落在阈值附近**的那一小撮候选，其余的排序纹丝不动；')
print('   而且翻转的都是低置信候选，对最终 AP 的影响远小于翻转率本身。')
print('⚠️  而回归头的 2 px 误差就能让 8x8 目标掉 %.0f%% 的召回。'
      % (100 * (1 - recall[(8, 2.0)])))
print('   **容错能力差一个数量级 —— 这是检测量化最重要的一条不对称。**')
print()

# —— 分尺寸汇总：整体指标怎么把小目标的塌方平均掉 ——
TSR_MIX  = {8: 0.34, 16: 0.31, 32: 0.20, 64: 0.10, 128: 0.05}   # TSR：绝大多数是小目标
COCO_MIX = {8: 0.06, 16: 0.12, 32: 0.24, 64: 0.31, 128: 0.27}   # 通用数据集
SIG = 2.0
print('%-14s %10s %10s' % ('尺寸桶', '召回', '相对无噪声'))
for s in SIZES:
    print('%-14s %10.3f %10.3f' % ('%dx%d' % (s, s), recall[(s, SIG)], recall[(s, SIG)] - 1.0))
tsr = sum(w * recall[(s, SIG)] for s, w in TSR_MIX.items())
coco = sum(w * recall[(s, SIG)] for s, w in COCO_MIX.items())
print()
print('按 TSR 尺寸分布加权的整体召回 : %.3f   （掉 %.1f 个点）' % (tsr, 100 * (1 - tsr)))
print('按 COCO 尺寸分布加权          : %.3f   （掉 %.1f 个点）' % (coco, 100 * (1 - coco)))
assert 1 - tsr > 2.5 * (1 - coco)
print()
print('⚠️  **同一个量化误差，在 COCO 上掉 %.1f 点、在 TSR 上掉 %.1f 点。**'
      % (100 * (1 - coco), 100 * (1 - tsr)))
print('   所以「别人家 INT8 只掉 0.5 mAP」这句话对 TSR 完全没有参考价值。')
print('   **TSR 的量化验收标准必须是「按像素尺寸分桶后最小的那一桶掉多少」，')
print('   外加「远处标志的首次检出距离退化多少米」。**')"""),

    code("""# —— 多尺度 concat 共用一个 per-tensor scale 的灾难 ——
rq = np.random.default_rng(17)
BRANCH = {}
for name, sc in [('P3 (stride 8)', 0.55), ('P4 (stride 16)', 1.7), ('P5 (stride 32)', 6.0)]:
    BRANCH[name] = np.abs(rq.normal(0, sc, 40000))
for k, v in BRANCH.items():
    print('%-16s max=%7.3f  99.9%%=%7.3f' % (k, v.max(), np.percentile(v, 99.9)))

cat = np.concatenate(list(BRANCH.values()))
thr_shared = percentile_threshold(cat, 99.9)
print('\\nconcat 之后的共享阈值 = %.3f  （由 P5 决定）' % thr_shared)
print()
print('%-16s %16s %16s %10s' % ('分支', '共享 scale SQNR', '各自 scale SQNR', '差距'))
gaps = {}
for k, v in BRANCH.items():
    t_own = percentile_threshold(v, 99.9)
    a, _ = quant_dequant(v, thr_shared)
    b, _ = quant_dequant(v, t_own)
    d1, d2 = sqnr_db(v, a), sqnr_db(v, b)
    gaps[k] = d2 - d1
    print('%-16s %13.2f dB %13.2f dB %8.2f dB' % (k, d1, d2, d2 - d1))

assert gaps['P3 (stride 8)'] > 15, gaps
assert gaps['P3 (stride 8)'] > gaps['P5 (stride 32)'] + 10
print()
print('⚠️  **P3 被压掉了 %.1f dB ≈ %.1f 位有效精度**（P4/P5 几乎没损失）。'
      % (gaps['P3 (stride 8)'], gaps['P3 (stride 8)'] / 6.02))
print('   而 P3 正是小目标（远处交通标志）的特征来源 —— 又一次，')
print('   **量化的伤害精准地落在了最脆弱的那一层上。**')
print()
print('   解法：各分支先各自量化再 concat（显式 Q/DQ 图里完全可控），')
print('   或者训练时就用归一化把各层级的激活范围对齐（如 FPN 后加 LayerNorm/BN）。')
print('   隐式校准模式下你只能寄希望于 TRT 自己判断 —— 这是推荐显式量化的一个具体理由。')"""),

    md("""## ✏️ 练习 1：per-channel 权重量化

实现 `per_channel_qdq(W, axis=1, n=127)`：沿 `axis` 求每个通道的 `max|w|` 作为阈值，
逐通道量化-反量化，返回与 `W` 同形状的结果。

（约定：`W` 的第 0 维是输出通道，`axis=1` 表示「对每一行单独定 scale」。）"""),

    code("""def per_channel_qdq(W, axis=1, n=127):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
# (a) 每行的最大值应被**精确**还原（它正好落在第 127 个电平上）
A = np.array([[2.0, -1.0, 0.5],
              [200.0, 100.0, -50.0]])
Aq = per_channel_qdq(A)
assert Aq.shape == A.shape
assert abs(Aq[0, 0] - 2.0) < 1e-12, Aq           # 行 0 的 max=2   -> step=2/127
assert abs(Aq[1, 0] - 200.0) < 1e-12, Aq         # 行 1 的 max=200 -> step=200/127
# 其余元素的误差不得超过半个步长（步长是**逐行**的）
step = np.abs(A).max(axis=1, keepdims=True) / 127
assert np.all(np.abs(Aq - A) <= step / 2 + 1e-9), np.abs(Aq - A) - step / 2
# 对比 per-tensor：行 0 的元素被行 1 的量级绑架
At, _ = quant_dequant(A, np.abs(A).max())
print('per-channel 行0 =', Aq[0], '  误差 %.4f' % np.abs(Aq[0] - A[0]).max())
print('per-tensor  行0 =', At[0], '  误差 %.4f' % np.abs(At[0] - A[0]).max())
assert np.abs(Aq[0] - A[0]).max() < 0.1 * np.abs(At[0] - A[0]).max()
# (b) 在通道尺度极不均衡的矩阵上，per-channel 必须显著优于 per-tensor
rq2 = np.random.default_rng(3)
Wt = rq2.normal(0, 1, (32, 25)) * np.exp(rq2.normal(0, 1.1, (32, 1)))
pt, _ = quant_dequant(Wt, np.abs(Wt).max())
pc = per_channel_qdq(Wt)
print('per-tensor  %.2f dB' % sqnr_db(Wt, pt))
print('per-channel %.2f dB' % sqnr_db(Wt, pc))
assert sqnr_db(Wt, pc) > sqnr_db(Wt, pt) + 6
# (c) 通道尺度均衡时收益变小，但 **per-channel 永不更差**
#     （每行阈值 <= 全局阈值 -> 每行步长 <= 全局步长 -> 逐元素误差不可能更大）
We = rq2.normal(0, 1, (32, 25))
e_pc = sqnr_db(We, per_channel_qdq(We))
e_pt = sqnr_db(We, quant_dequant(We, np.abs(We).max())[0])
print('通道尺度均衡时: per-tensor %.2f dB -> per-channel %.2f dB  (只赚 %.2f dB)'
      % (e_pt, e_pc, e_pc - e_pt))
assert e_pc >= e_pt - 1e-9, (e_pt, e_pc)
assert (e_pc - e_pt) < (sqnr_db(Wt, pc) - sqnr_db(Wt, pt)), '不均衡时收益应更大'
print('✅ 练习 1 通过：per-channel **永不更差**，而收益大小完全取决于通道尺度有多不均衡 ——')
print('   所以在 depthwise / 分组卷积上它是硬要求，不是可选优化。')"""),

    md("""## ✏️ 练习 2：熵校准的两个核心构造

实现：

- `reference_dist(hist, i)` → 参考分布 $P$：取 `hist[:i]`，把 `hist[i:]` 的**总质量并进最后一个 bin**
- `candidate_dist(hist, i, n_levels)` → 候选分布 $Q$：把 `hist[:i]` 均分成 `n_levels` 组
  （每组 `i // n_levels` 个 bin，**余数并入最后一组**），每组求和后**按组内非零 bin 的个数摊回去**，
  原本是 0 的 bin 保持 0

这两个函数就是 KL 校准的全部难点。"""),

    code("""def reference_dist(hist, i):
    # TODO
    raise NotImplementedError

def candidate_dist(hist, i, n_levels=128):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（全部可手算）——
hh = np.array([5, 3, 2, 1, 4], dtype=float)
P = reference_dist(hh, 3)
assert np.allclose(P, [5, 3, 2 + 1 + 4]), P          # 离群质量并进最后一个 bin
assert abs(P.sum() - hh.sum()) < 1e-12, '总质量必须守恒'
assert len(reference_dist(hh, 5)) == 5 and np.allclose(reference_dist(hh, 5), hh)

h2 = np.array([4, 0, 2, 6, 9, 9], dtype=float)
Q = candidate_dist(h2, 4, n_levels=2)                # 前 4 个 bin 压成 2 个电平
# 组1 [4,0] 和=4 非零=1 -> [4,0]；组2 [2,6] 和=8 非零=2 -> [4,4]
assert np.allclose(Q, [4, 0, 4, 4]), Q
assert abs(Q.sum() - h2[:4].sum()) < 1e-12
assert np.all((h2[:4] == 0) == (Q == 0)), '零 bin 必须保持零'

h3 = np.array([4, 0, 2, 0, 6, 0, 3, 3, 0, 1, 0, 0], dtype=float)
assert np.allclose(candidate_dist(h3, 12, 4), [3, 0, 3, 0, 6, 0, 3, 3, 0, 1, 0, 0])
# 余数并入最后一组：7 个 bin 压成 2 个电平 -> nm=3，组1=[0:3]，组2=[3:7]
h4 = np.array([2, 0, 4, 1, 1, 1, 1], dtype=float)
Q4 = candidate_dist(h4, 7, n_levels=2)
assert np.allclose(Q4, [3, 0, 3, 1, 1, 1, 1]), Q4

# 用它们复现第 3 节的 KL 扫描
hist_full, _ = np.histogram(np.abs(X), bins=2048, range=(0.0, float(np.abs(X).max())))
hist_full = hist_full.astype(float)
def kl_at(i):
    p = reference_dist(hist_full, i)
    q = candidate_dist(hist_full, i, 128)
    q = np.where(p == 0, 0.0, q)
    ps, qs = _smooth(p), _smooth(q)
    return kl_divergence(ps, qs)
assert kl_at(best_i) <= min(kl_at(best_i - 20), kl_at(best_i + 20), kl_at(2048))
print('best_i=%d  KL=%.3e   （左右各 20 个 bin 与末端的 KL 都更大）' % (best_i, kl_at(best_i)))
print('✅ 练习 2 通过：你已经把 TensorRT 默认校准算法的核心写出来了。')"""),

    md("""## ✏️ 练习 3：IoU 对坐标误差的尺寸依赖

实现：

- `iou_shift2(s, d)` → 边长 `s` 的正方形沿对角线位移 `d` 后的 IoU：
  $\\mathrm{IoU}=(s-d)^2/\\bigl(2s^2-(s-d)^2\\bigr)$（`d >= s` 时为 0）
- `min_box_size(d, target_iou=0.5)` → 使 `iou_shift2(s, d) >= target_iou` 的**最小整数** `s`（从 1 开始试）"""),

    code("""def iou_shift2(s, d):
    # TODO
    raise NotImplementedError

def min_box_size(d, target_iou=0.5):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert abs(iou_shift2(8, 0) - 1.0) < 1e-12
assert abs(iou_shift2(8, 1) - 49 / 79) < 1e-12
assert abs(iou_shift2(8, 2) - 36 / 92) < 1e-12
assert abs(iou_shift2(64, 2) - 3844 / 4348) < 1e-12
assert iou_shift2(8, 8) == 0.0 and iou_shift2(8, 20) == 0.0
assert min_box_size(0, 0.5) == 1
assert min_box_size(1, 0.5) == 6,  min_box_size(1, 0.5)     # 5:16/34=0.471 < 0.5 <= 6:25/47=0.532
assert min_box_size(2, 0.5) == 11, min_box_size(2, 0.5)     # 10:64/136=0.471 < 0.5 <= 11:81/161=0.503
assert min_box_size(2, 0.75) > min_box_size(2, 0.5)
print('%6s %14s %14s' % ('位移 d', '保住 IoU>=0.5', '保住 IoU>=0.75'))
for d in [0.5, 1, 2, 3, 4]:
    print('%6.1f %12d px %12d px' % (d, min_box_size(d, 0.5), min_box_size(d, 0.75)))
print()
print('✅ 练习 3 通过。TSR 落点：一块 60cm 的限速牌在 60m 外的 1080p/60°FOV 相机上约 20 px，')
print('   缩到 640 输入只剩 7 px。**此时 1 px 的量化误差就够把它判成漏检。**')"""),

    md("""## ✏️ 练习 4：混合精度的延迟模型与预算选型

实现：

- `mp_latency2(bits, t8=1.0, t16=1.9, tr=0.2)` → 总延迟 = 各层耗时 + **每个精度切换点** `tr`
- `best_config(cands, budget)` → `cands` 是 `[(bits, acc), ...]`，
  返回预算内精度最高的 `(bits, acc, latency)`；都不可行时返回 `None`"""),

    code("""def mp_latency2(bits, t8=1.0, t16=1.9, tr=0.2):
    # TODO
    raise NotImplementedError

def best_config(cands, budget):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测（手算）——
assert abs(mp_latency2([8, 8, 8]) - 3.0) < 1e-12
assert abs(mp_latency2([16, 16, 16]) - 5.7) < 1e-12
assert abs(mp_latency2([8, 8, 16]) - 4.1) < 1e-12      # 1+1+1.9 + 1 个切换点
assert abs(mp_latency2([8, 16, 8]) - 4.3) < 1e-12      # 1+1.9+1 + 2 个切换点
assert mp_latency2([8, 16, 8]) > mp_latency2([8, 8, 16]), '同样 1 层 FP16，夹在中间更贵'

CAND = [([8, 8, 8], 0.62), ([8, 8, 16], 0.75), ([8, 16, 8], 0.71),
        ([16, 8, 8], 0.68), ([8, 16, 16], 0.88), ([16, 16, 16], 1.00)]
b, a, t = best_config(CAND, 4.2)
assert b == [8, 8, 16] and abs(a - 0.75) < 1e-12 and abs(t - 4.1) < 1e-12, (b, a, t)
b2, a2, t2 = best_config(CAND, 5.2)
assert b2 == [8, 16, 16] and abs(t2 - 5.0) < 1e-12, (b2, a2, t2)   # 1+1.9+1.9 + 1 个切换点
assert best_config(CAND, 2.0) is None
for budget in [2.0, 3.5, 4.2, 5.2, 9.0]:
    r = best_config(CAND, budget)
    print('预算 %.1f ms -> %s' % (budget, '不可行' if r is None else
                                  '%s  acc=%.2f  lat=%.2f' % (r[0], r[1], r[2])))
print('✅ 练习 4 通过：**reformat 代价让「哪几层」比「几层」更重要** ——')
print('   同样一层 FP16，放在两端只加 1 个切换点，夹在中间要加 2 个。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def per_channel_qdq(W, axis=1, n=127):
    W = np.asarray(W, dtype=float)
    thr = np.abs(W).max(axis=axis, keepdims=True)
    s = np.where(thr > 0, thr / n, 1.0)
    return np.clip(np.round(W / s), -n, n) * s"""),

    code("""# 练习 2 参考答案
def reference_dist(hist, i):
    hist = np.asarray(hist, dtype=float)
    p = hist[:i].copy()
    p[-1] += hist[i:].sum()
    return p

def candidate_dist(hist, i, n_levels=128):
    h = np.asarray(hist, dtype=float)[:i]
    nm = i // n_levels
    starts = np.arange(n_levels) * nm
    sums = np.add.reduceat(h, starts)
    nzc = np.add.reduceat((h > 0).astype(float), starts)
    gid = np.repeat(np.arange(n_levels), np.diff(np.append(starts, i)))
    return np.where(h > 0,
                    np.where(nzc[gid] > 0, sums[gid] / np.maximum(nzc[gid], 1.0), 0.0),
                    0.0)"""),

    code("""# 练习 3 参考答案
def iou_shift2(s, d):
    inter = max(s - d, 0.0) ** 2
    return inter / (2.0 * s * s - inter)

def min_box_size(d, target_iou=0.5):
    s = 1
    while iou_shift2(s, d) < target_iou:
        s += 1
        if s > 100000:
            raise ValueError('无解')
    return s"""),

    code("""# 练习 4 参考答案
def mp_latency2(bits, t8=1.0, t16=1.9, tr=0.2):
    t = sum(t8 if b == 8 else t16 for b in bits)
    return t + tr * sum(1 for a, b in zip(bits, bits[1:]) if a != b)

def best_config(cands, budget):
    feas = [(a, -mp_latency2(b), b) for b, a in cands if mp_latency2(b) <= budget + 1e-9]
    if not feas:
        return None
    a, nt, b = max(feas)
    return b, a, -nt"""),

    md("""---
## 🧪 真实工程胶囊：校准脚本模板 + INT8 验收标准"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 校准集构造（80% 的 INT8 掉点问题在这一步，先把它做对）
# ══════════════════════════════════════════════════════════════════════
# 1) **复用线上的预处理函数，不许重写一份**
#    from deploy.preprocess import preprocess   # <- 与 C++ 端对齐过的那一份
#    禁止使用 train_loader（它带着 Mosaic / 色彩抖动 / RandomErasing）
#
# 2) 分层采样：按部署分布配额 + 每个关键场景设下限 + 每片段最多取 1~2 帧
#    QUOTA = {                      # 目标 ~800 张
#      'day_clear':   360,          # 按部署分布
#      'dusk':        100,
#      'night':       140,          # **反光膜 + 车灯 -> 激活极值的主要来源**
#      'rain_snow':    80,
#      'tunnel':       60,          # **出入口的极端动态范围，必须有配额**
#      'backlit':      60,          # 逆光
#    }
#    规则：每个片段(sequence)最多取 2 帧；同一路段同一时段最多取 N 帧
#
# 3) 自检（写成脚本，进 CI）：
#    · 独立片段数 >= 0.5 * 帧数        （防连续帧）
#    · 每个场景标签的实际张数 >= 配额的 80%
#    · **预处理指纹**：对同一张图，Python 校准链路与 C++ 部署链路的张量
#      逐元素 max|diff| < 1e-6        （模块 01 的对拍工具）
#    · 校准集里不能出现任何增强产物（拼图/纯色块/异常色相）

# ══════════════════════════════════════════════════════════════════════
# B. 算法选择：三个都跑，用分桶评测决定（各只要几十分钟）
# ══════════════════════════════════════════════════════════════════════
# TensorRT 隐式量化：
#   IInt8EntropyCalibrator2   <- CNN 检测/分类的默认首选
#   IInt8MinMaxCalibrator     <- **BERT/Transformer 类反而更好**
# 显式量化（推荐，TRT 8.x+）：用 pytorch-quantization / TensorRT Model Optimizer
#   产出带 QuantizeLinear/DequantizeLinear 的 ONNX，量化点由你决定
#
# trtexec 侧：
#   trtexec --onnx=det.onnx --int8 --fp16 --calib=calib.cache \\
#           --saveEngine=det_int8.plan --precisionConstraints=obey \\
#           --layerPrecisions=head.reg.*:fp16,backbone.stem.*:fp16
#
# calibration cache 的归档规则（缺一不可）：
#   calib.cache + {preprocess_version, weights_sha256, calibset_manifest_sha256,
#                  calibrator_type, n_images, scene_quota}
#   **cache 可以跨 GPU 型号复用；不能跨预处理复用。**

# ══════════════════════════════════════════════════════════════════════
# C. 掉点排查顺序（照这个顺序走，不要跳步）
# ══════════════════════════════════════════════════════════════════════
#  0. FP16 engine 的指标 == PyTorch 吗？不等 -> 不是量化问题（回模块 01/04）
#  1. 校准集：预处理一致？关增强了？场景覆盖？独立片段数？大小扫描 128/512/1024/2048
#  2. 校准算法：Entropy / Percentile(99.9, 99.99, 99.999) / MinMax 各建一个 engine
#  3. 逐层 SQNR（FP32 vs INT8 同层输出），标出 < 20 dB 的层；再用「恢复方向」确认
#     结构性检查：depthwise 是否 per-channel / concat 是否共用 scale /
#                 残差 Add 两路 scale 差多少 / Reformat 层数量是否异常
#  4. 混合精度：**按连续块划分**，画「FP16 层数 - 精度 - 延迟」曲线
#  5. 仍不行才上 QAT（1~3 周，且需要完整训练管线；BN 必须先折叠再插 fake-quant）

# ══════════════════════════════════════════════════════════════════════
# D. TSR 的 INT8 验收标准（不要用「整体 mAP 掉 < 1」这种口径）
# ══════════════════════════════════════════════════════════════════════
#  必须按**像素尺寸**分桶：  <16px / 16-32 / 32-64 / >64
#  必须按**场景**分桶：      day / dusk / night / rain / tunnel / backlit
#  门禁建议：
#    · 最小尺寸桶的 AP 退化   < 1.5      （整体 mAP 会把它平均掉）
#    · 每个场景桶的 AP 退化   < 1.0      （夜间/隧道是重灾区）
#    · **首次检出距离退化     < 5 m**    （TSR 的核心产品指标）
#    · 关键类别（停车让行/限速）的召回退化 < 0.5
#    · 延迟 p99 相对 FP16 的收益 > 25%   （否则不值得承担量化风险）
#  上线后监控：
#    · 车端记录关键层的**裁剪率**并按场景标签统计
#    · 某场景裁剪率显著高于校准时的水平 = 校准集缺这个场景
#      （这是不需要标注、不需要重评测的早期告警信号）
'''
print(RECIPE)
for token in ['train_loader', 'IInt8EntropyCalibrator2', 'IInt8MinMaxCalibrator',
              'precisionConstraints=obey', '独立片段数', '裁剪率',
              '首次检出距离', 'BN 必须先折叠', 'preprocess_version']:
    assert token in RECIPE, token
print('✅ 覆盖：校准集构造与自检 / 算法选择 / cache 归档 / 排查顺序 / TSR 验收门禁 / 上线监控')"""),

    md("""### 小结

- **对称量化 + per-tensor 激活 + per-channel 权重**，这不是三个独立选择，而是一条代数结论：
  权重 scale 与求和变量无关所以能提到 INT32 累加之外，激活 scale 落在求和号内所以不能。
  **SmoothQuant 正是利用这个不对称，把激活的通道差异「搬」到权重上去。**
- **MinMax 会把 8 位量化器变成 2.5 位**（本例：主体只占 127 个电平里的 5.5 个，SQNR 17 dB）。
  KL 熵校准把它救到 6.2 位。但 **Percentile 的分位点必须与离群比例匹配** ——
  本例里 99.99% 比 99.9% 差了 22.8 dB，比 MinMax 还糟。
- **KL 校准的完整算法**：2048-bin 直方图 → 从第 128 个 bin 起扫描截断点 →
  离群质量并进最后一个 bin 得参考分布 P → 压成 128 级再按非零 bin 摊回得候选分布 Q →
  取 KL 最小 → threshold = (i*+0.5)×bin 宽。**它只在有离群时才裁剪**；
  离群多到 0.5% 时它又回到 MinMax 附近，因为那已经不是离群了。
- **一个必须记住的反直觉**：按全张量 SQNR 评判 MinMax 反而赢（18.9 vs 6.1 dB），
  按主体 SQNR KL 赢 22 dB。**「哪个算法好」依赖于你认为哪部分信息重要，
  这只能由下游任务指标回答** —— 所以必须落到分桶评测。
- **校准集才是主要矛盾**。同样 512 张图、同样算法：只用白天 → 夜间裁剪率 49%、准确率掉 23 个点；
  分层采样 → 完全无损。「训练集头 500 张」叠了三个错误：只有 25 个独立片段、
  尾部场景覆盖 0%、还带着训练增强。
- **两个扫描方向不等价**（孤立量化 vs 恢复到 FP16），甚至会出现「恢复某层反而略降」——
  量化误差在层间会相互抵消。**做方案用「恢复」方向，且必须整体验证，不能逐层加总。**
  混合精度要**按连续块划分**：同样 2 层 FP16，散落比连续多付 2 个 reformat。
- **检测的特殊性**：分类头的分数噪声 0.03 只造成 ~1% 过阈翻转，
  而回归头 2 px 的误差就让 8×8 目标掉 55% 召回（64×64 几乎无感）。
  多尺度 concat 共用 per-tensor scale 会把 P3 压掉 15+ dB（约 2.6 位）—— 而 P3 正是小目标的特征来源。
  **同一个 2 px 坐标误差，按 COCO 尺寸分布掉 3.8 点召回，按 TSR 分布掉 20 点。**
- **排查顺序比方法更重要**：先确认不是一致性问题 → 校准集 → 算法 → 敏感层 →
  混合精度 → 最后才是 QAT。**直接上 QAT 是面试减分项**，因为 80% 的掉点在校准集上半天能解决。

下一站：**模块 04 · 后处理对齐与 C++ 推理管线** —— 量化会让分数出现大量并列，
NMS 的排序稳定性问题就从这里开始。"""),
]
