# -*- coding: utf-8 -*-
"""C70 模块 05 · 索引运维。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 01（摄取契约与 provenance）与 03（过滤前置）；"
                 "C68 模块 05（线上监控与漂移）读过更好"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_index_ops.ipynb'
                       '（三种腐烂 / 新鲜度公式与模拟对拍 / '
                       '新旧 embedding 混用的相似度失真 / 影子索引与原子切换 / '
                       '切换中途的混版本状态 / 派生资产（摘要、三元组）的静默过期 / '
                       '多租户的两种隔离 / 检索层监控四项与门禁）'),
    ("核心参考", "C68 模块 05（PSI/KS、漂移、数据闭环——本课直接复用不重推）· "
                 "C68 模块 01（版本语义与交集重算）· "
                 "本课模块 01（摄取契约）· 模块 03（过滤前置）· 模块 04（图的腐烂）· "
                 "C12 / C45（删除的合规要求）· "
                 "Kleppmann, <em>Designing Data-Intensive Applications</em>（双写与切换）"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("rot", "索引会腐烂：三种腐烂，三种修法", "".join([
        P("前面四个模块的产物都是<strong>一次性的决策</strong>："
          "解析器选定了、分块参数解出来了、查询流水线上线了。"
          "<strong>而索引是有状态的——它从建成的那一刻起就开始与现实脱节。</strong>"),
        TABLE(["腐烂类型", "什么变了", "症状", "修法", "能不能局部修"], [
            ["<strong>内容腐烂</strong>", "源文档改了 / 删了",
             "答出旧政策；答出已删除内容",
             "增量索引（第 2 节）",
             "<strong>能</strong>——按 <code>doc_id</code> 定位"],
            ["<strong>结构腐烂</strong>", "分块参数 / 解析器换了",
             "同一份内容以两种粒度共存，top-k 被自己造的近重复占满",
             "全量重建 + 原子切换（第 5 节）",
             "<strong>不能</strong>——新旧块混在一个索引里就是错的"],
            ["<strong>模型腐烂</strong>", "embedding 模型升级",
             "<strong>相似度失去意义</strong>（第 4 节量这件事）",
             "全量重建 + 原子切换",
             "<strong>绝对不能</strong>——两个向量空间之间的距离没有含义"],
        ]),
        DUAL(
            "最后一列是这一节的重点。"
            "<strong>内容腐烂可以一份份修，而结构腐烂与模型腐烂必须整体换。</strong>"
            "<em>把它们当成同一类问题处理（「那就慢慢迁移吧，先写新格式，旧的以后再说」）"
            "会产生一个既不是旧的也不是新的索引</em>，"
            "<strong>而这个中间状态的行为是无法解释的</strong>——"
            "违反了 C68 模块 00 的第一条性质（差异可解释）。",
            "为什么模型腐烂「绝对不能」局部修？因为"
            "<span class=\"term\">向量空间之间没有对齐关系</span>。"
            "两个不同模型（甚至同一模型的两个版本）产生的向量，"
            "<strong>其内积不是相似度，而是一个没有含义的数</strong>。"
            "<em>而它是一个「看起来很正常」的数</em>——"
            "在 $[-1, 1]$ 之间，有分布，能排序。"
            "<strong>所以混用不会报错，只会安静地给出错误的排序</strong>，"
            "这是本模块最危险的一个失败。第 4 节把失真量出来。",
        ),
        CALLOUT("danger", "有一个部署惯例会直接触发模型腐烂："
                          "<strong>把 embedding 模型名写成 <code>latest</code> 或不写版本。</strong>"
                          "<em>服务方更新模型后，新写入的向量与索引里的旧向量属于不同空间，"
                          "而系统一切正常、没有任何报错。</em>"
                          "<strong>模型 ID 与版本必须钉死，并且写进索引的元数据里</strong>——"
                          "这与 C69 模块 02「钉内容哈希而不是版本号」是同一类纪律。"),
    ])),

    # ============================================================== 2
    ("incremental", "增量索引：三种语义，其中删除最容易做错", "".join([
        P("模块 01 已经给出了摄取契约。这一节把它扩展到<strong>持续运行</strong>的场景。"),
        ASCII("""
   增量索引的三种操作

   ┌──────────┬─────────────────────────┬──────────────────────────┐
   │ 操作     │ 正确实现                 │ 常见错误                  │
   ├──────────┼─────────────────────────┼──────────────────────────┤
   │ 新增     │ upsert，主键 (doc,v,i)   │ append → 重复摄取变两份    │
   │ 更新     │ **先删该 doc 全部旧块**   │ 只写新块 → 新旧块共存      │
   │          │ 再写新块                 │  （旧块永远不会被访问到     │
   │          │                         │   ……除非它比新块更像查询）  │
   │ 删除     │ 删块 + 写 tombstone      │ 只从源库删 → 索引里还在     │
   │          │ + **断言删除数 == 预期**  │ 不断言 → 「删了 0 条」不报错 │
   └──────────┴─────────────────────────┴──────────────────────────┘
"""),
        DUAL(
            "「更新时只写新块」这个错误值得展开，因为它的症状很迷惑："
            "<strong>大部分查询表现正常</strong>（新块通常更像查询，排在前面），"
            "<em>但偶尔会返回旧内容</em>——"
            "而「偶尔」取决于查询措辞与旧块的相似度。"
            "<strong>这类间歇性错误极难定位，因为它不可复现。</strong>",
            "删除则有一个额外的<strong>可验证性</strong>要求："
            "<em>删除操作必须返回删掉了几条，调用方必须断言这个数</em>。"
            "<strong>「执行了删除但删掉 0 条」是一个必须能被发现的失败</strong>——"
            "它的成因通常是过滤条件写错（<code>doc_id</code> 大小写、"
            "路径归一化差异），"
            "而没有断言时它看起来是一次成功的删除。"
            "<em>这在合规语境下是实质性的：用户被告知数据已删除，而它还在被检索。</em>",
        ),
        H3("删除的三层"),
        OL([
            "<strong>索引里的向量与块</strong>——必须删。这是唯一决定「还能不能被检索到」的一层。",
            "<strong>派生资产</strong>：摘要、三元组、实体倒排、缓存（第 7 节）。"
            "<em>它们不删的话，内容会从另一条路回来。</em>",
            "<strong>日志与评测集</strong>——<em>这一层通常不能简单删</em>"
            "（会破坏历史可比性），"
            "<strong>正确做法是标记而不是物理删除，并在聚合时排除</strong>"
            "（与 C68 模块 01 的「坏题三条处理路径」同构）。",
        ]),
    ])),

    # ============================================================== 3
    ("freshness", "新鲜度：过期答案率是可以算的", "".join([
        P("「索引多久重建一次」通常是拍出来的。"
          "<strong>它可以从两个可测的量算出来：滞后时间与变更率。</strong>"),
        MATH(r"P(\text{某文档已过期}) = 1 - (1-p)^{L} \approx pL \quad (pL \ll 1)"),
        DUAL(
            "$p$ 是<strong>单篇文档单位时间的变更概率</strong>（可以从源库的修改时间统计出来），"
            "$L$ 是<strong>索引滞后的时间</strong>（单位与 $p$ 一致）。"
            "<em>$p = 1\\%/\\text{天}$、$L = 7$ 天时，约 6.8% 的文档在索引里是旧的。</em>",
            "但真正要报的不是这个数，而是<strong>它对答案的影响</strong>："
            "$$P(\\text{答案过期}) = \\sum_d \\pi(d) \\cdot \\left(1 - (1-p_d)^{L}\\right)$$"
            "其中 $\\pi(d)$ 是文档 $d$ 被查中的概率。"
            "<strong>关键洞察：$\\pi$ 与 $p$ 通常<em>正相关</em></strong>——"
            "<em>热门文档也是改得最频繁的文档</em>（政策、价格、排班）。"
            "所以按「文档均匀」估出来的过期率会<strong>系统性偏低</strong>。"
            "notebook 第 3 节把两种估法的差距量出来。",
        ),
        TABLE(["变更率 p", "滞后 L", "过期文档比例", "该怎么办"], [
            ["1%/天", "7 天", "6.8%", "可接受（多数内部文档库）"],
            ["1%/天", "30 天", "26%", "<strong>太高</strong>——缩短到周级"],
            ["5%/天", "7 天", "30%", "<strong>太高</strong>——需要事件驱动增量"],
            ["5%/天", "1 天", "5%", "可接受"],
            ["20%/天", "1 天", "20%", "<em>批量重建救不了</em>——必须近实时增量"],
        ]),
        CALLOUT("intuition", "这张表给出的工程结论很直接："
                             "<strong>先测 $p$，再定重建周期，而不是反过来。</strong>"
                             "<em>而 $p$ 几乎总是能从源库的 <code>updated_at</code> 免费算出来</em>——"
                             "它是本模块成本最低、收益最高的一次测量。"),
        H3("两种更新策略"),
        UL([
            "<strong>批量重建</strong>：定时全量或增量扫描。"
            "<em>简单、可预测；滞后等于周期的一半（平均）到一个周期（最坏）。</em>",
            "<strong>事件驱动</strong>：源库变更触发单篇重索引。"
            "<em>滞后可以做到分钟级，但需要一个可靠的变更流</em>，"
            "<strong>而且必须有一条定时的对账任务</strong>——"
            "<em>事件会丢，而丢了的那一篇会永久过期</em>。"
            "对账做法：比对源库与索引里的 <code>(doc_id, content_sha)</code> 集合。",
        ]),
    ])),

    # ============================================================== 4
    ("embedding-migration", "换 embedding 模型：不可混用的全量迁移", "".join([
        P("这是本模块最重要的一节，"
          "<strong>因为它的错误做法不会报错</strong>。"),
        ASCII("""
   ❌ 渐进迁移（错）
      新写入的块用新模型，旧块保持旧模型，同一个索引
      → 查询用哪个模型编码？
        用新模型 → 与旧块的内积没有含义
        用旧模型 → 与新块的内积没有含义
      → 无论怎么选，**一半的索引在给出无意义的分数**
      → 而这些分数长得很正常：在 [-1,1] 之间，有分布，能排序

   ✅ 双索引 + 原子切换（对）
      1. 建影子索引（新模型），与主索引并存
      2. 一致性校验：同一批查询在两个索引上的结果对比
      3. 原子切换：改一个指针（别名 / 配置项 / DNS）
      4. 保留旧索引 N 天，随时可回滚
