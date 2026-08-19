# -*- coding: utf-8 -*-
"""C56 模块 04 · 增强流水线工程。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–03（几何 / 光度 / 混合类增强）；C43（数据工程）与 C52（训练-部署一致性）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_aug_pipeline.ipynb'),
    ("核心参考", "Albumentations 论文与文档、PyTorch DataLoader 的 worker 语义、WBF（Weighted Boxes Fusion）论文、NVIDIA DALI / FFCV 文档"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("order", "顺序：为什么几何在前、光度在后", "".join([
        P("前三个模块讲的是<strong>单个算子</strong>；这一模块讲的是<strong>把它们串成一条流水线</strong>。这不是把算子随便排一排的小事——顺序、概率、进程模型这三件事，每一件搞错都会让「你以为的增强」和「实际发生的增强」相差一个数量级，<em>而且都不报错</em>。"),
        ASCII("""一条真实的检测增强流水线（YOLO 系的典型形态）

  原始样本 (img, boxes, labels)
      │
      ├─[A] 混合类（读多张图）   Mosaic(p=1.0) → MixUp(p=0.1)
      │        ↑ 必须最先：它改变"什么是一个样本"
      ├─[B] 几何类（改坐标）     RandomAffine → RandomPerspective → HFlip
      │        ↑ 全部合成一个 3×3 矩阵，**只重采样一次**
      ├─[C] 越界处理            裁剪到画布 → 面积/可见比阈值筛掉残框
      │        ↑ 必须紧跟几何：此时坐标才是最终的
      ├─[D] 光度类（不改坐标）   HSV → 亮度/对比度 → 噪声 → 运动模糊 → JPEG
      │        ↑ 放在几何之后，否则高频扰动被重采样抹平
      ├─[E] 尺寸归一            Letterbox / Resize（与推理端**逐行相同的代码**）
      └─[F] 张量化              HWC→CHW, uint8→float, mean/std 归一化
               ↑ 这一段在 val/test/部署三处必须完全一致"""),
        P("这个顺序不是约定俗成，每一步都有可以量化的理由。"),
        TABLE(["阶段", "是否改标注", "是否重采样像素", "放错位置的后果"], [
            ["<strong>A 混合类</strong>", "是（合并多图的框）", "是（缩放拼接）", "放在几何之后 → 每张子图各自做过几何，拼接后尺度分布失控"],
            ["<strong>B 几何类</strong>", "<strong>是</strong>", "<strong>是</strong>", "拆开分多次做 → 多次插值，细节被反复抹平（下面有数值）"],
            ["<strong>C 越界处理</strong>", "是（裁剪/丢弃）", "否", "放在几何之前 → 裁剪的是旧坐标，等于没裁"],
            ["<strong>D 光度类</strong>", "否", "否", "放在几何之前 → <strong>注入的噪声被后续插值平滑掉 50%–69%</strong>"],
            ["<strong>E 尺寸归一</strong>", "是（等比缩放）", "是", "与推理端实现不同 → 训练-部署鸿沟（C60 的头号杀手）"],
            ["<strong>F 张量化</strong>", "否", "否", "顺序错（先减均值再除 255）→ 数值全错但模型仍能训"],
        ]),
        DUAL(
            "「光度放在几何之后」的理由最容易被忽略，而它是可以精确算出来的：<strong>任何亚像素的几何变换都是一次低通滤波</strong>。双线性插值把一个像素写成相邻两点的凸组合，等价于一个 [1−f, f] 的卷积核。你先往图上加了 σ=0.1 的高斯噪声，再做一次 0.5 像素的平移，噪声方差就被乘上 <code>0.5²+0.5²=0.5</code>——<em>实际的 σ 只剩 0.071</em>。如果几何段是三个算子串着做，方差只剩 31%，σ 只剩 0.056。<strong>你在配置文件里写的强度和模型真正见到的强度，差了将近一倍。</strong>",
            "严格地说：设几何变换的重采样核为 <span class=\"term\">h</span>，对独立同分布的加性噪声，输出方差为 <code>σ² · ‖h‖²₂</code>。半像素双线性平移 <code>h=[0.5,0.5]</code>，<code>‖h‖²₂=0.5</code>；三次串联的等效核是它的三重卷积 <code>[1,3,3,1]/8</code>，<code>‖h‖²₂=20/64=0.3125</code>。<em>这同时给出了第二条规则</em>：几何算子应当<strong>先把所有变换合成一个仿射/透视矩阵，再做一次 <code>warpAffine</code></strong>，而不是逐个算子各调一次。串联三次不仅慢三倍，还额外损失了 <code>0.5−0.3125=37.5%</code> 的高频能量——<em>而高频正是小目标赖以被检出的信息</em>。",
        ),
        CALLOUT("warn", "<strong>「越界处理必须紧跟几何段」</strong>是另一个高频实现 bug。常见写法是在最后统一裁剪框，但此时若中间插入了 Mosaic 的二次拼接，坐标系已经换过了，裁剪就作用在错误的画布上。<em>症状是训练集里凭空出现大量贴边的窄条框</em>——它们是残缺目标，模型会学到「标志可以只有 2 像素宽」，直接污染小目标的尺度先验。<strong>规则：坐标系一变，立刻做一次合法性清洗。</strong>"),
        CALLOUT("intuition", "把顺序规则压成一句可背的话：<strong>先决定「一个样本是什么」（混合），再决定「它长在哪」（几何 + 清洗），最后决定「它看起来怎样」（光度），末尾是与推理端字节对齐的归一化</strong>。<em>越靠前的阶段影响越结构性、越不可逆；越靠后的阶段越是纯像素级的微调。</em>"),
    ])),
    ("prob", "概率相乘：你配置的强度和实际强度差一个数量级", "".join([
        P("流水线里每个算子都带一个触发概率 <code>p</code>。绝大多数人凭直觉理解它——「p=0.5 就是一半样本会被增强」——这句话对<strong>单个算子</strong>是对的，对<strong>整条流水线</strong>是灾难性的错。"),
        MATH("P(\\text{全部触发}) = \\prod_{i=1}^{k} p_i, \\qquad P(\\text{一个都不触发}) = \\prod_{i=1}^{k} (1-p_i), \\qquad \\mathbb{E}[\\#\\text{触发}] = \\sum_{i=1}^{k} p_i"),
        P("代入最常见的配置：<strong>5 个算子各 p=0.5</strong>。"),
        TABLE(["量", "公式", "数值", "直觉预期"], [
            ["全部触发", "0.5⁵", "<strong>3.1%</strong>", "很多人以为是「一半」"],
            ["一个都不触发", "0.5⁵", "<strong>3.1%</strong>", "——"],
            ["平均触发个数", "5×0.5", "2.5 个", "——"],
            ["至少触发 3 个", "(10+5+1)/32", "50.0%", "——"],
            ["至少触发 1 个", "1−0.5⁵", "96.9%", "看起来很安全，掩盖了强度分布"],
        ]),
        P("换成 8 个算子（真实流水线的常见规模）各 p=0.5：全部触发的概率是 <code>0.5⁸ = 0.39%</code>。<strong>你写在配置里的「最强增强组合」，在整个训练过程中只会出现在四百分之一的样本上</strong>——它几乎从未参与训练，而你却在 review 时按它来判断增强强度。"),
        DUAL(
            "反过来算更有用：<strong>如果你希望「全套增强都上」的样本占 30%，5 个算子每个的 p 该设多少？</strong>答案是 <code>0.30^(1/5) = 0.786</code>——每个算子都要接近 0.8，而不是直觉的 0.5 或 0.6。<em>这个反解在调参时极其实用：你先定「联合强度」这个业务上真正关心的量，再反推每个算子的 p，而不是逐个算子拍脑袋。</em>",
            "另一个必须知道的实现陷阱是<strong>嵌套概率的折叠</strong>。Albumentations 的 <code>OneOf([...], p=0.5)</code> 语义是：以 0.5 的概率进入这个组，进入后按<em>归一化权重</em>从组内选一个。所以组内某算子的实际触发率是 <code>0.5 × w_i/Σw</code>，而不是它自己写的那个 p。<em>三层嵌套（Compose 里套 OneOf 里套 Compose）之后，叶子算子的实际触发率常常低到 2%–3%</em>。<strong>唯一可靠的做法是给流水线打点，把每个算子的实际触发率和联合分布统计出来，而不是读配置文件推理。</strong>",
        ),
        CALLOUT("danger", "<p>这个坑在<strong>消融实验</strong>里会直接导致错误结论。你加了一个新算子、设 p=0.3，跑完发现 mAP 只涨了 0.1，于是判定「这个增强没用」。但如果它嵌在一个 <code>OneOf(p=0.5)</code> 的三选一里，实际触发率是 <code>0.5×1/3=16.7%</code>，再乘上它只对 12% 的夜间样本有意义——<em>真正受影响的样本占比 2%</em>。<strong>+0.1 的整体 mAP 对应的是那 2% 样本上的巨大提升</strong>。这也是模块 05 要讲的「分场景验证」的动机之一。</p>", "面试常问：你怎么判断一个增强算子有没有用"),
        CALLOUT("intuition", "落到 TSR 上：交通标志的关键失效场景（夜间、雨雾、逆光）在数据里本来就只占 10%–20%，<strong>针对它们的增强算子一旦再乘上一个 0.2 的触发概率，实际覆盖的样本就只剩 2%–4%</strong>。<em>所以场景专用增强的 p 应当显著高于通用增强的 p</em>，甚至应该按样本的场景标签做<strong>条件触发</strong>（只在夜间样本上加眩光、只在高速样本上加运动模糊），而不是全局均匀掷骰子。"),
    ])),
    ("throughput", "CPU 才是训练吞吐的真正瓶颈", "".join([
        P("检测训练的直觉是「GPU 在算」。真实情况常常相反：<strong>数据增强跑在 CPU 上，而检测增强（尤其是 Mosaic、copy-paste、透视变换）比分类增强重一个数量级</strong>。一旦 CPU 供不上，昂贵的 GPU 就在空转，而你从 loss 曲线上完全看不出来。"),
        MATH("\\text{throughput} = \\min\\!\\left(\\underbrace{\\frac{W}{t_{\\text{aug}}}}_{\\text{CPU 侧}},\\ \\underbrace{\\frac{B}{t_{\\text{step}}}}_{\\text{GPU 侧}}\\right), \\qquad \\text{GPU 利用率} = \\min\\!\\left(1,\\ \\frac{W \\cdot t_{\\text{step}}}{B \\cdot t_{\\text{aug}}}\\right)"),
        P("其中 <code>W</code> = worker 数，<code>t_aug</code> = 单样本增强耗时，<code>B</code> = batch size，<code>t_step</code> = 一步前反向的耗时。代入一组真实数字：<code>t_aug=12 ms</code>、<code>B=32</code>、<code>t_step=60 ms</code>。"),
        TABLE(["配置", "CPU 供给 (img/s)", "GPU 需求 (img/s)", "瓶颈", "GPU 利用率"], [
            ["W=4", "333", "533", "<strong>CPU（数据增强）</strong>", "<strong>62.5%</strong>"],
            ["W=7", "583", "533", "GPU（前反向）", "100%"],
            ["W=8", "667", "533", "GPU（前反向）", "100%"],
            ["W=8, 开 Mosaic（t_aug≈38 ms）", "208", "533", "<strong>CPU，严重</strong>", "<strong>39%</strong>"],
            ["要喂饱 GPU 所需最少 worker", "—", "—", "—", "<code>⌈533×0.012⌉=7</code>；开 Mosaic 后 <strong>21</strong>"],
        ]),
        P("最后一行是这一节的重点：<strong>Mosaic 要读 4 张图、解码 4 次、拼接后再做一次几何变换，单样本成本大约是普通增强的 3 倍</strong>。于是「喂饱一张卡」需要的 CPU 核数从 7 跳到 21——<em>在一台 8 卡机上就是 168 核，绝大多数机器给不出来</em>。这就是为什么开了 Mosaic 之后训练明显变慢却查不出原因。"),
        ASCII("""GPU 利用率随时间（W 不足时的锯齿波形 —— 这就是诊断指纹）

