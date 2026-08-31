# -*- coding: utf-8 -*-
"""C66 模块 01 · agentic 基准全景（任务形态 / 判分方式 / 已知缺陷）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 00（三层评测对象与七个决策点）；"
                 "对「单元测试」「HTTP 请求」「数据库最终状态」这些概念有基本印象即可，不需要写过"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_benchmark_landscape.ipynb'
                       '（基准画像库与查询 / 判分方式分类器 / 任务区分度与信息量 / '
                       'n-gram 污染检测器 / 时间截断检验 / 任务集规模与分辨力）'),
    ("核心参考", "Jimenez et al., <em>SWE-bench</em>（ICLR 2024）· OpenAI, <em>SWE-bench Verified</em>（2024）· "
                 "Yao et al., <em>τ-bench</em>（2024）· Mialon et al., <em>GAIA</em>（2023）· "
                 "Zhou et al., <em>WebArena</em>（ICLR 2024）· Xie et al., <em>OSWorld</em>（NeurIPS 2024）· "
                 "Chan et al., <em>MLE-bench</em>（2024）· 本课程 C03 模块 05（污染）"),
    ("预计时长", "读 60 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("map", "一张地图：按环境类型给 agentic 基准分类", "".join([
        P("「有哪些 agent 基准」这个问题如果按发布时间或者按机构来记，记完就忘。"
          "有用的分类维度只有一个：<strong>环境是什么</strong>——因为环境决定了判分方式，"
          "判分方式决定了这个分数能支持什么结论。"),
        ASCII("""
                        agentic 基准
                             │
   ┌──────────────┬──────────┴───────┬──────────────┬──────────────┐
   │              │                  │              │              │
 代码仓库        工具+对话          图形界面        开放网络       科研/长程
   │              │                  │              │              │
SWE-bench      τ-bench           WebArena         GAIA         MLE-bench
SWE-bench      τ²-bench          VisualWebArena   BrowseComp   RE-Bench
  Verified     （零售/航空）       OSWorld          Assistant-   SWE-Lancer
SWE-bench                        Mind2Web          Bench
  Multimodal                     WebVoyager
Terminal-Bench
   │              │                  │              │              │
判分：跑测试   判分：终态匹配    判分：程序化      判分：精确      判分：奖牌/
     (F2P+P2P)      (DB diff)        validator      匹配短答案      分数阈值
   │              │                  │              │              │
最客观 ←──────────────────────────────────────────────────→ 最依赖设计
"""),
        TABLE(["环境类型", "agent 能做什么", "判分函数长什么样", "最大的方差来源"], [
            ["<strong>代码仓库</strong>", "读文件、改文件、跑 shell、跑测试", "在钉死的容器里跑一组测试：<code>FAIL_TO_PASS</code> 必须由红转绿、<code>PASS_TO_PASS</code> 必须保持绿", "容器镜像与依赖版本；测试本身的强度"],
            ["<strong>工具 + 对话</strong>", "调 API（查订单、改地址、退款）、与被模拟的用户对话", "对比数据库<strong>最终状态</strong>与人工标注的目标状态；外加必答信息的检查", "<strong>用户模拟器</strong>本身是一个 LLM，它的随机性直接注入评测"],
            ["<strong>图形界面 / OS</strong>", "点击、输入、滚动、切换应用、跑命令", "每个任务配一个手写的 <code>validator()</code>：查数据库行、查文件内容、查页面元素", "页面渲染时序、应用版本、分辨率"],
            ["<strong>开放网络</strong>", "搜索、浏览、下载、读 PDF/图片", "把答案归一化后精确匹配（答案被设计成唯一且简短）", "<strong>互联网本身会变</strong>：页面下线、搜索结果排序漂移"],
            ["<strong>科研 / 长程</strong>", "写训练代码、跑实验、调参、提交结果", "在留出集上算分数，与人类基线（如 Kaggle 奖牌线）比较", "算力预算、运行时长（单任务可达数十 GPU 小时）"],
        ]),
        CALLOUT("intuition", "读这张表时抓住一条主线：<strong>判分越接近「跑一段确定性代码」，分数越可信；"
                             "判分越接近「问一个模型好不好」，分数越依赖判分器本身的质量</strong>。"
                             "本课 02 模块讲前者的工程细节，C67 整门课讲后者的可信度。"),
    ])),

    # ============================================================== 2
    ("swebench", "代码仓库类：SWE-bench 家族的三个数字", "".join([
        P("SWE-bench 是目前影响力最大的 agentic 基准，也是最值得逐层拆开看的一个——"
          "因为它把「一个好的 agentic 基准应该长什么样」和「一个 agentic 基准会踩哪些坑」同时演示了一遍。"),
        H3("任务是怎么构造出来的"),
        OL([
            "从 12 个流行的 Python 开源仓库里，抓取<strong>已合并的 PR</strong>；",
            "只保留「解决了某个 issue」且「修改了测试文件」的 PR——后者是关键：<strong>有测试改动，才有自动判分的可能</strong>；",
            "把 PR 拆成两半：<strong>issue 文本</strong>（给 agent 看）与 <strong>补丁 + 测试</strong>（用来判分，对 agent 隐藏）；",
            "把仓库回滚到 PR 的父提交，记录下 <code>FAIL_TO_PASS</code>（打上补丁前失败、之后通过的测试）"
            "与 <code>PASS_TO_PASS</code>（前后都必须通过的测试）。",
        ]),
        P("于是判分函数变成了一段完全确定性的代码：<strong>把 agent 产出的 patch 打进容器，跑这两组测试，"
          "全绿才算 1 分</strong>。原始版本有 2294 条任务实例。"),
        DUAL(
            "为什么 <code>PASS_TO_PASS</code> 这么重要？因为没有它的话，"
            "「把整个文件删掉再重写一个只让目标测试通过的版本」也能拿分。"
            "<code>PASS_TO_PASS</code> 是防回归的那道闸门——它对应模块 00 里"
            "「修一个好位置会引入回归」的那个设计。<strong>任何自建的代码类任务集，"
            "如果只检查目标行为、不检查既有行为，判分器就是有洞的。</strong>",
            "从测量的角度，$\\text{FAIL\\_TO\\_PASS}$ 度量的是<span class=\"term\">功能达成</span>，"
            "$\\text{PASS\\_TO\\_PASS}$ 度量的是<span class=\"term\">副作用约束</span>。"
            "只有前者的判分函数在数学上是一个<em>不完全的规格</em>（under-specified specification），"
            "它允许存在大量「通过判分但语义错误」的解——这正是 reward hacking 的入口"
            "（C67 模块 05 会从奖励模型的角度重讲这件事）。",
        ),
        H3("三个数字：2294 / 500 / 300"),
        TABLE(["版本", "规模", "怎么来的", "该在什么时候用"], [
            ["<strong>SWE-bench</strong>（full）", "2294", "自动化流水线产出，未经人工逐条审核", "研究覆盖面时用；报告主分数时已基本被 Verified 取代"],
            ["<strong>SWE-bench Verified</strong>", "500", "由专业开发者逐条审核，剔除「issue 描述不足以复现」「测试检查了 issue 没提到的行为」等不可解或误判任务", "<strong>报告主分数的默认选择</strong>"],
            ["<strong>SWE-bench Lite</strong>", "300", "按自动化规则筛出的轻量子集，跑得快、成本低", "开发迭代期的快速回归（呼应 C68 的 CI 门禁）"],
        ]),
        CALLOUT("warn", "<strong>Verified 的存在本身就是本模块最重要的一课。</strong>"
                        "它说明：一个被广泛引用、被写进无数技术报告的基准，在发布近一年后，"
                        "被发现有相当比例的任务<em>根本无法被正确完成</em>——不是模型不行，是题目有问题。"
                        "推论很直接：<strong>你自建的任务集，如果没有经过「人类专家能不能做出来」这一关，"
                        "默认就应该假设它含有可观比例的坏题。</strong>"),
        H3("家族的其余成员"),
        UL([
            "<strong>SWE-bench Multimodal</strong>：换成 JavaScript 仓库、且 issue 里带截图/录屏，"
            "考察「看得懂界面问题」的能力——判分方式不变，仍然是跑测试。",
            "<strong>SWE-bench Multilingual</strong>：把语言从 Python 扩展到多种语言，用来检验"
            "「在 Python 上的成绩有多少来自对 Python 生态的记忆」。",
            "<strong>持续更新型变体</strong>（如 SWE-bench-Live 一类的做法）：只收录<em>模型训练截止之后</em>"
            "新产生的 PR，定期滚动。这是对付污染的结构性解法，代价是每次滚动后分数不可与历史直接比较。",
            "<strong>Terminal-Bench</strong> 一类：把环境从「仓库」放宽到「一台终端」，任务包含环境配置、"
            "数据处理、系统运维，判分同样靠测试脚本。",
            "<strong>SWE-Lancer</strong> 一类：用真实自由职业任务与端到端测试判分，并附带「这个任务在市场上值多少钱」"
            "的价格标签——把成功率折算成经济价值，是 05 模块成本视角的一个极端版本。",
        ]),
    ])),

    # ============================================================== 3
    ("taubench", "工具+对话类：τ-bench 与「终态匹配」判分", "".join([
        P("SWE-bench 的判分靠跑测试，那么<strong>客服型 agent</strong>（帮用户改机票、退货、查订单）怎么判分？"
          "τ-bench 给出的答案是：<strong>不看它说了什么，看它把数据库改成了什么样。</strong>"),
        ASCII("""
   ┌─────────────┐   自然语言    ┌──────────────┐   工具调用   ┌────────────┐
   │ 用户模拟器   │ ◄──────────► │    被测 agent │ ◄─────────► │  领域数据库 │
   │ (也是 LLM)  │              │              │  (get/update)│ 订单/航班… │
   └─────────────┘              └──────────────┘             └────────────┘
          │                            │                            │
          │ 用户目标(隐藏)              │ 领域策略文档(可见)          │ 终态
          ▼                            ▼                            ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ 判分 = (数据库终态 == 标注的目标终态) AND (必答信息都对用户说了)      │
   └────────────────────────────────────────────────────────────────────┘
