# -*- coding: utf-8 -*-
"""C62 模块 00 · 课程总览与环境（编程面试实战：算法与数据结构）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "会写 Python（列表/字典/切片/函数），知道 for 与 while 的区别即可；不需要任何算法竞赛经验"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb（纯标准库 + numpy，六步协议自检器 / 复杂度换算器 / 一道题的全流程演示）'),
    ("核心参考", "HR 给出的一面形式说明 · CTCI 第 VII 章「Technical Questions」 · Google/Meta 公开的 coding rubric · 本课程 C61 模块 05（检测专项白板题）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("what-is-tested", "一面的 coding 环节到底在考什么", "".join([
        P("HR 把一面写成三段：<em>Technical Knowledge Assessment</em>（技术知识）、<em>Problem-Solving</em>（问题求解）、"
          "<strong><em>Practical (Coding) Exercise</em></strong>（实操编码）。第三段就是本课的战场——"
          "它是整个面试里<strong>唯一一个「你写下的东西会被逐字审视」</strong>的环节。"),
        P("先把最大的误解拆掉：<strong>ML/CV 岗的 coding 环节，题目难度的中位数是 LeetCode easy–medium，不是 hard</strong>。"
          "面试官手里通常只有 45 分钟，还要留时间寒暄、介绍题目、追问、答疑；他没有时间看你解一道需要灵光一闪的难题，"
          "也没有兴趣。<em>他真正想回答的问题是</em>："),
        CALLOUT("intuition", "「把一个我没提前告诉他的中等难度问题交给这个人，45 分钟后，他能不能交出一段<strong>我敢直接合进代码库</strong>的东西？」——"
                             "注意这句话里三个词：<strong>我没提前告诉他</strong>（考的是过程不是记忆）、<strong>45 分钟</strong>（考的是时间管理）、"
                             "<strong>敢合入</strong>（考的是正确性 + 可读性 + 你自己测过）。"),
        P("于是这个环节的交付物其实有<strong>三件</strong>，而不是一件。绝大多数人只交了第一件："),
        TABLE(["交付物", "具体形态", "不交会怎样", "被忽略的程度"], [
            ["① 一段能跑的代码", "15–40 行，变量名可读，能处理边界", "直接不及格", "所有人都知道"],
            ["② <strong>一句诚实的复杂度陈述</strong>", "「时间 O(n)，空间 O(1)，因为每个元素最多被两个指针各扫一次」", "面试官会认为你不知道自己写了什么", "<strong>一半人会说错或含糊过去</strong>"],
            ["③ <strong>一套你自己造的测试</strong>", "正常用例 + 空 + 单元素 + 全相同 + 极值，当场跑一遍", "「写完不测」是最常见的扣分项", "<strong>大部分人根本不做</strong>"],
        ]),
        DUAL(
            "换个说法：这一环节考的不是「你会不会这道题」，而是「<strong>你在不会的时候是怎么工作的</strong>」。"
            "一个当场认出原题、三分钟默写出最优解、全程不说话的候选人，分数常常低于一个先给 O(n²) 暴力解、"
            "讲清楚它慢在哪、然后一步步优化到 O(n)、最后自己造了五个测试用例跑通的候选人。"
            "<em>前者展示的是记忆，后者展示的是可复现的工作方式——公司雇的是后者。</em>",
            "更严谨地说：面试官是在用一个 45 分钟的<strong>高噪声样本</strong>，去估计「此人日常产出代码的质量分布」。"
            "样本量只有 1，所以他必须依赖那些<strong>方差小、可迁移</strong>的信号：是否先澄清需求（对应线上是否会写错需求）、"
            "是否先给可行解再优化（对应是否会过早优化）、是否主动测试（对应是否会把 bug 推到 code review）、"
            "是否诚实报复杂度（对应是否会对自己代码的性能撒谎）。<em>「解出题目」这个信号方差极大</em>"
            "——换一道题结果可能完全相反——所以它在评分里的权重反而没有你以为的那么高。",
        ),
        H3("本课在整个课程体系里补的是哪个洞"),
        P("这门课补的是<strong>全库最大的一个缺口</strong>。C00–C61 这 62 门课覆盖了检测、TSR、部署、VLA 等领域深度，"
          "但用关键词检索全库可以确认：<strong>「链表」「双指针」零命中，「时间复杂度」只出现在 1 门课里，「哈希表」也只有 1 门</strong>。"
          "也就是说，在此之前，你为这场面试准备的所有内容，都无法帮你通过 Practical (Coding) Exercise 这一关。"),
        TABLE(["课程", "考察板块", "题目形态", "与本课的关系"], [
            ["<strong>C62（本课）</strong>", "Practical (Coding) Exercise", "<strong>通用算法题</strong>：数组、字符串、哈希、二分、树图、DP", "本课主线"],
            ["C61 模块 05", "Practical (Coding) Exercise（<em>检测专项</em>）", "手撕 IoU / NMS / mAP / 匈牙利 / Focal Loss", "<strong>不重复</strong>：那些题只在 C61，本课需要时用「见 C61-05」引用"],
            ["C63", "System Design", "「设计一个 TSR 感知系统」", "同一场面试的另一段，无重叠"],
            ["C64", "Technical Knowledge", "「解释一下 BN 和 LN 的区别」", "口头问答，不写代码"],
            ["C65", "Problem-Solving", "估算、诊断、权衡、模糊需求", "本课的六步协议是它的特例"],
        ]),
        CALLOUT("warn", "<strong>不要指望「我是 ML 岗，应该不考算法题」。</strong>恰恰相反：算法题是所有技术岗位里<em>最标准化、最容易横向比较</em>的一段，"
                        "所以它常常是筛人的第一道闸门。一个候选人可以在 ML 知识上说得天花乱坠，"
                        "但如果连一道滑动窗口都写不对，面试官会立刻降低对他<strong>全部</strong>技术陈述的可信度——"
                        "<em>因为这是唯一一段有客观对错的内容</em>。"),
    ])),

    # ============================================================== 2
    ("protocol", "六步答题协议：把「灵光一闪」变成「可复现的流程」", "".join([
        P("整门课只有一个东西必须背下来，就是它。<strong>六步答题协议</strong>的价值不在于它能让你解出更多题，"
          "而在于它让你在<em>解不出来的时候仍然能拿到分</em>——因为每一步都是独立计分的可见产出。"),
        ASCII("""┌──────────────────────────────────────────────────────────────────────┐
