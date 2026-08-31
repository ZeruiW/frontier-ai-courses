# -*- coding: utf-8 -*-
"""C71 模块 05 · 提示的运维与跨模型迁移。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "（术语：本课的「灰度」对应 C66–C69 的<strong>金丝雀发布</strong>）· "
                 "读过本课模块 01（签名 / 三个量 / 版本化）与 03（优化与留出集）；"
                 "C70 模块 05（索引运维：影子 + 双写 + 原子切换）读过更好——本课复用它的结构"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_prompt_ops.ipynb'
                       '（四个「模型」的模拟器 / 同一个 prompt 的跨模型分数跨度 / '
                       '**为 A 优化的 prompt 在 B 上可能比基线更差** / '
                       '迁移的分层复核与阈值 / token 成本与前缀缓存 / '
                       '灰度与回滚 / 监控四项 / prompt 运维卡与门禁）'),
    ("核心参考", "本课程 C70 模块 05（影子 + 双写 + 原子切换 + 回滚，本课直接复用这套结构）· "
                 "C68 模块 04（门禁分级与阈值从方差推）· C68 模块 05（漂移与 PSI）· "
                 "C33 模块 05（前缀缓存与稳定前缀）· "
                 "C03 模块 03（prompt 敏感性——它解释了为什么迁移必然出问题）· "
                 "C48 / C37（灰度发布与回滚的一般做法）"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("asset-that-rots", "prompt 是会腐烂的资产", "".join([
        P("前四个模块把 prompt 做成了一个可测、可搜、可保证的对象。"
          "<strong>这一节处理一个不同性质的问题：它会失效，而失效的原因通常不在你这边。</strong>"),
        TABLE(["失效类型", "触发", "症状", "能不能提前发现"], [
            ["<strong>模型换小版本</strong>", "服务方静默更新",
             "<em>分数缓慢变化；预测分布偏移</em>",
             "<strong>能</strong>——把模型版本钉死 + 监控预测分布（第 6 节）"],
            ["<strong>模型换家族</strong>", "你主动换供应商 / 换尺寸",
             "<strong>为旧模型调出来的示例顺序、指令措辞、格式偏好全部失效</strong>",
             "能——这是一次<em>计划内的迁移</em>（第 3 节）"],
            ["<strong>行为漂移</strong>", "同一版本、同一 prompt，输出分布随时间变",
             "解析率或修复率缓慢上升",
             "<strong>只能靠监控</strong>（第 6 节的四项）"],
            ["<strong>示例池腐烂</strong>", "线上话题变了（模块 02 第 7 节）",
             "选中示例与输入的相似度下降",
             "能——它有一个无真值指标"],
        ]),
        DUAL(
            "<strong>第二行是本模块的主线，因为它的代价最容易被低估。</strong>"
            "<em>「换一个更强的模型」听起来是纯增益</em>，"
            "而实际上<strong>你为旧模型做的所有 prompt 层优化都可能不再成立</strong>——"
            "示例顺序（模块 02 量到三倍差距）、指令措辞、格式偏好、"
            "以及模块 03 搜出来的那套配置。"
            "<em>notebook 第 2 节量出这件事：为模型 A 优化的 prompt 在模型 B 上"
            "可能比基线还差。</em>",
            "为什么必然如此？因为<strong>prompt 层的优化本质上是在拟合某个模型的具体行为</strong>"
            "（近因偏置的强度、对格式的依从度、标签先验）。"
            "<em>这些行为在不同模型上不同，而且没有理由相同</em>。"
            "<strong>C03 模块 03 的 prompt 敏感性研究就是这件事的另一面："
            "既然同一个模型对措辞都敏感，那么跨模型不迁移是预期而不是意外。</strong>",
        ),
        CALLOUT("danger", "一个具体的、常见的事故："
                          "<strong>模型 ID 写成 <code>latest</code> 或不带版本。</strong>"
                          "<em>服务方更新后，你的 prompt 面对的是一个不同的模型，"
                          "而所有指标只是「慢慢变差」</em>。"
                          "<strong>这与 C70 模块 05 的「embedding 模型写 latest」是同一类错误，"
                          "而且同样不报错。</strong>"),
    ])),

    # ============================================================== 2
    ("what-transfers", "迁移时什么会失效、什么会保留", "".join([
        TABLE(["prompt 的组成", "跨模型迁移", "为什么"], [
            ["<strong>签名（契约）</strong>", "<strong>完全保留</strong>",
             "它不依赖任何模型；<em>这是模块 01「签名先于 prompt」的一个额外回报</em>"],
            ["<strong>取值域声明</strong>", "<strong>保留</strong>",
             "「把标签集写进指令」对任何模型都有效"],
            ["<strong>输出格式规范 + 解析器</strong>", "基本保留，<em>需重测解析率</em>",
             "不同模型对格式的依从度不同——<strong>解析率必须重测，不能假设</strong>"],
            ["<strong>解码约束</strong>", "<strong>保留（如果新栈支持）</strong>",
             "它是外部施加的保证，与模型行为无关——"
             "<em>这是「约束优于提示」的又一个理由</em>"],
            ["<strong>示例的选择</strong>", "部分保留",
             "「与输入相似的示例更好」这条规律比较稳；<em>但最优 k 会变</em>"],
            ["<strong>示例的顺序</strong>", "<strong>基本不保留</strong>",
             "它拟合的是具体模型的位置偏置——<em>方向都可能反过来</em>"],
            ["<strong>指令的具体措辞</strong>", "<strong>不保留</strong>",
             "模块 03 搜出来的措辞是对某个模型的拟合"],
            ["<strong>标签先验校准</strong>", "<strong>不保留</strong>",
             "先验是模型 × 示例的联合产物（模块 02 第 5 节）"],
        ]),
        DUAL(
            "<strong>这张表给出了一个很实用的设计原则：把可迁移的部分与不可迁移的部分分开存。</strong>"
            "<em>签名、取值域、格式规范、解码约束 → 与模型无关，一份就够；"
            "示例顺序、指令措辞、校准参数 → 每个模型一份</em>。"
            "<strong>于是「换模型」变成「换掉那一半」，而不是「重做一遍」。</strong>",
            "这也解释了为什么<strong>模块 04 的解码约束在长期上比模块 03 的指令优化更值</strong>："
            "<em>约束是一个外部施加的、与模型无关的保证；"
            "而搜出来的指令措辞是一次性资产，换模型就报废</em>。"
            "<strong>所以在两者都能解决同一个问题时（比如输出格式），优先选约束。</strong>"
            "<em>模块 03 第 6 节说的「搜出来的 prompt 要能被审阅」也是同一条："
            "看不懂的咒语在迁移时既不知道能不能留，也不知道该怎么改。</em>",
        ),
    ])),

    # ============================================================== 3
    ("migration", "迁移流程：直接复用 C70 模块 05 的结构", "".join([
        P("换模型是一次<strong>有状态的切换</strong>，"
          "而 C70 模块 05 已经把这类切换的正确形状定下来了。"
          "<strong>这里只需要把「索引」换成「prompt bundle + 模型」。</strong>"),
        ASCII("""
   t0  ACTIVE = (bundle_A, model_A)
   t1  影子评测：(bundle_A, model_B) 与 (bundle_B*, model_B) 都跑一遍
         │        └─ 直接搬过去        └─ 为 B 重新调过的（顺序/措辞/校准）
   t2  一致性校验（三条，见下）
   t3  灰度：1% → 10% → 50% → 100%，每一档看监控四项
   t4  ACTIVE = (bundle_B*, model_B)；保留旧配置 N 天
   t5  回滚 = 反向切那一个指针

   **中途状态必须不可达**：一个请求要么完全走旧配置，要么完全走新配置。
   混着走（新模型 + 旧示例顺序）是一个既没被评测过、也不会报错的组合。
"""),
        H3("一致性校验的三条"),
        OL([
            "<strong>确定性：解析率必须仍是 1.0</strong>（若用了解码约束）"
            "或<strong>不低于旧配置</strong>（若没用）。"
            "<em>这一项零误报，直接阻断。</em>",
            "<strong>统计：分层准确率——每一层都不能显著下降</strong>。"
            "<em>只看总分会掩盖「某一类塌了」</em>"
            "（与 C68 模块 03 的切片分析、C70 模块 04 的分层报分是同一条）。",
            "<strong>观测：预测标签分布的 PSI</strong>。"
            "<em>它不设阻断阈值</em>——"
            "<strong>换模型必然让分布变化，所以它高不代表坏</strong>；"
            "<em>但它是「新模型的先验与旧模型不同」的量化证据，"
            "用来决定要不要重做校准。</em>",
        ]),
        CALLOUT("intuition", "第 3 条的处理方式与 C70 模块 05 的「top-k 重叠率」完全同构："
                             "<strong>有些指标是观测量而不是门禁</strong>。"
                             "<em>它们的用途是解释变化的原因，而不是判定好坏。</em>"
                             "把观测量设成门禁，结果是门禁在正确的变更上误报。"),
    ])),

    # ============================================================== 4
    ("cost", "成本：token、缓存、以及它们与示例策略的耦合", "".join([
        MATH(r"\text{cost/req} = \big(n_{\text{instr}} + \textstyle\sum_i n_{d_i} "
             r"+ n_x\big)\cdot c_{\text{in}} \cdot (1 - h) + n_y \cdot c_{\text{out}}"),
        P("其中 $h$ 是<strong>前缀缓存命中率</strong>。"
          "<em>这一项把成本与模块 02 的示例选择策略直接绑在了一起。</em>"),
        TABLE(["示例策略", "前缀是否稳定", "缓存命中率 $h$", "相关性"], [
            ["<strong>固定示例</strong>", "<strong>完全稳定</strong>",
             "接近 1（只有输入 $x$ 是变的）", "最低"],
            ["<strong>分桶 kNN（N 桶）</strong>", "只有 N 种",
             "较高", "中"],
            ["<strong>全局 kNN</strong>", "<strong>每个请求都不同</strong>",
             "<strong>≈ 0</strong>", "最高"],
        ]),
        DUAL(
            "<strong>这个耦合常被忽略：模块 02 量到 kNN 的准确率收益很大，"
            "而这一节说明它的成本也很大。</strong>"
            "<em>在长 prompt、高 QPS 的场景下，"
            "「示例占 2000 token、缓存命中率从 0.9 掉到 0」"
            "带来的成本增长可能超过准确率提升的价值</em>。"
            "<strong>分桶 kNN 存在的理由就是这个权衡。</strong>",
            "还有一个与迁移相关的成本项："
            "<strong>不同模型的单价与 tokenizer 都不同</strong>。"
            "<em>同一段中文 prompt 在两个 tokenizer 下的 token 数可以差 30% 以上</em>，"
            "所以<strong>「换模型省钱」这个判断必须按 token 数重算，"
            "不能只看单价</strong>。"
            "<em>notebook 第 4 节把这两项一起算出来，"
            "并算出让「单价最低」与「总成本最低」分家的 token_ratio 临界值——<strong>而在本课的参数下这两个口径其实指向同一个模型，所以不能拿它当反例</strong>。</em>",
        ),
    ])),

    # ============================================================== 5
    ("rollout", "灰度与回滚", "".join([
        P("prompt 变更的灰度比模型变更简单（它是纯配置），"
          "<strong>但有两个 prompt 特有的注意点。</strong>"),
        OL([
            "<strong>灰度的分流必须按稳定 ID，不能按请求随机。</strong>"
            "<em>按请求随机会让同一个用户在同一个会话里遇到两套 prompt</em>——"
            "而多轮对话里这会产生不一致的行为（模块 03 提过的指代改写就依赖历史）。",
            "<strong>回滚必须是「切一个指针」，而不是「把 prompt 改回去」。</strong>"
            "<em>改回去意味着有人要手动编辑，而手动编辑会引入新的差异</em>"
            "（模块 01 练习 4 的 <code>audit</code> 正是抓这个）。"
            "<strong>正确形状：<code>ACTIVE -> v3</code> 这一个指针，"
            "旧版本文件原样保留。</strong>",
        ]),
        ASCII("""
   灰度期间必须分桶看指标（否则新旧被平均掉）

              旧配置 (90%)        新配置 (10%)
   parse_rate     1.00               1.00      ✓
   end_to_end     0.72               0.75      ✓
   by_label:
     bug          0.80               0.85
     other        0.65               0.40      ← **这一层塌了**
   pred_dist PSI    —                0.31      ← 与「other 塌了」一致

   总分（加权平均）: 0.723 → 0.723   ← **看不出任何问题**
