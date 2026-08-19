# 参考清单 · References（编程面试实战：算法与数据结构）

> 分主题列出。**★ = 必读**（读完这些能覆盖本课 80% 的内容与绝大多数面试提问）。
> 每条注明**它解决了什么问题**，以及要重点看哪一节——
> 算法书都很厚，但为面试准备时真正需要精读的通常只有其中三五章。
>
> 本清单有一个刻意的倾向：**优先给「能解释为什么」的一手材料**，而不是题解合集。
> 题解看再多也只能覆盖见过的题；而「为什么二分要这样写边界」「为什么贪心在这里成立」
> 这类问题一旦想通，没见过的题也能推出来——面试官考的恰恰是后者。
>
> 与相邻课程的分工：**C61-05** 是检测专项白板题（IoU/NMS/mAP/匈牙利/Focal）；
> **C07** 是 ML 数学推导；**C63** 是系统设计；**C64** 是概念问答；**C65** 是沟通与结构化表达。
> **本课只管通用算法与数据结构。**

---

## 一 · 教材：把「为什么」讲透的四本 · Textbooks

- ★ **Cormen, Leiserson, Rivest, Stein, _Introduction to Algorithms_（CLRS，第 4 版 2022）** —
  解决「所有结论都要有证明」的需求。**不要通读**，按下面的章节精读即可（括号内是第 3 版章号）：
  - **第 3 章 Characterizing Running Times**（3 版第 3 章）：渐进记号的严格定义。
    面试里说「O 只是上界、Θ 才是紧界」的底气来自这里。
  - **第 7 章 Quicksort + 第 9 章 Medians and Order Statistics** —
    **本课模块 02 的直接依据**。第 9.2 节的**期望线性时间选择（randomized-select）**给出了 quickselect
    期望 O(n) 的完整证明；9.3 节的 **median-of-medians（BFPRT）**给出确定性最坏 O(n) 的构造。
    重点体会「期望来自算法自己的随机数，不来自输入分布假设」这个区分——这是复杂度概念里最能显水平的一处。
  - **第 8 章 Sorting in Linear Time**：**比较排序的 Ω(n log n) 下界（决策树论证）**，
    以及计数/基数/桶排序如何绕过它。面试官问「能不能比 n log n 更快」时，这一节就是标准答案。
  - **第 11 章 Hash Tables**：链地址法与开放寻址、全域哈希。
    **11.2 的均摊分析解释了「均摊 O(1) 不是保证 O(1)」**，这是本课模块 02 的核心论点之一。
  - **第 14 章 Dynamic Programming**（3 版第 15 章）：**必读 14.3「Elements of dynamic programming」**——
    最优子结构与重叠子问题的精确定义，以及一个「看起来有最优子结构其实没有」的反例（最长简单路径）。
    本课 DP 五步法就是这一节的操作化版本。
  - **第 15 章 Greedy Algorithms**（3 版第 16 章）：**15.1–15.2 的活动选择问题与交换论证是贪心正确性证明的模板**；
    15.4 的拟阵（matroid）给出「什么样的问题结构保证贪心最优」的一般性回答，属于加分内容。
  - **第 16 章 Amortized Analysis**（3 版第 17 章）：聚合法/记账法/势能法三种均摊分析。
    动态数组扩容为什么是均摊 O(1)，这里有完整推导。
  - **第 19 章 Data Structures for Disjoint Sets**（3 版第 21 章）：**并查集的权威出处**。
    19.3 讲路径压缩 + 按秩合并，19.4 给出 **O(m α(n))** 的完整证明与反阿克曼函数的定义。
    「α(n) 对任何实际的 n 都 ≤ 5」这句话的依据就在这里。
  - **第 20 章 Elementary Graph Algorithms**（3 版第 22 章）：BFS/DFS 的性质、
    **20.4 的拓扑排序与 DFS 三色法判环**、20.5 的强连通分量。
  - **第 22 章 Single-Source Shortest Paths**（3 版第 24 章）：22.3 Dijkstra 及其**非负权前提的证明**——
    「已出队的点不再更新」这个性质为什么成立，答案在这一节的正确性证明里。
