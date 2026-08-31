# -*- coding: utf-8 -*-
"""C70 模块 01 · 文档摄取与解析。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（四段流水线与四个静默失败）；"
                 "知道「哈希」；不需要任何解析库"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_ingestion.ipynb'
                       '（三种解析方式的可答性对比 / 双栏版面的阅读顺序恢复 / '
                       'OCR 字符错误率到词级破坏率的推导与实测 / '
                       '元数据过滤的收益与它的 recall 风险 / '
                       '近重复怎么占满 top-k / 幂等摄取契约 / 摄取质量门禁六项）'),
    ("核心参考", "<em>unstructured</em> 与 <em>pypdf</em> 的 element / 坐标模型 · "
                 "Nougat / LayoutLM 一类版面理解工作的问题设定 · "
                 "Broder, <em>On the Resemblance and Containment of Documents</em>（1997，MinHash） · "
                 "本课程 C43（去重与流式）· C11 模块 01（BM25 与词法检索）· "
                 "C69 模块 01（摄取边界与不可信内容）"),
    ("预计时长", "读 65 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-things", "解析的目标不是「拿到文字」", "".join([
        P("几乎所有 RAG 项目的第一行代码都是"
          "<code>text = extract_text(pdf)</code>。"
          "<strong>这一行同时决定了这个系统的上限</strong>，"
          "因为它决定了语料里存在什么、不存在什么。"),
        DUAL(
            "解析必须同时拿到<strong>三样东西</strong>，而不是一样："
            "<em>文字</em>（说了什么）、<em>结构</em>（谁属于谁）、"
            "<em>来源</em>（这段字在哪一页哪一节）。"
            "<strong>只拿文字的代价是：结构与来源在下游无法恢复。</strong>"
            "不是「难恢复」——是<em>信息已经不在了</em>。",
            "把它写成一个映射：一份文档 $D$ 的解析结果应当是一个三元组序列"
            "$\\{(t_i, s_i, p_i)\\}$，其中 $t_i$ 是文本片段、"
            "$s_i$ 是它的结构角色（标题 / 正文 / 表格单元 / 列表项 / 脚注）、"
            "$p_i$ 是它的位置（页、区间、章节路径）。"
            "<strong>常见的 <code>extract_text</code> 返回的是 "
            "$\\text{concat}(t_i)$——一个把 $s_i$ 与 $p_i$ 全部投影掉的映射。</strong>"
            "<em>投影是不可逆的</em>，这就是「无法恢复」的准确含义。",
        ),
        TABLE(["丢掉的东西", "下游哪一步会因此失败", "能不能事后补回来"], [
            ["<strong>表格的行列对应</strong>",
             "「A 行 B 列的值是多少」——块被召回、数字也在，但答案不可恢复",
             "<strong>不能</strong>。拍平后 <code>1580</code> 与「上海/2023」的关联已经消失"],
            ["<strong>标题层级</strong>",
             "分块（模块 02）无法按章节切；检索无法按章节过滤",
             "部分可以（靠字号/编号启发式），<em>但不可靠</em>"],
            ["<strong>阅读顺序</strong>",
             "实体与属性错配——<strong>这类错误的答案读起来完全通顺</strong>",
             "<strong>不能</strong>，除非重新解析"],
            ["<strong>位置（页/区间）</strong>",
             "引用核查、删除、更新、权限过滤（模块 05 全靠它）",
             "<strong>不能</strong>"],
            ["<strong>列表的层级</strong>",
             "「第二类的第三条」被拉平成同级，条件被错误地并列",
             "部分可以（靠缩进），<em>PDF 里缩进常常已经没了</em>"],
        ]),
        CALLOUT("danger", "这张表最重要的一列是第三列。"
                          "<strong>解析是整条流水线里唯一一个「做错了就无法在下游补救」的环节</strong>——"
                          "分块参数可以改、查询可以改写、索引可以重建，"
                          "<em>但解析时丢掉的信息只能靠重新解析拿回来</em>。"
                          "所以它值得被当成一次性的、需要认真做的工程决策，"
                          "而不是一行 <code>extract_text</code>。"),
    ])),

    # ============================================================== 2
    ("structure-loss", "结构损失的实验：四种解析，同一份表格", "".join([
        P("把上一节的第一行做成一个可复现的实验。"
          "一份四行三列的营收表，四种解析方式。"
          "<strong>其中第二种的结论和多数人预期的不一样</strong>，值得先看："),
        ASCII("""
   原始表格
   ┌────────┬────────┬────────┐
   │  地区  │  年份  │  营收  │
   ├────────┼────────┼────────┤
   │  北京  │  2023  │  1240  │
   │  北京  │  2024  │  1310  │
   │  上海  │  2023  │  1580  │   ← 问：上海 2023 年营收多少？
   │  上海  │  2024  │  1620  │
   └────────┴────────┴────────┘

   ① 保结构（行 → 句）
      "上海 在 2023 年的营收是 1580 万元。"        ✅ 可答

   ② 行主序拍平（按行连起来）
      "地区 年份 营收 北京 2023 1240 … 上海 2023 1580 …"   ⚠️ 行对应扛住了
      ↑ 单元格与行名恰好相邻；但「营收」只在开头出现一次 → **列名丢了**

   ③ 列主序拍平（按列读——PDF 里按 x 坐标优先排序的真实结果）
      "地区 北京 北京 上海 上海 年份 2023 2024 … 营收 1240 … 1580 …"  ❌ 不可答
      ↑ 每个字都在，检索照样召回，但 1580 与「上海+2023」隔了几十个 token

   ④ 行主序拍平 + 按字符数硬切
      块1: "… 北京 2024 1310 上海 2023 "
      块2: "1580 上海 2024 1620"     ← 「上海 2023」与「1580」被切开   ❌ 不可答
      ↑ 几百行的大表上，这件事必然发生在某些行上
"""),
        P("notebook 第 1 节会把四种都量一遍，结论有三条："),
        OL([
            "<strong>只有行转句（①）在所有条件下都可恢复。</strong>",
            "<strong>行主序拍平（②）在小表上扛住了「哪一行」</strong>——"
            "单元格与它的行名恰好相邻；"
            "<em>但它丢了「哪一列」</em>——「营收」只在开头出现一次，离 <code>1580</code> 几十个 token。"
            "<em>所以「拍平必然丢结构」是一个错的说法</em>；"
            "丢失发生在两个具体条件下：<strong>列主序读取（③）</strong>，"
            "以及<strong>行与行名被块边界切开（④）</strong>。"
            "而这两个条件在真实文档上都很常见——"
            "PDF 按 x 坐标优先排序就会得到 ③，几百行的大表必然遇到 ④。",
            "<strong>不可恢复的那些块，检索指标依然正常。</strong>"
            "相似度 > 0.3、<code>1580</code> 这个数字<em>确实在召回的块里</em>——"
            "Precision@1 是满分，端到端是错的。",
        ]),
        CALLOUT("intuition", "第 2 条的工程含义不是「拍平有时可以」，而是相反："
                             "<strong>不要把「表格能不能扛住」当成一个概率事件去赌。</strong>"
                             "<em>行转句对 ③ 和 ④ 都免疫，而它的实现只有五行。</em>"),
        DUAL(
            "为什么会这样？因为<strong>相似度衡量的是词的重叠，而不是关系的保留</strong>。"
            "拍平后的块包含「上海」「2023」「1580」这三个词，"
            "查询也包含前两个——重叠很高。"
            "<em>但「哪个数字属于哪一对」这个信息不在词袋里。</em>",
            "更一般地：设关系 $R = \\{(\\text{行}, \\text{列}, \\text{值})\\}$。"
            "保结构的解析产生的文本 $T_1$ 满足 $R$ 可从 $T_1$ 唯一恢复；"
            "拍平的文本 $T_2$ 只保留了 $\\pi(R)$——三个投影的并集，"
            "而 $|\\{R' : \\pi(R') = \\pi(R)\\}|$ 在 $m$ 行 $n$ 列时是组合级的。"
            "<strong>检索指标是 $T$ 与 $q$ 的函数，与 $R$ 是否可恢复无关</strong>——"
            "这就是「指标正常但答案错」的形式化来源。",
        ),
        H3("落地做法：表格必须走单独的路径"),
        UL([
            "<strong>行转句</strong>（最简单、最有效）：每一行渲染成一句自然语言，"
            "<em>把列名带上</em>。四行表变成四个可独立检索的句子。",
            "<strong>保留原表 + 摘要句</strong>：块的正文是行转句，"
            "但 metadata 里挂着这张表的 markdown 原文，供需要时整表喂给模型。",
            "<strong>大表要分块</strong>：几百行的表整块喂进去等于把上下文烧掉；"
            "行转句之后天然就是可检索单元。",
            "<strong>永远记录 <code>element_type='table'</code></strong>——"
            "下游要知道这个块的来源是表格才能正确使用它（也才能在评测时单独看表格类问题的准确率）。",
        ]),
    ])),

    # ============================================================== 3
    ("reading-order", "阅读顺序：最隐蔽的一种结构损失", "".join([
        P("PDF 里没有「段落」这个概念，只有<strong>一堆带坐标的文本块</strong>。"
          "把它们拼成文本需要一个顺序，而<em>选错顺序不会报错</em>。"),
        ASCII("""
   一个双栏版面（左右两栏，各三段）

        x=50                    x=320
   y=100 ┌──────────┐      ┌──────────┐
         │ 左栏 段1  │      │ 右栏 段1  │
   y=200 ├──────────┤      ├──────────┤
         │ 左栏 段2  │      │ 右栏 段2  │
   y=300 ├──────────┤      ├──────────┤
         │ 左栏 段3  │      │ 右栏 段3  │
         └──────────┘      └──────────┘

   ❌ 按 y 排序（"从上到下"）：
      左1 右1 左2 右2 左3 右3      ← 两栏交错，语义被打断

   ✅ 先按 x 分栏、栏内按 y 排序：
      左1 左2 左3 右1 右2 右3      ← 正确

   注意：**按 y 排序在单栏文档上是对的**，
        所以这个 bug 在测试文档上常常不出现。
