# -*- coding: utf-8 -*-
"""C58 模块 03 · 主动学习与线上触发策略。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–02（数据闭环、长尾、难例挖掘）；C55 m04（跟踪与时序融合）会让「多帧一致性」这一节读起来轻松很多"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_active_learning_triggers.ipynb'),
    ("核心参考", "Settles, <em>Active Learning Literature Survey</em>（2009）；Beluch et al., <em>The Power of Ensembles for Active Learning in Image Classification</em>（CVPR 2018）；Kirsch et al., <em>BatchBALD</em>（NeurIPS 2019）；Tesla / Waymo 关于影子模式与数据引擎的公开技术分享"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    # ─────────────────────────────────────────────────────────────
    ("budget", "问题重述：车队数据无限，标注预算有限", "".join([
        P("模块 02 讨论的是「<strong>已经标好的数据里，该多看哪些</strong>」。这一模块的问题完全不同，也更贴近量产："),
        P("<strong>一支 10 万辆车的车队，每天产生的视频数据以 PB 计。你的标注预算是每天几万个框。回传哪些帧？</strong>"),
        P("这就是 <span class=\"term\">active learning</span>（主动学习）在自动驾驶里的真实形态，而且它比教科书里的主动学习多了三个硬约束："),
        TABLE(["约束", "教科书主动学习", "<strong>车端主动学习</strong>"], [
            ["候选池", "几万个已存储的无标注样本", "<strong>近乎无限的流式数据</strong>，且大部分永远不会被存储"],
            ["打分时机", "可以离线跑大模型给全池打分", "<strong>必须在车端实时算</strong>（算力只剩几个百分点给触发器）"],
            ["选择方式", "全局排序取 top-k", "<strong>只能用阈值做在线判决</strong>（看到这一帧就得决定留不留，没有全局视野）"],
            ["回传成本", "≈ 0", "<strong>带宽有钱，且用户流量与隐私都要顾</strong>"],
            ["评价指标", "标注 N 个后的模型精度", "「回传的东西里有多少真的是 badcase」+ 「真 badcase 有多少被抓到」"],
        ]),
        P("换个角度看，<strong>这就是一个「二分类器」的设计问题</strong>：输入是一帧（或一小段），输出是「回传 / 丢弃」。它有 precision（回传的里面有多少真值钱）和 recall（真正的 badcase 抓到了多少），有工作点，有 PR 曲线，也有偏差。<em>把触发器当成一个需要评估的模型来对待，是这一模块最重要的思维转变</em>——而绝大多数人只把它当成「几行 if 语句」。"),
        ASCII("""车端触发 → 回传 → 挖掘 → 标注 → 训练 的完整链路

  ┌── 车端（实时，算力预算 < 5%）──────────────────────────────┐
  │                                                          │
  │  相机 ─► 感知模型 ─► 检测/分类结果 + 跟踪                    │
  │                          │                               │
  │                          ▼                               │
  │              ┌───────────────────────┐                   │
  │              │   触发器（三类并联）    │                   │
  │              │  ① 不确定性            │                   │
  │              │  ② 一致性（含多帧）     │                   │
  │              │  ③ 规则/事件           │                   │
  │              └───────────┬───────────┘                   │
  │                          │  触发率必须 <= 带宽预算          │
  │                          ▼                               │
  │              环形缓冲区（保留触发点前后 ±3s）                │
  │                          │  脱敏（人脸/车牌模糊）           │
  └──────────────────────────┼───────────────────────────────┘
                             ▼
  ┌── 云端 ────────────────────────────────────────────────┐
  │  回传队列 ─► **去重**（近重复检测/聚类）─► 多样性采样       │
  │                    │                                    │
  │                    ▼                                    │
  │            大模型/离线模型复检（离线可以跑 10× 大的模型）    │
  │                    │                                    │
  │                    ▼                                    │
  │            标注 ─► 训练 ─► 评测 ─► 门禁 ─► 发布            │
  │                                       │                 │
  │                    影子模式验证 ◄──────┘                 │
  └────────────────────────────────────────────────────────┘

  ⚠️ 整条链路的**瓶颈永远是标注**，所以触发器的 precision
     （回传的里面有多少值得标）直接决定整个数据飞轮的效率。""")
        ,
        DUAL(
            "先把最容易被忽略的一点说清楚：<strong>「回传什么」的答案不是「模型不确定的」，而是「能让模型变好的」</strong>。这两者只在一部分情况下重合。<em>模型对某一帧不确定，可能是因为那一帧真的信息不足（远处 8 像素的标志，标了也学不到）；模型对某一帧很确定，也可能是它<strong>自信地错了</strong>（把限速 80 稳稳当当认成 60）</em>。<strong>后一类才是最危险的，而它恰恰是不确定性触发器的系统性盲区</strong>——这是本模块的第 6 节主题。",
            "形式化一点：主动学习的理想目标是选出使<span class=\"term\">expected model change</span>（期望模型改变量）或期望误差下降最大的样本。但这两个量都需要「知道真标签」才能算，所以实践中只能用<strong>代理量</strong>：不确定性、分歧、规则命中。<em>每一个代理量都有它偏离真实目标的方式，而这些偏离在长期运行的闭环里会被不断放大</em>（因为下一版模型是在这些数据上训的，触发器又跟着模型走）。<strong>所以触发器组合里必须有一条「与模型无关」的通路</strong>——随机基线、规则、外部先验（高精地图），三者缺一不可。",
        ),
        CALLOUT("intuition", "把数字摆出来会更有感觉。假设每辆车每天行驶 1 小时、30 FPS，那就是 <strong>10.8 万帧/天/车</strong>。1 万辆车 = <strong>10.8 亿帧/天</strong>。如果标注预算是 5 万帧/天，<strong>触发率必须控制在 4.6×10⁻⁵</strong>——也就是<em>每两万帧里只能挑出一帧</em>。<strong>在这个量级下，触发器 precision 从 5% 提到 20% 意味着标注效率翻两番</strong>，其价值远超模型上的大部分改动。这也是 JD 里「define mining strategies for long-tail scenarios」这条职责的真实分量。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("uncertainty", "不确定性触发：三种度量与它们各自的失效方式", "".join([
        P("最基础的一类触发器。给定模型对某个框输出的类别概率分布 <code>p</code>，用一个标量刻画「模型有多不确定」。三种常用度量："),
        MATH("H(p) = -\\sum_{c} p_c \\log p_c, \\qquad\\quad M(p) = p_{(1)} - p_{(2)}, \\qquad\\quad LC(p) = 1 - p_{(1)}"),
        P("分别是<span class=\"term\">entropy</span>（熵）、<span class=\"term\">margin</span>（最大与次大概率之差）与 <span class=\"term\">least confidence</span>（最小置信度，即 1 减去最大概率）。它们看起来差不多，但在<strong>类别数很多的场景下差别巨大</strong>——而 TSR 恰好是类别数很多的场景（百来个细分类）。"),
        TABLE(["度量", "抓住的是", "在 TSR 上的表现", "失效场景"], [
            ["<strong>熵 H(p)</strong>", "整个分布的弥散程度", "<strong>会被「长尾小概率」拉高</strong>：100 个类各分到 0.5% 的残余概率，熵就已经不低了，即使 top-1 是 0.5", "类别数多时对「真正的二选一混淆」不敏感；<em>被无关类的噪声概率污染</em>"],
            ["<strong>margin M(p)</strong>", "<strong>最像样的两个候选之间的竞争</strong>", "<strong>TSR 上最好用</strong>：限速 60 vs 80、禁止驶入 vs 禁止通行，都是典型的二选一", "三个及以上类别势均力敌时会低估不确定性"],
            ["<strong>least confidence</strong>", "只看 top-1 有多高", "最便宜（不需要排序），常用于车端粗筛第一层", "完全忽略「输给谁」；0.5 对 0.49 与 0.5 对 0.05 被视为一样"],
        ]),
        DUAL(
            "<strong>选哪个？在 TSR 这类「细粒度多类别 + 混淆成对出现」的任务上，margin 明显优于熵</strong>。原因很具体：熵是全分布的函数，当类别数 C 很大时，即使模型已经把答案锁定在两个类之间，剩下 C-2 个类上残余的小概率仍会贡献可观的熵值——<em>于是熵在「限速 60 vs 80」和「一片模糊什么都不像」这两种完全不同的情况上给出接近的分数</em>。而 margin 只看前两名，正好对应了 TSR 的错误结构。",
            "但有一个前提条件必须先满足：<strong>这三个度量都建立在「softmax 概率是可信的」这一假设上，而现代神经网络的 softmax 是<em>系统性过自信</em>的</strong>（Guo et al., 2017）。<em>未校准的模型上，0.9 的置信度可能对应 70% 的真实正确率</em>，这会让阈值完全失去意义，而且校准误差在不同类别、不同尺寸桶上还不一样（小目标通常更过自信）。<strong>所以不确定性触发器上线前必须先做校准</strong>（温度缩放最简单），并且<strong>按尺寸/光照分桶分别校准</strong>——否则触发器会系统性偏向某些桶。",
        ),
        CALLOUT("warn", "还有一个检测特有的维度常被忘掉：<strong>定位不确定性</strong>。分类概率只刻画「是什么」，不刻画「在哪里」。一个框如果类别很确定但<em>位置抖动很大</em>（多帧之间 IoU 反复跳、或用 MC-dropout / TTA 时框位置方差大），同样是值得回传的 badcase。<em>在 TSR 里这尤其重要——远处小标志的框抖动会直接导致跟踪断裂</em>。<strong>实现上可以用「回归头输出分布的方差」（如 GFL 的 distribution focal loss 天然给出分布）或「多帧框位置的方差」</strong>，成本都很低。"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("aggregate", "框级 → 图级：检测里最容易做错的一步聚合", "".join([
        P("上一节的度量都定义在<strong>单个框</strong>上，但回传决策是<strong>整帧（或整段）</strong>的。<em>这一步聚合看起来是个小细节，实际上它决定了触发器会系统性偏向什么样的场景</em>。"),
        TABLE(["聚合算子", "定义", "偏向什么", "什么时候用"], [
            ["<strong>max</strong>", "<code>U = max_j u_j</code>", "<strong>只要有一个可疑框就触发</strong>。对「单个关键错误」最敏感", "<strong>默认选择</strong>；TSR 关心的是「有没有一个标志被认错」而不是平均质量"],
            ["<strong>mean</strong>", "<code>U = mean_j u_j</code>", "<strong>偏向框少的帧</strong>：一帧只有 1 个可疑框时 mean 很高，10 个框里 1 个可疑时 mean 被稀释", "几乎不该单独用——它会系统性漏掉复杂路口"],
            ["<strong>top-k mean</strong>", "最高的 k 个的均值", "介于两者之间，比 max 抗噪", "k=2~3，对单帧噪声更稳"],
            ["<strong>count 超阈</strong>", "<code>U = #{j : u_j > τ}</code>", "<strong>偏向框多的帧</strong>（拥挤路口天然计数高）", "要做归一化才能用，否则触发的全是市区路口"],
            ["<strong>加权（按尺寸/距离）</strong>", "<code>U = max_j w_j u_j</code>", "可以显式偏向「近处大标志」或「远处小标志」", "<strong>与安全代价挂钩时用</strong>：近处的错误后果更严重"],
        ]),
        P("这里有一个必须点破的偏差机制："),
        CALLOUT("danger", "<p><strong>用 <code>mean</code> 聚合，会让触发器系统性地漏掉「复杂场景」；用 <code>count</code> 聚合，会让触发器几乎只回传市区拥挤路口</strong>。两者都是<em>由聚合算子引入的、与模型无关的采样偏差</em>——而它会在闭环里被固化：回传的数据偏向某类场景 → 模型在那类场景上变好 → 其他场景的问题永远发现不了。<em>这类偏差比模型的问题更难察觉，因为它不体现在任何模型指标上。</em></p>", "聚合算子是一个隐藏的采样偏差源")
        ,
        P("除了聚合算子，还要处理三个检测特有的细节："),
        OL([
            "<strong>只对「已检出的框」算不确定性，会漏掉漏检</strong>。模型完全没检出的目标，压根不会产生任何框级分数。<em>解法是同时用低阈值的候选（比如 score &gt; 0.05 的所有 proposal）参与打分</em>，或者依赖规则触发（跟踪丢失、地图先验）来覆盖漏检。<strong>这是不确定性触发器的第二个结构性盲区</strong>（第一个是「自信地错」）。",
            "<strong>要不要按框数归一化</strong>。如果用 max，不需要；如果用 count 或 sum，必须除以框数或做长度归一化，否则触发率与场景复杂度强相关。",
            "<strong>时间维度上的去重</strong>。30 FPS 下，一个 badcase 会连续触发几十帧。<em>必须做时间窗内抑制</em>（同一 track、同一场景在 N 秒内只触发一次），否则带宽预算会被少数几个片段吃光。<strong>这是「触发器 NMS」——和模块 02 里 OHEM 的 NMS 去重是同一个道理</strong>：不去重，预算就被少数几件事重复消耗。",
        ]),
        DUAL(
            "第三条特别值得展开：<strong>在时序数据上，「触发一次」和「触发一段」是完全不同的成本</strong>。一次触发实际回传的是触发点前后各 3 秒（约 180 帧）的片段。<em>如果不做时间窗抑制，一段 10 秒的困难路段可能产生 200 次触发、回传 200 个高度重叠的片段</em>——占满预算却只贡献一个场景的信息。",
            "正确做法是<strong>两级抑制</strong>：车端做<em>时间窗抑制</em>（同一 track 在 T 秒内只触发一次，且优先保留分数最高的那一帧）；云端做<em>内容去重</em>（感知哈希 / 嵌入聚类，见模块 04）。<strong>两级都需要，因为车端不知道这个路口昨天已经回传过 50 次了，而云端不知道这 200 帧其实是同一个 3 秒</strong>。<em>把这两级说清楚，就说明你理解了「触发」是一个分布式系统问题而不是一个打分问题。</em>",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("consistency", "一致性触发：多模型分歧，以及 TSR 的杀手锏「多帧不一致」", "".join([
        P("不确定性触发器只能看到<strong>模型自己报告的</strong>不确定性——而它系统性地不报告「自信地错了」那一类。一致性触发器绕开了这个问题：<strong>它不问模型「你有多确定」，而是把同一个东西的多个独立预测放在一起，看它们对不对得上</strong>。"),
        TABLE(["一致性来源", "怎么做", "抓到什么", "车端可行性"], [
            ["<strong>多模型分歧</strong>（query-by-committee）", "K 个独立训练的模型投票，算 vote entropy 或平均 JS 散度", "「模型集体不确定」与「单模型自信但集体分歧」两类", "<strong>车端跑不动 K 个模型</strong>；通常只在云端影子复检时用"],
            ["<strong>TTA 分歧</strong>", "同一帧做翻转/多尺度推理，看结果是否一致", "对增强不鲁棒的样本；标注边界模糊的样本", "延迟翻倍，车端一般只在低负载时抽样开启"],
            ["<strong>教师-学生分歧</strong>", "车端小模型 vs 云端/离线大模型的预测差异", "<strong>蒸馏损失最大的样本</strong>——直接对应「小模型学不会的东西」", "车端只跑学生；分歧在云端影子模式里算"],
            ["<strong>多帧不一致</strong>（temporal inconsistency）", "同一个 track 在连续帧上的类别序列是否跳变", "<strong>TSR 上极其有效</strong>——见下文", "<strong>几乎零成本</strong>（跟踪本来就要跑），车端首选"],
        ]),
        H3("为什么「多帧不一致」在 TSR 上如此有效"),
        P("因为交通标志有一个别的目标没有的强物理性质：<strong>它是静止的刚体，类别在时间上恒定</strong>。一个限速 60 的标志，在车辆接近的整个过程中永远是限速 60。所以——"),
        CALLOUT("intuition", "<strong>同一个 track 上出现类别跳变，就是一个「无需标注即可确认的错误」</strong>：不管跳变前后哪一帧是对的，<em>至少有一帧一定是错的</em>。这是一个<strong>免费的、零标注成本的自动标签</strong>——你不需要知道正确答案，就能确定「这里出了问题」。<em>行人跟踪、车辆跟踪都没有这个性质（它们的属性会真的变化），这是 TSR 独有的红利。</em>"),
        ASCII("""多帧一致性触发：同一个 track 的类别序列

  帧号:      t0    t1    t2    t3    t4    t5    t6    t7
  距离:     80m   70m   60m   50m   40m   30m   20m   15m
  像素:      9px  11px  13px  16px  20px  27px  40px  53px

  ✅ 正常 track（无需回传）
     类别:   SL60  SL60  SL60  SL60  SL60  SL60  SL60  SL60
     置信:   0.42  0.51  0.63  0.75  0.88  0.94  0.97  0.98
     → 类别恒定，置信度随距离单调上升 —— 教科书式的正常行为

  ⚠️ 类别跳变 track（**必须回传**）
     类别:   SL80  SL80  SL80  SL60  SL60  SL60  SL60  SL60
     置信:   0.91  0.93  0.88  0.72  0.85  0.93  0.96  0.98
                              ↑
              **远处「自信地」认成 SL80，近处才纠正过来**
              · 单帧不确定性完全抓不到（t0-t2 的置信度都 > 0.88）
              · 多帧一致性一抓一个准，而且**自动告诉你哪几帧错了**
                （用近处高置信的结果反标远处的低分辨率帧 = **免费的困难样本**）

  ⚠️ 闪烁 track（**必须回传**）
     类别:   SL60  SL80  SL60  SL80  SL60  SL60  SL60  SL60
     → 跳变次数 = 4，典型的「决策边界上反复横跳」

  可用的量化指标：
     flip_count      = 相邻帧类别变化次数
     mode_fraction   = 众数类别占比（越低越不一致）
     class_entropy   = track 上类别分布的熵
     stabilize_frame = 第几帧之后不再变（越晚越糟）""")
        ,
        DUAL(
            "「多帧不一致」不只是一个触发器，它还是一台<strong>自动标注机</strong>。因为 TSR 有一个额外的结构：<em>置信度随距离单调上升</em>——近处的预测几乎总是对的。<strong>于是可以用「近处高置信的结果」去反标「远处低分辨率的同一个 track」</strong>，自动产出一批「远距离小目标 + 正确标签」的困难样本，而这正是 TSR 最缺的数据类型。<em>这个技巧的正式名字叫 auto-labeling by temporal propagation / track-level label propagation，在量产系统里价值极高。</em>",
            "但要小心两个失效条件。<strong>① 跟踪本身可能错</strong>：如果两个相邻的标志被跟成同一个 track（ID switch），类别「跳变」其实是跟踪的错，不是分类的错。<em>所以反标之前必须先验证 track 的纯度</em>（用几何一致性：静止标志在自车运动下的图像位置是可预测的，偏离预测太多就说明 track 有问题）。<strong>② 可变电子牌的类别是真的会变的</strong>——限速 80 的电子牌可能在你接近的过程中变成 60。<em>这类标志必须从「类别恒定」假设里排除掉，否则你会把真实变化当成模型错误反复回传</em>。<strong>这两条例外是这个技巧能不能真正落地的分水岭。</strong>",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("rules", "规则触发：最便宜、最可解释，也最容易被低估", "".join([
        P("第三类触发器完全不依赖模型的输出分布，而是依赖<strong>系统级的、可以被外部验证的矛盾</strong>。它们的共同结构是：「<em>如果系统是对的，这件事不该发生；它发生了，所以某处出错了</em>」。"),
        TABLE(["规则触发器", "信号", "抓到什么类型的 badcase", "误触发风险 / 注意事项"], [
            ["<strong>检测到但跟踪丢失</strong>", "一个 track 存在 &lt; N 帧就消失，且不是因为出画面", "<strong>不稳定检测</strong>：远距离小目标、遮挡边缘、光照突变（隧道出入口）", "真实遮挡（被大车挡住）也会触发 → 要结合几何判断是否出画面"],
            ["<strong>阈值附近震荡</strong>", "score 在工作点阈值上下反复穿越（如 0.48↔0.52）", "<strong>决策边界样本</strong>——这批数据的边际信息量最高", "阈值附近本来就有大量样本 → <strong>触发率容易失控</strong>，必须配时间窗抑制"],
            ["<strong>与高精地图不符</strong>", "地图记录此处有「限速 60」，模型报「限速 80」或什么都没报", "<strong>直击「自信地错了」与漏检两大盲区</strong>（不确定性触发完全抓不到的两类）", "<strong>地图本身会过期</strong>（施工改道、限速调整）→ 触发的可能是「地图该更新了」，这同样有价值但要分开处理"],
            ["<strong>接管 / 急刹 / 急打方向前后</strong>", "驾驶员接管、AEB 触发、纵向加速度 &lt; -3 m/s²", "<strong>与安全后果直接相关的场景</strong>，价值密度最高", "多数接管与 TSR 无关 → 需要二次筛选（回传后用离线模型复检）"],
            ["<strong>罕见类别命中</strong>", "模型报出了一个长尾类（哪怕置信度很高）", "长尾类的真实分布样本 —— <strong>正是模块 01 最缺的</strong>", "罕见类的误报也很多 → 精确率天然低，但因为量小，绝对成本可控"],
            ["<strong>地理/时间围栏</strong>", "进入新城市、新国家、夜间、恶劣天气", "<strong>域偏移场景</strong>的主动覆盖", "与模型无关，是纯粹的分布覆盖策略 → <strong>这是对抗触发器偏差的重要一环</strong>"],
        ]),
        P("规则触发器有三个被严重低估的优点："),
        UL([
            "<strong>它们与模型无关</strong>。不确定性和一致性触发器都是模型的函数，所以它们的盲区会随着模型一起演化（模型在某处系统性地错，触发器也就在那处系统性地沉默）。<em>规则触发器打破了这个耦合</em>。",
            "<strong>它们可解释、可审计</strong>。「与高精地图不符」这个触发条件，可以直接生成一句人能读懂的说明，标注员和工程师都能立刻理解在看什么。<em>而「熵 &gt; 1.7」不能。</em>",
            "<strong>它们几乎不花算力</strong>。跟踪、地图匹配、车辆信号本来就在跑，触发条件只是几个比较。<em>在车端只剩几个百分点算力的约束下，这是决定性的优势</em>。",
        ]),
        CALLOUT("warn", "但规则触发器有一个共同的失效模式：<strong>规则会随着系统演进而悄悄失效</strong>。「跟踪丢失」这条规则的触发率，会因为跟踪器换了一版而整体漂移；「与高精地图不符」会因为地图版本更新而突然爆量。<em>所以每条规则触发器都必须有<strong>触发率监控</strong>与告警</em>——<strong>触发率的异常漂移本身就是一个极有价值的信号</strong>：它意味着模型、跟踪器、地图或真实世界中的某一个变了。<em>在成熟的团队里，触发率看板与模型指标看板是同等重要的两块屏。</em>"),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("bias", "触发器本身会引入偏差：「模型自信地错了」这个系统性盲区", "".join([
        CALLOUT("danger", "<p><strong>本模块最深的一个洞察：只回传「模型不确定的」样本，会系统性地漏掉「模型自信地错了」的样本。</strong> 而在安全关键系统里，<em>后者才是真正会出事的那一类</em>——模型不确定时，下游还能靠迟滞、多帧投票、保守策略兜住；模型自信地错时，整条链路都会相信它。</p>", "不确定性触发器的结构性盲区")
        ,
        ASCII("""把所有样本按「置信度 × 是否正确」摆成四象限

                        正确                     错误
              ┌───────────────────────┬───────────────────────┐
              │                       │                       │
     高置信度  │   ① 已经学会           │  ② **自信地错了**       │
              │   （占绝大多数）        │   ⚠️ **最危险**         │
              │   回传价值 ≈ 0         │   回传价值 **最高**      │
              │                       │                       │
              │   不确定性触发：不触发 ✅│  不确定性触发：**不触发** ❌│
              │                       │   ← **系统性盲区**      │
              ├───────────────────────┼───────────────────────┤
              │                       │                       │
     低置信度  │   ③ 蒙对了 / 边界       │  ④ 不确定且错了         │
              │   回传价值 中           │   回传价值 高           │
              │                       │                       │
              │   不确定性触发：触发 ⚠️  │   不确定性触发：触发 ✅  │
              │   （**误触发**，占用预算）│                       │
              └───────────────────────┴───────────────────────┘

  不确定性触发器实际做的是「按行切」（只看下面那一行），
  而我们真正想要的是「按列切」（只看右边那一列）。
  **两者的交集只有 ④ 一格。**

  ⇒ 象限 ② 只能靠：**一致性触发（多帧/多模型）** + **规则触发（地图/事件）**
    + **随机基线采样**（唯一能覆盖「未知的未知」的通路）""")
        ,
        P("这个盲区还有一个更麻烦的性质：<strong>它是自我强化的</strong>。"),
        OL([
            "触发器只回传模型不确定的样本 →",
            "标注 + 训练后，模型在「原本不确定的区域」上变得确定 →",
            "下一轮触发器在这些区域沉默，转向新的不确定区域 →",
            "<strong>而象限 ② 的那些样本，模型从一开始就很确定，所以从头到尾都不会被触发</strong> →",
            "<strong>这块盲区会一直存在，而且不会体现在任何离线指标上</strong>（因为验证集是从同一个有偏的回传流里抽的）。",
        ]),
        TABLE(["偏差来源", "具体机制", "会漏掉什么", "对策"], [
            ["<strong>不确定性偏差</strong>", "只按模型自报的不确定性选样本", "<strong>象限 ②：自信地错</strong>", "一致性触发 + 规则触发 + 随机基线"],
            ["<strong>漏检不可见</strong>", "没有检出就没有框，也就没有分数", "模型完全没看到的目标（远处、极端遮挡）", "低阈值候选参与打分；地图先验；跟踪丢失规则"],
            ["<strong>聚合偏差</strong>", "mean 偏向框少的帧，count 偏向拥挤帧", "整类场景（简单场景 / 复杂路口）", "用 max 或 top-k mean；<strong>按场景桶分别设阈值</strong>"],
            ["<strong>触发率的地理/时段偏差</strong>", "触发率在夜间/雨天天然更高 → 预算被这些时段吃光", "白天晴天下那些「罕见但确实存在」的错误", "<strong>按桶分配预算</strong>而不是全局阈值"],
            ["<strong>闭环反馈偏差</strong>", "触发器是模型的函数，模型是回传数据的函数", "<strong>盲区会被固化并随时间加深</strong>", "<strong>固定比例的随机采样（10–20%）作为无偏基线</strong>，并用它定期审计触发器"],
        ]),
        DUAL(
            "<strong>随机基线采样是这一整套里最容易被砍掉、也最不能砍的一环</strong>。它看起来极其低效——随机回传的帧里 99% 都是模型已经会的东西。但它有一个无可替代的作用：<em>它是唯一一条不经过模型判断的数据通路，因此是唯一能发现「未知的未知」的手段</em>。<strong>而且它同时提供了一个无偏的评测集</strong>——所有触发器的 precision / recall 都必须在这个无偏样本上度量，否则你根本不知道自己漏了多少。",
            "具体做法：<strong>把总预算的 10%–20% 划给纯随机采样（分层随机更好：按地理/时段/天气分层）</strong>，这批数据有两个用途——① 作为触发器的<strong>评测集</strong>：在这上面标注全部样本，就能算出每个触发器的真实 recall（分母是所有真 badcase，而不是「被触发的 badcase」）；② 作为模型的<strong>无偏验证集</strong>：它的分布才是真实路况分布，而回传流的分布已经被触发器扭曲了。<em>面试里能主动说出「必须留一部分随机采样做无偏审计」，是判断一个人是否真的做过闭环的分水岭</em>。",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("pr_budget", "把触发器当模型来评：PR 分析与带宽预算下的阈值优化", "".join([
        P("既然触发器是一个二分类器，就应该用二分类器的方式评估它。定义清楚三个量："),
        UL([
            "<strong>触发率</strong> <code>rate = P(触发)</code>——这是<em>成本</em>，直接对应带宽与标注预算；",
            "<strong>精确率</strong> <code>precision = P(是真 badcase | 触发)</code>——回传的东西里有多少值得标；",
            "<strong>召回率</strong> <code>recall = P(触发 | 是真 badcase)</code>——真 badcase 抓到了多少。<em>注意分母必须来自随机基线采样，否则算不出来。</em>",
        ]),
        P("于是「设阈值」就变成一个标准的<strong>约束优化</strong>问题：在总触发率不超过预算 B 的前提下，最大化召回。多个触发器并联时（OR 关系），目标写成："),
        MATH("\\max_{\\tau_1,\\dots,\\tau_T}\\; \\Big|\\bigcup_{t} S_t(\\tau_t) \\cap \\mathcal{B}\\Big| \\qquad \\text{s.t.} \\qquad \\Big|\\bigcup_{t} S_t(\\tau_t)\\Big| \\;\\le\\; B\\cdot N"),
        P("其中 <code>S_t(τ_t)</code> 是触发器 t 在阈值 τ_t 下选中的帧集合，<code>𝓑</code> 是真 badcase 集合。<strong>因为是「集合并集的覆盖」，这是一个 submodular（次模）最大化问题</strong>——贪心算法有 <code>1-1/e ≈ 63%</code> 的近似保证，而且实现只要十几行。<em>notebook 里会把这个贪心分配器写出来。</em>"),
        TABLE(["组合方式", "怎么算", "优点", "问题"], [
            ["<strong>OR（并联）</strong>", "任一触发器命中即回传", "召回高；各触发器独立可调、可单独下线", "<strong>触发率是并集</strong>，重叠部分白白算了两次预算 → 必须做全局去重"],
            ["<strong>AND（串联）</strong>", "多个同时命中才回传", "精确率高", "召回极低；容易只留下最平凡的 badcase"],
            ["<strong>加权打分</strong>", "<code>s = Σ w_t·u_t</code>，对 s 设单一阈值", "只有一个阈值要调；天然做了融合", "<strong>可解释性差</strong>；某个触发器坏掉时不易发现；权重难标定（量纲不同）"],
            ["<strong>级联</strong>", "车端便宜触发器粗筛 → 云端贵触发器精筛", "<strong>算力与带宽最优</strong>", "两级都要维护；粗筛的漏检无法被精筛挽回"],
            ["<strong>按桶配额</strong>", "每个场景桶（夜间/雨天/城区…）独立预算", "<strong>直接消除地理/时段偏差</strong>", "桶的划分本身是一个设计决策，需要定期回顾"],
        ]),
        H3("量产系统里的真实做法：级联 + 按桶配额 + 随机基线"),
        P("把上面几条合起来，一个能上车的配置大致是这样：<strong>车端跑最便宜的三个触发器（多帧一致性、跟踪丢失、地图不符）做粗筛，触发率控制在 10⁻³ 量级；回传后在云端用大模型 + 多模型分歧做精筛，把 precision 提到 20–40%；总预算按场景桶分配，每桶有独立配额；额外划 15% 给分层随机采样做无偏审计</strong>。<em>这套结构的每一部分在前面都有对应的理由，没有一条是拍脑袋的。</em>"),
        DUAL(
            "调阈值时有一个非常实用的经验：<strong>不要直接调「熵 &gt; 1.7」这种绝对阈值，而是调「触发率」这个百分位</strong>。因为绝对阈值会随模型版本漂移——换一版模型，同样的熵阈值可能让触发率翻十倍，直接打爆带宽。<em>而按分位数设阈（「触发 top-0.1% 最高熵的帧」）天然是自适应的</em>。<strong>实现上需要车端维护一个滑动窗口的分位数估计</strong>（P² 算法或简单的直方图即可），成本很低。",
            "还有一个必须提前设计的东西：<strong>安全阀（circuit breaker）</strong>。触发率一旦异常升高（模型换版、进入新区域、天气突变），必须能自动降级——例如把阈值临时上调、或直接停止回传并告警。<em>没有安全阀的触发器，会在某个雨夜把整个车队的流量打满</em>。<strong>这条在面试里说出来，会立刻显出「上过线」和「只写过 notebook」的区别</strong>：任何在车端持续运行、且消耗共享资源的组件，都必须有自我限流的能力。",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("shadow", "影子模式与线上工程：触发器怎么真的跑在车上", "".join([
        P("<span class=\"term\">shadow mode</span>（影子模式）是这套体系的运行载体：<strong>新模型（或新触发器）在车上实时运行，但它的输出不接入控制，只用于与线上模型对比、记录分歧</strong>。它同时解决了三个问题——验证新模型、发现 badcase、收集数据——所以是量产团队的标配。"),
        TABLE(["影子模式的三种用法", "比什么", "产出", "注意"], [
            ["<strong>新模型 vs 线上模型</strong>", "两者的检测/分类结果差异", "<strong>发布前的真实路况验证</strong>，不用等 A/B", "只知道「不一样」，不知道「谁对」→ 分歧片段仍需标注或大模型复检"],
            ["<strong>大模型 vs 车端小模型</strong>", "教师-学生分歧", "<strong>蒸馏最需要的样本</strong> + 车端模型的能力边界", "大模型跑不动就只能抽样跑，或者回传后在云端跑"],
            ["<strong>新触发器 vs 旧触发器</strong>", "触发率、重叠度、命中率", "触发器本身的 A/B 验证", "<strong>触发器也需要灰度发布</strong>，直接全量上线会打爆带宽"],
        ]),
        P("车端落地时的五个硬约束，每一条都会实实在在地砍掉一些方案："),
        OL([
            "<strong>算力预算</strong>：TSR 只是众多感知任务之一，触发器能分到的算力常常不足 1 ms/帧。<em>这直接排除了「车端跑 K 个模型做分歧」，也排除了大部分 TTA 方案</em>。多帧一致性与规则触发之所以是首选，正是因为它们几乎免费。",
            "<strong>存储与环形缓冲</strong>：触发发生时，你需要的是<em>触发点之前</em>的几秒（问题往往在触发前就开始了）。所以必须常驻一个环形缓冲区，滚动保存最近 N 秒的原始帧。<strong>缓冲区大小 = 回看时长 × 帧率 × 分辨率，是一笔要提前算的账。</strong>",
            "<strong>隐私与合规</strong>：回传前必须对人脸、车牌做模糊/脱敏，且要满足数据出境与用户授权的要求。<em>脱敏本身要花算力，且做得太狠会破坏训练数据的有效性</em>（把整块区域涂黑会制造训练-推理不一致）。",
            "<strong>触发器的版本与回滚</strong>：触发器配置（阈值、开关、桶配额）必须像模型一样有版本、可灰度、可远程回滚。<em>「改一个阈值要等下次 OTA」是不可接受的</em>。",
            "<strong>触发率监控与安全阀</strong>：实时上报每个触发器的触发率与带宽占用，异常时自动降级。<strong>触发率漂移本身是最早的系统异常信号</strong>——它比模型指标更早暴露「环境变了」或「上游变了」。",
        ]),
        ASCII("""触发器的评估看板（每天该看的几个数）

  ┌─────────────────────────────────────────────────────────────┐
  │ 触发器            触发率      带宽占比   精确率*   新场景占比  │
  ├─────────────────────────────────────────────────────────────┤
  │ 多帧类别跳变      3.2e-4      28%       34%      12%        │
  │ 跟踪丢失          5.1e-4      44%       18%       9%        │
  │ 地图不符          0.9e-4       8%       61%      31%   ★    │
  │ margin 低         1.4e-4      12%       22%       4%        │
  │ 接管/急刹前后     0.3e-4       3%       47%      22%        │
  │ **分层随机基线**   0.6e-4       5%        2%      **41%** ★★ │
  ├─────────────────────────────────────────────────────────────┤
  │ 合计（去重后）    9.8e-4     100%       29%      —          │
  │ 预算上限         10.0e-4                                    │
  └─────────────────────────────────────────────────────────────┘
   * 精确率的分母是回传量，分子是「经复检确认确实是 badcase」
   ★  地图不符精确率最高 —— 因为它用了**模型之外的外部真值**
   ★★ 随机基线精确率最低（2%），但**新场景占比最高（41%）** ——
      它是唯一能发现「未知的未知」的通路，砍掉它就等于关闭了这条路

  必看的三个趋势：
    · 触发率是否漂移（模型/跟踪/地图/环境变了）
    · 触发器之间的**重叠度**（重叠高 = 有一个是冗余的，可以省预算）
    · 从触发到修复上线的**周期时间**（这才是数据闭环真正的 KPI）""")
        ,
        DUAL(
            "最后一行值得单独强调：<strong>数据闭环的核心 KPI 不是「回传了多少数据」，而是「从发现问题到修复上线的周期时间」</strong>。<em>回传量是投入，修复速度才是产出</em>。一个每天回传 100 万帧但修一个 badcase 要六周的团队，远不如一个每天回传 5 万帧但两周就能闭环的团队。<strong>而周期时间的瓶颈通常不在模型，在标注排期与门禁流程</strong>——这也是模块 05 的主题。",
            "从这个角度反推，触发器设计还有一个常被忽略的目标：<strong>让回传的数据「好标」</strong>。同样是 badcase，一个「远处 9 像素的模糊标志」标注员标不了（也标不准），而一个「近处清晰但被认错的标志」几分钟就能标完且质量高。<em>所以触发时最好带上「可标注性」的信号</em>——比如优先回传那些「同一 track 里既有远处的困难帧、也有近处的清晰帧」的片段，<strong>这样标注员标一次近处，就能通过 track 传播反标出整段的困难样本</strong>。<em>这是把第 4 节的时序反标技巧反过来用于触发器设计，收益极高而几乎无人在意。</em>",
        ),
    ])),

    # ─────────────────────────────────────────────────────────────
    ("frontier", "研究前沿与开放问题", "".join([
        P("主动学习是一个有 30 年历史的领域，但它在深度学习 + 流式车队数据上的形态，绝大部分问题仍然是开放的。"),
        UL([
            "<strong>批量主动学习的多样性问题</strong>：按不确定性取 top-k 会选出<em>一批互相高度相似</em>的样本（都是同一个失效模式），信息严重冗余。<em>BatchBALD</em>（Kirsch et al., NeurIPS 2019）用互信息显式建模了批内冗余；<em>Core-set</em>（Sener &amp; Savarese, ICLR 2018）从覆盖角度选样本。<strong>但两者在千万级流式数据上都跑不动</strong>——如何在「只能看一遍、只能用阈值」的在线设定下保证批多样性，目前没有好答案。",
            "<strong>不确定性估计本身的可靠性</strong>：深度集成（deep ensembles）目前仍是最可靠的不确定性来源，但车端跑不起。单模型近似（MC-dropout、evidential deep learning、Laplace 近似、conformal prediction）各有各的问题。<em><span class=\"term\">Conformal prediction</span>（保形预测）因为能给出有覆盖率保证的预测集合，近年在自动驾驶里关注度上升很快</em>——它对触发器的意义是：<strong>可以把「触发率」直接和「真实错误率的上界」挂钩</strong>，而不是靠经验调阈值。",
            "<strong>「自信地错了」的检测</strong>：这是本模块指出的核心盲区，也是学术上的开放问题。相关方向包括 <span class=\"term\">OOD detection</span>（分布外检测）、<span class=\"term\">failure prediction</span>（失败预测，训练一个专门预测「主模型会不会错」的辅助模型）、以及用外部先验（地图、物理约束、多传感器一致性）做交叉验证。<em>其中「用物理/几何约束做自监督验证」在自动驾驶里最有前途，因为它完全不依赖模型自身的判断。</em>",
            "<strong>主动学习的理论保证在深度模型上基本失效</strong>：经典主动学习的样本复杂度分析依赖凸性与可实现性假设，深度网络两个都不满足。<em>实践中甚至存在「主动学习不如随机采样」的报告</em>（尤其在数据量已经很大、或不确定性估计很差时）——<strong>所以「用随机基线作对照」不只是工程上的谨慎，也是学术上的必需</strong>。",
            "<strong>用 VLM 做触发器</strong>：直接让视觉-语言模型判断「这一帧有没有异常/罕见场景」，可以表达远比阈值规则丰富的条件（「有临时施工标志」「有被遮挡一半的限速牌」）。<em>目前的瓶颈是车端跑不动，所以只能作为云端二级筛选</em>；蒸馏出一个极小的「场景异常打分器」放到车端，是当前很热的工程方向，也直接对应 JD 里的「automated data mining workflows」。",
            "<strong>闭环反馈偏差的理论刻画</strong>：触发器 → 数据 → 模型 → 触发器 是一个反馈系统，它会收敛到什么分布？盲区会如何演化？<em>这与推荐系统里的 feedback loop / filter bubble 研究是同构问题</em>，但在感知系统上几乎没有系统性研究。<strong>目前唯一可靠的对策仍然是那条最朴素的：留一条不经过模型的随机通路。</strong>",
        ]),
        CALLOUT("paper", "必读：Settles, <em>Active Learning Literature Survey</em>（2009）——把不确定性采样、query-by-committee、expected model change 等基本框架讲全了，读第 3 章即可；Beluch et al., <em>The Power of Ensembles for Active Learning in Image Classification</em>（CVPR 2018）——证明集成分歧优于 MC-dropout，是「一致性触发」的实证基础；Kirsch et al., <em>BatchBALD</em>（NeurIPS 2019）——批量选择的冗余问题与互信息解法；Sener &amp; Savarese, <em>Active Learning for CNNs: A Core-Set Approach</em>（ICLR 2018）——覆盖视角，与模块 04 的多样性采样直接相关；Guo et al., <em>On Calibration of Modern Neural Networks</em>（ICML 2017）——不确定性触发器的前提条件；Lakshminarayanan et al., <em>Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles</em>（NeurIPS 2017）；Angelopoulos &amp; Bates, <em>A Gentle Introduction to Conformal Prediction</em>（2021）——把触发率与错误率上界挂钩的现代工具。相邻模块：C58 m02（难例挖掘）、C58 m04（大规模挖掘基础设施）、C58 m05（闭环验证）、C55 m04（时序融合与跟踪）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · 主动学习与线上触发策略（不确定性 / 一致性 / 规则 / 偏差审计 / 预算优化）

目标：把「回传什么」做成一个**可度量、可优化、可审计**的系统。
你会亲手造出一条带 ground truth 的合成 TSR 检测流，然后实现三类触发器，
并用它复现本模块最重要的那个结论——
**只回传「模型不确定的」，会系统性地漏掉「模型自信地错了」的那一类。**

本 notebook 你会亲手实现：
1. 合成 TSR 检测流：**5 类样本**（已学会 / 低置信但对 / 低置信且错 / **高置信却错** / **完全漏检**）
2. 三种不确定性度量（**熵 / margin / least-confidence**）+ 它们在多类别下的差异
3. **置信度校准**（温度缩放 + ECE）——不确定性触发器的前提条件
4. **框级 → 图级聚合**（max / mean / top-k / count）与它引入的**场景偏差**
5. **多帧一致性触发**：利用「交通标志是静止刚体，类别必须恒定」这一物理性质
6. 多模型分歧（vote entropy）与规则触发（跟踪丢失 / 阈值震荡 / **与高精地图不符** / 接管急刹）
7. **触发器的 PR 分析**：触发率 vs 精确率 vs 召回率
8. **偏差审计**：分组召回率——证明不确定性触发对「高置信却错」的召回 ≈ 0
9. **带宽预算下的贪心分配**（submodular 覆盖）+ 强制随机基线配额

> 心智模型：**触发器是一个二分类器，必须按二分类器来评估。
> 它有 PR 曲线、有工作点，也有系统性偏差——而这个偏差不会体现在任何模型指标上。**"""),

    md("""## 1 · 合成一条带 ground truth 的 TSR 检测流

真实系统里我们不知道哪一帧是 badcase（那正是要找的东西）。
所以这里造一条**已知真值**的流，才能把触发器当成分类器来评估。

五类 track（一个 track = 一个标志由远及近的一次接近过程，8 帧）：

| 组 | 置信度 | 是否正确 | 谁能抓到 |
|---|---|---|---|
| `easy` | 高 | ✅（偶发闪烁） | 不需要抓 |
| `unc_correct` | 低 | ✅ | 不确定性触发（**误报**） |
| `unc_wrong` | 低 | ❌ | 不确定性触发 ✅ |
| **`conf_wrong`** | **高** | **❌（远处认错，近处改口）** | **一致性 / 地图，不确定性抓不到** |
| **`silent_miss`** | — | **完全漏检（没有框）** | **只有地图 / 随机基线** |"""),
    code("""import numpy as np

rng = np.random.default_rng(0)
C, T, N_FRAMES = 12, 8, 9000                 # 12 个类别 / 每个 track 8 帧 / 9000 帧
GROUP_N = {'easy': 1500, 'unc_correct': 120, 'unc_wrong': 60,
           'conf_wrong': 55, 'silent_miss': 35}
DET_P   = {'easy': 0.995, 'unc_correct': 0.90, 'unc_wrong': 0.90,
           'conf_wrong': 0.93, 'silent_miss': 0.0}

def one_prob(pred, runner, p1, p2):
    \"\"\"构造一条类别概率：pred 拿 p1，次高类 runner 拿 p2，剩下的均分。\"\"\"
    v = np.full(C, max(1.0 - p1 - p2, 1e-6) / (C - 2))
    v[pred] = p1; v[runner] = p2
    return v / v.sum()

obs = {k: [] for k in ['track', 't', 'frame', 'group', 'true', 'pred', 'det', 'p1']}
PROBS, TRACK_META = [], []
tid = 0
for g, n in GROUP_N.items():
    for _ in range(n):
        true_c = int(rng.integers(0, C))
        conf_c = int((true_c + rng.integers(1, C)) % C)     # 易混淆类（限速 60 vs 80）
        start = int(rng.integers(0, N_FRAMES - T))
        switch = int(rng.integers(3, 6))                    # conf_wrong 第几帧才改口
        map_has = bool(rng.random() < 0.60)                 # 高精地图只覆盖 60% 的标志
        TRACK_META.append(dict(tid=tid, group=g, true=true_c, map_has=map_has))
        for t in range(T):
            det = bool(rng.random() < DET_P[g])
            if g == 'easy':
                pred = true_c if rng.random() > 0.008 else conf_c   # 0.8% 偶发闪烁
                p1 = min(0.97, 0.72 + 0.03 * t + rng.uniform(0, 0.04))
                p2 = (1 - p1) * rng.uniform(0.3, 0.6)
            elif g == 'unc_correct':
                pred = true_c
                p1 = rng.uniform(0.34, 0.52); p2 = p1 * rng.uniform(0.78, 0.98)
            elif g == 'unc_wrong':
                pred = conf_c if rng.random() > 0.15 else true_c    # 低置信 -> 会闪回
                p1 = rng.uniform(0.34, 0.52); p2 = p1 * rng.uniform(0.78, 0.98)
            elif g == 'conf_wrong':
                pred = conf_c if t < switch else true_c             # **远处自信地错**
                p1 = 0.86 + rng.uniform(0, 0.10); p2 = (1 - p1) * rng.uniform(0.3, 0.6)
            else:                                                   # silent_miss
                pred, p1, p2 = true_c, 0.50, 0.20                   # 占位；det 恒为 False
            runner = conf_c if pred != conf_c else true_c
            PROBS.append(one_prob(pred, runner, p1, p2))
            obs['track'].append(tid); obs['t'].append(t); obs['frame'].append(start + t)
            obs['group'].append(g);   obs['true'].append(true_c); obs['pred'].append(pred)
            obs['det'].append(det);   obs['p1'].append(p1)
        tid += 1

O = {k: np.asarray(v) for k, v in obs.items()}
PROBS = np.asarray(PROBS)
O['bad'] = (~O['det']) | (O['det'] & (O['pred'] != O['true']))     # 漏检 或 认错
N_OBS = len(PROBS)

frame_bad = np.zeros(N_FRAMES, dtype=bool)
np.logical_or.at(frame_bad, O['frame'], O['bad'])
n_box = np.bincount(O['frame'][O['det']], minlength=N_FRAMES)      # 每帧的**已检出**框数

print(f'track {tid} 个 / 观测 {N_OBS} 条 / 帧 {N_FRAMES} 帧，平均每帧 {n_box.mean():.2f} 个框')
print(f'{"组":<14s}{"track 数":>9s}{"观测数":>8s}{"其中是 badcase":>15s}')
for g in GROUP_N:
    m = O['group'] == g
    print(f'{g:<14s}{GROUP_N[g]:>9d}{m.sum():>8d}{O["bad"][m].mean():>14.0%}')
print(f'\\n**帧级 badcase 率 = {frame_bad.mean():.1%}**（真实车队里要低两三个数量级，'
      f'这里放大是为了统计稳定）')
assert 0.05 < frame_bad.mean() < 0.35
assert O['bad'][O['group'] == 'silent_miss'].all(), '漏检组每一条观测都是 badcase'
assert O['bad'][O['group'] == 'unc_correct'].mean() < 0.15, '低置信但正确的组基本不是 badcase'
print('✅ 数据就位：**有真值**，所以可以把触发器当二分类器来评估')"""),

    md("""## 2 · 三种不确定性度量：熵 / margin / least-confidence

$H(p)=-\\sum_c p_c\\log p_c$，  $M(p)=p_{(1)}-p_{(2)}$，  $LC(p)=1-p_{(1)}$

在**类别多**的任务（TSR 有上百个细分类）上三者差别很大：
熵会被长尾小概率拉高，而 margin 只看前两名——正对应 TSR「限速 60 vs 80」这种成对混淆结构。"""),
    code("""def entropy(P):     return -(P * np.log(P + 1e-12)).sum(-1)
def margin(P):
    s = np.sort(P, axis=-1); return s[..., -1] - s[..., -2]
def least_conf(P):  return 1.0 - P.max(-1)

# 三个「不确定性分数」（越大越可疑）
U = {'entropy': entropy(PROBS), 'one_minus_margin': 1.0 - margin(PROBS),
     'least_conf': least_conf(PROBS)}

print(f'{"组":<14s}' + ''.join(f'{k:>20s}' for k in U))
for g in GROUP_N:
    m = (O['group'] == g) & O['det']
    if m.sum() == 0:
        continue
    print(f'{g:<14s}' + ''.join(f'{U[k][m].mean():>20.3f}' for k in U))

det = O['det']
u_unc  = U['one_minus_margin'][(O['group'] == 'unc_wrong') & det].mean()
u_conf = U['one_minus_margin'][(O['group'] == 'conf_wrong') & det].mean()
u_easy = U['one_minus_margin'][(O['group'] == 'easy') & det].mean()
print(f'\\n⚠️  **conf_wrong 的不确定性（{u_conf:.3f}）比 easy（{u_easy:.3f}）还低** —— ')
print(f'    它们「自信地错了」，而不确定性触发器看到的分数和「已经学会」的样本没有区别。')
print(f'    unc_wrong 的不确定性是 {u_unc:.3f}，高出一个量级。')
assert u_unc > 5 * u_conf, '低置信错例的不确定性应远高于高置信错例'
assert u_conf < u_easy * 1.2, 'conf_wrong 的不确定性与 easy 处于同一水平 —— 这就是盲区'

# 熵 vs margin：类别数多时，熵会被「长尾小概率」污染
tight = one_prob(0, 1, 0.45, 0.43)                  # 真正的二选一混淆
diffuse = np.full(C, 1 / C); diffuse[0] = 0.45
diffuse[1:] = (1 - 0.45) / (C - 1)                  # top-1 同样是 0.45，但剩余均匀弥散
print(f'\\n{"分布":<26s}{"top1":>7s}{"熵":>9s}{"1-margin":>11s}')
for nm, v in [('二选一混淆 (0.45/0.43)', tight), ('弥散 (0.45 + 均匀残余)', diffuse)]:
    print(f'{nm:<24s}{v.max():>7.2f}{entropy(v[None])[0]:>9.3f}{1 - margin(v[None])[0]:>11.3f}')
assert entropy(diffuse[None])[0] > entropy(tight[None])[0], '弥散分布的熵更高'
assert margin(tight[None])[0] < margin(diffuse[None])[0], '但真正混淆的是「二选一」那个'
print('\\n⚠️  两个分布的 top-1 都是 0.45，但**熵把弥散那个排得更靠前**，')
print('    而 TSR 真正要抓的是「二选一混淆」。**类别数越多，熵越不可靠。**')
print('✅ TSR 场景下 margin 通常优于熵；least-confidence 最便宜，适合车端第一层粗筛。')"""),

    code("""# ── 校准：不确定性触发器的前提条件 ──
# 现代网络的 softmax 是**系统性过自信**的：0.9 的置信度对应的真实正确率往往低得多
def ece(conf, correct, n_bins=10):
    \"\"\"Expected Calibration Error：分箱后 |平均置信度 - 平均正确率| 的加权和。\"\"\"
    edges = np.linspace(0, 1, n_bins + 1)
    e, n = 0.0, len(conf)
    for i in range(n_bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1])
        if m.sum() == 0:
            continue
        e += m.sum() / n * abs(conf[m].mean() - correct[m].mean())
    return float(e)

def temp_scale(P, temp):
    z = np.log(P + 1e-12) / temp
    z -= z.max(-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)

# 造一个**典型的过自信模型**：真实正确概率 a，但网络报告 conf = a^0.45 > a
r7 = np.random.default_rng(33)
a_true = r7.beta(5.0, 1.5, 6000)                        # 每个样本的真实正确概率
corr = (r7.random(6000) < a_true).astype(float)         # 实际对错
conf_rep = a_true ** 0.45                               # **过自信**：把概率往 1 推
Pd = np.stack([conf_rep, 1.0 - conf_rep], axis=1)       # 化成二类分布便于温度缩放
conf0 = Pd.max(-1)

print(f'{"置信度区间":<14s}{"样本数":>8s}{"平均置信度":>12s}{"真实正确率":>12s}{"差距":>9s}')
for lo, hi in [(0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0)]:
    m = (conf0 > lo) & (conf0 <= hi)
    if m.sum() == 0:
        continue
    print(f'{f"({lo:.2f},{hi:.2f}]":<14s}{m.sum():>8d}{conf0[m].mean():>12.3f}'
          f'{corr[m].mean():>12.3f}{conf0[m].mean()-corr[m].mean():>9.3f}')

grid = np.linspace(0.5, 4.0, 36)
eces = [ece(temp_scale(Pd, t).max(-1), corr) for t in grid]
t_best = float(grid[int(np.argmin(eces))])
print(f'\\nECE(T=1.0) = {ece(conf0, corr):.4f}   ->   ECE(T={t_best:.2f}) = {min(eces):.4f}')
assert (conf0 - corr).mean() > 0.05, '构造出来的就是一个过自信模型'
assert min(eces) < 0.5 * ece(conf0, corr), '温度缩放应大幅降低 ECE'
assert t_best > 1.0, '过自信的模型需要 T>1 把分布软化'
print('✅ 温度缩放（一个标量参数，在验证集上拟合）几乎零成本地修正了过自信。')
print('⚠️  未校准的模型上，「熵 > 1.7」这类绝对阈值是**没有意义**的，')
print('    而且校准误差在不同尺寸/光照桶上还不一样（小目标通常更过自信）')
print('    -> **触发器阈值必须分桶设定，或者干脆按分位数设阈**。')"""),

    md("""## 3 · 框级 → 图级聚合：一个隐藏的场景偏差源

回传决策是**整帧**的，但不确定性定义在**框**上。
这一步聚合看似是细节，实际决定了触发器会系统性偏向什么样的场景。"""),
    code("""def aggregate(frame_of, score, n_frames, how='max', k=3, thr=0.5):
    \"\"\"把框级分数聚合到帧级。frame_of: 每个框所属帧；未检出的框不参与。\"\"\"
    out = np.zeros(n_frames)
    order = np.argsort(frame_of, kind='mergesort')
    f_sorted, s_sorted = frame_of[order], score[order]
    bounds = np.searchsorted(f_sorted, np.arange(n_frames + 1))
    for f in range(n_frames):
        s = s_sorted[bounds[f]:bounds[f + 1]]
        if s.size == 0:
            continue
        if how == 'max':     out[f] = s.max()
        elif how == 'mean':  out[f] = s.mean()
        elif how == 'topk':  out[f] = np.sort(s)[-min(k, s.size):].mean()
        elif how == 'count': out[f] = (s > thr).sum()
        elif how == 'count_norm': out[f] = (s > thr).sum() / s.size
    return out

fo, sc = O['frame'][det], U['one_minus_margin'][det]
AGG = {h: aggregate(fo, sc, N_FRAMES, how=h) for h in
       ['max', 'mean', 'topk', 'count', 'count_norm']}

BUDGET = 0.05                                     # 假设只能回传 5% 的帧
print(f'{"聚合算子":<14s}{"触发帧平均框数":>16s}{"全体平均框数":>14s}{"badcase 精确率":>16s}')
has_box = n_box > 0
for h, v in AGG.items():
    kf = int(BUDGET * N_FRAMES)
    sel = np.argsort(-v, kind='mergesort')[:kf]
    print(f'{h:<14s}{n_box[sel].mean():>16.2f}{n_box[has_box].mean():>14.2f}'
          f'{frame_bad[sel].mean():>16.1%}')

kf = int(BUDGET * N_FRAMES)
nb = {h: n_box[np.argsort(-v, kind='mergesort')[:kf]].mean() for h, v in AGG.items()}
assert nb['mean'] < nb['max'], 'mean 聚合偏向框少的帧'
assert nb['count'] > nb['max'], 'count 聚合偏向框多的帧（拥挤路口）'
print(f'\\n⚠️  **mean 偏向框少的简单帧**（{nb["mean"]:.2f} 个框 vs 全体 {n_box[has_box].mean():.2f}），')
print(f'    **count 偏向框多的拥挤路口**（{nb["count"]:.2f} 个框）。')
print('    两者都是**由聚合算子引入、与模型无关的采样偏差** —— ')
print('    它不体现在任何模型指标上，却会让某类场景的问题永远发现不了。')
print('✅ 默认用 **max**（TSR 关心「有没有一个标志被认错」，不关心平均质量）；')
print('   要抗单帧噪声就用 top-k mean；count 必须归一化才能用。')"""),

    md("""## 4 · 多帧一致性：TSR 的杀手锏

交通标志是**静止刚体，类别在时间上恒定**。
所以同一个 track 上出现类别跳变 = **一个无需标注即可确认的错误**（至少有一帧一定是错的）。

这是 TSR 独有的红利：行人/车辆的属性会真的变化，没有这个性质。"""),
    code("""# 组织成 track -> 帧序列
tr_pred = {}; tr_frames = {}; tr_det = {}
for i in range(N_OBS):
    tr_pred.setdefault(O['track'][i], []).append(O['pred'][i])
    tr_frames.setdefault(O['track'][i], []).append(O['frame'][i])
    tr_det.setdefault(O['track'][i], []).append(O['det'][i])

def temporal_stats(preds, dets):
    \"\"\"只看**已检出**帧上的类别序列。\"\"\"
    seq = [p for p, d in zip(preds, dets) if d]
    if len(seq) < 2:
        return dict(flip=0, mode_frac=1.0, n=len(seq))
    flip = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    vals, cnt = np.unique(seq, return_counts=True)
    return dict(flip=int(flip), mode_frac=float(cnt.max() / len(seq)), n=len(seq))

TSTAT = {t: temporal_stats(tr_pred[t], tr_det[t]) for t in tr_pred}
g_of = {m['tid']: m['group'] for m in TRACK_META}

print(f'{"组":<14s}{"平均跳变次数":>14s}{"众数占比":>11s}{"至少跳变一次的 track":>22s}')
for g in GROUP_N:
    ts = [TSTAT[t] for t in TSTAT if g_of[t] == g]
    if not ts:
        continue
    print(f'{g:<14s}{np.mean([x["flip"] for x in ts]):>14.2f}'
          f'{np.mean([x["mode_frac"] for x in ts]):>11.2f}'
          f'{np.mean([x["flip"] > 0 for x in ts]):>21.0%}')

rec_conf = np.mean([TSTAT[t]['flip'] > 0 for t in TSTAT if g_of[t] == 'conf_wrong'])
rec_easy = np.mean([TSTAT[t]['flip'] > 0 for t in TSTAT if g_of[t] == 'easy'])
assert rec_conf > 0.90, '多帧一致性应几乎抓住全部「高置信却错」的 track'
assert rec_easy < 0.15, '正常 track 不应频繁误触发'
print(f'\\n✅ **多帧类别跳变对 conf_wrong 的召回 = {rec_conf:.0%}** —— ')
print(f'   而这一组的单帧不确定性和 easy 完全无法区分（上一节已验证）。')
print(f'   误报率（easy 组）只有 {rec_easy:.0%}，且成本几乎为零（跟踪本来就要跑）。')

# 帧级一致性分数：该帧所属 track 的「不一致程度」
temporal_score = np.zeros(N_FRAMES)
for t, st in TSTAT.items():
    s = 1.0 - st['mode_frac']
    for f, d in zip(tr_frames[t], tr_det[t]):
        if d:
            temporal_score[f] = max(temporal_score[f], s)

# ── 时序反标：用近处高置信结果反标远处困难帧（免费的困难样本）──
gain = 0
for t, st in TSTAT.items():
    seq = [(p, d) for p, d in zip(tr_pred[t], tr_det[t])]
    if st['flip'] > 0 and st['n'] >= 4:
        gain += sum(1 for k, (p, d) in enumerate(seq) if d and k < 4)   # 远处的困难帧
print(f'\\n✅ 附带红利：跳变 track 里可用「近处结果」反标出 {gain} 帧远距离小目标样本，')
print('   **零标注成本**，而这正是 TSR 最缺的数据类型（track-level label propagation）。')
print('⚠️  两个失效条件：① 跟踪 ID switch（两个相邻标志被跟成一个）→ 要先验证 track 纯度；')
print('    ② **可变电子牌的类别是真的会变的** → 必须从「类别恒定」假设里排除。')"""),

    md("""## 5 · 多模型分歧与规则触发

一致性触发的另一条路：K 个独立模型投票。
规则触发则完全不看模型的概率，只看**系统级矛盾**——最便宜、最可解释，也最容易被低估。"""),
    code("""# ── 多模型分歧（query-by-committee）──
K_MODEL = 5
r5 = np.random.default_rng(21)
AGREE = {'easy': 0.97, 'unc_correct': 0.55, 'unc_wrong': 0.55,
         'conf_wrong': 0.58, 'silent_miss': 0.5}
votes = np.zeros((N_OBS, K_MODEL), dtype=int)
for i in range(N_OBS):
    pa = AGREE[O['group'][i]]
    if O['group'][i] == 'conf_wrong' and O['pred'][i] == O['true'][i]:
        pa = 0.95                                   # 近处已改口 -> 模型也都同意了
    for m in range(K_MODEL):
        votes[i, m] = O['pred'][i] if r5.random() < pa else int(O['true'][i])

def vote_entropy(v, n_cls=C):
    cnt = np.bincount(v, minlength=n_cls) / len(v)
    return float(-(cnt[cnt > 0] * np.log(cnt[cnt > 0])).sum())

VE = np.array([vote_entropy(votes[i]) for i in range(N_OBS)])
print(f'{"组":<14s}{"平均 vote entropy":>20s}')
for g in GROUP_N:
    m = (O['group'] == g) & det
    if m.sum():
        print(f'{g:<14s}{VE[m].mean():>20.3f}')
assert VE[(O['group'] == 'conf_wrong') & det].mean() > 2.5 * VE[(O['group'] == 'easy') & det].mean()
print('✅ **多模型分歧能看见「自信地错」**：单模型很确定，但模型之间对不上。')
print('⚠️  代价：车端跑不动 K 个模型 —— 通常只在云端影子复检时用。')

# ── 规则触发（几乎零算力）──
rule = {k: np.zeros(N_FRAMES, dtype=bool) for k in
        ['track_lost', 'osc', 'map_mismatch', 'event']}

# ① 跟踪丢失：检出后中断
for t in tr_pred:
    d = tr_det[t]; fs = tr_frames[t]
    for k in range(1, len(d)):
        if d[k - 1] and not d[k]:
            rule['track_lost'][fs[k]] = True

# ② 阈值附近震荡：track 的 top-1 分数反复穿越工作点 0.5
TAU = 0.50
tr_idx = {}                                       # track -> 按时间排好序的观测下标
for i in np.argsort(O['track'] * (T + 1) + O['t'], kind='mergesort'):
    tr_idx.setdefault(int(O['track'][i]), []).append(int(i))
for t, sel in tr_idx.items():
    sel = np.asarray(sel)
    s = O['p1'][sel][O['det'][sel]]
    if s.size >= 2 and int(((s[:-1] - TAU) * (s[1:] - TAU) < 0).sum()) >= 2:
        for i in sel:                             # 只标记真正贴着工作点的那几帧
            if O['det'][i] and abs(O['p1'][i] - TAU) < 0.05:
                rule['osc'][O['frame'][i]] = True

# ③ 与高精地图不符（地图只覆盖 60% 的标志）
map_has = {m['tid']: m['map_has'] for m in TRACK_META}
for i in range(N_OBS):
    if map_has[O['track'][i]] and O['bad'][i]:
        rule['map_mismatch'][O['frame'][i]] = True

# ④ 接管 / 急刹：随机事件，但在 badcase 帧附近概率高 4 倍
r6 = np.random.default_rng(5)
base = np.where(frame_bad, 0.016, 0.004)
rule['event'] = r6.random(N_FRAMES) < base

print(f'\\n{"规则触发器":<16s}{"触发率":>10s}{"精确率":>10s}{"召回率":>10s}')
for k, v in rule.items():
    prec = frame_bad[v].mean() if v.sum() else 0.0
    rec = (v & frame_bad).sum() / frame_bad.sum()
    print(f'{k:<16s}{v.mean():>10.2%}{prec:>10.1%}{rec:>10.1%}')
assert frame_bad[rule['map_mismatch']].mean() > 0.95, '地图不符用的是**模型之外的外部真值**，精确率应极高'
assert frame_bad[rule['event']].mean() > frame_bad.mean(), '事件触发的精确率应高于基线'
print('\\n✅ **「与高精地图不符」精确率最高**，因为它用的是模型之外的外部真值 ——')
print('   它同时覆盖「自信地错」与「完全漏检」两个不确定性触发器的结构性盲区。')
print('⚠️  但地图只覆盖 60% 的标志，且**地图本身会过期**（施工/限速调整）——')
print('    触发的可能是「地图该更新了」，这同样有价值但要分开处理。')"""),

    md("""## 6 · 把触发器当分类器来评：PR 分析

三个量：**触发率**（成本）、**精确率**（回传的里面有多少值得标）、
**召回率**（真 badcase 抓到了多少）。
注意召回率的分母必须来自**无偏的随机基线采样**，否则根本算不出来。"""),
    code("""SCORES = {
    'unc_margin':  AGG['max'],
    'unc_entropy': aggregate(fo, entropy(PROBS)[det], N_FRAMES, how='max'),
    'disagree':    aggregate(fo, VE[det], N_FRAMES, how='max'),
    'temporal':    temporal_score,
    'map_mismatch': rule['map_mismatch'].astype(float),
    'track_lost':  rule['track_lost'].astype(float),
    'osc':         rule['osc'].astype(float),
    'event':       rule['event'].astype(float),
    'random':      np.random.default_rng(99).random(N_FRAMES),
}

def trigger_at_rate(score, is_bad, rate):
    \"\"\"取分数最高的 rate 比例的帧（分数为 0 的不算触发），返回工作点指标。\"\"\"
    kf = int(round(rate * len(score)))
    order = np.argsort(-score, kind='mergesort')
    sel = order[:kf]
    sel = sel[score[sel] > 0]
    fired = np.zeros(len(score), dtype=bool); fired[sel] = True
    prec = is_bad[fired].mean() if fired.sum() else 0.0
    return dict(rate=fired.mean(), precision=float(prec),
                recall=float((fired & is_bad).sum() / is_bad.sum()), mask=fired)

RATES = [0.02, 0.05, 0.10]
print(f'{"触发器":<15s}' + ''.join(f'{"rate=%.0f%%" % (100*r):>22s}' for r in RATES))
print(f'{"":<15s}' + ''.join(f'{"精确率 / 召回率":>22s}' for _ in RATES))
for k, s in SCORES.items():
    line = f'{k:<15s}'
    for r in RATES:
        mm = trigger_at_rate(s, frame_bad, r)
        cell = '%.0f%% / %.0f%%' % (100 * mm['precision'], 100 * mm['recall'])
        line += f'{cell:>22s}'
    print(line)

base_rate = frame_bad.mean()
m_rand = trigger_at_rate(SCORES['random'], frame_bad, 0.05)
m_temp = trigger_at_rate(SCORES['temporal'], frame_bad, 0.05)
assert abs(m_rand['precision'] - base_rate) < 0.04, '随机基线的精确率 ≈ 基线 badcase 率'
assert m_temp['precision'] > 3 * base_rate, '一致性触发的精确率应远高于随机'
print(f'\\n基线 badcase 率 = {base_rate:.1%}（= 随机采样的精确率 {m_rand["precision"]:.1%}）')
print('✅ 精确率必须与**基线 badcase 率**比，而不是看绝对值。')
print('⚠️  召回率的分母是「所有真 badcase」—— 只有靠随机基线全标才能得到。')
print('    只在「被触发的样本」里算召回，得到的永远是 100%，毫无意义。')"""),

    md("""## 7 · 偏差审计：不确定性触发器的系统性盲区

上面看到的都是**总体**指标。现在按组拆开看——
这一步会暴露一个总体指标完全掩盖的事实。"""),
    code("""# 每一帧属于哪些组（一帧可能有多个 track）
GROUPS = list(GROUP_N)
frame_group = {g: np.zeros(N_FRAMES, dtype=bool) for g in GROUPS}
for i in range(N_OBS):
    if O['bad'][i]:
        frame_group[O['group'][i]][O['frame'][i]] = True

def bias_audit(fired, tag=''):
    row = {}
    for g in GROUPS:
        m = frame_group[g]
        row[g] = float((fired & m).sum() / m.sum()) if m.sum() else float('nan')
    row['ALL'] = float((fired & frame_bad).sum() / frame_bad.sum())
    return row

def fire_set(k, rate):
    \"\"\"连续分数 -> 取 top-rate；二值规则 -> 用它的**自然触发集合**（不人为截断）。\"\"\"
    s = SCORES[k]
    if set(np.unique(s).tolist()) <= {0.0, 1.0}:
        return s > 0
    return trigger_at_rate(s, frame_bad, rate)['mask']

RATE = 0.10
print(f'连续分数统一取 top-{RATE:.0%}，二值规则用自然触发率，看**各组 badcase 的召回率**：\\n')
print(f'{"触发器":<15s}{"触发率":>8s}' + ''.join(f'{g:>13s}' for g in GROUPS) + f'{"总体":>8s}')
audits = {}
for k in ['unc_margin', 'unc_entropy', 'temporal', 'disagree', 'map_mismatch',
          'track_lost', 'random']:
    fired = fire_set(k, RATE)
    a = bias_audit(fired); audits[k] = a
    print(f'{k:<15s}{fired.mean():>8.1%}' + ''.join(f'{a[g]:>13.0%}' for g in GROUPS)
          + f'{a["ALL"]:>8.0%}')

# 判据要与**随机基线**比：lift = 该组召回 / 随机基线在该组的召回
# lift ≈ 1 意味着「这个触发器在该组上没有提供任何信息」
R0 = audits['random']
lift = {k: {g: audits[k][g] / R0[g] for g in list(GROUPS) + ['ALL']} for k in audits}
print(f'\\n相对随机基线的 **lift**（≈1 = 毫无信息）：\\n')
print(f'{"触发器":<15s}' + ''.join(f'{g:>13s}' for g in GROUPS) + f'{"总体":>8s}')
for k in ['unc_margin', 'temporal', 'disagree', 'map_mismatch']:
    print(f'{k:<15s}' + ''.join(f'{lift[k][g]:>12.1f}×' for g in GROUPS)
          + f'{lift[k]["ALL"]:>7.1f}×')

assert lift['unc_margin']['ALL'] > 1.8,          '不确定性触发在**总体**上确实有效'
assert lift['unc_margin']['unc_wrong'] > 4.0,    '它在低置信错例上很强'
assert lift['unc_margin']['conf_wrong'] < 1.2,   '但对「高置信却错」不比随机采样更好 —— 盲区①'
assert lift['unc_margin']['silent_miss'] < 2.2,  '对「完全漏检」同样近乎无信息 —— 盲区②'
assert lift['temporal']['conf_wrong'] > 5.0,     '一致性触发覆盖盲区①'
assert lift['map_mismatch']['silent_miss'] > 5.0, '地图先验覆盖盲区②'
assert audits['temporal']['conf_wrong'] > 0.60 and audits['map_mismatch']['silent_miss'] > 0.30
print(f'\\n⚠️  不确定性触发的**总体** lift = {lift["unc_margin"]["ALL"]:.1f}×（看起来很不错），')
print(f'    在 unc_wrong 上高达 {lift["unc_margin"]["unc_wrong"]:.1f}×；')
print(f'    但在 conf_wrong 上只有 {lift["unc_margin"]["conf_wrong"]:.1f}×、'
      f'silent_miss 上 {lift["unc_margin"]["silent_miss"]:.1f}× —— **与随机采样同一量级**。')
print('    （silent_miss 上那点残余 lift 只是「同一帧里还有别的 track」的巧合共现，')
print('     不是触发器真的看见了漏检。）')
print('    **总体指标完全掩盖了这两个结构性盲区。**')
print('\\n两个盲区的成因不同：')
print('  ① **自信地错**：模型自报的不确定性低 -> 按行切（低置信）永远切不到它（它在高置信行）')
print('  ② **完全漏检**：没有检出就没有框，也就没有任何分数可打')
print('\\n✅ 对策：一致性触发（多帧/多模型）覆盖 ①，规则触发（地图/跟踪丢失）覆盖 ②，')
print('   **随机基线覆盖「未知的未知」**——它是唯一不经过模型判断的数据通路。')
print(f'   随机基线在每一组上的召回都恰好 ≈ 触发率 {RATE:.0%}，**无偏但低效** —— ')
print('   它的价值不在效率，而在于它是唯一能算出「真实召回率分母」的东西。')"""),

    md("""## 8 · 带宽预算下的贪心分配

$\\max_{\\tau}\\;\\big|\\bigcup_t S_t(\\tau_t)\\cap\\mathcal{B}\\big|$  s.t.  $\\big|\\bigcup_t S_t(\\tau_t)\\big|\\le B\\cdot N$

这是一个**集合覆盖（submodular）最大化**问题，贪心有 $1-1/e\\approx63\\%$ 的近似保证。"""),
    code("""def greedy_allocate(scores, is_bad, budget_frames, step=30, exclude=()):
    \"\"\"贪心：每轮挑「每花一帧预算能新抓到最多 badcase」的那个触发器，取它接下来的 step 帧。\"\"\"
    names = [k for k in scores if k not in exclude]
    order = {k: np.argsort(-scores[k], kind='mergesort') for k in names}
    ptr = {k: 0 for k in names}
    chosen = np.zeros(len(is_bad), dtype=bool)
    alloc = {k: 0 for k in names}
    while chosen.sum() < budget_frames:
        best = None
        for k in names:
            take, i, o = [], ptr[k], order[k]
            while i < len(o) and len(take) < step:
                if not chosen[o[i]] and scores[k][o[i]] > 0:
                    take.append(o[i])
                i += 1
            if not take:
                continue
            gain = is_bad[take].sum() / len(take)
            if best is None or gain > best[1]:
                best = (k, gain, take, i)
        if best is None:
            break
        k, _, take, newptr = best
        room = int(budget_frames - chosen.sum())
        take = take[:room]
        chosen[take] = True; ptr[k] = newptr; alloc[k] += len(take)
    return chosen, alloc

B = 0.15                                     # 预算要设在「单一触发器已经不够用」的区间才有意义
budget = int(B * N_FRAMES)
RESULTS = {}

# 策略 A：全部预算给单一最好的触发器
best_single, best_rec = None, -1
for k in ['unc_margin', 'temporal', 'disagree', 'map_mismatch']:
    m = trigger_at_rate(SCORES[k], frame_bad, B)
    if m['recall'] > best_rec:
        best_single, best_rec, RESULTS['A 单一最优触发器'] = k, m['recall'], m['mask']

# 策略 B：贪心多触发器组合（不含随机）
mask_B, alloc_B = greedy_allocate(SCORES, frame_bad, budget, exclude=('random',))
RESULTS['B 贪心组合'] = mask_B

# 策略 C：组合 + 强制 15% 随机基线配额（对抗触发器偏差）
rand_share = 0.15
n_rand = int(rand_share * budget)
rand_sel = np.random.default_rng(7).permutation(N_FRAMES)[:n_rand]
mask_C = np.zeros(N_FRAMES, dtype=bool); mask_C[rand_sel] = True
extra, alloc_C = greedy_allocate(SCORES, frame_bad, budget - n_rand, exclude=('random',))
mask_C |= extra
RESULTS['C 组合 + 15% 随机基线'] = mask_C

print(f'预算 = {B:.0%} 的帧（{budget} 帧），最优单一触发器 = {best_single}\\n')
print(f'{"策略":<26s}{"实际触发率":>12s}{"精确率":>9s}{"总体召回":>10s}'
      + ''.join(f'{g:>13s}' for g in ['conf_wrong', 'silent_miss']))
for nm, msk in RESULTS.items():
    a = bias_audit(msk)
    print(f'{nm:<24s}{msk.mean():>12.2%}{frame_bad[msk].mean():>9.1%}{a["ALL"]:>10.1%}'
          + ''.join(f'{a[g]:>13.0%}' for g in ['conf_wrong', 'silent_miss']))

rec_A = bias_audit(RESULTS['A 单一最优触发器'])['ALL']
rec_B = bias_audit(RESULTS['B 贪心组合'])['ALL']
rec_C = bias_audit(RESULTS['C 组合 + 15% 随机基线'])
assert rec_B > rec_A + 0.05, '多触发器组合应显著优于单一触发器（它们覆盖不同盲区）'
assert rec_C['ALL'] <= rec_B + 1e-9, '留 15% 给随机基线，总召回不会更高 —— 这是刻意付出的代价'
assert rec_C['ALL'] > 0.85 * rec_B, '但这个代价应该很小'
print(f'\\n预算分配（策略 B）: ' + ', '.join(f'{k}={v}' for k, v in alloc_B.items() if v))
print(f'\\n✅ 贪心组合把总召回从 {rec_A:.1%} 提到 {rec_B:.1%} —— 因为不同触发器覆盖不同盲区，')
print('   而 submodular 覆盖的贪心解有 1-1/e ≈ 63% 的近似保证。')
print(f'✅ 策略 C 留出 15% 预算给随机基线，总召回只从 {rec_B:.1%} 降到 {rec_C["ALL"]:.1%}'
      f'（-{100*(rec_B-rec_C["ALL"]):.1f} pp）——')
print('   **一份极其便宜的保险**：换来一条不经过模型判断的数据通路，')
print('   它是唯一能发现「未知的未知」、也是唯一能算出真实召回率分母的东西。')
print('⚠️  注意精确率从 %.0f%% 降到 %.0f%% —— 随机基线本来就低效，'
      % (100 * frame_bad[mask_B].mean(), 100 * frame_bad[mask_C].mean()))
print('    它的价值不在效率，而在**无偏**。')
print('✅ 量产配置 = 车端便宜触发器粗筛 -> 云端大模型精筛 -> 按场景桶配额 -> 15% 随机基线。')"""),

    md("""## ✏️ 练习 1：图级聚合与工作点

实现 `image_uncertainty(box_scores, how, k=3, thr=0.5)`：输入**一帧内**所有框的分数
（可能为空数组），返回该帧的标量分数。支持 `'max' / 'mean' / 'topk' / 'count_norm'`。
空数组一律返回 `0.0`。`count_norm` = 超过 `thr` 的框数 / 总框数。"""),
    code("""def image_uncertainty(box_scores, how='max', k=3, thr=0.5):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s = np.array([0.1, 0.6, 0.9, 0.4])
assert abs(image_uncertainty(s, 'max') - 0.9) < 1e-12
assert abs(image_uncertainty(s, 'mean') - 0.5) < 1e-12
assert abs(image_uncertainty(s, 'topk', k=2) - 0.75) < 1e-12
assert abs(image_uncertainty(s, 'count_norm', thr=0.5) - 0.5) < 1e-12
assert image_uncertainty(np.array([]), 'max') == 0.0
assert image_uncertainty(np.array([]), 'mean') == 0.0
assert abs(image_uncertainty(s, 'topk', k=99) - s.mean()) < 1e-12, 'k 大于框数时退化为 mean'
# 在真实数据上与向量化实现对齐
fo_list = {}
for i in np.where(det)[0]:
    fo_list.setdefault(O['frame'][i], []).append(U['one_minus_margin'][i])
for f in list(fo_list)[:200]:
    assert abs(image_uncertainty(np.array(fo_list[f]), 'max') - AGG['max'][f]) < 1e-12
print('✅ 练习 1 通过：**默认用 max**；mean 偏向框少的帧，count 必须归一化')"""),

    md("""## ✏️ 练习 2：多帧一致性触发器

实现 `temporal_trigger(pred_seq, det_seq, min_obs=3)`，只统计**已检出**的帧，返回 dict：

- `'n'`：有效观测数
- `'flip'`：相邻类别变化次数
- `'mode_frac'`：众数类别占比
- `'fire'`：`n >= min_obs` **且** `flip >= 1` 时为 True（观测太少不下结论）"""),
    code("""def temporal_trigger(pred_seq, det_seq, min_obs=3):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r = temporal_trigger([3,3,3,3], [True]*4)
assert r['n'] == 4 and r['flip'] == 0 and abs(r['mode_frac'] - 1.0) < 1e-12 and not r['fire']
r = temporal_trigger([5,5,5,3,3], [True]*5)
assert r['flip'] == 1 and abs(r['mode_frac'] - 0.6) < 1e-12 and r['fire'], r
r = temporal_trigger([5,3,5,3], [True]*4)
assert r['flip'] == 3 and r['fire'], r
r = temporal_trigger([5,3], [True, True])              # 观测太少
assert not r['fire'], '观测数 < min_obs 时不下结论'
r = temporal_trigger([5,9,9,9], [True, False, False, False])
assert r['n'] == 1 and not r['fire'], '未检出的帧不参与'
# 真实数据上：对 conf_wrong 的召回应远高于 easy 的误报
fire = {t: temporal_trigger(tr_pred[t], tr_det[t])['fire'] for t in tr_pred}
rc = np.mean([fire[t] for t in fire if g_of[t] == 'conf_wrong'])
re_ = np.mean([fire[t] for t in fire if g_of[t] == 'easy'])
print(f'conf_wrong 召回 {rc:.0%} | easy 误报 {re_:.0%}')
assert rc > 0.85 and re_ < 0.15
print('✅ 练习 2 通过：**「标志是静止刚体，类别必须恒定」是一个免费的自动标签**')"""),

    md("""## ✏️ 练习 3：触发器的 PR 分析与偏差审计

实现 `evaluate_trigger(score, is_bad, group_masks, rate)`，返回 dict：

- `'rate'` / `'precision'` / `'recall'`（整体）
- `'by_group'`：`{组名: 该组 badcase 的召回率}`
- `'lift'`：`precision / is_bad.mean()`（相对随机基线的提升倍数）

选帧规则同正文：取分数最高的 `rate` 比例，且**分数必须 > 0**。"""),
    code("""def evaluate_trigger(score, is_bad, group_masks, rate):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
gm = {g: frame_group[g] for g in GROUPS}
e_rand = evaluate_trigger(SCORES['random'], frame_bad, gm, 0.05)
e_unc  = evaluate_trigger(SCORES['unc_margin'], frame_bad, gm, 0.05)
e_tmp  = evaluate_trigger(SCORES['temporal'], frame_bad, gm, 0.05)
assert abs(e_rand['lift'] - 1.0) < 0.35, '随机基线的 lift ≈ 1'
assert e_tmp['lift'] > 3.0, '一致性触发的 lift 应显著 > 1'
assert set(e_unc['by_group']) == set(GROUPS)
assert e_unc['by_group']['conf_wrong'] < 0.10, '**不确定性触发抓不到「自信地错」**'
assert e_tmp['by_group']['conf_wrong'] > 0.60, '一致性触发能抓到'
assert abs(e_rand['recall'] - 0.05) < 0.03, '随机基线的召回 ≈ 触发率'
print(f'{"触发器":<14s}{"lift":>7s}{"总召回":>9s}{"conf_wrong 召回":>17s}')
for nm, e in [('random', e_rand), ('unc_margin', e_unc), ('temporal', e_tmp)]:
    print(f'{nm:<14s}{e["lift"]:>7.1f}{e["recall"]:>9.0%}{e["by_group"]["conf_wrong"]:>17.0%}')
print('✅ 练习 3 通过：**总体召回会掩盖结构性盲区，必须分组审计**')"""),

    md("""## ✏️ 练习 4：带宽预算下的触发器组合

实现 `plan_triggers(scores, is_bad, budget_rate, random_share=0.15, step=30)`：

1. 先把 `budget_rate * N` 帧里的 `random_share` 比例**无条件**分给随机采样（种子固定为 7）
2. 剩余预算用 `greedy_allocate` 在其余触发器上贪心分配（排除 `'random'`）
3. 返回 `{'mask':…, 'alloc':…, 'recall':…, 'precision':…, 'random_frames':…}`"""),
    code("""def plan_triggers(scores, is_bad, budget_rate, random_share=0.15, step=30):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
p0 = plan_triggers(SCORES, frame_bad, 0.05, random_share=0.0)
p15 = plan_triggers(SCORES, frame_bad, 0.05, random_share=0.15)
assert p0['random_frames'] == 0 and p15['random_frames'] == int(0.15 * int(0.05 * N_FRAMES))
assert abs(p0['mask'].mean() - 0.05) < 0.005 and abs(p15['mask'].mean() - 0.05) < 0.006
assert p0['recall'] > p15['recall'], '留随机配额必然牺牲一点总召回'
assert p15['recall'] > 0.75 * p0['recall'], '但代价应可接受'
assert sum(p0['alloc'].values()) > 0 and 'random' not in p0['alloc']
print(f'{"配置":<22s}{"触发率":>9s}{"精确率":>9s}{"总召回":>9s}')
for nm, p in [('无随机基线', p0), ('15% 随机基线', p15)]:
    print(f'{nm:<20s}{p["mask"].mean():>9.2%}{p["precision"]:>9.1%}{p["recall"]:>9.1%}')
print('分配:', {k: v for k, v in p15['alloc'].items() if v})
print('✅ 练习 4 通过：**随机基线是刻意付出的代价** —— 它换来无偏审计与「未知的未知」')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def image_uncertainty(box_scores, how='max', k=3, thr=0.5):
    s = np.asarray(box_scores, dtype=float)
    if s.size == 0:
        return 0.0
    if how == 'max':
        return float(s.max())
    if how == 'mean':
        return float(s.mean())
    if how == 'topk':
        return float(np.sort(s)[-min(k, s.size):].mean())
    if how == 'count_norm':
        return float((s > thr).sum() / s.size)
    raise ValueError(how)"""),
    code("""# 练习 2 参考答案
def temporal_trigger(pred_seq, det_seq, min_obs=3):
    seq = [int(p) for p, d in zip(pred_seq, det_seq) if d]
    n = len(seq)
    if n == 0:
        return dict(n=0, flip=0, mode_frac=1.0, fire=False)
    flip = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    _, cnt = np.unique(seq, return_counts=True)
    mode_frac = float(cnt.max() / n)
    return dict(n=n, flip=int(flip), mode_frac=mode_frac,
                fire=bool(n >= min_obs and flip >= 1))"""),
    code("""# 练习 3 参考答案
def evaluate_trigger(score, is_bad, group_masks, rate):
    kf = int(round(rate * len(score)))
    order = np.argsort(-np.asarray(score), kind='mergesort')[:kf]
    order = order[np.asarray(score)[order] > 0]
    fired = np.zeros(len(score), dtype=bool); fired[order] = True
    base = is_bad.mean()
    prec = float(is_bad[fired].mean()) if fired.sum() else 0.0
    return dict(rate=float(fired.mean()), precision=prec,
                recall=float((fired & is_bad).sum() / is_bad.sum()),
                lift=prec / base if base > 0 else 0.0,
                by_group={g: (float((fired & m).sum() / m.sum()) if m.sum() else float('nan'))
                          for g, m in group_masks.items()},
                mask=fired)"""),
    code("""# 练习 4 参考答案
def plan_triggers(scores, is_bad, budget_rate, random_share=0.15, step=30):
    n = len(is_bad)
    budget = int(budget_rate * n)
    n_rand = int(random_share * budget)
    mask = np.zeros(n, dtype=bool)
    if n_rand:                                   # ① 无条件的随机基线配额
        mask[np.random.default_rng(7).permutation(n)[:n_rand]] = True
    extra, alloc = greedy_allocate(scores, is_bad, budget - n_rand,
                                   step=step, exclude=('random',))
    mask |= extra                                # ② 剩余预算贪心分配
    return dict(mask=mask, alloc=alloc, random_frames=n_rand,
                precision=float(is_bad[mask].mean()) if mask.sum() else 0.0,
                recall=float((mask & is_bad).sum() / is_bad.sum()))"""),

    md("""---
## 🧪 真实工程胶囊：车端触发器配置 + 每日看板 + 上线检查清单"""),
    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# 车端触发器 · 生产配置模板（可直接改成 yaml / protobuf）