- ★ **Kleinberg & Tardos, _Algorithm Design_（2005）** —
  解决 CLRS「证明严谨但设计思路藏得深」的问题。**这本书的组织方式是按「设计范式」而不是按「数据结构」**，
  更贴近面试的思考方式。三节必读：
  - **§4.1 Interval Scheduling**：无权区间调度的贪心（按结束时间排序）与**完整的交换论证**。
    这是「stays ahead」证明法最干净的示范。
  - **§6.1 Weighted Interval Scheduling**：**本课模块 04 把 1-D NMS 建模成加权区间调度的直接依据**。
    它先展示贪心在加权情形下失效，再引出 DP——这个「贪心 → 反例 → DP」的叙事正是本课模块 04 的骨架。
  - **§6.4 Knapsack / §6.6 Sequence Alignment**：背包与编辑距离的标准推导，含空间压缩的讨论。
- ★ **Sedgewick & Wayne, _Algorithms_（第 4 版）与配套 booksite** —
  解决「我知道原理但写不出干净代码」的问题。它的价值在于**每个算法都给了可运行的完整实现与实测数据**，
  以及大量可视化。重点看：
  - **§1.5 Case Study: Union-Find** — 从 quick-find 到 quick-union 到加权 quick-union 再到路径压缩，
    **一步一步给出每一版的实测运行时间**。这是理解「为什么要按秩合并」最有说服力的材料，
    比直接给最终版本强得多。
  - **§2.1–2.3 排序** 与 **§2.4 优先队列/堆**、**§2.5 排序的应用**（含稳定性讨论）。
  - **§3.4 Hash Tables** — 链地址与线性探测的实测对比，负载因子的影响曲线。
  - **§4.1–4.4 图算法** — 无向图/有向图/最小生成树/最短路，代码风格非常适合照着写。
  - **免费 booksite（algs4.cs.princeton.edu）有全部代码与练习**，且配 Coursera 上两门公开课。
- **Skiena, _The Algorithm Design Manual_（第 3 版）** —
  解决「面对一个新问题，我该往哪个方向想」的问题。它的**第二部分「算法目录」**按问题类型
  （而不是按技术）索引了 75 个经典问题，每个给出「什么时候用什么」的实用建议。
  第一部分的 **war stories** 讲的是真实工程里算法选择的故事，读起来轻松且很有启发。
  **面试前一晚翻目录部分的性价比很高。**
- **Laaksonen, _Competitive Programmer's Handbook_（免费 PDF）** —
  解决「模板要写成什么样」的问题。**它对「在答案上二分」和各类 DP 模板的写法总结得极其简洁**，
  是本课模板部分的重要参考。缺点是竞赛导向，有些内容（数论、几何模板）在面试里用不上，可跳过。

---

## 二 · 二分查找：一个值得单独立章的话题 · Binary Search

- ★ **Bentley, _Programming Pearls_（第 2 版）Column 4「Writing Correct Programs」** —
  解决「为什么这么简单的算法这么多人写错」。**它用二分查找当例子，完整演示了「用循环不变量做程序验证」的方法**：
  先写不变量，再写代码，每一行都对着不变量检查。
  **本课模块 02 把不变量写成 `assert` 放进循环体的做法，直接来自这一章。**
  Bentley 提到他曾让上百名职业程序员写二分，多数人的版本都有 bug——这个故事本身就值得在面试里当谈资。
