# -*- coding: utf-8 -*-
"""C62 模块 03 · 树、图与搜索。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（六步答题协议）；模块 01（数组与双指针）；模块 02（排序与哈希：并查集的 tie-break 与桶化会用到）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_trees_graphs.ipynb（遍历递归/迭代双实现对拍、并查集用于 <strong>bbox 聚类</strong>、网格连通域标记与逐像素扫描法对拍、BFS 最短路、拓扑排序、<strong>NMS 作为极大独立集</strong>）'),
    ("核心参考", "CLRS 第 19 章（并查集）· Tarjan &amp; van Leeuwen 1984 · Hosang et al. CVPR 2017（Learning NMS）· C57 模块 04（切片推理跨片合并）· C61 模块 05（NMS 手撕，本课不重复）"),
    ("预计时长", "读 85 分钟 + 跑 130 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("recursion", "递归三要素：为什么你写的递归会栈溢出", "".join([
        P("面试里的递归题，扣分几乎从来不是「想不出递归关系」，而是<strong>三要素里漏了一个</strong>。"
          "把三要素当成一张必填表格，每次写递归前口述一遍，是最便宜的保险。"),
        TABLE(["要素", "要回答的问题", "漏掉的后果", "面试官的检查方式"], [
            ["<strong>终止条件</strong>（base case）", "最小的子问题长什么样？答案是什么？",
             "无限递归 → <code>RecursionError</code>", "「空树输入会怎样？」"],
            ["<strong>拆解</strong>（recurse）", "怎么把问题变成<u>严格更小</u>的同类问题？",
             "规模不减 → 死循环；或漏分支 → 漏解", "「你凭什么保证它一定会停？」"],
            ["<strong>合并</strong>（combine）", "子问题的答案怎么拼成当前答案？",
             "返回值语义混乱、边界处 off-by-one", "「你的函数返回的到底是什么？」"],
        ]),
        P("其中<strong>「严格更小」是终止性的唯一保证</strong>，它对应模块 01 里讲的「严格递减的整数度量」："
          "树递归里度量是子树高度或结点数，图递归里度量是「未访问结点数」——"
          "<em>图 DFS 必须有 <code>visited</code> 集合，正是因为图有环，没有 visited 就没有递减度量。</em>"),
        H3("函数的「契约」必须先写下来"),
        P("递归写错最常见的根因是<strong>函数返回值的语义没定清楚</strong>。"
          "以「求二叉树直径」为例：递归函数返回的是<u>经过该结点向下的最大深度</u>，"
          "而<u>答案（直径）是在遍历过程中用一个外部变量维护的</u>——"
          "这两件事是不同的量，混在一起就会写出「直径 = 左深度 + 右深度」然后向上层返回它这种错误。"),
        CALLOUT("intuition", "<strong>心法</strong>：写递归时先写一行注释——"
                             "「本函数<u>输入</u>什么、<u>返回</u>什么、<u>副作用</u>是什么」。"
                             "<em>返回值和答案不是一回事</em>：很多树形 DP 都是「返回局部量，答案挂在外部变量上」。"
                             "面试里先说出这一行，面试官立刻知道你不是在瞎试。"),
        H3("递归的三个隐性代价"),
        UL([
            "<strong>栈深度</strong>。CPython 默认递归上限约 1000 层（<code>sys.getrecursionlimit()</code>），"
            "而一条 10 万结点的<u>退化成链表的树</u>会直接炸。<em>调大 limit 不是解法——"
            "真正的 C 栈只有几 MB，调太大会变成段错误（进程直接死掉，连异常都抓不到）。</em>"
            "<strong>唯一稳妥的解法是转迭代（第 2 节）。</strong>",
            "<strong>调用开销</strong>。Python 的函数调用比循环慢一个量级；"
            "对每帧都要跑的后处理，把递归 flood fill 换成显式栈的版本，实测能快 2–4 倍（notebook 里有实测）。",
            "<strong>重复子问题</strong>。同一个子问题被求解多次 → 指数爆炸。"
            "这正是模块 04 记忆化搜索要解决的问题；<em>在树上一般不会发生（子树不重叠），"
            "在图与网格上必须靠 visited 来杜绝。</em>",
        ]),
        DUAL(
            "递归的本质是<strong>把「记住走过的路」这件事外包给了调用栈</strong>。"
            "你没有写栈，但栈一直在那里——每层的局部变量、参数、返回地址都被压着。"
            "所以「递归转迭代」不是重写算法，只是<em>把这个隐式的栈显式地写出来</em>，"
            "算法本身一个字都不变。",
            "严谨地说，任何递归都可以机械地转成「显式栈 + 状态机」的迭代形式："
            "每个栈帧保存<u>参数、局部变量、以及「上次执行到第几个递归调用点」</u>（返回点编号）。"
            "尾递归（tail recursion）是特例，它的栈帧在递归调用后不再被使用，"
            "所以可以直接退化成 <code>while</code> 循环并复用同一个帧——"
            "<strong>但 CPython 不做尾调用优化</strong>，所以在 Python 里尾递归<u>依然会爆栈</u>，"
            "这与 Scheme/Scala 的行为不同，是一个常被误答的面试点。",
        ),
    ])),

    # ============================================================== 2
    ("rec2iter", "递归转迭代：把调用栈写出来", "".join([
        P("这是本模块<strong>最能拉开差距的一节</strong>。会写递归的人很多，"
          "能当场把递归改成显式栈、并说清「为什么后序最麻烦」的人少得多。"),
        H3("三种转法，难度递增"),
        TABLE(["转法", "适用", "关键技巧", "难度"], [
            ["<strong>直接循环</strong>", "尾递归 / 单分支递归（链表、二分）",
             "把递归参数变成循环变量", "★"],
            ["<strong>单栈 + 顺序控制</strong>", "前序 DFS、图 DFS、flood fill",
             "<u>先压右后压左</u>，因为栈是后进先出", "★★"],
            ["<strong>栈 + 状态机</strong>", "后序、树形 DP、任何「子结果回来后还要做事」的递归",
             "栈里存 <code>(结点, 阶段)</code>，阶段编号就是「返回点」", "★★★"],
        ]),
        ASCII("""
递归的三次访问时机（前/中/后序就是在这三个时刻做事）
─────────────────────────────────────────────────
        进入 node
          │  ← ① 前序：还没看孩子就做事
          ├──▶ 递归左子树
          │  ← ② 中序：左边做完了，右边还没开始
          ├──▶ 递归右子树
          │  ← ③ 后序：两个孩子的结果都回来了
        离开 node

显式栈要模拟的正是「同一个结点被经过三次」这件事：
    栈元素 = (node, stage)   stage ∈ {0=待展开, 1=左已完成, 2=右已完成}
    前序只需 stage 0        → 单栈就够
    后序需要区分 0 与 2     → 必须带 stage（或用 last_visited 标记）
""".rstrip()),
        P("<strong>为什么前序可以只用单栈？</strong>因为前序在「进入结点」时就把事做完了，"
          "结点弹出栈之后<u>不再需要回到它</u>——栈帧可以立刻丢弃。"
          "而后序必须等两个孩子都算完才做事，<em>结点弹出后还得再回来一次</em>，"
          "所以必须记录「我上次走到哪了」。这一句话就是状态机式转换的全部动机。"),
        H3("后序的两种写法"),
        OL([
            "<strong>改前序 + 反转</strong>：按「根→右→左」做前序，结果整体反转，就得到「左→右→根」。"
            "<em>代码最短、最好背，但它只适用于「后序只是为了得到一个访问序列」的情况</em>；"
            "如果你需要在后序时刻<u>使用子树的返回值</u>（树形 DP），这个技巧无效。",
            "<strong>栈 + stage 状态机</strong>：通用解法，可以携带子树返回值，也是把任意递归"
            "（包括模块 04 的记忆化搜索）转成迭代的标准套路。<em>面试里先给写法 1 展示手速，"
            "再主动说「如果要做树形 DP，得改成带 stage 的版本」——这是主动展示深度的机会。</em>",
        ]),
        CALLOUT("danger", "<strong>面试当场翻车点</strong>：被问「你的递归会不会栈溢出」时回答"
                          "「我可以 <code>sys.setrecursionlimit(10**6)</code>」。"
                          "<em>这是错的</em>——Python 的递归上限是为了保护真实的 C 栈（通常 8 MB）；"
                          "调到 10⁶ 后爆的是 C 栈，表现为<strong>段错误 / 进程被杀，没有异常、没有栈回溯、日志里什么都没有</strong>。"
                          "在车端这种「进程崩溃就意味着感知输出断流」的场景里，这是安全事故。"
                          "正确回答是：<u>「数据规模可能让深度到 10⁵，所以我会写成显式栈的迭代版本」</u>。"),
        DUAL(
            "什么时候<u>必须</u>转迭代？三个信号：① 深度可能到 10⁴ 以上（长链、大网格的 flood fill）；"
            "② 需要<strong>可中断</strong>（车端在帧预算耗尽时要能停下来，把栈存着下一帧继续）；"
            "③ 需要<strong>可序列化</strong>（把搜索状态存盘、跨进程迁移）。"
            "后两条在工程里比第一条更重要，却几乎从不出现在算法教材里。",
            "严谨地说，转迭代把<strong>控制状态从「不可见的调用栈」变成了「可见的数据结构」</strong>，"
            "于是控制流获得了数据的全部性质：可检查、可持久化、可限长、可分片。"
            "<em>这也是为什么工业级的图搜索（大规模连通域标记、点云聚类）几乎一律写成显式栈或队列</em>："
            "不是因为怕溢出，而是因为需要<u>对内存占用有硬上界</u>——"
            "显式容器可以 <code>reserve(capacity)</code> 并在超限时降级，调用栈做不到。",
        ),
    ])),

    # ============================================================== 3
    ("traversal", "二叉树的四种遍历：选哪个由「信息流方向」决定", "".join([
        P("遍历不是四个要背的名字，而是<strong>四种信息流方向</strong>。"
          "题目一给出，你要在 10 秒内判断：<u>信息是从上往下带（前序）、还是从下往上聚（后序）、"
          "还是按层同步（BFS）</u>。判断对了，代码几乎是自动的。"),
        TABLE(["遍历", "信息流", "典型题", "为什么是它"], [
            ["<strong>前序</strong> 根左右", "自上而下<strong>传递</strong>",
             "路径和、序列化、克隆树、带前缀的路径枚举", "父结点的信息（累积路径、深度）要先传给孩子"],
            ["<strong>中序</strong> 左根右", "有序输出",
             "BST 验证 / BST 第 k 小 / BST 转有序链表", "<strong>BST 的中序遍历恰好是升序</strong>——这是 BST 的定义性质"],
            ["<strong>后序</strong> 左右根", "自下而上<strong>聚合</strong>",
             "树高、直径、树形 DP、判平衡、释放资源", "当前结点的答案依赖两个子树的答案"],
            ["<strong>层序</strong> BFS", "按深度分层",
             "每层最大值、最小深度、右视图、之字形", "需要「同一层」这个概念，或需要<u>最先到达即最优</u>"],
        ]),
        P("<strong>层序的实现只有一个要点</strong>：进入循环时先记下 <code>n = len(queue)</code>，"
          "然后只处理这 <code>n</code> 个——这 <code>n</code> 个恰好是当前整层。"
          "<em>不记 <code>n</code> 就无法区分层，「每层最大值」这类题就写不出来。</em>"),
        H3("BST 的中序：一个被反复考的性质"),
        P("「验证一棵树是不是 BST」的经典错误是<u>只比较结点与它的两个孩子</u>。"
          "反例：根 10、左孩子 5、左孩子的右孩子 12——局部全部合法，但 12 出现在根的左子树里，不是 BST。"
          "<strong>两个正确解法</strong>：① 中序遍历必须严格递增（只需记住「上一个访问的值」）；"
          "② 递归时向下传递 <code>(lower, upper)</code> 开区间约束（这是前序：信息自上而下传）。"
          "<em>把这两个解法都说出来，并指出它们分别是中序与前序，比只写对一个更有价值。</em>"),
        CALLOUT("warn", "<strong>递归里最常见的三个 bug</strong>："
                        "① 空结点没处理（<code>if not node: return ...</code> 忘了写，或返回值语义不对）；"
                        "② <u>把「答案」和「返回值」混为一谈</u>（直径题：返回深度，答案挂在外部变量）；"
                        "③ 判平衡这类题写成 <code>height(左) - height(右)</code> 然后每层重算高度 → 退化成 $O(n^2)$，"
                        "正解是<strong>后序一趟返回「高度 + 是否平衡」</strong>，$O(n)$。"
                        "这三个 bug 在 notebook 里都被对拍抓了出来。"),
        DUAL(
            "为什么树题这么爱考？因为它<strong>用最短的代码同时检验递归、边界处理和返回值设计</strong>三件事，"
            "而且几乎不需要背任何数据结构细节。<em>对 ML/CV 岗来说，纯树题的出现频率是中等偏低的</em>，"
            "真正高频的是它的两个亲戚：<u>网格 BFS/DFS（第 5 节）与并查集（第 6 节）</u>——"
            "因为那两个直接对应图像上的操作。",
            "严谨地说，四种遍历都是同一次深度优先搜索在三个不同时刻做事的产物"
            "（前序/中序/后序），加上一次广度优先搜索（层序）。"
            "<strong>时间复杂度一律 $O(n)$；空间复杂度是关键区别</strong>："
            "DFS 是 $O(h)$（$h$ 为高度，退化成链时是 $O(n)$），"
            "BFS 是 $O(w)$（$w$ 为最大层宽，完全二叉树里是 $O(n/2)$）。"
            "<em>所以「深而窄的树用 DFS、浅而宽的树用 BFS」是一条真实的工程判据</em>，"
            "面试里被问到空间复杂度时，说出 $h$ 与 $w$ 这两个字母就够了。",
        ),
    ])),

    # ============================================================== 4
    ("bfs-dfs", "BFS vs DFS 的选择信号，以及最短路的最简形态", "".join([
        P("这一节只需要记住一句话：<strong>BFS 的第一次到达就是最优（在边权相同时），DFS 没有这个性质。</strong>"
          "所有选择信号都是这句话的推论。"),
        TABLE(["题面出现这些词", "用", "理由", "空间"], [
            ["最短 / 最少步数 / 最少操作 / 最短时间", "<strong>BFS</strong>",
             "按距离分层扩展，首次弹出即最短", "$O(\\text{层宽})$"],
            ["所有路径 / 全部方案 / 组合 / 排列", "<strong>DFS + 回溯</strong>",
             "需要「进入-撤销」的对称结构", "$O(\\text{深度})$"],
            ["连通性 / 有几个岛 / 是否可达", "<strong>都行</strong>（DFS 代码更短）",
             "只关心可达集合，不关心距离", "看形状"],
            ["拓扑序 / 依赖顺序 / 检测环", "<strong>都行</strong>（Kahn=BFS，三色=DFS）",
             "见第 7 节", "$O(V)$"],
            ["边权不同（有代价）", "<strong>Dijkstra</strong>（0/1 权用 deque-BFS）",
             "分层假设被破坏，必须按累计代价出堆", "$O(V)$"],
            ["有负权边", "<strong>Bellman-Ford</strong>",
             "Dijkstra 的「已确定不再更新」假设失效", "$O(V)$"],
        ]),
        H3("BFS 最短路：三个必须说对的细节"),
        OL([
            "<strong>入队时就标记 visited，不是出队时。</strong>否则同一个结点会被多次入队，"
            "队列膨胀到 $O(E)$，在网格上就是 4 倍常数；更糟的是<u>层数统计会出错</u>。"
            "<em>这是 BFS 最高频的实现错误。</em>",
            "<strong>距离记在哪里</strong>：要么用 <code>dist</code> 字典/数组，"
            "要么用「按层推进」（每轮处理 <code>len(queue)</code> 个，层数即距离）。"
            "两种写法都对，<u>但不要混着写</u>——混着写会出现「有的分支算了距离，有的靠层数」的混乱。",
            "<strong>多源 BFS</strong>：把所有源点<u>一次性全部入队</u>，就得到「到最近源点的距离」。"
            "<em>这个技巧在 CV 里就是距离变换（distance transform）</em>："
            "「每个像素到最近前景像素的距离」——一次 BFS 搞定，不需要跑 $k$ 次单源。",
        ]),
        ASCII("""
