# -*- coding: utf-8 -*-
"""C63 模块 00 · 课程总览与环境（ML 系统设计面试）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "做过或读过一个完整的检测/感知项目最好（C55/C57/C58/C60 任一门足够）；不需要会写生产级代码，"
                 "需要的是能在白板上画箭头、列表格、把话说清楚"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb（纯标准库 + numpy，'
                       "七步框架检查器 / 45 分钟时间预算模拟器 / 失败模式检测器 / 不确定性传播的数值演示）"),
    ("核心参考", "Chip Huyen《Designing Machine Learning Systems》(O'Reilly, 2022) · "
                 "Sculley et al. 《Hidden Technical Debt in Machine Learning Systems》(NeurIPS 2015) · "
                 "本课程 C07 模块 07（ML/eval system design 框架）· C37/C48/C58/C60（本课引用其结论，不重述细节）"),
    ("预计时长", "读 45 分钟 + 跑 35 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-system-design-tests", "system design 环节到底在评什么", "".join([
        P("最常见的误解是：候选人以为这个环节是<em>「架构复杂度竞赛」</em>——白板上箭头越多、组件名越新潮（"
          "「加一层 <span class=\"term\">feature store</span>」「上一个 <span class=\"term\">vector database</span>」），"
          "分数就越高。于是很多人把 45 分钟花在画一张看起来很唬人的图上，"
          "结果被面试官一句<strong>「你怎么知道这个模型需要这么复杂」</strong>问倒——"
          "因为图是背下来的，不是推出来的。"),
        CALLOUT("intuition", "面试官心里真正在问的只有三件事：<strong>① 你会不会先搞清楚要解决什么问题</strong>（需求澄清）、"
                             "<strong>② 你的每一个选择能不能说出为什么选它、放弃了什么</strong>（取舍显式）、"
                             "<strong>③ 我追问「如果这样呢」，你是自己先想到还是被问懵</strong>（能自我批判）。"
                             "<em>画出来的框图只是这三件事的载体，本身不计分。</em>"),
        TABLE(["候选人的常见预期", "面试官实际在打分的东西", "证据"], [
            ["图画得越复杂越显水平", "<strong>取舍是否显式</strong>——「我选了两级方案，因为长尾类别解耦更重要，代价是多一次推理延迟」", "同一张架构图，两个人讲出来分数能差 2 分"],
            ["记住了标准架构就能过", "<strong>需求澄清是否到位</strong>——同一道题换一个约束（延迟从 100ms 变成 10ms），方案要能跟着变", "背模板的人换约束后方案不变，会被当场识破"],
            ["讲完自己的方案就结束", "<strong>能否自我批判</strong>——主动说「这个方案在数据分布漂移时会失效，我们需要监控 X」", "只讲优点不讲代价，是系统设计面试里最常见的减分项"],
        ]),
        DUAL(
            "换句话说：这一环节不是在考「你会不会设计一个 TSR 系统」，因为根本不存在唯一正确答案。"
            "它在考「<strong>给你一个含糊的问题，你能不能把它变成一个你自己能证明合理的具体方案</strong>」。"
            "一个候选人如果上来就画出教科书级的完整流水线、却答不出「这一层为什么需要」，"
            "分数常常低于一个先花 5 分钟问清楚场景、只画了一个简化两级架构、但每一条线都能讲出取舍的候选人。",
            "更严谨地说，system design 面试是在用一个 45 分钟的<strong>结构化访谈</strong>，"
            "去估计候选人「面对一个未指定完全的工程问题时的决策质量」。"
            "由于没有 ground truth，评分依赖的是<em>过程信号</em>而非<em>结果信号</em>："
            "是否显式列出了约束、指标定义与假设是否前后一致、面对追问时论证是收敛还是崩溃。"
            "<strong>这也是为什么本课的核心主张是「评的不是画得多复杂，而是需求澄清 + 取舍显式 + 能自我批判」</strong>——"
            "这三者才是可以被面试官在 45 分钟内可靠观测到的信号。",
        ),
        P("在 XPENG TSR 岗位的这场面试里，题面很可能就是一句话：<em>「设计一套交通标志识别系统」</em>。"
          "面试官根本没有时间等你画出完整的感知栈——他更想看到的是你在第 3 分钟就开始问："
          "「这是面向 L2 辅助驾驶还是更高等级？标志的检测距离要求是多少？误检和漏检哪个代价更大？」"),
        CALLOUT("warn", "<strong>不要把这一环节和「八股文背诵」混淆。</strong>「FPN 怎么做多尺度融合」这类问题属于 C64（技术知识问答）；"
                        "本课要练的是<strong>把一个模糊的产品问题，在 45 分钟内变成一份可以被质询的设计</strong>——"
                        "这是完全不同的能力，也是很多刷了很多论文却在这一环节翻车的人真正缺的东西。"),
    ])),

    # ============================================================== 2
    ("seven-step-framework", "七步框架：把「设计」变成可检查的清单", "".join([
        P("整门课只有一个骨架需要背下来，就是它。七步框架的价值不在于「按这个顺序讲就一定对」——"
          "真实面试里你会被追问打断、被打回上一步——而在于<strong>它给了你一份「漏了什么」的自查清单</strong>，"
          "让你无论被打断多少次，最后都能回头把每一格补齐。"),
        ASCII("""┌────────────────────────────────────────────────────────────────────────┐