- ★ **Bloch, "Extra, Extra — Read All About It: Nearly All Binary Searches and Mergesorts are Broken"（Google Research Blog, 2006）** —
  解决「`(lo + hi) / 2` 的整数溢出」这个潜伏了二十年的 bug：
  **JDK 的 `Arrays.binarySearch` 从 1997 年写下到 2006 年才被发现并修复**。
  Python 因为 int 无限精度不受影响，但**面试官问「换成 C++/Java 呢」时，
  能答出 `lo + (hi - lo) // 2` 并说出这段历史，是很强的信号**；
  另外用 numpy 的 int32 做索引时这个坑仍然存在。
- **cp-algorithms.com 的 "Binary search" 条目** —
  解决「三套模板到底怎么统一」。它把二分统一表述为**在单调谓词上找分界点**，
  并给出闭区间与半开区间两种写法的完整不变量。**本课模块 02 的模板表与它的表述一致。**
- **Python 官方文档 `bisect` 模块** —
  解决「标准库是怎么定义边界的」。**`bisect_left` = 第一个 ≥ target 的位置，`bisect_right` = 第一个 > target 的位置**；
  文档里还给出了用 `bisect` 实现「查找、插入、按分数分档」的官方配方（`grade` 函数那个例子）。
  **本课的手写三模板会与 `bisect` 逐点对拍**，这是验证自己模板正确性的最省事方法。
  另注意 Python 3.10 起 `bisect` 支持 `key=` 参数，面试里用得上。

---

## 三 · Python 的实现细节与复杂度 · CPython Internals

> 这一组是本课的**特色**：ML/CV 岗的 coding 题几乎都用 Python 写，
> 而「Python 的这个操作到底是什么复杂度」是最常见也最容易答错的一类追问。

- ★ **Python Wiki, "TimeComplexity"（wiki.python.org/moin/TimeComplexity）** —
  解决「`list` / `dict` / `set` / `deque` 各操作的复杂度到底是多少」。
  **必须记住的几条**：`list.insert(0,x)` 与 `list.pop(0)` 是 **O(n)**（所以要用 `deque`）；
  `x in list` 是 **O(n)** 而 `x in set` 是均摊 **O(1)**；`list.append` 是**均摊** O(1)。
  **一半的「我的解法明明是 O(n) 为什么超时」都出在这张表上。**
- ★ **CPython 源码注释 `Objects/listsort.txt`（Tim Peters 撰写）** —
  解决「Timsort 到底做了什么」。这是一份**极其好读**的设计文档，讲清了：
  为什么利用自然 run、galloping mode 的触发条件、以及**为什么 Timsort 是稳定的**。
  面试里被问「Python 的 sort 是什么算法、稳定吗、最坏复杂度多少」时，答案全在这里
  （归并系 / 稳定 / 最坏 O(n log n) / 需要 O(n) 额外空间）。
- ★ **Python 官方文档 `heapq` 模块** —
  解决 Top-K 与优先队列。**三个必须知道的点**：
  ① Python **只有小顶堆**，大顶堆要取负数或用元组包装；
  ② `heapq.heapify` 是 **O(n)** 而不是 O(n log n)（文档明确写了 "in linear time"）；
  ③ `nlargest(k, it)` / `nsmallest` 内部就是 O(n log k) 的堆解法，
  但**考 Top-K 时直接调用它可能被判绕过考点**，先问一句再用。
- ★ **Python 官方文档 `collections` 模块** —
  `Counter`（一行统计频次，`most_common(k)` 内部走 `heapq.nlargest`）、
  `defaultdict`（省掉存在性判断）、**`deque`（两端 O(1)，是单调队列与 BFS 队列的正确载体）**。
  **用 `list` 当队列做 BFS 是隐藏的 O(n²)**，这是网格题里最常见的性能 bug。
- **Python 官方文档 `functools.lru_cache` / `cache`** —
  解决「记忆化搜索怎么写得最短」。一行装饰器把指数级递归变成多项式。
  **注意两个坑**：① 参数必须可哈希（所以传 `tuple` 不能传 `list`）；
  ② 递归深度仍然受限，n 很大时还是要改递推。
