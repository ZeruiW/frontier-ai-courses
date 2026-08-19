# -*- coding: utf-8 -*-
"""C58 模块 04 · 大规模挖掘基础设施。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03（不平衡 / 难例挖掘 / 触发策略）；C43（数据工程）与 C11（向量检索）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_mining_infrastructure.ipynb'),
    ("核心参考", "FAISS / HNSW 论文、Core-set active learning (Sener & Savarese)、感知哈希、VLM 自动标注相关工作"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("scale", "从 PB 到 500 张：挖掘基础设施要解决的问题", "".join([
        P("模块 03 解决的是「<strong>该不该回传这一帧</strong>」——那是车端的、逐帧的、在线的决策。本模块解决的是它的下游：<strong>几千万帧候选已经躺在云上了，怎么从里面挑出这一轮真正要标的那 500 张</strong>。这两件事经常被混为一谈，但它们的约束完全不同。"),
        TABLE(["", "车端触发（模块 03）", "云端挖掘（本模块）"], [
            ["决策对象", "单帧 / 单个片段", "<strong>整个候选池的一个子集</strong>"],
            ["能看到的信息", "只有当前帧与短时序", "<strong>全池的分布、标签、嵌入、历史</strong>"],
            ["主要约束", "算力与回传带宽", "<strong>标注预算与工程师时间</strong>"],
            ["优化目标", "命中率（触发的确实是难例）", "<strong>子集的边际价值</strong>（标完模型能涨多少）"],
            ["典型规模", "每车每天几百帧", "池子 10⁷–10⁹ 帧，选出 10³–10⁴"],
            ["失败形态", "触发率爆炸打爆带宽", "<strong>选出 1000 张同一个路口</strong>"],
        ]),
        P("最后一行是本模块的灵魂。<strong>触发器是逐帧独立工作的，它没有「已经回传过很多类似的了」这个概念</strong>——同一个隧道口的同一种逆光失效，一辆车经过一次就触发 200 帧，一个车队一天就是几万帧几乎一模一样的数据。它们全都是「真难例」，触发器没做错任何事，但把它们全标了，模型学到的东西约等于标 5 张。"),
        DUAL(
            "所以挖掘基础设施的核心命题只有一句：<strong>把「和这个 badcase 相似」和「彼此之间不相似」这两个要求同时满足</strong>。前者靠<span class=\"term\">embedding retrieval</span>（嵌入检索）与<span class=\"term\">scenario tagging</span>（场景标签）实现——它们负责<em>找得到</em>；后者靠去重与多样性采样实现——它们负责<em>不重复</em>。缺任一半，挖掘系统就退化成一个昂贵的随机采样器。",
            "形式化地说，这是一个带约束的子集选择问题：给定候选池 <code>P</code>、预算 <code>B</code>、以及一个（未知的）「标注后模型收益」函数 <code>V(S)</code>，求 <code>argmax_{S⊆P, cost(S)≤B} V(S)</code>。<em><code>V</code> 的真实形式要训完模型才知道，所以工程上永远是在优化它的代理（proxy）</em>：相似度、不确定性、覆盖度、类别缺口。<strong>本模块讲的每个组件，本质都是在给 <code>V</code> 造一个便宜且可计算的代理，并知道这个代理在什么时候会骗你。</strong>",
        ),
        CALLOUT("intuition", "一个能立刻用在面试里的说法：<strong>「数据挖掘系统的产出不是『找到了多少难例』，而是『每一块标注预算换来了多少模型提升』」</strong>。前者是虚荣指标——难例要多少有多少；后者才是这套基础设施存在的理由。<em>候选池是免费的，标注是贵的，所以整套系统的所有设计压力都集中在「筛选」这一步。</em>"),
    ])),

    ("embedding", "嵌入检索：以图搜图是长尾挖掘的主力工具", "".join([
        P("挖掘的最常见入口是这样一句话：<strong>「昨天路测在西二环隧道口漏了一块施工牌，帮我从池子里找 300 张类似的」</strong>。这句话里的「类似」没法用 SQL 表达——它不是「天气=雾」，而是「和<em>这一帧</em>长得像」。<span class=\"term\">embedding retrieval</span>（嵌入检索）就是把这句话变成可执行操作的方法。"),
        ASCII("""挖掘流水线的标准形态

  车队回传        ┌──────────────┐
  ──────────────► │  原始帧存储   │  (对象存储, 10^8 帧)
                  └──────┬───────┘
                         │  离线批处理：一次性算好、增量更新
                         ▼
       ┌─────────────────────────────────────────┐
       │  ① 嵌入 (embedding)   ② 场景标签 (tags)  │  ← 本模块的两个"索引面"
       │     backbone 特征         天气/光照/道路  │
       │     全局 pooling          遮挡/标志类别   │
       └────────┬──────────────────────┬─────────┘
                │                      │
        向量索引 (ANN)            结构化索引 (列存/数仓)
        "和这张像的"              "夜间+雨+隧道 的所有帧"
                │                      │
                └──────────┬───────────┘
                           ▼
                   候选集 (10^4 ~ 10^5)
                           │
                  ③ 去重 + 多样性采样      ← "别给我 1000 张同一路口"
                           │
                   待标集 (10^3)
                           │
                  ④ 预算分配 → 送标 → 质检
                           │
                  ⑤ 入库 + **版本与血缘**   ← 出问题能回溯到帧
                           ▼
                     训练集 v1.7.3""")
        ,
        P("这里的嵌入通常<strong>不是</strong>专门训的。最省事也最常用的做法是<strong>直接复用检测器 backbone 的中间特征</strong>：取 FPN 某一层做全局平均池化，得到 256–2048 维向量。它免费、和你的任务分布天然对齐（模型觉得像的，往往就是模型会犯同类错误的）。代价是：<em>它只反映模型「看到了什么」，模型看不见的东西（比如夜里那块本来就没检出的牌子）在嵌入里也不会体现</em>——这是嵌入检索的第一个系统性盲区。"),
        TABLE(["嵌入来源", "怎么拿", "优点", "盲区 / 代价"], [
            ["<strong>检测 backbone 特征</strong>", "FPN 层 GAP，免费顺手", "与任务分布对齐；零额外成本", "<strong>模型漏检的东西在嵌入里也是「空的」</strong>"],
            ["<strong>自监督 / CLIP 类通用嵌入</strong>", "跑一遍通用视觉模型", "语义丰富，跨任务可复用；支持<em>文本查图</em>", "与检测任务不完全对齐；要额外算力"],
            ["<strong>ROI 级嵌入</strong>（只对检测框抠图）", "对每个框单独编码", "<strong>精确到「这块牌子」</strong>，不被背景稀释", "只能找已检出的目标——<em>对漏检无效</em>"],
            ["<strong>场景级手工特征</strong>", "亮度直方图 / 边缘密度 / GPS", "极便宜、可解释", "表达力弱，只能做粗筛"],
        ]),
        DUAL(
            "「<strong>ROI 级 vs 全图级</strong>」是实践中要先想清楚的分叉。要挖「限速 60 和 80 被互相错分」的样本，用 ROI 级嵌入——因为你要找的是<em>牌子本身</em>长得像的；要挖「隧道口逆光整体失效」的场景，用全图级——因为你要找的是<em>环境</em>像的。<strong>用错粒度，检索出来的东西看着都对，但对模型没用。</strong>",
            "更根本的问题是<strong>嵌入检索对「漏检」这一类失效天生偏弱</strong>。ROI 嵌入需要先有框，漏检的样本压根没有框；全图嵌入虽然能用，但一整帧的全局特征被道路、天空、车辆主导，那块 12×12 像素的牌子对向量的贡献接近噪声。<em>实践中的对策是「用别的模态定位再检索」</em>：用高精地图里标注的标志位置反查该处的图像、用后帧检出的目标反向追溯前帧（<strong>目标从近处倒推回远处，正是 TSR 挖远距离漏检样本的标准姿势</strong>）。",
        ),
        CALLOUT("warn", "嵌入检索的<strong>质量必须被度量，而不是靠肉眼看几张图觉得「挺像」</strong>。最小可用的度量是：拿一批已知标签的帧做查询，看 top-k 里有多少条与查询帧属于同一场景/同类别（<code>precision@k</code>），并和「随机抽 k 张」的基线比。<em>如果 precision@10 只有随机基线的 2–3 倍，这个嵌入不值得建索引</em>——它省不下多少标注钱。notebook 里会实测这个比值。"),
    ])),

    ("ann", "向量索引：从暴力扫描到 IVF / HNSW / PQ", "".join([
        P("池子小的时候（&lt; 10⁶）暴力矩阵乘法就够了：<code>E @ q</code> 一次几十毫秒。<strong>但候选池是按车队规模线性增长的</strong>，到 10⁸ 量级时，暴力扫描一次查询要几十秒、内存放不下（10⁸ × 512 维 × 4 字节 = 200 GB）。<span class=\"term\">ANN</span>（approximate nearest neighbor，近似最近邻）索引就是用「牺牲一点召回换几十上百倍速度」来解这个问题。"),
        ASCII("""IVF（倒排文件）                        HNSW（分层可导航小世界）

  1. 先聚 nlist 个粗中心               上层：稀疏长边，快速跳转
     ●   ●   ●   ●                       ○────────────○
     │   │   │   │                       │            │
  2. 每个向量归到最近中心              中层：中等密度
     ┌─┴─┬─┴─┬─┴─┬─┴─┐                  ○──○────○────○
     │ ▪ │ ▪ │ ▪ │ ▪ │  倒排列表         │  │    │    │
     │ ▪ │ ▪ │ ▪ │   │                 底层：全部向量，短边
     └───┴───┴───┴───┘                  ○─○─○─○─○─○─○─○
  3. 查询时只扫 nprobe 个最近的列表
     nprobe=1  → 快、召回低              查询 = 从上往下贪心下降
     nprobe=全 → 退化成暴力扫描          每层走到局部最优再下一层

  代价模型：距离计算次数 ≈ nlist + nprobe/nlist · N
  → nlist=√N 时总代价约 2√N，比 N 小两三个数量级""")
        ,
        TABLE(["索引", "构建成本", "查询", "内存", "什么时候用"], [
            ["<strong>Flat（暴力）</strong>", "0", "O(N·D)", "全量", "<strong>N &lt; 10⁶，或作为 recall 的 ground truth</strong>"],
            ["<strong>IVF</strong>", "一次 k-means", "只扫 nprobe 个桶", "全量", "中等规模；<em>nprobe 给了一个可调的召回-延迟旋钮</em>"],
            ["<strong>HNSW</strong>", "较贵（建图）", "极快，召回高", "<strong>比 flat 还多</strong>（要存图）", "对延迟敏感、内存管够"],
            ["<strong>IVF-PQ</strong>", "k-means + 码本训练", "快", "<strong>压缩 8–64×</strong>", "10⁸ 级别，内存是硬约束时"],
            ["<strong>分片 + 粗筛</strong>", "按场景标签分区", "先标签过滤再向量检索", "按需加载", "<strong>工程上最实用</strong>：标签先砍掉 99%"],
        ]),
        DUAL(
            "最后一行值得单独说：<strong>真实系统里很少「对全池做向量检索」，而是先用结构化标签把范围砍到 1%，再在里面做向量检索</strong>。因为挖掘请求几乎总是带条件的——「夜间的、隧道里的、和这张像的」。<em>先过滤再检索，既省算力，检索质量也更高</em>（候选里没有大量无关场景来抢名额）。这也是下一节「场景标签」为什么值得单独建设的原因之一。",
            "但要注意<strong>「先过滤再检索」的召回陷阱</strong>：ANN 索引的 <code>nprobe</code> 是在<em>整个索引</em>上生效的，如果你的过滤条件命中的向量恰好分散在很多个 IVF 桶里，扫 nprobe 个桶可能一条都命中不到，返回空结果——而系统不会报错，只会「什么也没找到」。<em>正确做法是把高频过滤维度<strong>物化成分区</strong>（按天气/光照分别建索引），而不是建一个大索引再后置过滤</em>。<strong>「后置过滤导致召回塌陷」是向量检索系统最经典的静默故障。</strong>",
        ),
        MATH("\\text{cost}(\\text{IVF}) \\approx \\underbrace{n_{list}}_{\\text{粗量化}} + \\underbrace{\\frac{n_{probe}}{n_{list}}\\cdot N}_{\\text{扫倒排}}, \\qquad \\frac{\\partial \\text{cost}}{\\partial n_{list}} = 0 \\Rightarrow n_{list}^{\\star} = \\sqrt{n_{probe}\\cdot N}"),
        CALLOUT("intuition", "选索引其实没什么可纠结的，<strong>决策只有两个输入：池子多大、内存多少</strong>。10⁶ 以下别建索引（暴力最省心且是精确的）；10⁶–10⁸ 且内存够 → HNSW 或 IVF；超过 10⁸ 或内存不够 → 上 PQ 压缩。<em>真正要花心思的是「怎么把标签过滤和向量检索组合起来」，以及「怎么持续验证召回没有塌陷」</em>——这两件事没有现成方案，得自己建监控。"),
    ])),

    ("tagging", "场景标签体系：让数据变得可查询", "".join([
        P("嵌入检索回答「和这张像的」，<span class=\"term\">scenario tagging</span>（场景标签）回答另一半问题：<strong>「我们池子里到底有多少雪天+夜间+隧道口的数据？」「哪些场景我们几乎是空白？」</strong>。没有标签体系，数据池就是一个黑箱——你只能碰到问题了去捞，永远没法主动发现「这个场景我们从来没覆盖过」。<em>这条能力就是 JD 里 <strong>scenario tagging</strong> 那个词的实际含义。</em>"),
        H3("标签体系怎么设计：正交轴 + 受控词表"),
        P("好的标签体系有三个特征，缺一个用起来都别扭："),
        OL([
            "<strong>轴是正交的</strong>：天气 / 光照 / 道路类型 / 遮挡程度 / 标志类别 / 自车行为，各成一维。<em>「雨夜高速」这种复合标签不能当基本单位</em>——一旦复合，组合数爆炸且没法做交叉统计。",
            "<strong>每个轴是受控词表（controlled vocabulary）</strong>，取值封闭且互斥。自由文本标签在半年内一定会长出 <code>night</code> / <code>Night</code> / <code>夜间</code> / <code>low_light</code> 四种写法。",
            "<strong>标签自带来源与置信度</strong>：这条 <code>weather=fog</code> 是雨刷信号推的、规则推的、VLM 打的、还是人工标的？<em>不同来源的可信度差一个量级，做统计时必须能区分</em>。",
        ]),
        TABLE(["轴", "受控词表（示例）", "主要来源", "为什么这一轴必须有"], [
            ["weather", "clear / rain / fog / snow", "雨刷信号 + VLM", "决定图像退化的类型；<strong>雾天是 TSR 的经典失效场景</strong>"],
            ["lighting", "day / dusk / night / tunnel", "时间 + 大灯 + VLM", "<strong>隧道进出口的逆光是最难的一类</strong>，且时间戳推不出来"],
            ["road_type", "highway / urban / ramp / rural", "高精地图 / GPS", "决定标志的种类分布与出现频率"],
            ["occlusion", "none / partial / heavy", "标注或 VLM", "分桶评测的必需维度（模块 05 会用）"],
            ["sign_class", "GB 5768 类目", "检测器输出 + 人工", "<strong>长尾统计与预算分配的主键</strong>"],
            ["ego_event", "cruise / brake / takeover", "车端 CAN 信号", "关联到「接管前 10 秒」这类高价值片段"],
        ]),
        DUAL(
            "标签体系最大的价值不是「能查」，而是<strong>能算出「缺口矩阵」</strong>：把 <code>(场景, 标志类别)</code> 摆成一张二维表，每格填「训练集里有多少张 / 评测集里表现如何」，<em>空的和红的格子就是下一轮该挖的目标</em>。这张表是数据团队和感知团队之间最有效的沟通界面——它把「模型不太行」变成「<code>(night, tunnel) × construction</code> 只有 31 张，AP 0.34」。",
            "而它最大的工程风险是<strong>标签本身的漂移与不一致</strong>。同一个 <code>rain</code> 标签，去年是雨刷信号推的（覆盖全、精度低），今年换成 VLM 打的（精度高、语义变了：毛毛雨不再算 rain）。<em>于是「今年雨天数据变少了」这个结论完全是标签口径变化造成的假象</em>。<strong>所以标签必须版本化，且每次口径变更要么重刷全量、要么保留旧标签共存</strong>——这与本模块最后一节的数据血缘是同一件事。",
        ),
        CALLOUT("danger", "<p>一个真实会翻车的做法：<strong>用当前模型的输出当标签，再用这些标签去挖数据训下一版模型</strong>。比如用检测器输出的 <code>sign_class</code> 统计类别缺口——但检测器恰恰在稀有类上召回最差，于是稀有类的统计数字被系统性低估，<em>你会得出「这个类数据够了」的错误结论，然后再也不挖它</em>。<strong>这是数据闭环里最隐蔽的正反馈陷阱：模型的盲区会传染给数据系统，让盲区自我延续。</strong></p><p>对策：<em>关键统计维度上必须有一条不依赖当前模型的信息通路</em>——人工抽检、高精地图先验、或者独立的更大的教师模型。</p>", "模型的盲区会传染给数据系统"),
    ])),

    ("vlm_tag", "用 VLM 自动打标：现在的主流做法", "".join([
        P("标签体系设计完，问题就变成「<strong>10⁸ 帧，谁来打这些标签</strong>」。历史上有三条路，今天是三条路混用，但重心已经明显移动了。"),
        TABLE(["路线", "怎么做", "覆盖 / 精度", "成本", "适合的轴"], [
            ["<strong>① 元数据推断</strong>", "从 CAN 信号、时间戳、GPS、地图直接推", "覆盖 100%，精度参差", "<strong>≈ 0</strong>", "road_type、ego_event、粗粒度 lighting"],
            ["<strong>② 规则 / 小模型</strong>", "亮度直方图、雨滴检测器、专用分类头", "覆盖高，精度中", "低（一次推理）", "day/night、模糊度、曝光异常"],
            ["<strong>③ VLM 打标</strong>", "把帧喂给视觉语言模型，让它按受控词表输出结构化标签", "<strong>覆盖高、精度接近人工</strong>", "中（每帧几厘–几分钱）", "<strong>weather、occlusion、异常场景描述</strong>"],
            ["<strong>④ 人工标注</strong>", "标注员按规范打标", "精度最高", "<strong>高 100–1000×</strong>", "只用于<em>审计集</em>与仲裁"],
        ]),
        P("<strong>VLM 打标之所以在最近两年成为主流，是因为它把「加一个新标签轴」的成本从「训一个分类器」降到了「改一段 prompt」</strong>。以前想统计「画面里有没有施工锥桶」，要标几千张、训个模型、部署、维护；现在写一句 <code>是否存在施工锥桶？只答 yes/no</code> 就能刷全库。<em>这个成本结构的变化，才是「automated data mining workflow」这个词在今天的真实含义。</em>"),
        CODE("""# VLM 打标的工程形态：**强制结构化输出 + 受控词表 + 拒答选项**
