# -*- coding: utf-8 -*-
"""C54 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python/numpy；C18（目标检测基础：IoU / NMS / mAP）与 C53（实时检测器）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 从零实现匈牙利匹配 / 集合损失 / 注意力 / 可变形采样"),
    ("预计时长", "总览 30 分钟 + 跑 25 分钟"),
]

SECTIONS = [
    ("thesis", "核心命题：把「去重」从推理期挪到训练期", "".join([
        P("这门课只回答一个问题：<strong>检测器能不能一次就吐出一个「不含重复」的目标集合，而不是先吐出上万个候选框、再用 NMS 把重复的删掉？</strong>"),
        P("这个问题听起来像是工程洁癖，其实不是。传统检测器（Faster R-CNN、YOLO、RetinaNet、FCOS）的输出天生是<strong>密集且重复</strong>的：每个空间位置、每个 anchor 都独立地对「我这里有没有目标」做出判断，它们之间<em>没有任何互相协商的机制</em>。于是一块 24×24 像素的限速牌周围，会有几十个格子同时喊「我看到它了」。"),
        DUAL(
            "既然模型自己不去重，就只能在<strong>后处理</strong>里去重——这就是 <span class=\"term\">NMS</span>（non-maximum suppression，非极大值抑制）：按分数排序，留下最高分的，把和它 IoU 超过阈值的全删掉。这套机制统治了目标检测十年，它简单、有效、几乎无参数（就一个 IoU 阈值）。<em>但它有一个无法修补的结构性缺陷：它是一条写死的规则，而不是学出来的行为。</em>",
            "结构性缺陷具体表现为三条：① <strong>阈值是全局的，而「多重叠算重复」是场景相关的</strong>——远处小标志的重复框 IoU 有 0.6，而套装组合牌（大蓝底指路牌里嵌一块限速牌）两个<em>真目标</em>的 IoU 是 0.69，一个阈值不可能同时满足；② <strong>延迟数据依赖</strong>——NMS 的比较次数随候选框数平方增长，目标越多越慢，这让端到端延迟的 p99 不可控；③ <strong>它不可微</strong>，因此这一步的错误无法反传回模型，模型永远学不会「不要输出重复框」。",
        ),
        P("<span class=\"term\">Set prediction</span>（集合预测）给出的答案是：<strong>让模型直接输出一个固定大小的集合，并在训练时就用一对一匹配强迫它「一个目标只准一个预测去认领」</strong>。没被认领的预测被判为「无目标」。于是重复框在<em>训练期</em>就被压制掉了，推理时不需要任何去重步骤。"),
        CALLOUT("intuition", "把这门课浓缩成一句话：<strong>NMS 是在推理期删掉重复，一对一匹配是在训练期不让重复长出来</strong>。前者是打补丁，后者是改目标函数。<em>面试里如果只能记住一句关于 DETR 的话，就记这句</em>——因为几乎所有「DETR 为什么不需要 NMS」的追问都是它的展开。"),
    ])),
    ("paradigm", "两种范式的逐项对照", "".join([
        ASCII("""范式 A：密集预测 + NMS（Faster R-CNN / YOLO / RetinaNet / FCOS）

  图像 ──▶ backbone ──▶ 多尺度特征 ──▶ 每个位置/anchor 独立打分回归
                                        │
                                        ▼
                                  ~10^4–10^5 个候选框（**大量重复**）
                                        │  score 阈值
                                        ▼
                                  ~10^2–10^3 个候选框
                                        │  **NMS（不可微、O(n^2)、阈值全局）**
                                        ▼
                                  最终框（希望没重复）

