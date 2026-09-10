# -*- coding: utf-8 -*-
"""C77 模块 05 · 视频评测：FVD 的病理与运动口径。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00 第 5 节（逐帧特征对帧序完全免疫）；"
                 "模块 03（长视频指标必须报中位数 + 崩坏率）；"
                 "<strong>C14（评测与度量）</strong>提到过「文生图/视频评测要同时管"
                 "保真、多样、对齐与时序一致性」并把它列为开放问题——本课把时序那一半做完；"
                 "多元正态、Fréchet 距离的定义"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_video_eval.ipynb'
                       '（<strong>三个病理，每个都精确</strong>：'
                       '① 同分布之间的 FD <em>恒为正</em>且 $\\propto 1/N$'
                       '（$N$ 跨 $64$ 倍时系数稳定在 $0.560$–$0.566$）/ '
                       '② 对<strong>匹配前两阶矩</strong>的分布看不出差别'
                       '（$0.000587$ vs 同分布基线 $0.000603$，而峰度 $2.99$ vs $1.00$）/ '
                       '③ <strong>逐帧特征对帧序的敏感度是 $7.1\\times10^{-15}$</strong>'
                       '（机器精度），而时空特征是 $0.300$）'),
    ("核心参考", "Unterthiner et al., <em>Towards Accurate Generative Models of Video: "
                 "A New Metric &amp; Challenges</em>（2018/2019，FVD）· "
                 "Heusel et al., <em>GANs Trained by a Two Time-Scale Update Rule "
                 "Converge to a Local Nash Equilibrium</em>（NeurIPS 2017，FID）· "
                 "Chong &amp; Forsyth, <em>Effectively Unbiased FID and IS</em>"
                 "（CVPR 2020，有限样本偏差与 $\\text{FID}_\\infty$）· "
                 "Huang et al., <em>VBench</em>（CVPR 2024，把视频质量拆成 16 个维度）· "
                 "Ge et al., <em>On the Content Bias in Fréchet Video Distance</em>"
                 "（CVPR 2024，FVD 主要看内容而非运动）· "
                 "Kynkäänniemi et al., <em>Improved Precision and Recall Metric</em>"
                 "（NeurIPS 2019，把保真与多样分开）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [

("what", "FVD 是什么，以及它继承了什么", "".join([
    P("FVD 把每段视频过一个预训练的时空特征提取器，得到一个特征向量，"
      "然后对真实集合与生成集合各拟合一个多元正态，最后算两者的 <strong>Fréchet 距离</strong>："),
    MATH("d^2 = \\Vert \\mu_r - \\mu_g \\Vert^2 + "
         "\\text{tr}\\big(\\Sigma_r + \\Sigma_g - 2(\\Sigma_r \\Sigma_g)^{1/2}\\big)"),
    P("它是 FID 的直接搬运，所以<strong>继承了 FID 的全部性质</strong>——"
      "包括三个已知但常被忽略的病理。本模块把三个都量出来，"
      "并给出每一个的可操作对策。"),
    TABLE(["病理", "精确形式", "本课量出的值", "对策"],
          [["<strong>有限样本偏差</strong>", "同分布之间的 FD 恒为正，$\\propto 1/N$",
            "$N{=}64$ 时 $9.33$；$N{=}4096$ 时 $0.145$",
            "固定 $N$ 后才可比；或外推到 $N \\to \\infty$"],
           ["<strong>只看前两阶矩</strong>", "对任何同均值同协方差的分布给出 $\\approx 0$",
            "两点分布 vs 正态：$0.000587$（基线 $0.000603$）",
            "配 precision/recall 或 $k$-NN 类指标"],
           ["<strong>特征决定一切</strong>", "逐帧特征对帧序<em>结构性</em>免疫",
            "帧序置换后 FD $= 7.1\\times10^{-15}$",
            "对每个指标跑一次帧序置换检验"]]),
    CALLOUT("intuition", "为什么这三条值得单独学",
            "它们不是「FVD 不够准」，而是<strong>三种不同类型的失效</strong>："
            "第一个是<em>统计</em>问题（可以校正），"
            "第二个是<em>刻画能力</em>问题（只能靠补别的指标），"
            "第三个是<em>口径</em>问题（选错特征就完全没在评你想评的东西）。"
            "混为一谈会导致用错的对策。"),
])),

("bias", "病理一：同分布之间的 FVD 不是零", "".join([
    P("取两组来自<strong>完全相同</strong>分布的样本，算它们之间的 Fréchet 距离。"
      "真值显然是 $0$，而实测："),
    TABLE(["$N$", "FD 均值", "FD 中位数", "$d^2/N$（$d{=}32$）", "实测 / $(d^2/N)$"],
          [["$64$", "$9.3322$", "$9.3232$", "$16.000$", "$0.583$"],
           ["$128$", "$4.6564$", "$4.6417$", "$8.000$", "$0.582$"],
           ["$256$", "$2.3165$", "$2.3115$", "$4.000$", "$0.579$"],
           ["$512$", "$1.1580$", "$1.1615$", "$2.000$", "$0.579$"],
           ["$1024$", "$0.5773$", "$0.5782$", "$1.000$", "$0.577$"],
           ["$4096$", "$0.1447$", "$0.1445$", "$0.250$", "$0.579$"]]),
    P("<strong>$1/N$ 的标度是精确的</strong>：$N$ 跨 $64$ 倍，比值稳定在 $0.577$–$0.583$。"
      "而系数与特征维 $d$ 有关（实测从 $d{=}8$ 的 $0.85$ 漂到 $d{=}64$ 的 $0.54$），"
      "所以本课只断言 $1/N$ 律，$d$ 依赖给实测系数。"),
    CALLOUT("danger", "最常见的口径错误",
            "<strong>不同 $N$ 下的 FVD 不可比</strong>。"
            "「我们的 FVD 是 $180$，基线是 $210$」——"
            "如果两者的样本数不同，这个比较可能全部由有限样本偏差解释。"
            "而 $N{=}64$（视频评测里很常见，因为生成一段视频很贵）时"
            "的零假设值已经是 $9.33$（$d{=}32$）；"
            "在真实的 $d \\approx 400$ 的特征上，这个数会大得多。"),
    P("对策有两个。<strong>最低要求是固定 $N$</strong>（并在论文/报告里写出来）。"
      "更好的做法是 Chong &amp; Forsyth (2020) 的 $\\text{FID}_\\infty$："
      "在若干个 $N$ 上测，然后按 $1/N$ 外推到 $N \\to \\infty$——"
      "notebook 的练习 1 就是实现它，并验证外推后的偏差降到 $10^{-3}$ 量级。"),
])),

("moments", "病理二：只看前两阶矩", "".join([
    P("Fréchet 距离的定义里只出现 $\\mu$ 与 $\\Sigma$。"
      "所以<strong>任何两个同均值、同协方差的分布，FVD 都认为它们相同</strong>。"
      "这不是精度问题，是定义。"),
    P("notebook 构造一个极端例子：特征的第 $0$ 维"),
    UL(["分布 A：标准正态（连续、单峰、峰度 $2.99$）",
        "分布 B：$\\pm 1$ 的两点分布（离散、双峰、峰度 $1.00$）"]),
    P("两者的均值都是 $0$、方差都是 $1$。其余维度完全相同。结果："),
    CODE("A 的均值[0] = +0.00837, 方差[0] = 1.00319, 峰度[0] = 2.9901（正态 = 3）\n"
         "B 的均值[0] = -0.00364, 方差[0] = 0.99999, 峰度[0] = 1.0001（两点 = 1）\n\n"
         "两者的 Fréchet 距离     = 0.000587\n"
         "同分布 N=100000 的基线   = 0.000603"),
    P("<strong>FVD 认为「连续单峰」与「只有两个取值」是同一个分布</strong>"
      "（$0.000587 < 0.000603$，比同分布的基线还小）。"),
    CALLOUT("warn", "这直接对应一种真实失效",
            "「模式坍缩到几个离散模式」——生成器只会产出少数几种运动模式——"
            "是视频生成最常见的失效之一，而它<strong>恰好落在 FVD 的盲区里</strong>："
            "只要那几个模式的混合的一二阶矩对得上，FVD 就看不出来。"
            "所以 FVD 必须配一个能看到<em>更高阶结构</em>的指标："
            "precision/recall（Kynkäänniemi 2019）或 $k$-NN 类的覆盖度量。"
            "notebook 的练习 2 用一个最简的 $k$-NN 覆盖率把上面那个例子分开。"),
    DUAL("直觉：Fréchet 距离等价于「把两个分布都当成椭球，比较椭球」。"
         "椭球只由中心和形状决定，所以椭球内部<em>怎么填</em>它完全不管——"
         "均匀填、聚成几个团、还是只在表面上，都是同一个椭球。",
         "严格地说：FD 是 Wasserstein-2 距离在<strong>高斯族</strong>上的闭式。"
         "对一般分布 $P, Q$，$\\text{FD}(P,Q) = W_2(\\mathcal{N}(\\mu_P,\\Sigma_P), "
         "\\mathcal{N}(\\mu_Q,\\Sigma_Q))$，"
         "而这与 $W_2(P, Q)$ 一般<strong>不相等</strong>——"
         "前者只用到 $P$ 的二阶信息。"
         "所以「FVD 小」蕴含的是「二阶矩匹配」，不是「分布接近」。"),
])),

("features", "病理三：特征决定一切", "".join([
    P("前两个病理是 FID 家族共有的。第三个是视频<em>特有</em>的，而且最容易踩。"),
    P("notebook 取同一批视频，<strong>只把帧顺序打乱</strong>，然后算两组之间的 FD："),
    TABLE(["特征", "帧序置换后的 FD", "结论"],
          [["逐帧特征后对时间取平均", "$\\mathbf{7.1\\times10^{-15}}$",
            "<strong>结构性免疫</strong>（机器精度）"],
           ["含时间差分的时空特征", "$0.300$", "能看出帧序"]]),
    P("$7.1\\times10^{-15}$ 不是「不够敏感」，是<strong>恒等于零</strong>："
      "对时间取平均之后，帧的顺序在特征里<em>已经不存在了</em>。"
      "所以「用逐帧特征算出来的 FVD」根本不是在评测时间维——"
      "它是一个逐帧的 FID，只是名字里有个 V。"),
    H3("一个必须对每个视频指标跑一次的检验"),
    P("<strong>帧序置换检验</strong>：把同一批视频的帧顺序随机打乱，"
      "看指标变不变。变不了的指标，无论它用了多少帧，都不在评时间维。"),
    P("notebook 的练习 4 在五种特征上跑它，"
      "其中有一个刻意构造的陷阱：<strong>「对时间轴排序后再平均」</strong>——"
      "这个特征<em>用到了全部时间</em>（它排序了整段），"
      "却对帧序完全免疫（敏感度也是机器精度）。"),
    CALLOUT("paper", "所以判据不是「用了多少帧」",
            "常见的辩护是「我们的特征提取器是 3D 卷积/时空 Transformer，所以它当然看时间」。"
            "这个辩护不成立：<strong>网络结构能看时间，不代表最终特征里保留了帧序信息</strong>。"
            "上面那个「排序后平均」的例子就是一个纯粹的反例。"
            "唯一可靠的判据是<strong>把置换检验真的跑一遍</strong>——"
            "它只需要一批视频和一个随机置换，几行代码。"),
    P("Ge et al. (CVPR 2024) 从实证角度得到了同一方向的结论："
      "标准 FVD 主要反映<strong>单帧内容</strong>而不是运动，"
      "以至于用「打乱帧序的真实视频」都能拿到很好的 FVD。"
      "本节给出的是这个现象的<em>最小可复现核心</em>：一个恒等式。"),
])),

("alignment", "第四类问题：对齐与人评", "".join([
    P("前三节都在处理「生成分布 vs 真实分布」。而视频生成还有一整类评测问题"
      "在这个框架之外：<strong>生成的视频与提示是不是一回事</strong>。"),
    P("这一类的困难与前三节<em>正交</em>："
      "FVD 的三个病理都是「分布距离」的病理，"
      "而对齐问题里根本没有一个「真实分布」可比——"
      "给定一句提示，符合它的视频有无穷多种。"),
    TABLE(["评测目标", "有没有参考分布", "常用做法", "本课的处理"],
          [["保真（像不像真视频）", "有（真实视频集）", "FVD 及其变体",
            "本模块前三节"],
           ["多样（会不会坍缩）", "有", "覆盖率 / recall", "练习 2"],
           ["<strong>对齐（对不对提示）</strong>", "<strong>没有</strong>",
            "CLIP 类的文本-视频相似度；VQA 式提问", "本课不覆盖（需要真实模型）"],
           ["<strong>时序合理性</strong>", "弱（物理规律不是一个分布）",
            "分维度打分 / 人评", "本课不覆盖"]]),
    CALLOUT("warn", "对齐指标有一个与病理三同源的问题",
            "用「逐帧的图文相似度取平均」来量视频-文本对齐，"
            "在结构上与第 3 节的逐帧 FVD 是同一个错误——"
            "<strong>它对帧序免疫</strong>。"
            "「一个人坐下」与「一个人站起」的逐帧图文相似度均值几乎相同，"
            "而它们是相反的事件。"
            "所以第 3 节的<strong>帧序置换检验对对齐指标同样适用</strong>，"
            "而且更该跑——因为动词的方向性正是提示里最常出错的部分。"),
    H3("人评与自动指标的关系"),
    P("视频生成目前仍然以人评为最终裁判，而自动指标的作用是"
      "<strong>缩小搜索空间</strong>而不是替代人评。本课的三个病理给出这个分工的理由："),
    OL(["<strong>有限样本偏差</strong>让小差别不可分辨——"
        "而人评在小差别上恰恰更可靠（成对比较不受样本量偏差影响）；",
        "<strong>矩匹配盲区</strong>让模式坍缩看不见——"
        "而人只要看几十段就会注意到「怎么都差不多」；",
        "<strong>特征决定盲区</strong>意味着自动指标的口径必须被显式验证——"
        "而人评不需要（人看的就是视频本身）。"]),
    P("反过来，人评的问题是<strong>成本与一致性</strong>，"
      "所以现实的流程是：自动指标做粗筛（尤其是排除明显的崩坏，"
      "见模块 03 的崩坏率），人评做最终判定。"
      "<strong>而这个流程能不能工作，取决于自动指标的免疫范围有没有被写清楚</strong>——"
      "如果粗筛用的是一个对帧序免疫的指标，那么它筛掉的与人评关心的可能毫无关系。"),
    CALLOUT("paper", "本课在这一类上的边界",
            "对齐评测与人评都需要真实模型、真实提示与真实标注者，"
            "所以本课不覆盖。<strong>C14（评测与度量）</strong>处理评测方法论的一般问题"
            "（包括人评的一致性与自动指标的校准），"
            "而本课只把<em>时序</em>那一半做完："
            "给出一个可执行的判据（帧序置换检验）与三个病理的量化。"
            "这个分工是刻意的：帧序置换检验之所以值得单独学，"
            "正因为它<strong>不需要任何真实数据就能跑</strong>，"
            "而它能否决掉一大类看起来很时空的指标。"),
])),

("longvideo", "长视频评测的三个额外问题", "".join([
    P("前四节处理的是「一批固定长度的视频」。长视频（几十秒到几分钟）"
      "还有三个问题，而它们都不能靠「把 FVD 再算一遍」解决。"),
    H3("① 长度本身改变了指标"),
    P("FVD 在不同视频长度上<strong>不可比</strong>，理由与病理一同源："
      "更长的视频给特征提取器更多的时间上下文，"
      "于是特征分布本身变了。"
      "而更麻烦的是：<strong>生成更长的视频通常意味着更少的样本</strong>"
      "（算力固定），所以长度与 $N$ 同时变——"
      "两个混淆因素叠在一起。"),
    CALLOUT("warn", "一个必要的做法",
            "比较不同长度的生成时，<strong>把长视频切成固定长度的片段</strong>再算 FVD，"
            "并且明确说清切法（重叠？步长？只取开头？）。"
            "「只取开头」会系统性地偏向自回归模型（它们的前几段最好），"
            "而「均匀取样」会把崩坏样本的权重稀释掉——"
            "两种切法给出的排序可以相反。"),
    H3("② 两支失效需要分开报（模块 03）"),
    P("模块 03 量出：$a{=}0.98, n{=}50$ 时 rollout 方差的"
      "<strong>中位数是 $8.93$ 而均值是 $1.408\\times10^{14}$</strong>——差 $16$ 个数量级。"
      "在一批长视频上报<em>平均</em>任何指标都会被少数崩坏样本主导。"),
    P("所以长视频报告的最低要求是<strong>中位数 $+$ 崩坏率</strong>："
      "前者描述主体（模块 03 的「变静止」那一支），"
      "后者描述尾部（「指数爆炸」那一支）。"
      "而这两支的<em>症状相反</em>，所以任何单一的平均数都会把它们混成一个无意义的值。"),
    H3("③ 段间接缝"),
    P("层次化生成（模块 03 第 6 节）把长视频拼成段，"
      "于是产生了一类只在<strong>段边界</strong>出现的失效："
      "画面在边界处轻微跳变、运动在边界处不连续。"),
    P("而<strong>整段的 FVD 对它几乎不敏感</strong>："
      "如果一段 $128$ 帧的视频里有 $8$ 个边界，"
      "那么边界帧只占 $8/128 = 6\\%$，它们的贡献被稀释掉了。"
      "可操作的做法是<strong>专门在边界处采样</strong>："
      "取每个边界前后各 $2$ 帧，与「段内随机位置的同样数量的帧」对比，"
      "看两者的时间差分统计有没有系统性差别。"),
    CALLOUT("intuition", "三个问题的共同点",
            "它们都是<strong>「把一个数算在什么样本上」</strong>的问题，"
            "而不是「用哪个公式」的问题。"
            "这与本模块的三个病理形成对照：病理是公式的性质，"
            "而这三个是<em>采样口径</em>的性质。"
            "两类问题都不会报错，而后者更容易被忽略——"
            "因为公式没变，只是喂给它的样本变了。"),
])),

("checklist", "十个检查，全部不需要真实数据", "".join([
    P("把全课的可执行检查集中列一次。它们的共同点是"
      "<strong>只需要几行 numpy 和一批（可以是合成的）数据</strong>——"
      "不需要训练、不需要标注、不需要 GPU："),
    TABLE(["检查", "在哪", "输入", "它能否决什么"],
          [["$\\rho$ 的鲁棒估计", "m01 练习 1", "一批视频段",
            "「用全局常数压缩率」这个默认做法"],
           ["$p_t$ 的上限", "m01 练习 2", "$\\rho$、$T$、最长遮挡",
            "压过头的时间压缩（$\\rho_{\\text{eff}}<0.3$）"],
           ["流式代价", "m01 练习 3", "一批视频段",
            "「因果 tokenizer 会明显掉质量」这个担心"],
           ["码本的熵 $/\\log_2 K$", "m01 练习 4", "一批 latent",
            "用利用率判断坍缩"],
           ["Kronecker 秩", "m02 练习 2", "一个混合矩阵",
            "「多叠层/加残差能补回表达力」"],
           ["全局连通跳数", "m02 练习 4", "一个混合的非零模式",
            "「窗口和分解差不多」"],
           ["$\\rho(\\hat A)$", "m03 / m04", "学到的动力学",
            "任何用途（$>1$ 是硬否决）"],
           ["崩坏率 $+$ 中位数", "m03 练习 2", "一批 rollout",
            "报平均值"],
           ["批级平稳性", "m03 练习 4", "一批 rollout $+$ 一批真实序列",
            "把「不动点错」误判成「误差累积」"],
           ["帧序置换检验", "m05 练习 4", "一批视频 $+$ 一个置换",
            "任何对帧序免疫的「视频」指标"]]),
    P("十个检查里有<strong>四个</strong>会否决一条流行的做法或说法。"
      "而它们全部可以在拿到真实模型<em>之前</em>跑——"
      "只要有一个数据生成过程（哪怕是合成的）就够了。"),
])),

("closing", "五个模块的一张对照表", "".join([
    P("本课到此结束。把五个模块的核心结论并列一次，"
      "因为它们共享同一个形状："),
    TABLE(["模块", "那个便宜的近似", "精确的代价", "会不会报错"],
          [["01", "时间压缩 $p_t$", "$\\rho_{\\text{eff}} = \\rho^{p_t}$；latent 帧数 $T/p_t$",
            "不会"],
           ["01", "因果（流式）tokenizer", "$\\leq 3.3\\%$，峰值在中间相关性", "不会"],
           ["02", "分解式时空注意力", "Kronecker 秩 $1$——表示不了加速", "不会"],
           ["02", "串联接线（vs 并行）", "秩 $1$ vs $m^2{-}m{+}1$", "不会"],
           ["03", "一步拟合（教师强制）", "运动能量只有真值的 $35\\%$–$49\\%$", "不会"],
           ["03", "报平均而不是中位数", "均值被 $10\\%$ 的崩坏样本主导（差 $10^{16}$）", "不会"],
           ["04", "「一步准就是好模型」", "$3.95\\%$ 的一步误差 $\\to$ $251\\%$ 的回报高估", "不会"],
           ["04", "在训练分布上做诊断", "$g{=}0$ 时匹配与误配的曲线<em>逐点相同</em>", "不会"],
           ["05", "逐帧特征算 FVD", "帧序敏感度 $7.1\\times10^{-15}$", "不会"],
           ["05", "不同 $N$ 下比 FVD", "零假设值 $\\propto 1/N$（$N{=}64$ 时已是 $9.33$）", "不会"]]),
    P("最后一列全是「不会」。这不是巧合——"
      "<strong>会报错的近似早就被工程流程挡住了</strong>，"
      "剩下的正是这些安静地改变结果的。"),
    CALLOUT("paper", "所以本课的可交付物是什么",
            "不是「更好的模型」，也不是「更好的指标」，"
            "而是<strong>十个可以在几行 numpy 里重跑的检查</strong>："
            "$\\rho$ 的估计、$p_t$ 的上限、流式代价、码本的熵、"
            "Kronecker 秩、全局连通跳数、$\\rho(\\hat A)$、崩坏率、"
            "批级平稳性、帧序置换检验。"
            "每一个都不需要真实数据或训练，"
            "而每一个都能否决掉一类「看起来没问题」的配置。"),
])),

("bridge05", "三个病理的类型不同", "".join([
    P("在给对策之前重申一次：三个病理是<strong>三种不同类型</strong>的失效。"
      "有限样本偏差是<em>统计</em>问题（可以校正，练习 1）；"
      "矩匹配盲区是<em>刻画能力</em>问题（只能靠补别的指标，练习 2）；"
      "而特征决定盲区是<em>口径</em>问题（选错特征就完全没在评你想评的东西，练习 4）。"
      "混为一谈会导致用错的对策——例如用「加大 $N$」去修一个口径问题。"),
])),

("what_to_do", "该怎么评：把一个数拆成一组", "".join([
    P("三个病理各自否掉了「用单个 FVD 数字做决策」的一部分理由。"
      "把对策合起来，一份视频生成的评测报告至少要有五项："),
    TABLE(["项", "量什么", "为什么不能省", "本课的方法"],
          [["① 固定 $N$ 的 FVD 或 $\\text{FVD}_\\infty$", "整体分布距离",
            "$N$ 不同则不可比（病理一）", "练习 1 的 $1/N$ 外推"],
           ["② 覆盖度 / recall", "生成是否覆盖了真实的模式",
            "FVD 对模式坍缩免疫（病理二）", "练习 2 的 $k$-NN 覆盖率"],
           ["③ <strong>帧序置换检验</strong>", "指标到底在不在评时间维",
            "逐帧特征的敏感度是机器精度（病理三）", "练习 4"],
           ["④ 中位数 + 崩坏率", "长视频的两支失效",
            "均值会被崩坏样本主导（模块 03 的 $1.4\\times10^{14}$）", "模块 03 练习 2"],
           ["⑤ 分维度打分", "运动幅度 / 时序一致 / 对齐 / 保真 各自的分",
            "一个数无法同时表达四个正交的性质", "VBench 一类的做法"]]),
    P("第 ⑤ 项是 VBench 这类工作的动机：<strong>把一个数拆成一组</strong>。"
      "本课不复现那套基准（它需要真实模型与人工标注），"
      "但前四项都是可以在纯 numpy 上实现并断言的——这正是本模块 notebook 的内容。"),
    CALLOUT("intuition", "本课的最后一句",
            "五个模块下来，反复出现的是同一个模式："
            "<strong>时间轴上的每一个便宜的近似，都在别处产生一个精确可算的代价</strong>——"
            "时间压缩换走可观测性（m01）、分解式注意力换走 Kronecker 秩（m02）、"
            "一步拟合换走运动能量（m03）、被动生成的准确不蕴含抗优化（m04）、"
            "逐帧特征换走整个时间维（m05）。"
            "而这些代价<strong>全都不会报错</strong>。"
            "所以唯一的办法是把它们各自量出来，而每一个都只需要几行 numpy。"),
])),
]

NB = [
md("""# C77 模块 05 · 视频评测