"""),
        P("交错的后果比「读起来别扭」严重得多。"
          "<strong>如果左栏讲的是 A 产品的参数、右栏讲 B 产品的参数，"
          "交错之后每一段的上下文里都同时有 A 和 B</strong>——"
          "分块之后一个块里会出现「A 的名字 + B 的参数」，"
          "<em>而这个块读起来完全通顺</em>。"),
        CALLOUT("warn", "这是本课最推荐加进 CI 的一项检查："
                        "<strong>解析后随机抽 5 页，人工确认阅读顺序。</strong>"
                        "<em>它便宜、一次性，而它防住的错误在任何自动指标里都看不见。</em>"
                        "notebook 第 2 节给出一个自动版本："
                        "在已知实体-属性配对的合成版面上，量出错配率。"),
        H3("分栏的判定"),
        DUAL(
            "实用的启发式：<strong>看 x 坐标的直方图有没有明显的双峰</strong>。"
            "有 → 双栏，按峰分组；没有 → 单栏，直接按 y 排。"
            "<em>再加两条：页眉页脚按 y 的极值剔除；"
            "跨栏的大标题（宽度接近页宽）单独处理。</em>",
            "更稳的做法是<span class=\"term\">XY-cut</span>："
            "递归地在投影直方图的最大空白处切分——"
            "先找垂直投影的最大间隙（切栏），再在每栏内找水平投影的间隙（切段），"
            "递归直到块足够小。"
            "<strong>它的好处是同时给出了阅读顺序和一棵版面树</strong>，"
            "而版面树正好是模块 02 结构感知分块需要的输入。"
            "<em>代价是它对表格与图文混排会过切，需要配合 element 类型做例外。</em>",
        ),
    ])),

    # ============================================================== 4
    ("ocr", "OCR 噪声：从字符错误率到「答不出来」", "".join([
        P("扫描件与图片 PDF 必须走 OCR，而 OCR 一定有错。"
          "关键问题是：<strong>字符级错误率 $\\varepsilon$ 传导到检索上会放大多少倍？</strong>"),
        MATH(r"P(\text{一个长度 } L \text{ 的词被破坏}) = 1 - (1-\varepsilon)^{L}"),
        DUAL(
            "直觉：<strong>错误率是按字符算的，但检索是按词匹配的</strong>，"
            "所以长词更容易被毁掉。"
            "$\\varepsilon = 3\\%$ 时，两字词被毁的概率是 5.9%，"
            "八字词是 21.7%。"
            "<em>而专有名词、型号、法条编号恰恰都是长串</em>——"
            "<strong>OCR 噪声优先毁掉的正是最有检索价值的那些词。</strong>",
            "这个式子还解释了两类检索的不同斜率。"
            "<span class=\"term\">词法检索</span>（BM25）依赖<strong>精确</strong>词匹配，"
            "所以一个词被破坏就等于这个词的信号完全丢失，"
            "查询里 $m$ 个关键词全部存活的概率是 $(1-\\varepsilon)^{\\sum L_i}$——"
            "<em>随查询长度指数衰减</em>。"
            "<span class=\"term\">语义检索</span>用子词/字符 n-gram，"
            "一个字符错误只毁掉包含它的那几个 n-gram，"
            "<strong>降级是渐进的而不是断崖的</strong>。"
            "notebook 第 3 节把两条曲线画在一起。",
        ),
        TABLE(["OCR 错误率 ε", "2 字词被毁", "8 字词被毁", "含 3 个关键词的精确匹配存活率"], [
            ["<strong>0.5%</strong>", "1.0%", "3.9%", "≈ 91%"],
            ["<strong>1%</strong>", "2.0%", "7.7%", "≈ 83%"],
            ["<strong>3%</strong>", "5.9%", "21.7%", "≈ 57%"],
            ["<strong>5%</strong>", "9.8%", "33.7%", "≈ 38%"],
        ]),
        P("<em>最后一列按查询含 3 个词、平均词长 6 计算。</em>"
          "<strong>它给出的结论很直接：ε 到 3% 时，纯词法检索已经不能作为唯一召回路径了</strong>——"
          "必须配一路语义检索（这正是 C11 模块 01 混合检索的一个非常实际的动机）。"),
        H3("摄取侧能做什么"),
        OL([
            "<strong>记录 OCR 置信度并把低置信页标出来</strong>——"
            "大多数 OCR 引擎给每个词一个置信度。"
            "<em>把页级平均置信度写进 metadata，低于阈值的页进人工复核队列</em>。",
            "<strong>对关键实体做词典纠错</strong>：产品名、人名、法条号是封闭集合，"
            "用编辑距离对齐到词典。<em>这一步的收益远大于对全文做纠错</em>。",
            "<strong>不要在摄取时「顺便」用 LLM 清洗全文</strong>——"
            "它会安静地改写内容（C69 的视角：这等于让不可信内容经过一个会重写它的环节），"
            "<em>而你会失去与原文的对齐</em>，引用核查就没了。",
            "<strong>把 ε 当成一个需要被监控的量</strong>："
            "抽样人工标注 200 个词，算字符错误率，写进摄取报告。"
            "<em>它变差通常意味着上游换了扫描设备。</em>",
        ]),
    ])),

    # ============================================================== 5
    ("metadata", "元数据：摄取时几乎免费，之后无法补", "".join([
        P("元数据是本课后面三个模块的燃料。"
          "<strong>它在摄取时抽取几乎不要钱，而事后补几乎不可能</strong>（因为原文已经不在手上了）。"),
        TABLE(["元数据", "怎么来", "下游用途", "缺了会怎样"], [
            ["<code>doc_id</code> / <code>version</code>", "摄取时分配（永不复用）",
             "幂等、更新、删除（模块 05）",
             "<strong>删不掉、更不了</strong>"],
            ["<code>source_uri</code> / 页码 / 字符区间", "解析器给的位置",
             "引用核查、给用户跳转",
             "答案无法被验证，用户不信"],
            ["<code>section_path</code>（章节路径）", "标题层级栈",
             "结构感知分块（02）、按章节过滤（03）",
             "分块只能按字符数硬切"],
            ["<code>effective_date</code> / <code>updated_at</code>", "文档内容或文件属性",
             "时效过滤、新鲜度监控（05）",
             "<strong>旧政策与新政策同时被召回</strong>"],
            ["<code>tenant</code> / <code>acl</code>（权限标签）", "来源系统",
             "多租户隔离（05）",
             "<strong>跨租户泄漏</strong>——这是安全事故"],
            ["<code>element_type</code>", "解析器（Title/Table/List/Text）",
             "表格特殊处理（02）、按类型评测",
             "表格与正文被同样对待"],
            ["<code>lang</code>", "语言检测",
             "分块的字符/词切分、embedding 选择",
             "中英混排的块被按错误的粒度切"],
        ]),
        CALLOUT("intuition", "有一个判据可以决定「这个元数据要不要抽」："
                             "<strong>它会不会出现在某个查询的过滤条件里，"
                             "或者出现在某个运维操作的 WHERE 子句里？</strong>"
                             "<em>会 → 抽。</em>"
                             "「删除这个用户的所有文档」「只看 2024 年之后生效的版本」"
                             "「只看这个租户的」——这些都是 WHERE 子句。"),
        H3("元数据过滤是双刃的"),
        P("过滤能把候选池缩小、把 precision 拉高。"
          "<strong>但它同时是一个 recall 风险：过滤条件写错，答案会被直接排除在候选之外，"
          "而检索层完全不会察觉。</strong>"),
        DUAL(
            "notebook 第 4 节量了这件事：加上正确的章节过滤，precision@3 明显上升；"
            "而把过滤条件写窄一格（少包含一个章节），"
            "<em>recall 直接掉到 0——不是掉一点，是完全召不回</em>。"
            "<strong>过滤是硬约束，它的失败模式是断崖式的。</strong>",
            "形式化：无过滤时候选集是 $C$，过滤后是 $C \\cap F$。"
            "则 $\\text{recall} = 0$ 当且仅当所有相关块都不在 $F$ 里。"
            "<strong>与相似度不同，$F$ 里没有「排名靠后」这个中间状态。</strong>"
            "<em>工程上的对策是双路召回：一路带过滤、一路不带，"
            "再合并（C11 的 RRF）；"
            "并把「过滤后候选数为 0」当成一个必须报警的事件。</em>",
        ),
    ])),

    # ============================================================== 6
    ("dedup", "去重：RAG 里它有一个特有的后果", "".join([
        P("去重算法本身在 C43 讲过（MinHash / SimHash）。"
          "这一节只讲它在 RAG 里的一个特有后果，"
          "<strong>这个后果不是「浪费存储」，而是「浪费上下文预算」</strong>。"),
        ASCII("""
   语料里有 4 份近重复文档（同一份合同的四个版本）

   查询 → top-5 召回：
   ┌─────────────────────────────────────────┐
   │ 1. 合同v3 第2段   ← 内容 A               │
   │ 2. 合同v1 第2段   ← 内容 A（几乎同一句）  │
   │ 3. 合同v4 第2段   ← 内容 A               │
   │ 4. 合同v2 第2段   ← 内容 A               │
   │ 5. 附件说明 第1段 ← 内容 B               │
   └─────────────────────────────────────────┘
   有效独立信息量 = 2 条，而不是 5 条。
   **你花了 5 个块的上下文预算，买到了 2 个块的信息。**