范式 B：集合预测（DETR 家族）

  图像 ──▶ backbone ──▶ encoder ──▶ decoder(N 个 object query)
                                        │
                                        ▼
                                  **恰好 N 个预测**（N=100/300，含大量 "no-object"）
                                        │  只需 score 阈值 / top-k
                                        ▼
                                  最终框（**结构上就不含重复**）

  训练时多一步：预测集合 ⟷ GT 集合 做**二分图最优匹配**，再算集合损失。
  推理时少一步：**没有 NMS**。""")
        ,
        TABLE(["", "范式 A：密集预测 + NMS", "范式 B：集合预测"], [
            ["输出数量", "随图像内容变化（10⁴ 起，经阈值后仍不定）", "<strong>固定 N</strong>（100 / 300 / 900）"],
            ["预测之间是否交互", "❌ 完全独立", "<strong>✅ decoder self-attention 里互相协商</strong>"],
            ["去重发生在", "<strong>推理期</strong>（NMS，不可微）", "<strong>训练期</strong>（一对一匹配，可微目标）"],
            ["需要的先验", "anchor 尺寸/比例、层级分配规则、NMS 阈值", "<strong>只有 N</strong>（query 数量）"],
            ["后处理延迟", "随目标数增长，<strong>p99 不可控</strong>", "<strong>常数</strong>（N 次阈值比较）"],
            ["密集重叠目标", "阈值调低会误删真目标", "无抑制步骤，<strong>不存在误删</strong>"],
            ["代价", "工程成熟、收敛快", "<strong>收敛慢（原版 500 epoch）、小目标弱</strong>"],
        ]),
        DUAL(
            "「预测之间是否交互」这一行是<strong>范式差别的真正源头</strong>，其它几行都是它的后果。密集预测里每个格子只看自己感受野内的证据独立作答，<em>它根本没有「别人是不是也在报这个目标」这个信息</em>，所以必然重复。集合预测在 decoder 里让 N 个 query 之间做 self-attention，一个 query 可以「看到」别的 query 已经认领了某个目标，从而把自己压下去。<em>去重能力是从这个交互里长出来的。</em>",
            "严格地说，<strong>self-attention 提供的是「去重的能力」，一对一匹配提供的是「去重的动机」</strong>。两者缺一不可：只有交互没有一对一监督，模型没理由压制重复（多报几个反而召回高）；只有一对一监督没有交互，query 之间无法协调谁让谁，训练会极不稳定。<em>后面模块 03 会看到，把 decoder 的 self-attention 去掉，重复框立刻回来。</em>",
        ),
        CALLOUT("warn", "一个必须澄清的误解：<strong>「DETR 不需要 NMS」不等于「DETR 的输出里没有重复框」</strong>。训练充分的 DETR 重复率很低但不是零；真实量产系统里常常还会挂一个<em>非常宽松</em>的 NMS（IoU 阈值 0.9）做兜底。<em>面试时说「完全不需要」会被追问，说「结构上不需要，工程上常留兜底」才是准确的。</em>"),
    ])),
    ("mech", "三个必须搞懂的机制", "".join([
        P("集合预测不是一个技巧，是三个机制咬合在一起的系统。<strong>拆掉任何一个，另外两个都失效</strong>——这是本课模块 01–03 的组织依据。"),
        TABLE(["机制", "它解决什么", "拆掉它会怎样", "本课在哪讲"], [
            ["<strong>① 二分图最优匹配</strong><br>（Hungarian matching）",
             "预测集合与 GT 集合都<em>无序</em>，损失必须先建立一一对应",
             "<strong>没有对应关系就没法算损失</strong>；用贪心匹配则会得到次优对应，梯度指错方向",
             "<strong>模块 01</strong>（本课最重要的模块）"],
            ["<strong>② 集合预测损失</strong><br>（Hungarian loss）",
             "对匹配上的 query 算分类+框损失，对没匹配上的判 no-object",
             "<strong>不判 no-object 就没有「压制重复」的力</strong>；no-object 不降权则前景被背景淹没",
             "模块 02"],
            ["<strong>③ Object query</strong><br>+ cross/self-attention",
             "N 个可学习的「插槽」去图像里取证据，并彼此协商谁认领谁",
             "<strong>没有 self-attention 就没有去重能力</strong>；没有 cross-attention 就取不到图像证据",
             "模块 03"],
        ]),
        ASCII("""一次训练迭代里三个机制怎么咬合：

  图像 ──▶ 模型 ──▶ 预测集合 {(p_1,b_1), ..., (p_N,b_N)}      ← ③ object query 产生
                                    │
                     GT 集合 {(c_1,g_1), ..., (c_M,g_M)}
                                    │
                        ┌───────────┴───────────┐
                        │  ① 构造 N×M 代价矩阵   │   C_ij = 分类项 + L1 项 + GIoU 项
                        │     求**总代价最小**    │
                        │     的一对一匹配 σ      │   ← 匈牙利算法，O(n^3)
                        └───────────┬───────────┘
                                    ▼
                     matched:  (σ(j), j) ──▶ 分类损失 + 框损失   ┐
                     unmatched: 其余 N−M 个 ──▶ 判为 no-object   ┘ ② 集合损失
                                    │
                                    ▼
                              反传，更新模型

  关键：**匹配本身不参与梯度**（它是一个离散的 argmin，只决定「跟谁算账」），
        但它决定了每个 query 收到什么方向的梯度 —— 所以它比损失本身更关键。""")
        ,
        P("写成一个式子，整个训练目标就是下面这一行——<strong>它把三个机制全串起来了</strong>：<code>σ̂</code> 来自机制 ①，中括号里的两项是机制 ② 的前景部分，最后那个求和是机制 ② 的 no-object 部分（<strong>压制重复的力就在这里</strong>），而所有 <code>p̂</code> 与 <code>b̂</code> 都由机制 ③ 的 N 个 query 产生："),
        MATH("\\mathcal{L}_{\\text{set}} \\;=\\; \\sum_{j=1}^{M}\\Big[\\, -\\log \\hat p_{\\hat\\sigma(j)}(c_j) \\;+\\; \\mathcal{L}_{\\text{box}}\\big(\\hat b_{\\hat\\sigma(j)},\\, b_j\\big) \\Big] \\;+\\; \\lambda_{\\varnothing} \\sum_{i \\,\\notin\\, \\mathrm{Im}(\\hat\\sigma)} -\\log \\hat p_i(\\varnothing)"),
        P("注意 <strong>M 通常只有个位数而 N 是 100</strong>，所以右边那个求和有 90 多项、左边只有几项——<em>这就是 no-object 必须降权（<code>λ_∅</code> 取 0.1）的原因，模块 02 会量化不降权会发生什么。</em>"),
        CALLOUT("intuition", "第三个机制常被误解。<strong>object query 不是「特征」，是「位置/角色的可学习嵌入」</strong>——它更像是一张空白的登记表上的一行，写着「我负责去图像的某个区域找某种尺度的目标」。训练完成后你会发现每个 query 都有明显的空间偏好（模块 03 会实测这个现象）。<em>把 query 理解成「可学习的、带交互能力的 anchor」是最接近本质的类比</em>，但要注意它与 anchor 的三点差别：query 没有显式的几何参数（DAB-DETR 之后才有）、query 之间有 attention 交互、query 与 GT 是一对一而非一对多。"),
    ])),
    ("history", "DETR 换来了什么，代价是什么", "".join([
        P("<strong>DETR</strong>（End-to-End Object Detection with Transformers, ECCV 2020）的历史地位不在于精度——它发布时的 AP 只是<em>持平</em>一个调好的 Faster R-CNN，而且训练要 500 个 epoch。它的地位在于：<strong>它第一次证明了「检测可以不需要 anchor、不需要 NMS、不需要任何手工设计的匹配规则」，整条流水线端到端可微。</strong>"),
        TABLE(["它拿掉了什么", "以前这东西带来什么麻烦", "拿掉之后"], [
            ["<strong>anchor</strong>", "尺寸/比例/层级分配都要按数据集调；TSR 这种极端小目标数据集尤其难调", "只剩一个超参 N"],
            ["<strong>NMS</strong>", "阈值全局、不可微、延迟数据依赖", "后处理变成常数时间"],
            ["<strong>手工标签分配规则</strong>", "MaxIoU / ATSS / SimOTA 各有一堆超参，是精度的胜负手（C53 模块 02）", "分配由匹配算法自动给出"],
            ["<strong>RoI 相关模块</strong>", "RoIAlign、两阶段的 proposal 机制", "结构大幅简化"],
        ]),
        DUAL(
            "代价同样明确，而且都很痛。<strong>① 收敛慢</strong>：原版 500 epoch，而 Faster R-CNN 只要 12–36 epoch，差了一个数量级；<strong>② 小目标弱</strong>：DETR 的 AP_S 明显低于同期 CNN 检测器，因为它只用了单尺度（C5）特征；<strong>③ 训练不稳定</strong>：匹配结果在相邻 epoch 之间会跳变，优化目标一直在动。<em>这三条代价正好定义了后续三年整个 DETR 家族的研究议程。</em>",
            "更精确地说，② 和 ③ 都是 ① 的原因，而 ① 的两个根因是：<strong>cross-attention 在训练初期几乎是均匀分布</strong>（每个 query 对全图所有位置的注意力权重差不多，有效梯度极度稀疏），以及<strong>匹配不稳定</strong>（同一个 GT 在相邻 epoch 被不同 query 认领，被认领的 query 收到的梯度方向来回震荡）。<em>Deformable DETR 主要解决前者（把全局注意力换成每 query 只采样 K 个可学位置），DN-DETR / DINO 主要解决后者（用带噪 GT 作为绕过匹配的额外 query）</em>。模块 04 会把这条线索完整走一遍。",
        ),
        CALLOUT("warn", "<strong>不要把「DETR 精度不如 YOLO」当成结论背下来</strong>。这个说法在 2020 年成立，2023 年之后已经反过来了：RT-DETR 在同等延迟下 AP 高于同期 YOLO，DINO 系长期占据 COCO 榜首。<em>面试里说「DETR 慢/不准」会暴露知识停留在 2020 年</em>。准确的说法是：<strong>原始 DETR 的收敛与小目标问题在 Deformable/DN/DINO 之后已被系统性解决，剩下的真实代价是训练数据量需求更大、部署链路（attention 算子、动态形状）比纯 CNN 复杂。</strong>"),
    ])),
    ("tsr", "对 TSR 意味着什么", "".join([
        P("这门课属于「交通标志识别（TSR）岗位缺口补全」系列，所以每个机制都要落到 TSR 场景上问一句：<strong>它在车上到底能带来什么、又会带来什么新麻烦？</strong>"),
        TABLE(["TSR 的具体痛点", "集合预测怎么帮", "它带来的新麻烦"], [
            ["<strong>延迟 p99 必须可控</strong>：车端 30 FPS 意味着 33 ms 一帧，感知只分到十几毫秒，而 NMS 的耗时随框数波动",
             "后处理变成 N 次阈值比较，<strong>延迟与场景内容无关</strong>——市区密集标志与高速空旷路段耗时相同",
             "attention 算子在 TensorRT 上的支持与优化不如纯卷积；动态形状要小心"],
            ["<strong>组合标志牌</strong>：大指路牌里嵌一块限速牌，两个真目标 bbox 的 IoU 可达 0.69",
             "<strong>没有抑制步骤，就不存在「把真目标当重复删掉」</strong>",
             "两个高度重叠的目标要靠不同 query 认领，对 query 数量与 self-attention 提出要求"],
            ["<strong>类别极多且长尾</strong>：限速 5–120、组合牌、可变电子牌，anchor 与阈值都难以一套通吃",
             "分配由匹配代价自动决定，<strong>不需要为不同类别调 anchor 或 IoU 阈值</strong>",
             "长尾类的匹配代价里分类项弱，容易被框项主导（模块 02 会量化）"],
            ["<strong>小目标为主</strong>：60 m 外的 60 cm 限速牌在 1920×1080 相机上只有约 20 像素",
             "—（原版 DETR 在这一点上<strong>更差</strong>）",
             "<strong>必须上多尺度可变形注意力</strong>（Deformable DETR），否则 AP_S 不可接受"],
        ]),
        DUAL(
            "所以对 TSR 来说，<strong>集合预测的价值主要在「延迟确定性」与「密集重叠场景不误删」，而不是在纸面 AP</strong>。前者直接关系到功能安全（一帧超时就丢一帧感知结果），后者直接关系到组合标志牌这种<em>高频且高危</em>的场景——漏掉主牌下面的辅助牌（「前方 500 m」「货车」），会让限速约束被错误地施加到不该施加的路段上。",
            "但要诚实：<strong>如果直接把原版 DETR 放到 TSR 上，结果会很难看</strong>。单尺度 C5 特征的 stride 是 32，一个 20 像素的标志在特征图上占不到一个格子；100 个 query 里绝大多数会去认领大目标。<em>TSR 场景下可用的 DETR 系必须至少满足两个条件：多尺度输入（P3 甚至 P2）+ 可变形注意力（把全局 attention 的计算量压下来）</em>。这就是为什么本课模块 04 的 Deformable DETR 不是「历史演进的一站」，而是<strong>TSR 落地的前提条件</strong>。",
        ),
        CALLOUT("danger", "<p>一个会让面试当场翻车的说法：<strong>「DETR 没有 NMS，所以延迟更低」</strong>。这在多数情况下是<em>错的</em>——DETR 的 backbone+encoder 通常比同级 YOLO 更重，端到端延迟往往<strong>更高</strong>。正确的说法是：<strong>DETR 的延迟<em>方差</em>更小、p99 更接近 p50，因为它没有随目标数变化的后处理</strong>。<em>车端关心的是尾延迟而不是平均延迟</em>——这个区分能立刻显出你有没有真的做过部署。</p>", "别说「没有 NMS 所以更快」"),
    ])),
    ("map", "课程地图与运行环境", "".join([
        ASCII("""模块 00  课程总览与环境            ← 你在这里
   │     两种范式的输出差异 / 三个机制的分工 / NMS 阈值困境的量化
   ▼
