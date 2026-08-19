# -*- coding: utf-8 -*-
"""C62 模块 02 · 哈希、排序与二分。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（六步答题协议）、模块 01（数组与字符串 / 双指针）；不需要 C61 的检测背景"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_hash_sort_search.ipynb（纯 Python + numpy，三套二分与 bisect 对拍、Top-K 三解法计时）'),
    ("核心参考", "CLRS 第 8/9/11 章 · Bentley & McIlroy 快排工程 · Peters 的 Timsort listsort.txt · Kraska et al. 学习型索引"),
    ("预计时长", "读 80 分钟 + 跑 90 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("hash", "哈希表：均摊 O(1) 的代价，与 Python 的三个坑", "".join([
        P("哈希表是面试里出现频率最高的数据结构，也是最容易被<strong>误报复杂度</strong>的一个。"
          "「用个 dict 就是 O(1)」这句话在 90% 的面试题里是对的，但你必须知道它在什么条件下成立——"
          "<strong>面试官问「dict 的查找真的是 O(1) 吗」时，他要的就是那 10%</strong>。"),
        P("哈希表 = 一个定长数组 + 一个把 key 映射到下标的哈希函数 + 一套冲突解决策略。三样东西各自贡献一种失效模式："),
        ASCII("""链地址法（教学模型；CPython 实际用开放寻址）

  桶数组 (capacity = 8)              装载因子 α = n / capacity
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
  │ 0 │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │
  └─┬─┴───┴─┬─┴───┴─┬─┴───┴───┴───┘
    │       │       │
    ▼       ▼       ▼
   [k8]    [k1]    [k2]              ← 理想：每桶 O(1) 个元素
    │
    ▼
   [k16]                             ← 冲突：同一桶挂成链
    │
    ▼
   [k24]        ← 退化：若所有 key 都映射到同一桶，查找变成 O(n) 的链表扫描

  两种"变慢"要分清：
    ① 一次 rehash（扩容重建）= O(n)，但均摊到 n 次插入是 O(1)  ← 可接受
    ② 哈希函数烂 / 被攻击 → 每次查找都是 O(n)                  ← 不可接受"""),
        H3("均摊分析：为什么扩容不破坏 O(1)"),
        P("CPython 的 dict 在装载因子超过 2/3 时把容量翻倍并重建全部条目。"
          "单次扩容是 $O(n)$，但从空表插到 $n$ 个元素，一共只会在容量为 $1,2,4,\\dots$ 时各触发一次重建，总代价是等比级数："),
        MATH("\\sum_{i=0}^{\\lceil\\log_2 n\\rceil} 2^{i} \\;<\\; 2n \\quad\\Longrightarrow\\quad \\frac{\\text{总重建代价}}{n\\ \\text{次插入}} \\;=\\; O(1)\\ \\text{（均摊）}"),
        P("<strong>「均摊 O(1)」和「每次 O(1)」不是一回事</strong>。对延迟敏感的系统（比如车端每帧要跑的后处理），"
          "均摊 O(1) 意味着<em>某一帧会突然多花几毫秒</em>——这正是模块 00 里说的「延迟均值 vs 延迟分布」。"
          "工程上的对策是<strong>预分配</strong>：如果知道最多有 4000 个候选框，就一次性开好，别让它在关键路径上扩容。"),
        TABLE(["操作", "平均", "最坏", "触发最坏的条件", "面试怎么说"], [
            ["<code>d[k]</code> 查找", "$O(1)$", "<strong>$O(n)$</strong>", "所有 key 哈希到同一桶（自定义 <code>__hash__</code> 返回常数、或被构造的碰撞攻击）", "「期望 O(1)，最坏 O(n)，前提是哈希函数把 key 均匀散开」"],
            ["<code>d[k] = v</code> 插入", "$O(1)$ 均摊", "$O(n)$", "触发 rehash 的那一次", "「均摊 O(1)，但单次可能 O(n)——扩容重建」"],
            ["<code>del d[k]</code>", "$O(1)$", "$O(n)$", "同上", "CPython 删除只打墓碑，不缩容"],
            ["遍历 <code>for k in d</code>", "$O(\\text{capacity})$", "$O(\\text{capacity})$", "大量删除后表很稀疏", "<strong>不是 $O(n)$！</strong>删了 99% 的元素后遍历仍要扫全表"],
            ["<code>k in set</code>", "$O(1)$", "$O(n)$", "同查找", "set 与 dict 是同一套机制"],
        ]),
        H3("Python 面试里真正会踩的三个坑"),
        OL([
            "<strong><code>hash(1) == hash(1.0) == hash(True)</code></strong>。所以 <code>{1: 'x', 1.0: 'y', True: 'z'}</code> "
            "的长度是 <strong>1</strong>，值是 <code>'z'</code>。用「类别 id」做 key 时，如果一条路径传的是 <code>int</code>、"
            "另一条传的是 <code>np.float32</code>，它们会静默合并成同一个 key——<em>这类 bug 不报错，只是统计数字对不上</em>。",
            "<strong>浮点数做 key</strong>。<code>0.1 + 0.2 != 0.3</code>，所以 <code>d[0.1+0.2]</code> 会 KeyError。"
            "更隐蔽的是 <code>float('nan')</code>：<code>nan != nan</code>，但 dict 查找有一条 <em>identity 短路</em>"
            "（先比 <code>is</code> 再比 <code>==</code>），于是<strong>同一个 nan 对象能查到，另一个 nan 对象查不到</strong>。",
            "<strong>可哈希性</strong>。<code>list</code> 不可哈希，<code>tuple</code> 可以，但<em>含 list 的 tuple 又不可以</em>"
            "（哈希是递归计算的）。自定义类如果重写了 <code>__eq__</code> 而没重写 <code>__hash__</code>，"
            "Python 会把 <code>__hash__</code> 设为 <code>None</code>，实例直接变成不可哈希——<em>这是「我的对象放进 set 就报错」的标准答案</em>。",
        ]),
        DUAL(
            "面试里对内置函数的态度要分场合。<strong>如果考点不是哈希</strong>（比如题目是滑动窗口、二分、DP），"
            "直接用 <code>collections.Counter</code>、<code>defaultdict</code>、<code>set</code> 是加分的——它说明你熟悉标准库、代码短、不容易写错。"
            "<strong>如果考点就是哈希本身</strong>（「实现一个 LRU Cache」「设计一个支持 O(1) 随机删除的集合」），"
            "上来就 <code>Counter</code> 会被判「绕过考点」。<em>安全做法：先问一句「我可以用 collections 吗？还是你希望我手写？」——"
            "这一问本身就是分数</em>。",
            "更精确的判据是看<strong>题目要求的复杂度里，哈希是不是那个决定性的一步</strong>。"
            "「两数之和」的 $O(n)$ 解法唯一的技术内容就是「用哈希表把查找从 $O(n)$ 降到 $O(1)$」——"
            "此时用 <code>dict</code> 不是绕过考点，<em>用 <code>dict</code> 就是考点</em>。"
            "而「设计一个 <code>insert/delete/getRandom</code> 都 $O(1)$ 的结构」的考点是"
            "「哈希表存值到下标的映射 + 动态数组存值，删除时用『和末尾交换』避免空洞」——"
            "这里 <code>dict</code> 只是零件，不能替代设计。<strong>一句话：内置容器可以当零件，不能当答案。</strong>",
        ),
        CALLOUT("danger", "<p><strong>会导致线上事故的写法：用浮点数当 key 做分桶。</strong>"
                "评测代码里经常要按 IoU 或框面积分桶统计（呼应 C55-05 的分桶评测、C57-05 的按像素尺寸分桶），"
                "有人会写 <code>buckets[round(iou, 2)] += 1</code>。问题是 <code>round(0.145, 2)</code> 在 IEEE-754 下等于 "
                "<code>0.14</code> 而不是 <code>0.15</code>（因为 0.145 的二进制表示略小于 0.145），"
                "而 <code>round(0.155, 2)</code> 等于 <code>0.16</code>——<em>舍入方向随数值不规则地翻转</em>。"
                "同一份预测在两台机器上算出的 IoU 差 $10^{-16}$，就可能落进不同的桶，"
                "于是「训练机上的评测报告」和「CI 机上的评测报告」对不上。"
                "<strong>正确做法：桶边界用显式的有序数组 + <code>bisect</code> 定位，不要用浮点当 key。</strong></p>",
                "浮点数不能当哈希 key"),
    ])),

    # ============================================================== 2
    ("sort", "排序：自定义键、稳定性，以及 NMS 为什么需要它", "".join([
        P("Python 的 <code>sorted</code> / <code>list.sort</code> 用的是 <span class=\"term\">Timsort</span>"
          "（Tim Peters, 2002），一个「归并排序 + 自适应 run 检测」的混合算法。三条性质要能脱口而出："),
        TABLE(["性质", "含义", "为什么面试里重要"], [
            ["<strong>稳定</strong>", "比较相等的元素保持原相对顺序", "<strong>这是本节的主角</strong>——多关键字排序与输出确定性都靠它"],
            ["<strong>自适应</strong>", "对已经部分有序的输入接近 $O(n)$；最坏 $O(n\\log n)$", "「数据基本有序」是可以说出来的优化理由，比空谈复杂度有说服力"],
            ["<strong>key 只调用 n 次</strong>", "先算好所有 key（decorate-sort-undecorate），再排序", "所以 <code>key=</code> 比 <code>cmp_to_key</code> 快得多；<code>key</code> 里做重活（比如算 IoU）只付 $n$ 次而不是 $n\\log n$ 次"],
        ]),
        H3("多关键字排序的两种写法，以及为什么第二种必须靠稳定性"),
        CODE("""# 写法 A：元组 key —— 首选，一次排序搞定
recs.sort(key=lambda r: (r.cls, -r.score))     # 类别升序、分数降序

# 问题：字符串没法「取负」。下面这句是错的
recs.sort(key=lambda r: (-r.score, -r.name))   # ✗ TypeError