三个病理，每个都精确：

1. **同分布之间的 FD 恒为正**且 $\\propto 1/N$（$N$ 跨 64 倍时系数稳定在 0.577–0.583）；
2. 对**匹配前两阶矩**的分布**看不出差别**（0.000587 vs 同分布基线 0.000603）；
3. **逐帧特征对帧序的敏感度是 $7.1\\times10^{-15}$**（机器精度）。

纯 numpy / CPU / 离线，不训练任何网络。"""),

code("""import numpy as np

def frechet(m1, C1, m2, C2):
    '''高斯假设下的 Frechet 距离（= FID/FVD 的定义）。'''
    d = m1 - m2
    ev1, V1 = np.linalg.eigh(C1)
    S1 = V1 @ np.diag(np.sqrt(np.clip(ev1, 0, None))) @ V1.T
    ev = np.clip(np.linalg.eigvalsh(S1 @ C2 @ S1), 0, None)
    return float(d @ d + np.trace(C1) + np.trace(C2) - 2*np.sum(np.sqrt(ev)))

def fd_samples(X, Y):
    '''从两组样本估 Frechet 距离。'''
    return frechet(X.mean(0), np.cov(X, rowvar=False),
                   Y.mean(0), np.cov(Y, rowvar=False))

print('FVD = FID 的直接搬运：把视频过一个时空特征提取器，然后算 Frechet 距离。')
print('所以它继承了 FID 的全部性质 —— 包括本模块要量的三个病理。')"""),

md("""## 1. 病理一：同分布之间的 FD 不是零，且 $\\propto 1/N$"""),