Dijkstra 的骨架（面试里能写出这 8 行就够了）
──────────────────────────────────────────────
  dist = {s: 0};  heap = [(0, s)]
  while heap:
      d, u = heappop(heap)
      if d > dist.get(u, INF): continue    # ← 惰性删除：过期条目直接跳过
      for v, w in adj[u]:
          nd = d + w
          if nd < dist.get(v, INF):
              dist[v] = nd
              heappush(heap, (nd, v))      # 不删旧条目，靠上面那行过滤

  正确性依赖：边权非负 ⇒ 首次出堆的 d 就是最终最短距离
  复杂度：O((V + E) log V)   （堆里最多 E 个条目）
  0/1 权特例：把堆换成 deque，权 0 走 appendleft、权 1 走 append ⇒ O(V + E)
""".rstrip()),
        MATH("d(s,v)\\;=\\;\\min_{u\\in N(v)}\\bigl(d(s,u)+w(u,v)\\bigr)"
             "\\quad\\Longrightarrow\\quad \\text{BFS 在 } w\\equiv 1 \\text{ 时按 } d \\text{ 单调出队}"),
        CALLOUT("intuition", "<strong>为什么 Python 的堆没有 decrease-key？</strong>"
                             "因为<u>惰性删除</u>更简单也更快：不去修改旧条目，而是允许同一个结点在堆里存多份，"
                             "出堆时用 <code>d > dist[u]</code> 一行过滤掉过期的。"
                             "<em>面试里主动解释这一行，是「写过真代码」的强信号</em>——"
                             "很多人抄了这行却说不出它是干什么的。"),
        DUAL(
            "对本岗位来说，纯图论题的出现频率是<strong>低</strong>的（ML/CV coding 更爱矩阵、区间、采样）。"
            "但 BFS/DFS 是例外——因为<u>网格搜索天天用</u>：连通域标记、flood fill、"
            "距离变换、可行驶区域的连通性检查。<em>所以这一节的投入产出比集中在「网格 + 多源 BFS」上，"
            "Dijkstra 会写骨架就够，Bellman-Ford / SPFA 知道名字与适用条件即可。</em>",
            "严谨地说，BFS 求最短路的正确性来自<strong>「队列中的距离值单调不减，且至多取两个相邻值」</strong>"
            "这条不变量；一旦边权不等，这条不变量就破了，必须换成优先队列（Dijkstra），"
            "而 Dijkstra 的正确性又依赖<u>边权非负</u>——因为它假设「一个结点第一次出堆时距离已最终确定」，"
            "负权边可以在之后把它改小。<em>0/1 权是二者之间的临界情形</em>："
            "距离值仍然只有两个相邻取值，所以双端队列足以维持单调性，复杂度回到线性。",
        ),
    ])),

    # ============================================================== 5
    ("grid", "网格 BFS/DFS：它就是图像的连通域标记", "".join([
        P("这一节是本模块与本岗位的<strong>第一条硬连接</strong>。"
          "「岛屿数量」这类网格题在 LeetCode 上叫做算法题，在感知代码里叫做"
          "<span class=\"term\">connected component labeling</span>（连通域标记，CCL）——"
          "<u>同一个算法，两个名字</u>。"),
        TABLE(["网格题的说法", "CV 里的说法", "在 TSR 流水线里出现在哪"], [
            ["岛屿数量 / 连通块计数", "连通域个数", "分割 mask → 候选实例个数"],
            ["每个岛的面积", "连通域面积（像素数）", "按面积过滤噪点（&lt; N 像素的斑点丢掉）"],
            ["岛的外接矩形", "bounding box", "<strong>mask → bbox</strong>：分割结果转成检测框"],
            ["多源 BFS 的距离场", "距离变换 distance transform", "边缘距离、骨架化、watershed 的种子"],
            ["flood fill", "区域填充 / 漏洞填补", "mask 后处理：填掉标志牌内部的空洞"],
        ]),
        H3("4 邻域还是 8 邻域？这是一个语义选择，不是实现细节"),
        ASCII("""
   4 邻域（上下左右）            8 邻域（含对角）
      . X .                        X X X
      X o X                        X o X
      . X .                        X X X

同一张 mask，两种邻域给出不同的连通域个数：

      1 0            4 邻域 → 2 个连通域（对角不相连）
      0 1            8 邻域 → 1 个连通域（对角相连）

后果（真实会上线的 bug）：
  · 用 8 邻域：两个仅在角上接触的标志牌被合成一个 → 输出一个巨大的错框
  · 用 4 邻域：一条 1 像素宽的斜向反光条被切成一串碎块 → 面积过滤把它全丢了
拓扑事实：前景用 8 邻域 ⇔ 背景必须用 4 邻域，否则「前景连通」与「背景连通」会自相矛盾
        （这是数字拓扑里的连通性悖论，Rosenfeld 1970）
""".rstrip()),
        P("<strong>两种实现路线，notebook 里会对拍</strong>："
          "① <u>BFS/DFS 一遍法</u>——从每个未访问的前景像素出发泛洪，"
          "代码短、常数小，但递归版在大图上会爆栈（10⁶ 像素的连通域 → 10⁶ 层递归）；"
          "② <u>两遍扫描 + 并查集</u>（Hoshen–Kopelman 家族）——"
          "第一遍逐行扫描给临时标号、遇到冲突就 <code>union</code>，第二遍把标号替换成代表元。"
          "<em>路线 ② 是工业界与 GPU 实现的主流</em>，因为它<strong>访存是顺序的（对预取器友好）、"
          "可以分块并行、内存占用有确定上界</strong>——这三条正是第 2 节说的「显式化」的好处。"),
        CALLOUT("warn", "<strong>网格题的四个必答边界</strong>：① 空网格 / 全 0 / 全 1；"
                        "② 越界检查写在<u>入队前</u>还是<u>出队后</u>（写在入队前才不会污染 visited 的统计）；"
                        "③ 是否允许<u>原地修改输入</u>（把访问过的 1 改成 0 可以省掉 visited 数组，"
                        "但面试官可能追问「输入不许改怎么办」）；"
                        "④ <strong>递归深度</strong>——一个 1000×1000 的全 1 网格，DFS 递归深度是 10⁶。"
                        "<em>主动说出第 ④ 条并改成显式栈，是这类题最直接的加分点。</em>"),
        DUAL(
            "怎么在面试里把网格题答成「有领域感」的样子？做完基础版之后加一句："
            "<u>「这其实就是连通域标记，我在做分割后处理时用过；那时候我们用的是两遍扫描 + 并查集，"
            "因为它顺序访存、能分块并行；另外 4/8 邻域的选择要看目标形状——细长斜向目标必须用 8 邻域。」</u>"
            "<strong>一句话同时给出算法别名、工程实现选择、和一个具体的失效模式</strong>，"
            "这比多写一道题有用得多。",
            "严谨地说，网格是一个特殊的图：$V = HW$，每个结点度数 $\\le 4$（或 8），"
            "所以 $E = O(V)$，BFS/DFS 都是 $O(HW)$，与像素数线性。"
            "<em>它的特殊性在于「邻接关系可以由坐标直接算出，不需要存邻接表」</em>——"
            "这让空间从 $O(V+E)$ 降到 $O(V)$，也让 GPU 实现变得可行（每个像素一个线程）。"
            "<strong>而两遍扫描法的复杂度是 $O(HW\\,\\alpha(HW))$</strong>，"
            "$\\alpha$ 是并查集的反阿克曼函数（实际上 $\\le 4$），"
            "所以它与一遍法在渐进上等价，差别全在常数与并行性上。",
        ),
    ])),

    # ============================================================== 6
    ("dsu", "并查集：路径压缩、按秩合并，以及 bbox 聚类", "".join([
        P("这一节是本模块与本岗位的<strong>第二条硬连接</strong>，也是本模块唯一"
          "「一定要能默写出来」的数据结构。理由很实际："
          "<u>切片推理的跨片合并、框聚类、track ID 归并、近重复图片去重</u>——"
          "这四件事在实现层面是同一个数据结构。"),
        CODE("""class DSU:
    def __init__(self, n):
        self.parent = list(range(n))      # 初始每个元素自成一集，代表元是自己
        self.rank   = [0] * n             # 树高的上界（按秩合并用）
        self.size   = [1] * n             # 集合大小（很多题目要它）
        self.count  = n                   # 集合个数：每次成功 union 减 1

    def find(self, x):                    # 迭代版：不会爆栈
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:     # 路径压缩：把这条链上所有点直接挂到 root
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False                  # 已经同集合 —— 返回值能用来"检测环"
        if self.rank[ra] < self.rank[rb]:  # 按秩合并：矮树挂到高树下，树高不增
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1            # 只有等高相并，树高才 +1
        self.count -= 1
        return True""", "python"),
        P("<strong>两个优化各解决什么问题，必须分开说清</strong>："
          "<u>按秩（或按大小）合并</u>让树高保持 $O(\\log n)$——它防止「链化」；"
          "<u>路径压缩</u>把访问过的路径拍平——它把摊还代价降到几乎常数。"
          "<em>只用一个也能到 $O(\\log n)$，两个一起用才有下面这个著名结论：</em>"),
        MATH("m \\text{ 次操作的总代价} \\;=\\; O\\!\\left(m\\,\\alpha(n)\\right),"
             "\\qquad \\alpha(n)\\le 4 \\text{ 对一切实际的 } n\\;(<2^{65536})"),
        P("$\\alpha$ 是<span class=\"term\">inverse Ackermann function</span>（反阿克曼函数），"
          "增长极慢。<strong>面试里的标准答法</strong>：「摊还近似常数，严格说是 $O(\\alpha(n))$，"
          "实际当常数用；这个界是 Tarjan 证明的，而且是<u>紧的</u>——"
          "不存在渐进更快的通用不相交集合结构。」"),
        H3("并查集不能做什么（这才是深度问题）"),
        UL([
            "<strong>不能删边、不能分裂集合。</strong>路径压缩是不可逆的。"
            "<em>需要「逐步删边」的问题，标准套路是<u>离线倒序处理</u>："
            "把删边序列反过来变成加边序列。</em>面试里能说出这一招，说明你真懂它的局限。",
            "<strong>不能回答「两点间距离」。</strong>它只知道「是否同属一个集合」，不保留结构。"
            "要距离就得上 BFS 或 LCA。",
            "<strong>不能表达「非传递」的关系。</strong>这是下面那个陷阱的根源。",
        ]),
        H3("bbox 聚类：并查集的正确用法与它的失效模式"),
        P("把 $N$ 个候选框当成结点，<strong>IoU > 阈值就连一条边</strong>，"
          "然后用并查集求连通分量——这就是「框聚类」，"
          "在<u>切片推理的跨片合并</u>（见 C57-04）与<u>多相机结果融合</u>里天天用。"
          "notebook 里会把它与「逐对比较的暴力法」对拍，并实测 $O(N^2)$ 建边的耗时。"),
        CALLOUT("danger", "<strong>链式合并（chaining）—— 聚类法的致命失效模式。</strong>"
                          "IoU 关系<u>不是传递的</u>：$\\mathrm{IoU}(A,B)=0.6$、$\\mathrm{IoU}(B,C)=0.6$，"
                          "但 $\\mathrm{IoU}(A,C)$ 可能是 $0$。"
                          "而连通分量求的是<strong>传递闭包</strong>，于是 $A$、$B$、$C$ 被并成一个簇——"
                          "<em>在密集排列的一排限速牌上，这会把整排牌合成一个横跨半张图的巨大框。</em>"
                          "<strong>这正是 NMS 与「连通分量聚类」的本质区别</strong>："
                          "NMS 是<u>贪心地选代表并抑制邻居</u>（不传递），聚类是<u>求连通分量</u>（传递）。"
                          "两者在稀疏场景下结果几乎一样，在密集场景下差别巨大。"
                          "第 8 节会用图论语言把这件事说清楚。"),
        DUAL(
            "什么时候该用并查集而不是 NMS？<strong>当你要「合并」而不是「筛选」时。</strong>"
            "跨片合并要的是把同一个目标的多个碎片<u>拼成一个</u>（union 后取外接框或加权平均），"
            "NMS 要的是从一堆重复框里<u>挑一个</u>。<em>用错的症状很典型</em>："
            "该合并时用了 NMS → 跨边界的目标被截断成半个；"
            "该筛选时用了聚类 → 密集目标被连成一片。",
            "严谨地说，两者对应图上的两个不同问题："
            "并查集聚类求<strong>连通分量</strong>（等价关系的商集，$O(N^2)$ 建边 + $O(N^2\\alpha)$ 合并）；"
            "NMS 求<strong>按权重贪心的极大独立集</strong>（见第 8 节）。"
            "<em>缓解 chaining 的三条工程手段</em>：① 提高连边阈值并额外要求类别一致；"
            "② 用<u>更严格的连边条件</u>（如 IoU 且中心距 &lt; 阈值 且尺度比在范围内）；"
            "③ 只在<u>切片边界带</u>内允许合并（跨片合并的标准做法）——"
            "把「传递性」限制在物理上确实可能是同一目标的区域内。",
        ),
    ])),

    # ============================================================== 7
    ("toposort", "拓扑排序与环检测：从依赖调度到计算图", "".join([
        P("拓扑排序的题面几乎总是<strong>伪装成别的东西</strong>："
          "课程表、编译顺序、任务依赖、<u>算子融合的合法顺序</u>、<u>数据流水线的执行计划</u>。"
          "识别信号只有一个：<strong>「A 必须在 B 之前」这种成对约束</strong>。"),
        TABLE(["写法", "机理", "副产物", "适合"], [
            ["<strong>Kahn</strong>（BFS 式）", "反复取出入度为 0 的结点，删掉它的出边",
             "<u>输出的结点数 &lt; V 就说明有环</u>；天然支持「分层」（同层可并行）", "工程首选"],
            ["<strong>DFS 后序反转</strong>", "DFS 完成时间的逆序就是拓扑序",
             "三色标记可精确定位环上的边", "证明题、找环"],
        ]),
        ASCII("""