PROMPT = '''你是自动驾驶数据标注器。只输出 JSON，不要解释。
字段与允许取值（必须严格从中选择）：
  weather:   ["clear","rain","fog","snow"]
  lighting:  ["day","dusk","night","tunnel"]
  occlusion: ["none","partial","heavy"]        # 指画面中交通标志被遮挡的最严重程度
  sign_present: true | false
  confidence: 0.0-1.0                          # 你对以上判断的整体把握
无法判断的字段填 "unknown"，不要猜。'''

# 三条必须做的工程约束：
#   1) 输出用 JSON schema 约束（不是靠 prompt 求它听话）
#   2) **保留 confidence 与 "unknown"** —— 强迫模型二选一会制造大量静默错误
#   3) 每批抽 200–500 帧送人工做**审计集**，算 agreement / Cohen's kappa
#      kappa < 0.6 就不要用这批标签做任何统计决策"""),
        DUAL(
            "VLM 打标最容易被忽视的一点：<strong>它的错误不是随机的，是成片的（systematic）</strong>。人工标注员会零星标错，VLM 会「把所有薄雾一致地判成 clear」。<em>随机错误在统计聚合时会被平均掉，系统性错误不会——它会把整个缺口矩阵的某一行整体挪位</em>。所以审计集不能只算总体准确率，必须<strong>按每个取值分别算召回</strong>，专门盯稀有取值（fog、tunnel、heavy）。",
            "第二点是<strong>成本必须做级联</strong>。10⁸ 帧全过 VLM，即使每帧 0.001 美元也是 10 万美元。标准做法是三级：<em>元数据能定的先定（免费，砍掉 60–80%）→ 规则/小模型再定一层 → 只有剩下的「不确定」样本送 VLM</em>。notebook 里会把这个级联的成本-精度账算出来：<strong>级联能把 VLM 调用量降到 30–40%，而总体准确率只比全量 VLM 低 1 个点左右</strong>。",
        ),
        CALLOUT("warn", "别用 VLM 标签直接当训练监督（伪标签），除非你非常清楚在做什么。<strong>VLM 打的是「场景标签」（用来<em>组织</em>数据），不是「任务标签」（用来<em>训练</em>模型）</strong>。前者错了只是挖数据挖偏一点，后者错了是直接往训练集里注入噪声——而模块 02 已经讲过，<em>噪声标签混进难例池会毁掉模型</em>。这条界线在工程上要用不同的字段、不同的表、不同的权限来物理隔离。"),
    ])),

    ("dedup", "去重与多样性采样：别回传 1000 张同一路口", "".join([
        P("现在候选集有了：嵌入检索给了 20000 张「和 badcase 像的」。但这 20000 张里，可能 15000 张来自同 60 段行车片段——<strong>因为触发器在一段路上会连续触发几百帧，而这几百帧几乎是同一张图</strong>。直接送标，等于花 20000 张的钱买 60 张的信息量。"),
        H3("第一层：近重复检测（near-duplicate detection）"),
        P("最便宜的手段是<span class=\"term\">perceptual hash</span>（感知哈希）。它把图像压成一个 64 位指纹，<strong>视觉上几乎一样的图会得到汉明距离很小的指纹</strong>，而且指纹是整数、可以建倒排、可以在几十亿量级上做。"),
        TABLE(["哈希", "怎么算", "对什么鲁棒", "对什么敏感"], [
            ["<strong>aHash</strong>（average）", "缩到 8×8 灰度，与均值比较取 0/1", "亮度整体缩放、轻微压缩", "<strong>对结构变化不够敏感</strong>，误合并多"],
            ["<strong>dHash</strong>（difference）", "缩到 9×8，比较相邻像素大小", "亮度与对比度变化", "轻微平移会翻转较多位"],
            ["<strong>pHash</strong>（DCT）", "取 DCT 低频系数与中位数比较", "<strong>最鲁棒</strong>：缩放、压缩、小幅变换", "计算稍贵"],
            ["<strong>嵌入聚类</strong>", "在向量空间上做半径聚类", "语义级近重复（同路口不同天）", "贵；阈值难定"],
        ]),
        P("<strong>工程上一般两层都用</strong>：先用感知哈希砍掉「像素级几乎相同」的帧（便宜，能砍掉大头），再用嵌入距离砍掉「语义上重复」的帧（比如同一个路口不同时间拍的 20 次）。<em>注意第二层要小心：同一路口的雨天和晴天不是重复，它们恰恰是你要的对比样本</em>——所以嵌入聚类去重必须在场景标签内部做，跨场景不去重。"),
        H3("第二层：多样性采样（core-set）"),
        P("去完重还剩 5000 张，预算只有 500 张，选哪 500 张？<strong>随机抽是有效的基线，但它会按池子的分布抽——池子里 70% 是晴天城区，抽出来也是 70% 晴天城区</strong>，而那恰恰是模型已经会的。<span class=\"term\">core-set selection</span>（核心集选择）换一个目标：<em>让选出的子集在特征空间里「覆盖」整个池子</em>。"),
        MATH("S^{\\star} = \\arg\\min_{S \\subseteq P,\\, |S|=k} \\ \\max_{x \\in P} \\ \\min_{s \\in S} d(x, s)"),
        P("这就是 <span class=\"term\">k-center</span> 问题：最小化「池子里任意一点到最近的被选点」的最大距离，也叫<strong>覆盖半径</strong>。它是 NP-hard，但有一个漂亮的贪心近似——<strong>每次选「离已选集合最远的那个点」</strong>，可以证明结果不超过最优解的 2 倍。实现只有 5 行，且天然把稀有场景选进来（<em>稀有场景在特征空间里就是「离大家都远」的点</em>）。"),
        DUAL(
            "贪心 k-center 的直觉非常好用：<strong>第一步选任意点，之后每一步都问「现在覆盖得最差的是哪块区域」，然后往那块区域插一根钉子</strong>。它的行为和随机采样恰好相反——随机采样按密度分配名额，k-center 按<em>空白</em>分配名额。所以在长尾数据上，k-center 选出的子集里稀有场景的比例会远高于池子的自然比例。",
            "但它有一个致命弱点必须知道：<strong>k-center 对离群点（outlier）极度敏感</strong>。一帧因为相机故障产生的全绿图像，在特征空间里离所有点都很远，于是它一定会被选中——而且它旁边的每个噪声帧都会被接着选中。<em>结果是预算被一批坏数据吃掉</em>。<strong>对策是先做离群剔除（按 k 近邻密度过滤掉密度极低的点），或者改用「聚类均衡采样」</strong>：先聚类，再从每个簇里按 <code>√簇大小</code> 配额抽——它没有 k-center 那么激进，但对噪声稳健得多，是工业上更常见的选择。",
        ),
        CALLOUT("intuition", "把这一节压成一句可迁移的话：<strong>相似度决定「找什么」，多样性决定「买什么」</strong>。检索环节要的是高相似（越像 badcase 越好），采样环节要的是低相似（彼此越不像越好）。<em>把这两个阶段的目标搞混——比如直接把检索的 top-500 送标——就是「回传 1000 张同一路口」的根本原因。</em>notebook 里会量化这个差别：同样 500 张预算，core-set 覆盖的场景组合数比 top-k 检索高一倍以上。"),
    ])),

    ("budget", "标注预算分配：把钱花在最缺的格子上", "".join([
        P("最后一步是分钱。假设这一轮有 8 万元标注预算，缺口矩阵上有 40 个格子——<code>(场景, 标志类别)</code>——每个格子的现状、难度、单价都不同。<strong>「平均分」和「哪个 AP 最低给哪个」都是错的</strong>，前者浪费在已经饱和的格子上，后者会把钱全砸进一个可能根本救不回来的格子。"),
        TABLE(["格子的属性", "含义", "怎么获得", "在分配里的作用"], [
            ["<code>n_have</code>", "训练集里该格已有多少样本", "查数据仓库", "决定<strong>边际收益</strong>（已经很多 → 再加没用）"],
            ["<code>ap_now</code>", "评测集上该格当前 AP", "分桶评测（模块 05）", "低 AP 才有提升空间"],
            ["<code>w</code>（重要度）", "该格的安全权重 × 出现频率", "产品/安全团队给", "<strong>漏检「停车让行」和漏检「景点指示」不是一回事</strong>"],
            ["<code>cost</code>", "该格每张的标注单价", "标注供应商报价", "夜间/遮挡样本标注更慢更贵，<em>可差 3–5 倍</em>"],
            ["<code>n_avail</code>", "候选池里该格最多能挖出多少", "查候选池", "<strong>硬上限</strong>——池子里没有就是没有"],
        ]),
        P("把「标注 n 张后该格的收益」建模成一条<strong>饱和曲线</strong>（这正是模块 05 边际收益曲线的离线版本）："),
        MATH("V_c(n) = w_c\\left(1 - e^{-n/\\tau_c}\\right), \\qquad \\text{边际收益率} = \\frac{\\partial V_c/\\partial n}{\\text{cost}_c} = \\frac{w_c}{\\tau_c\\,\\text{cost}_c}e^{-n/\\tau_c}"),
        P("于是分配算法就是一句话：<strong>反复把下一块钱投给「当前边际收益率最高」的格子，直到预算用完</strong>。因为 <code>V_c</code> 是凹函数，这个贪心是最优的（这是经典的水位填充 / water-filling 结构）。它自动产生了三个符合直觉的行为：<em>样本已经很多的格子边际收益率低，自动不给钱；重要度高的格子多给；标注单价贵的格子会被折价</em>。"),
        DUAL(
            "这个模型的价值不在于它的数学，而在于<strong>它逼着你把「拍脑袋」变成三个可以被质疑的数字</strong>：这个格子多重要（<code>w</code>）、它离饱和还有多远（<code>τ</code>）、标一张多少钱（<code>cost</code>）。<em>面试里如果你能说出「我们把标注预算分配写成了一个带成本的贪心，w 由安全等级决定，τ 用历史边际收益曲线拟合」，这比任何算法细节都更能体现工程成熟度。</em>",
            "但要诚实地承认它的两个漏洞。第一，<code>τ_c</code> 是拟合出来的，<strong>新场景没有历史数据就没有 τ</strong>——冷启动只能先给一个探索性的小配额（比如 200 张）跑一轮，拿到真实的边际收益点再进入优化。第二，<strong>格子之间不独立</strong>：给「夜间限速牌」加数据，「夜间禁令牌」也会受益（共享的是夜间的低光特征）。<em>独立性假设会让贪心高估分散投资的价值</em>。实践中的粗暴修正是按场景轴（而不是场景×类别）分配，把相关性最强的格子先合并。",
        ),
        CALLOUT("warn", "<strong>别忘了给「保持集」留预算</strong>。所有钱都投给当前最缺的格子，会导致评测集与训练集的分布一起漂移——<em>半年后你发现所有场景的 AP 都在涨，但路测体验没变好，因为评测集也被这套逻辑喂成了「当前最缺场景」的集合</em>。规范做法：每轮预算里固定切出 10–15%，按<strong>部署真实分布</strong>随机采样去标，专门用来维护一个不随挖掘策略漂移的基准评测集。这条与模块 05 的「回归门禁」是一套的。"),
    ])),

    ("lineage", "数据版本与血缘：出了问题能回溯到帧", "".join([
        P("挖掘系统跑起来之后，最先出事的往往不是算法，是<strong>「这个模型到底是用哪些数据训的」没人说得清</strong>。当线上出现一类新的误检、怀疑是某批标注有问题时，你需要在几小时内回答三个问题——而没有血缘系统的话，这三个问题都答不了。"),
        ASCII("""数据血缘图（lineage）：每条边都必须可查

  mine_job#412 ──produces──► candidate_set/2026-07-03/tunnel_fp
       │  查询: emb_knn(seed=frame_88e1a, k=20000) & tags.lighting=tunnel
       │  索引版本: ivf_v3   嵌入模型: det_backbone@f19c2
       ▼
  dedup+coreset ──produces──► label_task#889  (1,204 帧)
       │  phash_thresh=6, coreset_k=1200, seed=7
       ▼
  标注供应商 A ──produces──► **batch_2026w27_tunnel**  (1,204 帧, 质检通过率 0.94)
       │                          │
       │                          ├──used_by──► dataset_v1.7.2  (+ v1.7.1 全量)
       │                          │                  │
       │                          │                  └──trains──► model_r38  ──► **已上车**
       │                          └──used_by──► dataset_v1.7.3 ──► model_r41 (灰度中)
       ▼
  反向查询："batch_2026w27_tunnel 标错了" → 受影响: dataset v1.7.2/v1.7.3
                                          → 受影响模型: model_r38(**线上**), r41
                                          → 决策: r38 回滚 or 热修?""")
        ,
        TABLE(["要回答的问题", "需要记录什么", "不记录的后果"], [
            ["<strong>这个模型用了哪些数据？</strong>", "model → dataset 版本 → batch 列表（含父数据集的递归展开）", "改了数据却不知道，指标变化无法归因"],
            ["<strong>这批数据是怎么挖来的？</strong>", "挖掘任务的查询、种子帧、索引版本、<strong>嵌入模型版本</strong>、去重与采样参数与随机种子", "复现不了；也说不清挖掘策略是否引入了偏差"],
            ["<strong>这批数据出问题了，谁受影响？</strong>", "batch → dataset → model 的<strong>反向索引</strong>，且要能递归传播", "只能全量重训「以防万一」，代价极高"],
            ["<strong>评测集和训练集有没有重叠？</strong>", "帧级唯一 ID + <strong>clip 级</strong>归属", "<strong>同一段路的相邻帧分别进训练和评测 → 指标虚高</strong>"],
        ]),
        DUAL(
            "最后一行是数据闭环里最常见、也最贵的事故：<strong>数据泄漏（leakage）</strong>。按帧随机划分训练/验证集，会让同一个 clip 的第 100 帧进训练、第 101 帧进验证——<em>它们几乎是同一张图</em>。于是验证 AP 虚高 5–15 个点，而且是<strong>系统性的、稳定的、看不出来的</strong>虚高。<strong>划分必须按 clip（更严格是按「路段 + 日期」）而不是按帧</strong>，这条在 TSR 上尤其致命，因为一块标志会在几十帧里连续出现。",
            "实现上不需要上重型工具。<strong>最小可用血缘 = 三张表加一条纪律</strong>：<code>batch</code> 表（一批标注的元数据 + 产出它的挖掘任务参数）、<code>dataset</code> 表（版本 → 包含哪些 batch，含父版本）、<code>run</code> 表（训练任务 → 用了哪个 dataset 版本 + 代码 commit）。纪律是：<em>训练脚本不接受「数据目录路径」，只接受「数据集版本号」</em>。<strong>把不可追溯的用法在接口层面禁掉，比要求所有人记得填表可靠得多</strong>——这与 C52 讲的「用产物的存在性编码验证已通过」是同一个模式。",
        ),
        CALLOUT("danger", "<p>一个必须提前设计的字段：<strong>嵌入模型的版本</strong>。挖掘用的嵌入来自某个 backbone；半年后 backbone 换了，新算的嵌入和索引里的旧嵌入<em>不在同一个空间</em>。此时检索会返回语义上毫无关系的结果，<strong>而且不会报错</strong>——相似度分数看起来一切正常（0.8、0.7……），只是含义全变了。</p><p>症状是「最近挖出来的数据质量突然变差，但说不上哪里不对」。<em>对策：索引必须绑定嵌入模型版本，版本不匹配直接拒绝查询；换 backbone 就重建全量索引（这是一笔要提前排期的算力预算）。</em></p>", "换 backbone = 全量重建索引"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("挖掘基础设施是工程味最重的一环，但它有几个真问题至今没有好答案，值得在面试里作为「我知道边界在哪」的信号讲出来。"),
        UL([
            "<strong>子集选择的目标函数依然是代理</strong>。core-set 优化的是特征空间覆盖，不确定性优化的是模型分歧，但真正想优化的是「标完之后模型涨多少」。<em>影响函数（influence function）、数据 Shapley、datamodels 这条线试图直接估计单条数据对最终指标的贡献</em>，但计算代价在检测任务与千万级数据上仍然不现实。目前工业界的共识是：<strong>用多个便宜代理的组合（相似 + 不确定 + 多样 + 类别缺口），而不是追求一个精确代理</strong>。",
            "<strong>批量主动学习的组合效应</strong>。逐条选择的最优性，在「一次选 1000 条」时完全不成立——单看每条都很有价值的 1000 条，可能高度冗余。<em>批量场景下的次模优化（submodularity）、行列式点过程（DPP）提供了理论工具</em>，但在高维嵌入与巨大候选池上的可扩展实现仍是开放问题。",
            "<strong>VLM 标注的可靠性度量</strong>。VLM 打标已经是主流，但「什么时候可以信它、信到什么程度」缺少标准方法。<em>自一致性（多次采样投票）、多模型交叉、置信度校准</em>都在被试，但 VLM 的置信度本身就是出了名的不可靠，且错误是成片而非随机的——这让传统的抽样审计效率大打折扣。",
            "<strong>合成数据在闭环里的位置</strong>。生成模型可以「造」出雪夜隧道口的施工牌，成本远低于去挖真实数据。<em>但合成数据的域差会不会把模型带偏、合成数据该占多大比例、怎么评估合成数据的「有效性」</em>，目前都只有经验答案。<strong>一个被反复验证的结论是：合成数据擅长补「几何/布局」的稀缺，不擅长补「传感器与光学退化」的稀缺</strong>——而 TSR 的难点恰恰大量属于后者。",
            "<strong>挖掘策略引入的分布偏移</strong>。挖掘系统按「模型现在的弱点」选数据，训练集就会持续偏离部署真实分布。<em>长期迭代后，训练分布是「历次弱点的并集」，与真实路况分布相去甚远</em>，这会以什么方式伤害模型（校准变差？对常见场景过拟合？）目前缺少系统研究，工程上只能靠「固定比例的随机采样」来对冲。",
            "<strong>跨车队/跨区域的数据可迁移性</strong>。欧洲车队挖到的雨夜数据能多大程度上帮到中国路况？<em>标志体系不同、道路结构不同、相机与 ISP 不同</em>——「数据可迁移性的度量」还没有比「拿去训一遍看结果」更好的方法，而这恰恰是最贵的方法。",
        ]),
        CALLOUT("paper", "必读：Sener &amp; Savarese, <em>Active Learning for Convolutional Neural Networks: A Core-Set Approach</em>（ICLR 2018，k-center 贪心的理论与实证，本模块 core-set 一节的来源）；Johnson et al., <em>Billion-scale similarity search with GPUs</em>（FAISS，IVF/PQ 的工程细节）；Malkov &amp; Yashunin, <em>Efficient and robust approximate nearest neighbor search using HNSW graphs</em>；Koh &amp; Liang, <em>Understanding Black-box Predictions via Influence Functions</em>（数据价值估计这条线的起点）；Ghorbani &amp; Zou, <em>Data Shapley</em>；Ilyas et al., <em>Datamodels</em>；Kirsch et al., <em>BatchBALD</em>（批量主动学习的冗余问题）。工程侧建议读 Tesla 与 Waymo 公开分享里关于 data engine / scenario mining 的部分，以及 DVC / LakeFS / Delta Lake 的数据版本模型。相邻课程：C43（数据工程与血缘）、C11（向量检索）、C00（VLM）、C58 模块 03（触发）与 05（闭环验证）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 大规模挖掘基础设施（嵌入检索 / ANN 索引 / 场景打标 / 去重与多样性 / 预算分配 / 血缘）

目标：把「车队每天回传几十 TB，标注预算只够几千张」这个真问题，拆成五个可以写代码解决的子问题，
并亲手实现每一个。

路线：合成候选池 → **嵌入检索**（找和 badcase 像的）→ IVF 索引的召回-代价旋钮 →
**感知哈希去重** → **core-set 贪心多样性采样** → 元数据/规则/**VLM 级联打标** →
**标注预算分配** → ✏️ 练习（MMR / 分层配额 / 近重复分组 / 数据血缘）→ 📖 答案 → 🧪 工程胶囊。

本 notebook 你会亲手实现：
- 余弦 kNN 检索 + `precision@k` 评估，并量化「不做 L2 归一化」的代价
- IVF 倒排索引（k-means 粗量化 + nprobe），画出**召回 vs 距离计算次数**的旋钮
- aHash 感知哈希 + 贪心去重，量化 clip 内 / clip 间的汉明距离分布
- k-center 贪心 core-set 选择，对比随机采样与 top-k 检索的**覆盖度**
- 元数据规则 + 模拟 VLM 打标 + **级联**，算清成本-精度账（含逐取值召回与 Cohen's kappa）
- 带成本的贪心**标注预算分配**，与平均分 / 缺口最大优先做对比

> 心智模型：**相似度决定「找什么」，多样性决定「买什么」。
> 把这两个阶段的目标搞混，就是「回传 1000 张同一路口」的根本原因。**"""),

    md("""## 1 · 合成一个车队候选池

规则：每个 <strong>clip</strong>（一段连续行车）有固定的（天气, 光照, 道路, 标志类别），
clip 内 3–8 帧几乎相同（这就是近重复的来源）。嵌入 = 域中心 + 类别中心 + 噪声。
另外**注入 10 段「雾天隧道口施工牌」**——这是我们这一轮要挖的失效场景。"""),
    code("""import numpy as np, itertools, collections, math, json
rng = np.random.default_rng(58)

WEATHER = ['clear', 'rain', 'fog', 'snow']
LIGHT   = ['day', 'dusk', 'night', 'tunnel']
ROAD    = ['highway', 'urban', 'ramp']
SIGN    = ['speed_60', 'speed_80', 'stop', 'no_left', 'construction']
D = 32                                    # 嵌入维度（真实系统 256~2048）

dom_center  = {k: rng.normal(size=D) for k in itertools.product(WEATHER, LIGHT)}
sign_center = {s: rng.normal(size=D) for s in SIGN}

def l2norm(x):
    return x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)

frames = []
def add_clip(cid, w, l, r, s):
    base = 0.9 * dom_center[(w, l)] + 1.0 * sign_center[s] + 0.35 * rng.normal(size=D)
    bg = rng.normal(size=(4, 4)) * 0.22          # 每个 clip 独有的背景（渲染时用）
    for _ in range(int(rng.integers(3, 9))):     # clip 内 3~8 帧 = 近重复
        frames.append(dict(clip=cid, weather=w, light=l, road=r, sign=s, bg=bg,
                           emb=base + 0.06 * rng.normal(size=D),
                           jit=rng.normal(size=2) * 0.6))

N_CLIPS = 380
for c in range(N_CLIPS):
    add_clip(c, WEATHER[rng.choice(4, p=[.70, .15, .09, .06])],
                LIGHT[rng.choice(4,   p=[.58, .16, .21, .05])],
                ROAD[rng.choice(3,    p=[.35, .55, .10])],
                SIGN[rng.choice(5,    p=[.44, .26, .15, .10, .05])])
TARGET = ('fog', 'tunnel', 'construction')       # ← 本轮要挖的失效场景
for c in range(N_CLIPS, N_CLIPS + 10):
    add_clip(c, TARGET[0], TARGET[1], 'highway', TARGET[2])

E = l2norm(np.array([f['emb'] for f in frames]))  # **先 L2 归一化**：点积 = 余弦
N = len(frames)
clip_of = np.array([f['clip'] for f in frames])
print(f'候选池: {N} 帧 / {N_CLIPS + 10} 个 clip，嵌入维度 {D}')

cnt = collections.Counter((f['weather'], f['light']) for f in frames)
print('\\n最常见 4 个 (天气,光照) 组合:')
for k, v in cnt.most_common(4):
    print(f'  {str(k):<22s} {v:5d} 帧  {v / N:6.1%}')
tail = set(k for k, v in cnt.items() if v / N < 0.02)
print(f'\\n占比 <2% 的长尾组合: {len(tail)} 个，合计只占 {sum(cnt[k] for k in tail) / N:.1%}')
assert N > 1500 and len(tail) >= 3
print('✅ 这就是长尾：头部两三个组合占掉一半以上，几十个尾部组合分剩下的零头')"""),

    md("""## 2 · 嵌入检索：找「和这个 badcase 长得像的」

评估必须**排除查询帧自己所在的 clip**——否则等于自问自答（同 clip 的帧几乎是同一张图）。
`precision@k` 要和「随机抽 k 张」的基线比，**看的是倍数，不是绝对值**。"""),
    code("""def knn(q, X, k=10, banned=None):
    '''余弦 kNN。X 已 L2 归一化 -> 点积即余弦相似度。'''
    sims = X @ q
    if banned is not None:
        sims = sims.copy(); sims[banned] = -np.inf
    k = min(k, int(np.isfinite(sims).sum()))
    idx = np.argpartition(-sims, k - 1)[:k]
    return idx[np.argsort(-sims[idx])], sims

def cell(f):                       # 场景「格子」= (天气, 光照, 标志类别)
    return (f['weather'], f['light'], f['sign'])

qi = int(np.where(clip_of == N_CLIPS)[0][0])          # 一个 badcase：雾天隧道口的施工牌
banned = clip_of == frames[qi]['clip']                # **排除自己那一段**
rel = np.array([cell(f) == cell(frames[qi]) for f in frames]) & (~banned)
base_rate = float(rel.mean())
order, _ = knn(E[qi], E, k=30, banned=banned)
hit = rel[order]

print('badcase 查询帧:', {k: frames[qi][k] for k in ['clip', 'weather', 'light', 'road', 'sign']})
print(f'池中同格子且不同 clip 的帧: {int(rel.sum())} / {N}  -> 随机基线 {base_rate:.2%}\\n')
for k in [5, 10, 20, 30]:
    print(f'  precision@{k:<3d} = {hit[:k].mean():6.1%}   （随机基线 {base_rate:.2%}，'
          f'提升 {hit[:k].mean() / base_rate:5.1f}×）')
n_clip_top = len(set(clip_of[order].tolist()))
print(f'\\n⚠️  top-30 只来自 {n_clip_top} 个不同的 clip —— 检索**天然会扎堆**，')
print('    直接把 top-k 送标就是「1000 张同一路口」。这正是第 4、5 节要解决的问题。')
assert hit[:10].mean() > 10 * base_rate, '嵌入检索应把命中率提升一个数量级以上'
assert n_clip_top < 15
print('✅ 以图搜图把命中率提升了一个数量级 —— 这是长尾挖掘的主力工具')
print('⚠️  合成数据是干净可分的，真实系统的 precision@10 通常只有 0.3~0.6；')
print('    **要看的是「比随机基线高多少倍」，而不是绝对值**。低于 3× 就别建索引了。')"""),

    code("""# ⚠️ 不做 L2 归一化的代价：裸内积会被「向量模长大」的帧劫持
scale = np.exp(rng.normal(0, 0.7, size=N))[:, None]   # 不同曝光/不同层输出 -> 模长差异
E_raw = E * scale

qs = rng.choice(N, 200, replace=False)
p_cos, p_dot = [], []
for q_ in qs:
    b_ = clip_of == frames[q_]['clip']
    r_ = np.array([cell(f) == cell(frames[q_]) for f in frames]) & (~b_)
    if r_.sum() < 5:
        continue
    o1, _ = knn(E[q_], E, k=10, banned=b_)
    sraw = E_raw @ E_raw[q_]; sraw[b_] = -np.inf
    o2 = np.argsort(-sraw)[:10]
    p_cos.append(r_[o1].mean()); p_dot.append(r_[o2].mean())

print(f'查询数 {len(p_cos)}')
print(f'  余弦（先 L2 归一化）  precision@10 = {np.mean(p_cos):.2%}')
print(f'  裸内积（不归一化）    precision@10 = {np.mean(p_dot):.2%}')
assert np.mean(p_cos) > 1.5 * np.mean(p_dot)
print('\\n⚠️  裸内积的排序 = 模长 × 余弦。查询帧的模长对所有候选是常数，')
print('    所以排序被**候选的模长**主导 —— 高亮度/高响应的帧无脑排前面。')
print('✅ 建索引前一定先 L2 归一化（或用真正的 L2 距离），这是零成本的一行代码。')"""),

    md("""## 3 · 向量索引：IVF 的「召回 vs 代价」旋钮

`nprobe` 是这个数据结构最重要的参数：它把「扫多少数据」变成一个**连续可调的旋钮**。
挖掘任务通常可以接受 0.9 的召回换 10× 的速度——**但这个取舍必须被量化，而不是拍脑袋**。"""),
    code("""def kmeans_cos(X, k, iters=20, seed=0):
    '''球面 k-means：粗量化器。'''
    r = np.random.default_rng(seed)
    C = X[r.choice(len(X), k, replace=False)].copy()
    for _ in range(iters):
        a = np.argmax(X @ C.T, axis=1)
        for j in range(k):
            m = (a == j)
            if m.any():
                C[j] = l2norm(X[m].mean(0))
    return C, np.argmax(X @ C.T, axis=1)

NLIST = 64                                   # 经验值 nlist ≈ sqrt(N)
C, assign = kmeans_cos(E, NLIST, seed=1)
lists = {j: np.where(assign == j)[0] for j in range(NLIST)}

def ivf_search(q, nprobe, k=10):
    cs = np.argsort(-(C @ q))[:nprobe]        # ① 先找最近的 nprobe 个粗中心
    cand = np.concatenate([lists[j] for j in cs])
    sims = E[cand] @ q                        # ② 只在这几个倒排列表里精算
    return cand[np.argsort(-sims)[:k]], len(cand) + NLIST   # 距离计算次数

QS = rng.choice(N, 80, replace=False)
gt = {i: set(knn(E[i], E, k=10)[0].tolist()) for i in QS}    # 暴力扫描的 ground truth
res = {}
print(f'{"nprobe":>7s} {"recall@10":>11s} {"距离计算次数":>13s} {"占暴力扫描":>11s}')
for npb in [1, 2, 4, 8, 16, NLIST]:
    rec = [len(set(ivf_search(E[i], npb)[0].tolist()) & gt[i]) / 10 for i in QS]
    cost = [ivf_search(E[i], npb)[1] for i in QS]
    res[npb] = (float(np.mean(rec)), float(np.mean(cost)))
    print(f'{npb:>7d} {res[npb][0]:>11.1%} {res[npb][1]:>13.0f} {res[npb][1] / N:>11.1%}')

assert res[1][0] < res[8][0], 'nprobe 越大召回越高'
assert res[NLIST][0] == 1.0, 'nprobe = nlist 时退化成暴力扫描，召回必然 1.0'
assert res[1][1] < 0.2 * N, 'nprobe=1 的代价应远小于暴力扫描'
print('\\n✅ nprobe 给了一个**连续可调的召回-代价旋钮**：')
print(f'   nprobe=1 用 {res[1][1] / N:.0%} 的算力拿到 {res[1][0]:.0%} 的召回。')
print('⚠️  但注意：如果先用标签过滤再检索，命中的向量可能分散在很多桶里 ->')
print('    扫 nprobe 个桶一条也命中不到，**返回空结果且不报错**。')
print('    正确做法是把高频过滤维度**物化成分区**（按天气/光照分别建索引）。')"""),

    md("""## 4 · 感知哈希：砍掉像素级近重复

先把每帧渲染成 32×32 的灰度「图像」（同 clip 内只差亚像素抖动），
再用 **aHash**（缩到 8×8，与均值比较取 0/1）得到 64 位指纹。"""),
    code("""def render(f, size=32):
    '''把一帧渲染成灰度图：标志盘面 + clip 特有背景 + 光照增益。'''
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    cx, cy = size / 2 + f['jit'][0], size / 2 + f['jit'][1]
    rad = {'stop': 7.0, 'speed_60': 10.0, 'speed_80': 10.0,
           'no_left': 8.5, 'construction': 9.2}[f['sign']]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disc = r < rad
    img = np.where(disc, 0.95, 0.18)
    if   f['sign'] == 'speed_60':     img[disc & (xx < cx)] = 0.25
    elif f['sign'] == 'speed_80':     img[disc & (xx > cx)] = 0.25
    elif f['sign'] == 'no_left':      img[disc & (np.abs((xx - cx) + (yy - cy)) < 1.8)] = 0.25
    elif f['sign'] == 'construction': img[disc & (((xx - cx) * (yy - cy)) > 0)] = 0.35
    img = img + np.kron(f['bg'], np.ones((size // 4, size // 4)))
    gain = {'day': 1.0, 'dusk': 0.72, 'night': 0.38, 'tunnel': 0.55}[f['light']]
    return np.clip(img * gain, 0.0, 1.0)

def ahash(img):
    '''aHash：32x32 -> 8x8 块均值 -> 与整体均值比较 -> 64 bit。'''
    s = img.reshape(8, 4, 8, 4).mean(axis=(1, 3))
    return (s > s.mean()).ravel()

H = np.array([ahash(render(f)) for f in frames])
by_clip = collections.defaultdict(list)
for i, c in enumerate(clip_of):
    by_clip[c].append(i)

w_d = [int(np.count_nonzero(H[a] != H[b]))
       for idxs in by_clip.values() for a, b in itertools.combinations(idxs, 2)]
c_d = []
for _ in range(4000):
    i, j = rng.integers(0, N, 2)
    if clip_of[i] != clip_of[j]:
        c_d.append(int(np.count_nonzero(H[i] != H[j])))
print(f'clip **内**   汉明距离 均值 {np.mean(w_d):5.2f}  （{len(w_d)} 对）')
print(f'clip **之间** 汉明距离 均值 {np.mean(c_d):5.2f}  5% 分位 {np.percentile(c_d, 5):.0f}')
assert np.mean(w_d) < np.mean(c_d) / 4, '同 clip 的帧应显著更像'

def dedup_greedy(H, thresh):
    '''贪心：与已保留的任何一帧汉明距离 <= thresh 就丢弃。'''
    keep = []
    for i in range(len(H)):
        if all(np.count_nonzero(H[i] != H[j]) > thresh for j in keep):
            keep.append(i)
    return keep

print(f'\\n{"阈值":>5s} {"保留帧数":>9s} {"压缩率":>8s} {"仍有代表的 clip":>16s}')
kept6 = None
for T in [0, 4, 6, 8]:
    k = dedup_greedy(H, T)
    if T == 6:
        kept6 = k
    print(f'{T:>5d} {len(k):>9d} {len(k) / N:>8.1%} {len(set(clip_of[k].tolist())):>10d} / {len(by_clip)}')
assert len(kept6) < N / 3 and len(set(clip_of[kept6].tolist())) > 0.8 * len(by_clip)
print('\\n✅ 阈值 6 把候选池砍到 1/5 以下，而 85%+ 的 clip 仍有代表 ——')
print('   **丢掉的几乎全是「同一段路的相邻帧」，信息量损失极小、标注费省了 80%。**')
print('⚠️  阈值是要调的：太小压不动，太大会把「同一路口的雨天和晴天」也合并掉')
print('   —— 而那恰恰是你想要的对比样本。所以**跨场景标签不去重**。')"""),

    md("""## 5 · core-set 贪心：把预算花在覆盖空白上

k-center 贪心：每次选「离已选集合最远的点」。目标是最小化**覆盖半径**
（池中任意点到最近被选点的最大距离）。它的行为和随机采样恰好相反——
随机按**密度**分配名额，k-center 按**空白**分配名额。"""),
    code("""def kcenter_greedy(X, k, start=0):
    sel = [start]
    d = 1.0 - X @ X[start]                     # 到已选集合的最小余弦距离
    radii = [float(d.max())]
    for _ in range(k - 1):
        i = int(np.argmax(d))                  # ← 覆盖得最差的那个点
        sel.append(i)
        d = np.minimum(d, 1.0 - X @ X[i])
        radii.append(float(d.max()))
    return np.array(sel), np.array(radii)

def coverage_radius(X, sel):
    return float(np.min(1.0 - X @ X[np.asarray(sel)].T, axis=1).max())

def bucket_cov(sel):
    return len({(frames[i]['weather'], frames[i]['light']) for i in sel})

def tail_frac(sel):
    return float(np.mean([(frames[i]['weather'], frames[i]['light']) in tail for i in sel]))

K = 80                                          # 本轮标注预算：80 张
sel_cs, radii = kcenter_greedy(E, K)
sel_topk, _ = knn(E[qi], E, k=K)                # 对照：直接送检索 top-K
rand_r = [coverage_radius(E, rng.choice(N, K, replace=False)) for _ in range(30)]
rand_b = [bucket_cov(rng.choice(N, K, replace=False)) for _ in range(30)]
rand_t = [tail_frac(rng.choice(N, K, replace=False)) for _ in range(30)]

print(f'{"选法":<16s} {"覆盖半径":>10s} {"覆盖场景组合":>14s} {"不同 clip":>10s} {"长尾占比":>10s}')
rows = [('core-set 贪心', coverage_radius(E, sel_cs), bucket_cov(sel_cs),
         len(set(clip_of[sel_cs].tolist())), tail_frac(sel_cs)),
        ('随机采样(均值)', float(np.mean(rand_r)), float(np.mean(rand_b)), None, float(np.mean(rand_t))),
        ('检索 top-K', coverage_radius(E, sel_topk), bucket_cov(sel_topk),
         len(set(clip_of[sel_topk].tolist())), tail_frac(sel_topk))]
for nm, rad, bc, nc, tf in rows:
    print(f'{nm:<16s} {rad:>10.3f} {bc:>14.1f} {str(nc) if nc else "-":>10s} {tf:>10.1%}')
print(f'（池子里长尾场景的自然占比 = {np.mean([(f["weather"], f["light"]) in tail for f in frames]):.1%}）')

assert coverage_radius(E, sel_cs) < 0.5 * np.mean(rand_r), 'core-set 的覆盖半径应显著更小'
assert bucket_cov(sel_cs) > bucket_cov(sel_topk), 'core-set 覆盖的场景组合应多于 top-K 检索'
assert tail_frac(sel_cs) > 2 * np.mean([(f['weather'], f['light']) in tail for f in frames])
print('\\n✅ 同样 80 张预算：core-set 的覆盖半径只有随机的 1/5，长尾场景占比翻了两三倍，')
print('   而检索 top-K 只覆盖到极少数几个 clip —— **它找得准，但买得重复**。')
print('⚠️  k-center 的死穴：**对离群点极度敏感**。一帧相机故障的全绿图离所有点都远，')
print('   它一定会被选中，接着它旁边的噪声帧也会被选中 —— 预算被坏数据吃掉。')"""),

    code("""# 更稳健的替代：聚类/标签均衡采样（轮转配额，某层发完就跳过）
def balanced_sample(k, keyfn, seed=0):
    r = np.random.default_rng(seed)
    groups = collections.defaultdict(list)
    for i in range(N):
        groups[keyfn(frames[i])].append(i)
    for g in groups.values():
        r.shuffle(g)
    keys = sorted(groups, key=str)
    out, ptr = [], collections.defaultdict(int)
    while len(out) < k:
        moved = False
        for kk in keys:
            if ptr[kk] < len(groups[kk]) and len(out) < k:
                out.append(groups[kk][ptr[kk]]); ptr[kk] += 1; moved = True
        if not moved:
            break
    return np.array(out)

bal = balanced_sample(K, lambda f: (f['weather'], f['light']))
print(f'{"选法":<16s} {"覆盖场景组合":>14s} {"长尾占比":>10s} {"对离群点":>10s}')
print(f'{"core-set 贪心":<16s} {bucket_cov(sel_cs):>14d} {tail_frac(sel_cs):>10.1%} {"极敏感":>10s}')
print(f'{"标签均衡采样":<16s} {bucket_cov(bal):>14d} {tail_frac(bal):>10.1%} {"稳健":>10s}')
print(f'{"随机采样":<16s} {np.mean(rand_b):>14.1f} {np.mean(rand_t):>10.1%} {"稳健":>10s}')
assert bucket_cov(bal) >= bucket_cov(sel_cs) - 2
assert tail_frac(bal) > np.mean(rand_t)
print('\\n✅ 均衡采样没有 k-center 激进，但对噪声稳健得多 —— **工业上更常见的选择**。')
print('   实战组合：先离群剔除 -> 再按场景标签分层 -> 层内用 core-set 或随机。')"""),

    md("""## 6 · 场景打标：元数据 / 规则 / VLM 的三级级联

三条路各有覆盖面：**元数据免费但只能推部分轴**、**VLM 准但要花钱**。
级联的做法是：规则有把握的地方用规则（免费且往往更准），剩下的交给 VLM。"""),
    code("""# —— 车端可拿到的元数据（雨刷档位 / 大灯 / 时间 / 地图道路等级）——
def make_meta(f):
    pw = {'clear': [.93, .06, .01], 'rain': [.03, .22, .75],
          'fog':   [.25, .62, .13], 'snow': [.05, .25, .70]}[f['weather']]
    wiper = int(rng.choice(3, p=pw))
    l = f['light']
    if   l == 'day':   hour, hl = int(rng.integers(9, 17)), int(rng.random() < 0.08)
    elif l == 'dusk':  hour, hl = int(rng.integers(17, 20)), int(rng.random() < 0.65)
    elif l == 'night': hour, hl = int(rng.choice([20, 21, 22, 23, 0, 1, 2, 5])), 1
    else:              hour, hl = int(rng.integers(9, 17)), 1   # ← tunnel：白天却开灯（陷阱）
    return dict(wiper=wiper, headlight=hl, hour=hour, road_class=f['road'])

METAD = [make_meta(f) for f in frames]

def rule_tag(m):
    w = 'rain' if m['wiper'] >= 1 else 'clear'         # 规则**根本区分不出** fog / snow
    if   17 <= m['hour'] < 20:                  l = 'dusk'
    elif m['hour'] >= 20 or m['hour'] < 6:      l = 'night'
    elif m['headlight'] == 1:                   l = 'night'   # ← 隧道被误判成夜间
    else:                                       l = 'day'
    return w, l

def rule_confident(m):
    '''规则「有把握」的判据：只在元数据能唯一确定时才认。'''
    cw = (m['wiper'] == 0)                                        # 雨刷不动 -> 基本是 clear
    cl = (17 <= m['hour'] < 20) or m['hour'] >= 20 or m['hour'] < 6 or m['headlight'] == 0
    return cw, cl

# —— 模拟 VLM 打标：**错误不是随机的，稀有取值召回明显更低** ——
P_OK_W = {'clear': .96, 'rain': .88, 'fog': .62, 'snow': .75}
P_OK_L = {'day': .96, 'dusk': .80, 'night': .93, 'tunnel': .70}
CONF_W = {'clear': ['fog'], 'rain': ['fog', 'snow'], 'fog': ['rain', 'clear'], 'snow': ['rain']}
CONF_L = {'day': ['dusk'], 'dusk': ['day', 'night'], 'night': ['dusk', 'tunnel'], 'tunnel': ['night']}
VLM_COST = 0.0015                                    # 美元 / 帧

def vlm_tag(f):
    w = f['weather'] if rng.random() < P_OK_W[f['weather']] else str(rng.choice(CONF_W[f['weather']]))
    l = f['light']   if rng.random() < P_OK_L[f['light']]   else str(rng.choice(CONF_L[f['light']]))
    return w, l

rule_w, rule_l = zip(*[rule_tag(m) for m in METAD])
vlm_w,  vlm_l  = zip(*[vlm_tag(f) for f in frames])
gt_w = [f['weather'] for f in frames]; gt_l = [f['light'] for f in frames]
acc = lambda a, b: float(np.mean([x == y for x, y in zip(a, b)]))

cas_w, cas_l, ncall = [], [], 0
for i, f in enumerate(frames):
    cw, cl = rule_confident(METAD[i])
    rw, rl = rule_tag(METAD[i])
    if not (cw and cl):
        ncall += 1
    cas_w.append(rw if cw else vlm_w[i])
    cas_l.append(rl if cl else vlm_l[i])

print(f'{"方案":<14s} {"weather 准确率":>15s} {"lighting 准确率":>16s} {"VLM 调用率":>11s} {"成本(USD)":>11s}')
print(f'{"① 纯规则":<14s} {acc(rule_w, gt_w):>15.1%} {acc(rule_l, gt_l):>16.1%} {0.0:>11.1%} {0.0:>11.2f}')
print(f'{"③ 全量 VLM":<14s} {acc(vlm_w, gt_w):>15.1%} {acc(vlm_l, gt_l):>16.1%} {1.0:>11.1%} {N * VLM_COST:>11.2f}')
print(f'{"①+③ 级联":<14s} {acc(cas_w, gt_w):>15.1%} {acc(cas_l, gt_l):>16.1%} '
      f'{ncall / N:>11.1%} {ncall * VLM_COST:>11.2f}')
assert acc(vlm_w, gt_w) > acc(rule_w, gt_w), 'VLM 应显著强于纯规则'
assert ncall < 0.6 * N, '级联应大幅削减 VLM 调用量'
assert acc(cas_l, gt_l) > acc(vlm_l, gt_l), '元数据确定的部分比 VLM 更准'
print('\\n✅ 级联不只是省钱：在元数据能唯一确定的那部分，规则**比 VLM 更准**（它是真值不是猜的）。')
print('   这就是「先免费的、再便宜的、最后才是贵的」这条工程铁律的具体形态。')"""),

    code("""# ⚠️ VLM 的错误是**成片的**：总体准确率好看，稀有取值的召回可能烂到不能用
def per_value_recall(pred, gt, labels):
    out = {}
    for L in labels:
        m = [i for i in range(len(gt)) if gt[i] == L]
        out[L] = (len(m), float(np.mean([pred[i] == L for i in m])) if m else float('nan'))
    return out

print('VLM 逐取值召回（weather）—— 总体准确率 %.1f%%：' % (100 * acc(vlm_w, gt_w)))
rec_w = per_value_recall(vlm_w, gt_w, WEATHER)
for L, (n_, r_) in rec_w.items():
    flag = '   ← ⚠️ 这一格的统计不能信' if r_ < 0.75 else ''
    print(f'  {L:<7s} n={n_:5d}  recall={r_:.2f}{flag}')
print('\\nVLM 逐取值召回（lighting）—— 总体准确率 %.1f%%：' % (100 * acc(vlm_l, gt_l)))
rec_l = per_value_recall(vlm_l, gt_l, LIGHT)
for L, (n_, r_) in rec_l.items():
    flag = '   ← ⚠️' if r_ < 0.75 else ''
    print(f'  {L:<7s} n={n_:5d}  recall={r_:.2f}{flag}')

def cohen_kappa(a, b, labels):
    '''一致性系数：扣掉「碰巧同意」之后的一致程度。'''
    po = float(np.mean([x == y for x, y in zip(a, b)]))
    pe = float(sum(np.mean([x == L for x in a]) * np.mean([y == L for y in b]) for L in labels))
    return (po - pe) / (1 - pe)

audit = rng.choice(N, 300, replace=False)              # 送人工的**审计集**
k_vlm  = cohen_kappa([vlm_w[i] for i in audit],  [gt_w[i] for i in audit], WEATHER)
k_rule = cohen_kappa([rule_w[i] for i in audit], [gt_w[i] for i in audit], WEATHER)
print(f'\\n审计集 300 帧的 Cohen kappa（weather）：VLM {k_vlm:.3f}   纯规则 {k_rule:.3f}')
assert rec_w['fog'][1] < 0.80, 'fog 是稀有取值，VLM 召回应明显偏低'
assert k_vlm > k_rule and k_vlm > 0.6
print('\\n⚠️  总体准确率 90% 看着很好，但 fog 只有 ~60% 的召回 ——')
print('    于是「我们池子里雾天数据不多」这个结论**是标注器造出来的假象**。')
print('✅ 所以审计集不能只看总体准确率，必须**按每个取值分别算召回**，专盯稀有取值。')
print('   经验门槛：kappa < 0.6 的标签轴，不要拿它做任何数据决策。')"""),

    md("""## 7 · 标注预算分配：把钱花在最缺的格子上

把「标 n 张后该格的收益」建模成饱和曲线 $V_c(n)=w_c(1-e^{-n/\\tau_c})$，
则边际收益率 = $\\dfrac{w_c}{\\tau_c\\,\\text{cost}_c}e^{-n/\\tau_c}$。
因为 $V_c$ 是凹的，「每次把下一块钱给边际收益率最高的格子」这个贪心是最优的。"""),
    code("""CELLS = [
    #  格子名                     已有   重要度  饱和尺度  单价(元)  池中可挖
    dict(name='tunnel × construction', have=180,   w=9.0,  tau=1500, cost=3.2, avail=4000),
    dict(name='fog × speed_limit',     have=90,    w=6.0,  tau=1200, cost=2.8, avail=1500),
    dict(name='day_urban × speed',     have=42000, w=10.0, tau=8000, cost=1.0, avail=200000),
    dict(name='rain × no_left',        have=600,   w=4.0,  tau=2000, cost=2.0, avail=9000),
    dict(name='night × stop',          have=1500,  w=8.0,  tau=3000, cost=1.8, avail=12000),
    dict(name='snow × any',            have=25,    w=2.5,  tau=800,  cost=4.0, avail=300),
]
CHUNK, BUDGET, MIN_RATE = 50, 30000.0, 1e-5

def total_value(alloc):
    return sum(c['w'] * (1 - math.exp(-(c['have'] + alloc[c['name']]) / c['tau'])) for c in CELLS)
BASE_V = sum(c['w'] * (1 - math.exp(-c['have'] / c['tau'])) for c in CELLS)

def alloc_greedy(budget, min_rate=MIN_RATE):
    x = {c['name']: 0 for c in CELLS}; spent = 0.0
    while True:
        best, rate = None, min_rate            # ← 低于门槛就不投：**预算没花完是对的**
        for c in CELLS:
            if x[c['name']] + CHUNK > c['avail']:      continue
            price = c['cost'] * CHUNK
            if spent + price > budget:                 continue
            n0 = c['have'] + x[c['name']]
            dv = c['w'] * (math.exp(-n0 / c['tau']) - math.exp(-(n0 + CHUNK) / c['tau']))
            if dv / price > rate:
                best, rate = c, dv / price
        if best is None:
            break
        x[best['name']] += CHUNK; spent += best['cost'] * CHUNK
    return x, spent

def alloc_uniform(budget):
    x = {c['name']: int(min(c['avail'], (budget / len(CELLS)) // c['cost'])) for c in CELLS}
    return x, sum(x[c['name']] * c['cost'] for c in CELLS)

def alloc_lowest_first(budget):
    '''常见但错误的做法：哪个格子最缺就全给它。'''
    x = {c['name']: 0 for c in CELLS}; spent = 0.0
    for c in sorted(CELLS, key=lambda c: c['have'] / c['tau']):
        n = int(min(c['avail'], (budget - spent) // c['cost']))
        x[c['name']] = n; spent += n * c['cost']
    return x, spent

print(f'{"分配策略":<18s} {"总收益":>10s} {"花费(元)":>11s}')
allocs = {}
for nm, fn in [('贪心：边际/元', alloc_greedy), ('平均分', alloc_uniform), ('缺口最大优先', alloc_lowest_first)]:
    x, sp = fn(BUDGET); allocs[nm] = x
    print(f'{nm:<18s} {total_value(x) - BASE_V:>10.3f} {sp:>11.0f}')
print(f'\\n贪心的具体分配：')
for c in CELLS:
    n = allocs['贪心：边际/元'][c['name']]
    note = '   ← **已饱和，一分钱不给**' if n == 0 else ('   ← 池子里就这么多' if n >= c['avail'] else '')
    print(f'  {c["name"]:<24s} {n:>6d} 张  花 {n * c["cost"]:>7.0f} 元{note}')

g = total_value(allocs['贪心：边际/元'])
assert g > total_value(allocs['平均分']), '贪心应优于平均分'
assert g > total_value(allocs['缺口最大优先']), '贪心应优于「哪个最缺给哪个」'
assert allocs['贪心：边际/元']['day_urban × speed'] == 0, '已饱和的格子不该拿到预算'
print('\\n✅ 三个符合直觉的行为自动出现了：已饱和的格子拿 0；重要度高的多给；单价贵的被折价。')
print('⚠️  这个模型的两个漏洞要能说出来：① 新场景没有历史 -> 没有 tau，只能先给探索性小配额；')
print('    ② 格子之间不独立（夜间限速牌涨了，夜间禁令牌也会涨）-> 贪心会高估分散投资的价值。')
print('⚠️  还要留 10~15% 预算，按**部署真实分布**随机采样去标，维护一个不漂移的基准评测集。')"""),

    md("""## ✏️ 练习 1：MMR —— 相关性与多样性的显式权衡

实现 `mmr_select(sims_q, X, cand, k, lam)`（Maximal Marginal Relevance）：

- 第一个**总是**选 `sims_q` 最大的候选；
- 之后每步选使 `lam * sims_q[i] - (1 - lam) * max_{j∈S} X[i]·X[j]` 最大的 `i`；
- 已选过的不再选；返回长度为 `k` 的 numpy 整数数组（按选中顺序）。

`lam=1.0` 时应退化成「按相关性取 top-k」。"""),
    code("""def mmr_select(sims_q, X, cand, k, lam):
    # TODO: ① 第一个选 sims_q 最大的
    #       ② 之后每步最大化 lam*相关性 - (1-lam)*与已选集合的最大相似度
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
q_sims = E @ E[qi]
cand = np.argsort(-q_sims)[:200]
sel_lam1 = mmr_select(q_sims, E, cand, 8, 1.0)
assert list(map(int, sel_lam1)) == list(map(int, cand[:8])), 'lam=1 应退化成 top-k'
sel_mmr = mmr_select(q_sims, E, cand, 8, 0.35)
assert len(set(map(int, sel_mmr))) == 8, '不能重复选'
n1 = len({int(clip_of[i]) for i in sel_lam1})
n2 = len({int(clip_of[i]) for i in sel_mmr})
print(f'lam=1.00（纯相关性）选出的 8 张来自 {n1} 个 clip')
print(f'lam=0.35（相关+多样）选出的 8 张来自 {n2} 个 clip')
assert n2 > n1, 'MMR 应该显著提高来源多样性'
print('✅ 练习 1 通过：**一个 lam 就把「找得准」和「买得散」放到了同一个目标函数里**')"""),

    md("""## ✏️ 练习 2：分层配额（stratified quota）

实现 `stratified_quota(keys, k)`：`keys` 是每个候选样本所属的层标签列表，`k` 是总配额。

- 各层配额尽量均等；
- **某层样本数不够时，余额要分给还有余量的层**（不能浪费配额）；
- 返回 `{层: 配额}`，且 `sum(配额) == min(k, len(keys))`；配额不超过该层样本数。

提示：按「该层样本数」升序轮转发放，每轮每层发 1 张，发满就跳过。"""),
    code("""def stratified_quota(keys, k):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
keys = ['A'] * 100 + ['B'] * 100 + ['C'] * 3 + ['D'] * 1
q = stratified_quota(keys, 40)
assert sum(q.values()) == 40, q
assert q['C'] == 3 and q['D'] == 1, '样本不够的层应全拿，且不超发'
assert abs(q['A'] - q['B']) <= 1 and q['A'] + q['B'] == 36, q
q2 = stratified_quota(keys, 10000)
assert sum(q2.values()) == len(keys) and q2['A'] == 100
q3 = stratified_quota(keys, 0)
assert sum(q3.values()) == 0
real = stratified_quota([(f['weather'], f['light']) for f in frames], 80)
print('真实池子上按 (天气,光照) 分层的 80 张配额（非零项）:')
for kk, v in sorted(real.items(), key=lambda kv: -kv[1]):
    if v:
        print(f'  {str(kk):<22s} {v:3d}')
assert sum(real.values()) == 80 and len([v for v in real.values() if v]) >= 8
print('✅ 练习 2 通过：**分层配额是最容易落地、也最难出错的多样性工具**')"""),

    md("""## ✏️ 练习 3：近重复分组（连通分量版去重）

贪心去重是**顺序相关**的（先来后到决定谁当代表）。更稳的做法是把
「汉明距离 ≤ thresh」看成一张图的边，取**连通分量**作为重复组。

实现 `near_dup_groups(H, thresh)`：返回 `list[list[int]]`，每个内层列表是一组的下标（升序），
外层按每组最小下标升序。要求：每个样本恰好属于一组，组的并集是全体。

提示：并查集（union-find）；先算两两汉明距离矩阵（本例 N 只有两千量级，可以直接算）。"""),
    code("""def near_dup_groups(H, thresh):
    # TODO: 并查集 + 汉明距离 <= thresh 连边 -> 连通分量
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
groups = near_dup_groups(H, 3)
flat = [i for g in groups for i in g]
assert sorted(flat) == list(range(len(H))), '每个样本恰好属于一组'
assert all(list(g) == sorted(g) for g in groups) and groups == sorted(groups, key=lambda g: g[0])
assert len(groups) < len(H) // 3, f'去重后组数应远小于总帧数，实际 {len(groups)}'
gid = {i: k for k, g in enumerate(groups) for i in g}
pair = next((a, b) for idxs in by_clip.values() for a, b in itertools.combinations(idxs, 2)
            if np.count_nonzero(H[a] != H[b]) <= 3)
assert gid[pair[0]] == gid[pair[1]], '汉明距离 <= 3 的两帧必须在同一组'

print(f'{"thresh":>7s} {"组数":>7s} {"最大组":>8s} {"单例组":>8s}')
prev = None
for T in [1, 2, 3, 4, 5, 6]:
    gs = near_dup_groups(H, T)
    sz = sorted((len(x) for x in gs), reverse=True)
    flag = '   ← ⚠️ **链式合并塌方**' if sz[0] > len(H) // 4 else ''
    print(f'{T:>7d} {len(gs):>7d} {sz[0]:>8d} {sum(1 for s in sz if s == 1):>8d}{flag}')
    if T == 6:
        prev = sz[0]
assert prev > len(H) // 4, '阈值放大后应出现巨型连通分量'
print(f'\\n贪心去重(thresh=6) 保留 {len(kept6)} 帧 vs 连通分量(thresh=3) {len(groups)} 组')
print('✅ 练习 3 通过：**连通分量与顺序无关**，但会因为「链式合并」比贪心更激进 ——')
print('   A~B、B~C 但 A 与 C 完全不像时，三者仍会被并成一组。阈值从 3 放到 6，')
print('   最大组就从几十帧膨胀到整个池子的一半 —— **所以连通分量法的阈值必须更保守**。')"""),

    md("""## ✏️ 练习 4：数据血缘 —— 「这批数据出问题了，谁受影响？」

给定数据集版本表与训练任务表，实现两个函数：

- `batches_of(datasets, ds)`：返回该数据集版本**递归展开父版本后**包含的全部 batch（集合）；
- `affected_models(datasets, runs, bad_batch)`：返回用到了 `bad_batch` 的**全部** model id（升序列表）。

这是数据闭环出事故时第一个要能回答的问题——没有它，只能全量重训「以防万一」。"""),
    code("""DATASETS = {
    'v1.7.1': dict(parent=None,     batches=['b_base_2025q4', 'b_night_2026w12']),
    'v1.7.2': dict(parent='v1.7.1', batches=['b_tunnel_2026w27']),
    'v1.7.3': dict(parent='v1.7.2', batches=['b_fog_2026w29']),
    'v2.0.0': dict(parent=None,     batches=['b_base_2025q4', 'b_resample_2026w30']),
}
RUNS = {'model_r31': 'v1.7.1', 'model_r38': 'v1.7.2',
        'model_r41': 'v1.7.3', 'model_x02': 'v2.0.0'}

def batches_of(datasets, ds):
    # TODO
    raise NotImplementedError

def affected_models(datasets, runs, bad_batch):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
assert batches_of(DATASETS, 'v1.7.1') == {'b_base_2025q4', 'b_night_2026w12'}
assert batches_of(DATASETS, 'v1.7.3') == {'b_base_2025q4', 'b_night_2026w12',
                                          'b_tunnel_2026w27', 'b_fog_2026w29'}
assert affected_models(DATASETS, RUNS, 'b_tunnel_2026w27') == ['model_r38', 'model_r41']
assert affected_models(DATASETS, RUNS, 'b_fog_2026w29') == ['model_r41']
assert affected_models(DATASETS, RUNS, 'b_base_2025q4') == \\
       ['model_r31', 'model_r38', 'model_r41', 'model_x02']
assert affected_models(DATASETS, RUNS, 'b_not_exist') == []
for b in ['b_tunnel_2026w27', 'b_base_2025q4']:
    print(f'{b:<22s} 受影响模型: {affected_models(DATASETS, RUNS, b)}')
print('✅ 练习 4 通过：**递归展开父版本**是最容易漏掉的一步 ——')
print('   只查「直接引用」会漏掉所有继承自它的下游数据集与模型。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def mmr_select(sims_q, X, cand, k, lam):
    cand = np.asarray(cand)
    first = int(cand[int(np.argmax(sims_q[cand]))])
    sel = [first]
    remaining = [int(i) for i in cand if int(i) != first]
    max_sim = {i: float(X[i] @ X[first]) for i in remaining}   # 到已选集合的最大相似度
    while len(sel) < k and remaining:
        scores = [lam * float(sims_q[i]) - (1 - lam) * max_sim[i] for i in remaining]
        pick = remaining.pop(int(np.argmax(scores)))
        sel.append(pick)
        for i in remaining:
            max_sim[i] = max(max_sim[i], float(X[i] @ X[pick]))
    return np.array(sel, dtype=int)"""),
    code("""# 练习 2 参考答案
def stratified_quota(keys, k):
    caps = collections.Counter(keys)
    quota = {g: 0 for g in caps}
    order = sorted(caps, key=lambda g: (caps[g], str(g)))       # 小层优先，保证余额能流出去
    left = min(k, len(keys))
    while left > 0:
        moved = False
        for g in order:
            if left == 0:
                break
            if quota[g] < caps[g]:
                quota[g] += 1; left -= 1; moved = True
        if not moved:
            break
    return quota"""),
    code("""# 练习 3 参考答案
def near_dup_groups(H, thresh):
    n = len(H)
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    Hi = H.astype(np.int8)
    for i in range(n):                                   # 一行对全体，向量化算汉明距离
        d = np.count_nonzero(Hi[i + 1:] != Hi[i], axis=1)
        for off in np.where(d <= thresh)[0]:
            union(i, i + 1 + int(off))
    buckets = collections.defaultdict(list)
    for i in range(n):
        buckets[find(i)].append(i)
    return sorted((sorted(v) for v in buckets.values()), key=lambda g: g[0])"""),
    code("""# 练习 4 参考答案
def batches_of(datasets, ds):
    out, cur = set(), ds
    while cur is not None:
        out |= set(datasets[cur]['batches'])
        cur = datasets[cur]['parent']
    return out

def affected_models(datasets, runs, bad_batch):
    return sorted(m for m, ds in runs.items() if bad_batch in batches_of(datasets, ds))"""),

    md("""---
## 🧪 真实工程胶囊：一条可直接照搬的挖掘任务定义"""),
    code("""RECIPE = r'''
# ===================== mining_job.yaml =====================
job_id: mine_2026w31_tunnel_construction
owner: perception-data@
# ---- ① 触发来源：这次挖掘为了修什么 ----
motivation:
  badcase_ticket: TSR-4471            # 路测单号，必填。没有 ticket 的挖掘任务不予排期
  failure_mode:   "隧道出口逆光下施工牌漏检（首检距离 < 25m）"
  seed_frames:    [frame_88e1a, frame_9d02c, frame_31fb7]

# ---- ② 召回：结构化过滤 **先** 于向量检索（先砍掉 99%）----
filter:
  tags.lighting: [tunnel, night]
  tags.sign_class: [construction, temporary]
  tags.tag_version: ">=2026.06"       # 标签口径版本，防止跨口径统计
retrieve:
  index:        ivf_pq_v3             # **索引绑定嵌入模型版本**
  embedding:    det_backbone@f19c2    # 换 backbone 必须重建索引，否则静默返回垃圾
  metric:       cosine                # 建索引前已 L2 归一化
  nprobe:       16                    # 召回 0.98 @ 12% 算力（离线批量任务可以调大）
  top_k:        20000

# ---- ③ 精选：去重 -> 多样性 -> 配额 ----
dedup:
  phash:        {type: phash64, thresh: 6}      # 先砍像素级近重复
  embed_radius: {cosine: 0.06, within_tag_only: true}  # **跨场景不去重**
diversify:
  method:       coreset_kcenter
  outlier_filter: {knn_density_percentile: 2}   # k-center 对离群点极敏感 -> 先剔除
  k:            1200
quota:
  stratify_by:  [tags.weather, tags.lighting]
  reserve_random_frac: 0.12           # **留 12% 按真实分布随机采**，防评测集漂移

# ---- ④ 送标 ----
label:
  spec_version: tsr_label_spec_v4.2
  price_per_frame_cny: {default: 2.0, occlusion_heavy: 3.2, night: 2.6}
  budget_cny:   30000
  qc_sample_rate: 0.05                # 质检抽样率；通过率 < 0.92 整批打回

# ---- ⑤ 产物与血缘（这一段不是文档，是**机器可读的契约**）----
outputs:
  batch_id:     b_tunnel_2026w31
  lineage:
    mined_by:   {job: mine_2026w31_tunnel_construction, index: ivf_pq_v3,
                 embedding: det_backbone@f19c2, seeds: [frame_88e1a, ...], rng_seed: 7}
    split_key:  clip_id               # **按 clip 划分训练/评测，绝不按帧**（防泄漏）
gate:
  - qc_pass_rate >= 0.92
  - duplicate_rate <= 0.03            # 抽检重复率
  - tag_kappa(weather) >= 0.6         # 标签一致性不达标 -> 这批标签不参与统计

# ===================== VLM 打标 prompt =====================
# 关键三条：JSON schema 强约束 / 保留 unknown 与 confidence / 逐取值召回做审计
VLM_PROMPT = (
  "只输出 JSON。字段与允许取值：\\n"
  '  weather:    ["clear","rain","fog","snow","unknown"]\\n'
  '  lighting:   ["day","dusk","night","tunnel","unknown"]\\n'
  '  occlusion:  ["none","partial","heavy","unknown"]\\n'
  "  confidence: 0.0-1.0\\n"
  "无法判断填 unknown，不要猜。"          # 强迫二选一会制造大量静默错误
)
'''
print(RECIPE)
for token in ['badcase_ticket', 'nprobe', 'phash', 'coreset_kcenter',
              'reserve_random_frac', 'split_key', 'tag_kappa', 'unknown']:
    assert token in RECIPE, token
print('✅ 配方覆盖：ticket 溯源 / 标签先过滤 / 索引绑嵌入版本 / 去重 / core-set / '
      '分层配额 / 随机保留集 / 质检门禁 / clip 级划分 / 血缘')"""),

    md("""### 小结

- **挖掘系统的产出不是「找到多少难例」，而是「每块标注预算换来多少模型提升」**。
  候选池免费、标注昂贵，所以全部设计压力都在「筛选」这一步。
- **相似度决定「找什么」，多样性决定「买什么」**。把这两阶段目标搞混 = 回传 1000 张同一路口。
  实测：同样 80 张预算，core-set 的覆盖半径只有随机的 1/5，而检索 top-K 只覆盖到几个 clip。
- **嵌入检索前必须 L2 归一化**（否则排序被候选的模长劫持）；**索引必须绑定嵌入模型版本**
  ——换 backbone 后旧索引不在同一空间，检索会静默返回垃圾。
- **场景标签体系 = 正交轴 + 受控词表 + 来源与置信度**。它的最大价值是能算出**缺口矩阵**，
  把「模型不太行」变成「`(tunnel) × construction` 只有 180 张，AP 0.34」。
- **VLM 打标是当前主流**，因为它把「加一个新标签轴」从「训个分类器」降成「改段 prompt」。
  但它的错误是**成片的**：总体 90% 而 fog 召回只有 60%——审计必须按取值分别算召回，kappa &lt; 0.6 不用。
- **三级级联**（元数据 → 规则/小模型 → VLM）能把 VLM 调用量降到 ~40%，
  而且在元数据能唯一确定的部分**比 VLM 更准**。
- **预算分配 = 带成本的凹函数贪心**：已饱和的格子给 0、重要度高的多给、单价贵的折价；
  并且**预算没花完是对的**，边际收益率低于门槛就该留到下一轮。
- **血缘的三张表 + 一条纪律**：batch / dataset / run，训练脚本只接受数据集版本号。
  **划分训练-评测必须按 clip 而不是按帧**——TSR 里一块标志会连续出现在几十帧，按帧划分会让指标虚高。

下一站：**模块 05 · 闭环验证** —— 数据挖回来标完了，怎么证明它<em>真的</em>有用。"""),
]