模块 01  二分图匹配与匈牙利算法    ★ 本课最重要
   │     代价矩阵与一对一约束 / 增广路径 / KM 对偶变量 / DETR 三项代价 /
   │     为什么一对一能替代 NMS / **匹配不稳定性**（后面所有工作的动机）
   ▼
模块 02  集合预测损失
   │     Hungarian loss 完整公式 / no-object 权重 / 为什么必须 L1+GIoU /
   │     IoU 家族的梯度性质 / 辅助损失为什么加速收敛
   ▼
模块 03  Object query 与交叉注意力
   │     query 到底是什么 / self-attn（去重协商）vs cross-attn（取证据）/
   │     query 的空间特化 / N 怎么选 / DAB-DETR 的 4D anchor query
   ▼
模块 04  收敛难题与 DETR 家族演进
   │     500 epoch 的两个根因 / Deformable（可变形注意力+多尺度+两阶段）/
   │     DN-DETR（去噪 query 绕过匹配）/ DINO / 一对多匹配的回归
   ▼
模块 05  DETR 工程实践：调参、诊断与选型
         学习率分组 / 小目标弱的根因与解法 / 训练失败诊断树 /
         DETR vs YOLO 工程取舍表 / **给 TSR 选哪个的完整论证**""")
        ,
        TABLE(["模块", "核心机制", "notebook 里从零做什么"], [
            ["01 匈牙利匹配", "线性指派问题、增广路径、对偶变量", "<strong>手写 O(n³) 匈牙利算法</strong>（不许用 scipy）+ 与暴力枚举全排列对拍 + <strong>匹配翻转率量化</strong>"],
            ["02 集合损失", "Hungarian loss、no-object 权重、IoU 家族", "<strong>IoU/GIoU/DIoU/CIoU 及其梯度</strong>（数值梯度校验）+ 完整集合损失 + 权重消融"],
            ["03 object query", "多头注意力、decoder 一层的结构", "<strong>numpy 版多头注意力</strong> + decoder 层 + query 空间特化可视化"],
            ["04 收敛与演进", "可变形注意力、去噪 query", "<strong>可变形采样 + 双线性插值（含梯度）</strong> + DN query 构造与 attention mask"],
            ["05 工程实践", "诊断指标、选型决策", "<strong>匹配翻转率 / 前景 query 占比 / 框中心分布熵</strong> + 选型脚本"],
        ]),
        P("<strong>运行环境</strong>：全课 <span class=\"badge cpu\">CPU</span>，纯 numpy + 标准库，不需要 torch / mmdet / GPU，不联网。所有 notebook 在 CPU 上实跑验证，<code>assert</code> 零失败。"),
        CODE("""pip install -r requirements.txt      # numpy / matplotlib / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        DUAL(
            "为什么不用 torch？<strong>因为本课的难点全部在「机制」而不在「API」</strong>。匈牙利算法是纯组合优化，注意力是三个矩阵乘法，可变形采样是双线性插值——这些用 numpy 写出来<em>反而更清楚</em>，因为没有任何一行被框架藏起来。而 <code>scipy.optimize.linear_sum_assignment</code> 这种一行调用会让你永远不知道匹配是怎么算出来的，<em>而面试恰恰会让你在白板上手写它</em>。",
            "本课与相邻课程的边界：<strong>C18 讲检测基础（IoU/NMS/mAP/anchor），C53 讲实时检测器架构（YOLO 演进 / RTMDet / RT-DETR 的工程取舍），C57 讲小目标，C60 讲部署</strong>。<em>本课只讲「集合预测」这一条主线的机理</em>——RT-DETR 的<em>工程实现</em>在 C53 模块 04，它背后的<em>匹配与集合损失原理</em>在这里。两门课刻意有一处重叠：RT-DETR 既是「实时检测器」也是「DETR 家族」，从两个角度各讲一遍是有意的。",
        ),
        CALLOUT("intuition", "学完本课你应当能在白板上完成这几件事：<strong>手写匈牙利算法并说清它为什么是 O(n³) 而不是 O(n!)；写出 DETR 的匹配代价三项并解释为什么分类项用概率而不是 log；解释「一对一匹配为什么能替代 NMS」并说清它和 self-attention 的分工；说出 DETR 收敛慢的两个根因，以及 Deformable / DN / DINO 各自打的是哪一个；给 TSR 场景在 DETR 系与 YOLO 系之间做选型并给出量化理由。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("集合预测这条线在 2020–2025 之间已经从「有趣的概念验证」变成「SOTA 检测器的默认骨架」，但下面几个问题仍然是开放的。"),
        UL([
            "<strong>一对一与一对多的真正关系</strong>：Group DETR / H-DETR / Co-DETR 都发现「训练时额外加一对多分支、推理时丢掉」能显著涨点。<em>这说明一对一是「推理端的需求」而不是「训练端的最优」</em>——监督信号太稀疏才是 DETR 收敛慢的本质。但「训练时到底该给多稠密的监督」目前只有经验配方，没有理论。",
            "<strong>匹配稳定性的理论刻画</strong>：匹配是一个离散 argmin，代价矩阵的微小扰动可以让整个指派翻转。<em>目前对「什么时候会翻转、翻转多严重才影响收敛」只有实验观察</em>（模块 01 的 notebook 会量化它），Stable-DINO 等工作提出用定位质量给分类分数加权来稳定匹配，但仍是启发式。",
            "<strong>query 数量 N 的自适应</strong>：N 固定意味着「单图目标数超过 N 就必然漏检」，而且 N 越大正样本占比越低。<em>能否让 N 随场景自适应</em>（稀疏场景少算几个 query）是部署上很有价值但尚未解决的问题——对 TSR 这种「大部分帧只有 0–3 块标志、偶尔路口有十几块」的极不均匀分布尤其重要。",
            "<strong>端到端与可解释性的矛盾</strong>：集合预测把「谁负责哪个目标」交给了匹配算法，好处是不用手工设计规则，坏处是<em>出问题时很难归因</em>——一个目标漏检，是 query 不够、是匹配把它让给了别的 query、还是 cross-attention 没取到证据？模块 05 会给一套诊断指标，但这仍是工程上的痛点。",
            "<strong>与 VLA / BEV 的接口</strong>：DETR 的输出天然是「一组带语义的 object token」，这比密集特征图更容易接到下游的语言模型或 BEV 融合模块上。<em>「检测器的输出应该是框还是 token」正在被重新讨论</em>（见 C59）。",
        ]),
        CALLOUT("paper", "必读（按阅读顺序）：<strong>★ Carion et al., <em>End-to-End Object Detection with Transformers</em>（DETR, ECCV 2020）</strong>——重点读 §3 的 set prediction loss 与匹配定义；<strong>★ Zhu et al., <em>Deformable DETR</em>（ICLR 2021）</strong>——重点读可变形注意力的定义与「为什么 DETR 收敛慢」的分析；<strong>★ Li et al., <em>DN-DETR</em>（CVPR 2022）</strong>——它对「匹配不稳定」的量化实验是本课模块 01 的直接来源；<strong>★ Zhang et al., <em>DINO</em>（ICLR 2023）</strong>；Zhao et al., <em>RT-DETR</em>（CVPR 2024）；Kuhn, <em>The Hungarian Method for the Assignment Problem</em>（1955，匈牙利算法原始论文，只有 12 页，值得读）。相邻课程：C18（检测基础）、C53（实时检测器）、C57（小目标）、C60（车端部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与两种范式的输出差异（NMS / 一对一匹配 / 集合损失）

目标：用一个**合成的 TSR 场景**把「密集预测 + NMS」和「一对一集合预测」两种范式
放在同一组数据上跑一遍，亲眼看到它们的输出差在哪、代价差在哪。

本 notebook 你会亲手实现：
1. **IoU 矩阵与 NMS**，并测出「同一场景里 NMS 阈值从 0.59 变到 0.60，输出框数从 5 跳到 6」
2. **NMS 阈值的可行窗口**，并在一个真实 TSR 场景（组合标志牌）上证明**这个窗口是空的**
3. **一对一集合预测的输出**：不做任何抑制，重复率天然为 0
4. **最小版的三机制玩具**：代价矩阵 → 暴力最优匹配 → 集合损失
5. **后处理代价对比**：NMS 的 O(n²) vs 集合预测的 O(N)

> 心智模型：**NMS 是在推理期删掉重复，一对一匹配是在训练期不让重复长出来。**"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, json, math, itertools
import numpy as np

print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
print('numpy ', np.__version__)
for name in ['torch', 'scipy', 'mmdet']:
    try:
        mod = __import__(name)
        print(f'  {name:<8s} {getattr(mod, "__version__", "?")}  (本课**不使用**它)')
    except ImportError:
        print(f'  {name:<8s} 未安装  ->  本课本来就不需要')

rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)
print('\\n✅ 环境就绪：纯 numpy + 标准库，CPU，不联网。')
print('⚠️  本课**禁止** scipy.optimize.linear_sum_assignment —— 匈牙利算法要在模块 01 手写。')"""),
    md("""## 2 · 合成一个 TSR 场景：一块牌，几个框？

1920×1080 的车载前视图像，三块交通标志：一块远处的小限速牌（24×24 px）、
一块中距禁令牌（40×40 px）、一块近处警告牌（60×60 px）。

**密集预测器**对每块牌都会吐出好几个高分框（因为周围好几个格子/anchor 都判定「这里有目标」），
外加两个背景误检（路边广告牌、前车车身贴纸）——这两类是 TSR 里最经典的假正例来源。"""),
    code("""# GT：xyxy 像素坐标
GT = np.array([
    [ 900., 300.,  924.,  324.],   # 0  远处限速60      24x24 px
    [1200., 380., 1240.,  420.],   # 1  中距禁止超车    40x40 px
    [ 640., 420.,  700.,  480.],   # 2  近处注意行人    60x60 px
])
GT_NAME = ['限速60(远,24px)', '禁止超车(中,40px)', '注意行人(近,60px)']

def shift(box, dx, dy):
    return box + np.array([dx, dy, dx, dy], dtype=float)

# 每块牌配几个「重复框」：位移几个像素、分数递减 —— 这就是密集预测器的真实行为
_SPEC = [
    ([0, 3, -3, 2], [0, 0, 2, -3], [0.92, 0.85, 0.78, 0.71]),   # GT0 的 4 个框
    ([0, 5, -4, 6], [0, 0, 4, -5], [0.88, 0.80, 0.74, 0.69]),   # GT1 的 4 个框
    ([0, 8, -6],    [0, 0, 6],     [0.95, 0.83, 0.72]),         # GT2 的 3 个框
]
_rows = []
for k, (dxs, dys, scs) in enumerate(_SPEC):
    for dx, dy, s in zip(dxs, dys, scs):
        _rows.append((shift(GT[k], dx, dy), s, k))
_rows.append((np.array([ 300., 600.,  340., 640.]), 0.61, -1))   # 背景误检：路边广告牌
_rows.append((np.array([1500., 200., 1530., 230.]), 0.55, -1))   # 背景误检：前车车身贴纸

P_BOX   = np.array([r[0] for r in _rows])
P_SCORE = np.array([r[1] for r in _rows])
P_SRC   = np.array([r[2] for r in _rows])       # 这个框来自哪个 GT，-1 表示背景误检

print(f'GT 数量        : {len(GT)}')
print(f'密集预测框数量 : {len(P_BOX)}   (其中背景误检 {int((P_SRC == -1).sum())} 个)')
print(f'{"idx":>3s} {"来源":>16s} {"score":>6s}  box')
for i in range(len(P_BOX)):
    src = GT_NAME[P_SRC[i]] if P_SRC[i] >= 0 else '背景误检'
    print(f'{i:>3d} {src:>16s} {P_SCORE[i]:>6.2f}  {P_BOX[i]}')

assert len(P_BOX) == 13 and (P_SRC == -1).sum() == 2
print('\\n⚠️  3 块牌 -> 13 个高分框。**模型自己不去重**，因为每个位置都是独立判断的。')"""),
    md("""## 3 · 范式 A：密集预测 + NMS

NMS 的规则只有一句：**按分数从高到低，保留当前最高分的框，删掉所有与它 IoU 超过阈值的框。**

先实现 IoU 矩阵和 NMS，然后扫一遍阈值，看输出框数怎么变。"""),
    code("""def iou_matrix(a, b):
    \"\"\"a:(N,4) b:(M,4) 均为 xyxy -> (N,M) 的 IoU 矩阵。\"\"\"
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-12)

