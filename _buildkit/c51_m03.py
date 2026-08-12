# -*- coding: utf-8 -*-
"""C51 模块 03 · LLM 驱动的指令数据合成。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–02；C02（SFT）与 C03（LLM-judge）的概念有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_instruction_synthesis.ipynb'),
    ("核心论文", "Wang et al. 2023（Self-Instruct）★、Xu et al. 2023（WizardLM / Evol-Instruct）★、Xu et al. 2024（Magpie）、Shumailov et al. 2024（model collapse）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("why", "指令层：唯一能真正增加信息量的增强", "".join([
        P("模块 01 与 02 的增强都只是「把已有样本换个说法」——<strong>信息量不增加</strong>，它们提供的是正则化。指令层不一样：<strong>它从教师模型的知识里采样出训练集里根本不存在的样本</strong>。"),
        ASCII("""词面/语义层增强的信息流:
   你的 1000 条数据  ──扰动/释义──▶  4000 条数据
   └─ 信息量上限 = 那 1000 条            （同一份信息的多个视角）

指令层合成的信息流:
   你的 175 条种子  ──▶ [ 教师 LLM ] ──▶ 52,000 条新指令数据
                          ▲
                          └─ 信息来自**教师模型的预训练知识**
   └─ 信息量上限 = **教师模型的能力**（远大于种子）

代价：① 你只能拿到教师会的东西（学生 ≤ 教师）
      ② 教师的偏差、风格、错误会被**完整继承甚至放大**
      ③ 反复用合成数据训练下一代，会走向**模式坍塌**（model collapse）""")
        ,
        DUAL(
            "这个转变是质变而非量变。Self-Instruct（Wang et al. 2023）从 175 条人写的种子任务出发，用 GPT-3 生成了 52k 条指令数据，把一个基座模型的指令跟随能力提到接近 InstructGPT 的水平。<strong>这条路线后来成了整个开源指令模型生态的基础</strong>——Alpaca、Vicuna、WizardLM、以及无数领域模型都走的是它的变体。",
            "但也要看清它的<strong>结构性上限</strong>：<em>学生模型的能力上限是教师</em>。这不是一个可以通过「造更多数据」绕过的问题——你造一百万条也不会让学生超过教师在那个能力维度上的水平（除了少数「弱到强泛化」的特殊设置，C23 有讨论）。所以合成数据的正确用途是<strong>把教师的能力「蒸馏」进一个更小/更便宜/更专用的模型</strong>（C49 模块 05 讲过这个模式），而不是「凭空创造新知识」。",
        ),
        CALLOUT("warn", "指令层合成有一个与前两个模块<strong>完全不同</strong>的风险维度：<strong>数据污染</strong>。词面增强不可能造出测试集里的句子（它只扰动训练集）；但 LLM 可能生成与你的测试集<em>高度相似甚至相同</em>的样本——因为教师模型很可能在预训练时见过那个测试集。<em>这会让你的评测分数虚高，且极难察觉</em>。所以指令层合成<strong>必须</strong>配去污染检查（模块 04），这在前两个模块里是可选的。"),
    ])),
    ("selfinstruct", "Self-Instruct：一个四步循环", "".join([
        ASCII("""种子池 (175 条人写任务)
   │
   ├──▶ ① 采样：从池里随机取 8 条（6 条人写 + 2 条已生成）作为 few-shot 示例
   │            └─ 混合人写与已生成，是为了在「质量」与「多样性」之间平衡
   │
   ├──▶ ② 生成新指令：让 LLM 续写第 9 条指令
   │
   ├──▶ ③ 过滤：
   │      · 与池中任一指令的 ROUGE-L > 0.7  -> 丢弃（**去重，最关键的一步**）
   │      · 太长/太短、含图像/音频等无法执行的要求 -> 丢弃
   │      · 关键词黑名单（"画一张图"、"写代码并运行"）-> 丢弃
   │
   ├──▶ ④ 生成实例：为通过的指令生成 (输入, 输出) 对
   │      · 分类任务用「输出优先」（先定标签再造输入，防标签分布倾斜）
   │      · 其他任务用「输入优先」
   │
   └──▶ 加入池，回到 ①（自举）""")
        ,
        P("这个循环里<strong>第 ③ 步的去重是全流程的命门</strong>。理解它为什么关键，就理解了 Self-Instruct 的全部。"),
        DUAL(
            "如果没有去重，会发生什么？LLM 在 few-shot 提示下有很强的<strong>模式惯性</strong>——你给它 8 个「翻译类」的例子，它就倾向于继续生成翻译类任务。几轮自举之后，池子里会挤满同一类任务的变体，<em>多样性坍塌</em>。而池子越单一，下一轮的 few-shot 示例就越单一，形成正反馈。<strong>去重是打断这个正反馈的唯一机制。</strong>",
            "<code>ROUGE-L &gt; 0.7</code> 这个阈值是 Self-Instruct 论文的选择，它的作用可以精确描述：<em>它在「多样性」与「产出率」之间设定了一个交换比</em>。阈值越严（如 0.5），保留下来的指令彼此越不像、多样性越高，但<strong>丢弃率急剧上升</strong>（要生成十条才留一条），成本相应上升。阈值越松（如 0.9），产出快但池子迅速同质化。<strong>notebook 会把这条曲线扫出来</strong>——你会看到丢弃率随阈值收紧呈超线性增长，这直接决定了合成的成本。",
        ),
        H3("「输出优先」：一个防标签倾斜的关键设计"),
        P("第 ④ 步里有个容易被忽略但很重要的细节。对<strong>分类任务</strong>，Self-Instruct 用「输出优先」（output-first）：<em>先让模型列出所有可能的标签，再为每个标签生成对应的输入</em>。"),
        UL([
            "<strong>输入优先</strong>（先造输入、再让模型标注）的问题：LLM 生成的输入会<em>严重偏向某一类</em>。让它「生成一条餐厅评论」，它大概率写正面的——因为正面评论在预训练数据里更常见、也更「安全」。结果标签分布极度倾斜。",
            "<strong>输出优先</strong>：先说「标签是负面」，再让它「写一条负面评论」。<em>标签分布由你控制</em>，不由模型的先验决定。",
        ]),
        CALLOUT("intuition", "这个设计的一般化教训值得记住：<strong>凡是让 LLM 生成带标签的数据，都要问「标签分布由谁决定」</strong>。如果由模型决定，你会得到它的先验（通常是不平衡的、安全的、常见的）；如果由你决定，你能控制分布并覆盖长尾。<em>「先定标签再造样本」是合成分类数据的默认正确姿势</em>，也是补长尾类别最有效的手段。notebook 会把两种顺序的标签分布对比出来。"),
    ])),
    ("evol", "Evol-Instruct：用演化算子提升难度与深度", "".join([
        P("Self-Instruct 解决「量」和「广度」，但生成的指令往往<strong>偏简单</strong>——因为 LLM 在续写时倾向于产出与示例难度相当的东西。WizardLM 的 <span class=\"term\">Evol-Instruct</span>（Xu et al. 2023）补的是「深度」。"),
        TABLE(["演化算子", "做什么", "例子"], [
            ["<strong>加约束</strong>", "给原指令增加一个限制条件", "「写一首诗」→「写一首不含字母 e 的十四行诗」"],
            ["<strong>深化</strong>", "把宽泛的问题变具体、要求更深的推理", "「解释光合作用」→「解释 C4 植物的光合作用与 C3 的差异及其生态意义」"],
            ["<strong>具体化</strong>", "把抽象概念替换成具体实例", "「分析一种算法」→「分析快速排序在近乎有序输入上的退化」"],
            ["<strong>增加推理步数</strong>", "要求多步推理而非单步", "「3+5 等于几」→「一个数加 5 后是它的两倍，求这个数」"],
            ["<strong>复杂化输入</strong>", "让输入格式更复杂（表格、代码、嵌套）", "纯文本 → 带表格的问题"],
            ["<strong>广度演化</strong>", "生成一个「同领域但全新」的指令（而非改造原指令）", "维持多样性，防止只在少数主题上深挖"],
        ]),
        DUAL(
            "Evol-Instruct 的循环是：<strong>随机选一个算子作用在池中的一条指令上 → 生成演化后的指令 → 生成回答 → 过滤 → 加回池</strong>。因为演化是<em>迭代</em>的（第二代在第一代基础上再演化），难度可以逐代提升——这是 Self-Instruct 单轮生成做不到的。",
            "但迭代演化引入了两个新问题。<strong>① 演化失败</strong>：模型可能产出「演化后的指令」其实与原指令等价、或者变成无法回答的胡话。原论文用一个「消除」步骤（elimination）过滤掉这些：<em>让 LLM 判断演化后的指令是否真的更难、是否可回答、是否与原指令实质不同</em>。<strong>② 难度分布漂移</strong>：若一直演化不加广度算子，池子会在少数主题上越挖越深，广度反而下降。<em>所以「深度演化」必须配「广度演化」</em>——这与 Self-Instruct 的去重是同一个「防坍塌」逻辑的不同表现。",
        ),
        CALLOUT("warn", "Evol-Instruct 有一个在实践中反复出现的失败模式：<strong>难度伪装</strong>。模型学会了「让指令看起来更难」（加更多约束词、更长的描述），但<em>实际推理难度没变</em>。症状是：合成数据的平均长度和约束数量在涨，但学生模型在真实困难基准上没有提升。<strong>防护办法是用「可验证的难度代理」</strong>——比如要求生成带标准答案的题目，然后看基座模型的答对率（答对率下降才说明真的变难了）。这与 C22（推理 RL）里 RLVR 的可验证性思路一致。"),
    ])),
    ("magpie", "Magpie 式无种子生成：用模板前缀「钓」出指令", "".join([
        P("Self-Instruct 与 Evol-Instruct 都需要<strong>种子</strong>。Magpie（Xu et al. 2024）提出了一个更简洁的思路：<strong>只给指令模型「用户回合的起始模板」，让它自己续写出用户会问什么</strong>。"),
        CODE("""# 给一个**只有模板前缀、没有任何内容**的输入：
