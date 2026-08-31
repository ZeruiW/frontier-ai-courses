# -*- coding: utf-8 -*-
"""C68 模块 01 · Task spec 与数据集版本化。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（四层架构与三个性质）；"
                 "知道「哈希」与「语义化版本」两个概念即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_task_spec.ipynb'
                       '（spec 的 schema 校验与默认值 / 内容哈希 vs 稳定 ID 的对比实验 / '
                       '数据集版本链与 diff / 坏题的三种处理路径与它们对历史可比性的影响 / '
                       '分层抽样的子集选择器 / spec 迁移器与向后兼容）'),
    ("核心参考", "OpenAI Evals 的 registry / YAML spec 设计 · "
                 "UK AISI <em>inspect_ai</em> 的 Task/Dataset 抽象 · "
                 "Preston-Werner, <em>Semantic Versioning 2.0.0</em> · "
                 "Gebru et al., <em>Datasheets for Datasets</em>（2018/2021） · "
                 "本课程 C43（数据版本与血缘）· C66 模块 01（任务集设计的六条规则）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("spec-as-data", "Spec 必须是纯数据：三条后果", "".join([
        P("模块 00 说过「spec 是纯数据」是投入产出比最高的结构决策。这一节讲清楚它换来了什么。"),
        TABLE(["性质", "因为 spec 是数据，所以…", "如果 spec 是代码，就要…"], [
            ["<strong>可哈希</strong>", "指纹 = <code>sha256(json)</code>，自动、完整、零维护", "人工维护一份「要记录哪些字段」的清单，且<em>必然会漏</em>"],
            ["<strong>可 diff</strong>", "两次运行的差异是一个结构化的 diff，能精确到字段", "读两份脚本的 git diff，靠人判断哪些改动会影响结果"],
            ["<strong>可生成 / 可扫描</strong>", "「跑 5 个模型 × 3 个温度」是 15 个 spec 的笛卡尔积", "写循环，而循环里的配置又回到了代码里"],
        ]),
        H3("怎么划界：什么进 spec，什么留在代码里"),
        DUAL(
            "一条实用的判据：<strong>「改这个东西，会不会让结果变得不可与之前比较？」</strong>"
            "会 → 进 spec；不会 → 留在代码里。"
            "<em>模型 ID、温度、prompt 模板、判分器版本、任务集版本、步数上限、超时——全部会；"
            "日志格式、进度条样式、重试的退避曲线——通常不会</em>"
            "（注意「重试次数」会，因为它影响错误率）。",
            "更严格的说法：spec 应当包含所有<span class=\"term\">会改变被测量分布</span>的因素。"
            "形式化地，设一次运行产生的结果分布是 $P(\\text{result} \\mid \\text{spec}, \\text{code}, \\text{env})$。"
            "<strong>基础设施的目标是让 $\\text{code}$ 与 $\\text{env}$ 对这个分布的影响可忽略</strong>——"
            "$\\text{env}$ 靠容器 digest 与录制回放固定（C66-05），$\\text{code}$ 靠「把影响分布的东西全搬进 spec」。"
            "<em>剩下的、确实会影响分布但又无法进 spec 的部分（比如并发导致的超时行为），"
            "就是模块 00 里「指纹相同却结果不同」那类告警要抓的东西。</em>",
        ),
        CALLOUT("warn", "一个反复出现的边界情况：<strong>prompt 模板该进 spec 还是留在代码里？</strong>"
                        "答案是<strong>它的哈希必须进 spec</strong>。"
                        "模板本身可以放在文件里（便于编辑与 review），"
                        "但 spec 里要存它的哈希——<em>否则改了一句措辞，指纹不变，两次运行看起来可比但实际不可比</em>。"
                        "这与 C67 模块 01 第 8 节的「judge prompt 是 harness 的一部分」是同一条。"),
    ])),

    # ============================================================== 2
    ("stable-ids", "样本 ID：为什么不能用内容哈希", "".join([
        P("这是评测数据集特有的一个问题，在普通的数据工程里不常见，"
          "但在评测里它<strong>直接决定了历史结果还能不能用</strong>。"),
        ASCII("""
   用内容哈希当 ID（❌）              用稳定 ID（✓）
   ┌────────────────────────┐        ┌────────────────────────┐
   │ id = sha(问题文本)      │        │ id = "billing-017"     │
   │                        │        │ （分配一次，永不改变）   │
   │ 修正一个错别字          │        │ 修正一个错别字          │
   │   → 文本变了            │        │   → 文本变了            │
   │   → **ID 变了**         │        │   → ID **不变**         │
   │   → 历史结果全部对不上   │        │   → 历史结果照样对得上   │
   └────────────────────────┘        └────────────────────────┘
                                      内容哈希单独存一列 content_sha，
                                      用来**检测**内容变化，而不是当 ID。
