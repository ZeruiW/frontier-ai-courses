# -*- coding: utf-8 -*-
"""C68 模块 05 · 线上监控与漂移。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 04（CI 门禁与告警疲劳）；"
                 "C67 模块 03（judge 漂移与哨兵集）读过更好，本模块会把它接到线上"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_online_monitoring.ipynb'
                       '（离线-在线相关性与「离线涨了线上没涨」的诊断 / 分布漂移检测：PSI 与 KS / '
                       'guardrail 的分层与误伤率 / 抽样策略：均匀 vs 分层 vs 不确定性驱动 / '
                       '线上信号回灌离线任务集的闭环 / 无标签监控：用代理指标预警）'),
    ("核心参考", "OpenTelemetry GenAI 语义约定（trace 与 span 属性）· "
                 "Population Stability Index 与 KS 检验在模型监控中的常规用法 · "
                 "Kohavi et al., <em>Trustworthy Online Controlled Experiments</em>（2020）· "
                 "本课程 C10 模块 07（在线 A/B）· C66 模块 03（轨迹埋点）· C67 模块 03（哨兵集与 CUSUM）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("offline-online", "离线指标与线上表现：为什么它们经常对不上", "".join([
        P("这门课到这里为止讲的都是<strong>离线</strong>评测：固定的任务集、可控的环境、可复现的结果。"
          "这一节讲那个所有人迟早会撞上的问题：<strong>离线涨了三个点，线上一点感觉都没有。</strong>"),
        TABLE(["原因", "机制", "怎么诊断", "怎么修"], [
            ["<strong>分布偏移</strong>", "离线任务集是人挑的，真实流量的分布完全不同", "把线上请求聚类，看离线任务集覆盖了哪些簇", "<strong>从线上采样回灌任务集</strong>（第 6 节）"],
            ["<strong>指标口径不同</strong>", "离线测「答案对不对」，线上看「用户满不满意」", "在同一批样本上同时算两个指标，看相关系数", "对齐口径，或明确声明离线是代理指标"],
            ["<strong>饱和</strong>", "离线任务集上大家都 90%+，提升发生在离线覆盖不到的尾部", "看离线分数的分布是否压在上界", "换更难的任务集（C66-01 的信息量分析）"],
            ["<strong>提升太小</strong>", "3 个点的离线提升，在线上被其他因素的方差淹没", "算线上的 MDE（C66-04）", "接受它检测不出来，或改用配对/影子设计"],
            ["<strong>非模型因素主导</strong>", "线上体验主要由延迟、UI、检索质量决定", "分解线上指标的方差来源", "先修那个主导因素"],
        ]),
        DUAL(
            "这五个原因里，<strong>最常见的是第一个，最容易被误诊成第四个</strong>。"
            "「可能是提升太小了」听起来很合理，于是团队去做更大的改动；"
            "<em>而真实原因往往是离线任务集根本不覆盖线上的主要场景</em>——"
            "改动再大也白搭，因为它优化的是一个不重要的分布。"
            "<strong>区分方法很直接：先看覆盖率，再谈效应量。</strong>",
            "形式化地说，离线指标估计的是 $\\mathbb{E}_{x \\sim D_{\\text{offline}}}[s(x)]$，"
            "而你关心的是 $\\mathbb{E}_{x \\sim D_{\\text{online}}}[u(x)]$。"
            "两者之间隔着<strong>两层不匹配</strong>："
            "$D_{\\text{offline}} \\ne D_{\\text{online}}$（分布）与 $s \\ne u$（指标口径）。"
            "<em>「离线涨了线上没涨」这件事，必须先确定是哪一层出的问题</em>——"
            "第一层用覆盖率诊断（第 2 节），第二层用同批样本上的相关系数诊断。"
            "<strong>两层的修法完全不同，混在一起谈会导致做错方向。</strong>",
        ),
        CALLOUT("intuition", "一条实用的诊断顺序：<strong>① 覆盖率（离线任务集覆盖了多少线上流量的分布）→ "
                             "② 口径相关性（在同一批样本上，离线指标与线上指标的相关系数）→ "
                             "③ 效应量与 MDE。</strong>"
                             "<em>按这个顺序查，通常在第一步就能找到答案</em>；"
                             "而很多团队直接从第三步开始，于是永远在讨论「是不是要做更大的改动」。"),
    ])),

    # ============================================================== 2
    ("drift", "分布漂移：PSI、KS，以及它们各自的盲区", "".join([
        P("线上监控的第一层是<strong>无标签监控</strong>——不需要知道答案对不对，"
          "只看输入和输出的分布有没有变。它便宜、实时、覆盖全量流量。"),
        H3("两个标准工具"),
        MATH(r"\text{PSI} = \sum_{b} (p_b - q_b)\ln\frac{p_b}{q_b}, \qquad \text{KS} = \sup_x |F_p(x) - F_q(x)|"),
        TABLE(["指标", "适用", "判读", "盲区"], [
            ["<strong>PSI</strong>（群体稳定性指数）", "分箱后的分布对比，类别型与数值型都行", "&lt; 0.1 稳定 · 0.1–0.25 需关注 · &gt; 0.25 显著漂移", "<strong>对分箱方式敏感</strong>；零频次桶要做平滑"],
            ["<strong>KS 统计量</strong>", "连续变量的分布对比", "配合样本量算 p 值", "只看最大偏离点，<em>对分布形状的局部变化不敏感</em>"],
            ["<strong>类别频次的卡方</strong>", "离散类别（意图、语言、来源）", "同上", "类别很多时功效低"],
            ["<strong>嵌入空间的分布距离</strong>", "语义漂移", "MMD / 分类器双样本检验", "计算贵；结果不可解释"],
        ]),
        CALLOUT("warn", "无标签漂移监控有一个结构性的局限，必须提前说清楚："
                        "<strong>它能告诉你「输入变了」，但不能告诉你「变得更差了」。</strong>"
                        "<em>输入分布漂移了，模型可能表现更好、更差、或者没变化</em>——"
                        "PSI 高只是一个「该去看看」的信号，不是一个「出问题了」的结论。"
                        "<strong>所以漂移告警的正确动作是「触发一次带标签的抽样评测」，"
                        "而不是直接回滚。</strong>"),
        H3("该监控哪些分布"),
        UL([
            "<strong>输入侧</strong>：请求长度、语言、意图类别、来源渠道、是否带附件/图片；",
            "<strong>输出侧</strong>：<em>响应长度、格式元素密度、拒答率、置信度分布</em>——"
            "<strong>这四个正是 C67 模块 05 里 reward hacking 的四种形态</strong>，"
            "在线上它们同样是「模型行为漂移」的最早信号；",
            "<strong>系统侧</strong>：延迟分位数、错误率、重试率、工具调用次数（agent 场景）、成本；",
            "<strong>判分器侧</strong>：如果线上有 LLM judge 在跑，它自己的分布也要监控（C67-03 的哨兵集）。",
        ]),
        P("<strong>输出侧的四个指标值得单独强调</strong>：它们不需要任何标签，"
          "却能抓住模型行为的实质性变化。"
          "<em>「平均响应长度一周内涨了 40%」这个信号，"
          "比任何离线指标都更早地告诉你「有什么东西变了」。</em>"),
    ])),

    # ============================================================== 3
    ("guardrails", "Guardrail：线上的实时护栏", "".join([
        P("漂移监控是<strong>事后</strong>的（发现了才去查）。"
          "Guardrail 是<strong>实时</strong>的：在响应返回给用户之前做一次检查。"),
        ASCII("""
   用户请求 ──► 模型 ──► ┌─────────────────────────────┐ ──► 用户
                        │ GUARDRAIL                   │
                        │  L0 规则   (微秒级, 零成本)  │
                        │  L1 小模型 (毫秒级, 极便宜)  │
                        │  L2 LLM    (百毫秒, 贵)      │
                        └─────────────────────────────┘
                                    │ 触发
                                    ▼
                           降级 / 重生成 / 转人工 / 拒答