def nms(boxes, scores, iou_thr, score_thr=0.5):
    \"\"\"贪心 NMS：返回保留下来的框下标（按分数降序）。\"\"\"
    idx = np.where(scores >= score_thr)[0]
    idx = idx[np.argsort(-scores[idx])]
    keep = []
    while len(idx):
        i = idx[0]
        keep.append(int(i))
        if len(idx) == 1:
            break
        ious = iou_matrix(boxes[i:i + 1], boxes[idx[1:]])[0]
        idx = idx[1:][ious <= iou_thr]          # IoU 超过阈值的被抑制
    return keep

# 自校验：一个框和自己的 IoU 必须是 1
assert abs(iou_matrix(P_BOX[:1], P_BOX[:1])[0, 0] - 1.0) < 1e-9
# 手算校验：GT0 的框 [900,300,924,324] 与它右移 3px 的副本
#   交集 21*24=504，并集 576*2-504=648  ->  IoU = 504/648 = 0.7778
assert abs(iou_matrix(P_BOX[0:1], P_BOX[1:2])[0, 0] - 504 / 648) < 1e-9
print('IoU 实现通过手算校验 ✅  (0.7778 = 504/648)')

print(f'\\n{"IoU 阈值":>10s} {"保留框数":>10s}   说明')
for t in [0.10, 0.30, 0.50, 0.59, 0.60, 0.70, 0.90]:
    k = nms(P_BOX, P_SCORE, t)
    note = '重复框全被删掉（3 真 + 2 误检）' if len(k) == 5 else \\
           ('几乎不抑制，13 个框全留' if len(k) == 13 else '开始漏删重复框')
    print(f'{t:>10.2f} {len(k):>10d}   {note}')