"""),
        H3("稳定 ID 的四条规则"),
        OL([
            "<strong>ID 分配一次，永不改变</strong>——哪怕内容被修正、被重写。",
            "<strong>ID 永不复用</strong>——删掉的样本，它的 ID 也退休，不能给新样本。"
            "<em>复用 ID 会让历史结果指向一个完全不同的样本，这是最难查的一类污染</em>。",
            "<strong>ID 里不编码可变信息</strong>——不要用 <code>hard_billing_017</code> 这种，"
            "因为「难度」和「所属子集」都会变；<em>那些应该是元数据字段，不是 ID 的一部分</em>。",
            "<strong>同时存 <code>content_sha</code></strong>——它不当 ID，"
            "但它是「这条样本的内容变过没有」的唯一可靠信号。",
        ]),
        CALLOUT("intuition", "第 4 条带来一个很有用的能力：<strong>当你比较两个数据集版本时，"
                             "可以精确地把变化分成四类</strong>——"
                             "新增（ID 只在新版有）、删除（只在旧版有）、"
                             "<strong>内容修改</strong>（ID 同但 content_sha 不同）、"
                             "以及元数据修改（两个都同，但难度/标签变了）。"
                             "<em>这四类对「历史结果还能不能用」的影响完全不同</em>——"
                             "notebook 第 3 节会把这个 diff 器写出来。"),
    ])),

    # ============================================================== 3
    ("versioning", "数据集版本：只增不改，以及三种变更的语义", "".join([
        P("模块 00 的反模式清单里有一条「就地修改任务集」。这一节讲替代方案。"),
        MATH(r"\text{dataset} = (\text{id},\ \text{version},\ \text{sha}) \quad\text{三元组唯一确定一份任务集}"),
        H3("三种变更，三种版本语义"),
        TABLE(["变更类型", "版本怎么走", "历史结果还能用吗", "典型场景"], [
            ["<strong>新增样本</strong>", "<code>v1 → v1.1</code>（次版本）", "<strong>能</strong>：旧样本的结果原样有效，只需补跑新增的", "扩充任务集"],
            ["<strong>修改样本内容</strong>", "<code>v1 → v2</code>（主版本）", "<strong>该样本的历史结果作废</strong>，其余仍有效", "修正坏题、补充缺失信息"],
            ["<strong>删除样本</strong>", "<code>v1 → v2</code>（主版本）", "该样本的历史结果保留但<em>不再进入聚合</em>", "剔除不可解的题（SWE-bench Verified 的做法）"],
        ]),
        DUAL(
            "为什么修改和删除都要走主版本？因为它们都<strong>改变了聚合分母</strong>。"
            "「v1 上 42%」和「v2 上 45%」这两个数字，如果 v2 剔除了 20 道最难的题，"
            "那么这 3 个点的提升可能<em>完全来自分母的变化</em>。"
            "<strong>主版本号的作用就是让这件事在文件名里就能看见</strong>，"
            "而不是藏在某次 commit 里。",
            "更精确地说，评测结果是一个定义在<strong>特定任务集上</strong>的量："
            "$\\hat{p}_{v} = \\frac{1}{|D_v|}\\sum_{i \\in D_v} s_i$。"
            "当 $D_v \\ne D_{v'}$ 时，$\\hat{p}_v$ 与 $\\hat{p}_{v'}$ <strong>估计的是两个不同的总体参数</strong>，"
            "直接比较是无意义的。"
            "<em>唯一可比的做法是在交集 $D_v \\cap D_{v'}$ 上重算两边</em>——"
            "这正是 notebook 第 4 节要实现的「交集重算」。",
        ),
        CALLOUT("danger", "发现坏题时最诱人、也最错误的做法是<strong>「就把那道题改一下，反正只是一道」</strong>。"
                          "后果是：<em>所有引用过 v1 的历史报告，从此都指向一个不存在的东西</em>——"
                          "文件名说 v1，内容已经不是 v1 了。"
                          "<strong>正确做法是发 v2，并且把 v1 保留为只读。</strong>"
                          "存储成本几乎为零（任务集通常只有几 MB），换来的是历史的完整性。"),
        H3("坏题的三条处理路径"),
        UL([
            "<strong>剔除并发新版</strong>——最干净，SWE-bench Verified 走的就是这条；"
            "代价是分母变了，需要在交集上重算历史。",
            "<strong>保留但标记 <code>excluded_from_main</code></strong>——"
            "样本还在，只是不进主指标。<em>好处是历史分母不变，可以直接比较</em>；"
            "坏处是需要在聚合逻辑里处理这个标记。",
            "<strong>修正内容并发主版本</strong>——适用于「题本身是好的，只是描述不全」。",
        ]),
        P("<strong>推荐第二条作为默认</strong>：它对历史可比性的破坏最小，"
          "而且「为什么剔除」这个信息被保留在数据集里而不是某个 commit message 里。"),
    ])),

    # ============================================================== 4
    ("subsets", "子集与切片：一份数据集，多种跑法", "".join([
        P("真实系统里，同一份任务集需要被以不同规模跑："
          "CI 门禁要快（几十条），选型要全（几百条），"
          "而分析要能按维度切片。这些需求<strong>不应该靠拷贝出多份数据集来满足</strong>。"),
        TABLE(["机制", "怎么做", "关键性质"], [
            ["<strong>元数据标签</strong>", "每条样本带 <code>tags</code>（难度、子系统、来源、创建时间）", "切片是查询，不是拷贝"],
            ["<strong>命名子集</strong>", "spec 里声明 <code>subset: \"smoke\"</code>，由标签定义", "子集定义本身也要版本化"],
            ["<strong>确定性抽样</strong>", "<code>sample_n=50, sample_seed=0</code>，用 ID 排序后取", "<strong>同 seed 必然抽到同一批</strong>——这是可复现的前提"],
            ["<strong>分层抽样</strong>", "按标签分层，每层保底 N 条", "小类不会被抽没（呼应 C66-01 的信息量分析）"],
        ]),
        CALLOUT("danger", "确定性抽样有一个比想象中更深的坑，值得把话说透："
                        "<strong>只要你固定抽样数量 N，任务集增长时，抽中的那批就<em>必然</em>会变。</strong>"
                        "这不是实现问题——「从 46 条里抽 15 条」和「从 246 条里抽 15 条」"
                        "本来就是两个不同的均匀样本，原有样本被挤出去是数学上必然的。"
                        "<strong>唯一真正稳定的做法是按<em>比例</em>选而不是按数量选</strong>："
                        "<code>include = int(hash(task_id), 16) % 1000 &lt; rate * 1000</code>。"
                        "这样<em>已有样本的入选与否永远不变</em>，新增样本只是按同样的比例被纳入。"
                        "notebook 第 5 节会把三种做法的稳定性对比出来。"),
        H3("固定数量 vs 固定比例：该选哪个"),
        TABLE(["需求", "该用", "理由"], [
            ["<strong>CI smoke 子集</strong>", "<strong>固定比例 + 分层保底</strong>", "membership 稳定，分数波动才能被归因到模型而不是「换了一批题」"],
            ["「我只有 20 分钟预算」", "固定数量", "接受 membership 会变，但要在报告里注明抽样是变化的"],
            ["调试单条样本", "显式列 ID", "不抽样"],
        ]),
        H3("smoke / full 两档是最常见的配置"),
        P("<strong>smoke 子集</strong>（30–80 条，覆盖各类型各一点，跑几分钟）用于 CI 每次提交；"
          "<strong>full 集</strong>（全量，跑几小时）用于合并前或每日定时。"
          "<em>smoke 的设计目标不是「准确估计分数」，而是「抓住明显的退化」</em>——"
          "所以它的抽样应当<strong>偏向覆盖度而不是代表性</strong>："
          "每个子系统、每种难度都要有，哪怕各只有两三条。"),
    ])),

    # ============================================================== 5
    ("schema-migration", "Schema 演化：只增字段、给默认值、写迁移器", "".join([
        P("spec 的字段一定会变——加新参数、拆旧字段、改语义。"
          "这一节讲怎么让它变得不痛。"),
        OL([
            "<strong>只增字段，不改语义。</strong>"
            "把 <code>timeout</code> 从「秒」改成「毫秒」是最坏的一类变更——"
            "<em>旧 spec 依然能解析，但含义变了，而且不会报错</em>。"
            "需要改语义时，<strong>加一个新字段并废弃旧的</strong>。",
            "<strong>新字段必须有默认值</strong>，且默认值要让旧 spec 的行为<strong>保持不变</strong>。"
            "例如新增 <code>retries</code> 时默认设为 0（而不是 2），"
            "否则所有历史 spec 的语义都被悄悄改了。",
            "<strong>spec 自带 <code>schema_version</code></strong>，"
            "并写一个 <code>migrate(spec)</code> 函数把旧版本升到当前版本。"
            "<em>迁移必须是纯函数且幂等</em>：<code>migrate(migrate(x)) == migrate(x)</code>。",
            "<strong>指纹在迁移后计算</strong>——否则同一个语义的 spec，"
            "旧格式和新格式会算出不同的指纹，历史结果又对不上了。",
        ]),
        CALLOUT("intuition", "第 4 条是个容易忽略但很关键的细节。"
                             "<strong>指纹应该是「规范化之后的 spec」的哈希</strong>，"
                             "而不是「用户写的那份 spec」的哈希。"
                             "<em>规范化包括：迁移到当前 schema、填上所有默认值、"
                             "把等价的写法归一（比如 <code>1</code> 与 <code>1.0</code>）。</em>"
                             "<strong>这样「显式写了默认值」和「没写」会算出同一个指纹</strong>——"
                             "这正是你想要的语义。"),
        H3("向后兼容的一个反例"),
        CODE("""# ❌ 危险的变更：新字段的默认值改变了旧 spec 的行为
# v1 的 spec 没有 retries 字段，当时的行为等价于 retries=0
{"budget": {"timeout_s": 30}}

# v2 加了 retries，默认值设成 2
DEFAULTS = {"retries": 2}          # ← 所有历史 spec 的错误率都被悄悄改了