# ══════════════════════════════════════════════════════════════════

# ── 总预算（一切设计的出发点）─────────────────────────────────────
#   10 万辆车 × 1 h/天 × 30 FPS = 1.08e10 帧/天
#   标注预算 5 万帧/天  ->  **允许触发率 ≈ 4.6e-6**
#   ⇒ 触发器 precision 从 5% 提到 20% = 标注效率翻两番
budget: {frames_per_day: 50000, bandwidth_gb_per_car_day: 0.2}

# ── ① 车端触发器（算力 < 1 ms/帧，所以只能用「本来就在跑」的信号）──
triggers:
  - name: temporal_class_flip        # **TSR 杀手锏**：静止刚体，类别必须恒定
    signal: track.pred_class_sequence
    fire_if: "flip_count >= 1 and n_obs >= 3"
    cost: ~0                          # 跟踪本来就要跑
    note: "跳变 = 无需标注即可确认的错误；还能用近处结果反标远处困难帧"
    exclude: ["variable_message_sign"]   # ⚠️ 电子可变牌的类别是**真的会变**的

  - name: track_lost
    fire_if: "detected_then_gap and not out_of_frame"

  - name: map_mismatch               # **精确率最高**：用了模型之外的外部真值
    fire_if: "hdmap.has_sign(loc) and (no_detection or pred_class != map_class)"
    note: "同时覆盖『自信地错』与『完全漏检』两个盲区；但地图会过期 -> 分开处理"

  - name: margin_low                 # margin 优于熵（类别多时熵被长尾污染）
    signal: "1 - (p1 - p2)"
    aggregate: max                    # **默认 max**；mean 偏向框少的帧，count 偏向拥挤路口
    fire_if: "score > quantile(0.999, sliding_window)"   # **按分位数设阈，不用绝对阈值**

  - name: takeover_or_hard_brake
    fire_if: "driver_takeover or a_long < -3.0"
    window: [-3s, +3s]

  - name: stratified_random          # ★★ **不能砍**
    share_of_budget: 0.15
    strata: [geo_region, time_of_day, weather]
    note: "唯一不经过模型判断的通路；也是唯一能算出真实召回率分母的东西"