assert len(nms(P_BOX, P_SCORE, 0.50)) == 5
assert len(nms(P_BOX, P_SCORE, 0.70)) == 10
assert len(nms(P_BOX, P_SCORE, 0.90)) == 13
print('\\n⚠️  阈值从 0.59 到 0.60，输出就从 5 个变成 6 个 —— **NMS 对阈值是硬切换，没有过渡带**。')"""),
    code("""# 「每个 GT 被几个框认领」—— 这就是重复率
def duplicates_per_gt_ref(pred_boxes, pred_scores, gt_boxes, score_thr=0.5, iou_thr=0.5):
    M = iou_matrix(pred_boxes, gt_boxes)
    return ((pred_scores[:, None] >= score_thr) & (M >= iou_thr)).sum(axis=0)

before = duplicates_per_gt_ref(P_BOX, P_SCORE, GT)
keep = nms(P_BOX, P_SCORE, 0.50)
after = duplicates_per_gt_ref(P_BOX[keep], P_SCORE[keep], GT)

print(f'{"GT":>18s} {"NMS 前":>8s} {"NMS 后":>8s}')
for j in range(len(GT)):
    print(f'{GT_NAME[j]:>18s} {before[j]:>8d} {after[j]:>8d}')
assert list(before) == [4, 4, 3] and list(after) == [1, 1, 1]
print('\\n✅ NMS 确实把重复率从 [4,4,3] 压到 [1,1,1] —— 它是有效的。')
print('   问题不在「有没有效」，而在「它是一条写死的全局规则」。下一节量化这一点。')"""),
    md("""## 4 · NMS 的阈值困境：一个真实的 TSR 反例

NMS 的 IoU 阈值必须同时满足两个互相冲突的要求：

- **要删掉重复框** → 阈值必须 **低于**「同一目标的重复框之间的 IoU」
- **要保住重叠的真目标** → 阈值必须 **不低于**「两个真目标之间的 IoU」

这两个条件在同一个数据集上未必有交集。下面用一个 TSR 里天天见的场景来证明：
**组合标志牌**——一块大的蓝底指路牌里嵌着一块限速牌，两个都是**必须检出的真目标**。"""),
    code("""# 重复框与「它所属 GT 的最高分框」之间的 IoU
top_of = [int(np.argmax(np.where(P_SRC == k, P_SCORE, -1.0))) for k in range(len(GT))]
dup_ious = []
for k in range(len(GT)):
    for i in np.where(P_SRC == k)[0]:
        if i != top_of[k]:
            dup_ious.append(float(iou_matrix(P_BOX[top_of[k]:top_of[k]+1], P_BOX[i:i+1])[0, 0]))
dup_ious = np.array(dup_ious)
print('重复框对的 IoU :', np.round(dup_ious, 4))
print(f'  -> 要删光重复框，阈值必须 < {dup_ious.min():.4f}')

# 组合标志牌：大指路牌 120x120，里面嵌一块 100x100 的限速牌（**两个都是真目标**）
OUTER = np.array([[980., 560., 1100., 680.]])    # 蓝底指路牌
INNER = np.array([[990., 570., 1090., 670.]])    # 嵌在里面的限速牌
iou_pair = float(iou_matrix(OUTER, INNER)[0, 0])
print(f'\\n组合标志牌：外牌与内牌的 IoU = {iou_pair:.4f}  (= 10000/14400，内牌完全被外牌包住)')
print(f'  -> 要同时保住这两个真目标，阈值必须 >= {iou_pair:.4f}')

lo, hi = iou_pair, float(dup_ious.min())
print(f'\\n可行阈值窗口 = [{lo:.4f}, {hi:.4f})   ->  {"非空" if lo < hi else "**空集**"}')
assert lo > hi, '这个场景下窗口应当是空的'
print('❌ 没有任何一个 IoU 阈值能同时做到「删光重复」和「不误删真目标」。')

# 实测：用能删光重复的阈值 0.5 去跑组合牌，会发生什么
pair_box = np.vstack([OUTER, INNER]); pair_score = np.array([0.90, 0.85])
k05 = nms(pair_box, pair_score, 0.50)
k70 = nms(pair_box, pair_score, 0.70)
print(f'\\n组合牌在 iou_thr=0.50 下保留 {len(k05)} 个框  -> **限速牌被当成重复删掉了**')
print(f'组合牌在 iou_thr=0.70 下保留 {len(k70)} 个框  -> 保住了，但此时主场景的重复框也全留下')
assert len(k05) == 1 and len(k70) == 2"""),
    code("""# 有人会说：用 class-wise NMS（只在同类之间抑制）不就行了？
# —— 它能救「外牌+内牌」（类别不同），但救不了「同类的相邻标志」。
GANTRY = np.array([          # 龙门架上两块**同类**限速牌，检测器把它们框得一大一小
    [700., 300., 820., 380.],       # 检成一个把两块都圈进去的大框
    [700., 300., 790., 380.],       # 只圈住左边那块
])
g_score = np.array([0.88, 0.84])
print(f'同类相邻标志的 IoU = {iou_matrix(GANTRY[:1], GANTRY[1:])[0,0]:.4f}')
print(f'class-wise NMS(0.5) 后保留 {len(nms(GANTRY, g_score, 0.5))} 个 —— 同类之间照样抑制')
assert len(nms(GANTRY, g_score, 0.5)) == 1

print('''
✅ 本节结论（面试高频）：
   NMS 的失败**不是实现问题，是范式问题** —— 它用一个全局标量阈值去回答
   「这两个框是不是同一个目标」，而这个问题的答案**依赖场景**。
   class-wise NMS / soft-NMS / WBF 都只是在缓解，没有改变「用规则代替学习」这一点。
   一对一匹配的做法是：**根本不问这个问题**，直接让模型学会一个目标只输出一个框。''')"""),
    md("""## 5 · 范式 B：一对一集合预测

集合预测器输出**恰好 N 个**槽位（object query），每个槽位一个 (score, box)。
因为训练时用的是一对一匹配，训练收敛后**不会有两个 query 认领同一个目标**。

这里我们不训练模型（那是模块 03–04 的事），直接模拟一个训练好的 DETR 的输出：
N=20 个 query，其中 3 个精准命中 3 块牌，2 个是背景误检，其余 15 个是 no-object。"""),
    code("""N_QUERY = 20
q_box = np.zeros((N_QUERY, 4)); q_score = np.zeros(N_QUERY)

# 3 个 query 各认领一块牌（框有 1-2 px 的正常回归误差）
q_box[3]  = shift(GT[0],  1., -1.); q_score[3]  = 0.93
q_box[11] = shift(GT[1], -2.,  1.); q_score[11] = 0.90
q_box[7]  = shift(GT[2],  1.,  2.); q_score[7]  = 0.96
# 2 个背景误检（任何检测器都会有）
q_box[15] = np.array([ 300., 600.,  340., 640.]); q_score[15] = 0.61
q_box[18] = np.array([1500., 200., 1530., 230.]); q_score[18] = 0.55
# 其余 15 个 query 是 no-object：分数极低，框是「没收敛的乱框」
idle = [i for i in range(N_QUERY) if q_score[i] == 0]
q_score[idle] = rng.uniform(0.01, 0.08, size=len(idle))
q_box[idle]   = np.column_stack([rng.uniform(0, 1700, len(idle)), rng.uniform(0, 900, len(idle)),
                                 np.zeros(len(idle)), np.zeros(len(idle))])