│ ① 澄清与范围 clarify & scope                                            │
│    用户是谁 / 场景 / 成功定义 / 失败定义 / 失败代价 / 约束 / 不做什么   │
│    ──────────────────────────────────────────────────────  见 C63-01    │
│        │                                                                 │
│        ▼                                                                │
│ ② 成功指标 success metrics                                              │
│    业务指标 → 模型指标 → 系统指标 三层映射，以及它们为什么会背离        │
│    ──────────────────────────────────────────────────────  见 C63-01    │
│        │                                                                 │
│        ▼                                                                │
│ ③ 数据 data                                                             │
│    来源 / 标注体系 / 划分与泄漏防范 / 长尾 / 冷启动                     │
│    ──────────────────────────────────────────────────────  见 C63-02    │
│        │                                                                 │
│        ▼                                                                │
│ ④ 建模 modeling                                                         │
│    baseline 优先，模型选型由约束驱动而非新颖度驱动                      │
│    ──────────────────────────────────────────────────────  见 C63-03    │
│        │                                                                 │
│        ▼                                                                │
│ ⑤ 评测 evaluation                                                       │
│    离线切片 + 回归门禁；在线 A/B / 影子模式；离线-在线一致性            │
│    ──────────────────────────────────────────────────────  见 C63-03    │
│        │                                                                 │
│        ▼                                                                │
│ ⑥ 服务与部署 serving & deployment                                       │
│    在线/近线/离线三层；延迟预算分解；容量估算；降级方案                 │
│    ──────────────────────────────────────────────────────  见 C63-04    │
│        │                                                                 │
│        ▼                                                                │
│ ⑦ 迭代与风险 iteration & risk                                          │
│    监控（数据漂移/指标漂移）；回滚；下一轮要做什么                      │
│    ──────────────────────────────────────────────────────  见 C63-05    │
└────────────────────────────────────────────────────────────────────────┘
        ↑____________________________________________________________|
        追问会把你打回任意一步——这不是失败，是这门课要练的能力本身"""),
        H3("七步各自解决什么问题，跳过会被记什么"),
        TABLE(["步骤", "解决什么问题", "跳过它的典型后果", "面试官心里记的那一笔"], [
            ["① 澄清与范围", "防止设计一个没人要的系统", "方案和真实约束完全脱节（比如给车端系统设计了云端才养得起的模型）", "「他没搞清楚问题就开始给方案」——<strong>最致命的一条</strong>"],
            ["② 成功指标", "定义「做得好」是什么样子，为后面所有取舍提供裁判标准", "后面讨论模型/评测时反复被问「你怎么知道这样是好的」", "「他没有可以拿来判断对错的标尺」"],
            ["③ 数据", "没有数据谈建模是空中楼阁；长尾与泄漏是决定成败的隐性因素", "只字不提数据从哪来、怎么标，直接讲模型架构", "「他假设数据会凭空出现」"],
            ["④ 建模", "证明你会按约束选方案，而不是背论文列表", "上来就讲最新的模型，不提为什么，也不提 baseline", "「他在秀新颖度，不在解决问题」"],
            ["⑤ 评测", "没有评测就无法判断系统是否真的达标，也无法安全地迭代", "讲完模型直接跳到「上线」", "「他不知道怎么验证自己」"],
            ["⑥ 服务与部署", "系统必须在真实约束（延迟/成本/硬件）下能跑起来", "只字不提延迟预算、QPS、成本", "「这套设计停留在论文阶段，从没考虑过要真正跑起来」"],
            ["⑦ 迭代与风险", "系统上线后会漂移、会犯错——没有监控和回滚就是在赌运气", "全程假设系统会完美运行，从不提失败场景", "「他没有工程事故意识」——<strong>见 §5</strong>"],
        ]),
        DUAL(
            "很多人以为「按顺序讲七步」就是标准答案，其实不是——<strong>真实面试是双向对话，"
            "面试官随时会打断你、把你打回某一步。</strong>比如你刚讲完建模，他突然问「你刚才说的成功指标，"
            "如果误检代价远大于漏检代价，还成立吗？」——这其实是把你打回了 ② 成功指标。"
            "七步框架真正的用法不是「讲稿」，是<strong>一份随时可以核对「我漏了哪一格」的清单</strong>。",
            "从信息论角度看，七步框架的作用是<strong>把一个高维、开放的设计问题，切成若干个可以独立验证的子问题</strong>。"
            "每一步都有明确的输入（上一步的产出）和输出（喂给下一步的产出），"
            "这让面试官可以在任意一步单独提问而不必等你讲完全部——"
            "<em>这也是为什么七步框架比「随手画一张架构图」更容易被追问，却也更容易拿到高分："
            "结构化本身就是一种「取舍显式」的证明。</em>",
        ),
        CALLOUT("intuition", "把七步记成三个动词会更好背：<strong>「想清楚（①②）→ 造出来（③④⑤）→ 撑得住（⑥⑦）」</strong>。"
                             "「想清楚」决定了你在解决正确的问题；「造出来」决定了方案本身是否合理；"
                             "「撑得住」决定了它在真实世界的不确定性下还能不能活下去——"
                             "<em>而「撑得住」这个维度，正是本课与传统后端 system design 分道扬镳的地方（见 §5）。</em>"),
    ])),

    # ============================================================== 3
    ("time-budget", "45 分钟怎么分：时间预算表", "".join([
        P("七步框架如果没有时间预算，最常见的翻车方式是「①②讲得意犹未尽，⑥⑦只剩 3 分钟随口带过」——"
          "而⑥⑦（服务部署、监控回滚）恰恰是最能显出工程成熟度的两步。下面这张表按<strong>45 分钟一题</strong>标定，"
          "notebook 里有可按总时长自动缩放的实现。"),
        ASCII("""0        8       13      19          27              33        39      43   45
├────────┼───────┼───────┼───────────┼───────────────┼─────────┼───────┼────┤
│①澄清   │②指标  │③数据  │  ④建模    │    ⑤评测      │ ⑥服务  │⑦迭代 │缓冲│
│  8 min │ 5min  │ 6min  │   8 min   │     6 min      │  6 min  │ 4 min │2min│
└────────┴───────┴───────┴───────────┴───────────────┴─────────┴───────┴────┘

