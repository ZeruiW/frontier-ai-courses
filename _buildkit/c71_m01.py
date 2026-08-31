# -*- coding: utf-8 -*-
"""C71 模块 01 · prompt program 与可组合结构。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（四个部件与三个量）；"
                 "会用 <code>json</code> 与简单的类"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_prompt_program.ipynb'
                       '（Signature 作为一等对象与它的 validate / '
                       '指令的五个槽位逐个删掉并量症状 / '
                       '两级流水线的错误传播是乘法 / '
                       '三种输出格式的解析鲁棒性 / '
                       '重试的选择偏倚初探 / prompt 版本化与回归门禁）'),
    ("核心参考", "Omar Khattab et al., <em>DSPy: Compiling Declarative Language Model Calls "
                 "into Self-Improving Pipelines</em>（2023）——signature / module / compile 三层抽象 · "
                 "<em>pydantic</em> / <em>JSON Schema</em>（输出契约的事实标准）· "
                 "本课程 C03 模块 03（答案抽取与 unparseable）· "
                 "C68 模块 01（spec 是纯数据）· C34（多步编排的错误传播）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("signature", "签名先于 prompt", "".join([
        P("模块 00 把一次调用拆成了四个部件。"
          "<strong>这一节再往前一步：先定义契约，再写 prompt。</strong>"),
        ASCII("""
   Signature（契约）                        prompt（实现）

   inputs:  {feedback: str}                「把用户反馈分类。
   output:  {label: Label,                  标签只能是 bug / feature / …
             reason: str}                   输出 JSON：{"label": …, "reason": …}」
   Label:   bug|feature|billing|
            account|other                   ↑ 这一段是**可替换的**
   parse:   json → validate                   而上面那个契约不是

   关系：**一个签名可以有很多种 prompt 实现**（模块 03 的搜索空间就是它们）；
        而换 prompt 不该改签名 —— 改签名意味着下游要改。
"""),
        DUAL(
            "为什么这个顺序重要？因为<strong>签名是可以被机械检查的，而 prompt 不是</strong>。"
            "<em>「输出必须是这五个标签之一」是一个断言；"
            "「这段指令写得清楚吗」不是</em>。"
            "<strong>把契约独立出来之后，你得到了一个不依赖任何模型就能跑的测试</strong>——"
            "而这是这一层能进 CI 的前提。",
            "更实际的一点：<strong>签名决定了「解析失败」这件事是否可判定</strong>。"
            "<em>没有取值域声明时，<code>parse</code> 只能返回模型说的那个字符串，"
            "而「模型自创了一个标签」与「模型答错了」无法区分</em>。"
            "<strong>有取值域之后，前者变成 <code>None</code>，后者变成一个错标签</strong>——"
            "两个不同的失败，两套修法（模块 00 第 1 节与它的 notebook 量过：一个是 100% 解析失败，"
            "一个是准确率掉一半）。",
        ),
        H3("签名的四个字段，每一个都有具体用途"),
        TABLE(["字段", "内容", "谁用它"], [
            ["<strong>inputs</strong>", "输入字段名与类型",
             "渲染器；<em>以及组合时的类型检查（第 3 节）</em>"],
            ["<strong>output</strong>", "输出字段名",
             "解析器；<em>它必须与格式规范里的字段名一致——不一致是一个真实的 bug 源</em>"],
            ["<strong>domain</strong>（取值域）", "枚举、区间、正则或 schema",
             "<strong>解析器的合法性判定</strong>；以及模块 04 的解码约束"],
            ["<strong>invariants</strong>（不变量）", "跨字段的约束，比如「reason 非空」「置信度在 [0,1]」",
             "<em>它抓的是「格式对但内容荒谬」这一类</em>，"
             "比如 <code>confidence = 7.5</code>"],
        ]),
        CALLOUT("intuition", "一个立刻可用的检查："
                             "<strong>把签名里的取值域和指令里出现的取值域做字符串比对。</strong>"
                             "<em>不一致 → 阻断</em>。"
                             "这一项是确定性的、零误报的，"
                             "而它防住的是模块 00 第 1 节那个「解析失败率 100%」的故障。"),
    ])),

    # ============================================================== 2
    ("three-numbers", "三个量必须一起报（这一节给出为什么）", "".join([
        P("模块 00 已经引入了三个量。"
          "<strong>这一节说明为什么它们不能互相替代——"
          "以及为什么只报端到端会让优化走向错误的方向。</strong>"),
        MATH(r"\text{end-to-end} = \underbrace{P(\text{parse ok})}_{\text{契约层}} "
             r"\times \underbrace{P(\text{correct} \mid \text{parse ok})}_{\text{能力层}}"),
        DUAL(
            "<strong>这是一个乘法分解，而两个因子的改进手段完全不同。</strong>"
            "<em>第一个因子靠指令、格式规范、解码约束提高（便宜、确定、可以做到 1.0）；"
            "第二个因子靠示例选择、更强的模型、微调提高（贵、不确定、有上界）</em>。"
            "<strong>只报乘积时，你不知道该动哪一个。</strong>",
            "更糟的是：<strong>只报乘积会让某些「改进」看起来有效而实际有害</strong>。"
            "<em>例子：把取值域放宽（允许模型输出任意字符串）会让解析率变成 1.0，"
            "于是端到端上升</em>——"
            "<strong>但这只是把「解析失败」重新标记成了「答错」，"
            "而下游拿到的是一个不在枚举里的值，可能直接崩</strong>。"
            "<em>三个量一起报时，这个「改进」会立刻暴露："
            "解析率 1.0 而 acc-given-parsed 掉了。</em>",
        ),
        TABLE(["情形", "parse_rate", "acc\\|parsed", "end-to-end", "该做什么"], [
            ["<strong>契约没定清</strong>", "0.0–0.6", "可能很高", "低",
             "<strong>先修契约</strong>（指令写全取值域、规定格式）；<em>不要碰示例</em>"],
            ["<strong>能力不够</strong>", "1.0", "低", "低",
             "示例选择（模块 02）→ 自动优化（模块 03）→ 才考虑换模型"],
            ["<strong>部分解析失败</strong>", "0.6–0.95", "偏高（<em>有偏</em>）", "中",
             "<strong>最危险</strong>：被丢掉的样本不是随机的（第 5 节）"],
            ["<strong>健康</strong>", "1.0", "高", "高", "看分层指标找残余问题"],
        ]),
        P("<strong>第三行的「偏高」是一个真实的估计偏差</strong>："
          "<em>解析失败的样本往往是模型「更不确定、更想多说话」的那些，"
          "而它们也更可能答错</em>。"
          "所以在解析成功的子集上算准确率，"
          "<strong>系统性地高估了模型的能力</strong>。"
          "第 5 节会量出这个偏差，模块 04 会给出修法。"),
    ])),

    # ============================================================== 3
    ("compose", "组合：错误传播是乘法", "".join([
        P("把一个任务拆成两步（先粗分再细分）是一个很自然的想法。"
          "<strong>但它有一个不那么直观的代价。</strong>"),
        ASCII("""
   单级                        两级

   feedback ──► [5 分类] ──► label     feedback ──► [是不是技术问题?] ──┬─► [bug/feature]
                                                                       └─► [billing/account/other]

   两级的端到端准确率 = P(第一级对) × P(第二级对 | 第一级对)

   0.90 × 0.90 = 0.81   ← 两个「都挺好」的模块，合起来是 0.81
   0.95 × 0.95 = 0.90
   三级: 0.95³ = 0.857