code("""d = 32
print(f'特征维 d={d}，两组都来自标准正态。真值应为 0')
print()
print('     N      FD 均值      FD 中位数    d²/N        实测/(d²/N)')
null_fd = {}
for N in (64, 128, 256, 512, 1024, 4096):
    vals = []
    for s in range(200):
        r = np.random.default_rng(s)
        vals.append(fd_samples(r.normal(0, 1, (N, d)), r.normal(0, 1, (N, d))))
    vals = np.array(vals)
    null_fd[N] = float(vals.mean())
    print(f'  {N:6d}   {vals.mean():10.4f}   {np.median(vals):10.4f}   '
          f'{d*d/N:9.3f}   {vals.mean()/(d*d/N):12.3f}')

# 1/N 律：ratio 稳定
ratios = [null_fd[N] / (d*d/N) for N in null_fd]
assert max(ratios) / min(ratios) < 1.05, \\
    f'1/N 律应精确（比值应稳定）：{[round(r,4) for r in ratios]}'
# FD 恒为正
assert all(v > 0 for v in null_fd.values()), '同分布下 FD 应恒为正'
# N 翻倍 FD 减半
for N in (64, 128, 256, 512):
    assert abs(null_fd[N] / null_fd[2*N] - 2.0) < 0.15, \\
        f'N 从 {N} 到 {2*N}: FD 应减半，实测 {null_fd[N]/null_fd[2*N]:.3f}'
assert abs(null_fd[1024] / null_fd[4096] - 4.0) < 0.6, \\
    f'N 从 1024 到 4096（4 倍）: FD 应降 4 倍，实测 {null_fd[1024]/null_fd[4096]:.3f}'

print()
print(f'✅ 1/N 律精确：N 跨 64 倍，实测/(d²/N) 稳定在 '
      f'{min(ratios):.3f}–{max(ratios):.3f}')
print(f'✅ 而 N=64 时零假设值已经是 {null_fd[64]:.2f}')
print()
print('系数对特征维 d 的依赖:')
print('    d      N=256      N=1024     FD/(d²/N) @256   @1024')
for dd in (8, 16, 32, 64):
    row = {}
    for N in (256, 1024):
        v = np.mean([fd_samples(np.random.default_rng(s).normal(0,1,(N,dd)),
                                np.random.default_rng(1000+s).normal(0,1,(N,dd)))
                     for s in range(120)])
        row[N] = v
    print(f'  {dd:5d}   {row[256]:9.4f}  {row[1024]:9.4f}   '
          f'{row[256]/(dd*dd/256):14.3f}   {row[1024]/(dd*dd/1024):7.3f}')
print()
print('-> 1/N 律对每个 d 都精确（同一 d 下两列的系数一致），')
print('   而**系数本身随 d 变化**（0.85 附近降到 0.54 附近）。')
print('   所以可断言的是 1/N 律；d 依赖只能报实测系数。')
print()
print('⚠️  最常见的口径错误：**不同 N 下的 FVD 不可比**。')
print(f'   「我们 FVD=180，基线 210」—— 若两者 N 不同，这个差可能全由有限样本偏差解释。')
print(f'   而视频评测里 N=64 很常见（生成一段视频很贵），此时 d=32 的零假设值已是 '
      f'{null_fd[64]:.2f}。')"""),

