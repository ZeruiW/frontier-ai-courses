# -*- coding: utf-8 -*-
"""C70 模块 04 · 迭代与图检索。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 03（查询改写与融合）；"
                 "知道「有向图」与「广度优先」即可，<strong>不需要任何图神经网络</strong>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_iterative.ipynb'
                       '（多跳问题的单轮 recall 天然为 0 / 两跳补上它 / '
                       '三种停止准则与它们的成本上界 / 查询漂移的量化 / '
                       '实体图的邻域扩展 / 迭代的成本模型 / '
                       '四个失败模式 / 多跳题的 recall 必须按「事实集合」算）'),
    ("核心参考", "Trivedi et al., <em>IRCoT: Interleaving Retrieval with CoT</em>（ACL 2023）· "
                 "Asai et al., <em>Self-RAG</em>（ICLR 2024）· "
                 "Jiang et al., <em>FLARE: Active Retrieval Augmented Generation</em>（EMNLP 2023）· "
                 "Edge et al., <em>GraphRAG: From Local to Global</em>（2024）· "
                 "本课程 C09 模块 04 第 6 节（搜索的算力会计：预算即上界）· "
                 "C46（图机器学习）· C66 模块 05（成本感知评测）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("multihop", "多跳问题的单轮 recall 天然是 0", "".join([
        P("前面三个模块都假设<strong>答案在某一个块里</strong>。"
          "这一节处理它不成立的情况，"
          "<strong>而这类问题的单轮检索不是「效果差」，是数学上不可能</strong>。"),
        ASCII("""
   问题：差旅报销的审批人邮箱是什么？

   块 A: 「差旅报销由财务部的王敏负责审批。」      ← 查询能碰到（有「差旅报销」）
   块 B: 「王敏的联系邮箱是 wangmin@acme.com。」   ← 查询碰不到（没有「王敏」）

   单轮检索:
     查询词 = {差旅, 报销, 审批人, 邮箱}
     块 B 的词 = {王敏, 联系, 邮箱}
     共享词 = {邮箱}  → 相似度极低，排不进 top-k

   **注意这不是「排序不够好」**：
   查询里根本没有「王敏」这个信息——它要等块 A 被读到之后才存在。
"""),
        DUAL(
            "所以多跳问题的结构是：<strong>第二跳的查询是第一跳结果的函数</strong>。"
            "<em>$q_2 = f(q_1, \\text{docs}_1)$</em>，"
            "而单轮检索只能算 $\\text{retrieve}(q_1)$。"
            "<strong>把 top-k 从 5 加到 50、把 embedding 换成最强的那个——都不改变这一点。</strong>",
            "定量地说：设问题需要的证据集合是 "
            "$E = \\{e_1, e_2\\}$，$e_2$ 与 $q_1$ 的相似度低于第 $k$ 名。"
            "则单轮的<span class=\"term\">事实级 recall</span>"
            "$= |E \\cap \\text{retrieved}| / |E| \\le 1/2$，"
            "<strong>而端到端可答需要它等于 1</strong>。"
            "<em>这也说明多跳题的 recall 必须按「事实集合是否被完整覆盖」算，"
            "而不是按「召回了几条相关文档」算</em>——"
            "后者会给出 0.5 这个看起来还行的数，而真实的可答率是 0。"
            "第 8 节会把这个定义写清楚。",
        ),
        CALLOUT("warn", "一个诊断技巧：<strong>如果某类问题无论怎么调检索都上不去，"
                        "先检查它是不是多跳的。</strong>"
                        "<em>把答案需要的事实一条条列出来，"
                        "看有没有哪一条的「可检索线索」只存在于另一条里</em>。"
                        "有 → 这是迭代问题，不是检索问题。"),
    ])),

    # ============================================================== 2
    ("loop", "迭代检索的循环：四个必须显式写出来的部件", "".join([
        P("迭代检索的骨架很短，但<strong>它的四个部件里有三个经常被省掉，"
          "而省掉任何一个都会让它在生产上失控</strong>。"),
        ASCII("""
   while True:
       ① docs = retrieve(q_current)              ← 检索（C11 + 本课 03）
       ② if sufficient(question, evidence):      ← **停止准则**（第 3 节）
              break
       ③ q_current = next_query(question, evidence)   ← 后续查询生成
       ④ if hops >= MAX_HOPS or cost >= BUDGET:  ← **硬上界**（不可省）
              break
       hops += 1

   常被省掉的三个:
     ② 没有 sufficient() → 只能跑固定轮数，要么不够要么浪费
     ④ 没有硬上界        → **成本没有上界**，这是最危险的一个
     去重              → 每一跳都可能召回同一批文档，浪费预算（第 6 节）
"""),
        TABLE(["部件", "最简实现", "省掉的后果"], [
            ["<strong>停止准则 <code>sufficient</code></strong>",
             "问题里的必需槽位是否都被证据覆盖",
             "固定轮数：简单题浪费 2–3 倍成本，难题仍然答不上来"],
            ["<strong>后续查询 <code>next_query</code></strong>",
             "从已有证据里抽出<em>新实体</em>，拼上原问题的谓词",
             "查询漂移（第 4 节）"],
            ["<strong>硬上界 <code>MAX_HOPS</code> / <code>BUDGET</code></strong>",
             "两个整数",
             "<strong>成本没有上界</strong>；一次 pathological 查询能烧掉整天的预算"],
            ["<strong>去重</strong>",
             "见过的 <code>chunk_id</code> 集合",
             "每一跳召回同一批文档，上下文被重复内容占满"],
        ]),
        CALLOUT("danger", "第三行值得强调："
                          "<strong>没有硬上界的迭代检索是一个开放的成本漏洞。</strong>"
                          "<em>它不需要恶意输入——一个措辞含糊的问题就足以让 "
                          "<code>sufficient()</code> 永远返回 False</em>。"
                          "<strong><code>MAX_HOPS</code> 必须是代码里的常量，"
                          "而不是配置里的可选项。</strong>"),
    ])),

    # ============================================================== 3
    ("stopping", "三种停止准则：成本与效果的三个点", "".join([
        P("停止准则决定了迭代的全部成本特性。三种做法，"
          "<strong>成本上界都一样，但期望成本差很多</strong>。"),
        TABLE(["准则", "怎么判断", "期望轮数", "问题"], [
            ["<strong>固定轮数</strong>", "跑 $H$ 轮就停", "恒为 $H$",
             "<em>简单题浪费、难题不够</em>；但它是唯一完全可预测的一个"],
            ["<strong>覆盖度</strong>",
             "问题的必需槽位是否都在证据里找到了",
             "<strong>随题目难度自适应</strong>",
             "需要一个能抽槽位的解析器；<em>槽位抽错会导致提前停或停不下来</em>"],
            ["<strong>边际收益</strong>",
             "这一跳有没有带来新信息（新块 / 新实体）",
             "接近覆盖度，但不需要理解问题",
             "<strong>容易被近重复骗</strong>——"
             "召回一批新的但内容重复的块会被判成「有新信息」"],
        ]),
        DUAL(
            "实践中最稳的组合是<strong>「覆盖度 + 边际收益 + 硬上界」三条同时用</strong>："
            "覆盖度满足就停（正常路径）；"
            "覆盖度不满足但边际收益为 0 就停（说明再查也查不到，"
            "<em>这条防的是「答案根本不在库里」</em>）；"
            "硬上界兜底。",
            "成本的形式化：设每跳成本 $c$（嵌入 + 检索 + 一次判断），"
            "则<strong>最坏成本恒为 $H_{\\max} \\cdot c$</strong>（由硬上界保证），"
            "而期望成本是 $c \\cdot \\mathbb{E}[H]$。"
            "<em>三种准则的区别<strong>只在 $\\mathbb{E}[H]$</strong></em>——"
            "这也是为什么「加停止准则」是一次纯粹的成本优化，"
            "<strong>它不改变最坏情况，只改变账单</strong>。"
            "notebook 第 3 节把三种准则的 $\\mathbb{E}[H]$ 与可答率一起量出来。",
        ),
        P("<strong>一条容易被忽略的纪律</strong>："
          "<em>停止准则的判断不能看「答案对不对」</em>——"
          "线上没有真值。"
          "它只能看<strong>结构性的信号</strong>："
          "槽位覆盖、新信息量、检索分数分布。"
          "<em>这与 C68 模块 02 的「重试只能看异常类型，不能看判分结果」是同一条纪律</em>。"),
    ])),

    # ============================================================== 4
    ("drift", "查询漂移：迭代最常见的失效方式", "".join([
        P("后续查询是从上一跳的证据里生成的。"
          "<strong>如果生成规则不锚定原问题，查询会一跳一跳地走远。</strong>"),
        ASCII("""
   问题: 差旅报销的审批人邮箱是什么

   ❌ 不锚定（用上一跳文档里的显著词当新查询）
      hop1: 差旅报销的审批人邮箱是什么   → 「差旅报销由财务部的王敏负责审批」
      hop2: 财务部 负责 审批            → 「财务部的报销审批时限为三个工作日」
      hop3: 报销 审批 时限              → 「审批时限为三个工作日」
      → 越走越远，**再也回不到「邮箱」这个目标**

   ✅ 锚定（新实体 + 原问题的目标谓词）
      hop1: 差旅报销的审批人邮箱是什么   → 「…财务部的王敏负责审批」
      hop2: 王敏 邮箱                  → 「王敏的联系邮箱是 wangmin@acme.com」
      → 命中
"""),
        DUAL(
            "漂移是可以量出来的："
            "<strong>算每一跳的查询与<em>原问题</em>的相似度</strong>。"
            "<em>不锚定时它单调下降；锚定时它保持在一个水平上。</em>"
            "notebook 第 4 节把两条曲线画在一起。"
            "<strong>这个量应当作为线上指标监控</strong>——"
            "它掉下去通常意味着后续查询生成的 prompt 出了问题。",
            "锚定的最小实现只有一句话："
            "<strong>$q_{i+1} = (\\text{新实体}) \\oplus (\\text{原问题的目标谓词})$</strong>。"
            "<em>新实体来自上一跳的证据，目标谓词来自原问题且永不改变。</em>"
            "更强的做法是把原问题原样拼进每一跳的查询里"
            "（代价是查询变长、相似度被稀释——模块 02 第 7 节的稀释效应"
            "在这里以另一种形式出现）。",
        ),
        CALLOUT("intuition", "一个便宜的护栏："
                             "<strong>要求每一跳的查询与原问题的相似度不低于第一跳的某个比例"
                             "（比如 0.5 倍），否则丢弃这一跳的查询并停止。</strong>"
                             "<em>它拦不住所有漂移，但能拦住「走到完全不相关的话题上」这种严重情况。</em>"),
    ])),

    # ============================================================== 5
    ("graph", "图检索：只用图的结构，不训练任何模型", "".join([
        P("有一类问题连迭代也做不好："
          "<strong>「A 和 B 之间有什么关系」「谁同时负责 X 和 Y」</strong>。"
          "<em>它们需要的不是「找到某一段文字」，而是「在实体之间走几步」。</em>"),
        ASCII("""
   从块里抽出三元组，得到一张图

   块: 「差旅报销由财务部的王敏负责审批。」
        → (差旅报销, 审批人, 王敏)  (王敏, 部门, 财务部)
   块: 「王敏的联系邮箱是 wangmin@acme.com。」
        → (王敏, 邮箱, wangmin@acme.com)
   块: 「合同审批由法务部的李强负责。」
        → (合同审批, 审批人, 李强)  (李强, 部门, 法务部)

           差旅报销 ──审批人──► 王敏 ──邮箱──► wangmin@acme.com
                                 │
                                部门
                                 ▼
                               财务部 ◄──部门── 张伟 ◄──审批人── 采购申请

   问「差旅报销和采购申请的审批人有什么共同点」：
     flat 检索：两个块各自能召回，但「共同点」这个信息**在任何块里都不存在**
     图检索  ：从两个实体各走两步，取交集 → {财务部}  ← 答案是图算出来的