"""),
        DUAL(
            "为什么内积「没有含义」而不只是「不太准」？"
            "因为<strong>两个模型的向量空间的基是无关的</strong>。"
            "<em>模型 A 的第 17 维编码的东西与模型 B 的第 17 维毫无关系</em>，"
            "所以逐维相乘再求和这个操作，"
            "<strong>在数学上是一个随机投影的内积</strong>——它的期望是 0，方差取决于维度。",
            "notebook 第 4 节用两个「模型」（不同的哈希盐）把这件事量出来："
            "<strong>同一段文本在两个空间里的向量，内积接近 0</strong>；"
            "而「一段文本与它自己的改写」在<em>同一个空间里</em>内积很高。"
            "<em>于是混用索引时，跨空间的那一半块的分数会系统性地偏低</em>——"
            "<strong>它们不是排在后面，而是几乎永远排在后面</strong>，"
            "等于那部分索引对检索不可见（而存储与账单照付）。",
        ),
        H3("一致性校验该比什么"),
        P("影子索引建好后不能直接切。"
          "<strong>但也不能要求「结果完全一致」——那等于要求新模型没有任何改进。</strong>"
          "正确的校验是三条："),
        OL([
            "<strong>覆盖率</strong>：两个索引的块数、doc 数、向量数必须<em>完全相等</em>。"
            "<strong>这是确定性检查，不相等就是漏了内容，直接阻断。</strong>",
            "<strong>离线指标不降</strong>：在同一套评测集上跑 recall / fact-recall，"
            "<em>按 C68 模块 04 的方法从方差推阈值</em>，不要拍一个百分比。",
            "<strong>结果重叠率作为观测量而不是门禁</strong>："
            "报 top-k 的 Jaccard，<em>但不设阈值</em>——"
            "<strong>它低可能意味着新模型更好，也可能意味着更差，这个数本身不能判定方向。</strong>"
            "<em>它的用途是：如果重叠率是 1.0，说明你其实没换成新模型（配置没生效）。</em>",
        ]),
        CALLOUT("warn", "第 3 条的最后一句是一个真实的、便宜的自检："
                        "<strong>迁移后如果结果一点没变，先怀疑配置没生效，"
                        "而不是高兴「新模型很稳」。</strong>"),
    ])),

    # ============================================================== 5
    ("switch", "双写与原子切换：中途状态必须不可达", "".join([
        P("切换的正确性只有一个要求："
          "<strong>任何一个请求看到的，要么是完整的旧索引，要么是完整的新索引，"
          "不存在第三种状态。</strong>"),
        ASCII("""
   时间线

   t0  主索引=A(旧模型)          影子=B(新模型，空)
   t1  主索引=A                  影子=B  ← 全量回填中
   t2  主索引=A                  影子=B  ← 回填完成，跑一致性校验
   t3  主索引=B                  旧=A    ← **原子切换：改一个指针**
   t4  主索引=B                  旧=A    ← 观察期（保留 N 天）
   t5  主索引=B                             ← 删除 A

   回填期间的新增/更新怎么办？
     **双写**：写 A 也写 B。B 用新模型编码。
     漏了双写的后果：切换后 B 缺了回填期间的所有变更，
     而这个缺口**不会报错**——只是有些内容检索不到。
"""),
        DUAL(
            "「原子」在实现上通常就是一个指针："
            "<em>向量库的 collection alias、配置中心的一个键、"
            "或者一个 <code>ACTIVE_INDEX</code> 环境变量</em>。"
            "<strong>关键是它必须是单一来源，且读取方每次请求都重新读它</strong>——"
            "<em>进程启动时读一次并缓存的实现，会让切换后旧进程继续用旧索引，"
            "于是同一时刻不同实例返回不同结果</em>。",
            "回滚同样重要：<strong>切换后要保留旧索引 N 天</strong>，"
            "$N$ 至少覆盖「一个完整的业务周期 + 发现问题需要的时间」。"
            "<em>而回滚必须是同一个指针的反向操作</em>——"
            "<strong>如果回滚需要重建索引，那就等于没有回滚。</strong>"
            "notebook 第 5 节把切换与回滚都实现了，"
            "并演示<em>中途状态（混版本）下的错误行为</em>。",
        ),
        H3("切换清单（六项，缺一项都可能出事）"),
        UL([
            "回填期间<strong>双写</strong>，且双写失败要报警而不是静默丢弃",
            "回填完成后<strong>覆盖率完全相等</strong>（确定性检查）",
            "<strong>离线指标不降</strong>（统计检查，阈值从方差推）",
            "<strong>切换是改一个指针</strong>，读取方每次请求重新读",
            "<strong>旧索引保留 N 天</strong>，回滚是同一指针的反向操作",
            "<strong>切换前后各跑一次监控基线</strong>（第 8 节的四项），"
            "<em>否则切换后指标变差时你分不清是新模型的问题还是切换的问题</em>",
        ]),
    ])),

    # ============================================================== 6
    ("tenant", "多租户：两种隔离，选错了是安全问题", "".join([
        P("模块 03 说过「过滤必须前置」。"
          "这一节讨论更基本的一层：<strong>要不要给每个租户单独的索引。</strong>"),
        TABLE(["方案", "隔离强度", "成本", "什么时候用"], [
            ["<strong>元数据过滤</strong>（共享索引）",
             "<em>取决于每一次调用都带对了过滤条件</em>",
             "低（一个索引）",
             "租户多、每个租户数据少；<strong>且过滤是不可绕过的默认值</strong>"],
            ["<strong>独立索引 / 独立 collection</strong>",
             "<strong>结构性隔离</strong>——错误的租户根本连不到那个索引",
             "高（N 个索引的元数据与内存开销）",
             "租户少而大；或<strong>合规要求物理隔离</strong>"],
            ["<strong>混合</strong>：大租户独立、小租户共享",
             "分档",
             "中",
             "最常见的落地形态；<em>但要注意「小租户升级成大租户」时的迁移</em>"],
        ]),
        DUAL(
            "选择的判据不是成本，而是<strong>「一次漏写的距离」</strong>："
            "<em>共享索引 + 可选的过滤参数 → 一行漏写就是一次跨租户泄漏；"
            "共享索引 + 必填的过滤参数 → 漏写会报错；"
            "独立索引 → 连错索引才可能出问题，而那是一个更显眼的错误。</em>"
            "<strong>这是一个纵深防御的排序，而不是三个等价选项。</strong>",
            "无论选哪个，有两条必须做："
            "<strong>① 租户维度的监控要分租户看</strong>——"
            "<em>「某个租户的零结果率突然 100%」在总体指标里完全看不见</em>；"
            "<strong>② 删除与新鲜度也是按租户的</strong>——"
            "一个租户要求删除数据时，"
            "<em>你需要能枚举「属于这个租户的全部块」</em>，"
            "而这依赖模块 01 把 <code>tenant</code> 写进了每个块的元数据。",
        ),
        CALLOUT("danger", "一个具体的、常见的泄漏路径："
                          "<strong>缓存。</strong>"
                          "<em>查询侧缓存（模块 03 第 7 节）的键如果不含 "
                          "<code>tenant</code>，那么租户 A 的结果会被租户 B 的相同查询命中。</em>"
                          "<strong>缓存键必须含租户标识——这一条与检索侧的过滤同等重要，"
                          "而它更容易被忘。</strong>"),
    ])),

    # ============================================================== 7
    ("derived", "派生资产会静默过期", "".join([
        P("索引里不只有块的向量。"
          "<strong>凡是从文档「算出来」的东西，都必须跟着文档版本失效。</strong>"),
        TABLE(["派生资产", "来自哪个模块", "不失效的后果"], [
            ["<strong>父块 / 摘要索引</strong>", "模块 02 第 6 节",
             "答案引用了新版本的子块，而<em>喂给模型的父块是旧的</em>"],
            ["<strong>三元组 / 实体倒排</strong>", "模块 04 第 5 节",
             "图里还有一条已经不存在的关系；<strong>而图检索答出来的东西「不在任何块里」，"
             "所以无法通过引用核查发现</strong>"],
            ["<strong>查询侧缓存</strong>", "模块 03 第 7 节",
             "文档更新了但缓存里是旧结果"],
            ["<strong>同义词表 / 别名表</strong>", "模块 03 第 3 节",
             "指向了已删除的文档用词"],
            ["<strong>离线评测集的 gold chunk id</strong>", "本课全程",
             "<strong>评测集悄悄失效</strong>——"
             "<em>gold 块被重新分块后 id 变了，于是所有题的 recall 都是 0，"
             "而这看起来像一次严重的效果退化</em>"],
        ]),
        DUAL(
            "统一的做法只有一条："
            "<strong>每个派生资产都带上它依赖的 <code>(doc_id, version)</code> 或"
            "<code>content_sha</code>，并在读取时校验。</strong>"
            "<em>不匹配就当缓存未命中（重新计算）或报警，而不是照用。</em>",
            "最后一行值得单独说，因为它会造成一次<strong>假的效果事故</strong>："
            "换了分块方案后，评测集里记录的 <code>gold_chunk_id</code> 全部失效，"
            "<em>recall 掉到 0，看起来像新分块方案彻底失败</em>。"
            "<strong>正确做法是评测集记录「答案文本 + doc_id」而不是 chunk_id</strong>——"
            "<em>本课全程用「答案字符串是否在召回的块里」判定，正是为了避免这个问题</em>。"
            "这与 C68 模块 01「不要用内容哈希当 ID」是同一类教训："
            "<strong>不要把标注绑在会变的东西上。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("monitoring", "检索层的监控四项 + 门禁", "".join([
        P("C68 模块 05 讲了线上监控的一般框架（PSI/KS、漂移、闭环）。"
          "这一节只给<strong>检索层特有的四个指标</strong>，"
          "它们都不需要真值。"),
        TABLE(["指标", "怎么算", "它能抓到什么", "分租户看吗"], [
            ["<strong>零结果率</strong>",
             "候选集为空或 top-1 分数低于阈值的请求占比",
             "过滤条件写错（模块 03 第 5 节）、索引被清空、租户配置错",
             "<strong>必须</strong>"],
            ["<strong>top-1 分数分布</strong>",
             "分位数（P10/P50/P90）",
             "<strong>embedding 模型被换掉了 / 混用了两个空间</strong>（<em>左尾变重，中位数可能不动</em>）、索引损坏",
             "建议"],
            ["<strong>引用率</strong>",
             "生成的答案里带引用的比例 / 引用被点击的比例",
             "召回质量下降（模型找不到可引用的依据）",
             "建议"],
            ["<strong>新鲜度滞后</strong>",
             "$\\max_d (\\text{now} - \\text{indexed\\_at}_d)$ 与 P99",
             "增量任务挂了、事件流丢消息（第 3 节的对账）",
             "<strong>必须</strong>"],
        ]),
        DUAL(
            "四个指标里<strong>「top-1 分数分布」最容易被忽略，但它是模型腐烂的唯一线上信号</strong>。"
            "<em>混用了两个 embedding 空间时，跨空间那部分块的分数会被压到接近 0，"
            "于是分布的左尾变重——而中位数可能一点不动</em>——"
            "<strong>而其它三个指标都可能完全正常。</strong>",
            "门禁按 C68 模块 04 的分级："
            "<strong>确定性项阻断</strong>（新旧索引的块数不等、"
            "任一租户的零结果率 100%、新鲜度滞后超过 SLA），"
            "<strong>统计项报警</strong>（分数分布的 PSI、引用率的变化）。"
            "<em>把统计项设成阻断是「门禁被关掉」这一结局的起点。</em>",
        ),
        H3("一张运维卡"),
        ASCII("""
   索引运维卡（每次重建/切换后生成）

   index_id:        kb-v7-e5large-2026w35
   embedding:       e5-large@2026-06-01   ← **钉死版本，不写 latest**
   chunker:         structure_aware s=400 o=62
   fingerprint:     3f9a71c2              ← 参数变了指纹就变（C68-01）
   docs / chunks:   12,480 / 51,203       ← 与旧索引必须完全相等
   built_at:        2026-08-31T04:12Z
   freshness_p99:   3.4 小时              ← SLA 6 小时 ✓
   change_rate p:   0.9%/天（从源库 updated_at 统计）
   → 预期过期文档比例 = 1-(1-0.009)^(3.4/24) ≈ 0.13%  ✓

   离线: fact-recall 0.83 → 0.86 (+3pp, 阈值 ±1.8pp) ✓
   重叠: top5 Jaccard 0.71  ← **观测量，不设门禁**
   零结果率（分租户最大）: 0.4%  ✓
   top1 分数 P10/P50: 0.31/0.62 → 0.30/0.61   PSI 0.03  ✓  ← 报分位数

   回滚: 指针 kb-active → kb-v6-...，旧索引保留至 2026-09-14
