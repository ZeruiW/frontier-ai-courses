# -*- coding: utf-8 -*-
"""C55 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "目标检测基础（C18）；C53/C54 的检测器架构有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy + 真实相机参数与安全需求推演"),
    ("预计时长", "总览 30 分钟 + 跑 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么：TSR 不是「检测 + 分类」的简单组合", "".join([
        P("<span class=\"term\">TSR</span>（Traffic Sign Recognition，交通标志识别）在教科书里通常只占半页纸：「用检测器找出标志框，再用一个分类器判断是哪一类」。这个描述<strong>没有错，但它省略了这门课全部的内容</strong>——因为它没有回答任何一个真正决定成败的问题。"),
        P("先看一组把问题说清楚的数字。一块中国城区常见的圆形禁令标志直径 60 cm；一台 1920×1080、水平视场角 60° 的前视相机，等效焦距约 <strong>1663 像素</strong>。那么这块标志在图像里有多大？"),
        TABLE(["距离", "标志边长（像素）", "标志面积（像素²）", "占全图面积", "在 COCO 定义下"], [
            ["20 m", "50 px", "2488", "0.12%", "small 的上界附近"],
            ["30 m", "33 px", "1106", "0.053%", "刚好越过 32² 门槛"],
            ["<strong>60 m</strong>", "<strong>17 px</strong>", "<strong>276</strong>", "<strong>0.013%</strong>", "<strong>典型 small</strong>"],
            ["100 m", "10 px", "100", "0.005%", "接近可检测下界"],
            ["146 m", "6.8 px", "47", "0.002%", "物理上无法可靠分类"],
        ]),
        P("再看一组安全侧的数字。车速 100 km/h，要把速度降到 60 km/h，取舒适减速度 2 m/s²、感知确认+决策+执行的总反应时间 0.8 s，需要的距离是 <strong>146 米</strong>。"),
        DUAL(
            "把这两组数字放在一起，这门课的全部张力就出来了：<strong>安全需求要求你在 146 米外就认出限速牌，而物理光学告诉你那时它只有 6.8 个像素</strong>。6.8 个像素里塞不下「60」和「80」的区别——这不是模型不够强，是<em>信息不存在</em>。所以量产 TSR 系统必然不是「一个更好的检测器」，而是<strong>多相机 + 时序累积 + 地图先验</strong>的组合。",
            "严谨地说，这是一个<span class=\"term\">信息可用性</span>（information availability）约束而非<span class=\"term\">模型容量</span>约束。给定针孔相机模型 <code>px = f·S/Z</code>，在焦距 f、物理尺寸 S 固定时，可用像素数随距离平方衰减（面积意义上）。任何单帧算法的性能上界都被这个物理量锁死。<em>识别出「这是信息问题不是模型问题」，并据此把工程投入从「换更大 backbone」转向「换相机配置 / 加时序 / 用地图」，是 TSR 工程师与通用检测工程师最显著的能力差别</em>。",
        ),
        CALLOUT("intuition", "学完这门课你应当能当场回答：<strong>TSR 与通用目标检测有哪五个本质不同？两级方案（类别无关检测 + crop 分类）与端到端多类检测各自的动机与代价是什么？级联召回为什么是乘法？为什么 mAP 不足以衡量 TSR，该换成什么？多帧融合的响应延迟与稳定性怎么量化权衡？对向车道的标志为什么必须在感知之外被丢掉？</strong> 这些问题在 XPENG「TSR 2D Detection」这类岗位的面试里几乎必然出现。"),
    ])),
    ("stack", "TSR 在自动驾驶软件栈里的位置", "".join([
        P("面试里一个高频的开放题是「讲讲 TSR 系统怎么设计」。<strong>面试官想听的第一件事不是模型，而是你知不知道 TSR 的输入从哪来、输出到哪去</strong>——因为这决定了你会不会把「检测框」当成终点。下面这张图是本课的坐标系，后面每个模块都会回到它。"),
        ASCII("""传感器层   前视长焦 30° │ 前视主摄 60° │ 前视广角 120° │ 侧视/环视 │ 毫米波 │ 激光雷达
             │
             │  ISP：去马赛克 / 白平衡 / 自动曝光 / 降噪 / 色调映射
             │        ↑ 训练数据（JPEG 解码图）与车端数据（ISP 输出）的第一个域差
             ▼
感知层     ┌────────────────────────────────────────────────────────┐
           │  2D 检测：车辆 / 行人 / 锥桶 / 红绿灯 / **交通标志** ← 本课  │
           │  车道线 · 可行驶区域 · BEV 编码 · 深度                    │
           └────────────────────────────────────────────────────────┘
             │  TSR 单帧输出：框 + 粗类 + 细类 + 属性(限速值/时段/车型) + 置信度
             ▼
融合 / 跟踪层   多相机融合（同一标志同时被长焦与主摄看到，谁说了算？）
               时序关联（IoU / 匈牙利匹配 + **自车运动补偿**）
               多帧投票 · 贝叶斯置信度累积 · 迟滞状态机
             │  输出：稳定的「标志实例」（有 ID、有生命周期、有累积置信度）
             ▼
地图 / 定位层   与高精地图标志图层匹配（地图有 → 先验提升；地图无 → 新增线索）
               **关联到车道 / 关联到自车路径**
               ↑ 对向车道、辅路、匝道的标志必须在这一层被丢掉，而不是在感知层
             │
             ▼
规控 / VLA     限速牌 → 速度上限约束        禁止左转 → 轨迹候选屏蔽
               停车让行 → 时空停止约束      解除牌 → 撤销既有约束
               冲突消解：临时施工牌 > 可变电子牌 > 固定牌 > 地图限速
             │
             ▼