"""),
        P("<strong>上面那张表是灰度里最常见的失败模式</strong>："
          "<em>新配置在某一层塌了，但因为它只占 10% 流量，总分完全看不出来</em>。"
          "<strong>所以灰度期间的指标必须按分桶 × 分层同时切。</strong>"),
        CALLOUT("warn", "还有一条容易忘的："
                        "<strong>灰度期间两套配置的指纹都要出现在每一条日志里。</strong>"
                        "<em>否则你无法把指标归因到具体哪一套</em>——"
                        "而这正是 C68 模块 00「可归因性」的要求。"),
    ])),

    # ============================================================== 6
    ("monitoring", "监控四项（都不需要真值）", "".join([
        TABLE(["指标", "怎么算", "它能抓到什么"], [
            ["<strong>解析率</strong>", "解析成功的请求占比",
             "<strong>模型换版本、格式依从度下降</strong>；"
             "<em>用了解码约束时它恒为 1，掉下来就是实现 bug（模块 04 练习 4）</em>"],
            ["<strong>修复率 / 重试率</strong>", "被语法修复过 / 重试过的占比",
             "<strong>最灵敏的早期信号</strong>——"
             "<em>它在解析率还是 1.0 的时候就会先动</em>"],
            ["<strong>预测标签分布</strong>", "各标签占比 + 相对基线的 PSI",
             "顺序偏置、示例池漂移、模型换版本（三者都表现为分布偏移）"],
            ["<strong>无内容探针的输出</strong>", "定时用 <code>N/A</code> 打一次",
             "<strong>标签先验的变化</strong>——"
             "<em>它是一次调用，而且它把「模型的默认倾向变了」变成一个可比的字符串</em>"],
        ]),
        DUAL(
            "<strong>第二项是这四项里最有价值的一个</strong>，因为它的灵敏度最高："
            "<em>模型的格式依从度下降时，先出现的是「需要修复」，"
            "之后才是「修不动了 → 解析失败」</em>。"
            "<strong>所以修复率是解析率的前导指标。</strong>"
            "<em>而它只有在修复被显式记录时才存在——静默修复会把这个信号丢掉"
            "（模块 04 第 6 节）。</em>",
            "第四项是本课特有的、成本极低的一个监控点："
            "<strong>无内容探针每小时一次调用，就能持续跟踪标签先验。</strong>"
            "<em>它变化时，要么是模型变了、要么是示例池变了、要么是有人改了顺序</em>——"
            "<strong>三种原因都值得知道，而三种都不会在准确率上立刻显现。</strong>"
            "（探针的机制在模块 02 第 5 节。）",
        ),
    ])),

    # ============================================================== 7
    ("failures", "六个失效模式", "".join([
        TABLE(["失效", "根因", "信号", "对策"], [
            ["<strong>模型静默更新</strong>", "模型 ID 没钉版本",
             "预测分布 PSI + 探针输出变化", "<strong>钉死版本并写进指纹</strong>"],
            ["<strong>换模型后效果掉</strong>", "prompt 层优化拟合的是旧模型",
             "分层准确率某几层下降",
             "为新模型重做顺序 + 校准（第 2 节那张表的下半部分）"],
            ["<strong>解析率缓慢下降</strong>", "格式依从度漂移",
             "<strong>修复率先上升</strong>", "上解码约束（模块 04）"],
            ["<strong>某一层塌了但总分没动</strong>", "灰度流量占比小 / 类别不平衡",
             "分桶 × 分层的指标",
             "<strong>门禁按层判，不按总分判</strong>"],
            ["<strong>成本涨了但没人知道为什么</strong>",
             "换了示例策略 → 前缀缓存失效",
             "缓存命中率 + 输入 token 数",
             "分桶 kNN；把 $h$ 写进成本模型（第 4 节）"],
            ["<strong>回滚失败</strong>", "回滚需要手动改 prompt",
             "—", "<strong>回滚必须是切指针；旧版本文件原样保留</strong>"],
        ]),
        CALLOUT("intuition", "六条里有四条的信号都不是准确率。"
                             "<strong>这正是本模块的要点：prompt 层的问题大多在准确率上"
                             "「反应很慢」，而在解析率、修复率、分布、探针上「反应很快」。</strong>"
                             "<em>只监控准确率，等于把所有问题都延迟到它们变严重之后才发现。</em>"),
    ])),

    # ============================================================== 8
    ("ops-card", "prompt 运维卡 + 门禁", "".join([
        ASCII("""
   prompt 运维卡（每次变更 / 迁移 / 灰度推进时生成）

   bundle:            classify_feedback/v7
   model:             model-b@2026-06-01        ← **钉死，不写 latest**
   prompt_fp:         9c31a7f2   （签名+指令+示例(有序)+格式+解码+模型+温度）
   changelog:         v7: 为 model-b 重做示例顺序与校准（迁移）
   decoding:          constrained(json schema)  → parse_rate 应恒为 1.0

   可迁移部分:        signature / domain / format / decoding    （未改）
   不可迁移部分:      demo_order / instruction_wording / calib  （已为 b 重做）

   离线:  parse_rate 1.00 ✓   分层准确率 每层 ≥ 基线−2σ ✓
   观测:  pred_dist PSI 0.28（换模型必然变，不设阻断）
          无内容探针 other → billing（先验变了，已重做校准）
   成本:  输入 token 1,840（+12%，tokenizer 不同）× 单价 0.6× → 总成本 0.67×
          前缀缓存命中率 0.88（分桶 kNN，8 桶）

   灰度:  1% → 10%（当前）；分桶 × 分层指标均达标
   回滚:  ACTIVE -> v6，旧版本文件保留至 2026-09-30
"""),
        H3("门禁（按 C68 模块 04 分级）"),
        UL([
            "<strong>确定性阻断</strong>：模型 ID 含 <code>latest</code> 或不带版本；"
            "指纹变了但 CHANGELOG 没动；"
            "启用约束但解析率 &lt; 1.0；<em>回滚指针缺失或指向不存在的版本</em>",
            "<strong>统计阻断</strong>：<em>任一分层</em>的准确率相对基线下降超过 $2\\sigma$",
            "<strong>报警</strong>：修复率或重试率上升；探针输出变化；"
            "总成本上升超过阈值",
            "<strong>观测（不设阈值）</strong>：预测分布 PSI",
        ]),
        P("<strong>这张卡里最重要的一行仍然是最后一行</strong>——"
          "<em>与 C70 模块 05 完全一致</em>："
          "<strong>如果回滚需要手动编辑 prompt，那么这次变更是不可回滚的，不该上线。</strong>"),
    ])),

    # ============================================================== 9
    ("timeline", "一次真实迁移的时间线", "".join([
        P("把第 3 节的流程放到日历上。"
          "<strong>这个时间线的形状本身是结论：影子期比切换期长得多。</strong>"),
        ASCII("""
   第 1 周  建影子环境
            portable/ 原样复用（签名 / 取值域 / 格式 / 解码约束）
            为新模型建一份 models/model-b@.../，先直接搬旧配置
            **先只跑离线**：分层准确率 + 解析率

   第 2 周  为新模型重做不可迁移的那一半
            示例顺序（搜一遍）· 指令措辞（小幅搜）· 校准（重测先验）
            产出一份优化报告（按模块 03 的规矩：空间大小 / 候选数 / 留出集分数）

   第 3 周  一致性校验 + 决定要不要迁
            三条校验（解析率 / 分层准确率 / PSI 观测）
            **允许的结论包括「不迁」**（练习 2 的 'stay'）

   第 4 周  灰度 1% → 10%，按稳定 ID 分流
            每天看分桶 × 分层的指标 + 监控四项

   第 5 周  灰度 50% → 100%
   第 6 周  观察期结束，删除旧配置（在此之前回滚随时可用）