100% ┤ ████        ████        ████        ████
     │ ████        ████        ████        ████
 50% ┤ ████        ████        ████        ████
     │ ████        ████        ████        ████
  0% ┴─████████────████████────████████────████████──→ t
       ↑    ↑
       │    └─ 空转 38%：worker 还在解码 JPEG + 拼 Mosaic
       └─ 计算：前向 + 反向

对照组（W 充足）：利用率贴着 95%–100% 平直，没有周期性谷底。
诊断口诀：**看 GPU 利用率的时间序列，不要看平均值。**
平均 62% 可能是「一直 62%」（算子本身低效），
也可能是「100% 和 0% 交替」（数据饿死）—— 两者的处方完全不同。"""),
        DUAL(
            "怎么<strong>确认</strong>是数据瓶颈而不是模型瓶颈？有一个五秒钟的判定法：<strong>把 DataLoader 换成一个返回固定张量的假数据源，再跑一遍</strong>。如果吞吐显著上升，瓶颈就在数据侧；如果几乎不变，瓶颈在 GPU 侧。<em>这个「短路实验」比任何 profiler 都快</em>，而且不会被采样误差和工具开销骗到。它和 C52 讲的「逐层二分定位」是同一个方法论：<strong>把整体慢分解成可以单独短路的环节。</strong>",
            "第二个必须区分的量是<strong>吞吐的均值瓶颈 vs 方差瓶颈</strong>。<code>prefetch_factor</code> 和队列只能<em>削峰</em>——它们把「某一批特别慢」的抖动吸收掉，让 GPU 不因为偶发慢批而空转。<strong>但队列无法提高长期平均吞吐</strong>：只要 <code>W/t_aug &lt; B/t_step</code>，无论队列多深，稳态吞吐都等于 CPU 侧的供给速率。<em>把 prefetch 从 2 调到 16 却没变快，说明你面对的是均值问题而不是方差问题</em>——此时唯一的出路是降低 <code>t_aug</code> 或提高 <code>W</code>。",
        ),
        CALLOUT("warn", "worker 数<strong>不是越多越好</strong>：① 每个 worker 是一个独立进程，要复制一份数据集索引与 Python 解释器，内存按 W 线性增长（大 <code>annotations</code> 字典能吃掉几 GB×W）；② 超过物理核数后线程争抢反而降低单 worker 吞吐；③ 与 <code>OMP_NUM_THREADS</code> 冲突——OpenCV/numpy 默认多线程，W 个 worker 各开 N 个线程会产生 W×N 的线程风暴。<em>标准做法是 <code>cv2.setNumThreads(0)</code> + <code>W ≈ 物理核数 − 2</code></em>。"),
    ])),
    ("optimize", "吞吐优化的六个杠杆（按性价比排序）", "".join([
        P("确认是 CPU 瓶颈之后，有六个杠杆可用。它们的收益、代价和适用条件差别很大，<strong>按性价比排序而不是按流行度排序</strong>。"),
        TABLE(["杠杆", "做什么", "典型收益", "代价 / 风险", "什么时候用"], [
            ["<strong>① 关掉库内多线程</strong>", "<code>cv2.setNumThreads(0)</code>、<code>OMP_NUM_THREADS=1</code>", "1.3–2×", "几乎无", "<strong>永远先做这一条</strong>，五秒钟见效"],
            ["<strong>② 合并几何算子</strong>", "多个仿射合成一个矩阵，只 warp 一次", "1.5–3×（几何段）", "要自己写矩阵合成", "几何算子 ≥3 个时必做，<em>顺带提升画质</em>"],
            ["<strong>③ 换解码格式</strong>", "JPEG 预解码成 raw/npy/webdataset/LMDB", "<strong>2–4×</strong>", "磁盘占用涨 5–10×", "JPEG 解码常占 t_aug 的 40%–60%"],
            ["<strong>④ 加 worker + 持久化</strong>", "<code>num_workers</code>↑、<code>persistent_workers=True</code>", "线性到核数上限", "内存 ×W；启动慢", "核数还有余量时"],
            ["<strong>⑤ GPU 侧增强</strong>", "DALI / Kornia / torchvision.transforms.v2 放到 GPU", "3–10×", "<strong>抢 GPU 显存与算力</strong>；算子集受限；<em>数值与 CPU 版不完全一致</em>", "CPU 核数不够且增强以张量运算为主"],
            ["<strong>⑥ 降低增强分辨率</strong>", "先 resize 到目标尺寸再做重算子", "1.5–2.5×", "<strong>小目标细节提前丢失</strong>", "<em>TSR 场景慎用</em>——见下方警告"],
        ]),
        DUAL(
            "杠杆 ③ 常常是最大的一块，却最少被想到。一张 1920×1080 的 JPEG 解码大约 6–10 ms，而整条增强流水线可能才 12 ms——<strong>意味着一半以上的 CPU 时间花在「把图片变成数组」而不是「增强」上</strong>。<em>预解码成未压缩格式后，读取变成纯 IO，t_aug 直接腰斩</em>。代价是磁盘：10 万张 1080p 图从 20 GB 涨到 300 GB。对车队数据这个代价通常可以接受，因为训练机本来就挂着大容量盘。",
            "杠杆 ⑤ 有一个必须提前知道的副作用：<strong>GPU 侧增强的数值与 CPU 侧不完全一致</strong>。插值实现、边界处理、浮点累加顺序都可能不同，导致「换了数据管线之后 mAP 变了 0.3」这类无法归因的现象。<em>更麻烦的是它抢占 GPU 资源</em>——增强占了 15% 的显存和算力后，你能开的 batch size 变小，反而可能整体更慢。<strong>正确做法是：先把 ①②③ 做完，确认 CPU 侧真的榨不出来了，再考虑 ⑤，并且切换前后必须做一次完整的对拍</strong>（这正是 C60 讲的训练-部署一致性方法论在训练侧的应用）。",
        ),
        CALLOUT("danger", "<p>杠杆 ⑥ 在 <strong>TSR 场景下是陷阱</strong>。「先把 1920×1080 缩到 640×640 再做增强」能省一大半 CPU，但 60 米外的限速牌在原图上只有 18 像素，缩放后只剩 6 像素——<em>它在增强流水线的第一步就被抹掉了</em>，后面所有的几何/光度增强都作用在一坨模糊上。<strong>症状是小目标 AP 莫名其妙掉 3–5 个点，而所有增强参数看起来都正常</strong>。规则：<strong>凡是会降低有效分辨率的优化，都必须按目标尺寸分桶验证</strong>，不能只看整体 mAP。</p>", "省 CPU 省掉了小目标"),
        CALLOUT("intuition", "一个能省很多事的工程约定：<strong>把 <code>t_aug</code> 做成训练日志里的一等公民</strong>——每个 epoch 打印一次「单样本增强耗时的 p50/p99、各算子耗时占比、GPU 利用率」。<em>这三个数一旦上了看板，「训练怎么变慢了」这个问题就从「玄学」变成了「看一眼日志」</em>。它的成本是十几行代码，收益是整个团队不再靠猜。"),
    ])),
    ("rng", "可复现性：DataLoader worker 的 RNG 陷阱", "".join([
        P("这一节讲的是<strong>一起真实事故</strong>，而且是那种「跑通了、指标也不算离谱、但你的增强多样性被静默砍掉了 3/4」的事故。它不会报错，不会 warning，只会让你的模型比应有的水平差几个点。"),
        ASCII("""PyTorch DataLoader 的 worker 是 **fork** 出来的子进程

  主进程   numpy 全局 RNG state = S0
     │     random 模块  state = R0
     │
     ├── fork ──> worker 0 :  numpy state = S0, random state = R0   ← 完全相同
     ├── fork ──> worker 1 :  numpy state = S0, random state = R0   ← 完全相同
     ├── fork ──> worker 2 :  numpy state = S0, random state = R0   ← 完全相同
     └── fork ──> worker 3 :  numpy state = S0, random state = R0   ← 完全相同

后果：4 个 worker 抽出的随机数序列**逐个相同**。
样本 0,4,8,...  由 worker0 处理，用 stream[0],stream[1],stream[2],...
样本 1,5,9,...  由 worker1 处理，用 **同一个** stream[0],stream[1],...
=> 样本 0/1/2/3 拿到**完全一样**的增强参数。
=> 一个 epoch 里不同的增强参数只有 N/W 组，**多样性打了 1/W 的折扣**。

注意：PyTorch 会为 **torch 自己的 RNG** 做 base_seed+worker_id 的处理，
所以 torch.rand 是安全的；**numpy 与 python random 不在此列**。
而绝大多数检测增强库（Albumentations、imgaug、自写算子）用的正是 numpy。"""),
        P("这个 bug 有三个变体，症状与修法各不相同。"),
        TABLE(["变体", "写法", "症状", "怎么检测", "修法"], [
            ["<strong>① 全 worker 同 seed</strong>", "worker 里直接用全局 <code>np.random</code>", "<strong>增强多样性 ÷ W</strong>，且完全静默", "统计一个 epoch 内不同增强参数的<strong>去重个数</strong>，应等于样本数", "<code>worker_init_fn</code> 里用 <code>base_seed+worker_id</code> 重新播种"],
            ["<strong>② 只按 worker_id 播种</strong>", "<code>seed(1234+worker_id)</code>", "<strong>每个 epoch 重复同一串增强</strong>；训练 300 epoch 只见过 1 个 epoch 的增强多样性", "对比 epoch 0 与 epoch 1 的参数序列，应完全不同", "seed 里必须含 <strong>epoch</strong>（或用 <code>torch.initial_seed()</code>，它每 epoch 变）"],
            ["<strong>③ 复现不了实验</strong>", "只固定 <code>torch.manual_seed</code>", "同样的命令跑两次结果不同", "跑两次对比 loss 曲线前 10 步", "固定 torch/numpy/random 三家 + <code>generator=</code> + 记录 <code>num_workers</code>"],
        ]),
        CODE("""# ✅ 正确写法：seed 必须同时含 base_seed / epoch / worker_id
import numpy as np, random, torch

def worker_init_fn(worker_id):
    # torch.initial_seed() = base_seed + worker_id，且**每个 epoch 由 sampler 重新生成**
    seed = torch.initial_seed() % (2 ** 31)
    np.random.seed(seed)          # ← numpy 全局（兼容老代码）
    random.seed(seed)             # ← python random
    cv2.setNumThreads(0)          # ← 顺手把线程风暴关掉

# 更干净的做法：不用全局 RNG，每个 worker 持有自己的 Generator
class AugDataset(torch.utils.data.Dataset):
    def _rng(self):
        info = torch.utils.data.get_worker_info()
        wid = 0 if info is None else info.id
        ss = np.random.SeedSequence(entropy=self.base_seed,
                                    spawn_key=(self.epoch, wid))   # ← epoch 必须在里面
        return np.random.default_rng(ss)

