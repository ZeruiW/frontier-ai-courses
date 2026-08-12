# -*- coding: utf-8 -*-
"""C52 模块 05 · 研究产出与知识产权。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–04；对自己做过的工作有一份清单（本模块要你把它变成产出）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_research_output_ip.ipynb'),
    ("核心参考", "USPTO/EPO 的可专利性标准、SPDX 许可清单、各大会议的投稿与 artifact 政策"),
    ("预计时长", "读 55 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    ("why", "为什么这是研究工程师的必修课", "".join([
        CALLOUT("danger", "<p><strong>本模块关于专利与开源许可的内容是工程视角的实用指南，不是法律意见。</strong>真实的专利申请、许可合规判断与合同解释<em>必须</em>由公司的法务/知识产权部门或执业律师做。本模块的目标是让你<strong>知道该在什么时候找他们、带什么材料去、以及不要做什么</strong>——这些恰恰是最常出错的地方，而且出错的代价通常不可逆。</p>", "先说清边界"),
        P("工业研究岗与学术研究岗的最大差别，往往不在做什么研究，而在<strong>研究产出的形式</strong>。JD 里那句「patents, publications, and presentations」不是客套——它描述的是<em>考核你的三种可交付物</em>。"),
        TABLE(["产出", "对公司的价值", "时间尺度", "常见误区"], [
            ["<strong>专利</strong>", "防御性资产、交叉许可筹码、账面资产", "1–4 年（申请到授权）", "<strong>先发论文再想申请——公开即丧失新颖性</strong>"],
            ["<strong>论文</strong>", "招聘品牌、外部验证、学术影响力", "6–18 个月", "没走内部审批就投稿；泄露了受保护的信息"],
            ["<strong>内部演示</strong>", "<strong>决定你的工作是否被采用</strong>", "即时", "讲成学术报告——听众关心的是决策而不是方法"],
            ["<strong>开源发布</strong>", "生态影响、招聘、外部贡献", "数周", "<strong>许可不兼容——把公司代码卷进了 copyleft</strong>"],
            ["<strong>内部工具/文档</strong>", "复利最高但最不被认可", "持续", "不写——于是每个新人重踩一遍你的坑"],
        ]),
        DUAL(
            "第一行的误区是<strong>不可逆且代价最高</strong>的一个：<em>在申请专利之前公开（发论文、发博客、开源、甚至在公开会议上讲）会导致该内容丧失新颖性</em>，在大多数司法辖区意味着永久失去专利权。<strong>而研究人员的本能恰恰是「做出来了就赶快发」</strong>。所以工业实验室普遍有一条规则：<em>任何对外公开前先走内部披露与审批</em>——这不是官僚，这是在保护一个可能价值数百万的资产。",
            "第三行的误区最常见也最影响你的职业发展：<strong>把内部演示讲成学术报告</strong>。学术报告的听众想知道「这个方法为什么有效、和 SOTA 比如何」；<em>内部听众想知道「要不要用、代价多少、风险在哪、下一步要什么资源」</em>。<strong>用错模板的后果是：你做了很好的工作，但没有人据此做决定，于是它不被采用，于是它等于没做</strong>。这个失败模式在技术能力强的人身上尤其常见。",
        ),
    ])),
    ("patent", "专利：一个工程师需要懂的部分", "".join([
        H3("三个门槛"),
        TABLE(["门槛", "含义", "在 AI/ML 领域的实际难点"], [
            ["<strong>新颖性</strong> (novelty)", "此前没有任何公开披露过同样的东西", "<strong>公开即丧失</strong>：论文、arXiv、博客、开源、公开演讲、甚至 GitHub 的公开 commit"],
            ["<strong>非显而易见性</strong> (non-obviousness)", "对该领域的普通技术人员来说不是显然的组合", "「把 A 方法用到 B 任务上」常被认为显而易见；<em>要有非预期的效果</em>"],
            ["<strong>可专利主题</strong> (eligibility)", "不能是抽象概念、数学公式本身、自然规律", "<strong>纯算法难，「算法 + 具体技术改进」容易</strong>——要说清它解决了什么<em>技术</em>问题"],
        ]),
        DUAL(
            "第三行是 AI 领域最关键也最微妙的一条。<strong>「一个更好的损失函数」本身很难获得专利</strong>（它像数学）；<em>但「一种通过在训练中动态调整损失权重来降低推理时显存占用的方法」就容易得多</em>——因为它绑定了一个具体的技术效果（显存占用）。<strong>所以撰写披露材料时，最重要的动作是把「算法创新」翻译成「技术问题 + 技术手段 + 技术效果」的三段式</strong>。",
            "第二行的「非显而易见」在实践中常常靠<strong>「非预期的效果」</strong>来论证。如果你的方法只是「按预期地好一点」，很容易被认为是常规优化；<em>如果它带来了某种反直觉的收益（如「减少参数反而提升了鲁棒性」），那就构成了非显而易见的有力证据</em>。<strong>所以做实验时留意那些「意外的好结果」，它们的专利价值可能高于主结果。</strong>",
        ),
        H3("权利要求的结构（读懂就够，不用会写）"),
        ASCII("""独立权利要求 1（最宽）
   「一种 X 的方法，包括：
      a) 步骤 A；
      b) 步骤 B；
      c) 基于 A 和 B 的结果执行 C。」
   ↑ 每增加一个限定，保护范围**变窄**但更容易被授权
   ↑ 要覆盖竞争者「绕过去」的所有明显变体

从属权利要求 2–N（更窄，逐层收缩）
   「根据权利要求 1 的方法，其中步骤 A 使用 <具体实现>。」
   ↑ 作用：如果权利要求 1 被无效，还有这些顶着
   ↑ 也用来覆盖具体的最佳实施例