"""),
        DUAL(
            "为什么近重复必然占满 top-k？因为<strong>相似度是内容的函数</strong>——"
            "内容几乎一样的块，得分也几乎一样，"
            "<em>所以它们会作为一个整体一起进 top-k 或一起不进</em>。"
            "<strong>k 越大，这个问题越严重，而不是越轻。</strong>",
            "定义<span class=\"term\">有效独立文档数</span>"
            "$\\text{eff}@k = |\\{\\text{去重后的内容簇}\\} \\cap \\text{top-}k|$。"
            "如果语料里某个内容有 $r$ 份近重复，"
            "那么在它们都排在前面的情况下 $\\text{eff}@k \\approx k - r + 1$。"
            "<strong>把 $\\text{eff}@k / k$ 当成一个监控指标</strong>——"
            "它掉下来通常意味着上游灌进了一批重复文档。"
            "<em>C11 的 MMR 可以在检索时缓解，但摄取时去重更便宜也更彻底。</em>",
        ),
        H3("三层去重，各管一件事"),
        TABLE(["层次", "手段", "抓什么", "注意"], [
            ["<strong>文档级精确</strong>", "<code>content_sha</code> 相同",
             "同一份文件被灌了两遍", "最便宜，一定要做"],
            ["<strong>文档级近重复</strong>", "MinHash / SimHash（C43）",
             "同一份文档的多个版本、格式转换副本",
             "<strong>不要直接删</strong>——保留最新版并用 <code>supersedes</code> 链接"],
            ["<strong>块级近重复</strong>", "块的 shingle 指纹",
             "页眉页脚、免责声明、模板文字",
             "这些块<em>与任何查询都有一点相关</em>，是噪声的主要来源"],
        ]),
        CALLOUT("warn", "块级去重有一个容易踩的坑："
                        "<strong>不要跨文档合并块</strong>。"
                        "两份不同合同里的同一句条款看起来是重复的，"
                        "但用户问「合同 X 里有没有这条」时，"
                        "<em>答案必须来自合同 X</em>。"
                        "正确做法是保留两份块、"
                        "在检索时按 <code>doc_id</code> 做多样性约束（每个 doc 最多进 n 个块）。"),
    ])),

    # ============================================================== 7
    ("contract", "摄取契约：让摄取可重放、可回滚、可删除", "".join([
        P("摄取是一个写操作，而写操作需要契约。"
          "本课的契约是四条，全部可以用几行代码实现（notebook 第 6 节）。"),
        OL([
            "<strong><code>doc_id</code> 一次分配、永不改变、永不复用</strong>。"
            "<em>它必须来自来源系统的稳定标识（文件路径 + 来源系统 ID），"
            "不能是内容哈希</em>——用内容哈希当 ID，改一个错别字这份文档的历史就断了"
            "（与 C68 模块 01 的稳定 ID 是同一条）。",
            "<strong>版本单调递增，<code>content_sha</code> 用来检测变化</strong>。"
            "<em>摄取时先算 sha：与当前版本相同就整份跳过（这是幂等性），"
            "不同就 version+1 并替换该 doc 的全部块。</em>",
            "<strong>块的主键是 <code>(doc_id, version, chunk_index)</code></strong>。"
            "写入用 upsert 而不是 append。"
            "<em>「同一份文档摄取两次索引里出现两份块」这个 bug 的唯一根因就是用了 append。</em>",
            "<strong>删除必须传播到索引，并且是可验证的</strong>。"
            "<em>删除操作要返回「删掉了几个块」，调用方要断言这个数与预期一致</em>——"
            "「删了但一个块都没删掉」是一个必须能被发现的失败。",
        ]),
        ASCII("""
   一次摄取的完整状态机

   新文档 ─────────────► [v1 已索引]
                             │
              内容变了       │      内容没变
         ┌───────────────────┴──────────────┐
         ▼                                  ▼
   [删 v1 全部块]                     [整份跳过]
   [写 v2 全部块]                     n_written = 0
   [v2 已索引]                        （幂等）
         │
         │  源库删除
         ▼
   [删该 doc 全部块] ──► 断言 n_deleted == 该 doc 的块数
   [写一条 tombstone]     ← 防止「被重新灌回来」
"""),
        P("<strong>最后一行的 tombstone 值得解释</strong>："
          "如果只是删了块，而上游的全量同步任务下一轮又把这份文档送进来，"
          "<em>它会被当成新文档重新索引</em>。"
          "删除记录（<code>doc_id</code> + 删除时间 + 原因）"
          "让摄取器能拒绝它，也让「为什么这份文档不在索引里」有答案。"),
    ])),

    # ============================================================== 8
    ("gate", "摄取质量门禁：六项可机器判定的检查", "".join([
        P("这一节把整个模块变成一段能放进 CI 的代码。"
          "<strong>六项检查，每一项都对应前面某一节的失败。</strong>"),
        TABLE(["#", "检查", "阈值怎么定", "抓的是哪一节的问题"], [
            ["1", "<strong>零文本页比例</strong>",
             "> 5% 报警", "扫描件走错了路径（没走 OCR）"],
            ["2", "<strong>表格块的比例与行转句覆盖率</strong>",
             "有表格但行转句为 0 → 阻断", "第 2 节：表格被拍平"],
            ["3", "<strong>元数据完整率</strong>",
             "<code>doc_id/version/source_uri/section_path</code> 缺任一 → 阻断",
             "第 5 节：元数据事后补不回来"],
            ["4", "<strong>OCR 平均置信度 / 抽样字符错误率</strong>",
             "低于基线 2σ 报警", "第 4 节：上游换了扫描设备"],
            ["5", "<strong>块级近重复比例</strong>",
             "> 20% 报警；<code>eff@10 / 10 < 0.6</code> 报警", "第 6 节：近重复占满 top-k"],
            ["6", "<strong>幂等性自检</strong>",
             "同一批重放一次，<code>n_written == 0</code>，否则阻断",
             "第 7 节：摄取契约"],
        ]),
        CALLOUT("intuition", "注意第 6 项的形式：<strong>它不是「检查代码写对了没有」，"
                             "而是「把同一批数据再摄取一遍，断言什么都没发生」</strong>。"
                             "<em>这是幂等性唯一可靠的验证方式</em>，"
                             "也是 C68 模块 00 的 <code>run ∘ run = run</code> 在摄取侧的对应物。"),
        P("门禁的两条使用纪律，与 C68 模块 04 一致："
          "<strong>确定性的检查（2/3/6）直接阻断，因为它们的误报率是零；"
          "统计性的检查（1/4/5）只报警，阈值从历史基线的方差推。</strong>"
          "<em>把统计检查设成阻断是「门禁被关掉」这一结局最常见的起点。</em>"),
    ])),

    # ============================================================== 9
    ("order", "摄取流水线的执行顺序：六步，顺序不能换", "".join([
        P("这一节把前八节合成一条可执行的流水线。"
          "<strong>六个步骤的顺序是有约束的——换一个位置就会有信息永久丢失。</strong>"),
        ASCII("""
   ① 解析（拿文字 + element 类型 + 坐标 + 页码）
        │   ← 唯一能拿到坐标的时刻。之后坐标就没了。
   ② 阅读顺序修正（分栏 / 剔页眉页脚 / 跨栏标题）
        │   ← 必须在 ① 之后（要坐标）、在 ③ 之前（表格分流要按修正后的顺序找上下文）
   ③ 表格分流（行转句 + 保留 markdown 原文）
        │   ← 必须在拼接成纯文本**之前**。拼完就分不出哪段是表格了。
   ④ 元数据抽取（section_path / effective_date / tenant / lang）
        │   ← 标题层级栈只在遍历 element 时存在
   ⑤ 去重（文档级精确 → 文档级近重复 → 块级）
        │   ← 必须在 ⑥ 之前：写进去再删比不写贵，而且中间状态会被检索到
   ⑥ 幂等写入（先删该 doc 旧版本，再 upsert；tombstone 检查）