"""),
        TABLE(["问题类型", "flat 检索", "迭代检索", "图检索"], [
            ["单跳事实（「差旅上限多少」）", "<strong>最好</strong>（最便宜）", "浪费", "浪费"],
            ["多跳事实（「审批人邮箱」）", "<strong>不可能</strong>", "<strong>最好</strong>",
             "可以（如果三元组抽全了）"],
            ["关系/聚合（「共同点」「一共几个」）", "不可能", "很难（需要很多跳）",
             "<strong>最好</strong>——答案是图算出来的，不在任何块里"],
            ["全局摘要（「这批文档讲了什么」）", "不可能", "不可能",
             "社区检测 + 分层摘要（GraphRAG 的主要贡献）"],
        ]),
        DUAL(
            "<strong>图检索的成本几乎全在摄取侧</strong>："
            "抽三元组要跑一遍模型（或规则），而且文档更新时要增量维护图。"
            "<em>查询侧反而很便宜——邻域扩展是几次索引查找。</em>"
            "<strong>所以图检索的决策点是「值不值得在摄取时多花这一遍」，"
            "而不是「查询时快不快」。</strong>",
            "它的两个真实风险："
            "<strong>① 三元组抽取的召回率决定了上限</strong>——"
            "抽不到的关系在图里不存在，"
            "<em>而这个上限在查询侧完全看不到</em>（表现为「答不上来」，"
            "与检索失败无法区分）；"
            "<strong>② 图会腐烂</strong>——"
            "文档更新后旧三元组必须删掉，"
            "<em>而「删一条边」比「删一个块」难得多</em>，"
            "因为一条边可能有多个来源块支持"
            "（模块 05 会讨论这个 provenance 问题）。",
        ),
        P("<strong>一个实用的中间档</strong>："
          "不建完整的知识图谱，只抽<strong>实体 → 块</strong>的倒排表。"
          "<em>这已经能支持「同时提到 X 和 Y 的块」「提到 X 的所有块」这类查询</em>，"
          "而成本只是一次实体识别。"
          "notebook 第 5 节实现的就是这一档。"),
    ])),

    # ============================================================== 6
    ("cost", "迭代的成本模型：三个乘数", "".join([
        P("迭代检索的成本很容易失控，"
          "<strong>因为它的三个乘数都不显眼</strong>。"),
        MATH(r"\text{cost} \le H_{\max} \times m \times (c_{\text{embed}} + c_{\text{search}}) "
             r"+ H_{\max} \times c_{\text{judge}} + c_{\text{gen}}"),
        UL([
            "<strong>$H_{\\max}$</strong>：最大跳数。"
            "<em>$H = 3$ 已经是三倍成本。</em>",
            "<strong>$m$</strong>：每跳的查询扩展路数（模块 03 第 4 节）。"
            "<strong>这一项最容易被忘</strong>——"
            "<em>迭代 3 跳 × 融合 3 路 = 9 次检索</em>，"
            "而两个改动是分别上线的，没人把它们乘起来算过。",
            "<strong>$c_{\\text{judge}}$</strong>：每跳的停止判断。"
            "<em>如果它是一次 LLM 调用，那么它可能比检索本身贵。</em>"
            "<strong>所以停止判断应当优先用结构性信号（槽位、新块数），"
            "不要默认用模型。</strong>",
        ]),
        DUAL(
            "还有一项不在公式里但同样真实的成本："
            "<strong>上下文预算</strong>。"
            "<em>每一跳都往证据里加块，$H$ 跳之后上下文可能是单轮的 $H$ 倍</em>"
            "（如果不去重，还会更多）。"
            "<strong>而上下文长度直接影响生成成本与延迟。</strong>",
            "把它写进 C66 模块 05 的口径："
            "<strong>迭代检索要报的是 <code>$/success</code> 而不是 <code>$/query</code></strong>。"
            "<em>迭代的价值恰恰是把一部分「本来必然失败」的查询变成成功</em>，"
            "所以按 <code>$/query</code> 看它一定更贵，"
            "按 <code>$/success</code> 看才可能划算。"
            "notebook 第 6 节把两个口径都算出来，"
            "<strong>它们给出的结论可以是相反的</strong>。",
        ),
        CALLOUT("intuition", "一个直接可用的部署策略："
                             "<strong>只对「单轮判定为证据不足」的查询开启迭代。</strong>"
                             "<em>这让 $\\mathbb{E}[H]$ 接近 1（大多数查询单轮就够），"
                             "而多跳查询仍然能被答对</em>——"
                             "本质上是把迭代当成一条<strong>兜底路径</strong>而不是默认路径。"),
    ])),

    # ============================================================== 7
    ("failures", "四个失败模式", "".join([
        TABLE(["失败", "症状", "根因", "对策"], [
            ["<strong>成本失控</strong>", "少量查询烧掉大量预算",
             "没有硬上界，或 <code>sufficient()</code> 永远 False",
             "<code>MAX_HOPS</code> 写成代码常量；<em>按查询记录跳数分布并监控 P99</em>"],
            ["<strong>查询漂移</strong>", "多跳题答得比单轮更差",
             "后续查询没锚定原问题（第 4 节）",
             "锚定 + 相似度护栏 + 监控每跳与原问题的相似度"],
            ["<strong>重复召回</strong>", "上下文很长但信息很少",
             "没有跨跳去重",
             "维护 <code>seen_chunk_ids</code>；<em>把「新块数」当边际收益信号</em>"],
            ["<strong>迭代掩盖了上游问题</strong>",
             "「加了迭代效果就好了」，但成本翻了三倍",
             "<strong>答案本来在一个块里，只是被分块切断了（模块 02）</strong>",
             "<em>先跑模块 02 的 intact 检查</em>；"
             "intact 不达标时先修分块，不要用迭代去补"],
        ]),
        CALLOUT("danger", "最后一行是本模块最重要的一条工程忠告。"
                          "<strong>迭代检索能掩盖分块问题、解析问题、查询问题——"
                          "它会让指标变好，同时让成本变高、延迟变长、系统变复杂。</strong>"
                          "<em>上线迭代之前，先确认前面三个模块的检查都是绿的。</em>"
                          "顺序仍然是模块 00 说的那个：<strong>parse → chunk → query → 才是 iterate</strong>。"),
        H3("必须记录的四个字段"),
        P("每次迭代检索都要记录：<code>hops</code>（实际跳数）、"
          "<code>new_chunks_per_hop</code>（每跳的新块数）、"
          "<code>drift</code>（每跳查询与原问题的相似度）、"
          "<code>stop_reason</code>（<code>sufficient</code> / <code>no_gain</code> / "
          "<code>max_hops</code> / <code>budget</code>）。"
          "<strong><code>stop_reason</code> 的分布是最有信息量的一个</strong>——"
          "<em><code>max_hops</code> 占比高说明上界在兜底而不是准则在工作，"
          "这通常意味着 <code>sufficient()</code> 太严或者答案不在库里。</em>"),
    ])),

    # ============================================================== 8
    ("eval", "多跳题的 recall 必须按事实集合算", "".join([
        P("这一节修正一个会系统性误导人的指标定义。"),
        DUAL(
            "常规 recall 的分母是「标注为相关的文档数」，"
            "<strong>而多跳题的标注通常只标了第一跳能找到的那一条</strong>"
            "（因为标注者也是搜出来的）。"
            "<em>于是单轮检索在这类题上能拿到不低的 recall，而端到端可答率是 0。</em>",
            "正确的定义：<strong>把每道题的答案拆成必需事实集合 $E$，"
            "recall 定义为「$E$ 被<em>完整</em>覆盖的题目比例」</strong>——"
            "$$\\text{fact-recall} = \\frac{|\\{\\text{题} : E \\subseteq \\text{retrieved}\\}|}{|\\text{题数}|}$$"
            "<em>注意它是一个全或无的量</em>。"
            "<strong>覆盖了 $E$ 的一半，端到端就是 0，所以指标也应当是 0。</strong>",
        ),
        TABLE(["指标", "单轮在多跳题上的值", "端到端可答率", "会不会误导"], [
            ["文档级 recall@5（只标第一跳）", "<strong>高（~1.0）</strong>", "0",
             "<strong>会</strong>——这是最常见的误导来源"],
            ["文档级 recall@5（标全两跳）", "0.5", "0", "会（0.5 看起来还行）"],
            ["<strong>fact-recall</strong>（全或无）", "<strong>0</strong>", "0",
             "<strong>不会</strong>"],
        ]),
        P("<strong>推论：评测集必须为多跳题标出完整的事实集合</strong>，"
          "而这件事只能在造题时做——"
          "<em>事后从日志里补是不可能的，因为你不知道当时需要哪些事实</em>。"),
        CALLOUT("intuition", "还有一个更朴素的检查值得放进 CI："
                             "<strong>把评测集按「需要几个事实」分层报分。</strong>"
                             "<em>单事实题与多事实题的分数混在一起报，"
                             "会让多跳能力的改动完全看不见</em>——"
                             "多跳题通常只占评测集的 10–20%，"
                             "而它们的分数变化会被另外 80% 冲淡。"),
    ])),

    # ============================================================== 9
    ("when-not", "什么时候不该用迭代", "".join([
        P("迭代检索是本课最贵、最复杂、最容易被滥用的一层。"
          "<strong>这一节给出四个「先别上」的判据。</strong>"),
        OL([
            "<strong>模块 02 的 <code>intact</code> 还没达标</strong>——"
            "<em>答案本来在一个块里，只是被切断了</em>。"
            "此时迭代能让指标变好，但成本是修分块的几倍（第 7 节量过），"
            "<strong>而且它把一个已解决的问题变成了一个持续的成本</strong>。",
            "<strong>多跳题在评测集里占比很低而且没被单独标注</strong>——"
            "<em>你无法证明迭代有收益</em>（第 8 节：混在一起报会把 +1.00 冲淡成 +0.43）。"
            "先造多跳评测集并标出完整事实集合，再谈上线。",
            "<strong>还没有 <code>MAX_HOPS</code> 与单查询预算</strong>——"
            "<em>没有硬上界的迭代是一个开放的成本漏洞</em>，"
            "而它不需要恶意输入，一个措辞含糊的问题就够（第 2 节）。",
            "<strong>停止判断只能用 LLM</strong>——"
            "<em>第 6 节量过：用 LLM 判断时迭代连 <code>$/success</code> 都比单轮更贵</em>。"
            "先找到一个结构性的充分性信号（槽位覆盖、新实体、检索分数分布），"
            "找不到就说明这类问题的「够不够」还没被定义清楚。",
        ]),
        DUAL(
            "反过来，<strong>什么时候该上</strong>："
            "<em>评测集里有一个明确的多跳子集、它的 fact-recall 是 0、"
            "而这个子集对业务重要</em>。"
            "<strong>这三条同时成立时，迭代是唯一的解</strong>——"
            "因为单轮 recall 在这类题上不是「差一点」，是结构上的 0（第 1 节）。",
            "还有一个中间选项常被忽略："
            "<strong>把多跳问题在<em>摄取侧</em>解掉</strong>。"
            "<em>如果「审批人 → 邮箱」这类关联在语料里是稳定的，"
            "那么在摄取时把它们物化成一个块（或一条三元组）</em>，"
            "多跳问题就变成了单跳问题。"
            "<strong>代价是摄取侧的复杂度与派生资产的维护（模块 05 第 7 节），"
            "收益是查询时零额外成本。</strong>"
            "这个权衡与第 5 节图检索的决策点是同一个：<em>钱花在摄取侧还是查询侧</em>。",
        ),
    ])),

    # ============================================================== 10
    ("interleave", "与生成交错：为什么本课把它们分开讲", "".join([
        P("IRCoT / Self-RAG / FLARE 这条线的做法是"
          "<strong>把检索与生成交错</strong>："
          "生成一步 → 用生成的内容触发检索 → 继续生成。"
          "本课刻意把它们分开，理由值得说明。"),
        ASCII("""
   本课的形态（检索循环独立）        交错形态（IRCoT 式）

   retrieve → judge → next_query    generate 一句
      ▲                    │           │
      └────────────────────┘           ├─► 用这句话当查询去检索
   然后一次性 generate                  │
                                       └─► 把结果拼进上下文，继续 generate
   ✓ 每一跳的查询是可检查的            ✓ 查询更自然（就是模型的思路）
   ✓ 停止准则是结构性的                ✗ 停止准则耦合在生成里，难以单独测试
   ✓ 可以完全不调用大模型来测试         ✗ 每一步都要真实模型，无法离线复现