# ✓ 正确：默认值保持旧行为，需要重试的显式写出来
DEFAULTS = {"retries": 0}"""),
    ])),

    # ============================================================== 6
    ("datasheet", "数据集也要有一张卡：来源、构造、已知缺陷", "".join([
        P("最后一节讲一个经常被跳过、但半年后必然后悔没做的东西："
          "<strong>给任务集配一份说明（datasheet）</strong>。"),
        P("它要回答的问题很具体——<em>都是「半年后有人会问、而当时的人已经离职」的那些</em>："),
        TABLE(["问题", "为什么会被问到", "不记的后果"], [
            ["<strong>样本从哪来</strong>", "评估污染风险（C66-01）", "无法判断分数是不是被污染撑起来的"],
            ["<strong>创建/采集时间</strong>", "做时间截断检验", "污染检测最有力的手段直接用不了"],
            ["<strong>谁标注的、标注规范是什么</strong>", "怀疑标签质量时要追溯", "只能重新标一遍"],
            ["<strong>已知坏题清单</strong>", "「这道题为什么被剔除」", "同一道坏题被反复发现、反复讨论"],
            ["<strong>不可能任务的比例</strong>", "解读「放弃率」这个指标", "把正确的放弃误判成失败（C66-01）"],
            ["<strong>判分器与它的 α/β</strong>", "校正观测值（C66-02）", "所有数字都可能是系统性偏的"],
            ["<strong>预期的合理分数区间</strong>", "判断「跑出 95%」是好消息还是 bug", "<strong>最容易被忽略、也最实用的一条</strong>"],
        ]),
        CALLOUT("intuition", "最后一行值得展开：<strong>给每个任务集写一句「合理的分数应该落在哪个区间」</strong>，"
                             "是一条极其便宜的健康检查。"
                             "<em>如果一个预期 30–50% 的任务集突然跑出 95%，"
                             "那几乎肯定是流水线出了问题（判分器坏了、答案泄漏进 prompt 了、"
                             "或者任务集被换成了 smoke 子集），而不是模型突然变强了。</em>"
                             "<strong>这条检查在 CI 里就是一行断言</strong>（04 模块）。"),
        P("datasheet 应当和数据集<strong>放在一起并一起版本化</strong>——"
          "放在 wiki 里的说明，三个月后必然与数据集脱节。"),
    ])),

    # ============================================================== 7
    ("checklist", "本模块的落地清单", "".join([
        CODE("""dataset/
  qa-tasks/
    v1/
      tasks.jsonl          # 每行: {task_id, content_sha, input, target, tags, meta}
      datasheet.md         # 来源 / 时间 / 标注 / 已知坏题 / 预期分数区间
      MANIFEST.json        # {"sha": "...", "n": 512, "created": "2026-03-01", "frozen": true}
    v2/
      tasks.jsonl
      datasheet.md
      MANIFEST.json
      CHANGELOG.md         # 相对 v1: 新增 12 / 修改 3 / 剔除 8（附每条的理由）
  subsets/
    smoke.json             # {"name":"smoke","filter":{"tags":["core"]},"sample_n":60,"seed":0}

spec/
  demo-qa.json             # 引用 dataset id+version+sha，不内联任务内容"""),
        UL([
            "<strong><code>frozen: true</code> 是一条硬约束</strong>："
            "已发布的版本目录设为只读，CI 里加一条检查——"
            "<em>已冻结版本的 sha 与 MANIFEST 不一致就直接失败</em>。",
            "<strong>CHANGELOG 要逐条记理由</strong>，尤其是剔除的那些。"
            "「为什么剔除这道题」是最容易丢失、也最容易被重复讨论的信息。",
            "<strong>spec 不内联任务内容</strong>，只引用 <code>(id, version, sha)</code>。"
            "<em>内联会让 spec 变得巨大且无法 diff</em>。",
            "<strong>子集定义是独立文件且要版本化</strong>——"
            "改了 smoke 的定义，等于换了一个任务集。",
        ]),
        CALLOUT("warn", "最后强调一遍本模块的核心纪律，因为它是所有后续模块的地基："
                        "<strong>任务集只增不改；改了就发新版本；已发布的版本永远只读。</strong>"
                        "<em>违反这一条的代价不是「不够规范」，而是「所有历史数字失去意义」</em>——"
                        "而这件事发生时不会有任何报错。"),
    ])),
    # ============================================================== 8x
    ("who-writes", "谁来写任务：三种来源与各自的偏倚", "".join([
        P("补一个模块 01 之前没说的问题：<strong>这些任务是谁写的，以及这件事怎么影响结果。</strong>"),
        TABLE(["来源", "怎么产生", "系统性偏倚", "该怎么标注"], [
            ["<strong>人工构造</strong>", "工程师/领域专家按经验写", "<strong>偏向「已知的失败模式」</strong>——写题的人写的是他想到的问题", "<code>source: manual</code>"],
            ["<strong>线上回灌</strong>", "从真实流量的问题样本转化（模块 05）", "<strong>偏向模型的弱项</strong>，占比过高会让任务集漂成疑难杂症集", "<code>source: from_production</code>，且设占比上限"],
            ["<strong>公开基准</strong>", "直接引入", "<strong>污染风险最高</strong>（C66-01）；分类体系可能与你的产品定义不一致", "<code>source: public</code> + 原始基准的版本"],
            ["<strong>合成生成</strong>", "用模型批量造题", "<strong>偏向生成模型自己擅长的形态</strong>；难度分布过于集中", "<code>source: synthetic</code> + 生成配置的哈希"],
        ]),
        CALLOUT("warn", "<strong><code>source</code> 这个字段的价值在于它让上面这些偏倚变得可分析。</strong>"
                        "<em>「这次提升主要来自 from_production 的那批题」和"
                        "「主要来自 manual 的那批」，是两个完全不同的结论</em>——"
                        "前者说明修好了真实问题，后者可能只是拟合了写题人的偏好。"
                        "<strong>而没有这个字段，这两种情况在数据里长得一模一样。</strong>"),
        P("合成任务还有一个特有的要求：<strong>生成配置必须被记录并版本化</strong>"
          "（用什么模型、什么 prompt、什么参数生成的）。"
          "<em>否则你无法回答「这批合成题为什么和上批不一样」</em>——"
          "而这正是本课模块 00「可归因性」在数据侧的同一条要求。"),
    ])),

    # ============================================================== 8
    ("multi-dataset", "多数据集与组合评测：一次运行跑多个任务集", "".join([
        P("真实系统里很少只有一个任务集。典型的配置是"
          "「核心能力集 + 安全集 + 回归集 + 线上回灌集」四个一起跑。"
          "<strong>这带来两个模块 01 之前没处理的问题：怎么聚合、怎么版本化。</strong>"),
        H3("问题一：跨数据集怎么聚合"),
        TABLE(["方式", "怎么算", "适合", "陷阱"], [
            ["<strong>不聚合</strong>", "每个数据集单独报一个数", "<strong>推荐默认</strong>", "读者需要自己综合，但这是诚实的"],
            ["<strong>等权平均</strong>", "各数据集分数取平均", "各集重要性相当时", "小数据集的噪声被放大到与大数据集同权"],
            ["<strong>按样本量加权</strong>", "等价于把所有样本合并求 micro", "各集来自同一分布时", "<strong>大数据集主导总分</strong>（C66-02 的 micro 陷阱）"],
            ["<strong>按业务重要性加权</strong>", "人为指定权重", "对外报告一个数时", "权重来源必须写进报告，否则不可复现"],
        ]),
        CALLOUT("warn", "<strong>「不聚合」应当是默认选择</strong>，理由和 C66 模块 02 的 micro/macro 讨论一致："
                        "<em>把安全集的 98% 和核心能力集的 43% 平均成 70.5%，"
                        "这个数字既不能用来判断能力，也不能用来判断安全</em>。"
                        "<strong>如果一定要一个总分（比如给管理层看），"
                        "那么权重必须显式写出来，并且要做敏感性分析</strong>——"
                        "权重扰动 ±20% 会不会翻转结论（呼应 C67-01 的 rubric 权重）。"),
        H3("问题二：组合的版本化"),
        P("每个数据集有自己的版本，那么<strong>「这次跑的是哪个组合」也需要一个版本</strong>："),
        CODE("""// suite.json —— 组合本身也是一个可版本化的对象
{
  "suite_id": "prod-eval",
  "suite_version": "v7",
  "datasets": [
    {"id": "core-tasks",   "version": "v12", "sha": "7d2e…", "weight": null},
    {"id": "safety-tasks", "version": "v4",  "sha": "a91c…", "weight": null},
    {"id": "regression",   "version": "v23", "sha": "3f8b…", "weight": null},
    {"id": "prod-replay",  "version": "v9",  "sha": "c04d…", "weight": null}
  ],
  "aggregation": "none",        // none | equal | micro | weighted
  "report_separately": true
}"""),
        UL([
            "<strong>suite 的指纹 = 各数据集三元组 + 聚合方式的哈希</strong>——"
            "<em>换掉任何一个子集的版本，suite 版本就要走</em>；",
            "<strong>子集之间的样本 ID 必须全局唯一</strong>："
            "<em>如果 core-tasks 和 regression 里都有 <code>t001</code>，"
            "结果表的主键就会冲突</em>。实践做法是给 ID 加数据集前缀（<code>core:t001</code>）；",
            "<strong>回归集是一个特殊的子集</strong>——它由线上回灌构成（模块 05），"
            "<em>只增不删，而且它的分数应当接近 100%</em>（因为都是已经修过的问题）。"
            "<strong>回归集的分数下降是一个比总分下降严重得多的信号。</strong>",
        ]),
        H3("一个实践细节：数据集之间会有重叠"),
        P("组合评测里一个容易被忽略的问题：<strong>同一道题可能同时出现在两个数据集里</strong>——"
          "线上回灌的问题被加进了回归集，而它恰好也被人工加进了核心能力集。"
          "<em>如果两边用了不同的 task_id，这道题会被算两遍；"
          "如果用了同一个 ID，结果表的主键就会冲突。</em>"),
        P("<strong>正确处理：在 suite 层面做一次去重检查，并显式声明「同一道题归属哪个集」。</strong>"
          "推荐的归属规则是<em>「最严格的那个集优先」</em>——"
          "同时出现在核心集与回归集时归回归集，"
          "因为回归集的门禁更严（下一段），归到那边不会漏掉问题。"),
        CALLOUT("intuition", "最后一条值得展开：<strong>回归集的语义与其他集完全不同。</strong>"
                             "核心能力集问「能做到多少」，回归集问「有没有把修好的又弄坏」。"
                             "<em>前者的分数是 40% 也很正常，后者掉到 95% 就该拉警报</em>——"
                             "<strong>所以它们的门禁阈值也应当完全不同</strong>（模块 04）。"
                             "把它们平均成一个数，等于同时毁掉两个信号。"),
    ])),
]

