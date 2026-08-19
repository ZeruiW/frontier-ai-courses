# -*- coding: utf-8 -*-
"""C63 模块 02 · 数据系统设计（ML 系统设计面试）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（七步框架）与模块 01（需求澄清与三层指标映射）；"
                 "不需要标注工具或数据库的实操经验，只需要理解「样本」「标签」「切分」这些概念"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_data_system_design.ipynb'
                       '（标注成本模型与预算分配 / 泄漏检测器——构造并检出四类泄漏 / '
                       '数据规模需求反推 / 分层抽样与代表性检验 / 存储与吞吐量级计算器 / 冷启动决策树）'),
    ("核心参考", "本课程 C43（数据工程实现细节，本课不重述）· C58（长尾与数据闭环的技术细节，本课只讲「面试里怎么组织这些结论」）· "
                 "C55 模块 01（TSR 数据集全景与标志分类体系，本课引用其结论）· "
                 "GDPR / 《个人信息保护法》对人脸车牌等生物特征与位置数据的合规要点纲要"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("sourcing", "数据从哪来：采集策略的成本-质量-合规画像", "".join([
        P("在 ML system design 面试里，「这批数据从哪来」几乎总是紧跟在需求澄清之后的第二个问题——"
          "<strong>比「用什么模型」更早</strong>。原因很直接：模型能拟合什么，上限由数据决定；"
          "而数据从哪来，直接决定了你能不能按时拿到、拿到的东西干不干净、会不会惹上合规麻烦。"
          "面试官在这一步真正想看的，是你能不能把「数据」拆成<strong>四条不同的采购渠道</strong>，"
          "并且对每一条渠道的代价说得出具体数字，而不是笼统地说「我们采集数据然后标注」。"),
        TABLE(["来源", "典型成本结构", "质量特征", "合规风险", "覆盖长尾的能力", "从决策到可用的前置时间"], [
            ["<strong>自采（车队 fleet）</strong>", "边际成本高：每公里/每小时都要付传感器+存储+车队运营的钱", "分布最贴近真实部署域，但长尾场景要主动触发才能采到", "<strong>最高</strong>：人脸车牌、GPS 轨迹全部要脱敏与留存合规", "强——可以<em>主动去有目标场景开车</em>", "数周到数月（还要等触发-挖掘-标注闭环跑一轮，见 C58）"],
            ["公开数据集", "近乎零边际成本，但授权范围可能限制商用", "标注规范、类别体系可能与自己的产品定义不一致（见 C55-01 的分类学差异）", "中：需要核实数据集许可证与是否含可识别个人信息", "弱——数据集的长尾结构是别人定的，不一定匹配你的 ODD", "立即可用"],
            ["合成数据", "生成引擎的一次性建设成本高，之后近乎零边际成本", "物理保真度是短板：光照/材质/传感器噪声的域差会传导到模型", "低——没有真实个人信息", "<strong>强——可以按需精确控制稀有场景的比例</strong>", "数周（搭建/校准渲染管线）"],
            ["众包", "单价低但需要质检层，隐性成本在 QC 而不是采集本身", "标注一致性通常低于自建团队，需要更强的质检兜底", "中：需要众包平台自身的数据处理协议", "中——众包工人分布广，但很难定向覆盖特定长尾场景", "数天到数周"],
        ]),
        DUAL(
            "直白地说：没有一种来源能单独撑起一个量产系统。自采数据最像「真实考试」，但贵、慢、还要过合规审查；"
            "公开数据集是「免费的起点」，但类别体系和真实产品的定义常常对不上；合成数据能<em>无限量</em>造稀有场景，"
            "但造出来的东西和真实传感器拍出来的东西终究有差距；众包便宜量大，但你标出来的东西质量参差不齐，"
            "得靠后面的质检环节兜底。<strong>面试里最加分的回答不是选一种，而是说清楚「用哪种来源覆盖哪一块缺口」。</strong>",
            "更严谨地说，这四条渠道在<span class=\"term\">分布对齐</span>（distribution alignment）与<span class=\"term\">边际成本</span>两个维度上几乎正交："
            "自采与众包的边际成本随样本量线性增长，合成数据的边际成本趋近于零但有一个不随样本量摊薄的<em>域差残差</em>（domain gap residual）；"
            "公开数据集的边际成本恒为零，但它的分布是历史冻结的，不会随你的产品迭代而更新。"
            "<em>一个成熟的数据系统设计，应该显式地把「用哪种来源覆盖哪一段缺口」写成一张表，而不是含糊地说『多渠道』。</em>",
        ),
        P("放到 TSR 场景里具体化：<strong>公开数据集</strong>（GTSRB / GTSDB / TT100K / Mapillary Traffic Sign，"
          "结论见 C55-01）能快速起步，但每个数据集的标志分类体系是按各自国家的法规定义的——"
          "直接拿 GTSRB（德国标准）训练再部署到国内路测，会在几十个「形状相同但语义不同」的标志类上系统性出错。"
          "<strong>合成数据</strong>在 TSR 里最擅长补的是「极端天气 + 稀有限速值」的组合（例如暴雨中的 120 限速牌），"
          "这类场景在真实车队一年也遇不到几次；<strong>自采</strong>仍然是长期精度的地基，"
          "因为标志的褪色、涂鸦、地域性变体这些「长尾里的长尾」只有真实世界会产生。"),
        CALLOUT("warn", "常见的面试失分点：只回答「我们会采集更多数据」而不说明<strong>用什么渠道补哪一类缺口</strong>。"
                        "面试官紧接着通常会追问「如果你只有 4 周时间，你会先做哪一渠道」——"
                        "答不出优先级，说明你没有真正想清楚成本-质量-合规这张画像，只是在背「要多样化数据来源」这句套话。"),
    ])),

    # ============================================================== 2
    ("labeling", "标注体系设计：规范、质检、一致性、成本模型、外包 vs 自建", "".join([
        P("数据来源解决的是「有没有」，标注体系解决的是「<strong>标签能不能被信任</strong>」。"
          "这是系统设计面试里经常被一句带过、但其实值得展开的一段——因为标注错误是最隐蔽的模型上限，"
          "它不会像代码 bug 一样报错，只会安静地把模型的天花板压低几个点。一套完整的标注体系设计要回答四个问题："
          "标注规范怎么写、怎么知道标注对不对、标注成本怎么算、以及自建团队还是外包。"),
        H3("标注规范（annotation guideline）"),
        P("规范不是一份「画框就行」的说明，而是一份<strong>边界案例判例集</strong>：多大的标志算「有效目标」（例如短边 ≥ 6 像素才标）、"
          "遮挡多少算「可标」还是「忽略」（例如遮挡 &gt; 60% 标记为 <code>ignore</code> 而不参与 loss）、"
          "背面朝向的标志怎么处理、多个相同标志重叠怎么拆分。<strong>没有边界案例判例的规范，等于把判断权下放给每个标注员自己的直觉</strong>，"
          "这正是标注不一致的根源。"),
        H3("质检（QC）三层防线"),
        TABLE(["层级", "做法", "抓什么问题", "成本占比（经验值）"], [
            ["黄金集抽检", "标注员定期标一批已有「专家共识答案」的图，比对差异", "标注员是否理解规范、是否在退化（fatigue drift）", "5%–10% 的标注量"],
            ["多标共识", "同一批图由 2–3 人独立标注，取多数/仲裁", "边界案例的系统性分歧，能量化<span class=\"term\">inter-annotator agreement</span>（标注者间一致性）", "标注成本翻 2–3 倍，只对高价值/高歧义子集做"],
            ["模型回环质检", "用当前模型的高置信度错误反查标注（模型错得「离谱」时，先怀疑标签而不是模型）", "系统性标注错误（如类别 ID 错位、坐标系反了）", "近乎零边际成本，是最划算的一层"],
        ]),
        P("一致性的量化指标：分类任务常用 <span class=\"term\">Cohen's kappa</span>（扣除随机一致后的一致率），"
          "检测任务通常用「IoU ≥ 阈值 且 类别一致」才算一次一致，再统计一致率。"
          "<strong>把一致性数字写进设计文档本身就是加分项</strong>——它说明你把「标签质量」当成一个可测量、可追踪的量，"
          "而不是「标注完了就默认它是对的」。"),
        DUAL(
            "标注成本的心算：把它拆成「单价 × 数量 × 复杂度系数」再加一个「质检开销」和「返工率」。"
            "比如每帧标注单价 0.5 元，一次质检发现 8% 的帧需要返工，返工成本按原价的 1.2 倍算（沟通与二次审核的额外开销），"
            "那么 100 万帧的真实预算就不是 50 万元，而是要再加上返工的那部分。",
            MATH(r"\text{Cost}_{\text{total}} = N \cdot p_0 \cdot c_{\text{complexity}} \;+\; N \cdot r \cdot p_0 \cdot c_{\text{rework}} \;+\; \text{Cost}_{\text{QC}}") +
            "其中 $N$ 是样本量、$p_0$ 是基础单价、$c_{\\text{complexity}}$ 是任务复杂度乘数（多类别检测通常比二分类贵 2–4 倍）、"
            "$r$ 是返工率、$c_{\\text{rework}}$ 是返工的相对代价系数、$\\text{Cost}_{\\text{QC}}$ 是质检本身的固定开销。"
            "<em>面试里能把这个公式的四项分别报出数量级，比只报一个总数更有说服力。</em>",
        ),
        H3("外包 vs 自建"),
        TABLE(["维度", "外包", "自建团队"], [
            ["单价", "更低（规模效应、劳动力成本地域套利）", "更高，但含隐性的管理与培训成本"],
            ["领域知识", "需要花时间培训，且流动性高、知识留不住", "<strong>能沉淀领域知识</strong>（如「这类褪色标志该怎么标」的经验会积累）"],
            ["响应速度", "受供应商产能与合同周期约束", "更快，能配合「触发→挖掘→标注」的紧急闭环节奏（见 C58-05）"],
            ["质量可控性", "依赖供应商自身的 QC，需要额外的验收流程", "质检环节可以直接嵌入内部工具链"],
            ["适用阶段", "标注需求量大、任务边界已经很清楚的成熟阶段", "任务刚定义、规范还在演化、需要快速迭代规范的早期阶段"],
        ]),
        CALLOUT("intuition", "<strong>一条经验法则</strong>：标注规范还在变的阶段用自建（规范每周都在改，外包团队跟不上迭代速度）；"
                             "规范稳定之后把「已定义清楚」的大批量标注外包出去，把内部团队的精力转移到「新场景的规范设计」和「质检」这两件更高价值的事上。"
                             "<em>面试里能说出这个「阶段性切换」的判断依据，比单纯说「都用一点」更显工程判断力。</em>"),
    ])),

    # ============================================================== 3
    ("leakage", "划分与泄漏防范：时间、地理、设备、track 级泄漏", "".join([
        P("这是数据系统设计里<strong>最容易被追问出破绽</strong>的一节。随机划分训练/验证/测试集在表格数据里通常是安全的，"
          "但在感知数据里几乎总是错的——因为感知数据天然带着<span class=\"term\">分组结构</span>（group structure）："
          "同一段视频的相邻帧、同一个地点拍的多张图、同一个设备产出的所有数据，彼此之间共享大量与「样本无关」的信息。"
          "随机划分会让这些共享信息同时出现在训练集和测试集里，<strong>测试集分数因此被系统性高估</strong>，"
          "这正是「离线指标很漂亮，上线却不行」的一个常见根因（呼应模块 03 的离线-在线背离）。"),
        H3("四类泄漏，逐一拆解"),
        TABLE(["泄漏类型", "机制", "TSR 场景下的具体表现", "危害程度"], [
            ["<strong>时间泄漏</strong>（temporal）", "用「未来」的信息影响了「过去」时刻的判断，或训练集里混入了测试时间段之后才产生的统计量", "用全数据集统计的归一化参数（均值/方差）去标准化训练集，而这个统计量包含了测试集时段的数据", "中——通常导致指标虚高几个点，不易察觉"],
            ["<strong>地理泄漏</strong>（geo）", "同一路口/路段的画面同时出现在训练集与测试集", "模型记住了「这个路口背景里固定有一块广告牌」，测试集恰好是同一路口的另一段视频，误判成好的泛化", "高——常见但容易被忽视，需要按位置分组"],
            ["<strong>设备泄漏</strong>（device）", "同一相机/同一标定参数的数据同时出现在两边", "某型号相机的固定畸变/色偏被模型学到，测试集恰好也用同型号相机拍摄，评测无法反映跨设备泛化", "中高——尤其是多相机供应商切换时会突然暴露"],
            ["<strong>track / 序列级泄漏</strong>（track）", "同一段连续视频里的相邻帧几乎是同一个样本的微小扰动，被随机拆到训练集与测试集两边", "标志从远到近的连续帧，其中几帧在训练、另几帧在测试——测试集本质是在考「插值」而不是「泛化」", "<strong>最高、最普遍</strong>：一段视频往往有几十到几百帧高度相关"],
        ]),
        ASCII("""连续视频序列（一次经过同一路口的行车记录）
