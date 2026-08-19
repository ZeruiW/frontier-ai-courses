# -*- coding: utf-8 -*-
"""C64 模块 03 · 深度学习架构问答（ML/DL 技术知识问答）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "知道卷积、池化、全连接层是什么；见过 ResNet/Transformer 的结构图即可，"
              "不需要重新推导反向传播或注意力的完整数学"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_architectures_qa.ipynb（纯 numpy，'
                    '参数量/FLOPs/感受野计算器 · 1×1 卷积与深度可分离卷积收益量化 · 空洞卷积 gridding 数值实验 · '
                    'BN/GN 小 batch 稳定性对比 · 从零实现 scaled dot-product attention 并验证 √d_k · 三类位置编码外推对比）'),
    ("核心参考", "C18 模块 02-03（CNN 分类/检测基础，本课不重复卷积的反向传播推导）· "
              "C00 模块 01/03（Transformer 结构，本课不重复）· C53-03（RTMDet 大核卷积）· C54 模块 03（object query 与注意力）"),
    ("预计时长", "读 60 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("conv-arithmetic", "卷积口算：参数量、FLOPs 与感受野递推", "".join([
        P("<strong>一句话定义</strong>：卷积层的参数量只取决于卷积核大小与输入输出通道数，"
          "<em>与输入分辨率无关</em>；FLOPs（或 MACs）则同时取决于参数量与输出特征图的空间尺寸——"
          "这一句话本身就是面试里「参数量和计算量为什么会不成比例」这个追问的标准答案。"),
        MATH("\\text{参数量（不含偏置）} = k_h k_w \\cdot C_{in} \\cdot C_{out} \\qquad\\qquad "
             "\\text{MACs} = k_h k_w \\cdot C_{in} \\cdot C_{out} \\cdot H_{out} \\cdot W_{out}"),
        CALLOUT("warn", "<strong>MACs 与 FLOPs 是两个常被混用的量</strong>：1 次乘加（multiply-accumulate）通常记为 2 FLOPs。"
                        "很多论文报的是 MACs 却写成 FLOPs（或反过来），<strong>面试里被问「这个模型多少 FLOPs」时，"
                        "先确认对方问的是 MACs 还是 2×MACs 的 FLOPs</strong>，否则报出来的数字会相差整整一倍，"
                        "这是最容易被追问出「原来他没有真正算过」的一个坑。"),
        P("<strong>感受野递推</strong>——不重复 C18 的完整推导，只给一个能在白板上 30 秒写出来的公式："
          "第 $l$ 层的感受野 $\\mathrm{RF}_l$ 由上一层感受野加上「这一层核在上一层坐标系里能张开多大」决定，"
          "而这个「张开量」要乘上此前所有层的累积步长 $\\mathrm{jump}_{l-1}$（因为越往深层走，"
          "一个像素在原图上对应的间隔越大）。"),
        MATH("\\mathrm{RF}_l = \\mathrm{RF}_{l-1} + (k_l-1)\\cdot\\mathrm{jump}_{l-1}, "
             "\\qquad \\mathrm{jump}_l = \\mathrm{jump}_{l-1}\\cdot s_l \\qquad (\\mathrm{RF}_0{=}1,\\ \\mathrm{jump}_0{=}1)"),
        ASCII("""三层 3x3 stride1 堆叠 == 一个 7x7 卷积的感受野（VGG 论文的经典论证）：

  层0(输入)   RF=1                     ●
  层1(3x3,s1) RF=1+(3-1)*1=3         ●●●
  层2(3x3,s1) RF=3+(3-1)*1=5       ●●●●●
  层3(3x3,s1) RF=5+(3-1)*1=7     ●●●●●●●

  代价对比（单层 3x3,Cout 通道 vs 三层堆叠，同样感受野 7x7）：
  一个 7x7 卷积:  参数 = 7*7*Cin*Cout = 49*Cin*Cout
  三个 3x3 卷积:  参数 = 3*(3*3*Cin*Cout) = 27*Cin*Cout   且中间多两次非线性激活
  -> 堆叠版参数更少、非线性更多，这正是 VGG/后续几乎所有 backbone 弃用大卷积核的原因"""),
        TABLE(["场景", "口算怎么问自己", "面试追问示例"], [
            ["「这层卷积多少参数」", "$k^2\\cdot C_{in}\\cdot C_{out}$，与分辨率<strong>无关</strong>", "「如果输入分辨率翻倍，这层参数量变吗」——不变，只有激活的显存占用会变"],
            ["「这层多少 FLOPs」", "参数量 $\\times H_{out}W_{out}\\times 2$（乘加算 2 FLOPs）", "「stride 2 的卷积比 stride 1 的 FLOPs 少多少」——输出分辨率变 1/4，FLOPs 也约变 1/4"],
            ["「堆到第 N 层，感受野多大」", "用递推公式手算 2-3 层，不要死记某个 backbone 的具体数字", "「有效感受野和理论感受野一样大吗」——不一样，"
             "理论感受野是几何上的覆盖范围，<strong>有效感受野（ERF）通常远小于理论值</strong>（中心像素权重远高于边缘，见 C53-03 的实测）"],
        ]),
        DUAL(
            "直白说：参数量只看「这个卷积核长什么样、连着多少个通道」，跟图片开多大分辨率没关系——"
            "就像一把固定尺寸的印章，不管纸多大，印章本身的刻字不会变；但你要盖多少次章（FLOPs），"
            "当然取决于纸有多大。",
            "严谨地说，感受野的递推公式描述的是<strong>理论感受野</strong>——几何上「这个输出像素依赖了输入的哪个范围」。"
            "但由于卷积核内部权重不均匀、非线性激活的截断效应，"
            "真正对输出有显著贡献的输入范围（<span class=\"term\">effective receptive field</span>）通常呈高斯状衰减，"
            "半径远小于理论值——这是<strong>大卷积核/空洞卷积/更深网络</strong>这几类设计动机的共同出发点，"
            "本课模块 03 的 dilated conv 一节会展开其中一种解法。",
        ),
    ])),

    # ============================================================== 2
    ("conv-1x1-depthwise", "1×1 卷积的三个作用与深度可分离卷积", "".join([
        P("<strong>1×1 卷积三个作用</strong>是一道几乎必考的白板题，三个作用要分开说清楚，别混成一句「降维」："),
        TABLE(["作用", "机制", "典型例子"], [
            ["① <strong>通道数变换（无空间混合）</strong>", "$k{=}1$ 时感受野贡献为 0（下方 notebook 会用感受野公式验证），"
             "纯粹是对每个空间位置的 $C_{in}$ 维向量做一次线性变换到 $C_{out}$ 维", "ResNet bottleneck 的降维/升维层"],
            ["② <strong>跨通道信息混合</strong>", "对同一空间位置的所有输入通道做加权求和，"
             "相当于在「通道」这个维度上做了一次全连接", "Inception 模块里融合多分支输出"],
            ["③ <strong>廉价地插入非线性 / 增加深度</strong>", "1×1 卷积后接一个 ReLU，"
             "用极少的参数和 FLOPs 换来多一层非线性表达能力，而不改变特征图分辨率", "NIN（Network in Network）的动机"],
        ]),
        P("<strong>最值钱的应用：瓶颈（bottleneck）结构</strong>——先用 1×1 把通道数压小，"
          "在压缩后的低维空间做代价最高的 3×3 卷积，再用 1×1 把通道数扩回去。"
          "notebook 会算出一个具体倍数：ResNet 的 256→64→64→256 瓶颈块，"
          "参数量只有同样输入输出通道数的两层 3×3 堆叠的<strong>约 5.9%</strong>（省了约 17 倍）。"),
        H3("深度可分离卷积：把「空间混合」和「通道混合」拆开算账"),
        P("<strong>一句话定义</strong>：标准卷积在一步里同时做「空间加权求和」和「跨通道求和」；"
          "深度可分离卷积把它拆成两步——<strong>depthwise</strong>（每个通道各自用一个 $k\\times k$ 核做空间卷积，"
          "通道之间互不干扰）+ <strong>pointwise</strong>（一个 1×1 卷积做跨通道混合）。"
          "两步合起来完成了标准卷积同样的「空间+通道」两件事，但参数量大幅下降。"),
        MATH("\\frac{\\text{深度可分离参数量}}{\\text{标准卷积参数量}} = \\frac{k^2 C_{in}+C_{in}C_{out}}{k^2 C_{in}C_{out}} "
             "= \\frac{1}{C_{out}} + \\frac{1}{k^2}"),
        TABLE(["项", "标准卷积（$C_{in}{=}C_{out}{=}256, k{=}3$）", "深度可分离", "收益/代价"], [
            ["参数量", "589,824", "67,840（depthwise 2,304 + pointwise 65,536）", "约 <strong>8.7 倍</strong>压缩，与公式 $1/256+1/9\\approx0.115$ 精确吻合"],
            ["表达能力", "空间与通道混合<strong>联合</strong>建模", "空间与通道混合<strong>分离</strong>建模", "分离假设有损失，通常需要更多层/更宽通道弥补"],
            ["硬件效率", "访存/计算比高度优化（主流框架卷积核成熟）", "depthwise 是访存受限操作（每个通道独立、算力利用率低）", "<strong>理论 FLOPs 降低不代表实际延迟等比例降低</strong>——这是移动端部署的经典陷阱"],
        ]),
        DUAL(
            "直白说：标准卷积做一次「既要看邻居像素、又要看别的通道」的运算；深度可分离卷积把这两件事拆开——"
            "先各管各的通道看邻居（depthwise），再用一个 1×1 把所有通道的结果掺一掺（pointwise）。"
            "拆开之后算得少了很多，但「一步到位」时能捕捉的某些跨通道-跨空间联合模式会丢一些。",
            "面试追问「MobileNet 参数少了很多，为什么实际部署延迟没有等比例减少」——标准答案是"
            "<strong>depthwise 卷积是访存受限（memory-bound）而非计算受限（compute-bound）操作</strong>："
            "每个输出通道只依赖对应的一个输入通道，数据复用率低，GPU/NPU 的算力单元大部分时间在等数据搬运，"
            "而不是在做乘加运算。<em>FLOPs 降低了，但硬件利用率也降低了，两者相乘后实际延迟的降低幅度远小于 FLOPs 降低幅度</em>——"
            "这正是「不能只看论文里的 FLOPs 表格来判断部署速度」这一条工程共识的来源（呼应 C60-05 的 roofline 视角）。",
        ),
        CALLOUT("intuition", "记住这句可以直接在面试里说的对照：<strong>「标准卷积一步做完空间+通道混合；"
                             "深度可分离把它拆成 depthwise（空间）+ pointwise（通道）两步，参数量降到约 "
                             "$1/C_{out}+1/k^2$，但因为 depthwise 是访存受限操作，实际部署加速比往往小于理论 FLOPs 加速比。」</strong>"),
    ])),

    # ============================================================== 3
    ("conv-dilated-transpose-pooling", "空洞卷积、转置卷积与池化 vs stride 卷积", "".join([
        P("<strong>空洞（dilated / atrous）卷积</strong>一句话定义：在卷积核的采样点之间插入固定间隔（膨胀率 $r$），"
          "用同样的参数量换来更大的感受野，且<strong>不downsample、不丢分辨率</strong>——"
          "这对需要「既要大感受野又要保留细节分辨率」的语义分割/检测任务很关键。"),
        P("<strong>什么时候它失效</strong>：如果连续多层都用<em>同一个</em>膨胀率，输入像素的采样点会形成规律的稀疏网格，"
          "导致<strong>棋盘状的采样空洞（gridding artifact）</strong>——某些输入位置<em>无论堆多少层都永远不会被采样到</em>，"
          "信息在这些位置上出现结构性丢失。"),
        ASCII("""1D 简化演示（3x3 核在膨胀率 r 下，单层采样偏移量为 {-r, 0, +r}）：

  连续 3 层膨胀率恒为 2（r=2,2,2）：
    可达偏移量（三层偏移集合的 Minkowski 和）= {-6,-4,-2,0,2,4,6}
    理论感受野范围 [-6,6]，但奇数位置 {-5,-3,-1,1,3,5} 永远采样不到  <- 棋盘空洞！

  HDC 方案（膨胀率依次为 1,2,5，来自 Hybrid Dilated Convolution）：
    可达偏移量 = {-8,...,8} 连续覆盖，零空洞

  结论：膨胀率必须像 (1,2,5) 这样"锯齿状"设计，不能每层都用同一个数字"""),
        P("<strong>转置卷积（transposed conv）</strong>一句话定义：用于上采样的卷积，"
          "本质是把卷积的前向/反向计算对调（前向变成「稀疏插值+卷积」）。它的经典失效模式是"
          "<strong>棋盘效应（checkerboard artifact）</strong>——当核大小不能被步长整除时"
          "（比如 kernel=4, stride=2 尚可，kernel=3, stride=2 就会不均匀），"
          "输出像素被上一层不同数量的输入像素重叠覆盖，形成周期性的亮暗条纹。"
          "<strong>对策</strong>：用「先插值（bilinear/nearest）再做普通卷积」替代转置卷积（Odena et al. 2016 的建议），"
          "或者保证 kernel 大小是 stride 的整数倍。"),
        H3("池化 vs stride 卷积：都在下采样，但下采样的方式不同"),
        TABLE(["方式", "机制", "优点", "缺点"], [
            ["<strong>Max/Avg Pooling</strong>", "无参数，取窗口内最大值/均值", "零参数、提供一定的平移不变性、正则化效应", "<strong>信息丢弃是硬性的</strong>——"
             "max pooling 直接丢掉除最大值外的所有信息，无法学习"],
            ["<strong>Stride 卷积</strong>", "卷积核本身带步长，下采样与特征提取同时完成", "下采样方式是<strong>可学习的</strong>，理论表达能力更强", "<strong>参数量与 FLOPs 都比池化多</strong>；"
             "现代 backbone（ResNet 之后）普遍用 stride 卷积替代池化做下采样"],
        ]),
        DUAL(
            "直白说：池化像是「这一块地方我只要个大概齐（最大值/平均值）」，简单粗暴但不会学坏；"
            "stride 卷积是「这一块地方具体怎么压缩，交给网络自己学」，更聪明但也多花了参数和算力。",
            "现代检测/分类 backbone（ResNet 及之后）的下采样几乎都用 stride 卷积（或 stride 卷积+shortcut 的组合）"
            "而非 pooling，只在网络末端偶尔保留一次 global average pooling 做空间聚合——"
            "这反映了一个通用趋势：<strong>只要参数/算力预算允许，把「人工设计的确定性操作」替换成「可学习的操作」"
            "通常能拿到精度收益</strong>，这也是 CNN 演进史的一条暗线，在下面「CNN vs Transformer」一节还会再出现。",
        ),
        CALLOUT("danger", "<strong>面试踩雷点</strong>：如果被要求设计一个语义分割网络的 decoder，"
                          "直接说「用转置卷积上采样」而不提棋盘效应的风险，会被追问「那你怎么保证输出不出现网格纹路」。"
                          "更稳妥的答案是<strong>先说权衡</strong>：「转置卷积可学习但有棋盘效应风险，"
                          "如果对输出平滑性要求高，我会用双线性插值+普通卷积；如果追求极致灵活度且有足够数据，"
                          "会用转置卷积但把 kernel 设成 stride 的整数倍来规避」。"),
    ])),

    # ============================================================== 4
    ("normalization-family", "归一化家族：BN / LN / GN / IN 与训练-推理的不同", "".join([
        P("<strong>一句话区分四者</strong>：它们唯一的区别是「在哪些维度上求均值和方差」——"
          "把一个特征图想成 $(N,C,H,W)$ 四个轴，四种归一化只是选了不同的轴子集来统计。"),
        TABLE(["方法", "统计的维度", "是否依赖 batch", "典型场景"], [
            ["<strong>BatchNorm</strong>", "$(N,H,W)$，每个 <em>C</em> 独立统计", "<strong>是</strong>——统计量跨样本计算", "分类/检测的 CNN backbone（batch 较大时）"],
            ["<strong>LayerNorm</strong>", "单个样本的 $(C,H,W)$（NLP 里通常是 $(C)$，即最后一维）", "否——每个样本独立", "Transformer（下面详细展开为什么）"],
            ["<strong>GroupNorm</strong>", "单个样本，$C$ 被分成 $G$ 组，每组内的 $(C/G,H,W)$", "否", "检测/分割（batch 天然很小时的 BN 替代品）"],
            ["<strong>InstanceNorm</strong>", "单个样本，单个通道的 $(H,W)$", "否", "风格迁移等需要保留单样本对比度的任务"],
        ]),
        CALLOUT("intuition", "<strong>GroupNorm 是 LN 和 IN 的一般化</strong>——这是一个非常适合白板画出来的事实："
                             "$G{=}1$（所有通道分一组）时 GN 退化为 LN；$G{=}C$（每个通道自成一组）时 GN 退化为 IN。"
                             "notebook 会直接用代码验证这个等价关系，这也是练习 3 的内容。"),
        P("<strong>BN 训练与推理为什么不同</strong>：训练时用<em>当前 mini-batch</em>的均值方差做归一化，"
          "同时用滑动平均维护一份 <span class=\"term\">running mean/var</span>；推理时 batch 可能只有 1"
          "（甚至逐帧推理，统计量没有意义），所以<strong>固定使用训练阶段积累的 running statistics</strong>，"
          "不再依赖当前输入的统计量——这也是 BN 层在 <code>model.eval()</code> 后行为切换的根源。"),
        P("<strong>BN 在小 batch 与检测任务上为什么出问题</strong>：检测/分割模型通常因为显存限制"
          "（图像分辨率大、需要多尺度特征、一张卡上只能塞进个位数张图）只能用很小的 batch size（1–4），"
          "而 BN 的统计量是跨 batch 维度计算的——<strong>batch 越小，单次估计的均值/方差方差就越大</strong>，"
          "训练时的归一化统计量变得高度依赖于「这一批恰好抽到了哪几张图」，等价于给模型引入了额外的、不可控的噪声源。"),
        ASCII("""固定同一张图 x_target，反复把它塞进不同组成的 mini-batch，测「BN 输出」随 batch 组成的抖动：

  batch_size=2    BN 输出方差(跨不同 batch 组成) ≈ 0.0051   <- 抖动很大
  batch_size=4                                   ≈ 0.0038
  batch_size=8                                   ≈ 0.0022
  batch_size=32                                  ≈ 0.00056
  batch_size=128                                 ≈ 0.00014  <- 抖动很小

  GroupNorm 对同一张图重复计算：输出<strong>完全相同</strong>（方差恒为 0）
  —— 因为 GN 的统计量只看这张图自己，与 batch 里有谁完全无关"""),
        P("正因如此，<strong>检测/分割领域常用 GroupNorm 或 Synchronized BN（跨多卡合并统计量）替代普通 BN</strong>——"
          "GN 用「分组统计单个样本」彻底摆脱了对 batch size 的依赖，代价是失去了 BN 隐含的"
          "跨样本正则化效应（有时需要额外的正则手段补偿）。"),
        H3("为什么 Transformer 用 LayerNorm 而不是 BatchNorm"),
        DUAL(
            "直白说：NLP 里一个 batch 里的句子长度参差不齐（要靠 padding 对齐），BN 要沿着 batch+序列长度求统计量，"
            "会把大量 padding 的「假数据」也算进均值方差里，统计量被污染；而且推理时经常是单条句子逐个处理（batch=1），"
            "BN 的统计量根本没法算。LayerNorm 只看每个 token 自己那一份特征向量，跟 batch 里有几条句子、"
            "句子多长完全没关系，天然适配变长序列和小/变化的 batch。",
            "更深一层的原因是<strong>序列任务里「样本」这个概念本身模糊</strong>——是整个句子算一个样本，"
            "还是每个 token 算一个样本？BN 假设固定输入分布跨 batch 可比较，这个假设在变长序列、"
            "自回归逐 token 生成（推理时 batch 维度经常退化为 1，且长度随生成过程变化）的场景下并不成立；"
            "LN 把归一化收缩到「单个 token 自己的特征维度」，从根本上绕开了这个假设。"
            "这也是为什么 Vision Transformer 处理图像 patch 序列时同样沿用 LN 而非 BN——"
            "一旦数据被表示成「变长 token 序列」的形式，LN 几乎是默认选择。",
        ),
        CALLOUT("warn", "<strong>踩雷点</strong>：不要笼统地说「Transformer 用 LN 是因为效果更好」——"
                        "面试官会追问「效果好在哪」。要能具体说出<strong>不依赖 batch 维度</strong>这一条硬约束，"
                        "而不只是「经验上试出来的」。"),
    ])),

    # ============================================================== 5
    ("residual", "残差连接：梯度视角与集成视角", "".join([
        P("<strong>一句话定义</strong>：残差连接让每个模块学习「相对于输入的改变量」$F(x)$，"
          "而不是直接学习目标映射 $H(x)$，输出为 $y=x+F(x)$——一个恒等映射（什么都不学）此时对应 $F(x)=0$，"
          "这比让一整个非线性模块去逼近恒等映射容易得多。"),
        MATH("y = x + F(x) \\qquad \\Rightarrow \\qquad \\frac{\\partial L}{\\partial x} = "
             "\\frac{\\partial L}{\\partial y}\\Big(1 + \\frac{\\partial F}{\\partial x}\\Big)"),
        P("<strong>梯度视角</strong>：反向传播时梯度里多了一个恒为 1 的加性项——不管 $\\partial F/\\partial x$"
          "本身有多小（哪怕这个模块的雅可比接近 0，梯度消失），<strong>那个「+1」都能让梯度原封不动地传回上一层</strong>。"
          "把很多个残差块叠起来，相当于给梯度提供了一条从最后一层直达最前面几层的「高速公路」，"
          "这是残差网络能训练到上百层而不出现严重梯度消失的核心机制（呼应本课模块 02 的梯度消失一节）。"),
        DUAL(
            "直白说：不加残差时，网络要学的是「把输入变成输出」这整件事；加了残差，"
            "网络只需要学「输出比输入多了点什么」——如果这一层其实什么都不用做，"
            "它只要把自己训练成输出 0 就行，这比训练成一个精确的恒等函数容易得多"
            "（对一个非线性堆叠的模块来说，逼近「什么都不做」远比看起来简单）。",
            "更完整的图景来自 Veit et al. (2016) 提出的<strong>集成视角</strong>："
            "$n$ 个残差块堆叠展开后，等价于 $2^n$ 条不同长度路径的<em>隐式集成</em>（因为每个残差块的输出"
            "既可以走 $F(x)$ 这条支路也可以直接走 shortcut，堆叠起来路径数指数增长）。"
            "实验观察到<strong>移除单个残差块对整体性能的影响很小</strong>（不像移除普通深层网络的一层会导致灾难性下降），"
            "这与「许多短路径的集成，去掉一条影响有限」的直觉一致——这也是残差网络对深度的鲁棒性来源之一。",
        ),
        CALLOUT("intuition", "面试可以直接说的两句话：<strong>「残差连接从梯度视角看是给反向传播加了一条恒为 1 的直连通路，"
                             "从集成视角看是把深层网络变成了大量不同长度路径的隐式集成——这两个视角互补，"
                             "分别解释了为什么残差网络训得动（梯度）和为什么它对深度鲁棒（集成）。」</strong>"),
    ])),

    # ============================================================== 6
    ("attention-qkv", "注意力与 QKV：为什么要除以 √d_k、多头的作用", "".join([
        P("<strong>QKV 的直觉</strong>：对序列里的每个位置，用一个「查询」向量 $Q$ 去和所有位置的「键」向量 $K$"
          "做相似度匹配，匹配分数经过 softmax 归一化成权重，再用这组权重去加权求和所有位置的「值」向量 $V$——"
          "本质是一次<strong>可微的、内容驱动的软查表</strong>：$Q$ 是「我想找什么」，$K$ 是「每个位置能提供什么索引」，"
          "$V$ 是「每个位置实际携带的信息」。"),
        MATH("\\mathrm{Attention}(Q,K,V) = \\mathrm{softmax}\\!\\Big(\\frac{QK^\\top}{\\sqrt{d_k}}\\Big)V"),
        P("<strong>为什么要除以 $\\sqrt{d_k}$</strong>——这是本节最高频的追问，机制要能推到数字："
          "假设 $Q,K$ 的每个分量独立、均值 0、方差 1，$QK^\\top$ 的每个元素是 $d_k$ 个独立同分布乘积项之和，"
          "其方差是 $d_k$（标准差 $\\sqrt{d_k}$）——<strong>维度越高，点积的数值波动就越大</strong>。"
          "未缩放时，softmax 的输入分布过于分散，会让 softmax 输出<strong>趋于 one-hot（饱和）</strong>，"
          "而 softmax 在饱和区的梯度 $p(1-p)$ 趋于 0——<strong>梯度消失</strong>。除以 $\\sqrt{d_k}$ 把方差重新拉回 1，"
          "让 softmax 保持在梯度充分、信息未过度坍缩的「健康区间」。"),
        TABLE(["", "未缩放（$QK^\\top$）", "缩放后（$QK^\\top/\\sqrt{d_k}$）"], [
            ["分数标准差（$d_k{=}512$ 时实测）", "≈ 23.3（理论 $\\sqrt{512}\\approx22.6$）", "≈ 1.03（理论 ≈1）"],
            ["softmax 最大权重均值（20 个位置）", "≈ 0.95（接近 one-hot，饱和）", "≈ 0.20（接近均匀分布 $1/20{=}0.05$，健康）"],
            ["softmax 梯度尺度 $\\overline{p(1-p)}$", "≈ 0.0045", "≈ 0.045（约<strong>大 10 倍</strong>）"],
        ]),
        ASCII("""未缩放：分数分布很"宽" -> softmax 几乎是 one-hot -> 梯度几乎为0
  scores: [ -40  2  38 -15  ... ]  -> softmax: [0.00 0.00 1.00 0.00 ...]  <- 饱和

