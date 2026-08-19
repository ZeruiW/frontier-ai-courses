# -*- coding: utf-8 -*-
"""C61 模块 02 · 误差分析工程：从指标到根因。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "C18 模块 03（IoU / NMS / AP 从零实现）、本课模块 01（实验设计与归因）；C55 模块 05（安全导向评测）可后看"),
    ("配套 notebook", "<span class='badge cpu'>CPU</span> 02_error_analysis.ipynb（纯 numpy：完整 TIDE 分解 + 修复收益 + PR 诊断器 + 分层抽样）"),
    ("核心参考", "TIDE (ECCV 2020) · Hoiem et al. Diagnosing Error in Object Detectors (ECCV 2012) · COCO detection analysis toolkit · Detectron2 error analysis"),
    ("预计时长", "读 80 分钟 + 跑 75 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("metric-gap", "指标不是结论：mAP 只说「有多差」，不说「差在哪」", "".join([
        P("先摆一个具体处境。你刚训完一版 TSR 检测器，评测集上 <code>mAP@0.5 = 0.721</code>，上一版是 <code>0.706</code>。"
          "接下来你要做什么？<strong>加数据？换 backbone？提高输入分辨率？调 NMS 阈值？改标签分配？做 copy-paste？</strong>"
          "这些每一条都要花 3 天到 3 周，而 <code>0.721</code> 这个数字对「该做哪一条」<em>没有提供任何信息</em>。"),
        P("这就是初级和资深检测工程师之间最大的一道分水岭。<strong>指标回答的是「我现在在哪」，误差分析回答的是「往哪走最省力」。</strong>"
          "一个只会看 mAP 的人，改进路径本质上是随机搜索；一个会做误差分解的人，每次改动之前就能给出「这条路的收益上界是 +X mAP」。"),
        TABLE(["工程师层级", "拿到 mAP=0.721 之后的第一个动作", "下一步的依据", "典型迭代效率"], [
            ["入门", "换一个更大的 backbone / 多训 100 epoch", "直觉与论文排行榜", "3 周 1 次有效改进"],
            ["中级", "看几十张 badcase 截图，凭印象总结", "<strong>被采样偏差主导</strong>（看到的都是常见场景）", "1 周 1 次，方向常错"],
            ["<strong>资深</strong>", "跑误差分解，算出<strong>每类错误的修复收益上界</strong>", "<strong>ΔAP 排序 + 修复成本估计</strong>", "<strong>每次改动前就知道天花板</strong>"],
        ]),
        H3("mAP 把六件完全不同的事压成了一个数"),
        P("回忆 AP 的定义——按置信度排序、逐条判 TP/FP、累积算 P/R、取单调包络下的面积："),
        MATH("\\text{AP} \\;=\\; \\sum_{k}\\bigl(r_k - r_{k-1}\\bigr)\\; p_{\\text{interp}}(r_k), \\qquad p_{\\text{interp}}(r) \\;=\\; \\max_{\\tilde r \\,\\ge\\, r} p(\\tilde r)"),
        P("这个式子里，<strong>「一个检测被判成 FP」这件事只有一个出口，但入口有五个</strong>：框对了类别错、类别对了框不准、两个都错、这个目标已经被另一个更高分的框认领了（重复）、图里那个位置根本没有目标（背景）。"
          "而 recall 没到 1 的原因也不止一个：有些 GT 被上面某类错误「半覆盖」了，有些 GT 是<em>彻底没有任何检测靠近</em>。"
          "<strong>mAP 把这六种失败混成一个标量，然后你从这个标量里是解不回去的。</strong>"),
        DUAL(
            "举个立刻能感受到差别的例子：同样是 <code>mAP@0.5 = 0.72</code>，可能是 A：每个类都在 0.70–0.74，模型均匀地「差一点」；"
            "也可能是 B：限速牌类 0.95、指路牌 0.93、而「停车让行」只有 0.11。"
            "<strong>A 需要的是更强的模型或更多数据；B 需要的是查「停车让行」这一类的标注、样本量和是否被别的类吃掉——这是两个完全不同的项目。</strong>"
            "而这两种情况在 mAP 这个数字上是<em>一模一样</em>的。",
            "更严格地说，mAP 是一个<span class='term'>聚合统计量</span>（aggregate statistic），它对底层错误分布的<strong>可辨识性（identifiability）为零</strong>："
            "给定一个 mAP 值，能产生它的 (TP, FP 分类, FN 分布) 组合有无穷多个。误差分析要做的事，就是把这个不可逆的聚合过程<em>部分地反演</em>回去——"
            "办法不是从数字反推，而是<strong>回到原始的检测-GT 匹配结果，按错误的成因重新分桶，再针对每一桶做「反事实」计算</strong>。"
            "第 3 节的修复收益（oracle ΔAP）正是这个反事实：<em>如果这一类错误全部消失，mAP 会变成多少？</em>",
        ),
        CALLOUT("intuition", "把本节压成一句话：<strong>误差分析的目的不是「知道自己错了」，而是「知道修哪一个最划算」。</strong>"
                "任何一次改进动作，都应该能回答「它对应哪一类错误、这类错误的收益上界是多少、修它的成本是多少」——<em>这三个问题答不上来，那次改动就是赌博。</em>"),
        CALLOUT("danger", "<p><strong>面试高频开场题：「线上某类交通标志漏检了，你的排查流程是什么？」</strong>"
                "如果你的回答从「我会先看看 badcase」开始，面试官基本就给你定档了。"
                "<em>正确的开场是：「先确认这是召回问题还是分类问题——因为『漏检』这个词在工程上至少有四种不同的病：真·无检出、检出但被判成别的类、检出但框不准被判 FP、检出但分数低于上线阈值。这四种的修法完全不同，而误差分解能在 10 分钟内区分它们。」</em>"
                "<strong>面试官想听的是你有一套可复用的分解流程，而不是你很勤奋地看图。</strong></p>", "「先看 badcase」= 没有流程"),
    ])),

    # ============================================================== 2
    ("tide-six", "TIDE 式误差分解：把 FP/FN 拆成六类", "".join([
        P("<span class='term'>TIDE</span>（A General Toolbox for Identifying Object Detection Errors，Bolya et al., ECCV 2020）给出的六类划分，"
          "已经是检测误差分析事实上的标准词汇。它的价值不在分类本身，而在于<strong>这六类各自对应一条不同的、可执行的修复路径</strong>——"
          "分完类你就知道该动数据、动标签分配、动 NMS、还是动分辨率。"),
        H3("判定只需要两个阈值"),
        P("TIDE 用两个 IoU 阈值：<strong>前景阈值 $t_f = 0.5$</strong>（判 TP 的那条线）和 <strong>背景阈值 $t_b = 0.1$</strong>（「离目标近到值得归因」的那条线）。"
          "对每一个被判为 FP 的检测，先算它与<em>同类</em> GT 的最大 IoU（记 $u_{\\text{same}}$）和与<em>异类</em> GT 的最大 IoU（记 $u_{\\text{other}}$），然后走下面这棵判定树："),
        ASCII("""一个被判 FP 的检测 d（类别 c，分数 s）
   │
   ├─ u_same >= 0.5 ?  ── 是 ──►  它本来能匹配上，但那个 GT 已被更高分的框认领
   │                              => 【Dupe】重复检测      修法：NMS / 一对一分配
   │  否
   ├─ 0.1 <= u_same < 0.5 ?  ─ 是 ─►  类别对了，框不够准
   │                              => 【Loc】定位误差        修法：回归损失 / 分配策略 / 分辨率
   │  否（同类 GT 都离得很远）
   ├─ u_other >= 0.5 ?  ── 是 ──►  框框得很准，但类别判错了
   │                              => 【Cls】分类误差        修法：细粒度分类 / 两级架构 / 难例
   │  否
   ├─ 0.1 <= u_other < 0.5 ? ─ 是 ─►  框也不准、类也不对
   │                              => 【Both】双错          修法：通常和 Loc 一起治
   │  否
   └────────────────────────────►  周围什么都没有
                                  => 【Bkg】背景误检        修法：难负样本挖掘 / 阈值 / 上下文