执行 / HMI     纵向控制（减速）· 横向控制（不换道）· 仪表显示当前限速"""),
        DUAL(
            "这张图里有两条经常被忽略的边。<strong>第一条是「感知层 → 融合层」：TSR 的单帧输出不是产品，稳定的标志实例才是</strong>。单帧检测抖一下没关系，但仪表上的限速数字闪一下用户立刻能看见。<em>所以 TSR 的最终指标必须定义在时序输出上，而不是逐帧 mAP 上</em>——这是模块 04 与 05 的主题。",
            "<strong>第二条是「融合层 → 地图/定位层」：一个标志「在图像里存在」与「对自车生效」是两件完全不同的事</strong>。对向车道的限速牌、辅路的禁令牌、匝道的指示牌都会合法地出现在前视图像里，而它们全都不应该改变自车的行为。<em>把这个判断放在感知层做（比如训练模型只检测「属于自车车道的标志」）是错误的设计</em>——因为它需要车道拓扑与路径规划信息，那些信息在感知层根本不存在。<strong>正确做法是感知层如实输出所有标志 + 几何属性，由下游做关联</strong>。面试里主动讲出这一点，会立刻区分你和「只跑过检测器」的候选人。",
        ),
        CALLOUT("warn", "另一个常见误解：<strong>把红绿灯识别（TLR）和交通标志识别（TSR）当成同一个任务</strong>。它们的相似之处只有「都是小目标、都在路边」；本质差别很大：<em>红绿灯是<strong>动态状态</strong>（颜色随时间变化，时序上不能做「多帧投票取众数」，必须做状态跳变检测），交通标志是<strong>静态语义</strong>（除可变电子牌外，多帧信息可以放心累积）</em>。这直接导致两者的时序融合策略完全不同。<strong>把两者混为一谈会在面试里立刻暴露</strong>。"),
    ])),
    ("five", "TSR 与通用目标检测的五个本质不同", "".join([
        P("这是本课最需要背下来的一个框架，也是面试开场最常被问到的题。<strong>用五个字记：小 · 偏 · 硬 · 连 · 歪</strong>——目标<em>小</em>、分布<em>偏</em>、语义<em>硬</em>、时序<em>连</em>、代价<em>歪</em>。"),
        TABLE(["#", "维度", "通用检测（COCO/BDD）", "TSR", "由此导出的工程后果"],
              [
            ["①", "<strong>小：目标尺度</strong>",
             "目标中位边长 50–100 px，small 只占一部分",
             "<strong>16–30 px 是常态而非极端</strong>；60 m 外仅 17 px",
             "必须动 stride/P2 层/输入分辨率/切片；IoU 阈值对小框极不公平；标注误差相对量级大"],
            ["②", "<strong>偏：类别分布</strong>",
             "80 类，最长尾/最短头相差 100× 量级",
             "<strong>200+ 细类，头尾相差 10³–10⁴ 倍，且尾巴随地域改变</strong>",
             "长尾方法是必需品不是加分项；<strong>类别体系必须分层</strong>；跨区域部署要换尾巴"],
            ["③", "<strong>硬：语义→动作</strong>",
             "输出是「有一只猫」，下游是统计消费",
             "<strong>输出直接变成控制约束</strong>：限速 60 → 速度上限 60",
             "错分「60/80」不是掉 1 点 AP，是让车开错速度；<strong>细类错分的代价 ≫ 定位不准</strong>"],
            ["④", "<strong>连：时序可用性</strong>",
             "目标自身在动，未来位置不可预测",
             "<strong>标志是静止刚体 + 自车运动已知 → 位置可精确预测</strong>",
             "时序是最便宜的精度来源；不用时序等于白扔一半信息；<strong>跟踪难度远低于行人跟踪</strong>"],
            ["⑤", "<strong>歪：代价不对称</strong>",
             "FP 与 FN 大致对称，用 mAP 平均即可",
             "<strong>双重不对称</strong>：FN vs FP 不对称，且按类别再次不对称",
             "指标要代价加权；工作点按 FP/km 定；<strong>mAP 会掩盖关键类的失效</strong>"],
        ]),
        H3("① 小：为什么「16 px 是常态」这句话很重"),
        P("模块 05 会给完整推导，这里先给结论的量纲。8×8 的框在 x、y 各偏移 2 px，IoU 从 1.0 掉到 <strong>36/92 ≈ 0.391</strong>；同样偏移 2 px，64×64 的框 IoU 还有 <strong>0.884</strong>。"),
        MATH("\\mathrm{IoU}(s,\\delta)=\\frac{(s-\\delta)^2}{2s^2-(s-\\delta)^2}\\quad\\Longrightarrow\\quad \\mathrm{IoU}(8,2)=0.391,\\ \\ \\mathrm{IoU}(64,2)=0.884"),
        P("这意味着 <strong>IoU=0.5 这个阈值对 8 px 的目标要求「亚 2 像素」的定位精度，而对 64 px 的目标只要求「10 像素以内」</strong>。同一个阈值，两个数量级的严苛度差异。<em>所以小目标的正样本稀缺不是「模型学不好」，是「分配规则本身把它们判死了」</em>——这条线索会一直贯穿到模块 03 与 C57。"),
        H3("② 偏：长尾还是「会搬家」的长尾"),
        P("通用检测的长尾是固定的：COCO 里 person 永远比 toaster 多。<strong>TSR 的长尾是区域相关的</strong>——「注意牲畜」在西部国道是常见类，在上海内环一年遇不到一次；「潮汐车道」在部分城市是高频类，在别处根本不存在。<em>这意味着「在采集数据上是尾部类」不等于「在部署区域是尾部类」，而按训练集频率做的重加权在新区域会系统性偏错</em>。"),
        H3("③ 硬：语义直接变成安全动作"),
        CALLOUT("danger", "<p>把「限速 80」错分成「限速 60」在 mAP 上是一个类别的一次错误，在车上是<strong>无缘无故的减速</strong>；反过来把「限速 60」错分成「限速 80」是<strong>超速</strong>。而在通用检测里，把 cat 分成 dog 只是掉分。<em>这条差异导出了一个直接的工程要求：<strong>混淆矩阵比 mAP 重要</strong></em>——你必须知道哪几对类别互相错分、每一对的下游后果是什么，然后针对性地加数据或加代价权重。<strong>面试里被问「你怎么衡量 TSR 效果」，只答 mAP 基本等于放弃这一轮</strong>。</p>", "错分不是掉分，是错误的控制动作"),
        H3("④ 连：这是 TSR 相对于行人检测的巨大优势"),
        P("车速 100 km/h、相机 30 FPS，一块标志从 100 m 接近到 30 m 的过程中，你有 <strong>75 帧</strong>观测它。而且因为标志静止、自车运动已知（轮速+IMU+定位），<strong>下一帧它会出现在哪里是可以解析预测的</strong>——不需要卡尔曼滤波去猜运动模型。<em>「TSR 的跟踪本质上是自车运动补偿而非目标运动建模」，这句话在面试里很有杀伤力</em>。模块 04 会把它做成代码。"),
        H3("⑤ 歪：双重不对称"),
        P("漏检一块「停车让行」可能导致路口冲突；漏检一块「景点指示」用户根本不会察觉。而误检的代价同样不对称：<strong>把广告牌误检成限速 30 会触发幽灵刹车（phantom braking），这是用户投诉的头号来源</strong>，而漏掉一块限速解除牌只是让车多开慢一会儿。<em>因此 TSR 的评测必须是代价敏感的，工作点必须按「每公里误报次数」（FP/km）而不是 precision 来定</em>——这是模块 05 的核心。"),
        DUAL(
            "把五点浓缩成一句可迁移的判断：<strong>TSR 是一个「信息严重不足、分布严重偏斜、错误代价严重不对称」的检测任务，而它同时享有「目标静止、自车运动已知」这个通用检测拿不到的红利</strong>。<em>好的 TSR 方案就是用第四点去补前三点</em>——用时序累积换单帧信息不足，用时序一致性挖掘长尾，用时序稳定性压住误报。",
            "更严谨地说，前三点是<span class=\"term\">问题难度</span>（irreducible difficulty），第五点是<span class=\"term\">损失函数的形状</span>（asymmetric loss），第四点是<span class=\"term\">额外的结构先验</span>（structural prior）。<em>三者是不同类型的东西，混在一起谈会导致「用错工具解错问题」</em>：比如用更强的 backbone 去解第①点（信息不足）收益很小，用代价加权去解第②点（长尾）会牺牲整体精度，而用时序去解第①③⑤点则同时有效。<strong>能把「这个问题属于哪一类」说清楚，就是系统设计能力</strong>。",
        ),
    ])),
    ("task", "TSR 的完整任务定义：四层输出", "".join([
        P("「TSR 的输出是什么」这个问题，一半的候选人会答「框 + 类别」。<strong>正确答案是四层，而且缺任何一层下游都没法用</strong>。"),
        TABLE(["层", "输出内容", "为什么必须有", "缺了会怎样"], [
            ["<strong>L0 定位</strong>",
             "2D 框（xyxy）+ 检测置信度 + 所属相机 + 时间戳",
             "下游要做多相机融合与时序关联，必须知道「哪台相机的哪一帧」",
             "跨相机重复上报同一块标志；时序关联无法对齐"],
            ["<strong>L1 粗类</strong>",
             "禁令 / 警告 / 指示 / 指路 / 辅助 / 施工 / 可变电子牌",
             "粗类由形状+颜色决定，样本充足、准确率高，<strong>可作为降级输出</strong>",
             "细类不确定时只能输出「无」，白白丢掉「这里有个禁令牌」这条强信息"],
            ["<strong>L2 细类</strong>",
             "限速 / 禁止驶入 / 禁止左转 / 注意行人 / …",
             "决定下游施加哪一类约束",
             "无法翻译成控制约束"],
            ["<strong>L3 属性</strong>",
             "限速值、生效时段、限定车型、箭头方向、距离数字、褪色/遮挡状态、<strong>是否面向自车</strong>、关联车道",
             "同一细类下的参数决定具体约束值；几何属性决定这块牌是否对自车生效",
             "「限速」但不知道限多少；对向车道的牌被错误施加到自车"],
        ]),
        DUAL(
            "<strong>L1 存在的唯一理由是「可降级」</strong>。远处一块牌只有 12 px，你能看出它是「白底红圈的圆形」（禁令）但看不出是禁止什么。此时输出 <code>{L1: prohibitory, L2: unknown, conf: 0.7}</code> 对下游<em>非常有用</em>——规控可以先保守一点、跟踪器可以先建实例、下一帧近了再补上 L2。<em>而如果你的输出 schema 只有「类别」这一个字段，这条信息就只能被丢掉。</em>",
            "<strong>L3 里的「是否面向自车」与「关联车道」是最容易被漏掉、也最容易在面试里加分的两项</strong>。感知层能提供的是几何证据：标志平面法向与自车朝向的夹角（背面/侧面会显著不同）、标志在图像中的横向位置与消失点的关系、以及（若有）标志的 3D 位置。<em>感知层不做「这块牌是否对我生效」的最终判断，但必须把做这个判断所需的证据全部输出</em>——这就是模块 02 讲的「接口设计原则：把判断留给有上下文的那一层，把证据留在产生它的那一层」。",
        ),
        CALLOUT("warn", "<strong>置信度必须逐层输出，而不是只给一个总分</strong>。两级方案里最终置信度是「检测置信度 × 分类置信度」，但下游需要区分这两种情况：<em>「我很确定这里有个牌，但不确定是什么」（det 0.95 × cls 0.4）</em> 与 <em>「我不太确定这里有牌，但如果有的话肯定是限速 60」（det 0.4 × cls 0.95）</em>。两者乘积都是 0.38，但下游的正确反应完全不同（前者应该继续观察，后者应该等更多证据）。<strong>把两个置信度乘起来再输出，就把这个区别永久抹掉了</strong>。这是感知-决策接口最常见的设计错误之一。"),
    ])),
    ("physics", "像素预算：用一个公式推出这门课的所有难点", "".join([
        P("本课所有的定量推理都从针孔相机模型出发。给定图像宽 W（像素）与水平视场角 HFOV，等效焦距（像素单位）是："),
        MATH("f_{px}=\\frac{W/2}{\\tan(\\mathrm{HFOV}/2)},\\qquad \\text{标志成像边长}\\ \\ p=\\frac{f_{px}\\cdot S}{Z}"),
        P("其中 S 是标志的物理尺寸（米），Z 是距离（米）。把真实参数代进去："),
        TABLE(["相机配置", "f<sub>px</sub>", "60 cm 标志 @50 m", "@100 m", "@146 m", "评价"], [
            ["广角 120° · 1920×1080", "554", "6.7 px", "3.3 px", "2.3 px", "<strong>完全不可用</strong>（它的任务是近场与路口）"],
            ["主摄 60° · 1920×1080", "1663", "20 px", "10 px", "6.8 px", "50 m 内可靠，100 m 勉强，146 m 无望"],
            ["主摄 60° · 3840×2160", "3326", "40 px", "20 px", "13.7 px", "分辨率翻倍 = 有效距离翻倍，代价是算力 4×"],
            ["<strong>长焦 30° · 1920×1080</strong>", "3582", "43 px", "21 px", "<strong>14.7 px</strong>", "<strong>远距离 TSR 的现实解</strong>，代价是视场窄"],
        ]),
        DUAL(
            "这张表回答了一个高频面试题：「<strong>要在 100 米外检出限速牌，你会怎么做？</strong>」。差的答案是「用更大的模型 / 加 FPN 的 P2 层」——那些都对，但都改变不了「10 个像素里没有 60 与 80 的区别」这个事实。<em>好的答案是先算像素预算，再说「所以我需要一路长焦相机，或者 4K 主摄，或者接受在 100 m 只输出 L1 粗类、靠时序累积到 60 m 再确认 L2」</em>。",
            "从公式还能反推一个非常实用的量：<strong>给定「必须在 Z 米外达到 p 像素」的需求，所需焦距是 f = pZ/S，对应的 HFOV = 2·arctan((W/2)/f)</strong>。代入 S=0.6 m、Z=100 m、p=20 px，得 f=3333 px、HFOV≈32°——<em>这恰好就是量产车上「长焦相机 30° 左右」这个配置的来历</em>。反过来，一台 60° 的主摄能在 50 m 处刚好达到 20 px（HFOV≈59.9°）。<strong>能把「相机选型」和「感知需求」用一个公式连起来，是这门课最值钱的一页</strong>。notebook 里你会把这个求解器写出来。",
        ),
        P("再叠加安全侧的约束。从 v₀ 减速到 v₁ 所需的距离（含反应时间 t_r、减速度 a）是："),
        MATH("D = v_0 t_r + \\frac{v_0^2-v_1^2}{2a}\\quad\\xrightarrow{\\ 100\\to 60\\,\\mathrm{km/h},\\ a=2,\\ t_r=0.8\\ }\\quad D=22.2+123.5=145.7\\ \\mathrm{m}"),
        CALLOUT("intuition", "把两个公式连起来就得到本课的<strong>中心矛盾</strong>：<em>安全需要 146 m 的检出距离，而 146 m 处标志只有 7–15 px</em>。<strong>这个矛盾无法在单帧、单相机内解决，所以量产 TSR 必然是一个「多相机 + 时序 + 地图」的系统工程问题，而不是一个模型问题。</strong> 记住这句话——它是本课后面五个模块存在的全部理由，也是面试里你应该主动抛出的第一个判断。"),
    ])),
    ("map", "课程地图、方法论与运行环境", "".join([
        ASCII("""起点：你会训一个检测器，但没做过「要上车」的检测。

  模块 00  课程总览与环境                      ← 你在这里
     │      TSR 在软件栈里的位置 / **五个本质不同（小·偏·硬·连·歪）** /
     │      四层输出定义 / 针孔模型与像素预算
     ▼      「先算清楚物理上什么可能、什么不可能」
  模块 01  数据集与标志分类体系
     │      GTSRB/GTSDB/**TT100K**/MTSD/BDD100K 的规模与局限 /
     │      GB 5768 vs Vienna vs MUTCD 的形状-颜色-语义映射 /
     │      类别爆炸与**层次标签设计** / 标注规范的坑 / 跨域偏差
     ▼      「你的类别体系决定了你的天花板」
  模块 02  TSR 系统设计：两级 vs 端到端
     │      两级方案的四个动机与代价 / **级联召回 = 检测召回 × 分类准确率** /
     │      crop 策略 / 置信度合成与标定 / 拒识与未知类
     ▼      「先定架构，再谈模型」
  模块 03  失效模式全景
     │      **四象限框架**（漏检/误检/错分/定位不准）/ 远距离·遮挡·逆光·夜间·
     │      雨雾·运动模糊·褪色·广告牌误检·电子牌·对向车道·区域性标志 /
     │      成因归因矩阵 / **优先级 = 频率 × 安全后果 × 修复成本**
     ▼      「知道会在哪里坏，才知道该修哪里」
  模块 04  时序与多帧融合
     │      IoU/匈牙利关联 + **自车运动补偿** / 贝叶斯累积 vs 滑窗投票 /
     │      **迟滞（hysteresis）与生命周期状态机** / 地图先验融合 /
     │      延迟与稳定性的根本矛盾
     ▼      「把 75 帧观测变成一个稳定的结论」
  模块 05  安全导向的评测体系
            为什么 mAP 不足 / 按距离·尺寸·光照·天气**分桶评测** /
            代价敏感指标 / **FP per km** / 首检距离与闪烁率 /
            场景化回归集与门禁 / 评测-部署一致性