帧号:  001  002  003  004  005  006  007  008  ...  118  119  120
       │    │    │    │    │    │    │    │         │    │    │
      ── 随机划分（错误）──────────────────────────────────────
train: 001  002       004       006  007            118       120
test :           003       005            008       119
       ↑ 003 和 002/004 几乎是同一个标志的相邻两帧，测试集"泄漏"了插值信息

      ── 按 track 分组划分（正确）───────────────────────────────
train: [001 .. 090]  这一整段 track 只出现在一边
test :              [091 .. 120]  另一整段 track 只出现在另一边"""),
        DUAL(
            "怎么发现泄漏？最直接的信号是「验证集指标好得不合理」，或者「验证集指标随训练 epoch 单调上升到接近 100%」——"
            "这在真实感知任务里几乎不可能，除非模型在背答案。更系统的方法是显式检查：给每条样本打上 <code>track_id</code>、"
            "<code>location_id</code>、<code>device_id</code>、<code>timestamp</code> 四个分组键，划分完之后逐一检查这四个键在训练集与测试集之间是否有交集。",
            "工程上的标准解法是 <span class=\"term\">group-based split</span>（分组划分，如 scikit-learn 的 <code>GroupKFold</code> 思路）："
            "选定一个或多个分组键，保证同一组的所有样本只出现在切分的一边。当多个分组键同时存在时（同一 track 可能横跨多个地点），"
            "需要按<strong>最严格的组合键</strong>分组，或者依次对每个键做交集检查并取并集排除。"
            "<em>时间泄漏的解法略有不同：应该用「训练集时间窗口早于验证/测试集时间窗口」的滚动切分（呼应真实部署里模型总是用过去数据预测未来），"
            "而不是先归一化整个数据集再切分。</em>",
        ),
        CALLOUT("danger", "<strong>「先归一化，再划分」是一个极其常见但危害很大的顺序错误。</strong>"
                          "如果先用全量数据算出均值方差再做归一化，测试集的统计信息已经通过归一化参数「泄漏」进了训练过程——"
                          "这属于时间泄漏的一种变体，即便数据本身没有时间戳也会发生。<strong>正确顺序永远是「先划分，再用训练集的统计量去处理其余各集」。</strong>"),
    ])),

    # ============================================================== 4
    ("long-tail", "长尾与偏差的识别", "".join([
        P("这一节讲的是<strong>识别</strong>，不是<strong>处理</strong>——处理长尾的具体技术（重采样、重加权、logit adjustment、"
          "解耦训练）属于 C58 模块 01，本课不重复。系统设计面试里，「你怎么知道数据有长尾/有偏差」本身就是一个常被单独追问的问题，"
          "而且很多候选人只会说「画个类别分布直方图」，这只覆盖了偏差的一个维度。"),
        TABLE(["偏差维度", "怎么识别", "TSR 场景的例子"], [
            ["类别频次长尾", "对类别计数排序画分布，用 Zipf 拟合检验幂律程度", "「限速 40」出现几十万次，「限速 5」（学校区）可能只有几十次"],
            ["场景/环境偏差", "按天气、光照、道路类型分桶统计占比，与目标运营域（ODD）的先验占比对比", "车队大多在晴天白天采集，夜间与雨雾场景占比远低于真实运营时长占比"],
            ["地理偏差", "按采集城市/路段统计占比，检查是否过度集中在少数几条常跑路线", "80% 的数据来自 3 条固定通勤路线，覆盖不了目标市场的其余路网"],
            ["标注者偏差", "按标注员分组统计其标注结果的类别分布/框尺寸分布，找出显著偏离总体的标注员", "某标注员系统性把「遮挡 &gt; 60%」也标成可见，拉高了小目标类别的「表面样本量」"],
            ["采集时间偏差", "按采集批次/月份统计，检查是否只反映某个时间窗口的路况（如某条路正在施工）", "某批数据集中采集于一次道路改造期间，临时标志占比远高于正常运营期"],
        ]),
        DUAL(
            "识别长尾和识别偏差其实是同一件事的两个切面：长尾问的是「<em>某个类别</em>是不是太少」，偏差问的是「<em>某个维度的分布</em>是不是不像真实运营环境」。"
            "两者都需要一个参照系——长尾需要「这个类别在真实世界里本来就稀少」还是「我们采集时凑巧漏了」这个区分，"
            "偏差则需要「目标运营域（ODD）里各场景的真实占比」这个先验，否则「偏差」无从谈起。",
            "更严谨地说，偏差识别的核心是比较两个分布：<strong>采集分布</strong> $P_{\\text{collect}}$ 与<strong>目标部署分布</strong> $P_{\\text{deploy}}$。"
            "常用的比较量是逐维度的占比差或 KL 散度；但 KL 散度对零概率敏感（某类在采集数据里完全缺失时会发散），"
            "工程上更常用的是<span class=\"term\">覆盖率检查</span>（coverage check）：先枚举目标 ODD 的场景组合，"
            "检查每个组合在采集数据里的样本数是否超过某个下限（例如每种「天气×光照×道路类型」组合至少 200 帧），"
            "低于下限的组合直接标记为「待补采」。",
        ),
        CALLOUT("intuition", "<strong>面试里的加分句式</strong>：「长尾和偏差不是同一件事——长尾是频次分布的形状问题，偏差是采集分布和部署分布不匹配的问题；"
                             "一个类别样本多但偏差大（比如都来自同一路口）照样是坏数据。」这句话能立刻把候选人和只会说「数据不平衡」的人区分开。"),
    ])),

    # ============================================================== 5
    ("privacy", "隐私与合规：人脸车牌脱敏及数据治理", "".join([
        P("车队采集的每一帧图像默认包含大量个人可识别信息（PII）：路人的脸、车辆的车牌、偶尔还有可定位到具体住址的门牌号。"
          "在系统设计面试里，<strong>合规不是「附加项」，是数据能不能合法存在的前提</strong>——不谈合规的数据方案，"
          "在真实公司里根本无法通过法务审查，面试官会把这一点当作「是否有量产意识」的直接信号。"),
        H3("要脱敏什么、在哪一层脱敏"),
        TABLE(["对象", "脱敏方式", "在哪个环节做", "关键权衡"], [
            ["人脸", "检测后打码/模糊化", "车端 ISP 后处理，或云端入库前的批处理", "车端脱敏更安全（原始数据不出车），但占用车端算力；云端脱敏需要传输前先做粗粒度打码"],
            ["车牌", "检测后打码/模糊化，部分场景需要保留可逆的加密映射供事故追溯", "同上", "「不可逆脱敏」满足隐私合规但丢失可追溯性；「可逆加密」需要额外的密钥管理体系"],
            ["GPS 轨迹", "空间/时间模糊化（降低坐标精度、掐头去尾隐藏起止点）", "元数据层面，而非图像层面", "过度模糊化会破坏地理分组划分（模块内第 3 节）所需要的位置信息，两者要联合设计"],
            ["门牌号/可定位背景", "通常不单独处理，依赖人脸车牌脱敏模型的检测范围覆盖它", "同脱敏模型", "误检率与漏检率的取舍见下方 callout"],
        ]),
        CALLOUT("danger", "<strong>脱敏模型本身是一个检测模型，它也有漏检率</strong>——这是一个经常被忽略的元问题："
                          "如果脱敏检测器对小尺寸/侧脸/遮挡车牌的召回率不够，就会有真实 PII 被当作「已合规处理」的数据存下来，"
                          "这本身就是合规事故。<strong>脱敏模型的召回率必须像业务模型一样被单独评测、单独设定回归门禁</strong>，"
                          "而且工作点要往「宁可错打码背景，也不能漏打码人脸」的方向偏——这是一个典型的<span class=\"term\">代价不对称</span>场景（呼应模块 01）。"),
        H3("数据治理的其他合规要点"),
        UL([
            "<strong>数据留存期限</strong>：多数隐私法规要求「留存时间不超过实现目的所必需」，系统设计里需要显式写出「原始未脱敏数据留存 N 天后自动删除，只保留脱敏版本和特征摘要」这类策略。",
            "<strong>跨境传输</strong>：车队数据如果需要传到境外的训练集群，往往受数据本地化法规约束——系统设计里要说明训练是否能在数据产生地完成，或者需要什么样的合规审批流程。",
            "<strong>最小必要原则</strong>：只采集、只标注、只传输任务真正需要的字段——例如车内摄像头不应该被用来做和乘客隐私无关的路侧标志检测任务的训练数据。",
        ]),
        DUAL(
            "直白地说：合规不是让你在设计文档末尾加一句「我们会遵守相关法规」，而是要把它落成几个可验证的具体机制——"
            "谁来脱敏、脱敏召回率多少、原始数据留多久、谁能访问未脱敏版本。",
            "从系统设计的角度，合规约束应该和延迟/成本约束一样，在<strong>需求澄清阶段</strong>就写进非功能需求里（呼应模块 01），"
            "并且反向影响架构：例如「原始图像不能出车」这条约束会直接决定脱敏必须在车端完成，而不是等数据传到云端再处理。",
        ),
    ])),

    # ============================================================== 6
    ("lineage", "数据版本与血缘", "".join([
        P("「这批模型是用哪批数据训出来的」——这个问题在事故排查、模型回滚、审计合规里会被反复问到，"
          "而大多数团队在早期都没有认真设计这件事，直到第一次「明明改了数据，却说不清模型的差异是数据还是代码带来的」才后悔。"
          "<strong>数据版本与血缘（lineage）</strong>要解决的正是这个问题：给每一份数据、每一次标注、每一次训练留下可追溯的链条。"),
        ASCII("""raw_batch_2026w03 ──┐
  (原始车队数据快照)  │
                      ├─▶ label_v7 ──┐