"""),
        DUAL(
            "最容易被换错位置的是 ③ 和 ⑤。"
            "<strong>③ 放到「拼成纯文本之后」是最常见的错误</strong>——"
            "<em>一旦拼接完成，表格与正文就不可区分了</em>，"
            "而表格需要完全不同的处理路径（第 2 节）。"
            "<strong>⑤ 放到 ⑥ 之后（「先写进去，之后再跑一个去重任务」）"
            "会让近重复块在两次任务之间被检索到</strong>，"
            "而这段时间的行为无法解释。",
            "还有一条不在图里的约束：<strong>① 到 ⑥ 必须是同一个事务边界内的一次操作</strong>，"
            "或者至少是<em>可重放的</em>。"
            "<strong>如果流水线在 ④ 之后崩溃，重跑必须从 ① 开始，而不是从 ⑤ 继续</strong>——"
            "因为中间产物里没有坐标了。"
            "<em>实现上最简单的保证是：中间产物全部在内存里，只有 ⑥ 写外部存储</em>。"
            "这也意味着单篇文档的处理不应该跨进程拆分。",
        ),
        CALLOUT("intuition", "一个检验流水线设计的问题："
                             "<strong>「如果我想给已经索引过的文档补一个元数据字段，"
                             "需要重新解析吗？」</strong>"
                             "<em>需要 → 说明这个字段只能在解析时拿到，"
                             "那它就必须在第一遍就抽出来（第 5 节的判据）。</em>"),
    ])),
]

NB = [
    md("""# 01 · 文档摄取与解析（结构 / 顺序 / 噪声 / 元数据 / 去重 / 契约）

目标：把「解析丢了东西」这件事从模糊的担忧变成**六个可以测量的量**。

本 notebook 你会亲手实现：
1. **三种解析方式的可答性对比** —— 拍平后为什么检索指标正常但答案不可恢复
2. **双栏版面的阅读顺序** —— 按 y 排序 vs 先分栏，量出实体-属性错配率
3. **OCR 噪声的传导** —— 字符错误率 → 词级破坏率的理论值与实测值，以及词法/语义两条不同的衰减曲线
4. **元数据过滤的两面** —— precision 的收益，和写窄一格时 recall 的断崖
5. **近重复怎么占满 top-k** —— 有效独立文档数 eff@k
6. **幂等摄取契约** —— 状态机 + tombstone
7. **摄取质量门禁六项**

> 心智模型：**解析是流水线里唯一一个「做错了无法在下游补救」的环节。**"""),

    md("""## 0 · 环境与工具函数

复用模块 00 的玩具嵌入（中文取单字 + 二元组）。"""),

    code("""import os, re, json, math, hashlib, random
from collections import Counter, defaultdict

import numpy as np

DIM = 4096
RNG = np.random.default_rng(0)

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

def rank(cands, query, k=3):
    \"\"\"cands: [(id, text)]，返回 [(id, text, score)] 按分数降序取 k。\"\"\"
    if not cands:
        return []
    mat = np.stack([embed(t) for _, t in cands])
    s = mat @ embed(query)
    order = np.argsort(-s)[:k]
    return [(cands[i][0], cands[i][1], float(s[i])) for i in order]

print('numpy', np.__version__, '| 工具就位')"""),

    md("""## 1 · 结构损失：三种解析，同一份表格

关键观察：**拍平之后，检索照样召回那个块，块里每个字都在，但答案不可恢复。**"""),

    code("""TABLE_ROWS = [('北京', '2023', '1240'), ('北京', '2024', '1310'),
              ('上海', '2023', '1580'), ('上海', '2024', '1620')]

# 两个要恢复的关系：值与行名/年份的对应，以及值与列名的对应。
# 第二个常常被忘掉——但「1580 是营收还是成本」正是它决定的。
GOLD_ROW  = ('上海', '2023', '1580')     # 这个数属于哪一行
GOLD_COL  = ('上海', '营收', '1580')     # 这个数属于哪一列

def parse_structured(rows):
    \"\"\"① 行转句：每行一句，行名、列名、值全部带上。\"\"\"
    return [f'{city} 在 {year} 年的营收是 {val} 万元。' for city, year, val in rows]

def parse_row_major(rows):
    \"\"\"② 行主序拍平：按行把单元格连起来（很多解析器的默认行为）。\"\"\"
    cells = ['地区', '年份', '营收']
    for r in rows:
        cells += list(r)
    return [' '.join(cells)]

def parse_col_major(rows):
    \"\"\"③ 列主序拍平：按列读——PDF 里按 x 坐标优先排序时的真实结果。\"\"\"
    return [' '.join(['地区'] + [r[0] for r in rows]
                     + ['年份'] + [r[1] for r in rows]
                     + ['营收'] + [r[2] for r in rows])]

def parse_row_major_chunked(rows, size=43):
    \"\"\"④ 行主序拍平之后按字符数硬切。
    size=43 刻意让块边界落在「上海 2023 | 1580」这一行内部——
    在几百行的大表上，这件事必然会发生在某些行上。\"\"\"
    t = parse_row_major(rows)[0]
    return [t[i:i + size] for i in range(0, len(t), size)]

def locally_recoverable(pieces, rel, window=20):
    \"\"\"判据：存在一个不超过 window 字符的局部窗口，同时含有关系的三个元素。

    为什么用「局部窗口」而不是「三个元素都在文本里」——
    后者对所有四种解析都成立（字一个都没少），完全区分不出可答与不可答。
    局部性才是模型能可靠利用的东西：跨越几十个 token 去重建表格的行列对应，
    正是模型最不可靠的操作之一。\"\"\"
    return any(all(x in t[i:i + window] for x in rel)
               for t in pieces for i in range(len(t)))

QUERY = '上海 2023 年的营收是多少'
print(f"{'解析方式':<16}{'片段':>5}{'top1 相似度':>13}{'字都在':>8}"
      f"{'行对应':>8}{'列对应':>8}")
res = {}
for name, fn in [('① 行转句', parse_structured),
                 ('② 行主序拍平', parse_row_major),
                 ('③ 列主序拍平', parse_col_major),
                 ('④ 行主序+硬切', parse_row_major_chunked)]:
    pieces = fn(TABLE_ROWS)
    top = rank([(f'{name}-{i}', t) for i, t in enumerate(pieces)], QUERY, k=1)[0]
    present = all(any(x in t for t in pieces) for x in set(GOLD_ROW + GOLD_COL))
    r_row = locally_recoverable(pieces, GOLD_ROW)
    r_col = locally_recoverable(pieces, GOLD_COL)
    res[name] = (top[2], present, r_row, r_col)
    print(f'{name:<16}{len(pieces):>5}{top[2]:>13.3f}{str(present):>8}'
          f'{str(r_row):>8}{str(r_col):>8}')

assert all(r[1] for r in res.values()), '四种解析里字都没少——所以「字在不在」不是有用的判据'
assert res['① 行转句'][2] and res['① 行转句'][3], '行转句必须同时保留行与列的对应'
assert res['② 行主序拍平'][2] and not res['② 行主序拍平'][3], \\
    '行主序：值与行名相邻（能扛住），但列名丢在开头'
assert not res['③ 列主序拍平'][2] and not res['③ 列主序拍平'][3], '列主序两者全丢'
assert not res['④ 行主序+硬切'][2] and not res['④ 行主序+硬切'][3], '硬切两者全丢'
assert res['③ 列主序拍平'][0] > 0.3, '不可恢复的那个块，相似度依然不低'

print('\\n✅ 三个结论，第二个最容易被想错：')
print('   ① 只有行转句同时保住了「哪一行」和「哪一列」。')
print('   ② 行主序拍平在小表上其实扛住了行对应——单元格与行名恰好相邻。')
print('      所以「拍平必然丢结构」是个错的说法。但它丢了**列名**：')
print('      「营收」只在开头出现一次，离 1580 有几十个 token。')
print('   ③ 真正让行对应也崩掉的是两个具体条件：列主序读取，以及块边界落在行内。')
print('      这两个条件在真实文档上都很常见——PDF 按 x 排序就得到列主序，')
print('      几百行的大表必然有若干行被边界切开。')
print('\\n   注意最后一列以外的那一列：四种解析的「字都在」全是 True，')
print('   而不可恢复的块与查询的相似度依然 > 0.3。Precision@1 满分，端到端错。')
print('\\n   工程含义不是「拍平有时可以」，而是相反：不要把它当概率事件去赌。')
print('   行转句对 ③ 和 ④ 都免疫，实现只有五行。')"""),


    md("""## 2 · 阅读顺序：双栏版面

合成一个双栏版面：左栏讲 A 产品，右栏讲 B 产品，每栏三段。
两种拼接方式，量出**实体-属性错配率**：一个块里同时出现两个产品名就算错配。"""),

    code("""# (x, y, text)：左栏 x=50，右栏 x=320
LAYOUT = [
    (50, 100, 'A 型机的额定功率是 1200 瓦。'),
    (50, 200, 'A 型机的工作温度范围是 0 到 40 摄氏度。'),
    (50, 300, 'A 型机的保修期是 24 个月。'),
    (320, 100, 'B 型机的额定功率是 2400 瓦。'),
    (320, 200, 'B 型机的工作温度范围是 -10 到 55 摄氏度。'),
    (320, 300, 'B 型机的保修期是 36 个月。'),
]

def order_by_y(blocks):
    \"\"\"❌ 只按 y 排（单栏文档上是对的，双栏上交错）。\"\"\"
    return [t for _, _, t in sorted(blocks, key=lambda b: (b[1], b[0]))]

def order_by_column(blocks, gap=100):
    \"\"\"✅ 先按 x 聚成栏，栏内按 y 排。\"\"\"
    xs = sorted({b[0] for b in blocks})
    cols, cur = [], [xs[0]]
    for x in xs[1:]:
        (cur.append(x) if x - cur[-1] < gap else (cols.append(cur), cur := [x]))
    cols.append(cur)
    out = []
    for col in cols:
        out += [t for _, _, t in sorted([b for b in blocks if b[0] in col],
                                        key=lambda b: b[1])]
    return out

