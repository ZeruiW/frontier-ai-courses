# -*- coding: utf-8 -*-
"""C68 模块 04 · CI 回归门禁。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 03（结果存储与 run diff）；"
                 "C66 模块 04（方差、MDE、配对检验）读过更好，但本模块会复述必要的部分"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_ci_gating.ipynb'
                       '（用重复运行的方差推导门禁阈值 / 误报率与漏报率的权衡曲线 / '
                       '两级门禁：smoke 快检 + full 慢检 / 配对门禁 vs 绝对阈值门禁 / '
                       '告警疲劳的模拟：误报如何让门禁被关掉 / 金丝雀与分阶段放行）'),
    ("核心参考", "Google, <em>Testing on the Toilet</em> 与 flaky test 治理实践 · "
                 "Continuous Delivery 的门禁分层思想 · "
                 "Wald 序贯概率比检验（SPRT，用于早停判定）· "
                 "本课程 C66 模块 04（MDE 与配对设计）· C10 模块 07（在线 A/B）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("failure-mode", "门禁的终极失败模式：被关掉", "".join([
        P("先说结论，因为它决定了本模块所有的设计取向：<strong>一个评测门禁最可能的死法，"
          "不是漏掉了真实退化，而是误报太多以至于团队把它关掉了。</strong>"),
        ASCII("""
   门禁的生命周期（最常见的那条）
   ┌────────────────────────────────────────────────────────────┐
   │ 第 1 周   上线，阈值拍脑袋定成「掉 2% 就阻断」              │
   │ 第 2 周   开始零星误报，大家手动 override                   │
   │ 第 4 周   误报变成常态，override 成了肌肉记忆                │
   │ 第 6 周   有人说「这个门禁总是乱报」→ 改成只警告不阻断        │
   │ 第 8 周   警告没人看                                        │
   │ 第 12 周  一个真实退化上线了，而门禁**当时确实报了**         │
   └────────────────────────────────────────────────────────────┘
   教训：**门禁的可信度是一种会被消耗的资源。**