"""),
        TABLE(["层", "检查什么", "延迟", "误伤率", "触发后的动作"], [
            ["<strong>L0 规则</strong>", "格式合法性、必填字段、长度上限、禁用词、PII 正则", "&lt; 1ms", "<strong>极低</strong>（确定性）", "重生成或用兜底模板"],
            ["<strong>L1 小模型</strong>", "安全分类、意图偏离、语言不匹配", "10–50ms", "低但非零", "降级到保守回答"],
            ["<strong>L2 LLM judge</strong>", "事实一致性、是否回答了问题、语气", "100–800ms", "<strong>取决于 judge 质量（C67）</strong>", "转人工或重生成"],
        ]),
        CALLOUT("danger", "Guardrail 有一个与 CI 门禁完全同构的失败模式（模块 04 第 1 节）："
                          "<strong>误伤率过高时，它会被降级成「只记录不拦截」，然后被忘掉。</strong>"
                          "<em>而线上 guardrail 的误伤代价比 CI 误报更直接——它伤的是真实用户的体验。</em>"
                          "<strong>所以分层的意义不只是省成本，更是把「零误伤的确定性检查」"
                          "和「有误伤的模型判断」分开</strong>："
                          "L0 可以放心拦截，L2 通常只该降级或标记，不该直接拒答。"),
        H3("Guardrail 的三个必报指标"),
        OL([
            "<strong>触发率</strong>（按层分开）——突然升高说明模型或流量变了；",
            "<strong>误伤率</strong>——<em>需要人工抽查被拦截的样本</em>。"
            "<strong>这个数不测就等于不知道 guardrail 在做什么</strong>；",
            "<strong>漏放率</strong>——从用户投诉、事后审计里反推。<em>最难测，但也最重要。</em>",
        ]),
        P("最后一条实践建议：<strong>guardrail 的每一次触发都要落一条结构化日志</strong>"
          "（哪一层、哪条规则、原始输出、最终动作）。"
          "<em>这些日志是回灌离线任务集最好的原料</em>（第 6 节）——"
          "被 guardrail 拦下来的样本，正是模型最容易出问题的地方。"),
    ])),

    # ============================================================== 4
    ("sampling", "抽样：全量记录不现实，随机抽样浪费预算", "".join([
        P("线上流量可能是每天几百万条，而人工标注预算可能是每天几百条。"
          "<strong>怎么抽这几百条，决定了你能发现什么。</strong>"),
        TABLE(["策略", "怎么抽", "适合发现什么", "代价"], [
            ["<strong>均匀随机</strong>", "固定比例随机抽", "<strong>估计整体质量</strong>（唯一无偏的）", "难样本太少，发现不了具体问题"],
            ["<strong>分层</strong>", "按意图/渠道/长度分层，每层保底", "各细分场景的质量", "需要分层维度"],
            ["<strong>不确定性驱动</strong>", "抽 judge 置信度低、swap 不一致的（C67-03）", "<strong>判分器的薄弱区 + 模型的边界</strong>", "结果有偏，不能直接外推"],
            ["<strong>异常驱动</strong>", "抽 guardrail 触发的、超时的、用户负反馈的", "<strong>真实问题</strong>", "极度有偏"],
        ]),
        CALLOUT("intuition", "推荐的组合与 C67 模块 03 的元评测集设计完全同构："
                             "<strong>「均匀随机的主集」+「不确定性驱动的加强集」+「异常驱动的问题集」，"
                             "三者分开统计、绝不混算。</strong>"
                             "<em>主集回答「整体质量是多少」（无偏），"
                             "加强集回答「难的地方怎么样」，问题集提供「该修什么」的线索。</em>"
                             "<strong>把它们混成一个数字，三个问题一个都答不了。</strong>"),
        H3("追踪采样率与统计的关系"),
        P("如果你对 trace 做了采样（比如只记录 1% 的完整轨迹），"
          "<strong>那么基于 trace 的任何统计都要做逆概率加权</strong>——"
          "而且要注意<em>采样本身可能是有偏的</em>："),
        UL([
            "<strong>头部采样</strong>（在请求开始时决定记不记）——无偏，但会漏掉罕见的错误；",
            "<strong>尾部采样</strong>（请求结束后按结果决定记不记，比如「出错的全记」）——"
            "<strong>信息量高得多，但引入了强选择偏倚</strong>。"
            "<em>用尾部采样的数据估计整体错误率会严重高估</em>；",
            "<strong>实践组合</strong>：<strong>头部固定比例（用于无偏统计）+ 尾部全量记录异常（用于诊断）</strong>，"
            "<em>并在数据里用一个字段标明这条 trace 是怎么被采到的</em>——"
            "没有这个字段，两类数据混在一起就再也分不开了。",
        ]),
    ])),

    # ============================================================== 5
    ("no-label", "无标签监控：没有金标准时能看什么", "".join([
        P("线上绝大多数请求是没有标签的——没人告诉你这个回答对不对。"
          "但<strong>没有标签不等于没有信号</strong>。"),
        TABLE(["信号", "怎么得到", "能预警什么", "可信度"], [
            ["<strong>自一致性</strong>", "同一请求采样两次，比较两个回答", "模型在这类输入上不稳定", "★★★（C67-03 的 swap 一致性同构）"],
            ["<strong>拒答/兜底率</strong>", "直接统计", "模型开始回避（或安全策略变了）", "★★★"],
            ["<strong>输出行为分布</strong>", "长度、格式密度、置信表述", "行为漂移（C67-05 的 hack 形态）", "★★★"],
            ["<strong>用户行为代理</strong>", "重问率、复制率、点踩率、会话轮数", "<strong>用户满意度的代理</strong>", "★★☆（受 UI 影响大）"],
            ["<strong>下游任务成功</strong>", "用户是否完成了目标动作", "<strong>最接近真实效用</strong>", "★★★（但归因难）"],
            ["<strong>工具调用成功率</strong>（agent）", "直接统计", "工具误用、环境变化", "★★★"],
        ]),
        DUAL(
            "这里面最有价值、也最容易被忽略的是<strong>「重问率」</strong>："
            "用户在收到回答后立刻换一种说法再问一遍，"
            "<em>几乎必然意味着上一个回答没解决问题</em>。"
            "<strong>它不需要任何标注，实时可得，而且与真实满意度高度相关。</strong>",
            "从测量的角度，这类信号是<span class=\"term\">行为代理指标</span>："
            "它们与真实效用相关，但混杂了 UI、用户习惯、流量构成等因素。"
            "<strong>因此它们适合做<em>相对比较</em>（新版本 vs 旧版本，同期同流量）"
            "而不适合做<em>绝对判断</em></strong>（「重问率 12% 说明质量不好」）。"
            "<em>这与 C67 模块 03 里「样本级 vs 系统级」的结论同构："
            "带噪声的信号在配对比较里依然有用，在绝对判断里不可靠。</em>",
        ),
        CALLOUT("intuition", "一个便宜且强推荐的组合：<strong>「自一致性抽样」+「行为分布监控」+「重问率」</strong>。"
                             "<em>三者都不需要标注、都能全自动跑、成本近乎为零</em>，"
                             "而且覆盖了三个不同的失败方向——"
                             "<strong>模型不稳定、行为漂移、用户没被满足。</strong>"
                             "（这与 C67 模块 05 第 6 节推荐的「可验证任务正确率 + 行为分布监控」是同一个思路。）"),
    ])),

    # ============================================================== 6
    ("feedback-loop", "闭环：把线上信号送回离线任务集", "".join([
        P("这是本课的落点，也是把「评测基础设施」与「模型改进」连起来的那一环。"),
        ASCII("""
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   线上流量 ──► guardrail 触发 / 负反馈 / 低置信 / 高重问      │
   │                          │                                   │
   │                          ▼                                   │
   │              ① 采样与去标识化（PII）                          │
   │                          ▼                                   │
   │              ② 人工确认「这确实是个问题」                     │
   │                          ▼                                   │
   │              ③ 写成可判分的任务（C66-01 的六条规则）           │
   │                          ▼                                   │
   │              ④ 进入任务集的**新版本**（C68-01：只增不改）      │
   │                          ▼                                   │
   │   离线评测 ──► CI 门禁 ──► 发布 ──────────────────────────────┘
   │                                                              │
   └──── 从此这个问题**永远不会再悄悄回来**（这就是回归测试的意义）  ┘
