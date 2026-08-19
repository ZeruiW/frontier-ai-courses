# -*- coding: utf-8 -*-
"""C65 模块 05 · 白板沟通与模拟演练（结构化问题求解与面试沟通 · 收官模块）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "本课 C65-00~04 全部——尤其是 C65-00 的沟通三铁律（结论先行/显式说假设/主动暴露不确定性）"
                 "与 C65-04 的收敛话术，本模块把它们全部整合进「说」这一件事里"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_mock_communication.ipynb（回答结构检查器 / '
                       '句式库与中英对照表 / 10 题模拟演练引擎（出题→计时→自评→弱项统计） / 面试前 24 小时检查清单）'),
    ("核心参考", "见本模块末节「研究前沿与开放问题」的 paper callout"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("think-aloud", "边想边说：把思考流程外化的句式库", "".join([
        P("这是全课程收官模块，也是最容易被低估的一节——因为它练的不是「知道什么」，而是"
          "<strong>把已经知道的东西说出来</strong>。前面五个模块（估算、诊断、权衡、模糊需求澄清）"
          "教的都是<em>怎么想</em>；这一节教的是<em>怎么让面试官看见你在想</em>。"
          "两者听起来相似，实际是完全不同的技能——很多候选人能想清楚，却在“说”这一步大幅失分。"),
        CALLOUT("intuition", "<strong>面试官打分的对象不是你脑子里的那个正确答案，是你嘴里说出来的那个思考过程。</strong>"
                             "一个没说出口的正确判断，在评分表上等于不存在；一个说出口的、"
                             "带着「我现在不确定，但我倾向于……」的半成品判断，反而能拿到分——"
                             "<em>因为分数评的是过程的可见度，不是结果的正确度。</em>"),
        P("「边想边说」最大的障碍不是不知道该说什么，而是<strong>大脑天然习惯把思考和表达分成两个串行阶段</strong>"
          "（先想清楚，再组织语言说出来）。面试要求你把这两个阶段并行——"
          "解法是准备一套<strong>句式库</strong>，让「进入下一个思考步骤」这件事本身触发一句可以脱口而出的话，"
          "从而不需要临场现想怎么表达。"),
        TABLE(["思考动作", "触发的句式（中）", "作用"], [
            ["开始分解问题", "「我先把这个问题拆成几块：……」", "把「分解」这个内部动作显式广播出来"],
            ["提出一个假设", "「这里我先假设……，原因是……」", "把隐含决定摊在明处（呼应 C65-00 沟通三铁律）"],
            ["注意到一个不确定点", "「这一步我不是很确定，先按……走，如果不对我们再调整」", "主动暴露不确定性，防止面试官以为你没意识到"],
            ["否定了自己刚才的想法", "「等一下，我刚才漏了一种情况：……，让我重新想一下」", "展示自我批判是加分项，不是丢脸的事"],
            ["得出一个阶段性结论", "「所以这一步的结论是……，这会影响下一步……」", "让面试官能跟上你的节奏，随时可以打断"],
            ["准备切换到下一个大步骤", "「好，这部分先到这里；接下来我看一下……」", "给对话加书签，方便面试官跟进或打断"],
        ]),
        DUAL(
            "直白地说：这套句式就是给你的思考过程装上「字幕」。观众（面试官）不需要读心术，"
            "只需要跟着字幕走，就知道你现在在哪一步、为什么在这一步、下一步打算去哪。"
            "<strong>没有字幕的思考，哪怕内容再精彩，观众也只会看到一段沉默的黑屏。</strong>",
            "更严谨地说，这本质是把<span class=\"term\">内部言语</span>（inner speech，"
            "认知科学里描述人类默会思考时使用的准语言表征）<strong>转译成外部言语</strong>的过程。"
            "转译天然有延迟和损耗，直接现场翻译会占用宝贵的工作记忆容量，导致「一边说话一边卡壳」。"
            "预先固化一套触发式句式，相当于把翻译这道工序提前编译好，运行时只需要「模式匹配 + 填空」，"
            "大幅降低了实时转译的认知负荷。",
        ),
        CALLOUT("warn", "<strong>句式库不是要背台词。</strong>如果你逐字背下一段「标准回答」，"
                        "面试官只要往旁边追问一句，你就会露馅——因为背的是内容，不是骨架。"
                        "正确的练法是把左边那一列「思考动作」练成条件反射：<em>只要脑子里出现这个动作，"
                        "嘴就自动开始说对应类型的句子，具体内容永远是临场的。</em>"),
    ])),

    # ============================================================== 2
    ("structured-expression", "结构化表达：结论先行 / 金字塔原理 / 三点法", "".join([
        P("光「说出来」还不够——说出来的东西如果是一团乱麻，面试官要花额外的精力去重组你的逻辑，"
          "这个重组成本本身就会拉低你的沟通分。<strong>结构化表达解决的是「说的顺序」问题</strong>，"
          "三个最实用的工具如下。"),
        TABLE(["工具", "结构", "适用场景", "反例"], [
            ["<strong>结论先行</strong>", "先说答案/判断，再说依据", "面试官问「你觉得应该先做哪个」这类需要立场的问题", "先讲一堆背景，讲到一半面试官已经不知道你到底支持哪个方案"],
            ["<strong>金字塔原理</strong>", "顶层结论 → 二级论据（通常 3 条以内）→ 每条论据下的支撑细节", "解释一个复杂判断，尤其是需要说服对方的场合", "论据和细节混在一起讲，听众分不清哪句是论点、哪句是论据"],
            ["<strong>三点法</strong>", "「有三个原因/三个维度/三个方案」，逐一编号讲", "临场组织一个尚未预先构思好结构的回答", "东想到一点说一点，讲完自己都数不清一共说了几条理由"],
        ]),
        ASCII("""金字塔原理的骨架（自顶向下）
┌──────────────────────────────────────────────┐
│ 顶层：结论 / 判断                              │
│  "我会优先做 A，而不是 B 或 C"                 │
└───────────────┬────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
  论据 1       论据 2       论据 3
 "成本最低"   "风险最小"   "验证最快"
     │           │           │
   支撑细节    支撑细节    支撑细节
  (数字/案例) (数字/案例) (数字/案例)

