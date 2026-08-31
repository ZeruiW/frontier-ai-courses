# -*- coding: utf-8 -*-
"""C66 模块 05 · 成本感知评测与 harness 可复现性。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 04（pass@k / pass^k 与统计）；"
                 "知道「容器镜像」和「哈希」两个概念即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_cost_and_harness.ipynb'
                       '（成本模型与归一化 / 成本-成功率帕累托前沿 / best-of-n 的边际收益 / '
                       'scaffold 方差实验：同模型不同 harness / 配置指纹与漂移检测 / '
                       '评测卡自动生成器 / 上线门槛的期望效用计算）'),
    ("核心参考", "Kapoor et al., <em>AI Agents That Matter</em>（2024，成本-精度前沿与 agent 评测的可复现性）· "
                 "SWE-bench 官方 harness 与容器化评测实践 · "
                 "Mitchell et al., <em>Model Cards</em>（FAT* 2019，报告规范的思想来源）· "
                 "本课程 C08（算力与成本账本）· C24（推理服务）· C68（评测基础设施）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("cost-first", "不带成本的成功率是不可比的", "".join([
        P("先说结论：<strong>「agent A 在 SWE-bench Verified 上得 48%」这句话，"
          "在没有成本信息时是一个无法使用的数字。</strong>原因很直接——"
          "任何 agent 的成功率都可以通过<em>多花钱</em>提高。"),
        TABLE(["花钱的方式", "怎么提高成功率", "成本增幅", "是否算「模型更强」"], [
            ["<strong>提高重试/采样次数</strong>", "跑 $n$ 次取最好的（需要验证器）", "线性 $\\times n$", "❌ 这是 best-of-n，不是模型能力"],
            ["<strong>放宽步数上限</strong>", "从 30 步放到 200 步", "近似线性", "❌ 换个预算数字就能复制"],
            ["<strong>更长的上下文 / 更多检索</strong>", "把整个仓库塞进上下文", "token 成本可能涨十倍", "❌ 这是 scaffold 的选择"],
            ["<strong>更强的 scaffold</strong>", "加反思、加子 agent、加验证步骤", "视实现而定，常 2–5 倍", "❌ 这是 harness 能力，不是模型能力"],
            ["<strong>模型本身更强</strong>", "同样预算下做对更多", "不变", "✅ 只有这一行才是"],
        ]),
        CALLOUT("danger", "所以「谁更强」这个问题<strong>在不固定预算的情况下没有定义</strong>。"
                          "正确的提法只有两种：<strong>①「给定相同预算，谁的成功率更高」；"
                          "②「达到相同成功率，谁的成本更低」</strong>。"
                          "这两种提法都要求你把成本作为一等公民记录下来——"
                          "<em>而这正是绝大多数公开 agent 评测报告缺失的那一栏。</em>"),
        DUAL(
            "换个说法：报告一个不带成本的 agent 分数，等价于报告一辆车的最高时速却不说油耗。"
            "两辆车都能跑到 200 公里，一辆烧 8 升一辆烧 30 升——"
            "<strong>「都能跑到 200」这句话本身是真的，但用它做采购决策是荒谬的。</strong>",
            "形式化地说，agent 的能力不是一个标量，而是一条<span class=\"term\">成本-效用曲线</span> "
            "$s(b)$：给定预算 $b$（token、时间、调用次数），可达到的期望成功率。"
            "报告单点 $s(b_0)$ 只在 $b_0$ 被明确写出时才有意义；"
            "<strong>比较两个 agent 等价于比较两条曲线，而两条曲线可以相交</strong>——"
            "低预算下 A 更好、高预算下 B 更好，是完全正常的情况。"
            "<em>这也解释了为什么「哪个模型最强」这个问题在产品语境下经常没有答案，"
            "而「在我们的预算下哪个更合适」永远有答案。</em>",
        ),
    ])),

    # ============================================================== 2
    ("cost-model", "成本模型：四种成本与归一化", "".join([
        P("要把成本记进报告，先要定义什么叫成本。agent 评测里有四种，它们的单位不同、可比性也不同。"),
        TABLE(["成本类型", "单位", "怎么测", "陷阱"], [
            ["<strong>token 成本</strong>", "美元 / 任务", "$\\sum(\\text{in} \\times p_{\\text{in}} + \\text{out} \\times p_{\\text{out}})$", "<strong>缓存命中会让实际账单远低于名义 token</strong>；跨模型比较时价格会变，应<em>同时</em>记 token 数与当时的单价"],
            ["<strong>墙钟时间</strong>", "秒 / 任务", "端到端计时", "受并发度、限流、外部服务抖动影响极大；<strong>不同并发下测出的时间不可比</strong>"],
            ["<strong>工具/环境成本</strong>", "调用次数、容器分钟", "计数 + 计时", "容易被忽略；跑测试套件的 CPU 时间在代码类任务里可能超过 token 成本"],
            ["<strong>人力成本</strong>", "人分钟 / 任务", "人工复核、人工判分的耗时", "在半自动评测里是真正的瓶颈；<em>它决定了评测能跑多大规模</em>"],
        ]),
        H3("归一化：三种做法，各自的适用面"),
        OL([
            "<strong>固定预算</strong>：给所有 agent 同样的 token/步数上限，比成功率。"
            "最简单、最公平，<strong>推荐作为默认做法</strong>。缺点是预算选得不好会让某些 agent 的曲线被截断在拐点之前。",
            "<strong>成本归一成功率</strong>：报「每美元买到多少次成功」。"
            "适合成本敏感的产品决策，但它<em>隐含假设成功的边际价值恒定</em>——"
            "对「必须做完否则一分不值」的任务不成立。",
            "<strong>报整条曲线</strong>：在多个预算档位各跑一遍，画成本-成功率前沿。"
            "信息最完整、成本最高，<strong>适合模型选型这种一次性决策</strong>。",
        ]),
        CALLOUT("warn", "一个非常容易踩的坑：<strong>用「平均 token 数」做成本归一化，"
                        "会重蹈模块 03 的 Goodhart 覆辙</strong>——失败的轨迹往往更短更便宜，"
                        "所以「降低平均成本」的最省事路径依然是「早点放弃」。"
                        "<strong>正确做法是报「每次成功的平均成本」</strong>"
                        "（总成本 ÷ 成功次数），它天然把失败的开销摊到了成功头上。"),
    ])),

    # ============================================================== 3
    ("pareto", "成本-成功率前沿：怎么读，怎么用", "".join([
        P("把每个配置（模型 × scaffold × 预算）画成 (成本, 成功率) 平面上的一个点，"
          "取<strong>帕累托前沿</strong>——不存在另一个点同时更便宜且更准的那些配置。"),
        ASCII("""
  成功率
    │                                      ● D (贵且强)
 60%│                          ● C
    │              ● B
 40%│      ● A                       ○ E (被 C 支配：更贵且更差)
    │  ○ F (被 A 支配)
 20%│
    └──────────────────────────────────────────────► 每任务成本
      $0.05    $0.2      $1.0        $4.0     $18

  前沿 = {A, B, C, D}。E 和 F 被支配 —— 它们在任何预算下都不该被选。
  选哪个取决于你的预算线落在哪里，而不是"谁的分数最高"。
