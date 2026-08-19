# -*- coding: utf-8 -*-
"""C62 模块 01 · 数组与字符串：双指针、滑动窗口、前缀和。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（六步答题协议、时间预算、复杂度换算）；会写 Python 的 for/while、列表、字典"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_arrays_strings.ipynb（13 道经典题，每题<strong>暴力解与最优解对拍</strong> + 边界用例 + 复杂度验证）'),
    ("核心参考", "CLRS 第 2 章（循环不变量）· Viola &amp; Jones 2001（积分图）· C61 模块 05（IoU/NMS 手撕，本课不重复）"),
    ("预计时长", "读 80 分钟 + 跑 120 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("two-pointer-family", "双指针三形态：对撞、快慢、同向", "".join([
        P("如果只能学一个模板，学这个。<strong>双指针覆盖了 ML/CV 岗 coding 题里最大的一块</strong>，"
          "而且它的三种形态可以用一句话区分：<em>两个指针是<u>相向</u>走、<u>同向不同速</u>走、还是<u>同向且都只前进</u></em>。"
          "把这三种的「适用信号」记住，你在听完题目的 30 秒内就能判断该用哪一种。"),
        ASCII("""① 对撞指针 (converging / opposite)      —— 前提：数组**有序**，或问题本身有单调性
   a = [ 2   7   11  15  19  23 ]
         ↑                    ↑
        lo ───────►      ◄─── hi          每轮把「一定不是答案」的一端排除掉
   不变量：答案（若存在）一定还在闭区间 [lo, hi] 内
   终止：lo >= hi 时区间为空 -> 无解

② 快慢指针 (fast & slow)                 —— 前提：需要「相对位置」而不是绝对下标
   a = [ 1   1   2   2   3 ]
         ↑       ↑
       slow    fast ──►                   fast 负责**读**，slow 负责**写**
   不变量：a[0..slow-1] 已经是处理完的合法结果，且保持原相对顺序
   典型：原地去重、原地移除、链表找中点/判环

③ 同向双指针 / 滑动窗口 (sliding window) —— 前提：窗口的「合法性」随长度**单调**
   s = "a b c a b c b b"
        └──────┘
       left   right ──►                   right 只前进，left 只前进 -> 总步数 <= 2n
   不变量：s[left..right] 始终满足题目约束（或「刚刚违反，正在修」）
   终止：right 走完整个数组"""),
        P("三者的判别信号，按「听到什么就选什么」整理："),
        TABLE(["形态", "听到这些信号就想到它", "循环不变量", "代表题（频率 / 优先级）"], [
            ["<strong>对撞指针</strong>", "「<strong>已排序</strong>」「找两个数使和为 target」「首尾配对」「最大面积 / 最多容器」「回文」", "答案一定还在 <code>[lo, hi]</code> 内；每次排除的那一端<strong>可证明不可能是答案</strong>", "两数之和 II（<strong>高频·必会</strong>）、盛最多水的容器（高频·必会）、三数之和（<strong>高频·必会</strong>）"],
            ["<strong>快慢指针</strong>", "「<strong>原地</strong>」「O(1) 额外空间」「返回新长度」「链表中点 / 判环」", "<code>a[0..slow-1]</code> 是已完成的合法前缀", "移除元素、删除有序数组重复项（<strong>高频·必会</strong>）、移动零（高频·必会）"],
            ["<strong>同向 / 滑窗</strong>", "「<strong>连续</strong>子数组 / 子串」「最长 / 最短」「恰好包含」「窗口内不超过 k 个」", "窗口内始终满足约束；<code>left</code> 单调不减", "最长无重复子串（<strong>高频·必会</strong>）、最小覆盖子串（中频·加分）、长度最小的子数组（高频·必会）"],
        ]),
        DUAL(
            "为什么双指针能把 $O(n^2)$ 降到 $O(n)$？因为它<strong>不是「跳过一些检查」，而是「每检查一次就排除一整行或一整列」</strong>。"
            "拿两数之和 II 举例：暴力解要检查 $n(n-1)/2$ 个数对；对撞指针每比较一次，"
            "如果 <code>a[lo]+a[hi] &lt; target</code>，那么 <em><code>a[lo]</code> 与 <u>任何</u> <code>a[hi']</code>（$hi' \\le hi$）的和都更小</em>"
            "——一次比较排除了以 <code>lo</code> 为左端的<u>整行</u> $hi-lo$ 个候选。"
            "$n$ 次比较排除了 $O(n^2)$ 个候选，这就是加速的来源。",
            "更严谨地说，双指针的正确性依赖一个<span class=\"term\">单调性/交换论证</span>结构：存在一个全序，"
            "使得「被排除的候选集」中不含最优解。这个论证必须<strong>逐题重新做一遍</strong>，"
            "不能想当然——<em>同样是对撞指针，两数之和 II 依赖数组有序，而盛最多水的容器<u>不依赖有序</u>，"
            "它依赖的是「面积 = 宽 × min(两端高度)」这个函数在移动长板时必然不增</em>。"
            "两道题的模板一模一样，但正确性证明完全不同。<strong>面试官追问「你怎么知道这样不会漏解」时，"
            "他要的就是这个证明，不是模板。</strong>第 2 节专门讲怎么当场把它说出来。",
        ),
        CALLOUT("warn", "<strong>最常见的误用：在无序数组上用对撞指针。</strong>「两数之和」（无序，返回下标）必须用哈希表，"
                        "而「两数之和 II」（有序，返回下标）才用对撞指针。"
                        "<em>如果面试官给的是无序数组而你直接排序，就破坏了「返回原下标」这个要求</em>——"
                        "这时正确的做法是排序前先记下 <code>(值, 原下标)</code>，或者干脆用哈希。"
                        "<strong>听到「返回下标」这三个字，先问一句「需要原数组的下标吗」。</strong>"),
    ])),

    # ============================================================== 2
    ("invariant", "循环不变量：怎么当场证明「不会漏解」", "".join([
        P("这一节是本模块最值钱的部分，因为它是<strong>区分「背过模板」和「懂了」的那道分水岭</strong>。"
          "面试官几乎一定会在你写完双指针后问一句：「你怎么保证这样不会漏掉最优解？」"
          "这时候有没有一句结构化的回答，直接决定「正确性」和「沟通」两栏的分。"),
        P("<span class=\"term\">循环不变量</span>（loop invariant）是一个关于程序状态的命题，要证明三件事（CLRS 第 2 章的标准框架）："),
        OL([
            "<strong>初始化</strong>（initialization）：进入循环前它成立。",
            "<strong>保持</strong>（maintenance）：如果某轮开始时成立，那么这轮结束时仍然成立。",
            "<strong>终止</strong>（termination）：循环结束时，不变量 + 终止条件<em>合起来</em>直接给出答案。",
        ]),
        H3("完整示范：盛最多水的容器，为什么可以「移动短板」"),
        P("题目：<code>h[i]</code> 是第 <code>i</code> 根柱子的高度，选两根柱子装水，面积 = "
          "$(j-i)\\times\\min(h_i,h_j)$，求最大面积。做法是 <code>lo=0, hi=n-1</code>，"
          "每轮结算当前面积，然后<strong>把矮的那一端往里移</strong>。"),
        MATH("\\text{不变量：}\\quad \\max_{\\,0\\le i<j\\le n-1} A(i,j) \\;=\\; \\max\\Bigl(\\textit{best},\\;\\; \\max_{\\,lo\\le i<j\\le hi} A(i,j)\\Bigr)"),
        P("翻译成人话：<strong>「全局最优 = 已经记下的 best 与还没排除的区间里的最优，二者之一」</strong>。"
          "三步证明："),
        UL([
            "<strong>初始化</strong>：<code>lo=0, hi=n-1, best=0</code>，右边那一项就是全体候选，成立。",
            "<strong>保持</strong>（关键的一步）：不妨设 $h_{lo} \\le h_{hi}$，我们要移动 <code>lo</code>。"
            "需要证明「所有以 <code>lo</code> 为左端的候选都可以安全丢弃」。对任意 $j &lt; hi$："
            "$A(lo,j) = (j-lo)\\cdot\\min(h_{lo},h_j) \\le (hi-lo)\\cdot h_{lo} = A(lo,hi)$"
            "——<em>宽度更小，且高度不可能超过 $h_{lo}$</em>。而 $A(lo,hi)$ 这轮已经结算进 <code>best</code> 了。"
            "所以丢掉整列不会丢掉最优解，不变量保持。",
            "<strong>终止</strong>：<code>lo == hi</code> 时右边那一项是空集，于是 <code>best</code> 就是全局最优。",
        ]),
        CALLOUT("intuition", "把这段证明压成面试里的<strong>一句话</strong>："
                             "「移动短板是安全的，因为<u>以短板为一端的所有其他组合，宽更小、高也不可能超过短板</u>，"
                             "而最宽的那一个我这轮已经算过了。」<em>这一句话就够了，不需要写公式。</em>"
                             "同样的句式可以套到两数之和 II：「<code>a[lo]+a[hi] &lt; target</code> 说明 "
                             "<code>a[lo]</code> 配任何更小的右端都更小，所以整行可以丢。」"),
        DUAL(
            "为什么一定要写注释说明不变量？因为<strong>双指针代码的 bug 几乎全部来自不变量被写歪</strong>，"
            "而不是来自打字错误。典型三种：<em>①该用 <code>while lo &lt; hi</code> 写成了 <code>&lt;=</code></em>"
            "（自己和自己配对）；<em>②该在移动前结算写成了移动后结算</em>（漏掉一个候选）；"
            "<em>③相等时该动哪一边没想清楚</em>（可能死循环）。"
            "在代码里写一行 <code># 不变量：...</code>，等于强迫自己在写之前先想清楚这三件事。",
            "在评分表上，这一行注释同时命中三栏：<strong>代码质量</strong>（自解释的代码）、"
            "<strong>正确性</strong>（面试官能顺着不变量核对边界）、<strong>沟通</strong>（把思考过程留在纸面上）。"
            "<em>成本是 8 个字，收益是三栏各半分</em>。这是整个准备过程里投入产出比最高的习惯之一。"
            "在真实工程里它同样成立——<span class=\"term\">NMS</span> 的抑制循环、"
            "多帧跟踪的滑动窗口维护、切片推理的跨片合并，这些代码在 code review 里被问到的第一句话，"
            "永远是「这个循环结束时你保证了什么」。",
        ),
        CALLOUT("danger", "<strong>不要用「我试了几个例子都对」来回答「怎么证明不漏解」。</strong>"
                          "这句话在面试官耳朵里等价于「我不知道为什么对」。"
                          "正确的降级答法是：「我没法当场严格证明，但直觉是这样：<u>……</u>。"
                          "我可以写一个暴力解做随机对拍来增强信心。」"
                          "<em>——承认边界 + 给出验证方案，这在「诚实度」上是加分的，比硬编一个伪证明好得多。</em>"),
    ])),

    # ============================================================== 3
    ("sliding-window", "滑动窗口：定长与可变两套模板", "".join([
        P("滑动窗口是同向双指针的特例，但它值得单独一套模板，因为<strong>「什么时候收缩」这一个决定，"
          "分出了三类完全不同的题</strong>。先看模板骨架："),
        ASCII("""【模板 A · 定长窗口】窗口长度恒为 k，进一个出一个
    s = sum(a[:k])                     # 先把第一个窗口装满
    best = s
    for right in range(k, n):
        s += a[right] - a[right - k]   # ← 一进一出，O(1) 维护
        best = max(best, s)
    # 不变量：循环体开始时，s == sum(a[right-k+1 .. right])

【模板 B · 可变窗口】right 每步前进 1，left 按条件收缩
    left = 0
    for right in range(n):
        加入 a[right] 到窗口状态
        while <窗口非法>:              # ← B1：违反约束才缩（求**最长**）
            移出 a[left]; left += 1
        best = max(best, right - left + 1)

    left = 0
    for right in range(n):
        加入 a[right] 到窗口状态
        while <窗口已满足>:            # ← B2：满足就缩到不能再缩（求**最短**）
            best = min(best, right - left + 1)
            移出 a[left]; left += 1

    差别只有一处：**while 的条件是「非法」还是「已满足」**，
    以及**结算写在 while 里面还是外面**。写反了就得到相反的答案。"""),
        P("三类题的对照（这张表建议直接背下来）："),
        TABLE(["求什么", "while 条件", "结算位置", "代表题", "频率 / 优先级"], [
            ["<strong>最长</strong>合法子串/子数组", "窗口<strong>非法</strong>时收缩", "while <strong>之后</strong>（此时窗口合法）", "最长无重复子串、至多含 K 个不同字符的最长子串", "<strong>高频 · 必会</strong>"],
            ["<strong>最短</strong>满足条件的子数组", "窗口<strong>已满足</strong>时收缩", "while <strong>之内</strong>（收缩前先记）", "长度最小的子数组、最小覆盖子串", "<strong>高频 · 必会</strong>"],
            ["<strong>定长</strong>窗口的极值/统计", "不收缩，长度恒为 k", "每步一次", "定长子数组最大和、滑动窗口最大值（配单调队列）", "中频 · 必会"],
        ]),
        H3("为什么是 O(n)：摊还分析"),
        P("很多人被「里面还有一个 while 循环」吓到，以为是 $O(n^2)$。<strong>不是</strong>，因为 "
          "<code>left</code> 只增不减，且上界是 $n$："),
        MATH("T(n) \\;=\\; \\underbrace{n}_{\\text{right 前进}} \\;+\\; \\underbrace{\\sum_{\\text{right}} \\Delta \\text{left}}_{\\text{总和} \\,\\le\\, n} \\;\\le\\; 2n \\;=\\; O(n)"),
        P("<strong>这句话必须能当场说出来</strong>：「内层 while 看起来是嵌套循环，但 <code>left</code> 在整个执行过程中"
          "总共只前进 $n$ 步，所以内层循环体的总执行次数不超过 $n$ 次，整体还是 $O(n)$——这是<span class=\"term\">摊还分析</span>"
          "（amortized analysis）。」<em>说得出这句，「复杂度」栏直接从 3 分变 5 分。</em>"),
        DUAL(
            "滑动窗口能成立，靠的是一个隐含前提：<strong>窗口的合法性关于长度是单调的</strong>——"
            "如果 <code>s[left..right]</code> 合法，那么它的任何子串也合法（对「最长」类题）；"
            "或者如果 <code>s[left..right]</code> 满足条件，那么任何包含它的更长区间也满足（对「最短」类题）。"
            "<em>只有这个单调性成立，「收缩到边界就停」才不会漏解。</em>",
            "反过来说，<strong>单调性一旦被破坏，滑动窗口立刻错</strong>，而且错得很隐蔽。"
            "最经典的反例是<em>「和为 K 的子数组」在有负数时</em>：加入一个负数会让窗口和<u>变小</u>，"
            "于是「和太大就收缩」这个规则失效——收缩之后可能反而更大。"
            "此时正确解法是<strong>前缀和 + 哈希表</strong>（第 4 节），复杂度同样 $O(n)$，但机制完全不同。"
            "<em>面试里如果你上来就写滑窗，面试官很可能只补一句「数组里可以有负数」，"
            "然后看你是否意识到整个解法塌了。</em>",
        ),
        CALLOUT("danger", "<strong>面试当场的高频翻车：用 <code>collections.defaultdict(int)</code> 维护窗口计数，"
                          "然后用 <code>len(window)</code> 判断「窗口里有几种字符」。</strong>"
                          "<code>defaultdict</code> 在<em>读取</em>不存在的 key 时会<u>创建</u>它，"
                          "于是 <code>if window[c] == 0</code> 这一句就把 <code>c</code> 塞进了字典，"
                          "<code>len(window)</code> 从此永远偏大。"
                          "<em>正确做法：用普通 <code>dict</code> + <code>.get(c, 0)</code>，"
                          "或者在计数归零时显式 <code>del window[c]</code>。</em>"
                          "这个 bug 在本地跑小例子常常看不出来，但在面试官的追问用例上会当场暴露。"),
    ])),

    # ============================================================== 4
    ("prefix-diff", "前缀和与差分：把「区间查询」压成 O(1)", "".join([
        P("前缀和是所有区间类问题的地基。定义上只有一行，但<strong>下标约定选错会让你在面试里反复 ±1</strong>，"
          "所以先把约定钉死："),
        CODE("""pre = [0] * (n + 1)                 # ← 长度是 n+1，不是 n。这一步消灭了所有 if i == 0