- **Python 语言参考中关于 `dict` 顺序的说明（Python 3.7+）** —
  解决「dict 到底有没有序」。**3.7 起插入顺序是语言级保证**（3.6 是实现细节），
  这让 `list(dict.fromkeys(a))` 成为标准的**保序去重**惯用法。
  但要清楚：**这个顺序是靠额外的紧凑数组维护的，和哈希桶无关**——面试里能说清这一层区别会很加分。
- **Rhodes, "The Mighty Dictionary"（PyCon 演讲）与 CPython `Objects/dictobject.c` 顶部注释** —
  解决「CPython 的 dict 内部到底怎么实现」。开放寻址 + 伪随机探测序列 + 紧凑布局（3.6 起的 key-sharing 与 indices 数组）。
  **属于加分内容**，但被问到「dict 怎么解决冲突」时能答出「CPython 用的是开放寻址不是链地址」，区分度很高。
- **Python 官方文档 `random` 模块** —
  `random.shuffle` **就是 Fisher-Yates**（文档明确说明），`random.sample` 是无放回采样，
  `random.choices` 是有放回加权采样。**面试里写测试时随手 `random.seed(0)` 是专业度信号。**
- **Grant Jenks, `sortedcontainers`（纯 Python 实现的 SortedList/SortedDict）** —
  解决「Python 没有 `std::set` / `TreeMap` 怎么办」。
  分块数组实现，实测比很多 C 扩展的平衡树还快。**面试里遇到需要「有序多重集合 + 动态插删」的题
  （滑窗中位数、区间合并的动态版），能说出「Python 标准库没有，我会用 sortedcontainers 或用两个堆模拟」是加分**。

---

## 四 · 并查集与连通域标记 · Union-Find & Connected Components

> **这一节是本课与 CV 岗结合最紧的地方**：并查集不是「竞赛技巧」，
> 它是检测后处理里框聚类、切片推理跨片合并、以及图像连通域标记的实际实现。

- ★ **Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm"（JACM 1975）** —
  解决「路径压缩 + 按秩合并到底有多快」。**给出了 O(m α(m,n)) 的上界与反阿克曼函数**。
  论文本身不好读，**但知道这个结论的出处、并能说清「α 不是常数但对任何实际 n ≤ 5」，
  比背一句「几乎 O(1)」强得多**。
- **Tarjan & van Leeuwen, "Worst-case Analysis of Set Union Algorithms"（JACM 1984）** —
  把路径压缩 / 路径分裂 / 路径减半，与按秩 / 按大小合并的所有组合都分析了一遍。
  **实用结论：路径减半（path halving）+ 按大小合并写起来最短，复杂度与完整版一样**——
  面试里写迭代版并查集时这是最省事的选择。
- **Fredman & Saks, "The Cell Probe Complexity of Dynamic Data Structures"（STOC 1989）** —
  证明了 **Ω(α(n)) 的下界**，即并查集的这个复杂度是最优的、不可能做到真正的常数。
  纯加分知识。
- ★ **Hoshen & Kopelman, "Percolation and cluster distribution I"（Physical Review B, 1976）** —
  **连通域标记的两遍扫描算法的原始出处**，来自统计物理的渗流研究。
  它的做法是：第一遍扫描给每个前景像素一个临时标号并**用并查集记录标号之间的等价关系**，
  第二遍把标号统一。**这就是「岛屿数量」这道题在真实图像处理里的工业实现**——
  面试里说出「这题的工业版本叫连通域标记，两遍扫描 + 并查集，出自 1976 年的渗流理论」，
  分量完全不同。
- ★ **Wu, Otoo & Suzuki, "Optimizing two-pass connected-component labeling algorithms"（Pattern Analysis and Applications, 2009）** —
  解决「两遍扫描怎么做到最快」：decision-tree 式的邻域访问顺序 + 数组式并查集。
  **本课模块 03 的连通域标记实现参考了它的邻域访问策略。**