所有 GT 里，**没有任何检测以 IoU >= 0.1 靠近过**的那些
                                  => 【Miss】漏检          修法：召回侧（分辨率/分配/采样/数据）"""),
        TABLE(["错误类型", "一句话定义", "TSR 里的典型成因", "第一顺位的修法", "通常动哪一层"], [
            ["<strong>Cls</strong>", "框对、类错", "限速 60 ↔ 80、禁止左转 ↔ 禁止掉头、区域变体", "细粒度分类头 / 两级架构 / 高分辨率 crop", "分类分支、数据"],
            ["<strong>Loc</strong>", "类对、框不准", "极小目标（8–20 px）位移 2 px 就跌破 0.5、遮挡导致边界不清", "回归损失（GIoU/DIoU）、标签分配、提分辨率", "回归分支、neck"],
            ["<strong>Both</strong>", "框不准且类错", "远处小目标的连锁失败", "先治 Loc，Both 常跟着降", "同上"],
            ["<strong>Dupe</strong>", "同一 GT 被检出两次以上", "NMS 阈值过高、多尺度重复触发、密集龙门架", "NMS / soft-NMS / 一对一分配", "后处理"],
            ["<strong>Bkg</strong>", "无中生有", "广告牌、车身贴纸、路侧圆形物体、树叶光斑", "难负样本挖掘、Focal Loss、上下文、提阈值", "训练采样、阈值"],
            ["<strong>Miss</strong>", "完全没看见", "太小（&lt;12 px）、被树叶遮挡、夜间低对比、长尾类样本太少", "分辨率 / P2 层 / copy-paste / 定向挖数据", "架构、数据"],
        ]),
        DUAL(
            "为什么一定要按<strong>顺序</strong>判、而不是「哪个像就归哪个」？因为这六类不是互斥的自然分类，是<em>人为定义的归因规则</em>。"
            "一个框可能同时和同类 GT 有 0.3 的 IoU、和异类 GT 有 0.6 的 IoU——它到底算 Loc 还是算 Cls？"
            "TIDE 的答案是「优先归给同类」，理由是<strong>「类别对了只是框歪」比「框对了类别错」更容易修</strong>，归因应当偏向更可行动的那一侧。"
            "<em>你可以不同意这个优先级，但你必须知道它存在——换了顺序，同一个模型的分解结果会不一样。</em>",
            "更本质地说，误差归因是一个<span class='term'>反事实赋值</span>（counterfactual attribution）问题，而反事实在多因共存时天然不唯一。"
            "TIDE 的处理方式是把「归因规则」显式写死成一棵判定树，用<strong>可复现性换取唯一性</strong>——"
            "只要所有人用同一棵树，跨模型、跨版本的分解结果就可比。<em>这和统计里的 Type I/Type III sum of squares 之争是同一类问题：不存在「正确」的分解，只存在「说清楚了的」分解。</em>"
            "因此在团队里做误差分析，<strong>第一件事是把 $t_f$、$t_b$ 和判定顺序写进评测配置并版本化</strong>，否则两个人算出来的 Cls 占比不同，谁也说服不了谁。",
        ),
        CALLOUT("warn", "<p><strong>三个几乎人人踩过的实现坑：</strong></p>"
                "<p>① <strong>Dupe 必须在匹配之后判</strong>。匹配是按分数降序贪心做的，「这个 GT 已被认领」这个状态依赖顺序；"
                "先分类再匹配会把大量 Dupe 错记成 Loc。</p>"
                "<p>② <strong>$u_{\\text{same}}$ 要对「所有同类 GT」算，不只对「未匹配的同类 GT」算</strong>，否则 Dupe 这一类会永远是 0。</p>"
                "<p>③ <strong>Miss 的定义必须和 Cls/Loc 不重复计</strong>。一个被判成 Cls 错误的检测，其实已经「看见」了那个 GT；"
                "如果 Miss 里再把这个 GT 数一遍，你会同时高估 Cls 和 Miss，两边都想修，最后修了个寂寞。</p>", "分解写错比不写更糟"),
    ])),

    # ============================================================== 3
    ("fix-gain", "修复收益：算出「修好每一类能涨多少 mAP」", "".join([
        P("上一节只是<strong>数数</strong>。数数会骗人——而且骗得很凶。"
          "「背景误检有 4200 个、分类错只有 310 个」这句话听起来结论很明显：去治背景误检。<strong>但这个结论在多数情况下是错的。</strong>"),
        H3("oracle：一次反事实实验"),
        P("TIDE 的核心工具叫 <span class='term'>oracle</span>（先知）：假装有一个神仙，帮你<em>只</em>修好某一类错误，其他一切不变，然后重新算一遍 mAP。差值就是这类错误的<strong>修复收益上界</strong>："),
        MATH("\\Delta\\text{AP}_i \\;=\\; \\text{mAP}\\bigl(\\mathcal{O}_i(D),\\; G\\bigr) \\;-\\; \\text{mAP}(D,\\; G)"),
        P("其中 $D$ 是检测结果集合，$G$ 是标注集合，$\\mathcal{O}_i$ 是第 $i$ 类错误的 oracle 算子。六个 oracle 的定义都非常朴素："),
        TABLE(["oracle", "它做什么", "为什么这样定义"], [
            ["<code>O_Loc</code>", "把 Loc 错误的框<strong>吸附到它最接近的同类 GT 上</strong>（IoU 变成 1）", "模拟「回归分支变完美」，但不改变分数与排序"],
            ["<code>O_Cls</code>", "把 Cls 错误的<strong>预测类别改成它框住的那个 GT 的类别</strong>", "模拟「分类分支变完美」，框保持原样"],
            ["<code>O_Both</code>", "同时修类别与框", "Both 的定义就是两者皆错"],
            ["<code>O_Dupe</code>", "<strong>删掉</strong>重复检测", "模拟「去重完美」"],
            ["<code>O_Bkg</code>", "<strong>删掉</strong>背景误检", "模拟「不再无中生有」"],
            ["<code>O_Miss</code>", "把彻底没被覆盖的 GT <strong>从评测中移除</strong>", "模拟「这些目标本来就检得到」——注意是改 $G$ 不是改 $D$"],
        ]),
        H3("为什么数量最多的错误往往最不值钱"),
        P("答案藏在 AP 的定义里：<strong>AP 是按分数排序后累积算的，所以一个 FP 的杀伤力完全取决于它排在第几名。</strong>"
          "背景误检的分数通常很低（模型自己也不确信），它们排在 PR 曲线的<em>最尾巴</em>，那一段的 recall 增量本来就接近 0，"
          "删掉它们对面积的贡献微乎其微。而一个 Cls 错误是<strong>双重伤害</strong>：它在<em>错的那个类</em>里是一个高分 FP（狠狠压低那条 PR 曲线的头部），"
          "同时在<em>对的那个类</em>里造成一个 FN（recall 上不去）。"),
        ASCII("""notebook 在合成 TSR 评测集上实测出的分解（baseline mAP = 0.602）

  错误类型   数量       占比     ΔmAP(pp)   每 100 个错误的 ΔmAP(pp)
  ────────────────────────────────────────────────────────────────────
  Bkg      1397  ███████ 87%    +3.05     ▏0.218   <- 数量之王、性价比之末
  Loc        65  ▍        4%    +9.98     ████████████ 15.35
  Miss       47  ▎        3%    +6.17     ██████████ 13.12
  Cls        43  ▎        3%    +8.75     ████████████████ 20.34  <- 最值钱
  Dupe       37  ▎        2%    +0.32     ▏0.863
  Both       18  ▏        1%    +1.44     ██████ 7.99
  ────────────────────────────────────────────────────────────────────
  六项之和 = 29.7 pp        离满分的总差距 = 39.8 pp   <- **ΔAP 不可加**

  按「数量」排序   -> 先修 Bkg   （错误的决策：占 87% 的数量，只值 3 个点）
  按「ΔmAP」排序   -> 先修 Loc   （对，但没考虑成本）
  按「ΔmAP / 成本」-> 先修 Cls   （真实世界的决策：分类头改动便宜得多）"""),
        P("注意最后一行。<strong>ΔAP 只是收益上界，真正的决策变量是「收益 ÷ 成本」。</strong>"
          "Miss 的 +6.3% 可能需要「把输入分辨率从 640 提到 1280 + 加 P2 层 + 延迟涨 40%」才能兑现一半；"
          "Cls 的 +7.8% 可能只需要「把限速类的 crop 送进一个 64×64 的二级分类器」，代价是 0.3 ms。<em>两者的性价比差一个数量级。</em>"),
        DUAL(
            "还有一个必须记住的性质：<strong>这些 ΔAP 不可以相加</strong>。修好 Cls 之后再修 Loc，得到的总收益一般小于 $\\Delta\\text{AP}_{\\text{Cls}} + \\Delta\\text{AP}_{\\text{Loc}}$。"
            "原因很直观——两类错误经常打在同一批 GT 上，第一个 oracle 已经把那部分 recall 救回来了，第二个 oracle 再救就没得救了。"
            "<em>所以看到「六项加起来 20%，但把所有错误全修好只涨 28% 到 100%」不要慌，这不是 bug。</em>",
            "从数学上看，AP 是匹配结果的<strong>非线性、非可加泛函</strong>：它经过了「排序 → 累积 → 单调包络 → 求面积」四步，其中排序和取 max 都是非线性的。"
            "因此 $\\mathcal{O}_i$ 的效应不满足叠加原理，$\\Delta\\text{AP}$ 更接近博弈论里的<span class='term'>边际贡献</span>而非独立分量。"
            "<em>如果你真的需要一组「可加」的归因值，正确的工具是对六个 oracle 求 Shapley 值（$2^6 = 64$ 次评测，完全跑得动）</em>——"
            "但实践中几乎没人这么做，因为<strong>决策只需要排序，不需要精确的份额</strong>。知道 Cls 最值钱就够了，不必知道它「精确占 34.7%」。",
        ),
        CALLOUT("danger", "<p><strong>面试里这是一个极高分的加分点，也是一个极容易翻车的点。</strong>"
                "被问「你怎么决定下一步做什么」时，说「我会做误差分析」只是及格；"
                "<em>说「我会跑 TIDE 分解，拿到六类错误的 ΔAP，然后按 ΔAP 除以我估的工程成本排序，先做性价比最高的那一项；"
                "而且我会特别小心『数量多但 ΔAP 小』的背景误检——它排在 PR 曲线尾部，删干净了 mAP 也只涨不到 1 个点」</em>——这才是拿分的回答。</p>"
                "<p><strong>翻车点</strong>：把 ΔAP 说成「可以相加的贡献占比」。面试官只要追问一句「那六项加起来等于总差距吗」，就能看出你到底跑过没跑过。</p>", "跑过的人和背过的人，一句话就分得出"),
    ])),

    # ============================================================== 4
    ("per-class", "逐类 AP 与混淆矩阵：找出最容易互相错分的标志对", "".join([
        P("六类分解告诉你「错在什么<em>机制</em>」，逐类分析告诉你「错在什么<em>对象</em>」。两者正交，都要做。"),
        H3("mAP 的那个「平均」是最危险的一步"),
        P("mAP 对类别取的是<strong>无权重算术平均</strong>：一个在数据集中只出现 40 次的「注意落石」和一个出现 12000 次的「限速 60」，在 mAP 里权重完全一样。"
          "这带来两个方向相反的陷阱："),
        UL([
            "<strong>陷阱 A（长尾稀释）</strong>：你把主力类别从 0.93 提到 0.95，mAP 只涨 0.02/N；而某个尾部类从 0.05 掉到 0.00，mAP 掉 0.05/N——"
            "<em>于是「主力变好、长尾变差」的改动在 mAP 上可能是负的，尽管产品体验是正的（或反过来）。</em>",
            "<strong>陷阱 B（尾部噪声）</strong>：只有 40 个样本的类，它的 AP 方差极大。换个随机种子 AP 可能从 0.31 跳到 0.48。"
            "<em>把这种波动当成「我的改动生效了」，是本课模块 01 讲的种子方差问题在类别维度上的变体。</em>",
        ]),
        P("所以逐类表必须<strong>三列一起看</strong>：类别 AP、该类的 GT 数量、该类 AP 的种子间标准差。只看第一列的人会不停地追逐噪声。"),
        H3("检测的混淆矩阵怎么算（和分类不一样）"),
        P("分类任务的混淆矩阵是 $C \\times C$，每个样本必进一格。检测不是——检测有「无中生有」和「视而不见」，所以矩阵必须是 <strong>$(C{+}1) \\times (C{+}1)$</strong>，多出来的那一行一列就是 background："),
        ASCII("""                    预测类别
                 限30  限60  限80  停让  禁左  ...   BG(未检出)
        限30  [  86     2     0     0     1        11   ]  <- 行和 = 该类 GT 数
        限60  [   1   740   162     0     0        44   ]
   真   限80  [   0   129   604     0     0        38   ]  <- **这一对是重灾区**
   实   停让  [   0     0     0    23     0        58   ]  <- 召回只有 28%！
   类   禁左  [   0     0     0     0   310        27   ]
   别   ...
        BG   [  55    91    73     8    40         -   ]  <- 背景误检，按预测类分布
       (误检)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
              最后一行 = Bkg 错误；最后一列 = Miss + 被判 FP 的 Loc 错误

  读法：
   · 非对角线的**块状热点** => 该类别对语义/外观太像 => 细粒度分类问题
   · 某一行的 BG 列特别大   => 该类**召回**有问题（不是分类问题）
   · 最后一行某列特别大     => 该类是**误检磁铁**（模型见谁都想判成它）""",),
        P("对 TSR 来说，混淆矩阵几乎总是会暴露出同一批「冤家对」。这些对子的共同特征是：<strong>整体形状与颜色完全一致，差异只在一个很小的局部区域</strong>——"
          "而这个局部区域在 20 像素的框里可能只有 3×5 个像素。"),
        TABLE(["典型混淆对", "为什么混", "远距离时的可分辨像素", "对应的修法"], [
            ["限速 60 ↔ 限速 80", "都是红圈白底黑数字，只有数字中间的一横之差", "数字笔画宽度约占框宽 8%，20 px 框 → <strong>1.6 px</strong>", "两级架构 + 高分辨率 crop；数字区域专门增强"],
            ["限速 30 ↔ 限速 80", "圆形轮廓 + 首位数字上半闭合", "同上", "同上；分类器用更大的输入（如 64×64）"],
            ["禁止左转 ↔ 禁止掉头", "红圈 + 斜杠 + 箭头，箭头尾部形状不同", "箭头尾部约占 12%", "<strong>禁止水平翻转增强</strong>（会把左转变右转）"],
            ["限速 X ↔ 解除限速 X", "解除牌是灰底斜杠，颜色差异明显但夜间失色", "颜色特征在低光下衰减", "低光增强 + 夜间切片单独评测"],
            ["警告牌 ↔ 施工临时牌", "都是三角/菱形黄底", "整体差异大，但临时牌样本极少", "长尾采样 + copy-paste（C58）"],
        ]),
        DUAL(
            "混淆矩阵最容易被忽略、信息量却最大的地方是<strong>最后一行和最后一列</strong>。"
            "很多人把混淆矩阵画成 $C \\times C$（因为工具默认这么画），于是「停车让行召回只有 28%」这个致命信息被完全隐藏了——"
            "在 $C \\times C$ 的矩阵里，这一行的对角线值 23 看起来还行，因为你不知道分母是 81。"
            "<em>而对 TSR 来说，「停车让行」漏检和「指路牌」漏检的安全后果差着好几个数量级。</em>",
            "工程上还要区分「未检出」与「检出但被判 FP」这两种落进最后一列的情况。前者是<span class='term'>召回问题</span>（模型压根没在那个位置输出任何框），"
            "后者是<span class='term'>定位/阈值问题</span>（有框，但 IoU 没到 0.5，或者分数低于评测的最低分数线）。"
            "<strong>这两者的修法完全相反</strong>：召回问题要动分辨率、标签分配、数据；定位问题要动回归损失与 IoU 阈值口径。"
            "所以成熟的评测脚本会把最后一列<em>再拆成两列</em>：<code>miss_no_box</code> 与 <code>miss_low_iou</code>，"
            "这正好对应第 2 节里的 Miss 与 Loc。<strong>混淆矩阵与 TIDE 分解在这里合流。</strong>",
        ),
        CALLOUT("warn", "混淆矩阵的构造有一个陷阱：<strong>你得先决定「拿哪些检测来填矩阵」</strong>。"
                "用全部检测（含分数 0.01 的）会让最后一行爆炸；用 <code>score &gt; 0.5</code> 的会让矩阵依赖于阈值选择。"
                "<em>推荐做法：用「与评测工作点一致的阈值」（见第 6 节）填矩阵，并把阈值写在图标题里。</em>"
                "同一个模型在阈值 0.3 和 0.5 下的混淆矩阵可以讲出完全不同的故事——<strong>不写阈值的混淆矩阵是不可复现的。</strong>"),
    ])),

    # ============================================================== 5
    ("pr-diagnosis", "PR 曲线的诊断读法：形状本身就是证据", "".join([
        P("大多数人看 PR 曲线只看一个东西：曲线下面积（就是 AP）。<strong>但曲线的<em>形状</em>携带的诊断信息，比它的面积多得多。</strong>"
          "AP 是把形状积掉之后剩下的一个数；形状里写着「病在哪一段」。"),
        ASCII("""P                                    P
1 ┤███████████▄                       1 ┤▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
  │           ██▄                       │
  │             ██▄                     │      (A) 健康
  │               ███▄▄                 │  平滑单调下滑，尾部缓慢衰减
  │                    ▀▀▀▀▄▄▄          │  => 没有结构性 bug，
0 └──────────────────────────► R      0 └──────────────────────────► R
  0                          1          0                          1

P                                    P
1 ┤████████████████████                1 ┤
  │                   █                  │  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄
  │                   █                  │
  │      (B) 高召回段崩塌               │      (C) 低召回段就不高
  │                   █                  │  最自信的预测就已经在错
0 ┤                   ▀▀▀▀▀▀▀▀        0 ┤  => **优先怀疑数据管线 bug**
  └──────────────────────────► R        └──────────────────────────► R
  0                 0.7      1          0                          1
  高分部分全对，某个点后突然全错
  => 有一整批样本「完全学不到」

P
1 ┤█████████▌
  │         ▌            (D) 召回天花板
  │         ▌      曲线在 R=0.55 处**直接断掉**
  │         ▌      => 45% 的 GT 从来没有任何检测靠近过