# 写法 B：分次排序 —— 从次关键字排到主关键字，靠稳定性把结果叠起来
recs.sort(key=lambda r: r.name)                 # ② 次关键字：名字升序
recs.sort(key=lambda r: r.score, reverse=True)  # ① 主关键字：分数降序
# 稳定性保证：分数相同的记录，仍保持上一步排好的名字顺序""",),
        P("<strong>写法 B 的顺序是反的</strong>（先排次要的、后排主要的），这是稳定排序最经典的应用，"
          "也是面试里「稳定性有什么用」的标准答案之一。<em>如果排序不稳定，写法 B 直接失效。</em>"),
        H3("真正的重点：NMS 的确定性依赖排序稳定性"),
        P("<span class=\"term\">NMS</span>（non-maximum suppression）的第一步是按分数降序排序，然后贪心地「保留最高分、抑制与它 IoU 超阈值的框」。"
          "问题来了：<strong>如果两个重叠的框分数完全相同，保留哪一个？</strong>"),
        ASCII("""两个 IoU = 0.72 的框，分数都是 0.90

  排序结果 [A, B]  →  保留 A，抑制 B  →  输出框在 (100,200,140,240)
  排序结果 [B, A]  →  保留 B，抑制 A  →  输出框在 (103,204,143,244)
                                            ↑ 差了 3 像素，下游的距离估计就差了

  "分数完全相同"有多罕见？一点也不罕见：
    · INT8 量化后，分类头的输出只有 256 个可能取值 → 大量并列   （见 C60）
    · 分数被 round 到 3 位小数后再排序                          （常见的日志/导出代码）
    · 同一个目标的多个候选框，特征几乎一样 → 浮点结果逐位相同""",),
        P("而排序实现的 tie-break 行为在各处<strong>不一致</strong>："),
        TABLE(["实现", "是否稳定", "并列时的顺序", "风险"], [
            ["Python <code>sorted</code> / <code>list.sort</code>", "<strong>稳定</strong>", "保持输入顺序", "安全，但依赖「输入顺序本身是确定的」"],
            ["<code>np.argsort(x)</code>（默认 quicksort）", "<strong>不稳定</strong>", "由 introsort 的划分决定，随数组长度和内容变化", "<strong>同一批框换个顺序输入，结果就变</strong>"],
            ["<code>np.argsort(x, kind='stable')</code>", "稳定", "保持输入顺序", "推荐"],
            ["<code>torch.sort</code>", "默认不保证；需 <code>stable=True</code>", "CUDA 上与 CPU 上可能不同", "训练端与部署端 tie-break 不一致"],
            ["TensorRT <code>TopK</code> / EfficientNMS", "未文档化保证", "由 kernel 的归约顺序决定", "<strong>车端与离线复现不一致的经典来源</strong>（见 C60）"],
        ]),
        DUAL(
            "这类 bug 的表现极具迷惑性：一致性对拍时，1000 帧里有 3 帧出现「1 个框不一致」，位置差几个像素，分数完全相同。"
            "你会先去怀疑预处理、怀疑量化、怀疑算子精度——<strong>而真正的原因只是两个并列分数的排序顺序不同</strong>。"
            "<em>修法只有一行：把排序键从 <code>-score</code> 换成一个保证唯一的元组。</em>",
            "严谨的表述：NMS 的输出是排序结果的函数，而排序在存在并列键时是<strong>一个关系而不是一个函数</strong>——"
            "它把一个输入映射到一组合法输出。要让整条流水线成为确定性函数，必须给排序键补上一个"
            "<span class=\"term\">total order</span>（全序）：把键扩展成 <code>(-score, class_id, x1, y1, box_index)</code> 之类，"
            "使任意两个不同元素的键都不相等。<strong>这样一来，是否稳定就不再重要了——因为根本不会出现并列。</strong>"
            "<em>这个技巧的通用形式叫「tiebreaker 消歧」，在任何「结果依赖排序顺序」的贪心算法里都适用</em>"
            "（模块 04 的区间调度、模块 03 的并查集聚类都会再遇到）。",
        ),
        CALLOUT("intuition", "一条可迁移的心法：<strong>凡是贪心算法，输出就依赖于排序顺序；凡是依赖排序顺序，"
                "就必须保证排序键是全序的。</strong><em>面试里被问「你的代码是确定性的吗」，"
                "能主动指出这一点比写出正确解法更显水平。</em>"),
    ])),

    # ============================================================== 3
    ("binsearch", "二分的三套模板与循环不变量", "".join([
        P("二分是「看起来会、写起来错」的头号题型。工程上的统计口径是：<strong>相当一部分工程师无法在不调试的情况下一次写对二分</strong>"
          "（Bentley 在《Programming Pearls》里做过课堂实验，Bloch 在 2006 年发现 JDK 里的二分查找有溢出 bug 且存在了九年）。"
          "面试里写错二分的代价特别高，因为<em>它是「基础题」，写错等于基础不牢</em>。"),
        P("解决办法不是「多做题找感觉」，是<strong>把循环不变量写下来，然后让每一行代码都为不变量服务</strong>。"),
        H3("先把前提说清楚：二分的条件不是「有序」"),
        P("很多人以为二分的前提是「数组有序」。<strong>更本质的前提是：存在一个把搜索空间切成两段的单调谓词</strong> $\\text{check}(x)$，"
          "使得它在前一段恒假、后一段恒真（或反过来）。数组有序只是让 <code>a[mid] &lt; t</code> 这个谓词单调的一个<em>充分条件</em>。"),
        MATH("\\exists\\, x^\\ast \\in [L, R]:\\quad \\text{check}(x)=\\text{False}\\ \\ \\forall x < x^\\ast, \\qquad \\text{check}(x)=\\text{True}\\ \\ \\forall x \\ge x^\\ast"),
        P("<strong>写二分之前，先把 <code>check</code> 写出来并确认它单调。</strong>做到这一步，第 5 节的「在答案上二分」就是同一套模板的直接应用。"),
        H3("模板 A · 找精确值（闭区间 $[lo, hi]$）"),
        CODE("""def bs_exact(a, t):
    \"\"\"不变量 I_A：若 t 存在于 a 中，则它的下标一定在闭区间 [lo, hi] 内。
       循环条件 lo <= hi 正是「闭区间非空」。\"\"\"
    lo, hi = 0, len(a) - 1              # 初始区间 = 全数组，I_A 显然成立
    while lo <= hi:
        mid = lo + (hi - lo) // 2       # 写成这样而不是 (lo+hi)//2：防止大整数溢出（Python 无此问题，C++/Java 有）
        if a[mid] == t:
            return mid
        if a[mid] < t:
            lo = mid + 1                # a[mid] 及其左边全 < t，t 不可能在那里 → I_A 保持
        else:
            hi = mid - 1                # a[mid] 及其右边全 > t → I_A 保持
    return -1                           # 区间空 ⇒ 由 I_A，t 不存在""",),
        H3("模板 B · 找左边界（半开区间 $[lo, hi)$）= <code>bisect_left</code>"),
        CODE("""def bs_left(a, t):
    \"\"\"返回第一个 >= t 的下标（不存在则返回 len(a)）。
       不变量 I_B：a[0:lo] 全部 < t   且   a[hi:n] 全部 >= t
       循环结束时 lo == hi，于是「< t」和「>= t」的分界点就是 lo。\"\"\"
    lo, hi = 0, len(a)                  # a[0:0] 与 a[n:n] 都是空集，I_B 平凡成立
    while lo < hi:
        mid = lo + (hi - lo) // 2       # lo <= mid < hi（下取整保证 mid != hi）
        if a[mid] < t:
            lo = mid + 1                # a[0:mid+1] 全 < t（因为有序）→ I_B 保持
        else:
            hi = mid                    # a[mid:n] 全 >= t → I_B 保持；注意是 mid 不是 mid-1
    return lo""",),
        H3("模板 C · 找右边界（半开区间 $[lo, hi)$）= <code>bisect_right</code>"),
        CODE("""def bs_right(a, t):
    \"\"\"返回第一个 > t 的下标。
       不变量 I_C：a[0:lo] 全部 <= t   且   a[hi:n] 全部 > t
       与模板 B 只差一个符号：a[mid] < t  →  a[mid] <= t\"\"\"
    lo, hi = 0, len(a)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if a[mid] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo""",),
        ASCII("""三套模板的区间语义（数组 a = [1, 3, 3, 3, 7]，t = 3）

  下标:      0    1    2    3    4         5
  值:        1    3    3    3    7        (末尾哨兵位)
             │    │              │         │
             │    └─ bs_left  = 1          │
             │       第一个 >= 3            │
             │                  └─ bs_right = 4
             │                     第一个 > 3
             └─ bs_exact 返回 1/2/3 中的某一个（不保证是哪个！）

  由 B 和 C 派生出的一切（**只背 B 和 C，其余现推**）：
    出现次数         = bs_right(a,t) - bs_left(a,t)          = 4 - 1 = 3
    最后一个 <= t    = bs_right(a,t) - 1                     = 3
    最后一个 <  t    = bs_left(a,t) - 1                      = 0
    第一个   >  t    = bs_right(a,t)                         = 4
    精确查找         = i = bs_left(a,t);  a[i] == t ?  i : -1
  ⇒ 面试里不要背三套模板，背 bs_left 一套 + 上面这张换算表。""",),
        H3("终止性：为什么这两套模板一定不死循环"),
        P("记第 $k$ 轮的区间长度 $\\ell_k = hi_k - lo_k$。模板 B/C 里 $mid = lo + \\lfloor \\ell_k/2 \\rfloor$，于是："),
        MATH("\\ell_{k+1} \\;=\\; \\begin{cases} hi_k - (mid+1) \\;=\\; \\lceil \\ell_k/2\\rceil - 1 & \\text{（走 } lo=mid+1\\text{）}\\\\[2pt] mid - lo_k \\;=\\; \\lfloor \\ell_k/2 \\rfloor & \\text{（走 } hi=mid\\text{）}\\end{cases} \\qquad \\Longrightarrow\\qquad \\ell_{k+1} < \\ell_k \\ \\ (\\forall\\, \\ell_k \\ge 1)"),
        P("<strong>两个分支都严格缩小区间</strong>，而 $\\ell$ 是非负整数，所以循环至多执行 $\\lceil \\log_2 n\\rceil$ 轮后 $\\ell = 0$，退出。"
          "<em>这就是「不会死循环」的完整证明——面试里说得出这句话，比说「我一般写 <code>hi = mid</code>」有份量得多。</em>"
          "注意关键点：当 $\\ell_k = 1$ 时 $mid = lo_k$，<strong>走 <code>hi = mid</code> 分支得到 $\\ell_{k+1} = 0$——正因为用了下取整，这个分支才没有卡死</strong>。"),
        DUAL(
            "记不住哪个模板对应哪种边界？给一个不用背的办法：<strong>写完循环体，用「区间只剩两个元素」的情形手推一遍</strong>。"
            "$lo, hi$ 相邻时 $mid$ 落在哪、两个分支各把区间变成什么——推 30 秒就能确定它会不会卡住。"
            "<em>这个手推动作在面试里应该<strong>说出来</strong>：「我验一下 lo 和 hi 相邻的情况……」——这是测试意识的直接展示。</em>",
            "更系统的方法是<span class=\"term\">循环不变量</span>三段式验证，这也是 Hoare 逻辑在实践中最常用的形式："
            "<em>①初始化</em>——进入循环前不变量成立（空区间上平凡成立）；"
            "<em>②保持</em>——若进入某轮时成立，则该轮结束时仍成立（这一步逼你说清「为什么 <code>lo = mid + 1</code> 是安全的」）；"
            "<em>③终止</em>——退出条件 + 不变量 ⇒ 目标结论（<code>lo == hi</code> 且 <code>a[:lo] &lt; t &lt;= a[hi:]</code> ⇒ <code>lo</code> 就是左边界）。"
            "<strong>再加上一个严格递减的整数度量（这里是 $\\ell$）就得到终止性。</strong>"
            "四件事写完，二分的正确性就是被证明的而不是被测试的。",
        ),
        CALLOUT("warn", "<code>mid = (lo + hi) // 2</code> 在 Python 里永远安全（大整数），"
                "但在 C++/Java/CUDA kernel 里当 <code>lo + hi</code> 超过 <code>INT_MAX</code> 会溢出成负数——"
                "<strong>这就是 Bloch 2006 年在 JDK 里找到的那个 bug</strong>。"
                "面试写 Python 时用 <code>lo + (hi - lo) // 2</code> 并顺口提一句「这样写是为了在 C++ 里也不溢出」，"
                "是一个成本极低、辨识度很高的加分动作。"),
    ])),

    # ============================================================== 4
    ("deadloop", "死循环的四种成因：开闭区间不一致", "".join([
        P("二分的所有 bug 几乎都能归到同一个根因：<strong>区间的开闭约定和更新语句不匹配</strong>。"
          "「$hi$ 是最后一个候选下标」（闭）和「$hi$ 是第一个被排除的下标」（半开）是两套不能混用的约定，"
          "而它们的初始化、循环条件、更新语句<em>各有一套配套写法</em>，混搭必出事。"),
        TABLE(["约定", "初始化", "循环条件", "排除 mid 的写法", "保留 mid 的写法"], [
            ["闭区间 $[lo, hi]$", "<code>hi = n - 1</code>", "<code>lo &lt;= hi</code>", "<code>lo = mid+1</code> / <code>hi = mid-1</code>", "<code>lo = mid</code> / <code>hi = mid</code>（<strong>危险</strong>，需配上取整）"],
            ["半开区间 $[lo, hi)$", "<code>hi = n</code>", "<code>lo &lt; hi</code>", "<code>lo = mid+1</code>", "<code>hi = mid</code>（安全）"],
        ]),
        H3("四种典型翻车"),
        TABLE(["#", "错误写法", "后果", "为什么"], [
            ["①", "<code>hi = len(a)</code> 配 <code>while lo &lt;= hi</code>", "<strong>IndexError</strong>", "当 <code>lo == hi == n</code> 时 <code>mid == n</code>，<code>a[n]</code> 越界"],
            ["②", "半开区间里写 <code>lo = mid</code>（忘了 <code>+1</code>）", "<strong>死循环</strong>", "<code>hi = lo+1</code> 时 <code>mid = lo</code>，走这支后 <code>lo</code> 不变、<code>hi</code> 不变 → 区间永不缩小"],
            ["③", "求右边界时用 <code>lo = mid</code> 配 <strong>下取整</strong> mid", "<strong>死循环</strong>", "同 ②。求右边界必须用 <code>mid = lo + (hi - lo + 1) // 2</code>（<strong>上取整</strong>）把 mid 顶到右边"],
            ["④", "半开区间里写 <code>hi = mid - 1</code>", "<strong>漏解</strong>（返回值偏小或 -1）", "半开区间里 <code>a[hi]</code> 本来就不在候选内，再减 1 等于多排除一个合法候选"],
        ]),
        ASCII("""成因 ② 的执行轨迹（a = [1, 3, 5]，找第一个 >= 5，错写成 lo = mid）

   轮次   lo   hi   mid   a[mid]   判断        更新           区间长度
   ─────────────────────────────────────────────────────────────────
     1     0    3    1      3      3 < 5      lo = mid = 1        3 → 2
     2     1    3    2      5      5 >= 5     hi = mid = 2        2 → 1
     3     1    2    1      3      3 < 5      lo = mid = 1        1 → 1   ← 不变！
     4     1    2    1      3      3 < 5      lo = mid = 1        1 → 1   ← 不变！
     ...                                                          ∞

   根因：区间长度为 1 时，下取整让 mid == lo；
        而 `lo = mid` 这条更新**没有跨过 mid**，于是度量函数不再递减。

   通用判据（背这一条就够）：
     ┌───────────────────────────────────────────────────────────┐
     │  mid 落在区间的哪一半，那一半的更新语句就必须「跨过 mid」  │
     │  下取整 mid 偏左  ⇒  左侧更新必须写 lo = mid + 1           │
     │  上取整 mid 偏右  ⇒  右侧更新必须写 hi = mid - 1           │
     └───────────────────────────────────────────────────────────┘""",),
        DUAL(
            "考场上的自保流程只有三步，30 秒能做完：<em>①写下你用的是闭区间还是半开区间，"
            "并把这句话<strong>说出来</strong>（「我用半开区间 [lo, hi)，hi 是第一个被排除的位置」）；"
            "②按上表抄配套写法；③用「区间只剩 1–2 个元素」手推一遍</em>。"
            "<strong>第①步的价值不只是防错——它让面试官知道你脑子里有明确的约定，而不是在试。</strong>",
            "如果你已经陷进去了（跑不出来 / 结果偏 1），<strong>不要盲改 <code>+1 -1</code></strong>——"
            "这是面试里最糟糕的画面，改一次跑一次，五分钟就没了。正确的补救是回到不变量："
            "<em>把「循环退出时 lo 应该满足什么」写在纸上（或注释里），再倒推每个分支是否维持了它</em>。"
            "一个实用的兜底手段是<strong>加一个步数上界</strong>：<code>for _ in range(len(a).bit_length() + 2)</code> "
            "替代 <code>while</code>，这样即使写错也只是结果错而不是挂死——"
            "<em>在压力下把「死循环」降级成「答案错」，是能救命的工程习惯</em>。",
        ),
        CALLOUT("danger", "<p><strong>面试当场翻车的场景：二分死循环。</strong>共享屏幕的编辑器卡住、进程没响应、你开始慌——"
                "这几乎是 coding 环节最难看的失败模式，因为它同时暴露了「不会写二分」和「没有测试意识」两件事。"
                "<strong>预防成本极低：所有二分统一用半开区间 + <code>bisect_left</code> 模板，"
                "其余边界一律用第 3 节的换算表现推。</strong>"
                "<em>如果真的卡住了，标准话术是：「我先加一个循环次数上界，把死循环变成可观察的错误，再看不变量哪里破了。」"
                "——面试官要的是这句话，不是你立刻改对。</em></p>", "死循环 = 双重扣分"),
    ])),

    # ============================================================== 5
    ("answer-space", "在答案上二分：最小化最大值 / 最大化最小值", "".join([
        P("这是<strong>中高频、且区分度最高</strong>的一类二分题。它的特征是：题面里出现「最小化最大的 X」「最大化最小的 X」"
          "「至少需要多少 Y」，而且<em>直接求最优解很难，但给定一个候选答案去验证可行性却很容易</em>。"),
        P("识别信号（三个都满足就基本可以断定）："),
        OL([
            "<strong>答案是一个数，且取值范围有明确上下界</strong>（$L$ = 最松/一定可行，$R$ = 最紧/一定不可行，或反过来）。",
            "<strong>存在一个单调的可行性谓词</strong>：若容量 $x$ 可行，则 $x+1$ 也一定可行（放宽约束不会让问题变难）。",
            "<strong><code>check(x)</code> 好写</strong>——通常是一遍 $O(n)$ 的贪心扫描。",
        ]),
        P("满足这三条，答案就是那个「谓词第一次为真的位置」，直接套模板 B："),
        MATH("x^\\ast \\;=\\; \\min\\,\\{\\, x \\in [L, R] \\;:\\; \\text{check}(x) = \\text{True} \\,\\} \\qquad \\text{总复杂度} \\;=\\; O\\bigl(\\,\\text{cost}(\\text{check}) \\cdot \\log (R-L)\\,\\bigr)"),
        H3("样板题：分割数组的最大值（LeetCode 410）"),
        P("把非负数组 <code>a</code> 分成 <code>m</code> 个连续子数组，使得<strong>各子数组和的最大值最小</strong>。"
          "直接做是区间 DP，$O(n^2 m)$；在答案上二分只要 $O(n\\log(\\sum a))$。"),
        CODE("""def split_array(a, m):
    # check(cap): 每段和都不超过 cap 的前提下，贪心地尽量多塞，最少需要几段？
    # 单调性：cap 越大 → 需要的段数单调不增 → parts(cap) <= m 是单调谓词  ✔
    def parts(cap):
        cnt, cur = 1, 0
        for x in a:
            if cur + x <= cap:
                cur += x
            else:
                cnt += 1; cur = x       # 开新的一段（贪心：能塞就塞是最优的）
        return cnt

    lo, hi = max(a), sum(a)             # lo：一段都装不下单个元素就不可能可行；hi：全放一段一定可行
    while lo < hi:                      # 半开区间 [lo, hi]，不变量：答案 ∈ [lo, hi]
        mid = lo + (hi - lo) // 2
        if parts(mid) <= m:
            hi = mid                    # mid 可行 → 答案 <= mid，保留 mid
        else:
            lo = mid + 1                # mid 不可行 → 答案 > mid
    return lo""",),
        P("<strong>两个边界的选取是这类题最容易错的地方</strong>：$lo$ 必须取「显然不可行的下界」或「可行性刚好可能开始的位置」"
          "——这里 $\\max(a)$ 是硬下界（任何一段至少要装得下最大的那个元素）；$hi$ 必须取「一定可行的上界」——全放一段即 $\\sum a$。"
          "<em>把边界的物理含义说出来，比写对代码更能证明你理解了</em>。"),
        H3("同一个模板下的题族"),
        TABLE(["题", "答案空间 $x$", "check(x)", "单调方向", "频率 / 层级"], [
            ["分割数组的最大值 (LC410)", "每段和的上限", "贪心分段，段数 $\\le m$", "$x\\uparrow$ ⇒ 更容易可行", "<strong>高频 / 必会</strong>"],
            ["在 D 天内送达包裹 (LC1011)", "船的载重", "贪心装船，天数 $\\le D$", "同上", "<strong>高频 / 必会</strong>"],
            ["爱吃香蕉的珂珂 (LC875)", "每小时吃的速度", "$\\sum \\lceil p_i/x\\rceil \\le H$", "同上", "中频 / 必会"],
            ["制作 m 束花所需最少天数 (LC1482)", "天数", "扫一遍数连续可用段", "同上", "中频 / 加分"],
            ["第 K 小的数对距离 (LC719)", "距离阈值", "双指针数「距离 $\\le x$ 的对数」$\\ge K$", "同上", "低频 / 加分"],
            ["最大化最小间距（放置 m 个物体）", "最小间距", "贪心放置，能放下 $\\ge m$ 个", "$x\\uparrow$ ⇒ <strong>更难</strong>可行（方向相反，找最后一个真）", "中频 / 加分"],
        ]),
        H3("CV / 感知工程里的同构问题（这才是本课的锚点）"),
        UL([
            "<strong>「给定 30 ms 的延迟预算，输入分辨率最大能开到多少？」</strong> "
            "$\\text{check}(r) = \\text{latency}(r) \\le 30$，分辨率越大延迟越大 ⇒ 谓词单调递减 ⇒ 二分找<em>最后一个</em>可行的 $r$。"
            "<em>这就是 C53-05 的选型问题的一维版本。</em>",
            "<strong>「要让召回率不低于 0.95，score 阈值最高能设到多少？」</strong> "
            "$\\text{check}(\\tau) = \\text{recall}(\\tau) \\ge 0.95$。$\\tau$ 越大召回越低 ⇒ 单调 ⇒ 二分。"
            "<em>这正是 C55-05 的工作点选择——而它在代码上就是一次答案空间二分。</em>",
            "<strong>「切片推理时重叠率最小取多少能保证不漏检？」</strong> "
            "$\\text{check}(\\rho) = $「任意目标至少完整落在一个切片内」，重叠越大越安全 ⇒ 单调 ⇒ 二分求下界（呼应 C57-04）。",
            "<strong>「标注预算固定，采样阈值取多少能覆盖长尾类的目标数量？」</strong> "
            "$\\text{check}(\\theta)$ = 触发量 $\\le$ 带宽预算（呼应 C58-03 的触发器阈值优化）。",
        ]),
        DUAL(
            "为什么这类题在 ML/CV 岗特别常见？因为<strong>工程里大量的决策就长这个样子</strong>：一个连续的旋钮（阈值、分辨率、批大小、重叠率），"
            "一个单调的约束（延迟、召回、带宽、显存），要找旋钮的极限位置。"
            "<em>你在工作里做的「二分调参」和面试里的 LC410，是同一个算法</em>——"
            "面试里能主动把这层联系说出来，是把「刷题」变成「工程直觉」的最直接证据。",
            "两个必须警惕的失效条件。<em>①单调性不成立</em>：延迟对分辨率<strong>不是</strong>严格单调的"
            "（TensorRT 会在特定尺寸上选到更优的 kernel，出现「更大反而更快」的反常点），"
            "此时二分会收敛到一个局部错误的答案——<strong>正确做法是先扫一遍粗网格确认单调，再在单调段内二分</strong>。"
            "<em>②浮点答案空间</em>：不能用 <code>while lo &lt; hi</code>（浮点相等几乎永不成立，会死循环），"
            "要用<strong>固定迭代次数</strong>——<code>for _ in range(100): mid = (lo+hi)/2; ...</code>，"
            "100 次把区间缩小 $2^{-100}$，远超 double 的精度，绝对够用且绝不死循环。",
        ),
        CALLOUT("warn", "<strong>面试里必须主动验证单调性。</strong>直接写「这题二分答案」而不说明 <code>check</code> 为什么单调，"
                "是典型的「背题痕迹」。正确的一句话是：「<em>我先确认单调性——如果容量 x 能装下，那 x+1 显然也能装下，"
                "所以 check 是单调的，可以二分。</em>」<strong>说这一句大约花 8 秒，但它把「我做过这题」变成了「我知道为什么可以这么做」。</strong>"),
    ])),

    # ============================================================== 6
    ("topk", "Top-K 的三种解法与选择依据", "".join([
        P("「从 $n$ 个数里取最大的 $k$ 个」是 ML/CV 岗的超高频题型，"
          "因为它在真实系统里到处都是：NMS 前的候选框截断、难例挖掘的回传排序（C58-03）、检索的近邻返回（C58-04）、"
          "长尾类别的重采样。三种解法要能<strong>同时说出复杂度、空间、副作用和适用场景</strong>。"),
        ASCII("""          ┌──────────────────────────────────────────────────┐
  n 个数  │  ① 全排序      sorted(a)[-k:]                     │  O(n log n)  空间 O(n)
  ───────►│  ② 大小为 k 的最小堆                              │  O(n log k)  空间 O(k)   ← 流式可用
          │     for x in a: heappushpop(h, x)                 │
          │  ③ quickselect  随机主元三路划分，只递归一侧      │  O(n) 期望   空间 O(1)   ← 破坏原数组
          └──────────────────────────────────────────────────┘

  ② 的关键性质：**只需要一次遍历，且内存只占 k**。
     数据是一条流（车队每天几 TB 的回传候选）时，①③ 都要求全量落地，② 不用。

  ③ 的关键性质：**期望 O(n)，最坏 O(n²)**。
     最坏发生在「每次主元都选到极值」——有序输入 + 固定取首元素做主元 = 必然退化。
     修法：随机主元（工程标配）或 median-of-medians（理论 O(n) 最坏，常数太大，实践不用）。""",),
        TABLE(["方法", "时间", "额外空间", "输出是否有序", "改动原数组", "什么时候选它"], [
            ["<strong>① 全排序</strong>", "$O(n\\log n)$", "$O(n)$", "<strong>是</strong>", "否（<code>sorted</code>）", "$k$ 接近 $n$；需要有序输出；<strong>$n$ 不大时它实际最快</strong>（见下）"],
            ["<strong>② 堆</strong>", "$O(n\\log k)$", "<strong>$O(k)$</strong>", "否（需再排 $k\\log k$）", "否", "<strong>$k \\ll n$；数据是流；内存受限</strong>"],
            ["<strong>③ quickselect</strong>", "$O(n)$ 期望 / $O(n^2)$ 最坏", "$O(1)$", "否", "<strong>是</strong>", "$n$ 极大且能一次性放进内存；只要「哪 $k$ 个」不要顺序"],
        ]),
        MATH("\\frac{T_{\\text{sort}}}{T_{\\text{heap}}} \\;=\\; \\frac{n\\log_2 n}{n\\log_2 k} \\;=\\; \\frac{\\log_2 n}{\\log_2 k} \\;=\\; \\frac{1}{\\alpha} \\quad\\text{（记 } k = n^{\\alpha}\\text{）} \\qquad\\Longrightarrow\\qquad k=\\sqrt{n}\\ \\text{时堆只快 2 倍}"),
        P("<strong>这个公式值得记住，因为它解释了一个反直觉的现实：堆的渐进优势远没有想象中大。</strong>"
          "$n = 10^6$、$k = 100$ 时，$\\log_2 n / \\log_2 k \\approx 20/6.6 \\approx 3$ 倍——"
          "而 Python 的 <code>sorted</code> 是 C 实现的 Timsort，常数比纯 Python 的堆循环小一到两个数量级。"
          "<em>notebook 会实测给你看：在 Python 里，$n = 10^5$ 量级时 <code>sorted(a)[-k:]</code> 往往比手写 quickselect 还快。</em>"),
        DUAL(
            "所以面试里被问「用哪个」，最好的答案不是报一个方法名，而是<strong>先反问约束</strong>："
            "「$k$ 和 $n$ 的量级是多少？数据能一次放进内存吗？需要有序输出吗？可以改原数组吗？」"
            "<em>四个问题问完，选哪个是自明的</em>——而且你已经展示了「按约束做决策」的思维方式，这正是模块 00 说的评分维度。",
            "更进一步，能主动区分<strong>渐进复杂度</strong>与<strong>实际耗时</strong>是一个很强的信号。"
            "标准说法：「<em>渐进上 quickselect 是 $O(n)$ 最优，但在 CPython 里 <code>sorted</code> 走的是 C 层 Timsort，"
            "常数小两个数量级；如果 $n$ 只有 $10^5$，我会先写 <code>sorted</code>，"
            "只有在 profile 证明这里是瓶颈、或者数据规模到 $10^7$ 以上时才换 quickselect。</em>」"
            "<strong>「先测量再优化」和「知道复杂度只是常数未知的上界」是两个独立的加分点，这句话同时拿到。</strong>"
            "<em>反过来，如果你张口就说「必须用 quickselect 因为它是 O(n)」，成熟度会被打折。</em>",
        ),
        H3("回到检测：NMS 前的 top-K 截断"),
        P("生产级检测后处理（TensorRT 的 <code>EfficientNMS</code>、MMDetection 的 <code>nms_pre</code>）"
          "几乎都会在 NMS 之前先做一次 <strong>top-1000 by score</strong>。这不是为了精度，是为了<strong>把最坏耗时钉死</strong>："
          "NMS 的代价是 $O(NK)$，$N$ 是过阈候选数；不截断时 $N$ 随场景无上界，截断后 $N \\le 1000$ 是常数（呼应 C53-04 的 WCET 讨论）。"
          "<em>代价是：极端密集的场景（一整排限速牌 + 龙门架）可能有目标被截掉，所以评测里必须专门覆盖这类切片。</em>"),
        CALLOUT("intuition", "把三种解法压成一句：<strong>全排序买「有序」，堆买「小内存 + 流式」，quickselect 买「渐进最优」。"
                "你付的钱分别是 $\\log n$ 因子、$\\log k$ 因子、和最坏情况的保证。</strong>"
                "<em>面试里说清「买了什么、付了什么」，比背三段代码有用。</em>"),
    ])),

    # ============================================================== 7
    ("dedup", "去重、计数与分桶：四种惯用法和它们的差别", "".join([
        P("去重和计数看起来是最简单的操作，但四种写法在<strong>是否保序、复杂度、额外空间</strong>上各不相同，"
          "面试里被追问「还有别的写法吗」时能一次说全四种，是很轻松的加分。"),
        TABLE(["写法", "时间", "额外空间", "保持原顺序", "要求输入有序", "备注"], [
            ["<code>set(a)</code>", "$O(n)$", "$O(n)$", "<strong>否</strong>", "否", "最快，但顺序不确定 ⇒ <strong>不要用于需要确定性输出的场合</strong>"],
            ["<code>list(dict.fromkeys(a))</code>", "$O(n)$", "$O(n)$", "<strong>是</strong>", "否", "CPython 3.7+ 起 dict 保持插入序是<em>语言规范</em>，可以放心用"],
            ["排序后相邻比较", "$O(n\\log n)$", "$O(1)$（原地排序）", "否", "否", "元素<strong>不可哈希</strong>但可比较时唯一的选择"],
            ["双指针原地去重", "$O(n)$", "<strong>$O(1)$</strong>", "是", "<strong>是</strong>", "模块 01 的快慢指针；面试题「删除有序数组中的重复项」"],
        ]),
        H3("计数的确定性陷阱"),
        P("<code>Counter(a).most_common(k)</code> 在<strong>频次并列时按插入顺序</strong>返回，不是按字典序。"
          "这意味着「同一份数据、不同的读取顺序 → 不同的 top-k 输出」——又是一个 tie-break 不确定性（和第 2 节的 NMS 是同一个病）。"
          "要确定性就必须显式给出全序键："),
        CODE("""from collections import Counter

c = Counter(a)
# ✗ 并列时的顺序依赖插入序，不可复现
top = c.most_common(k)

# ✓ 显式全序：先按频次降序，再按元素本身升序
top = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:k]

# ✓ 桶排序版本：频次是 [0, n] 的整数 ⇒ 可以 O(n) 完成（不需要 O(n log n)）
buckets = [[] for _ in range(len(a) + 1)]
for val, cnt in c.items():
    buckets[cnt].append(val)
out = []
for cnt in range(len(a), 0, -1):
    for val in sorted(buckets[cnt]):          # 桶内排序保证确定性
        out.append(val)
        if len(out) == k:
            break""",),
        P("<strong>「前 K 个高频元素」的桶排序解法（$O(n)$）是这道高频题的加分答案</strong>："
          "频次的取值范围被 $n$ 界住了，所以可以用计数排序思想直接把 $\\log$ 因子消掉。"
          "<em>面试里先给堆解法 $O(n\\log k)$，再补一句「如果要严格 $O(n)$，可以用桶排序，因为频次上界是 n」——这是标准的「先给可行解、再给优化」节奏。</em>"),
        H3("分桶：把连续值离散化成整数 key"),
        P("按尺寸 / 距离 / IoU 分桶做切片评测（C55-05、C57-05）是感知工程里最常做的统计。"
          "第 1 节已经说过<strong>不能用浮点当 key</strong>，正确姿势是显式桶边界 + <code>bisect</code>："),
        CODE("""import bisect

EDGES = [0, 16, 32, 64, 128, 256]     # 像素面积开方后的分桶边界（COCO 风格）
LABELS = ['<16', '16-32', '32-64', '64-128', '128-256', '>=256']

def bucket_of(v):
    # bisect_right 返回「第一个 > v 的边界下标」，减 1 就是 v 落在哪个区间
    # 不变量：EDGES[i] <= v < EDGES[i+1]  ⇔  返回 i
    i = bisect.bisect_right(EDGES, v) - 1
    return min(max(i, 0), len(LABELS) - 1)

# bucket_of(31.999999999) -> 1  ('16-32')；bucket_of(32.0) -> 2  ('32-64')
# 边界归属是**明确的**（左闭右开），不依赖浮点相等""",),
        H3("本模块的高频题单（按优先级排）"),
        TABLE(["题", "考点", "频率", "层级", "一句话解法"], [
            ["两数之和", "哈希", "<strong>高频</strong>", "<strong>必会</strong>", "边扫边把 <code>值→下标</code> 存进 dict，查 <code>t - a[j]</code>"],
            ["在排序数组中查找元素的首末位置", "二分左右边界", "<strong>高频</strong>", "<strong>必会</strong>", "<code>bs_left</code> 与 <code>bs_right - 1</code>"],
            ["搜索旋转排序数组", "二分 + 判断哪半有序", "<strong>高频</strong>", "<strong>必会</strong>", "比较 <code>a[lo]</code> 与 <code>a[mid]</code> 定位有序半区，再判 t 是否落在其中"],
            ["前 K 个高频元素", "哈希 + 堆 / 桶排序", "<strong>高频</strong>", "<strong>必会</strong>", "Counter + 大小 k 的堆；加分答案是桶排序 $O(n)$"],
            ["分割数组的最大值 / D 天送达", "答案空间二分", "<strong>高频</strong>", "<strong>必会</strong>", "贪心 <code>check(cap)</code> + 模板 B"],
            ["数组中的第 K 个最大元素", "quickselect / 堆", "<strong>高频</strong>", "<strong>必会</strong>", "随机主元三路划分；要能说出最坏 $O(n^2)$"],
            ["最长连续序列", "哈希集合", "中频", "<strong>必会</strong>", "只从「$x-1$ 不在集合里」的 $x$ 起步向右数，总代价 $O(n)$"],
            ["有效的字母异位词 / 字母异位词分组", "哈希计数", "中频", "必会", "排序后的字符串或 26 维计数元组做 key"],
            ["颜色分类（荷兰国旗）", "三路划分", "中频", "加分", "三指针一次扫描；和 quickselect 的划分是同一段代码"],
            ["H 指数", "排序 / 计数排序", "中频", "加分", "降序排后找最大的 $i$ 使 $c[i-1] \\ge i$"],
            ["寻找峰值 / 山脉数组的峰顶", "二分（谓词不是有序性）", "中频", "加分", "<code>a[mid] &lt; a[mid+1]</code> 即峰在右——<strong>无序数组也能二分</strong>"],
            ["第 K 小的数对距离", "答案二分 + 双指针计数", "低频", "加分", "二分距离阈值，双指针数对数"],
            ["两个有序数组的中位数", "分割点二分", "低频", "加分", "在短数组上二分分割点，$O(\\log \\min(m,n))$"],
        ]),
        CALLOUT("intuition", "<strong>「寻找峰值」这道题是理解二分的试金石。</strong>数组完全无序，但"
                "「<code>a[mid] &lt; a[mid+1]</code> ⇒ 右侧必有峰」这个谓词是单调可用的——"
                "<em>它证明了第 3 节那句话：二分的前提是「存在可切分的单调判据」，而不是「数组有序」。</em>"
                "面试里能拿这道题反过来解释二分的本质，说明你不是在背模板。"),
    ])),

    # ============================================================== 8
    ("interview", "面试标准答案骨架", "".join([
        P("这一节请当作可背诵材料。组织原则和模块 00 一致：<strong>先给判断，再给机制，最后给数字和代价</strong>。"),
        H3("Q1 · <code>dict</code> 的查找真的是 $O(1)$ 吗？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你分得清<strong>期望 / 均摊 / 最坏</strong>三种复杂度口径，而不是背一个符号"],
            ["<strong>30 秒骨架</strong>", "「<em>期望</em> $O(1)$，<em>最坏</em> $O(n)$。最坏发生在所有 key 冲突到同一个桶——现实里两种触发方式：自定义 <code>__hash__</code> 写成常数，或者被构造的碰撞攻击（CPython 从 3.3 起默认开启哈希随机化 <code>PYTHONHASHSEED</code> 就是为了这个）。插入还有第三个口径：<em>均摊</em> $O(1)$——装载因子超过 2/3 会翻倍扩容并重建，单次是 $O(n)$，但等比级数求和后均摊是 $O(1)$。<strong>对延迟敏感的系统这个区别是实的</strong>：均摊 $O(1)$ 意味着某一帧会突然多花几毫秒，所以关键路径上要预分配。」"],
            ["加分点", "补一句「还有个容易忽略的：<strong>遍历 dict 是 $O(\\text{capacity})$ 不是 $O(n)$</strong>，大量删除后表很稀疏，遍历仍要扫全表——CPython 删除只打墓碑不缩容」"],
            ["<strong>踩雷点</strong>", "只说「$O(1)$」；或者说「最坏 $O(\\log n)$」（那是 Java 8+ 的 HashMap 树化，Python 没有）"],
        ]),
        H3("Q2 · 你怎么保证你的二分不会死循环？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你有<strong>可陈述的方法</strong>，而不是「我一般都对」"],
            ["<strong>30 秒骨架</strong>", "「三件事。<strong>①约定</strong>：我统一用半开区间 <code>[lo, hi)</code>，<code>hi</code> 是第一个被排除的位置，所以初始化 <code>hi = n</code>、循环条件 <code>lo &lt; hi</code>、更新只用 <code>lo = mid+1</code> 或 <code>hi = mid</code>。<strong>②不变量</strong>：<code>a[:lo]</code> 全 $&lt; t$、<code>a[hi:]</code> 全 $\\ge t$，退出时 <code>lo == hi</code> 就是分界点。<strong>③终止性</strong>：下取整让 <code>lo &lt;= mid &lt; hi</code>，两个分支都严格缩小区间长度，而区间长度是非负整数，所以至多 $\\lceil\\log_2 n\\rceil$ 轮必然退出。写完我会用『区间只剩 1–2 个元素』手推一遍。」"],
            ["加分点", "「另外我只背 <code>bisect_left</code> 一套模板，右边界、计数、精确查找全部由它推——<em>少一套模板就少一类 bug</em>。」再顺口提 <code>lo + (hi-lo)//2</code> 防溢出（JDK 的经典 bug）"],
            ["<strong>踩雷点</strong>", "答「多写几遍就熟了」；或者当场靠改 <code>+1/-1</code> 试出来"],
        ]),
        H3("Q3 · Top-K 用哪种解法？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你<strong>先问约束</strong>再选方法，并且知道渐进复杂度不等于实际耗时"],
            ["<strong>30 秒骨架</strong>", "「先问四个问题：$k$ 与 $n$ 的量级、数据能否一次进内存、要不要有序输出、能不能改原数组。<strong>$k \\ll n$ 且是流式 → 大小 $k$ 的最小堆</strong>，$O(n\\log k)$、空间只要 $O(k)$；<strong>$n$ 极大且能全放内存、不要顺序 → quickselect</strong>，期望 $O(n)$，但要随机主元，否则有序输入会退化成 $O(n^2)$；<strong>$k$ 接近 $n$ 或需要有序 → 直接全排序</strong>。补一个实测事实：$\\log_2 n/\\log_2 k$ 在 $n=10^6,k=100$ 时只有 3 倍，而 CPython 的 <code>sorted</code> 是 C 层 Timsort，常数小两个数量级，所以 $n$ 在 $10^5$ 量级时全排序往往<em>实际更快</em>。」"],
            ["加分点", "主动连到工程：「检测后处理里 NMS 前的 <code>top-1000</code> 截断就是这个——不是为了精度，是为了把 NMS 的最坏耗时钉死，代价是极密集场景可能截掉真目标。」"],
            ["<strong>踩雷点</strong>", "张口就「必须 quickselect 因为 $O(n)$」；说不出 quickselect 的最坏情况与随机主元"],
        ]),
        H3("Q4 · 排序的稳定性有什么用？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你能给出<strong>两个层次</strong>的答案：语法层（多关键字）和系统层（确定性）"],
            ["<strong>30 秒骨架</strong>", "「两个用途。<strong>①多关键字排序</strong>：主关键字要降序而次关键字是字符串时没法用元组取负，只能『先按次关键字排、再按主关键字排』，这一步完全依赖稳定性。<strong>②输出确定性</strong>——这个更重要：任何贪心算法的输出都依赖排序顺序，NMS 就是典型。两个 IoU 超阈值的框如果分数完全相同，先排到的那个会被保留、另一个被抑制，输出的框位置就不一样。而<em>分数并列一点都不罕见</em>：INT8 量化后分类头只有 256 个可能取值。更糟的是 <code>np.argsort</code> 默认不稳定、<code>torch.sort</code> 默认不保证、TensorRT 的 TopK 没有文档化保证——<strong>训练端和部署端的 tie-break 不一致，表现为『1000 帧里有 3 帧差一个框』，极难定位</strong>。」"],
            ["加分点", "给出根治方案：「与其依赖稳定性，不如让排序键成为<strong>全序</strong>——用 <code>(-score, class_id, x1, y1, index)</code>，任意两个元素的键都不相等，就不存在并列，是否稳定也就无所谓了。」"],
            ["<strong>踩雷点</strong>", "只答「保持相等元素的相对顺序」——这是定义不是用途"],
        ]),
        H3("Q5 · 你怎么识别一道题该「在答案上二分」？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你有<strong>可复用的识别信号</strong>，而不是「见过这题」"],
            ["<strong>30 秒骨架</strong>", "「三个信号同时出现就基本可以断定：<strong>①题面是『最小化最大值』『最大化最小值』或『至少需要多少』</strong>；<strong>②直接求最优难，但给定候选答案验证可行性容易</strong>（通常一遍 $O(n)$ 贪心）；<strong>③可行性单调</strong>——放宽约束不会让问题变难。满足了就把答案空间当成有序数组，套 <code>bisect_left</code> 模板，复杂度是 $O(\\text{check} \\cdot \\log(R-L))$。写之前我会先说清 $L$ 和 $R$ 的物理含义，比如 LC410 里 $L=\\max(a)$ 是硬下界、$R=\\sum a$ 是一定可行的上界。」"],
            ["加分点", "「而且这个模式在工程里到处都是：给定延迟预算求最大分辨率、给定召回下限求最高 score 阈值、给定带宽预算求触发阈值——<strong>都是同一个算法</strong>。」<em>把刷题模式映射到工程决策，是这道题最高分的答法。</em>"],
            ["<strong>踩雷点</strong>", "不验证单调性直接二分；浮点答案空间用 <code>while lo &lt; hi</code>（会死循环，要用固定 100 次迭代）"],
        ]),
        CALLOUT("intuition", "五道题的共同结构：<strong>先分清口径（期望/均摊/最坏、渐进/实际），"
                "再给机制，最后给一个具体数字或一个工程后果。</strong>"
                "<em>数字和后果是把「背过」和「用过」区分开的东西——把 2/3 装载因子、$\\log_2 n/\\log_2 k$、"
                "INT8 的 256 档、$\\lceil\\log_2 n\\rceil$ 轮这几个记住即可。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>学习型索引（learned index）。</strong> Kraska 等人 2018 年提出：既然 B 树本质是「把 key 映射到位置」的函数，"
            "那就用一个小模型直接拟合累积分布函数 CDF，预测位置后在局部做小范围二分。"
            "在只读、分布平滑的数据上比 B 树快数倍且省内存。"
            "<em>开放问题：更新（插入会破坏已学的 CDF）、对抗分布下的最坏保证、以及如何给出可证明的误差界——"
            "这正是「机器学习替代经典数据结构」这条线的核心难点。</em>",
            "<strong>最坏 $O(1)$ 的哈希。</strong> Cuckoo hashing 用两个哈希函数保证查找最坏 $O(1)$（代价是插入可能失败并重建）；"
            "Robin Hood hashing 通过均衡探测距离压低方差。<em>它们在数据库和 GPU 上被广泛使用，"
            "但在通用语言的默认 dict 里几乎没有——因为通用场景更在意平均性能与内存布局，"
            "这是「理论最优」和「工程默认」分道扬镳的典型案例。</em>",
            "<strong>GPU 上的排序与 select 是另一套算法学。</strong> CPU 上的 quickselect 依赖分支和随机访问，在 GPU 上都是反模式；"
            "GPU 的 top-K 用的是 <span class=\"term\">radix select</span>（按位分桶，无数据依赖分支）或 bitonic 网络。"
            "<em>这解释了为什么 TensorRT 的 <code>EfficientNMS</code> 不是「把 CPU NMS 搬到 GPU」而是重新设计的算法——"
            "以及为什么它的 tie-break 行为和 CPU 不一致（呼应第 2 节与 C60 的一致性对拍）。</em>",
            "<strong>浮点归约的不确定性。</strong> 浮点加法不满足结合律，所以并行归约的分块方式一变，结果的最后几位就变；"
            "cuDNN 的算法自动选择（<code>benchmark=True</code>）会让同一份权重两次前向的分数差 $10^{-7}$。"
            "<em>这个 $10^{-7}$ 本身无害，但它会让「并列分数」在两次运行中翻转顺序，"
            "从而让 NMS 输出不同的框——「确定性训练/推理」（deterministic mode）为此付出的性能代价是否值得，"
            "在量产系统里仍是有争议的工程决策。</em>",
            "<strong>亚线性算法与 sketch。</strong> 当数据大到连一遍都扫不完时，Count-Min Sketch、HyperLogLog、"
            "蓄水池采样这类算法用固定内存给出有界误差的近似统计。"
            "<em>大规模数据挖掘（C58-04）里统计「某个稀有类在几十 PB 回传里出现了多少次」用的就是这类工具；"
            "开放问题是如何给检测这种「结构化输出」设计合适的 sketch。</em>",
            "<strong>近似最近邻（ANN）是高维版的 Top-K。</strong> HNSW、IVF-PQ、ScaNN 把精确 top-K 的 $O(n)$ 换成亚线性，"
            "代价是召回不再是 100%。<em>嵌入检索式的难例挖掘（C58-04）完全建立在这个取舍上——"
            "「召回 95% 的近邻但快 100 倍」在挖掘场景里是划算的，但在评测场景里就不一定；"
            "如何为不同下游任务选择 recall-latency 工作点，仍然主要靠经验。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Cormen et al., <em>Introduction to Algorithms</em>（CLRS）第 9 章"
                "（Medians and Order Statistics：quickselect 的期望线性证明与 median-of-medians）与第 11 章"
                "（Hash Tables：全域哈希与完美哈希的严格分析）——<em>这两章是本模块所有复杂度陈述的出处，"
                "面试里要报「期望 / 均摊 / 最坏」的口径就必须读它</em>。"
                "<strong>★</strong> Tim Peters, <em>listsort.txt</em>（CPython 源码 <code>Objects/listsort.txt</code>）——"
                "Timsort 的设计说明，讲清了「自适应」与「稳定」是怎么同时做到的，一小时能读完，性价比极高。</p>"
                "<p>延伸：Bentley &amp; McIlroy, <em>Engineering a Sort Function</em>（1993）——"
                "工业级快排的主元选择与三路划分，quickselect 的工程细节都来自这里；"
                "Bloch, <em>Extra, Extra – Read All About It: Nearly All Binary Searches and Mergesorts are Broken</em>"
                "（2006，JDK 二分溢出 bug 的著名博文）；Kraska et al., <em>The Case for Learned Index Structures</em>"
                "（SIGMOD 2018）；Pagh &amp; Rodler, <em>Cuckoo Hashing</em>（2004）；"
                "Cormode &amp; Muthukrishnan, <em>Count-Min Sketch</em>（2005）；"
                "Malkov &amp; Yashunin, <em>HNSW</em>（TPAMI 2020，ANN 检索的事实标准）。"
                "相邻课程：模块 01（双指针与滑动窗口）、模块 03（树与图，并查集的复杂度分析）、"
                "模块 04（DP 与贪心，区间调度）、C53-04（NMS 的 WCET 与 top-K 截断）、"
                "C58-04（嵌入检索与去重）、C60（训练-部署一致性与浮点确定性）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · 哈希、排序与二分（三套二分模板 / 答案空间二分 / Top-K 三解法 / 排序确定性）

目标：把这三样东西从「大概会」变成「能在压力下一次写对，并说清为什么对」。

本 notebook 你会亲手实现：
1. **玩具哈希表**，把「最坏 O(n)」真的跑出来；再验证 Python dict 的三个坑（`hash(1)==hash(1.0)==hash(True)`、浮点 key、可哈希性）
2. **扩容的均摊分析**：单次 O(n)，均摊 O(1) —— 并看清它对延迟分布的影响
3. **排序稳定性**：分次排序实现多关键字；**同一批框、同样的分数，tie-break 不同 → NMS 输出不同框**
4. **三套二分模板** + 循环不变量断言 + 与 `bisect` 的 2000 组随机对拍 + 换算表
5. **把死循环跑出来**：区间长度停止下降的完整轨迹；以及求右边界为什么必须用上取整 mid
6. **在答案上二分**：LC410 与 O(n²m) DP 对拍；再用同一套模板解「给定召回下限求最高 score 阈值」
7. **Top-K 三解法**（全排序 / 堆 / quickselect）的对拍与计时，以及元素访问次数的线性性验证
8. **10 道经典题的暴力解 vs 最优解随机对拍**，每题标注频率与层级

> 心智模型：**二分的前提不是「数组有序」，是「存在一个可切分的单调谓词」；
> 而贪心算法的输出永远依赖排序顺序，所以排序键必须是全序。**"""),

    md("""## 1 · 哈希表：均摊 O(1) 的边界在哪

先用一个链地址法的玩具哈希表，把「哈希函数退化 ⇒ 查找变 O(n)」跑成数字。
用**探测次数**（确定性）而不是墙钟时间（有噪声）做断言依据。"""),

    code("""import sys, time, random, bisect, heapq
from collections import Counter, defaultdict
import numpy as np

print('Python', sys.version.split()[0], '| numpy', np.__version__)


class ToyHash:
    \"\"\"链地址法哈希表（教学模型；CPython 实际用开放寻址）。probes 累计探测次数。\"\"\"
    def __init__(self, cap=64, hashfn=hash):
        self.cap, self.hashfn = cap, hashfn
        self.buckets = [[] for _ in range(cap)]
        self.probes = 0

    def _idx(self, k):
        return self.hashfn(k) % self.cap

    def put(self, k, v):
        b = self.buckets[self._idx(k)]
        for i, (kk, _) in enumerate(b):
            self.probes += 1
            if kk == k:
                b[i] = (k, v); return
        b.append((k, v))

    def get(self, k):
        for kk, vv in self.buckets[self._idx(k)]:
            self.probes += 1
            if kk == k:
                return vv
        raise KeyError(k)


N = 64
good = ToyHash(cap=64)                          # 好哈希：key 均匀散到 64 个桶
bad  = ToyHash(cap=64, hashfn=lambda k: 0)      # 坏哈希：所有 key 撞进同一个桶
for i in range(N):
    good.put(i, i); bad.put(i, i)
good.probes = bad.probes = 0                    # 清零，只统计查找
for i in range(N):
    good.get(i); bad.get(i)

print(f'好哈希：{N} 次查找共探测 {good.probes:>5} 次  → 平均 {good.probes / N:6.2f}')
print(f'坏哈希：{N} 次查找共探测 {bad.probes:>5} 次  → 平均 {bad.probes / N:6.2f}')
assert good.probes == N                         # 每桶恰好 1 个元素
assert bad.probes == N * (N + 1) // 2           # 第 i 次查找扫 i+1 个 → 等差和
print('\\n✅ 「最坏 O(n)」不是理论玩具：哈希函数一退化，平均探测次数从 1 变成 (n+1)/2 =',
      (N + 1) / 2)"""),

    code("""# ── Python dict 的三个坑（面试里被追问「dict 有什么坑」时的标准答案）──

# 坑 1：hash(1) == hash(1.0) == hash(True)
assert hash(1) == hash(1.0) == hash(True)
d = {1: 'x', 1.0: 'y', True: 'z'}
print(\"{1:'x', 1.0:'y', True:'z'} =\", d, '  ← 三个 key 合并成了一个')
assert len(d) == 1 and d[1] == 'z' and d[True] == 'z'

# 坑 2：浮点数做 key
d2 = {0.3: 'ok'}
print('0.1 + 0.2 =', repr(0.1 + 0.2), ' → 用它查 d2 会 KeyError')
assert (0.1 + 0.2) not in d2

nan = float('nan')
d3 = {nan: 'reachable-by-identity'}
assert d3[nan] == 'reachable-by-identity'   # 同一个对象：dict 先比 is，短路成功
assert float('nan') not in d3               # 另一个 nan 对象：is 不成立、== 也不成立
print('nan 作 key：同一个对象查得到，另一个 nan 查不到 —— 因为 nan != nan')

# 坑 3：可哈希性是递归计算的
assert isinstance(hash((1, 2)), int)
for bad_key in ([1, 2], (1, [2]), {1: 2}):
    try:
        hash(bad_key)
        raise AssertionError('应该抛 TypeError：' + repr(bad_key))
    except TypeError:
        pass
print('✅ list / 含 list 的 tuple / dict 都不可哈希（哈希递归到每个元素）')

# 附：分桶评测绝不能用 round 后的浮点当 key —— 舍入方向随数值不规则翻转
print('\\nround(0.035, 2) =', round(0.035, 2), '  ← 向上')
print('round(0.045, 2) =', round(0.045, 2), '  ← 向下（两个相邻的中点值被舍进了同一个桶）')
print('round(2.675, 2) =', round(2.675, 2), '  ← 著名的「应该是 2.68」')
assert round(0.035, 2) == 0.04 and round(0.045, 2) == 0.04 and round(2.675, 2) == 2.67
ups   = [x / 200 for x in range(1, 40, 2) if abs(round(x / 200, 2) - (x / 200 + 0.005)) < 1e-12]
downs = [x / 200 for x in range(1, 40, 2) if abs(round(x / 200, 2) - (x / 200 - 0.005)) < 1e-12]
print('向上舍入的中点值：', ups[:5])
print('向下舍入的中点值：', downs[:5])
assert ups and downs, '两个方向都存在 ⇒ 舍入方向不可预测'
print('   ↑ 因为这些十进制中点值在二进制里根本不是中点，方向由二进制表示决定，不规则。')"""),

    code("""# ── 均摊分析：翻倍扩容的总重建代价是等比级数 ──
def rebuild_cost(n, load=2/3, start=8):
    \"\"\"模拟 CPython 的 dict 扩容：装载因子超过 load 就翻倍并重建全部条目。\"\"\"
    cap, size, total, events = start, 0, 0, []
    for _ in range(n):
        if size + 1 > load * cap:
            cap *= 2
            total += size                 # 一次重建 = 搬运当前全部元素
            events.append((size, cap))
        size += 1
    return total, total / n, events

for n in (10**3, 10**4, 10**5, 10**6):
    tot, amo, ev = rebuild_cost(n)
    print(f'n={n:>8}  扩容 {len(ev):>2} 次  总搬运 {tot:>9}  均摊每次插入 {amo:5.3f}')
    assert amo < 2.0, '均摊代价必须是 O(1) 的小常数'

_, _, ev = rebuild_cost(10**4)
print('\\n第 10^4 次插入前的扩容时刻（size → 新容量）：', ev[-4:])
print('✅ 单次扩容 O(n)，均摊 O(1)。')
print('   但注意：**均摊 O(1) 意味着某一次插入会突然很慢** ——')
print('   车端后处理这类每帧都要跑的关键路径上，要预分配容量，别让它在帧内扩容。')"""),

    md("""## 2 · 排序：稳定性的两个用途

第一个是语法层的（多关键字），第二个是系统层的（**输出确定性**）——后者才是面试的重点。"""),

    code("""# ── 用途一：分次排序实现「主关键字降序 + 次关键字升序」──
recs = [('bravo', 2), ('alpha', 1), ('carol', 2), ('alpha', 3), ('bravo', 1)]

two_pass = sorted(recs, key=lambda r: r[1])       # ② 先排次关键字
two_pass = sorted(two_pass, key=lambda r: r[0])   # ① 再排主关键字（稳定 ⇒ 次序被保留）
one_pass = sorted(recs, key=lambda r: (r[0], r[1]))
print('分次排序 =', two_pass)
print('元组 key =', one_pass)
assert two_pass == one_pass
print('✅ 「先排次关键字，再排主关键字」只有在排序稳定时才成立')
print('   （主关键字要降序、次关键字是字符串没法取负时，这是唯一的写法）')

# Timsort 的自适应性：几乎有序的输入远快于随机输入
n = 200_000
near_sorted = list(range(n)); random.Random(0).shuffle(near_sorted[:200])
shuffled = list(range(n)); random.Random(0).shuffle(shuffled)
t0 = time.perf_counter(); sorted(near_sorted); t_near = time.perf_counter() - t0
t0 = time.perf_counter(); sorted(shuffled);    t_rand = time.perf_counter() - t0
print(f'\\n几乎有序 {t_near*1000:7.2f} ms   完全乱序 {t_rand*1000:7.2f} ms   '
      f'比值 {t_rand/max(t_near,1e-9):.1f}x')
print('   ↑ Timsort 检测已有的升序 run 并直接归并 → 近乎 O(n)')"""),

    code("""# ── 用途二（重点）：NMS 的输出依赖排序的 tie-break ──
def iou_1_to_n(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0]); y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2]); y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    a0 = (box[2] - box[0]) * (box[3] - box[1])
    a1 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(a0 + a1 - inter, 1e-9)

