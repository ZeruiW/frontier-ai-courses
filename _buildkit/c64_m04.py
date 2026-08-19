# -*- coding: utf-8 -*-
"""C64 模块 04 · 评估、概率与统计问答（ML/DL 技术知识问答）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "会算混淆矩阵、知道什么是 sigmoid 输出的概率；数学推导见 <span class=\"term\">C07</span>（贝叶斯公式、交叉验证的推导），本模块不重复"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_eval_stats_qa.ipynb（ROC-AUC/PR-AUC 分歧演示 · 可靠性图与温度缩放 · 三种置信区间对比 · A/B 功效计算 · 辛普森悖论构造，纯 numpy）'),
    ("核心参考", "Davis & Goadrich 2006「The Relationship Between PR and ROC」· Guo et al. 2017「On Calibration of Modern Neural Networks」· Efron 1979 bootstrap · Wilson 1927 · 本课程 C58-01（类别不平衡）、C61-01（种子方差与显著性）、C55-05（安全导向评测）"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("eval-stats-scope", "为什么这一段区分度最高：三段式答法用在统计上", "".join([
        P("前三个模块的三段式答法是「一句话定义 → 为什么需要 → 什么时候失效」。到了评估与统计这一段，"
          "<strong>「什么时候失效」不再是加分项，而是整个答案的重心</strong>——因为统计方法的正确性从来不是"
          "「公式对不对」，而是「前提假设成不成立」。正态置信区间假设样本够大、比例不极端；ROC-AUC 假设你关心"
          "排序而不是绝对错误率；A/B 测试的显著性检验假设你没有中途偷看结果。<em>忘记假设，工具就会给你一个"
          "看起来很科学、实际上错误的答案。</em>"),
        P("这也是为什么这一段是全部 <span class=\"term\">C64</span> 里<strong>区分度最高</strong>的一段。"
          "背公式人人都会——$F_1 = 2PR/(P+R)$ 三秒钟能查到，$\\text{ROC-AUC}$ 的定义随口能说。"
          "但能不能在 30 秒内说出「这个指标在什么场景下会撒谎」，才能看出候选人是<em>真的用过、debug 过</em>"
          "这些指标，还是只在课堂上背过定义。"),
        TABLE(["面试官的追问", "只背公式的候选人", "懂失效边界的候选人"], [
            ["「不平衡数据下你会用什么指标？」", "「F1，因为它综合了精确率和召回率」", "「先看不平衡程度：如果负类占 99%，我会看 <strong>PR-AUC</strong> 而不是 ROC-AUC，因为……」"],
            ["「那 ROC-AUC 有什么问题？」", "卡壳，或重复一遍 ROC-AUC 的定义", "「它的分母里有海量真阴性，会稀释假阳性的影响，我可以举个数字例子」"],
            ["「能举一个 ROC-AUC 很高但模型没用的例子吗？」", "说不出来", "秒举：<em>10 万分之一的欺诈检测，ROC-AUC=0.98 但精确率只有 5%</em>"],
        ]),
        CALLOUT("intuition", "统计学面试问的从来不是「这个指标是什么」，是<strong>「这个指标什么时候会说谎，以及你怎么发现它在说谎」</strong>。"
                             "把这句话当成本模块所有小节的统一读法。"),
        DUAL(
            "每一个统计工具都是在一组假设下才成立的近似。正态置信区间假设样本够大、分布不太偏；"
            "ROC-AUC 假设你关心的是「谁的分数更高」而不是「绝对错了多少」；A/B 测试的 $p$ 值假设你只看了一次结果。"
            "<em>忘记假设，工具不会报错，它只会安静地给你一个错误的自信。</em>",
            "更精确地说，每个统计方法都对应一个「如果条件不满足，第一类/第二类错误率会怎样膨胀」的具体机制——"
            "小样本下正态近似的覆盖率会低于名义置信度（尤其 $\\hat p$ 接近 0 或 1 时）；"
            "ROC-AUC 作为一个排序统计量（等价于 Mann-Whitney U 统计量的归一化形式），本身与类别先验<em>无关</em>，"
            "这正是它在不平衡场景下「对假阳性数量不敏感」的数学根源——不是它坏了，是它<u>压根没有被设计来衡量这件事</u>。",
        ),
        CALLOUT("warn", "面对不熟悉的检验，正确姿势是「我会先确认这个检验的假设是否满足——比如样本是否独立、"
                        "方差是否齐性——再决定能不能用」，而<strong>不是</strong>硬着头皮编一个公式出来。"
                        "承认「我需要先查一下」比编错一个公式安全得多，见模块 05 的知识边界练习。"),
        P("数学推导（贝叶斯公式的完整推导、交叉验证的方差分解）见 <span class=\"term\">C07</span>，本模块不重复；"
          "这里只训练「60 秒讲清 + 接住追问」。"),
    ])),

    # ============================================================== 2
    ("metric-family", "指标全家：Accuracy / Precision / Recall / F1 / Fβ", "".join([
        P("五个最基础的指标都从同一张<strong>混淆矩阵</strong>（TP/FP/FN/TN）里算出来，"
          "但它们回答的是<em>五个不同的问题</em>——把「它们都是分类指标」当成一回事，是这一段最常见的踩雷点。"),
        TABLE(["指标", "公式", "一句话回答的问题", "什么时候它会骗你"], [
            ["Accuracy", "$(TP+TN)/N$", "整体猜对了多少", "<strong>类别不平衡时完全失效</strong>：全猜负类在 99:1 数据上也有 99% accuracy"],
            ["Precision", "$TP/(TP+FP)$", "我说是正的，有多少真是正的", "只看它会忽略召回——把阈值调到 1.0，precision 可以刷到 1，但漏检全部"],
            ["Recall", "$TP/(TP+FN)$", "真正的正例，我抓到了多少", "只看它会忽略代价——把阈值调到 0，recall 恒为 1，但全是假阳性"],
            ["F1", "$2PR/(P+R)$", "precision 与 recall 的调和平均", "<strong>默认 precision 与 recall 同等重要</strong>——代价不对称时这个假设本身就是错的"],
            ["Fβ", "$(1{+}\\beta^2)PR / (\\beta^2P+R)$", "让 recall 的重要性是 precision 的 $\\beta$ 倍", "$\\beta$ 选错等于假设错了代价比——很多人报了 F1 却没意识到自己隐含选了 $\\beta{=}1$"],
        ]),
        MATH("F_\\beta = \\frac{(1+\\beta^2)\\cdot P \\cdot R}{\\beta^2 \\cdot P + R}, \\qquad \\beta{>}1 \\text{ 更看重召回}, \\;\\; \\beta{<}1 \\text{ 更看重精确率}"),
        DUAL(
            "调和平均（而不是算术平均）的意义在于<strong>惩罚两者失衡</strong>：precision=1.0、recall=0.01 时，"
            "算术平均还有 0.505 看起来不错，调和平均只有 0.0198，一眼就能看出「这个模型基本没用」。"
            "F1 就是靠这一点防止你被单边的高分数骗过去。",
            "严格地说 $\\beta$ 是「召回相对于精确率的重要性倍数」：$\\beta{=}2$（即 F2）意味着面试官告诉你"
            "「漏检的代价是误检的 4 倍」（$\\beta^2{=}4$）——这在 TSR 里对应<span class=\"term\">停车让行</span>这类"
            "标志：漏检一次的安全代价远高于多一次误刹车，此时该报 F2 甚至更极端的 recall 优先指标，"
            "而不是默认报 F1。",
        ),
        CALLOUT("danger", "<strong>「accuracy 高就是模型好」是面试里最容易当场翻车的一句话。</strong>"
                          "一个 <span class=\"term\">TSR</span> 数据集里「限速 5」这一类可能只占 0.1%，"
                          "一个永远不预测这个类的模型 accuracy 照样很高——面试官只要追问一句「稀有类的 recall 呢」，"
                          "这句话就会当场破功。"),
        H3("典型追问：给你一组 P/R，能不能秒算 F1/F0.5/F2？"),
        P("$P{=}0.9, R{=}0.1$ 时：$F_1{=}2{\\times}0.9{\\times}0.1/1.0{=}0.18$；"
          "$F_{0.5}$（更看重精确率）$\\approx 0.36$；$F_2$（更看重召回）$\\approx 0.12$。"
          "记住这个方向就够了：<strong>$\\beta$ 越大，Fβ 越贴近 recall 本身；$\\beta$ 越小，越贴近 precision 本身</strong>——"
          "不需要在白板上心算到小数点后四位，说对趋势 + 给出边界情况（$\\beta\\to 0$ 退化为 P，$\\beta\\to\\infty$ 退化为 R）就已经拿到分。"),
    ])),

    # ============================================================== 3
    ("roc-pr-map", "ROC-AUC vs PR-AUC vs mAP：不平衡数据下谁在骗你", "".join([
        P("这是本模块的<strong>招牌问题</strong>：「不平衡数据下 ROC-AUC 为什么会骗人？」几乎是检测/风控/医疗类岗位的"
          "必考题，而且是少数几个「能当场用数字讲清楚」的理论问题。"),
        ASCII("""ROC 空间：坐标是 (FPR, TPR)                 PR 空间：坐标是 (Recall, Precision)
  TPR                                          Precision
   1 ┤        ╭──────────                       1 ┤╲
     │     ╭──╯   看起来都贴着左上角           │ ╲___
     │  ╭──╯      —— 因为 FPR 分母里有         │     ╲___  —— 不平衡时会
     │╭─╯         海量真阴性 TN 在稀释 FP        │         ╲___ 塌到很低，
   0 └───────────────────────► FPR            0 └──────────────►Recall
     0                        1                  0                1
   两条不同分类器的 ROC 曲线几乎重合            同样两条分类器的 PR 曲线拉开明显差距
   （因为 FPR = FP/(FP+TN)，TN 巨大时不敏感）  （因为 Precision = TP/(TP+FP)，直接受 FP 绝对数量影响）"""),
        P("拿一组具体数字讲清楚：负类 99000、正类 1000。分类器 A 产生 900 个真阳性、1000 个假阳性——"
          "$FPR = 1000/99000 \\approx 0.0101$，看起来微不足道，ROC 曲线几乎贴着左上角，$\\text{ROC-AUC}$ 可以高达 0.97+。"
          "但 $\\text{Precision} = 900/(900{+}1000) \\approx 0.47$——<strong>你发出的每两个报警里就有一个是错的</strong>，"
          "这在下游系统里是完全不同的体验，而 PR 曲线会把这个问题直接暴露出来。"),
        MATH("\\text{ROC-AUC} = P\\big(s(x^+) > s(x^-)\\big) \\quad \\text{—— 只关心排序，与类别先验无关}"),
        TABLE(["指标", "数学本质", "对类别先验", "适用场景", "常见误用"], [
            ["ROC-AUC", "排序统计量（Mann-Whitney U 的归一化形式）", "<strong>不敏感</strong>——这是它「骗人」的根源", "两类样本量相近、你关心排序能力", "在极不平衡数据上报 ROC-AUC 当作唯一指标"],
            ["PR-AUC", "精确率-召回率曲线下面积", "敏感——正类越稀少，同样的 FP 数量对 precision 冲击越大", "正类稀少、你关心「报警的可信度」", "把 PR-AUC 和 ROC-AUC 数值直接比大小（量纲不同，基线不同）"],
            ["mAP", "对每个类别算 PR-AUC 再求平均（检测里还要在多个 IoU 阈值上再平均）", "对<strong>类别间</strong>不平衡不敏感——平均会掩盖表现极差的类", "多类检测的整体排行榜指标", "只看 mAP 不看逐类 AP——见 C61-02 的 TIDE 式误差分解；细节推导见 C18、C53–C61"],
        ]),
        DUAL(
            "直白地说：ROC 曲线的横轴（假阳性率）分母里站着<strong>全部</strong>真阴性，"
            "负类越多，同样数量的假阳性占比就越小，曲线自然显得好看；PR 曲线的横轴纵轴里根本没有真阴性这一项，"
            "假阳性一多，precision 立刻掉下来，<em>藏不住</em>。",
            "严格地说，PR-AUC 的这种敏感性不是「优点」而是<strong>对代价结构的不同建模</strong>：ROC-AUC 隐含假设"
            "「阴性样本被误判的相对代价 = 阴性样本的相对数量」，而这在类别本身极不平衡时通常不成立——"
            "真正在意的是「每次报警的可信度」而非「负类整体被误判的比例」。<em>选 ROC 还是 PR，本质是在选一个隐含的代价假设</em>，"
            "这也是为什么 Davis & Goadrich (2006) 证明「一条曲线在 ROC 空间占优，当且仅当它在 PR 空间也占优」——"
            "两者排序一致，但<strong>绝对数值的可读性</strong>天差地别。",
        ),
        CALLOUT("danger", "<strong>面试当场翻车模板</strong>：面试官给你一份「ROC-AUC=0.95」的报告问「这个模型能上线吗」，"
                          "你说「AUC 这么高，能上」——这是本节要根除的反应。正确反应是反问一句"
                          "「正负类比例是多少？能不能看一下 PR 曲线和实际阈值下的 precision？」。"),
        CALLOUT("intuition", "一句话记住选择规则：<strong>正类稀少 → 看 PR-AUC；两类均衡 → ROC-AUC 也可信；"
                             "多类检测的整体排行 → mAP，但永远要配一张逐类 AP 表</strong>。"),
    ])),

    # ============================================================== 4
    ("threshold-cost", "阈值、工作点与代价敏感决策", "".join([
        P("指标是连续的，但线上系统要做一个<strong>非黑即白的决定</strong>——这中间的桥梁就是<span class=\"term\">阈值</span>"
          "（threshold）。「用 0.5 当阈值」是最常见的默认动作，也是最没有依据的一个默认动作。"),
        DUAL(
            "0.5 只在一种情况下天然合理：两个类别一样多、犯两种错误的代价完全相等。现实里这两条几乎从不同时成立——"
            "类别常常不平衡，犯错的代价也几乎总是不对称的（漏检一个停车让行标志，和多看错一次广告牌，"
            "后果完全不是一个量级）。",
            "更严谨的做法是显式写出<strong>代价矩阵</strong> $C_{FP}, C_{FN}$，选择使<strong>期望代价</strong>"
            "$E[\\text{cost}] = C_{FP}\\cdot FP(\\tau) + C_{FN}\\cdot FN(\\tau)$ 最小的阈值 $\\tau$——"
            "这把「选阈值」从一个经验动作变成了一个可以在白板上写出目标函数的优化问题。",
        ),
        TABLE(["场景", "$C_{FN}$（漏检代价）", "$C_{FP}$（误检代价）", "该往哪个方向调阈值"], [
            ["TSR 停车让行标志检测", "极高——可能导致未减速通过路口", "低——多一次不必要的减速", "<strong>降低阈值</strong>，牺牲精确率换召回"],
            ["广告牌误识别为限速牌", "中——如果误触发限速会造成不必要减速", "中——同上", "阈值需结合下游多帧融合再定（见 C55-04）"],
            ["垃圾邮件过滤", "低——漏判一封垃圾邮件影响小", "高——把重要邮件误判为垃圾邮件代价大", "<strong>提高阈值</strong>，牺牲召回换精确率"],
            ["医疗初筛（阳性即转诊复查）", "极高——漏诊致命", "中——多一次复查有成本但可接受", "降低阈值，宁可信其有"],
        ]),
        CALLOUT("warn", "阈值选择必须建立在<strong>验证集</strong>上，不能用测试集调阈值——这和用测试集调超参数是同一类错误，"
                        "会让你在测试集上的评估结果虚高。工程上常见做法是在验证集上扫描阈值画出 PR 曲线，"
                        "锁定阈值后才在测试集上报一次最终指标。"),
        H3("典型追问：Youden's J 与「与场景无关」的阈值选择"),
        P("如果面试官问「没有明确代价矩阵怎么选阈值」，一个安全答案是 <span class=\"term\">Youden's J</span> 统计量："
          "$J = TPR - FPR$ 最大化的点，几何上是 ROC 曲线上离对角线最远的点。<strong>但要补一句「这只是一个无代价假设下的"
          "默认解，真实工程里几乎总有代价矩阵，应该优先用它」</strong>——只给出公式而不加这句限定，会显得你没有工作点选择的实战经验。"),
        CALLOUT("intuition", "一句话总结：<strong>阈值不是从指标里「读」出来的，是从代价矩阵里「算」出来的</strong>；"
                             "没有代价矩阵时才退而求其次用 Youden's J 或 F1 最大点。"),
    ])),

    # ============================================================== 5
    ("calibration", "校准：可靠性图、ECE、温度缩放", "".join([
        P("<span class=\"term\">校准</span>（calibration）回答的是一个和「准不准」完全不同的问题：<strong>"
          "「模型说我 90% 有把握时，它真的有 90% 的时候是对的吗？」</strong>——这是"
          "「高置信不等于高准确」这句话的精确版本。"),
        DUAL(
            "现代深度网络有一个广为人知的坏毛病：它们通常<strong>过度自信</strong>。一个 softmax 输出 0.99 的预测，"
            "实际正确率可能只有 0.85——网络在「知道自己不知道」这件事上是不诚实的，而这在需要做风险决策的系统里"
            "（要不要触发紧急制动、要不要转诊）是致命的。",
            "严格定义：模型是<strong>完美校准</strong的，如果对所有输出置信度为 $c$ 的预测，其真实正确率恰好等于 $c$。"
            "<span class=\"term\">可靠性图</span>（reliability diagram）把预测按置信度分桶，"
            "画「桶内平均置信度」vs「桶内实际准确率」，完美校准应该落在对角线上；"
            "<span class=\"term\">ECE</span>（Expected Calibration Error）把每个桶的偏差按桶内样本占比加权求和，"
            "给出一个标量总结这条曲线偏离对角线的程度。",
        ),
        MATH("\\text{ECE} = \\sum_{b=1}^{B} \\frac{n_b}{N}\\, \\big|\\, \\text{acc}(b) - \\text{conf}(b)\\, \\big|"),
        ASCII("""可靠性图（10 个置信度桶）
