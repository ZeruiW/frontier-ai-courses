# -*- coding: utf-8 -*-
"""C65 模块 00 · 课程总览与环境（结构化问题求解与面试沟通）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "不需要任何算法、系统设计或 ML 背景；唯一的前提是愿意把脑子里的推理过程说出来——"
                 "这门课练的是<strong>表达与结构</strong>，不是知识本身"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（四步框架自检器 / 沟通三铁律打分器 / 好坏回答结构对比打分器）'),
    ("核心参考", "Conn & McLean《Bulletproof Problem Solving》 · Minto《The Pyramid Principle》 · "
                 "Google re:Work《Structured Interviewing》 · 本课程 C61 模块 04 / C62 / C63 / C64"),
    ("预计时长", "读 40 分钟 + 跑 30 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-is-tested", "问题求解到底在考什么：思维过程的可见性", "".join([
        P("把一面拆开看：<em>Technical Knowledge</em> 考你知道什么，<em>Practical Coding</em> 考你能写出什么，而"
          "<strong>Problem-Solving 考的是你脑子里那条从问题到结论的推理线，是不是能被别人看见</strong>。"
          "这条线平时躺在你脑子里，面试官压根看不到——除非你把它说出来。"),
        P("这带来一个反直觉的结论：<strong>答案对不对，在这一环节里往往不是最重要的信号</strong>。"
          "真正的开放题（例如「怎么提升某个场景下的召回」「系统突然变慢怎么排查」）常常没有唯一正确答案，"
          "面试官自己也不一定知道「标准答案」是什么——他手里唯一能打分的，是你摊开的那条推理链。"),
        TABLE(["面试段落", "考察对象", "可打分的交付物", "沉默的代价"], [
            ["Technical Knowledge（C64）", "你知道什么", "一句话定义 + 边界条件", "答不出 = 直接暴露知识缺口，代价明确"],
            ["Practical Coding（C62）", "你能写出什么", "一段能跑的代码 + 复杂度陈述", "写不出 = 至少还有暴力解和口述兜底"],
            ["<strong>Problem-Solving（本课）</strong>", "你怎么想问题", "<strong>被说出来的推理链本身</strong>",
             "<strong>沉默 = 没有任何交付物，连兜底分都没有</strong>"],
        ]),
        CALLOUT("warn", "很多人把 problem-solving 当成一个「猜面试官心里的答案」的游戏，拼命去蒙一个他可能满意的结论。"
                        "这个策略在系统设计和知识问答里可能侥幸得分，但在这里几乎必输——因为<strong>你唯一能控制、"
                        "也唯一被打分的东西，是过程的可见度，不是你蒙没蒙对</strong>。"),
        DUAL(
            "换个说法：这门课不是教你「怎么想得更聪明」，是教你「怎么把脑子里已经在做的事说出来」。"
            "大多数候选人不是不会想，是<em>不习惯把想的过程讲出来</em>——平时自己写代码、自己做决策，从来不需要解说。",
            "更严谨地说，这是一个可观测性问题：面试官对你能力的估计，只能基于他能观测到的信号；"
            "而在一个只有 20-30 分钟、没有代码产出的开放问题里，唯一可观测的信号就是你显式表达出来的推理步骤。"
            "<em>提升可观测的推理质量，在期望得分上几乎总是优于提升蒙对答案的概率"
            "——因为后者的方差极大，而前者的方差你自己可控。</em>",
        ),
    ])),

    # ============================================================== 2
    ("framework", "四步通用框架：澄清 → 分解 → 假设与验证 → 收敛与权衡", "".join([
        P("整门课只有一个东西必须先刻进肌肉记忆，就是这四步。它不是一份「讲什么内容」的清单，"
          "是一份「先做什么、再做什么」的<strong>执行顺序</strong>——模块 02（诊断）、03（权衡）、04（模糊需求）"
          "全都是它在具体场景下的展开，记混了顺序，后面几个模块会觉得「不知道现在该干嘛」。"),
        ASCII("""┌────────────┐   发现新信息    ┌────────────┐
│ ① 澄清     │───────────────▶│ ② 分解     │
│  clarify   │◀───────────────│  decompose │
└─────┬──────┘  分解暴露新歧义 └─────┬──────┘
      │                              │
      ▼                              ▼
┌────────────┐   假设被证伪    ┌────────────┐
│④ 收敛与权衡│◀───────────────│③ 假设与验证│
│  converge  │───────────────▶│ hypothesize│
└────────────┘  权衡时发现     └────────────┘
                需要重新验证