def nms(boxes, order, iou_thr=0.5):
    \"\"\"贪心 NMS。order 是已排好序的下标序列 —— tie-break 由调用者决定。\"\"\"
    order, keep = list(order), []
    while order:
        i = order.pop(0); keep.append(i)
        if not order:
            break
        ious = iou_1_to_n(boxes[i], boxes[order])
        order = [j for j, u in zip(order, ious) if u <= iou_thr]
    return keep

# A、B 高度重叠且分数完全相同；C 在远处
BX = np.array([[100., 200., 140., 240.],      # A
               [103., 204., 143., 244.],      # B
               [600., 300., 660., 360.]])     # C
SC = np.array([0.90, 0.90, 0.75])
u_ab = float(iou_1_to_n(BX[0], BX[1:2])[0])
print(f'IoU(A,B) = 1332/1868 = {u_ab:.4f}  > 0.5 → A、B 必有一个被抑制')
assert abs(u_ab - 1332 / 1868) < 1e-12

keep_ab = nms(BX, [0, 1, 2])      # A 排在 B 前
keep_ba = nms(BX, [1, 0, 2])      # B 排在 A 前
print('排序 [A,B,C] → 保留下标', keep_ab, ' 框中心 x =', BX[keep_ab[0]][0])
print('排序 [B,A,C] → 保留下标', keep_ba, ' 框中心 x =', BX[keep_ba[0]][0])
assert keep_ab == [0, 2] and keep_ba == [1, 2] and keep_ab != keep_ba
print('\\n❗ 同一批框、同样的分数，只因 tie-break 不同，输出的框就差了 3 个像素。')
print('   分数并列一点都不罕见：INT8 量化后分类头只有 256 个可能取值（见 C60）。')"""),

    code("""# ── 修法：把排序键做成全序（total order），并列就不存在了 ──
