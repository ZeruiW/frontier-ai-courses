# -*- coding: utf-8 -*-
"""C57 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "C18（计算机视觉与检测基础：IoU / NMS / anchor / FPN）；C53 的标签分配一节有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("核心参考", "COCO 评测协议中的 AP_S 定义；Lin et al. FPN / RetinaNet；Luo et al. 有效感受野；Xu et al. NWD；Akyon et al. SAHI"),
    ("预计时长", "总览 30 分钟 + 跑 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么：检测里唯一没被架构进步解决的问题", "".join([
        P("过去十年目标检测的整体精度涨了很多，但有一个数字几乎原地踏步：<strong>COCO 上小目标的 AP_S 一直只有大目标 AP_L 的三分之一到二分之一</strong>。换掉 backbone、换掉 neck、从 anchor-based 换到 anchor-free、从 CNN 换到 Transformer——这个比例都没有实质改变。"),
        P("这说明一件重要的事：<strong>小目标之难不是「模型不够强」，而是问题本身在几个不同的地方被同时卡住了</strong>。换一个更强的模型只能缓解其中一两处，剩下几处纹丝不动，所以总账看不到变化。"),
        TABLE(["典型检测器在 COCO 上的表现", "AP_S（面积&lt;32²）", "AP_M", "AP_L", "AP_S / AP_L"], [
            ["Faster R-CNN + FPN", "约 21", "约 43", "约 54", "<strong>0.39</strong>"],
            ["RetinaNet", "约 21", "约 44", "约 54", "<strong>0.39</strong>"],
            ["YOLO 系（同量级）", "约 26", "约 47", "约 58", "<strong>0.45</strong>"],
            ["DETR（单尺度）", "约 20", "约 46", "约 61", "<strong>0.33</strong>"],
            ["Deformable DETR / DINO（多尺度）", "约 32–37", "约 55–58", "约 65–68", "<strong>0.49–0.54</strong>"],
        ]),
        DUAL(
            "这张表里唯一真正把比例往上抬的，是<strong>多尺度</strong>（Deformable DETR、DINO、以及所有带 FPN/P2 的方案）。<em>而多尺度解决的恰恰是「下采样把小目标抹掉了」这一个原因</em>——它对「IoU 阈值不公平」「标注本身带噪」这两条一点忙都帮不上。所以比例只能从 0.33 抬到 0.5 左右，抬不到 1.0。",
            "更严谨的读法是：<strong>AP_S 与 AP_L 的差距是「多个独立瓶颈的乘积」，而不是「一个瓶颈的强度」</strong>。若把五个原因分别记作 <code>r₁…r₅</code>（每个是小目标相对大目标的效率折损），总折损约为它们的乘积。<em>这解释了为什么单点改进的边际收益总是低于预期</em>——修好一个 <code>rᵢ</code>，剩下四个还在乘。反过来，这也是本课把「五个原因」拆开讲的全部理由。",
        ),
        CALLOUT("intuition", "本课要建立的第一个也是最重要的心智模型：<strong>「小目标难」不是一句抱怨，而是五个可以分别量化、分别修复、并且互相正交的工程问题</strong>。面试里被问到「小目标怎么做」，能把这五条拆开、说清每条的量级与对应解法，和只会说「加 FPN、加分辨率、用 copy-paste」是两个完全不同的水平。<em>后者是招式清单，前者是诊断框架。</em>"),
    ])),
    ("define", "「小目标」的三套定义，以及它们并不重合", "".join([
        P("讨论之前必须先约定「多小算小」。工程里流通着三套定义，<strong>它们在同一批数据上给出的答案并不一致</strong>，混用是很多口径争论的根源。"),
        TABLE(["定义", "判据", "优点", "致命弱点"], [
            ["<strong>① 绝对定义（COCO）</strong>", "目标像素面积 &lt; 32² = 1024 px²（即约 32×32 以下）", "客观、可比、评测通用", "<strong>与图像分辨率强耦合</strong>：同一块牌子，1080p 下算小目标，4K 下就不算了，可模型的困难其实没变多少"],
            ["<strong>② 相对定义</strong>", "目标边长 / 图像短边 &lt; 某比例（如 3%），或面积占比 &lt; 0.1%", "对分辨率不变，跨数据集可比", "<strong>与物理距离脱钩</strong>：广角相机拍的近处大牌子和长焦拍的远处小牌子可能给出同一个比例"],
            ["<strong>③ 网络相对定义</strong>", "目标边长 / 最细特征层 stride &lt; 2（即在最细的特征图上不足 2 个格子）", "<strong>直接对应「模型能不能看见」</strong>，是最有工程意义的一套", "依赖具体架构，换网络就要重算，不能写进公开评测"],
        ]),
        DUAL(
            "三套定义的关系可以一句话说清：<strong>① 说的是「相机给了多少像素」，② 说的是「在这张图里它有多不起眼」，③ 说的是「网络还剩多少格子来描述它」</strong>。真正决定检测难度的是 ③，但只有 ① 能写进论文表格。<em>于是就出现了「论文里 AP_S 提升了，换到自己的 1080p 车载数据上完全没动」这种常见困惑</em>——因为两边的 ③ 根本不同。",
            "工程上的正确做法是<strong>三套都不当作唯一标准，而是直接按像素尺寸分桶评测</strong>：把验证集按 <code>√(wh)</code> 切成 <code>[0,16) / [16,24) / [24,32) / [32,64) / [64,+∞)</code> 若干桶，每桶单独算 AP 与召回。<em>任何小目标改进的收益都必须在最小的两个桶里可见，否则它就不是小目标改进</em>。这一点在模块 05 会被做成一套可复用的评测代码；本模块的 notebook 里先把分桶算清楚。",
        ),
        CALLOUT("warn", "一个必须避免的口径事故：<strong>把「小目标」定义在<em>缩放后</em>的输入上，还是<em>原始图像</em>上</strong>。训练时图像被 letterbox 到 640×640，一块原图里 32px 的牌子在网络输入上可能只有 11px。<em>论文报的 AP_S 是在标注坐标系（原图）上算的，而模型看到的是缩放后的</em>。这两个数字差一个缩放因子，讨论时不说清楚就会各说各话。<strong>本课的所有数字，除非特别说明，都是「网络输入坐标系下的像素」</strong>——因为这才是模型真正面对的尺寸。"),
    ])),
    ("five", "小目标难的五个独立原因", "".join([
        P("这是全课的骨架。<strong>请把它当成五个不同的病，而不是一个病的五种症状</strong>——它们的机理不同、量化方式不同、解法不同，而且修好任何一个都不会顺带修好另一个。"),
        ASCII("""一块 8×8 像素的限速牌，从进相机到被判为正样本，要连过五关：

  ①  信息量少          8×8×3 = 192 个数；64×64×3 = 12288 个数（64 倍差距）
      │                 数字笔画在 8px 的牌子上不足 1 像素宽 → **低于奈奎斯特极限**
      │                 病灶：物理层。模型再强也变不出不存在的信息
      ▼
  ②  IoU 对位移极敏感   同样偏 2 像素：8×8 框 IoU=0.391，64×64 框 IoU=0.884
      │                 敏感度 dIoU/dd = -4/s，**与尺寸成反比**
      │                 病灶：度量层。IoU 这把尺子本身对小目标不公平
      ▼
  ③  正样本稀缺        RetinaNet 的最小 anchor 是 32px，8px 目标的
      │                 **最好可能 IoU 只有 (8/32)² = 0.0625** —— 阈值 0.5 下
      │                 永远匹配不到，一个正样本都没有。病灶：分配层
      ▼
  ④  下采样丢失        stride 32 的特征图上，8px 目标只占 0.25 个格子
      │                 （面积 0.0625 格）；有效感受野远小于理论感受野，
      │                 目标只占该神经元有效输入的约 1%。病灶：架构层
      ▼
  ⑤  标注误差相对大    人工标注每条边 ±2px：8px 框的平均 IoU 只有 0.62，
                        **只有 8% 的重标能达到 IoU 0.75** → AP@0.75 在小目标上
                        测的是标注员而不是模型。病灶：数据层

