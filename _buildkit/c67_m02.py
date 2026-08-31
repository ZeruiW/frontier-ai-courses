# -*- coding: utf-8 -*-
"""C67 模块 02 · Judge 偏差与去偏。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（judge 设计）；"
                 "线性回归的最小二乘解在 notebook 里从零写，不需要 sklearn"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_judge_bias.ipynb'
                       '（位置偏差探针与 swap 去偏 / 长度控制回归 LC 版胜率 / 自偏好探针 / '
                       '风格偏差与去风格化对照 / 多 judge 集成：独立偏差 vs 共同偏差 / '
                       '可识别性演示：长度与质量真相关时去偏会矫枉过正）'),
    ("核心参考", "Zheng et al., <em>MT-Bench &amp; Chatbot Arena</em>（NeurIPS 2023，位置/冗长/自增强偏差）· "
                 "Dubois et al., <em>Length-Controlled AlpacaEval</em>（2024，长度控制回归）· "
                 "Panickssery et al., <em>LLM Evaluators Recognize and Favor Their Own Generations</em>（2024）· "
                 "Chiang &amp; Lee, <em>Can Large Language Models Be an Alternative to Human Evaluations?</em>（ACL 2023）· "
                 "本课程 C10 模块 01/02（标注噪声与一致性）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("landscape", "四大偏差全景：机制、探针、去偏手段", "".join([
        P("模块 00 把 judge 的读数写成 $\\hat{q} = q + f(\\cdot) + \\varepsilon$。"
          "这一节把 $f$ 拆开：它主要由四个分量构成，每一个都有<strong>明确的探针</strong>"
          "（怎么把它量出来）和<strong>明确的去偏手段</strong>（怎么把它减掉）。"),
        TABLE(["偏差", "机制（为什么会有）", "探针（怎么量）", "去偏手段", "残留问题"], [
            ["<strong>位置偏差</strong><br>position", "自回归生成 + 提示结构，使得某个位置的候选被系统性偏好", "<strong>swap 一致性</strong>：交换 A/B 位置再判一次，看翻转比例", "<strong>两个位置各判一次取平均</strong>（成本翻倍）", "翻转样本怎么处理（记平局最保守）"],
            ["<strong>长度/冗长偏差</strong><br>verbosity", "更长的回答提供更多「看起来相关」的内容，也更像训练数据里的高质量回答", "控制质量后，看长度对胜率的边际效应（回归系数）", "<strong>长度控制回归</strong>：把长度作为协变量回归掉", "长度与质量<em>真的</em>相关时会矫枉过正（第 8 节）"],
            ["<strong>自偏好</strong><br>self-preference", "judge 对自己的生成分布有更高的似然，可能把「熟悉」误读为「好」", "同一批内容分别由同族/异族模型改写后再评", "<strong>换异族 judge</strong>；多 judge 集成", "「异族」的边界不清晰（同一批数据训出来的模型可能共享偏好）"],
            ["<strong>风格与格式偏差</strong><br>style", "markdown 标题、要点列表、自信语气被系统性奖励", "把同一内容重排成不同格式，看分数变化", "<strong>去风格化</strong>（统一格式后再评）或在 prompt 里显式禁止", "格式在某些任务上<em>确实是</em>质量的一部分"],
        ]),
        CALLOUT("intuition", "这张表最重要的是第三列。<strong>「我知道 judge 有偏差」和「我量过这个 judge 的偏差有多大」，"
                             "在工程上是两件完全不同的事。</strong>"
                             "前者只能让你在报告里加一句免责声明，后者能让你把偏差从数字里减掉、"
                             "或者至少判断出「这个 3 个点的差距是不是完全由长度差异造成的」。"
                             "<em>本模块的每一个探针都只需要几十到几百次额外的 judge 调用</em>——"
                             "相对于评测本身的成本，这是很便宜的。"),
        P("除了这四个主要分量，还有几个二级偏差值得知道名字："
          "<strong>bandwagon</strong>（告诉 judge「多数人认为 A 更好」会改变它的判断）、"
          "<strong>authority</strong>（虚构的引用与权威署名会提高分数）、"
          "<strong>身份偏差</strong>（提到作者身份会改变判断）。"
          "它们的共同点是：<em>都可以用「加/不加某个无关信息，看分数变不变」这个统一的探针范式来测</em>。"),
    ])),

    # ============================================================== 2
    ("position", "位置偏差：最容易测、也最容易修的一个", "".join([
        P("位置偏差是四个里唯一有<strong>干净修法</strong>的：因为「A 在前」和「B 在前」是一个"
          "完全对称的操作，把两种顺序各跑一次取平均，位置项就被消掉了。"),
        MATH(r"\hat{P}(A \succ B) = \tfrac{1}{2}\left[\Pr(\text{judge 说 A} \mid A \text{ 在前}) + \Pr(\text{judge 说 A} \mid A \text{ 在后})\right]"),
        H3("swap 一致率：一个必须报告的数字"),
        TABLE(["swap 一致率", "含义", "该怎么办"], [
            ["&gt; 90%", "位置偏差很小，judge 判断稳定", "正常使用；仍建议做 swap 平均"],
            ["80% – 90%", "存在可观的位置偏差或判断噪声", "<strong>必须做 swap 平均</strong>；不一致样本记平局"],
            ["70% – 80%", "偏差严重，或任务本身区分度低", "先检查是不是任务太难分——如果是，加大平局比例反而更诚实"],
            ["&lt; 70%", "<strong>这个 judge 的胜率数字不可用</strong>", "回到模块 01 重新设计（rubric 化、加参考答案、换更强的 judge 模型）"],
        ]),
        DUAL(
            "一个容易混淆的点：<strong>swap 不一致 ≠ 位置偏差</strong>。"
            "不一致有两个来源：位置偏差（系统性地偏向某个位置）和随机噪声（judge 就是不稳定）。"
            "<strong>区分方式很简单：看不一致样本里，「两次都说前面那个赢」占多少。</strong>"
            "如果不一致主要表现为「总是选第一个」，那是位置偏差；"
            "如果不一致是随机分布的，那是噪声。<em>两者的修法完全不同</em>——"
            "前者靠 swap 平均，后者靠多次采样或换更强的 judge。",
            "形式化：设 $p_1 = \\Pr(\\text{选第一个} \\mid \\text{顺序 AB})$、"
            "$p_2 = \\Pr(\\text{选第一个} \\mid \\text{顺序 BA})$。"
            "<strong>位置偏差的强度是 $\\frac{p_1 + p_2}{2} - \\frac{1}{2}$</strong>"
            "（两种顺序下「选第一个」的平均倾向偏离 0.5 的程度），"
            "而这个量与 A、B 的真实质量差无关——这正是它可以被消掉的原因。"
            "<em>噪声则表现为不一致率高但上述偏差量接近 0。</em>",
        ),
        CALLOUT("warn", "工程上还有一个细节容易忘：<strong>swap 之后要把 verdict 翻译回来</strong>。"
                        "第二次调用时 <code>\"A\"</code> 指的是原来的 B。"
                        "这个翻译如果写错，你会得到一个看起来「一致率极低」的假象——"
                        "<em>而且这个 bug 极其常见，因为它不会报错，只会让数字变难看。</em>"
                        "自检方法：拿一批「A 明显优于 B」的样本跑一遍，"
                        "如果 swap 一致率异常地低，先怀疑翻译写反了。"),
    ])),

    # ============================================================== 3
    ("length", "长度偏差与长度控制回归", "".join([
        P("长度偏差是四个里<strong>影响最大、修起来最微妙</strong>的一个。"
          "它的麻烦之处在于：<strong>长度与质量之间存在真实的相关性</strong>——"
          "一个完整回答确实通常比一个敷衍的短回答长。所以不能简单地「惩罚长回答」。"),
        H3("探针：控制质量后看长度的边际效应"),
        P("正确的探针必须<strong>控制住质量</strong>。三种做法，成本递增、可信度也递增："),
        OL([
            "<strong>回归法</strong>：拿现有的 judge 结果，把「胜负」对「质量代理变量 + 长度差」做回归，"
            "看长度差的系数。便宜，但需要一个质量代理变量（例如人类标注的子集）。",
            "<strong>改写法</strong>：把同一个回答扩写/精简成不同长度但<em>信息量相同</em>的版本，"
            "送 judge 打分，看分数随长度的变化。中等成本，最直观。",
            "<strong>配对法</strong>：找出「人类判为平局」的成对样本，看 judge 在这些样本上是否系统性偏向长的那个。"
            "需要人类标注，但结论最硬。",
        ]),
        H3("去偏：长度控制回归"),
        P("这是 AlpacaEval 的 LC（length-controlled）版本采用的思路，也是目前最实用的去偏方法。核心是一个逻辑回归："),
        MATH(r"\operatorname{logit}\Pr(A \succ B) = \theta_m + \gamma \cdot \Delta_{\text{len}} + \beta^\top x"),
        P("其中 $\\theta_m$ 是模型 $m$ 的<strong>质量参数</strong>（我们真正想要的量）、"
          "$\\Delta_{\\text{len}}$ 是两个回答的长度差（通常取 token 数之差或其某种标准化形式）、"
          "$\\gamma$ 是长度偏差的强度。"
          "<strong>拟合完之后，把 $\\Delta_{\\text{len}}$ 设为 0 再算胜率，就得到「长度控制后的胜率」</strong>。"),
        CALLOUT("intuition", "为什么这个做法比「直接惩罚长回答」好？因为它<strong>估计</strong>了长度效应而不是<strong>假设</strong>了它。"
                             "$\\gamma$ 是从数据里拟合出来的：如果这个 judge 其实没有长度偏差，"
                             "$\\gamma$ 会接近 0，去偏后的胜率与去偏前几乎一样——<em>方法自动退化成不做任何事</em>。"
                             "<strong>这是一个好的去偏方法应有的性质：没有偏差时不引入伤害。</strong>"),
        P("需要注意的实现细节：<strong>长度差要做某种归一化</strong>（例如除以两者长度之和，"
          "或者取对数长度之差），否则一条 5000 token 的回答会在回归里占据不成比例的杠杆。"
          "<em>另外，$\\gamma$ 应当<strong>按 judge 分别估计</strong>——不同的 judge 模型长度偏差差别很大，"
          "共用一个 $\\gamma$ 是没有依据的。</em>"),
    ])),

    # ============================================================== 4
    ("self-pref", "自偏好：最难证明、也最难修的一个", "".join([
        P("自偏好（self-preference / self-enhancement）指的是：<strong>judge 在评价自己（或同族模型）"
          "生成的内容时，倾向于给更高的分。</strong>"),
        H3("为什么难证明"),
        P("困难在于<strong>混杂</strong>：如果 judge 模型 M 评价 M 的输出得分更高，"
          "有两种同样合理的解释——① M 偏爱自己的输出（偏差）；② M 的输出确实更好（事实）。"
          "<strong>要分开这两者，必须控制住质量。</strong>"),
        TABLE(["实验设计", "怎么做", "能证明什么", "局限"], [
            ["<strong>交叉评审</strong>", "让 M1、M2 互评对方与自己的输出", "如果每个模型都把自己排第一，那至少有一个是偏差", "不能定量给出偏差幅度"],
            ["<strong>人类锚定</strong>", "取一批人类判为等质量的成对样本，看 judge 在其中是否偏向同族输出", "<strong>能定量</strong>", "需要人类标注"],
            ["<strong>风格迁移</strong>", "把 M2 的内容用 M1 改写成 M1 的风格（保持信息不变），看分数是否上升", "能分离「内容偏好」与「风格偏好」", "改写可能无意中改变了内容质量"],
            ["<strong>识别度关联</strong>", "先问 judge「这是不是你写的」，再看它给的分与识别度的相关", "揭示机制（自我识别 → 偏好）", "识别本身可能不准"],
        ]),
        CALLOUT("danger", "自偏好在一个具体场景下危害最大：<strong>用模型 M 做 judge 来评测 M 的新版本</strong>。"
                          "这是最常见的内部评测配置，而它恰好踩中了自偏好——"
                          "<em>新版本相对旧版本的「提升」，可能有一部分只是「新版本的输出更像 judge 自己」</em>。"
                          "<strong>最低限度的缓解：用一个异族 judge 做交叉验证，"
                          "至少确认两个 judge 给出的排序一致。</strong>"),
        H3("缓解手段"),
        UL([
            "<strong>换异族 judge</strong>——最直接，但要注意「异族」的边界并不清晰："
            "在相似数据上训练、用相似方法对齐的模型，可能共享同样的风格偏好。",
            "<strong>多 judge 集成</strong>——如果各 judge 的自偏好指向不同方向，集成会部分抵消（第 7 节）。",
            "<strong>rubric 化</strong>（模块 01）——把整体判断拆成客观检查项，"
            "自偏好在「有没有引用正确条款」这种项上很难发挥作用。<em>这是被低估的一条</em>。",
            "<strong>去风格化</strong>——如果自偏好主要通过风格起作用，统一格式能消掉一部分。",
        ]),
    ])),

    # ============================================================== 5
    ("style", "风格与格式偏差：以及「格式什么时候真的算质量」", "".join([
        P("markdown 标题、要点列表、加粗、开头的一句总结、自信而不含糊的语气——"
          "这些都被观察到能<strong>系统性地提高 judge 给的分</strong>，即使内容不变。"),
        H3("探针：同内容、不同格式"),
        CODE("""原始回答（纯文本）:
  要解决这个问题，先检查配置文件里的超时设置，然后确认网络策略允许出站请求，
  最后看一下日志里有没有 429 错误。