def order_by(scores, boxes, tiebreak=True):
    n = len(scores)
    if tiebreak:   # (-分数, x1, y1, 原下标) —— 任意两个不同元素的键都不相等
        key = lambda i: (-float(scores[i]), float(boxes[i, 0]), float(boxes[i, 1]), i)
    else:          # 只有分数 → 存在并列 → 结果依赖实现
        key = lambda i: -float(scores[i])
    return sorted(range(n), key=key)

perm = [2, 1, 0]                                   # 同一批框，换个输入顺序
BXp, SCp = BX[perm], SC[perm]

for tb in (True, False):
    k1 = sorted(nms(BX, order_by(SC, BX, tb)))
    k2 = sorted(perm[j] for j in nms(BXp, order_by(SCp, BXp, tb)))
    tag = '全序键 ' if tb else '仅分数键'
    print(f'{tag}: 原顺序输入 → {k1} ；打乱输入 → {k2} ；一致？{k1 == k2}')

k1 = sorted(nms(BX, order_by(SC, BX, True)))
k2 = sorted(perm[j] for j in nms(BXp, order_by(SCp, BXp, True)))
assert k1 == k2 == [0, 2], (k1, k2)
print('\\n✅ 全序排序键 ⇒ 输出与输入顺序无关；此时「排序是否稳定」不再重要，因为不会出现并列。')"""),

    md("""## 3 · 三套二分模板与循环不变量