"""),
        TABLE(["设计选择", "怎么做的", "为什么这么做", "副作用"], [
            ["用户是模拟的", "用一个 LLM 扮演用户，只知道自己的目标，不知道系统内部规则", "真实客服场景里信息是<strong>挤牙膏</strong>式给出的，一次性把需求说全不真实", "<strong>模拟器的随机性直接进入评测方差</strong>；模拟器换模型 = 换了基准"],
            ["判分看终态", "对比数据库最终状态与人工标注的目标状态", "绕开了「同一件事有很多种说法」的自然语言判分难题", "只对<strong>有写操作</strong>的任务有效；纯咨询类任务需要额外的信息检查项"],
            ["有领域策略文档", "给 agent 一份「什么情况下才允许退款」之类的规则文档", "考察<strong>规则遵循</strong>而不只是任务完成", "策略文档写得越细，越考「长文本里找规则」而非 agent 能力"],
            ["强调多次运行", "同一任务重复 $k$ 次，报告 <strong>pass^k</strong>（k 次全对的比例）", "客服 agent 的商业价值取决于<strong>可靠性</strong>而非峰值能力", "评测成本乘 $k$；04 模块专门讲这个指标"],
        ]),
        CALLOUT("intuition", "<strong>pass^k 是 τ-bench 留给整个领域的最重要遗产。</strong>"
                             "pass@k 问的是「试 $k$ 次至少成一次的概率」，适合<em>可以人工挑选结果</em>的场景（比如代码补全）；"
                             "pass^k 问的是「连续 $k$ 次都成功的概率」，适合<em>没人复核就直接执行</em>的场景（比如自动退款）。"
                             "<strong>把一个客服 agent 的 pass@8 拿去汇报，等于在汇报一个和产品价值无关的数字。</strong>"),
        P("τ²-bench 一类的后续工作把设定进一步推向<strong>双向控制</strong>：用户不再只是提供信息，"
          "而是也能操作环境（比如「你去重启一下路由器」），agent 必须<em>指挥用户</em>完成部分动作。"
          "这带来了新的判分维度：<strong>指令的可执行性</strong>——说得对但用户听不懂照做不了，同样是失败。"),
    ])),

    # ============================================================== 4
    ("gui-web", "图形界面与网页类：程序化 validator 与环境漂移", "".join([
        P("WebArena 与 OSWorld 代表了另一条路线：<strong>不构造判分测试，而是给每一个任务手写一个校验函数</strong>。"),
        TABLE(["基准", "环境", "规模", "判分方式", "关键设计"], [
            ["<strong>WebArena</strong>", "<strong>自建可复现的网站集群</strong>：购物、论坛、GitLab、CMS、地图，全部本地部署", "812 个任务", "每个任务一个程序化 validator：查数据库行、查 URL、查页面文本，或检查「不可能达成」时是否正确放弃", "<strong>自托管</strong>是全部关键——真实网站会变，本地快照才能复现"],
            ["<strong>VisualWebArena</strong>", "同上但任务需要视觉理解（按图找商品、看图填表）", "910 个任务", "同上 + 图像相关的检查", "考察 VLM 的界面理解（呼应 C00）"],
            ["<strong>OSWorld</strong>", "真实操作系统（Ubuntu/Windows）+ 真实应用（LibreOffice、GIMP、VS Code、浏览器）", "369 个任务", "每个任务一段执行式校验脚本：读文件内容、跑命令、查配置", "<strong>跨应用</strong>任务是难点：在 A 里查到的东西要填进 B"],
            ["<strong>Mind2Web</strong>", "离线录制的真实网页轨迹", "2350 个任务", "元素级匹配：选对了 DOM 元素、动作类型对不对", "离线 = 完全可复现，但<strong>无法评测「走错了能不能回来」</strong>"],
            ["<strong>WebVoyager</strong> 一类", "<strong>真实在线网站</strong>", "几百个任务", "用 VLM 看截图做 judge", "最真实，也最不可复现——同一个任务两周后跑，网站已经改版"],
        ]),
        DUAL(
            "离线、自托管、在线，三种取舍其实是同一个跷跷板：<strong>越真实越不可复现，越可复现越不真实</strong>。"
            "离线轨迹（Mind2Web）可以精确复现，但 agent 一旦偏离录好的路径就没法继续评了；"
            "自托管快照（WebArena）保住了交互性，代价是网站是「冻在某一天的样子」；"
            "在线真实网站最有说服力，但你今天的 45% 和三个月后的 45% 根本不是同一个实验。",
            "形式化地说，设 $\\mathcal{E}_t$ 是 $t$ 时刻的环境。可复现性要求 $\\mathcal{E}_{t_1} = \\mathcal{E}_{t_2}$；"
            "生态效度（ecological validity）要求 $\\mathcal{E}$ 与部署环境 $\\mathcal{E}^{*}$ 同分布。"
            "在线基准满足后者而违反前者，离线基准反之。"
            "<strong>工程上的通行解法是「双轨」：自托管快照做回归门禁（要可复现），"
            "在线小样本做生态校验（要真实），两条线的数字分开报告、从不混算</strong>——"
            "这正是 C68 模块 05 里离线-在线双回路的雏形。",
        ),
        CALLOUT("danger", "<strong>「不可能任务」是 WebArena 的一个被严重低估的设计。</strong>"
                          "任务集里混入了一部分在该网站上根本无法完成的请求，正确行为是<em>识别并明确放弃</em>。"
                          "没有这类任务的基准，会系统性奖励「编造一个看起来完成了的答复」的行为——"
                          "而这恰恰是 agent 在真实产品里最危险的失败模式。"
                          "<strong>自建任务集时，请务必留出 5%–15% 的不可能任务。</strong>"),
    ])),

    # ============================================================== 5
    ("open-web", "开放网络与科研类：唯一答案与人类基线", "".join([
        P("最后两类基准解决的是同一个难题：<strong>当任务的产出不是「代码」也不是「数据库状态」，怎么客观判分？</strong>"),
        H3("GAIA：把开放问题设计成唯一短答案"),
        P("GAIA 的做法是从判分倒推题目设计：<strong>只出那些答案唯一、简短、可以精确匹配的问题</strong>"
          "（一个数字、一个名字、一个短语），但通往这个答案的路径需要多步搜索、读文件、看图、算数。"
          "题目分三个难度级别（大致对应需要的步数与工具数），共几百道，"
          "并且发布时带着一个刺眼的对比：<strong>人类能做对九成以上，而当时最强的带插件模型只有一成多</strong>。"),
        CALLOUT("intuition", "GAIA 的方法论可以直接拿去自建任务集：<strong>先问「我怎么自动判对错」，"
                             "再据此设计题目形态</strong>，而不是先出一堆开放题再发愁怎么判分。"
                             "「答案唯一且简短」是一条极强的约束，它换来的是判分器几乎零成本、零主观性。"),
        H3("BrowseComp 一类：难找但易验证"),
        P("沿着 GAIA 的思路再推一步：刻意构造<strong>「答案极难找到、但一旦找到极易验证」</strong>的问题"
          "（把多个稀有约束叠加，使得答案在网上只有一处能拼出来）。"
          "这类基准的价值在于它<strong>专门测长程搜索的耐心</strong>，而不是知识量——"
          "模型记不住这些答案，只能真的去搜。"),
        H3("MLE-bench / RE-Bench 一类：用人类基线定分数"),
        TABLE(["设计问题", "解法", "代价"], [
            ["机器学习任务没有「对/错」，只有分数高低", "拿真实竞赛的排行榜当标尺，把 agent 的成绩折算成<strong>奖牌等级</strong>（铜/银/金）", "需要竞赛级别的完整数据与评测集"],
            ["不同任务的分数尺度完全不同", "统一转成「相对人类分布的百分位」再聚合", "百分位对分布尾部不敏感，接近上限时会失去区分度"],
            ["单个任务要跑很久（数小时到数十 GPU 小时）", "限定墙钟时间预算，并把<strong>时间预算作为一个自变量</strong>报告", "评测成本极高，通常只能跑很少的 seed（04 模块的统计困境在这里最尖锐）"],
        ]),
        P("这一类基准还引出了一个正在成为主流的报告维度：<strong>「时间跨度」（time horizon）</strong>——"
          "不问「成功率多少」，而问<strong>「这个 agent 能以 50% 成功率完成的任务，人类专家要花多久」</strong>。"
          "它的好处是把不同难度的任务统一到一根有物理意义的轴上，"
          "坏处是需要为每个任务标注可靠的人类耗时。"),
    ])),

    # ============================================================== 6
    ("pathologies", "所有 agentic 基准的四种共同病灶", "".join([
        P("不管环境是什么，agentic 基准都会得同样四种病。识别它们，是读懂任何一份 agent 评测报告的前提。"),
        TABLE(["病灶", "机制", "症状", "缓解手段"], [
            ["<strong>① 污染</strong>", "任务来自公开仓库/网页，早已进入训练语料；更隐蔽的是<strong>解法泄漏</strong>——issue 的评论区里就写着正确补丁", "小模型在某些任务上异常地好；模型能凭空说出仓库里的私有函数名", "时间截断（只用训练截止后的数据）· 持续滚动的 live 版本 · n-gram/嵌入重合检测 · 检查「不给 issue 只给文件名能不能做对」"],
            ["<strong>② 任务不可解或判分过弱</strong>", "描述信息不足以复现；隐藏测试检查了描述里没提的行为；或者反过来，测试太弱，随手改改就能过", "人类专家做不到 100%；不同的正确解法拿到不同分数", "<strong>人工逐条审核</strong>（Verified 的做法）· 用多个强模型的解法做交叉验证 · 检查测试覆盖率"],
            ["<strong>③ 环境漂移</strong>", "依赖版本、页面结构、外部 API 随时间变化", "同一份代码几个月后跑出不同分数；旧论文的数字复现不出来", "容器镜像 digest 钉死 · 网络录制回放 · 定期重跑历史基线做「环境健康检查」"],
            ["<strong>④ 饱和与 harness 过拟合</strong>", "分数逼近上限后区分度消失；或者大家都在调 scaffold 而不是模型", "榜单前几名挤在 1–2 个点内；换个 harness 排名就翻转", "报告 harness 全量配置 · 引入更难的子集 · 用 <strong>pass^k</strong> 等更严格的指标拉开差距"],
        ]),
        CALLOUT("warn", "关于污染有一个特别值得警惕的细节：<strong>代码类基准的「解法泄漏」不只发生在训练语料里，"
                        "也可能发生在任务本身内部</strong>——如果 issue 的正文或评论里已经贴出了修复补丁，"
                        "那么这道题测的是「读理解」而不是「解决问题」。"
                        "自建任务集时，<strong>把 issue 的评论区、后续 commit message、PR 描述全部剥离</strong>，"
                        "是一条必须写进流水线的清洗规则。"),
        DUAL(
            "怎么快速判断一份 agent 评测报告值不值得信？看它有没有回答这四个问题："
            "① 任务是什么时候产生的，模型训练截止是什么时候？② 任务集有没有人审过？"
            "③ 环境版本钉死了吗？④ harness 是什么、跑了几次？"
            "<strong>四个都没答的报告，读一下当参考即可，不要拿来做决策。</strong>",
            "这四个问题分别对应四类效度威胁：<span class=\"term\">construct validity</span>（污染让基准不再测量它声称测量的能力）、"
            "<span class=\"term\">internal validity</span>（坏题让分数与能力脱钩）、"
            "<span class=\"term\">reliability</span>（环境漂移让测量不可重复）、"
            "<span class=\"term\">external validity</span>（harness 过拟合让结论无法迁移到别的实现）。"
            "<em>C10 用心理测量学的语言系统讲过这四类效度，本课只是把它们翻译到 agent 场景。</em>",
        ),
    ])),

    # ============================================================== 7
    ("build-own", "什么时候必须自建任务集，以及怎么建", "".join([
        P("公开基准的价值是<strong>横向可比</strong>，但它几乎必然与你的真实场景有分布差距。"
          "以下三种情况必须自建："),
        UL([
            "<strong>你的工具集是私有的</strong>——公开基准里没有你们的内部 API，agent 在上面的表现说明不了任何事；",
            "<strong>你要做回归门禁</strong>——你需要的是「上周能做对的今天还能不能做对」，"
            "公开基准的粒度太粗、跑得太慢（C68 模块 04）；",
            "<strong>公开基准已经饱和</strong>——所有候选模型都在 90% 以上，分数不再包含决策信息。",
        ]),
        H3("自建任务集的六条规则"),
        OL([
            "<strong>先写判分函数，再写任务</strong>：判不了分的任务不要收。这条规则能挡掉八成的坏题。",
            "<strong>每个任务都要有防回归检查项</strong>（对应 <code>PASS_TO_PASS</code>）：只查目标行为的判分器一定会被 hack。",
            "<strong>混入不可能任务</strong>（5%–15%）：不这么做就是在奖励编造。",
            "<strong>难度要有梯度</strong>：全是难题 = 全零，没有区分度；全是简单题 = 全满分，同样没有区分度。"
            "目标是让整体成功率落在 <strong>30%–70%</strong> 区间——这是信息量最大的位置（notebook 里会算给你看）。",
            "<strong>任务要标注元数据</strong>：需要几个工具、预期几步、涉及哪个子系统、人类耗时。"
            "没有元数据就没法做切片分析，一个总分掩盖所有细节。",
            "<strong>先让人做一遍</strong>：人类专家做不到 90% 以上的任务，八成是题有问题而不是难。",
        ]),
        CALLOUT("intuition", "关于第 4 条的量化直觉：一道题如果所有被测 agent 都通过（或都失败），"
                             "它对<strong>区分</strong>这些 agent 的贡献是 <strong>0 bit</strong>——"
                             "它仍然可以用来验证「没有退化」，但对「A 和 B 谁更强」这个问题一无所知。"
                             "把任务集的成功率推向 50% 附近，等价于把每道题的信息量推向最大（$H(p)$ 在 $p=0.5$ 取最大）。"
                             "<em>这是 C10 的 IRT 视角在 agent 任务集设计上的直接应用。</em>"),
        P("最后一条实践建议：<strong>任务集要版本化，并且永远不要「就地修改」</strong>。"
          "发现坏题时，正确做法是发布 <code>v2</code> 并同时保留 <code>v1</code>，"
          "而不是悄悄把 <code>v1</code> 里的题改掉——否则所有历史分数一夜之间失去意义。"
          "版本化的具体做法见 C68 模块 01。"),
    ])),
]

NB = [
    md("""# 01 · agentic 基准全景（画像库 / 判分方式分类 / 任务区分度 / 污染检测 / 规模与分辨力）