0 ┤         ▌      => Miss 主导；查尺寸分布 / 标注 / 类别表
  └─────────┴────────────────► R
  0        0.55              1"""),
        TABLE(["曲线形状", "定量判据（可代码化）", "最可能的病因", "第一个该做的检查"], [
            ["<strong>(A) 平滑衰减</strong>", "$p(r{=}0.1) &gt; 0.95$ 且 $r_{\\max} &gt; 0.9$ 且中段斜率平缓", "没有结构性问题，属于「模型能力不够」", "跑 TIDE 看 Cls/Loc 谁大，走常规优化"],
            ["<strong>(B) 高召回段崩塌</strong>", "$p(r{=}0.5) &gt; 0.9$ 但 $p(r{=}0.85) &lt; 0.3$，落差集中在 &lt;0.1 的 recall 区间", "<strong>有一整批同质样本完全学不到</strong>：某个尺寸段、某个光照条件、某个子类", "按尺寸/场景分桶重画 PR；十有八九某个桶整段趴着"],
            ["<strong>(C) 低召回段就不高</strong>", "<strong>$p(r{=}0.1) &lt; 0.8$</strong>——最高分的那批预测里就有大量 FP", "<strong>几乎必然是数据管线 bug</strong>：类别映射、坐标格式、评测集类别表不一致", "立刻转模块 03 的三大元凶检查，不要调参"],
            ["<strong>(D) 召回天花板</strong>", "$r_{\\max} &lt; 0.75$（曲线在中途断掉）", "Miss 主导：目标太小 / 被 NMS 吃掉 / 分数低于评测最低分数线 / GT 有但从没输出", "查 GT 尺寸分布；查评测时的 <code>max_dets</code> 与最低分数线"],
        ]),
        P("(C) 这一条值得单独强调，因为它是<strong>最省时间的一个信号</strong>。想清楚它为什么成立："),
        DUAL(
            "PR 曲线的最左端（低 recall）对应的是<strong>模型最自信的那几十个预测</strong>。一个训练正常的检测器，它最自信的预测几乎不可能错——"
            "那些是最大、最清晰、最典型的目标。<em>如果连这批都错了一半，说明错的不是「难度」，而是「规则」</em>："
            "模型在按一套规则输出，评测在按另一套规则判分。<strong>类别 ID 差 1、坐标是 xywh 被当成 xyxy、评测集的类别表和训练时的顺序不同——这三个占了绝大多数。</strong>",
            "反过来说，(B) 高召回段崩塌是<strong>「难度」问题而非「规则」问题</strong>：规则是对的（高分预测都对），只是有一批样本模型确实没学会。"
            "崩塌点的位置还能反推出这批样本的规模——如果 PR 在 $r = 0.72$ 处崩掉，说明大约 28% 的 GT 属于这个「学不到」的子集。"
            "<em>接下来的动作是明确的：按各种维度（像素尺寸、类别、天气、遮挡度、图像区域）分桶重画 PR，找出哪个桶整段贴地。</em>"
            "<strong>找到那个桶，你就把一个模糊的「模型不行」变成了一个具体的、可以定向挖数据或改架构的工程问题。</strong>",
        ),
        CALLOUT("intuition", "一条心法：<strong>PR 曲线的左端诊断「规则」，右端诊断「难度」，中段诊断「能力」。</strong>"
                "<em>左端有病先别碰模型——去查管线；右端有病先别调参——去分桶。</em>"),
        CALLOUT("warn", "画 PR 曲线时必须注明三件事，否则曲线不可比：<strong>① IoU 阈值</strong>（0.5 还是 0.5:0.95 的哪一档）、"
                "<strong>② 是逐类曲线还是所有类混在一起</strong>（后者在长尾数据上几乎无意义，会被头部类完全主导）、"
                "<strong>③ 是否用了单调包络</strong>（VOC 风格的包络会把锯齿抹平，掩盖掉小规模的崩塌）。"
                "<em>诊断时建议看<strong>不包络的原始曲线</strong>——锯齿本身也是信息，密集的锯齿意味着高分区里 TP/FP 交替出现。</em>"),
    ])),

    # ============================================================== 6
    ("operating-point", "score 阈值与工作点：车端要的是「特定 FP 率下的召回」", "".join([
        P("这一节讲的是一个几乎所有做过研究、没做过产品的人都会犯的错：<strong>用 mAP 选模型，然后随便挑个 0.25 的阈值上线。</strong>"),
        H3("mAP 是阈值无关的，产品是阈值有关的"),
        P("AP 的定义里对分数只用了「排序」，没用「绝对值」——把所有分数开平方，AP 完全不变。"
          "<strong>这意味着 mAP 对「模型的分数标定得好不好」完全不敏感</strong>，而线上系统恰恰是靠分数的绝对值做取舍的。"
          "两个 mAP 相同的模型，在 <code>score &gt; 0.4</code> 这个具体工作点上的召回可以差 15 个点。"),
        P("车端的真实需求长这样：<strong>「在误报不超过每 10 公里 1 次的前提下，尽可能早、尽可能全地检出交通标志」</strong>。写成优化问题就是："),
        MATH("\\tau^\\star \\;=\\; \\arg\\max_{\\tau}\\; \\text{Recall}(\\tau) \\quad \\text{s.t.} \\quad \\frac{\\text{FP}(\\tau)}{N_{\\text{frames}}} \\;\\le\\; \\beta"),
        P("$\\beta$ 是产品定的误报预算（FP per frame，或换算成 FP per km / FP per hour）。<strong>注意这里根本没有出现 precision。</strong>"
          "原因是 precision 是个比值，它会随场景里目标的多少而漂移：高速上一公里只有 2 块标志，即使误报率不变，precision 也会比市区低得多。"
          "<em>而 FP/frame 是绝对量，它直接对应「司机每天被误报打扰几次」，是产品和安全团队真正能理解的语言。</em>"),
        TABLE(["指标", "定义", "随场景目标密度变化吗", "谁在用", "TSR 里的适用性"], [
            ["Precision", "TP / (TP + FP)", "<strong>会</strong>（分母含 TP）", "论文", "❌ 跨场景不可比"],
            ["<strong>FP / frame</strong>", "FP 总数 / 帧数", "不会", "<strong>感知与产品团队</strong>", "✅ 主力工作点指标"],
            ["<strong>FP / km</strong>", "FP 总数 / 里程", "不会", "<strong>路测与安全团队</strong>", "✅ 与体验直接对应"],
            ["Recall @ 固定 FP", "满足 FP 预算时的最大召回", "不会", "<strong>模型选型门禁</strong>", "✅ 版本对比的黄金指标"],
            ["mAP", "AP 对类别求平均", "不会（但阈值无关）", "论文、粗筛", "🟡 只能粗筛，不能定工作点"],
        ]),
        H3("必须逐类设阈值"),
        P("TSR 的类别之间<strong>代价极度不对称</strong>：漏掉一个「停车让行」可能导致路口事故；误报一个「景点指示牌」只是让 HMI 上多闪一下。"
          "用同一个全局阈值服务这两类，等于是拿最不重要的类别的误报预算，去限制最重要的类别的召回。"),
        TABLE(["标志类别组", "漏检后果", "误检后果", "建议工作点", "典型阈值"], [
            ["<strong>停车让行 / 让行</strong>", "<strong>可能不减速通过路口</strong>", "无谓刹车，体验差但安全", "召回优先", "<strong>低（0.15–0.25）</strong> + 时序确认"],
            ["限速类", "超速；但通常有地图限速兜底", "错误限速 → 突兀减速 → 后车风险", "<strong>平衡</strong>，且要求高分类准确率", "中（0.35–0.45）"],
            ["禁止类（禁左/禁行）", "违规行驶", "错误封路径 → 绕路", "平衡偏召回", "中（0.30–0.40）"],
            ["指路 / 景点牌", "几乎无后果", "HMI 闪烁，用户投诉", "<strong>精度优先</strong>", "<strong>高（0.55–0.70）</strong>"],
        ]),
        DUAL(
            "为什么阈值不能靠拍脑袋、也不能靠「取 F1 最大点」？因为 F1 隐含地假设了 precision 和 recall<strong>等价重要</strong>，"
            "而 TSR 里这个假设对任何一个类别都不成立。<em>正确做法是把产品的误报预算写成硬约束，在约束下最大化召回——"
            "这样阈值就成了一个可计算的量，而不是一个可争论的量。</em>"
            "notebook 里会实现这个求解器：输入检测结果、GT、帧数、预算 $\\beta$，输出每类的 $\\tau^\\star$ 与对应召回。",
            "还有一层更工程的考虑：<strong>阈值必须在「送进时序融合之前」还是「之后」定，是两个完全不同的问题。</strong>"
            "C55 模块 04 讲的多帧确认会显著改变工作点——单帧允许更低的阈值（更高召回、更多 FP），因为跨帧的一致性检验会把随机 FP 滤掉；"
            "而一个只出现一帧的误检根本活不到上报。<em>所以「单帧阈值」应该按「多帧确认后的 FP 预算」反推，而不是按单帧的 FP 预算设。</em>"
            "<strong>这也解释了一个常见的困惑：为什么离线评测里看起来误报很多的模型，上车之后体验反而更好——因为离线评测的是单帧，产品体验的是融合后的输出。</strong>"
            "如果你的评测流水线只评单帧，你就系统性地高估了误报、低估了召回收益，进而会把阈值定得过高。",
        ),
        CALLOUT("danger", "<p><strong>一个真实且常见的事故模式：用 mAP 做版本门禁，用固定阈值上线。</strong>"
                "新版本 mAP 从 0.72 涨到 0.75，顺利过门禁；上车后误报暴增，因为新模型的分数分布整体右移了（比如换了 loss 或加了标签平滑），"
                "同样的 0.4 阈值现在放行了更多低质量框。<em>mAP 涨了，产品坏了，而且离线指标完全看不出来。</em></p>"
                "<p><strong>解法只有一个：门禁指标必须是「工作点上的指标」</strong>——固定 FP/frame 预算下的召回，或固定召回下的 FP/frame。"
                "<strong>而且每次换模型都要重新求解阈值，不能沿用上一版的。</strong></p>", "mAP 过门禁 ≠ 产品不坏"),
    ])),

    # ============================================================== 7
    ("badcase-sampling", "badcase 可视化：为什么必须分层抽样", "".join([
        P("误差分解给你数字，混淆矩阵给你类别，PR 曲线给你形状——但最终你还是要<strong>用眼睛看图</strong>，因为只有看图才能发现「这些漏检的牌子后面都有一根路灯杆」这种数字里没有的模式。"
          "问题是：<strong>怎么选那 100 张要看的图。</strong>"),
        H3("「随便看看」看到的是分布的众数，不是问题的分布"),
        P("如果你从 badcase 池里均匀随机抽 100 张，你会得到什么？——<strong>你会得到 100 张限速牌</strong>。因为限速牌占了数据的 60%，"
          "即使它的错误率最低，绝对错误数依然最多。于是你花两小时看完，结论是「限速牌有时候会漏」，"
          "而真正的问题（那个只有 40 个样本、AP 只有 0.05 的施工临时牌）你一张都没看到。"),
        P("<strong>这是一个采样偏差问题，而不是勤奋程度问题。</strong>看 500 张也救不了——你只会看到 300 张限速牌。"),
        H3("分层维度：至少四个"),
        TABLE(["分层维度", "典型分桶", "为什么这个维度必须分", "不分的后果"], [
            ["<strong>错误类型</strong>", "Cls / Loc / Both / Dupe / Bkg / Miss", "六类的视觉表现完全不同，混在一起看不出模式", "只看到最多的那类（通常是 Bkg）"],
            ["<strong>像素尺寸</strong>", "&lt;16 / 16–32 / 32–64 / &gt;64 px", "TSR 的错误强烈依赖尺寸，小目标是主战场", "全是大目标的 case，看不出小目标的病"],
            ["<strong>类别频次</strong>", "head（&gt;5%）/ mid / tail（&lt;0.5%）", "长尾类的绝对错误数少但错误率高", "尾部类一张都抽不到"],
            ["<strong>分数区间</strong>", "高分 FP / 低分 FP / 高分被漏的 GT", "高分 FP 是「模型自信地错」，最有诊断价值", "只看高分 = 完全看不到召回问题"],
            ["场景（有条件时）", "夜间 / 逆光 / 雨雪 / 隧道口", "域相关的失效模式只在特定场景出现", "把域问题误判成模型能力问题"],
        ]),
        H3("配额怎么分：不要用比例分配"),
        P("按各层大小成比例分配（$n_h \\propto N_h$）等于没分层——大层还是吃掉全部名额。按等额分配（每层一样多）又会给一个只有 3 个样本的层塞 20 个名额。"
          "实践中最好用的是 <strong>平方根配额（square-root allocation）</strong>："),
        MATH("n_h \\;=\\; \\max\\Bigl(n_{\\min},\\; \\Bigl\\lfloor n_{\\text{total}} \\cdot \\frac{\\sqrt{N_h}}{\\sum_{h'} \\sqrt{N_{h'}}} \\Bigr\\rfloor\\Bigr), \\qquad n_h \\le N_h"),
        P("平方根压缩了层间的规模差异：一个 10000 样本的层和一个 100 样本的层，比例分配下名额差 100 倍，平方根分配下只差 10 倍。"
          "再加上「每个非空层至少 $n_{\\min}$ 个」的下限，就能保证<strong>尾部类和极小目标层一定会被你看到</strong>。"
          "<em>notebook 里会用最大余数法实现它，保证配额之和精确等于 $n_{\\text{total}}$。</em>"),
        DUAL(
            "分层抽样还有一个副产品好处：<strong>它让 badcase review 变成可复现的流程而不是个人手艺。</strong>"
            "同一份检测结果、同一个随机种子，任何人跑出来的 100 张图是同一批；"
            "上一版和这一版的对比可以做到「同一个层里，上版错 12 张、这版错 5 张」。<em>不分层就没法做这种版本对比，因为两次抽到的根本不是同一批东西。</em>",
            "更进一步，成熟团队会把这套抽样固化成<span class='term'>回归可视化集</span>：每个分层固定抽 N 张<em>图像 ID</em>（而不是每次重抽），"
            "每次训完新模型都在这同一批图上出对比图。<strong>这样人眼看到的差异就是模型的差异，而不是抽样的差异。</strong>"
            "代价是这批固定样本会逐渐被「过拟合」——团队会不自觉地针对这 100 张调优。"
            "<em>缓解办法是分两份：一份固定的回归集（用于版本对比），一份每次重抽的探索集（用于发现新问题），后者的种子随版本变化。</em>"
            "这和 C58 的数据闭环、模块 01 的实验纪律是同一套思路：<strong>任何用于决策的观察，都必须先说清它的采样规则。</strong>",
        ),
        CALLOUT("warn", "<p>一个具体的操作细节：<strong>看 badcase 时一定要同时看「模型输出」和「GT」，并且要能看到分数。</strong>"
                "至少有 10–20% 的所谓 badcase 其实是<strong>标注错误</strong>——牌子被标漏了、标错类了、框标歪了。"
                "<em>如果你不看 GT 就断定「模型漏了」，你会去挖一堆数据来修一个根本不存在的问题。</em>"
                "建议在 review 界面上直接放一个「这是标注问题」的按钮，把这类样本回流给标注团队——"
                "这条链路本身就是 C58 数据闭环的一部分，而且往往是投入产出比最高的一条。</p>", "10–20% 的 badcase 是标注错"),
    ])),

    # ============================================================== 8
    ("decision-tree", "从指标到根因：一棵可执行的决策树", "".join([
        P("把前七节合成一个流程。<strong>这棵树的设计原则是「先排除便宜的可能性」</strong>——"
          "查一次类别映射花 10 分钟，训一次模型花 10 小时，所以任何时候都应该先做那个 10 分钟的检查。"),
        ASCII("""【入口】拿到一版模型的评测结果
   │
   ├─ Q1: mAP 是不是接近 0（< 0.05）？
   │      是 ──► **不要做误差分析**，直接去模块 03 查三大元凶：
   │             ① 类别 ID 偏移 0/1  ② 坐标格式弄反  ③ 评测集类别表不一致
   │             （这三个占了 mAP≈0 案例的绝大多数）
   │      否 ↓
   │
   ├─ Q2: PR 曲线在 recall=0.1 处 precision < 0.8 ？
   │      是 ──► 最自信的预测就在错 => **数据管线 bug**，同样转模块 03
   │             典型：通道顺序、归一化 mean/std、验证集用了不同的预处理
   │      否 ↓
   │
   ├─ Q3: 跑 TIDE 分解，看六类 ΔAP 的排序
   │      │
   │      ├─ **Miss 最大** ──► 召回侧问题
   │      │     └─ 按像素尺寸分桶重画 PR
   │      │          ├─ 小目标桶整段趴着 => 分辨率 / P2 层 / 切片推理（C57）
   │      │          ├─ 某类别整段趴着   => 长尾（C58）：采样 / copy-paste / 两级架构
   │      │          └─ 各桶均匀偏低     => 模型容量或训练不足
   │      │
   │      ├─ **Cls 最大** ──► 分类侧问题
   │      │     └─ 看混淆矩阵找冤家对
   │      │          ├─ 集中在 2-3 对   => 细粒度：两级架构 + 高分辨率 crop
   │      │          └─ 弥散在整个矩阵 => 特征不够 / 标注类别定义本身有歧义
   │      │
   │      ├─ **Loc 最大** ──► 定位侧问题
   │      │     └─ 看 Loc 错误的尺寸分布
   │      │          ├─ 集中在小目标   => IoU 度量对小框太苛刻（NWD，C57 m03）
   │      │          └─ 均匀分布       => 回归损失（换 GIoU/DIoU）/ 标签分配
   │      │
   │      ├─ **Bkg 最大且 ΔAP 也大** ──► 难负样本挖掘（C58 m02）/ 提高阈值 / 上下文
   │      │     （注意：Bkg 数量大但 ΔAP 小是常态，那种情况**不用管**）
   │      │
   │      └─ **Dupe 最大** ──► 后处理：NMS 阈值 / class-wise vs agnostic / 一对一分配
   │
   └─ Q4: 六类都不突出、且分布均匀？
          ──► 没有结构性问题，模型处在「能力受限」区间
              => 这时候才轮到：更大 backbone / 更长训练 / 更多数据 / 更强增强
              **注意：这是最后一个选项，不是第一个**"""),
        TABLE(["症状", "首查项（10 分钟内可完成）", "判定证据", "确认后的动作"], [
            ["mAP ≈ 0", "把预测类别整体 ±1 后重算 mAP", "<strong>数值突然正常</strong>", "修类别映射；检查是否有 background 类占了 index 0"],
            ["mAP ≈ 0", "把预测框按 <code>cxcywh→xyxy</code> 转换后重算 IoU 分布", "<strong>平均 IoU 从 0.03 跳到 0.85</strong>", "统一坐标格式；在数据加载处加断言"],
            ["低召回段 precision 低", "dump 一个 batch 的输入张量，看通道均值", "R/B 通道均值与训练统计互换", "修 BGR/RGB；对拍训练与评测的预处理"],
            ["某类召回极低", "查该类 GT 数量与像素尺寸分布", "该类 90% 的 GT &lt; 16 px", "转小目标方案（C57），不要盲目加数据"],
            ["某对类别互相混", "看混淆矩阵的非对角块 + 抽样看图", "两类外观差异 &lt; 2 px", "两级架构；给二级分类器更大输入"],
            ["改动后 mAP +0.3", "<strong>跑 3–5 个种子做配对检验</strong>", "落在种子方差区间内", "<strong>判定为噪声，不要采纳</strong>（模块 01）"],
        ]),
        DUAL(
            "这棵树最重要的性质是<strong>它把「便宜的检查」排在了「昂贵的实验」前面</strong>。Q1 和 Q2 加起来不超过 30 分钟，"
            "却能拦下最常见、也最浪费时间的一整类问题——很多人在这两个问题上耗掉的是「训了三天发现是类别 ID 差 1」。"
            "<em>而 Q4 那个「换更大的 backbone」被放在最后，不是因为它没用，而是因为它<strong>掩盖问题的能力太强</strong>："
            "一个有管线 bug 的系统换了更大的模型也会涨点，于是 bug 被永久地留在了代码里。</em>",
            "从方法论上看，这是<span class='term'>期望信息增益除以成本</span>的贪心排序：每一步选「能排除最多可能性 ÷ 花费最少时间」的检查。"
            "这个原则可以推广到任何调试场景，也是模块 03 那整本手册的组织依据。"
            "<strong>另一个值得内化的原则是：每一步都要求「可证伪的证据」，而不是「看起来像」。</strong>"
            "「我觉得是小目标问题」不算证据；「按尺寸分桶后 &lt;16 px 桶的 AP 是 0.04、其余桶都 &gt; 0.7」才算证据。"
            "<em>面试里描述排查过程时，每说一个假设就跟一句「我会用 X 来验证它，如果看到 Y 就说明成立」——这个习惯会让你的回答听起来完全不一样。</em>",
        ),
        CALLOUT("intuition", "<strong>整棵树可以压成一句话：先证伪「管线错了」，再证伪「数据不够」，最后才承认「模型不行」。</strong>"
                "<em>绝大多数人是反着做的——上来就换模型，然后在一个有 bug 的管线上做了三个月的架构消融。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("误差分析看起来是「工程」，但它底下压着一批相当硬的开放问题。下面这些既是研究方向，也是面试里展示深度的材料。"),
        UL([
            "<strong>归因的唯一性。</strong>TIDE 用一棵固定的判定树换取可复现性，但归因本身是不唯一的（第 2 节）。"
            "<em>有没有一种「分解结果不依赖判定顺序」的定义？Shapley 值是一条路（对 $2^6$ 个 oracle 子集求边际贡献），"
            "但计算量与可解释性的取舍尚无定论，而且 Shapley 的公理是否适合 AP 这种排序型泛函也没被认真论证过。</em>",
            "<strong>误差分解与下游安全后果的脱节。</strong>ΔAP 度量的是「对 mAP 的贡献」，但 TSR 真正关心的是「对驾驶行为的影响」。"
            "<em>一个把「限速 80」判成「限速 60」的 Cls 错误，和把「停车让行」漏掉的 Miss 错误，在 ΔAP 上可能一样大，在安全上差着几个数量级。</em>"
            "把代价矩阵嵌进误差分解（cost-sensitive TIDE），是一个实用价值极高但公开工作很少的方向（C55 模块 05 给了代价敏感评测的雏形）。",
            "<strong>时序维度的误差分解完全缺失。</strong>现有工具全部是单帧的。而 TSR 是一个「接近过程」，"
            "真正的产品指标是<em>首次检出距离</em>、<em>闪烁次数</em>、<em>误报持续时长</em>。"
            "<strong>「把 TIDE 推广到 track 级」——把一条轨迹的失败归因到 ID 切换、过晚检出、中途丢失、类别跳变——目前没有标准工具。</strong>",
            "<strong>自动化的根因归纳。</strong>现在的流程是「分解 → 人看 badcase → 人总结模式」。"
            "<em>能否用 VLM 自动给 badcase 打场景标签，再做关联规则挖掘，直接输出「漏检集中在『逆光 + 树影 + 小于 20 px』这个交集」？</em>"
            "这正是 C58 模块 04 讲的 scenario tagging 与误差分析的交汇处，也是 JD 里 "
            "「automated data mining workflows」最有含金量的一层。",
            "<strong>标注噪声与模型错误的可分离性。</strong>10–20% 的 badcase 是标注问题（第 7 节）。"
            "<em>置信学习（confident learning）、损失轨迹分析、多模型一致性都能部分识别，但在检测任务上（涉及框与类别两个维度）仍缺少成熟方法。</em>"
            "在评测集上，一个未被识别的标注错误会同时污染分子和分母，使误差分解系统性偏移。",
            "<strong>评测集本身的代表性。</strong>所有误差分析的结论都以「评测集能代表线上分布」为前提。"
            "<em>当评测集与实际路况分布偏移时，你会自信地修一个线上并不重要的问题。</em>"
            "分布偏移的检测、评测集的持续更新与「评测集也要做版本管理」，是把误差分析真正落地的前提（C37 与 C58 模块 05）。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Bolya et al., <em>TIDE: A General Toolbox for Identifying Object Detection Errors</em>"
                "（ECCV 2020，arXiv:2008.08115）——重点读 §3 的六类定义与 oracle 设计、§4 对比不同检测器的分解结果"
                "（<em>看 one-stage 与 two-stage 的错误构成差异，这是面试里很好的谈资</em>）。配套代码 <code>tidecv</code> 只有几百行，建议通读。</p>"
                "<p><strong>★</strong> Hoiem, Chodpathumwan &amp; Dai, <em>Diagnosing Error in Object Detectors</em>（ECCV 2012）——"
                "TIDE 的思想源头，第一次系统提出「按错误类型分解检测器性能」；它对目标尺寸、长宽比、遮挡等属性的分层分析至今仍是模板。</p>"
                "<p><strong>★</strong> Lin et al., <em>Microsoft COCO</em>（ECCV 2014）附带的 detection analysis toolkit——"
                "那套 PR 曲线叠加图（C75 / Loc / Sim / Oth / BG / FN 逐层放宽）是 TIDE 的直接前身，理解它有助于理解「为什么需要 oracle」。</p>"
                "<p>延伸：Everingham et al., <em>The PASCAL VOC Challenge</em>（IJCV 2010，AP 定义与单调包络的来源）；"
                "Northcutt et al., <em>Confident Learning</em>（JAIR 2021，标注噪声识别）；"
                "Oksuz et al., <em>Localization Recall Precision (LRP) Error</em>（ECCV 2018，一个把定位质量显式写进指标的替代方案）。"
                "相邻课程：本课模块 01（种子方差与显著性）、模块 03（管线 bug 的诊断手册）、"
                "C55 模块 05（安全导向评测与分桶）、C57 模块 05（按尺寸分桶）、C58 模块 05（闭环验证）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · 误差分析工程（TIDE 六类分解 / 修复收益 / PR 诊断 / 工作点 / 分层抽样）

目标：把「mAP = 0.60，下一步做什么」这个问题，变成一串**可以算出来的数字**。

本 notebook 你会亲手实现：
1. **可控误差的合成 TSR 评测集** —— 用 `IoU = (w-dx)/(w+dx)` 精确注入指定 IoU 的定位误差
2. **VOC 全点 AP / mAP**（单调包络 + 面积）
3. **完整的 TIDE 六类误差分解**：Cls / Loc / Both / Dupe / Bkg / Miss
4. **六个 oracle 与修复收益 ΔmAP** —— 「修好每一类能涨多少」，并验证 **ΔAP 不可加**
5. **逐类 AP + $(C{+}1)\\times(C{+}1)$ 混淆矩阵**，自动找出最容易互相错分的标志对
6. **PR 曲线诊断器**：从曲线形状读出「管线 bug / 召回天花板 / 尾部崩塌 / 健康」
7. **工作点求解**：给定 FP/frame 预算求每类的最优 score 阈值
8. **badcase 分层抽样器**：平方根配额 + 最大余数法 + 按修复收益加权
9. **根因决策树的代码化**

> 心智模型：**mAP 告诉你「有多差」，误差分解告诉你「修哪个最划算」。**"""),

    md("""## 1 · 工具：IoU 与「精确注入指定 IoU」

后面所有实验都要能**按需造出 IoU 恰好等于 0.32 的框**。用水平平移就能做到闭式解：
同尺寸的框水平平移 $dx$ 后，交 $=(w-dx)h$、并 $=2wh-(w-dx)h$，于是

$$\\text{IoU} = \\frac{w-dx}{w+dx} \\quad\\Longrightarrow\\quad dx = w\\cdot\\frac{1-\\text{IoU}}{1+\\text{IoU}}$$

顺带记住那个**面试常考的数字**：$8\\times8$ 的框平移 2 px，IoU $= 6/10 = 0.6$；沿对角线平移 2 px 则是 $36/92 = 0.391$。"""),

    code("""import numpy as np
from collections import defaultdict, Counter

rng = np.random.default_rng(7)

CLASSES = ['限速30', '限速60', '限速80', '停车让行', '禁止左转', '注意行人', '解除限速', '指路牌']
NC = len(CLASSES)


def iou_matrix(a, b):
    # a: (N,4) xyxy, b: (M,4) xyxy -> (N,M)
    a = np.asarray(a, float).reshape(-1, 4)
    b = np.asarray(b, float).reshape(-1, 4)
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(aa[:, None] + bb[None, :] - inter, 1e-9)


def shift_for_iou(w, target_iou):
    # 水平平移量，使平移后的同尺寸框与原框 IoU 恰好等于 target_iou
    return w * (1.0 - target_iou) / (1.0 + target_iou)


base = np.array([[100., 100., 140., 140.]])          # 40x40 的框
for t in [0.9, 0.6, 0.5, 0.3, 0.15]:
    dx = shift_for_iou(40.0, t)
    got = iou_matrix(base, base + np.array([dx, 0, dx, 0]))[0, 0]
    assert abs(got - t) < 1e-9, (t, got)
print('✅ shift_for_iou 精确：可以按需造出任意 IoU 的定位误差')

# 小目标对位移的敏感性（面试常考）
small = np.array([[0., 0., 8., 8.]])
print('8x8 框水平移 2px 的 IoU =', round(float(iou_matrix(small, small + [2, 0, 2, 0])[0, 0]), 4), '= 6/10')
print('8x8 框对角移 2px 的 IoU =', round(float(iou_matrix(small, small + [2, 2, 2, 2])[0, 0]), 4), '= 36/92')
assert abs(float(iou_matrix(small, small + [2, 2, 2, 2])[0, 0]) - 36 / 92) < 1e-12
big = np.array([[0., 0., 64., 64.]])
print('64x64 框对角移 2px 的 IoU =', round(float(iou_matrix(big, big + [2, 2, 2, 2])[0, 0]), 4))
print('👉 同样 2 px 的误差，小框跌破 0.5 阈值，大框几乎无损 —— 这是 Loc 错误的物理来源')"""),

    md("""## 2 · 合成一个可控的 TSR 评测集

**合成规则**（每一条都对应真实检测器的一种行为）：
- 200 帧 1920×1080，每帧 1–4 块标志；类别按长尾先验采样（限速类多、停车让行少）
- 标志边长服从对数正态（中位数 30 px，从 10 px 到 130 px）—— TSR 的真实尺寸分布
- 每个 GT 按固定概率落入五种结局之一：**TP / Miss / Loc / Cls / Both**
  - `Loc`：同类，IoU 精确落在 [0.18, 0.46)（跌破 0.5 阈值）
  - `Cls`：框几乎完美，但类别被换成**易混淆的那个**（限速60↔80、禁左→解除限速）
  - `Both`：框歪 + 类错
- TP 有 12% 概率再生一个**重复框**（IoU 0.55–0.8，分数打折）→ Dupe
- 每帧额外 7 个**背景误检**，分数偏低但有长尾（模拟广告牌/车身贴纸偶尔拿到高分）

> 这样我们**事先就知道地面真相**，可以验证分解器是否把每类错误都找了回来。"""),

    code("""# 易混淆映射：只有限速类家族内部会互相错分（映射到自己 = 没有「双胞胎」）
CONFUSE = {0: 2, 1: 2, 2: 1, 3: 3, 4: 4, 5: 5, 6: 1, 7: 7}
CLS_PRIOR = np.array([0.10, 0.24, 0.20, 0.05, 0.09, 0.08, 0.06, 0.18])
CLS_PRIOR = CLS_PRIOR / CLS_PRIOR.sum()

N_IMG, W, H = 200, 1920, 1080
P_MISS, P_LOC, P_CLS, P_BOTH = 0.09, 0.10, 0.16, 0.05       # 其余为 TP
P_DUPE, N_BKG_PER_IMG = 0.12, 7

g_img, g_cls, g_box = [], [], []
d_img, d_cls, d_box, d_score = [], [], [], []

for im in range(N_IMG):
    for _ in range(int(rng.integers(1, 5))):
        c = int(rng.choice(NC, p=CLS_PRIOR))
        s = float(np.clip(np.exp(rng.normal(np.log(30), 0.55)), 10, 130))    # 标志边长 px
        cx, cy = float(rng.uniform(120, W - 120)), float(rng.uniform(80, H * 0.62))
        gb = np.array([cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2])
        g_img.append(im); g_cls.append(c); g_box.append(gb)

        u = rng.random()
        if u < P_MISS:                                        # 【Miss】完全没输出
            continue
        elif u < P_MISS + P_LOC:                              # 【Loc】类对框歪
            dx = shift_for_iou(s, float(rng.uniform(0.18, 0.46)))
            db, dc = gb + np.array([dx, 0, dx, 0]), c
            sc = 0.28 + 0.55 * rng.beta(2.0, 2.0)
        elif u < P_MISS + P_LOC + P_CLS:                      # 【Cls】框对类错（且很自信）
            db = gb + rng.normal(0, 0.02 * s, 4)
            dc = CONFUSE[c]                                   # 没有双胞胎的类 -> 仍是 TP
            sc = 0.40 + 0.52 * rng.beta(2.6, 1.4)
        elif u < P_MISS + P_LOC + P_CLS + P_BOTH:             # 【Both】都错
            dx = shift_for_iou(s, float(rng.uniform(0.15, 0.45)))
            db = gb + np.array([dx, 0, dx, 0])
            dc = CONFUSE[c]                                   # 没有双胞胎的类 -> 退化为 Loc
            sc = 0.25 + 0.5 * rng.beta(2.0, 2.2)
        else:                                                 # 【TP】
            db, dc = gb + rng.normal(0, 0.012 * s, 4), c
            sc = 0.45 + 0.5 * rng.beta(2.8, 1.2)
            if rng.random() < P_DUPE:                         # 【Dupe】重复框
                dx2 = shift_for_iou(s, float(rng.uniform(0.55, 0.8)))
                d_img.append(im); d_cls.append(c)
                d_box.append(gb + np.array([dx2, 0, dx2, 0]))
                d_score.append(sc * float(rng.uniform(0.45, 0.9)))
        d_img.append(im); d_cls.append(dc); d_box.append(db); d_score.append(min(sc, 0.995))

    for _ in range(N_BKG_PER_IMG):                            # 【Bkg】背景误检
        s = float(np.exp(rng.normal(np.log(34), 0.6)))
        cx, cy = float(rng.uniform(60, W - 60)), float(rng.uniform(40, H - 40))
        d_img.append(im); d_cls.append(int(rng.choice(NC, p=CLS_PRIOR)))
        d_box.append(np.array([cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2]))
        d_score.append(0.05 + 0.88 * rng.beta(1.5, 3.4))

GT = dict(img=np.array(g_img), cls=np.array(g_cls), box=np.array(g_box))
DT = dict(img=np.array(d_img), cls=np.array(d_cls), box=np.array(d_box), score=np.array(d_score))
print(f'GT {len(GT["img"])} 个目标 / {N_IMG} 帧;  检测 {len(DT["img"])} 个框')
print('每类 GT 数:', {CLASSES[c]: int((GT['cls'] == c).sum()) for c in range(NC)})
assert len(GT['img']) > 400 and len(DT['img']) > 1500"""),

    md("""## 3 · VOC 全点 AP 与 mAP

判定流程（C18 模块 03 的复习）：**按分数降序 → 每个检测取同图同类 IoU 最大的 GT →
IoU ≥ 0.5 且该 GT 未被占用则 TP，否则 FP → 累积 P/R → 单调包络 → 求面积**。

注意「IoU ≥ 0.5 但 GT 已被更高分的框占用 ⇒ FP」这一条——**它就是 Dupe 的来源**。"""),

    code("""def match_class(dets, gts, c, iou_thr=0.5):
    # 返回该类别下按分数降序的 (scores, is_tp, best_gt_idx, n_gt)
    di = np.where(dets['cls'] == c)[0]
    gi = np.where(gts['cls'] == c)[0]
    n_gt = len(gi)
    if len(di) == 0:
        return np.zeros(0), np.zeros(0, bool), np.zeros(0, int), n_gt
    order = di[np.argsort(-dets['score'][di], kind='stable')]
    gt_by_img = defaultdict(list)
    for j in gi:
        gt_by_img[int(gts['img'][j])].append(j)
    matched, is_tp, best = set(), np.zeros(len(order), bool), np.full(len(order), -1)
    for r, i in enumerate(order):
        cand = gt_by_img.get(int(dets['img'][i]), [])
        if not cand:
            continue
        ious = iou_matrix(dets['box'][i:i + 1], gts['box'][cand])[0]
        k = int(np.argmax(ious))
        if ious[k] >= iou_thr:
            best[r] = cand[k]
            if cand[k] not in matched:                 # GT 未被占 -> TP；已被占 -> FP（= Dupe）
                matched.add(cand[k]); is_tp[r] = True
    return dets['score'][order], is_tp, best, n_gt


def voc_ap(rec, prec):
    # 单调包络 + 面积（VOC 全点插值）
    if len(rec) == 0:
        return 0.0
    mrec = np.concatenate([[0.0], rec, [rec[-1]]])
    mpre = np.concatenate([[0.0], prec, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def class_pr(dets, gts, c, iou_thr=0.5):
    sc, tp, _, n_gt = match_class(dets, gts, c, iou_thr)
    if len(sc) == 0 or n_gt == 0:
        return np.zeros(0), np.zeros(0)
    ctp = np.cumsum(tp.astype(float)); cfp = np.cumsum((~tp).astype(float))
    return ctp / n_gt, ctp / np.maximum(ctp + cfp, 1e-12)


def evaluate(dets, gts, iou_thr=0.5):
    aps = {}
    for c in range(NC):
        n_gt = int((gts['cls'] == c).sum())
        if n_gt == 0:
            continue
        rec, prec = class_pr(dets, gts, c, iou_thr)
        aps[c] = voc_ap(rec, prec)
    return float(np.mean(list(aps.values()))), aps


# 手算校验：一个 GT、两个检测（高分 TP + 低分 Dupe）
tiny_g = dict(img=np.array([0]), cls=np.array([0]), box=np.array([[0., 0., 10., 10.]]))
tiny_d = dict(img=np.array([0, 0]), cls=np.array([0, 0]),
              box=np.array([[0., 0., 10., 10.], [1., 0., 11., 10.]]), score=np.array([0.9, 0.8]))
m, a = evaluate(tiny_d, tiny_g)
assert abs(a[0] - 1.0) < 1e-12, a          # 第 1 个就命中，recall 直接到 1，AP=1
print('手算校验 AP =', a[0], '（第一个检测就命中，后面的 Dupe 不再增加 recall）')

mAP0, aps0 = evaluate(DT, GT)
print(f'\\n=== baseline mAP@0.5 = {mAP0:.4f} ===')
print(f'{"类别":<10s}{"AP":>8s}{"GT 数":>8s}')
for c in range(NC):
    print(f'{CLASSES[c]:<10s}{aps0[c]:>8.3f}{int((GT["cls"] == c).sum()):>8d}')
assert 0.4 < mAP0 < 0.8
print('\\n👉 拿到这个 0.60，你现在还是不知道下一步该做什么。继续往下。')"""),

    md("""## 4 · TIDE 六类误差分解

对每个非 TP 的检测算两个数：
- $u_{\\text{same}}$：与**同类** GT 的最大 IoU
- $u_{\\text{other}}$：与**异类** GT 的最大 IoU

然后走判定树（顺序不能变）：

```
u_same >= 0.5              -> Dupe   （能匹配，但 GT 被更高分的框占了）
0.1 <= u_same < 0.5        -> Loc    （类对框歪）
u_other >= 0.5             -> Cls    （框对类错）
0.1 <= u_other < 0.5       -> Both
否则                        -> Bkg    （周围什么都没有）
```

**Miss** 单独算：所有「没有任何检测以 IoU ≥ 0.1 靠近过」的 GT。
这个定义保证了 Miss 与 Cls/Loc **不重复计数**——被 Cls 错误覆盖的 GT 不算 Miss。"""),

    code("""def tide_classify(dets, gts, tf=0.5, tb=0.1):
    # 返回 (每个检测的错误标签, 归因到的 GT 下标, 每个 GT 是否 Miss, u_same, u_other)
    n_d = len(dets['img'])
    label = np.array(['Bkg'] * n_d, dtype=object)
    tgt = np.full(n_d, -1)
    u_same = np.zeros(n_d); u_other = np.zeros(n_d)

    for c in range(NC):                                    # ① 先做匹配，确定 TP
        di = np.where(dets['cls'] == c)[0]
        if len(di) == 0:
            continue
        order = di[np.argsort(-dets['score'][di], kind='stable')]
        _, is_tp, best, _ = match_class(dets, gts, c, tf)
        for r, i in enumerate(order):
            if is_tp[r]:
                label[i] = 'TP'; tgt[i] = best[r]

    gt_by_img = defaultdict(list)
    for j in range(len(gts['img'])):
        gt_by_img[int(gts['img'][j])].append(j)

    for i in range(n_d):                                   # ② 非 TP 的走判定树
        cand = np.array(gt_by_img.get(int(dets['img'][i]), []), dtype=int)
        j_s = j_o = -1
        if len(cand):
            same = cand[gts['cls'][cand] == dets['cls'][i]]
            other = cand[gts['cls'][cand] != dets['cls'][i]]
            if len(same):
                v = iou_matrix(dets['box'][i:i + 1], gts['box'][same])[0]
                k = int(np.argmax(v)); u_same[i], j_s = float(v[k]), int(same[k])
            if len(other):
                v = iou_matrix(dets['box'][i:i + 1], gts['box'][other])[0]
                k = int(np.argmax(v)); u_other[i], j_o = float(v[k]), int(other[k])
        if label[i] == 'TP':
            continue
        if u_same[i] >= tf:
            label[i], tgt[i] = 'Dupe', j_s
        elif u_same[i] >= tb:
            label[i], tgt[i] = 'Loc', j_s
        elif u_other[i] >= tf:
            label[i], tgt[i] = 'Cls', j_o
        elif u_other[i] >= tb:
            label[i], tgt[i] = 'Both', j_o
        else:
            label[i] = 'Bkg'

    covered = np.zeros(len(gts['img']), bool)              # ③ Miss：没被任何框靠近过的 GT
    for i in range(n_d):
        cand = gt_by_img.get(int(dets['img'][i]), [])
        if not cand:
            continue
        v = iou_matrix(dets['box'][i:i + 1], gts['box'][cand])[0]
        for k, j in enumerate(cand):
            if v[k] >= tb:
                covered[j] = True
    return label, tgt, ~covered, u_same, u_other


LAB, TGT, MISS, U_SAME, U_OTHER = tide_classify(DT, GT)
CNT = Counter(LAB.tolist()); CNT['Miss'] = int(MISS.sum())
ERR_TYPES = ['Cls', 'Loc', 'Both', 'Dupe', 'Bkg', 'Miss']

print(f'{"类型":<8s}{"数量":>8s}{"占全部错误":>12s}')
n_err = sum(CNT[e] for e in ERR_TYPES)
for e in ERR_TYPES:
    print(f'{e:<8s}{CNT[e]:>8d}{CNT[e] / n_err:>11.1%}')
print(f'{"TP":<8s}{CNT["TP"]:>8d}')

assert CNT['TP'] + CNT['Loc'] + CNT['Cls'] + CNT['Both'] + CNT['Dupe'] + CNT['Bkg'] == len(DT['img'])
assert CNT['Bkg'] > 10 * CNT['Cls'], '合成时背景误检就是最多的'
print(f'\\n⚠️  Bkg 的数量是 Cls 的 {CNT["Bkg"] / CNT["Cls"]:.0f} 倍。凭数量做决策的话，你会去治背景误检。')
print('   下一节会证明这是错的。')"""),

    md("""## 5 · 修复收益：ΔmAP 才是决策依据

六个 **oracle**（先知）各修好一类错误，其余不动，重算 mAP：

| oracle | 动作 |
|---|---|
| `Loc`  | 把 Loc 错误的框**吸附到**它归因的 GT 上（分数与排序不变）|
| `Cls`  | 把 Cls 错误的**预测类别改对**（框不动）|
| `Both` | 类别与框一起修 |
| `Dupe` | **删掉**重复框 |
| `Bkg`  | **删掉**背景误检 |
| `Miss` | 把「完全没被看见」的 GT **从评测集里移除**（改的是 $G$ 不是 $D$）|

$$\\Delta\\text{AP}_i = \\text{mAP}\\bigl(\\mathcal{O}_i(D),\\,G\\bigr) - \\text{mAP}(D,\\,G)$$"""),

    code("""def apply_oracle(kind, dets, gts, lab, tgt, miss):
    d = {k: v.copy() for k, v in dets.items()}
    g = {k: v.copy() for k, v in gts.items()}
    if kind == 'Loc':
        m = (lab == 'Loc'); d['box'][m] = g['box'][tgt[m]]
    elif kind == 'Cls':
        m = (lab == 'Cls'); d['cls'][m] = g['cls'][tgt[m]]
    elif kind == 'Both':
        m = (lab == 'Both'); d['cls'][m] = g['cls'][tgt[m]]; d['box'][m] = g['box'][tgt[m]]
    elif kind in ('Dupe', 'Bkg'):
        keep = (lab != kind); d = {k: v[keep] for k, v in d.items()}
    elif kind == 'Miss':
        g = {k: v[~miss] for k, v in g.items()}
    return d, g


GAINS, PER100 = {}, {}
print(f'{"类型":<7s}{"数量":>7s}{"修好后 mAP":>12s}{"ΔmAP(pp)":>11s}{"每100个错的ΔmAP":>17s}')
for kind in ERR_TYPES:
    d2, g2 = apply_oracle(kind, DT, GT, LAB, TGT, MISS)
    m2, _ = evaluate(d2, g2)
    GAINS[kind] = m2 - mAP0
    PER100[kind] = GAINS[kind] * 100 / max(CNT[kind], 1) * 100
    print(f'{kind:<7s}{CNT[kind]:>7d}{m2:>12.4f}{GAINS[kind] * 100:>+11.2f}{PER100[kind]:>17.3f}')

for k in ['Dupe', 'Bkg', 'Miss']:
    assert GAINS[k] >= -1e-9, (k, GAINS[k])          # 删 FP / 删未覆盖 GT 只可能不变差
assert GAINS['Cls'] > GAINS['Bkg'], '数量最多的 Bkg 反而最不值钱'
assert PER100['Cls'] > 50 * PER100['Bkg']

print(f'\\n六项 ΔmAP 之和 = {sum(GAINS.values()) * 100:.2f} pp')
print(f'离满分的总差距   = {(1 - mAP0) * 100:.2f} pp')
assert sum(GAINS.values()) < 1 - mAP0
print('👉 **ΔAP 不可加**：AP 经过排序/包络/求面积三重非线性，oracle 的效应不满足叠加原理。')
print('   两类错误常常打在同一批 GT 上，第一个 oracle 救回来的，第二个就救不到了。')"""),

    code("""# 决策：ΔmAP / 工程成本 —— 真实世界的排序依据
COST = {'Cls': 3.0, 'Loc': 5.0, 'Both': 5.0, 'Dupe': 0.5, 'Bkg': 4.0, 'Miss': 12.0}   # 人天（估）
print(f'{"类型":<7s}{"ΔmAP(pp)":>10s}{"成本(人天)":>11s}{"ROI = pp/人天":>15s}')
roi = {k: GAINS[k] * 100 / COST[k] for k in ERR_TYPES}
for k in sorted(roi, key=lambda x: -roi[x]):
    print(f'{k:<7s}{GAINS[k] * 100:>+10.2f}{COST[k]:>11.1f}{roi[k]:>15.3f}')
best = max(roi, key=lambda k: roi[k])
print(f'\\n👉 按 ΔmAP 排序第一名 = {max(GAINS, key=lambda k: GAINS[k])}')
print(f'   按 ROI  排序第一名 = {best}')
print('   两者不一定相同 —— Miss 的 ΔmAP 不小，但要靠「提分辨率 + 加 P2 层」兑现，代价最高。')
assert roi['Cls'] > roi['Bkg'] and roi['Cls'] > roi['Miss']"""),

    md("""## 6 · 逐类 AP 与 $(C{+}1)\\times(C{+}1)$ 混淆矩阵

检测的混淆矩阵**必须多一行一列**：
- 最后一**列** = 该类 GT 没被任何检测认领（Miss + 定位失败）
- 最后一**行** = 背景被误检成某类（Bkg）

只画 $C\\times C$ 的话，「停车让行召回只有 68%」这种致命信息会被完全隐藏。"""),

    code("""def confusion_matrix(dets, gts, score_thr=0.30, iou_thr=0.5):
    cm = np.zeros((NC + 1, NC + 1), dtype=int)
    keep = np.where(dets['score'] >= score_thr)[0]
    keep = keep[np.argsort(-dets['score'][keep], kind='stable')]      # 类别无关的贪心匹配
    gt_by_img = defaultdict(list)
    for j in range(len(gts['img'])):
        gt_by_img[int(gts['img'][j])].append(j)
    used = set()
    for i in keep:
        cand = [j for j in gt_by_img.get(int(dets['img'][i]), []) if j not in used]
        if cand:
            v = iou_matrix(dets['box'][i:i + 1], gts['box'][cand])[0]
            k = int(np.argmax(v))
            if v[k] >= iou_thr:
                used.add(cand[k])
                cm[int(gts['cls'][cand[k]]), int(dets['cls'][i])] += 1
                continue
        cm[NC, int(dets['cls'][i])] += 1                              # 背景误检
    for j in range(len(gts['img'])):
        if j not in used:
            cm[int(gts['cls'][j]), NC] += 1                           # 未被认领的 GT
    return cm


SCORE_THR = 0.30
CM = confusion_matrix(DT, GT, SCORE_THR)
assert (CM[:NC].sum(1) == np.bincount(GT['cls'], minlength=NC)).all(), '每行之和必须等于该类 GT 数'

hdr = ''.join(f'{c[:4]:>7s}' for c in CLASSES) + f'{"未检出":>8s}'
print(f'混淆矩阵（score >= {SCORE_THR}）  行=真值, 列=预测')
print(f'{"":<10s}{hdr}')
for i in range(NC):
    row = ''.join(f'{CM[i, j]:>7d}' for j in range(NC))
    print(f'{CLASSES[i]:<10s}{row}{CM[i, NC]:>8d}')
row = ''.join(f'{CM[NC, j]:>7d}' for j in range(NC))
print(f'{"背景误检":<10s}{row}{"-":>8s}')"""),

    code("""def top_confused(cm, k=4):
    # 对称化的非对角热点：最容易互相错分的标志对
    out = [(int(cm[i, j] + cm[j, i]), i, j) for i in range(NC) for j in range(i + 1, NC)]
    out.sort(reverse=True)
    return out[:k]


print('最容易互相错分的标志对：')
for n, i, j in top_confused(CM):
    print(f'  {CLASSES[i]} <-> {CLASSES[j]:<8s} {n:>4d} 次')
worst = top_confused(CM, 1)[0]
assert {worst[1], worst[2]} == {1, 2}, '合成时就是限速60↔80 最混'
print('👉 限速 60 ↔ 80 是 TSR 的经典冤家：整体形状颜色完全一致，')
print('   差异只在数字中间那一横 —— 20 px 的框里它只有约 1.6 px 宽。')

print(f'\\n{"类别":<10s}{"AP":>7s}{"召回":>8s}{"被误检成它":>12s}{"GT数":>7s}')
for i in range(NC):
    rec_i = 1 - CM[i, NC] / max(CM[i].sum(), 1)
    print(f'{CLASSES[i]:<10s}{aps0[i]:>7.3f}{rec_i:>8.2f}{CM[NC, i]:>12d}{int(CM[i].sum()):>7d}')
print('\\n⚠️  只看第一列（AP）会漏掉两件事：该类的召回天花板、该类是不是「误检磁铁」。')"""),

    md("""## 7 · PR 曲线诊断：形状即证据

四种形状对应四种病。先算三个关键量（$p(r)$ 取单调包络意义下的 $\\max_{\\tilde r\\ge r} p(\\tilde r)$）：

| 量 | 含义 | 读法 |
|---|---|---|
| `p10` = $p(r{=}0.1)$ | 最自信的那批预测的精度 | **< 0.8 ⇒ 管线 bug**，不要调参 |
| `r_max` | 召回天花板 | **< 0.75 ⇒ 有一批 GT 从没被覆盖** |
| `p50`, `p85` | 中段与尾段精度 | `p50 高 + p85 崩` ⇒ 尾部塌陷 |

下面先造四条**手工曲线**当标尺，再用它们量真实模型。"""),

    code("""def p_at_recall(rec, prec, r):
    m = np.asarray(rec) >= r
    return float(np.asarray(prec)[m].max()) if m.any() else 0.0


def pr_shape_stats(rec, prec):
    rec = np.asarray(rec, float); prec = np.asarray(prec, float)
    return dict(r_max=float(rec.max()) if rec.size else 0.0,
                p10=p_at_recall(rec, prec, 0.10),
                p50=p_at_recall(rec, prec, 0.50),
                p85=p_at_recall(rec, prec, 0.85))


def make_curve(kind):
    if kind == 'HEALTHY':          # 平滑衰减
        r = np.linspace(0.02, 0.90, 60); p = 0.99 - 0.35 * (r / 0.9) ** 2
    elif kind == 'TAIL_COLLAPSE':  # 高分段完美，某点后突然崩
        r1 = np.linspace(0.02, 0.70, 40); p1 = np.full_like(r1, 0.97)
        r2 = np.linspace(0.71, 0.93, 40); p2 = np.linspace(0.55, 0.04, 40)
        r, p = np.concatenate([r1, r2]), np.concatenate([p1, p2])
    elif kind == 'DATA_BUG':       # 最自信的预测就在错
        r = np.linspace(0.02, 0.85, 50); p = 0.44 - 0.10 * (r / 0.85)
    else:                          # RECALL_CEILING：曲线中途断掉
        r = np.linspace(0.02, 0.55, 40); p = 0.96 - 0.10 * (r / 0.55)
    return r, p


print(f'{"标尺曲线":<16s}{"r_max":>8s}{"p10":>8s}{"p50":>8s}{"p85":>8s}')
REF = {}
for k in ['HEALTHY', 'TAIL_COLLAPSE', 'DATA_BUG', 'RECALL_CEILING']:
    r, p = make_curve(k); s = pr_shape_stats(r, p); REF[k] = s
    print(f'{k:<16s}{s["r_max"]:>8.2f}{s["p10"]:>8.2f}{s["p50"]:>8.2f}{s["p85"]:>8.2f}')

assert REF['DATA_BUG']['p10'] < 0.80              # 低召回段就不高
assert REF['RECALL_CEILING']['r_max'] < 0.75      # 天花板
assert REF['TAIL_COLLAPSE']['p50'] > 0.90 and REF['TAIL_COLLAPSE']['p85'] < 0.30
assert REF['HEALTHY']['p10'] > 0.95 and REF['HEALTHY']['r_max'] > 0.85
print('\\n✅ 三条判据都是可代码化的阈值，不是「看图感觉」。')"""),

    code("""# ① 真实模型的逐类曲线
print(f'{"类别":<10s}{"r_max":>8s}{"p10":>8s}{"p50":>8s}{"p85":>8s}')
base_stats = {}
for c in range(NC):
    s = pr_shape_stats(*class_pr(DT, GT, c)); base_stats[c] = s
    print(f'{CLASSES[c]:<10s}{s["r_max"]:>8.2f}{s["p10"]:>8.2f}{s["p50"]:>8.2f}{s["p85"]:>8.2f}')
print('👉 每一类的 p10 都是 1.00（最自信的预测都对）=> 管线没问题；')
print('   但 r_max 全都不到 0.8 => **召回天花板**。天花板从哪来？下面两个实验各给一半答案。')

# ② 注入一个「类别整体 +1」的管线 bug —— p10 立刻塌掉
DT_BUG = {k: v.copy() for k, v in DT.items()}
DT_BUG['cls'] = (DT_BUG['cls'] + 1) % NC
mAP_bug, _ = evaluate(DT_BUG, GT)
s_bug = pr_shape_stats(*class_pr(DT_BUG, GT, 1))
print(f'\\n[bug 版本] 类别整体 +1 后：mAP = {mAP_bug:.4f}, 限速60 的 p10 = {s_bug["p10"]:.2f}')
assert mAP_bug < 0.05 and s_bug['p10'] < 0.80
print('✅ 这就是模块 03 要处理的「mAP 恒为 0」的头号元凶，PR 曲线的左端立刻暴露它。')

# ③ 把 Cls + Loc 两类错误修好，天花板会不会抬起来？
d2, g2 = apply_oracle('Cls', DT, GT, LAB, TGT, MISS)
L2, T2, M2, _, _ = tide_classify(d2, g2)
d3, g3 = apply_oracle('Loc', d2, g2, L2, T2, M2)
mAP_fix, _ = evaluate(d3, g3)
print(f'\\n[修好 Cls+Loc] mAP {mAP0:.3f} -> {mAP_fix:.3f}')
print(f'{"类别":<10s}{"r_max 前":>10s}{"r_max 后":>10s}')
for c in range(NC):
    s = pr_shape_stats(*class_pr(d3, g3, c))
    print(f'{CLASSES[c]:<10s}{base_stats[c]["r_max"]:>10.2f}{s["r_max"]:>10.2f}')
    assert s['r_max'] > base_stats[c]['r_max']
print('\\n👉 关键洞察：**这个「召回天花板」有一大半不是召回问题，是分类问题**——')
print('   目标其实被检出了，只是被判进了别的类。混淆矩阵与 TIDE 分解在这里合流。')"""),

    md("""## 8 · 工作点：给定 FP/frame 预算求 score 阈值

mAP 只用了分数的**排序**（把所有分数开平方 AP 不变），所以它对「阈值该定在哪」毫无帮助。
车端真正的需求是一个**带约束的优化**：

$$\\tau^\\star = \\arg\\max_{\\tau}\\ \\text{Recall}(\\tau) \\quad \\text{s.t.}\\quad \\frac{\\text{FP}(\\tau)}{N_{\\text{frames}}} \\le \\beta$$

因为匹配本来就是按分数降序贪心做的，**按 $\\tau$ 截断 = 取排序后的前缀**，
累计 FP 单调不减 ⇒ 可行集是一个前缀 ⇒ 取最后一个可行位置即最优。$O(n\\log n)$ 解完。

下面对比两种做法：**全局单阈值** vs **按代价分配预算的逐类阈值**（总预算相同）。"""),

    code("""N_FRAMES = N_IMG
STATS = {c: match_class(DT, GT, c)[:2] + (int((GT['cls'] == c).sum()),) for c in range(NC)}


def pick_threshold(sc, tp, n_gt, n_frames, fp_budget_per_frame):
    # 返回 (tau, recall, fp_per_frame)；预算连一个框都放不下时返回 (None, 0, 0)
    if len(sc) == 0 or n_gt == 0:
        return None, 0.0, 0.0
    ctp = np.cumsum(tp.astype(float)); cfp = np.cumsum((~tp).astype(float))
    ok = cfp <= fp_budget_per_frame * n_frames
    if not ok.any():
        return None, 0.0, 0.0
    k = int(np.max(np.where(ok)[0]))                    # 可行集是前缀 -> 取最后一个
    return float(sc[k]), float(ctp[k] / n_gt), float(cfp[k] / n_frames)


TOTAL_BUDGET = 0.35                                     # 全系统 FP / frame

S = np.concatenate([STATS[c][0] for c in range(NC)])
T = np.concatenate([STATS[c][1] for c in range(NC)])
o = np.argsort(-S, kind='stable'); S, T = S[o], T[o]
tau_g, _, _ = pick_threshold(S, T, len(GT['img']), N_FRAMES, TOTAL_BUDGET)

print(f'【方案 A】全局单阈值 tau = {tau_g:.3f}   (总预算 {TOTAL_BUDGET} FP/frame)')
print(f'{"类别":<10s}{"recall":>9s}{"FP/frame":>11s}')
rec_g, fp_g = {}, 0.0
for c in range(NC):
    sc, tp, n_gt = STATS[c]
    m = sc >= tau_g
    rec_g[c] = float(tp[m].sum()) / n_gt
    f = float((~tp[m]).sum()) / N_FRAMES; fp_g += f
    print(f'{CLASSES[c]:<10s}{rec_g[c]:>9.2f}{f:>11.3f}')
print(f'{"合计":<10s}{"":>9s}{fp_g:>11.3f}')
assert fp_g <= TOTAL_BUDGET + 1e-9"""),

    code("""# 【方案 B】按「漏检代价」分配 FP 预算 —— 总预算完全相同
SHARE = np.array([1.0, 1.0, 1.0, 4.0, 2.0, 1.5, 0.8, 0.3])       # 停车让行 4x，指路牌 0.3x
SHARE = SHARE / SHARE.sum()

print(f'【方案 B】逐类阈值（同样的 {TOTAL_BUDGET} FP/frame 总预算，按代价重新分配）')
print(f'{"类别":<10s}{"tau":>8s}{"recall":>9s}{"vs 方案A":>10s}{"FP/frame":>11s}')
rec_p, fp_p, tau_p = {}, 0.0, {}
for c in range(NC):
    sc, tp, n_gt = STATS[c]
    tau, r, f = pick_threshold(sc, tp, n_gt, N_FRAMES, TOTAL_BUDGET * SHARE[c])
    rec_p[c], tau_p[c] = r, tau; fp_p += f
    print(f'{CLASSES[c]:<10s}{tau:>8.3f}{r:>9.2f}{r - rec_g[c]:>+10.2f}{f:>11.3f}')
print(f'{"合计":<10s}{"":>8s}{"":>9s}{"":>10s}{fp_p:>11.3f}')

assert fp_p <= TOTAL_BUDGET + 1e-9, '总预算不能超'
assert tau_p[3] < tau_g, '安全关键类的阈值必须被压低'
assert rec_p[3] > rec_g[3] and rec_p[4] > rec_g[4], '安全关键类召回必须上升'
assert rec_p[7] < rec_g[7], '代价由指路牌承担 —— 天下没有免费的召回'
print(f'\\n👉 停车让行：阈值 {tau_g:.3f} -> {tau_p[3]:.3f}，召回 {rec_g[3]:.2f} -> {rec_p[3]:.2f}')
print(f'   指路牌  ：召回 {rec_g[7]:.2f} -> {rec_p[7]:.2f}（这就是代价，而且是**我们主动选的**代价）')
print('   总 FP 预算没有变。mAP 也没有变（AP 与阈值无关）—— 但产品体验完全不同。')
print('\\n⚠️  这解释了一个常见事故：新模型 mAP 涨了、上车误报却暴增。')
print('   因为换 loss / 加标签平滑会整体平移分数分布，沿用旧阈值等于换了工作点。')
print('   **门禁指标必须是「工作点上的指标」，而且每换一次模型都要重解阈值。**')"""),

    md("""## 9 · badcase 分层抽样：别让限速牌吃掉全部名额

把每个错误（含 Miss 的 GT）打上三个标签：**错误类型 × 像素尺寸 × 类别频次**，
先看看「均匀随机抽 60 张」会抽到什么。"""),

    code("""def size_bucket(box):
    s = max(box[2] - box[0], box[3] - box[1])
    return '<16px' if s < 16 else ('16-32px' if s < 32 else ('32-64px' if s < 64 else '>64px'))


FREQ = np.bincount(GT['cls'], minlength=NC) / len(GT['cls'])
def freq_bucket(c):
    return 'head' if FREQ[c] >= 0.15 else ('mid' if FREQ[c] >= 0.06 else 'tail')


RECORDS = []
for i in range(len(DT['img'])):
    if LAB[i] == 'TP':
        continue
    RECORDS.append(dict(kind='det', idx=i, err=LAB[i], size=size_bucket(DT['box'][i]),
                        freq=freq_bucket(int(DT['cls'][i])), score=float(DT['score'][i])))
for j in np.where(MISS)[0]:
    RECORDS.append(dict(kind='gt', idx=int(j), err='Miss', size=size_bucket(GT['box'][j]),
                        freq=freq_bucket(int(GT['cls'][j])), score=0.0))

STRAT = defaultdict(int)
for r in RECORDS:
    STRAT[(r['err'], r['size'], r['freq'])] += 1
print(f'badcase 池 {len(RECORDS)} 条，分成 {len(STRAT)} 层')

pick = rng.choice(len(RECORDS), 60, replace=False)
u_err = Counter(RECORDS[i]['err'] for i in pick)
print('\\n均匀随机抽 60 条的错误类型分布：', dict(u_err))
print(f'其中 Bkg 占 {u_err["Bkg"] / 60:.0%}；池子里 Bkg 本来就占 '
      f'{sum(r["err"] == "Bkg" for r in RECORDS) / len(RECORDS):.0%}')
print(f'抽到的 tail 类占比 {sum(RECORDS[i]["freq"] == "tail" for i in pick) / 60:.1%}'
      f'，池子里 tail 占 {sum(r["freq"] == "tail" for r in RECORDS) / len(RECORDS):.1%}')
assert u_err['Bkg'] >= 40
print('\\n⚠️  均匀抽样只是把池子的分布复制了一遍 —— 你花两小时看的全是背景误检，')
print('   而上一节刚算出背景误检的 ΔmAP 是最低的。**这不是勤奋度问题，是采样偏差问题。**')"""),

    code("""def largest_remainder(weights, total, caps):
    # 按 weights 比例把 total 个名额分给各层，受 caps 上限约束，用最大余数法保证总和精确
    keys = list(weights)
    w = np.array([weights[k] for k in keys], float)
    cap = np.array([caps[k] for k in keys], int)
    alloc = np.zeros(len(keys), int)
    remain = int(total)
    active = alloc < cap
    while remain > 0 and active.any():
        ww = np.where(active, w, 0.0)
        if ww.sum() <= 0:
            break
        raw = remain * ww / ww.sum()
        add = np.minimum(np.floor(raw).astype(int), cap - alloc)
        alloc += add; remain -= int(add.sum())
        if add.sum() == 0:                                  # 都不足 1 个 -> 按小数部分补
            for t in np.argsort(-(raw - np.floor(raw))):
                if remain <= 0:
                    break
                if active[t] and alloc[t] < cap[t]:
                    alloc[t] += 1; remain -= 1
        active = alloc < cap
    return {k: int(a) for k, a in zip(keys, alloc)}


def sqrt_allocate(sizes, n_total, n_min=1):
    # 平方根配额：n_h ∝ sqrt(N_h)，且每个非空层至少 n_min 个
    base = {k: min(n_min, v) for k, v in sizes.items()}
    used = sum(base.values())
    assert used <= n_total, '名额太少，连每层下限都凑不齐'
    caps = {k: sizes[k] - base[k] for k in sizes}
    extra = largest_remainder({k: float(np.sqrt(sizes[k])) for k in sizes}, n_total - used, caps)
    return {k: base[k] + extra[k] for k in sizes}


N_REVIEW = 120
A_sqrt = sqrt_allocate(dict(STRAT), N_REVIEW, n_min=1)
A_prop = largest_remainder({k: float(v) for k, v in STRAT.items()}, N_REVIEW, dict(STRAT))
assert sum(A_sqrt.values()) == N_REVIEW and sum(A_prop.values()) == N_REVIEW

big = sorted(STRAT, key=lambda k: -STRAT[k])[:4]
small = sorted(STRAT, key=lambda k: STRAT[k])[:4]
print(f'{"层":<34s}{"层大小":>8s}{"比例分配":>9s}{"平方根":>8s}')
for k in big + small:
    print(f'{str(k):<34s}{STRAT[k]:>8d}{A_prop[k]:>9d}{A_sqrt[k]:>8d}')

cov_p = np.mean([A_prop[k] >= 1 for k in STRAT])
cov_s = np.mean([A_sqrt[k] >= 1 for k in STRAT])
share_p = sum(v for k, v in A_prop.items() if k[0] == 'Bkg') / N_REVIEW
share_s = sum(v for k, v in A_sqrt.items() if k[0] == 'Bkg') / N_REVIEW
print(f'\\n非空层被覆盖到的比例：比例分配 {cov_p:.0%}  ->  平方根+下限 {cov_s:.0%}')
print(f'Bkg 吃掉的名额比例  ：比例分配 {share_p:.0%}  ->  平方根+下限 {share_s:.0%}')
assert cov_s == 1.0 and cov_p < 0.5
assert share_s < share_p
print('\\n👉 平方根压缩了层间规模差（10000 vs 100 的差距从 100 倍压到 10 倍），')
print('   再加「每层至少 1 个」的下限，就能保证**尾部类和 <16px 的层一定会被你看到**。')
print('   练习 4 会把「修复收益」也加进权重 —— 直接按 ΔmAP 分配眼睛的时间。')"""),

    md("""## 10 · 根因决策树的代码化

把前面所有信号接进一棵树。**设计原则：先排除便宜的可能性**——
查一次类别映射 10 分钟，训一次模型 10 小时。"""),

    code("""def root_cause(m):
    # m: {'mAP', 'p10', 'gains'} -> (根因, 下一步动作, 判定依据)
    if m['mAP'] < 0.05:
        return ('管线 bug：类别 ID 偏移 / 坐标格式 / 类别表不一致',
                '转模块 03：把预测类别整体 ±1 重算 mAP；把框按 cxcywh→xyxy 转换重算 IoU 分布',
                'mAP ≈ 0')
    if m['p10'] < 0.80:
        return ('数据管线 bug：通道顺序 / 归一化 / 验证集预处理与训练不一致',
                'dump 一个 batch 的输入张量，与训练端逐元素对拍；对比 R/B 通道均值',
                'PR 曲线低召回段 precision < 0.8（最自信的预测就在错）')
    if not m['gains']:
        return ('信息不足', '先跑 TIDE 分解', '没有 ΔAP')
    top = max(m['gains'], key=lambda k: m['gains'][k])
    table = {
        'Miss': ('召回侧问题', '按像素尺寸分桶重画 PR：小目标桶趴着→C57（分辨率/P2/切片）；某类趴着→C58（长尾）'),
        'Cls':  ('分类侧问题', '看混淆矩阵找冤家对：集中在 2-3 对→两级架构 + 高分辨率 crop；弥散→类别定义有歧义'),
        'Loc':  ('定位侧问题', '看 Loc 错误的尺寸分布：集中在小目标→换尺度不敏感度量（NWD）；均匀→换 GIoU/DIoU'),
        'Both': ('定位侧问题（连锁）', '先治 Loc，Both 通常跟着降'),
        'Dupe': ('后处理问题', '查 NMS 阈值 / class-wise vs class-agnostic / 一对一分配'),
        'Bkg':  ('难负样本问题', 'OHEM / Focal Loss / 加上下文 / 提高工作点阈值'),
    }
    cause, action = table[top]
    return (cause, action, f'{top} 的 ΔAP 最大（{m["gains"][top] * 100:+.2f} pp）')


CASES = [
    ('刚接手的新代码库', dict(mAP=0.001, p10=0.00, gains={})),
    ('换了数据加载器之后', dict(mAP=0.44, p10=0.42, gains={'Cls': 0.01, 'Miss': 0.02})),
    ('本 notebook 的模型', dict(mAP=mAP0, p10=1.00, gains=GAINS)),
    ('小目标专项版本', dict(mAP=0.55, p10=0.97, gains={'Miss': 0.09, 'Cls': 0.02, 'Loc': 0.03})),
    ('NMS 阈值调错了', dict(mAP=0.61, p10=0.96, gains={'Dupe': 0.07, 'Cls': 0.02, 'Bkg': 0.01})),
]
for name, m in CASES:
    cause, action, why = root_cause(m)
    print(f'[{name}]\\n  根因: {cause}\\n  依据: {why}\\n  动作: {action}\\n')

assert root_cause(CASES[0][1])[0].startswith('管线 bug')
assert '通道顺序' in root_cause(CASES[1][1])[0]
assert root_cause(CASES[3][1])[0] == '召回侧问题'
assert root_cause(CASES[4][1])[0] == '后处理问题'
print('✅ 决策树就位。注意前两条 (mAP≈0 / p10<0.8) 都在 30 分钟内可查完，')
print('   却拦下了最浪费时间的一整类问题 —— 「训了三天发现是类别 ID 差 1」。')"""),

    md("""## ✏️ 练习 1：TIDE 判定树

实现 `classify_fp(u_same, u_other, tf=0.5, tb=0.1)`，输入一个**非 TP** 检测的
「与同类 GT 的最大 IoU」和「与异类 GT 的最大 IoU」，返回
`'Dupe' / 'Loc' / 'Cls' / 'Both' / 'Bkg'` 之一。

**判定顺序不能变**：同类优先于异类，高 IoU 优先于低 IoU。"""),

    code("""def classify_fp(u_same, u_other, tf=0.5, tb=0.1):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert classify_fp(0.70, 0.00) == 'Dupe'      # 同类 IoU 够，说明 GT 被更高分的框占了
assert classify_fp(0.50, 0.00) == 'Dupe'      # 边界：>= tf
assert classify_fp(0.30, 0.00) == 'Loc'
assert classify_fp(0.10, 0.00) == 'Loc'       # 边界：>= tb
assert classify_fp(0.05, 0.80) == 'Cls'
assert classify_fp(0.05, 0.30) == 'Both'
assert classify_fp(0.02, 0.03) == 'Bkg'
assert classify_fp(0.30, 0.95) == 'Loc', '同类优先：不能因为异类 IoU 更高就判 Cls'
assert classify_fp(0.55, 0.95) == 'Dupe'
# 与完整实现对拍：所有非 TP 检测都必须一致
bad = [i for i in range(len(LAB))
       if LAB[i] != 'TP' and classify_fp(U_SAME[i], U_OTHER[i]) != LAB[i]]
assert not bad, bad[:5]
print(f'✅ 练习 1 通过：{sum(LAB != "TP")} 个非 TP 检测的判定与完整实现逐条一致。')"""),

    md("""## ✏️ 练习 2：按性价比排序修复动作

实现 `rank_actions(counts, gains, costs)`：
- `counts[e]` 该类错误的个数，`gains[e]` 该类的 ΔmAP（小数，如 0.0875），`costs[e]` 估计工程成本（人天）
- 返回 `[(err, gain_pp, per100_pp, roi), ...]`，**按 `roi` 降序**
- `gain_pp = gains[e]*100`（百分点）；`per100_pp = gain_pp / max(counts[e],1) * 100`；`roi = gain_pp / costs[e]`"""),

    code("""def rank_actions(counts, gains, costs):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（手算）——
c0 = {'A': 200, 'B': 10}
g0 = {'A': 0.10, 'B': 0.02}
k0 = {'A': 5.0, 'B': 0.5}
out = rank_actions(c0, g0, k0)
assert [r[0] for r in out] == ['B', 'A'], out          # roi: B=2.0/0.5=4.0 > A=10/5=2.0
assert abs(out[0][1] - 2.0) < 1e-9 and abs(out[0][2] - 20.0) < 1e-9 and abs(out[0][3] - 4.0) < 1e-9
assert abs(out[1][1] - 10.0) < 1e-9 and abs(out[1][2] - 5.0) < 1e-9 and abs(out[1][3] - 2.0) < 1e-9
# 用真实分解结果排序
real = rank_actions(CNT, GAINS, COST)
print(f'{"排名":<5s}{"类型":<7s}{"ΔmAP(pp)":>10s}{"每100个(pp)":>13s}{"ROI":>8s}')
for r, (e, gp, p100, roi) in enumerate(real, 1):
    print(f'{r:<5d}{e:<7s}{gp:>10.2f}{p100:>13.3f}{roi:>8.3f}')
assert real[0][0] == 'Cls', 'ROI 第一名应该是分类错误'
assert real[-1][0] in ('Both', 'Miss'), '成本最高/收益最低的排最后'
print('\\n✅ 练习 2 通过：ΔmAP 第一名与 ROI 第一名不一定是同一个 —— 决策要用后者。')"""),

    md("""## ✏️ 练习 3：PR 曲线诊断器

实现 `diagnose_pr(rec, prec, p_low=0.80, r_low=0.75, p_tail=0.30)`，返回
`'DATA_BUG' / 'RECALL_CEILING' / 'TAIL_COLLAPSE' / 'HEALTHY'` 之一。

**判定顺序**（先排除最便宜的可能性）：
1. `p10 < p_low` → `DATA_BUG`（最自信的预测就在错，先查管线）
2. `r_max < r_low` → `RECALL_CEILING`
3. `p50 > 0.90` 且 `p85 < p_tail` → `TAIL_COLLAPSE`
4. 否则 `HEALTHY`

可以直接复用上面的 `pr_shape_stats`。"""),

    code("""def diagnose_pr(rec, prec, p_low=0.80, r_low=0.75, p_tail=0.30):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
for k in ['HEALTHY', 'TAIL_COLLAPSE', 'DATA_BUG', 'RECALL_CEILING']:
    got = diagnose_pr(*make_curve(k))
    assert got == k, (k, got)
# 真实模型：baseline 是召回天花板，修好 Cls+Loc 之后变健康
d_base = diagnose_pr(*class_pr(DT, GT, 0))
d_fix = diagnose_pr(*class_pr(d3, g3, 0))
d_bug = diagnose_pr(*class_pr(DT_BUG, GT, 1))
print(f'限速30 baseline      -> {d_base}')
print(f'限速30 修好 Cls+Loc  -> {d_fix}')
print(f'限速60 类别整体 +1   -> {d_bug}')
assert d_base == 'RECALL_CEILING' and d_fix == 'HEALTHY' and d_bug == 'DATA_BUG'
# 空曲线（模型对该类一个框都没输出）也不能崩
assert diagnose_pr(np.zeros(0), np.zeros(0)) == 'DATA_BUG'
print('\\n✅ 练习 3 通过：曲线形状 -> 病因，全程没有「看图感觉」这一步。')"""),

    md("""## ✏️ 练习 4：按修复收益加权的分层配额

`sqrt_allocate` 已经保证了每层都被看到，但它仍然把 57% 的名额给了 ΔmAP 最低的 Bkg。
把**修复收益**也放进权重：

$$w_h = \\sqrt{N_h}\\;\\cdot\\;\\max\\bigl(\\Delta\\text{AP}_{\\text{err}(h)},\\ \\varepsilon\\bigr)$$

实现 `gain_weighted_allocate(sizes, err_gain, n_total, n_min=1, eps=1e-4)`：
- `sizes[(err, size, freq)] = N_h`，`err_gain[err] = ΔmAP`（小数）
- 每个非空层仍至少 `n_min` 个；总和精确等于 `n_total`
- 直接复用上面写好的 `largest_remainder`"""),

    code("""def gain_weighted_allocate(sizes, err_gain, n_total, n_min=1, eps=1e-4):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
A_gw = gain_weighted_allocate(dict(STRAT), GAINS, N_REVIEW, n_min=1)
assert sum(A_gw.values()) == N_REVIEW
assert all(A_gw[k] >= 1 for k in STRAT), '每个非空层至少 1 个'
assert all(A_gw[k] <= STRAT[k] for k in STRAT), '不能超过该层实际样本数'

def err_share(alloc):
    d = defaultdict(int)
    for k, v in alloc.items():
        d[k[0]] += v
    return {e: d[e] / N_REVIEW for e in ERR_TYPES}

sh_p, sh_s, sh_g = err_share(A_prop), err_share(A_sqrt), err_share(A_gw)
print(f'{"错误类型":<8s}{"ΔmAP(pp)":>10s}{"比例分配":>10s}{"平方根":>9s}{"收益加权":>10s}')
for e in ERR_TYPES:
    print(f'{e:<8s}{GAINS[e] * 100:>+10.2f}{sh_p[e]:>10.0%}{sh_s[e]:>9.0%}{sh_g[e]:>10.0%}')
assert sh_g['Bkg'] < sh_s['Bkg'] < sh_p['Bkg'], 'Bkg 的名额应被一路压下去'
assert sh_g['Cls'] > sh_s['Cls'] and sh_g['Loc'] > sh_s['Loc']
print('\\n✅ 练习 4 通过：眼睛的时间也是预算，应该按 ΔmAP 分配，而不是按错误数量分配。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def classify_fp(u_same, u_other, tf=0.5, tb=0.1):
    if u_same >= tf:
        return 'Dupe'
    if u_same >= tb:
        return 'Loc'
    if u_other >= tf:
        return 'Cls'
    if u_other >= tb:
        return 'Both'
    return 'Bkg'"""),

    code("""# 练习 2 参考答案
def rank_actions(counts, gains, costs):
    out = []
    for e in gains:
        gp = gains[e] * 100.0
        out.append((e, gp, gp / max(counts.get(e, 0), 1) * 100.0, gp / costs[e]))
    out.sort(key=lambda r: -r[3])
    return out"""),

    code("""# 练习 3 参考答案
def diagnose_pr(rec, prec, p_low=0.80, r_low=0.75, p_tail=0.30):
    s = pr_shape_stats(rec, prec)
    if s['p10'] < p_low:
        return 'DATA_BUG'
    if s['r_max'] < r_low:
        return 'RECALL_CEILING'
    if s['p50'] > 0.90 and s['p85'] < p_tail:
        return 'TAIL_COLLAPSE'
    return 'HEALTHY'"""),

    code("""# 练习 4 参考答案
def gain_weighted_allocate(sizes, err_gain, n_total, n_min=1, eps=1e-4):
    base = {k: min(n_min, v) for k, v in sizes.items()}
    used = sum(base.values())
    assert used <= n_total, '名额太少，连每层下限都凑不齐'
    caps = {k: sizes[k] - base[k] for k in sizes}
    w = {k: float(np.sqrt(sizes[k])) * max(err_gain.get(k[0], 0.0), eps) for k in sizes}
    extra = largest_remainder(w, n_total - used, caps)
    return {k: base[k] + extra[k] for k in sizes}"""),

    md("""---
## 🧪 真实工程胶囊：误差分析 SOP（可原样贴进团队 wiki）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 检测模型误差分析 SOP —— 每训完一版就跑一遍，30 分钟出结论
# ══════════════════════════════════════════════════════════════════════

# ── 阶段 0：先证伪「管线错了」（10 分钟，永远第一步）────────────────────
#  0.1  mAP < 0.05 ?  -> 不要做误差分析，直接查三大元凶（模块 03）
#         · 预测类别整体 ±1 重算 mAP        （类别 ID 偏移 / background 占了 index 0）
#         · 框按 cxcywh->xyxy 转换重算 IoU  （坐标格式弄反）
#         · diff 训练与评测的 classes.txt   （类别表不一致）
#  0.2  PR 曲线 p(r=0.1) < 0.8 ?  -> 数据管线 bug，dump 输入张量对拍
#  通过条件：p10 >= 0.9 且 mAP 在合理量级，才允许进入阶段 1

# ── 阶段 1：TIDE 六类分解 + 修复收益（15 分钟）──────────────────────────
#  pip install tidecv     # 官方实现只有几百行，建议读一遍
#  from tidecv import TIDE, datasets
#  tide = TIDE(); tide.evaluate(datasets.COCO(gt_json), datasets.COCOResult(dt_json), mode=TIDE.BOX)
#  tide.summarize(); tide.plot()
#  产出必须包含三列：**数量 / ΔmAP / 每 100 个错误的 ΔmAP**
#  ⚠️ 只看数量必然被 Bkg 带偏（本 notebook 里 Bkg 占 87% 的数量、ΔmAP 却排倒数）
#  ⚠️ 六项 ΔAP **不可加**，别写成「Cls 贡献了 34.7% 的损失」

# ── 阶段 2：逐类 + 混淆矩阵（10 分钟）──────────────────────────────────
#  · 混淆矩阵必须是 (C+1)x(C+1)：最后一行=背景误检，最后一列=未检出
#  · 混淆矩阵**必须标注 score 阈值**，否则不可复现
#  · 逐类表三列并排：AP / GT 数 / 多种子 AP 标准差   <- 第三列防止追逐噪声
#  · 输出「最容易互相错分的 Top-5 标志对」，直接进下个迭代的 backlog

# ── 阶段 3：工作点（10 分钟）────────────────────────────────────────────
#  · 报 **Recall @ FP/frame <= beta**，不要报 precision（precision 随目标密度漂移）
#  · 逐类阈值，按漏检代价分配 FP 预算；安全关键类（停车让行/让行）单独设更低阈值
#  · **每换一次模型都要重解阈值** —— 换 loss / 加标签平滑会整体平移分数分布
#  · 单帧阈值要按「多帧确认后的 FP 预算」反推（C55 m04），否则会定得过高

# ── 阶段 4：badcase 分层抽样（人工，1-2 小时）──────────────────────────
#  分层维度 = 错误类型 x 像素尺寸(<16/16-32/32-64/>64) x 类别频次(head/mid/tail)
#  配额 = sqrt(N_h) * ΔmAP(该错误类型)，且每个非空层至少 1 个，最大余数法保证总和
#  ⚠️ 均匀随机抽样 = 把池子分布复制一遍，你会看到 90% 的背景误检
#  ⚠️ review 时必须同屏显示 GT + 预测 + 分数；10-20% 的 badcase 是**标注错误**
#      -> 界面上放一个「这是标注问题」按钮，直接回流标注团队（C58 数据闭环）
#  ⚠️ 固定一份「回归可视化集」（固定图像 ID）做版本对比 +
#      一份每次重抽的「探索集」发现新问题

# ── 阶段 5：产出物（写进实验记录，模块 01 的 schema）────────────────────
#  1. TIDE 表（数量 / ΔmAP / per-100）+ 一句话结论「下一步做 X，收益上界 +Y mAP」
#  2. 逐类表 + Top-5 混淆对
#  3. 工作点表（每类 tau / recall / FP-per-frame）
#  4. 分层 badcase 抽样清单（含 stratum id，可复现）
#  5. 本版与上一版的**同一批固定图像**的对比图
'''
print(RECIPE)
for tok in ['tidecv', '(C+1)x(C+1)', 'Recall @ FP/frame', 'sqrt(N_h)',
            '不可加', '标注错误', '重解阈值']:
    assert tok in RECIPE, tok
print('✅ SOP 覆盖：证伪管线 / 六类分解 / 逐类与混淆 / 工作点 / 分层抽样 / 产出物')"""),

    md("""### 小结

- **mAP 只说「有多差」，不说「差在哪」**。它把六种失败压成一个标量，而这个聚合是不可逆的。
  拿到 0.60 之后你必须回到原始的匹配结果重新分桶。
- **TIDE 六类靠一棵固定的判定树定义**（同类优先、高 IoU 优先），
  分类本身不重要，重要的是**六类各对应一条不同的修复路径**。
  阈值 $t_f=0.5$、$t_b=0.1$ 与判定顺序必须写进评测配置并版本化。
- **数量最多的错误几乎从不是最值钱的**。本 notebook 里 Bkg 占错误数的 87%，
  ΔmAP 却只有 +3.05 pp（每 100 个错误 0.22 pp）；Cls 只占 2.7%，ΔmAP 却有 +8.75 pp
  （每 100 个 20.3 pp）。**原因在 AP 的定义里：FP 的杀伤力取决于它排在第几名。**
- **ΔAP 不可加**（排序/包络/求面积三重非线性），六项之和 29.7 pp ≠ 总差距 39.8 pp。
  面试里把 ΔAP 说成「可加的贡献占比」是最容易被一句话戳穿的错。
- **混淆矩阵必须是 $(C{+}1)\\times(C{+}1)$**，最后一行一列信息量最大；
  而「召回天花板」经常根本不是召回问题 —— 本 notebook 里修好 Cls+Loc 之后
  各类 $r_{\\max}$ 从 0.6–0.75 升到 0.8–0.92。
- **PR 曲线左端诊断「规则」，右端诊断「难度」，中段诊断「能力」。**
  $p(r{=}0.1) < 0.8$ 几乎必然是数据管线 bug —— 别调参，去查管线。
- **mAP 与阈值无关，产品与阈值强相关。** 门禁指标要用「固定 FP/frame 预算下的召回」，
  而且逐类设阈值：停车让行阈值 0.70→0.47，召回 0.54→0.65，代价由指路牌承担。
- **badcase 要分层抽样**：均匀随机抽 60 条会抽到 55 条背景误检。
  配额用 $\\sqrt{N_h}\\cdot\\Delta\\text{AP}$ + 每层下限 + 最大余数法。
- **决策树的第一原则：先排除便宜的可能性。** 查类别映射 10 分钟，训模型 10 小时。

下一站：**模块 03 · 训练与部署调试手册** —— 当阶段 0 亮红灯时，具体怎么查。"""),
]