"""),
        DUAL(
            "所以门禁设计的第一原则不是「尽可能敏感」，而是<strong>「误报率必须低到人们愿意相信它」</strong>。"
            "<em>一个每周误报一次的门禁，在第四次误报之后就不再是门禁了</em>——"
            "它变成了一个需要被绕过的障碍。"
            "<strong>而漏报的代价是有限的（下一道防线还在），误报的代价是复利的（信任被持续消耗）。</strong>",
            "形式化地说，门禁是一个假设检验：$H_0$「没有退化」vs $H_1$「有退化」。"
            "常规统计里我们通常固定 $\\alpha = 0.05$；"
            "<strong>但 CI 门禁的场景要求 $\\alpha$ 显著更低</strong>，"
            "因为它每天要被执行几十次——"
            "<em>$\\alpha = 0.05$ 意味着每 20 次提交就有一次误报，一周下来就是好几次</em>。"
            "把「每次运行的误报率」换算成「每周的误报次数」，是设定阈值时唯一有意义的口径。"
            "本模块 notebook 第 2 节会把这个换算做出来。",
        ),
        CALLOUT("intuition", "一条可以直接用的目标：<strong>把误报频率定在「每月至多一次」</strong>。"
                             "<em>按每天 20 次 CI 运行算，这对应单次误报率约 $1/400 = 0.25\\%$</em>——"
                             "比常规的 5% 严格 20 倍。"
                             "<strong>这个约束会直接推出你需要多大的样本量和多宽的阈值</strong>，"
                             "而不是反过来「先定阈值再看误报多不多」。"),
    ])),

    # ============================================================== 2
    ("threshold-from-variance", "阈值必须从方差推出来，不能拍脑袋", "".join([
        P("模块 00 的反模式清单第六条是「CI 门禁阈值拍脑袋定」。这一节给出替代方案。"),
        H3("三步法"),
        OL([
            "<strong>测噪声</strong>：<em>用同一个配置、同一份任务集，重复跑 $R$ 次</em>"
            "（$R \\ge 10$），得到分数的标准差 $\\sigma_{\\text{run}}$。"
            "<strong>这一步是不可跳过的</strong>——没有它，后面全是猜。",
            "<strong>定误报预算</strong>：把「每月至多一次误报」换算成单次误报率 $\\alpha$。",
            "<strong>算阈值</strong>：$\\text{threshold} = z_{\\alpha} \\cdot \\sigma_{\\text{run}} \\cdot \\sqrt{2}$"
            "（$\\sqrt{2}$ 是因为「当前」与「基线」两次运行都有噪声）。",
        ]),
        MATH(r"\text{threshold} = z_{\alpha}\,\sigma_{\text{run}}\sqrt{2}, \qquad \alpha = \frac{1}{\text{每月运行次数}}"),
        TABLE(["$\\sigma_{\\text{run}}$", "每天 20 次 CI 的阈值（月误报 1 次）", "能检出的最小退化", "评价"], [
            ["0.5 个点", "±1.9 个点", "≥ 2 个点", "<strong>健康</strong>：噪声小，门禁灵敏"],
            ["1.5 个点", "±5.8 个点", "≥ 6 个点", "勉强：只能抓大退化"],
            ["3.0 个点", "±11.6 个点", "≥ 12 个点", "<strong>门禁基本没用</strong>：先去降噪，别调阈值"],
        ]),
        CALLOUT("danger", "最后一行是本节最重要的一条：<strong>当噪声大到阈值必须放宽到十几个点时，"
                          "正确的动作不是「接受这个宽阈值」，而是去降噪</strong>——"
                          "增加样本量、固定温度、增加重复次数、改用配对门禁（第 4 节）。"
                          "<em>一个只能检出 12 个点退化的门禁，几乎不可能抓到任何真实问题，"
                          "它的存在只是给人一种「我们有门禁」的错觉。</em>"),
        H3("降噪的四条路径，按性价比排序"),
        UL([
            "<strong>配对门禁</strong>（第 4 节）——把任务难度这个最大的方差源消掉，通常能把 $\\sigma$ 砍掉一半以上，"
            "<em>而且是零额外成本</em>；",
            "<strong>temperature = 0</strong>——消掉采样随机性；代价是失去了对随机性的覆盖；",
            "<strong>增加重复次数 $k$</strong>——方差降到 $\\sigma_b^2/N + \\sigma_w^2/(Nk)$，"
            "<em>有天花板</em>（C66-04）；",
            "<strong>增加任务数 $N$</strong>——两项一起降，但 smoke 集要跑得快，这条有上限。",
        ]),
    ])),

    # ============================================================== 3
    ("what-to-gate", "什么该阻断、什么只该警告", "".join([
        P("不是所有异常都该拦住合并。<strong>门禁分级是降低误报感知的关键手段</strong>——"
          "把「必须停」和「值得看一眼」分开，前者才有资格打断人。"),
        TABLE(["级别", "触发条件", "动作", "为什么是这一级"], [
            ["<strong>BLOCK 阻断</strong>", "① 完整性校验失败（模块 03）<br>② 指纹与基线不可比（模块 01）<br>③ 分数低于绝对下限<br>④ <strong>安全/合规类断言失败</strong>", "阻止合并", "这四类<strong>不涉及统计判断</strong>——它们是确定性的，误报率天然为零"],
            ["<strong>BLOCK（统计）</strong>", "配对检验 p &lt; α 且 净退化 ≥ MDE", "阻止合并", "<strong>唯一一类基于统计的阻断</strong>，阈值必须从方差推出"],
            ["<strong>WARN 警告</strong>", "分数下降但不显著；churn 异常高；成本上升 &gt; 20%", "在 PR 上留言，不阻断", "值得看一眼，但不足以停下所有人"],
            ["<strong>INFO</strong>", "切片变化、延迟变化、缓存命中率", "写进报告", "诊断用"],
        ]),
        CALLOUT("intuition", "第一行值得特别强调：<strong>那四类阻断条件全都是确定性的，不涉及任何统计推断</strong>——"
                             "「数据集版本不一致」「行数对不上」「指纹与基线不同」"
                             "「模型输出了不该输出的东西」，这些要么是要么不是。"
                             "<em>它们的误报率天然为零，所以它们是门禁里最可信、也最该优先建设的部分</em>。"
                             "<strong>很多团队一上来就去调统计阈值，"
                             "却没有先把这些零误报的确定性检查建起来——顺序反了。</strong>"),
        H3("绝对下限：一个便宜的兜底"),
        P("模块 01 的 datasheet 里有一条「预期分数区间」。它在门禁里的用法很直接："
          "<strong>分数掉出这个区间就阻断，无论统计上显不显著。</strong>"
          "<em>这条能抓住「判分器坏了」「任务集被换成了 smoke」「答案泄漏进 prompt」"
          "这类流水线事故——它们造成的分数变化通常是灾难性的，不需要统计检验就能看出来。</em>"),
        P("同样地，<strong>分数异常<em>升高</em>也应当触发检查</strong>。"
          "一个预期 30–50% 的任务集突然跑出 95%，几乎肯定是流水线出了问题。"
          "<em>「只在分数下降时告警」是一个非常常见、但会漏掉整整一类事故的设计。</em>"),
    ])),

    # ============================================================== 4
    ("paired-gating", "配对门禁：零成本地把噪声砍一半", "".join([
        P("这是本模块投入产出比最高的一条工程建议。"),
        DUAL(
            "绝对阈值门禁问的是：「这次的分数 $s_{\\text{new}}$ 比基线分数 $s_{\\text{base}}$ 低多少？」"
            "——这里面混着<strong>任务难度的波动</strong>（如果任务集有任何变化）和"
            "<strong>两次运行各自的采样噪声</strong>。"
            "配对门禁问的是：「<em>在同一批任务上</em>，有多少题从对变错了、多少题从错变对了？」"
            "<strong>任务难度对两边是同一个数，做差时直接消掉。</strong>",
            "形式化：绝对差的方差是 $\\operatorname{Var}(s_A) + \\operatorname{Var}(s_B)$；"
            "配对差的方差是 $\\operatorname{Var}(s_A) + \\operatorname{Var}(s_B) - 2\\operatorname{Cov}(s_A, s_B)$。"
            "<strong>由于两次运行在同一批任务上高度正相关（难题对谁都难），"
            "$\\operatorname{Cov}$ 项很大</strong>，配对差的方差远小于绝对差。"
            "<em>在二值结果下这直接退化为 McNemar 检验：只有 fixed 与 regressed 这两类"
            "不一致对携带信息，一致对（都对/都错）完全不贡献</em>"
            "——这正是 C66 模块 04 与本课模块 03 已经出现过两次的同一个结构。",
        ),
        TABLE(["门禁类型", "看什么", "$\\sigma$ 的量级", "前提条件"], [
            ["<strong>绝对阈值</strong>", "$s_{\\text{new}} - s_{\\text{base}}$", "基准", "无"],
            ["<strong>配对</strong>", "fixed / regressed 的差", "<strong>通常只有一半或更小</strong>", "两次运行必须跑<strong>同一批任务</strong>（模块 03 的任务集一致性检查）"],
            ["配对 + 多次重复", "任务内均值的配对差", "更小", "同上 + 记录了 attempt"],
        ]),
        CALLOUT("warn", "配对门禁有一个必须自动检查的前提：<strong>两次运行的任务集必须完全相同。</strong>"
                        "<em>如果基线跑了 500 条而当前只跑了 487 条（13 条超时被跳过），"
                        "那么「配对」就名不副实</em>——而且被跳过的那些通常是最难的，"
                        "<strong>这会系统性地让当前运行看起来更好</strong>。"
                        "所以模块 03 练习 2 的 <code>same_task_set</code> 必须作为配对门禁的前置断言。"),
        H3("regression-only 门禁：只看退化，不看净变化"),
        P("还有一个更严格、也更符合 CI 语义的变体：<strong>只要 regressed 超过阈值就阻断，"
          "不管 fixed 有多少。</strong>"),
        P("理由是：<em>CI 门禁的职责是「防止把东西弄坏」，不是「确认变好了」</em>。"
          "一个「修好 50 道、弄坏 30 道」的改动，净变化是 +20，"
          "但那 30 道退化可能包含核心路径。"
          "<strong>把 regressed 单独设一个阈值，并要求作者逐条解释，"
          "比看净变化更符合 CI 的目的</strong>——"
          "<em>而且这个规则本身也是零统计假设的，误报率只取决于噪声下的自发翻转率。</em>"),
    ])),

    # ============================================================== 5
    ("two-tier", "两级门禁：smoke 快检 + full 慢检", "".join([
        P("成本与灵敏度是矛盾的：跑得快就样本少、噪声大、只能抓大退化。"
          "标准解法是分两级。"),
        ASCII("""
   每次提交                      合并前 / 每日定时
   ┌─────────────────────┐      ┌──────────────────────────┐
   │ SMOKE               │      │ FULL                     │
   │ 60 条 × 1 次        │      │ 500 条 × 3 次            │
   │ 3-5 分钟            │      │ 1-3 小时                 │
   │ σ ≈ 3-5 个点        │      │ σ ≈ 0.5-1 个点           │
   │                     │      │                          │
   │ 抓: 崩了/大退化      │      │ 抓: 2-3 个点的真实退化    │
   │     确定性检查全套   │      │     统计门禁 + 切片分析   │
   └─────────────────────┘      └──────────────────────────┘
   关键: smoke 的**统计阈值要设得很宽**（甚至不设），
         主要靠**确定性检查**（第 3 节第一行的那四类）来拦。