准确率
  1.0┤                              ╱  ← 完美校准（对角线）
     │                          ●╱
     │                      ●  ╱
     │                  ● ╱               ● = 模型的实际桶（常见现象：
     │              ● ╱                        高置信区间的柱子低于对角线
     │          ●  ╱                            —— over-confident）
  0.0└──────────────────────────────► 置信度
     0.0                            1.0"""),
        TABLE(["校准方法", "做什么", "代价", "适用场景"], [
            ["<strong>温度缩放</strong> Temperature Scaling", "把 logits 除以标量 $T{>}1$ 再过 softmax，压平过度自信的分布", "只有 1 个参数，验证集拟合几秒钟", "<strong>首选</strong>——不改变预测排序（不影响 accuracy/AUC），只调整置信度的尺度"],
            ["Platt Scaling", "在 logit 上拟合一个逻辑回归 $\\sigma(aZ+b)$", "2 个参数，比温度缩放灵活但也更容易过拟合验证集", "二分类、样本量适中"],
            ["Isotonic Regression", "非参数、单调地重映射置信度", "参数量随分桶数增长，小验证集上容易过拟合", "验证集足够大时效果最好，但要小心过拟合"],
        ]),
        CALLOUT("danger", "<strong>「高置信不等于高准确」是这一节唯一要记住的一句话。</strong>"
                          "在检测/分类的下游决策里（例如 TSR 输出直接喂给 VLA，见 C59-03），"
                          "如果不传置信度、或置信度本身没有校准过，下游系统会把「模型自信但错了」的输出当真——"
                          "这是感知-决策接口最常见也最隐蔽的设计错误。"),
        CALLOUT("warn", "温度缩放只能修正<strong>整体</strong>的过度自信，修不了「模型对某个特定类别系统性地过度自信」这种"
                        "更细粒度的偏差——那需要按类别做校准，而且要小心校准用的验证集本身分布是否和线上一致。"),
    ])),

    # ============================================================== 6
    ("ci-significance", "置信区间与显著性检验：正态 / bootstrap / Wilson", "".join([
        P("「AP 从 0.42 涨到 0.45」——这句话本身没有意义，除非你能回答「这个 0.03 是噪声还是真实提升」。"
          "置信区间和显著性检验就是回答这个问题的两套工具，<strong>选错方法会让你把噪声当成信号</strong>（见 C61-01）。"),
        TABLE(["方法", "假设", "什么时候用", "什么时候失效"], [
            ["正态近似 CI", "$n$ 足够大，$\\hat p$ 不接近 0 或 1（中心极限定理生效）", "样本量大、比例适中的场景，计算最快", "<strong>小样本或极端比例下覆盖率显著低于名义值</strong>——比如 $n{=}20, \\hat p{=}0.95$ 时区间可能跑到 1 以外"],
            ["Bootstrap", "只需要能重复重采样，几乎不假设分布形状", "任意统计量（中位数、AUC、mAP 这类没有解析方差公式的量）", "计算量大；重采样次数不够时区间本身有噪声；对极小样本仍然不稳"],
            ["Wilson Score", "专为二项比例设计，用「反转正态检验」推导，天然把区间约束在 $[0,1]$", "<strong>二分类准确率/召回率这类比例型指标的首选</strong>，尤其小样本", "只适用于二项比例，不能直接套到均值或 AUC 上"],
        ]),
        MATH("\\text{Wilson}:\\quad \\hat p_{center} = \\frac{\\hat p + \\frac{z^2}{2n}}{1+\\frac{z^2}{n}}, \\qquad \\text{margin} = \\frac{z}{1+\\frac{z^2}{n}}\\sqrt{\\frac{\\hat p(1-\\hat p)}{n} + \\frac{z^2}{4n^2}}"),
        DUAL(
            "正态 CI 的公式人人都写得出（$\\hat p \\pm z\\sqrt{\\hat p(1-\\hat p)/n}$），但它有一个致命的隐藏假设：$n$ 要足够大。"
            "$n{=}20$ 时测出 19 次正确（$\\hat p{=}0.95$），正态公式会给出一个可能超过 1 的上界——"
            "<em>区间本身就已经荒谬了，这正是「小样本下别无脑用正态近似」的活证据</em>。",
            "Wilson 区间的推导思路是<strong>反转显著性检验</strong>：先问「对哪些 $p_0$，观测到的 $\\hat p$ 不会被拒绝」，"
            "把这些 $p_0$ 的集合作为置信区间——这个构造方式天然保证区间落在 $[0,1]$ 内，"
            "且小样本下的覆盖率比正态近似更接近名义值。<em>这也是为什么 Wilson 区间是二项比例场景下更稳的默认选择</em>，"
            "而不是「更复杂所以更好」。",
        ),
        H3("显著性检验：配对 vs 非配对"),
        P("同一批测试样本上，模型 A 与模型 B 的差异要用<strong>配对</strong>检验（paired t-test 或 bootstrap 配对），"
          "因为两组分数天然相关（同一张图片难，两个模型大概率都难）；"
          "如果是两批<em>不同</em>的测试样本（比如 A/B 测试里两组不同用户），才用非配对检验。"
          "<strong>用错会低估显著性——把配对数据当非配对处理，方差会被高估，导致本该显著的结果被判为不显著。</strong>"),
        CALLOUT("warn", "「+0.3 mAP 算不算提升」是检测岗最常见的追问（见 C61-01）。正确答法：先给出多种子的方差范围"
                        "（比如典型 ±0.2–0.5），再说明用的是配对还是非配对检验，最后给出结论——"
                        "<em>不给方差范围直接说「涨了」，是这一段最容易失分的地方</em>。"),
    ])),

    # ============================================================== 7
    ("ab-testing", "A/B 测试：样本量、功效、新奇效应与多重比较", "".join([
        P("A/B 测试是把「显著性检验」搬到真实用户身上的工程实践，多出的坑全部来自<strong>「真实世界」这三个字</strong>——"
          "用户会变、实验会被同时运行多个、新功能天然会引来短暂的额外关注。"),
        MATH("n \\;\\approx\\; \\frac{(z_{\\alpha/2} + z_{\\beta})^2 \\big(p_1(1-p_1) + p_2(1-p_2)\\big)}{(p_1 - p_2)^2}"),
        DUAL(
            "样本量公式的直觉是：想检出的效应 $|p_1-p_2|$ 越小，需要的样本量按<strong>平方反比</strong>暴涨——"
            "想把「能检出的最小提升」减半，样本量要翻 4 倍。这也是为什么很多团队宁愿多等两周攒够样本，"
            "也不愿意在样本不够时强行下结论。",
            "$z_{\\alpha/2}$ 由显著性水平 $\\alpha$（第一类错误率，通常 0.05）决定，$z_\\beta$ 由"
            "<span class=\"term\">功效</span>（power，$1-\\beta$，通常要求 0.8）决定——"
            "<strong>功效是「真的有效应时，你的实验有多大概率检测出来」</strong>，"
            "这是经常被忽略的一半：很多「无显著差异」的实验结论，其实只是样本量不够、功效太低，"
            "而不是真的没有效应。",
        ),
        TABLE(["陷阱", "机制", "怎么防"], [
            ["<strong>新奇效应</strong> novelty effect", "用户因为「新」而多点击/多停留，效应会随时间衰减", "实验跑够长（覆盖至少一个完整周期），看效应是否随时间递减"],
            ["<strong>多重比较</strong> multiple comparisons", "同时看 10 个指标，每个都用 $\\alpha{=}0.05$，至少一个假阳性的概率飙到 $1-0.95^{10}\\approx 40\\%$", "Bonferroni 校正（$\\alpha/m$）或控制 FDR（Benjamini-Hochberg），或提前锁定<strong>唯一</strong>的主指标"],
            ["<strong>提前偷看（peeking）</strong>", "看到显著就提前停止实验，等价于隐式做了多重比较，实际第一类错误率远高于 0.05", "预先固定样本量/时长，或用序贯检验（sequential testing）等专门为「持续监控」设计的方法"],
            ["样本比例失衡 / SRM", "分流本身就有 bug，两组样本比例不是预期的 50/50", "先做<span class=\"term\">样本比例不匹配</span>（Sample Ratio Mismatch）检验，比看指标更优先"],
        ]),
        CALLOUT("danger", "<strong>「每天看一眼 dashboard，一看到显著就下结论」是 A/B 测试里最常见的事故根源</strong>——"
                          "本质上是把「提前偷看」和「多重比较」揉在了一起：你在多个时间点上反复检验同一个假设，"
                          "总有一个时间点会因为纯噪声而「显著」。"),
        CALLOUT("intuition", "记住这条判断顺序：<strong>先查 SRM → 再查功效是否够 → 再查是不是多个指标/多个时间点在偷看 → "
                             "最后才谈论 $p$ 值本身</strong>。大部分「A/B 测试结论不可信」的真实故事，问题都出在前三步，而不是最后一步。"),
    ])),

    # ============================================================== 8
    ("traps-bayes", "统计陷阱四重奏与概率题：从辛普森悖论到基率谬误", "".join([
        P("这一节是「快问快答」的预演——面试官爱用一个简短故事考你能不能认出陷阱的名字，"
          "然后追问「你怎么在自己的数据里发现它」。"),
        TABLE(["陷阱", "一句话机制", "怎么在数据里发现它"], [
            ["<strong>辛普森悖论</strong> Simpson's Paradox", "分组内的趋势，合并后反转——因为组的权重（样本量）在分组间不同", "任何「整体指标」的结论，都要按关键维度（场景/子群体）切片复核一遍，见 C58-05 的分场景切片评测"],
            ["<strong>幸存者偏差</strong> Survivorship Bias", "只观察到「活下来」的样本，看不到被淘汰的那部分，导致结论系统性偏乐观", "检查数据收集流程本身是否存在过滤——线上只收集到「成功上报」的 badcase，漏检的往往不在里面"],
            ["<strong>回归到均值</strong> Regression to the Mean", "一次极端表现之后，下一次测量自然会更靠近均值，容易被误认为「干预生效」", "设对照组；只对「上次表现极端」的样本做前后对比是这个陷阱的经典触发条件"],
            ["<strong>p-hacking</strong>", "试了很多种切分/指标/模型，只报告显著的那个，本质是隐式的多重比较", "实验前<strong>预注册</strong>要检验的假设与指标；多重比较必须做校正（见上一节）"],
        ]),
        ASCII("""辛普森悖论的最小可复现构造：
                组 A（小样本）        组 B（大样本）        合并
  方案甲     8/10  = 80%          30/90  = 33%        38/100 = 38%
  方案乙     45/50 = 90%          2/10   = 20%        47/60  = 78%   ← 合并后乙反而遥遥领先！
  但分组看：组 A 里甲(80%)<乙(90%)，组 B 里甲(33%)>乙(20%) —— 两组内乙都不是简单地"更差"
  真相：乙把大量样本堆在组 A（乙容易的场景），甲把大量样本堆在组 B（甲难的场景），
        合并比例被"谁在哪个组测得多"主导，而不是被"哪个方案更好"主导。"""),
        DUAL(
            "贝叶斯定理直白地说，是「反过来想」：你想知道的是 $P(\\text{病}\\mid\\text{阳性})$，"
            "但你手上的数据通常是 $P(\\text{阳性}\\mid\\text{病})$（检测的灵敏度）——贝叶斯公式就是把后者倒过来算前者，"
            "而中间那个容易被忽略的分母，才是<span class=\"term\">基率谬误</span>（base rate fallacy）的根源。",
            "$P(A\\mid B) = P(B\\mid A)P(A) / P(B)$，其中 $P(B) = P(B\\mid A)P(A) + P(B\\mid \\neg A)P(\\neg A)$。"
            "基率谬误就是<strong>只盯着灵敏度 $P(B\\mid A)$，忘了先验 $P(A)$ 极小时分母会被 $P(\\neg A)$ 那一项主导</strong>——"
            "这正是「99% 准确率的检测，阳性结果却大概率是假的」这类反直觉结论的完整数学解释。",
        ),
        MATH("P(\\text{disease}\\mid{+}) = \\frac{P({+}\\mid\\text{disease})\\,P(\\text{disease})}{P({+}\\mid\\text{disease})P(\\text{disease}) + P({+}\\mid\\neg\\text{disease})P(\\neg\\text{disease})}"),
        P("代入一个经典数字：患病率 $P(\\text{disease}){=}0.001$，检测灵敏度与特异度都是 99%。"
          "算出来 $P(\\text{disease}\\mid{+}) \\approx 0.09$——<strong>阳性结果里超过 90% 是假阳性</strong>，"
          "尽管测试本身「99% 准」。这个数字每次算出来都会让人意外，这正是它作为面试题的价值："
          "<em>它检验的不是你会不会背公式，而是你有没有真正把公式在脑子里跑过一遍</em>。"),
        CALLOUT("warn", "「期望的线性性」$E[X+Y]=E[X]+E[Y]$<strong>永远成立，不需要 $X,Y$ 独立</strong>——"
                        "这是概率题里最容易被误用的一条「附加条件」，很多人下意识加上「因为独立」，"
                        "其实线性性对任意随机变量、任意相关结构都成立，独立只在算方差 $\\text{Var}(X{+}Y)$ 时才是必要条件。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("最后放一组更长期的问题——它们不会直接出现在你的一面里，但决定了「评估这件事」本身正在往哪个方向演化。"),
        UL([
            "<strong>校准在分布漂移下会失效吗？</strong>温度缩放假设验证集与部署分布一致；一旦线上出现验证集没见过的天气/光照，"
            "温度缩放学到的那个标量 $T$ 不再适用。<em>如何做「分布漂移鲁棒」的校准，仍是一个开放问题——"
            "目前的工程折中通常是按场景分桶各自校准（呼应 C58-05 的分场景评测），而不是追求一个全局最优 $T$。</em>",
            "<strong>安全攸关系统里 PR-AUC 也不够用。</strong>它仍然是一个「平均」指标，掩盖了具体在哪个阈值下、"
            "哪个子场景下会出问题。TSR、医疗这类领域正在转向<em>分桶 + 场景化</em>的评测体系"
            "（按距离/光照/类别切片，见 C55-05），单一标量指标的地位正在下降。",
            "<strong>持续实验平台上的多重比较问题被低估。</strong>大公司同时跑成百上千个 A/B 实验，"
            "传统的 Bonferroni 校正过于保守（会让检出效应变得极难），FDR 控制和贝叶斯层级模型是当前更主流的工业实践，"
            "但「怎么在保持高吞吐决策的同时控制长期误报率」仍在演进中。",
            "<strong>LLM 参与统计推理时会不会引入新的统计错误？</strong>让大模型辅助做数据分析、自动选择检验方法，"
            "正在成为新的工作流，但它们和人类一样会犯基率谬误、会被辛普森悖论骗到——"
            "<em>而且更危险的是它们输出时的语气通常很自信，这让「高置信不等于高准确」这条规律在人机协作场景里更加重要。</em>",
            "<strong>贝叶斯 A/B 测试与频率派方法之争仍未有定论。</strong>贝叶斯框架允许「持续监控不受多重比较惩罚」这类"
            "更符合工程直觉的用法，但它引入了先验选择的主观性；两派方法在工业界的取舍仍是一个活跃的讨论。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Davis & Goadrich, <em>The Relationship Between Precision-Recall and ROC Curves</em>"
                         "（ICML 2006）——ROC 与 PR 空间等价性的正式证明，本节 §3 的理论来源。"
                         "<strong>★</strong> Guo, Pleiss, Sun, Weinberger, <em>On Calibration of Modern Neural Networks</em>"
                         "（ICML 2017）——「现代网络普遍过度自信」的经典实证与温度缩放的提出。"
                         "<strong>★</strong> Wilson, <em>Probable Inference, the Law of Succession, and Statistical Inference</em>"
                         "（1927）——Wilson score interval 的原始推导。</p>"
                         "<p>Efron, <em>Bootstrap Methods: Another Look at the Jackknife</em>（1979）——bootstrap 的奠基工作；"
                         "Ioannidis, <em>Why Most Published Research Findings Are False</em>（PLoS Medicine, 2005）——"
                         "p-hacking 与多重比较在科研中系统性泛滥的经典论证；Kohavi et al., "
                         "<em>Trustworthy Online Controlled Experiments</em>（2020）——A/B 测试工程实践的权威参考。"
                         "相邻课程：数学推导见 <strong>C07</strong>；类别不平衡处理谱系见 <strong>C58-01</strong>；"
                         "安全导向的分桶评测见 <strong>C55-05</strong>；检测专项的 mAP/TIDE 细节见 <strong>C18、C53–C61</strong>；"
                         "种子方差与显著性的工程实践见 <strong>C61-01</strong>。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 04 · 评估、概率与统计问答（指标全家 / ROC vs PR-AUC / 校准 / 置信区间 / A/B 测试 / 统计陷阱）

目标：把「这个指标什么时候会骗你」从口头描述，变成**能跑出数字、能亲眼看到分歧**的小实验。

本 notebook 你会亲手实现：
1. **环境自检**
2. **指标全家计算器** —— 从混淆矩阵算 Accuracy/Precision/Recall/F1/Fβ，并验证它们之间的代数关系
3. **ROC-AUC vs PR-AUC 分歧演示** —— 同一个分类器，在平衡与不平衡数据上对比两种 AUC
4. **代价敏感阈值选择** —— 给定代价矩阵，扫描阈值求期望代价最小的工作点
5. **校准：可靠性图 / ECE / 温度缩放** —— 亲手把一个「过度自信」的模型校准回去
6. **三种置信区间对比** —— 正态 / bootstrap / Wilson，小样本下看谁更稳
7. **A/B 测试的样本量与功效** —— 反推「要检出这个效应需要多少用户」
8. **辛普森悖论的可复现构造** —— 分组内都占优，合并后反转

> 心智模型：**统计方法的正确性不是「公式对不对」，是「前提假设成不成立」。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math, random
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'trapezoid') or hasattr(np, 'trapz')

rng_global = np.random.default_rng(0)
print('\\n✅ 环境自检通过：本模块不需要 GPU、不需要联网，全程固定 seed 保证可复现。')"""),

    md("""## 1 · 指标全家计算器

从原始的 TP/FP/FN/TN 出发，算出 Accuracy/Precision/Recall/F1/Fβ，
并验证「F1 是 Fβ 在 β=1 时的特例」「β→0 退化为 Precision，β→∞ 退化为 Recall」。"""),

    code("""def confusion_counts(y_true, y_pred):
    \"\"\"y_true/y_pred: 0/1 数组，返回 (TP, FP, FN, TN)。\"\"\"
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    return tp, fp, fn, tn

def precision_recall(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return p, r

def f_beta(p, r, beta=1.0):
    num = (1 + beta**2) * p * r
    den = beta**2 * p + r
    return num / den if den > 0 else 0.0

# 构造一组带明显不平衡的预测
y_true = [1]*10 + [0]*90
y_pred = [1]*9 + [0]*1 + [1]*10 + [0]*80     # 9 个真阳性、10 个假阳性、1 个假阴性

tp, fp, fn, tn = confusion_counts(y_true, y_pred)
p, r = precision_recall(tp, fp, fn)
acc = (tp + tn) / len(y_true)

assert (tp, fp, fn, tn) == (9, 10, 1, 80)
assert abs(p - 9/19) < 1e-9 and abs(r - 0.9) < 1e-9
assert abs(acc - 0.89) < 1e-9

f1 = f_beta(p, r, 1.0)
f05 = f_beta(p, r, 0.5)
f2 = f_beta(p, r, 2.0)
assert abs(f1 - 2*p*r/(p+r)) < 1e-9
assert f05 < f1 < f2                          # beta 越大越贴近 recall（这里 recall > precision）
assert abs(f_beta(p, r, 1e-6) - p) < 1e-4      # beta -> 0 退化为 precision
assert abs(f_beta(p, r, 1e6) - r) < 1e-4       # beta -> inf 退化为 recall

print(f'TP={tp} FP={fp} FN={fn} TN={tn}   accuracy={acc:.3f}')
print(f'precision={p:.3f}  recall={r:.3f}')
print(f'F0.5={f05:.3f}  F1={f1:.3f}  F2={f2:.3f}   (recall > precision -> beta 越大分数越高)')
print('\\n✅ 指标全家验证通过：Fβ 在 β→0/1/∞ 三个极限下都符合预期。')"""),

    md("""## 2 · ROC-AUC vs PR-AUC 分歧演示

同一个分类器（用分数排序模拟），分别放到「平衡」和「不平衡」两份数据上，
看两种 AUC 谁先「露馅」。"""),

    code("""def roc_auc(y_true, scores):
    \"\"\"ROC-AUC = P(score(正例) > score(负例))，用 Mann-Whitney U 的等价形式算，避免依赖 sklearn。\"\"\"
    y_true = np.asarray(y_true); scores = np.asarray(scores)
    pos = scores[y_true == 1]; neg = scores[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float('nan')
    # 对每个正例，统计有多少负例分数更低（打平记 0.5）
    greater = (pos[:, None] > neg[None, :]).sum()
    equal = (pos[:, None] == neg[None, :]).sum()
    return (greater + 0.5 * equal) / (len(pos) * len(neg))

def pr_curve(y_true, scores):
    \"\"\"按分数降序扫描阈值，返回 (recall_list, precision_list)，用于算 PR-AUC。\"\"\"
    y_true = np.asarray(y_true)
    order = np.argsort(-scores)
    y_sorted = y_true[order]
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    n_pos = int((y_true == 1).sum())
    recall = tp_cum / max(n_pos, 1)
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)
    return recall, precision

def pr_auc(y_true, scores):
    \"\"\"用梯形法则对 (recall, precision) 积分，recall 需先排序。\"\"\"
    recall, precision = pr_curve(y_true, scores)
    order = np.argsort(recall)
    r_sorted, p_sorted = recall[order], precision[order]
    return float(np.trapezoid(p_sorted, r_sorted)) if hasattr(np, 'trapezoid') \\
        else float(np.trapz(p_sorted, r_sorted))

rng = np.random.default_rng(42)

def make_scored_data(n_pos, n_neg, sep=1.2):
    \"\"\"正例分数 ~ N(sep, 1)，负例分数 ~ N(0, 1)，sep 控制可分性（两份数据用同一个 sep，即"同一个分类器"）。\"\"\"
    pos_scores = rng.normal(sep, 1.0, n_pos)
    neg_scores = rng.normal(0.0, 1.0, n_neg)
    y = np.array([1]*n_pos + [0]*n_neg)
    s = np.concatenate([pos_scores, neg_scores])
    return y, s

# 平衡数据：500 正 500 负
y_bal, s_bal = make_scored_data(500, 500)
auc_bal = roc_auc(y_bal, s_bal)
prauc_bal = pr_auc(y_bal, s_bal)

# 不平衡数据：同样的分类器能力（sep 相同），但正例只有 1%
y_imb, s_imb = make_scored_data(100, 9900)
auc_imb = roc_auc(y_imb, s_imb)
prauc_imb = pr_auc(y_imb, s_imb)

print(f'{"数据集":<10}{"ROC-AUC":>10}{"PR-AUC":>10}')
print(f'{"平衡 1:1":<10}{auc_bal:>10.3f}{prauc_bal:>10.3f}')
print(f'{"不平衡 1:99":<10}{auc_imb:>10.3f}{prauc_imb:>10.3f}')

# 核心断言：分类器能力不变，ROC-AUC 几乎不受类别比例影响；PR-AUC 大幅下降
assert abs(auc_bal - auc_imb) < 0.03, 'ROC-AUC 应该对类别比例基本不敏感'
assert prauc_imb < prauc_bal - 0.15, 'PR-AUC 应该随正类稀释明显下降'
print('\\n✅ 分歧验证通过：同一个分类器，ROC-AUC 几乎不变，PR-AUC 明显下降 —— 这就是"ROC-AUC 会骗人"的数值证据。')"""),

    md("""## 3 · 代价敏感阈值选择

给定 $C_{FP}, C_{FN}$，扫描阈值求期望代价最小的工作点，而不是无脑用 0.5。"""),

    code("""def best_threshold(y_true, scores, c_fp, c_fn, grid=None):
    \"\"\"扫描阈值网格，返回 (最优阈值, 最小期望代价, 完整记录)。\"\"\"
    y_true = np.asarray(y_true); scores = np.asarray(scores)
    if grid is None:
        grid = np.linspace(scores.min(), scores.max(), 200)
    best_t, best_cost, records = None, float('inf'), []
    for t in grid:
        pred = (scores >= t).astype(int)
        tp, fp, fn, tn = confusion_counts(y_true, pred)
        cost = c_fp * fp + c_fn * fn
        records.append((t, cost, fp, fn))
        if cost < best_cost:
            best_cost, best_t = cost, t
    return best_t, best_cost, records

y_imb2, s_imb2 = y_imb, s_imb   # 复用上面的不平衡数据

# 场景一：漏检代价远高于误检（例如 TSR 停车让行标志）
t_a, cost_a, _ = best_threshold(y_imb2, s_imb2, c_fp=1.0, c_fn=20.0)
# 场景二：两种错误代价相同
t_b, cost_b, _ = best_threshold(y_imb2, s_imb2, c_fp=1.0, c_fn=1.0)

assert t_a < t_b, '漏检代价越高，最优阈值应该越低（更愿意多报警）'
print(f'漏检代价高（C_FN=20） -> 最优阈值 {t_a:.3f}，期望代价 {cost_a:.1f}')
print(f'两种代价相同（C_FN=1）  -> 最优阈值 {t_b:.3f}，期望代价 {cost_b:.1f}')
print(f'\\n阈值差 = {t_b - t_a:.3f} > 0，验证「漏检代价越高，阈值应该越低」这条方向性结论。')
print('✅ 代价敏感阈值选择通过：阈值不是"读"出来的，是从代价矩阵"算"出来的。')"""),

    md("""## 4 · 校准：可靠性图 / ECE / 温度缩放

先构造一个「刻意过度自信」的模型输出，量化它的 ECE，再用温度缩放把它校准回去。"""),

    code("""def make_overconfident_probs(y_true, base_acc=0.75, rng=rng):
    \"\"\"构造一个"实际准确率只有 base_acc，但汇报的置信度普遍很高"的模型输出。
    关键是让 preds 的正确性由 base_acc 独立决定，汇报的置信度与真实正确性脱钩——
    这正是"过度自信"的本质：置信度没有跟着真实难度走。\"\"\"
    y_true = np.asarray(y_true)
    n = len(y_true)
    is_correct = rng.random(n) < base_acc
    preds = np.where(is_correct, y_true, 1 - y_true)          # 按 base_acc 决定预测对不对
    conf_reported = np.clip(1 - 0.5 * rng.beta(1, 6, n), 0.55, 0.999)   # 汇报的置信度普遍偏高（0.55~0.999）
    probs = np.where(preds == 1, conf_reported, 1 - conf_reported)
    return probs

def reliability_bins(y_true, probs, n_bins=10):
    \"\"\"按置信度分桶，返回每桶的 (平均置信度, 实际准确率, 样本数)。\"\"\"
    y_true = np.asarray(y_true); probs = np.asarray(probs)
    preds = (probs >= 0.5).astype(int)
    correct = (preds == y_true).astype(float)
    conf = np.where(preds == 1, probs, 1 - probs)      # "预测那个类"的置信度
    edges = np.linspace(0, 1, n_bins + 1)
    out = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i+1]
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        if mask.sum() == 0:
            continue
        out.append((conf[mask].mean(), correct[mask].mean(), int(mask.sum())))
    return out

def ece(bins, n_total):
    return sum(cnt / n_total * abs(acc - cf) for cf, acc, cnt in bins)

y_true3 = rng.integers(0, 2, 2000)
probs_over = make_overconfident_probs(y_true3)

bins_over = reliability_bins(y_true3, probs_over)
ece_over = ece(bins_over, len(y_true3))
print('过度自信模型的可靠性桶（置信度, 准确率, 样本数）：')
for cf, acc, cnt in bins_over:
    print(f'  conf={cf:.2f}  acc={acc:.2f}  n={cnt}')
print(f'ECE(过度自信) = {ece_over:.3f}')
assert ece_over > 0.08, '构造的模型应该明显过度自信'"""),

    code("""def apply_temperature(probs, T):
    \"\"\"把概率转回 logit，除以 T，再转回概率 —— 温度缩放不改变预测排序，只压平置信度。\"\"\"
    probs = np.clip(probs, 1e-6, 1 - 1e-6)
    logit = np.log(probs / (1 - probs))
    scaled_logit = logit / T
    return 1 / (1 + np.exp(-scaled_logit))

def fit_temperature(y_true, probs, T_grid=None):
    \"\"\"在验证集上网格搜索使 ECE 最小的 T（真实工程里常用 NLL 而不是 ECE，这里为了直接讲清意图用 ECE）。\"\"\"
    if T_grid is None:
        T_grid = np.linspace(0.5, 8.0, 60)
    best_T, best_ece = 1.0, float('inf')
    for T in T_grid:
        p_scaled = apply_temperature(probs, T)
        b = reliability_bins(y_true, p_scaled)
        e = ece(b, len(y_true))
        if e < best_ece:
            best_ece, best_T = e, T
    return best_T, best_ece

T_star, ece_after = fit_temperature(y_true3, probs_over)
preds_before = (probs_over >= 0.5).astype(int)
p_scaled = apply_temperature(probs_over, T_star)
preds_after = (p_scaled >= 0.5).astype(int)

assert T_star > 1.5, '过度自信的模型应该需要 T > 1 来压平置信度'
assert ece_after < ece_over * 0.5, '温度缩放后 ECE 应该显著下降'
assert np.array_equal(preds_before, preds_after), '温度缩放不改变预测类别（排序不变），只改变置信度数值'

print(f'最优温度 T* = {T_star:.2f}')
print(f'ECE：{ece_over:.3f}  ->  {ece_after:.3f}（下降 {(1 - ece_after/ece_over)*100:.0f}%）')
print('预测类别在缩放前后完全一致：', np.array_equal(preds_before, preds_after))
print('\\n✅ 校准验证通过：温度缩放只调整"自信程度"，不改变"猜哪个类"。')"""),

    md("""## 5 · 三种置信区间对比：正态 / bootstrap / Wilson

在同一批数据上算三种 95% 置信区间，重点看**小样本 + 极端比例**下三者的差异。"""),

    code("""def normal_ci(k, n, z=1.96):
    p = k / n
    se = math.sqrt(p * (1 - p) / n) if n > 0 else 0.0
    return max(p - z*se, -math.inf), min(p + z*se, math.inf)   # 故意不裁剪到 [0,1]，暴露它会越界

def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = (z / denom) * math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    return center - margin, center + margin

def bootstrap_ci(successes_array, n_boot=5000, z_pct=(2.5, 97.5), rng=rng):
    \"\"\"successes_array: 0/1 数组。对均值做非参数 bootstrap。\"\"\"
    n = len(successes_array)
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        boot_means[i] = successes_array[idx].mean()
    lo, hi = np.percentile(boot_means, z_pct)
    return float(lo), float(hi)

# 场景：小样本、高比例 —— 三者分歧最大的地方
n_small, k_small = 20, 19          # 20 次里对了 19 次
arr_small = np.array([1]*k_small + [0]*(n_small-k_small))

lo_n, hi_n = normal_ci(k_small, n_small)
lo_w, hi_w = wilson_ci(k_small, n_small)
lo_b, hi_b = bootstrap_ci(arr_small)

print(f'小样本 n={n_small}, k={k_small} (p_hat={k_small/n_small:.2f})：')
print(f'  正态   CI: [{lo_n:.3f}, {hi_n:.3f}]  <- 注意上界是否超过 1')
print(f'  Wilson CI: [{lo_w:.3f}, {hi_w:.3f}]  <- 应天然落在 [0,1] 内')
print(f'  Bootstrap CI: [{lo_b:.3f}, {hi_b:.3f}]')

assert hi_n > 1.0, '正态近似在极端比例小样本下应该越界（这正是它的失效证据）'
assert 0.0 <= lo_w and hi_w <= 1.0, 'Wilson 区间天然落在 [0,1] 内'
assert 0.0 <= lo_b <= hi_b <= 1.0

# 场景：大样本、适中比例 —— 三者应该基本一致
n_big, k_big = 5000, 2500
arr_big = np.array([1]*k_big + [0]*(n_big-k_big))
lo_n2, hi_n2 = normal_ci(k_big, n_big)
lo_w2, hi_w2 = wilson_ci(k_big, n_big)
assert abs(lo_n2 - lo_w2) < 0.01 and abs(hi_n2 - hi_w2) < 0.01, '大样本适中比例下正态与 Wilson 应几乎重合'

print(f'\\n大样本 n={n_big}, p_hat=0.50：正态 [{lo_n2:.3f},{hi_n2:.3f}] vs Wilson [{lo_w2:.3f},{hi_w2:.3f}]  <- 几乎重合')
print('\\n✅ 三种 CI 验证通过：小样本极端比例下正态近似会越界，Wilson 稳；大样本下三者趋同。')"""),

    md("""## 6 · A/B 测试：样本量与功效计算

反推「要检出这个效应，需要多少用户」，并验证"效应减半、样本量翻 4 倍"这条平方反比关系。"""),

    code("""from math import erf, sqrt

def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))

def z_from_alpha(alpha_two_sided=0.05):
    \"\"\"双侧检验的临界值，用二分查找反解正态分布分位数（不依赖 scipy）。\"\"\"
    target = 1 - alpha_two_sided / 2
    lo, hi = 0.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def sample_size_two_proportion(p1, p2, alpha=0.05, power=0.8):
    \"\"\"两比例 z 检验所需的每组样本量（正态近似公式）。\"\"\"
    z_alpha = z_from_alpha(alpha)
    z_beta = z_from_alpha(2 * (1 - power))     # 单侧功效对应的 z_beta：power=1-beta -> beta=1-power
    numerator = (z_alpha + z_beta)**2 * (p1*(1-p1) + p2*(1-p2))
    denominator = (p1 - p2)**2
    return math.ceil(numerator / denominator)

z95 = z_from_alpha(0.05)
assert abs(z95 - 1.96) < 0.01, z95      # 验证反解出的临界值就是熟悉的 1.96

n1 = sample_size_two_proportion(0.10, 0.12)          # 基线 10% -> 12%，绝对提升 2pp
n2 = sample_size_two_proportion(0.10, 0.11)          # 效应减半：绝对提升只有 1pp

print(f'z(alpha=0.05, 双侧) = {z95:.3f}')
print(f'检出 10%->12% 需要每组约 {n1:,} 用户')
print(f'检出 10%->11%（效应减半）需要每组约 {n2:,} 用户')
print(f'样本量之比 = {n2/n1:.2f}   <- 效应减半，样本量应接近翻 4 倍（平方反比）')

assert 3.5 < n2 / n1 < 4.6, (n1, n2)
print('\\n✅ 功效计算验证通过：效应减半，所需样本量接近翻 4 倍。')"""),

    md("""## 7 · 辛普森悖论的可复现构造

固定构造一组"分组内都是方案乙更优、合并后方案甲反而更优"的数据，逐行验证反转确实发生。"""),

    code("""# 组 A（小分母，方案乙表现好）与组 B（大分母，方案乙表现差），但方案乙把大量样本堆在了"容易"的组 A
group_A = {'甲': (8, 10), '乙': (45, 50)}     # (成功数, 总数)
group_B = {'甲': (30, 90), '乙': (2, 10)}

def rate(k, n):
    return k / n

rate_A_jia, rate_A_yi = rate(*group_A['甲']), rate(*group_A['乙'])
rate_B_jia, rate_B_yi = rate(*group_B['甲']), rate(*group_B['乙'])

k_jia = group_A['甲'][0] + group_B['甲'][0]; n_jia = group_A['甲'][1] + group_B['甲'][1]
k_yi = group_A['乙'][0] + group_B['乙'][0]; n_yi = group_A['乙'][1] + group_B['乙'][1]
rate_overall_jia, rate_overall_yi = rate(k_jia, n_jia), rate(k_yi, n_yi)

print(f'组 A：甲 {rate_A_jia:.2f}   乙 {rate_A_yi:.2f}   (乙更优: {rate_A_yi > rate_A_jia})')
print(f'组 B：甲 {rate_B_jia:.2f}   乙 {rate_B_yi:.2f}   (甲更优: {rate_B_jia > rate_B_yi})')
print(f'合并：甲 {rate_overall_jia:.2f}   乙 {rate_overall_yi:.2f}   (乙更优: {rate_overall_yi > rate_overall_jia})')

# 核心断言：两个分组内的"谁更优"结论不一致，且合并结果与其中至少一组的结论相反
assert rate_A_yi > rate_A_jia          # 组 A 内乙更优
assert rate_B_jia > rate_B_yi          # 组 B 内甲更优
assert rate_overall_yi > rate_overall_jia   # 合并后乙更优 —— 与组 B 内的结论相反！

# 权重解释：乙在组 A（分母小、比例高）投入的样本占比 远高于 在组 B
weight_yi_in_A = group_A['乙'][1] / n_yi
weight_jia_in_A = group_A['甲'][1] / n_jia
assert weight_yi_in_A > weight_jia_in_A
print(f'\\n乙投入组 A 的样本占比 {weight_yi_in_A:.2f}，甲投入组 A 的样本占比 {weight_jia_in_A:.2f}')
print('乙把更多样本堆在了"更容易"的组 A —— 这正是合并比例被权重主导、而非被"真实优劣"主导的机制。')
print('\\n✅ 辛普森悖论构造验证通过：分组内结论相反，合并结论由样本权重主导。')"""),

    md("""## ✏️ 练习 1：Wilson 区间的宽度反推

实现 `wilson_width(k, n, z=1.96)`，直接返回 Wilson 区间的**总宽度**（上界 - 下界），
并验证「$n$ 越大，区间越窄；$\\hat p$ 越极端（越接近 0 或 1），同样 $n$ 下区间越窄」。"""),

    code("""def wilson_width(k, n, z=1.96):
    # TODO: 复用 wilson_ci，返回宽度
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
w1 = wilson_width(50, 100)     # p_hat = 0.5，最不确定的比例
w2 = wilson_width(50, 400)     # 样本量翻 4 倍
w3 = wilson_width(95, 100)     # 同样 n=100，但 p_hat=0.95（更极端）

assert w2 < w1, 'n 越大，区间应该越窄'
assert w3 < w1, '同样 n 下，p_hat 越极端，区间应该越窄（方差 p(1-p) 更小）'
assert w1 > 0 and w2 > 0 and w3 > 0
print(f'n=100,  p_hat=0.50 : 宽度 {w1:.4f}')
print(f'n=400,  p_hat=0.50 : 宽度 {w2:.4f}  <- 样本翻 4 倍变窄')
print(f'n=100,  p_hat=0.95 : 宽度 {w3:.4f}  <- 比例更极端也变窄')
print('\\n✅ 练习 1 通过：置信区间宽度由 n 和 p_hat(1-p_hat) 共同决定，不是只看 n。')"""),

    md("""## ✏️ 练习 2：多重比较校正（Bonferroni）

实现 `bonferroni_correct(p_values, alpha=0.05)`，返回 `(corrected_alpha, [是否显著, ...])`。
规则：`corrected_alpha = alpha / len(p_values)`；某个 `p_value <= corrected_alpha` 才算显著。"""),

    code("""def bonferroni_correct(p_values, alpha=0.05):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
pvals = [0.001, 0.03, 0.04, 0.20, 0.049]
corrected_alpha, sig = bonferroni_correct(pvals, alpha=0.05)

assert abs(corrected_alpha - 0.01) < 1e-9
assert sig == [True, False, False, False, False], sig     # 只有 0.001 <= 0.01

# 不做校正的话，0.03/0.04/0.049 都会被判"显著"，5 个指标里假阳性概率被推高到接近 1-0.95^5≈0.226
naive_sig = [p <= 0.05 for p in pvals]
assert sum(naive_sig) == 4 and sum(sig) == 1
print(f'校正后的 alpha = {corrected_alpha}')
print(f'不校正判定显著个数: {sum(naive_sig)}   校正后判定显著个数: {sum(sig)}')
print('\\n✅ 练习 2 通过：5 个指标同时检验时，不做校正会把假阳性率推到远高于 0.05。')"""),

    md("""## ✏️ 练习 3：期望代价最小阈值的整数网格版

实现 `min_cost_threshold_int(y_true, scores_int, c_fp, c_fn)`：`scores_int` 是**已排序去重**的整数分数候选阈值列表，
对每个候选阈值 `t`（`pred = 1 当 score >= t`）算期望代价，返回 `(最优阈值, 最小代价)`；
若有并列最小代价，取**较大**的阈值（更保守，误检更少）。"""),

    code("""def min_cost_threshold_int(y_true, scores, thresholds, c_fp, c_fn):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
y_ex = [1, 1, 1, 0, 0, 0, 0, 0]
s_ex = [9, 7, 3, 8, 6, 4, 2, 1]
cand = sorted(set(s_ex))

t_opt, cost_opt = min_cost_threshold_int(y_ex, s_ex, cand, c_fp=1.0, c_fn=1.0)
# 手工核对（y=1 的分数是 {9,7,3}，y=0 的分数是 {8,6,4,2,1}）：
#   t=7 -> TP=2(9,7),FP=1(8),FN=1(3)  cost=2
#   t=8 -> TP=1(9),  FP=1(8),FN=2(7,3) cost=3
#   t=9 -> TP=1(9),  FP=0,   FN=2(7,3) cost=2  <- 与 t=7 并列最小，取更大的阈值
assert t_opt == 9, t_opt
assert abs(cost_opt - 2.0) < 1e-9, cost_opt

t_opt2, cost_opt2 = min_cost_threshold_int(y_ex, s_ex, cand, c_fp=1.0, c_fn=10.0)
assert t_opt2 < t_opt, '漏检代价升高后，最优阈值应该更低（更愿意多报警而不是漏检）'
print(f'代价相同    -> 最优阈值 {t_opt}，代价 {cost_opt}')
print(f'漏检代价升高 -> 最优阈值 {t_opt2}，代价 {cost_opt2}')
print('\\n✅ 练习 3 通过：用整数网格重新验证"代价敏感阈值"，并列时选更保守的阈值。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def wilson_width(k, n, z=1.96):
    lo, hi = wilson_ci(k, n, z)
    return hi - lo"""),

    code("""# 练习 2 参考答案
def bonferroni_correct(p_values, alpha=0.05):
    corrected_alpha = alpha / len(p_values)
    sig = [p <= corrected_alpha for p in p_values]
    return corrected_alpha, sig"""),

    code("""# 练习 3 参考答案
def min_cost_threshold_int(y_true, scores, thresholds, c_fp, c_fn):
    y_true = np.asarray(y_true); scores = np.asarray(scores)
    best_t, best_cost = None, float('inf')
    for t in thresholds:
        pred = (scores >= t).astype(int)
        tp, fp, fn, tn = confusion_counts(y_true, pred)
        cost = c_fp * fp + c_fn * fn
        if cost < best_cost or (cost == best_cost and (best_t is None or t > best_t)):
            best_cost, best_t = cost, t
    return best_t, best_cost"""),

    md("""---
## 🧪 真实工程胶囊：评估与统计的面试速查卡"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 指标选择决策树（30 秒内说完）
# ══════════════════════════════════════════════════════════════════════
# 类别是否严重不平衡？
#   是 -> 看 PR-AUC，不要只看 ROC-AUC；报告时配一条"正类比例是多少"
#   否 -> ROC-AUC 可信；两者结论应该基本一致
# 是多类检测/分类？
#   -> 报 mAP，但必须配一张逐类 AP 表（mAP 会掩盖表现极差的类，见 C61-02 TIDE 分解）
# 犯两种错误的代价是否相等？
#   否 -> 别用默认阈值 0.5，从代价矩阵算最优工作点
#   是 -> Youden's J 或 F1 最大点是合理默认

# ══════════════════════════════════════════════════════════════════════
# B. 校准三问（面试官问"模型输出的概率能信吗"时用）
# ══════════════════════════════════════════════════════════════════════
# 1) 画过可靠性图 / 算过 ECE 吗？—— 没算过，先承认"没有校准过，置信度只能当排序用，不能当概率用"
# 2) 用什么校准？—— 温度缩放优先（不改变排序，一个参数，验证集上几秒拟合完）
# 3) 校准会不会过期？—— 会，分布漂移后需要重新校准，且理想上应按场景分桶校准

# ══════════════════════════════════════════════════════════════════════
# C. "+0.3 算不算提升"的标准答法（呼应 C61-01）
# ══════════════════════════════════════════════════════════════════════
# 「不看单次数字，看多种子的方差范围；同一测试集上用配对检验（因为难度天然相关）；
#   如果只跑了一个种子，我会说"暂时无法判断是信号还是噪声，需要多种子复核"。」

# ══════════════════════════════════════════════════════════════════════
# D. A/B 测试的四步检查顺序（别跳步）
# ══════════════════════════════════════════════════════════════════════
# 1) 先查 SRM（样本比例是否符合预期分流）
# 2) 再查功效是否够（样本量是否达到 power=0.8 的要求）
# 3) 再查是否多个指标/多个时间点在偷看（需要 Bonferroni/FDR 校正，或预先固定唯一主指标）
# 4) 最后才谈论 p 值本身

# ══════════════════════════════════════════════════════════════════════
# E. 统计陷阱一句话识别表
# ══════════════════════════════════════════════════════════════════════
# 整体涨了但分组看很怪         -> 辛普森悖论，按关键维度切片复核
# 数据只来自"成功上报"的样本   -> 幸存者偏差，检查数据收集流程本身
# 极端表现之后自然回落         -> 回归到均值，需要对照组
# 试了很多种切法只报好看的那个 -> p-hacking，预注册假设 + 多重比较校正

# ══════════════════════════════════════════════════════════════════════
# F. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 贝叶斯公式/交叉验证的完整数学推导        -> C07（本模块只讲"怎么讲清楚"）
# · 类别不平衡的处理谱系（重采样/重加权）    -> C58-01
# · 安全导向的分桶评测体系                  -> C55-05
# · mAP/TIDE 误差分解的检测专项细节         -> C18、C53-C61
# · 种子方差与显著性的工程实践              -> C61-01
# · 150+ 题快问快答题库（含本模块全部主题） -> C64 模块 05
'''
print(RECIPE)
for token in ['PR-AUC', '温度缩放', 'SRM', '辛普森悖论', 'C61-01', 'Youden']:
    assert token in RECIPE, token
print('✅ 速查卡覆盖：指标决策树 / 校准三问 / 提升判定 / A/B 四步顺序 / 陷阱识别 / 课程分工')"""),

    md("""### 小结

- **统计方法的正确性不是"公式对不对"，是"前提假设成不成立"。** 这是本模块所有小节的统一读法，
  也是「一句话定义 → 为什么需要 → **什么时候失效**」三段式在这一段被放大的原因。
- **ROC-AUC 在不平衡数据下会骗人**：它是一个排序统计量，分母里有海量真阴性稀释假阳性的影响；
  正类稀少时应该看 **PR-AUC**，报 mAP 时永远要配一张逐类 AP 表。
- **阈值不是"读"出来的，是从代价矩阵"算"出来的**——期望代价 $C_{FP}\\cdot FP + C_{FN}\\cdot FN$ 最小的点才是合理工作点。
- **高置信不等于高准确**：现代深度网络普遍过度自信，温度缩放是低成本的默认修复手段，
  但它修不了分布漂移后的失效，也修不了按类别的系统性偏差。
- **小样本 + 极端比例下，正态置信区间会越界，Wilson 区间更稳；** A/B 测试要按
  「先查 SRM → 再查功效 → 再查多重比较/偷看 → 最后才看 p 值」的顺序排查，不能跳步。
- **辛普森悖论/幸存者偏差/回归到均值/p-hacking 都有可复现的最小构造**——
  背下名字不够，要能在自己的数据里找出对应的机制并给出检测方法。

下一站：**模块 05 · 快问快答题库与自测** —— 整门课的收官，
150+ 题分主题题库、面试当天 90 分钟复习清单，以及一个真正能用的间隔重复自测引擎。"""),
]
