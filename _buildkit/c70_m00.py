# -*- coding: utf-8 -*-
"""C70 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过 C11（嵌入 / 向量检索 / 重排 / 检索指标 / RAG 评测）——"
                 "本课<strong>不重复</strong>那门课的任何内容；"
                 "会写 Python，理解「哈希」与「集合」"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（一条 60 行的端到端 RAG 流水线：摄取 → 分块 → 索引 → 检索 → 组装 → 回答 / '
                       '在这条流水线上依次注入四个「不在检索算法里」的故障并量出每一个的代价）'),
    ("核心参考", "本课程 C11（检索算法与 RAG 评测）· C33（上下文预算与压缩）· "
                 "C43（大规模数据工程：去重与流式）· C68（评测基础设施）· "
                 "Lewis et al., <em>Retrieval-Augmented Generation</em>（NeurIPS 2020）"),
    ("预计时长", "读 40 分钟 + 跑 30 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why", "这门课讲什么：RAG 的失败大多不在检索算法里", "".join([
        P("C11 已经把检索算法讲透了：嵌入、BM25、混合检索、IVF/HNSW/PQ、"
          "cross-encoder 重排、precision@k / nDCG、faithfulness 与 context recall。"
          "<strong>这门课从一个不同的观察出发：在真实系统里，「答不上来」这件事"
          "绝大多数时候和这些算法没有关系。</strong>"),
        ASCII("""
   一个真实 RAG 系统的完整链路

   ┌──────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
   │ 文档摄取  │──►│  分块  │──►│  索引  │──►│  检索  │──►│  组装  │──►答
   │  与解析   │   │        │   │        │   │        │   │  上下文 │
   └──────────┘   └────────┘   └────────┘   └────────┘   └────────┘
        ▲              ▲            ▲            ▲
        │              │            │            │
      本课 01        本课 02      本课 05      C11 全课
      本课 03（查询侧改写）· 本课 04（迭代检索）

   C11 覆盖的是「检索」这一格里的算法，以及最右边的评测。
   本课覆盖的是它左边的三格和右边的一格——**输入侧与运维侧**。
