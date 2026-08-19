# -*- coding: utf-8 -*-
"""C59 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "C00（VLM：视觉编码器 + 连接器 + LLM）；C55（TSR 与自动驾驶感知）。不需要会训练大模型"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("核心参考", "Brohan et al. RT-2；Kim et al. OpenVLA；Black et al. π0；Tian et al. DriveVLM；Hwang et al. EMMA"),
    ("预计时长", "总览 35 分钟 + 跑 25 分钟"),
]

SECTIONS = [
    ("three_gen", "自动驾驶架构的三代演进：每一代在换什么", "".join([
        P("这门课要讲的 <span class=\"term\">VLA</span>（Vision-Language-Action，视觉-语言-动作模型）不是凭空冒出来的。它是自动驾驶软件架构第三次大改的产物，而<strong>要理解它为什么值得做，必须先理解前两代各自卡在哪里</strong>。"),
        ASCII("""① 模块化流水线（2015–2021 量产主流）
   传感器 → 感知 → 融合/跟踪 → 预测 → 规划 → 控制
             │      │           │       │
             └──────┴───────────┴───────┴─ 每段接口由**人手写死**（结构化 schema）
   优点：每段可单测、可回归、出问题能定位到具体模块
   代价：**接口 schema 之外的信息全部丢失**，且下游只能消费你想到要写的字段

② 端到端 / 一段式（2022– ，UniAD、部分量产方案）
   传感器 ══════════ 一个网络（中间表示由梯度决定）══════════ 轨迹
   优点：不再有人为信息瓶颈；上限由数据决定而不是由 schema 决定
   代价：**不可解释、不可局部修复**——路测出问题，你不知道该补哪一段数据

