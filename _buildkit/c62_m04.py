# -*- coding: utf-8 -*-
"""C62 模块 04 · 动态规划与贪心。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01（数组与前缀和）、模块 02（排序与二分）、模块 03（递归三要素与记忆化的雏形）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_dp_greedy.ipynb（纯 numpy + 标准库，含 NMS↔加权区间调度的最优解实验）'),
    ("核心参考", "Kleinberg & Tardos《Algorithm Design》第 4/6 章 · CLRS 第 15/16 章 · Bodla et al. Soft-NMS · Solovyev et al. WBF"),
    ("预计时长", "读 70 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("dp-five-steps", "DP 五步：面试里唯一需要的模板", "".join([
        P("先说结论：<strong>面试里 DP 题的翻车，绝大多数不是死在转移方程上，而是死在第一句话——你怎么定义 <code>dp[i]</code></strong>。"
          "状态定义是这道题的「坐标系」，坐标系选歪了，后面的转移、初始化、遍历顺序、答案位置会一起歪，"
          "而且症状极具迷惑性：代码跑得通、小样例过、大样例错，你会花十分钟去 debug 转移方程，但根因在第一行。"),
        P("所以本课只教一个模板，叫 <span class=\"term\">DP 五步</span>。它不是记忆术，它是<strong>你在白板前必须说出口的五句话</strong>——"
          "把这五句话说完，面试官已经能给你打分了，代码只是把它们翻译成 Python。"),
        ASCII("""① 状态定义      dp[i] / dp[i][j] 的含义是什么？（一句完整的中文，必须含「以…结尾」或「前 i 个」这类限定词）
      │            └─ 检验：这句话能不能唯一确定一个数？如果不能，状态就没定义完
      ▼
② 转移方程      dp[i] 由哪些更小的状态决定？决策是什么？
      │            └─ 检验：转移里出现的每一项，都必须在①里被定义过
      ▼
③ 初始化        哪些状态无法由转移得到？它们的值是多少？（含「不可达」用 -inf / +inf 还是 0）
      │            └─ 检验：dp[0] 的语义要和①一致，不能为了凑答案硬填
      ▼
④ 遍历顺序      计算 dp[i] 时它依赖的状态必须已经算好
      │            └─ 检验：把依赖画成箭头，遍历方向必须与箭头同向
      ▼
⑤ 答案位置      答案是 dp[n]？还是 max(dp)？还是 dp[n][m]？
                   └─ 检验：把①的那句话代入，看它是不是题目要的东西"""),
        TABLE(["步骤", "白板上要说的话", "写错时的典型症状", "自检方法"], [
            ["<strong>① 状态定义</strong>", "「我定义 <code>dp[i]</code> 为<em>以第 i 个元素结尾</em>的最大子数组和」",
             "转移写不出来、需要额外变量才能转移、答案取不出来", "<strong>能不能只看这句话就写出转移？</strong>不能就是没定义完"],
            ["② 转移方程", "「第 i 个要么接在前面后面，要么自己另起——<code>dp[i]=max(dp[i-1]+a[i], a[i])</code>」",
             "转移里用到了未定义的量；漏掉某个决策分支", "枚举「最后一步的所有可能决策」，每个决策一个分支"],
            ["③ 初始化", "「<code>dp[0]=a[0]</code>，因为以第 0 个结尾只能是它自己」",
             "越界；把不可达状态填成 0 导致被误选为最优", "不可达用 <code>-inf</code>（求 max）或 <code>+inf</code>（求 min），<strong>不要填 0</strong>"],
            ["④ 遍历顺序", "「i 从小到大，因为 <code>dp[i]</code> 依赖 <code>dp[i-1]</code>」",
             "结果永远等于初始值；或空间压缩后答案变成了另一道题的答案", "画依赖箭头；压缩后重点检查是否读到了「本轮已被覆盖」的值"],
            ["<strong>⑤ 答案位置</strong>", "「答案是 <code>max(dp)</code>，不是 <code>dp[n-1]</code>，因为最大子数组可以在任意位置结束」",
             "<strong>所有中间值都对，最后一步取错</strong>——最隐蔽的一类错", "把①的那句话原样代入题目问句，读一遍是否通顺"],
        ]),
        H3("「状态定义错了后面全错」的诊断法"),
        P("这里给一个可当场演示的例子。<strong>打家劫舍</strong>（相邻两间不能同时偷，求最大值）有两种合法的状态定义："),
        MATH("\\text{A: } dp_i=\\text{前 }i\\text{ 间房能偷到的最大值}\\;\\Rightarrow\\; dp_i=\\max(dp_{i-1},\\ dp_{i-2}+a_i),\\quad \\text{答案}=dp_n"),
        MATH("\\text{B: } f_i=\\textbf{必须偷第 }i\\textbf{ 间}\\text{时的最大值}\\;\\Rightarrow\\; f_i=a_i+\\max_{j\\le i-2} f_j,\\quad \\text{答案}=\\max_i f_i"),
        P("两个都对。<strong>但如果你嘴上说的是 A、心里想的是 B，或者用了 B 的转移却取 A 的答案位置（<code>f_n</code>），就会得到一个「大部分用例都对、少数用例错」的程序</strong>——"
          "因为最优解恰好在最后一间房结束的概率相当高。notebook 里会把这两个版本都实现，并造出让错误版本翻车的用例。"),
        DUAL(
            "诊断法很朴素：<strong>拿到一个错误答案时，不要先改转移方程，先把你的状态定义那句话念出来，然后手算 <code>dp[1]</code> 和 <code>dp[2]</code>，看程序算出来的是不是那个数</strong>。"
            "如果 <code>dp[2]</code> 就已经不符合你的定义，问题在①或③；如果 <code>dp</code> 数组全对但答案错，问题在⑤。"
            "这个二分法能在 30 秒内把 bug 锁死在五步中的一步——<em>而在面试里，「能说清楚 bug 在哪一层」比「一次写对」得分更高</em>。",
            "更严谨地说：DP 的正确性依赖<span class=\"term\">最优子结构</span>（optimal substructure）与<span class=\"term\">无后效性</span>（一旦 $dp_i$ 确定，"
            "后续决策只依赖 $dp_i$ 的值而不依赖它是怎么取到的）。状态定义的本质是<strong>选一个足以屏蔽历史的充分统计量</strong>。"
            "打家劫舍里，「前 $i$ 间的最大值」不足以判断第 $i+1$ 间能不能偷（因为不知道第 $i$ 间偷没偷），所以 A 的转移必须回看两步；"
            "而 B 的状态天然携带了「第 $i$ 间偷了」这条信息，代价是答案要在整个数组上取 max。"
            "<em>两种定义的差别，就是把「第 i 间偷没偷」这一位信息放进状态里还是放进转移里。</em>",
        ),
        CALLOUT("intuition", "一句心法：<strong>状态定义是一句中文，不是一个数组。数组只是这句中文的存储。</strong>面试里先把这句中文说给面试官听，他点头你再动手。"),
        CALLOUT("danger", "<p><strong>最常见的面试翻车姿势：一上来就写 <code>dp = [0]*n</code>。</strong>面试官看到这一行会立刻问「dp[i] 是什么意思？」，"
                "而如果你答不上来或者答得含糊（「就是到 i 为止的结果」——什么结果？），这道题的沟通分就没了，"
                "<em>即使你后面把代码写对，评价也会是「像是背过这道题」</em>。反过来，先说清定义再写代码，"
                "哪怕最后没写完，面试官也能判定你会做。</p>", "先说定义，再写数组"),
    ])),

    # ============================================================== 2
    ("templates", "五类模板与遍历顺序的约束", "".join([
        P("ML/CV 岗的 DP 题不会考区间 DP 的奇技淫巧，考的是下面五类里的前三类。把它们的<strong>识别信号</strong>背下来，"
          "比背题解重要——面试的第一分钟你要做的是<em>把这道题归类</em>。"),
        TABLE(["类别", "状态形状", "识别信号", "代表题", "面试频率"], [
            ["<strong>一维序列 DP</strong>", "<code>dp[i]</code>", "答案与「前 i 个」或「以 i 结尾」有关；决策只看最近 1–2 个",
             "最大子数组和、打家劫舍、跳跃游戏、LIS", "<strong>高频</strong>"],
            ["<strong>双序列 / 网格 DP</strong>", "<code>dp[i][j]</code>", "两个序列对齐，或二维网格上从左上走到右下",
             "编辑距离、LCS、最小路径和、不同路径", "<strong>高频</strong>"],
            ["<strong>背包 DP</strong>", "<code>dp[i][c]</code> → <code>dp[c]</code>", "有「容量/预算」这个第二维；物品选或不选",
             "01 背包、分割等和子集、零钱兑换、目标和", "<strong>高频</strong>"],
            ["状态机 DP", "<code>dp[i][s]</code>，s 是有限状态", "存在「持有/不持有」「冷冻期」「已用几次机会」这类离散状态",
             "买卖股票含冷冻期/手续费/至多 k 次", "中频"],
            ["区间 DP", "<code>dp[i][j]</code>，i≤j", "答案由「合并两个相邻子区间」构成；枚举分割点",
             "戳气球、最长回文子序列、矩阵链乘", "低频（但能答出来是加分项）"],
        ]),
        H3("遍历顺序不是风格问题，是正确性问题"),
        P("遍历顺序的唯一规则是：<strong>计算 <code>dp[x]</code> 时，它依赖的所有状态必须已经是本轮的最终值</strong>。"
          "在二维数组上这条规则很宽松（几乎怎么写都对），一旦做<span class=\"term\">空间压缩</span>（滚动数组）就会变得极其苛刻——"
          "因为压缩后「上一行」和「本行」共用同一块内存，遍历方向直接决定你读到的是旧值还是新值。"),
        ASCII("""二维原始形态                          一维压缩后（同一块内存 dp[c]）
  dp[i][c] = max( dp[i-1][c],           倒序 c: C→0    正序 c: 0→C
                  dp[i-1][c-w] + v )      读 dp[c-w]      读 dp[c-w]
            ▲上一行  ▲上一行左侧          此时它还是         此时它已被
                                          「上一行」的值      本轮覆盖过
  dp[i][c] = max( dp[i-1][c],
                  dp[i][c-w] + v )      ⇒ 每件物品最多取 1 件   ⇒ 同一件物品可重复取
            ▲上一行  ▲本行左侧            = **01 背包**          = **完全背包**

  结论：同一份代码，只把 for c 的方向反过来，解的就是另一道题。""",),
        DUAL(
            "记不住方向怎么办？现场推一遍就行，只要 10 秒：<strong>「我需要的 <code>dp[c-w]</code> 是<em>没考虑当前物品</em>的值，还是<em>已经考虑过当前物品</em>的值？」</strong>"
            "01 背包要前者（每件只能拿一次，所以左边那个状态里不能已经拿过它）→ 必须让 <code>dp[c-w]</code> 保持旧值 → 倒序。"
            "完全背包要后者（可以再拿一件）→ 需要 <code>dp[c-w]</code> 已经更新 → 正序。"
            "<em>把这段话说出来，比写对代码更能证明你懂。</em>",
            "形式化地说，一维压缩把二维递推 $dp^{(i)}[c]=F(dp^{(i-1)}[\\cdot],\\,dp^{(i)}[\\cdot])$ 就地实现，"
            "此时数组在时刻 $t$ 的内容是「已更新前缀 + 未更新后缀」的混合。倒序遍历保证 $c-w<c$ 的位置尚未被本轮触碰，"
            "因而 <code>dp[c-w]</code> 严格等于 $dp^{(i-1)}[c-w]$；正序遍历则保证它等于 $dp^{(i)}[c-w]$。"
            "<strong>空间压缩的代价是：你失去了「回溯出具体选了哪些物品」的能力</strong>（因为中间层被覆盖了）。"
            "面试里若追问「那我要输出方案怎么办」，标准答案是：<em>保留二维表，或者记录 $O(nC)$ 的决策位图，或者用分治法（Hirschberg）以 $O(\\min(n,m))$ 空间换 2 倍时间</em>——"
            "最后一条是编辑距离在长序列上的真实工程做法。",
        ),
        CALLOUT("warn", "空间压缩是<strong>面试里的加分项，不是必答项</strong>。正确的顺序是：先写清楚的二维版本并测通过，"
                "然后说「这里可以压成一维，因为每行只依赖上一行；01 背包要倒序遍历容量，否则会变成完全背包」——"
                "<em>说出来即可得分，不一定要真的改写</em>。反过来，一上来就写一维压缩版然后写错方向，是纯粹的失分。"),
    ])),

    # ============================================================== 3
    ("seq2d", "双序列 DP：编辑距离、LCS，以及它们在评测里的样子", "".join([
        P("双序列 DP 是 ML 岗最值得优先掌握的一类，原因很实际：<strong>你在评测代码里天天用它，只是没意识到</strong>。"
          "OCR / 车牌识别 / 标志文字识别的 <span class=\"term\">CER</span>（character error rate）与语音的 <span class=\"term\">WER</span>，"
          "定义就是「编辑距离 ÷ 参考长度」；时序对齐用的 <span class=\"term\">DTW</span>（dynamic time warping）是同一个递推换了代价函数；"
          "而多目标跟踪里把预测轨迹和真值轨迹对齐算 IDF1 时，序列匹配的骨架也是这个。"),
        MATH("D[i][j]=\\begin{cases} \\max(i,j) & \\min(i,j)=0\\\\[2pt] \\min\\bigl(\\,D[i-1][j]+1,\\;\\; D[i][j-1]+1,\\;\\; D[i-1][j-1]+\\mathbb{1}[a_i\\ne b_j]\\,\\bigr) & \\text{otherwise}\\end{cases}"),
        P("三项分别对应<strong>删除 / 插入 / 替换（或匹配）</strong>。把这三个词说出来，就等于把转移方程讲清楚了。"
          "五步走一遍：①<code>D[i][j]</code> = 把 a 的前 i 个字符变成 b 的前 j 个字符的最少操作数；"
          "②见上式；③<code>D[i][0]=i, D[0][j]=j</code>（全删 / 全插）；④ i、j 都从小到大（依赖左、上、左上）；⑤答案是 <code>D[n][m]</code>。"),
        TABLE(["变体", "改哪一项", "得到什么", "在 ML 里的用途"], [
            ["<strong>LCS</strong>", "去掉替换分支，匹配时 +1 求 max", "最长公共子序列", "diff 工具；序列标注的一致性度量"],
            ["<strong>CER / WER</strong>", "代价全为 1，最后除以参考长度", "错误率", "<strong>OCR / 标志文字识别的标准指标</strong>"],
            ["加权编辑距离", "替换代价按混淆概率给（如 0↔O 便宜）", "领域敏感的距离", "车牌识别的容错评测"],
            ["<strong>DTW</strong>", "代价换成 $|x_i-y_j|$，允许重复对齐（不删不插）", "时序弯曲距离", "轨迹相似度、时序对齐、动作匹配"],
            ["最长公共子串", "不匹配时直接置 0，答案取全表 max", "连续公共段", "近重复检测的一个廉价特征"],
        ]),
        DUAL(
            "为什么这几道题「长得那么像」？因为它们问的都是同一个问题：<strong>把两个序列的元素两两配对，配对必须保持顺序不交叉，求最优配对</strong>。"
            "编辑距离允许「配不上就删/插并付代价」，LCS 只数「配上了几对」，DTW 允许「一对多」。"
            "<em>识别信号很好记：只要题目里出现两个序列且要求保序，就画二维表。</em>",
            "更精确地说，这类问题的解空间是<strong>两个序列索引的单调对齐路径</strong>：从 $(0,0)$ 走到 $(n,m)$，"
            "每步只能向右、向下或右下。不同的题只是给三种走法配了不同的代价。因此它们共享同一套性质："
            "时间 $O(nm)$、空间可压到 $O(\\min(n,m))$、路径可回溯出对齐方案。"
            "<strong>面试里被追问「能不能更快」时，标准答案是：一般情况下 $O(nm)$ 在细粒度归约下是紧的（SETH 条件下无法做到 $O((nm)^{1-\\epsilon})$），"
            "但如果只需要判断编辑距离是否 $\\le k$，可以只算主对角线附近的带状区域，降到 $O(nk)$</strong>——"
            "<em>后者正是真实 CER 计算库的优化，也是这道题最好的加分点</em>。",
        ),
        CALLOUT("intuition", "把编辑距离的三个分支翻译成人话：「<strong>我把 a 的最后一个字扔了</strong>（删）／"
                "「<strong>我在结果末尾补一个字</strong>」（插）／「<strong>这两个字对上了，对不上就改一下</strong>」（替换）。"
                "面试里边写边说这三句，比念公式有效得多。"),
    ])),

    # ============================================================== 4
    ("knapsack", "背包：从「选或不选」到「算力预算下的方案选择」", "".join([
        P("背包是唯一一类<strong>能直接对应你日常工作的 DP 题</strong>：给定一个预算（显存 / 延迟 / 标注人天 / 带宽），"
          "从一堆候选方案里挑一个组合使收益最大。C57 模块 05 排「小目标方案优先级」、"
          "C58 模块 04 分「标注预算」、C63 模块 04 做「容量估算」，本质都是背包。"),
        MATH("\\text{01 背包：}\\;dp[i][c]=\\max\\bigl(dp[i-1][c],\\;\\; dp[i-1][c-w_i]+v_i\\bigr),\\qquad dp[0][c]=0"),
        TABLE(["变体", "每件物品", "一维遍历方向", "初始化（求最大价值）", "初始化（求恰好装满）"], [
            ["<strong>01 背包</strong>", "最多取 1 件", "<strong>容量倒序</strong> C→w", "<code>dp[*]=0</code>", "<code>dp[0]=0</code>，其余 <code>-inf</code>"],
            ["<strong>完全背包</strong>", "可取无限件", "<strong>容量正序</strong> w→C", "<code>dp[*]=0</code>", "<code>dp[0]=0</code>，其余 <code>-inf</code>"],
            ["多重背包", "最多取 k 件", "二进制拆分成 01 背包", "同上", "同上"],
            ["分组背包", "每组至多选 1 件", "外层组、内层容量倒序、最内层组内物品", "同上", "同上"],
            ["<strong>零钱兑换（最少硬币）</strong>", "可取无限件", "正序", "—", "<code>dp[0]=0</code>，其余 <code>+inf</code>"],
        ]),
        P("<strong>「恰好装满」那一列是高频追问点。</strong>如果初始化时把所有 <code>dp[c]</code> 都填 0，"
          "就等价于宣称「容量 c 存在一个价值 0 的合法方案」，"
          "于是那些其实<em>凑不出来</em>的容量会被当成可行解参与 max，结果偏大且无法察觉。"
          "求最少个数时同理，不可达必须是 <code>+inf</code>。<em>这就是第 1 节说的「不可达状态不要填 0」。</em>"),
        DUAL(
            "背包在工程里最常见的伪装是：<strong>「延迟预算 33 ms，感知分到 12 ms，这 12 ms 里我要塞检测 + 跟踪 + 分类，各有几档配置，怎么配 AP 最高？」</strong>"
            "如果每个模块必须选且只能选一档，那是<em>分组背包</em>；如果某些模块可选可不选，那是 01 背包；"
            "如果预算是连续的（毫秒），就先量化成整数网格（比如 0.1 ms 一格）再跑 DP。"
            "<em>能在系统设计面试里把「配置选择」一句话归约到背包，是很强的信号。</em>",
            "但要诚实地说清背包解法的<strong>三个前提</strong>，否则会被追问打穿："
            "<em>① 价值可加</em>——各模块的 AP 增益必须近似独立，实际上检测器换了，跟踪器的收益也会变，存在交互项；"
            "<em>② 代价可加</em>——延迟必须能线性相加，但存在显存带宽争抢、kernel launch 开销、流水线重叠，实测常常不等于求和；"
            "<em>③ 容量是整数且不大</em>——伪多项式复杂度 $O(nC)$，$C$ 太大（比如按微秒离散）就退化。"
            "<strong>0-1 背包是 NP-hard 的（判定版本是 NP-完全），$O(nC)$ 里的 $C$ 是数值而不是输入长度，这就是「伪多项式」的含义</strong>——"
            "面试官问「背包不是有多项式算法吗，怎么会 NP-hard」时，答的就是这一句。",
        ),
        CALLOUT("warn", "<strong>面试里的经典陷阱：分割等和子集。</strong>「能否把数组分成两个和相等的子集」看起来是搜索题，"
                "实际是容量为 <code>sum/2</code> 的 01 背包可行性问题（<code>dp[c]</code> 为布尔）。"
                "<em>识别信号：出现「恰好 / 是否存在 / 目标和」且元素只能用一次。</em>先判 <code>sum</code> 是否为奇数——奇数直接返回 False，"
                "这个 1 行的剪枝面试官一定在等你写。"),
    ])),

    # ============================================================== 5
    ("memo", "记忆化搜索与递推的互转：先写能跑的那一版", "".join([
        P("在 45 分钟的面试里，<strong>记忆化搜索（top-down）通常是更安全的选择</strong>，因为它把「遍历顺序」这一步免掉了——"
          "递归天然按依赖顺序求值。代价是常数更大、有栈深度风险。这里给出两者的机械互转法，"
          "以及一条实用建议：<em>先写记忆化把逻辑跑通，再当着面试官的面说「这可以改写成自底向上的递推，遍历顺序是 …」</em>。"),
        ASCII("""记忆化搜索（top-down）                     递推（bottom-up）