loader = torch.utils.data.DataLoader(
    ds, batch_size=32, num_workers=8,
    worker_init_fn=worker_init_fn,
    generator=torch.Generator().manual_seed(1234),   # ← 控制 shuffle 的随机性
    persistent_workers=True, prefetch_factor=4,
)"""),
        DUAL(
            "把损害量化一下就知道为什么这值得单开一节：<strong>N=64 个样本、W=4 个 worker，变体 ① 下一个 epoch 里只有 16 组不同的增强参数</strong>。更糟的是，因为 seed 与 epoch 无关，<em>这 16 组参数在全部 300 个 epoch 里一模一样</em>——整个训练过程中模型只见过 16 种增强变体。而正确实现下是 <code>64×300 = 19200</code> 种。<strong>差了三个数量级，而 loss 曲线看起来完全正常。</strong>",
            "为什么它这么难被发现？因为<strong>增强的作用是统计性的</strong>：少了多样性不会让某个样本出错，只会让泛化差一点。你看到的是「mAP 比论文低 2 个点」，而这个差距会被归因到超参、数据量、backbone——<em>几乎不会有人怀疑到 RNG</em>。<strong>唯一可靠的防线是把「一个 epoch 内增强参数的去重个数」做成一条断言</strong>：它应该等于样本数，不等就直接抛异常。<em>这是那种写一次、终身受益的十行代码。</em>",
        ),
        CALLOUT("danger", "<p>还有一个更隐蔽的近亲：<strong>验证集 / 评测集的随机性</strong>。如果评测流水线里残留了任何随机算子（哪怕只是随机 letterbox 的填充位置），<em>同一个 checkpoint 评两次会得到不同的 mAP</em>。此时你在模块 05 要做的所有显著性检验都建立在流沙上——<strong>因为你无法区分「模型的差异」和「评测的噪声」</strong>。规则：<strong>评测路径必须是纯确定性的，并且用「同一权重评两次结果必须逐位相同」作为 CI 断言。</strong></p>", "评测有随机性 = 所有消融结论作废"),
        CALLOUT("warn", "「可复现」<strong>不等于</strong>「固定了 seed」。同一个 seed 在不同的 <code>num_workers</code> 下会产生不同的增强序列（因为样本到 worker 的分配变了）；不同版本的 OpenCV/Pillow 的插值实现也会给出不同像素。<em>所以实验记录里必须同时写下：seed、num_workers、增强配置哈希、以及关键库的版本号</em>。这四项少任何一项，半年后都复现不出来。"),
    ])),
    ("split", "训练 / 验证 / 测试 / 部署：四条路径的增强一致性", "".join([
        P("增强只属于训练。这句话人人都会说，但真实代码里违反它的方式有很多种，而且每一种都会让离线指标失去意义。"),
        TABLE(["路径", "允许的操作", "禁止的操作", "违反后的症状"], [
            ["<strong>train</strong>", "全部随机增强", "——", "——"],
            ["<strong>val</strong>", "<strong>只允许确定性变换</strong>：resize/letterbox/归一化", "任何随机性（含随机裁剪、随机 letterbox 填充位置）", "<strong>同一权重评两次结果不同</strong> → 消融结论全部作废"],
            ["<strong>test</strong>", "同 val，且必须与 val <strong>共用同一份代码</strong>", "为了刷分单独调预处理", "test 高于 val 是<em>数据泄漏或预处理不一致</em>的指纹"],
            ["<strong>deploy</strong>", "必须与 val <strong>逐位一致</strong>", "换库（cv2↔PIL）、换插值、换 padding 值", "<strong>离线 mAP 0.82，车上像 0.6</strong>（C60 模块 01 的经典故事）"],
        ]),
        DUAL(
            "最常见的违规不是「验证集做了增强」这种低级错误，而是<strong>「训练和验证的确定性部分走了两条代码路径」</strong>。训练里 letterbox 用 114 填充、缩放比例向下取整到 32 的倍数；验证里图省事直接 <code>cv2.resize(img,(640,640))</code>——<em>纵横比被拉伸了</em>。模型在训练时从未见过被拉伸的标志，验证 mAP 于是无故低几个点，而你会以为是模型过拟合。<strong>规则：train/val/deploy 的确定性段必须是同一个函数，通过参数开关随机段，而不是三份实现。</strong>",
            "另一个高频错误是<strong>「验证集做了 TTA、线上没做」</strong>。TTA 能让离线 mAP 涨 1–2 个点，如果只在验证路径上打开，你得到的是一个<em>系统性虚高的指标</em>：所有基于它的选型、门禁、消融都偏了，而且偏的量随模型不同而不同（弱模型从 TTA 受益更多），<strong>导致模型间的排序都可能反转</strong>。<em>原则：离线评测的配置必须是线上配置的一个精确镜像；任何线上不会做的事，评测路径也不许做。</em>",
        ),
        CALLOUT("intuition", "落到 TSR 上，这条原则有一个额外的维度：<strong>车端相机的 ISP 输出才是真正的部署分布</strong>。训练数据如果是从压缩视频里抽的帧，它带着 H.264 的块效应；而车端拿到的是 ISP 直出的 YUV。<em>这两者的高频特性差别很大，对 8–16 像素的小标志尤其致命</em>。所以「增强要贴近部署分布」在这里意味着：<strong>训练侧要么补上 JPEG/视频压缩伪影的增强，要么把训练数据换成 ISP 直出</strong>——而验证集必须用后者，否则你测的是「模型在压缩视频上的表现」，与车上无关。"),
        CALLOUT("warn", "一条容易被忽略的推论：<strong>close-mosaic 这类「阶段性增强」让训练分布在中途发生跳变</strong>。关掉 Mosaic 的那一刻，训练分布突然向验证分布靠拢，<em>验证 mAP 会出现一个明显的台阶</em>。如果你在切换点附近做模型选择或早停，就会选到一个「刚好赶上台阶」的 checkpoint，<strong>而这个提升与你正在消融的那个变量毫无关系</strong>。规则：<strong>所有对比实验必须在完全相同的 epoch 数与相同的 close-mosaic 时点下进行。</strong>"),
    ])),
    ("tta", "TTA 与 WBF：融合多个视角的正确方式", "".join([
        P("<span class=\"term\">TTA</span>（Test-Time Augmentation，测试时增强）是把同一张图用多种确定性变换各推一遍，再把结果融合。它是离线场景的免费午餐，也是车端几乎用不起的奢侈品。"),
        H3("① TTA 的构成与逆变换"),
        P("典型配置：<strong>3 个尺度 × 2 种翻转 = 6 个分支</strong>。关键的实现细节是<strong>每个分支的框必须逆变换回原图坐标系</strong>：缩放分支要除以缩放比，翻转分支要做 <code>x → W − x</code> 并<strong>交换 x1/x2</strong>（忘记交换会得到 x1&gt;x2 的非法框，NMS 里 IoU 全算成 0，症状是「TTA 之后反而掉点」）。"),
        H3("② 为什么融合不能用 NMS"),
        DUAL(
            "NMS 的语义是<strong>「选一个、删掉其他」</strong>。这在单模型输出上是对的——重复框是冗余，删掉即可。但在 TTA 场景下，<strong>6 个分支给出的 6 个框是同一个目标的 6 次独立观测</strong>，每一次都带独立的定位噪声。此时删掉 5 个只留最高分的那个，<em>等于扔掉了 5 份可以用来降噪的信息</em>。正确的做法是<strong>平均</strong>——多次独立观测的加权平均，其方差是单次观测的 1/n。",
            "<span class=\"term\">WBF</span>（Weighted Boxes Fusion，加权框融合）正是这么做的：按分数降序遍历所有框，与已有簇的融合框 IoU 超过阈值就并入该簇，并<strong>用分数作权重重算融合坐标</strong>；否则新建一个簇。最后还有关键的一步——<strong>按支持该簇的分支数重标定分数</strong>：只被 1 个分支检出的框，其分数要乘上 <code>1/T</code>（T 为分支总数）。<em>这一步是 WBF 相对 NMS 的第二个优势：它天然抑制了「只有某个尺度才看到」的偶发误检</em>，而 NMS 对这类框无能为力（它没有重复框可以比较）。",
        ),
        MATH("b_{\\text{fused}} = \\frac{\\sum_{i=1}^{n} s_i \\cdot b_i}{\\sum_{i=1}^{n} s_i}, \\qquad s_{\\text{fused}} = \\left(\\frac{1}{n}\\sum_{i=1}^{n} s_i\\right) \\cdot \\frac{\\min(n, T)}{T}"),
        TABLE(["融合方式", "坐标怎么定", "分数怎么定", "对 TTA 的适配性"], [
            ["<strong>NMS</strong>", "取最高分那一个", "最高分", "<strong>差</strong>：丢弃其余观测，定位方差不降"],
            ["<strong>Soft-NMS</strong>", "取最高分那一个", "重叠者降权而非删除", "中：保住了召回，但坐标仍来自单个分支"],
            ["<strong>NMW</strong>", "加权平均", "<strong>取最大值</strong>", "中：坐标对了，但单分支误检不被抑制"],
            ["<strong>WBF</strong>", "<strong>分数加权平均</strong>", "<strong>均值 × min(n,T)/T</strong>", "<strong>好</strong>：定位降噪 + 单分支误检降分"],
        ]),
        H3("③ 延迟账：为什么车端用不起"),
        P("6 个分支意味着 6 次前向。按尺度的计算量正比于面积，<code>[0.83, 1.0, 1.25]</code> 三个尺度的相对代价是 <code>0.69 + 1.00 + 1.56 = 3.25</code>，再乘 2（翻转）= <strong>6.5 倍单次推理</strong>。若单次推理 8 ms，TTA 就是 52 ms，加融合约 <strong>53.5 ms</strong>。"),
        CALLOUT("danger", "<p>而 TSR 在车端的<strong>整体预算</strong>是这样的：30 FPS → 每帧 33 ms，这 33 ms 要装下多路相机的感知、融合、跟踪、规控——<strong>TSR 分到的通常只有 8–12 ms</strong>。53.5 ms 超出预算 5 倍以上。<em>更致命的是 TTA 的延迟随目标数波动（融合是 O(n²) 的），破坏了 p99 延迟的确定性</em>——而车端要的恰恰是确定性。<strong>结论：TTA 在量产感知里基本不可用。面试里被问「你会用 TTA 吗」，正确答案是「离线会，车端不会，因为……」并给出这笔账。</strong></p>", "面试高频：TTA 上车吗"),
        CALLOUT("intuition", "但 TTA 在离线仍有三个高价值用途，<strong>这才是它该出现的地方</strong>：① <strong>打伪标签</strong>——半监督/自训练里用 TTA 提高教师模型的标注质量；② <strong>难例挖掘的一致性信号</strong>——<em>不同 TTA 分支给出的结果分歧越大，这张图越可能是难例</em>（这正是 C58 讲的一致性触发器）；③ <strong>评估精度上限</strong>——TTA 后的 mAP 可以视作「这个模型在这份数据上的能力天花板」，与单次推理的差距衡量了模型对视角/尺度的鲁棒性缺口。<em>换句话说：TTA 涨得越多，说明你的增强训练做得越差。</em>"),
    ])),
    ("config", "增强配置的版本管理：它是模型的一部分", "".join([
        P("增强配置不是「训练脚本的一个参数」，而是<strong>模型定义的一部分</strong>——同样的架构、同样的数据、不同的增强配置，产出的是两个能力完全不同的模型。它必须被当作代码一样版本化。"),
        TABLE(["必须记录的字段", "为什么", "漏了会怎样"], [
            ["<strong>算子列表与顺序</strong>", "顺序影响数值（见第 1 节）", "复现时把光度放到几何前，噪声强度差一倍"],
            ["<strong>每个算子的参数与 p</strong>", "强度的直接定义", "——"],
            ["<strong>实测的联合触发分布</strong>", "配置里的 p 与实际触发率常常不同（嵌套 OneOf）", "<strong>消融结论错误归因</strong>"],
            ["<strong>seed 策略 + num_workers</strong>", "两者共同决定实际的随机序列", "复现不出来（第 5 节）"],
            ["<strong>库版本</strong>（cv2 / PIL / albumentations）", "插值与边界实现随版本变化", "换机器后 mAP 漂移 0.2–0.5，查不出原因"],
            ["<strong>阶段性切换点</strong>（close-mosaic epoch）", "训练分布在此跳变", "对比实验的切换点不一致 → 结论不可比"],
            ["<strong>配置哈希</strong>", "一个字符串就能判断两次实验是否可比", "只能靠人肉 diff YAML"],
        ]),
        DUAL(
            "<strong>配置哈希</strong>是这里最有杠杆的一条：把规范化后的增强配置（含库版本）序列化，取一个短哈希，写进 checkpoint 的元数据和每一行训练日志。<em>此后「这两次实验的增强一样吗」就从一次考古变成了一次字符串比较</em>。它同时解决了另一个问题——<strong>当有人在 review 里说「我只改了学习率」时，哈希会告诉你他顺手动过增强</strong>。这与 C52 讲的「给不可读的二进制产物附一份可读的来源说明」是同一个模式。",
            "更进一步：<strong>把「实测触发率」也纳入产物</strong>。训练开始时跑 2000 个样本过一遍流水线，统计每个算子的实际触发率与联合分布，写进日志。<em>这一步把「配置」变成了「事实」</em>：你不再需要在脑子里折叠嵌套概率，也能立刻发现「这个算子的实际触发率是 2%，难怪消融看不出差别」。<strong>成本是训练开始时多花 3 秒，收益是消除了整整一类的错误归因。</strong>",
        ),
        CALLOUT("warn", "一个真实的组织性陷阱：<strong>增强配置常常被复制粘贴，然后各自演化</strong>。检测组从分类组抄了一份 HSV 参数，其中 <code>hue_shift=±20°</code> 对分类无害，但对 TSR 是灾难——<em>红色禁令牌的色相偏 20° 就滑向橙/品红，语义被破坏</em>（模块 02 已经量化过这一点）。<strong>规则：领域敏感的参数必须在配置里带注释说明约束来源，并写进 CI 断言</strong>（例如「hue 幅度不得超过 10°」），而不是指望下一个人记得。"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的心法：<strong>增强流水线是一个「你写的配置」与「模型实际见到的分布」之间存在系统性偏差的地方——顺序偏差、概率偏差、RNG 偏差、库实现偏差，四种都静默</strong>。<em>因此工程上唯一可靠的姿态是：不推理，去测量</em>。触发率要打点、多样性要断言、耗时要上看板、配置要哈希。<strong>这四件事加起来不到一百行代码，却消除了这个领域绝大多数的「查不出原因」。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("增强流水线工程看起来很「工程」，但它连着几个仍然开放的研究问题。"),
        UL([
            "<strong>自动增强搜索</strong>：AutoAugment 用 RL 搜策略、成本极高（几千 GPU 小时）；Fast AutoAugment 用密度匹配把成本降两个数量级；<strong>RandAugment 把搜索空间压成两个超参（N 个算子、强度 M）</strong>，几乎不损失精度——<em>这个「简化反而更好」的结果本身是个重要教训</em>；TrivialAugment 更进一步，连强度都随机采样。但<strong>检测任务上的自动搜索仍不成熟</strong>：搜索目标是 mAP（评估贵）、搜索空间要包含框变换的合法性约束、而且最优策略与数据集强相关。",
            "<strong>在线自适应增强</strong>：Population Based Augmentation、Adversarial AutoAugment 让增强强度<em>随训练进程变化</em>（早期弱、后期强），这与本课模块 05 要讲的「增强强度与训练时长的交互」是同一个现象的两面。开放问题是：<strong>能否用模型自身的不确定性来在线决定每个样本该被增强多强</strong>——即「样本级自适应增强」。",
            "<strong>数据管线的系统化</strong>：NVIDIA DALI、FFCV、WebDataset 把增强搬到 GPU 或做成流式格式。它们的共同难题是<strong>算子覆盖与数值一致性</strong>——GPU 实现与 CPU 实现的插值差异会造成不可归因的指标漂移。<em>「跨后端的位级一致增强」目前没有标准方案。</em>",
            "<strong>生成式增强</strong>：用扩散模型合成罕见场景（夜间的施工牌、雨雾中的限速牌）。收益诱人，但有两个硬问题：① <strong>标注一致性</strong>——生成的图里目标框在哪、语义对不对，需要可控生成而非自由生成；② <strong>分布真实性</strong>——生成数据的伪影会成为模型学到的捷径特征，<em>在真实数据上反而掉点</em>。这是当前 TSR 长尾问题最被寄予厚望也最不确定的方向。",
            "<strong>增强与半监督的统一</strong>：FixMatch / Unbiased Teacher 系列把「弱增强出伪标签、强增强做一致性约束」变成了半监督的核心机制。<em>这意味着增强不再只是正则化，而成了监督信号的来源</em>。开放问题是：<strong>强弱增强的「强度差」该多大</strong>——太小没有约束力，太大伪标签失效，目前仍靠手调。",
            "<strong>TTA 的低成本化</strong>：能否用一次前向获得多视角的效果（如让网络内部显式建模尺度/翻转等变性），从而在车端也享受 TTA 的降噪收益？等变网络（equivariant CNN）与 test-time 自适应是两条正在探索的路径，<em>目前都还没有达到「延迟可接受 + 收益可观」的组合</em>。",
        ]),
        CALLOUT("paper", "必读：<em>AutoAugment</em>（Cubuk et al., 2019）与 <em>RandAugment</em>（Cubuk et al., 2020）——对照读，理解「搜索空间简化为何不损失精度」；<em>Weighted Boxes Fusion</em>（Solovyev et al., 2021）——WBF 的原始定义与 vs NMS/NMW 的对比实验，本模块 notebook 实现的就是它；<em>Albumentations: Fast and Flexible Image Augmentations</em>（Buslaev et al., 2020）——检测增强库的设计取舍与 <code>OneOf</code> 的概率语义；NVIDIA <em>DALI</em> 与 <em>FFCV</em> 的文档（数据管线瓶颈的系统性解法）；PyTorch 官方文档的 <em>Randomness in multi-process data loading</em> 一节（worker RNG 陷阱的一手说明）。相邻课程：C43（数据工程）、C58（难例挖掘与一致性触发）、C60（训练-部署一致性）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 增强流水线工程（算子顺序 / 触发概率 / worker RNG / 吞吐瓶颈 / WBF）

目标：把一条检测增强流水线**当成一个可测量的系统**来对待——
测它的实际触发率、测它的随机性多样性、测它的吞吐上限、测它的融合质量。

路线：流水线骨架与打点 → **概率相乘的实际触发率** → 顺序为何是几何在前 →
**DataLoader worker RNG 陷阱（正确/错误两种 seed 策略）** → 吞吐瓶颈模型与预取 →
**WBF vs NMS** 与 TTA 延迟账 → ✏️ 4 道练习 → 📖 答案 → 🧪 工程胶囊。

> 心智模型：**你写的配置 ≠ 模型见到的分布**。顺序、概率、RNG、库实现，
> 四种偏差全都静默。工程上唯一可靠的姿态是：**不推理，去测量。**

本 notebook 你会亲手实现：
1. 带触发打点的增强流水线（算子 + 概率 + 顺序）
2. 联合触发分布的**精确计算**与概率反解
3. 重采样对高频扰动的抹平量化（为什么光度必须在几何之后）
4. **三种 worker seed 策略**及其多样性后果（这是一起真实事故）
5. CPU/GPU 吞吐模型、最少 worker 数、预取只削峰不提均值的证明
6. **WBF（加权框融合）**、与 NMS 的定位精度对比、TTA 的车端延迟账"""),

    md("""## 1 · 流水线骨架：算子 + 概率 + 顺序 + 打点

先把流水线建成一个**可观测**的对象：每个算子记录触发次数，每个样本记录触发组合。
没有打点的流水线是不可调试的。"""),
    code("""import numpy as np, math, itertools, collections, json

# ---------- 样本：一张小灰度图 + 若干框（x1,y1,x2,y2）----------
def make_sample(rng, H=48, W=64, n_box=3):
    img = rng.normal(0.5, 0.15, size=(H, W))
    boxes = []
    for _ in range(n_box):
        w = rng.integers(6, 16); h = rng.integers(6, 16)
        x1 = rng.integers(0, W - w); y1 = rng.integers(0, H - h)
        boxes.append([x1, y1, x1 + w, y1 + h])
    return {'img': img, 'boxes': np.array(boxes, dtype=float)}

# ---------- 算子 ----------
class Op:
    '''一个增强算子：名字 / 触发概率 / 类别(geometric|photometric) / 变换函数。'''
    def __init__(self, name, p, kind, fn):
        self.name, self.p, self.kind, self.fn = name, p, kind, fn
    def __repr__(self):
        return '%s(p=%.2f, %s)' % (self.name, self.p, self.kind)

def op_hflip(s, rng):                      # 几何：改像素也改标注
    img, b = s['img'][:, ::-1].copy(), s['boxes'].copy()
    W = s['img'].shape[1]
    x1, x2 = b[:, 0].copy(), b[:, 2].copy()
    b[:, 0], b[:, 2] = W - x2, W - x1      # ← 必须交换 x1/x2，否则得到非法框
    return {'img': img, 'boxes': b}

def op_shift(s, rng):                      # 几何：整数平移（roll）
    dx = int(rng.integers(-6, 7))
    b = s['boxes'].copy(); b[:, [0, 2]] += dx
    return {'img': np.roll(s['img'], dx, axis=1), 'boxes': b}

def op_bright(s, rng):                     # 光度：不改标注
    return {'img': s['img'] * float(rng.uniform(0.7, 1.3)), 'boxes': s['boxes']}

def op_noise(s, rng):
    return {'img': s['img'] + rng.normal(0, 0.08, size=s['img'].shape), 'boxes': s['boxes']}

def op_blur(s, rng):                       # 光度：3 点平滑
    x = s['img']
    return {'img': (np.roll(x, 1, 1) + 2 * x + np.roll(x, -1, 1)) / 4.0, 'boxes': s['boxes']}

# ---------- 流水线 ----------
class Pipeline:
    def __init__(self, ops):
        self.ops = ops
        self.hits = collections.Counter()      # 每个算子触发次数
        self.combo = collections.Counter()     # 每个样本触发了几个算子
        self.n = 0
    def __call__(self, sample, rng):
        out, fired = sample, []
        for op in self.ops:
            if rng.random() < op.p:            # ← 每个算子独立掷骰子
                out = op.fn(out, rng); fired.append(op.name)
        self.n += 1; self.combo[len(fired)] += 1
        for f in fired: self.hits[f] += 1
        return out, fired
    def rates(self):
        return {op.name: self.hits[op.name] / max(self.n, 1) for op in self.ops}

OPS = [Op('hflip', 0.5, 'geometric', op_hflip),
       Op('shift', 0.5, 'geometric', op_shift),
       Op('bright', 0.5, 'photometric', op_bright),
       Op('noise', 0.5, 'photometric', op_noise),
       Op('blur', 0.5, 'photometric', op_blur)]
print('流水线:', OPS)

# 顺序检查：几何必须全部排在光度之前
kinds = [o.kind for o in OPS]
assert kinds.index('photometric') > max(i for i, k in enumerate(kinds) if k == 'geometric'), \\
    '几何算子必须全部排在光度算子之前'
print('✅ 顺序合法：几何段', kinds.count('geometric'), '个 -> 光度段', kinds.count('photometric'), '个')"""),

    code("""rng = np.random.default_rng(0)
pipe = Pipeline(OPS)
N = 20000
for _ in range(N):
    pipe(make_sample(rng, n_box=2), rng)

print('%-10s %10s %10s' % ('算子', '配置 p', '实测触发率'))
for op in OPS:
    r = pipe.rates()[op.name]
    print('%-10s %10.2f %10.4f' % (op.name, op.p, r))
    assert abs(r - op.p) < 0.02, op.name          # 单算子：实测≈配置，符合直觉

print()
print('触发个数分布（这才是"实际强度"）:')
for k in range(len(OPS) + 1):
    c = pipe.combo[k]
    print('  触发 %d 个: %6d 次  %6.2f%%  %s' % (k, c, 100 * c / N, '█' * int(60 * c / N)))
p_all = pipe.combo[len(OPS)] / N
p_none = pipe.combo[0] / N
print()
print('全部 5 个都触发的样本占比: %.2f%%  （理论 %.2f%%）' % (100 * p_all, 100 * 0.5 ** 5))
print('一个都不触发的样本占比:   %.2f%%' % (100 * p_none))
assert abs(p_all - 0.03125) < 0.006 and abs(p_none - 0.03125) < 0.006
print()
print('⚠️  单看每个算子都是"一半样本被增强"，合起来却只有 3.1% 的样本走完全套。')
print('   你在 review 配置时脑子里想的那个"最强组合"，模型几乎没见过。')"""),

    md("""## 2 · 概率相乘：精确计算联合触发分布，以及反解每个 p

不要用模拟去估这个分布——它可以**精确算**（k 个算子只有 2^k 种触发组合）。"""),
    code("""def trigger_profile(ps):
    '''精确计算"恰好触发 j 个算子"的概率分布，返回长度 k+1 的数组。'''
    k = len(ps)
    dist = np.zeros(k + 1)
    for mask in itertools.product([0, 1], repeat=k):
        pr = 1.0
        for bit, p in zip(mask, ps):
            pr *= p if bit else (1.0 - p)
        dist[sum(mask)] += pr
    return dist

d = trigger_profile([0.5] * 5)
assert abs(d.sum() - 1.0) < 1e-12
assert abs(d[5] - 1 / 32) < 1e-12 and abs(d[0] - 1 / 32) < 1e-12
assert abs(float((np.arange(6) * d).sum()) - 2.5) < 1e-12
print('5 个算子各 p=0.5 的精确分布:', np.round(d, 5).tolist())
print()

print('%-22s %12s %12s %12s' % ('配置', 'P(全触发)', 'P(全不触发)', 'E[触发个数]'))
for k in (3, 5, 8):
    for p in (0.3, 0.5, 0.8):
        dd = trigger_profile([p] * k)
        print('%-22s %11.2f%% %11.2f%% %12.2f'
              % ('k=%d, p=%.1f' % (k, p), 100 * dd[k], 100 * dd[0], k * p))
print()
print('⚠️  8 个算子各 p=0.5 -> 全触发概率 0.39%，四百分之一。')
print('   这就是"配置强度"与"实际强度"之间的鸿沟。')"""),

    code("""def calibrate_uniform_p(k, target_all):
    '''反解：k 个算子、希望"全部触发"的样本占 target_all，每个算子的 p 该是多少。'''
    return target_all ** (1.0 / k)

print('%-8s %-14s %-10s' % ('算子数 k', '目标联合触发率', '每个算子的 p'))
for k in (3, 5, 8):
    for t in (0.10, 0.30, 0.50):
        p = calibrate_uniform_p(k, t)
        print('%-8d %-14s %-10.4f' % (k, '%.0f%%' % (100 * t), p))
        assert abs(p ** k - t) < 1e-12

p5 = calibrate_uniform_p(5, 0.30)
assert abs(p5 - 0.30 ** 0.2) < 1e-12
print()
print('结论：想让 30%% 的样本走完 5 个算子，每个 p 要 %.3f —— 而不是直觉的 0.5/0.6。' % p5)
print()

# 嵌套 OneOf 的概率折叠：叶子算子的实际触发率
def oneof_leaf_rate(outer_p, weights):
    '''OneOf(ops, p=outer_p) 语义：以 outer_p 进入组，进入后按归一化权重选一个。'''
    w = np.asarray(weights, float)
    return outer_p * w / w.sum()

leaf = oneof_leaf_rate(0.5, [1, 1, 1])
print('OneOf([A,B,C], p=0.5) 里每个叶子的实际触发率:', np.round(leaf, 4).tolist())
assert abs(leaf[0] - 1 / 6) < 1e-12
nested = oneof_leaf_rate(0.5, [1, 1, 1])[0] * 0.6          # 外面再套一层 Compose(p=0.6)
print('再套一层 Compose(p=0.6) 之后:', round(nested, 4))
assert abs(nested - 0.1) < 1e-12
print('⚠️  配置里写着 p=0.5 的算子，实际触发率 10%%。三层嵌套后常见 2%%-3%%。')
print('✅ 唯一可靠的做法：给流水线打点，统计实际触发率，而不是读配置推理。')"""),

    md("""## 3 · 顺序：为什么光度必须放在几何之后

**任何亚像素几何变换都是一次低通滤波。** 先注入的高频扰动会被后续重采样抹掉——
可以精确算出抹掉多少。"""),
    code("""def shift_bilinear(x, dx):
    '''沿最后一维做亚像素平移（双线性）。等价于卷积核 [1-f, f]。'''
    i = int(math.floor(dx)); f = dx - i
    return (1 - f) * np.roll(x, -i, axis=-1) + f * np.roll(x, -(i + 1), axis=-1)

r = np.random.default_rng(1)
noise = r.normal(0, 1.0, size=200000)            # 模拟"注入的高频扰动"
v0 = noise.var()

v_once = shift_bilinear(noise, 0.5).var() / v0                       # 一次半像素平移
seq = noise
for _ in range(3):                                                    # 串联三次（逐算子各 warp 一次）
    seq = shift_bilinear(seq, 0.5)
v_seq3 = seq.var() / v0
v_comp = shift_bilinear(noise, 1.5).var() / v0                        # 合成一次（等效位移 1.5px）

print('%-34s %10s %10s' % ('几何段的做法', '方差保留', '理论值'))
print('%-34s %9.3f %10.4f' % ('一次 0.5px 平移', v_once, 0.5))
print('%-34s %9.3f %10.4f' % ('串联 3 次 0.5px（逐算子 warp）', v_seq3, 20 / 64))
print('%-34s %9.3f %10.4f' % ('合成矩阵一次 warp（等效 1.5px）', v_comp, 0.5))
assert abs(v_once - 0.5) < 0.02
assert abs(v_seq3 - 0.3125) < 0.02, '三重卷积核 [1,3,3,1]/8 -> ||h||^2 = 20/64'
assert abs(v_comp - 0.5) < 0.02
print()
print('结论 A（光度要放后面）：你配置 sigma=0.10 的噪声，若放在几何之前，')
print('   串联几何后实际只剩 sigma=%.4f —— **强度打了对折**。' % (0.10 * math.sqrt(v_seq3)))
print('结论 B（几何要合成矩阵）：串联 3 次比合成 1 次多损失 %.1f%% 的高频能量，'
      % (100 * (v_comp - v_seq3) / v_comp))
print('   而高频正是小目标（8-16px 的交通标志）赖以被检出的信息。')"""),

    code("""# 越界处理必须紧跟几何段：演示"坐标系变了却没清洗"的后果
def clip_and_filter(boxes, W, H, min_area=16.0, min_visible=0.3):
    '''裁剪到画布内 + 按面积/可见比例丢弃残框。返回 (保留的框, 丢弃数)。'''
    b = boxes.copy()
    area0 = np.maximum(b[:, 2] - b[:, 0], 0) * np.maximum(b[:, 3] - b[:, 1], 0)
    b[:, [0, 2]] = np.clip(b[:, [0, 2]], 0, W)
    b[:, [1, 3]] = np.clip(b[:, [1, 3]], 0, H)
    area1 = np.maximum(b[:, 2] - b[:, 0], 0) * np.maximum(b[:, 3] - b[:, 1], 0)
    vis = np.divide(area1, np.maximum(area0, 1e-9))
    keep = (area1 >= min_area) & (vis >= min_visible)
    return b[keep], int((~keep).sum())

rr = np.random.default_rng(7)
s = make_sample(rr, n_box=6)
H, W = s['img'].shape
moved = s['boxes'].copy(); moved[:, [0, 2]] += 40          # 大幅平移 -> 大量越界
kept, dropped = clip_and_filter(moved, W, H)
print('平移后 %d 个框 -> 清洗后保留 %d 个，丢弃 %d 个' % (len(moved), len(kept), dropped))
assert dropped > 0 and len(kept) + dropped == len(moved)
if len(kept):
    w = kept[:, 2] - kept[:, 0]
    print('保留框的最小宽度: %.1f px（阈值挡住了 <4px 的贴边窄条）' % w.min())
    assert (kept[:, 2] - kept[:, 0]).min() * (kept[:, 3] - kept[:, 1]).min() >= 0
print()
print('⚠️  若把清洗放到流水线末尾、中间又插了 Mosaic 的二次拼接，')
print('   裁剪就作用在**错误的画布**上 -> 训练集里凭空出现大量贴边窄条框，')
print('   模型学到"标志可以只有 2 像素宽"，直接污染小目标的尺度先验。')
print('✅ 规则：坐标系一变，立刻清洗。')"""),

    md("""## 4 · DataLoader worker 的 RNG 陷阱（真实事故）

DataLoader 的 worker 是 **fork** 出来的：numpy / python-random 的全局状态被**原样复制**。
PyTorch 只替 torch 自己的 RNG 做了 `base_seed + worker_id`，**numpy 不在此列**——
而绝大多数检测增强库用的正是 numpy。

下面用三种 seed 策略跑同一个 epoch，看增强参数的**去重个数**。"""),
    code("""NUM_WORKERS, N_SAMPLES = 4, 64

def epoch_params(strategy, base_seed, num_workers, n, epoch):
    '''模拟一个 epoch：样本 i 由 worker (i % W) 处理，按顺序从该 worker 的 RNG 取增强参数。'''
    params = [None] * n
    for w in range(num_workers):
        if strategy == 'bad':            # ❌ fork 后全 worker 共享同一状态
            g = np.random.default_rng(base_seed)
        elif strategy == 'worker_only':  # ⚠️ 加了 worker_id 但没加 epoch
            g = np.random.default_rng(base_seed + w)
        elif strategy == 'good':         # ✅ base_seed + epoch + worker_id
            g = np.random.default_rng(
                np.random.SeedSequence(entropy=base_seed, spawn_key=(epoch, w)))
        else:
            raise ValueError(strategy)
        for i in range(w, n, num_workers):
            params[i] = round(float(g.random()), 12)     # 一个样本的增强参数
    return params

p_bad = epoch_params('bad', 1234, NUM_WORKERS, N_SAMPLES, 0)
p_wo = epoch_params('worker_only', 1234, NUM_WORKERS, N_SAMPLES, 0)
p_good = epoch_params('good', 1234, NUM_WORKERS, N_SAMPLES, 0)

print('一个 epoch，%d 个样本，%d 个 worker' % (N_SAMPLES, NUM_WORKERS))
print('%-16s %-16s %s' % ('策略', '不同参数个数', '结论'))
print('%-16s %-16d %s' % ('❌ bad', len(set(p_bad)), '多样性 ÷ %d' % NUM_WORKERS))
print('%-16s %-16d %s' % ('⚠️ worker_only', len(set(p_wo)), 'epoch 内 OK'))
print('%-16s %-16d %s' % ('✅ good', len(set(p_good)), 'epoch 内 OK'))
assert len(set(p_bad)) == N_SAMPLES // NUM_WORKERS == 16
assert len(set(p_wo)) == N_SAMPLES and len(set(p_good)) == N_SAMPLES
print()
print('样本 0/1/2/3 分别由 worker 0/1/2/3 处理，bad 策略下它们的参数:')
print('  ', [round(x, 6) for x in p_bad[:4]], '<- 完全相同')
print('   good 策略下:')
print('  ', [round(x, 6) for x in p_good[:4]], '<- 各不相同')
assert len(set(p_bad[:NUM_WORKERS])) == 1
assert len(set(p_good[:NUM_WORKERS])) == NUM_WORKERS"""),

    code("""# 跨 epoch 的后果：seed 里没有 epoch，整个训练就在重复同一批增强
EPOCHS = 50
totals = {}
for strat in ('bad', 'worker_only', 'good'):
    seen = set()
    for ep in range(EPOCHS):
        seen |= set(epoch_params(strat, 1234, NUM_WORKERS, N_SAMPLES, ep))
    totals[strat] = len(seen)

print('训练 %d 个 epoch，模型总共见过多少种不同的增强参数？' % EPOCHS)
print('%-16s %14s %14s' % ('策略', '总去重个数', '相对正确实现'))
for k, v in totals.items():
    print('%-16s %14d %13.2f%%' % (k, v, 100 * v / totals['good']))
assert totals['bad'] == 16, 'bad: seed 与 worker/epoch 都无关 -> 全程只有 16 种'
assert totals['worker_only'] == N_SAMPLES, 'worker_only: 每个 epoch 完全重复'
assert totals['good'] == N_SAMPLES * EPOCHS
print()
print('❌ bad        : 全程 16 种增强 —— 多样性是正确实现的 %.2f%%' % (100 * 16 / totals['good']))
print('⚠️ worker_only: 每个 epoch 一模一样，训练 50 轮等于只有 1 轮的多样性')
print('✅ good       : 64 × 50 = 3200 种')
print()
print('关键：以上三种都**不会报错、不会 warning、loss 曲线完全正常**。')
print('     你看到的只是"mAP 比论文低两个点"，然后去怪超参和 backbone。')

# 可复现性：同 seed/epoch 必须逐位一致
assert epoch_params('good', 1234, 4, 64, 3) == epoch_params('good', 1234, 4, 64, 3)
# 但换 num_workers 会改变序列 —— 所以复现记录里必须写 num_workers
assert epoch_params('good', 1234, 4, 64, 3) != epoch_params('good', 1234, 8, 64, 3)
print()
print('✅ 同 (seed, epoch, num_workers) -> 逐位可复现')
print('⚠️ 换 num_workers -> 序列改变。"可复现"必须记录 seed + num_workers + 配置哈希 + 库版本。')"""),

    code("""# 把防线写成一条断言：一个 epoch 内增强参数的去重个数必须等于样本数
def assert_aug_diversity(params, n_samples, name=''):
    u = len(set(params))
    if u != n_samples:
        raise AssertionError(
            'worker RNG 疑似共享: 去重参数 %d != 样本数 %d（多样性打了 1/%.1f 折）'
            % (u, n_samples, n_samples / max(u, 1)))
    return True

assert assert_aug_diversity(p_good, N_SAMPLES)
try:
    assert_aug_diversity(p_bad, N_SAMPLES)
    raise RuntimeError('不该走到这里')
except AssertionError as e:
    print('✅ 断言成功拦截:', e)
print()
print('这十行代码写一次、终身受益 —— 把一类"永远查不出原因"的事故变成启动即报错。')"""),
]