目标：把「有哪些基准」这个背诵题，变成几个**可以查询、可以计算、可以复用**的工具。

本 notebook 你会亲手实现：
1. **基准画像库与查询** —— 十余个主流 agentic 基准的结构化画像，按环境/判分方式检索
2. **判分方式分类器** —— 给定一个任务描述，判断它该用哪种判分函数
3. **任务区分度与信息量** —— 为什么全对/全错的任务是 0 bit，成功率该往哪推
4. **n-gram 污染检测器** —— 纯 Python 实现，检出「任务文本与训练语料重合」
5. **时间截断检验** —— 用发布时间切分任务集，检出「训练截止前后的分数断崖」
6. **任务集规模与分辨力** —— 要区分差 3 个点的两个 agent，需要多少道题

> 心智模型：**基准不是排行榜，是测量仪器。选基准 = 选一把尺子，
> 而每把尺子都有自己的量程、刻度和系统误差。**"""),

    md("""## 1 · 基准画像库与查询

先把讲解里的那张地图变成数据。字段的选择本身就是本模块的结论：
**环境类型决定判分方式，判分方式决定这个分数能支持什么结论。**"""),

    code("""import math, json, re
from collections import Counter, defaultdict
import numpy as np

# 说明：n_tasks 取各基准官方公布的量级，随版本滚动会变；报告分数时必须写明具体版本。
BENCHMARKS = [
    # name,                 env,        scoring,        n_tasks, reproducible, notes
    ('SWE-bench',           'repo',     'tests',        2294, 'high',  '自动化流水线，含不可解任务'),
    ('SWE-bench Verified',  'repo',     'tests',         500, 'high',  '人工逐条审核后的可解子集'),
    ('SWE-bench Lite',      'repo',     'tests',         300, 'high',  '轻量子集，适合 CI 回归'),
    ('SWE-bench Multimodal','repo',     'tests',         517, 'high',  'JS 仓库 + 截图/录屏'),
    ('Terminal-Bench',      'terminal', 'tests',         100, 'high',  '终端环境，测试脚本判分'),
    ('tau-bench',           'tools',    'final_state',   165, 'medium','用户由 LLM 模拟，注入方差'),
    ('tau2-bench',          'tools',    'final_state',   278, 'medium','双向控制：agent 指挥用户操作'),
    ('WebArena',            'web_self', 'validator',     812, 'high',  '自托管站点，含不可能任务'),
    ('VisualWebArena',      'web_self', 'validator',     910, 'high',  '需要视觉理解的网页任务'),
    ('OSWorld',             'os',       'validator',     369, 'medium','真实 OS + 真实应用，跨应用任务'),
    ('Mind2Web',            'web_off',  'element_match',2350, 'high',  '离线轨迹，无法评错误恢复'),
    ('GAIA',                'open_web', 'exact_match',   466, 'low',   '唯一短答案；互联网会漂移'),
    ('BrowseComp',          'open_web', 'exact_match',  1266, 'low',   '难找易验证，专测长程搜索'),
    ('MLE-bench',           'research', 'human_baseline', 75, 'medium','Kaggle 奖牌线做标尺'),
]