md("""## 2. 病理二：只看前两阶矩

构造两个**均值与协方差完全相同**但形状截然不同的分布。"""),

code("""r = np.random.default_rng(0)
N2, D2 = 100_000, 8

# A：第 0 维是标准正态
A_feat = r.normal(0, 1, (N2, D2))
# B：第 0 维是 ±1 的两点分布（方差同为 1），其余维与 A 同分布
B_feat = r.normal(0, 1, (N2, D2))
B_feat[:, 0] = r.choice([-1.0, 1.0], N2) + r.normal(0, 1e-6, N2)

def kurt(x):
    return float(((x - x.mean())**4).mean() / x.var()**2)

print('A = 第 0 维标准正态；B = 第 0 维是 ±1 的两点分布（方差同为 1）')
print(f'  A: 均值[0] = {A_feat[:,0].mean():+.5f}, 方差[0] = {A_feat[:,0].var():.5f}, '
      f'峰度[0] = {kurt(A_feat[:,0]):.4f}（正态 = 3）')
print(f'  B: 均值[0] = {B_feat[:,0].mean():+.5f}, 方差[0] = {B_feat[:,0].var():.5f}, '
      f'峰度[0] = {kurt(B_feat[:,0]):.4f}（两点 = 1）')
print()
fd_ab = fd_samples(A_feat, B_feat)
fd_null = fd_samples(A_feat, r.normal(0, 1, (N2, D2)))
print(f'  A 与 B 的 Frechet 距离        = {fd_ab:.6f}')
print(f'  同分布 N={N2} 的基线          = {fd_null:.6f}')
print(f'  比值                          = {fd_ab/fd_null:.4f}')

assert abs(A_feat[:,0].var() - B_feat[:,0].var()) < 0.01, '方差应匹配'
assert abs(kurt(A_feat[:,0]) - 3.0) < 0.1 and abs(kurt(B_feat[:,0]) - 1.0) < 0.1, \\
    '峰度应差别巨大'
assert fd_ab < 3 * fd_null, \\
    f'FD 应与同分布基线同量级（{fd_ab:.6f} vs {fd_null:.6f}）'

print()
print(f'✅ 峰度 {kurt(A_feat[:,0]):.2f} vs {kurt(B_feat[:,0]):.2f}（一个连续单峰、一个只有两个取值）')
print(f'✅ 而 FD 只有 {fd_ab:.6f}，与同分布基线 {fd_null:.6f} 同量级')
print()
print('-> 这不是精度问题，是**定义**：Frechet 距离的公式里只出现 μ 与 Σ。')
print('   所以任何两个同均值同协方差的分布，FVD 都认为它们相同。')
print()
print('   直接对应的真实失效：**模式坍缩到几个离散模式** ——')
print('   生成器只会产出少数几种运动模式，而只要它们的混合的一二阶矩对得上，')
print('   FVD 就看不出来。这是视频生成最常见的失效之一。')"""),

md("""## 3. 病理三：特征决定一切

同一批视频，**只把帧顺序打乱**，看指标变不变。"""),

code("""def make_videos(n=3000, T=8, d=16, seed=1, corr=0.9):
    '''合成「视频特征序列」：每帧 d 维，时间上做 AR(1)。'''
    r = np.random.default_rng(seed)
    V = r.normal(0, 1, (n, T, d))
    for t in range(1, T):
        V[:, t] = corr*V[:, t-1] + np.sqrt(1-corr**2)*V[:, t]
    return V

def feats_perframe(V):
    '''逐帧特征后对时间取平均 —— 很多实现就是这么做的。'''
    return V.mean(1)
def feats_spatiotemporal(V):
    '''加上时间差分的最简时空特征。'''
    return np.concatenate([V.mean(1), np.abs(np.diff(V, axis=1)).mean(1)], 1)

V = make_videos()
perm = np.random.default_rng(2).permutation(V.shape[1])
Vs = V[:, perm, :]
print(f'同一批 {len(V)} 段视频，只把帧顺序打乱（perm = {perm}）')
print()
fd_pf = fd_samples(feats_perframe(V), feats_perframe(Vs))
fd_st = fd_samples(feats_spatiotemporal(V), feats_spatiotemporal(Vs))
print(f'  逐帧特征取时间平均:    FD = {fd_pf:.6e}')
print(f'  含时间差分的时空特征:  FD = {fd_st:.6e}')
assert fd_pf < 1e-10, f'逐帧平均特征应对帧序**恒等于**免疫，得到 {fd_pf:.3e}'
assert fd_st > 0.1, f'时空特征应能看出帧序，得到 {fd_st:.3e}'

print()
print(f'✅ {fd_pf:.1e} 不是「不够敏感」，是**恒等于零**：')
print('   对时间取平均之后，帧的顺序在特征里已经不存在了。')
print()
print('   所以「用逐帧特征算出来的 FVD」根本不是在评测时间维 ——')
print('   它是一个逐帧的 FID，只是名字里有个 V。')

# 多个置换都一样
print()
print('  10 个不同的随机置换:')
fds = []
for s in range(10):
    p = np.random.default_rng(100+s).permutation(V.shape[1])
    fds.append(fd_samples(feats_perframe(V), feats_perframe(V[:, p, :])))
print(f'    逐帧特征: 最大 {max(fds):.3e}，全部 < 1e-10: {all(v < 1e-10 for v in fds)}')
assert all(v < 1e-10 for v in fds)
print('    -> 与置换无关，恒为机器精度。')"""),