"""),
        DUAL(
            "<strong>错误传播是乘法，所以级数是一个成本。</strong>"
            "<em>而人们拆分任务的直觉通常是「每一步更简单所以每一步更准」</em>——"
            "这没错，但要赢下来，<strong>每一步的准确率提升必须补偿掉多乘一次的损失</strong>。"
            "notebook 第 3 节在同一个任务上把单级与两级都跑一遍，"
            "<em>结果是单级更好</em>——这在小标签集上很常见。",
            "什么时候两级会赢？三种情况："
            "<strong>① 第一级近乎无误</strong>（比如靠规则而不是模型判定），"
            "于是乘法的损失接近 0；"
            "<strong>② 子任务的标签集差异很大</strong>，"
            "合成一级会让指令与示例互相干扰；"
            "<strong>③ 子任务需要不同的上下文</strong>"
            "（比如一支只需要产品文档、另一支只需要账务规则），"
            "<em>合成一级会让每次调用都带上两倍的上下文</em>。"
            "<strong>反过来说：如果三条都不成立，就不该拆。</strong>",
        ),
        H3("组合时必须显式处理的三件事"),
        OL([
            "<strong>类型检查</strong>：上一级的 <code>output</code> 必须能喂进下一级的 <code>inputs</code>。"
            "<em>这是签名的直接用途，而它可以在不调用模型的情况下检查</em>。",
            "<strong>解析失败的传播</strong>：上一级解析失败时，下一级<em>根本不该被调用</em>。"
            "<strong>否则你会把 <code>None</code> 渲染进下一级的 prompt</strong>——"
            "而那通常表现为「模型答了一个莫名其妙的东西」，很难定位。",
            "<strong>每一级的三个量都要分别记录</strong>。"
            "<em>只记端到端时，「第一级解析失败率上升」这件事在指标上表现为"
            "「整体效果下降」，而你会去优化第二级。</em>",
        ]),
        CALLOUT("warn", "一个具体的反模式："
                        "<strong>把「重试」当成一级</strong>。"
                        "<em>「解析失败就重试三次」看起来是提高鲁棒性，"
                        "但它同时改变了你的样本分布</em>——"
                        "第 5 节会量出这个偏倚，"
                        "而模块 04 会说明为什么<strong>约束优于重试</strong>。"),
    ])),

    # ============================================================== 4
    ("instruction-slots", "指令的五个槽位", "".join([
        P("指令看起来是一段自由文本，"
          "<strong>但它实际上有五个功能不同的槽位，而每个槽位缺失的症状不一样。</strong>"),
        TABLE(["槽位", "内容", "缺失的症状", "严重程度"], [
            ["<strong>① 任务</strong>", "要做什么",
             "输出跑题；<em>但通常示例能救回来</em>", "中"],
            ["<strong>② 取值域</strong>", "标签集 / 取值域 / schema",
             "<strong>模型自创值 → 解析失败率 100%</strong>", "<strong>致命</strong>"],
            ["<strong>③ 输出格式</strong>", "怎么输出、字段名",
             "部分解析失败（<em>最麻烦的一种</em>）", "<strong>高</strong>"],
            ["<strong>④ 边界与兜底</strong>", "「都不符合时输出 other」「信息不足时输出 unknown」",
             "<strong>模型被迫在不合适的选项里挑一个</strong>，"
             "<em>于是错误集中在边缘样本上</em>", "高"],
            ["<strong>⑤ 禁止项</strong>", "「不要解释」「不要输出 markdown 代码块」",
             "输出里裹了一层 ```json，解析器要么处理它要么失败", "中"],
        ]),
        DUAL(
            "<strong>第 4 个槽位最容易被忘，而它的症状最容易被误读。</strong>"
            "<em>没有兜底选项时，模型必须在给定的类里挑一个</em>，"
            "于是「其实不属于任何一类」的样本会被随机分配。"
            "<strong>在指标上这表现为「某几个类的精确率低」，"
            "而实际原因是缺一个 <code>other</code>。</strong>",
            "第 5 个槽位（禁止项）值得单独一提："
            "<strong>它是唯一一个「不加也能工作，但加了能显著降低解析器复杂度」的槽位。</strong>"
            "<em>每一条禁止项都对应解析器里的一段清洗代码</em>——"
            "去代码块围栏、去前后解释、去 markdown 加粗。"
            "<strong>把它写进指令，等于把清洗成本从每次调用移到一次性的一句话上。</strong>"
            "<em>但也不要指望它 100% 生效——解析器仍然要能处理没生效的情况。</em>",
        ),
        P("<strong>notebook 第 2 节把五个槽位逐个删掉</strong>，"
          "量出每一个的边际贡献。"
          "<em>结论是取值域与格式两项占了绝大部分</em>，"
          "而它们恰好是最便宜、最确定的两项——"
          "<strong>这也解释了为什么「先修契约」是正确的顺序。</strong>"),
    ])),

    # ============================================================== 5
    ("format-choice", "输出格式三选：不是越结构化越好", "".join([
        TABLE(["格式", "例子", "解析鲁棒性", "成本", "什么时候用"], [
            ["<strong>裸值</strong>", "<code>bug</code>",
             "<em>只要模型多说一个字就失败</em>", "最低（几个 token）",
             "<strong>配上解码约束时最优</strong>（模块 04）；不配约束时最脆"],
            ["<strong>JSON 单字段</strong>", "<code>{\"label\": \"bug\"}</code>",
             "较好；<em>能容忍前后有解释（可以正则抽取）</em>", "低",
             "<strong>默认选择</strong>"],
            ["<strong>JSON 多字段（带理由）</strong>",
             "<code>{\"reason\": \"…\", \"label\": \"bug\"}</code>",
             "好；<em>而且字段顺序会影响质量</em>",
             "高（理由的 token 数远超标签）",
             "需要可解释性、或需要理由参与后续判断时"],
        ]),
        DUAL(
            "<strong>「带理由的 JSON」有一个容易被忽略的设计点：字段顺序。</strong>"
            "<em>把 <code>reason</code> 放在 <code>label</code> 之前，"
            "模型在生成标签时已经写过理由</em>；"
            "<strong>反过来则理由是对已给答案的事后合理化</strong>。"
            "<em>这两者在质量上通常不同，而它是一个纯粹的格式设计选择。</em>"
            "notebook 不模拟这个效应（它需要真实模型的自回归性质），"
            "<strong>但工程上必须知道「字段顺序是一个可调项」，并把它写进指纹。</strong>",
            "另一个反直觉的点：<strong>更结构化不一定更鲁棒</strong>。"
            "<em>嵌套很深的 schema 会引入更多可能出错的地方"
            "（少一个括号、字段名拼错、类型不对）</em>，"
            "而<strong>解析失败是全或无的</strong>。"
            "<em>所以 schema 的复杂度应当由下游<strong>真正需要</strong>的字段决定，"
            "而不是「顺便多要几个」</em>。"
            "<strong>每多一个字段，就多一个解析失败的入口。</strong>",
        ),
        CALLOUT("intuition", "一条实用的规则："
                             "<strong>先用 JSON 单字段跑通并把解析率做到 1.0，"
                             "再考虑加字段。</strong>"
                             "<em>而每加一个字段都要重新量解析率</em>——"
                             "它不会自动保持 1.0。"),
    ])),

    # ============================================================== 6
    ("retry-bias", "重试的选择偏倚（初探）", "".join([
        P("解析失败时重试，是几乎所有系统的默认做法。"
          "<strong>它有效，但它会改变你测到的分布。</strong>"),
        DUAL(
            "机制：<strong>「重试直到解析成功」会系统性地丢掉那些「模型倾向于不按格式回答」的样本</strong>。"
            "<em>而这些样本通常是模型更不确定的那些，也就是更可能答错的那些。</em>"
            "<strong>于是在「解析成功」的样本上算准确率，会高估真实能力。</strong>",
            "形式化：设样本的难度是 $d$，"
            "解析成功概率 $P(\\text{parse} \\mid d)$ 随 $d$ 递减，"
            "正确概率 $P(\\text{correct} \\mid d)$ 也随 $d$ 递减。"
            "<strong>则条件期望 $E[\\text{correct} \\mid \\text{parse ok}] > E[\\text{correct}]$</strong>——"
            "<em>因为条件化在一个与正确性正相关的事件上</em>。"
            "notebook 第 5 节把这个偏差量出来："
            "<strong>只在解析成功的样本上报分，比真实端到端高出可观的一截。</strong>",
        ),
        H3("三条纪律"),
        OL([
            "<strong>重试的次数与最终是否成功必须被记录</strong>，"
            "<em>而且报告里要写明「N 个样本经过重试」</em>。"
            "这与 C68 模块 02 的「失败分类必须报告比例」是同一条。",
            "<strong>报分的分母必须是全部样本，解析失败记为错</strong>。"
            "<em>「在解析成功的样本上准确率 92%」这句话可以说，"
            "但不能单独说</em>——它必须与解析率一起出现。",
            "<strong>重试的触发条件只能是「解析失败」，不能是「结果看起来不对」</strong>。"
            "<em>后者是在用真值调参</em>——"
            "与 C68 模块 02 的「重试只能看异常类型，不能看判分结果」完全同构。",
        ]),
        P("<strong>而根本的修法是模块 04 的解码约束</strong>："
          "<em>让不合法的输出在生成时就不可能产生</em>，"
          "于是解析率恒为 1.0，重试与它带来的偏倚一起消失。"),
    ])),

    # ============================================================== 7
    ("versioning", "变更即发布", "".join([
        P("prompt 是<strong>唯一一处「改一个字就直接改变生产行为、"
          "却通常不进 code review、不进 CI、不进版本记录」的地方</strong>。"),
        ASCII("""
   一个最小可用的 prompt 版本化

   prompts/
     classify_feedback/
       v3/
         signature.json     ← 契约（inputs/output/domain/invariants）
         instruction.txt    ← 五个槽位
         demos.jsonl        ← **有序**，顺序是内容的一部分
         format.json        ← 输出格式规范
         decoding.json      ← 解码约束（模块 04）
         CHANGELOG.md       ← 为什么改，量到的变化是多少
       v4/ ...
     ACTIVE -> v3           ← 一个指针（与 C70 模块 05 的索引切换同构）

   指纹 = sha256(signature + instruction + demos(有序) + format + decoding
                 + model_id + temperature)