FIELDS = ['name', 'env', 'scoring', 'n_tasks', 'reproducible', 'notes']
DB = [dict(zip(FIELDS, row)) for row in BENCHMARKS]

def query(**kw):
    out = DB
    for k, v in kw.items():
        out = [b for b in out if b[k] == v]
    return out

print('按判分方式统计：')
for scoring, n in Counter(b['scoring'] for b in DB).most_common():
    names = ', '.join(b['name'] for b in query(scoring=scoring))
    print(f'  {scoring:<15} {n} 个 | {names}')

assert len(query(scoring='tests')) == 5
assert all(b['reproducible'] == 'low' for b in query(env='open_web'))
print('\\n✅ 注意最后一条断言：所有开放网络基准的可复现性都是 low——')
print('   这不是巧合，是「用真实互联网当环境」的必然代价。')"""),

    code("""# 判分方式 → 该分数能支持什么结论
IMPLICATION = {
    'tests':          ('客观性最高', '结论仅限于「测试覆盖到的行为」，测试弱则判分弱'),
    'final_state':    ('客观性高',   '仅适用于有写操作的任务；纯咨询任务需额外的信息检查项'),
    'validator':      ('客观性高',   '每题一个手写函数 → validator 本身可能有 bug，需要被测试'),
    'element_match':  ('客观性高',   '离线：无法评「走错后能不能纠正」这一最关键的 agent 能力'),
    'exact_match':    ('客观性最高', '要求答案唯一简短 → 任务形态被判分方式严格约束'),
    'human_baseline': ('相对尺度',   '跨任务可聚合，但接近人类上限时区分度快速消失'),
}
w = max(len(k) for k in IMPLICATION)
for k, (pro, con) in IMPLICATION.items():
    print(f'{k:<{w}}  {pro:<8} ⚠ {con}')

