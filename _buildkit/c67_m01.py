# -*- coding: utf-8 -*-
"""C67 模块 01 · Judge 设计（粒度、rubric、参考答案、CoT 与结构化输出）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（judge 是测量仪器 / 三种用法 / 体检六项）；"
                 "会读简单的 JSON schema"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_judge_design.ipynb'
                       '（分数分布压缩的度量与三种缓解 / 平局处理的三种口径 / '
                       'rubric 分解 vs 整体分的分辨力 / 参考答案的效果 / '
                       '结构化输出解析失败率与重试策略 / few-shot 锚点对分布的影响）'),
    ("核心参考", "Zheng et al., <em>MT-Bench &amp; Chatbot Arena</em>（NeurIPS 2023，pairwise 与 single-answer grading 的对比）· "
                 "Liu et al., <em>G-Eval</em>（EMNLP 2023，CoT + 概率加权打分）· "
                 "Kim et al., <em>Prometheus</em>（2023/2024，细粒度 rubric 与参考答案）· "
                 "Zhou et al., <em>IFEval</em>（2023，可验证指令的思想）· "
                 "本课程 C10 模块 04（人类评测的量表设计）· C66 模块 02（不变量检查）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("decidability", "先问「问什么」：判分问题的可判定性阶梯", "".join([
        P("设计 judge 的第一步不是写 prompt，而是<strong>把你想问的问题，往可判定的方向改写</strong>。"
          "同一个评测目标，可以被写成阶梯上的不同高度，而高度决定了这个 judge 能有多可靠。"),
        ASCII("""
   可判定性 ↑（越上面越可靠、越便宜、越不需要 LLM）
   ┌──────────────────────────────────────────────────────────────┐
   │ L4 程序可判定    "输出是不是合法 JSON / 有没有调用 tool X"      │  → 不该用 LLM（C66）
   ├──────────────────────────────────────────────────────────────┤
   │ L3 语义可判定    "有没有提到用户问的那个日期"                   │  → LLM 校验，一致率 >95%
   ├──────────────────────────────────────────────────────────────┤
   │ L2 规则可裁决    "是否符合这条 rubric：给出了至少两个反例"       │  → LLM rubric 项，一致率 85-95%
   ├──────────────────────────────────────────────────────────────┤
   │ L1 有序比较      "A 和 B 哪个更好"                              │  → pairwise，一致率 70-85%
   ├──────────────────────────────────────────────────────────────┤
   │ L0 绝对打分      "给这个回答打 1-5 分"                          │  → pointwise，最不可靠
   └──────────────────────────────────────────────────────────────┘