│  ① 复述与澄清        「我复述一遍：给定……返回……。我想确认三件事：      │
│     (restate)          数组有序吗？可以有重复吗？空数组返回什么？」    │
│         │              产出：一句复述 + 3–5 个问题                     │
│         ▼                                                             │
│  ② 举例走一遍        手造一个 5–8 元素的小例子，**口算**出答案；      │
│     (example)          再造一个边界例子（空 / 单元素 / 全相同）        │
│         │              产出：白板左上角一组 (输入 → 期望输出)          │
│         ▼                                                             │
│  ③ 先给暴力解        「最直接的做法是两层循环，O(n²)。我先说清楚它，  │
│     (brute force)      这样我们至少有一个正确的参照。」                │
│         │              产出：一句话说清做法 + 复杂度  ← **安全网**     │
│         ▼                                                             │
│  ④ 说优化思路        「暴力解里，内层循环反复算了同一段和 →           │
│     (optimize)         可以用前缀和把它降到 O(1)。目标 O(n)。」        │
│         │              产出：**指出重复计算在哪** + 目标复杂度 + 停顿  │
│         ▼              ←──── 在这里**等面试官点头**再往下走            │
│  ⑤ 写代码            边写边讲。先写主干骨架，再回头补边界。           │
│     (code)             产出：15–40 行，变量名可读                      │
│         │                                                             │
│         ▼                                                             │
│  ⑥ 测试与复杂度      跑第②步造的用例 + 边界用例；**报时间与空间复杂度**│
│     (test)             产出：「我过一遍：[2,7,11,15], target=9 → …」   │
└──────────────────────────────────────────────────────────────────────┘"""),
        P("六步各自解决什么问题、以及不做会被扣什么，逐条对照："),
        TABLE(["步骤", "解决什么问题", "跳过它的典型后果", "面试官心里记的那一笔"], [
            ["① 复述与澄清", "防止解错题；把隐含约束显式化", "写到一半才发现「原来数组是有序的」，或者「原来可能有负数」", "「他不问需求就动手」——这是<strong>线上事故的性格画像</strong>"],
            ["② 举例走一遍", "让你和面试官对「正确」达成共识；小例子还常常直接暴露解法", "写完代码没法验证，只能靠读代码找 bug", "「他没有 ground truth 就开始写」"],
            ["③ <strong>先给暴力解</strong>", "拿到保底分；给优化提供一个对照物", "卡在想最优解上，20 分钟白板一片空白", "「他没有可行解就去追最优解」——<strong>最致命的一条</strong>"],
            ["④ 说优化思路", "把「思考」变成可见的产出；给面试官提示你的机会", "闷头写一个自己也不确定的解法", "「我不知道他在想什么，也没法帮他」"],
            ["⑤ 写代码", "交付物本体", "—", "变量名、边界、缩进层数都在这里被看到"],
            ["⑥ 测试与复杂度", "证明你不是「写完就扔」", "面试官发现 bug 而不是你发现 bug", "「他的代码需要别人来兜底」"],
        ]),
        DUAL(
            "为什么第③步「先给暴力解」是整个协议里最反直觉、也最值钱的一步？"
            "因为大多数人的本能是「我不能让他觉得我只会写笨办法」，于是憋着不说，直接冲最优解。"
            "<strong>但面试官的计分板上，「有一个正确的可行解」和「有一个最优解」是两格，前一格先拿到手才安全。</strong>"
            "而且说出暴力解<em>不会</em>降低对你的评价——恰恰相反，它显示你能快速把问题归约到一个已知可解的形式，"
            "这正是工程师日常做的事。<em>真正掉价的是「既没有暴力解也没有最优解」的 20 分钟沉默。</em>",
            "从决策论看，这是一个<strong>期望值问题</strong>。设直接冲最优解的成功概率为 $p$，用时 $T_1$；"
            "先写暴力解要花 $t_0$ 分钟，但把「至少有可行解」的概率提到接近 1。"
            "在 45 分钟的硬约束下，直接冲最优解的失败分支（概率 $1-p$）的收益接近 0，"
            "而先给暴力解的失败分支仍能拿到「正确性 3/5 + 沟通 4/5」。<em>只要 $p < 0.85$ 左右，"
            "先给暴力解的期望分就更高</em>——而对一道你没见过的中等题，$p$ 通常远低于 0.85。"
            "更进一步：暴力解还提供了<strong>对拍基准</strong>（第 6 节与模块 01 会反复用到），"
            "让你能当场用随机测试验证最优解的正确性，这在评分表上又是一格。",
        ),
        CALLOUT("danger", "<p><strong>面试当场最容易翻车的三种开局</strong>，按危害排序：</p>"
                          "<p>① <strong>听完题目立刻开始写代码</strong>。这一个动作同时丢掉步骤 ①②③④ 的分。"
                          "即使你最后写对了，评分表上「沟通」和「测试意识」两栏也已经是低分了。<br>"
                          "② <strong>沉默超过 30 秒</strong>。面试官无法区分「在深度思考」和「已经卡死」，只能按后者记。"
                          "正确做法是把卡住这件事本身说出来：「我现在在想能不能用哈希把内层循环干掉，但我不确定重复元素怎么处理，让我先写个例子。」<br>"
                          "③ <strong>默默修改题目</strong>。想不出来就悄悄假设「输入一定有序」——面试官会当场记下「他改需求不打招呼」。"
                          "要改就大声改：「如果我可以假设输入有序，这题就变成对撞指针 O(n)；我可以先做这个版本吗？」</p>",
                "开局三雷"),
    ])),

    # ============================================================== 3
    ("time-budget", "45 分钟怎么分：时间预算表与超时补救", "".join([
        P("六步协议如果没有时间预算，就会变成「前四步讲得很爽，第五步只剩 8 分钟」。"
          "下面这张预算表是按 <strong>45 分钟一题</strong>标定的（这是最常见的配置；如果是 60 分钟两题，"
          "按 25 + 25 分配并把澄清压到 3 分钟）。notebook 里有可按总时长自动缩放的实现。"),
        ASCII("""0        4      7      11          17                      35            43   45
├────────┼──────┼──────┼───────────┼───────────────────────┼─────────────┼────┤
│ ①澄清  │②举例│③暴力 │ ④优化思路 │      ⑤ 写代码         │  ⑥ 测试     │缓冲│
│  4 min │ 3min │ 4min │   6 min   │       18 min          │   8 min     │2min│
└────────┴──────┴──────┴───────────┴───────────────────────┴─────────────┴────┘
             ▲                  ▲                        ▲
             │                  │                        │
      口算出期望输出      **在这里等点头**       17 分还没动键盘 = 危险
                          （面试官若不点头，
                            通常是你想复杂了）