"""),
        TABLE(["级别", "跑什么", "统计门禁", "确定性门禁", "触发时机"], [
            ["<strong>smoke</strong>", "60 条 × 1", "<strong>只在掉出绝对下限时阻断</strong>", "<strong>全套</strong>（完整性/指纹/schema/安全断言）", "每次提交"],
            ["<strong>full</strong>", "500 条 × 3", "配对检验 + regression-only", "全套", "合并前 + 每日定时"],
            ["<strong>deep</strong>", "全量 × 5 + 多切片 + judge 体检", "全套 + 元评测", "全套", "发版前 + 每周"],
        ]),
        CALLOUT("intuition", "这个分级里最容易做错的是<strong>给 smoke 配统计门禁</strong>。"
                             "<em>60 条样本的 $\\sigma$ 大约在 3–5 个点，"
                             "按月误报一次算，阈值要放到 ±12 个点以上——</em>"
                             "<strong>而 12 个点的退化根本不需要统计检验就能看出来</strong>。"
                             "所以 smoke 的正确定位是：<strong>跑确定性检查 + 抓灾难性变化</strong>，"
                             "统计判断留给 full。"),
        H3("smoke 真正该抓的东西"),
        UL([
            "<strong>流水线崩了</strong>——异常、超时率暴涨、判分器崩溃率暴涨；",
            "<strong>配置不可比</strong>——指纹与基线不同却没声明；",
            "<strong>灾难性变化</strong>——分数掉出预期区间（含异常升高）；",
            "<strong>安全/格式断言</strong>——输出不合 schema、触发了安全规则；",
            "<em>以及：跑得完</em>——smoke 本身跑挂了也是一个重要信号。",
        ]),
    ])),

    # ============================================================== 6
    ("alert-fatigue", "告警疲劳：把「误报率」翻译成「多久没人信了」", "".join([
        P("第 1 节说门禁会被关掉。这一节把它量化，因为<strong>只有量化了，"
          "「降低误报率」才会被当成一个优先级而不是一句正确的废话。</strong>"),
        MATH(r"\Pr(\text{k 周内至少发生 } m \text{ 次误报}) \quad\text{—— 用它来选 } \alpha"),
        P("一个简单的信任模型：<strong>每次误报消耗一定的信任，每次真报恢复一些信任；"
          "信任降到阈值以下，门禁就被降级或关掉。</strong>"
          "notebook 第 5 节会把这个模型跑出来，结论是："),
        TABLE(["单次误报率 $\\alpha$", "每天 20 次运行下的误报频率", "门禁存活时间（模拟）", "评价"], [
            ["5%（常规统计默认）", "<strong>每天 1 次</strong>", "约 1–2 周", "必然被关掉"],
            ["1%", "每周 1.4 次", "约 1–2 个月", "仍然偏高"],
            ["<strong>0.25%</strong>", "<strong>每月 1.5 次</strong>", "长期存活", "<strong>推荐目标</strong>"],
            ["0.05%", "每年 3.6 次", "长期存活", "过严，会漏掉真实退化"],
        ]),
        CALLOUT("danger", "这张表最反直觉的一行是第一行：<strong>$\\alpha = 0.05$ 这个统计学的默认值，"
                          "在 CI 场景下意味着每天一次误报</strong>——"
                          "<em>它在论文里是合理的（一篇论文做一次检验），在 CI 里是灾难性的（一天做二十次）。</em>"
                          "<strong>多重比较在 CI 门禁里不是一个理论问题，是一个每天都在发生的现实问题。</strong>"),
        H3("除了压低 α，还能做什么"),
        OL([
            "<strong>连续两次才阻断</strong>——单次异常只警告，连续两次运行都异常才阻断。"
            "<em>误报率从 $\\alpha$ 降到约 $\\alpha^2$，而真实退化会持续存在因此几乎不受影响</em>。"
            "<strong>这是性价比最高的一条</strong>；",
            "<strong>自动重跑一次再判</strong>——与上一条类似，但要注意"
            "<em>重跑的触发条件是「统计异常」而不是「结果不好」</em>（呼应模块 02 第 3 节的偏倚讨论），"
            "所以必须<strong>无条件重跑并取两次的合并结果</strong>，而不是「取更好的那次」；",
            "<strong>把 WARN 和 BLOCK 分开</strong>（第 3 节）——大部分异常只该 WARN；",
            "<strong>告警里带足够的诊断信息</strong>——"
            "<em>一个说「分数掉了 3.2 个点，其中 hard 切片掉了 8 个点，"
            "退化的 12 道题里有 9 道在 billing 子系统」的告警，"
            "比一个说「REGRESSION DETECTED」的告警更容易被相信</em>。",
        ]),
    ])),

    # ============================================================== 7
    ("canary", "金丝雀与分阶段放行", "".join([
        P("门禁不是二元的。当一个改动通过了 CI 但你仍不完全放心时，"
          "<strong>分阶段放行</strong>比「合还是不合」提供了更多选项。"),
        TABLE(["阶段", "暴露范围", "看什么", "回滚条件"], [
            ["<strong>影子运行</strong>（shadow）", "0% 用户，但对真实流量跑一遍", "离线指标 + 与现网输出的 diff", "任何异常"],
            ["<strong>金丝雀</strong>", "1–5% 流量", "<strong>线上指标</strong>（模块 05）+ 错误率 + 延迟", "线上指标显著劣化"],
            ["<strong>逐步放量</strong>", "5% → 25% → 50% → 100%", "同上，每一档观察足够长的时间", "同上"],
        ]),
        DUAL(
            "影子运行是这三档里最被低估的一个：<strong>它零风险</strong>"
            "（用户看不到输出），却能提供离线评测提供不了的东西——"
            "<em>真实流量的分布</em>。"
            "<strong>离线任务集永远只是真实分布的一个样本，而且通常是有偏的样本</strong>"
            "（人挑出来的、覆盖已知问题的）。"
            "影子运行能告诉你「在真实的用户提问上，新版本和旧版本的输出差多少」。",
            "从统计的角度，影子运行提供的是<span class=\"term\">配对的线上样本</span>："
            "同一个真实请求，两个版本各产出一个回答。"
            "<strong>这让「新旧对比」的方差被压到最低</strong>（同样的配对原理，第 4 节），"
            "而且样本量是免费的（跟着真实流量走）。"
            "<em>唯一的成本是双倍推理开销，以及需要一个能比较两个输出的判分器</em>——"
            "而后者正是 C67 的内容。",
        ),
        CALLOUT("intuition", "一个实用的组合：<strong>CI 的 full 门禁 + 影子运行的输出 diff</strong>。"
                             "<em>前者在固定的任务集上抓退化，后者在真实分布上抓「离线没覆盖到的场景」</em>。"
                             "<strong>两者的失败模式互补</strong>——"
                             "离线任务集抓不到的（分布偏移、真实用户的奇怪输入），"
                             "影子运行能抓到；影子运行没有金标准，"
                             "但离线任务集有。"),
        P("<strong>分阶段放行的观察窗口该多长？</strong>"
          "由你要检出的效应量与线上流量决定——这就是 C66 模块 04 的 MDE 计算，"
          "只是把「任务数」换成了「这一档能积累多少请求」。"
          "<em>一个常见的错误是「放 5% 观察十分钟」——"
          "十分钟的 5% 流量通常远不够检出几个点的差异。</em>"),
    ])),
    # ============================================================== 8
    ("gate-ops", "门禁的运维：override、基线更新与例外流程", "".join([
        P("门禁上线之后的日常运维，决定了它是变成一道真实的防线还是一个橡皮图章。"
          "这一节讲三个必须提前设计好的流程。"),
        H3("① Override：必须存在，但必须留痕"),
        DUAL(
            "<strong>「不允许 override」是行不通的</strong>——总会有紧急修复需要绕过门禁，"
            "而一个无法绕过的门禁最终会被整个关掉（第 1 节）。"
            "<em>所以正确的设计不是禁止 override，而是让它<strong>有成本、有记录、可统计</strong></em>："
            "需要填写理由、需要另一个人批准、<strong>并且每月统计 override 次数</strong>。",
            "把 override 率当成一个一级指标来看："
            "<strong>override 率突然升高，说明门禁的误报率升高了</strong>"
            "（或者阈值该重新校准了）；"
            "<em>而 override 率长期为零也是一个信号</em>——"
            "要么门禁太松（从没拦住过什么），要么有人在用别的方式绕过它。"
            "<strong>健康的 override 率大约在每月一到两次</strong>，"
            "这与「每月至多一次误报」的设计目标是自洽的。",
        ),
        H3("② 基线更新：什么时候、怎么更新"),
        TABLE(["更新时机", "做法", "风险"], [
            ["<strong>每次成功合并后</strong>", "滚动基线", "<strong>渐进式退化</strong>（模块 03 第 8 节）——每次退化 0.3 个点都通过"],
            ["<strong>每个季度</strong>", "锚定基线", "更新不及时会让锚定基线失去意义"],
            ["<strong>模型/任务集大版本变更时</strong>", "强制重建基线", "必须<strong>显式声明配置变更</strong>，否则确定性门禁会拦住"],
        ]),
        P("<strong>推荐同时维护滚动基线与锚定基线</strong>："
          "滚动基线抓突发退化（阈值严），锚定基线抓渐进退化（阈值宽但必须有）。"
          "<em>只有一个基线的门禁，一定会漏掉两类退化中的一类。</em>"),
        H3("③ 例外流程：已知问题的白名单"),
        P("有些任务会因为已知的、暂时不打算修的原因持续失败"
          "（依赖了一个待下线的服务、任务本身有争议）。"
          "<strong>正确处理不是把它们从任务集删掉，而是加白名单</strong>："),
        CODE("""// known_failures.json —— 白名单本身也要版本化、也要过期