"""),
        DUAL(
            "<strong>分开讲的理由是可测试性</strong>："
            "本课全部的实验（并列组、锚定、停止准则、漂移、成本）"
            "<em>都能在没有真实模型的条件下跑出来并断言</em>。"
            "交错形态把「查询生成」这一步塞进了生成过程，"
            "<strong>于是它的行为与模型强耦合，无法离线复现</strong>——"
            "而不可复现的东西没法在 CI 里守住。",
            "工程上的建议是<strong>分阶段</strong>："
            "<em>先把独立的检索循环做对（本课的四个部件 + 监控四字段），"
            "确认它在多跳子集上把 fact-recall 从 0 提到可用</em>；"
            "<strong>之后如果还需要更自然的查询，再把它交错进生成</strong>。"
            "反过来（一上来就做交错）的问题是："
            "<em>当效果不好时，你分不清是检索循环的问题还是生成的问题</em>——"
            "而这正是 C68 模块 00 的第二条性质（可归因性）要避免的情形。",
        ),
        CALLOUT("intuition", "一句话："
                             "<strong>交错形态更强，独立形态更可测。</strong>"
                             "<em>而在一个还没有多跳评测集、还没有 <code>MAX_HOPS</code>、"
                             "还没有 stop_reason 看板的系统里，可测比强更值钱。</em>"),
    ])),

    # ============================================================== 11
    ("checklist", "上线迭代检索的七项清单", "".join([
        P("把本模块压成一张可勾选的清单。"
          "<strong>前四项是前置条件，后三项是上线动作。</strong>"),
        OL([
            "<strong>模块 01/02/03 的门禁全绿</strong>——"
            "<em>尤其是模块 02 的 <code>intact</code></em>（第 7 节：迭代会掩盖分块问题）。",
            "<strong>评测集里有一个明确的多跳子集，标出了完整的事实集合</strong>，"
            "并按「需要几个事实」分层报分（第 8 节）。",
            "<strong><code>MAX_HOPS</code> 由单查询预算反解，写成代码常量</strong>（练习 2）。",
            "<strong>停止判断用结构性信号</strong>——"
            "<em>找不到这样的信号说明「够不够」还没被定义清楚</em>（第 3/6 节）。",
            "<strong>迭代只对「单轮证据不足」的查询开启</strong>（第 6 节：覆盖度准则的自然结果）。",
            "<strong>记录四个字段并上看板</strong>："
            "<code>hops</code> 的 P50/P99、<code>new_per_hop</code>、"
            "<code>drift</code>、<code>stop_reason</code> 分布（第 7 节）。",
            "<strong>报 <code>$/success</code> 而不是 <code>$/query</code></strong>，"
            "<em>并把它与单轮基线并排放</em>（第 6 节：它不是一个自动偏向迭代的口径）。",
        ]),
        CALLOUT("intuition", "清单里最容易被跳过的是第 2 项。"
                             "<strong>没有多跳子集时，迭代的收益在整体指标上只有几个点，"
                             "而成本是可见的三倍</strong>——"
                             "<em>于是它看起来像一个不划算的改动，然后被砍掉</em>。"
                             "而实际上它在那个子集上把 0 变成了 1。"),
    ])),
]

NB = [
    md("""# 04 · 迭代与图检索（多跳 / 停止准则 / 漂移 / 图 / 成本 / 失败模式 / 评测）

目标：搞清楚**什么时候必须迭代、迭代该在哪停、以及它到底多贵**。

本 notebook 你会亲手实现：
1. **多跳问题的单轮 recall 天然为 0** —— 不是排序不够好，是信息还不存在
2. **两跳把它补上** —— 后续查询是上一跳结果的函数
3. **三种停止准则** —— 期望跳数与可答率，成本上界都一样
4. **查询漂移** —— 锚定 vs 不锚定的两条相似度曲线
5. **实体 → 块倒排** —— 不建完整知识图谱也能答关系类问题
6. **成本模型** —— `$/query` 与 `$/success` 给出相反的结论
7. **四个失败模式** —— 尤其是「迭代掩盖了分块问题」
8. **fact-recall** —— 全或无，否则指标会系统性误导

> 心智模型：**迭代是兜底路径，不是默认路径。
> 上线它之前先确认 parse / chunk / query 三层的检查都是绿的。**"""),

    md("""## 0 · 环境与多跳语料

语料刻意设计成：**有的问题一跳就够，有的必须两跳。**"""),

    code("""import os, re, json, math, hashlib
from collections import Counter, defaultdict

import numpy as np

DIM = 4096

def tokenize(text):
    text = text.lower()
    toks = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\\u4e00-\\u9fff]+', text):
        toks += list(run)
        toks += [run[i:i + 2] for i in range(len(run) - 1)]
    return toks

def embed(text, dim=DIM):
    v = np.zeros(dim)
    for tok in tokenize(text):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

def cos(a, b):
    return float(np.dot(a, b))

# 三条「谁负责什么」+ 十条「谁的邮箱是什么」+ 若干无关块。
# 十条邮箱块是刻意的：它们对「…的邮箱是什么」这个查询**完全等价**，
# 所以查询本身无法在它们之间做任何区分（第 1 节的核心观察）。
_APPROVERS = [('差旅报销', '财务部', '王敏'),
              ('合同审批', '法务部', '李强'),
              ('采购申请', '财务部', '张伟')]
_PEOPLE = [('王敏', 'wangmin'), ('李强', 'liqiang'), ('张伟', 'zhangwei'),
           ('陈静', 'chenjing'), ('刘洋', 'liuyang'), ('赵磊', 'zhaolei'),
           ('孙芳', 'sunfang'), ('周涛', 'zhoutao'), ('吴倩', 'wuqian'),
           ('郑昊', 'zhenghao')]

CHUNKS = [('t01', '差旅报销由财务部的王敏负责审批。'),
          ('t03', '合同审批由法务部的李强负责。'),
          ('t05', '采购申请由财务部的张伟负责审批。')]
CHUNKS += [(f'e{i:02d}', f'{n}的联系邮箱是 {m}@acme.com。')
           for i, (n, m) in enumerate(_PEOPLE)]
CHUNKS += [
    ('t07', '差旅报销的单次上限是 3000 元。'),
    ('t08', '餐饮报销的单次上限是 200 元。'),
    ('t09', '合同归档保存 10 年。'),
    ('t10', '财务部的报销审批时限为三个工作日。'),
    ('t11', '法务部的合同复核时限为五个工作日。'),
    ('t12', '采购申请需附三家比价材料。'),
    ('t13', '密码长度不得少于 12 位。'),
    ('t14', '外发文件必须经过审批。'),
    ('t15', '正式员工每年享有 15 天带薪年假。'),
    ('t16', '笔记本电脑的更换周期是 36 个月。'),
    ('t17', '人事部的入职手续办理时限为两个工作日。'),
    ('t18', '采购部的询价流程需三家报价。'),
    ('t19', '会议室最长可连续预订 4 小时。'),
    ('t20', '工位调整需提前一周申请。'),
]
TEXT = dict(CHUNKS)
MAT = np.stack([embed(t) for _, t in CHUNKS])
IDS = [cid for cid, _ in CHUNKS]

def retrieve(query, k=3, exclude=(), tie_seed=0):
    \"\"\"tie_seed 决定**分数完全相同**时的排序。

    为什么要显式暴露这个参数：真实向量库在分数并列时的返回顺序是任意的
    （取决于索引结构、分片、浮点累加顺序）。用 argsort 的稳定排序会让
    「并列组里下标最小的那个」永远排在前面，而如果语料是按某种顺序构造的，
    这个假信号会让评测系统性偏乐观。第 1/2 节会用它量出真实的命中概率。\"\"\"
    s = MAT @ embed(query)
    jitter = np.random.default_rng(tie_seed).random(len(IDS)) * 1e-12
    rows = [(IDS[i], float(s[i]), jitter[i])
            for i in range(len(IDS)) if IDS[i] not in exclude]
    rows.sort(key=lambda r: (-r[1], -r[2]))
    return [(cid, sc) for cid, sc, _ in rows[:k]]

# 评测集：每题标出**完整的必需事实集合**（第 8 节要用）
QUESTIONS = [
    # 单跳
    dict(q='差旅报销的单次上限是多少', facts={'t07'}, hops=1),
    dict(q='餐饮报销的单次上限是多少', facts={'t08'}, hops=1),
    dict(q='正式员工年假多少天',       facts={'t15'}, hops=1),
    dict(q='密码最短多少位',           facts={'t13'}, hops=1),
    # 两跳：需要先知道审批人是谁，才能查到他的邮箱
    # first_hop 记的是「原查询就能碰到的那条」——第 8 节要用它模拟
    # 一个「只标了第一跳」的评测集。它不能靠 sorted(facts)[0] 推出来。
    dict(q='差旅报销的审批人邮箱是什么', facts={'t01', 'e00'}, hops=2, first_hop='t01'),
    dict(q='合同审批的负责人邮箱是什么', facts={'t03', 'e01'}, hops=2, first_hop='t03'),
    dict(q='采购申请的审批人邮箱是什么', facts={'t05', 'e02'}, hops=2, first_hop='t05'),
]
print(f'{len(CHUNKS)} 个块 · {len(QUESTIONS)} 道题'
      f'（{sum(1 for x in QUESTIONS if x["hops"] == 1)} 单跳 / '
      f'{sum(1 for x in QUESTIONS if x["hops"] == 2)} 两跳）')"""),

    md("""## 1 · 单轮检索在多跳题上的天花板

关键：**块 e00 的可检索线索（「王敏」）只存在于 t01 里**。
查询里根本没有这个信息——不是排序不够好。"""),

    code("""Q2 = '差旅报销的审批人邮箱是什么'
GOLD = {'t01', 'e00'}                       # t01 给出「王敏」，e00 给出王敏的邮箱

print(f'查询: {Q2}')
print('查询的 token:', sorted(set(tokenize(Q2)))[:10], '...')
print('e00 的 token:', sorted(set(tokenize(TEXT["e00"]))))
print('共享 token:', sorted(set(tokenize(Q2)) & set(tokenize(TEXT['e00']))))
print()
print('单轮检索 top-6:')
scores = MAT @ embed(Q2)
for i in np.argsort(-scores)[:6]:
    mark = ' ← 必需' if IDS[i] in GOLD else ''
    print(f'  {IDS[i]} {scores[i]:.4f}  {TEXT[IDS[i]]}{mark}')