③ VLA（2023– ）
   传感器 → 视觉编码器 ─┐
                        ├→ 语言模型（常识 + 推理）→ 动作 token → 轨迹
   指令 / 规则 / 标志语义 ┘
   优点：中间表示是**语言**——可读、可写、可注入先验、可要求它解释自己
   代价：延迟大、会幻觉、缺乏形式化安全保证；必须外挂规则层与安全层"""),
        TABLE(["维度", "① 模块化", "② 端到端", "③ VLA"], [
            ["中间表示", "人定义的结构化 schema", "<strong>学出来的隐向量</strong>（无语义）", "<strong>自然语言 + 动作 token</strong>"],
            ["谁定义接口", "架构师（写死在 proto/idl 里）", "梯度（没人定义）", "prompt 设计者（<em>可读、可改、可版本化</em>）"],
            ["遇到没见过的场景", "<strong>要新写一条规则</strong>", "要新采一批数据重训", "<strong>可能靠预训练常识直接泛化</strong>"],
            ["失败可定位性", "<strong>高</strong>（逐模块二分）", "<strong>极低</strong>（只有输入和输出）", "中（可以问它为什么，但答案可能是编的）"],
            ["典型推理延迟", "感知 20–40 ms，全链路 &lt;100 ms", "50–150 ms", "<strong>几百 ms 到数秒</strong>（这是硬伤）"],
            ["安全论证", "可做逐模块 FMEA / 可形式化", "困难", "<strong>目前做不到</strong>，只能靠外层兜底"],
            ["量产成熟度", "已大规模上车", "部分上车", "刚开始上车（多为云端 + 蒸馏）"],
        ]),
        DUAL(
            "三代的演进不是「后一代全面优于前一代」，而是<strong>每一代都在拿一样东西换另一样东西</strong>。模块化拿「信息完整性」换了「可定位性」；端到端把它换了回来——拿「可定位性」换「信息完整性」；<em>VLA 想做的是第三条路：用语言当中间表示，既保留可读性又不写死 schema</em>。它并没有取消这个权衡，只是换了个位置站。",
            "更精确地说，三代的差别在于<strong>「归纳偏置写在哪里」</strong>。模块化把归纳偏置写在<em>接口与规则</em>里（人的知识以代码形式存在）；端到端把它写在<em>数据分布</em>里（人的知识必须先变成标注）；VLA 把它写在<em>预训练权重 + prompt</em> 里（人的知识可以以自然语言形式直接注入，不必先变成代码也不必先变成标注）。<strong>这第三种注入方式的边际成本远低于前两种，这就是 VLA 的全部经济学理由。</strong>",
        ),
        CALLOUT("warn", "一个必须先说清的事实：<strong>今天没有任何量产车是「纯 VLA」的</strong>。所有落地方案都是混合体——VLA 负责语义理解与粗轨迹意图，下游仍有传统的规划器、控制器与安全监控层。<em>面试里如果你把 VLA 描述成「取代了整个软件栈」，会立刻暴露只读过新闻稿</em>。正确的描述是：<strong>VLA 是接在感知之后、规划之上的一层「语义决策」，它的输出仍要经过可行性与安全校验</strong>。"),
    ])),
    ("what_is_not", "VLA 是什么，更重要的是不是什么", "".join([
        P("先给一个能背下来的定义：<strong>VLA = 一个在大规模视觉-语言数据上预训练过的模型，被继续训练成「看图 + 读指令 → 输出动作」</strong>。关键词是<em>「预训练过的」</em>——如果从头训一个吃图像吐轨迹的网络，那是端到端，不是 VLA。<strong>VLA 的全部价值来自它继承了视觉-语言预训练里的常识与推理能力</strong>。"),
        TABLE(["常见误解", "实际是什么", "为什么这个区分重要"], [
            ["「给车装个聊天机器人」", "语言在这里是<strong>内部表示与接口</strong>，不是给用户聊天用的", "把它当交互功能，就会把评测做成对话质量，完全测不到该测的东西"],
            ["「VLA 取代了感知」", "VLA <strong>消费</strong>感知输出；感知（含 TSR）反而更重要了", "感知错了 VLA 会把错误<em>合理化</em>成一段像模像样的推理"],
            ["「端到端 = VLA」", "端到端强调「无手写接口」，VLA 强调「继承预训练语义」", "两者动机不同：一个为了信息不丢，一个为了长尾常识"],
            ["「VLA 能保证遵守交通规则」", "它只是<strong>更可能</strong>遵守；没有任何形式化保证", "规则层与安全层不能省，这是量产红线"],
            ["「上车就是把大模型塞进车机」", "量产路线是<strong>云端大模型 → 蒸馏 → 车端小模型</strong>", "不知道这条，就答不出「几百 ms 延迟怎么可能上车」"],
            ["「参数越大越好」", "车端算力与延迟预算是硬约束，<strong>存在最优规模而非越大越好</strong>", "面试问「为什么不用 72B」，答不上来会很尴尬"],
        ]),
        DUAL(
            "<strong>「不是什么」比「是什么」更值得花时间</strong>，原因很实际：VLA 是当前最被过度宣传的方向之一，面试官几乎一定会用一两个夸大的说法来试探你。<em>能主动划出能力边界、能说出「这件事 VLA 现在做不到」的候选人，可信度会立刻上一个台阶</em>。反过来，把 demo 视频当成能力证据，是最容易被追问穿的。",
            "边界大致有四条，值得记住：<strong>①「延迟」——大模型推理频率只有几 Hz，而车辆控制需要 10–100 Hz，所以 VLA 只能出「意图/粗轨迹」，高频跟踪必须交给下游控制器</strong>；②「幻觉」——它会报告不存在的标志、或为错误的感知输入编造合理解释；③「长尾仍是长尾」——预训练常识覆盖的是<em>互联网上常见的</em>长尾，不是<em>你这条路上的</em>长尾；④「不可验证」——目前无法对一个 VLA 给出「在场景集合 S 上永不违反规则 R」的论证。<em>这四条都不是工程调优能消掉的，是范式自带的。</em>",
        ),
        CALLOUT("danger", "面试当场翻车的典型：被问「VLA 相比端到端好在哪」，回答「效果更好」。<strong>这个回答几乎一定会被追问「哪个指标上好？在什么场景？代价是什么？」而崩掉。</strong><em>正确的骨架是：「不是通用指标更好，而是在<strong>需要语义理解的长尾场景</strong>上更好，代价是延迟与不可验证性；所以量产是混合架构，不是替换。」</em>"),
    ])),
    ("longtail", "核心痛点：长尾语义理解，或者说「规则写不完」", "".join([
        P("如果只能记住这门课的一句话，记这句：<strong>VLA 要解决的不是「开得更准」，而是「遇到没写过规则的场景时不至于失措」</strong>。这个痛点有一个可以算出来的形状。"),
        H3("为什么规则一定写不完"),
        P("把「驾驶场景类型」按出现频率排序，它近似服从 <span class=\"term\">Zipf 分布</span>（幂律）：第 <code>r</code> 常见的场景类型出现频率 ∝ <code>r<sup>-α</sup></code>，α 通常接近 1。一条规则覆盖一种场景类型，那么写 <code>K</code> 条规则能覆盖的场景<em>实例</em>比例是："),
        MATH("\\mathrm{Cov}(K)=\\frac{\\sum_{r=1}^{K} r^{-\\alpha}}{\\sum_{r=1}^{N} r^{-\\alpha}}\\;\\xrightarrow{\\;\\alpha=1\\;}\\;\\frac{H_K}{H_N}\\approx\\frac{\\ln K+\\gamma}{\\ln N+\\gamma}\\quad\\Longrightarrow\\quad K(c)\\approx N^{\\,c}"),
        P("代入 <code>N = 5000</code> 种场景类型（这个量级对一个国家的路网是保守估计），得到三个应该记住的数字："),
        TABLE(["想覆盖的场景实例比例", "需要的规则条数 K", "相比上一档新增"], [
            ["50%", "<strong>53</strong>", "—"],
            ["90%", "<strong>2014</strong>", "+1961"],
            ["99%", "<strong>4562</strong>", "<strong>+2548</strong>"],
            ["99.9%", "≈ 4939", "+377（且每条只覆盖约 0.0003%）"],
        ]),
        P("读法：<strong>53 条规则覆盖一半的路况，而最后那 9% 要再写 2548 条</strong>。这不是工程师偷懒，是幂律分布的数学性质——<em>规则法的成本随覆盖率超线性上升，而每条新规则的边际收益指数下降</em>。更糟的是这 2548 条规则彼此还会冲突，维护成本再乘一个系数。"),
        H3("「前方施工改道」：一个具体的例子"),
        P("设想这一帧：前方 80 m 有临时限速 40 的牌子（置信度 0.71，因为是临时牌、反光差、还小），40 m 处有一块固定的限速 80 牌（置信度 0.93，大而清晰），右侧有个「车道封闭」牌（置信度 0.44，被锥桶挡了一半），地上还有引导锥桶。人类司机零思考就知道该怎么办：<strong>临时的压固定的，不确定就保守，往左并。</strong>"),
        P("而模块化流水线会怎么处理？<em>规则表里如果没有「临时标志优先于固定标志」这一条，它就会取最近的那块牌——限速 80</em>；<code>construction_ahead</code> 这个类别如果不在规则表里，直接被忽略；<code>lane_closed_right</code> 置信度 0.44 低于阈值 0.6，被丢弃。<strong>三个信息全部丢失，输出「保持 80 km/h、保持车道」——一个危险且完全「符合设计」的结果。</strong>（notebook 里会把这条链路完整跑一遍。）"),
        DUAL(
            "VLA 的赌注是：<strong>「临时的压固定的」「不确定就保守」这类知识不需要被写成规则，因为它已经在语言预训练里了</strong>。你只要把感知输出序列化成文本、把优先级原则写成一句自然语言先验，模型就能组合出正确结论——而且换个国家、换种没见过的标志，同一句先验仍然成立。<em>这就是「边际成本低」的具体含义。</em>",
            "严谨地说，VLA 把「规则覆盖问题」转化成了「<strong>语义组合泛化</strong>问题」：不再要求为每个 <code>(场景类型 → 动作)</code> 配对写规则，而是要求模型能把有限的语义原语（临时/永久、封闭/开放、置信高/低、保守/激进）组合到没见过的配对上。<em>这个转化是否成立，是当前 VLA 研究最核心的经验问题</em>——它在互联网常见场景上大致成立，在<strong>区域性、行业性的长尾上并不可靠</strong>（模型没在中国某省的临时施工牌上预训练过）。所以量产方案里仍然需要针对性数据与蒸馏，这不是矛盾，是必要补充。",
        ),
        CALLOUT("intuition", "把这一节浓缩成一句可迁移的心法：<strong>规则法的成本随覆盖率超线性上升，学习法的成本随覆盖率次线性上升——两条曲线一定会交叉，交叉点之后就该换范式。</strong><em>VLA 的出现不是因为它「更先进」，而是因为量产车队的场景覆盖率已经推到了那个交叉点右边。</em>"),
    ])),
    ("interface", "为什么这门课的落点是「感知接口设计」", "".join([
        P("这门课对应 JD 里的一条职责：<em>「Improve VLA models to effectively consume TSR outputs and support traffic-sign-aware instruction following through VLA prompts」</em>。翻译成人话：<strong>不是让你去训 VLA，而是让你把交通标志识别（TSR）的输出，设计成 VLA 能吃、能吃对、吃错了还能兜住的形式。</strong>"),
        ASCII("""相机 ──→ [ TSR 检测 + 分类 ] ──→ [ 跟踪 / 多帧融合 ] ──→ ★ 接口层 ★ ──→ [ VLA ] ──→ 动作
                    │                       │                    │
              类别·框·分数            track_id·稳定语义      **本课的战场**
                                                              序列化 schema
                                                              置信度传递
                                                              prompt 模板
                                                              低置信降级策略