每个模板里都写了 `assert` 形式的**循环不变量**（教学用；生产代码里当然要关掉）。
不变量成立 + 区间长度严格递减 ⇒ 正确性与终止性都是被**证明**的，不是被测试的。"""),

    code("""def bs_exact(a, t):
    \"\"\"模板 A · 闭区间 [lo, hi]。不变量 I_A：若 t 存在于 a 中，其下标 ∈ [lo, hi]。\"\"\"
    lo, hi = 0, len(a) - 1
    while lo <= hi:                       # 闭区间非空
        mid = lo + (hi - lo) // 2         # 这样写而不是 (lo+hi)//2：C++/Java 里防溢出
        if a[mid] == t:
            return mid
        if a[mid] < t:
            lo = mid + 1                  # a[:mid+1] 全 < t → I_A 保持
        else:
            hi = mid - 1                  # a[mid:] 全 > t → I_A 保持
    return -1                             # 区间空 ⇒ 由 I_A，t 不存在


def bs_left(a, t, check_inv=True):
    \"\"\"模板 B · 半开区间 [lo, hi) = bisect_left。
       不变量 I_B：a[:lo] 全 < t  且  a[hi:] 全 >= t。\"\"\"
    lo, hi = 0, len(a)
    while lo < hi:
        if check_inv:
            assert all(x < t for x in a[:lo]) and all(x >= t for x in a[hi:]), 'I_B 破了'
        mid = lo + (hi - lo) // 2         # 下取整 ⇒ lo <= mid < hi
        if a[mid] < t:
            lo = mid + 1
        else:
            hi = mid                      # 注意是 mid，不是 mid-1
    return lo