"""),
        TABLE(["读法", "问题", "答案在图上哪里"], [
            ["<strong>预算给定</strong>", "我每任务最多花 $1，选谁", "在 $x = 1$ 处作垂线，取前沿上左侧最高的点（B 或 C）"],
            ["<strong>目标给定</strong>", "我要 55% 成功率，最便宜多少", "在 $y = 0.55$ 处作水平线，取前沿上最左的交点"],
            ["<strong>边际成本</strong>", "从 C 提到 D 值不值", "看两点间的斜率：多花的钱除以多得的成功率"],
            ["<strong>被支配点</strong>", "E 为什么永远不该选", "存在 C 同时更便宜更准——<strong>这类点在真实评测里非常常见</strong>，通常是 scaffold 没调好"],
        ]),
        H3("best-of-n 的特殊地位"),
        P("best-of-n（跑 $n$ 次取最好）是成本-成功率曲线上最容易被误用的一段。它的成功率就是模块 04 的 "
          "<strong>pass@n</strong>，成本近似线性增长。三条必须记住的性质："),
        UL([
            "<strong>它需要一个验证器</strong>。没有验证器就没法「取最好的」，"
            "此时 $n$ 次采样的实际价值接近 $n = 1$——<em>这是 best-of-n 最常见的误用</em>。",
            "<strong>边际收益急剧递减</strong>：pass@n 随 $n$ 增长很快饱和；"
            "从 1 到 2 通常涨十几个点，从 8 到 16 可能只涨一两个点，而成本翻倍。",
            "<strong>验证器本身有假阳率</strong>：$n$ 越大，「被验证器错判为成功的失败解」被选中的概率越高。"
            "<em>这是模块 02 的 $\\alpha$ 在 best-of-n 场景下的放大效应</em>——"
            "$n$ 大到一定程度，best-of-n 会开始<strong>系统性地挑出 hack 解</strong>。",
        ]),
        CALLOUT("intuition", "第三条值得记牢：<strong>best-of-n 是一个对判分器质量极其敏感的操作。</strong>"
                             "判分器完美时它单调有益；判分器有 5% 假阳率时，$n = 32$ 的 best-of-n "
                             "有很大概率选中一个假阳解。notebook 第 3 节会把这个概率算出来——"
                             "<em>它同时也是 C67 模块 05 里 reward hacking 的评测侧同构现象。</em>"),
    ])),

    # ============================================================== 4
    ("scaffold", "harness / scaffold：影响常常大于模型本身的差异", "".join([
        P("这是整门课里最反直觉、也最重要的工程事实：<strong>在 agentic 基准上，"
          "同一个模型换一套 scaffold，分数的变化幅度经常超过两代模型之间的差距。</strong>"),
        H3("scaffold 包含什么"),
        TABLE(["组成部分", "具体选择", "对分数的影响机制"], [
            ["<strong>工具集</strong>", "给不给 <code>grep</code>？文件编辑是全文替换还是行级 patch？", "工具的表达力直接决定了 agent 需要多少步；行级编辑工具能显著降低格式错误"],
            ["<strong>提示与角色</strong>", "系统提示、few-shot、是否要求先规划", "影响探索策略与放弃倾向"],
            ["<strong>循环结构</strong>", "单 agent / 反思循环 / planner-executor / 多子 agent", "结构越复杂，成本越高，收益不一定单调"],
            ["<strong>预算与终止</strong>", "最大步数、最大 token、超时、重试次数", "<strong>最容易被忽略、影响最大的一组</strong>"],
            ["<strong>上下文管理</strong>", "压缩策略、记忆、检索（C33）", "长任务上决定成败"],
            ["<strong>错误处理</strong>", "工具报错怎么回传给模型、要不要自动重试", "直接决定模块 03 的恢复率"],
        ]),
        CALLOUT("danger", "由此得到一条必须遵守的报告纪律：<strong>任何 agent 基准分数，"
                          "如果没有附带 scaffold 的完整描述，都不构成一个可比较、可复现的结果。</strong>"
                          "「模型 A 得 48%，模型 B 得 42%」这句话，如果 A 用的是精心调过的自研 scaffold、"
                          "B 用的是官方最简 baseline，那么这个 6 个点的差距<em>可能完全来自 scaffold</em>。"),
        H3("怎么做一次公平的模型对比"),
        OL([
            "<strong>固定 scaffold，只换模型</strong>——这是唯一能支持「模型 A 比 B 强」这个结论的设计；",
            "<strong>但要意识到它的局限</strong>：一个为 A 调优过的 scaffold 在 B 上可能水土不服。"
            "更公平（也更贵）的做法是<strong>各自用各自的最佳 scaffold</strong>，"
            "然后明确声明「这比较的是「模型+scaffold」这个组合，不是模型本身」；",
            "<strong>报告 scaffold 消融</strong>：至少给出「最简 baseline scaffold」下的分数作为参照，"
            "让读者能把 scaffold 贡献和模型贡献分开。",
        ]),
        DUAL(
            "为什么这件事在静态基准时代不存在？因为静态基准的 scaffold 只是一个 prompt 模板，"
            "变化空间很小。agent 的 scaffold 是<strong>一整个程序</strong>——"
            "它决定了模型能看到什么、能做什么、什么时候停。"
            "<strong>说得直白些：agent 基准测的从来不是模型，而是「模型 + 你写的那个程序」的组合。</strong>",
            "从测量的角度，scaffold 是一个未被控制的<span class=\"term\">调节变量</span>（moderator）。"
            "当调节变量的效应量与主效应量同阶时，不报告它就使得整个实验缺乏"
            "<span class=\"term\">内部效度</span>。"
            "<em>正确的实验设计是把 scaffold 作为一个显式因子纳入："
            "至少做 2×2（两个模型 × 两个 scaffold），从而能估计交互项。</em>"
            "notebook 第 4 节会把这个 2×2 设计跑一遍，展示交互项如何翻转结论。",
        ),
    ])),

    # ============================================================== 5
    ("repro", "可复现性清单：十个必须钉死的东西", "".join([
        P("「可复现」在 agent 评测里的含义是：<strong>另一个人拿到你的报告，"
          "能在正负一个误差棒内重现你的数字。</strong>下面这十项缺一项就做不到。"),
        TABLE(["#", "要钉死的东西", "怎么钉", "不钉会怎样"], [
            ["1", "<strong>容器镜像</strong>", "记 <code>sha256:</code> digest，不是 tag", "tag 会被覆盖，几个月后同一个 tag 是不同的镜像"],
            ["2", "<strong>任务集版本</strong>", "数据集哈希 + 版本号，且只增不改（模块 01）", "悄悄修过的题会让历史分数全部失效"],
            ["3", "<strong>scaffold 版本</strong>", "git commit + 配置文件哈希", "第 4 节的全部理由"],
            ["4", "<strong>模型标识</strong>", "完整模型 ID + 快照日期（若可用）", "「最新版」是一个会移动的目标"],
            ["5", "<strong>采样参数</strong>", "temperature / top_p / seed（若支持）", "温度不同，方差与均值都不同"],
            ["6", "<strong>预算参数</strong>", "max_steps / max_tokens / 超时 / 重试次数", "这是最影响分数、也最常被漏写的一组"],
            ["7", "<strong>并发度</strong>", "worker 数", "<strong>并发会改变超时行为</strong>——高并发下容器变慢，超时任务变多"],
            ["8", "<strong>网络策略</strong>", "断网 / 白名单 / 录制回放", "联网的评测在两个时间点跑就是两个实验"],
            ["9", "<strong>判分器版本</strong>", "判分代码的 commit + 金标准集的 α/β（模块 02）", "判分器也会被修 bug"],
            ["10", "<strong>重复次数与聚合方式</strong>", "$N$、$k$、micro/macro、CI 方法（模块 04）", "同一批数据能算出好几个不同的数字"],
        ]),
        H3("把十项压成一个指纹"),
        P("实践上的做法是把这十项序列化后取哈希，得到一个 <strong>run fingerprint</strong>，"
          "写进每一条结果记录。<strong>两次运行的指纹相同，分数却差很多——这本身就是一个需要调查的告警</strong>"
          "（说明还有没被记录的变量在动）；指纹不同的两次运行，则从一开始就不该被直接比较。"),
        CALLOUT("intuition", "指纹机制的额外好处是<strong>它让「不可比较」这件事变成机器可判定的</strong>。"
                             "在 C68 的 CI 门禁里，这一条直接变成一个断言："
                             "<code>assert current.fingerprint == baseline.fingerprint</code>，"
                             "不相等就不允许做回归对比，而不是让人去肉眼核对配置。"),
        H3("网络：录制回放（record/replay）"),
        P("对必须联网的评测，唯一可行的可复现方案是<strong>录制回放</strong>："
          "第一次运行时把所有 HTTP 请求与响应录下来，之后的运行从录制里回放。"
          "代价是录制会过期（页面改版后录制内容与真实世界脱节），"
          "所以正确的用法是<strong>双轨</strong>：<em>录制回放用于回归门禁（要可复现），"
          "定期的真实联网小样本用于校验录制是否已经失真</em>（呼应模块 01 的离线-在线取舍）。"),
    ])),

    # ============================================================== 6
    ("eval-card", "评测卡：一份完整报告的最小集合", "".join([
        P("把模块 02、04、05 的报告规范合并，得到一张<strong>评测卡</strong>（eval card）。"
          "它的作用和模型卡类似：<em>让读者在不重跑实验的情况下判断这个数字能不能用</em>。"),
        CODE("""# ════════════════════════════════════════════════════════════