"""),
        DUAL(
            "<strong>三个容易被压缩掉、但不该压缩的环节。</strong>"
            "<em>① 第 2 周「重做那一半」经常被跳过</em>——"
            "直接搬旧配置上线，而第 2 节量过它会掉到基线以下。"
            "<em>② 第 3 周「允许不迁」经常不被当成一个真实选项</em>——"
            "而一旦迁了，你就失去了对照。"
            "<em>③ 第 6 周之前不删旧配置</em>——"
            "<strong>删得太早等于放弃回滚。</strong>",
            "反过来，<strong>有一个环节经常被过度投入：灰度的档位数。</strong>"
            "<em>prompt 变更是纯配置，它不像模型部署那样有资源风险</em>，"
            "所以 1% → 10% → 50% → 100% 四档通常够了。"
            "<strong>真正决定安全性的不是档位多细，"
            "而是每一档有没有按「分桶 × 分层」看指标</strong>——"
            "<em>第 5 节量过：新配置在某一层塌了，而总分完全看不出来。</em>",
        ),
    ])),

    # ============================================================== 10
    ("ownership", "prompt 的所有权与评审", "".join([
        P("最后一个问题是组织性的，"
          "<strong>但它决定了前面所有机制会不会被执行。</strong>"),
        TABLE(["资产", "谁拥有", "评审要看什么"], [
            ["<strong>portable/</strong>（签名 / 取值域 / 格式 / 解码约束）",
             "<em>与下游消费方共同拥有</em>",
             "<strong>改它等于改接口</strong>——"
             "取值域增删、字段增删都要通知下游"],
            ["<strong>models/&lt;model&gt;/</strong>（指令 / 示例 / 校准）",
             "做这个功能的团队",
             "<em>指纹变了吗？CHANGELOG 写了吗？"
             "留出集分数报了吗？</em>（模块 01/03 的门禁）"],
            ["<strong>示例池</strong>", "<em>与标注/运营共同拥有</em>",
             "覆盖度、泄漏检查、回灌占比（模块 02 第 6/7 节）"],
            ["<strong>ACTIVE 指针</strong>", "值班/发布负责人",
             "<strong>改它就是一次发布</strong>——"
             "要有发布记录与回滚预案"],
        ]),
        DUAL(
            "<strong>这张表最重要的一行是第一行。</strong>"
            "<em>取值域与输出格式是接口</em>，"
            "而「加一个标签」「把 <code>confidence</code> 从必填改成可选」"
            "<strong>是一次会破坏下游的变更</strong>——"
            "<em>但因为它「只是改了 prompt」，通常不会走接口变更的流程</em>。"
            "<strong>把 portable/ 单独成目录、单独设 owner，就是为了让这件事变得显眼。</strong>",
            "评审的最小要求可以压成三个问题，"
            "<strong>而它们全都能从门禁的输出里直接读到</strong>："
            "<em>① 指纹变了吗、CHANGELOG 写了吗？"
            "② 留出集（不是搜索集）上的分层结果是什么？"
            "③ 回滚指针指向哪里、旧配置保留到什么时候？</em>"
            "<strong>三个都答得上来时，这次变更就是可追溯、可评估、可撤销的</strong>——"
            "<em>而这三条恰好就是本课五个模块想要换来的全部东西。</em>",
        ),
    ])),

    # ============================================================== 11
    ("course-recap", "全课回顾：五个模块为什么是这个顺序", "".join([
        P("这是本课的最后一节。"
          "<strong>五个模块的顺序不是叙述方便，它是由效应量与成本决定的。</strong>"),
        TABLE(["模块", "它换来什么", "成本", "为什么排在这个位置"], [
            ["<strong>01 契约</strong>",
             "「哪一层出了问题」变成可判定的",
             "几百行代码 + 一次目录重构",
             "<strong>它是其余四个模块的前提</strong>——"
             "<em>没有分层指标，后面所有改动都无法被评估</em>"],
            ["<strong>02 示例</strong>",
             "覆盖度（正确性）+ 顺序（三倍差距）",
             "<strong>前三步成本为零</strong>",
             "效应量最大而成本最低的一层，所以排第二"],
            ["<strong>03 优化</strong>",
             "在已定的空间里找一个更好的点",
             "一整套评测的算力 + 留出集",
             "<em>它的前提是「噪声已知、目标可靠、有留出集」</em>——"
             "所以必须在 01/02 之后"],
            ["<strong>04 约束</strong>",
             "<strong>解析率的保证（而不是改善）</strong>",
             "改推理栈或用现成实现",
             "<em>它能替代掉一部分 03 的工作</em>"
             "（格式问题不必再搜），<strong>而且它跨模型保留</strong>"],
            ["<strong>05 运维</strong>",
             "这套东西在换模型、换版本之后还成立",
             "目录结构 + 门禁 + 监控四项",
             "<strong>它保护前四个模块的产出</strong>；"
             "<em>而它同时告诉你哪一半会报废</em>"],
        ]),
        DUAL(
            "<strong>把 05 的结论反向套回全课，会得到一个有点意外的排序建议。</strong>"
            "<em>本模块第 2 节量到：没调过的 prompt 跨模型分数完全相同，"
            "而调过的会掉到基线以下</em>。"
            "<strong>也就是说：模块 03 的产出是最容易报废的资产，"
            "而模块 01 与 04 的产出（契约、约束）是最耐久的。</strong>"
            "<em>如果你预期一年内会换模型，"
            "那么把预算从 03 挪到 01 与 04 是一个理性的选择。</em>",
            "而模块 02 的位置很特殊：<strong>它的前三步（覆盖、泄漏、顺序）成本为零，"
            "但顺序那一项是不可迁移的。</strong>"
            "<em>所以正确的做法是「做，但记录它是模型特定的」</em>——"
            "把它放进 <code>models/&lt;model&gt;/</code> 而不是 <code>portable/</code>，"
            "<strong>换模型时重跑那个零成本的搜索就行</strong>。"
            "<em>这也是本课最后一个具体建议："
            "不可迁移不等于不该做，它只决定了这份产出该放在哪个目录里。</em>",
        ),
    ])),

    # ============================================================== 12
    ("last-word", "最后一条：这一层的价值不在分数上", "".join([
        P("本课量了很多分数：三倍的顺序差距、$10^8$ 的空间压缩、0.081 nat 的分布失真。"
          "<strong>但这一层最终交付的东西不是分数。</strong>"),
        DUAL(
            "把五个模块的产出列出来看："
            "<em>三个可分层的指标、一套零误报的契约检查、"
            "一份可 diff 的示例文件、一个带候选数与留出集分数的优化报告、"
            "一个解析率的保证、一张运维卡与一个回滚指针</em>。"
            "<strong>它们全部是「让变化变得可见、可评估、可撤销」的机制</strong>，"
            "而不是「让分数更高」的技巧。",
            "为什么这个区分重要？"
            "<em>因为分数会随模型变化（模块 05 第 2 节：为 A 调的东西在 B 上更差），"
            "而这些机制不会</em>。"
            "<strong>换模型时，你的示例顺序报废了，"
            "但「三个量分别打点」「指纹与 CHANGELOG 对齐」"
            "「留出集与搜索集分开」这些机制原样继续工作</strong>——"
            "<em>而正是它们让你在第二次、第三次换模型时越来越快。</em>",
        ),
        CALLOUT("intuition", "所以如果要给这门课一句真正的总结，不是「怎么把 prompt 写好」，"
                             "而是：<strong>怎么让「prompt 变好了还是变坏了」这个问题"
                             "有一个可以被回答的形式。</strong>"
                             "<em>而这个形式一旦建立，写好它就变成了一件可以迭代的常规工作</em>——"
                             "这也是「把 prompt 当程序」这句话的全部意思。"),
    ])),
]

NB = [
    md("""# 05 · 提示的运维与跨模型迁移（失效 / 迁移 / 成本 / 灰度 / 监控 / 运维卡）

目标：把 prompt 当成一个**会随模型失效的资产**来管理。

本 notebook 你会亲手实现：
1. **四个「模型」的模拟器** —— 它们在近因偏置、格式依从度、标签先验上不同
2. **同一个 prompt 的跨模型分数跨度** —— 以及**为 A 优化的 prompt 在 B 上比基线更差**
3. **迁移的分层复核** —— 总分看不出来的那一层
4. **成本模型** —— token 数 × 单价 × (1 − 缓存命中率)，并算出让两个口径分家的 token_ratio 临界值
5. **灰度分桶** —— 某一层塌了而总分完全没动
6. **监控四项** —— 修复率是解析率的前导指标
7. **prompt 运维卡 + 门禁**

> 心智模型：**签名、取值域、格式、解码约束跨模型保留；
> 示例顺序、指令措辞、校准参数不保留。把它们分开存，换模型就只换那一半。**"""),

    md("""## 0 · 环境与四个「模型」"""),

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

# 四个「模型」：在三个行为维度上不同
MODELS = {
    'model-a@2026-01': dict(recency=+0.35, prior='other', format_compliance=0.98,
                            price_in=1.0, token_ratio=1.00),
    'model-a@2026-06': dict(recency=+0.20, prior='other', format_compliance=0.95,
                            price_in=1.0, token_ratio=1.00),   # 同家族小版本
    'model-b@2026-06': dict(recency=-0.30, prior='billing', format_compliance=0.90,
                            price_in=0.6, token_ratio=1.30),   # 另一家族：近因偏置**反向**
    'model-c@2026-06': dict(recency=+0.05, prior='bug', format_compliance=0.99,
                            price_in=2.0, token_ratio=0.85),
}

def toy_lm(model_id, instruction, demos, x, allowed=None):
    \"\"\"同一套接口，行为由 model_id 决定。

    recency 为负 = **首因偏置**（靠前的示例更重）——真实模型的位置偏置方向确实不一致。
    \"\"\"
    cfg = MODELS[model_id]
    allowed = LABELS if allowed is None else allowed
    declared = [l for l in allowed if l in instruction]
    if not declared:
        return UNPARSEABLE
    if not demos:
        return cfg['prior']
    E = np.stack([embed(t) for t, _ in demos])
    s = E @ embed(x)
    n = len(demos)
    s = s + np.array([cfg['recency'] * (i / (n - 1) if n > 1 else 1.0)
                      for i in range(n)])
    label = demos[int(np.argmax(s))][1]
    return label if label in declared else cfg['prior']