任意一步结束，都应该已经有一个目前为止最好的判断可以交付——
这不是走一次就完事的直线，是随时可以被打断、也随时可以往回跳的循环。"""),
        TABLE(["步骤", "产出（要说出的话）", "跳过它的后果", "面试官心里记的一笔"], [
            ["① 澄清 clarify", "复述问题 + 明确目标 / 约束 / 成功标准", "解错题，后面全白做", "「他没有先确认范围就动手」"],
            ["② 分解 decompose", "把问题拆成可独立处理的子块", "被问题的复杂度淹没，来回打转", "「他抓不住结构，想到哪说到哪」"],
            ["③ 假设与验证 hypothesize", "提出可证伪的假设 + 怎么验证它", "假设说得斩钉截铁却经不起一问",
             "「他把猜测当结论，还不知道自己在猜」"],
            ["④ 收敛与权衡 converge", "给结论 + 显式说清放弃了什么", "要么不收敛，要么收敛却藏起代价",
             "「他要么没决断，要么假装没有代价」"],
        ]),
        P("举一个简短的例子体会这个顺序：面试官说「想办法提升 TSR 系统在雨天的检出率」。"
          "<strong>①澄清</strong>：先问清当前检出率具体指哪个指标、雨天和晴天差多少、是要即插即用还是可以重训；"
          "<strong>②分解</strong>：把雨天检出率低拆成数据（雨天样本够不够）、模型（雨滴模糊是否被增强覆盖）、"
          "后处理（阈值是否因雨天置信度整体下降而漏检）三块；<strong>③假设与验证</strong>：假设主因是数据不足，"
          "验证方法是看雨天场景的样本占比和逐场景 AP，若雨天 AP 显著低且样本占比 &lt; 5%，假设成立；"
          "<strong>④收敛与权衡</strong>：若验证成立，优先做针对性数据增强/采集而不是急着换模型架构——但要说清"
          "「这个判断建立在雨天数据确实稀缺这个假设上，如果验证后发现是模型对雨滴纹理的表征本身弱，结论会反过来」。"
          "这四步怎么具体展开、怎么应对追问，是模块 02-04 的内容；这里只是让你看到顺序本身长什么样。"),
        DUAL(
            "这四步不是走一次就完事的直线，是可以往回跳的。分解到一半发现「哦原来他说的检出率是逐帧的不是逐目标的」，"
            "那就要跳回澄清——这很正常，不是失败。",
            "更严谨地说，这是一个类似 anytime algorithm（随时可终止算法）式的结构：即使面试官在任意一步打断你"
            "（「时间到，说说你现在的判断」），你也应该已经有一个当前最好的部分结论可以交付，而不是"
            "「还没到收敛那一步所以什么都拿不出来」。<em>每一步结束时都默认自己有义务给出一个目前为止的判断，"
            "这是让框架真正抗打断的关键。</em>",
        ),
    ])),

    # ============================================================== 3
    ("comm-laws", "沟通三铁律：结论先行、显式说假设、主动暴露不确定性", "".join([
        P("如果说四步框架管的是「先想什么、再想什么」，这三条铁律管的是「怎么把想的东西说出来」——"
          "它们几乎适用于四步里的每一步，是贯穿全场的默认行为，不是某个阶段专属的技巧。"),
        TABLE(["铁律", "具体要求", "为什么", "反例"], [
            ["<strong>① 结论先行</strong>", "先给一句能独立成立的判断 / 框架，再展开论证",
             "面试官需要先知道你要去哪，才能跟上你怎么去；不然 30 秒后他已经不知道你在回答什么问题了",
             "「呃，这个问题有很多方面……（5 分钟后）……所以我觉得可能是数据问题吧」"],
            ["<strong>② 显式说假设</strong>", "把没验证的前提大声说出来，而不是悄悄当真",
             "面试官会用假设是否成立来追问；不说出来，一旦假设错了，你整段推理会被认为是没意识到自己在猜",
             "直接说「肯定是数据不平衡」，不说这只是一个待验证的猜测"],
            ["<strong>③ 主动暴露不确定性</strong>", "承认自己不确定的地方，并说清楚打算怎么去补",
             "不确定不是减分项，<strong>隐藏不确定性、被问出来才承认才是减分项</strong>",
             "被追问到答不上来才支支吾吾，而不是提前说「这块我没把握，如果是我，我会先查……」"],
        ]),
        CALLOUT("danger", "<strong>最容易被误解的一条是③。</strong>很多人以为暴露不确定性等于显得不专业，"
                          "于是硬撑着把没把握的判断说得斩钉截铁。真实情况恰好相反：<em>面试官几乎总能通过追问"
                          "戳穿虚张声势的自信</em>，而一旦被戳穿，他记下的不是这个人有一处不确定，是"
                          "这个人会在不确定的时候伪装确定——这是一条会被推广到他汇报工作时是不是也这样的、"
                          "危害大得多的推断。<strong>提前说「这里我不确定，大概六成把握，我会用 X 验证」，"
                          "永远比被戳穿后才承认要安全。</strong>"),
        DUAL(
            "三条铁律合在一起，其实就是把我脑子里那团乱乱的想法，整理成一句话结论加几条打了标签的支撑"
            "——标签就是这是假设、这是我不确定的、这是权衡后放弃的。",
            "形式化地看，三条铁律共同把一段自由文本的回答，转成一个带类型标注的结构："
            "<code>{conclusion, assumptions[], uncertainties[]}</code>。"
            "<em>这正是本模块 notebook 里结构分析器要做的事——把一段回答表示成一串带标签的言语行为序列，"
            "再检测这三类标签是否齐全、结论标签是否在最前面。</em>",
        ),
    ])),

    # ============================================================== 4
    ("think-vs-talk", "「想清楚再说」vs「边想边说」：取舍与折中", "".join([
        P("两种坏做法都很常见：<strong>完全想清楚再说</strong>——安静想 40 秒再开口，面试官在这 40 秒里只能看见沉默，"
          "大概率会误判成卡住了；<strong>边想边说</strong>——立刻开口，一边说一边试探性地改口，"
          "3 分钟后自己都绕晕了，面试官也没听出一个站得住的结构。"),
        ASCII("""0s          10s                                          Ns（展开长度按问题难度而定）
