# -*- coding: utf-8 -*-
"""C58 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "Python/numpy；C55（TSR 与自动驾驶感知）、C43（数据工程）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 复现长尾统计、难例挖掘与闭环决策"),
    ("预计时长", "总览 30 分钟 + notebook 35 分钟"),
]

SECTIONS = [
    ("moat", "护城河：模型架构会趋同，数据飞轮不会", "".join([
        P("先把这门课的立场亮出来：<strong>在量产自动驾驶感知里，真正的护城河是数据闭环，不是模型架构。</strong>这不是一句励志口号，而是一个可以被论证、也可以被证伪的工程判断。"),
        P("论证分三层。"),
        OL([
            "<strong>架构可复制，数据不可复制。</strong>RT-DETR、RTMDet、YOLOv10 的论文与权重都是公开的。任何一个有 8 张卡的团队，一周内就能把 COCO 上的数字复现到论文的 ±0.5 mAP 以内。<em>但没有任何一个团队能在一周内拿到「十万段中国高速隧道出口逆光下的限速牌」。</em>前者是知识，知识会扩散；后者是资产，资产要靠车队里程一公里一公里地攒。",
            "<strong>架构红利是一次性的，数据红利是复利的。</strong>把 backbone 从 ResNet-50 换成 CSPNeXt，涨 1.5 mAP，然后就到顶了——你不能再换一次同样的 backbone 再涨 1.5。而数据闭环是一个正反馈环：车越多 → 遇到的 badcase 越多 → 挖回来修好 → 模型越好 → 用户越敢用 → 里程越多 → 车越多。<em>这个环每转一圈，下一圈的起点都更高。</em>",
            "<strong>长尾是无限的，架构穷举不了。</strong>被树叶遮住一半的「注意行人」、褪色到发白的限速牌、贴在货车尾门上的假标志、临时施工用手写板改过的限速——这些场景写不完，也没有哪个 attention 变体能凭空推理出它们。<em>唯一的解法是「遇到 → 收回来 → 学会」，也就是闭环。</em>",
        ]),
        TABLE(["", "架构红利", "数据红利"], [
            ["来源", "论文 + 开源权重", "<strong>车队里程 + 闭环基础设施</strong>"],
            ["可复制性", "<strong>几乎完全可复制</strong>（一周内）", "不可复制（要几年里程 + 一整套工具链）"],
            ["收益形态", "一次性阶跃，很快到顶", "<strong>复利</strong>：每一轮闭环抬高下一轮的起点"],
            ["对长尾的作用", "几乎为零（架构不产生新知识）", "<strong>唯一有效的手段</strong>"],
            ["典型量级", "同一延迟档位内 1–3 mAP", "针对场景切片可以是 <strong>10–30 AP</strong>"],
            ["失效方式", "被别人一周内追平", "被自己的流程拖垮（下一节讲）"],
        ]),
        DUAL(
            "所以「上更强的 backbone」在面试里是一个<strong>典型的初级回答</strong>。<em>面试官问「如果给你更多资源你会做什么」，他真正想知道的是：你会不会做误差分析、会不会定位到具体场景、会不会为那个场景建触发器和评测切片。</em>回答「先做分场景误差分析，找出拖后腿的切片，为它建一条触发-挖掘-标注-验证的闭环，并用切片指标证明它涨了而其他切片没掉」——这才是量产团队想要的人。",
            "但必须同时承认反面：<strong>有数据 ≠ 有闭环</strong>。很多团队存了 PB 级的路采视频，硬盘天天在烧钱，却没有触发器（不知道该回传什么）、没有检索（找不到「和这个 badcase 长得像的」）、没有切片评测（不知道改动有没有用）。<em>这时数据不是资产，是负债。</em>本课就是把「PB 级视频」变成「可持续提升的模型」中间那一整套东西拆开讲。",
        ),
        CALLOUT("intuition", "一句话心法：<strong>模型架构决定你的天花板有多高，数据闭环决定你多快能撞到天花板、以及天花板本身会不会往上长。</strong>在 COCO 上比架构，在路上比闭环。"),
    ])),

    ("loop", "闭环三环节：触发 → 挖掘 → 验证", "".join([
        P("把「数据闭环」这个词拆开，它其实是三个可以分别失败、分别度量、分别优化的环节。<strong>这三个环节的划分是本课的骨架</strong>——后面五个模块正好一一对应。"),
        ASCII("""                       ┌──────────────── 车队（每天百万公里）────────────────┐
                       │                                                      │
                       ▼                                                      │
              ① 触发 TRIGGER                                                  │
              「什么样的帧值得回传？」                                          │
              · 不确定性（熵 / margin / 低置信）                                │
              · 一致性（多模型分歧 / 多帧类别跳变 / TTA 分歧）                   │
              · 规则（跟踪丢失 / 与高精地图不符 / 接管与急刹前后）               │
              约束：**回传带宽有限** → 触发率必须可控（典型 1e-5 ~ 1e-4）        │
                       │  回传 10^4 ~ 10^6 帧/天                               │
                       ▼                                                      │
              ② 挖掘 MINING                                                    │
              「从回传里挑出真正该标的那一小撮」                                 │
              · 嵌入检索：找「和这个 badcase 长得像的」                          │
              · 场景打标：天气/光照/道路/标志类别/遮挡度（规则 + VLM）           │
              · 去重与多样性：近重复过滤、core-set、聚类均衡                     │
              · 预算分配：按「类别缺口 × 难度 × 标注成本」分钱                    │
              约束：**标注预算有限** → 只有 10^3 ~ 10^4 帧能进标注              │
                       │                                                      │
                       ▼                                                      │
              ③ 验证 VALIDATION                                                │
              「怎么证明这批数据真的有用」                                       │
              · 分场景切片评测（目标切片涨了吗？）                                │
              · 回归门禁（其他切片掉了吗？掉多少算掉？）                          │
              · 显著性（涨的是数据的功劳还是种子噪声？）                          │
              · 边际收益曲线（还值不值得再标 1000 张？）                          │
                       │  通过门禁 → 发布 → 上车                                │
                       └──────────────────────────────────────────────────────┘

  闭环的核心度量：**cycle time** = 从「发现一个 badcase」到「修复版本上车」的天数。
  一流团队 1–2 周；做不动的团队 3 个月，或者根本量不出来。"""),
        TABLE(["环节", "输入 → 输出", "本课模块", "最常见的断点"],  [
            ["<strong>① 触发</strong>", "车端连续帧 → 少量候选帧", "m03（主动学习与触发策略）", "触发率没预算约束，一天回传几十 TB，管道直接堵死"],
            ["<strong>② 挖掘</strong>", "候选帧 → 待标注清单", "m02（难例挖掘）· m04（挖掘基础设施）", "<strong>不去重</strong>：回传的 1000 张里 900 张是同一个路口的连续帧"],
            ["<strong>③ 验证</strong>", "新模型 → 发布 / 打回", "m05（闭环验证）", "只看整体 mAP，不做切片；改动到底有没有用没人说得清"],
            ["贯穿", "类别分布本身就是歪的", "<strong>m01（类别不平衡）</strong>", "把长尾当成「数据不够」，其实还有一半是「损失与分类器的问题」"],
        ]),
        DUAL(
            "三个环节里，<strong>最容易被跳过的是 ③ 验证</strong>，而它恰恰是唯一能防止你白干的环节。「标了 2 万张夜间数据，整体 mAP +0.2」——这句话什么也没说明：+0.2 可能在种子方差以内（检测任务同配置换种子的典型波动就是 ±0.2~0.5），也可能是「夜间 +3、白天 -2」被平均掉了。<em>没有切片评测的闭环，是一个把钱变成硬盘占用的机器。</em>",
            "而<strong>最贵的是 ② 挖掘</strong>：标注是唯一一个成本随数据量线性增长且不可摊薄的环节（触发和验证都是写一次代码用无数次，标注是每一张都要花钱）。<em>所以挖掘环节的全部工程努力，本质上都在做一件事：提高「每一块标注预算换到的模型提升」。</em>去重、多样性采样、按类别缺口分配预算、用嵌入检索精确定位同类 badcase——它们的收益都应该折算成「每千元标注费带来的目标切片 AP」来衡量。",
        ),
        CALLOUT("warn", "一个反复出现的组织性失败：<strong>三个环节分属三个团队，而闭环的度量（cycle time）不属于任何一个团队</strong>。感知团队负责模型，数据团队负责标注，工具团队负责管道，每个团队的 KPI 都达标，但从「发现问题」到「修好上车」要三个月。<em>面试里如果你能主动提出「我会先把 cycle time 量出来」，这是一个很强的系统性思维信号。</em>"),
    ])),

    ("useless", "为什么「加数据」常常无效：四种失效", "".join([
        P("「效果不好？加数据。」这是所有回答里最安全也最没用的一句。<strong>加数据在实践中失败的频率高得惊人</strong>，而且失败的方式高度可归类。把这四类背下来，你就能在面试里把「长尾怎么办 / recall 怎么提」这类问题答到别人答不到的深度。"),
        TABLE(["失效", "机制", "症状（怎么看出来）", "检查方法"], [
            ["<strong>① 加的是已经会的</strong>",
             "随机采样的帧里 95%+ 是模型 loss ≈ 0 的样本，反传梯度接近零，<em>它们不携带任何新信息</em>",
             "训练 loss 曲线几乎不变；指标在噪声内波动；新增 10 万张与新增 0 张没区别",
             "<strong>算新数据的「有效样本数」</strong>：用当前模型跑一遍，看 loss 分布；<code>sum(loss)/参考难样本loss</code> 才是真正的增量"],
            ["<strong>② 加的分布不对</strong>",
             "问题出在隧道出口逆光，加的是城市晴天；新数据落在已经饱和的切片上",
             "整体 mAP 微涨 0.1–0.3，<strong>目标切片纹丝不动</strong>",
             "加数据<em>之前</em>先做分场景误差分析；新数据也要按同一套切片打标，看它落在哪个桶"],
            ["<strong>③ 加的标注有噪</strong>",
             "众包标注对小目标漏标严重；<strong>漏标的 GT 变成负样本监督</strong>——模型被明确告知「这里没有标志」",
             "<strong>recall 反而下降</strong>；训练 loss 反而升高；小尺寸桶掉得最狠",
             "抽检 200 张算标注一致性（IoU + 类别 agreement）；用当前模型的高分假正例反查漏标"],
            ["<strong>④ 加完没验证</strong>",
             "只看整体指标；不同切片的涨跌互相抵消；提升量在种子方差以内",
             "「涨了 0.2」但没人能说清是哪涨了；下一次改动又「涨了 0.2」，累计起来却没涨",
             "<strong>切片评测 + 多种子 + 配对检验</strong>；旧切片不掉点设为硬门禁"],
        ]),
        P("四类里，<strong>③ 最危险</strong>，因为它的方向是反的：其他三类最多是白花钱，③ 是花钱把模型变差。"),
        CALLOUT("danger", "<p><strong>漏标的危害是不对称的。</strong>在检测里，一个没被标注的真实目标不只是「少了一个正样本」——它所在的位置会被标签分配判定为背景，从而产生一条<em>明确的负梯度</em>：「这个位置没有交通标志」。模型学到的不是「不确定」，而是「确定没有」。</p><p>在 TSR 里这一点尤其致命：<strong>最容易漏标的恰恰是最远、最小、最需要提前检出的那一批标志</strong>（20×20 像素以下，标注员在 1080p 图上要放大才看得见）。于是漏标噪声与「远距离早检出」这个核心指标精确地打在同一个位置上。<em>「加了 5 万张远距离数据，60 米外的召回反而掉了 3 个点」——这是真实会发生的事，原因就在这里。</em></p>", "漏标 = 负监督，不是缺失"),
        DUAL(
            "把四类失效倒过来读，就是<strong>加数据之前必须回答的四个问题</strong>：这批数据模型现在会不会（<em>不会才值得加</em>）？它落在哪个切片（<em>必须是目标切片</em>）？标注质量抽检过没有（<em>尤其小目标</em>）？我打算用什么切片、什么显著性标准来判定它有用（<em>加之前就要定好</em>）？",
            "更进一步，这四个问题定义了<strong>「一份数据的价值」这个量的可测形式</strong>：价值 = 增量信息（不是已经会的）× 分布对齐（落在目标切片）× 标注保真度（不是噪声）× 可验证性（能被切片指标检出）。<em>四项任何一项为零，整批数据的价值就是零</em>——它们是乘法关系，不是加法关系。这也解释了为什么「多加点数据总没坏处」这个直觉是错的：③ 那一项可以是<strong>负数</strong>。",
        ),
    ])),

    ("powerlaw", "长尾的幂律本质与边际收益递减", "".join([
        P("现在给上面的判断一个定量的底座。交通标志的类别分布不是「有点不均衡」，它是<strong>幂律（power law）</strong>——按频次排序后，第 <em>r</em> 名类别的实例数近似满足："),
        MATH(r"n_r \;=\; n_1 \cdot r^{-\alpha}, \qquad \alpha \in [1.5,\,2.5] \ \ \text{(典型交通标志数据集)}"),
        P("取对数后是一条直线：<code>log n_r = log n_1 − α log r</code>。<strong>这条直线是可以在你自己的数据集上画出来的</strong>，而且它非常稳——换城市、换年份，斜率变化很小。它带来三个必须内化的结论。"),
        TABLE(["结论", "内容", "工程后果"], [
            ["<strong>① 尾部的类别数占多数，实例数占极少</strong>",
             "α≈1.9、80 类时，排名 40 之后的 41 个类（占类别数 51%）只占实例总数的 <strong>约 3%</strong>",
             "按实例采样时，一个 epoch 里尾部类几乎不出现；<em>macro 指标（每类平均）与 micro 指标（每实例平均）会给出完全相反的结论</em>"],
            ["<strong>② 头部早已饱和</strong>",
             "头部类有 10 万实例，AP 已经 0.90+；再加 3 万张对它的边际收益接近 0",
             "随机加数据 = 把绝大部分预算花在饱和区；<strong>这是失效 ① 与 ② 的数学根源</strong>"],
            ["<strong>③ 长尾没有尽头</strong>",
             "幂律没有截断：你解决了排名 60 的类，排名 61 会顶上来",
             "<em>目标不是「消灭长尾」，而是把「发现→修复」的 cycle time 压到足够短</em>"],
        ]),
        P("再看单个切片的边际收益。经验上，某个场景切片的 AP 随该切片训练样本数 <em>n</em> 的增长近似满足一条<strong>饱和幂律</strong>："),
        MATH(r"\mathrm{AP}(n) \;=\; \frac{A_{\max}}{1 + (k/n)^{\beta}}, \qquad \frac{d\,\mathrm{AP}}{dn} \propto n^{-(\beta+1)}"),
        P("<code>k</code> 是「半饱和样本数」（AP 达到一半上限时的样本量），<code>β</code> 是陡峭度。关键在导数：<strong>边际收益按 <code>n^{-(β+1)}</code> 衰减</strong>。取 β=0.6，把一个切片从 25 张加到 5000 张，AP 从 0.21 涨到 0.80；而把另一个切片从 5 万张加到 5.3 万张，AP 只涨 0.001。<strong>两张标注的边际价值可以差三个数量级。</strong>"),
        DUAL(
            "所以「数据越多越好」是错的，正确的说法是<strong>「每一张数据的边际收益差了几个数量级，你要做的是把预算搬到陡峭段」</strong>。<em>10 张精准定位的隧道出口逆光数据，可能比 10000 张随机路采更有用</em>——这不是修辞，notebook 里会把这个倍数算出来（在合成设定下定向加数据的宏观收益是随机加数据的 15–20 倍）。",
            "这条曲线还有一个更实用的用法：<strong>它是「还值不值得再标 1000 张」的决策工具</strong>。在目标切片上标 200 / 500 / 1000 张各训一次，拟合 <code>A_max、k、β</code>，就能外推「再标 2000 张能涨多少」，再与标注成本比较。<em>这是把「数据决策」从拍脑袋变成算账的唯一办法</em>，也是 m05 的核心内容。反过来，如果拟合出来的 <code>A_max</code> 只有 0.55，那说明<strong>瓶颈根本不是数据量</strong>（可能是分辨率、是标注定义、是任务本身在该切片上不可解），继续标下去是浪费。",
        ),
        CALLOUT("intuition", "把幂律与边际收益合起来看，长尾问题的真正结构是：<strong>类别频率是幂律的，而每类的边际收益是它自身样本数的减函数——两者叠加，导致「按自然分布采样」几乎必然把预算花在最没用的地方。</strong>本课后面所有技术（重采样、重加权、触发器、嵌入检索、core-set、预算分配）都是在对抗这一句话。"),
    ])),

    ("map", "课程地图：六个模块怎么串起来", "".join([
        ASCII("""起点：模型在整体 mAP 上看着还行，但尾部类 AP 接近 0，路测时总在同几个场景翻车。

  模块 00  课程总览与环境                  ← 你在这里
     │      护城河论证 / 闭环三环节 / 加数据无效的四种失效 / 幂律与边际收益
     ▼
  模块 01  **类别不平衡的处理谱系**
     │      两种不平衡（前景-背景 vs 类别间）要分开 /
     │      重采样（repeat factor sampling）· 重加权（Focal / CB Loss / LDAM）·
     │      **EQL / EQLv2**（检测特有：稀有类被负梯度淹没）·
     │      **logit adjustment**（零训练成本）· **解耦训练**（表示与分类器分开）
     ▼      「不加一张数据，先把现有数据榨干」
  模块 02  难例挖掘：OHEM、难负样本与难例的类型学
     │      OHEM 的实现细节 / Focal Loss 是软性 OHEM /
     │      难例的四种类型 / **挖掘过头会把噪声标签当难例**
     ▼      「在已有数据里找出该重点学的那一小撮」
  模块 03  主动学习与线上触发策略
     │      不确定性 / 一致性 / 规则触发 · 框级→图级聚合 ·
     │      影子模式 · **触发器的 PR 分析与带宽预算**
     ▼      「决定车队回传什么」
  模块 04  大规模挖掘基础设施
     │      嵌入检索（ANN）· 场景打标（规则 + **VLM**）·
     │      去重与多样性（感知哈希 / core-set）· 标注预算分配 · 数据血缘
     ▼      「把回传变成待标注清单」
  模块 05  闭环验证：证明数据真的有用
            分场景切片评测 · 回归门禁 · 边际收益曲线 ·
            灾难性遗忘与数据配比 · **把闭环做成流水线**

  贯穿全课的三个数：**触发率**（带宽约束）、**命中率**（挖掘质量）、**cycle time**（闭环速度）。"""),
        P("与其他课的关系："),
        UL([
            "<strong>C55（TSR 与自动驾驶感知）</strong>——本课的问题来源。C55 m03 的失效模式全景就是本课触发器要抓的东西；C55 m05 的安全导向评测是本课 m05 门禁的指标层。",
            "<strong>C56（检测数据增强）</strong>——本课的「另一半解法」。m01 讲的重采样只是把同一批样本看更多遍，而 <em>copy-paste 是真正在增加稀有类的实例数与背景多样性</em>，两者应该合起来用。",
            "<strong>C57（小目标检测）</strong>——与长尾高度纠缠。稀有类往往<em>同时也是小目标</em>（稀有 → 采集机会少 → 只在远处拍到过几次），两个问题叠加，误差分析时必须双向分桶才能看清。",
            "<strong>C40（研究方法论）/ C52（工业研究实务）</strong>——m05 的显著性检验、多重比较校正、实验记录规范在那两门课里有更完整的统计基础。",
        ]),
        CALLOUT("intuition", "本课的贯穿式练习是：<strong>把每一个模块的产物都写成一个「可以塞进流水线的函数」</strong>——触发器是 <code>should_upload(frame) -> bool</code>，挖掘器是 <code>rank(candidates) -> list</code>，门禁是 <code>gate(before, after) -> verdict</code>。<em>到 m05 结束时，你会把这些函数拼成一个完整闭环的状态机。</em>能在面试里画出这个状态机并说清每一步的门禁条件，就已经超过绝大多数候选人了。"),
    ])),

    ("env", "环境与运行方式", "".join([
        P("本课<strong>不需要 GPU、不需要 torch、不需要联网</strong>。所有 notebook 都是纯 numpy + 标准库，在笔记本 CPU 上每个 notebook 都能在 1–3 分钟内跑完。"),
        CODE("""# 依赖（三个就够）