total_tasks = sum(b['n_tasks'] for b in DB)
print(f'\\n画像库覆盖 {len(DB)} 个基准、{total_tasks:,} 道任务。')
assert total_tasks > 10000
print('✅ 一个常被忽略的事实：agentic 基准的任务总量比静态基准少两三个数量级——')
print('   因为每道题都要一套环境和一个判分器，边际成本极高。这直接决定了统计功效的天花板（第 6 节）。')"""),

    md("""## 2 · 判分方式分类器

自建任务集时的第一个决策：这道题该怎么判分？把讲解里的规则写成一棵可执行的决策树。"""),

    code("""def choose_scorer(has_tests, mutates_state, answer_is_unique_short, is_offline_trace,
                  has_human_baseline):
    \"\"\"判分方式选择树。顺序即优先级：能跑测试就跑测试，其次看终态，
    再次看唯一答案，最后才考虑相对基线/人工。\"\"\"
    if has_tests:
        return 'tests'
    if mutates_state:
        return 'final_state'
    if answer_is_unique_short:
        return 'exact_match'
    if is_offline_trace:
        return 'element_match'
    if has_human_baseline:
        return 'human_baseline'
    return 'llm_judge'          # 兜底：交给 C67

CASES = [
    (True,  True,  False, False, False, '修一个有回归测试的 bug'),
    (False, True,  False, False, False, '帮用户改签机票'),
    (False, False, True,  False, False, '查出某届会议最佳论文一作的博士导师'),
    (False, False, False, True,  False, '在录制好的网页轨迹上复现一次下单'),
    (False, False, False, False, True,  '在一个 Kaggle 数据集上把 AUC 做到尽可能高'),
    (False, False, False, False, False, '写一份关于某市场的调研摘要'),
]
for args in CASES:
    print(f'{args[-1]:<32} -> {choose_scorer(*args[:-1])}')

assert choose_scorer(True, True, True, True, True) == 'tests'
assert choose_scorer(False, False, False, False, False) == 'llm_judge'
print('\\n✅ 决策树就位。最后一条落到 llm_judge 上——这是唯一一类「判分器自己需要被评测」的情形，')
print('   本课把它整个交给 C67，因为它值一门独立的课。')"""),

    md("""## 3 · 任务区分度与信息量：成功率该往哪推