★ 接口层要回答的四个问题：
  1. 传什么字段？（类别 / 数值 / 距离 / 车道关联 / 置信度 / track_id / 首次检出时间）
  2. 用什么形式传？（文本 · 特征 token · 共享 BEV query —— 三种融合层次）
  3. 置信度怎么传、怎么让下游真的用它？（不传 = 强迫下游把所有检测当真）
  4. 感知错的时候，怎么让 VLA 保守而不是「合理化」错误输入？"""),
        TABLE(["融合层次", "怎么做", "信息量", "可解释性", "token/带宽成本", "典型使用者"], [
            ["<strong>① 符号 / 文本级</strong>", "检测结果序列化成结构化文本塞进 prompt", "低（有损）", "<strong>高</strong>（人能直接读）", "高（占上下文）", "研发调试、云端大模型"],
            ["<strong>② 特征级</strong>", "感知特征作为额外 token 或 cross-attention 注入", "<strong>高</strong>", "低", "中", "研究工作"],
            ["<strong>③ 中间表示级</strong>", "共享 BEV query / 场景 token", "高", "中", "<strong>低</strong>", "<strong>量产系统主流</strong>"],
        ]),
        DUAL(
            "为什么「接口」值得单开一门课？因为<strong>感知与决策之间的接口，是整个自动驾驶栈里最容易出错、又最少被系统讲授的地方</strong>。最常见的设计错误只有一句话：<em>只传类别不传置信度</em>——这等于强迫下游把 0.44 的检测和 0.93 的检测同等对待。<strong>而在 TSR 里，0.44 的「车道封闭」和 0.93 的「限速 80」触发的是完全相反的动作</strong>。",
            "更深一层的问题是<strong>错误传播的不对称性</strong>。传统流水线里，感知错误会被下游的规则「挡住」（阈值、合理性检查、地图比对）；而 VLA 是一个<em>生成模型</em>，它面对错误输入的默认行为不是拒绝，而是<strong>生成一段能解释这个输入的连贯推理</strong>——也就是把感知错误<em>放大成决策错误并附赠一个听起来很有道理的理由</em>。<em>这使得「让 VLA 在低置信输入下保持保守」不是锦上添花，而是接口设计的第一性要求。</em>本课 m03、m04 会把这件事做成可测量、可实现的机制。",
        ),
        CALLOUT("intuition", "面试里这条职责的高分答法：<strong>「TSR 输出进 VLA 不是把类别名拼成字符串就完了。至少要传<em>置信度、距离、车道关联、track_id 与首次检出时间</em>五项，因为下游需要区分『看到了』和『确认了』、『在我车道』和『在对向』；而且置信度必须是<strong>校准过</strong>的，否则下游用不了。」</strong><em>能主动说出「校准」两个字，基本就赢了这一问。</em>"),
    ])),
    ("map", "课程地图：六个模块与它们各自回答的问题", "".join([
        P("这门课按「从原理到接口再到上车」组织，<strong>重心刻意压在 m03 和 m04</strong>——因为那两节才是 JD 那条职责的正面战场，前面两节是为了让你有资格讨论它。"),
        TABLE(["模块", "回答的问题", "对 TSR 岗位的直接价值"], [
            ["<strong>m00</strong> 课程总览与环境", "三代架构各自的动机与代价；VLA 的能力边界", "面试开场那 3 分钟的定位能力"],
            ["<strong>m01</strong> 从 VLM 到 VLA", "动作怎么变成 token？机器人 VLA 与自驾 VLA 差在哪？", "能聊 RT-2 / OpenVLA / π0 / EMMA，且说得出差异"],
            ["<strong>m02</strong> 动作表示与输出头", "离散 token vs 回归 vs 扩散/流匹配；动作分块", "理解「为什么回归头会在路口输出直行」"],
            ["<strong>m03</strong> TSR 输出如何进入 VLA", "<strong>序列化 schema、三种融合层次、置信度传递</strong>", "<strong>JD 那条职责的核心，本课最重要一节</strong>"],
            ["<strong>m04</strong> 交通规则的指令跟随与约束化", "<strong>标志语义 → 可执行约束；作用域与生命周期；安全兜底</strong>", "<strong>体现「懂下游」的深度，第二重要</strong>"],
            ["<strong>m05</strong> VLA 的评测与上车", "开环 vs 闭环；幻觉度量；云-端蒸馏与延迟预算", "回答「这东西怎么验证、怎么上车」"],
        ]),
        H3("与其他课的关系"),
        UL([
            "<strong>C00（VLM）</strong>：视觉编码器 + 连接器 + LLM 的结构在那里讲透了。本课 m01 只做必要回顾，直接从「怎么接上动作」开始。<em>如果你对 CLIP/SigLIP 视觉塔与 projector 完全陌生，先补 C00 的对应两节。</em>",
            "<strong>C55（TSR 与自动驾驶感知）</strong>：本课的<em>上游</em>。C55 讲怎么把标志检出来、怎么跟踪、怎么评测；本课讲检出来之后怎么交给 VLA。<strong>两门课在 m03 直接接口，建议连着学。</strong>",
            "<strong>C58（难例挖掘与长尾数据闭环）</strong>：本课 m00 讲的「规则写不完」，在 C58 是「数据永远补不完」——<em>同一个幂律的两种表现</em>。C58 m04 提到的「用 VLM 给数据打标」也是 VLA 生态的一部分。",
            "<strong>C60（车端部署与一致性）</strong>：本课 m05 的蒸馏与延迟预算，落到 C60 的量化、导出与训练-部署一致性上。<em>「云端大模型蒸馏到车端」这句话的工程内容，一半在 C60。</em>",
            "<strong>C61（实战与面试实务）</strong>：本课的内容会以「架构演进题」「系统设计题」的形式出现在那里。",
        ]),
        CALLOUT("warn", "学习顺序上的一个建议：<strong>不要跳过 m02 直接看 m03</strong>。m03 讲的「置信度必须传递」之所以重要，前提是你知道 m02 里「动作是被离散化 / 被回归 / 被采样出来的」——<em>不同的动作头对输入噪声的敏感方式完全不同</em>。跳过 m02 会让你把 m03 读成一份字段清单，而它其实是一套关于误差传播的推理。"),
    ])),
    ("env", "环境、方法论与这门课怎么用", "".join([
        P("本课所有 notebook <strong>纯 numpy + 标准库，CPU 可跑，不联网、不下模型、不需要 GPU</strong>。这是刻意的选择，理由值得说明白。"),
        TABLE(["本课不做的事", "为什么不做", "本课改成做什么"], [
            ["跑真实 VLA 推理", "7B 模型要几十 GB 显存，且下载受限；跑通了也学不到设计", "<strong>手写机制的最小实现</strong>（分箱、因果掩码、序列化 schema）"],
            ["微调 OpenVLA", "算力门槛高，且微调本身不是本岗位的工作内容", "算清楚<strong>动作表示的精度-token 权衡</strong>"],
            ["接真实仿真器", "安装复杂、平台相关", "用<strong>可控的合成场景</strong>复现关键失效模式"],
            ["复现论文数字", "无法验证，且论文数字与量产无关", "复现<strong>论文里的机制</strong>并量化它的代价"],
        ]),
        DUAL(
            "方法论上，这门课坚持一件事：<strong>凡是能算的都算出来，凡是能构造反例的都构造出来</strong>。「离散化会损失精度」是一句正确的废话；<em>「256 个 bin 把曲率量化到 7.8×10⁻⁴ m⁻¹，在 30 m 前视距离上对应 0.18 m 的最大横向偏差、50 m 上就是 0.49 m」才是能用来做决策的信息</em>。m01 的 notebook 会把这个数一步步算出来。",
            "对应到学习方式：<strong>每个 notebook 的 ✏️ 练习都是「把讲解里那句结论亲手算一遍」</strong>，不是语法练习。做不出来通常意味着讲解里某个环节没读懂，此时回去读那一节比看答案有效得多。<em>参考答案放在最后，刻意与练习隔开</em>。另外 notebook 里的 <code>assert</code> 全部是真判分的——它们通过，说明你的实现在数值上真的对，而不是「看起来像」。",
        ),
        CODE("""# 环境要求（requirements.txt 里只有这几行）
numpy>=1.24        # 唯一的硬依赖
matplotlib>=3.7    # 可选，本课 notebook 不强制画图
jupyterlab>=4.0