raw_batch_2026w04 ──┘  (含标注规范     │
  (触发挖掘补充的难例)    v7 版本)      ├─▶ dataset_snapshot_v12 ──┬─▶ model_ckpt_A (训练集版本v12)
                                       │   (切分 + 去重 + 质检后)   │
public_TT100K_v3   ─────────────────┘                            └─▶ model_ckpt_B (同快照，不同超参)

反向查询："model_ckpt_A 出问题了，是哪批数据造成的？"
   model_ckpt_A → dataset_snapshot_v12 → {label_v7, raw_batch_2026w03/04, public_TT100K_v3}
   → 定位到 raw_batch_2026w04 里混入了一批坐标系错误的标注 → 回滚到 v11，只重新验证受影响的类别"""),
        P("血缘图的三个必须字段：<strong>内容寻址</strong>（每个数据快照有唯一 hash，内容不变 hash 不变，避免「同名不同货」）、"
          "<strong>产出清单</strong>（每次训练记录用了哪个 dataset snapshot、哪个 label 版本、哪个切分规则）、"
          "<strong>变更日志</strong>（每次数据集更新，写清楚新增了什么、删除了什么、为什么）。"),
        TABLE(["场景", "没有血缘会怎样", "有血缘能做什么"], [
            ["某类别精度突然下降", "只能怀疑「是不是最近改了什么」，逐个排查代码与配置", "直接查这个类别最近一次标注更新，锁定具体是哪批标注引入了问题"],
            ["发现一批标注有系统性错误", "不知道这批错误标注影响了哪些已发布的模型", "反向查询，列出所有使用过这批数据的模型版本，评估影响范围并决定是否需要重训"],
            ["监管审计要求说明模型训练数据来源", "需要人工回忆和翻找记录，耗时且不可靠", "直接导出该模型版本的完整数据血缘链，包括来源、标注版本、脱敏处理记录"],
            ["A/B 两个模型表现不同，想确认是不是数据差异导致", "无法确认两次训练是否真的用了完全相同的数据", "对比两次训练的 dataset snapshot hash，一致则排除数据因素"],
        ]),
        DUAL(
            "版本管理的直觉：把数据集当成代码一样对待——每次变更都是一次「提交」，每个训练产出都「引用」某个具体的提交，而不是含糊地说「最新的数据」。",
            "工程实现上常见的两条路：<span class=\"term\">内容寻址存储</span>（content-addressed storage，类似 Git 的对象模型，用数据内容的哈希作为标识）"
            "与<span class=\"term\">清单文件</span>（manifest，记录一个数据集版本包含哪些具体样本 ID 的列表）。前者保证「同一份数据永远有同一个 ID」，"
            "后者保证「同一个版本号永远指向同一组样本」，两者结合才能支撑上面表格里的四类查询。实现细节见 C43，本节只讲设计原则。",
        ),
        CALLOUT("intuition", "面试里的加分表达：不要说「我们会做好版本管理」，而要说「模型的可追溯性 = 数据血缘 + 代码版本 + 配置版本 + 随机种子，"
                             "这四项里数据血缘最容易被忽略，但审计和事故排查时它往往是最关键的一环」。"),
    ])),

    # ============================================================== 7
    ("cold-start", "冷启动策略的选择树", "".join([
        P("每当要支持一个全新类别、全新地区，或者一个全新任务（比如从「检测」升级到「检测+状态识别」），"
          "都会面临同一个问题：<strong>还没有真实标注数据，第一版模型要怎么起步</strong>。"
          "这就是冷启动问题，四条常见路径——预训练迁移、合成数据、主动学习——各自的适用边界不同，"
          "选错会浪费好几周时间在一条注定行不通的路上。"),
        ASCII("""             有没有相近领域的预训练模型？
                    │
        ┌───────yes─┴─no────────┐
        ▼                       ▼
  能不能拿到少量        目标类别在物理上是否
  真实标注(几百张)?     易于参数化建模(形状/颜色规则)?
        │                       │
   ┌─yes┴no──┐            ┌─yes─┴─no───┐
   ▼         ▼            ▼            ▼