┌───────────────────────────────┐        ┌───────────────────────────────┐
│ def f(i, c):                  │        │ dp = [[init]*(C+1) ...]       │
│     if 边界: return 基准值    │  ⇄     │ for i in 依赖方向:            │
│     if (i,c) in memo: return  │        │     for c in 依赖方向:        │
│     memo[(i,c)] = max(        │        │         dp[i][c] = max(       │
│         f(i-1, c),            │        │             dp[i-1][c],       │
│         f(i-1, c-w)+v)        │        │             dp[i-1][c-w]+v)   │
│     return memo[(i,c)]        │        │ return dp[n][C]               │
└───────────────────────────────┘        └───────────────────────────────┘
   函数参数  →  数组下标
   递归调用  →  读更早的数组元素
   边界条件  →  初始化
   （无需想）→  **遍历顺序**  ← 唯一需要额外思考的一步
   只算到达的状态（可能更省）  ← 权衡 →  无递归开销、可空间压缩（通常更快）"""),
        TABLE(["维度", "记忆化搜索", "自底向上递推", "面试建议"], [
            ["写起来", "<strong>快，照抄暴力递归 + 一个 cache</strong>", "要先想清遍历顺序", "<strong>先写记忆化</strong>"],
            ["状态空间稀疏时", "<strong>只算可达状态，可能快很多</strong>", "整表都要填", "稀疏就用记忆化"],
            ["常数与栈", "字典哈希 + 函数调用，慢 3–10×；Python 默认递归深度 1000", "数组访问，快", "n 上万必须转递推"],
            ["空间压缩", "<strong>做不到</strong>", "可滚动数组", "被问「能不能省空间」时必须提递推"],
            ["调试", "打印调用树，直观", "打印 dp 表，直观", "两者都好调"],
        ]),
        P("Python 里记忆化只要一行装饰器：<code>from functools import lru_cache</code> + <code>@lru_cache(maxsize=None)</code>"
          "（3.9+ 可用 <code>@cache</code>）。<strong>但要注意两条：参数必须可哈希（list 要转 tuple）；"
          "递归深度默认 1000，链式依赖的题（如 n=10⁴ 的 LIS）会 <code>RecursionError</code></strong>。"
          "面试里主动说「我这里用 lru_cache，但如果 n 到 10⁵ 我会改成递推避免爆栈」——这是免费的分。"),
        H3("区间 DP：唯一需要「按区间长度遍历」的一类"),
        P("区间 DP 的状态是 <code>dp[i][j]</code>（区间 <code>[i,j]</code> 的最优值），转移要枚举分割点 <code>k</code>，"
          "依赖的是<strong>更短的区间</strong>。所以遍历顺序不是「i 从小到大」，而是<strong>「长度从小到大」</strong>："
          "<code>for L in range(2, n+1): for i in range(n-L+1): j = i+L-1</code>。"
          "<em>这是「遍历顺序必须与依赖方向同向」这条规则最典型的体现——如果你写记忆化，这一步根本不用想。</em>"),
        CALLOUT("intuition", "面试策略：<strong>记忆化搜索是你的安全网。</strong>任何 DP 题，只要你能写出正确的暴力递归，"
                "加一个 cache 就是一个正确的 DP。所以卡住时的标准脱困路径是：<em>「我先写一个暴力递归确保语义正确，"
                "然后加记忆化，最后如果还有时间我把它改成递推并压缩空间。」</em>——这句话本身就展示了完整的解题方法论。"),
    ])),

    # ============================================================== 6
    ("greedy", "贪心：正确性论证与那个「看起来对但错」的反例", "".join([
        P("贪心的难点从来不是写代码（通常 5 行），而是<strong>证明它对</strong>。面试里贪心题的评分点几乎全部在这里："
          "面试官想听的不是「我按结束时间排序」，而是<strong>「为什么按结束时间排序一定不会更差」</strong>。"),
        H3("交换论证：一个可以背下来的证明模板"),
        P("<span class=\"term\">交换论证</span>（exchange argument）的骨架只有四句话，任何贪心题都能套："),
        OL([
            "设 <strong>G</strong> 是贪心解，<strong>O</strong> 是任意一个最优解，且 O 与 G 在<strong>第 k 步第一次不同</strong>（前 k−1 步相同）。",
            "把 O 的第 k 步<strong>换成</strong> G 的第 k 步，得到 O′。",
            "证明 <strong>O′ 仍然合法</strong>（不违反约束）<strong>且不比 O 差</strong>（目标值不下降）。",
            "于是可以反复交换把 O 变成 G 而目标值不下降 ⇒ <strong>G 也是最优解</strong>。归纳完成。",
        ]),
        P("以<strong>区间调度</strong>（给一堆区间，选最多个互不重叠的）为例，贪心是「按结束时间从早到晚选」。套模板："),
        MATH("\\text{设 } g_k=[s,e),\\; o_k=[s',e') \\text{ 且 } g_k\\ne o_k.\\;\\text{贪心选最早结束} \\Rightarrow e\\le e'."),
        P("因为 O 的第 k+1 个区间的起点 $\\ge e' \\ge e$，把 $o_k$ 换成 $g_k$ 后与后续区间仍不冲突，"
          "个数不变 ⇒ O′ 合法且同样最优。<strong>这个「$e\\le e'$ 所以换了之后后面只会更宽松」就是整个证明的核心，"
          "面试里说这一句就够了。</strong>"),
        H3("一个「看起来对但错」的反例：找零"),
        P("现在换一道几乎一模一样的题：<strong>给定硬币面值，用最少的硬币凑出金额 amount</strong>。"
          "自然的贪心是「每次拿能拿的最大面值」。在人民币面值 <code>[1,5,10,20,50,100]</code> 上它是对的，"
          "在 <code>[1,25,10,5]</code>（美分）上也是对的——<em>所以你会误以为它总是对的</em>。但："),
        TABLE(["面值集合", "目标", "贪心的解", "最优解", "结论"], [
            ["<code>[1, 3, 4]</code>", "6", "4 + 1 + 1 = <strong>3 枚</strong>", "3 + 3 = <strong>2 枚</strong>", "<strong>贪心错</strong>"],
            ["<code>[1, 15, 25]</code>", "30", "25 + 1×5 = <strong>6 枚</strong>", "15 + 15 = <strong>2 枚</strong>", "<strong>贪心错得离谱</strong>"],
            ["<code>[1, 5, 10, 25]</code>", "任意", "同最优", "同最优", "对（该面值系是 canonical 的）"],
            ["<code>[1, 3, 4]</code>", "5", "4 + 1 = 2 枚", "4 + 1 = 2 枚", "<strong>小用例上巧合正确</strong> ← 陷阱"],
        ]),
        P("<strong>注意最后一行。</strong>如果你在面试里只手测了 amount=5，贪心会通过，你会自信地说「这题贪心就行」，"
          "然后面试官给你 amount=6。<em>这正是「看起来对但错」的杀伤方式：反例往往不在最小的用例里。</em>"),
        DUAL(
            "为什么区间调度能贪心而找零不能？直觉上：<strong>区间调度里「早结束」这个局部优势是<em>单调传递</em>的——早结束的区间给后面留下的空间严格更大，永远不亏；"
            "而找零里「拿大面值」这个局部优势会<em>破坏余额的结构</em>——拿了 4 之后剩下 2，而 2 只能用两个 1 凑，"
            "你在第一步换来的收益（少拿一枚）被第二步的损失（多拿两枚）盖过了。</strong>"
            "<em>判别口诀：局部最优能不能「用一个不等式传递到下一步」？能就可能贪心，不能就上 DP。</em>",
            "严格的判据是<span class=\"term\">拟阵</span>（matroid）与<strong>贪心选择性质 + 最优子结构</strong>："
            "若可行解族构成拟阵（满足遗传性与交换性质），按权重贪心必然最优（Rado–Edmonds 定理）；"
            "区间调度虽不是拟阵但满足更弱的交换论证条件。找零问题的可行解族<strong>不</strong>满足交换性质："
            "把最优解 $\\{3,3\\}$ 里的一枚换成贪心的 $4$，得到 $\\{4,3\\}$ 面值和是 7 而不是 6，"
            "<em>交换后不合法，第 3 步就断了</em>——这恰恰说明「交换论证走不通」本身就是「贪心不对」的强烈信号。"
            "<strong>面试里如果交换论证卡在第 3 步，不要硬凑，直接改用 DP，并说明「我尝试了交换论证但换完不合法，说明贪心选择性质不成立」</strong>——"
            "这是极高质量的回答。",
        ),
        H3("DP 还是贪心？三条判别线"),
        TABLE(["观察到", "倾向", "理由", "典型题"], [
            ["能给出一个「排序键」，且排完序一遍扫描就能定", "<strong>贪心</strong>", "存在可传递的局部优势", "区间调度、分发饼干、跳跃游戏 II"],
            ["有<strong>容量/预算</strong>这一维，物品有「性价比」但不能拆分", "<strong>DP（背包）</strong>", "按性价比贪心在<em>不可分割</em>时会错", "01 背包、零钱兑换"],
            ["决策会<strong>改变后续可选集合的结构</strong>（而不只是缩小它）", "<strong>DP</strong>", "无法用一个不等式传递", "找零、加权区间调度"],
            ["物品<strong>可以拆分</strong>（分数背包）", "<strong>贪心</strong>", "按 $v/w$ 排序取满即最优（可用交换论证证明）", "分数背包、带宽分配"],
            ["能构造出反例", "<strong>DP</strong>", "—", "<em>面试里花 60 秒试着构造反例，是很值的投资</em>"],
        ]),
        CALLOUT("danger", "<p><strong>面试里最危险的贪心句式是「我觉得贪心应该可以」。</strong>面试官听到「我觉得」就会开始找反例，"
                "而你没有准备。正确的说法有两种：<em>①「我可以用交换论证证明：假设最优解与贪心解第一次不同于第 k 步…」——给出证明；"
                "②「我怀疑贪心不对，让我花半分钟找个反例……面值 [1,3,4] 凑 6，贪心 3 枚而最优 2 枚，所以要用 DP」——给出反例</em>。"
                "<strong>两条路都得分，只有「我觉得」不得分。</strong></p>", "要么证明，要么反例，不要「我觉得」"),
    ])),

    # ============================================================== 7
    ("nms-wis", "亮点实验：把 NMS 建模成加权区间调度，量化贪心的次优", "".join([
        P("这一节是本模块存在的理由。<strong>你每天用的 NMS 就是一个贪心算法，而且是一个可以被证明次优的贪心算法</strong>——"
          "把它和加权区间调度对照着看，你会同时理解两件事：这道算法题在考什么，以及你的检测器为什么会把两块相邻的限速牌合并成一个框。"),
        H3("归约：一维场景下 NMS = 加权区间调度"),
        P("考虑一个简化但真实的场景：<strong>龙门架上并排挂着几块标志，检测框在 x 轴上排成一列</strong>（y 方向差异可忽略）。"
          "把每个检测框看成一个区间 $[s_i, e_i)$，score 看成权重 $w_i$。把 NMS 的 IoU 阈值取 0（<em>任何重叠都算冲突</em>），于是："),
        ASCII("""NMS（贪心）                              加权区间调度（DP）