# ── ② 全局控制 ───────────────────────────────────────────────────
dedup:
  onboard_time_window_s: 30           # 同一 track / 同一场景 N 秒内只触发一次
  cloud: perceptual_hash + embedding_cluster    # 云端内容去重（见模块 04）
quota_by_bucket:                      # **按桶配额**，消除地理/时段偏差
  {night: 0.25, rain: 0.15, urban: 0.30, highway: 0.30}
circuit_breaker:                      # **安全阀**：触发率异常时自动降级
  max_rate_multiplier: 3.0
  action: raise_threshold_then_alert
rollout: {canary_fleet_pct: 1, ramp: [1, 5, 25, 100]}   # 触发器也要灰度

# ── ③ 每日看板（触发率看板与模型指标看板同等重要）─────────────────
#   触发器 | 触发率 | 带宽占比 | 精确率* | 新场景占比 | 与其他触发器的重叠度
#   * 精确率分母 = 回传量，分子 = 复检确认确实是 badcase
#   必看三个趋势：① 触发率漂移（模型/跟踪/地图/环境变了）
#                ② 触发器之间的重叠度（重叠高 = 有冗余，可省预算）
#                ③ **从触发到修复上线的周期时间** <- 数据闭环真正的 KPI

# ── 上线前检查清单 ────────────────────────────────────────────────
#   [ ] 概率**校准**过了吗？（温度缩放 + 分桶 ECE）阈值是按分位数还是绝对值？
#   [ ] 图级聚合用的是 max 吗？（mean/count 会引入场景偏差）
#   [ ] 做了**时间窗去重**吗？（不去重，一段 10s 困难路段能吃掉整天预算）
#   [ ] 做了**分组偏差审计**吗？（conf_wrong / silent_miss 两组召回是多少？）
#   [ ] 留了**随机基线配额**吗？没有它就算不出真实召回率
#   [ ] 有**安全阀**吗？触发率暴涨时能自动降级吗？
#   [ ] 触发器配置能**远程灰度与回滚**吗？还是要等下次 OTA？
#   [ ] 脱敏（人脸/车牌）在回传前完成了吗？脱敏会不会破坏训练数据？
'''
print(RECIPE)
for key in ['temporal_class_flip', 'map_mismatch', 'stratified_random', 'circuit_breaker',
            'quota_by_bucket', 'onboard_time_window_s', 'variable_message_sign',
            'quantile(0.999', '周期时间']:
    assert key in RECIPE, key
print('✅ 配方覆盖：预算推导 / 三类触发器 / 去重 / 桶配额 / 安全阀 / 灰度 / 看板 / 检查清单')"""),

    md("""### 小结

- **问题变了**：模块 02 是「已标好的数据里该多看哪些」，这里是「**无限的流式数据里该回传什么**」。
  10 万辆车 × 1h/天 × 30FPS ≈ 1e10 帧/天，标注预算 5 万帧/天 → **触发率必须压到 1e-6 量级**。
  在这个量级下，触发器 precision 从 5% 提到 20%，意味着标注效率翻两番。
- **触发器是一个二分类器**，必须按二分类器评估：触发率（成本）/ 精确率 / 召回率。
  **召回率的分母只能来自无偏的随机基线采样**——否则你算出来的永远是 100%。
- **三类触发器，各自覆盖不同盲区**：
  ① **不确定性**（熵 / margin / least-confidence）——类别多时 **margin 优于熵**；
     **前提是概率已校准**，且阈值应按分位数而非绝对值设定；
  ② **一致性**（多模型分歧 / TTA / 教师-学生 / **多帧不一致**）——
     多帧一致性在 TSR 上是杀手锏：**标志是静止刚体，类别必须恒定**，
     跳变即错误，**零标注成本**，还能用近处结果反标远处困难帧；
  ③ **规则**（跟踪丢失 / 阈值震荡 / **与高精地图不符** / 接管急刹 / 罕见类 / 地理围栏）——
     最便宜、最可解释，且**与模型无关**，所以不会随模型一起变瞎。
- **框级 → 图级的聚合算子是一个隐藏的采样偏差源**：mean 偏向框少的简单帧，
  count 偏向拥挤路口。默认用 **max**，抗噪用 top-k mean。
- **触发器本身会引入偏差**（本模块最深的一条）：只回传「模型不确定的」，会
  **系统性漏掉「模型自信地错了」**（高置信 + 错误）与**完全漏检**（没框就没分数）两类。
  而**总体召回指标完全掩盖这一点**——必须做**分组偏差审计**。
  更糟的是这个盲区**自我强化**：触发器是模型的函数，模型是回传数据的函数。
- **随机基线（10–20% 预算）不能砍**：它是唯一不经过模型判断的通路，
  既能发现「未知的未知」，又提供了触发器评估的无偏分母和模型的无偏验证集。
  它会让总召回略降——**这是刻意付出的代价**。
- **预算分配是 submodular 覆盖问题**，贪心即可（1−1/e 保证）。量产配置 =
  车端便宜触发器粗筛 → 云端大模型精筛 → **按场景桶配额** → 15% 分层随机基线 → **安全阀**。
- **数据闭环真正的 KPI 不是回传量，而是「从发现问题到修复上线的周期时间」。**

下一站：**模块 04 · 大规模挖掘基础设施** —— 数据回传之后：嵌入检索、
场景打标（含用 VLM 自动打标）、去重与多样性采样、标注预算分配、数据版本与血缘。"""),
]