md("""## ✏️ 练习 1：$\\text{FVD}_\\infty$——把有限样本偏差外推掉

既然零假设值 $\\propto 1/N$，就可以在若干个 $N$ 上测，然后线性外推到 $1/N = 0$。

实现 `fd_infinity(X, Y, Ns, reps)`：在给定的若干个子样本量上估 FD，
对 $1/N$ 做线性回归，返回截距（$= \\text{FD}_\\infty$）。"""),

code("""def fd_infinity(X, Y, Ns=(64, 128, 256, 512), reps=20, seed=0):
    '''FD_inf：在若干子样本量上估 FD，对 1/N 线性外推到 1/N = 0。

    参数
    ----
    X, Y : 两组特征样本
    Ns   : 子样本量（必须都 <= min(len(X), len(Y))）
    reps : 每个 N 重采样多少次取平均
    seed : 重采样 seed

    返回
    ----
    (fd_inf, slope, curve) :
      fd_inf = 对 1/N 线性回归的截距
      slope  = 斜率
      curve  = {N: 该 N 下的 FD 均值}
    '''
    r = np.random.default_rng(seed)
    # TODO: 对每个 N，重采样 reps 次（各取 N 个样本），算 fd_samples 的均值；
    #       然后用 np.polyfit(1/N, FD, 1) 得斜率与截距；返回 (截距, 斜率, 曲线)
    raise NotImplementedError"""),

code("""# 自测
_d = 32
_r = np.random.default_rng(7)
_NS = (64, 128, 256, 512, 1024)

print('  (a) 同分布：FD_inf 应接近 0，而各 N 的 FD 都明显 > 0')
_X = np.random.default_rng(7).normal(0, 1, (4000, _d))
_Y = np.random.default_rng(8).normal(0, 1, (4000, _d))
_inf, _sl, _cv = fd_infinity(_X, _Y, Ns=_NS)
print('     N      FD')
for _N in _NS:
    print(f'   {_N:5d}   {_cv[_N]:.4f}')
print(f'    FD_inf（外推）= {_inf:+.5f}   斜率 = {_sl:.2f}')
assert abs(_inf) < 0.05, f'同分布的 FD_inf 应接近 0，得到 {_inf:.5f}'
assert _cv[_NS[0]] > 5.0, f'N=64 时的 FD 应明显 >0，得到 {_cv[_NS[0]]:.4f}'
print(f'    -> 外推把偏差从 {_cv[_NS[0]]:.2f}（N=64）降到 {abs(_inf):.5f}'
      f'（{_cv[_NS[0]]/max(abs(_inf),1e-9):.0f} 倍）')

print()
print('  (b) 真有差别时，FD_inf 保留那个差别 —— 但精度是**绝对**的，不是相对的')
print('    均值偏移   真 FD     N=64 的 FD   FD_inf      绝对残差   相对残差')
_abs_res = []
for _shift in (0.0, 0.1, 0.3, 0.5, 1.0, 2.0):
    _Y2 = np.random.default_rng(8).normal(0, 1, (4000, _d))   # 固定 seed 便于复现
    _Y2[:, 0] += _shift
    _i2, _, _c2 = fd_infinity(_X, _Y2, Ns=_NS)
    _true = _shift**2
    _abs_res.append(abs(_i2 - _true))
    print(f'    {_shift:8.1f}   {_true:7.4f}   {_c2[64]:10.4f}   {_i2:+9.4f}   '
          f'{abs(_i2-_true):8.4f}   {abs(_i2-_true)/max(_true,0.02)*100:7.1f}%')

# 绝对残差有界，而相对残差在小效应上很大
assert max(_abs_res) < 0.10, \\
    f'绝对残差应 <0.10，实测最大 {max(_abs_res):.4f}'
_Y_small = np.random.default_rng(8).normal(0, 1, (4000, _d)); _Y_small[:, 0] += 0.1
_i_small = fd_infinity(_X, _Y_small, Ns=_NS)[0]
print()
print(f'    ⚠️  偏移 0.1（真 FD = 0.0100）时 FD_inf = {_i_small:+.4f}'
      f' —— **{_i_small/0.01:.1f} 倍高估**')
print('        残差的结构是「绝对底 + 小的乘性项」：')
print(f'        真 FD 从 0 到 4 时残差从 {_abs_res[0]:.4f} 涨到 {_abs_res[-1]:.4f}，')
print(f'        而**相对**残差从（无定义）降到 {_abs_res[-1]/4.0*100:.1f}%。')
print(f'    -> 所以 FD_inf 在大效应上相对精度很好（>= 0.09 时相对残差 <25%），')
print(f'       而在小效应上不可靠（绝对底约 {_abs_res[0]:.3f}）。')
print('       注意 1/N 线性拟合**不保证非负**，所以极小效应上它甚至可能给出负值。')

print()
print('  (c) 而**固定 N** 的 FD 会把小差别完全埋掉:')
_c_same = fd_infinity(_X, np.random.default_rng(8).normal(0, 1, (4000, _d)), Ns=_NS)[2][64]
for _shift in (0.0, 0.1, 0.3, 1.0):
    _Y2 = np.random.default_rng(8).normal(0, 1, (4000, _d))
    _Y2[:, 0] += _shift
    _c2 = fd_infinity(_X, _Y2, Ns=_NS)[2][64]
    print(f'    偏移 {_shift:.1f}: N=64 的 FD = {_c2:8.4f}'
          f'（真值 {_shift**2:.4f}，与「同分布」的 {_c_same:.4f} 相比差 '
          f'{abs(_c2-_c_same):.4f}）')
_Yb = np.random.default_rng(8).normal(0, 1, (4000, _d)); _Yb[:, 0] += 0.1
_c_b = fd_infinity(_X, _Yb, Ns=_NS)[2][64]
assert abs(_c_b - _c_same) < _c_same, \\
    f'小差别应被有限样本偏差淹没（差 {abs(_c_b-_c_same):.3f} vs 偏差 {_c_same:.3f}）'
print(f'    -> 偏移 0.1 造成的差 {abs(_c_b-_c_same):.3f} 远小于偏差本身 {_c_same:.3f}。')

print()
print(f'✅ 同分布的 FD_inf = {_inf:+.5f}（把 N=64 的偏差降了 '
      f'{_cv[_NS[0]]/max(abs(_inf),1e-9):.0f} 倍）')
print(f'✅ 真有差别时 FD_inf 的绝对残差 <= {max(_abs_res):.3f}（6 个偏移量），')
print(f'   而真 FD >= 0.09 时相对残差 < 25%')
print(f'⚠️  但小效应上不可靠：偏移 0.1（真 FD 0.01）时给出 {_i_small:+.4f}'
      f'（{_i_small/0.01:.1f} 倍高估）')
print()
print('   -> 两条可操作的结论:')
print('      · 「固定 N」是最低要求；要比较**接近**的模型必须做外推。')
print(f'      · 而外推本身有一个绝对精度下限（这里约 {max(_abs_res):.2f}）——')
print('        小于它的效应无论怎么外推都分辨不出，只能加大 N 或换指标。')"""),

md("""## ✏️ 练习 2：一个能看到模式坍缩的指标

FVD 对第 2 节那个例子免疫。实现一个 $k$-NN 覆盖率来补它：

`coverage(X_real, Y_gen, k)`：对每个**真实**样本，看它的第 $k$ 近邻半径内
有没有生成样本；返回被覆盖的真实样本比例。

模式坍缩会让覆盖率下降，而 FVD 看不出来。"""),

code("""def coverage(X_real, Y_gen, k=5, chunk=512):
    '''k-NN 覆盖率（recall 的一个简单实现）。

    对每个真实样本 x：
      r_k(x) = x 到其**第 k 个真实近邻**的距离（不含自己）
      被覆盖 = 存在生成样本落在 x 的 r_k(x) 半径内
    返回被覆盖的真实样本比例。

    参数
    ----
    X_real : 真实样本 (n, d)
    Y_gen  : 生成样本 (m, d)
    k      : 近邻数
    chunk  : 分块大小（避免建大矩阵）

    返回
    ----
    float : 覆盖率 ∈ [0, 1]
    '''
    # TODO: ① 对 X_real 内部算第 k 近邻距离 r_k（用 np.partition，排除自身距离 0）
    #       ② 算每个真实样本到最近**生成**样本的距离 dmin
    #       ③ 返回 mean(dmin <= r_k)
    #       两步都要分块，避免 (n, n) / (n, m) 的大矩阵
    raise NotImplementedError"""),