"""),
        H3("四个必须做对的细节"),
        OL([
            "<strong>去标识化必须在采样时做，不是在入库后做</strong>——"
            "<em>一旦真实用户数据进了任务集仓库，清理成本就高得多</em>；"
            "而且任务集通常会被更多人访问。",
            "<strong>人工确认这一步不能省</strong>：guardrail 触发不等于模型错了"
            "（可能是 guardrail 误伤）。<em>不确认就入库，等于把 guardrail 的误伤固化成了「标准答案」</em>。",
            "<strong>写成可判分的任务</strong>：这是 C66 模块 01 的六条规则"
            "（先写判分函数再写任务、要有防回归检查项、难度要有梯度……）。"
            "<em>「把线上 case 直接贴成一道题」通常判不了分</em>。",
            "<strong>进新版本而不是改旧版本</strong>（模块 01）——"
            "而且要<strong>标注来源为 <code>from_production</code></strong>，"
            "<em>因为这批任务的分布与人工构造的任务不同，分析时需要能分开</em>。",
        ]),
        CALLOUT("warn", "闭环有一个必须防的退化模式：<strong>任务集逐渐被「线上出过问题的 case」填满</strong>。"
                        "<em>这些 case 按定义是模型的弱项，所以任务集会变得越来越难、分数越来越低</em>，"
                        "而且<strong>它不再代表真实流量的分布</strong>。"
                        "<strong>缓解：给 <code>from_production</code> 的任务设一个占比上限（比如 30%），"
                        "并且同时从线上做<em>均匀随机</em>采样来补充「正常」的任务</strong>——"
                        "否则任务集会漂成一个「疑难杂症集」。"),
        H3("闭环的健康指标"),
        UL([
            "<strong>回灌延迟</strong>：从线上发现问题到它进入任务集的时间。"
            "<em>超过一个月，闭环基本等于不存在</em>；",
            "<strong>复发率</strong>：<strong>已经进了任务集的问题，有没有在线上再次出现</strong>。"
            "<em>这是闭环有没有真的起作用的唯一硬指标</em>；",
            "<strong>任务集的来源构成</strong>：人工构造 vs 线上回灌的比例，以及后者是否超了上限。",
        ]),
    ])),

    # ============================================================== 7
    ("wrap", "全课收尾：五层之间的信息流", "".join([
        P("把本课五个模块串起来，是一条从「声明」到「反馈」的完整回路："),
        ASCII("""
   ① SPEC      评什么、怎么判、版本与指纹        ─┐
        │                                        │
   ② RUNNER    并发/重试/缓存/预算，幂等可续      │  离线
        │                                        │
   ③ STORE     一条 rollout 一行，只追加          │
        │                                        │
   ④ CI GATE   确定性检查 + 配对统计门禁         ─┘
        │
        ▼  发布
   ⑤ ONLINE    漂移 / guardrail / 无标签信号
        │
        └──────────► 回灌 ──► ① 的新版本任务集
"""),
        TABLE(["模块", "它保证的性质", "缺了它会怎样"], [
            ["<strong>01 SPEC</strong>", "可归因（差异指向配置项）", "两次运行的差异说不清楚"],
            ["<strong>02 RUNNER</strong>", "执行不污染结果", "缓存读到旧结果、重试抬高分数——都不报错"],
            ["<strong>03 STORE</strong>", "未来能问出新问题", "换个口径就要重跑，于是大多数问题不会被问"],
            ["<strong>04 CI GATE</strong>", "退化进不了主干", "退化上线；或门禁误报太多被关掉"],
            ["<strong>05 ONLINE</strong>", "离线看不见的问题被抓住", "离线一直涨，线上一直没感觉"],
        ]),
        DUAL(
            "回头看，这五层解决的其实是同一个问题的五个面："
            "<strong>怎么让「这个数字变了」这件事变得可解释。</strong>"
            "<em>可归因（01）、不被执行污染（02）、可重新切片（03）、"
            "可被自动判断（04）、可被真实世界校验（05）</em>——"
            "五层都在服务同一个目标。",
            "而这个目标本身来自 C66 与 C67 的那条主线：<strong>先验证测量仪器，再相信读数。</strong>"
            "<em>C66 教你怎么量一个 agent，C67 教你怎么验证判分器，"
            "本课教你怎么让这套测量能被可靠地、重复地、便宜地执行。</em>"
            "<strong>三者合起来，才构成一个可以支撑决策的评测体系</strong>——"
            "而缺了本课这一环，前两课的方法只能被执行一次，"
            "然后在第二次执行时因为某个没被记录的配置项而失去可比性。",
        ),
        CALLOUT("intuition", "如果这门课只带走一句话：<strong>基础设施的价值不在于跑得快，"
                             "而在于它让「结果变了」这件事有唯一的解释。</strong>"
                             "<em>而所有的工程决策——spec 是纯数据、缓存键含指纹、"
                             "主键三元组、聚合后置、阈值从方差推、线上信号回灌——"
                             "都是在服务这一条。</em>"),
        P("<strong>下一门课 C69 · Agent 安全与提示注入</strong>："
          "本课模块 03 的 guardrail 是<em>质量护栏</em>，"
          "而当输入里有人<strong>主动</strong>想让 agent 做坏事时，需要的是另一套东西——"
          "攻击面在哪、怎么量它、怎么防。"),
    ])),
    # ============================================================== 7x
    ("shadow", "影子运行：零风险地拿到真实分布上的配对样本", "".join([
        P("C66 模块 05 第 7 节提到过影子运行。这一节把它放在监控的语境里重讲，"
          "因为它填补了离线评测与线上 A/B 之间的一个空档。"),
        ASCII("""
   真实请求 ──┬──► 现网模型 ──► 返回给用户
              │
              └──► 候选模型 ──► **不返回**，只落库
                                    │
                                    ▼
                   两个输出在同一个真实请求上配对 ──► 判分器比较
"""),
        TABLE(["方式", "用户暴露", "样本分布", "配对", "需要金标准吗"], [
            ["离线评测", "0%", "<strong>人挑的，通常有偏</strong>", "是（同一批任务）", "是"],
            ["<strong>影子运行</strong>", "<strong>0%</strong>", "<strong>真实流量</strong>", "<strong>是</strong>（同一个请求）", "<strong>否</strong>（比较两个输出即可）"],
            ["金丝雀 / A-B", "1–100%", "真实流量", "否（不同用户）", "否（看线上指标）"],
        ]),
        DUAL(
            "影子运行填的空档很具体：<strong>它同时具备「真实分布」与「配对」两个性质，"
            "而离线评测只有配对、A/B 只有真实分布。</strong>"
            "<em>配对意味着方差极低（同一个请求，两个版本），"
            "真实分布意味着它测的是用户实际会问的东西</em>——"
            "这两条加起来，让影子运行成为检测「离线覆盖不到的退化」最灵敏的手段。",
            "代价有两个，都要提前想清楚："
            "<strong>① 双倍推理成本</strong>（可以靠采样比例控制，1–5% 通常就够）；"
            "<strong>② 需要一个能比较两个输出的判分器</strong>——"
            "<em>而这正好是 C67 的内容，包括它的全部偏差问题</em>。"
            "<strong>特别要注意的是位置偏差：比较现网输出与候选输出时，"
            "必须做 swap 双跑</strong>（C67-02），"
            "<em>否则「候选更好」这个结论可能只是因为它被放在了第二位。</em>",
        ),
        CALLOUT("warn", "影子运行还有一个必须处理的工程细节：<strong>副作用。</strong>"
                        "<em>如果候选模型是一个 agent，它可能会真的去调用工具、写数据库</em>——"
                        "<strong>影子运行必须跑在只读或沙箱化的工具集上</strong>，"
                        "否则「零用户暴露」这个前提就不成立了。"
                        "这与 C69 的沙箱与权限边界是同一套机制。"),
    ])),

    # ============================================================== 8
    ("cost-of-monitoring", "监控本身的成本与优先级", "".join([
        P("本课列了十几种监控信号。全部都上是不现实的，"
          "这一节给出<strong>按性价比排序的建设顺序</strong>。"),
        TABLE(["优先级", "建什么", "成本", "覆盖什么失败", "为什么是这个顺序"], [
            ["<strong>P0</strong>", "错误率 / 延迟 / 成本的基础监控", "极低（通常已有）", "系统挂了", "不建这个，后面所有信号都不可信"],
            ["<strong>P0</strong>", "<strong>输出行为分布</strong>（长度、格式密度、拒答率）", "<strong>极低</strong>（纯统计，无标注无调用）", "模型行为漂移", "<strong>零成本，且是最早的预警信号</strong>"],
            ["<strong>P1</strong>", "重问率 / 用户行为代理", "低（需要会话拼接）", "用户没被满足", "与真实满意度强相关，且无需标注"],
            ["<strong>P1</strong>", "L0 确定性 guardrail", "低", "格式错误、越界输出", "零误伤，可放心拦截"],
            ["<strong>P2</strong>", "输入分布漂移（PSI/KS）", "低", "流量构成变化", "它只说「变了」，需要配合抽样才有结论"],
            ["<strong>P2</strong>", "自一致性抽样", "中（双倍推理，但只抽 1%）", "模型不稳定", "抽样比例可以很低"],
            ["<strong>P3</strong>", "每周人工抽样标注", "<strong>高</strong>（人力）", "真实质量", "唯一的金标准，但要等前面几层把范围缩小"],
            ["<strong>P3</strong>", "L2 LLM guardrail", "高（每请求一次额外调用）", "语义问题", "误伤落在用户身上，要先把 α/β 量出来（C67）"],
        ]),
        CALLOUT("intuition", "这张表最重要的是第二行：<strong>输出行为分布监控是零成本的</strong>——"
                             "它不需要标注、不需要额外调用、不需要金标准，"
                             "只是对已有日志做几个统计。"
                             "<em>而它覆盖的正是 C67 模块 05 里那四种 reward hacking 形态</em>"
                             "（长度膨胀、格式套路化、自信化、拒答漂移）。"
                             "<strong>如果你只能建一样东西，建这个。</strong>"),
        H3("从监控到诊断：三层漏斗"),
        P("上面那张表还隐含了一个结构：<strong>这些信号构成一个漏斗，"
          "每一层的作用是把「需要人看」的范围缩小一个数量级。</strong>"),
        ASCII("""
   全量流量 (10^6/天)
        │  P0: 行为分布 + 错误率     ← 零成本，全量覆盖
        ▼
   异常时段/切片 (10^4)
        │  P1: 重问率 + guardrail    ← 低成本，定位到具体场景
        ▼
   可疑样本 (10^2)
        │  P2: 自一致性 + PSI 驱动抽样
        ▼
   人工标注 (10^1-10^2/周)          ← 唯一的金标准，也是唯一贵的一层