NB = [
    md("""# 01 · Task spec 与数据集版本化（schema / 稳定 ID / 版本链 / 子集 / 迁移）

目标：把「任务集只增不改」这条纪律，变成**几个可以运行、可以断言的机制**。

本 notebook 你会亲手实现：
1. **spec 的 schema 校验与规范化** —— 填默认值、迁移旧版本，**指纹在规范化之后算**
2. **内容哈希 vs 稳定 ID** —— 改一个错别字，两种方案下历史结果各会怎样
3. **数据集 diff 器** —— 把版本差异精确分成新增/删除/内容修改/元数据修改四类
4. **坏题的三条处理路径** —— 各自对历史可比性的影响，以及「交集重算」
5. **确定性抽样的稳定性** —— 为什么「打乱取前 N」在扩样本时会全变
6. **分层抽样的 smoke 子集** —— 偏向覆盖度而不是代表性

> 心智模型：**评测结果是一个定义在特定任务集上的量。
> 任务集变了，你估计的就是另一个总体参数——直接比较是无意义的。**"""),

    md("""## 0 · 环境与示例数据集"""),

    code("""import os, json, math, hashlib, shutil, random, itertools
from collections import Counter, defaultdict

import numpy as np

TMP = os.path.abspath('./_eval_tmp')
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP, exist_ok=True)

def stable_hash(obj, n=8):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:n]

def content_sha(task):
    # 只对**内容字段**取哈希——tags/meta 变化不算内容变化
    return stable_hash({k: task[k] for k in ('input', 'target')}, 12)

def make_task(task_id, inp, target, tags):
    t = {'task_id': task_id, 'input': inp, 'target': target, 'tags': tags}
    t['content_sha'] = content_sha(t)
    return t

V1 = [
    make_task('billing-001', '订单 A 的退款金额是多少？', '120', ['core', 'easy', 'billing']),
    make_task('billing-002', '用户能否取消已发货订单？', 'no',  ['core', 'medium', 'billing']),
    make_task('billing-003', '优惠券叠加规则是什么？',   'stack_max_1', ['hard', 'billing']),
    make_task('flight-001',  '改签手续费怎么算？',       'fee_10pct', ['core', 'medium', 'flight']),
    make_task('flight-002',  '超售时的补偿标准？',       'comp_400', ['hard', 'flight']),
    make_task('flight-003',  '婴儿票是否占座？',         'no', ['core', 'easy', 'flight']),
]
print(f'V1 共 {len(V1)} 条')
for t in V1[:2]:
    print(' ', {k: t[k] for k in ('task_id', 'content_sha', 'tags')})
assert len({t['task_id'] for t in V1}) == len(V1), 'task_id 必须唯一'
print('\\n✅ 每条样本有两个标识：**稳定的 task_id**（永不改变）与 **content_sha**（用来检测内容变化）。')"""),

    md("""## 1 · spec 的规范化：填默认值 → 迁移 → 再算指纹

**关键点**：指纹是「规范化之后的 spec」的哈希。
这样「显式写了默认值」和「没写」会算出同一个指纹 —— 这正是你想要的语义。"""),

    code("""SCHEMA_VERSION = 3

DEFAULTS = {
    'model': {'temperature': 0.0, 'seed': 0, 'max_tokens': 1024},
    # 注意 retries 默认是 0 —— 保持「旧 spec 没写就是不重试」的语义（讲解第 5 节）
    'budget': {'max_attempts': 1, 'timeout_s': 30, 'retries': 0},
    'runner': {'concurrency': 4, 'cache': True},
    'scorer': {'kind': 'exact_match', 'version': 'v1'},
}

def deep_fill(d, defaults):
    out = json.loads(json.dumps(d))
    for k, v in defaults.items():
        if isinstance(v, dict):
            out[k] = deep_fill(out.get(k, {}), v)
        else:
            out.setdefault(k, v)
    return out

def migrate(spec):
    \"\"\"把旧 schema 升到当前版本。必须是纯函数且幂等。\"\"\"
    s = json.loads(json.dumps(spec))
    v = s.get('schema_version', 1)
    if v < 2:
        # v1 → v2: timeout 从毫秒改成秒时，**加新字段**而不是改旧字段的语义
        if 'timeout_ms' in s.get('budget', {}):
            s['budget']['timeout_s'] = s['budget'].pop('timeout_ms') / 1000.0
        v = 2
    if v < 3:
        # v2 → v3: dataset 从裸字符串变成三元组
        if isinstance(s.get('dataset'), str):
            s['dataset'] = {'id': s['dataset'], 'version': 'v1', 'sha': None}
        v = 3
    s['schema_version'] = SCHEMA_VERSION
    return s

def normalize(spec):
    return deep_fill(migrate(spec), DEFAULTS)

def fingerprint(spec):
    return stable_hash(normalize(spec), 8)

# 三份"看起来不同"但语义相同的 spec
spec_minimal = {'name': 'demo', 'dataset': {'id': 'qa', 'version': 'v1', 'sha': 'abc'},
                'model': {'id': 'm1'}}
spec_explicit = {'name': 'demo', 'dataset': {'id': 'qa', 'version': 'v1', 'sha': 'abc'},
                 'model': {'id': 'm1', 'temperature': 0.0, 'seed': 0, 'max_tokens': 1024},
                 'budget': {'max_attempts': 1, 'timeout_s': 30, 'retries': 0},
                 'runner': {'concurrency': 4, 'cache': True},
                 'scorer': {'kind': 'exact_match', 'version': 'v1'},
                 'schema_version': 3}
spec_old = {'name': 'demo', 'dataset': 'qa', 'model': {'id': 'm1'},
            'budget': {'timeout_ms': 30000}, 'schema_version': 1}

print('最简写法   指纹:', fingerprint(spec_minimal))
print('全写默认值 指纹:', fingerprint(spec_explicit))
assert fingerprint(spec_minimal) == fingerprint(spec_explicit)
print('→ 一致 ✓（写不写默认值不影响语义，因此不该影响指纹）')

# 迁移必须幂等
assert migrate(migrate(spec_old)) == migrate(spec_old)
print('\\n旧 spec 迁移后:', json.dumps(migrate(spec_old)['budget'], ensure_ascii=False))
print('迁移幂等性 ✓')
print('\\n✅ 指纹在规范化之后算——否则同一语义的新旧格式会算出不同指纹，历史结果又对不上了。')"""),

    code("""# 反例：如果新字段的默认值改变了旧 spec 的行为
BAD_DEFAULTS = json.loads(json.dumps(DEFAULTS)); BAD_DEFAULTS['budget']['retries'] = 2

def normalize_bad(spec):
    return deep_fill(migrate(spec), BAD_DEFAULTS)

old_semantics = normalize(spec_old)['budget']['retries']
new_semantics = normalize_bad(spec_old)['budget']['retries']
print(f'旧 spec 当时的行为: retries=0')
print(f'  正确的默认值 → retries={old_semantics}   （语义保持）')
print(f'  错误的默认值 → retries={new_semantics}   ← **所有历史 spec 的错误率都被悄悄改了**')
assert old_semantics == 0 and new_semantics == 2
print('\\n✅ 新字段的默认值必须让旧 spec 的行为**保持不变**。')
print('   这条错了不会报错，只会让历史与现在的数字失去可比性。')"""),

    md("""## 2 · 内容哈希 vs 稳定 ID：改一个错别字会怎样"""),

    code("""# 场景：修正 billing-003 的一个错别字（内容变了，但它还是同一道题）
V1_FIXED = json.loads(json.dumps(V1))
for t in V1_FIXED:
    if t['task_id'] == 'billing-003':
        t['input'] = '优惠券的叠加规则是什么？'      # 加了一个「的」
        t['content_sha'] = content_sha(t)

# 方案 A（❌）：用内容哈希当 ID
def id_by_content(task):
    return content_sha(task)

# 方案 B（✓）：稳定 ID
def id_stable(task):
    return task['task_id']

old_ids_A = {id_by_content(t) for t in V1}
new_ids_A = {id_by_content(t) for t in V1_FIXED}
old_ids_B = {id_stable(t) for t in V1}
new_ids_B = {id_stable(t) for t in V1_FIXED}

print(f'内容哈希当 ID: 修正前后能对上的样本 {len(old_ids_A & new_ids_A)} / {len(V1)}')
print(f'稳定 ID:       修正前后能对上的样本 {len(old_ids_B & new_ids_B)} / {len(V1)}')
assert len(old_ids_A & new_ids_A) == len(V1) - 1
assert len(old_ids_B & new_ids_B) == len(V1)
print('\\n✅ 用内容哈希当 ID：改一个字，这条样本的历史结果就永远对不上了。')
print('   用稳定 ID：ID 不变，历史结果照样对得上；而 content_sha 单独告诉你「内容变过」。')
print('   → **content_sha 用来检测变化，不用来当 ID。**')"""),

    md("""## 3 · 数据集 diff 器：四类变化，四种影响"""),

    code("""def dataset_diff(old, new):
    \"\"\"把两个版本的差异精确分成四类。这四类对「历史结果能不能用」的影响完全不同。\"\"\"
    o = {t['task_id']: t for t in old}
    n = {t['task_id']: t for t in new}
    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    common = set(o) & set(n)
    content_changed = sorted(i for i in common if o[i]['content_sha'] != n[i]['content_sha'])
    meta_changed = sorted(i for i in common
                          if o[i]['content_sha'] == n[i]['content_sha']
                          and o[i].get('tags') != n[i].get('tags'))
    return {'added': added, 'removed': removed,
            'content_changed': content_changed, 'meta_changed': meta_changed}

# 构造 v2：新增 2 条、剔除 1 条坏题、修正 1 条内容、改 1 条标签
V2 = [t for t in json.loads(json.dumps(V1)) if t['task_id'] != 'flight-002']   # 剔除坏题
for t in V2:
    if t['task_id'] == 'billing-003':
        t['input'] = '优惠券的叠加规则是什么？'; t['content_sha'] = content_sha(t)
    if t['task_id'] == 'flight-001':
        t['tags'] = ['core', 'hard', 'flight']            # 难度重标：medium → hard
V2 += [make_task('billing-004', '部分退款如何处理？', 'partial_ok', ['core', 'medium', 'billing']),
       make_task('flight-004',  '宠物托运费用？',     'pet_200',   ['hard', 'flight'])]

d = dataset_diff(V1, V2)
print(f"{'变化类型':<18}{'样本':<40}{'历史结果还能用吗'}")
IMPACT = {'added': '不适用（本来就没有）', 'removed': '保留但不再进入聚合',
          'content_changed': '**该样本的历史结果作废**', 'meta_changed': '能用（切片口径变了）'}
for k in ['added', 'removed', 'content_changed', 'meta_changed']:
    print(f'{k:<18}{str(d[k]):<40}{IMPACT[k]}')

assert d['added'] == ['billing-004', 'flight-004']
assert d['removed'] == ['flight-002']
assert d['content_changed'] == ['billing-003']
assert d['meta_changed'] == ['flight-001']
print('\\n✅ 四类变化被精确分开——而这四类对历史可比性的影响完全不同。')
print('   注意 meta_changed：内容没变但难度标签变了，**切片口径变了但总分仍可比**。')"""),

    code("""# 版本号该怎么走：由 diff 自动推导
def suggest_version(old_ver, diff):
    major, minor = (int(x) for x in old_ver.lstrip('v').split('.')) if '.' in old_ver \\
        else (int(old_ver.lstrip('v')), 0)
    breaking = bool(diff['removed'] or diff['content_changed'])
    if breaking:
        return f'v{major + 1}'
    if diff['added'] or diff['meta_changed']:
        return f'v{major}.{minor + 1}'
    return old_ver

print('本次 diff 建议的版本号:', suggest_version('v1', d))
assert suggest_version('v1', d) == 'v2'
assert suggest_version('v1', {'added': ['x'], 'removed': [], 'content_changed': [],
                              'meta_changed': []}) == 'v1.1'
assert suggest_version('v1', {'added': [], 'removed': [], 'content_changed': [],
                              'meta_changed': []}) == 'v1'
print('  只新增        → v1.1（次版本，历史全部有效）')
print('  剔除或改内容  → v2  （主版本，分母变了）')
print('\\n✅ 版本号不是拍脑袋写的，是由 diff 推导出来的——这让「分母变了」这件事在文件名里就能看见。')"""),

    md("""## 4 · 坏题的三条处理路径，以及「交集重算」"""),

    code("""rng = np.random.default_rng(0)
# 模拟：模型在 V1 上的逐题得分（flight-002 是坏题，谁做都错）
SCORES_V1 = {'billing-001': 1.0, 'billing-002': 1.0, 'billing-003': 0.0,
             'flight-001': 1.0, 'flight-002': 0.0, 'flight-003': 1.0}

def aggregate(scores, tasks, exclude_tag='excluded_from_main'):
    ids = [t['task_id'] for t in tasks if exclude_tag not in t.get('tags', [])]
    vals = [scores[i] for i in ids if i in scores]
    return (sum(vals) / len(vals)) if vals else float('nan'), len(vals)

# 路径 1：剔除并发 v2（分母变了）
V2_removed = [t for t in json.loads(json.dumps(V1)) if t['task_id'] != 'flight-002']
# 路径 2：保留但标记 excluded_from_main（分母也变了，但样本还在）
V2_marked = json.loads(json.dumps(V1))
for t in V2_marked:
    if t['task_id'] == 'flight-002':
        t['tags'] = t['tags'] + ['excluded_from_main']

base, n_base = aggregate(SCORES_V1, V1)
rem, n_rem = aggregate(SCORES_V1, V2_removed)
mark, n_mark = aggregate(SCORES_V1, V2_marked)
print(f"{'方案':<26}{'分数':>8}{'分母':>6}")
print(f'{"v1 原样":<26}{base:>8.1%}{n_base:>6}')
print(f'{"路径1 剔除并发 v2":<26}{rem:>8.1%}{n_rem:>6}')
print(f'{"路径2 保留但标记排除":<26}{mark:>8.1%}{n_mark:>6}')
assert rem == mark, '两条路径的主指标相同'
assert rem > base, '剔除一道谁都做错的坏题，分数必然上升'
print(f'\\n⚠️ 分数从 {base:.1%} 涨到 {rem:.1%}——**这 16.7 个点完全来自分母变化，模型一点没变**。')
print('   这就是为什么剔除必须走主版本号：让「分母变了」在文件名里就能看见。')"""),

    code("""# 唯一正确的跨版本比较方式：在交集上重算两边
def intersect_compare(scores_a, tasks_a, scores_b, tasks_b):
    ids_a = {t['task_id'] for t in tasks_a}
    ids_b = {t['task_id'] for t in tasks_b}
    common = sorted(ids_a & ids_b)
    va = [scores_a[i] for i in common if i in scores_a]
    vb = [scores_b[i] for i in common if i in scores_b]
    return {'n_common': len(common),
            'a': sum(va) / len(va) if va else float('nan'),
            'b': sum(vb) / len(vb) if vb else float('nan')}

# 新模型在 v2 上的得分（把 billing-003 做对了，其余不变）
SCORES_V2 = dict(SCORES_V1); SCORES_V2['billing-003'] = 1.0
SCORES_V2.update({'billing-004': 1.0, 'flight-004': 0.0})

naive_a, _ = aggregate(SCORES_V1, V1)
naive_b, _ = aggregate(SCORES_V2, V2)
print(f'朴素比较: v1 上 {naive_a:.1%} → v2 上 {naive_b:.1%}，看起来涨了 {naive_b-naive_a:+.1%}')

ic = intersect_compare(SCORES_V1, V1, SCORES_V2, V2)
print(f'\\n交集重算（{ic["n_common"]} 条共同样本）: {ic["a"]:.1%} → {ic["b"]:.1%}，'
      f'真实提升 {ic["b"]-ic["a"]:+.1%}')
assert ic['n_common'] < len(V1) and ic['n_common'] < len(V2)
assert abs((ic['b'] - ic['a']) - (naive_b - naive_a)) > 1e-6
print('\\n✅ 朴素比较把「分母变化」和「模型提升」混在了一起；')
print('   交集重算只在**两个版本都有的样本**上比较，这才是唯一可解释的跨版本对比。')
print('   注意：billing-003 内容变过，严格来说也该排除——练习 2 会处理这个细节。')"""),

    md("""## 5 · 确定性抽样：为什么「打乱取前 N」在扩样本时会全变"""),

    code("""def sample_shuffle(tasks, n, seed):
    \"\"\"打乱后取前 N。确定性有（同 seed 同结果），但对任务集增长完全不稳定。\"\"\"
    ids = sorted(t['task_id'] for t in tasks)
    rnd = random.Random(seed)
    rnd.shuffle(ids)
    return sorted(ids[:n])

def sample_hash_topn(tasks, n, seed):
    \"\"\"按 hash(task_id + seed) 排序取前 N。看起来更稳，但**只要 N 固定就仍然不稳**。\"\"\"
    scored = sorted(tasks, key=lambda t: stable_hash([t['task_id'], seed], 16))
    return sorted(t['task_id'] for t in scored[:n])

def sample_rate(tasks, rate, seed):
    \"\"\"✓ 按**比例**选：每条样本独立判定，与任务集里有哪些别的样本无关。
    这是唯一能让「已有样本的入选与否永不改变」的做法。\"\"\"
    keep = []
    for t in tasks:
        h = int(stable_hash([t['task_id'], seed], 16), 16)
        if (h % 10000) < rate * 10000:
            keep.append(t['task_id'])
    return sorted(keep)

BIG = V1 + [make_task(f'gen-{i:03d}', f'q{i}', str(i), ['core']) for i in range(40)]
BIG_PLUS = BIG + [make_task(f'x{i:04d}', f'q{i}', str(i), ['core']) for i in range(200)]

a1, b1 = set(sample_shuffle(BIG, 15, 0)), set(sample_shuffle(BIG_PLUS, 15, 0))
a2, b2 = set(sample_hash_topn(BIG, 15, 0)), set(sample_hash_topn(BIG_PLUS, 15, 0))
a3, b3 = set(sample_rate(BIG, 0.33, 0)), set(sample_rate(BIG_PLUS, 0.33, 0))

print(f"{'做法':<24}{'原始规模':>10}{'扩后规模':>10}{'原有样本的入选是否改变':>26}")
print(f'{"打乱取前 N":<24}{len(a1):>10}{len(b1):>10}'
      f'{f"变了 {len(a1 - b1)} 条":>26}')
print(f'{"hash 排序取前 N":<24}{len(a2):>10}{len(b2):>10}'
      f'{f"变了 {len(a2 - b2)} 条":>26}')
print(f'{"按比例选（rate=0.33）":<24}{len(a3):>10}{len(b3):>10}'
      f'{f"变了 {len(a3 - b3)} 条":>26}')

assert len(a1 - b1) > 0 and len(a2 - b2) > 0, '固定 N 的两种做法都会掉样本'
assert a3 <= b3, '按比例选：原有的入选样本必须全部保留'
assert len(a3 - b3) == 0
print('\\n✅ 关键结论：**只要 N 固定，任务集增长时抽中的那批就必然会变**——')
print('   这不是实现问题，「从 46 条抽 15」和「从 246 条抽 15」本来就是两个不同的均匀样本。')
print('   按比例选则完全稳定：每条样本独立判定，与任务集里有哪些别的样本无关。')
print(f'   代价是规模会随任务集增长（{len(a3)} → {len(b3)} 条），需要配合分层保底来控制。')"""),

    code("""# 分层抽样：smoke 子集要偏向**覆盖度**而不是代表性
def stratified_smoke(tasks, per_stratum=2, key=lambda t: (t['tags'][1] if len(t['tags']) > 1
                                                          else 'na'), seed=0):
    \"\"\"按难度分层，每层保底 per_stratum 条。目标是覆盖，不是代表性。\"\"\"
    by = defaultdict(list)
    for t in tasks:
        by[key(t)].append(t)
    out = []
    for k in sorted(by):
        ranked = sorted(by[k], key=lambda t: stable_hash([t['task_id'], seed], 16))
        out += [t['task_id'] for t in ranked[:per_stratum]]
    return sorted(out)

MIXED = V1 + [make_task(f'g{i:02d}', f'q{i}', str(i),
                        ['core', ['easy', 'medium', 'hard'][i % 3]]) for i in range(30)]
smoke = stratified_smoke(MIXED, per_stratum=3)
cover = Counter(next((tt for tt in t['tags'] if tt in ('easy', 'medium', 'hard')), 'na')
                for t in MIXED if t['task_id'] in smoke)
print('smoke 子集:', smoke)
print('各难度覆盖:', dict(cover))
assert all(v >= 3 for k, v in cover.items() if k != 'na'), '每个难度层都要有保底名额'
assert len(smoke) < len(MIXED) / 3
print(f'\\n✅ {len(smoke)} 条 smoke 覆盖了全部难度层，规模只有全集的 {len(smoke)/len(MIXED):.0%}。')
print('   smoke 的目标不是准确估计分数，是**抓住明显的退化**——所以覆盖度优先于代表性。')"""),

    md("""## ✏️ 练习 1：数据集健康检查

实现 `dataset_health(tasks)`：返回一个字典，包含
`n`（样本数）、`dup_ids`（重复的 task_id 列表）、`dup_content`（内容完全相同的 content_sha 列表）、
`stale_sha`（`content_sha` 与重算结果不一致的 task_id 列表）、`ok`（三者都为空则 True）。"""),

    code("""def dataset_health(tasks):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
h = dataset_health(V1)
assert h['ok'] is True and h['n'] == len(V1)

bad = json.loads(json.dumps(V1))
bad.append(dict(bad[0]))                                    # 重复 ID
bad[1]['input'] = '改了内容但没更新 content_sha'             # stale sha
h2 = dataset_health(bad)
print('健康的数据集:', {k: v for k, v in h.items() if k != 'n'})
print('有问题的数据集:', {k: v for k, v in h2.items() if k != 'n'})
assert h2['ok'] is False
assert h2['dup_ids'] == ['billing-001']
assert h2['stale_sha'] == ['billing-002']
print('✅ 练习 1 通过：这三项检查应当在 CI 里对每个数据集版本跑一遍——')
print('   重复 ID 会让聚合分母出错，stale sha 会让 diff 器漏报内容变化。')"""),

    md("""## ✏️ 练习 2：严格的交集比较

实现 `strict_intersect(scores_a, tasks_a, scores_b, tasks_b)`：
在 `intersect_compare` 的基础上，**额外排除 `content_sha` 变过的样本**
（内容变了就不是同一道题）。返回
`{'n_common', 'n_excluded_content_change', 'a', 'b', 'delta'}`。"""),

    code("""def strict_intersect(scores_a, tasks_a, scores_b, tasks_b):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
si = strict_intersect(SCORES_V1, V1, SCORES_V2, V2)
loose = intersect_compare(SCORES_V1, V1, SCORES_V2, V2)
print('宽松交集:', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in loose.items()})
print('严格交集:', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in si.items()})
assert si['n_excluded_content_change'] == 1, 'billing-003 内容变过，必须被排除'
assert si['n_common'] == loose['n_common'] - 1
assert abs(si['delta'] - (si['b'] - si['a'])) < 1e-12
print('✅ 练习 2 通过：billing-003 内容变过，虽然 ID 相同，但它已经不是同一道题了。')
print('   把它算进交集，就把「题变简单了」误记成了「模型变强了」。')"""),

    md("""## ✏️ 练习 3：抽样稳定性的量化

实现 `retention_curve(select_fn, tasks, growth_list, seed=0)`：
`select_fn(tasks, seed)` 返回被选中的 ID 集合。对每个「新增样本数」，
返回 `(新增数, 原始入选样本的保留比例)`——即
`|原始入选 ∩ 扩后入选| / |原始入选|`。

**这个量才是 smoke 子集真正需要的稳定性**：不是「样本数不变」，
而是「原来入选的那些还在不在」。"""),

    code("""def retention_curve(select_fn, tasks, growth_list, seed=0):
    # TODO：新增的样本用 make_task(f'y{i:04d}', ...) 生成
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
GROWTH = [10, 50, 200]
r_shuffle = retention_curve(lambda ts, sd: set(sample_shuffle(ts, 15, sd)), BIG, GROWTH)
r_topn = retention_curve(lambda ts, sd: set(sample_hash_topn(ts, 15, sd)), BIG, GROWTH)
r_rate = retention_curve(lambda ts, sd: set(sample_rate(ts, 0.33, sd)), BIG, GROWTH)
print(f"{'新增样本数':>12}{'打乱取前N':>13}{'hash取前N':>13}{'按比例选':>12}")
for (g, s1), (_, s2), (_, s3) in zip(r_shuffle, r_topn, r_rate):
    print(f'{g:>12}{s1:>13.0%}{s2:>13.0%}{s3:>12.0%}')
assert all(abs(s - 1.0) < 1e-12 for _, s in r_rate), '按比例选的保留率必须恒为 100%'
assert r_shuffle[-1][1] < 0.5 and r_topn[-1][1] < 0.5
print('✅ 练习 3 通过：两种「固定 N」的做法在任务集翻几倍后保留率都掉到一半以下，')
print('   而按比例选恒为 100%——因为每条样本的入选是独立判定的。')
print('   → CI 的 smoke 子集应当按比例选 + 分层保底，而不是固定 N。')"""),

    md("""## ✏️ 练习 4：spec 迁移的往返一致性

实现 `migration_roundtrip_ok(old_specs)`：对每个旧 spec 检查三条性质，
全部满足返回 True：① 迁移幂等 `migrate(migrate(s)) == migrate(s)`；
② 迁移后 `schema_version == SCHEMA_VERSION`；
③ 迁移不改变指纹语义——即 `fingerprint(s) == fingerprint(migrate(s))`。"""),

    code("""def migration_roundtrip_ok(old_specs):
    # TODO：返回 (是否全部通过, 失败的 spec 下标列表)
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
OLD_SPECS = [
    spec_old,
    {'name': 'x', 'dataset': 'qa', 'model': {'id': 'm2'}, 'schema_version': 2},
    {'name': 'y', 'dataset': {'id': 'qa', 'version': 'v2', 'sha': 'z'},
     'model': {'id': 'm3'}, 'schema_version': 3},
]
ok, failed = migration_roundtrip_ok(OLD_SPECS)
print('全部通过:', ok, '| 失败下标:', failed)
assert ok is True and failed == []

broken = [{'name': 'z', 'dataset': 'qa', 'model': {'id': 'm4'}}]     # 无 schema_version → v1
ok2, _ = migration_roundtrip_ok(broken)
assert ok2 is True, '缺 schema_version 应按 v1 处理并能正常迁移'
print('✅ 练习 4 通过：第 3 条（迁移不改变指纹）是最容易被忽略的——')
print('   它保证了「历史 spec 迁移到新格式后，仍然指向同一次运行」。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def dataset_health(tasks):
    ids = [t['task_id'] for t in tasks]
    dup_ids = sorted({i for i, c in Counter(ids).items() if c > 1})
    shas = [t['content_sha'] for t in tasks]
    dup_content = sorted({s for s, c in Counter(shas).items() if c > 1})
    stale = sorted({t['task_id'] for t in tasks if t['content_sha'] != content_sha(t)})
    return {'n': len(tasks), 'dup_ids': dup_ids, 'dup_content': dup_content,
            'stale_sha': stale,
            'ok': not (dup_ids or dup_content or stale)}"""),

    code("""# 练习 2 参考答案
def strict_intersect(scores_a, tasks_a, scores_b, tasks_b):
    a = {t['task_id']: t for t in tasks_a}
    b = {t['task_id']: t for t in tasks_b}
    common = set(a) & set(b)
    changed = {i for i in common if a[i]['content_sha'] != b[i]['content_sha']}
    usable = sorted(common - changed)
    va = [scores_a[i] for i in usable if i in scores_a]
    vb = [scores_b[i] for i in usable if i in scores_b]
    ma = sum(va) / len(va) if va else float('nan')
    mb = sum(vb) / len(vb) if vb else float('nan')
    return {'n_common': len(usable), 'n_excluded_content_change': len(changed),
            'a': ma, 'b': mb, 'delta': mb - ma}"""),

    code("""# 练习 3 参考答案
def retention_curve(select_fn, tasks, growth_list, seed=0):
    base = set(select_fn(tasks, seed))
    out = []
    for g in growth_list:
        grown = tasks + [make_task(f'y{i:04d}', f'q{i}', str(i), ['core']) for i in range(g)]
        cur = set(select_fn(grown, seed))
        out.append((g, len(base & cur) / len(base) if base else float('nan')))
    return out"""),

    code("""# 练习 4 参考答案
def migration_roundtrip_ok(old_specs):
    failed = []
    for i, s in enumerate(old_specs):
        m = migrate(s)
        if migrate(m) != m:
            failed.append(i); continue
        if m.get('schema_version') != SCHEMA_VERSION:
            failed.append(i); continue
        if fingerprint(s) != fingerprint(m):
            failed.append(i); continue
    return (len(failed) == 0, failed)"""),

    md("""---
## 🧪 真实工程胶囊：数据集目录与 CI 检查"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 目录结构（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
# dataset/qa-tasks/v1/{tasks.jsonl, datasheet.md, MANIFEST.json}
# dataset/qa-tasks/v2/{tasks.jsonl, datasheet.md, MANIFEST.json, CHANGELOG.md}
# dataset/subsets/smoke.json
# spec/demo-qa.json      ← 只引用 (id, version, sha)，不内联任务内容

# MANIFEST.json:
{ "id": "qa-tasks", "version": "v2", "sha": "7d2e…", "n": 512,
  "created": "2026-03-01", "frozen": true,
  "expected_score_range": [0.30, 0.55] }     # ← 讲解第 6 节：极便宜的健康检查

# ══════════════════════════════════════════════════════════════════
# B. CI 里必跑的四条数据集检查
# ══════════════════════════════════════════════════════════════════
def ci_dataset_checks(version_dir):
    tasks = load_jsonl(f"{version_dir}/tasks.jsonl")
    man = json.load(open(f"{version_dir}/MANIFEST.json"))
    # 1. 冻结版本不许被改
    if man.get("frozen"):
        assert stable_hash(tasks, 12) == man["sha"], "已冻结版本被修改了"
    # 2. 结构健康（练习 1）
    h = dataset_health(tasks)
    assert h["ok"], f"数据集结构有问题: {h}"
    # 3. 有 datasheet，且写了预期分数区间
    assert os.path.exists(f"{version_dir}/datasheet.md")
    assert "expected_score_range" in man
    # 4. 版本号与上一版的 diff 一致（讲解第 3 节）
    prev = load_prev_version(version_dir)
    if prev:
        assert man["version"] == suggest_version(prev["version"], dataset_diff(prev["tasks"], tasks))

# ══════════════════════════════════════════════════════════════════
# C. 跨版本比较：唯一正确的做法
# ══════════════════════════════════════════════════════════════════
# ✗ 直接比 v1 的分数和 v2 的分数
# ✓ strict_intersect(scores_v1, tasks_v1, scores_v2, tasks_v2)
#   并在报告里写明: "在 N 条共同且内容未变的样本上比较"
# 报告模板:
#   v1 (n=512): 41.2%    v2 (n=498): 44.7%    ← 不可直接比较
#   交集 (n=487, 排除 11 条内容变更): 41.0% → 43.1%   ← 真实提升 +2.1pp

# ══════════════════════════════════════════════════════════════════
# D. datasheet.md 的七个必答问题（讲解第 6 节）
# ══════════════════════════════════════════════════════════════════
# 1. 样本从哪来（污染风险）      2. 创建/采集时间（时间截断检验）
# 3. 谁标注的、规范是什么        4. 已知坏题清单与剔除理由
# 5. 不可能任务的比例            6. 判分器与它的 alpha/beta
# 7. **预期的合理分数区间**      ← 最便宜、最实用的一条
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| spec 是纯数据 | 换来可哈希、可 diff、可生成；prompt 的**哈希**必须进 spec | 全课 |
| 稳定 ID | ID 分配一次永不改；content_sha 用来检测变化，不当 ID | 数据集设计 |
| 版本语义 | 新增走次版本，修改/删除走主版本——因为分母变了 | 发布新版 |
| 交集重算 | 跨版本比较的唯一正确做法，且要排除内容变过的样本 | 报告 |
| 确定性抽样 | 固定 N 必然不稳；smoke 子集要**按比例选 + 分层保底** | smoke 子集 |
| schema 迁移 | 只增字段、默认值保持旧行为、**指纹在规范化之后算** | 长期演化 |
| datasheet | 七个必答问题，其中「预期分数区间」最便宜最实用 | 每个数据集版本 |

下一模块：**02 · Runner 工程**——并发、限流、重试、超时、缓存、断点续跑、预算熔断，
以及那个「改了 prompt 却读到旧结果」的隐蔽 bug 到底怎么防。""")
]