五关的病灶分别在：物理层 / 度量层 / 分配层 / 架构层 / 数据层。
**它们互相正交** —— 加 P2 修的是 ④，换 NWD 修的是 ②③，都修不了 ①⑤。""")
        ,
        TABLE(["原因", "一句话机理", "对应解法（本课模块）", "修好它不会顺带修好"], [
            ["① 信息量少", "像素预算不足，判别性细节低于采样极限", "提分辨率 / 长焦相机 / 切片推理 / ROI 精检（<strong>m04、m05</strong>）", "②③④⑤ —— 信息多了，IoU 阈值还是一样不公平"],
            ["② IoU 对位移敏感", "IoU 随<em>绝对</em>位移的衰减率 ∝ 1/s", "换度量：NWD / KLD / 尺度自适应阈值（<strong>m03</strong>）", "①④ —— 换尺子不增加信息，也不改变特征分辨率"],
            ["③ 正样本稀缺", "anchor 与阈值的组合让小目标匹配不到监督", "改分配：ATSS / SimOTA / RFLA / center-based（<strong>m03</strong>）", "①⑤ —— 有了正样本，标签仍然带噪"],
            ["④ 下采样丢失", "stride 与有效感受野把小目标稀释掉", "FPN/PAN/BiFPN、加 P2、可变形注意力（<strong>m02</strong>）", "②⑤ —— 特征细了，度量与标签的问题原样保留"],
            ["⑤ 标注误差相对大", "固定像素级标注抖动对小框是巨大相对误差", "标注规范、软标签、按尺寸分桶评测、放宽小目标 IoU 判定（<strong>m05</strong>）", "①②③④ —— 标得再准也不会多出像素"],
        ]),
        CALLOUT("danger", "<p>这张表最容易被忽略的是<strong>最后一列</strong>。工程上最常见的浪费，就是<em>反复在同一个原因上加码</em>：AP_S 不涨 → 再加一层 P2 → 再提高一次输入分辨率 → 再换一个更大的 backbone。这些全都在修 ①④，而如果瓶颈其实在 ③（分配根本没给小目标正样本）或 ⑤（标注噪声已经压住了指标上限），<strong>投入再多算力也不会有回报</strong>。</p><p><em>诊断顺序应该是：先看小目标的正样本数（③）→ 再看标注一致性（⑤）→ 再看特征分辨率（④）→ 最后才是加算力（①）</em>。这个顺序在 notebook 里会被写成一个可执行的诊断器。</p>", "别在同一个原因上重复加码"),
    ])),
    ("tsr", "TSR：小目标问题最纯粹的形态", "".join([
        P("交通标志识别（<span class=\"term\">Traffic Sign Recognition, TSR</span>）不是「碰巧也有小目标」的任务，而是<strong>小目标问题的极端样本</strong>。用针孔相机模型算一次就明白了。"),
        MATH("p = f\\cdot\\frac{S}{Z}, \\qquad f = \\frac{W/2}{\\tan(\\mathrm{FOV}_h/2)}"),
        P("其中 <code>p</code> 是标志在图像上的像素直径，<code>f</code> 是以像素为单位的焦距，<code>S</code> 是标志的物理尺寸，<code>Z</code> 是距离，<code>W</code> 是图像宽度。代入一组量产车常见参数：<strong>1920×1080、水平 FOV 60°</strong>，得 <code>f = 960 / tan(30°) ≈ 1662.8 px</code>；国标限速牌直径 <code>S = 0.6 m</code>。"),
        TABLE(["距离 Z", "像素直径 p（1920p / 60° FOV）", "120° 广角", "3840p / 60°", "这个尺寸意味着什么"],[
            ["30 m", "<strong>33.3 px</strong>", "11.1 px", "66.5 px", "刚好越过 COCO 的「小目标」线，可以稳定分类"],
            ["60 m", "<strong>16.6 px</strong>", "5.5 px", "33.3 px", "接近分类的下限：数字笔画约 1–2 px"],
            ["100 m", "<strong>10.0 px</strong>", "3.3 px", "20.0 px", "只能判「有个红色圆牌」，读不出限速值"],
            ["150 m", "<strong>6.7 px</strong>", "2.2 px", "13.3 px", "低于多数检测器的可检下限"],
        ]),
        DUAL(
            "把这张表和车速放在一起就是安全论证：<strong>高速上 120 km/h ≈ 33 m/s。若只能在 60 m 处才把限速值读准，留给系统的反应时间不到 2 秒</strong>；而人类驾驶员通常能在一两百米外就注意到牌子的存在。<em>「多远能检出、多远能读准」这两个距离，直接决定了 TSR 功能的可用性上限</em>——它们是像素预算的函数，不是模型精度的函数。",
            "更进一步，TSR 把五个原因<strong>全部同时触发</strong>：① 100 m 处只有 10 px，限速「60」与「80」的笔画差异低于奈奎斯特极限；② 车辆颠簸与检测抖动带来的 1–2 px 位移，对 10 px 的框就是 IoU 从 1.0 掉到 0.4 以下；③ 标准 anchor 集合完全覆盖不到 10 px；④ 车载模型为了延迟通常最细只到 stride 8，10 px 目标只有约 1 个格子；⑤ 标注员在 10 px 的牌子上画框，边界误差就是 20% 的相对误差。<em>没有哪个通用检测任务能把五条同时踩满。</em>",
        ),
        CALLOUT("intuition", "所以本课与 C55（TSR 与自动驾驶感知）的分工是：<strong>C55 讲「TSR 这个任务本身有哪些工程问题」，本课讲「其中最硬的那一条——目标太小——在物理、度量、分配、架构、数据五个层面各是什么，各能做到什么程度」</strong>。<em>本课的每一节都会在末尾把结论翻译回「对 60 米外的一块限速牌意味着什么」</em>，因为脱离了物理尺寸，小目标的讨论很快会退化成招式罗列。"),
    ])),
    ("map", "课程地图：五个原因 → 五个模块", "".join([
        ASCII("""起点：你有一个在 COCO 上 AP 不错的检测器，但它在 60 米外的限速牌上几乎全漏。

  模块 01  定量分析：小目标到底难在哪            ← 本课的地基
     │      IoU-位移闭式解 / 临界位移 / anchor 匹配上界 /
     │      stride 与格子预算 / 有效感受野 / 标注噪声的相对量级
     ▼      产出：**五个原因各自的数值量级**，以及一张归因表
  模块 02  架构层面的解法（修 ④，部分修 ①）
     │      FPN 层级分配公式 / PAN / BiFPN / 加 P2 的代价账 /
     │      多尺度可变形注意力 / 上下文利用
     ▼      产出：**在给定算力下把特征分辨率花在哪**
  模块 03  分配与损失层面的解法（修 ②③）
     │      center-based 分配 / 尺度自适应阈值 / ATSS / SimOTA /
     │      **NWD：把框建模成高斯，用 Wasserstein 距离替代 IoU** / RFLA
     ▼      产出：**让小目标真的拿到正样本，并有可用的梯度**
  模块 04  切片推理与高分辨率策略（修 ①）
     │      SAHI 切片 / 重叠率下界推导 / 跨片合并 / 计算代价 /
     │      两级级联（低分辨率找 ROI → 高分辨率精检）
     ▼      产出：**在延迟预算内把有效分辨率提上去**
  模块 05  TSR 小目标实战（把 ①–⑤ 组装成方案，并处理 ⑤）
            像素尺寸的物理推导 / 多相机分工 / ROI 裁剪 /
            方案组合的收益-成本排序 / **按像素尺寸分桶的评测**