关键检查点（把这三个数字记住，比记住整张表有用）：
  第 11 分钟 —— 必须已经说出暴力解与它的复杂度
  第 17 分钟 —— 必须开始写代码（无论是暴力解还是最优解）
  第 37 分钟 —— 必须停止写新代码，转入测试"""),
        P("<strong>「第 17 分钟必须开始写代码」是这张表里唯一不能妥协的一条。</strong>"
          "在此之前你可以任意压缩前四步，但一旦过了 17 分钟还没落笔，剩下的时间已经不足以「写完 + 测完」，"
          "而未测过的代码在评分表上接近于没有代码。"),
        H3("超时补救：三种情况，三个动作"),
        TABLE(["症状", "触发时刻", "立即动作", "话术（照抄）"], [
            ["想不出最优解", "第 15 分钟", "<strong>放弃优化，直接写暴力解</strong>，写完再回头优化", "「我先把 O(n²) 的版本写出来保证正确，如果还有时间我们再优化。」"],
            ["代码写到一半发现思路错了", "第 28 分钟", "<strong>不要删</strong>。说出你的判断和证据，问是否值得改", "「我发现这个写法在有重复元素时会漏，反例是 [1,1,2]。我想改成先排序再对撞，大约需要 5 分钟，可以吗？」"],
            ["写完了但只剩 3 分钟", "第 42 分钟", "<strong>放弃跑全部用例</strong>，只口述边界 + 报复杂度", "「时间关系我口头过一遍边界：空数组走 while 直接退出返回 []；单元素时 left==right 循环不进入。时间 O(n)，空间 O(1)。」"],
            ["面试官频繁打断提示", "任何时刻", "<strong>停下来接住提示</strong>，这是救命绳不是干扰", "「您是说可以用一个哈希表记住已经见过的？让我想 20 秒……对，那内层循环就没了。」"],
        ]),
        DUAL(
            "很多人以为超时补救是「加快速度」。不是。<strong>补救的本质是<em>降级交付</em>：主动把目标从「最优解 + 完整测试」"
            "降到「可行解 + 口述边界」，并且<u>把这个降级决定说出来</u>。</strong>"
            "说出来和不说出来是两个完全不同的分数：不说，面试官看到的是「他没写完」；"
            "说了，面试官看到的是「他在时间约束下做了合理的取舍并主动沟通」——<em>后者恰好是工程师最值钱的能力之一</em>。",
            "这条原则与 C63 的系统设计、C65 的权衡决策是同一条：<strong>在硬约束下，显式的降级路径比隐式的失败有价值得多</strong>。"
            "在车端感知系统里，这叫<span class=\"term\">graceful degradation</span>（优雅降级）——"
            "算力不足时主动把 decoder 从 6 层降到 3 层（见 C53-04），比直接丢帧强；"
            "在面试里，主动宣布「我现在改为交付暴力解 + 口述复杂度」，比默默写不完强。"
            "<em>面试官对这类信号极其敏感，因为它直接预测了你在项目 deadline 前的行为。</em>",
        ),
        CALLOUT("warn", "别把缓冲的 2 分钟花在「再优化一点点」上。那 2 分钟的最佳用途是<strong>反问</strong>："
                        "「这道题在你们实际工作里对应什么场景？」——这既是真实的好奇，也让面试官在收尾时对你留下正面印象。"
                        "<em>如果他说「我们做 TSR 的时候，多帧投票的窗口维护其实就是个滑动窗口」，你就拿到了后续话题的钥匙。</em>"),
    ])),

    # ============================================================== 4
    ("rubric", "面试官的五维评分表：分到底是怎么给的", "".join([
        P("大公司的 coding 面试普遍使用<strong>五维打分 + 加权</strong>的评分卡（rubric），每维 1–5 分。"
          "各家权重略有不同，但维度几乎一致。下面这套权重是一个可用的近似，notebook 里会把它代码化并做敏感性分析。"),
        TABLE(["维度", "权重", "1 分（不及格）", "3 分（及格）", "5 分（强通过）"],[
            ["<strong>正确性</strong> correctness", "0.30", "跑不通 / 逻辑根本错", "最优解基本对，边界有小漏", "最优解正确，边界全覆盖"],
            ["<strong>复杂度</strong> complexity", "0.20", "说不出复杂度，或说错", "能报对时间复杂度", "时间 + 空间都对，能说清<em>为什么</em>是这个量级"],
            ["<strong>代码质量</strong> code quality", "0.15", "单字母变量满天飞，嵌套 4 层", "可读，函数职责单一", "命名自解释，边界处理内聚，不用注释也读得懂"],
            ["<strong>沟通</strong> communication", "0.20", "长时间沉默 / 答非所问", "被问才答", "边写边讲，主动暴露不确定性，接得住提示"],
            ["<strong>测试意识</strong> testing", "0.15", "写完就说「好了」", "跑一个正常用例", "主动列边界清单并逐个跑，能自己找出 bug"],
        ]),
        P("把两个典型候选人代进去算一下，结论会让很多人不舒服："),
        TABLE(["候选人", "正确性", "复杂度", "代码质量", "沟通", "测试", "<strong>加权总分</strong>"], [
            ["<strong>A：沉默的最优解</strong><br><em>认出原题，5 分钟默写最优解，全程不说话，写完说「好了」</em>", "5", "5", "3", "1", "1", "<strong>3.30</strong>（不及格线通常在 3.5）"],
            ["<strong>B：会说话的暴力解</strong><br><em>没见过题，澄清 4 个问题，先给 O(n²)，讲清优化方向但没写完最优解，造了 5 个用例全跑通</em>", "4", "3", "4", "5", "5", "<strong>4.15</strong>（强通过）"],
        ]),
        CALLOUT("intuition", "<strong>沟通 + 测试意识合计占 35%，比正确性还多 5 个百分点。</strong>"
                             "这不是「大厂搞形式主义」——这两栏度量的是<em>你的产出需不需要别人兜底</em>，"
                             "而这恰恰是团队协作里成本最高的一项。把这个数字记住，它会改变你练题的方式："
                             "<strong>练「边写边讲 + 主动测试」的边际收益，高于多刷 50 道题。</strong>"),
        DUAL(
            "怎么用这张表指导准备？算<strong>提分收益</strong>：每一维「提升 1 分」的加权收益 = 权重 × 还差几分。"
            "对上面的候选人 A，收益排序是 沟通 0.20×4 = 0.80 &gt; 测试 0.15×4 = 0.60 &gt; 代码质量 0.15×2 = 0.30 &gt; 其余 0。"
            "<em>也就是说，A 应该做的不是再刷 100 道题（正确性已经满分），而是找个人对着讲一遍。</em>"
            "notebook 的练习 2 会把这个计算实现出来，你可以拿自己的模拟面试录像去打分。",
            "需要说明这套权重的<strong>局限</strong>：① 各家权重不同，有的公司把正确性提到 0.4，"
            "有的把「问题分解能力」单列一维；② 存在<strong>门槛效应</strong>——正确性拿 1 分通常直接一票否决，"
            "加权总分再高也没用，所以不能把它当成纯线性模型；③ 面试官之间的方差很大，"
            "同一份表现在不同面试官手里可能差 0.5 分。<em>正确的用法是把它当作<u>注意力分配的工具</u>"
            "（告诉你练什么），而不是当作可以精确预测结果的模型。</em>",
        ),
        CALLOUT("danger", "<strong>「正确性 1 分」是一票否决项。</strong>加权模型在这里失效：如果你的代码在面试官脑子里跑出了错误结果，"
                          "后面四栏拿满分也救不回来。<em>这就是为什么第③步「先给暴力解」如此重要——它把正确性的下限从 1 抬到 3。</em>"),
    ])),

    # ============================================================== 5
    ("ml-cv-topics", "ML/CV 岗的题型分布：把有限的时间花在哪", "".join([
        P("通用软件工程岗和 ML/CV 岗的 coding 题分布<strong>并不相同</strong>。差别来自出题人——"
          "给你出题的多半是感知组的工程师，他会本能地出他熟悉的题。这带来一个可利用的先验："),
        TABLE(["题型", "在 ML/CV 岗的频率", "代表题", "为什么这个岗位爱考", "本课位置"], [
            ["<strong>数组 / 双指针 / 滑动窗口</strong>", "<strong>高频·必会</strong>", "两数之和、无重复最长子串、区间合并、最小覆盖子串", "特征序列、时间窗口、区间运算是日常操作", "<strong>模块 01</strong>"],
            ["<strong>矩阵与几何</strong>", "<strong>高频·必会</strong>", "矩阵旋转、螺旋遍历、二维前缀和、二维矩阵搜索", "图像就是二维数组；IoU、坐标变换天天写", "模块 01 / 05"],
            ["<strong>区间问题</strong>", "<strong>高频·必会</strong>", "区间合并、区间交集、会议室 II、区间调度", "<strong>IoU 的一维投影就是区间求交；NMS 就是排序 + 扫描</strong>", "模块 01 / 04"],
            ["<strong>排序 + 二分</strong>", "<strong>高频·必会</strong>", "找左右边界、在答案上二分、Top-K", "阈值搜索、分位数、NMS 排序、工作点选择", "模块 02"],
            ["<strong>哈希与计数</strong>", "<strong>高频·必会</strong>", "字母异位词分组、Top-K 频次、去重", "类别统计、标签映射、长尾频次分析", "模块 02"],
            ["<strong>采样与随机</strong>", "<strong>中频·加分</strong>", "蓄水池采样、加权采样、Fisher-Yates 洗牌", "<strong>数据采样与长尾重采样是本岗位日常</strong>（见 C58）", "模块 05"],
            ["<strong>字符串解析</strong>", "中频·必会", "解析日志/配置、版本号比较、路径简化", "数据管线里解析标注文件与日志", "模块 01 / 02"],
            ["树与递归", "中频·必会", "二叉树遍历、层序、路径和", "递归三要素是通用能力；决策树/层次标签", "模块 03"],
            ["<strong>并查集 / 连通域</strong>", "中频·加分", "岛屿数量、朋友圈、bbox 聚类", "<strong>连通域标记就是网格 DFS；切片推理的跨片合并就是并查集</strong>", "模块 03"],
            ["DP 与贪心", "中频·加分", "编辑距离、01 背包、最长上升子序列、区间调度", "序列评测、预算分配、NMS 的最优选择", "模块 04"],
            ["图论进阶（最短路 / 网络流）", "<strong>低频</strong>", "Dijkstra、拓扑排序", "偶尔出现，拓扑排序在流水线依赖里有用", "模块 03（只给骨架）"],
            ["高级数据结构（线段树 / Trie / 平衡树）", "<strong>低频·不必强求</strong>", "区间最值查询、前缀树", "几乎不出现在 ML 岗；出现了也允许说「我会用 <code>bisect</code> 顶一下」", "不覆盖"],
        ]),
        CALLOUT("intuition", "这张表的<strong>使用方法</strong>：如果你只有 20 小时准备时间，"
                             "把 16 小时放在前五行（模块 01 + 02），3 小时放在采样与并查集，1 小时用来做模拟面试。"
                             "<em>把时间平均分给所有题型，是准备算法面试最常见的资源错配。</em>"),
        H3("复杂度速查：从 n 的量级反推「你被允许用什么算法」"),
        P("这是面试里一个<strong>免费的提示</strong>，而且大多数人不会用。当面试官说出「数组长度最多 $10^5$」时，"
          "他已经把答案的复杂度告诉你了。经验换算的依据是：一台现代机器每秒可做 $10^8$ 量级的基本操作（C/C++），"
          "而 <strong>Python 由于解释开销，实际能跑的量级是 $10^6$–$10^7$</strong>："),
        MATH("T(n) \\;\\approx\\; c \\cdot f(n) \\;\\le\\; B, \\qquad B_{\\text{C/C++}} \\approx 10^{8},\\quad B_{\\text{Python}} \\approx 10^{7}"),
        MATH("n \\le 10 \\Rightarrow O(n!) \\;\\;|\\;\\; n \\le 22 \\Rightarrow O(2^n) \\;\\;|\\;\\; n \\le 500 \\Rightarrow O(n^3) \\;\\;|\\;\\; n \\le 3\\times10^3 \\Rightarrow O(n^2) \\;\\;|\\;\\; n \\le 10^6 \\Rightarrow O(n\\log n) \\;\\;|\\;\\; n \\ge 10^7 \\Rightarrow O(n)"),
        P("这条阶梯是按 $B\\approx10^8$ 的通用口径给的（面试里大家默认的就是它，已留出安全余量）。"
          "<strong>用 Python 实测时要再打一个数量级的折扣</strong>——notebook 里两种预算的表都会打出来，"
          "唯一有分歧的格子恰好在 $n=10^6$：$C{+}{+}$ 下 $O(n\\log n)$ 还能跑（$2\\times10^7$ 次操作），Python 下就只剩 $O(n)$ 了。"),
        DUAL(
            "怎么当场用？听到「$n \\le 10^5$」，你就可以说："
            "「$10^5$ 排除了 $O(n^2)$（那是 $10^{10}$ 次操作），所以目标是 $O(n\\log n)$ 或 $O(n)$。"
            "$n\\log n$ 通常意味着排序或二分，$O(n)$ 通常意味着双指针、滑动窗口或哈希。让我先看看哪个性质可以利用。」"
            "<strong>这一句话同时展示了复杂度意识、算法储备和推理过程——三个评分维度一次拿到。</strong>",
            "反过来，这个换算也告诉你<strong>什么时候不该优化</strong>。如果面试官说 $n \\le 1000$，"
            "那 $O(n^2) = 10^6$ 完全可以接受，此时花 15 分钟去想 $O(n\\log n)$ 是<span class=\"term\">premature optimization</span>"
            "（过早优化），而且写出来的代码更容易错。<em>正确的做法是明说：「$n\\le1000$ 时 $O(n^2)$ 是 $10^6$ 次操作，"
            "在预算内，所以我先写简单正确的版本；如果你想看 $O(n\\log n)$ 我再展开。」——"
            "这句话在评分表上比硬写一个最优解更值钱，因为它显示你会算成本收益。</em>",
        ),
        CALLOUT("warn", "<strong>不要把 $O(\\cdot)$ 里的常数当成不存在。</strong>面试里说「都是 $O(n)$ 所以一样快」会被追问。"
                        "在 Python 里，一次 <code>dict</code> 查找的常数大约是一次列表下标访问的 3–5 倍，"
                        "一次 <code>np.ndarray</code> 的向量化操作又比 Python 循环快 20–100 倍。"
                        "<em>这就是为什么手写 NMS 的 numpy 版和纯 Python 版都是 $O(NK)$，但实测差两个数量级（见 C53-04）。</em>"),
    ])),

    # ============================================================== 6
    ("python-subset", "Python 面试子集：哪些内置大方用，哪些会被判「绕过考点」", "".join([
        P("Python 的标准库强大到可以把很多算法题变成一行。<strong>问题是：一行流解决的那道题，考点可能正好是那一行。</strong>"
          "判断规则其实非常简单，只有一条："),
        CALLOUT("intuition", "<strong>如果这个内置函数<em>就是</em>本题要考的那个数据结构或算法，那就不能直接用；"
                             "如果它只是一个与考点无关的工具，那就大方用，而且用得越熟练越好。</strong>"
                             "拿不准的时候，把选择权交给面试官：「我可以用 <code>collections.Counter</code> 吗？"
                             "还是您希望我手写这个计数逻辑？」——<em>问这一句，两种情况你都拿分。</em>"),
        TABLE(["内置 / 库", "什么时候大方用", "什么时候会被判「绕过考点」", "被拦下时怎么办"], [
            ["<code>sorted</code> / <code>list.sort</code>", "题目主体是别的（区间合并、Top-K 的对照解），排序只是预处理", "题目就是「实现快速排序 / 归并排序」", "手写归并（稳定、好写、O(n log n) 稳定不退化）"],
            ["<code>dict</code> / <code>set</code>", "<strong>几乎总是可以用</strong>。两数之和、去重、计数都指望它", "题目是「实现一个哈希表 / 处理哈希冲突」", "用数组 + 链地址法手写 <code>put/get</code>"],
            ["<code>collections.Counter</code>", "字符串统计、频次分析的<em>辅助</em>步骤", "题目是「统计词频并返回 Top-K」——Counter 会把整道题吃掉", "<code>d = {}; d[c] = d.get(c, 0) + 1</code>，两行而已"],
            ["<code>bisect</code>", "需要在有序数组上定位但考点不是二分（如 LIS 的 O(n log n) 解法）", "<strong>题目就是「实现二分查找 / 找左边界」</strong>", "手写三套模板（模块 02），并用 <code>bisect</code> 对拍"],
            ["<code>heapq</code>", "Top-K、合并 K 个有序表、Dijkstra", "题目是「实现一个堆 / siftup siftdown」", "手写数组表示的二叉堆"],
            ["<code>itertools</code>", "生成测试用例、写暴力解做对拍", "用 <code>permutations</code> 硬解本该 DP 的题（复杂度也不对）", "回到 DP / 回溯"],
            ["<code>functools.lru_cache</code>", "<strong>记忆化搜索的标准写法，大方用并说明</strong>", "几乎不会被拦，但要能说清它等价于手写 memo 字典", "手写 <code>memo = {}</code>"],
            ["<code>numpy</code>", "<strong>ML 岗的加分项</strong>：向量化 IoU、矩阵操作、采样验证", "题目明确要求「不用第三方库」，或考的是循环边界本身", "回到纯 Python，但可以先说「生产里我会向量化」"],
            ["<code>re</code> 正则", "解析日志、提取字段这类真实工程题", "题目是「实现字符串匹配 / KMP」", "手写朴素匹配 + 说明 KMP 思路"],
        ]),
        H3("三个必须熟练、且几乎不会被拦的写法"),
        UL([
            "<strong>切片与负索引</strong>：<code>a[::-1]</code>、<code>a[i:j]</code>、<code>a[-1]</code>。"
            "但要知道<em>切片是 O(k) 拷贝</em>——在循环里切片会把 O(n) 悄悄变成 O(n²)，这是 Python 面试里非常常见的隐藏复杂度陷阱。",
            "<strong>解包与多重赋值</strong>：<code>left, right = right, left</code>、<code>for i, x in enumerate(a)</code>。"
            "对撞指针的交换用它，代码短一半且不会写错临时变量。",
            "<strong><code>dict.get</code> / <code>collections.defaultdict</code></strong>：避免 <code>if k in d</code> 的分支，"
            "让滑动窗口的计数逻辑压到两行。<em>但 <code>defaultdict</code> 有个坑：读取不存在的 key 会<u>创建</u>它，"
            "在「窗口内还剩几种字符」这类判断里会导致计数错误</em>——模块 01 会踩这个坑给你看。",
        ]),
        DUAL(
            "还有一类问题是<strong>整数与浮点</strong>。Python 的 int 是任意精度，所以「整数溢出」这个在 C++/Java 面试里的经典考点，"
            "在 Python 里不存在——<em>但你仍然要提到它</em>：「在 Python 里 <code>(lo+hi)//2</code> 不会溢出，"
            "但如果是 C++ 我会写 <code>lo + (hi-lo)/2</code>。」<strong>这一句话展示的是跨语言的正确性意识，成本几乎为零。</strong>",
            "浮点则是<strong>真的会出事</strong>：IoU、置信度、坐标都是浮点，<code>==</code> 比较几乎总是错的。"
            "面试里写 <code>assert iou == 0.5</code> 会被当场指出；正确写法是 <code>abs(iou - 0.5) &lt; 1e-9</code> 或 "
            "<code>np.allclose</code>。<em>更隐蔽的是把浮点数当 <code>dict</code> 的 key</em>（模块 02 会展开）："
            "<code>0.1 + 0.2</code> 不等于 <code>0.3</code>，所以 <code>d[0.1+0.2]</code> 取不到 <code>d[0.3]</code>。"
            "在 TSR 的框去重里，如果你用「坐标元组」做 key 来判重，就会踩这个坑——"
            "<strong>正确做法是量化到整数像素再做 key</strong>。",
        ),
        CALLOUT("danger", "<strong>不要在面试里写一行流。</strong>"
                          "<code>return max((a[j]-a[i] for i in range(n) for j in range(i+1,n)), default=0)</code> 这种代码，"
                          "在评分表上「代码质量」不会加分，而「沟通」会扣分——因为面试官需要花 10 秒解析它，"
                          "而这 10 秒里他在想的是「他是不是在炫技」。<em>面试代码的目标函数是「让一个陌生人在 3 秒内读懂」，"
                          "不是「让行数最少」。15–40 行、有意义的变量名、必要时一行注释说明循环不变量——这才是满分形态。</em>"),
    ])),

    # ============================================================== 7
    ("frontier", "研究前沿与开放问题", "".join([
        P("最后放一组更长期的问题。它们不会出现在你的一面里，但会影响你怎么看待「刷题」这件事——"
          "以及三年后这个环节会变成什么样。"),
        UL([
            "<strong>coding 面试的预测效度到底有多高？</strong>公开研究极少，各家的内部数据也不外流。"
            "已知的是它对「代码正确性」有中等相关，对「长期产出」相关很弱。"
            "<em>这正是评分表把 35% 权重给沟通与测试的原因——那两栏被认为更能预测协作产出。"
            "但这个假设本身也缺乏公开验证。</em>",
            "<strong>LLM 让「能否解出题目」这个信号迅速贬值。</strong>当模型能秒解绝大多数 LeetCode medium，"
            "面试的重心必然从「解出来」移向「解释、调试、批判」。"
            "已经出现的新形态包括：给一段有 bug 的代码让你定位、给一个 LLM 生成的解法让你 review 并指出复杂度错误、"
            "以及要求你在受限环境下证明自己的解正确。<em>本课的「暴力解与最优解对拍」正是对这个趋势的直接准备——"
            "它训练的是「验证」而不是「产出」。</em>",
            "<strong>ML 岗特有的题型正在分化。</strong>越来越多的团队用<em>与业务同构</em>的题替代通用算法题："
            "手撕 IoU/NMS（见 C61-05）、实现蓄水池采样、写一个分层抽样器、实现一个滑动窗口的指标聚合器。"
            "<em>这类题的好处是能同时考算法与领域理解，坏处是可比性差、容易出成「只有内部人才知道」的题。</em>",
            "<strong>「允许查文档 / 允许用 AI」的面试怎么评分？</strong>一部分公司已经允许开着搜索引擎面试，"
            "评分重心转向提示词质量、对返回结果的批判、以及集成速度。"
            "<em>目前还没有成熟的 rubric，各家在摸索。可以预期：验证能力（写测试、造反例、对拍）的权重会继续上升。</em>",
            "<strong>算法复杂度的「实际常数」缺少可教材料。</strong>面试里人人会说 $O(n\\log n)$，"
            "但很少有人能说清「Python 里 $10^6$ 次 dict 查找大概几毫秒」。"
            "<em>这个知识在真实工程里（比如判断一个后处理能不能塞进 33 ms 的帧预算，见 C53-05）比渐近复杂度有用得多，"
            "但它高度依赖语言与硬件，因而没有被写进任何教材。notebook 里我们会自己测一组。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Gayle Laakmann McDowell, <em>Cracking the Coding Interview</em>（6th ed.）"
                         "第 VII 章「Technical Questions」——本课六步协议的原型出自这里，"
                         "但本课把它按 ML/CV 岗的题型分布做了重排，并把时间预算显式化。"
                         "<strong>★</strong> Steven Skiena, <em>The Algorithm Design Manual</em>（3rd ed.）第 1–2 章与「War Stories」——"
                         "读它是为了建立「先想问题归约、再想数据结构」的顺序感，而不是为了刷题。"
                         "<strong>★</strong> Cormen et al., <em>Introduction to Algorithms</em>（CLRS，4th ed.）第 2–4 章——"
                         "只读循环不变量（loop invariant）与主定理这两部分，它们是模块 01 与模块 02 的理论底座。</p>"
                         "<p>配套材料：Google 公开的 <em>Technical Interview Guidelines</em>（讲评分维度与「hire/no-hire」的判定方式）；"
                         "Vitter, <em>Random Sampling with a Reservoir</em>（1985）——模块 05 的蓄水池采样出处，"
                         "也是本岗位数据采样工作的理论源头。相邻课程：<strong>C61 模块 05</strong>（检测专项白板题：IoU/NMS/mAP/匈牙利/Focal，"
                         "本课不重复）、<strong>C63</strong>（ML 系统设计）、<strong>C64</strong>（技术知识问答）、"
                         "<strong>C65</strong>（结构化问题求解与沟通）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（六步协议 / 时间预算 / 复杂度换算 / 五维评分表）

目标：把「面试怎么答」从一堆经验之谈，变成**几个可以运行、可以断言的小工具**。

本 notebook 你会亲手实现：
1. **环境自检** —— 确认 Python / numpy 可用（本课全程不需要 GPU、不需要联网）
2. **六步答题协议自检器** —— 给一段「你实际做了什么」的动作序列，自动指出漏了哪步、哪两步顺序反了
3. **45 分钟时间预算器** —— 按总时长自动缩放，并给出三个不可妥协的检查点
4. **复杂度速查与经验换算** —— 从 `n` 的量级反推「你被允许用什么算法」
5. **五维评分表的代码化** —— 算出「沉默的最优解」为什么输给「会说话的暴力解」
6. **一道题的六步全流程演示** —— 含「面试官会在这里追问什么」的旁注

> 心智模型：**这个环节考的不是「你会不会这道题」，是「你不会的时候是怎么工作的」。**"""),

    md("""## 0 · 环境自检

本课全程只用标准库 + numpy。没有 GPU 依赖、不联网、不下载数据。"""),

    code("""import sys, math, random, time
import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert hasattr(np, 'argsort')

# 本课会反复用到的三个标准库模块（都不算「绕过考点」的工具）
import bisect, heapq, itertools
from collections import Counter, defaultdict, deque
print('bisect / heapq / itertools / collections 就位')
print('\\n✅ 环境自检通过：本课不需要 GPU、不需要联网。')"""),

    md("""## 1 · 六步答题协议自检器

协议本身是一个有序清单。自检器要回答两件事：
**（a）你漏了哪一步？（b）哪两步的顺序反了？**

顺序违规的定义：设规范里 `a` 应在 `b` 之前，但你**首次**做 `b` 的时刻早于首次做 `a` —— 记一次违规 `(b, a)`。"""),

    code("""STEPS = [
    ('clarify',  '① 复述与澄清', '复述题目 + 问 3-5 个约束问题'),
    ('example',  '② 举例走一遍', '手造小例子并口算答案（含一个边界）'),
    ('brute',    '③ 先给暴力解', '说清做法与复杂度 —— 这是安全网'),
    ('optimize', '④ 说优化思路', '指出重复计算在哪 + 目标复杂度 + 等点头'),
    ('code',     '⑤ 写代码',     '边写边讲，先主干后边界'),
    ('test',     '⑥ 测试与复杂度', '跑用例 + 边界 + 报时间/空间复杂度'),
]
RANK = {k: i for i, (k, _, _) in enumerate(STEPS)}

def check_protocol(trace):
    \"\"\"trace: 你实际做的动作序列（step key 的列表，可重复）。
       返回 (missing, inversions)：缺失的步骤、以及顺序违规对 (先做的, 本该更早的)。\"\"\"
    missing = [k for k, _, _ in STEPS if k not in trace]
    first = {}                                   # step -> 首次出现的位置
    for pos, t in enumerate(trace):
        first.setdefault(t, pos)
    inversions = set()
    present = [k for k in RANK if k in first]
    for a in present:
        for b in present:
            # 规范里 a 在 b 之前，但实际 b 先发生 -> 违规
            if RANK[a] < RANK[b] and first[a] > first[b]:
                inversions.add((b, a))
    return missing, sorted(inversions, key=lambda p: (RANK[p[0]], RANK[p[1]]))

for k, name, what in STEPS:
    print(f'{name:<12} {what}')"""),

    code("""# —— 三种典型表现 ——
good = ['clarify', 'example', 'brute', 'optimize', 'code', 'test']
rush = ['code', 'code', 'test']                                        # 听完就写
mixed = ['clarify', 'code', 'example', 'brute', 'optimize', 'test']    # 先写了再补流程

m1, i1 = check_protocol(good)
assert m1 == [] and i1 == []

m2, i2 = check_protocol(rush)
assert set(m2) == {'clarify', 'example', 'brute', 'optimize'}, m2
assert i2 == [], '只做了 code/test 两步，这两步的相对顺序是对的'

m3, i3 = check_protocol(mixed)
assert m3 == []
assert i3 == [('code', 'example'), ('code', 'brute'), ('code', 'optimize')], i3
assert len(i3) == 3

print('good  -> 缺失', m1, '违规', i1)
print('rush  -> 缺失', m2, '  ← 丢掉澄清/举例/暴力解/优化思路四步的分')
print('mixed -> 违规', i3, '  ← 代码写在了三步之前')
print('\\n✅ 自检器就位：把模拟面试的录像回放一遍，把动作打成 trace 喂进来。')"""),

    md("""## 2 · 45 分钟时间预算器

预算表按比例缩放（30 / 45 / 60 分钟通用），最后一项 `buffer` 吸收取整误差，保证**总和严格等于总时长**。"""),

    code("""BUDGET = [('clarify', 4), ('example', 3), ('brute', 4), ('optimize', 6),
          ('code', 18), ('test', 8), ('buffer', 2)]      # 基准：45 分钟

def budget(total_min=45):
    \"\"\"按比例缩放到 total_min，最后一项吸收取整误差。\"\"\"
    base = sum(m for _, m in BUDGET)
    out, acc = [], 0
    for name, m in BUDGET[:-1]:
        v = int(round(total_min * m / base))
        out.append((name, v)); acc += v
    out.append((BUDGET[-1][0], total_min - acc))
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
assert dict(budget(45))['code'] == 18
assert c45['brute'] == 11 and c45['optimize'] == 17 and c45['test'] == 43
print('\\n三个不可妥协的检查点（45 分钟制）：')
print(f\"  第 {c45['brute']:>2} 分钟 —— 必须已说出暴力解与复杂度\")
print(f\"  第 {c45['optimize']:>2} 分钟 —— 必须开始写代码（无论写的是哪个解）\")
print(f\"  第 {c45['code'] + 2:>2} 分钟 —— 必须停止写新代码，转入测试\")
print('\\n✅ 预算器就位。')"""),

    md("""## 3 · 复杂度速查：从 n 的量级反推可用算法

依据：一台现代机器每秒可做 $10^8$ 量级基本操作（C/C++），**Python 因解释开销只有 $10^6$–$10^7$**。
下面统一用 `ops = 1e7` 作为 Python 的预算。"""),

    code("""INF = float('inf')

def _fact(n):
    return math.factorial(int(n)) if n <= 20 else INF

def _exp2(n):
    return 2.0 ** n if n <= 1024 else INF

WORK = {                                        # 复杂度名 -> 工作量估计函数
    'log n':   lambda n: math.log2(max(n, 2)),
    'n':       lambda n: float(n),
    'n log n': lambda n: n * math.log2(max(n, 2)),
    'n^2':     lambda n: float(n) ** 2,
    'n^3':     lambda n: float(n) ** 3,
    '2^n':     _exp2,
    'n!':      _fact,
}
ORDER = ['log n', 'n', 'n log n', 'n^2', 'n^3', '2^n', 'n!']   # 由便宜到昂贵

def feasible(n, kind, ops=1e7):
    return WORK[kind](n) <= ops

def suggest(n, ops=1e7):
    \"\"\"返回在预算内「最昂贵仍可行」的复杂度 —— 它就是你被允许用的算法档次。\"\"\"
    ok = [k for k in ORDER if feasible(n, k, ops)]
    return ok[-1] if ok else None

assert feasible(5 * 10**5, 'n log n') and not feasible(10**6, 'n log n')   # 1e6·log2(1e6)≈2e7 > 1e7
assert feasible(10**6, 'n') and not feasible(10**6, 'n^2')
assert feasible(1000, 'n^2') and not feasible(10**4, 'n^2')
assert feasible(20, '2^n') and not feasible(25, '2^n')
assert feasible(10, 'n!') and not feasible(11, 'n!')
assert suggest(10**5) == 'n log n'
assert suggest(10**6) == 'n'                      # Python 预算下 n log n 已经超了
assert suggest(10**6, ops=1e8) == 'n log n'       # C/C++ 预算下还能跑
assert suggest(1000) == 'n^2'
assert suggest(20) == '2^n'
assert suggest(10) == 'n!'

HINT = {'n!': '全排列 / 回溯', '2^n': '状压 DP / 子集枚举', 'n^3': '三重循环 / Floyd',
        'n^2': '双重循环 / 区间 DP', 'n log n': '排序 或 二分 或 堆', 'n': '双指针 / 滑窗 / 哈希'}
print(f\"{'n':>10} | {'C/C++ (1e8)':<10} | {'Python (1e7)':<12} | 面试里该说的话\")
print('-' * 82)
for n in (10, 20, 500, 3000, 10**5, 10**6, 10**7):
    s7, s8 = suggest(n), suggest(n, ops=1e8)
    flag = '  <- 唯一有分歧的一格' if s7 != s8 else ''
    print(f'{n:>10} | {s8:<10} | {s7:<12} | 「目标 O({s8})，通常意味着 {HINT[s8]}」{flag}')"""),

    code("""# 常数不是不存在的：同为 O(n)，Python 循环与 numpy 向量化差两个数量级
N = 2_000_000
a = np.random.default_rng(0).random(N)

t0 = time.perf_counter(); s1 = float(a.sum());            t_np = time.perf_counter() - t0
t0 = time.perf_counter(); s2 = 0.0
for x in a[:200_000]:                                      # 只跑 1/10，否则太慢
    s2 += float(x)
t_py = (time.perf_counter() - t0) * 10                     # 折算到同样 N

assert abs(s1 - a.sum()) < 1e-6
print(f'numpy  求和 {N} 个数: {t_np*1000:8.2f} ms')
print(f'Python 循环（折算）  : {t_py*1000:8.2f} ms   ← 约 {t_py/max(t_np,1e-9):.0f} 倍')
print('\\n✅ 结论：渐近复杂度相同，实际耗时可以差两个数量级。')
print('   面试里说「都是 O(n) 所以一样快」会被追问；说「同为 O(n)，但 Python 循环的常数大约是')
print('   向量化的 20-100 倍，所以真要上车我会向量化」才是满分答案。')"""),

    md("""## 4 · 五维评分表：为什么「沉默的最优解」会输

权重是一个可用的近似（各家不同）。重点不是精确预测分数，而是**告诉你时间该花在哪**。"""),

    code("""RUBRIC = [
    ('correctness',   '正确性',   0.30),
    ('complexity',    '复杂度',   0.20),
    ('code_quality',  '代码质量', 0.15),
    ('communication', '沟通',     0.20),
    ('testing',       '测试意识', 0.15),
]
PASS_LINE = 3.5
assert abs(sum(w for _, _, w in RUBRIC) - 1.0) < 1e-12

def score(card):
    \"\"\"card: {维度: 1-5 分}  ->  加权总分\"\"\"
    return sum(w * card[k] for k, _, w in RUBRIC)

A = dict(correctness=5, complexity=5, code_quality=3, communication=1, testing=1)  # 沉默的最优解
B = dict(correctness=4, complexity=3, code_quality=4, communication=5, testing=5)  # 会说话的暴力解

sa, sb = score(A), score(B)
assert abs(sa - 3.30) < 1e-9, sa
assert abs(sb - 4.15) < 1e-9, sb
assert sa < PASS_LINE <= sb

print(f'A 沉默的最优解 : {sa:.2f}   ← 低于及格线 {PASS_LINE}')
print(f'B 会说话的暴力解: {sb:.2f}   ← 强通过')
print()
print(f'沟通 + 测试意识合计权重 = {0.20 + 0.15:.2f}，比正确性的 0.30 还高。')
print('这就是为什么「练边写边讲 + 主动测试」的边际收益高于多刷 50 道题。')"""),

    md("""## 5 · 一道题的六步全流程演示

题目（面试官原话，故意含糊）：**「给你一个数组，表示每天的价格。你只能买一次卖一次，求最大收益。」**

下面按六步走一遍，每步都标出**这一步的产出**与**面试官会在这里追问什么**。"""),

    code("""# ── 步骤 ① 复述与澄清 ──────────────────────────────────────────────
RESTATE = '我复述一遍：给一个长度为 n 的价格数组，选 i < j 使 prices[j]-prices[i] 最大，返回这个最大值。'
QUESTIONS = [
    ('必须先买后卖吗？',        '是 —— 所以 i 必须严格小于 j'),
    ('可以不交易吗？',          '可以 —— 那么收益为 0，而不是负数'),
    ('数组可能为空或只有 1 个元素吗？', '可能 —— 返回 0'),
    ('价格会是负数吗？',        '不会 —— 但代码不要依赖这一点'),
    ('n 的量级？',              '最多 1e5 —— 这就排除了 O(n^2)'),
]
print(RESTATE, '\\n')
for q, a in QUESTIONS:
    print(f'  Q: {q:<28} A: {a}')

n_max = 10**5
print(f'\\n>>> 由 n <= {n_max} 反推：可用的最昂贵复杂度是 O({suggest(n_max)})')
assert suggest(n_max) == 'n log n'
print('    O(n^2) = 1e10 直接出局 —— 这句话在第 1 分钟就该说出来。')
print('\\n【面试官旁注】问「可以不交易吗」的人，比不问的人少写一个 bug；')
print('              问「n 的量级」的人，直接拿到复杂度维度的第一分。')"""),

    code("""# ── 步骤 ② 举例走一遍（含边界）────────────────────────────────────
CASES = [
    ([7, 1, 5, 3, 6, 4], 5,  '正常：第 2 天买(1)第 5 天卖(6)'),
    ([7, 6, 4, 3, 1],    0,  '单调下降：一次都不交易'),
    ([],                 0,  '空数组'),
    ([5],                0,  '单元素：买了没法卖'),
    ([3, 3, 3],          0,  '全相同'),
    ([1, 2],             1,  '最短的有效交易'),
]
for arr, want, why in CASES:
    print(f'  {str(arr):<20} -> {want}   ({why})')

print('\\n【面试官旁注】第 2-5 条是「边界用例清单」的固定套路：')
print('              空 / 单元素 / 全相同 / 极端单调。四条背下来，每道题都用得上。')"""),

    code("""# ── 步骤 ③ 先给暴力解（安全网）────────────────────────────────────
def max_profit_brute(prices):
    \"\"\"枚举所有 (买, 卖) 对。时间 O(n^2)，空间 O(1)。\"\"\"
    best = 0
    for i in range(len(prices)):
        for j in range(i + 1, len(prices)):
            best = max(best, prices[j] - prices[i])
    return best

for arr, want, _ in CASES:
    assert max_profit_brute(arr) == want, arr

print('暴力解通过全部 6 个用例。口播：')
print('  「最直接的做法是枚举所有买卖对，O(n^2) 时间、O(1) 空间。')
print('   n=1e5 时是 1e10 次操作，跑不完，但它给了我们一个正确的参照。」')
print('\\n【面试官旁注】说完这句，「正确性」的下限已经从 1 分抬到 3 分了。')"""),

    code("""# ── 步骤 ④⑤ 优化思路 + 写代码 ─────────────────────────────────────
# 思路：暴力解的内层循环反复在问「i 之前的最小价格是多少」。
#       这个量可以在一次遍历里增量维护 -> 内层循环消失。

def max_profit(prices):
    \"\"\"时间 O(n)，空间 O(1)。
    循环不变量：处理完下标 i 后，
        min_price = min(prices[0..i])         # 到目前为止见过的最低买入价
        best      = max{prices[j]-prices[k] | k <= j <= i}   # 到目前为止的最优收益
    \"\"\"
    best = 0
    min_price = float('inf')                 # 空数组时保持 inf，循环不进入，返回 0
    for price in prices:
        # 先用旧的 min_price 结算「今天卖」，保证 买入日 < 卖出日
        best = max(best, price - min_price)
        min_price = min(min_price, price)    # 再更新最低买入价
    return best

for arr, want, why in CASES:
    got = max_profit(arr)
    assert got == want, (arr, got, want)
print('最优解通过全部 6 个用例。')

print('\\n【面试官旁注·高频追问】')
print('  Q: 如果把两行调换（先更新 min_price 再结算）会怎样？')
print('  A: 就允许了「同一天买入又卖出」，收益恒 >= 0 不会错，但语义变了；')
print('     若题目改成「必须持有至少一天」，这个顺序就是 bug 的来源。')
print('     —— 能主动说出「这两行的顺序编码了 i < j 这个约束」，是加分点。')"""),

    code("""# ── 步骤 ⑥ 测试与复杂度：随机对拍 + 复杂度陈述 ────────────────────
rng = random.Random(42)
for trial in range(2000):
    n = rng.randint(0, 12)
    arr = [rng.randint(0, 20) for _ in range(n)]
    assert max_profit(arr) == max_profit_brute(arr), arr      # 对拍：最优解 vs 暴力解
print('随机对拍 2000 组通过（长度 0-12，值域 0-20，含大量重复与空数组）。')

# 复杂度的经验验证：n 翻 10 倍，耗时应约翻 10 倍（线性）
def timeit(fn, arr, repeat=3):
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn(arr)
    return (time.perf_counter() - t0) / repeat

big1 = [rng.randint(0, 10**6) for _ in range(100_000)]
big2 = big1 * 10
r = timeit(max_profit, big2) / max(timeit(max_profit, big1), 1e-9)
print(f'n 从 1e5 -> 1e6，耗时比 = {r:.1f}（线性算法应在 8-13 之间）')
assert 5 < r < 25, r

print('\\n口播收尾（照抄）：')
print('  「时间 O(n)：每个元素只被访问一次；空间 O(1)：只用了两个标量。')
print('   边界：空数组时 min_price 保持 inf，循环不进入，返回 0；')
print('   单元素时进一次循环，price-inf 为 -inf，best 仍是 0。')
print('   我还用暴力解做了随机对拍，2000 组一致。」')
print('\\n✅ 六步走完。注意最后这段话同时拿到了「复杂度」「测试意识」「沟通」三栏的分。')"""),

    md("""## ✏️ 练习 1：超时报警器

实现 `budget_alarm(elapsed, done_steps, total=45)`，返回 `'ok'` / `'speed_up'` / `'fallback'`。

规则：
- `expected` = `cumulative(total)` 里**最后一个已完成步骤**的结束时刻（一步都没完成则为 0）
- `elapsed <= expected + 2` → `'ok'`
- `elapsed <= expected + 6` → `'speed_up'`
- 否则 → `'fallback'`（放弃最优解，立刻去写暴力解）

`done_steps` 是已完成步骤的 key 列表，保证是 `STEPS` 的前缀。"""),

    code("""def budget_alarm(elapsed, done_steps, total=45):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
# 45 分钟制的累计结束时刻：clarify=4 example=7 brute=11 optimize=17 code=35 test=43
assert budget_alarm(0,  []) == 'ok'
assert budget_alarm(6,  ['clarify']) == 'ok'                      # 4+2
assert budget_alarm(9,  ['clarify']) == 'speed_up'                # <= 4+6
assert budget_alarm(12, ['clarify']) == 'fallback'                # > 10
assert budget_alarm(20, ['clarify', 'example', 'brute', 'optimize']) == 'speed_up'   # 17+2 < 20 <= 17+6
assert budget_alarm(17, ['clarify', 'example', 'brute', 'optimize']) == 'ok'
assert budget_alarm(30, ['clarify', 'example', 'brute', 'optimize']) == 'fallback'
assert budget_alarm(10, ['clarify']) == 'speed_up'                # 45 分钟制：4+6=10 还在窗口内
assert budget_alarm(10, ['clarify'], total=30) == 'fallback'      # 30 分钟制 clarify 只到第 3 分钟 -> 同样 10 分钟已超
for e, d in [(0, []), (6, ['clarify']), (12, ['clarify']), (20, ['clarify', 'example', 'brute', 'optimize'])]:
    print(f'第 {e:>2} 分钟，已完成 {len(d)} 步 -> {budget_alarm(e, d)}')
print('✅ 练习 1 通过：第 17 分钟还没动键盘，报警器应该已经在叫了。')"""),

    md("""## ✏️ 练习 2：提分收益排序

实现 `rubric_gap(card)`，返回 `[(维度, 提升到 5 分的加权收益), ...]`：
- 收益 = `权重 × (5 - 当前分)`
- 按收益**降序**；收益相同时按维度名的**字典序升序**（保证结果确定）"""),

    code("""def rubric_gap(card):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
gap = rubric_gap(A)          # A = 沉默的最优解
names = [k for k, _ in gap]
vals = [v for _, v in gap]
assert names == ['communication', 'testing', 'code_quality', 'complexity', 'correctness'], names
assert np.allclose(vals, [0.80, 0.60, 0.30, 0.0, 0.0]), vals
gap_b = rubric_gap(B)
assert gap_b[0][0] == 'complexity' and abs(gap_b[0][1] - 0.40) < 1e-12, gap_b[0]
assert abs(sum(v for _, v in gap) + score(A) - 5.0) < 1e-12, '总收益 + 当前分应恰好等于满分 5'
for k, v in gap:
    print(f'  {k:<15} 提到 5 分可加 {v:.2f}')
print('\\n✅ 练习 2 通过：A 该做的不是再刷 100 道题（正确性已满分），是找个人对着讲一遍。')"""),

    md("""## ✏️ 练习 3：反解「最大可处理规模」

实现 `max_n(kind, ops=1e7)`：返回满足 `WORK[kind](n) <= ops` 的**最大整数 n**（`n >= 1`），
用二分查找，上界取 `10**9`。（`WORK` 的工作量函数对 n 单调不减，二分是合法的。）"""),

    code("""def max_n(kind, ops=1e7):
    # TODO: 二分 [1, 10**9]
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert max_n('n') == 10_000_000
assert max_n('n^2') == 3162, max_n('n^2')          # 3162^2=9,998,244 <= 1e7 < 3163^2
assert max_n('2^n') == 23, max_n('2^n')            # 2^23=8,388,608 <= 1e7 < 2^24
assert max_n('n!') == 10, max_n('n!')              # 10!=3,628,800 <= 1e7 < 11!
assert max_n('n^3') == 215, max_n('n^3')           # 215^3=9,938,375 <= 1e7 < 216^3
assert 5.2e5 < max_n('n log n') < 5.3e5, max_n('n log n')
assert max_n('n^2', ops=1e8) == 10_000
for k in ORDER:
    print(f'  O({k:<8}) 在 1e7 预算下最多处理 n = {max_n(k):,}')
print('\\n✅ 练习 3 通过：这张表反过来读，就是「看到 n 就知道该用什么算法」。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def budget_alarm(elapsed, done_steps, total=45):
    cum = dict(cumulative(total))
    expected = cum[done_steps[-1]] if done_steps else 0
    if elapsed <= expected + 2:
        return 'ok'
    if elapsed <= expected + 6:
        return 'speed_up'
    return 'fallback'"""),

    code("""# 练习 2 参考答案
def rubric_gap(card):
    out = [(k, w * (5 - card[k])) for k, _, w in RUBRIC]
    return sorted(out, key=lambda kv: (-kv[1], kv[0]))"""),

    code("""# 练习 3 参考答案
def max_n(kind, ops=1e7):
    f = WORK[kind]
    lo, hi = 1, 10 ** 9                 # 不变量：f(lo) <= ops < f(hi+1)
    if f(lo) > ops:
        return 0
    while lo < hi:
        mid = (lo + hi + 1) // 2        # 上取整，避免 lo=mid 死循环
        if f(mid) <= ops:
            lo = mid
        else:
            hi = mid - 1
    return lo"""),

    md("""---
## 🧪 真实工程胶囊：面试前 24 小时检查单 + 六步口播模板（中英对照）"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 面试前 24 小时检查单
# ══════════════════════════════════════════════════════════════════════
# □ 环境：确认协作编辑器（CoderPad / HackerRank / Google Doc）能打字、能运行
#         Google Doc 形式最坑 —— 没有语法高亮、没有自动缩进，务必提前试一次
# □ 语言：确认面试语言（Python 3）。提前写好这三个 snippet 的肌肉记忆：
#         for i, x in enumerate(a):        l, r = 0, len(a) - 1
#         d[k] = d.get(k, 0) + 1          while l < r: ...
# □ 复习：只复习「模块 01 + 02」的模板（双指针 / 滑窗 / 前缀和 / 二分三模板）
#         不要在面试前一晚学新算法 —— 边际收益为负
# □ 打印：把六步协议 + 三个时间检查点写在一张纸上，放在屏幕旁边
# □ 心态：目标不是「解出来」，是「六步都做到」。第③步做到就有及格分

# ══════════════════════════════════════════════════════════════════════
# B. 六步口播模板（中 / EN —— JD 是英文岗，两套都要能说）
# ══════════════════════════════════════════════════════════════════════
# ① 澄清 CN: 「我先复述一遍确认理解：……。我想确认三件事：输入有序吗？可以有重复吗？n 大概多大？」
#          EN: "Let me restate to make sure I got it: ... Three quick questions:
#               is the input sorted? can there be duplicates? what's the range of n?"
# ② 举例 CN: 「我拿一个小例子走一遍：输入 [..]，我算出来应该是 ..。再看一个边界：空数组返回 0。」
#          EN: "Let me walk through a small example: ... And an edge case: empty input returns 0."
# ③ 暴力 CN: 「最直接的做法是两层循环，O(n^2)。我先说清楚它，这样我们至少有一个正确的参照。」
#          EN: "The brute-force is a double loop, O(n^2). Let me state it first so we have a
#               correct baseline to compare against."
# ④ 优化 CN: 「暴力解里内层循环反复算了同一个量，这个量可以增量维护 -> 目标 O(n)。您觉得这个方向对吗？」
#          EN: "The inner loop recomputes the same quantity; I can maintain it incrementally,
#               which gets us to O(n). Does that direction sound right to you?"
# ⑤ 写码 CN: 「我先写主干，边界稍后补。这个变量记的是『到目前为止见过的最小值』。」
#          EN: "I'll write the main loop first and handle edges after.
#               This variable holds the minimum seen so far."
# ⑥ 收尾 CN: 「时间 O(n)、空间 O(1)。边界我过一遍：空 / 单元素 / 全相同。我还用暴力解对拍了 2000 组。」
#          EN: "Time O(n), space O(1). Edge cases: empty, single element, all-equal.
#               I also cross-checked against the brute force on 2000 random inputs."

# ══════════════════════════════════════════════════════════════════════
# C. 卡住时的三种脱困话术（沉默超过 30 秒是硬扣分）
# ══════════════════════════════════════════════════════════════════════
# 1) 退回上一层: 「我先退一步 —— 暴力解在这里做了什么重复计算？」
#                "Let me step back: what exactly is the brute force recomputing?"
# 2) 举具体例子: 「我拿 [1,1,2] 走一遍，看看我的假设在哪里断掉。」
#                "Let me trace [1,1,2] and see where my assumption breaks."
# 3) 明说要时间: 「我需要 30 秒理一下思路，我在权衡用哈希还是排序。」
#                "Give me 30 seconds — I'm weighing a hash map against sorting."

# ══════════════════════════════════════════════════════════════════════
# D. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 手撕 IoU / NMS / mAP / 匈牙利 / Focal Loss  -> C61 模块 05（检测专项，本课不重复）
# · 通用算法题（数组/哈希/二分/树图/DP/采样）   -> C62 模块 01-05（本课）
# · ML 系统设计（设计一个 TSR 感知系统）        -> C63
# · 技术知识快问快答（BN vs LN 之类）           -> C64
# · 估算 / 诊断 / 权衡 / 模糊需求               -> C65
'''
print(RECIPE)
for token in ['CoderPad', 'restate', 'brute-force', 'O(n^2)', '30 秒', 'C61 模块 05', 'enumerate']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：环境 / 语言肌肉记忆 / 复习范围 / 中英口播 / 脱困话术 / 课程分工')"""),

    md("""### 小结

- **这一环节考的不是「你会不会这道题」，是「你不会的时候是怎么工作的」。**
  交付物有三件：能跑的代码、诚实的复杂度陈述、一套你自己造的测试。多数人只交了第一件。
- **六步协议**（复述澄清 → 举例走一遍 → 先给暴力解 → 说优化思路 → 再写代码 → 测试与复杂度）
  的最大价值在第③步：**先给暴力解把「正确性」的下限从 1 分抬到 3 分**，而且它顺带提供了对拍基准。
- **三个不可妥协的时间检查点（45 分钟制）**：第 11 分钟说出暴力解、
  **第 17 分钟必须开始写代码**、第 37 分钟停止写新代码转入测试。
  超时时要**显式降级并说出来**——「我改为交付暴力解 + 口述复杂度」比默默写不完强得多。
- **沟通(0.20) + 测试意识(0.15) 合计 0.35，比正确性的 0.30 还高。**
  沉默的最优解 3.30 分不及格，会说话的暴力解 4.15 分强通过。
  练「边写边讲 + 主动测试」的边际收益，高于多刷 50 道题。
- **从 n 反推复杂度是免费的提示**：$n\\le10^5$ 排除 $O(n^2)$，目标就是 $O(n\\log n)$ 或 $O(n)$。
  但也要知道反向用法：$n\\le1000$ 时 $O(n^2)$ 就够，此时追最优解是过早优化。
- **Python 内置的判据只有一条**：它就是本题考点 → 不能用；它只是无关工具 → 大方用。
  拿不准就问一句「我可以用 `Counter` 吗，还是您希望我手写？」——两种情况都拿分。

下一站：**模块 01 · 数组与字符串：双指针、滑动窗口、前缀和** ——
ML/CV 岗最高频的题型，也是唯一一个「掌握模板就能覆盖三成题目」的领域。"""),
]
