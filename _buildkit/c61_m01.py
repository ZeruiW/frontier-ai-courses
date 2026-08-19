# -*- coding: utf-8 -*-
"""C61 模块 01 · 实验设计与归因。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00；对检测训练流程有基本了解（C18/C53）；不需要统计学背景，公式都从零推"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_experiment_design.ipynb（种子方差 / 配对 t / bootstrap / 功效分析 / Shapley 消融）'),
    ("核心参考", "Bouthillier et al. 2021（benchmark 方差分解）· Dodge et al. 2019（Show Your Work）· Henderson et al. 2018（RL that Matters）· Benjamini–Hochberg 1995"),
    ("预计时长", "读 80 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("single-var", "单变量原则：唯一的目的，和它总被破坏的四种方式", "".join([
        P("<strong>单变量原则</strong>（one factor at a time）不是什么学术洁癖，它只服务一个目的：<em>让观测到的指标变化可以被归因到你做的那个改动上</em>。一旦同时改了两个东西，「涨了 0.8」这个观测就同时兼容至少四种解释（A 有用 / B 有用 / 两者都有用 / 一个 +1.3 另一个 −0.5），而你无法用这次实验区分它们。"),
        P("但真实项目里几乎没有人能严格做到。原因不是懒，是<strong>这个原则在四个地方会被结构性地破坏</strong>——理解这四个机制，比背诵原则有用得多。"),
        H3("破坏方式一：改动自带隐藏耦合"),
        P("你以为改了一个变量，实际上改了五个。这是最隐蔽也最常见的一类："),
        ASCII("""你写在实验记录里的：  "backbone: ResNet50 -> ResNet101"