迁移学习   先做规则     合成数据+域    只能先上线一个
微调       兜底再       随机化预训练   保守的规则系统，
(冻结      收集数据                    同时启动众包/自采
backbone                              标注积累真实数据
只训头部)

  → 任何一条分支的终点都要接回「主动学习」：
    用初版模型跑线上流量，挑出低置信/高分歧样本优先送去标注（见 C58-03），
    持续把冷启动模型迭代成有真实数据支撑的正式模型。"""),
        TABLE(["场景", "推荐路径", "理由", "典型耗时"], [
            ["新增一个和已有类别形态相似的标志类别（比如新增一种限速值）", "迁移学习：冻结检测 backbone，只重训/扩展分类头", "视觉特征已经被已有类别学过，新类别只是决策边界的调整", "数天，几百张标注即可起步"],
            ["进入一个新国家/新法规体系（标志的形状-颜色-语义映射完全不同）", "先用规则系统兜底（形状+颜色的先验规则）+ 合成数据预训练，再逐步替换为学习模型", "规则系统能立刻上线保证基本可用性，避免「无保护上线」；合成数据能在没有真实数据时提供起步信号", "规则系统数天可上线，学习模型替换需要数周"],
            ["全新任务，物理上高度可参数化（比如标志的电子可变内容识别）", "合成数据 + 域随机化预训练，再用少量真实数据微调", "可参数化意味着合成引擎能覆盖绝大多数变化维度", "数周（搭建生成管线）"],
            ["完全没有先验、连规则都写不出来的新问题", "只能先收集数据，同时上线一个保守默认策略（比如「不确定就不响应/交给下游兜底规则」）", "没有任何近似模型可用时，主动学习的「用模型挑数据」这一步本身无法成立", "数月，且必须先设计好安全兜底"],
        ]),
        DUAL(
            "怎么用这棵树？先问「有没有相近领域的预训练模型」，这是最省钱的一条路，能用就先用；"
            "如果不能用，再问「问题本身好不好用规则/物理先验去近似」——形状、颜色这些强先验的东西通常可以先写规则或造合成数据兜底；"
            "如果两条都不满足，说明这是真正意义上的冷启动，唯一现实的路径是先上线安全默认值，同时尽快积累真实数据。",
            "这棵选择树的本质是在问：<strong>「哪一种先验信息可以替代真实标注数据」</strong>——预训练模型提供的是<em>视觉特征先验</em>，"
            "规则系统提供的是<em>领域知识先验</em>，合成数据提供的是<em>物理生成过程先验</em>。三种先验的强度和真实数据需求量成反比："
            "先验越强，冷启动阶段需要的真实标注就越少。<em>面试里能把这个「先验替代数据」的逻辑讲出来，"
            "比直接背「用迁移学习」这四个字更有说服力，因为它能推广到任何一个新场景，而不只是背下来的一个答案。</em>",
        ),
        CALLOUT("warn", "常见误区：把「先上规则系统」当作权宜之计而在设计文档里一笔带过。"
                        "实际上规则系统往往会作为学习模型上线后的<strong>安全兜底层</strong>长期保留（呼应 C59-04 的安全兜底设计），"
                        "而不是一个用完即弃的过渡方案——这一点在面试里主动提出，是对「量产系统怎么演进」有认识的信号。"),
    ])),

    # ============================================================== 8
    ("storage", "存储与读取吞吐的量级估算", "".join([
        P("数据系统设计的最后一块拼图是数量级——面试官经常会追问一句「这个规模大概需要多少存储/多快的读取带宽」，"
          "这时候需要的不是精确数字，而是<strong>能撑住合理性检验的数量级心算</strong>。通用的 Fermi 估算方法见 C65-01，"
          "本节只给数据系统专属的锚点数字与两条常用公式。"),
        MATH(r"V_{\text{daily}} \;=\; N_{\text{vehicle}} \times H_{\text{active}} \times N_{\text{cam}} \times \text{fps} \times 3600 \times \bar{s}_{\text{frame}}"),
        P("举一组假设性的具体数字走一遍：单车 7 路摄像头、1920×1080、30 fps、JPEG 压缩后平均每帧约 300KB、每天有效行驶 8 小时。"
          "单车每秒产出 $7 \\times 30 \\times 300\\text{KB} \\approx 63\\text{MB/s}$，单车每天约 $63\\text{MB/s} \\times 3600 \\times 8 \\approx 1.8\\text{TB}$。"
          "一支 200 辆车的车队，<strong>全量原始数据每天约 360TB</strong>——这个数字大到不可能全部上传与长期存储。"
          "这正是为什么触发式回传（见 C58-03）是必需品而不是可选项：只有命中触发规则的片段才上传，命中率通常在万分之一到千分之一量级，"
          "把实际上传量压到 GB–TB/天的可承受范围。"),
        H3("训练侧的读取吞吐"),
        MATH(r"\text{Throughput}_{\text{required}} \;=\; N_{\text{accelerator}} \times \text{imgs/s per accelerator} \times \bar{s}_{\text{stored}}"),
        P("假设单张加速卡在给定 batch size 下能吃 150 张图/秒（数量级示例，具体值取决于模型与硬件），"
          "存储的图片经压缩平均 300KB，单卡所需读取带宽约 $150 \\times 300\\text{KB} \\approx 45\\text{MB/s}$；"
          "8 卡训练节点则需要约 <strong>360MB/s</strong> 的持续读取吞吐。把这个数字和常见存储介质的吞吐量级对比，"
          "就能立刻判断「本地磁盘够不够、要不要加缓存层」。"),
        TABLE(["存储/网络介质", "吞吐量级", "对 360MB/s 需求的结论"], [
            ["机械硬盘 HDD（7200rpm）", "≈150–200 MB/s", "<strong>不够</strong>，随机读还会更差，必须靠预取/缓存"],
            ["SATA SSD", "≈500 MB/s", "单块勉强够，但没有冗余余量"],
            ["NVMe SSD", "≈2000–7000 MB/s", "<strong>充裕</strong>，是训练节点本地缓存的首选"],
            ["万兆网卡 / 网络存储（10GbE）", "≈1.25 GB/s（理论上限）", "多节点共享网络存储时要除以并发训练任务数，容易成为瓶颈"],
            ["对象存储（如 S3 兼容存储）单连接", "≈100–500 MB/s，可并行多连接线性扩展", "适合冷数据长期存放，训练前需要预先同步/缓存到本地"],
        ]),
        DUAL(
            "怎么在面试里用这两条公式？听到「车队规模」和「训练吞吐需求」，先各自套一遍公式报出数量级，"
            "再对照锚点表说出结论——「原始车队数据是 TB/天量级，必须靠触发式回传；训练读取吞吐是几百 MB/s 量级，"
            "本地 NVMe 缓存就够，不需要为了这个去过度设计分布式存储」。",
            "这两个公式的价值在于把「存储系统怎么设计」从一个开放式问题，变成一个<strong>先算数量级、再选方案</strong>的收敛过程——"
            "数量级差一个到两个数量级，方案选择完全不同（是否需要分布式存储、是否需要边缘预筛选、是否需要专门的高吞吐缓存层）。"
            "<em>面试官往往通过「你敢不敢先写下一个具体假设再算」来判断你是否真的具备工程量感，而不是通过数字本身对不对来打分。</em>",
        ),
        CALLOUT("intuition", "记住两个可复用的锚点：① 单路摄像头原始/压缩视频流大致是 <strong>MB/s 量级</strong>（而不是 KB/s 或 GB/s）；"
                             "② 单张现代加速卡训练检测模型的数据吞吐需求大致是<strong>几十 MB/s 量级</strong>。"
                             "记住这两个锚点，任何规模的车队/训练集群问题都能靠乘法心算给出数量级答案。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("数据系统设计这块，学术界的关注度长期低于建模——但工业界的真实投入恰恰相反。下面几个方向，"
          "面试里未必会被直接问到，但理解它们能帮你在被追问「你觉得现在这套流程还有什么问题」时给出有分量的回答。"),
        UL([
            "<strong>数据质量的可计算度量仍不成熟。</strong>「一致性」「代表性」这些概念目前主要靠人工设计的代理指标（一致率、覆盖率检查）去近似，"
            "还没有一个被广泛接受的、能端到端预测「这批数据能带来多少模型收益」的质量分数。"
            "<em>Data-centric AI 这个方向近几年正在尝试补这个洞，但离「拿一个数字就能决定值不值得标注」还有距离。</em>",
            "<strong>合成数据的域差衡量本身缺少标准。</strong>「这批合成数据和真实数据差多少」目前主要靠下游模型表现间接推断，"
            "而不是有一个独立于任务的度量。<em>这意味着合成数据策略在系统设计里天然带有「要靠实验验证」的不确定性，"
            "面试里主动提到这一点，比假设合成数据「理所当然有效」更诚实。</em>",
            "<strong>隐私保护与数据可用性的权衡还在演化。</strong>差分隐私、联邦学习等技术理论上能在不集中原始数据的前提下训练模型，"
            "但在自动驾驶感知这类对长尾场景极度敏感的任务上，这些技术目前的实用性仍然有限——"
            "<em>脱敏之后的数据能不能支撑长尾场景的精细分析，本身是一个未解问题。</em>",
            "<strong>血缘系统的标准化程度低。</strong>不同公司的数据血缘实现几乎都是自研，业界还没有类似「Git 之于代码版本管理」那样的事实标准，"
            "这也是为什么很多团队在规模变大之后才被迫补课。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Sambasivan et al., <em>“Everyone wants to do the model work, not the data work”</em>（CHI 2021）——"
                         "工业界数据工作被系统性低估的实证研究，是理解「为什么数据系统设计值得单独准备」的最佳背景材料。"
                         "<strong>★</strong> Northcutt et al., <em>Confident Learning</em>（JMLR 2021）——用模型自身的预测置信度反查标注错误的方法论，"
                         "对应本模块「模型回环质检」这一层。"
                         "<strong>★</strong> Gebru et al., <em>Datasheets for Datasets</em>（2018）——数据集文档化的标准提案，"
                         "是数据版本与血缘设计里「元数据该记什么」这一问题的经典参考。</p>"
                         "<p>相邻课程：C43（数据工程实现细节，本课不重复）、C58（长尾与数据闭环的技术细节，本课只讲面试组织方式）、"
                         "C55 模块 01（TSR 数据集全景）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 02 · 数据系统设计（成本-质量-合规画像 / 标注体系 / 泄漏防范 / 长尾 / 隐私 / 血缘 / 冷启动 / 存储吞吐）

目标：把「数据系统怎么设计」从一段口头描述，变成几个**可以运行、可以断言**的小工具。

本 notebook 你会亲手实现：
1. **标注成本模型与预算分配** —— 从单价推总预算，再在预算有限时决定优先给哪个类别补标注
2. **泄漏检测器** —— 构造 track / 地理 / 设备 / 时间四类泄漏，并各自验证「坏切分触发、干净切分不触发」
3. **数据规模需求反推** —— 用两个试点观测点拟合学习曲线，反推达到目标指标需要多少样本
4. **分层抽样与代表性检验** —— 用卡方统计量 + 蒙特卡洛 p 值，纯 numpy 判断一份样本代表不代表总体
5. **存储与吞吐量级计算器** —— 车队原始数据量、训练读取吞吐，各自的数量级
6. **冷启动策略决策树** —— 给定先验条件，代码化地选出该走哪条路

> 心智模型：**这一模块讲的都是「在建模开始之前，必须想清楚的事」——数据系统设计得好不好，直接决定了模型能力的天花板。**"""),

    md("""## 1 · 标注成本模型与预算分配

成本 = 基础单价 × 数量 × 复杂度系数 + 返工成本 + 质检固定开销。预算有限时，按「缺口从大到小」贪心分配。"""),

    code("""import numpy as np, math, random
from collections import Counter

def annotation_cost(n, p0=0.5, c_complexity=2.5, rework_rate=0.08, rework_multiplier=1.2, qc_fixed=0.0):
    \"\"\"标注总成本：基础成本 + 返工成本 + 质检固定开销。
    p0: 单帧基础单价；c_complexity: 任务复杂度乘数（多类别检测通常 2-4 倍于二分类）；
    rework_rate: 质检发现的返工比例；rework_multiplier: 返工的相对代价系数。\"\"\"
    base = n * p0 * c_complexity
    rework = n * rework_rate * p0 * c_complexity * rework_multiplier
    return base + rework + qc_fixed

total = annotation_cost(1_000_000, qc_fixed=50_000)
print(f'100 万帧、多类别检测复杂度系数 2.5、返工率 8%：总预算 ≈ {total:,.0f} 元')
assert abs(total - 1_420_000) < 1e-6
print('其中返工成本占比：', f\"{(total - 1_000_000*0.5*2.5 - 50_000) / total:.1%}\")
print('\\n✅ 成本模型就位：面试里能把「基础成本 / 返工成本 / 质检开销」三项分别报数量级，比只报一个总数更有说服力。')"""),

    code("""def allocate_budget(gaps, unit_cost, budget):
    \"\"\"gaps: {类别: 需要补标注的样本数缺口}。按缺口从大到小贪心分配预算，
    直到预算用尽或缺口全部补齐。返回 (实际分配, 剩余预算)。\"\"\"
    order = sorted(gaps, key=lambda k: -gaps[k])
    alloc = {k: 0 for k in gaps}
    remaining = budget
    for k in order:
        need = gaps[k]
        cost_needed = need * unit_cost
        if cost_needed <= remaining:
            alloc[k] = need
            remaining -= cost_needed
        else:
            alloc[k] = int(remaining // unit_cost)
            remaining -= alloc[k] * unit_cost
            break
    return alloc, remaining

gaps = {'限速5': 500, '限速120': 300, '停车让行': 1000}   # 三个长尾类别的补标注缺口
alloc, remaining = allocate_budget(gaps, unit_cost=1.25, budget=2000)
print('分配结果：', alloc, '| 剩余预算：', remaining)
assert alloc == {'限速5': 500, '限速120': 100, '停车让行': 1000}
assert remaining == 0
print('\\n✅ 预算优先给缺口最大的「停车让行」，「限速120」只补到预算耗尽为止——')
print('   这正是长尾类别补标注时最常见的真实约束：预算不够覆盖所有缺口，必须显式排优先级。')"""),

    md("""## 2 · 泄漏检测器：构造并检出四类泄漏

track / 地理 / 设备 / 时间，各自构造一个「随机切分（坏）」与一个「按分组切分（干净）」，
验证检测器能在坏切分上报警、在干净切分上保持沉默。"""),

    code("""def group_overlap(train_ids, test_ids):
    \"\"\"分组键在训练集与测试集之间的交集——非空即泄漏。\"\"\"
    return set(np.unique(train_ids)) & set(np.unique(test_ids))

def has_time_leak(train_time, test_time):
    \"\"\"时间泄漏：训练集里存在比测试集最早样本还晚的时间点，说明切分不是严格「早训练、晚测试」。\"\"\"
    return bool(train_time.max() > test_time.min())

# ── 场景 A：track 级泄漏（同一段连续视频的帧被随机拆到两边）──
rng_a = np.random.default_rng(1)
n_tracks, frames_per_track = 20, 10
track_id = np.repeat(np.arange(n_tracks), frames_per_track)     # 20 条 track，每条 10 帧
idx = np.arange(len(track_id))

bad_idx = rng_a.permutation(idx)                                 # 坏切分：忽略 track 边界随机打散
split = int(0.8 * len(idx))
bad_train, bad_test = bad_idx[:split], bad_idx[split:]
leak_bad_track = group_overlap(track_id[bad_train], track_id[bad_test])
assert len(leak_bad_track) > 0, '随机切分理应产生 track 泄漏'

clean_test_tracks = set(range(16, 20))                            # 干净切分：整段 track 归一边
clean_mask = np.isin(track_id, list(clean_test_tracks))
leak_clean_track = group_overlap(track_id[idx[~clean_mask]], track_id[idx[clean_mask]])
assert len(leak_clean_track) == 0, '按 track 分组切分不应有重叠'

print(f'track 泄漏 —— 坏切分重叠 {len(leak_bad_track)} 条 track；干净切分重叠 {len(leak_clean_track)} 条 track')"""),

    code("""# ── 场景 B：地理泄漏（同一路口/路段同时出现在两边）──
rng_b = np.random.default_rng(2)
n = 500
location_id = rng_b.integers(0, 8, size=n)                        # 8 个地理位置
idx = np.arange(n)
bad_idx = rng_b.permutation(idx)
split = int(0.8 * n)
bad_train, bad_test = bad_idx[:split], bad_idx[split:]
leak_bad_geo = group_overlap(location_id[bad_train], location_id[bad_test])
assert len(leak_bad_geo) > 0

clean_mask = np.isin(location_id, [6, 7])                         # 干净切分：整片地点只留给测试集
leak_clean_geo = group_overlap(location_id[idx[~clean_mask]], location_id[idx[clean_mask]])
assert len(leak_clean_geo) == 0
print(f'地理泄漏 —— 坏切分重叠 {len(leak_bad_geo)} 个地点；干净切分重叠 {len(leak_clean_geo)} 个地点')

# ── 场景 C：设备泄漏（同一相机/标定同时出现在两边）──
rng_c = np.random.default_rng(3)
device_id = rng_c.integers(0, 3, size=n)                          # 3 种设备
bad_idx = rng_c.permutation(idx)
bad_train, bad_test = bad_idx[:split], bad_idx[split:]
leak_bad_dev = group_overlap(device_id[bad_train], device_id[bad_test])
assert len(leak_bad_dev) > 0

clean_mask = device_id == 2                                       # 干净切分：设备 2 整体留给测试集
leak_clean_dev = group_overlap(device_id[idx[~clean_mask]], device_id[idx[clean_mask]])
assert len(leak_clean_dev) == 0
print(f'设备泄漏 —— 坏切分重叠 {len(leak_bad_dev)} 种设备；干净切分重叠 {len(leak_clean_dev)} 种设备')

# ── 场景 D：时间泄漏（切分不满足「训练集时间早于测试集」）──
rng_d = np.random.default_rng(4)
n2 = 1000
timestamp = np.arange(n2)                                         # 严格递增的时间戳
idx2 = np.arange(n2)
bad_idx = rng_d.permutation(idx2)
split2 = int(0.8 * n2)
bt, bte = bad_idx[:split2], bad_idx[split2:]
leak_bad_time = has_time_leak(timestamp[bt], timestamp[bte])
assert leak_bad_time is True

ct, cte = idx2[:split2], idx2[split2:]                            # 干净切分：滚动切分，训练集严格更早
leak_clean_time = has_time_leak(timestamp[ct], timestamp[cte])
assert leak_clean_time is False
print(f'时间泄漏 —— 坏切分: {leak_bad_time}；干净切分: {leak_clean_time}')

print('\\n✅ 四类泄漏全部「坏切分触发、干净切分不触发」——这正是「随机划分在感知数据里几乎总是错的」的可执行证据。')"""),

    md("""## 3 · 数据规模需求反推：从学习曲线拟合到样本量

用一个饱和型学习曲线 $p(n) = 1 - a \\cdot n^{-b}$ 近似「样本量 → 指标」的关系，
两个试点观测点就能拟合 $a, b$，再反解「达到目标指标需要多少样本」。"""),

    code("""def learning_curve(n, a=5.0, b=0.4):
    \"\"\"饱和型学习曲线：n 越大指标越接近 1，但边际收益递减。\"\"\"
    return 1.0 - a * (np.asarray(n, dtype=float) ** -b)

def required_n_closed_form(target, a, b):
    \"\"\"闭式反解：target = 1 - a n^-b  =>  n = (a / (1-target)) ** (1/b)。\"\"\"
    assert 0 < target < 1
    return (a / (1 - target)) ** (1 / b)

def required_n_binary_search(target, a, b, n_max=10**12):
    \"\"\"二分反解，作为闭式解的独立校验（learning_curve 对 n 单调递增，二分合法）。\"\"\"
    lo, hi = 1.0, float(n_max)
    for _ in range(200):
        mid = (lo + hi) / 2
        if learning_curve(mid, a, b) >= target:
            hi = mid
        else:
            lo = mid
    return hi

a0, b0 = 5.0, 0.4
n90_cf = required_n_closed_form(0.9, a0, b0)
n90_bs = required_n_binary_search(0.9, a0, b0)
print(f'闭式解: {n90_cf:,.0f}   二分解: {n90_bs:,.0f}')
assert abs(n90_cf - n90_bs) / n90_cf < 1e-6
assert learning_curve(n90_cf, a0, b0) >= 0.9 - 1e-9

print('\\n✅ 闭式解与二分解一致：反推样本量不需要靠猜，只要有一个单调的「样本量→指标」模型就能解。')"""),

    md("""## 4 · 分层抽样与代表性检验

分层抽样：按各层在总体里的真实占比抽样。代表性检验：用卡方统计量 + 蒙特卡洛模拟出的 p 值判断
「这份样本的分布，像不像是从总体里按真实比例抽出来的」——全程纯 numpy，不依赖 scipy。"""),

    code("""def stratified_sample(population, strata_values, n_total, rng):
    \"\"\"按各层在总体中的占比等比例抽样；名额向下取整后的剩余名额补给样本量最大的层。\"\"\"
    counts = {s: int(np.sum(population == s)) for s in strata_values}
    total = len(population)
    alloc = {s: int(n_total * counts[s] / total) for s in strata_values}
    remainder = n_total - sum(alloc.values())
    if remainder > 0:
        biggest = max(strata_values, key=lambda s: counts[s])
        alloc[biggest] += remainder
    sample_idx = []
    for s in strata_values:
        idx_s = np.where(population == s)[0]
        sample_idx.append(rng.choice(idx_s, size=alloc[s], replace=False))
    return np.concatenate(sample_idx), alloc

def chi_square_stat(observed_counts, expected_props):
    \"\"\"皮尔逊卡方统计量：观测计数与「按期望比例应有的计数」的偏离程度。\"\"\"
    n = observed_counts.sum()
    expected_counts = expected_props * n
    return float(np.sum((observed_counts - expected_counts) ** 2 / expected_counts))

def monte_carlo_pvalue(stat_obs, expected_props, n_total, rng, n_sim=2000):
    \"\"\"用多项分布蒙特卡洛模拟「真代表总体的样本」应有的卡方统计量分布，
    p 值 = 模拟统计量 >= 观测统计量 的比例；p 值小说明观测样本偏离真实比例太远，不像是随机抽样的结果。\"\"\"
    sims = rng.multinomial(n_total, expected_props, size=n_sim)
    sim_stats = np.array([chi_square_stat(row, expected_props) for row in sims])
    return float(np.mean(sim_stats >= stat_obs))

rng_s = np.random.default_rng(11)
pop_props = np.array([0.50, 0.25, 0.15, 0.07, 0.03])              # 5 个场景桶的真实占比
strata_values = list(range(5))
N = 20_000
population = np.repeat(np.arange(5), (pop_props * N).astype(int))
rng_s.shuffle(population)

sample_idx, alloc = stratified_sample(population, strata_values, 1000, rng_s)
sample = population[sample_idx]
sample_props = np.array([np.mean(sample == s) for s in strata_values])
print('分层抽样占比:', np.round(sample_props, 3), '| 总体占比:', pop_props)
assert np.allclose(sample_props, pop_props, atol=0.02)

obs_counts = np.array([np.sum(sample == s) for s in strata_values])
stat = chi_square_stat(obs_counts, pop_props)
p_good = monte_carlo_pvalue(stat, pop_props, 1000, rng_s, n_sim=1000)
print(f'分层抽样样本：卡方统计量 {stat:.2f}，蒙特卡洛 p 值 {p_good:.3f}')
assert p_good > 0.05, '按真实比例分层抽出来的样本不应该被判定为不具代表性'
print('\\n✅ 分层抽样通过代表性检验：p 值远大于 0.05，没有理由怀疑它偏离总体分布。')"""),

    code("""# ── 对照：一份「图省事」的便利抽样（只抄了场景 0/1 前面若干条），代表性检验应该报警 ──
convenience_idx = np.concatenate([
    np.where(population == 0)[0][:800],
    np.where(population == 1)[0][:200],
])
convenience_sample = population[convenience_idx]
bad_counts = np.array([np.sum(convenience_sample == s) for s in strata_values])
bad_stat = chi_square_stat(bad_counts, pop_props)
p_bad = monte_carlo_pvalue(bad_stat, pop_props, 1000, rng_s, n_sim=1000)
print(f'便利抽样：卡方统计量 {bad_stat:.2f}，蒙特卡洛 p 值 {p_bad:.3f}')
assert p_bad < 0.01, '完全没有场景 2/3/4 的便利抽样理应被判定为不具代表性'
print('\\n✅ 便利抽样被正确拦下——这正是「验证集必须做代表性检验」的意义：')
print('   光看抽样量够不够大是不够的，分布对不对也要专门验证。')"""),

    md("""## 5 · 存储与吞吐量级计算器

车队原始数据的量级，和训练侧需要的读取吞吐量级，是数据系统设计里最容易被追问「大概多少」的两个数字。"""),

    code("""def daily_raw_volume_gb(n_vehicle, hours_active, n_cam, fps, avg_frame_kb):
    \"\"\"车队每日原始数据量（GB）：车数 x 有效行驶小时 x 摄像头数 x 帧率 x 每帧大小。\"\"\"
    bytes_per_day = n_vehicle * hours_active * n_cam * fps * 3600 * avg_frame_kb * 1024
    return bytes_per_day / (1024 ** 3)

def required_throughput_mb_s(n_accelerator, imgs_per_s_per_accel, avg_img_kb):
    \"\"\"训练侧所需读取吞吐（MB/s）：加速卡数 x 单卡每秒吃图数 x 单图大小。\"\"\"
    return n_accelerator * imgs_per_s_per_accel * avg_img_kb / 1024

daily_gb = daily_raw_volume_gb(n_vehicle=200, hours_active=8, n_cam=7, fps=30, avg_frame_kb=300)
print(f'200 辆车、7 路摄像头、30fps、每天 8 小时：原始数据量 ≈ {daily_gb:,.0f} GB/天 ≈ {daily_gb/1024:.0f} TB/天')
assert 1e5 < daily_gb < 1e6, '这应该是十万到百万 GB 量级（百TB到PB级），否则假设有问题'

train_mb_s = required_throughput_mb_s(n_accelerator=8, imgs_per_s_per_accel=150, avg_img_kb=300)
print(f'8 卡训练节点、单卡 150 图/秒、每图 300KB：所需读取吞吐 ≈ {train_mb_s:.0f} MB/s')
assert 100 < train_mb_s < 1000, '训练读取吞吐通常是几百 MB/s 量级'

MEDIA = [('HDD 7200rpm', 175), ('SATA SSD', 500), ('NVMe SSD', 3500), ('10GbE 网络存储', 1250)]
print(f\"\\n{'介质':<16} {'吞吐(MB/s)':>10}   能否撑住 {train_mb_s:.0f} MB/s 的训练读取需求\")
for name, bw in MEDIA:
    ok = '✅ 够' if bw >= train_mb_s else '❌ 不够，需缓存/预取'
    print(f'{name:<16} {bw:>10}   {ok}')

print(f'\\n结论：原始数据是 <strong>百 TB/天</strong> 量级，必须靠触发式回传（见 C58-03）而非全量上传；')
print(f'      训练读取吞吐是<strong>几百 MB/s</strong>量级，本地 NVMe 足够，HDD 不够。')"""),

    md("""## 6 · 冷启动策略决策树"""),

    code("""def cold_start_strategy(has_pretrained, physically_parameterizable):
    \"\"\"冷启动选择树：
    有相近领域的预训练模型 -> 迁移学习微调；
    没有预训练但问题物理上可参数化（形状/颜色/材质规则明确）-> 合成数据 + 域随机化预训练；
    两者都没有 -> 先上规则/安全默认值兜底，同时启动真实数据采集与主动学习。\"\"\"
    if has_pretrained:
        return 'transfer_learning'
    if physically_parameterizable:
        return 'synthetic_pretrain'
    return 'rule_based_fallback'

CASES = [
    (True,  True,  '新增一个和已有类别形态相似的标志类别'),
    (True,  False, '进入新国家但已有跨域预训练的检测 backbone'),
    (False, True,  '电子可变限速牌识别（内容高度可参数化）'),
    (False, False, '完全没有先验的新问题'),
]
for has_pre, param, desc in CASES:
    strategy = cold_start_strategy(has_pre, param)
    print(f'{desc:<32} -> {strategy}')

assert cold_start_strategy(True, True) == 'transfer_learning'
assert cold_start_strategy(True, False) == 'transfer_learning'
assert cold_start_strategy(False, True) == 'synthetic_pretrain'
assert cold_start_strategy(False, False) == 'rule_based_fallback'
print('\\n✅ 决策树就位：核心是问「哪种先验能替代真实标注数据」，而不是死记「用迁移学习」这一个答案。')"""),

    md("""## ✏️ 练习 1：标注质检抽检比例求解器

实现 `min_spotcheck_n(defect_rate, confidence=0.95)`：给定标注缺陷率 `defect_rate`，
求最少要抽检多少帧，才能保证「至少发现一个缺陷帧」的概率 ≥ `confidence`。

提示：抽检 n 帧一个缺陷都没抓到的概率是 $(1-\\text{defect\\_rate})^n$，
所以「至少抓到一个」的概率是 $1-(1-\\text{defect\\_rate})^n \\ge \\text{confidence}$，反解 $n$ 并向上取整。"""),

    code("""def min_spotcheck_n(defect_rate, confidence=0.95):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert min_spotcheck_n(0.01, 0.95) == 299
assert min_spotcheck_n(0.02, 0.99) == 228
assert min_spotcheck_n(0.10, 0.95) == 29

def catch_prob(n, defect_rate):
    return 1 - (1 - defect_rate) ** n

n_needed = min_spotcheck_n(0.01, 0.95)
assert catch_prob(n_needed, 0.01) >= 0.95
assert catch_prob(n_needed - 1, 0.01) < 0.95        # n-1 帧应该还不够
print(f'缺陷率 1% 时，抽检 {n_needed} 帧才能有 95% 把握发现至少一个缺陷帧。')
print('✅ 练习 1 通过：质检抽检比例不是拍脑袋定的 5%/10%，是缺陷率和置信度的函数。')"""),

    md("""## ✏️ 练习 2：泄漏严重度评分器

实现 `leakage_severity(track_frac, geo_frac, device_frac, time_leak, weights=(0.4,0.3,0.2,0.1))`：
返回加权严重度分数 = `weights[0]*track_frac + weights[1]*geo_frac + weights[2]*device_frac + weights[3]*float(time_leak)`。
权重次序对应「危害排序：track > 地理 > 设备 > 时间」（呼应第 3 节的四类泄漏危害程度分析）。"""),

    code("""def leakage_severity(track_frac, geo_frac, device_frac, time_leak, weights=(0.4, 0.3, 0.2, 0.1)):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
s_bad = leakage_severity(16 / 20, 8 / 8, 3 / 3, True)
s_clean = leakage_severity(0, 0, 0, False)
assert abs(s_bad - 0.92) < 1e-9, s_bad
assert s_clean == 0.0
s_only_time = leakage_severity(0, 0, 0, True)
assert abs(s_only_time - 0.1) < 1e-9
print(f'全部泄漏: {s_bad:.2f} | 全部干净: {s_clean:.2f} | 只有时间泄漏: {s_only_time:.2f}')
print('✅ 练习 2 通过：把「有没有泄漏」升级成「泄漏有多严重」，才谈得上排优先级修复。')"""),

    md("""## ✏️ 练习 3：学习曲线拟合反推样本量

实现 `fit_learning_curve(n1, p1, n2, p2)`：给定两个试点观测点 $(n_1,p_1),(n_2,p_2)$，
拟合 $p(n) = 1 - a n^{-b}$ 里的 $a, b$，返回 `(a, b)`。

推导：$\\dfrac{1-p_1}{1-p_2} = \\left(\\dfrac{n_2}{n_1}\\right)^{b}$，两边取对数解出 $b$，再代回任意一点解出 $a$。"""),

    code("""def fit_learning_curve(n1, p1, n2, p2):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
a_fit, b_fit = fit_learning_curve(1000, 0.6, 4000, 0.75)
assert abs(learning_curve(1000, a_fit, b_fit) - 0.6) < 1e-9
assert abs(learning_curve(4000, a_fit, b_fit) - 0.75) < 1e-9

n_target = required_n_closed_form(0.9, a_fit, b_fit)
assert n_target > 4000, '目标指标 0.9 高于试点 2 的 0.75，需要的样本量必须更多'
print(f'拟合得到 a={a_fit:.3f}, b={b_fit:.3f}；要把指标从 0.75（n=4000）推到 0.9，需要约 {n_target:,.0f} 个样本。')
print('✅ 练习 3 通过：两个试点观测点，就能把「还要标多少数据」从直觉变成一个可算的数。')"""),

    md("""## ✏️ 练习 4：分层抽样的预算保底分配器

实现 `stratified_alloc_with_floor(strata_counts, n_total, min_per_stratum)`：
按各层在总体中的占比比例分配抽样名额（向下取整），但每层至少分到 `min_per_stratum` 个名额——
即便这会让总分配量超过 `n_total`（这正是「保证稀有层被看见」要付出的代价）。"""),

    code("""def stratified_alloc_with_floor(strata_counts, n_total, min_per_stratum):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
strata_counts = {'A': 10000, 'B': 5000, 'C': 500, 'D': 50}
alloc = stratified_alloc_with_floor(strata_counts, 1000, min_per_stratum=30)
assert alloc == {'A': 643, 'B': 321, 'C': 32, 'D': 30}
assert sum(alloc.values()) == 1026          # 超过 n_total=1000，因为 D 层被保底拉到了 30
print('分配结果：', alloc, '| 总分配量：', sum(alloc.values()), '（原始预算 1000）')
print('✅ 练习 4 通过：稀有层 D 本该按比例只分到 3 个名额，保底机制把它拉到 30，')
print('   代价是总分配量超出预算 26 个——这个超支就是「不让稀有层归零」需要付出的真实代价。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def min_spotcheck_n(defect_rate, confidence=0.95):
    if defect_rate <= 0:
        return float('inf')
    n = math.log(1 - confidence) / math.log(1 - defect_rate)
    return math.ceil(n)"""),

    code("""# 练习 2 参考答案
def leakage_severity(track_frac, geo_frac, device_frac, time_leak, weights=(0.4, 0.3, 0.2, 0.1)):
    return (weights[0] * track_frac + weights[1] * geo_frac
            + weights[2] * device_frac + weights[3] * float(time_leak))"""),

    code("""# 练习 3 参考答案
def fit_learning_curve(n1, p1, n2, p2):
    b = math.log((1 - p1) / (1 - p2)) / math.log(n2 / n1)
    a = (1 - p1) * (n1 ** b)
    return a, b"""),

    code("""# 练习 4 参考答案
def stratified_alloc_with_floor(strata_counts, n_total, min_per_stratum):
    total = sum(strata_counts.values())
    alloc = {}
    for s, c in strata_counts.items():
        raw = int(n_total * c / total)
        alloc[s] = max(min_per_stratum, raw)
    return alloc"""),

    md("""---
## 🧪 真实工程胶囊：数据系统设计文档模板 + 面试口播要点"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# A. 数据系统设计文档模板（面试白板可以照这个骨架展开）
# ══════════════════════════════════════════════════════════════════════
# 1. 来源画像：自采 / 公开 / 合成 / 众包 各覆盖哪一块缺口，给出成本-质量-合规的对比
# 2. 标注体系：规范（含边界案例判例）+ 质检三层防线（黄金集/多标共识/模型回环）
#              + 成本模型（基础+返工+QC）+ 外包/自建的阶段性判断
# 3. 划分方案：分组键有哪些（track_id/location_id/device_id/timestamp），
#              按哪个粒度分组切分，是否做过四类泄漏检测
# 4. 长尾与偏差：类别频次分布 + 场景覆盖率检查（对照目标 ODD 的先验占比）
# 5. 隐私合规：脱敏对象、脱敏发生在哪一层、脱敏模型自身的召回率指标、留存期限
# 6. 版本与血缘：数据集快照怎么标识、训练如何引用具体版本、能否反查血缘
# 7. 冷启动：新任务/新地区上线时走哪条路径，安全兜底是什么
# 8. 存储与吞吐：车队原始数据量级、触发回传后的实际上传量级、训练读取吞吐需求

# ══════════════════════════════════════════════════════════════════════
# B. 面试里最容易被追问的三句话，提前想好怎么答
# ══════════════════════════════════════════════════════════════════════
# Q: "你怎么保证训练集和测试集没有泄漏？"
# A: "我会按 track_id / location_id / device_id 做分组切分而不是随机切分，
#     并且用滚动时间窗口保证训练集严格早于测试集；上线前我会跑一次四类泄漏检测。"
#
# Q: "标注质量怎么保证？"
# A: "三层质检：黄金集抽检看标注员理解是否到位，多标共识量化标注者间一致性，
#     模型回环质检零成本地抓系统性错误——三层组合而不是只做一层。"
#
# Q: "数据不够怎么办？"
# A: "先看这是长尾问题还是冷启动问题：长尾用重采样/重加权/copy-paste 处理（见 C58），
#     全新任务用冷启动选择树——有预训练用迁移学习，问题可参数化用合成数据，否则先上
#     规则兜底同时启动主动学习。"

# ══════════════════════════════════════════════════════════════════════
# C. 与本课程其他部分的分工（别重复准备）
# ══════════════════════════════════════════════════════════════════════
# · 长尾处理的具体算法（重采样/重加权/logit adjustment）  -> C58 模块 01（本课只讲识别）
# · 数据闭环的触发/挖掘/基础设施细节                        -> C58 模块 03-05（本课只讲面试组织方式）
# · 数据工程的实现细节（存储格式/流水线代码）                -> C43（本课只讲设计取舍）
# · TSR 数据集全景与标志分类体系                            -> C55 模块 01（本课直接引用其结论）
# · 通用 Fermi 估算方法                                    -> C65 模块 01（本课只给数据系统专属锚点数字）
'''
print(RECIPE)
for token in ['track_id', 'location_id', '滚动时间窗口', '三层质检', '冷启动选择树', 'C58 模块 01', 'C55 模块 01']:
    assert token in RECIPE, token
print('✅ 检查单覆盖：设计文档骨架 / 高频追问的标准答法 / 与其他课程的分工边界')"""),

    md("""### 小结

- **数据来源没有万能解**：自采/公开/合成/众包在成本-质量-合规三个维度上几乎互补，
  面试里最加分的回答是「用哪种来源覆盖哪一段缺口」，而不是选一种。
- **标注体系要能回答「标签能不能被信任」**：规范里的边界案例判例、三层质检防线
  （黄金集/多标共识/模型回环）、以及把成本拆成「基础+返工+QC」三项，都是可以当场讲清楚的具体机制。
- **随机划分在感知数据里几乎总是错的**：track / 地理 / 设备 / 时间四类泄漏会让离线指标被系统性高估，
  正确做法是按分组键做 group-based split，时间维度用滚动窗口而不是全局随机。
- **长尾和偏差是两个不同的问题**：长尾问的是「某类别是不是太少」，偏差问的是「采集分布和部署分布是否匹配」——
  一个类别样本多但都来自同一路口，照样是坏数据。
- **合规是数据能不能合法存在的前提，不是附加项**：脱敏模型本身也有召回率，需要像业务模型一样被单独评测。
- **冷启动的本质是问「哪种先验能替代真实标注数据」**：预训练模型给视觉特征先验，规则系统给领域知识先验，
  合成数据给物理生成过程先验——先验越强，需要的真实数据越少。
- **数量级心算是免费的说服力**：车队原始数据是百 TB/天量级，训练读取吞吐是几百 MB/s 量级，
  两个数字能瞬间判断「要不要为了这个过度设计分布式存储」。

下一站：**模块 03 · 建模与评测设计** —— 数据系统就位之后，
下一个最容易在面试里丢分的地方，是跳过 baseline 直接谈架构新颖度。"""),
]