q_box[idle, 2] = q_box[idle, 0] + rng.uniform(20, 200, len(idle))
q_box[idle, 3] = q_box[idle, 1] + rng.uniform(20, 200, len(idle))

# 集合预测的「后处理」：只有一个分数阈值，**没有 NMS**
out = np.where(q_score >= 0.5)[0]
print(f'N = {N_QUERY} 个 query，score>=0.5 的输出 {len(out)} 个：{list(out)}')
dup = duplicates_per_gt_ref(q_box[out], q_score[out], GT)
print(f'每个 GT 被几个输出认领: {dup.tolist()}   (没有做任何抑制)')
assert len(out) == 5 and list(dup) == [1, 1, 1]
print('✅ 重复率天然为 1 —— 因为训练时的一对一匹配已经把重复压制掉了。')

# 同一个组合标志牌场景：集合预测不做抑制，两块牌都留下
pair_q_score = np.array([0.90, 0.85])
pair_out = np.where(pair_q_score >= 0.5)[0]
print(f'\\n组合标志牌：集合预测输出 {len(pair_out)} 个框（外牌+内牌都保住）')
assert len(pair_out) == 2
print('✅ **没有抑制步骤，就不可能误删真目标** —— 这是 TSR 组合牌场景的关键收益。')"""),
    md("""## 6 · 三个机制的最小玩具：query / 二分匹配 / 集合损失

现在把训练那一侧也走一遍。用归一化的 `cxcywh` 坐标（DETR 的约定），
N=6 个 query、M=2 个 GT，走完整条链路：

**代价矩阵 → 一对一最优匹配（暴力枚举，模块 01 会换成 O(n³) 的匈牙利）→ 集合损失**"""),
    code("""def cxcywh_to_xyxy(b):
    cx, cy, w, h = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=-1)

def giou_matrix(a_xyxy, b_xyxy):
    \"\"\"GIoU = IoU - (C - union)/C，C 是最小外接框面积。范围 [-1, 1]。\"\"\"
    a, b = a_xyxy, b_xyxy
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = aa[:, None] + bb[None, :] - inter
    iou = inter / (union + 1e-12)
    ex1 = np.minimum(a[:, None, 0], b[None, :, 0]); ey1 = np.minimum(a[:, None, 1], b[None, :, 1])
    ex2 = np.maximum(a[:, None, 2], b[None, :, 2]); ey2 = np.maximum(a[:, None, 3], b[None, :, 3])
    C = np.clip(ex2 - ex1, 0, None) * np.clip(ey2 - ey1, 0, None)
    return iou - (C - union) / (C + 1e-12)

# 6 个 query 的输出（归一化 cxcywh）+ 每个 query 对目标类的概率
q_boxes = np.array([[0.30, 0.50, 0.05, 0.05],   # q0 几乎压在 GT0 上
                    [0.32, 0.52, 0.06, 0.06],   # q1 也很靠近 GT0 —— **重复框的来源**
                    [0.70, 0.40, 0.09, 0.09],   # q2 靠近 GT1
                    [0.10, 0.20, 0.20, 0.20],   # q3 空
                    [0.85, 0.80, 0.15, 0.15],   # q4 空
                    [0.50, 0.50, 0.40, 0.40]])  # q5 一个大而无当的框
q_prob  = np.array([0.80, 0.65, 0.75, 0.05, 0.04, 0.10])
g_boxes = np.array([[0.30, 0.50, 0.04, 0.04],   # GT0 远处小限速牌
                    [0.70, 0.40, 0.08, 0.08]])  # GT1 中距禁令牌

W_CLS, W_L1, W_GIOU = 1.0, 5.0, 2.0
l1   = np.abs(q_boxes[:, None, :] - g_boxes[None, :, :]).sum(-1)
gi   = giou_matrix(cxcywh_to_xyxy(q_boxes), cxcywh_to_xyxy(g_boxes))
COST = W_CLS * (-q_prob[:, None]) + W_L1 * l1 + W_GIOU * (-gi)

print('代价矩阵 C[query, GT]   (越小越该配对)')
print('        ' + '  '.join(f'GT{j}' + ' ' * 4 for j in range(len(g_boxes))))
for i in range(len(q_boxes)):
    print(f'  q{i}  ' + '  '.join(f'{COST[i, j]:7.3f}' for j in range(len(g_boxes))))
assert COST.shape == (6, 2)"""),
    code("""def brute_force_assignment(cost):
    \"\"\"暴力枚举所有一对一指派，返回 (row_ind, col_ind, 最小总代价)。
       cost:(N,M)。N>=M 时枚举「哪 M 个 query 去认领这 M 个 GT」。\"\"\"
    a = np.asarray(cost, dtype=float); n, m = a.shape
    best, best_pair = np.inf, None
    if n <= m:
        for perm in itertools.permutations(range(m), n):
            t = float(sum(a[i, perm[i]] for i in range(n)))
            if t < best:
                best, best_pair = t, (np.arange(n), np.array(perm))
    else:
        for perm in itertools.permutations(range(n), m):
            t = float(sum(a[perm[j], j] for j in range(m)))
            if t < best:
                r = np.array(perm); c = np.arange(m); o = np.argsort(r)
                best, best_pair = t, (r[o], c[o])
    return best_pair[0], best_pair[1], best

rows, cols, total = brute_force_assignment(COST)
print(f'枚举了 C(6,2)*2! = {6*5} 种指派')
for r, c in zip(rows, cols):
    print(f'  GT{c} 由 q{r} 认领   代价 {COST[r, c]:.3f}')
print(f'总代价 = {total:.3f}')
assert list(rows) == [0, 2] and list(cols) == [0, 1]
print('\\n⚠️  注意 q1 也很靠近 GT0（IoU 不低、分数 0.65），但它**没有**被匹配上。')
print('    下一段就是 DETR 全部魔力的所在：没匹配上的 query 会被判为 no-object。')"""),
    code("""def set_loss(cost_rows, cost_cols, q_prob, q_boxes, g_boxes, w_noobj=0.1):
    \"\"\"集合损失：匹配上的算「分类为前景 + 框」，没匹配上的算「分类为 no-object」。\"\"\"
    matched = set(int(r) for r in cost_rows)
    l_cls_pos = l_box = l_cls_neg = 0.0
    for r, c in zip(cost_rows, cost_cols):
        l_cls_pos += -np.log(q_prob[r] + 1e-12)
        l1_ = np.abs(q_boxes[r] - g_boxes[c]).sum()
        gi_ = giou_matrix(cxcywh_to_xyxy(q_boxes[r:r+1]), cxcywh_to_xyxy(g_boxes[c:c+1]))[0, 0]
        l_box += W_L1 * l1_ + W_GIOU * (1.0 - gi_)
    for i in range(len(q_prob)):
        if i not in matched:
            l_cls_neg += -w_noobj * np.log(1.0 - q_prob[i] + 1e-12)
    return l_cls_pos, l_box, l_cls_neg

lp, lb, ln = set_loss(rows, cols, q_prob, q_boxes, g_boxes)
print(f'匹配上的分类损失 (推向前景)   = {lp:.4f}   作用于 q{list(rows)}')
print(f'匹配上的框损失   (推向 GT)     = {lb:.4f}')
print(f'未匹配的分类损失 (推向 no-obj) = {ln:.4f}   作用于 q{[i for i in range(6) if i not in set(rows)]}')
print(f'总损失 = {lp + lb + ln:.4f}')
assert lp > 0 and lb > 0 and ln > 0