- **He, Ren, Gao, Zhao et al., "The connected-component labeling problem: A review of state-of-the-art algorithms"（Pattern Recognition, 2017）** —
  综述，解决「有多少种 CCL 算法、各自的适用场景」。
  **重点看它对 4 邻域与 8 邻域的讨论**：两者会给出不同的连通块数，
  且前景用 8 邻域时背景必须用 4 邻域才能保持拓扑一致（Jordan 曲线性质）。
  **这个细节在面试里提到会非常亮眼，因为它说明你写过真实的图像处理代码而不只是刷过题。**
- **OpenCV 文档 `cv2.connectedComponentsWithStats` 与 SciPy `ndimage.label`** —
  解决「工业界实际怎么调用」。**知道有现成实现、且知道 `connectivity` 参数控制 4/8 邻域，
  是「我知道什么时候不该造轮子」的信号**——但面试要你手写时仍然要能写出来。

---

## 五 · CV 场景的算法连接 · Algorithms in Vision

> 这一组回答一个具体问题：**「算法题和我要做的 TSR 检测有什么关系？」**
> 答案是：关系比想象中直接得多，而能说清这层关系，是 ML/CV 岗 coding 环节最有效的差异化。

- ★ **Viola & Jones, "Rapid Object Detection using a Boosted Cascade of Simple Features"（CVPR 2001）** —
  解决「怎么在 2001 年的硬件上做到实时人脸检测」。
  **它的第一个关键贡献就是 integral image（积分图）——也就是二维前缀和**：
  Haar 特征需要在成千上万个不同位置、不同大小的矩形上求和，
  用积分图后**每个矩形和都只要四次查表，与矩形大小无关**。
  **必读 §2「Features」的前两页**，那是二维前缀和最有说服力的一次应用。
  这篇论文让「前缀和」这个看起来像刷题技巧的东西，变成了一个真实系统的性能支柱。
- **Crow, "Summed-Area Tables for Texture Mapping"（SIGGRAPH 1984）** —
  积分图的**真正原始出处**（比 Viola-Jones 早 17 年，来自图形学的纹理映射）。
  **提到这一条说明你追过源头**，是很轻的加分但成本极低。
- ★ **Neubeck & Van Gool, "Efficient Non-Maximum Suppression"（ICPR 2006）** —
  解决「NMS 本身的算法复杂度」。它把 NMS 当作一个**独立的算法问题**来分析并给出高效实现，
  而不是当作检测器的一个附属步骤。**本课模块 03 把 NMS 重述成图论问题、
  模块 04 把它重述成加权区间调度，思路上都是这条线的延续。**
- **Rothe, Guillaumin & Van Gool, "Non-maximum suppression for object detection by passing messages between windows"（ACCV 2014）** —
  把 NMS 显式表述成**框之间的图上推理**（消息传递 / 聚类），
  是「NMS 是一个图问题」这个视角最直接的文献支持。
- **Hosang, Benenson & Schiele, "Learning non-maximum suppression"（CVPR 2017）** —
  解决「贪心 NMS 是次优的，能不能学一个更好的」。
  **它开篇对贪心 NMS 局限性的分析，正是本课模块 04「量化贪心次优程度」实验的动机来源。**
- **Karp, "Reducibility Among Combinatorial Problems"（1972）** —
  **最大独立集 / 团问题 NP-完全性的出处**。
  本课把 NMS 重述成「加权最大独立集」后，这条引用回答了「那为什么不直接求最优解」：
  因为一般图上的最大加权独立集是 NP-难的，**贪心 NMS 是一个廉价近似**。
  一维区间的特殊情形（加权区间调度）才有多项式时间的 DP 最优解——这正是本课要做的对比实验。
- **Levenshtein 距离与 WER/CER 的关系（各类 OCR / ASR 评测文档）** —
  解决「编辑距离在 ML 里干什么用」。**字符错误率（CER）就是编辑距离除以参考长度**，
  车牌识别、路牌文字识别的评测直接依赖它。
  模块 04 写编辑距离时，请把它当作一个**评测指标的实现**来写，而不是一道刷题题。