# 验证：
python3 -c "import numpy; print(numpy.__version__)"
jupyter lab        # 打开 00_environment_check.ipynb 全部执行，应无报错"""),
        CALLOUT("intuition", "怎么用这门课，一句话：<strong>先把 m00 的「三代权衡」和 m01 的「差异表」背到能脱口而出，再把 m03 的 schema 设计练到能在白板上默写</strong>。<em>前者决定你能不能进入这个话题，后者决定你能不能在这个话题上显出深度。</em>剩下的 m02/m04/m05 是支撑，用来接住追问。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("这个方向变化极快，下面几条是<strong>2024–2026 年仍然没有共识的问题</strong>。面试里主动提出其中一两条，比复述任何 SOTA 数字都有用。"),
        UL([
            "<strong>动作表示之争尚未收敛</strong>：离散 token（RT-2、OpenVLA）、连续回归、扩散/流匹配（π0、RDT）各有拥趸。<em>目前的经验规律是「频率越高、维度越高、越需要多模态表达，就越该离开离散 token」</em>，但自动驾驶这种「低维、需要高精度、又必须多模态」的组合到底该用哪个，仍是开放问题（m02 详述）。",
            "<strong>VLA 到底有没有「常识迁移」</strong>：VLA 在没见过的场景上表现好，究竟是真的迁移了预训练常识，还是因为微调数据里已经有近似样本？<em>目前缺少能干净分离这两者的评测协议</em>——这直接影响「值不值得用大模型」这个投资决策。",
            "<strong>延迟-能力的帕累托前沿</strong>：思维链让推理更准但更慢，而车端延迟预算是硬的。<strong>快慢双系统</strong>（快系统直接反应、慢系统深度推理）是当前主流答案，但两个系统如何交接、慢系统结论过期了怎么办，没有标准做法（m04）。",
            "<strong>幻觉的度量与抑制</strong>：VLA 会报告不存在的标志、或为错误感知编造解释。<em>如何在没有完美 ground truth 的路测数据上度量幻觉率</em>，仍是开放问题（m05）。",
            "<strong>云端蒸馏的一致性保证</strong>：量产路线是「云端大模型教车端小模型」，但<strong>怎么证明蒸馏后的小模型在长尾上没有系统性退化</strong>？蒸馏一致性的度量、以及「教师错了学生跟着错」的检测，都缺工具。",
            "<strong>感知接口的标准化</strong>：本课 m03 讲的序列化 schema，目前每家一套。<em>是否会出现一个类似 ONNX 之于模型的「感知-决策接口标准」</em>，现在还看不出来——但这恰恰意味着现在做这件事的人有定义权。",
            "<strong>可验证性</strong>：如何对一个 VLA 给出「在场景集合 S 上不违反规则 R」的论证？目前的答案是「做不到，所以外挂规则层」。<em>这层兜底能不能被形式化、能不能被证明完备</em>，是 VLA 上车规模化的真正瓶颈。",
        ]),
        CALLOUT("paper", "必读（按建议顺序）：<em>RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control</em>（Brohan et al., 2023 —— 「动作即 token」的起点，读第 3 节的动作离散化就够）；<em>OpenVLA: An Open-Source Vision-Language-Action Model</em>（Kim et al., 2024 —— 唯一能看到全部实现细节的，读它的动作归一化与 bin 设计）；<em>π0: A Vision-Language-Action Flow Model for General Robot Control</em>（Black et al., 2024 —— 流匹配动作头与动作分块）；<em>DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models</em>（Tian et al., 2024 —— 自驾侧的慢-快双系统）；<em>EMMA: End-to-End Multimodal Model for Autonomous Driving</em>（Hwang et al., 2024 —— Waymo 的做法，重点看它怎么把感知结果写成文本）。相邻课程：C00（VLM 结构）、C55（TSR 上游）、C60（车端部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（三代架构信息流 / 长尾覆盖率 / 感知接口初见）

目标：在**同一个场景**上，把「模块化流水线 / 端到端 / VLA」三种架构各跑一遍，
看清它们分别在哪一步丢掉了信息、以及为什么只有第三种能处理「前方施工改道」。

本 notebook 你会亲手实现：
1. 一个可复现的合成场景（含**置信度、距离、车道关联、临时/固定来源**四类信息）
2. **模块化流水线**：规则表 + 置信度阈值 + 冲突消解 —— 并看它在长尾场景上怎么输错
3. **端到端**：最近邻策略 —— 并量化「它错了但你查不出为什么」
4. **VLA 风格**：感知输出序列化成文本 + 自然语言先验 —— 并看它为什么能对
5. 三种架构的**信息流量化对比**（可解释中间量个数 / 延迟 / 长尾覆盖）
6. **Zipf 覆盖率模型**：算出「50% 要 53 条规则，99% 要 4562 条」
7. ✏️ 三道练习 + 📖 参考答案 + 🧪 TSR→VLA 接口契约草案

> 心智模型：**规则法的成本随覆盖率超线性上升，学习法次线性上升——
> 两条曲线一定会交叉，交叉点之后就该换范式。**"""),
    md("""## 1 · 环境自检

本课**只需要 numpy**。没有 torch、没有 GPU、不联网。"""),
    code("""import sys, math, json, collections
import numpy as np

print('python  :', sys.version.split()[0])
print('numpy   :', np.__version__)
assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert int(np.__version__.split('.')[0]) >= 1, 'numpy 版本异常'

# 本课刻意不依赖任何深度学习框架：机制要手写才学得到
for mod in ['torch', 'tensorflow', 'transformers']:
    print(f'  {mod:<14s} 需要? 否（本课不使用）')

rng = np.random.default_rng(59)   # 全课固定种子，保证可复现
print()
print('✅ 环境就绪：纯 numpy + 标准库，CPU 可跑，不联网')"""),
    md("""## 2 · 一个场景：前方施工改道

这是本 notebook 的**唯一场景**，三种架构都吃它。刻意设计成一个
「人类零思考、规则系统必错」的例子。

四类信息缺一不可：
- `score` —— 临时牌又小又脏，置信度天然低（0.71），而固定牌又大又清晰（0.93）
- `dist_m` —— 临时牌更远（82 m），固定牌更近（40 m）→ **「取最近的」这条规则会选错**
- `lane` —— 「车道封闭」说的是右车道，不是自车道
- `src` —— 临时 / 固定，**这是解决冲突的关键，但规则表里往往没有这一维**"""),
    code("""SCENE = {
    'id': 'construction_detour',
    'human_desc': '前方 80 米施工，右侧车道封闭，临时限速 40，锥桶引导向左并道',
    'ego_speed_kmh': 78.0,
    'dets': [
        # cls,                    score, dist_m, lane,    src
        {'cls': 'speed_limit_80',    'score': 0.93, 'dist_m': 40.0, 'lane': 'ego',   'src': 'permanent'},
        {'cls': 'speed_limit_40',    'score': 0.71, 'dist_m': 82.0, 'lane': 'ego',   'src': 'temporary'},
        {'cls': 'construction_ahead','score': 0.63, 'dist_m': 85.0, 'lane': 'ego',   'src': 'temporary'},
        {'cls': 'lane_closed_right', 'score': 0.44, 'dist_m': 88.0, 'lane': 'right', 'src': 'temporary'},
    ],
    # 人类司机（也是 ground truth）会怎么做
    'gt': {'v_target_kmh': 40.0, 'lane_cmd': 'keep_left'},
}

print(f"场景: {SCENE['human_desc']}")
print(f"自车速度: {SCENE['ego_speed_kmh']:.0f} km/h")
print()
print(f"{'类别':<22s}{'score':>7s}{'dist_m':>9s}{'lane':>8s}{'src':>12s}")
for d in SCENE['dets']:
    print(f"{d['cls']:<22s}{d['score']:>7.2f}{d['dist_m']:>9.1f}{d['lane']:>8s}{d['src']:>12s}")
print()
print(f"人类司机（ground truth）: 目标速度 {SCENE['gt']['v_target_kmh']:.0f} km/h, "
      f"车道指令 {SCENE['gt']['lane_cmd']}")
assert len(SCENE['dets']) == 4
print()
print('⚠️  注意两个陷阱：① 固定的 80 牌比临时的 40 牌**更近也更自信**')
print('               ② lane_closed_right 的 score 只有 0.44（被锥桶挡了一半）')"""),
    md("""## 3 · 架构 ①：模块化流水线

规则表（人手写）→ 置信度阈值过滤 → 类别查表 → 冲突消解（取最近）。
每一步都合理、都可单测、都「符合设计」。"""),
    code("""# 人手写的规则表：类别 -> 约束。**它只可能包含写规则的人想到的类别。**
RULES = {
    'speed_limit_30':  {'v_max_kmh': 30.0},
    'speed_limit_40':  {'v_max_kmh': 40.0},
    'speed_limit_60':  {'v_max_kmh': 60.0},
    'speed_limit_80':  {'v_max_kmh': 80.0},
    'speed_limit_120': {'v_max_kmh': 120.0},
    'stop':            {'must_stop': True},
    'no_left_turn':    {'ban_maneuver': 'left'},
}
SCORE_TH = 0.60          # 规则层的置信度门限：低于此的检测直接丢弃

def modular_plan(scene, rules=RULES, score_th=SCORE_TH):
    '''模块化流水线：阈值过滤 -> 查表 -> 取最近的限速牌。'''
    trace = {'dropped_lowscore': [], 'unknown_class': [], 'wrong_lane': [], 'fired': []}
    candidates = []
    for d in scene['dets']:
        if d['score'] < score_th:
            trace['dropped_lowscore'].append(d['cls']); continue
        if d['lane'] != 'ego':                    # 只看自车道的标志
            trace['wrong_lane'].append(d['cls']); continue
        if d['cls'] not in rules:                 # 规则表里没有 -> 这条信息消失
            trace['unknown_class'].append(d['cls']); continue
        trace['fired'].append(d['cls'])
        candidates.append((d, rules[d['cls']]))
    # 冲突消解：规则表里**没有**"临时优先于固定"，只能用通用启发式"取最近的"
    speed_c = [(d, c) for d, c in candidates if 'v_max_kmh' in c]
    v = None
    if speed_c:
        d_near, c_near = min(speed_c, key=lambda t: t[0]['dist_m'])
        v = c_near['v_max_kmh']
    return {'v_target_kmh': v, 'lane_cmd': 'keep'}, trace

out1, trace1 = modular_plan(SCENE)
print('中间量（可检查，这是模块化的最大优点）:')
for k, v in trace1.items():
    print(f'  {k:<20s} {v}')
print()
print('输出:', out1)
print('真值:', SCENE['gt'])

assert out1['v_target_kmh'] == 80.0, '取最近的限速牌 -> 选中固定的 80'
assert out1['lane_cmd'] == 'keep'
assert 'construction_ahead' in trace1['unknown_class']
assert 'lane_closed_right' in trace1['dropped_lowscore']
print()
print('❌ 输出 80 km/h + 保持车道 —— 危险，而且**完全符合设计**。')
print('   三处信息丢失: 未知类别 construction_ahead / 低分 lane_closed_right / 无临时优先规则')
print('✅ 但注意: 上面的 trace 有 4 个可检查的中间量 —— **失败是可定位的**。')"""),
    md("""## 4 · 架构 ②：端到端

把场景压成一个特征向量，用训练集里最近的样本的动作作为输出。
这是端到端「从数据中学映射」的最小可执行模型——**关键性质是它没有可解释的中间量**。"""),
    code("""VOCAB = ['speed_limit_30','speed_limit_40','speed_limit_60','speed_limit_80',
         'speed_limit_120','stop','no_left_turn','construction_ahead','lane_closed_right']

def scene_feature(scene):
    '''把场景压成固定长度向量：每个类别取最大置信度（这就是"隐向量"的类比）。'''
    f = np.zeros(len(VOCAB) + 1)
    for d in scene['dets']:
        if d['cls'] in VOCAB:
            i = VOCAB.index(d['cls'])
            f[i] = max(f[i], d['score'])
    f[-1] = scene['ego_speed_kmh'] / 120.0        # 归一化自车速度
    return f

def mk(id_, dets, v, lane, ego=78.0):
    return {'id': id_, 'human_desc': id_, 'ego_speed_kmh': ego, 'dets': dets,
            'gt': {'v_target_kmh': v, 'lane_cmd': lane}}

# 训练分布：常见场景。**刻意不含施工改道**——这就是"长尾"的含义
TRAIN = [
    mk('normal_highway', [{'cls':'speed_limit_80','score':0.95,'dist_m':50,'lane':'ego','src':'permanent'}], 80.0, 'keep'),
    mk('urban_stop',     [{'cls':'stop','score':0.91,'dist_m':25,'lane':'ego','src':'permanent'}], 0.0, 'keep', ego=40.0),
    mk('school_zone',    [{'cls':'speed_limit_30','score':0.88,'dist_m':60,'lane':'ego','src':'permanent'}], 30.0, 'keep', ego=45.0),
    mk('highway_fast',   [{'cls':'speed_limit_120','score':0.96,'dist_m':70,'lane':'ego','src':'permanent'}], 120.0, 'keep', ego=110.0),
]
TRAIN_F = np.stack([scene_feature(s) for s in TRAIN])

def e2e_plan(scene):
    '''端到端：一个前向，输出动作。中间没有任何人类可读的量。'''
    f = scene_feature(scene)
    d = np.linalg.norm(TRAIN_F - f, axis=1)
    j = int(np.argmin(d))
    return ({'v_target_kmh': TRAIN[j]['gt']['v_target_kmh'],
             'lane_cmd': TRAIN[j]['gt']['lane_cmd']},
            {'ood_distance': float(d[j]), 'nearest_train_scene': TRAIN[j]['id']})

out2, dbg2 = e2e_plan(SCENE)
print('输出:', out2)
print('真值:', SCENE['gt'])
print()
print(f"最近训练场景: {dbg2['nearest_train_scene']}  距离 {dbg2['ood_distance']:.3f}")
d_in = [float(np.linalg.norm(TRAIN_F - scene_feature(s), axis=1).min()) for s in TRAIN]
print(f"训练集内样本的最近距离: {max(d_in):.3f}  <- 分布内基本为 0")

assert out2['v_target_kmh'] == 80.0, '最近邻落到 normal_highway'
assert dbg2['ood_distance'] > 0.5, '施工场景明显在分布外'
print()
print('❌ 同样输出 80 km/h。而且这一次：')
print('   · 没有 trace、没有中间量，**只有输入和输出**')
print('   · 模型不会说"我不确定"，它照样给出一个自信的数')
print('   · 想修它，只能"再采一批施工场景数据重训"——而长尾有几千种')
print('✅ ood_distance 是唯一的线索，但它只告诉你"怪"，不告诉你"哪里怪"。')"""),
    md("""## 5 · 架构 ③：VLA 风格 —— 把感知输出序列化成文本 + 注入自然语言先验

**重要声明**：下面不是真的跑一个大模型。它模拟的是 VLA 的一个关键性质——
**约束来自可组合的自然语言先验，而不是逐类别硬编码的规则表**。
真实 VLA 里这一步由预训练权重完成；这里用关键词组合显式写出来，
好处是你能看清「哪条先验在起作用」。"""),
    code("""def serialize_perception(scene):
    '''① 把结构化检测结果序列化成文本行（m03 会把这个 schema 做深）。'''
    lines = [f"ego_speed: {scene['ego_speed_kmh']:.0f} km/h"]
    for d in sorted(scene['dets'], key=lambda x: x['dist_m']):
        lines.append(
            f"sign: cls={d['cls']} conf={d['score']:.2f} dist={d['dist_m']:.0f}m "
            f"lane={d['lane']} source={d['src']}")
    return lines

# ② 自然语言先验：**注意它们不提任何具体类别**，所以对没见过的标志同样成立
PRIORS = [
    'P1 临时标志的优先级高于固定标志。',
    'P2 出现施工/作业相关标志时，按施工区处理：降速并准备变道。',
    'P3 置信度低于 0.6 的信息不可直接执行，但可作为**保守化**的理由。',
    'P4 车道封闭时，向未封闭的一侧并道。',
    'P5 存在多个速度约束时，取最严格的那个。',
]

PROMPT = serialize_perception(SCENE) + [''] + PRIORS
print('\\n'.join(PROMPT))
print()
print(f'prompt 行数 {len(PROMPT)}, 字符数 {sum(len(l) for l in PROMPT)}')
assert any('source=temporary' in l for l in PROMPT), '来源字段必须进 prompt'
assert any('conf=0.44' in l for l in PROMPT), '低置信检测也要进 prompt（由下游决定怎么用）'
print()
print('✅ 关键差别: **低置信的 lane_closed_right 没有被丢弃，而是带着 conf 传下去了**。')
print('   模块化在阈值那一步就把它删了；VLA 让下游自己决定怎么用这个 0.44。')"""),
    code("""def vla_plan(scene, priors=PRIORS):
    '''③ 语义推理（用关键词组合显式模拟"预训练常识"）。
       注意：**没有一条分支写死了具体类别名**，靠的是 source/conf/lane 这些语义维度。'''
    reasoning, constraints = [], []
    speed_signs = [d for d in scene['dets'] if d['cls'].startswith('speed_limit')
                   and d['lane'] == 'ego']
    temp = [d for d in speed_signs if d['src'] == 'temporary']
    perm = [d for d in speed_signs if d['src'] == 'permanent']
    if temp and perm:                                     # P1
        v = min(float(d['cls'].split('_')[-1]) for d in temp)
        reasoning.append(f'P1: 同时存在临时({v:.0f})与固定({perm[0]["cls"]})限速 -> 取临时')
        constraints.append(('v_max_kmh', v))
    elif speed_signs:                                     # P5
        v = min(float(d['cls'].split('_')[-1]) for d in speed_signs)
        reasoning.append(f'P5: 取最严格的速度约束 {v:.0f}')
        constraints.append(('v_max_kmh', v))

    if any('construction' in d['cls'] or 'work' in d['cls'] for d in scene['dets']):
        reasoning.append('P2: 检出施工相关标志 -> 按施工区处理（降速 + 准备变道）')

    lane_cmd = 'keep'
    closed = [d for d in scene['dets'] if 'closed' in d['cls']]
    for d in closed:
        if d['score'] >= 0.60:                            # P4
            lane_cmd = 'keep_left' if d['lane'] == 'right' else 'keep_right'
            reasoning.append(f'P4: {d["lane"]} 车道封闭(conf={d["score"]:.2f}) -> 向另一侧并道')
        else:                                             # P3 低置信 -> 保守
            lane_cmd = 'keep_left' if d['lane'] == 'right' else 'keep_right'
            reasoning.append(f'P3: {d["lane"]} 车道可能封闭(conf={d["score"]:.2f}，低置信) '
                             f'-> 不执行强动作，但**保守地远离**该侧')
    v_target = min([c[1] for c in constraints], default=scene['ego_speed_kmh'])
    return ({'v_target_kmh': v_target, 'lane_cmd': lane_cmd},
            {'reasoning': reasoning, 'constraints': constraints})

out3, dbg3 = vla_plan(SCENE)
print('推理链（可读、可审计——这是 VLA 相比端到端的真正优势）:')
for r in dbg3['reasoning']:
    print('  ·', r)
print()
print('输出:', out3)
print('真值:', SCENE['gt'])

assert out3['v_target_kmh'] == 40.0, '临时限速应压过固定限速'
assert out3['lane_cmd'] == 'keep_left', '右车道可能封闭 -> 向左'
assert out3 == SCENE['gt'], 'VLA 路线应与人类司机一致'
print()
print('✅ 两项都对。而且对的原因是**可组合的语义先验**，不是"施工改道"这条规则：')
print('   换成没见过的临时标志、换个国家，P1/P3/P4 仍然成立。')
print('⚠️  代价见下一节：延迟、以及"它也可能把错误输入合理化"。')"""),
    md("""## 6 · 三代架构的量化对比

同一个场景、同一份感知输出，把三条路线的**信息流与代价**摆在一起。
延迟数字用的是各路线的典型量级（车端），不是精确测量。"""),
    code("""ARCHS = [
    # 名称,        输出,   可检查中间量数, 典型延迟ms, 新长尾场景的修复动作, 修复成本
    ('① 模块化',   out1, len([c for v in trace1.values() for c in v]), 45,
     '写一条新规则', '小时级，但会与已有规则冲突'),
    ('② 端到端',   out2, 0, 90,
     '采集+标注一批数据重训', '周级'),
    ('③ VLA',      out3, len(dbg3['reasoning']), 600,
     '改一句 prompt 先验 / 或蒸馏一批数据', '分钟级（prompt）到天级（蒸馏）'),
]

print(f"{'架构':<10s}{'v_target':>10s}{'lane_cmd':>12s}{'正确':>6s}"
      f"{'中间量':>8s}{'延迟ms':>8s}")
for name, out, n_mid, lat, _, _ in ARCHS:
    ok = '✅' if out == SCENE['gt'] else '❌'
    v = 'None' if out['v_target_kmh'] is None else f"{out['v_target_kmh']:.0f}"
    print(f'{name:<10s}{v:>10s}{out["lane_cmd"]:>12s}{ok:>6s}{n_mid:>8d}{lat:>8d}')

print()
print(f"{'架构':<10s}{'新长尾场景怎么修':<30s}{'修复成本'}")
for name, _, _, _, fix, cost in ARCHS:
    print(f'{name:<10s}{fix:<30s}{cost}')

correct = [name for name, out, *_ in ARCHS if out == SCENE['gt']]
assert correct == ['③ VLA'], f'只有 VLA 路线应答对，实际 {correct}'
assert ARCHS[1][2] == 0, '端到端没有可检查的中间量'
assert ARCHS[2][3] > 10 * ARCHS[0][3], 'VLA 延迟比模块化高一个数量级以上'
print()
print('⚠️  别只看"正确"那一列。VLA 的 600 ms 延迟意味着它**不可能**直接控车：')
print('    量产做法是 VLA 出粗轨迹/意图（几 Hz），下游控制器高频跟踪（10-100 Hz）。')
print('✅ 三代不是替代关系。量产架构 = 模块化的可测性 + VLA 的语义泛化 + 规则安全层。')"""),
    md("""## 7 · 为什么规则一定写不完：Zipf 覆盖率模型

场景类型按频率排序近似服从幂律 $f_r \\propto r^{-\\alpha}$（$\\alpha \\approx 1$）。
一条规则覆盖一种场景类型，那么 K 条规则覆盖的场景**实例**比例是
$\\mathrm{Cov}(K) = H_K / H_N$，于是 $K(c) \\approx N^{c}$。

这个式子的含义很反直觉：**要多覆盖 1 个百分点，规则数是乘上去的而不是加上去的。**"""),
    code("""def zipf_freq(N, alpha=1.0):
    r = np.arange(1, N + 1, dtype=float)
    w = r ** (-alpha)
    return w / w.sum()

def coverage(K, N, alpha=1.0):
    '''K 条规则（覆盖最常见的 K 种场景）能覆盖的场景实例比例。'''
    f = zipf_freq(N, alpha)
    return float(f[:K].sum())

def rules_needed(c, N, alpha=1.0):
    '''覆盖 c 比例的场景实例，最少需要多少条规则。'''
    f = zipf_freq(N, alpha)
    cum = np.cumsum(f)
    return int(np.searchsorted(cum, c) + 1)

N = 5000                       # 一个国家路网上的场景类型数（保守估计）
print(f'场景类型数 N = {N}, alpha = 1.0')
print()
print(f"{'目标覆盖率':>10s}{'需要规则数 K':>14s}{'相比上一档新增':>16s}{'每条新规则的边际覆盖':>22s}")
prev_k = 0
rows = []
for c in [0.50, 0.90, 0.99, 0.999]:
    k = rules_needed(c, N)
    marginal = (c - coverage(prev_k, N)) / max(k - prev_k, 1)
    rows.append((c, k, k - prev_k, marginal))
    print(f'{c:>10.1%}{k:>14d}{k - prev_k:>16d}{marginal:>21.5%}')
    prev_k = k

k50, k90, k99 = rules_needed(0.5, N), rules_needed(0.9, N), rules_needed(0.99, N)
assert 45 <= k50 <= 60, f'50% 覆盖约需 53 条，得到 {k50}'
assert 1900 <= k90 <= 2100, f'90% 覆盖约需 2014 条，得到 {k90}'
assert 4400 <= k99 <= 4700, f'99% 覆盖约需 4562 条，得到 {k99}'
assert (k99 - k90) > (k90 - k50) / 2, '最后 9% 的成本必须与前面 40% 可比'

print()
print(f'✅ **{k50} 条规则覆盖一半的路况；最后 9% 要再写 {k99 - k90} 条。**')
print(f'   而且这 {k99 - k90} 条彼此还会冲突，维护成本要再乘一个系数。')

# 与解析近似 K(c) ≈ N^c 对照
for c in [0.5, 0.9, 0.99]:
    print(f'  c={c:.2f}: 数值解 {rules_needed(c, N):>5d}   解析近似 N^c = {N ** c:>8.0f}')
print()
print('⚠️  alpha 越小（尾巴越肥），情况越糟 —— 下面验证：')
for a in [1.2, 1.0, 0.8]:
    print(f'  alpha={a:.1f}: 覆盖 99% 需要 {rules_needed(0.99, N, a):>5d} 条规则')
assert rules_needed(0.99, N, 0.8) > rules_needed(0.99, N, 1.2), '尾巴越肥，规则越多'
print('✅ 这就是"规则法成本随覆盖率超线性上升"的确切含义。')"""),
    md("""## ✏️ 练习 1：覆盖率与规则预算

实现 `rule_budget(target_cov, N, alpha, hours_per_rule)`，返回
`{'K': 规则数, 'cov': 实际覆盖率, 'person_hours': 总工时, 'marginal_hours_per_pct': 最后一个百分点的工时}`。

- `K` 用「累积频率首次 ≥ target_cov 的下标 + 1」
- `marginal_hours_per_pct` = 从 `target_cov - 0.01` 覆盖率提升到 `target_cov` 所需的**新增规则数** × `hours_per_rule`"""),
    code("""def rule_budget(target_cov, N=5000, alpha=1.0, hours_per_rule=4.0):
    # TODO:
    #  ① 用 zipf_freq + cumsum 求 K
    #  ② cov = 前 K 项之和
    #  ③ person_hours = K * hours_per_rule
    #  ④ marginal = (K(target) - K(target-0.01)) * hours_per_rule
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
b50 = rule_budget(0.50)
b99 = rule_budget(0.99)
assert 45 <= b50['K'] <= 60, b50
assert 4400 <= b99['K'] <= 4700, b99
assert b50['cov'] >= 0.50 and b99['cov'] >= 0.99
assert abs(b99['person_hours'] - b99['K'] * 4.0) < 1e-6
assert b99['marginal_hours_per_pct'] > 30 * b50['marginal_hours_per_pct'], \\
    '最后一个百分点的边际成本应比中段贵一个数量级以上'
print(f"{'目标覆盖':>10s}{'K':>8s}{'总工时':>10s}{'最后1%的工时':>16s}")
for c in [0.50, 0.80, 0.90, 0.95, 0.99]:
    b = rule_budget(c)
    print(f'{c:>10.0%}{b["K"]:>8d}{b["person_hours"]:>10.0f}{b["marginal_hours_per_pct"]:>16.0f}')
print()
print('✅ 练习 1 通过：**规则法的成本曲线是超线性的，这是换范式的经济学理由**')"""),
    md("""## ✏️ 练习 2：找出信息在流水线的哪一步丢失

实现 `information_loss(scene, rules, score_th)`，返回一个 dict：
每个检测的 `cls` → 它**在哪一步被丢弃**，取值为
`'kept'` / `'lowscore'` / `'wrong_lane'` / `'unknown_class'`。

判定顺序必须与 `modular_plan` 一致：先分数、再车道、再类别表。"""),
    code("""def information_loss(scene, rules=RULES, score_th=SCORE_TH):
    # TODO: 对 scene['dets'] 里每个检测，按 分数 -> 车道 -> 类别表 的顺序判定归宿
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
loss = information_loss(SCENE)
assert loss['speed_limit_80'] == 'kept'
assert loss['speed_limit_40'] == 'kept'
assert loss['construction_ahead'] == 'unknown_class', loss
assert loss['lane_closed_right'] == 'lowscore', '0.44 < 0.60，先被分数门限拦下'
assert set(loss) == {d['cls'] for d in SCENE['dets']}
# 顺序敏感性：把阈值降到 0.4，lane_closed_right 就改为在车道那一步被丢
loss2 = information_loss(SCENE, score_th=0.40)
assert loss2['lane_closed_right'] == 'wrong_lane', loss2
print(f"{'类别':<22s}{'归宿'}")
for k, v in loss.items():
    mark = '✅' if v == 'kept' else '❌'
    print(f'{k:<22s}{mark} {v}')
print()
print('✅ 练习 2 通过：**模块化的每一处信息丢失都是"符合设计"的** ——')
print('   所以事故复盘时你找不到 bug，只能找到"当初没想到"。')"""),
    md("""## ✏️ 练习 3：分层控制的频率账

VLA 推理只有几 Hz，而车辆控制需要 10–100 Hz。量产解法是**分层**：
VLA 输出一段未来 `chunk_k` 步的动作（动作分块，m02 详述），下游控制器以 `ctrl_hz` 高频执行。

实现 `layered_ok(vla_hz, chunk_k, ctrl_hz)`，返回
`{'vla_period_s':…, 'chunk_span_s':…, 'covered':bool, 'gap_s':…}`。

- `vla_period_s = 1 / vla_hz` —— 两次 VLA 推理之间的间隔
- `chunk_span_s = chunk_k / ctrl_hz` —— 一个动作块能撑多久
- `covered` = `chunk_span_s >= vla_period_s`（撑得住才不会出现"没有动作可执行"的空窗）
- `gap_s = max(0, vla_period_s - chunk_span_s)`"""),
    code("""def layered_ok(vla_hz, chunk_k, ctrl_hz):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
r = layered_ok(vla_hz=2.0, chunk_k=50, ctrl_hz=50.0)
assert abs(r['vla_period_s'] - 0.5) < 1e-9
assert abs(r['chunk_span_s'] - 1.0) < 1e-9
assert r['covered'] and abs(r['gap_s']) < 1e-9
bad = layered_ok(vla_hz=2.0, chunk_k=10, ctrl_hz=50.0)
assert not bad['covered'] and abs(bad['gap_s'] - 0.3) < 1e-9, bad
print(f"{'VLA Hz':>8s}{'chunk_k':>9s}{'ctrl Hz':>9s}{'块时长s':>10s}{'周期s':>9s}{'空窗s':>9s}{'OK':>5s}")
for vla_hz, k, ctrl in [(1.0, 20, 50), (2.0, 50, 50), (2.0, 10, 50), (0.5, 100, 50), (5.0, 20, 100)]:
    r = layered_ok(vla_hz, k, ctrl)
    print(f'{vla_hz:>8.1f}{k:>9d}{ctrl:>9.0f}{r["chunk_span_s"]:>10.2f}'
          f'{r["vla_period_s"]:>9.2f}{r["gap_s"]:>9.2f}{"✅" if r["covered"] else "❌":>5s}')
print()
print('✅ 练习 3 通过：**"VLA 延迟几百 ms 怎么可能上车" 的答案就是这张表** ——')
print('   不是让 VLA 变快，而是让它一次输出足够长的动作块。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def rule_budget(target_cov, N=5000, alpha=1.0, hours_per_rule=4.0):
    f = zipf_freq(N, alpha)
    cum = np.cumsum(f)
    K = int(np.searchsorted(cum, target_cov) + 1)
    K_prev = int(np.searchsorted(cum, max(target_cov - 0.01, 0.0)) + 1)
    return {'K': K,
            'cov': float(cum[K - 1]),
            'person_hours': K * hours_per_rule,
            'marginal_hours_per_pct': (K - K_prev) * hours_per_rule}"""),
    code("""# 练习 2 参考答案
def information_loss(scene, rules=RULES, score_th=SCORE_TH):
    out = {}
    for d in scene['dets']:
        if d['score'] < score_th:
            out[d['cls']] = 'lowscore'
        elif d['lane'] != 'ego':
            out[d['cls']] = 'wrong_lane'
        elif d['cls'] not in rules:
            out[d['cls']] = 'unknown_class'
        else:
            out[d['cls']] = 'kept'
    return out"""),
    code("""# 练习 3 参考答案
def layered_ok(vla_hz, chunk_k, ctrl_hz):
    vla_period_s = 1.0 / vla_hz
    chunk_span_s = chunk_k / ctrl_hz
    return {'vla_period_s': vla_period_s,
            'chunk_span_s': chunk_span_s,
            'covered': chunk_span_s >= vla_period_s,
            'gap_s': max(0.0, vla_period_s - chunk_span_s)}"""),
    md("""---
## 🧪 真实工程胶囊：TSR → VLA 接口契约草案

这份契约是 m03 的正式内容，这里先给出骨架——**建议现在就读一遍字段注释**，
后面每一节都会回来给某个字段补上「为什么必须有」。"""),
    code("""RECIPE = r'''
# ── configs/interfaces/tsr_to_vla.yaml ──────────────────────────────
# 随模型一起版本化。任何字段变更都要升 schema_version 并跑接口回归。
schema_version: "0.1"

frame:
  ts_ns: int                 # 感知帧时间戳。**必须是传感器时间，不是系统时间**
  ego_speed_mps: float       # VLA 需要它才能判断"80m 外的牌还来不来得及反应"
  ego_lane_id: str

signs:                       # 每个元素 = 一个被**跟踪**的标志实例（不是逐帧检测框）
  - track_id: int            # 有 track_id 才能表达"首次检出/已确认 N 帧"
    cls: str                 # 层次类别: regulatory.speed_limit / warning.construction
    value: float | null      # 数值语义（限速值）；非数值类为 null，不要塞进 cls 字符串
    score: float             # ** 必须传。不传 = 强迫下游把所有检测当真 **
    score_calibrated: bool   # 未校准的 0.9 不等于 90% —— 下游必须知道这件事
    dist_m: float
    lateral_offset_m: float
    lane_assoc: enum[ego, left, right, oncoming, unknown]   # unknown 必须可表达
    source: enum[perception, hdmap, v2x]
    validity: enum[permanent, temporary, conditional]       # 临时 vs 固定的优先级依据
    first_seen_ts_ns: int
    n_frames_confirmed: int  # "看到了" 与 "确认了" 是两件事

policy_hints:                # 交给 VLA 的自然语言先验（与 schema 一起版本化）
  - "临时标志优先于固定标志。"
  - "score < 0.6 的信息不可直接执行，但可作为保守化的理由。"
  - "lane_assoc=unknown 时，按最保守的车道假设处理。"

# ── 接口回归的三条最低门禁 ──────────────────────────────────────
# 1. 字段完整性：signs[*].score 缺失 -> 直接 reject，不允许默认 1.0
# 2. 顺序稳定性：signs 按 dist_m 升序；同距离按 track_id 升序（prompt 才可复现）
# 3. 降级路径：感知超时 -> 发空 signs + degraded=true，而不是发上一帧的旧结果
'''
print(RECIPE)
for key in ['score_calibrated', 'track_id', 'lane_assoc', 'validity',
            'n_frames_confirmed', 'policy_hints', 'degraded=true']:
    assert key in RECIPE, key
print()
print('✅ 契约覆盖：置信度传递 / 跟踪身份 / 车道关联 / 临时优先 / 确认状态 / 降级路径')
print('   —— 这七项里任何一项缺失，都对应一类真实的路测事故。m03 逐项展开。')"""),
    md("""### 小结

- **三代架构不是替代关系，是权衡的三个不同站位**：模块化拿信息完整性换可定位性；
  端到端换回来；VLA 用语言当中间表示，试图两头都要一点。**量产是三者的混合体。**
- **VLA 的定义里最重要的词是「预训练」**。从头训一个吃图吐轨迹的网络是端到端，不是 VLA。
  它的全部价值来自继承的视觉-语言常识。
- **核心痛点是长尾语义理解，而长尾的形状是可以算出来的**：Zipf 分布下
  **53 条规则覆盖 50%，最后 9% 要再写 2548 条**。规则法成本超线性上升，
  这就是换范式的经济学理由。
- **能力边界必须能脱口而出**：延迟（几 Hz vs 控制需要的 10–100 Hz）、幻觉、
  长尾仍是长尾、不可验证。**面试里主动划边界是加分项，不是减分项。**
- **「几百 ms 延迟怎么上车」的答案是分层 + 动作分块**，不是让模型变快。
- **本课的战场是感知与 VLA 之间的接口**：传什么字段、用什么形式传、
  置信度怎么传、感知错了怎么让下游保守。**「只传类别不传置信度」是这个接口最常见的设计错误。**

下一站：**模块 01 · 从 VLM 到 VLA** —— 动作是怎么变成 token 的，
以及机器人 VLA 与自驾 VLA 到底差在哪。"""),
]