# EVAL CARD · agent-billing-v3 @ 2026-08-28
# ════════════════════════════════════════════════════════════
## 1. 被测对象
model:            claude-sonnet-5 (snapshot 2026-05)
scaffold:         inhouse-harness @ a3f19c2   (loop=reflect, tools=8, max_steps=40)
baseline scaffold: minimal-react @ a3f19c2    ← scaffold 消融的参照

## 2. 任务集
dataset:          billing-tasks v12  (sha256:7d2e…)   N=420  (含 8% 不可能任务)
task provenance:  自建, 2026-06 之后创建, 与训练截止无重叠
scorer:           final_state 不变量检查 + 过程约束断言
scorer alpha/beta: 0.031 / 0.022   (金标准集 n=140)

## 3. 结果
pass^1 (micro):   41.7%  [37.9%, 45.6%]   ← 按任务聚类自举, 2000 次
pass^1 (macro):   38.2%                    ← 与 micro 排序一致
pass@5:           66.3%     pass^5:  18.4%
corrected pass^1: 40.3%  [36.2%, 44.4%]   ← Rogan–Gladen 校正后
n_eff:            861  (N=420 × k=5, ρ=0.68)
MDE (配对):        6.8 个百分点  (α=0.05, power=0.8)

## 4. 成本
$/task (全部):     0.83      $/success:  1.99    ← 后者才是可比的口径
median steps (成功): 11        P90: 34
early-quit rate:   4.1%       loop rate: 6.8%