def bs_right(a, t, check_inv=True):
    \"\"\"模板 C · 半开区间 [lo, hi) = bisect_right。
       不变量 I_C：a[:lo] 全 <= t  且  a[hi:] 全 > t。与模板 B 只差一个 `=`。\"\"\"
    lo, hi = 0, len(a)
    while lo < hi:
        if check_inv:
            assert all(x <= t for x in a[:lo]) and all(x > t for x in a[hi:]), 'I_C 破了'
        mid = lo + (hi - lo) // 2
        if a[mid] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo


demo = [1, 3, 3, 3, 7]
print('a =', demo)
print('bs_left (a,3) =', bs_left(demo, 3), '  （第一个 >= 3）')
print('bs_right(a,3) =', bs_right(demo, 3), '  （第一个 > 3）')
print('出现次数      =', bs_right(demo, 3) - bs_left(demo, 3))
assert (bs_left(demo, 3), bs_right(demo, 3)) == (1, 4)"""),

    code("""# ── 与 bisect 的 2000 组随机对拍，同时验证「换算表」──
rng_bs = random.Random(0)
for _ in range(2000):
    n = rng_bs.randint(0, 12)
    a = sorted(rng_bs.randint(0, 6) for _ in range(n))
    t = rng_bs.randint(-1, 7)

    assert bs_left(a, t)  == bisect.bisect_left(a, t),  (a, t)
    assert bs_right(a, t) == bisect.bisect_right(a, t), (a, t)

    i = bs_exact(a, t)
    assert (i == -1) == (t not in a), (a, t, i)
    if i != -1:
        assert a[i] == t

    # 换算表：只背 bs_left / bs_right，其余全部现推
    assert bs_right(a, t) - bs_left(a, t) == a.count(t)
    assert bs_right(a, t) - 1 == max([j for j, x in enumerate(a) if x <= t], default=-1)
    assert bs_left(a, t) - 1  == max([j for j, x in enumerate(a) if x < t],  default=-1)
    assert bs_right(a, t) == len(a) - len([x for x in a if x > t])

print('✅ 2000 组随机数组（含空数组、大量重复、目标不存在）：')
print('   三套模板与 bisect 完全一致，四条换算关系全部成立。')
print('   ⇒ 面试里只背 bs_left 一套，其余现推 —— 少一套模板就少一类 bug。')"""),

    md("""## 4 · 把死循环跑出来

区间长度是二分的**度量函数（variant）**。死循环的定义就是它不再严格递减。"""),

    code("""def bs_left_buggy(a, t, max_steps=64):
    \"\"\"错误示范：半开区间里把 lo = mid + 1 写成了 lo = mid。
       返回 (结果, 步数, 是否撞上步数上界)。\"\"\"
    lo, hi = 0, len(a)
    for step in range(1, max_steps + 1):
        if lo >= hi:
            return lo, step - 1, False
        mid = lo + (hi - lo) // 2
        if a[mid] < t:
            lo = mid                      # ← 少了 +1：更新没有「跨过 mid」
        else:
            hi = mid
    return None, max_steps, True          # 撞上界 = 真实场景下的死循环

arr = [1, 3, 5]
res, steps, looped = bs_left_buggy(arr, 5)
print(f'bs_left_buggy([1,3,5], 5) → 结果 {res}，步数 {steps}，卡死 {looped}')
assert looped is True and res is None
assert bs_left(arr, 5) == 2               # 正确实现 2 步就出来了

# 逐轮打印度量函数
print('\\n轮次   lo  hi  mid  a[mid]   更新         区间长度')
lo, hi = 0, len(arr)
for step in range(1, 7):
    if lo >= hi:
        break
    mid = lo + (hi - lo) // 2
    old_lo, old_hi = lo, hi
    if arr[mid] < 5:
        lo, act = mid, 'lo = mid  (错)'
    else:
        hi, act = mid, 'hi = mid  (对)'
    old = old_hi - old_lo
    flag = '' if hi - lo < old else '   ← 没有下降！'
    print(f'{step:^5}{old_lo:>4}{old_hi:>4}{mid:>5}{arr[mid]:>8}   {act:<14}{old} → {hi-lo}{flag}')
print('\\n✅ 根因：区间长度为 1 时下取整让 mid == lo，而 `lo = mid` 没有跨过 mid。')
print('   通用判据：**mid 落在哪一半，那一半的更新就必须跨过 mid**。')"""),

    code("""# ── 求右边界的唯一安全组合：上取整 mid + lo = mid ──
def bs_last_le(a, t):
    \"\"\"最后一个 <= t 的下标（不存在返回 -1）。闭区间 [lo, hi]，答案最终落在 lo。
       不变量：a[lo] <= t（lo = -1 是虚拟哨兵，视为恒成立）且 a[hi+1:] 全 > t。\"\"\"
    lo, hi = -1, len(a) - 1
    while lo < hi:
        mid = lo + (hi - lo + 1) // 2     # **上取整**：把 mid 顶到右半边
        if a[mid] <= t:
            lo = mid                      # 保留 mid；因为 mid > lo，区间仍然缩小
        else:
            hi = mid - 1
    return lo

a2 = [1, 3, 3, 3, 7]
for t in range(-1, 9):
    assert bs_last_le(a2, t) == bisect.bisect_right(a2, t) - 1, t
print('a2 =', a2)
print('t        :', list(range(-1, 9)))
print('last_le  :', [bs_last_le(a2, t) for t in range(-1, 9)])
print('✅ 上取整 mid 配 `lo = mid` 才不会死循环；下取整配 `lo = mid` 必死。')
print('   —— 这就是为什么本课建议：只用半开区间 + bs_left，右边界一律用换算表推。')"""),

    md("""## 5 · 在答案上二分：最小化最大值

三个识别信号：① 题面是「最小化最大值 / 至少需要多少」；② `check(x)` 好写（O(n) 贪心）；
③ **`check` 单调**。第三条必须先说出来，否则就是背题。"""),

    code("""def split_array_bs(a, m):
    \"\"\"LC410：把 a 分成 m 个连续子数组，最小化「各段和的最大值」。O(n log(sum a))。\"\"\"
    def parts(cap):
        # check：每段和不超过 cap 时，贪心地尽量多塞，最少需要几段
        cnt, cur = 1, 0
        for x in a:
            if cur + x <= cap:
                cur += x
            else:
                cnt += 1; cur = x
        return cnt

    lo, hi = max(a), sum(a)     # lo：任何一段至少要装得下最大元素；hi：全放一段一定可行
    while lo < hi:              # 不变量：答案 ∈ [lo, hi]
        mid = lo + (hi - lo) // 2
        if parts(mid) <= m:
            hi = mid            # mid 可行 ⇒ 答案 <= mid（保留 mid）
        else:
            lo = mid + 1        # mid 不可行 ⇒ 答案 > mid
    return lo


def split_array_dp(a, m):
    \"\"\"暴力对照：区间 DP，O(n²m)。dp[k][i] = 前 i 个元素分 k 段时，最大段和的最小值。\"\"\"
    n = len(a); INF = float('inf')
    pre = [0] * (n + 1)
    for i, x in enumerate(a):
        pre[i + 1] = pre[i] + x
    dp = [[INF] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0
    for k in range(1, m + 1):
        for i in range(k, n + 1):
            for j in range(k - 1, i):
                if dp[k - 1][j] < INF:
                    dp[k][i] = min(dp[k][i], max(dp[k - 1][j], pre[i] - pre[j]))
    return dp[m][n]


print('split_array([7,2,5,10,8], 2) =', split_array_bs([7, 2, 5, 10, 8], 2), '（期望 18）')
assert split_array_bs([7, 2, 5, 10, 8], 2) == 18

rng_sa = random.Random(7)
for _ in range(200):
    n = rng_sa.randint(1, 7)
    a = [rng_sa.randint(0, 12) for _ in range(n)]
    m = rng_sa.randint(1, n)
    assert split_array_bs(a, m) == split_array_dp(a, m), (a, m)
print('✅ 200 组随机数据：答案空间二分与 O(n²m) DP 完全一致')
print('   单调性论证：cap 越大 → 需要的段数单调不增 → parts(cap) <= m 是单调谓词。')"""),

    code("""# ── 同一套模板的工程同构：给定召回下限，求最高可用的 score 阈值 ──
# （这正是 C55-05 的「工作点选择」；在代码上它就是一次答案空间二分）
rng_np = np.random.default_rng(0)
scores_tp = rng_np.beta(5, 2, size=400)          # 400 个真实目标各自的检出分数

def recall_at(thr):
    return float((scores_tp >= thr).mean())      # thr 越大 → 召回越低（单调不增）

TARGET = 0.95
lo_f, hi_f = 0.0, 1.0                            # 不变量：lo 可行、hi 不可行
for _ in range(100):                             # 浮点二分：**固定迭代次数**，绝不 while
    mid = (lo_f + hi_f) / 2
    if recall_at(mid) >= TARGET:
        lo_f = mid
    else:
        hi_f = mid

print(f'满足 recall >= {TARGET} 的最高阈值 ≈ {lo_f:.6f}')
print(f'  该阈值处 recall = {recall_at(lo_f):.4f}；再抬一点点 recall = {recall_at(hi_f):.4f}')
assert recall_at(lo_f) >= TARGET and recall_at(hi_f) < TARGET
print(f'区间已缩到 {hi_f - lo_f:.3e}（100 次迭代 ≈ 2^-100），远超 double 精度')
print('\\n✅ 浮点答案空间不要用 `while lo < hi`（浮点相等几乎永不成立 → 死循环），')
print('   用固定 100 次迭代：既够精确，又绝对不会卡住。')"""),

    md("""## 6 · Top-K 的三种解法：对拍 + 计时

重点不是「哪个快」，而是**渐进复杂度 ≠ 实际耗时**，以及三种解法各自买到了什么。"""),

    code("""def topk_sort(a, k):
    \"\"\"① 全排序 O(n log n)，空间 O(n)，输出天然有序。\"\"\"
    return sorted(a, reverse=True)[:k]


def topk_heap(a, k):
    \"\"\"② 大小为 k 的最小堆：堆顶就是「当前第 k 大」，比它小的直接丢。
       O(n log k)，空间 O(k)，**只遍历一次 ⇒ 流式可用**。\"\"\"
    h = []
    for x in a:
        if len(h) < k:
            heapq.heappush(h, x)
        elif x > h[0]:
            heapq.heapreplace(h, x)      # 弹出最小、压入 x，一次堆调整
    return sorted(h, reverse=True)


_QS_VISITS = 0

def quickselect_kth(a, k, rnd):
    \"\"\"③ 返回第 k 小（k 从 0 开始）的值。随机主元 + 三路划分，期望 O(n)。
       划分不变量：[lo,i) < p，[i,t) == p，(j,hi] > p；答案下标 k 始终落在 [lo,hi]。\"\"\"
    global _QS_VISITS
    a = list(a)                          # 不修改调用方的数据
    lo, hi = 0, len(a) - 1
    while True:
        p = a[rnd.randint(lo, hi)]       # 随机主元：否则有序输入会退化成 O(n²)
        i, j, t = lo, hi, lo
        while t <= j:                    # 荷兰国旗三路划分
            _QS_VISITS += 1
            if a[t] < p:
                a[i], a[t] = a[t], a[i]; i += 1; t += 1
            elif a[t] > p:
                a[t], a[j] = a[j], a[t]; j -= 1
            else:
                t += 1
        if k < i:
            hi = i - 1                   # 答案在左段
        elif k > j:
            lo = j + 1                   # 答案在右段
        else:
            return p                     # 落在「等于主元」的那段


def topk_quickselect(a, k, rnd):
    if k <= 0:
        return []
    v = quickselect_kth(a, len(a) - k, rnd)      # 第 k 大 = 第 (n-k) 小
    out = [x for x in a if x > v]
    out += [v] * (k - len(out))                  # 用主元值补齐（处理重复元素）
    return sorted(out, reverse=True)


rnd_tk = random.Random(1)
for _ in range(300):
    n = rnd_tk.randint(1, 40)
    a = [rnd_tk.randint(0, 15) for _ in range(n)]     # 大量重复，专门考验三路划分
    k = rnd_tk.randint(1, n)
    r1, r2, r3 = topk_sort(a, k), topk_heap(a, k), topk_quickselect(a, k, rnd_tk)
    assert r1 == r2 == r3, (a, k, r1, r2, r3)
print('✅ 300 组随机对拍（含大量重复元素）：三种解法输出完全一致')"""),

    code("""# ── 计时与「元素访问次数」──
N_BIG, K = 100_000, 100
big = [rnd_tk.randrange(10**9) for _ in range(N_BIG)]

timings, results = {}, {}
for name, fn in [('① sorted   ', lambda: topk_sort(big, K)),
                 ('② heap(k)  ', lambda: topk_heap(big, K)),
                 ('③ quickselect', lambda: topk_quickselect(big, K, rnd_tk))]:
    t0 = time.perf_counter(); out = fn(); dt = time.perf_counter() - t0
    timings[name.strip()], results[name.strip()] = dt, out
    print(f'{name}  {dt*1000:8.2f} ms   top3 = {out[:3]}')
assert len({tuple(v) for v in results.values()}) == 1, '三者结果必须一致'

_QS_VISITS = 0
topk_quickselect(big, K, rnd_tk)
print(f'\\nquickselect 的元素访问次数 = {_QS_VISITS:,}  ≈ {_QS_VISITS/N_BIG:.2f}·n  ← 线性')
assert _QS_VISITS < 12 * N_BIG, '随机主元下期望约 2n~4n；12n 是很宽松的上界'

print(f'\\n理论比值 log2(n)/log2(k) = {np.log2(N_BIG)/np.log2(K):.2f}x  '
      f'（堆相对全排序的渐进优势）')
print('观察：③ 渐进上是 O(n) 最优，但 ① 走的是 C 层 Timsort，常数小一到两个数量级。')
print('结论：**复杂度是常数未知的上界**。面试里要同时说得出「渐进最优」和「实测更快」，')
print('      并且知道 ② 的真正卖点是 O(k) 空间 + 单遍流式，而不是那个 log 因子。')"""),

    md("""## 7 · 经典题单：暴力解 vs 最优解随机对拍

每题标注**频率**与**层级**。所有实现控制在 15–40 行、变量名清晰、注明不变量。"""),

    code("""def duel(name, fast, brute, gen, trials=400):
    for _ in range(trials):
        args = gen()
        f, b = fast(*args), brute(*args)
        assert f == b, (name, args, f, b)
    print(f'  ✅ {name:<34} {trials} 轮随机对拍一致')


# ── 哈希类 ──
def two_sum_hash(a, t):
    \"\"\"[高频/必会] 边扫边把「值 → 首次出现的下标」存进 dict。O(n)。\"\"\"
    seen = {}
    for j, x in enumerate(a):
        if t - x in seen:
            return (seen[t - x], j)
        if x not in seen:               # 只记首次出现，与暴力解的 tie-break 对齐
            seen[x] = j
    return None

def two_sum_brute(a, t):
    for j in range(len(a)):
        for i in range(j):
            if a[i] + a[j] == t:
                return (i, j)
    return None


def longest_consec_hash(a):
    \"\"\"[中频/必会] 只从「x-1 不在集合里」的序列起点开始向右数 ⇒ 每个元素至多被访问 2 次，总 O(n)。\"\"\"
    s, best = set(a), 0
    for x in s:
        if x - 1 in s:
            continue                    # 不是起点，跳过 —— 这一行是 O(n) 的关键
        y = x
        while y + 1 in s:
            y += 1
        best = max(best, y - x + 1)
    return best

def longest_consec_brute(a):
    if not a:
        return 0
    b = sorted(set(a)); best = cur = 1
    for i in range(1, len(b)):
        cur = cur + 1 if b[i] == b[i - 1] + 1 else 1
        best = max(best, cur)
    return best


def topk_freq_bucket(a, k):
    \"\"\"[高频/必会] 桶排序版：频次上界是 n ⇒ 可以 O(n) 完成，把 log 因子消掉。\"\"\"
    c = Counter(a)
    buckets = [[] for _ in range(len(a) + 1)]
    for v, cnt in c.items():
        buckets[cnt].append(v)
    out = []
    for cnt in range(len(a), 0, -1):
        for v in sorted(buckets[cnt]):  # 桶内排序 ⇒ 并列时的顺序也是确定的
            out.append(v)
            if len(out) == k:
                return out
    return out

def topk_freq_brute(a, k):
    c = Counter(a)
    return [v for v, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))][:k]