一道所有 agent 都通过（或都失败）的题，对「谁更强」这个问题贡献 0 bit。
用二元熵 $H(p) = -p\\log_2 p - (1-p)\\log_2(1-p)$ 量化，并算一个任务集的**有效题量**。"""),

    code("""def binary_entropy(p):
    if p <= 0 or p >= 1:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

for p in [0.0, 0.05, 0.2, 0.3, 0.5, 0.7, 0.95, 1.0]:
    bar = '█' * int(binary_entropy(p) * 40)
    print(f'  成功率 {p:5.0%}  信息量 {binary_entropy(p):.3f} bit  {bar}')

assert binary_entropy(0.5) == 1.0
assert binary_entropy(0.0) == binary_entropy(1.0) == 0.0
assert binary_entropy(0.3) > binary_entropy(0.05)
print('\\n✅ 30%-70% 区间内信息量 ≥ 0.88 bit，接近最大值；')
print('   而 5% 或 95% 的题只剩 0.29 bit——七成的测量预算被浪费掉了。')"""),

    code("""def effective_task_count(pass_rates):
    \"\"\"有效题量 = 各题信息量之和 / 1 bit。衡量「名义 N 道题里，实际有多少道在干活」。\"\"\"
    return sum(binary_entropy(p) for p in pass_rates)

rng = np.random.default_rng(3)
# 三种任务集：饱和（大家都过）、地狱（大家都不过）、健康（难度有梯度）
saturated = np.clip(rng.normal(0.93, 0.05, 300), 0, 1)
hellish   = np.clip(rng.normal(0.04, 0.03, 300), 0, 1)
healthy   = np.clip(rng.uniform(0.15, 0.85, 300), 0, 1)

for name, rates in [('饱和 (均值0.93)', saturated), ('地狱 (均值0.04)', hellish),
                    ('健康 (均匀0.15-0.85)', healthy)]:
    eff = effective_task_count(rates)
    print(f'{name:<22} 名义 300 题 → 有效 {eff:6.1f} 题（利用率 {eff/300:5.1%}）')

assert effective_task_count(healthy) > 2 * effective_task_count(saturated)
print('\\n✅ 同样 300 道题，健康任务集的测量效率是饱和任务集的两倍以上。')
print('   这就是「基准饱和了就该换基准」的定量版本——不是情怀问题，是信息论问题。')"""),

    md("""## 4 · n-gram 污染检测器

最朴素也最实用的污染信号：任务文本与训练语料的 n-gram 重合率。
纯 Python 实现，没有依赖。"""),

    code("""def ngrams(text, n=13):
    toks = re.findall(r'\\w+', text.lower())
    return {tuple(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1))}

def contamination_score(task_text, corpus_texts, n=13):
    \"\"\"返回任务文本里有多大比例的 n-gram 能在语料中找到。\"\"\"
    task_ngrams = ngrams(task_text, n)
    if not task_ngrams:
        return 0.0
    corpus_ngrams = set()
    for t in corpus_texts:
        corpus_ngrams |= ngrams(t, n)
    return len(task_ngrams & corpus_ngrams) / len(task_ngrams)

CORPUS = [
    'when the parser encounters a nested list inside a table cell it raises an '
    'index error because the cell width is computed before the nested content is expanded',
    'the recommended fix is to defer width computation until after all nested '
    'structures have been fully expanded and flattened into the layout tree',
]
clean_task = ('the exporter drops trailing whitespace in code blocks which breaks '
              'doctest output comparison for users who rely on exact formatting rules')
dirty_task = ('when the parser encounters a nested list inside a table cell it raises an '
              'index error because the cell width is computed before the nested content is expanded')

c_clean = contamination_score(clean_task, CORPUS, n=8)
c_dirty = contamination_score(dirty_task, CORPUS, n=8)
print(f'干净任务的 8-gram 重合率: {c_clean:.1%}')
print(f'污染任务的 8-gram 重合率: {c_dirty:.1%}')
assert c_clean < 0.05 and c_dirty > 0.9
print('\\n✅ n-gram 检测能抓「逐字重合」，但抓不到「语义重合」（改写过的同一道题）。')
print('   更强的做法是嵌入相似度 + 「不给题面只给文件名，看模型能不能做对」的行为学检验。')"""),

    md("""## 5 · 时间截断检验：训练截止前后的分数断崖

比 n-gram 更有说服力的污染证据：把任务按**创建时间**排序，
看模型的成功率在训练截止日期附近有没有断崖。"""),

    code("""def time_cutoff_test(dates, scores, cutoff):
    \"\"\"返回 (截止前成功率, 截止后成功率, 差值)。差值显著为正 = 污染嫌疑。\"\"\"
    dates, scores = np.asarray(dates), np.asarray(scores, dtype=float)
    before, after = scores[dates < cutoff], scores[dates >= cutoff]
    return before.mean(), after.mean(), before.mean() - after.mean()

rng = np.random.default_rng(5)
n = 600
dates = rng.uniform(0, 24, size=n)              # 过去 24 个月
CUTOFF = 14.0                                    # 训练截止在第 14 个月

# 场景 A：被污染的模型——截止前的任务它"见过"
p_contaminated = np.where(dates < CUTOFF, 0.62, 0.34)
scores_contaminated = (rng.random(n) < p_contaminated).astype(float)
# 场景 B：干净的模型——成功率与任务创建时间无关
scores_clean = (rng.random(n) < 0.40).astype(float)

for name, sc in [('污染嫌疑模型', scores_contaminated), ('干净模型', scores_clean)]:
    b, a, d = time_cutoff_test(dates, sc, CUTOFF)
    # 两比例差的标准误
    nb, na = (dates < CUTOFF).sum(), (dates >= CUTOFF).sum()
    se = math.sqrt(b * (1 - b) / nb + a * (1 - a) / na)
    z = d / se
    print(f'{name:<14} 截止前 {b:.1%} | 截止后 {a:.1%} | 差 {d:+.1%} | z = {z:+.2f}')

b, a, d = time_cutoff_test(dates, scores_contaminated, CUTOFF)
assert d > 0.15, '污染场景下应有明显断崖'
b2, a2, d2 = time_cutoff_test(dates, scores_clean, CUTOFF)
assert abs(d2) < 0.10, '干净场景下不应有系统性断崖'
print('\\n✅ 时间截断检验的强项：它不需要访问训练语料，只需要任务的创建时间。')
print('   弱点：任务难度本身可能随时间变化（新代码更复杂），需要用同期的对照任务集控制。')"""),

    md("""## 6 · 任务集规模与分辨力：要区分 3 个点，需要多少道题