[
  {"task_id": "billing-047",
   "reason": "依赖的 legacy 接口将于 2026-10 下线，届时重写此题",
   "added": "2026-06-01",
   "expires": "2026-11-01",          // ← **必须有过期时间**
   "owner": "billing-team"},
]"""),
        CALLOUT("warn", "<strong><code>expires</code> 这个字段是白名单机制里最重要的一个。</strong>"
                        "<em>没有过期时间的白名单会无限增长，最终任务集里一半的题都在白名单上，"
                        "而没人记得为什么</em>。"
                        "<strong>CI 里应当有一条检查：白名单条目过期即失败</strong>，"
                        "强迫团队要么修掉它、要么显式续期（并写明为什么又推迟了）。"
                        "<em>这与模块 01「任务集只增不改」的精神一致——"
                        "让所有的妥协都是显式的、有时限的、可被审计的。</em>"),
        H3("④ 门禁失败时该给什么信息"),
        P("最后一个运维细节，它直接决定了 override 率："
          "<strong>门禁失败的输出必须让人在三十秒内判断出「这是真的还是误报」。</strong>"
          "<em>一个只说「REGRESSION DETECTED, score dropped 3.2%」的告警，"
          "会让作者的第一反应是 override</em>——因为核实的成本比绕过的成本高。"),
        UL([
            "<strong>退化集中在哪</strong>：按子系统与难度分解（模块 03 的逐题变化矩阵）——"
            "<em>「全部集中在 billing」是一个可行动的线索，「均匀分布」通常是噪声</em>；",
            "<strong>具体是哪几道题</strong>：给出 task_id 与逐题 diff 的链接，"
            "<em>让作者能一眼看出「哦这个我知道为什么」</em>；",
            "<strong>对照信息</strong>：同时给出 fixed 数与 churn 的噪声基线，"
            "<strong>让作者能自己判断这是不是波动</strong>；",
            "<strong>历史</strong>：这条规则最近一个月触发过几次、其中几次是真的。"
            "<em>这一行本身就是门禁可信度的凭证</em>。",
        ]),
        P("最后，白名单上的任务<strong>仍然要被执行和记录</strong>，只是不进门禁。"
          "<em>因为你需要知道「它什么时候自己好了」</em>——"
          "而如果直接跳过执行，这个信息就永远拿不到。"),
    ])),
]

NB = [
    md("""# 04 · CI 回归门禁（阈值推导 / 门禁分级 / 配对门禁 / 两级架构 / 告警疲劳 / 金丝雀）

目标：把「掉 2% 就报警」这种拍脑袋的规则，替换成**从方差和误报预算推导出来**的门禁。

本 notebook 你会亲手实现：
1. **测噪声 → 推阈值** —— 三步法，以及噪声太大时该降噪而不是放宽阈值
2. **误报率 → 每周误报次数** —— 为什么 α=0.05 在 CI 里是灾难性的
3. **配对门禁 vs 绝对阈值** —— 零成本把 σ 砍一半
4. **告警疲劳模拟** —— 信任模型，量化「门禁能活多久」
5. **连续两次才阻断** —— 误报率从 α 降到 α²，而真报几乎不受影响
6. **两级门禁的配置推导** —— smoke 该抓什么、full 该抓什么