"""),
        CALLOUT("intuition", "这张卡最重要的一行是最后一行："
                             "<strong>如果它写不出来（回滚需要重建索引），"
                             "那么这次切换是不可回滚的，不该上线。</strong>"),
    ])),

    # ============================================================== 9
    ("capacity", "索引的容量与成本：三个乘数", "".join([
        P("索引运维的最后一件事是账。"
          "<strong>向量索引的成本有三个乘数，而它们都容易被低估。</strong>"),
        MATH(r"\text{cost} \approx N_{\text{doc}} \times \frac{L_{\text{doc}}}{s-o} "
             r"\times \big(d \cdot b + m_{\text{meta}}\big) \times (1 + r_{\text{shadow}})"),
        TABLE(["乘数", "它是什么", "容易被低估的原因"], [
            ["<strong>$\\frac{L_{\\text{doc}}}{s-o}$</strong>（每文档的块数）",
             "由分块参数决定",
             "<strong>重叠是分母里的减项</strong>：$s=400, o=62$ 时块数是无重叠的 1.18 倍，"
             "而 $s=100,o=59$ 时是 2.44 倍（模块 02 第 3 节）"],
            ["<strong>$d \\cdot b$</strong>（每向量的字节数）",
             "维度 × 每维字节",
             "<em>换一个「更好的」嵌入模型经常同时把维度从 768 提到 1024–3072</em>，"
             "<strong>而这是一个 1.3–4 倍的存储与内存乘数</strong>，"
             "还会同时抬高检索延迟"],
            ["<strong>$1 + r_{\text{shadow}}$</strong>（影子索引期间）",
             "迁移期间两份索引并存",
             "<strong>迁移期间容量翻倍</strong>，"
             "而「保留旧索引 N 天」意味着这个翻倍要持续 N 天（第 5 节）"],
        ]),
        DUAL(
            "第二行值得展开，因为它是一个常见的、被低估的决策。"
            "<strong>「升级到更强的嵌入模型」在账面上不只是一次重建</strong>："
            "<em>维度变大 → 向量存储与内存按比例增长 → 检索延迟增长 → "
            "如果用了量化（C11 模块 02 的 PQ），量化参数也要重调</em>。"
            "<strong>所以这个决策该先在离线集上量出「fact-recall 提升多少」，"
            "再和这一串成本一起看。</strong>",
            "还有一项不在公式里的成本：<strong>元数据的基数</strong>。"
            "<em>本课要求每个块带 "
            "<code>doc_id / version / chunk_index / start / end / section_path / "
            "tenant / effective_date / element_type</code></em>——"
            "<strong>这些字段的存储通常与向量本身同量级</strong>，"
            "而且它们上面的索引（用于前置过滤）还要额外开销。"
            "<em>但它们不是可以省的：模块 01 第 5 节已经说过，"
            "缺任一个都会让某个运维操作变得不可能。</em>"
            "<strong>正确的做法不是砍字段，而是把它们放在合适的存储里</strong>——"
            "过滤要用的进向量库的 metadata，只用于展示的放外部表按需取。",
        ),
        CALLOUT("intuition", "一个能立刻用上的估算："
                             "<strong>先算「每文档块数 × 向量字节数」，再乘 2（影子期）</strong>。"
                             "<em>如果这个数已经超出预算，那么在选嵌入模型之前，"
                             "先回去看模块 02 的成本倍数——"
                             "把重叠从「块长的 20%」改成「最长答案 −1」通常能省掉一大截</em>。"),
    ])),
]

NB = [
    md("""# 05 · 索引运维（腐烂 / 增量 / 新鲜度 / 模型迁移 / 切换 / 多租户 / 派生资产 / 监控）

目标：把「索引会腐烂」这件事变成**可算的公式 + 可执行的切换流程**。

本 notebook 你会亲手实现：
1. **三种腐烂** —— 内容 / 结构 / 模型，以及为什么后两种不能局部修
2. **增量索引三种语义** —— 「更新时只写新块」这个错误的间歇性症状
3. **新鲜度公式** —— $1-(1-p)^L$ 与模拟对拍，以及「热门文档改得更勤」造成的低估
4. **新旧 embedding 混用** —— 跨空间内积接近 0，而它看起来完全正常
5. **影子索引与原子切换** —— 含双写、一致性校验、回滚、以及中途混版本状态
6. **多租户的两种隔离** —— 以及缓存键这条容易被忘的泄漏路径
7. **派生资产的静默过期** —— 尤其是评测集 gold id 造成的「假事故」
8. **检索层监控四项 + 运维卡门禁**

> 心智模型：**索引是有状态的、会腐烂的。
> 内容腐烂可以一份份修；结构腐烂与模型腐烂必须整体换。**"""),

    md("""## 0 · 环境：两个「embedding 模型」