print('四个模型的行为参数:')
for m, c in MODELS.items():
    print(f'  {m:<18} recency {c["recency"]:+.2f}  prior {c["prior"]:<9}'
          f' format {c["format_compliance"]:.2f}  price {c["price_in"]:.1f}'
          f'  token×{c["token_ratio"]:.2f}')"""),

    md("""## 1 · 数据与一个 prompt bundle

**bundle 分成两半**：可迁移的（签名/取值域/格式/解码）与不可迁移的（顺序/措辞/校准）。"""),

    code("""POOL = [
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

PORTABLE = dict(                      # ← 与模型无关，一份就够
    signature=dict(inputs=['feedback'], output='label', domain=LABELS),
    instruction_core=('把用户反馈分类为 bug / feature / billing / account / other 之一，'
                      '只输出标签。都不符合时输出 other。'),
    format_spec='json {"label": "<标签>"}',
    decoding=dict(constrained=True, grammar='json+enum'),
)
def make_bundle(model_id, demo_order=None, wording_suffix='', calib=None, k=8):
    \"\"\"不可迁移的部分：示例顺序、措辞后缀、校准。\"\"\"
    demos = [POOL[i] for i in (demo_order if demo_order else range(k))]
    return dict(model_id=model_id, demos=demos,
                instruction=PORTABLE['instruction_core'] + wording_suffix,
                calib=calib, **PORTABLE)

def run_bundle(b, test=None, apply_format_noise=True, seed=0):
    \"\"\"返回 dict(parse_rate, repair_rate, end_to_end, by_label, pred_dist)。\"\"\"
    test = TEST if test is None else test
    cfg = MODELS[b['model_id']]
    n_ok = n_rep = n_c = 0
    by_label, preds = defaultdict(list), Counter()
    for x, gold in test:
        raw = toy_lm(b['model_id'], b['instruction'], b['demos'], x)
        parsed = raw if raw in LABELS else None
        repaired = False
        if apply_format_noise and parsed is not None:
            h = int(hashlib.md5((x + b['model_id'] + str(seed)).encode()), 16) \\
                if False else int(hashlib.md5((x + b['model_id']).encode()).hexdigest(), 16)
            if (h % 1000) / 1000.0 > cfg['format_compliance']:
                if b['decoding']['constrained']:
                    pass                       # 约束下不可能不合格式
                else:
                    repaired = True            # 语法层修复救回来
        n_rep += repaired
        if parsed is not None:
            n_ok += 1
        hit = (parsed == gold)
        n_c += hit
        by_label[gold].append(float(hit))
        preds[parsed] += 1
    n = len(test)
    return dict(parse_rate=n_ok / n, repair_rate=n_rep / n, end_to_end=n_c / n,
                by_label={l: float(np.mean(v)) for l, v in by_label.items()},
                pred_dist=dict(preds))

B_A = make_bundle('model-a@2026-01')
r = run_bundle(B_A)
print('bundle_A on model-a@2026-01:',
      {k: (round(v, 3) if isinstance(v, float) else v)
       for k, v in r.items() if k not in ('by_label', 'pred_dist')})
assert r['parse_rate'] == 1.0
print('\\n✅ PORTABLE 四项（签名/取值域/格式/解码）与模型无关；')
print('   demos 顺序、措辞、校准是每个模型一份。这个拆分是本模块的设计核心。')"""),

    md("""## 2 · 跨模型：同一个 prompt 的分数跨度

以及本模块的核心结果：**为 A 优化的 prompt 在 B 上可能比基线更差。**"""),

    code("""# 覆盖全部五个标签的基线示例集（模块 02 第 2 节：不覆盖会让某类归零）
BASELINE_ORDER = [0, 4, 8, 12, 16, 1, 5, 9]
print('基线示例的标签序列:', [y for _, y in [POOL[i] for i in BASELINE_ORDER]])

print(f"\\n{'模型':<20}{'end2end':>9}{'解析率':>9}{'预测分布':>44}")
scores, dists = {}, {}
for m in MODELS:
    b = make_bundle(m, demo_order=BASELINE_ORDER)
    r = run_bundle(b)
    scores[m], dists[m] = r['end_to_end'], r['pred_dist']
    print(f'{m:<20}{r["end_to_end"]:>9.0%}{r["parse_rate"]:>9.0%}'
          f'{str(r["pred_dist"]):>44}')

spread = max(scores.values()) - min(scores.values())
print(f'\\n一个**没有针对任何模型调过**的 prompt，四个模型上的跨度: {spread:.0%}')

assert all(v == 1.0 for v in
           [run_bundle(make_bundle(m, BASELINE_ORDER))['parse_rate'] for m in MODELS]), \\
    '解码约束让解析率在所有模型上都是 1.0'
assert spread == 0.0, f'基线 prompt 在四个模型上分数相同，实际跨度 {spread}'
# 但预测分布不同
uniq = {frozenset(d.items()) for d in dists.values()}
assert len(uniq) > 1, '预测分布必须不同——行为差异在这里，不在总分上'
print('\\n✅ 两个观察，第二个是本模块最重要的伏笔：')
print(f'   ① 解析率在四个模型上都是 1.0——**因为它由解码约束保证，与模型行为无关**。')
print('      这就是「可迁移部分」的价值（讲解第 2 节那张表的上半部分）。')
print(f'   ② 端到端分数**完全相同**（都是 {list(scores.values())[0]:.0%}），')
print('      但**预测分布明显不同**：')
for m in MODELS:
    print(f'      {m:<20}{str(dists[m])}')
print('      也就是说：这四个模型的**行为**确实不同，')
print('      只是在这个没调过的 prompt 上，行为差异恰好没有转化成分数差异。')
print()
print('   下一节会说明这个伏笔的意思：**迁移风险不来自「换模型」本身，')
print('   而来自「这个 prompt 已经针对某个模型调过」。**')"""),

    code("""# --- 为 A 搜一个最优示例顺序，然后搬到 B 上 ---
def best_order_for(model_id, n_trials=200, seed=0, base=None):
    \"\"\"在**同一个示例集合**上搜排列（不改集合，只改顺序）。\"\"\"
    base = BASELINE_ORDER if base is None else list(base)
    rng = np.random.default_rng(seed)
    best, best_a = list(base), -1.0
    for _ in range(n_trials):
        order = [base[i] for i in rng.permutation(len(base))]
        a = run_bundle(make_bundle(model_id, demo_order=order))['end_to_end']
        if a > best_a:
            best, best_a = order, a
    return best, best_a

order_A, acc_A = best_order_for('model-a@2026-01', 200, seed=0)
order_B, acc_B = best_order_for('model-b@2026-06', 200, seed=0)
print(f'为 A 搜出的顺序 {order_A} → A 上 {acc_A:.0%}')
print(f'为 B 搜出的顺序 {order_B} → B 上 {acc_B:.0%}')

base_on_B = run_bundle(make_bundle('model-b@2026-06', BASELINE_ORDER))['end_to_end']
A_order_on_B = run_bundle(make_bundle('model-b@2026-06', order_A))['end_to_end']
base_on_A = run_bundle(make_bundle('model-a@2026-01', BASELINE_ORDER))['end_to_end']
B_order_on_A = run_bundle(make_bundle('model-a@2026-01', order_B))['end_to_end']

print(f"\\n{'':<28}{'在 A 上':>10}{'在 B 上':>10}")
print(f'{"基线顺序":<28}{base_on_A:>10.0%}{base_on_B:>10.0%}')
print(f'{"为 A 搜出的顺序":<28}{acc_A:>10.0%}{A_order_on_B:>10.0%}')
print(f'{"为 B 搜出的顺序":<28}{B_order_on_A:>10.0%}{acc_B:>10.0%}')

assert acc_A > base_on_A, '为 A 搜的顺序在 A 上更好'
assert acc_B > base_on_B, '为 B 搜的顺序在 B 上更好'
assert A_order_on_B <= base_on_B, \\
    f'为 A 优化的顺序搬到 B 上不该更好: {A_order_on_B:.2f} vs 基线 {base_on_B:.2f}'
print(f'\\n✅ **为 A 优化的顺序搬到 B 上是 {A_order_on_B:.0%}，'
      f'而 B 的基线是 {base_on_B:.0%}——不升反降，反而掉了 '
      f'{base_on_B - A_order_on_B:.0%}。**')
print(f'   而为 B 重新搜一遍能拿到 {acc_B:.0%}。')
print()
print('   把它和上一节放在一起，得到本模块的核心结论：')
print(f'   **没调过的 prompt 在四个模型上分数完全相同（都 {base_on_B:.0%}）；')
print('   一旦针对某个模型调过，它就变得不可迁移了。**')
print('   换句话说：**迁移风险是优化的副产物，不是换模型本身的代价。**')
print('   这也给出一个反直觉的推论：如果你从未做过 prompt 层优化，')
print('   那么换模型对你来说是安全的——而做过优化之后，每次换模型都要重做那一半。')
print('   机制在模拟器里是显式的：A 的 recency 是 +0.35（近因偏置），')
print('   B 是 −0.30（**首因偏置**）——位置偏置的方向是相反的。')
print('   真实模型上位置偏置的方向也确实不一致，所以这不是人造的。')
print()
print('   工程结论：**换模型时，示例顺序必须重做，不能搬**。')
print('   而签名、取值域、格式、解码约束可以原样保留（上一节验证过解析率仍是 1.0）。')"""),

    md("""## 3 · 迁移的分层复核：总分看不出来的那一层"""),

    code("""def layered_compare(b_old, b_new, sigma=0.05):
    r_old, r_new = run_bundle(b_old), run_bundle(b_new)
    rows = []
    for l in LABELS:
        a, bnew = r_old['by_label'][l], r_new['by_label'][l]
        rows.append((l, a, bnew, bnew - a, (bnew < a - 2 * sigma)))
    return r_old, r_new, rows

B_old = make_bundle('model-a@2026-06', demo_order=order_A)
B_new = make_bundle('model-b@2026-06', demo_order=order_A)   # 直接搬过去（错误做法）
r_o, r_n, rows = layered_compare(B_old, B_new)

print(f"{'层':<10}{'旧':>8}{'新':>8}{'变化':>9}{'显著下降':>10}")
for l, a, bn, d, bad in rows:
    print(f'{l:<10}{a:>8.0%}{bn:>8.0%}{d:>+9.0%}{"是" if bad else "":>10}')
print(f'\\n总分: {r_o["end_to_end"]:.0%} → {r_n["end_to_end"]:.0%} '
      f'({r_n["end_to_end"] - r_o["end_to_end"]:+.0%})')

dropped = [l for l, _, _, _, bad in rows if bad]
print(f'显著下降的层: {dropped}')
assert dropped, '直接搬 prompt 过去，至少有一层应当显著下降'
total_drop = r_n['end_to_end'] - r_o['end_to_end']
print(f'\\n✅ 有 {len(dropped)} 层显著下降，而总分只变了 {total_drop:+.0%}。')
print('   **门禁必须按层判，不按总分判**——')
print('   这与 C68 模块 03 的切片分析、C70 模块 04 的分层报分是同一条。')

# PSI 是观测量而不是门禁
def psi(p, q, labels=LABELS, eps=1e-6):
    n_p, n_q = sum(p.values()), sum(q.values())
    v = 0.0
    for l in labels:
        a = max(p.get(l, 0) / n_p, eps)
        b_ = max(q.get(l, 0) / n_q, eps)
        v += (a - b_) * math.log(a / b_)
    return v

ps = psi(r_o['pred_dist'], r_n['pred_dist'])
print(f'\\n预测分布 PSI = {ps:.3f}')
print('  换模型必然让分布变化，所以 PSI 高**不代表坏**——它是观测量，不设阻断阈值。')
print('  它的用途是：给「新模型的先验与旧模型不同」提供量化证据，据此决定要不要重做校准。')
print('  （与 C70 模块 05 的「top-k 重叠率是观测量不是门禁」完全同构。）')
assert ps > 0.0"""),

    md("""## 4 · 成本：token × 单价 × (1 − 缓存命中率)

以及让「单价最低」与「总成本最低」分家的临界 token_ratio。"""),

    code("""def count_tokens(b):
    text = b['instruction'] + ''.join(a + c for a, c in b['demos'])
    return len(tokenize(text))

def cost_per_request(b, cache_hit=0.0, n_out=8, price_out_ratio=3.0):
    cfg = MODELS[b['model_id']]
    n_in = count_tokens(b) * cfg['token_ratio']
    return (n_in * cfg['price_in'] * (1 - cache_hit)
            + n_out * cfg['price_in'] * price_out_ratio) / 1000.0

print(f"{'模型':<20}{'输入 token':>12}{'单价':>7}{'h=0.9 成本':>12}{'h=0 成本':>11}")
for m in MODELS:
    b = make_bundle(m, BASELINE_ORDER)
    n_in = count_tokens(b) * MODELS[m]['token_ratio']
    print(f'{m:<20}{n_in:>12.0f}{MODELS[m]["price_in"]:>7.1f}'
          f'{cost_per_request(b, 0.9):>12.5f}{cost_per_request(b, 0.0):>11.5f}')

# 「单价最低」与「总成本最低」是不是同一个模型？—— 本课参数下**是**，
# 所以不能拿它当反例。诚实的做法是把翻转的临界值算出来。
cheapest_by_price = min(MODELS, key=lambda m: MODELS[m]['price_in'])
cheapest_by_cost = min(MODELS, key=lambda m: cost_per_request(
    make_bundle(m, BASELINE_ORDER), cache_hit=0.9))
print(f'\\n单价最低: {cheapest_by_price} | h=0.9 时总成本最低: {cheapest_by_cost}')
print('  → 本课的参数下**是同一个模型**，所以这里没有反例可看。')

def breakeven_token_ratio(cheap, ref, cache_hit=0.9, step=0.01, hi=6.0):
    \"\"\"cheap 的 token_ratio 要涨到多少，它才不再比 ref 便宜。\"\"\"
    saved = MODELS[cheap]['token_ratio']
    ref_cost = cost_per_request(make_bundle(ref, BASELINE_ORDER), cache_hit=cache_hit)
    r = saved
    try:
        while r < hi:
            MODELS[cheap]['token_ratio'] = r
            if cost_per_request(make_bundle(cheap, BASELINE_ORDER),
                               cache_hit=cache_hit) >= ref_cost:
                return r
            r += step
        return None
    finally:
        MODELS[cheap]['token_ratio'] = saved

for h in (0.9, 0.5, 0.0):
    r = breakeven_token_ratio('model-b@2026-06', 'model-a@2026-06', cache_hit=h)
    cur = MODELS['model-b@2026-06']['token_ratio']
    print(f'  h={h:.1f}: model-b 的 token_ratio 要从 {cur:.2f} 涨到 '
          f'{("%.2f" % r) if r else ">6"} 才不再比 model-a 便宜')

r90 = breakeven_token_ratio('model-b@2026-06', 'model-a@2026-06', cache_hit=0.9)
r00 = breakeven_token_ratio('model-b@2026-06', 'model-a@2026-06', cache_hit=0.0)
assert cheapest_by_price == cheapest_by_cost, '本课参数下两个口径给出同一个模型'
assert r00 is not None and r00 < 2.0, '缓存命中率低时，临界 token_ratio 很容易被跨过'
assert (r90 is None) or (r90 > r00), '缓存命中率高时，token 数的影响被 (1-h) 压小了'
print()
print('✅ 这一节的诚实结论比「单价低不等于总成本低」精细：')
print(f'   在本课参数下两个口径**一致**（都是 {cheapest_by_price}）——所以不要把它当反例讲。')
print(f'   真正可算的是**临界值**：h=0 时 token_ratio 超过 {r00:.2f} 排序就翻转，')
print('   而 h=0.9 时输入 token 只按 (1-h) 计费，临界值被推得很远甚至不存在。')
print('   **也就是说：tokenizer 的影响被缓存命中率放大或压制**——')
print('   两个乘数必须一起看，而不是各自看。')

# 关键对比：示例策略改变缓存命中率
print(f"\\n{'示例策略':<22}{'缓存命中率':>12}{'model-b 成本':>14}{'相对固定示例':>14}")
b_b = make_bundle('model-b@2026-06', BASELINE_ORDER)
base_cost = cost_per_request(b_b, cache_hit=0.95)
for name, h in [('固定示例', 0.95), ('分桶 kNN（8 桶）', 0.80), ('全局 kNN', 0.0)]:
    c = cost_per_request(b_b, cache_hit=h)
    print(f'{name:<22}{h:>12.2f}{c:>14.5f}{c / base_cost:>14.2f}×')

c_fixed = cost_per_request(b_b, 0.95)
c_knn = cost_per_request(b_b, 0.0)
assert c_knn > 2 * c_fixed, '全局 kNN 的成本应当明显更高'
print(f'\\n✅ 只改示例策略（不改模型、不改 prompt 长度），成本涨了 '
      f'{c_knn / c_fixed:.1f} 倍。')
print('   而模块 02 量到全局 kNN 的准确率收益也很大——**这是一个真实的权衡**，')
print('   分桶 kNN 存在的理由就是它。')
print()
print('   另一条与迁移相关的：**同一段中文 prompt 在不同 tokenizer 下 token 数差 30%+**，')
print('   所以「换模型省钱」必须按 token 数重算，不能只看单价。')"""),

    md("""## 5 · 灰度：某一层塌了而总分完全没动"""),

    code("""def canary_metrics(b_old, b_new, share_new=0.10, test=None):
    \"\"\"灰度：按稳定 ID 分流（不是按请求随机）。返回分桶 × 分层的指标。\"\"\"
    test = TEST if test is None else test
    buckets = {'old': [], 'new': []}
    for x, gold in test:
        h = int(hashlib.md5(x.encode()).hexdigest(), 16) % 1000
        buckets['new' if h < share_new * 1000 else 'old'].append((x, gold))
    out = {}
    for name, items in buckets.items():
        if not items:
            out[name] = None
            continue
        out[name] = run_bundle(b_old if name == 'old' else b_new, test=items)
        out[name]['n'] = len(items)
    return out

# 造一个「某一层塌了」的新配置：把 other 类的示例全换成 billing
def sabotage_other(k=8):
    demos = [POOL[i] for i in BASELINE_ORDER]
    return [(t, 'billing' if y == 'other' else y) for t, y in demos]

B_canary = make_bundle('model-a@2026-06', BASELINE_ORDER)
B_canary['demos'] = sabotage_other()

# 用 50% 分流让两桶都有足够样本
m = canary_metrics(make_bundle('model-a@2026-06', BASELINE_ORDER), B_canary,
                   share_new=0.5)
print(f"{'':<14}{'旧桶':>10}{'新桶':>10}")
print(f'{"样本数":<14}{m["old"]["n"]:>10}{m["new"]["n"]:>10}')
print(f'{"parse_rate":<14}{m["old"]["parse_rate"]:>10.0%}'
      f'{m["new"]["parse_rate"]:>10.0%}')
print(f'{"end_to_end":<14}{m["old"]["end_to_end"]:>10.0%}'
      f'{m["new"]["end_to_end"]:>10.0%}')
print('by_label:')
for l in LABELS:
    a = m['old']['by_label'].get(l)
    b_ = m['new']['by_label'].get(l)
    fa = f'{a:.0%}' if a is not None else '—'
    fb = f'{b_:.0%}' if b_ is not None else '—'
    print(f'  {l:<12}{fa:>10}{fb:>10}')

# 加权总分：新桶只占一小部分时，总分几乎不动
for share in (0.10, 0.5):
    mm = canary_metrics(make_bundle('model-a@2026-06', BASELINE_ORDER), B_canary,
                        share_new=share)
    if mm['new'] is None:
        continue
    n_o, n_n = mm['old']['n'], mm['new']['n']
    blended = (mm['old']['end_to_end'] * n_o + mm['new']['end_to_end'] * n_n) / (n_o + n_n)
    pure_old = run_bundle(make_bundle('model-a@2026-06', BASELINE_ORDER))['end_to_end']
    print(f'\\n灰度 {share:.0%}: 加权总分 {blended:.0%} vs 全旧配置 {pure_old:.0%} '
          f'(差 {blended - pure_old:+.0%})')

m10 = canary_metrics(make_bundle('model-a@2026-06', BASELINE_ORDER), B_canary,
                     share_new=0.10)
if m10['new'] is not None:
    n_o, n_n = m10['old']['n'], m10['new']['n']
    blended10 = (m10['old']['end_to_end'] * n_o + m10['new']['end_to_end'] * n_n) / (n_o + n_n)
    pure = run_bundle(make_bundle('model-a@2026-06', BASELINE_ORDER))['end_to_end']
    assert abs(blended10 - pure) < 0.15, '小比例灰度时总分几乎不动'
print('\\n✅ 三条灰度纪律：')
print('   ① **分流按稳定 ID，不按请求随机**——否则同一用户在同一会话里遇到两套 prompt；')
print('   ② 指标必须按**分桶 × 分层**同时切，总分会把新配置的问题平均掉；')
print('   ③ 两套配置的指纹都要出现在每一条日志里，否则指标无法归因（C68-00 可归因性）。')"""),

    md("""## 6 · 监控四项：修复率是解析率的前导指标"""),

    code("""def simulate_drift(model_id, weeks=8, base_compliance=0.98, decay=0.02,
                   constrained=False):
    \"\"\"模拟格式依从度缓慢下降，看四项指标谁先动。\"\"\"
    rows = []
    for w in range(weeks):
        comp = base_compliance - decay * w
        n = 400
        rng = np.random.default_rng(w)
        raw_ok = rng.random(n) < comp                     # 输出本身合格
        if constrained:
            parse_ok = np.ones(n, dtype=bool)             # 约束保证
            repaired = np.zeros(n, dtype=bool)
        else:
            # 不合格的里面，语法层修复能救回 70%
            rescued = (~raw_ok) & (rng.random(n) < 0.7)
            parse_ok = raw_ok | rescued
            repaired = rescued
        rows.append(dict(week=w, compliance=comp,
                         parse_rate=float(parse_ok.mean()),
                         repair_rate=float(repaired.mean())))
    return rows

print('不带解码约束（格式依从度每周降 2 个点）:')
print(f"{'week':>5}{'依从度':>9}{'解析率':>9}{'修复率':>9}")
rows = simulate_drift('model-a@2026-06', constrained=False)
for r in rows:
    print(f'{r["week"]:>5}{r["compliance"]:>9.2f}{r["parse_rate"]:>9.3f}'
          f'{r["repair_rate"]:>9.3f}')

# 修复率的变化幅度大于解析率的变化幅度 → 它更灵敏
d_parse = rows[0]['parse_rate'] - rows[-1]['parse_rate']
d_repair = rows[-1]['repair_rate'] - rows[0]['repair_rate']
print(f'\\n8 周里：解析率下降 {d_parse:.3f}，修复率上升 {d_repair:.3f}')
assert d_repair > d_parse, '修复率的变化幅度更大 → 它是更灵敏的信号'

rows_c = simulate_drift('model-a@2026-06', constrained=True)
assert all(r['parse_rate'] == 1.0 for r in rows_c), '约束下解析率恒为 1.0'
assert all(r['repair_rate'] == 0.0 for r in rows_c)
print('✅ 带解码约束时解析率恒为 1.0、修复率恒为 0——')
print('   **此时「解析率 < 1.0」直接是实现 bug 的信号**（模块 04 练习 4）。')
print(f'   而不带约束时，修复率的变化幅度是解析率的 {d_repair / d_parse:.1f} 倍——')
print('   **修复率是解析率的前导指标**。而它只在修复被显式记录时才存在。')"""),

    code("""# --- 第四项：无内容探针 ---
def probe(model_id, bundle, probes=('N/A', '', '[MASK]')):
    return Counter(toy_lm(model_id, bundle['instruction'], bundle['demos'], p)
                   for p in probes)

print(f"{'模型':<20}{'探针输出':>26}")
priors = {}
for m in MODELS:
    b = make_bundle(m, BASELINE_ORDER)
    pr = probe(m, b)
    priors[m] = set(pr)
    print(f'{m:<20}{str(dict(pr)):>26}')

assert len({frozenset(v) for v in priors.values()}) > 1, '不同模型的先验不同'
print('\\n✅ 无内容探针每次一次调用，就把「模型的默认倾向」变成一个可比的字符串。')
print('   它变化时，三种原因都值得知道：模型换版本 / 示例池变了 / 有人改了顺序——')
print('   **而三种都不会在准确率上立刻显现。**')
print()
print('   四项监控里有三项（修复率、预测分布、探针）都不是准确率。')
print('   这正是本模块的要点：**prompt 层的问题在准确率上反应很慢，')
print('   在这三项上反应很快。**')"""),

    md("""## 7 · prompt 运维卡 + 门禁"""),

    code("""def prompt_fp(b):
    payload = dict(signature=b['signature'], instruction=b['instruction'],
                   demos=[[a, c] for a, c in b['demos']],
                   format_spec=b['format_spec'], decoding=b['decoding'],
                   model_id=b['model_id'])
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()[:12]

def ops_card(b, metrics, baseline_metrics, changelog, rollback_to,
             cache_hit=0.8, sigma=0.05):
    ps = psi(baseline_metrics['pred_dist'], metrics['pred_dist'])
    return dict(
        model_id=b['model_id'], prompt_fp=prompt_fp(b), changelog=changelog,
        constrained=b['decoding']['constrained'],
        parse_rate=metrics['parse_rate'], repair_rate=metrics['repair_rate'],
        by_label=metrics['by_label'],
        baseline_by_label=baseline_metrics['by_label'],
        psi=ps, probe=sorted(probe(b['model_id'], b)),
        baseline_probe=sorted(probe('model-a@2026-01',
                                    make_bundle('model-a@2026-01', BASELINE_ORDER))),
        cost=cost_per_request(b, cache_hit=cache_hit),
        cache_hit=cache_hit, rollback_to=rollback_to, sigma=sigma)

def ops_gate(card, prev_changelog=None):
    blocking, warn, observe = [], [], []
    # 确定性
    if 'latest' in card['model_id'] or '@' not in card['model_id']:
        blocking.append(f"模型 ID {card['model_id']!r} 未钉死版本")
    if prev_changelog is not None and card['changelog'] == prev_changelog:
        blocking.append('指纹变了但 CHANGELOG 没动')
    if card['constrained'] and card['parse_rate'] < 1.0:
        blocking.append(f"启用约束但解析率 {card['parse_rate']:.2f} < 1.0（实现有 bug）")
    if not card['rollback_to']:
        blocking.append('缺回滚指针——这次变更不可回滚，不该上线')
    # 统计：按层判
    for l, v in card['by_label'].items():
        b0 = card['baseline_by_label'].get(l)
        if b0 is not None and v < b0 - 2 * card['sigma']:
            blocking.append(f'{l} 层准确率下降 {b0:.2f} → {v:.2f}（> 2σ）')
    # 报警
    if card['repair_rate'] > 0:
        warn.append(f"修复率 {card['repair_rate']:.1%} > 0（解析率的前导指标）")
    if card['probe'] != card['baseline_probe']:
        warn.append(f"探针输出变了: {card['baseline_probe']} → {card['probe']}")
    # 观测（不设阈值）
    observe.append(f"预测分布 PSI {card['psi']:.3f}（换模型必然变，不设阻断）")
    return blocking, warn, observe

BASE_M = run_bundle(make_bundle('model-a@2026-01', BASELINE_ORDER))
GOOD = make_bundle('model-b@2026-06', demo_order=order_B)     # 为 B 重做了顺序
card_good = ops_card(GOOD, run_bundle(GOOD), BASE_M,
                     'v7: 迁移到 model-b，重做示例顺序与校准', 'v6')
b, w, o = ops_gate(card_good, prev_changelog='v6: 初版')
print('为 B 重做顺序后:')
print('  阻断:', b if b else '无')
print('  报警:', w if w else '无')
print('  观测:', o)

BAD = make_bundle('model-b@2026-06', demo_order=order_A)      # 直接搬 A 的顺序
card_bad = ops_card(BAD, run_bundle(BAD), BASE_M,
                    'v7: 迁移到 model-b（直接搬旧配置）', 'v6')
b2, _, _ = ops_gate(card_bad, prev_changelog='v6: 初版')
print(f'\\n直接搬 A 的顺序: 阻断 {len(b2)} 项')
for x in b2[:3]:
    print('  ·', x)

assert any('层准确率下降' in x for x in b2), b2
# 模型 ID 没钉版本 → 阻断
card_latest = dict(card_good); card_latest['model_id'] = 'model-b:latest'
assert any('未钉死版本' in x for x in ops_gate(card_latest)[0])
# 缺回滚指针 → 阻断
card_norb = dict(card_good); card_norb['rollback_to'] = None
assert any('回滚' in x for x in ops_gate(card_norb)[0])
# CHANGELOG 没动 → 阻断
assert any('CHANGELOG' in x for x in
           ops_gate(card_good, prev_changelog=card_good['changelog'])[0])
print('\\n✅ 四项确定性阻断 + 按层的统计阻断 + 两项报警 + 一项观测。')
print('   而这张卡里最重要的一行仍然是回滚指针——与 C70 模块 05 完全一致：')
print('   **如果回滚需要手动编辑 prompt，那么这次变更是不可回滚的，不该上线。**')"""),

    md("""## ✏️ 练习 1：可迁移性分类器

实现 `migration_plan(bundle)`：把 bundle 的每一部分归到
`'portable'`（跨模型保留）/ `'retest'`（保留但必须重测）/ `'redo'`（必须重做）。

依据讲解第 2 节那张表：
- `portable`：`signature` / `domain`（取值域）/ `decoding`
- `retest`：`format_spec`（保留但解析率必须重测）
- `redo`：`demos`（顺序）/ `instruction`（措辞）/ `calib`

返回 `dict(portable=[...], retest=[...], redo=[...])`，键名排序。
再实现 `migration_effort(plan)`：返回 `len(redo) / (总项数)`——
**这个比例就是「换模型要重做多少」。**"""),

    code("""def migration_plan(bundle):
    \"\"\"返回 dict(portable=[...], retest=[...], redo=[...])，每个列表已排序。\"\"\"
    # TODO
    raise NotImplementedError

def migration_effort(plan):
    \"\"\"返回 redo 占全部项的比例。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
plan = migration_plan(B_A)
print(plan)
assert set(plan) == {'portable', 'retest', 'redo'}
assert 'signature' in plan['portable'] and 'decoding' in plan['portable']
assert 'domain' in plan['portable']
assert plan['retest'] == ['format_spec'], plan['retest']
assert set(plan['redo']) == {'calib', 'demos', 'instruction'}, plan['redo']
for k in plan:
    assert plan[k] == sorted(plan[k]), f'{k} 未排序'

eff = migration_effort(plan)
print(f'换模型要重做的比例: {eff:.0%}')
assert abs(eff - 3 / 7) < 1e-9, eff
# 如果不用解码约束（把它从 portable 里去掉），重做比例会更高
plan2 = migration_plan({**B_A, 'decoding': dict(constrained=False)})
assert 'decoding' in plan2['portable'], '不管开不开，decoding 本身都是可迁移的配置项'
print('✅ 练习 1 通过：把 bundle 分成三档，「换模型」就变成「换那一档」')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
PORTABLE_KEYS = ('signature', 'domain', 'decoding')
RETEST_KEYS = ('format_spec',)
REDO_KEYS = ('demos', 'instruction', 'calib')

def migration_plan(bundle):
    out = dict(portable=[], retest=[], redo=[])
    for k in PORTABLE_KEYS:
        if k == 'domain':
            if 'signature' in bundle and 'domain' in bundle['signature']:
                out['portable'].append('domain')
        elif k in bundle:
            out['portable'].append(k)
    for k in RETEST_KEYS:
        if k in bundle:
            out['retest'].append(k)
    for k in REDO_KEYS:
        if k in bundle:
            out['redo'].append(k)
    return {k: sorted(v) for k, v in out.items()}

def migration_effort(plan):
    total = sum(len(v) for v in plan.values())
    return len(plan['redo']) / total if total else 0.0

plan = migration_plan(B_A)
assert plan['retest'] == ['format_spec']
assert set(plan['redo']) == {'calib', 'demos', 'instruction'}
assert abs(migration_effort(plan) - 3 / 7) < 1e-9
print('✅ 参考答案 1 通过')
print(f'   本例的重做比例是 {migration_effort(plan):.0%}——三项里的三项。')
print('   而这个比例是**可以设计的**：')
print('   把格式保证从「指令措辞」搬到「解码约束」，就把一项从 redo 挪到了 portable。')
print('   这是模块 04 那句「约束在长期上比指令优化更值」的量化形式。')"""),

    md("""## ✏️ 练习 2：迁移决策

实现 `migration_decision(old_bundle, new_model, sigma=0.05, n_trials=200)`：

1. 直接搬（`transfer`）：把旧顺序搬到新模型
2. 重做（`redo`）：为新模型搜一个最优顺序
3. 对每种方案跑分层比较，返回

```
dict(baseline_new=..., transfer=..., redo=...,
     transfer_layers_dropped=[...], redo_layers_dropped=[...],
     recommendation='redo'|'transfer'|'stay')
```

推荐规则：
- `redo` 无层下降且 `redo` 总分 ≥ 旧模型总分 → `'redo'`
- 否则若 `transfer` 无层下降且总分 ≥ 旧模型总分 → `'transfer'`
- 否则 → `'stay'`（不迁移）"""),

    code("""def migration_decision(old_bundle, new_model, sigma=0.05, n_trials=200):
    \"\"\"返回上面描述的 dict。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
OLD = make_bundle('model-a@2026-06', demo_order=order_A)
d = migration_decision(OLD, 'model-b@2026-06')
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()})

assert set(d) >= {'baseline_new', 'transfer', 'redo', 'transfer_layers_dropped',
                  'redo_layers_dropped', 'recommendation'}
assert d['recommendation'] in ('redo', 'transfer', 'stay')
# 重做至少不比直接搬差
assert d['redo'] >= d['transfer'] - 1e-9, (d['redo'], d['transfer'])
# 直接搬会掉层，而重做掉的层更少
assert len(d['transfer_layers_dropped']) >= len(d['redo_layers_dropped'])

# 迁到同家族的小版本：变化应当更小
d2 = migration_decision(make_bundle('model-a@2026-01', demo_order=order_A),
                        'model-a@2026-06')
print('\\n迁到同家族小版本:', {k: (round(v, 3) if isinstance(v, float) else v)
                        for k, v in d2.items()})
assert len(d2['transfer_layers_dropped']) <= len(d['transfer_layers_dropped']), \\
    '同家族迁移的层级损失不该比跨家族更大'
print('✅ 练习 2 通过：迁移决策由分层结果给出，而不是由总分给出')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def migration_decision(old_bundle, new_model, sigma=0.05, n_trials=200):
    old_m = run_bundle(old_bundle)
    old_order = [POOL.index(d) for d in old_bundle['demos']]

    b_transfer = make_bundle(new_model, demo_order=old_order)
    m_transfer = run_bundle(b_transfer)

    order_new, _ = best_order_for(new_model, n_trials=n_trials, seed=0,
                                  base=old_order)
    b_redo = make_bundle(new_model, demo_order=order_new)
    m_redo = run_bundle(b_redo)

    def dropped(m):
        return sorted(l for l in LABELS
                      if m['by_label'].get(l, 0.0)
                      < old_m['by_label'].get(l, 0.0) - 2 * sigma)

    d_t, d_r = dropped(m_transfer), dropped(m_redo)
    if not d_r and m_redo['end_to_end'] >= old_m['end_to_end'] - 1e-9:
        rec = 'redo'
    elif not d_t and m_transfer['end_to_end'] >= old_m['end_to_end'] - 1e-9:
        rec = 'transfer'
    else:
        rec = 'stay'
    return dict(baseline_new=run_bundle(make_bundle(new_model,
                                                    BASELINE_ORDER))['end_to_end'],
                transfer=m_transfer['end_to_end'], redo=m_redo['end_to_end'],
                transfer_layers_dropped=d_t, redo_layers_dropped=d_r,
                recommendation=rec)

d = migration_decision(OLD, 'model-b@2026-06')
assert d['recommendation'] in ('redo', 'transfer', 'stay')
assert d['redo'] >= d['transfer'] - 1e-9
assert len(d['transfer_layers_dropped']) >= len(d['redo_layers_dropped'])
print('✅ 参考答案 2 通过')
print(f"   本例推荐: {d['recommendation']}")
print('   注意 `stay` 这个选项的存在很重要：**「迁移」不是一个必然要完成的动作**。')
print('   如果重做之后仍有层下降，正确的结论是「先不迁」，')
print('   而不是「迁了再想办法」——因为迁移之后你已经失去了对照。')"""),

    md("""## ✏️ 练习 3：总成本比较（含 tokenizer 与缓存）

实现 `total_cost_compare(models, demo_strategy_hit, n_out=8, qps_hours=1.0)`：
对每个模型算出

```
dict(model_id -> dict(n_in_tokens, price_in, cache_hit, cost_per_req, cost_per_hour))
```

`demo_strategy_hit` 是示例策略对应的缓存命中率。
`cost_per_hour = cost_per_req * qps_hours * 3600`。

然后实现 `cheapest(models, hit)`：返回按 `cost_per_req` 最便宜的 model_id。

用它检验一个常见的说法：**「单价最低的模型不一定总成本最低」**——
在本课的参数下这个反例**并不存在**，所以这道题的重点是把结论改成可算的形式。"""),

    code("""def total_cost_compare(models, demo_strategy_hit, n_out=8, qps_hours=1.0):
    \"\"\"返回 {model_id: dict(...)}。\"\"\"
    # TODO
    raise NotImplementedError

def cheapest(models, hit):
    \"\"\"返回 cost_per_req 最低的 model_id。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
tbl = total_cost_compare(list(MODELS), demo_strategy_hit=0.9)
print(f"{'模型':<20}{'输入 token':>12}{'单价':>7}{'成本/请求':>12}{'成本/小时':>12}")
for m, v in tbl.items():
    print(f'{m:<20}{v["n_in_tokens"]:>12.0f}{v["price_in"]:>7.1f}'
          f'{v["cost_per_req"]:>12.5f}{v["cost_per_hour"]:>12.2f}')

assert set(tbl) == set(MODELS)
for v in tbl.values():
    assert v['cache_hit'] == 0.9
    assert abs(v['cost_per_hour'] - v['cost_per_req'] * 3600) < 1e-9

# 单价最低的模型
cheapest_price = min(MODELS, key=lambda m: MODELS[m]['price_in'])
print(f'\\n单价最低的模型: {cheapest_price} '
      f'(price {MODELS[cheapest_price]["price_in"]:.1f})')
print(f'总成本最低的模型: {cheapest(list(MODELS), 0.9)}')

# 缓存命中率会改变排序
c_high = cheapest(list(MODELS), 0.95)
c_low = cheapest(list(MODELS), 0.0)
print(f'h=0.95 时最便宜: {c_high} | h=0 时最便宜: {c_low}')
# token_ratio 让「单价低」不等于「总成本低」
b_b = make_bundle('model-b@2026-06', BASELINE_ORDER)
b_c = make_bundle('model-c@2026-06', BASELINE_ORDER)
assert MODELS['model-b@2026-06']['token_ratio'] > \\
       MODELS['model-c@2026-06']['token_ratio'], 'b 的 token 数更多'
print('✅ 练习 3 通过：总成本要按「token 数 × 单价 × (1−缓存命中率)」算')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def total_cost_compare(models, demo_strategy_hit, n_out=8, qps_hours=1.0):
    out = {}
    for m in models:
        b = make_bundle(m, BASELINE_ORDER)
        cfg = MODELS[m]
        n_in = count_tokens(b) * cfg['token_ratio']
        cpr = cost_per_request(b, cache_hit=demo_strategy_hit, n_out=n_out)
        out[m] = dict(n_in_tokens=n_in, price_in=cfg['price_in'],
                      cache_hit=demo_strategy_hit, cost_per_req=cpr,
                      cost_per_hour=cpr * qps_hours * 3600)
    return out

def cheapest(models, hit):
    tbl = total_cost_compare(models, hit)
    return min(tbl, key=lambda m: tbl[m]['cost_per_req'])

tbl = total_cost_compare(list(MODELS), 0.9)
assert set(tbl) == set(MODELS)
for v in tbl.values():
    assert abs(v['cost_per_hour'] - v['cost_per_req'] * 3600) < 1e-9
print('✅ 参考答案 3 通过')
print('   两个容易被忽略的乘数：')
print('   ① **tokenizer**：同一段中文 prompt 在不同 tokenizer 下 token 数差 30%+，')
print('      所以「单价低」不等于「总成本低」；')
print('   ② **缓存命中率**：它由示例策略决定（模块 02 第 3 节的分桶 kNN），')
print('      而它出现在成本公式的括号里——全局 kNN 会把这一项直接归零。')
print('   而输出 token 的单价通常是输入的几倍，所以「让模型少说话」')
print('   （模块 01 的禁止项槽位 + 模块 04 的解码约束）也是一项成本优化。')"""),

    md("""## ✏️ 练习 4：完整的运维门禁

把第 7 节的门禁补全为 `full_gate(card, prev_card)`，在原有规则之外再加三条：

**确定性阻断**
- `card['prompt_fp'] == prev_card['prompt_fp']` 但 changelog 不同
  （「改了说明但什么都没改」）
- `card['constrained']` 为假而 `card['parse_rate'] < 1.0` **且**
  `card['repair_rate'] == 0`（没开约束、解析失败、又没有修复记录 → 修复是静默的）

**报警**
- `card['cost'] > prev_card['cost'] * 1.2`（成本上升超过 20%）

返回 `(blocking, warnings, observations)`。"""),

    code("""def full_gate(card, prev_card):
    \"\"\"返回 (blocking, warnings, observations)。\"\"\"
    # TODO：先调用 ops_gate，再加三条
    raise NotImplementedError"""),

    code("""# —— 自测 ——
PREV = ops_card(make_bundle('model-a@2026-01', BASELINE_ORDER),
                BASE_M, BASE_M, 'v6: 初版', 'v5')

b, w, o = full_gate(card_good, PREV)
print('正常迁移: 阻断', len(b), '| 报警', len(w), '| 观测', len(o))
assert not any('什么都没改' in x for x in b)

# a) 指纹相同但 changelog 不同
same_fp = dict(card_good); same_fp['prompt_fp'] = PREV['prompt_fp']
b2, _, _ = full_gate(same_fp, PREV)
assert any('什么都没改' in x for x in b2), b2

# b) 没开约束 + 解析失败 + 无修复记录 → 静默修复
silent = dict(card_good)
silent['constrained'] = False
silent['parse_rate'] = 0.93
silent['repair_rate'] = 0.0
b3, _, _ = full_gate(silent, PREV)
assert any('静默' in x for x in b3), b3

# c) 成本上升超过 20% → 报警
pricey = dict(card_good); pricey['cost'] = PREV['cost'] * 1.5
_, w4, _ = full_gate(pricey, PREV)
assert any('成本' in x for x in w4), w4

# d) 原有规则仍然生效
nolatest = dict(card_good); nolatest['model_id'] = 'model-b:latest'
assert any('未钉死版本' in x for x in full_gate(nolatest, PREV)[0])
print('✅ 练习 4 通过：七项确定性阻断 + 按层统计阻断 + 三项报警 + 一项观测')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def full_gate(card, prev_card):
    blocking, warn, observe = ops_gate(card, prev_changelog=prev_card['changelog'])
    if card['prompt_fp'] == prev_card['prompt_fp'] and \\
            card['changelog'] != prev_card['changelog']:
        blocking.append('指纹与上一版相同但 changelog 不同——改了说明但什么都没改')
    if (not card['constrained']) and card['parse_rate'] < 1.0 \\
            and card['repair_rate'] == 0:
        blocking.append('没开约束、解析率 < 1.0、却没有任何修复记录'
                        '——修复是静默的，信号被丢掉了')
    if card['cost'] > prev_card['cost'] * 1.2:
        warn.append(f"成本上升 {card['cost'] / prev_card['cost']:.2f}× > 1.2×")
    return blocking, warn, observe

b, w, o = full_gate(card_good, PREV)
same_fp = {**card_good, 'prompt_fp': PREV['prompt_fp']}
assert any('什么都没改' in x for x in full_gate(same_fp, PREV)[0])
silent = {**card_good, 'constrained': False, 'parse_rate': 0.93, 'repair_rate': 0.0}
assert any('静默' in x for x in full_gate(silent, PREV)[0])
assert any('成本' in x for x in
           full_gate({**card_good, 'cost': PREV['cost'] * 1.5}, PREV)[1])
print('✅ 参考答案 4 通过')
print('   第二条新增检查值得单独说：')
print('   **「解析率 < 1.0 而修复率 = 0」是一个自相矛盾的组合**——')
print('   要么修复其实发生了但没被记录（信号丢了），')
print('   要么解析失败被静默当成了「答错」（模块 01 的三个量被混成了一个）。')
print('   两种情形都需要人看，所以它是阻断而不是报警。')
print()
print('   而这套门禁里最重要的一条仍然是回滚指针（第 7 节）：')
print('   **如果回滚需要手动编辑 prompt，那么这次变更是不可回滚的，不该上线。**')"""),

    md("""## 🧪 真实工程胶囊：prompt 运维的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 目录结构：可迁移与不可迁移分开存（讲解第 2 节 / 练习 1）
# ══════════════════════════════════════════════════════════════════
prompts/classify_feedback/
  portable/                       # ← 与模型无关，一份
    signature.json                #   inputs / output / domain / invariants
    format.json
    decoding.json                 #   JSON schema + 约束开关
  models/
    model-a@2026-06/
      instruction.txt  demos.jsonl  calib.json  CHANGELOG.md
    model-b@2026-06/
      instruction.txt  demos.jsonl  calib.json  CHANGELOG.md
  ACTIVE -> models/model-a@2026-06     # ← 一个指针；回滚 = 反向切它

# ══════════════════════════════════════════════════════════════════
# B. 模型 ID 必须钉死（讲解第 1 节）
# ══════════════════════════════════════════════════════════════════
MODEL = 'claude-x@2026-06-01'     # ← 不是 'latest'、不是不带版本
#   钉死之后，服务方更新不会静默改变你的 prompt 面对的对象。
#   而它进指纹，所以「换模型」必然产生一次可见的变更记录。

# ══════════════════════════════════════════════════════════════════
# C. 迁移流程（讲解第 3 节，结构直接来自 C70 模块 05）
# ══════════════════════════════════════════════════════════════════
# 1) 影子评测：(bundle_A, model_B) 与 (bundle_B*, model_B) 都跑
# 2) 三条校验：解析率（确定性）· 分层准确率（统计，按层判）· PSI（观测，不设阈值）
# 3) 灰度 1% → 10% → 50% → 100%，**分流按稳定 ID 哈希，不按请求随机**
# 4) 每一档看分桶 × 分层的指标；两套配置的指纹都进日志
# 5) 保留旧配置 N 天；回滚 = 反向切 ACTIVE

# ══════════════════════════════════════════════════════════════════
# D. 监控四项（讲解第 6 节）—— 三项都不是准确率
# ══════════════════════════════════════════════════════════════════
# parse_rate                    约束下恒为 1.0；掉下来 = 实现 bug
# repair_rate / retry_rate      **解析率的前导指标**；必须显式记录修复
# pred_label_distribution + PSI  抓顺序偏置 / 示例漂移 / 模型换版本
# content_free_probe            每小时一次调用，跟踪标签先验

# ══════════════════════════════════════════════════════════════════
# E. 成本（讲解第 4 节 / 练习 3）
# ══════════════════════════════════════════════════════════════════
# cost = (n_instr + Σ n_demo + n_x) · price_in · (1 − cache_hit) + n_out · price_out
#   两个易忘的乘数：tokenizer（中文差 30%+）与 cache_hit（由示例策略决定）
#   换模型「省钱」必须按 token 数重算，不能只看单价。
```

---

## 小结

| 结论 | 数字 | 在哪一节 |
|---|---|---|
| prompt 是会随模型失效的资产 | 四种失效，三种只能靠监控发现 | 讲解 1 |
| 签名/取值域/格式/解码约束跨模型保留 | 解析率在四个模型上都是 1.0 | 第 2 节 |
| **为 A 优化的示例顺序搬到 B 上不升反降** | 而为 B 重做能拿到更高分 | 第 2 节 |
| 位置偏置的方向在不同模型上可以相反 | A 是 +0.35（近因），B 是 −0.30（首因） | 第 2 节 |
| 迁移的门禁必须按层判，不按总分判 | 有层显著下降而总分几乎没动 | 第 3 节 |
| PSI 是观测量不是门禁 | 换模型必然让分布变化 | 第 3 节 |
| 只改示例策略，成本涨几倍 | 缓存命中率 0.95 → 0 | 第 4 节 |
| tokenizer 的影响被缓存命中率放大或压制 | h=0 时 token_ratio 超过临界值排序就翻转；h=0.9 时临界值被推得很远 | 第 4 节 / 练习 3 |
| 灰度分流按稳定 ID，不按请求随机 | 否则同一会话遇到两套 prompt | 第 5 节 |
| 修复率是解析率的前导指标 | 8 周里它的变化幅度更大 | 第 6 节 |
| 「解析率 < 1.0 而修复率 = 0」自相矛盾 | 修复是静默的，信号丢了 | 练习 4 |
| 回滚必须是切指针 | 需要手动编辑 = 不可回滚 = 不该上线 | 第 7 节 |

**C71 完结。** 全课的一句话：
**prompt 是一个有契约、可分层测量、可搜索、可保证、需要运维的程序——
而这五件事的顺序不能换：先定契约（01）、再拿免费收益（02）、
再自动搜索（03）、能约束的用约束（04）、最后把它当资产管起来（05）。**"""),
]