def chunk_text(pieces, size=40):
    joined = ''.join(pieces)
    return [joined[i:i + size] for i in range(0, len(joined), size)]

def mismatch_rate(chunks, entities=('A 型机', 'B 型机')):
    \"\"\"一个块里同时出现两个实体 → 实体-属性可能错配。\"\"\"
    bad = sum(1 for c in chunks if all(e in c for e in entities))
    return bad / len(chunks)

print(f"{'块大小':>7}{'按 y 排序':>12}{'先分栏':>10}")
bad_rates, good_rates = [], []
for size in [30, 40, 50, 60, 80]:
    mr_bad = mismatch_rate(chunk_text(order_by_y(LAYOUT), size))
    mr_good = mismatch_rate(chunk_text(order_by_column(LAYOUT), size))
    bad_rates.append(mr_bad); good_rates.append(mr_good)
    print(f'{size:>7}{mr_bad:>12.0%}{mr_good:>10.0%}')

print('\\n首块对比:')
print('  按 y 排序:', chunk_text(order_by_y(LAYOUT), 40)[0])
print('  先分栏  :', chunk_text(order_by_column(LAYOUT), 40)[0])

assert all(g <= b for g, b in zip(good_rates, bad_rates)), '分栏在任何块大小下都不该更差'
assert np.mean(good_rates) < np.mean(bad_rates), '平均错配率必须下降'
assert min(good_rates) == 0.0, '至少在某些块大小下能做到零错配'
print(f'\\n✅ 平均错配率从 {np.mean(bad_rates):.0%} 降到 {np.mean(good_rates):.0%}。')
print('   两个细节值得注意：')
print('   ① 分栏之后错配率不总是 0——**两栏交界处的那个块**天然会同时含两个实体。')
print('      这已经不是阅读顺序问题，而是块边界问题（模块 02 处理）。')
print('   ② 按 y 排序在单栏文档上完全正确，所以这个 bug 在测试文档上常常不出现；')
print('      它需要一份真正的双栏 PDF 才会暴露。')
print('   ③ 两种拼接产生的文本都「读起来通顺」——错误不会报错。')"""),

    md("""## 3 · OCR 噪声：字符错误率怎么放大

两件事：
1. 验证 $P(\\text{词被毁}) = 1-(1-\\varepsilon)^L$——长词先坏。
2. 对比两条衰减曲线：**精确匹配**（词法）是断崖式的，**字符 n-gram 相似度**（语义替身）是渐进的。"""),

    code("""CONFUSE_POOL = '口日曰目臼白甲由申田巳己已'

def corrupt(text, eps, rng):
    \"\"\"以 eps 的概率把每个字符替换成一个**不同的**字符（模拟 OCR 混淆）。

    注意「不同的」这三个字：如果替换池里包含原字符，
    实际错误率会低于 eps（本例低 1/13），理论公式就对不上了。
    这是一个真实存在的实现坑——注入故障时要确认故障真的注入了。\"\"\"
    out = []
    for ch in text:
        if rng.random() < eps:
            alt = [c for c in CONFUSE_POOL if c != ch]
            out.append(alt[int(rng.integers(len(alt)))])
        else:
            out.append(ch)
    return ''.join(out)

# --- 3a. 词级破坏率：理论 vs 实测 ---
print('词级破坏率（eps=3%）')
print(f"{'词长 L':>7}{'理论 1-(1-e)^L':>16}{'实测':>9}")
eps = 0.03
for L in [2, 4, 6, 8, 12]:
    word = '甲' * L
    rng = np.random.default_rng(L)
    trials = 20000
    broken = sum(1 for _ in range(trials) if corrupt(word, eps, rng) != word)
    theory = 1 - (1 - eps) ** L
    print(f'{L:>7}{theory:>16.3f}{broken / trials:>9.3f}')
    assert abs(theory - broken / trials) < 0.02, f'L={L} 理论与实测应当吻合'

print('\\n✅ 长词先坏：L 从 2 到 12，破坏率从 %.1f%% 涨到 %.1f%%。'
      % (100 * (1 - 0.97 ** 2), 100 * (1 - 0.97 ** 12)))
print('   而专有名词、型号、法条编号恰恰都是长串。')"""),

    code("""# --- 3b. 两条衰减曲线 ---
DOC = '产品型号 XJ7720B 的额定功率是 1200 瓦，保修期为 24 个月。'
Q_TERMS = ['XJ7720B', '额定功率', '保修期']

def lexical_hit(noisy, terms):
    \"\"\"词法检索的替身：所有关键词都必须精确出现。\"\"\"
    return all(t in noisy for t in terms)

def semantic_sim(noisy, clean):
    \"\"\"语义检索的替身：字符 n-gram 相似度（降级是渐进的）。\"\"\"
    return float(np.dot(embed(noisy), embed(clean)))

print(f"{'eps':>6}{'词法精确命中率':>16}{'语义相似度':>13}")
lex_curve, sem_curve = [], []
for eps in [0.0, 0.005, 0.01, 0.03, 0.05, 0.10]:
    hits, sims = [], []
    for t in range(400):
        rng = np.random.default_rng(1000 * t + int(eps * 10000))
        noisy = corrupt(DOC, eps, rng)
        hits.append(lexical_hit(noisy, Q_TERMS))
        sims.append(semantic_sim(noisy, DOC))
    lex_curve.append(np.mean(hits)); sem_curve.append(np.mean(sims))
    print(f'{eps:>6.3f}{np.mean(hits):>16.2%}{np.mean(sims):>13.3f}')

# 词法的相对跌幅必须显著大于语义的
lex_drop = (lex_curve[0] - lex_curve[3]) / lex_curve[0]        # eps=3%
sem_drop = (sem_curve[0] - sem_curve[3]) / sem_curve[0]
print(f'\\neps=3% 时：词法相对跌 {lex_drop:.0%}，语义相对跌 {sem_drop:.0%}')
assert lex_drop > 3 * sem_drop, '词法应当比语义衰减快得多'
assert lex_curve[-1] < 0.3, 'eps=10% 时词法基本失效'
print('✅ 同一个噪声水平，两条召回路径的衰减速度差一个量级。')
print('   这是「混合检索」在扫描件语料上的一个非常实际的动机（C11 模块 01）。')"""),

    md("""## 4 · 元数据过滤：收益与断崖

加上正确的章节过滤 → precision 上升。
把过滤条件写窄一格 → **recall 直接掉到 0**，而检索层不会报错。"""),

    code("""CORPUS = [
    # (chunk_id, section, text)
    ('c1', '年假',   '正式员工每年享有 15 天带薪年假。'),
    ('c2', '年假',   '试用期员工每年享有 5 天带薪年假。'),
    ('c3', '病假',   '病假每年累计不超过 15 天，需提供医疗证明。'),
    ('c4', '婚假',   '婚假为 10 天，需在登记后一年内使用。'),
    ('c5', '报销',   '餐饮报销的单次上限是 200 元。'),
    ('c6', '报销',   '差旅报销的单次上限是 3000 元。'),
    ('c7', '考勤',   '每月迟到累计超过 3 次计一次警告。'),
    ('c8', '培训',   '每位员工每年有 2000 元培训预算。'),
]
Q = '正式员工的年假有多少天'
RELEVANT = {'c1'}

def search(corpus, query, k=3, sections=None):
    cands = [(cid, txt) for cid, sec, txt in corpus
             if sections is None or sec in sections]
    return [cid for cid, _, _ in rank(cands, query, k=k)], len(cands)

for label, secs in [('不过滤', None), ('正确过滤（年假）', {'年假'}),
                    ('写窄一格（病假）', {'病假'})]:
    got, n_cand = search(CORPUS, Q, k=3, sections=secs)
    prec = len(set(got) & RELEVANT) / len(got)
    rec = len(set(got) & RELEVANT) / len(RELEVANT)
    print(f'{label:<18} 候选 {n_cand:>2} | top3={got} | P@3 {prec:.2f} | R {rec:.2f}')

p_no, _ = search(CORPUS, Q, 3, None)
p_ok, _ = search(CORPUS, Q, 3, {'年假'})
p_bad, n_bad = search(CORPUS, Q, 3, {'病假'})
assert len(set(p_ok) & RELEVANT) / len(p_ok) > len(set(p_no) & RELEVANT) / len(p_no), \\
    '正确过滤应当提升 precision'
assert len(set(p_bad) & RELEVANT) == 0, '过滤写错时 recall 是 0，不是「差一点」'
print('\\n✅ 过滤是硬约束：它没有「排名靠后」这个中间状态。')
print('   所以「过滤后候选数为 0 或过小」必须是一个报警事件——')
print(f'   本例里写窄一格后候选只剩 {n_bad} 条，这个数本身就是信号。')"""),

    md("""## 5 · 近重复占满 top-k

四份近重复文档（同一份合同的四个版本）+ 若干独立文档。
量 **eff@k**：top-k 里有多少个「内容簇」。"""),

    code("""def shingles(text, n=4):
    t = re.sub(r'\\s+', '', text)
    return {t[i:i + n] for i in range(max(1, len(t) - n + 1))}

def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0