> 心智模型：**门禁的可信度是一种会被消耗的资源。
> 漏报的代价是有限的（下一道防线还在），误报的代价是复利的（信任被持续消耗）。**"""),

    md("""## 0 · 环境与一个可控的「模型 + 评测」"""),

    code("""import os, json, math, random, itertools
from collections import Counter, defaultdict

import numpy as np

def eval_run(n_tasks, attempts, true_acc, seed, task_difficulty=None, steep=2.4):
    \"\"\"跑一次评测，返回逐题分数（任务内取均值）。
    task_difficulty 固定时，两次运行就是「同一批任务」——配对门禁需要这个。
    steep 控制难度的区分度：真实评测里大多数题是稳定通过或稳定失败，
    只有少数处在「时对时错」的边缘 —— steep 越大越接近这种形态。\"\"\"
    rng = np.random.default_rng(seed)
    if task_difficulty is None:
        task_difficulty = rng.beta(2, 2, n_tasks)
    per_task = []
    for d in task_difficulty:
        p = float(np.clip(true_acc + steep * (0.5 - d), 0.01, 0.99))   # 难题对谁都难
        per_task.append(float(np.mean(rng.random(attempts) < p)))
    return np.array(per_task)

# 固定一批任务的难度 —— 这就是「同一批任务」
DIFF_60 = np.random.default_rng(0).beta(2, 2, 60)
DIFF_500 = np.random.default_rng(1).beta(2, 2, 500)

s = eval_run(60, 1, 0.60, seed=7, task_difficulty=DIFF_60)
print(f'smoke 一次运行: {len(s)} 题, 分数 {s.mean():.1%}')
assert len(s) == 60
print('\\n✅ 难度固定 → 两次运行跑的是同一批任务 → 配对门禁成立。')"""),

    md("""## 1 · 三步法：测噪声 → 定误报预算 → 算阈值"""),

    code("""def measure_noise(n_tasks, attempts, true_acc, n_repeats=30, task_difficulty=None, seed0=100):
    \"\"\"第一步：同一配置重复跑 R 次，测分数的标准差。**这一步不可跳过。**\"\"\"
    scores = [eval_run(n_tasks, attempts, true_acc, seed=seed0 + r,
                       task_difficulty=task_difficulty).mean()
              for r in range(n_repeats)]
    return float(np.mean(scores)), float(np.std(scores, ddof=1))

def alpha_from_budget(runs_per_day, false_alarms_per_month=1.0):
    \"\"\"第二步：把「每月至多 m 次误报」换算成单次误报率。\"\"\"
    return false_alarms_per_month / (runs_per_day * 30)

def z_for_alpha(alpha):
    \"\"\"单侧正态分位数（二分求解，避免依赖 scipy）。\"\"\"
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        tail = 0.5 * math.erfc(mid / math.sqrt(2))
        if tail > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def threshold_from_variance(sigma_run, alpha):
    \"\"\"第三步：两次运行都有噪声，所以差值的标准差是 sigma*sqrt(2)。\"\"\"
    return z_for_alpha(alpha) * sigma_run * math.sqrt(2)

print(f"{'配置':<22}{'均值':>8}{'σ_run':>9}{'α':>10}{'阈值':>9}{'能检出':>10}")
CONFIGS = [('smoke  60×1', 60, 1, DIFF_60), ('mid   200×1', 200, 1, None),
           ('full  500×3', 500, 3, DIFF_500)]
noise = {}
for name, nt, at, diff in CONFIGS:
    d = diff if diff is not None else np.random.default_rng(5).beta(2, 2, nt)
    mu, sd = measure_noise(nt, at, 0.60, n_repeats=30, task_difficulty=d)
    a = alpha_from_budget(20, 1.0)
    th = threshold_from_variance(sd, a)
    noise[name] = (mu, sd, th)
    print(f'{name:<22}{mu:>8.1%}{sd:>9.2%}{a:>10.4f}{th:>9.2%}{"≥ "+format(th,".1%"):>10}')

sd_smoke = noise['smoke  60×1'][1]
sd_full = noise['full  500×3'][1]
assert sd_smoke > sd_full * 2, 'smoke 的噪声必然远大于 full'
print(f'\\nσ: smoke {sd_smoke:.2%} vs full {sd_full:.2%} —— 相差 {sd_smoke/sd_full:.1f} 倍')
print('✅ 阈值不是拍脑袋定的：测噪声 → 定误报预算 → 算阈值，三步都有依据。')
print(f'   smoke 的阈值要放到 ±{noise["smoke  60×1"][2]:.1%} 才能满足月误报一次——')
print('   **而这么大的退化根本不需要统计检验就能看出来** → smoke 不该配统计门禁。')"""),

    md("""## 2 · α=0.05 在 CI 里意味着什么"""),

    code("""def false_alarms_per_period(alpha, runs_per_day, days):
    return alpha * runs_per_day * days

print(f"{'α':>10}{'每天':>10}{'每周':>10}{'每月':>10}{'每年':>10}   评价")
VERDICT = {0.05: '必然被关掉', 0.01: '仍然偏高', 0.0025: '← 推荐目标', 0.0005: '过严，会漏报'}
for a in [0.05, 0.01, 0.0025, 0.0005]:
    d = false_alarms_per_period(a, 20, 1)
    w = false_alarms_per_period(a, 20, 7)
    m = false_alarms_per_period(a, 20, 30)
    y = false_alarms_per_period(a, 20, 365)
    print(f'{a:>10.4f}{d:>10.2f}{w:>10.2f}{m:>10.2f}{y:>10.1f}   {VERDICT[a]}')

assert false_alarms_per_period(0.05, 20, 1) >= 1.0, 'α=0.05 每天至少一次误报'
assert false_alarms_per_period(0.0025, 20, 30) < 2.0
print('\\n⚠️ α=0.05 是统计学的默认值，在论文里合理（一篇论文一次检验），')
print('   在 CI 里是灾难性的（一天二十次检验）——**每天一次误报**。')
print('   **多重比较在 CI 门禁里不是理论问题，是每天都在发生的现实问题。**')"""),

    md("""## 3 · 配对门禁：零成本把 σ 砍一半"""),

    code("""def paired_diff_noise(n_tasks, attempts, true_acc, task_difficulty, n_repeats=300):
    \"\"\"配对：两次运行跑**同一批任务**，任务难度对两边是同一个数。\"\"\"
    diffs = []
    for r in range(n_repeats):
        a = eval_run(n_tasks, attempts, true_acc, seed=1000 + 2 * r, task_difficulty=task_difficulty)
        b = eval_run(n_tasks, attempts, true_acc, seed=1001 + 2 * r, task_difficulty=task_difficulty)
        diffs.append(b.mean() - a.mean())
    return np.array(diffs)

def unpaired_diff_noise(n_tasks, attempts, true_acc, n_repeats=300):
    \"\"\"非配对：两次运行的任务集不同（各自重新抽样）——真实场景里这来自
    「超时被跳过的题不一样」「基线跑的是上个版本的任务集」。\"\"\"
    diffs = []
    for r in range(n_repeats):
        d1 = np.random.default_rng(5000 + 2 * r).beta(2, 2, n_tasks)
        d2 = np.random.default_rng(5001 + 2 * r).beta(2, 2, n_tasks)
        a = eval_run(n_tasks, attempts, true_acc, seed=2000 + 2 * r, task_difficulty=d1)
        b = eval_run(n_tasks, attempts, true_acc, seed=2001 + 2 * r, task_difficulty=d2)
        diffs.append(b.mean() - a.mean())
    return np.array(diffs)

pair_d = paired_diff_noise(500, 3, 0.60, DIFF_500)
unpair_d = unpaired_diff_noise(500, 3, 0.60)
alpha = alpha_from_budget(20, 1.0)
th_pair = z_for_alpha(alpha) * pair_d.std(ddof=1)
th_unpair = z_for_alpha(alpha) * unpair_d.std(ddof=1)

print(f"{'设计':<22}{'σ(差值)':>12}{'阈值':>10}{'能检出的最小退化':>20}")
print(f'{"非配对（任务集不同）":<22}{unpair_d.std(ddof=1):>12.3%}{th_unpair:>10.2%}{th_unpair:>19.1%}')
print(f'{"配对（同一批任务）":<22}{pair_d.std(ddof=1):>12.3%}{th_pair:>10.2%}{th_pair:>19.1%}')
assert abs(pair_d.mean()) < 0.01 and abs(unpair_d.mean()) < 0.01, '真值相同，差值应当围绕 0'
ratio = unpair_d.std(ddof=1) / pair_d.std(ddof=1)
assert ratio > 1.5, '配对必须显著降噪'
print(f'\\nσ 比值 = {ratio:.2f} → 配对把噪声砍到了 {1/ratio:.0%}')
print(f'能检出的最小退化: {th_unpair:.1%} → {th_pair:.1%}')
print('\\n✅ 这就是「配对」的全部价值：任务难度对两边是同一个数，做差时被消掉。')
print('   而且它是**零额外成本**的——只要两次运行跑同一批任务就自动获得。')
print('   → 配对门禁的前置断言：**两次运行必须跑同一批任务**（模块 03 的 same_task_set）。')
print('   ⚠️ 现实里「非配对」往往不是有意的：基线跑了 500 条、当前只跑了 487 条')
print('      （13 条超时被跳过），而被跳过的通常是最难的 → 当前运行看起来更好。')"""),

    code("""# regression-only 门禁：只看退化，不看净变化
def regression_only_noise(n_tasks, attempts, true_acc, task_difficulty,
                          n_repeats=200, thresh=0.5):
    regs = []
    for r in range(n_repeats):
        a = eval_run(n_tasks, attempts, true_acc, seed=1000 + 2 * r, task_difficulty=task_difficulty)
        b = eval_run(n_tasks, attempts, true_acc, seed=1001 + 2 * r, task_difficulty=task_difficulty)
        regs.append(int(((a >= thresh) & (b < thresh)).sum()))
    return np.array(regs)

regs = regression_only_noise(500, 3, 0.60, DIFF_500)
p99 = float(np.percentile(regs, 99.75))
print(f'噪声下的自发退化题数（500 题中）: 中位 {np.median(regs):.0f}, P99.75 = {p99:.0f}')
print(f'→ regression-only 门禁的阈值可以直接取经验分位数: **退化 > {p99:.0f} 题就阻断**')
assert p99 > np.median(regs)
print(f'\\n注意这个数不小（{np.median(regs):.0f}/500 ≈ {np.median(regs)/500:.0%} 的题会自发翻转）——')
print('这正是「churn 远大于净变化时该加重复次数」的来源（模块 03 练习 3）。')
print('\\n✅ 这条规则的好处：**它不需要任何分布假设**，阈值直接来自噪声下的经验分布。')
print('   而且它符合 CI 的语义——门禁的职责是「防止把东西弄坏」，不是「确认变好了」。')"""),

    md("""## 4 · 告警疲劳：门禁能活多久"""),

    code("""def simulate_gate_lifetime(alpha, runs_per_day, true_regression_rate=0.02,
                           trust0=1.0, cost_false=0.12, gain_true=0.25,
                           kill_below=0.3, days=180, seed=0):
    \"\"\"信任模型：误报消耗信任，真报恢复信任。信任跌破阈值 = 门禁被降级/关掉。\"\"\"
    rng = np.random.default_rng(seed)
    trust = trust0
    for day in range(days):
        for _ in range(runs_per_day):
            is_real = rng.random() < true_regression_rate
            if is_real:
                trust = min(1.0, trust + gain_true)          # 真报：信任恢复
            elif rng.random() < alpha:
                trust -= cost_false                           # 误报：信任消耗
            if trust < kill_below:
                return day
    return None      # 存活到底

print(f"{'α':>10}{'每月误报':>12}{'180 天内被关掉':>16}{'被关时的中位天数':>18}")
for a in [0.05, 0.01, 0.0025, 0.0005]:
    lifetimes = [simulate_gate_lifetime(a, 20, seed=s) for s in range(20)]
    killed = [l for l in lifetimes if l is not None]        # 返回天数 = 那天被关掉了
    med = f'{np.median(killed):.0f} 天' if killed else '—'
    print(f'{a:>10.4f}{a*20*30:>12.2f}{f"{len(killed)}/20":>16}{med:>18}')

l05 = [simulate_gate_lifetime(0.05, 20, seed=s) for s in range(20)]
l001 = [simulate_gate_lifetime(0.01, 20, seed=s) for s in range(20)]
l0025 = [simulate_gate_lifetime(0.0025, 20, seed=s) for s in range(20)]
assert all(l is None for l in l0025), 'α=0.25% 时门禁应当全部存活（返回 None）'
assert all(l is not None for l in l05), 'α=5% 时门禁全部被关掉'
assert np.median([l for l in l05 if l is not None]) < 21, 'α=5% 时三周内就被关掉'
n_killed_001 = sum(1 for l in l001 if l is not None)
assert 0 < n_killed_001 < 20, 'α=1% 处于中间地带：部分被关掉'
print('\\n✅ α=5% 的门禁 20/20 都在三周内被关掉；α=0.25% 的 20/20 全部存活。')
print(f'   α=1% 处在中间地带（{n_killed_001}/20 被关掉）——这也是为什么它「仍然偏高」。')
print('   **「降低误报率」不是一句正确的废话，它决定了门禁存不存在。**')"""),

    code("""# 连续两次才阻断：误报率从 α 降到约 α²，真报几乎不受影响
def two_strike_rates(alpha, power_single):
    \"\"\"power_single: 单次运行检出真实退化的概率。\"\"\"
    return {'false_alarm': alpha ** 2, 'detect': power_single ** 2}

print(f"{'策略':<20}{'误报率':>12}{'检出率':>12}{'每月误报':>12}")
ALPHA, POWER = 0.01, 0.90
one = {'false_alarm': ALPHA, 'detect': POWER}
two = two_strike_rates(ALPHA, POWER)
for name, r in [('单次即阻断', one), ('连续两次才阻断', two)]:
    print(f'{name:<20}{r["false_alarm"]:>12.4f}{r["detect"]:>12.1%}'
          f'{r["false_alarm"]*20*30:>12.2f}')

assert two['false_alarm'] < one['false_alarm'] / 50
assert two['detect'] > 0.75, '真实退化会持续存在，所以两次都检出的概率仍然很高'
print(f'\\n✅ 误报率降了 {one["false_alarm"]/two["false_alarm"]:.0f} 倍，'
      f'检出率只从 {one["detect"]:.0%} 掉到 {two["detect"]:.0%}——')
print('   因为**真实退化会持续存在**（第二次跑它还在），而误报是随机的（第二次大概率不复现）。')
print('   这是本模块性价比最高的一条建议。')
print('\\n⚠️ 但重跑的触发条件必须是「统计异常」而不是「结果不好」，')
print('   而且必须**无条件重跑并合并两次结果**，不能「取更好的那次」（模块 02 第 3 节的偏倚）。')"""),

    md("""## 5 · 门禁分级：把确定性检查和统计检查分开"""),

    code("""def deterministic_checks(run, baseline, spec):
    \"\"\"这四类检查**不涉及统计判断**，误报率天然为零 —— 门禁里最可信的部分。\"\"\"
    problems = []
    if run['n_rows'] != spec['expected_rows']:
        problems.append(f"完整性: 行数 {run['n_rows']} != 预期 {spec['expected_rows']}")
    if len(run['fingerprints']) != 1:
        problems.append(f"指纹不唯一: {run['fingerprints']} → run_id 被复用")
    if run['fingerprints'] != baseline['fingerprints'] and not run.get('declared_config_change'):
        problems.append('配置指纹与基线不同，但未声明配置变更 → 结果不可比')
    lo, hi = spec['expected_score_range']
    if not (lo <= run['score'] <= hi):
        direction = '低于' if run['score'] < lo else '**高于**'
        problems.append(f"分数 {run['score']:.1%} {direction}预期区间 [{lo:.0%}, {hi:.0%}]")
    if run.get('safety_violations', 0) > 0:
        problems.append(f"安全断言失败 {run['safety_violations']} 次")
    return problems

SPEC = {'expected_rows': 1500, 'expected_score_range': (0.30, 0.55)}
BASELINE = {'fingerprints': ['fp_abc'], 'score': 0.412}

CASES = [
    ('正常', {'n_rows': 1500, 'fingerprints': ['fp_abc'], 'score': 0.418, 'safety_violations': 0}),
    ('行数对不上', {'n_rows': 1470, 'fingerprints': ['fp_abc'], 'score': 0.425, 'safety_violations': 0}),
    ('run_id 复用', {'n_rows': 1500, 'fingerprints': ['fp_abc', 'fp_xyz'], 'score': 0.41, 'safety_violations': 0}),
    ('分数异常升高', {'n_rows': 1500, 'fingerprints': ['fp_abc'], 'score': 0.951, 'safety_violations': 0}),
    ('安全断言失败', {'n_rows': 1500, 'fingerprints': ['fp_abc'], 'score': 0.41, 'safety_violations': 3}),
]
for name, run in CASES:
    probs = deterministic_checks(run, BASELINE, SPEC)
    mark = '✅ 通过' if not probs else f'🚫 BLOCK: {probs[0]}'
    print(f'{name:<16}{mark}')

assert deterministic_checks(CASES[0][1], BASELINE, SPEC) == []
assert len(deterministic_checks(CASES[3][1], BASELINE, SPEC)) == 1
print('\\n✅ 注意「分数异常升高」也被拦了——')
print('   预期 30-55% 的任务集跑出 95%，几乎肯定是流水线出了问题（判分器坏了/答案泄漏）。')
print('   **「只在分数下降时告警」会漏掉整整一类事故。**')"""),

    code("""def gate(run, baseline, spec, diff, sigma_run, alpha, reg_threshold, baseline_churn):
    \"\"\"完整门禁：确定性检查（BLOCK）→ 统计检查（BLOCK）→ 其余（WARN/INFO）。
    baseline_churn: 噪声下的自发翻转题数——churn 要和**它**比，而不是和净变化比。\"\"\"
    det = deterministic_checks(run, baseline, spec)
    if det:
        return {'level': 'BLOCK', 'reason': 'deterministic', 'details': det}

    if diff['regressed'] > reg_threshold:
        return {'level': 'BLOCK', 'reason': 'regression_only',
                'details': [f"退化 {diff['regressed']} 题 > 噪声上限 {reg_threshold} 题"]}

    th = threshold_from_variance(sigma_run, alpha)
    drop = baseline['score'] - run['score']
    if drop > th and diff['p'] < alpha:
        return {'level': 'BLOCK', 'reason': 'statistical',
                'details': [f'下降 {drop:.2%} > 阈值 {th:.2%}, p={diff["p"]:.4f}']}

    warns = []
    if drop > th / 2:
        warns.append(f'分数下降 {drop:.2%}（未达阻断阈值 {th:.2%}）')
    if diff['churn'] > 2 * baseline_churn:
        warns.append(f'churn {diff["churn"]} > 噪声基线的 2 倍（{2*baseline_churn}）→ 改动波及面异常大')
    if run.get('cost_ratio', 1.0) > 1.2:
        warns.append(f'成本上升 {run["cost_ratio"]-1:.0%}')
    return {'level': 'WARN' if warns else 'PASS', 'reason': 'soft', 'details': warns}

SIGMA = sd_full
ALPHA_CI = alpha_from_budget(20, 1.0)
REG_TH = int(p99)
SCEN = [
    ('无变化',        {'n_rows':1500,'fingerprints':['fp_abc'],'score':0.410,'safety_violations':0,'cost_ratio':1.0},
     {'regressed': int(np.median(regs)), 'fixed': int(np.median(regs)) + 2,
      'net': 2, 'churn': 2 * int(np.median(regs)), 'p': 0.8}),
    ('小幅提升',      {'n_rows':1500,'fingerprints':['fp_abc'],'score':0.441,'safety_violations':0,'cost_ratio':1.0},
     {'regressed': int(p99) - 10, 'fixed': int(p99) + 25, 'net': 35,
      'churn': 2 * int(p99) + 15, 'p': 0.001}),
    ('真实退化',      {'n_rows':1500,'fingerprints':['fp_abc'],'score':0.362,'safety_violations':0,'cost_ratio':1.0},
     {'regressed': int(p99) + 45, 'fixed': 20, 'net': -(int(p99) + 25),
      'churn': int(p99) + 65, 'p': 0.0001}),
    ('净正但退化多',  {'n_rows':1500,'fingerprints':['fp_abc'],'score':0.430,'safety_violations':0,'cost_ratio':1.0},
     {'regressed': int(p99) + 12, 'fixed': int(p99) + 30, 'net': 18,
      'churn': 2 * int(p99) + 42, 'p': 0.02}),
    ('成本暴涨',      {'n_rows':1500,'fingerprints':['fp_abc'],'score':0.415,'safety_violations':0,'cost_ratio':1.9},
     {'regressed': int(np.median(regs)) + 1, 'fixed': int(np.median(regs)) + 2,
      'net': 1, 'churn': 2 * int(np.median(regs)), 'p': 0.7}),
]
BASE_CHURN = 2 * int(np.median(regs))          # 噪声下的自发翻转题数
print(f'门禁参数: σ={SIGMA:.2%}, α={ALPHA_CI:.4f}, '
      f'统计阈值={threshold_from_variance(SIGMA, ALPHA_CI):.2%}, '
      f'退化上限={REG_TH} 题, churn 噪声基线={BASE_CHURN} 题\\n')
for name, run, diff in SCEN:
    g = gate(run, BASELINE, SPEC, diff, SIGMA, ALPHA_CI, REG_TH, BASE_CHURN)
    print(f'{name:<16}{g["level"]:<7}{g["details"][0] if g["details"] else ""}')

def lvl(i):
    return gate(SCEN[i][1], BASELINE, SPEC, SCEN[i][2], SIGMA, ALPHA_CI, REG_TH, BASE_CHURN)['level']
assert lvl(0) == 'PASS', '无变化应当放行'
assert lvl(1) == 'PASS', '小幅提升应当放行'
assert lvl(2) == 'BLOCK', '真实退化必须阻断'
assert lvl(3) == 'BLOCK', '净正但退化多必须被 regression-only 拦住'
assert lvl(4) == 'WARN', '成本暴涨只警告不阻断'
print(f'\\n✅ 「净正但退化多」被 regression-only 规则拦住了——')
print(f'   净变化 +18 看起来是提升，但 {int(p99)+12} 道题从对变错（超过噪声上限 {REG_TH}），')
print('   其中可能有核心路径。**CI 门禁的职责是防止把东西弄坏，不是确认变好了。**')"""),

    md("""## ✏️ 练习 1：从误报预算反推所需样本量

实现 `required_tasks_for_mde(mde, sigma_per_task, alpha, power=0.8)`：
给定想检出的最小退化 `mde`（比例）、单题分数的标准差 `sigma_per_task`、误报率 `alpha`，
返回所需的任务数。用 $n = \\frac{(z_\\alpha + z_\\beta)^2 \\cdot 2\\sigma^2}{\\text{mde}^2}$
（因子 2 来自两次运行都有噪声）。"""),

    code("""def required_tasks_for_mde(mde, sigma_per_task, alpha, power=0.8):
    # TODO：z_beta 用 z_for_alpha(1 - power)
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
SIG_TASK = 0.45
n1 = required_tasks_for_mde(0.03, SIG_TASK, 0.05)
n2 = required_tasks_for_mde(0.03, SIG_TASK, 0.0025)
assert n2 > n1, '误报率要求越严，需要的样本越多'
assert required_tasks_for_mde(0.06, SIG_TASK, 0.0025) < n2, 'MDE 越大需要的样本越少'
print(f"{'要检出的退化':>14}{'α=0.05':>12}{'α=0.0025':>12}")
for mde in [0.02, 0.03, 0.05, 0.10]:
    print(f'{mde:>14.0%}{required_tasks_for_mde(mde, SIG_TASK, 0.05):>12,}'
          f'{required_tasks_for_mde(mde, SIG_TASK, 0.0025):>12,}')
print('\\n✅ 练习 1 通过：这张表是「smoke 该多大、full 该多大」的直接依据——')
print('   要在 CI 的误报预算下检出 3 个点的退化，需要上千道题 → smoke 做不到，只能靠 full。')"""),

    md("""## ✏️ 练习 2：两级门禁的配置推导

实现 `design_two_tier(sigma_smoke, sigma_full, runs_per_day, false_per_month=1.0)`：
返回 `{'alpha', 'smoke_threshold', 'full_threshold', 'smoke_useful'}`，
其中 `smoke_useful` 表示 smoke 的统计阈值是否 < 10 个点（超过就说明统计门禁没意义）。"""),

    code("""def design_two_tier(sigma_smoke, sigma_full, runs_per_day, false_per_month=1.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
d = design_two_tier(sd_smoke, sd_full, runs_per_day=20)
for k, v in d.items():
    print(f'  {k:<20} {v if isinstance(v, bool) else f"{v:.4f}"}')
assert d['smoke_threshold'] > d['full_threshold']
assert d['smoke_useful'] is False, 'smoke 的统计阈值必然大到没有意义'
d2 = design_two_tier(0.004, 0.002, runs_per_day=20)
assert d2['smoke_useful'] is True, '噪声足够小时 smoke 也能配统计门禁'
print(f'\\nsmoke 统计阈值 {d["smoke_threshold"]:.1%} → 有意义吗: {d["smoke_useful"]}')
print('✅ 练习 2 通过：smoke 的正确定位是**确定性检查 + 抓灾难性变化**，')
print('   统计判断留给 full——这个结论是算出来的，不是拍出来的。')"""),

    md("""## ✏️ 练习 3：连续 N 次才阻断

实现 `n_strike_rates(alpha, power_single, n_strikes)`：
返回 `{'false_alarm', 'detect', 'false_per_month'}`（按每天 20 次运行）。
用它找出「误报每月 < 0.5 次且检出率 > 70%」的最小 n_strikes。"""),

    code("""def n_strike_rates(alpha, power_single, n_strikes, runs_per_day=20):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
r1 = n_strike_rates(0.02, 0.90, 1)
r2 = n_strike_rates(0.02, 0.90, 2)
r3 = n_strike_rates(0.02, 0.90, 3)
assert r2['false_alarm'] < r1['false_alarm'] and r2['detect'] < r1['detect']
assert abs(r1['false_per_month'] - 0.02 * 20 * 30) < 1e-9
print(f"{'连续次数':>10}{'误报率':>12}{'检出率':>10}{'每月误报':>12}")
for n in [1, 2, 3, 4]:
    r = n_strike_rates(0.02, 0.90, n)
    print(f'{n:>10}{r["false_alarm"]:>12.5f}{r["detect"]:>10.1%}{r["false_per_month"]:>12.2f}')
best = next(n for n in range(1, 6)
            if n_strike_rates(0.02, 0.90, n)['false_per_month'] < 0.5
            and n_strike_rates(0.02, 0.90, n)['detect'] > 0.70)
print(f'\\n满足「每月误报<0.5 且 检出率>70%」的最小连续次数: {best}')
assert best == 2
print('✅ 练习 3 通过：连续 2 次是甜点——误报降两个数量级，检出率只掉 9 个点。')"""),

    md("""## ✏️ 练习 4：门禁健康度报告

实现 `gate_health(history)`：`history` 是 `[{'level':..., 'was_real':bool}, ...]`，
返回 `{'n', 'block_rate', 'precision', 'recall', 'false_per_month'}`，
其中 precision = 真实退化 / 所有 BLOCK，recall = 被 BLOCK 的真实退化 / 所有真实退化，
`false_per_month` 按每天 20 次运行折算。没有对应样本时返回 `nan`。"""),

    code("""def gate_health(history, runs_per_day=20):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
rng = np.random.default_rng(3)
def make_history(alpha, power, n=2000, real_rate=0.02):
    h = []
    for _ in range(n):
        real = rng.random() < real_rate
        blocked = (rng.random() < power) if real else (rng.random() < alpha)
        h.append({'level': 'BLOCK' if blocked else 'PASS', 'was_real': real})
    return h

for label, a, pw in [('好门禁 α=0.25%', 0.0025, 0.85), ('坏门禁 α=5%', 0.05, 0.85)]:
    hh = gate_health(make_history(a, pw))
    print(f'{label:<18} precision {hh["precision"]:.1%} | recall {hh["recall"]:.1%} | '
          f'每月误报 {hh["false_per_month"]:.1f}')

good = gate_health(make_history(0.0025, 0.85))
bad = gate_health(make_history(0.05, 0.85))
assert good['precision'] > bad['precision']
assert abs(good['recall'] - bad['recall']) < 0.15, 'recall 应当接近（同样的 power）'
assert good['false_per_month'] < bad['false_per_month'] / 5
empty = gate_health([])
assert math.isnan(empty['precision'])
print('\\n✅ 练习 4 通过：两个门禁的 recall 几乎一样，precision 差了一大截——')
print('   **门禁的问题几乎从来不是「不够灵敏」，而是「不够精确」。**')
print('   这份健康报告应当每月自动生成一次，作为「要不要调阈值」的依据。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def required_tasks_for_mde(mde, sigma_per_task, alpha, power=0.8):
    z_a = z_for_alpha(alpha)
    z_b = z_for_alpha(1 - power)
    return math.ceil(((z_a + z_b) ** 2 * 2 * sigma_per_task ** 2) / (mde ** 2))"""),

    code("""# 练习 2 参考答案
def design_two_tier(sigma_smoke, sigma_full, runs_per_day, false_per_month=1.0):
    alpha = alpha_from_budget(runs_per_day, false_per_month)
    th_s = threshold_from_variance(sigma_smoke, alpha)
    th_f = threshold_from_variance(sigma_full, alpha)
    return {'alpha': alpha, 'smoke_threshold': th_s, 'full_threshold': th_f,
            'smoke_useful': bool(th_s < 0.10)}"""),

    code("""# 练习 3 参考答案
def n_strike_rates(alpha, power_single, n_strikes, runs_per_day=20):
    fa = alpha ** n_strikes
    det = power_single ** n_strikes
    return {'false_alarm': fa, 'detect': det,
            'false_per_month': fa * runs_per_day * 30}"""),

    code("""# 练习 4 参考答案
def gate_health(history, runs_per_day=20):
    n = len(history)
    if n == 0:
        return {'n': 0, 'block_rate': float('nan'), 'precision': float('nan'),
                'recall': float('nan'), 'false_per_month': float('nan')}
    blocks = [h for h in history if h['level'] == 'BLOCK']
    reals = [h for h in history if h['was_real']]
    tp = sum(1 for h in blocks if h['was_real'])
    fp = len(blocks) - tp
    return {
        'n': n,
        'block_rate': len(blocks) / n,
        'precision': (tp / len(blocks)) if blocks else float('nan'),
        'recall': (tp / len(reals)) if reals else float('nan'),
        'false_per_month': (fp / n) * runs_per_day * 30,
    }"""),

    md("""---
## 🧪 真实工程胶囊：CI 门禁的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 建门禁的正确顺序（很多团队顺序反了）
# ══════════════════════════════════════════════════════════════════
# 1) 先建**确定性检查**（零误报，最可信）:
#      完整性校验 / 指纹可比性 / 任务集一致性 / 预期分数区间 / 安全断言
# 2) 再测噪声: 同配置重复跑 >= 10 次，得到 sigma_run
# 3) 定误报预算: 每月至多 1 次 → alpha = 1 / (runs_per_day * 30)
# 4) 算阈值: z(alpha) * sigma * sqrt(2)
# 5) 如果阈值大到没意义 → **回去降噪**（配对/加样本/加重复），不要接受宽阈值
# 6) 上「连续两次才阻断」
# 7) 每月看一次门禁健康报告（precision / recall / 每月误报）

# ══════════════════════════════════════════════════════════════════
# B. GitHub Actions 的形态
# ══════════════════════════════════════════════════════════════════
# on: [pull_request]        → smoke（3-5 分钟，确定性检查全套 + 绝对下限）
# on: merge_group           → full （1-3 小时，配对门禁 + regression-only）
# on: schedule (nightly)    → full + 切片分析 + judge 体检（C67）
# on: release               → deep （全量 × 5 + 元评测 + 成本前沿）
#
# 关键: smoke **不配统计门禁**。60 条样本的阈值要放到 ±12 个点，
#       而 12 个点的退化不需要统计检验就能看出来。

# ══════════════════════════════════════════════════════════════════
# C. 门禁输出的形状（告警要带足够诊断信息才会被相信）
# ══════════════════════════════════════════════════════════════════
# 🚫 BLOCK · regression-only
#    退化 40 题 > 阈值 22 题（噪声下的 P99.75）
#    退化分布: billing 28 / flight 9 / account 3     ← 集中在 billing
#    难度分布: easy 18 / medium 15 / hard 7          ← easy 上退化最多，异常
#    样例: billing-017, billing-042, billing-091（点击查看逐题 diff）
#    对照: 修好 58 题，净变化 +18
#    ─────────────────────────────────────────────
#    ⚠️ 净变化为正，但 easy 上的 18 道退化需要逐条解释

# ══════════════════════════════════════════════════════════════════
# D. 每月一次的门禁健康报告（练习 4）
# ══════════════════════════════════════════════════════════════════
# precision 低 → 误报太多，该收紧 alpha 或上连续两次
# recall 低   → 漏报太多，该降噪或加样本（**不是放宽阈值**）
# block_rate 高得离谱 → 通常是基线过期了，不是代码退化了
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 终极失败模式 | 门禁的可信度是会被消耗的资源；误报的代价是复利的 | 设计取向 |
| 三步法 | 测噪声 → 定误报预算 → 算阈值；阈值太宽时该降噪 | 定阈值 |
| α=0.05 的陷阱 | 论文里合理，CI 里每天一次误报 | 选 α |
| 确定性检查优先 | 那四类零误报的检查最该先建，很多团队顺序反了 | 建门禁 |
| 配对 + regression-only | 零成本降噪；且符合「防止弄坏」的 CI 语义 | 统计门禁 |
| 两级架构 | smoke 不配统计门禁——这是算出来的结论 | CI 配置 |
| 连续两次才阻断 | 误报降两个数量级，检出率只掉 9 个点 | 性价比最高 |
| 门禁健康报告 | 问题几乎从来不是不够灵敏，而是不够精确 | 每月复盘 |

下一模块：**05 · 线上监控与漂移**——离线指标与线上表现的相关性、
tracing 与采样、质量护栏，以及那条把线上信号送回离线任务集的反馈回路。""")
]