"""),
        DUAL(
            "这张梯子的实用价值在于：<strong>你手上那个「主观」的评测目标，"
            "往往可以被拆成一堆 L2/L3 的小问题</strong>，而不是被迫停在 L0。"
            "「这个客服回复好不好」这个 L0 问题，可以拆成："
            "有没有回答用户实际问的问题（L3）、有没有引用正确的政策条款（L3）、"
            "有没有承诺公司做不到的事（L2）、语气是否得体（L1，只能停在这一层）。"
            "<strong>拆完之后，四项里有三项都爬到了梯子上层。</strong>",
            "形式化地说，这是把一个<span class=\"term\">整体判断</span>（holistic judgment）"
            "分解为一组<span class=\"term\">分析性判断</span>（analytic judgments）。"
            "分解的收益有两层：<strong>① 每个子判断的方差更小</strong>"
            "（问题更窄 → judge 的不确定性更低）；"
            "<strong>② 子判断可以被独立验证与独立监控</strong>"
            "（哪一项在退化，一眼看得出来）。"
            "代价是引入了聚合权重这个新的自由度——它必须做敏感性分析（notebook 第 3 节）。",
        ),
        CALLOUT("intuition", "一条可以立刻执行的检查：<strong>把你的 judge prompt 里那个问题读出来，"
                             "问自己「两个认真的人类看同一份材料，会不会给出不同答案？」</strong>"
                             "如果会，说明这个问题还停在 L0/L1，值得再往上拆一层。"
                             "<em>停在 L0 有时是不可避免的（审美、语气），但绝不应该是默认选择。</em>"),
    ])),

    # ============================================================== 2
    ("pointwise", "pointwise 打分：分数分布压缩，以及三种缓解", "".join([
        P("pointwise（给单个回答打 1–5 分）是最常见也最容易出问题的用法。"
          "它的头号病症是<strong>分数分布压缩</strong>：让 judge 给一百个回答打分，"
          "你会发现七八十个都是 4 分。"),
        H3("压缩为什么发生"),
        UL([
            "<strong>没有锚点</strong>：judge 不知道「4 分」相对于什么。"
            "人类标注员在校准会上会看一批标好的例子，judge 通常什么都没看到。",
            "<strong>回避极端</strong>：模型倾向于避免 1 分和 5 分这种强判断（与 RLHF 训出的谨慎倾向一致）。",
            "<strong>量表本身太粗</strong>：五档要覆盖从「完全错误」到「无可挑剔」，中间的差异被压进同一档。",
        ]),
        P("压缩的直接后果是<strong>判别力归零</strong>：如果 80% 的样本都是 4 分，"
          "那么这个 judge 在这 80% 之间提供的信息是 0 bit。"
          "量化方式就是分数分布的<strong>熵</strong>——或者更直观的<strong>有效档位数</strong> "
          "$2^{H}$（$H$ 以 bit 为单位，与 notebook 里的实现一致）：五档量表如果有效档位数只有 1.6，说明你实际上在用一个「一档半」的量表。"),
        TABLE(["缓解手段", "怎么做", "效果", "代价"], [
            ["<strong>rubric 分解</strong>", "拆成 4–6 个二元/三元的子项，再加权聚合（第 4 节）", "<strong>最有效</strong>：每个子项的分布都不压缩，聚合后连续化", "要设计 rubric、要定权重"],
            ["<strong>few-shot 锚点</strong>", "给出每一档的 1–2 个标注样例", "有效，尤其是给出 1 分与 5 分的样例", "占上下文；锚点选得不好会引入新偏差"],
            ["<strong>更细的量表 + 强制分布</strong>", "改成 0–100 分，或要求「不许连续给同一分」", "有效但脆弱：模型会集中在 70/80/85 这些整十整五上", "分数的语义变得更模糊"],
            ["<strong>改用 pairwise</strong>", "直接换用法（第 3 节）", "彻底绕开该问题", "失去绝对分数，无法设阈值"],
        ]),
        CALLOUT("warn", "有一个看起来很聪明、实际上要小心的做法：<strong>用 token 概率做加权平均分</strong>"
                        "（如 G-Eval 的思路：取 1–5 这五个 token 的概率，算期望分）。"
                        "它确实能把整数分变成连续分、缓解压缩；"
                        "但它<strong>要求你能拿到 logprobs</strong>，而且<em>把「模型对某个分数的不确定性」"
                        "当成了「质量的中间态」</em>——这两件事并不等价。"
                        "作为缓解手段可以用，但不要把它当成校准过的概率（03 模块会讲怎么检验）。"),
    ])),

    # ============================================================== 3
    ("pairwise", "pairwise 比较：平局、置信度，以及「必须成对调用」", "".join([
        P("pairwise 把「打多少分」换成「谁更好」，绕开了绝对量表的全部问题，"
          "代价是引入了三个新的设计决策。"),
        H3("决策一：允不允许平局"),
        TABLE(["口径", "做法", "适用", "陷阱"], [
            ["<strong>强制二选一</strong>", "不给平局选项", "样本量小、需要最大分辨力时", "把「确实分不出」的样本变成了纯噪声，<strong>并可能放大位置偏差</strong>（分不出时就选默认位置）"],
            ["<strong>允许平局</strong>", "A / B / tie 三选一", "<strong>推荐默认</strong>", "平局比例过高（&gt; 40%）时分辨力下降，需要检查是不是任务本身没有区分度"],
            ["<strong>五档</strong>", "A 明显更好 / A 略好 / 平 / B 略好 / B 明显更好", "需要区分「差多少」时（如构造偏好数据）", "档位越多，一致性越低；<em>「略好」这一档的一致率通常很差</em>"],
        ]),
        H3("决策二：平局怎么进统计"),
        MATH(r"\text{win rate} = \frac{W + \tfrac{1}{2}T}{W + L + T} \quad\text{（推荐）}\qquad\text{vs}\qquad \frac{W}{W+L}\ \text{（丢弃平局）}"),
        P("两种口径会给出不同的数字，而且在平局率高时差别很大。"
          "<strong>推荐左边这种（平局算半分）</strong>——它与 Elo 以及 Arena 类榜单拟合 Bradley–Terry 时的"
          "实际做法一致（把平局记成 $y=0.5$，见 04 模块）。"
          "<em>严格来说 BT 本身没有平局项，处理平局的正统扩展是 Davidson 或 Rao–Kupper 模型；半分是一个好用的近似，但要在报告里写明。</em>"
          "而且不会因为「平局多」而人为放大胜负差距。"
          "<em>无论选哪种，都必须在报告里写明</em>。"),
        H3("决策三：必须成对调用（swap）"),
        CALLOUT("danger", "<strong>这是本节最重要的一条工程纪律：任何 pairwise judge 调用都必须做两次，"
                          "第二次交换 A/B 的位置。</strong>"
                          "理由在 02 模块会量化：位置偏差普遍存在且幅度可观。"
                          "两次结果不一致时，标准处理是<strong>记为平局</strong>（最保守）。"
                          "而 <strong>swap 一致率本身是一个必须报告的指标</strong>——"
                          "低于 80% 时，这个 judge 给出的胜率基本不可信。"),
        P("成对调用把成本翻倍。这是值得付的——但它也意味着你在设计评测规模时要把这一倍算进去"
          "（呼应 C66 模块 05 的成本模型）。"
          "<em>一个常见的折中：全量做单次调用，随机抽 10%–20% 做 swap 用于监控一致率</em>；"
          "但请注意这只适合<strong>监控</strong>，不适合<strong>出结论</strong>——"
          "出结论的那一次评测应该全量 swap。"),
    ])),

    # ============================================================== 4
    ("rubric", "rubric 设计：把主观质量拆成客观检查项", "".join([
        P("rubric 是这门课里性价比最高的一个工具。它把第 1 节的「往梯子上爬」变成了具体做法。"),
        H3("一个好 rubric 的五条标准"),
        OL([
            "<strong>每一项都能独立判定</strong>：判定第 3 项时不需要看第 1 项的结论。"
            "互相依赖的项会让 judge 的错误在项之间传播。",
            "<strong>每一项都是二元或三元的</strong>：「有 / 没有」「完全满足 / 部分满足 / 不满足」。"
            "<em>不要在 rubric 项内部再放一个 1–5 分量表</em>——那等于把压缩问题复制了 N 份。",
            "<strong>项与项之间尽量正交</strong>：「准确性」和「是否有事实错误」是同一项的两种说法，"
            "放两遍等于给它加了双倍权重（而且是隐式的）。",
            "<strong>覆盖失败模式而不是覆盖优点</strong>：从「这类回答通常怎么坏掉」倒推 rubric 项，"
            "比从「一个好回答应该有什么」正推更有效——<em>后者容易写出一堆无法区分的空泛项</em>。",
            "<strong>包含一条否决项</strong>：某些问题（编造引用、承诺做不到的事、违反安全策略）"
            "应该<strong>直接把总分归零</strong>，而不是按权重扣分。",
        ]),
        H3("聚合：权重从哪来，以及怎么检验"),
        P("rubric 分项之后必须聚合成一个数。权重是一个新引入的自由度，处理方式："),
        UL([
            "<strong>先试等权</strong>：等权是一个诚实的默认值，而且经常已经够用；",
            "<strong>用人类偏好拟合权重</strong>：如果有一批人类的整体偏好标注，"
            "可以把「rubric 分项 → 人类偏好」拟合成一个线性模型，权重就是回归系数。"
            "<em>这同时也检验了 rubric 的完备性——如果拟合得很差，说明你漏了某个维度</em>；",
            "<strong>无论怎么定，都要做敏感性分析</strong>：权重扰动 ±20%，结论会不会翻转"
            "（呼应 C65 模块 03 与 C66 模块 02 的做法）。<strong>一扰动就翻的结论，"
            "真正的分歧点在权重上而不在数据上。</strong>",
        ]),
        CALLOUT("intuition", "rubric 还有一个常被忽略的好处：<strong>它让 judge 的输出变得可解释、可申诉。</strong>"
                             "「B 得 3.4 分、A 得 3.1 分」没法讨论；"
                             "「B 在『引用了正确条款』这一项通过、A 没通过」可以被具体检查、被具体反驳。"
                             "<em>在需要跟业务方对齐评测口径的场景，这一点的价值往往超过分辨力本身。</em>"),
    ])),

    # ============================================================== 5
    ("reference", "参考答案：有 vs 无，以及参考答案本身的质量", "".join([
        P("给 judge 一份参考答案（reference / gold answer），是提升一致性最直接的手段之一——"
          "但它有三个必须知道的边界。"),
        TABLE(["设置", "judge 与人类的一致性", "适用场景", "风险"], [
            ["<strong>无参考</strong>", "最低", "开放式创作、无唯一解的任务", "judge 只能凭自己的先验判断，自偏好偏差最强"],
            ["<strong>有参考答案</strong>", "显著提升", "有标准答案或范例的任务", "<strong>judge 会奖励「像参考答案」而不是「同样正确」</strong>"],
            ["<strong>有参考 + 评分要点</strong>", "最高", "有明确得分点的任务（考试式）", "要点写得不全时，正确但不在要点里的答案被判错"],
        ]),
        CALLOUT("danger", "中间那一行的风险值得展开：<strong>给了参考答案之后，judge 的判断会向"
                          "「与参考答案的相似度」漂移</strong>，而相似度不等于正确性。"
                          "一个用完全不同但同样正确的方法解题的回答，可能因为「和参考不像」被判低分。"
                          "<em>这与 C66 模块 03 里「把轨迹相似度当主指标等于惩罚探索」是完全同构的错误。</em>"
                          "<strong>缓解办法：在 prompt 里显式写「参考答案只是一种正确解法，"
                          "其他正确解法应同等评分」，并在 rubric 里用「是否得出正确结论」"
                          "替代「是否与参考一致」。</strong>"),
        H3("参考答案自己有多好"),
        P("一个常被跳过的问题：<strong>你的参考答案是谁写的？</strong>"
          "如果它是某个模型生成后人工快速过了一遍的，那么它可能本身就带着那个模型的风格与错误，"
          "而 judge 会把这些一并当成标准。"
          "<em>检验方式很简单：把参考答案本身送进 judge 打分，看它得多少分。"
          "如果参考答案自己只能得 3.5 分，那么用它当标准是有问题的。</em>"),
    ])),

    # ============================================================== 6
    ("cot-structured", "CoT 与结构化输出：顺序、schema 与解析失败", "".join([
        H3("先理由后结论，还是先结论后理由"),
        P("<strong>先理由后结论</strong>几乎总是更好，原因不是「让模型思考」这种笼统说法，"
          "而是一个具体的机制：<strong>先输出的 token 会成为后面 token 的条件</strong>。"
          "如果先写 <code>\"verdict\": \"A\"</code>，后面的 reasoning 就变成了对既有结论的辩护，"
          "而不是导向结论的推理——这在结构上就无法起到纠错作用。"),
        CODE("""// ✓ 推荐：理由在前，结论在后
{"reasoning": "…", "verdict": "A"}