工程师最容易犯的错：
   ❌ 只描述你实际做的那一种实现 -> 保护范围过窄，竞争者稍改就绕过
   ❌ 把限定写得过多过细 -> 同上
   ✅ 列出**所有你能想到的变体**（不同架构、不同精度、不同粒度），
      让专利代理人决定哪些进权利要求""")
        ,
        CALLOUT("intuition", "一个立刻可用的判断法：<strong>「如果竞争者要绕过我的专利，最小的改动是什么？」</strong> 如果答案是「把 ReLU 换成 GELU 就绕过了」，说明你的权利要求写得太具体。<em>披露材料里应该主动列出这些「明显的变体」</em>——它们不会削弱你的专利，反而是撰写宽权利要求的原料。<strong>这个思维练习花十分钟，能显著提升专利质量</strong>，而它只有你（发明人）能做，代理人做不了。"),
        H3("发明披露书：你实际要写的东西"),
        P("你通常不写专利，你写<strong>发明披露书</strong>（invention disclosure），由专利代理人据此撰写申请。一份好的披露书有六部分："),
        UL([
            "<strong>①问题</strong>：现有技术解决不了什么<em>技术</em>问题（不是「效果不够好」，而是具体的技术瓶颈）。",
            "<strong>②现有技术</strong>：你知道的最接近的已有方案，以及它们为什么不够。<em>诚实列出——隐瞒会在审查时反噬。</em>",
            "<strong>③你的方案</strong>：核心机制，越具体越好，配图/伪代码。",
            "<strong>④为什么有效</strong>：机制上的解释 + 实验证据。<em>特别标注「非预期的效果」。</em>",
            "<strong>⑤变体</strong>：所有你能想到的替代实现（这是最容易被跳过、也最有价值的一节）。",
            "<strong>⑥时间线与公开状态</strong>：<strong>第一次构思的日期、有没有对外提过、代码在哪</strong>——这一节决定了还能不能申请。",
        ]),
        CALLOUT("warn", "关于<strong>时间线</strong>：即使是内部的、看似无害的公开也可能有影响——在有外部人员参加的会议上讲、在公开的 Slack 频道贴、把代码推到公开仓库、给客户做 demo。<em>所以正确的顺序是：有想法 → 记录（带日期）→ 内部披露 → 等法务确认 → 再决定公开与否</em>。<strong>「先发 arXiv 占坑再申请专利」在多数辖区是不可行的</strong>——虽然美国有 12 个月宽限期，但这既不适用于所有国家，也不该作为默认策略。"),
    ])),
    ("license", "开源许可：一张必须会看的兼容表", "".join([
        P("这是研究工程师日常最容易踩、且后果最严重的合规问题：<strong>你在项目里引入了一个依赖，而它的许可要求你开源整个产品</strong>。"),
        TABLE(["许可", "类型", "核心义务", "能否用于闭源产品", "陷阱"], [
            ["<strong>MIT / BSD / Apache-2.0</strong>", "宽松 (permissive)", "保留版权声明；Apache 还要标注修改", "✅ 可以", "Apache-2.0 有专利授权条款（通常是好事）"],
            ["<strong>LGPL</strong>", "弱 copyleft", "<strong>动态链接可以，修改 LGPL 部分需开源该部分</strong>", "🔶 需谨慎（静态链接有争议）", "静态链接与「衍生作品」边界模糊"],
            ["<strong>GPL-2.0 / GPL-3.0</strong>", "强 copyleft", "<strong>分发时必须以同样许可开源整个衍生作品</strong>", "❌ 不行", "「链接算不算衍生」有长期争议；<em>但别拿自己的产品去测试</em>"],
            ["<strong>AGPL-3.0</strong>", "网络 copyleft", "<strong>连「通过网络提供服务」也触发开源义务</strong>", "❌ 不行", "<em>SaaS 场景下最危险的一个</em>——很多人以为不分发就没事"],
            ["<strong>CC-BY-NC</strong>", "非商业", "禁止商业使用", "❌ 不行", "<strong>大量数据集是这个许可</strong>——训练商业模型即违约"],
            ["<strong>自定义模型许可</strong>", "各不相同", "如用户数上限、禁止改进竞品、可接受使用政策", "🔶 <strong>必须逐条读</strong>", "Llama 等的许可不是 OSI 认可的开源许可"],
        ]),
        DUAL(
            "<strong>AGPL 是 AI 领域最容易踩的坑</strong>，因为它打破了「不分发就没有义务」这个直觉。GPL 的义务在<em>分发</em>时触发，所以内部使用是安全的；<em>而 AGPL 的义务在「通过网络向用户提供功能」时就触发</em>——这正是所有 AI 服务的形态。<strong>如果你的推理服务里有一个 AGPL 的组件，你可能要开源整个服务</strong>。而 AGPL 在数据处理与向量数据库这类工具里并不罕见。",
            "<strong>而模型与数据集的许可比代码许可更混乱</strong>。「开源模型」常常不是 OSI 意义上的开源：Llama 系列有用户数条款与可接受使用政策；很多模型是 CC-BY-NC（禁止商业）；<em>更麻烦的是「许可传染性」——用 NC 数据训练出的模型，其许可状态在法律上不明确，且不同辖区看法不同</em>。<strong>实践中的安全做法是维护一份「许可清单」，记录每个数据集/模型/代码依赖的许可与用途限制</strong>，并在项目启动时（而不是发布前）过一遍。",
        ),
        CALLOUT("danger", "<p>两个必须记住的操作规则：<strong>①许可检查要在<em>引入依赖时</em>做，不是发布前做</strong>——发布前发现问题意味着要重写已经写好的代码，成本高一个数量级。<strong>②不要自己判断边界情形</strong>（静态链接算不算衍生、NC 数据训练的模型能不能商用）——<em>这些是真正有争议的法律问题，交给法务</em>。你的职责是<strong>准确记录「用了什么、什么许可、怎么用的」</strong>，让法务能做判断。</p>", "两条操作规则"),
    ])),
    ("presentation", "内部演示：一个不同的模板", "".join([
        P("<strong>学术报告与内部演示的目标不同，所以结构必须不同</strong>。这个差别在技术能力强的人身上最容易被忽略。"),
        TABLE(["", "学术报告", "内部技术演示"], [
            ["听众要什么", "「这个方法为什么有效」", "<strong>「要不要用、代价多少」</strong>"],
            ["开头", "背景与动机", "<strong>结论与建议（第一张幻灯片就给）</strong>"],
            ["主体", "方法细节 → 实验 → 消融", "<strong>决策所需的证据 + 代价 + 风险</strong>"],
            ["与 SOTA 比较", "必需（这是贡献的证明）", "<em>次要</em>（除非影响决策）"],
            ["失败与局限", "常常轻描淡写", "<strong>必须明确说</strong>（听众要据此评估风险）"],
            ["结尾", "未来工作", "<strong>明确的 ask</strong>：要什么资源、要谁决定什么"],
            ["时长分配", "80% 方法，20% 结果", "<strong>20% 方法，80% 影响与代价</strong>"],
        ]),
        DUAL(
            "<strong>「第一张幻灯片就给结论」</strong>是最重要的一条，也最反学术训练的直觉。学术报告为了铺垫会把结论留到后面；<em>而内部演示的听众可能只听前五分钟（后面在看手机或被叫走）</em>。<strong>所以结构应该是倒金字塔：结论 → 依据 → 细节</strong>，让人在任何时刻离场都拿到了最重要的信息。",
            "<strong>「明确的 ask」</strong>是第二条。一个没有 ask 的演示，最好的结果是「大家觉得挺有意思」，然后什么都不发生。<em>ask 可以是「批准 200 GPU 小时做规模化验证」、「让 X 团队评估集成成本」、「决定是否申请专利」</em>——但必须具体到「谁在什么时候做什么决定」。<strong>把演示的成功定义为「产生了一个决定」而不是「讲清楚了」</strong>，你的工作被采用的比例会显著上升。",
        ),
        CALLOUT("intuition", "一个能立刻提升演示质量的检查：<strong>写完之后，只看第一张和最后一张幻灯片，问「一个只看这两张的人能做出决定吗？」</strong> 如果不能，说明结论或 ask 不够清楚。<em>另一个检查：把每张幻灯片的标题连起来读，应该构成一个完整的论证</em>——如果标题是「实验设置」「结果」「消融」这种，说明你在用学术模板。<strong>标题应该是断言</strong>（「显存降低 40%，精度损失 0.3 分」），不是章节名。"),
    ])),
    ("publish", "论文与开源：内部流程的现实", "".join([
        ASCII("""工业界发论文/开源的典型流程（各公司细节不同，形状类似）

  想法 / 结果
     ↓
  ① 内部披露（invention disclosure）—— **必须在任何公开之前**
     ↓ 法务/IP 评估：值得申请专利吗？
     ├── 值得 → 先申请（或至少提交临时申请）→ 之后才能公开
     └── 不值得 → 直接进入 ② （但要有书面确认）
     ↓
  ② 内容审查（publication review）
     · 有没有泄露未公开的产品计划、客户信息、内部数据？
     · 有没有用到受限的数据集 / 第三方受保护的信息？
     · 有没有与既有专利申请冲突的表述？
     ↓
  ③ 开源专项审查（若涉及代码/权重）
     · 依赖的许可兼容性（本模块的兼容表）
     · 用什么许可发布（公司通常有默认选择，如 Apache-2.0）
     · 权重的许可与可接受使用政策
     ↓
  ④ 投稿 / 发布
     ↓
  ⑤ 后续义务：安全披露渠道、维护承诺、社区响应