三个不可妥协的检查点：
  第  8 分钟 —— 必须已经说出「用户是谁 / 成功是什么 / 不做什么」三句话
  第 27 分钟 —— 必须已经过了「数据 + 建模」，进入评测环节
  第 39 分钟 —— 必须已经讲到服务与部署，留出至少 4 分钟给「迭代与风险」

  ⚠️ 「迭代与风险」被压缩到 0 分钟，是这门课里最高频的翻车模式（见 §4 失败模式 ④）"""),
        P("和 C62 的编码面试六步协议对比会发现一个关键差异：<strong>system design 的「澄清」阶段（8 分钟）"
          "比编码题的「澄清」阶段（4 分钟）几乎多一倍。</strong>这不是巧合——编码题的约束通常是数字（n 的量级），"
          "而 system design 的约束是<em>语义性</em>的（用户是谁、失败代价有多大），需要更多来回问答才能钉死。"),
        TABLE(["症状", "触发时刻", "立即动作"], [
            ["澄清阶段面试官一直在追问，8 分钟打不住", "第 10 分钟仍在澄清", "主动收口：「我先按这个假设往下走，如果不对我们随时可以回来改」——<strong>停在澄清阶段不动本身就是失分</strong>"],
            ["建模讲了很多论文细节，时间被吃掉", "第 30 分钟还在讲模型", "立刻打住：「模型细节我们可以之后展开，我先把评测和部署的骨架讲完，这样您能看到完整设计」"],
            ["只剩 5 分钟，⑥⑦都没讲", "第 40 分钟", "**压缩成两句话**：「部署上我会分在线/近线两层，延迟预算按 X 分解；风险上我最担心 Y 场景的数据漂移，会用 Z 指标监控」"],
        ]),
        CALLOUT("warn", "<strong>「先讲完模型再考虑评测和部署」是最常见的时间分配错误。</strong>"
                        "很多候选人把 30 分钟花在建模的技术细节上（哪个 backbone、要不要用 transformer），"
                        "结果服务部署和迭代风险只剩「时间不够了，大概会加监控」这种空话。"
                        "<em>面试官对「有没有讲」远比对「模型选得多先进」敏感——一句具体的监控指标"
                        "（「监控每小时的漏检率变化」）比十分钟的模型架构介绍更值钱。</em>"),
    ])),

    # ============================================================== 4
    ("failure-modes", "四种常见失败模式", "".join([
        P("下面这四种失败模式，几乎覆盖了 system design 面试里绝大多数的低分案例。"
          "它们的共同特征是：<strong>候选人把一个「有不确定性、会犯错」的系统，当成了一个「写对了就不会错」的确定性系统来设计。</strong>"),
        TABLE(["失败模式", "具体表现", "面试官会怎么记", "怎么避免"], [
            ["<strong>① 直接跳到模型</strong><br>jump to model", "题目一出口就开始讲用什么 backbone、要不要上 transformer，完全跳过澄清与指标", "「他不知道要解决什么问题，就已经在给方案了」", "先用 60–90 秒复述场景与约束，讲清楚「不做什么」，再谈模型（见 C63-01）"],
            ["<strong>② 不问约束</strong><br>skip constraints", "自顾自设计一个理想化系统，从不问延迟预算、算力上限、数据规模、团队规模", "「这套方案脱离真实部署环境，是在背模板」", "主动问 SLA、算力、数据量、标注预算——问约束不是浪费时间，是加分项"],
            ["<strong>③ 不谈评测</strong><br>skip evaluation", "讲完模型直接跳到「上线」，完全不提怎么知道系统真的达标", "「他没有验证的习惯，这在生产系统里是最危险的信号」", "至少讲清楚离线怎么切片评测、在线怎么灰度/A-B（见 C63-03）"],
            ["<strong>④ 不谈失败与回滚</strong><br>skip failure & rollback", "全程假设系统会完美运行，从不提监控、降级、回滚", "「他没有工程事故意识，这个人上线出问题会手足无措」", "主动讲清楚会监控什么指标、什么条件触发回滚（见 C63-04/05）"],
        ]),
        DUAL(
            "这四种失败模式表面上互不相关，其实是<strong>同一件事的四个切面</strong>：候选人下意识地把 ML 系统当成传统软件来设计——"
            "「写对了逻辑，它就会一直正确」。①是跳过了「先弄清楚要解决什么」，②是跳过了「真实世界有约束」，"
            "③是跳过了「模型的正确性需要被验证」，④是跳过了「系统会犯错，需要兜底」。"
            "<em>四者的共同解药是同一句话：把不确定性当成设计的一部分，而不是设计完成后才考虑的意外。</em>",
            "用评分表的语言说：①②主要扣在<strong>「需求澄清」</strong>这个维度，③④主要扣在<strong>「自我批判」</strong>这个维度。"
            "一个候选人如果四个失败模式都踩中，几乎必然拿到「背了一个标准架构图但没有理解问题」的评价——"
            "这也是 §1 里反复强调「评的不是画得多复杂」的原因：<em>图可以很简单，但只要四个模式都避开了，"
            "分数就已经超过大多数只会画复杂架构图的候选人。</em>",
        ),
        CALLOUT("danger", "<strong>最隐蔽的失败方式不是「完全不讲」，而是「讲了但空洞」。</strong>"
                          "「我们会做好监控」这句话如果没有具体指标（监控什么？多大的变化触发告警？），"
                          "在面试官听来和「什么都没讲」没有区别——甚至更差，因为它制造了一种"
                          "「他以为自己讲了」的假象。<em>本课后面每一模块都会要求给出具体数字或具体规则，"
                          "而不是「合理」「充分」这类无法验证的形容词。</em>"),
    ])),

    # ============================================================== 5
    ("uncertainty-first-class", "ML system design 与传统后端 system design 的差异", "".join([
        P("很多候选人准备 system design 面试时，读的是《System Design Interview》这类偏后端的书——"
          "「设计一个短链接服务」「设计 Twitter feed」。这类系统的核心是<strong>资源与一致性的工程权衡</strong>："
          "QPS、存储、缓存一致性、CAP 定理。它们有一个共同的隐含假设：<em>只要代码写对、配置写对，"
          "系统的行为就是确定的——同样的输入永远得到同样的输出，SLA 是可以被证明满足的。</em>"),
        DUAL(
            "ML system design 打破了这个假设。<strong>就算代码完全正确、部署完全正确，模型仍然会犯错——"
            "这是设计的一部分，不是 bug。</strong>换句话说，传统后端 system design 问的是"
            "「如何保证系统在给定负载下正确运行」；<strong>ML system design 问的是「系统在本质上会犯错的情况下，"
            "如何让这个错误可控、可发现、可恢复」。</strong>这个差异决定了后面每一模块的设计重心都会不一样。",
            "严谨地说，不确定性在 ML 系统里有<strong>三个独立来源</strong>，缺一不可地要在设计里显式处理："
            "<strong>① 模型会错</strong>（不可约误差 irreducible error + 训练/测试分布之间永远存在的差距）；"
            "<strong>② 数据会漂</strong>（<span class=\"term\">data drift</span>：线上输入分布随时间偏离训练时的分布，"
            "比如新出现的电子可变限速牌样式）；<strong>③ 指标会背离</strong>（业务指标、模型指标、系统指标"
            "在同一套改动下可能给出不一致的结论，见 C63-01 的三层指标映射）。"
            "<em>传统后端系统里没有这三个来源——一次数据库写入的正确性不会随时间「漂移」。</em>",
        ),
        H3("一个具体的数字：可靠性是「链式相乘」，不是「取最短板」"),
        P("传统后端工程师有一个根深蒂固的直觉——<span class=\"term\">weakest link</span>（最短板）思维："
          "系统的可靠性大致等于最不可靠的那个组件，因为无状态服务之间的错误通常不会相互放大。"
          "这个直觉在 ML 感知流水线里是<strong>危险的错觉</strong>。"),
        MATH("R_{\\text{system}} \\;=\\; \\prod_{i=1}^{k} r_i \\qquad (r_i：第 \\, i \\, 个阶段独立正确的概率)"),
        P("以一个简化的 TSR 流水线为例：检测正确率 0.95，跨帧关联（tracking association）正确率 0.90，"
          "多传感器融合正确率 0.97——每一项单独看都「相当不错」。用最短板思维，你会以为整体表现约等于 90%。"
          "但按链式相乘：$0.95\\times0.90\\times0.97\\approx0.829$，<strong>比任何单一环节都差 7 个百分点以上</strong>。"
          "更极端地，如果一条流水线有 5 个环节，每个环节都高达 97%（听起来已经很优秀），"
          "整体也只剩 $0.97^5\\approx0.859$——<strong>five nines 的错觉在多级流水线里迅速崩塌</strong>。"),
        CALLOUT("intuition", "<strong>这就是「不确定性是一等公民」的数字含义。</strong>传统后端设计里，"
                             "你默认每个微服务「写对了就是 100% 正确」，所以只需要关心最慢/最不可用的那个组件；"
                             "ML 流水线里每个环节都有独立的犯错概率，<em>错误会沿着流水线复合</em>——"
                             "这也是为什么 C63-05 的六个案例演练里，每一个都会要求你显式算一遍"
                             "「端到端的复合正确率大概是多少」，而不是只报每个模块单独的指标。"),
        P("这个差异也解释了为什么 §4 的四种失败模式在传统后端面试里几乎不会被扣分——"
          "「不谈失败与回滚」在一个无状态 CRUD 服务里确实不那么致命，但在一个<strong>本质上会犯错</strong>的感知系统里，"
          "没有监控和回滚约等于没有设计过这个系统。"),
    ])),

    # ============================================================== 6
    ("course-boundaries", "本课与既有课程的分工", "".join([
        P("在动手做本课的模块 01–05 之前，先把「这门课不讲什么」钉死——本批课程刻意避免重复造轮子，"
          "需要具体技术细节时，正文会用「见 CXX-XX」引用，<strong>不会在本课里重新展开</strong>。"),
        TABLE(["课程", "覆盖内容", "与 C63 的关系"], [
            ["C07 模块 07", "ML/eval system design 的一节框架性介绍", "<strong>C63 是这一节的完整展开</strong>：45 分钟怎么答的方法论 + 六个案例库"],
            ["C37", "MLOps 全生命周期（CI/CD、训练流水线工程）", "C63 引用其结论回答「怎么持续迭代」，不重复讲流水线怎么搭"],
            ["C48", "云端部署架构", "C63 模块 04 引用其结论作为服务层选项之一，不重复讲云服务配置细节"],
            ["C58", "难例挖掘与长尾数据闭环", "C63 模块 02/05 引用其结论作为数据策略依据，不重复挖掘算法本身"],
            ["C60", "车端部署与训练-部署一致性", "C63 模块 04/05 引用其结论，不重复 TensorRT/INT8/C++ 推理细节"],
            ["C61", "检测工程实战与项目叙事", "C61 讲「怎么讲你做过的真实项目」；<strong>C63 讲「怎么设计一个假设的新系统」</strong>——态度相通，场景不同"],
            ["C65", "结构化问题求解与沟通", "C63 的七步框架是 C65「澄清→分解→假设验证→收敛权衡」四步框架在 system design 场景下的具象化"],
        ]),
        DUAL(
            "简单说：如果你发现自己在 system design 面试里开始讲「TensorRT 的 INT8 校准算法选哪个」，"
            "你已经越界到 C60 的内容——<strong>正确的做法是把结论提出来，把细节推迟</strong>：「量化上我们会做校准，"
            "有专门的一套排查方法，现在先假设它能把精度损失控制在 1 个点以内，往下讲」。",
            "这种「结论显式化、细节可推迟」的能力，本身就是本课要练的核心技能之一——"
            "<em>它同时也是应对 45 分钟时间压力最有效的策略：与其把预算耗在你最熟悉的一个子话题上，"
            "不如保证七步框架的每一格都被摸到，需要深挖的地方留给面试官主动追问。</em>",
        ),
        CALLOUT("warn", "<strong>C61 模块 05 的白板题（手撕 IoU/NMS/mAP/匈牙利/Focal）不属于本课</strong>，"
                        "那是「Practical Coding Exercise」板块的内容；本课对应的是 HR 邮件里单独列出的"
                        "「system design」这一项。同理，C64 的「解释 BN 和 LN 的区别」这类口头知识问答也不在本课范围内。"),
    ])),

    # ============================================================== 7
    ("frontier", "研究前沿与开放问题", "".join([
        P("最后放一组更长期的问题——它们不会出现在你的一面里，但会影响你怎么看待「系统设计能力」这件事本身。"),
        UL([
            "<strong>system design 面试的可教性有多高？</strong>它更像一种沟通协议而非可以刷题掌握的知识。"
            "近年来工业界围绕这套框架已经形成了相当程度的共识（Chip Huyen 的书某种意义上就是把各大厂的"
            "内部培训材料公开化），<em>但这套共识本身是否真的能预测「谁能设计出好系统」，缺乏公开的实证研究"
            "——这一点和 C62-00 提到的编码面试预测效度问题是同一类困境。</em>",
            "<strong>LLM/agent 系统给这套框架带来了新的不确定性来源。</strong>七步框架里的「④ 建模」正在从"
            "「训练一个模型」变成「选择基础模型 + 设计 prompt/微调策略」；「⑦ 迭代与风险」里的漂移"
            "也从「数据分布漂移」扩展到「prompt 漂移」「上下文窗口截断导致的信息丢失」。"
            "<em>框架本身仍然适用，但每一格里装的技术内容正在快速变化。</em>",
            "<strong>「评测能否覆盖分布外场景」仍是没有标准答案的开放问题。</strong>这和 C58 的难例挖掘、"
            "C61 的 TIDE 误差分析高度相关，但目前没有一套闭环方法能保证「线下评测通过 = 线上不会出新的失效模式」——"
            "本课能给的只是一套<em>让这个风险被显式讨论</em>的框架，而不是消除这个风险的算法。",
            "<strong>45 分钟能否真的评估出系统设计能力，业界内部也有怀疑。</strong>它本质上是一个高噪声的单样本测量："
            "换一个面试官、换一道题面，同一候选人的表现方差可能相当大。<em>正确的应对方式不是追求「答对」，"
            "而是把过程做得足够结构化，让这次高噪声测量尽量落在你能力分布的中位数附近，而不是运气好坏的极端。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Chip Huyen, <em>Designing Machine Learning Systems</em>（O'Reilly, 2022）——"
                         "全书基本就是这套七步框架的教科书版展开，第 1、6、8、11 章尤其对应本课模块 01/03/04/05。"
                         "<strong>★</strong> D. Sculley et al., <em>Hidden Technical Debt in Machine Learning Systems</em>"
                         "（NeurIPS 2015）——讲清楚为什么 ML 系统的复杂度不在模型本身而在周边（数据依赖、反馈环路、监控），"
                         "是理解「为什么⑥⑦这么重要」的最短路径。"
                         "<strong>★</strong> Breck et al., <em>The ML Test Score</em>（2017）——一套评测 ML 系统生产就绪度的"
                         "checklist，与本课七步框架的⑥⑦高度呼应。</p>"
                         "<p>配套材料：Alex Xu, <em>System Design Interview</em>——传统后端 system design 的参照系，"
                         "用于对比理解「ML 特有」的部分究竟特在哪里。相邻课程：<strong>C07 模块 07</strong>（框架的原型一节）、"
                         "<strong>C61</strong>（真实项目的叙事）、<strong>C64</strong>（技术知识问答）、"
                         "<strong>C65</strong>（结构化问题求解）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（七步框架 / 45 分钟时间预算 / 失败模式检测 / 不确定性传播）

目标：把「system design 面试怎么答」从一堆经验之谈，变成**几个可以运行、可以断言的小工具**。

本 notebook 你会亲手实现：
1. **环境自检** —— 确认 Python / numpy 可用（本课全程不需要 GPU、不需要联网）
2. **七步框架检查器** —— 给一份「你实际讲了什么」的步骤序列，自动指出漏了哪步、哪两步顺序反了
3. **45 分钟时间预算模拟器** —— 按总时长自动缩放，给出不可妥协的检查点
4. **不确定性传播的数值演示** —— 为什么 ML 流水线的可靠性是「链式相乘」而不是「取最短板」
5. **四道练习**：失败模式检测器 / 超时报警器 / 反解「需要多可靠的单级」/ 一份完整的赛后复盘工具

> 心智模型：**评的不是画得多复杂，是「需求澄清 + 取舍显式 + 能自我批判」。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'isclose')
print('\\n✅ 环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · 七步框架检查器

给一份「你实际做了什么」的动作序列（`trace`，元素是七个步骤 key 的列表，可重复、可乱序），
自动指出 **(a) 漏了哪一步？(b) 哪两步的顺序反了？**

顺序违规的定义：规范里 `a` 应在 `b` 之前，但你**首次**做 `b` 的时刻早于首次做 `a` —— 记一次违规 `(b, a)`。
这和 C62-00 的六步协议检查器是同一套逻辑，换成了七步框架。"""),

    code("""STEPS7 = [
    ('clarify_scope',   '① 澄清与范围',   '用户/场景/成功定义/失败定义/失败代价/约束/不做什么'),
    ('metrics',         '② 成功指标',     '业务指标 -> 模型指标 -> 系统指标 三层映射'),
    ('data',            '③ 数据',         '来源/标注/划分/长尾/冷启动'),
    ('modeling',        '④ 建模',         'baseline 优先，约束驱动选型'),
    ('evaluation',      '⑤ 评测',         '离线切片 + 在线 A/B，一致性检查'),
    ('serving',         '⑥ 服务与部署',   '延迟预算/容量估算/降级方案'),
    ('iteration_risk',  '⑦ 迭代与风险',   '监控/回滚/下一轮迭代计划'),
]
RANK = {k: i for i, (k, _, _) in enumerate(STEPS7)}

def check_framework(trace):
    \"\"\"trace: 实际步骤序列（key 列表）。返回 (missing, inversions)。\"\"\"
    missing = [k for k, _, _ in STEPS7 if k not in trace]
    first = {}
    for pos, t in enumerate(trace):
        first.setdefault(t, pos)
    inversions = set()
    present = [k for k in RANK if k in first]
    for a in present:
        for b in present:
            if RANK[a] < RANK[b] and first[a] > first[b]:
                inversions.add((b, a))
    return missing, sorted(inversions, key=lambda p: (RANK[p[0]], RANK[p[1]]))

for k, name, what in STEPS7:
    print(f'{name:<10} {what}')"""),

    code("""# —— 三种典型表现 ——
good  = ['clarify_scope', 'metrics', 'data', 'modeling', 'evaluation', 'serving', 'iteration_risk']
jump  = ['modeling', 'clarify_scope', 'metrics', 'data', 'evaluation', 'serving', 'iteration_risk']  # 上来先讲模型
noeval = ['clarify_scope', 'metrics', 'data', 'modeling', 'serving', 'iteration_risk']               # 完全没提评测

m1, i1 = check_framework(good)
assert m1 == [] and i1 == []

m2, i2 = check_framework(jump)
assert m2 == []
assert ('modeling', 'clarify_scope') in i2 and ('modeling', 'metrics') in i2

m3, i3 = check_framework(noeval)
assert m3 == ['evaluation'] and i3 == []

print('good   -> 缺失', m1, '违规', i1)
print('jump   -> 违规', i2, '  <- 模型讲在了澄清与指标之前')
print('noeval -> 缺失', m3, '  <- 完全没有评测环节')
print('\\n✅ 检查器就位：把一次设计演练的动作记录喂进来，就能自动指出漏了哪一格。')"""),

    md("""## 2 · 45 分钟时间预算模拟器

预算按比例缩放（30/45/60 分钟通用），最后一项 `buffer` 吸收取整误差，保证**总和严格等于总时长**。
基准（45 分钟制）：①8 ②5 ③6 ④8 ⑤6 ⑥6 ⑦4 + 缓冲2。"""),

    code("""BUDGET7 = [('clarify_scope', 8), ('metrics', 5), ('data', 6), ('modeling', 8),
           ('evaluation', 6), ('serving', 6), ('iteration_risk', 4), ('buffer', 2)]   # 基准：45 分钟

def budget(total_min=45):
    \"\"\"按比例缩放到 total_min，最后一项吸收取整误差。\"\"\"
    base = sum(m for _, m in BUDGET7)
    out, acc = [], 0
    for name, m in BUDGET7[:-1]:
        v = int(round(total_min * m / base))
        out.append((name, v)); acc += v
    out.append((BUDGET7[-1][0], total_min - acc))
    return out

def cumulative(total_min=45):
    \"\"\"每一步「应该在第几分钟前结束」。\"\"\"
    acc, out = 0, []
    for name, m in budget(total_min):
        acc += m
        out.append((name, acc))
    return out

for total in (30, 45, 60):
    plan = budget(total)
    assert sum(v for _, v in plan) == total, (total, plan)
    print(f'{total} 分钟 :', ' '.join(f'{k}={v}' for k, v in plan))

c45 = dict(cumulative(45))
assert c45['clarify_scope'] == 8 and c45['modeling'] == 27 and c45['serving'] == 39
print('\\n三个不可妥协的检查点（45 分钟制）：')
print(f\"  第 {c45['clarify_scope']:>2} 分钟 —— 必须已说出「用户是谁 / 成功是什么 / 不做什么」\")
print(f\"  第 {c45['modeling']:>2} 分钟 —— 必须已经过完数据与建模，进入评测\")
print(f\"  第 {c45['serving']:>2} 分钟 —— 必须讲到服务部署，留时间给「迭代与风险」\")
print('\\n✅ 预算器就位。')"""),

    md("""## 3 · 不确定性传播：为什么可靠性是「链式相乘」

传统后端工程师的直觉是「最短板决定整体」（weakest link）。ML 流水线里每一级都有独立犯错概率，
正确的模型是**相乘**，不是**取最小值**——这正是本课与传统后端 system design 的关键差异（见正文 §5）。"""),

    code("""def pipeline_success_rate(rates):
    \"\"\"多级流水线的端到端正确率 = 各级独立正确率之积。\"\"\"
    r = 1.0
    for x in rates:
        r *= x
    return r

# TSR 三级流水线：检测 0.95、跨帧关联 0.90、多传感融合 0.97
tsr_rates = [0.95, 0.90, 0.97]
tsr_chain = pipeline_success_rate(tsr_rates)
tsr_weakest_link = min(tsr_rates)

assert abs(tsr_chain - 0.82935) < 1e-6
assert tsr_chain < tsr_weakest_link          # 链式相乘 < 最短板估计 —— 这是关键结论

print(f'各级正确率: {tsr_rates}')
print(f'最短板直觉给出的估计: {tsr_weakest_link:.3f}')
print(f'实际链式相乘的整体正确率: {tsr_chain:.3f}   <- 比任何单一环节都差 {(tsr_weakest_link-tsr_chain)*100:.1f} 个百分点')

# 更极端的例子：5 级流水线，每级都高达 97%（听起来已经很优秀）
five_stage = pipeline_success_rate([0.97] * 5)
assert abs(five_stage - 0.97 ** 5) < 1e-9
print(f'\\n5 级流水线、每级 97%: 整体只剩 {five_stage:.3f}')
print('✅ 结论：级数越多，"每级都很优秀"造成的整体可靠性错觉就越危险。')"""),

    md("""## ✏️ 练习 1：失败模式检测器

在 `check_framework` 基础上实现 `detect_failure_modes(trace)`，
返回触发的失败模式集合（`set`），取值来自 `{'jump_to_model', 'skip_constraints', 'skip_evaluation', 'skip_rollback'}`：

- `jump_to_model`：`('modeling','clarify_scope')` 或 `('modeling','metrics')` 出现在 inversions 里；
  **或** `'modeling'` 在 trace 里但 `'clarify_scope'` / `'metrics'` 整个缺失（完全没做，比顺序反了更严重）
- `skip_constraints`：`'clarify_scope'` 缺失
- `skip_evaluation`：`'evaluation'` 缺失
- `skip_rollback`：`'iteration_risk'` 缺失"""),

    code("""def detect_failure_modes(trace):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
onlymodel = ['modeling']   # 只做了建模，什么都没澄清

assert detect_failure_modes(good) == set()
assert detect_failure_modes(jump) == {'jump_to_model'}
assert detect_failure_modes(noeval) == {'skip_evaluation'}
assert detect_failure_modes(onlymodel) == {'jump_to_model', 'skip_constraints', 'skip_evaluation', 'skip_rollback'}

for name, trace in [('good', good), ('jump', jump), ('noeval', noeval), ('onlymodel', onlymodel)]:
    print(f'{name:<10} -> {detect_failure_modes(trace)}')
print('\\n✅ 练习 1 通过：把一次模拟设计演练的动作序列喂进来，就能自动列出触发了哪些失败模式。')"""),

    md("""## ✏️ 练习 2：超时报警器

实现 `time_budget_alarm(elapsed, done_steps, total=45)`，返回 `'ok'` / `'speed_up'` / `'fallback'`。

规则：
- `expected` = `cumulative(total)` 里 `done_steps` 最后一个元素对应的结束时刻（`done_steps` 为空则为 0）
- `elapsed <= expected + 3` → `'ok'`
- `elapsed <= expected + 10` → `'speed_up'`
- 否则 → `'fallback'`（放弃深入某一步的细节，立刻压缩讲完剩余步骤）"""),

    code("""def time_budget_alarm(elapsed, done_steps, total=45):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
# 45 分钟制的累计结束时刻：clarify=8 metrics=13 data=19 modeling=27 evaluation=33 serving=39 iteration_risk=43
assert time_budget_alarm(0,  []) == 'ok'
assert time_budget_alarm(10, ['clarify_scope']) == 'ok'                          # 8+3=11
assert time_budget_alarm(15, ['clarify_scope']) == 'speed_up'                    # <= 8+10=18
assert time_budget_alarm(20, ['clarify_scope']) == 'fallback'                    # > 18
assert time_budget_alarm(30, ['clarify_scope', 'metrics', 'data', 'modeling']) == 'ok'         # 27+3=30
assert time_budget_alarm(35, ['clarify_scope', 'metrics', 'data', 'modeling']) == 'speed_up'   # <= 27+10=37
assert time_budget_alarm(40, ['clarify_scope', 'metrics', 'data', 'modeling']) == 'fallback'    # > 37
assert time_budget_alarm(11, ['clarify_scope'], total=30) == 'speed_up'          # 30 分钟制：clarify 只到第 5 分钟

for e, d in [(0, []), (10, ['clarify_scope']), (20, ['clarify_scope']), (35, ['clarify_scope', 'metrics', 'data', 'modeling'])]:
    print(f'第 {e:>2} 分钟，已完成到 {d[-1] if d else \"(未开始)\"} -> {time_budget_alarm(e, d)}')
print('\\n✅ 练习 2 通过：第 39 分钟还没讲到服务部署，报警器应该已经在叫了。')"""),

    md("""## ✏️ 练习 3：反解「单级需要多可靠」

实现 `required_stage_reliability(k, target)`：给定流水线有 `k` 级、且假设每级正确率相同 `r`，
求满足 $r^k \\ge \\text{target}$ 的**最小** `r`（用公式 $r = \\text{target}^{1/k}$ 直接求解即可，不需要二分）。"""),

    code("""def required_stage_reliability(k, target):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
r5 = required_stage_reliability(5, 0.99)
r10 = required_stage_reliability(10, 0.99)

assert abs(r5 - 0.99 ** (1/5)) < 1e-9
assert abs(r5 ** 5 - 0.99) < 1e-9
assert abs(required_stage_reliability(1, 0.9) - 0.9) < 1e-12
assert r10 > r5, '流水线级数越多，单级需要的可靠性反而越高（同样的整体目标下）'

print(f'5 级流水线要达到整体 99%，单级至少要 {r5:.4f}')
print(f'10 级流水线要达到整体 99%，单级至少要 {r10:.4f}（比 5 级更苛刻）')
print('\\n✅ 练习 3 通过：这是 §5 结论的反向用法——流水线越长，对每一级的可靠性要求越苛刻。')"""),

    md("""## ✏️ 练习 4：赛后复盘工具（综合练习）

把前面三个工具组合成一份「45 分钟结束后」的复盘报告。
实现 `design_review(trace, elapsed_total, total=45)`，返回：

```
{'missing': [...], 'inversions': [...], 'failure_modes': {...}, 'over_time': True/False}
```

`over_time` 表示实际用时 `elapsed_total` 是否超过了 `total`（不需要用到 `time_budget_alarm`，
这是赛后的整体复盘，不是过程中的实时报警）。"""),

    code("""def design_review(trace, elapsed_total, total=45):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
r1 = design_review(good, 44, 45)
assert r1 == {'missing': [], 'inversions': [], 'failure_modes': set(), 'over_time': False}

r2 = design_review(good, 50, 45)
assert r2['over_time'] is True

r3 = design_review(noeval, 45, 45)
assert r3['missing'] == ['evaluation'] and r3['failure_modes'] == {'skip_evaluation'} and r3['over_time'] is False

r4 = design_review(onlymodel, 10, 45)
assert r4['failure_modes'] == {'jump_to_model', 'skip_constraints', 'skip_evaluation', 'skip_rollback'}

for name, r in [('good(44min)', r1), ('good(50min,超时)', r2), ('noeval', r3), ('onlymodel', r4)]:
    print(f'{name:<18} -> {r}')
print('\\n✅ 练习 4 通过：一份可以直接拿去给自己模拟面试录像打分的复盘工具。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def detect_failure_modes(trace):
    missing, inversions = check_framework(trace)
    modes = set()
    jumped = (('modeling', 'clarify_scope') in inversions
              or ('modeling', 'metrics') in inversions
              or ('modeling' in trace and ('clarify_scope' in missing or 'metrics' in missing)))
    if jumped:
        modes.add('jump_to_model')
    if 'clarify_scope' in missing:
        modes.add('skip_constraints')
    if 'evaluation' in missing:
        modes.add('skip_evaluation')
    if 'iteration_risk' in missing:
        modes.add('skip_rollback')
    return modes"""),

    code("""# 练习 2 参考答案
def time_budget_alarm(elapsed, done_steps, total=45):
    cum = dict(cumulative(total))
    expected = cum[done_steps[-1]] if done_steps else 0
    if elapsed <= expected + 3:
        return 'ok'
    if elapsed <= expected + 10:
        return 'speed_up'
    return 'fallback'"""),

    code("""# 练习 3 参考答案
def required_stage_reliability(k, target):
    return target ** (1.0 / k)"""),

    code("""# 练习 4 参考答案
def design_review(trace, elapsed_total, total=45):
    missing, inversions = check_framework(trace)
    modes = detect_failure_modes(trace)
    return {
        'missing': missing,
        'inversions': inversions,
        'failure_modes': modes,
        'over_time': elapsed_total > total,
    }"""),

    md("""---
## 🧪 真实工程胶囊：45 分钟开场脚手架 + 七步自检清单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 开场 90 秒该说什么（拿到题目后，先说这一段，不要沉默）
# ══════════════════════════════════════════════════════════════════════
# 「在我开始设计之前，我想先确认几件事：这个系统的用户是谁、在什么场景下用、
#  怎么算成功、怎么算失败、失败的代价有多大、有哪些硬约束（延迟/算力/数据）、
#  以及——同样重要——第一版我们明确不做什么。」
# 这一段话同时覆盖了七步框架的 ①，也提前打消了 §4 失败模式 ①②的风险。

# ══════════════════════════════════════════════════════════════════════
# B. 七步自检清单（面试进行中，随时对照这张表看漏了哪一格）
# ══════════════════════════════════════════════════════════════════════
# □ ① 澄清与范围   —— 用户/场景/成功/失败/代价/约束/不做什么 都说了吗？
# □ ② 成功指标     —— 业务指标 -> 模型指标 -> 系统指标，三层都提到了吗？
# □ ③ 数据         —— 来源/标注/划分/长尾，至少提一句？
# □ ④ 建模         —— 有没有先给 baseline，再讲更复杂的方案？
# □ ⑤ 评测         —— 离线怎么测、在线怎么灰度，都说了吗？
# □ ⑥ 服务与部署   —— 延迟预算、容量、降级方案，有没有具体数字？
# □ ⑦ 迭代与风险   —— 监控什么指标、什么条件回滚，说清楚了吗？
#   ⚠️ ⑥⑦ 最容易在时间不够时被压缩成空话 —— 宁可少讲①-⑤的细节也要留时间给它们

# ══════════════════════════════════════════════════════════════════════
# C. 卡住/被追问时的应对（中 / EN）
# ══════════════════════════════════════════════════════════════════════
# 被问「为什么选这个方案」CN: 「主要是因为约束 X，取舍是我们放弃了 Y，换来了 Z。」
#                          EN: "Mainly because of constraint X; the tradeoff is we give up
#                               Y in exchange for Z."
# 被问「如果约束变了呢」  CN: 「如果 X 变成这样，我会把方案改成……，因为……」
#                          EN: "If X changes to this, I'd switch the design to ...,
#                               because ..."
# 想不出细节时           CN: 「这部分我们课程里有更细的展开，现在先给出结论，往下讲行吗？」
#                          EN: "There's a deeper rabbit hole here — let me state the
#                               conclusion and move on, is that OK?"

# ══════════════════════════════════════════════════════════════════════
# D. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 需求澄清与三层指标映射细节        -> C63 模块 01（下一站）
# · 数据系统设计（标注/泄漏/冷启动）  -> C63 模块 02
# · 建模与评测设计                    -> C63 模块 03
# · 服务、部署与容量估算              -> C63 模块 04
# · 六个完整案例演练（含 TSR 主案例） -> C63 模块 05
# · MLOps 生命周期 / 云部署 / 数据闭环 / 车端一致性的技术细节
#   -> 分别见 C37 / C48 / C58 / C60（本课引用结论，不重述）
'''
print(RECIPE)
for token in ['90 秒', '七步自检清单', 'tradeoff', 'C63 模块 01', 'C37', 'C60']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：开场脚手架 / 七步自检 / 追问应对话术 / 课程分工')"""),

    md("""### 小结

- **system design 面试评的不是画得多复杂**，而是「需求澄清 + 取舍显式 + 能自我批判」——
  三者都是可以在 45 分钟内被面试官可靠观测到的**过程信号**，而不是「方案本身有多新颖」这种结果信号。
- **七步框架**（澄清与范围 → 成功指标 → 数据 → 建模 → 评测 → 服务与部署 → 迭代与风险）
  的价值不是「按顺序讲」，是**一份随时能核对「漏了哪一格」的清单**——真实面试会不断把你打回某一步。
- **45 分钟时间预算**里最容易翻车的不是澄清阶段拖太久，而是**⑥⑦（服务部署、迭代风险）被压缩成空话**；
  三个不可妥协的检查点是第 8 分钟（澄清完）、第 27 分钟（进入评测）、第 39 分钟（讲到服务部署）。
- **四种失败模式**（跳到模型 / 不问约束 / 不谈评测 / 不谈失败回滚）本质是同一件事：
  把一个会犯错的 ML 系统当成写对了就不会错的传统软件来设计。
- **ML system design 与传统后端 system design 的核心差异是不确定性的地位**：
  传统系统里可靠性近似取「最短板」，ML 流水线里可靠性是**链式相乘**——
  三级 95%/90%/97% 的流水线整体只剩 82.9%，比任何单级都差。这正是本课七步框架里
  ⑥⑦两步分量特别重的原因。

下一站：**模块 01 · 需求澄清与指标定义** —— 把七步框架的第①②步拆开讲透：
怎么用一份提问清单把模糊需求变成可验收规格，以及业务指标为什么总在系统上线后开始"背离"模型指标。"""),
]