- **Cuturi & Blondel, "Soft-DTW: a Differentiable Loss Function for Time-Series"（ICML 2017）** —
  解决「DTW 这个老 DP 算法在深度学习时代还有没有用」：把 min 换成 soft-min 使其可微，
  于是可以直接当损失训练。**用来回答「动态规划在现代 ML 里过时了吗」这个追问。**

---

## 六 · 采样与随机化 · Sampling & Randomization

> ML/CV 岗特有的高频题型。它们看起来是「概率题」，其实是**数据管线里的真实需求**：
> 从不知道多长的日志流里均匀抽样、按类别频率做长尾重采样、以及正确地打乱数据集。

- ★ **Vitter, "Random Sampling with a Reservoir"（ACM TOMS, 1985）** —
  **蓄水池采样的权威出处**。解决「流的长度未知时如何等概率抽 k 个」。
  **必须能当场证明**：第 i 个元素以 k/i 的概率入池，则每个元素最终留在池中的概率都是 k/n——
  归纳证明只有三行，但面试官一定会让你推。
  论文里还给出了 Algorithm X/Y/Z 这几个**跳过式加速版本**（不必对每个元素都掷骰子），属于加分内容。
- ★ **Efraimidis & Spirakis, "Weighted random sampling with a reservoir"（Information Processing Letters, 2006）** —
  解决**加权**蓄水池采样。核心技巧（A-Res）非常漂亮：
  给每个元素生成键 `u^(1/w)`（u 是 [0,1) 均匀随机数、w 是权重），取键最大的 k 个即可。
  **这直接对应长尾数据的重采样**（稀有类别给更大的 w），呼应 **C58** 的数据工程内容。
- ★ **Knuth, _TAOCP_ Vol. 2, §3.4.2「Random Sampling and Shuffling」（Algorithm P）** —
  **Fisher-Yates 洗牌的权威表述**，也叫 Knuth shuffle。
  解决「怎么让 n! 种排列严格等概率」。**关键是第 i 步只能与 `[0, i]` 范围内交换**，
  写成 `[0, n-1]` 就是那个经典的错误版本。
- **Durstenfeld, "Algorithm 235: Random permutation"（CACM 1964）与 Fisher & Yates 的原始统计表（1938）** —
  前者是现代 O(n) 原地版本的出处，后者是算法的最初形式（纸笔时代，O(n²)）。
  **知道「Fisher-Yates 原版是 O(n²)、Durstenfeld 才把它做成 O(n) 原地」是个很轻的加分点。**
- **关于错误洗牌的偏差分析（如 "The Danger of Naïveté" 一类的经典博文与 Microsoft 2007 年浏览器选择页事件）** —
  解决「凭什么说那个写法有偏」。**计数论证非常干净**：
  错误写法（`swap(i, random(0, n-1))`）产生 nⁿ 条等概率执行路径，要覆盖 n! 种排列，
  而 **n ≥ 3 时 nⁿ 不能被 n! 整除**，由鸽笼原理必有排列的概率不等。
  2007 年微软为反垄断和解做的浏览器随机排序页面，就是因为用了错误的洗牌而被发现有明显偏向——
  **这是一个真实世界的、代价高昂的算法 bug，在面试里是极好的例子。**
  本课模块 05 用卡方检验在几千次重复里把这个偏差直接测出来。
- **Motwani & Raghavan, _Randomized Algorithms_（第 1 章）** —
  解决「随机化到底买到了什么」。**核心论点：随机化把最坏情况从「输入决定」变成「骰子决定」，
  于是对手无法构造坏输入。** 这是理解 quickselect「期望 O(n)」的关键，
  也是复杂度讨论里最能拉开区分度的一处。第 1 章读完就够。

---