"""),
        P("<strong>建设顺序应当自上而下</strong>：先建全量的零成本层，让它把范围缩小，"
          "再让昂贵的人力只处理最后那一小撮。"
          "<em>反过来做（一上来就大规模人工标注）的问题不是「太贵」，"
          "而是「抽样是随机的，因此大概率抽不到真正出问题的地方」</em>——"
          "这与第 4 节抽样策略的讨论是同一件事。"),
        H3("一个容易被忽略的成本：监控自己的可靠性"),
        P("<strong>监控系统本身也会坏，而且它坏了的时候不会告警</strong>"
          "（因为告警就是它的职责）。三条便宜的防御："),
        UL([
            "<strong>心跳指标</strong>：监控管道每分钟写一个计数器。"
            "<em>「指标停止上报」应当触发告警，而不是被当成「一切正常」</em>；",
            "<strong>合成流量</strong>：定期发几条已知答案的请求走完整链路，"
            "<em>它同时验证了服务与监控两条链路</em>；",
            "<strong>告警的告警</strong>：如果某个指标连续 N 天没有任何波动，"
            "<em>那通常不是「非常稳定」，而是「数据源断了」</em>。",
        ]),
        DUAL(
            "最后一条值得单独说：<strong>「指标异常地平稳」是一个被严重低估的故障信号。</strong>"
            "<em>真实指标总是有噪声的；一条完全水平的曲线，"
            "十有八九是采集断了、或者读到了缓存、或者除数被写死了。</em>",
            "这与模块 02 的「首次运行缓存命中率非 0」是同一类诊断："
            "<strong>都是在检查「一个本该变化的量为什么没有变化」</strong>。"
            "<em>这类检查的共同特点是：它们抓的不是「值超出了范围」，"
            "而是「值的<strong>行为</strong>不对」</em>——"
            "而后者往往对应着更根本的故障（数据没进来、代码路径没被执行），"
            "却几乎不会被常规的阈值告警覆盖。",
        ),
    ])),
]

NB = [
    md("""# 05 · 线上监控与漂移（离线-在线相关性 / PSI 与 KS / guardrail / 抽样 / 无标签信号 / 闭环）

目标：把「离线涨了线上没涨」从一个玄学问题，变成**可以按顺序诊断的三步**。

本 notebook 你会亲手实现：
1. **离线-在线的两层不匹配** —— 分布偏移 vs 口径不同，两者的诊断与修法完全不同
2. **PSI 与 KS** —— 以及「PSI 高不等于变差了」这个必须说清的局限
3. **无标签信号** —— 自一致性 / 行为分布 / 重问率，三者覆盖三个失败方向
4. **guardrail 分层** —— 误伤率与触发率的权衡，以及为什么 L2 不该直接拒答
5. **抽样策略** —— 均匀 vs 分层 vs 异常驱动；尾部采样的选择偏倚
6. **闭环健康度** —— 回灌延迟、复发率、任务集来源构成的上限