## 5. 复现指纹
fingerprint:      f2a91b7c   (镜像 sha256:… / 并发 8 / 超时 300s / 重试 2 / 断网)
""" ),
        CALLOUT("warn", "评测卡里最容易被砍掉、但绝对不能砍的三行是："
                        "<strong>① scorer 的 α/β</strong>（没有它，所有数字都可能是系统性偏的）；"
                        "<strong>② MDE</strong>（没有它，「不显著」没有信息量）；"
                        "<strong>③ fingerprint</strong>（没有它，这份报告不可复现）。"
                        "这三行的共同点是：它们都在<em>限制</em>你能从数字里得出的结论，"
                        "所以在追求好看的压力下最先被删掉。"),
    ])),

    # ============================================================== 7
    ("to-decision", "从评测到决策：上线门槛该怎么定", "".join([
        P("最后一步，也是整门课的落点：<strong>这些数字怎么变成「能不能上线」这个二值决策。</strong>"),
        H3("把指标翻译成期望效用"),
        MATH(r"\mathbb{E}[U] = p_{\text{success}} \cdot V_{\text{success}} - p_{\text{fail}} \cdot C_{\text{fail}} - C_{\text{run}}"),
        P("其中 $V_{\\text{success}}$ 是一次成功的业务价值、$C_{\\text{fail}}$ 是一次失败的代价"
          "（包括人工返工、用户流失、可能的赔付）、$C_{\\text{run}}$ 是运行成本。"
          "<strong>上线门槛就是 $\\mathbb{E}[U] > \\mathbb{E}[U_{\\text{现状}}]$。</strong>"),
        TABLE(["场景", "$C_{\\text{fail}}$ 的量级", "需要的成功率门槛", "该用的指标"], [
            ["草稿建议（人来定稿）", "很低——人会改", "低（40% 就有价值）", "pass@k 或 pass^1"],
            ["自动执行、可撤销", "中等——出错要回滚", "中（80%+）", "<strong>pass^k</strong>，$k$ 取一次会话的操作数"],
            ["自动执行、不可撤销（转账、发邮件）", "<strong>极高</strong>", "很高，且必须有人工确认点", "pass^k + 越权/副作用率（模块 03）"],
            ["安全相关", "灾难性", "无论多高都要加保护层", "以上全部 + C69 的攻击面评测"],
        ]),
        CALLOUT("danger", "有一个必须显式说破的推论：<strong>当 $C_{\\text{fail}}$ 很高时，"
                          "提高成功率的边际价值会低于「加一个人工确认点」的价值。</strong>"
                          "换句话说，<em>把 41% 提到 47% 可能远不如「在不可逆操作前停下来问一句」有用</em>。"
                          "评测报告如果只报成功率，会让整个团队一直往「提分」的方向使劲，"
                          "而错过这个在产品上更划算的选项。"),
        H3("三个必须报给决策者的数字"),
        OL([
            "<strong>给定预算下的成功率与其置信区间</strong>——它决定 $p_{\\text{success}}$；",
            "<strong>失败的构成</strong>（模块 03 的七分类）——它决定 $C_{\\text{fail}}$，"
            "因为「没做完」和「做错了还删了东西」的代价差几个数量级；",
            "<strong>每次成功的成本</strong>——它决定 $C_{\\text{run}}$，也决定这件事在规模化后还成不成立。",
        ]),
        P("到这里，本课的闭环就完成了：模块 01 选/建任务集，02 定义并验证判分器，"
          "03 从轨迹里挖归因信息，04 给出可信的不确定度，05 把成本与可复现性钉死并翻译成决策。"
          "<strong>下一步：判分器如果是一个 LLM 呢？那整套「先验证测量仪器」的逻辑要怎么做？——那是 C67。</strong>"),
    ])),
    # ============================================================== 8
    ("cheaper-eval", "评测本身的成本控制：用更少的钱得到同样的结论", "".join([
        P("最后一个实用主题：前面所有内容都在教你把评测做严谨，而严谨通常意味着更贵。"
          "这一节反过来——<strong>在不牺牲结论质量的前提下，把评测成本降下来。</strong>"),
        TABLE(["手段", "怎么做", "省多少", "代价 / 前提"], [
            ["<strong>剔除零信息任务</strong>", "所有候选 agent 都过或都不过的任务，对<em>区分</em>它们贡献 0 bit（模块 01）", "常能省 30%–50% 的运行量", "只对「比较」有效；做回归门禁时这些任务仍然有用（它们检测退化）"],
            ["<strong>分层抽样</strong>", "按难度/子系统分层，从每层抽样而不是全跑", "线性节省", "需要任务元数据；小层要有保底名额"],
            ["<strong>循环与预算早停</strong>", "检出循环即终止（模块 03）", "省掉长尾轨迹的大部分开销", "终止规则必须与最终标签独立（04 模块第 8 节）"],
            ["<strong>缓存</strong>", "同一 (prompt, 模型, 参数) 的结果复用", "重跑时可省 90%+", "<strong>会掩盖非确定性</strong>——测方差时必须关掉缓存"],
            ["<strong>两阶段筛选</strong>", "先用便宜的小任务集粗筛掉明显不行的配置，再用全量任务集精测存活者", "候选多时省得最多", "粗筛的排序必须与精测相关；相关性要先验证过"],
            ["<strong>配对设计</strong>", "同一批任务同时跑两个 agent（模块 04）", "样本量省一半以上", "两者必须共享完全相同的环境快照"],
        ]),
        CALLOUT("warn", "第四条的缓存值得单独警告：<strong>缓存会让你的评测看起来非常稳定，"
                        "而这种稳定是假的</strong>。开着缓存重跑两次得到完全一样的分数，"
                        "说明的不是「结果可复现」，而是「你根本没有重跑」。"
                        "<strong>规则：估计方差、算置信区间、跑 pass^k 时必须关闭缓存；"
                        "只有在做确定性回归对比（配置没变、只想确认没退化）时才开。</strong>"),
        H3("最贵的那一项通常不是算力"),
        P("一个反直觉但普遍的事实：<strong>成熟评测体系里最贵的成本项往往是人力</strong>——"
          "写任务、写判分器、做人工审核、复核 L3 样本（模块 02 第 8 节）。"
          "算力可以线性扩容，人力不行。所以真正的成本优化重点是："),
        OL([
            "<strong>让判分器可复用</strong>：把判分逻辑做成不变量库而不是每个任务一段一次性脚本（模块 02 第 3 节）；",
            "<strong>让任务可生成</strong>：能参数化生成的任务（同一模板换参数）边际成本接近零，"
            "但要小心它们的<em>难度分布过于集中</em>，通常需要与人工任务混合使用；",
            "<strong>让人工只做机器做不了的事</strong>：人不该去判「测试过没过」，"
            "只该去判「这条判分器都拿不准的样本到底算不算成功」——这正是三级流水线的设计目的。",
        ]),
        P("<strong>把这三条做到位，评测的边际成本会从「每次都要投入人力」变成「一次投入、长期复用」</strong>，"
          "而这正是 C68 那门课要展开的主题：把评测从一次性的实验变成一套基础设施。"),
    ])),
]

NB = [
    md("""# 05 · 成本感知评测与 harness 可复现性（成本模型 / 帕累托前沿 / best-of-n / scaffold 2×2 / 指纹 / 评测卡）

目标：把「谁更强」这个没有定义的问题，改写成「给定预算谁更强」，并把 harness 钉死到别人能复现。

本 notebook 你会亲手实现：
1. **成本模型与归一化** —— 四种成本，以及为什么必须报「每次成功的成本」
2. **成本-成功率帕累托前沿** —— 找出被支配的配置，按预算线选配置
3. **best-of-n 的边际收益与陷阱** —— 判分器假阳率如何在大 n 时系统性选出 hack 解
4. **scaffold 2×2 实验** —— 交互项如何翻转「哪个模型更强」的结论
5. **配置指纹与漂移检测** —— 十项清单压成一个哈希，让「不可比较」变成机器可判定
6. **评测卡生成器** —— 从原始结果直接产出一张完整的 eval card