## 七 · 面试实务：题库与评分视角 · Interview Practice

> ⚠️ 这一组的定位是**辅助**。本课的主张是：协议与模板比题量重要。
> 但如果你还有时间做题，下面几本能保证你做的是「对的题」。

- ★ **McDowell, _Cracking the Coding Interview_（第 6 版）** —
  解决「面试官那一侧在想什么」。**真正必读的是前 60 页（Part I: The Interview Process）**，
  尤其是它对**评分维度**与「面试官如何评估一个 hint 之后的表现」的描述。
  后面的题库质量中等且偏 Java，**可以只当索引用**。
- ★ **Aziz, Lee & Prakash, _Elements of Programming Interviews in Python_** —
  解决「题解要写成什么样才算好代码」。**它的参考解普遍比 CtCI 干净**，
  且每题都给出复杂度分析与变体追问。**Chapter 5（Arrays）、6（Strings）、11（Searching）、
  13（Sorting）、14（BST）、16（DP）、17（Greedy & Invariants）** 与本课模块一一对应。
  **第 17 章叫 "Greedy Algorithms and Invariants"——把贪心和不变量放在一章，
  这个编排本身就说明了本课反复强调的那件事。**
- **yangshun, _Tech Interview Handbook_（免费开源）** —
  解决「有限时间怎么排优先级」。它给出了一份基于统计的**题型优先级排序**与
  "Blind 75 / Grind 75" 式的精选题单。**如果你只有三天，用它的题单比自己乱选强。**
  注意它面向通用软件岗，**ML/CV 岗的分布不一样**（本课 README 里给了修正）。
- **各家公开的面试评分维度说明（Google/Meta 等公司 careers 页面与工程博客上的公开描述）** —
  解决「五维评分表是我编的吗」。这些公开材料普遍提到
  **problem solving / coding / communication** 三大类，
  其中 communication 被反复强调。**本课的五维表是对它们的一个操作化拆分。**
- **LeetCode 的 Discuss 区里高赞的「模板总结」帖（滑动窗口、二分、回溯、DP）** —
  解决「同一类题的统一写法」。**用法建议**：不要背模板，
  而是拿它和本课的模板对照，**找出差异并搞清楚为什么**——差异通常出在边界处理上，
  而那正是最容易写错的地方。
- **`cp-algorithms.com` 与 USACO Guide** —
  解决「某个具体算法的标准实现长什么样」。两者都免费、都有严格的复杂度说明，
  且代码风格干净。**查具体算法时比翻书快。**

---

## 八 · 本库内的交叉引用 · Cross-References

- **C61 · 检测工程实战与面试实务** — **模块 05 是检测专项白板题**：
  IoU、NMS、mAP、匈牙利匹配、Focal Loss、anchor 生成、坐标变换的手撕实现。
  **本课与它严格互补**：C61 用代码考「你懂不懂检测」，本课用代码考「你会不会写代码」。
  C61-05 写过的题本课一道不重写；反过来，本课模块 03/04 把 NMS 当作**图论题与 DP 题**来分析，
  那是 C61 不会讲的角度。**面试前两门都要过一遍。**
- **C07 · ML 基础与面试数学** — 数学推导（softmax 梯度、贝叶斯、最大似然、k-fold、偏差-方差）。
  与本课对应 HR 所说的不同板块：C07 偏 Technical Knowledge，本课就是 Practical (Coding) Exercise。
- **C58 · 数据工程与闭环** — 长尾重采样、分层抽样。**本课模块 05 的加权蓄水池采样是它的算法底座。**
- **C57 · 小目标检测** — 切片推理（SAHI）的跨片框合并。**那个合并用的就是本课模块 03 的并查集。**
- **C63 / C64 / C65 · 同批新课** — 分别对应系统设计、概念问答、结构化沟通。
  一句话记住五门课的分工：**C07 推导 · C62 编码 · C63 设计 · C64 问答 · C65 沟通。**