> 心智模型：**无标签监控能告诉你「输入/输出变了」，不能告诉你「变差了」。
> 漂移告警的正确动作是触发一次带标签的抽样评测，而不是直接回滚。**"""),

    md("""## 0 · 环境与一个可控的「线上系统」"""),

    code("""import os, json, math, random, itertools
from collections import Counter, defaultdict

import numpy as np

def make_traffic(n, rng, intent_mix=None, len_scale=1.0, shift=0.0):
    \"\"\"生成线上请求。intent 是场景类别，latent 是「这条请求有多难」。\"\"\"
    mix = intent_mix or {'faq': 0.55, 'billing': 0.25, 'troubleshoot': 0.15, 'other': 0.05}
    intents = list(mix); probs = np.array([mix[i] for i in intents], dtype=float)
    probs = probs / probs.sum()
    idx = rng.choice(len(intents), size=n, p=probs)
    latent = np.clip(rng.beta(2, 2, n) + shift, 0, 1)
    return [{'req_id': f'r{i:06d}', 'intent': intents[k],
             'length': int(np.clip(rng.lognormal(4.2, 0.6) * len_scale, 5, 4000)),
             'latent': float(l)}
            for i, (k, l) in enumerate(zip(idx, latent))]

BASE_QUALITY = {'faq': 0.92, 'billing': 0.70, 'troubleshoot': 0.45, 'other': 0.55}

def serve(reqs, rng, model_shift=0.0, verbosity=1.0):
    \"\"\"模拟线上服务：产出回答的质量（我们知道，系统不知道）与可观测的行为指标。\"\"\"
    out = []
    for r in reqs:
        p = float(np.clip(BASE_QUALITY[r['intent']] + model_shift - 0.5 * (r['latent'] - 0.5),
                          0.01, 0.99))
        good = bool(rng.random() < p)
        out.append({**r, 'good': good,
                    'resp_len': int(np.clip(rng.lognormal(4.6, 0.5) * verbosity, 10, 6000)),
                    'md_density': float(np.clip(rng.beta(2, 6) * verbosity, 0, 1)),
                    'refused': bool(rng.random() < 0.02),
                    # 重问率：回答不好时用户更可能换个说法再问一遍
                    'reasked': bool(rng.random() < (0.42 if not good else 0.06))})
    return out

rng = np.random.default_rng(0)
online = serve(make_traffic(20000, rng), rng)
print(f'线上样本 {len(online)} 条')
print('意图分布:', {k: round(v / len(online), 3)
                    for k, v in Counter(o['intent'] for o in online).most_common()})
print(f"真实质量（系统看不到）: {np.mean([o['good'] for o in online]):.1%}")
print(f"重问率（系统看得到）:   {np.mean([o['reasked'] for o in online]):.1%}")
print('\\n✅ 「真实质量」我们知道但系统不知道——这让我们能验证「无标签信号有没有用」。')"""),

    md("""## 1 · 离线-在线的两层不匹配

离线指标估计的是 $\\mathbb{E}_{x\\sim D_{off}}[s(x)]$，你关心的是 $\\mathbb{E}_{x\\sim D_{on}}[u(x)]$。
中间隔着**分布**与**口径**两层，两层的修法完全不同。"""),

    code("""# 离线任务集：人工构造，偏向 troubleshoot（因为"难题才值得写成题"）
OFFLINE_MIX = {'faq': 0.15, 'billing': 0.25, 'troubleshoot': 0.55, 'other': 0.05}
offline = serve(make_traffic(2000, np.random.default_rng(1), intent_mix=OFFLINE_MIX),
                np.random.default_rng(1))

def coverage_report(offline, online):
    off_mix = Counter(o['intent'] for o in offline)
    on_mix = Counter(o['intent'] for o in online)
    n_off, n_on = len(offline), len(online)
    rows = []
    for k in sorted(set(off_mix) | set(on_mix)):
        rows.append((k, off_mix[k] / n_off, on_mix[k] / n_on))
    return rows

print(f"{'意图':<14}{'离线占比':>10}{'线上占比':>10}{'比值':>8}")
for k, po, pn in coverage_report(offline, online):
    print(f'{k:<14}{po:>10.1%}{pn:>10.1%}{(po/pn if pn else float("inf")):>8.2f}')

off_score = np.mean([o['good'] for o in offline])
on_score = np.mean([o['good'] for o in online])
print(f'\\n离线分数 {off_score:.1%} | 线上真实质量 {on_score:.1%} | 差 {off_score-on_score:+.1%}')
assert abs(off_score - on_score) > 0.08, '分布不同 → 两个数字本来就不该相等'
print('✅ 第一层不匹配（分布）：离线任务集里 55% 是 troubleshoot，线上只有 15%。')
print('   → 离线分数系统性偏低，而且**离线的提升主要发生在线上不重要的场景上**。')"""),

    code("""# 用线上分布对离线分数做重加权 —— 这才是可比的口径（= 模块 03 的直接标准化）
def reweight_to_online(offline, online):
    on_mix = Counter(o['intent'] for o in online)
    n_on = len(online)
    by_intent = defaultdict(list)
    for o in offline:
        by_intent[o['intent']].append(float(o['good']))
    num = den = 0.0
    for k, vals in by_intent.items():
        w = on_mix[k] / n_on
        num += w * float(np.mean(vals))
        den += w
    return num / den if den else float('nan')

rw = reweight_to_online(offline, online)
print(f'离线原始   {off_score:.1%}')
print(f'离线重加权 {rw:.1%}   ← 用线上意图分布加权')
print(f'线上真实   {on_score:.1%}')
assert abs(rw - on_score) < abs(off_score - on_score), '重加权后应当更接近线上'
print(f'\\n✅ 重加权把差距从 {abs(off_score-on_score):.1%} 缩到 {abs(rw-on_score):.1%}——')
print('   剩下的差距才是「口径不同」等其他原因。')
print('   → **诊断顺序：先查覆盖率（分布），再谈效应量。**')
print('   很多团队直接从「是不是提升太小了」开始，于是永远在讨论要不要做更大的改动。')"""),

    code("""# 第二层不匹配（口径）：离线测"答案对不对"，线上看"用户满不满意"
def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ac, bc = a - a.mean(), b - b.mean()
    d = math.sqrt(float((ac**2).sum()) * float((bc**2).sum()))
    return float((ac*bc).sum()/d) if d else float('nan')

good = np.array([o['good'] for o in online], float)
satisfied = np.array([not o['reasked'] for o in online], float)
print(f'「答案对不对」与「用户没重问」的相关: {corr(good, satisfied):.3f}')
assert 0.2 < corr(good, satisfied) < 0.9
print('✅ 相关但远非等同——这就是第二层不匹配。')
print('   报告规范：**如果离线指标只是代理指标，必须显式声明**，')
print('   并给出它与线上指标在同一批样本上的相关系数。')"""),

    md("""## 2 · 漂移检测：PSI 与 KS，以及它们的盲区"""),

    code("""def psi(expected, actual, bins=10, eps=1e-6):
    \"\"\"Population Stability Index。分箱边界由基线（expected）决定 —— 这一点很重要。\"\"\"
    e = np.asarray(expected, float); a = np.asarray(actual, float)
    edges = np.quantile(e, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    pe, _ = np.histogram(e, bins=edges); pa, _ = np.histogram(a, bins=edges)
    pe = pe / max(pe.sum(), 1) + eps
    pa = pa / max(pa.sum(), 1) + eps
    return float(np.sum((pa - pe) * np.log(pa / pe)))

def ks_stat(a, b):
    a = np.sort(np.asarray(a, float)); b = np.sort(np.asarray(b, float))
    allv = np.concatenate([a, b])
    fa = np.searchsorted(a, allv, 'right') / len(a)
    fb = np.searchsorted(b, allv, 'right') / len(b)
    return float(np.max(np.abs(fa - fb)))

def psi_categorical(expected, actual, eps=1e-6):
    ce, ca = Counter(expected), Counter(actual)
    keys = set(ce) | set(ca)
    ne, na = max(len(expected), 1), max(len(actual), 1)
    tot = 0.0
    for k in keys:
        pe = ce[k]/ne + eps; pa = ca[k]/na + eps
        tot += (pa - pe) * math.log(pa / pe)
    return float(tot)

base = online
SCENARIOS = {
    '无漂移':        serve(make_traffic(20000, np.random.default_rng(10)), np.random.default_rng(10)),
    '请求变长':      serve(make_traffic(20000, np.random.default_rng(11), len_scale=1.8),
                          np.random.default_rng(11)),
    '意图构成变了':  serve(make_traffic(20000, np.random.default_rng(12),
                                        intent_mix={'faq':0.30,'billing':0.25,
                                                    'troubleshoot':0.40,'other':0.05}),
                          np.random.default_rng(12)),
    '模型变啰嗦':    serve(make_traffic(20000, np.random.default_rng(13)),
                          np.random.default_rng(13), verbosity=1.9),
}
print(f"{'场景':<16}{'PSI(请求长度)':>16}{'PSI(意图)':>12}{'KS(响应长度)':>15}{'真实质量变化':>14}")
for name, cur in SCENARIOS.items():
    p_len = psi([o['length'] for o in base], [o['length'] for o in cur])
    p_int = psi_categorical([o['intent'] for o in base], [o['intent'] for o in cur])
    k_out = ks_stat([o['resp_len'] for o in base], [o['resp_len'] for o in cur])
    dq = np.mean([o['good'] for o in cur]) - np.mean([o['good'] for o in base])
    print(f'{name:<16}{p_len:>16.4f}{p_int:>12.4f}{k_out:>15.4f}{dq:>+14.1%}')

p_none = psi([o['length'] for o in base], [o['length'] for o in SCENARIOS['无漂移']])
p_long = psi([o['length'] for o in base], [o['length'] for o in SCENARIOS['请求变长']])
assert p_none < 0.1 and p_long > 0.25, 'PSI 应当只在真漂移时报警'
dq_verbose = np.mean([o['good'] for o in SCENARIOS['模型变啰嗦']]) - np.mean([o['good'] for o in base])
k_verbose = ks_stat([o['resp_len'] for o in base],
                    [o['resp_len'] for o in SCENARIOS['模型变啰嗦']])
assert k_verbose > 0.3 and abs(dq_verbose) < 0.03
print('\\n⚠️ 看最后一行：模型变啰嗦了（KS=0.4+ 强烈报警），但**真实质量几乎没变**。')
print('✅ 这就是无标签监控的结构性局限：**它能告诉你「变了」，不能告诉你「变差了」。**')
print('   → 漂移告警的正确动作是「触发一次带标签的抽样评测」，而不是直接回滚。')"""),

    md("""## 3 · 无标签信号：三个覆盖不同失败方向的指标"""),

    code("""def self_consistency(reqs, rng, model_shift=0.0, n_pairs=None):
    \"\"\"同一请求采样两次，看两个回答是否一致（好/坏是否相同）。\"\"\"
    sel = reqs if n_pairs is None else reqs[:n_pairs]
    a = serve(sel, np.random.default_rng(101), model_shift=model_shift)
    b = serve(sel, np.random.default_rng(202), model_shift=model_shift)
    return float(np.mean([x['good'] == y['good'] for x, y in zip(a, b)]))

def behavior_profile(rows):
    return {'resp_len_p50': float(np.median([r['resp_len'] for r in rows])),
            'md_density': float(np.mean([r['md_density'] for r in rows])),
            'refusal_rate': float(np.mean([r['refused'] for r in rows])),
            'reask_rate': float(np.mean([r['reasked'] for r in rows]))}

CASES = {
    '基线':          dict(shift=0.0, verbosity=1.0),
    '模型退化 -12pp': dict(shift=-0.12, verbosity=1.0),
    '模型变啰嗦':     dict(shift=0.0, verbosity=1.9),
}
print(f"{'场景':<16}{'真实质量':>10}{'自一致性':>10}{'重问率':>10}{'响应长度P50':>14}{'md密度':>10}")
profiles = {}
for name, cfg in CASES.items():
    reqs = make_traffic(8000, np.random.default_rng(21))
    rows = serve(reqs, np.random.default_rng(22), model_shift=cfg['shift'],
                 verbosity=cfg['verbosity'])
    prof = behavior_profile(rows)
    sc = self_consistency(reqs[:3000], None, model_shift=cfg['shift'])
    profiles[name] = (np.mean([r['good'] for r in rows]), sc, prof)
    print(f'{name:<16}{profiles[name][0]:>10.1%}{sc:>10.1%}{prof["reask_rate"]:>10.1%}'
          f'{prof["resp_len_p50"]:>14.0f}{prof["md_density"]:>10.3f}')

q_base, sc_base, pr_base = profiles['基线']
q_deg, sc_deg, pr_deg = profiles['模型退化 -12pp']
q_verb, sc_verb, pr_verb = profiles['模型变啰嗦']
assert pr_deg['reask_rate'] > pr_base['reask_rate'] + 0.02, '质量退化时重问率必须上升'
assert pr_verb['resp_len_p50'] > 1.5 * pr_base['resp_len_p50'], '变啰嗦时长度必须涨'
assert abs(q_verb - q_base) < 0.03, '变啰嗦但质量没变'
print('\\n✅ 三个信号覆盖三个不同的失败方向：')
print(f'   · 重问率     抓「用户没被满足」 —— 质量掉 12pp 时它涨了 '
      f'{pr_deg["reask_rate"]-pr_base["reask_rate"]:.1%}')
print(f'   · 行为分布   抓「模型行为漂移」 —— 变啰嗦时长度涨了 '
      f'{pr_verb["resp_len_p50"]/pr_base["resp_len_p50"]:.1f} 倍（而质量没变）')
print('   · 自一致性   抓「模型不稳定」')
print('   三者都不需要标注、全自动、成本近乎为零。')"""),

    code("""# 重问率作为质量的代理：适合相对比较，不适合绝对判断
qs, rs = [], []
for shift in [-0.20, -0.12, -0.06, 0.0, 0.06]:
    rows = serve(make_traffic(6000, np.random.default_rng(31)),
                 np.random.default_rng(32), model_shift=shift)
    qs.append(float(np.mean([r['good'] for r in rows])))
    rs.append(float(np.mean([r['reasked'] for r in rows])))
print(f"{'质量':>10}{'重问率':>10}")
for q, r in zip(qs, rs):
    print(f'{q:>10.1%}{r:>10.1%}')
c = corr(qs, rs)
print(f'\\n质量与重问率的相关: {c:.3f}')
assert c < -0.9, '质量越高重问率越低，应当强负相关'
print('✅ 强负相关 → 重问率可以做质量的代理指标。')
print('⚠️ 但它混杂了 UI、用户习惯、流量构成——')
print('   **适合做相对比较（新旧版本同期同流量），不适合做绝对判断**')
print('   （「重问率 12% 说明质量不好」这句话没有依据）。')"""),

    md("""## 4 · Guardrail：分层与误伤率"""),

    code("""def l0_rules(row):
    \"\"\"L0 确定性规则：格式/长度/必填。零误伤（对合法输出永远不触发）。\"\"\"
    return row['resp_len'] > 5000 or row['resp_len'] < 15

def l1_small_model(row, rng, recall=0.55, fpr=0.02):
    \"\"\"L1 小模型：对「坏回答」有一定召回，对好回答有小的误伤率。\"\"\"
    return (rng.random() < recall) if not row['good'] else (rng.random() < fpr)

def l2_llm_judge(row, rng, recall=0.80, fpr=0.08):
    \"\"\"L2 LLM judge：召回更高，但误伤率也更高（C67：judge 的 alpha/beta）。\"\"\"
    return (rng.random() < recall) if not row['good'] else (rng.random() < fpr)

def eval_guardrail(rows, layers, seed=0):
    rng = random.Random(seed)
    trig = {name: 0 for name, _ in layers}
    fired_bad = fired_good = 0
    for r in rows:
        hit = None
        for name, fn in layers:
            if fn(r, rng) if fn.__code__.co_argcount > 1 else fn(r):
                hit = name; break
        if hit:
            trig[hit] += 1
            if r['good']:
                fired_good += 1        # 误伤
            else:
                fired_bad += 1         # 正确拦截
    n_bad = sum(1 for r in rows if not r['good'])
    n_good = len(rows) - n_bad
    return {'trigger_rate': (fired_bad + fired_good) / len(rows),
            'recall': fired_bad / n_bad if n_bad else float('nan'),
            'false_hit_rate': fired_good / n_good if n_good else float('nan'),
            'precision': fired_bad / (fired_bad + fired_good) if (fired_bad + fired_good) else float('nan'),
            'by_layer': trig}

sample = serve(make_traffic(20000, np.random.default_rng(41)), np.random.default_rng(42))
CONFIGS = {
    'L0 only':        [('L0', l0_rules)],
    'L0+L1':          [('L0', l0_rules), ('L1', l1_small_model)],
    'L0+L1+L2':       [('L0', l0_rules), ('L1', l1_small_model), ('L2', l2_llm_judge)],
}
print(f"{'配置':<14}{'触发率':>10}{'召回':>10}{'误伤率':>10}{'精确率':>10}")
res = {}
for name, layers in CONFIGS.items():
    r = eval_guardrail(sample, layers, seed=7)
    res[name] = r
    print(f'{name:<14}{r["trigger_rate"]:>10.2%}{r["recall"]:>10.1%}'
          f'{r["false_hit_rate"]:>10.2%}{r["precision"]:>10.1%}')

assert res['L0+L1+L2']['recall'] > res['L0 only']['recall'], '加层数召回必然上升'
assert res['L0+L1+L2']['false_hit_rate'] > res['L0 only']['false_hit_rate'], '误伤率也必然上升'
print('\\n✅ 加层数：召回上升，**误伤率也上升**——这就是为什么要分层而不是一股脑全上。')
print('   L0 是确定性的（对合法输出永不触发），可以放心**拦截**；')
print(f'   L2 的误伤率 {res["L0+L1+L2"]["false_hit_rate"]:.1%} 落到真实用户身上，')
print('   所以它通常只该**降级或标记**，不该直接拒答。')
print('\\n   ⚠️ 这与模块 04 的 CI 门禁完全同构：误伤率过高 → guardrail 被降级成「只记录」→ 被忘掉。')"""),

    md("""## 5 · 抽样：尾部采样的选择偏倚"""),

    code("""def head_sampling(rows, rate, seed=0):
    \"\"\"头部采样：请求开始时就决定记不记 —— 与结果无关，因此无偏。\"\"\"
    rng = random.Random(seed)
    return [r for r in rows if rng.random() < rate]

def tail_sampling(rows, base_rate, anomaly_rate, seed=0):
    \"\"\"尾部采样：出错/异常的全记，正常的按低比例记 —— 信息量高但有强选择偏倚。\"\"\"
    rng = random.Random(seed)
    out = []
    for r in rows:
        anomalous = (not r['good']) or r['refused'] or r['reasked']
        p = anomaly_rate if anomalous else base_rate
        if rng.random() < p:
            out.append(dict(r, _sample_kind='anomaly' if anomalous else 'normal',
                            _sample_p=p))
    return out

true_q = float(np.mean([r['good'] for r in sample]))
head = head_sampling(sample, 0.05, seed=1)
tail = tail_sampling(sample, base_rate=0.01, anomaly_rate=1.0, seed=1)

q_head = float(np.mean([r['good'] for r in head]))
q_tail_naive = float(np.mean([r['good'] for r in tail]))
# 逆概率加权（IPW）修正尾部采样的偏倚
w = np.array([1.0 / r['_sample_p'] for r in tail])
q_tail_ipw = float(np.sum(w * np.array([r['good'] for r in tail], float)) / np.sum(w))

print(f'真实质量               {true_q:.1%}')
print(f'头部采样（5%, n={len(head)}）  {q_head:.1%}   偏差 {q_head-true_q:+.1%}')
print(f'尾部采样朴素平均（n={len(tail)}） {q_tail_naive:.1%}   偏差 {q_tail_naive-true_q:+.1%}  ← 严重低估')
print(f'尾部采样 + IPW 加权         {q_tail_ipw:.1%}   偏差 {q_tail_ipw-true_q:+.1%}')
assert abs(q_head - true_q) < 0.02, '头部采样无偏'
assert q_tail_naive < true_q - 0.15, '尾部采样朴素平均严重低估质量'
assert abs(q_tail_ipw - true_q) < abs(q_tail_naive - true_q), 'IPW 必须改善'
print('\\n✅ 尾部采样的数据**不能直接算平均**——它按定义就富集了异常样本。')
print('   要么做 IPW 加权，要么只把它当诊断素材而不是统计样本。')
print('   → 实践组合：**头部固定比例（无偏统计）+ 尾部全量记录异常（诊断）**，')
print('     并且用一个字段标明这条数据是怎么被采到的——没有它，两类数据混在一起就再也分不开。')"""),

    md("""## 6 · 闭环健康度：回灌延迟、复发率、来源构成"""),

    code("""def loop_health(incidents, task_set, today=100):
    \"\"\"incidents: [{'id','found_day','ingested_day'(可None),'recurred':bool}]
    task_set: [{'task_id','source'}]\"\"\"
    ingested = [i for i in incidents if i['ingested_day'] is not None]
    lat = [i['ingested_day'] - i['found_day'] for i in ingested]
    recur = [i for i in ingested if i['recurred']]
    src = Counter(t['source'] for t in task_set)
    n = max(len(task_set), 1)
    return {
        'n_incidents': len(incidents),
        'ingest_rate': len(ingested) / max(len(incidents), 1),
        'median_latency_days': float(np.median(lat)) if lat else float('nan'),
        'p90_latency_days': float(np.percentile(lat, 90)) if lat else float('nan'),
        'recurrence_rate': len(recur) / max(len(ingested), 1),
        'prod_share': src.get('from_production', 0) / n,
    }

rng = np.random.default_rng(5)
INCIDENTS = []
for i in range(60):
    found = int(rng.integers(0, 80))
    ingested = found + int(rng.gamma(2, 6)) if rng.random() < 0.75 else None
    INCIDENTS.append({'id': f'inc{i:03d}', 'found_day': found,
                      'ingested_day': ingested,
                      'recurred': bool(rng.random() < 0.08)})
TASK_SET = ([{'task_id': f'm{i}', 'source': 'manual'} for i in range(340)]
            + [{'task_id': f'p{i}', 'source': 'from_production'} for i in range(160)])

h = loop_health(INCIDENTS, TASK_SET)
THRESH = {'ingest_rate': ('>=', 0.70), 'median_latency_days': ('<=', 14),
          'p90_latency_days': ('<=', 30), 'recurrence_rate': ('<=', 0.10),
          'prod_share': ('<=', 0.30)}
print(f"{'指标':<24}{'实测':>10}{'阈值':>14}{'状态':>8}")
alerts = []
for k, (op, v) in THRESH.items():
    cur = h[k]
    ok = (cur >= v) if op == '>=' else (cur <= v)
    if not ok:
        alerts.append(k)
    fmt = f'{cur:.1%}' if k in ('ingest_rate', 'recurrence_rate', 'prod_share') else f'{cur:.1f}'
    print(f'{k:<24}{fmt:>10}{f"{op} {v}":>14}{"✅" if ok else "⚠️":>8}')

assert 'prod_share' in alerts, '本例中线上回灌占比超了上限'
print(f'\\n未达标: {alerts}')
print(f'\\n⚠️ prod_share = {h["prod_share"]:.0%} > 30% —— 任务集正在漂成一个「疑难杂症集」。')
print('   这些 case 按定义是模型的弱项，占比过高会让任务集不再代表真实流量分布。')
print('   → 缓解：给 from_production 设占比上限，并同时从线上做**均匀随机**采样补充「正常」任务。')
print('\\n✅ 三个健康指标里，**复发率**是闭环有没有真的起作用的唯一硬指标——')
print('   已经进了任务集的问题又在线上出现，说明回归测试没起到作用。')"""),

    md("""## ✏️ 练习 1：漂移告警的分级

实现 `drift_verdict(psi_value, quality_delta=None)`：
- `psi_value < 0.1` → `'stable'`
- `0.1 <= psi < 0.25` → `'watch'`
- `psi >= 0.25` 且 `quality_delta is None` → `'investigate'`（触发带标签抽样）
- `psi >= 0.25` 且 `quality_delta <= -0.03` → `'degraded'`
- `psi >= 0.25` 且 `quality_delta > -0.03` → `'benign_shift'`（变了但没变差）"""),

    code("""def drift_verdict(psi_value, quality_delta=None):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert drift_verdict(0.05) == 'stable'
assert drift_verdict(0.18) == 'watch'
assert drift_verdict(0.40) == 'investigate'
assert drift_verdict(0.40, -0.08) == 'degraded'
assert drift_verdict(0.40, +0.01) == 'benign_shift'
p_verbose = psi([o['resp_len'] for o in base],
                [o['resp_len'] for o in SCENARIOS['模型变啰嗦']])
print(f'「模型变啰嗦」的 PSI(响应长度) = {p_verbose:.3f}')
print(f'  只看 PSI:            {drift_verdict(p_verbose)}')
print(f'  抽样评测后（质量没变）: {drift_verdict(p_verbose, dq_verbose)}')
assert drift_verdict(p_verbose) == 'investigate'
assert drift_verdict(p_verbose, dq_verbose) == 'benign_shift'
print('✅ 练习 1 通过：`investigate` 这一档是关键——')
print('   它把「触发带标签抽样」和「判定为退化」分成了两步，')
print('   避免了「PSI 高就回滚」这种把「变了」误当成「变差了」的错误。')"""),

    md("""## ✏️ 练习 2：Guardrail 的期望代价

实现 `guardrail_cost(recall, fpr, bad_rate, cost_miss=10.0, cost_false_hit=1.0)`：
返回 `{'miss_cost', 'false_hit_cost', 'total'}`，
其中漏放代价 = `bad_rate * (1-recall) * cost_miss`，
误伤代价 = `(1-bad_rate) * fpr * cost_false_hit`。
用它找出「加 L2 到底划不划算」。"""),

    code("""def guardrail_cost(recall, fpr, bad_rate, cost_miss=10.0, cost_false_hit=1.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
BAD = 1 - true_q
c_l1 = guardrail_cost(res['L0+L1']['recall'], res['L0+L1']['false_hit_rate'], BAD)
c_l2 = guardrail_cost(res['L0+L1+L2']['recall'], res['L0+L1+L2']['false_hit_rate'], BAD)
print(f'坏回答比例 {BAD:.1%}')
print(f"{'配置':<12}{'漏放代价':>12}{'误伤代价':>12}{'总代价':>10}")
for name, c in [('L0+L1', c_l1), ('L0+L1+L2', c_l2)]:
    print(f'{name:<12}{c["miss_cost"]:>12.4f}{c["false_hit_cost"]:>12.4f}{c["total"]:>10.4f}')
assert c_l2['miss_cost'] < c_l1['miss_cost'], '加 L2 减少漏放'
assert c_l2['false_hit_cost'] > c_l1['false_hit_cost'], '但增加误伤'
better = 'L0+L1+L2' if c_l2['total'] < c_l1['total'] else 'L0+L1'
print(f'\\n代价比 10:1 时更优的配置: {better}')
# 误伤代价变高时结论会翻转
c_l1b = guardrail_cost(res['L0+L1']['recall'], res['L0+L1']['false_hit_rate'], BAD, 10.0, 8.0)
c_l2b = guardrail_cost(res['L0+L1+L2']['recall'], res['L0+L1+L2']['false_hit_rate'], BAD, 10.0, 8.0)
print(f'误伤代价提到 8 时: L0+L1 {c_l1b["total"]:.4f} vs L0+L1+L2 {c_l2b["total"]:.4f}')
assert c_l2b['total'] < c_l1b['total'], '误伤代价 8 时 L2 仍然更优'
# 继续提高误伤代价，直到结论翻转 —— 找出那个临界点
flip = None
for cf in [1, 2, 4, 8, 12, 16, 20, 30, 50]:
    a = guardrail_cost(res['L0+L1']['recall'], res['L0+L1']['false_hit_rate'], BAD, 10.0, cf)
    b = guardrail_cost(res['L0+L1+L2']['recall'], res['L0+L1+L2']['false_hit_rate'], BAD, 10.0, cf)
    if b['total'] > a['total']:
        flip = cf
        break
print(f'\\n误伤代价涨到 {flip} 时（漏放代价固定为 10），结论翻转为 L0+L1 更优')
assert flip is not None and flip > 8
print('✅ 练习 2 通过：「该不该加 L2」没有普遍答案——它取决于漏放与误伤的**代价比**。')
print(f'   本例的临界比是 10 : {flip}，也就是说：')
print('   **只有当「误伤一个好回答」的代价超过「漏放一个坏回答」的一倍多时，L2 才不划算。**')
print('   这个比值必须由业务显式给出，不能由工程师默认——')
print('   而在「拒答」这种直接伤害用户体验的动作上，误伤代价往往比想象中高得多。')"""),

    md("""## ✏️ 练习 3：采样方式的标注与合并

实现 `combined_estimate(rows)`：输入带 `_sample_kind` 与 `_sample_p` 字段的样本，
返回 `{'naive', 'ipw', 'n_normal', 'n_anomaly'}`。
`naive` 是朴素平均，`ipw` 是逆概率加权平均。"""),

    code("""def combined_estimate(rows):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
ce = combined_estimate(tail)
print(f'真实质量 {true_q:.1%}')
print(f'朴素平均 {ce["naive"]:.1%} (n_normal={ce["n_normal"]}, n_anomaly={ce["n_anomaly"]})')
print(f'IPW 加权 {ce["ipw"]:.1%}')
assert ce['n_anomaly'] > 0 and ce['n_normal'] > 0
assert abs(ce['ipw'] - true_q) < abs(ce['naive'] - true_q)
# 采样率相同时两者应当一致
uniform = [dict(r, _sample_kind='normal', _sample_p=0.05) for r in head]
cu = combined_estimate(uniform)
assert abs(cu['naive'] - cu['ipw']) < 1e-9, '均匀采样时 IPW 退化为朴素平均'
print('\\n均匀采样时: 朴素 = IPW ✓（IPW 在无偏采样下自动退化成不做任何事）')
print('✅ 练习 3 通过：`_sample_p` 这个字段是把两类数据合并统计的唯一途径——')
print('   不记它，尾部采样的数据就只能当诊断素材，永远进不了统计。')"""),

    md("""## ✏️ 练习 4：闭环的复发率追踪

实现 `recurrence_report(incidents, window_days=60)`：
只统计「入库后至少观察了 window_days」的事件，返回
`{'n_tracked', 'n_recurred', 'recurrence_rate', 'healthy'}`，
`healthy` 表示复发率 ≤ 10%。假设今天是第 100 天。"""),

    code("""def recurrence_report(incidents, window_days=60, today=100):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
rr = recurrence_report(INCIDENTS)
print(f'追踪中的事件 {rr["n_tracked"]} 条 | 复发 {rr["n_recurred"]} 条 | '
      f'复发率 {rr["recurrence_rate"]:.1%} | 健康={rr["healthy"]}')
assert rr['n_tracked'] < len([i for i in INCIDENTS if i['ingested_day'] is not None]), \\
    '未观察满窗口的事件应被排除'
assert 0 <= rr['recurrence_rate'] <= 1
bad = [{'id': 'x', 'found_day': 0, 'ingested_day': 1, 'recurred': True}] * 10
assert recurrence_report(bad)['healthy'] is False
empty = recurrence_report([{'id': 'y', 'found_day': 90, 'ingested_day': 95, 'recurred': False}])
assert empty['n_tracked'] == 0 and math.isnan(empty['recurrence_rate'])
print('\\n刚入库不久的事件被正确排除（观察窗口不足），空样本返回 nan ✓')
print('✅ 练习 4 通过：复发率是闭环有没有真的起作用的**唯一硬指标**——')
print('   回灌延迟再短，如果问题照样复发，说明那道题写得不对（判分器没抓住真正的失败模式）。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def drift_verdict(psi_value, quality_delta=None):
    if psi_value < 0.1:
        return 'stable'
    if psi_value < 0.25:
        return 'watch'
    if quality_delta is None:
        return 'investigate'
    return 'degraded' if quality_delta <= -0.03 else 'benign_shift'"""),

    code("""# 练习 2 参考答案
def guardrail_cost(recall, fpr, bad_rate, cost_miss=10.0, cost_false_hit=1.0):
    miss = bad_rate * (1 - recall) * cost_miss
    fh = (1 - bad_rate) * fpr * cost_false_hit
    return {'miss_cost': miss, 'false_hit_cost': fh, 'total': miss + fh}"""),

    code("""# 练习 3 参考答案
def combined_estimate(rows):
    if not rows:
        return {'naive': float('nan'), 'ipw': float('nan'),
                'n_normal': 0, 'n_anomaly': 0}
    vals = np.array([float(r['good']) for r in rows])
    w = np.array([1.0 / r['_sample_p'] for r in rows])
    return {'naive': float(vals.mean()),
            'ipw': float((w * vals).sum() / w.sum()),
            'n_normal': sum(1 for r in rows if r['_sample_kind'] == 'normal'),
            'n_anomaly': sum(1 for r in rows if r['_sample_kind'] == 'anomaly')}"""),

    code("""# 练习 4 参考答案
def recurrence_report(incidents, window_days=60, today=100):
    tracked = [i for i in incidents
               if i['ingested_day'] is not None
               and today - i['ingested_day'] >= window_days]
    n = len(tracked)
    rec = sum(1 for i in tracked if i['recurred'])
    rate = (rec / n) if n else float('nan')
    return {'n_tracked': n, 'n_recurred': rec, 'recurrence_rate': rate,
            'healthy': bool(n and rate <= 0.10)}"""),

    md("""---
## 🧪 真实工程胶囊：线上监控的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 埋点：沿用 OpenTelemetry GenAI 语义约定（C66-03 已经讲过一次）
# ══════════════════════════════════════════════════════════════════
with tracer.start_as_current_span("gen_ai.chat") as sp:
    sp.set_attribute("gen_ai.request.model", MODEL_ID)
    sp.set_attribute("gen_ai.usage.input_tokens", n_in)
    sp.set_attribute("gen_ai.usage.output_tokens", n_out)
    # 监控必需的自定义属性:
    sp.set_attribute("app.intent", intent)              # 分层与漂移
    sp.set_attribute("app.guardrail.layer", hit_layer)  # guardrail 触发在哪层
    sp.set_attribute("app.sample_kind", kind)           # head | tail_anomaly ← **必须记**
    sp.set_attribute("app.sample_p", p)                 # 逆概率加权需要
# 没有 sample_kind / sample_p，头部与尾部采样的数据混在一起就再也分不开了。

# ══════════════════════════════════════════════════════════════════
# B. 每日自动跑的监控（全部无标签，成本近乎为零）
# ══════════════════════════════════════════════════════════════════
DAILY = {
  "psi_request_length":  lambda: psi(baseline.req_len, today.req_len),
  "psi_intent":          lambda: psi_categorical(baseline.intent, today.intent),
  "resp_len_p50":        ...,   # 行为漂移（C67-05 的 hack 形态）
  "md_density":          ...,
  "refusal_rate":        ...,
  "reask_rate":          ...,   # 用户没被满足（最有价值的无标签信号）
  "self_consistency":    ...,   # 抽 1% 请求跑两次
  "guardrail_trigger":   ...,   # 按层分开
}
# 告警规则用 drift_verdict（练习 1）：
#   PSI 高 → **investigate**（触发带标签抽样），而不是直接回滚。

# ══════════════════════════════════════════════════════════════════
# C. 每周人工抽样（三段结构，与 C67-03 的元评测集同构）
# ══════════════════════════════════════════════════════════════════
# main_sample/      均匀随机 200 条  → 无偏估计整体质量
# uncertainty/      低置信/swap 不一致 100 条 → 判分器与模型的边界
# incident/         guardrail 触发 + 负反馈 全量 → 该修什么
# **三者分开统计，绝不混算。**

# ══════════════════════════════════════════════════════════════════
# D. 闭环的四个细节（讲解第 6 节）
# ══════════════════════════════════════════════════════════════════
# 1. 去标识化在**采样时**做，不是入库后
# 2. 人工确认「这确实是模型的问题」——guardrail 触发 != 模型错了
# 3. 写成可判分的任务（C66-01 的六条规则），不是直接贴原文
# 4. 进任务集**新版本**（C68-01 只增不改），source='from_production'
#    并设占比上限（<= 30%），否则任务集会漂成「疑难杂症集」
#
# 健康指标: 回灌延迟中位 <= 14 天 · 复发率 <= 10% · prod_share <= 30%
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 两层不匹配 | 分布 vs 口径；先查覆盖率，再谈效应量 | 「离线涨了线上没涨」 |
| 重加权 | 用线上分布给离线分数加权，才是可比的口径 | 离线-在线对齐 |
| PSI/KS 的局限 | 能告诉你「变了」，不能告诉你「变差了」 | 漂移告警的动作 |
| 三个无标签信号 | 自一致性 / 行为分布 / 重问率，覆盖三个失败方向 | 每日监控 |
| Guardrail 分层 | L0 可拦截，L2 通常只该降级——误伤落在真实用户身上 | 实时护栏 |
| 尾部采样的偏倚 | 不能直接算平均；必须记 `sample_kind` 与 `sample_p` | 采样设计 |
| 闭环健康度 | 复发率是唯一硬指标；`from_production` 要设占比上限 | 反馈回路 |

**全课收尾**：01 声明 → 02 执行 → 03 存储 → 04 门禁 → 05 线上与回灌。
五层服务同一个目标：**让「这个数字变了」这件事有唯一的解释。**

**下一门课 C69 · Agent 安全与提示注入**：本课的 guardrail 是质量护栏，
而当输入里有人**主动**想让 agent 做坏事时，需要的是另一套东西——
攻击面在哪、怎么量它、怎么防。""")
]