for i in range(n):
    pre[i + 1] = pre[i] + a[i]

# 语义：pre[i] = a[0] + a[1] + ... + a[i-1]   （前 i 个元素之和，**不含** a[i]）
# 区间和 a[l..r]（闭区间）= pre[r + 1] - pre[l]        ← 只有这一个公式要背
# 自检：a[0..n-1] 的和 = pre[n] - pre[0] = pre[n]  ✓"""),
        CALLOUT("intuition", "<strong>「多留一格哨兵」是数组题里回报最高的一个技巧。</strong>"
                             "长度 $n+1$ 的前缀和数组让「从头开始的区间」不再是特例；"
                             "长度 $n+1$ 的差分数组让「改到最后一个元素」不越界。"
                             "<em>面试里每消掉一个 <code>if</code> 分支，就少一个可能写错的边界。</em>"),
        H3("差分：前缀和的逆运算"),
        P("差分数组 <code>d</code> 满足 <code>a = 前缀和(d)</code>。它解决的是<strong>「批量区间加，最后只问一次结果」</strong>："),
        TABLE(["操作", "朴素做法", "差分做法", "复杂度对比"], [
            ["把 <code>a[l..r]</code> 全部加 <code>v</code>（共 m 次操作）", "每次遍历区间", "<code>d[l] += v; d[r+1] -= v</code>", "$O(m\\cdot n)$ → <strong>$O(m + n)$</strong>"],
            ["查询任意区间和（共 q 次查询）", "每次遍历区间", "预处理前缀和后 <code>pre[r+1]-pre[l]</code>", "$O(q\\cdot n)$ → <strong>$O(n + q)$</strong>"],
            ["<em>既要改又要查（交替进行）</em>", "—", "<em>差分/前缀和都不行</em>，需要树状数组或线段树", "$O((n+q)\\log n)$，<strong>低频，面试里可直接说「我会用 BIT」</strong>"],
        ]),
        P("差分在感知工程里的一个真实用途：<strong>统计「每个时刻同时被多少个 track 覆盖」</strong>。"
          "每条 track 是一个时间区间 <code>[t_start, t_end]</code>，要算每一帧的活跃 track 数——"
          "朴素做法是对每条 track 遍历它的所有帧（$O(\\text{track 数}\\times\\text{帧数}）$），"
          "差分做法是每条 track 只做两次 ±1，最后扫一遍前缀和。"),
        H3("和为 K 的子数组：前缀和 + 哈希表"),
        P("这是<strong>高频·必会</strong>题，也是第 3 节那个「滑窗在负数下失效」的正解。核心恒等式只有一行："),
        MATH("\\mathrm{sum}(i..j) = k \\iff \\mathrm{pre}[j{+}1] - \\mathrm{pre}[i] = k \\iff \\mathrm{pre}[i] = \\mathrm{pre}[j{+}1] - k"),
        P("于是从左往右扫，边扫边把见过的前缀和存进哈希表，"
          "对当前的 <code>pre[j+1]</code> 直接查「有多少个 <code>pre[i] == pre[j+1] - k</code>」。"
          "$O(n)$ 时间、$O(n)$ 空间，<strong>而且完全不依赖元素正负</strong>。"),
        DUAL(
            "初始化 <code>seen = {0: 1}</code> 这一行是最容易漏的。它的含义是「空前缀 <code>pre[0]=0</code> 已经见过一次」——"
            "没有它，「从下标 0 开始就恰好等于 k 的子数组」会被漏掉。"
            "<em>面试官如果想抓 bug，第一个试的用例就是 <code>a=[k]</code>。</em>",
            "更本质地看，这道题展示了一个<strong>可迁移的转换范式</strong>："
            "<span class=\"term\">「区间问题 → 两点问题」</span>。"
            "任何形如「求满足 $f(\\text{区间}) = c$ 的区间个数」的问题，只要 $f$ 可以写成"
            "$g(\\text{右端点}) \\ominus g(\\text{左端点})$ 的形式（$\\ominus$ 是可逆运算），"
            "就可以用同一套「前缀量 + 哈希表」解决。<em>把「和」换成「异或」就是「异或和为 K 的子数组」；"
            "换成「0/1 计数差」就是「含相同个数 0 和 1 的最长子数组」；"
            "换成「模 k 的余数」就是「和能被 k 整除的子数组」。</em>"
            "<strong>识别出这个范式，等于一次拿下四五道题——面试里主动说出这个归纳，是明确的加分点。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("prefix2d", "二维前缀和：它就是 CV 里的积分图", "".join([
        P("这是本模块<strong>与本岗位关系最直接</strong>的一节。二维前缀和在算法书里叫 prefix sum 2D，"
          "在计算机视觉里叫 <span class=\"term\">integral image</span>（积分图）或 "
          "<span class=\"term\">summed-area table</span>（SAT）——"
          "<strong>它们是同一个东西，只是两个圈子各起了一个名字</strong>。"),
        MATH("S(r,c) \\;=\\; \\sum_{i<r}\\;\\sum_{j<c} I(i,j), \\qquad S \\in \\mathbb{R}^{(H+1)\\times(W+1)}"),
        MATH("\\mathrm{sum}\\bigl(r_0..r_1,\\; c_0..c_1\\bigr) \\;=\\; S(r_1{+}1,\\,c_1{+}1) \\;-\\; S(r_0,\\,c_1{+}1) \\;-\\; S(r_1{+}1,\\,c_0) \\;+\\; S(r_0,\\,c_0)"),
        ASCII("""容斥的四个角（为什么最后要「加回来」一次）

        c0          c1+1
         │           │
   r0 ───A───────────B───           A = S(r0,   c0  )
         │           │              B = S(r0,   c1+1)
         │  ┌─────┐  │              C = S(r1+1, c0  )
         │  │目标 │  │              D = S(r1+1, c1+1)
         │  └─────┘  │
 r1+1 ───C───────────D───           目标 = D - B - C + A
         │           │
                                    D 是整个左上大矩形；
                                    减 B 去掉上方长条，减 C 去掉左方长条，
                                    但左上角那块 A 被**减了两次**，所以加回一次。

   四次数组访问，与矩形大小完全无关 —— 这就是 O(1)。"""),
        TABLE(["任务", "朴素做法", "积分图做法", "在什么规模下值得"], [
            ["查询 q 个任意矩形的和", "$O(q \\cdot hw)$", "预处理 $O(HW)$ + 查询 $O(q)$", "<strong>q 稍大就必赢</strong>；矩形越大差距越夸张"],
            ["box filter（均值滤波）", "$O(HW k^2)$", "$O(HW)$，<strong>与核大小无关</strong>", "核大于 3×3 就该用"],
            ["Haar 特征（Viola-Jones 人脸检测）", "不可行", "每个特征 6–9 次访问", "<strong>这是积分图 2001 年被发明出来的原因</strong>"],
            ["统计每个候选框内的前景像素数 / 平均置信度", "$O(\\text{框数} \\times \\text{框面积})$", "$O(HW + \\text{框数})$", "候选框成千上万时（<strong>难例挖掘、框打分</strong>）"],
        ]),
        DUAL(
            "在 TSR 的工程实践里，这个技巧最常出现在两个地方。"
            "<em>①候选框的快速打分</em>：拿到一张前景概率图和几千个候选框，要算每个框内的平均概率——"
            "逐框切片求和是 $O(\\text{框数}\\times\\text{面积})$，积分图是建一次 + 每框四次访问。"
            "<em>②图像内容的粗筛</em>：判断「这一片区域是不是几乎全是天空/路面」，用积分图算区域均值与方差，"
            "可以在送进检测器之前就把大片无信息区域跳过（呼应 C57 的 ROI 裁剪）。",
            "两个必须知道的<strong>工程陷阱</strong>。<em>①溢出</em>：一张 1920×1080 的 uint8 图，"
            "积分图右下角的值是 $1920\\times1080\\times255 \\approx 5.3\\times10^{8}$，"
            "已经超过 int32 的一半——如果图是 float32 累加，"
            "<u>大数吃小数</u>会让远处的小矩形和产生可见误差。"
            "<strong>正确做法：整型图用 int64，浮点图用 float64 累加</strong>（OpenCV 的 "
            "<code>cv2.integral</code> 默认就给 float64/int32 两种输出，不是随便选的）。"
            "<em>②闭区间还是半开区间</em>：算法题里矩形边界通常是闭区间 <code>[r0..r1]</code>，"
            "而 bbox 常用半开或浮点坐标；两边混用会产生系统性的 off-by-one。"
            "<strong>面试里写这道题，先花 5 秒说清「我用闭区间，所以 +1 出现在这两处」，比事后改三遍强。</strong>",
        ),
        CALLOUT("warn", "<strong>面试里不要直接调 <code>np.cumsum</code> 就说做完了。</strong>"
                        "考点是容斥的四项和 <code>+1</code> 的位置，不是会不会用 numpy。"
                        "<em>可接受的做法是：先手写双重循环版本 <code>S[i+1][j+1] = S[i][j+1] + S[i+1][j] - S[i][j] + I[i][j]</code>"
                        "（注意这里也是容斥），说清楚它，再补一句「实际工程里我会写成 "
                        "<code>img.cumsum(0).cumsum(1)</code>，向量化后快两个数量级」。</em>"
                        "——先证明你懂机制，再展示你懂工程，两栏都拿到。"),
    ])),

    # ============================================================== 6
    ("inplace", "原地修改与 O(1) 空间：读写双指针", "".join([
        P("「原地」（in-place）在面试里有一个<strong>精确定义</strong>，最好在开始写之前确认一遍："
          "<em>额外空间 $O(1)$，输出写回输入数组，返回有效长度</em>——输出本身不算额外空间。"
          "很多人栽在这里：用了一个新列表装结果，最后再赋值回去，这不是原地。"),
        CODE("""# 读写双指针的通用骨架（快慢指针的最常见用法）
def compact(a, keep):
    write = 0                       # 不变量：a[0 .. write-1] 是已确定的结果，且保持原相对顺序
    for read in range(len(a)):      # read 负责扫描，write 负责落笔
        if keep(a[read]):
            a[write] = a[read]
            write += 1
    return write                    # a[:write] 是答案；a[write:] 是"垃圾区"，题目通常不关心

# 三道题共用这一个骨架，只换 keep：
#   移除元素        keep = lambda x: x != val
#   移动零(保序)     keep = lambda x: x != 0        （之后把 a[write:] 填 0）
#   删除有序数组重复 keep 依赖前一个写入值 -> 改成 if write == 0 or a[read] != a[write-1]"""),
        TABLE(["技巧", "做什么", "为什么面试爱考", "频率 / 优先级"], [
            ["<strong>读写双指针</strong>", "扫描 + 就地压缩", "一个骨架覆盖 4–5 道题，且能考出「相对顺序保不保」的细节", "<strong>高频 · 必会</strong>"],
            ["<strong>三次反转轮转数组</strong>", "轮转 k 位 = 整体反转 + 前 k 反转 + 后 n−k 反转", "$O(1)$ 空间的漂亮解；追问「k &gt; n 怎么办」（取模）", "中频 · 必会"],
            ["<strong>首尾交换反转</strong>", "<code>a[lo], a[hi] = a[hi], a[lo]</code>", "对撞指针最简形态；字符串题的基础件", "高频 · 必会"],
            ["<strong>符号位/绝对值标记</strong>", "把「见过 x」记成 <code>a[x-1] *= -1</code>", "「找缺失的第一个正数」这类题的 $O(1)$ 空间解", "低频 · 加分"],
            ["<strong>就地哈希（下标即键）</strong>", "把值 <code>v</code> 交换到下标 <code>v-1</code>", "同上；<em>能想到就是加分，想不到不致命</em>", "低频 · 加分"],
        ]),
        CALLOUT("danger", "<strong>三个会把 $O(n)$ 悄悄变成 $O(n^2)$ 的 Python 写法</strong>，"
                          "面试官盯着看的就是这些：<br>"
                          "① <code>for x in a: if x == val: a.remove(x)</code> —— "
                          "<code>list.remove</code> 是 $O(n)$，而且<em>边遍历边删会跳过元素</em>（双重错误）。<br>"
                          "② <code>a.pop(0)</code> 当队列用 —— 每次 $O(n)$ 的元素搬移。"
                          "正确做法是 <code>collections.deque</code> 的 <code>popleft()</code>（$O(1)$）。<br>"
                          "③ 循环里做切片 <code>window = a[left:right+1]</code> —— "
                          "切片是 $O(k)$ 的<u>拷贝</u>，套在 $O(n)$ 的循环里就是 $O(n^2)$，"
                          "而且额外空间也不再是 $O(1)$。<em>滑动窗口题里这是最常见的隐藏复杂度炸弹。</em>",
                "Python 特有的三个复杂度陷阱"),
        DUAL(
            "为什么面试官这么在意 $O(1)$ 空间？表面理由是「考察你对内存的敏感度」，"
            "真实理由更具体：<strong>在嵌入式与车端场景里，堆分配本身就是延迟的不确定性来源</strong>。"
            "一个每帧都要 <code>malloc</code> 一块临时缓冲的后处理函数，在内存碎片化之后耗时会变得不可预测——"
            "这与 C53-04 讲的「NMS 让延迟依赖场景」是同一类问题。"
            "<em>量产代码里常见的做法是预分配固定大小的缓冲池，函数只在里面就地操作。</em>",
            "所以「原地」这个要求在面试里其实是<strong>一个代理指标</strong>："
            "它测的不是你会不会写 <code>write</code> 指针，而是<em>你是否知道内存分配有成本</em>。"
            "面试里主动补一句会很加分：「这里我用了 $O(1)$ 额外空间；"
            "如果这段代码在车端每帧调用，我还会考虑把输出缓冲预分配好，避免每帧的动态分配——"
            "<strong>因为分配的耗时方差比它的均值更麻烦</strong>。」"
            "<em>这一句话把一道算法题接到了工程现实上，是明确的信号。</em>",
        ),
    ])),

    # ============================================================== 7
    ("edge-cases", "边界条件清单：写完不测是最贵的错误", "".join([
        P("回忆模块 00 的评分表：<strong>测试意识占 15%，而大部分候选人这一栏拿 1 分</strong>。"
          "拿到 5 分的成本其实极低——你只需要背一张六行的清单，每道题照着念一遍。"),
        TABLE(["边界类别", "具体用例", "会挂在哪种题上", "为什么容易忘"], [
            ["<strong>空输入</strong>", "<code>[]</code> / <code>\"\"</code> / <code>None</code>", "<em>几乎所有题</em>。前缀和的 <code>pre[n]</code>、双指针的 <code>hi = n-1 = -1</code>", "本地测试从不构造空输入"],
            ["<strong>单元素</strong>", "<code>[5]</code> / <code>\"a\"</code>", "对撞指针（<code>lo == hi</code> 循环不进入）、快慢指针（<code>fast</code> 越界）", "「至少两个元素」是脑子里的隐含假设"],
            ["<strong>全相同</strong>", "<code>[3,3,3,3]</code> / <code>\"aaaa\"</code>", "三数之和的去重、删除重复项、滑动窗口的收缩条件", "去重逻辑写在哪一层，这里立刻暴露"],
            ["<strong>已排序 / 完全逆序</strong>", "<code>[1,2,3]</code> / <code>[3,2,1]</code>", "区间合并（全重叠 vs 全不重叠）、单调队列（退化成 $O(n)$ 次弹出）", "最好和最坏两个极端往往是同一行代码的两个分支"],
            ["<strong>重复元素</strong>", "<code>[1,1,2,2]</code>、target 出现多次", "三数之和、两数之和返回哪一对、二分找左右边界", "「假设元素互不相同」是最常见的<u>未声明假设</u>"],
            ["<strong>极值 / 符号</strong>", "<code>[-1,-2]</code>、<code>0</code>、非常大的数", "和为 K 的子数组（负数让滑窗失效）、乘积类题（<strong>0 和负数</strong>）", "题目里没写「都是正数」，你就不能假设"],
        ]),
        CALLOUT("intuition", "把这张表做成<strong>一句口播</strong>，写完代码后照着念："
                             "「我过一遍边界：空数组走不进循环返回 0；单元素时 lo==hi 直接退出；"
                             "全相同时去重那一行会跳过；有负数时……嗯，这里我的滑窗假设不成立，"
                             "我得改成前缀和 + 哈希。」"
                             "<em>——注意最后半句：<strong>当场发现自己的 bug，比面试官发现它，分数高得多</strong>。</em>"),
        H3("随机对拍：把「我觉得对」变成「我验证过」"),
        P("边界清单覆盖的是<em>你想得到的</em>情况。真正强的做法是加一层<strong>随机对拍</strong>（stress testing）："
          "写一个显然正确的暴力解，随机生成大量小规模输入，逐一比对两者的输出。"),
        CODE("""def stress(opt, brute, gen, trials=500, seed=0):
    rng = random.Random(seed)
    for _ in range(trials):
        arg = gen(rng)                      # 生成**小规模**输入：长度 0-10，值域窄，重复多
        g, w = opt(arg), brute(arg)
        if g != w:
            return {'ok': False, 'input': arg, 'got': g, 'want': w}   # 返回最小反例
    return {'ok': True, 'trials': trials}"""),
        P("三个让对拍真正有效的细节：<strong>①规模要小</strong>（长度 0–10），"
          "这样反例是人能一眼看懂的；<strong>②值域要窄</strong>（比如只用 0–3 或 <code>'abc'</code>），"
          "这样重复元素和边界会被高频触发；<strong>③要固定 seed</strong>，否则反例不可复现。"),
        DUAL(
            "在 45 分钟的面试里当然来不及写完整的对拍框架，"
            "但<strong>你可以把它说出来</strong>：「我这里写了暴力解，如果时间允许我会用它做随机对拍，"
            "长度取 0 到 8、值域取 0 到 3，这样重复元素和空数组都能高频覆盖到。」"
            "<em>这句话让「先给暴力解」这一步产生了第二笔收益——它不只是安全网，还是验证工具。</em>",
            "这个方法论在真实工作里的对应物是<strong>参考实现对拍</strong>，"
            "在训练-部署一致性验证里是标准动作（C60 的主题）："
            "用 PyTorch 的输出作为 reference，逐层比对 TensorRT engine 的输出；"
            "或者用 Python 版的 NMS 对拍 C++/CUDA 版的实现。"
            "<em>「写一个慢但显然正确的版本作为 ground truth」不是面试技巧，"
            "是感知工程里定位问题最快的手段</em>——差别只在于面试里对拍的是算法，"
            "工程里对拍的是<u>实现</u>。<strong>能把这个联系说出来，面试官会立刻知道你做过真实项目。</strong>",
        ),
    ])),

    # ============================================================== 8
    ("cv-bridge", "回到 CV：这些模板在感知代码里长什么样", "".join([
        P("这一节把前面七节的东西<strong>接回本岗位</strong>。三条连接，每一条都可以在面试里主动提出来——"
          "它们同时展示算法功底和领域理解，是这门课相对于「纯刷题」的全部价值所在。"),
        H3("① IoU 的一维投影，就是区间求交"),
        P("轴对齐框的 IoU，交集面积可以分解成两个独立的一维区间求交之积："),
        MATH("\\mathrm{inter} = \\underbrace{\\max\\bigl(0,\\;\\min(x_2,x_2') - \\max(x_1,x_1')\\bigr)}_{x\\text{ 轴上的区间交长度}} \\times \\underbrace{\\max\\bigl(0,\\;\\min(y_2,y_2') - \\max(y_1,y_1')\\bigr)}_{y\\text{ 轴上的区间交长度}}"),
        P("而「给两组各自不相交且有序的区间，求所有交集」正是<strong>双指针</strong>的标准题"
          "（谁的右端点先结束谁前进，$O(m+n)$）。"
          "<em>手撕完整的 IoU / GIoU / NMS / mAP 请去 <strong>C61 模块 05</strong>，本课不重复；"
          "这里只需要知道：那些代码的骨架，就是你在这一模块练的区间操作。</em>"),
        H3("② NMS 就是「排序 + 扫描」"),
        P("贪心 NMS 的结构是：<strong>按分数降序排序 → 从高到低扫描 → 每保留一个就抑制掉与它 IoU 超阈值的后续框</strong>。"
          "这与「区间调度」（按结束时间排序后贪心取）是同一个模式：<em>排序建立一个全序，扫描时用一个"
          "「已选集合」做局部约束检查</em>。C62 模块 04 会把 NMS 建模成加权区间调度并用 DP 求最优解，"
          "量化贪心的次优程度。"),
        H3("③ 多帧投票 = 滑动窗口；bbox 统计 = 积分图"),
        P("TSR 的时序融合（C55-04）里，「最近 K 帧里这个 track 被检出了几次」就是一个定长滑动窗口的计数；"
          "「置信度在窗口内的移动平均」就是定长窗口求和。"
          "而候选框打分、前景像素统计、区域均值方差粗筛，都是积分图的直接应用。"),
        H3("本模块题目清单与优先级"),
        P("下表是<strong>本模块 notebook 里全部亲手实现的题</strong>，按频率与必要性排序。"
          "如果时间紧，先把「高频 · 必会」这一档全部写到不看模板也能写对为止。"),
        TABLE(["题", "模板", "频率", "优先级", "关键陷阱"], [
            ["两数之和 II（有序）", "对撞指针", "<strong>高频</strong>", "<strong>必会</strong>", "无序版必须用哈希；「返回原下标」要先问"],
            ["盛最多水的容器", "对撞指针", "<strong>高频</strong>", "<strong>必会</strong>", "要能证明「移动短板不漏解」"],
            ["三数之和", "排序 + 对撞", "<strong>高频</strong>", "<strong>必会</strong>", "<strong>去重三处</strong>（固定元素、左指针、右指针）"],
            ["移除元素 / 删除有序数组重复项", "快慢指针", "<strong>高频</strong>", "<strong>必会</strong>", "返回长度而不是新数组；相对顺序"],
            ["最长无重复子串", "可变滑窗（求最长）", "<strong>高频</strong>", "<strong>必会</strong>", "<code>last[ch] &gt;= left</code> 这个判断漏了就错"],
            ["长度最小的子数组", "可变滑窗（求最短）", "<strong>高频</strong>", "<strong>必会</strong>", "结算写在 while 里；元素必须非负"],
            ["和为 K 的子数组", "前缀和 + 哈希", "<strong>高频</strong>", "<strong>必会</strong>", "<code>seen = {0: 1}</code>；<strong>有负数时滑窗失效</strong>"],
            ["区间合并", "排序 + 扫描", "<strong>高频</strong>", "<strong>必会</strong>", "边界相接算不算重叠，要问"],
            ["定长子数组最大和", "定长滑窗", "中频", "必会", "先装满再滑；一进一出"],
            ["区间交集（双数组）", "双指针", "中频", "必会", "谁先结束谁前进；<strong>直连 IoU</strong>"],
            ["二维前缀和求任意矩形和", "积分图", "中频", "<strong>必会（本岗位）</strong>", "容斥四项 + <code>+1</code> 位置；<strong>溢出</strong>"],
            ["最小覆盖子串", "可变滑窗 + 计数", "中频", "加分", "<code>missing</code> 计数器的更新时机"],
            ["滑动窗口最大值", "定长滑窗 + 单调队列", "中频", "加分", "队列存<strong>下标</strong>不存值；过期弹出"],
            ["除自身以外数组的乘积", "前缀积 + 后缀积", "中频", "加分", "不用除法（有 0）；输出数组不算额外空间"],
            ["区间加（差分）", "差分数组", "低频", "加分", "<code>d[r+1] -= v</code> 的越界；<strong>需要「边改边查」就得上 BIT</strong>"],
        ]),
        DUAL(
            "怎么用这张表？<strong>不要按题号刷，按模板刷</strong>。"
            "把「可变滑窗求最长」这一个模板写三遍（最长无重复子串、至多 K 个不同字符、"
            "至多含一个 0 的最长连续 1），你会发现三道题的差别只在「窗口状态怎么维护」这两行；"
            "<em>而按题号刷会让你每次都从头想一遍</em>。"
            "模板熟练的标志是：听完题目 30 秒内能说出「这是可变滑窗求最长，窗口状态用一个 dict 记最后出现位置」。",
            "但也要警惕<strong>模板依赖的反面</strong>：面试官很清楚候选人在背模板，"
            "所以他常常会把题目改一个字节来破坏模板的前提——"
            "<em>「如果数组里可以有负数呢？」（滑窗塌了，要上前缀和哈希）；"
            "「如果要求返回所有答案而不是个数呢？」（哈希表要存下标列表）；"
            "「如果数据是流式的、不能回头看呢？」（前缀和数组存不下，要改成在线算法）。</em>"
            "<strong>真正的准备是：对每个模板，知道它成立的<u>前提</u>是什么，以及前提被破坏时该换成什么。</strong>"
            "这也是为什么第 2 节的循环不变量比模板本身更重要——<em>不变量就是前提的形式化表述</em>。",
        ),
        CALLOUT("warn", "<strong>不要在这门课里重复准备 C61-05 的内容。</strong>"
                        "IoU / GIoU、NMS / Soft-NMS、mAP 的插值计算、匈牙利匹配、Focal Loss 的手撕实现，"
                        "全部在 <strong>C61 模块 05</strong>，那里有完整的代码与追问预案。"
                        "<em>本模块的定位是「那些代码的底层积木」——区间、双指针、排序扫描、积分图。"
                        "两门课合起来才是完整的 coding 准备，分开准备会重复投入。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("数组与字符串算法是教科书里最「已完成」的一章，但仍然有几个值得知道的活跃问题——"
          "它们不会出现在一面里，却能在「你平时关注什么」的闲聊里显出你的深度。"),
        UL([
            "<strong>缓存友好性正在超越渐近复杂度。</strong>在现代 CPU 上，"
            "一个 $O(n\\log n)$ 但访存随机的算法，常常慢于 $O(n^2)$ 但顺序访存的算法（在 $n$ 不太大时）。"
            "<em>双指针与滑动窗口之所以在实践中极快，很大程度上是因为它们是<u>顺序扫描</u>，"
            "对预取器（prefetcher）极其友好；而哈希表虽然摊还 $O(1)$，每次查找都是一次可能的 cache miss。</em>"
            "<strong>这个差距在 ML 后处理里是可测量的</strong>——把候选框按空间排序后再做 NMS，"
            "有时比不排序快，尽管复杂度没变。",
            "<strong>SIMD 与向量化让「常数」重新变成主角。</strong>numpy 的向量化、"
            "AVX-512、以及 ARM NEON（车端 SoC 上就是它）能把顺序扫描类算法加速 8–32 倍。"
            "<em>问题是：哪些算法可以向量化？前缀和有并行扫描（parallel scan / Blelloch）算法，"
            "但双指针的 <code>left</code> 更新是<u>数据依赖</u>的，天然难向量化。</em>"
            "<strong>「可向量化性」正在成为算法选择的一个新维度，而教科书还没跟上。</strong>",
            "<strong>字符串匹配的实际最优解仍在演化。</strong>理论上 KMP 是 $O(n+m)$，"
            "但实践中 <code>memmem</code> / Boyer-Moore / SIMD 加速的两字节过滤常常更快。"
            "<em>这是「渐近最优 ≠ 实际最优」最经典的案例，也是面试里一个很好的诚实回答素材：</em>"
            "「我知道 KMP 是 $O(n+m)$，但如果是生产代码我会先测一下标准库的实现，"
            "它通常已经做了 SIMD 优化。」",
            "<strong>流式/在线版本的算法缺少系统教材。</strong>本模块所有算法都假设数据在内存里、可以随意回头看。"
            "<em>但在车端，帧是流式到来的，你不能存下所有历史。滑动窗口天然适合流式（这也是它在时序融合里被大量使用的原因），"
            "而前缀和需要存整个数组。</em><strong>「把一个离线算法改成在线算法」是感知工程的日常，"
            "却几乎不出现在算法教材里</strong>——这也是 C55-04 的时序融合那一节要单独讲的原因。",
            "<strong>LLM 会不会让这类题彻底退场？</strong>目前的观察是：题目本身在贬值，"
            "但<em>「读懂一段别人写的双指针代码并指出它的不变量在哪一行被破坏」</em>这类任务在升值。"
            "<strong>本模块的「暴力解 + 对拍」训练的正是这种验证能力</strong>——"
            "当代码变得廉价，验证代码的能力就变成瓶颈。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Cormen, Leiserson, Rivest, Stein, <em>Introduction to Algorithms</em>（CLRS, 4th ed.）"
                         "<strong>第 2.1 节「Insertion sort」里的循环不变量框架</strong>——只读那三页，"
                         "初始化/保持/终止这三步就是本模块第 2 节的全部理论来源。"
                         "<strong>★</strong> Viola &amp; Jones, <em>Rapid Object Detection using a Boosted Cascade of Simple Features</em>（CVPR 2001）"
                         "——<strong>积分图（integral image）的出处</strong>，读第 2.1 节即可；"
                         "「用 $O(1)$ 的矩形求和换取实时性」这个思路今天仍然在用。"
                         "<strong>★</strong> Crow, <em>Summed-Area Tables for Texture Mapping</em>（SIGGRAPH 1984）——"
                         "同一个数据结构在图形学里的更早出处，说明这是被独立发明了两次的想法。</p>"
                         "<p>配套材料：Skiena, <em>The Algorithm Design Manual</em>（3rd ed.）第 3 章（数据结构选择）；"
                         "Blelloch, <em>Prefix Sums and Their Applications</em>（1990，并行前缀和，理解「为什么前缀和可以向量化而双指针不行」）。"
                         "相邻课程：<strong>模块 00</strong>（六步协议与时间预算）、<strong>模块 02</strong>（哈希、排序与二分：本模块的「排序 + 扫描」在那里被展开）、"
                         "<strong>模块 04</strong>（DP 与贪心：NMS 建模成加权区间调度）、"
                         "<strong>C61 模块 05</strong>（IoU/NMS/mAP 手撕，本模块不重复）、"
                         "<strong>C55 模块 04</strong>（时序融合：滑动窗口的工程形态）、"
                         "<strong>C57 模块 04</strong>（切片推理：跨片合并里的区间与并查集）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 01 · 数组与字符串（双指针 / 滑动窗口 / 前缀和 · 13 题暴力对拍）

目标：把「模板背得出」升级成「不变量说得清、边界测得到、暴力解对得上」。
面试里真正被评分的不是你写得多快，而是**你凭什么相信自己写对了**。

本 notebook 你会亲手实现：

1. **双指针三形态**：对撞（两数之和 II、盛最多水的容器）、快慢/读写（移除元素、有序去重）、同向（区间交集）
2. **把循环不变量跑成 assert**：穷举所有小规模输入，逐轮验证「最优解仍在 `[lo, hi]` 内」——
   这是「移动短板不漏解」的**执行级证明**，不是感觉
3. **滑动窗口三套模板**：定长、可变求最长、可变求最短；并**把两个经典 bug 跑出来**
   （漏掉 `last[ch] >= left`、数组含负数时窗口塌掉）
4. **前缀和与差分**：和为 K 的子数组、除自身以外数组的乘积、区间加
5. **二维前缀和 = 积分图**：$O(1)$ 求任意矩形和，并把**整数溢出与 float32 精度丢失**跑成数字
6. **13 道经典题的暴力解 vs 最优解随机对拍**（每题标注频率与层级）
7. **复杂度断言**：用**操作计数**（确定性）而不是墙钟时间（有噪声）证明 $O(n)$ 与 $O(n^2)$ 的分野
8. **边界用例总表**：空 / 单元素 / 全相同 / 极值 / 重复 / 溢出，一次全过

> 心智模型：**双指针与滑动窗口的正确性来自「每一步排除的候选一定不含最优解」；
> 前缀和的正确性来自「差分可逆」。这两句话就是这一模块的全部理论。**

> 与 **C61 模块 05** 的分工：IoU / GIoU、NMS / Soft-NMS、mAP、匈牙利匹配的手撕实现在那里，
> 本 notebook 只练**它们的底层积木**（区间、双指针、排序扫描、积分图），不重复。"""),

    md("""## 1 · 双指针三形态

三种形态，三种不变量。**先说不变量，再写代码** —— 面试里这个顺序本身就是加分项。

| 形态 | 指针关系 | 适用信号 | 不变量的形状 |
|---|---|---|---|
| 对撞 two-pointer | 一头一尾，向内收 | 有序数组 + 两数配对 / 容器类极值 | 「答案的两个下标都在 `[lo, hi]` 内」 |
| 快慢 / 读写 | 同起点，读快写慢 | **原地**修改、$O(1)$ 空间 | 「`a[:w]` 是已确认的结果，顺序不变」 |
| 同向 | 两个序列各一个 | 两个有序序列求交/并/差 | 「先结束的那个不可能再与对方后续相交」 |"""),

    code("""import sys, time, random
from collections import Counter, defaultdict, deque
import numpy as np

print('Python', sys.version.split()[0], '| numpy', np.__version__)


# ══════════ 形态一：对撞指针 ══════════

def two_sum_sorted(a, t):
    \"\"\"[高频/必会] 有序数组的两数之和，返回一对下标 (i, j)，不存在返回 None。
       不变量 I：若存在和为 t 的一对，则它的两个下标都落在闭区间 [lo, hi] 内。\"\"\"
    lo, hi = 0, len(a) - 1
    while lo < hi:
        s = a[lo] + a[hi]
        if s == t:
            return (lo, hi)
        if s < t:
            lo += 1        # a[lo] 配 [lo+1,hi] 里任何元素都 <= s < t → 排除 lo，I 保持
        else:
            hi -= 1        # a[hi] 配 [lo,hi-1] 里任何元素都 >= s > t → 排除 hi，I 保持
    return None            # 区间空 ⇒ 由 I，无解


def max_area(h):
    \"\"\"[高频/必会] 盛最多水的容器。面积 = 宽 x 短板，所以「移动短板」是唯一安全的选择。
       不变量 I：在 [lo, hi] 内一定存在一对达到全局最优面积的柱子。\"\"\"
    lo, hi, best = 0, len(h) - 1, 0
    while lo < hi:
        best = max(best, (hi - lo) * min(h[lo], h[hi]))
        if h[lo] < h[hi]:
            lo += 1        # 短板是 lo：它与任何更靠内的柱子配对，宽更小、短板不会更高 → 不可能更优
        else:
            hi -= 1
    return best


a_sorted = [2, 3, 4, 7, 11, 15]
print('a =', a_sorted)
print('two_sum_sorted(a, 9)  =', two_sum_sorted(a_sorted, 9), ' → 值', 2, '+', 7)
print('two_sum_sorted(a, 100) =', two_sum_sorted(a_sorted, 100))
assert two_sum_sorted(a_sorted, 9) == (0, 3)
assert two_sum_sorted(a_sorted, 100) is None

H = [1, 8, 6, 2, 5, 4, 8, 3, 7]
print('\\nmax_area(%s) = %d   （下标 1 与 8：宽 7 x 短板 7）' % (H, max_area(H)))
assert max_area(H) == 49
print('\\n⚠️ 无序数组的两数之和不能用对撞指针（排序会毁掉原下标）→ 必须用哈希，见模块 02。')
print('   面试里先问一句「数组有序吗？要返回下标还是值？」，直接决定用哪套算法。')"""),

    code("""# ══════════ 形态二：快慢 / 读写双指针（原地修改，O(1) 空间）══════════

def remove_element(a, val):
    \"\"\"[高频/必会] 原地移除所有等于 val 的元素，返回新长度 k；a[:k] 即结果。
       不变量：a[:w] 是已确认保留的元素且相对顺序不变；a[w:r] 是可以被覆盖的坑。\"\"\"
    w = 0                          # 下一个待写入的位置
    for r in range(len(a)):        # r 是读指针，永不回头
        if a[r] != val:
            a[w] = a[r]
            w += 1
    return w


def remove_duplicates_sorted(a):
    \"\"\"[高频/必会] 有序数组原地去重，返回新长度。
       不变量：a[:w] 已去重且有序，a[w-1] 是目前保留的最大值。\"\"\"
    if not a:
        return 0
    w = 1
    for r in range(1, len(a)):
        if a[r] != a[w - 1]:       # 与「已保留的最后一个」比，而不是与 a[r-1] 比
            a[w] = a[r]
            w += 1
    return w


def move_zeroes(a):
    \"\"\"[中频/必会] 把 0 全部移到末尾，非零元素保持相对顺序。返回非零个数。\"\"\"
    w = 0
    for r in range(len(a)):
        if a[r] != 0:
            a[w], a[r] = a[r], a[w]    # 交换而不是覆盖 ⇒ 尾部自然被 0 填满
            w += 1
    return w


buf = [3, 2, 2, 3, 4]
k = remove_element(buf, 3)
print('remove_element([3,2,2,3,4], 3) → k =', k, ' a[:k] =', buf[:k], ' 整个 buf =', buf)
assert (k, buf[:k]) == (3, [2, 2, 4])

buf2 = [0, 0, 1, 1, 1, 2, 2, 3]
k2 = remove_duplicates_sorted(buf2)
print('remove_duplicates_sorted →', k2, buf2[:k2])
assert (k2, buf2[:k2]) == (4, [0, 1, 2, 3])

buf3 = [0, 1, 0, 3, 12]
k3 = move_zeroes(buf3)
print('move_zeroes([0,1,0,3,12]) →', buf3, ' 非零个数', k3)
assert buf3 == [1, 3, 12, 0, 0] and k3 == 3

print('\\n✅ 三题共用一条骨架：**读指针扫全程，写指针只在「确认保留」时前进**。')
print('   面试追问预案：「返回长度还是新数组？」「a[k:] 里的垃圾值算不算问题？」')
print('   「要不要保持相对顺序？」（不要求顺序时可以用首尾交换，写更少的次数）')"""),

    code("""# ══════════ 形态三：同向双指针（两个有序序列）+ 排序后扫描 ══════════

def interval_intersection(A, B):
    \"\"\"[中频/必会] A、B 各自升序且互不相交，求所有交集。O(m+n)。
       不变量：右端点更小的那个区间，不可能再与对方的**后续**区间相交 → 让它前进。
       这正是 IoU 在单个坐标轴上的投影（完整 IoU/GIoU 实现见 C61-05，本课不重复）。\"\"\"
    i = j = 0
    out = []
    while i < len(A) and j < len(B):
        lo = max(A[i][0], B[j][0])          # 交集左端 = 两个左端的较大者
        hi = min(A[i][1], B[j][1])          # 交集右端 = 两个右端的较小者
        if lo <= hi:                        # 单点交集算不算？先问面试官，这里算
            out.append([lo, hi])
        if A[i][1] < B[j][1]:
            i += 1
        else:
            j += 1
    return out


def merge_intervals(iv):
    \"\"\"[高频/必会] 区间合并。按左端点排序后一遍扫描 —— 这就是「排序 + 扫描」模式。
       不变量：out 内区间两两不重叠且升序，且**只有 out[-1] 可能被下一个区间扩展**。\"\"\"
    out = []
    for s, e in sorted(iv):                 # 排序建立全序，后面的扫描只需看 out[-1]
        if out and s <= out[-1][1]:         # 相接（s == out[-1][1]）算不算重叠？必须先问
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def merge_intervals_brute(iv):
    \"\"\"暴力：反复找任意一对相交的区间合并掉，直到不再有变化。O(n^3) 但显然正确。\"\"\"
    cur = [list(x) for x in iv]
    changed = True
    while changed:
        changed = False
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                x, y = cur[i], cur[j]
                if x[0] <= y[1] and y[0] <= x[1]:
                    cur[i] = [min(x[0], y[0]), max(x[1], y[1])]
                    cur.pop(j)
                    changed = True
                    break
            if changed:
                break
    return sorted(cur)


A_iv = [[0, 2], [5, 10], [13, 23], [24, 25]]
B_iv = [[1, 5], [8, 12], [15, 24], [25, 26]]
print('A =', A_iv)
print('B =', B_iv)
print('交集 =', interval_intersection(A_iv, B_iv))
assert interval_intersection(A_iv, B_iv) == [[1, 2], [5, 5], [8, 10], [15, 23], [24, 24], [25, 25]]

raw = [[1, 3], [2, 6], [8, 10], [15, 18]]
print('\\nmerge_intervals(%s) = %s' % (raw, merge_intervals(raw)))
assert merge_intervals(raw) == [[1, 6], [8, 10], [15, 18]]
assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]        # 相接 → 合并
assert merge_intervals([[1, 4], [5, 6]]) == [[1, 4], [5, 6]]
assert merge_intervals([[1, 9], [2, 3]]) == [[1, 9]]        # 完全包含
print('\\n📌 「排序 + 扫描」是贪心 NMS 的同一个骨架：')
print('   排序建立全序 → 扫描时用「已选集合」做局部约束检查。')
print('   模块 04 会把 NMS 建模成加权区间调度并用 DP 求最优解，量化贪心的次优程度。')"""),

    md("""## 2 · 把循环不变量跑成 assert

「移动短板不漏解」这句话，绝大多数人只会**背**。下面把它变成可执行的证明：

- 不变量 $I$：**全局最优面积要么已经被记进 `best`，要么由当前区间 $[lo, hi]$ 内的某一对柱子达到。**
  形式化就是 $\\max(\\mathtt{best},\\;\\mathrm{opt}[lo,hi]) = \\mathrm{opt}$。
  （注意不能写成「最优解一定还在 $[lo,hi]$ 内」——`best` 记下它之后，它就被允许离开区间了。
  **这个「要么已记录、要么还在候选里」的两分式，是所有扫描型算法不变量的通用形状。**）
- 初始化：`best = 0`，$[0, n-1]$ 是全部候选，$I$ 显然成立。
- 保持：设 $h[lo] < h[hi]$。任何以 $lo$ 为一端的配对 $(lo, j)$ 都满足
  面积 $= (j-lo)\\cdot\\min(h[lo],h[j]) \\le (hi-lo)\\cdot h[lo]$，而后者已被记入 `best`。
  所以**排除 $lo$ 不会丢掉尚未被记录的更优解**，$I$ 保持。
- 终止：$hi - lo$ 每轮严格减 1，至多 $n-1$ 轮。终止时 `best` 已等于最优。

下面这个带检查的版本，在**每一轮循环开始时**用 $O(n^2)$ 暴力重算「区间内最优」，
与全局最优比对 —— 如果不变量在任何一轮被破坏，assert 会当场炸掉。"""),

    code("""def max_area_checked(h):
    \"\"\"带不变量检查的版本（教学用，O(n^3)）。\"\"\"
    def best_in(lo, hi):
        \"\"\"暴力：闭区间 [lo, hi] 内所有配对的最大面积。\"\"\"
        return max([(j - i) * min(h[i], h[j])
                    for i in range(lo, hi + 1) for j in range(i + 1, hi + 1)], default=0)

    opt = best_in(0, len(h) - 1)          # 全局最优（暴力算出，作为真值）
    lo, hi, best = 0, len(h) - 1, 0
    rounds = 0
    while lo < hi:
        # 不变量 I：最优解「要么已记进 best，要么仍由 [lo, hi] 内的某一对达到」
        assert max(best, best_in(lo, hi)) == opt, ('不变量 I 被破坏！', h, lo, hi, best)
        best = max(best, (hi - lo) * min(h[lo], h[hi]))
        if h[lo] < h[hi]:
            lo += 1
        else:
            hi -= 1
        rounds += 1
    assert best == opt, (h, best, opt)
    assert rounds == max(len(h) - 1, 0), '每轮区间长度严格减 1 ⇒ 恰好 n-1 轮'
    return best


# 穷举验证：长度 2..7、高度取值 0..3 的随机样本 + 全部长度 2..5 的完整穷举
import itertools
n_checked = 0
for n in (2, 3, 4, 5):
    for h in itertools.product(range(4), repeat=n):     # 4^2 + 4^3 + 4^4 + 4^5 = 1360 个
        max_area_checked(list(h))
        n_checked += 1
_r = random.Random(0)
for _ in range(400):
    n = _r.randint(2, 7)
    max_area_checked([_r.randint(0, 20) for _ in range(n)])
    n_checked += 1
print('✅ 在', n_checked, '个输入上，循环不变量每一轮都成立，且结果 == 暴力最优。')
print('   这不是「测了几个例子」——长度 <= 5 的输入是**穷举完了**的。')
print('\\n面试里怎么用：说完「移动短板」之后补一句')
print('   「因为以短板为端点的所有配对都不会超过当前面积，所以排除它不漏解」，')
print('   这一句话把答案从「背过」变成「证明过」，是最便宜的加分。')"""),

    md("""## 3 · 滑动窗口：三套模板与两个经典 bug

三套模板的差别只在**两行**：窗口状态怎么维护、结算写在哪里。

| 模板 | 收缩条件 | 结算位置 | 代表题 |
|---|---|---|---|
| 定长 | `r - left + 1 > k`（一进一出） | 每次滑动后 | 定长子数组最大和 |
| 可变 · 求**最长** | 窗口**非法**时收缩 | 收缩之后（此时窗口合法） | 最长无重复子串 |
| 可变 · 求**最短** | 窗口**合法**时就继续收缩 | 收缩**之前**（写在 `while` 里） | 长度最小的子数组 |

**可变窗口成立的前提**：`left` 只右移不回退。这要求「窗口扩大 ⇒ 条件单调变化」。
数组含负数时求「和 >= target」就不满足 —— 下面把这个 bug 跑出来。"""),

    code("""# ── 模板一：定长窗口（一进一出）──

def max_sum_window(a, k):
    \"\"\"[中频/必会] 定长 k 的窗口最大和。k > n 或 k <= 0 时返回 None。\"\"\"
    n = len(a)
    if k <= 0 or k > n:
        return None
    s = sum(a[:k])                 # 先装满
    best = s
    for r in range(k, n):
        s += a[r] - a[r - k]       # 一进一出：窗口和 O(1) 维护，不重新求和
        best = max(best, s)
    return best


def max_sum_window_brute(a, k):
    n = len(a)
    if k <= 0 or k > n:
        return None
    return max(sum(a[i:i + k]) for i in range(n - k + 1))


aw = [1, -2, 3, 4, -1, 2]
for kk in (1, 3, 6, 7):
    print('k=%d  max_sum_window=%s  brute=%s' % (kk, max_sum_window(aw, kk), max_sum_window_brute(aw, kk)))
    assert max_sum_window(aw, kk) == max_sum_window_brute(aw, kk)
print('\\n工程同构：TSR 时序融合里「最近 K 帧这个 track 被检出几次」「置信度的移动平均」')
print('   就是定长窗口计数与求和（见 C55-04）。流式数据天然适合定长窗口 —— 只需 O(k) 内存。')"""),

    code("""# ── 模板二：可变窗口求最长 —— 以及那个漏掉就错的判断 ──

def longest_unique(s):
    \"\"\"[高频/必会] 最长无重复字符子串的长度。
       不变量：s[left : r+1] 内无重复字符。last[ch] 是 ch 最后一次出现的下标。\"\"\"
    last = {}
    left = best = 0
    for r, ch in enumerate(s):
        if ch in last and last[ch] >= left:    # ← 关键：只有落在**当前窗口内**才需要收缩
            left = last[ch] + 1                #    left 只右移，绝不回退
        last[ch] = r
        best = max(best, r - left + 1)
    return best


def longest_unique_buggy(s):
    \"\"\"少了 `last[ch] >= left` 这半个条件 —— left 会回退，窗口里就混进了重复字符。\"\"\"
    last = {}
    left = best = 0
    for r, ch in enumerate(s):
        if ch in last:
            left = last[ch] + 1
        last[ch] = r
        best = max(best, r - left + 1)
    return best


def longest_unique_brute(s):
    best = 0
    for i in range(len(s)):
        seen = set()
        for j in range(i, len(s)):
            if s[j] in seen:
                break
            seen.add(s[j])
            best = max(best, j - i + 1)
    return best


print('s = "abba"')
print('  正确实现 =', longest_unique('abba'), '   （"ab" 或 "ba"）')
print('  漏判实现 =', longest_unique_buggy('abba'), '  ← 错！它把 left 从 2 拉回了 1，窗口变成 "bba"')
assert longest_unique('abba') == 2 and longest_unique_buggy('abba') == 3

_r3 = random.Random(1)
bad_cnt = 0
for _ in range(2000):
    s = ''.join(_r3.choice('abc') for _ in range(_r3.randint(0, 10)))
    assert longest_unique(s) == longest_unique_brute(s), s
    if longest_unique_buggy(s) != longest_unique_brute(s):
        bad_cnt += 1
print('\\n✅ 正确实现与暴力解 2000 组随机对拍一致；漏判实现有', bad_cnt, '组不一致。')
print('   ↑ 这就是为什么必须写暴力对拍：这个 bug 在 "abc"、"aab" 这种小例子上是看不出来的。')"""),

    code("""# ── 模板三：可变窗口求最短 —— 以及「有负数就塌掉」──

def min_subarray_len(a, target):
    \"\"\"[高频/必会] 和 >= target 的最短连续子数组长度，不存在返回 0。**要求元素非负**。
       结算写在 while 里：每次收缩前的窗口都是「以 r 结尾的合法窗口中最短的那个」。\"\"\"
    left = 0
    s = 0
    best = len(a) + 1
    for r, x in enumerate(a):
        s += x
        while s >= target:                 # 合法就继续收缩，直到再收缩就不合法
            best = min(best, r - left + 1)
            s -= a[left]
            left += 1
    return 0 if best == len(a) + 1 else best


def min_subarray_len_brute(a, target):
    n = len(a)
    best = n + 1
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += a[j]
            if s >= target:
                best = min(best, j - i + 1)
                break                      # 元素非负 ⇒ 再往右只会更长
    return 0 if best == n + 1 else best


_r4 = random.Random(2)
for _ in range(2000):
    a = [_r4.randint(0, 6) for _ in range(_r4.randint(0, 10))]
    t = _r4.randint(1, 15)
    assert min_subarray_len(a, t) == min_subarray_len_brute(a, t), (a, t)
print('✅ 非负数组上 2000 组对拍一致。')

# ── 前提被破坏：数组含负数 ──
neg = [1, -1, 5]
def brute_any(a, target):
    n = len(a); best = n + 1
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += a[j]
            if s >= target:
                best = min(best, j - i + 1)      # 不能 break：后面可能还有更短的
    return 0 if best == n + 1 else best

print('\\na =', neg, ' target = 5')
print('  滑动窗口给出 =', min_subarray_len(neg, 5), '  ← 错')
print('  真实最短     =', brute_any(neg, 5), '  （就是 [5] 本身，长度 1）')
assert min_subarray_len(neg, 5) == 3 and brute_any(neg, 5) == 1
print('\\n❗ 根因：负数让「窗口变大 ⇒ 和变大」不再成立，left 右移后可能又出现合法窗口，')
print('   但 left 已经不能回退了。**有负数就换前缀和 + 哈希（见下一节），不要硬套滑窗。**')
print('   面试里主动说出这个前提，比写对代码更能显示你理解了算法而不是背了模板。')"""),

    code("""# ── 可变窗口 + 计数器：最小覆盖子串（面试里的滑窗天花板题）──

def min_window(s, t):
    \"\"\"[中频/加分] s 中包含 t 全部字符（计重数）的最短子串；不存在返回 ''。
       need[ch]：还需要几个 ch（可以为负 ⇒ 窗口内有多余的 ch，可以被收缩掉）。
       missing：还差多少个字符才凑齐 —— 只有它归零，窗口才合法。\"\"\"
    if not t or len(t) > len(s):
        return ''
    need = Counter(t)
    missing = len(t)
    left = 0
    best = (len(s) + 1, 0, 0)          # (长度, 起点, 终点+1)
    for r, ch in enumerate(s):
        if need[ch] > 0:               # 只有「还需要」的字符才让 missing 减少
            missing -= 1
        need[ch] -= 1                  # 多余的字符变成负数，这是收缩的判据
        if missing == 0:
            while need[s[left]] < 0:   # 左端是多余字符 → 收缩
                need[s[left]] += 1
                left += 1
            if r - left + 1 < best[0]:  # 严格小于 ⇒ 并列时保留最左的那个（结果确定）
                best = (r - left + 1, left, r + 1)
    return '' if best[0] > len(s) else s[best[1]:best[2]]


def min_window_brute(s, t):
    need = Counter(t)
    for L in range(len(t), len(s) + 1):            # 按长度从小到大
        for i in range(0, len(s) - L + 1):         # 同长度按起点从左到右
            if not (need - Counter(s[i:i + L])):   # Counter 相减：不够就会留下正项
                return s[i:i + L]
    return ''


print('min_window("ADOBECODEBANC", "ABC") =', repr(min_window('ADOBECODEBANC', 'ABC')))
assert min_window('ADOBECODEBANC', 'ABC') == 'BANC'
assert min_window('a', 'aa') == '' and min_window('a', 'a') == 'a'

_r5 = random.Random(5)
for _ in range(1200):
    s = ''.join(_r5.choice('abc') for _ in range(_r5.randint(0, 9)))
    t = ''.join(_r5.choice('abc') for _ in range(_r5.randint(1, 3)))
    assert min_window(s, t) == min_window_brute(s, t), (s, t)
print('✅ 1200 组随机对拍一致（含大量「t 有重复字符」的用例 —— 这正是最容易写错的地方）。')
print('   追问预案：「t 里有重复字符怎么办？」→ 计重数，用 Counter 而不是 set。')"""),

    md("""## 4 · 前缀和与差分：把「区间查询」压成 O(1)

一句话：**前缀和把「区间求和」变成两点相减；差分把「区间修改」变成两点相加。二者互为逆运算。**

$$P[i] = \\sum_{k<i} a[k], \\qquad \\sum_{k=i}^{j} a[k] = P[j+1] - P[i]$$

`P` 比 `a` 长 1（`P[0] = 0` 代表空前缀）。**这个 `+1` 是本节所有 off-by-one 的唯一来源**，
写代码前先在纸上写下 `P` 的长度和 `P[0]` 的含义，能省掉一半调试时间。

| 需求 | 数据结构 | 建表 | 单次查询/修改 |
|---|---|---|---|
| 静态数组，多次区间**求和** | 前缀和 | $O(n)$ | $O(1)$ |
| 多次区间**加**，最后统一读 | 差分数组 | $O(1)$/次 | 还原 $O(n)$ |
| **边改边查** | 树状数组 BIT / 线段树 | $O(n)$ | $O(\\log n)$ |
| 二维静态区域和 | 二维前缀和（积分图） | $O(HW)$ | $O(1)$ |"""),

    code("""def prefix_sum(a):
    \"\"\"P[i] = a[0..i-1] 之和。len(P) == len(a) + 1，P[0] == 0（空前缀）。\"\"\"
    P = [0] * (len(a) + 1)
    for i, x in enumerate(a):
        P[i + 1] = P[i] + x
    return P


def subarray_sum_k(a, k):
    \"\"\"[高频/必会] 和恰为 k 的子数组个数。**有负数也成立**（这正是它替代滑窗的场景）。
       seen[前缀和] = 该前缀和出现过几次；seen = {0: 1} 表示「空前缀」，漏了它就少算以下标 0 开头的解。\"\"\"
    seen = {0: 1}
    s = cnt = 0
    for x in a:
        s += x
        cnt += seen.get(s - k, 0)          # 以当前元素结尾、和为 k 的子数组个数
        seen[s] = seen.get(s, 0) + 1
    return cnt


def subarray_sum_k_brute(a, k):
    return sum(1 for i in range(len(a)) for j in range(i, len(a)) if sum(a[i:j + 1]) == k)


av = [1, 2, 3, -3, 3]
P = prefix_sum(av)
print('a =', av)
print('P =', P, '  ← 长度 = len(a)+1')
print('a[1..3] 之和 = P[4]-P[1] =', P[4] - P[1], ' 校验', sum(av[1:4]))
assert P[4] - P[1] == sum(av[1:4])

print('\\nsubarray_sum_k([1,2,3,-3,3], 3) =', subarray_sum_k(av, 3), ' brute =', subarray_sum_k_brute(av, 3))
_r6 = random.Random(7)
for _ in range(2000):
    a = [_r6.randint(-4, 4) for _ in range(_r6.randint(0, 9))]
    k = _r6.randint(-5, 5)
    assert subarray_sum_k(a, k) == subarray_sum_k_brute(a, k), (a, k)
print('✅ 2000 组随机对拍一致（含负数与 k=0）。')
print('   边界点名：subarray_sum_k([0,0,0], 0) =', subarray_sum_k([0, 0, 0], 0), '（6 个子数组全都和为 0）')
assert subarray_sum_k([0, 0, 0], 0) == 6"""),

    code("""# ── 差分数组：m 次区间加，从 O(mn) 压到 O(m + n) ──

def range_add(n, ops):
    \"\"\"[低频/加分] ops = [(l, r, v)]，闭区间 [l, r] 每个位置加 v。返回最终数组。
       d 多开一格专门接 d[r+1]：r = n-1 时正好落在这一格，不越界 —— 这是唯一的实现陷阱。\"\"\"
    d = [0] * (n + 1)
    for l, r, v in ops:
        d[l] += v
        d[r + 1] -= v
    out = [0] * n
    run = 0
    for i in range(n):
        run += d[i]                 # 前缀和还原：差分与前缀和互为逆运算
        out[i] = run
    return out


def range_add_brute(n, ops):
    out = [0] * n
    for l, r, v in ops:
        for i in range(l, r + 1):
            out[i] += v
    return out


ops_demo = [(0, 2, 5), (1, 4, -3), (4, 4, 10)]
print('n=5, ops =', ops_demo)
print('差分实现 =', range_add(5, ops_demo))
print('暴力实现 =', range_add_brute(5, ops_demo))
assert range_add(5, ops_demo) == range_add_brute(5, ops_demo)

_r7 = random.Random(9)
for _ in range(2000):
    n = _r7.randint(1, 8)
    ops = [(lambda l: (l, _r7.randint(l, n - 1), _r7.randint(-5, 5)))(_r7.randint(0, n - 1))
           for _ in range(_r7.randint(0, 5))]
    assert range_add(n, ops) == range_add_brute(n, ops), (n, ops)
print('✅ 2000 组随机对拍一致。')
print('\\n⚠️ 差分只支持「先全改完，最后一次性读」。**需要边改边查就必须上树状数组 BIT**，')
print('   查询与修改都变成 O(log n)。面试里说出这条分界线，比写出差分本身更值钱。')"""),

    code("""# ── 前缀积 / 后缀积：除自身以外数组的乘积（不许用除法）──

def product_except_self(a):
    \"\"\"[中频/加分] out[i] = 除 a[i] 以外全部元素之积。禁止除法（数组里有 0 就没法除）。
       两遍扫描：第一遍把「左边所有元素之积」写进 out，第二遍用一个变量滚「右边之积」。
       输出数组不计入额外空间 ⇒ 额外空间 O(1)。\"\"\"
    n = len(a)
    out = [1] * n
    for i in range(1, n):
        out[i] = out[i - 1] * a[i - 1]      # 不变量：out[i] == a[0..i-1] 之积
    suf = 1
    for i in range(n - 1, -1, -1):
        out[i] *= suf                       # 左积 x 右积
        suf *= a[i]
    return out


def product_except_self_brute(a):
    out = []
    for i in range(len(a)):
        p = 1
        for j in range(len(a)):
            if j != i:
                p *= a[j]
        out.append(p)
    return out


print('product_except_self([1,2,3,4]) =', product_except_self([1, 2, 3, 4]))
print('含一个 0：      [1,0,3]        →', product_except_self([1, 0, 3]))
print('含两个 0：      [0,0,3]        →', product_except_self([0, 0, 3]))
assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]
assert product_except_self([1, 0, 3]) == [0, 3, 0]
assert product_except_self([0, 0, 3]) == [0, 0, 0]

_r8 = random.Random(13)
for _ in range(2000):
    a = [_r8.randint(-3, 3) for _ in range(_r8.randint(0, 7))]
    assert product_except_self(a) == product_except_self_brute(a), a
print('✅ 2000 组随机对拍一致（含 0、含负数、含空数组）。')
print('   追问预案：「用除法行不行？」→ 有 0 就不行；「有一个 0 呢？」→ 只有 0 那一位非零；')
print('   「有两个 0 呢？」→ 全为 0。这三问几乎必来，直接背下来。')"""),

    md("""## 5 · 二维前缀和 = CV 里的积分图

$$P[i][j] = \\sum_{r<i}\\sum_{c<j} M[r][c], \\qquad
\\mathrm{sum}(r_0..r_1,\\; c_0..c_1) = P[r_1{+}1][c_1{+}1] - P[r_0][c_1{+}1] - P[r_1{+}1][c_0] + P[r_0][c_0]$$

**四项容斥，$O(1)$，与矩形大小无关。** 这就是 Viola–Jones 在 2001 年做到实时人脸检测的核心技巧
（integral image / summed-area table）。在本岗位上它的用途：候选框内的前景像素占比、
区域均值与方差的快速粗筛、多尺度滑窗打分。

**两个必须在面试里主动提的数值风险**（这才是区分「刷过题」和「写过生产代码」的地方）：

- **整数溢出**：$1920\\times1080$、像素值 $\\le 255$ 的图，积分图右下角是
  $255\\times 1920\\times 1080 \\approx 5.3\\times10^8$ —— int32 装得下（上限 $2.1\\times10^9$）；
  但 **4K 图 $3840\\times2160$ 是 $2.115\\times10^9$，只剩 1.5% 余量**，
  而求区域方差要用的**平方和积分图**（$255^2$ 累加）会超出 int32 **250 倍**，必然溢出。用 int64。
- **float32 精度**：float32 的尾数只有 24 位，$2^{24}=16777216$ 之后**整数就不再连续**——
  $2^{24}+1$ 在 float32 里等于 $2^{24}$。积分图的累加值早就越过这条线了，
  于是「大矩形减大矩形」会得到明显错误的小差值（灾难性抵消）。"""),

    code("""def integral_image(M):
    \"\"\"二维前缀和 / 积分图。返回 (H+1, W+1) 的表，P[i, j] = M[:i, :j] 之和。
       多加的一行一列全 0 ⇒ 查询时边界不需要任何 if 判断，这是 padding 的全部意义。\"\"\"
    H, W = M.shape
    P = np.zeros((H + 1, W + 1), dtype=np.int64)
    P[1:, 1:] = M
    return P.cumsum(axis=0).cumsum(axis=1)


def rect_sum(P, r0, c0, r1, c1):
    \"\"\"闭区间 [r0, r1] x [c0, c1] 的和。四项容斥，O(1)。\"\"\"
    return int(P[r1 + 1, c1 + 1] - P[r0, c1 + 1] - P[r1 + 1, c0] + P[r0, c0])


M = np.arange(1, 13, dtype=np.int64).reshape(3, 4)
P2 = integral_image(M)
print('M =\\n', M)
print('P（注意第 0 行第 0 列全是 0）=\\n', P2)
print('\\nrect_sum(1,1,2,3) =', rect_sum(P2, 1, 1, 2, 3), ' 校验', int(M[1:3, 1:4].sum()))
assert rect_sum(P2, 1, 1, 2, 3) == int(M[1:3, 1:4].sum())
assert rect_sum(P2, 0, 0, 2, 3) == int(M.sum())
assert rect_sum(P2, 1, 2, 1, 2) == int(M[1, 2])      # 单元素矩形

# 随机对拍：任意矩阵 x 任意矩形
_r9 = random.Random(17)
for _ in range(3000):
    H, W = _r9.randint(1, 6), _r9.randint(1, 6)
    A = np.array([[_r9.randint(-9, 9) for _ in range(W)] for _ in range(H)], dtype=np.int64)
    PA = integral_image(A)
    r0 = _r9.randint(0, H - 1); r1 = _r9.randint(r0, H - 1)
    c0 = _r9.randint(0, W - 1); c1 = _r9.randint(c0, W - 1)
    assert rect_sum(PA, r0, c0, r1, c1) == int(A[r0:r1 + 1, c0:c1 + 1].sum())
print('\\n✅ 3000 组（矩阵 x 矩形）随机对拍一致，含单行/单列/单元素/整幅。')

# 工程用途：用积分图 O(1) 算候选框内的前景像素占比（粗筛掉明显不含标志的框）
mask = (np.arange(24 * 32).reshape(24, 32) % 7 == 0).astype(np.int64)   # 合成前景掩码
Pm = integral_image(mask)
boxes = [(2, 3, 9, 14), (10, 0, 23, 31), (0, 0, 1, 1)]
for (r0, c0, r1, c1) in boxes:
    area = (r1 - r0 + 1) * (c1 - c0 + 1)
    ratio = rect_sum(Pm, r0, c0, r1, c1) / area
    assert abs(ratio - float(mask[r0:r1 + 1, c0:c1 + 1].mean())) < 1e-12
    print('框 (%2d,%2d)-(%2d,%2d)  面积 %4d  前景占比 %.4f' % (r0, c0, r1, c1, area, ratio))
print('   ↑ 一次 O(HW) 建表之后，**任意多个框、任意大小，每个都是 4 次访存**。')"""),

    code("""# ══════════ 积分图的两个数值陷阱：跑出来，不要只背 ══════════

# 陷阱 1：整数溢出。np.cumsum 默认会把 int16 提升到平台整型（int64），
#         所以必须显式 dtype 才能复现真实 C/CUDA 代码里的溢出。
img = np.full((256, 256), 255, dtype=np.int16)
exact = 255 * 256 * 256
ii_16 = img.cumsum(axis=0, dtype=np.int16).cumsum(axis=1, dtype=np.int16)
ii_64 = img.cumsum(axis=0, dtype=np.int64).cumsum(axis=1, dtype=np.int64)
print('256x256 全 255 的图，积分图右下角应为', exact)
print('  int16 累加 →', int(ii_16[-1, -1]), '  ← 回绕（int16 上限 32767）')
print('  int64 累加 →', int(ii_64[-1, -1]), '  ← 正确')
assert int(ii_64[-1, -1]) == exact
assert int(ii_16[-1, -1]) != exact
print('  默认 dtype（不写 dtype）=', int(img.cumsum(axis=0).cumsum(axis=1)[-1, -1]),
      ' ← numpy 悄悄提升到 int64，掩盖了 bug')

print('\\n真实分辨率下的账（INT32_MAX = 2147483647）：')
for name, (h, w) in [('1280x720', (720, 1280)), ('1920x1080', (1080, 1920)), ('3840x2160', (2160, 3840))]:
    tot = 255 * h * w
    print('  %-10s 积分图上界 %13d   余量 %5.1f%%   int32 装得下？%s'
          % (name, tot, 100 * (1 - tot / (2**31 - 1)), tot <= 2**31 - 1))
assert 255 * 2160 * 3840 < 2**31 - 1                     # 4K 只剩 1.5% 余量
assert 255 * 2160 * 3840 > 0.98 * (2**31 - 1), '4K 图的积分图已经顶在 int32 边界上'
# 而「平方和积分图」（求区域方差要用）必然溢出 int32：
sq = 255**2 * 2160 * 3840
print('  4K 的**平方和**积分图上界 %d = %.0f 倍 INT32_MAX → 必然溢出'
      % (sq, sq / (2**31 - 1)))
assert sq > 2**31 - 1

# 陷阱 2：float32 的尾数只有 24 位 —— 2^24 之后整数不再连续
f = np.float32(2**24)
print('\\nfloat32: 2^24 =', f, '  2^24 + 1 =', f + np.float32(1), '  相等？', bool(f + np.float32(1) == f))
assert f + np.float32(1) == f
print('  ⇒ 积分图累加值一旦超过 16777216，float32 就开始丢整数；')
print('    而 720p 图的积分图上界是', 255 * 720 * 1280, '—— 早就越线了。')
print('    「大矩形减大矩形得到小差值」还会叠加灾难性抵消（catastrophic cancellation）。')
print('\\n✅ 结论（可直接在面试里说）：积分图一律用 int64 / uint32 / float64 建表，')
print('   绝不用 int32 存 4K、绝不用 float32 存积分图。这是一个真实会上线的 bug。')"""),

    md("""## 6 · 13 道经典题：暴力解 vs 最优解随机对拍

前五节已经把 13 道题全部实现完了。这一节做的事情只有一件：**把它们放进同一个对拍框架里跑一遍**。

为什么必须写暴力解？三个理由，面试里都能说：

1. **它是正确性的唯一免费真值。** 没有暴力解，你的「测试」只是几个手挑的例子。
2. **它是优化的起点。** 六步协议里「先给暴力解」不是走形式 —— 有了它才能讨论瓶颈在哪。
3. **随机对拍能抓到你想不到的用例。**（上面 `longest_unique_buggy` 就是被随机对拍抓出来的。）"""),

    code("""def duel(name, fast, brute, gen, trials=400):
    \"\"\"随机对拍：同一份输入喂给最优解与暴力解，输出必须完全一致。\"\"\"
    for _ in range(trials):
        args = gen()
        f, b = fast(*args), brute(*args)
        assert f == b, (name, args, f, b)
    print('  ✅ %-38s %d 轮随机对拍一致' % (name, trials))


rq = random.Random(2024)
ints = lambda lo, hi, n: [rq.randint(lo, hi) for _ in range(n)]

def gen_disjoint():
    \"\"\"生成一组升序且互不相交的整数区间（区间交集题的合法输入）。\"\"\"
    def one():
        pts = sorted(rq.sample(range(16), 2 * rq.randint(0, 4)))
        return [[pts[2 * k], pts[2 * k + 1]] for k in range(len(pts) // 2)]
    return (one(), one())

def gen_rect():
    H, W = rq.randint(1, 6), rq.randint(1, 6)
    A = np.array([ints(-9, 9, W) for _ in range(H)], dtype=np.int64)
    r0 = rq.randint(0, H - 1); r1 = rq.randint(r0, H - 1)
    c0 = rq.randint(0, W - 1); c1 = rq.randint(c0, W - 1)
    return (A, r0, c0, r1, c1)

def gen_ops():
    n = rq.randint(1, 8)
    ops = []
    for _ in range(rq.randint(0, 5)):
        l = rq.randint(0, n - 1)
        ops.append((l, rq.randint(l, n - 1), rq.randint(-5, 5)))
    return (n, ops)

# 为了让「返回一对下标」这类多解题可比，统一成 None / True，并在内部校验解的合法性
def two_sum_ok(a, t):
    r = two_sum_sorted(a, t)
    if r is None:
        return None
    i, j = r
    assert 0 <= i < j < len(a) and a[i] + a[j] == t, ('返回的不是合法解', a, t, r)
    return True

def two_sum_ok_brute(a, t):
    return True if any(a[i] + a[j] == t
                       for i in range(len(a)) for j in range(i + 1, len(a))) else None

# 原地修改类：包一层，不污染调用方数据，返回 (新长度, 结果切片)
rm_fast = lambda a, v: (lambda b: (lambda k: (k, b[:k]))(remove_element(b, v)))(list(a))
rm_brute = lambda a, v: (lambda c: (len(c), c))([x for x in a if x != v])
dd_fast = lambda a: (lambda b: (lambda k: (k, b[:k]))(remove_duplicates_sorted(b)))(list(a))
dd_brute = lambda a: (lambda c: (len(c), c))(sorted(set(a)))

print('对撞 / 快慢指针类：')
duel('① 两数之和 II（有序）[高频/必会]', two_sum_ok, two_sum_ok_brute,
     lambda: (sorted(ints(-6, 6, rq.randint(0, 9))), rq.randint(-9, 9)))
duel('② 盛最多水的容器 [高频/必会]', max_area,
     lambda h: max([(j - i) * min(h[i], h[j])
                    for i in range(len(h)) for j in range(i + 1, len(h))], default=0),
     lambda: (ints(0, 12, rq.randint(0, 9)),))
duel('③ 移除元素（原地）[高频/必会]', rm_fast, rm_brute,
     lambda: (ints(0, 4, rq.randint(0, 9)), rq.randint(0, 4)))
duel('④ 有序数组去重（原地）[高频/必会]', dd_fast, dd_brute,
     lambda: (sorted(ints(0, 5, rq.randint(0, 9))),))"""),

    code("""print('滑动窗口类：')
duel('⑤ 最长无重复子串 [高频/必会]', longest_unique, longest_unique_brute,
     lambda: (''.join(rq.choice('abcd') for _ in range(rq.randint(0, 12))),))
duel('⑥ 长度最小的子数组 [高频/必会]', min_subarray_len, min_subarray_len_brute,
     lambda: (ints(0, 6, rq.randint(0, 10)), rq.randint(1, 15)))
duel('⑦ 定长子数组最大和 [中频/必会]', max_sum_window, max_sum_window_brute,
     lambda: (ints(-8, 8, rq.randint(0, 10)), rq.randint(0, 6)))
duel('⑧ 最小覆盖子串 [中频/加分]', min_window, min_window_brute,
     lambda: (''.join(rq.choice('abc') for _ in range(rq.randint(0, 9))),
              ''.join(rq.choice('abc') for _ in range(rq.randint(1, 3)))))

print('\\n前缀和 / 差分 / 区间类：')
duel('⑨ 和为 K 的子数组 [高频/必会]', subarray_sum_k, subarray_sum_k_brute,
     lambda: (ints(-4, 4, rq.randint(0, 9)), rq.randint(-5, 5)))
duel('⑩ 除自身以外数组的乘积 [中频/加分]', product_except_self, product_except_self_brute,
     lambda: (ints(-3, 3, rq.randint(0, 7)),))
duel('⑪ 区间加（差分）[低频/加分]', range_add, range_add_brute, gen_ops)
duel('⑫ 区间合并 [高频/必会]', merge_intervals, merge_intervals_brute,
     lambda: ([[l, l + rq.randint(0, 4)] for l in ints(0, 12, rq.randint(0, 6))],))
duel('⑬ 区间交集（双数组）[中频/必会]', interval_intersection,
     lambda A, B: sorted([[max(x[0], y[0]), min(x[1], y[1])] for x in A for y in B
                          if max(x[0], y[0]) <= min(x[1], y[1])]), gen_disjoint)
duel('⑭ 二维前缀和求矩形和 [中频/必会]',
     lambda A, r0, c0, r1, c1: rect_sum(integral_image(A), r0, c0, r1, c1),
     lambda A, r0, c0, r1, c1: int(A[r0:r1 + 1, c0:c1 + 1].sum()), gen_rect)

print('\\n14 道题、5600 组随机输入，暴力解与最优解**逐一对拍通过**。')
print('这张表就是本模块的交付物：不是「看过」，是「实现过并验证过」。')"""),

    md("""## 7 · 复杂度断言：用操作计数，不用墙钟时间

面试里说复杂度靠嘴，代码里验证复杂度要靠**确定性的操作计数** ——
墙钟时间受 CPU 频率、GC、缓存状态影响，在 CI 里是不稳定的（这是真实会挂的测试）。

做法：在实现里塞一个计数器，然后看**计数随 $n$ 的增长率**。
对全不相同的输入序列，`longest_unique` 的循环体恰好执行 $n$ 次，
而暴力解恰好执行 $n(n+1)/2$ 次 —— 两个**精确等式**，可以直接 assert。"""),

    code("""def longest_unique_ops(s):
    \"\"\"带操作计数的滑窗版：ops 恰等于外层循环次数。\"\"\"
    ops = 0
    last = {}
    left = best = 0
    for r, ch in enumerate(s):
        ops += 1
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = r
        best = max(best, r - left + 1)
    return best, ops


def longest_unique_brute_ops(s):
    ops = 0
    best = 0
    for i in range(len(s)):
        seen = set()
        for j in range(i, len(s)):
            ops += 1
            if s[j] in seen:
                break
            seen.add(s[j])
            best = max(best, j - i + 1)
    return best, ops


print('输入：n 个互不相同的元素（这是暴力解的最坏情况，也是唯一公平的比较点）')
print('%8s %12s %14s %12s' % ('n', '滑窗 ops', '暴力 ops', '倍数'))
prev = None
for n in (200, 400, 800, 1600):
    s = list(range(n))                      # 全不相同
    b1, o1 = longest_unique_ops(s)
    b2, o2 = longest_unique_brute_ops(s)
    assert b1 == b2 == n                    # 答案都是 n
    assert o1 == n,               'O(n)：外层循环恰好 n 次'
    assert o2 == n * (n + 1) // 2, 'O(n^2)：等差和'
    print('%8d %12d %14d %12.1fx' % (n, o1, o2, o2 / o1))
    if prev:
        assert abs((o2 / prev) - 4.0) < 0.02, 'n 翻倍 ⇒ 暴力 ops 变成约 4 倍'
    prev = o2
print('\\n✅ 两条精确等式 + 「n 翻倍 ⇒ ops x4」的倍增检验，把 O(n) 与 O(n^2) 的差别**证明**了。')

# 双指针的操作次数同样是精确的：区间长度每轮减 1
def max_area_ops(h):
    lo, hi, ops = 0, len(h) - 1, 0
    while lo < hi:
        ops += 1
        if h[lo] < h[hi]:
            lo += 1
        else:
            hi -= 1
    return ops
for n in (10, 100, 1000):
    assert max_area_ops(list(range(n))) == n - 1
print('✅ 对撞指针：ops 恰好 n-1（每轮 hi-lo 严格减 1）⇒ 终止性也被验证了。')

t0 = time.perf_counter(); longest_unique_ops(list(range(20000))); t_fast = time.perf_counter() - t0
t0 = time.perf_counter(); longest_unique_brute_ops(list(range(2000))); t_brute = time.perf_counter() - t0
print('\\n参考墙钟（仅供感觉，不作断言）：滑窗 n=20000 用 %.1f ms；暴力 n=2000 用 %.1f ms。'
      % (t_fast * 1000, t_brute * 1000))
print('   注意口径：n 差 10 倍，暴力还更慢 —— 这就是 O(n) 与 O(n^2) 在 n=10^4 量级的现实差距。')"""),

    code("""# ══════════ 边界用例总表：一次全过 ══════════
# 面试里写完代码主动跑这六类，比面试官提醒你要好得多。

print('① 空输入')
assert two_sum_ok([], 5) is None
assert max_area([]) == 0 and max_area([1]) == 0
assert (lambda b: (remove_element(b, 1), b))([])[0] == 0
assert remove_duplicates_sorted([]) == 0
assert longest_unique('') == 0
assert min_subarray_len([], 5) == 0
assert max_sum_window([], 1) is None
assert subarray_sum_k([], 0) == 0
assert product_except_self([]) == []
assert merge_intervals([]) == [] and interval_intersection([], []) == []
assert min_window('', 'a') == ''
print('   全部 11 个入口在空输入上返回「有定义的空答案」，没有一个抛异常。')

print('\\n② 单元素')
assert max_area([7]) == 0                     # 一根柱子围不出面积
assert longest_unique('a') == 1
assert min_subarray_len([5], 5) == 1 and min_subarray_len([4], 5) == 0
assert max_sum_window([3], 1) == 3 and max_sum_window([3], 2) is None
assert product_except_self([9]) == [1]        # 「除自身以外」= 空积 = 1，这个答案要敢说
assert merge_intervals([[2, 3]]) == [[2, 3]]

print('\\n③ 全相同')
assert two_sum_ok([2, 2], 4) is True
assert max_area([5, 5, 5]) == 10              # 取最外两根：宽 2 x 高 5
assert longest_unique('aaaa') == 1
b = [2, 2, 2]; assert remove_element(b, 2) == 0
assert remove_duplicates_sorted([1, 1, 1]) == 1
assert subarray_sum_k([0, 0, 0], 0) == 6

print('\\n④ 极值 / 单调')
assert max_area([1, 2, 3, 4, 5]) == 6         # (0,4)=4x1  (1,4)=3x2  (2,4)=2x3  (3,4)=1x4 → 6
assert longest_unique('abcdef') == 6
assert min_subarray_len([1, 1, 1, 1], 4) == 4

print('\\n⑤ 重复元素与边界相接')
assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]        # 相接算重叠（必须先问面试官）
assert merge_intervals([[1, 4], [5, 6]]) == [[1, 4], [5, 6]]
assert merge_intervals([[1, 9], [2, 3]]) == [[1, 9]]        # 完全被包含
assert interval_intersection([[0, 2]], [[2, 5]]) == [[2, 2]]  # 单点交集
assert min_window('aa', 'aa') == 'aa' and min_window('a', 'aa') == ''

print('\\n⑥ 数值风险')
assert rect_sum(integral_image(np.full((3, 3), 10**9, dtype=np.int64)), 0, 0, 2, 2) == 9 * 10**9
print('   int64 积分图能装下 9e9（int32 会溢出）；float32 在 1.7e7 之后就丢整数。')
print('\\n✅ 六类边界全部通过。把这张表背成肌肉记忆：')
print('   **空 / 单元素 / 全相同 / 极值 / 重复与相接 / 溢出与精度** —— 交卷前 30 秒逐条点名。')"""),

    md("""## ✏️ 练习 1：三数之和（去重是全部难点）

实现 `three_sum(nums)`：返回所有**和为 0** 的三元组，要求

- 每个三元组内部**升序**，返回值整体按字典序排序（这样结果是唯一确定的，可以直接对拍）
- **不含重复三元组**（`[-1,0,1]` 只能出现一次，哪怕输入里有两个 `-1`）
- 时间 $O(n^2)$：排序 $O(n\\log n)$ + 固定一个数后对撞指针 $O(n)$
- 不许用 `set` 去重（那是绕过考点；面试官要看的是**三处去重**）

**三处去重的位置**（写代码前先说出来）：
1. 固定元素 `a[i]`：`i > 0 and a[i] == a[i-1]` 时跳过
2. 找到一组解之后，左指针要跳过与刚用过的相同的值
3. 同上，右指针也要跳"""),

    code("""def three_sum(nums):
    # TODO:
    #   a = sorted(nums)
    #   for i in range(len(a) - 2):
    #       去重①：i > 0 且 a[i] == a[i-1] → continue
    #       剪枝 ：a[i] > 0 → break（三个非负数和为 0 只能全是 0，已被 i=0 覆盖）
    #       lo, hi = i+1, len(a)-1；对撞：s<0 → lo+=1；s>0 → hi-=1；s==0 → 记录并两侧同时收
    #       去重②③：记录后，while lo<hi and a[lo]==a[lo-1]: lo+=1 ；右侧同理
    #   return sorted(out)
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
import itertools as _it

def _three_sum_brute(nums):
    seen = {tuple(sorted(c)) for c in _it.combinations(nums, 3) if sum(c) == 0}
    return [list(t) for t in sorted(seen)]

assert three_sum([-1, 0, 1, 2, -1, -4]) == [[-1, -1, 2], [-1, 0, 1]]
assert three_sum([0, 0, 0, 0]) == [[0, 0, 0]], '四个 0 只能产出一个三元组'
assert three_sum([]) == [] and three_sum([1, 2]) == [] and three_sum([1, 2, 3]) == []

_r1 = random.Random(31)
for _ in range(600):
    n = _r1.randint(0, 9)
    a = [_r1.randint(-5, 5) for _ in range(n)]          # 小值域 ⇒ 大量重复，专打去重
    assert three_sum(a) == _three_sum_brute(a), (a, three_sum(a), _three_sum_brute(a))

# 复杂度自检：对撞指针部分对每个 i 至多走 n 步 ⇒ 总步数 <= n^2
_a = list(range(-40, 40))
_t0 = time.perf_counter(); three_sum(_a); _dt = time.perf_counter() - _t0
assert _dt < 1.0, 'n=80 还要 1 秒以上 ⇒ 很可能写成了 O(n^3) 三重循环'
print('✅ 练习 1 通过：600 组高重复率随机对拍 + 四个边界 + 复杂度粗检（n=80 用 %.1f ms）'
      % (_dt * 1000))
print('   面试话术：「我先排序，然后固定最小的那个数，剩下变成有序数组的两数之和，')
print('   用对撞指针 O(n)；去重有三处，分别在固定元素和两个指针上。」')"""),

    md("""## ✏️ 练习 2：可变窗口求最长（同一个模板的第三次复用）

实现 `longest_k_distinct(s, k)`：`s` 中**最多包含 k 个不同字符**的最长子串长度。

这道题和「最长无重复子串」是**同一个模板**，差别只在两行：
窗口状态从「字符 → 最后出现位置」换成「字符 → 出现次数」，非法条件从「有重复」换成 `len(cnt) > k`。

要求：
- $O(n)$，`left` 只右移
- **计数归零时必须 `del` 掉那个键**，否则 `len(cnt)` 永远不减 —— 这是本题唯一的坑
- `k <= 0` 返回 `0`；`k` 大于字符集大小时返回 `len(s)`"""),

    code("""def longest_k_distinct(s, k):
    # TODO:
    #   if k <= 0: return 0
    #   cnt = defaultdict(int); left = best = 0
    #   for r, ch in enumerate(s):
    #       cnt[ch] += 1
    #       while len(cnt) > k:            # 窗口非法 → 收缩
    #           cnt[s[left]] -= 1
    #           if cnt[s[left]] == 0: del cnt[s[left]]     # ← 忘了这行就永远出不来
    #           left += 1
    #       best = max(best, r - left + 1)  # 结算在收缩之后（此时窗口一定合法）
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
def _lkd_brute(s, k):
    if k <= 0:
        return 0
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            if len(set(s[i:j + 1])) <= k:
                best = max(best, j - i + 1)
    return best

assert longest_k_distinct('eceba', 2) == 3          # 'ece'
assert longest_k_distinct('aa', 1) == 2
assert longest_k_distinct('', 3) == 0
assert longest_k_distinct('abc', 0) == 0
assert longest_k_distinct('abcabc', 10) == 6, 'k 大于字符集 ⇒ 整串'

_r2 = random.Random(37)
for _ in range(1500):
    s = ''.join(_r2.choice('abcd') for _ in range(_r2.randint(0, 12)))
    k = _r2.randint(0, 5)
    assert longest_k_distinct(s, k) == _lkd_brute(s, k), (s, k)

# k=1 时答案必然等于「最长连续相同字符段」的长度 —— 一条独立的交叉验证
for _ in range(300):
    s = ''.join(_r2.choice('ab') for _ in range(_r2.randint(1, 15)))
    runs = max(len(list(g)) for _, g in _it.groupby(s))
    assert longest_k_distinct(s, 1) == runs, (s,)
print('✅ 练习 2 通过：1500 组随机对拍 + 5 个边界 + 300 组「k=1 等价于最长同字符段」交叉验证。')
print('   这三道题（最长无重复 / 最多 K 个不同 / 至多一个 0 的最长连续 1）用的是同一个模板；')
print('   面试里听到「最长的满足某条件的子串」，先按这个模板起手，再想窗口状态怎么维护。')"""),

    md("""## ✏️ 练习 3：二维前缀和（本岗位的必会题）

实现两个函数：

- `my_prefix2d(M)`：输入 `(H, W)` 的 numpy 整数矩阵，返回 `(H+1, W+1)` 的 **int64** 前缀和表，
  满足 `P[i, j] == M[:i, :j].sum()`；`P` 的第 0 行与第 0 列全为 0
- `my_rect_sum(P, r0, c0, r1, c1)`：返回闭区间矩形 `[r0..r1] x [c0..c1]` 的和，**必须是 $O(1)$**
  （只读容斥的 4 个格子，自测会用一个计数代理对象验证这一点）

递推式（不许直接调 `cumsum`，手写递推才能看出你懂容斥）：

$$P[i{+}1][j{+}1] = M[i][j] + P[i][j{+}1] + P[i{+}1][j] - P[i][j]$$

**为什么要减 `P[i][j]`？** 因为「上面那块」和「左边那块」把左上角重复算了一次。
容斥的加减号，在建表和查询时是**镜像**的 —— 这是最容易记混的地方。"""),

    code("""def my_prefix2d(M):
    # TODO: H, W = M.shape
    #       P = np.zeros((H+1, W+1), dtype=np.int64)   # 必须 int64：见第 5 节的溢出实验
    #       双层循环按递推式填 P[i+1, j+1]
    raise NotImplementedError

def my_rect_sum(P, r0, c0, r1, c1):
    # TODO: 四项容斥。注意查询用的是 r1+1 / c1+1（闭区间 → 前缀和的开区间上界）
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
_r3 = random.Random(41)
for _ in range(400):
    H, W = _r3.randint(1, 5), _r3.randint(1, 5)
    A = np.array([[_r3.randint(-9, 9) for _ in range(W)] for _ in range(H)], dtype=np.int64)
    P = my_prefix2d(A)
    assert P.shape == (H + 1, W + 1), '表必须比原图多一行一列'
    assert P.dtype == np.int64, '必须 int64，否则大图会溢出'
    assert int(P[0].sum()) == 0 and int(P[:, 0].sum()) == 0, '第 0 行/列必须全 0'
    for i in range(H + 1):
        for j in range(W + 1):
            assert int(P[i, j]) == int(A[:i, :j].sum()), '定义：P[i,j] = M[:i,:j] 之和'
    r0 = _r3.randint(0, H - 1); r1 = _r3.randint(r0, H - 1)
    c0 = _r3.randint(0, W - 1); c1 = _r3.randint(c0, W - 1)
    assert my_rect_sum(P, r0, c0, r1, c1) == int(A[r0:r1 + 1, c0:c1 + 1].sum())

# 溢出安全：4x4 的 1e9 → 1.6e10，远超 int32
_big = np.full((4, 4), 10**9, dtype=np.int64)
assert my_rect_sum(my_prefix2d(_big), 0, 0, 3, 3) == 16 * 10**9

# O(1) 验证：用计数代理统计查询读了几个格子
class _CountingTable:
    def __init__(self, P):
        self.P, self.reads = P, 0
    def __getitem__(self, idx):
        self.reads += 1
        return self.P[idx]

_ct = _CountingTable(my_prefix2d(np.ones((30, 30), dtype=np.int64)))
assert my_rect_sum(_ct, 0, 0, 29, 29) == 900
assert _ct.reads <= 8, '查询读了 %d 次 ⇒ 不是 O(1)，肯定在循环求和' % _ct.reads
print('✅ 练习 3 通过：400 组随机矩阵逐格校验定义 + 任意矩形对拍 + int64 溢出安全 + O(1)（读 %d 格）'
      % _ct.reads)
print('   工程用途：候选框内前景像素占比、区域均值方差粗筛、多尺度滑窗打分 ——')
print('   一次 O(HW) 建表，之后任意多个框每个 4 次访存（Viola-Jones 2001 的核心技巧）。')"""),

    md("""## ✏️ 练习 4：滑动窗口最大值（单调队列）

实现 `sliding_window_max(a, k, stats=None)`：返回每个长度为 `k` 的窗口的最大值列表。
`k <= 0` 或 `k > len(a)` 时返回 `[]`。

要求：
- **总时间 $O(n)$**（不是 $O(nk)$）。用一个双端队列存**下标**，维护「对应值从队首到队尾单调递减」
- 两个操作缺一不可：① 尾部弹出所有 `a[尾] <= a[r]` 的下标（它们永远不可能再当最大值）
  ② 队首若已滑出窗口（`dq[0] <= r - k`）就弹掉
- 每次 `append` / `pop` / `popleft` 都调用一次 `_bump(stats)` —— 自测会用它验证操作数 $\\le 3n$

**为什么存下标而不是存值？** 因为「过期」只能靠下标判断。这是本题的第一个考点，
面试里被问到时直接答这一句。"""),

    code("""def _bump(stats):
    \"\"\"操作计数器（自测用）。每次对 deque 的增删都调用一次。\"\"\"
    if stats is not None:
        stats['ops'] = stats.get('ops', 0) + 1


def sliding_window_max(a, k, stats=None):
    # TODO:
    #   if k <= 0 or k > len(a): return []
    #   dq = deque()                     # 存下标；不变量：a[dq[0]] >= a[dq[1]] >= ...
    #   for r in range(len(a)):
    #       while dq and a[dq[-1]] <= a[r]: dq.pop(); _bump(stats)
    #       dq.append(r); _bump(stats)
    #       if dq[0] <= r - k: dq.popleft(); _bump(stats)
    #       if r >= k - 1: out.append(a[dq[0]])
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
def _swm_brute(a, k):
    if k <= 0 or k > len(a):
        return []
    return [max(a[i:i + k]) for i in range(len(a) - k + 1)]

assert sliding_window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
assert sliding_window_max([], 1) == [] and sliding_window_max([1, 2], 0) == []
assert sliding_window_max([1, 2], 5) == [], 'k > n 必须返回空，不能崩'
assert sliding_window_max([4, 4, 4], 2) == [4, 4], '全相同：<= 的写法保证不会漏'
assert sliding_window_max([7, 2, 4], 1) == [7, 2, 4], 'k=1 ⇒ 原数组'

_r4 = random.Random(43)
for _ in range(1500):
    n = _r4.randint(0, 12)
    a = [_r4.randint(-5, 5) for _ in range(n)]
    k = _r4.randint(0, n + 2)
    assert sliding_window_max(a, k) == _swm_brute(a, k), (a, k)

# 复杂度断言：每个下标至多入队一次、出队一次 ⇒ ops <= 2n（留到 3n 的余量）
for pattern, name in [(list(range(4000)), '严格递增'),
                      (list(range(4000, 0, -1)), '严格递减'),
                      ([1] * 4000, '全相同')]:
    st = {}
    out = sliding_window_max(pattern, 100, stats=st)
    ops = st.get('ops', 0)
    assert out == _swm_brute(pattern, 100)
    assert ops <= 3 * len(pattern), '%s：ops=%d 超过 3n ⇒ 不是 O(n)' % (name, ops)
    print('  %s n=4000 k=100 → 队列操作 %5d 次（<= 3n = %d）' % (name, ops, 3 * len(pattern)))
print('✅ 练习 4 通过：1500 组随机对拍 + 5 个边界 + 三种最坏模式的 O(n) 操作数断言。')
print('   追问预案：「要滑动窗口最小值呢？」→ 反号或把 <= 改成 >=；')
print('   「要中位数呢？」→ 单调队列不行了，得上双堆或有序容器（O(n log k)）。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def three_sum(nums):
    a = sorted(nums)
    n = len(a)
    out = []
    for i in range(n - 2):
        if i > 0 and a[i] == a[i - 1]:
            continue                       # 去重①：固定元素与上一轮相同 → 结果必然重复
        if a[i] > 0:
            break                          # 剪枝：最小的都 > 0 ⇒ 三数和不可能为 0
        lo, hi = i + 1, n - 1
        while lo < hi:                     # 不变量：解的两个下标都在 [lo, hi] 内
            s = a[i] + a[lo] + a[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                out.append([a[i], a[lo], a[hi]])
                lo += 1
                hi -= 1
                while lo < hi and a[lo] == a[lo - 1]:
                    lo += 1                # 去重②：左指针跳过刚用过的值
                while lo < hi and a[hi] == a[hi + 1]:
                    hi -= 1                # 去重③：右指针同理
    return sorted(out)"""),

    code("""# 练习 2 参考答案
def longest_k_distinct(s, k):
    if k <= 0:
        return 0
    cnt = defaultdict(int)                 # 窗口内「字符 → 出现次数」
    left = best = 0
    for r, ch in enumerate(s):
        cnt[ch] += 1
        while len(cnt) > k:                # 窗口非法（不同字符太多）→ 收缩
            cnt[s[left]] -= 1
            if cnt[s[left]] == 0:
                del cnt[s[left]]           # 必须删键，否则 len(cnt) 永远不减 → 死循环
            left += 1
        best = max(best, r - left + 1)     # 结算在收缩之后：此刻窗口一定合法
    return best"""),

    code("""# 练习 3 参考答案
def my_prefix2d(M):
    H, W = M.shape
    P = np.zeros((H + 1, W + 1), dtype=np.int64)      # int64：见第 5 节的溢出实验
    for i in range(H):
        for j in range(W):
            # 容斥：上面那块 + 左边那块 - 重复算的左上角
            P[i + 1, j + 1] = int(M[i, j]) + P[i, j + 1] + P[i + 1, j] - P[i, j]
    return P

def my_rect_sum(P, r0, c0, r1, c1):
    # 建表时是「+ 上 + 左 - 左上」，查询时符号镜像成「全 - 上 - 左 + 左上」
    return int(P[r1 + 1, c1 + 1] - P[r0, c1 + 1] - P[r1 + 1, c0] + P[r0, c0])"""),

    code("""# 练习 4 参考答案
def sliding_window_max(a, k, stats=None):
    n = len(a)
    if k <= 0 or k > n:
        return []
    dq = deque()                           # 存**下标**；不变量：a[dq[0]] >= a[dq[1]] >= ...
    out = []
    for r in range(n):
        while dq and a[dq[-1]] <= a[r]:    # 比新元素小的旧元素永远不可能再当最大值
            dq.pop(); _bump(stats)
        dq.append(r); _bump(stats)
        if dq[0] <= r - k:                 # 队首过期（窗口是 [r-k+1, r]）
            dq.popleft(); _bump(stats)     # 下标每步只增 1 ⇒ 每轮至多弹一次
        if r >= k - 1:                     # 窗口装满后才开始产出
            out.append(a[dq[0]])
    return out
# 复杂度：每个下标恰好入队一次、至多出队一次 ⇒ 总操作 <= 2n ⇒ O(n)"""),

    md("""---
## 🧪 真实工程胶囊：数组 / 字符串三大模板速查卡"""),

    code("""RECIPE = r'''
# ======================================================================
# 面试与生产两用速查卡 · 双指针 / 滑动窗口 / 前缀和        （C62 模块 01）
# ======================================================================

# ---------- 1. 双指针：先说不变量，再写代码 ----------
# 对撞（有序 + 配对 / 容器极值）
#   不变量：答案的两个下标都在 [lo, hi] 内
#   保持   ：排除的那一端，与区间内任何元素配对都不可能优于已记录的最优
# 快慢/读写（原地修改，O(1) 空间）
#   不变量：a[:w] 是已确认保留的结果，相对顺序不变；a[w:r] 是可覆盖的坑
# 同向（两个有序序列）
#   不变量：右端点更小的那个，不可能再与对方后续元素相交 -> 让它前进
def interval_intersection(A, B):            # IoU 在单轴上的投影
    i = j = 0; out = []
    while i < len(A) and j < len(B):
        lo, hi = max(A[i][0], B[j][0]), min(A[i][1], B[j][1])
        if lo <= hi: out.append([lo, hi])
        if A[i][1] < B[j][1]: i += 1
        else:                 j += 1
    return out

# ---------- 2. 滑动窗口：三套模板，差别只在两行 ----------
# 定长        : 先装满 k 个，之后 s += a[r] - a[r-k]（一进一出）
# 可变·求最长 : while 窗口非法: 收缩 ；结算写在收缩**之后**
# 可变·求最短 : while 窗口合法: 结算 + 收缩 ；结算写在收缩**之前**
# 成立前提（必须当场说出来）：left 只右移不回退
#   <=> "窗口扩大 => 条件单调变化"
#   反例：数组含负数时求"和 >= target"的最短子数组 —— 滑窗给出 3，真实答案是 1
#         有负数就换 前缀和 + 哈希（模块 02）
# 常见 bug：最长无重复子串漏掉 `last[ch] >= left` -> left 回退 -> "abba" 返回 3（应为 2）
#           最多 K 个不同字符忘了 `del cnt[ch]` -> len(cnt) 永不减 -> 死循环

# ---------- 3. 前缀和 / 差分 / 二维 ----------
# P[i] = a[0..i-1] 之和；len(P) = len(a)+1；P[0]=0 代表空前缀（所有 off-by-one 的源头）
# 和为 k 的子数组：seen = {0: 1} 必须有，否则漏掉以下标 0 开头的解；**有负数也成立**
# 差分：d[l] += v; d[r+1] -= v（多开一格接 r=n-1）；只支持"先全改完再统一读"
#       需要边改边查 -> 树状数组 BIT，O(log n)
# 选型表
#   静态多次区间求和 -> 前缀和        建表 O(n)   查询 O(1)
#   多次区间加后统一读 -> 差分        修改 O(1)   还原 O(n)
#   边改边查         -> BIT/线段树   两者 O(log n)
#   二维静态区域和   -> 积分图        建表 O(HW)  查询 O(1)

# ---------- 4. 积分图（CV 里天天用，也是两个真实上线 bug 的产地） ----------
import numpy as np
def integral_image(M):                      # 返回 (H+1, W+1)，多的一行一列全 0 => 查询无需 if
    H, W = M.shape
    P = np.zeros((H+1, W+1), dtype=np.int64)
    P[1:, 1:] = M
    return P.cumsum(0).cumsum(1)
def rect_sum(P, r0, c0, r1, c1):            # 闭区间，四项容斥，O(1)
    return int(P[r1+1, c1+1] - P[r0, c1+1] - P[r1+1, c0] + P[r0, c0])
# 数值红线（面试里主动提，直接显工程手感）：
#   int32 上限 2.147e9；4K 图 3840x2160x255 = 2.115e9 —— 正好顶在边界，务必 int64
#   float32 尾数 24 位：2^24 = 16777216 之后整数不再连续，720p 的积分图早就越线
#   numpy 陷阱：cumsum 会把 int16/int32 悄悄提升到平台整型，掩盖真实 C/CUDA 里的溢出；
#              要复现就得写 M.cumsum(0, dtype=np.int16)
# 用途：候选框前景占比、区域均值方差粗筛、多尺度滑窗打分（Viola-Jones 2001）

# ---------- 5. 对拍：把"我觉得对"变成"我验证过" ----------
def duel(fast, brute, gen, trials=400):
    for _ in range(trials):
        args = gen()
        assert fast(*args) == brute(*args), args
# 三条经验：
#   1) 生成器用**小值域**（如 -5..5）+ **小长度**（0..10），才能高频命中重复元素与空输入
#   2) 多解题先把输出**规范化**（排序 / 只比存在性 / 内部 assert 解的合法性），否则对拍会假失败
#   3) 复杂度用**操作计数**断言，别用墙钟时间 —— CI 上的时间断言必然 flaky

# ---------- 6. 交卷前 30 秒：边界六连 ----------
#   [ ] 空输入（返回什么？会不会 IndexError）
#   [ ] 单元素（max_area 返回 0、product_except_self 返回 [1]）
#   [ ] 全相同（去重/滑窗/NMS 并列）
#   [ ] 极值与单调（全递增、全递减）
#   [ ] 重复元素与"边界相接算不算重叠"（区间题必问面试官）
#   [ ] 数值：整数溢出、float32 精度、除零/负数破坏前提
'''
print(RECIPE)
for _tok in ['interval_intersection', 'integral_image', 'rect_sum', 'duel',
             '边界六连', 'float32 尾数 24 位']:
    assert _tok in RECIPE, _tok
print('\\n（前 4 节可直接复制进项目；第 5 节的 duel 建议放进你的测试工具箱。）')"""),

    md("""### 小结

1. **模板的价值不在模板本身，在它成立的前提。**
   可变滑窗要求「`left` 只右移」，前提是「窗口扩大 ⇒ 条件单调」；
   本 notebook 用 `[1, -1, 5]` 把这个前提被破坏时的错误答案跑了出来（滑窗给 3，真实是 1）。
   面试官改一个字（「如果可以有负数呢？」）就能把背模板的人问倒 ——
   **准备的正确形态是：对每个模板，知道前提是什么、前提被破坏时换成什么。**

2. **循环不变量是可执行的，不是修辞。** 第 2 节对长度 $\\le 5$ 的输入**穷举**验证了
   「区间 $[lo,hi]$ 内始终存在最优解」这条不变量。会写这种检查的人，
   debug 双指针时不需要靠瞪代码 —— 他会在循环里插一句 assert，让程序自己指出哪一轮破了。

3. **暴力解是免费的真值，随机对拍是免费的测试用例生成器。**
   `longest_unique_buggy` 在 `"abc"`、`"aab"` 上完全正确，是 2000 组随机对拍把它抓出来的。
   对拍的三条工程经验：小值域 + 小长度、输出先规范化、复杂度用**操作计数**而不是墙钟时间断言。

4. **前缀和与差分互为逆运算，这一句话统一了四种数据结构的选型。**
   静态求和用前缀和、批量修改用差分、边改边查用 BIT、二维用积分图。
   而积分图在本岗位上不是「一道题」，是**每天都在跑的代码** ——
   连带它的两条数值红线（int32 装不下 4K、float32 在 $2^{24}$ 之后丢整数）也一起记住。

5. **这一模块练的是 C61-05 那些代码的底层积木。**
   IoU 的区间求交是双指针、NMS 是排序 + 扫描、多帧投票是定长窗口、bbox 统计是积分图。
   面试里把这三条连接主动说出来，你就同时展示了算法功底与领域理解 ——
   这是「刷题的人」和「能上手写感知后处理的人」之间最短的那段距离。"""),
]