# 关键实验：把 q1（那个「重复框」）的分数调高，看它承受多大的压制力
for p1 in [0.20, 0.65, 0.90]:
    qp = q_prob.copy(); qp[1] = p1
    C2 = W_CLS * (-qp[:, None]) + W_L1 * l1 + W_GIOU * (-gi)
    r2, c2, _ = brute_force_assignment(C2)
    _, _, ln2 = set_loss(r2, c2, qp, q_boxes, g_boxes)
    fired = 1 in set(int(x) for x in r2)
    print(f'  q1 的前景概率 = {p1:.2f} -> 被匹配? {fired} | 未匹配项损失 = {ln2:.4f}')
print('''
✅ **q1 越自信，它作为「未匹配 query」承受的 no-object 损失就越大。**
   这就是「训练期压制重复」的全部机制：一个目标只有一个 query 能被判为前景，
   其余想认领它的 query 都会被 no-object 损失按下去。
   而 NMS 是在推理期把它们**删掉**（模型自己还是学不会）。''')"""),
    md("""## 7 · 后处理代价：NMS 随目标数增长，集合预测不随

这一节量化的是**车端最关心的那件事**：延迟的确定性。

- NMS 是贪心迭代，最坏情况要做 `n(n-1)/2` 次 IoU 比较，**n 是通过分数阈值的候选框数**
- 集合预测的后处理是 `N` 次分数比较，**N 是固定的 query 数**，与场景内容无关"""),
    code("""def nms_comparisons(n):        return n * (n - 1) // 2      # 最坏情况的两两 IoU 比较次数
def set_comparisons(n_query):  return n_query                 # N 次分数阈值比较

print(f'{"候选框数 n":>12s} {"NMS 比较次数":>14s} {"集合预测(N=300)":>16s} {"倍数":>8s}')
for n in [10, 50, 100, 300, 1000, 3000]:
    a, b = nms_comparisons(n), set_comparisons(300)
    print(f'{n:>12d} {a:>14d} {b:>16d} {a / b:>8.1f}x')

assert nms_comparisons(1000) == 499500
assert nms_comparisons(1000) / set_comparisons(1000) > 400

# 场景内容如何影响延迟：市区路口 vs 高速空旷路段
scenes = [('高速空旷（1 块牌）', 12), ('城市普通路段（3 块牌）', 40),
          ('复杂路口（12 块牌 + 广告牌）', 260), ('隧道口逆光（大量低分误检）', 900)]
print(f'\\n{"场景":>28s} {"候选框":>8s} {"NMS 比较":>10s} {"集合预测":>10s}')
costs_nms = []
for name, n in scenes:
    costs_nms.append(nms_comparisons(n))
    print(f'{name:>28s} {n:>8d} {nms_comparisons(n):>10d} {set_comparisons(300):>10d}')
spread = max(costs_nms) / min(costs_nms)
print(f'\\nNMS 后处理开销在不同场景之间相差 {spread:.0f} 倍；集合预测相差 1.0 倍。')
assert spread > 100
print('''
✅ 面试标准答案：**DETR 系的价值不是「平均延迟更低」（通常更高），
   而是「延迟方差更小、p99 更接近 p50」**，因为它没有随目标数变化的后处理。
   车端功能安全关心的是**尾延迟**：一帧超时就丢一帧感知结果。''')"""),
    md("""## ✏️ 练习 1：NMS 阈值的可行窗口

实现 `feasible_nms_window(dup_ious, keep_ious)`：

- `dup_ious`：所有「同一目标的重复框对」的 IoU 列表 → 要删光它们，阈值必须 **严格小于** 其最小值
- `keep_ious`：所有「必须同时保留的真目标对」的 IoU 列表 → 要保住它们，阈值必须 **大于等于** 其最大值

返回 `(lo, hi, ok)`：窗口为 `[lo, hi)`，`ok` 表示窗口是否非空（`lo < hi`）。
两个列表可能为空：`keep_ious` 为空时 `lo = 0.0`；`dup_ious` 为空时 `hi = 1.0`。"""),
    code("""def feasible_nms_window(dup_ious, keep_ious):
    # TODO: 返回 (lo, hi, ok)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
lo, hi, ok = feasible_nms_window([0.78, 0.67, 0.59], [0.27, 0.31])
assert abs(lo - 0.31) < 1e-9 and abs(hi - 0.59) < 1e-9 and ok, (lo, hi, ok)
lo2, hi2, ok2 = feasible_nms_window([0.78, 0.67, 0.59], [0.27, 0.69])
assert not ok2, '0.69 > 0.59，窗口应为空'
lo3, hi3, ok3 = feasible_nms_window([0.9], [])
assert ok3 and abs(lo3 - 0.0) < 1e-12 and abs(hi3 - 0.9) < 1e-12
lo4, hi4, ok4 = feasible_nms_window([], [0.4])
assert ok4 and abs(hi4 - 1.0) < 1e-12
# 用本 notebook 真实场景的数据再验一次
lo5, hi5, ok5 = feasible_nms_window(list(dup_ious), [iou_pair])
assert not ok5, '组合标志牌场景下窗口必须是空的'
print(f'真实 TSR 场景窗口 = [{lo5:.4f}, {hi5:.4f})  非空? {ok5}')
print('✅ 练习 1 通过：**这个窗口是否非空，是判断「该不该上一对一匹配」的最直接依据**')"""),
    md("""## ✏️ 练习 2：重复率统计

实现 `duplicates_per_gt(pred_boxes, pred_scores, gt_boxes, score_thr=0.5, iou_thr=0.5)`：
返回长度为 M 的整数数组，第 j 个元素是「分数 ≥ `score_thr` **且** 与 GT j 的 IoU ≥ `iou_thr`」的预测个数。

理想值全是 1：等于 0 是漏检，大于 1 是重复。**这个指标是诊断 DETR 训练是否收敛的第一个信号**
（模块 05 会把它做成训练监控项）。"""),
    code("""def duplicates_per_gt(pred_boxes, pred_scores, gt_boxes, score_thr=0.5, iou_thr=0.5):
    # TODO: 用 iou_matrix，返回 shape=(M,) 的整数数组
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
d0 = duplicates_per_gt(P_BOX, P_SCORE, GT)
assert list(d0) == [4, 4, 3], d0
d1 = duplicates_per_gt(P_BOX[keep], P_SCORE[keep], GT)
assert list(d1) == [1, 1, 1], d1
d2 = duplicates_per_gt(q_box[out], q_score[out], GT)
assert list(d2) == [1, 1, 1], d2
# 阈值收紧后，边缘重复框应当被排除
d3 = duplicates_per_gt(P_BOX, P_SCORE, GT, score_thr=0.5, iou_thr=0.75)
assert list(d3) == [2, 2, 2], d3
d4 = duplicates_per_gt(P_BOX, P_SCORE, GT, score_thr=0.9)
assert list(d4) == [1, 0, 1], d4      # 只有 GT0(0.92) 和 GT2(0.95) 有 >=0.9 的框
print(f'密集预测 NMS 前 {d0.tolist()} -> NMS 后 {d1.tolist()} | 集合预测 {d2.tolist()}（未做抑制）')
print('✅ 练习 2 通过：**「重复率」比 mAP 更早暴露训练问题** —— 它在第几个 epoch 降到 1，')
print('   直接反映一对一监督有没有生效。')"""),
    md("""## ✏️ 练习 3：贪心匹配为什么不够

实现 `greedy_one_to_one(cost)`：反复取全局最小的未占用格子作为一组配对，
直到行或列用完。返回 `(rows, cols, total)`，`rows` 按升序排列。

然后对照 `brute_force_assignment` 的最优解——**贪心不是最优**，
这正是我们下一模块必须学匈牙利算法的原因。"""),
    code("""def greedy_one_to_one(cost):
    # TODO: 每次取剩余矩阵的全局最小，配对后划掉该行该列
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
TRAP = np.array([[1.0,   2.0],
                 [2.0, 100.0]])
