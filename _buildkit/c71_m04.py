# -*- coding: utf-8 -*-
"""C71 模块 04 · 受限解码与结构化输出。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（三个量与解析失败）；"
                 "知道「自回归采样」与「有限状态机」两个概念即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_constrained_decoding.ipynb'
                       '（一个 token 级玩具 LM 与全量枚举 / 语法掩码把非法率压到 0 / '
                       '**逐步掩码 vs 真实条件分布的精确对比与 KL** / '
                       'JSON schema 编译成掩码 / 重试的选择偏倚定量 / '
                       '修复的可行与有害两种情形 / 三条路的选择树与门禁）'),
    ("核心参考", "Willard & Louf, <em>Efficient Guided Generation for Large Language Models</em>"
                 "（Outlines, 2023）——正则/CFG 到 FSM 的编译 · "
                 "<em>guidance</em> / <em>llama.cpp GBNF</em> / <em>xgrammar</em> 的语法约束实现 · "
                 "Park et al., <em>Grammar-Aligned Decoding</em>（NeurIPS 2024）"
                 "——逐步掩码的分布失真与它的修正 · "
                 "HuggingFace <em>LogitsProcessor</em> 接口（C50）· "
                 "本课程 C01 模块（采样与解码）· C68 模块 02（重试只能看异常类型）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-roads", "保证输出合法的三条路", "".join([
        P("模块 01 把「解析失败」量化了。这一节给出三条修法，"
          "<strong>它们的成本与副作用完全不同。</strong>"),
        TABLE(["路", "怎么做", "成本", "解析率能到 1.0 吗", "副作用"], [
            ["<strong>重试</strong>", "解析失败就重新采样",
             "<em>期望 $1/p$ 次调用</em>；$p$ 小时爆炸",
             "<strong>不能保证</strong>（可能一直失败）",
             "<strong>选择偏倚</strong>——被重试掉的样本不是随机的（第 5 节）"],
            ["<strong>修复</strong>", "对不合法的输出做后处理（补括号、抽取、映射）",
             "近零",
             "不能保证",
             "<strong>可能改变语义</strong>——修得越激进越危险（第 6 节）"],
            ["<strong>约束（受限解码）</strong>", "在每一步把不合法的 token 的 logit 设成 $-\\infty$",
             "近零（一次掩码计算）",
             "<strong>能</strong>——不合法输出在生成时就不可能产生",
             "<strong>分布失真</strong>——本模块第 3 节会把它精确算出来"],
        ]),
        DUAL(
            "<strong>约束是唯一能把解析率保证到 1.0 的路</strong>，"
            "而且它同时消掉了重试的偏倚与修复的语义风险。"
            "<em>所以在能用约束的地方，它应当是默认选择。</em>"
            "<strong>但它不是免费的：它换来的是一个更微妙的问题——分布失真。</strong>",
            "三条路的关系不是「三选一」，而是<strong>有优先级的组合</strong>："
            "<em>能约束的字段用约束（枚举、数值、正则、JSON schema）；"
            "约束不了的部分（自由文本）用修复兜底；"
            "两者都失败时才重试，而且重试次数与结果必须被记录</em>。"
            "<strong>这个顺序不能反：先重试再考虑约束，等于用钱买一个本可以免费拿到的性质。</strong>",
        ),
        CALLOUT("intuition", "一条判断能不能上约束的实用问题："
                             "<strong>「你的输出规范能写成一个正则或 JSON schema 吗？」</strong>"
                             "<em>能 → 直接约束；不能（比如「一段自然语言的解释」）→ 那部分只能修复兜底</em>。"
                             "而大多数结构化任务的输出<strong>大部分</strong>是可约束的——"
                             "枚举标签、数值区间、字段名、括号配对。"),
    ])),

    # ============================================================== 2
    ("mechanism", "受限解码的机制：掩码 + 状态机", "".join([
        ASCII("""
   每一步的三件事

   1. 模型给出 logits over vocab            [v0, v1, …, v_{|V|-1}]
   2. 语法状态机告诉你哪些 token 合法        mask ∈ {0, 1}^{|V|}
   3. 把非法位置设成 -inf，再 softmax        p_i ∝ exp(v_i) · mask_i

   状态机从哪来：
     正则 / CFG / JSON schema  ──编译──►  FSM（状态 × token → 状态 或 ⊥）
     每一步：当前状态 + 候选 token → 有后继状态就合法

   关键性质：**掩码是"这一步这个 token 能不能出现"，
             而不是"选了它之后还能不能合法收尾"** —— 第 3 节的失真就来自这里。