// ✗ 不推荐：结论在前，理由变成事后辩护
{"verdict": "A", "reasoning": "…"}

// ⚠ 注意：JSON 对象的字段顺序在生成时是有意义的（模型按序生成），
//    即使解析后字段顺序无关紧要。"""),
        H3("结构化输出的三个工程问题"),
        TABLE(["问题", "表现", "处理"], [
            ["<strong>解析失败</strong>", "返回的不是合法 JSON（多了解释文字、截断、markdown 代码块包裹）", "① 用原生结构化输出/工具调用约束；② 兜底做一次宽松解析（剥离代码块、找第一个 <code>{</code>）；③ <strong>重试，并记录重试率</strong>"],
            ["<strong>枚举越界</strong>", "verdict 返回了 <code>\"A is better\"</code> 而不是 <code>\"A\"</code>", "schema 里用 enum 约束；解析时做归一化映射"],
            ["<strong>截断</strong>", "reasoning 太长把 verdict 挤出了 max_tokens", "<strong>限制 reasoning 长度</strong>（「2–3 句」）并给足 max_tokens；这是「理由在前」的主要代价"],
        ]),
        CALLOUT("warn", "<strong>解析失败率必须被记录并报告。</strong>"
                        "原因不只是工程洁癖：<em>解析失败往往不是随机的</em>——"
                        "遇到难判的样本时，judge 更可能输出一堆解释而不是干净的 JSON。"
                        "如果你悄悄丢掉了这些样本，就引入了一个"
                        "<strong>与判断难度相关的选择偏倚</strong>，"
                        "剩下样本的一致率会虚高。正确做法是重试；重试仍失败的记为平局并<strong>计入分母</strong>。"),
    ])),

    # ============================================================== 7
    ("anchors", "few-shot 锚点与量表校准", "".join([
        P("如果最终还是要用 pointwise，那么锚点是把分布拉开的最有效手段。"
          "但锚点的选择本身是一个需要小心的设计。"),
        OL([
            "<strong>优先给两端</strong>：1 分和 5 分的样例比中间档更有价值——"
            "它们定义了量表的<em>范围</em>，而中间档会被内插出来。",
            "<strong>锚点必须来自与被评样本相同的分布</strong>：用一批「精心挑选的漂亮回答」当 5 分锚点，"
            "会让所有真实回答都显得平庸，整体分数下移（严厉度偏差）。",
            "<strong>锚点数量要少</strong>：每档 1–2 个。锚点占的上下文越多，"
            "被评内容在上下文里的相对权重越低；而且<em>过多的锚点会让 judge 去做「最近邻匹配」"
            "而不是按标准判断</em>。",
            "<strong>锚点要版本化</strong>：换了锚点就等于换了量表，历史分数不可直接比较——"
            "这与 C66 模块 05 的 运行指纹是同一件事。",
        ]),
        DUAL(
            "一个实用的自检：把锚点样例本身当作待评样本，送进 judge 跑一遍。"
            "<strong>如果 5 分锚点被打成 4 分，说明你的 prompt 与锚点之间存在矛盾</strong>，"
            "judge 并没有真的把锚点当作标准。这个自检便宜、快，而且经常能抓到问题。",
            "更一般地说，这是在检验量表的<span class=\"term\">内部一致性</span>："
            "锚点定义了从质量到分数的映射 $g$，judge 的实际打分函数是 $\\hat{g}$，"
            "自检就是在检查 $\\hat{g}(\\text{anchor}_k) = k$ 是否成立。"
            "<em>不成立说明 prompt 中的文字描述（「5 分表示……」）与锚点样例给出的隐式定义不一致，"
            "而模型通常更信样例</em>——所以修锚点比修文字描述更有效。",
        ),
    ])),

    # ============================================================== 8
    ("versioning", "judge prompt 的版本管理与回归", "".join([
        P("最后一节讲一件几乎所有团队都会在半年后后悔没做的事：<strong>judge prompt 的版本管理</strong>。"),
        P("judge prompt 是评测系统里<strong>唯一一个「随时会被人顺手改一下」的组件</strong>——"
          "有人觉得措辞不好改一句，有人加了一条 rubric，有人调了锚点。"
          "而每一次改动，都意味着<strong>之前所有用这个 judge 跑出来的分数，与之后的分数不可比较</strong>。"),
        TABLE(["要做的事", "怎么做", "不做的后果"], [
            ["<strong>prompt 哈希进结果</strong>", "把 judge prompt 模板（含锚点）的哈希写进每一条结果记录", "半年后没人说得清某个历史数字是哪版 prompt 跑的"],
            ["<strong>金标准回归集</strong>", "留一批人类标注好的样本，每次改 prompt 都重跑，看一致率变化", "改动是「改好了」还是「改坏了」全靠感觉"],
            ["<strong>双跑重叠期</strong>", "改版时新旧 judge 并行跑一段，量化两者的系统性差异", "指标曲线上出现一个无法解释的跳变"],
            ["<strong>锚点与 rubric 单独版本化</strong>", "它们改动频率最高，单独管理便于定位", "无法回答「这次分数变化是模型变了还是量表变了」"],
        ]),
        CALLOUT("danger", "最后强调一遍这条与 C66 模块 05 完全同构的纪律："
                          "<strong>judge prompt 是 harness 的一部分。</strong>"
                          "「我们的模型这个月分数涨了 3 个点」——"
                          "如果这个月里有人动过 judge prompt，这句话就是无意义的。"
                          "<em>把 prompt 哈希放进指纹，让「不可比较」变成机器可判定的一行 assert，"
                          "而不是靠人回忆。</em>"),
    ])),
    # ============================================================== 9
    ("multi-turn", "多轮对话与长文档：judge 设计的两个特例", "".join([
        P("前八节默认被评的是「一个 prompt 对应一个回答」。真实系统里有两类常见情形"
          "需要额外的设计决策，值得单独说清楚。"),
        H3("多轮对话：评哪一轮"),
        TABLE(["评法", "怎么做", "适用", "问题"], [
            ["<strong>只评最后一轮</strong>", "把前面的轮次当上下文，只判最后一个回复", "客服、问答类的单点质量监控", "看不出「前面几轮把对话带偏了」这类失败"],
            ["<strong>逐轮评再聚合</strong>", "每一轮独立打分，取平均或最小值", "需要定位「第几轮开始崩」时", "<strong>轮次之间不独立</strong>——第 3 轮的差，可能完全是第 2 轮造成的"],
            ["<strong>整段对话评一次</strong>", "把整个对话当一个整体判断", "评「这次会话有没有解决用户问题」", "长上下文里 judge 的注意力分布不均，<em>结尾的内容权重更高</em>"],
            ["<strong>目标达成检查</strong>", "不评「好不好」，只查「用户的目标达成了没有」", "<strong>推荐</strong>：任务型对话", "需要为每个会话标注目标——但这正是 C66 终态判分的思路"],
        ]),
        CALLOUT("intuition", "多轮场景里最容易被忽略的一条：<strong>逐轮打分的平均值，"
                             "会系统性地低估「前期埋雷、后期爆炸」这类失败</strong>——"
                             "因为前面几轮单看都还不错。"
                             "<em>如果你关心的是「这次会话成功了吗」，"
                             "就应该用目标达成检查（一个可判定的 L3 问题）而不是逐轮打分（一堆 L0 问题）。</em>"
                             "这又是第 1 节那把梯子的应用。"),
        H3("长文档：位置效应与分块"),
        P("当被评内容很长（几千到几万 token）时，会出现两个 pointwise/pairwise 都要面对的问题："),
        UL([
            "<strong>位置效应</strong>：长上下文中间部分的内容更容易被忽略。"
            "这意味着<em>同样的错误，出现在文档中间比出现在开头或结尾更不容易被 judge 发现</em>——"
            "这是一种与内容无关的系统偏差，可以用「把同一个错误插到不同位置」的探针测出来（模块 02 的范式）；",
            "<strong>整体判断被稀释</strong>：一份 8000 字的报告里有一个致命的事实错误，"
            "整体打分可能只掉 0.5 分。<strong>解法是 rubric 化 + 否决项</strong>——"
            "「有没有事实错误」作为一个独立的二元项，触发即否决，而不是混进整体印象里。",
        ]),
        H3("一个两类情形共用的原则：先问「失败长什么样」"),
        P("多轮与长文档看起来是两个问题，但它们的正确解法来自同一句话："
          "<strong>先列出这类内容<em>典型的失败形态</em>，再据此设计 judge，"
          "而不是先写一个「请评价这段内容的质量」的通用 prompt。</strong>"),
        P("多轮对话的典型失败是「前期把用户的需求理解偏了，后面几轮都在解决错误的问题」；"
          "长文档的典型失败是「整体结构不错，但中间藏着一个致命的事实错误」。"
          "<em>这两种失败，通用的「整体质量」prompt 都抓不到</em>——"
          "前者需要「目标达成检查」，后者需要「事实错误」作为否决项。"
          "<strong>而一旦你列出了失败形态，rubric 项其实是被这份清单直接决定的</strong>"
          "（呼应第 4 节的第 4 条：覆盖失败模式而不是覆盖优点）。"),
        P("<strong>分块评测</strong>是一个常见但需要小心的做法：把长文档切成块分别评再聚合。"
          "它能缓解位置效应，但引入了新问题——<em>跨块的一致性问题（前后矛盾）在分块评测里完全看不见</em>。"
          "实践中的折中是<strong>「分块评局部质量 + 整体评一致性」两条线分开跑</strong>，"
          "各自报告，不要合成一个数。"),
    ])),
]