重排后（结构化）:
  ## 排查步骤
  1. **检查超时设置** — 配置文件中的 timeout 值
  2. **确认网络策略** — 是否允许出站请求
  3. **查看日志** — 搜索 429 错误

  信息量完全相同。如果 judge 给第二个更高的分，差值就是格式偏差。"""),
        DUAL(
            "关键问题来了：<strong>格式偏差到底算不算偏差？</strong>"
            "如果最终用户读的就是这段文本，那么「更好读」<em>确实是</em>质量的一部分，"
            "judge 给它更高分是对的。但如果这段文本要被程序解析、"
            "或者你评测的是「事实准确性」，那么格式就是纯粹的噪声。"
            "<strong>所以答案取决于你的评测目标——而这必须被显式声明，不能靠默认。</strong>",
            "用测量学的语言：格式是不是<span class=\"term\">构念的一部分</span>"
            "（part of the construct）还是<span class=\"term\">构念无关方差</span>"
            "（construct-irrelevant variance），取决于构念的定义。"
            "<em>同一个 judge 读数，在「整体有用性」这个构念下格式是信号，"
            "在「事实准确性」这个构念下格式是噪声。</em>"
            "<strong>这也是为什么模块 01 主张 rubric 化：把「格式清晰」单列成一项，"
            "它就从一个隐藏的混杂变量变成了一个可以被显式加权（甚至权重设为 0）的维度。</strong>",
        ),
        CALLOUT("warn", "一个实际会发生的坏结果：如果你用一个有格式偏差的 judge 做训练信号或选型标准，"
                        "<strong>模型会学会「把简单答案包装成有标题有列表的长文」</strong>——"
                        "在需要简洁回答的场景，这是纯粹的退化。"
                        "<em>而且这个退化在 judge 的分数上表现为「提升」</em>，"
                        "所以只看分数你永远发现不了。<strong>唯一的发现方式是监控输出的长度分布与格式分布</strong>"
                        "——这条监控在 C68 模块 05 里是一条标准的漂移告警。"),
    ])),

    # ============================================================== 6
    ("probe-pattern", "统一的探针范式：加一个无关变量，看读数变不变", "".join([
        P("前面五节的探针看起来各不相同，其实是同一个模式的实例。把它抽象出来，"
          "你就能给任何新怀疑的偏差<strong>自己设计探针</strong>。"),
        ASCII("""
   探针范式（反事实对照）
   ┌─────────────────────────────────────────────────────────────┐
   │ 1. 选一个你怀疑的表面属性 X（位置/长度/风格/署名/引用/…）      │
   │ 2. 构造成对样本：内容与质量完全相同，只有 X 不同               │
   │ 3. 送同一个 judge 打分                                        │
   │ 4. 分数差的均值 = X 的偏差幅度；差的方差 = 这个探针的噪声      │
   │ 5. 用配对检验（同一内容成对）判断偏差是否显著                  │
   └─────────────────────────────────────────────────────────────┘
   关键在第 2 步：「质量完全相同」这件事必须是**构造出来的**，
   不能靠"我觉得这两个差不多"。最可靠的构造方式是「同一份内容的变体」。