def group_anagrams(words):
    \"\"\"[中频/必会] 排序后的字符元组做 key。O(Σ L log L)。\"\"\"
    g = defaultdict(list)
    for w in words:
        g[tuple(sorted(w))].append(w)
    return sorted(sorted(v) for v in g.values())

def group_anagrams_brute(words):
    groups = []
    for w in words:
        for gr in groups:
            if sorted(gr[0]) == sorted(w):
                gr.append(w); break
        else:
            groups.append([w])
    return sorted(sorted(gr) for gr in groups)


rnd_q = random.Random(42)
print('哈希类：')
duel('两数之和 [高频/必会]', two_sum_hash, two_sum_brute,
     lambda: ([rnd_q.randint(-6, 6) for _ in range(rnd_q.randint(0, 9))], rnd_q.randint(-8, 8)))
duel('最长连续序列 [中频/必会]', longest_consec_hash, longest_consec_brute,
     lambda: ([rnd_q.randint(0, 12) for _ in range(rnd_q.randint(0, 12))],))
duel('前 K 高频元素 [高频/必会]', topk_freq_bucket, topk_freq_brute,
     lambda: ([rnd_q.randint(0, 5) for _ in range(rnd_q.randint(1, 12))], rnd_q.randint(1, 4)))
duel('字母异位词分组 [中频/必会]', group_anagrams, group_anagrams_brute,
     lambda: ([''.join(rnd_q.choice('abc') for _ in range(rnd_q.randint(1, 3)))
               for _ in range(rnd_q.randint(0, 8))],))"""),

    code("""# ── 二分 / 排序类 ──