"""),
        DUAL(
            "为什么这个分工重要？因为<strong>检索算法只能在「已经进了索引的东西」里找</strong>。"
            "如果答案在解析时被丢掉了、在分块时被切断了、在索引里已经过期了，"
            "那么把 HNSW 换成暴力 kNN、把 top-5 改成 top-20、加一个 cross-encoder 重排——"
            "<em>一个都救不回来</em>。"
            "<strong>这类失败的共同特征是：检索指标看起来正常，端到端答案却是错的。</strong>",
            "形式化一点：设问题 $q$ 的答案证据是文档集合里的一个片段 $e$。"
            "端到端可答的必要条件是"
            "$e \\subseteq \\bigcup_{c \\in \\text{retrieved}(q)} c$，"
            "而这个条件可以在四个地方被破坏："
            "$e$ 在解析时丢失（$e \\notin \\text{corpus}$）、"
            "$e$ 被分块切断（$\\nexists c: e \\subseteq c$）、"
            "$e$ 的索引版本已过期、"
            "$q$ 与承载 $e$ 的块之间存在词汇或语义鸿沟。"
            "<em>只有最后一个是检索算法能处理的</em>，"
            "而 C11 的全部工具都作用在最后一个上。",
        ),
        CALLOUT("intuition", "一句话记住本课的定位："
                             "<strong>C11 教你在语料里把对的段落找出来，"
                             "本课教你让「对的段落」一开始就存在、"
                             "并且在一年后还是对的。</strong>"),
    ])),

    # ============================================================== 2
    ("failures", "六个静默失败：它们都不会让检索指标变差", "".join([
        P("下面这六个是本课每个模块各自的靶子。"
          "把它们排在一起是因为它们有一个共同的、危险的性质："
          "<strong>发生时没有任何报错，而且离线检索指标可能完全正常。</strong>"),
        TABLE(["#", "失败", "症状（用户看到的）", "为什么检索指标抓不到", "本课模块"], [
            ["1", "<strong>解析丢结构</strong>",
             "「这张表里 2023 年的数字是多少」答错",
             "表格被拍平成文本后，行列对应关系已经不在语料里了；"
             "检索照样能召回那个块，<em>块里的字也都在</em>",
             "01"],
            ["2", "<strong>阅读顺序错乱</strong>",
             "把 A 的属性说成 B 的",
             "双栏版面按坐标乱序拼接后，句子仍然是「相关」的，"
             "只是实体与属性错配了",
             "01"],
            ["3", "<strong>答案跨块边界</strong>",
             "答案说一半",
             "召回的块<em>确实是最相关的那个</em>——precision@k 满分，"
             "但答案的后半截在下一个块里",
             "02"],
            ["4", "<strong>词汇鸿沟</strong>",
             "「明明文档里写了」却答不出来",
             "用户的问法和文档的写法不共享任何词；"
             "这在<em>用查询本身做的评测</em>里看不出来",
             "03"],
            ["5", "<strong>需要两跳</strong>",
             "答案自信但错",
             "单轮检索的 recall 对这个问题<em>天然是 0</em>，"
             "而 recall 是按「标注的相关文档」算的——标注本身只标了第一跳",
             "04"],
            ["6", "<strong>索引过期 / 删除没生效</strong>",
             "答出了已经删掉的内容",
             "离线评测跑在一个静态快照上，"
             "<em>快照里没有「时间」这一维</em>",
             "05"],
        ]),
        CALLOUT("danger", "第 6 个值得单独强调，因为它同时是一个<strong>合规问题</strong>："
                          "如果用户要求删除一份文档，而它的向量还留在索引里，"
                          "那么这份文档<em>仍然会被检索到并被喂给模型</em>。"
                          "<strong>「从源库删除」和「从索引删除」是两件事，"
                          "而只有后者决定用户还能不能看到它。</strong>"),
        P("本课的每个模块都遵循同一个套路："
          "<strong>先把这类失败做成一个可以复现的实验，"
          "然后给出一个能把它变成机器可判定的检查。</strong>"
          "<em>「注意分块要合理」不是工程，「答案完整落在单块内的比例 ≥ 0.9，"
          "低于就报警」才是。</em>"),
    ])),

    # ============================================================== 3
    ("map", "课程地图：四段流水线 + 一段运维", "".join([
        P("六个模块分成两半：01–04 是<strong>数据与查询怎么进来</strong>，"
          "05 是<strong>它进来之后怎么活下去</strong>。"),
        TABLE(["模块", "主题", "核心主张（一句话）"], [
            ["<strong>01</strong>", "文档摄取与解析",
             "解析的目标不是「拿到文字」，而是<strong>拿到文字 + 它的结构与来源</strong>；"
             "丢掉的结构在下游<em>无法恢复</em>"],
            ["<strong>02</strong>", "分块",
             "分块不是「切成差不多大的段」，而是"
             "<strong>让答案有机会完整地落在一个可检索单元里</strong>；"
             "这是一个可以直接测量的量"],
            ["<strong>03</strong>", "查询侧改写与路由",
             "查询是流水线里<strong>唯一你能在运行时改写的东西</strong>；"
             "而第一个该问的问题是「这个查询到底该不该检索」"],
            ["<strong>04</strong>", "迭代与图检索",
             "多跳问题的单轮 recall 天然是 0；"
             "<strong>迭代必须带停止准则，否则成本没有上界</strong>"],
            ["<strong>05</strong>", "索引运维",
             "索引是<strong>有状态的、会腐烂的</strong>；"
             "「换 embedding 模型」是一次<em>不可混用的全量迁移</em>，不是一次配置修改"],
        ]),
        H3("三条贯穿全课的纪律"),
        OL([
            "<strong>每一个块都要能回答「你从哪来」</strong>——"
            "文档 ID、版本、页码/章节、字符区间。"
            "<em>没有 provenance 的块无法被删除、无法被更新、无法被引用核查。</em>"
            "这条在 01 建立，在 05 被用来做删除与新鲜度。",
            "<strong>摄取必须幂等</strong>——"
            "同一份文档摄取两次，索引里不能出现两份块。"
            "实现只需要一句话：<em>主键 <code>(doc_id, version, chunk_index)</code>，"
            "写入前先查在不在</em>（与 C68 模块 00 的幂等 store 同构）。",
            "<strong>每一层改动都要能被同一套离线集重测</strong>——"
            "换分块参数、加一个查询改写、升级 embedding 模型，"
            "都必须能跑出「之前 / 之后」两个数。"
            "<em>这门课不重复 C11 的指标定义，但会反复用它们做 A/B。</em>",
        ]),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工（读这一节可以省掉很多重复）", "".join([
        P("全库里和 RAG 相关的课有好几门。这一节把边界划清，"
          "<strong>本课不重复其中任何一门的内容</strong>。"),
        TABLE(["课程", "它讲什么", "与本课的关系"], [
            ["<strong>C11</strong> · 检索增强与长上下文评测",
             "嵌入与相似度、BM25、混合检索、IVF/HNSW/PQ、bi- vs cross-encoder 重排、"
             "MMR、RRF、precision@k / MRR / MAP / nDCG、faithfulness / RAGAS、"
             "NIAH 与 lost-in-the-middle",
             "<strong>本课的上游与下游</strong>。C11 讲「在索引里怎么找」，"
             "本课讲「索引里装的是什么、查询长什么样、索引怎么维护」。"
             "<em>本课全程复用 C11 的指标，但一个都不重新定义</em>"],
            ["<strong>C33</strong> · 上下文与记忆工程",
             "token 预算与截断、compaction、长期记忆、检索入门、prompt 缓存",
             "<strong>本课到「组装上下文」为止，之后交给 C33</strong>。"
             "「召回的块塞不进窗口怎么办」「稳定前缀怎么设计」全部属于 C33；"
             "<em>本课不讲预算分配</em>"],
            ["<strong>C43</strong> · 大规模数据工程",
             "去重（MinHash / SimHash）、流式处理、吞吐、去污染",
             "<strong>本课模块 01 的去重直接复用 C43 的算法</strong>，"
             "只讨论它在 RAG 语境下的一个特有后果：<em>近重复会占满 top-k</em>"],
            ["<strong>C68</strong> · Eval 基础设施（同批）",
             "spec / runner / store / report、版本化、CI 门禁、线上监控",
             "<strong>本课每一层的 A/B 都按 C68 的规矩做</strong>："
             "分块参数进 spec、参数变了指纹就变、门禁阈值从方差推"],
            ["<strong>C71</strong> · 提示与上下文的程序化优化（同批新课）",
             "prompt program 与签名、示例选择与顺序、自动提示优化、受限解码、提示运维",
             "<strong>本课管「数据与查询怎么进来、索引怎么活下去」，"
             "C71 管「prompt 本身的结构、优化与运维」</strong>。"
             "<em>两者的交界在「组装上下文」这一步：本课把召回的块交出去，"
             "C71 决定它们与指令、示例、格式一起怎么组织成一次调用</em>；"
             "而两者都不碰 C11（检索算法）与 C33（上下文预算）"],
            ["<strong>C46</strong> · 图机器学习",
             "message passing、GCN/GAT、图 transformer",
             "本课模块 04 的图检索<strong>只用图的结构（邻域扩展），不训练任何图神经网络</strong>；"
             "需要 GNN 的部分在 C46"],
            ["<strong>C12 / C45</strong> · 责任与隐私",
             "隐私度量、DP、遗忘",
             "本课模块 05 的「删除必须在索引里物理生效」是这两门课的<em>工程落地面</em>，"
             "但本课不讲 DP 与遗忘的算法"],
        ]),
        CALLOUT("warn", "如果你只想解决一个具体问题，可以直接跳："
                        "<strong>「文档里明明有但答不出来」→ 01 与 02；"
                        "「用户换个说法就不行了」→ 03；"
                        "「需要综合两处信息就错」→ 04；"
                        "「昨天改的文档今天还是旧答案」→ 05。</strong>"),
    ])),

    # ============================================================== 5
    ("method", "方法论：为什么用玩具嵌入而不接真实模型", "".join([
        P("这门课的 notebook 全部是<strong>纯 numpy / 标准库、CPU、断网、无需 API key</strong>。"
          "嵌入是确定性的玩具向量，「生成」是规则函数。这是一个刻意的选择，理由有三条。"),
        OL([
            "<strong>本课要测的量都不需要真实模型</strong>——"
            "「答案完整落在单块内的比例」「近重复占满 top-k 的程度」"
            "「索引滞后导致的过期答案率」「新旧 embedding 混用后的相似度失真」，"
            "<em>这些全都是流水线的结构性质，与用哪个嵌入模型无关</em>。",
            "<strong>只有在知道真值的条件下，才能验证一个改动是把结果推近了还是推远了</strong>。"
            "真实模型会把「分块改好了」和「模型今天心情好」混在一起；"
            "玩具替身让每个实验只有一个变量。"
            "<em>这与 C66/C67/C68 的方法论是同一条。</em>",
            "<strong>玩具替身让「失败」可以被精确注入</strong>——"
            "OCR 错误率设成 3%、索引滞后设成 6 小时、答案跨块设成必然发生。"
            "真实系统里这些故障是偶发的，<em>而偶发的故障没法用来教学</em>。",
        ]),
        P("每个模块末尾都有 <strong>🧪 真实工程胶囊</strong>："
          "可以原样复制到生产的落地代码骨架"
          "（unstructured / pypdf 的解析入口、"
          "父子块的存储布局、查询改写的 prompt 与缓存、"
          "增量索引的双写与原子切换、检索层的监控指标）。"
          "<strong>但课程本身不依赖它们。</strong>"),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：机制 → 可测量的量 → 怎么变成检查项",
            "<strong>notebook</strong>：5–7 个 worked 小节，每节都以一个 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 自动判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接真实解析库 / 向量库 / 生产索引的代码",
        ]),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        P("零安装门槛。"),
        CODE("""# 本地