实际同时发生的变化：
  ├── 参数量 25.6M -> 44.5M              （模型容量 ↑）
  ├── 预训练权重换了一份                 （**预训练数据/配方可能完全不同**）
  ├── 显存占用 ↑ -> batch size 32 -> 16   （**有效学习率、BN 统计量全变了**）
  ├── 单步耗时 ↑ -> 同样 wall-clock 下 epoch 数 ↓（**训练预算变了**）
  └── 最优学习率区间右移                 （沿用旧 lr 等于给新模型一个次优配置）

  ▶ 于是"R101 涨了 1.2"这个观测，兼容的解释至少有五个。
  ▶ **正确做法不是硬拆**（有些耦合物理上不可分离），
    而是：① 显式声明耦合组；② 在耦合组内做补偿（如按 batch 线性缩放 lr）；
          ③ 报告时把耦合写出来，而不是假装它不存在。"""),
        TABLE(["表面上的一个变量", "被它牵动的隐藏变量", "不控制时的偏差方向", "怎么控"], [
            ["<strong>提高输入分辨率</strong> 640→1280", "正样本数、anchor/GT 的尺度匹配分布、单步耗时、显存→batch、增强参数（crop 尺寸）", "偏向高分辨率（同时得到了更多正样本与更长的有效训练）", "固定 iteration 而非 epoch；重新校准 anchor/分配阈值；报告延迟"],
            ["<strong>加入 Mosaic</strong>", "有效 batch 内目标数、小目标比例、训练难度→需要的 epoch 数", "短训练下<em>低估</em> Mosaic（强增强需要更长训练才收敛）", "两边都延长到收敛；或同时报告 12/36 epoch 两组"],
            ["<strong>换标签分配</strong> MaxIoU→SimOTA", "正样本数量与分布、分类/回归损失的相对量级、最优 loss 权重", "偏向新分配（顺带换了更合适的损失配比）", "分配与损失权重分开消融；或对两者各自做小规模调参"],
            ["<strong>换优化器</strong> SGD→AdamW", "最优 lr 相差 1–2 个数量级、weight decay 语义不同、warmup 需求", "严重偏向被调过的那一个", "各自做等预算的 lr 搜索，比较各自的最优"],
            ["<strong>换数据版本</strong> v7.1→v7.2", "训练集分布、<em>可能连评测集也一起变了</em>、类别表", "无法解释（这时任何模型对比都失效）", "数据版本必须与模型改动分开做实验，评测集永远冻结"],
        ]),
        H3("破坏方式二至四：漂移与打包"),
        UL([
            "<strong>基线漂移</strong>：baseline 的数字是三周前跑的，期间代码库合并了 7 个 PR（包括一次数据加载器的修复）。<em>你在和一个已经不存在的系统比较</em>。→ 规则：<strong>baseline 与实验必须在同一个 commit 上重跑</strong>，「用历史数字当 baseline」是最常见的隐性作弊。",
            "<strong>环境漂移</strong>：换了卡（A100→H100）、升了 CUDA、换了 cuDNN 版本、评测脚本改过一次。这些都能在 0.1–0.5 点的量级上移动结果，正好覆盖你要检测的效应量。→ 规则：环境写进 manifest，跨环境的对比要标注。",
            "<strong>打包改动</strong>：为了赶版本，一次改了 5 项，整体涨了 1.5，于是全部保留。<em>问题不是「不知道哪个有用」，而是「不知道其中哪个是负的」</em>——完全可能是 4 项各 +0.5、1 项 −0.5，你带着一个负收益的改动上线并永远不会发现。→ 规则：打包上线可以，但<strong>打包之后必须补做减法式消融</strong>（第 6 节）。",
        ]),
        DUAL(
            "有一个常见的误解需要澄清：单变量原则<strong>不等于「一次只改一行代码」</strong>。有些变量在物理上就是绑定的——batch size 与有效学习率、模型容量与最优训练时长、分辨率与 anchor 尺度。<em>硬拆它们只会得到「在次优配置下的公平对比」，那同样没有意义</em>。正确的做法是把它们当成一个<strong>耦合组</strong>整体替换，并在组内做标准补偿（如线性缩放规则），然后在实验记录里明确写出「本次改动的耦合组包含哪些变量」。",
            "更严谨地说，实验设计要控制的不是「变量个数」，而是<span class=\"term\">混杂因子</span>（confounder）——即那些同时影响「你的改动」和「你的指标」的第三个变量。<em>训练预算是检测实验里最大的混杂因子</em>：几乎所有「更强的方法」同时也更慢、更吃显存、需要更长的训练，于是在固定 wall-clock 或固定 epoch 的对比里，它们得到的实际训练量是不同的。<strong>面试里能主动说出「我把训练预算按 iteration 而不是 epoch 对齐，因为 Mosaic 会改变有效 epoch 的含义」这类话，是很强的信号</strong>——它说明你知道要控的是什么，而不只是知道有个原则叫单变量。",
        ),
        CALLOUT("danger", "<p><strong>面试高频追问，且极容易当场翻车。</strong>你说「我加了 Mosaic，mAP 涨了 1.2」，面试官会问：<em>「两边训练了多少 epoch？」「baseline 是重跑的还是用的历史数字？」「有没有 close-mosaic？」「跑了几个种子？」</em>——只要有一个答不上来，这个 1.2 就作废了，而且比不说更糟（因为暴露了你不知道要控什么）。<strong>安全的说法是把条件先说出来</strong>：「同一 commit、同 36 epoch、同分辨率、最后 10 epoch 关闭 Mosaic、3 个种子配对，均值 +1.2、配对差的标准差 0.18，配对 t 检验 p&lt;0.01。」<em>把条件说在前面，追问就没有落点了。</em></p>", "「涨了 1.2」——条件不说，数字就作废"),
    ])),

    # ============================================================== 2
    ("seed-variance", "种子方差：为什么 +0.3 很可能什么都不是", "".join([
        P("这是本模块、也可能是整门课里<strong>面试性价比最高的一节</strong>。它的结论只有一句话：<strong>同一份配置、同一份数据、只换随机种子，检测任务的 mAP 波动典型在 ±0.2–0.5 之间。所以一个 +0.3 的「提升」，在单次对比里有约 20% 的概率纯粹是噪声。</strong>"),
        H3("方差从哪里来"),
        TABLE(["方差来源", "机制", "能否关掉", "相对量级"], [
            ["<strong>权重初始化</strong>", "检测头/颈部是随机初始化的（backbone 通常预训练）", "能（固定种子）", "中"],
            ["<strong>数据顺序与 shuffle</strong>", "样本进入网络的顺序改变优化轨迹；小批量梯度是随机的", "能", "<strong>大</strong>"],
            ["<strong>增强的随机采样</strong>", "每个样本被 Mosaic/翻转/色彩抖动到什么程度是随机的", "能", "<strong>大</strong>（增强越强越大）"],
            ["<strong>Dropout / stochastic depth</strong>", "训练期随机丢弃", "能", "小-中"],
            ["<strong>cuDNN 非确定性算法</strong>", "某些卷积反向的原子加法顺序不定 → 浮点结果不可重复", "能但慢 20–40%（<code>deterministic=True</code>）", "小（但足以让两次「同种子」run 不完全相同）"],
            ["<strong>多卡梯度规约顺序</strong>", "AllReduce 的求和顺序随通信调度变化", "很难", "小"],
            ["<strong>评测集本身的抽样</strong>", "评测集只是真实分布的一个有限样本；AP 是它的非线性泛函", "不能（除非换更大的评测集）", "<strong>大，且不随种子平均消失</strong>"],
        ]),
        P("最后一行值得单独强调：<strong>多跑种子只能消除「训练随机性」，消不掉「评测集抽样随机性」</strong>。前者可以靠平均压下去，后者是你这个评测集固有的，只有加数据或换更大的集合才能减小。<em>这也是为什么「在自己的评测集上涨了 1 点」与「在另一批数据上也涨」是两个强度完全不同的证据。</em>"),
        H3("把它写成一个可计算的模型"),
        P("把第 $i$ 个配置、第 $j$ 个种子的结果写成："),
        MATH("\\mathrm{mAP}_{ij} \\;=\\; \\mu_i \\;+\\; s_j \\;+\\; \\varepsilon_{ij}\\,, \\qquad s_j \\sim \\mathcal N(0,\\sigma_s^2)\\ \\ (\\text{种子共享}),\\quad \\varepsilon_{ij} \\sim \\mathcal N(0,\\sigma_e^2)\\ \\ (\\text{配置内独立})"),
        P("$s_j$ 是「这个种子本身好不好」（初始化、数据顺序对两个配置的影响是相关的），$\\varepsilon_{ij}$ 是配置特有的噪声。于是两个配置比较时，差值的方差取决于你怎么设计实验："),
        MATH("\\operatorname{Var}(\\Delta)_{\\text{非配对}} = 2(\\sigma_s^2+\\sigma_e^2)\\,, \\qquad \\operatorname{Var}(\\Delta)_{\\text{配对}} = 2\\sigma_e^2 \\;\\;\\ll\\;\\; \\operatorname{Var}(\\Delta)_{\\text{非配对}}"),
        P("代入一组贴近检测实践的数字（$\\sigma_s=0.22$、$\\sigma_e=0.12$，于是单次 run 的标准差 $\\sigma=0.25$）："),
        TABLE(["量", "数值", "含义"], [
            ["单次 run 的 mAP 标准差 $\\sigma$", "<strong>0.25</strong>", "跑 5 个种子，最大值与最小值的<strong>期望极差约 0.58</strong>（$2.33\\sigma$）"],
            ["非配对单次比较的 $\\sigma_\\Delta$", "<strong>0.354</strong>", "$\\sqrt2 \\cdot 0.25$"],
            ["$P(\\Delta \\ge +0.3 \\mid \\text{真实差异}=0)$", "<strong>19.9%</strong>", "<strong>五次纯噪声对比里就有一次能看到「+0.3 的提升」</strong>"],
            ["$P(\\Delta \\ge +0.5 \\mid \\text{真实差异}=0)$", "7.9%", "连 +0.5 都有 1/13 的概率是假的"],
            ["配对单次比较的 $\\sigma_\\Delta$", "0.170", "$\\sqrt2\\cdot\\sigma_e$——配对把噪声砍掉了一半以上"],
            ["配对下 $P(\\Delta\\ge+0.3\\mid 0)$", "3.9%", "同样一次实验，配对设计把假阳性率从 20% 降到 4%"],
        ]),
        DUAL(
            "所以「+0.3 算不算提升」这个问题的正确回答不是「算」或「不算」，而是<strong>「取决于你的 σ 是多少、跑了几个种子、是不是配对的」</strong>。同样一个 +0.3：单种子非配对 → 五分之一的概率是噪声，不能采信；3 个种子配对且配对差的标准差 0.18 → $t = 0.3/(0.18/\\sqrt3) = 2.89$，$p\\approx0.10$，仍然不够但已经值得再跑两个种子；5 个种子配对 → 大概率能定下来。<em>关键是你要能报出这些数，而不是报一个孤零零的 0.3。</em>",
            "还有一个更精细的点：<strong>分桶指标的方差比整体 mAP 大得多</strong>。整体 mAP 在数千个实例上平均，而「夜间 + 小目标」桶可能只有几百个实例。AP 的抽样标准差大致随 $1/\\sqrt{n}$ 增长，所以一个只有 800 个实例的桶，其种子标准差可以到 <strong>0.8–1.5 点</strong>——是整体 mAP 的 3–6 倍。<em>这直接决定了回归门禁的阈值该怎么设</em>：如果你对每个桶都用「掉 0.5 就阻塞」的统一规则，小桶会天天误报警，团队三周内就会把门禁关掉。<strong>正确做法是每个桶用自己的 $2\\sigma_{\\text{bucket}}$ 作为阈值，而 $\\sigma_{\\text{bucket}}$ 必须先用多种子 baseline 测出来</strong>——这就是模块 00 第一周检查单里第 ③ 项的意义。<em>在 TSR 里这一点尤其致命：「停车让行」「注意儿童」这类关键类在一个评测集里可能只有几十到几百个实例，它们的 AP 种子标准差可以到 1–3 点</em>。<strong>所以关键类的门禁不能写成「掉一点就阻塞」（那会天天误报），而应该同时用两个判据：AP 掉幅超过 $2\\sigma_{\\text{class}}$，或者<u>绝对漏检实例数</u>增加——后者是整数计数，方差小得多，而且直接对应安全后果。</strong>",
        ),
        CALLOUT("danger", "<p><strong>「+0.3 算提升吗」是这个岗位的标志性面试题</strong>，因为它一句话就能把「跑过实验的人」和「负责过指标的人」分开。<em>不及格答法</em>：「算啊，0.3 也是涨。」／「不算吧，太小了。」——两者都没有依据。<strong>满分答法的骨架：①先反问口径</strong>（「整体 mAP 还是某个桶？几个种子？配对了吗？」）；<strong>②给出判据</strong>（「检测任务单次 run 的 mAP 标准差典型在 0.2–0.5，非配对单次比较的差值标准差是它的 √2 倍，所以真实差异为 0 时看到 +0.3 的概率约 20%——这个量级不能单独采信」）；<strong>③给出该怎么做</strong>（「同种子配对跑 3–5 组，做配对 t 或 bootstrap；同时看分桶是否一致——如果 +0.3 全部来自它理应影响的那个桶，证据强度会高很多」）；<strong>④给出退路</strong>（「如果算力做不起多种子，就退而求其次找多个弱证据的一致性：分桶方向一致、跨数据集一致、与机制预期一致」）。</p>", "面试标志题：+0.3 算提升吗"),
        CALLOUT("intuition", "一个能直接用的经验法则：<strong>把你项目的 baseline 跑 3–5 个种子，把每个桶的标准差 $\\sigma_{\\text{bucket}}$ 记在墙上。从此所有「提升」都以 $\\sigma$ 为单位报告</strong>（「+1.6σ」而不是「+0.4」）。<em>这一个动作能消灭团队里 80% 的伪提升，成本是一次性的 3–5 次训练。</em>"),
    ])),

    # ============================================================== 3
    ("significance", "多种子 + 配对检验：把「看起来涨了」变成「有多大把握」", "".join([
        P("知道有方差之后，下一步是用统计工具把「把握有多大」量出来。检测工程里真正需要的只有三件工具，且都能用几十行 numpy 写出来（notebook 里会全部实现）。"),
        H3("① 配对设计：先做设计，再谈检验"),
        P("配对的做法极简单：<strong>用同一组种子跑两个配置</strong>，比较每一对的差值 $d_j = \\mathrm{mAP}_{Bj} - \\mathrm{mAP}_{Aj}$。因为同一个种子下的 $s_j$ 在两边相同，它在做差时被完全抵消——这就是上一节公式里 $\\sigma_s$ 消失的来源。"),
        MATH("t \\;=\\; \\frac{\\bar d}{s_d/\\sqrt{n}}\\,, \\qquad \\bar d = \\frac1n\\sum_j d_j\\,, \\quad s_d^2 = \\frac{1}{n-1}\\sum_j (d_j-\\bar d)^2\\,, \\quad \\text{自由度 } \\nu = n-1"),
        P("<strong>配对不需要额外的算力预算</strong>——同样跑 $2n$ 次训练，只是把种子对齐了。这是本节里性价比最高的一条建议：<em>它是免费的方差削减</em>。"),
        H3("② Bootstrap：当分布不好假设时"),
        P("mAP 是一个高度非线性的汇总量（排序 → 累积 → 单调包络 → 面积），它的抽样分布没有好的解析形式。<span class=\"term\">bootstrap</span> 绕开这个问题：从已有样本有放回重采样，直接把统计量的分布模拟出来。<strong>但要分清两种 bootstrap，它们回答的是不同的问题</strong>："),
        TABLE(["bootstrap 的对象", "回答的问题", "适用场景", "陷阱"], [
            ["<strong>对种子重采样</strong>", "「如果我再跑一次训练，差值会落在哪」", "多种子实验的差值置信区间", "$n$ 只有 3–5 时 bootstrap 的分位数很粗糙，宁可用配对 t"],
            ["<strong>对评测图像重采样</strong>", "「如果换一批同分布的评测数据，mAP 会落在哪」", "评测集大小是否足够、绝对指标的不确定度", "<strong>必须按图像整体重采样</strong>，不能按框重采样（同图的框不独立）"],
            ["<strong>两者都做（分层）</strong>", "总不确定度", "写论文/写模型卡时的完整报告", "两个来源不能简单相加，要么嵌套模拟要么分开报告"],
        ]),
        H3("③ 多重比较：试得越多，越容易「发现」不存在的东西"),
        P("这是被忽略得最彻底的一条。假设你这个季度试了 20 个改动，每个都用 $\\alpha=0.05$ 判定："),
        MATH("P(\\text{至少一个假阳性}) \\;=\\; 1-(1-\\alpha)^m \\;=\\; 1-0.95^{20} \\;=\\; \\mathbf{64.2\\%}"),
        P("<strong>也就是说，一个什么都没做对的季度，有近三分之二的概率会「发现」至少一个显著提升。</strong>两种校正各有适用场景："),
        TABLE(["方法", "控制什么", "怎么做", "什么时候用", "代价"], [
            ["<strong>Bonferroni</strong>", "<span class=\"term\">FWER</span>（一个假阳性都不要）", "把阈值改成 $\\alpha/m$", "上线门禁、安全相关判定——<em>宁可漏掉真提升，不能放进假提升</em>", "非常保守，$m$ 大时几乎什么都通不过"],
            ["<strong>Benjamini–Hochberg</strong>", "<span class=\"term\">FDR</span>（被判显著的里面假的比例 ≤ q）", "$p$ 值升序排，找最大的 $k$ 使 $p_{(k)}\\le \\frac{k}{m}q$，拒绝前 $k$ 个", "探索阶段——<em>要的是「值得跟进的候选清单」</em>", "允许清单里混入 q 比例的假阳性"],
            ["<strong>预注册 + 分阶段</strong>", "实践上最有效", "探索阶段随便试，但候选必须在<strong>新的、没用过的评测切片</strong>上复现才算数", "团队日常流程", "需要预留一个「验证集的验证集」"],
        ]),
        DUAL(
            "第三行的「预注册 + 分阶段」在工程上比任何统计校正都好用，因为它不需要你算 $p$ 值。做法是把评测集切成 <strong>dev</strong>（随便看、随便试、随便调）和 <strong>holdout</strong>（每个改动只准跑一次，跑完就记账）。<em>探索在 dev 上做，确认在 holdout 上做</em>。这样多重比较的问题被隔离在 dev 上，而 holdout 上的数字保持诚实。<strong>代价是 holdout 会随着使用次数逐渐「变脏」，所以要有定期换血的机制。</strong>",
            "还有一个必须知道的边界条件：<strong>配对不是万能的，它的方差削减效果取决于两个配置的结果相关性</strong>。如果改动很小（加一个增强、调一个损失权重），同种子下 A 和 B 高度相关，配对能砍掉大部分方差；<em>但如果改动改变了随机性本身的作用（换优化器、换整个增强流水线、换 backbone），相关性会显著下降，配对的收益就没那么大了</em>。实践上应该<strong>实测这个相关系数</strong>：把配对差的标准差 $s_d$ 与单边标准差 $s$ 比较——若 $s_d \\approx \\sqrt2 s$，说明配对没起作用（相关性接近 0），此时就得老老实实加种子。notebook 里会把这个诊断实现出来。",
        ),
        CALLOUT("warn", "统计检验的一个常见误用：<strong>把 $p$ 值当成「提升有多大」的度量</strong>。$p$ 只回答「这个观测在零假设下有多罕见」，它随样本量增大而必然变小——跑 50 个种子，一个 +0.05 的差异也能做到 $p<0.001$，但那个 +0.05 在工程上毫无意义。<em>要同时报<strong>效应量</strong>（差了多少点、相当于几个 $\\sigma$）和<strong>置信区间</strong>（差值的 95% CI），$p$ 值只是附带信息</em>。面试里能说出「我更关心效应量和置信区间而不是 p 值」，是一个明显高于平均水平的回答。"),
    ])),

    # ============================================================== 4
    ("power", "功效分析：需要多少个种子才能检出 +0.3", "".join([
        P("上一节回答的是「已有数据，把握有多大」。这一节回答一个更早、更有用的问题：<strong>在开跑之前，先算出「要检出我期待的这个提升，我需要跑多少次训练」</strong>。这一步叫<span class=\"term\">功效分析</span>（power analysis），做了它，你就不会浪费两周跑一个注定说明不了任何问题的实验。"),
        H3("公式"),
        P("设显著性水平 $\\alpha$（通常 0.05，双侧）、检验功效 $1-\\beta$（通常 0.8，即真有效应时有 80% 的概率检出）、想检出的效应量 $\\delta$、差值的标准差 $\\sigma_\\Delta$，则所需的重复数为："),
        MATH("n \\;\\ge\\; \\frac{\\bigl(z_{1-\\alpha/2}+z_{1-\\beta}\\bigr)^2\\,\\sigma_\\Delta^2}{\\delta^2} \\;=\\; \\frac{(1.96+0.8416)^2\\,\\sigma_\\Delta^2}{\\delta^2} \\;=\\; \\frac{7.849\\,\\sigma_\\Delta^2}{\\delta^2}"),
        P("代入上一节的数字（$\\sigma=0.25$，配对差 $\\sigma_\\Delta^{\\text{配对}}=0.170$，非配对差 $\\sigma_\\Delta^{\\text{非配对}}=0.354$）："),
        TABLE(["要检出的效应 $\\delta$", "非配对（每组 $n$ / 总训练次数）", "配对（$n$ 对 / 总训练次数）", "现实评价"], [
            ["<strong>+0.3</strong>", "<strong>11 / 22 次</strong>", "<strong>3 / 6 次</strong>（模拟修正后 ≈5 / 10 次）", "配对把成本降到 1/4 左右"],
            ["+0.5", "4 / 8 次", "2 / 4 次（修正后 3 / 6）", "可承受"],
            ["+1.0", "1 / 2 次", "1 / 2 次", "单次对比就够——<em>所以大改动不需要统计学</em>"],
            ["+0.1", "99 / 198 次", "23 / 46 次", "<strong>做不起。这个量级的效应在检测里基本无法证实</strong>"],
        ]),
        CALLOUT("warn", "<p>上表里的「模拟修正后」不是笔误。<strong>那个闭式公式用的是正态分位数 $z$，而小样本下检验统计量服从 $t$ 分布，尾巴更厚</strong>——$n=3$ 时自由度只有 2，双侧 0.05 的临界值是 <strong>4.303</strong> 而不是 1.96。于是闭式给出的 $n=3$ 实际功效远低于 80%。<em>notebook 里会用蒙特卡洛把真实所需的 $n$ 搜出来，结论是配对约需 5–6 对</em>。<strong>可迁移的教训：小样本下所有基于正态近似的公式都会低估所需样本量，务必用模拟校验。</strong></p>", "闭式公式在小样本下会低估"),
        H3("反过来用：给定预算，你能检出多大的提升"),
        P("更常见的情形是预算先定死了（「这个实验最多跑 6 次训练」）。这时把公式反解，得到<span class=\"term\">最小可检效应</span>（minimum detectable effect, MDE）："),
        MATH("\\delta_{\\min} \\;=\\; \\bigl(z_{1-\\alpha/2}+z_{1-\\beta}\\bigr)\\,\\frac{\\sigma_\\Delta}{\\sqrt n} \\;\\approx\\; 2.80\\,\\frac{\\sigma_\\Delta}{\\sqrt n}"),
        P("预算 3 对配对实验 → $\\delta_{\\min}\\approx 2.80\\times0.170/\\sqrt3 = 0.27$（正态近似；<strong>notebook 里的蒙特卡洛给出真实值约 0.56，是闭式的两倍</strong>）。<strong>这句话的工程含义是：「我这次实验只能看见 0.5 以上的效应，0.5 以下的一律报『无结论』而不是『无效果』」</strong>——<em>「没有证据说明它有用」和「有证据说明它没用」是两个完全不同的结论，混淆这两者是实验解读里最常见的错误。</em>"),
        DUAL(
            "现实是残酷的：<strong>一次 COCO 规模的检测训练要几十 GPU-小时，绝大多数团队跑不起 10 次重复</strong>。所以真实工程里的做法不是「严格做显著性检验」，而是<em>用多个独立的弱证据凑出强证据</em>：①<strong>分桶一致性</strong>——如果这个改动只该影响小目标，那 mAP_small 涨、其他桶不动，比整体涨 0.3 有说服力得多；②<strong>跨数据集/跨规模一致性</strong>——在 tiny 和 small 两个模型尺寸上都涨，或在两个不同来源的评测集上都涨；③<strong>机制可解释性 + 事前预测</strong>——你能在实验前写下「我预期它会涨在哪个桶、大约多少」，然后观测吻合。",
            "第 ③ 条是最被低估的。<strong>事前写下预测，是把「事后找解释」这个最强的自欺来源堵死的唯一办法</strong>。人类在事后为任何数据模式编出合理解释的能力是无限的：涨了就是「有效」，没涨就是「数据不够」，掉了就是「需要调参」——三种结果都能被解释成支持你的假设。<em>而如果你在跑之前就写下「我预期 mAP_small +1.5~3.0、mAP_large 不动、延迟 +30%」，那么观测与预测的吻合度本身就是一个强证据，且它无法被事后改写</em>。<strong>这在面试里也是一个极强的信号——它对应临床试验里的「预注册」，说明你理解证据强度的来源。</strong>",
        ),
        CALLOUT("intuition", "把本节压成一句可执行的规则：<strong>开跑之前先算 MDE。如果 MDE 比你期待的效应还大，这个实验不值得跑</strong>——要么加预算，要么改设计（配对、共享评测集、降低方差），要么换一个效应更大的改动去做。<em>「跑完才发现说明不了任何问题」是研究工程里最贵的浪费。</em>"),
    ])),

    # ============================================================== 5
    ("fair", "公平对比的五个条件：让「谁更好」这个问题有意义", "".join([
        P("统计学解决的是「差异是不是噪声」。公平性解决的是<strong>「差异是不是来自你说的那个原因」</strong>。后者出问题时，统计再严谨也没用——你只是精确地测量了一个错误的量。"),
        TABLE(["条件", "违反的典型形式", "偏差方向", "典型量级", "怎么控"], [
            ["<strong>同训练预算</strong>", "新方法训 300 epoch，baseline 用论文里的 12 epoch 数字", "严重偏向新方法", "1–4 点", "两边都训到收敛；或按 iteration 对齐并报告曲线"],
            ["<strong>同增强</strong>", "新方法带 Mosaic + MixUp，baseline 只有翻转", "偏向新方法", "1–2 点", "增强作为独立变量单独消融"],
            ["<strong>同分辨率</strong>", "新方法 1280，baseline 640；或测试时分辨率与训练不一致", "偏向高分辨率（尤其小目标桶）", "<strong>3–6 点（mAP_small）</strong>", "分辨率写进对比表的每一行"],
            ["<strong>同调参预算</strong>", "新方法搜了 200 组超参，baseline 用默认值", "<strong>偏向被调的一方，且难以察觉</strong>", "0.5–2 点", "见第 7 节：等预算搜索，或报告 budget 曲线"],
            ["<strong>同评测集与评测代码</strong>", "评测集加过数据；IoU 口径不同（VOC vs COCO）；score 阈值不同", "任意方向", "<strong>任意大</strong>", "评测集冻结 + 哈希；评测代码进 CI"],
        ]),
        P("再加两条容易被忘掉的隐性条件："),
        UL([
            "<strong>同数值精度与硬件</strong>：fp16 与 fp32 训练的结果可以差 0.1–0.3；不同 GPU 上 cuDNN 选择的算法不同。<em>跨硬件的对比要标注，不要混在一张表里。</em>",
            "<strong>同后处理工作点</strong>：score 阈值、NMS IoU 阈值、max_det 上限。<em>一个模型在 score=0.05、另一个在 score=0.25 下评测，比的是两个不同的东西</em>；正确做法是要么统一，要么各自扫一遍取最优（并说明是各自最优）。",
        ]),
        ASCII("""公平对比自查表（贴在实验记录模板里，每次对比逐项打勾）

  [ ] 同一个 commit（**baseline 是重跑的，不是历史数字**）
  [ ] 同 iteration / epoch，且两边都训到收敛（画 loss 与 val 曲线确认）
  [ ] 同增强配方（差异项就是被测变量本身时，明确写出来）
  [ ] 同输入分辨率 + 同 letterbox 实现
  [ ] 同 batch size 与等效学习率（若不同，说明用了什么缩放规则）
  [ ] 同调参预算（各搜 N 组，或都用默认；**不能一边搜一边默认**）
  [ ] 同评测集版本 + 同评测代码版本（记哈希）
  [ ] 同后处理工作点（score / NMS IoU / max_det）
  [ ] 同精度（fp16/fp32）与同硬件；不同则标注
  [ ] **同一组随机种子（配对），且 n >= 3**
  [ ] 报告：均值 ± 标准差、配对差的 CI、分桶表、延迟与显存

  ▶ 打不满勾不是不能做实验，而是**必须把没打勾的那几项写进结论的限定条件**。
  ▶ 「在同 epoch、同增强下，A 比 B 高 1.2±0.3」是结论；
    「A 比 B 好」不是结论，是口号。"""),
        DUAL(
            "五条里<strong>「同调参预算」是最难做到也最容易被忽略的</strong>。原因很简单：你花在自己方法上的时间必然比花在 baseline 上的多——你会为它调学习率、调损失权重、调增强强度，而 baseline 你只是「跑一下」。<em>这个不对称不需要任何主观恶意就会自然发生</em>，它是研究工作的默认状态。<strong>所以公平对比需要主动对抗这个默认状态</strong>：要么给 baseline 同样的搜索预算，要么把「新方法只调了它自己引入的那一个超参」写清楚。",
            "在 TSR 这类<strong>两级 vs 端到端</strong>的架构对比里，公平性还有额外的层次。两级方案（类别无关检测 + crop 分类）与端到端多类检测的对比必须统一：<em>①端到端的延迟口径要包含 NMS，两级的要包含所有 crop 的分类耗时（且这个耗时随检出个数变化，要报 p99 而不是均值）；②两级的检测器只需分辨「是不是标志」，它的 mAP 与端到端的多类 mAP 根本不是同一个量，必须换算到<strong>端到端的最终类别级指标</strong>再比；③两级方案的 crop 分辨率是一个额外的自由度，不能一边用 128×128 一边把端到端限制在 640 输入</em>。<strong>面试里如果被问「你会选两级还是端到端」，先说清楚「在什么口径下比」，比直接给答案更能体现水平。</strong>",
        ),
        CALLOUT("danger", "<p><strong>「你怎么保证这个对比是公平的」是一道高区分度的面试题</strong>，而且它经常在你讲完一个项目后作为追问出现。<em>不及格答法</em>：「我们两边用的是同一套代码。」——这只覆盖了十条里的一条。<strong>满分答法是直接背出自查表的核心项并说明为什么</strong>：「同 commit 重跑 baseline（防基线漂移）、同 iteration 对齐（因为 Mosaic 会改变有效 epoch 的含义）、同调参预算（这是最容易出问题的一条，我给 baseline 也跑了同样规模的 lr 搜索）、评测集冻结并记哈希、同一组种子配对跑 3 组。最后报的是均值 ± 标准差和配对差的 95% 置信区间，不是一个孤立数字。」<em>面试官不需要你全对，他需要看到你有一张自查表，而不是靠感觉。</em></p>", "「你怎么保证对比公平」——要背得出自查表"),
    ])),

    # ============================================================== 6
    ("ablation", "消融设计：加法式与减法式为什么会给出相反的结论", "".join([
        P("消融（ablation）的目的是回答「这几个组件里，哪个才是真正起作用的」。它有两种做法，而<strong>大多数人不知道它们会给出不同的答案，也不知道该报哪个</strong>。"),
        TABLE(["设计", "做法", "度量的是什么", "偏差"], [
            ["<strong>加法式</strong>（additive / bottom-up）", "从 baseline 出发，每次<em>加一个</em>组件", "该组件的<strong>主效应</strong>（在没有其他组件时的贡献）", "<strong>高估冗余组件</strong>——两个做同一件事的组件，各自单独加都涨"],
            ["<strong>减法式</strong>（subtractive / leave-one-out）", "从完整系统出发，每次<em>去掉一个</em>组件", "该组件的<strong>边际贡献</strong>（在其他组件都在时还剩多少）", "<strong>低估冗余组件、高估协同组件</strong>"],
            ["<strong>全子集 + Shapley</strong>", "跑遍 $2^k$ 个子集，按 Shapley 值分摊", "公理化的<strong>公平分摊</strong>（效率 / 对称 / 虚拟 / 可加）", "无偏，但代价 $2^k$"],
        ]),
        H3("一个具体的数字例子（notebook 会完整跑出来）"),
        P("设有三个组件 A（Mosaic）、B（copy-paste）、C（更长训练），baseline 40.0。真实的响应函数含交互项：A 与 B 有<strong>冗余</strong>（都在制造更多小目标，交互 −0.8），B 与 C 有<strong>协同</strong>（更多合成数据需要更长训练才吃得下，交互 +0.5），A 与 C 轻微冲突（−0.3），三者同时有 +0.2 的高阶项。完整系统 42.2，总增益 <strong>+2.2</strong>。三种归因给出的「A 的贡献」是："),
        TABLE(["组件", "加法式（单独加）", "减法式（从 full 去掉）", "Shapley 值", "结论差异"], [
            ["<strong>A（Mosaic）</strong>", "<strong>+1.00</strong>", "<strong>+0.10</strong>", "+0.52", "<strong>相差 10 倍</strong>——同一组实验，两种读法"],
            ["B（copy-paste）", "+1.00", "+0.90", "+0.92", "一致（它与别人的交互相互抵消了）"],
            ["C（更长训练）", "+0.60", "+1.00", "+0.77", "减法式高估（它与 B 的协同都被算给了它）"],
            ["<strong>合计</strong>", "2.60 ≠ 2.20", "2.00 ≠ 2.20", "<strong>2.20 = 2.20</strong> ✅", "只有 Shapley 满足「加总等于总增益」"],
        ]),
        P("<strong>关键在于：加法式和减法式都没有算错，它们只是在回答不同的问题。</strong>加法式回答「如果我只能加一个，加哪个」；减法式回答「如果我要砍掉一个省成本，砍哪个代价最小」。<em>把其中任何一个说成「A 的贡献」这个唯一数字，都是错的。</em>"),
        DUAL(
            "工程上该怎么办？<strong>三条实用规则</strong>：①<em>当你要决定「上不上线」时用减法式</em>——因为部署形态就是完整系统，你关心的是「去掉它会掉多少」；②<em>当你要决定「下一步做什么」时用加法式</em>——因为你的起点是当前系统，你关心的是「单独加一个新东西能涨多少」；③<em>当组件数 $k\\le4$ 时直接跑全子集</em>（$2^4=16$ 组实验，配合多种子仍在可承受范围），因为它顺带把交互作用也测出来了，而交互作用往往比主效应更有信息量。",
            "关于 <span class=\"term\">Shapley value</span>：它是合作博弈论里对「联盟总收益如何公平分摊给成员」的唯一满足四条公理（效率、对称性、虚拟成员、可加性）的解。公式是对所有加入顺序求平均：$\\phi_i = \\sum_{S\\subseteq N\\setminus\\{i\\}} \\frac{|S|!\\,(n-|S|-1)!}{n!}\\bigl[f(S\\cup\\{i\\})-f(S)\\bigr]$。<em>它在 ML 里更常见的化身是 SHAP（特征归因），但用在消融上同样自然</em>：把「组件」当成玩家、把「mAP」当成联盟收益。<strong>它的唯一问题是 $2^k$ 的代价</strong>——$k=6$ 时 64 组实验、配合 3 个种子就是 192 次训练，已经不现实。<em>此时的实用退路是「报告加法式与减法式两端，并把两端差距大的组件标记为『存在显著交互，需要单独研究』」</em>——这个做法几乎零成本，却能避免绝大多数错误结论。",
        ),
        CALLOUT("intuition", "记住这个判据：<strong>如果加法式和减法式给出的贡献差得很远，那不是数据有问题，那正是「存在交互作用」的信号，而且这个信号本身就是有价值的发现</strong>。在上面的例子里，A 的两个数字差 10 倍，直接告诉你「Mosaic 和 copy-paste 在做同一件事」——<em>这个结论比「Mosaic 涨 1.0 点」有用得多，因为它意味着你可以砍掉一个来省训练时间</em>。"),
        CALLOUT("warn", "消融的另一个高频错误：<strong>消融时没有重新调参</strong>。去掉 Mosaic 之后，原来为强增强配置的 300 epoch 变成了过拟合，于是「去掉 Mosaic 掉 3 点」——但其中至少一半是「训练时长不再匹配」造成的。<em>严格的消融要求每个子集各自调到最优，而这会让代价再乘一个系数</em>。实践中的折中是：<strong>至少对训练时长这一个最敏感的耦合变量做补偿</strong>，并在报告里注明其余超参沿用完整系统的配置。"),
    ])),

    # ============================================================== 7
    ("hpo", "超参搜索预算与「调参不公平」陷阱", "".join([
        P("这是「公平对比」里最隐蔽的一条，值得单独一节。它的形态是：<strong>新方法被调了 200 组超参，baseline 用了论文里的默认值——然后你报告说新方法涨了 1.5 点。</strong>问题是：这 1.5 点里，有多少是方法带来的，有多少只是「被调过」带来的？"),
        H3("为什么「调过」本身就能涨点"),
        P("把超参搜索看成一个抽样过程：每次抽一组超参，得到一个结果。<strong>报告最优的那一次，等于报告 $n$ 次抽样的最大值——而最大值随 $n$ 单调增长，与方法好坏无关。</strong>设单次抽样超过 baseline 的概率为 $p$，则："),
        MATH("P(\\text{至少一次超过 baseline}) \\;=\\; 1-(1-p)^n \\quad\\Longrightarrow\\quad p=0.10,\\ n=20 \\;\\Rightarrow\\; \\mathbf{87.8\\%}"),
        P("<strong>也就是说，即使你的方法完全不比 baseline 好，只要允许你随机调 20 组超参，你有 88% 的概率能找到一组「涨了」的配置。</strong>这不是作弊，这是搜索的数学性质——但如果你只报最优那一组而不报预算，读者（和面试官）会把它误读成方法的效果。"),
        TABLE(["报告方式", "内容", "读者能判断什么", "评价"], [
            ["<strong>只报最优</strong>", "「我们的方法达到 53.1 AP」", "什么都判断不了", "❌ 最常见，也最没有信息量"],
            ["报最优 + 预算", "「搜索 50 组，最优 53.1」", "至少知道搜索规模", "🟡 及格线"],
            ["<strong>报预算-期望最优曲线</strong>", "「预算 1/5/10/50 组时的期望最优分别是 51.2 / 52.3 / 52.7 / 53.1」", "<strong>在相同预算下比较两个方法</strong>；还能看出方法对超参的敏感度", "✅ Dodge et al. 推荐；曲线越平说明方法越鲁棒"],
            ["<strong>等预算对照</strong>", "「两个方法各搜 50 组，各自的最优是 53.1 vs 52.4」", "直接可比", "✅ 工程上最实用"],
        ]),
        P("<strong>预算-期望最优曲线</strong>的计算不需要额外实验：把你已经跑过的 $N$ 组结果保存下来，用有放回重采样估计「如果只有预算 $n$，期望能拿到的最优值是多少」。notebook 里会实现这个估计器——<em>它是把「已经跑过的所有实验」变成可发表证据的最便宜手段。</em>"),
        DUAL(
            "这条陷阱有一个很反直觉的推论：<strong>「对超参不敏感」本身是方法的一个重要优点，而只报最优值的做法会把这个优点完全抹掉</strong>。两个方法都能调到 53.1，但一个在预算 5 组时就到 52.9、另一个要 50 组才到 52.7——前者在工程上远优于后者（换数据集、换分辨率时不用重调）。<em>预算-期望最优曲线正好把这个差别显示出来：曲线越早变平，方法越鲁棒。</em>",
            "在量产场景里这个问题会以另一种形式出现：<strong>你的超参是在当前数据版本上调的，而数据每周都在增长</strong>。一个高度依赖超参的方法，会在数据更新后悄悄退化——因为原来的最优点已经漂走了，而没有人会为每次数据更新重跑一次搜索。<em>所以「在多个数据版本上都用同一组超参也能工作」是量产系统的硬需求</em>，它比「在某个版本上调到极致」重要得多。<strong>面试里主动提这一点，等于告诉对方你考虑过「上线之后」的事。</strong>",
        ),
        CALLOUT("danger", "<p><strong>面试追问预案：「你的 baseline 调过参吗？」</strong>这是一个陷阱题，因为两个方向的诚实回答都可能扣分——说「调过」要能说出调了什么、多大预算；说「没调」等于承认对比不公平。<em>安全且真实的答法</em>：<strong>「baseline 我用的是官方配方（它本身就是被社区调过的），我的改动只引入了一个新超参，我对这一个超参做了 5 组扫描并报告了全部 5 组，不是只报最优。另外我在两个模型尺寸上都验证了同一个结论——如果提升只来自调参，它不会在两个尺寸上都成立。」</strong><em>后半句是关键：跨配置的一致性是对抗「调参幻觉」的最强证据，而且几乎免费。</em></p>", "「你的 baseline 调过参吗」"),
    ])),

    # ============================================================== 8
    ("record", "实验记录与可复现：最小必要字段和一份实操清单", "".join([
        P("前面七节讲的所有东西，只有在实验能被记录、被检索、被重现时才有累积价值。否则每一次实验都是一次性的消耗品，团队的知识永远停留在「大家印象中好像是……」。"),
        H3("先分清三层可复现"),
        TABLE(["层级", "定义", "达成条件", "什么时候需要"], [
            ["<strong>逐位可复现</strong>（bit-wise）", "两次运行的权重逐位相同", "固定全部种子 + <code>cudnn.deterministic</code> + 单卡 + 固定库版本", "调试数值 bug、验证重构没改变行为；<em>代价是慢 20–40%，日常不必开</em>"],
            ["<strong>统计可复现</strong>（statistical）", "重跑落在多种子分布内", "manifest 完整 + 数据与代码版本固定", "<strong>日常标准。这一层做不到，一切实验结论都不可信</strong>"],
            ["<strong>概念可复现</strong>（conceptual）", "别人按你的描述独立实现，能得到同向结论", "方法描述完整 + 关键超参公开 + 报告了方差", "论文/技术分享；也是<strong>交接的真正标准</strong>"],
        ]),
        H3("实验记录的最小必要字段"),
        P("模块 00 给了 manifest 的完整结构，这里补充<strong>为什么每一项都是必需的</strong>——每一项都对应一类「三个月后无法回答的问题」："),
        TABLE(["字段", "缺了它，哪个问题回答不了", "常见的偷懒形式"], [
            ["<strong>代码 commit + dirty 标记</strong>", "「这次实验用的到底是哪版代码」", "只记分支名（分支会移动）"],
            ["<strong>数据版本（含哈希）</strong>", "「训练集是加数据之前还是之后的」", "只记路径（路径下的内容会变）"],
            ["<strong>完整配置（展开，非 diff）</strong>", "「当时那个 lr 是多少」——base config 后来改过了", "只存与 base 的 diff"],
            ["<strong>环境</strong>（python/库/驱动/GPU）", "「为什么现在重跑差了 0.4」", "完全不记"],
            ["<strong>随机种子</strong>", "「这个差异是改动还是噪声」——<em>本模块全部内容的前提</em>", "记了但训练脚本里其实没真正固定住"],
            ["<strong>完整指标（含全部分桶）</strong>", "「当时夜间桶是多少」——评测代码已经改过", "只存整体 mAP"],
            ["<strong>评测集版本 + 评测代码版本</strong>", "「这两个数字可比吗」", "假设评测集永远不变"],
            ["<strong>训练时长与硬件</strong>", "「这个方法的实际成本是多少」", "不记，于是无法算 ROI"],
            ["<strong>对照 run 的 id</strong>", "「这次实验的 baseline 是哪一次」", "写「和之前那个比」"],
        ]),
        ASCII("""可复现实操清单（按顺序做，每项都有可验证的通过条件）

  1. 训练脚本启动时**第一件事**：写 manifest（而不是结束时写）
     └ 崩溃的 run 也要有记录，否则"跑了但没结果"的实验会被重复做

  2. 种子要固定**四处**，少一处就前功尽弃：
       random.seed(s) / np.random.seed(s) / torch.manual_seed(s)
       + DataLoader 的 worker_init_fn（**每个 worker 有独立 RNG**）
     └ 验证：跑两次前 100 步，loss 序列必须逐值相同

  3. 数据版本 = 内容哈希，不是路径也不是日期
     └ 验证：sha256 清单进 manifest；数据目录设为只读

  4. 评测集**冻结**，评测代码进 CI
     └ 验证：拿一个固定 ckpt，每天 CI 跑一次，mAP 必须完全不变

  5. baseline 与实验**同 commit 重跑**，且用同一组种子
     └ 验证：manifest 里的 baseline_run_id 指向本周的 run，不是上个月的

  6. 结果落库时同时存：全量指标 + 分桶 + 延迟 + 显存 + wall-clock
     └ 验证：能直接查询"某个桶在过去 20 次 run 里的走势"

  7. 每月做一次**复现演练**：随机抽一个 30 天前的 run 重跑
     └ 通过条件：落在多种子分布的 2σ 内；不落则说明有未记录的漂移""")
        ,
        DUAL(
            "第 2 条里的 <code>worker_init_fn</code> 值得单独说，因为它是一个<strong>真实事故</strong>而不是理论风险：PyTorch 的 DataLoader 多进程 worker 会各自继承主进程的 numpy 随机状态，<em>如果不在 <code>worker_init_fn</code> 里给每个 worker 设不同的种子，所有 worker 会生成完全相同的增强随机数</em>。症状是训练看起来正常、loss 也降，但你的增强多样性实际上只有 <code>1/num_workers</code>——mAP 会莫名其妙低 0.5–1.5 点，而且极难发现。<strong>C56 模块 04 有完整的复现实验。</strong>",
            "第 7 条的「复现演练」是整个清单里最容易被跳过、也最能暴露问题的一条。<em>它检验的不是某一次 run，而是你的记录系统本身是否完整</em>——只要有任何一个未被记录的变量在漂移（库版本、驱动、数据软链接指向、某个没进 git 的本地脚本），演练就会失败。<strong>而这类漂移在平时是完全隐形的：它不会报错，只会让你的历史数字慢慢变得不可比</strong>。定期演练相当于给可复现性加了一个<span class=\"term\">金丝雀测试</span>。<em>在 TSR 这种「模型要在车上跑三年、期间不断迭代」的场景里，「三年前那版为什么比现在这版在隧道口好」是一个真实会被问到的问题——能不能回答它，取决于你今天有没有做第 7 条。</em>",
        ),
        CALLOUT("warn", "记录系统的一个常见失败模式是<strong>「记了但没人用」</strong>：字段很全、写进了实验追踪平台，但没有人在做决策时去查。<em>判断记录系统是否真的在工作，看一个指标：「上一次有人查询三个月前的 run 是什么时候」</em>。如果答案是「没有过」，那这套记录就只是仪式。<strong>让它活起来的最有效办法是把它接进门禁</strong>——回归门禁必须去查历史 run 的分桶数字来算阈值，于是记录系统就有了不可替代的读取方。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("实验方法学这个领域正在从「大家心照不宣的手艺」变成「有明确规范的工程学科」，但仍有几个真正未解的问题。它们既是研究机会，也是很好的面试谈资。"),
        UL([
            "<strong>大模型时代的方差报告困境。</strong>训练成本越高，重复实验越不可行，而效应量却在变小（成熟领域的改进普遍在 0.1–0.5 点）。<em>「成本上升 × 效应量下降」这个剪刀差意味着：越是前沿的工作，越难被统计学证实</em>。目前的替代路径（跨规模一致性、scaling law 外推、机制解释）都还没有形成公认的证据强度标准。这可能是当前 ML 实证方法学最重要的开放问题。",
            "<strong>方差的来源分解仍不完整。</strong>Bouthillier 等人把 benchmark 方差拆成了数据划分、初始化、数据顺序、超参搜索等来源，但检测任务特有的来源——<em>标注噪声、评测集的类别分布抽样、NMS 与 score 阈值的交互——还没有系统的量化工作</em>。「一个 TSR 评测集需要多少实例，才能让夜间桶的 AP 标准差降到 0.3 以下」这类问题目前只能靠经验。",
            "<strong>交互作用的高效估计。</strong>Shapley 需要 $2^k$ 次实验，而部分因子设计（fractional factorial design）、响应面方法这些统计学里成熟了几十年的工具，在 ML 消融里几乎没有被使用。<em>「用 $O(k^2)$ 次实验估计出所有二阶交互」在原理上是可行的，但缺少现成的工具与共识</em>。",
            "<strong>自动化实验与统计严谨性的冲突。</strong>当 agent 能自动改配置、跑训练、读指标时，「试到显著为止」这种坏实践的速度会被放大几个数量级——<em>一个能自主跑 1000 次实验的 agent，几乎必然能找到「显著」的伪结果</em>。多重比较校正、预注册、以及「自动化实验的审计日志」正在成为新的系统设计需求，但还没有成熟方案。",
            "<strong>评测集老化与隐性过拟合。</strong>同一个评测集被反复使用后，社区在其上报告的提升有多少来自真实进步、多少来自对该集合的适应？Recht 等人的重采样实验给出了部分答案（绝对值下降但排序基本保持），<em>但对自动驾驶这类「评测集与训练集来自同一批采集」的场景，这个问题更严重且缺少研究</em>。",
            "<strong>离线指标与下游价值的对齐。</strong>mAP 涨了、路测体验没变，是自动驾驶感知的常态。<em>「什么样的离线指标能预测下游安全收益」目前没有公认答案</em>；代价敏感 mAP、场景加权、规则违反率代理各有缺陷（C55 模块 05 展开）。这既是评测问题，也是实验设计问题——<strong>因为如果你的目标指标本身与价值不对齐，再严谨的实验设计也只是在精确地优化一个错误的东西。</strong>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Bouthillier, Delaunay, Bronzi et al., <em>Accounting for Variance in Machine Learning Benchmarks</em>（MLSys 2021）——本节全部方差论述的理论基础；重点看它对「多个方差源的相对贡献」的分解，以及「固定种子反而会低估真实方差」这个反直觉结论。<strong>★</strong> Dodge, Gururangan, Card et al., <em>Show Your Work: Improved Reporting of Experimental Results</em>（EMNLP 2019）——预算-期望最优曲线的出处，第 7 节的直接来源。<strong>★</strong> Henderson, Islam, Bachman et al., <em>Deep Reinforcement Learning that Matters</em>（AAAI 2018）——多种子与报告规范的经典警世文，图 1（同一算法不同种子的学习曲线）值得记住。</p><p>统计工具：Benjamini &amp; Hochberg, <em>Controlling the False Discovery Rate</em>（JRSS-B 1995，BH 校正原文）；Efron &amp; Tibshirani, <em>An Introduction to the Bootstrap</em>（1993）；Demšar, <em>Statistical Comparisons of Classifiers over Multiple Data Sets</em>（JMLR 2006，多数据集比较的规范）；Shapley, <em>A Value for n-Person Games</em>（1953，消融归因的公理基础）。方法学批评：Lipton &amp; Steinhardt, <em>Troubling Trends in Machine Learning Scholarship</em>（2018）；Musgrave, Belongie &amp; Lim, <em>A Metric Learning Reality Check</em>（ECCV 2020，公平对比后大部分提升消失的实证）；Melis, Dyer &amp; Blunsom, <em>On the State of the Art of Evaluation in Neural Language Models</em>（ICLR 2018，等预算调参后老模型反超）；Recht et al., <em>Do ImageNet Classifiers Generalize to ImageNet?</em>（ICML 2019）；Pineau et al., <em>Improving Reproducibility in Machine Learning Research</em>（JMLR 2021）。相邻课程：模块 00（三个核心能力）、模块 02（误差分析：实验之后往哪走）、模块 03（调试手册）、C37（实验追踪与 MLOps）、C40（研究方法论）、C56 模块 05（增强的消融与验证）、C58 模块 05（闭环验证与回归门禁）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 01 · 实验设计与归因（种子方差 / 配对检验 / 功效分析 / 消融偏差 / 记录 schema）

目标：把「**+0.3 到底算不算提升**」这个问题，从一场辩论变成一次计算。

本 notebook 你会亲手实现：
1. **种子方差的生成模型**（$\\mathrm{mAP}=\\mu+s_j+\\varepsilon$），并算出 5 个种子的期望极差
2. **单次对比的假阳性率**：真实差异为 0 时，看到「+0.3」的概率是多少（闭式 + 蒙特卡洛互相验证）
3. **配对设计**：同一批数据，配对分析 $p=0.002$、非配对分析 $p=0.20$ —— 设计决定你能不能看见效应
4. **Student-t 尾概率**（不用 scipy，自己写不完全 Beta 函数的连分数展开），并对已知临界值校验
5. **两种 bootstrap**：对种子重采样 vs 对评测图像重采样，它们回答不同的问题
6. **多重比较**：20 个改动 → 64% 概率至少一个假阳性；Bonferroni 与 Benjamini–Hochberg
7. **功效分析**：闭式公式 + 蒙特卡洛搜索，证明**正态近似在小样本下会低估所需种子数**
8. **消融的三种归因**：加法式 / 减法式 / Shapley —— 同一组实验，A 的贡献相差 10 倍
9. **调参预算的期望最优曲线**，以及「baseline 没调参」到底能偷走多少个点
10. **实验记录 schema 与公平性审计器**

> 心智模型：**没有方差估计的"提升"不是结论，是观测。
> 而把观测变成结论，只需要三样东西：配对设计、多种子、效应量与置信区间。**"""),

    md("""## 1 · 种子方差的生成模型

$$\\mathrm{mAP}_{ij} = \\mu_i + s_j + \\varepsilon_{ij}, \\qquad
s_j\\sim\\mathcal N(0,\\sigma_s^2)\\ (\\text{种子共享}),\\quad
\\varepsilon_{ij}\\sim\\mathcal N(0,\\sigma_e^2)\\ (\\text{配置内独立})$$

取 $\\sigma_s=0.22$、$\\sigma_e=0.12$，于是单次 run 的标准差 $\\sigma=0.2506$ ——
落在「检测任务典型 ±0.2–0.5」这个经验区间里。"""),

    code("""import math, json, itertools
import numpy as np
from statistics import NormalDist

SIGMA_S, SIGMA_E = 0.22, 0.12          # 种子共享 / 配置内独立
SIGMA = math.hypot(SIGMA_S, SIGMA_E)   # 单次 run 的总标准差
print(f'sigma_s={SIGMA_S}  sigma_e={SIGMA_E}  ->  单次 run 的 sigma = {SIGMA:.4f}')

def simulate_runs(mu, n_seeds, rng, seed_effects=None):
    '''模拟同一配置在 n_seeds 个种子下的 mAP。
       seed_effects 传入时表示"复用同一组种子"（= 配对设计）。'''
    s = rng.normal(0, SIGMA_S, size=n_seeds) if seed_effects is None else np.asarray(seed_effects)
    return mu + s + rng.normal(0, SIGMA_E, size=n_seeds), s

rng = np.random.default_rng(20260817)
runs, _ = simulate_runs(41.80, 5, rng)
print('\\n同一份配置、同一份数据，只换种子跑 5 次：')
print('  mAP =', np.round(runs, 3))
print(f'  均值 {runs.mean():.3f}   标准差 {runs.std(ddof=1):.3f}   '
      f'极差 {runs.max()-runs.min():.3f}')

# 5 个种子的**期望极差**：标准正态下是 2.326 sigma
r2 = np.random.default_rng(0)
z = r2.normal(size=(100000, 5))
exp_range_std = float((z.max(1) - z.min(1)).mean())
print(f'\\nE[极差 | n=5 标准正态] = {exp_range_std:.4f} sigma')
print(f'换算到 mAP：{exp_range_std * SIGMA:.4f} 点')
assert abs(exp_range_std - 2.326) < 0.02, exp_range_std
assert abs(exp_range_std * SIGMA - 0.583) < 0.02
print('\\n⚠️  **跑 5 个种子，最好的一次比最差的一次高约 0.58 个 mAP —— 而它们完全相同。**')
print('    如果你只跑一次就和 baseline 比，你比较的一半是配置，一半是运气。')"""),

    md("""## 2 · 「+0.3 是提升吗」：单次对比的假阳性率

真实差异 $\\delta=0$ 时，观测到 $\\Delta \\ge 0.3$ 的概率是多少？
非配对时 $\\sigma_\\Delta=\\sqrt2\\,\\sigma$，配对时 $\\sigma_\\Delta=\\sqrt2\\,\\sigma_e$。"""),

    code("""ND = NormalDist()

def p_false_positive(threshold, sd_diff):
    '''真实差异为 0 时，观测差值 >= threshold 的概率。'''
    return 1.0 - ND.cdf(threshold / sd_diff)

SD_UNPAIRED = math.sqrt(2) * SIGMA        # 非配对：两边的种子效应都保留
SD_PAIRED   = math.sqrt(2) * SIGMA_E      # 配对：种子效应被抵消
print(f'非配对单次比较 sigma_delta = {SD_UNPAIRED:.4f}')
print(f'配对  单次比较 sigma_delta = {SD_PAIRED:.4f}   （砍掉了 {1-SD_PAIRED/SD_UNPAIRED:.0%}）\\n')

print(f"{'观测到的"提升"':>14s} {'非配对假阳性率':>16s} {'配对假阳性率':>14s}")
for thr in [0.1, 0.2, 0.3, 0.5, 0.8, 1.0]:
    print(f'{thr:>14.1f} {p_false_positive(thr, SD_UNPAIRED):>16.1%} '
          f'{p_false_positive(thr, SD_PAIRED):>14.1%}')

p03 = p_false_positive(0.3, SD_UNPAIRED)
p05 = p_false_positive(0.5, SD_UNPAIRED)
assert abs(p03 - 0.1986) < 1e-3, p03
assert abs(p05 - 0.0791) < 1e-3, p05
assert abs(p_false_positive(0.3, SD_PAIRED) - 0.0385) < 1e-3

# 蒙特卡洛互相验证（闭式与模拟必须对得上，否则是公式写错了）
r3 = np.random.default_rng(7)
sim = r3.normal(0.0, SD_UNPAIRED, size=400000)
mc03 = float((sim >= 0.3).mean())
print(f'\\n蒙特卡洛校验：P(>=0.3) 闭式 {p03:.4f} vs 模拟 {mc03:.4f}')
assert abs(mc03 - p03) < 0.005, (mc03, p03)
print('\\n⚠️  **真实差异为 0 时，单次非配对对比有 19.9% 的概率显示"+0.3 的提升"。**')
print('    五次这样的对比里就有一次会骗到你。而一个季度做 20 次对比是很正常的。')
print('✅ 面试答法：先反问口径（哪个指标/几个种子/配对没有），再给这个 20% 的数。')"""),

    md("""## 3 · 配对设计：免费的方差削减

配对不需要额外算力——同样跑 $2n$ 次训练，只是把种子对齐了。
下面用**同一批数据**做两种分析，看结论差多少。"""),

    code("""# 一次真实规模的实验：baseline 41.80，新方法真实高 0.35，5 个种子**配对**
n = 5
rg = np.random.default_rng(2)
s_shared = rg.normal(0, SIGMA_S, size=n)              # 两个配置共享的种子效应
A = 41.80 + s_shared + rg.normal(0, SIGMA_E, size=n)  # baseline
B = 41.80 + 0.35 + s_shared + rg.normal(0, SIGMA_E, size=n)   # 新方法

print(f"{'种子':>4s} {'baseline':>10s} {'新方法':>10s} {'配对差':>8s}")
for j in range(n):
    print(f'{j:>4d} {A[j]:>10.3f} {B[j]:>10.3f} {B[j]-A[j]:>+8.3f}')
d = B - A
print(f'\\n均值      {A.mean():>10.3f} {B.mean():>10.3f} {d.mean():>+8.3f}')
print(f'标准差    {A.std(ddof=1):>10.3f} {B.std(ddof=1):>10.3f} {d.std(ddof=1):>8.3f}')

# 关键观察：**单边标准差 0.32/0.40，而配对差的标准差只有 0.105**
assert A.std(ddof=1) > 0.25 and B.std(ddof=1) > 0.25
assert d.std(ddof=1) < 0.15
corr = float(np.corrcoef(A, B)[0, 1])
print(f'\\nA 与 B 的配对相关系数 r = {corr:.3f}  （理论值 sigma_s^2/(sigma_s^2+sigma_e^2) = '
      f'{SIGMA_S**2/(SIGMA_S**2+SIGMA_E**2):.3f}）')
assert corr > 0.9
print('\\n✅ 配对差的标准差 0.105 << 单边标准差 0.32 —— 种子效应在做差时被抵消了。')
print('   **这就是"免费的方差削减"：同样 10 次训练，配对设计的信噪比高一倍以上。**')"""),

    code("""# 配对是否真的起作用？做一个可以直接用在项目里的诊断
def pairing_diagnostic(a, b):
    '''若配对无效（相关性≈0），s_d 会接近 sqrt(2)*s_单边；
       若配对有效，s_d 会显著小于它。返回 (s_d, 无效时的期望 s_d, 方差削减比)。'''
    a, b = np.asarray(a, float), np.asarray(b, float)
    s_side = math.sqrt(0.5 * (a.var(ddof=1) + b.var(ddof=1)))
    s_d = (b - a).std(ddof=1)
    return s_d, math.sqrt(2) * s_side, 1 - s_d / (math.sqrt(2) * s_side)

s_d, s_d_if_useless, cut = pairing_diagnostic(A, B)
print(f'实际配对差标准差       s_d = {s_d:.4f}')
print(f'若配对完全无效应为     s_d = {s_d_if_useless:.4f}')
print(f'方差削减              {cut:.1%}')
assert cut > 0.5, '本例中配对应削减一半以上'

# 反例：改动改变了随机性本身的作用（如换优化器），种子效应不再共享
# 单次 n=5 的削减比噪声很大，所以做 2000 次复现取均值
rg2 = np.random.default_rng(5)
cuts_shared, cuts_broken = [], []
for _ in range(2000):
    s0 = rg2.normal(0, SIGMA_S, size=n)
    a1 = 41.80 + s0 + rg2.normal(0, SIGMA_E, size=n)
    b1 = 42.15 + s0 + rg2.normal(0, SIGMA_E, size=n)          # 种子效应共享
    cuts_shared.append(pairing_diagnostic(a1, b1)[2])
    a2 = 41.80 + rg2.normal(0, SIGMA_S, size=n) + rg2.normal(0, SIGMA_E, size=n)
    b2 = 42.15 + rg2.normal(0, SIGMA_S, size=n) + rg2.normal(0, SIGMA_E, size=n)  # 不共享
    cuts_broken.append(pairing_diagnostic(a2, b2)[2])
c_ok, c_bad = float(np.mean(cuts_shared)), float(np.mean(cuts_broken))
print(f'\\n2000 次复现的平均方差削减：')
print(f'  种子效应共享（配对有效）  {c_ok:.1%}   （理论上限 1 - sigma_e/sigma = '
      f'{1 - SIGMA_E/SIGMA:.1%}）')
print(f'  种子效应不共享（配对失效）{c_bad:.1%}')
assert c_ok > 0.40 and c_bad < 0.10, (c_ok, c_bad)
print('⚠️  **配对不是万能的**：如果改动改变了随机性的作用（换优化器/换整套增强/换 backbone），')
print('    同种子下两边的相关性会掉下来，配对收益变小 —— 这时只能老实加种子。')
print('✅ 所以每次配对实验都应该跑一遍这个诊断，而不是假设配对一定有效。')"""),

    md("""## 4 · 配对 t 检验：自己实现 Student-t 的尾概率

不用 scipy。双侧 $p$ 值可以写成正则化不完全 Beta 函数：
$$p = I_{\\nu/(\\nu+t^2)}\\!\\left(\\tfrac{\\nu}{2},\\ \\tfrac12\\right)$$
用 Lentz 连分数算 $I_x(a,b)$，几十行标准库就够。"""),

    code("""def _betacf(a, b, x, itmax=300, eps=3e-16):
    '''不完全 Beta 函数的连分数展开（Lentz 修正算法）。'''
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300: d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300: d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300: c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300: d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300: c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h

def betai(a, b, x):
    '''正则化不完全 Beta 函数 I_x(a, b)。'''
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b

def t_pvalue(t, df):
    '''双侧 p 值。'''
    t = abs(float(t))
    return betai(0.5 * df, 0.5, df / (df + t * t))

def t_crit(df, alpha=0.05):
    '''双侧临界值：二分求 t 使 t_pvalue(t, df) = alpha。'''
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_pvalue(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

# —— 对照标准 t 表校验（这些临界值可以查表核对）——
print(f"{'df':>8s} {'t_0.975 (查表)':>16s} {'本实现':>12s} {'p(该 t)':>10s}")
for df, ref in [(2, 4.3027), (4, 2.7764), (5, 2.5706), (9, 2.2622), (20, 2.0860), (100, 1.9840)]:
    got = t_crit(df)
    print(f'{df:>8d} {ref:>16.4f} {got:>12.4f} {t_pvalue(ref, df):>10.5f}')
    assert abs(got - ref) < 2e-3, (df, got, ref)
    assert abs(t_pvalue(ref, df) - 0.05) < 1e-3
assert t_pvalue(0.0, 5) == 1.0
assert t_pvalue(1.0, 10) > t_pvalue(2.0, 10) > t_pvalue(3.0, 10)   # 单调
print('\\n✅ t 分布尾概率实现正确（与标准 t 表在 2e-3 内一致）。')"""),

    code("""def paired_ttest(a, b, alpha=0.05):
    '''配对 t 检验。返回 (mean_diff, t, p, ci_lo, ci_hi)。'''
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    n = len(d)
    md, sd = float(d.mean()), float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    t = md / se
    tc = t_crit(n - 1, alpha)
    return md, t, t_pvalue(t, n - 1), md - tc * se, md + tc * se

def unpaired_ttest(a, b, alpha=0.05):
    '''两独立样本 t 检验（等方差）。'''
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sp = math.sqrt(((na-1)*a.var(ddof=1) + (nb-1)*b.var(ddof=1)) / (na + nb - 2))
    se = sp * math.sqrt(1/na + 1/nb)
    t = (b.mean() - a.mean()) / se
    return float(b.mean() - a.mean()), t, t_pvalue(t, na + nb - 2)

md_, t_, p_, lo_, hi_ = paired_ttest(A, B)
md_u, t_u, p_u = unpaired_ttest(A, B)
print('同一批数据（第 3 节那 5 对），两种分析方式：\\n')
print(f'  【配对】  差值 {md_:+.4f}   t={t_:.3f} (df={n-1})   p={p_:.5f}   95% CI [{lo_:+.3f}, {hi_:+.3f}]')
print(f'  【非配对】差值 {md_u:+.4f}   t={t_u:.3f} (df={2*n-2})   p={p_u:.4f}')
assert p_ < 0.01 and p_u > 0.10, (p_, p_u)
assert lo_ > 0, '配对下 95% CI 不含 0 -> 可以下结论'
print('\\n⚠️  **同一批数据、同一个真实效应（+0.35）：**')
print(f'    配对分析   p = {p_:.4f}  -> 显著，CI 不含 0，可以下结论')
print(f'    非配对分析 p = {p_u:.4f}  -> 不显著，"无结论"')
print('    差别**完全来自实验设计**，不是来自数据、模型或统计工具。')
print('\\n✅ 报告规范：报 **效应量 + 置信区间**，p 值只是附带。')
print(f'   本例的规范写法：「+{md_:.2f} mAP（95% CI [{lo_:.2f}, {hi_:.2f}]，n=5 配对，p={p_:.3f}）」')
print(f'   效应量也可以用 sigma 为单位：+{md_/SIGMA:.2f} sigma —— 跨项目可比。')"""),

    md("""## 5 · 两种 bootstrap：它们回答不同的问题

- **对种子重采样** → 「如果我再跑一次训练，差值会落在哪」
- **对评测图像重采样** → 「如果换一批同分布的评测数据，指标会落在哪」

第二种**不会随着多跑种子而消失**——它是评测集本身的抽样不确定性。"""),

    code("""def bootstrap_ci(values, stat=np.mean, n_boot=20000, alpha=0.05, seed=0):
    '''百分位法 bootstrap 置信区间。'''
    v = np.asarray(values, float)
    r = np.random.default_rng(seed)
    idx = r.integers(0, len(v), size=(n_boot, len(v)))
    boots = stat(v[idx], axis=1)
    lo, hi = np.percentile(boots, [100*alpha/2, 100*(1-alpha/2)])
    return float(boots.mean()), float(lo), float(hi)

# ① 对**种子**重采样：配对差的分布
mb, lb, hb = bootstrap_ci(B - A, seed=1)
print(f'① 对种子重采样  配对差 {mb:+.3f}  95% CI [{lb:+.3f}, {hb:+.3f}]   (n=5)')
print(f'   对照配对 t 的 CI                    [{lo_:+.3f}, {hi_:+.3f}]')
assert lb > 0, '两种方法都应给出不含 0 的区间'
print('   ⚠️  n=5 时 bootstrap 的分位数很粗糙（只有 5 个不同取值可抽），')
print('       这种情形**宁可用配对 t**；bootstrap 的优势要 n>=20 才体现。\\n')

# ② 对**评测图像**重采样：绝对指标的不确定度
#    合成 2000 张图的"逐图 AP 贡献"（Beta 分布：多数图好、少数图差 —— 贴近真实长尾）
rimg = np.random.default_rng(3)
per_image_ap = rimg.beta(6.0, 1.4, size=2000)
proxy_map = float(per_image_ap.mean())
mi, li, hi_ = bootstrap_ci(per_image_ap, n_boot=5000, seed=4)
print(f'② 对评测图像重采样（2000 张）  代理 mAP {proxy_map:.4f}  95% CI [{li:.4f}, {hi_:.4f}]')
print(f'   区间半宽 = {(hi_-li)/2*100:.3f} 个百分点')
assert abs(mi - proxy_map) < 0.005
half_2000 = (hi_ - li) / 2

# 评测集只有 1/4 大时呢？
small = per_image_ap[:500]
_, ls, hs = bootstrap_ci(small, n_boot=5000, seed=5)
half_500 = (hs - ls) / 2
print(f'   若评测集只有 500 张           95% CI 半宽 = {half_500*100:.3f} 个百分点')
print(f'   半宽之比 {half_500/half_2000:.2f}  ≈ sqrt(4) = 2  —— **不确定度按 1/sqrt(N) 缩小**')
assert 1.6 < half_500 / half_2000 < 2.5, half_500 / half_2000
print('\\n⚠️  注意：真实 mAP 不是"逐图 AP 的平均"（它是全局排序后的面积），')
print('    这里用逐图贡献做**代理**以便 bootstrap。真实实现要按图像整体重采样后**重算 mAP**。')
print('    但结论不变：**评测集抽样噪声不随多跑种子而消失**，只能靠加数据。')
print('📌 TSR 落点：夜间桶只有几百个实例 -> 它的 CI 半宽是整体 mAP 的 2–3 倍。')
print('    所以分桶门禁的阈值必须按桶各自的 sigma 设，统一阈值一定会误报警。')"""),

    md("""## 6 · 多重比较：试得越多，越容易「发现」不存在的东西"""),

    code("""m_tests = 20
alpha = 0.05
fwer = 1 - (1 - alpha) ** m_tests
print(f'一个季度做 {m_tests} 次独立对比，每次用 alpha={alpha}：')
print(f'  **至少出现一个假阳性的概率 = 1 - 0.95^20 = {fwer:.1%}**')
assert abs(fwer - 0.6415) < 1e-3

def bonferroni(pvals, alpha=0.05):
    thr = alpha / len(pvals)
    return sorted(i for i, p in enumerate(pvals) if p <= thr), thr

def benjamini_hochberg(pvals, q=0.05):
    '''控制 FDR：p 升序排，找最大的 k 使 p_(k) <= k/m*q，拒绝前 k 个。'''
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    k = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= rank / m * q:
            k = rank
    return sorted(order[:k])

# 一个季度的 10 个改动的 p 值（3 个真有效，7 个纯噪声）
P = [0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.074, 0.205, 0.212, 0.216]
naive = [i for i, p in enumerate(P) if p <= 0.05]
bonf, thr = bonferroni(P)
bh = benjamini_hochberg(P, q=0.05)
print(f'\\n{len(P)} 个改动的 p 值: {P}')
print(f'  朴素 p<0.05        -> 判定显著的有 {len(naive)} 个: {naive}')
print(f'  Bonferroni (a/m={thr:.4f}) -> {len(bonf)} 个: {bonf}   （控 FWER，很保守）')
print(f'  Benjamini-Hochberg -> {len(bh)} 个: {bh}   （控 FDR，探索期更实用）')
assert naive == [0, 1, 2, 3, 4]
assert bonf == [0]
assert bh == [0, 1], bh
print('\\n✅ 同一组 p 值，三种口径给出 5 / 1 / 2 个"显著" —— **先说清用哪种口径**。')
print('   工程建议：探索阶段用 BH 生成"值得跟进的候选清单"；')
print('   上线门禁用 Bonferroni（宁可漏掉真提升，不能放进假提升）。')
print('   而比统计校正更好用的是**分阶段验证**：dev 上随便试，holdout 上每个改动只跑一次。')"""),

    md("""## 7 · 功效分析：需要多少个种子

$$n \\ge \\frac{(z_{1-\\alpha/2}+z_{1-\\beta})^2\\,\\sigma_\\Delta^2}{\\delta^2}
= \\frac{7.849\\,\\sigma_\\Delta^2}{\\delta^2},
\\qquad
\\delta_{\\min} = 2.80\\,\\frac{\\sigma_\\Delta}{\\sqrt n}$$

先算闭式，再用蒙特卡洛校验——**你会发现闭式在小样本下严重低估**。"""),

    code("""Z_SUM = ND.inv_cdf(0.975) + ND.inv_cdf(0.80)     # 1.96 + 0.8416
print(f'z_(1-a/2) + z_(1-b) = {Z_SUM:.4f}   平方 = {Z_SUM**2:.4f}')
assert abs(Z_SUM**2 - 7.8489) < 1e-3

def n_closed(delta, sd_diff, alpha=0.05, power=0.80):
    z = ND.inv_cdf(1 - alpha/2) + ND.inv_cdf(power)
    return math.ceil(z * z * sd_diff * sd_diff / (delta * delta))

def mde_closed(n, sd_diff, alpha=0.05, power=0.80):
    z = ND.inv_cdf(1 - alpha/2) + ND.inv_cdf(power)
    return z * sd_diff / math.sqrt(n)

print(f"\\n{'要检出的效应':>12s} {'非配对 n/组':>12s} {'总训练次数':>11s} "
      f"{'配对 n 对':>10s} {'总训练次数':>11s}")
for delta in [0.1, 0.3, 0.5, 1.0]:
    nu = n_closed(delta, SD_UNPAIRED)
    npd = n_closed(delta, SD_PAIRED)
    print(f'{delta:>12.1f} {nu:>12d} {2*nu:>11d} {npd:>10d} {2*npd:>11d}')

assert n_closed(0.3, SD_UNPAIRED) == 11
assert n_closed(0.3, SD_PAIRED) == 3
assert n_closed(1.0, SD_UNPAIRED) == 1, '+1.0 这种大改动单次对比就够 —— 大改动不需要统计学'
assert n_closed(0.1, SD_UNPAIRED) == 99
print('\\n✅ 闭式结论：检出 +0.3 需要非配对 22 次训练 / 配对 6 次；')
print('   检出 +0.1 需要 198 次 —— **这个量级的效应在检测里基本无法证实**。')"""),

    code("""# —— 蒙特卡洛校验：闭式用的是正态分位数，而小样本服从 t 分布（尾巴更厚）——
def sim_power_paired(n, delta, trials=4000, seed=1):
    r = np.random.default_rng(seed)
    d = r.normal(delta, SD_PAIRED, size=(trials, n))
    t = d.mean(1) / (d.std(1, ddof=1) / math.sqrt(n))
    return float((t > t_crit(n - 1)).mean())        # 双侧 0.05 且方向为正

def sim_power_unpaired(n, delta, trials=4000, seed=2):
    r = np.random.default_rng(seed)
    a = r.normal(0.0, SIGMA, size=(trials, n))
    b = r.normal(delta, SIGMA, size=(trials, n))
    sp = np.sqrt((a.var(1, ddof=1) + b.var(1, ddof=1)) / 2)
    t = (b.mean(1) - a.mean(1)) / (sp * math.sqrt(2.0 / n))
    return float((t > t_crit(2 * n - 2)).mean())

def search_n(power_fn, delta, target=0.80, n_max=40):
    for n in range(2, n_max + 1):
        if power_fn(n, delta) >= target:
            return n
    return None

print(f"{'配对 n':>8s} {'t 临界值':>10s} {'实际功效(delta=0.3)':>20s}")
for n_ in range(2, 9):
    print(f'{n_:>8d} {t_crit(n_-1):>10.3f} {sim_power_paired(n_, 0.3):>20.1%}')

n_sim_p = search_n(sim_power_paired, 0.3)
n_sim_u = search_n(sim_power_unpaired, 0.3)
print(f'\\n达到 80% 功效所需（delta=0.3）：')
print(f'  配对   闭式 {n_closed(0.3, SD_PAIRED):>2d} 对   蒙特卡洛 {n_sim_p:>2d} 对')
print(f'  非配对 闭式 {n_closed(0.3, SD_UNPAIRED):>2d} /组  蒙特卡洛 {n_sim_u:>2d} /组')
assert n_closed(0.3, SD_PAIRED) < n_sim_p, '闭式（正态近似）在小样本下会低估所需重复数'
assert 4 <= n_sim_p <= 8, n_sim_p
assert n_sim_u >= 2 * n_sim_p, (n_sim_u, n_sim_p)
print('\\n⚠️  n=3 时自由度只有 2，双侧 0.05 的 t 临界值是 **4.303** 而不是 1.96 ——')
print('    闭式给的 3 对，实际功效只有 40%。**小样本下所有正态近似的公式都要用模拟校验。**')"""),

    code("""# —— 反过来用：预算定死了，你到底能看见多大的效应（MDE）——
def sim_mde(n, target=0.80, grid=None):
    '''给定 n，搜出实际能以 target 功效检出的最小效应。'''
    grid = np.arange(0.05, 1.50, 0.01) if grid is None else grid
    for d in grid:
        if sim_power_paired(n, float(d)) >= target:
            return float(d)
    return None

print(f"{'预算(配对对数)':>14s} {'闭式 MDE':>10s} {'该 delta 下实际功效':>20s} {'真实 MDE':>10s}")
mdes = {}
for n_ in [3, 5, 10]:
    mc = mde_closed(n_, SD_PAIRED)
    mdes[n_] = sim_mde(n_)
    print(f'{n_:>14d} {mc:>10.3f} {sim_power_paired(n_, mc):>20.1%} {mdes[n_]:>10.3f}')

assert mdes[3] > 1.5 * mde_closed(3, SD_PAIRED), '3 对时闭式 MDE 乐观了一倍'
assert mdes[3] > mdes[5] > mdes[10], 'MDE 必须随预算单调下降'
print('\\n⚠️  **只有 3 对预算时，你真正能可靠看见的最小效应是 0.56，不是闭式说的 0.27。**')
print('✅ 开跑之前先算 MDE：如果 MDE 比你期待的效应还大，这个实验不值得跑 ——')
print('   要么加预算，要么改设计（配对/共享评测集），要么换一个效应更大的改动。')
print('\\n📌 一条必须分清的表述差别：')
print('   「没有证据说明它有用」 != 「有证据说明它没用」')
print('   MDE 之下的结果只能报**前者**。把前者说成后者，是实验解读里最常见的错误。')"""),

    md("""## 8 · 消融设计的偏差：加法式 / 减法式 / Shapley

三个组件 A（Mosaic）、B（copy-paste）、C（更长训练），baseline 40.0。
真实响应含交互：A×B **冗余** −0.8（都在制造小目标）、B×C **协同** +0.5、
A×C −0.3、三阶 +0.2。**完整系统 42.2，总增益 +2.2。**"""),

    code("""BASE = 40.0
MAIN  = {'A': 1.0, 'B': 1.0, 'C': 0.6}
INTER = {('A', 'B'): -0.8, ('B', 'C'): 0.5, ('A', 'C'): -0.3, ('A', 'B', 'C'): 0.2}
COMPS = ['A', 'B', 'C']
NAMES = {'A': 'Mosaic', 'B': 'copy-paste', 'C': '更长训练'}

def perf(S):
    '''子集 S 的真实性能（我们这里"知道"真值；现实中每个 S 要跑一次训练）。'''
    S = frozenset(S)
    v = BASE + sum(MAIN[x] for x in S)
    for key, val in INTER.items():
        if set(key) <= S:
            v += val
    return v

full = perf(COMPS)
total_gain = full - perf([])
print(f'baseline = {perf([]):.2f}   完整系统 = {full:.2f}   总增益 = {total_gain:+.2f}\\n')
print('全部 2^3 = 8 个子集（这就是"全子集消融"要跑的实验数）：')
for r in range(4):
    for S in itertools.combinations(COMPS, r):
        print(f"  {'{' + ','.join(S) + '}':<10s} {perf(S):.2f}")
assert abs(full - 42.2) < 1e-9 and abs(total_gain - 2.2) < 1e-9"""),

    code("""def additive(x):     return perf([x]) - perf([])                 # 从 baseline 加一个
def subtractive(x):  return perf(COMPS) - perf([c for c in COMPS if c != x])   # 从 full 去一个

def shapley(x):
    '''对所有加入顺序求平均的边际贡献。'''
    others = [c for c in COMPS if c != x]
    n = len(COMPS)
    tot = 0.0
    for r in range(len(others) + 1):
        for S in itertools.combinations(others, r):
            w = math.factorial(len(S)) * math.factorial(n - len(S) - 1) / math.factorial(n)
            tot += w * (perf(set(S) | {x}) - perf(S))
    return tot

add = {x: additive(x) for x in COMPS}
sub = {x: subtractive(x) for x in COMPS}
sha = {x: shapley(x) for x in COMPS}

print(f"{'组件':<16s} {'加法式':>9s} {'减法式':>9s} {'Shapley':>9s}   结论")
for x in COMPS:
    note = '**相差 10 倍**' if abs(add[x] - sub[x]) > 0.5 else ''
    print(f'{x + " " + NAMES[x]:<16s} {add[x]:>+9.2f} {sub[x]:>+9.2f} {sha[x]:>+9.2f}   {note}')
print(f'{"合计":<16s} {sum(add.values()):>+9.2f} {sum(sub.values()):>+9.2f} '
      f'{sum(sha.values()):>+9.2f}   真实总增益 {total_gain:+.2f}')

assert abs(add['A'] - 1.00) < 1e-9 and abs(sub['A'] - 0.10) < 1e-9
assert abs(sha['A'] - 0.5166666666) < 1e-6
# Shapley 的**效率公理**：各组件的分摊之和 == 总增益（另两种都不满足）
assert abs(sum(sha.values()) - total_gain) < 1e-9, sum(sha.values())
assert abs(sum(add.values()) - total_gain) > 0.3, '加法式合计 2.60 != 2.20'
assert abs(sum(sub.values()) - total_gain) > 0.15, '减法式合计 2.00 != 2.20'
print('\\n⚠️  **A 的贡献：加法式说 +1.00，减法式说 +0.10 —— 相差 10 倍，而两者都没算错。**')
print('    加法式回答「只能加一个时加哪个」；减法式回答「要砍一个时砍哪个代价最小」。')
print('    把任何一个说成"A 的贡献"这个唯一数字，都是错的。')"""),

    code("""# 交互作用可以被直接测出来 —— 而它往往比主效应更有信息量
def interaction_2way(x, y):
    '''二阶交互 = f(xy) - f(x) - f(y) + f({})，正=协同，负=冗余。'''
    return perf([x, y]) - perf([x]) - perf([y]) + perf([])

print('实测二阶交互（从全子集实验里免费得到）：')
for x, y in itertools.combinations(COMPS, 2):
    v = interaction_2way(x, y)
    kind = '协同（1+1>2）' if v > 0.05 else ('冗余（做的是同一件事）' if v < -0.05 else '基本独立')
    print(f'  {NAMES[x]:<10s} x {NAMES[y]:<10s} {v:>+6.2f}   {kind}')
assert abs(interaction_2way('A', 'B') - (-0.8)) < 1e-9
assert abs(interaction_2way('B', 'C') - 0.5) < 1e-9

gap = {x: abs(add[x] - sub[x]) for x in COMPS}
flag = [x for x in COMPS if gap[x] > 0.3]
print(f'\\n加法/减法差距 > 0.3 的组件：{[NAMES[x] for x in flag]}'
      f' -> **存在显著交互，需要单独研究**')
print(f'  差距最小的是 {NAMES[min(gap, key=gap.get)]}（{min(gap.values()):.2f}）'
      f' —— 它与别人的交互相互抵消了，两种读法一致')
assert flag == ['A', 'C'], flag
assert min(gap, key=gap.get) == 'B'
print('\\n✅ 三条实用规则：')
print('   ① 决定"上不上线" -> 用**减法式**（部署形态就是完整系统）')
print('   ② 决定"下一步做什么" -> 用**加法式**（起点是当前系统）')
print('   ③ 组件数 k<=4 -> 直接跑全子集（2^4=16 组），顺带把交互作用也测出来')
print('   预算不够时的零成本退路：**同时报两端**，差距大的组件标注"存在交互"。')
print('\\n📌 TSR 落点：Mosaic 与 copy-paste 都在制造更多小目标 —— 冗余是可预期的。')
print('    知道它们冗余，就可以砍掉一个省训练时间，而这个结论比"Mosaic 涨 1.0"有用得多。')"""),

    md("""## 9 · 调参预算：「baseline 没调参」能偷走多少个点

只报最优 = 报 $n$ 次抽样的最大值，而最大值随 $n$ 单调增长，**与方法好坏无关**。
$$P(\\text{至少一次超过 baseline}) = 1-(1-p)^n$$"""),

    code("""def p_at_least_one_beats(p, n):
    return 1 - (1 - p) ** n

print('单次抽样超过 baseline 的概率 p，与搜索 n 组后"至少找到一组更好"的概率：')
print(f"{'p':>6s}" + ''.join(f'{n:>9d}' for n in [1, 5, 10, 20, 50]))
for p in [0.05, 0.10, 0.20]:
    print(f'{p:>6.2f}' + ''.join(f'{p_at_least_one_beats(p, n):>9.1%}' for n in [1, 5, 10, 20, 50]))
assert abs(p_at_least_one_beats(0.10, 20) - 0.8784) < 1e-3
print('\\n⚠️  **即使方法一点不比 baseline 好，只要允许随机调 20 组超参，')
print('    你有 87.8% 的概率能找到一组"涨了"的配置。** 这不是作弊，是搜索的数学性质。')"""),

    code("""# —— 预算-期望最优曲线：不用额外实验，用已跑过的结果重采样估计 ——
def expected_best_curve(results, budgets, trials=20000, seed=0):
    '''若只有预算 n 组，期望能拿到的最优值是多少（有放回重采样）。'''
    v = np.asarray(results, float)
    r = np.random.default_rng(seed)
    out = {}
    for n in budgets:
        idx = r.integers(0, len(v), size=(trials, n))
        out[n] = float(v[idx].max(1).mean())
    return out

# 方法 M：对超参敏感（方差大）；方法 R：鲁棒（方差小），二者的"极限最优"接近
rh = np.random.default_rng(0)
res_M = rh.normal(51.6, 0.90, size=200)     # 敏感：要搜很多组才能到高分
res_R = rh.normal(52.5, 0.25, size=200)     # 鲁棒：默认配置就不错
BUDGETS = [1, 2, 5, 10, 20, 50]
cM = expected_best_curve(res_M, BUDGETS, seed=1)
cR = expected_best_curve(res_R, BUDGETS, seed=2)

print(f"{'预算(组)':>9s} {'方法 M(敏感)':>14s} {'方法 R(鲁棒)':>14s} {'谁更好':>8s}")
for n in BUDGETS:
    print(f'{n:>9d} {cM[n]:>14.3f} {cR[n]:>14.3f} {("M" if cM[n] > cR[n] else "R"):>8s}')

assert cM[1] < cR[1], '小预算下鲁棒方法更好'
assert cM[50] > cM[1] + 1.5, '敏感方法的曲线爬升很多 —— 提升大半来自"搜索"而不是"方法"'
assert cR[50] - cR[1] < cM[50] - cM[1], '鲁棒方法的曲线更平'
print(f'\\n方法 M 从预算 1 到 50：{cM[1]:.2f} -> {cM[50]:.2f}（爬升 {cM[50]-cM[1]:+.2f}）')
print(f'方法 R 从预算 1 到 50：{cR[1]:.2f} -> {cR[50]:.2f}（爬升 {cR[50]-cR[1]:+.2f}）')
print('\\n⚠️  如果只报「最优值」：M 报 {:.2f}、R 报 {:.2f}，看起来 M 赢。'.format(cM[50], cR[50]))
print('    但在预算 1–5 组（= 真实项目的常态）时 **R 全面更好**，')
print('    而且 R 换数据集/换分辨率后不用重调 —— **"对超参不敏感"本身是重要优点**，')
print('    只报最优值的做法会把这个优点完全抹掉。')
print('\\n✅ 面试答法：「我报的是等预算对比 —— 两个方法各搜 N 组，各自的最优。」')
print('   加分句：「而且我在两个模型尺寸上都验证了同一结论 —— ')
print('           如果提升只来自调参，它不会在两个尺寸上都成立。」')"""),

    md("""## 10 · 实验记录 schema 与公平性审计器

两个可以直接搬进项目的小工具：
**① 记录校验**（缺字段就拒绝这次 run）、**② 公平性审计**（找出两个配置里"本不该不同"的项）。"""),

    code("""EXPERIMENT_SCHEMA = {
    'run_id':        ('str',  '唯一且人可读'),
    'baseline_run_id': ('str', '**对照是哪一次** —— 缺了它，这次实验没有可比对象'),
    'code_commit':   ('str',  '哪版代码'),
    'code_dirty':    ('bool', 'True = 这份代码在世界上任何地方都不存在'),
    'data_version':  ('str',  '含内容哈希，不是路径也不是日期'),
    'eval_version':  ('str',  '评测集版本（冻结）'),
    'eval_code_sha': ('str',  '评测代码版本 —— 评测代码改了，历史数字就不可比'),
    'config':        ('dict', '**完整展开**，不是与 base 的 diff'),
    'env':           ('dict', 'python/库/驱动/GPU'),
    'seed':          ('int',  '本模块全部内容的前提'),
    'metrics':       ('dict', '全量：整体 + 全部分桶 + 延迟 + 显存'),
    'wallclock_h':   ('num',  '没有它就算不出 ROI'),
}
TYPES = {'str': str, 'bool': bool, 'int': int, 'dict': dict, 'num': (int, float)}

def validate_record(rec, schema=EXPERIMENT_SCHEMA):
    problems = []
    for key, (typ, why) in schema.items():
        if key not in rec:
            problems.append(('missing', key, why))
        elif rec[key] is None:
            problems.append(('null', key, why))
        elif not isinstance(rec[key], TYPES[typ]) or (typ == 'int' and isinstance(rec[key], bool)):
            problems.append(('badtype', key, f'期望 {typ}，得到 {type(rec[key]).__name__}'))
    if rec.get('code_dirty') is True:
        problems.append(('blocker', 'code_dirty', '工作区脏 -> 不可复现，这次 run 不应产出正式结论'))
    mt = rec.get('metrics')
    if isinstance(mt, dict) and not any(k.startswith('by_') for k in mt):
        problems.append(('blocker', 'metrics', '只有整体指标、没有任何分桶 -> 无法归因'))
    return (not problems), problems

GOOD_REC = dict(
    run_id='2026-08-17_mosaic_s0', baseline_run_id='2026-08-17_base_s0',
    code_commit='d41d8cd98f00', code_dirty=False,
    data_version='tsr_v7.2#sha256:9f86d0', eval_version='tsr_eval_v3#frozen',
    eval_code_sha='a1b2c3d4',
    config={'lr': 0.01, 'epochs': 36, 'mosaic': True, 'close_mosaic': 10},
    env={'python': '3.11.9', 'numpy': '1.26.4', 'gpu': 'A100-80G'},
    seed=0,
    metrics={'mAP': 42.13, 'by_size': {'<16px': 21.4, '16-32': 38.7, '>32': 55.1},
             'by_light': {'day': 45.0, 'night': 33.2}, 'latency_p99_ms': 9.2},
    wallclock_h=11.4)
BAD_REC = json.loads(json.dumps(GOOD_REC))
BAD_REC['code_dirty'] = True
del BAD_REC['baseline_run_id']
BAD_REC['seed'] = None
BAD_REC['metrics'] = {'mAP': 42.13}

for label, rec in [('GOOD', GOOD_REC), ('BAD', BAD_REC)]:
    ok, probs = validate_record(rec)
    print(f'{label}: {"✅ 通过" if ok else "❌ 拒绝"}')
    for kind, key, why in probs:
        print(f'    [{kind:<8s}] {key:<16s} {why}')

assert validate_record(GOOD_REC)[0]
ok_b, probs_b = validate_record(BAD_REC)
assert not ok_b
kinds = {(k, key) for k, key, _ in probs_b}
assert ('missing', 'baseline_run_id') in kinds
assert ('null', 'seed') in kinds
assert ('blocker', 'code_dirty') in kinds
assert ('blocker', 'metrics') in kinds
print('\\n✅ 四个问题各自对应一类无法回答的问题：')
print('   缺 baseline_run_id -> "这次和谁比的？" | seed=None -> "这是改动还是噪声？"')
print('   dirty=True -> "用的哪版代码？"        | 无分桶    -> "涨在哪？"')"""),

    code("""# —— 公平性审计：找出两个配置里"本不该不同"的项 ——
CONTROLLED = ['epochs', 'iterations', 'img_size', 'batch_size', 'lr', 'optimizer',
              'eval_version', 'eval_code_sha', 'score_thr', 'nms_iou', 'precision', 'seed_set']

def fairness_audit(cfg_a, cfg_b, tested_vars, controlled=CONTROLLED):
    '''tested_vars：本次实验**有意**改变的变量（含它的耦合组）。
       返回 (公平吗, 意外差异列表, 未记录的受控项列表)。'''
    diffs, missing = [], []
    for k in controlled:
        if k not in cfg_a or k not in cfg_b:
            missing.append(k)
            continue
        if cfg_a[k] != cfg_b[k] and k not in tested_vars:
            diffs.append((k, cfg_a[k], cfg_b[k]))
    return (not diffs and not missing), diffs, missing

BASE_CFG = dict(epochs=36, iterations=90000, img_size=640, batch_size=32, lr=0.01,
                optimizer='SGD', eval_version='v3', eval_code_sha='a1b2c3d4',
                score_thr=0.05, nms_iou=0.65, precision='fp16', seed_set='0,1,2',
                mosaic=False)
# 实验一：只改 mosaic —— 公平
EXP1 = dict(BASE_CFG, mosaic=True)
# 实验二：改了 mosaic，但顺手把 epochs 拉长、评测集也换了新版 —— 不公平
EXP2 = dict(BASE_CFG, mosaic=True, epochs=72, iterations=180000, eval_version='v4')

for label, cfg in [('实验一（只改 mosaic）', EXP1), ('实验二（顺手改了别的）', EXP2)]:
    fair, diffs, missing = fairness_audit(BASE_CFG, cfg, tested_vars={'mosaic'})
    print(f'{label}: {"✅ 公平" if fair else "❌ 不公平"}')
    for k, va, vb in diffs:
        print(f'    ⚠️ 意外差异  {k}: baseline={va}  实验={vb}')
    for k in missing:
        print(f'    ⚠️ 未记录     {k}')

assert fairness_audit(BASE_CFG, EXP1, {'mosaic'})[0]
fair2, diffs2, _ = fairness_audit(BASE_CFG, EXP2, {'mosaic'})
assert not fair2 and len(diffs2) == 3, diffs2
assert {k for k, _, _ in diffs2} == {'epochs', 'iterations', 'eval_version'}
# 未记录受控项也算不公平（因为你无法证明它相同）
_, _, miss3 = fairness_audit({'epochs': 36}, {'epochs': 36}, set())
assert len(miss3) == len(CONTROLLED) - 1
print('\\n✅ 实验二的三项意外差异里，**换评测集是最致命的** ——')
print('   前两项让结论有偏，第三项让两个数字根本不可比。')
print('📌 把这个审计器接进实验提交流程：不公平的实验**不允许写进对比表**。')"""),

    md("""## ✏️ 练习 1：方差预算与所需种子数

实现两个函数：
- `sd_of_mean_diff(sigma_s, sigma_e, n, paired)` → **两个配置各跑 n 个种子后，均值之差**的标准差
  （配对：$\\sqrt2\\,\\sigma_e/\\sqrt n$；非配对：$\\sqrt2\\sqrt{\\sigma_s^2+\\sigma_e^2}/\\sqrt n$）
- `seeds_needed(delta, sigma_s, sigma_e, paired, alpha=0.05, power=0.8)`
  → 闭式所需的 n（向上取整）；用 $n \\ge 7.849\\,\\sigma_\\Delta^2/\\delta^2$，其中 $\\sigma_\\Delta$ 是 **n=1** 时的差值标准差"""),

    code("""def sd_of_mean_diff(sigma_s, sigma_e, n, paired):
    # TODO
    raise NotImplementedError

def seeds_needed(delta, sigma_s, sigma_e, paired, alpha=0.05, power=0.8):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(sd_of_mean_diff(0.22, 0.12, 1, True)  - SD_PAIRED)   < 1e-12
assert abs(sd_of_mean_diff(0.22, 0.12, 1, False) - SD_UNPAIRED) < 1e-12
assert abs(sd_of_mean_diff(0.22, 0.12, 4, True)  - SD_PAIRED / 2) < 1e-12   # 1/sqrt(4)
assert sd_of_mean_diff(0.22, 0.12, 5, True) < sd_of_mean_diff(0.22, 0.12, 5, False)
# sigma_s=0 时配对没有任何优势（种子效应本来就不存在）
assert abs(sd_of_mean_diff(0.0, 0.12, 3, True) - sd_of_mean_diff(0.0, 0.12, 3, False)) < 1e-12

assert seeds_needed(0.3, 0.22, 0.12, paired=True)  == 3
assert seeds_needed(0.3, 0.22, 0.12, paired=False) == 11
assert seeds_needed(1.0, 0.22, 0.12, paired=False) == 1
assert seeds_needed(0.1, 0.22, 0.12, paired=False) == 99
assert seeds_needed(0.3, 0.22, 0.12, True) < seeds_needed(0.3, 0.22, 0.12, False)

print(f"{'delta':>7s} {'配对 n':>8s} {'非配对 n':>10s} {'配对省下的训练次数':>20s}")
for d_ in [0.2, 0.3, 0.5, 1.0]:
    a_ = seeds_needed(d_, 0.22, 0.12, True); b_ = seeds_needed(d_, 0.22, 0.12, False)
    print(f'{d_:>7.1f} {a_:>8d} {b_:>10d} {2*(b_-a_):>20d}')
print('✅ 练习 1 通过：**配对是免费的方差削减** —— 同样的算力，能看见更小的效应。')"""),

    md("""## ✏️ 练习 2：Holm–Bonferroni 逐步降级法

Bonferroni 太保守，BH 只控 FDR。**Holm** 在严格控制 FWER 的同时比 Bonferroni 更强。

实现 `holm(pvals, alpha=0.05)`：把 $p$ 升序排，依次检查 $p_{(k)} \\le \\alpha/(m-k+1)$，
**第一次失败就停止**，拒绝此前的全部。返回被拒绝的**原始下标**升序列表。"""),

    code("""def holm(pvals, alpha=0.05):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（手算）——
P2 = [0.004, 0.006, 0.030]        # m=3，阈值依次 0.05/3=0.01667, 0.05/2=0.025, 0.05/1=0.05
assert holm(P2) == [0, 1, 2], holm(P2)             # 三个都通过
assert bonferroni(P2)[0] == [0, 1]                 # Bonferroni 只认前两个（阈值恒为 0.01667）
P3 = [0.004, 0.030, 0.006]                         # 打乱顺序，结果应与 P2 相同（按原始下标）
assert holm(P3) == [0, 1, 2], holm(P3)
assert holm([0.02, 0.03, 0.04]) == [], '第一步 0.02 > 0.05/3 就该全部停下'
assert holm(P, 0.05) == [0], holm(P, 0.05)         # 第 6 节那组 p 值
assert set(holm(P)) <= set(benjamini_hochberg(P)), 'Holm(控 FWER) 必然不比 BH(控 FDR) 激进'
print(f'P2 = {P2}')
print(f'  Bonferroni -> {bonferroni(P2)[0]}   Holm -> {holm(P2)}   （Holm 严格更强，且仍控 FWER）')
print(f'P  = {P}')
print(f'  Bonferroni -> {bonferroni(P)[0]}   Holm -> {holm(P)}   BH -> {benjamini_hochberg(P)}')
print('✅ 练习 2 通过：门禁用 Holm（控 FWER 但比 Bonferroni 少漏），探索用 BH。')"""),

    md("""## ✏️ 练习 3：通用 Shapley 归因

实现 `shapley_values(perf_fn, components)`：对任意 `perf_fn(子集) -> 数值` 与组件列表，
返回 `{组件: Shapley 值}`。

$$\\phi_i=\\sum_{S\\subseteq N\\setminus\\{i\\}}\\frac{|S|!\\,(n-|S|-1)!}{n!}\\bigl[f(S\\cup\\{i\\})-f(S)\\bigr]$$"""),

    code("""def shapley_values(perf_fn, components):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
sv = shapley_values(perf, COMPS)
assert abs(sv['A'] - 0.5166666667) < 1e-6, sv
assert abs(sv['B'] - 0.9166666667) < 1e-6, sv
assert abs(sv['C'] - 0.7666666667) < 1e-6, sv
# **效率公理**：分摊之和 == 总增益
assert abs(sum(sv.values()) - (perf(COMPS) - perf([]))) < 1e-9

# 无交互时，三种归因必须完全一致（这是最好的正确性检查）
def perf_additive(S):
    return 40.0 + sum({'X': 1.0, 'Y': 0.5, 'Z': 0.2}[c] for c in S)
sv2 = shapley_values(perf_additive, ['X', 'Y', 'Z'])
assert abs(sv2['X'] - 1.0) < 1e-12 and abs(sv2['Y'] - 0.5) < 1e-12 and abs(sv2['Z'] - 0.2) < 1e-12

# **虚拟成员公理**：不贡献任何东西的组件，Shapley 值必须是 0
def perf_dummy(S):
    return perf_additive([c for c in S if c != 'W'])
sv3 = shapley_values(perf_dummy, ['X', 'Y', 'Z', 'W'])
assert abs(sv3['W']) < 1e-12, sv3

print('含交互:', {k: round(v, 4) for k, v in sv.items()},  '合计', round(sum(sv.values()), 4))
print('无交互:', {k: round(v, 4) for k, v in sv2.items()}, '-> 与加法式/减法式完全一致')
print('虚拟项:', {k: round(v, 4) for k, v in sv3.items()}, '-> W 的贡献恰为 0')
print('✅ 练习 3 通过：**无交互时三种归因一致 —— 所以它们的分歧本身就是交互的度量。**')"""),

    md("""## ✏️ 练习 4：预算-期望最优曲线的闭式解

不用重采样也能算。把 $N$ 个结果升序排成 $v_{(1)}\\le\\dots\\le v_{(N)}$，
有放回抽 $n$ 次的最大值期望是：

$$\\mathbb E[\\max] = \\sum_{i=1}^{N} v_{(i)}\\left[\\left(\\tfrac iN\\right)^{n}-\\left(\\tfrac{i-1}{N}\\right)^{n}\\right]$$

实现 `expected_best_exact(results, n)`，并与第 9 节的蒙特卡洛版本对拍。"""),

    code("""def expected_best_exact(results, n):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测（手算）——
assert abs(expected_best_exact([1, 2, 3, 4], 1) - 2.5) < 1e-12
# n=2: (1*1 + 2*3 + 3*5 + 4*7)/16 = 50/16 = 3.125
assert abs(expected_best_exact([1, 2, 3, 4], 2) - 3.125) < 1e-12
assert abs(expected_best_exact([5.0], 7) - 5.0) < 1e-12
assert expected_best_exact([1, 2, 3, 4], 10) > expected_best_exact([1, 2, 3, 4], 3)

# 与蒙特卡洛对拍（这是验证闭式实现最可靠的方式）
print(f"{'预算':>6s} {'蒙特卡洛':>10s} {'闭式':>10s} {'差':>9s}")
for n_ in BUDGETS:
    mc_ = cR[n_]; ex_ = expected_best_exact(res_R, n_)
    print(f'{n_:>6d} {mc_:>10.4f} {ex_:>10.4f} {abs(mc_-ex_):>9.5f}')
    assert abs(mc_ - ex_) < 0.02, (n_, mc_, ex_)
print('✅ 练习 4 通过：**已经跑过的实验就够画出预算曲线了，不需要新实验。**')
print('   把它加进你的实验报告，「调参不公平」这个质疑就自动被回答了。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def sd_of_mean_diff(sigma_s, sigma_e, n, paired):
    per_run_var = sigma_e ** 2 if paired else sigma_s ** 2 + sigma_e ** 2
    return math.sqrt(2 * per_run_var / n)

def seeds_needed(delta, sigma_s, sigma_e, paired, alpha=0.05, power=0.8):
    z = ND.inv_cdf(1 - alpha / 2) + ND.inv_cdf(power)
    sd1 = sd_of_mean_diff(sigma_s, sigma_e, 1, paired)      # n=1 时的差值标准差
    return math.ceil(z * z * sd1 * sd1 / (delta * delta))"""),

    code("""# 练习 2 参考答案
def holm(pvals, alpha=0.05):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    rejected = []
    for k, i in enumerate(order, start=1):
        if pvals[i] <= alpha / (m - k + 1):
            rejected.append(i)
        else:
            break                                   # **第一次失败就停止**
    return sorted(rejected)"""),

    code("""# 练习 3 参考答案
def shapley_values(perf_fn, components):
    comps = list(components)
    n = len(comps)
    out = {}
    for x in comps:
        others = [c for c in comps if c != x]
        tot = 0.0
        for r in range(len(others) + 1):
            for S in itertools.combinations(others, r):
                w = math.factorial(len(S)) * math.factorial(n - len(S) - 1) / math.factorial(n)
                tot += w * (perf_fn(list(S) + [x]) - perf_fn(list(S)))
        out[x] = tot
    return out"""),

    code("""# 练习 4 参考答案
def expected_best_exact(results, n):
    v = np.sort(np.asarray(results, float))
    N = len(v)
    i = np.arange(1, N + 1)
    w = (i / N) ** n - ((i - 1) / N) ** n           # P(max 恰好是第 i 小的那个)
    return float((v * w).sum())"""),

    md("""---
## 🧪 真实工程胶囊：一次可信实验的完整流程"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 「我要验证 X 有没有用」—— 从提出假设到写下结论的完整流程
# 每一步都有明确的产出物；缺任何一步，结论的强度都要打折并**如实标注**
# ══════════════════════════════════════════════════════════════════════

# ─── 阶段 0：开跑之前（最重要，也最常被跳过）────────────────────────
# 0.1 写下**事前预测**（预注册）。这一条堵死了"事后找解释"这个最强的自欺来源
#     assumption.md:
#       假设：copy-paste 增强能提升稀有类召回
#       机制：稀有类样本量从 30 -> 300，正样本数是当前瓶颈
#       预测：尾部类 AP +3~8；整体 mAP +0.2~0.6；head 类不动（±0.2 内）
#       延迟：0（训练期改动）      显存：+0（离线合成）
#       **若整体涨了但尾部类没涨，说明机制判断错了，不能算验证成功**
#
# 0.2 算 MDE：我这次预算能看见多大的效应？
#     sigma = 项目 baseline 的多种子标准差（模块 00 第一周检查单第③项）
#     MDE_closed = 2.80 * sqrt(2)*sigma_e / sqrt(n)   # 记得：**闭式会乐观一倍**
#     若 MDE > 预测效应 -> **这个实验不值得跑**，先加预算或改设计
#
# 0.3 公平性自查（fairness_audit）：列出本次**有意**改变的变量及其耦合组，
#     其余受控项逐项对齐。特别注意：epoch/iteration、增强、分辨率、
#     score/NMS 阈值、评测集版本、评测代码版本、精度、硬件

# ─── 阶段 1：跑 ────────────────────────────────────────────────────
# 1.1 **配对**：两个配置用同一组种子
#     for s in 0 1 2 3 4; do
#       train.py --cfg base.yaml      --seed $s --tag base_s$s
#       train.py --cfg base+cp.yaml   --seed $s --tag cp_s$s
#     done
# 1.2 baseline **必须在同一个 commit 上重跑**，不许用历史数字
# 1.3 每个 run 落 manifest（validate_record 不过就不产出）

# ─── 阶段 2：分析 ──────────────────────────────────────────────────
# 2.1 配对诊断：pairing_diagnostic(A, B) —— 削减 < 20% 说明配对失效，要加种子
# 2.2 配对 t 检验 + 95% CI；**报效应量与 CI，p 值只是附带**
# 2.3 分桶逐个看：涨的是不是**预测的那个桶**？其他桶有没有掉？
# 2.4 多重比较：本季度做了几次对比？超过 5 次就上 Holm 或 BH

# ─── 阶段 3：写结论（模板，直接套用）──────────────────────────────
#   【结论】在 <同 commit / 36 epoch / 640 输入 / 同增强其余项 / eval_v3 冻结> 下，
#           copy-paste 使 **尾部类 AP +4.2（95% CI [2.1, 6.3]，n=5 配对，p=0.004）**，
#           整体 mAP +0.31（95% CI [0.05, 0.57]），head 类 -0.08（在噪声内）。
#   【代价】训练时长 +8%，显存不变，推理延迟不变；实例库构建一次性 6 人时。
#   【局限】只在 tsr_v7.2 与 640 分辨率下验证；1280 下未测；
#           尾部类样本量 <10 的极稀有类仍无提升（n 太小，本次 MDE 覆盖不到）。
#   【下一步】按 0.1 的机制推断，应对 <10 张的极稀有类改用两级架构（C55 m02）。
#
#   ▶ **四段缺一不可**：只有【结论】没有【代价】和【局限】的报告，
#     在面试和在评审会上会被同样的追问打穿。

# ─── 反模式速查 ───────────────────────────────────────────────────
#  · "涨了 0.4，上了"                 -> 没有 sigma，不知道 0.4 是不是噪声
#  · "baseline 用的论文数字"           -> 基线漂移，对比无效
#  · "顺手把 epoch 也拉长了"           -> 混杂因子，归因失效
#  · "这个 p=0.03，所以有效"           -> 只报 p 不报效应量与 CI
#  · "试了 20 个改动，这个显著"        -> 多重比较，FWER 已达 64%
#  · "新方法搜了 200 组，baseline 默认" -> 调参不公平，报预算曲线
'''
print(RECIPE)
for token in ['事前预测', 'MDE', 'fairness_audit', '配对', 'pairing_diagnostic',
              '95% CI', '分桶', '多重比较', '【代价】', '【局限】', '反模式']:
    assert token in RECIPE, token
print('✅ 流程覆盖：预注册 -> 功效 -> 公平性 -> 配对执行 -> 统计分析 -> 四段式结论')"""),

    md("""### 小结

- **种子方差是这门课的第一性事实**：$\\sigma\\approx0.25$ 时，5 个种子的期望极差是 **0.58 个 mAP**，
  而它们是完全相同的配置。**真实差异为 0 时，单次非配对对比有 19.9% 的概率显示「+0.3 的提升」。**
- **「+0.3 算提升吗」的满分答法**：先反问口径（哪个指标 / 几个种子 / 配对没有）→ 给出 20% 这个数
  → 说该怎么做（配对 3–5 组 + 分桶一致性）→ 给出退路（算力不够时用多个弱证据的一致性）。
- **配对是免费的方差削减**：同一组种子跑两个配置，种子效应在做差时抵消。
  本模块的例子里，**同一批数据配对分析 $p=0.002$、非配对分析 $p=0.20$** ——
  差别完全来自实验设计。但要跑 `pairing_diagnostic` 确认它真的生效了。
- **功效分析要在开跑前做**。检出 +0.3 需要非配对 22 次训练 / 配对 6 次（闭式）；
  而**闭式用正态近似，小样本下会低估**——蒙特卡洛给出配对实际需要 5 对。
  预算只有 3 对时，真实 MDE 是 **0.56 而不是 0.27**。
  MDE 之下只能报「没有证据说明它有用」，不能报「有证据说明它没用」。
- **多重比较**：20 次对比 → 至少一个假阳性的概率 **64%**。
  门禁用 Bonferroni/Holm（控 FWER），探索用 BH（控 FDR）；比统计校正更好用的是
  **dev/holdout 分阶段验证**。
- **消融的加法式与减法式会给出相反结论**：例子里 A 的贡献是 +1.00 还是 +0.10 相差 10 倍，
  而两者都没算错。**它们的分歧本身就是交互作用的度量**（无交互时三种归因完全一致）。
  $k\\le4$ 时直接跑全子集（16 组），顺带把交互测出来。
- **只报最优值等于报 $n$ 次抽样的最大值**：即使方法一点不比 baseline 好，
  随机搜 20 组也有 **87.8%** 的概率找到「涨了」的配置。用**预算-期望最优曲线**
  （已跑过的实验就够算，还有闭式解）来做等预算对比。
- **结论必须四段式**：结论（含全部实验条件）/ 代价 / 局限 / 下一步。
  少了【代价】与【局限】的报告，在评审会和面试里会被同样的追问打穿。

下一站：**模块 02 · 误差分析工程** —— 实验证明了「有用」之后，
下一个问题是「现在该做什么」：把 mAP 的损失拆成 Cls/Loc/Dupe/Bkg/Miss 六类，
并算出**修好每一类能涨多少**。"""),
]