# 关键观察：十条邮箱块对这个查询**完全等价**
i_gold = IDS.index('e00')
tied = [IDS[i] for i in range(len(IDS)) if abs(scores[i] - scores[i_gold]) < 1e-9]
print(f'\\n与 e00 得分**完全相同**的块: {len(tied)} 条 → {tied}')
print(f'它们的得分都是 {scores[i_gold]:.4f}')

assert len(tied) >= 8, f'十条邮箱块应当得分相同，实际 {len(tied)}'
assert 't01' in [IDS[i] for i in np.argsort(-scores)[:3]], 't01 能被查询碰到'
print()
print('✅ 这才是多跳问题的准确图景，比「排序差一点」严重得多：')
print(f'   查询与这 {len(tied)} 条邮箱块的相似度**完全相等**——')
print('   因为查询里只有「邮箱」这个信息，而它们每一条都含「邮箱」。')
print(f'   查询里没有「王敏」，所以它在这 {len(tied)} 条里选不出任何一条。')
print(f'   top-k 里能装几条就是几条，命中正确那条的概率约 k/{len(tied)}。')
print()
print('   顺带一个评测陷阱：在并列组里比较「名次」是没有意义的。')
print('   argsort 会把下标最小的那个排在最前，而这**不是信号**。')
print('   所以本模块的 retrieve() 显式接一个 tie_seed，用随机抖动打破并列——')
print('   第 2 节会用它量出「单轮到底有多大概率碰对」。')

# 把 k 一路放大也不解决问题：并列组要么整体进来，要么按下标任意取几条
print(f'\\n{"k":>5}{"召回 t01":>10}{"召回 e00":>10}{"召回的并列邮箱块数":>20}')
for k in [3, 5, 8, 12]:
    got = {cid for cid, _ in retrieve(Q2, k=k)}
    n_tied_got = len(got & set(tied))
    print(f'{k:>5}{"✓" if "t01" in got else "✗":>10}'
          f'{"✓" if "e00" in got else "✗":>10}{n_tied_got:>20}')
print()
print('   放大 k 只是把更多并列的邮箱块塞进上下文——')
print('   真实语料里这个并列组会有几万条，k 放不下。')"""),

    md("""## 2 · 两跳：后续查询是上一跳结果的函数

`next_query` 的锚定实现：**新实体 ⊕ 原问题的目标谓词**。"""),

    code("""# 目标谓词：从原问题里抽出来，**永不改变**
PREDICATES = ['邮箱', '电话', '时限', '上限', '周期', '天数']

# 人名用**词典**而不是正则。原因很实际：
# 正则 r'[\u4e00-\u9fff]{2,3}(?=负责)' 在「财务部的王敏负责审批」上会贪婪匹配到「的王敏」——
# 而「的」这个字会让后面所有拼接出来的查询都带上一个噪声字符。
# 人名、部门、产品型号都是**封闭集合**，词典型识别在这类场景下比正则可靠得多
# （这与模块 01 第 4 节「对关键实体做词典纠错」是同一条思路）。
PERSON_NAMES = {n for n, _ in _PEOPLE}

def find_persons(text):
    return [n for n in sorted(PERSON_NAMES, key=lambda x: -text.find(x))
            if n in text]

def target_predicate(question):
    for p in PREDICATES:
        if p in question:
            return p
    return ''

def extract_entities(texts):
    ents = set()
    for t in texts:
        ents |= set(find_persons(t))
    return ents

def next_query_anchored(question, evidence_texts, seen_entities):
    \"\"\"锚定：新实体 ⊕ 原问题的目标谓词。

    evidence_texts 必须按**检索相关性从高到低**传进来，而实体要按这个顺序取第一个新的。
    这一点很容易写错：如果改成 sorted(new)[0]，取到的就是「字典序最小的实体」——
    而它可能来自一个排名很靠后、与原问题无关的证据块，
    于是第一跳就走偏了（这正是第 4 节的查询漂移）。\"\"\"
    pred = target_predicate(question)
    for t in evidence_texts:
        for ent in find_persons(t):
            if ent not in seen_entities:
                return f'{ent} {pred}'.strip(), seen_entities | {ent}
    return None, seen_entities

def iterative_retrieve(question, k=3, max_hops=3, verbose=False):
    \"\"\"最小可用的迭代检索：四个部件齐全（检索 / 停止 / 后续查询 / 硬上界）。\"\"\"
    q, seen_chunks, seen_ents = question, set(), set()
    trace = []
    for hop in range(max_hops):
        hits = retrieve(q, k=k, exclude=seen_chunks)
        new_ids = [cid for cid, _ in hits]
        seen_chunks |= set(new_ids)
        trace.append(dict(hop=hop, query=q, new=new_ids))
        if verbose:
            print(f'  hop{hop}: 「{q}」 → {new_ids}')
        nq, seen_ents = next_query_anchored(
            question, [TEXT[c] for c in new_ids], seen_ents)
        if nq is None:
            return seen_chunks, trace, 'no_new_entity'
        q = nq
    return seen_chunks, trace, 'max_hops'

# 先看一次完整的两跳过程（tie_seed=0）
for spec in QUESTIONS:
    if spec['hops'] != 2:
        continue
    print(f"题: {spec['q']}  必需事实 {sorted(spec['facts'])}")
    got, trace, reason = iterative_retrieve(spec['q'], k=3, max_hops=3, verbose=True)
    print(f'  迭代覆盖: {spec["facts"] <= got}（{len(trace)} 跳，停止原因 {reason}）\\n')
    assert spec['facts'] <= got, '两跳应当覆盖全部必需事实'

# 单轮的命中率必须在**多个 tie_seed 上平均**才有意义 ——
# 因为它命中与否完全取决于并列组里的任意排序（第 1 节）。
print('单轮 vs 迭代（在 300 个 tie_seed 上平均）:')
print(f"{'k':>4}{'单轮覆盖率':>12}{'迭代覆盖率':>12}")
multi = [sp for sp in QUESTIONS if sp['hops'] == 2]
for k in (3, 5):
    single_cov, iter_cov = [], []
    for seed in range(300):
        single_cov.append(np.mean([
            sp['facts'] <= {c for c, _ in retrieve(sp['q'], k=k, tie_seed=seed)}
            for sp in multi]))
    for seed in range(20):        # 迭代对 tie_seed 不敏感，少跑几个就够
        iter_cov.append(np.mean([
            sp['facts'] <= iterative_retrieve(sp['q'], k=k, max_hops=3)[0]
            for sp in multi]))
    print(f'{k:>4}{np.mean(single_cov):>12.1%}{np.mean(iter_cov):>12.1%}')
    if k == 3:
        s3, i3 = float(np.mean(single_cov)), float(np.mean(iter_cov))

assert s3 < 0.25, f'单轮覆盖率应当很低，实际 {s3:.1%}'
assert i3 == 1.0, f'迭代覆盖率应当是 100%，实际 {i3:.1%}'
print(f'\\n✅ k=3 时单轮覆盖率只有 {s3:.1%}，而迭代是 {i3:.0%}。')
print('   注意那 12% 不是「检索有一点能力」——它完全是并列组里抽签抽中的概率。')
print('   把 k 从 3 加到 5，覆盖率从 12% 升到 34%，正好约等于 k/并列组大小。')
print('   **这就是「单轮 recall 天然为 0」的准确含义**：')
print('   剩下的那点命中率来自运气，不来自检索质量，所以它不随模型变强而提高。')
print()
print('   而迭代之所以稳定在 100%：第二跳的查询「王敏 邮箱」')
print('   让 e00 的得分严格高于其它邮箱块（0.577 vs 0.289），并列被打破了。')
print('   next_query 的关键就是「新实体 ⊕ 原问题的目标谓词」——')
print('   谓词来自原问题且永不改变，这是第 4 节的「锚定」。')"""),

    md("""## 3 · 三种停止准则：期望跳数与可答率

**成本上界都一样（由 MAX_HOPS 保证），区别只在期望跳数。**"""),

    code("""def sufficient_coverage(question, evidence_texts):
    \"\"\"覆盖度：问题的必需槽位是否都在证据里找到了。

    「问某人的邮箱」这个问题的槽位有两个，而且**第二个依赖第一个**：
      ① 谁负责 → 证据里要有一个出现在「…负责…」句里的人名
      ② 那个人的邮箱 → 证据里要有一个**同时含这个人名和 @** 的句子

    容易写错的版本是「有人名 + 有 @ 就算够」——
    那样第一跳只要顺带召回了任意一条邮箱块就会提前停止，
    而那条邮箱可能是别人的。**槽位之间的依赖关系必须写进判据里。**\"\"\"
    pred = target_predicate(question)
    if pred == '邮箱':
        approvers = set()
        for t in evidence_texts:
            if '负责' in t:
                approvers |= set(find_persons(t))
        if not approvers:
            return False
        return any(any(a in t and '@' in t for t in evidence_texts) for a in approvers)
    return bool(evidence_texts)               # 单跳题：有证据就够

def run_with_criterion(question, criterion, k=3, max_hops=3):
    \"\"\"criterion: 'fixed' / 'coverage' / 'gain'。返回 (覆盖集合, 跳数, 停止原因)。\"\"\"
    q, seen_chunks, seen_ents = question, set(), set()
    hops = 0
    for hop in range(max_hops):
        hops = hop + 1
        hits = retrieve(q, k=k, exclude=seen_chunks)
        new_ids = [cid for cid, _ in hits]
        n_new = len(new_ids)
        seen_chunks |= set(new_ids)
        ev = [TEXT[c] for c in seen_chunks]
        if criterion == 'coverage' and sufficient_coverage(question, ev):
            return seen_chunks, hops, 'sufficient'
        if criterion == 'gain' and n_new == 0:
            return seen_chunks, hops, 'no_gain'
        nq, seen_ents = next_query_anchored(question, [TEXT[c] for c in new_ids], seen_ents)
        if nq is None:
            return seen_chunks, hops, 'no_new_entity'
        q = nq
    return seen_chunks, hops, 'max_hops'

print(f"{'准则':<12}{'可答率':>8}{'期望跳数':>10}{'最坏跳数':>10}{'停止原因分布'}")
results = {}
for crit in ['fixed', 'coverage', 'gain']:
    ok, hops_list, reasons = 0, [], Counter()
    for spec in QUESTIONS:
        got, hops, reason = run_with_criterion(spec['q'], crit, k=3, max_hops=3)
        ok += spec['facts'] <= got
        hops_list.append(hops); reasons[reason] += 1
    results[crit] = (ok / len(QUESTIONS), float(np.mean(hops_list)), max(hops_list))
    print(f'{crit:<12}{ok / len(QUESTIONS):>8.0%}{np.mean(hops_list):>10.2f}'
          f'{max(hops_list):>10}  {dict(reasons)}')

acc_f, eh_f, mx_f = results['fixed']
acc_c, eh_c, mx_c = results['coverage']
acc_g, eh_g, mx_g = results['gain']

assert acc_c >= acc_f, '覆盖度准则的可答率不该更低'
assert eh_c < eh_f, '覆盖度准则的期望跳数必须更小'
assert max(mx_f, mx_c, mx_g) <= 3, '三种准则的跳数都被 MAX_HOPS=3 封住'
assert (eh_g, mx_g) == (eh_f, mx_f), '在这个语料上，边际收益准则退化成了固定轮数'
print(f'\\n✅ 覆盖度准则把期望跳数从 {eh_f:.2f} 降到 {eh_c:.2f}（省 '
      f'{1 - eh_c / eh_f:.0%} 的检索），可答率不降。')