"""),
        DUAL(
            "掩码的构造有一个容易忽略的要求："
            "<strong>合法的定义必须是「存在一条路径能走到接受状态」，"
            "而不是「这一步在语法里出现过」</strong>。"
            "<em>前者需要在 FSM 上做一次可达性分析（哪些状态能到接受态），"
            "后者只看局部转移</em>——"
            "<strong>用后者会产生「走到一半发现无路可走」的死局</strong>。",
            "工程上的实现要点：<strong>掩码要能被缓存</strong>。"
            "<em>状态数通常远小于序列数</em>，"
            "所以 <code>(状态) → 允许的 token 集合</code> 是一张可以预计算的表。"
            "<strong>这让约束的运行时开销接近零</strong>——"
            "<em>这也是为什么第 1 节的表里它的成本写「近零」</em>。"
            "而 tokenizer 会带来一个真实的复杂度："
            "<strong>同一个字符串可能有多种 token 切分</strong>，"
            "所以 FSM 要建在 token 层而不是字符层"
            "（Outlines 这条线的主要工程贡献就在这里）。",
        ),
    ])),

    # ============================================================== 3
    ("distortion", "逐步掩码 ≠ 条件分布（本模块的核心）", "".join([
        P("这一节是本模块存在的理由。"
          "<strong>受限解码通常被理解成「从模型分布里只保留合法的部分」——"
          "而这个理解是错的。</strong>"),
        MATH(r"P_{\text{mask}}(y) \neq P_{\text{model}}(y \mid y \in \mathcal{S})"),
        DUAL(
            "为什么不等？<strong>因为逐步掩码在每一步只看「这一步哪些 token 合法」，"
            "它不知道「选了这个 token 之后，还有多少概率质量能合法收尾」。</strong>"
            "<em>两个分支在这一步的概率相同，但一个分支之后大概率跑偏、"
            "另一个大概率能收好尾——真实的条件分布会偏向后者，而逐步掩码不会。</em>",
            "notebook 第 3 节用一个可以<strong>全量枚举</strong>的玩具 LM 把两个分布精确算出来。"
            "结果："
            "<strong>真实条件分布 <code>{bug: 0.188, feature: 0.562, other: 0.250}</code>，"
            "逐步掩码 <code>{bug: 0.083, feature: 0.750, other: 0.167}</code></strong>，"
            "<em>$\\mathrm{KL} = 0.081$ nat，而 <code>bug</code> 被低估了 2.3 倍</em>。"
            "<strong>机制在例子里是显式的：<code>bug</code> 被选中的概率低（0.05），"
            "但它之后「正确收尾」的概率高（0.90）；"
            "逐步掩码只看见前者。</strong>",
        ),
        ASCII("""
   为什么 bug 被低估

   在 {"label":" 之后，模型给出：
     bug 0.05   feature 0.45   other 0.10   oops 0.40

   逐步掩码：去掉 oops，归一化 → bug 0.083  feature 0.75  other 0.167
                                   ↑ 到此为止，不再往后看

   真实条件分布：还要乘上「之后能合法收尾」的概率
     bug     : 0.05 × 0.90 = 0.045
     feature : 0.45 × 0.30 = 0.135
     other   : 0.10 × 0.60 = 0.060
                归一化   → bug 0.188  feature 0.562  other 0.250

   **bug 是一个"不常被想起、但一旦想起就写得对"的选项。**
   逐步掩码看不见它的这个优点。
"""),
        H3("失真的唯一来源：分支之间的收尾能力差异"),
        P("这一点值得单独立一小节，因为它与直觉相反。"
          "<strong>notebook 练习 2 会精确证明两件事</strong>："),
        OL([
            "<strong>如果所有分支的「下游收尾概率」相同，"
            "那么逐步掩码 <em>恰好等于</em> 条件分布——$\\mathrm{KL} = 0$，"
            "无论被掩掉了多少质量。</strong>"
            "<em>被掩掉 56% 还是 91%，KL 都精确地是 0。</em>",
            "<strong>失真随「分支之间收尾概率的差异」增长。</strong>"
            "<em>把某个分支的收尾概率从 0.60 压到 0.15，"
            "KL 从 0.007 涨到 0.270（近 40 倍）。</em>",
        ]),
        P("<strong>所以「语法越紧失真越大」这个直觉是错的</strong>："
          "<em>紧不紧（掩掉多少）根本不影响失真；"
          "只有「不同分支之后有多容易合法收尾」才影响</em>。"
          "<strong>这也给出了一个实用的判断："
          "如果你的语法在所有分支之后的结构都一样（比如枚举一个标签然后固定收尾），"
          "那么失真为零，可以完全不管它。</strong>"),
        H3("这个失真什么时候重要"),
        UL([
            "<strong>分支之后的结构不同时才有失真</strong>——"
            "<em>比如联合类型、可选字段、变长数组：选了 A 之后还要写很多东西、"
            "选了 B 之后马上就能收尾</em>。",
            "<strong>只取 argmax（贪心/温度 0）时通常不重要</strong>——"
            "<em>因为失真改变的是概率，而 argmax 常常不变</em>。"
            "<strong>这也解释了为什么大多数生产系统没被它咬到：它们跑温度 0。</strong>",
            "<strong>需要采样多个候选、或需要用概率做后续判断时重要</strong>——"
            "<em>best-of-n、自一致性投票、把 logprob 当置信度</em>。"
            "<strong>这些场景下失真会系统性地偏向「容易开头但不容易收尾」的分支。</strong>",
        ]),
        CALLOUT("warn", "修正它需要在解码时做前瞻（估计每个分支的「可完成质量」），"
                        "<strong>而那很贵</strong>——"
                        "<em>这是 grammar-aligned decoding 这条研究线在做的事</em>。"
                        "<strong>工程上的现实结论是：知道它存在、知道它在什么条件下重要，"
                        "并在那些条件下不要把掩码后的概率当成条件概率来用。</strong>"),
    ])),

    # ============================================================== 4
    ("schema", "从 JSON schema 编译到掩码", "".join([
        P("实践里最常用的约束来源是 JSON schema。"
          "<strong>它的四类约束各自对应一种掩码。</strong>"),
        TABLE(["schema 约束", "掩码怎么做", "注意"], [
            ["<strong>枚举</strong> <code>enum: [...]</code>",
             "在值的位置只允许能前缀匹配某个枚举项的 token",
             "<strong>最有价值的一类</strong>——它直接把模块 01 的「取值域」变成硬保证"],
            ["<strong>类型</strong> <code>type: integer</code>",
             "只允许数字 token；小数点/负号按类型放行",
             "<em>区间约束（<code>minimum</code>）无法完全用掩码表达</em>——"
             "前几位数字合法但整体越界；只能生成后校验"],
            ["<strong>必填字段</strong> <code>required</code>",
             "状态机在字段未齐时不允许 <code>}</code>",
             "这一条把「缺字段」这类解析失败彻底消掉"],
            ["<strong>字符串格式</strong> <code>pattern</code>",
             "正则编译成 FSM",
             "<em>复杂正则的 FSM 会很大</em>；要缓存"],
        ]),
        DUAL(
            "<strong>第二行那个例外值得记住</strong>："
            "<em>区间约束不能完全用掩码表达</em>。"
            "「生成一个 0 到 1 之间的数」时，"
            "<strong>掩码可以保证它是一个合法的小数，"
            "但不能保证它 ≤ 1</strong>（<code>0.9</code> 的前缀 <code>0.</code> 与 "
            "<code>7.5</code> 的前缀 <code>7</code> 在字符层都合法）。"
            "<em>所以「不变量校验」这一步（模块 01 的 signature）不能被约束替代。</em>",
            "还有一个纯工程的坑：<strong>schema 与解析器必须由同一个来源生成</strong>。"
            "<em>手写 schema 给模型、手写解析器读结果，两者会漂移</em>——"
            "而模块 01 练习 1 的第 3 项检查正是抓这个。"
            "<strong>正确做法是从一个类型定义（pydantic / dataclass）同时导出"
            "schema、掩码与解析器。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("retry", "重试的选择偏倚（定量）", "".join([
        P("模块 01 第 6 节定性地说明了它。这一节给出定量结果与成本。"),
        MATH(r"\mathbb{E}[\text{calls}] = \frac{1}{p_{\text{parse}}}, \qquad "
             r"\mathbb{E}[\text{correct} \mid \text{parse ok}] > \mathbb{E}[\text{correct}]"),
        DUAL(
            "<strong>成本：期望调用次数是 $1/p$。</strong>"
            "<em>$p = 0.9$ 时是 1.11 次（可以接受）；"
            "$p = 0.5$ 时是 2 次；$p = 0.2$ 时是 5 次</em>。"
            "<strong>而「重试上限」把它变成一个截断分布："
            "上限 $R$ 时仍有 $(1-p)^R$ 的比例最终失败。</strong>",
            "<strong>偏倚：解析成功与答对正相关（都受样本难度影响），"
            "所以在解析成功的子集上算准确率会高估。</strong>"
            "<em>notebook 第 5 节把这个偏差量出来</em>。"
            "<strong>而受限解码让 $p = 1$，于是成本回到 1 次、偏倚消失</strong>——"
            "<em>这是「约束优于重试」最直接的论证：它同时便宜且无偏。</em>",
        ),
        H3("如果必须重试（约束不可用时）"),
        OL([
            "<strong>重试的触发条件只能是「解析失败」</strong>——"
            "<em>不能是「结果看起来不对」</em>（那是在用真值调参，"
            "与 C68 模块 02 的重试纪律同构）。",
            "<strong>报分的分母是全部样本，最终失败记为错</strong>。",
            "<strong>重试次数的分布必须进报告</strong>——"
            "<em>它是成本，也是「解析率其实不是 1.0」的证据</em>。",
            "<strong>重试要带温度扰动</strong>——"
            "<em>温度 0 时重试会得到完全相同的输出，等于白花一次钱</em>。"
            "而这又意味着重试引入了不确定性，"
            "<strong>于是配置的可复现性下降（C68 模块 02 的老问题）。</strong>",
        ]),
    ])),

    # ============================================================== 6
    ("repair", "修复：可行与有害的两种情形", "".join([
        TABLE(["修复动作", "可行吗", "为什么"], [
            ["去掉 markdown 代码块围栏", "<strong>可行</strong>",
             "纯语法层，不触碰内容；<em>而且它对应模块 01 的「禁止项」槽位</em>"],
            ["去掉前后的解释文字，抽取 JSON 块", "<strong>可行</strong>",
             "同上；用「第一个 <code>{</code> 到匹配的 <code>}</code>」定位"],
            ["补上缺失的右括号", "<em>谨慎</em>",
             "<strong>可能把一个被截断的输出补成一个「看起来完整」的错误结果</strong>——"
             "<em>而截断通常意味着 max_tokens 不够，那是一个应当被发现的配置问题</em>"],
            ["把不在枚举里的值映射到最近的合法值", "<strong>有害</strong>",
             "<em>它把「模型不知道答案」伪装成了「模型给了一个答案」</em>；"
             "<strong>而下游无法区分这两者</strong>"],
            ["用另一个模型把输出改写成合法格式", "<strong>有害（通常）</strong>",
             "引入第二个不确定环节，且<em>错误传播变成乘法</em>（模块 01 第 3 节）；"
             "<strong>能用约束的地方绝不该用这个</strong>"],
        ]),
        DUAL(
            "分界线很清楚：<strong>只做语法层的清洗，不做语义层的猜测。</strong>"
            "<em>去围栏、抽 JSON 块是语法；"
            "把 <code>BUG</code> 映射成 <code>bug</code> 是灰色（大小写可以规范化）；"
            "把 <code>maybe_bug</code> 映射成 <code>bug</code> 是语义猜测</em>。",
            "还有一条记录纪律：<strong>修复必须被记录，而且被修复过的样本要能被单独统计。</strong>"
            "<em>因为「修复率」是一个健康指标</em>——"
            "<strong>它上升通常意味着 prompt 的格式槽位或模型行为变了</strong>，"
            "而如果修复是静默的，这个信号就丢了。"
            "<em>这与 C68 模块 02 的「失败分类必须报告比例」是同一条。</em>",
        ),
    ])),

    # ============================================================== 7
    ("decision", "选择树", "".join([
        ASCII("""
   输出规范能写成正则 / JSON schema 吗？
     │
     ├─ 能 ────► **用受限解码**（解析率保证 1.0）
     │            │
     │            ├─ 需要采样多个候选 / 用 logprob 当置信度？
     │            │     ├─ 是 → 注意第 3 节的分布失真，别把掩码后的概率当条件概率
     │            │     └─ 否（温度 0 取 argmax）→ 失真通常不影响结果
     │            │
     │            └─ 有区间/跨字段不变量？→ 生成后仍要做 validate（掩码表达不了）
     │
     └─ 不能（输出含自由文本）
                  │
                  ├─ 把**可约束的部分**单独成字段并约束它
                  │   （比如 {"label": <枚举>, "reason": <自由文本>}）
                  │
                  ├─ 自由文本部分用**语法层修复**兜底（去围栏、抽 JSON 块）
                  │
                  └─ 仍然失败 → 重试（带温度扰动 + 上限 + 记录次数）
                                └─ 报分的分母仍然是全部样本
"""),
        P("<strong>这棵树的形状本身是结论</strong>："
          "<em>约束在最上层、修复在中层、重试在最下层</em>，"
          "而<strong>「把可约束的部分拆成独立字段」是一个几乎总是值得做的重构</strong>——"
          "它把一次「全或无」的解析变成「结构化字段有保证 + 自由文本尽力而为」。"),
        H3("门禁（按 C68 模块 04 分级）"),
        UL([
            "<strong>确定性阻断</strong>：schema 与解析器不是同源生成的；"
            "启用了约束但 <code>parse_rate < 1.0</code>（说明掩码有 bug）；"
            "<code>required</code> 字段在 schema 里但掩码没实现",
            "<strong>统计阻断</strong>：修复率或重试率相对基线上升超过阈值",
            "<strong>报警</strong>：修复率 > 0 且在上升（<em>它是格式槽位或模型行为变化的早期信号</em>）",
        ]),
        CALLOUT("intuition", "最后一条确定性检查值得单独说："
                             "<strong>「启用了约束但解析率不是 1.0」是一个逻辑矛盾</strong>——"
                             "<em>约束的定义就是不合法输出不可能产生</em>。"
                             "所以它出现时一定是实现有 bug（掩码漏了某条规则、"
                             "或者约束根本没生效），"
                             "<strong>而这是一个零误报的检查。</strong>"),
    ])),

    # ============================================================== 8
    ("tokenizer", "tokenizer 带来的复杂度", "".join([
        P("前七节把掩码当成「token 集合」来处理。"
          "<strong>而把语法从字符层搬到 token 层，是这一层最真实的工程难点。</strong>"),
        ASCII("""
   问题：同一个字符串有多种 token 切分

   目标：输出 "feature"
   可能的切分:  [feature]  |  [feat][ure]  |  [f][eature]  |  [fe][at][ure] …

   如果掩码只允许 [feature] 这一个 token，
   那么当模型倾向于先出 [feat] 时，这条路被掩掉了 ——
   **而它本来能走到一个合法结果**。

   于是掩码必须允许「任何能拼出某个合法后续的 token」，
   也就是要在 token 层重建 FSM，而不是在字符层。
"""),
        DUAL(
            "<strong>这不是理论问题，它有两个真实后果。</strong>"
            "<em>① 掩码过严 → 把合法路径掩掉 → 模型被迫走一条概率更低的路，"
            "输出质量下降</em>（而这看起来像「加了约束效果变差了」）；"
            "<em>② 掩码过松 → 生成出无法回到合法状态的前缀 → 死局</em>"
            "（练习 1 那个问题的另一种形态）。",
            "<strong>正确做法是预计算一张 <code>(FSM 状态) → (允许的 token 集合)</code> 的表</strong>，"
            "其中「允许」的定义是：<em>这个 token 的字符串是某条合法路径的一个前缀片段</em>。"
            "<strong>状态数远小于序列数，所以这张表可以在启动时算好并缓存</strong>——"
            "这也是为什么受限解码的运行时开销可以接近零。"
            "<em>而这张表依赖具体的 tokenizer，所以<strong>换模型时要重算</strong></em>"
            "（模块 05 会把这一点归到「保留但需重测」那一档）。",
        ),
        CALLOUT("warn", "一个实践建议："
                        "<strong>不要自己实现 token 层的语法编译。</strong>"
                        "<em>用 Outlines / xgrammar / GBNF 这类成熟实现</em>——"
                        "它们的主要价值恰恰在这个又琐碎又容易出错的地方。"
                        "<strong>本课从零实现的是「掩码的语义」，不是它的高效实现。</strong>"),
    ])),

    # ============================================================== 9
    ("api-structured-output", "API 上的 structured output 与 tool-calling", "".join([
        P("拿不到 logits 时，还有一条路："
          "<strong>服务方提供的 structured output / tool-calling —— 它们内部就是约束。</strong>"),
        TABLE(["形式", "它给你什么", "要注意什么"], [
            ["<strong>JSON mode</strong>", "保证输出是合法 JSON",
             "<em>只保证语法，不保证 schema</em>——"
             "<strong>字段名、枚举值、类型仍然要自己 validate</strong>"],
            ["<strong>schema-constrained output</strong>",
             "保证符合给定 JSON schema",
             "<strong>区间约束（<code>minimum</code>）通常不被保证</strong>"
             "（第 5 节的那个例外）；<em>而 schema 的哪些关键字被支持要查文档</em>"],
            ["<strong>tool-calling</strong>",
             "保证参数符合工具的参数 schema",
             "<em>它同时改变了模型的行为（模型知道自己在「调工具」）</em>，"
             "所以<strong>它与「输出 JSON」不是等价的两种写法</strong>——效果要分别测"],
        ]),
        DUAL(
            "<strong>三者的共同点：它们把「保证」从你这边移到了服务方那边。</strong>"
            "<em>好处是省事；代价是你不知道它内部怎么实现的</em>——"
            "<strong>包括本模块第 3 节那个分布失真是否被修正过。</strong>"
            "<em>所以在采样多候选或用 logprob 当置信度的场景下，"
            "仍然要按「可能有失真」来对待。</em>",
            "还有一条纯工程的纪律："
            "<strong>无论用哪种形式，本地仍然要跑一次 <code>validate</code>。</strong>"
            "<em>理由有三个：区间与跨字段不变量通常不被保证；"
            "服务方的实现可能在某些边缘情况下失效；"
            "而且这一步让你的解析率指标是自己测出来的，而不是相信来的。</em>"
            "<strong>「启用了约束但解析率不是 1.0」这个矛盾"
            "（练习 4 的第一条检查）只有在你自己 validate 时才可能被发现。</strong>",
        ),
    ])),

    # ============================================================== 10
    ("recap", "本模块的四条可执行结论", "".join([
        OL([
            "<strong>能约束的字段全部上约束。</strong>"
            "<em>它是唯一能把解析率<strong>保证</strong>到 1.0 的路，"
            "同时消掉重试的成本（$1/p$）与偏倚</em>。"
            "<strong>而它还是可迁移的</strong>——换模型时它原样保留（模块 05）。",
            "<strong>把可约束的部分拆成独立字段。</strong>"
            '<em>比如 <code>{"label": &lt;枚举&gt;, "reason": &lt;自由文本&gt;}</code></em>——'
            "<strong>这把一次「全或无」的解析变成"
            "「结构化字段有保证 + 自由文本尽力而为」</strong>，"
            "是一个几乎总是值得做的重构。",
            "<strong>不变量校验不能被约束替代。</strong>"
            "<em>区间约束（<code>0 ≤ x ≤ 1</code>）无法用逐步掩码表达</em>，"
            "而跨字段的约束更不行。"
            "<strong>所以模块 01 的 <code>signature.validate</code> 这一步永远保留。</strong>",
            "<strong>在三类场景下不要把掩码后的概率当条件概率：</strong>"
            "<em>采样多个候选（best-of-n）、自一致性投票、把 logprob 当置信度</em>。"
            "<strong>而判断有没有失真的判据很具体：看语法在不同分支之后的结构是否相同</strong>——"
            "相同则失真恰好为 0（练习 2），不同则要小心。",
        ]),
        DUAL(
            "<strong>这四条里第 2 条最容易被忽略，而它的收益最直接。</strong>"
            "<em>很多系统的输出是「一段带解释的自然语言，里面藏着一个结论」</em>，"
            "于是解析永远是概率性的。"
            "<strong>把结论抽成一个枚举字段之后，那部分就变成了确定的</strong>——"
            "而解释部分即使解析失败，也不影响结论可用。",
            "第 4 条的判据值得再说一次，因为它把一个抽象结论变成了一次检查："
            "<strong>如果你的 schema 是「一个枚举 + 固定的收尾」，"
            "那么所有分支之后的结构相同，失真恰好为 0，可以完全不管它。</strong>"
            "<em>需要警惕的是联合类型、可选字段、变长数组</em>——"
            "那里「选了 A 还要写很多、选了 B 马上收尾」，"
            "<strong>而这类 schema 恰恰是最常见的复杂输出形态。</strong>",
        ),
    ])),
]

NB = [
    md("""# 04 · 受限解码与结构化输出（三条路 / 掩码 / **分布失真** / schema / 重试 / 修复）

目标：搞清楚受限解码**保证了什么**、**代价是什么**，
以及为什么它优于重试与修复。

本 notebook 你会亲手实现：
1. **一个 token 级玩具 LM** —— 小到可以**全量枚举**所有输出串及其概率
2. **语法掩码** —— 把非法率从 74% 压到 0
3. **逐步掩码 vs 真实条件分布的精确对比** —— KL = 0.081 nat，`bug` 被低估 2.3 倍
4. **失真什么时候重要** —— argmax 不变 vs 采样/置信度场景；
   而练习 2 会证明**失真的唯一来源是分支的收尾能力差异，与掩掉多少质量无关**
5. **JSON schema 编译成掩码** —— 枚举 / 类型 / 必填 / 正则，以及区间的例外
6. **重试的成本与选择偏倚** —— $1/p$ 与高估的量
7. **修复的可行与有害** —— 语法层 vs 语义层的分界
8. **选择树 + 门禁**

> 心智模型：**约束是唯一能把解析率保证到 1.0 的路，
> 而它换来的是一个更微妙的问题——逐步掩码得到的分布不是条件分布。**"""),

    md("""## 0 · 环境"""),

    code("""import os, re, json, math, hashlib, itertools
from collections import Counter, defaultdict

import numpy as np

print('numpy', np.__version__, '| 本模块的「模型」是一个可全量枚举的玩具 LM')

VALUES = ['bug', 'feature', 'other']
VOCAB = ['{', '}', '"', ':', 'label', 'bug', 'feature', 'other', 'oops', 'EOS']
V_IDX = {t: i for i, t in enumerate(VOCAB)}"""),

    md("""## 1 · 一个可全量枚举的 token 级玩具 LM

关键设计：**把字段名与值当成单个 token**（真实 BPE 对常见字符串也是这样），
于是所有输出串的数量很小，可以精确枚举。"""),

    code("""def next_dist(prefix):
    \"\"\"给定 token 前缀，返回下一个 token 的分布。确定性、可枚举。

    刻意设计的一点：**不同的 value 之后「正确收尾」的概率不同**——
    第 3 节的分布失真就来自这里。
    \"\"\"
    p = list(prefix)
    if p == []:
        return {'{': 0.9, '"': 0.1}                     # 10% 一开头就跑偏
    if p == ['{']:
        return {'"': 1.0}
    if p == ['{', '"']:
        return {'label': 0.95, 'oops': 0.05}
    if p == ['{', '"', 'label']:
        return {'"': 1.0}
    if p == ['{', '"', 'label', '"']:
        return {':': 1.0}
    if p == ['{', '"', 'label', '"', ':']:
        return {'"': 0.9, 'bug': 0.1}                   # 10% 忘了引号
    if p == ['{', '"', 'label', '"', ':', '"']:
        return {'bug': 0.05, 'feature': 0.45, 'other': 0.10, 'oops': 0.40}
    if len(p) == 7 and p[6] in VALUES + ['oops']:
        # ← 关键：收尾概率依赖前面选了哪个 value
        q = {'bug': 0.90, 'feature': 0.30, 'other': 0.60, 'oops': 0.50}[p[6]]
        return {'"': q, 'EOS': 1 - q}
    if len(p) == 8 and p[7] == '"':
        return {'}': 0.95, 'EOS': 0.05}
    if len(p) == 9 and p[8] == '}':
        return {'EOS': 1.0}
    return {'EOS': 1.0}

def enumerate_all(maxlen=10):
    \"\"\"枚举所有完整输出串及其概率。\"\"\"
    out = {}
    def rec(prefix, prob):
        if prefix and prefix[-1] == 'EOS':
            out[tuple(prefix)] = out.get(tuple(prefix), 0.0) + prob
            return
        if len(prefix) >= maxlen:
            return
        for t, p in next_dist(prefix).items():
            if p > 0:
                rec(prefix + [t], prob * p)
    rec([], 1.0)
    return out

UNCOND = enumerate_all()
print(f'完整输出串共 {len(UNCOND)} 个，概率之和 = {sum(UNCOND.values()):.6f}')
for seq, p in sorted(UNCOND.items(), key=lambda kv: -kv[1])[:5]:
    print(f'  {p:.4f}  {" ".join(seq)}')
assert abs(sum(UNCOND.values()) - 1.0) < 1e-9, '枚举必须覆盖全部概率质量'
print('\\n✅ 全量枚举成功——这是本模块能精确算出分布失真的前提。')"""),

    md("""## 2 · 语法与掩码：把非法率压到 0"""),

    code("""def is_valid(seq):
    \"\"\"语法：{ " label " : " <VALUE> " } EOS\"\"\"
    seq = list(seq)
    return (len(seq) == 10
            and seq[:6] == ['{', '"', 'label', '"', ':', '"']
            and seq[6] in VALUES
            and seq[7:] == ['"', '}', 'EOS'])

VALID = {k: v for k, v in UNCOND.items() if is_valid(k)}
invalid_mass = 1.0 - sum(VALID.values())
print(f'合法串 {len(VALID)} 个，合法质量 {sum(VALID.values()):.4f}')
print(f'**无约束采样的非法率 = {invalid_mass:.1%}**')

# 合法前缀集合：这是掩码的正确定义（存在一条路径能走到接受态）
VALID_PREFIXES = set()
for k in VALID:
    for i in range(len(k) + 1):
        VALID_PREFIXES.add(tuple(k[:i]))
print(f'合法前缀 {len(VALID_PREFIXES)} 个')

def mask(prefix):
    \"\"\"返回这一步允许的 token 集合。

    注意定义：允许 = 「加上它之后仍是某个合法串的前缀」，
    而不是「它在语法里出现过」。后者会产生「走到一半无路可走」的死局。
    \"\"\"
    return {t for t in VOCAB if tuple(list(prefix) + [t]) in VALID_PREFIXES}

def masked_dist(prefix):
    d = next_dist(prefix)
    allowed = {t: p for t, p in d.items() if t in mask(prefix)}
    z = sum(allowed.values())
    return {t: p / z for t, p in allowed.items()} if z > 0 else {}

def enumerate_masked():
    out = {}
    def rec(prefix, prob):
        if prefix and prefix[-1] == 'EOS':
            out[tuple(prefix)] = out.get(tuple(prefix), 0.0) + prob
            return
        for t, p in masked_dist(prefix).items():
            rec(prefix + [t], prob * p)
    rec([], 1.0)
    return out

MASKED = enumerate_masked()
print(f'\\n受限解码后：{len(MASKED)} 个输出串，全部合法 = '
      f'{all(is_valid(k) for k in MASKED)}')
print(f'概率之和 = {sum(MASKED.values()):.6f}')
assert all(is_valid(k) for k in MASKED), '受限解码不可能产生非法输出'
assert abs(sum(MASKED.values()) - 1.0) < 1e-9
assert invalid_mass > 0.5, '无约束时非法率应当很高（这个玩具 LM 刻意设成这样）'
print(f'\\n✅ 非法率从 {invalid_mass:.1%} 压到 0——而且是**保证**，不是概率上的改善。')
print('   掩码的成本是一次集合查表；状态数远小于序列数，所以它可以预计算并缓存。')"""),

    md("""## 3 · 核心：逐步掩码 ≠ 条件分布

两个分布都精确算出来，然后比。"""),

    code("""Z = sum(VALID.values())
COND = {k: v / Z for k, v in VALID.items()}      # 真实条件分布 P(·| 合法)

print(f"{'输出':<10}{'逐步掩码':>12}{'真实条件分布':>16}{'比值':>9}")
rows = []
for k in sorted(COND, key=lambda k: k[6]):
    m, c = MASKED[k], COND[k]
    rows.append((k[6], m, c, m / c))
    print(f'{k[6]:<10}{m:>12.4f}{c:>16.4f}{m / c:>9.2f}')

kl = sum(MASKED[k] * math.log(MASKED[k] / COND[k]) for k in MASKED if MASKED[k] > 0)
print(f'\\nKL(逐步掩码 ‖ 真实条件分布) = {kl:.4f} nat')

ratios = {v: r for v, _, _, r in rows}
assert abs(sum(MASKED.values()) - 1.0) < 1e-9 and abs(sum(COND.values()) - 1.0) < 1e-9
assert kl > 0.05, f'两个分布必须明显不同，KL = {kl}'
assert ratios['bug'] < 0.5, 'bug 被低估了一倍以上'
assert ratios['feature'] > 1.2, 'feature 被高估'
print(f'\\n✅ 两个分布明显不同：bug 被低估 {1 / ratios["bug"]:.1f} 倍，'
      f'feature 被高估 {ratios["feature"]:.2f} 倍。')"""),

    code("""# --- 机制：把两条链路的概率摊开 ---
print('在 {"label":" 之后，模型给出的原始分布:')
raw = next_dist(['{', '"', 'label', '"', ':', '"'])
for t, p in raw.items():
    print(f'  {t:<10}{p:.2f}')

print('\\n逐步掩码：去掉 oops 后归一化（**到此为止，不再往后看**）')
allowed = {t: p for t, p in raw.items() if t in VALUES}
z1 = sum(allowed.values())
for t, p in allowed.items():
    print(f'  {t:<10}{p / z1:.4f}')

print('\\n真实条件分布：还要乘上「之后能合法收尾」的概率')
tail = {'bug': 0.90, 'feature': 0.30, 'other': 0.60}
joint = {t: raw[t] * tail[t] * 0.95 for t in VALUES}      # ×0.95 是 } 的概率
z2 = sum(joint.values())
for t in VALUES:
    print(f'  {t:<10}{raw[t]:.2f} × {tail[t]:.2f} = {raw[t] * tail[t]:.4f}'
          f'  → 归一化 {joint[t] / z2:.4f}')

for t in VALUES:
    assert abs(joint[t] / z2 - COND[tuple(['{', '"', 'label', '"', ':', '"', t,
                                           '"', '}', 'EOS'])]) < 1e-9
print('\\n✅ 失真的来源是显式的：')
print('   **bug 是一个「不常被想起、但一旦想起就写得对」的选项**')
print('   （被选中概率 0.05，但收尾概率 0.90）。')
print('   逐步掩码只看见前者——它不知道「选了这个 token 之后还有多少质量能合法收尾」。')
print('   修正它需要在解码时做前瞻（估计每个分支的可完成质量），而那很贵。')
print('   这正是 grammar-aligned decoding 这条研究线在做的事。')"""),

    md("""## 4 · 失真什么时候重要

三个场景，两种结论。"""),

    code("""def argmax_of(dist):
    return max(dist, key=lambda k: dist[k])

am_masked = argmax_of(MASKED)[6]
am_cond = argmax_of(COND)[6]
print(f'argmax（温度 0 取最可能）: 逐步掩码 → {am_masked} | 真实条件分布 → {am_cond}')
assert am_masked == am_cond, '本例里 argmax 相同——这是常见情形'

# 场景二：采样多个候选（best-of-n / 自一致性投票）
def sample_dist(dist, n, seed=0):
    rng = np.random.default_rng(seed)
    keys = list(dist)
    probs = np.array([dist[k] for k in keys])
    idx = rng.choice(len(keys), size=n, p=probs)
    return Counter(keys[i][6] for i in idx)

n = 20000
c_masked = sample_dist(MASKED, n, seed=1)
c_cond = sample_dist(COND, n, seed=1)
print(f'\\n采样 {n} 次的标签分布:')
print(f"{'':<10}{'逐步掩码':>12}{'真实条件':>12}")
for v in VALUES:
    print(f'{v:<10}{c_masked[v] / n:>12.3f}{c_cond[v] / n:>12.3f}')

diff = max(abs(c_masked[v] / n - c_cond[v] / n) for v in VALUES)
assert diff > 0.1, f'采样分布应当明显不同: {diff}'

# 场景三：把掩码后的概率当置信度
conf_masked = MASKED[argmax_of(MASKED)]
conf_cond = COND[argmax_of(COND)]
print(f'\\n把最大概率当置信度: 逐步掩码 {conf_masked:.3f} | 真实条件 {conf_cond:.3f}')
assert conf_masked > conf_cond, '掩码后的「置信度」被高估'
print(f'  → 高估了 {conf_masked - conf_cond:.3f}（相对 '
      f'{(conf_masked - conf_cond) / conf_cond:.0%}）')

print('\\n✅ 三个场景的结论不同:')
print('   ① **温度 0 取 argmax：通常不受影响**（本例里 argmax 相同）——')
print('      这解释了为什么大多数生产系统没被它咬到。')
print(f'   ② 采样多个候选：标签分布差 {diff:.2f}，会系统性偏向「容易开头」的分支；')
print(f'   ③ 把概率当置信度：高估 {(conf_masked - conf_cond) / conf_cond:.0%}。')
print('   **所以纪律很具体：在 ② ③ 这两类场景下，不要把掩码后的概率当条件概率。**')
print()
print('   而练习 2 会给出一个更有用的判据：**失真的唯一来源是分支之间的收尾能力差异**。')
print('   如果你的语法在所有分支之后结构相同（枚举一个标签然后固定收尾），失真恰好是 0。')"""),

    md("""## 5 · JSON schema 编译成掩码

四类约束，以及区间那个无法用掩码表达的例外。"""),

    code("""def compile_enum_mask(enum_values):
    \"\"\"枚举 → 允许的 token 集合（本玩具里 value 是单 token）。\"\"\"
    return set(enum_values)

def compile_required_mask(schema_fields, emitted_fields):
    \"\"\"必填字段未齐时不允许闭合。\"\"\"
    missing = [f for f in schema_fields if f not in emitted_fields]
    return set() if missing else {'}'}

def compile_type_mask(kind, so_far):
    \"\"\"类型 → 允许的字符集合（这里用字符层演示数字类型）。\"\"\"
    digits = set('0123456789')
    if kind == 'integer':
        return digits | ({'-'} if so_far == '' else set())
    if kind == 'number':
        allowed = digits | ({'-'} if so_far == '' else set())
        if '.' not in so_far and so_far not in ('', '-'):
            allowed |= {'.'}
        return allowed
    raise ValueError(kind)

SCHEMA = {'type': 'object',
          'properties': {'label': {'enum': VALUES},
                         'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}},
          'required': ['label', 'confidence']}

print('枚举掩码:', sorted(compile_enum_mask(SCHEMA['properties']['label']['enum'])))
print('必填掩码（只发了 label）:', compile_required_mask(SCHEMA['required'], ['label']))
print('必填掩码（都发了）      :', compile_required_mask(SCHEMA['required'],
                                                    ['label', 'confidence']))
print('number 类型掩码（so_far=""）  :',
      ''.join(sorted(compile_type_mask('number', ''))))
print('number 类型掩码（so_far="0."）:',
      ''.join(sorted(compile_type_mask('number', '0.'))))

assert compile_required_mask(SCHEMA['required'], ['label']) == set(), \\
    '字段未齐时不允许闭合'
assert '}' in compile_required_mask(SCHEMA['required'], ['label', 'confidence'])
assert '.' not in compile_type_mask('number', '0.'), '已有小数点后不再允许小数点'

# --- 区间约束的例外 ---
print('\\n区间约束（0 ≤ x ≤ 1）能用掩码表达吗？')
for s in ['0', '0.', '0.9', '7', '7.5']:
    ok_chars = compile_type_mask('number', s.rstrip('0123456789.') or s[:1]) if False \\
        else compile_type_mask('number', s)
    print(f'  前缀 {s!r:<7} 在字符层合法 = True，'
          f'而整体是否 ≤ 1 = {float(s.rstrip(".") or 0) <= 1}')
print('  → 「7」这个前缀在字符层完全合法，但它注定超界。')
print('  **区间约束无法用逐步掩码表达**——只能生成后校验。')
assert '7' not in ('0', '0.9'), 'trivially true; 重点是下面这条断言'
assert float('7.5') > 1, '7.5 越界，而它的每一个前缀在字符层都合法'
print('\\n✅ 四类约束里三类可以掩码，区间不能。')
print('   所以模块 01 的 signature.validate（不变量校验）**不能被约束替代**。')
print('   还有一条纯工程的纪律：**schema 与解析器必须同源生成**')
print('   （从一个 pydantic 类型同时导出 schema、掩码与解析器），')
print('   否则两者会漂移——模块 01 练习 1 的第 3 项检查正是抓这个。')"""),

    md("""## 6 · 重试：成本与选择偏倚"""),

    code("""def expected_calls(p, max_retries=None):
    \"\"\"解析成功率 p 时的期望调用次数。max_retries=None 表示无限重试。\"\"\"
    if p <= 0:
        return float('inf')
    if max_retries is None:
        return 1.0 / p
    # 截断：1 + (1-p) + (1-p)^2 + ... + (1-p)^R
    return sum((1 - p) ** i for i in range(max_retries + 1))

def final_failure_rate(p, max_retries):
    return (1 - p) ** (max_retries + 1)

print(f"{'p':>6}{'期望调用(无限)':>14}{'期望调用(R=3)':>14}{'最终失败率(R=3)':>16}")
for p in [0.95, 0.9, 0.7, 0.5, 0.26, 0.2]:
    print(f'{p:>6.2f}{expected_calls(p):>14.2f}{expected_calls(p, 3):>14.2f}'
          f'{final_failure_rate(p, 3):>16.2%}')

p_unconstrained = sum(VALID.values())
print(f'\\n本玩具 LM 的无约束解析率 p = {p_unconstrained:.3f}')
print(f'  → 期望调用 {expected_calls(p_unconstrained):.2f} 次；'
      f'R=3 时仍有 {final_failure_rate(p_unconstrained, 3):.1%} 最终失败')
print(f'  受限解码：p = 1.0 → 期望调用 1.00 次，最终失败率 0')
assert expected_calls(1.0) == 1.0
assert expected_calls(p_unconstrained) > 4, '低解析率下重试成本爆炸'
print('\\n✅ 「约束优于重试」的第一个论证就是成本：'
      f'{expected_calls(p_unconstrained):.1f} 次 vs 1 次。')"""),

    code("""# --- 选择偏倚：解析成功与答对正相关 ---
def simulate_retry_bias(n_items=400, seed=0):
    rng = np.random.default_rng(seed)
    d = rng.random(n_items)                              # 难度
    parse_ok = rng.random(n_items) > d * 0.9             # 难 → 更可能解析失败
    correct = rng.random(n_items) > d * 0.9              # 难 → 更可能答错
    honest = float(np.mean(parse_ok & correct))          # 分母 = 全部
    biased = float(np.mean(correct[parse_ok]))           # 分母 = 解析成功的
    return honest, biased, float(np.mean(parse_ok)), float(
        np.corrcoef(parse_ok.astype(float), correct.astype(float))[0, 1])

h, b, pr, corr = simulate_retry_bias()
print(f'解析成功率            {pr:.1%}')
print(f'诚实口径（分母=全部）  {h:.1%}')
print(f'有偏口径（只看解析成功）{b:.1%}')
print(f'高估 {b - h:.1f} 个百分点（相对 {(b - h) / h:.0%}）')
print(f'解析成功与答对的相关系数 {corr:.3f}')

assert b > h, '在解析成功的子集上报分会高估'
assert corr > 0.1, '偏倚的来源是两者正相关'
print('\\n✅ 偏倚的来源很清楚：解析成功与答对**都受样本难度影响**，因此正相关，')
print('   于是条件化在「解析成功」上会拉高准确率。')
print('   而受限解码让 p = 1，所有样本都进分母——**偏倚消失**。')
print('   这是「约束优于重试」的第二个论证：它同时便宜且无偏。')
print()
print('   如果约束不可用而必须重试，四条纪律：')
print('   ① 触发条件只能是「解析失败」，不能是「结果看起来不对」（C68-02 的重试纪律）；')
print('   ② 报分的分母是全部样本，最终失败记为错；')
print('   ③ 重试次数的分布必须进报告；')
print('   ④ 重试要带温度扰动——温度 0 时重试会得到完全相同的输出，等于白花钱。')"""),

    md("""## 7 · 修复：语法层可行，语义层有害"""),

    code("""def repair_syntactic(raw):
    \"\"\"只做语法层清洗：去围栏、抽 JSON 块。不触碰内容。\"\"\"
    s = raw.strip()
    s = re.sub(r'^```[a-z]*\\s*|\\s*```$', '', s)
    m = re.search(r'\\{.*\\}', s, re.S)
    return m.group(0) if m else s

def repair_semantic(value, allowed):
    \"\"\"语义层猜测：把不在枚举里的值映射到「最近的」合法值。\"\"\"
    if value in allowed:
        return value, False
    low = str(value).lower()
    for a in allowed:
        if a in low or low in a:
            return a, True
    # 兜底：字符重叠最多的那个
    best = max(allowed, key=lambda a: len(set(a) & set(low)))
    return best, True

CASES = [
    ('```json\\n{"label": "bug"}\\n```', 'bug', '围栏'),
    ('这条应该是：{"label": "feature"}', 'feature', '前置解释'),
    ('{"label": "BUG"}', 'bug', '大小写'),
    ('{"label": "maybe_bug"}', None, '模型不确定'),
    ('{"label": "unknown"}', None, '模型不知道'),
]
print(f"{'情形':<12}{'语法修复后可解析':>18}{'语义映射的结果':>18}{'该不该映射':>12}")
for raw, gold, note in CASES:
    fixed = repair_syntactic(raw)
    try:
        v = json.loads(fixed).get('label')
    except json.JSONDecodeError:
        v = None
    v_norm = v.lower() if isinstance(v, str) else v
    parses = v_norm in VALUES
    mapped, did = repair_semantic(v_norm, VALUES) if v_norm else (None, False)
    should = '可以' if gold else '**不该**'
    print(f'{note:<12}{str(parses):>18}{str(mapped):>18}{should:>12}')

assert json.loads(repair_syntactic(CASES[0][0]))['label'] == 'bug', '去围栏可行'
assert json.loads(repair_syntactic(CASES[1][0]))['label'] == 'feature', '抽 JSON 块可行'
m_unknown, did = repair_semantic('unknown', VALUES)
assert did and m_unknown in VALUES, '语义映射会给出一个合法值'
print(f'\\n⚠️ 最后两行是问题所在：「maybe_bug」与「unknown」被映射成了合法值')
print(f'   （unknown → {m_unknown}）。')
print('   **它把「模型不知道答案」伪装成了「模型给了一个答案」，而下游无法区分这两者。**')
print()
print('✅ 分界线：**只做语法层清洗，不做语义层猜测**。')
print('   去围栏、抽 JSON 块 → 语法，可行；')
print('   大小写规范化 → 灰色（通常可以，但要记录）；')
print('   把 unknown 映射成 bug → 语义猜测，有害。')
print()
print('   还有一条记录纪律：**修复必须被记录，被修复过的样本要能单独统计**。')
print('   因为「修复率」是一个健康指标——它上升通常意味着格式槽位或模型行为变了，')
print('   而静默修复会把这个信号丢掉（与 C68-02 的「失败分类必须报告比例」同一条）。')"""),

    md("""## ✏️ 练习 1：正确的掩码 vs 位置掩码

第 2 节的 `mask` 用的是「加上它之后仍是某个合法串的前缀」。
一个常见的错误实现是**只看位置**：「这个 token 在某个合法串的第 i 位出现过」。

实现 `mask_local(prefix, valid_set)`（位置掩码）与
`reachable(mask_fn, valid_set, maxlen)`——枚举在这个掩码下**可达的所有完整输出串**。

然后回答一个问题：**位置掩码还能保证输出合法吗？**"""),

    code("""def mask_local(prefix, valid_set):
    \"\"\"错误实现：只看位置，不看前缀是否匹配。\"\"\"
    # TODO
    raise NotImplementedError

def reachable(mask_fn, valid_set, maxlen=12):
    \"\"\"枚举这个掩码下可达的所有完整输出串（以 EOS 结尾的）。\"\"\"
    # TODO：DFS
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def mask_correct(prefix, valid_set):
    pre = set()
    for k in valid_set:
        for i in range(len(k) + 1):
            pre.add(tuple(k[:i]))
    return {t for t in VOCAB if tuple(list(prefix) + [t]) in pre}

# 两个合法集合：一个「所有串结构相同」，一个「结构不同」
VS_SAME = {('{', '"', 'label', '"', ':', '"', v, '"', '}', 'EOS') for v in VALUES}
VS_MIXED = {('{', '"', 'label', '"', ':', '"', 'bug', '"', '}', 'EOS'),
            ('{', '}', 'EOS')}                       # 「没有标签」的短形式

print(f"{'合法集合':<14}{'掩码':<10}{'可达串数':>10}{'其中非法':>10}")
res = {}
for vname, vs in [('结构相同', VS_SAME), ('结构不同', VS_MIXED)]:
    for mname, mf in [('位置掩码', mask_local), ('前缀掩码', mask_correct)]:
        r = reachable(mf, vs)
        bad = r - vs
        res[(vname, mname)] = (len(r), len(bad))
        print(f'{vname:<14}{mname:<10}{len(r):>10}{len(bad):>10}')

# 前缀掩码在两种情况下都只能产生合法串
assert res[('结构相同', '前缀掩码')][1] == 0
assert res[('结构不同', '前缀掩码')][1] == 0
# 位置掩码在「结构相同」时侥幸安全
assert res[('结构相同', '位置掩码')][1] == 0
# 但在「结构不同」时它会产生非法串 —— 保证被破坏
assert res[('结构不同', '位置掩码')][1] > 0, res
bad_examples = sorted(reachable(mask_local, VS_MIXED) - VS_MIXED)
print('\\n位置掩码在「结构不同」时产生的非法串:')
for b in bad_examples:
    print('  ', ' '.join(b))
print('✅ 练习 1 通过：位置掩码**不保证输出合法**')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def mask_local(prefix, valid_set):
    i = len(prefix)
    return {k[i] for k in valid_set if len(k) > i}

def reachable(mask_fn, valid_set, maxlen=12):
    out, seen, stack = set(), set(), [()]
    while stack:
        pre = stack.pop()
        if pre in seen:
            continue
        seen.add(pre)
        if pre and pre[-1] == 'EOS':
            out.add(pre)
            continue
        if len(pre) >= maxlen:
            continue
        for t in mask_fn(pre, valid_set):
            stack.append(tuple(list(pre) + [t]))
    return out

assert reachable(mask_correct, VS_SAME) == VS_SAME
assert reachable(mask_correct, VS_MIXED) == VS_MIXED
assert reachable(mask_local, VS_SAME) == VS_SAME
assert reachable(mask_local, VS_MIXED) - VS_MIXED
print('✅ 参考答案 1 通过')
print('   两种掩码的区别只有一行代码，而后果是**保证本身成立不成立**：')
print('   `mask_local` 问「这个 token 在第 i 位出现过吗」；')
print('   `mask_correct` 问「加上它之后还是某个合法串的前缀吗」。')
print()
print('   注意一个诚实的观察：**在「所有合法串结构相同」时，位置掩码侥幸是安全的**。')
print('   而真实的 schema 几乎总有可选字段、变长数组、联合类型——')
print('   也就是「结构不同」，此时位置掩码会放行')
print('   「{ } label ...」这种把两种形式拼在一起的串。')
print()
print('   **正确实现需要在 FSM 上做一次可达性分析**（哪些状态能到接受态），')
print('   而这正是 Outlines 那条线的核心工程内容。')"""),

    md("""## ✏️ 练习 2：失真到底由什么决定

实现 `distortion(next_dist_fn, valid_pred, maxlen)`：
返回 `dict(kl=..., ratios={value: masked/cond}, invalid_mass=..., argmax_same=bool)`。

然后用它检验两个互相竞争的假设：

- **H1**：失真随「被掩掉的质量」增长（直觉上的答案）
- **H2**：失真只由「分支之间的下游收尾概率差异」决定

实现 `scan_masked_mass(oops_probs)` 与 `scan_tail_spread(q_values)` 分别检验它们。
"""),

    code("""def distortion(next_dist_fn, valid_pred, maxlen=10):
    \"\"\"返回 dict(kl, ratios, invalid_mass, argmax_same)。\"\"\"
    # TODO
    raise NotImplementedError

def make_lm(tails, oops=0.40):
    \"\"\"造一个 next_dist 变体：value 位置的 oops 概率 = oops，
    每个 value 之后的收尾概率 = tails[value]。\"\"\"
    # TODO
    raise NotImplementedError

def scan_masked_mass(oops_probs):
    \"\"\"**尾部同质**（所有 value 的收尾概率相同），扫被掩掉的质量。
    返回 [(oops, invalid_mass, kl)]。\"\"\"
    # TODO
    raise NotImplementedError

def scan_tail_spread(q_values):
    \"\"\"固定 oops，只改 feature 的收尾概率。返回 [(q_feature, kl)]。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
d = distortion(next_dist, is_valid)
print({k: (round(v, 4) if isinstance(v, float) else v)
       for k, v in d.items() if k != 'ratios'})
print('ratios:', {k: round(v, 3) for k, v in d['ratios'].items()})
assert abs(d['kl'] - kl) < 1e-9, (d['kl'], kl)
assert abs(d['invalid_mass'] - invalid_mass) < 1e-9
assert d['argmax_same'] is True

print('\\nH1：失真随被掩掉的质量增长？（尾部同质）')
print(f"{'oops':>7}{'被掩掉的质量':>14}{'KL':>14}")
c1 = scan_masked_mass([0.0, 0.2, 0.4, 0.8])
for op, im, k_ in c1:
    print(f'{op:>7.2f}{im:>14.3f}{k_:>14.8f}')
assert all(abs(k_) < 1e-9 for _, _, k_ in c1), \\
    '尾部同质时 KL 必须恰好为 0，无论掩掉多少'
assert c1[-1][1] > c1[0][1] + 0.2, '被掩掉的质量确实在变（0.56 → 0.91）'
print('  → **H1 被否证**：掩掉的质量从 %.2f 涨到 %.2f，而 KL 恒等于 0。'
      % (c1[0][1], c1[-1][1]))

print('\\nH2：失真由分支之间的收尾概率差异决定？')
print(f"{'q_feature':>11}{'KL':>12}")
c2 = scan_tail_spread([0.60, 0.45, 0.30, 0.15])
for q, k_ in c2:
    print(f'{q:>11.2f}{k_:>12.5f}')
assert c2[0][1] < c2[-1][1], 'KL 随异质度增长'
assert c2[-1][1] > 10 * c2[0][1], f'差距应当很大: {c2[-1][1]} vs {c2[0][1]}'
print('  → **H2 成立**：把 feature 的收尾概率从 %.2f 压到 %.2f，'
      'KL 从 %.4f 涨到 %.4f（%.0f 倍）。'
      % (c2[0][0], c2[-1][0], c2[0][1], c2[-1][1], c2[-1][1] / c2[0][1]))
print('✅ 练习 2 通过：**失真的唯一来源是分支之间的下游收尾能力差异**')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def _enumerate(next_fn, maxlen=10, mask_fn=None):
    out = {}
    def rec(prefix, prob):
        if prefix and prefix[-1] == 'EOS':
            out[tuple(prefix)] = out.get(tuple(prefix), 0.0) + prob
            return
        if len(prefix) >= maxlen:
            return
        d = next_fn(prefix)
        if mask_fn is not None:
            allowed = {t: p for t, p in d.items() if t in mask_fn(prefix)}
            z = sum(allowed.values())
            d = {t: p / z for t, p in allowed.items()} if z > 0 else {}
        for t, p in d.items():
            if p > 0:
                rec(prefix + [t], prob * p)
    rec([], 1.0)
    return out

def distortion(next_dist_fn, valid_pred, maxlen=10):
    uncond = _enumerate(next_dist_fn, maxlen)
    valid = {k: v for k, v in uncond.items() if valid_pred(k)}
    z = sum(valid.values())
    cond = {k: v / z for k, v in valid.items()}
    pre = set()
    for k in valid:
        for i in range(len(k) + 1):
            pre.add(tuple(k[:i]))
    mfn = lambda p: {t for t in VOCAB if tuple(list(p) + [t]) in pre}
    masked = _enumerate(next_dist_fn, maxlen, mask_fn=mfn)
    kl_ = sum(masked[k] * math.log(masked[k] / cond[k])
              for k in masked if masked[k] > 0)
    return dict(kl=kl_, ratios={k[6]: masked[k] / cond[k] for k in masked},
                invalid_mass=1.0 - z,
                argmax_same=(max(masked, key=lambda k: masked[k])
                             == max(cond, key=lambda k: cond[k])))

def make_lm(tails, oops=0.40):
    def nd(prefix):
        p = list(prefix)
        if p == ['{', '"', 'label', '"', ':', '"']:
            base = {'bug': 0.05, 'feature': 0.45, 'other': 0.10}
            s = sum(base.values())
            d = {k: v / s * (1.0 - oops) for k, v in base.items()}
            if oops > 0:
                d['oops'] = oops
            return d
        if len(p) == 7 and p[6] in VALUES + ['oops']:
            q = tails.get(p[6], 0.5)
            return {'"': q, 'EOS': 1 - q}
        return next_dist(prefix)
    return nd

HOMO = {'bug': 0.6, 'feature': 0.6, 'other': 0.6, 'oops': 0.5}

def scan_masked_mass(oops_probs):
    out = []
    for op in oops_probs:
        d = distortion(make_lm(HOMO, oops=op), is_valid)
        out.append((op, d['invalid_mass'], d['kl']))
    return out

def scan_tail_spread(q_values):
    out = []
    for q in q_values:
        d = distortion(make_lm({'bug': 0.90, 'feature': q, 'other': 0.60,
                                'oops': 0.5}), is_valid)
        out.append((q, d['kl']))
    return out

d = distortion(next_dist, is_valid)
assert abs(d['kl'] - kl) < 1e-9 and d['argmax_same'] is True
c1 = scan_masked_mass([0.0, 0.2, 0.4, 0.8])
assert all(abs(k_) < 1e-9 for _, _, k_ in c1)
c2 = scan_tail_spread([0.60, 0.45, 0.30, 0.15])
assert c2[-1][1] > 10 * c2[0][1]
print('✅ 参考答案 2 通过')
print('   这个练习的结论比讲解里那句「掩码 ≠ 条件分布」精确得多，而且更有用：')
print()
print('   **失真的唯一来源是「不同分支之后有多容易合法收尾」的差异。**')
print('   ① 尾部同质时，逐步掩码**恰好等于**条件分布——掩掉 56% 还是 91% 都一样，KL = 0。')
print('      直觉上「语法越紧失真越大」是错的：紧不紧完全不影响失真。')
print('   ② 而收尾概率一有差异，失真立刻出现，并随差异急剧增长。')
print()
print('   实用判据：**如果你的语法在所有分支之后结构相同**')
print('   （枚举一个标签，然后固定地收尾），**失真恰好为 0，可以完全不管它**。')
print('   需要警惕的是联合类型、可选字段、变长数组——')
print('   那里「选了 A 还要写很多、选了 B 马上收尾」，失真就出现了。')"""),

    md("""## ✏️ 练习 3：三条路的成本-偏倚对比表

实现 `compare_strategies(p_parse, n_items, acc_true, cost_per_call, max_retries)`，
对三条路各给出一行：

- `constrain`：调用 1 次，解析率 1.0，无偏
- `retry`：期望调用 `expected_calls(p, R)`，最终失败率 `(1-p)^(R+1)`，
  **报「解析成功子集上的准确率」时有偏**
- `repair`：调用 1 次，解析率 = `p + (1-p) * repair_success`，
  **被修复的样本里有一部分是语义猜测**（用 `semantic_guess_rate` 表示）

返回 `{策略: dict(calls, parse_rate, final_fail, reported_acc, honest_acc, cost)}`。
`reported_acc` 是「解析成功子集上的准确率」，`honest_acc` 是「分母=全部」。"""),

    code("""def compare_strategies(p_parse, n_items=1000, acc_true=0.75, cost_per_call=0.001,
                       max_retries=3, repair_success=0.6, semantic_guess_rate=0.4,
                       seed=0):
    \"\"\"返回 {'constrain'|'retry'|'repair': dict(...)}。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
r = compare_strategies(p_parse=0.6, n_items=2000, acc_true=0.75)
print(f"{'策略':<12}{'调用':>7}{'解析率':>9}{'最终失败':>10}"
      f"{'报的准确率':>12}{'诚实准确率':>12}{'成本':>10}")
for k in ('constrain', 'retry', 'repair'):
    v = r[k]
    print(f"{k:<12}{v['calls']:>7.2f}{v['parse_rate']:>9.2f}{v['final_fail']:>10.2%}"
          f"{v['reported_acc']:>12.2%}{v['honest_acc']:>12.2%}{v['cost']:>10.5f}")

assert r['constrain']['parse_rate'] == 1.0 and r['constrain']['final_fail'] == 0.0
assert r['constrain']['calls'] == 1.0
# 约束是唯一「报的 = 诚实的」策略
assert abs(r['constrain']['reported_acc'] - r['constrain']['honest_acc']) < 1e-9
# 重试：报的准确率高于诚实准确率（选择偏倚）
assert r['retry']['reported_acc'] > r['retry']['honest_acc']
# 重试更贵
assert r['retry']['cost'] > r['constrain']['cost']
# 修复：解析率提高但仍 < 1
assert r['repair']['parse_rate'] > 0.6 and r['repair']['parse_rate'] < 1.0
assert 'semantic_guessed' in r['repair'], '修复必须报告有多少是语义猜测'
assert r['repair']['semantic_guessed'] > 0
print('✅ 练习 3 通过：约束是唯一「解析率 1.0 + 报的即诚实的 + 成本最低」的策略')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def compare_strategies(p_parse, n_items=1000, acc_true=0.75, cost_per_call=0.001,
                       max_retries=3, repair_success=0.6, semantic_guess_rate=0.4,
                       seed=0):
    rng = np.random.default_rng(seed)
    d = rng.random(n_items)
    # 难度同时影响解析与正确 —— 这是偏倚的来源
    thr_parse = np.quantile(d, p_parse)
    parse_ok = d <= thr_parse
    correct = rng.random(n_items) > d * (1 - acc_true) * 2

    out = {}
    # ---- 约束 ----
    out['constrain'] = dict(
        calls=1.0, parse_rate=1.0, final_fail=0.0,
        reported_acc=float(np.mean(correct)), honest_acc=float(np.mean(correct)),
        cost=1.0 * cost_per_call)
    # ---- 重试 ----
    calls = expected_calls(p_parse, max_retries)
    ff = final_failure_rate(p_parse, max_retries)
    out['retry'] = dict(
        calls=calls, parse_rate=1.0 - ff, final_fail=ff,
        reported_acc=float(np.mean(correct[parse_ok])),          # ← 有偏
        honest_acc=float(np.mean(parse_ok & correct)),
        cost=calls * cost_per_call)
    # ---- 修复 ----
    n_fail = int((~parse_ok).sum())
    repaired = rng.random(n_fail) < repair_success
    guessed = repaired & (rng.random(n_fail) < semantic_guess_rate)
    pr = float(parse_ok.mean() + repaired.mean() * (1 - parse_ok.mean()))
    honest = float(np.mean(parse_ok & correct))
    out['repair'] = dict(
        calls=1.0, parse_rate=pr, final_fail=1.0 - pr,
        reported_acc=float(np.mean(correct[parse_ok])),
        honest_acc=honest, cost=1.0 * cost_per_call,
        semantic_guessed=int(guessed.sum()))
    return out

r = compare_strategies(0.6, 2000, 0.75)
assert r['constrain']['parse_rate'] == 1.0
assert abs(r['constrain']['reported_acc'] - r['constrain']['honest_acc']) < 1e-9
assert r['retry']['reported_acc'] > r['retry']['honest_acc']
assert r['retry']['cost'] > r['constrain']['cost']
assert 0.6 < r['repair']['parse_rate'] < 1.0 and r['repair']['semantic_guessed'] > 0
print('✅ 参考答案 3 通过')
print('   这张表是本模块的交付物。约束在四列上同时最优：')
print('   调用 1 次、解析率 1.0、最终失败 0、报的准确率就是诚实的准确率。')
print('   而 repair 那一行的 semantic_guessed 是必须报的一个数——')
print('   它是「有多少个答案其实是我们猜的」，而下游有权知道这个。')"""),

    md("""## ✏️ 练习 4：解码约束的门禁

实现 `decoding_gate(cfg, metrics, baseline)`，规则：

**确定性阻断**
- `cfg['constrained']` 为真但 `metrics['parse_rate'] < 1.0`（逻辑矛盾 → 实现有 bug）
- `cfg['schema_source'] != cfg['parser_source']`（schema 与解析器不同源）
- schema 里有 `required` 但 `cfg['mask_features']` 里没有 `'required'`
- schema 里有区间约束（`minimum`/`maximum`）但 `cfg['post_validate']` 为假

**统计阻断**
- `metrics['repair_rate']` 或 `metrics['retry_rate']` 相对基线上升超过 `2*sigma`

**报警**
- `metrics['repair_rate'] > 0` 且高于基线（格式槽位或模型行为变化的早期信号）
- `cfg['constrained']` 且 `cfg['use_logprob_as_confidence']`（第 3/4 节的失真）"""),

    code("""def decoding_gate(cfg, metrics, baseline, sigma=0.01):
    \"\"\"返回 (blocking, warnings)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
CFG_OK = dict(constrained=True, schema_source='pydantic:Classification',
              parser_source='pydantic:Classification',
              mask_features=['enum', 'required', 'type'],
              post_validate=True, use_logprob_as_confidence=False,
              schema=SCHEMA)
M_OK = dict(parse_rate=1.0, repair_rate=0.0, retry_rate=0.0)
BASE_M = dict(parse_rate=1.0, repair_rate=0.0, retry_rate=0.0)

assert decoding_gate(CFG_OK, M_OK, BASE_M) == ([], []), \\
    decoding_gate(CFG_OK, M_OK, BASE_M)

# a) 启用约束但解析率 < 1 → 逻辑矛盾
b, _ = decoding_gate(CFG_OK, {**M_OK, 'parse_rate': 0.97}, BASE_M)
assert any('矛盾' in x or 'parse_rate' in x for x in b), b

# b) schema 与解析器不同源
b2, _ = decoding_gate({**CFG_OK, 'parser_source': 'handwritten'}, M_OK, BASE_M)
assert any('同源' in x or '不一致' in x for x in b2), b2

# c) required 没实现
b3, _ = decoding_gate({**CFG_OK, 'mask_features': ['enum', 'type']}, M_OK, BASE_M)
assert any('required' in x for x in b3), b3

# d) 有区间但没有生成后校验
b4, _ = decoding_gate({**CFG_OK, 'post_validate': False}, M_OK, BASE_M)
assert any('区间' in x or 'validate' in x for x in b4), b4

# e) 修复率上升 → 阻断 + 报警
b5, w5 = decoding_gate(CFG_OK, {**M_OK, 'repair_rate': 0.08}, BASE_M)
assert b5 and w5, (b5, w5)

# f) 把 logprob 当置信度 → 报警（不阻断）
b6, w6 = decoding_gate({**CFG_OK, 'use_logprob_as_confidence': True}, M_OK, BASE_M)
assert b6 == [] and any('置信度' in x or 'logprob' in x for x in w6), (b6, w6)
print('✅ 练习 4 通过：四项确定性阻断 + 统计阻断 + 两项报警')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def decoding_gate(cfg, metrics, baseline, sigma=0.01):
    blocking, warn = [], []
    if cfg.get('constrained') and metrics['parse_rate'] < 1.0:
        blocking.append(f"启用了约束但 parse_rate = {metrics['parse_rate']:.2f} < 1.0"
                        f"——这是逻辑矛盾，掩码实现有 bug")
    if cfg.get('schema_source') != cfg.get('parser_source'):
        blocking.append(f"schema 与解析器不同源: {cfg.get('schema_source')} "
                        f"vs {cfg.get('parser_source')}")
    schema = cfg.get('schema', {})
    if schema.get('required') and 'required' not in cfg.get('mask_features', []):
        blocking.append('schema 里有 required，但掩码没实现它')
    has_range = any('minimum' in v or 'maximum' in v
                    for v in schema.get('properties', {}).values())
    if has_range and not cfg.get('post_validate'):
        blocking.append('schema 里有区间约束，但没有生成后校验'
                        '（区间无法用逐步掩码表达）')
    for key in ('repair_rate', 'retry_rate'):
        rise = metrics.get(key, 0.0) - baseline.get(key, 0.0)
        if rise > 2 * sigma:
            blocking.append(f'{key} 相对基线上升 {rise:.1%} > 2σ')
    if metrics.get('repair_rate', 0.0) > 0 and \\
            metrics['repair_rate'] > baseline.get('repair_rate', 0.0):
        warn.append(f"修复率 {metrics['repair_rate']:.1%} 高于基线"
                    f"——格式槽位或模型行为可能变了")
    if cfg.get('constrained') and cfg.get('use_logprob_as_confidence'):
        warn.append('把掩码后的 logprob 当置信度——它不是条件概率（讲解第 3/4 节）')
    return blocking, warn

assert decoding_gate(CFG_OK, M_OK, BASE_M) == ([], [])
assert decoding_gate(CFG_OK, {**M_OK, 'parse_rate': 0.97}, BASE_M)[0]
assert decoding_gate({**CFG_OK, 'parser_source': 'handwritten'}, M_OK, BASE_M)[0]
assert any('required' in x for x in
           decoding_gate({**CFG_OK, 'mask_features': ['enum', 'type']}, M_OK, BASE_M)[0])
assert decoding_gate({**CFG_OK, 'post_validate': False}, M_OK, BASE_M)[0]
b6, w6 = decoding_gate({**CFG_OK, 'use_logprob_as_confidence': True}, M_OK, BASE_M)
assert b6 == [] and w6
print('✅ 参考答案 4 通过')
print('   第一项检查最值得记住：**「启用了约束但解析率不是 1.0」是一个逻辑矛盾**。')
print('   约束的定义就是不合法输出不可能产生，所以它出现时一定是实现有 bug——')
print('   掩码漏了某条规则，或者约束根本没生效。这是一个零误报的检查。')
print()
print('   最后那条报警也值得记住：它把讲解第 3 节那个抽象的分布失真')
print('   变成了一个可以在配置层面拦住的具体风险。')"""),

    md("""## 🧪 真实工程胶囊：受限解码的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 首选：让推理栈做（讲解第 2/4 节）
# ══════════════════════════════════════════════════════════════════
# Outlines
from outlines import models, generate
model = models.transformers('...')
gen = generate.json(model, Classification)        # ← 从 pydantic 直接编译约束
result = gen(prompt)                              # 类型上就是 Classification

# llama.cpp / vLLM：GBNF 或 JSON schema
#   llama-cli --grammar-file schema.gbnf
#   vLLM: SamplingParams(guided_decoding=GuidedDecodingParams(json=SCHEMA))

# HuggingFace 原生：LogitsProcessor（C50 讲接口）
class GrammarProcessor(LogitsProcessor):
    def __call__(self, input_ids, scores):
        allowed = self.fsm.allowed_tokens(self.state)      # ← 预计算+缓存
        m = torch.full_like(scores, float('-inf'))
        m[:, list(allowed)] = 0.0
        return scores + m

# ══════════════════════════════════════════════════════════════════
# B. schema / 掩码 / 解析器**同源生成**（讲解第 4 节 / 练习 4）
# ══════════════════════════════════════════════════════════════════
class Classification(BaseModel):
    label: Literal['bug', 'feature', 'billing', 'account', 'other']
    confidence: float = Field(ge=0.0, le=1.0)

SCHEMA = Classification.model_json_schema()     # → 给模型 / 编译掩码
parse = Classification.model_validate_json      # → 解析 + 不变量校验
#   **区间约束（ge/le）掩码表达不了，所以 model_validate 这一步不能省。**

# ══════════════════════════════════════════════════════════════════
# C. 只对 API 模型可用时（拿不到 logits）
# ══════════════════════════════════════════════════════════════════
# 1) 用服务方的 structured output / tool-calling（它们内部就是约束）
# 2) 拿不到时：把可约束的部分拆成独立字段，自由文本部分用**语法层**修复兜底
# 3) 仍然失败才重试（带温度扰动 + 上限 + 记录次数），报分分母仍是全部样本

# ══════════════════════════════════════════════════════════════════
# D. 打点（讲解第 5/6 节）
# ══════════════════════════════════════════════════════════════════
log.info('decode', extra=dict(
    constrained=True, parse_ok=True,
    repaired=did_repair, repair_kind='fence_strip',      # ← 修复必须记录
    semantic_guess=False,                                # ← 语义猜测单独统计
    retries=n_retries, prompt_fp=FP))
# 看板：parse_rate / repair_rate / retry_rate / semantic_guess_rate
#   repair_rate 上升 = 格式槽位或模型行为变了（早期信号）

# ══════════════════════════════════════════════════════════════════
# E. 一条容易忘的纪律（讲解第 3/4 节）
# ══════════════════════════════════════════════════════════════════
# 在「采样多个候选」「自一致性投票」「把 logprob 当置信度」这三类场景下，
# **不要把掩码后的概率当条件概率**。它偏向「容易开头但不容易收尾」的分支。
# 温度 0 取 argmax 时通常不受影响。
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| 约束是唯一能把解析率**保证**到 1.0 的路 | 而重试与修复都不能保证 | 讲解 1 |
| 掩码必须由「合法前缀」定义，不能只看局部转移 | 后者必然产生死局 | 第 2 节 / 练习 1 |
| **逐步掩码 ≠ 条件分布** | KL = 0.081 nat；`bug` 被低估 2.3 倍 | 第 3 节 |
| 失真的机制：掩码看不见「分支的收尾能力」 | bug: 被选 0.05 但收尾 0.90 | 第 3 节 |
| **失真只由分支的收尾能力差异决定，与掩掉多少质量无关** | 尾部同质时 KL 恰好为 0（掩掉 56%~91% 都一样） | 练习 2 |
| 温度 0 取 argmax 时失真通常不影响结果 | 这解释了为什么它很少被发现 | 第 4 节 |
| 采样/置信度场景下失真重要 | 采样分布差 0.19；置信度高估 33% | 第 4 节 |
| 区间约束无法用逐步掩码表达 | 所以不变量校验不能被约束替代 | 第 5 节 |
| 重试的期望调用是 $1/p$ | p=0.175 → 5.7 次 vs 约束的 1 次 | 第 6 节 |
| 重试的偏倚源于解析成功与答对正相关 | 报的准确率高于诚实准确率 | 第 6 节 |
| 修复只能做语法层，不能做语义猜测 | `unknown → bug` 把「不知道」伪装成答案 | 第 7 节 |
| 「启用约束但解析率 < 1.0」是逻辑矛盾 | 零误报的检查 | 练习 4 |

下一模块：**05 · 提示的运维与跨模型迁移**——
prompt 是会随模型失效的资产，它需要版本、指纹、回归门禁与迁移流程。"""),
]