三色标记法（DFS 环检测）—— 面试里被问"怎么找到环"时的标准答案
────────────────────────────────────────────────────────────
  白 WHITE = 0  尚未访问
  灰 GRAY  = 1  正在递归栈上（本次 DFS 的祖先链上）
  黑 BLACK = 2  子树已全部完成

  dfs(u): color[u] = GRAY
          for v in adj[u]:
              if color[v] == GRAY:  ⇒ 发现 back edge，(u,v) 在环上 ★
              if color[v] == WHITE: dfs(v)
          color[u] = BLACK

关键点：只有"指向灰色结点"才是环。
       指向黑色结点只是 DAG 里的重复汇聚（forward / cross edge），不是环。
       ── 这一条是最高频的错误来源：用一个 visited 集合是判不出环的。
""".rstrip()),
        P("<strong>Kahn 的分层副产物在工程上比拓扑序本身更有用</strong>："
          "同一层的任务之间没有依赖，<u>可以并行执行</u>；层数就是<strong>关键路径长度</strong>，"
          "即在无限并行度下的最短完成时间。"
          "<em>这直接对应 C63-04 的延迟预算分解：把感知流水线画成 DAG，"
          "关键路径决定了端到端延迟的下界，优化非关键路径上的算子是白费力气。</em>"),
        H3("在本岗位上，拓扑序出现在哪"),
        UL([
            "<strong>训练/评测流水线的依赖调度</strong>：数据下载 → 解码 → 增强 → 训练 → 导出 → 量化 → 评测。"
            "环 = 配置写错了（比如「评测依赖导出、导出又依赖评测报告」），要在启动前就检出并<u>指出环上的边</u>。",
            "<strong>计算图的算子融合与执行顺序</strong>：TensorRT / 编译器做融合时必须保持拓扑序合法（见 C60）。",
            "<strong>DAG 上的最长路 = 关键路径</strong>：按拓扑序做一遍 DP 就能求，$O(V+E)$。"
            "<em>这是「DAG 上一切 DP 都按拓扑序推」的最简例子，与模块 04 的遍历顺序是同一件事。</em>",
        ]),
        CALLOUT("intuition", "<strong>一句话记住</strong>：<u>拓扑排序 = 在 DAG 上找一个合法的线性执行顺序；"
                             "它存在 ⟺ 图无环</u>。所以「拓扑排序」与「环检测」是同一个算法的两种问法——"
                             "Kahn 跑完数一下输出了几个结点，就同时回答了两个问题。"),
    ])),

    # ============================================================== 8
    ("nms-graph", "图视角下的 NMS：极大独立集与贪心近似", "".join([
        P("这一节把前面所有东西收束到一个观点上，也是本模块<strong>最值得在面试里主动抛出的一段</strong>。"
          "它不需要你写代码，只需要 60 秒把话说清楚。（<em>NMS 的手撕实现在 C61-05，这里不重复。</em>）"),
        H3("建模：把 NMS 写成图问题"),
        P("给定 $N$ 个候选框，每个框 $i$ 有分数 $s_i$。构造<strong>冲突图</strong> $G=(V,E)$："
          "$V$ 是全部候选框，$(i,j)\\in E$ 当且仅当 $\\mathrm{IoU}(i,j) > \\tau$（「这两个框互相冲突」）。"
          "那么："),
        UL([
            "NMS 的输出集合 $S$ 满足：<strong>任意两个被保留的框之间没有边</strong>——"
            "$S$ 是 $G$ 的一个 <span class=\"term\">independent set</span>（独立集）。",
            "而且 $S$ 是<strong>极大的</strong>（maximal）：任何被抑制的框都至少与 $S$ 中某个框冲突，"
            "所以往 $S$ 里再加任何一个框都会破坏独立性。",
            "我们真正想要的是<strong>最大权独立集</strong>（maximum weight independent set, MWIS）——"
            "在保证两两不冲突的前提下让保留框的总分最高。",
        ]),
        MATH("\\max_{S\\subseteq V}\\;\\sum_{i\\in S}s_i "
             "\\quad\\text{s.t.}\\quad \\forall\\,i,j\\in S:\\;(i,j)\\notin E"),
        P("<strong>关键结论</strong>：一般图上的 MWIS 是 <span class=\"term\">NP-hard</span> 的"
          "（而且在最坏情况下连好的近似都难）。"
          "所以<u>贪心 NMS——按分数降序扫描、能加就加——正是 MWIS 的标准贪心近似算法</u>。"
          "这一句话同时解释了三件事："),
        OL([
            "<strong>为什么 NMS 是贪心的、为什么它不最优</strong>：它是 NP-hard 问题的启发式。",
            "<strong>为什么它「先排序」不可省</strong>：贪心的近似质量完全依赖那个全序"
            "（分数并列时 tie-break 不同 → 输出不同，见模块 02 的确定性讨论）。",
            "<strong>贪心的近似比是有保证的</strong>：按权降序的贪心至少能拿到 "
            "$\\mathrm{OPT}/(\\Delta+1)$，其中 $\\Delta$ 是冲突图的最大度。"
            "<em>$\\Delta$ 小（稀疏场景）时贪心几乎最优；$\\Delta$ 大（密集场景）时才可能明显次优</em>——"
            "这恰好解释了「NMS 在密集小目标场景里表现变差」这个经验现象。",
        ]),
        H3("一维特例：可以精确解"),
        P("如果冲突关系来自<strong>一维区间的重叠</strong>（比如只看 $x$ 轴投影、或时序上的片段），"
          "冲突图是<span class=\"term\">interval graph</span>（区间图），"
          "而<u>区间图上的最大权独立集可以用 DP 在 $O(n\\log n)$ 内精确求解</u>"
          "——这正是「加权区间调度」。<strong>模块 04 会把它写出来，"
          "并与贪心 NMS 对比，量化贪心到底次优多少。</strong>"
          "<em>面试里能说出「二维一般图是 NP-hard，但一维区间图有多项式精确解」，"
          "是很强的信号：说明你知道难度来自哪里，而不是背下了「NMS 是贪心」这句话。</em>"),
        TABLE(["方法", "图论视角", "代价", "什么时候值得"], [
            ["贪心 NMS", "按权降序的极大独立集", "$O(N^2)$（排序后扫描）", "默认；$\\Delta$ 小时几乎最优"],
            ["Soft-NMS", "不删点，<u>降低邻居的权重</u>", "同上", "密集遮挡场景，召回优先"],
            ["Matrix / Cluster NMS", "把抑制关系写成矩阵一次算完", "可向量化，GPU 友好", "延迟敏感、$N$ 大"],
            ["并查集聚类", "求<strong>连通分量</strong>（传递闭包）", "$O(N^2\\alpha)$", "要「合并碎片」而不是「挑代表」"],
            ["加权区间调度 DP", "区间图上的 MWIS <u>精确解</u>", "$O(n\\log n)$，仅一维", "一维/时序去重；作为贪心的上界基准"],
            ["Learned NMS", "用网络学习成对关系", "训练成本 + 推理开销", "研究方向，量产少见"],
        ]),
        CALLOUT("intuition", "<strong>60 秒答法（可以背下来）</strong>："
                             "「把每个框当顶点、IoU 超阈值连边，NMS 的输出就是这张冲突图上的一个<u>极大独立集</u>；"
                             "我们想要的是<u>最大权独立集</u>，但一般图上这是 NP-hard 的，"
                             "所以贪心 NMS 是它的近似算法，近似比与冲突图的最大度有关——"
                             "这解释了为什么密集场景下 NMS 更容易出问题。"
                             "如果冲突只来自一维区间重叠，图是区间图，可以用 DP 精确解，"
                             "那就是加权区间调度。」<em>三句话，把一个「大家都会用」的模块讲出了结构。</em>"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("图算法是教科书里最成熟的一块，但它与视觉系统的接缝处仍有活跃问题——"
          "这些内容不会出现在一面的编程题里，却是「你平时关注什么」这类问题的好素材。"),
        UL([
            "<strong>并查集的并行化仍然没有完美答案。</strong>路径压缩本质是「写共享内存」，"
            "并发下要用无锁 CAS，而 GPU 上的连通域标记（block-based union-find、label equivalence）"
            "是一个持续被刷新的工程赛道。<em>本质矛盾：并查集的高效来自「破坏结构以换取摊还」，"
            "而并行化要求「结构可预测」。</em>",
            "<strong>动态图连通性（decremental / fully dynamic）是真难题。</strong>"
            "只加边有并查集，只删边或又加又删就需要复杂得多的结构（Holm–de Lichtenberg–Thorup 等），"
            "常数大到实践中常常干脆重算。<em>这是「离线倒序处理」这个技巧在工业界如此常见的原因。</em>",
            "<strong>把 NMS 做成可学习、可微的模块。</strong>Learning NMS（Hosang 2017）用网络学成对关系；"
            "无 NMS 检测器（DETR 的一对一匹配、YOLOv10 的一致双分配，见 C53/C54）"
            "则是<u>从根上绕开这个 NP-hard 问题</u>——"
            "<strong>把「推理期去重」变成「训练期就不产生重复」。</strong>"
            "<em>这个视角转换是近五年检测领域最重要的思想之一，值得在面试里主动提。</em>",
            "<strong>GPU 上的 BFS 有本质的负载不均衡问题。</strong>层宽在图上剧烈变化，"
            "导致线程空转；frontier 压缩、方向优化（direction-optimizing BFS：稠密层改成自底向上）"
            "是标准手段。<em>网格图相对规则，所以 CV 里的 flood fill 反而比一般图 BFS 好并行。</em>",
            "<strong>图神经网络与经典图算法的关系正在被重新理解。</strong>"
            "「algorithmic alignment」这条线在研究 GNN 能否学会 BFS / Bellman-Ford 这类算法；"
            "结论倾向于：<u>结构对齐的模型才泛化</u>。"
            "<em>对面试的启示：当被问「为什么不用学习方法替代 NMS」，"
            "可以答「因为经典算法在这个问题上的结构先验极强，学习方法要赢必须先对齐这个结构」。</em>",
            "<strong>LLM 时代这类题还考不考？</strong>题目本身在贬值，"
            "但<u>「说清一个图算法的不变量与失效模式」</u>在升值。"
            "本模块的两组对拍（递归 vs 迭代、并查集聚类 vs 逐对比较）训练的正是这种能力。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：CLRS <em>Introduction to Algorithms</em> 第 19 章"
                         "（Data Structures for Disjoint Sets）——只读 19.3 与 19.4，"
                         "路径压缩 + 按秩合并的 $O(m\\,\\alpha(n))$ 证明。"
                         "<strong>★</strong> Tarjan &amp; van Leeuwen, <em>Worst-case Analysis of Set Union Algorithms</em>"
                         "（JACM 1984）——各种压缩/合并组合的紧界，知道结论即可。"
                         "<strong>★</strong> Hosang, Benenson, Schiele, <em>Learning Non-Maximum Suppression</em>"
                         "（CVPR 2017）——<u>把 NMS 当成一个可学习的关系推理问题</u>，"
                         "读引言与问题建模那两节就能拿到本模块第 8 节的全部视角。</p>"
                         "<p>配套材料：Bodla et al., <em>Soft-NMS</em>（ICCV 2017）；"
                         "He, Ren, Wang, Suzuki, <em>The connected-component labeling problem: a review</em>"
                         "（Pattern Recognition 2017，两遍扫描法与 GPU 实现的全景）；"
                         "Rosenfeld, <em>Connectivity in Digital Pictures</em>（JACM 1970，"
                         "4/8 邻域必须互补的拓扑理由）；Kahn 1962（拓扑排序原文，两页）。"
                         "相邻课程：<strong>模块 01</strong>（区间与双指针）、<strong>模块 02</strong>"
                         "（排序确定性：贪心 NMS 的 tie-break）、<strong>模块 04</strong>"
                         "（把 NMS 建模成加权区间调度并用 DP 求精确解）、"
                         "<strong>C57 模块 04</strong>（切片推理的跨片合并——并查集的真实战场）、"
                         "<strong>C61 模块 05</strong>（IoU/NMS/mAP 手撕，本模块不重复）、"
                         "<strong>C63 模块 04</strong>（DAG 关键路径与延迟预算分解）。"
                         "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · 树、图与搜索（递归转迭代 / 并查集 / 连通域标记 / NMS 即极大独立集）

目标：把「树图题」从背模板变成三件可验证的能力 ——
**能把任何递归改写成显式栈**、**能认出网格题就是连通域标记**、
**能用图论语言解释 NMS 为什么是贪心近似**。

本 notebook 你会亲手实现：

1. **递归三要素的三个坑**：返回值 vs 答案（树直径）、$O(n^2)$ 的判平衡、**栈深度实测爆栈**
2. **四种遍历的递归与迭代双实现**，在 2000 棵随机树上**逐一对拍**；
   后序两种写法（前序+反转 / **stage 状态机**）；用状态机迭代做树形 DP
3. **BST 验证的两种正解 + 一种经典错解**（只比孩子），用反例把错解抓出来
4. **BFS 最短路 / 多源 BFS（= 距离变换）/ Dijkstra 惰性删除 / 0-1 BFS**，
   与 Floyd 暴力全源最短路对拍
5. **网格连通域标记两条路线对拍**：BFS 泛洪一遍法 vs **逐像素两遍扫描 + 并查集**；
   4/8 邻域给出不同答案的最小反例；mask → bbox
6. **并查集**（路径压缩 + 按秩合并）：把「不优化会退化成链」跑成数字（步数差 1000 倍）；
   **用于 bbox 聚类**并与逐对比较暴力法对拍；**演示 chaining 失效模式**
7. **拓扑排序 Kahn 分层 + 三色环检测**，与全排列暴力对拍；DAG 关键路径
8. **把 NMS 表述成图上的极大独立集**：暴力枚举求最大权独立集（MWIS），
   量化贪心的次优程度，并验证 $\\mathrm{greedy} \\ge \\mathrm{OPT}/(\\Delta+1)$

> 心智模型：**递归 = 隐式栈；把栈显式化，控制流就变成了可检查、可持久化、可限长的数据。
> 而图算法在 CV 里几乎总是换了个名字：flood fill、连通域、框聚类、冲突图。**

> 与 **C61 模块 05** 的分工：IoU / NMS / mAP 的手撕实现在那里，本 notebook 只用它们做**结构分析**。"""),

    md("""## 1 · 递归三要素与它的三个隐性代价

先建一棵树，然后把三个最常见的坑各跑一遍：
**返回值与答案混淆**、**重算导致的 $O(n^2)$**、**栈深度**。"""),

    code("""import sys, time, random, heapq, itertools
from collections import deque, defaultdict, Counter
import numpy as np

print('Python', sys.version.split()[0], '| numpy', np.__version__,
      '| 递归上限', sys.getrecursionlimit())


class Node:
    __slots__ = ('val', 'left', 'right')
    def __init__(self, val, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build(vals):
    \"\"\"从层序列表建树，None 表示空位（LeetCode 的标准输入格式）。\"\"\"
    if not vals or vals[0] is None:
        return None
    root = Node(vals[0]); q = deque([root]); i = 1
    while q and i < len(vals):
        node = q.popleft()
        for side in ('left', 'right'):
            if i < len(vals):
                v = vals[i]; i += 1
                if v is not None:
                    child = Node(v); setattr(node, side, child); q.append(child)
    return root


def rand_tree(rnd, n):
    \"\"\"随机形状二叉树，结点值是 0..n-1 的一个排列（值互不相同 ⇒ 遍历序列可直接比较）。\"\"\"
    if n == 0:
        return None
    vals = list(range(n)); rnd.shuffle(vals)
    root = Node(vals[0]); nodes = [root]
    for v in vals[1:]:
        while True:                        # n 个结点总有 n+1 个空位，必然能插进去
            p = rnd.choice(nodes)
            if rnd.random() < 0.5:
                if p.left is None:
                    p.left = Node(v); nodes.append(p.left); break
            else:
                if p.right is None:
                    p.right = Node(v); nodes.append(p.right); break
    return root


def unlink_chain(node):
    \"\"\"迭代解链：超长链不能靠引用计数级联释放 —— 那是 C 栈上的递归析构，会段错误。
       这也是「后序遍历用于资源释放」的现实版本。\"\"\"
    while node is not None:
        nxt, node.left = node.left, None
        node = nxt


def nodes_of(root):
    \"\"\"层序收集全部结点（迭代，安全）。\"\"\"
    out, q = [], deque([root] if root else [])
    while q:
        n = q.popleft(); out.append(n)
        if n.left:  q.append(n.left)
        if n.right: q.append(n.right)
    return out


T = build([1, 2, 3, 4, 5, None, 6])
print('测试树 =', [n.val for n in nodes_of(T)], '（层序）')
assert len(nodes_of(T)) == 6
print('✅ 树的构造与层序收集就绪。')"""),

    code("""# ── 坑 ①：返回值 ≠ 答案（树直径）──

def diameter(root):
    \"\"\"直径 = 任意两结点间最长路径的**边数**。
       契约：内层 depth() 返回「以 node 为根向下的最大深度」；
             **答案挂在外部变量 best 上** —— 这两个量不是一回事。\"\"\"
    best = 0
    def depth(node):
        nonlocal best
        if node is None:
            return 0                       # 终止条件
        l, r = depth(node.left), depth(node.right)
        best = max(best, l + r)            # 经过 node 的最长路径（合并）
        return 1 + max(l, r)               # 返回值：深度，绝不是 l + r
    depth(root)
    return best


def diameter_brute(root):
    \"\"\"暴力真值：把树当无向图，从每个结点跑一次 BFS，取最大距离。\"\"\"
    ns = nodes_of(root)
    if not ns:
        return 0
    adj = defaultdict(list)
    for n in ns:
        for c in (n.left, n.right):
            if c:
                adj[id(n)].append(id(c)); adj[id(c)].append(id(n))
    best = 0
    for s in ns:
        dist = {id(s): 0}; q = deque([id(s)])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1; q.append(v)
        best = max(best, max(dist.values()))
    return best


# ── 坑 ②：判平衡写成「每层重算高度」→ O(n^2) ──
H_CALLS = 0
def height(node):
    global H_CALLS
    H_CALLS += 1
    return 0 if node is None else 1 + max(height(node.left), height(node.right))

def balanced_slow(node):
    if node is None:
        return True
    return (abs(height(node.left) - height(node.right)) <= 1
            and balanced_slow(node.left) and balanced_slow(node.right))

def balanced_fast(node):
    \"\"\"后序一趟：同时返回 (高度, 是否平衡)。这就是「自下而上聚合」的标准形状。\"\"\"
    def go(n):
        if n is None:
            return 0, True
        hl, bl = go(n.left)
        hr, br = go(n.right)
        return 1 + max(hl, hr), (bl and br and abs(hl - hr) <= 1)
    return go(node)[1]


def sum_heights_slow(node):
    \"\"\"❌ 「在每个结点上重新算一遍高度」的典型写法 —— 重复计算，最坏 O(n^2)。\"\"\"
    if node is None:
        return 0
    return height(node) + sum_heights_slow(node.left) + sum_heights_slow(node.right)

def sum_heights_fast(node):
    \"\"\"✅ 后序一趟：高度在返回值里往上带，顺手累加。O(n)。\"\"\"
    total = 0
    def go(n):
        nonlocal total
        if n is None:
            return 0
        h = 1 + max(go(n.left), go(n.right))
        total += h
        return h
    go(node)
    return total


rnd_t = random.Random(0)
for _ in range(500):
    t = rand_tree(rnd_t, rnd_t.randint(0, 12))
    assert diameter(t) == diameter_brute(t)
    assert balanced_slow(t) == balanced_fast(t)
    assert sum_heights_slow(t) == sum_heights_fast(t)
print('✅ 500 棵随机树：直径与暴力 BFS 一致；两种判平衡、两种高度和结果一致。')

# 把「重复计算」跑成数字：左偏斜树上，slow 版的 height 调用次数是二次的
print('\\n%5s %18s %14s' % ('n', 'slow 的 height 调用', '≈ n^2'))
for n in (50, 100, 200, 400):
    chain = None
    for v in range(n):
        chain = Node(v, left=chain)        # 纯左链 —— 重复计算的最坏形状
    H_CALLS = 0; sum_heights_slow(chain); slow_calls = H_CALLS
    H_CALLS = 0; sum_heights_fast(chain); fast_calls = H_CALLS
    print('%5d %18d %14d   （fast 版的 height 调用 = %d）' % (n, slow_calls, n * n, fast_calls))
    assert slow_calls > 0.4 * n * n, 'slow 版确实是 O(n^2)'
    assert fast_calls == 0, 'fast 版根本不调用 height —— 高度在返回值里往上带'
    unlink_chain(chain)
print('\\n✅ 结论：「在每个结点上重新算高度」= O(n^2)，「后序一趟把高度带上来」= O(n)。')
print('   判平衡是同一个坑的小一号版本（最坏 O(n log n)）：')
print('   面试话术是「不能每层重算高度，要后序一趟同时返回高度和平衡标志」。')"""),

    code("""# ── 坑 ③：栈深度 —— 把 RecursionError 跑出来 ──

def depth_rec(node):
    if node is None:
        return 0
    return 1 + max(depth_rec(node.left), depth_rec(node.right))

def depth_iter(root):
    \"\"\"显式栈版：深度多大都不会爆。栈里存 (结点, 该结点的深度)。\"\"\"
    if root is None:
        return 0
    best, st = 0, [(root, 1)]
    while st:
        node, d = st.pop()
        best = max(best, d)
        if node.left:  st.append((node.left, d + 1))
        if node.right: st.append((node.right, d + 1))
    return best


N_DEEP = 3 * sys.getrecursionlimit()        # 稳超上限，不依赖具体环境
chain = None
for v in range(N_DEEP):
    chain = Node(v, left=chain)

blew_up = False
try:
    depth_rec(chain)
except RecursionError:
    blew_up = True
print('深度 %d 的左链：' % N_DEEP)
print('  递归版 →', 'RecursionError（默认上限 %d）' % sys.getrecursionlimit() if blew_up else '居然没炸')
assert blew_up, '递归版必须在这里爆栈 —— 这就是本节要证明的事'
print('  迭代版 →', depth_iter(chain))
assert depth_iter(chain) == N_DEEP

t0 = time.perf_counter(); depth_iter(chain); t_it = time.perf_counter() - t0
print('  迭代版耗时 %.1f ms' % (t_it * 1000))

unlink_chain(chain); chain = None           # 迭代解链释放（见上一格的 unlink_chain）

print('\\n❗ 反面教材：sys.setrecursionlimit(10**6) 不是解法。')
print('   Python 的上限是为了保护真实的 C 栈（通常 8 MB）；调过头之后爆的是 C 栈，')
print('   表现为**段错误 / 进程被杀，没有异常、没有回溯、日志里什么都没有**。')
print('   车端的感知进程崩了就是输出断流 —— 所以深度不可控时一律写迭代版。')"""),

    md("""## 2 · 递归转迭代：前序 / 中序 / 后序 / 树形 DP

四段代码，一个共同结构：**显式栈就是把「同一个结点被经过三次」这件事写出来**。

- 前序：进入时做事 → 结点弹出后不再需要 → **单栈够用**（先压右后压左）
- 中序：左子树完成时做事 → 需要「一路向左把祖先链压栈」
- 后序：两个孩子都完成才做事 → **必须区分「第一次见」和「孩子回来了」** → 带 `stage`
- 树形 DP：后序 + 携带子树返回值 → 只有 `stage` 版本能做（「前序+反转」的技巧在这里失效）"""),

    code("""# ── 递归版（真值）──
def preorder_rec(n):  return [] if n is None else [n.val] + preorder_rec(n.left) + preorder_rec(n.right)
def inorder_rec(n):   return [] if n is None else inorder_rec(n.left) + [n.val] + inorder_rec(n.right)
def postorder_rec(n): return [] if n is None else postorder_rec(n.left) + postorder_rec(n.right) + [n.val]


# ── 迭代版 ──
def preorder_iter(root):
    out, st = [], ([root] if root else [])
    while st:
        n = st.pop(); out.append(n.val)
        if n.right: st.append(n.right)     # 先压右、后压左 ⇒ 栈是 LIFO，弹出顺序才是 左→右
        if n.left:  st.append(n.left)
    return out


def inorder_iter(root):
    out, st, cur = [], [], root
    while st or cur:
        while cur:                         # 一路向左：把整条祖先链压栈
            st.append(cur); cur = cur.left
        n = st.pop(); out.append(n.val)    # 弹出 ⇔ 「左子树已完成」这一时刻
        cur = n.right
    return out


def postorder_iter_rev(root):
    \"\"\"写法 1：按 根→右→左 做前序，最后整体反转。最短、好背。
       局限：它只产出**访问序列**，无法在后序时刻使用子树的返回值。\"\"\"
    out, st = [], ([root] if root else [])
    while st:
        n = st.pop(); out.append(n.val)
        if n.left:  st.append(n.left)      # 注意左右顺序与前序相反
        if n.right: st.append(n.right)
    return out[::-1]


def postorder_iter_stage(root):
    \"\"\"写法 2：栈里存 (结点, stage)。stage 就是递归的「返回点编号」：
       0 = 还没展开，1 = 左子树回来了，2 = 右子树也回来了。通用、可携带返回值。\"\"\"
    out, st = [], ([(root, 0)] if root else [])
    while st:
        n, stage = st.pop()
        if stage == 0:
            st.append((n, 1))
            if n.left:  st.append((n.left, 0))
        elif stage == 1:
            st.append((n, 2))
            if n.right: st.append((n.right, 0))
        else:
            out.append(n.val)              # 两个孩子都完成 ⇒ 后序时刻
    return out


rnd_i = random.Random(1)
for _ in range(2000):
    t = rand_tree(rnd_i, rnd_i.randint(0, 14))
    assert preorder_iter(t)       == preorder_rec(t)
    assert inorder_iter(t)        == inorder_rec(t)
    assert postorder_iter_rev(t)  == postorder_rec(t)
    assert postorder_iter_stage(t) == postorder_rec(t)
print('✅ 2000 棵随机树：四个迭代版与递归版**逐序列完全一致**。')
print('   T =', [n.val for n in nodes_of(T)], '（层序）')
print('   前序', preorder_iter(T), ' 中序', inorder_iter(T), ' 后序', postorder_iter_stage(T))"""),

    code("""# ── stage 状态机做树形 DP：迭代地算出每个结点的子树和 ──

def subtree_sums_rec(root):
    sums = {}
    def go(n):
        if n is None:
            return 0
        s = n.val + go(n.left) + go(n.right)
        sums[id(n)] = s
        return s
    go(root)
    return sums


def subtree_sums_iter(root):
    \"\"\"和 postorder_iter_stage 同一个骨架，只是在 stage==2 时读取孩子的结果。
       这就是「任何递归都能机械地转成显式栈」的完整示范。\"\"\"
    sums = {}
    st = [(root, 0)] if root else []
    while st:
        n, stage = st.pop()
        if stage == 0:
            st.append((n, 1))
            if n.left:  st.append((n.left, 0))
        elif stage == 1:
            st.append((n, 2))
            if n.right: st.append((n.right, 0))
        else:
            sums[id(n)] = n.val + sums.get(id(n.left), 0) + sums.get(id(n.right), 0)
    return sums


rnd_d = random.Random(2)
for _ in range(1000):
    t = rand_tree(rnd_d, rnd_d.randint(0, 14))
    a, b = subtree_sums_rec(t), subtree_sums_iter(t)
    assert a == b, '两种实现的子树和字典必须逐键相等'
    if t is not None:
        assert a[id(t)] == sum(n.val for n in nodes_of(t))   # 根的子树和 = 全部结点之和
print('✅ 1000 棵随机树：迭代树形 DP 与递归结果逐键一致。')

# 深链上迭代版照样работает，递归版爆栈
N2 = 2 * sys.getrecursionlimit()
chain2 = None
for v in range(1, N2 + 1):
    chain2 = Node(v, left=chain2)
try:
    subtree_sums_rec(chain2); rec_ok = True
except RecursionError:
    rec_ok = False
it = subtree_sums_iter(chain2)
print('深度 %d 的链：递归版成功？%s   迭代版根的子树和 = %d（应为 1+2+...+%d = %d）'
      % (N2, rec_ok, it[id(chain2)], N2, N2 * (N2 + 1) // 2))
assert not rec_ok and it[id(chain2)] == N2 * (N2 + 1) // 2
unlink_chain(chain2); chain2 = None
print('\\n📌 转换配方（背这三行就够）：栈存 (状态, 阶段)；阶段 0 展开、阶段 k 处理第 k 个子结果；')
print('   子结果放在一个以「结点身份」为键的表里。任何递归都能这样机械地转过来 ——')
print('   包括模块 04 的记忆化搜索。')"""),

    md("""## 3 · 层序遍历与 BST：两个必考性质

层序的唯一要点：**进入循环先记下 `n = len(queue)`，只处理这 `n` 个**（它们恰好是当前整层）。
不记 `n` 就没有「层」的概念，「每层最大值」「之字形」「右视图」全都写不出来。

BST 的唯一要点：**中序遍历严格递增**。「只比较结点与它的两个孩子」是经典错解。"""),

    code("""def level_order(root):
    out, q = [], deque([root] if root else [])
    while q:
        n_this = len(q)                    # ← 关键的一行：当前层的宽度
        level = []
        for _ in range(n_this):
            node = q.popleft(); level.append(node.val)
            if node.left:  q.append(node.left)
            if node.right: q.append(node.right)
        out.append(level)
    return out


def zigzag(root):
    return [lv if i % 2 == 0 else lv[::-1] for i, lv in enumerate(level_order(root))]

def right_view(root):
    return [lv[-1] for lv in level_order(root)]


L = level_order(T)
print('层序   =', L)
print('之字形 =', zigzag(T))
print('右视图 =', right_view(T))
print('每层最大值 =', [max(lv) for lv in L])
assert L == [[1], [2, 3], [4, 5, 6]]
assert zigzag(T) == [[1], [3, 2], [4, 5, 6]]
assert right_view(T) == [1, 3, 6]

rnd_l = random.Random(3)
for _ in range(1000):
    t = rand_tree(rnd_l, rnd_l.randint(0, 14))
    lv = level_order(t)
    assert sum(len(x) for x in lv) == len(nodes_of(t))       # 每个结点恰好出现一次
    assert len(lv) == depth_iter(t)                          # 层数 == 树高
    assert sorted(v for x in lv for v in x) == sorted(n.val for n in nodes_of(t))
print('✅ 1000 棵随机树：层数 == 树高，且每个结点恰好被分到一层。')
print('   空间复杂度对比：BFS 是 O(最大层宽)，DFS 是 O(树高) ——')
print('   深而窄的树用 DFS，浅而宽的树用 BFS。这是真实的工程判据。')"""),

    code("""# ── BST 验证：两种正解 + 一种经典错解 ──

def is_bst_inorder(root):
    \"\"\"解法 A（中序）：只需记住「上一个访问的值」，必须严格递增。\"\"\"
    prev = None
    for v in inorder_iter(root):
        if prev is not None and v <= prev:
            return False
        prev = v
    return True


def is_bst_bounds(node, lo=None, hi=None):
    \"\"\"解法 B（前序）：把 (lo, hi) 开区间约束自上而下传给孩子。\"\"\"
    if node is None:
        return True
    if lo is not None and node.val <= lo:
        return False
    if hi is not None and node.val >= hi:
        return False
    return (is_bst_bounds(node.left, lo, node.val)
            and is_bst_bounds(node.right, node.val, hi))


def is_bst_naive(node):
    \"\"\"❌ 经典错解：只比较结点与它的两个孩子。局部合法 ≠ 全局合法。\"\"\"
    if node is None:
        return True
    if node.left and node.left.val >= node.val:
        return False
    if node.right and node.right.val <= node.val:
        return False
    return is_bst_naive(node.left) and is_bst_naive(node.right)


BAD = build([10, 5, 15, None, 12])       # 12 在根的**左**子树里，却比根大
print('反例树：根 10，左孩子 5，5 的右孩子 12')
print('  中序序列 =', inorder_iter(BAD), ' → 不是递增')
print('  is_bst_inorder =', is_bst_inorder(BAD), ' is_bst_bounds =', is_bst_bounds(BAD),
      ' is_bst_naive =', is_bst_naive(BAD), ' ← 错解说它是 BST')
assert is_bst_inorder(BAD) is False and is_bst_bounds(BAD) is False
assert is_bst_naive(BAD) is True, '这就是错解的失效点'


def bst_insert(root, v):
    if root is None:
        return Node(v)
    if v < root.val:
        root.left = bst_insert(root.left, v)
    elif v > root.val:
        root.right = bst_insert(root.right, v)
    return root


rnd_b = random.Random(4)
wrong = 0
for _ in range(1500):
    if rnd_b.random() < 0.5:                                  # 一半是真 BST
        t = None
        for v in rnd_b.sample(range(30), rnd_b.randint(0, 10)):
            t = bst_insert(t, v)
    else:                                                     # 一半是随机树
        t = rand_tree(rnd_b, rnd_b.randint(0, 10))
    a, b, c = is_bst_inorder(t), is_bst_bounds(t), is_bst_naive(t)
    assert a == b, '两种正解必须一致'
    if c != a:
        wrong += 1
print('\\n✅ 1500 棵树：两种正解结果完全一致；错解有 %d 棵判错。' % wrong)
assert wrong > 0
print('   面试加分说法：「有两种写法 —— 中序必须严格递增，或者前序向下传 (lo, hi) 约束；')
print('   只比孩子是错的，反例是「左子树里藏一个比根大的结点」。」')"""),

    md("""## 4 · BFS / 多源 BFS / Dijkstra / 0-1 BFS

四段代码，一条主线：**BFS 的第一次到达即最优（边权相同）；边权不同就必须换出队规则。**

- BFS：队列，**入队时标记 visited**（不是出队时）
- 多源 BFS：所有源点一次性入队 → 得到「到最近源点的距离」= **距离变换**
- Dijkstra：堆 + **惰性删除**（不 decrease-key，出堆时用 `d > dist[u]` 过滤过期条目）
- 0-1 BFS：权 0 走 `appendleft`、权 1 走 `append`，双端队列足以维持单调性 → 线性"""),

    code("""def bfs_dist(adj, s):
    \"\"\"无权图单源最短路。dist 同时充当 visited —— 一个字典办两件事。\"\"\"
    dist = {s: 0}; q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:              # ★ 入队时就标记；写在出队时会导致重复入队
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def bfs_dist_buggy(adj, s):
    \"\"\"❌ 出队时才标记：同一个结点被反复入队，队列规模从 O(V) 涨到 O(E)。\"\"\"
    dist = {}; q = deque([(s, 0)]); pushes = 0
    while q:
        u, d = q.popleft()
        if u in dist:
            continue
        dist[u] = d
        for v in adj[u]:
            q.append((v, d + 1)); pushes += 1
    return dist, pushes


def dijkstra(adjw, s):
    \"\"\"边权非负的单源最短路。O((V+E) log V)。\"\"\"
    INF = float('inf')
    dist = {s: 0.0}; heap = [(0.0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, INF):
            continue                       # ★ 惰性删除：过期条目直接跳过（代替 decrease-key）
        for v, w in adjw[u]:
            nd = d + w
            if nd < dist.get(v, INF):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def bfs01(adjw, s):
    \"\"\"边权只有 0/1 时的线性算法：双端队列维持「队内距离至多两个相邻取值」。\"\"\"
    INF = float('inf')
    dist = {s: 0}; dq = deque([s])
    while dq:
        u = dq.popleft()
        for v, w in adjw[u]:
            nd = dist[u] + w
            if nd < dist.get(v, INF):
                dist[v] = nd
                dq.appendleft(v) if w == 0 else dq.append(v)
    return dist


def floyd(n, edges):
    \"\"\"暴力真值：全源最短路 O(n^3)。\"\"\"
    INF = float('inf')
    D = [[INF] * n for _ in range(n)]
    for i in range(n):
        D[i][i] = 0
    for u, v, w in edges:
        D[u][v] = min(D[u][v], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if D[i][k] + D[k][j] < D[i][j]:
                    D[i][j] = D[i][k] + D[k][j]
    return D


rnd_g = random.Random(7)
for _ in range(300):
    n = rnd_g.randint(1, 8)
    edges = [(rnd_g.randrange(n), rnd_g.randrange(n), rnd_g.choice([0, 1]))
             for _ in range(rnd_g.randint(0, 14))]
    adj  = defaultdict(list); adjw = defaultdict(list)
    for u, v, w in edges:
        adj[u].append(v); adjw[u].append((v, w))
    for i in range(n):
        adj[i]; adjw[i]
    D = floyd(n, edges)
    for s in range(n):
        dd = dijkstra(adjw, s)
        d01 = bfs01(adjw, s)
        for t in range(n):
            truth = D[s][t]
            assert (dd.get(t, float('inf')) == truth), ('dijkstra', edges, s, t)
            assert (d01.get(t, float('inf')) == truth), ('bfs01', edges, s, t)
        # 边权全 1 时 BFS 必须等于 Dijkstra
        adj1 = defaultdict(list)
        for u, v, _ in edges:
            adj1[u].append(v)
        for i in range(n):
            adj1[i]
        b = bfs_dist(adj1, s)
        d1 = dijkstra({i: [(v, 1) for v in adj1[i]] for i in range(n)}, s)
        assert b == {k: int(v) for k, v in d1.items()}, ('bfs vs dijkstra', edges, s)
print('✅ 300 张随机图 x 全部源点：Dijkstra、0-1 BFS 与 Floyd 全源真值完全一致；')
print('   边权全 1 时 BFS == Dijkstra。')

# 「出队才标记」的代价：入队次数
star = defaultdict(list)
for i in range(1, 60):
    star[0].append(i)
    for j in range(1, 60):
        star[i].append(j)
_, pushes = bfs_dist_buggy(star, 0)
print('\\n稠密图上「出队才标记」的入队次数 =', pushes, ' vs 正确版最多 V-1 =', 59)
assert pushes > 20 * 59
print('   ↑ 队列规模从 O(V) 涨到 O(E)。在网格上这是 4 倍常数，在稠密图上是数量级差异。')"""),

    code("""# ── 多源 BFS = 距离变换（CV 里天天用的那个）──

def distance_transform(mask):
    \"\"\"多源 BFS：每个像素到最近前景像素（mask==1）的 4 邻域步数。
       所有源点**一次性入队** ⇒ 一遍 BFS 就得到「到最近源」的距离。\"\"\"
    H, W = mask.shape
    INF = 10**9
    dist = np.full((H, W), INF, dtype=np.int64)
    q = deque()
    for i in range(H):
        for j in range(W):
            if mask[i, j]:
                dist[i, j] = 0; q.append((i, j))
    while q:
        i, j = q.popleft()
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < H and 0 <= nj < W and dist[ni, nj] > dist[i, j] + 1:
                dist[ni, nj] = dist[i, j] + 1
                q.append((ni, nj))
    return dist


def distance_transform_brute(mask):
    \"\"\"暴力真值：无障碍网格上，4 邻域最短步数就是到最近源点的曼哈顿距离。\"\"\"
    H, W = mask.shape
    src = [(i, j) for i in range(H) for j in range(W) if mask[i, j]]
    out = np.full((H, W), 10**9, dtype=np.int64)
    for i in range(H):
        for j in range(W):
            if src:
                out[i, j] = min(abs(i - a) + abs(j - b) for a, b in src)
    return out


rnd_dt = random.Random(11)
for _ in range(200):
    H, W = rnd_dt.randint(1, 7), rnd_dt.randint(1, 7)
    m = (np.array([[rnd_dt.random() < 0.25 for _ in range(W)] for _ in range(H)])).astype(np.int64)
    assert np.array_equal(distance_transform(m), distance_transform_brute(m))
print('✅ 200 张随机 mask：多源 BFS 的距离场 == 到最近前景的曼哈顿距离（暴力真值）。')

demo = np.zeros((5, 9), dtype=np.int64); demo[2, 1] = 1; demo[0, 7] = 1
print('\\nmask（1 = 前景）:')
print(demo)
print('距离变换:')
print(distance_transform(demo))
print('\\n📌 一次 BFS 解决 k 个源点，不需要跑 k 次单源 —— 这就是多源 BFS 的全部价值。')
print('   CV 用途：边缘距离场、骨架化、watershed 的种子扩张、mask 空洞的距离判据。')"""),

    md("""## 5 · 网格连通域标记：两条路线对拍

**「岛屿数量」= connected component labeling（CCL）。同一个算法，两个名字。**

- 路线 ①：**BFS/DFS 泛洪一遍法** —— 代码短、常数小；递归版在大连通域上会爆栈
- 路线 ②：**逐像素两遍扫描 + 并查集** —— 顺序访存、可分块并行、内存有确定上界，
  是工业界与 GPU 实现的主流（Hoshen–Kopelman 家族）

两条路线的标号必须**逐像素完全一致**（都按行优先的首次出现顺序编号），下面对拍验证。"""),

    code("""NBR4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
NBR8 = NBR4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def ccl_flood(mask, nbrs=NBR4):
    \"\"\"路线①：BFS 泛洪。返回 (标号图, 连通域个数)；标号 0 = 背景，1..k 按行优先首次出现编号。\"\"\"
    H, W = mask.shape
    lab = np.zeros((H, W), dtype=np.int64)
    k = 0
    for i in range(H):
        for j in range(W):
            if mask[i, j] and lab[i, j] == 0:
                k += 1
                lab[i, j] = k; q = deque([(i, j)])      # 入队即标号
                while q:
                    y, x = q.popleft()
                    for dy, dx in nbrs:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = k; q.append((ny, nx))
    return lab, k


def ccl_two_pass(mask, nbrs=NBR4):
    \"\"\"路线②：逐像素两遍扫描 + 并查集。
       这里内联一个最小并查集（只做路径压缩）；完整版（按秩合并 + 复杂度）见第 6 节。\"\"\"
    H, W = mask.shape
    parent = [0]                                        # 标号从 1 开始，parent[0] 占位

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)           # 小标号当代表元 ⇒ 结果确定

    # 只看「已经扫过」的邻居：dy<0，或同一行的 dx<0
    prev_nbrs = [(dy, dx) for dy, dx in nbrs if dy < 0 or (dy == 0 and dx < 0)]
    tmp = np.zeros((H, W), dtype=np.int64)
    nxt = 0
    for i in range(H):                                  # 第一遍：给临时标号，冲突就 union
        for j in range(W):
            if not mask[i, j]:
                continue
            found = []
            for dy, dx in prev_nbrs:
                ni, nj = i + dy, j + dx
                if 0 <= ni < H and 0 <= nj < W and tmp[ni, nj]:
                    found.append(int(tmp[ni, nj]))
            if not found:
                nxt += 1; parent.append(nxt); tmp[i, j] = nxt
            else:
                lo = min(found)
                tmp[i, j] = lo
                for f in found:
                    union(lo, f)                        # 同一个域被给了两个标号 → 记下等价
    remap, k = {}, 0                                    # 第二遍：代表元 → 1..k
    lab = np.zeros((H, W), dtype=np.int64)
    for i in range(H):
        for j in range(W):
            if tmp[i, j]:
                r = find(int(tmp[i, j]))
                if r not in remap:
                    k += 1; remap[r] = k
                lab[i, j] = remap[r]
    return lab, k


def canon(lab):
    \"\"\"把标号规范化成「行优先首次出现顺序」，让两种实现可以逐像素比较。\"\"\"
    remap, nxt = {}, 0
    out = np.zeros_like(lab)
    for i in range(lab.shape[0]):
        for j in range(lab.shape[1]):
            v = int(lab[i, j])
            if v:
                if v not in remap:
                    nxt += 1; remap[v] = nxt
                out[i, j] = remap[v]
    return out


rnd_c = random.Random(13)
for nbrs, name in ((NBR4, '4 邻域'), (NBR8, '8 邻域')):
    for _ in range(400):
        H, W = rnd_c.randint(1, 8), rnd_c.randint(1, 8)
        m = np.array([[1 if rnd_c.random() < 0.45 else 0 for _ in range(W)]
                      for _ in range(H)], dtype=np.int64)
        l1, k1 = ccl_flood(m, nbrs)
        l2, k2 = ccl_two_pass(m, nbrs)
        assert k1 == k2, (name, m, k1, k2)
        assert np.array_equal(canon(l1), canon(l2)), (name, m)
    print('  ✅ %s：400 张随机 mask，泛洪法与两遍扫描法**逐像素标号一致**' % name)"""),

    code("""# ── 4 邻域 vs 8 邻域：最小反例，以及它在 TSR 里的后果 ──
diag = np.array([[1, 0],
                 [0, 1]], dtype=np.int64)
print('mask =\\n', diag)
print('4 邻域连通域个数 =', ccl_flood(diag, NBR4)[1], '（对角不相连）')
print('8 邻域连通域个数 =', ccl_flood(diag, NBR8)[1], '（对角相连）')
assert ccl_flood(diag, NBR4)[1] == 2 and ccl_flood(diag, NBR8)[1] == 1


def components_stats(lab, k):
    \"\"\"连通域 → 面积 + 外接框（mask → bbox，分割结果转检测框的标准后处理）。\"\"\"
    out = []
    for c in range(1, k + 1):
        ys, xs = np.nonzero(lab == c)
        out.append({'label': c, 'area': int(len(ys)),
                    'bbox': (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))})
    return out


# 合成一张 mask：两个方块 + 一条 1 像素宽的斜线（模拟标志牌上的斜向反光条）
m = np.zeros((12, 20), dtype=np.int64)
m[1:5, 1:5] = 1                       # 方块 A
m[1:5, 7:11] = 1                      # 方块 B（与 A 之间隔一列背景）
for t in range(6):
    m[6 + t, 12 + t] = 1              # 斜线：只在对角相邻
print('\\n合成 mask：')
print(m)
for nbrs, name in ((NBR4, '4 邻域'), (NBR8, '8 邻域')):
    lab, k = ccl_flood(m, nbrs)
    st = components_stats(lab, k)
    print('\\n%s → %d 个连通域' % (name, k))
    for d in st:
        print('   label %d  area %3d  bbox(y0,x0,y1,x1) = %s' % (d['label'], d['area'], d['bbox']))
    assert sum(d['area'] for d in st) == int(m.sum())      # 面积之和 == 前景像素数
lab4, k4 = ccl_flood(m, NBR4)
lab8, k8 = ccl_flood(m, NBR8)
assert (k4, k8) == (8, 3), (k4, k8)
print('\\n❗ 后果（真实会上线的 bug）：')
print('   · 4 邻域把那条斜向反光条切成 6 个 1 像素碎块 → 面积阈值一过滤就全丢了')
print('   · 8 邻域会把「仅在角上接触」的两个目标合成一个 → 输出一个巨大的错框')
print('   拓扑事实：前景用 8 邻域 ⇔ 背景必须用 4 邻域，否则前景连通与背景连通自相矛盾')
print('   （Rosenfeld 1970）。面试里说出这一条，比多做十道岛屿题有用。')"""),

    md("""## 6 · 并查集：优化的必要性、以及 bbox 聚类

两个优化解决**两个不同的问题**：
**按秩合并**防止树链化（把树高压到 $O(\\log n)$）；**路径压缩**把访问过的路径拍平（摊还近似常数）。
下面先把「不优化会怎样」跑成数字，再用它做 bbox 聚类。"""),

    code("""class DSU:
    \"\"\"路径压缩 + 按秩合并。steps 统计 find 的爬升步数，用来验证复杂度。\"\"\"
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.size = [1] * n
        self.count = n                     # 集合个数：每次成功 union 减 1
        self.steps = 0

    def find(self, x):
        root = x
        while self.parent[root] != root:   # 先找到根
            root = self.parent[root]; self.steps += 1
        while self.parent[x] != root:      # 路径压缩：整条链直接挂到 root
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False                   # 已同集合 —— 这个返回值可以直接用来检测环
        if self.rank[ra] < self.rank[rb]:   # 按秩合并：矮树挂到高树下，树高不增
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1             # 只有等高相并，树高才 +1
        self.count -= 1
        return True


class DSUNaive:
    \"\"\"❌ 无优化版：不压缩、不按秩。用来把「为什么需要优化」跑成数字。\"\"\"
    def __init__(self, n):
        self.parent = list(range(n)); self.steps = 0
    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]; self.steps += 1
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


n = 2000
naive, opt = DSUNaive(n), DSU(n)
for i in range(1, n):                      # 最坏输入：union(i, i-1) 让朴素版长成一条链
    naive.union(i, i - 1); opt.union(i, i - 1)
naive.steps = opt.steps = 0
for i in range(n):
    naive.find(i); opt.find(i)
print('n = %d，最坏 union 序列后做 n 次 find：' % n)
print('  无优化   总爬升 %9d 步  ≈ n^2/2 = %d' % (naive.steps, n * n // 2))
print('  优化后   总爬升 %9d 步' % opt.steps)
print('  差距 %.0f 倍' % (naive.steps / max(opt.steps, 1)))
assert naive.steps > 0.4 * n * n
assert opt.steps < 5 * n
assert naive.steps > 100 * max(opt.steps, 1)
assert opt.count == 1 and opt.size[opt.find(0)] == n
print('\\n✅ 两个优化一起用，摊还代价是 O(alpha(n))，alpha(n) <= 4 对一切实际的 n。')
print('   面试标准答法：「摊还近似常数，严格是 O(alpha(n))；这个界是 Tarjan 证明的，而且是紧的。」')

# 与暴力（BFS 求连通分量）对拍
def components_brute(n, edges):
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v); adj[v].append(u)
    lab, c = [-1] * n, 0
    for s in range(n):
        if lab[s] != -1:
            continue
        q = deque([s]); lab[s] = c
        while q:
            u = q.popleft()
            for v in adj[u]:
                if lab[v] == -1:
                    lab[v] = c; q.append(v)
        c += 1
    return c, lab

def canon_labels(lab):
    remap, nxt, out = {}, 0, []
    for v in lab:
        if v not in remap:
            remap[v] = nxt; nxt += 1
        out.append(remap[v])
    return out

rnd_u = random.Random(17)
for _ in range(1000):
    nn = rnd_u.randint(1, 12)
    edges = [(rnd_u.randrange(nn), rnd_u.randrange(nn)) for _ in range(rnd_u.randint(0, 15))]
    d = DSU(nn)
    for u, v in edges:
        d.union(u, v)
    cb, lb = components_brute(nn, edges)
    assert d.count == cb, (nn, edges)
    assert canon_labels([d.find(i) for i in range(nn)]) == canon_labels(lb)
print('✅ 1000 张随机图：并查集的连通分量个数与标号（规范化后）都与 BFS 暴力法一致。')"""),

    code("""# ══════════ 并查集的真实战场：bbox 聚类 ══════════
# 场景：切片推理（C57-04）后，同一个标志牌被多个切片各检出一次，需要**合并碎片**；
#       或多相机结果融合。注意这是「合并」而不是「筛选」——所以用并查集，不是 NMS。

def iou_matrix(boxes):
    \"\"\"N x N 的 IoU 矩阵（向量化）。boxes = [[x1,y1,x2,y2], ...]\"\"\"
    b = np.asarray(boxes, dtype=np.float64)
    ix1 = np.maximum(b[:, None, 0], b[None, :, 0]); iy1 = np.maximum(b[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(b[:, None, 2], b[None, :, 2]); iy2 = np.minimum(b[:, None, 3], b[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area[:, None] + area[None, :] - inter, 1e-9)


def cluster_dsu(boxes, thr):
    \"\"\"IoU > thr 就 union ⇒ 连通分量即簇。返回规范化标号。\"\"\"
    n = len(boxes)
    if n == 0:
        return []
    M = iou_matrix(boxes)
    d = DSU(n)
    for i in range(n):
        for j in range(i + 1, n):
            if M[i, j] > thr:
                d.union(i, j)
    return canon_labels([d.find(i) for i in range(n)])


def cluster_pairwise_brute(boxes, thr):
    \"\"\"暴力对照：逐对比较建邻接表 + BFS 求连通分量（完全不用并查集）。\"\"\"
    n = len(boxes)
    if n == 0:
        return []
    M = iou_matrix(boxes)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if M[i, j] > thr]
    _, lab = components_brute(n, edges)
    return canon_labels(lab)


def merge_cluster_boxes(boxes, labels):
    \"\"\"每个簇取外接框（跨片合并的标准做法之一；也可以按分数加权平均）。\"\"\"
    b = np.asarray(boxes, dtype=np.float64)
    out = []
    for c in range(max(labels) + 1 if labels else 0):
        sel = b[[i for i, l in enumerate(labels) if l == c]]
        out.append([sel[:, 0].min(), sel[:, 1].min(), sel[:, 2].max(), sel[:, 3].max()])
    return out


rnd_bb = random.Random(19)
for _ in range(500):
    n = rnd_bb.randint(0, 10)
    bs = []
    for _ in range(n):
        x, y = rnd_bb.randint(0, 40), rnd_bb.randint(0, 40)
        w, h = rnd_bb.randint(5, 25), rnd_bb.randint(5, 25)
        bs.append([x, y, x + w, y + h])
    for thr in (0.1, 0.3, 0.5, 0.7):
        assert cluster_dsu(bs, thr) == cluster_pairwise_brute(bs, thr), (bs, thr)
print('✅ 500 组随机框 x 4 个阈值：并查集聚类与逐对比较 + BFS 暴力法结果完全一致。')

# 计时：建边是 O(N^2)，这是聚类法的真实瓶颈（不是并查集）
for N in (200, 400, 800):
    bs = [[i % 50 * 7, i // 50 * 7, i % 50 * 7 + 30, i // 50 * 7 + 30] for i in range(N)]
    t0 = time.perf_counter(); cluster_dsu(bs, 0.5); dt = time.perf_counter() - t0
    print('  N=%4d  聚类耗时 %6.1f ms  （O(N^2) 建边主导，并查集部分近似 O(N)）' % (N, dt * 1000))"""),

    code("""# ══════════ chaining：聚类法的失效模式（必须知道的那个坑）══════════
# 构造一排等间距的框：相邻 IoU = 0.6，隔一个 IoU = 0.333，隔三个 IoU = 0。
BOXES = np.array([[25.0 * i, 0.0, 25.0 * i + 100.0, 100.0] for i in range(6)])
SCORES = np.array([0.95, 0.94, 0.93, 0.92, 0.91, 0.90])
M = iou_matrix(BOXES)
print('IoU 矩阵（保留两位）:')
print(np.round(M, 3))
assert abs(M[0, 1] - 0.6) < 1e-9 and abs(M[0, 2] - 1 / 3) < 1e-9 and M[0, 4] == 0.0

thr = 0.5
labels = cluster_dsu(BOXES, thr)
merged = merge_cluster_boxes(BOXES, labels)
print('\\n【并查集聚类，thr=%.1f】簇标号 = %s  → %d 个簇' % (thr, labels, max(labels) + 1))
print('   合并后的框 =', [[round(v, 1) for v in bb] for bb in merged])
assert labels == [0] * 6, '6 个框被链式并成了一个簇'
assert merged[0] == [0.0, 0.0, 225.0, 100.0]
print('   ❗ 单框宽 100，合并后宽 225 —— 一个横跨整排的巨大错框。')
print('   根因：IoU(A,B)=0.6、IoU(B,C)=0.6，但 IoU(A,C)=0.333；')
print('        **IoU 关系不传递，而连通分量求的是传递闭包。**')


def greedy_nms(scores, M, thr):
    \"\"\"贪心 NMS：按分数降序（用 (-score, idx) 做全序 tie-break，见模块 02）扫描，能留就留。\"\"\"
    order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))
    keep = []
    for i in order:
        if all(M[i, j] <= thr for j in keep):
            keep.append(i)
    return sorted(keep)


keep = greedy_nms(SCORES, M, thr)
print('\\n【贪心 NMS，thr=%.1f】保留下标 = %s → %d 个框' % (thr, keep, len(keep)))
assert keep == [0, 2, 4]
print('   NMS 是「挑代表并抑制邻居」（不传递），聚类是「求连通分量」（传递）。')
print('   稀疏场景两者几乎一样，密集场景差别巨大 —— 这就是选错的代价。')
print('\\n缓解 chaining 的三条工程手段：')
print('   ① 提高连边阈值，并额外要求类别一致')
print('   ② 更严格的连边条件（IoU 且 中心距 < d 且 尺度比 in [0.7, 1.4]）')
print('   ③ **只在切片边界带内允许合并** —— 把传递性限制在物理上确实可能是同一目标的区域内')
print('      （这是 SAHI 式跨片合并的标准做法，见 C57-04）')"""),

    md("""## 7 · 拓扑排序：Kahn 分层、三色环检测、DAG 关键路径

Kahn 的**分层副产物**在工程上比拓扑序本身更有用：
同层任务无依赖 ⇒ **可并行**；层数 - 1 = **关键路径长度** = 无限并行度下的最短完成时间
（这正是 C63-04 的延迟预算分解在做的事）。"""),

    code("""def kahn_layers(n, edges):
    \"\"\"返回分层列表（每层升序）；**有环返回 None**。
       结点 v 所在层号 = 从任一源点到 v 的最长路径长度。\"\"\"
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v in edges:
        adj[u].append(v); indeg[v] += 1
    cur = sorted(i for i in range(n) if indeg[i] == 0)
    layers, seen = [], 0
    while cur:
        layers.append(cur); seen += len(cur)
        nxt = []
        for u in cur:
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    nxt.append(v)
        cur = sorted(nxt)
    return None if seen != n else layers      # 没输出完 ⇒ 剩下的结点在环里


def find_cycle_edge(n, edges):
    \"\"\"三色标记：返回环上的一条边 (u, v)，无环返回 None。
       只有「指向灰色结点」才是环；指向黑色只是 DAG 里的重复汇聚。\"\"\"
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    color = [0] * n                            # 0 白（未访问）1 灰（在递归栈上）2 黑（已完成）
    box = []

    def dfs(u):
        color[u] = 1
        for v in adj[u]:
            if color[v] == 1:
                box.append((u, v)); return True    # ★ back edge
            if color[v] == 0 and dfs(v):
                return True
        color[u] = 2
        return False

    for s in range(n):
        if color[s] == 0 and dfs(s):
            return box[0]
    return None


def has_cycle_wrong(n, edges):
    \"\"\"❌ 只用一个 visited 集合 —— 把「重复汇聚」误判成环。\"\"\"
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    vis = set()
    def dfs(u):
        vis.add(u)
        for v in adj[u]:
            if v in vis or dfs(v):
                return True
        return False
    return any(dfs(s) for s in range(n) if s not in vis)


def longest_path_edges(n, edges):
    \"\"\"DAG 上按拓扑序做一遍 DP，求最长路（边数）= 关键路径长度。\"\"\"
    layers = kahn_layers(n, edges)
    if layers is None:
        return None
    order = [u for lv in layers for u in lv]
    pre = defaultdict(list)
    for u, v in edges:
        pre[v].append(u)
    dp = {}
    for u in order:                            # 拓扑序保证前驱都算完了
        dp[u] = max([dp[p] + 1 for p in pre[u]], default=0)
    return max(dp.values(), default=0)


# 菱形图：0→1, 0→2, 1→3, 2→3 —— 无环，但错版会说有环
DIAMOND = [(0, 1), (0, 2), (1, 3), (2, 3)]
print('菱形图 0→1, 0→2, 1→3, 2→3')
print('  Kahn 分层        =', kahn_layers(4, DIAMOND))
print('  三色找环         =', find_cycle_edge(4, DIAMOND))
print('  只用 visited 的错版说有环？', has_cycle_wrong(4, DIAMOND), '  ← 错')
assert kahn_layers(4, DIAMOND) == [[0], [1, 2], [3]]
assert find_cycle_edge(4, DIAMOND) is None
assert has_cycle_wrong(4, DIAMOND) is True

CYC = [(0, 1), (1, 2), (2, 0)]
print('\\n三元环 0→1→2→0：Kahn =', kahn_layers(3, CYC), ' 环上的边 =', find_cycle_edge(3, CYC))
assert kahn_layers(3, CYC) is None and find_cycle_edge(3, CYC) is not None

# 与全排列暴力对拍：有拓扑序 ⟺ 无环
rnd_p = random.Random(23)
for _ in range(600):
    nn = rnd_p.randint(1, 6)
    edges = list({(rnd_p.randrange(nn), rnd_p.randrange(nn)) for _ in range(rnd_p.randint(0, 10))})
    edges = [(u, v) for u, v in edges if u != v]
    layers = kahn_layers(nn, edges)
    ok_brute = any(all(perm.index(u) < perm.index(v) for u, v in edges)
                   for perm in itertools.permutations(range(nn)))
    assert (layers is not None) == ok_brute, (nn, edges)
    assert (find_cycle_edge(nn, edges) is None) == ok_brute
    if layers is not None:
        flat = [u for lv in layers for u in lv]
        assert sorted(flat) == list(range(nn))
        pos = {u: i for i, u in enumerate(flat)}
        assert all(pos[u] < pos[v] for u, v in edges), '展平后必须是合法拓扑序'
        li = {u: i for i, lv in enumerate(layers) for u in lv}
        assert all(li[u] < li[v] for u, v in edges), '层号必须严格递增'
        assert longest_path_edges(nn, edges) == len(layers) - 1, '关键路径 = 层数 - 1'
print('\\n✅ 600 张随机图：Kahn / 三色标记 / 全排列暴力三者对「是否有环」完全一致；')
print('   分层是合法拓扑序，且「关键路径边数 == 层数 - 1」处处成立。')"""),

    md("""## 8 · 把 NMS 表述成图上的极大独立集

建模：顶点 = 候选框，$\\mathrm{IoU}>\\tau$ 连边 ⇒ **冲突图** $G$。于是

- 贪心 NMS 的输出是 $G$ 的一个**极大独立集**（maximal independent set）
- 我们真正想要的是**最大权独立集** MWIS（$\\max\\sum_{i\\in S}s_i$，两两无边）—— 一般图上 **NP-hard**
- 按权降序的贪心是 MWIS 的标准近似，且有保证：$w(\\text{greedy}) \\ge \\mathrm{OPT}/(\\Delta+1)$，
  $\\Delta$ = 冲突图最大度

下面把这四条**全部跑成断言**：验证独立性、验证极大性、暴力枚举求 OPT、量化次优、验证近似比。"""),

    code("""def is_independent(keep, M, thr):
    return all(M[i, j] <= thr for a, i in enumerate(keep) for j in keep[a + 1:])

def is_maximal(keep, M, thr, n):
    \"\"\"极大：任何未被保留的框，加进来都会破坏独立性。\"\"\"
    return all(any(M[i, j] > thr for j in keep) for i in range(n) if i not in keep)

def mwis_brute(scores, M, thr):
    \"\"\"暴力枚举所有子集求最大权独立集（n <= 16）。返回 (最优权重, 最优集合)。\"\"\"
    n = len(scores)
    best, arg = -1.0, None
    for mask in range(1 << n):
        idx = [i for i in range(n) if mask >> i & 1]
        if is_independent(idx, M, thr):
            w = float(sum(scores[i] for i in idx))
            if w > best:
                best, arg = w, idx
    return best, arg

def max_degree(M, thr, n):
    return max([sum(1 for j in range(n) if j != i and M[i, j] > thr) for i in range(n)], default=0)


# 先在上一节那排框上验证
keep = greedy_nms(SCORES, M, thr)
opt_w, opt_set = mwis_brute(SCORES, M, thr)
g_w = float(SCORES[keep].sum())
delta = max_degree(M, thr, len(SCORES))
print('那一排 6 个框（thr=0.5）：')
print('  贪心 NMS 保留 %s  权重 %.2f' % (keep, g_w))
print('  暴力 MWIS  保留 %s  权重 %.2f  最大度 Delta = %d' % (opt_set, opt_w, delta))
assert is_independent(keep, M, thr), '贪心输出必须是独立集'
assert is_maximal(keep, M, thr, len(SCORES)), '贪心输出必须是极大的'
assert g_w <= opt_w + 1e-12
assert g_w >= opt_w / (delta + 1) - 1e-12
print('  ✅ 独立性、极大性、g <= OPT、g >= OPT/(Delta+1) 全部成立')

# 随机搜索：贪心什么时候严格次优？
rnd_m = random.Random(29)
n_sub, worst, worst_case = 0, 1.0, None
for _ in range(3000):
    n = rnd_m.randint(2, 9)
    bs, sc = [], []
    for _ in range(n):
        x, y = rnd_m.randint(0, 30), rnd_m.randint(0, 30)
        w, h = rnd_m.randint(8, 24), rnd_m.randint(8, 24)
        bs.append([x, y, x + w, y + h]); sc.append(round(rnd_m.uniform(0.5, 1.0), 3))
    sc = np.array(sc); Mi = iou_matrix(bs); th = 0.4
    kp = greedy_nms(sc, Mi, th)
    ow, _ = mwis_brute(sc, Mi, th)
    gw = float(sc[kp].sum())
    d = max_degree(Mi, th, n)
    assert is_independent(kp, Mi, th) and is_maximal(kp, Mi, th, n)
    assert gw <= ow + 1e-9, '贪心不可能超过最优'
    assert gw >= ow / (d + 1) - 1e-9, '(Delta+1)-近似界必须成立'
    if gw < ow - 1e-9:
        n_sub += 1
        if gw / ow < worst:
            worst, worst_case = gw / ow, (bs, sc.tolist(), th, kp, ow, gw, d)
print('\\n3000 组随机场景（thr=0.4）：')
print('  贪心严格次优的比例 = %d/3000 = %.1f%%' % (n_sub, 100 * n_sub / 3000))
print('  最差比值 greedy/OPT = %.4f' % worst)
assert n_sub > 0, '必须能找到贪心次优的例子'
assert worst < 1.0
bs_w, sc_w, th_w, kp_w, ow_w, gw_w, d_w = worst_case
print('  最差例子：%d 个框，最大度 Delta=%d，贪心 %.3f vs 最优 %.3f' % (len(bs_w), d_w, gw_w, ow_w))
print('\\n📌 60 秒答法（背下来）：')
print('   「把每个框当顶点、IoU 超阈值连边，NMS 的输出就是这张冲突图上的一个极大独立集；')
print('    我们想要的是最大权独立集，但一般图上这是 NP-hard 的，所以贪心 NMS 是它的近似算法，')
print('    近似比与冲突图的最大度有关 —— 这解释了为什么密集场景下 NMS 更容易出问题。')
print('    如果冲突只来自一维区间重叠，图是区间图，可以用 DP 精确解，那就是加权区间调度。」')
print('   （一维精确解在模块 04；NMS 的手撕实现在 C61-05。）')"""),

    md("""## ✏️ 练习 1：用并查集做 bbox 聚类

实现 `cluster_boxes(boxes, iou_thr)`：

- 输入 `boxes = [[x1, y1, x2, y2], ...]`（可能为空），`iou_thr` 是连边阈值
- **IoU > iou_thr 就把两个框并进同一簇**（严格大于，与本节的实现口径一致）
- 返回长度为 `N` 的标号列表，标号**按第一次出现的顺序规范化**为 `0, 1, 2, ...`
  （这样结果唯一确定，可以直接对拍）
- 必须用并查集；建边可以用 `iou_matrix(boxes)`

**先在心里回答**：这道题为什么不能用 NMS？（提示：合并 vs 筛选，以及 chaining）"""),

    code("""def cluster_boxes(boxes, iou_thr):
    # TODO:
    #   n = len(boxes); if n == 0: return []
    #   M = iou_matrix(boxes)
    #   d = DSU(n)
    #   对所有 i < j：M[i, j] > iou_thr 就 d.union(i, j)
    #   return canon_labels([d.find(i) for i in range(n)])
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert cluster_boxes([], 0.5) == []
assert cluster_boxes([[0, 0, 10, 10]], 0.5) == [0]
assert cluster_boxes([[0, 0, 10, 10], [100, 100, 110, 110]], 0.5) == [0, 1]

# 那一排链式相连的框：必须全部并成一簇（这是 chaining，也是这道题的重点）
assert cluster_boxes(BOXES.tolist(), 0.5) == [0] * 6
# 阈值提高到 0.65 之后，相邻 IoU=0.6 不再连边 ⇒ 六个独立簇
assert cluster_boxes(BOXES.tolist(), 0.65) == [0, 1, 2, 3, 4, 5]

_r1 = random.Random(101)
for _ in range(500):
    n = _r1.randint(0, 10)
    bs = []
    for _ in range(n):
        x, y = _r1.randint(0, 40), _r1.randint(0, 40)
        w, h = _r1.randint(5, 25), _r1.randint(5, 25)
        bs.append([x, y, x + w, y + h])
    for thr in (0.1, 0.3, 0.5, 0.7):
        lab = cluster_boxes(bs, thr)
        assert lab == cluster_pairwise_brute(bs, thr), (bs, thr)
        # 结构自检：同簇 ⟺ 在「IoU>thr」图上连通
        if n:
            Mi = iou_matrix(bs)
            for i in range(n):
                for j in range(n):
                    if Mi[i, j] > thr:
                        assert lab[i] == lab[j], '直接相连的框必须同簇'

_t0 = time.perf_counter()
_big = [[i % 60 * 6, i // 60 * 6, i % 60 * 6 + 28, i // 60 * 6 + 28] for i in range(300)]
_lab = cluster_boxes(_big, 0.5)
_dt = time.perf_counter() - _t0
assert _dt < 5.0, 'N=300 还要 5 秒以上 ⇒ 很可能对每对都跑了一次 BFS'
print('✅ 练习 1 通过：500 组随机框 x 4 个阈值与暴力法一致 + chaining 用例 + N=300 用时 %.0f ms'
      % (_dt * 1000))
print('   面试话术：「跨片合并要的是把碎片**合并**，所以用并查集求连通分量；')
print('   但 IoU 不传递，密集场景会 chaining —— 我会加中心距和尺度比约束，或只在边界带内合并。」')"""),

    md("""## ✏️ 练习 2：迭代版网格连通域计数

实现 `count_components_iter(mask, conn=4)`：返回 `mask` 中值为 1 的连通域个数。

- `conn` 取 `4` 或 `8`，分别对应 4 邻域与 8 邻域
- **必须是迭代实现（显式栈或队列），不许递归** ——
  自测会在一张 $300\\times300$ 的全 1 网格上跑，递归版必然 `RecursionError`
- 不要修改输入 `mask`（自测会检查）
- 空网格（0 行或 0 列）返回 0"""),

    code("""def count_components_iter(mask, conn=4):
    # TODO:
    #   nbrs = NBR4 if conn == 4 else NBR8
    #   H, W = mask.shape；seen = np.zeros_like(mask, dtype=bool)
    #   行优先扫描，遇到未访问的前景像素：计数 +1，然后用 **显式栈/队列** 泛洪
    #   泛洪时：入栈前判越界 + 判前景 + 判未访问，并**入栈时就置 seen=True**
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
assert count_components_iter(np.zeros((0, 0), dtype=np.int64)) == 0
assert count_components_iter(np.zeros((4, 4), dtype=np.int64)) == 0
assert count_components_iter(np.ones((4, 4), dtype=np.int64)) == 1
_diag = np.array([[1, 0], [0, 1]], dtype=np.int64)
assert count_components_iter(_diag, 4) == 2 and count_components_iter(_diag, 8) == 1

_r2 = random.Random(103)
for _ in range(400):
    H, W = _r2.randint(1, 8), _r2.randint(1, 8)
    m2 = np.array([[1 if _r2.random() < 0.45 else 0 for _ in range(W)]
                   for _ in range(H)], dtype=np.int64)
    before = m2.copy()
    for conn, nbrs in ((4, NBR4), (8, NBR8)):
        assert count_components_iter(m2, conn) == ccl_flood(m2, nbrs)[1], (m2, conn)
    assert np.array_equal(m2, before), '不许修改输入 mask'

# 大网格：单个连通域含 90000 个像素 ⇒ 递归版会 RecursionError（当前上限 %d）
_t0 = time.perf_counter()
_huge = np.ones((300, 300), dtype=np.int64)
assert count_components_iter(_huge, 4) == 1
_dt = time.perf_counter() - _t0
print('✅ 练习 2 通过：400 张随机 mask x 两种邻域与参考实现一致；')
print('   300x300 全 1 网格（90000 像素、递归深度会到 9e4）用时 %.0f ms 且未爆栈。' % (_dt * 1000))
print('   这就是「递归深度不可控时必须写迭代版」的验收标准。')"""),

    md("""## ✏️ 练习 3：迭代求树的直径（stage 状态机）

实现 `tree_diameter_iter(root)`：返回树的直径（**两结点间最长路径的边数**），
**必须用显式栈迭代实现**，不许递归。

这是第 2 节 `subtree_sums_iter` 的直接变形：

- 栈里存 `(结点, stage)`，`stage ∈ {0, 1, 2}`
- 在 `stage == 2`（两个孩子都回来了）时：
  - `depth[node] = 1 + max(depth[left], depth[right])`（空孩子的深度算 0）
  - `best = max(best, depth[left] + depth[right])`（经过 node 的最长路径）
- 空树返回 0

自测会在一条深度约 2000 的链上跑 —— 递归版在那里必然爆栈。"""),

    code("""def tree_diameter_iter(root):
    # TODO：
    #   if root is None: return 0
    #   depth = {}; best = 0; st = [(root, 0)]
    #   while st:
    #       n, stage = st.pop()
    #       stage 0 -> 压回 (n,1)，再压左孩子 (left,0)
    #       stage 1 -> 压回 (n,2)，再压右孩子 (right,0)
    #       stage 2 -> dl = depth.get(id(n.left), 0); dr = depth.get(id(n.right), 0)
    #                  best = max(best, dl + dr); depth[id(n)] = 1 + max(dl, dr)
    #   return best
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert tree_diameter_iter(None) == 0
assert tree_diameter_iter(build([1])) == 0
assert tree_diameter_iter(build([1, 2, 3])) == 2
assert tree_diameter_iter(T) == diameter(T)

_r3 = random.Random(107)
for _ in range(1500):
    t3 = rand_tree(_r3, _r3.randint(0, 16))
    assert tree_diameter_iter(t3) == diameter(t3) == diameter_brute(t3), '与递归版和 BFS 暴力真值都要一致'

# 深链：递归版必爆栈，迭代版必须给出 N-1
_N = 2 * sys.getrecursionlimit()
_chain = None
for _v in range(_N):
    _chain = Node(_v, left=_chain)
_rec_ok = True
try:
    diameter(_chain)
except RecursionError:
    _rec_ok = False
_d = tree_diameter_iter(_chain)
unlink_chain(_chain); _chain = None
assert _rec_ok is False, '深度 %d 的链上递归版应当爆栈' % _N
assert _d == _N - 1, ('链的直径 = 结点数 - 1', _d, _N - 1)
print('✅ 练习 3 通过：1500 棵随机树与递归版/暴力真值三方一致；')
print('   深度 %d 的链上递归版爆栈，迭代版给出直径 %d。' % (_N, _d))
print('   记住这个骨架：它能把**任何**后序型递归（树形 DP、记忆化搜索）改成迭代。')"""),

    md("""## ✏️ 练习 4：把 NMS 写成贪心极大独立集

实现 `greedy_mis(weights, edges)`：

- `weights[i]` 是顶点 `i` 的权重，`edges` 是**无向冲突边**列表 `[(u, v), ...]`
  （可能含重复边与自环，自环请忽略）
- 按**权重降序**扫描（权重并列时按**下标升序**，保证结果确定），
  与已选集合无冲突就选入
- 返回**升序**的下标列表

这就是 NMS 换一个接口写出来的样子：`weights` = 分数，`edges` = IoU 超阈值的框对。
自测会验证四条性质：**独立性、极大性、$w\\le\\mathrm{OPT}$、$w\\ge\\mathrm{OPT}/(\\Delta+1)$**。"""),

    code("""def greedy_mis(weights, edges):
    # TODO:
    #   conflict = defaultdict(set)；把 edges 里 u != v 的双向加入
    #   order = sorted(range(len(weights)), key=lambda i: (-weights[i], i))
    #   keep = []；逐个考察 i：若 conflict[i] 与 keep 无交集则 keep.append(i)
    #   return sorted(keep)
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
def _mwis_edges_brute(weights, edges):
    \"\"\"暴力枚举全部子集求最大权独立集（n <= 14）。\"\"\"
    n = len(weights)
    E = {(min(u, v), max(u, v)) for u, v in edges if u != v}
    best, arg = -1.0, None
    for mask in range(1 << n):
        idx = [i for i in range(n) if mask >> i & 1]
        if all((min(i, j), max(i, j)) not in E
               for a, i in enumerate(idx) for j in idx[a + 1:]):
            w = float(sum(weights[i] for i in idx))
            if w > best:
                best, arg = w, idx
    return best, arg

def _deg(n, edges):
    d = defaultdict(set)
    for u, v in edges:
        if u != v:
            d[u].add(v); d[v].add(u)
    return d, max([len(d[i]) for i in range(n)], default=0)

assert greedy_mis([], []) == []
assert greedy_mis([1.0, 2.0, 3.0], []) == [0, 1, 2], '无边 ⇒ 全选'
assert greedy_mis([1.0], [(0, 0)]) == [0], '自环必须被忽略'
# 星形反例：贪心先拿中心（3），把三个叶子（各 2）全挡掉 ⇒ 3 < 6
_star_w, _star_e = [3.0, 2.0, 2.0, 2.0], [(0, 1), (0, 2), (0, 3)]
assert greedy_mis(_star_w, _star_e) == [0]
assert _mwis_edges_brute(_star_w, _star_e)[0] == 6.0
print('星形反例：贪心权重 3.0，最优 6.0 —— 贪心可以差到 2 倍。')

_r4 = random.Random(109)
_sub = 0
for _ in range(2000):
    n = _r4.randint(1, 10)
    w = [round(_r4.uniform(0.5, 1.0), 3) for _ in range(n)]
    es = [(_r4.randrange(n), _r4.randrange(n)) for _ in range(_r4.randint(0, 14))]
    keep4 = greedy_mis(w, es)
    d, delta = _deg(n, es)
    assert keep4 == sorted(set(keep4)), '返回值必须是升序且不重复'
    assert all(v not in d[u] for a, u in enumerate(keep4) for v in keep4[a + 1:]), '① 必须是独立集'
    assert all(any(j in d[i] for j in keep4) for i in range(n) if i not in keep4), '② 必须是极大的'
    ow, _ = _mwis_edges_brute(w, es)
    gw = sum(w[i] for i in keep4)
    assert gw <= ow + 1e-9, '③ 贪心不可能超过最优'
    assert gw >= ow / (delta + 1) - 1e-9, '④ (Delta+1)-近似界'
    if gw < ow - 1e-9:
        _sub += 1
print('✅ 练习 4 通过：2000 组随机冲突图，四条性质全部成立；')
print('   其中 %d 组（%.1f%%）贪心严格次优 —— 这就是「NMS 是 NP-hard 问题的贪心近似」的实证。'
      % (_sub, 100 * _sub / 2000))
assert _sub > 0"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def cluster_boxes(boxes, iou_thr):
    n = len(boxes)
    if n == 0:
        return []
    M = iou_matrix(boxes)              # O(N^2) 建边 —— 这才是真正的瓶颈
    d = DSU(n)
    for i in range(n):
        for j in range(i + 1, n):
            if M[i, j] > iou_thr:
                d.union(i, j)          # 并查集部分近似 O(N alpha(N))
    return canon_labels([d.find(i) for i in range(n)])
# 为什么不能用 NMS：NMS 是「挑代表并抑制邻居」（筛选），聚类是「求连通分量」（合并）。
# 代价：IoU 不传递 ⇒ 密集场景会 chaining，要靠中心距/尺度比/边界带来约束传递性。"""),

    code("""# 练习 2 参考答案
def count_components_iter(mask, conn=4):
    nbrs = NBR4 if conn == 4 else NBR8
    if mask.size == 0:
        return 0
    H, W = mask.shape
    seen = np.zeros((H, W), dtype=bool)
    cnt = 0
    for i in range(H):
        for j in range(W):
            if not mask[i, j] or seen[i, j]:
                continue
            cnt += 1
            seen[i, j] = True
            st = [(i, j)]              # 显式栈：深度多大都不会爆
            while st:
                y, x = st.pop()
                for dy, dx in nbrs:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True    # ★ 入栈时就标记，避免重复入栈
                        st.append((ny, nx))
    return cnt"""),

    code("""# 练习 3 参考答案
def tree_diameter_iter(root):
    if root is None:
        return 0
    depth = {}                         # id(结点) -> 向下最大深度（空 = 0）
    best = 0
    st = [(root, 0)]
    while st:
        n, stage = st.pop()
        if stage == 0:
            st.append((n, 1))
            if n.left:  st.append((n.left, 0))
        elif stage == 1:
            st.append((n, 2))
            if n.right: st.append((n.right, 0))
        else:                          # 两个孩子都回来了 —— 这就是"后序时刻"
            dl = depth.get(id(n.left), 0)
            dr = depth.get(id(n.right), 0)
            best = max(best, dl + dr)  # 答案：经过 n 的最长路径（边数）
            depth[id(n)] = 1 + max(dl, dr)   # 返回值：深度。两者不是一回事
    return best"""),

    code("""# 练习 4 参考答案
def greedy_mis(weights, edges):
    conflict = defaultdict(set)
    for u, v in edges:
        if u != v:                     # 自环忽略：一个框和自己不冲突
            conflict[u].add(v); conflict[v].add(u)
    # 全序键 (-权重, 下标)：并列时也有确定顺序（见模块 02 的确定性讨论）
    order = sorted(range(len(weights)), key=lambda i: (-weights[i], i))
    keep = []
    for i in order:
        if not conflict[i].intersection(keep):   # 与已选集合无冲突 ⇒ 选入
            keep.append(i)
    return sorted(keep)
# 性质：① 独立（构造保证）② 极大（被跳过的一定与某个已选冲突）
#      ③ w <= OPT ④ w >= OPT/(Delta+1)：每个被选中的点最多挡掉 Delta 个权重不超过它的点"""),

    md("""---
## 🧪 真实工程胶囊：树 / 图 / 搜索速查卡"""),

    code("""RECIPE = r'''
# ======================================================================
# 面试与生产两用速查卡 · 递归转迭代 / 并查集 / 网格搜索 / NMS 图视角   （C62 模块 03）
# ======================================================================

# ---------- 1. 递归三要素（写代码前口述一遍） ----------
#   终止：最小子问题是什么、答案是什么           -> 漏了就 RecursionError
#   拆解：怎么变成"严格更小"的同类问题            -> 图上必须有 visited，否则没有递减度量
#   合并：子答案怎么拼成当前答案                  -> 先写一行契约注释：输入/返回/副作用
#   陷阱：**返回值 != 答案**（直径题返回深度，答案挂在外部变量上）
#   陷阱：每层重算高度 = 重复计算，最坏 O(n^2)；正解是后序一趟把高度带上来

# ---------- 2. 递归转迭代：万能配方 ----------
#   栈元素 = (状态, 阶段)；阶段 k = "第 k 个递归调用点的返回位置"
#   stage 0 -> 压回 (n,1) 再压第一个子问题；stage 1 -> 压回 (n,2) 再压第二个；stage 2 -> 合并
#   子结果放在以"结点身份"为键的表里（树用 id(node)，图用结点编号）
def postorder_iter(root):
    out, st = [], ([(root, 0)] if root else [])
    while st:
        n, stage = st.pop()
        if   stage == 0: st.append((n, 1));  st.append((n.left, 0))  if n.left  else None
        elif stage == 1: st.append((n, 2));  st.append((n.right, 0)) if n.right else None
        else:            out.append(n.val)
    return out
# 什么时候**必须**转：① 深度可能到 1e4+  ② 需要可中断（帧预算耗尽就存栈下帧继续）
#                    ③ 需要可序列化/可限长内存
# 反面教材：sys.setrecursionlimit(10**6) —— 爆的是 C 栈，段错误、无异常、无日志

# ---------- 3. BFS / Dijkstra / 0-1 BFS ----------
# BFS：dist 字典兼作 visited；**入队时标记**（出队才标记会让队列从 O(V) 涨到 O(E)）
# 多源 BFS：所有源点一次性入队 = 距离变换（CV 里的 distance transform）
# Dijkstra：堆 + 惰性删除（不 decrease-key；出堆时 `if d > dist[u]: continue`）；边权须非负
# 0-1 BFS：deque，权 0 走 appendleft、权 1 走 append -> O(V+E)
# 选择信号：最短步数->BFS；所有路径/回溯->DFS；有代价->Dijkstra；有负权->Bellman-Ford

# ---------- 4. 并查集（默写级） ----------
class DSU:
    def __init__(self, n):
        self.p = list(range(n)); self.r = [0]*n; self.sz = [1]*n; self.count = n
    def find(self, x):
        root = x
        while self.p[root] != root: root = self.p[root]
        while self.p[x] != root: self.p[x], x = root, self.p[x]   # 路径压缩
        return root
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return False                                  # 返回值可直接用来检测环
        if self.r[ra] < self.r[rb]: ra, rb = rb, ra                # 按秩合并
        self.p[rb] = ra; self.sz[ra] += self.sz[rb]
        if self.r[ra] == self.r[rb]: self.r[ra] += 1
        self.count -= 1; return True
# 复杂度 O(m alpha(n))，alpha <= 4；两个优化各管一件事：按秩防链化、压缩降摊还
# 做不到：删边、分裂、查距离 -> 删边问题用**离线倒序处理**变成加边

# ---------- 5. 网格搜索 = 连通域标记（CCL） ----------
# 路线① BFS/DFS 泛洪：短、常数小；递归版在 1e6 像素的域上必爆栈
# 路线② 两遍扫描 + 并查集：顺序访存、可分块并行、内存有上界 -> 工业界与 GPU 主流
# 4 vs 8 邻域是**语义选择**：8 邻域会把角接触的两个目标并成一个巨框；
#                          4 邻域会把 1 像素宽的斜向结构切成碎块
# 拓扑事实：前景 8 邻域 <=> 背景必须 4 邻域（Rosenfeld 1970）
# 产物：面积（过滤噪点）、外接框（mask -> bbox）、距离场（多源 BFS）

# ---------- 6. 框聚类 vs NMS：合并还是筛选 ----------
# 并查集聚类 = 连通分量 = **传递闭包**  -> 用于跨片合并、多相机融合（要"拼碎片"）
# 贪心 NMS   = 极大独立集             -> 用于去重（要"挑代表"）
# chaining 失效：IoU(A,B)=.6, IoU(B,C)=.6, IoU(A,C)=0 却被并成一簇 -> 一排限速牌变一个巨框
# 三条缓解：提高阈值+同类别 / 加中心距与尺度比约束 / **只在切片边界带内允许合并**

# ---------- 7. NMS 的图论表述（60 秒讲稿） ----------
# 顶点=框，IoU>tau 连边 -> 冲突图 G
#   贪心 NMS 的输出 = G 的一个**极大独立集**
#   想要的是**最大权独立集 MWIS** -> 一般图 NP-hard -> 所以 NMS 是贪心近似
#   保证：w(greedy) >= OPT/(Delta+1)，Delta = 最大度
#         => Delta 小(稀疏)时几乎最优；Delta 大(密集)时才明显次优 —— 解释了密集场景为何变差
#   一维特例：冲突来自区间重叠 -> 区间图 -> DP 可**精确**解（加权区间调度，见模块 04）
#   绕开路线：一对一匹配的无 NMS 检测器（DETR / YOLOv10）—— 把"推理期去重"变成"训练期不产生重复"

# ---------- 8. 交卷前 30 秒自检 ----------
#   [ ] 递归：说清返回值语义；估一下最坏深度；深度不可控就改迭代
#   [ ] BFS：入队时标记；层数用 len(queue) 切层
#   [ ] 网格：越界判断写在入队前；4/8 邻域先问；是否允许改输入先问
#   [ ] 并查集：find 写迭代版；说出"摊还 O(alpha(n))"而不是"O(1)"
#   [ ] 环检测：三色标记，只有指向**灰色**才是环（单 visited 集合判不出来）
#   [ ] 边界：空树/空图/单结点/自环/重边/非连通图
'''
print(RECIPE)
for _tok in ['postorder_iter', 'class DSU', '入队时标记', 'Rosenfeld 1970',
             '极大独立集', 'OPT/(Delta+1)', '交卷前 30 秒自检']:
    assert _tok in RECIPE, _tok
print('\\n（第 2、4 节可直接复制进项目；第 7 节建议在面试前一天读出声一遍。）')"""),

    md("""### 小结

1. **递归 = 隐式栈；把栈显式化，控制流就变成了数据。**
   转换配方只有一条：栈里存 `(状态, 阶段)`，阶段编号就是「返回点」。
   本 notebook 用它把后序遍历、子树和、树的直径都改成了迭代版，
   并在深度 2000 的链上验证了「递归爆栈、迭代照常」。
   **必须转的三个信号是：深度不可控、需要可中断、需要可序列化** ——
   后两条在车端工程里比第一条更常见，却几乎不出现在算法教材里。

2. **网格题就是连通域标记，图题在 CV 里几乎总是换了个名字。**
   岛屿数量 = CCL，flood fill = 区域填充，多源 BFS = 距离变换，
   连通域外接框 = mask → bbox。而 **4/8 邻域是语义选择不是实现细节**：
   8 邻域会把角接触的两个标志牌并成一个巨框，4 邻域会把 1 像素宽的斜向反光条切成碎块。

3. **并查集要能默写，也要能说出它做不到什么。**
   两个优化各管一件事（按秩防链化、路径压缩降摊还），
   本 notebook 把「不优化」的代价跑成了 1000 倍的步数差。
   它不能删边、不能分裂、不能查距离——**删边问题的标准套路是离线倒序处理**。

4. **聚类与 NMS 是两件事：合并 vs 筛选。**
   并查集聚类求的是传递闭包，而 IoU 不传递，所以密集场景会 **chaining**——
   本 notebook 用一排框把「6 个宽 100 的框被并成一个宽 225 的巨框」跑了出来。
   跨片合并要用聚类（拼碎片），去重要用 NMS（挑代表），用错的症状非常典型。

5. **把 NMS 讲成「冲突图上的极大独立集」，是这一模块最值钱的 60 秒。**
   它一次性解释了：为什么 NMS 是贪心的、为什么排序不可省、
   为什么密集场景下它更容易出问题（近似比与最大度 $\\Delta$ 有关）、
   以及为什么一维情形可以用 DP 精确解（模块 04）、
   为什么 DETR / YOLOv10 要用一对一匹配从根上绕开它（C53/C54）。
   **能把一个天天用的模块讲出结构，比多刷十道图论题有价值。**"""),
]