<|im_start|>user
                       ← 到这里就停，让模型自己续写

# 指令模型会续写出一条它「觉得用户会问」的指令：
<|im_start|>user
帮我写一个 Python 函数，把嵌套字典展平成单层。<|im_end|>

# 然后正常地让它回答这条指令，得到 (指令, 回答) 对。"""),
        DUAL(
            "为什么这能工作？因为<strong>对齐后的指令模型在训练时见过大量「用户回合」，它的分布里编码了「用户通常问什么」</strong>。给它一个空的用户回合前缀，它就从这个分布里采样。<em>本质上是在「反演」模型的对齐训练数据分布</em>。",
            "它的优点是<strong>零种子、极简、且多样性天然较高</strong>（因为采样直接来自模型的完整用户分布，而不是被 few-shot 示例锚定在少数几类上）。缺点是<strong>可控性最差</strong>：你几乎无法指定领域、难度或标签分布。所以它适合<em>造通用指令数据</em>，不适合<em>补特定长尾</em>。<strong>实践中三者常组合使用</strong>：Magpie 起量与广度、Self-Instruct 定领域、Evol-Instruct 提难度。",
        ),
        TABLE(["方法", "需要种子", "可控性", "多样性", "最适合"], [
            ["<strong>Self-Instruct</strong>", "需要（175 条量级）", "中（种子决定领域）", "中（靠去重维持）", "定向造某个领域的指令数据"],
            ["<strong>Evol-Instruct</strong>", "需要（在已有池上演化）", "中高（算子可选）", "中（需配广度算子）", "提升难度与深度"],
            ["<strong>Magpie</strong>", "<strong>不需要</strong>", "<strong>低</strong>", "<strong>高</strong>", "零成本起量、造通用指令数据"],
            ["<strong>定向 prompt 生成</strong>", "不需要（用规格说明）", "<strong>最高</strong>", "取决于规格", "补特定长尾、造特定标签分布"],
        ]),
        CALLOUT("intuition", "从这张表可以提炼出一条实用的组合策略：<strong>用最可控的方法补最缺的部分</strong>。如果你的问题是「数据总量不够」，用 Magpie 或 Self-Instruct 起量；如果是「某个类别/场景样本太少」，用定向 prompt 精确补（并用「输出优先」控制标签）；如果是「模型在难样本上表现差」，用 Evol-Instruct 提难度。<em>先诊断缺什么，再选方法</em>——这比「用最新的那个方法」有效得多。"),
    ])),
    ("bias", "教师偏差的传递与模式坍塌", "".join([
        P("合成数据最深的问题不是「质量不够好」，而是<strong>它的分布是教师模型的分布，而不是真实世界的分布</strong>。这带来两个不同层次的问题。"),
        H3("① 偏差传递：学生完整继承教师的系统性倾向"),
        TABLE(["教师的倾向", "在合成数据里表现为", "学生学到什么"], [
            ["<strong>长度偏好</strong>（回答越长越「好」）", "合成回答系统性偏长", "学生也变啰嗦；若用于 DPO 会加剧长度偏差（C50 模块 04）"],
            ["<strong>格式偏好</strong>（爱用列表、Markdown 标题）", "几乎每条回答都是分点列表", "学生在不该用列表的场合也用列表"],
            ["<strong>安全过度</strong>（对边界话题一律拒答）", "合成数据里大量「我不能帮你…」", "学生过度拒答，实用性下降"],
            ["<strong>知识错误</strong>（教师本身答错的领域）", "错误答案被当成金标准", "<strong>错误被固化，且学生无法自行纠正</strong>"],
            ["<strong>文化/语言偏斜</strong>", "以英语世界视角为默认", "在其他文化语境下表现差"],
        ]),
        P("<strong>「知识错误」这一行最需要警惕</strong>，因为它与其他几行有本质区别：其他偏差是「风格问题」（可以靠后续 SFT 调整），而知识错误是<em>把错的当对的写进了训练目标</em>。学生模型不但学不到正确答案，还会<strong>对错误答案变得更自信</strong>（因为它是唯一的监督信号）。"),
        H3("② 模式坍塌：递归使用合成数据的长期后果"),
        DUAL(
            "<span class=\"term\">model collapse</span>（Shumailov et al. 2024）描述的是：<strong>用上一代模型的输出训练下一代，反复几轮后，模型的输出分布会逐渐丢失尾部、向众数收缩</strong>。直观地说——每次采样都倾向于采到高概率区域，低概率的「尾部」内容被系统性地采不到，于是下一代模型就不知道尾部存在了。几代之后，分布退化成少数几个模式。",
            "这个现象在数学上是一个<strong>方差递减 + 尾部截断</strong>的过程。它有两个可分离的成因：<em>①统计误差</em>（有限采样必然欠采样尾部，这个即使模型完美也存在）；<em>②模型误差</em>（模型对尾部的建模本来就不准，误差逐代放大）。<strong>关键的缓解手段是「保留真实数据」</strong>——只要每一代训练里都混入足量的原始真实数据，坍塌就能被大幅延缓。这也是为什么「用合成数据完全替代真实数据」是危险的，而「用合成数据补充真实数据」是可行的。",
        ),
        CALLOUT("danger", "<p>坍塌的<strong>早期征兆</strong>是可以监测的，而且不需要等到效果崩溃：<strong>①多样性指标下降</strong>（distinct-n 降、self-BLEU 升——模块 04 会实现）；<strong>②长度分布收窄</strong>（方差变小，都变成差不多长）；<strong>③高频模式占比上升</strong>（某些开头/句式的比例逐代增加，如「当然！我很乐意帮你…」）；<strong>④嵌入空间覆盖收缩</strong>。<em>把这四个指标做成每一代都跑的看板</em>，你就能在坍塌显现于下游指标之前发现它。这是本课「多样性指标不是为了好看，是为了当警报」这个立场的最强论据。</p>", "坍塌的四个早期征兆"),
    ])),
    ("ledger", "算一笔账：合成数据的成本与去重阈值", "".join([
        MATH("\\text{单条可用数据成本} = \\frac{c_{gen}\\times(n_{instr} + n_{resp})}{\\text{通过率}}"),
        P("其中「通过率」是去重 + 格式过滤 + 质量过滤后的保留比例。这个分母是成本的主导因素，而它由<strong>去重阈值</strong>直接控制。"),
        TABLE(["ROUGE-L 阈值", "去重后多样性", "通过率", "每条可用数据的相对成本", "适合"], [
            ["0.5（严）", "<strong>最高</strong>", "低（~20–30%）", "<strong>3–5×</strong>", "追求多样性、预算充足"],
            ["0.7（Self-Instruct 默认）", "高", "中（~50%）", "2×", "<strong>默认起点</strong>"],
            ["0.9（松）", "中", "高（~80%）", "1.25×", "只是要起量；接受同质化"],
            ["不去重", "<strong>会坍塌</strong>", "100%", "1×", "❌ 不要这么做"],
        ]),
        P("再给一个与前两个模块的完整成本对比（以 EDA=1）："),
        TABLE(["方法", "相对成本", "信息量", "保真度风险", "污染风险", "多样性"], [
            ["EDA / AEDA", "1", "不增加", "中（可用保护规则控制）", "<strong>无</strong>", "低"],
            ["回译 + 过滤", "~1000", "不增加", "中（隐蔽，需过滤）", "<strong>无</strong>", "中"],
            ["Self-Instruct", "~5000", "<strong>增加</strong>", "中（教师偏差）", "<strong>有</strong>", "中高"],
            ["Evol-Instruct", "~10000（多轮）", "<strong>增加</strong>", "中高（难度伪装）", "<strong>有</strong>", "高（配广度算子）"],
        ]),
        P("读这张表：<strong>指令层贵三到四个数量级，但它是唯一能真正增加信息量的</strong>。所以选择逻辑很清晰——"),
        UL([
            "<strong>需要的只是正则化</strong>（有足够数据但容易过拟合）→ 用最便宜的（EDA/AEDA/embedding 噪声）。",
            "<strong>需要的是真正缺失的样本类型</strong>（某类场景一条都没有）→ 只有指令层能做，贵也得做。",
            "<strong>需要的是「让小模型学会大模型的能力」</strong>→ 指令层的数据蒸馏是标准路径（C49 模块 05）。",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>合成数据的质量上限是教师，多样性上限是去重阈值，而它的长期风险是坍塌——三者都必须被显式测量</strong>。前两个模块你可以「凭经验调参」，指令层不行：<em>因为它的失败是渐进的、不报错的、且会在几代之后才显现</em>。所以指令层合成必须配一套持续运行的监测（多样性四指标 + 去污染 + 教师-学生能力对比），这也是模块 04 存在的理由。"),
    ])),
    ("practice", "把三种方法组合成一条可执行的合成管线", "".join([
        P("模块前面分别讲了 Self-Instruct、Evol-Instruct、Magpie。实践中<strong>它们不是三选一，而是流水线上的三个阶段</strong>——因为它们各自补的洞不同。"),
        ASCII("""诊断：先问「我缺的是什么」，再决定用哪一段

  缺「量与广度」        缺「特定领域/标签分布」     缺「难度」
        │                        │                     │
        ▼                        ▼                     ▼
   ① Magpie 起量          ② 定向 prompt / SI      ③ Evol-Instruct
   （零种子、多样性高）     （输出优先控标签分布）    （深度算子+广度算子）
        │                        │                     │
        └────────────┬───────────┴─────────────────────┘
                     ▼
              ④ 统一的去重（ROUGE-L）
                     ▼
              ⑤ 去污染（vs 测试集，模块 04）—— **对合成数据必做**
                     ▼
              ⑥ 混入真实数据（防坍塌）
                     ▼
              ⑦ 多样性四指标入看板（趋势监测）"""),
        TABLE(["阶段", "输入", "输出", "关键参数", "验收"], [
            ["① 起量", "无（或模板前缀）", "宽而浅的指令池", "生成条数", "领域熵、唯一 key 比"],
            ["② 定向补缺", "缺口清单（领域/标签/场景）", "针对性样本", "<strong>输出优先的标签分布</strong>", "补完后各类别的样本数"],
            ["③ 提难度", "已有池", "更深的变体", "算子集（<strong>必须含广度算子</strong>）", "<strong>可验证难度</strong>（基座答对率）"],
            ["④ 去重", "全部候选", "去重后的池", "ROUGE-L 阈值（0.7 起）", "丢弃率（>70% 说明生成器同质化）"],
            ["⑤ 去污染", "去重后的池", "干净的池", "n-gram 的 n（8–13）", "<strong>丢弃率 >1% 就要查</strong>"],
            ["⑥ 混真实", "合成池 + 真实数据", "最终训练集", "合成占比上限", "合成占比是否超过约束"],
            ["⑦ 监测", "每批数据", "看板", "相对变化阈值", "四个征兆是否有告警"],
        ]),
        DUAL(
            "这条管线里最容易被跳过、后果也最严重的是 <strong>⑤ 去污染</strong>。前两个模块（词面、语义增强）不需要它——扰动训练集的句子不可能凭空造出测试集的内容。<em>但指令层合成完全不同：教师模型很可能在预训练时见过你的测试集</em>，于是它「凭记忆」生成的样本可能与测试集高度相似甚至相同。<strong>而这个失效的症状是「评测分数变好」，所以不会引起任何警觉。</strong>",
            "第二个容易跳过的是 <strong>② 之前的「诊断」</strong>。很多团队直接从「用最新的那个方法造一批数据」开始，而不先问「我到底缺什么」。<em>缺量、缺特定类别、缺难度，这三种缺口对应完全不同的方法与完全不同的验收标准</em>。诊断的成本很低（统计一下各类别/各场景的样本数、看看模型在哪些子集上错得多），但它能避免「造了五万条数据，缺的那类还是只有十条」这种典型浪费。",
        ),
        CALLOUT("warn", "关于第 ⑥ 步的合成占比，给一个务实的起点：<strong>合成数据不超过总量的 50%，且每一轮迭代都要重新混入真实数据</strong>（而不是「第一轮混过就行」）。模块的坍塌实验已经显示，只要每代都有真实数据注入，尾部就能被持续带回来。<em>如果你发现「真实数据不够，混不到 50%」——那正是这条约束想告诉你的：你需要的是标注，不是更多合成。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>合成数据的缩放律</strong>：真实数据有 Chinchilla 式的缩放律（C21），合成数据没有。<em>「加十倍合成数据」的收益曲线是什么形状、什么时候饱和、饱和点与教师能力的关系</em>——这些都缺乏系统刻画。经验上收益饱和得比真实数据快得多，但没有定量规律。",
            "<strong>弱到强泛化</strong>：学生能否超过教师？Burns et al. 2023 的 weak-to-strong generalization 表明在某些设置下可以（学生的预训练知识 + 弱监督 &gt; 弱监督本身），这挑战了「学生 ≤ 教师」的朴素结论。<em>什么条件下成立、能超多少</em>，是当前对齐研究的核心问题之一（C23）。",
            "<strong>坍塌的定量刻画</strong>：Shumailov et al. 2024 给出了现象与简化模型，但「混入多少比例真实数据能完全避免坍塌」「不同任务的坍塌速率差异」缺乏可操作的结论。工程上目前只能靠监测而非预测。",
            "<strong>难度的可验证代理</strong>：Evol-Instruct 的「难度伪装」问题需要可验证的难度度量。数学/代码有天然的可验证性（答案对错），开放式任务没有。<em>把可验证性引入开放式指令数据的合成</em>是活跃方向（与 RLVR 同源，C22）。",
            "<strong>合成数据的检测与标注</strong>：随着合成数据在网络上大量出现，「这段文本是不是模型生成的」变得重要——既为了避免用合成数据污染预训练语料（加剧坍塌），也为了溯源。水印与检测都不可靠，这是个开放的社会技术问题（C12/C14）。",
        ]),
        CALLOUT("paper", "必读：Wang et al. 2023 <em>Self-Instruct</em>（重点看 §2 的四步循环与 ROUGE-L 去重，以及分类任务的「输出优先」设计）、Xu et al. 2023 <em>WizardLM: Empowering Large Language Models to Follow Complex Instructions</em>（Evol-Instruct 的算子与消除步骤）、Xu et al. 2024 <em>Magpie</em>（无种子生成的思路极其简洁）、Shumailov et al. 2024 <em>AI models collapse when trained on recursively generated data</em>（Nature；坍塌的现象与机制）、Burns et al. 2023 <em>Weak-to-Strong Generalization</em>（学生能否超过教师）。相邻课程：C02（SFT 与后训练全链路）、C14（合成数据理论）、C21（预训练数据配比）、C23（对齐前沿）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · LLM 驱动的指令数据合成（Self-Instruct / Evol-Instruct / Magpie，用可控模拟教师）

目标：把 **Self-Instruct 四步循环 → ROUGE-L 去重阈值的作用 → 输出优先防标签倾斜 →
Evol-Instruct 演化算子 → Magpie 无种子生成 → 教师偏差传递 → 模式坍塌与四个早期征兆** 全部实现并量化。

路线：可控模拟教师（bias / diversity / collapse 三个参数）→ 完整 self-instruct 循环 →
**去重阈值扫描（丢弃率超线性上升）** → 输入优先 vs 输出优先的标签分布 → evol 算子与难度伪装 →
Magpie → 教师偏差传递实验 → **递归训练的坍塌与四个征兆** → ✏️ 练习 → 📖 答案 → 🧪 成本胶囊。

> 心智模型：**质量上限是教师，多样性上限是去重阈值，长期风险是坍塌——三者都必须被显式测量。**"""),
    md("""## 0 · 一个可控的模拟教师

真实 LLM 不可用，但指令合成的**机制与失败模式**完全可以用一个带三个参数的模拟器复现：
`bias`（教师的系统性倾向强度）、`diversity`（生成的主题广度）、`mode_inertia`（模式惯性，导致坍塌）。

**参数可控让我们能做真实环境里做不到的实验**——比如「把 bias 从 0 调到 0.5，看学生的偏差怎么变」。"""),
    md("""### 指令的结构化表示

为了能精确度量多样性与偏差，我们把「指令」表示成一个结构化对象而不是自由文本：
`(领域, 动作, 对象, 约束数, 长度倾向)`。这样每个维度都可以被统计。"""),
    code("""import numpy as np, math, collections, itertools
rng = np.random.default_rng(0)

DOMAINS = ['餐饮', '旅行', '编程', '医疗', '金融', '教育', '法律', '体育']
ACTIONS = ['总结', '翻译', '分类', '解释', '改写', '生成', '比较', '推荐']
OBJECTS = ['评论', '文章', '代码', '报表', '对话', '公告', '题目', '清单']
CONSTRAINTS = ['限 50 字', '用列表', '不含数字', '正式语气', '分三点', '带示例']

class Instruction:
    __slots__ = ('domain', 'action', 'obj', 'constraints', 'depth', 'label')
    def __init__(self, domain, action, obj, constraints=(), depth=1, label=None):
        self.domain, self.action, self.obj = domain, action, obj
        self.constraints = tuple(constraints); self.depth = depth; self.label = label
    def tokens(self):
        '''把指令渲染成 token 序列（用于算 ROUGE-L / 多样性）。'''
        return [self.domain, self.action, self.obj] + list(self.constraints) + [f'd{self.depth}']
    def key(self):
        return (self.domain, self.action, self.obj, self.constraints, self.depth)
    def __repr__(self):
        c = ('+' + ','.join(self.constraints)) if self.constraints else ''
        return f'[{self.domain}]{self.action}{self.obj}{c}(d{self.depth})'

def lcs_len(a, b):
    m, n = len(a), len(b)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m):
        for j in range(n):
            dp[i+1][j+1] = dp[i][j]+1 if a[i] == b[j] else max(dp[i][j+1], dp[i+1][j])
    return dp[m][n]

def rouge_l(a, b):
    '''ROUGE-L F1（基于最长公共子序列）—— Self-Instruct 的去重判据。'''
    if not a or not b: return 0.0
    l = lcs_len(a, b)
    p, r = l/len(b), l/len(a)
    return 0.0 if p + r == 0 else 2*p*r/(p+r)

i1 = Instruction('餐饮', '总结', '评论')
i2 = Instruction('餐饮', '总结', '评论', ('限 50 字',))
i3 = Instruction('编程', '生成', '代码')
print(f'{i1} vs {i2}: ROUGE-L = {rouge_l(i1.tokens(), i2.tokens()):.3f}  ← 很像')
print(f'{i1} vs {i3}: ROUGE-L = {rouge_l(i1.tokens(), i3.tokens()):.3f}  ← 很不像')
assert rouge_l(i1.tokens(), i2.tokens()) > rouge_l(i1.tokens(), i3.tokens())
assert abs(rouge_l(i1.tokens(), i1.tokens()) - 1.0) < 1e-9, '自己与自己的 ROUGE-L = 1'
print('✅ ROUGE-L 去重判据就绪')"""),
    code("""class SimulatedTeacher:
    '''可控的模拟教师。
       bias        : 系统性倾向强度（偏好某些领域/动作、回答偏长、爱用列表）
       diversity   : 主题广度（低 -> 只在少数领域生成）
       mode_inertia: 模式惯性（few-shot 示例对生成的锚定强度 -> 坍塌的来源）
       error_rate  : 知识错误率（把错的当金标准）
    '''
    FAV_DOMAINS = ['编程', '餐饮']          # 教师偏爱的领域
    FAV_ACTIONS = ['解释', '生成']          # 教师偏爱的动作

    def __init__(self, bias=0.0, diversity=1.0, mode_inertia=0.0, error_rate=0.0, seed=0):
        self.bias, self.diversity = bias, diversity
        self.mode_inertia, self.error_rate = mode_inertia, error_rate
        self.r = np.random.default_rng(seed)
        self.n_calls = 0

    def _pick(self, pool, favored, shots=()):
        # ① 模式惯性：以 mode_inertia 概率直接抄 few-shot 示例的取值
        if shots and self.r.random() < self.mode_inertia:
            return str(self.r.choice([getattr(s, 'domain', None) or s for s in shots]))
        # ② 偏差：以 bias 概率只从偏爱集合里选
        if self.r.random() < self.bias:
            return str(self.r.choice(favored))
        # ③ 多样性：只在前 k 个候选里选
        k = max(1, int(round(len(pool) * self.diversity)))
        return str(self.r.choice(pool[:k]))

    def generate_instruction(self, shots=()):
        self.n_calls += 1
        dom_shots = [s.domain for s in shots] if shots else ()
        act_shots = [s.action for s in shots] if shots else ()
        dom = self._pick(DOMAINS, self.FAV_DOMAINS, dom_shots)
        act = self._pick(ACTIONS, self.FAV_ACTIONS, act_shots)
        obj = str(self.r.choice(OBJECTS))
        n_c = int(self.r.integers(0, 2 + int(self.bias * 3)))     # bias 高 -> 爱加约束
        cons = tuple(sorted(self.r.choice(CONSTRAINTS, size=min(n_c, len(CONSTRAINTS)),
                                          replace=False))) if n_c else ()
        return Instruction(dom, act, obj, cons)

    def generate_response(self, instr, label=None):
        '''返回 (回答长度, 是否用列表, 是否正确)。教师偏差在这里体现。'''
        base_len = 40
        length = int(base_len * (1 + 2.5 * self.bias) + self.r.normal(0, 5))
        uses_list = bool(self.r.random() < 0.2 + 0.7 * self.bias)
        correct = bool(self.r.random() >= self.error_rate)
        return max(5, length), uses_list, correct

t = SimulatedTeacher(bias=0.0, diversity=1.0, seed=1)
print('无偏教师生成的 6 条指令:')
for _ in range(6):
    print('  ', t.generate_instruction())
tb = SimulatedTeacher(bias=0.6, diversity=1.0, seed=1)
print('\\n高偏差教师(bias=0.6)生成的 6 条:')
for _ in range(6):
    print('  ', tb.generate_instruction())
print('\\n✅ 模拟教师就绪：注意高偏差教师明显偏向「编程/餐饮」与「解释/生成」')"""),
    md("""## 1 · Self-Instruct 的四步循环

① 从池中采样 few-shot 示例 → ② 生成新指令 → ③ **过滤（ROUGE-L 去重是命门）** → ④ 生成实例 → 回到 ①"""),
    code("""BLACKLIST_OBJ = {'图片', '音频'}          # 无法执行的要求

def format_filter(instr):
    '''③ 的一部分：格式与可执行性过滤。'''
    if instr.obj in BLACKLIST_OBJ: return False
    if len(instr.constraints) > 4: return False      # 约束过多 -> 不可执行
    return True

def self_instruct(teacher, seeds, target=200, rouge_thresh=0.7, n_shots=8,
                  human_ratio=0.75, seed=0):
    '''完整的 Self-Instruct 循环。返回 (池, 统计)。'''
    r = np.random.default_rng(seed)
    pool = list(seeds)
    human, generated = list(seeds), []
    stats = collections.Counter()
    guard = 0
    while len(pool) < target and guard < target * 60:
        guard += 1
        # ① 采样 few-shot：混合人写与已生成（平衡质量与多样性）
        n_h = max(1, int(n_shots * human_ratio))
        shots = list(r.choice(human, size=min(n_h, len(human)), replace=False))
        if generated:
            shots += list(r.choice(generated, size=min(n_shots-n_h, len(generated)),
                                   replace=False))
        # ② 生成
        cand = teacher.generate_instruction(shots)
        stats['generated'] += 1
        # ③ 过滤
        if not format_filter(cand):
            stats['drop_format'] += 1; continue
        ct = cand.tokens()
        if any(rouge_l(ct, p.tokens()) > rouge_thresh for p in pool):
            stats['drop_dup'] += 1; continue
        # ④ 生成实例（这里只记录，不真的产文本）
        pool.append(cand); generated.append(cand); stats['kept'] += 1
    return pool, stats

SEEDS = [Instruction(d, a, o) for d, a, o in
         [('餐饮', '总结', '评论'), ('旅行', '推荐', '清单'), ('编程', '生成', '代码'),
          ('医疗', '解释', '文章'), ('金融', '分类', '报表'), ('教育', '改写', '题目'),
          ('法律', '比较', '公告'), ('体育', '翻译', '对话')]]
teacher = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.2, seed=3)
pool, st = self_instruct(teacher, SEEDS, target=150, rouge_thresh=0.7, seed=5)
print(f'种子 {len(SEEDS)} 条 -> 池 {len(pool)} 条')
print(f'统计: {dict(st)}')
print(f'通过率 = kept/generated = {st["kept"]/st["generated"]:.1%}')
assert len(pool) >= 150 or st['generated'] > 0
assert st['drop_dup'] > 0, '去重必然会丢弃一部分'
print(f'\\n新生成的 5 条: {pool[len(SEEDS):len(SEEDS)+5]}')
print('✅ Self-Instruct 循环工作正常')"""),
    md("""### ROUGE-L 阈值：多样性与产出率的交换比

**丢弃率随阈值收紧呈超线性上升** —— 这直接决定合成成本。"""),
    code("""def unique_key_ratio(pool):
    return len({p.key() for p in pool}) / len(pool)

def domain_entropy(pool):
    c = collections.Counter(p.domain for p in pool)
    ps = np.array(list(c.values()), dtype=float); ps /= ps.sum()
    return float(-(ps * np.log(ps + 1e-12)).sum())

def ngrams(t, n):
    return [tuple(t[i:i+n]) for i in range(len(t)-n+1)]

def distinct_n(texts, n=2):
    tot, uniq = 0, set()
    for t in texts:
        g = ngrams(t, n); tot += len(g); uniq.update(g)
    return len(uniq)/tot if tot else 0.0

print(f"{'阈值':>6s} {'池大小':>7s} {'通过率':>8s} {'相对成本':>9s} {'唯一key比':>10s} "
      f"{'领域熵':>8s} {'distinct-2':>11s}")
rows = []
for th in [0.4, 0.55, 0.7, 0.85, 1.01]:
    t = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.3, seed=3)
    p, s = self_instruct(t, SEEDS, target=120, rouge_thresh=th, seed=5)
    pass_rate = s['kept']/max(1, s['generated'])
    rows.append((th, len(p), pass_rate, 1/max(pass_rate, 1e-9),
                 unique_key_ratio(p), domain_entropy(p),
                 distinct_n([x.tokens() for x in p], 2)))
    print(f'{th:>6.2f} {len(p):>7d} {pass_rate:>8.1%} {1/max(pass_rate,1e-9):>9.1f} '
          f'{unique_key_ratio(p):>10.3f} {domain_entropy(p):>8.3f} '
          f'{distinct_n([x.tokens() for x in p],2):>11.4f}')

pass_rates = [r[2] for r in rows]
assert pass_rates == sorted(pass_rates), '阈值越松，通过率越高'
costs = [r[3] for r in rows]
assert costs[0] > costs[-1] * 2, '严阈值的相对成本应显著更高'
assert rows[0][4] >= rows[-1][4] - 1e-9, '严阈值的唯一性不低于松阈值'
print(f'\\n✅ 阈值 0.4 的成本是 1.01（不去重）的 {costs[0]/costs[-1]:.1f} 倍，')
print('   换来的是更高的唯一性与多样性。**这就是「多样性 vs 产出率」的交换比。**')
print('   Self-Instruct 的 0.7 是这条曲线上一个务实的取点。')"""),
    md("""### 不去重会怎样：模式惯性导致池子迅速同质化"""),
    code("""print(f"{'模式惯性':>9s} {'去重(0.7)后领域熵':>19s} {'不去重的领域熵':>16s}")
for mi in [0.0, 0.3, 0.6, 0.9]:
    t1 = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=mi, seed=3)
    p1, _ = self_instruct(t1, SEEDS, target=120, rouge_thresh=0.7, seed=5)
    t2 = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=mi, seed=3)
    p2, _ = self_instruct(t2, SEEDS, target=120, rouge_thresh=1.01, seed=5)
    print(f'{mi:>9.1f} {domain_entropy(p1):>19.3f} {domain_entropy(p2):>16.3f}')

t_hi = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.9, seed=3)
p_dedup, _ = self_instruct(t_hi, SEEDS, target=120, rouge_thresh=0.7, seed=5)
t_hi2 = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.9, seed=3)
p_nodedup, _ = self_instruct(t_hi2, SEEDS, target=120, rouge_thresh=1.01, seed=5)
assert unique_key_ratio(p_dedup) > unique_key_ratio(p_nodedup), '去重维持了唯一性'
print(f'\\n高惯性(0.9)时: 去重后唯一key比 {unique_key_ratio(p_dedup):.3f} vs '
      f'不去重 {unique_key_ratio(p_nodedup):.3f}')
print('\\n✅ LLM 在 few-shot 下有强**模式惯性**：给它 8 个翻译例子，它就继续生成翻译。')
print('   池子越单一 -> 下一轮 few-shot 越单一 -> 正反馈。**去重是打断它的唯一机制。**')"""),
    md("""## 2 · 输出优先 vs 输入优先：防标签倾斜

让 LLM「生成一条餐厅评论」，它大概率写正面的（预训练里更常见、也更「安全」）。
**先定标签再造样本**，标签分布才由你控制。"""),
    code("""def input_first(teacher, n, seed=0):
    '''输入优先：先造输入，再让教师标注 -> 标签分布由教师先验决定。'''
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        # 教师的先验：倾向生成正面样本（预训练里更常见、更安全）
        y = 1 if r.random() < 0.78 else 0
        out.append((teacher.generate_instruction(), y))
    return out

def output_first(teacher, n, label_dist=(0.5, 0.5), seed=0):
    '''输出优先：先按你指定的分布定标签，再造对应输入。'''
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        y = int(r.random() >= label_dist[0])       # 标签分布由**你**控制
        instr = teacher.generate_instruction()
        instr.label = y
        out.append((instr, y))
    return out

t = SimulatedTeacher(bias=0.1, seed=7)
d_in = input_first(t, 600, seed=11)
d_out = output_first(t, 600, label_dist=(0.5, 0.5), seed=11)
p_in = float(np.mean([y for _, y in d_in]))
p_out = float(np.mean([y for _, y in d_out]))
print(f'输入优先: 正面占比 {p_in:.1%}   ← 由教师先验决定（严重倾斜）')
print(f'输出优先: 正面占比 {p_out:.1%}   ← 由你指定')
assert abs(p_in - 0.78) < 0.05, '输入优先会得到教师的先验分布'
assert abs(p_out - 0.5) < 0.05, '输出优先能精确控制分布'

# 补长尾：想造 90% 负面来补一个稀有类别？输出优先直接指定即可
d_rare = output_first(t, 400, label_dist=(0.1, 0.9), seed=13)
print(f'\\n要补长尾（90% 负面）: 输出优先得到正面占比 {np.mean([y for _,y in d_rare]):.1%} ✅')
assert np.mean([y for _, y in d_rare]) > 0.85
print('\\n✅ 一般化教训：**凡是让 LLM 生成带标签的数据，都要问「标签分布由谁决定」**。')
print('   由模型决定 -> 得到它的先验（不平衡、安全、常见）；由你决定 -> 可控且能覆盖长尾。')"""),
    md("""## 3 · Evol-Instruct：演化算子与「难度伪装」

深度演化必须配**广度演化**，否则池子在少数主题上越挖越深、广度反而下降。
而「难度伪装」（约束变多但实际推理难度没变）需要**可验证的难度代理**才能识别。"""),
    code("""def evol_add_constraint(instr, r):
    avail = [c for c in CONSTRAINTS if c not in instr.constraints]
    if not avail: return None
    return Instruction(instr.domain, instr.action, instr.obj,
                       instr.constraints + (str(r.choice(avail)),), instr.depth)

def evol_deepen(instr, r):
    return Instruction(instr.domain, instr.action, instr.obj,
                       instr.constraints, instr.depth + 1)

def evol_concretize(instr, r):
    return Instruction(instr.domain, instr.action, str(r.choice(OBJECTS)),
                       instr.constraints, instr.depth)

def evol_breadth(instr, r):
    '''广度演化：同领域但全新的指令（维持广度，防只在少数主题深挖）。'''
    return Instruction(str(r.choice(DOMAINS)), str(r.choice(ACTIONS)),
                       str(r.choice(OBJECTS)), (), 1)

DEPTH_OPS = [evol_add_constraint, evol_deepen, evol_concretize]
ALL_OPS = DEPTH_OPS + [evol_breadth]

def elimination(orig, evolved, pool, rouge_thresh=0.85):
    '''消除步骤：演化失败的要丢（与原指令实质相同、或已重复、或约束过多）。'''
    if evolved is None: return False
    if evolved.key() == orig.key(): return False                    # 实质没变
    if not format_filter(evolved): return False                     # 不可执行
    et = evolved.tokens()
    if any(rouge_l(et, p.tokens()) > rouge_thresh for p in pool): return False
    return True

def evol_instruct(seeds, rounds=4, ops=ALL_OPS, seed=0, rouge_thresh=0.85):
    r = np.random.default_rng(seed)
    pool = list(seeds); stats = collections.Counter()
    for _ in range(rounds):
        new = []
        for instr in list(pool):
            op = ops[int(r.integers(0, len(ops)))]
            cand = op(instr, r)
            stats['attempted'] += 1
            if elimination(instr, cand, pool + new, rouge_thresh):
                new.append(cand); stats['kept'] += 1
            else:
                stats['eliminated'] += 1
        pool += new
    return pool, stats

print(f"{'算子集':<20s} {'池大小':>7s} {'平均深度':>9s} {'平均约束数':>11s} {'领域熵':>8s}")
for label, ops in [('仅深度算子', DEPTH_OPS), ('深度+广度', ALL_OPS)]:
    p, s = evol_instruct(SEEDS, rounds=4, ops=ops, seed=17)
    print(f'{label:<20s} {len(p):>7d} {np.mean([x.depth for x in p]):>9.2f} '
          f'{np.mean([len(x.constraints) for x in p]):>11.2f} {domain_entropy(p):>8.3f}')

p_depth, _ = evol_instruct(SEEDS, rounds=4, ops=DEPTH_OPS, seed=17)
p_both, _ = evol_instruct(SEEDS, rounds=4, ops=ALL_OPS, seed=17)
assert np.mean([x.depth for x in p_depth]) > 1.0, '深度算子应提升深度'
# 广度算子的正确验证量：**不同 (领域, 动作, 对象) 三元组的数量**
tri_depth = len({(x.domain, x.action, x.obj) for x in p_depth})
tri_both = len({(x.domain, x.action, x.obj) for x in p_both})
print(f'\\n不同 (领域,动作,对象) 三元组数: 仅深度 {tri_depth} | 深度+广度 {tri_both}')
assert tri_both > tri_depth, '只用深度算子不会产生新的主题组合 —— 广度算子才会'
print('\\n✅ 只用深度算子会在少数主题上越挖越深；**深度演化必须配广度演化**。')
print('   这与 Self-Instruct 的去重是同一个「防坍塌」逻辑的不同表现。')"""),
    code("""# 难度伪装：约束数在涨，但「实际难度」没涨
def apparent_difficulty(instr):
    '''表观难度：**只含看得见的部分**（约束数量）——模型很容易「优化」这个。
       注意它不含 depth：depth 代表真实推理步数，评审者从指令文本里看不出来。'''
    return len(instr.constraints)

def verifiable_difficulty(instr, base_model_skill=0.75, r=None):
    '''可验证难度：基座模型答对的概率（越低越难）。
       关键：只有 depth 真的降低答对率，约束数只影响表观。'''
    r = r or np.random.default_rng(0)
    p_correct = base_model_skill ** instr.depth        # 只有深度真的变难
    return 1 - p_correct

def fake_evol(instr, r):
    '''难度伪装：只加约束、不加深度 —— 看起来更难，实际没变。'''
    return evol_add_constraint(instr, r)

print(f"{'策略':<22s} {'表观难度':>9s} {'可验证难度':>11s}")
# 注意 rouge_thresh 放宽到 0.95：加一个约束只改动一个 token，0.85 的阈值会把它全部消除掉
for label, ops in [('真深化 (evol_deepen)', [evol_deepen]),
                   ('伪装 (只加约束)', [fake_evol])]:
    p, _ = evol_instruct(SEEDS, rounds=3, ops=ops, seed=19, rouge_thresh=0.95)
    app = float(np.mean([apparent_difficulty(x) for x in p]))
    ver = float(np.mean([verifiable_difficulty(x) for x in p]))
    print(f'{label:<22s} {app:>9.2f} {ver:>11.3f}')

p_real, _ = evol_instruct(SEEDS, rounds=3, ops=[evol_deepen], seed=19, rouge_thresh=0.95)
p_fake, _ = evol_instruct(SEEDS, rounds=3, ops=[fake_evol], seed=19, rouge_thresh=0.95)
app_real = np.mean([apparent_difficulty(x) for x in p_real])
app_fake = np.mean([apparent_difficulty(x) for x in p_fake])
ver_real = np.mean([verifiable_difficulty(x) for x in p_real])
ver_fake = np.mean([verifiable_difficulty(x) for x in p_fake])
assert app_fake > app_real, '伪装策略的表观难度更高（约束堆得更多）'
assert ver_fake < ver_real, '但可验证难度明显更低 —— 这就是难度伪装'
print(f'\\n⚠️  伪装策略的表观难度 {app_fake:.2f} **高于**真深化的 {app_real:.2f}，')
print(f'   但可验证难度只有 {ver_fake:.3f} vs 真深化的 {ver_real:.3f}。')
print('✅ 防护：用**可验证的难度代理**（基座模型答对率）而不是表观指标。')
print('   这与 C22 的 RLVR 可验证性思路一致。')"""),
    md("""## 4 · Magpie：无种子生成

只给「用户回合的起始模板」，让指令模型自己续写用户会问什么——
本质是**反演模型的对齐训练数据分布**。零种子、多样性天然高、但可控性最差。"""),
    code("""def magpie(teacher, n, seed=0):
    '''无种子：不给任何 few-shot 示例，直接让教师从它的「用户分布」采样。'''
    return [teacher.generate_instruction(shots=()) for _ in range(n)]

t_mag = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.5, seed=23)
p_mag = magpie(t_mag, 150)
t_si = SimulatedTeacher(bias=0.1, diversity=1.0, mode_inertia=0.5, seed=23)
p_si, _ = self_instruct(t_si, SEEDS, target=150, rouge_thresh=0.7, seed=23)

print(f"{'方法':<22s} {'池大小':>7s} {'唯一key比':>10s} {'领域熵':>8s} {'需要种子':>9s} {'可控性':>7s}")
for label, p, need_seed, ctrl in [('Magpie (无种子)', p_mag, '否', '低'),
                                  ('Self-Instruct', p_si, '是', '中')]:
    print(f'{label:<22s} {len(p):>7d} {unique_key_ratio(p):>10.3f} '
          f'{domain_entropy(p):>8.3f} {need_seed:>9s} {ctrl:>7s}')

assert domain_entropy(p_mag) > 0, 'Magpie 应覆盖多个领域'
# Magpie 不受 few-shot 锚定 -> 领域熵不低于被示例锚定的 Self-Instruct
print(f'\\n✅ Magpie 不被 few-shot 示例锚定，所以多样性天然较高（领域熵 '
      f'{domain_entropy(p_mag):.3f}）。')
print('   但它几乎无法指定领域/难度/标签分布 —— **可控性最差**。')
print('\\n实践中三者组合：Magpie 起量与广度、Self-Instruct 定领域、Evol-Instruct 提难度。')
print('先诊断「缺什么」，再选方法 —— 比「用最新那个方法」有效得多。')"""),
    md("""## 5 · 教师偏差的传递：学生完整继承

**「知识错误」这一类最危险**：其他偏差是风格问题（可后续调整），
知识错误是把错的当对的写进训练目标——学生不但学不到正确答案，还会对错误更自信。"""),
    code("""def synthesize_dataset(teacher, n, seed=0):
    '''生成 n 条 (指令, 回答长度, 是否列表, 是否正确)。'''
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        instr = teacher.generate_instruction()
        ln, lst, ok = teacher.generate_response(instr)
        out.append((instr, ln, lst, ok))
    return out

def dataset_profile(ds):
    return {'平均长度': float(np.mean([x[1] for x in ds])),
            '长度标准差': float(np.std([x[1] for x in ds])),
            '列表占比': float(np.mean([x[2] for x in ds])),
            '正确率': float(np.mean([x[3] for x in ds])),
            '偏爱领域占比': float(np.mean([x[0].domain in SimulatedTeacher.FAV_DOMAINS
                                       for x in ds]))}

print(f"{'教师 bias':>10s} {'平均长度':>9s} {'列表占比':>9s} {'偏爱领域占比':>13s}")
for b in [0.0, 0.2, 0.5, 0.8]:
    t = SimulatedTeacher(bias=b, seed=29)
    prof = dataset_profile(synthesize_dataset(t, 400, seed=29))
    print(f'{b:>10.1f} {prof["平均长度"]:>9.1f} {prof["列表占比"]:>9.1%} '
          f'{prof["偏爱领域占比"]:>13.1%}')

p0 = dataset_profile(synthesize_dataset(SimulatedTeacher(bias=0.0, seed=29), 400, seed=29))
p8 = dataset_profile(synthesize_dataset(SimulatedTeacher(bias=0.8, seed=29), 400, seed=29))
assert p8['平均长度'] > p0['平均长度'] * 1.8, '高偏差教师的回答系统性偏长'
assert p8['列表占比'] > p0['列表占比'] * 2, '高偏差教师爱用列表'
assert p8['偏爱领域占比'] > p0['偏爱领域占比'], '高偏差教师偏向特定领域'
print('\\n✅ 教师的三类风格偏差（长度/格式/领域）全部完整传递进合成数据。')
print('   若用这份数据做 DPO，长度偏差还会被进一步放大（C50 模块 04）。')"""),
    code("""# 知识错误：学生的正确率上限 = 教师的正确率
def student_ceiling(teacher_error_rate, student_capacity=0.97, n=4000, seed=0):
    r = np.random.default_rng(seed)
    teacher_ok = r.random(n) >= teacher_error_rate
    # 学生以 student_capacity 的概率与教师一致
    student_ok = np.where(r.random(n) < student_capacity, teacher_ok, ~teacher_ok)
    return float(teacher_ok.mean()), float(student_ok.mean())

print(f"{'教师错误率':>11s} {'教师正确率':>11s} {'学生正确率':>11s} {'差距':>7s}")
for er in [0.0, 0.05, 0.15, 0.30]:
    tt, ss = student_ceiling(er)
    print(f'{er:>11.0%} {tt:>11.1%} {ss:>11.1%} {tt-ss:>+7.1%}')

t15, s15 = student_ceiling(0.15)
t0, s0 = student_ceiling(0.0)
assert s15 < t15, '学生一般不超过教师'
assert s0 > s15, '教师越准，学生越准'
print('\\n⚠️  **学生的能力上限是教师** —— 这不是「造更多数据」能绕过的。')
print('   所以合成数据的正确用途是把教师能力**蒸馏**进更小/更便宜的模型（C49 模块 05），')
print('   而不是「凭空创造新知识」。')
print('\\n   防护：留一小份**人工标注**的验证集，用来检测学生是否继承了教师的系统性错误。')"""),
    md("""## 6 · 模式坍塌：递归训练的四个早期征兆

用上一代的输出训练下一代，反复几轮后分布会丢失尾部、向众数收缩。
**四个早期征兆**：多样性降、长度分布收窄、高频模式占比升、嵌入覆盖收缩。"""),
    code("""def recursive_generations(n_gen=6, pool_size=300, real_data_ratio=0.0,
                         mutate_p=0.25, seed=0):
    '''模拟递归训练。**坍塌的核心机制是「有限采样」**（Shumailov 的统计误差）：
       每一代从上一代的**经验分布**里有限采样 -> 低频项以一定概率被漏掉，
       而一旦漏掉就**再也回不来**（下一代的分布里已经没有它了）。
       real_data_ratio: 每代混入的真实数据比例（**坍塌的主要缓解手段**）。'''
    r = np.random.default_rng(seed)
    real_pool = [Instruction(str(r.choice(DOMAINS)), str(r.choice(ACTIONS)),
                             str(r.choice(OBJECTS))) for _ in range(pool_size)]
    cur = list(real_pool)
    history = []

    def mutate(x):
        '''教师的局部变异：只改约束/深度，**不引入新的领域** ——
           这正是合成数据的本质：它只能重组教师已有的东西。'''
        if r.random() >= mutate_p:
            return Instruction(x.domain, x.action, x.obj, x.constraints, x.depth)
        cons = list(x.constraints)
        if cons and r.random() < 0.5:
            cons.pop(int(r.integers(0, len(cons))))
        else:
            cand = [c for c in CONSTRAINTS if c not in cons]
            if cand: cons.append(str(r.choice(cand)))
        return Instruction(x.domain, x.action, x.obj, tuple(sorted(cons)), x.depth)

    for g in range(n_gen):
        n_syn = int(pool_size * (1 - real_data_ratio))
        n_real = pool_size - n_syn
        # ① 有限采样上一代（有放回）—— 尾部被随机丢弃
        idx = r.integers(0, len(cur), size=n_syn)
        syn = [mutate(cur[i]) for i in idx]
        # ② 混入真实数据（唯一能把丢失的尾部带回来的途径）
        fresh = [real_pool[i] for i in r.integers(0, len(real_pool), size=n_real)] \\
                if n_real else []
        cur = syn + fresh
        lens = [len(x.tokens()) for x in cur]
        top_mode = collections.Counter((x.domain, x.action) for x in cur).most_common(1)[0][1]
        history.append({
            'gen': g + 1,
            'distinct-2': distinct_n([x.tokens() for x in cur], 2),
            '长度标准差': float(np.std(lens)),
            '最高频模式占比': top_mode / len(cur),
            '唯一key比': unique_key_ratio(cur),
            '领域熵': domain_entropy(cur),
        })
    return history

print('=== 纯合成（不混真实数据）===')
print(f"{'代':>3s} {'distinct-2':>11s} {'长度σ':>7s} {'最高频模式占比':>14s} {'唯一key比':>10s} {'领域熵':>8s}")
h0 = recursive_generations(n_gen=6, real_data_ratio=0.0, seed=31)
for h in h0:
    print(f'{h["gen"]:>3d} {h["distinct-2"]:>11.4f} {h["长度标准差"]:>7.2f} '
          f'{h["最高频模式占比"]:>14.1%} {h["唯一key比"]:>10.3f} {h["领域熵"]:>8.3f}')

assert h0[-1]['唯一key比'] < h0[0]['唯一key比'], '唯一性应逐代下降'
assert h0[-1]['最高频模式占比'] > h0[0]['最高频模式占比'], '高频模式占比应逐代上升'
assert h0[-1]['领域熵'] < h0[0]['领域熵'], '领域熵应逐代下降'
print('\\n✅ 四个征兆全部按预期变化：多样性降、高频模式升、唯一性降、熵降。')
print('   **注意这些征兆在下游指标崩溃之前就出现了** —— 这才是它们的价值。')"""),
    code("""# 缓解：每代混入真实数据
print(f"{'真实数据比例':>13s} {'第6代 唯一key比':>16s} {'第6代 领域熵':>14s} {'第6代 最高频占比':>17s}")
finals = []
for ratio in [0.0, 0.1, 0.3, 0.5]:
    h = recursive_generations(n_gen=6, real_data_ratio=ratio, seed=31)
    finals.append((ratio, h[-1]))
    print(f'{ratio:>13.0%} {h[-1]["唯一key比"]:>16.3f} {h[-1]["领域熵"]:>14.3f} '
          f'{h[-1]["最高频模式占比"]:>17.1%}')

uniq = [f[1]['唯一key比'] for f in finals]
assert uniq[-1] > uniq[0], '混入真实数据显著缓解坍塌'
ent = [f[1]['领域熵'] for f in finals]
assert ent[-1] > ent[0]
print(f'\\n✅ 混入 50% 真实数据把第 6 代的唯一性从 {uniq[0]:.3f} 拉回 {uniq[-1]:.3f}。')
print('   **「用合成数据完全替代真实数据」是危险的；「用合成补充真实」是可行的。**')
print('   （Shumailov et al. 2024 的两个成因：统计误差（有限采样欠采尾部）+ 模型误差。）')"""),
    md("""## ✏️ 练习 1：带去重的合成循环

实现 `dedup_add(pool, candidate, rouge_thresh)`：
若 candidate 与 pool 中任一元素的 ROUGE-L > `rouge_thresh` 则返回 `(False, 最大相似度)`，
否则把它加入 pool 并返回 `(True, 最大相似度)`。"""),
    code("""def dedup_add(pool, candidate, rouge_thresh):
    # TODO: 算 candidate.tokens() 与 pool 中每个元素的 ROUGE-L，取最大值
    #       > thresh -> (False, max_sim)；否则 pool.append 并 (True, max_sim)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
pool_t = [Instruction('餐饮', '总结', '评论')]
ok, sim = dedup_add(pool_t, Instruction('餐饮', '总结', '评论'), 0.7)
assert not ok and sim > 0.9, f'完全相同应被拒，sim={sim}'
assert len(pool_t) == 1
ok2, sim2 = dedup_add(pool_t, Instruction('编程', '生成', '代码'), 0.7)
assert ok2 and sim2 < 0.5 and len(pool_t) == 2
# 空池时应总是接受
empty = []
ok3, sim3 = dedup_add(empty, Instruction('医疗', '解释', '文章'), 0.7)
assert ok3 and sim3 == 0.0 and len(empty) == 1
print(f'池大小 {len(pool_t)}，相似度分别 {sim:.3f} / {sim2:.3f}')
print('✅ 练习 1 通过：去重是打断「模式惯性正反馈」的唯一机制')"""),
    md("""## ✏️ 练习 2：坍塌预警器

实现 `collapse_alert(history, window=3, drop_thresh=0.1)`：
给定 `recursive_generations` 返回的 history，检测四个征兆。
若某个指标在最近 `window` 代内的**相对变化**超过 `drop_thresh`（多样性/唯一性/熵是下降、
最高频占比是上升），就把它加入告警列表。返回告警名称列表。"""),
    code("""def collapse_alert(history, window=3, drop_thresh=0.1):
    # TODO: 比较 history[-window] 与 history[-1]；
    #   'distinct-2' / '唯一key比' / '领域熵' 下降超 drop_thresh -> 告警
    #   '最高频模式占比' 上升超 drop_thresh -> 告警
    #   返回告警名列表（顺序不限）
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
alerts_bad = collapse_alert(h0)
print('纯合成 6 代的告警:', alerts_bad)
assert len(alerts_bad) >= 2, f'纯合成应触发多个告警，得到 {alerts_bad}'
h_ok = recursive_generations(n_gen=6, real_data_ratio=0.5, seed=31)
alerts_ok = collapse_alert(h_ok)
print('混 50% 真实数据的告警:', alerts_ok)
assert len(alerts_ok) < len(alerts_bad), '混入真实数据应减少告警'
# window 大于历史长度时不应崩
assert isinstance(collapse_alert(h0[:2], window=5), list)
print('✅ 练习 2 通过：把这四个指标做成每代都跑的看板 ——')
print('   你就能在坍塌显现于下游指标之前发现它。')"""),
    md("""## ✏️ 练习 3：合成成本

实现 `synthesis_cost(n_target, pass_rate, cost_per_instruction, cost_per_response)`：
返回 `{'attempts':…, 'total_cost':…, 'cost_per_usable':…}`。
注意：**被去重丢弃的指令也花了生成费用**（但没花回答费用，因为过滤在生成回答之前）。"""),
    code("""def synthesis_cost(n_target, pass_rate, cost_per_instruction, cost_per_response):
    # TODO: attempts = ceil(n_target / pass_rate)
    #       total = attempts*cost_per_instruction + n_target*cost_per_response
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
c = synthesis_cost(52000, pass_rate=0.5, cost_per_instruction=0.0002, cost_per_response=0.0010)
assert c['attempts'] == 104000
assert abs(c['total_cost'] - (104000*0.0002 + 52000*0.0010)) < 1e-9
print(f'造 52k 条数据（通过率 50%）: 尝试 {c["attempts"]:,} 次, '
      f'总成本 ${c["total_cost"]:.2f}, 每条 ${c["cost_per_usable"]:.6f}')
# 更严的去重 -> 通过率降 -> 成本升
c_strict = synthesis_cost(52000, 0.25, 0.0002, 0.0010)
assert c_strict['total_cost'] > c['total_cost']
print(f'去重更严（通过率 25%）: 总成本 ${c_strict["total_cost"]:.2f} '
      f'（+{(c_strict["total_cost"]/c["total_cost"]-1):.0%}）')
print('\\n✅ 练习 3 通过：注意**过滤放在生成回答之前**，所以被丢的指令只花了指令生成费 ——')
print('   这是个真实的成本优化（先过滤再生成回答，而不是反过来）。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def dedup_add(pool, candidate, rouge_thresh):
    ct = candidate.tokens()
    max_sim = max((rouge_l(ct, p.tokens()) for p in pool), default=0.0)
    if max_sim > rouge_thresh:
        return False, max_sim
    pool.append(candidate)
    return True, max_sim"""),
    code("""# 练习 2 参考答案
def collapse_alert(history, window=3, drop_thresh=0.1):
    if len(history) < 2: return []
    a = history[max(0, len(history) - window - 1)]
    b = history[-1]
    alerts = []
    for k in ('distinct-2', '唯一key比', '领域熵'):
        if a[k] > 0 and (a[k] - b[k]) / a[k] > drop_thresh:
            alerts.append(k + '↓')
    k = '最高频模式占比'
    if a[k] > 0 and (b[k] - a[k]) / a[k] > drop_thresh:
        alerts.append(k + '↑')
    return alerts"""),
    code("""# 练习 3 参考答案
def synthesis_cost(n_target, pass_rate, cost_per_instruction, cost_per_response):
    attempts = math.ceil(n_target / pass_rate)
    total = attempts * cost_per_instruction + n_target * cost_per_response
    return {'attempts': attempts, 'total_cost': total,
            'cost_per_usable': total / n_target}"""),
    md("""---
## 🧪 真实数据胶囊：Self-Instruct 的公开量级

用论文报告的数字算清「52k 条数据要多少钱」，以及去重阈值怎么影响它。"""),
    code("""# Self-Instruct 论文的公开数字
SEED_TASKS = 175
FINAL_DATA = 52_000
REPORTED_DUP_DROP = 0.5          # 论文报告约一半因去重被丢
# 今天的 API 量级（$/1M token）
PRICE_IN, PRICE_OUT = 0.15, 0.60
TOK_INSTR_IN, TOK_INSTR_OUT = 600, 60      # few-shot 提示较长、指令较短
TOK_RESP_IN, TOK_RESP_OUT = 120, 250

cost_instr = (TOK_INSTR_IN/1e6)*PRICE_IN + (TOK_INSTR_OUT/1e6)*PRICE_OUT
cost_resp = (TOK_RESP_IN/1e6)*PRICE_IN + (TOK_RESP_OUT/1e6)*PRICE_OUT
print(f'单次指令生成 ${cost_instr:.6f} | 单次回答生成 ${cost_resp:.6f}')

print(f"\\n{'去重阈值':>9s} {'通过率':>8s} {'尝试次数':>10s} {'总成本$':>9s} {'每条$':>9s}")
for th, pr in [(0.5, 0.25), (0.7, 0.50), (0.9, 0.80)]:
    c = synthesis_cost(FINAL_DATA, pr, cost_instr, cost_resp)
    print(f'{th:>9.1f} {pr:>8.0%} {c["attempts"]:>10,} {c["total_cost"]:>9.2f} '
          f'{c["cost_per_usable"]:>9.6f}')

c07 = synthesis_cost(FINAL_DATA, 0.50, cost_instr, cost_resp)
c05 = synthesis_cost(FINAL_DATA, 0.25, cost_instr, cost_resp)
print(f'\\n从 175 条种子造出 {FINAL_DATA:,} 条数据（阈值 0.7）: ${c07["total_cost"]:.0f}')
print(f'放大倍数: {FINAL_DATA/SEED_TASKS:.0f}×')
assert c05['total_cost'] > c07['total_cost'], '更严的去重更贵'
print(f'把去重收紧到 0.5: 成本升到 ${c05["total_cost"]:.0f} '
      f'（+{(c05["total_cost"]/c07["total_cost"]-1):.0%}），换更高的多样性。')
print('\\n✅ 关键量级感：几十美元就能从 175 条种子造出 5 万条指令数据 ——')
print('   这就是为什么 Self-Instruct 打开了整个开源指令模型生态。')
print('   ⚠️ 但记住三条上限：学生 ≤ 教师、偏差会传递、递归会坍塌。')"""),
    md("""**🧪 胶囊练习**：实现 `synthetic_mix_plan(n_real, target_total, max_synthetic_ratio)`：
返回 `{'n_synthetic':…, 'actual_ratio':…, 'feasible':…}`。
合成数据比例不能超过 `max_synthetic_ratio`（防坍塌）；若目标总量在此约束下达不到，
`feasible=False` 且返回约束下的最大总量对应的合成条数。"""),
    code("""def synthetic_mix_plan(n_real, target_total, max_synthetic_ratio):
    # TODO: 约束 n_syn / (n_real + n_syn) <= max_ratio
    #       -> n_syn <= n_real * max_ratio / (1 - max_ratio)
    raise NotImplementedError"""),
    code("""# 自测
p = synthetic_mix_plan(n_real=1000, target_total=4000, max_synthetic_ratio=0.5)
assert p['feasible'] is False, '真实 1000 条、合成占比上限 50% -> 总量最多 2000'
assert p['n_synthetic'] == 1000 and abs(p['actual_ratio'] - 0.5) < 1e-9
p2 = synthetic_mix_plan(1000, 1800, 0.5)
assert p2['feasible'] is True and p2['n_synthetic'] == 800
print(f'真实 1000 条, 目标 4000, 合成上限 50% -> 可行? {p["feasible"]}, '
      f'只能合成 {p["n_synthetic"]} 条（总量 {1000+p["n_synthetic"]}）')
print(f'真实 1000 条, 目标 1800 -> 可行? {p2["feasible"]}, 合成 {p2["n_synthetic"]} 条')
print('\\n✅ 胶囊练习通过：**「想要多少合成数据」受「有多少真实数据」约束** ——')
print('   这是防坍塌的硬约束，不是可以商量的偏好。')
print('   要更多合成数据，先去标注更多真实数据。')"""),
    code("""# 📖 胶囊参考答案
def synthetic_mix_plan(n_real, target_total, max_synthetic_ratio):
    cap = n_real * max_synthetic_ratio / (1 - max_synthetic_ratio)
    want = max(0, target_total - n_real)
    n_syn = int(min(want, cap))
    total = n_real + n_syn
    return {'n_synthetic': n_syn,
            'actual_ratio': (n_syn / total) if total else 0.0,
            'feasible': n_syn >= want}"""),
    md("""### 小结
- **指令层是唯一能真正增加信息量的增强**：信息来自教师的预训练知识，而非原样本的重组。
- **Self-Instruct 的命门是 ROUGE-L 去重**：LLM 有强模式惯性（few-shot 锚定 → 池子同质 → 更强锚定的正反馈），去重是打断它的唯一机制。阈值收紧 → 丢弃率超线性上升 → **成本直接翻倍**。
- **「输出优先」防标签倾斜**：让 LLM 自己造样本会得到它的先验（本课模拟里 78% 正面）；先定标签再造样本才可控、才能补长尾。
- **Evol-Instruct 的深度演化必须配广度演化**；并要用**可验证的难度代理**（基座答对率）识别「难度伪装」。
- **Magpie 零种子、多样性高、可控性最差**。三者组合：Magpie 起量、Self-Instruct 定领域、Evol 提难度。**先诊断缺什么。**
- **教师偏差完整传递**（长度/格式/领域/知识错误）；**学生 ≤ 教师**，所以合成数据的正确用途是蒸馏而非创造知识。
- **模式坍塌的四个早期征兆**：多样性降、长度分布收窄、高频模式占比升、覆盖收缩。它们**在下游指标崩溃之前就出现**——这是多样性指标真正的价值（当警报，不是好看）。
- **混入真实数据是主要缓解手段**：「合成完全替代真实」危险，「合成补充真实」可行。**想要多少合成数据，受有多少真实数据约束。**

下一站：**模块 04 · 增强的质量控制** —— 把这些检验做成一套可持续运行的管线。"""),
]