"""),
        TABLE(["怀疑的属性 X", "怎么构造只差 X 的成对样本", "注意"], [
            ["位置", "交换 A/B 顺序", "最干净——交换是严格保内容的"],
            ["长度", "扩写/精简到不同长度但信息量相同", "很难做到「信息量严格相同」，需要人工核对"],
            ["格式", "把同一内容重排成纯文本 / markdown", "相对容易保内容"],
            ["署名 / 身份", "在 prompt 里加上「这是 X 写的」", "干净，但要注意 judge 可能拒绝回答"],
            ["虚构引用", "加一条格式正确但不存在的引用", "<strong>这条同时也是安全探针</strong>——judge 被虚构权威提分，说明它没在核实"],
            ["自信语气", "把「可能是……」改成「就是……」", "保内容但改变认知标记，是校准相关的重要探针"],
        ]),
        CALLOUT("intuition", "第 5 步用<strong>配对检验</strong>而不是独立检验，理由与 C66 模块 04 完全相同："
                             "成对样本共享内容，内容质量这个最大的方差源被直接消掉。"
                             "<em>这意味着探针需要的样本量比你想象的少得多</em>——"
                             "几十到一两百对通常就足以把偏差幅度定位到有用的精度。"),
    ])),

    # ============================================================== 7
    ("ensemble", "多 judge 集成：什么时候真的有用", "".join([
        P("「用三个 judge 投票」是一个被广泛推荐的做法。它有效，但<strong>只对某一类误差有效</strong>，"
          "而人们常常把它当成万能解药。"),
        TABLE(["误差类型", "集成有没有用", "原因"], [
            ["<strong>随机噪声</strong>", "✅ 非常有用", "独立噪声按 $1/\\sqrt{K}$ 衰减，这是集成的标准收益"],
            ["<strong>各 judge 方向不同的偏差</strong>", "✅ 有用", "方向不同的系统项在平均后部分抵消"],
            ["<strong>各 judge 共有的偏差</strong>", "❌ <strong>完全无用</strong>", "所有 judge 都偏向长回答时，平均之后还是偏向长回答——而且置信区间会变窄，让你<em>更自信地相信一个偏了的结论</em>"],
        ]),
        CALLOUT("danger", "第三行是这一节的全部重点。<strong>长度偏差、格式偏差在几乎所有主流 judge 模型上都存在，"
                          "且方向一致。</strong>对这类偏差，多 judge 集成<em>不但没用，还有害</em>——"
                          "它把随机噪声压下去，使得残留的系统偏差在统计上显得更「显著」。"
                          "<strong>集成只能治噪声，不能治共有的偏差。</strong>"),
        H3("那什么时候值得做集成"),
        UL([
            "<strong>judge 之间确实异质</strong>——不同厂商、不同规模、不同对齐方式。"
            "<em>先用第 6 节的探针测一下它们的偏差方向，方向一致的 judge 集成起来没有额外收益</em>；",
            "<strong>你已经把共有偏差处理掉了</strong>——先做 swap 平均、先做长度控制，剩下的才交给集成；",
            "<strong>预算允许</strong>——集成的成本是线性的，而收益是 $1/\\sqrt{K}$ 的。"
            "<em>三个 judge 通常是性价比拐点</em>，五个以上很少划算。",
        ]),
        P("最后一个实用提示：<strong>集成的聚合方式要与用法匹配</strong>。"
          "pairwise 场景用多数投票（并把「无多数」记为平局）；"
          "pointwise 场景用均值（并<strong>报告 judge 间的标准差</strong>——"
          "这个标准差本身就是一个有用的「这个样本难判」信号，可以拿去做人工复核的分诊）。"),
    ])),

    # ============================================================== 8
    ("identifiability", "去偏的极限：当长度与质量真的相关时", "".join([
        P("最后一节讲一个必须诚实面对的问题：<strong>去偏不是免费的，它有可能矫枉过正。</strong>"),
        P("长度控制回归的隐含假设是：<strong>在控制住模型身份之后，长度差与质量差无关</strong>。"
          "但这个假设并不总成立——如果模型 A 真的因为「回答更完整」而更长，"
          "那么把长度效应全部回归掉，就<em>把 A 的一部分真实优势也一起减掉了</em>。"),
        MATH(r"\Delta_{\text{len}} = \underbrace{\delta_{\text{quality}}}_{\text{因为更完整而更长}} + \underbrace{\delta_{\text{padding}}}_{\text{纯粹的注水}}"),
        DUAL(
            "问题在于：<strong>这两项在观测数据里是无法分离的</strong>——"
            "你看到的只有总长度差。这是一个典型的<em>不可识别</em>问题："
            "同一份数据可以由「A 更完整」和「A 更爱注水」两种假设同样好地解释。"
            "<strong>所以长度控制后的胜率不是「真值」，而是「假设长度全是注水时的下界」。</strong>",
            "要打破不可识别，必须引入<span class=\"term\">额外的识别假设</span>或额外的数据。"
            "实践中有三条路：<strong>① 用人类标注的子集去估计 $\\delta_{\\text{quality}}$</strong>"
            "（人类判定「这段额外内容有没有增加信息」）；"
            "<strong>② 构造反事实样本</strong>（第 6 节的改写法：造出「同信息量不同长度」的对照，"
            "此时 $\\delta_{\\text{quality}} = 0$ 被构造性地保证了）；"
            "<strong>③ 报告一个区间而不是一个点</strong>——"
            "「原始胜率 62%，长度控制后 54%，真值在两者之间」。"
            "<em>第三条最诚实，也最容易执行。</em>",
        ),
        CALLOUT("intuition", "把这条推广成本模块的总结论：<strong>去偏的正确输出不是一个更准的数字，"
                             "而是一个更窄的区间加上一句关于假设的说明。</strong>"
                             "「LC 胜率 54%」如果不附带「原始 62%」和「差值 8 个点全部归因于长度」这个假设，"
                             "它给读者的确定感就超过了它实际拥有的信息。"),
        H3("本模块的报告规范"),
        CODE("""judge:              claude-sonnet-5, prompt e3a1f9c, temp 0.0