├───────────┼──────────────────────────────────────────────────┤
│ 结论先行  │            边展开边验证、边说假设、边收敛          │
│（10秒结构）│  分解 → 假设与验证 → 必要时回到收敛调整结论        │
└───────────┴──────────────────────────────────────────────────┘
      ▲
      │
 这10秒不是最终答案，是给面试官一个可以打断/引导你的锚点。"""),
        MATH("L \\;\\le\\; c\\cdot t,\\qquad c\\approx 4\\text{--}5\\ \\text{字/秒（中文口语语速）},"
             "\\ \\ t = 10\\,\\text{s}\\ \\ \\Rightarrow\\ \\ L \\lesssim 40\\text{--}50\\ \\text{字}"),
        P("也就是说，这句十秒结构的字数上限大约是 40-50 个汉字——大概是结论加一条假设加接下来打算怎么展开这三句话"
          "拼起来的长度，notebook 练习 1 会把这个预算做成一个可判定的函数。"),
        DUAL(
            "折中方案是：<strong>先用 10 秒说出一个暂定结论加展开顺序，再开始边想边说地展开细节</strong>。"
            "这 10 秒不需要是最终答案，它只是给面试官一个锚点——他知道你现在在哪、接下来要去哪，"
            "他也能在这个锚点上打断你、引导你。",
            "更严谨地表述这是一个信息论视角的取舍：完全想清楚再说，把思考时长的全部方差都压缩到沉默里，"
            "面试官在这段时间里获得的信息增益为 0；边想边说不加结构，信息以很高的<em>噪声</em>速率传出，"
            "方差大但均值不高。<strong>先给 10 秒结构，相当于先传出一个低噪声、高信息量的先验，再用后续展开去"
            "补充细节和修正</strong>——这与贝叶斯更新的直觉一致：<em>有一个明确的先验，后面的证据才有地方挂。</em>",
        ),
    ])),

    # ============================================================== 5
    ("good-vs-bad", "「好回答」vs「坏回答」：一段结构对比", "".join([
        P("把上面三条铁律和四步框架放在一起看一个例子。题面同样是「提升某检测系统在困难场景下的召回率」"
          "——两种回答，内容知识量可能差不多，但结构天差地别。"),
        TABLE(["维度", "坏回答", "好回答"], [
            ["开场", "「这个问题挺复杂的，让我想想……」（沉默 15 秒）",
             "「我的初步判断是：先确认这是数据问题还是模型问题，我倾向于先查数据。」（10 秒内给出锚点）"],
            ["假设", "直接断言肯定是负样本不够，不说这是猜测",
             "「我先假设是负样本覆盖不够，这个假设可以通过看这类场景的样本占比来验证」"],
            ["结构", "东想到哪说到哪，没有分块", "显式分块：「我从数据、模型、后处理三块分别看」"],
            ["不确定性", "被问到才说「呃我不太确定」",
             "主动说「这一块我把握不到八成，如果验证结果不支持，我会转向模型侧」"],
            ["收尾", "说到一半戛然而止，面试官要追问才有结论",
             "主动收敛：「综合看我会优先做 A，代价是 B，如果预算允许我会同时做 C」"],
        ]),
        CALLOUT("intuition", "把这张表逐行看下来会发现：<strong>两种回答包含的知识可能完全一样</strong>"
                             "——都提到了数据/模型/后处理三个维度，都提到了负样本假设。"
                             "<em>差别 100% 出在结构和显式度上。</em>这也是为什么本课程叫结构化问题求解，"
                             "而不是更懂 ML 的问题求解——知识密度不是这门课要补的洞，结构才是。"),
        DUAL(
            "notebook 里会把好回答、坏回答都表示成一串发言标签（比如 conclusion / assumption / decompose / "
            "uncertainty / filler），然后写一个打分函数——分数差会大到你自己都意外。",
            "这是一个结构化评测的简化实现：把非结构化的自然语言回答，先<em>标注</em>成一串离散的言语行为标签序列，"
            "再对标签序列做规则打分。这和后面模块 05 的回答结构检查器是同一套方法在模拟演练场景下的复用。",
        ),
    ])),

    # ============================================================== 6
    ("scope", "本课地图与分工：与 C61-04 / C62 / C63 / C64 怎么分", "".join([
        P("结构化问题求解这件事，在一面的三个板块里其实反复出现——只是每次换了个外壳。"
          "搞清楚外壳和内核的关系，能省下大量重复练习的时间。"),
        TABLE(["场景 / 课程", "外壳（题目形态）", "内核（用的还是哪套框架）", "关系"], [
            ["<strong>C65（本课）</strong>", "估算 / 诊断 / 权衡 / 模糊需求等开放问题",
             "<strong>四步框架 + 三铁律，本课的原生形态</strong>", "主线"],
            ["C62 六步编码协议", "写代码解一道算法题",
             "四步框架在产出是代码场景下的特化（暴力解 = 先给可行假设，优化 = 分解 + 验证）",
             "见 C62-00，本课不重复六步协议"],
            ["C63 ML 系统设计七步", "设计一个 ML / 感知系统",
             "四步框架在产出是架构图加指标场景下的特化，分解更细（拆成数据/建模/服务）",
             "见 C63-00；容量估算见 <strong>C63-04</strong>，本课模块 01 只讲通用估算方法"],
            ["C61 模块 04 项目叙事", "讲一个你做过的项目",
             "<strong>不是这套框架</strong>——STAR 讲的是已经发生的事，不是当场解一道新题，"
             "重点在结果与代价的诚实陈述", "不要混用：叙事用 STAR，当场解题用四步"],
            ["C64 知识问答三段式", "解释一个概念",
             "更简单：一句话定义 → 为什么需要 → 什么时候失效，不需要分解这么重的结构", "见 C64-00"],
        ]),
        P("本课后续四个模块，就是把四步框架分别套进四类最常见的开放题：模块 01 <strong>估算</strong>"
          "（Fermi 方法，本质是分解这一步的专项深化），模块 02 <strong>诊断归因</strong>"
          "（本质是假设与验证这一步的专项深化，把假设可证伪这条铁律用到极致），模块 03 <strong>权衡决策</strong>"
          "（本质是收敛这一步的专项深化），模块 04 <strong>模糊问题澄清</strong>（本质是澄清这一步的专项深化），"
          "模块 05 把四者揉进模拟演练里练习表达。可以说，<strong>模块 01-04 分别放大了四步框架里的一步，"
          "模块 05 再把它们缝回一整段回答。</strong>"),
        CALLOUT("warn", "看到估算、诊断这些标题不要误以为它们是互相独立的新技能——它们共用的是同一个"
                        "四步框架和同一套三铁律，<strong>换的只是分解或假设验证具体怎么做</strong>。"
                        "如果你发现自己在模块 02 又把先给暴力解的思路搬出来（见 C62-00），"
                        "那说明你已经在正确地做迁移了。"),
    ])),

    # ============================================================== 7
    ("frontier", "研究前沿与开放问题", "".join([
        P("结构化问题求解这套方法论，大部分来自咨询行业（McKinsey 等）几十年的案例面试实践，"
          "被科技公司借用来评估非 coding 的思考能力。但它作为一种评估手段，本身也有一些尚未解决的问题。"),
        UL([
            "<strong>这套方法本身的预测效度有多高？</strong>没有太多公开研究能证明讲得结构化的人，工作中判断力"
            "真的更好——它更可能是和优秀候选人的表达习惯相关，而不是因果关系。"
            "<em>但只要面试官在用它打分，提升这个信号仍然是理性的准备策略。</em>",
            "<strong>结构化表达的评估标准是否有文化偏差？</strong>结论先行在部分语境里被视为西式沟通习惯，"
            "而更含蓄、先给背景再给结论的表达方式，在同一套评分表下天然吃亏。"
            "<em>这在英文面试（本课程锚定的岗位 JD 就是英文）里更明显——模块 05 会给出中英对照的表达句式，"
            "部分就是为了弥合这种差异，而不是假装它不存在。</em>",
            "<strong>LLM 正在改变这类问题正确答案本身的可获得性</strong>——如果面试官允许你用 AI 辅助思考，"
            "怎么把 AI 给出的框架转成你自己的、可追问的推理链，会成为新的考点，而不是框架本身。",
            "结构化打分器（比如本课 notebook 里的言语标签分析）本质是对真实评分过程的一个粗糙近似——"
            "真实面试官会综合语气、眼神、追问反应等无法代码化的信号，<em>把它当作练习校准的工具，"
            "而不是当作面试评分的真实模型。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Charles Conn &amp; Robert McLean, "
                         "<em>Bulletproof Problem Solving</em>（2019）——本课四步框架的方法论原型"
                         "（原书是麦肯锡内部沿用的七步问题求解流程，本课按面试场景压成四步）。"
                         "<strong>★</strong> Barbara Minto, <em>The Pyramid Principle</em>——"
                         "结论先行与金字塔式表达的经典出处，模块 05 会直接引用它的分组分层写法。"
                         "<strong>★</strong> Google re:Work, <em>Structured Interviewing</em> 指南——"
                         "关于以可观测的推理过程而非印象打分的招聘实践依据。</p>"
                         "<p>相邻课程：<strong>C61 模块 04</strong>（项目叙事，STAR 模板，讲过去而非当场解题）、"
                         "<strong>C62</strong>（编码六步协议，四步框架在写代码场景的特化）、"
                         "<strong>C63</strong>（ML 系统设计七步，容量估算见 C63-04）、"
                         "<strong>C64</strong>（技术知识三段式问答）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（四步框架自检器 / 沟通三铁律打分器 / 好坏回答结构对比）

目标：把"结构化表达"从一堆经验之谈，变成**几个可以运行、可以断言的小工具**。

本 notebook 你会亲手实现：
1. **环境自检** —— 确认 Python / numpy 可用（本课全程不需要 GPU、不需要联网）
2. **四步框架自检器** —— 给一段"你实际做了什么"的动作序列，自动指出漏了哪步、哪两步顺序反了
3. **四步框架完整度打分器** —— 把"缺步"和"顺序违规"合成一个 0-1 分
4. **沟通三铁律打分器** —— 给一段回答的三个布尔标记打分，找出最该补的一条
5. **"好回答 vs 坏回答"结构分析与打分器** —— 把自然语言回答表示成一串"言语行为标签"，量化两者的差距
6. **10 秒结构预算器** —— 把"先给结构再展开"这句话变成一个可判定的字数上限

> 心智模型：**这个环节考的不是"你知道多少"，是"你的推理过程能不能被别人看见"。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math, random
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'argsort')

print('\\n环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · 四步框架自检器

框架本身是一个有序清单。自检器要回答两件事：
**（a）你漏了哪一步？（b）哪两步的顺序反了？**

顺序违规的定义：设框架里 `a` 应在 `b` 之前，但你**首次**做 `b` 的时刻早于首次做 `a` —— 记一次违规 `(b, a)`。"""),

    code("""FRAMEWORK_STEPS = [
    ('clarify',     '① 澄清',       '确认目标、边界、约束、成功标准'),
    ('decompose',   '② 分解',       '把问题拆成互相独立、可逐个处理的子问题'),
    ('hypothesize', '③ 假设与验证', '提出一个可证伪的假设，说清怎么验证'),
    ('converge',    '④ 收敛与权衡', '给出结论，显式说清放弃了什么、为什么'),
]
FRANK = {k: i for i, (k, _, _) in enumerate(FRAMEWORK_STEPS)}

def check_framework(trace):
    \"\"\"trace: 你实际做的动作序列（step key 的列表，可重复）。
       返回 (missing, inversions)：缺失的步骤、以及顺序违规对 (先做的, 本该更早的)。\"\"\"
    missing = [k for k, _, _ in FRAMEWORK_STEPS if k not in trace]
    first = {}
    for pos, t in enumerate(trace):
        first.setdefault(t, pos)
    inversions = set()
    present = [k for k in FRANK if k in first]
    for a in present:
        for b in present:
            if FRANK[a] < FRANK[b] and first[a] > first[b]:
                inversions.add((b, a))
    return missing, sorted(inversions, key=lambda p: (FRANK[p[0]], FRANK[p[1]]))

for k, name, what in FRAMEWORK_STEPS:
    print(f'{name:<10} {what}')"""),

    code("""# —— 三种典型表现 ——
good  = ['clarify', 'decompose', 'hypothesize', 'converge']    # 规范顺序
rush  = ['converge']                                           # 一上来就给结论，没有推理过程
mixed = ['clarify', 'converge', 'decompose', 'hypothesize']    # 先给了结论，才回头分解验证

m1, i1 = check_framework(good)
assert m1 == [] and i1 == []

m2, i2 = check_framework(rush)
assert set(m2) == {'clarify', 'decompose', 'hypothesize'}, m2
assert i2 == [], '只做了 converge 一步，没有别的步骤可比较顺序'

m3, i3 = check_framework(mixed)
assert m3 == []
assert i3 == [('converge', 'decompose'), ('converge', 'hypothesize')], i3
assert len(i3) == 2

print('good  -> 缺失', m1, '违规', i1)
print('rush  -> 缺失', m2, '  <- 丢掉澄清/分解/假设验证三步的分，只剩一个孤零零的结论')
print('mixed -> 违规', i3, '  <- 结论说在了分解与验证之前')
print('\\n自检器就位：把模拟面试的录像回放一遍，把动作打成 trace 喂进来。')"""),

    md("""## 2 · 四步框架完整度打分器

把"缺步"和"顺序违规"合成一个 0-1 分：`completeness = (4 - 缺步数) / 4`，
`penalty = 0.15 × 违规对数`，`score = max(0, completeness - penalty)`。"""),

    code("""def framework_score(trace):
    \"\"\"结合步骤完整度与顺序违规惩罚给出 0-1 分。\"\"\"
    missing, inversions = check_framework(trace)
    completeness = (4 - len(missing)) / 4
    penalty = 0.15 * len(inversions)
    return max(0.0, completeness - penalty)

s_good, s_rush, s_mixed = framework_score(good), framework_score(rush), framework_score(mixed)
assert abs(s_good - 1.0) < 1e-9, s_good
assert abs(s_rush - 0.25) < 1e-9, s_rush
assert abs(s_mixed - 0.7) < 1e-9, s_mixed

for name, s in [('good', s_good), ('rush', s_rush), ('mixed', s_mixed)]:
    print(f'{name:<6} -> {s:.2f}')
print('\\n完整但顺序反了（mixed）仍然好于严重缺步（rush）——')
print('说明"至少把四步都提到"，比"顺序完美但漏了大半"更重要。')"""),

    md("""## 3 · 沟通三铁律打分器

三律：结论先行 / 显式说假设 / 主动暴露不确定性，各占三分之一权重。"""),

    code("""LAWS = [
    ('conclusion_first',     '结论先行'),
    ('explicit_assumptions', '显式说假设'),
    ('surfaced_uncertainty', '主动暴露不确定性'),
]

def score_communication(flags):
    \"\"\"flags: dict{law_key: bool}。返回 (score 0-1, 未达标的律 list)。\"\"\"
    keys = [k for k, _ in LAWS]
    hit = sum(1 for k in keys if flags.get(k, False))
    missed = [k for k in keys if not flags.get(k, False)]
    return hit / len(keys), missed

GOOD_FLAGS = dict(conclusion_first=True, explicit_assumptions=True, surfaced_uncertainty=True)
BAD_FLAGS = dict(conclusion_first=False, explicit_assumptions=False, surfaced_uncertainty=True)

sg, mg = score_communication(GOOD_FLAGS)
sb, mb = score_communication(BAD_FLAGS)
assert sg == 1.0 and mg == []
assert abs(sb - 1 / 3) < 1e-9, sb
assert mb == ['conclusion_first', 'explicit_assumptions'], mb

print(f'好回答: 分数={sg:.2f}  未达标={mg}')
print(f'坏回答: 分数={sb:.2f}  未达标={mb}')
print('\\n坏回答唯一做对的是"暴露了不确定性"，但另外两条全丢，分数只剩三分之一。')"""),

    md("""## 4 · "好回答 vs 坏回答"结构分析与打分

把一段回答表示成一串"言语行为标签"（发言时依次做的事）：
`conclusion`（给结论）/ `clarify_q`（提澄清问题）/ `decompose`（分解）/ `assumption`（说假设）/
`evidence`（给证据）/ `tradeoff`（说权衡）/ `uncertainty`（说不确定）/ `filler`（口水话）/ `silence`（沉默）。"""),

    code("""def analyze_answer(tags):
    \"\"\"tags: 言语行为标签的有序列表。返回结构分析字典。\"\"\"
    n = len(tags)
    leads = n > 0 and tags[0] == 'conclusion'
    has_assumption = 'assumption' in tags
    has_uncertainty = 'uncertainty' in tags
    has_tradeoff = 'tradeoff' in tags
    filler = tags.count('filler') + tags.count('silence')
    filler_ratio = filler / n if n else 0.0
    # 四步框架里，哪几步在这段回答里被真正提到过
    mapping = {'clarify_q': 'clarify', 'decompose': 'decompose',
               'assumption': 'hypothesize', 'tradeoff': 'converge'}
    covered = {mapping[t] for t in tags if t in mapping}
    return dict(leads_with_conclusion=leads, has_assumption=has_assumption,
                has_uncertainty=has_uncertainty, has_tradeoff=has_tradeoff,
                filler_ratio=filler_ratio, coverage=len(covered) / 4)

def score_answer(tags):
    \"\"\"把 analyze_answer 的结果合成一个 0-1 总分（下限截到 0）。
       权重：四步覆盖度 0.4，结论先行 0.2，说了假设 0.15，说了不确定性 0.15，
       口水话/沉默按比例倒扣（最多倒扣 0.3）。\"\"\"
    a = analyze_answer(tags)
    raw = (0.4 * a['coverage'] + 0.2 * a['leads_with_conclusion']
           + 0.15 * a['has_assumption'] + 0.15 * a['has_uncertainty'])
    raw -= 0.3 * a['filler_ratio']
    return max(0.0, raw)

GOOD_ANSWER = ['conclusion', 'assumption', 'clarify_q', 'decompose', 'evidence', 'tradeoff', 'uncertainty']
BAD_ANSWER = ['filler', 'filler', 'decompose', 'filler', 'conclusion', 'silence']

a_good = analyze_answer(GOOD_ANSWER)
assert a_good['coverage'] == 1.0 and a_good['leads_with_conclusion'] is True

sg2, sb2 = score_answer(GOOD_ANSWER), score_answer(BAD_ANSWER)
assert abs(sg2 - 0.9) < 1e-6, sg2
assert sb2 == 0.0, sb2

print(f'好回答标签: {GOOD_ANSWER}')
print(f'  分析: {a_good}')
print(f'  总分: {sg2:.2f}')
print(f'坏回答标签: {BAD_ANSWER}')
print(f'  总分: {sb2:.2f}')
print('\\n两段回答提到的"知识维度"可能一样多，但结构打分能拉开近满分的差距。')"""),

    md("""## 5 · 10 秒结构预算器

"先给 10 秒结构再展开"的字数上限：中文口语语速约 4-5 字/秒，10 秒约 40-50 字。
下面按 4.5 字/秒 的保守估计做判定。"""),

    code("""def opening_ok(text, cps=4.5, seconds=10):
    \"\"\"判断 text 能否在 seconds 秒内、按 cps 字/秒的语速说完。\"\"\"
    return len(text) <= cps * seconds

short_text = '结论：先查数据。假设：负样本不够。接下来我按数据、模型、后处理三块看。'
long_text = '结论：' + 'x' * 30 + '。假设：' + 'y' * 30 + '。接下来我按：' + 'z' * 30 + '。'

assert opening_ok(short_text) is True, len(short_text)
assert opening_ok(long_text) is False, len(long_text)
assert opening_ok('x' * 45) is True and opening_ok('x' * 46) is False   # 45 = 4.5*10 的边界

print(f'短开场（{len(short_text)} 字，预算 45 字）-> {opening_ok(short_text)}')
print(f'长开场（{len(long_text)} 字，预算 45 字）  -> {opening_ok(long_text)}')
print('\\n40-50 字大约就是"一句结论 + 一条假设 + 一句展开顺序"的长度。')"""),

    md("""## ✏️ 练习 1：10 秒开场拼装器

实现 `opening_stub(conclusion, assumption, plan, cps=4.5, seconds=10)`，
拼出格式为 `'结论：{conclusion}。假设：{assumption}。接下来我按：{plan}。'` 的开场白，
并判断它能否在 `seconds` 秒内说完（复用 `opening_ok` 的判据）。返回 `(text, fits)`。"""),

    code("""def opening_stub(conclusion, assumption, plan, cps=4.5, seconds=10):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
text1, fits1 = opening_stub('先做数据端', '数据不足', '三步展开')
assert text1 == '结论：先做数据端。假设：数据不足。接下来我按：三步展开。', text1
assert fits1 is True, (text1, len(text1))

text2, fits2 = opening_stub('x' * 30, 'y' * 30, 'z' * 30)
assert fits2 is False, (text2, len(text2))
assert text2.startswith('结论：') and '假设：' in text2 and '接下来我按：' in text2

for t, f in [(text1, fits1), (text2, fits2)]:
    print(f'{t}\\n  -> {len(t)} 字, fits={f}')
print('\\n练习 1 通过：把结论/假设/计划拼成一句话，先测它是不是真的能在 10 秒内说完。')"""),

    md("""## ✏️ 练习 2：提分收益排序（沟通三铁律版）

实现 `laws_gap(flags)`，返回 `[(铁律, 补齐它的收益), ...]`：
- 收益 = `(1/3) if not flags.get(key, False) else 0`（每条铁律权重相等）
- 按收益**降序**；收益相同时按 `LAWS` 里定义的原始顺序排列（保证结果确定）"""),

    code("""def laws_gap(flags):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
gap = laws_gap(BAD_FLAGS)
names = [k for k, _ in gap]
vals = [v for _, v in gap]
assert names == ['conclusion_first', 'explicit_assumptions', 'surfaced_uncertainty'], names
assert np.allclose(vals, [1 / 3, 1 / 3, 0.0]), vals

gap_good = laws_gap(GOOD_FLAGS)
assert all(v == 0.0 for _, v in gap_good)

for k, v in gap:
    print(f'  {k:<22} 补齐可加 {v:.3f}')
print('\\n练习 2 通过：坏回答该补的是"结论先行"和"显式说假设"，"暴露不确定性"这条它已经做到了。')"""),

    md("""## ✏️ 练习 3：两段回答的胜负判定

实现 `compare_answers(tags_a, tags_b)`，复用 `score_answer`：
返回 `(winner, margin)`，`winner ∈ {'a', 'b', 'tie'}`，
当两者分数之差小于 `1e-9` 时判为 `'tie'`，否则 `margin = abs(score_a - score_b)`。"""),

    code("""def compare_answers(tags_a, tags_b):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
w, m = compare_answers(GOOD_ANSWER, BAD_ANSWER)
assert w == 'a', w
assert abs(m - 0.9) < 1e-6, m

w2, m2 = compare_answers(GOOD_ANSWER, GOOD_ANSWER)
assert w2 == 'tie' and m2 == 0.0

print(f'好回答 vs 坏回答 -> 胜者 {w}，分差 {m:.2f}')
print(f'好回答 vs 好回答 -> {w2}，分差 {m2:.2f}')
print('\\n练习 3 通过：同样的知识内容，结构上的差距能拉开接近满分的差距。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def opening_stub(conclusion, assumption, plan, cps=4.5, seconds=10):
    text = f'结论：{conclusion}。假设：{assumption}。接下来我按：{plan}。'
    fits = opening_ok(text, cps=cps, seconds=seconds)
    return text, fits"""),

    code("""# 练习 2 参考答案
def laws_gap(flags):
    out = [(k, 0.0 if flags.get(k, False) else 1 / 3) for k, _ in LAWS]
    return sorted(out, key=lambda kv: -kv[1])"""),

    code("""# 练习 3 参考答案
def compare_answers(tags_a, tags_b):
    sa, sb = score_answer(tags_a), score_answer(tags_b)
    if abs(sa - sb) < 1e-9:
        return 'tie', 0.0
    return ('a' if sa > sb else 'b'), abs(sa - sb)"""),

    md("""---
## 🧪 真实工程胶囊：四步框架 + 三铁律的现场口播模板（中英对照）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 四步框架的现场口播模板（中 / EN —— JD 是英文岗，两套都要能说）
# ══════════════════════════════════════════════════════════════════════
# 澄清 CN: 「在开始前，我想先确认几个边界条件：……」
#        EN: "Before I start, let me confirm a few boundaries: ..."
# 分解 CN: 「我把这个问题拆成三块：……」
#        EN: "I'll break this into three parts: ..."
# 假设与验证 CN: 「我先假设是……，可以通过……验证」
#            EN: "My working hypothesis is ..., which I'd verify by ..."
# 收敛与权衡 CN: 「综合来看我会选……，代价是……」
#            EN: "Weighing these, I'd go with ..., at the cost of ..."

# ══════════════════════════════════════════════════════════════════════
# B. 沟通三铁律的口播模板
# ══════════════════════════════════════════════════════════════════════
# 结论先行     CN: 「先说结论：……，下面是我的推理。」
#             EN: "My conclusion first: ..., here's the reasoning."
# 显式说假设   CN: 「这里我假设……，如果不成立，结论会变成……。」
#             EN: "I'm assuming ... here; if that doesn't hold, the answer changes to ..."
# 暴露不确定性 CN: 「这部分我不确定，把握大概六成，我会这样去验证……」
#             EN: "I'm not fully sure here, maybe 60% confident; I'd verify by ..."

# ══════════════════════════════════════════════════════════════════════
# C. 与其他板块 / 课程的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 六步编码协议（C62 模块 00）是这个框架在"产出是代码"场景下的具体化
# · ML system design 七步框架（C63 模块 00）是这个框架在"产出是架构"场景下的具体化
# · 估算（C65-01）/ 诊断（C65-02）/ 权衡（C65-03）/ 模糊需求（C65-04）/ 模拟演练（C65-05）
#   都是这四步框架在具体场景下的展开，不是四个新框架
# · 项目叙事（C61-04）用的是 STAR，讲的是"已经发生的事"，不是当场解一道新题——不要混用
'''
print(RECIPE)
for token in ['澄清', '分解', '假设', '收敛', '结论先行', 'C62 模块 00', 'C63 模块 00', 'STAR']:
    assert token in RECIPE, token
print('检查单覆盖：四步框架口播 / 三铁律口播 / 与其他课程的分工')"""),

    md("""### 小结

- **problem-solving 考的是思维过程的可见性**：面试官买的是你的推理，不是答案本身；
  一段没有被说出来的正确判断，在评分表上等于不存在。
- **四步通用框架**（澄清 → 分解 → 假设与验证 → 收敛与权衡）是本课所有模块共用的骨架，
  且不是走一次就完事的直线——分解暴露新歧义可以跳回澄清，权衡时假设被证伪可以跳回验证。
- **沟通三铁律**：结论先行 / 显式说假设 / 主动暴露不确定性。
  其中"暴露不确定性"最反直觉——**提前承认不确定，永远比被追问戳穿要安全**。
- **"想清楚再说"和"边想边说"都不是最优解**：折中方案是先用 10 秒给一个结构性的锚点
  （结论 + 假设 + 展开顺序，字数上限约 40-50 字），再边展开边验证。
- **同样的知识内容，结构上的差距可以拉开接近满分的差距**——这是本课程存在的理由：
  这门课补的不是知识密度，是表达结构。
- **本课与相邻课程分工**：C62 六步协议 / C63 七步框架都是这个四步框架的场景特化；
  C61-04 项目叙事用 STAR，讲过去而非当场解题，不要混用。

下一站：**模块 01 · 估算题与数量级心算** —— 用 Fermi 方法把"分解"这一步做深，
学会在没有任何数据的情况下，靠锚点数字和乘法给出一个数量级正确的答案。"""),
]