def search_rotated(a, t):
    \"\"\"[高频/必会] 旋转有序数组（元素互不相同）。
       不变量：任何时刻 [lo, mid] 与 [mid, hi] 中至少有一半是有序的。\"\"\"
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if a[mid] == t:
            return mid
        if a[lo] <= a[mid]:                     # 左半 [lo, mid] 有序
            if a[lo] <= t < a[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                                   # 右半 [mid, hi] 有序
            if a[mid] < t <= a[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1

def rotated_brute(a, t):
    return a.index(t) if t in a else -1

def gen_rotated():
    n = rnd_q.randint(1, 10)
    base = sorted(rnd_q.sample(range(30), n))
    k = rnd_q.randrange(n)
    return (base[k:] + base[:k], rnd_q.randint(0, 29))


def find_range(a, t):
    \"\"\"[高频/必会] 元素的首末位置：bs_left 与 bs_right - 1。\"\"\"
    l = bs_left(a, t)
    if l == len(a) or a[l] != t:
        return (-1, -1)
    return (l, bs_right(a, t) - 1)

def find_range_brute(a, t):
    idx = [i for i, x in enumerate(a) if x == t]
    return (idx[0], idx[-1]) if idx else (-1, -1)


def find_peak(a):
    \"\"\"[中频/加分] 山脉数组的峰顶。**数组无序，但谓词 a[mid] < a[mid+1] 单调可用** ——
       这道题是「二分的前提是单调谓词而非有序」的最好证据。\"\"\"
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = lo + (hi - lo) // 2       # lo < hi ⇒ mid < hi ⇒ mid+1 合法
        if a[mid] < a[mid + 1]:
            lo = mid + 1                # 峰一定在右边
        else:
            hi = mid                    # 峰是 mid 或更左
    return lo

def peak_brute(a):
    return max(range(len(a)), key=lambda i: a[i])

def gen_mountain():
    up, down = rnd_q.randint(1, 5), rnd_q.randint(1, 5)
    return (list(range(up)) + [up] + list(range(up - 1, up - 1 - down, -1)),)


def h_index(cit):
    \"\"\"[中频/加分] 降序排后找最大的 i 使 c[i-1] >= i。\"\"\"
    c = sorted(cit, reverse=True); h = 0
    for i, x in enumerate(c, 1):
        if x >= i:
            h = i
        else:
            break                       # c 递减、i 递增 ⇒ 一旦失败就不会再成立
    return h

def h_index_brute(cit):
    return max(h for h in range(len(cit) + 1) if sum(1 for x in cit if x >= h) >= h)


def sort_colors(a):
    \"\"\"[中频/加分] 荷兰国旗三路划分 —— 和 quickselect 里的划分是同一段代码。
       不变量：[0,i) == 0，[i,t) == 1，(j,n) == 2。\"\"\"
    a = list(a); i, j, t = 0, len(a) - 1, 0
    while t <= j:
        if a[t] == 0:
            a[i], a[t] = a[t], a[i]; i += 1; t += 1
        elif a[t] == 2:
            a[t], a[j] = a[j], a[t]; j -= 1     # 换来的元素还没检查，t 不动
        else:
            t += 1
    return a


print('二分 / 排序类：')
duel('搜索旋转排序数组 [高频/必会]', search_rotated, rotated_brute, gen_rotated)
duel('查找元素首末位置 [高频/必会]', find_range, find_range_brute,
     lambda: (sorted(rnd_q.randint(0, 6) for _ in range(rnd_q.randint(0, 10))),
              rnd_q.randint(-1, 7)))
duel('寻找峰值（山脉数组）[中频/加分]', find_peak, peak_brute, gen_mountain)
duel('H 指数 [中频/加分]', h_index, h_index_brute,
     lambda: ([rnd_q.randint(0, 8) for _ in range(rnd_q.randint(1, 8))],))
duel('颜色分类（荷兰国旗）[中频/加分]', sort_colors, sorted,
     lambda: ([rnd_q.randint(0, 2) for _ in range(rnd_q.randint(0, 12))],))
print('\\n✅ 10 道题全部通过暴力解对拍（含第 5、6 节的 LC410 与 Top-K）。')"""),

    md("""## ✏️ 练习 1：只背一套模板，其余全部现推

实现四个函数（**不许调用 `bisect`**）：
- `my_bs_left(a, t)` → 第一个 `>= t` 的下标（等价 `bisect_left`）。半开区间 `[lo, hi)`，
  不变量：`a[:lo]` 全 `< t` 且 `a[hi:]` 全 `>= t`
- `my_bs_right(a, t)` → 第一个 `> t` 的下标（等价 `bisect_right`）。与上面**只差一个 `=`**
- `count_equal(a, t)` → `t` 的出现次数。**只能用上面两个函数**（不许 `count` / 循环）
- `last_le(a, t)` → 最后一个 `<= t` 的下标，不存在返回 `-1`。**只能用上面两个函数**"""),

    code("""def my_bs_left(a, t):
    # TODO: 半开区间 [lo, hi)，lo=0, hi=len(a)
    #       a[mid] < t  -> lo = mid + 1  （必须 +1，否则死循环）
    #       否则         -> hi = mid
    raise NotImplementedError

def my_bs_right(a, t):
    # TODO: 与 my_bs_left 只差把 `a[mid] < t` 换成 `a[mid] <= t`
    raise NotImplementedError

def count_equal(a, t):
    # TODO: 用换算表
    raise NotImplementedError

def last_le(a, t):
    # TODO: 用换算表
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
_r1 = random.Random(3)
for _ in range(3000):
    n = _r1.randint(0, 10)
    a = sorted(_r1.randint(0, 5) for _ in range(n))
    t = _r1.randint(-1, 6)
    assert my_bs_left(a, t)  == bisect.bisect_left(a, t),  ('left', a, t)
    assert my_bs_right(a, t) == bisect.bisect_right(a, t), ('right', a, t)
    assert count_equal(a, t) == a.count(t), ('count', a, t)
    assert last_le(a, t) == max([i for i, x in enumerate(a) if x <= t], default=-1), ('le', a, t)
# 空数组与全相同数组这两个边界必须单独点名
assert my_bs_left([], 5) == 0 and my_bs_right([], 5) == 0 and last_le([], 5) == -1
assert my_bs_left([2, 2, 2], 2) == 0 and my_bs_right([2, 2, 2], 2) == 3
assert count_equal([2, 2, 2], 2) == 3 and last_le([2, 2, 2], 2) == 2
print('✅ 练习 1 通过：3000 组随机对拍 + 空/全相同边界，四个函数与标准库完全一致。')
print('   记住这条：面试里只背 bs_left，右边界 / 计数 / 精确查找全部由它现推。')"""),

    md("""## ✏️ 练习 2：在答案上二分

实现 `min_ship_capacity(weights, days)`（LeetCode 1011）：
包裹必须**按给定顺序**在 `days` 天内运完，每天装的包裹重量和不超过船的运载能力，求**最小运载能力**。

步骤：
1. 写 `need(cap)`：贪心地按顺序装，装不下就开新的一天，返回需要几天
2. `lo = max(weights)`（一天至少要装得下最重的那个包裹），`hi = sum(weights)`（一天全装完一定可行）
3. 套模板 B：`need(mid) <= days` → `hi = mid`，否则 `lo = mid + 1`

**先在心里说清楚：为什么 `need(cap) <= days` 是关于 `cap` 单调的？**"""),

    code("""def min_ship_capacity(weights, days):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
assert min_ship_capacity([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == 15
assert min_ship_capacity([3, 2, 2, 4, 1, 4], 3) == 6
assert min_ship_capacity([1, 2, 3, 1, 1], 4) == 3
assert min_ship_capacity([7], 1) == 7

def _brute_capacity(w, d):
    \"\"\"暴力对照：从 max(w) 开始线性往上试第一个可行的 cap。\"\"\"
    def need(cap):
        cnt, cur = 1, 0
        for x in w:
            if cur + x <= cap:
                cur += x
            else:
                cnt += 1; cur = x
        return cnt
    cap = max(w)
    while need(cap) > d:
        cap += 1
    return cap

_r2 = random.Random(11)
for _ in range(300):
    n = _r2.randint(1, 9)
    w = [_r2.randint(1, 9) for _ in range(n)]
    d = _r2.randint(1, n)
    assert min_ship_capacity(w, d) == _brute_capacity(w, d), (w, d)
# 单调性自检：可行性一旦为真，就不会再变回假
_w, _d = [3, 2, 2, 4, 1, 4], 3
_ans = min_ship_capacity(_w, _d)
_feas = [_brute_capacity(_w, _d) <= c for c in range(max(_w), sum(_w) + 1)]
assert _feas == sorted(_feas), 'check 必须单调，否则不能二分'
print(f'✅ 练习 2 通过：300 组随机数据与线性扫描一致；最小运载能力 = {_ans}')
print('   同一套模板还能解：爱吃香蕉的珂珂、制作 m 束花、分割数组的最大值、')
print('   以及工程里的「给定延迟预算求最大分辨率」「给定召回下限求最高阈值」。')"""),

    md("""## ✏️ 练习 3：quickselect

实现 `my_quickselect(a, k, rnd)` 返回列表 `a` 中**第 k 小**的值（`k` 从 0 开始）。要求：
- **随机主元**（用 `rnd.randint(lo, hi)`）—— 否则有序输入会退化成 O(n²)
- **三路划分**（荷兰国旗）—— 否则大量重复元素时也会退化
- **不修改传入的 `a`**（内部先 `list(a)` 复制）
- 不许调用 `sorted` / `heapq` / `min` / `max`"""),

    code("""def my_quickselect(a, k, rnd):
    # TODO：
    #   a = list(a); lo, hi = 0, len(a)-1
    #   循环：p = a[rnd.randint(lo, hi)]
    #        三路划分成 [lo,i) < p，[i,j] == p，(j,hi] > p
    #        k < i  -> hi = i-1 ；k > j -> lo = j+1 ；否则 return p
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
_r3 = random.Random(5)
assert my_quickselect([3, 1, 2], 0, _r3) == 1
assert my_quickselect([3, 1, 2], 2, _r3) == 3
assert my_quickselect([5, 5, 5, 5], 2, _r3) == 5       # 全相同：三路划分的关键用例
assert my_quickselect([9], 0, _r3) == 9                 # 单元素

_src = [7, 7, 1, 9, 3, 3, 3, 8]
for _k in range(len(_src)):
    assert my_quickselect(_src, _k, _r3) == sorted(_src)[_k], _k
assert _src == [7, 7, 1, 9, 3, 3, 3, 8], '不许修改调用方传入的列表'

for _ in range(300):
    n = _r3.randint(1, 25)
    a = [_r3.randint(0, 8) for _ in range(n)]           # 大量重复
    k = _r3.randrange(n)
    assert my_quickselect(a, k, _r3) == sorted(a)[k], (a, k)

# 有序输入也必须是线性的（随机主元的意义）
_sorted_in = list(range(4000))
_t0 = time.perf_counter()
assert my_quickselect(_sorted_in, 2000, _r3) == 2000
_dt = time.perf_counter() - _t0
print(f'✅ 练习 3 通过：300 组随机数据 + 全相同 + 单元素；'
      f'4000 个已排序元素上取中位数只用了 {_dt*1000:.1f} ms（未退化）')"""),

    md("""## ✏️ 练习 4：让 NMS 的输入成为确定性的

实现 `nms_order(scores, boxes)`：返回下标的排序结果，满足
- 主序：**分数降序**
- 并列时用 `(x1, y1, 原始下标)` 依次 tie-break —— 保证键是**全序**（任意两个不同元素的键都不相等）

这样一来，「排序是否稳定」就不再重要，因为根本不会出现并列。"""),

    code("""def nms_order(scores, boxes):
    # TODO: return sorted(range(n), key=lambda i: (...))
    #       注意把 numpy 标量转成 float / int，避免比较时的类型意外
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测（手算）——
_sc = np.array([0.9, 0.9, 0.7, 0.9])
_bx = np.array([[10., 10., 20., 20.],     # 0
                [ 5., 30., 15., 40.],     # 1
                [50., 50., 60., 60.],     # 2
                [10.,  5., 20., 15.]])    # 3
_o = nms_order(_sc, _bx)
assert [round(float(_sc[i]), 3) for i in _o] == [0.9, 0.9, 0.9, 0.7], _o
# 并列的 0/1/3 按 (x1, y1) 升序：(5,30) < (10,5) < (10,10)
assert _o == [1, 3, 0, 2], _o

# 换个输入顺序，排序后的「框序列」必须逐字节一致
_perm = [2, 0, 3, 1]
_o2 = nms_order(_sc[_perm], _bx[_perm])
assert np.array_equal(_bx[_perm][_o2], _bx[_o]), '全序键 ⇒ 输出与输入顺序无关'

# 接上第 2 节的 NMS：全序键下，打乱输入不改变保留的框
_k1 = sorted(nms(BX, nms_order(SC, BX)))
_k2 = sorted([2, 1, 0][j] for j in nms(BX[[2, 1, 0]], nms_order(SC[[2, 1, 0]], BX[[2, 1, 0]])))
assert _k1 == _k2 == [0, 2], (_k1, _k2)
print('✅ 练习 4 通过：全序排序键让整条 NMS 流水线成为确定性函数。')
print('   面试里被问「你的代码是确定性的吗」，这就是标准答案。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def my_bs_left(a, t):
    lo, hi = 0, len(a)                    # 不变量：a[:lo] < t <= a[hi:]
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if a[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo

def my_bs_right(a, t):
    lo, hi = 0, len(a)                    # 不变量：a[:lo] <= t < a[hi:]
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if a[mid] <= t:                   # ← 唯一的差别
            lo = mid + 1
        else:
            hi = mid
    return lo

def count_equal(a, t):
    return my_bs_right(a, t) - my_bs_left(a, t)

def last_le(a, t):
    return my_bs_right(a, t) - 1"""),

    code("""# 练习 2 参考答案
def min_ship_capacity(weights, days):
    def need(cap):
        # 贪心：能装就装。可以证明这是最优的（提前开新的一天不会更好）
        cnt, cur = 1, 0
        for x in weights:
            if cur + x <= cap:
                cur += x
            else:
                cnt += 1; cur = x
        return cnt

    # 单调性：cap 增大 ⇒ 每天能装的不减 ⇒ need(cap) 单调不增 ⇒ need(cap) <= days 单调
    lo, hi = max(weights), sum(weights)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if need(mid) <= days:
            hi = mid
        else:
            lo = mid + 1
    return lo"""),

    code("""# 练习 3 参考答案
def my_quickselect(a, k, rnd):
    a = list(a)                                  # 不动调用方的数据
    lo, hi = 0, len(a) - 1
    while True:
        p = a[rnd.randint(lo, hi)]               # 随机主元
        i, j, t = lo, hi, lo
        # 划分不变量：[lo,i) < p，[i,t) == p，(j,hi] > p，[t,j] 未检查
        while t <= j:
            if a[t] < p:
                a[i], a[t] = a[t], a[i]; i += 1; t += 1
            elif a[t] > p:
                a[t], a[j] = a[j], a[t]; j -= 1  # 换来的元素还没检查，t 不动
            else:
                t += 1
        if k < i:
            hi = i - 1
        elif k > j:
            lo = j + 1
        else:
            return p                             # 落在等于主元的段内，直接出答案"""),

    code("""# 练习 4 参考答案
def nms_order(scores, boxes):
    n = len(scores)
    return sorted(range(n), key=lambda i: (-float(scores[i]),
                                           float(boxes[i, 0]),
                                           float(boxes[i, 1]),
                                           i))"""),

    md("""---
## 🧪 真实工程胶囊：哈希 / 排序 / 二分的速查卡"""),

    code("""RECIPE = r'''
# ======================================================================
# 面试与生产两用速查卡 · 哈希 / 排序 / 二分            （C62 模块 02）
# ======================================================================

# ---------- 1. 只背这一套二分，其余全部现推 ----------
def bisect_left_(a, t):
    lo, hi = 0, len(a)              # 半开区间 [lo, hi)，hi = 第一个被排除的位置
    while lo < hi:                  # 不变量：a[:lo] < t <= a[hi:]
        mid = lo + (hi - lo) // 2   # 下取整 => lo <= mid < hi => 两支都严格缩区间
        if a[mid] < t: lo = mid + 1 # 必须 +1，否则度量函数不递减 -> 死循环
        else:          hi = mid
    return lo                       # 终止：至多 ceil(log2 n) 轮

# 换算表（不要再背第二套模板）
#   bisect_right = 把上面的 `<` 换成 `<=`
#   出现次数      = bisect_right - bisect_left
#   最后一个 <= t = bisect_right - 1
#   最后一个 <  t = bisect_left  - 1
#   精确查找      = i = bisect_left(a,t);  a[i] == t ? i : -1
# 求右边界若非要写成 lo = mid，则 mid 必须上取整：mid = lo + (hi-lo+1)//2

# ---------- 2. 在答案上二分（最小化最大值 / 最大化最小值） ----------
# 三个识别信号：(1) 题面是"最小化最大值 / 至少需要多少"
#               (2) check(x) 好写（通常一遍 O(n) 贪心）
#               (3) check 单调（x 可行 => x+1 可行）   <-- 必须先说出这一句
def min_feasible(lo, hi, check):                     # 整数答案空间
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if check(mid): hi = mid
        else:          lo = mid + 1
    return lo

def min_feasible_float(lo, hi, check, iters=100):    # 浮点：固定次数，绝不用 while
    for _ in range(iters):
        mid = (lo + hi) / 2
        if check(mid): hi = mid
        else:          lo = mid
    return hi

# 工程同构（同一个算法，换个名字）：
#   给定延迟预算 -> 最大输入分辨率      check(r) = latency(r) <= budget
#   给定召回下限 -> 最高 score 阈值      check(th) = recall(th) >= 0.95
#   切片推理     -> 最小安全重叠率       check(ov) = 任意目标完整落入某片
#   带宽预算     -> 难例回传触发阈值     check(th) = 触发量 <= 预算
# 陷阱：单调性没验证就二分。延迟对分辨率并非严格单调（kernel 选择会有反常点），
#      先扫粗网格确认单调，再在单调段内二分。

# ---------- 3. 确定性 NMS：把排序键做成全序 ----------
# 症状：一致性对拍时 1000 帧里有几帧"差一个框"，位置差几像素，分数完全相同。
# 根因：分数并列（INT8 量化后分类头只有 256 档）+ tie-break 在各实现间不一致：
#       np.argsort 默认 quicksort 不稳定 / torch.sort 默认不保证 /
#       TensorRT TopK 无文档化保证（GPU 归约顺序决定）。
def stable_order(scores, boxes, class_ids):
    n = len(scores)
    return sorted(range(n), key=lambda i: (-float(scores[i]),
                                           int(class_ids[i]),
                                           float(boxes[i][0]), float(boxes[i][1]), i))
# 有了全序键，"排序是否稳定"就不再重要 —— 因为根本不会出现并列。
# 同样的道理适用于任何贪心：区间调度、并查集聚类、匈牙利匹配的候选枚举。

# ---------- 4. 分桶评测：绝不用浮点当 dict 的 key ----------
import bisect as _bs
EDGES  = [0, 16, 32, 64, 128, 256]           # sqrt(面积) 的桶边界，左闭右开
LABELS = ['<16', '16-32', '32-64', '64-128', '128-256', '>=256']
def bucket_of(v):
    return min(max(_bs.bisect_right(EDGES, v) - 1, 0), len(LABELS) - 1)
# 反例：buckets[round(iou, 2)] += 1
#   round(0.035,2)=0.04 向上，round(0.045,2)=0.04 向下 —— 方向由二进制表示决定，
#   两台机器上差 1e-16 的 IoU 就可能落进不同的桶，评测报告对不上。

# ---------- 5. Top-K 选型（先问四个问题） ----------
#   k 与 n 的量级？ 数据能一次进内存？ 要有序输出？ 能改原数组？
#   k << n 且流式     -> heapq.nlargest / 大小 k 的最小堆   O(n log k)  空间 O(k)
#   n 极大、不要顺序  -> quickselect（**随机主元 + 三路划分**）O(n) 期望
#   k 接近 n 或要有序 -> sorted                              O(n log n)
#   实测提醒：CPython 的 sorted 是 C 层 Timsort，n ~ 1e5 时常比手写 quickselect 更快。
#   检测后处理的 nms_pre = top-1000：不是为精度，是把 NMS 的最坏耗时钉死（见 C53-04）。

# ---------- 6. 交卷前 30 秒自检 ----------
#   [ ] 二分：说出用的是闭区间还是半开区间；用"区间只剩 1-2 个元素"手推一遍
#   [ ] 二分：mid 写成 lo + (hi-lo)//2（C++/Java 防溢出，JDK 曾为此挂了九年）
#   [ ] 答案二分：显式说明 check 为什么单调、lo/hi 各自的物理含义
#   [ ] 哈希：报复杂度时说清"查找期望 O(1) / 最坏 O(n) / 插入均摊 O(1)"
#   [ ] 排序：下游若是贪心（NMS / 区间调度），排序键必须是全序
#   [ ] 边界五连：空输入、单元素、全相同、目标不存在、目标落在两端
'''
print(RECIPE)
for _tok in ['bisect_left_', 'min_feasible_float', 'stable_order', 'bucket_of',
             'quickselect', '边界五连']:
    assert _tok in RECIPE, _tok
print('\\n（速查卡建议面试前一天过一遍；前 3 节是可直接复制进项目的代码）')"""),

    md("""### 小结

1. **二分的前提不是「数组有序」，是「存在一个可切分的单调谓词」。**
   写代码前先把 `check` 写出来并确认单调 —— 做到这一步，「在答案上二分」就是同一套模板的直接应用，
   而「寻找峰值」这种无序数组也能二分就不再神秘。

2. **只背 `bisect_left` 一套模板，其余用换算表现推。** 少一套模板就少一类 bug。
   死循环的通用判据只有一条：**mid 落在哪一半，那一半的更新就必须跨过 mid**；
   正确性靠「不变量三段式 + 严格递减的整数度量」来证明，而不是靠多做题找感觉。

3. **报复杂度要说清口径。** dict 查找是「期望 O(1)、最坏 O(n)」，插入是「均摊 O(1)」；
   而均摊 O(1) 意味着某一次会突然很慢 —— 在每帧都要跑的关键路径上，这是要预分配来规避的。

4. **渐进复杂度是常数未知的上界。** 本 notebook 实测：$n=10^5$ 时 C 层 Timsort 的全排序
   比纯 Python 的 O(n) quickselect 还快。面试里同时说得出「渐进最优」和「实测更快」，
   比背一个复杂度符号有价值得多。

5. **凡是贪心，输出就依赖排序顺序；凡是依赖排序顺序，排序键就必须是全序。**
   NMS 是最典型的例子：分数并列（INT8 量化后只有 256 档）+ 各实现 tie-break 不一致
   = 训练端与车端「差一个框」的疑难杂症。修法只有一行：把键扩成 `(-score, cls, x1, y1, idx)`。"""),
]