⚠️ 时间成本：①②③ 加起来常常是 2–8 周。**投稿截止前一周才启动是来不及的。**""")
        ,
        DUAL(
            "这套流程常被研究人员视为障碍，但它的两个作用是真实的：<strong>①保护专利权（一次不慎的公开就永久失去）；②防止无意泄露</strong>（你可能不知道某个数据集是客户提供且受合同限制的）。<em>把它当成「和法务的一次协作」而不是「审批」，体验会好很多</em>——他们通常能给出「这样改一下就可以发」的具体建议。",
            "实操上最重要的建议是<strong>时间管理</strong>：<em>把内部流程的 2–8 周计入投稿计划</em>。这意味着如果 NeurIPS 五月截止，你要在三月就启动披露流程，而不是五月第一周。<strong>更好的做法是「结果一出来就启动披露」</strong>——因为披露本身不需要论文写完，只需要说清方法与结果。<em>这样流程与写论文可以并行，而不是串行。</em>",
        ),
        CALLOUT("warn", "还有一个容易被忽略的项：<strong>⑤后续义务</strong>。开源一个模型或库意味着承担了持续的责任——安全漏洞的披露与修复、issue 的响应、破坏性变更的沟通。<em>如果团队没有能力承担，「开源」会变成一个逐渐腐烂的仓库，对公司品牌是负资产</em>。<strong>所以决定开源时应该同时决定「维护承诺的级别」</strong>，并写在 README 里（如「本仓库为研究用途，不承诺长期维护」）。这句话能省掉大量后续的期望管理。"),
    ])),
    ("docs", "内部文档与工具：价值最高、认可最少", "".join([
        P("表格里那一行「内部文档/工具」值得单独展开，因为它是<strong>唯一一个「价值高但激励错配」的产出</strong>——而错配意味着它会被系统性地供给不足。"),
        TABLE(["内部产出", "复利来源", "为什么没人做"], [
            ["<strong>踩坑记录</strong>（本课模块 04 那种诊断树）", "每个新人省下你踩坑的时间 × 人数", "写的时候你已经解决了问题，动力最低的那一刻"],
            ["<strong>可复用的工具</strong>（对拍脚本、显存计算器、导出检查器）", "每次用都省一次，且能防住整类错误", "「这只是个小脚本」——于是每个人各写一份"],
            ["<strong>决策记录</strong>（为什么选 A 不选 B）", "半年后有人问「当初为什么不用 X」时唯一的答案", "决策时觉得理由很显然，忘了它三个月后就不显然了"],
            ["<strong>失败记录</strong>（试过什么、为什么不work）", "<strong>防止团队反复试同一个死路</strong>", "没人愿意记录自己的失败"],
        ]),
        DUAL(
            "<strong>「失败记录」是其中价值密度最高的一项</strong>，也是最稀缺的。研究工作里失败远多于成功，而「我们试过 X，在 Y 条件下不 work，原因是 Z」这句话能直接省掉另一个人几周时间。<em>但没有任何机制奖励它</em>——季度总结里没人写「我证明了三条路走不通」，尽管那可能正是最有价值的贡献。<strong>团队层面的缓解办法是把失败记录变成例行动作</strong>（每个实验结束都写两行结论，不管成败），<em>而不是依赖个人的自觉</em>。",
            "对个人而言，缓解激励错配的办法是<strong>把内部产出「外化」成可见的东西</strong>：在演示里明确提到「这个诊断树已经放在 wiki 上」；让新人 onboarding 时引用它；把工具做成团队人人在用的脚本而不是你自己的 notebook。<em>可见度不会自动产生，需要你主动制造</em>。<strong>这不是邀功——如果一份文档没人知道它存在，它的复利就是零，制造可见度是让它产生价值的必要步骤。</strong>",
        ),
        CALLOUT("intuition", "有一个判断「该不该写下来」的简单标准：<strong>「如果这件事我三个月后忘了，重新搞清楚要多久？」</strong> 超过半小时就值得写。<em>因为「三个月后的你」与「一个新同事」在信息量上几乎没有差别</em>——你会忘掉所有上下文，只留下一个模糊的「好像处理过这个」。<strong>按这个标准，本课每个模块的 checklist、诊断树、命令集都属于「必须写下来」的那一类</strong>，而它们恰好也是这门课最值得直接搬进你自己工具库的部分。"),
    ])),
    ("ledger", "算一笔账：产出形式的投入产出", "".join([
        TABLE(["产出", "典型投入", "对公司的价值", "对你的价值", "时间到价值"], [
            ["专利（一件）", "20–40 h（披露 + 与代理人往复）", "防御资产、交叉许可", "简历上的硬指标；很多公司有奖金", "1–4 年"],
            ["顶会论文（一篇）", "<strong>200–400 h</strong>", "招聘品牌、外部验证", "学术声誉、外部机会", "6–18 个月"],
            ["内部演示（一次）", "<strong>4–12 h</strong>", "<strong>决定工作是否被采用</strong>", "<strong>可见度（最高性价比）</strong>", "即时"],
            ["开源发布", "40–120 h + 持续维护", "生态影响、招聘", "外部可见度", "数周–数月"],
            ["内部文档/工具", "8–40 h", "<strong>团队复利（最高但最不被认可）</strong>", "🔶 常被低估", "持续"],
        ]),
        P("三点观察："),
        UL([
            "<strong>内部演示的性价比远高于其他形式</strong>（4–12 小时 vs 论文的 200–400 小时），而且它直接决定你的工作是否被采用。<em>很多人在论文上投入过度、在演示上投入不足</em>。",
            "<strong>专利的投入被严重低估其性价比</strong>：20–40 小时换一个长期资产 + 简历硬指标，且它<em>不要求工作达到发表水平</em>（很多不够发论文的工程改进是可专利的）。",
            "<strong>内部文档的价值最高但最不被认可</strong>——这是一个真实的激励错配。<em>缓解办法是把文档做成可见的产出</em>（在演示里提、在周报里列、让新人在 onboarding 时引用它）。",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>研究的价值不等于研究的产出——中间隔着一次「把技术工作翻译成组织能消费的形式」的转换，而这个转换是你的责任，不是别人的</strong>。<em>同一份工作，翻译成「一次带明确 ask 的演示 + 一份发明披露 + 一份内部文档」与翻译成「一份写得很好的技术报告」，产生的影响可以差一个数量级</em>。<strong>而这个转换的成本远低于研究本身的成本</strong>——这就是为什么它值得刻意练习。"),
    ])),
    ("timeline", "把三种产出排进同一条时间线", "".join([
        P("最后一件实操：<strong>专利、论文、开源、演示不是四个独立的选择，而是同一份工作的四种表达，它们之间有<em>顺序约束</em></strong>。把它们排错，最好的情况是浪费时间，最坏的情况是永久失去专利权。"),
        ASCII("""结果出来（Day 0）
  │
  ├─ 立刻：**内部演示**（4–12 h）
  │     不需要等任何审批；决定这份工作会不会被继续投入
  │     ⚠️ 但演示材料本身不要外发、不要贴到有外部人的频道
  │
  ├─ 第 1 周：**发明披露**（20–40 h，可与其它事并行）
  │     ⚠️ **必须在任何对外公开之前** —— 这是唯一不可逆的约束
  │     不需要论文写完，只需说清方法与结果
  │
  ├─ 第 2–8 周：法务评估 + 内容审查（你只需响应问题）
  │     └─ 若决定申请：等临时申请提交后才能公开
  │
  ├─ 并行：**写论文**（200–400 h）
  │     写作与专利流程可以并行 —— 只要不投出去
  │
  ├─ 第 8 周起：投稿 / 开源发布
  │     └─ 开源还要过依赖许可审查（模块第 4 节）
  │
  └─ 持续：**内部文档**（8–40 h）
        写的最佳时机是「刚解决完问题、上下文还在脑子里」""")
        ,
        DUAL(
            "这条时间线的关键洞察是：<strong>只有「发明披露」有硬性的顺序约束，其余都可以并行</strong>。很多人把它理解成一条串行流水线（先专利、再论文、再开源），于是觉得内部流程拖慢了一切。<em>实际上你可以在披露提交的第二天就开始写论文、做内部演示、写文档</em>——唯一不能做的是<strong>把内容对外公开</strong>。理解这个差别，能把「2–8 周的等待」变成「2–8 周的并行工作」。",
            "第二个洞察是<strong>「内部演示应该排在最前面，而不是最后」</strong>。很多人的顺序是「等结果足够好 → 写完论文 → 再讲给内部听」，这意味着<em>你在没有任何反馈的情况下投入了几百小时</em>。而演示只要 4–12 小时，且能立刻回答「这个方向值不值得继续」「有没有人已经试过」「产品侧关心的是不是这个指标」。<strong>把最便宜、反馈最快的那个产出放在最前面</strong>——这是标准的工程直觉，只是很多人不把它用在自己的产出规划上。",
        ),
        CALLOUT("warn", "时间线里有一个陷阱值得单独标出：<strong>「内部演示」虽然不需要审批，但它的材料仍可能构成公开</strong>。如果听众里有外部人员（合作方、客户、实习生的学校导师）、或者你把幻灯片贴到了对外可见的地方，<em>那就是一次公开披露</em>。<strong>安全做法：在披露提交之前，内部演示的材料只在明确的内部渠道流转，并在首页标注保密级别</strong>。这个动作只要五秒，但能避免一个不可逆的损失。"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>AI 生成内容的知识产权</strong>：模型生成的代码/文本的版权归属、AI 是否可为发明人（多国已判定不可）、训练数据的合理使用边界——<em>这些都在快速变化的判例与立法中</em>。实践建议：记录人类的实质贡献，不要依赖尚未确立的规则。",
            "<strong>训练数据的合规</strong>：多起诉讼正在界定「用受版权保护的数据训练」的合法性，各辖区结论可能不同。<em>工程侧能做的是保持数据溯源可查</em>（每个数据源的来源、许可、获取日期），这样无论规则如何演变都能应对。",
            "<strong>模型许可的碎片化</strong>：各家自定义许可（用户数阈值、禁止改进竞品、可接受使用政策）互不兼容，且多数不是 OSI 认可的开源许可。<em>「开源模型」这个词已经严重失去精确性</em>——OSI 的 Open Source AI Definition 是一次收敛尝试，采纳情况仍在演进。",
            "<strong>可复现性与 artifact 评审</strong>：主要会议逐步引入 artifact evaluation 与 checklist，但工业界的论文常因不能开源代码/数据而受影响。<em>「在不公开数据的前提下如何提供可信的可复现性」是一个未解决的张力</em>。",
            "<strong>专利与开源的共存</strong>：Apache-2.0 的专利授权条款、OIN 等专利联盟、防御性专利承诺——生态在探索「既申请专利又参与开源」的机制。<em>对个人的实践含义是：申请专利与开源发布不一定互斥，但顺序与许可选择需要设计</em>。",
        ]),
        CALLOUT("paper", "必读（工程视角，非法律意见）：USPTO 的 <em>Subject Matter Eligibility</em> 指南（尤其 AI 相关的示例，能让你理解「算法 + 技术效果」为什么重要）；EPO 的 <em>Guidelines for Examination, G-II 3.3</em>（欧洲对计算机实现发明的标准，与美国不同）；<strong>choosealicense.com</strong> 与 SPDX 许可清单（日常查许可的两个入口）；GNU 的 <em>License Compatibility</em> 页面（copyleft 的传染规则）；OSI 的 <em>Open Source AI Definition</em>（理解「开源模型」争议）。演示与写作：Simon Peyton Jones 的 <em>How to Give a Great Research Talk</em>（学术侧的经典，注意本模块讲的内部演示模板与它不同）、Barbara Minto 的金字塔原理（「结论先行」的出处）。相邻课程：C48（部署与合规环境）、本课模块 00 的交付契约。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 研究产出与知识产权（可专利性自检 / 权利要求结构 / 许可兼容 / 演示模板）

> ⚠️ **本 notebook 是工程视角的实用工具，不是法律意见。** 真实的专利申请、许可合规判断
> 必须由法务/IP 部门或执业律师做。这里的目标是让你**知道该在什么时候找他们、带什么材料去**。

目标：把 **可专利性三门槛 → 权利要求宽窄 → 发明披露书 → 许可兼容矩阵 → 演示结构检查**
做成可运行的检查器。

路线：可专利性自检（含「公开即丧失」的硬拦截）→ 权利要求宽窄与绕过分析 →
披露书完整性检查 → 许可兼容矩阵与**AGPL 的网络触发** → 依赖树传染性传播 →
演示结构检查（结论先行 / 明确 ask）→ 产出投入产出账 → ✏️ 练习 → 📖 答案 → 🧪 模板胶囊。

> 心智模型：**研究的价值 ≠ 研究的产出。中间隔着一次「翻译成组织能消费的形式」的转换，
> 而这个转换是你的责任。**"""),
    md("""## 1 · 可专利性自检：三个门槛 + 一个硬拦截"""),
    code("""import numpy as np, collections, itertools, json, textwrap

DISCLOSURE_KINDS = ['arxiv', 'paper', 'blog', 'open_source', 'public_talk',
                    'public_commit', 'customer_demo', 'none']

def patentability_selfcheck(invention):
    '''工程视角的自检。返回 (verdict, 逐项结论)。verdict: 'blocked'|'weak'|'promising'。'''
    notes, blocking = [], False

    # 硬拦截：已公开 -> 新颖性丧失（多数辖区不可逆）
    pub = invention.get('public_disclosure', 'none')
    if pub != 'none':
        blocking = True
        notes.append(f'❌ **硬拦截**：已通过 {pub} 公开 -> 新颖性可能已丧失。'
                     f'立刻找法务（美国有 12 个月宽限期，但不适用于所有辖区）')
    else:
        notes.append('✅ 尚未对外公开 -> 新颖性门槛未被破坏')

    # 门槛 1：新颖性（相对现有技术）
    if invention.get('closest_prior_art_delta', '') in ('', 'none'):
        notes.append('🔶 新颖性：说不清与最接近现有技术的差别 -> 先做检索')
    else:
        notes.append(f'✅ 新颖性：与现有技术的差别 = {invention["closest_prior_art_delta"]}')

    # 门槛 2：非显而易见性 —— **「非预期的效果」是最有力的论据**
    if invention.get('unexpected_effect'):
        notes.append(f'✅ 非显而易见：有非预期效果「{invention["unexpected_effect"]}」（强论据）')
    elif invention.get('is_transfer_only'):
        notes.append('🔶 非显而易见：只是「把 A 方法用到 B 任务」-> 常被认为显而易见')
    else:
        notes.append('🔶 非显而易见：只有「按预期地好一点」-> 论据偏弱')

    # 门槛 3：可专利主题 —— **算法 + 具体技术效果**
    tech = invention.get('technical_effect')
    if tech:
        notes.append(f'✅ 可专利主题：绑定了具体技术效果「{tech}」')
    else:
        notes.append('❌ 可专利主题：纯算法/数学，未绑定技术效果 -> 很难通过')

    strong = sum(1 for n in notes if n.startswith('✅'))
    if blocking:
        v = 'blocked'
    elif strong >= 3 and tech:
        v = 'promising'
    else:
        v = 'weak'
    return v, notes

INVENTIONS = [
    ('已发 arXiv 的好想法', dict(
        public_disclosure='arxiv', closest_prior_art_delta='动态权重调度',
        unexpected_effect='参数更少反而更鲁棒', technical_effect='推理显存降低 40%')),
    ('纯损失函数改进', dict(
        public_disclosure='none', closest_prior_art_delta='新的正则项',
        technical_effect=None)),
    ('A 方法搬到 B 任务', dict(
        public_disclosure='none', closest_prior_art_delta='应用领域不同',
        is_transfer_only=True, technical_effect='端到端延迟降低 15%')),
    ('绑定技术效果 + 非预期收益', dict(
        public_disclosure='none', closest_prior_art_delta='训练中动态调整损失权重',
        unexpected_effect='减少参数反而提升鲁棒性',
        technical_effect='推理显存降低 40%，无需改动推理代码')),
]
for name, inv in INVENTIONS:
    v, notes = patentability_selfcheck(inv)
    print(f'=== {name} -> **{v}** ===')
    for n in notes: print('   ' + n)
    print()

assert patentability_selfcheck(INVENTIONS[0][1])[0] == 'blocked', '已公开 -> 硬拦截'
assert patentability_selfcheck(INVENTIONS[1][1])[0] == 'weak', '纯算法无技术效果 -> 弱'
assert patentability_selfcheck(INVENTIONS[3][1])[0] == 'promising'
print('⚠️  **「先发 arXiv 占坑再申请专利」在多数辖区不可行** ——')
print('    正确顺序：有想法 -> 记录（带日期）-> 内部披露 -> 法务确认 -> 再决定公开。')
print('✅ 把「算法创新」翻译成「技术问题 + 技术手段 + **技术效果**」三段式，是关键动作。')"""),
    md("""## 2 · 权利要求的宽窄：绕过分析

**「如果竞争者要绕过我的专利，最小的改动是什么？」** 花十分钟，能显著提升专利质量。"""),
    code("""class Claim:
    def __init__(self, limitations):
        self.limitations = list(limitations)     # 每条限定
    def breadth(self):
        '''限定越多，保护范围越窄。'''
        return 1.0 / (1 + len(self.limitations))
    def covers(self, implementation):
        '''实现必须满足**所有**限定才落入保护范围。'''
        return all(any(lim in feat for feat in implementation) for lim in self.limitations)
    def __repr__(self):
        return '一种方法，包括：\\n' + '\\n'.join(
            f'  {chr(97+i)}) {l}' for i, l in enumerate(self.limitations))

# 过窄的权利要求：把实现细节都写进去了
narrow = Claim(['使用 ReLU 激活', '在 Transformer 的第 12 层', '使用 fp16 精度',
                '动态调整损失权重'])
# 合理宽度：只保留发明的核心机制
broad = Claim(['在训练过程中根据中间层统计量动态调整损失权重'])

IMPLS = {
    '我的实现':        ['使用 ReLU 激活', '在 Transformer 的第 12 层', '使用 fp16 精度',
                        '在训练过程中根据中间层统计量动态调整损失权重', '动态调整损失权重'],
    '竞争者：换 GELU': ['使用 GELU 激活', '在 Transformer 的第 12 层', '使用 fp16 精度',
                        '在训练过程中根据中间层统计量动态调整损失权重', '动态调整损失权重'],
    '竞争者：换 bf16': ['使用 ReLU 激活', '在 Transformer 的第 12 层', '使用 bf16 精度',
                        '在训练过程中根据中间层统计量动态调整损失权重', '动态调整损失权重'],
    '竞争者：第 8 层': ['使用 ReLU 激活', '在 Transformer 的第 8 层', '使用 fp16 精度',
                        '在训练过程中根据中间层统计量动态调整损失权重', '动态调整损失权重'],
    '真正不同的方案':  ['使用固定的损失权重', '在 Transformer 的第 12 层'],
}
print(f"{'实现':<22s} {'过窄的权利要求':>16s} {'合理宽度':>12s}")
for name, impl in IMPLS.items():
    print(f'{name:<22s} {("落入 ❌被覆盖" if narrow.covers(impl) else "绕过 ✅"):>18s} '
          f'{("落入" if broad.covers(impl) else "绕过"):>12s}')

assert narrow.covers(IMPLS['我的实现'])
assert not narrow.covers(IMPLS['竞争者：换 GELU']), '换个激活函数就绕过了过窄的权利要求'
assert broad.covers(IMPLS['竞争者：换 GELU']), '合理宽度仍覆盖'
assert not broad.covers(IMPLS['真正不同的方案']), '不该覆盖真正不同的方案'
assert broad.breadth() > narrow.breadth()
print(f'\\n保护范围: 过窄 {narrow.breadth():.2f} vs 合理 {broad.breadth():.2f}')
print('\\n⚠️  过窄的权利要求：竞争者「把 ReLU 换成 GELU」就绕过了。')
print('✅ 你（发明人）的独特贡献是**列出所有能想到的变体** ——')
print('   不同架构、不同精度、不同粒度、不同层。让代理人决定哪些进权利要求。')

VARIANTS = ['任意激活函数（ReLU/GELU/SiLU）', '任意层（不限第 12 层）',
            '任意精度（fp32/fp16/bf16/int8）', '任意统计量（均值/方差/范数/梯度范数）',
            '也适用于 CNN 与 RNN，不限 Transformer',
            '权重调整可以是连续的或离散分档的']
print(f'\\n变体清单（披露书第 ⑤ 节，最容易被跳过也最有价值）：')
for v in VARIANTS: print(f'  · {v}')
assert len(VARIANTS) >= 5"""),
    md("""## 3 · 发明披露书的完整性检查"""),
    code("""REQUIRED_SECTIONS = {
    'problem':        '① 现有技术解决不了什么**技术**问题',
    'prior_art':      '② 最接近的已有方案，以及为什么不够（诚实列出）',
    'solution':       '③ 核心机制（配图/伪代码，越具体越好）',
    'why_works':      '④ 机制解释 + 实验证据（标注非预期效果）',
    'variants':       '⑤ 所有能想到的替代实现（**最易跳过、最有价值**）',
    'timeline':       '⑥ 构思日期 / 是否对外提过 / 代码在哪（**决定还能不能申请**）',
}

def check_disclosure(doc):
    missing = [k for k in REQUIRED_SECTIONS if not doc.get(k)]
    warnings = []
    if doc.get('variants') and len(doc['variants']) < 3:
        warnings.append('⑤ 变体少于 3 条 -> 权利要求可能过窄')
    tl = doc.get('timeline') or {}
    if tl.get('public_disclosure', 'none') != 'none':
        warnings.append(f'⑥ 已通过 {tl["public_disclosure"]} 公开 -> **立刻找法务**')
    if not tl.get('conception_date'):
        warnings.append('⑥ 缺构思日期 -> 优先权与发明人认定会有麻烦')
    return {'missing': missing, 'warnings': warnings,
            'ok': not missing and not warnings}

draft = {
    'problem': '长序列训练时激活显存随序列长平方增长，限制了可用的上下文长度',
    'prior_art': 'FlashAttention 解决注意力矩阵，但 FFN 中间激活仍是瓶颈；'
                 '梯度检查点全局重算，代价 30% 计算',
    'solution': '按中间层统计量动态选择哪些层重算，形成自适应的重算策略',
    'why_works': '显存-计算的帕累托前沿更优；**非预期效果**：重算的层数减少后收敛更快',
    'variants': VARIANTS,
    'timeline': {'conception_date': '2026-03-14', 'public_disclosure': 'none',
                 'code': 'internal-git/exp/adaptive-ckpt'},
}
r = check_disclosure(draft)
print('完整披露书检查:', r)
assert r['ok'], r

incomplete = {k: v for k, v in draft.items() if k not in ('variants', 'why_works')}
r2 = check_disclosure(incomplete)
print('\\n缺 ④⑤ 的草稿:')
for k in r2['missing']: print(f'   缺 {REQUIRED_SECTIONS[k]}')
assert set(r2['missing']) == {'variants', 'why_works'}

leaked = dict(draft); leaked['timeline'] = dict(draft['timeline'],
                                                public_disclosure='public_talk')
r3 = check_disclosure(leaked)
assert any('立刻找法务' in w for w in r3['warnings'])
print(f'\\n已公开的草稿: {r3["warnings"]}')
print('\\n⚠️  即使是「内部但有外部人参加的会议」、「公开 Slack 频道」、「公开仓库 commit」、')
print('    「给客户做 demo」都可能构成公开。**先记录、先披露，再决定公开与否。**')"""),
    md("""## 4 · 许可兼容矩阵：日常最容易踩的坑"""),
    code("""LICENSES = {
    'MIT':          dict(kind='permissive', copyleft=0, network_trigger=False, commercial=True),
    'BSD-3-Clause': dict(kind='permissive', copyleft=0, network_trigger=False, commercial=True),
    'Apache-2.0':   dict(kind='permissive', copyleft=0, network_trigger=False, commercial=True),
    'LGPL-3.0':     dict(kind='weak-copyleft', copyleft=1, network_trigger=False, commercial=True),
    'GPL-2.0':      dict(kind='strong-copyleft', copyleft=2, network_trigger=False, commercial=True),
    'GPL-3.0':      dict(kind='strong-copyleft', copyleft=2, network_trigger=False, commercial=True),
    'AGPL-3.0':     dict(kind='network-copyleft', copyleft=3, network_trigger=True, commercial=True),
    'CC-BY-NC-4.0': dict(kind='non-commercial', copyleft=0, network_trigger=False, commercial=False),
    'Llama-Community': dict(kind='custom', copyleft=0, network_trigger=False, commercial='conditional'),
}

def can_use(license_name, product_closed_source, distributed, network_service,
            commercial_use=True):
    '''工程视角的粗筛。真实判断交法务。'''
    L = LICENSES[license_name]
    if commercial_use and L['commercial'] is False:
        return False, f'{license_name} 禁止商业使用'
    if L['commercial'] == 'conditional':
        return 'review', f'{license_name} 是自定义许可（用户数阈值/可接受使用政策）-> **逐条读**'
    if L['copyleft'] == 0:
        return True, f'{license_name} 宽松许可，闭源产品可用（保留声明/标注修改）'
    if not product_closed_source:
        return True, f'{license_name}：你的产品本身开源 -> 兼容'
    # 闭源产品 + copyleft
    if L['network_trigger'] and network_service:
        return False, (f'{license_name}：**「通过网络提供服务」即触发开源义务** '
                       f'-> 闭源 SaaS 不可用（最容易踩的坑）')
    if L['copyleft'] >= 2 and distributed:
        return False, f'{license_name}：分发衍生作品必须同样开源 -> 闭源产品不可用'
    if L['copyleft'] == 1:
        return 'review', f'{license_name}：动态链接通常可以，静态链接有争议 -> 交法务'
    if L['copyleft'] >= 2 and not distributed and not network_service:
        return True, f'{license_name}：仅内部使用、不分发 -> 义务未触发（但别以此为长期策略）'
    return 'review', f'{license_name}：边界情形 -> 交法务'

SCENARIOS = [
    ('闭源 SaaS 推理服务', True, False, True),
    ('闭源本地分发的 App', True, True, False),
    ('仅内部使用的工具',   True, False, False),
    ('我们自己也开源',     False, True, True),
]
for sc, closed, dist, net in SCENARIOS:
    print(f'=== {sc} ===')
    for lic in ['MIT', 'Apache-2.0', 'LGPL-3.0', 'GPL-3.0', 'AGPL-3.0',
                'CC-BY-NC-4.0', 'Llama-Community']:
        ok, why = can_use(lic, closed, dist, net)
        mark = {True: '✅', False: '❌', 'review': '🔶'}[ok]
        print(f'  {mark} {lic:<18s} {why}')
    print()

assert can_use('AGPL-3.0', True, False, True)[0] is False, 'AGPL + 闭源 SaaS -> 不行'
assert can_use('GPL-3.0', True, False, False)[0] is True, 'GPL + 仅内部使用 -> 义务未触发'
assert can_use('GPL-3.0', True, True, False)[0] is False, 'GPL + 分发 -> 不行'
assert can_use('CC-BY-NC-4.0', True, False, False)[0] is False, 'NC 禁止商业使用'
assert can_use('MIT', True, True, True)[0] is True
print('⚠️  **AGPL 打破了「不分发就没有义务」这个直觉** ——')
print('    GPL 的义务在分发时触发（内部使用安全）；')
print('    AGPL 的义务在「通过网络提供功能」时就触发 —— 这正是所有 AI 服务的形态。')
print('⚠️  **大量数据集是 CC-BY-NC** —— 训练商业模型即违约。')"""),
    code("""# copyleft 的传染性：沿依赖树传播
DEPS = {
    'my-service':   ['inference-lib', 'vector-db', 'utils'],
    'inference-lib':['onnxruntime', 'numpy'],
    'vector-db':    ['some-agpl-index'],          # ← 藏在二级依赖里
    'utils':        ['requests'],
    'onnxruntime':  [], 'numpy': [], 'requests': [], 'some-agpl-index': [],
}
DEP_LICENSE = {
    'inference-lib': 'Apache-2.0', 'vector-db': 'MIT', 'utils': 'MIT',
    'onnxruntime': 'MIT', 'numpy': 'BSD-3-Clause', 'requests': 'Apache-2.0',
    'some-agpl-index': 'AGPL-3.0',                # ← 真正的问题在这里
}

def scan_licenses(root, deps, lic):
    '''遍历依赖树，返回 (全部许可, 最强 copyleft, 路径)。'''
    seen, worst, path_to_worst = set(), None, None
    def walk(node, path):
        nonlocal worst, path_to_worst
        if node in seen: return
        seen.add(node)
        L = lic.get(node)
        if L:
            cl = LICENSES[L]['copyleft']
            if worst is None or cl > LICENSES[worst]['copyleft']:
                worst, path_to_worst = L, path + [node]
        for d in deps.get(node, []):
            walk(d, path + [node])
    walk(root, [])
    return sorted({lic[n] for n in seen if n in lic}), worst, path_to_worst

all_lic, worst, path = scan_licenses('my-service', DEPS, DEP_LICENSE)
print('依赖树里的全部许可:', all_lic)
print(f'最强 copyleft: **{worst}**')
print('传播路径: ' + ' -> '.join(path))
ok, why = can_use(worst, product_closed_source=True, distributed=False, network_service=True)
print(f'\\n闭源 SaaS 场景下: {"✅" if ok is True else "❌" if ok is False else "🔶"} {why}')
assert worst == 'AGPL-3.0' and ok is False
assert 'some-agpl-index' in path and 'vector-db' in path
print('\\n⚠️  问题藏在**二级依赖**里：vector-db 自己是 MIT，但它依赖一个 AGPL 的索引库。')
print('✅ 两条操作规则：')
print('   ① 许可检查要在**引入依赖时**做，不是发布前做（发布前发现要重写已写好的代码）')
print('   ② **不要自己判断边界情形** —— 你的职责是准确记录「用了什么、什么许可、怎么用」')"""),
    md("""## 5 · 演示结构检查：结论先行 + 明确 ask"""),
    code("""ACADEMIC_TEMPLATE = ['背景与动机', '相关工作', '方法', '实验设置', '结果',
                     '消融实验', '结论与未来工作']
INTERNAL_TEMPLATE = ['结论与建议', '为什么值得做（1 张）', '关键证据',
                     '代价与风险', '与现有方案的对比', '**明确的 ask**']

def check_talk_structure(slide_titles, ask=None, time_split=None):
    problems = []
    # ① 结论先行
    first = slide_titles[0] if slide_titles else ''
    if not any(k in first for k in ['结论', '建议', '要点', 'TL;DR', '我们发现']):
        problems.append(f'① 第一张是「{first}」而不是结论 -> 听众可能只听前五分钟')
    # ② 标题应是断言而不是章节名
    section_names = ['背景', '相关工作', '方法', '实验设置', '结果', '消融', '未来工作']
    generic = [t for t in slide_titles if any(t.strip() == s for s in section_names)]
    if generic:
        problems.append(f'② 标题是章节名而非断言: {generic} -> 连起来读不成论证')
    # ③ 必须有明确 ask
    if not ask:
        problems.append('③ 没有明确的 ask -> 最好的结果是「挺有意思」，然后什么都不发生')
    elif not any(k in ask for k in ['批准', '决定', '评估', '分配', '由']):
        problems.append(f'③ ask 不够具体（「{ask}」）-> 要说清谁在什么时候做什么决定')
    # ④ 时间分配
    if time_split and time_split.get('method', 0) > 0.4:
        problems.append(f'④ 方法占 {time_split["method"]:.0%} -> 内部演示应 ~20% 方法、'
                        f'80% 影响与代价')
    # ⑤ 必须讲局限
    if not any('风险' in t or '代价' in t or '局限' in t for t in slide_titles):
        problems.append('⑤ 没有代价/风险页 -> 听众无法评估风险，通常会因此不批准')
    return {'problems': problems, 'ok': not problems}

bad = check_talk_structure(ACADEMIC_TEMPLATE, ask=None,
                           time_split={'method': 0.8, 'impact': 0.2})
print('用学术模板做内部演示:')
for p_ in bad['problems']: print('   ❌ ' + p_)
assert len(bad['problems']) >= 4

good_titles = ['结论：自适应重算把显存降 40%，精度损失 0.3 分',
               '为什么值得做：解锁 32k 上下文，无需换卡',
               '关键证据：3 个模型 × 2 个数据集上稳定复现',
               '代价与风险：训练慢 8%；长序列下需重新调参',
               '与现有方案对比：优于全局梯度检查点（快 22%）',
               'ask：批准 200 GPU 小时做 70B 规模验证']
good = check_talk_structure(good_titles,
                            ask='批准 200 GPU 小时做 70B 规模验证，由平台组在两周内评估集成成本',
                            time_split={'method': 0.2, 'impact': 0.8})
print('\\n用内部演示模板:')
print('   ✅ 通过' if good['ok'] else good['problems'])
assert good['ok'], good['problems']

print('\\n两个立刻可用的检查:')
print('  ① 只看第一张和最后一张 —— 一个只看这两张的人能做出决定吗？')
print('  ② 把所有标题连起来读 —— 应该构成一个完整的论证。')
print('     **标题应该是断言**（「显存降 40%，精度损失 0.3 分」），不是章节名（「结果」）。')
first_last = [good_titles[0], good_titles[-1]]
assert '结论' in first_last[0] and 'ask' in first_last[1]
print(f'\\n本例的第一张+最后一张:\\n  {first_last[0]}\\n  {first_last[1]}')
print('✅ 能据此做决定 -> 结构合格。')"""),
    md("""## 6 · 产出形式的投入产出账"""),
    code("""OUTPUTS = [
    ('专利（一件）',      30,   'high',   'high',   '1–4 年'),
    ('顶会论文（一篇）',  300,  'medium', 'high',   '6–18 个月'),
    ('内部演示（一次）',  8,    'high',   'high',   '即时'),
    ('开源发布',          80,   'medium', 'medium', '数周–数月'),
    ('内部文档/工具',     20,   'high',   'low',    '持续'),
]
SCORE = {'high': 3, 'medium': 2, 'low': 1}

print(f"{'产出':<20s} {'工时':>6s} {'公司价值':>9s} {'个人价值':>9s} "
      f"{'性价比':>8s} {'时间到价值'}")
rows = []
for name, hours, comp, pers, t2v in OUTPUTS:
    roi = (SCORE[comp] + SCORE[pers]) / hours * 100
    rows.append((name, roi))
    print(f'{name:<20s} {hours:>6d} {comp:>9s} {pers:>9s} {roi:>8.1f} {t2v}')

rows.sort(key=lambda r: -r[1])
print(f'\\n按性价比排序: ' + ' > '.join(n for n, _ in rows))
best = rows[0][0]
assert '内部演示' in best, f'内部演示应性价比最高，实际 {best}'
paper_roi = dict(rows)['顶会论文（一篇）']
talk_roi = dict(rows)['内部演示（一次）']
assert talk_roi > paper_roi * 10
print(f'\\n✅ 内部演示的性价比是论文的 {talk_roi/paper_roi:.0f} 倍（8 小时 vs 300 小时），')
print('   而且它**直接决定你的工作是否被采用**。很多人在论文上投入过度、演示上投入不足。')
patent_roi = dict(rows)['专利（一件）']
assert patent_roi > paper_roi
print(f'✅ 专利的性价比也高于论文（{patent_roi:.1f} vs {paper_roi:.1f}），且**不要求达到发表水平** ——')
print('   很多不够发论文的工程改进是可专利的。')
print('⚠️  内部文档价值最高但最不被认可（激励错配）。缓解：把它做成可见的产出。')"""),
    md("""## ✏️ 练习 1：公开前的门禁检查

实现 `publication_gate(item)`：`item` 含
`{'kind': 'paper'|'blog'|'open_source'|'talk', 'ip_disclosed': bool,
'ip_cleared': bool, 'content_reviewed': bool, 'license_reviewed': bool,
'contains_customer_data': bool, 'weeks_until_deadline': int}`。
返回 `{'allowed': bool, 'blockers': [...], 'warnings': [...]}`。
规则：未披露或未获 IP 放行 → 阻断；未过内容审查 → 阻断；含客户数据 → 阻断；
`open_source` 且未做许可审查 → 阻断；剩余时间 < 3 周 → 警告（流程通常要 2–8 周）。"""),
    code("""def publication_gate(item):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
ready = dict(kind='paper', ip_disclosed=True, ip_cleared=True, content_reviewed=True,
             license_reviewed=True, contains_customer_data=False, weeks_until_deadline=8)
assert publication_gate(ready)['allowed']
no_ip = dict(ready, ip_disclosed=False)
r = publication_gate(no_ip)
assert not r['allowed'] and any('披露' in b for b in r['blockers'])
cust = dict(ready, contains_customer_data=True)
assert not publication_gate(cust)['allowed']
oss = dict(ready, kind='open_source', license_reviewed=False)
r2 = publication_gate(oss)
assert not r2['allowed'] and any('许可' in b for b in r2['blockers'])
rush = dict(ready, weeks_until_deadline=1)
r3 = publication_gate(rush)
assert r3['allowed'] and r3['warnings'], '时间紧应给警告而不是阻断'
for name, it in [('齐备', ready), ('未披露', no_ip), ('含客户数据', cust),
                 ('开源未查许可', oss), ('只剩一周', rush)]:
    g = publication_gate(it)
    print(f'{name:<14s} allowed={str(g["allowed"]):<6s} '
          f'blockers={g["blockers"]} warnings={g["warnings"]}')
print('✅ 练习 1 通过：**内部流程要 2–8 周，投稿截止前一周才启动是来不及的**')"""),
    md("""## ✏️ 练习 2：依赖许可清单

实现 `license_manifest(deps, dep_license, usage)`：`usage` 含
`{'closed_source': bool, 'distributed': bool, 'network_service': bool}`。
返回 `{'blockers': [(依赖, 许可, 原因)], 'reviews': [...], 'ok': bool}`——
对每个依赖调用 `can_use`，`False` 进 blockers，`'review'` 进 reviews。"""),
    code("""def license_manifest(deps, dep_license, usage):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
USAGE_SAAS = dict(closed_source=True, distributed=False, network_service=True)
m = license_manifest(DEPS, DEP_LICENSE, USAGE_SAAS)
assert not m['ok']
assert any(d == 'some-agpl-index' for d, _, _ in m['blockers']), m['blockers']
clean = {k: v for k, v in DEP_LICENSE.items() if k != 'some-agpl-index'}
m2 = license_manifest({k: [d for d in v if d != 'some-agpl-index']
                       for k, v in DEPS.items()}, clean, USAGE_SAAS)
assert m2['ok'], m2
lgpl = dict(clean); lgpl['utils'] = 'LGPL-3.0'
m3 = license_manifest(DEPS, lgpl, USAGE_SAAS)
assert any(d == 'utils' for d, _, _ in m3['reviews']), 'LGPL 应进 review 而不是 blocker'
print('SaaS + 含 AGPL:')
for d, l, why in m['blockers']: print(f'   ❌ {d} ({l}): {why}')
print(f'\\n清理后: ok={m2["ok"]}')
print(f'含 LGPL: reviews={[(d,l) for d,l,_ in m3["reviews"]]}')
print('✅ 练习 2 通过：**问题常藏在二级依赖里**，要遍历整棵树')"""),
    md("""## ✏️ 练习 3：演示改写

实现 `rewrite_titles(academic_titles, findings)`：把学术章节名改写成断言式标题。
`findings` 是 `{章节名: 断言}` 的映射；没有对应断言的章节保留原名并在返回的
第二个元素里报出来。返回 `(新标题列表, 未改写的章节列表)`。"""),
    code("""def rewrite_titles(academic_titles, findings):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
FINDINGS = {
    '背景与动机': '32k 上下文被激活显存卡住，这是当前最大的产品限制',
    '方法': '按层统计量自适应选择重算的层',
    '结果': '显存降 40%，精度损失 0.3 分，训练慢 8%',
    '消融实验': '统计量的选择不敏感；层数阈值是唯一需要调的超参',
}
new, missed = rewrite_titles(ACADEMIC_TEMPLATE, FINDINGS)
assert len(new) == len(ACADEMIC_TEMPLATE)
assert new[0] == FINDINGS['背景与动机']
assert set(missed) == {'相关工作', '实验设置', '结论与未来工作'}, missed
for t in new: print('  ·', t)
print(f'\\n未改写: {missed}')
res = check_talk_structure(new, ask='批准 200 GPU 小时', time_split={'method': 0.2})
print(f'改写后的结构检查: {len(res["problems"])} 个问题（原本 '
      f'{len(check_talk_structure(ACADEMIC_TEMPLATE)["problems"])} 个）')
assert len(res['problems']) < len(check_talk_structure(ACADEMIC_TEMPLATE)['problems'])
print('✅ 练习 3 通过：**标题是断言，连起来读成一个完整论证**')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def publication_gate(item):
    blockers, warnings = [], []
    if not item.get('ip_disclosed'):
        blockers.append('未做内部发明披露 -> 公开会永久丧失新颖性')
    elif not item.get('ip_cleared'):
        blockers.append('IP 评估未放行（等法务确认是否先申请专利）')
    if not item.get('content_reviewed'):
        blockers.append('未过内容审查（产品计划/客户信息/受限数据）')
    if item.get('contains_customer_data'):
        blockers.append('含客户数据 -> 合同与隐私风险，必须移除或获授权')
    if item.get('kind') == 'open_source' and not item.get('license_reviewed'):
        blockers.append('开源发布未做依赖许可审查')
    if item.get('weeks_until_deadline', 99) < 3:
        warnings.append(f'距截止仅 {item["weeks_until_deadline"]} 周，'
                        f'而内部流程通常要 2–8 周')
    return {'allowed': not blockers, 'blockers': blockers, 'warnings': warnings}"""),
    code("""# 练习 2 参考答案
def license_manifest(deps, dep_license, usage):
    seen = set()
    def walk(node):
        if node in seen: return
        seen.add(node)
        for d in deps.get(node, []): walk(d)
    for root in deps: walk(root)
    blockers, reviews = [], []
    for d in sorted(seen):
        lic = dep_license.get(d)
        if not lic: continue
        ok, why = can_use(lic, usage['closed_source'], usage['distributed'],
                          usage['network_service'])
        if ok is False: blockers.append((d, lic, why))
        elif ok == 'review': reviews.append((d, lic, why))
    return {'blockers': blockers, 'reviews': reviews, 'ok': not blockers}"""),
    code("""# 练习 3 参考答案
def rewrite_titles(academic_titles, findings):
    new, missed = [], []
    for t in academic_titles:
        if t in findings:
            new.append(findings[t])
        else:
            new.append(t); missed.append(t)
    return new, missed"""),
    md("""---
## 🧪 模板胶囊：三份可直接复制的模板"""),
    code("""TEMPLATES = r'''
════════════════════════════════════════════════════════════════════
① 发明披露书模板（交给专利代理人的东西）
════════════════════════════════════════════════════════════════════
标题：
发明人（全部，按贡献）：
构思日期：____-__-__        ← **决定优先权，务必准确**
对外公开状态：□ 从未 □ 已通过 ______ 公开（若已公开，**立刻联系法务**）
代码位置：

① 技术问题
   现有技术在 ______ 场景下无法 ______，具体瓶颈是 ______。
   （写「技术瓶颈」，不要写「效果不够好」）

② 最接近的现有技术（诚实列出，隐瞒会在审查时反噬）
   · 方案 A：______ ，不足：______
   · 方案 B：______ ，不足：______

③ 本发明的方案（核心机制 + 伪代码/框图）

④ 为什么有效
   机制解释：______
   实验证据：______
   ⭐ **非预期的效果**：______        ← 非显而易见性的最有力论据

⑤ 变体（列尽所有能想到的替代实现 —— 最易跳过、最有价值）
   · 不同架构 / 不同精度 / 不同粒度 / 不同层 / 连续 vs 离散 …
   自问：「竞争者绕过我的最小改动是什么？」把答案也写进来。

⑥ 技术效果的量化（绑定具体技术效果，这决定可专利主题）
   ______ 降低 __%，在 ______ 条件下测得。

════════════════════════════════════════════════════════════════════
② 内部技术演示模板（6 张，每张标题都是断言）
════════════════════════════════════════════════════════════════════
1. 结论：<具体数字的断言>                        ← 第一张就给
2. 为什么值得做：<解锁了什么产品能力>
3. 关键证据：<多少模型 × 多少数据集上复现>
4. 代价与风险：<训练慢多少 / 需重调什么 / 什么情况下失效>   ← 必须有
5. 与现有方案对比：<只保留影响决策的比较>
6. ask：<谁 在 什么时候 做 什么决定 / 需要什么资源>          ← 必须具体

自检：只看第 1 张和第 6 张，一个人能做出决定吗？
自检：把 6 个标题连起来读，是一个完整论证吗？

════════════════════════════════════════════════════════════════════
③ 依赖许可清单（在**引入依赖时**填，不是发布前）
════════════════════════════════════════════════════════════════════
| 依赖/数据集/模型 | 版本 | 许可 | 用途 | 是否分发 | 是否网络服务 | 结论 |
|---|---|---|---|---|---|---|
| onnxruntime | 1.18 | MIT | 推理 | 否 | 是 | ✅ |
| <某向量库>  | ...  | MIT（但二级依赖含 AGPL！）| ... | 否 | 是 | ❌ 交法务 |
| <某数据集>  | ...  | CC-BY-NC | 训练 | — | — | ❌ 禁商用 |

规则一：许可检查在引入依赖时做（发布前发现要重写已写好的代码）
规则二：**不要自己判断边界情形**（静态链接、NC 数据训练的模型）—— 交法务
你的职责：准确记录「用了什么、什么许可、怎么用的」
'''
print(TEMPLATES)
for k in ['构思日期', '非预期的效果', '变体', 'ask', '二级依赖', 'CC-BY-NC']:
    assert k in TEMPLATES, k
print('✅ 三份模板覆盖：发明披露 / 内部演示 / 依赖许可清单')"""),
    md("""### 小结
- **公开即丧失新颖性**，且多数辖区不可逆。正确顺序：**有想法 → 记录（带日期）→ 内部披露 → 法务确认 → 再决定公开**。
  「先发 arXiv 占坑再申请专利」不是可行策略。
- **可专利主题的关键是把「算法创新」翻译成「技术问题 + 技术手段 + 技术效果」**。纯算法难，绑定具体技术效果容易。
- **「非预期的效果」是非显而易见性最有力的论据** —— 留意实验里那些反直觉的好结果。
- **权利要求过窄 = 竞争者稍改就绕过**。你（发明人）不可替代的贡献是**列尽所有变体**；
  自问「绕过我的最小改动是什么」。
- **AGPL 打破了「不分发就没有义务」的直觉**：网络提供服务即触发 —— 这正是所有 AI 服务的形态。
  **大量数据集是 CC-BY-NC**（禁商用）。问题常藏在**二级依赖**里。
- **许可检查在引入依赖时做，不是发布前**；**边界情形不要自己判断**，你的职责是准确记录。
- **内部演示 ≠ 学术报告**：结论先行、标题是断言、必须讲代价与风险、必须有具体的 ask。
  成功的定义是「产生了一个决定」，不是「讲清楚了」。
- **投入产出**：内部演示性价比是论文的数十倍；专利不要求达到发表水平；内部文档价值最高但最不被认可。
- **一句话**：研究的价值 ≠ 研究的产出。中间隔着一次「翻译成组织能消费的形式」的转换，
  而这个转换的成本远低于研究本身 —— 这就是它值得刻意练习的原因。

**C52 完结。** 至此这门课补齐了 JD 里的最后一批要求：TF/Keras 心智模型、跨框架迁移、
模型导出与运行时、真机 GPU 工作流、以及研究产出与知识产权。"""),
]