缩放后：分数分布收窄到 ~N(0,1) -> softmax 比较"软" -> 梯度健康
  scores: [ -1.8 0.1 1.7 -0.7 ... ] -> softmax: [0.03 0.19 0.35 0.09 ...]  <- 有区分度但不极端"""),
        H3("多头注意力的作用"),
        P("<strong>一句话定义</strong>：把 $d_{model}$ 维的 $Q,K,V$ 切成 $h$ 个更低维（$d_k{=}d_{model}/h$）的子空间，"
          "各自独立算一遍注意力再拼接——<strong>不是简单地重复计算 $h$ 次同一件事</strong>，"
          "而是让模型在<strong>不同的表示子空间里学习不同种类的「相关性模式」</strong>"
          "（比如一个头关注句法邻近关系，另一个头关注长距离共指关系）。"
          "计算量上，$h$ 个头总参数量与单头、$d_{model}$ 维时基本持平（每个头的维度按比例缩小），"
          "所以多头几乎是「免费」拿到的表示多样性。"),
        DUAL(
            "直白说：与其派一个人用全部精力盯着一种关系找线索，不如派好几个人，"
            "每人只负责盯一小块维度、找一种特定类型的线索，最后把各自的发现拼起来——"
            "总的「工作量」（参数量/计算量）差不多，但因为分工不同，能同时捕捉到更丰富的模式。",
            "需要澄清一个常见误解：多头不是<em>提高了模型容量</em>（参数量基本不变），"
            "而是<em>改变了归纳偏置</em>——强制模型在多个独立的低维子空间里分别学习注意力模式，"
            "这种「结构化的多样性」在实践中被证明比同样参数量的单头注意力效果更好，"
            "但这一点<strong>缺乏严格的理论证明，主要是经验结果</strong>（Michel et al. 2019 甚至发现"
            "训练好的模型里很多头可以被剪掉而不损失精度，说明并非所有头都在学「不同的东西」）。",
        ),
        CALLOUT("warn", "<strong>踩雷点</strong>：把「多头」说成「相当于集成学习」——这个类比不准确。"
                        "集成学习的多个模型通常独立训练/独立参数化且投票时相对独立；"
                        "多头共享同一次前向传播里的上下文，且各头的输出被拼接后<strong>共同</strong>经过下一层的线性变换再融合，"
                        "并不是简单投票或平均。"),
    ])),

    # ============================================================== 7
    ("positional-encoding", "位置编码三类做法与 O(n²) 的来源与缓解", "".join([
        P("Self-attention 本身是<strong>置换不变（permutation-invariant）</strong>的——"
          "打乱输入序列的顺序，注意力算出来的加权结果只是跟着重新排列，模型无法从注意力机制本身分辨「谁在前谁在后」。"
          "<strong>位置编码就是专门补上这条被置换不变性抹掉的信息</strong>。三类做法要能分清各自的假设与外推行为："),
        TABLE(["类型", "机制", "能否外推到训练时未见过的更长序列", "代表"], [
            ["<strong>固定正弦（sinusoidal）</strong>", "用不同频率的 sin/cos 函数直接算出每个位置的编码，无需学习", "<strong>可以</strong>——"
             "本质是一个连续函数，任意位置整数都能直接代入公式算出有限值", "Transformer 原论文"],
            ["<strong>可学习绝对位置嵌入</strong>", "为每个位置维护一个可训练的向量，本质是一张查找表", "<strong>不能</strong>——"
             "表的大小在训练时就固定了，超出表长的位置<em>根本没有对应的向量</em>", "BERT、早期 ViT"],
            ["<strong>相对/旋转位置编码（RoPE 等）</strong>", "把位置信息编码成对 $Q,K$ 的旋转变换，"
             "两个 token 的注意力分数只依赖<strong>相对位置差</strong>而非各自的绝对位置", "架构上没有硬性长度上限，"
             "外推行为通常优于前两者（但极长距离仍会有精度退化，需要额外的缩放技巧）", "GPT-NeoX、LLaMA 系列"],
        ]),
        P("notebook 会直接验证 RoPE 类方法最核心的性质：<strong>只要两个 token 的相对位置差相同，"
          "无论它们的绝对位置分别是 (5,8) 还是 (1005,1008)，旋转后的点积结果完全一致</strong>——"
          "这是一个精确的数学恒等式（旋转变换保持内积在相对旋转下不变），不是近似。"),
        H3("O(n²) 的来源与工程缓解"),
        P("Self-attention 需要计算<strong>每一对</strong>位置之间的相似度，$QK^\\top$ 是一个 $n\\times n$ 矩阵——"
          "序列长度翻倍，注意力矩阵的计算与显存占用变成 4 倍，这是长序列 Transformer"
          "（长文档、高分辨率图像 patch 序列、长时序感知帧序列）绕不开的瓶颈。"),
        TABLE(["缓解方向", "思路", "代价"], [
            ["<strong>稀疏/局部注意力</strong>（如 Swin 的窗口注意力）", "只在局部窗口内算全量注意力，窗口间靠位移/层级结构交换信息", "牺牲了一步到位的全局建模能力，需要多层堆叠才能达到全局感受野"],
            ["<strong>降采样/聚合 KV</strong>（如可变形注意力，见 C54-04）", "每个 query 只采样少量关键位置而非全部位置", "采样位置的选择本身需要额外学习，实现更复杂"],
            ["<strong>线性/核化注意力</strong>", "把 softmax 注意力近似成可以按 $O(n)$ 结合律重排计算的形式", "近似带来精度损失，需要在效率和精度之间权衡"],
            ["<strong>工程层面（FlashAttention 等）</strong>", "不改变数学定义，只优化显存读写模式（分块计算，避免把整个 $n\\times n$ 矩阵物化到显存）", "降低的是实际显存/延迟，<strong>理论 FLOPs 仍是 $O(n^2)$</strong>——"
             "这是常被混淆的一点：FlashAttention 优化的是常数因子和显存，不是渐近复杂度"],
        ]),
        DUAL(
            "直白说：注意力要让每个词都去看一眼所有其他词，词一多，「两两组合」的次数就爆炸式增长——"
            "这就是 $O(n^2)$ 的来源。省这个账无非两条路：要么让每个词少看几个（稀疏/局部/采样），"
            "要么换一种数学上不用真的算出「两两组合」矩阵的等价算法（线性注意力），"
            "要么干脆不改数学、只是把显存搬运安排得更聪明（FlashAttention）。",
            "需要区分<strong>渐近复杂度优化</strong>与<strong>常数因子/工程优化</strong>这两类完全不同的解法："
            "稀疏注意力、线性注意力改变的是复杂度阶数本身（$O(n^2)\\to O(n\\log n)$ 或 $O(n)$，"
            "但往往以精度或架构灵活性为代价）；FlashAttention 类工作<strong>不改变理论 FLOPs</strong>，"
            "只是通过分块计算、减少显存读写次数来降低实际墙钟时间——"
            "这也是为什么长上下文 LLM 既需要架构层面的稀疏化，<em>也</em>同时需要 FlashAttention 这类系统层优化，"
            "两者解决的是不同层面的问题，不能互相替代。",
        ),
        CALLOUT("intuition", "可以直接背的对照句：<strong>「$O(n^2)$ 来自每个 token 都要和其它所有 token 算一次相似度；"
                             "稀疏/线性注意力是从数学上少算或近似算这个 $n\\times n$ 矩阵；FlashAttention 是数学不变，"
                             "只优化显存搬运方式——前者降复杂度阶数，后者降常数因子，不是一回事。」</strong>"),
    ])),

    # ============================================================== 8
    ("cnn-vs-transformer", "CNN vs Transformer：归纳偏置与数据量的取舍", "".join([
        P("<strong>一句话定义归纳偏置</strong>：CNN 的卷积核在设计上就<em>预先假设</em>了"
          "「局部性」（一个像素只与邻域相关）和「平移不变性」（同一个卷积核在图像各处共享）；"
          "Transformer 的 self-attention 不做这些假设，任意两个位置都可以直接建立联系，"
          "位置关系需要完全靠数据学出来（位置编码只是提供了原始信号，不是强加约束）。"),
        TABLE(["维度", "CNN", "Transformer（ViT 等）"], [
            ["归纳偏置强度", "强（局部性+平移不变性内置在结构里）", "弱（几乎不内置先验，位置编码只提供信息不做约束）"],
            ["小数据表现", "<strong>更好</strong>——先验替代了部分数据需求", "<strong>更差</strong>——若无充分预训练/数据增强，容易欠拟合或过拟合到偏置信号"],
            ["大数据/大算力表现", "增益逐渐饱和", "<strong>随数据量/模型规模持续提升更明显</strong>（scaling 特性更好）"],
            ["长距离依赖建模", "需要堆很多层或用空洞卷积扩大感受野才能间接建模", "<strong>天然支持</strong>，任意两位置一步可达"],
            ["部署工程成熟度", "算子高度优化，量化/TensorRT 支持成熟（见 C60）", "attention 算子相对新，量化/边缘部署工具链仍在追赶"],
        ]),
        DUAL(
            "直白说：CNN 出厂自带一副「图像的物理直觉眼镜」——附近的像素更可能相关、同一个花纹不管出现在图像哪里都该被同样识别——"
            "这副眼镜在数据不够多的时候非常划算，因为很多东西不用从数据里重新学，直接是白送的。"
            "Transformer 不戴这副眼镜，一开始什么先验假设都没有，所以数据少的时候容易学偏；"
            "但数据一旦给得足够多，不戴眼镜反而能看到眼镜本身会遮挡的、不符合「局部/平移不变」假设的模式。",
            "这个权衡在 ViT 论文（Dosovitskiy et al. 2020）里有直接的实验证据：ViT 在 ImageNet-1k 规模的数据上"
            "从零训练不如同等规模的 CNN，但在 JFT-300M 这类超大规模数据预训练后反超——"
            "<strong>归纳偏置的价值本质上是「先验知识替代数据」的价值，数据越稀缺，先验越值钱；"
            "数据越充裕，先验反而可能变成限制模型发现「先验之外的真实模式」的枷锁</strong>。"
            "这也解释了工业界近年的一个折中路线——<span class=\"term\">混合架构</span>"
            "（CNN backbone 提特征 + Transformer 做全局融合/decoder，如 DETR 系，见 C54），"
            "用 CNN 的先验处理数据相对有限的下游任务，同时用 attention 补上 CNN 弱的长距离建模能力。",
        ),
        H3("参数量与显存的口算方法：一张可以直接套用的速查表"),
        TABLE(["要估算什么", "口算公式/锚点", "备注"], [
            ["模型参数占用显存", "参数量 $\\times$ 4 字节（fp32）或 $\\times$ 2 字节（fp16/bf16）", "1B 参数 fp32 ≈ 4GB，fp16 ≈ 2GB"],
            ["优化器状态占用（Adam）", "再加 参数量 $\\times$ 8 字节（$m,v$ 两份 fp32）", "Adam 训练时显存 ≈ 参数本身的 3 倍以上（权重+梯度+m+v）"],
            ["激活值显存（训练时反传需要）", "$\\approx$ batch × 层数 × 每层激活尺寸 × 4 字节，随 batch 和分辨率线性增长", "这是显存里最容易被低估的一块，尤其对高分辨率检测任务"],
            ["Attention 显存", "$O(n^2)$ 项：batch × heads × $n^2$ × 4 字节", "序列长度 $n$ 每翻倍，这一项翻 4 倍——长上下文显存爆炸的直接原因"],
        ]),
        CALLOUT("warn", "<strong>激活显存和 attention 的 $O(n^2)$ 显存，比参数本身的显存更容易被面试者忽略</strong>，"
                        "被问「这个模型训练需要多少显存」时，只报参数量对应的显存是不完整答案——"
                        "训练时真正的显存大头往往是参数+梯度+优化器状态+激活值四项之和，而不是参数本身。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("以下问题不会直接出现在一面里，但能帮你在「你还了解哪些新进展」这类开放追问里给出有厚度的回答。"),
        UL([
            "<strong>归纳偏置到底是不是必需品，还是可以完全用数据换回来？</strong>ViT 之后的一系列工作"
            "（ConvNeXt 把 CNN「Transformer 化」、MLP-Mixer 干脆去掉卷积和注意力只用 MLP）显示，"
            "在数据和算力足够时，很多「结构先验」的性能差距可以被规模抹平。<em>这引出一个尚无定论的问题：随着数据/算力持续增长，"
            "架构设计的边际价值是否会继续下降？</em>",
            "<strong>归一化是否还是必需的？</strong>近期一些工作探索去掉归一化层（用精心设计的初始化/残差缩放替代），"
            "在特定规模下取得了与带归一化相当的效果。<em>如果这条路线成熟，本模块「归一化家族」这一整节"
            "在几年后可能会被重写成「归一化的替代方案」。</em>",
            "<strong>线性注意力/状态空间模型（Mamba 等）能否真正替代 softmax 注意力？</strong>"
            "这类方法把 $O(n^2)$ 降到 $O(n)$，在长序列任务上展现出有竞争力的效果，"
            "但<em>它们在「上下文内检索/复制」这类需要精确访问任意历史位置的任务上是否存在系统性弱点，仍是活跃的研究问题。</em>",
            "<strong>有效感受野（ERF）与理论感受野的鸿沟能否被系统性缩小？</strong>大核卷积"
            "（如 RTMDet 的 5×5 depthwise，见 C53-03）、结构重参数化等工作都在朝这个方向努力，"
            "<em>但「多大的核、多深的网络」才是某个任务的最优组合，目前仍缺乏一个可泛化的理论指导，主要靠经验搜索。</em>",
            "<strong>混合架构的最优配比是多少？</strong>CNN 提特征 + Transformer 做全局融合的混合设计"
            "（检测里的 hybrid encoder，见 C53-04）已被证明有效，<em>但「哪些层该用卷积、哪些层该用注意力」"
            "这个设计空间目前主要靠经验试错，还没有成熟的自动化搜索方法能可靠给出答案。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Vaswani et al., <em>Attention Is All You Need</em>（2017）——"
                         "QKV、多头、位置编码的原始出处。"
                         "<strong>★</strong> He et al., <em>Deep Residual Learning for Image Recognition</em>（2015）与 "
                         "Veit et al., <em>Residual Networks Behave Like Ensembles of Relatively Shallow Networks</em>（2016，"
                         "集成视角出处）。"
                         "<strong>★</strong> Wu & He, <em>Group Normalization</em>（2018）——本节 BN 小 batch 问题与 GN 动机的直接出处。"
                         "<strong>★</strong> Ioffe & Szegedy, <em>Batch Normalization</em>（2015）；Ba et al., "
                         "<em>Layer Normalization</em>（2016）。"
                         "<strong>★</strong> Howard et al., <em>MobileNets</em>（2017，深度可分离卷积）；"
                         "Wang et al., <em>Understanding Convolution for Semantic Segmentation</em>（2018，"
                         "本节 gridding artifact 与 HDC 方案的出处）；Odena et al., <em>Deconvolution and Checkerboard "
                         "Artifacts</em>（2016）。"
                         "<strong>★</strong> Dosovitskiy et al., <em>An Image is Worth 16x16 Words</em>（2020，ViT）；"
                         "Su et al., <em>RoFormer</em>（2021，RoPE 出处）；Dao et al., <em>FlashAttention</em>（2022）。</p>"
                         "<p>配套材料：Michel et al., <em>Are Sixteen Heads Really Better than One?</em>（2019，"
                         "多头冗余性的实证）；Liu et al., <em>Swin Transformer</em>（2021，窗口注意力）。"
                         "卷积反向传播与感受野的完整数学推导见 <strong>C18 模块 02-03</strong>；"
                         "Transformer 完整结构与训练细节见 <strong>C00 模块 01/03</strong>；"
                         "大核卷积的有效感受野实测见 <strong>C53 模块 03</strong>；"
                         "可变形注意力与 object query 见 <strong>C54 模块 03-04</strong>。"
                         "相邻模块：<strong>C64-02</strong>（优化与训练问答）、<strong>C64-04</strong>（评估、概率与统计问答）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · 深度学习架构问答（卷积口算 / 1×1与深度可分离 / gridding / BN小batch / attention √d_k / 位置编码外推）

目标：把「说说卷积和 Transformer 的区别」这类问题，从背概念变成**能亲手算出数字来支撑答案**。

本 notebook 你会亲手实现并验证：
1. **参数量/FLOPs 计算器 + 感受野递推**，对照真实 backbone 的层配置校验
2. **1×1 卷积三作用**的数值演示（bottleneck 参数节省的具体倍数）与**深度可分离卷积**的收益公式
3. **空洞卷积的 gridding artifact**：用集合论证明"某些像素永远不会被采样到"
4. **BN vs GroupNorm 在小 batch 下的统计稳定性**对比（含 GN=LN/IN 特例的验证）
5. **从零实现 scaled dot-product attention**，用数值实验验证 $\\sqrt{d_k}$ 缩放的必要性
6. **三类位置编码的外推行为**对比（固定正弦 / 可学习绝对 / 类 RoPE 相对）

> 心智模型：**架构问答的"追问陷阱"几乎都藏在一个可以用 20 行 numpy 复现的具体数字里——本 notebook 就是把这些数字都跑出来。**"""),

    md("""## 0 · 环境自检"""),

    code("""import sys
import numpy as np

print('Python:', sys.version.split()[0])
print('numpy :', np.__version__)
assert sys.version_info >= (3, 8)
rng = np.random.default_rng(0)
print('\\n✅ 环境自检通过：本课全程 numpy + 标准库，无需 GPU，不联网。')"""),

    md("""## 1 · 参数量、FLOPs 与感受野递推：对照真实 backbone 校验"""),

    code("""def conv_params(cin, cout, k, bias=False):
    p = k * k * cin * cout
    return p + cout if bias else p

def conv_macs(cin, cout, k, hout, wout):
    return k * k * cin * cout * hout * wout

def out_size(hin, k, s, p):
    return (hin + 2 * p - k) // s + 1

# ResNet 系列的 stem 层：7x7, Cin=3, Cout=64, stride=2, pad=3，输入 224x224（无 bias，后接 BN）
p_stem = conv_params(3, 64, 7, bias=False)
h_out = out_size(224, 7, 2, 3)
macs_stem = conv_macs(3, 64, 7, h_out, h_out)

print(f'ResNet stem conv1: 参数量={p_stem:,}  输出分辨率={h_out}x{h_out}  MACs={macs_stem:,}  FLOPs(=2xMACs)={2*macs_stem:,}')
assert p_stem == 9408, 'ResNet conv1 是一个广为人知的校验数字：7*7*3*64=9408'
assert h_out == 112
assert macs_stem == 118_013_952
print('\\n✅ 与公开资料里 ResNet conv1 的参数量/MACs 数字一致，说明公式没写错。')"""),

    code("""def receptive_field(layers):
    \"\"\"layers: [(k, s), ...] -> [(RF, jump), ...]，RF_0=1, jump_0=1。\"\"\"
    rf, jump = 1, 1
    out = [(rf, jump)]
    for k, s in layers:
        rf = rf + (k - 1) * jump
        jump = jump * s
        out.append((rf, jump))
    return out

# 三层 3x3 stride1 堆叠 == 一个 7x7 卷积的感受野（VGG 论文的经典论证）
seq = receptive_field([(3, 1), (3, 1), (3, 1)])
print('三层 3x3 s1 堆叠的 RF 序列:', seq)
assert seq[-1][0] == 7, '三层 3x3 堆叠应等价一个 7x7 卷积的感受野'

# 参数量对比：三层 3x3 堆叠 vs 一个 7x7，同样感受野
p_stack = 3 * conv_params(64, 64, 3)
p_single = conv_params(64, 64, 7)
print(f'三层 3x3 堆叠参数量: {p_stack:,}   单层 7x7 参数量: {p_single:,}   节省比例: {1 - p_stack/p_single:.2%}')
assert p_stack < p_single

# ResNet stem + maxpool + 两层 3x3：验证感受野随层数增长
seq2 = receptive_field([(7, 2), (3, 2), (3, 1), (3, 1)])
print('ResNet stem(7x7,s2) + pool(3x3,s2) + 两层3x3(s1) 的 RF 序列:', seq2)
assert seq2[-1][0] == 27
print('\\n✅ 验证：感受野递推公式在真实层配置下算得出确定的数字，可以在白板上现推。')"""),

    md("""## 2 · 1×1 卷积三作用 + 深度可分离卷积的收益公式"""),

    code("""# ---- 1x1 卷积不贡献感受野（作用①：只做通道变换，不做空间混合）----
rf_before = receptive_field([(3, 1)])[-1]
rf_after_1x1 = receptive_field([(3, 1), (1, 1)])[-1]
print('叠加 3x3 后的 RF:', rf_before, '  再叠加 1x1 后的 RF:', rf_after_1x1)
assert rf_before[0] == rf_after_1x1[0], '1x1 卷积(k=1)不应改变感受野'

# ---- bottleneck (256->64->64->256) vs 两层 3x3 堆叠 (256->256->256) ----
bott = conv_params(256, 64, 1) + conv_params(64, 64, 3) + conv_params(64, 256, 1)
plain = conv_params(256, 256, 3) + conv_params(256, 256, 3)
print(f'\\nBottleneck(1x1+3x3+1x1) 参数量: {bott:,}')
print(f'两层 3x3 堆叠(256->256->256) 参数量: {plain:,}')
print(f'比例: {bott/plain:.4f}  (节省 {plain/bott:.1f} 倍)')
assert bott / plain < 0.1, 'bottleneck 应把参数量压到 plain 设计的 10% 以下'

# ---- 深度可分离卷积: 参数比例 = 1/Cout + 1/k^2 ----
def depthwise_separable_params(cin, cout, k):
    dw = k * k * cin
    pw = cin * cout
    return dw + pw, dw, pw

cin = cout = 256; k = 3
std_p = conv_params(cin, cout, k)
dsp_p, dw_p, pw_p = depthwise_separable_params(cin, cout, k)
print(f'\\n标准卷积参数量: {std_p:,}')
print(f'深度可分离参数量: {dsp_p:,} (depthwise={dw_p:,} + pointwise={pw_p:,})')
print(f'比例: {dsp_p/std_p:.4f}   公式 1/Cout+1/k^2 = {1/cout + 1/(k*k):.4f}')
assert abs(dsp_p / std_p - (1 / cout + 1 / (k * k))) < 1e-9
print('\\n✅ 验证：1x1 卷积不贡献感受野；bottleneck 省参数 ~17 倍；深度可分离卷积压缩比例精确等于 1/Cout+1/k^2。')"""),

    md("""## 3 · 空洞卷积的 gridding artifact：集合论证明"有些像素永远采样不到\""""),

    code("""def sumset_after_layers(dilations, k=3):
    \"\"\"k=3 核在膨胀率 r 下采样偏移量为 {-r,0,r}；多层堆叠的可达偏移量是各层偏移集合的 Minkowski 和。\"\"\"
    offsets_per_layer = [(-r, 0, r) for r in dilations]
    reachable = {0}
    for offs in offsets_per_layer:
        reachable = {a + b for a in reachable for b in offs}
    return reachable

const_dilation = sumset_after_layers([2, 2, 2])
hdc_dilation = sumset_after_layers([1, 2, 5])

all_positions_const = set(range(min(const_dilation), max(const_dilation) + 1))
gaps_const = sorted(all_positions_const - const_dilation)
all_positions_hdc = set(range(min(hdc_dilation), max(hdc_dilation) + 1))
gaps_hdc = sorted(all_positions_hdc - hdc_dilation)

print('恒定 dilation=(2,2,2): 可达偏移量=', sorted(const_dilation))
print('  理论感受野范围:', min(const_dilation), '~', max(const_dilation))
print('  从未被采样到的位置(gridding 空洞):', gaps_const, ' 空洞数=', len(gaps_const))
print()
print('HDC dilation=(1,2,5): 可达偏移量=', sorted(hdc_dilation))
print('  从未被采样到的位置:', gaps_hdc, ' 空洞数=', len(gaps_hdc))

assert len(gaps_const) == 6, '恒定膨胀率下，理论感受野内应有 6 个位置从未被采样到'
assert len(gaps_hdc) == 0, 'HDC (1,2,5) 方案应完全覆盖理论感受野，零空洞'
print('\\n✅ 验证：连续用同一膨胀率会在理论感受野内留下规律性空洞；HDC 的锯齿膨胀率方案能补上这些空洞。')"""),

    md("""## 4 · BN vs GroupNorm 在小 batch 下的统计稳定性"""),

    code("""C, H, W = 16, 8, 8
eps = 1e-5
x_target = rng.standard_normal((C, H, W)).astype(np.float64)   # 固定的目标样本，反复塞进不同 batch

def sample_other(r):
    \"\"\"80% 概率是普通样本 N(0,1)，20% 概率是"离群样本"(比如夜间强噪声帧)，方差大 10 倍。\"\"\"
    if r.random() < 0.2:
        return r.standard_normal((C, H, W)) * np.sqrt(10.0)
    return r.standard_normal((C, H, W))

def bn_normalize_target(batch):
    \"\"\"batch: (N,C,H,W)，第0个是 target。返回 target 的 BN 输出在各通道上的空间均值 (C,)。\"\"\"
    mean = batch.mean(axis=(0, 2, 3))
    var = batch.var(axis=(0, 2, 3))
    normed = (batch[0] - mean[:, None, None]) / np.sqrt(var[:, None, None] + eps)
    return normed.mean(axis=(1, 2))

T = 200
bn_vars = {}
for N in [2, 4, 8, 32, 128]:
    outs = []
    for _ in range(T):
        others = np.stack([sample_other(rng) for _ in range(N - 1)], axis=0) if N > 1 else np.zeros((0, C, H, W))
        batch = np.concatenate([x_target[None], others], axis=0)
        outs.append(bn_normalize_target(batch))
    outs = np.array(outs)
    bn_vars[N] = outs.var(axis=0).mean()
    print(f'N={N:>4}  BN 输出方差(跨 batch 组成) = {bn_vars[N]:.6f}')

Ns = [2, 4, 8, 32, 128]
assert all(bn_vars[Ns[i]] > bn_vars[Ns[i+1]] for i in range(len(Ns)-1)), 'BN 的统计不稳定性应随 batch 增大而单调下降'
assert bn_vars[2] / bn_vars[128] > 10, '小 batch 的抖动应比大 batch 明显大一个数量级以上'
print('\\n✅ 验证：BN 统计量的抖动随 batch size 减小而急剧增大——这正是检测/分割任务小 batch 下 BN 出问题的数值证据。')"""),

    code("""def groupnorm_forward(x, num_groups, eps=1e-5):
    \"\"\"x: (C,H,W)，单个样本，与 batch 里其他样本完全无关。\"\"\"
    C_, H_, W_ = x.shape
    G = num_groups
    s = x.reshape(G, C_ // G, H_, W_)
    mean = s.mean(axis=(1, 2, 3), keepdims=True)
    var = s.var(axis=(1, 2, 3), keepdims=True)
    return ((s - mean) / np.sqrt(var + eps)).reshape(C_, H_, W_)

def layernorm_forward(x, eps=1e-5):
    mean = x.mean()
    var = x.var()
    return (x - mean) / np.sqrt(var + eps)

def instancenorm_forward(x, eps=1e-5):
    \"\"\"逐通道，只在 (H,W) 上统计。\"\"\"
    mean = x.mean(axis=(1, 2), keepdims=True)
    var = x.var(axis=(1, 2), keepdims=True)
    return (x - mean) / np.sqrt(var + eps)

# GN 的可复现性：与 batch 组成无关
gn_out1 = groupnorm_forward(x_target, num_groups=4)
gn_out2 = groupnorm_forward(x_target, num_groups=4)
assert np.allclose(gn_out1, gn_out2), 'GN 只依赖自身样本，重复计算必须完全一致'

# GN 的两个特例：G=1 等价 LN；G=C 等价 IN
gn_g1 = groupnorm_forward(x_target, num_groups=1)
ln_out = layernorm_forward(x_target)
gn_gC = groupnorm_forward(x_target, num_groups=C)
in_out = instancenorm_forward(x_target)

assert np.allclose(gn_g1, ln_out, atol=1e-9), 'G=1 时 GroupNorm 应完全等价于 LayerNorm'
assert np.allclose(gn_gC, in_out, atol=1e-9), 'G=C 时 GroupNorm 应完全等价于 InstanceNorm'
print('GN(G=1) 与 LN 是否完全一致:', np.allclose(gn_g1, ln_out, atol=1e-9))
print('GN(G=C) 与 IN 是否完全一致:', np.allclose(gn_gC, in_out, atol=1e-9))
print('\\n✅ 验证：GroupNorm 是 LN(G=1) 与 IN(G=C) 的一般化，且对 batch 组成完全不敏感（方差恒为0）。')"""),

    md("""## 5 · 从零实现 Scaled Dot-Product Attention：验证 √d_k 缩放的必要性"""),

    code("""def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def scaled_dot_product_attention(Q, K, V, scale=True):
    d_k = Q.shape[-1]
    scores = Q @ K.T
    if scale:
        scores = scores / np.sqrt(d_k)
    weights = softmax(scores, axis=-1)
    return weights @ V, weights

n, d_k = 20, 512
r2 = np.random.default_rng(0)
Q = r2.standard_normal((n, d_k))
K = r2.standard_normal((n, d_k))
V = r2.standard_normal((n, d_k))

out_unscaled, w_unscaled = scaled_dot_product_attention(Q, K, V, scale=False)
out_scaled, w_scaled = scaled_dot_product_attention(Q, K, V, scale=True)

raw_scores = Q @ K.T
scaled_scores = raw_scores / np.sqrt(d_k)

print('未缩放 QK^T 分数 std:', raw_scores.std(), '  理论 sqrt(d_k)=', np.sqrt(d_k))
print('缩放后分数 std      :', scaled_scores.std(), '  理论 ~1')

max_p_unscaled = w_unscaled.max(axis=-1).mean()
max_p_scaled = w_scaled.max(axis=-1).mean()
print('未缩放 softmax 最大权重均值(越接近1越"饱和"):', max_p_unscaled)
print('缩放后   softmax 最大权重均值:', max_p_scaled)

grad_scale_unscaled = (w_unscaled * (1 - w_unscaled)).mean()
grad_scale_scaled = (w_scaled * (1 - w_scaled)).mean()
print('未缩放 softmax 梯度尺度 mean(p(1-p)):', grad_scale_unscaled)
print('缩放后   softmax 梯度尺度 mean(p(1-p)):', grad_scale_scaled)

assert np.allclose(weights_sum := w_scaled.sum(axis=-1), np.ones(n)), '每行注意力权重必须归一化到 1'
assert raw_scores.std() > 15, '未缩放分数的标准差应接近 sqrt(d_k)（明显偏大）'
assert scaled_scores.std() < 2.0, '缩放后分数标准差应回落到接近 1'
assert max_p_unscaled > 0.7, '未缩放时 softmax 应明显饱和（接近 one-hot）'
assert max_p_scaled < 0.4, '缩放后 softmax 应保持较"软"的分布'
assert grad_scale_scaled > grad_scale_unscaled * 5, '缩放后 softmax 的梯度尺度应显著大于未缩放（至少 5 倍）'
print('\\n✅ 验证：不除以 sqrt(d_k)，分数方差随维度线性增长导致 softmax 饱和、梯度趋于消失；'
      '缩放后梯度尺度恢复了约 10 倍。')"""),

    md("""## 6 · 三类位置编码的外推行为对比"""),

    code("""d_pe = 8  # 偶数，RoPE 按 2 维一组旋转

def sinusoidal_pe(pos, d=8, base=10000.0):
    i = np.arange(d)
    angle = pos / (base ** (2 * (i // 2) / d))
    pe = np.zeros(d)
    pe[0::2] = np.sin(angle[0::2])
    pe[1::2] = np.cos(angle[1::2])
    return pe

def rope(x, pos, base=10000.0):
    d = x.shape[-1]
    out = x.copy()
    for j in range(0, d, 2):
        theta = pos / (base ** (j / d))
        c, s = np.cos(theta), np.sin(theta)
        x0, x1 = x[j], x[j + 1]
        out[j] = x0 * c - x1 * s
        out[j + 1] = x0 * s + x1 * c
    return out

# ① 固定正弦：任意 pos 都能直接算，即便远超训练时见过的最大长度
pe_far = sinusoidal_pe(100_000, d_pe)
assert np.all(np.isfinite(pe_far)), '正弦位置编码在超远位置仍应给出有限值'
print('sinusoidal PE 在 pos=100000 处依然可算，示例:', pe_far[:4])

# ② 可学习绝对位置嵌入：固定表，超出训练时的最大长度直接不存在
max_len = 512
learned_table = rng.standard_normal((max_len, d_pe)) * 0.02
try:
    _ = learned_table[100_000]
    can_extrapolate = True
except IndexError:
    can_extrapolate = False
print('learned absolute PE 能否直接取到 pos=100000 的向量:', can_extrapolate)
assert can_extrapolate is False, '可学习绝对位置编码架构上就不支持超出表长的位置'

# ③ 类 RoPE：只依赖相对位置差，即便绝对位置远超"训练范围"也精确成立
r3 = np.random.default_rng(1)
q_vec, k_vec = r3.standard_normal(d_pe), r3.standard_normal(d_pe)
dot_near = rope(q_vec, 5) @ rope(k_vec, 8)          # 相对位置差 = 3
dot_far = rope(q_vec, 1005) @ rope(k_vec, 1008)     # 相对位置差同样 = 3，但绝对位置远超常见训练长度
dot_diff_offset = rope(q_vec, 5) @ rope(k_vec, 9)   # 相对位置差 = 4，应该给出不同的点积

print(f'RoPE: 相对位置差=3 时 dot(近)={dot_near:.6f}  dot(远)={dot_far:.6f}  是否几乎相等: {np.isclose(dot_near, dot_far, atol=1e-8)}')
print(f'RoPE: 相对位置差=4 时 dot={dot_diff_offset:.6f}  (应与上面不同)')

assert np.isclose(dot_near, dot_far, atol=1e-8), 'RoPE 的点积应严格只依赖相对位置差，与绝对位置无关'
assert not np.isclose(dot_near, dot_diff_offset, atol=1e-4), '相对位置差不同时，点积应不同'
print('\\n✅ 验证：三类位置编码里，只有固定正弦与类 RoPE 能"算"到训练时未见过的位置；'
      '可学习绝对位置编码架构上有硬性长度上限；RoPE 的相对不变性是精确的数学恒等式，不是近似。')"""),

    md("""## ✏️ 练习 1：卷积参数量与 FLOPs 计算器

实现 `conv_flops_and_params(cin, cout, k, hout, wout, bias=False)`，
返回 `(params, macs, flops)`，其中 `flops = 2 * macs`。"""),

    code("""def conv_flops_and_params(cin, cout, k, hout, wout, bias=False):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
params, macs, flops = conv_flops_and_params(3, 64, 7, 112, 112, bias=False)
assert params == 9408, params
assert macs == 118_013_952, macs
assert flops == 2 * macs
params2, macs2, flops2 = conv_flops_and_params(64, 64, 3, 56, 56, bias=True)
assert params2 == 3 * 3 * 64 * 64 + 64
assert macs2 == 3 * 3 * 64 * 64 * 56 * 56
print(f'ResNet conv1: params={params:,}  MACs={macs:,}  FLOPs={flops:,}')
print(f'3x3(64->64,56x56,带bias): params={params2:,}  MACs={macs2:,}  FLOPs={flops2:,}')
print('✅ 练习 1 通过。')"""),

    md("""## ✏️ 练习 2：带膨胀率的感受野递推

实现 `receptive_field_dilated(layers)`，`layers` 元素为 `(k, s, dilation)`。
膨胀率为 $d$ 时，核的"有效跨度"变成 $k_{\\text{eff}} = k + (k-1)(d-1)$，
其余递推与普通感受野公式完全一样（用 $k_{\\text{eff}}$ 替换 $k$）。"""),

    code("""def receptive_field_dilated(layers):
    # TODO: 返回 [(RF, jump), ...]，RF_0=1, jump_0=1
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
# 膨胀率恒为1时应退化为普通感受野公式
seq_d1 = receptive_field_dilated([(3, 1, 1), (3, 1, 1), (3, 1, 1)])
assert seq_d1[-1][0] == 7, seq_d1

# 单层 3x3, dilation=2: k_eff = 3+(3-1)*(2-1) = 5, RF = 1+(5-1)*1 = 5
seq_d2 = receptive_field_dilated([(3, 1, 2)])
assert seq_d2[-1][0] == 5, seq_d2

# 三层 3x3, dilation 分别为 1,2,5 (HDC): 逐层核跨度为 3,5,11
seq_hdc = receptive_field_dilated([(3, 1, 1), (3, 1, 2), (3, 1, 5)])
print('HDC (1,2,5) 三层的 RF 序列:', seq_hdc)
assert seq_hdc[-1][0] == 1 + 2 + 4 + 10   # 1 + (3-1) + (5-1) + (11-1) = 17
print('✅ 练习 2 通过：膨胀率通过"有效跨度"进入同一套感受野递推公式。')"""),

    md("""## ✏️ 练习 3：GroupNorm 与 LN / IN 的等价关系

实现 `is_gn_equivalent_to(x, kind)`，`kind` 为 `'ln'` 或 `'in'`：
用 `groupnorm_forward` 分别以 `num_groups=1`（应等价 LN）和 `num_groups=C`（应等价 IN）计算，
返回布尔值表示是否与对应的参考实现（`layernorm_forward` / `instancenorm_forward`）数值一致。"""),

    code("""def is_gn_equivalent_to(x, kind):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert is_gn_equivalent_to(x_target, 'ln') is True
assert is_gn_equivalent_to(x_target, 'in') is True
x_other = rng.standard_normal((C, H, W))
assert is_gn_equivalent_to(x_other, 'ln') is True   # 对任意样本都应成立，不是只对 x_target 恰好成立
print('✅ 练习 3 通过：GroupNorm(G=1)==LayerNorm，GroupNorm(G=C)==InstanceNorm，对任意输入恒成立。')"""),

    md("""## ✏️ 练习 4：从零实现并验证 Scaled Dot-Product Attention 的基本性质

实现 `attention_row_stochastic_check(Q, K, V, scale=True)`，
复用第 5 节的 `scaled_dot_product_attention`，返回 `(weights 每行和是否都为1, 输出形状是否等于V的形状)`
两个布尔值。"""),

    code("""def attention_row_stochastic_check(Q, K, V, scale=True):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
r4 = np.random.default_rng(2)
Qs, Ks, Vs = r4.standard_normal((7, 16)), r4.standard_normal((7, 16)), r4.standard_normal((7, 16))
rows_ok, shape_ok = attention_row_stochastic_check(Qs, Ks, Vs, scale=True)
assert rows_ok is True
assert shape_ok is True
rows_ok2, shape_ok2 = attention_row_stochastic_check(Qs, Ks, Vs, scale=False)
assert rows_ok2 is True, '不管缩不缩放，softmax 输出都必须每行归一化到 1'
print('✅ 练习 4 通过：无论是否缩放，注意力权重矩阵都必须行归一化，输出形状必须与 V 一致。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def conv_flops_and_params(cin, cout, k, hout, wout, bias=False):
    params = k * k * cin * cout + (cout if bias else 0)
    macs = k * k * cin * cout * hout * wout
    flops = 2 * macs
    return params, macs, flops"""),

    code("""# 练习 2 参考答案
def receptive_field_dilated(layers):
    rf, jump = 1, 1
    out = [(rf, jump)]
    for k, s, d in layers:
        k_eff = k + (k - 1) * (d - 1)
        rf = rf + (k_eff - 1) * jump
        jump = jump * s
        out.append((rf, jump))
    return out"""),

    code("""# 练习 3 参考答案
def is_gn_equivalent_to(x, kind):
    if kind == 'ln':
        C_ = x.shape[0]
        return bool(np.allclose(groupnorm_forward(x, num_groups=1), layernorm_forward(x), atol=1e-9))
    elif kind == 'in':
        C_ = x.shape[0]
        return bool(np.allclose(groupnorm_forward(x, num_groups=C_), instancenorm_forward(x), atol=1e-9))
    raise ValueError(kind)"""),

    code("""# 练习 4 参考答案
def attention_row_stochastic_check(Q, K, V, scale=True):
    out, weights = scaled_dot_product_attention(Q, K, V, scale=scale)
    rows_ok = bool(np.allclose(weights.sum(axis=-1), np.ones(weights.shape[0])))
    shape_ok = bool(out.shape == V.shape)
    return rows_ok, shape_ok"""),

    md("""---
## 🧪 真实工程胶囊：架构选型与常见踩雷速查"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 卷积口算速查（面试可直接背的版本）
# ══════════════════════════════════════════════════════════════════════
# 参数量  = k^2 * Cin * Cout                       (与分辨率无关)
# MACs    = 参数量 * Hout * Wout                    FLOPs = 2 * MACs
# RF_l    = RF_(l-1) + (k_l-1)*jump_(l-1)           jump_l = jump_(l-1)*s_l
# 1x1 卷积: k=1 时对 RF 无贡献，只做通道变换/混合/廉价加非线性
# 深度可分离: 参数比例 = 1/Cout + 1/k^2 （通常远小于1，但depthwise是访存受限，
#            实际部署加速比 < 理论 FLOPs 加速比）

# ══════════════════════════════════════════════════════════════════════
# B. 归一化选型速查
# ══════════════════════════════════════════════════════════════════════
# □ 分类/大 batch 训练           -> BatchNorm（训练用 batch 统计，推理用 running stats）
# □ 检测/分割/小 batch(1-4)       -> GroupNorm（或多卡 SyncBN）
# □ Transformer（任意模态）       -> LayerNorm（不依赖 batch 维度，变长序列友好）
# □ 风格迁移/需要保留单样本对比度   -> InstanceNorm
# 记忆锚点: GroupNorm(G=1)==LayerNorm, GroupNorm(G=C)==InstanceNorm

# ══════════════════════════════════════════════════════════════════════
# C. Attention 常见踩雷点
# ══════════════════════════════════════════════════════════════════════
# 坑1: 忘记除以 sqrt(d_k) -> 训练初期 loss 不降或直接 NaN（softmax 饱和梯度消失）
# 坑2: padding token 忘记 mask -> attention 会"看到"填充位置，注意力权重被污染
# 坑3: 可学习绝对位置编码 + 推理时序列变长 -> 直接 index out of range
# 坑4: FlashAttention 只优化显存/延迟常数，不改变 O(n^2) 的理论 FLOPs，
#      长序列的根本瓶颈仍需架构层面（稀疏/线性/窗口注意力）来解决

# ══════════════════════════════════════════════════════════════════════
# D. CNN vs Transformer 选型的一句话决策树
# ══════════════════════════════════════════════════════════════════════
# 数据量小 / 需要快速收敛 / 部署工具链要求成熟  -> CNN（或 CNN backbone + 轻量 attention）
# 数据量大 / 需要长距离建模 / 能接受更长训练与更新的部署工具链 -> Transformer / 混合架构
# TSR 等车载检测任务的现实选择通常是: CNN backbone 提特征 + 少量 attention 做跨尺度融合
# (呼应 C53 的 RTMDet/RT-DETR 混合设计)

# ══════════════════════════════════════════════════════════════════════
# E. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 卷积反向传播的完整数学推导                 -> C18 模块 02-03（本课不重复）
# · Transformer 完整结构与训练细节             -> C00 模块 01/03
# · 大核卷积的有效感受野实测、结构重参数化       -> C53 模块 01/03
# · 可变形注意力、object query、匈牙利匹配      -> C54 模块 01/03/04
# · 优化器、初始化、损失函数                   -> C64 模块 02（上一站）
'''
print(RECIPE)
for token in ['sqrt(d_k)', 'GroupNorm(G=1)', 'FlashAttention', 'C18 模块 02-03', 'C54 模块 01/03/04']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：卷积口算 / 归一化选型 / attention 踩雷 / CNN-Transformer 决策树 / 课程分工')"""),

    md("""### 小结

- **参数量只看卷积核和通道数，FLOPs 还要再乘输出分辨率**——这一句话就能接住"参数少但算力大"的追问。
  **1×1 卷积不贡献感受野**，它的价值在通道变换/混合/廉价加非线性；bottleneck 结构能把参数压到不到 1/10。
- **空洞卷积的膨胀率不能每层都一样**——连续用同一个膨胀率会在理论感受野内留下永远采不到的"棋盘空洞"，
  必须用锯齿状的膨胀率组合（如 1,2,5）填补。
- **归一化家族只有一个区别：在哪些维度上求统计量**。BN 依赖 batch 维度，小 batch/检测任务下统计量抖动剧烈；
  GroupNorm 是 LN(G=1) 与 IN(G=C) 的一般化，对 batch 组成完全不敏感——这是它替代 BN 的根本原因。
- **除以 $\\sqrt{d_k}$ 不是经验技巧，是精确的方差控制**：不缩放会让 softmax 饱和、梯度消失约 10 倍。
- **三类位置编码的外推行为完全不同**：可学习绝对编码架构上有硬性长度上限，固定正弦和类 RoPE 都能算到训练时未见过的位置，
  RoPE 的相对位置不变性是精确的数学恒等式。
- **CNN vs Transformer 的核心取舍是归纳偏置 vs 数据量**：先验知识在数据稀缺时值钱，在数据充裕时可能变成枷锁。

下一站：**模块 04 · 评估、概率与统计问答** —— 指标全家桶、校准、置信区间、A/B 测试与常见统计陷阱。"""),
]