code("""# 自测
_r2 = np.random.default_rng(11)
_n, _dd = 4000, 8

print('  (a) 同分布：覆盖率应高')
_XR = _r2.normal(0, 1, (_n, _dd))
_YG = _r2.normal(0, 1, (_n, _dd))
_cov_same = coverage(_XR, _YG, k=5)
print(f'    覆盖率 = {_cov_same:.4f}')
assert _cov_same > 0.7, f'同分布的覆盖率应 >0.7，得到 {_cov_same:.4f}'

print()
print('  (b) 第 2 节那个例子：FVD 看不出，覆盖率能看出')
_A2 = _r2.normal(0, 1, (_n, _dd))
_B2 = _r2.normal(0, 1, (_n, _dd))
_B2[:, 0] = _r2.choice([-1.0, 1.0], _n)            # 第 0 维坍缩成两点
_fd = fd_samples(_A2, _B2)
_fd_base = fd_samples(_A2, _r2.normal(0, 1, (_n, _dd)))
_cov_collapse = coverage(_A2, _B2, k=5)
print(f'    FVD:     A vs B = {_fd:.5f}，同分布基线 = {_fd_base:.5f}'
      f'（比值 {_fd/_fd_base:.2f}）')
print(f'    覆盖率:  A vs B = {_cov_collapse:.4f}，同分布 = {_cov_same:.4f}'
      f'（降低 {(1-_cov_collapse/_cov_same)*100:.0f}%）')
assert _fd < 5 * _fd_base, 'FVD 应看不出差别'
assert _cov_collapse < 0.95 * _cov_same, \\
    f'覆盖率应下降（{_cov_collapse:.4f} vs {_cov_same:.4f}）'

print()
print('  (c) 坍缩程度 vs 两个指标')
print('    保留的模式数   FVD / 基线    覆盖率    覆盖率 / 同分布')
for _nmode in (2, 4, 8, 32, 1000):
    _Bm = _r2.normal(0, 1, (_n, _dd))
    _centers = _r2.normal(0, 1, (_nmode,))
    _centers = (_centers - _centers.mean()) / _centers.std()      # 匹配一二阶矩
    _Bm[:, 0] = _centers[_r2.integers(0, _nmode, _n)]
    _f = fd_samples(_A2, _Bm) / _fd_base
    _c = coverage(_A2, _Bm, k=5)
    print(f'    {_nmode:12d}   {_f:10.2f}    {_c:.4f}   {_c/_cov_same:.4f}')

print()
print(f'✅ 同分布覆盖率 {_cov_same:.3f}；坍缩到两点时降到 {_cov_collapse:.3f}')
print(f'✅ 而同一对分布的 FVD 只有基线的 {_fd/_fd_base:.2f} 倍 —— 完全看不出')
print()
print('   -> 覆盖率与 FVD 是**互补**的，不是替代关系：')
print('      FVD 对整体的一二阶矩敏感、对模式结构免疫；')
print('      覆盖率对模式结构敏感、对整体平移不敏感。')
print('      两个都报才能同时管住「分布错位」与「模式坍缩」。')"""),

md("""## ✏️ 练习 3：$N$ 多小算太小

正文说 $N{=}64$ 时零假设值已经是 $9.33$（$d{=}32$）。
把它变成一条可以用来定 $N$ 的规则：实现 `min_N_for_effect(d, target_fd, ratio)`，
返回让「有限样本偏差 $\\leq$ 目标效应 / ratio」所需的最小 $N$。"""),

code("""def null_fd_estimate(d, N, reps=40, seed=0):
    '''同分布下 FD 的均值（有限样本偏差的大小）。'''
    vals = []
    for s in range(reps):
        r = np.random.default_rng(seed + s)
        vals.append(fd_samples(r.normal(0, 1, (N, d)), r.normal(0, 1, (N, d))))
    return float(np.mean(vals))

def min_N_for_effect(d, target_fd, ratio=5.0, Ns=(64, 128, 256, 512, 1024, 2048, 4096)):
    '''让有限样本偏差 <= target_fd / ratio 所需的最小 N。

    用 1/N 律外推而不是逐个测（逐个测太慢）：
      先在一个基准 N0 上测出偏差 b0，则 b(N) ≈ b0 * N0 / N。

    参数
    ----
    d         : 特征维
    target_fd : 你想分辨的效应大小
    ratio     : 要求偏差比效应小多少倍
    Ns        : 候选 N

    返回
    ----
    (min_N, b0, curve) :
      min_N = 最小可行的 N（候选内都不够时返回 None）
      b0    = 在 Ns[0] 上实测的偏差
      curve = {N: 外推的偏差}
    '''
    N0 = Ns[0]
    b0 = null_fd_estimate(d, N0)
    # TODO: 用 b(N) = b0 * N0 / N 外推；返回第一个满足 b(N) <= target_fd/ratio 的 N
    raise NotImplementedError"""),

code("""# 自测
print('  (a) 外推的偏差与实测吻合（d=32）')
_b0 = null_fd_estimate(32, 64)
print('     N     外推 b0*64/N    实测        相对差')
for _N in (128, 256, 512, 1024):
    _ex = _b0 * 64 / _N
    _me = null_fd_estimate(32, _N)
    print(f'   {_N:5d}   {_ex:12.4f}   {_me:9.4f}   {abs(_ex-_me)/_me*100:6.1f}%')
    assert abs(_ex - _me) / _me < 0.10, f'N={_N}: 外推应与实测吻合到 10%'

print()
print('  (b) 想分辨多小的效应，就需要多大的 N（d=32, ratio=5）')
print('    目标效应   所需最小 N     该 N 下的偏差')
for _tf in (100.0, 20.0, 5.0, 1.0, 0.2):
    _mn, _b, _cv2 = min_N_for_effect(32, _tf, ratio=5.0)
    _shown = str(_mn) if _mn else '>4096'
    _bias = _cv2[_mn] if _mn else float('nan')
    print(f'    {_tf:8.1f}   {_shown:>10s}     {_bias:.4f}')
    if _mn:
        assert _cv2[_mn] <= _tf / 5.0 + 1e-9

print()
print('  (c) 特征维的影响（目标效应固定为 5.0）')
print('     d     所需最小 N   N=64 时的偏差')
for _dd in (8, 16, 32, 64):
    _mn, _b, _ = min_N_for_effect(_dd, 5.0, ratio=5.0)
    print(f'   {_dd:5d}   {str(_mn) if _mn else ">4096":>10s}   {_b:.4f}')
_mn8 = min_N_for_effect(8, 5.0)[0]
_mn64 = min_N_for_effect(64, 5.0)[0]
assert _mn64 > _mn8, 'd 越大所需 N 越大'

print()
print(f'✅ 1/N 外推与实测吻合到 10% 以内（4 个 N 全对）')
print(f'✅ d=8 时需要 N>={_mn8}，d=64 时需要 N>={_mn64}')
print()
print('   -> 这条规则可以在**做实验之前**用：')
print('      先想清「我要分辨多大的差别」，再算所需的 N。')
print('      如果算出来的 N 生成不起，那这个实验就不该被做成 FVD 比较 ——')
print('      应该换成分维度打分或人评。')"""),

md("""## ✏️ 练习 4：帧序置换检验

正文说这个检验应该对每个视频指标跑一次。实现它，
并在五种特征上测——其中有一个是刻意构造的陷阱。"""),

code("""def order_sensitivity(feat_fn, n=2000, T=8, dfeat=16, seeds=5, corr=0.9):
    '''特征函数对帧序的敏感度（多次随机置换的 FD 中位数）。

    参数
    ----
    feat_fn : 把 (n, T, d) 的视频批映射到 (n, k) 特征的函数
    n, T, dfeat : 批大小、帧数、每帧特征维
    seeds   : 试多少个随机置换
    corr    : 视频的时间相关性

    返回
    ----
    float : FD 的中位数
    '''
    V = make_videos(n=n, T=T, d=dfeat, seed=11, corr=corr)
    # TODO: 对 s in range(seeds)：用 np.random.default_rng(100+s).permutation(T)
    #       打乱帧序，算 fd_samples(feat_fn(V), feat_fn(V_shuffled))，返回中位数
    raise NotImplementedError"""),