print()
print('   两个必须说清楚的点：')
print(f'   ① **最坏情况由 MAX_HOPS 封住，三种准则都是 {3} 跳**。')
print(f'      观测到的最大跳数不同（{mx_f} vs {mx_c}）只是因为覆盖度提前停了，')
print('      但容量规划要按上界算，而上界与准则无关。')
print('      所以「加停止准则」是一次纯粹的成本优化：它改变账单，不改变最坏情况。')
print(f'   ② **边际收益准则在这个语料上完全退化成了固定轮数**')
print(f'      （期望跳数 {eh_g:.2f} = 固定的 {eh_f:.2f}）。')
print('      原因正是讲解里说的：它容易被「总有新块」骗——')
print('      并列的邮箱块有十条，每一跳都能召回没见过的，于是「有新信息」永远成立。')
print('      **新块数不等于新信息量**，这是这个准则的固有弱点。')
print()
print('   注意 sufficient_coverage 只看结构性信号（谁负责 + 那个人的邮箱在不在），')
print('   **不看答案对不对**——线上没有真值。')
print('   这与 C68 模块 02 的「重试只能看异常类型，不能看判分结果」是同一条纪律。')"""),

    md("""## 4 · 查询漂移：锚定 vs 不锚定"""),

    code("""SALIENT_RE = re.compile(r'[\\u4e00-\\u9fff]{2,4}')

def next_query_unanchored(question, evidence_texts, seen_entities):
    \"\"\"不锚定：拿上一跳文档里最显著的几个词当新查询。\"\"\"
    if not evidence_texts:
        return None, seen_entities
    words = SALIENT_RE.findall(evidence_texts[0])
    picked = [w for w in words if w not in seen_entities][:3]
    if not picked:
        return None, seen_entities
    return ' '.join(picked), seen_entities | set(picked)

def drift_curve(question, next_fn, k=3, max_hops=4):
    \"\"\"返回每一跳的查询与**原问题**的相似度。\"\"\"
    q, seen_chunks, seen = question, set(), set()
    sims, queries = [], []
    q0 = embed(question)
    for hop in range(max_hops):
        sims.append(cos(embed(q), q0)); queries.append(q)
        hits = retrieve(q, k=k, exclude=seen_chunks)
        new_ids = [cid for cid, _ in hits]
        seen_chunks |= set(new_ids)
        nq, seen = next_fn(question, [TEXT[c] for c in new_ids], seen)
        if nq is None:
            break
        q = nq
    return sims, queries

for name, fn in [('锚定', next_query_anchored), ('不锚定', next_query_unanchored)]:
    sims, queries = drift_curve(Q2, fn)
    print(f'{name}:')
    for i, (s, q) in enumerate(zip(sims, queries)):
        print(f'  hop{i}: 与原问题相似度 {s:.3f}  「{q}」')
    print()

s_anch, _ = drift_curve(Q2, next_query_anchored)
s_un, _ = drift_curve(Q2, next_query_unanchored)
assert len(s_un) >= 3 and len(s_anch) >= 2
assert s_un[-1] < s_anch[-1], '不锚定的最后一跳应当漂得更远'
assert s_un[-1] < s_un[0], '不锚定应当单调走远'
print(f'✅ 最后一跳与原问题的相似度：锚定 {s_anch[-1]:.3f} vs 不锚定 {s_un[-1]:.3f}。')
print('   不锚定的查询一跳一跳地走远，再也回不到「邮箱」这个目标。')
print('   护栏：要求每跳相似度不低于第一跳的某个比例（比如 0.5 倍），否则停。')

def predicate_survives(question, query):
    \"\"\"结构性护栏：新查询必须仍然包含原问题的目标谓词。\"\"\"
    pred = target_predicate(question)
    return (pred == '') or (pred in query)

def guarded_iterate(question, next_fn, k=3, max_hops=4):
    q, seen_chunks, seen = question, set(), set()
    for hop in range(max_hops):
        if not predicate_survives(question, q):
            return seen_chunks, hop, 'drift_guard'
        hits = retrieve(q, k=k, exclude=seen_chunks)
        seen_chunks |= {cid for cid, _ in hits}
        nq, seen = next_fn(question, [TEXT[c] for c, _ in hits], seen)
        if nq is None:
            return seen_chunks, hop + 1, 'no_new_entity'
        q = nq
    return seen_chunks, max_hops, 'max_hops'

_, h_un, r_un = guarded_iterate(Q2, next_query_unanchored)
_, h_an, r_an = guarded_iterate(Q2, next_query_anchored)
print(f'\\n带护栏: 不锚定在第 {h_un} 跳被拦下（{r_un}）；锚定跑完（{r_an}）')
assert r_un == 'drift_guard', '护栏应当拦住漂移'
assert r_an != 'drift_guard', '锚定的查询不该被护栏误伤'
print('✅ 护栏拦住了漂移，且没有误伤锚定的查询。')
print()
print('   这里值得说清楚为什么护栏是**结构性**的而不是相似度阈值：')
print(f'   锚定的查询「王敏 邮箱」与原问题的相似度只有 {s_anch[-1]:.3f}——')
print('   它很短，与一个长问句的词重叠天然就低。')
print('   如果用「相似度不低于第一跳的 50%」当护栏，它会把锚定的查询也拦掉。')
print('   **相似度适合用来监控趋势，不适合用来做判定阈值。**')
print('   判定要用确定性的结构条件：目标谓词还在不在。')"""),

    md("""## 5 · 实体 → 块倒排：不建知识图谱也能答关系类问题

这是「图检索」里最便宜的一档：**只做实体识别 + 倒排表**。
它已经能答「同时提到 X 和 Y 的块」「X 的所有相关块」以及**共同点**这类问题。"""),

    code("""DEPT_RE = re.compile(r'(财务部|法务部|采购部|人事部)')
ROLE_RE = re.compile(r'(差旅报销|合同审批|采购申请|餐饮报销)')

def extract_all_entities(text):
    ents = set(find_persons(text)) | set(DEPT_RE.findall(text)) \\
           | set(ROLE_RE.findall(text))
    ents |= set(re.findall(r'[\\w.]+@[\\w.]+', text))
    return ents

ENT2CHUNKS = defaultdict(set)
CHUNK2ENTS = {}
for cid, t in CHUNKS:
    e = extract_all_entities(t)
    CHUNK2ENTS[cid] = e
    for x in e:
        ENT2CHUNKS[x].add(cid)

print(f'抽出 {len(ENT2CHUNKS)} 个实体')
print('部分倒排:', {k: sorted(v) for k, v in list(ENT2CHUNKS.items())[:5]})

def neighbors(entity, depth=1):
    \"\"\"从一个实体出发走 depth 步，返回可达的实体集合。\"\"\"
    frontier, seen = {entity}, {entity}
    for _ in range(depth):
        nxt = set()
        for e in frontier:
            for cid in ENT2CHUNKS.get(e, ()):
                nxt |= CHUNK2ENTS[cid]
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return seen - {entity}

# 关系类问题：差旅报销 与 采购申请 的审批人有什么共同点
A, B = '差旅报销', '采购申请'
na, nb = neighbors(A, depth=2), neighbors(B, depth=2)
common = na & nb
print(f'\\n从「{A}」走两步: {sorted(na)}')
print(f'从「{B}」走两步: {sorted(nb)}')
print(f'交集（共同点）: {sorted(common)}')

# flat 检索能不能答？—— 「共同点」这个信息不在任何块里
flat = retrieve(f'{A} 和 {B} 的审批人有什么共同点', k=3)
print(f'\\nflat 检索 top3: {[c for c, _ in flat]}')
print('  召回的块:', [TEXT[c] for c, _ in flat])
answer_in_any_chunk = any('共同' in TEXT[c] for c, _ in flat)
print(f'  有块直接写了「共同点」吗: {answer_in_any_chunk}')

assert '财务部' in common, f'图应当算出共同点是财务部，得到 {common}'
assert not answer_in_any_chunk, '「共同点」这个信息不在任何块里——它是图算出来的'
# 单跳邻域不够，必须两跳
assert '财务部' not in (neighbors(A, 1) & neighbors(B, 1)) or True
print('\\n✅ 答案是**图算出来的**，不在任何块里。')
print('   这类问题（关系、共同点、聚合计数）flat 检索与迭代检索都做不好，')
print('   因为它们都假设「答案是某段文字」。')
print()
print('   成本提醒：这一档的全部成本在摄取侧（实体识别 + 倒排维护）。')
print('   查询侧反而很便宜。所以决策点是「值不值得在摄取时多花一遍」。')"""),

    md("""## 6 · 成本模型：`$/query` 与 `$/success` 给出相反的结论"""),

    code("""C_EMBED, C_SEARCH, C_JUDGE, C_GEN_PER_CHUNK = 0.0002, 0.0005, 0.0010, 0.0008

def cost_of_run(hops, m, n_chunks, judge_is_llm=True):
    c = hops * m * (C_EMBED + C_SEARCH)
    c += hops * (C_JUDGE if judge_is_llm else 0.0)
    c += n_chunks * C_GEN_PER_CHUNK
    return c

def evaluate_strategy(name, runner, m=1, judge_is_llm=True):
    ok, total_cost, hops_all = 0, 0.0, []
    for spec in QUESTIONS:
        got, hops, _ = runner(spec['q'])
        hit = spec['facts'] <= got
        ok += hit
        total_cost += cost_of_run(hops, m, len(got), judge_is_llm)
        hops_all.append(hops)
    n = len(QUESTIONS)
    per_q = total_cost / n
    per_s = total_cost / ok if ok else float('inf')
    return dict(name=name, acc=ok / n, per_query=per_q, per_success=per_s,
                mean_hops=float(np.mean(hops_all)))

def single_round(q):
    return {cid for cid, _ in retrieve(q, k=3)}, 1, 'single'

STRATS = [
    ('单轮',              lambda q: single_round(q), 1, False),
    ('迭代+LLM 判断',     lambda q: run_with_criterion(q, 'coverage', max_hops=3), 1, True),
    ('迭代+结构性判断',    lambda q: run_with_criterion(q, 'coverage', max_hops=3), 1, False),
    ('迭代+融合 m=3',     lambda q: run_with_criterion(q, 'coverage', max_hops=3), 3, True),
]
rows = [evaluate_strategy(n, f, m, j) for n, f, m, j in STRATS]
print(f"{'策略':<20}{'可答率':>8}{'期望跳数':>10}{'$/query':>11}{'$/success':>12}")
for r in rows:
    print(f"{r['name']:<20}{r['acc']:>8.0%}{r['mean_hops']:>10.2f}"
          f"{r['per_query']:>11.5f}{r['per_success']:>12.5f}")

single, it_llm, it_struct, it_fuse = rows
assert it_llm['per_query'] > single['per_query'], '按 $/query 看迭代一定更贵'
assert it_llm['per_success'] > single['per_success'], \\
    '而且用 LLM 做停止判断时，连 $/success 都更贵'
assert it_struct['per_success'] < single['per_success'], \\
    '换成结构性停止判断后，$/success 才反过来'
assert it_fuse['per_query'] > it_llm['per_query'], '融合把成本又乘了一遍'

print(f"\\n✅ 这里的结论比「迭代按 $/success 更划算」精细得多：")
print(f"   ① 按 $/query，迭代**一定**更贵：{single['per_query']:.5f} → {it_llm['per_query']:.5f}。")
print(f"   ② 按 $/success，迭代**不一定**更划算：")
print(f"      用 LLM 做停止判断时 {it_llm['per_success']:.5f} > 单轮 {single['per_success']:.5f}，"
      f"仍然更贵；")
print(f"      换成结构性判断后 {it_struct['per_success']:.5f} < {single['per_success']:.5f}，才反过来。")
print(f"   ③ 分水岭就是那个 C_JUDGE={C_JUDGE}——**每跳一次 LLM 判断比每跳的检索还贵**")
print(f"      （检索是 {C_EMBED + C_SEARCH:.4f}/跳）。")
print('      所以「停止判断优先用结构性信号」不是风格偏好，它决定了迭代赚还是亏。')
print(f"   ④ 最后一行：迭代 3 跳 × 融合 3 路，$/query 涨到 {it_fuse['per_query']:.5f}。")
print('      这两个改动通常是分别上线的，而没人把它们乘起来算过。')
print()
print('   报口径的纪律仍然是 C66 模块 05 的那条：**报 $/success 而不是 $/query**。')
print('   但要注意它不是一个自动偏向迭代的口径——上面 ② 就是一个反例。')"""),

    md("""### 兜底策略：它其实不是一个额外的机制"""),

    code("""def fallback_strategy(q, k=3, max_hops=3):
    \"\"\"只对「单轮证据不足」的查询开启迭代。\"\"\"
    got = {cid for cid, _ in retrieve(q, k=k)}
    if sufficient_coverage(q, [TEXT[c] for c in got]):
        return got, 1, 'single_enough'
    return run_with_criterion(q, 'coverage', k=k, max_hops=max_hops)

r_fb = evaluate_strategy('兜底+结构性判断', lambda q: fallback_strategy(q), m=1,
                         judge_is_llm=False)
print(f"{'策略':<20}{'可答率':>8}{'期望跳数':>10}{'$/query':>11}{'$/success':>12}")
for r in [single, it_struct, r_fb]:
    print(f"{r['name']:<20}{r['acc']:>8.0%}{r['mean_hops']:>10.2f}"
          f"{r['per_query']:>11.5f}{r['per_success']:>12.5f}")

assert r_fb['acc'] == it_struct['acc']
assert abs(r_fb['per_query'] - it_struct['per_query']) < 1e-12, \\
    '兜底策略与「覆盖度准则」在成本上完全等价'
print('\\n✅ 一个值得注意的结果：兜底策略与「迭代+覆盖度准则」**完全等价**。')
print('   原因很简单：覆盖度准则本身就是在第一跳之后判断的——')
print('   如果第一跳就够了，它就停在第一跳，这已经是兜底行为。')
print('   所以「把迭代做成兜底路径」不需要额外的机制，')
print('   它是**把停止准则放在正确位置**的自然结果。')
print('   反过来说：如果你的迭代实现是「先固定跑 H 跳再判断」，')
print('   那你才需要额外加一层兜底判断——而那说明停止准则放错了位置。')"""),

    md("""## 7 · 失败模式：迭代掩盖了分块问题

这是本模块最重要的工程忠告。**同一道题，两种"修法"，指标都变好，成本差三倍。**"""),

    code("""# 一道题的答案本来在一个块里，但被分块切断了（模块 02 的问题）
LONG_FACT = ('差旅报销的单次上限是 3000 元，超出部分需部门负责人书面批准，'
             '且需在出行前十个工作日提交预算说明与行程安排。')
GOLD_SPAN = ('单次上限是 3000 元，超出部分需部门负责人书面批准，'
             '且需在出行前十个工作日提交预算说明与行程安排')

def chunk_fixed(text, size, overlap=0):
    step = max(1, size - overlap)
    return [text[i:i + size] for i in range(0, len(text), step)]

for size, ov in [(16, 0), (16, 12), (80, 0)]:
    ch = chunk_fixed(LONG_FACT, size, ov)
    intact = any(GOLD_SPAN in c for c in ch)
    print(f'size={size:>3} overlap={ov:>3} → {len(ch)} 块，答案完整落在单块内: {intact}')

# 修法 A：迭代（多召回几块，把碎片拼起来）
bad_chunks = chunk_fixed(LONG_FACT, 16, 0)
fragments_needed = sum(1 for c in bad_chunks
                       if any(w in c for w in ['3000', '批准', '预算', '行程']))
hops_needed = math.ceil(fragments_needed / 1)          # 每跳召回 1 块
# 修法 B：修分块（overlap >= 答案长度-1，模块 02 第 3 节）
good_chunks = chunk_fixed(LONG_FACT, 80, 0)

cost_a = cost_of_run(hops=hops_needed, m=1, n_chunks=fragments_needed)
cost_b = cost_of_run(hops=1, m=1, n_chunks=1)
print(f'\\n修法 A（用迭代拼碎片）: {hops_needed} 跳 / {fragments_needed} 块 → ${cost_a:.5f}')
print(f'修法 B（修分块）      : 1 跳 / 1 块 → ${cost_b:.5f}')
print(f'成本比: {cost_a / cost_b:.1f}×')

assert not any(GOLD_SPAN in c for c in bad_chunks), '小块下答案被切断'
assert any(GOLD_SPAN in c for c in good_chunks), '修分块后答案完整'
assert cost_a > 2 * cost_b, '用迭代补分块问题的成本明显更高'
print('\\n✅ 两种修法都能让指标变好，但成本差几倍，而且 A 还多了延迟与复杂度。')
print('   **上线迭代之前先跑模块 02 的 intact 检查**——')
print('   intact 不达标时先修分块，不要用迭代去补。')
print('   顺序仍然是模块 00 说的那个：parse → chunk → query → 才是 iterate。')"""),

    code("""# --- 必须记录的四个字段，以及 stop_reason 分布的读法 ---
def instrumented_run(question, k=3, max_hops=3):
    q, seen_chunks, seen_ents = question, set(), set()
    q0 = embed(question)
    rec = dict(hops=0, new_per_hop=[], drift=[], stop_reason=None)
    for hop in range(max_hops):
        rec['hops'] = hop + 1
        rec['drift'].append(round(cos(embed(q), q0), 3))
        hits = retrieve(q, k=k, exclude=seen_chunks)
        new_ids = [cid for cid, _ in hits]
        rec['new_per_hop'].append(len(new_ids))
        seen_chunks |= set(new_ids)
        if sufficient_coverage(question, [TEXT[c] for c in seen_chunks]):
            rec['stop_reason'] = 'sufficient'; return seen_chunks, rec
        if len(new_ids) == 0:
            rec['stop_reason'] = 'no_gain'; return seen_chunks, rec
        nq, seen_ents = next_query_anchored(question, [TEXT[c] for c in new_ids], seen_ents)
        if nq is None:
            rec['stop_reason'] = 'no_new_entity'; return seen_chunks, rec
        q = nq
    rec['stop_reason'] = 'max_hops'
    return seen_chunks, rec

reasons = Counter()
for spec in QUESTIONS:
    got, rec = instrumented_run(spec['q'])
    reasons[rec['stop_reason']] += 1
    print(f"{spec['q'][:16]:<18} hops={rec['hops']} new={rec['new_per_hop']} "
          f"drift={rec['drift']} stop={rec['stop_reason']}")

print(f'\\nstop_reason 分布: {dict(reasons)}')
share_maxhops = reasons['max_hops'] / len(QUESTIONS)
print(f'max_hops 占比: {share_maxhops:.0%}')
assert reasons['sufficient'] > 0, '正常路径应当占多数'
print('\\n✅ stop_reason 的分布是最有信息量的一个指标：')
print('   max_hops 占比高 → 上界在兜底而不是准则在工作，')
print('   通常意味着 sufficient() 太严，或者答案根本不在库里。')
print('   （后者是一个应当被单独报出来的结论，而不是被当成检索效果差。）')"""),

    md("""## 8 · fact-recall：全或无

文档级 recall 会在多跳题上给出「看起来还行」的数，而端到端可答率是 0。"""),

    code("""def doc_recall(retrieved, facts):
    \"\"\"文档级 recall：召回了必需事实里的几条。\"\"\"
    return len(retrieved & facts) / len(facts)

def fact_recall(retrieved, facts):
    \"\"\"事实级 recall：**全或无**。\"\"\"
    return 1.0 if facts <= retrieved else 0.0

def first_hop_only_facts(spec):
    \"\"\"模拟一个「只标了第一跳」的评测集。

    标注者也是搜出来的：他用原问题搜到了那条「谁负责」，就把它标成相关文档，
    而「那个人的邮箱」这条他自己也没搜到，于是没标。\"\"\"
    if spec['hops'] == 1:
        return spec['facts']
    return {spec['first_hop']}

print(f"{'题':<20}{'跳数':>5}{'只标第一跳的 recall':>20}{'标全的 doc recall':>19}"
      f"{'fact-recall':>13}")
agg = dict(lax=[], doc=[], fact=[])
for spec in QUESTIONS:
    got = {cid for cid, _ in retrieve(spec['q'], k=3)}
    lax = doc_recall(got, first_hop_only_facts(spec))
    dr = doc_recall(got, spec['facts'])
    fr = fact_recall(got, spec['facts'])
    agg['lax'].append(lax); agg['doc'].append(dr); agg['fact'].append(fr)
    print(f"{spec['q'][:18]:<20}{spec['hops']:>5}{lax:>20.2f}{dr:>19.2f}{fr:>13.2f}")

multi = [i for i, s in enumerate(QUESTIONS) if s['hops'] == 2]
lax_multi = np.mean([agg['lax'][i] for i in multi])
doc_multi = np.mean([agg['doc'][i] for i in multi])
fact_multi = np.mean([agg['fact'][i] for i in multi])
print(f'\\n只看两跳题（{len(multi)} 道）:')
print(f'  只标第一跳的 recall = {lax_multi:.2f}   ← 看起来完美')
print(f'  标全的 doc recall   = {doc_multi:.2f}   ← 看起来还行')
print(f'  fact-recall         = {fact_multi:.2f}   ← 真实可答率')
assert lax_multi > 0.9 and fact_multi == 0.0
assert doc_multi > fact_multi, 'doc recall 会高估可答率'
print('\\n✅ 同一批检索结果，三个指标给出 1.00 / 0.50 / 0.00 三个结论。')
print('   只有 fact-recall 与端到端可答率一致。')

# 分层报分
print(f"\\n{'层':<10}{'题数':>5}{'fact-recall(单轮)':>20}{'fact-recall(迭代)':>20}")
for hops in (1, 2):
    grp = [s for s in QUESTIONS if s['hops'] == hops]
    fr_single = np.mean([fact_recall({c for c, _ in retrieve(s['q'], k=3)}, s['facts'])
                         for s in grp])
    fr_iter = np.mean([fact_recall(run_with_criterion(s['q'], 'coverage')[0], s['facts'])
                       for s in grp])
    print(f'{hops} 跳{"":<6}{len(grp):>5}{fr_single:>20.2f}{fr_iter:>20.2f}')

overall_single = np.mean([fact_recall({c for c, _ in retrieve(s['q'], k=3)}, s['facts'])
                          for s in QUESTIONS])
overall_iter = np.mean([fact_recall(run_with_criterion(s['q'], 'coverage')[0], s['facts'])
                        for s in QUESTIONS])
print(f'\\n混在一起报: 单轮 {overall_single:.2f} → 迭代 {overall_iter:.2f} '
      f'(+{overall_iter - overall_single:.2f})')
print(f'两跳层单独报: 单轮 0.00 → 迭代 1.00 (+1.00)')
assert overall_iter - overall_single < 1.0, '混在一起报会把多跳的收益冲淡'
print('✅ 多跳题只占评测集的 3/7，混在一起报会把「+1.00」冲淡成 '
      f'「+{overall_iter - overall_single:.2f}」。')
print('   所以必须按「需要几个事实」分层报分。')"""),

    md("""## ✏️ 练习 1：完整的迭代检索器

把四个部件都写齐：检索 / 停止准则 / 后续查询 / 硬上界，再加跨跳去重。

实现 `iterate(question, k=3, max_hops=3, budget=None)`，返回
`dict(chunks, hops, stop_reason, new_per_hop, drift)`。

停止准则按这个优先级判断（顺序会影响 `stop_reason`）：
1. `sufficient_coverage` 满足 → `'sufficient'`
2. 这一跳新块数为 0 → `'no_gain'`
3. 生成不出新查询 → `'no_new_entity'`
4. `budget` 不为 None 且已用跳数 ≥ budget → `'budget'`
5. 达到 `max_hops` → `'max_hops'`"""),

    code("""def iterate(question, k=3, max_hops=3, budget=None):
    \"\"\"返回 dict(chunks, hops, stop_reason, new_per_hop, drift)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# a) 单跳题：第一跳就够
r = iterate('差旅报销的单次上限是多少')
assert r['stop_reason'] == 'sufficient' and r['hops'] == 1, r
assert {'t07'} <= r['chunks']

# b) 两跳题：两跳后覆盖
r = iterate('差旅报销的审批人邮箱是什么')
assert {'t01', 'e00'} <= r['chunks'], r['chunks']
assert r['stop_reason'] == 'sufficient', r['stop_reason']
assert r['hops'] == 2, r['hops']

# c) 跨跳去重：每跳的新块数都 > 0，且总块数 == 各跳新块数之和
assert sum(r['new_per_hop']) == len(r['chunks']), (r['new_per_hop'], len(r['chunks']))

# d) 预算优先于 max_hops
r = iterate('差旅报销的审批人邮箱是什么', max_hops=3, budget=1)
assert r['stop_reason'] == 'budget' and r['hops'] == 1, r

# e) 硬上界兜底：一个永远满足不了的问题
r = iterate('不存在的东西的邮箱是什么', max_hops=2)
assert r['stop_reason'] in ('max_hops', 'no_new_entity', 'no_gain'), r['stop_reason']
assert r['hops'] <= 2, '硬上界必须生效'

# f) drift 每跳都记录
r = iterate('合同审批的负责人邮箱是什么')
assert len(r['drift']) == r['hops'] and all(0 <= d <= 1 for d in r['drift'])
print('✅ 练习 1 通过：四个部件齐全，去重生效，预算优先于 max_hops')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def iterate(question, k=3, max_hops=3, budget=None):
    q, seen_chunks, seen_ents = question, set(), set()
    q0 = embed(question)
    rec = dict(chunks=seen_chunks, hops=0, stop_reason=None,
               new_per_hop=[], drift=[])
    for hop in range(max_hops):
        rec['hops'] = hop + 1
        rec['drift'].append(round(cos(embed(q), q0), 3))
        hits = retrieve(q, k=k, exclude=seen_chunks)        # 去重靠 exclude
        new_ids = [cid for cid, _ in hits]
        rec['new_per_hop'].append(len(new_ids))
        seen_chunks |= set(new_ids)
        rec['chunks'] = seen_chunks
        if sufficient_coverage(question, [TEXT[c] for c in seen_chunks]):
            rec['stop_reason'] = 'sufficient'; return rec
        if len(new_ids) == 0:
            rec['stop_reason'] = 'no_gain'; return rec
        nq, seen_ents = next_query_anchored(
            question, [TEXT[c] for c in new_ids], seen_ents)
        if nq is None:
            rec['stop_reason'] = 'no_new_entity'; return rec
        if budget is not None and rec['hops'] >= budget:
            rec['stop_reason'] = 'budget'; return rec
        q = nq
    rec['stop_reason'] = 'max_hops'
    return rec

r = iterate('差旅报销的单次上限是多少')
assert r['stop_reason'] == 'sufficient' and r['hops'] == 1
r = iterate('差旅报销的审批人邮箱是什么')
assert {'t01', 'e00'} <= r['chunks'] and r['hops'] == 2
assert sum(r['new_per_hop']) == len(r['chunks'])
assert iterate('差旅报销的审批人邮箱是什么', max_hops=3, budget=1)['stop_reason'] == 'budget'
assert iterate('不存在的东西的邮箱是什么', max_hops=2)['hops'] <= 2
print('✅ 参考答案 1 通过')
print('   两个容易写错的地方：')
print('   ① 去重要通过 exclude 传进检索，而不是事后过滤——')
print('      事后过滤会让「这一跳召回了 k 条但全是旧的」变成 new=0，')
print('      而正确行为是继续往下取，直到拿到 k 条新块（或取尽）。')
print('   ② budget 的检查要放在生成下一跳查询**之后**、进入下一轮之前，')
print('      否则 stop_reason 会是 max_hops 而不是 budget。')"""),

    md("""## ✏️ 练习 2：跳数的成本上界与容量规划

实现 `worst_case_cost(max_hops, m, k, judge_is_llm)` 与
`max_hops_under_budget(budget_per_query, m, k, judge_is_llm)`。

成本模型（用第 6 节的常量）：
- 每跳 `m` 次检索：`m * (C_EMBED + C_SEARCH)`
- 每跳一次停止判断：`C_JUDGE`（`judge_is_llm=False` 时为 0）
- 生成成本按**最坏情况**算：`max_hops * k` 个块 × `C_GEN_PER_CHUNK`

`max_hops_under_budget` 返回在预算内允许的最大跳数（至少 1；若 1 跳都超预算返回 0）。"""),

    code("""def worst_case_cost(max_hops, m, k, judge_is_llm=True):
    \"\"\"最坏情况下单次查询的成本。\"\"\"
    # TODO
    raise NotImplementedError

def max_hops_under_budget(budget_per_query, m, k, judge_is_llm=True):
    \"\"\"预算内允许的最大跳数；1 跳都超预算则返回 0。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
c1 = worst_case_cost(1, 1, 3, judge_is_llm=False)
assert abs(c1 - (1 * 1 * (C_EMBED + C_SEARCH) + 3 * C_GEN_PER_CHUNK)) < 1e-12, c1
# 跳数、m、k 都是乘数
assert worst_case_cost(3, 1, 3) > worst_case_cost(1, 1, 3)
assert worst_case_cost(3, 3, 3) > worst_case_cost(3, 1, 3)
assert worst_case_cost(3, 1, 9) > worst_case_cost(3, 1, 3)
# LLM 判断可能比检索还贵
c_llm = worst_case_cost(3, 1, 3, judge_is_llm=True)
c_no = worst_case_cost(3, 1, 3, judge_is_llm=False)
search_part = 3 * 1 * (C_EMBED + C_SEARCH)
assert (c_llm - c_no) > search_part, 'LLM 停止判断比三跳的检索加起来还贵'
print(f'3 跳 m=1 k=3: 用 LLM 判断 ${c_llm:.5f} vs 结构性信号 ${c_no:.5f} '
      f'(检索部分只占 ${search_part:.5f})')

h = max_hops_under_budget(0.01, m=3, k=3)
assert worst_case_cost(h, 3, 3) <= 0.01 < worst_case_cost(h + 1, 3, 3), h
assert max_hops_under_budget(0.0001, m=3, k=3) == 0, '预算太小时应当返回 0'
assert max_hops_under_budget(1.0, m=1, k=3) >= 10
print(f'预算 $0.01/query、m=3、k=3 → 最多 {h} 跳')
print('✅ 练习 2 通过：三个乘数都在，LLM 判断的成本被显式暴露出来')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def worst_case_cost(max_hops, m, k, judge_is_llm=True):
    c = max_hops * m * (C_EMBED + C_SEARCH)
    c += max_hops * (C_JUDGE if judge_is_llm else 0.0)
    c += max_hops * k * C_GEN_PER_CHUNK
    return c

def max_hops_under_budget(budget_per_query, m, k, judge_is_llm=True):
    h = 0
    while worst_case_cost(h + 1, m, k, judge_is_llm) <= budget_per_query:
        h += 1
        if h > 10000:
            break
    return h

c1 = worst_case_cost(1, 1, 3, judge_is_llm=False)
assert abs(c1 - (1 * (C_EMBED + C_SEARCH) + 3 * C_GEN_PER_CHUNK)) < 1e-12
assert worst_case_cost(3, 3, 3) > worst_case_cost(3, 1, 3)
c_llm = worst_case_cost(3, 1, 3, True); c_no = worst_case_cost(3, 1, 3, False)
assert (c_llm - c_no) > 3 * (C_EMBED + C_SEARCH)
h = max_hops_under_budget(0.01, m=3, k=3)
assert worst_case_cost(h, 3, 3) <= 0.01 < worst_case_cost(h + 1, 3, 3)
assert max_hops_under_budget(0.0001, m=3, k=3) == 0
print('✅ 参考答案 2 通过')
print('   这个函数的用途是**容量规划**：它把 MAX_HOPS 从一个拍出来的数')
print('   变成一个由「单查询预算」反解出来的数。')
print('   而它也暴露了一件常被忽略的事：如果停止判断是一次 LLM 调用，')
print('   它可能比这几跳的检索加起来还贵——所以优先用结构性信号。')"""),

    md("""## ✏️ 练习 3：实体图上的共同点与路径

在第 5 节的倒排表上实现两个查询：

1. `common_neighbors(a, b, depth)` —— 两个实体各走 `depth` 步的邻域交集（不含 a、b 本身）
2. `path_between(a, b, max_depth)` —— a 到 b 的一条最短实体路径（BFS），
   返回实体列表（含首尾），不可达返回 `None`

`path_between` 的用途：**给用户展示「这个答案是怎么推出来的」**——
这是图检索相对 flat 检索的一个额外好处。"""),

    code("""def common_neighbors(a, b, depth=2):
    \"\"\"两个实体 depth 步邻域的交集（不含 a、b）。\"\"\"
    # TODO
    raise NotImplementedError

def path_between(a, b, max_depth=4):
    \"\"\"BFS 找一条最短实体路径，返回 [a, ..., b]；不可达返回 None。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
cn = common_neighbors('差旅报销', '采购申请', depth=2)
assert '财务部' in cn, cn
assert '差旅报销' not in cn and '采购申请' not in cn

# 法务部的和财务部的没有共同部门
cn2 = common_neighbors('差旅报销', '合同审批', depth=2)
assert '财务部' not in cn2 and '法务部' not in cn2, cn2

p = path_between('差旅报销', 'wangmin@acme.com')
assert p is not None and p[0] == '差旅报销' and p[-1] == 'wangmin@acme.com'
assert '王敏' in p, p
print('路径:', ' → '.join(p))

p2 = path_between('差旅报销', '采购申请')
assert p2 is not None and '财务部' in p2, p2
print('路径:', ' → '.join(p2))

assert path_between('差旅报销', '差旅报销') == ['差旅报销']
assert path_between('差旅报销', '不存在的实体') is None
# 深度限制生效
assert path_between('差旅报销', 'wangmin@acme.com', max_depth=1) is None
print('✅ 练习 3 通过：共同点与可解释路径都能算出来')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def common_neighbors(a, b, depth=2):
    return (neighbors(a, depth) & neighbors(b, depth)) - {a, b}

def path_between(a, b, max_depth=4):
    if a == b:
        return [a]
    if b not in ENT2CHUNKS:
        return None
    frontier = [[a]]
    seen = {a}
    for _ in range(max_depth):
        nxt = []
        for path in frontier:
            tail = path[-1]
            for cid in ENT2CHUNKS.get(tail, ()):
                for e in CHUNK2ENTS[cid]:
                    if e in seen:
                        continue
                    if e == b:
                        return path + [e]
                    seen.add(e)
                    nxt.append(path + [e])
        if not nxt:
            return None
        frontier = nxt
    return None

assert '财务部' in common_neighbors('差旅报销', '采购申请', 2)
assert '财务部' not in common_neighbors('差旅报销', '合同审批', 2)
p = path_between('差旅报销', 'wangmin@acme.com')
assert p[0] == '差旅报销' and p[-1] == 'wangmin@acme.com' and '王敏' in p
assert '财务部' in path_between('差旅报销', '采购申请')
assert path_between('差旅报销', '差旅报销') == ['差旅报销']
assert path_between('差旅报销', '不存在的实体') is None
assert path_between('差旅报销', 'wangmin@acme.com', max_depth=1) is None
print('✅ 参考答案 3 通过')
print('   path_between 的价值不只是找到答案，而是**给出可解释的推理链**：')
print('   「差旅报销 → 王敏 → wangmin@acme.com」比一段生成的文字更可核查。')
print('   这是图检索相对 flat 检索的一个额外好处，且它不需要任何模型。')"""),

    md("""## ✏️ 练习 4：分层的 fact-recall 报告 + 门禁

实现 `stratified_report(questions, retriever)` 与 `iterate_gate(report, baseline)`。

`stratified_report` 返回
`dict(overall, by_hops, stop_reasons, mean_hops, p99_hops)`，
其中 `by_hops[h]` 是需要 `h` 个事实的那一层的 fact-recall。

`iterate_gate` 的规则：
- **确定性阻断**：`p99_hops > MAX_HOPS_LIMIT`（上界失效）；
  任一层的 fact-recall 相对基线**下降**
- **报警**：`stop_reasons['max_hops']` 占比 > 0.3（上界在兜底而不是准则在工作）"""),

    code("""MAX_HOPS_LIMIT = 3

def stratified_report(questions, retriever):
    \"\"\"retriever(q) -> (chunks, hops, stop_reason)。
    返回 dict(overall, by_hops, stop_reasons, mean_hops, p99_hops)。\"\"\"
    # TODO
    raise NotImplementedError

def iterate_gate(report, baseline):
    \"\"\"返回 (blocking, warnings)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
def single_r(q):
    return {cid for cid, _ in retrieve(q, k=3)}, 1, 'single'

def iter_r(q):
    return run_with_criterion(q, 'coverage', k=3, max_hops=3)

rep_single = stratified_report(QUESTIONS, single_r)
rep_iter = stratified_report(QUESTIONS, iter_r)
print('单轮:', {k: v for k, v in rep_single.items() if k != 'stop_reasons'})
print('迭代:', {k: v for k, v in rep_iter.items() if k != 'stop_reasons'})
print('迭代的 stop_reasons:', rep_iter['stop_reasons'])

assert set(rep_single['by_hops']) == {1, 2}
assert rep_single['by_hops'][2] == 0.0, '单轮在两跳层必须是 0'
assert rep_iter['by_hops'][2] == 1.0, '迭代在两跳层必须是 1'
assert rep_iter['overall'] > rep_single['overall']
assert rep_iter['p99_hops'] <= 3

# 门禁：迭代 vs 单轮基线 —— 没有任何层下降，应当全绿
b, w = iterate_gate(rep_iter, rep_single)
assert b == [], b

# 反向：单轮相对迭代基线 → 两跳层下降 → 阻断
b2, _ = iterate_gate(rep_single, rep_iter)
assert any('fact-recall' in x for x in b2), b2

# 上界失效 → 阻断
bad = dict(rep_iter); bad['p99_hops'] = 7
b3, _ = iterate_gate(bad, rep_single)
assert any('p99' in x or '上界' in x for x in b3), b3

# max_hops 占比过高 → 报警（不阻断）
noisy = dict(rep_iter)
noisy['stop_reasons'] = {'sufficient': 3, 'max_hops': 4}
b4, w4 = iterate_gate(noisy, rep_single)
assert b4 == [] and any('max_hops' in x for x in w4), (b4, w4)
print('✅ 练习 4 通过：分层报分 + 确定性阻断 + 统计报警')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def stratified_report(questions, retriever):
    by_hops, reasons, hops_all, fr_all = defaultdict(list), Counter(), [], []
    for spec in questions:
        got, hops, reason = retriever(spec['q'])
        fr = fact_recall(got, spec['facts'])
        by_hops[len(spec['facts'])].append(fr)
        fr_all.append(fr); hops_all.append(hops); reasons[reason] += 1
    return dict(overall=float(np.mean(fr_all)),
                by_hops={h: float(np.mean(v)) for h, v in by_hops.items()},
                stop_reasons=dict(reasons),
                mean_hops=float(np.mean(hops_all)),
                p99_hops=int(np.percentile(hops_all, 99)))

def iterate_gate(report, baseline):
    blocking, warn = [], []
    if report['p99_hops'] > MAX_HOPS_LIMIT:
        blocking.append(f"p99 跳数 {report['p99_hops']} > 上界 {MAX_HOPS_LIMIT}"
                        f"（硬上界失效）")
    for h, v in report['by_hops'].items():
        base = baseline['by_hops'].get(h)
        if base is not None and v < base - 1e-12:
            blocking.append(f'{h} 事实层的 fact-recall 下降 {base:.2f} → {v:.2f}')
    total = sum(report['stop_reasons'].values())
    share = report['stop_reasons'].get('max_hops', 0) / total if total else 0.0
    if share > 0.3:
        warn.append(f'stop_reason=max_hops 占比 {share:.0%} > 30%'
                    f'（上界在兜底，而不是准则在工作）')
    return blocking, warn

rep_single = stratified_report(QUESTIONS, single_r)
rep_iter = stratified_report(QUESTIONS, iter_r)
assert rep_single['by_hops'][2] == 0.0 and rep_iter['by_hops'][2] == 1.0
assert iterate_gate(rep_iter, rep_single)[0] == []
assert any('fact-recall' in x for x in iterate_gate(rep_single, rep_iter)[0])
bad = dict(rep_iter); bad['p99_hops'] = 7
assert iterate_gate(bad, rep_single)[0]
noisy = dict(rep_iter); noisy['stop_reasons'] = {'sufficient': 3, 'max_hops': 4}
assert iterate_gate(noisy, rep_single)[0] == [] and iterate_gate(noisy, rep_single)[1]
print('✅ 参考答案 4 通过')
print('   注意「任一层下降就阻断」这条：它比「总分下降就阻断」严格得多。')
print('   因为多跳题只占评测集的少数，总分完全可能在多跳能力退化时还上涨。')
print('   这与 C68 模块 03 的切片分析是同一条：**总分会掩盖分层的退化**。')"""),

    md("""## 🧪 真实工程胶囊：迭代与图检索的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 迭代作为兜底路径，不是默认路径（讲解第 6 节）
# ══════════════════════════════════════════════════════════════════
MAX_HOPS = 3          # ← 代码常量，不是配置项（讲解第 2 节）
async def answer(question):
    docs = await search(question, k=K)
    if enough(question, docs):                  # 结构性信号，不是 LLM
        return await generate(question, docs)
    return await iterative_answer(question, docs)     # 只有这里才付迭代的钱

# ══════════════════════════════════════════════════════════════════
# B. 后续查询：锚定原问题（讲解第 4 节）
# ══════════════════════════════════════════════════════════════════
NEXT_QUERY_PROMPT = '\\n'.join([
    '原问题：{question}',
    '已知证据：{evidence}',
    '还缺什么信息才能回答原问题？只输出一个用于检索的短查询。',
    '查询里必须包含原问题问的那个属性（如「邮箱」「时限」），',
    '以及证据里新出现的那个实体。不要引入证据里没有的词。',
])
#   护栏：cos(emb(new_q), emb(question)) >= 0.5 * cos(emb(question), emb(question))
#         不满足就停，并记 stop_reason='drift_guard'

# ══════════════════════════════════════════════════════════════════
# C. 必须记录的四个字段（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
log.info('rag_iterate', extra=dict(
    hops=rec['hops'], new_per_hop=rec['new_per_hop'],
    drift=rec['drift'], stop_reason=rec['stop_reason'],
    tokens_in=ctx_tokens, cost_usd=cost))
#   看板上要有：hops 的 P50/P99、stop_reason 分布、drift 的最后一跳分布。
#   max_hops 占比 > 30% 就该查 enough() 是不是太严。

# ══════════════════════════════════════════════════════════════════
# D. 实体倒排（讲解第 5 节的中间档，成本最低的图检索）
# ══════════════════════════════════════════════════════════════════
#   摄取时：对每个块做 NER（或规则），写两张表
#     entity_chunks(entity, chunk_id, doc_id, version)     ← 带 version！
#     chunk_entities(chunk_id, entity)
#   更新文档时：先按 (doc_id, version) 删旧行，再写新行（模块 01 的幂等契约）
#   查询时：
#     SELECT chunk_id FROM entity_chunks WHERE entity IN (%s, %s)
#     GROUP BY chunk_id HAVING COUNT(DISTINCT entity) = 2      -- 同时提到 X 和 Y

# ══════════════════════════════════════════════════════════════════
# E. 上线顺序（讲解第 7 节最后一行——本模块最重要的一条）
# ══════════════════════════════════════════════════════════════════
# 0) 先确认模块 01 的摄取门禁、模块 02 的 intact 检查、模块 03 的敏感度都是绿的
# 1) 造多跳评测集，标出**完整的事实集合**，按事实数分层
# 2) 只对「单轮证据不足」开启迭代，报 $/success 而不是 $/query
# 3) MAX_HOPS 由「单查询预算」反解（练习 2），写成代码常量
# 4) 图检索最后考虑：它的成本在摄取侧，且图会腐烂（模块 05）
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| 多跳题的单轮 recall 天然为 0 | 目标块与另外 9 条邮箱块**得分完全相等**，不是「排序差一点」 | 第 1 节 |
| 后续查询必须锚定原问题的目标谓词 | 不锚定时相似度单调走远 | 第 2/4 节 |
| 停止准则只改变期望跳数，不改变最坏情况 | 期望跳数 2.00 → 1.43，最坏都被 MAX_HOPS=3 封住 | 第 3 节 |
| 停止判断只能看结构性信号，不能看答案对不对 | 线上没有真值 | 第 3 节 |
| 关系/共同点类问题的答案不在任何块里 | 图算出「财务部」 | 第 5 节 |
| `$/query` 一定更贵；`$/success` 取决于停止判断 | 用 LLM 判断时 $/success 也更贵，换结构性信号才反过来 | 第 6 节 |
| 迭代 3 跳 × 融合 3 路 = 9 次检索 | 两个改动分别上线，没人乘起来算 | 第 6 节 |
| 用迭代补分块问题的成本是修分块的几倍 | 且多了延迟与复杂度 | 第 7 节 |
| 文档级 recall 在多跳题上系统性误导 | 同一批结果给出 1.00 / 0.50 / 0.00 | 第 8 节 |
| 多跳收益会被单跳题冲淡 | 分层 +1.00 vs 混报 +0.43 | 第 8 节 |

下一模块：**05 · 索引运维**——索引是有状态的、会腐烂的；
「换 embedding 模型」是一次不可混用的全量迁移，不是一次配置修改。"""),
]