讲的顺序永远是从上往下：先给结论，
面试官如果同意，你可以跳过细节直接往下讲；
如果他对某条论据有疑问，再下钻到细节。"""),
        DUAL(
            "「结论先行」最反直觉的地方在于：很多人担心「结论都还没论证，怎么能先说」，"
            "于是习惯把证明过程铺垫完才敢下结论——<strong>这是学术写作的顺序，不是面试对话的顺序。</strong>"
            "面试对话本质是一场信息带宽极其有限的实时交互，先给结论能让面试官<em>立刻决定要不要深挖某一部分</em>，"
            "这本身就是在为双方节省时间。",
            "从信息论的角度看，金字塔原理是一种<span class=\"term\">渐进式细化</span>"
            "（progressive refinement）的编码方式：接收方（面试官）可以在任意深度提前截断接收——"
            "听完结论就懂了大意，需要更多细节时才继续下钻。这与「先发送低分辨率略图再逐步补充细节」"
            "的渐进式图像传输是同一个信息组织原则，只是应用在语言而不是像素上。",
        ),
        CALLOUT("intuition", "<strong>三点法的隐藏价值不是「三」这个数字本身，而是它逼你在开口之前先做一次快速归纳。</strong>"
                             "哪怕临场只想出两点，也不要凑数说「第三点是……呃……」——"
                             "宁可诚实说「主要是两个原因」，也不要为了凑够三点而临时编造一条站不住脚的理由，"
                             "那会立刻被追问戳穿。"),
    ])),

    # ============================================================== 3
    ("stuck-recovery", "卡住时的三种脱困法：不要让沉默替你说话", "".join([
        P("即使准备再充分，白板上也一定会有卡壳的时刻——这不是失败信号，"
          "<strong>沉默本身才是失败信号，卡壳时如何反应才是评分点。</strong>"
          "C62 模块 00 已经讲过「沉默超过 30 秒」是编码面试的硬扣分项，这个规律在白板沟通题里同样成立，"
          "甚至更严重，因为白板题往往没有代码可以「先写起来再说」当退路。"),
        TABLE(["脱困法", "怎么做", "适用情形", "话术示例"], [
            ["<strong>① 退回上一层</strong>", "回到上一个你确信站得住的结论，重新审视是哪一步开始站不住", "发现自己在某个分支想太细，已经忘了最初想解决什么", "「我退一步——我们最初想解决的是……，我刚才好像绕远了，让我重新对齐一下。」"],
            ["<strong>② 举具体例子</strong>", "用一个极简的具体数字/案例走一遍，让抽象假设露出破绽或获得确认", "抽象推理卡住，无法判断某个方案是否成立", "「我拿一个具体例子走一遍：假设只有 100 张训练图，这个方法还成立吗……」"],
            ["<strong>③ 明说需要一分钟</strong>", "直接说出你需要安静思考的时间，而不是尴尬地沉默", "需要真正安静下来做一次心算或理清多个分支", "「这里有两个方向在打架，给我 20-30 秒理一下，我在权衡……」"],
        ]),
        ASCII("""卡住了 —— 三选一，但**永远选一个说出口**，不要选"沉默"
   │
   ├─ 退回上一层：  "我退一步——最初要解决的是……"
   ├─ 举具体例子：  "我拿一个具体例子走一遍：……"
   └─ 明说要时间：  "给我 20-30 秒，我在权衡……"
   │
   （这三条本身都不消耗多少时间，
    但都能把"卡住"从一个负面信号
    转换成一个"正在工作"的信号）"""),
        DUAL(
            "三种方法的共同点是：<strong>它们都把「卡住」这件事本身说了出来，而不是试图隐藏它。</strong>"
            "很多候选人本能地觉得「说出我卡住了」会显得不专业，于是选择沉默硬撑——"
            "但面试官分不清「沉默地想出办法」和「沉默地卡死」，只能按更差的那种记分。"
            "反而是「我意识到自己卡在哪、我知道该怎么脱困」这件事，展示的是<em>更高</em>而不是更低的专业度。",
            "三种方法分别对应三类卡壳的根因：<strong>①</strong> 对应「路径偏离」（走远了忘了起点），"
            "<strong>②</strong> 对应「抽象层级过高」（缺少具体锚点验证假设），"
            "<strong>③</strong> 对应「多分支决策未决」（需要串行化并行涌现的多个念头）。"
            "诊断出自己此刻属于哪一类，能让你更快选中对的脱困法，而不是三种都试一遍浪费时间。",
        ),
        CALLOUT("danger", "<strong>最差的应对不是选错脱困法，是干脆什么都不做地等待。</strong>"
                          "如果连续 15-20 秒没有任何输出（既没有说话也没有在白板上写字），"
                          "面试官大概率会主动打断你——这本身不算严重扣分，但<em>意味着你把「先自救」的分数拱手让人了</em>。"
                          "养成的肌肉记忆应该是：卡住的瞬间，第一反应是从上面三种里选一句话说出口，而不是继续沉默思考。"),
    ])),

    # ============================================================== 4
    ("formats", "白板 / 共享屏幕 / 纯语音：三种形式的差异", "".join([
        P("同样的沟通内容，在不同的媒介下呈现方式必须调整——很多人只练了一种形式，"
          "到了另一种形式上会明显不适应。面试通知邮件里通常会写清楚用哪种工具，<strong>提前确认并试用一次</strong>。"),
        TABLE(["形式", "典型工具", "优势", "陷阱", "应对策略"], [
            ["<strong>实体白板</strong>", "线下面试的真实白板", "空间自由、可以画大图、面试官看得最直观", "字迹潦草会被扣分；空间用完了没地方改", "先在角落画一个「草稿区」；框架图和细节分区，别混着画"],
            ["<strong>共享屏幕 + 协作文档</strong>", "Google Doc / CoderPad / Excalidraw", "可以打字更快、方便复制粘贴表格", "没有语法高亮、没有自动缩进、打字磕巴会被看见", "关闭自动更正/自动缩进导致的干扰；先想好再打字，减少来回删改"],
            ["<strong>纯语音（无共享画面）</strong>", "电话面试 / 早期筛选轮", "没有画面负担，可以完全专注表达", "对方看不到你的结构，只能靠语言本身传递层次", "<strong>必须靠口播显式建立结构</strong>：「我讲三部分：第一……第二……第三……」"],
        ]),
        DUAL(
            "三种形式里，<strong>纯语音是对结构化表达要求最高的一种</strong>——"
            "没有画面兜底，你说的每一句话都要自带「路标」。反过来，白板和共享屏幕给了你一个视觉外挂："
            "把关键结构画出来，说漏的部分观众还能从图上补全。<em>但这个外挂也是陷阱</em>——"
            "很多人过度依赖画图，画完却不解释，面试官只能自己猜你想表达的逻辑关系。",
            "从<span class=\"term\">通道容量</span>（channel capacity）的角度看，纯语音信道的带宽最窄，"
            "所以对信息的<em>预先编码质量</em>要求最高——这正是「结论先行 / 三点法」这类显式结构化工具在纯语音场景下"
            "收益最大的原因。共享屏幕信道带宽居中，但存在延迟（打字速度低于语速，且容易分心去调格式）。"
            "白板信道带宽最宽，但要求发送者（你）具备把逻辑关系正确映射到二维空间布局的能力——"
            "这是三种形式里唯一需要「空间规划」这项额外技能的。",
        ),
        CALLOUT("warn", "<strong>共享文档形式最容易被低估的坑：没有自动缩进和语法高亮。</strong>"
                        "如果你平时用惯了 IDE，第一次在纯文本框里打字会觉得「怎么这么难打」——"
                        "缩进错位、括号不匹配的感觉会分散你的注意力。<em>务必提前用同款工具跑一遍，"
                        "而不是在正式面试时第一次遇到这个摩擦。</em>"),
    ])),

    # ============================================================== 5
    ("english-expressions", "英文面试的关键表达：中英对照句库（务必扎实）", "".join([
        P("JD 明确写的是英文岗位，一面很可能全程或部分用英文进行。<strong>这一节是本模块的重中之重</strong>——"
          "中文思路再清楚，如果关键的澄清、假设、权衡、承认不确定这几类话在英文里说得磕磕巴巴，"
          "面试官对你专业度的判断会被severely打折。下面按「功能」而不是「话题」分类，"
          "因为这几类功能在任何题目里都会反复用到。"),
        H3("① 澄清 Clarifying questions"),
        TABLE(["中文", "English"], [
            ["我先复述一遍，确认我理解对了：……", "Let me restate to make sure I understand correctly: ..."],
            ["在我开始之前，我想确认几件事。", "Before I dive in, I'd like to confirm a few things."],
            ["您说的“效果”具体指哪个指标？", "When you say “improve the result,” which metric are you referring to specifically?"],
            ["这个有没有延迟或算力上的限制？", "Are there any constraints on latency or compute budget?"],
            ["这次明确不需要考虑的是什么？", "Is there anything that's explicitly out of scope for this?"],
        ]),
        H3("② 假设 Stating assumptions"),
        TABLE(["中文", "English"], [
            ["我先假设……，如果不对请随时打断我。", "I'll assume ... for now — please stop me if that's not right."],
            ["我先按 A 这个假设往下展开；如果不对，需要的话我们再切到 B。", "I'll go with assumption A for now; if it turns out to be wrong, we can pivot to B."],
            ["鉴于您没提到重训预算，我假设这次不涉及重新训练整个模型。", "Since retraining budget wasn't mentioned, I'll assume this doesn't involve retraining the whole model."],
        ]),
        H3("③ 权衡 Tradeoffs"),
        TABLE(["中文", "English"], [
            ["这里有一个权衡：……", "There's a tradeoff here between ... and ..."],
            ["我选 A 而不是 B，是因为……，代价是……", "I'm going with A over B because ...; the cost of that is ..."],
            ["这是可逆的决定，所以我倾向于先快速试一下。", "This decision is reversible, so I'd lean toward moving fast and validating quickly."],
            ["如果换一个约束（比如延迟预算更宽松），我的选择会变成……", "If the constraint changed — say, a looser latency budget — I'd lean toward ... instead."],
        ]),
        H3("④ 承认不确定 Acknowledging uncertainty"),
        TABLE(["中文", "English"], [
            ["这一点我不是很确定，我的第一反应是……，但我想再确认一下。", "I'm not fully certain here — my first instinct is ..., but I'd want to double-check."],
            ["这个我没有直接经验，但基于……的原理，我推测应该是……", "I don't have direct experience with this, but based on ..., my best guess would be ..."],
            ["这个具体数字我不确定，但我可以给你一个数量级的估算。", "I don't know the exact number, but I can give you an order-of-magnitude estimate."],
            ["我不知道确切答案，但我会这样去查证：……", "I don't know the exact answer, but here's how I'd go find out: ..."],
        ]),
        CALLOUT("intuition", "<strong>这四类句子的共同结构是「先给一个可执行的立场，再补上限定条件」</strong>——"
                             "英文里对应的语法标志通常是 <em>“I'll assume… but…”</em> "
                             "<em>“I'm not fully certain, but my instinct is…”</em> 这种「让步」句式。"
                             "<strong>反面例子</strong>是只说 <em>“I don't know”</em> 然后停住——"
                             "这在英文语境下听起来比中文更生硬、更像放弃，一定要在后面接一句你会怎么处理。"),
        DUAL(
            "很多母语非英语的候选人会把「我不确定」直译成生硬的 <em>“I don't know”</em>，"
            "这句话单独存在时传递的信号是「到此为止」，而不是「我在诚实地标注这一点的置信度」。"
            "<strong>加一个从句就能扭转整个观感</strong>：<em>“I don't know for certain, but here's my best guess and how I'd verify it.”</em>"
            "——这句话长了几个词，传递的专业度却完全不同。",
            "这也解释了为什么 C65-00 的「诚实暴露不确定性」这条铁律在英文语境下需要<strong>更刻意的句式支撑</strong>："
            "中文里「我不确定，但……」的让步结构非常自然，几乎不需要特别设计；"
            "而英文的让步从句（<em>but / though / that said / my best guess is</em>）需要被显式练习，"
            "否则母语惯性会让人说完否定部分就停下，漏掉补救的那半句。",
        ),
    ])),

    # ============================================================== 6
    ("time-and-closing", "时间管理与主动收尾 · 反问环节", "".join([
        P("白板题通常没有 C62 那种「45 分钟切成六段」的精细预算，但<strong>粗粒度的时间意识仍然是硬性要求</strong>——"
          "一道开放题如果讲了 20 分钟还没有任何阶段性结论，面试官会认为你不知道自己在往哪个方向走。"),
        TABLE(["阶段", "建议占比（一道 15-20 分钟的开放题）", "该产出什么"], [
            ["澄清与收敛", "15%–20%", "一个有边界的题面 + 一句确认话术（见 C65-04）"],
            ["主体分析/方案展开", "55%–65%", "结构化的论证：结论 + 2-3 条支撑论据 + 关键数字或例子"],
            ["权衡与风险", "10%–15%", "至少一处主动说出「代价是什么」「什么情况下这个方案会失效」"],
            ["主动收尾 + 反问", "5%–10%", "总结 + 反问面试官一个真实的问题"],
        ]),
        H3("主动收尾：不要等面试官问「还有别的吗」"),
        P("时间快到时，<strong>主动做一次收尾陈述</strong>比被追问着结束效果好得多："
          "「我先总结一下：我们的方案是……，关键假设是……，最大的风险是……，"
          "如果有更多时间我会进一步验证……」——这句话同时展示了结构化能力、对不确定性的诚实，"
          "以及时间意识本身。"),
        H3("反问环节：这是最后一次留下印象的机会"),
        UL([
            "<strong>问真实的技术问题</strong>：「你们现在 TSR 的召回率主要卡在哪个场景？」——"
            "这既显示了真实的好奇心，也可能问出对你后续答题有用的信息。",
            "<strong>避免问网上查得到的问题</strong>（「公司主要业务是什么」这类），会显得没做功课。",
            "<strong>可以追问刚才那道题的真实答案</strong>：「你们实际是怎么处理这个的？」——"
            "面试官通常乐于分享，这也是一次不着痕迹的加分互动。",
            "<strong>不要一次问三个以上</strong>，反问环节通常只有 2-3 分钟，问一个有质量的问题胜过问五个泛泛的问题。",
        ]),
        DUAL(
            "主动收尾这件事之所以重要，是因为面试官脑子里最后停留的印象，"
            "很大程度上决定了他事后回忆打分时的锚点——<strong>一场表现平平但收尾干净利落的面试，"
            "常常比一场分析精彩但戛然而止的面试拿分更高</strong>，这被称为峰终定律"
            "（peak-end rule）在面试场景下的体现：人们对一段体验的记忆，"
            "主要取决于高峰时刻和结束时刻的感受，而不是全程的平均值。",
            "反问环节本质是面试双向选择的体现——公司在评估你，你也在评估这份工作是否匹配自己。"
            "<em>把反问单纯当作「表演关心」是短视的</em>：真正有价值的反问应该是你确实想知道、"
            "会影响你判断这份工作是否值得的信息。这既是加分策略，也是对自己负责的实际动作。",
        ),
        CALLOUT("warn", "<strong>不要用反问环节临时救场式地展示知识面</strong>（比如突然背一段与话题无关的论文名词）。"
                        "面试官分辨得出「真实好奇」和「表演」的区别，后者往往适得其反。"),
    ])),

    # ============================================================== 7
    ("mock-drills", "10 个开放题的完整模拟演练", "".join([
        P("把前六节的所有工具串起来，走一遍完整题库。每题给出<strong>评分要点</strong>（面试官在听什么）、"
          "<strong>满分答法骨架</strong>（结构，不是逐字答案）与<strong>常见失分点</strong>。"
          "notebook 里会把这十题做成可计时、可自评的演练引擎。"),
        TABLE(["#", "题目", "评分要点（面试官在听什么）", "满分答法骨架", "常见失分点"], [
            ["1", "「提升 TSR 效果，你会怎么做？」", "是否先收敛边界、是否给出可执行排序", "澄清六维度 → 收敛假设 → RICE 排序 → 分阶段计划（见 C65-04）", "上来就讲技术方案，没有先定义“效果”是什么"],
            ["2", "「这个检测器上线一周后指标掉了，你怎么排查？」", "是否用结构化诊断而不是罗列猜测", "先分清是数据/模型/部署哪一层 → 二分定位 → 可证伪的假设（见 C65-02）", "一次性列出十个可能原因但没有排查顺序"],
            ["3", "「给你两个月和一个工程师，你会先做检测精度还是先做部署稳定性？」", "是否显式列出维度并说清放弃了什么", "列维度 → 打分 → 说明帕累托关系（见 C65-03）", "只给结论不给理由，或含糊说“都重要”"],
            ["4", "「如果你只能加一种数据，你会加哪种？」", "是否用影响/成本/不确定性排序而不是直觉判断", "候选集合 → RICE 打分 → 排序理由", "凭直觉说一个方向，没有对比其他候选"],
            ["5", "「估算一下给这个系统采集训练数据需要多久。」", "是否用锚点数字 + 分解，而不是瞎猜一个数", "分解到子任务 → 锚点数字 → 相乘 → 双路径校验（见 C65-01）", "直接编一个数字，说不出是怎么算出来的"],
            ["6", "「你怎么向一个非技术背景的产品经理解释这个方案的风险？」", "是否结论先行、是否避免行话堆砌", "先说结论性风险 → 类比而非行话 → 给出应对措施", "满口专业术语，PM 听不懂也不敢打断"],
            ["7", "「这个方案在夜间场景可能会失效，你怎么和团队沟通这件事？」", "是否主动暴露不确定性而不是掩盖", "先说现象 → 假设根因 → 提出验证计划 → 说明当前不确定的程度", "把话说得比实际更有把握，掩盖了未验证的部分"],
            ["8", "「给你三个候选方案，客户临时把预算砍半，你怎么办？」", "是否能快速重新排序而不是原地卡住", "重新计算约束下的可行集 → 更新排序 → 说明砍掉了什么", "抱怨约束不合理，而不是给出调整后的方案"],
            ["9", "「你和另一位工程师对某个技术方案有分歧，怎么解决？」", "是否给出可验证的判据而不是诉诸权威或情绪", "列出分歧背后的假设 → 设计一个能分辨对错的小实验 → 谁的假设被验证就用谁的方案", "说“我觉得我的经验更多”而不提出可验证的判据"],
            ["10", "「如果这次的方案没达到预期，你怎么复盘？」", "是否愿意承认失败并展示学习闭环", "对比预期与实际 → 归因（数据/模型/评测/沟通）→ 下一步行动", "把失败归咎于外部因素，不做自我审视"],
        ]),
        CALLOUT("intuition", "<strong>这十题看起来主题各不相同，但骨架高度重复：定义边界 → 结构化展开 → 显式权衡/假设 → "
                             "主动暴露不确定性 → 给出下一步。</strong>这正是 C65-00 四步框架在十个不同外壳下的反复出现——"
                             "练熟骨架，比针对每道题分别背答案划算得多。"),
        CALLOUT("paper", "本节十题的评分要点与骨架，会在配套 notebook 里做成一个「出题 → 计时 → 自评 → 弱项统计」的"
                        "演练引擎——把这张表当作 notebook 里 `DRILL_BANK` 数据结构的说明书来读。"),
    ])),

    # ============================================================== 8
    ("frontier", "研究前沿与开放问题", "".join([
        P("白板沟通与模拟演练是整门课的收官，也是离「面试评估本身如何被验证」这个问题最近的一节——"
          "下面几条更长期的问题，会影响你怎么看待「练沟通」这件事的边际价值。"),
        UL([
            "<strong>结构化表达的训练效果能持续多久？</strong>沟通技巧类似于运动技能，"
            "存在明显的<span class=\"term\">技能衰退</span>（skill decay）——如果面试前一周高强度练习、"
            "面试前一天完全不碰，效果会显著下降。<em>这解释了为什么 notebook 里的模拟演练引擎要设计成"
            "可重复使用的训练工具，而不是一次性的题库——它更接近体育训练里的“保持手感”，而不是刷题式的“一次通关”。</em>",
            "<strong>「峰终定律」在面试评分里到底有多强？</strong>本模块引用它来支持「主动收尾」的价值，"
            "但需要老实承认：这条经验规律主要来自消费体验与疼痛记忆的研究，把它直接套用到「面试官事后打分」"
            "这个场景，目前缺少专门的验证。<em>可以合理预期它部分成立（人类记忆机制的通用规律），"
            "但强度可能因面试官是否当场记录评分表而有很大差异——当场逐项打分的评委，峰终效应会弱得多。</em>",
            "<strong>非母语者的英文沟通劣势能被结构化训练弥补到什么程度？</strong>语言流利度和逻辑结构化"
            "是两个可分离的能力——已有证据支持「即使语法不完美，高度结构化的表达仍然显著提升可理解度和可信度」，"
            "这正是本模块把英文句库按「功能」（澄清/假设/权衡/不确定性）而非「话题」组织的原因："
            "<em>功能句式的复用率远高于话题内容，投入产出比也更高。</em>",
            "<strong>LLM 面试官会如何改变这门课教的内容？</strong>越来越多公司用 AI 做第一轮技术面试的预筛选。"
            "已知的是当前的 AI 面试官对「结构化程度」这类可被浅层模式识别的信号异常敏感"
            "（结论先行、显式说出假设这类句式，恰好是最容易被自动化评分系统捕捉到的特征），"
            "<em>这意味着本模块教的技巧短期内不会贬值，反而可能因为评估自动化而变得更重要——"
            "但长期看，一旦面试官本身也是能做深度追问的模型，纯粹依赖句式模板而缺乏真实推理内容的回答"
            "会更容易被戳穿，这又把重心带回了前四个模块的实质内容。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Barbara Minto, <em>The Pyramid Principle</em>——"
                         "金字塔原理的原始出处，本节「结论先行」直接来自这里，麦肯锡等咨询公司的"
                         "结构化沟通训练大多以此为蓝本。"
                         "<strong>★</strong> Kahneman, Fredrickson, Schreiber & Redelmeier, "
                         "<em>When More Pain Is Preferred to Less: Adding a Better End</em>（1993）——"
                         "峰终定律（peak-end rule）的经典实验来源，本节「主动收尾」价值的理论依据，"
                         "但如正文所述，把它推广到面试评分场景需要保留一定的怀疑。"
                         "<strong>★</strong> Vygotsky, <em>Thought and Language</em>——"
                         "内部言语（inner speech）与外部言语转换的经典论述，是「边想边说」为何需要"
                         "专门训练而非自然发生的理论背景。</p>"
                         "<p>配套材料：Google 的 <em>Technical Interview Guidelines</em>（关于沟通维度的评分说明，"
                         "见 C62-00 引用）；CTCI 第 VII 章关于「Talk Through Your Solution」的段落。"
                         "相邻课程：<strong>C65-00</strong>（沟通三铁律的源头）、<strong>C65-04</strong>"
                         "（本模块第 1、7 节里「收敛」类演练题的方法论出处）、<strong>C61-04</strong>"
                         "（项目叙事，同样练“讲清楚”，但对象是过去做过的项目而非当场的开放题）、"
                         "<strong>C63-05</strong>（六个 ML 系统设计案例的完整演练脚本，"
                         "与本节的十题演练是同一种训练形式在不同题型上的应用）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 05 · 白板沟通与模拟演练（回答结构检查器 / 中英句库 / 10 题模拟引擎 / 24 小时清单）

目标：把「边想边说、结构化表达、卡住怎么办」这些沟通技巧，变成**可以运行、可以量化**的训练工具。
这是本课程的收官 notebook，会把前面四个模块（估算/诊断/权衡/模糊需求澄清）的方法论
统一接入到「一次完整的开放题回答」里。

本 notebook 你会亲手实现：
1. **环境自检**
2. **回答结构检查器** —— 给一段回答文本，自动判断：是否结论先行？是否显式说了假设？是否给了验证方式？
3. **句式库与中英对照表** —— 内置数据结构，按「思考动作/沟通功能」索引
4. **10 题模拟演练引擎**（✏️ 练习）—— 出题 → 计时 → 自评 → 弱项统计
5. **弱项报告生成器**（✏️ 练习）—— 多轮演练后自动指出最该优先练的维度
6. **面试前 24 小时检查清单** —— 结构化 + 中英对照

> 心智模型：**面试官打分的对象不是你脑子里的正确答案，是你嘴里说出来的思考过程。**"""),

    md("""## 0 · 环境自检"""),

    code("""import sys
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)
assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'argsort')
print('\\n✅ 环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · 回答结构检查器：三个维度的关键词探测

真实场景下判断「是否结论先行/是否说了假设/是否给了验证方式」需要语义理解，
这里用一个**教学版的关键词+位置探测器**做近似——它足够识别本模块例句里的结构特征，
让你在自己的模拟录音转写文本上也能跑一遍，作为练习时的量化反馈，而不是精确的 NLP 系统。"""),

    code("""CONCLUSION_MARKERS = ['我会', '我建议', '结论是', '我倾向于', '我的判断是', '我先说结论']
ASSUMPTION_MARKERS = ['我假设', '我先假设', '假设是', '如果不对', '按……展开', '我先按']
VERIFY_MARKERS = ['验证', '我会去查', '可以通过', '用……来确认', '对拍', '交叉校验', 'A/B']

def _find_first_position(text, markers):
    \"\"\"返回文本中最早出现的 marker 的字符位置；都不出现则返回 None。\"\"\"
    positions = [text.index(m) for m in markers if m in text]
    return min(positions) if positions else None

def analyze_structure(text, lead_window=40):
    \"\"\"返回一个 dict：
       has_conclusion / has_assumption / has_verification -> bool
       conclusion_first -> 结论标志是否出现在文本的前 lead_window 个字符内
    \"\"\"
    c_pos = _find_first_position(text, CONCLUSION_MARKERS)
    a_pos = _find_first_position(text, ASSUMPTION_MARKERS)
    v_pos = _find_first_position(text, VERIFY_MARKERS)
    return {
        'has_conclusion': c_pos is not None,
        'has_assumption': a_pos is not None,
        'has_verification': v_pos is not None,
        'conclusion_first': c_pos is not None and c_pos <= lead_window,
    }

GOOD = ('我建议先做时序投票这一项。理由是：我先假设这次不重训整个检测器，'
        '在这个前提下时序投票成本最低、见效最快。做完之后我会用离线的闪烁率指标验证效果。')
BAD = ('这个问题挺复杂的，可以从很多角度想，比如数据、模型、部署都有可能有问题，'
       '也不太确定具体是哪个，可能要看看情况。')

r_good = analyze_structure(GOOD)
r_bad = analyze_structure(BAD)
assert r_good == {'has_conclusion': True, 'has_assumption': True, 'has_verification': True, 'conclusion_first': True}
assert r_bad == {'has_conclusion': False, 'has_assumption': False, 'has_verification': False, 'conclusion_first': False}

print('好回答的结构诊断:', r_good)
print('差回答的结构诊断:', r_bad)
print('\\n✅ 探测器能区分"结论先行+说假设+给验证"与"绕圈子不落地"两种典型回答。')"""),

    md("""## 2 · 句式库：按「思考动作/沟通功能」索引（中英对照）

内置一个字典，key 是「沟通功能」，value 是一组中英对照句式。这是配套 notebook 的
「随时可查」版本——正文第 5 节的完整句库以这个数据结构为准。"""),

    code("""PHRASE_BANK = {
    'clarify': [
        ('我先复述一遍，确认我理解对了：……', "Let me restate to make sure I understand correctly: ..."),
        ('您说的这个指标具体指哪个？', "When you say that, which metric are you referring to specifically?"),
    ],
    'assumption': [
        ('我先假设……，如果不对请随时打断我。', "I'll assume ... for now — please stop me if that's not right."),
        ('我先按 A 这个假设往下展开，需要的话再切到 B。', "I'll go with assumption A for now; we can pivot to B if needed."),
    ],
    'tradeoff': [
        ('这里有一个权衡：……', "There's a tradeoff here between ... and ..."),
        ('我选 A 而不是 B，代价是……', "I'm going with A over B; the cost of that is ..."),
    ],
    'uncertainty': [
        ('这一点我不是很确定，我的第一反应是……', "I'm not fully certain here — my first instinct is ..."),
        ('这个数字我不确定，但可以给一个量级估算。', "I don't know the exact number, but I can give an order-of-magnitude estimate."),
    ],
}
FUNCTIONS = list(PHRASE_BANK)
assert FUNCTIONS == ['clarify', 'assumption', 'tradeoff', 'uncertainty']
assert all(len(v) >= 2 for v in PHRASE_BANK.values())

for fn in FUNCTIONS:
    print(f'[{fn}]')
    for cn, en in PHRASE_BANK[fn]:
        print(f'  CN: {cn}')
        print(f'  EN: {en}')
print('\\n✅ 句库就位：按功能查，而不是按话题背。')"""),

    md("""### 句库实战：把四类功能句拼成一段完整开场白

单独背句子容易，难的是临场把它们串起来。下面拼一段真实会用到的开场白，
再用第 1 节的结构检查器验证它确实拿到了结构满分——这就是句库和检查器该配合使用的方式。"""),

    code("""opening = (
    '我建议先做多帧时序投票这一项。'
    '我先假设这次场景是城市道路，如果不对请随时打断我。'
    '这里有一个权衡：时序投票成本低，但对召回本身提升有限。'
    '这一点我不是很确定，等做完我会用离线的闪烁率指标验证效果。'
)
r_opening = analyze_structure(opening)
assert r_opening['conclusion_first'] is True
assert r_opening['has_assumption'] is True
assert r_opening['has_verification'] is True
manual_score = int(r_opening['conclusion_first']) + int(r_opening['has_assumption']) + int(r_opening['has_verification'])
assert manual_score == 3

print(opening)
print()
print('结构诊断:', r_opening, '  得分:', manual_score, '/3  （这就是练习 1 要实现的 score_answer 逻辑）')
print('\\n✅ 句库不是用来单独背的，是用来拼成一段"结论先行+说假设+给验证"的完整开场白。')"""),

    md("""## 3 · 10 题模拟演练题库（数据结构）

把正文第 7 节的十道题内置为结构化数据：每题有评分要点 `rubric_points`（3 条）、
满分骨架 `skeleton`（拆成有序步骤）、常见失分点 `pitfall`，以及建议用时 `suggested_min`。"""),

    code("""DRILL_BANK = [
    {'id': 1, 'q': '提升 TSR 效果，你会怎么做？', 'suggested_min': 4,
     'rubric_points': ['是否先收敛边界', '是否给出可执行排序', '是否声明假设并请确认'],
     'skeleton': ['澄清六维度', '收敛出一个假设并声明', 'Impact×Confidence÷Cost 排序', '给分阶段计划'],
     'pitfall': '上来就讲技术方案，没有先定义"效果"是什么'},
    {'id': 2, 'q': '检测器上线一周后指标掉了，你怎么排查？', 'suggested_min': 4,
     'rubric_points': ['是否结构化诊断', '假设是否可证伪', '是否分层定位'],
     'skeleton': ['分清数据/模型/部署哪一层', '按二分法或信息增益排查顺序', '把假设写成可验证的形式'],
     'pitfall': '一次性列出十个可能原因但没有排查顺序'},
    {'id': 3, 'q': '两个月一个工程师，先做精度还是先做部署稳定性？', 'suggested_min': 3,
     'rubric_points': ['是否列维度', '是否显式打分', '是否说清放弃了什么'],
     'skeleton': ['列出比较维度', '打分', '说明帕累托关系与取舍'],
     'pitfall': '只给结论不给理由，或含糊说都重要'},
    {'id': 4, 'q': '只能加一种数据，你会加哪种？', 'suggested_min': 3,
     'rubric_points': ['候选集合是否完整', '是否用打分而非直觉', '排序理由是否可复算'],
     'skeleton': ['列候选方向', 'RICE 打分', '排序并说明理由'],
     'pitfall': '凭直觉说一个方向，没有对比其他候选'},
    {'id': 5, 'q': '估算采集训练数据需要多久。', 'suggested_min': 4,
     'rubric_points': ['是否分解到子任务', '是否用锚点数字', '是否双路径校验'],
     'skeleton': ['分解任务', '给锚点数字', '相乘估算', '换一条路径交叉校验'],
     'pitfall': '直接编一个数字，说不出是怎么算出来的'},
    {'id': 6, 'q': '向非技术产品经理解释方案风险。', 'suggested_min': 3,
     'rubric_points': ['是否结论先行', '是否避免行话', '类比是否贴切'],
     'skeleton': ['先说结论性风险', '用类比替代行话', '给出应对措施'],
     'pitfall': '满口专业术语，PM 听不懂也不敢打断'},
    {'id': 7, 'q': '方案在夜间场景可能失效，怎么和团队沟通？', 'suggested_min': 3,
     'rubric_points': ['是否主动暴露不确定性', '是否给出验证计划', '语气是否诚实'],
     'skeleton': ['说现象', '给出假设根因', '提出验证计划', '说明当前把握程度'],
     'pitfall': '把话说得比实际更有把握，掩盖未验证的部分'},
    {'id': 8, 'q': '预算临时砍半，怎么办？', 'suggested_min': 3,
     'rubric_points': ['是否快速重新排序', '是否说清砍掉了什么', '态度是否积极'],
     'skeleton': ['重算约束下的可行集', '更新排序', '说明砍掉的部分与影响'],
     'pitfall': '抱怨约束不合理，而不是给出调整后的方案'},
    {'id': 9, 'q': '和同事对技术方案有分歧，怎么解决？', 'suggested_min': 3,
     'rubric_points': ['是否给出可验证判据', '是否避免诉诸权威/情绪', '方案是否可执行'],
     'skeleton': ['列出分歧背后的假设', '设计一个能分辨对错的小实验', '按结果决定采用哪个'],
     'pitfall': '说"我经验更多"而不给可验证判据'},
    {'id': 10, 'q': '方案没达到预期，怎么复盘？', 'suggested_min': 3,
     'rubric_points': ['是否承认失败', '归因是否具体', '是否给出下一步行动'],
     'skeleton': ['对比预期与实际', '按数据/模型/评测/沟通归因', '给出下一步行动'],
     'pitfall': '把失败归咎于外部因素，不做自我审视'},
]
assert len(DRILL_BANK) == 10
assert all(len(d['rubric_points']) == 3 for d in DRILL_BANK)
assert all(len(d['skeleton']) >= 3 for d in DRILL_BANK)
assert [d['id'] for d in DRILL_BANK] == list(range(1, 11))
print(f'题库就位：共 {len(DRILL_BANK)} 题，建议总用时 {sum(d["suggested_min"] for d in DRILL_BANK)} 分钟。')"""),

    md("""## ✏️ 练习 1：回答结构评分函数

实现 `score_answer(text)`，基于第 1 节的 `analyze_structure`，返回 0-3 的整数分：
`conclusion_first` + `has_assumption` + `has_verification` 各算 1 分（`has_conclusion`
不单独计分——如果结论没出现在前段，只出现在后面，不给结论分，因为这不算"结论先行"）。"""),

    code("""def score_answer(text):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert score_answer(GOOD) == 3, score_answer(GOOD)
assert score_answer(BAD) == 0, score_answer(BAD)

# 结论出现了，但不在开头 —— 不算"结论先行"，这一分拿不到
LATE_CONCLUSION = ('这个问题背景比较复杂，有很多因素需要考虑，' + '占位' * 20 +
                   '综合下来我建议先做时序投票。我先假设不重训模型，做完会用离线指标验证。')
r = score_answer(LATE_CONCLUSION)
assert r == 2, r   # 有假设 + 有验证，但结论不在前 40 字 -> 少 1 分

# 只说了假设，没有验证也没有结论
ONLY_ASSUMPTION = '我先假设这次场景是城市道路。'
assert score_answer(ONLY_ASSUMPTION) == 1, score_answer(ONLY_ASSUMPTION)

for label, t in [('好回答', GOOD), ('差回答', BAD), ('结论靠后', LATE_CONCLUSION), ('只有假设', ONLY_ASSUMPTION)]:
    print(f'{label:<8} -> {score_answer(t)}/3')
print('\\n✅ 练习 1 通过：结论先行不是"有没有结论"，是"结论出没出现在开头"。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def score_answer(text):
    r = analyze_structure(text)
    return int(r['conclusion_first']) + int(r['has_assumption']) + int(r['has_verification'])"""),

    md("""## 4 · 模拟演练引擎（worked）：出题 → 计时 → 自评

`run_drill(drill_id, elapsed_sec, self_scores)` 模拟一次演练的记录动作：
给定题号、实际用时（秒）与自评分（三个维度各 0/1），返回一条结构化记录，
供后续弱项统计使用。这里先给出 worked 版本，练习 2 会在此基础上实现多轮统计。"""),

    code("""DRILL_BY_ID = {d['id']: d for d in DRILL_BANK}

def run_drill(drill_id, elapsed_sec, self_scores):
    \"\"\"self_scores: dict，如 {'clarity': 1, 'assumption': 1, 'verification': 0}\"\"\"
    d = DRILL_BY_ID[drill_id]
    over_time = elapsed_sec > d['suggested_min'] * 60
    return {
        'id': drill_id,
        'q': d['q'],
        'elapsed_sec': elapsed_sec,
        'suggested_sec': d['suggested_min'] * 60,
        'over_time': over_time,
        'self_scores': dict(self_scores),
        'total': sum(self_scores.values()),
    }

rec = run_drill(1, elapsed_sec=200, self_scores={'clarity': 1, 'assumption': 1, 'verification': 0})
assert rec['over_time'] is False   # 200s < 4*60=240s
assert rec['total'] == 2
rec2 = run_drill(1, elapsed_sec=300, self_scores={'clarity': 1, 'assumption': 1, 'verification': 1})
assert rec2['over_time'] is True   # 300s > 240s

print(rec)
print(rec2)
print('\\n✅ 单次演练记录就位，练习 2 要把多轮记录汇总成弱项报告。')"""),

    md("""## ✏️ 练习 2：弱项统计与报告生成器

实现 `weakness_report(records)`：输入是若干条 `run_drill` 返回的记录（列表），
返回一个 dict：
- `avg_by_dim`：三个维度（`clarity`/`assumption`/`verification`）各自的平均自评分（浮点数）
- `weakest_dim`：平均分最低的维度名（并列时取字典序最小的那个）
- `over_time_rate`：`over_time=True` 的记录占比"""),

    code("""def weakness_report(records):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
RECORDS = [
    run_drill(1, 200, {'clarity': 1, 'assumption': 1, 'verification': 0}),
    run_drill(2, 200, {'clarity': 1, 'assumption': 0, 'verification': 0}),
    run_drill(3, 150, {'clarity': 1, 'assumption': 1, 'verification': 1}),
    run_drill(4, 400, {'clarity': 0, 'assumption': 0, 'verification': 0}),
]
rep = weakness_report(RECORDS)

assert abs(rep['avg_by_dim']['clarity'] - 0.75) < 1e-9        # (1+1+1+0)/4
assert abs(rep['avg_by_dim']['assumption'] - 0.5) < 1e-9        # (1+0+1+0)/4
assert abs(rep['avg_by_dim']['verification'] - 0.25) < 1e-9     # (0+0+1+0)/4
assert rep['weakest_dim'] == 'verification'
assert abs(rep['over_time_rate'] - 0.25) < 1e-9                 # 只有题 4 超时(400s > 3*60=180s)

for dim, avg in rep['avg_by_dim'].items():
    print(f'{dim:<12} 平均分 {avg:.2f}')
print(f\"最弱维度: {rep['weakest_dim']}   超时率: {rep['over_time_rate']:.0%}\")
print('\\n✅ 练习 2 通过：verification（给验证方式）是这组演练里最该优先练的维度。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 2 参考答案
def weakness_report(records):
    dims = ['clarity', 'assumption', 'verification']
    avg_by_dim = {dim: sum(r['self_scores'][dim] for r in records) / len(records) for dim in dims}
    weakest_dim = min(dims, key=lambda d: (avg_by_dim[d], d))
    over_time_rate = sum(1 for r in records if r['over_time']) / len(records)
    return {'avg_by_dim': avg_by_dim, 'weakest_dim': weakest_dim, 'over_time_rate': over_time_rate}"""),

    md("""## ✏️ 练习 3：卡住检测与脱困提示器

实现 `stuck_advice(silence_sec)`，根据沉默时长返回建议采取的脱困法（对应正文第 3 节）：
- `silence_sec < 10` → `'ok'`（还不到需要动作的程度）
- `10 <= silence_sec < 20` → `'step_back'`（建议：退回上一层）
- `20 <= silence_sec < 30` → `'concrete_example'`（建议：举具体例子）
- `silence_sec >= 30` → `'ask_for_time'`（建议：明说需要一分钟——**这是最后的底线，
  绝不能选择继续沉默**）"""),

    code("""def stuck_advice(silence_sec):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert stuck_advice(5) == 'ok'
assert stuck_advice(10) == 'step_back'
assert stuck_advice(19) == 'step_back'
assert stuck_advice(20) == 'concrete_example'
assert stuck_advice(29) == 'concrete_example'
assert stuck_advice(30) == 'ask_for_time'
assert stuck_advice(120) == 'ask_for_time'   # 沉默 2 分钟也不会有第五种建议，永远收敛到"明说要时间"

for s in (5, 12, 22, 35, 60):
    print(f'沉默 {s:>3}s -> {stuck_advice(s)}')
print('\\n✅ 练习 3 通过：无论沉默多久，系统永远给出一个"该说什么"，而不是"继续等"。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 3 参考答案
def stuck_advice(silence_sec):
    if silence_sec < 10:
        return 'ok'
    if silence_sec < 20:
        return 'step_back'
    if silence_sec < 30:
        return 'concrete_example'
    return 'ask_for_time'"""),

    md("""---
## 🧪 真实工程胶囊：面试前 24 小时检查清单（中英对照）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 面试前 24 小时检查清单
# ══════════════════════════════════════════════════════════════════════
# □ 形式确认：白板 / 共享屏幕 / 纯语音，提前用同款工具跑一遍（尤其是没有
#             语法高亮和自动缩进的协作文档，务必先适应摩擦）
# □ 句库过一遍：clarify / assumption / tradeoff / uncertainty 四类中英各背 2 句，
#             练到"动作触发句子"而不是"回忆句子"
# □ 十题过一遍骨架（不是背答案）：每题只回忆 skeleton 的 3-4 步，
#             忘了哪步就回去看正文表格
# □ 收尾话术准备好一句可复用的模板：
#             "我先总结一下：方案是……，关键假设是……，最大风险是……，
#              如果有更多时间我会验证……"
# □ 反问准备 1-2 个真实问题（不要问网上查得到的）
# □ 心态：目标不是"讲得完美"，是"讲得让人看见你在想什么"

# ══════════════════════════════════════════════════════════════════════
# B. 四类关键英文表达速查（各挑最常用的一句背下来）
# ══════════════════════════════════════════════════════════════════════
# 澄清:   "Let me restate to make sure I understand correctly: ..."
# 假设:   "I'll assume ... for now — please stop me if that's not right."
# 权衡:   "There's a tradeoff here between ... and ...; I'm going with ... because ..."
# 不确定: "I'm not fully certain here — my first instinct is ..., but I'd want to double-check."

# ══════════════════════════════════════════════════════════════════════
# C. 卡住时的行动表（沉默超过 30 秒是硬扣分线）
# ══════════════════════════════════════════════════════════════════════
# < 10s   继续想，无需动作
# 10-20s  退回上一层："我退一步——最初要解决的是……"
# 20-30s  举具体例子："我拿一个具体例子走一遍：……"
# >= 30s  明说要时间："给我 20-30 秒，我在权衡……"（绝不能选择继续沉默）

# ══════════════════════════════════════════════════════════════════════
# D. 与本课程其他部分的分工（收官提醒）
# ══════════════════════════════════════════════════════════════════════
# · 澄清问题清单与收敛话术         -> C65-04（本模块第7节10题里反复复用）
# · 估算/诊断/权衡的具体方法论     -> C65-01 / C65-02 / C65-03
# · 项目叙事（讲过去做过的事）     -> C61-04（对象不同：过去 vs 当场开放题）
# · ML 系统设计的完整案例演练脚本  -> C63-05（同一种训练形式，题型更大）
'''
print(RECIPE)
for token in ['24 小时', 'restate', "I'll assume", '30 秒', 'C65-04', 'C63-05']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：赛前清单 / 中英速查 / 卡壳行动表 / 课程收官分工')"""),

    md("""### 小结

- **面试官打分的对象是你说出来的思考过程，不是你脑子里的正确答案。** 边想边说需要一套
  「思考动作 → 触发句式」的固化映射，而不是临场现想怎么表达。
- **结构化表达的核心工具是结论先行 / 金字塔原理 / 三点法**——先给答案，
  再给不超过三条的支撑论据，让面试官可以随时决定是否要下钻细节。
- **卡住时永远从三种脱困法里选一个说出口**（退回上一层 / 举具体例子 / 明说要时间），
  沉默本身才是失分项，卡壳不是。
- **三种沟通形式（白板/共享屏幕/纯语音）对结构化表达的要求依次递增**，
  纯语音下必须靠语言本身显式建立层次，不能依赖画面兜底。
- **英文的「让步句式」（I'll assume ... but / I'm not certain, but my instinct is ...）
  需要被专门练习**，直译成生硬的 "I don't know" 会传递错误的信号——一定要在后面接一句你的判断或验证计划。
- **10 道开放题看起来主题各异，骨架高度重复**：定义边界 → 结构化展开 → 显式权衡/假设 →
  主动暴露不确定性 → 给出下一步。这正是 C65-00 四步框架在不同外壳下的反复出现。

到此，C65 全课收官：从估算（01）、诊断（02）、权衡（03）、模糊需求澄清（04），
到本模块的白板沟通与模拟演练（05）——五个模块共同训练的是同一件事：
**让面试官清楚看见你的思考过程，而不只是看见你的结论。**"""),
]