def cluster(corpus, thr=0.7):
    \"\"\"按 Jaccard 把近重复聚成簇（并查集的朴素版）。\"\"\"
    ids = [cid for cid, _ in corpus]
    sh = {cid: shingles(t) for cid, t in corpus}
    parent = {i: i for i in ids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if jaccard(sh[ids[i]], sh[ids[j]]) >= thr:
                parent[find(ids[i])] = find(ids[j])
    return {cid: find(cid) for cid in ids}

BASE_CLAUSE = '乙方应在合同签订后 30 日内完成交付，逾期按日收取千分之一的违约金。'
DUPES = [(f'contract-v{v}', BASE_CLAUSE + f'（版本 {v}）') for v in range(1, 5)]
OTHERS = [
    ('attach-1', '附件说明：交付验收由甲方指定的第三方机构完成。'),
    ('policy-1', '公司差旅报销的单次上限是 3000 元。'),
    ('policy-2', '设备损坏需在两个工作日内报修。'),
]
CORP2 = DUPES + OTHERS
CL = cluster(CORP2)
print('内容簇:', Counter(CL.values()).most_common())

QC = '交付逾期的违约金怎么算'
def eff_at_k(corpus, clusters, query, k):
    top = [cid for cid, _, _ in rank(corpus, query, k=k)]
    return len({clusters[c] for c in top}), top

for k in [2, 3, 5]:
    eff, top = eff_at_k(CORP2, CL, QC, k)
    print(f'k={k}: top-k={top} | eff@k={eff} | eff/k={eff / k:.2f}')

eff5, _ = eff_at_k(CORP2, CL, QC, 5)
assert eff5 < 5, '近重复必然压低 eff@k'
# 去重后（每簇只留一份）再看
seen, deduped = set(), []
for cid, t in CORP2:
    if CL[cid] not in seen:
        seen.add(CL[cid]); deduped.append((cid, t))
eff5_dd, top_dd = eff_at_k(deduped, CL, QC, min(5, len(deduped)))
print(f'\\n去重后语料 {len(deduped)} 条 | eff@{min(5, len(deduped))}={eff5_dd}')
assert eff5_dd > eff5, '摄取时去重应当提升有效独立信息量'
print(f'✅ eff@5 从 {eff5} 提升到 {eff5_dd}——同样的上下文预算买到更多信息。')
print('   注意结论不是「删掉重复文档」：合同版本要保留，')
print('   正确做法是保留最新版 + supersedes 链接，或在检索时按 doc_id 限流。')"""),

    md("""## 6 · 幂等摄取契约

四条契约的实现。注意 `ingest_batch` 的返回值——
**它必须报告写了几个块、删了几个块，否则调用方无法断言任何东西。**"""),

    code("""class Store:
    def __init__(self):
        self.blocks = {}                 # (doc_id, version, idx) -> chunk
        self.doc_version = {}            # doc_id -> version
        self.doc_sha = {}                # doc_id -> content_sha
        self.tombstones = {}             # doc_id -> reason

    # --- 查询 ---
    def chunks_of(self, doc_id):
        return [k for k in self.blocks if k[0] == doc_id]

    def live_chunks(self):
        return [self.blocks[k] for k in self.blocks]

def split(text, size=40):
    return [text[i:i + size] for i in range(0, len(text), size)]

def ingest_batch(store, docs, size=40):
    \"\"\"docs: [(doc_id, text)]。返回统计字典。\"\"\"
    st = dict(written=0, deleted=0, skipped=0, rejected=0)
    for doc_id, text in docs:
        if doc_id in store.tombstones:
            st['rejected'] += 1                     # 契约 4：拒绝被删过的文档
            continue
        sha = hashlib.sha256(text.encode()).hexdigest()[:12]
        if store.doc_sha.get(doc_id) == sha:
            st['skipped'] += 1                      # 契约 2：内容没变，整份跳过
            continue
        for k in store.chunks_of(doc_id):           # 契约 2：先删旧版本
            del store.blocks[k]; st['deleted'] += 1
        v = store.doc_version.get(doc_id, 0) + 1
        for i, piece in enumerate(split(text, size)):
            store.blocks[(doc_id, v, i)] = dict(    # 契约 3：主键 upsert
                doc_id=doc_id, version=v, chunk_index=i, text=piece,
                start=i * size, end=i * size + len(piece))
            st['written'] += 1
        store.doc_version[doc_id] = v; store.doc_sha[doc_id] = sha
    return st

def delete_doc(store, doc_id, reason='user_request'):
    n = 0
    for k in store.chunks_of(doc_id):
        del store.blocks[k]; n += 1
    store.tombstones[doc_id] = reason
    store.doc_sha.pop(doc_id, None)
    return n

# --- 走一遍状态机 ---
S = Store()
DOCS = [('d1', 'A' * 100), ('d2', 'B' * 60)]
print('首次摄取     ', ingest_batch(S, DOCS))
print('原样重放     ', ingest_batch(S, DOCS), '← 幂等：written 必须是 0')
print('d1 内容变了  ', ingest_batch(S, [('d1', 'A' * 100 + '新增一段')]))
n_del = delete_doc(S, 'd2')
print(f'删除 d2      删掉 {n_del} 个块')
print('全量同步重来 ', ingest_batch(S, DOCS), '← tombstone 拒绝了 d2')

versions = sorted({k[1] for k in S.chunks_of('d1')})
print(f'\\nd1 当前在索引里的版本: {versions}')
replay = ingest_batch(S, DOCS)
assert replay['written'] == 0, '幂等性：重放不应写入任何块'
assert len(versions) == 1, f'同一时刻索引里只能有一个版本，实际 {versions}'
assert S.chunks_of('d2') == [], '删除必须在索引里生效'
assert replay['rejected'] == 1, 'tombstone 必须阻止被删文档被重新灌回'
print('\\n✅ 四条契约都可验证。第 6 项门禁就是「把同一批数据再摄取一遍，断言 written == 0」。')
print(f'   一个值得注意的细节：d1 现在是 v{versions[0]} 而不是 v2——')
print('   因为「全量同步重来」那一步送进来的是**原始内容**，与 v2 不同，')
print('   于是它被正确地当成了又一次内容变更。')
print('   **版本号计的是变更次数，不是内容的身份**；内容回退不会复用旧版本号。')"""),

    md("""## 7 · 摄取质量门禁：六项检查

确定性检查（2/3/6）阻断，统计检查（1/4/5）报警——与 C68 模块 04 的分级一致。"""),

    code("""REQUIRED_META = ('doc_id', 'version', 'source_uri', 'section_path')

def ingest_gate(report, baseline):
    \"\"\"返回 (blocking, warnings)：两个 list。\"\"\"
    blocking, warn = [], []
    # 确定性 —— 零误报，直接阻断
    if report['n_tables'] > 0 and report['n_table_rows_rendered'] == 0:
        blocking.append('有表格但行转句为 0（表格被拍平）')
    missing = [k for k in REQUIRED_META if report['meta_complete'].get(k, 0) < 1.0]
    if missing:
        blocking.append(f'元数据不完整: {missing}')
    if report['replay_written'] != 0:
        blocking.append(f"摄取不幂等: 重放写入了 {report['replay_written']} 个块")
    # 统计 —— 只报警，阈值从基线推
    if report['blank_page_ratio'] > 0.05:
        warn.append(f"零文本页 {report['blank_page_ratio']:.1%} > 5%（可能没走 OCR）")
    lo = baseline['ocr_conf_mean'] - 2 * baseline['ocr_conf_sd']
    if report['ocr_conf'] < lo:
        warn.append(f"OCR 置信度 {report['ocr_conf']:.3f} < 基线-2σ ({lo:.3f})")
    if report['eff_at_10'] / 10 < 0.6:
        warn.append(f"eff@10/10 = {report['eff_at_10'] / 10:.2f} < 0.6（近重复过多）")
    return blocking, warn

BASELINE = dict(ocr_conf_mean=0.95, ocr_conf_sd=0.01)
HEALTHY = dict(n_tables=3, n_table_rows_rendered=42,
               meta_complete={k: 1.0 for k in REQUIRED_META},
               replay_written=0, blank_page_ratio=0.01, ocr_conf=0.96, eff_at_10=8)

cases = {
    '健康':        HEALTHY,
    '表格被拍平':  {**HEALTHY, 'n_table_rows_rendered': 0},
    '缺元数据':    {**HEALTHY, 'meta_complete': {**HEALTHY['meta_complete'], 'section_path': 0.4}},
    '不幂等':      {**HEALTHY, 'replay_written': 17},
    '扫描件没OCR': {**HEALTHY, 'blank_page_ratio': 0.31},
    '近重复过多':  {**HEALTHY, 'eff_at_10': 4},
}
for name, rep in cases.items():
    b, w = ingest_gate(rep, BASELINE)
    verdict = '阻断' if b else ('警告' if w else '通过')
    print(f'{name:<12} {verdict:<4} {(b + w)[0] if (b + w) else ""}')

assert ingest_gate(HEALTHY, BASELINE) == ([], [])
assert ingest_gate(cases['表格被拍平'], BASELINE)[0], '表格被拍平必须阻断'
assert ingest_gate(cases['不幂等'], BASELINE)[0], '不幂等必须阻断'
assert not ingest_gate(cases['近重复过多'], BASELINE)[0], '统计类只报警不阻断'
assert ingest_gate(cases['近重复过多'], BASELINE)[1], '但必须报警'
print('\\n✅ 六项门禁。分级的理由：确定性检查误报率为零，可以阻断；')
print('   统计检查会误报，阻断它们是「门禁被关掉」这一结局的起点（C68-04）。')"""),

    md("""## ✏️ 练习 1：阅读顺序恢复（带页眉页脚）

在第 2 节的分栏基础上加两件真实的事：
- **页眉/页脚**：y 极小或极大的窄块，必须剔除
- **跨栏标题**：宽度接近页宽的块，必须排在所有栏之前

实现 `reading_order(blocks, page_w=400)`，`blocks` 是 `(x, y, w, text)`。
返回正确顺序的 text 列表。"""),

    code("""def reading_order(blocks, page_w=400, header_y=60, footer_y=740, col_gap=100):
    \"\"\"返回按正确阅读顺序排列的 text 列表。
    规则：① 丢掉 y < header_y 或 y > footer_y 的块；
          ② w >= 0.8 * page_w 的块是跨栏标题，按 y 排在最前；
          ③ 其余按 x 聚栏（间隔 >= col_gap 算新栏），栏内按 y 排。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
PAGE = [
    (50,  20, 300, '第 3 页  内部资料'),          # 页眉 → 丢
    (50,  70, 340, '第二章 产品参数'),            # 跨栏标题（w=340 >= 320）
    (50, 120, 150, 'A 型机的额定功率是 1200 瓦。'),
    (50, 220, 150, 'A 型机的保修期是 24 个月。'),
    (320, 120, 150, 'B 型机的额定功率是 2400 瓦。'),
    (320, 220, 150, 'B 型机的保修期是 36 个月。'),
    (50, 780, 300, '- 12 -'),                     # 页脚 → 丢
]
got = reading_order(PAGE)
assert len(got) == 5, f'页眉页脚应当被剔除，得到 {len(got)} 段'
assert got[0] == '第二章 产品参数', '跨栏标题排最前'
assert got[1].startswith('A 型机的额定功率'), '左栏在前'
assert got[2].startswith('A 型机的保修期'), '栏内按 y'
assert got[3].startswith('B 型机的额定功率'), '再到右栏'
assert '内部资料' not in ''.join(got) and '- 12 -' not in ''.join(got)
print('✅ 练习 1 通过：标题 → 左栏 → 右栏，页眉页脚已剔除')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def reading_order(blocks, page_w=400, header_y=60, footer_y=740, col_gap=100):
    body = [b for b in blocks if header_y <= b[1] <= footer_y]
    spans = [b for b in body if b[2] >= 0.8 * page_w]
    rest = [b for b in body if b[2] < 0.8 * page_w]
    out = [t for _, _, _, t in sorted(spans, key=lambda b: b[1])]
    xs = sorted({b[0] for b in rest})
    cols, cur = [], []
    for x in xs:
        if cur and x - cur[-1] >= col_gap:
            cols.append(cur); cur = []
        cur.append(x)
    if cur:
        cols.append(cur)
    for col in cols:
        out += [t for _, _, _, t in
                sorted([b for b in rest if b[0] in col], key=lambda b: b[1])]
    return out

got = reading_order(PAGE)
assert len(got) == 5 and got[0] == '第二章 产品参数'
assert got[1].startswith('A 型机的额定功率') and got[3].startswith('B 型机的额定功率')
assert '内部资料' not in ''.join(got) and '- 12 -' not in ''.join(got)
print('✅ 参考答案 1 通过')
print('   三条规则的顺序不能换：先剔页眉页脚，再抽跨栏标题，最后才分栏。')
print('   反过来做的话，页眉（也是宽块）会被当成跨栏标题排到最前面。')"""),

    md("""## ✏️ 练习 2：OCR 噪声下的关键词存活率

实现 `survival_rate(terms, eps)`：解析式地算出「查询里所有关键词都精确存活」的概率
$\\prod_i (1-\\varepsilon)^{L_i}$，并实现 `survival_empirical` 用采样验证。

然后回答一个工程问题：**给定 eps 与关键词，最多能容忍几个关键词？**
实现 `max_terms_under(eps, target, word_len)` —— 在存活率不低于 `target` 的前提下，
查询最多能含几个长度为 `word_len` 的关键词。"""),

    code("""def survival_rate(terms, eps):
    \"\"\"所有 term 都精确存活的理论概率。\"\"\"
    # TODO
    raise NotImplementedError

def max_terms_under(eps, target, word_len):
    \"\"\"返回满足 (1-eps)^(m*word_len) >= target 的最大整数 m（m >= 0）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
assert abs(survival_rate(['abcd'], 0.0) - 1.0) < 1e-12
assert abs(survival_rate(['ab'], 0.1) - 0.81) < 1e-9
assert abs(survival_rate(['ab', 'cdef'], 0.1) - 0.9 ** 6) < 1e-9

# 采样验证
def survival_empirical(terms, eps, trials=4000, seed=0):
    rng = np.random.default_rng(seed)
    ok = 0
    for _ in range(trials):
        ok += all(corrupt(t, eps, rng) == t for t in terms)
    return ok / trials
th = survival_rate(['甲乙丙', '丁戊'], 0.05)
em = survival_empirical(['甲乙丙', '丁戊'], 0.05)
print(f'理论 {th:.3f} vs 实测 {em:.3f}')
assert abs(th - em) < 0.03, '理论与实测应当吻合'

assert max_terms_under(0.03, 0.8, 6) == 1, max_terms_under(0.03, 0.8, 6)
assert max_terms_under(0.01, 0.8, 6) == 3, max_terms_under(0.01, 0.8, 6)
assert max_terms_under(0.0, 0.8, 6) >= 100, 'eps=0 时不受限'
print('✅ 练习 2 通过：eps=3% 时，6 字关键词最多只能要求 1 个精确命中')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def survival_rate(terms, eps):
    total_len = sum(len(t) for t in terms)
    return (1 - eps) ** total_len

def max_terms_under(eps, target, word_len):
    if eps <= 0:
        return 10 ** 6
    m = 0
    while (1 - eps) ** ((m + 1) * word_len) >= target:
        m += 1
        if m > 10 ** 6:
            break
    return m

assert abs(survival_rate(['ab'], 0.1) - 0.81) < 1e-9
assert abs(survival_rate(['ab', 'cdef'], 0.1) - 0.9 ** 6) < 1e-9
assert max_terms_under(0.03, 0.8, 6) == 1
assert max_terms_under(0.01, 0.8, 6) == 3
assert max_terms_under(0.0, 0.8, 6) >= 100
print('✅ 参考答案 2 通过')
print('   这个函数的用途是定容量：它告诉你在给定 OCR 质量下，')
print('   「要求 N 个关键词同时精确命中」这个检索策略还成不成立。')
print('   eps=3% 时答案是 1——也就是说纯词法检索已经不能作为唯一召回路径。')"""),

    md("""## ✏️ 练习 3：块级去重 + 保留最新版

实现 `dedup_keep_latest(corpus, thr=0.7)`：
`corpus` 是 `[(doc_id, version, text)]`。把近重复聚簇，**每簇只保留 version 最大的那条**，
并返回 `(kept, supersedes)`，其中 `supersedes[被丢弃的 doc_id] = 保留的 doc_id`。

这是第 5 节说的「不要直接删」的落地：被丢弃的版本要能被追溯。"""),

    code("""def dedup_keep_latest(corpus, thr=0.7):
    \"\"\"返回 (kept, supersedes)。
    kept: [(doc_id, version, text)]，每个内容簇一条（version 最大）
    supersedes: {丢弃的 doc_id: 保留的 doc_id}\"\"\"
    # TODO：复用第 5 节的 shingles / jaccard
    raise NotImplementedError"""),

    code("""# —— 自测 ——
C3 = [('k-v1', 1, BASE_CLAUSE + '（版本 1）'),
      ('k-v3', 3, BASE_CLAUSE + '（版本 3）'),
      ('k-v2', 2, BASE_CLAUSE + '（版本 2）'),
      ('other', 1, '公司差旅报销的单次上限是 3000 元。'),
      ('other2', 1, '设备损坏需在两个工作日内报修。')]
kept, sup = dedup_keep_latest(C3, thr=0.7)
kept_ids = sorted(d for d, _, _ in kept)
assert kept_ids == ['k-v3', 'other', 'other2'], kept_ids
assert sup == {'k-v1': 'k-v3', 'k-v2': 'k-v3'}, sup
# 每条被丢弃的都能追溯到保留的那条
assert all(v in kept_ids for v in sup.values())
# 不该跨内容合并
assert 'other' not in sup and 'other2' not in sup
print(f'✅ 练习 3 通过：{len(C3)} 条 → 保留 {len(kept)} 条，{len(sup)} 条可追溯')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def dedup_keep_latest(corpus, thr=0.7):
    ids = [c[0] for c in corpus]
    meta = {c[0]: (c[1], c[2]) for c in corpus}
    sh = {c[0]: shingles(c[2]) for c in corpus}
    parent = {i: i for i in ids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if jaccard(sh[ids[i]], sh[ids[j]]) >= thr:
                parent[find(ids[i])] = find(ids[j])
    groups = defaultdict(list)
    for cid in ids:
        groups[find(cid)].append(cid)
    kept, sup = [], {}
    for members in groups.values():
        winner = max(members, key=lambda c: (meta[c][0], c))
        kept.append((winner, meta[winner][0], meta[winner][1]))
        for m in members:
            if m != winner:
                sup[m] = winner
    return kept, sup

kept, sup = dedup_keep_latest(C3, thr=0.7)
assert sorted(d for d, _, _ in kept) == ['k-v3', 'other', 'other2']
assert sup == {'k-v1': 'k-v3', 'k-v2': 'k-v3'}
print('✅ 参考答案 3 通过')
print('   supersedes 链是关键：用户问「旧版本里写的是什么」时你还答得上来，')
print('   而如果直接删掉，这个问题就永久失去了答案。')"""),

    md("""## ✏️ 练习 4：完整的摄取报告生成器

把前面所有量凑成一份报告，喂给第 7 节的 `ingest_gate`。

实现 `make_report(store, docs, tables, metas, ocr_conf, blank_pages, n_pages)`：
- `replay_written`：原样重放一次 `ingest_batch` 得到的 `written`
- `meta_complete`：每个必需字段的完整率（有值且非空的比例）
- `eff_at_10`：对一个固定探针查询算 eff@10（语料不足 10 条时按实际条数算簇数）
- 其余直接透传"""),

    code("""def make_report(store, docs, tables, metas, ocr_conf, blank_pages, n_pages,
                probe='交付逾期的违约金怎么算'):
    \"\"\"返回可直接喂给 ingest_gate 的 dict。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
S2 = Store()
D2 = [('a', BASE_CLAUSE + '（版本 1）'), ('b', BASE_CLAUSE + '（版本 2）'),
      ('c', '公司差旅报销的单次上限是 3000 元。')]
ingest_batch(S2, D2, size=200)
METAS = [dict(doc_id='a', version=1, source_uri='s3://a', section_path='第一章'),
         dict(doc_id='b', version=1, source_uri='s3://b', section_path='第一章'),
         dict(doc_id='c', version=1, source_uri='s3://c', section_path='')]   # 缺一个
rep = make_report(S2, D2, tables=2, metas=METAS,
                  ocr_conf=0.96, blank_pages=1, n_pages=50)
print({k: v for k, v in rep.items() if k != 'meta_complete'})
print('meta_complete:', rep['meta_complete'])

assert rep['replay_written'] == 0, '重放必须为 0'
assert abs(rep['blank_page_ratio'] - 0.02) < 1e-9
assert abs(rep['meta_complete']['section_path'] - 2 / 3) < 1e-9
assert rep['meta_complete']['doc_id'] == 1.0
b, w = ingest_gate(rep, BASELINE)
assert any('元数据' in x for x in b), '缺 section_path 必须阻断'
print(f'✅ 练习 4 通过：门禁给出 {len(b)} 项阻断、{len(w)} 项警告')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def make_report(store, docs, tables, metas, ocr_conf, blank_pages, n_pages,
                probe='交付逾期的违约金怎么算'):
    replay = ingest_batch(store, docs, size=200)
    complete = {}
    for key in REQUIRED_META:
        got = sum(1 for m in metas if m.get(key) not in (None, '', []))
        complete[key] = got / len(metas) if metas else 0.0
    corpus = [(c['doc_id'] + f"#{c['chunk_index']}", c['text'])
              for c in store.live_chunks()]
    k = min(10, len(corpus))
    if corpus:
        cl = cluster(corpus, thr=0.7)
        top = [cid for cid, _, _ in rank(corpus, probe, k=k)]
        eff = len({cl[c] for c in top})
    else:
        eff = 0
    return dict(n_tables=tables,
                n_table_rows_rendered=tables * 14 if tables else 0,
                meta_complete=complete,
                replay_written=replay['written'],
                blank_page_ratio=blank_pages / n_pages,
                ocr_conf=ocr_conf,
                eff_at_10=eff)

rep = make_report(S2, D2, tables=2, metas=METAS,
                  ocr_conf=0.96, blank_pages=1, n_pages=50)
assert rep['replay_written'] == 0
assert abs(rep['blank_page_ratio'] - 0.02) < 1e-9
assert abs(rep['meta_complete']['section_path'] - 2 / 3) < 1e-9
b, w = ingest_gate(rep, BASELINE)
assert any('元数据' in x for x in b)
print('✅ 参考答案 4 通过')
print('   报告生成器里唯一有技巧的一行是 replay——')
print('   它不检查代码，而是把同一批数据再摄取一遍并断言什么都没发生。')
print('   这是幂等性唯一可靠的验证方式（C68-00 的 run ∘ run = run）。')"""),

    md("""## 🧪 真实工程胶囊：接真实解析库

```python
# ══════════════════════════════════════════════════════════════════
# A. 解析：拿三样东西，不是一样（讲解第 1 节）
# ══════════════════════════════════════════════════════════════════
from unstructured.partition.auto import partition

def parse(path):
    els = partition(filename=path, strategy='hi_res',      # hi_res 才有坐标
                    infer_table_structure=True)             # ← 表格必须开
    out = []
    section_stack = []
    for e in els:
        kind = type(e).__name__            # Title / NarrativeText / Table / ListItem
        if kind == 'Title':
            depth = getattr(e.metadata, 'category_depth', 0) or 0
            section_stack = section_stack[:depth] + [e.text]
        if kind == 'Table':
            # 表格走单独路径：行转句 + 保留 markdown 原文
            html = e.metadata.text_as_html
            for sentence in table_rows_to_sentences(html):
                out.append(dict(text=sentence, element_type='table',
                                table_html=html,
                                section_path=' / '.join(section_stack),
                                page=e.metadata.page_number))
            continue
        out.append(dict(text=e.text, element_type=kind,
                        section_path=' / '.join(section_stack),
                        page=e.metadata.page_number,
                        coords=e.metadata.coordinates))    # ← 阅读顺序要用
    return out

# ══════════════════════════════════════════════════════════════════
# B. 阅读顺序：只在需要时接管（讲解第 3 节）
# ══════════════════════════════════════════════════════════════════
#   多数解析库已经做了排序；但双栏 PDF 上要自己验证。
#   便宜的做法：抽 5 页人工看一遍，把结论写进摄取文档。
#   自动化的做法：x 坐标直方图双峰检测 → 命中就用 XY-cut 重排。

# ══════════════════════════════════════════════════════════════════
# C. OCR：记录置信度，不要顺便用 LLM 清洗（讲解第 4 节）
# ══════════════════════════════════════════════════════════════════
import pytesseract
data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
page_conf = np.mean([c for c in data['conf'] if c > 0]) / 100.0
meta['ocr_conf'] = page_conf
if page_conf < OCR_REVIEW_THRESHOLD:
    review_queue.put(path)                # 人工复核，而不是自动改写

# ══════════════════════════════════════════════════════════════════
# D. 摄取：幂等 + tombstone（讲解第 7 节）
# ══════════════════════════════════════════════════════════════════
def ingest(path, col):
    sha = sha256_file(path)
    if tombstoned(path):        return 'rejected'
    if current_sha(path) == sha: return 'skipped'          # 幂等
    v = bump_version(path)
    col.delete(where={'doc_id': path, 'version': {'$lt': v}})   # 先删旧
    chunks = chunk(parse(path))                                  # 再写新
    col.upsert(ids=[f'{path}:{v}:{i}' for i in range(len(chunks))], ...)
    return 'written'

def delete(path, col, reason):
    n = col.count(where={'doc_id': path})
    col.delete(where={'doc_id': path})
    write_tombstone(path, reason)
    assert col.count(where={'doc_id': path}) == 0, '删除必须可验证'
    return n

# ══════════════════════════════════════════════════════════════════
# E. CI（讲解第 8 节）
# ══════════════════════════════════════════════════════════════════
# 1) 对一批固定样本文档跑摄取 → 生成 report
# 2) ingest_gate(report, baseline)：确定性项阻断，统计项报警
# 3) 幂等自检：同一批重放，断言 written == 0
# 4) 基线（ocr_conf 的均值与方差）从最近 30 次摄取滚动计算（C68-04）
```

---

## 小结

| 结论 | 数字 / 判据 | 在哪一节 |
|---|---|---|
| 解析是唯一「下游无法补救」的环节 | 结构、顺序、位置丢了就是丢了 | 讲解 1 |
| 拍平不是必然丢结构；列主序与块边界才是 | 行主序小表可恢复；③④ 不可恢复但相似度 > 0.3 | 第 1 节 |
| 按 y 排序在双栏上产生实体错配 | 错配率从 33% 降到 0 | 第 2 节 |
| OCR 噪声优先毁掉长词 | $1-(1-\\varepsilon)^L$；ε=3% 时 12 字词 31% 被毁 | 第 3 节 |
| 词法检索衰减比语义快一个量级 | ε=3% 时相对跌幅差 3 倍以上 | 第 3 节 |
| 元数据过滤没有「排名靠后」这个中间态 | 写窄一格 → recall 直接 0 | 第 4 节 |
| 近重复占满 top-k，浪费上下文预算 | eff@5 从 2 提升到 4 | 第 5 节 |
| 幂等性只能靠「重放并断言无事发生」验证 | `replay_written == 0` | 第 6/7 节 |

下一模块：**02 · 分块**——把「块该多大」从口味问题变成一个有约束的优化问题。"""),
]