终点：你能独立设计一套 TSR 方案，并说清它在每种失效模式下的行为与代价。"""),
        TABLE(["模块", "核心机制", "notebook 里从零做什么"], [
            ["00 总览", "针孔模型、像素预算、五个本质不同", "<strong>像素-距离换算器</strong> + 相机选型反解 + 代价不对称风险打分"],
            ["01 数据与体系", "长尾、层次标签、标注规范", "<strong>Zipf 拟合与 head/tail 划分</strong> + 层次编码与层次感知评测 + 标注一致性 agreement"],
            ["02 系统设计", "级联误差传播、置信度标定", "<strong>级联召回计算器</strong> + 两级 vs 端到端模拟 + 可靠性图与 ECE"],
            ["03 失效模式", "四象限、优先级排序", "<strong>失效模式打分器</strong> + 混淆矩阵分析 + 退化因子对分数的影响曲线"],
            ["04 时序融合", "关联、累积、迟滞", "<strong>IoU 跟踪器 + 匈牙利关联</strong> + 贝叶斯累积 vs 投票 + 闪烁率测量"],
            ["05 安全评测", "分桶、代价敏感、FP/km", "<strong>分桶 mAP</strong> + 风险评分 + 首检距离与闪烁率 + 回归门禁判定器"],
        ]),
        DUAL(
            "本课有一个必须坦白的约束：<strong>它讲的东西本质上需要真实车队数据与真实标志图像</strong>，而这些既不能下载也不能开源。所以 notebook 全部走「<em>物理建模 + 合成数据</em>」的路线：用真实的相机参数、真实的标志尺寸标准（GB 5768）、真实的车速与减速度、真实的长尾指数，去合成可计算的场景。<em>合成的是像素，不是规律。</em>",
            "这个约束其实指向了更好的学法。<strong>TSR 的困难几乎都不在「怎么写模型代码」，而在「怎么把物理约束、安全需求、数据分布、代价结构翻译成工程决策」</strong>——而这些全都是可以用几十行 numpy 精确复现的。<em>你在 notebook 里算出的「146 m 处只有 6.8 px」，与在真车上量出来的是同一个数</em>。讲解里则紧跟真实的数据集数字、真实的标注规范条款、可原样复制的配置——这些放在每个模块末尾的 🧪 胶囊里。",
        ),
        CODE("""pip install -r requirements.txt      # numpy / matplotlib / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        CALLOUT("warn", "与相邻课程的分界要说清楚，避免重复投入：<strong>C53 讲实时检测器架构（RTMDet/RT-DETR），C54 讲集合预测与匈牙利匹配，C56 讲检测数据增强，C57 讲小目标的通用方法，C58 讲难例挖掘与长尾闭环，C59 讲 VLA 接口，C60 讲车端部署一致性，C61 讲面试实务</strong>。<em>本课只讲「TSR 这个具体任务」的领域知识</em>——它会频繁引用那些课的方法，但不重复讲方法本身。建议顺序：先读本课建立场景，再按需回到方法课。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>端到端感知与显式 TSR 模块的竞争</strong>：以 UniAD / VAD 为代表的端到端架构主张「感知不必输出人类可读的中间结果」，而 TSR 恰恰是最需要显式中间结果的任务之一（限速值必须显示在仪表上、必须可审计、出事故要能追溯）。<em>「哪些感知任务可以被端到端吸收、哪些必须保留显式接口」目前没有定论</em>，而可解释性与法规要求正在把天平推向后者。",
            "<strong>VLM/VLA 做长尾标志理解</strong>：用视觉-语言模型直接读懂「前方 500 米施工，货车禁行，8:00–18:00」这类组合牌与文字牌，绕开「为每种组合定义一个类别」的死路。<em>难点是延迟（VLM 推理频率远低于 30 FPS）与幻觉（模型会「合理化」看不清的牌）</em>。现实路线是分层：小模型做高频检测，大模型对少数复杂牌做低频语义解析。这条线在 C59 展开。",
            "<strong>开放词表检测（open-vocabulary detection）在 TSR 的适用性</strong>：GLIP / Grounding DINO / OWL-ViT 让「用文本描述定义新类别」成为可能，理论上直接对上「新增标志类型不重训」的需求。<em>但交通标志的细类差别是「圆圈里的数字不同」这种极细粒度的视觉差异，而开放词表模型的强项是粗粒度语义对齐</em>——两者是否匹配，目前实验结果并不乐观。",
            "<strong>跨区域泛化与标志体系的形式化</strong>：如何把「在德国训练的模型」迁移到中国，本质上是「形状-颜色-语义映射函数」的迁移。<em>是否存在一种把 GB 5768 / Vienna / MUTCD 统一起来的中间表示（比如「形状+主色+图元」的组合编码），使得模型学到的是可组合的部件而非整体模板</em>，是一个既有理论价值又有工程价值的开放问题。",
            "<strong>物理世界对抗攻击</strong>：贴纸、涂鸦、特定图案可以让「停车让行」被稳定误分类（Eykholt 等人的经典工作），而这类攻击在真实道路上极易实施。<em>防御手段（时序一致性、多相机交叉验证、地图先验）都不是模型内部的，而是系统层面的</em>——这再次说明 TSR 的鲁棒性必须在系统层解决。",
            "<strong>评测基准与真实体验的脱节</strong>：现有 TSR 基准几乎都是单帧 mAP，而量产系统关心的是首检距离、闪烁率、FP/km、关键类召回。<em>缺少一个被广泛接受的、时序的、代价敏感的 TSR 基准</em>，是这个领域最明显的空白之一——也意味着大量论文的提升在车上不可见。",
        ]),
        CALLOUT("paper", "必读：Zhu et al., <em>Traffic-Sign Detection and Classification in the Wild</em>（CVPR 2016，TT100K 数据集与中国场景长尾的一手材料）★；Stallkamp et al., <em>Man vs. Computer: Benchmarking Machine Learning Algorithms for Traffic Sign Recognition</em>（Neural Networks 2012，GTSRB 与人类基准）★；Houben et al., <em>Detection of Traffic Signs in Real-World Images: The German Traffic Sign Detection Benchmark</em>（IJCNN 2013，GTSDB）；Ertler et al., <em>The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale</em>（ECCV 2020，全球尺度与区域差异）★；Eykholt et al., <em>Robust Physical-World Attacks on Deep Learning Visual Classification</em>（CVPR 2018，停车标志对抗贴纸）；Hu et al., <em>UniAD: Planning-oriented Autonomous Driving</em>（CVPR 2023 best paper，端到端架构与显式模块的张力）。标准文本：<em>GB 5768《道路交通标志和标线》</em>、<em>Vienna Convention on Road Signs and Signals (1968)</em>、<em>MUTCD</em>（美国联邦公路局）——<strong>这三份是模块 01 的基础，面试里能引用具体条款会很加分</strong>。相邻课程：C53/C54（检测器）、C57（小目标）、C58（长尾闭环）、C59（VLA）、C60（部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（针孔模型 / 像素预算 / 相机选型反解 / 代价不对称）

目标：在写任何模型代码之前，先用**物理量**把 TSR 的边界算清楚——
**多远的标志有多少像素、安全需要多远检出、什么相机配置才够、哪种错误更贵**。

本 notebook 你会亲手实现：
1. **针孔相机模型**：从 (图像宽, HFOV) 求等效焦距（像素）
2. **像素-距离换算器**：标志在任意距离下的成像尺寸与面积占比
3. **小目标判定**：算出「从多远开始，这块牌就是 COCO 定义的 small」
4. **安全反推**：从「100→60 km/h 要多少米」反推所需检出距离与像素
5. **五个本质不同的量化速览**（小·偏·硬·连·歪）
6. ✏️ 相机选型反解器 / 接近过程可用帧数 / 代价敏感风险打分

> 心智模型：**安全需要 146 米，光学只给 7 像素。这门课的六个模块都是在补这个缺口。**"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math, json, itertools, collections
import numpy as np

print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
print('numpy ', np.__version__)

assert sys.version_info >= (3, 8), '需要 Python 3.8+'
_ver = tuple(int(x) for x in np.__version__.split('.')[:2])
assert _ver >= (1, 20), 'numpy 版本过低'

rng = np.random.default_rng(55)
print('\\n✅ 环境就绪：本课全程 **纯 numpy + 标准库、CPU、不联网**。')
print('   我们不合成图像，只合成**物理量**——相机参数、标志尺寸、车速都用真实值。')"""),
    md("""## 2 · 针孔相机模型：从视场角求等效焦距

$$f_{px}=\\frac{W/2}{\\tan(\\mathrm{HFOV}/2)}$$

**这个量是 TSR 所有定量推理的起点**：它把「相机选型」和「感知能力」连成一条公式。"""),
    code("""def focal_px(img_w, hfov_deg):
    '''等效焦距（像素单位）。img_w: 图像宽（px）；hfov_deg: 水平视场角（度）。'''
    return (img_w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)

# 量产车上常见的四种前视配置
CAMERAS = {
    '广角 120° · 1920x1080': (1920, 1080, 120.0),
    '主摄  60° · 1920x1080': (1920, 1080,  60.0),
    '主摄  60° · 3840x2160': (3840, 2160,  60.0),
    '长焦  30° · 1920x1080': (1920, 1080,  30.0),
}

print(f"{'相机配置':<26s} {'f_px':>9s}   说明")
for name, (w, h, fov) in CAMERAS.items():
    print(f'{name:<26s} {focal_px(w, fov):>9.1f}')

# 数值校核
assert abs(focal_px(1920, 60.0) - 1662.77) < 0.5
assert abs(focal_px(1920, 30.0) - 3582.35) < 0.5
assert np.isclose(focal_px(3840, 60.0), 2 * focal_px(1920, 60.0))   # 分辨率翻倍 → 焦距翻倍
assert focal_px(1920, 120.0) < focal_px(1920, 60.0) < focal_px(1920, 30.0)
print('\\n✅ 视场角越窄 → 焦距越长 → 同一目标成像越大（代价是看得越窄）')
print('✅ 同视场角下分辨率翻倍 ⇔ 焦距翻倍 ⇔ **有效识别距离翻倍**，代价是算力约 4 倍')"""),
    md("""## 3 · 像素-距离换算器：标志在图像里到底有多大

$$p=\\frac{f_{px}\\cdot S}{Z}$$

标志的物理尺寸 S 来自 **GB 5768**：城区圆形禁令牌直径 60 cm，公路 80 cm，
三角警告牌边长 70 cm（郊区 90 cm）。"""),
    code("""def sign_px(f_px, size_m, dist_m):
    '''标志在图像中的成像边长（像素）。'''
    return f_px * size_m / dist_m

SIGN_SIZES = {          # GB 5768 常见规格（米）
    '圆形禁令牌 Ø60cm(城区)': 0.60,
    '圆形禁令牌 Ø80cm(公路)': 0.80,
    '三角警告牌 边长70cm':    0.70,
}

S = 0.60                                     # 本 notebook 的基准标志
f_main = focal_px(1920, 60.0)                # 基准相机：主摄 60° 1080p
DISTS = [20, 30, 50, 60, 80, 100, 146]

print(f'基准：{S*100:.0f} cm 圆形标志 · 主摄 60° 1920x1080 (f={f_main:.0f} px)\\n')
print(f"{'距离(m)':>8s} {'边长(px)':>10s} {'面积(px^2)':>12s} {'占全图':>9s}")
for z in DISTS:
    p = sign_px(f_main, S, z)
    frac = 100.0 * p * p / (1920 * 1080)
    print(f'{z:>8d} {p:>10.1f} {p*p:>12.0f} {frac:>8.4f}%')

assert abs(sign_px(f_main, S, 60) - 16.63) < 0.05
assert abs(sign_px(f_main, S, 100) -  9.98) < 0.05
assert abs(sign_px(f_main, S, 146) -  6.83) < 0.05
# 反比关系：距离翻倍 → 像素减半 → 面积变 1/4
assert np.isclose(sign_px(f_main, S, 50) / sign_px(f_main, S, 100), 2.0)
print('\\n⚠️  60 米外只有 **17 像素**，占全图面积 **0.013%**（约 1/7500）。')
print('    「16–30 px 是 TSR 的常态而非极端」——这句话是整门课的出发点。')"""),
    md("""## 4 · 小目标判定：从多远开始它就是 COCO 定义的 small

COCO 的定义：面积 < 32² = 1024 px² 为 small，32²–96² 为 medium，> 96² 为 large。
**关键问题不是「它是不是小目标」，而是「从多远开始它变成小目标」。**"""),
    code("""def coco_bucket(px):
    a = px * px
    return 'small' if a < 32**2 else ('medium' if a < 96**2 else 'large')

def dist_for_px(f_px, size_m, target_px):
    '''反解：标志成像达到 target_px 时对应的距离。'''
    return f_px * size_m / target_px

print(f"{'相机配置':<26s} {'变 small 的距离':>16s} {'降到 16px 的距离':>18s} {'降到 8px':>12s}")
for name, (w, h, fov) in CAMERAS.items():
    f = focal_px(w, fov)
    print(f'{name:<26s} {dist_for_px(f, S, 32):>14.1f} m {dist_for_px(f, S, 16):>16.1f} m'
          f' {dist_for_px(f, S, 8):>10.1f} m')

z32 = dist_for_px(f_main, S, 32)
assert abs(z32 - 31.18) < 0.05                # 主摄 60°：超过 31 米就是 small
assert coco_bucket(sign_px(f_main, S, 20)) == 'medium'
assert coco_bucket(sign_px(f_main, S, 40)) == 'small'
print(f'\\n⚠️  主摄 60° 下，**超过 {z32:.0f} 米这块牌就落进 COCO 的 small 桶**。')
print('    而 TSR 真正需要的工作距离是 60–150 米 —— 也就是说：')
print('    **TSR 的绝大部分工作量都发生在「比 COCO small 还小」的区域。**')
print('    这直接意味着：按 COCO 调好的 anchor/stride/IoU 阈值，拿到 TSR 上必然要重调。')"""),
    md("""## 5 · 从安全需求反推检出距离：本课的中心矛盾

$$D = v_0 t_r + \\frac{v_0^2-v_1^2}{2a}$$

$t_r$ 是**总反应时间**（感知确认 + 决策 + 执行器响应），$a$ 是可接受的减速度。
乘用车舒适减速度约 2 m/s²，紧急制动可到 6–8 m/s² 但会明显影响体验。"""),
    code("""def required_distance(v0_kmh, v1_kmh, decel=2.0, reaction_s=0.8):
    '''从 v0 减到 v1 所需的纵向距离（米）。'''
    v0, v1 = v0_kmh / 3.6, v1_kmh / 3.6
    return v0 * reaction_s + max(0.0, (v0**2 - v1**2) / (2 * decel))

SCENARIOS = [
    ('高速 120 -> 100 (限速降级)', 120, 100, 2.0, 0.8),
    ('高速 100 ->  60 (施工区)  ', 100,  60, 2.0, 0.8),
    ('高速 100 ->  60 (可接受急一点)', 100, 60, 3.0, 0.8),
    ('城区  60 ->  30 (学校区域)', 60,  30, 2.0, 0.8),
    ('城区  50 ->   0 (停车让行)', 50,   0, 3.0, 0.8),
]

print(f"{'场景':<32s} {'所需距离':>10s} {'主摄60°像素':>13s} {'长焦30°像素':>13s}")
for name, v0, v1, a, tr in SCENARIOS:
    D = required_distance(v0, v1, a, tr)
    p_main = sign_px(focal_px(1920, 60.0), S, D)
    p_tele = sign_px(focal_px(1920, 30.0), S, D)
    print(f'{name:<32s} {D:>9.1f} m {p_main:>12.1f} {p_tele:>12.1f}')

D_key = required_distance(100, 60, 2.0, 0.8)
assert abs(D_key - 145.68) < 0.1
assert abs(sign_px(focal_px(1920, 60.0), S, D_key) - 6.85) < 0.05
assert sign_px(focal_px(1920, 30.0), S, D_key) > 2 * sign_px(focal_px(1920, 60.0), S, D_key)
print(f'\\n⚠️  **本课的中心矛盾**：100->60 km/h 需要 {D_key:.0f} 米的提前量，')
print(f'    而那里主摄只给 {sign_px(focal_px(1920,60.0), S, D_key):.1f} 像素 —— '
      '「60」和「80」的区别在物理上不存在。')
print('✅ 出路只有三条，且必须组合使用：')
print('   ① 换硬件：长焦相机 / 更高分辨率（有效距离随焦距线性增长）')
print('   ② 用时序：远处先输出 L1 粗类，随着接近逐帧累积到 L2 细类（模块 04）')
print('   ③ 用先验：高精地图的标志图层给出「这里应该有一块牌」（模块 04）')
print('   —— **没有一条是「换更大的 backbone」**。这就是 TSR 领域知识的价值。')"""),
    md("""## 6 · 五个本质不同的量化速览：小 · 偏 · 硬 · 连 · 歪

上面已经量化了「小」。这一节把另外四个也各用几行代码量化一次，
**目的是让这个框架从「五句话」变成「五个数」**——面试里说得出数字才可信。"""),
    code("""# ── ① 小：IoU 对位移的敏感性（同样偏移 2 px，小框被判死、大框没事）
def iou_shift(side, delta):
    '''边长 side 的正方形框在 x,y 各偏移 delta 后与原框的 IoU。'''
    inter = max(0.0, side - delta) ** 2
    return inter / (2 * side**2 - inter)

print('① 小 —— 同样偏移 2 px：')
for s_ in [8, 16, 32, 64]:
    print(f'   {s_:>3d}x{s_:<3d} 框  IoU = {iou_shift(s_, 2):.3f}'
          f'   {"❌ 低于 0.5 阈值，直接被判为负样本" if iou_shift(s_, 2) < 0.5 else ""}')
assert abs(iou_shift(8, 2) - 36/92) < 1e-9
assert abs(iou_shift(64, 2) - 0.8842) < 1e-3
print('   → IoU=0.5 对 8px 框要求「亚 2 像素」定位，对 64px 框只要求「10 像素以内」。')
print('   → **同一个阈值，两个数量级的严苛度差异** —— 小目标正样本稀缺的根因。\\n')

# ── ② 偏：长尾（Zipf），且尾巴随地域改变
ranks = np.arange(1, 121)
w = ranks ** -1.6; w = w / w.sum()
print('② 偏 —— 120 个细类、Zipf(s=1.6) 的类别分布：')
print(f'   前 10 类占全部实例的 {100*w[:10].sum():.1f}%')
print(f'   后 60 类合计只占     {100*w[60:].sum():.1f}%')
print(f'   头尾频次比            {w[0]/w[-1]:.0f}x')
assert w[:10].sum() > 0.75 and w[60:].sum() < 0.05
print('   → 而且这条尾巴是**区域相关**的：「注意牲畜」在西部国道是常见类。\\n')

# ── ③ 硬：错分直接变成错误的控制动作
CONFUSABLE = [('限速60', '限速80', '车按 80 开，超速'),
              ('限速80', '限速60', '无故减速，用户投诉'),
              ('禁止驶入', '禁止停车', '错过路口/绕路'),
              ('停车让行', '减速让行', '路口不停车，安全事件')]
print('③ 硬 —— 错分不是「掉分」，是错误的控制动作：')
for a, b, effect in CONFUSABLE:
    print(f'   {a} → {b:<8s}  下游后果：{effect}')
print('   → **混淆矩阵比 mAP 重要**：你必须知道哪几对类互相错分。\\n')

# ── ④ 连：接近过程中有多少帧可用
def approach_seconds(z_far, z_near, speed_kmh):
    return (z_far - z_near) / (speed_kmh / 3.6)
t_ = approach_seconds(100, 30, 100.0)
print('④ 连 —— 标志静止 + 自车运动已知：')
print(f'   100 km/h 下从 100 m 接近到 30 m 用时 {t_:.2f} s，30 FPS 下有 '
      f'{math.floor(t_*30 + 1e-9)} 帧观测')
assert math.floor(t_ * 30 + 1e-9) == 75
print('   → 而行人检测拿不到这个红利（目标自己在动，未来位置不可解析预测）。')
print('   → **TSR 的跟踪本质上是自车运动补偿，而不是目标运动建模。**\\n')

# ── ⑤ 歪：双重不对称（FN vs FP，且按类别再次不对称）
COST = {'停车让行': {'fn': 1000, 'fp':  50},
        '限速60':   {'fn':  100, 'fp':  30},
        '景点指示': {'fn':    1, 'fp':   1}}
print('⑤ 歪 —— 代价的双重不对称（相对单位）：')
print(f"   {'类别':<10s} {'漏检代价':>9s} {'误检代价':>9s} {'FN/FP 比':>10s}")
for k, v in COST.items():
    print(f"   {k:<10s} {v['fn']:>9d} {v['fp']:>9d} {v['fn']/v['fp']:>10.1f}x")
assert COST['停车让行']['fn'] / COST['景点指示']['fn'] == 1000
print('   → 关键类与非关键类的漏检代价相差 1000 倍，而 mAP 对它们**一视同仁**。')
print('   → 这就是模块 05「安全导向评测」存在的理由。')"""),
    md("""## ✏️ 练习 1：相机选型反解器

实现 `required_hfov_deg(size_m, dist_m, min_px, img_w)`：
给定「物理尺寸 `size_m` 的标志，必须在 `dist_m` 米外达到 `min_px` 像素」，
求所需的**最大**水平视场角（度）。

推导：`f = min_px * dist_m / size_m`，`HFOV = 2 * arctan((img_w/2) / f)`。

这是把「感知需求」翻译成「相机选型」的那一步——面试里能当场推出来非常加分。"""),
    code("""def required_hfov_deg(size_m, dist_m, min_px, img_w=1920):
    # TODO: ① 求所需焦距 f（像素）  ② 由 f 与 img_w 反解 HFOV（度）
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
h1 = required_hfov_deg(0.60, 100.0, 20, 1920)
h2 = required_hfov_deg(0.60,  50.0, 20, 1920)
h3 = required_hfov_deg(0.60, 100.0, 30, 1920)
assert abs(h1 - 32.15) < 0.2, f'60cm 标志 @100m 达 20px 需要约 32° 视场，得到 {h1}'
assert abs(h2 - 59.87) < 0.2, f'@50m 达 20px 恰好对应约 60° 主摄，得到 {h2}'
assert h3 < h1, '要求更多像素 → 视场必须更窄'
assert required_hfov_deg(0.60, 100.0, 20, 3840) > h1, '分辨率翻倍 → 同需求下可用更宽视场'
print(f"{'需求':<34s} {'所需 HFOV':>10s}")
for s_, z_, p_, w_ in [(0.6, 50, 20, 1920), (0.6, 100, 20, 1920),
                       (0.6, 146, 20, 1920), (0.6, 100, 20, 3840)]:
    print(f'{f"{s_*100:.0f}cm @ {z_}m >= {p_}px, W={w_}":<34s} '
          f'{required_hfov_deg(s_, z_, p_, w_):>9.1f}°')
print('\\n✅ 练习 1 通过：**「要在 100 m 外识别限速牌」= 「要一路 32° 的长焦相机」**')
print('   —— 量产车上那颗 30° 长焦的来历，就是这一行公式。')"""),
    md("""## ✏️ 练习 2：接近过程的可用帧数

实现 `approach_frames(z_far, z_near, speed_kmh, fps)`：
车以 `speed_kmh` 匀速接近，标志从 `z_far` 米到 `z_near` 米之间共有多少帧观测。

用 `t = (z_far - z_near) / (speed_kmh / 3.6)`，
帧数 `= math.floor(t * fps + 1e-9)`（+1e-9 是为了避开浮点误差，必须照写）。

这个数决定了模块 04「多帧融合」能有多少本钱。"""),
    code("""def approach_frames(z_far, z_near, speed_kmh, fps=30.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert approach_frames(100, 30, 100.0, 30.0) == 75
assert approach_frames(100, 30, 120.0, 30.0) == 63
assert approach_frames(100, 30,  60.0, 30.0) == 126
assert approach_frames(100, 30, 100.0, 15.0) == 37      # 帧率减半 → 帧数减半
assert approach_frames( 60, 30, 100.0, 30.0) == 32      # 只从 60m 起算 → 帧数骤减
print(f"{'场景':<34s} {'可用帧数':>9s}")
for zf, zn, v, f_ in [(100, 30, 100, 30), (100, 30, 120, 30), (100, 30, 60, 30),
                      (60, 30, 100, 30), (100, 30, 100, 15)]:
    print(f'{f"{zf}->{zn} m @ {v} km/h, {f_} FPS":<34s} '
          f'{approach_frames(zf, zn, v, f_):>9d}')
print('\\n✅ 练习 2 通过。三条可迁移的结论：')
print('   ① 车速越高，可用帧数越少 —— **高速工况才是 TSR 最难的工况**（信息更少、要求更远）')
print('   ② 帧率是可用信息量的线性因子，但提高帧率也线性提高算力')
print('   ③ **能多早开始检出，比单帧精度更值钱**：首检距离从 60m 推到 100m，')
print('      可用帧数从 32 涨到 75 —— 多帧融合的空间直接翻倍。')"""),
    md("""## ✏️ 练习 3：代价敏感的风险打分

实现 `risk_score(errors, costs)`：

- `errors = {类别: {'fn': 漏检次数, 'fp': 误检次数}}`
- `costs  = {类别: {'fn': 单次漏检代价, 'fp': 单次误检代价}}`
- 返回 `{类别: fn*cost_fn + fp*cost_fp}`

**这是模块 05 的雏形**：它回答的是「下一个季度先修哪个类」，
而 mAP 回答不了这个问题。"""),
    code("""def risk_score(errors, costs):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
ERRORS = {'停车让行': {'fn':   2, 'fp':   1},
          '限速60':   {'fn':  30, 'fp':  20},
          '景点指示': {'fn': 200, 'fp': 150}}
COSTS  = {'停车让行': {'fn': 1000, 'fp': 50},
          '限速60':   {'fn':  100, 'fp': 30},
          '景点指示': {'fn':    1, 'fp':  1}}
r = risk_score(ERRORS, COSTS)
assert r['停车让行'] == 2050 and r['限速60'] == 3600 and r['景点指示'] == 350
rank = sorted(r, key=lambda k: -r[k])
assert rank == ['限速60', '停车让行', '景点指示']
assert r['停车让行'] > r['景点指示'], '错误数少 100 倍，风险却高 6 倍'

n_err = {k: v['fn'] + v['fp'] for k, v in ERRORS.items()}
print(f"{'类别':<10s} {'错误总数':>9s} {'风险分':>9s}  {'按错误数排名':>12s} {'按风险排名':>10s}")
by_n = sorted(n_err, key=lambda k: -n_err[k])
for k in ERRORS:
    print(f'{k:<10s} {n_err[k]:>9d} {r[k]:>9d} {by_n.index(k)+1:>12d} {rank.index(k)+1:>10d}')
print('\\n✅ 练习 3 通过。两个必须记住的结论：')
print('   ① **按错误数排序与按风险排序的结果完全相反**（景点指示错最多，风险最低）。')
print('      按「哪个类 badcase 最多」安排工作，就是在给最不重要的类投入最多人力。')
print('   ② 风险 = 频率 x 代价，两项都要算。「限速60」之所以排第一，')
print('      不是因为它最危险，而是因为它**又常见又不便宜** —— 这才是真实的优先级。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def required_hfov_deg(size_m, dist_m, min_px, img_w=1920):
    f = min_px * dist_m / size_m                       # 所需等效焦距（像素）
    return 2.0 * math.degrees(math.atan((img_w / 2.0) / f))"""),
    code("""# 练习 2 参考答案
def approach_frames(z_far, z_near, speed_kmh, fps=30.0):
    t = (z_far - z_near) / (speed_kmh / 3.6)           # 接近过程时长（秒）
    return math.floor(t * fps + 1e-9)"""),
    code("""# 练习 3 参考答案
def risk_score(errors, costs):
    return {c: errors[c]['fn'] * costs[c]['fn'] + errors[c]['fp'] * costs[c]['fp']
            for c in errors}"""),
    md("""---
## 🧪 真实工程胶囊：一页纸的 TSR 感知规格书

下面这份 `RECIPE` 可以原样复制到真实项目里作为**感知需求文档的骨架**。
它把本模块的四件事（软件栈位置 / 五个本质不同 / 四层输出 / 像素预算）
落成可评审、可验收的条目。"""),
    code("""RECIPE = r'''
# ============================================================
# TSR 感知规格书（骨架）  v0.1
# ============================================================

## 1. 硬件与像素预算  ——  先算物理，再谈模型
camera:
  main:  {resolution: [1920, 1080], hfov_deg: 60,  f_px: 1663}
  tele:  {resolution: [1920, 1080], hfov_deg: 30,  f_px: 3582}
  wide:  {resolution: [1920, 1080], hfov_deg: 120, f_px: 554}

sign_physical_size_m:      # 依据 GB 5768
  prohibitory_circle_urban: 0.60
  prohibitory_circle_road:  0.80
  warning_triangle:         0.70

# 像素预算（60cm 标志）：p = f_px * S / Z
#   主摄: 50m->20px  60m->17px  100m->10px  146m->6.8px
#   长焦: 50m->43px 100m->21px  146m->15px
# 结论：>100m 的 L2 细类识别必须依赖长焦；主摄在 >60m 只承诺 L1 粗类。

## 2. 需求反推  ——  安全需要多远
required_detection_distance_m:
  # D = v0*t_r + (v0^2 - v1^2) / (2a)，t_r=0.8s，a=2.0 m/s^2
  highway_100_to_60: 146
  highway_120_to_100: 106
  urban_60_to_30:     70
# ⚠️ 146m 处主摄仅 6.8px —— 单帧不可解。必须：长焦 + 时序累积 + 地图先验。

## 3. 输出 schema  ——  四层，缺一层下游就用不了
TsrDetection:
  # L0 定位
  bbox_xyxy:        [float, float, float, float]
  camera_id:        str            # 多相机融合必须
  timestamp_ns:     int            # 时序关联必须
  det_confidence:   float          # ⚠️ 与 cls_confidence **分开输出，不要相乘**
  # L1 粗类（可降级：细类不确定时仍然输出这一层）
  coarse_class:     enum[prohibitory, warning, mandatory, guide, auxiliary, workzone, vms]
  coarse_confidence: float
  # L2 细类
  fine_class:       enum[...] | UNKNOWN
  cls_confidence:   float
  # L3 属性
  attributes:
    speed_value:      int   | null      # 限速值
    time_range:       str   | null      # "08:00-18:00"
    vehicle_type:     str   | null      # "truck"
    arrow_direction:  str   | null
    condition:        enum[normal, faded, damaged, occluded, graffiti]
    facing:           enum[front, back, side]      # ← 对向车道判定的几何证据
    is_variable:      bool                         # 可变电子牌
    group_id:         int   | null      # 组合牌（主牌 + 辅助牌）的关联
  # 时序（由融合层填充，感知层留空）
  track_id:         int | null
  first_seen_dist_m: float | null
  accumulated_confidence: float | null

## 4. 验收指标  ——  mAP 只是入场券
acceptance:
  bucketed_recall:                  # 按像素尺寸分桶，否则改进不可见
    ">= 32px": 0.98
    "16-32px": 0.92
    "8-16px":  0.70                 # L1 粗类召回；L2 不做承诺
  critical_class_recall:            # 关键类单独立指标
    stop_giveway: 0.995
  false_positive_per_km: "< 0.05"   # ← 比 precision 有用得多
  first_detection_distance_p50_m:
    speed_limit: 90
  flicker_per_instance: "< 0.5"     # 上报后又撤销的次数
  latency_p99_ms: 25                # 尾延迟，不是均值

## 5. 明确不做的事（写清楚边界，避免下游误用）
non_goals:
  - 感知层不判断标志是否对自车生效；只输出 facing / 横向位置 / 3D 位置等几何证据
  - 感知层不做限速值的合法性校验（如 "限速 999"）；由下游规则层兜底
  - 可变电子牌只输出「这是 VMS + 当前读数」，不承诺读数的时效性
'''
print(RECIPE)
for k in ['f_px', 'GB 5768', 'required_detection_distance_m', 'det_confidence',
          'coarse_class', 'facing', 'false_positive_per_km', 'non_goals']:
    assert k in RECIPE, k
print('✅ 规格书覆盖：像素预算 / 需求反推 / 四层输出 schema / 分桶验收 / 边界声明')"""),
    md("""### 小结

- **先算物理，再谈模型。** 针孔模型 `p = f_px·S/Z` 与制动公式 `D = v₀t_r + (v₀²-v₁²)/2a`
  这两行，就能定出一套 TSR 方案的上界。**面试里先算这两个数，再谈方案。**
- **本课的中心矛盾**：安全需要 146 m 的检出距离，主摄在那里只给 6.8 px。
  出路只有 **长焦 / 时序 / 地图** 三条，**没有一条是「换更大的 backbone」**。
- **五个本质不同：小 · 偏 · 硬 · 连 · 歪。** 目标小（16 px 是常态）、分布偏（且尾巴随地域搬家）、
  语义硬（直接变控制约束）、时序连（静止刚体 + 自车运动已知）、代价歪（双重不对称）。
  **前三点是问题难度，第五点是损失函数形状，第四点是额外先验——用第四点去补前三点。**
- **TSR 的输出是四层**（定位 / 粗类 / 细类 / 属性），不是「框 + 类别」。
  L1 存在的理由是**可降级**；L3 里的 `facing` 与车道关联是最容易漏、也最容易加分的两项。
  **两个置信度要分开输出，不要相乘。**
- **感知层如实输出所有标志与几何证据，「这块牌是否对自车生效」由有上下文的下游判断。**
  把这个判断塞进感知层是常见的架构错误。
- **按错误数排优先级与按风险排优先级的结论常常相反。** 风险 = 频率 × 代价，两项都要算。

下一站：**模块 01 · 数据集与标志分类体系** —— 你的类别体系决定了你的天花板。""")
,
]