swap consistency:   0.883        ← < 0.80 时胜率不可用
position bias:      +0.041       ← (两种顺序下"选第一个"的平均倾向) - 0.5
win rate (raw):     62.1%  [58.4%, 65.7%]
win rate (LC):      54.3%  [50.6%, 58.0%]   ← 长度控制后
  └─ gamma (长度系数):  0.31 per unit normalized length diff
  └─ 假设: 长度差全部归因于注水；真值在 raw 与 LC 之间
style probe:        +0.18 分 (markdown 重排 vs 纯文本, 同内容, n=120, 配对 p<0.001)
self-pref probe:    +0.09 分 (同族 vs 异族改写, n=150)
judge ensemble:     未使用（三个候选 judge 的长度偏差方向一致，集成无额外收益）"""),
    ])),
    # ============================================================== 9
    ("bias-budget", "偏差预算：一份评测该花多少钱在探针上", "".join([
        P("本模块给了五个探针。它们都很便宜，但加起来也是成本。"
          "这一节回答一个很实际的问题：<strong>该按什么顺序做、做到什么程度就可以停。</strong>"),
        TABLE(["优先级", "探针", "额外调用量", "什么时候可以跳过"], [
            ["<strong>P0 必做</strong>", "swap 一致性", "×2（全量）", "<strong>永远不能跳过</strong>——它同时是去偏手段和质量指标"],
            ["<strong>P0 必做</strong>", "长度偏差（回归法）", "<strong>0</strong>（用已有结果拟合）", "永远不能跳过：零边际成本，只需要日志里有长度字段"],
            ["<strong>P1 强烈推荐</strong>", "风格探针（同内容不同格式）", "~200 对", "被评内容的格式高度统一时可跳过"],
            ["<strong>P1 强烈推荐</strong>", "自偏好探针", "~300 对", "judge 与被评模型确定异族时可跳过"],
            ["<strong>P2 按需</strong>", "虚构引用 / 权威 / 从众探针", "各 ~150 对", "非事实密集任务可跳过"],
            ["<strong>P2 按需</strong>", "多 judge 集成", "×K（全量）", "<strong>先确认候选 judge 的偏差方向不同</strong>，方向一致就别做"],
        ]),
        CALLOUT("intuition", "注意第二行：<strong>长度偏差的回归法探针边际成本是零</strong>——"
                             "它只需要你在日志里记了 <code>a_len_tokens</code> 与 <code>b_len_tokens</code>，"
                             "然后对已有的判断结果拟合一个逻辑回归。"
                             "<em>这可能是整个评测流程里性价比最高的一件事："
                             "几行代码，换来「这 6 个点的差距有多少来自长度」这个关键答案。</em>"
                             "<strong>而它的前提只是「日志里有那两个字段」——"
                             "这又一次说明 schema 是事前决定（呼应 C66-03）。</strong>"),
        H3("什么时候可以停"),
        P("一个可操作的停止规则，按结论的用途分："),
        UL([
            "<strong>只是内部看看趋势</strong>：做完 P0 两项即可，把 raw 与 LC 两个数一起看；",
            "<strong>要写进报告或做选型决策</strong>：P0 + P1 全做，"
            "并在报告里给出 raw–LC 区间与两个探针的幅度；",
            "<strong>judge 要被用作训练信号</strong>：<strong>全部做完，而且要定期重做</strong>——"
            "因为模块 05 会讲到，训练信号的误差会被优化过程主动放大，"
            "<em>你在这里量到的每一个偏差，都会在训练后变成一种 reward hacking 形态</em>。",
        ]),
        P("最后一条值得展开一句：<strong>偏差探针的结果，是可以直接预测 hack 方向的</strong>。"
          "如果你量到长度系数 $\\gamma = 0.8$，那么用这个 judge 训出来的模型<em>一定</em>会把输出推长——"
          "这不需要等实验结果，可以提前布置监控。模块 05 第 3 节会把这条对应关系列成一张完整的表。"),
    ])),
]

NB = [
    md("""# 02 · Judge 偏差与去偏（位置 / 长度 / 自偏好 / 风格 · 探针与去偏）

目标：把「我知道 judge 有偏差」升级成「我量过这个 judge 的偏差有多大，并把它从数字里减掉了」。

本 notebook 你会亲手实现：
1. **位置偏差探针与 swap 去偏** —— 区分「位置偏差」与「纯噪声」，两者修法完全不同
2. **长度控制回归** —— 纯 numpy 的逻辑回归，拟合长度系数 γ 并算出 LC 胜率
3. **自偏好探针** —— 在人类判为等质量的样本上，量同族偏好的幅度
4. **风格偏差与去风格化** —— 同内容不同格式的配对检验
5. **多 judge 集成** —— 独立偏差 vs 共有偏差，后者集成完全无用
6. **可识别性演示** —— 长度与质量真相关时，去偏会把真实优势一起减掉

