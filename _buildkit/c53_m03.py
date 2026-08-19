# -*- coding: utf-8 -*-
"""C53 模块 03 · RTMDet 解剖：大核、共享头与软标签。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（YOLO 演进、重参数化）与模块 02（标签分配、dynamic-k、软中心先验）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_rtmdet.ipynb（梯度回传法数值测 ERF / 软标签代价矩阵 / 缩放计算器）'),
    ("核心参考", "RTMDet (arXiv 2212.07784) · ConvNeXt · RepLKNet · CSPNet · Effective Receptive Field (NeurIPS 2016)"),
    ("预计时长", "读 70 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    ("philosophy", "设计哲学：用一套框架吃下 tiny → x 全尺度", "".join([
        P("RTMDet（Real-Time Models for object Detection，MMDetection 团队，2022）的副标题是 <em>An Empirical Study of Designing Real-Time Object Detectors</em>——<strong>它是一篇「实证研究」而不是一篇「新模块」论文</strong>。这个定位本身就是它最值得学的地方：它没有发明惊天动地的新算子，而是把 backbone / neck / head / 标签分配 / 数据增强 / 优化器<em>逐项换掉再逐项验证</em>，最后给出一套在 tiny 到 x 五档尺度上<strong>同构</strong>的配置。"),
        DUAL(
            "「同构」是什么意思、为什么重要？<strong>YOLO 系的各档模型经常不是同一个东西</strong>：v5 的 nano 和 x 用的是同一套结构但宽深不同，而 v7 的 tiny 与 v7-E6E 在结构上差别很大（辅助头、重参数化分支的用法都不同）。<em>结果是：你在 large 上调好的一个技巧，换到 tiny 上可能根本不成立</em>。RTMDet 坚持五档共用同一套 block、同一个 head、同一个分配器，<strong>只有 depth/width 两个标量在变</strong>。",
            "对工程团队来说，这个性质的价值是<strong>「一次调参，五档复用」</strong>：车端可能同时需要一个跑在主 SoC 上的 m 档模型、一个跑在备份芯片上的 tiny 档模型，还需要一个 x 档模型在云端做自动标注（伪标签教师）。<em>如果三个模型结构不同构，就要维护三套训练配方、三套导出脚本、三套精度基线</em>。RTMDet 让这三件事塌缩成一件。<strong>面试里被问「为什么选 RTMDet 而不是 YOLOv8」，「全尺度同构带来的工程收益」是一个比「AP 高 0.5」有力得多的答案。</strong>",
        ),
        ASCII("""RTMDet 的整体结构（本模块会逐块拆开）

  输入 640x640
     │
  ┌──▼───────────────────────────────────────────────┐
  │ CSPNeXt backbone                                 │  ← 第 2 节
  │   stem(3x 3x3 conv) → 4 x [下采样 + CSPLayer]     │
  │   CSPNeXtBlock = 3x3 conv + **5x5 depthwise** + 1x1  ← 第 3/4 节
  └──┬────────────┬────────────┬─────────────────────┘
     │ C3(s=8)    │ C4(s=16)   │ C5(s=32)
  ┌──▼────────────▼────────────▼─────────────────────┐
  │ CSPNeXtPAFPN（neck）：与 backbone **同一种 block**  │
  │   自顶向下 + 自底向上，全部统一到 256 通道          │
  └──┬────────────┬────────────┬─────────────────────┘
     │ P3         │ P4         │ P5
  ┌──▼────────────▼────────────▼─────────────────────┐
  │ RTMDetSepBNHead：**卷积权重跨层共享 + 每层独立 BN** │  ← 第 5 节
  │   cls 支 2x(3x3) ─┐         reg 支 2x(3x3) ─┐      │
  │   每层各自的 1x1 输出头 ←┘                  ←┘      │
  └──────────────────────────────────────────────────┘
     │
  DynamicSoftLabelAssigner（训练期）                     ← 第 6 节
  软标签分类代价 + IoU 代价 + **软中心先验 10^(d/s-3)**"""),
        CALLOUT("intuition", "读 RTMDet 论文的正确姿势：<strong>把它当成一份「消融表汇编」</strong>。它的每个设计点都配了一行 AP/延迟对照——backbone 换成 CSPNeXt、block 里加 5×5 depthwise、neck 与 backbone 用同一种 block、head 共享权重、分配器换 DSLA、训练用 AdamW + cosine + 后期关 Mosaic。<em>面试里能按「改了什么 → 收益多少 → 代价是什么」讲三到四个点，比背整个结构图有用得多。</em>"),
    ])),

    ("cspnext", "CSPNeXt：backbone 到底改了什么", "".join([
        P("<span class=\"term\">CSPNeXt</span> 这个名字直接说明了它的血统：<strong>CSP</strong>（Cross Stage Partial，来自 CSPNet / YOLOv4）+ <strong>NeXt</strong>（来自 ConvNeXt 的现代化配方）。它不是从零设计的，而是在 CSPDarknet（YOLOv5 的 backbone）上做了几处替换。"),
        TABLE(["部件", "CSPDarknet（YOLOv5）", "CSPNeXt（RTMDet）", "为什么换"], [
            ["基本 block", "两个 3×3 dense conv 的残差块", "<strong>3×3 conv + 5×5 depthwise + 1×1</strong>", "用几乎零成本的 depthwise 大核换<strong>更大的有效感受野</strong>（第 3 节详解）"],
            ["跨阶段结构", "CSP：特征分两半，一半过 block、一半直连，最后 concat", "<strong>保留 CSP</strong>", "CSP 减少约一半的 block 计算量、缓解梯度重复，是被反复验证过的结构"],
            ["neck 的 block", "与 backbone 不同（YOLOv5 的 neck 用普通 C3）", "<strong>与 backbone 完全相同</strong>", "同构 → 结构简单、缩放规则统一、部署时算子种类更少"],
            ["通道注意力", "无", "<strong>CSPLayer 末尾加 channel attention</strong>", "小模型上收益明显（弥补容量不足），大模型上收益递减"],
            ["激活", "SiLU", "SiLU", "未变——RTMDet 的消融显示激活函数不是瓶颈"],
        ]),
        DUAL(
            "<strong>「neck 与 backbone 用同一种 block」</strong>这条看起来只是省事，其实有实打实的工程收益。YOLO 系的 neck 通常是另一套结构（PAN + C3/C2f），<em>于是缩放时要为 neck 单独定一套规则、导出时要多支持一类算子、写 TensorRT plugin 时要多调一次</em>。RTMDet 直接复用 CSPNeXtBlock，<strong>整个网络只有三种基本算子：3×3 conv、5×5 depthwise conv、1×1 conv</strong>——这对车端量化与算子覆盖检查是很友好的性质（C60 会展开）。",
            "更深一层的观察：RTMDet 的论文明确指出 <strong>backbone 与 neck 的计算量分配也是一个可调的设计变量</strong>。他们发现把一部分预算从 backbone 挪到 neck（提高 neck 的通道数与 block 数），在同等延迟下 AP 更高。<em>直觉是：检测任务真正吃紧的是多尺度融合而不是语义抽取</em>——ImageNet 预训练已经把语义抽取做得不错了，而多尺度融合是检测特有的、必须从检测数据里学的部分。<strong>这个「backbone/neck 预算分配」的视角在面试里很少有人提，提出来会显得你真的读过论文而不只是看过结构图。</strong>",
        ),
        CALLOUT("warn", "一个容易被忽略的实现细节：<strong>CSPNeXtBlock 里的 depthwise 是「5×5 depthwise + 1×1 pointwise」的可分离结构，不是单独一个 5×5 depthwise</strong>。少了后面那个 1×1，通道之间就完全不通信了——depthwise 卷积<em>只在空间维度混合，不在通道维度混合</em>。<strong>「depthwise 必须配 pointwise」是一条硬规则</strong>，而下一节会看到：<em>成本几乎全在那个 1×1 上，5×5 那部分只占零头</em>。"),
    ])),

    ("erf", "5×5 depthwise 大核：有效感受野才是真的感受野", "".join([
        P("这是本模块最值得花时间的一节。<strong>「大核为什么有效」的标准答案不是「感受野更大」——那是理论感受野，而理论感受野几乎不影响精度</strong>。真正起作用的是 <span class=\"term\">effective receptive field</span>（ERF，有效感受野）。"),
        H3("① 理论感受野（TRF）：一个纯几何量"),
        P("理论感受野是「输出的一个单元，在输入上<em>可能</em>依赖的像素范围」。它由一个递推式完全决定，与权重无关："),
        MATH("r_{\\ell} \\;=\\; r_{\\ell-1} + (k_{\\ell}-1)\\cdot d_{\\ell} \\cdot j_{\\ell-1}, \\qquad j_{\\ell} = j_{\\ell-1}\\cdot s_{\\ell}, \\qquad r_0=1,\\; j_0=1"),
        P("$k$ 是核尺寸、$s$ 是 stride、$d$ 是空洞率、$j$ 是累计 stride（jump）。<strong>堆 $N$ 层 3×3（stride 1）的 TRF 半径是 $N$；堆 $N$ 层 5×5 的 TRF 半径是 $2N$。</strong> 简单、干净、也<em>基本没用</em>——因为它假设了「范围内的每个像素都同等重要」，而这个假设是错的。"),
        H3("② 有效感受野（ERF）：一个统计量"),
        P("Luo et al. (NeurIPS 2016) 的关键观察：<strong>把中心输出单元对输入的梯度画出来，得到的不是一个均匀的方块，而是一个近似高斯的钟形</strong>。中心像素的贡献远大于边缘像素，边缘的贡献几乎为零。这个梯度图的「有效宽度」才是模型真正看得见的范围。"),
        DUAL(
            "为什么会是高斯？<strong>因为卷积的堆叠就是概率分布的卷积</strong>。把每层卷积核归一化后看成一个概率分布（每个位置的权重 = 「信息从这里来」的概率），堆 $N$ 层就是这个分布自己卷自己 $N$ 次。<em>中心极限定理直接给出结论：$N$ 大时结果趋于高斯，方差是单层方差的 $N$ 倍</em>。于是 ERF 的<strong>标准差</strong>按 $\\sqrt{N}$ 增长，而 TRF 的半径按 $N$ 增长。",
            "这就得到了本节最重要的一个式子：对宽度为 $k$ 的均匀核，单层的空间方差是 $(k^2-1)/12$（离散均匀分布的方差），堆 $N$ 层后 $\\sigma_{ERF} = \\sqrt{N(k^2-1)/12}$。<strong>而 TRF 半径 $= N(k-1)/2$。两者之比按 $1/\\sqrt{N}$ 衰减</strong>：<em>网络越深，模型「名义上看得见」和「实际上用得上」的差距就越大</em>。notebook 里会用梯度回传法把这个式子逐项数值验证到小数点后六位——<strong>这不是近似关系，在均匀核线性网络下它是精确成立的等式。</strong>",
        ),
        MATH("\\sigma_{ERF} \\;=\\; \\sqrt{\\;\\sum_{\\ell=1}^{N} \\frac{d_{\\ell}^2\\,(k_{\\ell}^2-1)}{12}\\;} \\;\\;\\xrightarrow[\\;\\text{同核}\\;]{}\\;\\; \\sqrt{\\frac{N(k^2-1)}{12}}, \\qquad \\frac{\\sigma_{ERF}}{r_{TRF}} = \\frac{2}{k-1}\\sqrt{\\frac{k^2-1}{12N}}"),
        TABLE(["配置", "TRF 半径", "ERF 标准差（实测＝理论）", "ERF/TRF", "结论"], [
            ["3×3 × 10 层", "10", "2.582", "<strong>0.258</strong>", "名义看 21×21，实际只用得上中间 ~5×5"],
            ["5×5 × 10 层", "20", "4.472", "0.224", "TRF 翻倍，ERF 只涨 √3 ≈ 1.73 倍"],
            ["7×7 × 10 层", "30", "6.325", "0.211", "继续加大核，ERF/TRF 继续下降"],
            ["3×3 × 64 层", "64", "6.532", "<strong>0.102</strong>", "<em>深网络的 TRF 早就覆盖全图，但 ERF 只有十几个像素</em>"],
        ]),
        H3("③ 于是 5×5 depthwise 的价值就清楚了"),
        P("两个 3×3 与一个 5×5 的 <strong>TRF 完全相同</strong>（半径都是 2），但 ERF 不同：$\\sigma_{2\\times3\\times3} = \\sqrt{2\\cdot 8/12} = 1.155$，$\\sigma_{1\\times5\\times5} = \\sqrt{24/12} = 1.414$，<strong>比值 $\\sqrt{1.5} = 1.2247$</strong>。也就是说——<em>用一层 5×5 换掉两层 3×3，TRF 不变、深度减半、ERF 反而大了 22.5%</em>。"),
        CALLOUT("intuition", "把「大核为什么有效」压缩成一句面试可用的话：<strong>「堆小核只能让理论感受野线性增长，而有效感受野按 $\\sqrt{N}$ 增长——增大单层核尺寸是<em>直接</em>把每一步的方差做大，这比多堆几层划算得多，而且不增加深度（不增加串行延迟、不加重梯度传播负担）。」</strong> <em>能同时说出「TRF 线性、ERF 根号」和「深度是串行延迟」这两点，就已经比绝大多数候选人讲得深了。</em>"),
        CALLOUT("warn", "ERF 还有两个必须知道的修正：<strong>① ReLU 让 ERF 进一步缩小</strong>——门控会随机切断梯度路径，notebook 里会看到激活门控（保留概率 0.3）把「有效面积」从 205 压到 52（缩小 4 倍），而梯度总质量掉了 4 个数量级；<strong>② ERF 是训练出来的，不是固定的</strong>——Luo 的论文指出训练后的 ERF 会显著大于随机初始化时的 ERF。<em>所以「ERF 不够大」有时是训练不充分的症状，不一定是结构问题。</em>"),
    ])),

    ("cost", "成本账：为什么 5×5 几乎免费，又为什么不是 11×11", "".join([
        P("如果大核这么好，为什么不直接上 11×11？答案分两层：<strong>参数量的账说「上」，硬件的账说「停」</strong>。"),
        H3("① 参数量：depthwise 让核尺寸变成零头"),
        MATH("\\text{params}_{\\text{dense }k\\times k} = k^2 C^2, \\qquad \\text{params}_{\\text{DW }k\\times k + \\text{PW}} = k^2 C + C^2 = C^2\\left(1 + \\frac{k^2}{C}\\right)"),
        TABLE(["通道数 C", "5×5 depthwise", "两层 3×3 dense", "倍数", "5×5 DW 占「DW+PW」总量的比例"], [
            ["64", "1,600", "73,728", "46×", "1600 / (1600+4096) = <strong>28%</strong>"],
            ["128", "3,200", "294,912", "92×", "3200 / (3200+16384) = <strong>16%</strong>"],
            ["256", "6,400", "1,179,648", "<strong>184×</strong>", "6400 / (6400+65536) = <strong>8.9%</strong>"],
            ["512", "12,800", "4,718,592", "369×", "12800 / (12800+262144) = <strong>4.7%</strong>"],
        ]),
        DUAL(
            "最后一列是关键：<strong>在可分离结构里，成本几乎全在 1×1 pointwise 上，空间核只占零头</strong>。C=256 时把 block 里的 3×3 depthwise 换成 5×5 depthwise，整个 block 的参数只涨 <code>(6400-2304)/67840 ≈ 6.0%</code>。<em>这就是「5×5 depthwise 几乎免费」的准确含义——不是绝对免费，而是相对于同一个 block 里那个 1×1，它便宜到可以忽略。</em>",
            "notebook 里会做一个更有意思的实验：<strong>固定参数预算，问「买哪个核尺寸能得到最大的 ERF」</strong>。C=256、预算 200 万参数时，答案是 <em>核越大越好</em>——k=3 能堆 29 层得到 $\\sigma=4.40$，k=11 只能堆 20 层但 $\\sigma=14.14$，<strong>相差 3.2 倍</strong>。纯参数量视角下，大核是压倒性的。<em>所以「为什么 RTMDet 停在 5×5」这个问题，答案一定不在参数量里。</em>",
        ),
        H3("② 硬件：depthwise 卷积是访存受限的"),
        P("算一笔 <span class=\"term\">arithmetic intensity</span>（算术强度，MAC 数 ÷ 访存元素数）："),
        UL([
            "<strong>Dense 3×3</strong>（C=256）：MACs $= 9C^2HW$，访存 $\\approx 2CHW$，强度 $\\approx 9C/2 = 1152$ —— 妥妥的<em>计算受限</em>，GPU 跑得飞快。",
            "<strong>Depthwise $k\\times k$</strong>：MACs $= k^2CHW$，访存 $\\approx 2CHW$，强度 $\\approx k^2/2$。$k=3$ 时是 4.5，$k=5$ 时是 12.5 —— <strong>比 dense 低两个数量级，是彻底的<em>访存受限</em></strong>。",
            "<strong>推论</strong>：depthwise 层的墙钟时间主要由「读一遍输入、写一遍输出」决定，<em>而这部分与 $k$ 无关</em>。所以 3×3→5×5 的延迟增量非常小；但 $k$ 继续增大到 9/11 时，权重驻留、寄存器压力、以及 cuDNN/TensorRT 对大 depthwise 核的 kernel 优化不足开始显现，<strong>延迟会非线性地跳上去</strong>。",
        ]),
        CALLOUT("danger", "这是一个<strong>「FLOPs 骗人」的经典案例</strong>，面试里出现频率很高：<em>depthwise 卷积的 FLOPs 极低，但实测延迟远高于 FLOPs 预测</em>。MobileNet 系在 GPU 上「FLOPs 只有 ResNet 的 1/10，实测只快 2 倍」就是这个原因。<strong>正确的说法是：FLOPs 是计算受限算子的良好代理，对访存受限算子完全失效。</strong> 讲 RTMDet 的大核时如果只说「参数几乎不涨」而不提访存，会被追问到；<em>主动说出「所以 RTMDet 停在 5×5 是硬件约束而不是精度约束」，是很强的加分项。</em>"),
        P("RTMDet 论文的消融给出的结论与这个分析一致：<strong>3×3 → 5×5 带来明确的 AP 提升且延迟几乎不变，而 5×5 → 7×7 精度收益消失、延迟开始上升</strong>。<em>5×5 是精度-延迟曲线的拐点，不是一个拍脑袋的数字。</em>"),
    ])),

    ("head", "颈部与检测头：共享权重 + 每层独立 BN", "".join([
        P("<span class=\"term\">RTMDetSepBNHead</span> 的名字里 <code>SepBN</code> 就是它的全部设计：<strong>卷积权重在 FPN 各层之间共享，但 BatchNorm 的统计量每层各自独立</strong>。这个组合看起来是个小 trick，实际上解决了一个真问题。"),
        ASCII("""三种检测头设计的对比（feat=256, stacked_convs=2, 3 层 FPN, 80 类）

  ① 每层独立头（RetinaNet 早期 / 部分 YOLO 实现）
     P3 ──► [conv3x3, conv3x3] ──► 1x1 out      各层参数完全独立
     P4 ──► [conv3x3, conv3x3] ──► 1x1 out      主体 = 3 x 2 x 2 x 590K
     P5 ──► [conv3x3, conv3x3] ──► 1x1 out      含输出头共 ≈ **7.15 M**

  ② 全共享头（RetinaNet 原版：conv 与 BN 全共享）
     P3 ─┐                                      共 ≈ **2.43 M**（省 2.95 倍）
     P4 ─┼► [同一套 conv3x3, conv3x3] ──► 1x1    但 **BN 统计量被三层的特征混着算**
     P5 ─┘                                      而三层的特征尺度差异极大 ✗

  ③ 共享 conv + 每层独立 BN（RTMDet）
     P3 ─┐                             ┌─ BN_P3 ─┐
     P4 ─┼► [同一套 conv3x3 权重] ──────┼─ BN_P4 ─┼──► 每层各自的 1x1 out
     P5 ─┘                             └─ BN_P5 ─┘
     共 ≈ **2.43 M**  ← 只比全共享多 4,096 个参数（BN 从 2,048 变成 6,144）
     既拿到共享的正则化收益，又不让三层的统计量互相污染 ✅

  （以上按 feat=256 / stacked_convs=2 / 3 层 FPN / 80 类，含每层的 1x1 输出头）"""),
        DUAL(
            "为什么 BN 不能共享？<strong>因为 FPN 三层的特征分布根本不是一个量级</strong>。P3（stride 8）是高分辨率、低语义、激活幅值小；P5（stride 32）是低分辨率、高语义、激活幅值大。<em>用一套 BN 统计量去归一化它们，等价于用同一个均值方差去标准化三组分布差很远的数据</em>——结果是三层都没被正确归一化，且推理时 running stats 会偏向格点数最多的那一层（P3 的格点数是 P5 的 16 倍）。",
            "而卷积权重<strong>应该</strong>共享，原因也很清楚：<em>「什么样的局部纹理是交通标志」这件事在三个尺度上是同一个函数</em>，只是输入的尺度不同。共享权重让三层的梯度汇到同一套参数上，<strong>等价于把训练样本量乘了 3</strong>——这对小目标层（P3 的正样本本来就少）是实打实的收益。notebook 里会用合成特征验证：共享 BN 下某一层归一化后的均值可以偏离 0 达到 1 个标准差以上，而每层独立 BN 下三层都精确落在 (0, 1)。",
        ),
        TABLE(["方案", "参数量", "正则化效果", "多尺度统计", "部署影响"], [
            ["每层独立头", "7.15 M", "弱（各层各学各的）", "各层正确", "权重多，engine 更大"],
            ["全共享（含 BN）", "2.43 M", "<strong>强</strong>", "<strong>✗ 被污染</strong>（P5 归一化后均值偏离 +1.63）", "最省"],
            ["<strong>共享 conv + 独立 BN</strong>", "<strong>2.43 M</strong>（只多 4,096 个参数）", "<strong>强</strong>", "<strong>✓ 各层精确落在 (0, 1)</strong>", "省；且 BN 可与 conv 折叠"],
        ]),
        CALLOUT("intuition", "有一个很漂亮的部署副产品：<strong>推理时 BN 会被折叠进卷积（Conv+BN fusion），于是「共享 conv + 每层独立 BN」在导出后就变成了「每层一套独立的 conv 权重」</strong>——<em>训练时享受共享带来的正则化与样本量放大，推理时又不承担任何额外开销</em>。这与模块 01 讲的结构重参数化是同一类思想：<strong>训练态与推理态可以是两个不同的结构，只要数值等价。</strong>"),
        CALLOUT("warn", "落到 TSR 上有个直接后果：<strong>共享头意味着「远处 12px 的标志」和「近处 96px 的标志」用的是同一套分类权重</strong>。好处是稀有类别在任何尺度上出现都能贡献梯度（长尾友好）；<em>坏处是如果某一类只在特定尺度出现（比如高速龙门架上的可变限速牌几乎只在 P5 上出现），共享权重会让它与其他尺度的类别互相干扰</em>。<strong>这也是「两级方案（类别无关检测 + 高分辨率 crop 分类）」在 TSR 里长期有生命力的原因之一</strong>——C55 模块 02 会完整展开。"),
    ])),

    ("dsla", "Dynamic Soft Label Assignment：代价函数逐项拆解", "".join([
        P("模块 02 已经铺垫过它的三项，这里把完整实现讲透。RTMDet 的 <span class=\"term\">DynamicSoftLabelAssigner</span> 是目前工业实时检测器里综合最稳的一个分配器，也是 MMDetection 里 RTMDet / RTMDet-Ins / RTMDet-R 的默认选择。"),
        MATH("C_{ig} \\;=\\; \\underbrace{\\sum_{c}\\mathrm{BCE}\\big(p_{ic},\\, y_{igc}\\big)\\cdot\\big|y_{igc}-p_{ic}\\big|^{2}}_{\\text{软标签分类代价}} \\;+\\; \\underbrace{\\lambda\\big(-\\log u_{ig}\\big)}_{\\lambda=3}\\;+\\; \\underbrace{10^{\\,d_{ig}/s_i-R}}_{R=3,\\ \\text{软中心先验}}"),
        P("其中 $y_{igc} = u_{ig}\\cdot\\mathbf{1}[c = c_g]$ 是<strong>软标签</strong>——分类目标不是 1，而是该格点预测框与 GT 的 IoU。三项分别在做三件事："),
        TABLE(["项", "形式", "解决什么问题", "去掉它会怎样"], [
            ["<strong>软标签分类代价</strong>", "BCE 乘以 $|y-p|^2$ 调制因子", "把「框准不准」写进分类目标，让分数可用于 NMS 排序", "退化成 SimOTA 的硬标签；分数与定位质量脱钩，NMS 排错"],
            ["<strong>调制因子 $|y-p|^2$</strong>", "focal 式的平方权重", "已对齐的格点代价 → 0，<strong>不再参与争抢</strong>；差得远的被放大", "所有格点的分类代价量级相近，代价矩阵区分度下降"],
            ["<strong>IoU 代价</strong>", "$-\\log u$，$u\\to 0$ 时发散", "天然排除框离得远的格点；权重 3 与 YOLOX 一致", "分配变成纯分类驱动，回归监督质量下降"],
            ["<strong>软中心先验</strong>", "$10^{d/s-3}$，连续单调增", "把 SimOTA 的 0/100000 悬崖换成斜坡", "候选不足时 dynamic-k 顶穿硬先验、选到框外格点（模块 02 实测）"],
        ]),
        DUAL(
            "$|y-p|^2$ 这个调制因子值得单独强调，因为它有一个可以直接 assert 的性质：<strong>当预测 $p$ 恰好等于软标签 $y$ 时，分类代价严格为 0</strong>。含义是——<em>「你已经报了一个与你的定位质量完全相称的分数，我不再需要动你」</em>。这让代价矩阵天然把「已经对齐好的格点」排在最前面，<strong>分配结果因此比 SimOTA 稳定得多</strong>（相邻 epoch 之间正样本集合的翻转更少）。",
            "软中心先验的三个刻度值得背下来：$d=0$ 时代价 $10^{-3}$（几乎不惩罚）；$d=3s$ 时代价 $1$（与一个中等 IoU 代价相当，$-\\log 0.37 \\approx 1$）；$d=5s$ 时代价 $100$（实质排除）。<strong>把 <code>soft_center_radius</code> 从 3.0 调到 2.5，等价于把整条衰减曲线左移半个 stride——远处格点的代价整体乘以 $10^{0.5}\\approx 3.2$</strong>。<em>在 TSR 这类「小 + 密」的场景里，调小它能有效减少两个紧邻标志的候选池重叠</em>；代价是极小目标可用的候选进一步减少。",
        ),
        P("剩下的两步与 SimOTA 相同：<strong>dynamic-k</strong>（RTMDet 用 top-13 的 IoU 求和取整，SimOTA 用 top-10）与<strong>去冲突</strong>（代价最小者胜）。<em>所以 DSLA 可以准确地概括成一句话：「把 SimOTA 的硬标签换成 IoU 软标签，把 0/100000 硬先验换成 $10^{d/s-3}$ 软先验，其余不变。」</em>"),
        CALLOUT("danger", "换成软标签后<strong>必须</strong>同步换分类损失：普通 <code>FocalLoss</code> 只接受 0/1 标签，喂给它一个连续目标值会静默出错（不报错、AP 掉几个点）。正确搭配是 <span class=\"term\">Quality Focal Loss</span>：$\\mathrm{QFL}(p,y) = |y-p|^{\\beta}\\cdot\\mathrm{BCE}(p,y)$，它把 focal 的调制项从「离散的难易」推广到「连续的偏离量」。<em>notebook 的练习 4 会让你实现它并验证 $\\mathrm{QFL}(y,y)=0$ 这个性质。</em> <strong>「软标签必须配 QFL」是一个非常具体、面试官一听就知道你真调过的细节。</strong>"),
    ])),

    ("scaling", "模型缩放与任务扩展：tiny→x 的预算怎么分", "".join([
        P("RTMDet 用两个标量控制全部五档：<strong>deepen_factor</strong>（每个 stage 的 block 数乘子）与 <strong>widen_factor</strong>（通道数乘子）。这是 EfficientNet 复合缩放的简化版——<em>去掉了分辨率维度（检测端分辨率通常由部署约束定死），只保留深度与宽度</em>。"),
        TABLE(["档位", "deepen", "widen", "参数量", "FLOPs@640", "COCO AP", "典型定位"], [
            ["<strong>tiny</strong>", "0.167", "0.375", "4.8 M", "8.1 G", "41.1", "边缘芯片 / 备份链路"],
            ["<strong>s</strong>", "0.33", "0.5", "8.89 M", "14.8 G", "44.6", "中低算力车端"],
            ["<strong>m</strong>", "0.67", "0.75", "24.7 M", "39.3 G", "49.4", "<strong>主流量产档位</strong>"],
            ["<strong>l</strong>", "1.0", "1.0", "52.3 M", "80.2 G", "51.5", "高算力车端 / 车队回传预筛"],
            ["<strong>x</strong>", "1.33", "1.25", "94.9 M", "141.7 G", "52.8", "<strong>云端教师模型 / 自动标注</strong>"],
        ]),
        MATH("\\text{params} \\;\\propto\\; w^2 \\cdot f(d), \\qquad \\text{FLOPs} \\;\\propto\\; w^2 \\cdot f(d) \\cdot r^2"),
        DUAL(
            "三条缩放规律必须分清楚：<strong>参数量对宽度是<em>平方</em>关系</strong>（每个 conv 的输入输出通道都乘以 $w$）；<strong>对深度是<em>近似线性</em></strong>（多堆几个 block）；<strong>而分辨率完全不影响参数量，只按平方影响 FLOPs</strong>。notebook 的计算器会把这三条各自 assert 一遍：宽度翻倍 → 参数 ×3.98，分辨率翻倍 → FLOPs ×4.00。",
            "为什么 RTMDet 的宽深比这么保守（x 档只有 widen=1.25）？<strong>因为宽度带来的是并行度，深度带来的是串行延迟</strong>。在 GPU/NPU 上，加宽通常能被并行度吃掉、延迟增长远小于 FLOPs 增长；<em>而加深每一层都要等前一层算完，延迟是硬加上去的</em>。所以<strong>面向延迟优化的模型族倾向于「宽而浅」，面向 FLOPs 优化的倾向于「窄而深」</strong>——这也解释了为什么直接照搬 ImageNet 上的缩放系数到检测器上往往效果不好。<em>面试里能说出「宽度换并行、深度换串行延迟」这一句，就把缩放这题答透了。</em>",
        ),
        H3("同一套结构还能长出别的任务"),
        UL([
            "<strong>RTMDet-Ins（实例分割）</strong>：在检测头旁加一个 mask 分支，用 <em>kernel + mask feature 的动态卷积</em>（CondInst / SOLOv2 路线）——检测头预测一组卷积核参数，与一张共享的 mask feature 做卷积得到实例掩码。<em>好处是掩码分辨率不受 ROI 尺寸限制，对小目标友好</em>。",
            "<strong>RTMDet-R（旋转框）</strong>：把回归目标从 4 维改成 5 维（加角度），并处理角度的周期性与边界不连续问题。<strong>这一条对 TSR 有直接价值</strong>——<em>侧向安装、倾斜的标志牌，以及路侧广告牌与标志的区分，用旋转框能显著减少背景像素占比</em>。",
            "<strong>RTMPose / RTMO</strong>：同一套 CSPNeXt backbone 被复用到姿态估计。<em>这反过来验证了「同构」的价值：一个 backbone 训一次，多个任务复用。</em>",
        ]),
        CALLOUT("intuition", "选档位的实用法则：<strong>先定延迟预算，再在帕累托前沿上取点，而不是先选模型再测延迟</strong>。TSR 在车端通常只分到整个感知预算的一小块（33 ms 里可能只有 3–5 ms），<em>这基本上把选择框定在 tiny/s 两档，或者 m 档 + INT8</em>。而 x 档的正确用法不是上车，是<strong>当云端教师</strong>——跑在回传数据上做自动标注与难例挖掘（C58 的核心工具）。<em>「同一个模型族里，大档位模型的价值在离线而不在线上」是一个很成熟的工程观点。</em>"),
    ])),

    ("tradeoff", "与 YOLO 系的工程取舍：给 TSR 选哪个", "".join([
        P("把 RTMDet 与同期的 YOLO 系放在一起，逐项对比工程属性——<strong>注意这里刻意不比 AP</strong>，因为在同延迟下它们的 AP 差距通常在 1 点以内，而工程属性的差距可以是数量级的。"),
        TABLE(["维度", "RTMDet", "YOLOv8", "YOLOv10", "对 TSR 的含义"], [
            ["<strong>全尺度同构</strong>", "<strong>✓ 五档同一套 block/head/分配器</strong>", "✓ 基本同构", "✓", "一次调参五档复用；车端+云端共用配方"],
            ["<strong>算子种类</strong>", "<strong>只有 3×3 / 5×5 DW / 1×1</strong>", "C2f 结构分支较多", "含 PSA 等注意力块", "算子越少，<strong>TensorRT 覆盖越好、量化越稳</strong>"],
            ["<strong>标签分配</strong>", "DSLA（软标签 + 软先验）", "TaskAligned", "一致双分配", "DSLA 对<strong>密集小目标更稳</strong>；v10 无 NMS 延迟更可控"],
            ["<strong>需要 NMS</strong>", "✓ 需要", "✓ 需要", "<strong>✗ 不需要</strong>", "NMS 让 p99 延迟随目标数波动 —— 车端最忌讳"],
            ["<strong>许可证</strong>", "<strong>Apache 2.0</strong>", "AGPL-3.0", "AGPL-3.0", "<strong>量产项目的硬约束，别忽略</strong>"],
            ["<strong>生态</strong>", "MMDetection（配置化、可复现）", "ultralytics（开箱即用）", "同 v8", "团队协作与实验管理 vs 快速原型"],
        ]),
        DUAL(
            "<strong>许可证那一行是真实会卡住量产的</strong>：ultralytics 的 YOLOv8/v10 是 AGPL-3.0，商用需要购买商业授权，否则整个调用它的系统都可能被要求开源。<em>很多团队在 POC 阶段用 YOLOv8 跑得很爽，到量产评审时才发现这个问题</em>。RTMDet 的 Apache 2.0 没有这个负担。<strong>面试里主动提许可证，会让人觉得你有产品化经验而不只是刷榜经验。</strong>",
            "如果只能给一个 TSR 场景的选型结论，我会这样论证：<strong>① 小目标多 → 需要密集且高质量的正样本 → DSLA 的软先验 + dynamic-k 优于固定 top-k；② 类别多且长尾 → 共享头对稀有类友好，且两级方案可平滑接入；③ 车端延迟预算紧且要 p99 稳定 → 算子种类少、易量化，但 NMS 的目标数依赖是个减分项；④ 量产合规 → Apache 2.0。</strong> <em>综合下来 RTMDet-s/m 是一个很稳的起点；如果 p99 延迟是硬指标，则应该同时评估 RT-DETR（模块 04）或 YOLOv10 这类无 NMS 方案</em>。<strong>注意这个论证的结构：先列场景约束，再逐条映射到技术属性，最后给结论——这就是系统设计题的标准答法。</strong>",
        ),
        CALLOUT("warn", "一个常见的比较错误：<strong>拿 RTMDet 论文里的 FPS 与 YOLOv8 官方的 FPS 直接比</strong>。两者的测量口径几乎肯定不同——是否含 NMS、是否含预处理、batch size、精度（fp16/int8）、显卡型号都可能不一样。<em>模块 05 会专门讲怎么读延迟-精度曲线；这里只记住一条：<strong>跨论文的 FPS 数字不可比，唯一可信的是你自己在目标硬件上、用同一套 harness 测出来的数</strong>。</em>"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>大核的上限在哪里</strong>：RepLKNet 用 31×31、SLaK 用 51×51（稀疏分解）在分类上有效，但<em>检测器上普遍停在 5×5–7×7</em>。是精度真的饱和，还是被硬件 kernel 的实现质量卡住？<strong>如果 depthwise 大核的算子实现被优化到接近访存上限，检测器的最优核尺寸会不会上移？</strong>这是一个「结论依赖硬件代际」的开放问题。",
            "<strong>ERF 的可控设计</strong>：目前 ERF 是结构的<em>副产品</em>——选好核尺寸和深度，ERF 就定了。<strong>能不能把 ERF 作为显式的设计目标</strong>（例如给定目标 $\\sigma_{ERF}$ 反解结构，或加一个正则项直接塑形 ERF）？本模块 notebook 里的解析公式 $\\sigma=\\sqrt{\\sum d_\\ell^2(k_\\ell^2-1)/12}$ 已经把「反解」这一步变得可行，<em>但训练后的真实 ERF 与解析值的偏差如何建模，仍然没有好答案</em>。",
            "<strong>分配的稳定性度量</strong>：DSLA 的 $|y-p|^2$ 调制被认为让分配更稳，但<em>「更稳」缺少标准指标</em>。定义一个「跨 epoch 正样本翻转率」并系统比较 SimOTA / TaskAligned / DSLA，是一个门槛低、价值高的实验（模块 02 的诊断报告是现成的起点）。",
            "<strong>共享头的尺度干扰</strong>：共享权重对长尾友好，但<em>尺度特化的类别会被互相干扰</em>。有没有介于「全共享」与「全独立」之间的方案（例如低秩的 per-level adapter，或按尺度分组共享）？这在 TSR 这类「类别多 + 尺度跨度大」的任务上收益可能很直接。",
            "<strong>缩放系数的自动搜索</strong>：RTMDet 的 deepen/widen 组合是人工给定的。<em>在给定硬件延迟约束下自动搜索宽深比</em>（延迟感知 NAS）在学术上做过很多，但工业上很少真用——因为搜索成本高、且结果换个硬件就失效。<strong>「延迟模型足够准 → 搜索可以离线做」是一条尚未被充分利用的路径</strong>（模块 05 会建这样的延迟模型）。",
            "<strong>无 NMS 与软标签的结合</strong>：YOLOv10 的一致双分配去掉了 NMS，而 DSLA 的软标签让分数携带定位质量。<em>两者原则上互补</em>（无 NMS 需要更可靠的排序，而软标签正是为排序设计的），但把 DSLA 直接接到一对一分支上会遇到监督过稀的问题。<strong>这是一个明确、具体、可做的方向。</strong>",
        ]),
        CALLOUT("paper", "必读（按阅读顺序）：<em>RTMDet: An Empirical Study of Designing Real-Time Object Detectors</em>（★ 主线；重点读消融表而不是结构图）；<em>Understanding the Effective Receptive Field in Deep Convolutional Neural Networks</em>（Luo et al., NeurIPS 2016，★ 本模块第 3 节的理论来源，高斯形状与 $\\sqrt{N}$ 增长的原始推导）；<em>A ConvNet for the 2020s</em>（ConvNeXt，7×7 depthwise 与现代化配方的来源）；<em>Scaling Up Your Kernels to 31×31: Revisiting Large Kernel Design in CNNs</em>（RepLKNet，大核的上限探索与「大核需要重参数化辅助」的观察）；<em>CSPNet: A New Backbone that can Enhance Learning Capability of CNN</em>（CSP 结构）；<em>Generalized Focal Loss</em>（★ Quality Focal Loss 与软标签的理论支撑）；<em>Conditional Convolutions for Instance Segmentation</em>（CondInst，RTMDet-Ins 的 mask 分支路线）。相邻课程：C53 模块 02（标签分配）、模块 04（RT-DETR）、模块 05（延迟-精度权衡）；C57（小目标）、C60（量化与部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · RTMDet 解剖（有效感受野 / 5×5 depthwise / 共享头 / 软标签 / 模型缩放）

目标：把 RTMDet 的四个核心设计**用数字验证一遍**，而不是背结构图。

本 notebook 你会亲手实现：

1. **理论感受野**（TRF）的递推计算器（含 stride 与 dilation）
2. **有效感受野**（ERF）的**梯度回传数值实验** —— 从中心输出单元反传，测出真实的高斯钟形
3. 验证解析公式 $\\sigma_{ERF}=\\sqrt{\\sum d_\\ell^2(k_\\ell^2-1)/12}$ —— **实测与理论精确到小数点后 8 位**
4. **两个 3×3 vs 一个 5×5**：同样的 TRF，ERF 差 $\\sqrt{1.5}=1.2247$ 倍
5. **ReLU 门控**让 ERF 进一步缩小的量化（有效面积 205 → 52）
6. 大核的**成本账**：depthwise/pointwise 拆分、算术强度、固定预算下的最优核尺寸
7. **共享 conv + 每层独立 BN**：参数量账 + 共享 BN 会把统计量污染成什么样
8. **DynamicSoftLabelAssigner 完整代价矩阵**（软标签 + IoU + 软中心先验）
9. **模型缩放计算器**：tiny→x 的参数量/FLOPs，与官方数字对比

> 心智模型：**理论感受野是几何量，有效感受野是统计量。
> 精度跟着后者走，而后者按 √N 增长 —— 所以「加大单层核」比「多堆几层」划算。**"""),

    md("""## 1 · 理论感受野：一个纯几何量（与权重无关）

递推：$r_\\ell = r_{\\ell-1} + (k_\\ell-1)\\cdot d_\\ell \\cdot j_{\\ell-1}$，$j_\\ell = j_{\\ell-1}\\cdot s_\\ell$，$r_0=1,\\ j_0=1$。

先只看 stride=1、dilation=1 的情况：**TRF 直径 $= 1 + \\sum_\\ell (k_\\ell - 1)$**。"""),
    code("""import numpy as np
np.set_printoptions(precision=4, suppress=True)

def trf_stride1(kernels):
    '''stride=1, dilation=1 的堆叠：TRF 直径 = 1 + sum(k-1)。'''
    return 1 + sum(k - 1 for k in kernels)

print(f'{"配置":<22s} {"层数":>5s} {"TRF直径":>8s} {"TRF半径":>8s}')
CONFIGS = [
    ('3x3 x 1',      [3]),
    ('3x3 x 2',      [3, 3]),
    ('5x5 x 1',      [5]),
    ('3x3 x 10',     [3] * 10),
    ('5x5 x 10',     [5] * 10),
    ('7x7 x 10',     [7] * 10),
    ('3x3 x 64',     [3] * 64),
    ('CSPNeXtBlock', [3, 5, 1]),      # 3x3 + 5x5 depthwise + 1x1
]
for name, ks in CONFIGS:
    r = trf_stride1(ks)
    print(f'{name:<22s} {len(ks):>5d} {r:>8d} {r//2:>8d}')

# 两个 3x3 与一个 5x5 的 TRF **完全相同** —— 这是「小核堆叠等价大核」说法的来源
assert trf_stride1([3, 3]) == trf_stride1([5]) == 5
assert trf_stride1([3, 3, 3]) == trf_stride1([7]) == 7
assert trf_stride1([3] * 10) == 21
print()
print('✅ 两个 3x3 的 TRF 与一个 5x5 完全相同（都是 5x5）。')
print('   「小核堆叠可以等价替代大核」这句话，**在 TRF 意义上是对的**。')
print('⚠️  但精度并不跟着 TRF 走。下一节我们把真正起作用的那个量测出来。')"""),

    md("""## 2 · 有效感受野：梯度回传法把它测出来

方法（Luo et al. NeurIPS 2016 的原始做法）：
**从输出特征图的中心单元反传一个单位梯度，看它在输入上留下什么形状。**

对线性卷积栈，反传就是「用 180° 旋转后的核再卷一次」；
我们用均匀核（每个位置权重 $1/k^2$），这样结果可以与解析式精确对拍。"""),
    code("""def conv_same(x, w, d=1):
    '''单通道 same 卷积，支持 dilation。'''
    k = w.shape[0]
    p = (k - 1) * d // 2
    xp = np.pad(x, p)
    out = np.zeros_like(x)
    H, W = x.shape
    for a in range(k):
        for b in range(k):
            out += w[a, b] * xp[a * d:a * d + H, b * d:b * d + W]
    return out

def erf_map(specs, size=161, gate=None, seed=0):
    '''梯度回传法测 ERF。specs = [(kernel, dilation), ...]（从输出侧往输入侧走）。
       均匀核是中心对称的，所以 180 度旋转后还是它自己 -> 反传就是再卷一次。
       gate=None 表示线性网络；gate=p 表示每层有 p 的概率保留梯度（模拟 ReLU 门控）。'''
    g = np.zeros((size, size))
    c = size // 2
    g[c, c] = 1.0                                   # ← 中心输出单元的单位梯度
    rg = np.random.default_rng(seed)
    for (k, d) in specs:
        g = conv_same(g, np.ones((k, k)) / (k * k), d)
        if gate is not None:
            g = g * (rg.random((size, size)) < gate)
    return g

def spatial_std(m):
    '''ERF 的空间标准差（把归一化后的梯度图当成一个二维概率分布）。'''
    s = m.sum()
    if s <= 0:
        return 0.0
    p = m / s
    n = m.shape[0]
    x = np.arange(n) - n // 2
    px = p.sum(0)
    mu = (px * x).sum()
    return float(np.sqrt((px * (x - mu) ** 2).sum()))

def show_erf(m, half=10, chars=' .:-=+*#%@'):
    '''把 ERF 中心区域画成字符热力图。'''
    c = m.shape[0] // 2
    sub = m[c - half:c + half + 1, c - half:c + half + 1]
    v = sub / max(sub.max(), 1e-30)
    for row in v:
        print('  ' + ''.join(chars[min(int(x * (len(chars) - 1) + 0.5), len(chars) - 1)]
                              for x in row))

E = erf_map([(3, 1)] * 10)
print('3x3 堆 10 层的 ERF（TRF 直径 21，下面画的是中心 21x21 区域）：')
show_erf(E, half=10)
print()
print(f'梯度总质量 = {E.sum():.6f}（线性网络下严格守恒 = 1）')
print(f'ERF 空间标准差 = {spatial_std(E):.6f}')
assert abs(E.sum() - 1.0) < 1e-9, '线性卷积栈的梯度质量守恒'
assert E[E.shape[0] // 2, E.shape[1] // 2] == E.max(), '中心贡献最大'
print()
print('⚠️  形状是**钟形而不是方块**：TRF 说「21x21 都可能有贡献」，')
print('    但边缘像素的梯度已经接近 0 —— 模型实际用得上的只有中间那一小块。')"""),

    md("""## 3 · 解析式验证：$\\sigma_{ERF}=\\sqrt{\\sum d_\\ell^2 (k_\\ell^2-1)/12}$

把每层归一化的卷积核看成一个概率分布，堆叠 = 分布自卷积。
宽度 $k$ 的离散均匀分布方差是 $(k^2-1)/12$；空洞率 $d$ 把坐标拉伸 $d$ 倍，方差乘 $d^2$。
**方差可加 ⇒ 标准差按 $\\sqrt{N}$ 增长。这在均匀核线性网络下是精确等式，不是近似。**"""),
    code("""def erf_sigma_theory(specs):
    return float(np.sqrt(sum(d * d * (k * k - 1) / 12 for k, d in specs)))

print(f'{"配置":<24s} {"实测 sigma":>13s} {"理论 sigma":>13s} {"绝对误差":>11s}')
CASES = [
    ('3x3 x 6',                 [(3, 1)] * 6),
    ('5x5 x 6',                 [(5, 1)] * 6),
    ('7x7 x 6',                 [(7, 1)] * 6),
    ('7x7 dilation=3 x 1',      [(7, 3)]),
    ('混合 3,5,3(d2),5,3',      [(3, 1), (5, 1), (3, 2), (5, 1), (3, 1)]),
]
for name, sp in CASES:
    meas = spatial_std(erf_map(sp))
    theo = erf_sigma_theory(sp)
    print(f'{name:<24s} {meas:>13.8f} {theo:>13.8f} {abs(meas - theo):>11.2e}')
    assert abs(meas - theo) < 1e-9, (name, meas, theo)

print()
print('✅ 实测与理论在小数点后 8 位完全一致 —— 这不是拟合，是恒等式。')
print()
print('现在看 ERF/TRF 的比值随深度怎么衰减：')
print(f'{"配置":<16s} {"TRF半径":>8s} {"ERF sigma":>11s} {"ERF/TRF":>9s} {"1/sqrt(N) 参考":>15s}')
for k in [3, 5, 7]:
    for N in [1, 10]:
        sp = [(k, 1)] * N
        sig = erf_sigma_theory(sp)
        r = N * (k - 1) / 2
        print(f'{f"{k}x{k} x {N}":<16s} {r:>8.0f} {sig:>11.4f} {sig / r:>9.4f} '
              f'{1 / np.sqrt(N):>15.4f}')

for N in [1, 4, 16, 64]:
    sp = [(3, 1)] * N
    ratio = erf_sigma_theory(sp) / (N * 1.0)
    print(f'  3x3 x {N:<3d}  ERF/TRF = {ratio:.4f}')
r1 = erf_sigma_theory([(3, 1)] * 4) / 4
r2 = erf_sigma_theory([(3, 1)] * 64) / 64
assert abs(r1 / r2 - 4.0) < 1e-9, 'N 涨 16 倍，ERF/TRF 应恰好降到 1/4'
print()
print('✅ N 从 4 涨到 64（16 倍），ERF/TRF 恰好降到 1/4 = 1/sqrt(16)。')
print('⚠️  推论：**深网络的 TRF 早就覆盖全图，但 ERF 只有十几个像素。**')
print('    「感受野够大了」这句话如果指的是 TRF，基本没有信息量。')"""),

    md("""## 4 · 两个 3×3 vs 一个 5×5：同样的 TRF，不同的 ERF

这是「为什么要用大核」最干净的一个证据。"""),
    code("""a = [(3, 1), (3, 1)]     # 两层 3x3
b = [(5, 1)]             # 一层 5x5
sa, sb = spatial_std(erf_map(a)), spatial_std(erf_map(b))

print(f'{"配置":<14s} {"层数":>5s} {"TRF直径":>8s} {"ERF sigma":>11s}')
print(f'{"3x3 x 2":<14s} {2:>5d} {trf_stride1([3,3]):>8d} {sa:>11.6f}')
print(f'{"5x5 x 1":<14s} {1:>5d} {trf_stride1([5]):>8d} {sb:>11.6f}')
print()
print(f'TRF 完全相同（都是 5），但 ERF 比值 = {sb / sa:.6f}')
print(f'理论值 sqrt( (24/12) / (2*8/12) ) = sqrt(1.5) = {np.sqrt(1.5):.6f}')

assert trf_stride1([3, 3]) == trf_stride1([5])
assert abs(sb / sa - np.sqrt(1.5)) < 1e-9
assert sb > sa
print()
print('✅ 用一层 5x5 换掉两层 3x3：')
print('   · TRF 不变')
print('   · 深度减半  -> **串行延迟减半、梯度路径变短**')
print(f'   · ERF 反而大 {(sb/sa-1)*100:.1f}%')
print()
print('同深度下的差距更大（RTMDet 是在**不减层**的前提下把 3x3 换成 5x5 depthwise）：')
print(f'{"N":>4s} {"3x3 sigma":>11s} {"5x5 sigma":>11s} {"比值":>8s}')
for N in [2, 4, 8, 16]:
    s3 = erf_sigma_theory([(3, 1)] * N)
    s5 = erf_sigma_theory([(5, 1)] * N)
    print(f'{N:>4d} {s3:>11.4f} {s5:>11.4f} {s5 / s3:>8.4f}')
assert abs(erf_sigma_theory([(5, 1)] * 8) / erf_sigma_theory([(3, 1)] * 8) - np.sqrt(3.0)) < 1e-9
print()
print(f'✅ 同深度下 5x5 相对 3x3 的 ERF 比值恒为 sqrt(24/8) = sqrt(3) = {np.sqrt(3):.4f}，与深度无关。')"""),

    md("""## 5 · ReLU 门控：真实网络的 ERF 还要再小一圈

上面是线性网络。真实网络里 ReLU 会随机切断梯度路径。
用「每层以概率 $p$ 保留梯度」模拟，看两个量：
**梯度总质量**（衰减多快）与**有效面积** $(\\sum m)^2/\\sum m^2$（参与度，即「多少个像素在实质贡献」）。"""),
    code("""def participation(m):
    '''有效面积：全部质量集中在 1 个像素时 = 1，均匀摊在 n 个像素上时 = n。'''
    return float(m.sum() ** 2 / (m ** 2).sum())

print('5x5 堆 8 层，5 个随机种子取平均：')
print(f'{"保留概率":>9s} {"梯度总质量":>13s} {"有效面积":>10s} {"相对线性网络":>13s}')
res = {}
for gate in [None, 0.7, 0.5, 0.3]:
    ms, ps = [], []
    for s in range(5):
        m = erf_map([(5, 1)] * 8, size=121, gate=gate, seed=s)
        ms.append(m.sum())
        ps.append(participation(m))
    res[gate] = (float(np.mean(ms)), float(np.mean(ps)))
    tag = '线性（无门控）' if gate is None else f'p={gate}'
    print(f'{tag:>9s} {res[gate][0]:>13.3e} {res[gate][1]:>10.1f} '
          f'{res[gate][1] / res[None][1]:>13.2f}x')

assert res[0.7][1] < res[None][1]
assert res[0.5][1] < res[0.7][1]
assert res[0.3][1] < res[0.5][1], '门控越强，有效面积越小'
assert res[0.3][0] < res[None][0] * 1e-3, '梯度质量随门控指数衰减'
print()
print('单个种子（p=0.3）的 ERF 形状 —— 注意它变得**稀疏且不规则**：')
show_erf(erf_map([(5, 1)] * 8, size=121, gate=0.3, seed=3), half=10)
print()
print(f'⚠️  有效面积从 {res[None][1]:.0f} 掉到 {res[0.3][1]:.0f}（缩小 {res[None][1]/res[0.3][1]:.1f} 倍），')
print(f'    梯度总质量掉了 {np.log10(res[None][0]/res[0.3][0]):.0f} 个数量级。')
print('✅ 所以真实网络的 ERF **比线性估计还要小**。')
print('⚠️  但也别把结论推过头：Luo 的论文指出**训练后的 ERF 显著大于初始化时的 ERF**。')
print('    「ERF 不够大」有时是训练不充分的症状，不一定是结构问题。')"""),

    md("""## 6 · 成本账：为什么 5×5 几乎免费，又为什么不是 11×11"""),
    code("""def conv_params(cin, cout, k, groups=1):
    return (cin // groups) * cout * k * k

def conv_macs(cin, cout, k, hw, groups=1):
    return conv_params(cin, cout, k, groups) * hw * hw

print('① 参数量：depthwise 让核尺寸变成零头')
print(f'{"C":>5s} {"5x5 DW":>10s} {"2x(3x3 dense)":>15s} {"倍数":>8s} '
      f'{"5x5DW 占 DW+PW 的":>18s}')
for C in [64, 128, 256, 512]:
    dw5 = conv_params(C, C, 5, groups=C)
    dense2 = 2 * conv_params(C, C, 3)
    pw = conv_params(C, C, 1)
    print(f'{C:>5d} {dw5:>10,d} {dense2:>15,d} {dense2 / dw5:>7.0f}x {dw5 / (dw5 + pw):>17.1%}')

C = 256
dw3, dw5 = conv_params(C, C, 3, groups=C), conv_params(C, C, 5, groups=C)
pw = conv_params(C, C, 1)
grow = (dw5 - dw3) / (dw3 + pw)
print()
print(f'C=256 时，把 block 里的 3x3 DW 换成 5x5 DW，整个 block 参数只涨 {grow:.1%}')
assert grow < 0.10, '5x5 相对 3x3 的参数增量应小于 10%'
assert dw5 / (dw5 + pw) < 0.10, 'C=256 时空间核只占可分离 block 的 9%'
print('✅ 「5x5 depthwise 几乎免费」的准确含义：相对同一个 block 里的 1x1 pointwise，')
print('   空间核便宜到可以忽略 —— **成本几乎全在 pointwise 上**。')"""),
    code("""print('② 算术强度（MAC 数 / 访存元素数）：depthwise 是**访存受限**的')
HW = 40
print(f'{"算子 (C=256, 40x40)":<26s} {"MACs":>14s} {"访存元素":>11s} {"算术强度":>10s} {"瓶颈":>8s}')
rows = []
for name, k, grp in [('dense 3x3', 3, 1), ('dense 1x1', 1, 1),
                     ('depthwise 3x3', 3, 256), ('depthwise 5x5', 5, 256),
                     ('depthwise 7x7', 7, 256), ('depthwise 11x11', 11, 256)]:
    macs = conv_macs(256, 256, k, HW, groups=grp)
    mem = 2 * 256 * HW * HW + conv_params(256, 256, k, grp)     # 读输入 + 写输出 + 权重
    ai = macs / mem
    rows.append((name, macs, mem, ai))
    print(f'{name:<26s} {macs:>14,d} {mem:>11,d} {ai:>10.1f} '
          f'{("计算受限" if ai > 100 else "**访存受限**"):>8s}')

ai = {r[0]: r[3] for r in rows}
assert ai['dense 3x3'] > 40 * ai['depthwise 5x5'], 'dense 与 depthwise 的算术强度差两个数量级'
assert ai['depthwise 5x5'] < 20
print()
print('⚠️  这是「FLOPs 骗人」的经典案例：depthwise 的 FLOPs 极低，')
print('    但墙钟时间由「读一遍输入、写一遍输出」决定 —— **而这部分与 k 无关**。')
print('    所以 3x3 -> 5x5 的延迟增量很小；但 k 继续增大时权重驻留、寄存器压力、')
print('    以及 kernel 优化不足会让延迟**非线性地跳上去**。')
print('✅ 正确说法：FLOPs 是计算受限算子的良好代理，对访存受限算子完全失效。')"""),
    code("""print('③ 固定参数预算，哪个核尺寸买到最大的 ERF？')
BUDGET, C = 2_000_000, 256
print(f'预算 {BUDGET:,} 参数，通道数 {C}，每层 = depthwise k*k + pointwise 1x1')
print()
print(f'{"k":>4s} {"每层参数":>10s} {"能堆几层":>9s} {"ERF sigma":>11s} {"TRF半径":>8s}')
best = None
for k in [3, 5, 7, 9, 11]:
    per = conv_params(C, C, k, groups=C) + conv_params(C, C, 1)
    n = BUDGET // per
    sig = erf_sigma_theory([(k, 1)] * n)
    print(f'{k:>4d} {per:>10,d} {n:>9d} {sig:>11.3f} {n * (k - 1) // 2:>8d}')
    if best is None or sig > best[1]:
        best = (k, sig)

sig3 = erf_sigma_theory([(3, 1)] * (BUDGET // (conv_params(C, C, 3, groups=C) + C * C)))
assert best[0] == 11, '纯参数量视角下，核越大 ERF 越大'
assert best[1] / sig3 > 3.0, 'k=11 的 ERF 应是 k=3 的 3 倍以上'
print()
print(f'✅ 纯参数量视角：核越大越划算（k=11 的 ERF 是 k=3 的 {best[1]/sig3:.1f} 倍）。')
print('⚠️  **所以「为什么 RTMDet 停在 5x5」的答案一定不在参数量里，而在上一格的访存账里。**')
print('   RTMDet 的消融结论与此一致：3x3->5x5 有明确 AP 提升且延迟几乎不变；')
print('   5x5->7x7 精度收益消失、延迟开始上升。5x5 是精度-延迟曲线的拐点。')"""),

    md("""## 7 · 共享 conv + 每层独立 BN：参数量账与「为什么 BN 不能共享」"""),
    code("""def head_params(feat=256, stacked=2, n_levels=3, n_cls=80, mode='shared_conv_sep_bn'):
    '''三种检测头方案的参数量。cls/reg 两条支路各 stacked 层 3x3。'''
    conv = feat * feat * 9
    bn = 2 * feat                       # gamma + beta（running stats 不算可学参数）
    out = (feat * n_cls + n_cls) + (feat * 4 + 4)      # 每层各自的 1x1 输出头
    if mode == 'per_level':
        body = n_levels * stacked * 2 * (conv + bn)
    elif mode == 'fully_shared':
        body = stacked * 2 * (conv + bn)
    elif mode == 'shared_conv_sep_bn':
        body = stacked * 2 * conv + n_levels * stacked * 2 * bn
    else:
        raise ValueError(mode)
    return body + n_levels * out

MODES = [('per_level', '① 每层独立头'),
         ('fully_shared', '② 全共享（含 BN）'),
         ('shared_conv_sep_bn', '③ 共享 conv + 独立 BN')]
res = {mode: head_params(mode=mode) for mode, _ in MODES}
print(f'{"方案":<26s} {"参数量":>12s} {"相对最省":>10s}')
for mode, name in MODES:
    print(f'{name:<26s} {res[mode]:>12,d} {res[mode] / res["fully_shared"]:>9.3f}x')

assert res['per_level'] > 2.5 * res['shared_conv_sep_bn'], '独立头约为共享头的 3 倍'
assert res['shared_conv_sep_bn'] - res['fully_shared'] < 10_000, '独立 BN 只多几千个参数'
print()
print(f'✅ 方案③ 的 BN 参数是 3 层 x 2 支路 x 2 层 x 512 = {3*2*2*512:,}，方案② 只有 '
      f'2 支路 x 2 层 x 512 = {2*2*512:,}，')
print(f'   两者相差仅 {res["shared_conv_sep_bn"] - res["fully_shared"]:,} 个参数，'
      f'却拿回了正确的多尺度统计量。')
print(f'✅ 方案③ 比方案① 省 {1 - res["shared_conv_sep_bn"]/res["per_level"]:.0%} 的参数，')
print('   同时把三层的梯度汇到同一套权重上 —— **等价于把训练样本量乘了 3**。')"""),
    code("""# 为什么 BN 不能共享：FPN 三层的特征分布根本不是一个量级
rg = np.random.default_rng(0)
FEATS = {                                   # (格点数, 均值, 标准差) —— 高分辨率层幅值小、语义弱
    'P3 (s=8)':  rg.normal(0.2, 0.5, 4000),
    'P4 (s=16)': rg.normal(1.0, 1.5, 1000),
    'P5 (s=32)': rg.normal(2.5, 4.0, 250),
}
pooled = np.concatenate(list(FEATS.values()))
gm, gv = pooled.mean(), pooled.var()
print(f'三层混在一起的统计量: mean={gm:.3f}  var={gv:.3f}')
print(f'（注意格点数 4000:1000:250 —— 混合统计量会被 P3 主导）')
print()
print(f'{"层":<12s} {"原始 mean":>10s} {"原始 std":>9s} | {"共享BN后 mean":>14s} {"std":>7s} '
      f'| {"独立BN后 mean":>14s} {"std":>7s}')
worst = 0.0
for name, v in FEATS.items():
    z_shared = (v - gm) / np.sqrt(gv + 1e-5)
    z_sep = (v - v.mean()) / np.sqrt(v.var() + 1e-5)
    worst = max(worst, abs(z_shared.mean()))
    print(f'{name:<12s} {v.mean():>10.3f} {v.std():>9.3f} | {z_shared.mean():>+14.3f} '
          f'{z_shared.std():>7.3f} | {z_sep.mean():>+14.3f} {z_sep.std():>7.3f}')
    assert abs(z_sep.mean()) < 1e-9 and abs(z_sep.std() - 1.0) < 1e-4

assert worst > 1.0, '共享 BN 下至少有一层的归一化均值偏离 0 超过 1 个标准差'
print()
print(f'⚠️  共享 BN 下，P5 归一化后的均值是 {(FEATS["P5 (s=32)"].mean()-gm)/np.sqrt(gv+1e-5):+.2f}、'
      f'标准差 {FEATS["P5 (s=32)"].std()/np.sqrt(gv+1e-5):.2f} ——')
print('    这一层根本没有被正确归一化。而独立 BN 下三层都精确落在 (0, 1)。')
print('✅ 卷积权重该共享（「什么纹理是交通标志」三个尺度上是同一个函数），')
print('   BN 统计量必须独立（三层的特征分布差一个量级）。RTMDetSepBNHead 的全部设计就是这句话。')
print('✅ 部署副产品：推理时 BN 折叠进 conv -> 导出后变成「每层一套独立 conv 权重」，')
print('   训练享受共享的正则化，推理不承担任何额外开销（与模块 01 的重参数化同源）。')"""),

    md("""## 8 · DynamicSoftLabelAssigner：完整代价矩阵

$$C_{ig} = \\underbrace{\\textstyle\\sum_c \\mathrm{BCE}(p_{ic}, y_{igc})\\cdot|y_{igc}-p_{ic}|^2}_{\\text{软标签分类代价}}
+ \\underbrace{3\\cdot(-\\log u_{ig})}_{\\text{IoU 代价}}
+ \\underbrace{10^{\\,d_{ig}/s_i-3}}_{\\text{软中心先验}}$$

其中 $y_{igc}=u_{ig}\\cdot\\mathbf{1}[c=c_g]$ —— **分类目标不是 1，而是该格点预测框的 IoU**。"""),
    code("""# ---- 一个紧凑的合成场景（320x320，三层 FPN，3 个 GT）----
IMG, STRIDES = 320, [8, 16, 32]

def make_points(img=IMG, strides=STRIDES):
    P, S = [], []
    for s in strides:
        n = img // s
        gy, gx = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
        P.append(np.stack([(gx.ravel() + 0.5) * s, (gy.ravel() + 0.5) * s], 1).astype(float))
        S.append(np.full(n * n, float(s)))
    return np.concatenate(P), np.concatenate(S)

POINTS, PT_S = make_points()
GT = np.array([[150., 90., 168., 108.],      # 18x18 远处标志
               [ 60., 180., 108., 228.],     # 48x48
               [200., 160., 264., 224.]])    # 64x64
GT_CLS = np.array([0, 1, 0])
N_CLS = 3

def bbox_iou(a, b):
    aa = (a[:, 2] - a[:, 0]).clip(0) * (a[:, 3] - a[:, 1]).clip(0)
    ab = (b[:, 2] - b[:, 0]).clip(0) * (b[:, 3] - b[:, 1]).clip(0)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = (rb - lt).clip(0)
    inter = wh[..., 0] * wh[..., 1]
    return inter / (aa[:, None] + ab[None, :] - inter + 1e-12)

def synth_detector(points, gt, gt_cls, n_cls=N_CLS, seed=5):
    rg = np.random.default_rng(seed)
    N = len(points)
    ctr = (gt[:, :2] + gt[:, 2:]) / 2
    sz = np.sqrt((gt[:, 2] - gt[:, 0]) * (gt[:, 3] - gt[:, 1]))
    d = np.linalg.norm(points[:, None, :] - ctr[None, :, :], axis=2) / sz[None, :]
    near, q = d.argmin(1), np.exp(-(d.min(1) / 0.7) ** 2)
    g = gt[near]
    gcx, gcy = (g[:, 0] + g[:, 2]) / 2, (g[:, 1] + g[:, 3]) / 2
    gw, gh = g[:, 2] - g[:, 0], g[:, 3] - g[:, 1]
    j, nz = 1 - q, rg.normal(size=(N, 4))
    pcx, pcy = gcx + nz[:, 0] * .45 * gw * j, gcy + nz[:, 1] * .45 * gh * j
    pw, ph = gw * np.exp(nz[:, 2] * .4 * j), gh * np.exp(nz[:, 3] * .4 * j)
    box = np.stack([pcx - pw / 2, pcy - ph / 2, pcx + pw / 2, pcy + ph / 2], 1)
    logit = rg.normal(-3.6, .6, size=(N, n_cls))
    logit[np.arange(N), gt_cls[near]] += 6.6 * q + rg.normal(0, .9, N)
    return 1 / (1 + np.exp(-logit)), box

CLS_PRED, BOX_PRED = synth_detector(POINTS, GT, GT_CLS)
print(f'格点 {len(POINTS)} 个（40^2+20^2+10^2）, GT {len(GT)} 个, 类别 {N_CLS}')
assert len(POINTS) == 2100 and CLS_PRED.shape == (2100, 3)
print('✅ 合成场景就位')"""),
    code("""EPS = 1e-7

def dsla_cost(points, pt_stride, gt, gt_cls, cls_pred, box_pred,
              iou_weight=3.0, soft_center_radius=3.0):
    '''RTMDet 的 DynamicSoftLabelAssigner 代价矩阵，返回 (G,N) 与三项分解。'''
    G, N, C = len(gt), len(points), cls_pred.shape[1]
    ious = bbox_iou(gt, box_pred).clip(0.0, 1.0)                   # (G,N)

    onehot = np.zeros((G, C)); onehot[np.arange(G), gt_cls] = 1.0
    soft = ious[:, :, None] * onehot[:, None, :]                   # (G,N,C) ← 软标签 = IoU
    p = np.clip(cls_pred, EPS, 1 - EPS)[None]                      # (1,N,C)
    bce = -(soft * np.log(p) + (1 - soft) * np.log(1 - p))
    cls_cost = (bce * (soft - p) ** 2).sum(-1)                     # ← |y-p|^2 调制

    iou_cost = -np.log(np.clip(ious, EPS, None)) * iou_weight

    gctr = (gt[:, :2] + gt[:, 2:]) / 2
    d = np.linalg.norm(points[None, :, :] - gctr[:, None, :], axis=2) / pt_stride[None, :]
    center_cost = 10.0 ** (d - soft_center_radius)

    return cls_cost + iou_cost + center_cost, dict(
        cls=cls_cost, iou=iou_cost, center=center_cost, ious=ious, soft=soft)

COST, PART = dsla_cost(POINTS, PT_S, GT, GT_CLS, CLS_PRED, BOX_PRED)
print(f'代价矩阵 shape = {COST.shape}')
print()
print(f'{"GT":>3s} {"尺寸":>7s} {"最小代价":>10s} {"其中 cls":>10s} {"iou":>9s} {"center":>9s}')
for g in range(len(GT)):
    i = COST[g].argmin()
    print(f'{g:>3d} {GT[g,2]-GT[g,0]:>4.0f}px {COST[g,i]:>10.4f} {PART["cls"][g,i]:>10.4f} '
          f'{PART["iou"][g,i]:>9.4f} {PART["center"][g,i]:>9.4f}')

# —— 性质 1：预测与软标签完全一致时，分类代价严格为 0 ——
g, i = 0, COST[0].argmin()
soft_gi = PART['soft'][g, i]
p_perfect = np.clip(soft_gi, EPS, 1 - EPS)[None, :]
cls_perfect = (-(soft_gi * np.log(p_perfect) + (1 - soft_gi) * np.log(1 - p_perfect))
               * (soft_gi - p_perfect) ** 2).sum()
print()
print(f'软标签 y = {soft_gi}  (IoU={PART["ious"][g,i]:.4f} 放在 GT 类别那一维)')
print(f'若预测恰好 p = y，分类代价 = {cls_perfect:.3e}')
assert cls_perfect < 1e-12, '|y-p|^2 调制因子应让完全对齐的格点代价归零'

# —— 性质 2：软中心先验的三个刻度 ——
for dn, expect in [(0.0, 1e-3), (3.0, 1.0), (5.0, 100.0)]:
    assert abs(10.0 ** (dn - 3.0) - expect) < 1e-9
print(f'软中心先验刻度: d/s=0 -> {10.0**-3:.4f}   d/s=3 -> {10.0**0:.1f}   d/s=5 -> {10.0**2:.0f}')

# —— 性质 3：IoU 代价随 IoU 单调减 ——
u = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
assert np.all(np.diff(-np.log(u) * 3.0) < 0)
print(f'IoU 代价 (-3·log u): ' + '  '.join(f'u={a:.1f}->{-np.log(a)*3:.2f}' for a in u))
print()
print('✅ 三项各司其职：软标签把「框准不准」写进分类目标；|y-p|^2 让已对齐的格点退出争抢；')
print('   IoU 代价排除远框；软中心先验用**斜坡**替代 SimOTA 的 0/100000 **悬崖**。')"""),
    code("""# 剩下两步与 SimOTA 相同：dynamic-k（RTMDet 用 top-13）+ 去冲突（代价最小者胜）
def dsla_assign(cost, ious, topk=13):
    G, N = cost.shape
    nk = min(topk, N)
    dyn_k = np.clip(np.floor(np.sort(ious, 1)[:, -nk:].sum(1)).astype(int), 1, None)
    matching = np.zeros((G, N), bool)
    for g in range(G):
        matching[g, np.argsort(cost[g])[:dyn_k[g]]] = True
    multi = matching.sum(0) > 1
    n_conf = int(multi.sum())
    if multi.any():
        win = np.where(matching, cost, np.inf)[:, multi].argmin(0)
        matching[:, multi] = False
        matching[win, np.where(multi)[0]] = True
    assign = np.full(N, -1)
    has = matching.any(0)
    assign[has] = matching[:, has].argmax(0)
    return assign, dyn_k, n_conf

ASSIGN, DYN_K, NCONF = dsla_assign(COST, PART['ious'])
gctr = (GT[:, :2] + GT[:, 2:]) / 2
dnorm = np.linalg.norm(POINTS[None] - gctr[:, None], axis=2) / PT_S[None]

print(f'{"GT":>3s} {"尺寸":>7s} {"dynamic-k":>10s} {"正样本":>7s} {"正样本平均IoU":>14s} '
      f'{"平均 d/stride":>14s}')
for g in range(len(GT)):
    m = ASSIGN == g
    print(f'{g:>3d} {GT[g,2]-GT[g,0]:>4.0f}px {DYN_K[g]:>10d} {int(m.sum()):>7d} '
          f'{PART["ious"][g, m].mean():>14.3f} {dnorm[g, m].mean():>14.3f}')
print(f'去冲突仲裁次数: {NCONF}')

assert DYN_K.min() >= 1 and (ASSIGN >= 0).sum() == DYN_K.sum() - NCONF
assert all(dnorm[g, ASSIGN == g].mean() < 3.0 for g in range(len(GT))), \
    '软中心先验应把正样本压在 3 个 stride 以内'
assert all(PART['ious'][g, ASSIGN == g].mean() > 0.5 for g in range(len(GT)))
print()
print('✅ 所有正样本的平均中心距离都在 3 个 stride 以内 —— 软先验在 d/s=3 处代价已经等于 1，')
print('   足以压过大多数格点的 cls+iou 优势。这就是「斜坡」的作用方式。')
print('✅ 一句话总结 DSLA：**把 SimOTA 的硬标签换成 IoU 软标签，把 0/100000 硬先验')
print('   换成 10^(d/s-3) 软先验，其余（dynamic-k、去冲突）完全不变。**')"""),

    md("""## 9 · 模型缩放计算器：tiny → x

`deepen_factor` 控制每个 stage 的 block 数，`widen_factor` 控制通道数。
下面这个计算器是**简化的结构估算**（略去 SPPF、通道注意力等），
但我们会验证：**它对官方数字的比值在五个档位上几乎恒定** —— 说明缩放趋势被完整保留。"""),
    code("""def cp(cin, cout, k, groups=1, bn=True):
    return (cin // groups) * cout * k * k + (2 * cout if bn else 0)

def cf(cin, cout, k, hw, groups=1):
    return (cin // groups) * cout * k * k * hw * hw

def cspnext_block(c):                       # 3x3 + 5x5 DW + 1x1
    return cp(c, c, 3) + cp(c, c, 5, groups=c) + cp(c, c, 1)

def cspnext_block_f(c, hw):
    return cf(c, c, 3, hw) + cf(c, c, 5, hw, groups=c) + cf(c, c, 1, hw)

def csp_layer(cin, cout, n):                # CSP: 主/短两支 1x1 + n 个 block + 汇合 1x1
    mid = cout // 2
    return cp(cin, mid, 1) * 2 + cp(mid * 2, cout, 1) + n * cspnext_block(mid)

def csp_layer_f(cin, cout, n, hw):
    mid = cout // 2
    return cf(cin, mid, 1, hw) * 2 + cf(mid * 2, cout, 1, hw) + n * cspnext_block_f(mid, hw)

def rtmdet_stats(widen=1.0, deepen=1.0, res=640, n_cls=80, n_lv=3):
    ch = [int(64 * widen), int(128 * widen), int(256 * widen),
          int(512 * widen), int(1024 * widen)]
    nb = [max(round(3 * deepen), 1), max(round(6 * deepen), 1),
          max(round(6 * deepen), 1), max(round(3 * deepen), 1)]
    Pm = Fm = 0
    hw = res // 2
    Pm += cp(3, ch[0] // 2, 3) + cp(ch[0] // 2, ch[0] // 2, 3) + cp(ch[0] // 2, ch[0], 3)
    Fm += cf(3, ch[0] // 2, 3, hw) + cf(ch[0] // 2, ch[0] // 2, 3, hw) + cf(ch[0] // 2, ch[0], 3, hw)
    for i in range(4):                                    # backbone 4 个 stage
        hw //= 2
        Pm += cp(ch[i], ch[i + 1], 3);            Fm += cf(ch[i], ch[i + 1], 3, hw)
        Pm += csp_layer(ch[i + 1], ch[i + 1], nb[i]); Fm += csp_layer_f(ch[i + 1], ch[i + 1], nb[i], hw)
    nch, nn = ch[2], max(round(3 * deepen), 1)            # neck: PAFPN，统一到 ch[2]
    sizes = [res // 8, res // 16, res // 32]
    for i, s in enumerate(sizes):
        Pm += cp([ch[2], ch[3], ch[4]][i], nch, 1); Fm += cf([ch[2], ch[3], ch[4]][i], nch, 1, s)
    for s in sizes[:2]:
        Pm += csp_layer(nch * 2, nch, nn); Fm += csp_layer_f(nch * 2, nch, nn, s)
    for s in sizes[1:]:
        Pm += cp(nch, nch, 3); Fm += cf(nch, nch, 3, s)
        Pm += csp_layer(nch * 2, nch, nn); Fm += csp_layer_f(nch * 2, nch, nn, s)
    for _ in range(2):                                    # head: 共享 conv + 每层独立 BN
        Pm += cp(nch, nch, 3, bn=False) * 2 + 2 * 2 * nch * n_lv
        for s in sizes:
            Fm += cf(nch, nch, 3, s) * 2
    Pm += (nch * n_cls + n_cls + nch * 4 + 4) * n_lv
    for s in sizes:
        Fm += (nch * n_cls + nch * 4) * s * s
    return Pm, Fm

OFFICIAL = {'tiny': (4.8, 8.1), 's': (8.89, 14.8), 'm': (24.71, 39.27),
            'l': (52.3, 80.23), 'x': (94.86, 141.67)}
VARIANTS = [('tiny', .375, .167), ('s', .5, .33), ('m', .75, .67),
            ('l', 1., 1.), ('x', 1.25, 1.33)]

print(f'{"档位":<6s} {"widen":>6s} {"deepen":>7s} {"估算参数":>10s} {"官方":>8s} {"比值":>7s} '
      f'{"估算MACs":>10s} {"官方":>8s} {"比值":>7s}')
pr, fr = [], []
for name, w, d in VARIANTS:
    p, f = rtmdet_stats(w, d)
    op, of = OFFICIAL[name]
    pr.append(p / 1e6 / op); fr.append(f / 1e9 / of)
    print(f'{name:<6s} {w:>6.3f} {d:>7.3f} {p/1e6:>9.2f}M {op:>7.2f}M {pr[-1]:>7.3f} '
          f'{f/1e9:>9.2f}G {of:>7.2f}G {fr[-1]:>7.3f}')

print()
print(f'参数比值区间 [{min(pr):.3f}, {max(pr):.3f}]，极差 {max(pr)/min(pr):.3f}x')
print(f'MACs 比值区间 [{min(fr):.3f}, {max(fr):.3f}]，极差 {max(fr)/min(fr):.3f}x')
assert max(pr) / min(pr) < 1.05, '简化估算器对官方参数量的比值应在五档上几乎恒定'
assert max(fr) / min(fr) < 1.05
print('✅ 简化估算器系统性偏离官方值（参数约 0.55x、MACs 约 0.77x，因为略去了 SPPF/注意力等），')
print('   但**比值在五个档位上几乎恒定** —— 缩放趋势被完整保留，这正是我们要验证的东西。')"""),
    code("""# 三条缩放规律，各 assert 一遍
p1, f1 = rtmdet_stats(1.0, 1.0, 640)
p2, _ = rtmdet_stats(2.0, 1.0, 640)
p3, _ = rtmdet_stats(1.0, 2.0, 640)
_, f2 = rtmdet_stats(1.0, 1.0, 1280)

print(f'{"变化":<26s} {"参数量比":>10s} {"FLOPs比":>10s} {"理论":>14s}')
print(f'{"widen x2 (宽度翻倍)":<26s} {p2/p1:>10.3f} {"-":>10s} {"w^2 = 4.00":>14s}')
print(f'{"deepen x2 (深度翻倍)":<26s} {p3/p1:>10.3f} {"-":>10s} {"近似线性":>14s}')
print(f'{"res x2 (分辨率翻倍)":<26s} {1.000:>10.3f} {f2/f1:>10.3f} {"r^2 = 4.00":>14s}')

assert 3.9 < p2 / p1 < 4.1, '参数量对宽度是平方关系'
assert 1.3 < p3 / p1 < 1.8, '参数量对深度近似线性（stem/neck/head 不随深度变）'
assert abs(f2 / f1 - 4.0) < 1e-9, 'FLOPs 对分辨率精确是平方关系'
assert rtmdet_stats(1., 1., 1280)[0] == p1, '分辨率完全不影响参数量'
print()
print('✅ 三条规律：参数 ∝ w^2 · f(d)，与分辨率无关；FLOPs ∝ w^2 · f(d) · r^2。')
print('⚠️  为什么 RTMDet 的宽深比这么保守（x 档只有 widen=1.25）？')
print('    **宽度带来并行度，深度带来串行延迟。**')
print('    加宽通常能被 GPU/NPU 的并行度吃掉，延迟增长远小于 FLOPs 增长；')
print('    加深则每层都要等前一层算完，延迟是硬加上去的。')
print('    -> 面向延迟优化的模型族倾向「宽而浅」，面向 FLOPs 的倾向「窄而深」。')
print()
print('TSR 选型的实用法则：先定延迟预算，再在帕累托前沿取点。')
print('  · 车端 33ms 里 TSR 常常只分到 3~5ms -> 基本框定在 tiny/s，或 m + INT8')
print('  · x 档的正确用法不是上车，是**当云端教师**：跑回传数据做自动标注与难例挖掘')"""),

    md("""## ✏️ 练习 1：通用理论感受野计算器

实现 `theoretical_rf(specs)`，`specs = [(k, stride, dilation), ...]`（从输入侧往输出侧）。
返回 `(rf_diameter, total_stride)`。

递推：$r \\mathrel{+}= (k-1)\\cdot d\\cdot j$；$j \\mathrel{*}= s$；初值 $r=1,\\ j=1$。"""),
    code("""def theoretical_rf(specs):
    # TODO: 返回 (感受野直径, 总 stride)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
assert theoretical_rf([(3, 1, 1)]) == (3, 1)
assert theoretical_rf([(5, 1, 1)]) == (5, 1)
assert theoretical_rf([(3, 1, 2)]) == (5, 1), '3x3 空洞率2 的 TRF 等于 5x5'
assert theoretical_rf([(3, 1, 1)] * 10) == (21, 1)
assert theoretical_rf([(3, 1, 1)] * 2) == theoretical_rf([(5, 1, 1)]), '两个3x3 == 一个5x5'
assert theoretical_rf([(1, 1, 1)] * 5) == (1, 1), '1x1 卷积不扩大感受野'
# 下采样让后续每一层的贡献都乘以累计 stride
assert theoretical_rf([(3, 2, 1), (3, 1, 1)]) == (7, 2)
assert theoretical_rf([(3, 2, 1), (3, 2, 1), (3, 1, 1)]) == (15, 4)

print(f'{"结构":<44s} {"TRF直径":>8s} {"总stride":>9s}')
STACKS = [
    ('单层 3x3',                          [(3, 1, 1)]),
    ('CSPNeXtBlock (3x3 + 5x5DW + 1x1)',  [(3, 1, 1), (5, 1, 1), (1, 1, 1)]),
    ('同上但用 3x3 替代 5x5',             [(3, 1, 1), (3, 1, 1), (1, 1, 1)]),
    ('stem + 4 stage 下采样 (每 stage 1 block)',
     [(3, 2, 1), (3, 2, 1), (3, 1, 1), (5, 1, 1), (3, 2, 1), (3, 1, 1), (5, 1, 1),
      (3, 2, 1), (3, 1, 1), (5, 1, 1), (3, 2, 1), (3, 1, 1), (5, 1, 1)]),
]
for name, sp in STACKS:
    r, j = theoretical_rf(sp)
    print(f'{name:<44s} {r:>8d} {j:>9d}')

r_big, j_big = theoretical_rf(STACKS[-1][1])
assert j_big == 32 and r_big > 300
print()
print(f'✅ 练习 1 通过：到 stride 32 那一层，TRF 直径已经有 {r_big} 像素 —— 远超 640 的输入。')
print('   **TRF 早就饱和了，但精度还在随大核提升 —— 这正是必须区分 TRF 与 ERF 的原因。**')"""),

    md("""## ✏️ 练习 2：ERF 的解析预测器，并与数值实验对拍

实现 `erf_sigma(specs)`，`specs = [(k, dilation), ...]`（stride=1）：
$\\sigma = \\sqrt{\\sum_\\ell d_\\ell^2 (k_\\ell^2-1)/12}$。

再实现 `erf_over_trf(k, n)`：同核堆叠 $n$ 层时 ERF 标准差与 TRF 半径的比值。"""),
    code("""def erf_sigma(specs):
    # TODO
    raise NotImplementedError

def erf_over_trf(k, n):
    # TODO: erf_sigma([(k,1)]*n) / (n*(k-1)/2)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert abs(erf_sigma([(3, 1)]) - np.sqrt(8 / 12)) < 1e-12
assert abs(erf_sigma([(5, 1)]) - np.sqrt(2.0)) < 1e-12
assert abs(erf_sigma([(1, 1)] * 9) - 0.0) < 1e-12, '1x1 卷积不扩大 ERF'
assert abs(erf_sigma([(3, 2)]) - erf_sigma([(3, 1)]) * 2) < 1e-12, '空洞率让 sigma 线性放大'
assert abs(erf_sigma([(3, 1)] * 4) - erf_sigma([(3, 1)]) * 2) < 1e-12, '层数 x4 -> sigma x2'

# 与第 2 节的梯度回传数值实验对拍（这是本练习的重点）
for sp in [[(3, 1)] * 6, [(5, 1)] * 4, [(7, 3)], [(3, 1), (5, 1), (3, 2), (5, 1)]]:
    meas = spatial_std(erf_map(sp))
    assert abs(meas - erf_sigma(sp)) < 1e-9, (sp, meas, erf_sigma(sp))
print('✅ 与梯度回传数值实验逐项对拍通过（误差 < 1e-9）')

assert abs(erf_over_trf(3, 1) - np.sqrt(8 / 12) / 1.0) < 1e-12
assert abs(erf_over_trf(3, 4) / erf_over_trf(3, 64) - 4.0) < 1e-9, 'ERF/TRF 按 1/sqrt(N) 衰减'
print()
print(f'{"k":>4s} ' + ' '.join(f'{f"N={n}":>10s}' for n in [1, 4, 16, 64]))
for k in [3, 5, 7]:
    print(f'{k:>4d} ' + ' '.join(f'{erf_over_trf(k, n):>10.4f}' for n in [1, 4, 16, 64]))
print()
print('✅ 练习 2 通过。反过来用这个公式做**结构设计**：')
print('   给定目标 sigma，可以直接反解「用什么核、堆几层」——')
print('   例如想要 sigma=8，5x5 需要 n = 8^2*12/24 = 32 层，7x7 只要 16 层。')
n5 = 8 ** 2 * 12 / (5 ** 2 - 1)
n7 = 8 ** 2 * 12 / (7 ** 2 - 1)
assert abs(n5 - 32) < 1e-9 and abs(n7 - 16) < 1e-9
print(f'   验算: 5x5 需 {n5:.0f} 层, 7x7 需 {n7:.0f} 层')"""),

    md("""## ✏️ 练习 3：固定参数预算下的最优核尺寸

实现 `best_kernel(budget, C, kernels)`：每层是「$k\\times k$ depthwise + $1\\times1$ pointwise」，
参数量 $= Ck^2 + C^2$。在预算内能堆 $n=\\lfloor budget/per\\rfloor$ 层，ERF 为 $\\sqrt{n(k^2-1)/12}$。

返回 `(best_k, {k: (per_layer, n_layers, sigma)})`。"""),
    code("""def best_kernel(budget, C, kernels=(3, 5, 7, 9, 11)):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
bk, table = best_kernel(2_000_000, 256)
assert set(table) == {3, 5, 7, 9, 11}
assert table[3][0] == 256 * 9 + 256 * 256 == 67840
assert table[3][1] == 2_000_000 // 67840 == 29
assert abs(table[3][2] - np.sqrt(29 * 8 / 12)) < 1e-9
assert bk == 11, '纯参数量视角下核越大越划算'
assert table[11][2] / table[3][2] > 3.0

print(f'预算 2,000,000 参数, C=256')
print(f'{"k":>4s} {"每层参数":>10s} {"层数":>6s} {"ERF sigma":>11s} {"相对k=3":>9s}')
for k in sorted(table):
    per, n, sig = table[k]
    print(f'{k:>4d} {per:>10,d} {n:>6d} {sig:>11.3f} {sig/table[3][2]:>8.2f}x')

# 通道数越大，空间核的相对成本越低 -> 大核越划算
bk_small, t_small = best_kernel(2_000_000, 64)
print()
print(f'C=64  时最优 k = {bk_small};  C=256 时最优 k = {bk}')
assert t_small[11][2] / t_small[3][2] < table[11][2] / table[3][2], \
    'C 越小，pointwise 占比越低，大核的相对优势越小'
print()
print('✅ 练习 3 通过。**但现实里 RTMDet 停在 5x5** ——')
print('   因为 depthwise 是访存受限的：墙钟时间由「读输入+写输出」决定，与 k 基本无关，')
print('   而 k 大到 9/11 时权重驻留与 kernel 优化不足会让延迟非线性跳升。')
print('   **参数量的账说「上」，硬件的账说「停」。这就是 5x5 这个数字的来历。**')"""),

    md("""## ✏️ 练习 4：Quality Focal Loss —— 软标签必须配的损失

$\\mathrm{QFL}(p, y) = |y-p|^{\\beta}\\cdot\\big[-(y\\log p + (1-y)\\log(1-p))\\big]$，默认 $\\beta=2$。

实现 `quality_focal_loss(p, y, beta=2.0)`（逐元素，返回同形状数组）。
注意数值稳定：把 `p` clip 到 `[1e-7, 1-1e-7]`。"""),
    code("""def quality_focal_loss(p, y, beta=2.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
p = np.array([0.1, 0.5, 0.8, 0.8, 0.2])
y = np.array([0.0, 0.5, 0.8, 0.2, 0.9])
L = quality_focal_loss(p, y)
assert L.shape == p.shape

# 性质 ①：预测恰好等于目标 -> 损失为 0（|y-p|^beta = 0）
assert L[1] < 1e-12 and L[2] < 1e-12, '完全对齐时 QFL = 0'
# 性质 ②：偏离越大损失越大（同一个 y 下单调）
grid = np.linspace(0.01, 0.99, 99)
lv = quality_focal_loss(grid, np.full_like(grid, 0.7))
i0 = int(np.argmin(np.abs(grid - 0.7)))
assert lv[i0] == lv.min(), 'QFL 在 p=y 处取最小'
assert np.all(np.diff(lv[:i0]) < 0) and np.all(np.diff(lv[i0:]) > 0), 'p=y 两侧单调'
# 性质 ③：y 为 0/1 时退化成 focal 风格（易样本被强烈降权）
easy = quality_focal_loss(np.array([0.99]), np.array([1.0]))[0]
hard = quality_focal_loss(np.array([0.10]), np.array([1.0]))[0]
assert hard > 500 * easy, '难样本的权重应远大于易样本'
# 性质 ④：beta 越大，易样本被压得越狠
assert (quality_focal_loss(np.array([0.9]), np.array([1.0]), beta=4.0)[0]
        < quality_focal_loss(np.array([0.9]), np.array([1.0]), beta=2.0)[0])

print(f'{"p":>6s} {"y":>6s} {"|y-p|^2":>9s} {"BCE":>9s} {"QFL":>10s}')
for pi, yi in zip(p, y):
    pc = np.clip(pi, 1e-7, 1 - 1e-7)
    bce = -(yi * np.log(pc) + (1 - yi) * np.log(1 - pc))
    print(f'{pi:>6.2f} {yi:>6.2f} {abs(yi-pi)**2:>9.4f} {bce:>9.4f} '
          f'{quality_focal_loss(np.array([pi]), np.array([yi]))[0]:>10.5f}')
print()
print('✅ 练习 4 通过。**为什么必须换损失**：普通 FocalLoss 只接受 0/1 标签，')
print('   喂给它一个连续目标值会**静默出错**（不报错、AP 掉几个点）。')
print('   QFL 把 focal 的调制项从「离散的难易」推广到「连续的偏离量」，')
print('   于是同一套机制既能处理硬标签也能处理软标签。')
print('⚠️  连带后果：软标签让分类分数整体下移（目标值从 1.0 变成 IoU≈0.6~0.9）——')
print('   **换分配器后 score 阈值必须在验证集上重扫**，否则召回会莫名掉一截。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def theoretical_rf(specs):
    r, j = 1, 1
    for (k, s, d) in specs:
        r += (k - 1) * d * j
        j *= s
    return r, j"""),
    code("""# 练习 2 参考答案
def erf_sigma(specs):
    return float(np.sqrt(sum(d * d * (k * k - 1) / 12 for k, d in specs)))

def erf_over_trf(k, n):
    return erf_sigma([(k, 1)] * n) / (n * (k - 1) / 2)"""),
    code("""# 练习 3 参考答案
def best_kernel(budget, C, kernels=(3, 5, 7, 9, 11)):
    table = {}
    for k in kernels:
        per = C * k * k + C * C          # depthwise k x k + pointwise 1x1
        n = budget // per
        table[k] = (per, int(n), float(np.sqrt(n * (k * k - 1) / 12)))
    return max(table, key=lambda k: table[k][2]), table"""),
    code("""# 练习 4 参考答案
def quality_focal_loss(p, y, beta=2.0):
    p = np.clip(np.asarray(p, dtype=float), 1e-7, 1 - 1e-7)
    y = np.asarray(y, dtype=float)
    bce = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return np.abs(y - p) ** beta * bce"""),

    md("""---
## 🧪 真实工程胶囊：RTMDet 的关键配置与「照抄哪些、别抄哪些」"""),
    code(r"""RECIPE = r'''
# ============ ① mmdetection 里 RTMDet 的关键配置块 ============
model = dict(
    type='RTMDet',
    backbone=dict(
        type='CSPNeXt', arch='P5',
        deepen_factor=0.67, widen_factor=0.75,      # ← m 档；五档只改这两个数
        channel_attention=True,                      # 小模型收益明显，大模型递减
        norm_cfg=dict(type='SyncBN'), act_cfg=dict(type='SiLU', inplace=True)),
    neck=dict(
        type='CSPNeXtPAFPN',
        in_channels=[192, 384, 768], out_channels=192,
        num_csp_blocks=2,                            # ← neck 与 backbone 用**同一种 block**
        expand_ratio=0.5),
    bbox_head=dict(
        type='RTMDetSepBNHead',
        in_channels=192, feat_channels=192, stacked_convs=2,
        share_conv=True,                             # ← **卷积权重跨层共享，BN 每层独立**
        pred_kernel_size=1,
        loss_cls=dict(type='QualityFocalLoss', use_sigmoid=True, beta=2.0,
                      loss_weight=1.0),              # ← 软标签**必须**配 QFL
        loss_bbox=dict(type='GIoULoss', loss_weight=2.0)),
    train_cfg=dict(assigner=dict(
        type='DynamicSoftLabelAssigner',
        topk=13,                                     # dynamic-k：top-13 IoU 求和
        iou_weight=3.0,
        soft_center_radius=3.0)),                    # 10^(d/stride - 3)
)

# ============ ② TSR 场景要改的地方（别原样照抄 COCO 配置） ============
# 1. soft_center_radius: 3.0 -> 2.5
#    密集小目标（主牌+辅助牌）候选池重叠严重，收紧中心先验能减少名额争夺。
#    代价：极小目标可用候选进一步减少 —— 必须配合下面第 2 条一起改。
# 2. 加 P2 层（stride 4）或提高输入分辨率。
#    16x16 的标志在 stride 8/16/32 上一共只有 2 个格点中心落在框内（模块 02 实测）。
#    **这是物理上限，换任何分配器都突破不了。**
# 3. score 阈值必须重扫。软标签把分类分数整体下移，沿用旧阈值会掉召回。
# 4. num_classes 大幅增加时，head 的 1x1 输出层参数会线性增长；
#    类别极多（>200）时考虑两级方案（类别无关检测 + 高分辨率 crop 分类，见 C55 m02）。

# ============ ③ 5x5 大核相关的部署检查 ============
# - depthwise 5x5 在 TensorRT 上是否被高效实现？用 trtexec --dumpProfile 看逐层耗时，
#   如果 DW 层占比异常高，说明 kernel 走了慢路径（换 TRT 版本或退回 3x3 验证）。
# - depthwise 层是**访存受限**的：FLOPs 低不等于快。别用 FLOPs 估延迟。
# - Conv+BN 折叠后，「共享 conv + 每层独立 BN」会展开成每层独立的 conv 权重，
#   engine 体积按层数增长 —— 导出后核对参数量，别以为共享头就一定省 engine。

# ============ ④ 换核尺寸/换分配器时的最小验证集 ============
#   [ ] 参数量与 MACs 变化（本 notebook 的计算器）
#   [ ] 目标硬件上的 p50/p99 延迟（不是 FLOPs！）
#   [ ] 分尺寸桶的 AP（小目标桶单独看，整体 mAP 会掩盖它）
#   [ ] 重扫 score 阈值后的 PR 曲线，而不是固定阈值下的单点
'''
print(RECIPE)
for key in ['CSPNeXt', 'deepen_factor', 'CSPNeXtPAFPN', 'RTMDetSepBNHead', 'share_conv',
            'QualityFocalLoss', 'DynamicSoftLabelAssigner', 'soft_center_radius',
            '访存受限', 'p99']:
    assert key in RECIPE, key
print('✅ 配方覆盖：五档同构配置 / TSR 定制改动 / 大核部署检查 / 最小验证集')"""),

    md("""### 小结

- **理论感受野是几何量，有效感受野是统计量，精度跟着后者走。**
  TRF 半径按 $N$ 线性增长，ERF 标准差按 $\\sqrt{N}$ 增长 ——
  两者之比按 $1/\\sqrt{N}$ 衰减（3×3 堆 64 层时只剩 10%）。
- **$\\sigma_{ERF}=\\sqrt{\\sum d_\\ell^2(k_\\ell^2-1)/12}$ 在均匀核线性网络下是恒等式**，
  本 notebook 用梯度回传法验证到小数点后 8 位。ReLU 门控会让真实 ERF 再小一圈
  （有效面积 205 → 52），但训练后的 ERF 又会显著大于初始化时的。
- **两个 3×3 与一个 5×5 的 TRF 完全相同，ERF 差 $\\sqrt{1.5}$ 倍**；
  同深度下 5×5 相对 3×3 的 ERF 比值恒为 $\\sqrt{3}$，与深度无关。
  **加大单层核比多堆几层划算，而且不增加串行延迟。**
- **可分离结构里成本几乎全在 1×1 pointwise 上**（C=256 时 5×5 DW 只占 8.9%），
  所以 3×3→5×5 只涨 5.7% 参数。**但 depthwise 是访存受限的** ——
  参数量的账说「核越大越好」，硬件的账说「停在 5×5」。
  **「FLOPs 是计算受限算子的良好代理，对访存受限算子完全失效」是面试高频点。**
- **共享 conv + 每层独立 BN**：省 67% 参数、把三层梯度汇到同一套权重（等价样本量 ×3），
  又不让 FPN 三层差一个量级的统计量互相污染。推理时 BN 折叠 → 零额外开销。
- **DSLA = SimOTA 换两件事**：硬标签 → IoU 软标签（分数携带定位质量，NMS 排序才对）；
  0/100000 硬先验 → $10^{d/s-3}$ 软先验（斜坡替代悬崖）。
  **软标签必须配 Quality Focal Loss，且 score 阈值必须重扫。**
- **缩放三规律**：参数 $\\propto w^2 f(d)$、与分辨率无关；FLOPs $\\propto w^2 f(d) r^2$。
  **宽度换并行度，深度换串行延迟** —— 面向延迟的模型族倾向「宽而浅」。
  x 档的正确用法是当云端教师做自动标注，不是上车。

下一站：**模块 04 · RT-DETR 解剖** —— 当 NMS 成为延迟方差的来源时，检测器该怎么重构。"""),
]