终点：给定「要在 X 米外检出 Y 厘米的标志、延迟预算 Z 毫秒」，
      你能给出一套有优先级、有代价估算、有验证方案的完整方案。""")
        ,
        TABLE(["模块", "主要修哪个原因", "notebook 里从零做什么"], [
            ["01 定量分析", "<strong>全部五个的量化</strong>", "IoU-位移曲线与临界位移 / anchor 匹配上界 / ERF 数值实验 / 标注噪声模拟"],
            ["02 架构", "④（下采样丢失）", "FPN 层级分配规则 / 加 P2 的 FLOPs 与显存增量 / 加权多尺度融合"],
            ["03 分配与损失", "②（度量）③（分配）", "<strong>NWD 完整实现</strong>与 IoU 的行为对比 / 尺度自适应阈值 / scale-aware 加权"],
            ["04 切片推理", "①（信息量）", "切片生成与坐标还原 / 跨片 NMS / <strong>重叠率下界推导</strong> / 两级级联延迟对比"],
            ["05 TSR 实战", "①⑤ + 方案组装", "像素尺寸求解器 / 收益-成本排序 / <strong>按尺寸分桶的评测</strong>"],
        ]),
        CALLOUT("warn", "与相邻课程的边界要划清，避免重复：<strong>C18 讲检测基础（IoU/NMS/anchor/FPN 是什么）；C53 讲实时检测器架构与标签分配的全谱系；C54 讲 DETR 与集合预测；C55 讲 TSR 的系统设计、失效模式与时序融合；C56 讲检测增强工程</strong>。<em>本课只讲「目标太小」这一条主线</em>——凡是与尺寸无关的检测知识，本课默认你已经会，或者到对应课程去补。"),
    ])),
    ("env", "环境、方法论与怎么用这门课", "".join([
        P("本课全程 <strong>纯 numpy + 标准库、CPU 可跑、不联网</strong>。不需要 GPU、torch、mmdetection 或任何真实数据集。所有 notebook 在 CPU 上实跑验证、<code>assert</code> 全部通过。"),
        CODE("""pip install -r requirements.txt      # numpy / matplotlib / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        P("这个约束不是妥协，而是本课的方法论："),
        UL([
            "<strong>小目标之难的核心全部是可以精确计算的量</strong>——IoU 随位移的衰减是初等代数；anchor 匹配上界是一个面积比；stride 上的格子数是一次除法；有效感受野的宽度是中心极限定理；标注噪声的影响是一次蒙特卡洛。<em>它们不需要训练任何模型就能算清楚，而算清楚之后，「该做什么」几乎是自明的。</em>",
            "<strong>训练一个真模型反而会掩盖机理</strong>。真实实验里 AP_S 涨了 1.5 点，你很难说清是分配变了、还是特征细了、还是碰巧那批数据标得好。<em>而在合成设定下每个变量都可以单独拧</em>，因果关系是干净的。",
            "<strong>凡是结论都要带数字</strong>。本课不接受「小目标特征少所以难」这种说法，只接受「8×8 的 patch 是 192 个数、64×64 是 12288 个数，差 64 倍；且在固定 0.8 px 的镜头模糊下，『60』与『80』的可分性 d′ 从 32px 时的约 90 掉到 8px 时的约 6，衰减约按 D^1.95」这种说法。<em>面试里前者是常识，后者是能力。</em>",
        ]),
        DUAL(
            "怎么用这门课：<strong>模块 01 必须先读透，它是后面四个模块的记账本</strong>。02–04 三个模块彼此独立，可以按你当前的瓶颈跳读；模块 05 是把前面所有东西组装成一套 TSR 方案，建议最后读。<em>如果你时间只够读一个模块，读 01——因为「能把小目标之难量化」本身就是这门课最值钱的产出</em>。",
            "面试视角的用法：<strong>本课的高频考点集中在三处</strong>——① 为什么同一个 IoU 阈值对不同尺度不公平（要能当场推导 <code>IoU = (s-d)²/(2s²-(s-d)²)</code> 并代入数字）；② NWD 相比 IoU 好在哪（尺度不敏感、且在两框不相交时仍有梯度）；③ 切片推理的重叠率该怎么定（要能从「最大目标不被任何切片边界切断」推出下界）。<em>这三处在讲解里都用 <strong>加粗</strong> 标出，并说明面试官想听什么。</em>",
        ),
        CALLOUT("intuition", "最后一句方法论：<strong>本课所有的数值实验都可以在面试白板上重做一遍简化版</strong>。「同样偏 2 像素，8×8 的框 IoU 掉到 0.39，64×64 还有 0.88」——这两个数只需要 <code>(s-d)²/(2s²-(s-d)²)</code> 一个公式，三十秒能算出来。<em>能在白板上把一个定性抱怨变成两个具体数字，是本课想训练的核心能力</em>。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("小目标检测是一个「问题定义清晰、但没有统一解」的方向。当前几条活跃的线索："),
        UL([
            "<strong>度量的重新设计</strong>：NWD、KLD、RFLA 这一类工作的共同主张是「IoU 不是唯一可用的框相似度」。它们在小目标上确有收益，但<em>代价是与主流评测指标（仍以 IoU 为准）脱钩</em>——训练用 NWD、评测用 IoU，两者的最优解不一定重合。「该不该连评测一起换掉」目前没有共识。",
            "<strong>标注噪声下的评测上限</strong>：如果两位标注员在 8px 目标上的一致性 IoU 只有 0.62，那么 AP@[.5:.95] 在小目标桶上究竟测的是什么？<em>「按尺寸自适应的 IoU 阈值」是被反复提出但一直没有被主流评测采纳的方案</em>，因为它会破坏跨数据集可比性。这是一个真实的开放问题。",
            "<strong>高分辨率的算力墙</strong>：提分辨率对小目标几乎总是有效，但代价按分辨率平方增长。<em>稀疏化路线</em>（只在可能有目标的区域做高分辨率计算：稀疏卷积、动态分辨率、query-based 稀疏采样）是当前最有希望绕开平方墙的方向，但工程复杂度与延迟方差都显著上升——对车端尤其敏感。",
            "<strong>时序与多帧超分</strong>：单帧信息不够时，把相邻多帧的亚像素位移利用起来（多帧超分、时序聚合）在理论上能突破单帧的采样极限。<em>TSR 场景对此格外有利</em>：标志是静止的，自车运动可测，位移可预测。这条线在学术上讨论不少，量产落地的公开报道很少。",
            "<strong>合成数据与稀有小目标</strong>：copy-paste 与渲染合成能廉价地制造小目标样本，但「合成的小目标」与「真实的远处小目标」在模糊、噪声、ISP 响应上有系统性差异，<em>过度依赖会训出一个只认识合成模糊的模型</em>。如何度量这个域差，仍然缺少标准工具。",
        ]),
        CALLOUT("paper", "必读（按本课顺序）：<em>Feature Pyramid Networks for Object Detection</em>（Lin et al., 2017 —— 多尺度的奠基，本课模块 02 的基础）；<em>Understanding the Effective Receptive Field in Deep CNNs</em>（Luo et al., 2016 —— 证明 ERF 呈高斯形且半径按 √n 增长，本课模块 01 会数值复现）；<em>A Normalized Gaussian Wasserstein Distance for Tiny Object Detection</em>（Xu et al., 2021 —— NWD，模块 03 的核心）；<em>RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection</em>（Xu et al., ECCV 2022）；<em>Slicing Aided Hyper Inference (SAHI)</em>（Akyon et al., ICIP 2022 —— 切片推理，模块 04）；数据集侧读 <em>TT100K</em>（Zhu et al., CVPR 2016 —— 中国交通标志，小目标 + 长尾的典型）与 <em>AI-TOD / TinyPerson</em> 两个专门的小目标基准。相邻课程：C18（检测基础）、C53（实时检测器与标签分配）、C55（TSR 系统）、C56（检测增强）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 小目标检测 · 环境自检与「五个原因」的数值热身（IoU 敏感性 / anchor 上界 / stride 预算 / ERF / 标注噪声）

本课全程 **纯 numpy + 标准库、CPU、不联网**。因为小目标之难的核心全部是**可以精确计算的量**——
不需要训练任何模型就能算清楚，而算清楚之后「该做什么」几乎是自明的。

**这个 notebook 你会亲手实现：**
1. 两个贯穿全课的基础函数：`iou_xyxy` 与 `square_box`
2. 「小目标」三套定义的**重合度统计**（并证明它们并不重合）
3. **针孔相机模型**：算出 60 米 / 100 米外的限速牌到底有几个像素
4. **五个原因各自的一个数值演示**——每个都给出可引用的具体数字
5. 一个**五因诊断器**：给定一份数据与网络配置，指出瓶颈在哪一条

> 心智模型：**「小目标难」不是一个问题，是五个互相正交的问题。
> 修好一个不会顺带修好另一个 —— 所以必须先诊断，再动手。**"""),
    md("""## 1 · 环境自检与两个基础函数"""),
    code("""import sys, math, platform, json
import numpy as np

print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
print('numpy ', np.__version__)
rng = np.random.default_rng(0)

def iou_xyxy(a, b):
    '''a, b: (..., 4) 的 [x1, y1, x2, y2]。返回逐对 IoU。'''
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    ix = np.maximum(0.0, np.minimum(a[..., 2], b[..., 2]) - np.maximum(a[..., 0], b[..., 0]))
    iy = np.maximum(0.0, np.minimum(a[..., 3], b[..., 3]) - np.maximum(a[..., 1], b[..., 1]))
    inter = ix * iy
    area_a = (a[..., 2] - a[..., 0]) * (a[..., 3] - a[..., 1])
    area_b = (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
    return inter / (area_a + area_b - inter)

def square_box(cx, cy, s):
    '''以 (cx, cy) 为中心、边长 s 的正方形框。'''
    h = s / 2.0
    return np.stack([cx - h, cy - h, cx + h, cy + h], axis=-1)

# 自校验：同框 IoU=1；8px 框对角偏 2px 的 IoU 必须是 36/92
g = square_box(0.0, 0.0, 8.0)
p = square_box(2.0, 2.0, 8.0)
assert np.isclose(iou_xyxy(g, g), 1.0)
assert np.isclose(iou_xyxy(g, p), 36 / 92), iou_xyxy(g, p)
print('iou(同框)          =', float(iou_xyxy(g, g)))
print('iou(8px 框对角偏2px)=', round(float(iou_xyxy(g, p)), 6), '  (= 36/92)')
print('OK 基础函数就位')"""),
    md("""## 2 · 「小目标」的三套定义并不重合

- **① 绝对（COCO）**：`area < 32² = 1024 px²`
- **② 相对**：`√area / 图像短边 < 3%`
- **③ 网络相对**：`√area / 最细 stride < 2`（在最细特征图上不足 2 个格子）

关键实验：**同一批物理目标，只把相机分辨率从 1080p 换到 4K，三套定义给出的「小目标比例」怎么变。**"""),
    code("""def synth_sign_sizes(n=20000, rng=rng):
    '''合成一批 TSR 目标的物理像素直径（1920x1080 / 60deg FOV 下）。

    合成规则（物理合理）：标志物理直径 0.6m 固定，距离 Z 服从 10~150m 的分布
    （近处目标少、中远处多，用 Beta 分布塑形），像素直径 p = f*S/Z。'''
    f = (1920 / 2) / math.tan(math.radians(60 / 2))
    Z = 10 + 140 * rng.beta(2.0, 2.2, size=n)      # 距离 10~150 m
    return f * 0.6 / Z, Z

px_1080, Z = synth_sign_sizes()
px_4k = px_1080 * 2.0                              # 同一场景换 4K 相机：像素直径翻倍

def classify(px, img_short_side, finest_stride):
    area = px ** 2
    return dict(
        abs_coco = area < 32 ** 2,
        relative = px / img_short_side < 0.03,
        network  = px / finest_stride < 2.0,
    )

print(f"{'定义':<26}{'1080p(stride8)':>16}{'4K(stride8)':>14}{'4K(stride16)':>14}")
rows = [('① 绝对 COCO area<32^2', 'abs_coco'),
        ('② 相对 边长/短边<3%',   'relative'),
        ('③ 网络 边长/stride<2',  'network')]
c_a = classify(px_1080, 1080, 8)
c_b = classify(px_4k,   2160, 8)
c_c = classify(px_4k,   2160, 16)
for label, key in rows:
    print(f'{label:<26}{c_a[key].mean():>15.1%}{c_b[key].mean():>14.1%}{c_c[key].mean():>14.1%}')

# 三套定义两两之间的 Jaccard 重合度（同一批 1080p 目标上）
def jac(u, v): return (u & v).sum() / max(1, (u | v).sum())
print()
print('1080p 上三套定义的两两 Jaccard 重合度:')
print(f"  ①vs②  {jac(c_a['abs_coco'], c_a['relative']):.3f}")
print(f"  ①vs③  {jac(c_a['abs_coco'], c_a['network']):.3f}")
print(f"  ②vs③  {jac(c_a['relative'], c_a['network']):.3f}")

assert c_b['abs_coco'].mean() < c_a['abs_coco'].mean(), '换 4K 后「绝对小目标」比例必然下降'
assert np.isclose(c_b['relative'].mean(), c_a['relative'].mean()), '相对定义对分辨率不变'
assert c_c['network'].mean() > c_b['network'].mean(), 'stride 变粗，「网络意义上的小目标」变多'
print()
print('结论: 换 4K 相机 -> 绝对定义的小目标比例下降，但**相对定义纹丝不动**；')
print('      而 stride 从 8 变 16，网络定义的小目标比例立刻上升 —— 模型的困难其实是被 stride 决定的。')
print('==> 三套定义都不完备，工程上必须**直接按像素尺寸分桶**评测。')"""),
    md("""## 3 · 针孔模型：TSR 的像素预算表

$$p = f\\cdot\\frac{S}{Z},\\qquad f=\\frac{W/2}{\\tan(\\mathrm{FOV}_h/2)}$$

这是本课与 TSR 之间的桥。**先算清「有几个像素」，再谈「模型能做到什么」。**"""),
    code("""def focal_px(width_px, hfov_deg):
    '''由图像宽度与水平 FOV 反解以像素为单位的焦距。'''
    return (width_px / 2.0) / math.tan(math.radians(hfov_deg / 2.0))

def sign_px(width_px, hfov_deg, size_m, dist_m):
    return focal_px(width_px, hfov_deg) * size_m / dist_m

def dist_for_px(width_px, hfov_deg, size_m, want_px):
    '''反问：要让标志达到 want_px 像素，最远能在多少米外？'''
    return focal_px(width_px, hfov_deg) * size_m / want_px

CAMS = [('1920x1080 / 60deg 主视', 1920, 60.0),
        ('1920x1080 / 120deg 广角', 1920, 120.0),
        ('1920x1080 / 30deg 长焦', 1920, 30.0),
        ('3840x2160 / 60deg 主视', 3840, 60.0)]
DISTS = [30, 60, 100, 150]

print('国标限速牌 S = 0.6 m 的像素直径')
print(f"{'相机':<26}{'f(px)':>9}" + ''.join(f'{d:>8}m' for d in DISTS))
for name, w, fov in CAMS:
    f = focal_px(w, fov)
    print(f'{name:<26}{f:>9.1f}' + ''.join(f'{sign_px(w, fov, 0.6, d):>9.1f}' for d in DISTS))

f60 = focal_px(1920, 60.0)
assert abs(f60 - 1662.77) < 0.1, f60
assert abs(sign_px(1920, 60.0, 0.6, 60) - 16.63) < 0.05
assert abs(sign_px(1920, 60.0, 0.6, 100) - 9.98) < 0.05

print()
print('反解: 用 1920x1080 / 60deg 主视相机')
for want in [32, 24, 16, 10]:
    d = dist_for_px(1920, 60.0, 0.6, want)
    t = d / (120 / 3.6)     # 120 km/h 下还剩多少秒
    print(f'  要达到 {want:>2d} px，最远 {d:6.1f} m  -> 120km/h 下留给系统 {t:.2f} 秒')
print()
print('这就是 TSR 的核心矛盾: **想早看见 -> 必须接受极小的像素预算**。')"""),
    md("""## 4 · 五个原因，五个数值演示

下面五个 cell 各给出一个可以直接引用的数字。
**请记住这些数字——它们是本课后面所有讨论的锚点。**

### 原因 ① 信息量少：像素预算与奈奎斯特极限"""),
    code("""print('=== 原因 ① 信息量少 ===')
for s in [8, 16, 32, 64]:
    print(f'  {s:>3d}x{s:<3d} RGB patch = {s*s*3:>6d} 个数')
ratio = (64 * 64 * 3) / (8 * 8 * 3)
print(f'  64px 目标的原始像素预算是 8px 目标的 {ratio:.0f} 倍')
assert ratio == 64.0

# 奈奎斯特：限速牌上「数字笔画」的宽度约为牌子直径的 1/8；红环厚度约 1/10。
# 要在采样后还能分辨一条笔画，它至少要占 2 个像素（Nyquist）。
print()
print(f"{'牌子直径 D':>12}{'笔画宽 D/8':>14}{'红环厚 D/10':>14}  可分辨性")
for D in [8, 12, 16, 20, 24, 32, 48]:
    stroke, ring = D / 8, D / 10
    if stroke >= 2:   verdict = '可读出数字（笔画 >= 2px）'
    elif ring >= 2:   verdict = '只能判「有个圆牌」，读不出数字'
    else:             verdict = '连轮廓都在采样极限之下'
    print(f'{D:>10d}px{stroke:>13.2f}{ring:>14.2f}  {verdict}')

D_min_digit = 8 * 2.0     # 笔画 >= 2px
D_min_ring  = 10 * 2.0    # 红环 >= 2px
print()
print(f'==> 分类下限约 {D_min_digit:.0f} px，检测下限约 {D_min_ring:.0f} px。')
print('    对 1920p/60deg 相机，这分别对应 %.0f m 与 %.0f m 之外就无能为力。'
      % (dist_for_px(1920, 60.0, 0.6, D_min_digit), dist_for_px(1920, 60.0, 0.6, D_min_ring)))
assert D_min_digit == 16.0 and D_min_ring == 20.0
print('    **这是物理极限，不是模型能力问题** —— 唯一的解法是给更多像素。')"""),
    md("""### 原因 ② IoU 对位移极敏感（本课最重要的一个数字）"""),
    code("""print('=== 原因 ② IoU 对位移的敏感性 ===')

def iou_after_shift(s, d):
    '''边长 s 的正方形，沿对角线方向 x、y 各偏 d 像素后的 IoU（闭式解）。'''
    inter = max(0.0, s - d) ** 2
    return inter / (2.0 * s * s - inter)

print(f"{'边长 s':>8}" + ''.join(f'{f"d={d}px":>10}' for d in [1, 2, 3, 4]))
for s in [8, 16, 32, 64, 128]:
    print(f'{s:>7d}px' + ''.join(f'{iou_after_shift(s, d):>10.4f}' for d in [1, 2, 3, 4]))

i8, i64 = iou_after_shift(8, 2), iou_after_shift(64, 2)
assert np.isclose(i8, 36 / 92) and np.isclose(i64, 3844 / 4348)
print()
print(f'**同样偏 2 像素：8x8 框 IoU = {i8:.4f}，64x64 框 IoU = {i64:.4f}（差 {i64/i8:.2f} 倍）**')
print('  8x8 的框已经掉到 0.5 阈值以下 —— 会被判成负样本；64x64 的框毫发无伤。')
print()
print('敏感度（在 d=0 处的导数，闭式解 dIoU/dd = -4/s）:')
for s in [8, 64]:
    num = (iou_after_shift(s, 1e-6) - 1.0) / 1e-6
    print(f'  s={s:>3d}px  数值 {num:>9.5f}   公式 -4/s = {-4/s:>9.5f}  (每偏 1px 掉 {-num:.1%} IoU)')
    assert abs(num - (-4.0 / s)) < 1e-3
print()
print('==> **IoU 对绝对位移的敏感度与目标尺寸成反比**。')
print('    而真实的定位误差（标注抖动、特征量化、抖动的相机）大多是**绝对像素量级**的，')
print('    所以同一个 IoU 阈值对小目标是系统性的不公平。')"""),
    md("""### 原因 ③ 正样本稀缺：anchor 匹配的**上界**"""),
    code("""print('=== 原因 ③ 正样本稀缺 ===')
# RetinaNet 的标准 anchor 集合：base {32,64,128,256,512} x scales {2^0, 2^(1/3), 2^(2/3)}
SCALES = [2 ** 0, 2 ** (1 / 3), 2 ** (2 / 3)]
ANCHORS = sorted(b * s for b in [32, 64, 128, 256, 512] for s in SCALES)
print('最小的 6 个 anchor 边长:', [round(a, 1) for a in ANCHORS[:6]])

def best_possible_iou(obj_s, anchors=ANCHORS):
    '''中心完美对齐、形状完美的情况下，方形目标能拿到的**最好** IoU。
    当目标完全落在 anchor 内部时 IoU = 面积比。'''
    return max(min(obj_s, a) ** 2 / max(obj_s, a) ** 2 for a in anchors)

print()
print(f"{'目标边长':>10}{'最好可能 IoU':>16}  能否达到 0.5 阈值")
for s in [4, 8, 12, 16, 20, 24, 32, 64]:
    b = best_possible_iou(s)
    print(f'{s:>8d}px{b:>16.4f}  {"是" if b >= 0.5 else "**否 —— 一个正样本都拿不到**"}')

assert np.isclose(best_possible_iou(8), 0.0625), best_possible_iou(8)
assert best_possible_iou(16) < 0.5 and best_possible_iou(24) >= 0.5
s_min = 32 / math.sqrt(2)
print()
print(f'**8px 目标的最好可能 IoU 只有 {best_possible_iou(8):.4f} = (8/32)^2 —— 注意这是上界，')
print(f'  中心还没偏、形状还没错就已经是这个数了。**')
print(f'  能与 32px anchor 达到 IoU 0.5 的最小目标边长 = 32/sqrt(2) = {s_min:.2f} px。')
print('  ==> 低于约 22.6px 的目标在标准 anchor 集合下**在数学上不可能**成为正样本。')
print('      这正是现代检测器要么把 anchor 聚类到自己数据上、要么干脆放弃 IoU 分配的原因。')"""),
    md("""### 原因 ④ 下采样丢失：stride 上的格子预算"""),
    code("""print('=== 原因 ④ 下采样丢失 ===')
print(f"{'stride':>8}{'层':>6}" + ''.join(f'{f"{s}px目标":>18}' for s in [8, 64]))
print(f"{'':>14}" + ''.join(f'{"(线性格 / 面积格)":>18}' for _ in range(2)))
for stride, lvl in [(4, 'P2'), (8, 'P3'), (16, 'P4'), (32, 'P5')]:
    cols = ''
    for s in [8, 64]:
        lin = s / stride
        cols += f'{f"{lin:.2f} / {lin*lin:.4f}":>18}'
    print(f'{stride:>8d}{lvl:>6}{cols}')

lin32 = 8 / 32
assert np.isclose(lin32, 0.25) and np.isclose(lin32 ** 2, 0.0625)
print()
print(f'**stride 32 的特征图上，8 像素的目标只占 {lin32:.2f} 个格子（面积 {lin32**2:.4f} 格）。**')
print('  也就是说它连一个特征格子都填不满 —— 它与周围的背景共享同一个特征向量。')
print(f'  同一层上 64px 目标占 {64/32:.0f}x{64/32:.0f} = {(64/32)**2:.0f} 个格子，是 {(64/32)**2/lin32**2:.0f} 倍。')
print()
# 加 P2 的代价：head/neck 的空间代价正比于格子总数
base = sum(1.0 / (s ** 2) for s in [8, 16, 32, 64, 128])       # P3..P7
withp2 = base + 1.0 / (4 ** 2)                                  # 加上 P2(stride 4)
print(f'加 P2 的代价: neck+head 的空间格子总数 x{withp2/base:.2f}（P3..P7 -> P2..P7）')
assert 3.9 < withp2 / base < 4.1
print('  ==> 小目标最直接的架构解法（加细特征层）代价是**约 4 倍**，模块 02 会把这笔账算全。')"""),
    md("""### 原因 ⑤ 标注误差的相对量级：**小目标的标签本身就带噪**"""),
    code("""print('=== 原因 ⑤ 标注噪声 ===')
N = 100000
print('模型: 人工标注每条边独立抖动 U(-2, +2) px（这是很温和的假设）')
print(f"{'边长 s':>8}{'平均 IoU':>11}{'P(IoU>=0.5)':>14}{'P(IoU>=0.75)':>15}{'IoU 5%分位':>12}")
res = {}
for s in [8, 16, 32, 64, 128]:
    gt = np.tile(np.array([0.0, 0.0, s, s]), (N, 1))
    nb = gt + rng.uniform(-2, 2, size=(N, 4))
    nb[:, 2] = np.maximum(nb[:, 2], nb[:, 0] + 0.5)   # 防止退化
    nb[:, 3] = np.maximum(nb[:, 3], nb[:, 1] + 0.5)
    v = iou_xyxy(gt, nb)
    res[s] = v
    print(f'{s:>7d}px{v.mean():>11.4f}{np.mean(v >= 0.5):>14.4f}{np.mean(v >= 0.75):>15.4f}'
          f'{np.percentile(v, 5):>12.4f}')

assert 0.60 < res[8].mean() < 0.65, res[8].mean()
assert np.mean(res[8] >= 0.75) < 0.15
assert np.mean(res[64] >= 0.75) > 0.99
print()
print(f'**两位诚实的标注员在 8px 目标上的一致性 IoU 平均只有 {res[8].mean():.2f}，')
print(f'  只有 {np.mean(res[8] >= 0.75):.1%} 的重标能达到 IoU 0.75。**')
print(f'  同样的抖动在 64px 目标上：平均 {res[64].mean():.3f}，达到 0.75 的比例 {np.mean(res[64] >= 0.75):.1%}。')
print()
print('==> 推论（面试可以直接讲）: 在小目标桶上，**AP@0.75 测的是标注员而不是模型**。')
print('    ±2px 对 8px 框是 25% 的相对误差；对 64px 框只有 3%。')
print('    这是一个**数据层**的原因，无论模型多强、特征多细都无法消除。')"""),
    md("""## 5 · 五因归因表与正交性

把上面五个数字放在一起，并**逐条验证「修好一个不会顺带修好另一个」**。"""),
    code("""CAUSES = {
    '1_info':   dict(name='信息量少',        layer='物理层', metric='8px vs 64px 像素预算 64 倍差',
                     fix=['提分辨率', '长焦相机', '切片推理', 'ROI 精检'], module='m04/m05'),
    '2_metric': dict(name='IoU 对位移敏感',  layer='度量层', metric='偏 2px: 0.391 vs 0.884',
                     fix=['NWD', 'KLD', '尺度自适应 IoU 阈值'], module='m03'),
    '3_assign': dict(name='正样本稀缺',      layer='分配层', metric='8px 最好可能 IoU 仅 0.0625',
                     fix=['ATSS', 'SimOTA', 'RFLA', 'center-based 分配'], module='m03'),
    '4_stride': dict(name='下采样丢失',      layer='架构层', metric='stride32 上 8px 只占 0.25 格',
                     fix=['FPN/PAN/BiFPN', '加 P2', '可变形注意力'], module='m02'),
    '5_label':  dict(name='标注误差相对大',  layer='数据层', metric='8px 重标一致性 IoU 仅 0.62',
                     fix=['标注规范', '软标签', '按尺寸分桶评测'], module='m05'),
}
# 每种解法真正能修的原因（工程共识；用来验证正交性）
FIX_EFFECT = {
    '提分辨率': {'1_info', '4_stride'}, '长焦相机': {'1_info'},
    '切片推理': {'1_info', '4_stride'}, 'ROI 精检': {'1_info', '4_stride'},
    'NWD': {'2_metric', '3_assign'}, 'KLD': {'2_metric', '3_assign'},
    '尺度自适应 IoU 阈值': {'2_metric', '3_assign'},
    'ATSS': {'3_assign'}, 'SimOTA': {'3_assign'}, 'RFLA': {'3_assign'},
    'center-based 分配': {'3_assign'},
    'FPN/PAN/BiFPN': {'4_stride'}, '加 P2': {'4_stride'}, '可变形注意力': {'4_stride'},
    '标注规范': {'5_label'}, '软标签': {'5_label'}, '按尺寸分桶评测': {'5_label'},
}
print(f"{'原因':<16}{'病灶':<8}{'量化':<32}{'模块'}")
for k, v in CAUSES.items():
    print(f"{v['name']:<16}{v['layer']:<8}{v['metric']:<32}{v['module']}")

# 正交性：**没有任何单一解法能覆盖全部五个原因**
covered_by_best = max(len(FIX_EFFECT[f]) for f in FIX_EFFECT)
assert covered_by_best < 5, '若存在覆盖全部五因的银弹，本课就不必存在了'
union_all = set().union(*FIX_EFFECT.values())
assert union_all == set(CAUSES), '所有解法合起来才覆盖全部五因'
print()
print(f'单一解法最多覆盖 {covered_by_best} 个原因；要覆盖全部 5 个，至少需要组合多条。')

# 求一个最小覆盖集（贪心）
remaining, chosen = set(CAUSES), []
while remaining:
    best = max(FIX_EFFECT, key=lambda f: len(FIX_EFFECT[f] & remaining))
    chosen.append(best); remaining -= FIX_EFFECT[best]
print('贪心最小覆盖集:', ' + '.join(chosen))
assert len(chosen) >= 3, '至少要三类不同层面的手段才能覆盖五因'
print('==> **小目标方案必然是组合方案**，而且必须横跨架构 / 分配 / 数据三个层面。')"""),
    md("""## ✏️ 练习 1：像素预算求解器

实现 `plan_camera(size_m, need_px, dist_m, width_px)`：
给定标志物理尺寸、需要的像素数、需要的检出距离、图像宽度，
**反解出所需的水平 FOV（度）**。若所需 FOV 落在实用区间 `[10, 179)` 之外则返回 `None`
（太窄 = 极端长焦，视野覆盖不了车道；太宽 = 物理上做不出来）。

提示：由 `p = f·S/Z` 与 `f = (W/2)/tan(FOV/2)` 反解 `FOV = 2·atan((W/2)·S/(Z·p))`。"""),
    code("""def plan_camera(size_m, need_px, dist_m, width_px=1920):
    # TODO: 反解所需水平 FOV（度）；落在 [10, 179) 之外返回 None
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
fov = plan_camera(0.6, 16, 60, 1920)
assert fov is not None and abs(fov - 60.0) < 2.0, fov     # 正好是主视相机的配置
fov2 = plan_camera(0.6, 16, 120, 1920)
assert fov2 is not None and fov2 < fov, '要看更远 -> 需要更窄的 FOV（长焦）'
assert plan_camera(0.6, 32, 100, 1920) is not None
assert plan_camera(0.6, 32, 300, 1920) is None, '需要约 6.9 度的极端长焦 -> 判为不可行'
assert plan_camera(0.05, 40, 500, 1920) is None, '要求太苛刻时应判为不可行'
print(f"{'需求':<34}{'所需 HFOV':>12}")
for need, dist in [(16, 60), (16, 100), (32, 60), (24, 150), (32, 300)]:
    v = plan_camera(0.6, need, dist, 1920)
    txt = f'{v:.1f} deg' if v else '不可行'
    print(f'{f"0.6m 牌 / {need}px / {dist}m":<34}{txt:>12}')
print('✅ 练习 1 通过：**先算像素预算，再选相机** —— 这是 TSR 方案的第一步')"""),
    md("""## ✏️ 练习 2：按尺寸分桶

实现 `size_buckets(px_array, edges)`：给定一批目标的像素边长与桶边界，
返回 `{桶名: 该桶内目标数}`，桶名形如 `'[16,24)'`，最后一桶为 `'[64,inf)'`。
桶必须**左闭右开**，且所有目标恰好被分到一个桶。"""),
    code("""def size_buckets(px_array, edges=(0, 16, 24, 32, 64)):
    # TODO: 返回 OrderedDict 风格的 {桶名: 计数}
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
b = size_buckets(np.array([1.0, 15.9, 16.0, 23.9, 24.0, 31.9, 32.0, 63.9, 64.0, 1000.0]))
assert list(b.keys()) == ['[0,16)', '[16,24)', '[24,32)', '[32,64)', '[64,inf)'], list(b.keys())
assert list(b.values()) == [2, 2, 2, 2, 2], list(b.values())
assert sum(b.values()) == 10
bb = size_buckets(px_1080)
assert sum(bb.values()) == len(px_1080)
print(f"{'桶':<12}{'数量':>9}{'占比':>9}")
for k, v in bb.items():
    print(f'{k:<12}{v:>9d}{v/len(px_1080):>9.1%}')
print('✅ 练习 2 通过：**任何小目标改进都必须在最小的两个桶里可见**，否则它不是小目标改进')"""),
    md("""## ✏️ 练习 3：五因诊断器

实现 `diagnose(cfg)`：给定一个配置字典
`{'obj_px':…, 'finest_stride':…, 'min_anchor':…, 'anno_jitter_px':…}`，
返回**按严重度排序**的瓶颈列表 `[(原因key, 严重度 0~1, 一句话建议), ...]`。

严重度定义（都归一到 0~1，越大越严重）：
- `1_info`：`clip(1 - obj_px/16, 0, 1)` —— 16px 是分类下限
- `2_metric`：`clip(1 - iou_after_shift(obj_px, 2)/0.5, 0, 1)` —— 偏 2px 后离 0.5 阈值还差多少
- `3_assign`：`clip(1 - best_possible_iou_1(obj_px, min_anchor)/0.5, 0, 1)`，
  其中 `best_possible_iou_1(s, A) = 1.0 if s >= A else (s/A)**2`
  （**只有比最小 anchor 还小的目标才会吃亏**——比 A 大的目标总能在更大的 anchor 档位上找到匹配）
- `4_stride`：`clip(1 - (obj_px/finest_stride)/2, 0, 1)` —— 不足 2 个格子就算有问题
- `5_label`：`clip(2*anno_jitter_px/obj_px, 0, 1)` —— 抖动占边长的相对量级"""),
    code("""def diagnose(cfg):
    # TODO: 返回 [(cause_key, severity, advice), ...]，按 severity 降序
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
d1 = diagnose(dict(obj_px=10, finest_stride=8, min_anchor=32, anno_jitter_px=2))
keys = [k for k, _, _ in d1]
sev = dict((k, s) for k, s, _ in d1)
assert set(keys) == set(CAUSES), keys
assert all(0.0 <= s <= 1.0 for s in sev.values())
assert [s for _, s, _ in d1] == sorted([s for _, s, _ in d1], reverse=True), '必须按严重度降序'
assert sev['3_assign'] > 0.8, '10px 目标 vs 32px anchor 应当是重度瓶颈'
assert sev['5_label'] > 0.3

d2 = diagnose(dict(obj_px=64, finest_stride=8, min_anchor=32, anno_jitter_px=2))
sev2 = dict((k, s) for k, s, _ in d2)
assert sev2['3_assign'] == 0.0 and sev2['1_info'] == 0.0, '64px 目标不该有这两个瓶颈'
assert sev2['5_label'] < sev['5_label']

print('配置 A: 10px 目标 / stride 8 / 最小 anchor 32 / 标注抖动 2px')
for k, s, adv in d1:
    print(f'  {CAUSES[k]["name"]:<16} 严重度 {s:.2f}  {adv}')
print()
print('配置 B: 64px 目标（同网络）')
for k, s, adv in d2:
    print(f'  {CAUSES[k]["name"]:<16} 严重度 {s:.2f}  {adv}')
print()
print('✅ 练习 3 通过：**先诊断再动手** —— 不要在已经不是瓶颈的原因上继续加码')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def plan_camera(size_m, need_px, dist_m, width_px=1920):
    # p = f*S/Z, f = (W/2)/tan(FOV/2)  =>  tan(FOV/2) = (W/2)*S/(Z*p)
    t = (width_px / 2.0) * size_m / (dist_m * need_px)
    fov = 2.0 * math.degrees(math.atan(t))
    return fov if 10.0 <= fov < 179.0 else None"""),
    code("""# 练习 2 参考答案
def size_buckets(px_array, edges=(0, 16, 24, 32, 64)):
    px_array = np.asarray(px_array, dtype=float)
    out = {}
    bounds = list(edges) + [math.inf]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        name = f'[{lo:g},inf)' if math.isinf(hi) else f'[{lo:g},{hi:g})'
        out[name] = int(np.sum((px_array >= lo) & (px_array < hi)))
    return out"""),
    code("""# 练习 3 参考答案
def diagnose(cfg):
    s = float(cfg['obj_px']); stride = float(cfg['finest_stride'])
    A = float(cfg['min_anchor']); j = float(cfg['anno_jitter_px'])
    clip = lambda v: float(min(1.0, max(0.0, v)))
    best_iou_1 = 1.0 if s >= A else (s / A) ** 2
    sev = {
        '1_info':   clip(1 - s / 16.0),
        '2_metric': clip(1 - iou_after_shift(s, 2) / 0.5),
        '3_assign': clip(1 - best_iou_1 / 0.5),
        '4_stride': clip(1 - (s / stride) / 2.0),
        '5_label':  clip(2 * j / s),
    }
    advice = {
        '1_info':   '提高输入分辨率 / 换长焦 / 切片推理（m04, m05）',
        '2_metric': '换尺度不敏感度量：NWD / KLD（m03）',
        '3_assign': '改标签分配：缩小 anchor、ATSS/SimOTA、RFLA（m03）',
        '4_stride': '加细特征层（P2）或用可变形注意力（m02）',
        '5_label':  '收紧标注规范 + 按尺寸分桶评测，别用 AP@0.75 看小目标（m05）',
    }
    return sorted(((k, v, advice[k]) for k, v in sev.items()), key=lambda t: -t[1])"""),
    md("""---
## 🧪 真实工程胶囊：小目标问题的开场白（可直接复制到你的项目 README）"""),
    code("""RECIPE = r'''
# ── 小目标专项：开工前必须先填的一张表 ───────────────────────────────────
# 任何「小目标不行」的工单，先把下面 8 个数字填出来再讨论方案。

## A. 物理层（决定天花板）
camera            = "1920x1080, HFOV 60deg"          # -> f = (W/2)/tan(FOV/2) = 1662.8 px
target_physical   = 0.60                              # m，国标限速牌直径
required_distance = 60                                # m，功能要求的检出距离
=> pixel_budget   = f * S / Z = 1662.8 * 0.6 / 60 = 16.6 px
   # 判据：分类需要 >= 16px（笔画 >= 2px）；检测需要 >= 20px（红环 >= 2px）
   # 若 pixel_budget 不达标，**先改相机/分辨率，改模型是浪费**

## B. 度量与分配层（决定能否拿到监督）
finest_stride     = 8                                 # 网络最细特征层
min_anchor        = 32                                # 最小 anchor 边长（anchor-free 填 0）
=> cells_per_obj  = pixel_budget / finest_stride = 2.08 格
=> best_iou_bound = (min(s,A)/max(s,A))**2 = (16.6/32)**2 = 0.269
   # **若 best_iou_bound < 分配阈值，该尺寸的目标一个正样本都拿不到**

## C. 数据层（决定指标上限）
anno_jitter_px    = 2                                 # 标注复核实测的每边抖动
=> relative_error = 2*jitter/pixel_budget = 24%
   # 相对误差 > 15% 时，AP@0.75 在该尺寸桶上已经不可信 -> 评测改用 AP@0.5 + 召回

## D. 评测口径（必须先定，否则改进不可见）
size_buckets      = [0,16) [16,24) [24,32) [32,64) [64,inf)   # 单位：sqrt(w*h) 像素
primary_metric    = "recall@[0,24) with FP/km <= X"   # 整体 mAP 会掩盖小目标的变化

## E. 动手顺序（严格按此，别跳步）
1) 算 A —— 像素预算不达标就先解决相机/分辨率/ROI，模型层怎么改都没用
2) 查 B —— 统计小目标桶的**正样本数**；为 0 或极少 -> 先改分配（成本最低、收益最大）
3) 查 C —— 抽 200 个小目标重标，算标注一致性 IoU；< 0.7 -> 先修标注规范
4) 再改架构（加 P2 / 多尺度）—— 代价约 4x，放在最后
'''
print(RECIPE)
for kw in ['pixel_budget', 'best_iou_bound', 'anno_jitter_px', 'size_buckets', '动手顺序']:
    assert kw in RECIPE, kw
print()
print('✅ 胶囊覆盖：物理预算 / 分配上界 / 标注上限 / 评测口径 / 动手顺序')"""),
    md("""### 小结

- **「小目标难」是五个互相正交的问题**：信息量少（物理层）、IoU 对位移敏感（度量层）、
  正样本稀缺（分配层）、下采样丢失（架构层）、标注误差相对大（数据层）。
  **修好一个不会顺带修好另一个**——所以必须先诊断再动手。
- **五个必须记住的数字**：8×8 vs 64×64 的像素预算差 **64 倍**；同样偏 2px 的 IoU 是
  **0.391 vs 0.884**；8px 目标对 32px anchor 的最好可能 IoU 只有 **0.0625**；
  stride 32 上 8px 目标只占 **0.25 个格子**；每边 ±2px 抖动下 8px 框的重标一致性
  IoU 只有 **0.62**（只有 8% 能到 0.75）。
- **三套「小目标」定义并不重合**：绝对定义随分辨率变、相对定义与物理距离脱钩、
  网络相对定义最有工程意义却不能写进公开评测。**结论：直接按像素尺寸分桶评测。**
- **TSR 是小目标最纯粹的形态**：1920p/60° 相机下，60cm 的限速牌在 60 m 处只有 16.6 px、
  100 m 处只有 10 px。**想早看见就必须接受极小的像素预算**，这是物理约束不是模型问题。
- **动手顺序**：像素预算 → 正样本数 → 标注一致性 → 架构。**加算力放在最后**，
  因为它只修五因中的一到两条。

下一站：**模块 01 · 定量分析：小目标到底难在哪** —— 把这五个数字的推导全部补齐。"""),
]