用不同的哈希盐模拟两个模型。它们各自内部自洽（同义句相似度高），
**但彼此之间的向量不可比**——第 4 节就是量这件事。"""),

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

def make_embedder(model_id, dim=DIM):
    \"\"\"不同 model_id → 不同的哈希盐 → **不同的向量空间**。

    这正是两个真实 embedding 模型之间的关系：各自内部自洽，
    但第 17 维编码的东西毫无关系，所以跨空间的内积没有含义。\"\"\"
    def embed(text):
        v = np.zeros(dim)
        for tok in tokenize(text):
            h = hashlib.md5((model_id + '|' + tok).encode()).hexdigest()
            v[int(h, 16) % dim] += 1.0
        n = np.linalg.norm(v)
        return v / n if n > 0 else v
    embed.model_id = model_id
    return embed

EMB_OLD = make_embedder('e5-base@2025-11-01')
EMB_NEW = make_embedder('e5-large@2026-06-01')

def cos(a, b):
    return float(np.dot(a, b))

# 各自内部自洽
a1, a2 = '餐饮报销的单次上限是 200 元。', '餐饮报销单次最多 200 元。'
for name, E in [('旧模型', EMB_OLD), ('新模型', EMB_NEW)]:
    print(f'{name}: 同义句相似度 {cos(E(a1), E(a2)):.3f}')
assert cos(EMB_OLD(a1), EMB_OLD(a2)) > 0.5
assert cos(EMB_NEW(a1), EMB_NEW(a2)) > 0.5
print('\\n✅ 两个「模型」各自内部自洽。第 4 节会看它们之间是什么关系。')"""),

    md("""## 1 · 语料与一个可运维的索引

`Index` 的关键是**每个块都带 provenance 与 indexed_at**——
模块 01 埋下的字段在这里全部被用到。"""),

    code("""SOURCE = {
    # doc_id -> dict(text, version, tenant, updated_at)
    'hr-01':  dict(text='正式员工每年享有 15 天带薪年假。', version=1,
                   tenant='acme', updated_at=0),
    'fin-01': dict(text='餐饮报销的单次上限是 200 元。', version=1,
                   tenant='acme', updated_at=0),
    'fin-02': dict(text='差旅报销的单次上限是 3000 元。', version=1,
                   tenant='acme', updated_at=0),
    'it-01':  dict(text='笔记本电脑的更换周期是 36 个月。', version=1,
                   tenant='acme', updated_at=0),
    'sec-01': dict(text='密码长度不得少于 12 位。', version=1,
                   tenant='acme', updated_at=0),
    'gx-01':  dict(text='门禁卡遗失需到前台补办。', version=1,
                   tenant='globex', updated_at=0),
    'gx-02':  dict(text='访客需由员工陪同进入。', version=1,
                   tenant='globex', updated_at=0),
}

class Index:
    def __init__(self, index_id, embedder):
        self.index_id = index_id
        self.embed = embedder
        self.blocks = {}          # (doc_id, version) -> dict(text, vec, tenant, indexed_at)
        self.tombstones = {}

    # ---- 写 ----
    def upsert(self, doc_id, doc, now=0):
        \"\"\"正确实现：先删该 doc 的全部旧版本，再写新版本。\"\"\"
        if doc_id in self.tombstones:
            return dict(written=0, deleted=0, rejected=1)
        old = [k for k in self.blocks if k[0] == doc_id]
        for k in old:
            del self.blocks[k]
        self.blocks[(doc_id, doc['version'])] = dict(
            text=doc['text'], vec=self.embed(doc['text']),
            tenant=doc['tenant'], indexed_at=now,
            embed_model=self.embed.model_id)
        return dict(written=1, deleted=len(old), rejected=0)

    def upsert_wrong(self, doc_id, doc, now=0):
        \"\"\"错误实现：只写新版本，不删旧版本。\"\"\"
        self.blocks[(doc_id, doc['version'])] = dict(
            text=doc['text'], vec=self.embed(doc['text']),
            tenant=doc['tenant'], indexed_at=now,
            embed_model=self.embed.model_id)
        return dict(written=1, deleted=0, rejected=0)

    def delete(self, doc_id, reason='user_request'):
        ks = [k for k in self.blocks if k[0] == doc_id]
        for k in ks:
            del self.blocks[k]
        self.tombstones[doc_id] = reason
        return len(ks)

    # ---- 读 ----
    def search(self, query, k=3, tenant=None):
        q = self.embed(query)
        rows = [(key, b, cos(b['vec'], q)) for key, b in self.blocks.items()
                if tenant is None or b['tenant'] == tenant]
        rows.sort(key=lambda r: -r[2])
        return [(key, b['text'], sc) for key, b, sc in rows[:k]]

    def stats(self):
        return dict(index_id=self.index_id, docs=len({k[0] for k in self.blocks}),
                    blocks=len(self.blocks),
                    models={b['embed_model'] for b in self.blocks.values()})

MAIN = Index('kb-v6-e5base', EMB_OLD)
for did, doc in SOURCE.items():
    MAIN.upsert(did, doc, now=0)
print(MAIN.stats())
print(MAIN.search('餐饮报销上限', k=2, tenant='acme'))
assert MAIN.stats()['blocks'] == len(SOURCE)
print('\\n✅ 主索引就位：7 个文档，单一 embedding 模型。')"""),

    md("""## 2 · 增量索引：「更新时只写新块」的间歇性症状

这个错误的可怕之处：**大部分查询正常，偶尔返回旧内容**，而且不可复现。"""),

    code("""def scenario(upsert_fn, label):
    idx = Index('tmp', EMB_OLD)
    for did, doc in SOURCE.items():
        idx.upsert(did, doc, now=0)
    # fin-01 改了：200 元 → 260 元
    new_doc = dict(SOURCE['fin-01']); new_doc['text'] = '餐饮报销的单次上限是 260 元。'
    new_doc['version'] = 2
    st = upsert_fn(idx, 'fin-01', new_doc, 1)
    versions = sorted(k[1] for k in idx.blocks if k[0] == 'fin-01')
    print(f'{label:<16} 写 {st["written"]} 删 {st["deleted"]} | '
          f'fin-01 在索引里的版本: {versions}')
    return idx

idx_ok = scenario(lambda i, d, doc, n: i.upsert(d, doc, n), '正确（先删后写）')
idx_bad = scenario(lambda i, d, doc, n: i.upsert_wrong(d, doc, n), '错误（只写新块）')

# 三个不同措辞的查询，看错误实现的表现
QUERIES = ['餐饮报销的单次上限是多少', '吃饭能报多少钱', '餐饮报销 200']
print(f"\\n{'查询':<22}{'正确实现 top1':<22}{'错误实现 top1':<22}")
stale_hits = 0
for q in QUERIES:
    t_ok = idx_ok.search(q, k=1, tenant='acme')[0][1]
    t_bad = idx_bad.search(q, k=1, tenant='acme')[0][1]
    stale_hits += ('200 元' in t_bad)
    print(f'{q:<22}{t_ok:<22}{t_bad:<22}')

assert all('260' in idx_ok.search(q, k=1, tenant='acme')[0][1] or
           '餐饮' not in idx_ok.search(q, k=1, tenant='acme')[0][1] for q in QUERIES)
assert stale_hits >= 1, '错误实现在某些措辞下会返回旧内容'
assert stale_hits < len(QUERIES), '而在另一些措辞下表现正常——这才是它难定位的原因'
print(f'\\n✅ 错误实现在 {stale_hits}/{len(QUERIES)} 个措辞下返回了旧值「200 元」。')
print('   注意它不是「总是错」也不是「总是对」——**它取决于查询措辞与旧块的相似度**。')
print('   这类间歇性错误极难定位，因为它不可复现。')
print('   而正确实现（先删该 doc 全部旧版本，再写新版本）从结构上排除了它。')"""),

    code("""# --- 删除必须可验证 ---
n = MAIN.delete('gx-01')
print(f'删除 gx-01 → 删掉 {n} 个块')
assert n == 1, '删除必须返回删掉的条数，调用方必须断言它'
assert MAIN.search('门禁卡遗失', k=3, tenant='globex') == [] or \\
       all('门禁卡' not in t for _, t, _ in MAIN.search('门禁卡遗失', k=3, tenant='globex'))

# 「删了 0 条」必须能被发现
n2 = MAIN.delete('doc-id-typo')
print(f'删除一个不存在的 doc_id → 删掉 {n2} 个块')
assert n2 == 0
try:
    assert n2 > 0, '删除操作没有删掉任何块——很可能 doc_id 写错了'
    raise SystemExit('不该到这里')
except AssertionError as e:
    print(f'✅ 断言捕获: {e}')

# tombstone 阻止被删文档被全量同步灌回
st = MAIN.upsert('gx-01', SOURCE['gx-01'], now=2)
print(f'全量同步重灌 gx-01 → {st}')
assert st['rejected'] == 1, 'tombstone 必须阻止重灌'
print('\\n✅ 删除的三条：删块 + 写 tombstone + **断言删除数**。')
print('   第三条最容易漏，而漏了它时「执行了删除但删掉 0 条」看起来是一次成功的删除。')
print('   在合规语境下这是实质性的：用户被告知数据已删除，而它还在被检索。')"""),

    md("""## 3 · 新鲜度：公式、模拟、以及为什么均匀假设会低估

$P(\\text{已过期}) = 1-(1-p)^L$。先对拍，再看「热门文档改得更勤」的影响。"""),

    code("""def stale_frac_formula(p, L):
    return 1 - (1 - p) ** L

def stale_frac_sim(p, L, n_docs=20000, seed=0):
    \"\"\"每天每篇文档以概率 p 变更；索引滞后 L 天。\"\"\"
    rng = np.random.default_rng(seed)
    changed = (rng.random((n_docs, L)) < p).any(axis=1)
    return float(changed.mean())

print(f"{'p':>8}{'L':>5}{'公式':>9}{'模拟':>9}{'差':>8}")
worst = 0.0
for p, L in [(0.01, 7), (0.01, 30), (0.05, 7), (0.05, 1), (0.20, 1), (0.002, 90)]:
    f, s = stale_frac_formula(p, L), stale_frac_sim(p, L)
    worst = max(worst, abs(f - s))
    print(f'{p:>8.3f}{L:>5}{f:>9.3f}{s:>9.3f}{abs(f - s):>8.4f}')
assert worst < 0.02, f'公式与模拟的最大偏差 {worst}'
print(f'\\n✅ 公式与模拟吻合（最大偏差 {worst:.4f}）。')
print('   工程结论：**先测 p，再定重建周期**，而不是反过来。')
print('   p 几乎总能从源库的 updated_at 免费算出来。')"""),

    code("""# --- 均匀假设会低估：热门文档改得更勤 ---
def expected_stale_answer_rate(p_per_doc, pi_per_doc, L):
    \"\"\"按「被查中概率」加权的过期答案率。\"\"\"
    p_per_doc, pi_per_doc = np.asarray(p_per_doc), np.asarray(pi_per_doc)
    pi = pi_per_doc / pi_per_doc.sum()
    return float((pi * (1 - (1 - p_per_doc) ** L)).sum())

n = 200
rng = np.random.default_rng(7)
# 文档热度服从幂律；变更率与热度**正相关**（政策、价格、排班都是这样）
pi = 1.0 / (np.arange(1, n + 1) ** 1.1)
p_correlated = np.clip(0.002 + 0.06 * (pi / pi.max()), 0, 1)
p_uniform = np.full(n, p_correlated.mean())      # 同样的平均变更率，但与热度无关

L = 7
naive = expected_stale_answer_rate(p_uniform, np.ones(n), L)      # 文档均匀 + 均匀热度
weighted = expected_stale_answer_rate(p_correlated, pi, L)        # 真实情况
print(f'平均变更率 p̄ = {p_correlated.mean():.4f}/天, 滞后 L = {L} 天')
print(f'  按「文档均匀」估:   {naive:.2%}')
print(f'  按「查询加权」估:   {weighted:.2%}')
print(f'  低估倍数: {weighted / naive:.1f}×')
assert weighted > naive, '热门文档改得更勤时，均匀假设会低估过期答案率'
assert weighted / naive > 1.5
print(f'\\n✅ 均匀假设低估了 {weighted / naive:.1f} 倍。')
print('   原因：π（被查中概率）与 p（变更率）正相关——热门文档也是改得最频繁的。')
print('   所以要报的不是「多少比例的文档过期」，而是「多少比例的**答案**过期」。')

# --- 事件驱动必须配对账 ---
def reconcile(source, index):
    \"\"\"比对源库与索引的 (doc_id, version) 集合。返回 (缺失, 多余)。\"\"\"
    src = {(d, doc['version']) for d, doc in source.items()}
    idx = {(k[0], k[1]) for k in index.blocks}
    return sorted(src - idx), sorted(idx - src)

drifted = Index('event-driven', EMB_OLD)
for i, (did, doc) in enumerate(SOURCE.items()):
    if i == 2:
        continue                      # 模拟一条事件丢了
    drifted.upsert(did, doc, now=0)
missing, extra = reconcile(SOURCE, drifted)
print(f'\\n对账: 索引缺 {missing}，多 {extra}')
assert missing and not extra, '丢了的那一篇必须能被对账发现'
print('✅ 事件会丢，而丢了的那一篇会**永久**过期——所以事件驱动必须配一条定时对账。')"""),

    md("""## 4 · 新旧 embedding 混用：跨空间内积接近 0

**而它看起来完全正常**：在 [-1,1] 之间，有分布，能排序。"""),

    code("""TEXTS = [doc['text'] for doc in SOURCE.values()]
same_space, cross_space = [], []
for t in TEXTS:
    same_space.append(cos(EMB_OLD(t), EMB_OLD(t)))          # 自己与自己
    cross_space.append(cos(EMB_OLD(t), EMB_NEW(t)))         # 同一段文本，跨空间

print(f'同一段文本：同空间内积 {np.mean(same_space):.3f}，'
      f'跨空间内积 {np.mean(cross_space):.4f}')

# 「一段文本与它的改写」在同空间里的相似度作为参照
pairs = [('餐饮报销的单次上限是 200 元。', '餐饮报销单次最多 200 元。'),
         ('密码长度不得少于 12 位。', '密码至少要 12 位。'),
         ('笔记本电脑的更换周期是 36 个月。', '笔记本三年换一次。')]
same_para = [cos(EMB_OLD(a), EMB_OLD(b)) for a, b in pairs]
cross_para = [cos(EMB_OLD(a), EMB_NEW(b)) for a, b in pairs]
print(f'改写对：  同空间 {np.mean(same_para):.3f}，跨空间 {np.mean(cross_para):.4f}')

assert np.mean(cross_space) < 0.1, '跨空间内积应当接近 0'
assert np.mean(same_para) > 5 * abs(np.mean(cross_para)), \\
    '同空间的改写相似度远高于跨空间的同文本相似度'
print(f'\\n✅ **同一段文本**在两个空间里的内积只有 {np.mean(cross_space):.4f}，')
print(f'   而「一段文本与它的改写」在同一个空间里有 {np.mean(same_para):.3f}。')
print('   跨空间的内积不是「不太准」，它是一个随机投影的内积——期望为 0。')"""),

    code("""# --- 混版本索引的后果：跨空间的块几乎永远排在后面 ---
MIXED = Index('mixed-DANGER', EMB_NEW)          # 查询用新模型编码
for i, (did, doc) in enumerate(SOURCE.items()):
    E = EMB_NEW if i % 2 == 0 else EMB_OLD      # 一半用新、一半用旧（渐进迁移的产物）
    MIXED.blocks[(did, doc['version'])] = dict(
        text=doc['text'], vec=E(doc['text']), tenant=doc['tenant'],
        indexed_at=0, embed_model=E.model_id)

print('混版本索引:', MIXED.stats())
assert len(MIXED.stats()['models']) == 2, '这个索引里有两个 embedding 空间'

# 对每个块，看它「作为自己内容的查询」时能排第几
print(f"\\n{'块':<10}{'编码模型':<26}{'用自己的文本查时的名次':>22}")
ranks_same, ranks_cross = [], []
for (did, v), b in MIXED.blocks.items():
    hits = MIXED.search(b['text'], k=len(MIXED.blocks))
    rank = [key for key, _, _ in hits].index((did, v)) + 1
    is_same = b['embed_model'] == EMB_NEW.model_id
    (ranks_same if is_same else ranks_cross).append(rank)
    print(f'{did:<10}{b["embed_model"]:<26}{rank:>22}')

print(f'\\n与查询同空间的块: 平均名次 {np.mean(ranks_same):.1f}')
print(f'跨空间的块:       平均名次 {np.mean(ranks_cross):.1f}')
assert np.mean(ranks_same) < np.mean(ranks_cross), '跨空间的块系统性地排在后面'
assert min(ranks_same) == 1 and min(ranks_cross) > 1, \\
    '同空间的块能排第一，跨空间的块连「用自己的文本查」都排不到第一'
print('\\n✅ 跨空间的块**连用自己的原文去查都排不到第一名**。')
print('   等于那部分索引对检索不可见——而存储、内存、账单照付。')
print('   而且整个过程没有任何报错：分数都在 [-1,1] 之间，有分布，能排序。')
print('   这是本模块最危险的一个失败，也是为什么模型腐烂只能整体换。')"""),

    md("""## 5 · 影子索引与原子切换

含双写、一致性校验、**中途混版本状态的错误行为**、以及回滚。"""),

    code("""class Router:
    \"\"\"原子切换的实现：一个指针。读取方**每次请求**重新读它。\"\"\"
    def __init__(self, active, previous=None):
        self.active = active
        self.previous = previous

    def search(self, *a, **kw):
        return self.active.search(*a, **kw)      # 每次都读 self.active

    def switch_to(self, new_index):
        self.previous, self.active = self.active, new_index

    def rollback(self):
        assert self.previous is not None, '没有可回滚的索引——这次切换是不可回滚的'
        self.active, self.previous = self.previous, self.active

# --- t0/t1: 建影子索引 + 双写 ---
SRC = {k: dict(v) for k, v in SOURCE.items() if k != 'gx-01'}   # gx-01 已删
main = Index('kb-v6-e5base', EMB_OLD)
for did, doc in SRC.items():
    main.upsert(did, doc, now=0)
router = Router(main)

shadow = Index('kb-v7-e5large', EMB_NEW)
backfilled = list(SRC.items())[:3]                 # 回填进行到一半
for did, doc in backfilled:
    shadow.upsert(did, doc, now=1)

# 回填期间来了一次更新：**必须双写**
upd = dict(SRC['sec-01']); upd['text'] = '密码长度不得少于 16 位。'; upd['version'] = 2
SRC['sec-01'] = upd
def dual_write(did, doc, now):
    a = router.active.upsert(did, doc, now)
    b = shadow.upsert(did, doc, now)
    if a['written'] != b['written']:
        raise RuntimeError('双写不一致 —— 必须报警，不能静默丢弃')
    return a, b
dual_write('sec-01', upd, 2)

# 回填剩下的
for did, doc in SRC.items():
    if (did, doc['version']) not in [(d, x['version']) for d, x in backfilled] \\
            and (did, doc['version']) not in shadow.blocks:
        shadow.upsert(did, doc, now=2)

print('主索引:', router.active.stats())
print('影子  :', shadow.stats())"""),

    code("""# --- t2: 一致性校验（三条） ---
def consistency_check(old, new, eval_pairs, k=3):
    \"\"\"返回 (blocking, observations)。\"\"\"
    blocking, obs = [], {}
    # ① 覆盖率必须完全相等 —— 确定性检查
    so, sn = old.stats(), new.stats()
    if (so['docs'], so['blocks']) != (sn['docs'], sn['blocks']):
        blocking.append(f"覆盖率不等: 旧 {so['docs']}/{so['blocks']} "
                        f"vs 新 {sn['docs']}/{sn['blocks']}")
    # 新索引必须单一模型
    if len(sn['models']) != 1:
        blocking.append(f"新索引里有 {len(sn['models'])} 个 embedding 空间")
    # ② 离线指标
    def hit_rate(idx):
        return np.mean([any(gold in t for _, t, _ in idx.search(q, k=k, tenant='acme'))
                        for q, gold in eval_pairs])
    obs['recall_old'] = float(hit_rate(old)); obs['recall_new'] = float(hit_rate(new))
    if obs['recall_new'] < obs['recall_old'] - 1e-12:
        blocking.append(f"离线命中率下降 {obs['recall_old']:.2f} → {obs['recall_new']:.2f}")
    # ③ 重叠率 —— **观测量，不设门禁**
    js = []
    for q, _ in eval_pairs:
        a = {key for key, _, _ in old.search(q, k=k, tenant='acme')}
        b = {key for key, _, _ in new.search(q, k=k, tenant='acme')}
        js.append(len(a & b) / len(a | b) if (a | b) else 1.0)
    obs['top_k_jaccard'] = float(np.mean(js))
    return blocking, obs

EVAL = [('正式员工年假多少天', '15 天'), ('餐饮报销上限', '200 元'),
        ('差旅报销上限', '3000 元'), ('电脑多久换', '36 个月'),
        ('密码要多长', '16 位')]
blocking, obs = consistency_check(router.active, shadow, EVAL)
print('阻断项:', blocking if blocking else '无')
print('观测量:', {k: round(v, 3) for k, v in obs.items()})
assert blocking == [], f'一致性校验应当通过: {blocking}'
assert obs['top_k_jaccard'] < 1.0, \\
    '重叠率必须 < 1.0——如果等于 1.0，说明配置没生效，你其实没换成新模型'
print('\\n✅ 校验通过。注意重叠率是**观测量而不是门禁**：')
print(f"   {obs['top_k_jaccard']:.2f} 低可能意味着新模型更好，也可能更差，这个数不能判定方向。")
print('   它唯一确定的用途是：如果等于 1.0，先怀疑配置没生效。')"""),

    code("""# --- t3: 原子切换 + 回滚 ---
q = '密码要多长'
before = router.search(q, k=1, tenant='acme')
router.switch_to(shadow)
after = router.search(q, k=1, tenant='acme')
print(f'切换前 top1: {before[0][1]}  (索引 {router.previous.index_id})')
print(f'切换后 top1: {after[0][1]}  (索引 {router.active.index_id})')
assert '16 位' in before[0][1] and '16 位' in after[0][1], '双写保证了两边都有最新内容'
assert router.active is shadow and router.previous is main

router.rollback()
assert router.active is main, '回滚必须是同一个指针的反向操作'
print(f'回滚后: 索引 {router.active.index_id}')
router.switch_to(shadow)

# 不可回滚的情况
lonely = Router(Index('only-one', EMB_NEW))
try:
    lonely.rollback()
    raise SystemExit('不该到这里')
except AssertionError as e:
    print(f'✅ 断言捕获: {e}')
print('\\n✅ 切换是改一个指针；回滚是同一指针的反向操作。')
print('   如果回滚需要重建索引，那就等于没有回滚——这样的切换不该上线。')"""),

    code("""# --- 中途状态必须不可达：缓存了 active 的读取方 ---
class BadReader:
    \"\"\"错误实现：进程启动时读一次并缓存。\"\"\"
    def __init__(self, router):
        self.index = router.active          # ← 缓存了

    def search(self, *a, **kw):
        return self.index.search(*a, **kw)

router2 = Router(main)
bad = BadReader(router2)                    # 旧实例
router2.switch_to(shadow)
good = router2                              # 新实例每次重新读 active

upd2 = dict(SRC['fin-01']); upd2['text'] = '餐饮报销的单次上限是 260 元。'
upd2['version'] = 2
SRC['fin-01'] = upd2                        # 源库更新了
shadow.upsert('fin-01', upd2, now=3)        # 但**只有新索引**收到了这次更新
# 注意这里刻意没有双写 —— 下面要演示的正是「切换后旧进程继续用旧索引」的后果

q2 = '餐饮报销上限'
t_bad = bad.search(q2, k=1, tenant='acme')[0][1]
t_good = good.search(q2, k=1, tenant='acme')[0][1]
print(f'缓存了 active 的实例: {t_bad}')
print(f'每次重读 active 的实例: {t_good}')
assert t_bad != t_good, '同一时刻两个实例返回了不同结果'
print('\\n✅ 这就是「中途状态可达」的具体形态：')
print('   切换后旧进程继续用旧索引，于是**同一时刻不同实例返回不同结果**。')
print('   要求很简单但必须写进代码：读取方每次请求重新读那个指针。')"""),

    md("""## 6 · 多租户：两种隔离，以及缓存键这条泄漏路径"""),

    code("""# 方案 A：共享索引 + 元数据过滤（tenant 是**必填关键字参数**）
def search_shared(index, query, k=3, *, tenant):
    \"\"\"tenant 是必填关键字参数——漏写会 TypeError，而不是静默返回全部。\"\"\"
    return index.search(query, k=k, tenant=tenant)

try:
    search_shared(shadow, '门禁卡', k=3)          # 故意漏写 tenant
    raise SystemExit('不该到这里')
except TypeError as e:
    print(f'✅ 漏写 tenant 直接报错: {type(e).__name__}')

# 方案 B：独立索引 —— 结构性隔离
PER_TENANT = {}
for did, doc in SOURCE.items():
    t = doc['tenant']
    if t not in PER_TENANT:
        PER_TENANT[t] = Index(f'kb-{t}', EMB_NEW)
    PER_TENANT[t].upsert(did, doc, now=0)
print({t: idx.stats()['blocks'] for t, idx in PER_TENANT.items()})
# 连不到别人的索引：globex 的索引里根本没有 acme 的内容
res = PER_TENANT['globex'].search('餐饮报销上限', k=3)
assert all('报销' not in t for _, t, _ in res), 'globex 的索引里不该有 acme 的内容'
print('✅ 独立索引：错误的租户根本连不到那个索引。')"""),

    code("""# --- 缓存键：容易被忘的泄漏路径 ---
CACHE = {}

def cached_search_bad(index, query, k=3, *, tenant):
    key = (query, k)                                  # ❌ 没有 tenant
    if key not in CACHE:
        CACHE[key] = index.search(query, k=k, tenant=tenant)
    return CACHE[key]

def cached_search_good(index, query, k=3, *, tenant):
    key = (tenant, query, k)                          # ✅ 含 tenant
    if key not in CACHE:
        CACHE[key] = index.search(query, k=k, tenant=tenant)
    return CACHE[key]

Q = '需要提前申请吗'
for name, fn in [('缓存键不含 tenant', cached_search_bad),
                 ('缓存键含 tenant', cached_search_good)]:
    CACHE.clear()
    r_acme = fn(shadow, Q, k=2, tenant='acme')
    r_gx = fn(shadow, Q, k=2, tenant='globex')
    leaked = any(shadow.blocks[key]['tenant'] != 'globex' for key, _, _ in r_gx)
    print(f'{name:<22} globex 拿到 acme 的内容: {leaked}')
    if name.endswith('不含 tenant'):
        assert leaked, '不含 tenant 的缓存键会造成跨租户泄漏'
    else:
        assert not leaked, '含 tenant 的缓存键不会泄漏'
print('\\n✅ 缓存键必须含租户标识——这一条与检索侧的过滤同等重要，而它更容易被忘。')
print('   注意泄漏的方向：**先查的那个租户的结果被后查的租户命中**，')
print('   所以它在低流量测试里常常不出现（两个租户很少查同一个问题）。')"""),

    md("""## 7 · 派生资产的静默过期

最危险的一个是**评测集的 gold chunk id**——它会造成一次「假事故」。"""),

    code("""# --- 派生资产：带上依赖的版本，读取时校验 ---
class DerivedStore:
    def __init__(self):
        self.items = {}          # key -> dict(value, dep_doc, dep_version)

    def put(self, key, value, dep_doc, dep_version):
        self.items[key] = dict(value=value, dep_doc=dep_doc, dep_version=dep_version)

    def get(self, key, source):
        it = self.items.get(key)
        if it is None:
            return None, 'miss'
        cur = source.get(it['dep_doc'])
        if cur is None:
            return None, 'dep_deleted'
        if cur['version'] != it['dep_version']:
            return None, 'stale'                 # ← 当未命中处理，不照用
        return it['value'], 'hit'

SUM = DerivedStore()
SUM.put('sum:fin-01', '餐饮报销上限 200 元（摘要）', 'fin-01', 1)
SUM.put('sum:gx-01', '门禁卡补办流程（摘要）', 'gx-01', 1)

print(SUM.get('sum:fin-01', SRC))                    # fin-01 已到 v2 → stale
print(SUM.get('sum:gx-01', SRC))                     # gx-01 已删 → dep_deleted
SUM.put('sum:fin-01', '餐饮报销上限 260 元（摘要）', 'fin-01', 2)
print(SUM.get('sum:fin-01', SRC))                    # 重算后 → hit

assert SUM.get('sum:gx-01', SRC)[1] == 'dep_deleted'
assert SUM.get('sum:fin-01', SRC)[1] == 'hit'
print('\\n✅ 每个派生资产都带 (dep_doc, dep_version)，读取时校验。')
print('   不匹配就当未命中重新计算，而不是照用。')"""),

    code("""# --- 评测集绑在 chunk_id 上 → 换分块后的「假事故」 ---
# 需要**足够长**的文档才能演示：短文档在任何块大小下都只有 #0，id 不会变。
LONG_DOCS = {
    'fin-10': dict(tenant='acme', version=1, text=(
        '报销总则。所有报销需在费用发生后 30 天内提交，逾期不予受理。'
        '餐饮报销的单次上限是 200 元，需附消费明细。'
        '交通报销需提供正规发票，网约车行程单视为有效凭证。')),
    'sec-10': dict(tenant='acme', version=1, text=(
        '账号安全规范。账号不得共享给他人使用，违规将追究责任。'
        '密码长度不得少于 12 位，且需每 90 天更换一次。'
        '离职时需在最后工作日交回所有权限凭证。')),
    'it-10': dict(tenant='acme', version=1, text=(
        '设备管理办法。设备申领需部门负责人审批，到货后由资产管理员登记。'
        '笔记本电脑的更换周期是 36 个月，显示器为 48 个月。'
        '设备损坏需在两个工作日内报修。')),
}

def chunk_by(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]

def build_with_chunking(size, docs=LONG_DOCS):
    idx = Index(f'kb-s{size}', EMB_NEW)
    for did, doc in docs.items():
        for i, piece in enumerate(chunk_by(doc['text'], size)):
            idx.blocks[(f'{did}#{i}', doc['version'])] = dict(
                text=piece, vec=EMB_NEW(piece), tenant=doc['tenant'],
                indexed_at=0, embed_model=EMB_NEW.model_id)
    return idx

idx_a = build_with_chunking(40)      # 旧分块
idx_b = build_with_chunking(24)      # 新分块 → chunk 边界与 id 全变了

def gold_chunk_id(idx, doc_id, answer):
    for key, b in idx.blocks.items():
        if key[0].startswith(doc_id) and answer in b['text']:
            return key[0]
    return None

ANSWERS = [('餐饮报销上限', 'fin-10', '200 元'),
           ('密码要多长', 'sec-10', '12 位'),
           ('电脑多久换', 'it-10', '36 个月')]
print('同一条答案在两种分块下的 chunk_id:')
for q, did, ans in ANSWERS:
    print(f'  {ans:<8} 旧分块 {gold_chunk_id(idx_a, did, ans)}  '
          f'新分块 {gold_chunk_id(idx_b, did, ans)}')

# 评测集写法一：绑 chunk_id（❌）—— 在旧分块上标注
GOLD_BY_ID = [(q, gold_chunk_id(idx_a, did, ans), ans) for q, did, ans in ANSWERS]
# 评测集写法二：绑答案文本（✅，本课全程用的写法）
GOLD_BY_TEXT = [(q, ans) for q, did, ans in ANSWERS]

def id_validity(idx, gold):
    \"\"\"标注的 chunk_id 在这个索引里**还指着答案吗**。
    这个量与检索无关——它衡量的是标注本身有没有失效。\"\"\"
    ok = 0
    for q, gid, ans in gold:
        blk = [b for key, b in idx.blocks.items() if key[0] == gid]
        ok += bool(blk) and (ans in blk[0]['text'])
    return ok / len(gold)

def recall_by_text(idx, pairs, k=3):
    return float(np.mean([any(gold in t for _, t, _ in idx.search(q, k=k))
                          for q, gold in pairs]))

print(f"\\n{'':<14}{'旧分块(标注时)':>16}{'新分块':>10}")
print(f'{"标注 id 仍有效":<14}{id_validity(idx_a, GOLD_BY_ID):>16.2f}'
      f'{id_validity(idx_b, GOLD_BY_ID):>10.2f}')
print(f'{"按答案文本 recall":<14}{recall_by_text(idx_a, GOLD_BY_TEXT):>16.2f}'
      f'{recall_by_text(idx_b, GOLD_BY_TEXT):>10.2f}')

v_old, v_new = id_validity(idx_a, GOLD_BY_ID), id_validity(idx_b, GOLD_BY_ID)
t_new = recall_by_text(idx_b, GOLD_BY_TEXT)
assert v_old == 1.0, '标注是在旧分块上做的，所以在旧分块上必然全有效'
assert v_new < 1.0, '换分块后部分标注失效'
assert t_new > v_new, '绑答案文本的评测集不受 chunk_id 变化影响'
print(f'\\n✅ 换分块方案后，{1 - v_new:.0%} 的标注失效了——')
print('   这些题的 recall 会直接变成 0，而看起来像新分块方案彻底失败。')
print(f'   而按答案文本判定的 recall 是 {t_new:.2f}，不受影响。')
print()
print(f'   注意还有 {v_new:.0%} 的 id **碰巧仍然指对了**（块边界恰好没穿过那句话）。')
print('   这让失效更难发现：它不是「全挂」，而是「一部分题莫名变成 0 分」。')
print('   这与 C68 模块 01「不要用内容哈希当 ID」是同一类教训：')
print('   **不要把标注绑在会变的东西上。**')"""),

    md("""## 8 · 检索层监控四项"""),

    code("""def retrieval_metrics(index, queries, tenants, score_floor=0.15, now=10):
    \"\"\"四项指标，全部不需要真值。零结果率**分租户**算。\"\"\"
    zero_by_tenant, top1 = defaultdict(list), []
    for q, t in zip(queries, tenants):
        hits = index.search(q, k=3, tenant=t)
        empty = (len(hits) == 0) or (hits[0][2] < score_floor)
        zero_by_tenant[t].append(empty)
        if hits:
            top1.append(hits[0][2])
    lags = [now - b['indexed_at'] for b in index.blocks.values()]
    return dict(
        zero_rate_overall=float(np.mean([v for vs in zero_by_tenant.values() for v in vs])),
        zero_rate_by_tenant={t: float(np.mean(v)) for t, v in zero_by_tenant.items()},
        top1_p10=float(np.percentile(top1, 10)) if top1 else 0.0,
        top1_p50=float(np.percentile(top1, 50)) if top1 else 0.0,
        freshness_p99=float(np.percentile(lags, 99)) if lags else 0.0)

QS = ['餐饮报销上限', '密码要多长', '电脑多久换', '年假多少天',
      '门禁卡遗失', '访客怎么进', '差旅报销上限', '报销要多久提交']
TS = ['acme'] * 4 + ['globex'] * 2 + ['acme'] * 2

healthy = retrieval_metrics(shadow, QS, TS)
print('健康:', {k: (round(v, 3) if isinstance(v, float) else
                  {a: round(b, 2) for a, b in v.items()}) for k, v in healthy.items()})

# 故障一：某个租户的过滤条件写错 → 只有那个租户的零结果率爆掉
broken = retrieval_metrics(shadow, QS, ['acme'] * 4 + ['nonexist'] * 2 + ['acme'] * 2)
print('租户配置错:', {k: (round(v, 3) if isinstance(v, float) else
                        {a: round(b, 2) for a, b in v.items()})
                   for k, v in broken.items() if 'zero' in k})
assert broken['zero_rate_by_tenant']['nonexist'] == 1.0
assert broken['zero_rate_overall'] < 0.5, '总体指标完全看不出来'
print(f"  → 总体零结果率只有 {broken['zero_rate_overall']:.0%}，"
      f"而 nonexist 租户是 {broken['zero_rate_by_tenant']['nonexist']:.0%}")

# 故障二：模型腐烂 → top-1 分数分布的**左尾变重**（而中位数可能不动）
mixed_metrics = retrieval_metrics(MIXED, QS, TS)
print(f"\\ntop1 分数: 健康 P10={healthy['top1_p10']:.3f} P50={healthy['top1_p50']:.3f}")
print(f"          混版本 P10={mixed_metrics['top1_p10']:.3f} "
      f"P50={mixed_metrics['top1_p50']:.3f}")
assert mixed_metrics['top1_p10'] < healthy['top1_p10'], '混版本索引的 top1 左尾下移'
assert mixed_metrics['zero_rate_overall'] > healthy['zero_rate_overall']
print('\\n✅ 三个结论：')
print('   ① 零结果率**必须分租户看**——总体指标会把「某个租户全挂」完全平均掉。')
print(f"   ② 模型腐烂的信号在**左尾**而不是中位数：")
print(f"      P50 几乎没动（{healthy['top1_p50']:.3f} → {mixed_metrics['top1_p50']:.3f}），")
print(f"      而 P10 从 {healthy['top1_p10']:.3f} 掉到 {mixed_metrics['top1_p10']:.3f}。")
print('      原因很清楚：跨空间的那部分块分数被压到接近 0，它们只影响分布的下端；')
print('      而查询命中同空间块时，top-1 分数照常。')
print('   ③ **所以只监控中位数会漏掉这个故障**——分数指标必须报分位数，不是均值或中位数。')"""),

    md("""## ✏️ 练习 1：重建周期反解

给定变更率 `p`（每天）与「可接受的过期答案率」`target`，
反解出**最大允许滞后 L**（天），以及对应的重建周期。

实现 `max_lag_for_target(p, target)` 与 `rebuild_period(p, target, mode)`：
- `max_lag_for_target`：最大的 `L`（正整数）使 `1-(1-p)^L <= target`；1 天都超标返回 0
- `rebuild_period(p, target, mode)`：`mode='batch'` 时**平均滞后是周期的一半**，
  所以周期 = `2 * L`；`mode='event'` 时周期就是 L（近实时，滞后≈处理延迟）"""),

    code("""def max_lag_for_target(p, target):
    \"\"\"最大允许滞后天数（整数）。1 天都超标返回 0。\"\"\"
    # TODO
    raise NotImplementedError

def rebuild_period(p, target, mode='batch'):
    \"\"\"返回重建周期（天）。批量模式下平均滞后是周期的一半。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
assert max_lag_for_target(0.01, 0.07) == 7, max_lag_for_target(0.01, 0.07)
L = max_lag_for_target(0.01, 0.07)
assert stale_frac_formula(0.01, L) <= 0.07 < stale_frac_formula(0.01, L + 1)
assert max_lag_for_target(0.5, 0.01) == 0, '变更率极高时 1 天都超标'
assert max_lag_for_target(0.001, 0.05) > 40

# 批量 vs 事件驱动
assert rebuild_period(0.01, 0.07, 'batch') == 2 * L
assert rebuild_period(0.01, 0.07, 'event') == L
# 变更率越高，允许的周期越短
assert rebuild_period(0.05, 0.07, 'batch') < rebuild_period(0.01, 0.07, 'batch')
# 高变更率下批量重建救不了 → 周期 0
assert rebuild_period(0.5, 0.01, 'batch') == 0

print(f"{'p/天':>8}{'target':>9}{'最大滞后':>10}{'批量周期':>10}{'事件周期':>10}")
for p_, t_ in [(0.001, 0.05), (0.01, 0.07), (0.05, 0.07), (0.05, 0.30), (0.20, 0.20)]:
    print(f'{p_:>8.3f}{t_:>9.2f}{max_lag_for_target(p_, t_):>10}'
          f'{rebuild_period(p_, t_, "batch"):>10}{rebuild_period(p_, t_, "event"):>10}')
print('✅ 练习 1 通过：重建周期是从 p 与 target 反解出来的，不是拍出来的')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def max_lag_for_target(p, target):
    if p <= 0:
        return 10 ** 6
    L = 0
    while stale_frac_formula(p, L + 1) <= target + 1e-12:
        L += 1
        if L > 10 ** 6:
            break
    return L

def rebuild_period(p, target, mode='batch'):
    L = max_lag_for_target(p, target)
    return 2 * L if mode == 'batch' else L

assert max_lag_for_target(0.01, 0.07) == 7
assert max_lag_for_target(0.5, 0.01) == 0
assert rebuild_period(0.01, 0.07, 'batch') == 14
assert rebuild_period(0.5, 0.01, 'batch') == 0
print('✅ 参考答案 1 通过')
print('   注意批量模式那个 2 倍：**平均滞后是周期的一半**，')
print('   所以「每 7 天重建一次」对应的平均滞后是 3.5 天、最坏是 7 天。')
print('   报 SLA 时要报最坏值；估过期率时用平均值。混用这两个数是一个常见错误。')
print('   而当反解出的周期是 0 时，结论不是「周期设成 0」，')
print('   而是**批量重建这条路对这个变更率不成立，必须换事件驱动**。')"""),

    md("""## ✏️ 练习 2：切换前的一致性校验

实现 `migration_gate(old, new, eval_pairs, sigma, k=3)`，返回 `(blocking, warnings, obs)`：

- **确定性阻断**：docs/blocks 数不等；新索引里有多于一个 embedding 空间；
  新索引里存在 `embed_model` 与索引声明不符的块
- **统计阻断**：离线命中率下降超过 `2 * sigma`（`sigma` 是重复测量得到的噪声）
- **报警**：`top_k_jaccard == 1.0`（配置很可能没生效）
- `obs` 里要有 `recall_old` / `recall_new` / `top_k_jaccard`"""),

    code("""def migration_gate(old, new, eval_pairs, sigma, k=3):
    \"\"\"返回 (blocking, warnings, obs)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
SIGMA = 0.02

# ---- 先把所有 fixture 建好（放在断言之前，这样它们对参考答案 cell 也可见）----
# 用一对**干净的**索引：前面几节为了演示故障，已经把 main / shadow 改成不一致了。
# 评测集的 gold 也跟着源库的当前值走（fin-01 已是 260 元、sec-01 已是 16 位）。
MIG_SRC = {k: dict(v) for k, v in SRC.items()}
mig_old = Index('mig-v6', EMB_OLD)
mig_new = Index('mig-v7', EMB_NEW)
for did, doc in MIG_SRC.items():
    mig_old.upsert(did, doc, now=0)
    mig_new.upsert(did, doc, now=0)
MIG_EVAL = [('正式员工年假多少天', '15 天'), ('餐饮报销上限', '260 元'),
            ('差旅报销上限', '3000 元'), ('电脑多久换', '36 个月'),
            ('密码要多长', '16 位')]

partial = Index('partial', EMB_NEW)                  # 只回填了一部分
for did, doc in list(MIG_SRC.items())[:3]:
    partial.upsert(did, doc, now=0)

weak = Index('weak', EMB_NEW)                        # 人为破坏两条内容
for did, doc in MIG_SRC.items():
    d2 = dict(doc)
    if did in ('fin-01', 'sec-01'):
        d2['text'] = '（本节内容已移除）'
    weak.upsert(did, d2, now=0)

# ---- 断言 ----
# a) 正常迁移 → 全绿
b, w, obs = migration_gate(mig_old, mig_new, MIG_EVAL, SIGMA)
assert b == [], b
assert set(obs) >= {'recall_old', 'recall_new', 'top_k_jaccard'}

# b) 覆盖率不等 → 阻断
b2, _, _ = migration_gate(mig_old, partial, MIG_EVAL, SIGMA)
assert any('覆盖率' in x for x in b2), b2

# c) 混了两个 embedding 空间 → 阻断
b3, _, _ = migration_gate(mig_old, MIXED, MIG_EVAL, SIGMA)
assert any('空间' in x or 'embedding' in x for x in b3), b3

# d) 自己跟自己比 → 重叠率 1.0 → 报警（不阻断）
b4, w4, obs4 = migration_gate(mig_old, mig_old, MIG_EVAL, SIGMA)
assert b4 == [], b4
assert abs(obs4['top_k_jaccard'] - 1.0) < 1e-9
assert any('没生效' in x or 'jaccard' in x.lower() for x in w4), w4

# e) 命中率下降超过 2σ → 阻断
b5, _, obs5 = migration_gate(mig_old, weak, MIG_EVAL, SIGMA)
assert any('命中率' in x for x in b5), (b5, obs5)
print('✅ 练习 2 通过：确定性项与统计项分级，重叠率只报警')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def migration_gate(old, new, eval_pairs, sigma, k=3):
    blocking, warn, obs = [], [], {}
    so, sn = old.stats(), new.stats()
    if (so['docs'], so['blocks']) != (sn['docs'], sn['blocks']):
        blocking.append(f"覆盖率不等: 旧 {so['docs']}/{so['blocks']} "
                        f"vs 新 {sn['docs']}/{sn['blocks']}")
    if len(sn['models']) != 1:
        blocking.append(f"新索引里有 {len(sn['models'])} 个 embedding 空间，必须只有 1 个")
    else:
        declared = new.embed.model_id
        bad = [k for k, b in new.blocks.items() if b['embed_model'] != declared]
        if bad:
            blocking.append(f'{len(bad)} 个块的 embed_model 与索引声明不符')

    def hit_rate(idx):
        return float(np.mean([
            any(gold in t for _, t, _ in idx.search(q, k=k, tenant='acme'))
            for q, gold in eval_pairs]))
    obs['recall_old'], obs['recall_new'] = hit_rate(old), hit_rate(new)
    if obs['recall_new'] < obs['recall_old'] - 2 * sigma:
        blocking.append(f"离线命中率下降 {obs['recall_old']:.2f} → "
                        f"{obs['recall_new']:.2f}（> 2σ = {2 * sigma:.2f}）")

    js = []
    for q, _ in eval_pairs:
        a = {key for key, _, _ in old.search(q, k=k, tenant='acme')}
        bset = {key for key, _, _ in new.search(q, k=k, tenant='acme')}
        js.append(len(a & bset) / len(a | bset) if (a | bset) else 1.0)
    obs['top_k_jaccard'] = float(np.mean(js))
    if abs(obs['top_k_jaccard'] - 1.0) < 1e-9:
        warn.append('top-k jaccard = 1.0，结果一点没变——先怀疑配置没生效')
    return blocking, warn, obs

b, w, obs = migration_gate(mig_old, mig_new, MIG_EVAL, SIGMA)
assert b == []
assert any('覆盖率' in x for x in migration_gate(mig_old, partial, MIG_EVAL, SIGMA)[0])
assert any('空间' in x for x in migration_gate(mig_old, MIXED, MIG_EVAL, SIGMA)[0])
assert migration_gate(mig_old, mig_old, MIG_EVAL, SIGMA)[1]
assert any('命中率' in x for x in migration_gate(mig_old, weak, MIG_EVAL, SIGMA)[0])
print('✅ 参考答案 2 通过')
print('   三条校验的分工值得记住：')
print('   ① 覆盖率 / 单一模型空间 —— 确定性，零误报，阻断；')
print('   ② 离线命中率 —— 统计，阈值从 σ 推（C68-04），阻断；')
print('   ③ 重叠率 —— **只报警**，因为它低既可能是变好也可能是变坏。')
print('      它唯一确定的用途是：等于 1.0 时说明你其实没换成新模型。')"""),

    md("""## ✏️ 练习 3：租户数据的完整删除

一个租户要求删除它的全部数据。实现 `purge_tenant(index, derived, cache, tenant)`，
返回 `dict(blocks_deleted, derived_deleted, cache_deleted, remaining)`。

要求（对应讲解第 2 节的「删除的三层」）：
- 删索引里该租户的全部块
- 删所有依赖这些 doc 的派生资产
- 删缓存里所有属于该租户的条目（缓存键形如 `(tenant, query, k)`）
- `remaining` 是删除后索引里仍属于该租户的块数，**必须是 0**"""),

    code("""def purge_tenant(index, derived, cache, tenant):
    \"\"\"返回 dict(blocks_deleted, derived_deleted, cache_deleted, remaining)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
idx = Index('purge-test', EMB_NEW)
for did, doc in SOURCE.items():
    idx.upsert(did, doc, now=0)
der = DerivedStore()
for did in SOURCE:
    der.put(f'sum:{did}', f'{did} 的摘要', did, 1)
    der.put(f'triples:{did}', [(did, 'rel', 'x')], did, 1)
cch = {('acme', '年假', 3): ['...'], ('globex', '门禁', 3): ['...'],
       ('globex', '访客', 3): ['...'], ('acme', '报销', 3): ['...']}

n_gx_blocks = sum(1 for b in idx.blocks.values() if b['tenant'] == 'globex')
r = purge_tenant(idx, der, cch, 'globex')
print(r)

assert r['remaining'] == 0, '删除后必须一个块都不剩'
assert r['blocks_deleted'] == n_gx_blocks, (r['blocks_deleted'], n_gx_blocks)
assert r['derived_deleted'] == 2 * n_gx_blocks, '每个 doc 有两个派生资产'
assert r['cache_deleted'] == 2, 'globex 有两条缓存'
# acme 的数据一条都不能少
assert sum(1 for b in idx.blocks.values() if b['tenant'] == 'acme') == \\
       sum(1 for d in SOURCE.values() if d['tenant'] == 'acme')
assert any(k[0] == 'acme' for k in cch), 'acme 的缓存必须保留'
assert all(k[0] != 'globex' for k in cch), 'globex 的缓存必须清空'
# tombstone 防止被全量同步灌回
assert idx.upsert('gx-02', SOURCE['gx-02'], now=1)['rejected'] == 1
print('✅ 练习 3 通过：三层都删干净，且不误伤其它租户')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def purge_tenant(index, derived, cache, tenant):
    doc_ids = {k[0] for k, b in index.blocks.items() if b['tenant'] == tenant}
    blocks_deleted = 0
    for did in doc_ids:
        blocks_deleted += index.delete(did, reason=f'tenant_purge:{tenant}')
    derived_deleted = 0
    for key in [k for k, it in derived.items.items() if it['dep_doc'] in doc_ids]:
        del derived.items[key]; derived_deleted += 1
    cache_deleted = 0
    for key in [k for k in cache if k[0] == tenant]:
        del cache[key]; cache_deleted += 1
    remaining = sum(1 for b in index.blocks.values() if b['tenant'] == tenant)
    return dict(blocks_deleted=blocks_deleted, derived_deleted=derived_deleted,
                cache_deleted=cache_deleted, remaining=remaining)

idx = Index('purge-test', EMB_NEW)
for did, doc in SOURCE.items():
    idx.upsert(did, doc, now=0)
der = DerivedStore()
for did in SOURCE:
    der.put(f'sum:{did}', f'{did} 的摘要', did, 1)
    der.put(f'triples:{did}', [(did, 'rel', 'x')], did, 1)
cch = {('acme', '年假', 3): ['...'], ('globex', '门禁', 3): ['...'],
       ('globex', '访客', 3): ['...'], ('acme', '报销', 3): ['...']}
r = purge_tenant(idx, der, cch, 'globex')
assert r['remaining'] == 0 and r['cache_deleted'] == 2
assert idx.upsert('gx-02', SOURCE['gx-02'], now=1)['rejected'] == 1
print('✅ 参考答案 3 通过')
print('   注意 remaining 这个字段：它不是日志，是**断言的对象**。')
print('   「执行了删除」和「删干净了」是两件事，而只有后者能对用户与监管交代。')
print('   而枚举「属于这个租户的全部块」依赖模块 01 把 tenant 写进了每个块的元数据——')
print('   摄取时几乎免费的一个字段，在这里决定了合规能不能做到。')"""),

    md("""## ✏️ 练习 4：索引运维卡 + 门禁

实现 `ops_card(index, source, metrics, p_change, sla_hours, now)` 与
`ops_gate(card)`。

`ops_card` 返回含这些键的 dict：
`index_id` / `embed_models` / `docs` / `blocks` / `freshness_p99_h` /
`p_change` / `expected_stale_frac`（用 `1-(1-p)^L`，L 用 `freshness_p99_h/24` 天）/
`zero_rate_max_tenant` / `top1_p50` / `reconcile_missing`（对账缺失数）。

`ops_gate` 的规则：
- **确定性阻断**：`embed_models` 多于 1 个；`freshness_p99_h > sla_hours`；
  任一租户零结果率 == 1.0；`reconcile_missing > 0`
- **报警**：`expected_stale_frac > 0.05`"""),

    code("""def ops_card(index, source, metrics, p_change, sla_hours, now):
    \"\"\"返回运维卡 dict（含 sla_hours）。\"\"\"
    # TODO
    raise NotImplementedError

def ops_gate(card):
    \"\"\"返回 (blocking, warnings)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# ---- fixture 全部前置 ----
fresh_idx = Index('kb-v7-e5large', EMB_NEW)
for did, doc in SRC.items():
    fresh_idx.upsert(did, doc, now=10)
m = retrieval_metrics(fresh_idx, QS, TS, now=12)
m_mixed = retrieval_metrics(MIXED, QS, TS, now=12)

stale_idx = Index('kb-stale', EMB_NEW)
for did, doc in SRC.items():
    stale_idx.upsert(did, doc, now=0)
m_stale = retrieval_metrics(stale_idx, QS, TS, now=48)

# ---- 断言 ----
card = ops_card(fresh_idx, SRC, m, p_change=0.009, sla_hours=6, now=12)
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in card.items()})
b, w = ops_gate(card)
assert card['embed_models'] == 1
assert card['reconcile_missing'] == 0
assert b == [], b

# a) 混版本 → 阻断
card_mixed = ops_card(MIXED, SOURCE, m_mixed, 0.009, 6, now=12)
assert card_mixed['embed_models'] == 2
assert any('空间' in x or 'embed' in x for x in ops_gate(card_mixed)[0])

# b) 新鲜度超 SLA → 阻断
card_stale = ops_card(stale_idx, SRC, m_stale, 0.009, sla_hours=6, now=48)
assert card_stale['freshness_p99_h'] > 6
assert any('新鲜度' in x or 'SLA' in x for x in ops_gate(card_stale)[0])

# c) 对账缺失 → 阻断
card_missing = ops_card(partial, SRC, m, 0.009, 6, now=12)
assert card_missing['reconcile_missing'] > 0
assert any('对账' in x for x in ops_gate(card_missing)[0])

# d) 过期率高 → 只报警
card_hot = ops_card(stale_idx, SRC, m_stale, p_change=0.05, sla_hours=100, now=48)
b4, w4 = ops_gate(card_hot)
assert b4 == [] and any('过期' in x for x in w4), (b4, w4)
print('✅ 练习 4 通过：运维卡四项阻断 + 一项报警')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def ops_card(index, source, metrics, p_change, sla_hours, now):
    lags_h = [now - b['indexed_at'] for b in index.blocks.values()]
    p99_h = float(np.percentile(lags_h, 99)) if lags_h else 0.0
    missing, extra = reconcile(source, index)
    return dict(
        index_id=index.index_id,
        embed_models=len(index.stats()['models']),
        docs=index.stats()['docs'], blocks=index.stats()['blocks'],
        freshness_p99_h=p99_h,
        sla_hours=sla_hours,
        p_change=p_change,
        expected_stale_frac=stale_frac_formula(p_change, p99_h / 24.0),
        zero_rate_max_tenant=max(metrics['zero_rate_by_tenant'].values()),
        top1_p50=metrics['top1_p50'],
        reconcile_missing=len(missing))

def ops_gate(card):
    blocking, warn = [], []
    if card['embed_models'] != 1:
        blocking.append(f"索引里有 {card['embed_models']} 个 embedding 空间")
    if card['freshness_p99_h'] > card['sla_hours']:
        blocking.append(f"新鲜度 p99 {card['freshness_p99_h']:.1f}h "
                        f"> SLA {card['sla_hours']}h")
    if card['zero_rate_max_tenant'] >= 1.0:
        blocking.append('有租户的零结果率是 100%（很可能是租户配置错）')
    if card['reconcile_missing'] > 0:
        blocking.append(f"对账发现索引缺 {card['reconcile_missing']} 篇文档")
    if card['expected_stale_frac'] > 0.05:
        warn.append(f"预期过期文档比例 {card['expected_stale_frac']:.1%} > 5%")
    return blocking, warn

card = ops_card(fresh_idx, SRC, m, 0.009, 6, now=12)
assert ops_gate(card)[0] == []
assert ops_gate(ops_card(MIXED, SOURCE, m_mixed, 0.009, 6, now=12))[0]
assert ops_gate(ops_card(stale_idx, SRC, m_stale, 0.009, 6, now=48))[0]
assert ops_gate(ops_card(partial, SRC, m, 0.009, 6, now=12))[0]
assert ops_gate(ops_card(stale_idx, SRC, m_stale, 0.05, 100, now=48))[0] == []
assert ops_gate(ops_card(stale_idx, SRC, m_stale, 0.05, 100, now=48))[1]
print('✅ 参考答案 4 通过')
print('   四项阻断的共同点：它们全是**算术或计数**，误报率为零。')
print('   而「预期过期率」只报警，因为它依赖一个估计出来的 p。')
print('   注意这张卡里最重要的一行不在门禁里——是回滚指针。')
print('   如果回滚需要重建索引，那么这次切换是不可回滚的，不该上线。')"""),

    md("""## 🧪 真实工程胶囊：索引运维的落地

```python
# ══════════════════════════════════════════════════════════════════
# A. 模型版本钉死，写进索引元数据（讲解第 1 节）
# ══════════════════════════════════════════════════════════════════
INDEX_SPEC = {
    'index_id': 'kb-v7-e5large-2026w35',
    'embed_model': 'intfloat/e5-large-v2',
    'embed_revision': 'a1b2c3d',          # ← HF revision / 镜像 digest，不是 'latest'
    'chunker': 'structure_aware', 'chunk_size': 400, 'overlap': 62,
}
#   每个块的 metadata 里也存一份 embed_revision —— 这样「索引里有几个空间」
#   变成一次 SELECT COUNT(DISTINCT embed_revision)，而不是靠人记得。

# ══════════════════════════════════════════════════════════════════
# B. 增量：更新 = 先删该 doc 全部旧块，再写（讲解第 2 节）
# ══════════════════════════════════════════════════════════════════
def reindex_doc(path, col):
    v = bump_version(path)
    col.delete(where={'doc_id': path})                 # ← 先删全部旧版本
    col.upsert(ids=[...], embeddings=[...], metadatas=[...])

def delete_doc(path, col):
    n = col.count(where={'doc_id': path})
    col.delete(where={'doc_id': path})
    write_tombstone(path)
    purge_derived(path)                                # 摘要 / 三元组 / 缓存
    assert col.count(where={'doc_id': path}) == 0, '删除必须可验证'
    return n

# ══════════════════════════════════════════════════════════════════
# C. 新鲜度：先测 p，再定周期（讲解第 3 节）
# ══════════════════════════════════════════════════════════════════
# SELECT COUNT(*) FILTER (WHERE updated_at > now() - interval '1 day')::float
#        / COUNT(*) AS p_daily FROM documents;
# L = max_lag_for_target(p_daily, target=0.05);  period = 2 * L（批量）
#   事件驱动必须配对账（每天一次）：
#     比对 source 的 (doc_id, content_sha) 与索引的，缺的补、多的删

# ══════════════════════════════════════════════════════════════════
# D. 迁移：影子索引 + 双写 + 原子切换（讲解第 4/5 节）
# ══════════════════════════════════════════════════════════════════
# 1) create_collection('kb-v7')          2) 全量回填（离线，可断点续跑）
# 3) 回填期间双写；双写失败**报警**，不静默丢弃
# 4) migration_gate()（练习 2）           5) 切 alias：kb-active -> kb-v7
# 6) 保留 kb-v6 至少 N 天；回滚 = 反向切 alias
#   读取方：每次请求读 alias，**不要在进程启动时缓存**（讲解第 5 节）

# ══════════════════════════════════════════════════════════════════
# E. 多租户（讲解第 6 节）
# ══════════════════════════════════════════════════════════════════
def search(q, *, tenant, k=5):        # tenant 必填关键字参数
    key = (tenant, q, k, INDEX_SPEC['index_id'])       # ← 缓存键必须含 tenant
    ...
#   大租户给独立 collection；小租户共享 + 必填过滤。

# ══════════════════════════════════════════════════════════════════
# F. 监控（讲解第 8 节）—— 全部不需要真值
# ══════════════════════════════════════════════════════════════════
# zero_result_rate{tenant}   ← **必须分租户**
# top1_score_quantiles       ← 模型腐烂的唯一线上信号
# citation_rate
# freshness_lag_seconds{p99} ← 与 SLA 比
# 门禁：确定性项阻断（空间数、SLA、某租户 100% 零结果、对账缺失），统计项报警
```

---

## 小结

| 结论 | 数字 / 判据 | 在哪一节 |
|---|---|---|
| 内容腐烂能局部修，结构与模型腐烂必须整体换 | 混版本索引的行为无法解释 | 讲解 1 |
| 「更新时只写新块」的症状是间歇性的 | 3 个措辞里 1 个返回旧值 | 第 2 节 |
| 删除必须断言删除条数 | 「删了 0 条」看起来像成功 | 第 2 节 |
| 过期文档比例 = $1-(1-p)^L$ | 与模拟偏差 < 0.02 | 第 3 节 |
| 均匀假设会低估过期答案率 | 本例低估 2 倍以上（π 与 p 正相关） | 第 3 节 |
| 事件驱动必须配定时对账 | 丢了的那一篇会永久过期 | 第 3 节 |
| 跨 embedding 空间的内积接近 0 | 同文本跨空间 < 0.1 vs 同空间改写 > 0.5 | 第 4 节 |
| 混版本索引里跨空间的块用自己的原文都查不到第一 | 等于那部分索引不可见，账单照付 | 第 4 节 |
| top-k 重叠率是观测量不是门禁 | 等于 1.0 时先怀疑配置没生效 | 第 4 节 / 练习 2 |
| 切换后旧进程会继续用旧索引 | 同一时刻不同实例返回不同结果 | 第 5 节 |
| 缓存键不含 tenant 就是一条泄漏路径 | 且在低流量测试里不出现 | 第 6 节 |
| 评测集绑 chunk_id 会造成假事故 | 换分块后 recall 掉到 0 | 第 7 节 |
| 零结果率必须分租户看 | 某租户 100% 时总体只有 25% | 第 8 节 |

**C70 完结。** 全课的一句话：
**RAG 的调试顺序是从左往右的——先确认答案在语料里（01）、
没被切断（02）、查询能碰到它（03）、需要几跳（04）、
并且一年后还是对的（05）。检索算法（C11）是这条链里最不容易出错的一环。**"""),
]
