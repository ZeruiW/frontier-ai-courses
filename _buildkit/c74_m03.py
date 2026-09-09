# -*- coding: utf-8 -*-
"""C74 模块 03 · 可微分 tile 光栅化。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 为什么是 <strong>tile</strong> 而不是逐像素或逐高斯；"
                   "② <strong>一个 64 位键让一次基数排序同时按 tile 与深度排好序</strong>，"
                   "而深度用几位量化是一个有量化后果的选择；"
                   "③ 排序成本由<strong>覆盖半径</strong>决定（半径 ×2.5 → 对数 ×3.06）；"
                   "④ 提前终止省掉 92.2% 的工作；"
                   "⑤ <strong>整帧时延由最慢的那个 tile 决定</strong>（不均衡 2.67×）；"
                   "⑥ 反向传播的写冲突：一个 8 px 的高斯要承受 201 次 atomicAdd"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_rasterization.ipynb'
                       '（<strong>从零写一个能出图的 tile 光栅化器</strong> / '
                       '64 位键的正确性与量化位数的碰撞率 / '
                       '<strong>16 位深度会让 68.75% 的相邻对顺序未定义</strong> / '
                       '提前终止的逐 tile 收益 / 负载分布 / '
                       '<strong>与逐像素暴力实现逐位比对</strong>）'),
    ("核心参考", "Kerbl et al., <em>3D Gaussian Splatting</em>（SIGGRAPH 2023，§6 光栅化器）· "
                 "官方实现 <code>diff-gaussian-rasterization</code>（forward.cu / backward.cu）· "
                 "Merrill &amp; Grimshaw, <em>High Performance and Scalable Radix Sorting</em>（2011）· "
                 "Radl et al., <em>StopThePop</em>（SIGGRAPH 2024，逐像素排序）· "
                 "Ye et al., <em>gsplat</em>（JMLR 2025，开源重实现）· "
                 "本课程 <strong>C36</strong>（GPU 内核与性能工程，本模块只讲算法结构不讲 CUDA）"),
    ("预计时长", "读 50 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-tile", "为什么是 tile：两种朴素做法各自死在哪", "".join([
        P("目标：给定几十万个已投影成 2D 椭圆的高斯，算出 1920×1080 的图像。"
          "而 α 合成要求**每个像素上按深度有序**。有三种组织方式。"),
        TABLE(["做法", "怎么做", "死在哪"], [
            ["<strong>逐像素</strong>",
             "对每个像素，找出覆盖它的高斯，排序，合成",
             "<strong>排序次数 = 像素数 = 207 万次</strong>。"
             "<em>每次排序几十到几百个元素，而且相邻像素的排序结果高度重复——"
             "全是重复劳动</em>"],
            ["<strong>逐高斯</strong>",
             "按深度排一次全局序，然后从近到远把每个高斯「涂」上去",
             "<strong>不能提前终止</strong>（不知道哪个像素已经饱和了），"
             "而且<strong>写冲突严重</strong>——"
             "<em>相邻高斯覆盖同一批像素，GPU 上是读-改-写竞争。"
             "更根本的是它无法做 $T$ 的串行累积</em>"],
            ["<strong>逐 tile（3DGS 的做法）</strong>",
             "把屏幕切成 16×16 的 tile；对每个 tile 收集覆盖它的高斯、排一次序；"
             "tile 内 256 个像素<strong>共享这一个顺序</strong>",
             "<strong>排序次数降到 8160 次</strong>，"
             "<em>而代价是「tile 内共享顺序」这个近似</em>（第 5 节）"],
        ]),
        ASCII("""
   1920x1080，16x16 的 tile：

   ceil(1920/16) = 120 列   ceil(1080/16) = 68 行   ->  8160 个 tile
   （1080/16 = 67.5，所以最后一行 tile 只用了 8 行像素）

   ┌────┬────┬────┬─  ...  ─┬────┐
   │ 0  │ 1  │ 2  │         │119 │   每个 tile = 16x16 = 256 个像素
   ├────┼────┼────┼─  ...  ─┼────┤   GPU 上：一个 tile = 一个 block
   │120 │121 │    │         │    │              一个像素 = 一个线程
   ├────┼────┼────┼─  ...  ─┼────┤
   ...                                256 个线程共享一份「排好序的高斯列表」
   └────┴────┴────┴─  ...  ─┴────┘    -> 从共享内存分批读，而不是各自去全局内存取
        """),
        DUAL(
            "<strong>16×16 = 256 不是随便挑的：它正好是一个 CUDA block 的常用线程数，"
            "而 256 个线程刚好能协作把高斯数据分批载入共享内存。</strong>"
            "<em>tile 太大 → 一个 tile 里的高斯列表太长、共享顺序的近似误差变大、"
            "而且提前终止的收益被摊薄（因为要等 tile 里最深的那个像素）；"
            "tile 太小 → 排序次数变多、每个高斯被重复登记到更多 tile 里</em>。",
            "<strong>而「tile 内共享一个顺序」是 3DGS 的一个真实近似，"
            "不是实现细节。</strong>"
            "<em>两个相互穿插的椭球，在 tile 的左半边 A 在前、右半边 B 在前，"
            "但它们在这个 tile 里只有一个顺序</em>。"
            "<strong>相机转动时这个顺序会在某个角度突然翻转，画面「跳一下」——"
            "这就是 popping</strong>，"
            "<em>StopThePop（2024）用分层/逐像素排序修它，代价是 2 倍左右的渲染时间</em>。"),
    ])),

    # ============================================================== 2
    ("binning", "分箱与那个 64 位键", "".join([
        P("第一步：对每个高斯，算出它的 $3\\sigma$ 包围盒覆盖哪些 tile，"
          "为每个 (高斯, tile) 组合生成一个条目。这个数字直接决定后面所有成本。"),
        TABLE(["高斯数", "覆盖半径", "每个高斯覆盖的 tile 数", "(高斯,tile) 对总数",
               "每 tile 平均"], [
            ["100 k", "8 px", "4.00", "0.40 M", "49.0"],
            ["500 k", "4 px", "2.25", "1.12 M", "137.9"],
            ["500 k", "8 px", "4.00", "<strong>2.00 M</strong>", "<strong>245.1</strong>"],
            ["500 k", "20 px", "12.25", "<strong>6.12 M</strong>", "750.6"],
            ["1 M", "8 px", "4.00", "4.00 M", "490.2"],
        ]),
        P("覆盖 tile 数 $\\approx (2r/16 + 1)^2$。所以**半径从 8 涨到 20（2.5 倍），"
          "对数涨 3.06 倍**——而对数就是排序的输入规模。"),
        CALLOUT("intuition",
                "<strong>这解释了模块 02 里 <code>max_screen_size = 20</code> 那个剪枝的第二重意义。</strong>"
                "<em>它不只是为了控制仿射近似的误差（模块 02 第 4 节），"
                "更是为了控制排序成本——一个屏幕半径 100 px 的高斯要被登记到 "
                "$(200/16+1)^2 \\approx 177$ 个 tile 里，"
                "抵得上 44 个正常大小的高斯</em>。"),
        H3("键的设计：一次基数排序解决两件事"),
        P("需要的顺序是「先按 tile 分组，组内按深度」。3DGS 的做法是把两者拼进一个 64 位整数："),
        ASCII("""
   uint64 key = (tile_id << 32) | depth_bits

   ┌──────────── 高 32 位 ────────────┬──────────── 低 32 位 ────────────┐
   │          tile_id (0..8159)        │   深度（单调编码成 uint32）       │
   └───────────────────────────────────┴──────────────────────────────────┘

   对这个键做一次**基数排序**，结果自动就是「按 tile 分组、组内按深度升序」。
   然后扫一遍找出每个 tile 的 [start, end) 区间即可。

   官方实现：cub::DeviceRadixSort::SortPairs(...)  —— 一次调用
        """),
        DUAL(
            "<strong>为什么是基数排序而不是快排：基数排序是 $O(P)$，比较排序是 $O(P\\log P)$。</strong>"
            "<em>$P = 2\\times10^6$ 时 $\\log_2 P = 20.9$——比较排序要多做 21 倍的工作量级</em>。"
            "<strong>而基数排序对 64 位键只需固定的几遍扫描（每遍处理 4–8 位），"
            "且完全没有分支——正好是 GPU 擅长的形状。</strong>",
            "<strong>而「深度用多少位」是一个有真实后果的选择，不是实现细节。</strong>"
            "<em>位数不够时，不同深度的高斯会量化到同一个值，"
            "于是它们的相对顺序变成<strong>未定义</strong>（取决于排序是否稳定、以及输入顺序）</em>。"
            "<strong>把深度范围 0.5–100 m 量化后，相邻键相等的比例：</strong>"),
        TABLE(["深度位数", "相邻键相等（顺序未定义）的比例", "后果"], [
            ["16 位", "<strong>68.75%</strong>",
             "<strong>三分之二的相邻对顺序随机</strong>——"
             "<em>而模块 01 量过，打乱顺序的中位偏差是 19.6%</em>"],
            ["20 位", "9.15%", "仍然明显"],
            ["24 位", "0.585%", "大致可接受"],
            ["32 位", "<strong>0.0025%</strong>", "<strong>官方的选择</strong>"],
        ]),
        CALLOUT("paper",
                "<strong>官方实现的做法比「量化」更聪明：它直接把 float32 的深度按位重解释成 uint32。</strong>"
                "<em>对<strong>正</strong>浮点数，IEEE 754 的位模式与数值是单调同序的——"
                "所以按 uint32 排序就等于按 float 排序，一位精度都不损失</em>。"
                "<strong>而这个技巧只对正数成立</strong>，"
                "<em>所以它依赖前一步的近平面剔除（$z > 0.2$）已经保证了深度为正</em>——"
                "<em>两个看起来无关的实现细节其实是耦合的</em>。"),
    ])),

    # ============================================================== 3
    ("render", "逐 tile 渲染：分批、共享内存、提前终止", "".join([
        ASCII("""
   每个 tile 的内层循环（256 个线程 = 256 个像素，同步推进）：

   T = 1.0;  C = 0
   for (batch of 256 gaussians in this tile's sorted range) {
       ─── 256 个线程协作，把这 256 个高斯的 (uv, Σ'⁻¹, α, color) 载入共享内存 ───
       __syncthreads();
       for (j = 0; j < 256; j++) {              // 每个线程独立走这 256 个
           alpha = α_j * exp(-0.5 * d^T Σ'⁻¹ d);
           if (alpha < 1/255) continue;         // 太淡，跳过
           if (T * (1-alpha) < 1e-4) { done = true; break; }   // 提前终止
           C += T * alpha * color_j;
           T *= (1 - alpha);
       }
       if (__syncthreads_count(done) == 256) break;   // 整个 tile 都饱和了才退出外层
   }
        """),
        DUAL(
            "<strong>两个层次的提前终止要分清。</strong>"
            "<em>① <strong>线程级</strong>：某个像素饱和后它自己 <code>break</code>，"
            "不再累加——省的是算术；"
            "② <strong>block 级</strong>：只有当 tile 里<strong>全部 256 个像素</strong>都饱和了，"
            "才停止从全局内存载入下一批高斯——省的是访存</em>。"
            "<strong>后者才是省时间的主项，而它要求整个 tile 一起饱和</strong>——"
            "<em>所以一个 tile 里只要有一个像素看向天空（永不饱和），"
            "整个 tile 就要把列表走完</em>。",
            "<strong>而收益的量级：模块 01 量过，$\\alpha\\in[0.1,0.7]$、"
            "$T_{\\min}=10^{-4}$ 时，245 个高斯里只需处理 19 个——"
            "92.2% 的算术可以省掉，误差 $2.4\\times10^{-5}$（远低于 8 bit 的 1/255）。</strong>"
            "<em>但这是<strong>单个像素、且 $\\alpha$ 都不小</strong>时的数字</em>。"
            "<strong>notebook 在它自己那个含大片背景的场景上实测："
            "省下 <em>76.5%</em> 的高斯-像素求值（均值从 34.4 降到 8.1）</strong>——"
            "<em>低于 92.2%，因为该场景里 α 偏小、而且大片背景永远不饱和</em>。"
            "<strong>而 block 级的收益还要更低，因为它取决于 tile 内最难饱和的那个像素。</strong>"
            "<em>这是一个真实的、结构性的落差，不该含糊过去："
            "92.2% 是理想上界，76.5% 是一个具体场景的实测，而访存的收益比两者都低</em>。"),
        H3("$\\alpha < 1/255$ 就跳过"),
        P("这一行看着微不足道，但它与模块 02 的 $3\\sigma$ 截断是同一件事的两面。"
          "$3\\sigma$ 处的衰减因子是 $e^{-4.5} = 0.0111$，"
          "所以 $\\alpha^{(g)} < 0.353$ 的高斯在 $3\\sigma$ 处已低于 $1/255$——"
          "**对它们，包围盒的外圈本来就是白算的**。"),
    ])),

    # ============================================================== 4
    ("backward", "反向传播：重放、写冲突、以及必须存什么", "".join([
        P("模块 01 已经给出了 α 合成的梯度式。这里的问题是**怎么在 tile 结构上算它**。"),
        TABLE(["需求", "为什么", "实现代价"], [
            ["<strong>必须知道前向的顺序</strong>",
             "$T_i$ 依赖前面所有 $\\alpha_j$",
             "<strong>排序结果必须保留到反向</strong>（或重排一遍）。"
             "<em>官方选择保留：2 M 个 uint64 键 = 16 MB，比重排便宜</em>"],
            ["<strong>必须重放提前终止点</strong>",
             "被跳过的高斯梯度应为零",
             "前向记录每个像素的 <code>last_contributor</code>，"
             "<em>反向 <code>if (contributor > last_contributor) continue;</code></em>"],
            ["<strong>必须知道 $T_{\\text{final}}$</strong>",
             "反向从末尾往回推 $T_i = T_{i+1}/(1-\\alpha_i)$",
             "<em>存一张 $T_{\\text{final}}$ 图（每像素一个 float）</em>"],
            ["<strong>梯度要累加到高斯上</strong>",
             "一个高斯覆盖很多像素，每个像素都贡献一份梯度",
             "<strong>atomicAdd，且冲突严重</strong>——见下"],
        ]),
        H3("写冲突的量级"),
        TABLE(["高斯的屏幕半径", "覆盖的像素数", "反向时打到同一高斯的 atomicAdd 次数"], [
            ["4 px", "≈ 50", "50 × 59 个参数"],
            ["8 px", "≈ 201", "<strong>201 × 59 个参数</strong>"],
            ["20 px", "≈ 1257", "<strong>1257 × 59 个参数</strong>"],
        ]),
        DUAL(
            "<strong>这是 3DGS 训练比推理慢得多的主因之一，而它是结构性的。</strong>"
            "<em>前向是「多个高斯 → 一个像素」（读多写少）；"
            "反向是「一个像素 → 多个高斯」（读少写多，且写地址高度重合）</em>。"
            "<strong>官方内核的缓解手段是先在 block 内的共享内存里做归约，"
            "每个 tile 只对每个高斯发一次全局 atomicAdd</strong>——"
            "<em>把 201 次降到「覆盖的 tile 数」次，即 4 次左右</em>。",
            "<strong>而这又一次说明覆盖半径是主控变量：</strong>"
            "<em>它同时决定了 ① (高斯,tile) 对数（第 2 节：半径 ×2.5 → 对数 ×3.06）、"
            "② 每 tile 的列表长度、③ 反向的 atomicAdd 次数</em>。"
            "<strong>所以「剪掉屏幕半径过大的高斯」这一个操作同时改善了"
            "仿射近似的精度、排序成本、渲染成本与训练成本</strong>——"
            "<em>在整套系统里很少见到这么划算的一个旋钮</em>。"),
    ])),

    # ============================================================== 5
    ("imbalance", "整帧时延由最慢的那个 tile 决定", "".join([
        P("GPU 上一个 tile 对应一个 block。**block 之间没有同步，但整帧要等最后一个 block 结束。**"
          "所以有意义的量不是每 tile 的平均工作量，而是分布的尾部。"),
        P("notebook 里量了两个场景。<strong>A</strong> 是一个平滑的、"
          "偏向画面下方的合成分布（20 万高斯、半径中位 6 px、1920×1080）；"
          "<strong>B</strong> 是 notebook 自己那个含「一面墙 + 一个近处物体」的场景。"),
        TABLE(["统计量", "A：平滑分布", "B：含近处大物体（notebook 的场景）"], [
            ["均值", "136.1", "34.4"],
            ["中位", "116", "16"],
            ["P95", "311", "160"],
            ["<strong>最大</strong>", "<strong>364</strong>", "<strong>298</strong>"],
            ["空 tile 比例", "7.9%", "5.3%"],
            ["<strong>最大 / 均值</strong>", "<strong>2.67×</strong>",
             "<strong>8.67×</strong>"],
        ]),
        DUAL(
            "<strong>注意 B 比 A 差三倍多，而 B 才是真实场景的形状。</strong>"
            "<em>A 的分布是平滑的，所以最大值只是均值的 2.67 倍；"
            "而 B 里有一个近处的物体压住十几个 tile，"
            "那几个 tile 的列表长是均值的 8.67 倍</em>。"
            "<strong>所以「按均值估算帧时延」在平滑场景里低估 2.7 倍，"
            "在有近景的场景里低估近 9 倍</strong>——"
            "<em>而任何有前景主体的场景都属于后者</em>。"
            "<strong>空 tile（5–8%）的 block 几乎立刻退出，"
            "它们占的调度资源是浪费的，但代价很小，所以官方没做 tile 合并。</strong>",
            "<strong>而不均衡与提前终止有一个不太直观的互动。</strong>"
            "<em>提前终止在「高斯多、$\\alpha$ 大」的 tile 上收益最大"
            "（近处的实心物体，19/245 就停），"
            "而这些恰好是列表最长的 tile</em>。"
            "<strong>所以提前终止不只是把平均值降下来，它<em>同时</em>把尾部压平了</strong>——"
            "<em>这是两个收益，而后者对帧时延更重要</em>。"
            "<strong>反过来，最糟的 tile 是「列表长、但 $\\alpha$ 都很小」的那种</strong>："
            "<em>薄雾、半透明的植被、训练早期还没收敛的区域</em>。"),
        CALLOUT("warn",
                "<strong>一个实际的性能坑：训练早期 FPS 极低，中后期突然变快。</strong>"
                "<em>原因就是本节——初始化时所有高斯的 $\\alpha$ 都被设成一个小值"
                "（官方用 0.1 的 inverse-sigmoid），于是没有任何 tile 能提前终止；"
                "等不透明度优化上来之后，92% 的工作才开始被省掉</em>。"
                "<strong>所以拿训练早期的 iter/s 去外推总时长会严重高估。</strong>"),
    ])),

    # ============================================================== 6
    ("cost", "每帧的结构性账：钱花在哪，以及 tile 尺寸为什么是 16", "".join([
        P("下面是 500 k 高斯、覆盖半径 8 px、1920×1080 时每帧的<strong>操作计数</strong>。"
          "绝对毫秒数取决于硬件，所以这里只给计数与比值——"
          "<strong>而比值才是能迁移的那部分。</strong>"),
        TABLE(["阶段", "规模", "每帧计数", "正比于"], [
            ["① 预处理（投影 + 协方差 + SH 求值）", "$O(N)$", "0.50 M 次",
             "<strong>高斯数</strong>"],
            ["② 分箱（写 (高斯,tile) 条目）", "$O(P)$", "2.00 M 次写", "$P$"],
            ["③ 基数排序（64 位键，8 位一遍）", "$O(P)$",
             "<strong>2.00 M × 8 遍 = 16.0 M 次扫描</strong>", "$P$"],
            ["④ 载入（每 tile 的列表读一次）", "$O(P)$",
             "2.00 M 个条目 ≈ <strong>72 MB 访存</strong>", "$P$"],
            ["⑤ 渲染算术（<em>不</em>提前终止）", "$O(\\text{像素}\\times P/T)$",
             "<strong>508 M 次高斯-像素求值</strong>", "像素数 × 每 tile 列表长"],
            ["⑤ 渲染算术（提前终止，每像素 19 个）", "同上",
             "<strong>39 M 次（省 92.2%）</strong>", "像素数 × 实际处理数"],
        ]),
        DUAL(
            "<strong>两个比值把整张账说清了。</strong>"
            "<em>① $P/N = 4.0$——分箱与排序的规模是高斯数的 4 倍，"
            "所以「高斯数」不是成本的直接度量，$P$ 才是；"
            "② 渲染求值 / $P$ = 19.7（有终止）vs 254.1（无终止）</em>。"
            "<strong>所以提前终止把「渲染」从压倒性的主项变成了与排序同一量级的一项</strong>——"
            "<em>这也解释了为什么去掉它之后 3DGS 不只是慢一点，而是<strong>不再实时</strong></em>。",
            "<strong>而 tile 尺寸的取舍现在可以精确写出来。</strong>"
            "<em>$P \\propto (2r/T_s+1)^2$ 而 tile 数 $\\propto 1/T_s^2$，"
            "所以每 tile 的列表长 $\\propto (2r/T_s+1)^2 T_s^2$</em>——"
            "<strong>两者往<em>相反</em>方向变，而 16×16 正好在拐点附近：</strong>"),
        TABLE(["配置", "tile 数", "$P$", "每 tile 列表长"], [
            ["<strong>16×16（基准）</strong>", "8160", "2.00 M（1.00×）",
             "245.1（1.00×）"],
            ["8×8", "32400", "<strong>4.50 M（2.25×）</strong>",
             "138.9（<strong>0.57×</strong>）"],
            ["32×32", "2040", "1.12 M（<strong>0.56×</strong>）",
             "<strong>551.5（2.25×）</strong>"],
            ["高斯 ×2（16×16）", "8160", "4.00 M（2.00×）", "490.2（2.00×）"],
            ["半径 ×2.5（16×16）", "8160", "<strong>6.12 M（3.06×）</strong>",
             "<strong>750.6（3.06×）</strong>"],
        ]),
        CALLOUT("paper",
                "<strong>注意最后两行与前三行的性质完全不同。</strong>"
                "<em>改 tile 尺寸是把成本在「排序」与「渲染」之间<strong>搬来搬去</strong>"
                "（一个 ×2.25、另一个 ×0.57，乘积几乎不变）；"
                "而改高斯数或覆盖半径是<strong>两项一起涨</strong></em>。"
                "<strong>所以 tile 尺寸只能调优，而剪枝（控制半径与数量）才能真正降成本</strong>——"
                "<em>这就是模块 04 的题目</em>。"),
    ])),

    # ============================================================== 7
    ("verify", "怎么验证一个光栅化器是对的", "".join([
        P("这一节讲方法，因为 notebook 里就是这么做的，而它对任何自己动手改内核的人都适用。"),
        OL([
            "<strong>与逐像素暴力实现逐位比对——先把近似列全。</strong>"
            "<em>tile 版一共有<strong>三</strong>个近似，而第三个最容易漏："
            "① 提前终止；② tile 内共享顺序；"
            "③ <strong>$3\\sigma$ 包围盒是 tile 对齐的</strong>——"
            "tile 版对该 tile 里的<strong>每个</strong>像素求值，"
            "哪怕那个像素在高斯的精确包围盒之外</em>。"
            "<strong>所以暴力版必须用同一个判定集合才能逐位比对</strong>——"
            "<em>notebook 里的做法是让暴力版<strong>独立地</strong>对每个像素判断"
            "「它所在的 tile 是否落在这个高斯的 tile 区间内」，"
            "完全不用分箱的输出，于是这才是一次真正的交叉验证</em>。"
            "<strong>这样做之后两者严格相等到机器精度。</strong>"
            "<em>而第三个近似本身的影响：把包围盒整体去掉，"
            "最大图像差是 $1.95\\times10^{-3}$，即 <strong>0.50 个 8 bit 色阶</strong>——"
            "小但不为零，且与模块 02 算的「3σ 处 α 衰减 0.0111」量级完全对得上</em>",
            "<strong>关掉近似做消融。</strong>"
            "<em>$T_{\\min}=0$、tile 尺寸 = 1×1（退化成逐像素）、"
            "$3\\sigma$ 截断改成 $\\infty$。每关掉一个，差应当降到零</em>",
            "<strong>梯度用数值差分核对</strong>（模块 01 练习 3 的做法）。"
            "<em>但要注意：提前终止让损失对参数<strong>不再光滑</strong>——"
            "在终止点附近，数值差分与解析梯度会不一致，而这不是 bug</em>",
            "<strong>顺序不变性的反向检查。</strong>"
            "<em>把输入高斯的<strong>数组顺序</strong>打乱（不是深度顺序），"
            "渲染结果应当不变（因为会重新排序）。"
            "如果变了，说明排序键有相等项而排序不稳定</em>——"
            "<strong>这正好抓住第 2 节那个深度位数问题</strong>",
            "<strong>确定性检查。</strong>"
            "<em>同一份输入跑两遍，输出必须逐位相同。"
            "如果不是，说明某处依赖了哈希顺序、未初始化内存，"
            "或（在 GPU 上）依赖了 atomicAdd 的完成次序</em>——"
            "<strong>而最后一种在反向传播里几乎必然发生，"
            "所以「梯度不确定」是正常的，「前向不确定」不是</strong>",
            "<strong>能量守恒检查。</strong>"
            "<em>$\\sum_i T_i\\alpha_i + T_{\\text{final}} = 1$ 必须逐像素成立到机器精度"
            "（模块 01 第 0 节）。提前终止会破坏它，"
            "而破坏的量正好是 $T_{\\min}$ 的上界——所以它也是一个可验证的量</em>",
        ]),
        CALLOUT("paper",
                "<strong>那为什么不干脆逐像素排序，把 popping 彻底解决？算一下就知道。</strong>"
                "<em>1920×1080 有 207 万个像素，而 tile 只有 8160 个——"
                "排序次数差 <strong>254 倍</strong></em>。"
                "<strong>而每次排序的元素个数只从「每 tile 245 个」降到"
                "「每像素几十个」，降不了 254 倍</strong>——"
                "<em>所以逐像素排序的总成本高一个数量级以上</em>。"
                "<strong>StopThePop（2024）的折中是「分层」："
                "在 tile 内按 2×2 或 4×4 的子块重排，"
                "只对顺序真正会翻转的那些高斯做局部修正</strong>，"
                "<em>代价约 2 倍渲染时间，换来 popping 基本消失</em>。"),
        CALLOUT("intuition",
                "<strong>第 4 条值得单独记住，因为它把一个看不见的 bug 变成了一行测试。</strong>"
                "<em>「打乱输入顺序，输出应不变」——"
                "如果深度用 16 位量化，68.75% 的相邻对会因为键相等而顺序未定义，"
                "于是这条测试立刻失败</em>。"
                "<strong>而如果只看图像质量指标，这个 bug 会表现为「PSNR 差了 0.5 dB」，"
                "谁也不会想到是排序键的位数。</strong>"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 03 · 从零写一个 tile 光栅化器

本 notebook 真的写出一个能出图的 tile 光栅化器，并验证它：

1. **分箱**：$3\\sigma$ 包围盒 → (高斯, tile) 对；
2. **一个 64 位键让一次排序同时按 tile 与深度排好**，
   而**深度用 16 位量化会让 68.75% 的相邻对顺序未定义**；
3. **逐 tile 渲染 + 提前终止**，出一张图；
4. **与逐像素暴力实现逐位比对** —— 关掉两个近似后必须严格相等；
5. 负载分布（最大/均值 = 2.67×）与每帧的操作计数；
6. **顺序不变性检查**：打乱输入数组顺序，输出必须不变。

只用 numpy，CPU，离线。分辨率取 640×480 以便在 CPU 上跑得动。"""),

code("""import numpy as np, math
print('numpy', np.__version__)

W_IMG, H_IMG, TS = 640, 480, 16
NX, NY = math.ceil(W_IMG/TS), math.ceil(H_IMG/TS)
NTILE = NX * NY
F, CX, CY = 600.0, W_IMG/2, H_IMG/2
print(f'{W_IMG}x{H_IMG} / {TS}x{TS} = {NX} x {NY} = {NTILE} tiles')
print(f'对照 1920x1080: {math.ceil(1920/16)} x {math.ceil(1080/16)} = '
      f'{math.ceil(1920/16)*math.ceil(1080/16)} tiles')
assert math.ceil(1920/16)*math.ceil(1080/16) == 8160

def quat_to_R(q):
    q = np.asarray(q, float); q = q/np.linalg.norm(q); w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
                     [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])

def cov3d(scale, q):
    M = quat_to_R(q) * np.asarray(scale, float)
    return M @ M.T

def make_scene(n=3000, seed=0):
    '''一个合成场景：一面墙 + 一个近处的物体 + 一些散落的小高斯。'''
    rng = np.random.default_rng(seed)
    mus, scales, quats, alphas, colors = [], [], [], [], []
    # 墙：z=8m 附近的一片
    nw = n//2
    mus.append(np.stack([rng.uniform(-3.0, 3.0, nw), rng.uniform(-2.2, 2.2, nw),
                         8.0 + rng.normal(0, 0.05, nw)], 1))
    scales.append(np.stack([rng.uniform(0.04, 0.10, nw), rng.uniform(0.04, 0.10, nw),
                            rng.uniform(0.004, 0.012, nw)], 1))
    quats.append(rng.normal(0, 1, (nw, 4)))
    alphas.append(rng.uniform(0.4, 0.9, nw))
    colors.append(np.stack([rng.uniform(0.3, 0.5, nw), rng.uniform(0.35, 0.55, nw),
                            rng.uniform(0.45, 0.65, nw)], 1))
    # 近物：z=3m 的一个团
    no = n//3
    mus.append(np.stack([rng.normal(0.5, 0.30, no), rng.normal(-0.2, 0.25, no),
                         3.0 + rng.normal(0, 0.20, no)], 1))
    scales.append(np.exp(rng.normal(np.log(0.035), 0.4, (no, 3))))
    quats.append(rng.normal(0, 1, (no, 4)))
    alphas.append(rng.uniform(0.5, 0.95, no))
    colors.append(np.stack([rng.uniform(0.7, 1.0, no), rng.uniform(0.3, 0.6, no),
                            rng.uniform(0.1, 0.3, no)], 1))
    # 散落
    nr = n - nw - no
    mus.append(np.stack([rng.uniform(-2.5, 2.5, nr), rng.uniform(-1.8, 1.8, nr),
                         rng.uniform(1.5, 12.0, nr)], 1))
    scales.append(np.exp(rng.normal(np.log(0.03), 0.6, (nr, 3))))
    quats.append(rng.normal(0, 1, (nr, 4)))
    alphas.append(rng.uniform(0.1, 0.6, nr))
    colors.append(rng.uniform(0.2, 0.9, (nr, 3)))
    return (np.concatenate(mus), np.concatenate(scales), np.concatenate(quats),
            np.concatenate(alphas), np.concatenate(colors))

MU, SC, QT, AL, CO = make_scene(3000, 0)
print(f'\\n场景：{len(MU)} 个高斯，深度范围 {MU[:,2].min():.2f} ~ {MU[:,2].max():.2f} m')"""),

md("""## 1 · 预处理：投影成 2D 椭圆，算出圆锥系数与包围半径

对每个高斯算出 `(uv, conic, radius, depth, alpha, color)`。
`conic` 是 $\\Sigma'^{-1}$ 的三个独立分量 —— 渲染时只需要它，不需要 $\\Sigma'$ 本身。"""),

code("""def preprocess(mu, sc, qt, al, co, z_near=0.2, dilate=0.3, k_sigma=3.0):
    '''返回一个 dict，只含通过剔除的高斯。'''
    keep = mu[:, 2] > z_near
    mu, sc, qt, al, co = mu[keep], sc[keep], qt[keep], al[keep], co[keep]
    n = len(mu)
    uv = np.stack([CX + F*mu[:, 0]/mu[:, 2], CY + F*mu[:, 1]/mu[:, 2]], 1)
    conic = np.empty((n, 3)); radius = np.empty(n)
    for i in range(n):
        x, y, z = mu[i]
        J = np.array([[F/z, 0.0, -F*x/z**2], [0.0, F/z, -F*y/z**2]])
        S2 = J @ cov3d(sc[i], qt[i]) @ J.T
        S2 = S2 + dilate*np.eye(2)                       # 模块 02 的低通滤波
        det = S2[0,0]*S2[1,1] - S2[0,1]**2
        conic[i] = [S2[1,1]/det, -S2[0,1]/det, S2[0,0]/det]   # Σ'⁻¹ 的 (a,b,c)
        mid = 0.5*(S2[0,0] + S2[1,1])
        lam1 = mid + np.sqrt(max(0.1, mid*mid - det))    # 官方的 max(0.1,·) 保护
        radius[i] = np.ceil(k_sigma*np.sqrt(lam1))
    # 屏幕外剔除
    on = ((uv[:,0] + radius > 0) & (uv[:,0] - radius < W_IMG) &
          (uv[:,1] + radius > 0) & (uv[:,1] - radius < H_IMG))
    return dict(uv=uv[on], conic=conic[on], radius=radius[on],
                depth=mu[on, 2], alpha=al[on], color=co[on])

G = preprocess(MU, SC, QT, AL, CO)
n_g = len(G['uv'])
print(f'通过剔除的高斯 {n_g} / {len(MU)}')
print(f'屏幕半径: 中位 {np.median(G["radius"]):.1f} px  均值 {G["radius"].mean():.1f}'
      f'  P95 {np.percentile(G["radius"],95):.1f}  最大 {G["radius"].max():.0f}')

# conic 必须正定（否则 exp(-½dᵀΣ'⁻¹d) 会发散）
a, b, c = G['conic'].T
det_inv = a*c - b*b
assert np.all(a > 0) and np.all(c > 0) and np.all(det_inv > 0), 'conic 必须正定'
print(f'\\n✓ 全部 {n_g} 个 conic 正定（a>0, c>0, ac-b²>0）')
print(f'  最小的 ac-b² = {det_inv.min():.3e} —— 这是 +0.3I 保证的（模块 02）')"""),

md("""## 2 · 分箱：$3\\sigma$ 包围盒 → (高斯, tile) 对"""),

code("""def tile_range(uv, radius, nx=NX, ny=NY, ts=TS):
    '''包围盒覆盖的 tile 区间 [x0,x1] x [y0,y1]（闭区间，已裁到屏幕内）。'''
    x0 = np.clip(np.floor((uv[0]-radius)/ts).astype(int), 0, nx-1)
    x1 = np.clip(np.floor((uv[0]+radius)/ts).astype(int), 0, nx-1)
    y0 = np.clip(np.floor((uv[1]-radius)/ts).astype(int), 0, ny-1)
    y1 = np.clip(np.floor((uv[1]+radius)/ts).astype(int), 0, ny-1)
    return x0, x1, y0, y1

def bin_gaussians(G):
    '''返回 (gauss_idx, tile_id) 两个等长数组 —— 所有 (高斯,tile) 对。'''
    gi, ti = [], []
    for i in range(len(G['uv'])):
        x0, x1, y0, y1 = tile_range(G['uv'][i], G['radius'][i])
        tx = np.arange(x0, x1+1); ty = np.arange(y0, y1+1)
        t = (ty[:, None]*NX + tx[None, :]).ravel()
        gi.append(np.full(len(t), i)); ti.append(t)
    return np.concatenate(gi), np.concatenate(ti)

gidx, tidx = bin_gaussians(G)
P = len(gidx)
print(f'(高斯,tile) 对总数 P = {P}')
print(f'  P / 高斯数 = {P/n_g:.2f}   每 tile 平均 {P/NTILE:.1f}')

per_g = np.bincount(gidx, minlength=n_g)
print(f'\\n每个高斯覆盖的 tile 数: 中位 {np.median(per_g):.0f}  均值 {per_g.mean():.2f}'
      f'  最大 {per_g.max()}')
# 理论：半径 r 的包围盒覆盖约 (2r/TS+1)² 个 tile
pred = ((2*G['radius']/TS)+1)**2
print(f'理论 (2r/{TS}+1)² 的均值 {pred.mean():.2f}（实测 {per_g.mean():.2f}）')
assert abs(per_g.mean()/pred.mean() - 1) < 0.25, '实测与理论应在 25% 内'
print('✓ 实测与 (2r/TS+1)² 一致（差异来自裁剪与包围盒的整数对齐）')

# 覆盖半径是主控变量
print('\\n覆盖半径对 P 的影响（1920x1080, 50 万高斯）：')
NT_HD = 8160
for r in [4, 8, 20, 100]:
    pr = (2*r/16+1)**2
    print(f'  半径 {r:3d} px: 每高斯 {pr:7.2f} tiles -> P = {500_000*pr/1e6:6.2f}M'
          f'  每 tile {500_000*pr/NT_HD:7.1f}')
print(f'\\n✓ 半径 8 -> 20（2.5×）时 P 涨 {((2*20/16+1)/(2*8/16+1))**2:.2f}×')
print(f'  一个半径 100 px 的高斯抵得上 {((2*100/16+1)/(2*8/16+1))**2:.0f} 个正常高斯')"""),

md("""## 3 · 64 位键：一次排序解决两件事

`key = (tile_id << 32) | depth_bits`。对它排一次序，结果自动是
「按 tile 分组、组内按深度升序」。"""),

code("""def float_to_uint32_monotonic(x):
    '''把**正** float32 按位重解释成 uint32。对正数，位模式与数值同序。'''
    x32 = np.asarray(x, np.float32)
    assert np.all(x32 > 0), '这个技巧只对正数成立（依赖近平面剔除）'
    return x32.view(np.uint32)

def make_keys(tile_ids, depths):
    '''返回 uint64 键。高 32 位是 tile_id，低 32 位是深度的单调编码。'''
    t = np.asarray(tile_ids, np.uint64)
    d = float_to_uint32_monotonic(depths).astype(np.uint64)
    return (t << np.uint64(32)) | d

# 先验证位重解释的单调性
_probe = np.array([1e-6, 0.2, 1.0, 1.5, 7.99, 8.0, 8.01, 1e6], np.float32)
_bits = float_to_uint32_monotonic(_probe)
assert np.all(np.diff(_bits.astype(np.int64)) > 0), '正 float32 的位模式必须与数值同序'
print('float32 位重解释的单调性:')
for v, b in zip(_probe, _bits):
    print(f'  {v:12.6g} -> 0x{b:08x}')
print('✓ 严格单调 —— 所以按 uint32 排序 == 按 float 排序，一位精度都不损失')

keys = make_keys(tidx, G['depth'][gidx])
order = np.argsort(keys, kind='stable')
st, sd = tidx[order], G['depth'][gidx][order]

assert np.all(np.diff(st.astype(np.int64)) >= 0), 'tile_id 必须非降'
same_tile = np.diff(st.astype(np.int64)) == 0
assert np.all(np.diff(sd)[same_tile] >= -1e-7), '同一 tile 内深度必须非降'
print(f'\\n✓ {P} 个键排一次序：tile 非降 ✓，同 tile 内深度非降 ✓')

# 每个 tile 的区间
starts = np.searchsorted(st, np.arange(NTILE), 'left')
ends = np.searchsorted(st, np.arange(NTILE), 'right')
counts = ends - starts
print(f'\\n每 tile 的列表长: 均值 {counts.mean():.1f}  中位 {np.median(counts):.0f}'
      f'  P95 {np.percentile(counts,95):.0f}  最大 {counts.max()}  空 tile {(counts==0).mean():.1%}')
print(f'  最大/均值 = {counts.max()/counts.mean():.2f}×'
      f'  <- GPU 上整帧时延由最慢的 tile 决定')
assert counts.sum() == P"""),

code("""# 深度用多少位量化：碰撞率
def collision_rate(depths, bits):
    '''把深度线性量化到 `bits` 位后，排序键相邻相等（顺序未定义）的比例。'''
    d = np.asarray(depths, float)
    lo, hi = d.min(), d.max()
    q = ((d - lo)/(hi - lo)*(2**bits - 1)).astype(np.uint64)
    return float((np.diff(np.sort(q)) == 0).mean())

# 用一个 0.5~100m 的连续深度分布（比本场景更接近真实户外）
rng_d = np.random.default_rng(0)
depths_wide = rng_d.uniform(0.5, 100.0, 200_000)
print('深度范围 0.5~100 m，20 万个值：')
print('  位数    相邻键相等（顺序未定义）的比例')
rates = {}
for bits in [16, 20, 24, 32]:
    r = collision_rate(depths_wide, bits); rates[bits] = r
    print(f'   {bits:2d}     {r:9.4%}')

assert rates[16] > 0.6, f'16 位应有 60%+ 的碰撞，实测 {rates[16]:.2%}'
assert rates[32] < 1e-3, f'32 位应几乎无碰撞，实测 {rates[32]:.4%}'
assert rates[16] > rates[20] > rates[24] > rates[32]
print(f'\\n✓ 16 位: {rates[16]:.2%} 的相邻对顺序**未定义**')
print(f'  而模块 01 量过，打乱顺序的中位偏差是 19.6% —— 所以这不是无害的精度损失')
print(f'  32 位: {rates[32]:.4%}。官方更进一步：直接位重解释 float32，零精度损失')

# 碰撞的直接后果：排序不稳定时输出会变
print('\\n演示：把深度量化到 16 位，再打乱输入顺序，输出会不会变？')
d_small = G['depth'][gidx]
lo, hi = d_small.min(), d_small.max()
q16 = ((d_small - lo)/(hi - lo)*(2**16-1)).astype(np.uint64)
key16 = (tidx.astype(np.uint64) << np.uint64(32)) | q16
perm = np.random.default_rng(3).permutation(P)
o_a = np.argsort(key16, kind='stable')
o_b = perm[np.argsort(key16[perm], kind='stable')]
n_diff = int((G['depth'][gidx][o_a] != G['depth'][gidx][o_b]).sum())
print(f'  16 位键：打乱输入后，{n_diff}/{P} 个位置的深度不同 ({n_diff/P:.2%})')
o_a32 = np.argsort(keys, kind='stable')
o_b32 = perm[np.argsort(keys[perm], kind='stable')]
n_diff32 = int((G['depth'][gidx][o_a32] != G['depth'][gidx][o_b32]).sum())
print(f'  32 位键：{n_diff32}/{P} ({n_diff32/P:.2%})')
assert n_diff > 0, '16 位键下打乱输入必须改变排序结果'
print('\\n✓ 这就是「顺序不变性检查」能抓到的 bug —— 而它只看 PSNR 是看不出来的')"""),

md("""## 4 · 逐 tile 渲染 + 提前终止"""),

code("""def render_tiles(G, gidx, tidx, T_min=1e-4, alpha_min=1.0/255,
                 shared_order=True, bg=(0.05, 0.05, 0.08)):
    '''逐 tile 渲染。返回 (img, T_final, n_processed)。
    shared_order=False 时退化为逐像素各自排序（关掉那个近似）。'''
    keys = make_keys(tidx, G['depth'][gidx])
    order = np.argsort(keys, kind='stable')
    g_s, t_s = gidx[order], tidx[order]
    starts = np.searchsorted(t_s, np.arange(NTILE), 'left')
    ends = np.searchsorted(t_s, np.arange(NTILE), 'right')

    img = np.zeros((H_IMG, W_IMG, 3))
    Tmap = np.ones((H_IMG, W_IMG))
    n_proc = np.zeros((H_IMG, W_IMG), int)

    for tid in range(NTILE):
        s, e = starts[tid], ends[tid]
        if s == e:
            continue
        ty, tx = divmod(tid, NX)
        y0, y1 = ty*TS, min((ty+1)*TS, H_IMG)
        x0, x1 = tx*TS, min((tx+1)*TS, W_IMG)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        T = np.ones(yy.shape); acc = np.zeros(yy.shape + (3,))
        cnt = np.zeros(yy.shape, int)
        for k in range(s, e):
            gi = g_s[k]
            live = T >= T_min                       # 提前终止（逐像素）
            if not live.any():
                break
            dx = xx - G['uv'][gi, 0]; dy = yy - G['uv'][gi, 1]
            a_, b_, c_ = G['conic'][gi]
            m2 = a_*dx*dx + 2*b_*dx*dy + c_*dy*dy
            al = G['alpha'][gi] * np.exp(-0.5*m2)
            use = live & (al >= alpha_min)
            if not use.any():
                continue
            w = np.where(use, T*al, 0.0)
            acc += w[..., None] * G['color'][gi]
            T = np.where(use, T*(1-al), T)
            cnt += use
        img[y0:y1, x0:x1] = acc
        Tmap[y0:y1, x0:x1] = T
        n_proc[y0:y1, x0:x1] = cnt
    img = img + Tmap[..., None]*np.array(bg)        # 合成背景
    return img, Tmap, n_proc

import time
t0 = time.time()
img, Tmap, nproc = render_tiles(G, gidx, tidx)
print(f'渲染完成 {time.time()-t0:.2f} s')
print(f'累积不透明度 A = 1-T: 均值 {1-Tmap.mean():.4f}  '
      f'A>0.99 的像素 {(1-Tmap > 0.99).mean():.1%}')
print(f'每像素实际处理的高斯数: 均值 {nproc.mean():.1f}  中位 {np.median(nproc):.0f}'
      f'  P95 {np.percentile(nproc,95):.0f}  最大 {nproc.max()}')

# 与「不提前终止」对比
_, _, nproc_full = render_tiles(G, gidx, tidx, T_min=0.0, alpha_min=0.0)
print(f'\\n不提前终止时: 均值 {nproc_full.mean():.1f}  最大 {nproc_full.max()}')
saved = 1 - nproc.sum()/nproc_full.sum()
print(f'提前终止省下 {saved:.1%} 的高斯-像素求值')
assert saved > 0.3, f'应至少省下 30%，实测 {saved:.1%}'
print('（本合成场景的 α 偏小、且大片背景永不饱和，所以低于 245 个高斯那个理想例子的 92.2%）')

print('\\n图像（. < 0.15 < : < 0.35 < o < 0.6 < #）：')
lum = img.mean(2)
for r in range(0, H_IMG, 20):
    line = ''.join('.' if lum[r,c] < 0.15 else (':' if lum[r,c] < 0.35 else
                   ('o' if lum[r,c] < 0.6 else '#')) for c in range(0, W_IMG, 8))
    print('  ' + line)"""),

md("""## 5 · 与逐像素暴力实现逐位比对

tile 版一共有**三个**近似，第三个很容易被忽略：

1. **提前终止**（`T_min`、`alpha_min`）；
2. **tile 内共享一个顺序**（本场景里恰好与全局深度序一致，所以这一项此处为零）；
3. **$3\\sigma$ 包围盒是 tile 对齐的** —— tile 版对该 tile 里的**每个**像素都求值，
   哪怕那个像素在高斯的精确包围盒之外。

所以暴力版必须用**同一个判定集合**才能逐位比对：
它独立地对每个像素算出「该像素所在的 tile 是否落在这个高斯的 tile 区间内」。"""),

code("""def render_brute(G, T_min=0.0, alpha_min=0.0, bg=(0.05, 0.05, 0.08),
                 step=8, use_tile_box=True):
    '''逐像素暴力：每个像素独立遍历全部高斯（全局深度序）、独立判定包含、合成。
    use_tile_box=True 时用与 tile 版**相同**的判据（该像素所在 tile 是否在高斯的 tile 区间内）；
    False 时不做任何包围盒截断（用来量出这个截断本身的影响）。
    step 只算一个稀疏的像素子集，否则太慢。'''
    order = np.argsort(G['depth'], kind='stable')          # 全局深度序
    img = np.zeros((H_IMG//step, W_IMG//step, 3))
    Tm = np.ones((H_IMG//step, W_IMG//step))
    # 每个高斯的 tile 区间（独立算，不用 bin_gaussians 的结果）
    box = [tile_range(G['uv'][i], G['radius'][i]) for i in range(len(G['uv']))]
    for iy, y in enumerate(range(0, H_IMG, step)):
        for ix, x in enumerate(range(0, W_IMG, step)):
            my_tx, my_ty = x//TS, y//TS
            T = 1.0; acc = np.zeros(3)
            for gi in order:
                if T < T_min:
                    break
                if use_tile_box:
                    bx0, bx1, by0, by1 = box[gi]
                    if not (bx0 <= my_tx <= bx1 and by0 <= my_ty <= by1):
                        continue
                dx = x - G['uv'][gi, 0]; dy = y - G['uv'][gi, 1]
                a_, b_, c_ = G['conic'][gi]
                al = G['alpha'][gi]*np.exp(-0.5*(a_*dx*dx + 2*b_*dx*dy + c_*dy*dy))
                if al < alpha_min:
                    continue
                acc += T*al*G['color'][gi]; T *= (1-al)
            img[iy, ix] = acc; Tm[iy, ix] = T
    return img + Tm[..., None]*np.array(bg), Tm

print('关掉提前终止（T_min=0, alpha_min=0），用同一判定集合比对稀疏像素子集...')
t0 = time.time()
img_b, Tm_b = render_brute(G, step=16, use_tile_box=True)
print(f'暴力版 {time.time()-t0:.1f} s（{(H_IMG//16)*(W_IMG//16)} 个像素）')

img_t, Tmap_t, _ = render_tiles(G, gidx, tidx, T_min=0.0, alpha_min=0.0)
sub = img_t[::16, ::16]
sub_T = Tmap_t[::16, ::16]
d_img = np.abs(sub - img_b).max()
d_T = np.abs(sub_T - Tm_b).max()
print(f'\\n图像最大绝对差 {d_img:.3e}')
print(f'透射率最大绝对差 {d_T:.3e}')
assert d_img < 1e-12, f'关掉近似后必须逐位相等，实测 {d_img:.3e}'
assert d_T < 1e-12
print('✓ **严格相等到机器精度** —— 说明 tile 版的分箱、键、tile 区间划分全部正确')
print('  （暴力版独立地对每个像素判定包含关系，没有用 bin_gaussians 的任何输出，')
print('   所以这确实是一次交叉验证，而不是把同一段逻辑跑两遍）')

# 那么第三个近似（tile 对齐的 3σ 包围盒）本身有多大影响？
print('\\n第三个近似：tile 对齐的 3σ 包围盒。把它整体去掉试试...')
t0 = time.time()
img_nb, Tm_nb = render_brute(G, step=32, use_tile_box=False)
print(f'  无任何包围盒的暴力版 {time.time()-t0:.1f} s')
img_wb, Tm_wb = render_brute(G, step=32, use_tile_box=True)
d_box = np.abs(img_wb - img_nb).max()
print(f'  有盒 vs 无盒 的最大差 {d_box:.3e}（相当于 {d_box*255:.2f} 个 8bit 色阶）')
assert d_box > 0, '包围盒确实是一个近似，不该恰好为零'
assert d_box < 0.02, f'但它应当很小，实测 {d_box:.3e}'
print('  ✓ 3σ 截断的影响是 %.2f 个色阶量级 —— 小，但**不为零**。' % (d_box*255))
print('    而模块 02 量过：3σ 处的 α 衰减因子 0.0111，对 α≈0.9 的高斯仍有 2.8 个色阶，')
print('    所以这个量级完全对得上，不是数值噪声。')

# 能量守恒：Σw + T_final = 1
w_sum = (img_t - Tmap_t[..., None]*np.array([0.05,0.05,0.08]))
# 用一个全白颜色重渲一遍来直接测权重和
G_white = dict(G); G_white['color'] = np.ones_like(G['color'])
img_w, Tm_w, _ = render_tiles(G_white, gidx, tidx, T_min=0.0, alpha_min=0.0, bg=(0,0,0))
resid = np.abs(img_w[..., 0] + Tm_w - 1.0).max()
print(f'\\n能量守恒 |Σw + T_final - 1| 的最大值 {resid:.3e}')
assert resid < 1e-12, '必须逐像素守恒'
print('✓ 逐像素守恒到机器精度')

# 而开了提前终止后，守恒被破坏，破坏量恰好被 T_min 约束
for tm in [1e-2, 1e-4]:
    img_w2, Tm_w2, _ = render_tiles(G_white, gidx, tidx, T_min=tm, alpha_min=0.0, bg=(0,0,0))
    r2 = np.abs(img_w2[..., 0] + Tm_w2 - 1.0).max()
    print(f'  T_min={tm:.0e}: 守恒残差最大 {r2:.3e}  (上界 {tm:.0e})')
    assert r2 <= tm + 1e-12, f'残差必须被 T_min 约束'
print('✓ 提前终止破坏守恒，而破坏量严格被 T_min 约束 —— 这也是一个可验证的量')"""),

md("""## 6 · 顺序不变性与每帧的操作计数"""),

code("""# ① 打乱输入数组顺序，输出必须不变（因为会重新排序）
perm = np.random.default_rng(7).permutation(n_g)
G_p = {k: v[perm] for k, v in G.items()}
inv = np.empty(n_g, int); inv[perm] = np.arange(n_g)
gidx_p, tidx_p = bin_gaussians(G_p)
img_p, _, _ = render_tiles(G_p, gidx_p, tidx_p, T_min=0.0, alpha_min=0.0)
d = np.abs(img_p - img_t).max()
print(f'打乱输入数组顺序后，图像最大差 {d:.3e}')
assert d < 1e-12, f'必须完全不变，实测 {d:.3e}（说明排序键有相等项）'
print('✓ 完全不变 —— 说明 32 位深度键下没有影响结果的相等项')

# ② 每帧的操作计数（换算到 1920x1080 / 50 万高斯）
print('\\n每帧操作计数（1920x1080, 50 万高斯, 半径 8 px）：')
NG_HD, R_HD = 500_000, 8
NT_HD, NPIX_HD = 8160, 1920*1080
per_hd = (2*R_HD/16+1)**2
P_HD = NG_HD*per_hd
bytes_each = 4*2 + 4*3 + 4*1 + 4*3          # uv + conic + alpha + rgb
print(f'  ① 预处理            {NG_HD/1e6:6.2f} M 次')
print(f'  ② 分箱写条目        {P_HD/1e6:6.2f} M 次')
print(f'  ③ 基数排序(8位/遍)  {P_HD/1e6:6.2f} M × 8 = {P_HD*8/1e6:.1f} M 次扫描')
print(f'  ④ 载入条目          {P_HD/1e6:6.2f} M 个 ≈ {P_HD*bytes_each/1e6:.0f} MB 访存')
print(f'  ⑤ 渲染(不终止)      {NPIX_HD*P_HD/NT_HD/1e6:6.0f} M 次高斯-像素求值')
print(f'     渲染(每像素 19)  {NPIX_HD*19/1e6:6.0f} M 次  -> 省 {1-19/(P_HD/NT_HD):.1%}')
print(f'\\n  P/高斯数 = {P_HD/NG_HD:.1f}   渲染求值/P = {NPIX_HD*19/P_HD:.1f}'
      f'（不终止时 {NPIX_HD*(P_HD/NT_HD)/P_HD:.1f}）')
assert abs(P_HD/NG_HD - 4.0) < 1e-9

# ③ 负载不均衡：本场景 + 一个 1920x1080 的场景
print('\\n负载不均衡（本场景 640x480, 2940 个高斯）：')
print(f'  每 tile 列表长: 均值 {counts.mean():.1f}  中位 {np.median(counts):.0f}'
      f'  P95 {np.percentile(counts,95):.0f}  最大 {counts.max()}')
print(f'  最大/均值 = {counts.max()/counts.mean():.2f}×   空 tile {(counts==0).mean():.1%}')

# 换一个 1920x1080、偏向画面下方（地面与物体在下、天空在上）的分布
rng_hd = np.random.default_rng(1)
NG_L = 200_000
nx_hd, ny_hd = math.ceil(1920/16), math.ceil(1080/16)
gx = rng_hd.uniform(0, 1920, NG_L)
gy = 1080*(1 - rng_hd.beta(1.6, 4.0, NG_L))          # 偏向下方
gr = np.abs(rng_hd.lognormal(np.log(6), 0.8, NG_L)) + 1
cnt_hd = np.zeros((ny_hd, nx_hd), np.int64)
for x, y, r in zip(gx, gy, gr):
    x0 = max(0, int((x-r)//16)); x1 = min(nx_hd-1, int((x+r)//16))
    y0 = max(0, int((y-r)//16)); y1 = min(ny_hd-1, int((y+r)//16))
    cnt_hd[y0:y1+1, x0:x1+1] += 1
ch = cnt_hd.ravel()
print(f'\\n1920x1080, {NG_L} 个高斯, 半径中位 6 px, 分布偏向画面下方：')
print(f'  每 tile: 均值 {ch.mean():.1f}  中位 {np.median(ch):.0f}'
      f'  P95 {np.percentile(ch,95):.0f}  最大 {ch.max()}  最小 {ch.min()}')
print(f'  最大/均值 = {ch.max()/ch.mean():.2f}×   空 tile {(ch==0).mean():.1%}')
assert ch.max()/ch.mean() > 2.0, '不均衡比应大于 2'
assert counts.max()/counts.mean() > ch.max()/ch.mean(), \\
    '本场景（有近处大物体）应比这个平滑分布更不均衡'
print(f'\\n✓ 两个场景的不均衡比分别是 {counts.max()/counts.mean():.2f}× 与 {ch.max()/ch.mean():.2f}×。')
print('  本场景更糟，因为它有一个近处的大物体压住十几个 tile ——')
print('  而这正是真实场景的常态，平滑的合成分布反而低估了不均衡')

# ④ tile 尺寸的取舍
print('\\ntile 尺寸的取舍（同一场景）：')
print('  tile     tiles      P          每 tile 列表长')
base = None
for ts in [8, 16, 32]:
    nt = math.ceil(1920/ts)*math.ceil(1080/ts)
    pr = (2*R_HD/ts+1)**2; pp = NG_HD*pr
    if base is None:
        base = (pp, pp/nt)
    print(f'  {ts:2d}x{ts:<2d}  {nt:7d}   {pp/1e6:6.2f}M ({pp/base[0]:5.2f}×)'
          f'   {pp/nt:8.1f} ({(pp/nt)/base[1]:5.2f}×)')
_p8 = NG_HD*(2*R_HD/8+1)**2; _n8 = math.ceil(1920/8)*math.ceil(1080/8)
_p32 = NG_HD*(2*R_HD/32+1)**2; _n32 = math.ceil(1920/32)*math.ceil(1080/32)
assert _p8 > P_HD and (_p8/_n8) < (P_HD/NT_HD), '小 tile：P 变大但列表变短'
assert _p32 < P_HD and (_p32/_n32) > (P_HD/NT_HD), '大 tile：P 变小但列表变长'
print('\\n✓ 改 tile 尺寸是把成本在「排序」与「渲染」之间搬来搬去，两项方向相反；')
print('  而改高斯数或覆盖半径是**两项一起涨** —— 所以只有剪枝能真正降成本（模块 04）')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 包围盒到 tile 区间

实现 `my_tile_range(uv, radius, nx, ny, ts)`，返回 `(x0, x1, y0, y1)` —— **闭区间**，
且已裁剪到 `[0, nx-1] × [0, ny-1]`。"""),

code("""def my_tile_range(uv, radius, nx=NX, ny=NY, ts=TS):
    '''返回覆盖的 tile 闭区间 (x0, x1, y0, y1)，已裁剪。'''
    # TODO: x0 = clip(floor((uv[0]-radius)/ts), 0, nx-1)
    #       x1 = clip(floor((uv[0]+radius)/ts), 0, nx-1)   <- 用 +radius，且是 floor
    #       y 同理。返回 int。
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
# ① 完全在中心的小高斯只覆盖 1 个 tile
_r = my_tile_range(np.array([8.0, 8.0]), 1.0)
assert _r == (0, 0, 0, 0), f'应只覆盖 tile (0,0)，实得 {_r}'
# ② 正好跨越 tile 边界
_r = my_tile_range(np.array([16.0, 16.0]), 1.0)
assert _r == (0, 1, 0, 1), f'跨边界应覆盖 2x2，实得 {_r}'
# ③ 屏幕外的负坐标必须被裁到 0
_r = my_tile_range(np.array([-100.0, -100.0]), 5.0)
assert _r == (0, 0, 0, 0), f'负坐标应裁到 0，实得 {_r}'
# ④ 超出右下角必须被裁到 nx-1 / ny-1
_r = my_tile_range(np.array([W_IMG+500.0, H_IMG+500.0]), 5.0)
assert _r == (NX-1, NX-1, NY-1, NY-1), f'应裁到右下角，实得 {_r}'
# ⑤ 一个覆盖整屏的巨大高斯
_r = my_tile_range(np.array([CX, CY]), 10_000.0)
assert _r == (0, NX-1, 0, NY-1), f'应覆盖全部 tile，实得 {_r}'
# ⑥ 与参考实现在随机输入上一致
_rg = np.random.default_rng(2)
for _ in range(3000):
    _uv = _rg.uniform(-50, W_IMG+50, 2)
    _rad = _rg.uniform(0.5, 60)
    assert my_tile_range(_uv, _rad) == tuple(int(v) for v in tile_range(_uv, _rad)), \\
        f'与参考不符: uv={_uv} r={_rad}'
# ⑦ tile 数与 (2r/ts+1)² 的量级一致
_cnt = []
for _ in range(2000):
    _uv = _rg.uniform(100, W_IMG-100, 2); _rad = _rg.uniform(2, 30)
    _x0, _x1, _y0, _y1 = my_tile_range(_uv, _rad)
    _cnt.append(((_x1-_x0+1)*(_y1-_y0+1), (2*_rad/TS+1)**2))
_cnt = np.array(_cnt)
_ratio = _cnt[:, 0].mean()/_cnt[:, 1].mean()
assert 0.85 < _ratio < 1.35, f'实测/理论 = {_ratio:.3f}，应接近 1'
print(f'✓ 练习 1 通过：7 类边界情形 + 3000 组随机输入；'
      f'实测 tile 数 / (2r/16+1)² = {_ratio:.3f}')"""),

md("""### 📖 参考答案 1"""),

code("""def my_tile_range(uv, radius, nx=NX, ny=NY, ts=TS):
    x0 = int(np.clip(np.floor((uv[0]-radius)/ts), 0, nx-1))
    x1 = int(np.clip(np.floor((uv[0]+radius)/ts), 0, nx-1))
    y0 = int(np.clip(np.floor((uv[1]-radius)/ts), 0, ny-1))
    y1 = int(np.clip(np.floor((uv[1]+radius)/ts), 0, ny-1))
    return x0, x1, y0, y1

print('参考答案 1 已定义')
print('两个容易错的地方：')
print('  ① 上界要用 floor((uv+r)/ts) 而不是 ceil。因为 tile 编号是「像素//ts」，')
print('     所以 x=16 属于 tile 1，而 ceil(16/16)=1 恰好对，但 x=15 时 ceil 给 1（错，应是 0）。')
print('  ② 裁剪必须在 floor **之后**。先裁 uv 再 floor 会把「部分在屏幕外」的高斯')
print('     的覆盖范围算小，导致边缘的 tile 漏掉它 —— 表现为画面四边有一条缺失。')"""),

md("""### ✏️ 练习 2 · 64 位排序键

实现 `my_keys(tile_ids, depths)`：返回 `uint64` 键，高 32 位是 `tile_id`，
低 32 位是深度的**单调**编码（用 float32 位重解释，不要线性量化）。"""),

code("""def my_keys(tile_ids, depths):
    '''返回 uint64 键数组。'''
    # TODO: 1) t = tile_ids 转 np.uint64
    #       2) d = np.asarray(depths, np.float32).view(np.uint32).astype(np.uint64)
    #          （先断言 depths 全为正 —— 这个技巧只对正数成立）
    #       3) 返回 (t << np.uint64(32)) | d
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_t = np.array([5, 5, 5, 2, 2, 9], np.uint64)
_d = np.array([3.0, 1.0, 2.0, 8.0, 0.5, 4.0], np.float32)
_k = my_keys(_t, _d)
assert _k.dtype == np.uint64, f'必须是 uint64，实得 {_k.dtype}'
_o = np.argsort(_k, kind='stable')
assert list(_t[_o]) == [2, 2, 5, 5, 5, 9], f'tile 必须成组升序，实得 {list(_t[_o])}'
assert list(_d[_o]) == [0.5, 8.0, 1.0, 2.0, 3.0, 4.0], \\
    f'组内深度必须升序，实得 {list(_d[_o])}'

# 高 32 位必须精确恢复 tile_id
assert list((_k >> np.uint64(32)).astype(np.int64)) == list(_t.astype(np.int64))
# 低 32 位必须精确恢复深度
_lo = (_k & np.uint64(0xFFFFFFFF)).astype(np.uint32)
assert np.array_equal(_lo.view(np.float32), _d), '低 32 位必须无损恢复 float32 深度'

# 大规模：与参考实现一致，且排序结果正确
_kb = my_keys(tidx, G['depth'][gidx])
assert np.array_equal(_kb, make_keys(tidx, G['depth'][gidx])), '与参考实现不符'
_ob = np.argsort(_kb, kind='stable')
_st, _sd = tidx[_ob], G['depth'][gidx][_ob]
assert np.all(np.diff(_st.astype(np.int64)) >= 0)
_sm = np.diff(_st.astype(np.int64)) == 0
assert np.all(np.diff(_sd)[_sm] >= -1e-7)

# 打乱输入后排序结果必须一致（没有影响结果的相等键）
_pm = np.random.default_rng(3).permutation(len(_kb))
_oa = G['depth'][gidx][np.argsort(_kb, kind='stable')]
_obp = G['depth'][gidx][_pm[np.argsort(_kb[_pm], kind='stable')]]
assert np.array_equal(_oa, _obp), '打乱输入不该改变排序结果'

# 负深度必须被拒绝
try:
    my_keys(np.array([0], np.uint64), np.array([-1.0], np.float32))
    raise SystemExit('负深度必须被拒绝（位重解释对负数不单调）')
except AssertionError:
    pass
print(f'✓ 练习 2 通过：{len(_kb)} 个键排序正确；高/低 32 位可无损恢复；'
      f'打乱输入不变；负深度被拒绝')"""),

md("""### 📖 参考答案 2"""),

code("""def my_keys(tile_ids, depths):
    d32 = np.asarray(depths, np.float32)
    assert np.all(d32 > 0), '位重解释只对正 float32 单调（依赖近平面剔除 z>0.2）'
    t = np.asarray(tile_ids, np.uint64)
    d = d32.view(np.uint32).astype(np.uint64)
    return (t << np.uint64(32)) | d

print('参考答案 2 已定义')
print('要点一：为什么用位重解释而不是线性量化 —— 量化到 16 位时，')
print('       0.5~100 m 范围内有 68.75% 的相邻对键相等，顺序变成未定义。')
print('要点二：这个技巧依赖「深度全为正」，而那是**近平面剔除**保证的。')
print('       两个看起来无关的实现细节其实是耦合的：去掉 z>0.2 的剔除，排序就会错。')
print('       （IEEE 754：正 float 的符号位为 0，指数在高位、尾数在低位，')
print('        所以位模式作为无符号整数与数值同序。负数会反序。）')"""),

md("""### ✏️ 练习 3 · 一个 tile 的渲染（含提前终止）

实现 `my_render_tile(G, g_list, y0, y1, x0, x1, T_min, alpha_min)`，
返回 `(acc, T, cnt)`：该 tile 内每个像素的累积颜色、剩余透射率、实际处理的高斯数。
`g_list` 是**已按深度排好序**的高斯索引。"""),

code("""def my_render_tile(G, g_list, y0, y1, x0, x1, T_min=1e-4, alpha_min=1.0/255):
    '''返回 (acc (h,w,3), T (h,w), cnt (h,w))。'''
    # TODO: yy, xx = np.mgrid[y0:y1, x0:x1]；T=ones, acc=zeros, cnt=zeros(int)
    #  按 g_list 顺序遍历 gi：
    #    live = T >= T_min；若 not live.any(): break
    #    dx = xx - uv[gi,0]; dy = yy - uv[gi,1]
    #    a,b,c = conic[gi]；m2 = a*dx² + 2b*dx*dy + c*dy²
    #    al = alpha[gi]*exp(-0.5*m2)
    #    use = live & (al >= alpha_min)；若 not use.any(): continue
    #    acc += where(use, T*al, 0)[...,None]*color[gi]
    #    T = where(use, T*(1-al), T)；cnt += use
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_keys3 = make_keys(tidx, G['depth'][gidx])
_o3 = np.argsort(_keys3, kind='stable')
_gs, _ts = gidx[_o3], tidx[_o3]
_s3 = np.searchsorted(_ts, np.arange(NTILE), 'left')
_e3 = np.searchsorted(_ts, np.arange(NTILE), 'right')
# 挑几个非空的 tile
_busy = np.argsort(_e3-_s3)[::-1][:6]

for _tid in _busy:
    _ty, _tx = divmod(int(_tid), NX)
    _y0, _y1 = _ty*TS, min((_ty+1)*TS, H_IMG)
    _x0, _x1 = _tx*TS, min((_tx+1)*TS, W_IMG)
    _gl = _gs[_s3[_tid]:_e3[_tid]]

    # ① 关掉两个近似时，必须与完整合成逐位相等
    _acc, _T, _cnt = my_render_tile(G, _gl, _y0, _y1, _x0, _x1, 0.0, 0.0)
    assert _acc.shape == (_y1-_y0, _x1-_x0, 3) and _T.shape == _acc.shape[:2]
    assert np.all(_cnt == len(_gl)), '关掉近似时每个像素都该处理全部高斯'
    # 能量守恒（用全白颜色）
    _Gw = dict(G); _Gw['color'] = np.ones_like(G['color'])
    _accw, _Tw, _ = my_render_tile(_Gw, _gl, _y0, _y1, _x0, _x1, 0.0, 0.0)
    assert np.abs(_accw[..., 0] + _Tw - 1.0).max() < 1e-12, '必须逐像素守恒'

    # ② 提前终止：误差被 T_min 约束，且处理的高斯数不增加
    for _tm in [1e-2, 1e-4]:
        _a2, _T2, _c2 = my_render_tile(G, _gl, _y0, _y1, _x0, _x1, _tm, 0.0)
        assert np.abs(_a2 - _acc).max() <= _tm + 1e-12, \\
            f'T_min={_tm} 时误差 {np.abs(_a2-_acc).max():.3e} 超上界'
        assert np.all(_c2 <= _cnt), '提前终止不该增加处理量'

    # ③ T 单调不增、落在 (0,1]
    assert np.all(_T > 0) and np.all(_T <= 1.0 + 1e-15)
    # ④ 与本 notebook 的整帧实现在该 tile 上一致
    assert np.abs(_acc - (img_t - Tmap_t[..., None]*np.array([0.05,0.05,0.08]))
                  [_y0:_y1, _x0:_x1]).max() < 1e-12, '与整帧实现不一致'

# ⑤ 空列表
_ae, _Te, _ce = my_render_tile(G, np.array([], int), 0, 16, 0, 16, 1e-4, 0.0)
assert np.allclose(_ae, 0) and np.allclose(_Te, 1.0) and np.all(_ce == 0)
print(f'✓ 练习 3 通过：6 个最繁忙的 tile（列表长 {int(_e3[_busy[0]]-_s3[_busy[0]])} '
      f'~ {int(_e3[_busy[-1]]-_s3[_busy[-1]])}）；守恒、误差上界、单调性、空列表全部通过')"""),

md("""### 📖 参考答案 3"""),

code("""def my_render_tile(G, g_list, y0, y1, x0, x1, T_min=1e-4, alpha_min=1.0/255):
    yy, xx = np.mgrid[y0:y1, x0:x1]
    T = np.ones(yy.shape)
    acc = np.zeros(yy.shape + (3,))
    cnt = np.zeros(yy.shape, int)
    for gi in g_list:
        live = T >= T_min
        if not live.any():
            break
        dx = xx - G['uv'][gi, 0]; dy = yy - G['uv'][gi, 1]
        a_, b_, c_ = G['conic'][gi]
        m2 = a_*dx*dx + 2*b_*dx*dy + c_*dy*dy
        al = G['alpha'][gi] * np.exp(-0.5*m2)
        use = live & (al >= alpha_min)
        if not use.any():
            continue
        acc += np.where(use, T*al, 0.0)[..., None] * G['color'][gi]
        T = np.where(use, T*(1-al), T)
        cnt += use
    return acc, T, cnt

print('参考答案 3 已定义')
print('要点一：`live = T >= T_min` 要在**处理之前**判，否则误差上界不再是 T_min。')
print('要点二：`break` 与 `continue` 的区别是本函数最容易错的地方 ——')
print('       T < T_min 时 break（后面更远的高斯只会更被遮挡）；')
print('       α < alpha_min 时 continue（这个高斯太淡，但后面的可能不淡）。')
print('       写反了：break 太早会丢内容，continue 代替 break 会白算 92% 的工作。')
print('要点三：GPU 上的 live 是 per-thread 的 break，而 `not live.any()` 对应')
print('       __syncthreads_count(done)==256 那个 block 级退出 —— 省访存的那一层。')"""),

md("""### ✏️ 练习 4 · 深度量化位数的碰撞率

实现 `my_collision(depths, bits)`：把 `depths` 线性量化到 `bits` 位后，
返回**排序后相邻键相等**的比例（即顺序未定义的相邻对占比）。"""),

code("""def my_collision(depths, bits):
    '''线性量化到 bits 位后，排序后相邻相等的比例。'''
    # TODO: lo, hi = depths.min(), depths.max()
    #       q = ((depths-lo)/(hi-lo)*(2**bits-1)).astype(np.uint64)
    #       返回 (np.diff(np.sort(q)) == 0).mean()
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_dw = np.random.default_rng(0).uniform(0.5, 100.0, 200_000)
_r = {b: my_collision(_dw, b) for b in [16, 20, 24, 32]}

for _b, _v in _r.items():
    assert 0.0 <= _v <= 1.0, f'{_b} 位: {_v} 不是比例'
# 位数越多碰撞越少（严格单调）
assert _r[16] > _r[20] > _r[24] > _r[32], f'必须单调: {_r}'
# 具体量级
assert 0.60 < _r[16] < 0.75, f'16 位应在 60~75%，实测 {_r[16]:.2%}'
assert _r[32] < 1e-3, f'32 位应 <0.1%，实测 {_r[32]:.4%}'
# 与参考实现一致
for _b in [16, 24, 32]:
    assert abs(my_collision(_dw, _b) - collision_rate(_dw, _b)) < 1e-12

# 理论核对：n 个值均匀落进 m 个桶时，碰撞率 ≈ 1 - m/n·(1-exp(-n/m)) 的近似不好用，
# 直接用「非空桶数」核对：相邻相等的对数 = n - 非空桶数
for _b in [16, 20]:
    _lo, _hi = _dw.min(), _dw.max()
    _q = ((_dw-_lo)/(_hi-_lo)*(2**_b-1)).astype(np.uint64)
    _n_distinct = len(np.unique(_q))
    _expect = (len(_dw) - _n_distinct) / (len(_dw) - 1)
    assert abs(my_collision(_dw, _b) - _expect) < 1e-9, \\
        f'{_b} 位: 碰撞率应等于 (n - 不同值个数)/(n-1)'

# 极端：1 位时几乎全部碰撞
assert my_collision(_dw, 1) > 0.99
# 深度全相同时，任何位数都是 100% 碰撞
assert my_collision(np.full(1000, 7.0), 32) == 1.0
print(f'✓ 练习 4 通过：16 位 {_r[16]:.2%} / 20 位 {_r[20]:.2%} / '
      f'24 位 {_r[24]:.2%} / 32 位 {_r[32]:.4%}；与「(n-不同值数)/(n-1)」恒等式一致')"""),

md("""### 📖 参考答案 4"""),

code("""def my_collision(depths, bits):
    d = np.asarray(depths, float)
    lo, hi = d.min(), d.max()
    if hi == lo:
        return 1.0
    q = ((d - lo)/(hi - lo)*(2**int(bits) - 1)).astype(np.uint64)
    return float((np.diff(np.sort(q)) == 0).mean())

print('参考答案 4 已定义')
print('要点：碰撞率有一个精确的恒等式 —— (n - 不同值个数)/(n-1)。')
print('     所以它其实是在数「量化后还剩多少个不同的深度」，')
print('     而这正是「排序还能区分多少层」。16 位下 20 万个深度只剩 6 万多个不同值。')
print()
print('工程结论：不要线性量化，直接位重解释 float32（练习 2）。')
print('        而这条结论只能通过「打乱输入顺序，输出应不变」这条测试发现 ——')
print('        只看 PSNR 的话，它表现为莫名的 0.5 dB 损失。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 官方实现：分箱与排序（cuda_rasterizer/rasterizer_impl.cu）----
# 1) 每个高斯算出 tile 区间，用前缀和确定它在全局数组里的写入位置
#    getRect(p_screen, my_radius, rect_min, rect_max, grid);
#    cub::DeviceScan::InclusiveSum(..., tiles_touched, point_offsets, P);
#    num_rendered = point_offsets[P-1];              // ← 练习 1 的 P
#
# 2) 生成 64 位键：高 32 位 tile_id，低 32 位深度的位重解释
#    duplicateWithKeys<<<...>>>(...):
#        uint64_t key = y * grid.x + x;              // tile_id
#        key <<= 32;
#        key |= *((uint32_t*)&depths[idx]);          // ← 练习 2 的位重解释
#
# 3) 一次基数排序
#    cub::DeviceRadixSort::SortPairs(
#        list_sorting_space, sorting_size,
#        point_list_keys_unsorted, point_list_keys,
#        point_list_unsorted, point_list, num_rendered, 0, 32 + bit);
#    // 注意最后两个参数：只排低 (32+bit) 位，bit = ceil(log2(tile 数))
#    // 8160 个 tile -> bit=13 -> 只排 45 位，省下 19 位的扫描
#
# 4) 找每个 tile 的区间
#    identifyTileRanges<<<...>>>(num_rendered, point_list_keys, imgState.ranges);

# ---- gsplat 的对应接口（更容易读，也能单独调用每一步）----
from gsplat import fully_fused_projection, isect_tiles, isect_offset_encode, rasterize_to_pixels
radii, means2d, depths, conics, compensations = fully_fused_projection(
    means, None, quats, scales, viewmats, Ks, width, height)
tiles_per_gauss, isect_ids, flatten_ids = isect_tiles(
    means2d, radii, depths, tile_size=16,
    tile_width=math.ceil(W/16), tile_height=math.ceil(H/16))
isect_offsets = isect_offset_encode(isect_ids, C, tile_width, tile_height)
colors, alphas = rasterize_to_pixels(
    means2d, conics, colors, opacities, width, height, 16, isect_offsets, flatten_ids)
# tiles_per_gauss 就是练习 1 算的东西；isect_ids 就是练习 2 的键

# ---- 自己改内核时的五条验证（第 7 节）----
# 1) T_min=0 + tile=1x1 时与逐像素暴力实现**逐位相等**
# 2) 逐个关掉近似做消融，差应降到 0
# 3) 梯度用数值差分核对（注意提前终止让损失不光滑）
# 4) 打乱输入**数组**顺序，输出必须不变   <- 抓排序键的相等项
# 5) Σw + T_final = 1 逐像素成立；开了终止后残差被 T_min 约束
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 画面四边缺一条 | `tile_range` 是先裁剪还是先 floor | 先裁 uv 会把部分出屏的高斯覆盖范围算小 |
| PSNR 莫名低 0.5 dB，图看不出问题 | 深度键的位数；排序是否稳定 | 16 位量化时 68.75% 的相邻对顺序未定义 |
| 相机转动时画面「跳一下」 | popping：tile 内共享顺序 | 两个穿插的椭球在一个 tile 里只有一个顺序 |
| 性能远低于预期 | 有没有超大的高斯 | 半径 100 px 的一个高斯 ≈ 44 个正常高斯的分箱成本 |
| 训练早期极慢、后期突然变快 | α 初值太小 → 无法提前终止 | 官方初值 α=0.1，此时没有 tile 能终止 |
| 改小 tile 反而更慢 | 成本被搬到了排序侧 | 8×8: P ×2.25 而列表长 ×0.57 |
| 反向比前向慢很多 | atomicAdd 冲突 | 8 px 的高斯覆盖 201 个像素 |"""),
]