NB += [
    md("""## 5 · 吞吐瓶颈：CPU 供给 vs GPU 需求

`throughput = min(W / t_aug, B / t_step)`。
先算出瓶颈在哪一侧，再决定拧哪个旋钮——**不要先动手优化，先做这道算术。**"""),
    code("""def throughput(t_aug_ms, num_workers, gpu_step_ms, batch):
    cpu_ips = num_workers / (t_aug_ms / 1000.0)      # CPU 侧供给 (img/s)
    gpu_ips = batch / (gpu_step_ms / 1000.0)         # GPU 侧需求 (img/s)
    return {'cpu_ips': cpu_ips, 'gpu_ips': gpu_ips,
            'ips': min(cpu_ips, gpu_ips),
            'gpu_util': min(1.0, cpu_ips / gpu_ips),
            'bottleneck': 'CPU(数据增强)' if cpu_ips < gpu_ips else 'GPU(前反向)'}

def min_workers(t_aug_ms, gpu_step_ms, batch):
    '''喂饱 GPU 所需的最少 worker 数。'''
    return int(math.ceil((batch / (gpu_step_ms / 1000.0)) * (t_aug_ms / 1000.0)))

T_STEP, BATCH = 60.0, 32
print('GPU 需求: batch=%d / step=%.0fms = %.1f img/s' % (BATCH, T_STEP, BATCH / (T_STEP / 1000)))
print()
print('%-30s %11s %11s %-16s %9s' % ('配置', 'CPU供给', 'GPU需求', '瓶颈', 'GPU利用率'))
for t_aug, W, tag in [(12.0, 4, '基础增强, W=4'), (12.0, 7, '基础增强, W=7'),
                      (12.0, 8, '基础增强, W=8'), (38.4, 8, '开 Mosaic(≈3.2x), W=8'),
                      (38.4, 21, '开 Mosaic, W=21')]:
    r = throughput(t_aug, W, T_STEP, BATCH)
    print('%-30s %11.0f %11.0f %-16s %8.1f%%'
          % (tag, r['cpu_ips'], r['gpu_ips'], r['bottleneck'], 100 * r['gpu_util']))

assert throughput(12, 4, T_STEP, BATCH)['bottleneck'].startswith('CPU')
assert throughput(12, 8, T_STEP, BATCH)['gpu_util'] == 1.0
assert abs(throughput(12, 4, T_STEP, BATCH)['gpu_util'] - 0.625) < 1e-9
assert min_workers(12.0, T_STEP, BATCH) == 7
assert min_workers(38.4, T_STEP, BATCH) == 21
assert min_workers(5.0, T_STEP, BATCH) == 3
print()
print('喂饱一张卡所需最少 worker: 基础增强 %d 个；开 Mosaic 后 %d 个。'
      % (min_workers(12.0, T_STEP, BATCH), min_workers(38.4, T_STEP, BATCH)))
print('⚠️  一台 8 卡机开 Mosaic 就需要 %d 核 —— 绝大多数机器给不出来。'
      % (8 * min_workers(38.4, T_STEP, BATCH)))
print('   这就是"开了 Mosaic 之后训练明显变慢却查不出原因"的算术解释。')"""),

    code("""# 预取只削峰，不提均值：用 max-plus 递推精确验证
def simulate(prep_times, t_gpu, prefetch):
    '''prefetch 个 batch 在 t=0 已就绪；其余按生产顺序陆续到达。'''
    cum = np.cumsum(prep_times)
    n = len(prep_times)
    end, idle_total = 0.0, 0.0
    for i in range(n):
        avail = 0.0 if i < prefetch else float(cum[i - prefetch])
        idle_total += max(0.0, avail - end)
        end = max(end, avail) + t_gpu
    return {'wall': end, 'idle': idle_total, 'per_step': end / n}

def lognormal_times(rng, n, mean, sigma=0.25):
    mu = math.log(mean) - sigma ** 2 / 2
    return np.exp(rng.normal(mu, sigma, size=n))

rg = np.random.default_rng(11)
N_B, T_GPU = 1000, 0.060

prep_A = lognormal_times(rg, N_B, 0.048)      # 场景 A：CPU 比 GPU 快 25%
prep_B = lognormal_times(rg, N_B, 0.075)      # 场景 B：CPU 比 GPU 慢 25%

print('%-38s %10s %10s %10s' % ('场景 / 预取深度', '每步(ms)', '空转(s)', '相对GPU下限'))
rows = []
for tag, prep in [('A: CPU快25% (mean 48ms)', prep_A), ('B: CPU慢25% (mean 75ms)', prep_B)]:
    for q in (0, 8, 64):
        r = simulate(prep, T_GPU, q)
        rows.append((tag, q, r))
        print('%-38s %10.2f %10.2f %9.2fx'
              % ('%s | q=%d' % (tag, q), 1000 * r['per_step'], r['idle'],
                 r['per_step'] / T_GPU))

A0, A8, A64 = [r for t, q, r in rows if t.startswith('A')]
B0, B8, B64 = [r for t, q, r in rows if t.startswith('B')]
# 单调性：预取只会让空转不增（max-plus 递推的单调性，恒成立）
assert A0['idle'] >= A8['idle'] >= A64['idle']
assert B0['idle'] >= B8['idle'] >= B64['idle']
# 场景 A：CPU 够快，q=8 就已经把 GPU 喂满，每步 = t_gpu
assert abs(A8['per_step'] - T_GPU) < 1e-3, 'CPU 够快时预取能把利用率拉到 100%'
# 场景 B：CPU 不够快，加深预取也救不了
assert B8['per_step'] > T_GPU * 1.10 and B64['per_step'] > T_GPU * 1.10
print()
print('场景 A：q 从 0 -> 8，空转 %.2fs -> %.2fs，每步稳定在 %.1fms = GPU 下限。'
      % (A0['idle'], A8['idle'], 1000 * A8['per_step']))
print('场景 B：q 从 8 -> 64（8 倍队列），每步只从 %.2fms 降到 %.2fms（%.1f%%）。'
      % (1000 * B8['per_step'], 1000 * B64['per_step'],
         100 * (B8['per_step'] - B64['per_step']) / B8['per_step']))
print()
print('✅ 结论：prefetch 是**方差工具**不是**均值工具**。')
print('   把 prefetch_factor 从 2 调到 16 却没变快 -> 你面对的是均值问题，')
print('   唯一出路是降低 t_aug（预解码/合并算子/关库内多线程）或提高 worker 数。')"""),

    md("""## 6 · TTA 与 WBF：多个视角怎么融合

TTA 的 6 个分支给出的是**同一目标的 6 次独立观测**。
NMS 的语义是"选一个删其他"——等于扔掉 5 份可以用来降噪的信息。
WBF 的语义是"分数加权平均 + 按支持分支数重标定分数"。"""),
    code("""def iou1(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0

def nms(boxes, scores, thr=0.55):
    '''返回保留框的下标（按分数降序）。'''
    order = [int(i) for i in np.argsort(-np.asarray(scores))]
    keep = []
    while order:
        i = order.pop(0); keep.append(i)
        order = [j for j in order if iou1(boxes[i], boxes[j]) < thr]
    return keep

def wbf(boxes, scores, n_branches, iou_thr=0.55):
    '''加权框融合：坐标按分数加权平均，分数 = 簇内均分 × min(n, T)/T。'''
    boxes = np.asarray(boxes, float); scores = np.asarray(scores, float)
    clusters = []
    for idx in np.argsort(-scores):
        b, s = boxes[idx].copy(), float(scores[idx])
        best, best_iou = -1, iou_thr
        for ci, c in enumerate(clusters):
            v = iou1(b, c['fused'])
            if v > best_iou:
                best, best_iou = ci, v
        if best < 0:
            clusters.append({'b': [b], 's': [s], 'fused': b.copy()})
        else:
            c = clusters[best]; c['b'].append(b); c['s'].append(s)
            w = np.asarray(c['s']); B = np.asarray(c['b'])
            c['fused'] = (B * w[:, None]).sum(0) / w.sum()     # ← 分数加权平均坐标
    fb = np.asarray([c['fused'] for c in clusters])
    cnt = np.asarray([len(c['s']) for c in clusters])
    fs = np.asarray([float(np.mean(c['s'])) * min(len(c['s']), n_branches) / n_branches
                     for c in clusters])                        # ← 少数分支支持 -> 降分
    return fb, fs, cnt

# 手算校验
bx = np.array([[0., 0., 10., 10.], [1., 1., 11., 11.], [100., 100., 110., 110.]])
sc = np.array([0.9, 0.7, 0.8])
print('IoU(box0, box1) = %.4f' % iou1(bx[0], bx[1]))
fb, fs, cnt = wbf(bx, sc, n_branches=3, iou_thr=0.5)
print('簇大小:', cnt.tolist())
print('融合框 0:', np.round(fb[0], 4).tolist(), ' 分数 %.6f' % fs[0])
print('融合框 1:', np.round(fb[1], 4).tolist(), ' 分数 %.6f' % fs[1])
assert cnt.tolist() == [2, 1]
assert np.allclose(fb[0], [0.4375, 0.4375, 10.4375, 10.4375])   # (0.9*b0+0.7*b1)/1.6
assert abs(fs[0] - 0.8 * 2 / 3) < 1e-12 and abs(fs[1] - 0.8 * 1 / 3) < 1e-12
print('✅ 只被 1/3 分支支持的框，分数被打到 1/3 —— NMS 对这类偶发误检无能为力。')"""),

    code("""# 定位精度对比：3 个 TTA 分支各带独立定位噪声
GT = np.array([100., 100., 150., 150.])
T_BR, TRIALS = 3, 2000
rq = np.random.default_rng(3)
iou_nms, iou_wbf = [], []
for _ in range(TRIALS):
    bs = GT + rq.normal(0, 6.0, size=(T_BR, 4))       # 每个分支独立的定位噪声
    ss = rq.uniform(0.55, 0.95, size=T_BR)
    keep = nms(bs, ss, thr=0.55)
    iou_nms.append(iou1(bs[keep[0]], GT))             # NMS: 就是"最高分那一个"
    fb, fs, _ = wbf(bs, ss, n_branches=T_BR, iou_thr=0.55)
    iou_wbf.append(iou1(fb[int(np.argmax(fs))], GT))

m_nms, m_wbf = float(np.mean(iou_nms)), float(np.mean(iou_wbf))
print('%d 次试验，3 个 TTA 分支，每坐标 sigma=6px（目标 50x50）' % TRIALS)
print('  NMS 融合（=选最高分）  平均 IoU = %.4f' % m_nms)
print('  WBF 融合（=加权平均）  平均 IoU = %.4f' % m_wbf)
print('  提升 = %+.4f' % (m_wbf - m_nms))
assert m_wbf > m_nms + 0.02, 'n 次独立观测取平均，定位方差降到 1/n'
print()
print('原理：n 次独立观测的加权平均，其方差是单次的 1/n（这里 3 个分支 -> sigma 6 -> 3.5）。')
print('NMS 删掉其余 %d 个观测，定位方差一点没降；WBF 把它们全用上了。' % (T_BR - 1))
print('✅ 所以融合多个 TTA / 多模型结果时用 WBF，不要用 NMS。')"""),

    code("""# 车端延迟账：TTA 为什么上不了车
BASE_MS = 8.0                       # 单次推理
SCALES = [0.83, 1.0, 1.25]
FLIPS = 2
FUSION_MS = 1.5

per_scale = [BASE_MS * s * s for s in SCALES]        # 计算量 ∝ 面积
tta_ms = sum(per_scale) * FLIPS + FUSION_MS

print('单次推理           : %.1f ms' % BASE_MS)
for s, c in zip(SCALES, per_scale):
    print('  尺度 %.2f 分支    : %.2f ms' % (s, c))
print('3 尺度 × 2 翻转     : %.2f ms' % (sum(per_scale) * FLIPS))
print('WBF 融合            : %.1f ms' % FUSION_MS)
print('TTA 总计            : %.2f ms  = %.2fx 单次推理' % (tta_ms, tta_ms / BASE_MS))
print()
FRAME_MS = 1000.0 / 30
TSR_BUDGET_MS = 10.0
print('车端预算: 30 FPS -> 每帧 %.1f ms，要装下多路感知+融合+跟踪+规控' % FRAME_MS)
print('          TSR 分到的通常只有 %.0f ms' % TSR_BUDGET_MS)
print('TTA 超出 TSR 预算 %.1f 倍；超出整帧预算 %.1f 倍'
      % (tta_ms / TSR_BUDGET_MS, tta_ms / FRAME_MS))
assert tta_ms > 5 * TSR_BUDGET_MS
assert tta_ms > FRAME_MS
print()
print('⚠️  更致命的是 TTA 的延迟**随目标数波动**（融合是 O(n^2)），破坏 p99 的确定性 ——')
print('    而车端要的恰恰是确定性。**结论：TTA 在量产感知里基本不可用。**')
print('✅ TTA 该出现的地方：① 打伪标签  ② 难例挖掘的一致性信号  ③ 估计模型能力上限')
print('   （TTA 涨得越多，说明你的增强训练做得越差 —— 这是一个诊断信号）')"""),

    md("""## ✏️ 练习 1：联合触发分布与概率反解

实现两个函数：
- `trigger_profile_exact(ps)`：精确返回"恰好触发 j 个"的概率数组（长度 `len(ps)+1`），**不许用模拟**。
- `calibrate_uniform_p(k, target_all)`：k 个同概率算子，希望"全部触发"的样本占 `target_all`，返回每个算子的 p。"""),
    code("""def trigger_profile_exact(ps):
    # TODO: 枚举 2^k 种触发组合，把概率累加到"触发个数"这一维
    raise NotImplementedError

def calibrate_uniform_p_ex(k, target_all):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
d = trigger_profile_exact([0.5] * 5)
assert len(d) == 6 and abs(sum(d) - 1.0) < 1e-12
assert abs(d[5] - 1 / 32) < 1e-12 and abs(d[0] - 1 / 32) < 1e-12
assert abs(float(np.dot(np.arange(6), d)) - 2.5) < 1e-12
d2 = trigger_profile_exact([0.9, 0.2, 0.5])
assert abs(d2[3] - 0.9 * 0.2 * 0.5) < 1e-12
assert abs(d2[0] - 0.1 * 0.8 * 0.5) < 1e-12
d3 = trigger_profile_exact([1.0, 0.5])
assert abs(d3[0] - 0.0) < 1e-12 and abs(d3[2] - 0.5) < 1e-12
p = calibrate_uniform_p_ex(5, 0.30)
assert abs(p ** 5 - 0.30) < 1e-12 and abs(p - 0.30 ** 0.2) < 1e-12
assert abs(calibrate_uniform_p_ex(8, 0.5) ** 8 - 0.5) < 1e-12
print('8 个算子想让 50%% 的样本走完全套 -> 每个 p = %.4f'
      % calibrate_uniform_p_ex(8, 0.5))
print('✅ 练习 1 通过：**先定联合强度，再反解每个 p**，而不是逐个算子拍脑袋')"""),

    md("""## ✏️ 练习 2：正确的 worker seed 策略

实现 `epoch_draws(base_seed, epoch, num_workers, n)`：模拟一个 epoch，
样本 `i` 由 worker `i % num_workers` 处理，返回长度 n 的增强参数列表。
要求：**同一个 epoch 内 n 个参数互不相同；不同 epoch 之间也互不相同；
同 (seed, epoch, num_workers) 逐位可复现。**"""),
    code("""def epoch_draws(base_seed, epoch, num_workers, n):
    # TODO: 每个 worker 用 np.random.SeedSequence(entropy=..., spawn_key=(epoch, worker_id))
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
a = epoch_draws(1234, 0, 4, 64)
b = epoch_draws(1234, 1, 4, 64)
c = epoch_draws(1234, 0, 4, 64)
assert len(a) == 64 and len(set(a)) == 64, 'epoch 内必须 64 个各不相同'
assert len(set(a) & set(b)) == 0, '不同 epoch 不能重复'
assert a == c, '同 (seed, epoch, num_workers) 必须逐位可复现'
d8 = epoch_draws(1234, 0, 8, 64)
assert len(set(d8)) == 64
assert d8 != a, '换 num_workers 会改变序列 —— 复现记录必须写下 num_workers'
assert_aug_diversity(a, 64)
print('epoch0 前 4 个参数:', [round(x, 6) for x in a[:4]])
print('epoch1 前 4 个参数:', [round(x, 6) for x in b[:4]])
print('✅ 练习 2 通过：seed 必须同时含 **base_seed / epoch / worker_id** 三者')"""),

    md("""## ✏️ 练习 3：TTA 分支的逆变换

每个 TTA 分支在"缩放 + 可选翻转"后的图上推理，框必须还原到原图坐标系。
实现 `tta_untransform(boxes, scale, flipped, W)`：`boxes` 是分支输出的 `(N,4) xyxy`，
`scale` 是该分支相对原图的缩放比，`flipped` 表示该分支做过水平翻转，`W` 是**原图宽度**。

⚠️ 翻转的逆变换必须 **交换 x1/x2**，否则得到 `x2 < x1` 的非法框（IoU 恒为 0，症状是"TTA 之后反而掉点"）。"""),
    code("""def tta_untransform(boxes, scale, flipped, W):
    # TODO: ① 先除以 scale 回到原图尺寸  ② 若 flipped，用 W 做镜像并**交换 x1/x2**
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
b0 = np.array([[10., 20., 30., 40.]])
o1 = tta_untransform(b0, scale=2.0, flipped=False, W=200)
assert np.allclose(o1, [[5., 10., 15., 20.]]), o1
o2 = tta_untransform(b0, scale=1.0, flipped=True, W=100)
assert np.allclose(o2, [[70., 20., 90., 40.]]), o2      # x1=100-30, x2=100-10
o3 = tta_untransform(b0, scale=2.0, flipped=True, W=100)
assert np.allclose(o3, [[85., 10., 95., 20.]]), o3      # 先 /2 -> [5,10,15,20]，再镜像
for o in (o1, o2, o3):
    assert (o[:, 2] > o[:, 0]).all() and (o[:, 3] > o[:, 1]).all(), '必须是合法框'
# 忘记交换 x1/x2 的后果
wrong = b0.copy(); wrong[:, 0] = 100 - wrong[:, 0]; wrong[:, 2] = 100 - wrong[:, 2]
assert (wrong[:, 2] < wrong[:, 0]).all()
assert iou1(wrong[0], np.array([70., 20., 90., 40.])) == 0.0
print('忘记交换 x1/x2 得到:', wrong.tolist(), ' -> 与正确框的 IoU =',
      iou1(wrong[0], o2[0]))
print('✅ 练习 3 通过：翻转分支忘记交换 x1/x2 -> 非法框 -> IoU 恒 0 -> "TTA 反而掉点"')"""),

    md("""## ✏️ 练习 4：worker 数规划

实现 `plan_workers(t_aug_ms, gpu_step_ms, batch, cpu_cores)`，返回
`{'cpu_ips','gpu_ips','min_workers','feasible','bottleneck'}`。
`min_workers` = 喂饱 GPU 所需最少 worker 数（向上取整）；
`feasible` = `min_workers <= cpu_cores`；`bottleneck` 按 `cpu_cores` 全开时判断。"""),
    code("""def plan_workers(t_aug_ms, gpu_step_ms, batch, cpu_cores):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
r1 = plan_workers(12.0, 60.0, 32, 16)
assert r1['min_workers'] == 7 and r1['feasible']
assert abs(r1['gpu_ips'] - 533.3333333) < 1e-4
r2 = plan_workers(38.4, 60.0, 32, 16)
assert r2['min_workers'] == 21 and not r2['feasible']
assert r2['bottleneck'].startswith('CPU')
r3 = plan_workers(5.0, 60.0, 32, 16)
assert r3['min_workers'] == 3 and r3['feasible'] and r3['bottleneck'].startswith('GPU')
print('%-34s %8s %8s %10s' % ('配置', '最少W', '可行?', '瓶颈'))
for tag, t, cores in [('基础增强, 16 核', 12.0, 16), ('开 Mosaic, 16 核', 38.4, 16),
                      ('开 Mosaic, 32 核', 38.4, 32), ('预解码后, 16 核', 5.0, 16)]:
    r = plan_workers(t, 60.0, 32, cores)
    print('%-34s %8d %8s %10s' % (tag, r['min_workers'],
                                  '✅' if r['feasible'] else '❌', r['bottleneck']))
print('✅ 练习 4 通过：开增强之前先做这道算术，别等训练慢了再查')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def trigger_profile_exact(ps):
    k = len(ps)
    dist = np.zeros(k + 1)
    for mask in itertools.product([0, 1], repeat=k):
        pr = 1.0
        for bit, p in zip(mask, ps):
            pr *= p if bit else (1.0 - p)
        dist[sum(mask)] += pr
    return dist

def calibrate_uniform_p_ex(k, target_all):
    return target_all ** (1.0 / k)"""),
    code("""# 练习 2 参考答案
def epoch_draws(base_seed, epoch, num_workers, n):
    out = [None] * n
    for w in range(num_workers):
        ss = np.random.SeedSequence(entropy=base_seed, spawn_key=(epoch, w))
        g = np.random.default_rng(ss)
        for i in range(w, n, num_workers):
            out[i] = round(float(g.random()), 12)
    return out"""),
    code("""# 练习 3 参考答案
def tta_untransform(boxes, scale, flipped, W):
    b = np.asarray(boxes, float) / float(scale)      # ① 回到原图尺寸
    if flipped:                                       # ② 镜像并交换 x1/x2
        x1, x2 = b[:, 0].copy(), b[:, 2].copy()
        b[:, 0], b[:, 2] = W - x2, W - x1
    return b"""),
    code("""# 练习 4 参考答案
def plan_workers(t_aug_ms, gpu_step_ms, batch, cpu_cores):
    gpu_ips = batch / (gpu_step_ms / 1000.0)
    need = int(math.ceil(gpu_ips * (t_aug_ms / 1000.0)))
    cpu_ips = cpu_cores / (t_aug_ms / 1000.0)
    return {'cpu_ips': cpu_ips, 'gpu_ips': gpu_ips, 'min_workers': need,
            'feasible': need <= cpu_cores,
            'bottleneck': 'CPU(数据增强)' if cpu_ips < gpu_ips else 'GPU(前反向)'}"""),

    md("""---
## 🧪 真实工程胶囊：一份可直接搬走的流水线配置与自检"""),
    code("""RECIPE = r'''
# ============ 1. DataLoader：seed / 线程 / 预取 ============
import cv2, numpy as np, random, torch
cv2.setNumThreads(0)                    # ★ 第一条：关掉库内多线程，避免 W×N 线程风暴

def worker_init_fn(worker_id):
    seed = torch.initial_seed() % (2 ** 31)   # = base_seed + worker_id，且**每 epoch 变**
    np.random.seed(seed); random.seed(seed)   # ★ torch 会自己处理，numpy/random 不会
    cv2.setNumThreads(0)

loader = torch.utils.data.DataLoader(
    ds, batch_size=32, shuffle=True,
    num_workers=8,                       # ★ 先算 min_workers = ceil(gpu_ips * t_aug)
    worker_init_fn=worker_init_fn,
    generator=torch.Generator().manual_seed(1234),
    persistent_workers=True,             # 避免每 epoch 重启 worker
    prefetch_factor=4,                   # 只削峰，不提均值
    pin_memory=True, drop_last=True,
)

# ============ 2. 增强顺序：混合 -> 几何 -> 清洗 -> 光度 -> 归一 ============
import albumentations as A
GEOM = A.Compose([                                   # ★ 几何段合成一次仿射，只重采样一次
    A.Affine(scale=(0.5, 1.5), translate_percent=(-0.1, 0.1),
             rotate=(-8, 8), shear=(-4, 4), p=0.9),
    A.HorizontalFlip(p=0.5),                         # ★ TSR: 必须配类别白名单（左转/右转！）
], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['labels'],
                            min_area=16, min_visibility=0.3))   # ★ 清洗紧跟几何
PHOTO = A.Compose([                                  # ★ 光度段放在几何之后，否则被插值抹平
    A.HueSaturationValue(hue_shift_limit=8, sat_shift_limit=25,
                         val_shift_limit=25, p=0.7), # ★ TSR: hue 幅度必须 <=10（颜色是语义）
    A.RandomBrightnessContrast(0.2, 0.2, p=0.5),
    A.OneOf([A.MotionBlur(7), A.GaussNoise((5, 30)), A.ImageCompression(40, 85)], p=0.4),
])
# 验证/部署路径：只保留确定性段，**与训练共用同一个 letterbox 函数**
VAL = A.Compose([])   # 仅 letterbox + normalize，写在 collate 之外，train/val/deploy 共享

# ============ 3. 启动自检：三条断言，写一次终身受益 ============
def startup_checks(dataset, loader, n_probe=2000):
    # (a) 实际触发率：不要读配置推理，要打点
    hits = {}
    for i in range(n_probe):
        for name in dataset.last_fired_ops(i):    # 你的 Pipeline 需要记录 fired
            hits[name] = hits.get(name, 0) + 1
    rates = {k: v / n_probe for k, v in hits.items()}
    print('实测触发率:', {k: round(v, 4) for k, v in sorted(rates.items())})
    joint = np.prod([v for v in rates.values()])
    print('联合(全触发)概率: %.4f  <- 常常比你以为的低一个数量级' % joint)

    # (b) worker RNG 多样性：一个 epoch 的增强参数去重数必须等于样本数
    params = collect_aug_params_one_epoch(loader)
    assert len(set(params)) == len(params), \
        'worker RNG 疑似共享！多样性打了 1/num_workers 的折扣'

    # (c) 评测路径必须是纯确定性的：同权重评两次必须逐位相同
    assert evaluate(model, val_loader) == evaluate(model, val_loader), \
        '评测路径残留随机性 -> 所有消融/显著性结论作废'

# ============ 4. 配置指纹：写进 checkpoint 与每行日志 ============
import hashlib, json
def aug_fingerprint(cfg, lib_versions):
    blob = json.dumps({'cfg': cfg, 'lib': lib_versions}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:12]
# 记录: seed / num_workers / 算子顺序+参数+p / 实测触发率 /
#       close_mosaic_epoch / cv2,PIL,albumentations 版本 / 指纹

# ============ 5. TTA（仅离线：伪标签 / 难例挖掘 / 能力上限）============
# 分支: scales [0.83,1.0,1.25] × flip [F,T] = 6 次前向 ≈ 6.5x 延迟
# 每个分支输出后先 tta_untransform（★ 翻转要交换 x1/x2），再 WBF 融合：
#   b_fused = sum(s_i*b_i)/sum(s_i);  s_fused = mean(s)*min(n,T)/T
# 车端预算 8-12ms -> TTA 53ms，超 5 倍且延迟随目标数波动 -> **不上车**
'''
print(RECIPE)
for k in ['setNumThreads(0)', 'worker_init_fn', 'torch.initial_seed', 'persistent_workers',
          'min_visibility', 'hue_shift_limit', 'aug_fingerprint', 'tta_untransform',
          'min(n,T)/T', 'num_workers']:
    assert k in RECIPE, k
print('✅ 配方覆盖：线程/seed/预取 · 顺序与清洗 · 三条启动断言 · 配置指纹 · TTA 与 WBF')"""),

    md("""### 小结

- **顺序**：混合 → 几何（合成一个矩阵、只重采样一次）→ 立刻清洗越界框 → 光度 → 与部署逐位一致的归一化。
  光度放在几何之前，注入的噪声会被插值抹掉 **50%–69%**；几何串联 3 次比合成 1 次多丢 **37.5%** 的高频能量。
- **概率相乘**：5 个算子各 p=0.5，全部触发只有 **3.1%**；8 个各 0.5 只有 **0.39%**。
  想要 30% 的样本走完 5 个算子，每个 p 要 **0.786**。嵌套 `OneOf` 会把叶子触发率再压一个数量级。
  **不要读配置推理，要打点测量。**
- **worker RNG 陷阱**：fork 复制 numpy 全局状态 → 所有 worker 生成**完全相同**的增强序列，
  多样性 ÷ num_workers，**且不报错**。seed 必须同时含 `base_seed / epoch / worker_id`。
  防线是一条断言：**一个 epoch 内增强参数的去重数必须等于样本数。**
- **吞吐**：`min(W/t_aug, B/t_step)`。开 Mosaic 后喂饱一张卡要 21 个 worker。
  **prefetch 只削峰不提均值**——调深了没变快，说明是均值问题，得降 `t_aug`。
- **train/val/deploy 的确定性段必须是同一份代码**；评测路径必须纯确定性，否则消融结论建立在流沙上。
- **TTA 融合用 WBF 不用 NMS**：n 次独立观测取加权平均，定位方差降到 1/n；
  再按支持分支数重标定分数，天然抑制单分支误检。**但 6.5× 延迟 + p99 不确定 → 车端不可用**，
  它的正确用途是打伪标签、难例挖掘的一致性信号、以及估计模型能力上限。

下一站：**模块 05 · 增强的消融与验证** —— 有了这条流水线，怎么证明它真的有用。"""),
]