code("""# 自测
def _f_mean(V):
    '''逐帧特征取时间平均。'''
    return V.mean(1)
def _f_sorted(V):
    '''对时间轴**排序**后再平均 —— 一个刻意构造的陷阱。'''
    return np.sort(V, axis=1).mean(1)
def _f_concat(V):
    '''把所有帧拼起来（保留全部顺序信息）。'''
    return V.reshape(len(V), -1)
def _f_diff(V):
    '''时间差分的绝对值均值。'''
    return np.abs(np.diff(V, axis=1)).mean(1)
def _f_firstlast(V):
    '''首末帧之差。'''
    return V[:, -1] - V[:, 0]

print('  特征                              用了多少帧   帧序敏感度      判定')
_res = {}
for _name, _fn, _uses, _expect in [
        ('逐帧平均 mean_t', _f_mean, '全部 T 帧', 'blind'),
        ('**时间排序后**平均', _f_sorted, '全部 T 帧', 'blind'),
        ('全帧拼接', _f_concat, '全部 T 帧', 'sensitive'),
        ('时间差分均值', _f_diff, '全部 T 帧', 'sensitive'),
        ('首末帧之差', _f_firstlast, '仅 2 帧', 'sensitive')]:
    _v = order_sensitivity(_fn)
    _res[_name] = _v
    _verdict = '❌ 对帧序免疫' if _v < 1e-9 else '✅ 能看出帧序'
    print(f'  {_name:32s}  {_uses:10s}  {_v:.6e}   {_verdict}')
    if _expect == 'blind':
        assert _v < 1e-9, f'{_name} 应对帧序免疫，得到 {_v:.3e}'
    else:
        assert _v > 1e-3, f'{_name} 应能看出帧序，得到 {_v:.3e}'

print()
print('✅ 两类特征被干净地分开：免疫的 < 1e-9（机器精度），敏感的 > 1e-3')
print()
print('⚠️  注意两行的对照:')
print('    「时间排序后平均」**用到了全部 T 帧**（它排序了整段），却对帧序完全免疫；')
print('    「首末帧之差」**只用了 2 帧**，却能看出帧序。')
print()
print('   -> 所以判据不是「用了多少帧」，也不是「网络结构能不能看时间」。')
print('      常见的辩护是「我们的提取器是 3D 卷积/时空 Transformer」——')
print('      但**结构能看时间不代表最终特征里保留了帧序信息**。')
print('      唯一可靠的判据是把置换检验真的跑一遍，而它只需要几行代码。')

# 相关性对敏感度的影响
print()
print('  时间相关性 vs 敏感度（时空特征）:')
print('    corr    敏感度')
for _c in (0.0, 0.3, 0.6, 0.9, 0.99):
    _v = order_sensitivity(_f_diff, corr=_c)
    print(f'    {_c:.2f}    {_v:.6e}')
_v0 = order_sensitivity(_f_diff, corr=0.0)
_v9 = order_sensitivity(_f_diff, corr=0.9)
assert _v9 > _v0 * 10, '相关性越高，打乱帧序造成的差别应越大'
print()
print(f'✅ corr=0 时敏感度 {_v0:.2e}（本来就没有时间结构可打乱）')
print(f'   corr=0.9 时是 {_v9:.2e}（{_v9/max(_v0,1e-12):.0f} 倍）')
print('   -> 置换检验的**功效**取决于素材本身的时间相关性。')
print('      在快剪辑素材上做这个检验会得到假的「通过」—— 检验本身需要合适的数据。')"""),

md("""## 📖 参考答案"""),

code("""def fd_infinity(X, Y, Ns=(64, 128, 256, 512), reps=20, seed=0):
    '''FD_inf：在若干子样本量上估 FD，对 1/N 线性外推。'''
    r = np.random.default_rng(seed)
    curve = {}
    for N in Ns:
        vals = []
        for _ in range(reps):
            ix = r.choice(len(X), N, replace=False)
            iy = r.choice(len(Y), N, replace=False)
            vals.append(fd_samples(X[ix], Y[iy]))
        curve[N] = float(np.mean(vals))
    xs = np.array([1.0/N for N in Ns])
    ys = np.array([curve[N] for N in Ns])
    slope, intercept = np.polyfit(xs, ys, 1)
    return float(intercept), float(slope), curve

def coverage(X_real, Y_gen, k=5, chunk=512):
    '''k-NN 覆盖率（recall 的一个简单实现）。'''
    n = len(X_real)
    # ① 真实样本内部的第 k 近邻距离
    rk = np.empty(n)
    xn = (X_real * X_real).sum(1)
    for i in range(0, n, chunk):
        blk = X_real[i:i+chunk]
        d2 = (blk*blk).sum(1)[:, None] - 2.0*(blk @ X_real.T) + xn[None, :]
        d2 = np.maximum(d2, 0.0)
        # 排除自身（每行的最小值 0）
        part = np.partition(d2, k, axis=1)[:, :k+1]
        part = np.sort(part, axis=1)[:, 1:k+1]
        rk[i:i+chunk] = np.sqrt(part[:, -1])
    # ② 到最近生成样本的距离
    dmin = np.empty(n)
    yn = (Y_gen * Y_gen).sum(1)
    for i in range(0, n, chunk):
        blk = X_real[i:i+chunk]
        d2 = (blk*blk).sum(1)[:, None] - 2.0*(blk @ Y_gen.T) + yn[None, :]
        dmin[i:i+chunk] = np.sqrt(np.maximum(d2.min(1), 0.0))
    return float(np.mean(dmin <= rk))

def min_N_for_effect(d, target_fd, ratio=5.0, Ns=(64, 128, 256, 512, 1024, 2048, 4096)):
    '''让有限样本偏差 <= target_fd/ratio 所需的最小 N（用 1/N 律外推）。'''
    N0 = Ns[0]
    b0 = null_fd_estimate(d, N0)
    curve = {N: b0 * N0 / N for N in Ns}
    thresh = target_fd / ratio
    for N in Ns:
        if curve[N] <= thresh:
            return N, b0, curve
    return None, b0, curve

def order_sensitivity(feat_fn, n=2000, T=8, dfeat=16, seeds=5, corr=0.9):
    '''特征函数对帧序的敏感度（多次随机置换的 FD 中位数）。'''
    V = make_videos(n=n, T=T, d=dfeat, seed=11, corr=corr)
    vals = []
    for s in range(seeds):
        perm = np.random.default_rng(100 + s).permutation(T)
        vals.append(fd_samples(feat_fn(V), feat_fn(V[:, perm, :])))
    return float(np.median(vals))

print('参考答案已定义。')
print()
print('要点：')
print('  1. FD_inf 的 1/N 外推把 N=64 的偏差降 2 个数量级，而真实差别被保留。')
print('     「固定 N」只是最低要求；比较接近的模型必须外推。')
print('  2. 覆盖率与 FVD **互补**：前者对模式结构敏感，后者对一二阶矩敏感。')
print('  3. 「我要分辨多大的差别」决定所需的 N —— 这个账应该在实验之前算。')
print('  4. 帧序置换检验的判据不是「用了多少帧」：')
print('     「排序后平均」用了全部帧却免疫，「首末帧之差」只用 2 帧却敏感。')"""),

md("""## 🧪 真实工程胶囊：一份视频评测报告的最低配置

下面这段代码把本模块与模块 03 的结论合成一份报告：
它对一批生成视频输出五项，并对每一项标注**它管得住什么、管不住什么**。

关键设计：报告里每一项都带一个「这一项对什么免疫」的字段。
因为本模块的三个病理说明，<strong>不写清免疫范围的指标等于没有量纲</strong>。"""),