agentic 基准最痛的现实约束：任务少。用两比例检验反推所需样本量。"""),

    code("""def required_n(p1, p2, alpha=0.05, power=0.8):
    \"\"\"两独立比例检验所需的每组样本量（正态近似）。\"\"\"
    z_a, z_b = 1.959963985, 0.8416212336        # 双侧 alpha=0.05 / power=0.8
    p_bar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(num / (p1 - p2) ** 2)

print(f"{'对比':<26}{'每组所需任务数':>16}")
for p1, p2 in [(0.40, 0.50), (0.40, 0.45), (0.40, 0.43), (0.40, 0.41)]:
    print(f'{p1:.0%} vs {p2:.0%}{"":<16}{required_n(p1, p2):>14,}')

n_needed = required_n(0.40, 0.43)
print(f'\\nSWE-bench Verified 只有 500 道题，而区分 40% vs 43% 需要每组约 {n_needed:,} 道。')
assert n_needed > 500
print('→ 结论很硬：**在 500 道题的基准上，3 个点的差距在统计上不可分辨**。')
print('  榜单上挤在几个点内的名次，绝大部分是噪声。')
print('\\n两条出路（04 模块展开）：')
print('  ① 配对设计——同一批任务上比较两个 agent，消掉任务难度这个最大的方差源；')
print('  ② 多次重复——每个任务跑 k 次，用任务内平均代替 0/1，降低单任务方差。')"""),

    code("""def required_n_paired(p_discordant, delta, alpha=0.05, power=0.8):
    \"\"\"配对设计（McNemar）所需任务数：只有「一个对一个错」的不一致对携带信息。
    p_discordant: 不一致对的比例；delta: 两个 agent 的成功率之差。\"\"\"
    z_a, z_b = 1.959963985, 0.8416212336
    return math.ceil(((z_a + z_b) ** 2 * p_discordant) / (delta ** 2))

print('配对设计（同一批任务同时跑两个 agent）：')
for pd in [0.10, 0.20, 0.30]:
    print(f'  不一致对占比 {pd:.0%} → 区分 3 个点需要 {required_n_paired(pd, 0.03):>6,} 道任务')
gain = required_n(0.40, 0.43) / required_n_paired(0.20, 0.03)
print(f'\\n配对设计相对独立设计的样本量节省：约 {gain:.1f} 倍')
assert gain > 1.0
print('✅ 这就是「同一批任务、同一套 harness、同时跑两个 agent」为什么是 agent 评测的默认设计。')"""),

    md("""## ✏️ 练习 1：任务集健康度评分

实现 `task_set_health(pass_rates)`：返回一个 0–1 的健康度 = **有效题量 / 名义题量**
（即各题二元熵的平均）。用它比较三种任务集。"""),

    code("""def task_set_health(pass_rates):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(task_set_health([0.5] * 10) - 1.0) < 1e-12
assert abs(task_set_health([0.0, 1.0, 0.0, 1.0])) < 1e-12
h_healthy, h_sat = task_set_health(healthy), task_set_health(saturated)
assert h_healthy > 0.8 and h_sat < 0.5
print(f'健康任务集 {h_healthy:.1%} | 饱和任务集 {h_sat:.1%}')
print('✅ 练习 1 通过：健康度掉到 50% 以下，说明该换基准或加难题了。')"""),

    md("""## ✏️ 练习 2：不可能任务的正确处理率

实现 `impossible_task_score(responses)`：输入一批对**不可能任务**的响应
（每条形如 `{'abstained': bool, 'fabricated': bool}`），返回
`(正确放弃率, 编造率)`。正确放弃 = `abstained and not fabricated`。"""),

    code("""def impossible_task_score(responses):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
resp = [{'abstained': True,  'fabricated': False},
        {'abstained': False, 'fabricated': True},
        {'abstained': False, 'fabricated': True},
        {'abstained': True,  'fabricated': False}]
ab, fab = impossible_task_score(resp)
assert abs(ab - 0.5) < 1e-12 and abs(fab - 0.5) < 1e-12
all_good = [{'abstained': True, 'fabricated': False}] * 5
assert impossible_task_score(all_good) == (1.0, 0.0)
print(f'正确放弃率 {ab:.0%} | 编造率 {fab:.0%}')
print('✅ 练习 2 通过：没有不可能任务的基准，会系统性奖励编造——')
print('   而编造恰恰是 agent 在真实产品里最危险的失败模式。')"""),

    md("""## ✏️ 练习 3：污染嫌疑的组合判据

实现 `contamination_flag(ngram_overlap, time_gap_delta, name_recall)`：
三个信号任意<strong>两个</strong>超阈值就标记为嫌疑。阈值：
`ngram_overlap > 0.3`、`time_gap_delta > 0.12`、`name_recall > 0.5`
（`name_recall` = 不给题面、只给文件名时模型说出私有符号名的比例）。
返回 `(是否嫌疑, 触发的信号列表)`。"""),

    code("""def contamination_flag(ngram_overlap, time_gap_delta, name_recall):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
flag, sig = contamination_flag(0.45, 0.20, 0.10)
assert flag is True and set(sig) == {'ngram_overlap', 'time_gap_delta'}
flag2, sig2 = contamination_flag(0.45, 0.02, 0.10)
assert flag2 is False and sig2 == ['ngram_overlap']
flag3, sig3 = contamination_flag(0.9, 0.9, 0.9)
assert flag3 is True and len(sig3) == 3
print('单一信号不足以定罪：', contamination_flag(0.45, 0.02, 0.10))
print('两个信号同时触发：  ', contamination_flag(0.45, 0.20, 0.10))
print('✅ 练习 3 通过：单个污染信号都有各自的假阳性来源——')
print('   n-gram 会被通用样板文本触发，时间断崖会被难度漂移触发，需要交叉印证。')"""),

    md("""## ✏️ 练习 4：给定预算下的任务集配比

实现 `allocate_tasks(budget_minutes, cost_per_task, min_per_bucket)`：
`cost_per_task` 是 `{难度: 每题分钟数}`，按「每一分钟买到的信息量最大」贪心分配，
每档至少 `min_per_bucket` 道。假设各档难度对应的成功率为
`{'easy': 0.85, 'medium': 0.5, 'hard': 0.2}`，信息量用二元熵。
返回 `{难度: 题数}`。"""),

    code("""PASS_BY_BUCKET = {'easy': 0.85, 'medium': 0.5, 'hard': 0.2}