"""),
        DUAL(
            "<strong>把 demos 存成文件而不是代码里的列表，是这套结构里最有价值的一步。</strong>"
            "<em>它让「示例集合与顺序」变成可 diff、可 review、可回滚的数据</em>，"
            "而不是散落在代码里的字符串。"
            "<strong>而模块 03 的自动优化产出的正是这个文件</strong>——"
            "于是「人手改」与「自动搜」产出同一种资产。",
            "回归门禁按 C68 模块 04 分级："
            "<strong>确定性阻断</strong>（签名里的取值域与指令里的不一致；"
            "格式规范的字段名与解析器不一致；指纹变了但 CHANGELOG 没动），"
            "<strong>统计阻断</strong>（分层准确率相对基线下降超过按方差推出的阈值），"
            "<strong>报警</strong>（预测标签分布的 PSI —— 它抓的是顺序偏置与示例漂移）。"
            "<em>把统计项设成阻断是「门禁被关掉」这一结局的起点。</em>",
        ),
        CALLOUT("intuition", "最后一条确定性检查值得单独说："
                             "<strong>「指纹变了但 CHANGELOG 没动」是一个纯粹的算术检查</strong>，"
                             "零误报，而它防住的是本模块最想防的那件事——"
                             "<em>一次没人知道发生过的 prompt 变更</em>。"),
    ])),

    # ============================================================== 8
    ("antipatterns", "五个反模式", "".join([
        TABLE(["反模式", "为什么有人这么做", "后果"], [
            ["<strong>只报端到端一个数</strong>", "「一个数好比较」",
             "格式问题与能力问题混在一起；<em>放宽取值域这种有害改动看起来是改进</em>（第 2 节）"],
            ["<strong>示例硬编码在代码里</strong>", "「就几个例子」",
             "顺序不进版本、不进 diff、不进指纹；"
             "<strong>而顺序有真实影响</strong>（模块 00 的 notebook 量过）"],
            ["<strong>指令里不写取值域</strong>", "「示例里已经有了」",
             "<strong>解析失败率 100%</strong>——示例不能替代取值域声明（第 4 节）"],
            ["<strong>为了「更结构化」加字段</strong>", "「以后可能有用」",
             "每多一个字段就多一个解析失败入口，而解析失败是全或无的（第 5 节）"],
            ["<strong>拆成多级流水线</strong>", "「每一步更简单」",
             "<em>错误传播是乘法</em>；两个 0.9 合起来是 0.81（第 3 节）。"
             "<strong>拆分要满足三个条件之一，否则不该拆</strong>"],
        ]),
        P("<strong>这五条有一个共同点：它们都让「哪一层出了问题」变得不可判定。</strong>"
          "<em>而本模块的全部内容就是把这件事变回可判定的</em>——"
          "签名给出契约、三个量给出分层、组合显式化错误传播、"
          "版本化让每次变更留下痕迹。"),
    ])),

    # ============================================================== 9
    ("checklist", "一个 prompt program 的最小工程清单", "".join([
        P("把前八节压成一张可勾选的清单。"
          "<strong>它的顺序就是投入的顺序。</strong>"),
        OL([
            "<strong>写签名，不写 prompt</strong>——"
            "输入字段、输出字段、取值域、不变量。"
            "<em>这一步不需要任何模型，而它产出的三个检查可以立刻进 CI。</em>",
            "<strong>把解析器与格式规范一起写</strong>，并让它们同源生成。"
            "<em>手写 schema 给模型、手写解析器读结果，两者必然漂移。</em>",
            "<strong>指令按五个槽位写全</strong>，"
            "尤其是取值域（缺了就归零）与边界兜底（缺了会让错误集中在边缘样本上）。",
            "<strong>三个量分别打点</strong>：解析率 / 给定解析的正确率 / 端到端。"
            "<em>只报第三个时，第一个的问题会被误读成模型能力问题。</em>",
            "<strong>示例存成有序文件</strong>（不是代码里的列表），"
            "并进指纹。<em>顺序是内容的一部分。</em>",
            "<strong>加一个 <code>ACTIVE</code> 指针</strong>与 CHANGELOG，"
            "并在 CI 里跑 <code>audit</code>。"
            "<em>没有这一步，「改一个字」就是一次没人知道的发布。</em>",
        ]),
        DUAL(
            "<strong>这张清单里没有一项是「把 prompt 写得更好」。</strong>"
            "<em>全部六项都是结构性的：契约、解析、打点、版本</em>。"
            "这不是因为措辞不重要，"
            "而是因为<strong>在结构没建起来之前，你无法判断一次措辞改动是好是坏</strong>——"
            "而那正是模块 03 要处理的问题。",
            "一个常见的反对意见是「我们的场景简单，不需要这些」。"
            "<em>判据很具体：如果你能回答「上一次改 prompt 是什么时候、改了什么、"
            "效果变化多少」这三个问题，那确实不需要</em>。"
            "<strong>而如果三个都答不上来，那么这套结构的成本"
            "（大约几百行代码与一次目录重构）"
            "远低于「某天发现效果掉了但不知道是什么时候开始的」的代价。</strong>",
        ),
    ])),

    # ============================================================== 10
    ("dspy-map", "与 DSPy 的概念对应", "".join([
        P("本课从零实现这一层，但落地时大概率会用现成框架。"
          "<strong>这一节把概念对齐，方便两边互译。</strong>"),
        TABLE(["本课的概念", "DSPy 里的对应", "说明"], [
            ["<strong>Signature</strong>（本模块第 1 节）",
             "<code>dspy.Signature</code>",
             "DSPy 用类的 docstring 当指令、字段注解当取值域；"
             "<em>本课把它们拆开是为了让「取值域是否在指令里出现」可以被单独检查</em>"],
            ["<strong>PromptProgram</strong>（渲染 + 解析）",
             "<code>dspy.Predict</code> / <code>dspy.Module</code>",
             "DSPy 的 Module 可以组合，对应本模块第 3 节的 Pipeline"],
            ["<strong>三个量</strong>",
             "需要自己在 <code>metric</code> 里实现",
             "<strong>框架默认只给一个分数</strong>；"
             "<em>解析率与「给定解析的正确率」要自己打点</em>"],
            ["<strong>示例集合与顺序</strong>",
             "<code>compile()</code> 产出的 <code>demos</code>",
             "<em>它是有序列表</em>——所以第 7 节「顺序进指纹」这条同样适用"],
            ["<strong>bundle 与指纹</strong>",
             "<code>save()</code> / <code>load()</code> 的 JSON",
             "<strong>框架不会替你算指纹或检查 CHANGELOG</strong>——这一层要自己加"],
            ["<strong>ACTIVE 指针与回滚</strong>", "没有对应物",
             "<em>这是纯运维层，属于模块 05</em>"],
        ]),
        CALLOUT("intuition", "两句话总结这张表："
                             "<strong>框架帮你做「渲染 + 优化」，"
                             "不帮你做「契约检查 + 分层打点 + 版本运维」。</strong>"
                             "<em>而后三件事恰好是本课模块 01 的全部内容</em>——"
                             "所以用不用框架，这一层都得自己建。"),
    ])),

    # ============================================================== 11
    ("summary-discipline", "三条纪律的完整形式", "".join([
        P("模块 00 给出了三条贯穿全课的纪律。"
          "<strong>本模块把第一条与第三条补完了，这里写出它们的完整形式。</strong>"),
        OL([
            "<strong>格式合规与任务正确必须分开计。</strong>"
            "完整形式：<em>报三个量（解析率 / 给定解析的正确率 / 端到端），"
            "而且「解析成功的样本上准确率 X%」这句话不能单独出现</em>——"
            "它必须与解析率一起出现，"
            "<strong>因为解析成功与答对正相关，条件化在它上面会高估（第 5 节）</strong>。",
            "<strong>任何 prompt 改动都要在留出集上复核。</strong>"
            "<em>这一条在模块 03 展开</em>，但本模块已经给出了它的前提："
            "<strong>没有分层指标时，「复核」只能看一个总分，"
            "而总分会掩盖某一层的塌陷。</strong>",
            "<strong>prompt 的每一个组成部分都要进指纹。</strong>"
            "完整形式：<em>签名、指令、示例集合<strong>与顺序</strong>、"
            "格式规范、解码约束、模型 ID、温度</em>；"
            "<strong>而 CHANGELOG 不进指纹</strong>——"
            "正因为它不进，「指纹变了但 CHANGELOG 没动」才成为一个可检查的矛盾。",
        ]),
        CALLOUT("intuition", "三条纪律有一个共同的形状："
                             "<strong>它们都把一个「靠人记得」的要求，"
                             "变成了一个机器可以判定的条件。</strong>"
                             "<em>而这正是「把 prompt 当程序」这句话的实际含义</em>——"
                             "不是让 prompt 看起来像代码，"
                             "而是让它享有代码已有的那些保障：类型检查、测试、版本、评审。"),
    ])),
]

NB = [
    md("""# 01 · prompt program 与可组合结构（签名 / 三个量 / 组合 / 槽位 / 格式 / 重试 / 版本化）

目标：把 prompt 变成一个**有契约、可分层测量、可组合、可版本化**的对象。

本 notebook 你会亲手实现：
1. **Signature 作为一等对象** —— 含 `validate`，不调用任何模型就能测
2. **指令的五个槽位** —— 逐个删掉，量出每一个的边际贡献
3. **两级流水线的错误传播是乘法** —— 并看到单级在这个任务上更好
4. **三种输出格式的解析鲁棒性** —— 以及「每加一个字段就多一个失败入口」
5. **重试的选择偏倚** —— 只在解析成功的样本上报分会高估多少
6. **prompt 版本化与回归门禁** —— 含「指纹变了但 CHANGELOG 没动」这条零误报检查