gr, gc, gtot = greedy_one_to_one(TRAP)
_, _, otot = brute_force_assignment(TRAP)
assert abs(gtot - 101.0) < 1e-9, f'贪心先拿走 C[0,0]=1，剩下只能吃 100，总代价 101，得到 {gtot}'
assert abs(otot -   4.0) < 1e-9, '最优是 (0->1)+(1->0) = 2+2 = 4'
assert gtot > otot
print(f'贪心总代价 {gtot:.1f}  vs  最优总代价 {otot:.1f}   ->  贪心差了 {gtot/otot:.1f} 倍')

# 在本 notebook 的真实代价矩阵上贪心恰好等于最优（小矩阵常常如此，别被骗了）
gr2, gc2, gt2 = greedy_one_to_one(COST)
_, _, ot2 = brute_force_assignment(COST)
print(f'本节 6x2 代价矩阵：贪心 {gt2:.4f} / 最优 {ot2:.4f}  -> {"相同" if abs(gt2-ot2)<1e-9 else "不同"}')
# 随机大量抽样，统计贪心的次优比例
rng2 = np.random.default_rng(7); bad = 0; TRIALS = 300
for _ in range(TRIALS):
    A = np.round(rng2.normal(size=(5, 4)) * 3, 2)
    if greedy_one_to_one(A)[2] > brute_force_assignment(A)[2] + 1e-9:
        bad += 1
print(f'随机 5x4 代价矩阵 {TRIALS} 次：贪心给出次优解的比例 = {bad/TRIALS:.1%}')
assert bad / TRIALS > 0.05, '贪心应当在相当比例的随机矩阵上次优'
print('✅ 练习 3 通过：**贪心「局部最便宜」会锁死后面的选择** —— 必须用全局最优的匈牙利算法。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def feasible_nms_window(dup_ious, keep_ious):
    lo = float(max(keep_ious)) if len(keep_ious) else 0.0   # 保住真目标：thr >= max(keep)
    hi = float(min(dup_ious))  if len(dup_ious)  else 1.0   # 删光重复框：thr <  min(dup)
    return lo, hi, lo < hi"""),
    code("""# 练习 2 参考答案
def duplicates_per_gt(pred_boxes, pred_scores, gt_boxes, score_thr=0.5, iou_thr=0.5):
    if len(pred_boxes) == 0:
        return np.zeros(len(gt_boxes), dtype=int)
    M = iou_matrix(np.asarray(pred_boxes, float), np.asarray(gt_boxes, float))
    hit = (np.asarray(pred_scores, float)[:, None] >= score_thr) & (M >= iou_thr)
    return hit.sum(axis=0).astype(int)"""),
    code("""# 练习 3 参考答案
def greedy_one_to_one(cost):
    a = np.array(cost, dtype=float)
    n, m = a.shape
    rows, cols = [], []
    for _ in range(min(n, m)):
        i, j = np.unravel_index(int(np.argmin(a)), a.shape)
        rows.append(int(i)); cols.append(int(j))
        a[i, :] = np.inf; a[:, j] = np.inf          # 划掉该行该列
    order = np.argsort(rows)
    rows = np.array(rows)[order]; cols = np.array(cols)[order]
    total = float(np.asarray(cost, dtype=float)[rows, cols].sum())
    return rows, cols, total"""),
    md("""---
## 🧪 真实工程胶囊：把「两种范式」写进配置与验收标准"""),
    code("""RECIPE = r'''
# ============================================================
# A. 密集检测器（YOLO / RTMDet）的后处理配置 —— 注意每一项都是**手工先验**
# ============================================================
model.test_cfg = dict(
    score_thr=0.05,          # 太低 -> NMS 输入框数暴涨 -> 延迟 p99 失控
    nms=dict(type='nms', iou_threshold=0.65),   # <-- 全局标量阈值，本课的靶心
    max_per_img=300,         # 截断保护：没有它，逆光/隧道口会把延迟拖爆
    nms_pre=1000,            # NMS 前先按分数取 top-k
)
# 车端验收必须额外测：**不同目标数下的后处理耗时分布**，而不只是平均 FPS
#   for n_obj in [1, 5, 20, 100, 500]: measure_p50_p99(nms_latency)

# ============================================================
# B. DETR 系的对应配置 —— 后处理只剩 top-k
# ============================================================
model.test_cfg = dict(max_per_img=100)      # 就这一项；**没有 nms 字段**
# 训练侧多出来的是 matcher：
train_cfg = dict(assigner=dict(
    type='HungarianAssigner',
    match_costs=[dict(type='ClassificationCost',  weight=1.0),   # 用**概率**不是 log
                 dict(type='BBoxL1Cost',          weight=5.0, box_format='xywh'),
                 dict(type='IoUCost', iou_mode='giou', weight=2.0)]))

# ============================================================
# C. 选型自检清单（把本 notebook 的量化结论变成可执行的检查）
# ============================================================
CHECKLIST = [
  ("统计数据集里「必须同时保留的重叠真目标对」的 IoU 分布",
   "取 95 分位数 -> 这是 NMS 阈值的下界 lo"),
  ("统计当前检测器输出的「同目标重复框对」IoU 分布",
   "取 5 分位数 -> 这是 NMS 阈值的上界 hi"),
  ("若 lo >= hi -> 单一 NMS 阈值不存在，**这是选 DETR 系的硬理由**", ""),
  ("实测后处理耗时随目标数的曲线，报告 p99/p50 比值", "> 2.0 说明延迟方差不可接受"),
  ("DETR 系上线仍建议挂一个 iou_thr=0.9 的兜底 NMS", "训练不充分时重复率不为零"),
]
for i, (k, v) in enumerate(CHECKLIST, 1):
    print(f"{i}. {k}")
    if v:
        print(f"     -> {v}")
'''
print(RECIPE)
for token in ['HungarianAssigner', 'iou_threshold', 'max_per_img',
              'ClassificationCost', 'giou', 'p99/p50', 'lo >= hi']:
    assert token in RECIPE, token
print('✅ 胶囊覆盖：密集检测器后处理配置 / DETR matcher 配置 / 选型量化自检清单')"""),
    md("""### 小结

- **核心命题**：NMS 是在**推理期删掉**重复，一对一匹配是在**训练期不让**重复长出来。
  前者是打补丁（不可微、阈值全局、延迟数据依赖），后者是改目标函数。
- **NMS 的失败是范式问题而非实现问题**：它用一个全局标量阈值回答「这两个框是不是同一个目标」，
  而这个问题的答案依赖场景。本 notebook 在真实 TSR 组合标志牌场景上算出
  **可行阈值窗口 = [0.694, 0.592) = 空集** —— 没有任何阈值能同时删光重复且不误删真目标。
- **三个机制缺一不可**：① 二分图最优匹配建立对应关系；② 集合损失里的 no-object
  提供压制重复的力；③ object query 的 self-attention 提供去重的**能力**。
  匹配给动机，attention 给能力。
- **贪心匹配不够**：随机代价矩阵上有相当比例会给出次优解，锁死后面的选择。
  下一模块要手写 O(n³) 的匈牙利算法。
- **对 TSR 的真实价值**是「延迟确定性」与「密集重叠不误删」，**不是**纸面 AP。
  面试里说「DETR 没有 NMS 所以更快」是错的；正确说法是「延迟方差更小、p99 更接近 p50」。
- 原版 DETR 直接用在 TSR 上会很难看（单尺度 stride-32 特征 + 100 query）。
  **多尺度 + 可变形注意力是 TSR 落地 DETR 系的前提条件**，不是可选项。

下一站：**模块 01 · 二分图匹配与匈牙利算法** —— 本课最重要的一章，从零手写 O(n³) 匹配。"""),
]