NB = [
    md("""# 01 · Judge 设计（分布压缩 / 平局口径 / rubric 分解 / 参考答案 / 结构化输出 / 锚点）

目标：把「怎么写一个 judge」从调 prompt 的手艺，变成几个**可以测量、可以对比**的设计决策。

本 notebook 你会亲手实现：
1. **分数分布压缩的度量** —— 熵与有效档位数，量化「五档量表实际只用了一档半」
2. **三种缓解手段的对比** —— rubric 分解 / 锚点 / 更细量表，谁真的把判别力救回来了
3. **平局的三种统计口径** —— 同一批判断，三个不同的胜率
4. **rubric 分解 vs 整体分** —— 分辨力对比 + 权重敏感性 + 否决项
5. **参考答案的双刃效果** —— 一致性提升，但「像参考」会被误当成「正确」
6. **结构化输出的解析失败率** —— 为什么悄悄丢掉解析失败的样本会让一致率虚高

> 心智模型：**设计 judge 的第一步不是写 prompt，是把问题往可判定的方向改写。
> 能拆成 rubric 就不要打整体分，能比较就不要打绝对分。**"""),

    md("""## 1 · 分数分布压缩：量化「五档量表实际用了几档」"""),

    code("""import math, json, re, hashlib
from collections import Counter, defaultdict
import numpy as np

def score_entropy(scores, scale=5):
    \"\"\"分数分布的熵（bit）。\"\"\"
    cnt = Counter(np.asarray(scores).astype(int).tolist())
    n = sum(cnt.values())
    return -sum((c / n) * math.log2(c / n) for c in cnt.values() if c > 0)

def effective_levels(scores, scale=5):
    \"\"\"有效档位数 = 2^H。五档量表的上限是 5；实际常常只有 1.5-2.5。\"\"\"
    return 2 ** score_entropy(scores, scale)

rng = np.random.default_rng(0)
N = 2000
q = rng.uniform(0, 1, N)                       # 真实质量

def judge_pointwise(q, noise=0.6, compression=0.55, severity=0.0, scale=5, rng=None):
    rng = rng or np.random.default_rng(0)
    v = q + rng.normal(0, noise, size=np.shape(q)) - severity
    v = 0.5 + compression * (v - 0.5)
    return np.clip(np.round(v * (scale - 1) + 1), 1, scale)

s_compressed = judge_pointwise(q, noise=0.25, compression=0.30, rng=np.random.default_rng(1))
print('分数分布:', dict(sorted(Counter(s_compressed.astype(int).tolist()).items())))
print(f'熵 {score_entropy(s_compressed):.3f} bit | 有效档位数 {effective_levels(s_compressed):.2f} / 5')
assert effective_levels(s_compressed) < 2.5
print('\\n✅ 五档量表实际只用到了不到 2.5 档——')
print('   落在同一档里的样本之间，这个 judge 提供的信息是 0 bit。')"""),

    code("""# 判别力：分数与真实质量的相关系数（判别力的直接度量）
def discrimination(scores, q_true):
    s = np.asarray(scores, dtype=float)
    t = np.asarray(q_true, dtype=float)
    sc, tc = s - s.mean(), t - t.mean()
    d = math.sqrt(float((sc ** 2).sum()) * float((tc ** 2).sum()))
    return float((sc * tc).sum() / d) if d else 0.0

VARIANTS = {
    '基线（压缩严重）': dict(noise=0.25, compression=0.30, scale=5),
    '加锚点（拉开分布）': dict(noise=0.25, compression=0.85, scale=5),
    '0-100 细量表':      dict(noise=0.25, compression=0.55, scale=101),
    '降噪（更好的 prompt）': dict(noise=0.12, compression=0.55, scale=5),
}
print(f"{'变体':<22}{'有效档位':>10}{'与真值相关':>12}")
for name, kw in VARIANTS.items():
    sc = judge_pointwise(q, rng=np.random.default_rng(5), **kw)
    lv = effective_levels(sc, kw['scale'])
    print(f'{name:<22}{lv:>10.2f}{discrimination(sc, q):>12.3f}')

base = judge_pointwise(q, noise=0.25, compression=0.30, scale=5, rng=np.random.default_rng(5))
anchored = judge_pointwise(q, noise=0.25, compression=0.85, scale=5, rng=np.random.default_rng(5))
assert discrimination(anchored, q) > discrimination(base, q)
print('\\n✅ 注意 0-100 细量表这一行：有效档位数暴涨，但与真值的相关只涨了一点点——')
print('   **把量表变细并不会凭空创造信息**，它只是把同样的噪声铺得更开。')
print('   真正有效的是「拉开分布」（锚点）和「降噪」（更好的 prompt / rubric）。')"""),

    md("""## 2 · rubric 分解：为什么它比整体分更有判别力

把一个整体判断拆成 K 个独立的二元判断，再平均。每个子判断有各自的噪声，
但**独立噪声在平均后按 $1/\\sqrt{K}$ 衰减**——这就是 rubric 的全部数学。"""),

    code("""def holistic_judge(q, noise=0.25, compression=0.30, rng=None):
    return judge_pointwise(q, noise=noise, compression=compression, scale=5, rng=rng)

def rubric_judge(q, k_items=5, item_noise=0.35, weights=None, rng=None):
    \"\"\"K 个独立的二元 rubric 项：第 j 项通过的真实概率与 q 相关，judge 各自带噪声地判定。\"\"\"
    rng = rng or np.random.default_rng(0)
    q = np.asarray(q, dtype=float)
    w = np.ones(k_items) if weights is None else np.asarray(weights, dtype=float)
    w = w / w.sum()
    total = np.zeros_like(q)
    for j in range(k_items):
        thresh = (j + 0.5) / k_items                     # 每项的难度不同
        perceived = q + rng.normal(0, item_noise, size=q.shape)
        total += w[j] * (perceived > thresh).astype(float)
    return total

h = holistic_judge(q, rng=np.random.default_rng(9))
r = rubric_judge(q, k_items=5, rng=np.random.default_rng(9))
print(f'整体分     与真值相关 {discrimination(h, q):.3f} | 有效档位 {effective_levels(h):.2f}')
print(f'rubric(5项) 与真值相关 {discrimination(r, q):.3f} | 取值个数 {len(set(np.round(r,6).tolist()))}')
assert discrimination(r, q) > discrimination(h, q)

print(f"\\n{'rubric 项数':>12}{'与真值相关':>12}")
for k in [1, 3, 5, 8, 12]:
    rr = rubric_judge(q, k_items=k, rng=np.random.default_rng(9))
    print(f'{k:>12}{discrimination(rr, q):>12.3f}')
print('\\n✅ 项数越多相关越高，但收益递减（$1/\\\\sqrt{K}$）。')
print('   实践中 4-6 项就能拿到大部分收益——再往上加，边际收益抵不过设计与调用成本。')"""),

    code("""# 权重敏感性：结论会不会被权重扰动翻转
def weight_sensitivity(qA, qB, k_items=5, delta=0.2, n=300, seed=0):
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        w = np.ones(k_items) * (1 + rng.uniform(-delta, delta, k_items))
        a = rubric_judge(qA, k_items, weights=w, rng=np.random.default_rng(1)).mean()
        b = rubric_judge(qB, k_items, weights=w, rng=np.random.default_rng(2)).mean()
        if a > b:
            wins += 1
    return wins / n

rng2 = np.random.default_rng(3)
qA = rng2.uniform(0, 1, 400) * 0.0 + rng2.uniform(0.30, 0.75, 400)
qB = rng2.uniform(0.28, 0.73, 400)
frac = weight_sensitivity(qA, qB)
print(f'权重扰动 ±20% 后，A 胜出的比例: {frac:.1%}')
assert 0.0 <= frac <= 1.0
verdict = '稳健' if frac > 0.9 or frac < 0.1 else '结论由权重决定，不该写成「A 更好」'
print(f'判读: {verdict}')
print('\\n✅ 敏感性分析是 rubric 聚合的必备步骤——')
print('   胜出比例接近 50% 时，真正的分歧点在权重上而不在数据上。')"""),

    code("""# 否决项：某些问题应当直接归零，而不是按权重扣分
def rubric_with_veto(rubric_score, veto_flags):
    \"\"\"veto_flags 为 True 的样本（编造引用 / 承诺做不到的事 / 违反安全策略）直接归零。\"\"\"
    return np.where(np.asarray(veto_flags, dtype=bool), 0.0, np.asarray(rubric_score, dtype=float))

rng3 = np.random.default_rng(4)
veto = rng3.random(len(q)) < 0.06          # 6% 的样本触发否决项
r_veto = rubric_with_veto(r, veto)
print(f'无否决项 平均分 {r.mean():.3f} | 有否决项 平均分 {r_veto.mean():.3f}')
print(f'被否决样本在无否决口径下的平均分: {r[veto].mean():.3f}（看起来还不错）')
assert r_veto.mean() < r.mean()
assert r[veto].mean() > 0.3
print('\\n✅ 关键在最后一行：被否决的样本在加权口径下平均分并不低——')
print('   一个「编造了引用但其他方面都写得很好」的回答，按权重扣分后仍然是高分。')
print('   **这类问题必须用否决项处理，不能靠权重。**')"""),

    md("""## 3 · 平局的三种统计口径：同一批判断，三个胜率"""),

    code("""def win_rate(w, l, t, mode='half'):
    total = w + l + t
    if mode == 'half':      # 平局算半分（推荐；这是 Elo/Arena 拟合 BT 时的惯例）
        return (w + 0.5 * t) / total if total else float('nan')
    if mode == 'drop':      # 丢弃平局
        return w / (w + l) if (w + l) else float('nan')
    if mode == 'loss':      # 平局算输（偶尔在"必须严格更好"的场景用）
        return w / total if total else float('nan')
    raise ValueError(mode)

CASES = [('平局少', 120, 100, 20), ('平局中等', 100, 80, 120), ('平局很多', 60, 40, 200)]
print(f"{'场景':<12}{'W':>5}{'L':>5}{'T':>5}{'half':>10}{'drop':>10}{'loss':>10}")
for name, w, l, t in CASES:
    print(f'{name:<12}{w:>5}{l:>5}{t:>5}'
          f'{win_rate(w,l,t,"half"):>10.1%}{win_rate(w,l,t,"drop"):>10.1%}{win_rate(w,l,t,"loss"):>10.1%}')

h1 = win_rate(60, 40, 200, 'half')
d1 = win_rate(60, 40, 200, 'drop')
assert abs(d1 - h1) > 0.05
print(f'\\n平局率 {200/300:.0%} 时，两种口径差 {abs(d1-h1):.1%}——')
print('✅ 「胜率 57%」这句话在没写明平局口径时是不完整的。')
print('   推荐用 half（与 BT 模型一致，且不会因平局多而人为放大差距）。')"""),

    md("""## 4 · 参考答案的双刃效果

参考答案提升一致性，但会让 judge 奖励「像参考」而不是「同样正确」。
构造一批「正确但与参考风格不同」的回答，看它们被怎么对待。"""),

    code("""rng = np.random.default_rng(12)
M = 1500
correct = (rng.random(M) < 0.5).astype(float)          # 是否真的正确
similarity = rng.uniform(0, 1, M)                       # 与参考答案的表面相似度（与正确性独立）

def judge_with_reference(correct, similarity, w_correct=1.0, w_sim=0.0, noise=0.35, seed=0):
    rng = np.random.default_rng(seed)
    v = w_correct * correct + w_sim * similarity + rng.normal(0, noise, size=correct.shape)
    return (v > (w_correct + w_sim) / 2).astype(int)

no_ref = judge_with_reference(correct, similarity, w_correct=1.0, w_sim=0.0, noise=0.55, seed=1)
with_ref = judge_with_reference(correct, similarity, w_correct=1.0, w_sim=0.0, noise=0.28, seed=2)
with_ref_leak = judge_with_reference(correct, similarity, w_correct=1.0, w_sim=0.6, noise=0.28, seed=3)

for name, pred in [('无参考', no_ref), ('有参考（理想）', with_ref), ('有参考（相似度泄漏）', with_ref_leak)]:
    acc = float((pred == correct).mean())
    # 「正确但不像参考」的子群上，被判对的比例
    sub = (correct == 1) & (similarity < 0.3)
    recall_unlike = float(pred[sub].mean())
    print(f'{name:<22} 总一致率 {acc:.1%} | 「正确但不像参考」被判对的比例 {recall_unlike:.1%}')

acc_leak = float((with_ref_leak == correct).mean())
acc_ref = float((with_ref == correct).mean())
sub = (correct == 1) & (similarity < 0.3)
assert with_ref_leak[sub].mean() < with_ref[sub].mean()
print('\\n✅ 「相似度泄漏」这一行是关键：总一致率看起来还行，')
print('   但「用不同方法做对了」的回答被系统性地判错——')
print('   这与 C66-03「把轨迹相似度当主指标等于惩罚探索」是完全同构的错误。')
print('   缓解：prompt 里显式写「参考只是一种正确解法」+ rubric 用「结论是否正确」而非「是否与参考一致」。')"""),

    md("""## 5 · 结构化输出：解析失败率与选择偏倚

关键洞察：**解析失败不是随机的**——难判的样本更容易输出一堆解释而不是干净 JSON。
悄悄丢掉它们，剩下样本的一致率会虚高。"""),

    code("""def parse_verdict(raw):
    \"\"\"宽松解析：剥离代码块、找第一个 JSON 对象、归一化 enum。\"\"\"
    if raw is None:
        return None
    txt = re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.M).strip()
    m = re.search(r'\\{.*\\}', txt, flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    v = str(obj.get('verdict', '')).strip().lower()
    for key, out in [('tie', 'tie'), ('a', 'A'), ('b', 'B')]:
        if v.startswith(key):
            return out
    return None

SAMPLES = [
    '{"reasoning": "A is more accurate.", "verdict": "A"}',
    '```json\\n{"reasoning": "…", "verdict": "B"}\\n```',
    'Sure! Here is my analysis:\\n{"reasoning": "…", "verdict": "tie"}',
    '{"reasoning": "A is better because it',                 # 截断
    'I think A is better, but it depends.',                  # 根本没给 JSON
    '{"reasoning": "…", "verdict": "A is better"}',          # 枚举越界（宽松解析可救）
]
for s_ in SAMPLES:
    print(f'{parse_verdict(s_)!s:<6} <- {s_[:52]!r}')
assert parse_verdict(SAMPLES[0]) == 'A'
assert parse_verdict(SAMPLES[1]) == 'B'
assert parse_verdict(SAMPLES[2]) == 'tie'
assert parse_verdict(SAMPLES[3]) is None and parse_verdict(SAMPLES[4]) is None
assert parse_verdict(SAMPLES[5]) == 'A'
print('\\n✅ 宽松解析能救回代码块包裹与枚举越界，但救不了截断与完全没给 JSON。')"""),

    code("""# 解析失败与判断难度相关 → 悄悄丢弃会让一致率虚高
rng = np.random.default_rng(17)
K = 3000
difficulty = rng.uniform(0, 1, K)                     # 越大越难判
truth_v = rng.integers(0, 2, K)
# 难样本更容易判错
pred = np.where(rng.random(K) < 0.10 + 0.35 * difficulty, 1 - truth_v, truth_v)
# 也更容易解析失败
parse_ok = rng.random(K) > (0.01 + 0.20 * difficulty)

acc_all = float((pred == truth_v).mean())
acc_parsed = float((pred[parse_ok] == truth_v[parse_ok]).mean())
acc_with_tie = float(np.where(parse_ok, pred == truth_v, 0.5).mean())   # 失败记平局计入分母
print(f'解析成功率            {parse_ok.mean():.1%}')
print(f'全体一致率（真值）     {acc_all:.1%}')
print(f'只统计解析成功的样本   {acc_parsed:.1%}   ← 虚高')
print(f'失败记平局并计入分母   {acc_with_tie:.1%}')
assert acc_parsed > acc_all
print('\\n✅ 悄悄丢掉解析失败的样本，一致率虚高了几个点。')
print('   正确做法：重试；重试仍失败的记为平局并**计入分母**，同时把解析失败率写进报告。')"""),

    md("""## ✏️ 练习 1：有效档位数与「该不该换量表」

实现 `scale_utilization(scores, scale)`：返回 `有效档位数 / 名义档位数`。
用它判断：一个 0–100 的量表如果分数全部落在 70/75/80/85 四个值上，利用率是多少。"""),

    code("""def scale_utilization(scores, scale):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
uniform5 = np.array([1, 2, 3, 4, 5] * 40)
assert abs(scale_utilization(uniform5, 5) - 1.0) < 1e-9
const = np.array([4] * 200)
assert abs(scale_utilization(const, 5)) < 1e-9 or scale_utilization(const, 5) == 0.2
lumpy100 = np.array([70, 75, 80, 85] * 50)
u = scale_utilization(lumpy100, 101)
print(f'0-100 量表但只用了 4 个值 → 利用率 {u:.2%}')
assert u < 0.05
print(f'五档均匀分布 → 利用率 {scale_utilization(uniform5, 5):.0%}')
print('✅ 练习 1 通过：把量表变细而分数仍然扎堆，利用率会低到离谱——')
print('   这个数字是「该不该换设计」的直接信号。')"""),

    md("""## ✏️ 练习 2：rubric 项数的边际收益

实现 `marginal_gain(k, item_noise=0.35, n=2000, seed=0)`：
返回从 `k` 项加到 `k+1` 项时，与真值相关系数的增量。
用它找出「加到第几项之后收益就不值得了」。"""),

    code("""def marginal_gain(k, item_noise=0.35, n=2000, seed=0):
    # TODO：用上面已定义的 rubric_judge 与 discrimination
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
g1 = marginal_gain(1)
g8 = marginal_gain(8)
assert g1 > g8, '边际收益必须递减'
print(f"{'k→k+1':>8}{'相关系数增量':>14}")
for k in [1, 2, 3, 5, 8, 12]:
    print(f'{f"{k}→{k+1}":>8}{marginal_gain(k):>14.4f}')
print('✅ 练习 2 通过：从 1 项加到 2 项收益巨大，从 8 项加到 9 项几乎没有——')
print('   4-6 项是性价比的甜点区。')"""),

    md("""## ✏️ 练习 3：平局口径的转换

实现 `convert_win_rate(wr_drop, tie_rate)`：已知「丢弃平局口径」下的胜率 `wr_drop`
与平局比例 `tie_rate`，反算「平局算半分」口径下的胜率。

推导：设总数为 1，则 $W+L = 1-t$，$W = (1-t)\\cdot wr_{drop}$，
所以 $wr_{half} = W + t/2 = (1-t)\\cdot wr_{drop} + t/2$。"""),

    code("""def convert_win_rate(wr_drop, tie_rate):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert abs(convert_win_rate(0.60, 0.0) - 0.60) < 1e-12
assert abs(convert_win_rate(0.60, 1.0) - 0.50) < 1e-12       # 全是平局 → 必然 50%
w, l, t = 60, 40, 200
assert abs(convert_win_rate(win_rate(w, l, t, 'drop'), t / (w + l + t))
           - win_rate(w, l, t, 'half')) < 1e-9
for tr in [0.0, 0.2, 0.5, 0.8]:
    print(f'丢弃口径 65% + 平局率 {tr:.0%} → half 口径 {convert_win_rate(0.65, tr):.1%}')
print('✅ 练习 3 通过：平局率越高，两个口径差得越远——')
print('   平局会把胜率往 50% 拉，这正是它应该做的（分不出就别装作分得出）。')"""),

    md("""## ✏️ 练习 4：解析失败的正确记账

实现 `agreement_with_failures(pred, truth, parse_ok, policy)`，
`policy ∈ {'drop', 'tie', 'retry'}`：
- `drop`：只统计解析成功的样本（会虚高）
- `tie`：失败记平局，按 0.5 分计入分母
- `retry`：失败样本按 `retry_success=0.7` 的概率重试成功（成功后沿用 `pred`），
  仍失败的按 `tie` 处理

返回一致率。`retry` 模式用固定 seed 保证可复现。"""),

    code("""def agreement_with_failures(pred, truth, parse_ok, policy, retry_success=0.7, seed=0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
a_drop = agreement_with_failures(pred, truth_v, parse_ok, 'drop')
a_tie = agreement_with_failures(pred, truth_v, parse_ok, 'tie')
a_retry = agreement_with_failures(pred, truth_v, parse_ok, 'retry', seed=1)
print(f'drop  {a_drop:.1%}  ← 虚高（悄悄丢掉了难样本）')
print(f'tie   {a_tie:.1%}  ← 最保守')
print(f'retry {a_retry:.1%}  ← 推荐：先重试，仍失败才记平局')
assert a_drop > a_tie
assert a_tie <= a_retry <= a_drop + 1e-9
print('✅ 练习 4 通过：三种记账口径的排序永远是 tie ≤ retry ≤ drop。')
print('   报告里必须写明用的是哪种，并且把解析失败率一起报出来。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def scale_utilization(scores, scale):
    if scale <= 1:
        return 0.0
    return effective_levels(scores, scale) / scale"""),

    code("""# 练习 2 参考答案
def marginal_gain(k, item_noise=0.35, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    qq = rng.uniform(0, 1, n)
    a = discrimination(rubric_judge(qq, k_items=k, item_noise=item_noise,
                                    rng=np.random.default_rng(seed + 1)), qq)
    b = discrimination(rubric_judge(qq, k_items=k + 1, item_noise=item_noise,
                                    rng=np.random.default_rng(seed + 1)), qq)
    return b - a"""),

    code("""# 练习 3 参考答案
def convert_win_rate(wr_drop, tie_rate):
    return (1 - tie_rate) * wr_drop + tie_rate / 2"""),

    code("""# 练习 4 参考答案
def agreement_with_failures(pred, truth, parse_ok, policy, retry_success=0.7, seed=0):
    pred = np.asarray(pred)
    truth = np.asarray(truth)
    ok = np.asarray(parse_ok, dtype=bool)
    hit = (pred == truth).astype(float)
    if policy == 'drop':
        return float(hit[ok].mean())
    if policy == 'tie':
        return float(np.where(ok, hit, 0.5).mean())
    if policy == 'retry':
        rng = np.random.default_rng(seed)
        recovered = (~ok) & (rng.random(len(pred)) < retry_success)
        final_ok = ok | recovered
        return float(np.where(final_ok, hit, 0.5).mean())
    raise ValueError(policy)"""),

    md("""---
## 🧪 真实工程胶囊：可直接用的 judge 模板与版本管理"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. rubric 型 judge 的完整模板（推荐作为默认起点）
# ══════════════════════════════════════════════════════════════════
RUBRIC_JUDGE = "\n".join([
    "Evaluate the response against the rubric below.",
    "",
    "<request>{request}</request>",
    "<response>{response}</response>",
    '<reference note="ONE valid solution. Other correct approaches score equally.">{reference}</reference>',
    "",
    "For EACH item, output pass/fail independently. Do not let one item influence another.",
    "",
    "RUBRIC",
    "  R1 answers_question   The response addresses what was actually asked.",
    "  R2 factually_correct  No incorrect factual claims.",
    "  R3 cites_policy       Cites the applicable policy clause when one exists.",
    "  R4 no_overpromise     Does not commit to anything outside stated capabilities.",
    "  R5 actionable         The user can act on it without asking a follow-up.",
    "",
    "VETO (if ANY is true, total score is 0 regardless of the rubric)",
    "  V1 fabricated_citation  Cites a source/clause that does not exist.",
    "  V2 unsafe               Violates the safety policy.",
    "",
    "Return JSON only, reasoning BEFORE verdicts:",
    '{{"reasoning": "<2-3 sentences>",',
    '  "rubric": {{"R1": true, "R2": true, "R3": false, "R4": true, "R5": true}},',
    '  "veto":   {{"V1": false, "V2": false}}}}',
])

def score_from_rubric(obj, weights=None):
    if any(obj["veto"].values()):
        return 0.0                                   # 否决项：直接归零，不按权重扣
    items = obj["rubric"]
    w = weights or {k: 1.0 for k in items}
    tot = sum(w.values())
    return sum(w[k] for k, v in items.items() if v) / tot

# ══════════════════════════════════════════════════════════════════
# B. judge prompt 的版本指纹（判分器也是 harness 的一部分）
# ══════════════════════════════════════════════════════════════════
import hashlib, json
def judge_fingerprint(template, anchors, model_id, temperature):
    payload = json.dumps({"template": template, "anchors": anchors,
                          "model": model_id, "temperature": temperature},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:8]
# 把它写进每一条 judge 结果。改了 prompt、改了锚点、换了 judge 模型 → 指纹变 →
# 与历史分数不可直接比较（C68 的 CI 门禁里这是一行 assert）。

# ══════════════════════════════════════════════════════════════════
# C. 结构化输出：优先用原生约束，宽松解析只作兜底
# ══════════════════════════════════════════════════════════════════
# Anthropic / OpenAI 都支持用工具调用或 response_format 强制 schema。
# 无论用哪种，都要记录：parse_ok、retry_count、raw_output（失败样本必须留原文，
# 否则你永远查不出它为什么失败）。

# ══════════════════════════════════════════════════════════════════
# D. 锚点自检（便宜、快、经常抓到问题）
# ══════════════════════════════════════════════════════════════════
# 把每个锚点样例本身当作待评样本送进 judge：
#   5 分锚点被打成 4 分 → prompt 文字描述与锚点样例互相矛盾，模型更信样例
#   → 改锚点比改文字描述有效
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 可判定性阶梯 | 设计 judge 的第一步是把问题往可判定方向改写 | 任何新 judge |
| 分布压缩 | 五档量表常常只有效用到一档半；把量表变细不创造信息 | pointwise |
| rubric 分解 | 独立噪声按 1/sqrt(K) 衰减；4–6 项是甜点区 | 提升判别力 |
| 否决项 | 编造引用这类问题必须归零，不能按权重扣分 | rubric 设计 |
| 平局口径 | 平局算半分（Arena 拟合 BT 的惯例），且必须写明 | pairwise 报告 |
| 参考答案 | 提升一致性，但会奖励「像参考」而非「同样正确」 | 有标准答案的任务 |
| 解析失败 | 失败与难度相关，悄悄丢弃会让一致率虚高 | 工程记账 |
| prompt 版本化 | judge prompt 是 harness 的一部分 | 长期可比性 |

下一模块：**02 · Judge 偏差与去偏**——位置、长度、自偏好、风格四个偏差的量化探针，
以及把它们从读数里减掉的具体方法。""")
]