> 心智模型：**去偏的正确输出不是一个更准的数字，而是一个更窄的区间 + 一句关于假设的说明。**"""),

    md("""## 1 · 位置偏差探针：区分「偏差」与「噪声」"""),

    code("""import math, json
from collections import Counter, defaultdict
import numpy as np

class BiasedJudge:
    \"\"\"带四个显式偏差旋钮的 judge。所有偏差都作用在「感知质量」上。\"\"\"

    def __init__(self, b_pos=0.0, b_len=0.0, b_self=0.0, b_style=0.0,
                 noise=0.25, seed=0):
        self.b_pos, self.b_len = b_pos, b_len
        self.b_self, self.b_style = b_self, b_style
        self.noise = noise
        self.rng = np.random.default_rng(seed)

    def _v(self, q, is_first, z_len, is_self, is_styled):
        return (q + self.b_pos * is_first + self.b_len * z_len
                + self.b_self * is_self + self.b_style * is_styled
                + self.rng.normal(0, self.noise, size=np.shape(q)))

    def compare(self, qa, qb, a_first=True, z_len_a=0.0, z_len_b=0.0,
                self_a=0, self_b=0, style_a=0, style_b=0):
        \"\"\"返回 1 = 判 A 赢。a_first 决定谁被放在提示的第一位。\"\"\"
        va = self._v(np.asarray(qa, float), 1 if a_first else 0, z_len_a, self_a, style_a)
        vb = self._v(np.asarray(qb, float), 0 if a_first else 1, z_len_b, self_b, style_b)
        return (va > vb).astype(int)


def swap_probe(judge, qa, qb):
    \"\"\"两种顺序各判一次。返回 (一致率, 位置偏差强度, swap 平均后的 A 胜率)。
    位置偏差强度 = 两种顺序下「选第一个」的平均倾向 - 0.5。\"\"\"
    v_ab = judge.compare(qa, qb, a_first=True)      # A 在前，1 表示选了第一个
    v_ba = judge.compare(qa, qb, a_first=False)     # A 在后，1 表示选了第二个
    consistent = float((v_ab == v_ba).mean())
    pick_first = float((v_ab.mean() + (1 - v_ba).mean()) / 2)
    win_a = float((v_ab.mean() + v_ba.mean()) / 2)  # swap 平均：位置项被消掉
    return consistent, pick_first - 0.5, win_a


rng = np.random.default_rng(0)
N = 4000
qa = rng.uniform(0, 1, N)
qb = rng.uniform(0, 1, N)
truth_win = float((qa > qb).mean())

CASES = [
    ('无偏差、低噪声', BiasedJudge(noise=0.10, seed=1)),
    ('纯噪声（无位置偏差）', BiasedJudge(noise=0.45, seed=2)),
    ('纯位置偏差（低噪声）', BiasedJudge(b_pos=0.25, noise=0.10, seed=3)),
    ('位置偏差 + 噪声', BiasedJudge(b_pos=0.25, noise=0.45, seed=4)),
]
print(f"{'judge':<24}{'swap 一致率':>12}{'位置偏差':>10}{'swap 平均胜率':>14}")
for name, j in CASES:
    c, bias, wa = swap_probe(j, qa, qb)
    print(f'{name:<24}{c:>12.1%}{bias:>+10.3f}{wa:>14.1%}')
print(f'{"真值":<24}{"":>12}{0.0:>+10.3f}{truth_win:>14.1%}')

c_noise, bias_noise, _ = swap_probe(BiasedJudge(noise=0.45, seed=2), qa, qb)
c_pos, bias_pos, _ = swap_probe(BiasedJudge(b_pos=0.25, noise=0.10, seed=3), qa, qb)
assert abs(bias_noise) < 0.05, '纯噪声不应产生位置偏差'
assert bias_pos > 0.05, '纯位置偏差必须被探针检出'
assert c_noise < 0.95 and c_pos < 0.95, '两者都会降低 swap 一致率'
print('\\n✅ 关键结论：**两个 judge 的 swap 一致率都不高，但成因完全不同**——')
print('   噪声型：一致率低但位置偏差 ≈ 0 → 修法是多次采样或换更强的 judge')
print('   偏差型：一致率低且位置偏差显著 → 修法是 swap 平均（本函数已经做了）')"""),

    code("""# swap 平均确实把位置偏差消掉了：与只做单向调用对比
j = BiasedJudge(b_pos=0.30, noise=0.15, seed=7)
one_way = float(j.compare(qa, qb, a_first=True).mean())
_, _, swapped = swap_probe(BiasedJudge(b_pos=0.30, noise=0.15, seed=7), qa, qb)
print(f'真值 A 胜率        {truth_win:.1%}')
print(f'单向调用（A 在前） {one_way:.1%}   偏离 {one_way - truth_win:+.1%}')
print(f'swap 平均          {swapped:.1%}   偏离 {swapped - truth_win:+.1%}')
assert abs(swapped - truth_win) < abs(one_way - truth_win)
print('\\n✅ swap 平均把位置偏差从数字里消掉了——代价是调用次数翻倍。')
print('   这是四个偏差里唯一有干净修法的一个，因为「交换顺序」是严格保内容的操作。')"""),

    md("""## 2 · 长度控制回归：拟合 γ，算出 LC 胜率

$$\\operatorname{logit}\\Pr(A \\succ B) = \\theta + \\gamma\\cdot\\Delta_{\\text{len}}$$

拟合完把 $\\Delta_{\\text{len}}$ 设为 0，就得到长度控制后的胜率。纯 numpy 的梯度下降。"""),

    code("""def fit_logistic(X, y, lr=0.5, iters=3000, l2=1e-4):
    \"\"\"纯 numpy 逻辑回归（含截距）。X: (n, d)，y: (n,) 取值 0/1。返回系数向量（末位是截距）。\"\"\"
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    Xb = np.hstack([X, np.ones((len(X), 1))])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        z = Xb @ w
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        grad = Xb.T @ (p - y) / len(y) + l2 * w
        w -= lr * grad
    return w

def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

# 造数据：A 比 B 真实质量高 delta_q，同时 A 平均更长
rng = np.random.default_rng(11)
M = 6000
delta_q = 0.06
base = rng.uniform(0, 0.9, M)
qA, qB = base + delta_q, base
len_A = rng.normal(600, 200, M)
len_B = rng.normal(380, 160, M)
dlen = (len_A - len_B) / (len_A + len_B)             # 归一化长度差（关键：不要用原始差值）

judge_len = BiasedJudge(b_len=0.0, noise=0.30, seed=13)
# 长度偏差直接体现在感知质量上：A 每单位归一化长度差 +0.9
va = qA + 0.9 * dlen + rng.normal(0, 0.30, M)
vb = qB + rng.normal(0, 0.30, M)
y = (va > vb).astype(int)

raw_win = float(y.mean())
w = fit_logistic(dlen.reshape(-1, 1), y)
gamma, theta = float(w[0]), float(w[1])
lc_win = float(sigmoid(theta))                       # 把 dlen 置 0
print(f'原始胜率 (raw)       {raw_win:.1%}')
print(f'长度系数 gamma       {gamma:+.3f}')
print(f'长度控制后胜率 (LC)  {lc_win:.1%}')
assert gamma > 0.5, '长度偏差必须被拟合出来'
assert lc_win < raw_win, '控制掉长度优势后，胜率应当下降'
print('\\n✅ 8 个点里有一大半来自「A 写得更长」，而不是「A 写得更好」。')"""),

    code("""# 好的去偏方法应有的性质：没有偏差时不引入伤害
rng = np.random.default_rng(21)
va2 = qA + 0.0 * dlen + rng.normal(0, 0.30, M)       # 这次 judge 没有长度偏差
vb2 = qB + rng.normal(0, 0.30, M)
y2 = (va2 > vb2).astype(int)
w2 = fit_logistic(dlen.reshape(-1, 1), y2)
raw2, lc2 = float(y2.mean()), float(sigmoid(w2[1]))
print(f'无长度偏差的 judge: gamma = {w2[0]:+.3f} | raw {raw2:.1%} → LC {lc2:.1%}（几乎不变）')
assert abs(float(w2[0])) < 0.25
assert abs(lc2 - raw2) < 0.03
print('\\n✅ γ 被拟合成接近 0，去偏后的胜率与去偏前几乎一样——')
print('   **方法自动退化成「什么都不做」，这是一个好的去偏方法应有的性质。**')
print('   对比「直接惩罚长回答」那种做法：它在没有偏差时会主动制造偏差。')"""),

    code("""# 为什么必须归一化长度差：用原始 token 差会让长回答占据不成比例的杠杆
raw_dlen = (len_A - len_B)
w_raw = fit_logistic(raw_dlen.reshape(-1, 1), y)
lc_raw_scale = float(sigmoid(w_raw[1]))
print(f'归一化长度差:  gamma={gamma:+.4f}      LC 胜率 {lc_win:.1%}')
print(f'原始 token 差: gamma={float(w_raw[0]):+.6f}  LC 胜率 {lc_raw_scale:.1%}')
print(f'\\n两种做法的 LC 胜率差 {abs(lc_win - lc_raw_scale):.1%}')
print('✅ 归一化不是洁癖：原始差值的量纲让极端长的样本获得极大杠杆，')
print('   系数估计对少数长样本非常敏感。推荐用 (a-b)/(a+b) 或 log 长度之差。')"""),

    md("""## 3 · 自偏好探针：在「人类判为等质量」的样本上量"""),

    code("""# 设计：取一批真实质量严格相等的成对样本（构造性地保证），
# 其中一个由 judge 的同族模型生成。任何系统性偏向都是自偏好。
rng = np.random.default_rng(31)
K = 3000
q_equal = rng.uniform(0.2, 0.8, K)                  # 两边质量完全相同
is_self_a = np.ones(K)                              # A 由同族模型生成
is_self_b = np.zeros(K)

def self_pref_probe(b_self, noise=0.25, seed=0):
    j = BiasedJudge(b_self=b_self, noise=noise, seed=seed)
    v_ab = j.compare(q_equal, q_equal, a_first=True, self_a=is_self_a, self_b=is_self_b)
    v_ba = j.compare(q_equal, q_equal, a_first=False, self_a=is_self_a, self_b=is_self_b)
    return float((v_ab.mean() + v_ba.mean()) / 2)   # swap 平均，排除位置偏差干扰

print(f"{'自偏好强度 b_self':>18}{'同族模型的胜率':>16}{'偏离 50%':>12}")
for b in [0.0, 0.05, 0.10, 0.20]:
    wr = self_pref_probe(b, seed=int(b * 100) + 1)
    print(f'{b:>18.2f}{wr:>16.1%}{wr-0.5:>+12.1%}')

wr0 = self_pref_probe(0.0, seed=1)
wr2 = self_pref_probe(0.20, seed=21)
assert abs(wr0 - 0.5) < 0.03, '无自偏好时应当是 50/50'
assert wr2 > 0.55, '自偏好必须被检出'
print('\\n✅ 探针的关键在于「质量构造性地相等」——')
print('   在真实数据上做这个探针，必须用人类判为平局的子集，否则无法区分')
print('   「偏爱自己」与「自己确实更好」这两种解释。')"""),

    code("""# 最危险的配置：用模型 M 做 judge 来评测 M 的新旧版本
rng = np.random.default_rng(37)
n = 4000
q_old = rng.uniform(0, 1, n)
true_gain = 0.02                                     # 新版本真实只强 2 个点
q_new = q_old + true_gain

def measured_gain(b_self_new, seed):
    j = BiasedJudge(b_self=b_self_new, noise=0.25, seed=seed)
    # 新版本的输出更像 judge 自己（judge 就是新版本的同族）
    v1 = j.compare(q_new, q_old, a_first=True, self_a=np.ones(n), self_b=np.zeros(n))
    v2 = j.compare(q_new, q_old, a_first=False, self_a=np.ones(n), self_b=np.zeros(n))
    return float((v1.mean() + v2.mean()) / 2)

wr_no_self = measured_gain(0.0, 41)
wr_self = measured_gain(0.12, 42)
print(f'真实质量提升             {true_gain:+.1%}')
print(f'异族 judge 测出的胜率     {wr_no_self:.1%}')
print(f'同族 judge 测出的胜率     {wr_self:.1%}  ← 虚高 {wr_self - wr_no_self:+.1%}')
assert wr_self > wr_no_self + 0.03
print('\\n✅ 这正是最常见的内部评测配置——用自家模型评自家新版本。')
print('   缓解的最低限度：用一个异族 judge 交叉验证，至少确认排序一致。')"""),

    md("""## 4 · 风格偏差：同内容、不同格式的配对检验"""),

    code("""def paired_t(diff):
    \"\"\"配对样本的 t 统计量与近似双侧 p 值（正态近似）。\"\"\"
    d = np.asarray(diff, dtype=float)
    t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)) + 1e-12)
    p = math.erfc(abs(t) / math.sqrt(2))
    return float(t), float(p)

rng = np.random.default_rng(51)
n_pairs = 400
q_same = rng.uniform(0.2, 0.8, n_pairs)             # 同一份内容，质量当然相同

def style_probe(b_style, seed):
    j = BiasedJudge(b_style=b_style, noise=0.25, seed=seed)
    # 左边是「markdown 重排版」，右边是「纯文本版」，内容完全相同
    v1 = j.compare(q_same, q_same, a_first=True, style_a=1, style_b=0)
    v2 = j.compare(q_same, q_same, a_first=False, style_a=1, style_b=0)
    wins = (v1 + v2) / 2                             # 每对样本的「结构化版胜出」得分
    return float(wins.mean()), paired_t(wins - 0.5)

for b in [0.0, 0.10, 0.25]:
    wr, (t, p) = style_probe(b, seed=int(b * 100) + 61)
    print(f'风格偏差 {b:.2f} → 结构化版胜率 {wr:.1%} | 配对 t={t:+.2f} p={p:.2e}')

wr0, (t0, p0) = style_probe(0.0, 61)
wr2, (t2, p2) = style_probe(0.25, 86)
assert p0 > 0.01, '无风格偏差时不应显著'
assert p2 < 0.001 and wr2 > 0.6, '有风格偏差时必须被检出'
print('\\n✅ 400 对样本就足以把风格偏差检出到 p < 0.001——')
print('   配对检验消掉了「内容质量」这个最大的方差源（呼应 C66-04 的配对设计）。')
print('   注意：格式算不算质量，取决于你的构念定义。rubric 化能把它变成显式加权的一项。')"""),

    md("""## 5 · 多 judge 集成：独立偏差有用，共有偏差完全无用"""),

    code("""def ensemble_experiment(bias_mode, K_judges=5, n=4000, seed=0):
    \"\"\"bias_mode: 'noise'(纯噪声) | 'independent'(方向各异的偏差) | 'shared'(共有偏差)\"\"\"
    rng = np.random.default_rng(seed)
    q1 = rng.uniform(0, 1, n)
    q2 = rng.uniform(0, 1, n)
    truth = (q1 > q2).astype(int)
    votes = np.zeros(n)
    for k in range(K_judges):
        if bias_mode == 'noise':
            b = 0.0
        elif bias_mode == 'independent':
            b = 0.30 * (1 if k % 2 == 0 else -1)     # 方向交替
        else:
            b = 0.30                                  # 所有 judge 同方向
        j = BiasedJudge(b_pos=b, noise=0.35, seed=seed * 100 + k)
        votes += j.compare(q1, q2, a_first=True)
    maj = (votes > K_judges / 2).astype(int)
    single = BiasedJudge(b_pos=(0.0 if bias_mode == 'noise' else 0.30),
                         noise=0.35, seed=seed * 100 + 999).compare(q1, q2, a_first=True)
    return float((single == truth).mean()), float((maj == truth).mean())

print(f"{'误差类型':<22}{'单 judge':>12}{'5-judge 投票':>14}{'提升':>10}")
for mode, label in [('noise', '纯随机噪声'), ('independent', '方向各异的偏差'),
                    ('shared', '共有的同方向偏差')]:
    s, m = ensemble_experiment(mode, seed=7)
    print(f'{label:<22}{s:>12.1%}{m:>14.1%}{m-s:>+10.1%}')

s_n, m_n = ensemble_experiment('noise', seed=7)
s_s, m_s = ensemble_experiment('shared', seed=7)
s_i, m_i = ensemble_experiment('independent', seed=7)
assert (m_n - s_n) > (m_s - s_s), '集成对噪声的收益必须大于对共有偏差的收益'
assert (m_i - s_i) > (m_s - s_s), '方向各异的偏差也能被集成部分抵消'
print('\\n✅ 共有偏差那一行的提升最小——集成只能治噪声，不能治所有 judge 共有的偏差。')
print('   而长度偏差、格式偏差恰恰在几乎所有主流 judge 上方向一致。')
print('   **更糟的是：集成会让置信区间变窄，让你更自信地相信一个偏了的结论。**')"""),

    md("""## 6 · 可识别性：长度与质量真相关时，去偏会矫枉过正"""),

    code("""def lc_with_true_correlation(frac_quality, n=6000, seed=0):
    \"\"\"A 比 B 长的部分中，有 frac_quality 的比例是「因为更完整而更长」（真实质量），
    其余是纯注水。看长度控制回归会把多少真实优势一起减掉。\"\"\"
    rng = np.random.default_rng(seed)
    base = rng.uniform(0, 0.85, n)
    extra_len = np.abs(rng.normal(0.25, 0.12, n))          # A 多出来的归一化长度
    q_gain = frac_quality * 0.4 * extra_len                # 其中真实提升质量的部分
    qA_, qB_ = base + q_gain, base
    va_ = qA_ + 0.9 * extra_len + rng.normal(0, 0.3, n)    # judge 还有 0.9 的长度偏差
    vb_ = qB_ + rng.normal(0, 0.3, n)
    yy = (va_ > vb_).astype(int)
    ww = fit_logistic(extra_len.reshape(-1, 1), yy)
    raw = float(yy.mean())
    lc = float(sigmoid(ww[1]))
    # 真值：没有长度偏差时的胜率
    va_true = qA_ + rng.normal(0, 0.3, n)
    true_wr = float((va_true > (qB_ + rng.normal(0, 0.3, n))).mean())
    return raw, lc, true_wr

print(f"{'长度中真实质量占比':>20}{'raw':>10}{'LC':>10}{'真值':>10}{'LC 的误差':>12}")
for f in [0.0, 0.3, 0.6, 1.0]:
    r_, l_, t_ = lc_with_true_correlation(f, seed=71)
    print(f'{f:>20.0%}{r_:>10.1%}{l_:>10.1%}{t_:>10.1%}{l_-t_:>+12.1%}')

r0, l0, t0 = lc_with_true_correlation(0.0, seed=71)
r1, l1, t1 = lc_with_true_correlation(1.0, seed=71)
assert abs(l0 - t0) < abs(l1 - t1), '长度全是注水时 LC 最准；长度全是质量时 LC 矫枉过正'
assert l1 < t1, 'LC 把真实优势也减掉了'
print('\\n✅ 第一行（长度全是注水）：LC 几乎等于真值——去偏做对了。')
print('   最后一行（长度全来自更完整）：LC 显著低于真值——**把真实优势一起减掉了**。')
print('   而观测数据无法区分这两种情形（不可识别）。')
print('   → 诚实的报告方式：**给区间**「raw 62%，LC 54%，真值在两者之间」。')"""),

    md("""## ✏️ 练习 1：位置偏差与噪声的分离

先记一个恒等式（值得单独理解）：设不一致率 $u = 1 - \\text{一致率}$。

- **一致**的样本对，两种顺序选的是同一个答案 → 一次选到第一位、一次选到第二位 → 平均贡献 0.5；
- 因**位置偏差**而不一致的样本对，两次都选了「排在前面的那个」→ 贡献 1.0；
- 因**噪声**而不一致的样本对，翻转方向是随机的 → 平均仍贡献 0.5。

所以 $\\text{位置偏差强度} = \\Pr(\\text{选第一个}) - 0.5 = \\tfrac{1}{2}u_{\\text{position}}$，
即 **$u$ 中由位置偏差解释的比例 = $2\\times\\text{位置偏差} / u$**。

实现 `diagnose_swap(v_ab, v_ba)`：输入两种顺序下的判断
（`v_ab[i]=1` 表示顺序 AB 时判 A 赢；`v_ba[i]=1` 表示顺序 BA 时判 A 赢），
返回 `(一致率, 位置偏差强度, 解释比例, 诊断)`，诊断规则：
`u < 0.08` → `'clean'`；否则 `ratio ≥ 0.6` → `'position'`，
`ratio ≤ 0.25` → `'noise'`，其余 → `'both'`。"""),

    code("""def diagnose_swap(v_ab, v_ba):
    # TODO：位置偏差强度 = ((v_ab 选第一个的比例) + (v_ba 选第一个的比例)) / 2 - 0.5
    # 注意 v_ba 里「选第一个」等价于「没选 A」；解释比例 = 2*偏差/不一致率
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
def gen(judge):
    return judge.compare(qa, qb, a_first=True), judge.compare(qa, qb, a_first=False)

for name, j, expect in [
        ('无偏差低噪声', BiasedJudge(noise=0.03, seed=101), 'clean'),
        ('纯噪声',       BiasedJudge(noise=0.60, seed=102), 'noise'),
        ('纯位置偏差',   BiasedJudge(b_pos=0.30, noise=0.02, seed=103), 'position'),
        ('两者兼有',     BiasedJudge(b_pos=0.20, noise=0.60, seed=104), 'both')]:
    c, b, r, d = diagnose_swap(*gen(j))
    print(f'{name:<14} 一致率 {c:.1%} | 位置偏差 {b:+.3f} | 位置解释了 {r:5.0%} 的不一致 | 诊断 {d}')
    assert d == expect, f'{name} 期望 {expect} 实际 {d}'
print('\\n✅ 练习 1 通过：注意「纯噪声」和「纯位置偏差」两行的一致率都在五成左右——')
print('   只看一致率完全分不开它们，而「位置解释了多少不一致」这个比例一眼就分开了。')
print('   噪声型 → 多采样或换更强的 judge；偏差型 → swap 平均。')"""),

    md("""## ✏️ 练习 2：长度控制后的胜率与区间

实现 `lc_report(dlen, y)`：返回字典
`{'raw': 原始胜率, 'gamma': 长度系数, 'lc': 长度控制后胜率, 'interval': (min, max)}`，
其中 `interval` 是 `(min(raw, lc), max(raw, lc))`——即第 6 节主张的「诚实区间」。"""),

    code("""def lc_report(dlen, y):
    # TODO：用上面的 fit_logistic 与 sigmoid
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
rep = lc_report(dlen, y)
assert set(rep) == {'raw', 'gamma', 'lc', 'interval'}
assert rep['interval'][0] <= rep['raw'] <= rep['interval'][1]
assert rep['interval'][0] <= rep['lc'] <= rep['interval'][1]
assert rep['gamma'] > 0.5
rep2 = lc_report(dlen, y2)                       # 无长度偏差的那批数据
assert abs(rep2['interval'][1] - rep2['interval'][0]) < abs(rep['interval'][1] - rep['interval'][0])
for k_, v_ in rep.items():
    print(f'  {k_:<10} {v_}')
print(f"\\n无长度偏差时区间宽度 {rep2['interval'][1]-rep2['interval'][0]:.3f}"
      f" < 有偏差时 {rep['interval'][1]-rep['interval'][0]:.3f}")
print('✅ 练习 2 通过：区间宽度本身就是「长度偏差有多大」的直接读数。')"""),

    md("""## ✏️ 练习 3：集成的边际收益

实现 `ensemble_gain(mode, K_list, seed=0)`：对每个 K 返回 `(K, 多数投票准确率)`。
用它验证「共有偏差下，增加 judge 数量几乎不提升准确率」。"""),

    code("""def ensemble_gain(mode, K_list, seed=0):
    # TODO：复用 ensemble_experiment，返回 [(K, maj_acc), ...]
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
KS = [1, 3, 5, 9]
g_noise = ensemble_gain('noise', KS, seed=5)
g_shared = ensemble_gain('shared', KS, seed=5)
print(f"{'K':>4}{'纯噪声':>12}{'共有偏差':>12}")
for (k1, a1), (k2, a2) in zip(g_noise, g_shared):
    print(f'{k1:>4}{a1:>12.1%}{a2:>12.1%}')
gain_noise = g_noise[-1][1] - g_noise[0][1]
gain_shared = g_shared[-1][1] - g_shared[0][1]
assert gain_noise > gain_shared
print(f'\\nK 从 1 加到 9：纯噪声提升 {gain_noise:+.1%} | 共有偏差提升 {gain_shared:+.1%}')
print('✅ 练习 3 通过：共有偏差下，加再多 judge 也换不来准确率——')
print('   只会换来更窄的置信区间，也就是「更自信地相信一个偏了的结论」。')"""),

    md("""## ✏️ 练习 4：探针范式的通用实现

实现 `counterfactual_probe(judge_fn, q, attr_a, attr_b, n_repeat=2)`：
`judge_fn(q, q, attr_a, attr_b, a_first)` 返回 0/1（A 是否胜出）。
在 `a_first=True/False` 各跑一次取平均（消位置偏差），
返回 `(带属性一方的胜率, 配对 t, 配对 p)`。"""),

    code("""def counterfactual_probe(judge_fn, q, attr_a, attr_b):
    # TODO：调用两次（a_first True/False），取每对的平均得分，再做配对检验（用 paired_t）
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
def make_style_fn(b_style, seed):
    j = BiasedJudge(b_style=b_style, noise=0.25, seed=seed)
    def fn(qa_, qb_, sa, sb, a_first):
        return j.compare(qa_, qb_, a_first=a_first, style_a=sa, style_b=sb)
    return fn

wr_a, t_a, p_a = counterfactual_probe(make_style_fn(0.0, 201), q_same,
                                      np.ones(n_pairs), np.zeros(n_pairs))
wr_b, t_b, p_b = counterfactual_probe(make_style_fn(0.25, 202), q_same,
                                      np.ones(n_pairs), np.zeros(n_pairs))
print(f'无风格偏差: 胜率 {wr_a:.1%}  t={t_a:+.2f}  p={p_a:.3f}')
print(f'有风格偏差: 胜率 {wr_b:.1%}  t={t_b:+.2f}  p={p_b:.2e}')
assert p_a > 0.01 and p_b < 0.001
assert wr_b > wr_a
print('✅ 练习 4 通过：同一个函数可以测任何你怀疑的表面属性——')
print('   位置、长度、格式、署名、虚构引用、自信语气。这就是探针范式的价值。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def diagnose_swap(v_ab, v_ba):
    v_ab = np.asarray(v_ab, dtype=float)
    v_ba = np.asarray(v_ba, dtype=float)
    consistent = float((v_ab == v_ba).mean())
    u = 1 - consistent
    pick_first = float((v_ab.mean() + (1 - v_ba).mean()) / 2)
    bias = pick_first - 0.5
    ratio = (2 * bias / u) if u > 1e-12 else 0.0
    if u < 0.08:
        d = 'clean'
    elif ratio >= 0.6:
        d = 'position'
    elif ratio <= 0.25:
        d = 'noise'
    else:
        d = 'both'
    return (consistent, bias, ratio, d)"""),

    code("""# 练习 2 参考答案
def lc_report(dlen, y):
    w = fit_logistic(np.asarray(dlen).reshape(-1, 1), y)
    raw = float(np.asarray(y, dtype=float).mean())
    lc = float(sigmoid(w[1]))
    return {'raw': round(raw, 4), 'gamma': round(float(w[0]), 4),
            'lc': round(lc, 4), 'interval': (round(min(raw, lc), 4), round(max(raw, lc), 4))}"""),

    code("""# 练习 3 参考答案
def ensemble_gain(mode, K_list, seed=0):
    out = []
    for K in K_list:
        _, maj = ensemble_experiment(mode, K_judges=K, seed=seed)
        out.append((K, maj))
    return out"""),

    code("""# 练习 4 参考答案
def counterfactual_probe(judge_fn, q, attr_a, attr_b):
    v1 = judge_fn(q, q, attr_a, attr_b, True)
    v2 = judge_fn(q, q, attr_a, attr_b, False)
    scores = (np.asarray(v1, dtype=float) + np.asarray(v2, dtype=float)) / 2
    t, p = paired_t(scores - 0.5)
    return (float(scores.mean()), t, p)"""),

    md("""---
## 🧪 真实工程胶囊：偏差探针的落地脚本"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. swap 探针（每次评测都必须跑，不是可选项）
# ══════════════════════════════════════════════════════════════════
async def judge_with_swap(client, item):
    v1 = await call_judge(client, item.request, item.a, item.b)          # 顺序 AB
    v2 = await call_judge(client, item.request, item.b, item.a)          # 顺序 BA
    v2 = {"A": "B", "B": "A", "tie": "tie"}[v2]        # ← 必须翻译回来，这个 bug 极常见
    return {"v_ab": v1, "v_ba": v2, "consistent": v1 == v2,
            "final": v1 if v1 == v2 else "tie"}
# 报告：swap 一致率 + 位置偏差强度。一致率 < 0.80 时，胜率数字不要用。

# ══════════════════════════════════════════════════════════════════
# B. 长度控制回归（AlpacaEval-LC 的简化实现思路）
# ══════════════════════════════════════════════════════════════════
import numpy as np
def lc_win_rate(df):
    # df 需要列: y (A是否胜), len_a, len_b。返回 raw / gamma / lc
    dlen = (df.len_a - df.len_b) / (df.len_a + df.len_b)     # 归一化，别用原始差
    w = fit_logistic(dlen.values.reshape(-1, 1), df.y.values)
    return {"raw": df.y.mean(), "gamma": w[0], "lc": sigmoid(w[1])}
# 注意：gamma 要**按 judge 分别估计**。不同 judge 的长度偏差差别很大。

# ══════════════════════════════════════════════════════════════════
# C. 风格探针：造对照样本的最省事做法
# ══════════════════════════════════════════════════════════════════
REFORMAT_PROMPT = "\n".join([
    "Rewrite the text below into markdown with a heading and",
    "a numbered list. Do NOT add, remove, or change any information.",
    "Return only the rewritten text.",
    "",
    "<text>{text}</text>",
])
# 用一个**独立于被测 judge** 的模型做重排，避免把 judge 自己的风格偏好引进来。
# 重排后人工抽查 20 条，确认信息量确实没变——这一步不能省。

# ══════════════════════════════════════════════════════════════════
# D. 每次评测都该产出的偏差报告块（贴进 eval card）
# ══════════════════════════════════════════════════════════════════
BIAS_BLOCK = "\n".join([
    "judge:            {model}, prompt {prompt_hash}, temp {temp}",
    "swap consistency: {swap_consistency:.3f}   (< 0.80 时胜率不可用)",
    "position bias:    {position_bias:+.3f}",
    "win rate (raw):   {raw:.1%}  [{raw_lo:.1%}, {raw_hi:.1%}]",
    "win rate (LC):    {lc:.1%}   gamma={gamma:+.3f}",
    "  └─ 假设: 长度差全部归因于注水；真值在 raw 与 LC 之间",
    "style probe:      {style_delta:+.3f} (n={style_n}, paired p={style_p:.1e})",
    "self-pref probe:  {self_delta:+.3f} (n={self_n})",
])
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 四大偏差 | 位置 / 长度 / 自偏好 / 风格，各有探针与去偏手段 | judge 体检 |
| swap 诊断 | 一致率低有两种成因，位置偏差与噪声修法完全不同 | 每次评测 |
| 长度控制回归 | 估计 γ 而不是假设它；没有偏差时自动退化成不做事 | 报告 LC 胜率 |
| 自偏好 | 最危险的配置是「用 M 评 M 的新版本」 | 内部评测 |
| 探针范式 | 造只差一个属性的成对样本 + 配对检验，几十到几百对就够 | 测任何新怀疑的偏差 |
| 集成的边界 | 只能治噪声，治不了所有 judge 共有的偏差 | 决定要不要多 judge |
| 不可识别 | 长度里有多少是真实质量无法从数据分离 | 诚实报区间 |

下一模块：**03 · 元评测与校准**——judge 到底有多准？人类自身的一致率上界是多少？
以及「一致率 82%」这个数字到底该怎么读。""")
]