─────────────────────────────           ─────────────────────────────
输入 : 框 + 分数                        输入 : 区间 + 权重
约束 : 保留的框两两不重叠               约束 : 选中的区间两两不重叠
目标 : （隐含）留下"对的那些框"         目标 : 总权重最大
算法 : 按分数降序，能留就留             算法 : 按结束时间排序 + DP
                                                p(j) = 最大的 i<j 使 e_i <= s_j
复杂度: O(n log n + nK)                  复杂度: O(n log n)
最优性: **无保证**                       最优性: **精确最优**

           A ████████████████████  w=10        贪心先拿 A（分数最高）→ B、C 被抑制 → 总分 10
           B █████                 w=6         DP  选 B + C（互不重叠）      → 总分 12
           C           ██████      w=6
           ───────────────────────► x          **贪心 / 最优 = 10/12 = 0.833**""",),
        MATH("\\mathrm{OPT}(j)=\\max\\bigl(\\underbrace{\\mathrm{OPT}(j-1)}_{\\text{不选第 }j\\text{ 个}},\\;\\; \\underbrace{w_j+\\mathrm{OPT}(p(j))}_{\\text{选第 }j\\text{ 个}}\\bigr),\\qquad \\mathrm{OPT}(0)=0"),
        P("上面那个 A/B/C 的例子不是玩具——<strong>它就是「一个覆盖两块牌子的大框，分数略高于两个正确的小框」这一真实失效模式</strong>。"
          "贪心 NMS 一定会保留大框并杀掉两个正确框，最终 recall 掉一半；而 DP 会保留两个小框。"
          "notebook 里会把这个场景合成出来，并同时报告两个指标：<em>总分</em>与<em>真正找回了几块牌子</em>。"),
        H3("贪心到底能差多少？答案是：可以任意差"),
        P("构造一族反例：一个长框覆盖 $k$ 块牌子、权重 $1+\\epsilon$；$k$ 个正确的小框各权重 1。"
          "贪心拿长框得 $1+\\epsilon$，最优拿 $k$ 个小框得 $k$，比值 $\\frac{1+\\epsilon}{k}\\to 0$。"
          "<strong>所以「贪心 NMS 的近似比」没有常数下界</strong>——它不是「差一点点」，是「原则上可以差任意多」。"
          "在随机场景上它通常很接近最优（notebook 实测均值 > 0.97），<em>但最坏情况恰好发生在密集排列的标志上，"
          "而那正是 TSR 最在意的场景</em>。"),
        DUAL(
            "那为什么工业界不换成 DP？三个理由，缺一不可，<strong>这也是这道题在面试里最好的收尾</strong>："
            "<em>① 二维不成立</em>——一维区间的「不重叠」关系有良好结构（区间图），MWIS 可 DP 求解；"
            "二维 bbox 的冲突图是任意图，最大权独立集是 NP-hard，DP 没了。"
            "<em>② 目标函数是假的</em>——「总分最大」只是代理目标，真正想要的是「每个真实目标恰好留一个框」，"
            "分数高不等于框对。<em>③ 延迟</em>——NMS 已经是延迟的方差来源（见 C53-04），换成更重的算法只会更糟。",
            "但这个分析<strong>指出了改进方向，而这正是真实工作的样子</strong>："
            "既然贪心的失效模式是「高分框独吞一片区域」，那么补救手段就都围绕「别让它一票否决」展开——"
            "<span class=\"term\">Soft-NMS</span> 不删框而是按重叠度衰减分数（把硬约束软化）；"
            "<span class=\"term\">Cluster-NMS / Matrix-NMS</span> 把抑制关系矩阵化并迭代，逼近全局解且可并行；"
            "<span class=\"term\">WBF</span>（weighted boxes fusion）把一簇框加权融合而不是择一（见 C56-04）；"
            "而 <strong>DETR 系与 YOLOv10 的一对一标签分配则是从根上取消这个组合优化问题</strong>——"
            "训练期就保证每个目标只有一个正样本，推理期无需去重（见 C53-04、C54）。"
            "<em>「贪心的次优性 → 三条改进路线」这条链路，是把算法题和检测岗位真正连起来的地方。</em>",
        ),
        CALLOUT("intuition", "<strong>一句话把两件事焊死：NMS 是「最大权独立集」的贪心近似，"
                "一维时最优解可以用加权区间调度 DP 精确求出，二维时问题变成 NP-hard 所以只能贪心。</strong>"
                "面试里被问「NMS 的本质是什么」，这就是满分答案（并可引 C62 模块 03 的图论表述）。"),
        CALLOUT("warn", "别把这个结论说过头。<strong>不要说「NMS 是错的，应该用 DP」</strong>——"
                "面试官会立刻反问二维复杂度和延迟，你会答不上来。"
                "<em>正确的表述是：「NMS 是一个贪心近似，它的失效模式可以被精确刻画（高分框独吞区域），"
                "在一维退化情形下我可以用 DP 求出最优解并量化这个 gap；工程上的解法不是换成 DP，而是 Soft-NMS / WBF / 一对一分配。」</em>"),
    ])),

    # ============================================================== 8
    ("interview", "题单、优先级与答题骨架", "".join([
        P("按「频率 × 是否必会」排优先级。<strong>如果只有一天时间，把「高频 + 必会」这七道题做到闭着眼睛写对，"
          "剩下的只要能说清思路就够了</strong>。每题给出<em>状态定义的那一句中文</em>——这是你在白板上要说的第一句话。"),
        TABLE(["题", "频率", "分级", "类别", "状态定义（要说出口的那句话）", "复杂度"], [
            ["最大子数组和 (Kadane)", "<strong>高频</strong>", "<strong>必会</strong>", "一维", "<code>dp[i]</code> = <strong>以 i 结尾</strong>的最大子数组和；答案 <code>max(dp)</code>", "O(n)/O(1)"],
            ["编辑距离", "<strong>高频</strong>", "<strong>必会</strong>", "双序列", "<code>D[i][j]</code> = a 前 i 个变成 b 前 j 个的最少操作数", "O(nm)/O(min)"],
            ["最长公共子序列", "<strong>高频</strong>", "<strong>必会</strong>", "双序列", "<code>L[i][j]</code> = a 前 i 个与 b 前 j 个的 LCS 长度", "O(nm)"],
            ["零钱兑换（最少硬币）", "<strong>高频</strong>", "<strong>必会</strong>", "完全背包", "<code>dp[c]</code> = 凑出金额 c 的最少硬币数，不可达为 +inf", "O(nC)"],
            ["01 背包 / 分割等和子集", "<strong>高频</strong>", "<strong>必会</strong>", "背包", "<code>dp[c]</code> = 容量 c 时的最大价值（或可行性布尔）", "O(nC)"],
            ["最长上升子序列", "<strong>高频</strong>", "必会(n²)/<strong>加分</strong>(n log n)", "一维", "<code>dp[i]</code> = <strong>以 i 结尾</strong>的 LIS 长度；或 <code>tails[k]</code> = 长为 k+1 的上升子序列的最小结尾", "O(n²) / O(n log n)"],
            ["跳跃游戏 I / II", "<strong>高频</strong>", "<strong>必会</strong>", "贪心", "维护「当前这一跳能到的最远边界」，越界即 +1 步", "O(n)"],
            ["不同路径 / 最小路径和", "中频", "<strong>必会</strong>", "网格", "<code>dp[i][j]</code> = 走到 (i,j) 的方案数 / 最小代价", "O(nm)"],
            ["打家劫舍 I / II", "中频", "<strong>必会</strong>", "一维", "见第 1 节的 A / B 两种定义", "O(n)/O(1)"],
            ["买卖股票（冷冻期/手续费/k 次）", "中频", "加分", "状态机", "<code>dp[i][s]</code>，s ∈ {持有, 不持有, 冷冻}", "O(nk)"],
            ["区间调度（最多不重叠区间）", "中频", "<strong>必会</strong>", "贪心", "按<strong>结束时间</strong>升序，能选就选（交换论证）", "O(n log n)"],
            ["<strong>加权区间调度</strong>", "低频", "<strong>加分</strong>", "DP", "<code>OPT(j)</code> = 前 j 个区间（按结束排序）的最大权重", "O(n log n)"],
            ["分发糖果（两遍贪心）", "低频", "加分", "贪心", "左右各扫一遍取 max，说明两个约束可分离", "O(n)"],
            ["戳气球 / 最长回文子序列", "低频", "加分", "区间", "<code>dp[i][j]</code> = 区间 [i,j] 的最优值，按<strong>长度</strong>遍历", "O(n³)/O(n²)"],
        ]),
        P("<em>「合并区间」「和为 K 的子数组」等区间与前缀和题在模块 01，「Top-K」「在答案上二分」在模块 02，"
          "「并查集做框聚类」「NMS 作为极大独立集」在模块 03——本节不重复。</em>"),
        H3("三个高频追问的标准骨架"),
        TABLE(["追问", "面试官想听", "30 秒骨架", "踩雷点"], [
            ["「这题为什么不能贪心？」",
             "你会用<strong>反例</strong>或<strong>交换论证失败</strong>来回答，而不是「感觉不行」",
             "「我先试交换论证：把最优解的第一个不同决策换成贪心的决策，需要证明换完仍合法且不更差。这里换完<em>不合法</em>（举例说明），说明贪心选择性质不成立。再补一个具体反例：面值 [1,3,4] 凑 6，贪心 3 枚、最优 2 枚。所以用 DP。」",
             "只给反例不给结构性理由；或只说「DP 更保险」"],
            ["「能不能优化空间？」",
             "你知道压缩的<strong>条件</strong>与<strong>代价</strong>",
             "「每行只依赖上一行，所以可以滚动成一维，空间 O(nm)→O(min(n,m))。01 背包压缩后容量必须<strong>倒序</strong>遍历，否则会变成完全背包。代价是丢失回溯能力——要输出具体方案就得保留二维表，或者用 Hirschberg 分治以 2 倍时间换 O(min) 空间。」",
             "说「可以压缩」但答不出倒序；或忘了提丢失方案回溯"],
            ["「LIS 的 O(n log n) 解法里那个数组是什么？」",
             "你知道它<strong>不是</strong> LIS 本身",
             "「<code>tails[k]</code> 是所有长度为 k+1 的上升子序列中<strong>最小的结尾值</strong>。它单调递增所以能二分。注意它的<em>内容不是任何一个真实的 LIS</em>，只有<em>长度</em>是对的；要还原具体序列得额外记前驱。」",
             "<strong>把 tails 当成 LIS 输出</strong>——这是这道题最经典的错误"],
        ]),
        CALLOUT("intuition", "所有 DP 题的开场白都可以复用同一句：<strong>「我先定义状态：<code>dp[i]</code> 表示……。"
                "这样定义是因为它足以决定后续决策，不需要回看更多历史。」</strong>"
                "——第二句解释了「为什么这么定义」，而这正是面试官在等的东西。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>去重从「推理期组合优化」变成「训练期约束」。</strong>NMS 之所以是贪心近似，是因为它在推理期解一个 NP-hard 的最大权独立集。"
            "DETR 的一对一匈牙利匹配、YOLOv10 的一致双分配都是把这个问题<em>挪到训练期</em>解决。"
            "<em>开放问题：一对一分配带来的监督稀疏与匹配不稳定（见 C54-04）尚无最优解，Group/Co-DETR 的「训练一对多、推理一对一」是当前折中。</em>",
            "<strong>可微分的组合优化。</strong>把排序、Top-K、匹配、动态规划做成可微算子（soft-DTW、differentiable DP、Sinkhorn 近似匈牙利、"
            "Gumbel-Top-K），使「选择」本身可以被端到端训练。<em>soft-DTW 在时序对齐上已经实用；"
            "可微 NMS 的尝试（如 Learning-NMS）效果有限，这仍是开放方向。</em>",
            "<strong>DP 的细粒度复杂度下界。</strong>编辑距离在 SETH 假设下不存在 $O(n^{2-\\epsilon})$ 算法（Backurs–Indyk 2015），"
            "LCS 同理。<em>这类结果解释了为什么工程上只能走「带状近似」「量化剪枝」而不是找更好的精确算法</em>——"
            "面试里知道「这是有条件下界的」是很强的信号。",
            "<strong>近似算法的实用取舍。</strong>MWIS 在一般图上难以近似（$n^{1-\\epsilon}$ 不可近似），"
            "但在<em>有界厚度</em>（bounded thickness）的几何图上有 PTAS。<em>检测框的冲突图恰好是几何图且局部稀疏，"
            "理论上存在比贪心更好的多项式近似，但常数与延迟使其在车端不实用——这是「理论可行 ≠ 工程可用」的好例子。</em>",
            "<strong>把预算分配问题做成在线/自适应背包。</strong>车端算力预算随其他任务负载波动（见 C53-04 的运行时降级），"
            "静态背包解出的配置在运行时可能不可行。<em>在线背包与 bandit 式资源分配在这类场景下的理论保证仍不完善。</em>",
            "<strong>LLM 时代的算法面试还考不考 DP？</strong>业界正在从「手撕算法」转向「结对编程 + 代码审查 + 系统设计」。"
            "<em>但 DP 题的核心考点——把模糊问题形式化成状态与转移、并论证正确性——恰恰是 AI 辅助编程无法替代的部分，"
            "所以短期内它只会换形式，不会消失。</em>",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Kleinberg &amp; Tardos, <em>Algorithm Design</em>, 第 4 章（贪心与交换论证，"
                "§4.1 区间调度的证明是本模块第 6 节的原型）与第 6 章（动态规划，§6.1–6.2 的加权区间调度就是第 7 节的骨架）。"
                "<strong>★</strong> Cormen et al., <em>CLRS</em> 第 15 章（DP：最优子结构与无后效性的形式化）、第 16 章（贪心与拟阵，"
                "§16.4 的 Rado–Edmonds 定理给出了「什么时候贪心一定对」的充分条件）。</p>"
                "<p>与检测的连接：Bodla et al., <em>Soft-NMS — Improving Object Detection With One Line of Code</em>（ICCV 2017）；"
                "Solovyev et al., <em>Weighted Boxes Fusion</em>（Image and Vision Computing 2021）；"
                "Jiang et al., <em>Cluster-NMS / Enhancing Geometric Factors in Model Learning</em>（IEEE TCyb 2021）。"
                "复杂度下界：Backurs &amp; Indyk, <em>Edit Distance Cannot Be Computed in Strongly Subquadratic Time</em>（STOC 2015）。"
                "可微组合优化：Cuturi &amp; Blondel, <em>Soft-DTW</em>（ICML 2017）；Mena et al., <em>Learning Latent Permutations with Gumbel-Sinkhorn</em>（ICLR 2018）。"
                "相邻课程：模块 03（NMS 作为图上极大独立集、并查集做框聚类）、模块 05（timed drill 与采样题）、"
                "C53-04（NMS 的延迟方差与无 NMS 检测器）、C54（匈牙利匹配）、C56-04（WBF）、C57-05（方案组合排序）。"
                "完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 04 · 动态规划与贪心（DP 五步 / 背包 / 交换论证 / NMS 的次优性）

目标：把 DP 从「背题解」变成**五句话的机械流程**，把贪心从「感觉可以」变成**能证明或能举反例**。

本 notebook 你会亲手实现：
1. **DP 五步检查器**，以及「答案位置取错」的翻车演示（Kadane）
2. **打家劫舍的两种状态定义**，构造出让「转移用 B、答案位置用 A」翻车的用例
3. **编辑距离**（二维 / 滚动数组 / **带状 O(nk)**）与 CER，**LCS 及方案回溯**
4. **01 背包与完全背包**：同一份一维代码，只把遍历方向反过来就变成另一道题
5. **LIS 的 O(n²) 与 O(n log n) 对拍**，并证明 `tails` 数组**不是**一个真实的上升子序列
6. **记忆化搜索 ↔ 递推**的互转与实测常数差
7. **交换论证的数值验证**：区间调度三种排序键谁对谁错；**找零的贪心反例**
8. **亮点实验**：把 NMS 建模成**加权区间调度**，用 DP 求最优解，
   量化贪心 NMS 的次优程度，并复现「一个大框吃掉两块牌子」的真实失效模式
9. 二维情形下最大权独立集的**暴力求解**，说明为什么工程上只能用贪心

> 心智模型：**状态定义是一句中文，不是一个数组。贪心要么能证明，要么能举反例，没有第三种答案。**"""),

    md("""## 1 · DP 五步：先把五句话说出来

把五步写成一个 dict，逼自己每一步都填。**第 ⑤ 步「答案位置」是最容易漏的一项**——
所有中间值都算对，最后一行取错，是最难 debug 的一类错误。"""),

    code("""import bisect, math, random, time
from functools import lru_cache
import numpy as np

rng = np.random.default_rng(0)
random.seed(0)

FIVE_STEPS = ("状态定义", "转移方程", "初始化", "遍历顺序", "答案位置")

def check_dp_plan(plan):
    # 返回 (是否五步齐全, 缺失的步骤列表)
    missing = [s for s in FIVE_STEPS if not plan.get(s, "").strip()]
    return (len(missing) == 0), missing

plan_kadane = {
    "状态定义": "dp[i] = 以第 i 个元素结尾的最大子数组和",
    "转移方程": "dp[i] = max(dp[i-1] + a[i], a[i])   # 接上去 or 另起",
    "初始化":   "dp[0] = a[0]",
    "遍历顺序": "i 从小到大（dp[i] 依赖 dp[i-1]）",
    "答案位置": "max(dp)  —— 不是 dp[n-1]，因为最大子数组可以在任意位置结束",
}
plan_missing = dict(plan_kadane); plan_missing["答案位置"] = ""

print("完整计划 :", check_dp_plan(plan_kadane))
print("缺一步   :", check_dp_plan(plan_missing))
assert check_dp_plan(plan_kadane) == (True, [])
assert check_dp_plan(plan_missing) == (False, ["答案位置"])

# ── 按上面的五步实现 Kadane，并与暴力对拍 ──
def max_subarray(a):
    dp = best = a[0]                 # ③ 初始化
    for x in a[1:]:                  # ④ i 从小到大
        dp = max(dp + x, x)          # ② 转移
        best = max(best, dp)         # ⑤ 答案是 max(dp)
    return best

def max_subarray_last_dp(a):
    # 故意把 ⑤ 写成 dp[n-1]：中间值全对，只有答案位置错
    dp = a[0]
    for x in a[1:]:
        dp = max(dp + x, x)
    return dp

def max_subarray_brute(a):
    return max(sum(a[i:j]) for i in range(len(a)) for j in range(i + 1, len(a) + 1))

bad = 0
for _ in range(300):
    n = random.randint(1, 12)
    a = [random.randint(-9, 9) for _ in range(n)]
    assert max_subarray(a) == max_subarray_brute(a), a
    if max_subarray_last_dp(a) != max_subarray_brute(a):
        bad += 1
print(f"\\n正确版 300/300 与暴力一致；\\"答案位置\\"写错的版本在 {bad}/300 个随机用例上给出错误答案")
demo = [-1, -2, -3]
print(f"最刺眼的一个: a={demo}  正确={max_subarray(demo)}  取 dp[n-1]={max_subarray_last_dp(demo)}")
assert max_subarray(demo) == -1 and max_subarray_last_dp(demo) == -3
assert bad > 50, "答案位置写错应该在相当比例的用例上翻车"
print("✅ 五步齐全 + Kadane 对拍通过。第 ⑤ 步不是形式主义。")"""),

    md("""## 2 · 「状态定义错了后面全错」：打家劫舍的两种状态

同一道题（相邻两间不能同时偷，求最大值）有两种合法状态定义：

- **A**：`dp[i]` = 前 i 间房能偷到的最大值 → 答案 `dp[n]`
- **B**：`f[i]` = **必须偷第 i 间**时的最大值 → 答案 `max(f)`

两个都对。**但如果你用 B 的转移、A 的答案位置（`f[n-1]`），就会得到一个「大部分用例都对」的程序。**"""),

    code("""def rob_A(a):
    # ① dp[i] = 前 i 间的最大值   ⑤ 答案 dp[n]
    n = len(a)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        take = a[i - 1] + (dp[i - 2] if i >= 2 else 0)
        dp[i] = max(dp[i - 1], take)
    return dp[n], dp

def rob_B_correct(a):
    # ① f[i] = **必须偷第 i 间**时的最大值   ⑤ 答案 max(f)（外加"一间都不偷"=0）
    n = len(a)
    f = [0] * n
    for i in range(n):
        f[i] = a[i] + max([f[j] for j in range(i - 1)] + [0])   # j <= i-2
    return max(f + [0]), f

def rob_B_wrong(a):
    # 转移用 B，答案位置照抄 A —— 典型的"状态定义与答案位置不匹配"
    _, f = rob_B_correct(a)
    return (f[-1] if f else 0), f

def rob_brute(a):
    n, best = len(a), 0
    for mask in range(1 << n):
        if mask & (mask >> 1):            # 有相邻两位同时为 1 -> 非法
            continue
        best = max(best, sum(a[i] for i in range(n) if mask >> i & 1))
    return best

trap = [5, 1, 1, 5, 1]
gA, dpA = rob_A(trap)
gB, fB = rob_B_correct(trap)
gW, _ = rob_B_wrong(trap)
print(f"a = {trap}")
print(f"  A 的 dp 表 = {dpA}      -> 答案 dp[n] = {gA}")
print(f"  B 的 f  表 = {fB}       -> 答案 max(f) = {gB}   /  错取 f[n-1] = {gW}")
print(f"  暴力      = {rob_brute(trap)}")
assert gA == gB == rob_brute(trap) == 10
assert gW == 7, gW      # 最优方案在第 3 间结束，f[n-1] 看不到它

n_wrong = 0
for _ in range(400):
    a = [random.randint(0, 9) for _ in range(random.randint(1, 12))]
    ref = rob_brute(a)
    assert rob_A(a)[0] == ref and rob_B_correct(a)[0] == ref, a
    n_wrong += (rob_B_wrong(a)[0] != ref)
print(f"\\n错误版本在 {n_wrong}/400 个随机用例上出错 —— 也就是说约 {100*(1-n_wrong/400):.0f}% 的用例它是对的。")
print("✅ 这就是'状态定义错了后面全错'最阴险的地方：它不会在小用例上暴露。")
print("   诊断法：拿到错误答案先念状态定义那句话，再手算 dp[1]/dp[2] 核对，最后查答案位置。")"""),

    md("""## 3 · 双序列 DP：编辑距离、带状加速与 LCS

编辑距离的三个分支就是**删 / 插 / 替换**。它同时是 OCR / 标志文字识别的 **CER** 指标的定义
（`CER = 编辑距离 / 参考长度`）。这里实现三个版本：二维表、滚动数组、**带状 O(nk)**（真实评测库的做法）。"""),

    code("""def edit_distance(a, b):
    n, m = len(a), len(b)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i                       # ③ 全删
    for j in range(m + 1):
        D[0][j] = j                       # ③ 全插
    for i in range(1, n + 1):             # ④ 依赖 左 / 上 / 左上
        for j in range(1, m + 1):
            D[i][j] = min(D[i - 1][j] + 1,                       # 删 a[i-1]
                          D[i][j - 1] + 1,                       # 插 b[j-1]
                          D[i - 1][j - 1] + (a[i - 1] != b[j - 1]))  # 匹配/替换
    return D[n][m]

def edit_distance_rolling(a, b):
    # 空间压缩到 O(min(n,m))：只保留上一行
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[len(b)]

def edit_distance_banded(a, b, k):
    # 只算 |i-j| <= k 的带状区域；若真实距离 > k 则返回 k+1（"至少 k+1"）
    n, m = len(a), len(b)
    INF = k + 1
    if abs(n - m) > k:
        return INF
    prev = [INF] * (m + 1)
    for j in range(0, min(m, k) + 1):
        prev[j] = j
    for i in range(1, n + 1):
        cur = [INF] * (m + 1)
        if i <= k:
            cur[0] = i
        for j in range(max(1, i - k), min(m, i + k) + 1):
            cur[j] = min(INF, prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return min(prev[m], INF)

assert edit_distance("horse", "ros") == 3
assert edit_distance("intention", "execution") == 5
assert edit_distance("", "abc") == 3 and edit_distance("abc", "") == 3
assert edit_distance("abc", "abc") == 0

ALPHA = "abcd"
for _ in range(200):
    a = "".join(random.choice(ALPHA) for _ in range(random.randint(0, 9)))
    b = "".join(random.choice(ALPHA) for _ in range(random.randint(0, 9)))
    d = edit_distance(a, b)
    assert edit_distance_rolling(a, b) == d, (a, b)
    for k in (0, 1, 2, 3):
        assert min(edit_distance_banded(a, b, k), k + 1) == min(d, k + 1), (a, b, k)

# ── 用它算标志文字识别的 CER ──
def cer(ref, hyp):
    return edit_distance(ref, hyp) / max(1, len(ref))

pairs = [("限速120", "限速20"), ("限速60", "限速80"), ("前方施工", "前方施工"), ("禁止左转", "禁止右转")]
for r, h in pairs:
    print(f"  ref={r!r:>8}  hyp={h!r:>8}  编辑距离={edit_distance(r, h)}  CER={cer(r, h):.3f}")
assert abs(cer("限速120", "限速20") - 0.2) < 1e-12
assert cer("前方施工", "前方施工") == 0.0
print("✅ 编辑距离三版一致；带状版在 d<=k 时精确，是长序列 CER 的标准优化。")"""),

    code("""def lcs_table(a, b):
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    return L

def lcs_string(a, b):
    # 从表右下角回溯出一个具体方案 —— **空间压缩后就做不到这一步**
    L = lcs_table(a, b)
    i, j, out = len(a), len(b), []
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1]); i -= 1; j -= 1
        elif L[i - 1][j] >= L[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(reversed(out))

def is_subseq(s, t):
    it = iter(t)
    return all(c in it for c in s)

A, B = "ABCBDAB", "BDCABA"
s = lcs_string(A, B)
print(f"LCS('{A}', '{B}') = '{s}'  长度 {len(s)}  (表值 {lcs_table(A, B)[len(A)][len(B)]})")
assert len(s) == 4 and lcs_table(A, B)[len(A)][len(B)] == 4
assert is_subseq(s, A) and is_subseq(s, B)

def lcs_brute(a, b):
    best = 0
    for mask in range(1 << len(a)):
        sub = "".join(a[i] for i in range(len(a)) if mask >> i & 1)
        if is_subseq(sub, b):
            best = max(best, len(sub))
    return best

for _ in range(150):
    a = "".join(random.choice("abc") for _ in range(random.randint(0, 8)))
    b = "".join(random.choice("abc") for _ in range(random.randint(0, 8)))
    got = lcs_table(a, b)[len(a)][len(b)]
    assert got == lcs_brute(a, b), (a, b)
    r = lcs_string(a, b)
    assert len(r) == got and is_subseq(r, a) and is_subseq(r, b)
print("✅ LCS 表值与暴力一致，且回溯出的串确实是两者的公共子序列。")
print("   记住：回溯需要完整的二维表 —— 这就是空间压缩的代价。")"""),

    md("""## 4 · 背包：同一份代码，方向一反就是另一道题

`dp[c]` = 容量 c 下的最大价值。一维压缩后：

- **容量倒序** → 读到的 `dp[c-w]` 还是「上一行」的值 → 每件最多取 1 件 → **01 背包**
- **容量正序** → 读到的 `dp[c-w]` 已被本轮更新 → 同一件可重复取 → **完全背包**"""),

    code("""def knap01_2d(w, v, C):
    n = len(w)
    dp = [[0] * (C + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for c in range(C + 1):
            dp[i][c] = dp[i - 1][c]
            if c >= w[i - 1]:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w[i - 1]] + v[i - 1])
    return dp[n][C]

def knap_1d(w, v, C, reverse=True):
    # reverse=True -> 01 背包；reverse=False -> 完全背包。**只有这一行的差别**
    dp = [0] * (C + 1)
    for wi, vi in zip(w, v):
        rng_c = range(C, wi - 1, -1) if reverse else range(wi, C + 1)
        for c in rng_c:
            dp[c] = max(dp[c], dp[c - wi] + vi)
    return dp[C]

def knap01_brute(w, v, C):
    n, best = len(w), 0
    for mask in range(1 << n):
        tw = sum(w[i] for i in range(n) if mask >> i & 1)
        if tw <= C:
            best = max(best, sum(v[i] for i in range(n) if mask >> i & 1))
    return best

W, V, C = [2, 3, 4], [3, 4, 6], 8
print(f"w={W} v={V} C={C}")
print(f"  01 背包  二维={knap01_2d(W, V, C)}  一维倒序={knap_1d(W, V, C, True)}  暴力={knap01_brute(W, V, C)}")
print(f"  完全背包 一维正序={knap_1d(W, V, C, False)}   (4 号物品拿两件: w=8, v=12)")
assert knap01_2d(W, V, C) == knap_1d(W, V, C, True) == knap01_brute(W, V, C) == 10
assert knap_1d(W, V, C, False) == 12

for _ in range(200):
    n = random.randint(1, 9)
    w = [random.randint(1, 7) for _ in range(n)]
    v = [random.randint(1, 20) for _ in range(n)]
    C = random.randint(0, 20)
    ref = knap01_brute(w, v, C)
    assert knap01_2d(w, v, C) == ref, (w, v, C)
    assert knap_1d(w, v, C, True) == ref, (w, v, C)
    assert knap_1d(w, v, C, False) >= ref            # 完全背包只会更大或相等
print("✅ 一维倒序 == 二维 == 暴力；正序则严格变成了完全背包。方向不是风格问题。")

# ── 工程化的用法：延迟预算下的模块配置选择（分组背包）──
BUDGET_TENTH_MS = 120                                   # 12.0 ms，量化到 0.1 ms
GROUPS = {                                              # 模块 -> [(名称, 延迟(0.1ms), AP 增益)]
    "detector": [("tiny", 35, 6.0), ("small", 55, 8.4), ("medium", 80, 9.6)],
    "tracker":  [("iou", 5, 0.8), ("kalman", 12, 1.4), ("bytetrack", 22, 1.9)],
    "classifier": [("none", 0, 0.0), ("cls-64", 18, 2.2), ("cls-128", 34, 3.1)],
}

def group_knapsack(groups, budget):
    NEG = -1e18
    dp = [NEG] * (budget + 1); dp[0] = 0.0
    pick = [[None] * (budget + 1) for _ in range(len(groups))]
    for gi, (gname, items) in enumerate(groups.items()):
        nd = [NEG] * (budget + 1)
        for c in range(budget + 1):
            for name, cost, gain in items:
                if cost <= c and dp[c - cost] > NEG / 2 and dp[c - cost] + gain > nd[c]:
                    nd[c] = dp[c - cost] + gain
                    pick[gi][c] = (name, cost)
        dp = nd
    best_c = max(range(budget + 1), key=lambda c: dp[c])
    plan, c = [], best_c
    for gi in range(len(groups) - 1, -1, -1):
        name, cost = pick[gi][c]
        plan.append((list(groups)[gi], name, cost / 10))
        c -= cost
    return dp[best_c], best_c / 10, list(reversed(plan))

gain, used, plan = group_knapsack(GROUPS, BUDGET_TENTH_MS)
print(f"\\n预算 {BUDGET_TENTH_MS/10} ms -> 最优组合 AP 增益 {gain:.1f}，实际用掉 {used} ms")
for g, name, cost in plan:
    print(f"    {g:<11s} {name:<9s} {cost:.1f} ms")
assert used <= BUDGET_TENTH_MS / 10 + 1e-9
assert abs(gain - 13.7) < 1e-6, gain          # medium(8.0ms,9.6) + bytetrack(2.2,1.9) + cls-64(1.8,2.2)
print("✅ 「算力预算下选方案」= 分组背包。C57-05 / C63-04 的排序问题都是这个形状。")"""),

    code("""# ── 初始化陷阱：「恰好装满」必须用 inf，不能用 0 ──
def coin_min(coins, amount):
    INF = math.inf
    dp = [INF] * (amount + 1)
    dp[0] = 0                                   # ③ 只有 0 是天然可达的
    for c in range(1, amount + 1):
        for coin in coins:
            if coin <= c and dp[c - coin] + 1 < dp[c]:
                dp[c] = dp[c - coin] + 1
    return -1 if dp[amount] == INF else dp[amount]

def coin_min_zero_init(coins, amount):
    dp = [0] * (amount + 1)                     # ← 把不可达状态填成 0
    for c in range(1, amount + 1):
        for coin in coins:
            if coin <= c:
                dp[c] = min(dp[c], dp[c - coin] + 1)
    return dp[amount]

print("coins=[1,3,4]  amount=6 ->", coin_min([1, 3, 4], 6), "(3+3)")
print("coins=[2]      amount=3 ->", coin_min([2], 3), "(不可达)")
print("coins=[2]      amount=3 -> 0 初始化版本给出", coin_min_zero_init([2], 3), "  ← 谎报可行")
assert coin_min([1, 3, 4], 6) == 2
assert coin_min([1, 5, 10, 25], 63) == 6        # 25+25+10+1+1+1
assert coin_min([2], 3) == -1
assert coin_min_zero_init([2], 3) == 0          # 全 0 初始化 => 恒返回 0，错得毫无征兆
print("✅ 求 min 时不可达 = +inf，求 max 时 = -inf。填 0 等于宣称『存在一个代价 0 的方案』。")"""),

    md("""## 5 · LIS：O(n²) 与 O(n log n) 对拍，以及 `tails` 的真相

`tails[k]` = **所有长度为 k+1 的上升子序列中最小的那个结尾值**。
它单调递增所以能二分，但**它的内容不是任何一个真实的 LIS**——只有长度是对的。
这是这道题面试中最经典的误解。"""),

    code("""def lis_n2(a):
    if not a:
        return 0
    dp = [1] * len(a)                       # ① dp[i] = **以 i 结尾**的 LIS 长度
    for i in range(len(a)):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)                          # ⑤ 答案是 max(dp)

def lis_nlogn(a, return_tails=False):
    tails = []
    for x in a:
        i = bisect.bisect_left(tails, x)    # 严格上升用 bisect_left
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x                    # 用更小的结尾替换，为将来留余地
    return (len(tails), tails) if return_tails else len(tails)

for _ in range(300):
    a = [random.randint(0, 15) for _ in range(random.randint(0, 14))]
    assert lis_n2(a) == lis_nlogn(a), a
print("O(n^2) 与 O(n log n) 在 300 个随机数组上完全一致")

a = [1, 3, 5, 2]
L, tails = lis_nlogn(a, return_tails=True)
print(f"\\na = {a}   LIS 长度 = {L}   tails = {tails}")
assert tails == [1, 2, 5] and L == 3
assert not is_subseq(tails, a), "本例中 tails 恰恰不是 a 的子序列"
print(f"  tails={tails} 在 a 里？ {is_subseq(tails, a)}   ← 5 出现在 2 之前，tails 不是合法子序列")
print("  真实的一个 LIS 是 [1,3,5]。要还原具体序列必须额外记录前驱下标。")

# 计时对比：n 大时 O(n^2) 会明显吃亏
for n in (400, 1600):
    big = [random.randint(0, 10**6) for _ in range(n)]
    t0 = time.perf_counter(); r1 = lis_n2(big);   t1 = time.perf_counter()
    r2 = lis_nlogn(big);                          t2 = time.perf_counter()
    assert r1 == r2
    print(f"  n={n:>5d}  O(n^2) {1e3*(t1-t0):7.2f} ms   O(n log n) {1e3*(t2-t1):7.2f} ms")
print("✅ 面试里先写 O(n^2) 保证正确，再说 O(n log n) 的 tails 语义 —— 顺序别反。")"""),

    md("""## 6 · 记忆化搜索 ↔ 递推：先写能跑的那一版

同一道 01 背包，两种写法。**记忆化把「遍历顺序」这一步免掉了**，代价是常数与栈深度。"""),

    code("""def knap_memo(w, v, C):
    w, v = tuple(w), tuple(v)

    @lru_cache(maxsize=None)
    def f(i, c):                     # f(i,c) = 只考虑前 i 件、容量 c 时的最大价值
        if i == 0 or c == 0:
            return 0
        best = f(i - 1, c)                                  # 不选第 i 件
        if w[i - 1] <= c:
            best = max(best, f(i - 1, c - w[i - 1]) + v[i - 1])   # 选第 i 件
        return best

    r = f(len(w), C)
    return r, f.cache_info()

n = 60
W = [25 * random.randint(1, 12) for _ in range(n)]   # 延迟以 25 微秒为量化单位 -> 状态空间稀疏
V = [random.randint(1, 100) for _ in range(n)]
CAP = 750

t0 = time.perf_counter(); r_memo, info = knap_memo(W, V, CAP); t1 = time.perf_counter()
r_tab = knap_1d(W, V, CAP, True);                              t2 = time.perf_counter()
print(f"记忆化搜索 = {r_memo}   耗时 {1e3*(t1-t0):.1f} ms   缓存命中/未命中 = {info.hits}/{info.misses}")
print(f"自底向上   = {r_tab}   耗时 {1e3*(t2-t1):.1f} ms")
assert r_memo == r_tab
full_table = (n + 1) * (CAP + 1)
print(f"完整状态表 {full_table} 格，记忆化只算了 {info.misses} 格（{info.misses/full_table:.1%}）"
      " ← 稀疏状态空间正是记忆化的优势")
assert info.misses < full_table, "记忆化应当只触及可达状态"
print()
print("互转口诀:  函数参数 -> 数组下标 | 递归调用 -> 读更早的元素 | 边界 -> 初始化 | (递归不用想) -> 遍历顺序")
print("注意: Python 默认递归深度 1000，链式依赖的题（如 n=1e4 的 LIS）用记忆化会 RecursionError。")
print("✅ 面试策略：暴力递归 -> 加 @lru_cache -> （口头）改递推 + 压缩空间。")"""),

    md("""## 7 · 贪心：交换论证的数值验证，和一个「看起来对但错」的反例

区间调度里三种「看起来都合理」的排序键：**最早结束 / 最早开始 / 最短区间**。
只有第一种能通过交换论证，另外两种在随机用例上会被打脸。"""),

    code("""def overlap(a, b):
    # 半开区间 [s,e)：接触不算冲突
    return min(a[1], b[1]) - max(a[0], b[0]) > 0

def schedule_greedy(iv, key):
    keep = []
    for i in sorted(range(len(iv)), key=lambda i: key(iv[i])):
        if all(not overlap(iv[i], iv[j]) for j in keep):
            keep.append(i)
    return sorted(keep)

def schedule_brute(iv):
    n, best = len(iv), []
    for mask in range(1 << n):
        sel = [i for i in range(n) if mask >> i & 1]
        if all(not overlap(iv[a], iv[b]) for a in sel for b in sel if a < b):
            if len(sel) > len(best):
                best = sel
    return best

KEYS = {
    "最早结束 (正确)": lambda x: x[1],
    "最早开始":        lambda x: x[0],
    "最短区间":        lambda x: x[1] - x[0],
}
fails = {k: 0 for k in KEYS}
for _ in range(400):
    n = random.randint(1, 9)
    iv = []
    for _ in range(n):
        s = random.randint(0, 20); iv.append((s, s + random.randint(1, 8)))
    opt = len(schedule_brute(iv))
    for k, f in KEYS.items():
        if len(schedule_greedy(iv, f)) != opt:
            fails[k] += 1
for k, c in fails.items():
    print(f"  {k:<16s} 在 400 组随机用例中失手 {c} 次")
assert fails["最早结束 (正确)"] == 0, "最早结束贪心必须永远最优（交换论证）"
assert fails["最早开始"] > 0 and fails["最短区间"] > 0
print()
print("交换论证（最早结束）: 设最优解 O 与贪心解 G 第一次在第 k 步不同，g_k 的结束时间 e <= o_k 的 e'，")
print("  把 o_k 换成 g_k 后，O 的第 k+1 个区间起点 >= e' >= e，仍不冲突，个数不变 => O' 同样最优。")
demo = [(0, 10), (1, 2), (3, 4)]
print(f"\\n最早开始的反例: {demo} -> 它选 {schedule_greedy(demo, KEYS['最早开始'])}，最优是 {schedule_brute(demo)}")
demo2 = [(0, 4), (3, 5), (4, 8)]
print(f"最短区间的反例: {demo2} -> 它选 {schedule_greedy(demo2, KEYS['最短区间'])}，最优是 {schedule_brute(demo2)}")
assert len(schedule_greedy(demo, KEYS["最早开始"])) == 1 and len(schedule_brute(demo)) == 2
assert len(schedule_greedy(demo2, KEYS["最短区间"])) == 1 and len(schedule_brute(demo2)) == 2
print("✅ 「排序键」选错，贪心就错。能证明的只有最早结束这一个。")"""),

    code("""# ── 找零：贪心在某些面值系上正确，在另一些上错 —— 而反例往往不在最小的用例里 ──
def coin_greedy(coins, amount):
    left, cnt = amount, 0
    for c in sorted(coins, reverse=True):
        take = left // c
        cnt += take; left -= take * c
    return cnt if left == 0 else -1

def scan_counterexamples(coins, hi=40):
    out = []
    for amt in range(1, hi + 1):
        g, d = coin_greedy(coins, amt), coin_min(coins, amt)
        if d != -1 and (g == -1 or g > d):
            out.append((amt, g, d))
    return out

for coins in ([1, 3, 4], [1, 15, 25], [1, 5, 10, 25], [1, 5, 10, 20, 50, 100]):
    ce = scan_counterexamples(coins, 40)
    head = ce[:4]
    print(f"  面值 {str(coins):<26s} 反例数 {len(ce):>2d}  前几个 (金额, 贪心, 最优): {head}")

ce134 = scan_counterexamples([1, 3, 4], 40)
assert (6, 3, 2) in ce134, ce134[:5]
assert coin_greedy([1, 3, 4], 5) == coin_min([1, 3, 4], 5) == 2, "amount=5 上贪心恰好对 —— 这就是陷阱"
assert scan_counterexamples([1, 5, 10, 25], 100) == []
assert scan_counterexamples([1, 5, 10, 20, 50, 100], 200) == []
print()
print("陷阱演示: amount=5 时贪心 4+1=2 枚 == 最优；amount=6 时贪心 4+1+1=3 枚 > 最优 3+3=2 枚。")
print("✅ 只手测一两个小用例就宣称『贪心可以』，是面试里最常见的失分方式。")"""),

    md("""## 8 · 亮点实验：NMS = 加权区间调度的贪心近似

一维场景（龙门架上并排的标志）里，把检测框看成区间、score 看成权重、IoU 阈值取 0，于是：

| | NMS | 加权区间调度 |
|---|---|---|
| 约束 | 保留的框两两不重叠 | 选中的区间两两不重叠 |
| 算法 | 按分数降序，能留就留（**贪心**） | 按结束时间排序 + **DP** |
| 最优性 | 无保证 | 精确最优 |

`OPT(j) = max(OPT(j-1), w_j + OPT(p(j)))`，其中 `p(j)` = 最大的 `i<j` 使 `end_i <= start_j`。"""),

    code("""def greedy_nms_1d(iv, w):
    # 标准贪心 NMS（IoU 阈值 = 0：任何重叠都抑制）
    keep = []
    for i in sorted(range(len(iv)), key=lambda i: -w[i]):
        if all(not overlap(iv[i], iv[j]) for j in keep):
            keep.append(i)
    return sorted(keep)

def weighted_interval_scheduling(iv, w):
    # 返回 (最优总权重, 选中的原始下标列表)
    n = len(iv)
    if n == 0:
        return 0.0, []
    idx = sorted(range(n), key=lambda i: iv[i][1])       # 按结束时间升序
    ends = [iv[i][1] for i in idx]
    p = [bisect.bisect_right(ends, iv[idx[k]][0], 0, k) for k in range(n)]
    OPT = [0.0] * (n + 1)
    take_it = [False] * (n + 1)
    for k in range(1, n + 1):
        take = w[idx[k - 1]] + OPT[p[k - 1]]
        if take > OPT[k - 1] + 1e-12:
            OPT[k], take_it[k] = take, True
        else:
            OPT[k] = OPT[k - 1]
    sel, k = [], n
    while k > 0:
        if take_it[k]:
            sel.append(idx[k - 1]); k = p[k - 1]
        else:
            k -= 1
    return OPT[n], sorted(sel)

# ── 教科书级的三框反例：一个大框 vs 两个小框 ──
IV = [(0, 10), (0, 4), (6, 10)]
WT = [10.0, 6.0, 6.0]
g = greedy_nms_1d(IV, WT); gw = sum(WT[i] for i in g)
ow, o = weighted_interval_scheduling(IV, WT)
print("      A ████████████████████  w=10")
print("      B █████                 w=6")
print("      C           ██████      w=6")
print(f"\\n贪心 NMS 保留 {['ABC'[i] for i in g]}  总分 {gw}")
print(f"DP  最优 保留 {['ABC'[i] for i in o]}  总分 {ow}")
print(f"贪心 / 最优 = {gw/ow:.4f}")
assert g == [0] and gw == 10.0
assert o == [1, 2] and ow == 12.0
assert abs(gw / ow - 10 / 12) < 1e-12

# ── DP 的正确性：与暴力枚举对拍 ──
def wis_brute(iv, w):
    n, best = len(iv), 0.0
    for mask in range(1 << n):
        sel = [i for i in range(n) if mask >> i & 1]
        if all(not overlap(iv[a], iv[b]) for a in sel for b in sel if a < b):
            best = max(best, sum(w[i] for i in sel))
    return best

for _ in range(300):
    n = random.randint(0, 10)
    iv, w = [], []
    for _ in range(n):
        s = random.randint(0, 30); iv.append((s, s + random.randint(1, 9)))
        w.append(round(random.uniform(0.1, 1.0), 3))
    ow2, sel = weighted_interval_scheduling(iv, w)
    assert abs(ow2 - wis_brute(iv, w)) < 1e-9, (iv, w)
    assert all(not overlap(iv[a], iv[b]) for a in sel for b in sel if a < b)
    assert abs(sum(w[i] for i in sel) - ow2) < 1e-9
print("✅ 加权区间调度 DP 与暴力枚举在 300 组随机用例上完全一致（且方案确实互不重叠）。")"""),

    code("""# ── 贪心到底能差多少？答案：可以任意差 ──
def adversarial(k, eps=0.01):
    # 一个覆盖 k 块牌子的大框（权重 1+eps） + k 个正确的小框（权重各 1）
    iv = [(0.0, float(k))] + [(float(i), float(i + 1)) for i in range(k)]
    w = [1.0 + eps] + [1.0] * k
    return iv, w

print("最坏情况族：一个略高分的大框 vs k 个正确的小框")
print(f"{'k':>4s} {'贪心':>8s} {'最优':>8s} {'比值':>8s}")
ratios = []
for k in (2, 5, 10, 50, 200):
    iv, w = adversarial(k)
    gw = sum(w[i] for i in greedy_nms_1d(iv, w))
    ow, _ = weighted_interval_scheduling(iv, w)
    ratios.append(gw / ow)
    print(f"{k:>4d} {gw:>8.2f} {ow:>8.2f} {gw/ow:>8.4f}")
assert all(ratios[i] > ratios[i + 1] for i in range(len(ratios) - 1))
assert ratios[-1] < 0.01, "k=200 时比值应趋于 0 —— 贪心近似比无常数下界"
print("=> 贪心 NMS 的近似比**没有常数下界**，不是『差一点点』。")

# ── 随机场景上的统计：平均很好，但确实存在次优 ──
def random_scene(n, rng):
    s = rng.uniform(0, 100, size=n)
    e = s + rng.uniform(2, 18, size=n)
    w = rng.uniform(0.1, 1.0, size=n)
    return list(zip(s.tolist(), e.tolist())), w.tolist()

rs = np.random.default_rng(7)
rr, n_sub = [], 0
for _ in range(400):
    iv, w = random_scene(rs.integers(4, 16), rs)
    gw = sum(w[i] for i in greedy_nms_1d(iv, w))
    ow, _ = weighted_interval_scheduling(iv, w)
    rr.append(gw / ow)
    n_sub += (gw < ow - 1e-9)
rr = np.array(rr)
print(f"\\n随机场景 400 组: 平均比值 {rr.mean():.4f}  最差 {rr.min():.4f}  "
      f"5% 分位 {np.percentile(rr,5):.4f}  贪心次优的比例 {n_sub/400:.1%}")
assert 0 < n_sub < 400
assert rr.mean() > 0.85 and rr.min() < 1.0
print("✅ 平均场景下贪心很接近最优，**但最坏情况恰好发生在密集排列的标志上** —— 而那正是 TSR 最在意的场景。")"""),

    code("""# ── 真实失效模式：一个"合并框"吃掉两块相邻的牌子 ──
def iou_1d(a, b):
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0

def build_gantry(n_pairs=4):
    # 每对: 两块相邻的牌子 + 各自的正确框 + 一个跨越两者的"合并"误检（分数略高）
    gts, iv, w, tag = [], [], [], []
    for t in range(n_pairs):
        b = 100.0 * t
        g1, g2 = (b, b + 10), (b + 14, b + 24)
        gts += [g1, g2]
        iv += [g1, g2, (b, b + 24)]
        w += [0.60, 0.55, 0.63]
        tag += ["正确框1", "正确框2", "合并误检"]
    return gts, iv, w, tag

def recall_at(gts, iv, keep, thr=0.5):
    hit = sum(any(iou_1d(g, iv[i]) >= thr for i in keep) for g in gts)
    return hit / len(gts)

gts, iv, w, tag = build_gantry(4)
kg = greedy_nms_1d(iv, w)
ow, ko = weighted_interval_scheduling(iv, w)
gw = sum(w[i] for i in kg)
print(f"场景: {len(gts)} 块牌子, {len(iv)} 个候选框（每对牌子附带一个跨越两者的合并误检 score=0.63）")
print(f"  贪心 NMS 保留 {len(kg)} 个: {sorted(set(tag[i] for i in kg))}   总分 {gw:.2f}   召回 {recall_at(gts,iv,kg):.0%}")
print(f"  DP  最优 保留 {len(ko)} 个: {sorted(set(tag[i] for i in ko))}   总分 {ow:.2f}   召回 {recall_at(gts,iv,ko):.0%}")
print(f"  合并框与单块牌子的 IoU = {iou_1d((0,24),(0,10)):.4f} < 0.5 -> 它一个牌子都算不上检出")
assert recall_at(gts, iv, kg) == 0.0 and recall_at(gts, iv, ko) == 1.0
assert abs(gw - 4 * 0.63) < 1e-9 and abs(ow - 4 * 1.15) < 1e-9
assert all(tag[i] == "合并误检" for i in kg)
print("✅ 贪心 NMS 的失效模式可以被精确刻画：**高分框独吞一片区域**。")
print("   这正是 Soft-NMS（衰减而非删除）、WBF（融合而非择一）、")
print("   以及 DETR/YOLOv10 的一对一分配（训练期就去重）想解决的同一个问题。")"""),

    code("""# ── 那为什么工业界不换成 DP？因为二维情形下问题变成 NP-hard ──
def iou_2d(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def nms_2d(boxes, scores, thr=0.5):
    keep = []
    for i in sorted(range(len(boxes)), key=lambda i: -scores[i]):
        if all(iou_2d(boxes[i], boxes[j]) <= thr for j in keep):
            keep.append(i)
    return sorted(keep)

def mwis_brute_2d(boxes, scores, thr=0.5):
    # 冲突图上的最大权独立集：**只能枚举 2^n**
    n = len(boxes)
    adj = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            if iou_2d(boxes[i], boxes[j]) > thr:
                adj[i] |= 1 << j; adj[j] |= 1 << i
    best, bmask = 0.0, 0
    for mask in range(1 << n):
        ok, m = True, mask
        while m:
            i = (m & -m).bit_length() - 1
            if adj[i] & mask:
                ok = False; break
            m &= m - 1
        if ok:
            s = sum(scores[i] for i in range(n) if mask >> i & 1)
            if s > best:
                best, bmask = s, mask
    return best, sorted(i for i in range(n) if bmask >> i & 1)

r2 = np.random.default_rng(11)
worse, tot = 0, 0
for _ in range(60):
    n = int(r2.integers(6, 13))
    cx, cy = r2.uniform(0, 40, n), r2.uniform(0, 40, n)
    ww, hh = r2.uniform(8, 26, n), r2.uniform(8, 26, n)
    boxes = [(cx[i] - ww[i] / 2, cy[i] - hh[i] / 2, cx[i] + ww[i] / 2, cy[i] + hh[i] / 2) for i in range(n)]
    sc = r2.uniform(0.1, 1.0, n).tolist()
    g = sum(sc[i] for i in nms_2d(boxes, sc))
    o, _ = mwis_brute_2d(boxes, sc)
    assert o >= g - 1e-9, "暴力最优不可能比贪心差"
    worse += (g < o - 1e-9); tot += 1
print(f"二维随机场景 {tot} 组：贪心 NMS 严格次优的比例 {worse/tot:.0%}")

print("\\n暴力 MWIS 的耗时随 n 指数增长:")
for n in (10, 13, 16):
    cx, cy = r2.uniform(0, 60, n), r2.uniform(0, 60, n)
    boxes = [(cx[i] - 10, cy[i] - 10, cx[i] + 10, cy[i] + 10) for i in range(n)]
    sc = r2.uniform(0.1, 1.0, n).tolist()
    t0 = time.perf_counter(); mwis_brute_2d(boxes, sc); dt = time.perf_counter() - t0
    print(f"  n={n:>3d}  2^n={2**n:>8d}  {1e3*dt:8.1f} ms")
print("  一帧检测器输出常有 N=1000+ 个过阈框 -> 2^1000 完全不可行。")
print("✅ 结论：**一维退化情形可以 DP 求最优；二维是 NP-hard，只能贪心 + 工程补丁。**")
print("   面试标准答案：『NMS 是最大权独立集的贪心近似；我可以在一维情形下用 DP 求最优并量化 gap，")
print("   但二维不可行，工程上的解法是 Soft-NMS / WBF / 一对一标签分配。』")"""),

    md("""## ✏️ 练习 1：最长公共子序列（高频 · 必会 · 15 行以内）

实现 `lcs_length(a, b)`，返回两个字符串的 LCS 长度。

**动手前先把五步说出来**：
① `L[i][j]` = a 前 i 个与 b 前 j 个的 LCS 长度；② 相等则 `L[i-1][j-1]+1`，否则 `max(L[i-1][j], L[i][j-1])`；
③ `L[0][*]=L[*][0]=0`；④ i、j 都从小到大；⑤ 答案 `L[n][m]`。"""),

    code("""def lcs_length(a, b):
    # TODO: 二维 DP，返回 LCS 长度
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert lcs_length("ABCBDAB", "BDCABA") == 4
assert lcs_length("abcde", "ace") == 3
assert lcs_length("abc", "") == 0 and lcs_length("", "") == 0
assert lcs_length("abc", "def") == 0
assert lcs_length("aaa", "aa") == 2
for _ in range(200):
    a = "".join(random.choice("abc") for _ in range(random.randint(0, 8)))
    b = "".join(random.choice("abc") for _ in range(random.randint(0, 8)))
    assert lcs_length(a, b) == lcs_brute(a, b), (a, b)
print("✅ 练习 1 通过：与暴力枚举在 200 组随机串上一致。")
print("   面试加分句：『空间可压到 O(min(n,m))，但那样就回溯不出具体的公共子序列了。』")"""),

    md("""## ✏️ 练习 2：01 背包的一维空间压缩（高频 · 必会）

实现 `knapsack01_1d(weights, values, C)`，**必须用一维数组**，返回最大价值。

**考点只有一个：遍历容量的方向。**方向反了就变成完全背包，而自测会当场抓住你。"""),

    code("""def knapsack01_1d(weights, values, C):
    # TODO: dp = [0]*(C+1)，对每件物品遍历容量 —— 方向？
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
assert knapsack01_1d([2, 3, 4], [3, 4, 6], 8) == 10
assert knapsack01_1d([], [], 10) == 0
assert knapsack01_1d([5], [9], 4) == 0            # 装不下
assert knapsack01_1d([5], [9], 5) == 9
# 关键：必须**严格不等于**完全背包的答案，否则说明方向写反了
assert knapsack01_1d([2, 3, 4], [3, 4, 6], 8) != knap_1d([2, 3, 4], [3, 4, 6], 8, reverse=False)
for _ in range(200):
    n = random.randint(0, 9)
    w = [random.randint(1, 7) for _ in range(n)]
    v = [random.randint(1, 20) for _ in range(n)]
    C = random.randint(0, 20)
    assert knapsack01_1d(w, v, C) == knap01_brute(w, v, C), (w, v, C)
print("✅ 练习 2 通过：一维压缩 + 容量倒序 == 二维 == 暴力。")
print("   面试加分句：『倒序是因为 dp[c-w] 必须还是上一行的值——否则同一件物品会被重复选。』")"""),

    md("""## ✏️ 练习 3：加权区间调度 DP（低频 · 加分 · 本模块的核心）

实现 `weighted_interval_dp(intervals, weights)`，返回**最优总权重**（float）。

区间是半开的 `[s, e)`，接触不算重叠。提示：按结束时间排序 → 用二分求 `p(j)` → `OPT(j)=max(OPT(j-1), w_j+OPT(p(j)))`。"""),

    code("""def weighted_interval_dp(intervals, weights):
    # TODO: 返回最大总权重（不需要返回方案）
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert abs(weighted_interval_dp([(0, 10), (0, 4), (6, 10)], [10.0, 6.0, 6.0]) - 12.0) < 1e-9
assert weighted_interval_dp([], []) == 0
assert abs(weighted_interval_dp([(0, 5)], [3.0]) - 3.0) < 1e-9
assert abs(weighted_interval_dp([(0, 5), (5, 10)], [1.0, 2.0]) - 3.0) < 1e-9   # 半开区间：接触不冲突
assert abs(weighted_interval_dp([(0, 5), (4, 10)], [1.0, 2.0]) - 2.0) < 1e-9   # 真重叠：只能取一个
for _ in range(300):
    n = random.randint(0, 10)
    iv, w = [], []
    for _ in range(n):
        s = random.randint(0, 30); iv.append((s, s + random.randint(1, 9)))
        w.append(round(random.uniform(0.1, 1.0), 3))
    assert abs(weighted_interval_dp(iv, w) - wis_brute(iv, w)) < 1e-9, (iv, w)
print("✅ 练习 3 通过：与 2^n 暴力枚举在 300 组随机用例上一致。")
print("   面试加分句：『p(j) 用二分求，所以总复杂度是排序主导的 O(n log n)。』")"""),

    md("""## ✏️ 练习 4：量化贪心 NMS 的次优程度

实现 `greedy_gap(intervals, weights)`，返回 `(greedy_total, opt_total, ratio)`：

- `greedy_total`：贪心 NMS（按权重降序，能留就留）保留下来的总权重
- `opt_total`：加权区间调度 DP 的最优总权重
- `ratio`：`greedy_total / opt_total`（`opt_total == 0` 时返回 `1.0`）

可以直接复用前面的 `greedy_nms_1d` 与你在练习 3 写的 `weighted_interval_dp`。"""),

    code("""def greedy_gap(intervals, weights):
    # TODO: 返回 (greedy_total, opt_total, ratio)
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
g, o, r = greedy_gap([(0, 10), (0, 4), (6, 10)], [10.0, 6.0, 6.0])
assert abs(g - 10.0) < 1e-9 and abs(o - 12.0) < 1e-9 and abs(r - 10 / 12) < 1e-9
assert greedy_gap([], []) == (0, 0, 1.0) or abs(greedy_gap([], [])[2] - 1.0) < 1e-12
iv_a, w_a = adversarial(10)
g, o, r = greedy_gap(iv_a, w_a)
assert abs(g - 1.01) < 1e-9 and abs(o - 10.0) < 1e-9 and r < 0.11, (g, o, r)
# 贪心永远不会优于最优；随机场景下平均很接近 1 但确实存在次优
rr4 = np.random.default_rng(23)
vals, sub = [], 0
for _ in range(300):
    iv, w = random_scene(int(rr4.integers(4, 16)), rr4)
    g, o, r = greedy_gap(iv, w)
    assert r <= 1.0 + 1e-9, r
    vals.append(r); sub += (r < 1 - 1e-9)
print(f"随机 300 组：平均比值 {np.mean(vals):.4f}  最差 {min(vals):.4f}  次优比例 {sub/300:.1%}")
assert 0 < sub < 300 and np.mean(vals) > 0.85
print("✅ 练习 4 通过：贪心 NMS 的 gap 是可以被量化的，而它的最坏情形没有常数下界。")"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def lcs_length(a, b):
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]          # ③ 边界天然是 0
    for i in range(1, n + 1):                          # ④ 依赖 左 / 上 / 左上
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1          # ② 配上了
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])  # ② 丢掉 a 的最后一个 或 b 的最后一个
    return L[n][m]                                     # ⑤"""),

    code("""# 练习 2 参考答案
def knapsack01_1d(weights, values, C):
    dp = [0] * (C + 1)
    for wi, vi in zip(weights, values):
        for c in range(C, wi - 1, -1):     # **倒序**：保证 dp[c-wi] 还是"没考虑本件"的值
            dp[c] = max(dp[c], dp[c - wi] + vi)
    return dp[C]"""),

    code("""# 练习 3 参考答案
def weighted_interval_dp(intervals, weights):
    n = len(intervals)
    if n == 0:
        return 0
    idx = sorted(range(n), key=lambda i: intervals[i][1])       # 按结束时间升序
    ends = [intervals[i][1] for i in idx]
    OPT = [0.0] * (n + 1)
    for k in range(1, n + 1):
        s = intervals[idx[k - 1]][0]
        p = bisect.bisect_right(ends, s, 0, k - 1)              # 最后一个 end <= s 的位置数
        OPT[k] = max(OPT[k - 1], weights[idx[k - 1]] + OPT[p])
    return OPT[n]"""),

    code("""# 练习 4 参考答案
def greedy_gap(intervals, weights):
    g = sum(weights[i] for i in greedy_nms_1d(intervals, weights))
    o = weighted_interval_dp(intervals, weights)
    return g, o, (g / o if o > 0 else 1.0)"""),

    md("""---
## 🧪 真实工程胶囊：把工程问题归约到 DP / 贪心的检查单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 白板上的 DP 五步（每一步都要出声说）
# ══════════════════════════════════════════════════════════════════════
# ① 状态定义  "dp[i] 表示 ___"          <- 必须含「以 i 结尾」或「前 i 个」这类限定词
# ② 转移方程  枚举"最后一步的决策"，每个决策一个分支
# ③ 初始化    不可达用 -inf(求 max) / +inf(求 min)，**不要填 0**
# ④ 遍历顺序  画依赖箭头；一维压缩时：01 背包倒序、完全背包正序、区间 DP 按长度
# ⑤ 答案位置  dp[n] ? max(dp) ? dp[n][m] ?  <- 把①那句话代入题目问句读一遍
#
# 卡住时的脱困路径（说出来就得分）：
#   暴力递归（保证语义对） -> @lru_cache（变成 DP） -> 递推 + 空间压缩（如果还有时间）

# ══════════════════════════════════════════════════════════════════════
# B. 贪心：要么证明，要么反例，不许说"我觉得"
# ══════════════════════════════════════════════════════════════════════
# 交换论证模板：
#   设最优解 O 与贪心解 G 在第 k 步第一次不同（前 k-1 步相同）
#   把 O 的第 k 步换成 G 的第 k 步得到 O'
#   证明 O' 仍合法 且 目标值不下降  =>  G 也最优
# 如果第 3 步走不通（换完不合法/更差），这本身就是"贪心不对"的强信号 -> 改 DP
# 反例构造清单（60 秒内试完）：
#   · 一个大项 vs 多个小项（找零 [1,3,4] 凑 6；加权区间调度）
#   · 局部最优挤掉后续机会（区间调度按最早开始 / 最短区间排序）
#   · 边界：空 / 单元素 / 全相同 / 恰好等于阈值

# ══════════════════════════════════════════════════════════════════════
# C. 检测后处理：NMS 是贪心近似，知道它错在哪就知道该换什么
# ══════════════════════════════════════════════════════════════════════
# 失效模式：**高分框独吞一片区域** —— 一个跨越两块牌子的合并框把两个正确框都杀了
# 对应的工程补丁（按代价从低到高）：
#   1) 调 iou_thr           密集场景调高（0.5 -> 0.65），代价是重复框变多
#   2) class-aware NMS      按类别分组做，避免不同类互相抑制（限速牌 vs 指路牌）
#   3) Soft-NMS             不删框，按重叠度衰减分数：s_i *= exp(-IoU^2 / sigma)
#                           sigma 典型 0.5；只在离线/评测用，车端慎用（保留框数变多 -> 延迟涨）
#   4) WBF (weighted boxes fusion)   一簇框加权融合而非择一，见 C56-04；适合 TTA / 多模型集成
#   5) 一对一标签分配        DETR 系匈牙利匹配 / YOLOv10 一致双分配 —— 训练期去重，
#                           推理端**根本不需要 NMS**（见 C53-04、C54）
#
# ── 推荐的验证方法（可直接抄进你的评测脚本）──
#   · 造一维退化用例（龙门架并排标志），用加权区间调度 DP 求最优，量化 NMS 的 gap
#   · 按"每个 GT 被几个保留框覆盖"分桶统计：>1 是重复，=0 是漏检，定位失效类型
#   · 延迟：NMS 是 O(N·K)，N 与 K 都随场景增长 -> 报 p50 和 **p99** 两个数（见 C53-04）

# ══════════════════════════════════════════════════════════════════════
# D. 预算分配 = 分组背包（把工程问题写成 DP 的最常见入口）
# ══════════════════════════════════════════════════════════════════════
#   把连续预算（ms / GB / 人天）量化成整数网格（如 0.1 ms 一格）
#   每个模块 = 一组，组内每档配置 = 一件物品 (cost, gain)
#   dp[c] = 该预算下的最大总收益；分组背包 O(组数 x 预算 x 组内档数)
#   **必须声明的三个前提**：收益可加、代价可加、预算可离散化
#   （现实里三个都只是近似：模块间有交互、延迟不线性叠加 —— 说出来是加分项）
'''
print(RECIPE)
for token in ["状态定义", "遍历顺序", "答案位置", "交换论证", "Soft-NMS", "WBF",
              "一对一标签分配", "分组背包", "p99"]:
    assert token in RECIPE, token
print("✅ 检查单覆盖：DP 五步 / 脱困路径 / 贪心的证明与反例 / NMS 补丁阶梯 / 预算分配的归约")"""),

    md("""### 小结

- **DP 五步里最贵的是第 ① 步和第 ⑤ 步。**状态定义是一句中文，不是一个数组；
  答案位置写错会给出「74% 的用例都对」的程序——本 notebook 用打家劫舍的两种状态定义把它复现了。
  拿到错误答案时的诊断顺序是：**念状态定义 → 手算 dp[1]/dp[2] → 查答案位置**。
- **不可达状态必须是 ±inf。**填 0 等于宣称「存在一个代价为 0 的方案」，
  于是「恰好装满 / 最少硬币」类题目会静默地给出错误答案（`coins=[2], amount=3` 返回 0）。
- **一维压缩后遍历方向决定题目本身**：容量倒序是 01 背包，正序是完全背包，
  同一份代码只差一个 `range` 的方向。压缩的代价是**失去方案回溯**。
- **贪心只有两种合法答案：给出交换论证，或给出反例。**
  区间调度按「最早结束」可证明最优（400 组随机用例 0 次失手），
  按「最早开始」失手 57 次、按「最短区间」失手 11 次；
  找零在 `[1,3,4]` 上从 amount=6 起就错，而 amount=5 恰好对——**反例往往不在最小用例里**。
- **NMS 就是最大权独立集的贪心近似。**一维退化情形下它等价于加权区间调度，
  可以用 DP 求出精确最优：教科书反例上贪心/最优 = 10/12 = 0.833，
  最坏情况族的比值趋于 0（**近似比无常数下界**），随机场景平均 0.98 但约 20% 的场景次优。
  真实失效模式是「合并框吃掉两块相邻牌子」——本 notebook 里贪心召回 0%、DP 召回 100%。
- **但不要说「应该换成 DP」。**二维 bbox 的冲突图是任意图，最大权独立集 NP-hard（实测 2^n 增长），
  而且「总分最大」只是代理目标。工程解法是 **Soft-NMS / WBF / 一对一标签分配**——
  把去重从推理期的组合优化挪到训练期的约束。

下一站：**模块 05 · 模拟面试与压力下的编码** —— 45 分钟怎么分、卡住了怎么说、
以及蓄水池采样这类 ML 岗真正高频的原题。"""),
]