pip install -r requirements.txt      # 只有 numpy 与 jupyterlab
jupyter lab

# 或者点每个 notebook 顶部的 Colab 徽章，CPU 运行时即可

# 顺序：先读 NN_讲解.html，再跑同目录的 NN_*.ipynb""", "bash"),
        P("<strong>先跑 <code>00_environment_check.ipynb</code></strong>——"
          "它用 60 行搭出一条完整的 RAG 流水线，"
          "然后在这条流水线上依次注入本课四个模块各自的靶子故障，"
          "并量出每一个的代价。<em>这个 notebook 是全课的地图。</em>"),
        CALLOUT("intuition", "如果你读完 00 只记住一件事，希望是这个："
                             "<strong>RAG 的调试顺序应该是从左往右的——"
                             "先确认答案在语料里、再确认它没被切断、再确认查询能碰到它，"
                             "最后才去调检索算法。</strong>"
                             "<em>反过来做（先换 embedding 模型、先加重排）是最常见的浪费。</em>"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与一条 60 行的 RAG 流水线

这个 notebook 做两件事：

1. **搭一条最小但完整的 RAG 流水线** —— 摄取 → 分块 → 索引 → 检索 → 组装 → 回答，
   全部用 numpy 与标准库，确定性、可复现。
2. **在这条流水线上依次注入本课四个模块的靶子故障**，并量出每一个的代价：
   解析丢结构（01）· 答案跨块（02）· 词汇鸿沟（03）· 索引过期（05）。

> 心智模型：**检索算法只能在「已经进了索引的东西」里找。
> 本课讲的是它左边和右边的那些格子。**"""),

    md("""## 0 · 环境"""),

    code("""import os, re, json, math, hashlib, random
from collections import Counter, defaultdict

import numpy as np

print('numpy', np.__version__)
print('本课全程 CPU / 断网 / 无需 API key')

RNG = np.random.default_rng(0)"""),

    md("""## 1 · 玩具嵌入：确定性、无需模型

我们需要一个「语义向量」，但不想训练也不想下载。做法：**把词哈希到固定维度的 one-hot 上再叠加**
（这就是 hashing trick），然后 L2 归一化。

这个嵌入有真实嵌入的两个关键性质：**共享词多则相似度高**、**长度被归一化掉**。
它没有的性质是同义词泛化——所以模块 03 讲词汇鸿沟时，它是一个**诚实的坏例子**。"""),

    code("""DIM = 4096

def tokenize(text):
    \"\"\"英文按词，中文同时取单字与二元组。
    二元组是关键——只用单字的话，「的」这类高频字会让任意两句话都显得相关。\"\"\"
    text = text.lower()
    toks = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\\u4e00-\\u9fff]+', text):
        toks += list(run)
        toks += [run[i:i + 2] for i in range(len(run) - 1)]
    return toks

def embed(text, dim=DIM):
    v = np.zeros(dim, dtype=np.float64)
    for tok in tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

def cos(a, b):
    return float(np.dot(a, b))

a = embed('向量检索 的 召回率')
b = embed('召回率 与 向量检索')
c = embed('分布式 训练 的 通信 开销')
print(f'同词不同序: {cos(a, b):.3f}')
print(f'完全不同题: {cos(a, c):.3f}')
assert cos(a, b) > 0.9 and cos(a, c) < 0.2, '玩具嵌入的基本性质'
print(f'\\n✅ 确定性玩具嵌入可用（{DIM} 维，共享词 → 高相似；无共享词 → 近 0）')
print('   它没有的能力是同义词泛化——模块 03 讲词汇鸿沟时它是一个诚实的坏例子。')"""),

    md("""## 2 · 一条 60 行的 RAG 流水线

五个函数，每个都短到可以一眼看完。注意 `Chunk` 里带的 **provenance 字段**——
`doc_id / version / start / end`。本课模块 05 的删除与更新全靠它。"""),

    code("""def ingest(raw_docs):
    \"\"\"摄取：给每份文档一个 ID、一个版本、一个内容哈希。\"\"\"
    docs = []
    for doc_id, text in raw_docs:
        sha = hashlib.sha256(text.encode()).hexdigest()[:12]
        docs.append(dict(doc_id=doc_id, version=1, text=text, content_sha=sha))
    return docs

def chunk(docs, size=120, overlap=0):
    \"\"\"分块：固定字符窗口。size/overlap 是模块 02 的主角。\"\"\"
    out = []
    for d in docs:
        t, i, idx = d['text'], 0, 0
        step = max(1, size - overlap)
        while i < len(t):
            piece = t[i:i + size]
            out.append(dict(doc_id=d['doc_id'], version=d['version'],
                            chunk_index=idx, start=i, end=i + len(piece), text=piece))
            i += step; idx += 1
    return out

def build_index(chunks):
    \"\"\"索引：把每个块的向量堆成矩阵。真实系统里这里是 HNSW（C11 模块 02）。\"\"\"
    mat = np.stack([embed(c['text']) for c in chunks]) if chunks else np.zeros((0, DIM))
    return dict(chunks=chunks, mat=mat)

def retrieve(index, query, k=3):
    \"\"\"检索：暴力 kNN。C11 讲怎么把它变快，本课不碰。\"\"\"
    if len(index['chunks']) == 0:
        return []
    scores = index['mat'] @ embed(query)
    order = np.argsort(-scores)[:k]
    return [(index['chunks'][i], float(scores[i])) for i in order]

def answer(query, hits, facts):
    \"\"\"「生成」：规则替身。只有当答案字符串完整出现在某个召回块里时才答对。
    这条规则是刻意的——它把「答案被切断」变成一个可观测的失败。\"\"\"
    gold = facts[query]
    for ch, _ in hits:
        if gold in ch['text']:
            return gold
    return None

print('✅ 五个函数就位：ingest / chunk / build_index / retrieve / answer')"""),

    md("""## 3 · 跑通一次：健康基线

三份短文档，三个问题。这是后面所有对比的基线。"""),

    code("""RAW = [
    ('doc-hr',     '公司的年假政策如下。正式员工每年享有 15 天带薪年假。'
                   '试用期员工每年享有 5 天带薪年假。年假需提前三个工作日申请。'),
    ('doc-fin',    '报销流程说明。餐饮报销的单次上限是 200 元。'
                   '差旅报销的单次上限是 3000 元。所有报销需在费用发生后 30 天内提交。'),
    ('doc-it',     '设备管理规定。笔记本电脑的更换周期是 36 个月。'
                   '显示器的更换周期是 48 个月。设备损坏需在两个工作日内报修。'),
    ('doc-sec',    '信息安全条例。密码长度不得少于 12 位。'
                   '外发文件必须经过审批。离职时需交回所有权限凭证。'),
    ('doc-train',  '培训制度。新员工入职培训为期 5 天。'
                   '每位员工每年有 2000 元培训预算。外部课程需部门负责人批准。'),
    ('doc-office', '办公场地管理。工位调整需提前一周申请。'
                   '会议室最长可连续预订 4 小时。夜间进入需登记。'),
    ('doc-legal',  '合同管理办法。对外合同需法务复核。'
                   '单笔金额超过 50 万元的合同需总经理签批。合同归档保存 10 年。'),
    ('doc-perf',   '绩效考核办法。考核周期为每半年一次。'
                   '考核结果分为五档。申诉需在结果公布后 5 个工作日内提出。'),
]

# 语料有 8 份文档而不是 3 份，是为了让 top-k=3 真的有选择性：
# 只有 3 份文档时 top-3 会把整个语料都召回，检索层就没有被测试到。

FACTS = {
    '正式员工每年享有多少天带薪年假':      '15 天带薪年假',
    '餐饮报销的单次上限是多少':            '200 元',
    '笔记本电脑的更换周期是多久':          '36 个月',
}

def run_pipeline(raw=RAW, size=120, overlap=0, k=3, queries=None, facts=FACTS):
    docs = ingest(raw)
    chunks = chunk(docs, size=size, overlap=overlap)
    index = build_index(chunks)
    qs = queries if queries is not None else list(facts)
    got = 0
    for q in qs:
        hits = retrieve(index, q, k=k)
        if answer(q, hits, facts) is not None:
            got += 1
    return got / len(qs), len(chunks)

base_acc, n_chunks = run_pipeline()
print(f'基线: 端到端正确率 {base_acc:.0%}  ({n_chunks} 个块)')
assert base_acc == 1.0, '健康流水线应该全对'
print('\\n✅ 基线全对。下面四节各注入一个故障，看正确率怎么掉。')"""),

    md("""## 4 · 故障一（模块 01）：解析丢结构

一份表格文档，两种解析方式：
- **保结构**：每行变成一句「行名的列名是值」——行列对应关系被保留在文字里。
- **拍平**：按阅读顺序把单元格连起来——所有的字都还在，**对应关系没了**。

关键点：**拍平之后检索照样召回那个块，块里每个字都在，但答案不可从中恢复。**"""),

    code("""TABLE_ROWS = [('北京', '2023', '1240'), ('北京', '2024', '1310'),
              ('上海', '2023', '1580'), ('上海', '2024', '1620')]

def render_structured(rows):
    return '各地区营收表。' + ''.join(
        f'{city} 在 {year} 年的营收是 {val} 万元。' for city, year, val in rows)

def render_flattened(rows):
    cells = ['地区', '年份', '营收']
    for r in rows: cells += list(r)
    return '各地区营收表。' + ' '.join(cells)

TABLE_FACTS = {'上海在2023年的营收是多少': '上海 在 2023 年的营收是 1580 万元'}

for name, render in [('保结构', render_structured), ('拍平', render_flattened)]:
    text = render(TABLE_ROWS)
    acc, _ = run_pipeline(raw=[('doc-t', text)], size=400,
                         queries=list(TABLE_FACTS), facts=TABLE_FACTS)
    hits = retrieve(build_index(chunk(ingest([('doc-t', text)]), size=400)),
                    list(TABLE_FACTS)[0], k=1)
    print(f'{name:>4}: 端到端 {acc:.0%} | 检索到的块相似度 {hits[0][1]:.3f} '
          f'| 「1580」在块里吗 {"1580" in hits[0][0]["text"]}')

print('\\n✅ 拍平后：检索相似度依然很高、数字也确实在块里，但答案无法恢复。')
print('   这就是「检索指标正常，端到端错」的第一种形态——模块 01 的靶子。')"""),

    md("""## 5 · 故障二（模块 02）：答案跨块边界

把块调小，让答案字符串正好横跨两个块的边界。
**precision@k 满分**——召回的确实是最相关的块；但答案说了一半。

然后加 overlap，看它怎么被修回来。这是模块 02 的核心可测量。"""),

    code("""def answer_intact_rate(raw, facts, size, overlap):
    \"\"\"答案完整落在「某一个块」里的比例——模块 02 的核心指标。\"\"\"
    chunks = chunk(ingest(raw), size=size, overlap=overlap)
    ok = 0
    for gold in facts.values():
        if any(gold in c['text'] for c in chunks):
            ok += 1
    return ok / len(facts)

print(f"{'块大小':>8}{'overlap':>9}{'答案完整率':>12}{'端到端':>9}{'块数':>7}")
for size, ov in [(120, 0), (60, 0), (40, 0), (24, 0), (24, 12), (24, 20)]:
    intact = answer_intact_rate(RAW, FACTS, size, ov)
    acc, nc = run_pipeline(size=size, overlap=ov)
    print(f'{size:>8}{ov:>9}{intact:>12.0%}{acc:>9.0%}{nc:>7}')

i_small = answer_intact_rate(RAW, FACTS, 24, 0)
i_ovlap = answer_intact_rate(RAW, FACTS, 24, 20)
assert i_small < 1.0, '块太小时答案必然被切断'
assert i_ovlap > i_small, 'overlap 应当把完整率救回来'
print(f'\\n✅ 块=24 无重叠时答案完整率只有 {i_small:.0%}，加到 overlap=20 后 {i_ovlap:.0%}。')
print('   代价是块数暴涨——这个权衡是模块 02 的主线。')"""),

    md("""## 6 · 故障三（模块 03）：词汇鸿沟

用户的问法和文档的写法不共享任何词。玩具嵌入没有同义词泛化能力，
所以它在这里是一个**诚实的坏例子**：相似度直接掉到 0，召回不到。

然后用一个「查询改写」把用户词映射到文档词——模块 03 的主线。"""),

    code("""SYNONYM = {'吃饭': '餐饮', '最多能花': '单次上限是'}

def rewrite(q, table=SYNONYM):
    out = q
    for user_word, doc_word in table.items():
        out = out.replace(user_word, doc_word)
    return out

index = build_index(chunk(ingest(RAW), size=120))
GAP_Q = '吃饭最多能花多少钱'
GOLD = '200 元'

for label, q in [('原始查询', GAP_Q), ('改写后', rewrite(GAP_Q))]:
    hits = retrieve(index, q, k=3)
    hit_ok = any(GOLD in c['text'] for c, _ in hits)
    print(f'{label:>8}: 「{q}」 → top1={hits[0][0]["doc_id"]:<10s} '
          f'相似度 {hits[0][1]:.3f} | 召回到答案 {hit_ok}')

h_raw = retrieve(index, GAP_Q, k=3)
h_rew = retrieve(index, rewrite(GAP_Q), k=3)
assert not any(GOLD in c['text'] for c, _ in h_raw), '词汇鸿沟下召回不到'
assert any(GOLD in c['text'] for c, _ in h_rew), '改写后应当召回到'
print('\\n✅ 同一个索引、同一个检索算法，只改了查询——从召回不到变成召回到。')
print('   注意原始查询的 top1 是一份完全无关的文档，相似度只有 0.03：')
print('   词汇鸿沟下检索不是「排序差一点」，而是根本没进候选。')
print('   查询是流水线里唯一能在运行时改写的东西，这是模块 03 的立足点。')"""),

    md("""## 7 · 故障四（模块 05）：索引过期与删除没生效

两个独立的问题，都发生在时间维度上：
1. 文档更新了，索引还是旧版本 → **过期答案**。
2. 文档从源库删了，索引里的向量还在 → **答出已删除内容**（这同时是合规问题）。"""),

    code("""# --- 过期 ---
docs = ingest(RAW)
index = build_index(chunk(docs, size=120))
UPDATED = RAW[0][1].replace('15 天带薪年假', '20 天带薪年假')
q = '正式员工每年享有多少天带薪年假'

stale = retrieve(index, q, k=3)
print('源库已更新为「20 天」，但索引未重建：')
print('  索引里仍能召回「15 天带薪年假」:', any('15 天带薪年假' in c['text'] for c, _ in stale))

reindexed = build_index(chunk(ingest([('doc-hr', UPDATED)] + list(RAW[1:])), size=120))
fresh = retrieve(reindexed, q, k=3)
print('  重建后召回「20 天带薪年假」:', any('20 天带薪年假' in c['text'] for c, _ in fresh))

# --- 删除 ---
def delete_from_index(index, doc_id):
    keep = [i for i, c in enumerate(index['chunks']) if c['doc_id'] != doc_id]
    return dict(chunks=[index['chunks'][i] for i in keep], mat=index['mat'][keep])

src_deleted = [r for r in RAW if r[0] != 'doc-fin']    # 源库删了 doc-fin
q2 = '餐饮报销的单次上限是多少'
print('\\n源库已删除 doc-fin：')
print('  索引未同步 → 仍能召回:',
      any(c['doc_id'] == 'doc-fin' for c, _ in retrieve(index, q2, k=3)))
after = delete_from_index(index, 'doc-fin')
print('  索引同步删除后 → 还能召回:',
      any(c['doc_id'] == 'doc-fin' for c, _ in retrieve(after, q2, k=3)))

assert any('15 天带薪年假' in c['text'] for c, _ in stale), '未重建时应当仍是旧值'
assert not any(c['doc_id'] == 'doc-fin' for c, _ in retrieve(after, q2, k=3)), '删除必须在索引里生效'
print('\\n✅ 这两个失败在任何静态离线评测里都不可见——快照里没有时间这一维。')
print('   注意删除是靠 provenance 字段 doc_id 做到的：没有它就删不掉。')"""),

    md("""## 8 · 四个故障的代价汇总

把四个故障放在一张表里。**注意最后一列**：只有一个故障能被「检索层的指标」看见。"""),

    code("""SUMMARY = [
    ('01 解析丢结构',   '表格行列对应丢失',   '块被召回、字都在、答案不可恢复', False),
    ('02 答案跨块',     '答案横跨块边界',     'precision@k 满分但答案不完整',   False),
    ('03 词汇鸿沟',     '查询与文档无共享词', '相似度掉到 0（这个能看见）',     True),
    ('05 索引过期/删除', '索引落后于源库',     '离线快照里没有时间维',           False),
]

print(f"{'故障':<16}{'机制':<22}{'症状':<34}{'检索指标能看见':>14}")
for name, mech, symp, visible in SUMMARY:
    print(f'{name:<16}{mech:<22}{symp:<34}{"是" if visible else "否":>14}')

visible_count = sum(1 for *_, v in SUMMARY if v)
assert visible_count == 1, '四个故障里只有一个是检索层能看见的'
print(f'\\n✅ 4 个故障里只有 {visible_count} 个能被检索指标发现。')
print('   这就是这门课存在的理由：另外三个需要在流水线的其它位置建检查。')"""),

    md("""## ✏️ 练习 1：端到端归因器

给定一个答不上来的查询，判断**是哪一层的问题**。这是本课最有用的一个工具：
它把「RAG 效果不好」变成一个有指向的诊断。

判定顺序（这个顺序本身就是结论）：
1. 答案字符串**在语料里都找不到** → `'parse'`（解析丢了）
2. 答案在语料里，但**没有任何一个块完整包含它** → `'chunk'`（被切断）
3. 答案完整在某个块里，但**那个块没被召回** → `'query'`（查询碰不到）
4. 块被召回了但还是答错 → `'generate'`

补全 `diagnose`。"""),

    code("""def diagnose(query, gold, raw, size, overlap, k=3):
    \"\"\"返回 'parse' / 'chunk' / 'query' / 'generate' / 'ok' 之一。\"\"\"
    # TODO：按上面的四步顺序判断
    raise NotImplementedError
"""),

    code("""# —— 自测 ——
# a) 语料里根本没有答案 → parse
assert diagnose('x', '不存在的答案', RAW, 120, 0) == 'parse'
# b) 答案在语料里但块太小被切断 → chunk
assert diagnose('正式员工每年享有多少天带薪年假', '15 天带薪年假', RAW, 12, 0) == 'chunk'
# c) 答案完整在块里，但查询有词汇鸿沟 → query
assert diagnose('吃饭最多能花多少钱', '200 元', RAW, 120, 0) == 'query'
# d) 一切正常 → ok
assert diagnose('正式员工每年享有多少天带薪年假', '15 天带薪年假', RAW, 120, 0) == 'ok'
print('✅ 练习 1 通过：归因器能把失败指到具体的一层')"""),

    md("""## 📖 参考答案 1"""),

    code("""def diagnose(query, gold, raw, size, overlap, k=3):
    docs = ingest(raw)
    if not any(gold in d['text'] for d in docs):
        return 'parse'
    chunks = chunk(docs, size=size, overlap=overlap)
    holders = [c for c in chunks if gold in c['text']]
    if not holders:
        return 'chunk'
    index = build_index(chunks)
    hits = retrieve(index, query, k=k)
    if not any(gold in c['text'] for c, _ in hits):
        return 'query'
    return 'ok' if answer(query, hits, {query: gold}) is not None else 'generate'

assert diagnose('x', '不存在的答案', RAW, 120, 0) == 'parse'
assert diagnose('正式员工每年享有多少天带薪年假', '15 天带薪年假', RAW, 12, 0) == 'chunk'
assert diagnose('吃饭最多能花多少钱', '200 元', RAW, 120, 0) == 'query'
assert diagnose('正式员工每年享有多少天带薪年假', '15 天带薪年假', RAW, 120, 0) == 'ok'
print('✅ 参考答案 1 通过')
print('   诊断顺序 parse → chunk → query → generate 就是本课模块的顺序，')
print('   也是真实调试时该走的顺序：从左往右，别一上来就换 embedding 模型。')"""),

    md("""## ✏️ 练习 2：幂等摄取

同一份文档摄取两次，索引里不能出现两份块。
实现一个带主键 `(doc_id, version, chunk_index)` 的 upsert。

要求：
- 重复摄取同一版本 → 块数不变
- 摄取更高版本 → 旧版本的块被**替换**（不是叠加）"""),

    code("""def upsert_chunks(store, new_chunks):
    \"\"\"store: dict，键是 (doc_id, version, chunk_index)。
    同 doc_id 的更高版本进来时，删掉该 doc 的所有旧版本块。
    返回 (store, 本次实际写入数, 本次删除数)。\"\"\"
    # TODO
    raise NotImplementedError
"""),

    code("""# —— 自测 ——
store = {}
c1 = chunk(ingest([('d1', 'A' * 300)]), size=100)
store, w1, d1_ = upsert_chunks(store, c1)
assert (w1, d1_, len(store)) == (3, 0, 3), (w1, d1_, len(store))

store, w2, d2_ = upsert_chunks(store, c1)          # 同版本重复摄取
assert (w2, d2_, len(store)) == (0, 0, 3), '幂等：重复摄取不应写入'

c2 = chunk([dict(doc_id='d1', version=2, text='B' * 150)], size=100)
store, w3, d3_ = upsert_chunks(store, c2)          # 新版本
assert d3_ == 3 and len(store) == 2, '新版本必须替换旧版本，而不是叠加'
assert all(k[1] == 2 for k in store), '旧版本块必须全部消失'
print('✅ 练习 2 通过：摄取幂等，且版本升级是替换而非叠加')"""),

    md("""## 📖 参考答案 2"""),

    code("""def upsert_chunks(store, new_chunks):
    written = deleted = 0
    for c in new_chunks:
        key = (c['doc_id'], c['version'], c['chunk_index'])
        old_keys = [k for k in store
                    if k[0] == c['doc_id'] and k[1] < c['version']]
        for k in old_keys:
            del store[k]; deleted += 1
        if key not in store:
            store[key] = c; written += 1
    return store, written, deleted

store = {}
c1 = chunk(ingest([('d1', 'A' * 300)]), size=100)
store, w1, d1_ = upsert_chunks(store, c1)
assert (w1, d1_, len(store)) == (3, 0, 3)
store, w2, d2_ = upsert_chunks(store, c1)
assert (w2, d2_, len(store)) == (0, 0, 3)
c2 = chunk([dict(doc_id='d1', version=2, text='B' * 150)], size=100)
store, w3, d3_ = upsert_chunks(store, c2)
assert d3_ == 3 and len(store) == 2
assert all(k[1] == 2 for k in store)
print('✅ 参考答案 2 通过')
print('   注意「先删旧版本再写新块」这个顺序：反过来会在中途留下混版本的索引。')
print('   模块 05 会把这一点变成「双写 + 原子切换」。')"""),

    md("""## ✏️ 练习 3：答案完整率的最优块大小

给定文档与答案集，扫一遍 `(size, overlap)` 网格，返回**在满足答案完整率 ≥ 阈值的前提下、
块数最少**的那个配置。

这是模块 02 的核心工具：它把「块该多大」从口味变成一个有约束的优化问题。"""),

    code("""def best_chunk_config(raw, facts, sizes, overlaps, min_intact=1.0):
    \"\"\"返回 (size, overlap, intact, n_chunks)；
    在 intact >= min_intact 的配置里选块数最少的；平局取 size 最大的。
    若没有配置达标，返回 intact 最高的那个。\"\"\"
    # TODO
    raise NotImplementedError
"""),

    code("""# —— 自测 ——
cfg = best_chunk_config(RAW, FACTS, [24, 40, 80, 120], [0, 8, 16], min_intact=1.0)
size, ov, intact, nc = cfg
assert intact == 1.0, '应当找到达标配置'
assert answer_intact_rate(RAW, FACTS, size, ov) == 1.0
# 达标里块数最少 → 不应该选最小的块
assert size >= 80, f'块数最少应该倾向大块，得到 size={size}'
# 无法达标时退化为「尽力而为」
cfg2 = best_chunk_config(RAW, FACTS, [8], [0], min_intact=1.0)
assert cfg2[2] < 1.0, '不可能达标时返回最好的那个'
print(f'✅ 练习 3 通过：最优配置 size={size} overlap={ov} → {nc} 个块')"""),

    md("""## 📖 参考答案 3"""),

    code("""def best_chunk_config(raw, facts, sizes, overlaps, min_intact=1.0):
    rows = []
    for s in sizes:
        for o in overlaps:
            if o >= s:
                continue
            intact = answer_intact_rate(raw, facts, s, o)
            nc = len(chunk(ingest(raw), size=s, overlap=o))
            rows.append((s, o, intact, nc))
    ok = [r for r in rows if r[2] >= min_intact]
    if ok:
        return sorted(ok, key=lambda r: (r[3], -r[0]))[0]
    return sorted(rows, key=lambda r: (-r[2], r[3]))[0]

cfg = best_chunk_config(RAW, FACTS, [24, 40, 80, 120], [0, 8, 16], min_intact=1.0)
size, ov, intact, nc = cfg
assert intact == 1.0 and size >= 80
assert best_chunk_config(RAW, FACTS, [8], [0], min_intact=1.0)[2] < 1.0
print(f'✅ 参考答案 3 通过：size={size} overlap={ov} intact={intact:.0%} 块数={nc}')
print('   这个函数的形状很重要：**先满足约束，再最小化成本**。')
print('   反过来（先定块数再看效果）就是大多数系统里分块参数的来历。')"""),

    md("""## ✏️ 练习 4：流水线指纹

按 C68 的规矩：**改了会让结果不可比较的东西，全部进指纹**。
本课的流水线里这些是：分块参数、嵌入维度、top-k、查询改写表、语料的内容哈希集合。

实现 `pipeline_fingerprint`，要求改任何一项指纹都变，而改与结果无关的东西（比如日志级别）不变。"""),

    code("""def pipeline_fingerprint(config):
    \"\"\"config 是一个 dict。只把影响结果的键纳入指纹。
    返回 12 位十六进制字符串。\"\"\"
    # TODO：定义 RELEVANT 键集合，规范化后哈希
    raise NotImplementedError"""),

    code("""# —— 自测 ——
BASE = dict(size=120, overlap=0, dim=256, k=3,
            rewrite_table={'休假': '年假'},
            corpus_shas=['ab12', 'cd34'], log_level='INFO')

fp0 = pipeline_fingerprint(BASE)
for key, val in [('size', 100), ('overlap', 8), ('dim', 512), ('k', 5),
                 ('rewrite_table', {}), ('corpus_shas', ['ab12'])]:
    c = dict(BASE); c[key] = val
    assert pipeline_fingerprint(c) != fp0, f'改 {key} 必须让指纹变'

c = dict(BASE); c['log_level'] = 'DEBUG'
assert pipeline_fingerprint(c) == fp0, '与结果无关的键不该进指纹'
c = dict(BASE); c['corpus_shas'] = ['cd34', 'ab12']
assert pipeline_fingerprint(c) == fp0, '语料哈希的顺序不该影响指纹'
print(f'✅ 练习 4 通过：指纹 {fp0}')"""),

    md("""## 📖 参考答案 4"""),

    code("""RELEVANT = ('size', 'overlap', 'dim', 'k', 'rewrite_table', 'corpus_shas')

def pipeline_fingerprint(config):
    norm = {}
    for key in RELEVANT:
        v = config.get(key)
        if isinstance(v, (list, tuple, set)):
            v = sorted(v)
        elif isinstance(v, dict):
            v = sorted(v.items())
        norm[key] = v
    blob = json.dumps(norm, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]

fp0 = pipeline_fingerprint(BASE)
for key, val in [('size', 100), ('overlap', 8), ('dim', 512), ('k', 5),
                 ('rewrite_table', {}), ('corpus_shas', ['ab12'])]:
    c = dict(BASE); c[key] = val
    assert pipeline_fingerprint(c) != fp0
c = dict(BASE); c['log_level'] = 'DEBUG'
assert pipeline_fingerprint(c) == fp0
c = dict(BASE); c['corpus_shas'] = ['cd34', 'ab12']
assert pipeline_fingerprint(c) == fp0
print(f'✅ 参考答案 4 通过：{fp0}')
print('   两个细节：① 集合要排序（否则顺序变指纹就变，产生假的不可比）；')
print('   ② 语料哈希进指纹，因为语料变了分数就不可比——这与 C68-01 的交集重算是同一条。')"""),

    md("""## 🧪 真实工程胶囊：把这条玩具流水线换成真实组件

结构一行不用改，只把四个函数的实现换掉。**注意 provenance 字段必须原样保留**——
它是模块 05 全部运维能力的前提。

```python
# ---- ingest：真实解析（模块 01 会展开）
from unstructured.partition.auto import partition
def ingest(paths):
    docs = []
    for p in paths:
        els = partition(filename=p)                    # 保留 element 类型与坐标
        docs.append(dict(doc_id=p, version=file_mtime_version(p),
                         elements=els, content_sha=sha256_file(p)))
    return docs

# ---- chunk：结构感知 + 父子块（模块 02）
#   小块进索引，父块进上下文；两者共享 parent_id

# ---- build_index：真实向量库
import chromadb
col = chromadb.Client().get_or_create_collection('kb')
col.upsert(ids=[chunk_key(c) for c in chunks],           # 主键 = 幂等性
           embeddings=model.encode([c['text'] for c in chunks]).tolist(),
           metadatas=[{k: c[k] for k in
                       ('doc_id', 'version', 'chunk_index', 'start', 'end')}
                      for c in chunks])

# ---- retrieve：带元数据过滤（模块 03 / 05：多租户与时间窗）
col.query(query_embeddings=[model.encode(q).tolist()], n_results=k,
          where={'tenant': tenant_id, 'version': {'$gte': min_version}})
```

要点：
1. `chunk_key(c)` 用 `(doc_id, version, chunk_index)`，**upsert 而不是 add**——这是幂等性。
2. 元数据里必须有 `doc_id` 与 `version`，否则**删不掉也更新不了**。
3. 分块参数、嵌入模型名与版本、top-k 全部进 spec 并进指纹（C68-01）。
4. 真实解析库会给你 element 类型（Title / Table / NarrativeText）与坐标——
   **不要在这一步把它们扔掉**，模块 01 与 02 全靠它们。

---

## 小结

| 结论 | 为什么 | 在哪一层 |
|---|---|---|
| 检索算法只能在已进索引的东西里找 | 解析丢的、切断的、过期的都救不回来 | 全课的出发点 |
| 四个故障里只有一个能被检索指标看见 | 另外三个不改变「块与查询的相关性」 | 00 第 8 节 |
| 调试顺序应当是 parse → chunk → query → generate | 从左往右，先确认答案存在 | 练习 1 |
| 摄取必须幂等，版本升级是替换 | 否则索引里会混版本 | 练习 2 |
| 块大小是有约束的优化问题 | 先满足答案完整率，再最小化块数 | 练习 3 |
| 语料哈希与分块参数必须进指纹 | 它们变了分数就不可比 | 练习 4 |

下一模块：**01 · 文档摄取与解析**——为什么「拿到文字」不等于「拿到内容」，
以及结构、顺序、来源这三样东西丢了以后为什么无法恢复。"""),
]