> 心智模型：**agent 的能力不是一个标量，是一条成本-成功率曲线。
> 两条曲线可以相交——所以「哪个模型最强」经常没有答案，而「我们的预算下选哪个」永远有答案。**"""),

    md("""## 1 · 成本模型与归一化"""),

    code("""import math, json, hashlib, itertools
from collections import defaultdict
import numpy as np

PRICE = {'in_per_mtok': 3.0, 'out_per_mtok': 15.0}     # 美元 / 百万 token（示例价）

def task_cost(tokens_in, tokens_out, tool_calls=0, container_sec=0.0,
              price=PRICE, tool_unit=0.0002, container_per_sec=0.00012):
    return (tokens_in / 1e6 * price['in_per_mtok']
            + tokens_out / 1e6 * price['out_per_mtok']
            + tool_calls * tool_unit
            + container_sec * container_per_sec)

def run_costs(rows):
    \"\"\"rows: [{'score':0/1,'tokens_in':..,'tokens_out':..,'tool_calls':..,'container_sec':..}]
    返回三种口径：每任务成本 / 每次成功成本 / 每美元买到的成功数。\"\"\"
    total = sum(task_cost(r['tokens_in'], r['tokens_out'], r['tool_calls'], r['container_sec'])
                for r in rows)
    n_succ = sum(r['score'] for r in rows)
    return {'per_task': total / len(rows),
            'per_success': total / n_succ if n_succ else float('inf'),
            'success_per_dollar': n_succ / total if total else 0.0}

rng = np.random.default_rng(0)

def make_rows(n, p_succ, mean_tok_succ, mean_tok_fail, rng):
    rows = []
    for _ in range(n):
        ok = rng.random() < p_succ
        base = mean_tok_succ if ok else mean_tok_fail
        ti = int(rng.normal(base, base * 0.25))
        rows.append({'score': float(ok), 'tokens_in': max(ti, 100),
                     'tokens_out': max(int(ti * 0.05), 20),
                     'tool_calls': int(max(ti / 4000, 1)), 'container_sec': ti / 900})
    return rows

# A：成功率高、失败时也会硬撑到底   B：成功率低得多、一遇到麻烦就早早放弃
A = make_rows(400, 0.52, 90000, 120000, rng)
B = make_rows(400, 0.22, 80000, 45000, rng)
for name, rows in [('A 稳健', A), ('B 早放弃', B)]:
    c = run_costs(rows)
    print(f"{name:<10} 成功率 {np.mean([r['score'] for r in rows]):.1%} | "
          f"每任务 ${c['per_task']:.3f} | 每次成功 ${c['per_success']:.3f} | "
          f"每美元成功 {c['success_per_dollar']:.2f}")

cA, cB = run_costs(A), run_costs(B)
assert cB['per_task'] < cA['per_task'], 'B 的每任务成本更低（失败得快，一半的钱都没花出去）'
assert cB['per_success'] > cA['per_success'], '但 B 的每次成功成本更高（成功率太低，摊不动）'
print('\\n✅ 两个口径给出相反的结论。「每任务成本」奖励早放弃——这是模块 03 Goodhart 的成本版本。')
print('   报告里唯一可比的口径是「每次成功的成本」。')"""),

    md("""## 2 · 成本-成功率帕累托前沿"""),

    code("""def pareto_front(points):
    \"\"\"points: [(name, cost, success)]。返回不被任何其他点支配的点
    （支配 = 成本更低 且 成功率更高）。\"\"\"
    front = []
    for name, c, s in points:
        dominated = any((c2 <= c and s2 >= s) and (c2 < c or s2 > s)
                        for n2, c2, s2 in points if n2 != name)
        if not dominated:
            front.append((name, c, s))
    return sorted(front, key=lambda t: t[1])

CONFIGS = [
    ('A · haiku + minimal',      0.05, 0.22),
    ('B · haiku + reflect',      0.20, 0.38),
    ('C · sonnet + minimal',     0.42, 0.47),
    ('D · sonnet + reflect',     1.05, 0.58),
    ('E · sonnet + 4 subagents', 4.10, 0.55),     # 更贵却更差 → 被 D 支配
    ('F · haiku + 8 retries',    0.60, 0.35),     # 被 C 支配
    ('G · opus + reflect',      18.00, 0.64),
]
front = pareto_front(CONFIGS)
print('帕累托前沿（按成本升序）:')
for n, c, s in front:
    print(f'  {n:<28} ${c:>6.2f}  {s:.0%}')
dominated = [n for n, c, s in CONFIGS if n not in [f[0] for f in front]]
print(f'\\n被支配（任何预算下都不该选）: {dominated}')
assert 'E · sonnet + 4 subagents' in dominated
assert 'F · haiku + 8 retries' in dominated
print('✅ E 和 F 在任何预算下都不该被选——这类点在真实评测里非常常见，')
print('   通常意味着某个 scaffold 没调好，而不是模型不行。')"""),

    code("""def pick_under_budget(points, budget):
    ok = [(n, c, s) for n, c, s in points if c <= budget]
    return max(ok, key=lambda t: t[2]) if ok else None

def cheapest_for_target(points, target):
    ok = [(n, c, s) for n, c, s in points if s >= target]
    return min(ok, key=lambda t: t[1]) if ok else None

print('按预算选:')
for b in [0.10, 0.50, 2.00, 20.0]:
    print(f'  预算 ${b:>6.2f} → {pick_under_budget(CONFIGS, b)}')
print('\\n按目标选:')
for t in [0.35, 0.50, 0.60]:
    print(f'  目标 {t:.0%} → {cheapest_for_target(CONFIGS, t)}')

# 边际成本：沿前沿往上走，每多 1 个百分点要多花多少钱
print('\\n沿前沿的边际成本（每 +1 个百分点的成功率要多花多少）:')
for (n1, c1, s1), (n2, c2, s2) in zip(front, front[1:]):
    print(f'  {n1[:12]:<12} → {n2[:12]:<12}  ${(c2-c1)/((s2-s1)*100):>7.3f} / 百分点')

assert pick_under_budget(CONFIGS, 0.10)[0].startswith('A')
assert pick_under_budget(CONFIGS, 20.0)[0].startswith('G')
print('\\n✅ 注意最后一行的边际成本——从 D 到 G 每提高一个百分点要花几美元。')
print('   这个数字才是「值不值得换更强模型」这个决策的真正输入。')"""),

    md("""## 3 · best-of-n：边际收益递减，以及判分器假阳率的放大效应"""),

    code("""def pass_at_n(p, n):
    return 1 - (1 - p) ** n

P_SINGLE = 0.35
print(f"{'n':>4}{'pass@n':>10}{'相对成本':>10}{'每+1点的边际成本':>20}")
prev_s, prev_c = P_SINGLE, 1.0
for n in [1, 2, 4, 8, 16, 32]:
    s, c = pass_at_n(P_SINGLE, n), float(n)
    marg = (c - prev_c) / ((s - prev_s) * 100) if n > 1 and s > prev_s else float('nan')
    print(f'{n:>4}{s:>10.1%}{c:>10.1f}x{marg:>19.3f}')
    prev_s, prev_c = s, c

assert pass_at_n(P_SINGLE, 2) - pass_at_n(P_SINGLE, 1) > \\
       pass_at_n(P_SINGLE, 32) - pass_at_n(P_SINGLE, 16)
print('\\n✅ 从 1 到 2 涨 12 个点，从 16 到 32 只涨不到 1 个点，而成本翻倍。')"""),

    code("""def bon_with_imperfect_verifier(p_true, n, alpha, rng, trials=5000):
    \"\"\"验证器有假阳率 alpha（把失败解判成成功）。best-of-n 会挑第一个被判成功的候选。
    返回 (被判成功的比例, 在被判成功的样本中真正正确的比例)。\"\"\"
    picked, correct = 0, 0
    for _ in range(trials):
        real = rng.random(n) < p_true                 # 每个候选是否真的正确
        judged = np.where(real, True, rng.random(n) < alpha)   # 验证器判定（真解一律判对）
        if judged.any():
            picked += 1
            idx = int(np.argmax(judged))              # 取第一个被判成功的
            correct += bool(real[idx])
    return picked / trials, (correct / picked if picked else float('nan'))

rng = np.random.default_rng(3)
print(f"{'n':>4}{'验证器说成功':>14}{'其中真正正确':>14}{'真实成功率':>12}")
for n in [1, 2, 4, 8, 16, 32]:
    sel, prec = bon_with_imperfect_verifier(0.35, n, alpha=0.05, rng=rng)
    print(f'{n:>4}{sel:>14.1%}{prec:>14.1%}{sel*prec:>12.1%}')

sel1, prec1 = bon_with_imperfect_verifier(0.35, 1, 0.05, rng)
sel32, prec32 = bon_with_imperfect_verifier(0.35, 32, 0.05, rng)
assert abs(prec32 - prec1) < 0.05, '被选中解的精确率恒为 p/q，与 n 无关'
assert sel32 > sel1
gap1, gap32 = sel1 * (1 - prec1), sel32 * (1 - prec32)
print(f'\\n✅ 精确率恒为 p/q ≈ {prec1:.0%}，与 n 无关；')
print(f'   但验证器报出的成功率从 {sel1:.0%} 一路涨到 {sel32:.0%}（看起来很棒）。')
print(f'   两者之差就是被系统性引入的假阳解：n=1 时占 {gap1:.1%}，n=32 时占 {gap32:.1%}。')
assert gap32 > gap1
print('   **n 越大，你交付出去的"成功"里越多是判分器的假阳解**——')
print('   这就是 reward hacking 在评测侧的同构现象（C67-05 会从奖励模型角度重讲）。')"""),

    md("""## 4 · scaffold 2×2 实验：交互项如何翻转结论"""),

    code("""# 两个模型 × 两个 scaffold。真值由一个「模型能力 + scaffold 加成 + 交互项」的模型生成。
TRUTH = {
    ('model_A', 'minimal'): 0.30,
    ('model_A', 'reflect'): 0.52,       # A 从反思循环里获益极大
    ('model_B', 'minimal'): 0.38,
    ('model_B', 'reflect'): 0.44,       # B 获益有限（它本来就会自我检查）
}

def run_cell(p, N=600, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.random(N) < p).astype(float)

cells = {key: run_cell(v, seed=100 + i) for i, (key, v) in enumerate(sorted(TRUTH.items()))}
print(f"{'':<10}{'minimal':>10}{'reflect':>10}")
for m in ['model_A', 'model_B']:
    print(f"{m:<10}{cells[(m,'minimal')].mean():>10.1%}{cells[(m,'reflect')].mean():>10.1%}")

winner_minimal = 'model_A' if cells[('model_A', 'minimal')].mean() > cells[('model_B', 'minimal')].mean() else 'model_B'
winner_reflect = 'model_A' if cells[('model_A', 'reflect')].mean() > cells[('model_B', 'reflect')].mean() else 'model_B'
print(f'\\nminimal scaffold 下的赢家: {winner_minimal}')
print(f'reflect scaffold 下的赢家: {winner_reflect}')
assert winner_minimal != winner_reflect
print('\\n✅ 换一套 scaffold，「哪个模型更强」的结论直接翻转。')
print('   只报一个 scaffold 下的分数，等于在报告一个由你自己的实现决定的结论。')"""),

    code("""# 效应分解：主效应 vs 交互项
def effects(cells):
    a_min, a_ref = cells[('model_A', 'minimal')].mean(), cells[('model_A', 'reflect')].mean()
    b_min, b_ref = cells[('model_B', 'minimal')].mean(), cells[('model_B', 'reflect')].mean()
    model_effect = ((a_min + a_ref) - (b_min + b_ref)) / 2
    scaffold_effect = ((a_ref + b_ref) - (a_min + b_min)) / 2
    interaction = (a_ref - a_min) - (b_ref - b_min)
    return model_effect, scaffold_effect, interaction

me, se, ix = effects(cells)
print(f'模型主效应 (A - B)      {me:+.1%}')
print(f'scaffold 主效应 (ref-min) {se:+.1%}')
print(f'交互项                  {ix:+.1%}')
assert abs(se) > abs(me), 'scaffold 的主效应大于模型的主效应'
assert abs(ix) > abs(me), '交互项也大于模型主效应'
print('\\n✅ scaffold 的效应和交互项都大于模型主效应——')
print('   这就是「agent 基准测的是「模型+你写的那个程序」的组合」这句话的定量形式。')
print('   报告规范：至少给出一个最简 baseline scaffold 下的分数作为参照。')"""),

    md("""## 5 · 配置指纹与漂移检测"""),

    code("""REPRO_FIELDS = [
    'image_digest', 'dataset_hash', 'scaffold_commit', 'model_id',
    'temperature', 'max_steps', 'max_tokens', 'timeout_s', 'retries',
    'concurrency', 'network_policy', 'scorer_commit', 'n_tasks', 'k_attempts',
    'aggregation', 'ci_method',
]

def fingerprint(cfg):
    missing = [f for f in REPRO_FIELDS if f not in cfg]
    if missing:
        raise ValueError(f'配置缺失字段，无法生成指纹: {missing}')
    payload = json.dumps({f: cfg[f] for f in REPRO_FIELDS}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:8]

BASE = {'image_digest': 'sha256:9a1c', 'dataset_hash': 'sha256:7d2e',
        'scaffold_commit': 'a3f19c2', 'model_id': 'claude-sonnet-5@2026-05',
        'temperature': 0.0, 'max_steps': 40, 'max_tokens': 200000,
        'timeout_s': 300, 'retries': 2, 'concurrency': 8,
        'network_policy': 'offline', 'scorer_commit': 'b71d0e4',
        'n_tasks': 420, 'k_attempts': 5, 'aggregation': 'micro',
        'ci_method': 'cluster_bootstrap'}

fp_base = fingerprint(BASE)
print('baseline 指纹:', fp_base)
for change in [{'concurrency': 16}, {'max_steps': 60}, {'model_id': 'claude-sonnet-5@2026-08'},
               {'aggregation': 'macro'}]:
    cfg = dict(BASE, **change)
    print(f'  改 {list(change)[0]:<16} → {fingerprint(cfg)}  '
          f'{"⚠️ 不可与 baseline 直接比较" if fingerprint(cfg) != fp_base else ""}')

assert fingerprint(BASE) == fingerprint(dict(BASE))
try:
    fingerprint({k: v for k, v in BASE.items() if k != 'concurrency'})
    raise AssertionError('缺字段时应当报错')
except ValueError as e:
    print(f'\\n缺字段时正确报错: {str(e)[:46]}…')
print('✅ 指纹机制让「不可比较」变成机器可判定的——')
print('   C68 的 CI 门禁里这直接是一行 assert，而不是让人肉眼核对配置。')"""),

    code("""def drift_alarm(runs, tol=0.05):
    \"\"\"同指纹的多次运行，分数差异超过 tol 就是告警——说明还有没被记录的变量在动。\"\"\"
    by_fp = defaultdict(list)
    for r in runs:
        by_fp[r['fingerprint']].append(r['score'])
    alarms = []
    for fp, scores in by_fp.items():
        if len(scores) > 1 and (max(scores) - min(scores)) > tol:
            alarms.append((fp, min(scores), max(scores), max(scores) - min(scores)))
    return alarms

RUNS = [
    {'fingerprint': fp_base, 'score': 0.417},
    {'fingerprint': fp_base, 'score': 0.424},
    {'fingerprint': fp_base, 'score': 0.489},        # ← 同配置却高出 7 个点
    {'fingerprint': 'deadbeef', 'score': 0.512},
]
al = drift_alarm(RUNS)
for fp, lo, hi, d in al:
    print(f'⚠️ 指纹 {fp} 的多次运行分数从 {lo:.1%} 到 {hi:.1%}（差 {d:.1%}）——存在未记录的变量')
assert len(al) == 1
print('\\n✅ 这类告警的常见根因：外部 API 行为变了、容器所在机器负载不同导致超时数变了、')
print('   或者某个「以为是常量」的东西其实读了环境变量。指纹机制让它们暴露出来。')"""),

    md("""## 6 · 评测卡生成器"""),

    code("""def eval_card(name, cfg, X, rows, alpha_beta, baseline_scaffold_score=None):
    \"\"\"从原始结果直接产出一张 eval card（字典形式，print 出来就是报告）。\"\"\"
    X = np.asarray(X, dtype=float)
    N, k = X.shape
    task_means = X.mean(axis=1)
    vb = float(np.var(task_means, ddof=1))
    vw = float(np.mean(task_means * (1 - task_means)))
    rho = vb / (vb + vw) if (vb + vw) > 0 else 0.0
    n_eff = N * k / (1 + (k - 1) * rho)
    rng = np.random.default_rng(0)
    boots = [X[rng.integers(0, N, N)].mean() for _ in range(1500)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    a, b = alpha_beta
    p_obs = float(X.mean())
    corrected = (p_obs - a) / (1 - b - a)
    costs = run_costs(rows)
    return {
        'name': name,
        'fingerprint': fingerprint(cfg),
        'N_tasks': N, 'k_attempts': k,
        'pass1_micro': round(p_obs, 4),
        'ci95': (round(float(lo), 4), round(float(hi), 4)),
        'scorer_alpha_beta': (a, b),
        'pass1_corrected': round(corrected, 4),
        'n_eff': round(n_eff, 1), 'rho': round(rho, 3),
        'usd_per_task': round(costs['per_task'], 4),
        'usd_per_success': round(costs['per_success'], 4),
        'baseline_scaffold_pass1': baseline_scaffold_score,
    }

rng = np.random.default_rng(8)
Xdemo = (rng.random((420, 5)) < rng.beta(1.2, 1.6, size=(420, 1))).astype(float)
card = eval_card('agent-billing-v3', BASE, Xdemo, A, alpha_beta=(0.031, 0.022),
                 baseline_scaffold_score=0.301)
print('# ═════════ EVAL CARD ═════════')
for kk, vv in card.items():
    print(f'{kk:<26} {vv}')

assert card['pass1_corrected'] < card['pass1_micro'], '假阳率 > 假阴率时，校正后应下降'
assert card['n_eff'] <= 420 * 5
assert card['usd_per_success'] >= card['usd_per_task']
print('\\n✅ 这张卡里最容易被砍掉、也最不能砍的三行：scorer_alpha_beta / n_eff / fingerprint。')
print('   它们的共同点是「限制你能从数字里得出的结论」——所以在追求好看的压力下最先被删。')"""),

    md("""## ✏️ 练习 1：等预算下的公平对比

实现 `equalize_budget(configs, budget)`：`configs` 是 `[(name, cost_per_run, p_single)]`，
在总预算 `budget` 下，每个配置能跑 `n = floor(budget / cost_per_run)` 次 best-of-n，
返回 `[(name, n, pass_at_n)]` 按 pass@n 降序。这才是「同样的钱谁更强」。"""),

    code("""def equalize_budget(configs, budget):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
CFG = [('cheap_weak', 0.05, 0.22), ('mid', 0.42, 0.47), ('expensive_strong', 4.00, 0.62)]
res = equalize_budget(CFG, budget=4.00)
print('预算 $4.00 时:')
for n_, k_, s_ in res:
    print(f'  {n_:<20} 可跑 {k_:>3} 次 → pass@n {s_:.1%}')
assert res == sorted(res, key=lambda t: -t[2]), '返回必须按 pass@n 降序'
assert res[0][0] == 'cheap_weak', '小预算下，便宜模型靠多跑几次反超'
res2 = equalize_budget(CFG, budget=0.50)
print(f'\\n预算 $0.50 时的赢家: {res2[0][0]} (pass@n {res2[0][2]:.1%})')
assert dict((r[0], r[1]) for r in res)['expensive_strong'] == 1
print('✅ 练习 1 通过：等预算下，便宜模型的 best-of-n 可以反超贵模型的单次运行——')
print('   前提是你有验证器。没有验证器的话这个反超是幻觉（第 3 节）。')"""),

    md("""## ✏️ 练习 2：帕累托前沿的支配关系检查

实现 `dominates(p, q)`：`p, q` 均为 `(name, cost, success)`，
当 `p` 的成本 ≤ `q` 且成功率 ≥ `q`，且至少一项严格更优时返回 True。
再实现 `dominated_by(point, points)` 返回所有支配它的点的名字列表。"""),

    code("""def dominates(p, q):
    # TODO
    raise NotImplementedError

def dominated_by(point, points):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
p1 = ('X', 1.0, 0.50); p2 = ('Y', 2.0, 0.40); p3 = ('Z', 1.0, 0.50)
assert dominates(p1, p2) is True
assert dominates(p2, p1) is False
assert dominates(p1, p3) is False          # 完全相同 → 互不支配
e = ('E · sonnet + 4 subagents', 4.10, 0.55)
doms = dominated_by(e, CONFIGS)
print(f'支配 E 的配置: {doms}')
assert 'D · sonnet + reflect' in doms
assert dominated_by(('G · opus + reflect', 18.00, 0.64), CONFIGS) == []
print('✅ 练习 2 通过：G 最贵但没人支配它（它也最准）——')
print('   前沿上的点都不被支配，选哪个取决于预算线，不取决于「谁分数最高」。')"""),

    md("""## ✏️ 练习 3：判分器假阳率下 best-of-n 的真实收益

实现 `true_bon_success(p_true, n, alpha)`：解析地算出
「验证器判为成功」的概率与「被选中的解真正正确」的概率之积，即真实成功率。

提示：验证器判某个候选成功的概率 $q = p + (1-p)\\alpha$；
$n$ 个候选至少一个被判成功的概率 $1-(1-q)^n$；
在被判成功的候选中，真正正确的比例是 $p / q$（对每个候选独立成立，
因此第一个被判成功的候选正确的条件概率也是 $p/q$）。"""),

    code("""def true_bon_success(p_true, n, alpha):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert abs(true_bon_success(0.35, 1, 0.0) - 0.35) < 1e-12
assert abs(true_bon_success(0.35, 1, 0.05) - 0.35) < 1e-12    # n=1 时假阳不改变真实成功率
print(f"{'n':>4}{'α=0':>10}{'α=0.05':>10}{'α=0.20':>10}")
for n in [1, 2, 4, 8, 16, 32]:
    print(f'{n:>4}', end='')
    for a_ in [0.0, 0.05, 0.20]:
        print(f'{true_bon_success(0.35, n, a_):>10.1%}', end='')
    print()
assert true_bon_success(0.35, 32, 0.20) < true_bon_success(0.35, 32, 0.0)
gap = true_bon_success(0.35, 32, 0.0) - true_bon_success(0.35, 32, 0.20)
assert gap > 0.2
print(f'\\nn=32 时，α 从 0 涨到 0.20 让真实成功率掉了 {gap:.0%}')
print('✅ 练习 3 通过：best-of-n 的收益完全建立在验证器质量上——')
print('   验证器越差，n 越大，你挑出来的越可能是假阳解。')"""),

    md("""## ✏️ 练习 4：上线决策的期望效用

实现 `expected_utility(p_success, v_success, c_fail, c_run)`：
返回 $p \\cdot V - (1-p)\\cdot C_{fail} - C_{run}$。
再实现 `min_success_for_launch(v_success, c_fail, c_run, baseline_utility=0.0)`：
反解上线所需的最低成功率，结果夹到 $[0,1]$。"""),

    code("""def expected_utility(p_success, v_success, c_fail, c_run):
    # TODO
    raise NotImplementedError

def min_success_for_launch(v_success, c_fail, c_run, baseline_utility=0.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
assert abs(expected_utility(1.0, 10, 50, 1) - 9.0) < 1e-12
assert abs(expected_utility(0.0, 10, 50, 1) + 51.0) < 1e-12
p_need = min_success_for_launch(v_success=10, c_fail=50, c_run=1)
assert abs(expected_utility(p_need, 10, 50, 1)) < 1e-9
print(f"{'场景':<28}{'C_fail':>9}{'上线门槛':>12}")
for label, cf in [('草稿建议（人来定稿）', 2), ('自动执行、可撤销', 50), ('自动执行、不可撤销', 500)]:
    print(f'{label:<28}{cf:>9}{min_success_for_launch(10, cf, 1):>12.1%}')
assert min_success_for_launch(10, 500, 1) > min_success_for_launch(10, 2, 1)
assert min_success_for_launch(10, 500, 20) == 1.0   # 运行成本 > 一次成功的价值 → 任何成功率都不划算
print(f'\\n运行成本(20) 超过一次成功的价值(10) 时的门槛: '
      f'{min_success_for_launch(10, 500, 20):.0%}（夹到上限）')
print('✅ 练习 4 通过：门槛随失败代价急剧上升——不可撤销场景要到 98%，')
print('   而当运行成本本身就超过一次成功的价值时，门槛被夹到 100%，')
print('   意思是「靠提高成功率解决不了」：要么降成本，要么加人工确认点。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def equalize_budget(configs, budget):
    out = []
    for name, cost, p in configs:
        n = max(int(budget // cost), 1)
        out.append((name, n, pass_at_n(p, n)))
    return sorted(out, key=lambda t: -t[2])"""),

    code("""# 练习 2 参考答案
def dominates(p, q):
    return (p[1] <= q[1] and p[2] >= q[2]) and (p[1] < q[1] or p[2] > q[2])

def dominated_by(point, points):
    return [n for n, c, s in points if n != point[0] and dominates((n, c, s), point)]"""),

    code("""# 练习 3 参考答案
def true_bon_success(p_true, n, alpha):
    q = p_true + (1 - p_true) * alpha        # 单个候选被判为成功的概率
    if q <= 0:
        return 0.0
    p_any_judged = 1 - (1 - q) ** n
    precision = p_true / q                    # 被判成功的候选里真正正确的比例
    return p_any_judged * precision"""),

    code("""# 练习 4 参考答案
def expected_utility(p_success, v_success, c_fail, c_run):
    return p_success * v_success - (1 - p_success) * c_fail - c_run

def min_success_for_launch(v_success, c_fail, c_run, baseline_utility=0.0):
    # p*V - (1-p)*C_fail - C_run = baseline  →  p*(V + C_fail) = baseline + C_run + C_fail
    denom = v_success + c_fail
    if denom <= 0:
        return 1.0
    p = (baseline_utility + c_run + c_fail) / denom
    return float(min(1.0, max(0.0, p)))"""),

    md("""---
## 🧪 真实工程胶囊：可复现评测的落地骨架"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 钉死容器：永远用 digest，永远不用 tag
# ══════════════════════════════════════════════════════════════════
# ✗ docker run swebench/eval:latest
# ✓ docker run swebench/eval@sha256:9a1c7f...   ← digest 不可变
# 取 digest:  docker inspect --format='{{index .RepoDigests 0}}' <image>
# 在评测配置里存 digest，并在每条结果记录里带上它。

# ══════════════════════════════════════════════════════════════════
# B. 并发度是 harness 的一部分（最常被忽略的一条）
# ══════════════════════════════════════════════════════════════════
# 高并发 → 容器争抢 CPU → 测试跑得慢 → 更多任务撞上 timeout → 分数下降。
# 复现清单里必须写 concurrency，并且做一次敏感性检查：
#   for c in [1, 4, 8, 16]:
#       run_eval(..., concurrency=c)      # 分数随 c 变化 = 你的 timeout 设得太紧
# 分数对并发不敏感，才说明 timeout 有足够余量。

# ══════════════════════════════════════════════════════════════════
# C. 网络：录制回放
# ══════════════════════════════════════════════════════════════════
# pip install vcrpy
import vcr
my_vcr = vcr.VCR(record_mode="once", match_on=["method", "scheme", "host", "path", "query"],
                 filter_headers=["authorization", "x-api-key"])   # ← 千万别把密钥录进去
with my_vcr.use_cassette("cassettes/task_017.yaml"):
    run_agent(task_017)
# 双轨制：录制回放跑回归门禁（可复现），每周一次真实联网小样本校验录制没失真。

# ══════════════════════════════════════════════════════════════════
# D. 每条结果记录的最小字段（够算出本课全部指标）
# ══════════════════════════════════════════════════════════════════
RESULT_ROW = {
  "run_id": "...", "fingerprint": "f2a91b7c",
  "task_id": "...", "attempt": 0,
  "score": 1, "scorer_version": "b71d0e4",
  "steps": 14, "tokens_in": 51230, "tokens_out": 2210,
  "tool_calls": 12, "container_sec": 61.2, "wall_ms": 41200,
  "failure_class": None,          # 模块 03 的七分类
  "terminated_by": None,          # loop_detector | budget | timeout | done
}

# ══════════════════════════════════════════════════════════════════
# E. 报告前的自检清单（六个 yes 才能发出去）
# ══════════════════════════════════════════════════════════════════
# [ ] 判分器的 alpha/beta 量过了吗？（模块 02）
# [ ] N 和 k 分开写了吗？CI 用的是聚类自举吗？（模块 04）
# [ ] MDE 写了吗？（模块 04）
# [ ] 成本报的是 per_success 而不是 per_task 吗？（本模块）
# [ ] baseline scaffold 的分数给了吗？（本模块第 4 节）
# [ ] fingerprint 写进报告了吗？（本模块第 5 节）
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 成本是一等公民 | 不带预算的「谁更强」没有定义 | 任何模型对比 |
| 归一化口径 | 报 `$/success` 而不是 `$/task`——后者奖励早放弃 | 报告规范 |
| 帕累托前沿 | 被支配的配置在任何预算下都不该选 | 模型选型 |
| best-of-n | 收益急剧递减，且对判分器假阳率极度敏感 | 决定要不要多采样 |
| scaffold 2×2 | scaffold 效应与交互项常大于模型主效应 | 实验设计 |
| 十项复现清单与指纹 | 让「不可比较」变成机器可判定的 | CI 门禁（C68） |
| 期望效用 | 失败代价高时，加人工确认点比提分更划算 | 上线决策 |

**全课到此闭环**：01 选/建任务集 → 02 定义并验证判分器 → 03 从轨迹挖归因 →
04 给出可信的不确定度 → 05 钉死成本与可复现性并翻译成决策。

**下一门课**：判分器如果本身是一个 LLM 呢？「先验证测量仪器」这套逻辑要怎么执行？——**C67 · LLM-as-a-Judge 与评分模型**。""")
]