> 心智模型：**签名先于 prompt。契约可以被机械检查，prompt 不能。**"""),

    md("""## 0 · 环境（沿用模块 00 的模拟器与数据）"""),

    code("""import os, re, json, math, hashlib, itertools
from collections import Counter, defaultdict

import numpy as np

DIM = 2048
LABELS = ['bug', 'feature', 'billing', 'account', 'other']
UNPARSEABLE = 'UNPARSEABLE'

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

POOL = [
    ('登录后一直转圈，点不动', 'bug'), ('保存文件时报错 500', 'bug'),
    ('页面加载不出来', 'bug'), ('导出 CSV 会丢最后一行', 'bug'),
    ('希望支持批量导出', 'feature'), ('能不能加暗色主题', 'feature'),
    ('想要一个搜索框', 'feature'), ('建议增加导入模板', 'feature'),
    ('这个月扣了两次钱', 'billing'), ('发票开错了公司名', 'billing'),
    ('为什么涨价了', 'billing'), ('想申请退款', 'billing'),
    ('忘记密码收不到邮件', 'account'), ('想改绑定手机号', 'account'),
    ('账号被锁了', 'account'), ('想注销账号', 'account'),
    ('你们客服态度不错', 'other'), ('随便看看', 'other'),
    ('没什么事', 'other'), ('祝好', 'other'),
]
TEST = [
    ('打开报表就崩溃', 'bug'), ('保存草稿会丢内容', 'bug'),
    ('希望能加个批量删除', 'feature'), ('想要导出 PDF 的功能', 'feature'),
    ('这个月账单不对', 'billing'), ('发票上的税号不对', 'billing'),
    ('登录不上，密码重置也收不到', 'account'), ('手机号换了要怎么改', 'account'),
    ('感谢你们的帮助', 'other'), ('没别的了', 'other'),
]

def toy_lm(instruction, demos, x, recency=0.35, prior='other', allowed=None):
    allowed = LABELS if allowed is None else allowed
    declared = [l for l in allowed if l in instruction]
    if not declared:
        return UNPARSEABLE
    if not demos:
        return prior
    E = np.stack([embed(t) for t, _ in demos])
    s = E @ embed(x)
    n = len(demos)
    s = s + np.array([recency * (i / (n - 1) if n > 1 else 1.0) for i in range(n)])
    label = demos[int(np.argmax(s))][1]
    return label if label in declared else prior

print('模拟器与数据就位：', len(POOL), '示例池 /', len(TEST), '测试')"""),

    md("""## 1 · Signature 作为一等对象

关键：`validate` **不调用任何模型**。它是这一层唯一能进 CI 的确定性测试。"""),

    code("""class Signature:
    def __init__(self, inputs, output, domain, invariants=()):
        self.inputs = list(inputs)          # [(name, type)]
        self.output = output                # 字段名
        self.domain = domain                # 枚举 list / ('range', lo, hi) / ('regex', pat)
        self.invariants = list(invariants)  # [(名字, 谓词)]

    # ---- 不需要模型的检查 ----
    def domain_terms(self):
        return list(self.domain) if isinstance(self.domain, list) else []

    def check_instruction(self, instruction):
        \"\"\"取值域必须在指令里出现。确定性、零误报，可以直接阻断。\"\"\"
        missing = [t for t in self.domain_terms() if t not in instruction]
        return missing

    def check_format(self, format_spec):
        \"\"\"格式规范里的字段名必须与签名的 output 一致。\"\"\"
        if format_spec is None:
            return ['未规定输出格式']
        return [] if self.output in format_spec else [f'格式规范里没有字段 {self.output}']

    def validate(self, value):
        \"\"\"返回 (是否合法, 原因)。\"\"\"
        if value is None:
            return False, 'parse_failed'
        if isinstance(self.domain, list):
            if value not in self.domain:
                return False, 'out_of_domain'
        elif self.domain[0] == 'range':
            if not (isinstance(value, (int, float)) and self.domain[1] <= value <= self.domain[2]):
                return False, 'out_of_range'
        elif self.domain[0] == 'regex':
            if not re.fullmatch(self.domain[1], str(value)):
                return False, 'regex_mismatch'
        for name, pred in self.invariants:
            if not pred(value):
                return False, f'invariant:{name}'
        return True, 'ok'

SIG = Signature(inputs=[('feedback', str)], output='label', domain=LABELS)

INSTR_FULL = ('把用户反馈分类为 bug / feature / billing / account / other 之一，'
              '只输出标签。都不符合时输出 other。不要解释。')
INSTR_NO_DOMAIN = '请把用户反馈分类，只输出标签。'
FMT = 'json {"label": "<标签>"}'

print('取值域检查（完整指令）:', SIG.check_instruction(INSTR_FULL))
print('取值域检查（缺取值域）:', SIG.check_instruction(INSTR_NO_DOMAIN))
print('格式检查:', SIG.check_format(FMT), SIG.check_format('json {"category": "..."}'))
print('validate:', SIG.validate('bug'), SIG.validate('BUG'), SIG.validate(None))

assert SIG.check_instruction(INSTR_FULL) == [], '完整指令应当通过'
assert len(SIG.check_instruction(INSTR_NO_DOMAIN)) == len(LABELS)
assert SIG.check_format('json {"category": "..."}'), '字段名不一致必须被抓到'
assert SIG.validate('bug')[0] and not SIG.validate('BUG')[0]
assert SIG.validate(None) == (False, 'parse_failed')
print('\\n✅ 三个检查全部不需要调用模型——这是这一层能进 CI 的前提。')
print('   注意 validate 区分了 parse_failed 与 out_of_domain：')
print('   前者是「没解析出东西」，后者是「解析出来了但不在枚举里」，修法不同。')"""),

    md("""## 2 · 指令的五个槽位：逐个删掉

**取值域与格式两项占了绝大部分**——而它们恰好是最便宜、最确定的两项。"""),

    code("""SLOTS = {
    'task':    '把用户反馈分类。',
    'domain':  '标签只能是 bug / feature / billing / account / other 之一。',
    'format':  '只输出标签本身。',
    'fallback': '都不符合时输出 other。',
    'forbid':  '不要解释，不要输出代码块。',
}

def build_instruction(drop=()):
    return ''.join(v for k, v in SLOTS.items() if k not in drop)

def run_program(instruction, demos, format_spec, sig=SIG, verbose_rate=0.0, seed=0):
    \"\"\"返回 (parse_rate, acc_given_parsed, end_to_end)。\"\"\"
    n_ok = n_cgo = n_c = 0
    for x, gold in TEST:
        raw = toy_lm(instruction, demos, x, allowed=sig.domain)
        # 「禁止项」缺失时，模型有一定概率裹一层代码块 —— 解析器要能处理
        if 'forbid' not in instruction and verbose_rate > 0:
            h = int(hashlib.md5((x + str(seed)).encode()).hexdigest(), 16)
            if raw != UNPARSEABLE and (h % 100) / 100 < verbose_rate:
                raw = f'```json\\n{{"label": "{raw}"}}\\n```'
        parsed = parse_output(raw, format_spec, sig)
        ok, _ = sig.validate(parsed)
        if ok:
            n_ok += 1
            n_cgo += (parsed == gold)
        n_c += (parsed == gold)
    n = len(TEST)
    return dict(parse_rate=n_ok / n,
                acc_given_parsed=(n_cgo / n_ok) if n_ok else float('nan'),
                end_to_end=n_c / n)

def parse_output(raw, format_spec, sig):
    if raw == UNPARSEABLE:
        return None
    if format_spec is None:
        return raw if raw in sig.domain_terms() else None
    body = raw.strip()
    body = re.sub(r'^```[a-z]*\\s*|\\s*```$', '', body)      # 清洗代码块围栏
    if body.startswith('{'):
        try:
            return json.loads(body).get(sig.output)
        except json.JSONDecodeError:
            return None
    return body if body in sig.domain_terms() else None

base = run_program(build_instruction(), POOL, FMT)
print(f"完整指令: parse {base['parse_rate']:.0%} | "
      f"acc|parsed {base['acc_given_parsed']:.0%} | end2end {base['end_to_end']:.0%}")
print()
print(f"{'删掉的槽位':<12}{'parse':>8}{'acc|parsed':>12}{'end2end':>10}{'边际贡献':>10}")
contrib = {}
for slot in SLOTS:
    r = run_program(build_instruction(drop=(slot,)), POOL, FMT)
    contrib[slot] = base['end_to_end'] - r['end_to_end']
    a = r['acc_given_parsed']
    print(f"{slot:<12}{r['parse_rate']:>8.0%}"
          f"{('nan' if a != a else f'{a:.0%}'):>12}{r['end_to_end']:>10.0%}"
          f"{contrib[slot]:>10.0%}")

# 单独删 domain 之后端到端不是 0 —— 为什么？
r_no_domain = run_program(build_instruction(drop=('domain',)), POOL, FMT)
r_no_both = run_program(build_instruction(drop=('domain', 'fallback')), POOL, FMT)
print()
print(f"只删 domain        : end2end {r_no_domain['end_to_end']:.0%}")
print(f"删 domain + fallback: end2end {r_no_both['end_to_end']:.0%}")
print(f"剩下的指令: 「{build_instruction(drop=('domain', 'fallback'))}」")

assert contrib['domain'] >= max(contrib.values()), '取值域是最重要的槽位'
assert 0.0 < r_no_domain['end_to_end'] < base['end_to_end'], \\
    '只删 domain 时端到端下降但**不是 0**'
assert r_no_both['end_to_end'] == 0.0, '同时删掉两个才归零'
print()
print('✅ 取值域是最重要的槽位，但这里出现了一个更有意思的现象：')
print(f"   **只删 domain 时端到端是 {r_no_domain['end_to_end']:.0%} 而不是 0**。")
print('   原因：fallback 槽位那句「都不符合时输出 other」里出现了 other 这个标签——')
print('   它**意外地声明了取值域的一部分**，于是模型至少知道有 other 这个选项。')
print(f"   同时删掉 domain 与 fallback，端到端才归零（{r_no_both['end_to_end']:.0%}）。")
print()
print('   这不是模拟器的瑕疵，是一个真实且重要的性质：**指令的槽位不是独立的**。')
print('   两个推论：')
print('   ① 消融的边际贡献**不可加**——五项之和不等于「全删」的损失（C69-05 的二阶交互）；')
print('   ② 「取值域写全了吗」这个检查不能靠人读指令判断，')
print('      要靠第 1 节那个机械的 check_instruction（把每一项逐个字符串匹配）。')
print()
print('   也注意 format / fallback / forbid 在这个模拟器上贡献是 0：')
print('   模拟器不建模「被迫在不合适的类里挑一个」与「裹代码块」这两个真实行为。')
print('   下一节把 forbid 的效应显式注入进来。')"""),

    code("""# --- 显式注入「缺禁止项 → 裹代码块」的效应 ---
print(f"{'配置':<28}{'parse':>8}{'end2end':>10}")
for label, instr, vr in [
        ('完整指令（有禁止项）', build_instruction(), 0.4),
        ('缺禁止项 + 解析器会清洗围栏', build_instruction(drop=('forbid',)), 0.4),
]:
    r = run_program(instr, POOL, FMT, verbose_rate=vr)
    print(f"{label:<28}{r['parse_rate']:>8.0%}{r['end_to_end']:>10.0%}")

# 如果解析器**不**清洗围栏会怎样
def parse_strict(raw, format_spec, sig):
    if raw == UNPARSEABLE:
        return None
    if raw.startswith('{'):
        try:
            return json.loads(raw).get(sig.output)
        except json.JSONDecodeError:
            return None
    return raw if raw in sig.domain_terms() else None

def run_strict(instruction, verbose_rate=0.4, seed=0):
    n_ok = 0
    for x, gold in TEST:
        raw = toy_lm(instruction, POOL, x, allowed=SIG.domain)
        h = int(hashlib.md5((x + str(seed)).encode()).hexdigest(), 16)
        if raw != UNPARSEABLE and (h % 100) / 100 < verbose_rate:
            raw = f'```json\\n{{"label": "{raw}"}}\\n```'
        n_ok += SIG.validate(parse_strict(raw, FMT, SIG))[0]
    return n_ok / len(TEST)

pr_strict = run_strict(build_instruction(drop=('forbid',)))
print(f'\\n解析器不清洗围栏时的解析成功率: {pr_strict:.0%}')
assert pr_strict < 1.0, '不清洗围栏时会部分解析失败'
print('✅ 禁止项与解析器是**互补**的，不是二选一：')
print('   写进指令 → 把清洗成本从每次调用移到一次性的一句话；')
print('   解析器仍然要能处理没生效的情况——因为指令不保证 100% 被遵守。')
print(f'   两者都不做时，解析成功率是 {pr_strict:.0%}，而这是「部分失败」——最麻烦的一种。')"""),

    md("""## 3 · 组合：错误传播是乘法

同一个任务，单级 5 分类 vs 两级（先判是不是技术问题，再细分）。"""),

    code("""TECH = {'bug', 'feature'}
NONTECH = {'billing', 'account', 'other'}

SIG_STAGE1 = Signature([('feedback', str)], 'kind', ['tech', 'nontech'])
SIG_TECH = Signature([('feedback', str)], 'label', sorted(TECH))
SIG_NONTECH = Signature([('feedback', str)], 'label', sorted(NONTECH))

INSTR_S1 = '判断这条用户反馈是 tech 还是 nontech，只输出其中一个。'
INSTR_TECH = '把这条技术反馈分类为 bug / feature 之一，只输出标签。'
INSTR_NONTECH = '把这条反馈分类为 account / billing / other 之一，只输出标签。'

def demos_for(sig, mapper=None):
    out = []
    for x, y in POOL:
        v = mapper(y) if mapper else y
        if v in sig.domain:
            out.append((x, v))
    return out

D_S1 = demos_for(SIG_STAGE1, lambda y: 'tech' if y in TECH else 'nontech')
D_TECH = demos_for(SIG_TECH)
D_NONTECH = demos_for(SIG_NONTECH)

def call(sig, instruction, demos, x):
    raw = toy_lm(instruction, demos, x, allowed=sig.domain)
    parsed = parse_output(raw, f'json {{"{sig.output}": "<v>"}}', sig)
    ok, _ = sig.validate(parsed)
    return parsed if ok else None

# --- 单级 ---
single_correct = 0
for x, gold in TEST:
    single_correct += (call(SIG, build_instruction(), POOL, x) == gold)
acc_single = single_correct / len(TEST)

# --- 两级 ---
s1_correct = s2_correct_given_s1 = both = n_s1_ok = 0
for x, gold in TEST:
    gold_kind = 'tech' if gold in TECH else 'nontech'
    kind = call(SIG_STAGE1, INSTR_S1, D_S1, x)
    if kind is None:
        continue                                    # 上一级解析失败 → 下一级不该被调用
    n_s1_ok += 1
    s1_correct += (kind == gold_kind)
    if kind != gold_kind:
        continue
    sig2, instr2, d2 = ((SIG_TECH, INSTR_TECH, D_TECH) if kind == 'tech'
                        else (SIG_NONTECH, INSTR_NONTECH, D_NONTECH))
    y = call(sig2, instr2, d2, x)
    s2_correct_given_s1 += (y == gold)
    both += (y == gold)

p1 = s1_correct / len(TEST)
p2_given = s2_correct_given_s1 / s1_correct if s1_correct else 0.0
acc_two = both / len(TEST)

print(f'单级 5 分类:            端到端 {acc_single:.0%}')
print(f'两级: P(第一级对) = {p1:.0%}, P(第二级对|第一级对) = {p2_given:.0%}')
print(f'      乘积 = {p1 * p2_given:.0%}   实测端到端 = {acc_two:.0%}')

assert abs(p1 * p2_given - acc_two) < 1e-9, '端到端就是两个概率的乘积'
assert acc_single >= acc_two, '在这个小标签集上，单级不该更差'
print(f'\\n✅ 错误传播是乘法，而且是**精确的**乘法：{p1:.2f} × {p2_given:.2f} = {acc_two:.2f}。')
print(f'   在这个任务上单级 {acc_single:.0%} ≥ 两级 {acc_two:.0%}——')
print('   拆分让每一步更简单，但要赢下来，简化带来的提升必须补偿掉多乘一次的损失。')
print('   什么时候两级会赢：① 第一级近乎无误（比如靠规则）；')
print('   ② 子任务标签集差异很大，合成一级会互相干扰；③ 子任务需要不同的上下文。')
print('   **三条都不成立就不该拆。**')"""),

    code("""# --- 解析失败的传播：上一级失败时下一级不该被调用 ---
def two_stage(x, s1_instruction):
    \"\"\"返回 (label 或 None, 停在哪一级)。\"\"\"
    kind = call(SIG_STAGE1, s1_instruction, D_S1, x)
    if kind is None:
        return None, 'stage1_parse_failed'          # ← 不继续
    sig2, instr2, d2 = ((SIG_TECH, INSTR_TECH, D_TECH) if kind == 'tech'
                        else (SIG_NONTECH, INSTR_NONTECH, D_NONTECH))
    y = call(sig2, instr2, d2, x)
    return (y, 'ok') if y is not None else (None, 'stage2_parse_failed')

BAD_S1 = '判断这条用户反馈的类型，只输出类型。'      # 缺取值域
stops = Counter(two_stage(x, BAD_S1)[1] for x, _ in TEST)
print('第一级缺取值域时的停止位置:', dict(stops))
assert stops['stage1_parse_failed'] == len(TEST)
assert 'stage2_parse_failed' not in stops, '第一级失败时第二级不该被调用'

stops_ok = Counter(two_stage(x, INSTR_S1)[1] for x, _ in TEST)
print('第一级正常时:', dict(stops_ok))
print('\\n✅ 每一级都要**分别**记录三个量。')
print('   只记端到端时，「第一级解析失败率上升」表现为「整体效果下降」，')
print('   而你会去优化第二级——这是组合系统里最常见的归因错误。')"""),

    md("""## 4 · 输出格式三选：每加一个字段就多一个失败入口"""),

    code("""SIG_MULTI = Signature(
    [('feedback', str)], 'label', LABELS,
    invariants=[('confidence_in_unit', lambda v: True)])   # label 本身的不变量

def simulate_output(fmt, x, y, seed=0):
    \"\"\"模拟三种格式下模型的实际输出（含各自的典型失败）。\"\"\"
    h = int(hashlib.md5((x + fmt + str(seed)).encode()).hexdigest(), 16)
    r = (h % 1000) / 1000.0
    if fmt == 'bare':
        return y if r > 0.30 else f'我认为是 {y}。'            # 30% 多说话
    if fmt == 'json1':
        return (json.dumps({'label': y}) if r > 0.10
                else f'```json\\n{json.dumps({"label": y})}\\n```')   # 10% 裹围栏
    # json3: 三个字段 → 每个字段都有出错的机会
    if r > 0.55:
        return json.dumps({'reason': '用户描述了一个故障', 'label': y, 'confidence': 0.8})
    if r > 0.40:
        return json.dumps({'reason': '…', 'label': y})              # 缺字段
    if r > 0.25:
        return json.dumps({'reason': '…', 'label': y, 'confidence': 7.5})  # 越界
    if r > 0.10:
        return '{"reason": "…", "label": "%s", "confidence": 0.8' % y      # 少括号
    return f'```json\\n{json.dumps({"reason": "…", "label": y, "confidence": 0.8})}\\n```'

def parse_fmt(raw, fmt):
    body = re.sub(r'^```[a-z]*\\s*|\\s*```$', '', raw.strip())
    if fmt == 'bare':
        return body if body in LABELS else None
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        return None
    if obj.get('label') not in LABELS:
        return None
    if fmt == 'json3':
        c = obj.get('confidence')
        if not (isinstance(c, (int, float)) and 0.0 <= c <= 1.0):
            return None                       # 不变量违规也是解析失败
        if not obj.get('reason'):
            return None
    return obj['label']

print(f"{'格式':<10}{'字段数':>7}{'解析成功率':>12}{'典型失败':<28}")
rates = {}
for fmt, nf, note in [('bare', 1, '多说一个字就失败'),
                      ('json1', 1, '裹代码块（可清洗）'),
                      ('json3', 3, '缺字段/越界/少括号/围栏')]:
    ok = sum(1 for x, y in TEST if parse_fmt(simulate_output(fmt, x, y), fmt) is not None)
    rates[fmt] = ok / len(TEST)
    print(f'{fmt:<10}{nf:>7}{rates[fmt]:>12.0%}  {note:<28}')

assert rates['json3'] < rates['json1'], '字段越多解析成功率越低'

# 放大样本：让裸值的脆弱性真的显现
BIG = [(f'{x}#{i}', y) for i in range(20) for x, y in TEST]
big = {}
for fmt in ('bare', 'json1', 'json3'):
    ok = sum(1 for x, y in BIG
             if parse_fmt(simulate_output(fmt, x, y), fmt) is not None)
    big[fmt] = ok / len(BIG)
print(f"\\n放大到 {len(BIG)} 条后："
      f"bare {big['bare']:.0%} · json1 {big['json1']:.0%} · json3 {big['json3']:.0%}")
assert big['bare'] < big['json1'], '样本够大时裸值确实最脆'
assert big['json3'] < big['json1'], '字段越多越脆'
print('   → 这才是真实的排序：bare < json3 或 json1，而 json1 最稳。')
print('   **小样本上「两个都 100%」不是「一样鲁棒」，是「分辨不出来」**——')
print('   这与模块 03 第 5 节「样本量与候选数必须一起看」是同一条。')
print(f"\\n✅ 解析成功率：bare {rates['bare']:.0%} · json1 {rates['json1']:.0%} · "
      f"json3 {rates['json3']:.0%}。")
print('   注意 bare 与 json1 在这 10 条样本上都是 100%——'
      '**样本太小，裸值的脆弱性没显现出来**（它 30% 的概率多说话，10 条里恰好没抽到）。')
print('   下面把样本放大到 200 条再看一次，让这个差别真的出现。')
print('   两个结论：')
print('   ① 裸值不配解码约束时最脆——多说一个字就全丢（模块 04 会把它变成最优选择）；')
print('   ② **每多一个字段就多一个解析失败入口**，而解析失败是全或无的。')
print('      所以 schema 的复杂度该由下游真正需要的字段决定，不是「顺便多要几个」。')
print('   一个模拟器不能演示但工程上必须知道的点：**字段顺序是一个可调项**。')
print('   reason 放在 label 之前，模型生成标签时已经写过理由；反过来则是事后合理化。')"""),

    md("""## 5 · 重试的选择偏倚

「只在解析成功的样本上报分」会高估多少？"""),

    code("""# 构造一个真实的相关性：难样本更可能解析失败，**也**更可能答错
DIFFICULTY = {x: (int(hashlib.md5(x.encode()).hexdigest(), 16) % 100) / 100.0
              for x, _ in TEST}

def simulate_with_difficulty(x, gold, seed=0):
    d = DIFFICULTY[x]
    r1 = ((int(hashlib.md5((x + 'p' + str(seed)).encode()).hexdigest(), 16) % 1000) / 1000)
    r2 = ((int(hashlib.md5((x + 'c' + str(seed)).encode()).hexdigest(), 16) % 1000) / 1000)
    parse_ok = r1 > d * 0.9          # 难 → 更可能解析失败
    correct = r2 > d * 0.9           # 难 → 更可能答错
    return parse_ok, correct

def biased_vs_honest(n_seeds=200):
    honest, biased, parse_rates = [], [], []
    for seed in range(n_seeds):
        n_ok = n_c_given_ok = n_c = 0
        for x, gold in TEST:
            ok, corr = simulate_with_difficulty(x, gold, seed)
            if ok:
                n_ok += 1
                n_c_given_ok += corr
            n_c += (ok and corr)
        honest.append(n_c / len(TEST))
        biased.append(n_c_given_ok / n_ok if n_ok else float('nan'))
        parse_rates.append(n_ok / len(TEST))
    return float(np.mean(honest)), float(np.nanmean(biased)), float(np.mean(parse_rates))

h, b, pr = biased_vs_honest()
print(f'解析成功率           {pr:.1%}')
print(f'诚实口径（分母=全部） {h:.1%}')
print(f'有偏口径（只看解析成功的） {b:.1%}')
print(f'高估了 {(b - h) * 100:.1f} 个百分点（相对 {(b - h) / h:.0%}）')

assert b > h, '在解析成功的子集上报分会高估'
# 偏倚来源：解析成功与答对正相关
xs = [(int(ok), int(c)) for x, g in TEST for ok, c in [simulate_with_difficulty(x, g, 0)]]
if len(set(a for a, _ in xs)) > 1 and len(set(c for _, c in xs)) > 1:
    corr = float(np.corrcoef([a for a, _ in xs], [c for _, c in xs])[0, 1])
    print(f'\\n解析成功与答对的相关系数（单个 seed）: {corr:.2f}')
print('\\n✅ 偏倚的来源很清楚：解析成功与答对**正相关**（都受难度影响），')
print('   所以条件化在「解析成功」上会拉高准确率。')
print('   三条纪律：')
print('   ① 报分的分母必须是全部样本，解析失败记为错；')
print('   ② 「解析成功的样本上准确率 X%」可以说，但必须与解析率一起出现；')
print('   ③ 重试的触发条件只能是「解析失败」，不能是「结果看起来不对」——')
print('      后者是在用真值调参（与 C68 模块 02 的重试纪律同构）。')
print('   而根本的修法是模块 04 的解码约束：让不合法输出在生成时就不可能产生。')"""),

    md("""## 6 · prompt 版本化与回归门禁"""),

    code("""def prompt_bundle(sig, instruction, demos, format_spec, decoding,
                  model_id, temperature, changelog):
    return dict(signature=dict(inputs=[[n, t.__name__] for n, t in sig.inputs],
                               output=sig.output, domain=list(sig.domain)),
                instruction=instruction,
                demos=[[a, b] for a, b in demos],        # 有序！
                format_spec=format_spec, decoding=decoding,
                model_id=model_id, temperature=temperature,
                changelog=changelog)

FP_FIELDS = ('signature', 'instruction', 'demos', 'format_spec', 'decoding',
             'model_id', 'temperature')       # changelog **不**进指纹

def bundle_fingerprint(b):
    payload = {k: b[k] for k in FP_FIELDS}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]

V3 = prompt_bundle(SIG, build_instruction(), POOL[:8], FMT,
                   dict(constrained=False), 'toy-lm@1', 0.0, 'v3: 初版')
print('v3 指纹:', bundle_fingerprint(V3))

def prompt_gate(new, old, sig, new_metrics, old_metrics, sigma=0.05):
    blocking, warn = [], []
    # 确定性 —— 零误报
    miss = sig.check_instruction(new['instruction'])
    if miss:
        blocking.append(f'指令里缺取值域: {miss}')
    fmt_err = sig.check_format(new['format_spec'])
    if fmt_err:
        blocking.append(f'格式规范问题: {fmt_err}')
    if bundle_fingerprint(new) != bundle_fingerprint(old) and \\
            new['changelog'] == old['changelog']:
        blocking.append('指纹变了但 CHANGELOG 没动——一次没人知道发生过的 prompt 变更')
    if new_metrics['parse_rate'] < 1.0:
        blocking.append(f"解析成功率 {new_metrics['parse_rate']:.0%} < 100%")
    # 统计
    drop = old_metrics['end_to_end'] - new_metrics['end_to_end']
    if drop > 2 * sigma:
        blocking.append(f"端到端下降 {drop:.1%} > 2σ ({2 * sigma:.1%})")
    # 报警：预测分布漂移
    if new_metrics.get('psi', 0.0) > 0.25:
        warn.append(f"预测标签分布 PSI {new_metrics['psi']:.2f} > 0.25（顺序偏置/示例漂移）")
    return blocking, warn

M_OK = dict(parse_rate=1.0, end_to_end=0.70, psi=0.05)
V4_good = dict(V3); V4_good['demos'] = [[a, b] for a, b in POOL[:10]]
V4_good['changelog'] = 'v4: 示例从 8 条加到 10 条，端到端 +2pp'
print('\\n正常升级:', prompt_gate(V4_good, V3, SIG, M_OK, M_OK))

V4_silent = dict(V3); V4_silent['instruction'] = build_instruction() + ' 请仔细思考。'
print('改了指令但没写 CHANGELOG:',
      prompt_gate(V4_silent, V3, SIG, M_OK, M_OK)[0])

V4_nodomain = dict(V4_good); V4_nodomain['instruction'] = INSTR_NO_DOMAIN
print('新指令缺取值域:', prompt_gate(V4_nodomain, V3, SIG, M_OK, M_OK)[0][:1])

assert prompt_gate(V4_good, V3, SIG, M_OK, M_OK) == ([], [])
assert any('CHANGELOG' in x for x in prompt_gate(V4_silent, V3, SIG, M_OK, M_OK)[0])
assert any('取值域' in x for x in prompt_gate(V4_nodomain, V3, SIG, M_OK, M_OK)[0])
assert prompt_gate(V4_good, V3, SIG, dict(parse_rate=1.0, end_to_end=0.55, psi=0.05),
                   M_OK)[0], '端到端下降超过 2σ 必须阻断'
assert prompt_gate(V4_good, V3, SIG, dict(parse_rate=1.0, end_to_end=0.70, psi=0.4),
                   M_OK) == ([], [
    '预测标签分布 PSI 0.40 > 0.25（顺序偏置/示例漂移）'])
print('\\n✅ 四项确定性阻断 + 一项统计阻断 + 一项报警。')
print('   最有价值的是「指纹变了但 CHANGELOG 没动」这一条：它是纯算术、零误报，')
print('   而它防住的正是本模块最想防的那件事——一次没人知道发生过的 prompt 变更。')"""),

    md("""## ✏️ 练习 1：Signature 的完整校验

扩展 `Signature`：实现 `full_check(instruction, format_spec, parser_fields)`，
返回一个问题列表（空列表 = 通过）。要检查四件事：

1. 取值域里的每一项都出现在指令里
2. 格式规范里含签名的 `output` 字段名
3. **解析器实际读取的字段名集合**必须与格式规范里声明的一致
   （`parser_fields` 是解析器会读的字段名集合）
4. 若 `domain` 是枚举，则它**不能为空**，且不能有重复项"""),

    code("""def full_check(sig, instruction, format_spec, parser_fields):
    \"\"\"返回问题字符串列表；空列表表示通过。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
assert full_check(SIG, build_instruction(), FMT, {'label'}) == []

# 1) 缺取值域
p1 = full_check(SIG, INSTR_NO_DOMAIN, FMT, {'label'})
assert any('取值域' in x for x in p1), p1

# 2) 格式规范里没有 output 字段
p2 = full_check(SIG, build_instruction(), 'json {"category": "<v>"}', {'label'})
assert any('格式' in x or 'output' in x for x in p2), p2

# 3) 解析器读的字段与格式规范不一致 —— 这是一个真实的、很难发现的 bug
p3 = full_check(SIG, build_instruction(), FMT, {'label', 'confidence'})
assert any('解析器' in x for x in p3), p3

# 4) 空枚举 / 重复项
sig_empty = Signature([('x', str)], 'label', [])
assert any('空' in x for x in full_check(sig_empty, build_instruction(), FMT, {'label'}))
sig_dup = Signature([('x', str)], 'label', ['bug', 'bug', 'other'])
instr_dup = '标签只能是 bug / other 之一。'
assert any('重复' in x for x in full_check(sig_dup, instr_dup, FMT, {'label'}))
print('✅ 练习 1 通过：四项检查全部不需要调用模型')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def full_check(sig, instruction, format_spec, parser_fields):
    problems = []
    if isinstance(sig.domain, list):
        if len(sig.domain) == 0:
            problems.append('取值域为空——解析器无法判定合法性')
        if len(set(sig.domain)) != len(sig.domain):
            dup = [k for k, c in Counter(sig.domain).items() if c > 1]
            problems.append(f'取值域有重复项: {dup}')
    miss = sig.check_instruction(instruction)
    if miss:
        problems.append(f'指令里缺取值域: {miss}')
    fmt_err = sig.check_format(format_spec)
    if fmt_err:
        problems.append(f'格式规范问题: {fmt_err}')
    if format_spec:
        declared = set(re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)"\\s*:', format_spec))
        if declared and set(parser_fields) - declared:
            problems.append(f'解析器读的字段 {sorted(set(parser_fields) - declared)} '
                            f'未在格式规范里声明')
    return problems

assert full_check(SIG, build_instruction(), FMT, {'label'}) == []
assert any('取值域' in x for x in full_check(SIG, INSTR_NO_DOMAIN, FMT, {'label'}))
assert any('格式' in x for x in
           full_check(SIG, build_instruction(), 'json {"category": "<v>"}', {'label'}))
assert any('解析器' in x for x in full_check(SIG, build_instruction(), FMT,
                                          {'label', 'confidence'}))
assert any('空' in x for x in
           full_check(Signature([('x', str)], 'label', []), build_instruction(), FMT, {'label'}))
assert any('重复' in x for x in
           full_check(Signature([('x', str)], 'label', ['bug', 'bug', 'other']),
                      '标签只能是 bug / other 之一。', FMT, {'label'}))
print('✅ 参考答案 1 通过')
print('   第 3 项检查值得特别注意：**解析器读了一个格式规范里没声明的字段**。')
print('   这个 bug 的症状是「那个字段永远是 None」，而它不会报错——')
print('   下游拿到 None 之后可能一路传下去，直到某个远处的地方崩掉。')"""),

    md("""## ✏️ 练习 2：槽位的最小充分集

实现 `minimal_slots(target_end_to_end)`：在 `SLOTS` 的所有子集里，
找出**能达到 `target_end_to_end` 的、槽位最少的那个组合**（平局取字典序最小的）。

返回 `(frozenset(保留的槽位), 实测端到端)`；不存在则返回 `None`。

这个函数的用途：**指令不是越长越好**——它告诉你哪些句子是真的在起作用。"""),

    code("""def minimal_slots(target_end_to_end):
    \"\"\"返回 (frozenset(保留的槽位名), 端到端分数) 或 None。\"\"\"
    # TODO：枚举 SLOTS 的所有非空子集
    raise NotImplementedError"""),

    code("""# —— 自测 ——
full = run_program(build_instruction(), POOL, FMT)['end_to_end']
print(f'完整指令（5 个槽位）端到端 = {full:.0%}')

r = minimal_slots(full)
assert r is not None
kept, got = r
print(f'最小充分集: {sorted(kept)} → {got:.0%}')
assert got >= full - 1e-9
assert 'domain' in kept, '取值域必须在里面（缺了就归零）'
assert len(kept) < len(SLOTS), '应当能去掉一些槽位而不掉分'

# 目标定得不可能高 → 无解
assert minimal_slots(1.01) is None

# 目标很低 → 只要 domain 就够
low = minimal_slots(0.1)
assert low is not None and 'domain' in low[0]
print(f'目标 10% 时的最小充分集: {sorted(low[0])}')
print('✅ 练习 2 通过：指令不是越长越好，而是「哪些句子真的在起作用」')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def minimal_slots(target_end_to_end):
    names = list(SLOTS)
    best = None
    for r in range(1, len(names) + 1):
        for combo in itertools.combinations(names, r):
            drop = tuple(n for n in names if n not in combo)
            e2e = run_program(build_instruction(drop=drop), POOL, FMT)['end_to_end']
            if e2e >= target_end_to_end - 1e-9:
                cand = (len(combo), tuple(sorted(combo)), frozenset(combo), e2e)
                if best is None or cand[:2] < best[:2]:
                    best = cand
        if best is not None:
            break                       # 已找到最小规模，不必再看更大的
    return None if best is None else (best[2], best[3])

full = run_program(build_instruction(), POOL, FMT)['end_to_end']
kept, got = minimal_slots(full)
assert got >= full - 1e-9 and 'domain' in kept and len(kept) < len(SLOTS)
assert minimal_slots(1.01) is None
assert 'domain' in minimal_slots(0.1)[0]
print('✅ 参考答案 2 通过')
print('   注意那个 break：一旦在规模 r 上找到解，就不必再看 r+1——')
print('   我们要的是**最少槽位**，而更大的组合规模一定更差（按这个目标）。')
print()
print('   一个诚实的说明：这个模拟器里 fallback 与 forbid 的贡献是 0，')
print('   所以「最小充分集」会把它们去掉。**在真实系统上不要照搬这个结论**——')
print('   它们的效应（被迫在不合适的类里挑一个 / 裹代码块）这个模拟器不建模。')
print('   这个函数的价值是**方法**：把「指令该写多长」变成一次可测量的搜索。')
print('   而它也正是模块 03 自动提示优化的最小形态。')"""),

    md("""## ✏️ 练习 3：可组合的 pipeline 与错误传播

实现 `Pipeline`：接一串 `(signature, instruction, demos, mapper)`，
按顺序调用，并且

- **上一级解析失败时，下一级不被调用**
- 每一级分别统计 `calls / parse_ok / correct`
- `run(x, gold)` 返回 `(最终输出或 None, 停止位置)`
- `stats()` 返回每一级的 `parse_rate`，以及端到端准确率

`mapper(gold)` 把最终真值映射成这一级的期望输出（用来算每一级的正确率）。"""),

    code("""class Pipeline:
    def __init__(self, stages):
        \"\"\"stages: [(sig, instruction, demos, mapper)]。mapper=None 表示最后一级。\"\"\"
        # TODO
        raise NotImplementedError

    def run(self, x):
        \"\"\"返回 (输出或 None, 'ok' / f'stage{i}_parse_failed')。\"\"\"
        raise NotImplementedError

    def stats(self, test=None):
        \"\"\"返回 dict(per_stage=[{calls, parse_rate}], end_to_end=...)。\"\"\"
        raise NotImplementedError"""),

    code("""# —— 自测 ——
def route_mapper(gold):
    return 'tech' if gold in TECH else 'nontech'

# 正常两级
pipe = Pipeline([(SIG_STAGE1, INSTR_S1, D_S1, route_mapper),
                 (SIG_TECH, INSTR_TECH, D_TECH, None)])
out, stop = pipe.run('打开报表就崩溃')
print('run:', out, stop)
assert stop == 'ok' and out in sorted(TECH)

st = pipe.stats()
print('stats:', st)
assert len(st['per_stage']) == 2
assert st['per_stage'][0]['calls'] == len(TEST)
assert st['per_stage'][0]['parse_rate'] == 1.0
# 第二级只在第一级解析成功时被调用
assert st['per_stage'][1]['calls'] <= st['per_stage'][0]['calls']

# 第一级缺取值域 → 第二级一次都不该被调用
bad_pipe = Pipeline([(SIG_STAGE1, BAD_S1, D_S1, route_mapper),
                     (SIG_TECH, INSTR_TECH, D_TECH, None)])
st_bad = bad_pipe.stats()
print('第一级坏掉:', st_bad)
assert st_bad['per_stage'][0]['parse_rate'] == 0.0
assert st_bad['per_stage'][1]['calls'] == 0, '上一级失败时下一级不该被调用'
assert st_bad['end_to_end'] == 0.0
assert bad_pipe.run('打开报表就崩溃')[1] == 'stage0_parse_failed'
print('✅ 练习 3 通过：解析失败不向下传播，且每一级分别统计')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
class Pipeline:
    def __init__(self, stages):
        self.stages = list(stages)

    def run(self, x):
        cur = x
        for i, (sig, instr, demos, mapper) in enumerate(self.stages):
            y = call(sig, instr, demos, cur)
            if y is None:
                return None, f'stage{i}_parse_failed'
            if mapper is not None:
                cur = x            # 本例里下一级仍然看原始输入；真实系统可传 y
        return y, 'ok'

    def stats(self, test=None):
        test = TEST if test is None else test
        per = [dict(calls=0, parse_ok=0) for _ in self.stages]
        e2e = 0
        for x, gold in test:
            cur = x
            failed = False
            y = None
            for i, (sig, instr, demos, mapper) in enumerate(self.stages):
                per[i]['calls'] += 1
                y = call(sig, instr, demos, cur)
                if y is None:
                    failed = True
                    break
                per[i]['parse_ok'] += 1
            if not failed:
                e2e += (y == gold)
        return dict(per_stage=[dict(calls=p['calls'],
                                    parse_rate=(p['parse_ok'] / p['calls']) if p['calls'] else 0.0)
                               for p in per],
                    end_to_end=e2e / len(test))

pipe = Pipeline([(SIG_STAGE1, INSTR_S1, D_S1, route_mapper),
                 (SIG_TECH, INSTR_TECH, D_TECH, None)])
assert pipe.run('打开报表就崩溃')[1] == 'ok'
st = pipe.stats()
assert st['per_stage'][0]['parse_rate'] == 1.0
assert st['per_stage'][1]['calls'] <= st['per_stage'][0]['calls']
bad_pipe = Pipeline([(SIG_STAGE1, BAD_S1, D_S1, route_mapper),
                     (SIG_TECH, INSTR_TECH, D_TECH, None)])
st_bad = bad_pipe.stats()
assert st_bad['per_stage'][1]['calls'] == 0 and st_bad['end_to_end'] == 0.0
print('✅ 参考答案 3 通过')
print('   关键的一行是 `break`：上一级解析失败时**跳出整个循环**，')
print('   而不是把 None 渲染进下一级的 prompt。')
print('   后者的症状是「模型答了一个莫名其妙的东西」，而且很难定位——')
print('   因为它看起来像模型的问题，实际是上游的 None 被当成输入了。')"""),

    md("""## ✏️ 练习 4：CHANGELOG 门禁与版本目录

实现 `PromptRepo`：一个最小的 prompt 版本仓库。

- `add(version, bundle)` —— 加一个版本；**若指纹与上一个版本相同但 version 不同，报错**
  （那说明「改了个名字但什么都没改」）
- `activate(version)` —— 切 ACTIVE 指针
- `diff(v1, v2)` —— 返回哪些指纹字段变了（字段名列表）
- `audit()` —— 返回问题列表：
  ① 相邻版本之间指纹变了但 changelog 没变；
  ② 存在指纹完全相同的两个版本；
  ③ ACTIVE 指向的版本不存在"""),

    code("""class PromptRepo:
    def __init__(self):
        self.versions = {}      # version -> bundle
        self.order = []
        self.active = None

    def add(self, version, bundle):
        # TODO
        raise NotImplementedError

    def activate(self, version):
        raise NotImplementedError

    def diff(self, v1, v2):
        raise NotImplementedError

    def audit(self):
        raise NotImplementedError"""),

    code("""# —— 自测 ——
repo = PromptRepo()
repo.add('v3', V3)
repo.add('v4', V4_good)
repo.activate('v4')

d = repo.diff('v3', 'v4')
print('v3 → v4 变了:', d)
assert d == ['demos'], d
assert repo.audit() == [], repo.audit()

# a) 指纹相同但版本号不同 → add 就该拒绝
V5_same = dict(V4_good); V5_same['changelog'] = 'v5: 只改了说明'
try:
    repo.add('v5', V5_same)
    raise SystemExit('不该到这里')
except ValueError as e:
    print('✅ add 拒绝:', e)

# b) 指纹变了但 changelog 没变 → audit 报出来
V6 = dict(V4_good); V6['instruction'] = build_instruction() + ' 请仔细思考。'
repo.add('v6', V6)                       # changelog 沿用 v4 的
issues = repo.audit()
assert any('changelog' in x.lower() for x in issues), issues
print('audit:', issues)

# c) ACTIVE 指向不存在的版本
repo.active = 'v99'
assert any('ACTIVE' in x for x in repo.audit())
repo.activate('v6')
assert not any('ACTIVE' in x for x in repo.audit())
print('✅ 练习 4 通过：版本仓库能把「悄悄改了 prompt」变成一个 audit 失败')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
class PromptRepo:
    def __init__(self):
        self.versions = {}
        self.order = []
        self.active = None

    def add(self, version, bundle):
        fp = bundle_fingerprint(bundle)
        for v, b in self.versions.items():
            if bundle_fingerprint(b) == fp:
                raise ValueError(f'{version} 与 {v} 指纹相同（{fp}）——'
                                 f'改了版本号但什么都没改')
        self.versions[version] = bundle
        self.order.append(version)

    def activate(self, version):
        assert version in self.versions, f'{version} 不存在'
        self.active = version

    def diff(self, v1, v2):
        a, b = self.versions[v1], self.versions[v2]
        return [k for k in FP_FIELDS if a.get(k) != b.get(k)]

    def audit(self):
        issues = []
        for prev, cur in zip(self.order, self.order[1:]):
            if bundle_fingerprint(self.versions[prev]) != \\
                    bundle_fingerprint(self.versions[cur]) and \\
                    self.versions[prev]['changelog'] == self.versions[cur]['changelog']:
                issues.append(f'{prev} → {cur}: 指纹变了但 changelog 没变')
        fps = Counter(bundle_fingerprint(b) for b in self.versions.values())
        for fp, c in fps.items():
            if c > 1:
                issues.append(f'指纹 {fp} 出现在 {c} 个版本里')
        if self.active is not None and self.active not in self.versions:
            issues.append(f'ACTIVE 指向不存在的版本 {self.active}')
        return issues

repo = PromptRepo()
repo.add('v3', V3); repo.add('v4', V4_good); repo.activate('v4')
assert repo.diff('v3', 'v4') == ['demos'] and repo.audit() == []
try:
    repo.add('v5', {**V4_good, 'changelog': 'v5: 只改了说明'})
    raise SystemExit
except ValueError:
    pass
repo.add('v6', {**V4_good, 'instruction': build_instruction() + ' 请仔细思考。'})
assert any('changelog' in x.lower() for x in repo.audit())
repo.active = 'v99'
assert any('ACTIVE' in x for x in repo.audit())
print('✅ 参考答案 4 通过')
print('   两条检查的分工：')
print('   ① `add` 里的「指纹相同」是**写入时**拒绝——它防的是版本号膨胀；')
print('   ② `audit` 里的「指纹变了但 changelog 没变」是**事后**检查——')
print('      它防的是一次没人知道发生过的变更。')
print('   两者都是纯算术、零误报，所以都可以进阻断项（C68-04 的分级）。')"""),

    md("""## 🧪 真实工程胶囊：DSPy 式的签名与自建两条路

```python
# ══════════════════════════════════════════════════════════════════
# A. 用 DSPy 的话（签名 / 模块 / 编译三层）
# ══════════════════════════════════════════════════════════════════
import dspy

class ClassifyFeedback(dspy.Signature):
    \"\"\"把用户反馈分类。\"\"\"                       # ← docstring 就是指令
    feedback: str = dspy.InputField()
    label: Literal['bug', 'feature', 'billing', 'account', 'other'] = dspy.OutputField()

classify = dspy.Predict(ClassifyFeedback)
#   模块 03 的自动优化在 DSPy 里是 teleprompter/optimizer：
#     compiled = dspy.MIPROv2(metric=my_metric).compile(classify, trainset=train)
#   它产出的正是「指令 + 示例集合与顺序」这个 bundle。

# ══════════════════════════════════════════════════════════════════
# B. 不用框架时，自己维护这三件事就够（本 notebook 的结构）
# ══════════════════════════════════════════════════════════════════
prompts/classify_feedback/
  v3/ signature.json instruction.txt demos.jsonl format.json decoding.json CHANGELOG.md
  ACTIVE -> v3
#   demos.jsonl 是**有序**文件 —— 顺序是内容的一部分，进指纹（模块 00 练习 2）

# ══════════════════════════════════════════════════════════════════
# C. 三个量分别打点（讲解第 2 节）
# ══════════════════════════════════════════════════════════════════
log.info('llm_call', extra=dict(
    prompt_fp=FP, parse_ok=parse_ok, out_of_domain=ood,
    retries=n_retries, latency_ms=ms, tokens_out=n_tok))
#   看板上必须有：parse_rate、acc_given_parsed、end_to_end **三条线**，
#   以及 retries 的分布（讲解第 6 节：重试次数必须被记录）。

# ══════════════════════════════════════════════════════════════════
# D. CI（讲解第 7 节 / 练习 1 & 4）
# ══════════════════════════════════════════════════════════════════
# 阻断（确定性，零误报）:
#   full_check(sig, instruction, format_spec, parser_fields) == []
#   repo.audit() == []
#   parse_rate == 1.0（在冒烟集上）
# 阻断（统计）:
#   任一标签的分层准确率相对基线下降 > 按方差推出的阈值（C68-04）
# 报警:
#   预测标签分布的 PSI（抓顺序偏置与示例漂移）
```

---

## 小结

| 结论 | 数字 / 判据 | 在哪一节 |
|---|---|---|
| 签名先于 prompt；契约可机械检查 | 三个检查全不需要调用模型 | 第 1 节 |
| 端到端 = 解析率 × 给定解析的正确率 | 两个因子的改进手段完全不同 | 讲解 2 |
| 放宽取值域会让端到端「上升」而实际有害 | 三个量一起报时立刻暴露 | 讲解 2 |
| 取值域是最重要的槽位 | 边际贡献 50pp（唯一非零的一项）；单删它剩 20%，与 fallback 同删才归零 | 第 2 节 |
| 禁止项与解析器是互补的，不是二选一 | 两者都不做时部分解析失败 | 第 2 节 |
| 错误传播是**精确的**乘法 | p₁ × p₂ 与实测端到端相等 | 第 3 节 |
| 拆成多级要满足三个条件之一，否则不该拆 | 本任务上单级 ≥ 两级 | 第 3 节 |
| 上一级解析失败时下一级不该被调用 | 否则 None 被渲染进 prompt | 第 3 节 |
| 每多一个字段就多一个解析失败入口 | 三字段 JSON 解析率 80%，单字段与裸值都 100% | 第 4 节 |
| 只在解析成功的样本上报分会高估 | 因为解析成功与答对正相关 | 第 5 节 |
| 「指纹变了但 CHANGELOG 没动」是零误报检查 | 它防的是一次没人知道的变更 | 第 6 节 / 练习 4 |

下一模块：**02 · few-shot 示例选择与顺序**——
选择的收益远大于数量，而顺序的影响大到不能忽略。"""),
]