python3 -m pip install numpy matplotlib jupyterlab

# 启动
cd C58_HardCase_LongTail_Course
jupyter lab

# 快速自检（应当全部打印 ✅）
python3 -c "import numpy, sys; print(sys.version.split()[0], numpy.__version__)\"""", "bash"),
        TABLE(["为什么不用真实数据集 / 真实框架", "本课的做法"], [
            ["TT100K / LVIS 下载动辄几十 GB，且大部分时间花在解压和跑 baseline 上", "<strong>用 <code>np.random</code> 按幂律合成类别分布</strong>，并把合成规则写清楚——你能改参数看规律怎么变，这比跑通一次别人的配置学到的多"],
            ["跑一次真实的长尾检测实验要几十 GPU 小时，无法在课上迭代", "把要讲的<strong>机制</strong>（负梯度淹没、重采样的过拟合、分类器权重范数失衡）在几百维的合成任务上复现，秒级出结果"],
            ["真实框架（mmdet）的实现细节会淹没原理", "<strong>公式从零手写</strong>：repeat factor、有效样本数、logit adjustment、EQLv2 的梯度统计——写一遍就再也不会记错"],
        ]),
        P("每个 notebook 的固定结构：<code>worked 小节（含 <strong>assert</strong> 自校验）→ ✏️ 练习（TODO 骨架 + 判分 cell）→ 📖 参考答案 → 🧪 真实工程胶囊（可原样复制到项目里的配置/命令）→ 小结</code>。<strong>练习的 assert 是真的会失败的</strong>，不要跳过。"),
        CALLOUT("warn", "一个使用建议：<strong>先把 notebook 里的数字改一改再看结论</strong>。比如把幂律指数 α 从 1.9 改成 1.2（更平的分布），你会发现本课半数方法的收益都大幅缩水——<em>这恰恰说明这些方法的适用边界是「分布有多歪」</em>。能说出方法的适用边界，比能背出方法名重要一个数量级。"),
    ])),

    ("frontier", "研究前沿与开放问题", "".join([
        P("这门课讲的是一套已经在量产系统里跑通的工程方法学，但它的每一环都还有真正的开放问题。"),
        UL([
            "<strong>数据价值的事前可预测性。</strong>目前判断一批数据有没有用，唯一可靠的办法是「标了、训了、测了」——一个完整的 cycle。<em>能不能在标注之前就估出一张图的边际价值？</em>influence function、data Shapley、TracIn 这条线在小模型小数据上可行，但在检测这种「一张图含多个实例、损失是结构化的」的任务上，扩展性与稳定性都还没解决。这是本领域最值钱的开放问题。",
            "<strong>触发器的选择偏差。</strong>不确定性触发只能回传「模型知道自己不确定」的样本，而<strong>最危险的失效恰恰是「模型自信地错了」</strong>（高分假正例：把广告牌当限速牌）。这类样本在不确定性度量上看起来完全正常。多模型分歧与多帧一致性能覆盖一部分，但系统性的解法尚不存在。",
            "<strong>合成数据能替代多少真实长尾。</strong>扩散模型生成稀有类样本、copy-paste 合成、仿真渲染——三条路都能提升尾部指标，但都存在域差，且<em>「合成数据涨的点在真实路测上兑现多少」缺少可信的度量</em>。目前的共识是合成能救「实例数不足」，救不了「场景多样性不足」。",
            "<strong>闭环的评测污染。</strong>挖掘出来的难例既进了训练集也可能进了测试集；触发器本身依赖当前模型，于是评测集会逐渐向「当前模型的弱点」倾斜。<em>几轮闭环之后，你的验证集还能代表真实路况分布吗？</em>这个问题在工业界普遍存在但很少被公开讨论。",
            "<strong>长尾方法与大规模预训练的交互。</strong>有证据表明，足够强的预训练表示会让很多长尾专用方法的增益大幅缩水（因为尾部类的表示本来就够好了，问题只在分类器）。<em>如果这个结论成立，那么长尾研究的重心应当从「怎么学表示」彻底移到「怎么校准分类器与先验」</em>——这正是 m01 里 logit adjustment 与解耦训练那条线的理论意义。",
            "<strong>开放词表检测（open-vocabulary detection）</strong>把长尾推向极端：稀有类干脆不在训练集里，用 CLIP/VLM 的文本嵌入做零样本识别。对 TSR 这种「类别体系随法规变化、新标志会不断出现」的任务，它的吸引力显而易见，但当前的零样本精度距离量产安全要求还有明显差距。",
        ]),
        CALLOUT("paper", "本模块必读（长尾与数据闭环的地基，★ 为优先）：★ <em>LVIS: A Dataset for Large Vocabulary Instance Segmentation</em>（Gupta et al., CVPR 2019）——repeat factor sampling 的原始出处，也是长尾检测评测的事实标准；★ <em>Deep Long-Tailed Learning: A Survey</em>（Zhang et al., TPAMI 2023）——方法谱系的最好地图，m01 的骨架来自它；★ <em>Deep Learning Scaling is Predictable, Empirically</em>（Hestness et al., 2017）与 <em>Revisiting Unreasonable Effectiveness of Data in Deep Learning Era</em>（Sun et al., ICCV 2017）——数据量-精度幂律的两篇奠基工作，本节边际收益公式的来源；<em>Pervasive Label Errors in Test Sets Destabilize ML Benchmarks</em>（Northcutt et al., NeurIPS 2021）——标注噪声危害的量化，对应失效 ③；<em>Active Learning Literature Survey</em>（Settles, 2009）——触发策略的经典总结，m03 的前置；<em>Active Learning for Convolutional Neural Networks: A Core-Set Approach</em>（Sener &amp; Savarese, ICLR 2018）——多样性采样，m04 的前置。相邻课程：C55（TSR 感知）、C56（数据增强）、C57（小目标）、C43（数据工程）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（幂律长尾 / 边际收益 / 加数据的四种失效 / 闭环预算）

目标：用纯 numpy 把本课的**三个底层事实**算出来，而不是背下来——
**① 类别分布是幂律的；② 边际收益按 n^-(β+1) 衰减；③「加数据」有四种可归类的失效方式。**

本 notebook 你会亲手实现：
1. **幂律（Zipf）类别分布的生成与拟合**——在 log-log 上做线性回归反解指数 α
2. **LVIS 口径的 rare / common / frequent 分桶**，并算出「尾部类占一半类别、却只占 3% 实例」这笔账
3. **边际收益曲线**与「随机加数据 vs 定向加数据」的收益倍数
4. 失效 ①②：**已经会的样本梯度贡献≈0**、**加错切片**
5. 失效 ③④：**漏标 = 负监督**（会让 recall 掉到比不加还低）、**整体指标掩盖切片涨跌**
6. **闭环预算的账**：触发率 × 命中率 × 去重保留率 × 标注单价 → cycle time
7. 环境自检

> 心智模型：**架构决定天花板有多高，闭环决定你多快撞到它、以及它会不会继续往上长。**"""),

    md("""## 1 · 幂律长尾的生成与 Zipf 拟合

交通标志的类别分布不是「有点不均衡」，它是幂律：按频次排序后 `n_r = n_1 · r^(-α)`。
取对数是一条直线——**这条直线可以在你自己的数据集上画出来，而且非常稳**。"""),

    code(r"""import numpy as np, math, json, sys, platform, time
rng = np.random.default_rng(58)
np.set_printoptions(precision=4, suppress=True)

# ── 合成一个 TSR 风格的类别分布 ──────────────────────────────────
# 合成规则（写清楚，便于你改参数看规律）：
#   · C 个类别，按频次降序排列，排名 r 的类实例数 n_r = N_TOP * r^(-ALPHA)
#   · 下限 FLOOR：再稀有的类在数据集里也至少留下几个实例（否则它根本不在类别表里）
C, ALPHA, N_TOP, FLOOR = 120, 1.9, 80000, 5
ranks = np.arange(1, C + 1)
counts = np.maximum(np.round(N_TOP * ranks ** (-ALPHA)), FLOOR).astype(int)

print(f'类别数 C = {C}   幂律指数 α = {ALPHA}   头部类实例数 = {counts[0]:,}')
print(f'实例总数         = {counts.sum():,}')
print(f'最稀有类实例数   = {counts[-1]}     头/尾比 = {counts[0] / counts[-1]:,.0f} : 1')
print()
print('排名     1     2     3     5    10    20    40    80   120')
idx = np.array([1, 2, 3, 5, 10, 20, 40, 80, 120]) - 1
print('实例  ' + ' '.join(f'{counts[i]:>5d}' for i in idx))

# ── 在 log-log 上做最小二乘，反解 α ─────────────────────────────
def fit_zipf(cnts):
    '''log n_r = log n_1 - α log r  →  对 (log r, log n) 做一次线性回归。
       返回 (alpha_hat, r2)。'''
    r = np.arange(1, len(cnts) + 1)
    x, y = np.log(r), np.log(cnts)
    A = np.stack([x, np.ones_like(x)], axis=1)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = coef
    pred = A @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return -slope, 1.0 - ss_res / ss_tot

alpha_hat, r2 = fit_zipf(counts)
print(f'\n拟合结果: α_hat = {alpha_hat:.3f}  (真值 {ALPHA})   R² = {r2:.4f}')
assert abs(alpha_hat - ALPHA) < 0.25, f'反解的 α 偏差过大: {alpha_hat}'
assert r2 > 0.97, f'幂律拟合应当非常好, R²={r2}'
print('✅ 幂律在 log-log 上就是一条直线 —— R² > 0.97 说明它不是"有点不均衡", 而是结构性的。')""") ,

    md("""## 2 · LVIS 口径分桶：尾部占一半类别，却只占 3% 实例

LVIS 的划分标准用的是**包含该类的图像数**（不是实例数）：
`rare < 10 张图`、`common 10–100 张`、`frequent > 100 张`。
这个口径很重要——**m01 的 repeat factor sampling 公式里的 f_c 就是图像频率**。"""),

    code(r"""# 假设：含类别 c 的图像里，平均出现 1.4 个该类实例（同一张图常有成对的标志牌）
INST_PER_IMG = 1.4
img_counts = np.ceil(counts / INST_PER_IMG).astype(int)
N_IMAGES = 100_000                     # 数据集总图像数（用于算图像频率 f_c）
img_freq = img_counts / N_IMAGES       # f_c = 含该类的图像数 / 总图像数

def bucketize(img_cnt):
    '''LVIS 口径: rare < 10 imgs, common 10-100, frequent > 100'''
    return np.where(img_cnt < 10, 'rare', np.where(img_cnt <= 100, 'common', 'frequent'))

bucket = bucketize(img_counts)
print(f"{'桶':<10s}{'类别数':>7s}{'类别占比':>10s}{'实例数':>10s}{'实例占比':>10s}")
stat = {}
for b in ['frequent', 'common', 'rare']:
    m = bucket == b
    stat[b] = dict(n_cls=int(m.sum()), n_inst=int(counts[m].sum()),
                   cls_share=float(m.mean()), inst_share=float(counts[m].sum() / counts.sum()))
    s = stat[b]
    print(f"{b:<10s}{s['n_cls']:>7d}{s['cls_share']:>9.1%}{s['n_inst']:>10,d}{s['inst_share']:>9.2%}")

tail_cls_share = stat['rare']['cls_share'] + stat['common']['cls_share']
tail_inst_share = stat['rare']['inst_share'] + stat['common']['inst_share']
print(f'\nrare + common 合计: 占类别数 {tail_cls_share:.1%}, 占实例数 {tail_inst_share:.2%}')
assert stat['rare']['n_cls'] > 0, '这个分布应当产生一批 rare 类'
assert stat['rare']['inst_share'] < 0.01, 'rare 桶的实例占比应当低于 1%'
assert tail_cls_share > 0.4, '尾部类别应当占类别数的一大半'

# 为什么 macro 与 micro 会给出相反的结论
ap = np.clip(0.93 - 0.45 * np.exp(-counts / 900.0) - 0.42 * np.exp(-counts / 40.0), 0.02, 0.95)
macro = ap.mean()
micro = float((ap * counts).sum() / counts.sum())
print(f'\n同一组逐类 AP:  macro(每类平均) = {macro:.3f}   micro(按实例加权) = {micro:.3f}')
assert micro - macro > 0.15, 'micro 应当被头部类拉得明显更高'
print('⚠️  差 %.3f。**汇报 micro、被质问 macro** 是长尾任务最常见的翻车方式。' % (micro - macro))
print('✅ 长尾任务必须同时报 macro / micro, 并给出 rare/common/frequent 三桶的分项。')""") ,

    md("""## 3 · 边际收益曲线：随机加数据 vs 定向加数据

单个场景切片的 AP 随该切片样本数近似满足饱和幂律
`AP(n) = A_max / (1 + (k/n)^β)`，于是 `dAP/dn ∝ n^-(β+1)`。
**两张标注的边际价值可以差三个数量级** —— 下面把这个倍数算出来。"""),

    code(r"""A_MAX, K, BETA = 0.92, 200.0, 0.6        # 上限 / 半饱和样本数 / 陡峭度

def ap_of(n):
    n = np.maximum(np.asarray(n, dtype=float), 1e-9)
    return A_MAX / (1.0 + (K / n) ** BETA)

# 8 个场景切片（TSR 真实会用的划分：天气 × 光照 × 道路）
SLICES = ['城市白天晴', '高速白天晴', '城市夜间', '高速夜间',
          '雨天', '隧道出入口逆光', '雪天', '施工临时标志']
n_now = np.array([50000, 20000, 8000, 3000, 900, 300, 80, 25], dtype=float)

print(f"{'切片':<16s}{'现有样本':>9s}{'当前AP':>8s}{'每+100张的收益':>15s}")
for s, n in zip(SLICES, n_now):
    d = ap_of(n + 100) - ap_of(n)
    print(f'{s:<16s}{int(n):>9,d}{ap_of(n):>8.3f}{d:>15.4f}')

BUDGET = 5000                              # 这一轮能标 5000 张

# ── 策略 A: 随机加数据（按自然分布，正比于现有样本数）──
alloc_rand = BUDGET * n_now / n_now.sum()
# ── 策略 B: 定向加数据（贪心：每 50 张给当前边际收益最大的切片）──
alloc_tgt, step = np.zeros_like(n_now), 50
for _ in range(BUDGET // step):
    cur = n_now + alloc_tgt
    gain = ap_of(cur + step) - ap_of(cur)
    alloc_tgt[int(np.argmax(gain))] += step

macro0 = ap_of(n_now).mean()
macro_r = ap_of(n_now + alloc_rand).mean()
macro_t = ap_of(n_now + alloc_tgt).mean()
print(f'\n{"切片":<16s}{"随机分配":>10s}{"定向分配":>10s}')
for s, a, b in zip(SLICES, alloc_rand, alloc_tgt):
    print(f'{s:<16s}{a:>10.0f}{b:>10.0f}')
print(f'\nmacro AP:  基线 {macro0:.4f}  →  随机 {macro_r:.4f} (+{macro_r-macro0:.4f})'
      f'  |  定向 {macro_t:.4f} (+{macro_t-macro0:.4f})')
ratio = (macro_t - macro0) / (macro_r - macro0)
print(f'**同样 5000 张标注, 定向的收益是随机的 {ratio:.1f} 倍**')
assert macro_t > macro_r, '定向分配必须优于随机分配'
assert ratio > 5, f'倍数应当很悬殊, 实际 {ratio:.1f}'
print('\n✅ 这就是"10 张精准数据 > 10000 张随机路采"的定量版本。')
print('   随机加数据把 %.0f%% 的预算花在了已经饱和的头两个切片上。'
      % (100 * alloc_rand[:2].sum() / BUDGET))""") ,

    md("""## 4 · 失效 ① 加的是已经会的 ／ 失效 ② 加的分布不对

**① 的机制**：交叉熵的梯度幅值正比于 loss。模型 loss≈0 的样本，反传梯度也≈0，
它们占用了标注预算、磁盘和训练时间，却**不携带任何新信息**。
**② 的机制**：新数据落在已经饱和的切片上（第 3 节已经算过它有多亏）。"""),

    code(r"""# ── 失效 ①: 用「有效样本数」量化"加的是已经会的" ──────────────
N_POOL = 100_000
is_hard = rng.random(N_POOL) < 0.04                    # 只有 4% 是模型真的不会的
losses = np.where(is_hard,
                  rng.exponential(1.2, N_POOL),        # 难样本: 均值 1.2
                  rng.exponential(0.02, N_POOL))       # 已经会的: 均值 0.02

REF = 1.2                                              # 参考: 一个典型难样本的 loss
def effective_n(ls):
    '''有效样本数 = 总 loss / 一个典型难样本的 loss（梯度幅值 ∝ loss）'''
    return float(ls.sum() / REF)

pick_rand = rng.choice(N_POOL, 10_000, replace=False)  # 随机采 1 万张
order = np.argsort(-losses)
pick_top = order[:1_000]                               # 按 loss 挑最难的 1 千张

for name, pick in [('随机采样 10,000 张', pick_rand), ('按 loss 定向挑 1,000 张', pick_top)]:
    ls = losses[pick]
    print(f'{name:<26s} 张数 {len(pick):>6,d}  难样本占比 {is_hard[pick].mean():>6.1%}'
          f'  总loss {ls.sum():>8.1f}  **有效样本数 {effective_n(ls):>7.0f}**')

eff_rand, eff_top = effective_n(losses[pick_rand]), effective_n(losses[pick_top])
print(f'\n定向 1,000 张的有效样本数 = {eff_top:.0f}, 随机 10,000 张 = {eff_rand:.0f}'
      f'  →  **每张标注的价值差 {(eff_top/1000)/(eff_rand/10000):.0f} 倍**')
assert eff_top / 1_000 > 5 * eff_rand / 10_000, '定向挑选的单张价值应当高一个量级'
print('✅ "加了 10 万张、指标纹丝不动" 的机制: 95% 的新数据梯度贡献接近 0。')

# ── 失效 ②: 加到错误的切片上 ────────────────────────────────────
target = SLICES.index('隧道出入口逆光')
wrong  = SLICES.index('城市白天晴')
n_a, n_b = n_now.copy(), n_now.copy()
n_a[wrong] += 5000                                     # 全加到已饱和的切片
n_b[target] += 5000                                    # 全加到目标切片
print(f'\n{"":<28s}{"目标切片 AP":>12s}{"macro AP":>10s}')
print(f'{"基线":<28s}{ap_of(n_now[target]):>12.4f}{ap_of(n_now).mean():>10.4f}')
print(f'{"+5000 张(城市白天晴)":<28s}{ap_of(n_a[target]):>12.4f}{ap_of(n_a).mean():>10.4f}')
print(f'{"+5000 张(隧道逆光)":<28s}{ap_of(n_b[target]):>12.4f}{ap_of(n_b).mean():>10.4f}')
assert abs(ap_of(n_a[target]) - ap_of(n_now[target])) < 1e-9, '加错切片, 目标切片纹丝不动'
assert ap_of(n_b[target]) - ap_of(n_now[target]) > 0.25, '加对切片应当大涨'
print('⚠️  加错切片时, 目标切片 AP **完全没动**, 而整体 macro 涨了一点点 —— ')
print('    这正是"整体涨 0.2 但问题没解决"的来源。')""") ,

    md("""## 5 · 失效 ③ 标注有噪 ／ 失效 ④ 加完没验证

**③ 是四类里唯一方向为负的**：在检测里，一个没被标注的真实目标不是「缺失」，
它所在的位置会被标签分配判成背景，产生一条明确的负梯度——
模型学到的是「确定没有」，不是「不确定」。

下面用一个 4 维逻辑回归复现它：**漏标率超过某个点，加数据会让召回比不加还低。**"""),

    code(r"""# ── 失效 ③: 漏标 = 负监督 ──────────────────────────────────────
D_FEAT = 4
mu_pos = np.array([1.15, -0.85, 0.65, 0.45])          # 正样本(真有标志)的特征均值

def make_data(n, miss_rate, gen):
    '''一半正一半负；miss_rate 比例的正样本被**漏标**成负样本。'''
    n_pos = n // 2
    Xp = mu_pos + gen.normal(size=(n_pos, D_FEAT))
    Xn = gen.normal(size=(n - n_pos, D_FEAT))
    X = np.vstack([Xp, Xn])
    y = np.concatenate([np.ones(n_pos), np.zeros(n - n_pos)])
    miss = (gen.random(n) < miss_rate) & (y == 1)      # 漏标: 正样本被标成 0
    return X, np.where(miss, 0.0, y)

def train_logreg(X, y, steps=600, lr=0.35):
    w, b = np.zeros(D_FEAT), 0.0
    for _ in range(steps):
        p = 1.0 / (1.0 + np.exp(-(X @ w + b)))
        g = p - y
        w -= lr * (X.T @ g) / len(X)
        b -= lr * g.mean()
    return w, b

def recall_at(w, b, Xt, yt, thr=0.5):
    p = 1.0 / (1.0 + np.exp(-(Xt @ w + b)))
    pos = yt == 1
    return float(((p >= thr) & pos).sum() / pos.sum())

Xte, yte = make_data(20_000, 0.0, np.random.default_rng(7))          # 干净测试集
X0, y0 = make_data(200, 0.0, np.random.default_rng(11))              # 干净基线训练集
w0, b0 = train_logreg(X0, y0)
base_rec = recall_at(w0, b0, Xte, yte)
print(f'基线(200 张干净数据) 的 recall@0.5 = {base_rec:.3f}\n')

print(f"{'新增 3000 张的漏标率':>20s}{'recall@0.5':>12s}{'相对基线':>10s}")
rows = []
for m in [0.0, 0.10, 0.20, 0.30, 0.45, 0.60]:
    X1, y1 = make_data(3000, m, np.random.default_rng(100 + int(m * 100)))
    w, b = train_logreg(np.vstack([X0, X1]), np.concatenate([y0, y1]))
    r = recall_at(w, b, Xte, yte)
    rows.append((m, r))
    flag = '  ← 比不加还差' if r < base_rec else ''
    print(f'{m:>19.0%}{r:>12.3f}{r - base_rec:>+10.3f}{flag}')

rec = dict(rows)
cross = min([m for m, r in rows if r < base_rec], default=None)
print(f'\n**临界漏标率 ≈ {cross:.0%}** —— 超过它, 加 3000 张新数据反而不如不加。')
assert rec[0.0] > base_rec, '干净数据加进去应当有正收益'
assert rec[0.60] < base_rec, '高漏标率下, 加数据必须比不加更差'
assert rec[0.0] > rec[0.60] + 0.3, '漏标的危害应当非常显著'
assert cross is not None and cross <= 0.2, '临界漏标率不应太高（真实标注很容易触到）'
print('⚠️  在 TSR 里最容易漏标的恰恰是**最远、最小**的那批标志（20×20 像素以下），')
print('    于是漏标噪声与"远距离早检出"这个核心指标精确地打在同一个位置上。')
print('✅ 所以新数据进训练集之前必须抽检: IoU + 类别 agreement, 200 张就能看出问题。')""") ,

    code(r"""# ── 失效 ④: 整体指标掩盖切片涨跌 ───────────────────────────────
before = {'城市白天晴': 0.884, '高速白天晴': 0.861, '城市夜间': 0.702,
          '高速夜间': 0.615, '雨天': 0.548, '隧道出入口逆光': 0.401,
          '雪天': 0.312, '施工临时标志': 0.205}
after  = {'城市白天晴': 0.889, '高速白天晴': 0.866, '城市夜间': 0.681,
          '高速夜间': 0.583, '雨天': 0.612, '隧道出入口逆光': 0.436,
          '雪天': 0.318, '施工临时标志': 0.207}
weights = dict(zip(SLICES, n_now))                   # 用样本数作为 micro 权重

def slice_report(bef, aft, w, seed_std=0.004):
    '''seed_std: 同配置换随机种子的典型波动（检测任务 0.2~0.5 个点）'''
    rs = []
    for k in bef:
        d = aft[k] - bef[k]
        rs.append((k, bef[k], aft[k], d, abs(d) > 2 * seed_std))
    tot = sum(w.values())
    micro_b = sum(bef[k] * w[k] for k in bef) / tot
    micro_a = sum(aft[k] * w[k] for k in aft) / tot
    macro_b = sum(bef.values()) / len(bef)
    macro_a = sum(aft.values()) / len(aft)
    return rs, (micro_b, micro_a), (macro_b, macro_a)

rows, (mib, mia), (mab, maa) = slice_report(before, after, weights)
print(f"{'切片':<16s}{'before':>8s}{'after':>8s}{'Δ':>9s}  显著?")
for k, b, a, d, sig in rows:
    print(f'{k:<16s}{b:>8.3f}{a:>8.3f}{d:>+9.3f}  {"✅" if sig else "· 噪声内"}'
          + ('   ← **回归**' if d < -0.01 else ''))
print(f'\n整体(micro, 按样本量加权): {mib:.4f} → {mia:.4f}  ({mia-mib:+.4f})')
print(f'整体(macro, 每切片平均)  : {mab:.4f} → {maa:.4f}  ({maa-mab:+.4f})')
regressed = [k for k, b, a, d, s in rows if d < -0.01]
print(f'**回归的切片: {regressed}**')
assert mia - mib > 0, 'micro 看起来是涨的'
assert len(regressed) >= 2, '应当有切片明显回归'
assert min(d for _, _, _, d, _ in rows) < -0.02, '存在 2 个点以上的回归'
print('\n⚠️  只看 micro: "+0.4%, 发布!"。看切片: **夜间掉了 2~3 个点** —— 夜间正是安全关键场景。')
print('✅ 回归门禁的正确形式: 任何切片回归超过 2×种子标准差 → 直接打回, 不看整体。')""") ,

    md("""## 6 · 闭环预算的账：触发率 × 命中率 × 去重 × 单价 → cycle time

闭环是一条有硬约束的流水线：**回传带宽有限、标注预算有限、发布节奏有限**。
把这三条约束写成一个可求解的账，你就能反推「触发阈值该设多少」。"""),

    code(r"""LOOP = dict(
    fleet=20_000,          # 车队规模（辆）
    hours_per_day=1.2,     # 每辆车日均行驶小时
    fps_sampled=2.0,       # 感知回传候选的采样帧率（不是相机帧率）
    trigger_rate=3e-5,     # 触发率（触发器阈值决定）
    hit_rate=0.35,         # 触发中"确实是难例"的比例（触发器精度）
    dedup_keep=0.22,       # 去重 + 多样性采样后的保留率
    price_per_frame=2.6,   # 标注单价（元/帧，含框 + 类别 + 质检）
    budget_per_day=9000.0, # 日均标注预算（元）
)

def loop_budget(cfg):
    frames = cfg['fleet'] * cfg['hours_per_day'] * 3600 * cfg['fps_sampled']
    triggered = frames * cfg['trigger_rate']
    useful = triggered * cfg['hit_rate']
    after_dedup = useful * cfg['dedup_keep']
    affordable = cfg['budget_per_day'] / cfg['price_per_frame']
    labeled = min(after_dedup, affordable)
    return dict(frames=frames, triggered=triggered, useful=useful,
                after_dedup=after_dedup, affordable=affordable, labeled=labeled,
                bottleneck=('标注预算' if affordable < after_dedup else '挖掘产出'))

r = loop_budget(LOOP)
print(f"{'候选帧/天':<16s}{r['frames']:>14,.0f}")
print(f"{'触发回传/天':<16s}{r['triggered']:>14,.0f}   (触发率 {LOOP['trigger_rate']:.0e})")
print(f"{'其中真难例':<16s}{r['useful']:>14,.0f}   (命中率 {LOOP['hit_rate']:.0%})")
print(f"{'去重后':<16s}{r['after_dedup']:>14,.0f}   (保留 {LOOP['dedup_keep']:.0%})")
print(f"{'预算能标':<16s}{r['affordable']:>14,.0f}   ({LOOP['budget_per_day']:,.0f} 元 / "
      f"{LOOP['price_per_frame']} 元每帧)")
print(f"{'实际标注/天':<16s}{r['labeled']:>14,.0f}   ← **瓶颈: {r['bottleneck']}**")
assert r['labeled'] == min(r['after_dedup'], r['affordable'])
assert r['bottleneck'] in ('标注预算', '挖掘产出')

# 反推: 想每天正好标满预算, 触发率该设多少？
def solve_trigger_rate(cfg):
    frames = cfg['fleet'] * cfg['hours_per_day'] * 3600 * cfg['fps_sampled']
    need = cfg['budget_per_day'] / cfg['price_per_frame']
    return need / (frames * cfg['hit_rate'] * cfg['dedup_keep'])

t_star = solve_trigger_rate(LOOP)
print(f'\n**恰好用满预算的触发率 = {t_star:.2e}**（当前 {LOOP["trigger_rate"]:.0e}）')
chk = dict(LOOP); chk['trigger_rate'] = t_star
assert abs(loop_budget(chk)['after_dedup'] - loop_budget(chk)['affordable']) < 1e-6
print('✅ 触发率不是拍脑袋的超参, 它由"标注预算 ÷ (车队规模 × 命中率 × 去重保留率)"反解出来。')

# cycle time: 从发现 badcase 到修复上车
STAGES = [('触发命中', 1.0), ('回传落库', 1.0), ('挖掘去重', 0.5), ('标注+质检', 5.0),
          ('训练', 2.0), ('切片评测+门禁', 1.5), ('灰度发布', 3.0)]
cycle = sum(d for _, d in STAGES)
print(f'\n{"闭环阶段":<14s}{"天":>6s}')
for s, d in STAGES:
    print(f'{s:<14s}{d:>6.1f}')
print(f'{"合计 cycle time":<14s}{cycle:>6.1f} 天  →  一年约 {365/cycle:.0f} 轮')
assert abs(cycle - 14.0) < 1e-6
print('⚠️  **标注(5天) + 灰度(3天) 占了 57%** —— 想压 cycle time, 先动这两块, 别去优化训练速度。')""") ,

    md("""## 7 · 环境自检"""),

    code(r"""t0 = time.time()
print('Python  :', sys.version.split()[0])
print('平台    :', platform.platform())
print('numpy   :', np.__version__)
_a = rng.normal(size=(600, 600))
_ = _a @ _a.T
print(f'600×600 矩阵乘  {time.time()-t0:.3f}s   ← 本课全部 notebook 都是这个量级')
assert sys.version_info >= (3, 8), '需要 Python 3.8+'
assert int(np.__version__.split('.')[0]) >= 1
print('\n✅ 本课不需要 GPU / torch / mmdet / 联网。三个依赖: numpy, matplotlib, jupyterlab。')""") ,

    md("""## ✏️ 练习 1：Zipf 拟合器（带截断处理）

实现 `fit_zipf_robust(counts, min_count=1)`：只用 `counts > min_count` 的那些点做 log-log 回归
（**下限截断的类会把斜率拉平**，必须排除），返回 `(alpha, r2, n_used)`。
`alpha` 取回归斜率的相反数；`r2` 只在用到的点上计算。"""),

    code(r"""def fit_zipf_robust(counts, min_count=1):
    # TODO: ① 用 rank = 1..len(counts)（**注意 rank 是原始排名, 不能重新编号**）
    #       ② 只保留 counts > min_count 的点
    #       ③ 在这些点上对 (log rank, log count) 做最小二乘, 返回 (alpha, r2, n_used)
    raise NotImplementedError"""),

    code(r"""# —— 练习 1 自测 ——
pure = np.round(50000 * np.arange(1, 61) ** (-1.7))          # 无截断的纯幂律
a, r2_, k = fit_zipf_robust(pure, min_count=0)
assert abs(a - 1.7) < 0.05, f'纯幂律应精确反解, 得到 {a}'
assert r2_ > 0.999 and k == 60

clipped = np.maximum(np.round(50000 * np.arange(1, 121) ** (-1.7)), 20)   # 后段被下限截平
a_bad, _, _ = fit_zipf_robust(clipped, min_count=0)          # 不排除截断点
a_good, _, k_good = fit_zipf_robust(clipped, min_count=20)   # 排除截断点
print(f'含截断点一起拟合: α = {a_bad:.3f}   (被拉平)')
print(f'排除截断点后    : α = {a_good:.3f}   使用 {k_good} 个点  (接近真值 1.7)')
assert a_bad < a_good, '截断点会把斜率拉平'
assert abs(a_good - 1.7) < 0.08, f'排除截断后应接近真值, 得到 {a_good}'
print('✅ 练习 1 通过：**数据集的下限截断会系统性低估 α** —— 拟合前必须先排除。')"""),

    md("""## ✏️ 练习 2：标注预算的最优分配

实现 `allocate(n_now, budget, step=50)`：用贪心逐块分配（每次把 `step` 张给
**当前边际收益最大**的切片），返回长度与 `n_now` 相同的分配数组。
用第 3 节的 `ap_of` 作为收益函数。要求分配总量恰好等于 `budget`
（假定 `budget` 是 `step` 的整数倍）。"""),

    code(r"""def allocate(n_now, budget, step=50):
    # TODO: 贪心：重复 budget//step 次，每次给 (ap_of(n+step) - ap_of(n)) 最大的切片加 step
    raise NotImplementedError"""),

    code(r"""# —— 练习 2 自测 ——
alloc = allocate(n_now, 5000, step=50)
assert alloc.shape == n_now.shape and abs(alloc.sum() - 5000) < 1e-9, alloc.sum()
assert (alloc >= 0).all()
gain_alloc = ap_of(n_now + alloc).mean() - ap_of(n_now).mean()
gain_rand = ap_of(n_now + 5000 * n_now / n_now.sum()).mean() - ap_of(n_now).mean()
assert gain_alloc > gain_rand, '贪心必须优于按现状比例分配'
assert alloc[0] < alloc[-1], '样本最少的切片应当拿到更多预算'
uniform = np.full_like(n_now, 5000 / len(n_now))
assert gain_alloc >= ap_of(n_now + uniform).mean() - ap_of(n_now).mean() - 1e-9, '贪心不应差于均分'
print(f"{'切片':<16s}{'现有':>9s}{'分配':>8s}{'AP前':>8s}{'AP后':>8s}")
for s, n, a in zip(SLICES, n_now, alloc):
    print(f'{s:<16s}{int(n):>9,d}{a:>8.0f}{ap_of(n):>8.3f}{ap_of(n+a):>8.3f}')
print(f'\nmacro 收益: 贪心 {gain_alloc:+.4f}  vs  按现状比例 {gain_rand:+.4f}'
      f'  ({gain_alloc/gain_rand:.1f}×)')
print('✅ 练习 2 通过：预算分配不是均分, 也不是按现状比例, 而是**按边际收益排序**。')"""),

    md("""## ✏️ 练习 3：回归门禁判定器

实现 `gate(before, after, seed_std=0.004, tol=0.0)`：
- 只要有任一切片 `after - before < -(2*seed_std + tol)`，判定 **BLOCK**（打回）
- 否则若存在切片提升超过 `2*seed_std`，判定 **PASS**
- 否则（全在噪声内）判定 **NO_SIGNAL**

返回 `{'verdict': ..., 'regressed': [切片名], 'improved': [切片名]}`，
两个列表按 |Δ| 从大到小排序。"""),

    code(r"""def gate(before, after, seed_std=0.004, tol=0.0):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 3 自测 ——
g = gate(before, after)
assert g['verdict'] == 'BLOCK', g
assert '高速夜间' in g['regressed'] and '城市夜间' in g['regressed']
assert g['regressed'][0] == '高速夜间', '应按 |Δ| 降序, 高速夜间掉得最多'
assert '雨天' in g['improved']

good = {k: v + 0.02 for k, v in before.items()}
assert gate(before, good)['verdict'] == 'PASS'
flat = {k: v + 0.001 for k, v in before.items()}
assert gate(before, flat)['verdict'] == 'NO_SIGNAL'
# 容差可以放行小回归
assert gate(before, after, tol=0.05)['verdict'] == 'PASS', '给足容差后不该再 BLOCK'
print(json.dumps(gate(before, after), ensure_ascii=False, indent=2))
print('✅ 练习 3 通过：**门禁的第一条永远是"旧场景不许掉"**, 而不是"整体要涨"。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code(r"""# 练习 1 参考答案
def fit_zipf_robust(counts, min_count=1):
    counts = np.asarray(counts, dtype=float)
    rank = np.arange(1, len(counts) + 1, dtype=float)      # 保持原始排名
    keep = counts > min_count
    x, y = np.log(rank[keep]), np.log(counts[keep])
    A = np.stack([x, np.ones_like(x)], axis=1)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return -float(coef[0]), r2, int(keep.sum())"""),

    code(r"""# 练习 2 参考答案
def allocate(n_now, budget, step=50):
    alloc = np.zeros_like(np.asarray(n_now, dtype=float))
    for _ in range(int(budget // step)):
        cur = np.asarray(n_now, dtype=float) + alloc
        gain = ap_of(cur + step) - ap_of(cur)
        alloc[int(np.argmax(gain))] += step
    return alloc"""),

    code(r"""# 练习 3 参考答案
def gate(before, after, seed_std=0.004, tol=0.0):
    thr = 2 * seed_std
    deltas = {k: after[k] - before[k] for k in before}
    regressed = sorted([k for k, d in deltas.items() if d < -(thr + tol)],
                       key=lambda k: deltas[k])
    improved = sorted([k for k, d in deltas.items() if d > thr],
                      key=lambda k: -deltas[k])
    if regressed:
        verdict = 'BLOCK'
    elif improved:
        verdict = 'PASS'
    else:
        verdict = 'NO_SIGNAL'
    return {'verdict': verdict, 'regressed': regressed, 'improved': improved}"""),

    md("""---
## 🧪 真实工程胶囊：一页纸的「加数据之前的检查单」"""),

    code(r"""RECIPE = r'''
# ========== 加数据之前必须回答的四个问题（对应四种失效）==========
# ① 模型现在会不会？ —— 用当前模型跑一遍候选池，看 loss / 熵分布
python tools/score_pool.py --ckpt work_dirs/base/latest.pth \
    --pool data/pool_20240817 --out pool_scores.jsonl
python - <<'PY'
import json, numpy as np
ls = np.array([json.loads(l)["loss"] for l in open("pool_scores.jsonl")])
print("有效样本数 =", ls.sum() / np.percentile(ls, 95))   # 远小于张数 -> 别标
PY

# ② 它落在哪个切片？ —— 新数据必须用与评测集**同一套**切片打标
python tools/tag_slices.py --in pool_scores.jsonl --schema configs/slices_tsr.yaml
# 期望输出: 目标切片(隧道逆光/夜间)占比 > 50%，否则重新调触发器

# ③ 标注质量抽检 —— 200 张双标，算 IoU + 类别 agreement
python tools/label_agreement.py --a annA.json --b annB.json --iou-thr 0.5
# 红线: box recall agreement < 0.92 或 小目标(<32px) agreement < 0.85 -> 打回重标
#      **漏标是负监督，比不标更糟**

# ④ 我要用什么切片、什么显著性判定它有用？（**在标注之前就写死**）
cat > exp/2024w34_tunnel.yaml <<'YAML'
hypothesis: "补 5000 张隧道出入口逆光样本, 该切片 AP50 提升 >= 3.0"
eval_slices: [tunnel_backlight, night_highway, rain, city_day]   # 目标 + 回归切片
gate:
  target_slice: tunnel_backlight
  min_gain: 0.030
  max_regression: 0.008          # 任一其他切片回归超过此值 -> BLOCK
  seeds: 3                       # 多种子, 用配对检验
YAML

# ========== 闭环预算反推触发阈值 ==========
# trigger_rate* = (日预算 / 单价) / (车队候选帧数 × 命中率 × 去重保留率)
# 触发率不是拍脑袋的超参 —— 它由标注预算反解出来。

# ========== cycle time 是闭环的第一指标 ==========
# 触发1 + 回传1 + 挖掘0.5 + **标注5** + 训练2 + 评测1.5 + **灰度3** = 14 天
# 想提速先动"标注"和"灰度"，别去优化训练速度。
'''
print(RECIPE)
for k in ['有效样本数', 'tag_slices', 'label_agreement', 'max_regression',
          'trigger_rate*', 'cycle time']:
    assert k in RECIPE, k
print('✅ 检查单覆盖四种失效 + 触发率反解 + cycle time —— 可原样贴进项目 wiki。')"""),

    md("""### 小结

- **护城河是数据闭环，不是模型架构**：架构可复制、收益一次性；闭环不可复制、收益复利。
  面试里「给你更多资源做什么」，答「换更大的 backbone」是初级回答。
- **闭环 = 触发 → 挖掘 → 验证**，三环节可以分别失败。第一指标是 **cycle time**
  （从发现 badcase 到修复上车），本例 14 天，其中标注 5 天 + 灰度 3 天占 57%。
- **「加数据」的四种失效**：① 加的是已经会的（梯度≈0，10 万张 ≈ 0 张）；
  ② 分布不对（目标切片纹丝不动）；③ **标注有噪**——漏标是负监督，方向为负，
  会让 recall 比不加还低；④ 加完没验证（micro 涨 0.4%，夜间掉 3 个点）。
- **长尾是幂律的**：α≈1.9 时，尾部占一半类别却只占 3% 实例；micro 与 macro 会给出相反结论。
- **边际收益按 n^-(β+1) 衰减**：同样 5000 张标注，定向分配的收益是随机的十几倍。
  预算分配要**按边际收益排序**，不是均分、也不是按现状比例。
- **触发率由预算反解**：`trigger_rate* = (预算/单价) / (候选帧数 × 命中率 × 去重保留率)`。

下一站：**模块 01 · 类别不平衡的处理谱系** —— 在不加一张数据的前提下，
先把现有数据榨干：重采样、重加权、EQL、logit adjustment、解耦训练。"""),
]