def allocate_tasks(budget_minutes, cost_per_task, min_per_bucket):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
cost = {'easy': 2.0, 'medium': 3.0, 'hard': 20.0}
alloc = allocate_tasks(600, cost, min_per_bucket=5)
assert set(alloc) == {'easy', 'medium', 'hard'}
assert all(v >= 5 for v in alloc.values())
spent = sum(alloc[k] * cost[k] for k in alloc)
assert spent <= 600 + 1e-9, f'超预算: {spent}'
# medium 的「每分钟信息量」最高（1.0 bit / 6 min），应拿到最多的追加名额
assert alloc['medium'] > alloc['hard']
info = sum(alloc[k] * binary_entropy(PASS_BY_BUCKET[k]) for k in alloc)
print('分配结果：', alloc, f'| 耗时 {spent:.0f} 分钟 | 总信息量 {info:.1f} bit')
print('✅ 练习 4 通过：medium 每分钟买到 0.33 bit（最高），hard 只有 0.036 bit（最低）——')
print('   但保底名额仍然必须给，否则任务集会失去对强模型的区分度（这是「保底 vs 效率」的经典取舍）。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def task_set_health(pass_rates):
    rates = list(pass_rates)
    if not rates:
        return 0.0
    return sum(binary_entropy(p) for p in rates) / len(rates)"""),

    code("""# 练习 2 参考答案
def impossible_task_score(responses):
    n = len(responses)
    if n == 0:
        return (0.0, 0.0)
    ab = sum(1 for r in responses if r['abstained'] and not r['fabricated']) / n
    fab = sum(1 for r in responses if r['fabricated']) / n
    return (ab, fab)"""),

    code("""# 练习 3 参考答案
def contamination_flag(ngram_overlap, time_gap_delta, name_recall):
    signals = []
    if ngram_overlap > 0.3:
        signals.append('ngram_overlap')
    if time_gap_delta > 0.12:
        signals.append('time_gap_delta')
    if name_recall > 0.5:
        signals.append('name_recall')
    return (len(signals) >= 2, signals)"""),

    code("""# 练习 4 参考答案
def allocate_tasks(budget_minutes, cost_per_task, min_per_bucket):
    alloc = {k: min_per_bucket for k in cost_per_task}
    remaining = budget_minutes - sum(min_per_bucket * c for c in cost_per_task.values())
    if remaining < 0:
        raise ValueError('预算不足以覆盖每档的保底名额')
    # 每分钟买到的信息量，从高到低贪心
    order = sorted(cost_per_task, key=lambda k: -binary_entropy(PASS_BY_BUCKET[k]) / cost_per_task[k])
    for k in order:
        n_extra = int(remaining // cost_per_task[k])
        alloc[k] += n_extra
        remaining -= n_extra * cost_per_task[k]
    return alloc"""),

    md("""---
## 🧪 真实工程胶囊：接入三个真实基准的最短路径"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. SWE-bench Verified：查看任务、检查污染窗口
# ══════════════════════════════════════════════════════════════════
from datasets import load_dataset
ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
print(len(ds))                       # 500
ex = ds[0]
# 污染自检：任务对应 PR 的创建时间 vs 你的模型训练截止时间
print(ex["created_at"], ex["repo"], ex["version"])
# 清洗规则（自建任务集时必做）：剥离 issue 评论、后续 commit message、PR 描述
import re
clean = re.split(r"\\n\\s*(?:Comment|Reply|Fix|Patch)\\b", ex["problem_statement"])[0]

# ══════════════════════════════════════════════════════════════════
# B. tau-bench：注意用户模拟器是评测的一部分
# ══════════════════════════════════════════════════════════════════
# pip install tau-bench   (github.com/sierra-research/tau-bench)
# python run.py --agent-strategy tool-calling \\
#     --env retail --model claude-sonnet-5 --model-provider anthropic \\
#     --user-model claude-sonnet-5 --user-model-provider anthropic \\
#     --num-trials 8            # ← 8 次重复才能算 pass^k
# 报告时必须写清 user-model 是谁：换了用户模拟器 = 换了基准，分数不可比。

# ══════════════════════════════════════════════════════════════════
# C. WebArena：自托管快照才是可复现的关键
# ══════════════════════════════════════════════════════════════════
# 官方提供各站点的 docker 镜像（shopping / reddit / gitlab / cms / map）。
# 复现清单（缺一项就不可复现）：
#   1. 镜像 digest（不是 tag——tag 会被覆盖）
#   2. 每次任务开始前 reset 到快照（否则前一个任务的写操作会污染后一个）
#   3. 固定浏览器版本与视窗尺寸（页面布局变化会让基于坐标的动作失效）
#   4. 记录 validator 的版本——validator 是手写代码，它自己也会被修 bug

# ══════════════════════════════════════════════════════════════════
# D. 自建任务集的最小 schema（照抄即可）
# ══════════════════════════════════════════════════════════════════
TASK_SCHEMA = {
  "task_id": "str, 稳定不变",
  "prompt": "str, 已剥离解法泄漏",
  "env_snapshot": "str, 镜像 digest 或数据快照哈希",
  "scorer": "tests | final_state | validator | exact_match",
  "success_check": "必须达成的条件",
  "regression_check": "必须保持不变的条件（对应 PASS_TO_PASS）",
  "impossible": "bool, 5%-15% 的任务应为 True",
  "meta": {"n_tools_expected": 3, "human_minutes": 12, "subsystem": "billing",
           "created_at": "2026-03-01"},
}
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 按环境分类 | 环境决定判分方式，判分方式决定分数能支持什么结论 | 选基准 / 自建任务集 |
| SWE-bench 的三个数字 | 2294 全量 / 500 人工审核 / 300 轻量；Verified 的存在证明「坏题是常态」 | 报告主分数用 Verified |
| 终态匹配与 pass^k | 客服型 agent 的价值在可靠性，pass@k 报出来没有意义 | 04 模块 |
| 程序化 validator | 每题一个手写函数——validator 自己也需要被测试 | 02 模块 |
| 四种共同病灶 | 污染 / 坏题 / 环境漂移 / 饱和与 harness 过拟合 | 读任何评测报告 |
| 信息论视角 | 成功率推向 30–70% 才有区分度；500 题分辨不了 3 个点 | 04 模块 |

下一模块：**02 · 结果判分与部分得分**——把「怎么判对错」从一句话展开成一套工程，
包括判分器自身的假阳/假阴、部分得分会不会改变模型排序、以及 rubric checkpoint 怎么设计。""")
]
