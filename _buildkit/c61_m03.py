# -*- coding: utf-8 -*-
"""C61 模块 03 · 训练与部署调试手册。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "本课模块 01（实验设计）、模块 02（误差分析）；C18 模块 03（检测评测）。C60 是本模块在部署侧的延伸"),
    ("配套 notebook", "<span class='badge cpu'>CPU</span> 03_debug_playbook.ipynb（纯 numpy：可训练的迷你检测头 + 单 batch 过拟合诊断 + 三类管线 bug 的指纹检测）"),
    ("核心参考", "Karpathy《A Recipe for Training Neural Networks》· PyTorch autograd anomaly detection · MMDetection / Detectron2 的 FAQ 与 issue 库"),
    ("预计时长", "读 80 分钟 + 跑 75 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("first-principles", "调试的第一性原理：把「不 work」变成可证伪的假设", "".join([
        P("模块 02 的决策树在第一步就把你送到这里：<strong>mAP ≈ 0，或者 PR 曲线的左端就崩了。</strong>"
          "这一节先讲方法，后面八节是具体的病历。"),
        H3("三条铁律"),
        OL([
            "<strong>先证伪最便宜的假设。</strong>「查一次类别映射」10 分钟，「训一次模型」10 小时。"
            "任何时候都应该先做那个 10 分钟的检查——即使你「觉得」不太可能是它。"
            "<em>「觉得不可能」正是这类 bug 能存活三个月的原因。</em>",
            "<strong>每个假设都要能被一个具体的观察证伪。</strong>「我觉得是学习率问题」不是假设，"
            "「如果是学习率过大，那么第 1 个 iteration 的梯度范数应该 &gt; 100，且权重更新后 loss 会上升」才是假设。"
            "<em>写不出「如果……那么应该观察到……」的句子，说明你还没想清楚。</em>",
            "<strong>二分定位，而不是逐个尝试。</strong>训练链路是 数据 → 增强 → 编码 → 前向 → 损失 → 反传 → 更新 → 评测 八段。"
            "八段里定位一段，二分只要 3 次；逐个试平均要 4 次，最坏 8 次。"
            "<em>更重要的是二分给了你「已排除」的确定性，而逐个试只给你「试过了没用」的焦虑。</em>",
        ]),
        ASCII("""训练链路的八段与「二分定位」的切点

  ①原始数据 → ②增强 → ③标签编码 → ④前向 → ⑤损失 → ⑥反传 → ⑦优化器 → ⑧评测
       │         │         │         │        │        │        │        │
       │         │         │         │        │        │        │        └─ 反解：把预测
       │         │         │         │        │        │        │           喂成 GT，mAP
       │         │         │         │        │        │        │           必须 = 1.0
       │         │         │         │        │        │        └─ 冻结全部权重，
       │         │         │         │        │        │           loss 必须完全不变
       │         │         │         │        │        └─ 数值梯度对拍解析梯度
       │         │         │         │        └─ 把 GT 当成完美预测喂进 loss，
       │         │         │         │           loss 必须 ≈ 0
       │         │         │         └─ **单 batch 过拟合**：loss 必须 → 0
       │         │         └─ 把编码后的目标**解码回框**，与原 GT 逐元素对拍
       │         └─ 关掉全部增强，看指标是否恢复
       └─ 直接可视化 dataloader 吐出来的张量 + 框，画在图上肉眼看

  **每一段都有一个「必须成立的等式」**——这就是可证伪性的具体形态。"""),
        DUAL(
            "为什么「反解检查」这么有效？因为它把一个开放问题（模型为什么不好）变成了一个封闭问题（这个变换是不是可逆的）。"
            "<strong>标签编码 → 解码 → 与原 GT 对拍</strong>，如果对不上，bug 就一定在编码里，不可能在别处；"
            "如果对得上，编码这一段就被<em>彻底排除</em>了，你再也不用回头怀疑它。"
            "<em>调试的进展不是「试了很多东西」，而是「排除了很多可能」。</em>",
            "更严格地说，这是把系统的每一段都包上一个<span class='term'>不变量</span>（invariant）："
            "编码段的不变量是 $\\text{decode}(\\text{encode}(b)) \\approx b$；损失段的不变量是 $\\mathcal{L}(\\text{GT}, \\text{GT}) \\approx 0$；"
            "反传段的不变量是解析梯度与数值梯度在 $10^{-5}$ 量级一致；评测段的不变量是「把 GT 当预测送进去 mAP = 1.0」。"
            "<strong>这些不变量应当写成单元测试常驻仓库，而不是每次出事再手写一遍。</strong>"
            "在 TSR 这种「数据格式多、供应商多、坐标系多」的项目里，这套断言的价值会随着团队规模超线性增长——"
            "<em>因为大多数管线 bug 是在别人改了上游之后引入的，而单元测试是唯一会替你盯着上游的东西。</em>",
        ),
        CALLOUT("intuition", "把本节压成一句话：<strong>不要问「是什么坏了」，要问「哪一段可以被彻底排除」。</strong>"
                "<em>每一次成功的调试，都是把搜索空间对半砍掉若干次的结果。</em>"),
        CALLOUT("danger", "<p><strong>面试里这一节是「资深度探针」。</strong>被问「模型不收敛你怎么查」时，"
                "列举一堆可能原因（学习率、初始化、数据……）只能拿及格分——<em>因为那是背下来的清单，不是流程</em>。"
                "拿高分的回答是给出<strong>顺序与判据</strong>：「我会先跑单 batch 过拟合，因为它一步就能把『数据+模型+损失+优化器』整体判定为可用或不可用；"
                "如果过拟合不了，说明是前四段；如果能过拟合但真实训练不降，说明是数据规模/增强/学习率调度的问题。」"
                "<strong>面试官要听的是你能把搜索空间切开，而不是你知道很多可能性。</strong></p>", "列清单 vs 给流程"),
    ])),

    # ============================================================== 2
    ("nan", "症状一：loss 变成 NaN", "".join([
        P("NaN 的特点是<strong>会传染</strong>：一旦某个张量里出现一个 NaN，它会在下一次前向-反传中污染所有与之相连的权重，"
          "两三个 iteration 之内整个网络就全是 NaN 了。<em>所以「什么时候出现的」比「现在哪里有」重要得多——你必须抓第一现场。</em>"),
        H3("四条通路"),
        TABLE(["通路", "机制", "典型触发条件", "10 分钟内的判据"], [
            ["<strong>① 数值溢出</strong>", "学习率过大 → 权重爆炸 → 激活爆炸 → <code>exp</code>/<code>softmax</code>/<code>log</code> 溢出",
             "lr 比正常大 10–100×；warmup 没生效；混合精度下 fp16 的最大值只有 65504",
             "看 <strong>grad norm 曲线</strong>：NaN 之前一定有一段指数上升。若 grad norm 正常则不是这条"],
            ["<strong>② $\\log 0$ / 除零</strong>", "$-\\log p$ 在 $p$ 被 saturate 成 0 或 1 时；IoU 的分母为 0；标准差为 0 的归一化",
             "自己手写的 BCE/focal 没加 $\\epsilon$；<strong>标注里存在 $x_1 = x_2$ 的退化框</strong>",
             "NaN 在<strong>第一个 iteration 就出现</strong>，且与 lr 无关 → 几乎必然是这条"],
            ["<strong>③ 坏标注</strong>", "$\\log(w/w_a)$ 在 $w \\le 0$ 时；坐标为 <code>inf</code>/<code>nan</code>；类别 id 越界导致索引到未初始化内存",
             "标注 json 里有负宽高、超界坐标、空框；数据增强裁剪后产生零面积框",
             "<strong>固定 seed 后 NaN 出现在同一个 iteration</strong> → 一定是某个特定样本"],
            ["<strong>④ 反传中的除零</strong>", "$\\sqrt{x}$ 在 $x=0$ 处梯度为 $\\infty$；$\\lVert v\\rVert$ 归一化时 $v = 0$；GIoU 的闭包面积为 0",
             "前向不报错、反传才 NaN；常见于自写的 IoU-family 损失",
             "前向的所有中间张量都正常，<strong>只有 <code>.grad</code> 里有 NaN</strong>"],
        ]),
        H3("为什么手写 BCE 一定要用 log-sum-exp 稳定版"),
        P("这是最常见的 ② 号病例，值得写清楚。朴素实现是："),
        MATH("\\mathcal{L} \\;=\\; -y\\log\\sigma(z) \\;-\\; (1-y)\\log\\bigl(1-\\sigma(z)\\bigr), \\qquad \\sigma(z) = \\frac{1}{1+e^{-z}}"),
        P("当 $e^{-z}$ 相对 1 小于机器精度时，$1+e^{-z}$ 被舍入成 $1$，于是 $\\sigma(z)$ 被<strong>精确地</strong>舍入成 <code>1.0</code>——"
          "<strong>float32 的临界点约 $z = 17$，float64 约 $z = 37$</strong>（notebook 会把这两个断点逐点打出来）。"
          "此时 $\\log(1-\\sigma(z)) = \\log 0 = -\\infty$；如果这个样本的标签恰好是 $y=0$，loss 就是 $+\\infty$，反传立刻产出 NaN。"
          "<strong>注意这不是「数值不准」，是「结果完全错误」——而且它只在某些样本上触发，所以看平均 loss 是发现不了的。</strong>稳定形式是："),
        MATH("\\mathcal{L} \\;=\\; \\max(z,0) \\;-\\; z\\,y \\;+\\; \\log\\bigl(1 + e^{-|z|}\\bigr)"),
        P("这个式子对任意 $z$ 都不会溢出（$e^{-|z|} \\le 1$），且与朴素式在数学上完全等价。"
          "<em>notebook 里会把两者在 $z$ 从 10 到 100 的范围内逐点对比，看着朴素版在 $z = 37$ 附近断掉。</em>"),
        DUAL(
            "定位 NaN 的标准姿势是<strong>「前向逐层挂哨兵」</strong>：在每一层输出后记录 <code>(有无 NaN, min, max)</code>，"
            "找到<em>第一个</em>出现 NaN 的位置。PyTorch 里可以用 <code>torch.autograd.set_detect_anomaly(True)</code>（会慢很多，只在复现时开）"
            "或者给每个模块挂 forward hook。<strong>关键是不要在 NaN 已经扩散之后才去看——那时候到处都是 NaN，信息量为零。</strong>",
            "工程上更彻底的做法是把哨兵做成<strong>常驻的、低成本的</strong>：每 $N$ 个 iteration 记录一次全局 grad norm、"
            "各层激活的 <code>max(|x|)</code>、以及 loss 的各个分项（cls / box / obj 分开记）。"
            "<em>这样 NaN 出现时你不需要复现——历史曲线里已经写着答案。</em>"
            "特别地，<strong>把 loss 的各分项分开记录能一眼区分通路 ①③</strong>："
            "只有 box 分项炸而 cls 正常，几乎必然是坏标注（$\\log(w/w_a)$ 那条）；"
            "所有分项同时炸，才是学习率导致的整体发散。<em>这个「分项记录」的成本接近 0，但省下的排查时间以小时计。</em>",
        ),
        CALLOUT("warn", "<p><strong>TSR 项目里 ③ 号通路格外高发</strong>，因为交通标志的标注常常来自多个供应商、多个年份、多种工具。"
                "真实见过的坏数据：宽或高为 0 的框（标注员点了一下就保存）、坐标是归一化值但字段名写着 <code>pixel</code>、"
                "被遮挡标志的框被标成负坐标、以及<strong>一张图里同一块牌子被标了两次且其中一次类别不同</strong>。"
                "<em>防御手段只有一个：在 Dataset 的 <code>__getitem__</code> 里加断言</em>——"
                "<code>assert (w &gt; 1) and (h &gt; 1) and 0 &lt;= x1 &lt; x2 &lt;= W</code>，"
                "并且<strong>在断言里打印文件名</strong>，否则你只知道「有坏数据」，不知道是哪张。</p>", "坏标注不是小概率事件"),
        CALLOUT("intuition", "<strong>NaN 的第一个问题永远是「它是第几个 iteration 出现的」。</strong>"
                "<em>第 0–1 个 iteration 出现 ⇒ 数据或损失的实现问题；训练几百步后才出现 ⇒ 学习率/发散；"
                "固定 seed 后总在同一步出现 ⇒ 某个特定样本。</em>这一个问题就能砍掉三分之二的可能性。"),
    ])),

    # ============================================================== 3
    ("flat-loss", "症状二：loss 不降（或降一点就躺平）", "".join([
        P("比 NaN 更折磨人，因为它不报错。<strong>四个嫌疑人，按「查起来由便宜到贵」排序。</strong>"),
        TABLE(["嫌疑人", "特征", "验证方法（都在 10 分钟内）", "修法"], [
            ["<strong>学习率</strong>", "太小：loss 缓慢线性下降，怎么都到不了低位。<br>太大：loss 剧烈震荡或先降后升",
             "<strong>lr range test</strong>：从 $10^{-7}$ 指数增长到 $10$，画 loss-lr 曲线，取「下降最陡」处的 1/10",
             "改 lr；检查 warmup 是否真的生效（打印前 100 步的实际 lr）"],
            ["<strong>标签映射错</strong>", "loss 会降一点点然后卡在「预测先验分布」的水平，<strong>mAP ≈ 0</strong>",
             "把一个 batch 的编码后目标<strong>解码回框与类别名</strong>，画到图上肉眼看",
             "见第 4 节"],
            ["<strong>数据没打乱</strong>", "loss 曲线呈<strong>周期性锯齿</strong>（周期 = 一个 epoch 或一个数据分片）",
             "打印前 200 个样本的类别序列；<code>shuffle=True</code> 是否被 <code>sampler</code> 覆盖了",
             "开 shuffle；分布式下确认 <code>DistributedSampler.set_epoch(epoch)</code> 被调用"],
            ["<strong>冻错了层</strong>", "loss 完全水平，或只在小范围抖动；<strong>参数量统计里可训练参数远小于预期</strong>",
             "<code>sum(p.numel() for p in model.parameters() if p.requires_grad)</code> 打出来对一遍；<br>再看 optimizer 的 <code>param_groups</code> 里到底有几个张量",
             "解冻；注意 <code>requires_grad=False</code> 与「不在 optimizer 里」是两回事"],
        ]),
        H3("「数据没打乱」为什么会让 loss 躺平"),
        P("如果一个 batch 里全是同一类（比如连续 64 帧同一段路的限速 60），那么<strong>这个 batch 的最优解就是「无论看到什么都输出限速 60」</strong>。"
          "下一个 batch 全是指路牌，最优解又变成「都输出指路牌」。"
          "于是模型在两个互相矛盾的解之间来回跳，<em>梯度互相抵消，平均下来什么也没学到</em>。"
          "<strong>TSR 的数据天然是按行车序列采集的，相邻帧极度相关——这使得「忘记打乱」在 TSR 项目里的后果比在 ImageNet 上严重得多。</strong>"),
        DUAL(
            "「冻错了层」有一个非常隐蔽的变体：<strong>你设了 <code>requires_grad=False</code>，但 optimizer 是在设之前构造的</strong>。"
            "此时参数确实不产生梯度，但如果 optimizer 带 weight decay，它<em>仍然会每步把这些权重乘以 $(1-\\lambda\\eta)$ 往零缩</em>——"
            "结果是「冻结」的 backbone 被慢慢地衰减成零。<em>症状是训练前几百步正常，然后指标开始不可逆地下滑。</em>",
            "反过来的坑同样常见：<strong>BatchNorm 的统计量不受 <code>requires_grad</code> 控制</strong>。"
            "把 backbone 「冻住」但忘了 <code>model.eval()</code> 或忘了把 BN 换成 <code>FrozenBatchNorm</code>，"
            "BN 的 <code>running_mean/var</code> 会继续被新数据更新，于是「冻结的 backbone」的输出分布在训练中一直在变。"
            "<em>这在 TSR 的微调场景里很致命</em>：你在 COCO 预训练权重上微调，本意是保住通用特征，"
            "结果 BN 统计被几千张全是路面和天空的图带偏，<strong>通用特征反而被破坏得比不冻还厉害</strong>。"
            "<strong>检查方法很简单：训练前后把 backbone 某个 BN 层的 <code>running_mean</code> 打出来对比，变了就说明没真冻住。</strong>",
        ),
        CALLOUT("warn", "lr range test 有一个容易忽略的前提：<strong>它必须在「已经确认数据管线正确」之后做</strong>。"
                "如果标签是错的，任何学习率下 loss 都降不下去，你会得出「所有 lr 都不行」的结论，然后浪费一天在调 lr 上。"
                "<em>这就是为什么第 7 节的「单 batch 过拟合」应该排在 lr range test 之前——它能一次性判定「数据+模型+损失」这一整块是否可用。</em>"),
    ])),

    # ============================================================== 4
    ("map-zero", "症状三：mAP 恒为 0（三大元凶占绝大多数）", "".join([
        P("这是检测任务独有的、最经典的症状：<strong>loss 在正常下降、可视化的框看起来也在目标附近，但评测出来 mAP 就是 0.00x。</strong>"
          "工业界的经验分布是：<strong>类别 ID 偏移、坐标格式弄反、评测集与训练集类别表不一致——这三个加起来占了绝大多数。</strong>"
          "<em>它们的共同点是：都不会报错，都不会让 loss 异常，只在最终指标上表现为「一切归零」。</em>"),
        ASCII("""mAP ≈ 0 的三分钟分诊

  ┌────────────────────────────────────────────────────────────────┐
  │ 检查 A：把预测类别整体 +1 / -1，重算 mAP                        │
  │   mAP 突然正常  ==>  【类别 ID 偏移】                            │
  │   常见根因：COCO 的 category_id 从 1 开始，模型输出从 0 开始；   │
  │             有的框架把 background 放在 index 0，有的不放        │
  └────────────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────────────────────┐
  │ 检查 B：把预测框按 cxcywh->xyxy（或 xywh->xyxy、yxyx->xyxy）    │
  │         转换后重算「与最近 GT 的 IoU」分布                      │
  │   平均 IoU 从 0.0x 跳到 0.8+  ==>  【坐标格式弄反】              │
  │   指纹：转换前的框**面积中位数与 GT 差一个数量级**，            │
  │         且框中心系统性偏向左上（xywh 被当成 xyxy 时）           │
  └────────────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────────────────────┐
  │ 检查 C：diff 训练与评测两侧的类别表（顺序！不只是集合）          │
  │   两边 sorted() 的结果不同  ==>  【类别表不一致】                │
  │   指纹：**混淆矩阵是一个置换矩阵**——每一行的质量都集中在        │
  │         某一个非对角格子上，且这个映射是一一对应的              │
  └────────────────────────────────────────────────────────────────┘

  三条都过了才允许怀疑模型。**顺序不要换：A/B/C 各 3 分钟，训一次模型 10 小时。**"""),
        H3("为什么类别表不一致这么隐蔽"),
        P("因为它经常是<strong>由「正确的代码」产生的</strong>。典型场景：训练侧用 <code>sorted(os.listdir(ann_dir))</code> 得到类别顺序，"
          "评测侧用 <code>json.load()</code> 里 <code>categories</code> 数组的原始顺序。两边都没错，但顺序不同。"
          "<em>更隐蔽的是：某个类在训练集里出现过、在评测集里一个样本都没有，于是评测侧的类别表少了一项，后面所有 index 全部左移一位。</em>"),
        TABLE(["元凶", "为什么发生", "它<strong>不会</strong>表现为什么", "根治手段"], [
            ["<strong>类别 ID 偏移</strong>", "COCO 的 <code>category_id</code> 从 1 开始；Pascal VOC 把 background 当 0 类；<br>不同框架对「有没有 background 类」约定不同",
             "不会让 loss 异常（模型照样能学，只是学到了偏移一位的映射）",
             "把 <strong>id ↔ name 的映射表</strong>随权重一起序列化，评测时从权重里读，不从配置文件读"],
            ["<strong>坐标格式</strong>", "<code>xyxy</code> / <code>xywh</code>（左上+宽高） / <code>cxcywh</code>（中心+宽高） / 归一化 vs 像素 / <code>yxyx</code>（TF 系）",
             "不会报错——四个数就是四个数，任何格式都能塞进去",
             "在数据结构里<strong>带上格式标签</strong>（<code>Boxes(fmt='xyxy')</code>），转换必须显式调用"],
            ["<strong>类别表不一致</strong>", "两侧从不同来源、用不同顺序构造类别列表；某类在某个 split 里样本数为 0",
             "不会让训练侧有任何异常，训练指标一路正常",
             "<strong>类别表只允许有一个来源</strong>（单一 <code>classes.json</code>），并把它的 md5 写进模型卡"],
        ]),
        DUAL(
            "为什么「类别 ID 偏移」会让 mAP 精确地掉到 0 而不是掉一半？因为 AP 是<strong>逐类算的</strong>。"
            "偏移一位之后，类 $c$ 的预测全部落进类 $c{+}1$ 的评测里；而类 $c{+}1$ 的 GT 与类 $c$ 的目标在图像上完全不重叠，"
            "所以 IoU 全是 0，<em>每一类的 AP 都是 0，平均下来还是 0</em>。"
            "<strong>这也解释了一个反直觉的现象：偏移 1 位和偏移 5 位的后果完全一样，都是 0。</strong>所以「mAP 是 0 而不是 0.3」本身就是强烈的信号——"
            "<em>模型能力问题不会让指标精确归零，只有映射问题会。</em>",
            "坐标格式的情况稍有不同，值得单独想清楚。把 <code>cxcywh</code> 直接当 <code>xyxy</code> 用会得到 "
            "$(c_x, c_y, w, h)$ 这样一个「框」：当 $w &lt; c_x$ 或 $h &lt; c_y$ 时它的宽高为负，面积按 <code>clip(x2-x1,0)</code> 算出来是 0，"
            "<strong>于是 IoU 恒为 0，mAP 精确为 0</strong>；而当目标靠近图像左上角时 $w &gt; c_x$，会得到一个「从中心点延伸到 $(w,h)$」的怪框，"
            "IoU 是个很小的正数。<em>所以「坐标格式弄反」的指纹不只是 IoU 低，更关键的是<strong>「IoU 恰好等于 0 的比例接近 100%」</strong></em>——<strong>而模型定位不准时这个比例几乎是 0</strong>（框再歪也总有些许重叠，IoU 是连续分布）。"
            "<strong>notebook 里会把「正常 / cxcywh 当 xyxy / xywh 当 xyxy / yxyx 当 xyxy」四种情况的指纹并排打出来，一眼就能分辨。</strong>",
        ),
        CALLOUT("danger", "<p><strong>这是 TSR / 检测岗位的高频面试题：「mAP 一直是 0，你怎么查？」</strong></p>"
                "<p><em>不合格的回答</em>：「我会检查数据、检查代码、打印一下看看。」</p>"
                "<p><em>拿分的回答</em>：「我会按三个 3 分钟的检查走。<strong>第一，把预测类别整体 ±1 重算 mAP</strong>——"
                "如果突然正常就是类别 ID 偏移，COCO 的 category_id 从 1 开始是最常见的来源。"
                "<strong>第二，把预测框按 cxcywh→xyxy 转换后重算 IoU 分布</strong>——如果平均 IoU 从 0.03 跳到 0.85 就是坐标格式。"
                "而且格式错的指纹很特别：IoU 分布是『大量精确的 0 + 少量小正值』的双峰，不是模型定位不准的单峰。"
                "<strong>第三，diff 训练与评测两侧类别表的<u>顺序</u></strong>——如果混淆矩阵是个置换矩阵，就是这个。"
                "这三条覆盖绝大多数情况，都不用重训；三条都过了我才会去怀疑模型。」</p>"
                "<p><strong>加分句</strong>：「而且 mAP 恰好是 0 而不是 0.3 本身就是线索——模型能力问题不会让指标精确归零。」</p>", "背清单 vs 给判据"),
    ])),

    # ============================================================== 5
    ("fingerprints", "数据管线 bug 的特征指纹", "".join([
        P("上一节的三大元凶都是「让 mAP 归零」的重症。还有一类更麻烦：<strong>指标掉了但没归零</strong>——"
          "模型照样能跑，指标从 0.72 掉到 0.58，你会以为是「这次训练没调好」，于是开始调超参，"
          "然后在一个有 bug 的管线上做三个月的架构消融。"),
        P("<strong>对抗这类 bug 的唯一有效手段是「指纹」：每种 bug 都有一组它<em>独有的</em>可观测特征。</strong>"
          "认识指纹，你就能从症状直接反推病因，而不是逐个试。"),
        TABLE(["bug", "指标表现", "<strong>独有指纹</strong>", "一行验证"], [
            ["<strong>类别 ID 偏移</strong>", "mAP ≈ 0",
             "混淆矩阵的质量集中在<strong>偏离对角线 $k$ 格的次对角线</strong>上；<br>把预测类别 $-k$ 后指标完全恢复",
             "<code>argmax_k Σ_i cm[i, i+k]</code>，若 $k \\ne 0$ 则中招"],
            ["<strong>坐标格式弄反</strong>", "mAP ≈ 0",
             "<strong>IoU 恰好为 0 的比例 ≈ 100%</strong>（定位不准时该比例 ≈ 0）；<br>预测框的有效面积中位数塌成 0（宽或高为负被 clip）",
             "对候选格式各试一遍，取 <code>mean IoU</code> 最大的"],
            ["<strong>x/y 互换（yxyx）</strong>", "mAP ≈ 0（非方形图更明显）",
             "<strong><code>corr(pred_cx, gt_cy)</code> 很高而 <code>corr(pred_cx, gt_cx)</code> 很低</strong>——散点图是转置的",
             "算两个相关系数比大小"],
            ["<strong>通道顺序 BGR/RGB</strong>", "mAP 掉 5–15 点，<strong>但不归零</strong>",
             "<strong>颜色语义类别掉点远大于中性色类别</strong>：红色禁令牌与蓝色指示牌互相错分，白底黑字的指路牌几乎不掉；<br>输入张量的 R/B 通道均值与训练集统计互换",
             "把输入 <code>[..., ::-1]</code> 后重测，指标恢复即确诊"],
            ["<strong>归一化 mean/std 不一致</strong>", "掉 3–20 点不等",
             "<strong>所有类别均匀掉点</strong>（没有颜色语义的偏向）；<br>第一层卷积输出的激活分布整体平移或缩放",
             "dump 一个 batch，比对 <code>x.mean(axis=(0,1,2))</code> 与训练端"],
            ["<strong>resize 插值/对齐不一致</strong>", "掉 1–5 点，<strong>小目标掉得多</strong>",
             "<strong>按像素尺寸分桶后，&lt;16 px 桶掉 10+ 点、&gt;64 px 桶几乎不掉</strong>",
             "同一张图两边 resize 后逐元素 diff，看 max abs error"],
        ]),
        H3("为什么「通道顺序」的指纹是类别相关的"),
        P("这是本节最有价值的一条，也是 TSR 特有的洞察。<strong>交通标志的颜色是语义</strong>："
          "红色 = 禁令、蓝色 = 指示、黄色 = 警告、绿色 = 高速指路。R 与 B 互换会把红色变成蓝色、蓝色变成红色——"
          "<em>一个禁令标志在模型眼里变成了指示标志</em>。而白底黑字的指路牌 R≈G≈B，交换前后几乎不变。"),
        ASCII("""BGR/RGB 弄反的类别指纹（notebook 会实测这张表）

  类别组              颜色特征          交换 R/B 后          准确率变化
  ─────────────────────────────────────────────────────────────────────
  红色禁令（限速/禁止）  R 高 B 低    ->   R 低 B 高  变蓝     ▼▼▼ 崩到接近 0
  蓝色指示（直行/环岛）  B 高 R 低    ->   B 低 R 高  变红     ▼▼▼ 崩到接近 0
  黄色警告（注意行人）   R 高 G 高 B 低 -> R 低 G 高 B 高 变青   ▼▼  大幅下降
  白底黑字（指路牌）    R≈G≈B       ->   R≈G≈B     几乎不变  ▬   基本不掉
  ─────────────────────────────────────────────────────────────────────
  **这个「掉点的类别选择性」就是指纹。**

  对照：如果是 mean/std 归一化写错，所有类别会**均匀**掉点，
        因为它不改变通道之间的相对关系，只是整体平移/缩放。

  => 看到「颜色类崩、中性色类不掉」就直接去查通道顺序，不要调超参。"""),
        DUAL(
            "指纹思维的价值在于它把调试从<strong>「顺序搜索」变成「哈希查表」</strong>。"
            "没有指纹时，你面对 6 种可能的 bug 要平均试 3.5 次，每次可能要重训或重跑评测；"
            "有指纹时，你看一眼「掉点的类别选择性」就能定位。"
            "<em>而且指纹是可以自动化的——把这几条检查写成一个脚本，每次评测完自动跑一遍，它会主动告诉你「疑似通道顺序问题」。</em>",
            "更深一层：<strong>好的指纹必须是「充分区分」的，而不只是「相关」的。</strong>"
            "「mAP 掉了」和通道顺序相关，但它和另外五种 bug 也相关，所以它不是指纹。"
            "「颜色语义类崩而中性色类不掉」只和通道顺序相关，所以它是指纹。"
            "<em>设计指纹的方法是问：这个 bug 的机制会在哪个维度上产生<strong>不对称</strong>的影响？</em>"
            "通道顺序 → 颜色维度不对称；resize 不一致 → 尺寸维度不对称；类别表错位 → 类别维度上呈置换结构；"
            "坐标格式 → IoU 分布形态不对称。<strong>「找不对称」是构造指纹的通用方法，也是本节最可迁移的东西。</strong>",
        ),
        CALLOUT("warn", "<p><strong>一个真实的、极难查的组合 bug</strong>：训练用 PIL 读图（RGB）+ <code>cv2.resize</code>（默认 INTER_LINEAR），"
                "推理用 <code>cv2.imread</code>（BGR）+ PIL 的 <code>resize</code>（默认 BICUBIC）。"
                "<em>两个 bug 叠加时，指纹会互相干扰</em>——通道错导致颜色类崩、插值错导致小目标崩，"
                "你看到的是「颜色类的小目标崩得特别厉害」，很容易被误判成「小目标问题」而去加 P2 层。"
                "<strong>所以指纹检查必须是「逐项独立」的：一次只改一个变量重测</strong>，"
                "而不是看着最终指标猜。<em>这正好呼应模块 01 的单变量原则。</em></p>", "组合 bug 会污染指纹"),
    ])),

    # ============================================================== 6
    ("train-val-gap", "症状四：训练正常但验证极差；过拟合与欠拟合的区分", "".join([
        P("「训练 loss 一路下降到 0.05，验证 mAP 只有 0.11」——这个症状有两个完全不同的病因，"
          "而<strong>把它们搞混是初级工程师最典型的失误</strong>：一个需要更多数据/更强正则，另一个需要修 bug。"),
        TABLE(["", "真·过拟合", "<strong>验证管线不一致</strong>（伪过拟合）"], [
            ["训练指标", "很好", "很好"],
            ["验证指标", "差，但<strong>不至于崩</strong>（比如 0.72 → 0.55）", "<strong>崩到接近随机</strong>（0.72 → 0.11）"],
            ["<strong>关键判据</strong>", "把<strong>训练集</strong>当验证集跑评测流程 → 指标仍然很好", "把<strong>训练集</strong>当验证集跑评测流程 → <strong>指标同样崩</strong>"],
            ["曲线形态", "验证 loss 先降后升，有明确拐点", "验证 loss <strong>从第一个 epoch 就是坏的</strong>，没有拐点"],
            ["随数据量", "加数据会改善", "加数据完全无效"],
            ["常见根因", "数据太少、模型太大、增强太弱、训太久", "验证侧的 resize/归一化/通道/letterbox 与训练侧不同；<br>评测时忘了 <code>model.eval()</code>（BN 用了 batch 统计）；<br>验证集类别表不一致（见第 4 节）"],
        ]),
        P("<strong>那个关键判据值得单独强调</strong>：把训练集喂进<em>验证的那条代码路径</em>去评测。"
          "如果指标同样崩，那就与「泛化」毫无关系——数据模型都是同一批，唯一的变量就是那条代码路径。"
          "<em>这是一个能在 20 分钟内做完、并且结论是二值的实验，收益极高。</em>"),
        H3("过拟合与欠拟合的信号"),
        TABLE(["信号", "欠拟合", "过拟合"], [
            ["训练 loss", "高，且还在下降（没到平台）", "很低，接近 0"],
            ["训练-验证 gap", "小", "<strong>大且持续扩大</strong>"],
            ["加强增强", "指标<strong>变差</strong>", "指标变好"],
            ["加大模型", "指标变好", "指标变差或不变"],
            ["加数据", "帮助有限", "<strong>帮助最大</strong>"],
            ["<strong>单 batch 过拟合</strong>", "<strong>做不到</strong>（说明容量/优化/实现有问题）", "轻松做到"],
            ["检测任务特有", "框普遍偏大偏中心（回归退化到均值）；分类分数普遍偏低", "训练集上框极准，验证集上小目标与罕见类崩得特别厉害"],
        ]),
        DUAL(
            "检测任务的欠拟合有一个很有辨识度的表现：<strong>回归分支退化到「输出训练集框的平均值」</strong>。"
            "表现为所有预测框尺寸差不多、位置都靠近图像中心。"
            "<em>因为在没学到有效特征时，最小化 L1/GIoU 损失的最优常数解就是训练集框分布的中位数。</em>"
            "<strong>看到「所有框长得一样」，先别怀疑标签分配，先怀疑模型压根没在学。</strong>",
            "TSR 场景里还有一类介于两者之间的情况值得警惕：<span class='term'>虚假过拟合</span>——"
            "模型不是记住了训练样本，而是<strong>记住了训练集里的一个捷径特征</strong>。"
            "<em>例如某个采集批次的图像都有相同的相机 ISP 风格，模型学会了「这种色调下出现的圆形物体就是限速牌」；"
            "换到另一个批次（另一台车、另一个国家），这个捷径失效，指标崩塌。</em>"
            "<strong>它的判据是：验证集按「采集批次」分桶后，同批次内的验证指标好、跨批次的差。</strong>"
            "这不是加数据能解决的（加同批次的数据没用），也不是正则化能解决的——"
            "<strong>唯一的解法是让训练数据在那个捷径维度上具有多样性</strong>（多车型、多时段、多地域），"
            "或者用增强主动破坏那个捷径（色彩抖动、ISP 模拟）。<em>这直接连到 C56 的增强设计与 C58 的数据闭环。</em>",
        ),
        CALLOUT("danger", "<p><strong>最容易在面试里丢分的一句话：「验证集上差就是过拟合」。</strong>"
                "面试官会立刻追问「你怎么排除是验证管线的问题」。"
                "<em>准备好那个判据</em>：<strong>「我会先把训练集喂进验证的代码路径跑一遍——如果指标同样崩，那和泛化没关系，是管线；"
                "如果指标依然很好，才是真的泛化问题。这个实验 20 分钟能做完，结论是二值的。」</strong></p>", "别把管线问题说成泛化问题"),
    ])),

    # ============================================================== 7
    ("overfit-one-batch", "万能诊断法：先把一个 batch 过拟合", "".join([
        P("如果这门课你只能记住一个技巧，就记这个。<strong>拿 8–32 个样本，关掉所有增强、关掉正则、关掉 dropout、关掉学习率衰减，"
          "反复在这一个 batch 上训练几百到几千步。训练 loss 必须掉到接近 0，mAP 必须接近 1.0。</strong>"),
        H3("它为什么这么强"),
        P("因为它<strong>一次性判定了「数据 → 增强 → 编码 → 前向 → 损失 → 反传 → 优化器」这一整块是否可用</strong>，"
          "而且把「泛化」这个最难的变量彻底移出了方程。"),
        MATH("\\text{一个足够容量的模型在 } n \\text{ 个样本上，最优训练损失应当} \\to 0 \\quad (n \\ll \\text{参数量})"),
        P("这句话是<strong>无条件成立的</strong>——它不依赖数据质量、不依赖任务难度、不依赖超参调得好不好。"
          "所以<strong>如果做不到，就一定有 bug</strong>，而不是「这个任务比较难」。这个「无条件」是它作为判据的全部价值所在。"),
        ASCII("""单 batch 过拟合的结果 -> 结论

  loss -> ~0，mAP -> ~1.0
      ==> 数据/编码/前向/损失/反传/优化器 **全部可用**
          问题一定在：数据规模、增强、学习率调度、正则、验证管线
          （搜索空间瞬间砍掉一半以上）

  loss 完全水平（一动不动）
      ==> 梯度没有流到权重
          查：requires_grad / optimizer.param_groups / 是否忘了 loss.backward()
              / 是否 detach 了 / lr 是否为 0 / 是否有 torch.no_grad() 包住了

  loss 下降但停在某个正数（例如二分类停在 0.693 = ln 2）
      ==> 模型只能输出常数
          查：特征全被 ReLU 杀死（死亡神经元）/ 输入全零 / 归一化把方差归零了
              / 只有 bias 可训练

  loss 下降到 0 但 mAP 仍然是 0
      ==> **训练侧对、评测侧错** —— 直接跳到第 4 节的三大元凶
          （这是最有价值的一种结果：它把 bug 精确锁在评测代码里）

  loss 剧烈震荡 / 变 NaN
      ==> 学习率过大或数值实现有问题（第 2 节）"""),
        TABLE(["检查项", "为什么必须关掉", "忘了关的后果"], [
            ["数据增强", "随机增强让「同一个 batch」每步都不同，等于换了任务", "loss 降不到 0，你会误判为有 bug"],
            ["Dropout / DropPath", "注入随机性，同上", "loss 在某个正数附近抖动"],
            ["Weight decay", "把权重往零拉，与「记住这几个样本」相冲突", "loss 停在一个非零平台"],
            ["<strong>学习率 warmup/衰减</strong>", "几百步的实验里 warmup 可能还没结束，lr 还接近 0", "<strong>loss 几乎不动，被误判成「梯度不流」</strong>"],
            ["EMA / 模型平均", "评测用的是 EMA 权重，而 EMA 需要很多步才追上", "训练 loss 到 0 但评测指标很差"],
            ["shuffle", "只有一个 batch，无所谓，但要确保每步用的是<strong>同一批</strong>数据", "实际上在遍历数据集，等于普通训练"],
        ]),
        DUAL(
            "还有一个进阶用法：<strong>用「能过拟合多少个样本」来估计模型容量与实现质量</strong>。"
            "先过拟合 1 个样本，再 8 个、64 个、512 个。<em>如果 8 个能过拟合而 64 个不能，说明有一个与 batch 大小相关的 bug</em>"
            "（比如损失里错误地对 batch 维度求了 max 而不是 mean，或者标签分配在多目标时出错）。"
            "<strong>这个「阶梯式过拟合」能定位到很多单样本测不出来的问题。</strong>",
            "在检测任务里还要额外注意一点：<strong>「过拟合一个 batch」在有标签分配（label assignment）的检测器里不是平凡的</strong>。"
            "如果分配策略有 bug——比如所有 anchor 都被判成负样本、或者正样本阈值设得过高——"
            "<em>那么无论训多久，分类分支都只会学到「全是背景」，loss 会降到「全预测背景」对应的值然后不动</em>。"
            "<strong>所以检测的单 batch 过拟合必须同时打印「每步分到的正样本数」</strong>："
            "如果正样本数是 0 或者远小于 GT 数，问题就在分配，而不在网络。"
            "<em>这一条在 TSR 上尤其重要，因为小目标（8–20 px）在 IoU 阈值 0.5 的静态分配下天然极难匹配到正样本</em>（C57 模块 03 展开），"
            "<strong>「正样本数 = 0」在 TSR 项目里是常态而不是异常</strong>。",
        ),
        CALLOUT("intuition", "<strong>单 batch 过拟合是检测调试里唯一的「无条件必须成立」的实验。</strong>"
                "<em>它成立时你排除了半个系统；它不成立时你知道 bug 一定在前半段。没有任何其他实验有这么高的信息量/成本比。</em>"),
        CALLOUT("warn", "常见的自欺欺人：<strong>「我的 loss 降到 0.02 了，应该没问题」</strong>。"
                "在检测里 loss 是多项之和（cls + box + obj/dfl），<em>某一项塌成 0 而另一项没动，总和看起来也会很小</em>。"
                "<strong>必须分项打印，并且必须同时看 mAP</strong>——mAP 在单 batch 上应该达到 0.95 以上，"
                "达不到就说明「loss 低」和「预测对」之间断了链，那个断点通常就在后处理或评测里。"),
    ])),

    # ============================================================== 8
    ("distributed-repro", "分布式不一致与复现失败的排查顺序", "".join([
        P("单卡跑通之后，多卡上出现「指标比单卡低 2 个点」「每次跑结果都不一样」「某张卡 hang 住」——"
          "<strong>这类问题的特点是：它们几乎从不报错，只是让结果慢慢变得不可信。</strong>"),
        TABLE(["问题", "机制", "症状", "检查/修法"], [
            ["<strong>BN 不同步</strong>", "每张卡用自己的 mini-batch 算 BN 统计。8 卡 × batch 2 = 每张卡只有 2 个样本的统计量",
             "多卡指标低于单卡；<strong>per-GPU batch 越小差距越大</strong>",
             "换 <code>SyncBatchNorm</code>；或增大 per-GPU batch；或换 GN/LN。<em>per-GPU batch ≥ 16 时通常不必同步</em>"],
            ["<strong>随机种子相同</strong>", "所有 rank 用同一个 seed → <strong>数据增强在所有卡上完全一样</strong>",
             "等效 batch 的多样性只有名义值的 $1/N$；训练比预期慢、指标偏低",
             "<code>seed = base_seed + rank</code>；<strong>DataLoader worker 还要再叠一层 worker_id</strong>"],
            ["<strong>数据分片重叠</strong>", "sampler 配置错误导致同一样本被多张卡拿到；或 <code>drop_last=False</code> 时补齐样本重复",
             "一个 epoch 的实际样本数 ≠ 数据集大小；<strong>指标虚高</strong>（重复样本相当于变相过采样）",
             "打印 <code>len(sampler) * world_size</code> 与数据集大小对比；评测时用 <strong>去重后的</strong> 结果"],
            ["<strong>忘了 <code>set_epoch</code></strong>", "<code>DistributedSampler</code> 的打乱种子固定 → 每个 epoch 的划分完全相同",
             "每个 epoch 每张卡看到的都是同一批数据；<strong>loss 曲线呈现强周期性</strong>",
             "每个 epoch 开头调 <code>sampler.set_epoch(epoch)</code>——这是最常忘的一行"],
            ["<strong>梯度累积与 loss 缩放</strong>", "累积 $k$ 步时 loss 没除以 $k$，等效学习率变成 $k$ 倍",
             "换了累积步数之后训练发散或指标变化很大",
             "确认 loss 归一化口径；<strong>换累积步数时等效 lr 要跟着变</strong>"],
            ["<strong>评测只在 rank 0 做</strong>", "各 rank 的结果没有 gather 完全，或 gather 时顺序不定",
             "多卡评测结果与单卡不一致，且每次略有不同",
             "评测结果按样本 id 排序后再算指标；<strong>指标计算只在一个 rank 上做</strong>"],
        ]),
        H3("复现失败的排查顺序"),
        P("「同一份代码、同一份配置，昨天 0.72、今天 0.68」——按下面的顺序查，<strong>每一步都比下一步便宜</strong>："),
        OL([
            "<strong>先确认这不是种子方差。</strong>检测任务同配置不同种子的 mAP 波动典型是 ±0.2–0.5 个点（模块 01）。"
            "<em>0.72 vs 0.68 完全可能就是噪声。先跑 3–5 个种子看分布，再决定要不要查。</em>"
            "<strong>这一步排除掉的「bug」占了所有「复现失败」报告的一大半。</strong>",
            "<strong>代码版本。</strong><code>git status</code> 是否干净？有没有未提交的本地修改？依赖库版本有没有变（"
            "<code>pip freeze</code> diff）？<em>「我只改了个打印」是经典的最后遗言。</em>",
            "<strong>数据版本。</strong>数据集有没有被人补标/修标？标注文件的 md5 对得上吗？"
            "<em>在 TSR 项目里数据是持续回流的，「同一个数据集」这个说法本身就需要版本号才有意义。</em>",
            "<strong>随机性来源。</strong>seed 设了几处（python / numpy / 框架 / cudnn / DataLoader worker）？"
            "<code>cudnn.benchmark=True</code> 会让算法选择依赖硬件状态；某些 GPU 算子本身<strong>非确定性</strong>（atomicAdd 的浮点加法不满足结合律）。"
            "<em>完全确定性通常要付 10–30% 的速度代价，所以多数团队选择「不追求逐位复现，只追求指标分布可复现」。</em>",
            "<strong>环境。</strong>驱动 / CUDA / 框架版本 / 硬件型号。<em>换卡会改变 kernel 选择，也会改变浮点累加顺序。</em>",
            "<strong>最后才是「代码里有 bug」。</strong>",
        ]),
        DUAL(
            "第 1 步值得再强调一次：<strong>大多数「复现失败」根本不是失败，是没有理解方差。</strong>"
            "一个只跑了单种子的实验，它的 mAP 是一个随机变量的<em>一次抽样</em>，"
            "而你在拿两次抽样比大小。<em>「昨天 0.72 今天 0.68」这句话在统计上是没有信息的，除非你知道 $\\sigma$。</em>",
            "反过来，真正需要「逐位复现」的场景也是存在的，而且在车企里很重要：<strong>安全相关的模型证据链</strong>。"
            "当一个模型要进入量产、要过功能安全评审时，「这份权重是由这份代码 + 这份数据 + 这个环境产生的」"
            "必须是可验证的，否则出了事故无法归因。<em>此时可复现性不再是调试便利，而是合规要求。</em>"
            "<strong>工程上的做法是分层：日常迭代允许非确定性（换速度），发布候选版本必须在确定性模式下重跑一遍并归档</strong>"
            "（固定 seed、<code>cudnn.deterministic=True</code>、固定镜像、固定数据快照）。"
            "<em>这套东西在 C37 的 MLOps 课里叫「实验记录的最小必要字段」，在这里叫「出事之后你还能不能说清楚」。</em>",
        ),
        CALLOUT("warn", "<p><strong>DataLoader worker 的种子是一个经典事故</strong>，值得单独记住："
                "多个 worker 进程会各自继承主进程的 numpy 随机状态，如果不显式给每个 worker 设不同的种子，"
                "<strong>所有 worker 会生成完全相同的随机增强</strong>。"
                "<em>症状是：增强的有效多样性只有名义值的 $1/N_{\\text{workers}}$，指标莫名其妙比预期低，而且怎么调增强参数都没用。</em>"
                "修法是给 DataLoader 传 <code>worker_init_fn</code>，用 <code>base_seed + rank * n_workers + worker_id</code> 初始化。"
                "<strong>这个 bug 在 C56 模块 04 有完整的实验复现。</strong></p>", "所有 worker 生成同样的增强"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("调试看起来是最「工程」的一节，但它背后有一批还没被解决好的问题。"),
        UL([
            "<strong>训练故障的自动诊断。</strong>目前 grad norm、激活分布、loss 分项这些信号都要人看。"
            "<em>能否用一组规则或一个小模型，从训练日志里自动判定「这是学习率过大 / 这是标签分配失效 / 这是数据管线错」？</em>"
            "工业界已有雏形（如自动 NaN 归因、自动 lr 推荐），但覆盖率与误报率都还很差，"
            "<strong>而这恰恰是「训练一次要几千 GPU 小时」的场景下最值钱的能力</strong>。",
            "<strong>标签噪声与「难例」的可分离性。</strong>模块 02 提到 10–20% 的 badcase 是标注错。"
            "<em>置信学习、损失轨迹（一个样本的 loss 随训练的演化形态）、多模型一致性都能部分识别，</em>"
            "但在检测任务上（框与类别两个维度、还有漏标）仍无成熟方法。"
            "<strong>漏标（missing annotation）尤其难</strong>：模型检出了一个真实存在但没被标注的目标，"
            "训练时它被当成难负样本，<em>等于主动教模型「不要检出这类目标」</em>——这是长尾类别持续变差的隐藏机制。",
            "<strong>确定性与性能的取舍。</strong>GPU 上的浮点归约天然非确定，完全确定性要付显著的速度代价。"
            "<em>能否设计出「统计可复现」的训练——不要求逐位相同，但保证指标分布的可复现性有理论界？</em>"
            "这对需要通过安全评审的车载模型是实际需求，目前只能靠「多跑几次取分布」这种经验做法。",
            "<strong>训练-部署一致性的形式化验证。</strong>现在的做法是逐层对拍 + 容差判定，"
            "<em>但容差该设多少、逐层对齐能否推出端到端对齐、量化误差如何在层间传播——这些都没有可用的理论</em>。"
            "C60 模块 01/04 给了工程做法，但「证明两条管线等价」仍然是开放问题。",
            "<strong>分布式训练的可观测性。</strong>多卡训练里「哪张卡拖慢了」「哪次通信超时了」「BN 统计在各卡上差多少」"
            "目前都缺乏低开销的标准工具。<em>随着模型与集群规模增长，这类「系统层的误差」正在变成精度损失的重要来源，"
            "而它们在单卡上完全不可见。</em>",
            "<strong>把调试知识沉淀成可执行资产。</strong>本模块的每条诊断都可以写成一个自动检查器（notebook 里做了几个）。"
            "<em>更进一步的问题是：如何让这些检查器随着代码演化而不腐化？</em>"
            "<strong>「不变量测试」（decode∘encode = id、$\\mathcal{L}(\\text{GT},\\text{GT})=0$、GT-as-prediction 的 mAP = 1）"
            "应当像单元测试一样常驻 CI</strong>，但业界这么做的团队仍是少数——这是一个「知道该做但没做」的巨大缺口。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Andrej Karpathy, <em>A Recipe for Training Neural Networks</em>（2019 博文）——"
                "「先和数据融为一体 / 搭端到端骨架并接上 dumb baseline / 过拟合 / 正则化 / 调参 / 榨干」这套顺序，"
                "以及「<strong>neural net training fails silently</strong>」这个论断，是本模块全部方法论的源头。<em>建议逐段精读并对照自己的流程。</em></p>"
                "<p><strong>★</strong> Bolya et al., <em>TIDE</em>（ECCV 2020）——与模块 02 配套；"
                "当你需要判断「是模型能力问题还是管线问题」时，TIDE 的分解形态本身就是一个强指纹。</p>"
                "<p><strong>★</strong> Northcutt, Jiang &amp; Chuang, <em>Confident Learning: Estimating Uncertainty in Dataset Labels</em>"
                "（JAIR 2021）——标注噪声的系统性识别；把它的思路迁移到检测（框 + 类别 + 漏标）是很好的自研课题。</p>"
                "<p>延伸：Ioffe &amp; Szegedy, <em>Batch Normalization</em>（ICML 2015，理解 BN 在冻结/分布式下的行为）；"
                "Goyal et al., <em>Accurate, Large Minibatch SGD</em>（2017，warmup 与线性缩放规则，也解释了梯度累积的 loss 归一化口径）；"
                "Peng et al., <em>MegDet</em>（CVPR 2018，检测里 SyncBN 的实证）；"
                "PyTorch 官方的 <em>Reproducibility</em> 与 <em>Autograd anomaly detection</em> 文档（工程细节最权威）。"
                "相邻课程：本课模块 01（种子方差与显著性）、模块 02（误差分析与决策树）、"
                "C56 模块 04（worker RNG 事故的完整复现）、C57 模块 03（小目标的正样本稀缺）、"
                "C60 模块 01/04（预处理与后处理的逐层对拍）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · 训练与部署调试手册（单 batch 过拟合 / NaN 溯源 / 三类管线 bug 的指纹）

目标：把「模型不 work」这句没信息量的话，拆成一串**可以在 10 分钟内证伪的假设**。

本 notebook 你会亲手实现：
1. **一个真的能训练的迷你检测头**（纯 numpy，手写反传 + 数值梯度对拍）
2. **「先把一个 batch 过拟合」诊断法**，以及它的四种失败形态各自意味着什么
3. **静态 IoU 分配下小目标正样本数 = 0** 的数值证据（TSR 的头号隐形杀手）
4. **NaN 的四条通路**：朴素 BCE 的溢出断点、退化框的 0/0、坏标注的 $\\log(w\\le0)$，
   以及一个 `trace_nonfinite` 逐段定位器
5. **梯度/激活健康检查器**：非有限值、梯度爆炸/消失、死亡神经元
6. **三类经典数据管线 bug 的构造与指纹检测**
   —— 类别 ID 偏移 / 坐标格式弄反 / 通道顺序 BGR-RGB，每种给出**独有指纹**与一行验证
7. **诊断树（playbook）的代码化**：症状 + 观察到的事实 → 排好序的假设与检查动作

> 心智模型：**调试的进展不是「试了很多东西」，而是「排除了很多可能」。**"""),

    md("""## 1 · 一个真的能训练的迷你检测头

结构就是检测头的最小骨架：`输入特征 → ReLU 隐层 → 两个分支`
- **分类分支**：一个 logit，判「这个位置是不是前景」（BCE）
- **回归分支**：4 维框偏移 $(dx, dy, dw, dh)$，**只对正样本算**（Smooth L1）

手写反传，然后用**数值梯度对拍**——这就是第 1 节说的「反传段的不变量」。"""),

    code("""import numpy as np

rng = np.random.default_rng(0)


def sigmoid(z):
    # 数值稳定版：正负分支分开算，避免 exp 溢出
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-np.abs(z))),
                    np.exp(-np.abs(z)) / (1.0 + np.exp(-np.abs(z))))


def stable_bce(z, y):
    # log-sum-exp 稳定形式：max(z,0) - z*y + log(1+exp(-|z|))
    return np.maximum(z, 0.0) - z * y + np.log1p(np.exp(-np.abs(z)))


def init_model(d_in=12, d_h=48, seed=0):
    r = np.random.default_rng(seed)
    return dict(W1=r.normal(0, np.sqrt(2 / d_in), (d_in, d_h)), b1=np.zeros(d_h),
                w2=r.normal(0, np.sqrt(2 / d_h), (d_h,)), b2=np.zeros(1),
                W3=r.normal(0, np.sqrt(2 / d_h), (d_h, 4)), b3=np.zeros(4))


def forward(p, X):
    z1 = X @ p['W1'] + p['b1']
    h = np.maximum(z1, 0.0)                       # ReLU
    return dict(z1=z1, h=h,
                logit=h @ p['w2'] + p['b2'][0],   # 分类分支
                box=h @ p['W3'] + p['b3'])        # 回归分支


def loss_grads(p, X, y, t, w_box=1.0):
    n = len(X)
    f = forward(p, X)
    l_cls = float(stable_bce(f['logit'], y).mean())
    pos = y > 0.5
    npos = int(pos.sum())
    d = f['box'][pos] - t[pos] if npos else np.zeros((0, 4))
    ad = np.abs(d)
    l_box = float(np.where(ad < 1.0, 0.5 * d ** 2, ad - 0.5).mean()) if npos else 0.0
    loss = l_cls + w_box * l_box

    dlogit = (sigmoid(f['logit']) - y) / n                       # dL/dlogit
    dbox = np.zeros_like(f['box'])
    if npos:
        dbox[pos] = w_box * np.where(ad < 1.0, d, np.sign(d)) / (npos * 4)
    dh = np.outer(dlogit, p['w2']) + dbox @ p['W3'].T
    dz1 = dh * (f['z1'] > 0)                                     # ReLU 的导数
    g = dict(W1=X.T @ dz1, b1=dz1.sum(0), w2=f['h'].T @ dlogit,
             b2=np.array([dlogit.sum()]), W3=f['h'].T @ dbox, b3=dbox.sum(0))
    return loss, g, f, dict(l_cls=l_cls, l_box=l_box, n_pos=npos)


# —— 不变量：解析梯度 == 数值梯度 ——
Xc = rng.normal(0, 1, (16, 12))
yc = (rng.random(16) > 0.5).astype(float)
tc = rng.normal(0, 1, (16, 4))
pc = init_model(seed=1)
_, Gc, _, _ = loss_grads(pc, Xc, yc, tc)
worst = 0.0
for k in pc:
    flat = pc[k].ravel()
    for idx in rng.choice(flat.size, min(4, flat.size), replace=False):
        e, old = 1e-6, flat[idx]
        flat[idx] = old + e; Lp = loss_grads(pc, Xc, yc, tc)[0]
        flat[idx] = old - e; Lm = loss_grads(pc, Xc, yc, tc)[0]
        flat[idx] = old
        num, ana = (Lp - Lm) / (2 * e), Gc[k].ravel()[idx]
        worst = max(worst, abs(num - ana) / max(abs(num), abs(ana), 1e-8))
        assert np.isclose(num, ana, rtol=3e-4, atol=1e-8), (k, idx, num, ana)
print(f'✅ 数值梯度对拍通过，最大相对误差 {worst:.2e}')
print('   这就是「反传段的不变量」—— 它应该作为单元测试常驻仓库，而不是出事才写。')"""),

    md("""## 2 · 万能诊断法：先把一个 batch 过拟合

24 个样本，关掉增强/正则/衰减，反复训练。**一个有足够容量的模型必须把训练 loss 压到接近 0。**

这句话是**无条件成立**的——它不依赖数据质量、不依赖任务难度。
所以**做不到就一定有 bug**，而不是「这个任务比较难」。"""),

    code("""def train(p, X, y, t, steps=2000, lr=0.05, frozen=(), wd=0.0, record_every=0):
    # 极简 Adam。frozen 里的参数不更新；wd = weight decay（做过拟合诊断时必须设 0）
    p = {k: v.copy() for k, v in p.items()}
    m = {k: np.zeros_like(v) for k, v in p.items()}
    v = {k: np.zeros_like(x) for k, x in p.items()}
    hist = []
    for s in range(1, steps + 1):
        loss, g, _, info = loss_grads(p, X, y, t)
        if record_every and (s == 1 or s % record_every == 0):
            hist.append((s, loss, info['l_cls'], info['l_box']))
        for k in p:
            if k in frozen:
                continue
            gg = g[k] + wd * p[k]
            m[k] = 0.9 * m[k] + 0.1 * gg
            v[k] = 0.999 * v[k] + 0.001 * gg ** 2
            p[k] -= lr * (m[k] / (1 - 0.9 ** s)) / (np.sqrt(v[k] / (1 - 0.999 ** s)) + 1e-8)
    loss, _, _, info = loss_grads(p, X, y, t)
    return p, loss, info, hist


Xb = rng.normal(0, 1, (24, 12))
yb = (rng.random(24) > 0.5).astype(float)
tb = rng.normal(0, 1, (24, 4))
p0 = init_model(seed=2)
L_init = loss_grads(p0, Xb, yb, tb)[0]

_, l_ok, i_ok, hist = train(p0, Xb, yb, tb, steps=2000, lr=0.05, record_every=400)
print(f'初始 loss = {L_init:.4f}   （正样本 {i_ok["n_pos"]} / {len(Xb)}）')
print(f'{"step":>6s}{"loss":>12s}{"cls":>12s}{"box":>12s}')
for s, l, lc, lbx in hist:
    print(f'{s:>6d}{l:>12.3e}{lc:>12.3e}{lbx:>12.3e}')
assert l_ok < 1e-3, l_ok
print(f'\\n✅ 单 batch 过拟合成功（final loss {l_ok:.2e}）')
print('   => 数据 / 编码 / 前向 / 损失 / 反传 / 优化器 **整块可用**。')
print('   接下来所有问题只可能出在：数据规模、增强、学习率调度、正则、验证管线。')
print('   **一个实验砍掉半个搜索空间 —— 没有别的实验有这么高的信息量/成本比。**')"""),

    code("""# 四种「过拟合不了」的形态，各自意味着什么
def verdict(loss, l_init, tol=1e-3):
    if loss < tol:
        return '✅ 正常：前六段全部可用'
    if abs(loss - l_init) < 1e-9:
        return '❌ loss 一动不动 -> 梯度没流到权重（requires_grad / optimizer / no_grad / lr=0）'
    if loss > 0.6 * l_init:
        return '⚠️  几乎不动 -> lr 过小 或 warmup 还没结束 或 大部分参数被冻'
    return '⚠️  停在非零平台 -> 模型只能输出常数（weight decay 没关 / 死亡神经元 / 容量不足）'


cases = []
_, l_all, _, _ = train(p0, Xb, yb, tb, steps=300, lr=0.05, frozen=tuple(p0.keys()))
cases.append(('全部参数都冻住了', l_all))
_, l_bias, _, _ = train(p0, Xb, yb, tb, steps=2000, lr=0.05,
                        frozen=('W1', 'b1', 'w2', 'W3', 'b3'))
cases.append(('只有输出 bias 可训练', l_bias))
_, l_lr, _, _ = train(p0, Xb, yb, tb, steps=2000, lr=2e-6)
cases.append(('学习率小了 4 个数量级', l_lr))
_, l_wd, _, _ = train(p0, Xb, yb, tb, steps=2000, lr=0.05, wd=0.5)
cases.append(('忘了关 weight decay', l_wd))
cases.append(('正常', l_ok))

print(f'{"场景":<24s}{"final loss":>12s}   判定')
for nm, l in cases:
    print(f'{nm:<24s}{l:>12.4f}   {verdict(l, L_init)}')

assert abs(l_all - L_init) < 1e-12, '全冻结时 loss 必须逐位不变'
assert l_bias > 0.6 * L_init and l_lr > 0.6 * L_init
assert 1e-3 < l_wd < 0.8 * L_init
print('\\n⚠️  做过拟合诊断前必须关掉：增强 / dropout / weight decay / **lr warmup 与衰减** / EMA。')
print('   最常见的自欺欺人是 warmup 没走完就下结论 —— 那时 lr 还接近 0，看起来像「梯度不流」。')
print('⚠️  另一个坑：检测的 loss 是多项之和，某一项塌成 0 而另一项没动，总和看起来也会很小。')
print('   **必须分项打印，并且必须同时看 mAP。**')"""),

    md("""## 3 · 检测特有的陷阱：正样本数 = 0

在有标签分配的检测器里，「过拟合一个 batch」不是平凡的。
**如果分配策略把所有 anchor 都判成负样本，分类分支只会学到「全是背景」，loss 会降到某个平台然后不动。**

下面用 RetinaNet 的默认 anchor 配置（P3–P7，stride 8/16/32/64/128，
base size 32/64/128/256/512，每级 3 个尺度）算一算：
**多大的交通标志才能拿到至少一个 IoU ≥ 0.5 的正样本 anchor？**"""),

    code("""def iou_mat(a, b):
    a = np.asarray(a, float).reshape(-1, 4); b = np.asarray(b, float).reshape(-1, 4)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = np.clip(a[:, 2] - a[:, 0], 0, None) * np.clip(a[:, 3] - a[:, 1], 0, None)
    bb = np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)
    return inter / np.maximum(aa[:, None] + bb[None, :] - inter, 1e-9)


def make_anchors(levels, img=256):
    out = []
    for stride, base in levels:
        for s in [1.0, 2 ** (1 / 3), 2 ** (2 / 3)]:          # 每级 3 个尺度
            sz = base * s
            cs = np.arange(stride / 2, img, stride)
            cx, cy = np.meshgrid(cs, cs)
            cx, cy = cx.ravel(), cy.ravel()
            out.append(np.stack([cx - sz / 2, cy - sz / 2, cx + sz / 2, cy + sz / 2], 1))
    return np.concatenate(out, 0)


P3P7 = [(8, 32), (16, 64), (32, 128), (64, 256), (128, 512)]
A = make_anchors(P3P7)
A2 = make_anchors([(4, 16)] + P3P7)                            # 额外加一个 P2 层
print(f'anchor 总数：P3-P7 = {len(A)}，加 P2 后 = {len(A2)}')
print(f'\\n{"标志边长":>9s}{"P3-P7 最大IoU":>14s}{"正样本数":>9s}{"加P2 最大IoU":>14s}{"正样本数":>9s}')
zero_pos = []
for gs in [8, 12, 16, 20, 24, 32, 48, 64, 96]:
    g = np.array([[128 - gs / 2, 128 - gs / 2, 128 + gs / 2, 128 + gs / 2]])
    v, v2 = iou_mat(A, g)[:, 0], iou_mat(A2, g)[:, 0]
    n1, n2 = int((v >= 0.5).sum()), int((v2 >= 0.5).sum())
    if n1 == 0:
        zero_pos.append(gs)
    print(f'{gs:>9d}{v.max():>14.3f}{n1:>9d}{v2.max():>14.3f}{n2:>9d}')

assert zero_pos == [8, 12, 16, 20], zero_pos
assert int((iou_mat(A2, np.array([[122., 122., 134., 134.]]))[:, 0] >= 0.5).sum()) > 0
print(f'\\n🚨 **≤ {max(zero_pos)} px 的交通标志在 P3-P7 上拿不到任何一个正样本 anchor。**')
print('   它对分类损失完全不可见 —— 模型不是「学不好」，是**根本没被要求去学**。')
print('   TSR 里 80 米外的限速牌在 1920 宽的图上约 15-20 px，缩到 640 输入后只剩 5-7 px。')
print('   => 所以「单 batch 过拟合」在检测里**必须同时打印每步分到的正样本数**；')
print('      正样本数 = 0 时，问题在分配策略，不在网络。')
print('   => 修法：加 P2 层（上表右侧）/ 降低小目标的 IoU 阈值 / 换 center-based 分配')
print('      / 换尺度不敏感的度量（C57 模块 03 的 NWD）。')"""),

    md("""## 4 · NaN 的四条通路

按「第几个 iteration 出现」分诊：
- **第 0–1 步就出现** ⇒ 数值实现或数据问题（本节的 ②③）
- **训练几百步后出现** ⇒ 发散（①）
- **固定 seed 后总在同一步出现** ⇒ 某个特定样本（③）"""),

    code("""def naive_bce(z, y):
    p = 1.0 / (1.0 + np.exp(-z))                 # 朴素实现：先算概率再取 log
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


print('② log(0)：朴素 BCE 在 y=0 时的溢出断点')
print(f'{"z":>5s}{"float32 朴素":>16s}{"float64 朴素":>16s}{"稳定版":>12s}')
brk32 = brk64 = None
with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
    for z in [5., 10., 16., 17., 20., 36., 37., 40., 90.]:
        n32 = float(naive_bce(np.float32(z), np.float32(0.0)))
        n64 = float(naive_bce(np.float64(z), 0.0))
        st = float(stable_bce(np.float64(z), 0.0))
        if brk32 is None and not np.isfinite(n32):
            brk32 = z
        if brk64 is None and not np.isfinite(n64):
            brk64 = z
        f32 = 'inf' if not np.isfinite(n32) else f'{n32:.4f}'
        f64 = 'inf' if not np.isfinite(n64) else f'{n64:.4f}'
        print(f'{z:>5.0f}{f32:>16s}{f64:>16s}{st:>12.4f}')
print(f'\\n断点：float32 在 z≈{brk32:.0f}，float64 在 z≈{brk64:.0f}；稳定版永远有限。')
assert brk32 == 17 and brk64 == 37
assert np.isfinite(stable_bce(np.float64(1e4), 0.0))
# 稳定版与朴素版在安全区内必须完全一致
zs = np.linspace(-10, 10, 41)
assert np.allclose(stable_bce(zs, 0.0), naive_bce(zs, 0.0), atol=1e-12)
assert np.allclose(stable_bce(zs, 1.0), naive_bce(zs, 1.0), atol=1e-12)
print('✅ 两者在安全区数学等价；差别只在极端 z 上，而极端 z 恰恰是训练发散时必然出现的。')"""),

    code("""# ② 除零：退化框（标注里 x1 == x2）
def iou_pair_1(a, b, eps=0.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    inter = (np.clip(np.minimum(a[2], b[2]) - np.maximum(a[0], b[0]), 0, None) *
             np.clip(np.minimum(a[3], b[3]) - np.maximum(a[1], b[1]), 0, None))
    u = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / (u + eps)


degenerate = np.array([10., 10., 10., 20.])          # 宽度为 0：标注员点一下就保存了
with np.errstate(divide='ignore', invalid='ignore'):
    v_bad = iou_pair_1(degenerate, degenerate)
    v_ok = iou_pair_1(degenerate, degenerate, eps=1e-9)
    # ③ 坏标注：框回归目标 log(w / w_anchor)
    t_zero = np.log(np.float64(0.0) / 32)
    t_neg = np.log(np.float64(-5.0) / 32)
print(f'退化框的 IoU：无 eps -> {v_bad}   有 eps -> {v_ok}')
print(f'log(w/w_a)：w=0 -> {t_zero}   w=-5 -> {t_neg}')
assert np.isnan(v_bad) and v_ok == 0.0
assert np.isinf(t_zero) and np.isnan(t_neg)


def trace_nonfinite(stages):
    # stages: [(名字, 张量), ...]，按前向顺序。返回第一个含 NaN/Inf 的段
    for name, arr in stages:
        a = np.asarray(arr, float)
        if not np.isfinite(a).all():
            fin = a[np.isfinite(a)]
            return name, dict(n_nan=int(np.isnan(a).sum()), n_inf=int(np.isinf(a).sum()),
                              lo=float(fin.min()) if fin.size else float('nan'),
                              hi=float(fin.max()) if fin.size else float('nan'))
    return None, {}


with np.errstate(divide='ignore', invalid='ignore'):
    pipeline = [('input', np.ones((4, 3))),
                ('backbone', np.ones((4, 8)) * 2.0),
                ('cls_logit', np.array([1.2, -0.4, 3.1, 0.0])),
                ('box_target', np.log(np.array([32., 16., 0., 64.]) / 32)),   # ← 第 3 个框宽为 0
                ('loss', np.array([1.0]))]
    where, det = trace_nonfinite(pipeline)
print(f'\\n第一个出问题的段：{where}  {det}')
assert where == 'box_target' and det['n_inf'] == 1
print('✅ 关键在于**抓第一现场**：NaN 会传染，两三步之后整个网络都是 NaN，那时信息量为零。')
print('   工程做法：每 N 步常驻记录 grad norm、各层 max|x|、**loss 的各分项分开记**。')
print('   只有 box 分项炸而 cls 正常 => 几乎必然是坏标注；所有分项同时炸 => 才是学习率。')"""),

    md("""## 5 · 梯度与激活的健康检查器

四个检查项，全部可以在训练循环里低成本常驻：
**非有限值 / 梯度爆炸 / 梯度消失 / 死亡神经元**（整个 batch 上激活恒为 0 的隐层单元）。"""),

    code("""def health_check(acts, grads, gn_hi=1e3, gn_lo=1e-7, dead_hi=0.5):
    issues = []
    for n, a in acts.items():
        if not np.isfinite(np.asarray(a, float)).all():
            issues.append(f'nonfinite_act:{n}')
    for n, g in grads.items():
        if not np.isfinite(np.asarray(g, float)).all():
            issues.append(f'nonfinite_grad:{n}')
    fin = [np.asarray(g, float) for g in grads.values() if np.isfinite(np.asarray(g, float)).all()]
    gn = float(np.sqrt(sum(float((g ** 2).sum()) for g in fin))) if fin else float('nan')
    if np.isfinite(gn):
        if gn > gn_hi:
            issues.append('grad_explosion')
        elif gn < gn_lo:
            issues.append('grad_vanish')
    for n, a in acts.items():
        a = np.asarray(a, float)
        if a.ndim == 2 and np.isfinite(a).all():
            dead = float((np.abs(a) <= 1e-12).all(axis=0).mean())   # 整个 batch 上恒为 0
            if dead > dead_hi:
                issues.append(f'dead_units:{n}')
    return sorted(issues), gn


_, G_h, F_h, _ = loss_grads(p0, Xb, yb, tb)
scen = {}
scen['健康'] = ({'h': F_h['h']}, G_h)
scen['梯度爆炸'] = ({'h': F_h['h']}, {k: v * 1e7 for k, v in G_h.items()})
p_dead = {k: v.copy() for k, v in p0.items()}
p_dead['b1'] = np.full_like(p_dead['b1'], -50.0)      # 巨大的负 bias -> ReLU 全灭
_, G_d, F_d, _ = loss_grads(p_dead, Xb, yb, tb)
scen['死亡神经元'] = ({'h': F_d['h']}, G_d)
G_n = {k: v.copy() for k, v in G_h.items()}; G_n['W1'][0, 0] = np.nan
scen['梯度里有 NaN'] = ({'h': F_h['h']}, G_n)

print(f'{"场景":<16s}{"grad norm":>13s}   诊断')
for nm, (a, g) in scen.items():
    iss, gn = health_check(a, g)
    print(f'{nm:<16s}{gn:>13.3e}   {iss if iss else "无异常"}')

assert health_check(*scen['健康'])[0] == []
assert 'grad_explosion' in health_check(*scen['梯度爆炸'])[0]
assert 'dead_units:h' in health_check(*scen['死亡神经元'])[0]
assert 'nonfinite_grad:W1' in health_check(*scen['梯度里有 NaN'])[0]
print('\\n👉 「死亡神经元」在检测里有一个很有辨识度的后果：**回归分支退化到输出常数**，')
print('   表现为所有预测框尺寸差不多、位置都靠近图像中心（= 训练集框分布的中位数）。')
print('   看到「所有框长得一样」，先怀疑模型压根没在学，而不是先怀疑标签分配。')"""),

    md("""## 6 · 管线 bug 之一：类别 ID 偏移

**指纹：混淆矩阵的质量集中在偏离对角线 $k$ 格的次对角线上。**

来源千奇百怪但都很常见：COCO 的 `category_id` 从 1 开始、
有的框架把 background 放在 index 0 而有的不放、
两侧从不同来源构造类别列表、某个类在某个 split 里样本数为 0 导致后面全部左移。

**它不会让 loss 异常**——模型照样能学，只是学到了一个偏移一位的映射。"""),

    code("""NC = 8
CLASSES = ['限速30', '限速60', '限速80', '停车让行', '禁止左转', '注意行人', '解除限速', '指路牌']
r6 = np.random.default_rng(3)

true_cls = r6.integers(0, NC, 600)
pred_ok = true_cls.copy()
flip = r6.random(600) < 0.12                       # 12% 的正常分类错误
pred_ok[flip] = r6.integers(0, NC, int(flip.sum()))
pred_shift = (pred_ok + 1) % NC                    # ← 注入 bug：类别整体 +1


def conf_mat(t, p, n=NC):
    cm = np.zeros((n, n), int)
    for a, b in zip(t, p):
        cm[a, b] += 1
    return cm


CM_OK, CM_BAD = conf_mat(true_cls, pred_ok), conf_mat(true_cls, pred_shift)


def show_cm(cm, title):
    print(title)
    print(' ' * 10 + ''.join(f'{c[:4]:>7s}' for c in CLASSES))
    for i in range(NC):
        print(f'{CLASSES[i]:<10s}' + ''.join(f'{cm[i, j]:>7d}' for j in range(NC)))


show_cm(CM_BAD, '有 bug 时的混淆矩阵（行=真值，列=预测）：')
print('\\n👉 质量整体跑到了对角线右边一格 —— 这就是「次对角线」指纹。')
print('   对比：正常模型的质量在对角线上，错误弥散分布。')
print(f'   正常：对角线占比 {np.trace(CM_OK) / CM_OK.sum():.1%}   '
      f'有 bug：对角线占比 {np.trace(CM_BAD) / CM_BAD.sum():.1%}')
assert np.trace(CM_BAD) / CM_BAD.sum() < 0.05 and np.trace(CM_OK) / CM_OK.sum() > 0.8
print('\\n⚠️  注意 mAP 会精确掉到 ~0 而不是掉一半：AP 是逐类算的，')
print('   偏移之后类 c 的预测全落进类 c+1 的评测里，两者在图像上完全不重叠 => 每类 AP 都是 0。')
print('   **「mAP 恰好是 0 而不是 0.3」本身就是线索 —— 模型能力问题不会让指标精确归零。**')"""),

    md("""## 7 · 管线 bug 之二：坐标格式弄反

四个数就是四个数，任何格式都能塞进去，**不会报错**。

**指纹**（下表会实测）：
- `cxcywh` / `xywh` 被当成 `xyxy`：宽或高常常是负的 → clip 后面积为 0 →
  **IoU 恰好等于 0 的比例接近 100%**（模型定位不准时这个比例几乎是 0）
- `yxyx`（TF 系）被当成 `xyxy`：**`corr(pred_cx, gt_cy)` 很高而 `corr(pred_cx, gt_cx)` 很低**
  —— 中心点散点图被转置了"""),

    code("""r7 = np.random.default_rng(5)
n = 400
cx = r7.uniform(60, 1860, n); cy = r7.uniform(60, 1020, n)
sz = np.exp(r7.normal(np.log(34), 0.5, n))                 # TSR 的典型尺寸分布
GT7 = np.stack([cx - sz / 2, cy - sz / 2, cx + sz / 2, cy + sz / 2], 1)

PREDS = {
    '正常（框略有偏差）': GT7 + r7.normal(0, 0.02 * sz[:, None], (n, 4)),
    '定位很差（真·模型问题）': GT7 + np.repeat(r7.normal(0, 0.30 * sz[:, None], (n, 2)), 2, axis=1),
    'cxcywh 当 xyxy': np.stack([cx, cy, sz, sz], 1),
    'xywh 当 xyxy': np.stack([cx - sz / 2, cy - sz / 2, sz, sz], 1),
    'yxyx 当 xyxy': GT7[:, [1, 0, 3, 2]],
}

CANDS = {
    'as_is': lambda b: b,
    'xywh->xyxy': lambda b: np.stack([b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]], 1),
    'cxcywh->xyxy': lambda b: np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2,
                                        b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1),
    'yxyx->xyxy': lambda b: b[:, [1, 0, 3, 2]],
}


def iou_pair(a, b):
    x1 = np.maximum(a[:, 0], b[:, 0]); y1 = np.maximum(a[:, 1], b[:, 1])
    x2 = np.minimum(a[:, 2], b[:, 2]); y2 = np.minimum(a[:, 3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = np.clip(a[:, 2] - a[:, 0], 0, None) * np.clip(a[:, 3] - a[:, 1], 0, None)
    bb = np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)
    return inter / np.maximum(aa + bb - inter, 1e-9)


def box_fingerprint(pred, gt):
    v = iou_pair(pred, gt)
    ap = np.clip(pred[:, 2] - pred[:, 0], 0, None) * np.clip(pred[:, 3] - pred[:, 1], 0, None)
    ag = (gt[:, 2] - gt[:, 0]) * (gt[:, 3] - gt[:, 1])
    pcx, pcy = (pred[:, 0] + pred[:, 2]) / 2, (pred[:, 1] + pred[:, 3]) / 2
    gcx, gcy = (gt[:, 0] + gt[:, 2]) / 2, (gt[:, 1] + gt[:, 3]) / 2
    return dict(iou=float(v.mean()), zero=float((v < 1e-9).mean()),
                area=float(np.median(ap) / np.median(ag)),
                cxx=float(np.corrcoef(pcx, gcx)[0, 1]), cxy=float(np.corrcoef(pcx, gcy)[0, 1]))


print(f'{"情形":<24s}{"平均IoU":>9s}{"IoU=0占比":>11s}{"面积比":>9s}{"corr(px,gx)":>13s}{"corr(px,gy)":>13s}')
FP = {}
for nm, pb in PREDS.items():
    FP[nm] = box_fingerprint(pb, GT7)
    f = FP[nm]
    print(f'{nm:<24s}{f["iou"]:>9.3f}{f["zero"]:>11.0%}{f["area"]:>9.2f}{f["cxx"]:>13.2f}{f["cxy"]:>13.2f}')

assert FP['定位很差（真·模型问题）']['zero'] < 0.05, '模型定位不准时几乎没有精确为 0 的 IoU'
assert FP['cxcywh 当 xyxy']['zero'] > 0.95 and FP['xywh 当 xyxy']['zero'] > 0.95
assert FP['yxyx 当 xyxy']['cxy'] > 0.9 > FP['yxyx 当 xyxy']['cxx']
assert FP['正常（框略有偏差）']['cxx'] > 0.9 > FP['正常（框略有偏差）']['cxy']
print('\\n👉 「定位很差」和「格式弄反」在 mAP 上都会很难看，但**指纹完全不同**：')
print(f'   定位差：平均 IoU {FP["定位很差（真·模型问题）"]["iou"]:.2f}，'
      f'**IoU 恰好为 0 的比例 {FP["定位很差（真·模型问题）"]["zero"]:.0%}**（框再歪也总有些许重叠）')
print(f'   格式错：平均 IoU {FP["cxcywh 当 xyxy"]["iou"]:.2f}，'
      f'**IoU 恰好为 0 的比例 {FP["cxcywh 当 xyxy"]["zero"]:.0%}**（宽或高为负，被 clip 成 0 面积）')
print('   => 区分它们的不是均值，是**「恰好为 0」的那个比例**，以及面积比是否塌成 0。')
print('👉 x/y 互换的指纹是**相关系数被转置**：corr(pred_cx, gt_cy) 反而接近 1。')
print('   这个 bug 在方形图上很难发现，在 1920x1080 上会让框飞出画面。')"""),

    md("""## 8 · 管线 bug 之三：通道顺序 BGR / RGB

这一类和前两类有本质区别：**它不会让指标归零，只会掉 5–15 个点**。
于是你会以为「这次训练没调好」，然后在一个有 bug 的管线上做三个月的架构消融。

**TSR 特有的指纹**：交通标志的颜色<u>就是</u>语义（红=禁令、蓝=指示、黄=警告），
R/B 互换会把红牌变成蓝牌；而白底黑字的指路牌 $R\\approx G\\approx B$，几乎不受影响。
=> **掉点具有类别选择性**，这正是它和「归一化 mean/std 写错」（所有类均匀掉点）的区别。"""),

    code("""SIGN_GROUPS = [
    ('红色禁令(限速/禁止)', np.array([0.75, 0.25, 0.22]), 'color'),
    ('蓝色指示(直行/环岛)', np.array([0.20, 0.35, 0.78]), 'color'),
    ('黄色警告(注意行人)', np.array([0.85, 0.75, 0.20]), 'color'),
    ('白底黑字(指路牌)', np.array([0.82, 0.82, 0.81]), 'neutral'),
    ('灰色解除限速', np.array([0.46, 0.47, 0.48]), 'neutral'),
]
PRIOR = np.array([0.40, 0.18, 0.12, 0.20, 0.10])          # 红色禁令占比最高（限速+禁止）


def make_patches(n, seed):
    # 合成 16x16 的标志块：底色 + 光照增益 + 噪声 + 中间较暗的图案区
    r = np.random.default_rng(seed)
    lab = r.choice(len(SIGN_GROUPS), n, p=PRIOR)
    P = np.zeros((n, 16, 16, 3))
    for i, c in enumerate(lab):
        img = np.tile(SIGN_GROUPS[c][1], (16, 16, 1)) * r.uniform(0.88, 1.12)
        img += r.normal(0, 0.035, (16, 16, 3))
        img[5:11, 5:11] *= r.uniform(0.25, 0.5)
        P[i] = np.clip(img, 0, 1)
    return P, lab


TR, ytr = make_patches(1500, 1)
TE, yte = make_patches(600, 2)
mean_rgb = lambda P: P.reshape(len(P), -1, 3).mean(1)
CENTROID = np.stack([mean_rgb(TR)[ytr == k].mean(0) for k in range(len(SIGN_GROUPS))])
predict = lambda P: ((mean_rgb(P)[:, None, :] - CENTROID[None]) ** 2).sum(-1).argmin(1)

COLOR_IDS = [k for k, g in enumerate(SIGN_GROUPS) if g[2] == 'color']
NEUTRAL_IDS = [k for k, g in enumerate(SIGN_GROUPS) if g[2] == 'neutral']


def report(P, y, tag):
    pr = predict(P)
    print(f'[{tag}]  总体准确率 {(pr == y).mean():.3f}')
    for k, (nm, _, grp) in enumerate(SIGN_GROUPS):
        m = y == k
        top = SIGN_GROUPS[int(np.bincount(pr[m], minlength=len(SIGN_GROUPS)).argmax())][0]
        print(f'   {nm:<20s}[{grp:7s}] acc={(pr[m] == y[m]).mean():.3f}  最常被判成 -> {top}')
    mc, mn = np.isin(y, COLOR_IDS), np.isin(y, NEUTRAL_IDS)
    ac, an = float((pr[mc] == y[mc]).mean()), float((pr[mn] == y[mn]).mean())
    print(f'   >>> 颜色语义类 acc={ac:.3f}    中性色类 acc={an:.3f}')
    return float((pr == y).mean()), ac, an


a_rgb = report(TE, yte, 'RGB 正确')
print()
a_bgr = report(TE[..., ::-1], yte, 'BGR 通道顺序弄反')
assert a_rgb[1] > 0.95 and a_rgb[2] > 0.95
assert a_bgr[1] < 0.05, '颜色语义类应该崩到接近 0'
assert a_bgr[2] > 0.95, '中性色类几乎不受影响 —— 这就是指纹'
print('\\n🔎 **指纹：颜色语义类 1.00 -> 0.00，中性色类 1.00 -> 1.00。**')
print('   对照：如果是归一化 mean/std 写错，所有类别会**均匀**掉点，')
print('   因为它不改变通道之间的相对关系，只是整体平移/缩放。')"""),

    code("""def detect_channel_swap(batch, ref_mean_rgb, ratio=0.5):
    # 把 batch 的通道均值与训练集统计比：反过来更接近就说明通道被交换了
    o = np.asarray(batch).reshape(-1, 3).mean(0)
    d0 = float(np.linalg.norm(o - ref_mean_rgb))
    d1 = float(np.linalg.norm(o[::-1] - ref_mean_rgb))
    return (d1 < d0 * ratio), d0, d1


REF = mean_rgb(TR).mean(0)
print('训练集通道均值 ref =', np.round(REF, 3))
for tag, batch in [('RGB 输入', TE), ('BGR 输入', TE[..., ::-1])]:
    sw, d0, d1 = detect_channel_swap(batch, REF)
    print(f'{tag:<10s} ||obs-ref||={d0:.4f}  ||reversed(obs)-ref||={d1:.4f}  -> 疑似交换: {sw}')
assert detect_channel_swap(TE, REF)[0] is False
assert detect_channel_swap(TE[..., ::-1], REF)[0] is True

# 最强的确诊手段：把输入反过来重测，指标恢复即坐实
a_fix = report(TE[..., ::-1][..., ::-1], yte, '把输入通道反过来 -> 恢复')
assert abs(a_fix[0] - a_rgb[0]) < 1e-12
print('\\n✅ 一行验证：`x = x[..., ::-1]` 之后指标完全恢复 => 确诊通道顺序。')
print('⚠️  组合 bug 会污染指纹：训练用 PIL(RGB)+cv2.resize，推理用 cv2.imread(BGR)+PIL.resize，')
print('   两个 bug 叠加时你看到的是「颜色类的小目标崩得特别厉害」，很容易误判成小目标问题。')
print('   **所以指纹检查必须逐项独立：一次只改一个变量重测。**（模块 01 的单变量原则）')"""),

    md("""## 9 · 诊断树（playbook）的代码化

每条假设带四个字段：**名字 / 检查动作 / 若成立会观察到什么 / 先验权重**，
再加一个 `when(facts)` 把「你已经观察到的事实」变成权重调整。

**输出是排好序的检查清单**，而不是一个答案——调试本来就是逐步排除。"""),

    code("""PLAYBOOK = {
    'loss_nan': [
        dict(name='① 学习率过大 / 数值溢出', prior=3.0,
             check='看 NaN 之前 200 步的 grad norm 与各层 max|x| 曲线',
             expect='NaN 之前有一段指数上升',
             when=lambda f: 3.0 if f.get('first_nan_iter', 0) > 50 else 0.2),
        dict(name='② log(0) / 除零（自写损失缺 eps、退化框）', prior=3.0,
             check='对同一 batch 只跑 cls 分项、再只跑 box 分项；检查标注里有无 w<=0 或 h<=0',
             expect='某一分项单独就能触发；换成 log-sum-exp 稳定版后消失',
             when=lambda f: 4.0 if f.get('first_nan_iter', 999) <= 2 else 0.5),
        dict(name='③ 坏标注（负宽高 / 越界坐标 / 空框）', prior=2.0,
             check='固定 seed 定位到具体 iteration，dump 那个 batch 的文件名',
             expect='每次都在同一步 NaN，且只有 box 分项炸',
             when=lambda f: 4.0 if f.get('same_iter_every_run') else 0.6),
        dict(name='④ 反传中的除零（sqrt(0) / 零向量归一化 / GIoU 闭包为 0）', prior=1.5,
             check='前向逐层挂哨兵，再单独检查 .grad',
             expect='前向所有中间张量有限，只有梯度非有限',
             when=lambda f: 4.0 if (f.get('forward_finite') and f.get('grad_nonfinite')) else 1.0),
    ],
    'loss_flat': [
        dict(name='单 batch 都过拟合不了 -> 前六段有 bug', prior=5.0,
             check='24 个样本、关掉增强/正则/衰减，训 2000 步',
             expect='loss 必须 < 1e-3；否则按本 notebook 第 2 节的四种形态分诊',
             when=lambda f: 5.0 if not f.get('can_overfit_one_batch', True) else 0.1),
        dict(name='学习率不合适', prior=3.0, check='lr range test（1e-7 -> 10 指数扫描）',
             expect='取「下降最陡」处的 1/10',
             when=lambda f: 1.0),
        dict(name='标签映射错', prior=2.5, check='把编码后的目标解码回框与类别名，画到图上',
             expect='解码结果与原 GT 逐元素一致', when=lambda f: 1.0),
        dict(name='数据没打乱', prior=2.0, check='打印前 200 个样本的类别序列；查 shuffle/sampler',
             expect='loss 曲线的周期 = 一个 epoch 或一个分片',
             when=lambda f: 3.0 if f.get('loss_periodic') else 0.5),
        dict(name='冻错了层', prior=2.0,
             check='统计可训练参数量；对比 optimizer.param_groups；打印 BN 的 running_mean 是否在变',
             expect='可训练参数量远小于预期', when=lambda f: 1.0),
    ],
    'map_zero': [
        dict(name='类别 ID 偏移 0/1', prior=5.0, check='把预测类别整体 ±1 重算 mAP',
             expect='mAP 突然正常；混淆矩阵的质量在偏移 k 格的次对角线上', when=lambda f: 1.0),
        dict(name='坐标格式弄反', prior=4.5,
             check='把预测框按 cxcywh/xywh/yxyx -> xyxy 各试一遍，重算平均 IoU',
             expect='某个变换下平均 IoU 从 0.0x 跳到 0.8+；且原始 IoU=0 的比例接近 100%',
             when=lambda f: 1.0),
        dict(name='评测集与训练集类别表不一致', prior=4.0,
             check='diff 两侧类别列表的**顺序**，不只是集合；查是否有类在某个 split 里样本数为 0',
             expect='混淆矩阵是一个置换矩阵', when=lambda f: 1.0),
        dict(name='模型能力不足', prior=0.5, check='看训练 loss 与训练集上的 mAP',
             expect='训练集 mAP 也很低', when=lambda f: 1.0),
    ],
    'val_bad': [
        dict(name='验证管线与训练不一致（伪过拟合）', prior=4.0,
             check='**把训练集喂进验证的那条代码路径**跑评测',
             expect='训练集在验证路径上同样崩 => 与泛化无关',
             when=lambda f: 5.0 if f.get('train_as_val_also_bad') else 0.2),
        dict(name='忘了 model.eval()（BN 用了 batch 统计）', prior=2.0,
             check='对比 eval/train 模式下同一批数据的输出', expect='两者差异巨大', when=lambda f: 1.0),
        dict(name='真·过拟合', prior=2.0, check='看验证 loss 是否先降后升；加数据/加增强做消融',
             expect='有明确拐点，加数据能改善',
             when=lambda f: 3.0 if f.get('val_loss_has_turning_point') else 0.8),
        dict(name='捷径特征（跨采集批次失效）', prior=1.5,
             check='按采集批次给验证集分桶，比较桶内与跨桶指标',
             expect='同批次好、跨批次崩', when=lambda f: 1.0),
    ],
}


def diagnose(symptom, facts=None):
    facts = facts or {}
    items = [(h['prior'] * h['when'](facts), h) for h in PLAYBOOK[symptom]]
    items.sort(key=lambda x: -x[0])
    return [dict(score=round(s, 2), name=h['name'], check=h['check'], expect=h['expect'])
            for s, h in items]


def show(symptom, facts, title):
    print(f'\\n=== {title} ===')
    for i, h in enumerate(diagnose(symptom, facts), 1):
        print(f'{i}. [{h["score"]:>5.2f}] {h["name"]}\\n     查：{h["check"]}\\n     若成立：{h["expect"]}')


show('loss_nan', {'first_nan_iter': 1}, 'NaN 出现在第 1 个 iteration')
show('loss_nan', {'first_nan_iter': 800}, 'NaN 出现在第 800 个 iteration')
show('map_zero', {}, 'mAP 恒为 0')
show('val_bad', {'train_as_val_also_bad': True}, '训练好、验证崩，且训练集走验证路径也崩')

assert diagnose('loss_nan', {'first_nan_iter': 1})[0]['name'].startswith('② log(0)')
assert diagnose('loss_nan', {'first_nan_iter': 800})[0]['name'].startswith('① 学习率')
assert diagnose('map_zero')[0]['name'].startswith('类别 ID 偏移')
assert diagnose('map_zero')[-1]['name'] == '模型能力不足', '「模型不行」永远排最后'
assert '验证管线' in diagnose('val_bad', {'train_as_val_also_bad': True})[0]['name']
assert '过拟合' in diagnose('val_bad', {'val_loss_has_turning_point': True})[0]['name']
print('\\n✅ 注意 map_zero 里「模型能力不足」的先验只有 0.5 —— **它永远排在最后**。')"""),

    md("""## ✏️ 练习 1：数值稳定的 BCE

实现 `my_bce(z, y)`，要求：
- 在 $|z| \\le 10$ 的安全区里与朴素实现 $-y\\log\\sigma(z)-(1-y)\\log(1-\\sigma(z))$ 数值一致（`atol=1e-12`）
- 在 $|z|$ 极大（如 $10^4$）时**仍然有限**
- 支持数组输入

提示：$\\mathcal{L} = \\max(z,0) - zy + \\log(1+e^{-|z|})$。"""),

    code("""def my_bce(z, y):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
zz = np.linspace(-10, 10, 81)
for yy in [0.0, 1.0]:
    assert np.allclose(my_bce(zz, yy), naive_bce(zz, yy), atol=1e-12), yy
for big in [1e2, 1e4, -1e4]:
    v0, v1 = float(my_bce(np.float64(big), 0.0)), float(my_bce(np.float64(big), 1.0))
    assert np.isfinite(v0) and np.isfinite(v1), big
# y=0 时 loss 应等于 max(z,0)+log(1+e^-|z|)，z 很大时约等于 z 本身
assert abs(float(my_bce(np.float64(1e4), 0.0)) - 1e4) < 1e-6
assert float(my_bce(np.float64(1e4), 1.0)) < 1e-6
# 与 float32 朴素版对比：朴素版在 z=17 就废了
with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
    assert not np.isfinite(float(naive_bce(np.float32(17.0), np.float32(0.0))))
assert np.isfinite(float(my_bce(np.float32(17.0), np.float32(0.0))))
print('✅ 练习 1 通过：稳定版在安全区数学等价，在极端 z 上不溢出。')
print('   这不是「精度更好」的问题 —— 朴素版给出的是 inf/nan，是**完全错误**。')"""),

    md("""## ✏️ 练习 2：类别 ID 偏移检测器

实现 `detect_label_shift(cm)`：输入 $C\\times C$ 混淆矩阵（行=真值，列=预测），
返回 `(k, mass)`：
- `k` 使 $\\sum_i cm[i,\\,i{+}k]$ 最大的偏移量（**不做环绕**，只累加下标合法的项）
- `mass` = 该次对角线上的样本数 ÷ 总样本数

`k == 0` 说明正常；`k != 0` 且 `mass` 很高就是中招了。"""),

    code("""def detect_label_shift(cm):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
k0, m0 = detect_label_shift(CM_OK)
k1, m1 = detect_label_shift(CM_BAD)
print(f'正常模型   -> k={k0}, 次对角线质量={m0:.1%}')
print(f'类别 +1 bug -> k={k1}, 次对角线质量={m1:.1%}')
assert k0 == 0 and m0 > 0.8
assert k1 == 1 and m1 > 0.6
# 手算：一个 3x3 的纯 -1 偏移矩阵
tiny = np.array([[0, 0, 0], [7, 0, 0], [0, 9, 0]])
assert detect_label_shift(tiny) == (-1, 1.0), detect_label_shift(tiny)
# 全零矩阵不能崩
assert detect_label_shift(np.zeros((4, 4), int))[1] == 0.0
print('✅ 练习 2 通过：一个混淆矩阵 + 一行代码，就能把「mAP=0」的头号元凶钉死。')"""),

    md("""## ✏️ 练习 3：坐标格式自动识别

实现 `best_box_format(pred, gt, cands=CANDS)`：对每个候选变换算变换后与 `gt` 的**平均 IoU**，
返回 `(最佳变换名, {变换名: 平均IoU})`。可直接用上面的 `iou_pair`。"""),

    code("""def best_box_format(pred, gt, cands=None):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
expect = {'正常（框略有偏差）': 'as_is', '定位很差（真·模型问题）': 'as_is',
          'cxcywh 当 xyxy': 'cxcywh->xyxy', 'xywh 当 xyxy': 'xywh->xyxy',
          'yxyx 当 xyxy': 'yxyx->xyxy'}
print(f'{"情形":<24s}{"识别出的格式":<16s}{"该格式下的平均IoU":>18s}')
for nm, pb in PREDS.items():
    best, sc = best_box_format(pb, GT7)
    print(f'{nm:<24s}{best:<16s}{sc[best]:>18.3f}')
    assert best == expect[nm], (nm, best)
    if nm.endswith('当 xyxy'):
        assert sc[best] > 0.99, '修正后应当几乎完美重合'
        assert sc['as_is'] < 0.05, '未修正时平均 IoU 接近 0'
print('✅ 练习 3 通过：坐标格式不该靠「读代码猜」，应该靠「试一遍看 IoU」。')
print('   根治手段：在数据结构里带上格式标签（Boxes(fmt=...)），转换必须显式调用。')"""),

    md("""## ✏️ 练习 4：症状 + 事实 → 排序后的检查清单

实现 `next_checks(symptom, facts, top=2)`：调用 `diagnose`，返回**前 `top` 条**的
`(name, check)` 二元组列表。再用它验证四个场景的首选检查是否符合预期。"""),

    code("""def next_checks(symptom, facts=None, top=2):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
c1 = next_checks('loss_nan', {'first_nan_iter': 1}, top=2)
assert len(c1) == 2 and isinstance(c1[0], tuple) and len(c1[0]) == 2
assert c1[0][0].startswith('② log(0)')
assert next_checks('loss_nan', {'first_nan_iter': 800})[0][0].startswith('① 学习率')
assert next_checks('map_zero', {})[0][0].startswith('类别 ID 偏移')
assert '验证管线' in next_checks('val_bad', {'train_as_val_also_bad': True})[0][0]
assert next_checks('loss_flat', {'can_overfit_one_batch': False})[0][0].startswith('单 batch')

print('把本 notebook 的观察串成一次完整分诊：')
FACTS = dict(first_nan_iter=1, can_overfit_one_batch=False,
             train_as_val_also_bad=True, loss_periodic=False)
for sym, title in [('loss_nan', 'loss 变 NaN'), ('loss_flat', 'loss 不降'),
                   ('map_zero', 'mAP 恒为 0'), ('val_bad', '验证极差')]:
    print(f'\\n[{title}] 先做这两件事：')
    for nm, ck in next_checks(sym, FACTS, top=2):
        print(f'   · {nm}\\n     -> {ck}')
print('\\n✅ 练习 4 通过：调试的产物是**排好序的检查清单**，不是一个猜测。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def my_bce(z, y):
    z = np.asarray(z, dtype=np.float64) if np.ndim(z) else np.float64(z)
    return np.maximum(z, 0.0) - z * y + np.log1p(np.exp(-np.abs(z)))"""),

    code("""# 练习 2 参考答案
def detect_label_shift(cm):
    cm = np.asarray(cm)
    n = cm.shape[0]
    tot = int(cm.sum())
    best_k, best_m = 0, -1
    for k in range(-n + 1, n):
        m = int(sum(cm[i, i + k] for i in range(n) if 0 <= i + k < n))
        if m > best_m:
            best_k, best_m = k, m
    return best_k, (best_m / tot if tot else 0.0)"""),

    code("""# 练习 3 参考答案
def best_box_format(pred, gt, cands=None):
    cands = CANDS if cands is None else cands
    sc = {name: float(iou_pair(fn(pred), gt).mean()) for name, fn in cands.items()}
    return max(sc, key=lambda k: sc[k]), sc"""),

    code("""# 练习 4 参考答案
def next_checks(symptom, facts=None, top=2):
    return [(h['name'], h['check']) for h in diagnose(symptom, facts)[:top]]"""),

    md("""---
## 🧪 真实工程胶囊：调试手册（可原样贴进团队 wiki）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 检测模型调试手册 —— 症状 -> 检查顺序（每条都给「若成立会观察到什么」）
# ══════════════════════════════════════════════════════════════════════

# ── 0. 常驻的不变量测试（写成 pytest，不是出事才手写）──────────────────
#   test_encode_decode_roundtrip : decode(encode(box)) == box            (atol=1e-6)
#   test_loss_on_perfect_pred    : L(GT_as_pred, GT) < 1e-6
#   test_gt_as_prediction        : evaluate(GT_as_pred, GT).mAP == 1.0
#   test_grad_numeric            : 解析梯度 vs 数值梯度  rtol < 1e-4
#   test_dataset_sanity          : 所有框 w>1 and h>1 and 0<=x1<x2<=W；断言里打印文件名
#   test_class_table_md5         : 训练/评测两侧 classes.json 的 md5 必须一致

# ── 1. 【最先做】单 batch 过拟合 ────────────────────────────────────────
#   8-32 个样本，**关掉**：增强 / dropout / weight decay / lr warmup 与衰减 / EMA
#   通过条件：训练 loss < 1e-3 且训练集 mAP > 0.95
#   检测特有：**每步打印分到的正样本数**；n_pos == 0 说明问题在标签分配，不在网络
#   四种失败形态：
#     loss 一动不动        -> requires_grad / optimizer.param_groups / no_grad / lr=0
#     loss 停在初值附近     -> lr 过小；warmup 还没走完；大部分参数被冻
#     loss 停在非零平台     -> weight decay 没关 / 死亡神经元 / 只有 bias 可训练
#     loss -> 0 但 mAP = 0 -> **训练侧对、评测侧错**，直接跳到第 3 节

# ── 2. loss = NaN ──────────────────────────────────────────────────────
#   第一个问题永远是「它是第几个 iteration 出现的」
#     0-1 步     -> 数值实现或数据（log(0)、退化框 0/0、log(w<=0)）
#     几百步后   -> 学习率/发散（看 grad norm 是否指数上升）
#     固定 seed 后总在同一步 -> 某个特定样本，dump 那个 batch 的文件名
#   手写损失一律用 log-sum-exp 稳定式：max(z,0) - z*y + log1p(exp(-|z|))
#     朴素式的断点：float32 z≈17，float64 z≈37
#   IoU / GIoU 的分母一律 + 1e-9（真实数据里 x1==x2 的退化框并不罕见）
#   常驻记录：grad norm、各层 max|x|、**loss 各分项分开记**
#     只有 box 分项炸 -> 坏标注；所有分项同时炸 -> 学习率

# ── 3. mAP 恒为 0：三大元凶（各 3 分钟）────────────────────────────────
#   A. 预测类别整体 ±1 重算 mAP            -> 突然正常 = 类别 ID 偏移
#      指纹：混淆矩阵质量在偏移 k 格的次对角线上（detect_label_shift）
#   B. 框按 cxcywh/xywh/yxyx -> xyxy 各试一遍 -> IoU 从 0.0x 跳到 0.8+ = 格式错
#      指纹：**IoU 恰好为 0 的比例 ~100%**（定位不准时该比例 ~0%）
#            yxyx 的指纹是 corr(pred_cx, gt_cy) ~ 1 而 corr(pred_cx, gt_cx) ~ 0
#   C. diff 两侧类别表的**顺序**（不只是集合）-> 混淆矩阵是置换矩阵 = 类别表不一致
#   三条都过了才允许怀疑模型。「mAP 恰好是 0 而不是 0.3」本身就是线索。

# ── 4. 指标掉了但没归零（最危险，因为像「没调好」）──────────────────────
#   通道顺序 BGR/RGB : **颜色语义类崩、中性色类不掉**；x = x[..., ::-1] 后恢复
#   归一化 mean/std  : **所有类均匀掉点**；dump 一个 batch 比对通道均值
#   resize 插值/对齐 : **小目标掉得多、大目标几乎不掉**；同图两边逐元素 diff
#   ⚠️ 组合 bug 会污染指纹 -> 一次只改一个变量重测（单变量原则）

# ── 5. 训练好、验证崩 ──────────────────────────────────────────────────
#   决定性实验：**把训练集喂进验证的那条代码路径**
#     同样崩 -> 管线问题（预处理不一致 / 忘了 eval() / 类别表）
#     依然好 -> 真泛化问题（过拟合 / 捷径特征）
#   捷径特征的判据：按采集批次分桶，桶内好、跨桶崩

# ── 6. 分布式 ──────────────────────────────────────────────────────────
#   BN 不同步        : per-GPU batch < 16 时换 SyncBatchNorm
#   seed 全卡相同     : seed = base + rank；DataLoader 再叠 worker_id
#   忘了 set_epoch    : 每个 epoch 开头 sampler.set_epoch(epoch)  <- 最常忘
#   数据分片重叠      : len(sampler)*world_size 与数据集大小对比；评测结果按 id 去重
#   梯度累积          : loss 要除以累积步数，否则等效 lr 变成 k 倍

# ── 7. 复现失败的排查顺序（每步都比下一步便宜）─────────────────────────
#   ① 种子方差（检测任务 ±0.2-0.5 mAP 是常态）-> 先跑 3-5 个种子看分布
#   ② 代码版本（git status / pip freeze diff）
#   ③ 数据版本（标注文件 md5；数据是持续回流的）
#   ④ 随机性来源（python/numpy/框架/cudnn/worker；cudnn.benchmark 依赖硬件状态）
#   ⑤ 环境（驱动/CUDA/框架/卡型号 —— 换卡会改变 kernel 与浮点累加顺序）
#   ⑥ 最后才是「代码里有 bug」
#   发布候选版本必须在确定性模式下重跑并归档（固定 seed + deterministic + 镜像 + 数据快照）
'''
print(RECIPE)
for tok in ['单 batch 过拟合', 'log-sum-exp', 'float32 z≈17', 'IoU 恰好为 0',
            '颜色语义类崩', 'set_epoch', '种子方差', 'n_pos == 0']:
    assert tok in RECIPE, tok
print('✅ 手册覆盖：不变量测试 / 单batch过拟合 / NaN / mAP=0 三元凶 / 指纹 / 验证崩 / 分布式 / 复现')"""),

    md("""### 小结

- **调试的进展不是「试了很多东西」，而是「排除了很多可能」。**
  每一段链路都要有一个「必须成立的等式」：`decode∘encode = id`、`L(GT,GT)≈0`、
  数值梯度 == 解析梯度、`GT 当预测 -> mAP = 1.0`。**把它们写成常驻单元测试。**
- **「先把一个 batch 过拟合」是唯一无条件必须成立的实验。**
  它成立 ⇒ 数据/编码/前向/损失/反传/优化器整块可用，搜索空间立刻砍半；
  它不成立 ⇒ bug 一定在前六段。做之前必须关掉增强/dropout/weight decay/**warmup 与衰减**/EMA。
- **检测特有：必须同时打印正样本数。** RetinaNet 默认 anchor（P3–P7）下，
  **≤ 20 px 的交通标志拿不到任何 IoU ≥ 0.5 的正样本**——它对分类损失完全不可见。
  加一个 P2 层（stride 4 / base 16）能把 12–20 px 救回来。
- **NaN 的第一个问题永远是「第几个 iteration 出现的」。**
  0–1 步 ⇒ 实现或数据；几百步后 ⇒ 发散；固定 seed 后总在同一步 ⇒ 某个样本。
  手写损失一律用 log-sum-exp（朴素式断点：**float32 z≈17，float64 z≈37**），
  IoU 分母一律加 `eps`（真实标注里 `x1==x2` 的退化框并不罕见）。
- **mAP 恒为 0 的三大元凶**：类别 ID 偏移 / 坐标格式弄反 / 类别表不一致，
  各 3 分钟可查完。「mAP 恰好是 0 而不是 0.3」本身就是线索——
  **模型能力问题不会让指标精确归零。**
- **指纹思维把调试从「顺序搜索」变成「哈希查表」。** 构造指纹的通用方法是**找不对称**：
  通道顺序 → 颜色维度不对称（颜色类崩、中性色类不掉）；
  resize 不一致 → 尺寸维度不对称；类别表错位 → 类别维度呈置换结构；
  坐标格式 → **IoU 恰好为 0 的比例 ≈ 100%**（定位不准时 ≈ 0%）。
- **「验证集上差」不等于「过拟合」。** 决定性实验是把训练集喂进验证的代码路径：
  同样崩 = 管线问题，依然好 = 真泛化问题。这个实验 20 分钟能做完，结论是二值的。
- **复现失败先怀疑方差，不要先怀疑 bug。** 检测任务同配置不同种子的 mAP 波动
  典型是 ±0.2–0.5 个点，这一条排除掉的「bug」占了大半。

下一站：**模块 04 · 项目叙事** —— 把这些排查过程讲成让人信服的故事。"""),
]