code("""def video_eval_report(gen_feats, real_feats, gen_seqs=None, real_seqs=None,
                      d_hint=None, verbose=True):
    '''视频评测的最低配置报告。

    gen_feats / real_feats : (n, T, d) 的**逐帧**特征（本函数自己做两种聚合）
    gen_seqs / real_seqs   : 可选，1D 序列批（给模块 03 的长程诊断）
    '''
    out = {}
    T = gen_feats.shape[1]

    # ① FVD（两种特征各算一次）——并同时报有限样本偏差
    f_pf_g, f_pf_r = gen_feats.mean(1), real_feats.mean(1)
    f_st_g = np.concatenate([gen_feats.mean(1),
                             np.abs(np.diff(gen_feats, axis=1)).mean(1)], 1)
    f_st_r = np.concatenate([real_feats.mean(1),
                             np.abs(np.diff(real_feats, axis=1)).mean(1)], 1)
    N = min(len(f_pf_g), len(f_pf_r))
    d_eff = d_hint if d_hint is not None else f_st_r.shape[1]
    out['fvd_perframe'] = fd_samples(f_pf_g, f_pf_r)
    out['fvd_spatiotemporal'] = fd_samples(f_st_g, f_st_r)
    out['null_bias'] = null_fd_estimate(min(d_eff, 32), min(N, 512), reps=10)
    out['N'] = N

    # ② 覆盖率
    out['coverage'] = coverage(f_st_r[:min(2000, len(f_st_r))],
                               f_st_g[:min(2000, len(f_st_g))], k=5)

    # ③ 帧序置换检验（对**本报告用的两种特征**各跑一次）
    perm = np.random.default_rng(3).permutation(T)
    out['order_sens_perframe'] = fd_samples(f_pf_r, real_feats[:, perm, :].mean(1))
    _sp = real_feats[:, perm, :]
    out['order_sens_spatiotemporal'] = fd_samples(
        f_st_r, np.concatenate([_sp.mean(1), np.abs(np.diff(_sp, axis=1)).mean(1)], 1))

    # ④ 长程（模块 03）
    if gen_seqs is not None and real_seqs is not None:
        ref_sd = float(np.median([np.std(y) for y in real_seqs]))
        bad = sum(1 for y in gen_seqs
                  if (not np.isfinite(y).all()) or np.abs(y).max() > 10*ref_sd)
        out['collapse_rate'] = bad / len(gen_seqs)
        ok = [y for y in gen_seqs
              if np.isfinite(y).all() and np.abs(y).max() <= 10*ref_sd]
        if ok:
            m_g = float(np.median([np.std(y[len(y)//2:]) for y in ok]))
            m_r = float(np.median([np.std(y[len(y)//2:]) for y in real_seqs]))
            out['energy_ratio'] = m_g / max(m_r, 1e-12)

    if verbose:
        print(f'  样本数 N = {out["N"]}，特征维 = {f_st_r.shape[1]}')
        print('  ' + '-' * 70)
        print(f'  ① FVD（逐帧特征）        = {out["fvd_perframe"]:10.4f}')
        print(f'     免疫：帧序（本模块第 3 节实测 {out["order_sens_perframe"]:.1e}）、'
              f'高阶矩、模式坍缩')
        print(f'  ① FVD（时空特征）        = {out["fvd_spatiotemporal"]:10.4f}')
        print(f'     免疫：高阶矩、模式坍缩。有限样本偏差 ≈ {out["null_bias"]:.4f}'
              f'（N={min(out["N"],512)}, d≈{min(d_eff,32)}）')
        print(f'  ② 覆盖率（k=5）          = {out["coverage"]:10.4f}')
        print(f'     免疫：整体平移（它只看局部近邻结构）')
        print(f'  ③ 帧序置换敏感度')
        print(f'       逐帧特征            = {out["order_sens_perframe"]:.3e}'
              + ('   ⚠️  免疫 —— 这一项**不在**评时间维'
                 if out['order_sens_perframe'] < 1e-9 else ''))
        print(f'       时空特征            = {out["order_sens_spatiotemporal"]:.3e}')
        if 'collapse_rate' in out:
            print(f'  ④ 崩坏率                 = {out["collapse_rate"]*100:9.1f}%')
            print(f'     能量比（未崩坏部分）   = {out.get("energy_ratio", float("nan")):10.4f}')
            print(f'     免疫：单帧质量（它只看长程的二阶统计）')
        print('  ' + '-' * 70)
    return out

# 构造一批「生成」与「真实」的视频特征
_REAL = make_videos(n=3000, T=8, d=16, seed=1, corr=0.9)
print('=== 场景 A：生成分布与真实一致 ===')
_GEN_A = make_videos(n=3000, T=8, d=16, seed=555, corr=0.9)
_rA = video_eval_report(_GEN_A, _REAL)
print()

print('=== 场景 B：时间结构错了（corr 0.9 -> 0.3），但**单帧分布不变** ===')
_GEN_B = make_videos(n=3000, T=8, d=16, seed=555, corr=0.3)
_rB = video_eval_report(_GEN_B, _REAL)
assert _rB['fvd_spatiotemporal'] > 5 * _rA['fvd_spatiotemporal'], \\
    '时空特征应能看出时间结构变了'
print()

print('=== 场景 C：**矩匹配**的模式坍缩 ===')
print('    把若干特征维坍缩成 ±σ 的两点分布，而符号按 AR(1)(corr=0.9) 翻转 ——')
print('    于是均值、方差、时间相关性**全部匹配**，只有高阶矩不同（峰度 3 -> 1）。')
_GEN_C = make_videos(n=3000, T=8, d=16, seed=555, corr=0.9)
_rc = np.random.default_rng(4)
_p_flip = (1 - 0.9) / 2
for _j in range(16):                       # 全部 16 维都坍缩
    _sg = np.ones((3000, 8))
    _sg[:, 0] = _rc.choice([-1.0, 1.0], 3000)
    for _t in range(1, 8):
        _sg[:, _t] = _sg[:, _t-1] * ((_rc.random(3000) < _p_flip) * (-2) + 1)
    _GEN_C[:, :, _j] = _sg * _GEN_C[:, :, _j].std()
def _kurt(x):
    return float(((x - x.mean())**4).mean() / x.var()**2)
print(f'    真实的 dim0 峰度 = {_kurt(_REAL[:,:,0].ravel()):.4f}（正态 = 3）')
print(f'    生成的 dim0 峰度 = {_kurt(_GEN_C[:,:,0].ravel()):.4f}（两点 = 1）')
print()
_rC = video_eval_report(_GEN_C, _REAL)
print()

print('=== 三个场景的对照 ===')
print('  场景   FVD(逐帧)  /A      FVD(时空)  /A       覆盖率   抓住问题的是谁')
for _tag, _r, _who in [
        ('A', _rA, '（无问题）'),
        ('B', _rB, 'FVD(时空)'),
        ('C', _rC, 'FVD(时空)')]:
    print(f'  {_tag}     {_r["fvd_perframe"]:9.4f} {_r["fvd_perframe"]/_rA["fvd_perframe"]:6.2f}   '
          f'{_r["fvd_spatiotemporal"]:9.4f} {_r["fvd_spatiotemporal"]/_rA["fvd_spatiotemporal"]:6.2f}    '
          f'{_r["coverage"]:.4f}   {_who}')

_pf_B = _rB['fvd_perframe'] / _rA['fvd_perframe']
_st_B = _rB['fvd_spatiotemporal'] / _rA['fvd_spatiotemporal']
_pf_C = _rC['fvd_perframe'] / _rA['fvd_perframe']
_st_C = _rC['fvd_spatiotemporal'] / _rA['fvd_spatiotemporal']

# 场景 B、C 里 FVD(逐帧) 都盲，而 FVD(时空) 都抓住
assert _st_B > 3 * _pf_B, f'场景 B: 时空应远比逐帧敏感（{_st_B:.2f} vs {_pf_B:.2f}）'
assert _st_C > 5 * _pf_C, f'场景 C: 时空应远比逐帧敏感（{_st_C:.2f} vs {_pf_C:.2f}）'
assert _pf_C < 1.0, f'场景 C 的 FVD(逐帧) 应**低于**基线（完全盲），实测 {_pf_C:.2f}'
assert _st_C > 5.0, f'场景 C 的 FVD(时空) 应明显放大，实测 {_st_C:.2f}'

print()
print('工程含义：')
print(f'  · **两个场景里 FVD(逐帧) 都是盲的**：场景 B 放大 {_pf_B:.2f}x，')
print(f'    场景 C 甚至是 {_pf_C:.2f}x（**低于**同分布基线）。')
print(f'    而 FVD(时空) 分别放大 {_st_B:.1f}x 与 {_st_C:.1f}x。')
print('    -> 「FVD」这三个字母如果不说清用的是哪种特征，这个数就没有量纲。')
print()
print('  · 场景 C 值得单独说：均值、方差、时间相关性**全部匹配**，只有峰度从 3 变成 1。')
print(f'    FVD(逐帧) 因此完全看不出（{_pf_C:.2f}x）—— 这正是本模块病理二。')
print('    而 FVD(时空) 能看出，机制很具体：|diff| 这个特征把一个**四阶矩**差别')
print('    转成了**一阶矩**差别（两点符号过程的 |Δ| 只取 0 或 2σ，均值与高斯不同）。')
print('    -> 所以病理二的准确表述是「FVD 对**给定特征的**高阶矩免疫」，')
print('       而**选对特征可以把信号搬进前两阶** —— 这就是指标特征工程的全部内容。')
print()
print('  · 覆盖率在场景 C 上只降到 '
      f'{_rC["coverage"]/_rA["coverage"]:.3f}x —— 它不是万能的补丁。')
print('    它的强项是「生成完全没覆盖到某些区域」，而不是「覆盖了但形状不对」。')
print()
print('  · 每一项都带「它对什么免疫」的字段。这不是啰嗦 ——')
print('    本模块的三个病理说明，**不写清免疫范围的指标等于没有量纲**。')
""")
,]
