# -*- coding: utf-8 -*-
"""C71 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "会写 Python；读过 C03 模块 03（prompt 敏感性）更好但不必需；"
                 "<strong>本课不需要任何模型调用</strong>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（一个可控的 in-context learning 模拟器：demo 上的 kNN + 近因偏置 + 先验 / '
                       '一个最小 prompt program / 四个靶子各注入一次并量出代价 / '
                       'prompt 指纹与「改一个字就是一次未记录的发布」）'),
    ("核心参考", "本课程 C03 模块 03（prompt 敏感性）与 06（elicitation）· "
                 "C33（上下文预算与压缩）· C67（judge：优化的目标函数从哪来）· "
                 "C68（把优化变成可门禁的流程）· "
                 "Khattab et al., <em>DSPy</em>（2023）· "
                 "Yang et al., <em>Large Language Models as Optimizers</em>（OPRO, 2024）"),
    ("预计时长", "读 40 分钟 + 跑 30 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("prompt-is-program", "prompt 不是文本，是程序", "".join([
        P("绝大多数系统里的 prompt 是一个字符串常量，"
          "它被反复手改、没有版本、没有测试、也没有指标。"
          "<strong>这门课的主张是：它其实是一个有结构、可组合、可测试、可优化的程序，"
          "而把它当程序对待会改变你能做的事。</strong>"),
        ASCII("""
   一次调用里，你实际上在控制四个独立的东西

   ┌──────────────────────────────────────────────────────────┐
   │ ① 指令 instruction    任务是什么、标签集是什么、边界在哪   │
   │ ② 示例 demos          选哪些、几个、什么顺序               │
   │ ③ 输出格式 format     字段、类型、如何解析                 │
   │ ④ 解码约束 decoding   哪些 token 在这一步是被允许的        │
   └──────────────────────────────────────────────────────────┘
        ▲          ▲              ▲              ▲
      本课 01     本课 02        本课 01/04      本课 04
                本课 03（把 ①②③ 变成一个可搜索的空间）
                本课 05（把它们变成可运维的资产）

   四个的失败方式完全不同：
     ① 缺标签集 → 模型自创标签 → **解析失败率 100%**（notebook 会量出来）
     ② 选错示例 → 准确率掉一半，而且没有任何报错
     ③ 没规定格式 → 解析失败，或者更糟：**只有一部分样本解析失败**
     ④ 没有约束 → 无效输出靠重试兜，而重试会引入选择偏倚
"""),
        DUAL(
            "为什么这个拆分重要？因为<strong>它们的成本与可控性差一个量级</strong>。"
            "<em>指令与格式几乎免费；示例选择要一次检索；"
            "自动优化要跑一整套评测；解码约束要改推理栈</em>。"
            "<strong>而把它们混成一个字符串时，你无法分别评估，"
            "也就无法知道该在哪里投入。</strong>",
            "更形式化一点：一次调用是"
            "$y \\sim \\text{Decode}\\big(M(\\cdot \\mid \\text{render}(I, D, F, x)), \\; C\\big)$，"
            "其中 $I$ 是指令、$D$ 是示例序列、$F$ 是格式规范、$x$ 是输入、"
            "$C$ 是解码约束、$M$ 是模型。"
            "<strong>「prompt 工程」通常只在改 $I$；"
            "而 $D$（选择与顺序）、$F$、$C$ 是三个独立的、可以被系统性优化的维度。</strong>"
            "<em>本课的每个模块对应其中一个或几个。</em>",
        ),
        CALLOUT("intuition", "一个判断系统成熟度的问题："
                             "<strong>「你们上一次改 prompt 是什么时候，改了什么，效果变化多少？」</strong>"
                             "<em>三个问题都答不上来，说明 prompt 还没有被当成代码</em>——"
                             "而它是唯一一处「改一个字就直接影响生产行为、"
                             "却通常不进 code review、不进 CI、不进版本记录」的地方。"),
    ])),

    # ============================================================== 2
    ("three-properties", "把它当程序对待，换来三条性质", "".join([
        TABLE(["性质", "含义", "没有它会怎样"], [
            ["<strong>可组合</strong>",
             "prompt 拆成有<em>签名</em>（输入/输出契约）的模块，模块之间可以串、可以换",
             "<strong>一个 800 行的字符串</strong>，改任何一处都可能影响别处，"
             "而没人敢删任何一句（「万一它有用」）"],
            ["<strong>可测试</strong>",
             "每个模块有自己的输入输出与断言；<em>格式合规性可以单独测，与效果解耦</em>",
             "只能端到端看一个数；<strong>格式问题与能力问题混在一起</strong>——"
             "「答错」和「没按格式答」被记成同一件事（C03 模块 03 的混淆变量）"],
            ["<strong>可优化</strong>",
             "$I, D, F$ 构成一个<strong>有限的搜索空间</strong>，"
             "而评测集给了目标函数——于是可以自动搜",
             "只能手改；<em>而手改的样本量通常是「我试了三个版本」</em>，"
             "这个样本量不足以区分改进与噪声（C68 模块 04 的阈值问题）"],
        ]),
        DUAL(
            "第三条是本课的核心，也是最容易被误解的一条。"
            "<strong>「自动提示优化」听起来像魔法，但它的机制很朴素</strong>："
            "<em>定义一个搜索空间、一个评分函数，然后搜</em>。"
            "<strong>而它的全部风险也都在这两个定义里</strong>——"
            "模块 03 会证明：<em>搜索空间定义不当会让搜索退化成噪声拟合，"
            "而评分函数与留出集的关系决定了搜出来的东西能不能上线</em>。",
            "还有一条不那么明显的收益：<strong>可优化性反过来约束了设计</strong>。"
            "<em>如果一个 prompt 的效果无法被自动评估，"
            "那么它也无法被可靠地手动改进</em>——"
            "因为你没有判断改动方向的依据。"
            "<strong>所以「先有评测集，再谈 prompt」不是流程洁癖，"
            "而是这一层能不能被工程化的前提。</strong>"
            "<em>这与 C67 的关系很直接：目标函数通常是一个 judge，"
            "而 judge 本身的正确性是 C67 的内容。</em>",
        ),
    ])),

    # ============================================================== 3
    ("map", "课程地图", "".join([
        TABLE(["模块", "主题", "核心主张（一句话）"], [
            ["<strong>01</strong>", "prompt program 与可组合结构",
             "<strong>给每个模块一个签名</strong>，"
             "把「格式合规」与「答得对不对」分成两个可以独立测的量"],
            ["<strong>02</strong>", "few-shot 示例选择与顺序",
             "示例不是「多放几个」——"
             "<strong>选择的收益远大于数量，而顺序的影响大到不能忽略</strong>"],
            ["<strong>03</strong>", "自动提示优化",
             "搜索空间 + 评分函数 = 一次优化；"
             "<strong>而它最大的风险是在留出集上不成立</strong>"],
            ["<strong>04</strong>", "受限解码与结构化输出",
             "约束能保证输出合法，"
             "<strong>但逐步掩码得到的分布不是「条件分布」</strong>——"
             "本课会把这个失真精确算出来"],
            ["<strong>05</strong>", "提示的运维与跨模型迁移",
             "prompt 是<strong>会随模型失效的资产</strong>；"
             "它需要版本、指纹、回归门禁与迁移流程"],
        ]),
        H3("三条贯穿全课的纪律"),
        OL([
            "<strong>格式合规与任务正确必须分开计</strong>——"
            "<em>「没按格式答」和「答错了」是两个不同的失败，修法也不同</em>。"
            "这条在 01 建立，在 04 变成解析失败率与选择偏倚的分析。",
            "<strong>任何 prompt 改动都要在留出集上复核</strong>——"
            "<em>搜索空间越大，在训练集上过拟合越容易</em>（03 会量出来）。"
            "而 prompt 的搜索空间通常比人们以为的大得多。",
            "<strong>prompt 的每一个组成部分都要进指纹</strong>——"
            "指令、示例集合与顺序、格式规范、解码约束、模型 ID 与温度。"
            "<em>漏一项，两次评测就不可比而看起来可比</em>（C68 模块 02 的老问题）。",
        ]),
    ])),

    # ============================================================== 4
    ("boundary", "与既有课程的分工", "".join([
        P("这一层与好几门课相邻。<strong>本课不重复其中任何一门。</strong>"),
        TABLE(["课程", "它讲什么", "与本课的关系"], [
            ["<strong>C33</strong> · 上下文与记忆工程",
             "token 预算与截断、compaction、长期记忆、检索入门、prompt 缓存",
             "<strong>C33 管「上下文里装什么、怎么装得下」，本课管「prompt 本身的结构与优化」</strong>。"
             "<em>预算分配、压缩、稳定前缀设计全部属于 C33，本课一律不讲</em>；"
             "但本课模块 05 会用到 C33 的缓存友好性作为一个约束"],
            ["<strong>C03</strong> 模块 03 · prompt 敏感性",
             "分隔符/空格/选项顺序对分数的影响、答案抽取与 unparseable、"
             "「答错还是没按格式答」这个混淆变量",
             "<strong>C03 是<em>测量</em>视角：把敏感性当成评测的噪声源来量化</strong>。"
             "本课是<em>优化</em>视角：把同一批变量当成可搜索的设计空间。"
             "<em>本课模块 02 是 C03-03 第 6 节的展开</em>"],
            ["<strong>C03</strong> 模块 06 · elicitation",
             "能力 vs 表现、引出阶梯、pass@k、scaffolding 效应",
             "<strong>C03-06 问「模型的能力上界在哪」，本课问「怎么把 prompt 这一层做到位」</strong>。"
             "<em>本课的所有优化都在「不改权重」的前提下</em>，"
             "这正是 elicitation 阶梯里 prompt 那一格"],
            ["<strong>C02</strong> · 后训练",
             "SFT、RLHF、DPO、RLVR",
             "<strong>训练时优化 vs 推理时优化</strong>。"
             "<em>本课的自动提示优化不改任何权重</em>；"
             "两者的关系是：<strong>prompt 优化通常应当先做</strong>——它便宜、可回滚、"
             "而且它给微调提供了一个更强的基线"],
            ["<strong>C67</strong> · LLM-as-a-Judge",
             "judge 设计、偏差、元评测、排名",
             "<strong>自动提示优化的目标函数通常是一个 judge</strong>，"
             "而<em>judge 的偏差会被优化过程直接放大</em>——"
             "本课模块 03 会讨论这件事，但 judge 本身怎么验证在 C67"],
            ["<strong>C68</strong> · Eval 基础设施",
             "spec / 指纹 / CI 门禁 / 阈值从方差推",
             "<strong>本课的每一次 prompt 改动都按 C68 的规矩走</strong>："
             "进 spec、进指纹、门禁分级"],
            ["<strong>C50</strong> · HuggingFace 生态",
             "tokenizers、generate、logits processor",
             "<strong>模块 04 的受限解码在真实栈上就是一个 LogitsProcessor</strong>；"
             "本课从零实现它的逻辑，接口层面的用法在 C50"],
        ]),
        CALLOUT("warn", "如果你只想解决一个具体问题，可以直接跳："
                        "<strong>「输出格式老是不对」→ 01 与 04；"
                        "「换了几个示例效果就变了」→ 02；"
                        "「手改 prompt 改不动了」→ 03；"
                        "「换了模型 prompt 全失效」→ 05。</strong>"),
    ])),

    # ============================================================== 5
    ("method", "方法论：一个机制清楚的 in-context learning 模拟器", "".join([
        P("本课全程<strong>不调用任何真实模型</strong>。"
          "notebook 里的「模型」是一个三十行的确定性函数。"
          "<strong>但它不是随便编的——它的机制是有依据的，"
          "而且正是这个机制让本课的实验有意义。</strong>"),
        ASCII("""
   ToyLM（模块 00–03 用）

   输入: instruction, demos = [(x_i, y_i)], x
   ┌────────────────────────────────────────────────────────────┐
   │ 1. 解析指令：标签集在 instruction 里声明了吗？              │
   │      没有 → 返回 UNPARSEABLE（模型「自创标签」的替身）      │
   │ 2. demos 为空 → 返回先验标签                                │
   │ 3. 否则：在 demos 上做 kNN                                  │
   │      score_i = sim(x, x_i) + recency * (i / (n-1))          │
   │                              └── 近因偏置：靠后的 demo 更重  │
   │ 4. 返回 argmax 的那个 demo 的标签                            │
   └────────────────────────────────────────────────────────────┘
"""),
        DUAL(
            "为什么用 kNN？因为<strong>「in-context learning 的行为在很多任务上很像在示例上做最近邻」"
            "这一点有相当多的经验支持</strong>，"
            "而且它自然地解释了本课要研究的三件事："
            "<em>示例选择为什么重要（决定了近邻集合）、"
            "示例数量的收益为什么会饱和（近邻已经够近了）、"
            "顺序为什么有影响（位置偏置叠加在相似度上）</em>。",
            "<strong>用它的关键好处是每个实验只有一个变量。</strong>"
            "<em>真实模型会把「示例选得更好」与「模型今天更配合」混在一起</em>，"
            "而这里两者是可分离的。"
            "<strong>但也要诚实地说清它的局限</strong>："
            "<em>它没有真正的推理能力，所以它不能用来研究「思维链有没有用」这类问题</em>；"
            "本课因此<strong>不讨论 CoT 的效果</strong>——"
            "那需要真实模型，属于 C09（推理与测试时计算）。",
        ),
        P("模块 04 用另一个替身：<strong>一个 token 级的小语言模型 + 一个 JSON 语法掩码器</strong>。"
          "<em>它同样是几十行、确定性的，但它足以把「受限解码的分布失真」精确算出来</em>——"
          "而这是一个用真实模型<strong>算不出来</strong>的量（需要枚举全部合法串）。"),
        H3("每个模块的固定结构"),
        UL([
            "<strong>讲解页</strong>：机制 → 可测量的量 → 怎么变成检查项",
            "<strong>notebook</strong>：6–8 个 worked 小节，每节以 <code>assert</code> 结尾",
            "<strong>4 道 ✏️ 练习</strong>：TODO 骨架 + <code>assert</code> 判分 + 📖 参考答案",
            "<strong>🧪 真实工程胶囊</strong>：接真实模型 / DSPy / logits processor 的代码",
        ]),
    ])),

    # ============================================================== 6
    ("env", "环境与运行", "".join([
        CODE("""pip install -r requirements.txt      # 只有 numpy 与 jupyterlab
jupyter lab

# 或者点每个 notebook 顶部的 Colab 徽章，CPU 运行时即可
# 顺序：先读 NN_讲解.html，再跑同目录的 NN_*.ipynb""", "bash"),
        P("<strong>先跑 <code>00_environment_check.ipynb</code></strong>——"
          "它建起模拟器，然后在同一个任务上依次注入本课四个靶子"
          "（指令缺标签集、示例选错、顺序反了、没规定格式），"
          "<em>并量出每一个的代价</em>。"),
        CALLOUT("intuition", "如果你读完 00 只记住一件事，希望是这个："
                             "<strong>prompt 的四个组成部分（指令 / 示例 / 格式 / 解码约束）"
                             "失败方式完全不同，所以它们需要四套不同的检查。</strong>"
                             "<em>而把它们混成一个字符串，等于放弃了分别检查的可能。</em>"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与一个可控的 in-context learning 模拟器

这个 notebook 做两件事：

1. **建起一个机制清楚的 ToyLM** —— demo 上的 kNN + 近因偏置 + 先验，三十行、确定性。
2. **在同一个任务上依次注入本课四个靶子**并量出代价：
   指令缺标签集（01）· 示例选错（02）· 顺序反了（02）· 没规定输出格式（01/04）。

> 心智模型：**一次调用里你在控制四个独立的东西——指令、示例、格式、解码约束。
> 它们的失败方式完全不同，所以需要四套不同的检查。**"""),

    md("""## 0 · 环境"""),

    code("""import os, re, json, math, hashlib, itertools
from collections import Counter, defaultdict

import numpy as np

print('numpy', np.__version__)
print('本课全程 CPU / 断网 / 无需 API key —— 「模型」是一个确定性函数')

DIM = 2048

def tokenize(text):
    text = text.lower()
    toks = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\\u4e00-\\u9fff]+', text):
        toks += list(run)
        toks += [run[i:i + 2] for i in range(len(run) - 1)]
    return toks

def embed(text, dim=DIM):
    v = np.zeros(dim)
    for tok in tokenize(text):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

def sim(a, b):
    return float(np.dot(embed(a), embed(b)))"""),

    md("""## 1 · 任务与数据

一个五分类任务：把用户反馈分到 `bug / feature / billing / account / other`。
20 条训练样本（示例池）+ 10 条测试样本。"""),

    code("""LABELS = ['bug', 'feature', 'billing', 'account', 'other']

POOL = [
    ('登录后一直转圈，点不动', 'bug'),
    ('保存文件时报错 500', 'bug'),
    ('页面加载不出来', 'bug'),
    ('导出 CSV 会丢最后一行', 'bug'),
    ('希望支持批量导出', 'feature'),
    ('能不能加暗色主题', 'feature'),
    ('想要一个搜索框', 'feature'),
    ('建议增加导入模板', 'feature'),
    ('这个月扣了两次钱', 'billing'),
    ('发票开错了公司名', 'billing'),
    ('为什么涨价了', 'billing'),
    ('想申请退款', 'billing'),
    ('忘记密码收不到邮件', 'account'),
    ('想改绑定手机号', 'account'),
    ('账号被锁了', 'account'),
    ('想注销账号', 'account'),
    ('你们客服态度不错', 'other'),
    ('随便看看', 'other'),
    ('没什么事', 'other'),
    ('祝好', 'other'),
]

TEST = [
    ('打开报表就崩溃', 'bug'),
    ('保存草稿会丢内容', 'bug'),
    ('希望能加个批量删除', 'feature'),
    ('想要导出 PDF 的功能', 'feature'),
    ('这个月账单不对', 'billing'),
    ('发票上的税号不对', 'billing'),
    ('登录不上，密码重置也收不到', 'account'),
    ('手机号换了要怎么改', 'account'),
    ('感谢你们的帮助', 'other'),
    ('没别的了', 'other'),
]

print(f'示例池 {len(POOL)} 条（每类 {len(POOL) // len(LABELS)} 条）· 测试 {len(TEST)} 条')
print('标签分布:', Counter(y for _, y in POOL))"""),

    md("""## 2 · ToyLM：demo 上的 kNN + 近因偏置 + 先验

三条机制，每一条都对应本课要研究的一件事：

| 机制 | 它解释了什么 |
|---|---|
| 在 demos 上做 kNN | **示例选择**为什么重要（它决定了近邻集合） |
| 近因偏置 `recency * i/(n-1)` | **顺序**为什么有影响 |
| 指令里没声明标签集 → `UNPARSEABLE` | **指令**与**格式**为什么是独立的失败 |"""),

    code("""UNPARSEABLE = 'UNPARSEABLE'

def toy_lm(instruction, demos, x, recency=0.35, prior='other'):
    \"\"\"一个机制清楚的 in-context learning 替身。

    1) 指令里没声明标签集 → 模型「自创标签」，返回 UNPARSEABLE
    2) 没有 demos → 返回先验标签
    3) 否则在 demos 上做 kNN，分数叠加一个位置相关的近因偏置
    \"\"\"
    declared = [l for l in LABELS if l in instruction]
    if not declared:
        return UNPARSEABLE
    if not demos:
        return prior
    E = np.stack([embed(t) for t, _ in demos])
    s = E @ embed(x)
    n = len(demos)
    boost = np.array([recency * (i / (n - 1) if n > 1 else 1.0) for i in range(n)])
    s = s + boost
    label = demos[int(np.argmax(s))][1]
    return label if label in declared else prior

INSTR_FULL = '把用户反馈分类为 bug / feature / billing / account / other 之一，只输出标签。'
INSTR_NO_LABELS = '请把用户反馈分类，只输出标签。'

def evaluate(instruction, demos, recency=0.35, test=None):
    test = TEST if test is None else test
    correct = unparsed = 0
    for x, gold in test:
        y = toy_lm(instruction, demos, x, recency=recency)
        unparsed += (y == UNPARSEABLE)
        correct += (y == gold)
    return dict(accuracy=correct / len(test), unparsed_rate=unparsed / len(test))

print('指令完整 + 全部示例:', evaluate(INSTR_FULL, POOL))
print('指令缺标签集         :', evaluate(INSTR_NO_LABELS, POOL))
assert evaluate(INSTR_FULL, POOL)['accuracy'] > 0.5
assert evaluate(INSTR_NO_LABELS, POOL)['unparsed_rate'] == 1.0
print('\\n✅ 模拟器可用。注意第二行：**准确率是 0 而不是「差一点」**——')
print('   因为解析失败和答错是两个不同的失败，而它们经常被记成同一件事。')"""),

    md("""## 3 · 一个最小的 prompt program

四个部件各自独立：`instruction` / `demos` / `format` / （`decoding` 在模块 04）。
注意 `parse` 是 program 的一部分——**格式规范与解析器必须成对定义**。"""),

    code("""class PromptProgram:
    \"\"\"一个有签名的 prompt 模块。签名 = 输入字段 + 输出字段 + 输出取值域。\"\"\"

    def __init__(self, instruction, demos, out_field='label', allowed=None,
                 format_spec=None, recency=0.35):
        self.instruction = instruction
        self.demos = list(demos)
        self.out_field = out_field
        self.allowed = list(allowed) if allowed else list(LABELS)
        self.format_spec = format_spec          # None = 不规定格式
        self.recency = recency

    # ---- 渲染（真实系统里这里拼字符串） ----
    def render(self, x):
        parts = [self.instruction]
        if self.format_spec:
            parts.append(f'输出格式：{self.format_spec}')
        for dx, dy in self.demos:
            parts.append(f'输入：{dx}\\n输出：{dy}')
        parts.append(f'输入：{x}\\n输出：')
        return '\\n\\n'.join(parts)

    # ---- 调用 + 解析 ----
    def __call__(self, x):
        raw = toy_lm(self.instruction, self.demos, x, recency=self.recency)
        return raw, self.parse(raw)

    def parse(self, raw):
        \"\"\"格式规范与解析器必须成对定义。没规定格式时，解析只能靠猜。\"\"\"
        if raw == UNPARSEABLE:
            return None
        if self.format_spec is None:
            # 没规定格式：只有恰好等于某个合法标签时才算解析成功
            return raw if raw in self.allowed else None
        if self.format_spec.startswith('json'):
            try:
                obj = json.loads(raw if raw.startswith('{')
                                 else json.dumps({self.out_field: raw}))
            except json.JSONDecodeError:
                return None
            v = obj.get(self.out_field)
            return v if v in self.allowed else None
        return raw if raw in self.allowed else None

    def signature(self):
        return dict(inputs=['x'], output=self.out_field, allowed=self.allowed,
                    n_demos=len(self.demos), has_format=self.format_spec is not None)

prog = PromptProgram(INSTR_FULL, POOL, format_spec='json {"label": "<标签>"}')
print('signature:', prog.signature())
print()
print('渲染出来的 prompt（前 160 字）:')
print(prog.render('打开报表就崩溃')[:160], '...')
print()
for probe in ['打开报表就崩溃', '这个月账单不对', '想改绑定手机号']:
    raw, parsed = prog(probe)
    print(f'{probe:<16} raw={raw!r:<12} parsed={parsed!r}')
    assert parsed in LABELS, '解析必须成功（对不对是另一件事）'
print('\\n✅ 一个 prompt program = 指令 + 示例 + 格式 + 解析器 + 签名。')
print('   注意第一条预测是错的（应当是 bug）——**这正是本课要区分的两件事**：')
print('   解析成功（契约层面对了）与答对（能力层面对了）是两个独立的量。')
print('   签名是这四样东西的契约，模块 01 会展开它。')"""),

    md("""## 4 · 靶子一（模块 01）：指令缺标签集

**格式合规与任务正确必须分开计。** 混在一起时，这个故障看起来像「效果差」。"""),

    code("""def scored(instruction, demos, **kw):
    \"\"\"分别计三个量：解析成功率 / 解析成功里的正确率 / 端到端正确率。\"\"\"
    p = PromptProgram(instruction, demos, **kw)
    n_ok = n_correct_given_ok = n_correct = 0
    for x, gold in TEST:
        _, parsed = p(x)
        if parsed is not None:
            n_ok += 1
            n_correct_given_ok += (parsed == gold)
        n_correct += (parsed == gold)
    return dict(parse_rate=n_ok / len(TEST),
                acc_given_parsed=(n_correct_given_ok / n_ok) if n_ok else float('nan'),
                end_to_end=n_correct / len(TEST))

rows = {
    '指令完整':     scored(INSTR_FULL, POOL),
    '指令缺标签集': scored(INSTR_NO_LABELS, POOL),
}
print(f"{'配置':<14}{'解析成功率':>12}{'解析成功里的正确率':>20}{'端到端':>9}")
for k, v in rows.items():
    a = v['acc_given_parsed']
    print(f"{k:<14}{v['parse_rate']:>12.0%}"
          f"{('nan' if a != a else f'{a:.0%}'):>20}{v['end_to_end']:>9.0%}")

assert rows['指令完整']['parse_rate'] == 1.0
assert rows['指令缺标签集']['parse_rate'] == 0.0
print('\\n✅ 两个配置的端到端分数都是一个数，但**它们的失败完全不同**：')
print('   指令缺标签集 → 解析成功率 0%，这不是能力问题，是契约问题。')
print('   如果只看端到端，你会去「优化 prompt 让模型更聪明」——而该做的是把标签集写进指令。')
print('   这就是 C03 模块 03 说的混淆变量：**答错，还是没按格式答？**')"""),

    md("""## 5 · 靶子二（模块 02）：示例选错

同样的数量，不同的选择，准确率差一半。**而没有任何报错。**"""),

    code("""rng = np.random.default_rng(0)

def select_random(pool, k, seed=0):
    r = np.random.default_rng(seed)
    return [pool[i] for i in r.permutation(len(pool))[:k]]

def select_one_per_label(pool, k):
    out = []
    for l in LABELS:
        out += [t for t in pool if t[1] == l][:max(1, k // len(LABELS))]
    return out[:k]

def select_single_label(pool, k, label='other'):
    \"\"\"最坏的选法：全部示例来自同一类。\"\"\"
    same = [t for t in pool if t[1] == label]
    rest = [t for t in pool if t[1] != label]
    return (same + rest)[:k]

print(f"{'示例选择（k=5）':<22}{'端到端正确率':>14}")
res = {}
for name, fn in [('随机 5 条', lambda: select_random(POOL, 5)),
                 ('每类 1 条', lambda: select_one_per_label(POOL, 5)),
                 ('全部来自 other 类', lambda: select_single_label(POOL, 5))]:
    d = select_random(POOL, 5) if False else fn()
    a = evaluate(INSTR_FULL, d)['accuracy']
    res[name] = a
    print(f'{name:<22}{a:>14.0%}')

assert res['每类 1 条'] > res['全部来自 other 类'], '覆盖全部标签的选法必须更好'
print(f"\\n✅ 同样 5 条示例，覆盖全类 {res['每类 1 条']:.0%} vs 全来自一类 "
      f"{res['全部来自 other 类']:.0%}。")
print('   注意「全来自一类」这个配置在真实系统里不是刻意的——')
print('   它是「从最近的标注里取前 5 条」的自然结果，而最近的标注往往集中在同一批问题上。')"""),

    md("""## 6 · 靶子三（模块 02）：顺序

同一批示例，只改顺序。近因偏置让**最后几条示例的标签被系统性偏好**。"""),

    code("""other_last = [t for t in POOL if t[1] != 'other'] + [t for t in POOL if t[1] == 'other']
other_first = [t for t in POOL if t[1] == 'other'] + [t for t in POOL if t[1] != 'other']

print(f"{'顺序':<16}{'端到端':>9}{'预测里 other 的占比':>22}")
def pred_dist(demos):
    ys = [toy_lm(INSTR_FULL, demos, x) for x, _ in TEST]
    return Counter(ys)

for name, d in [('other 放最后', other_last), ('other 放最前', other_first)]:
    a = evaluate(INSTR_FULL, d)['accuracy']
    c = pred_dist(d)
    print(f"{name:<16}{a:>9.0%}{c['other'] / len(TEST):>22.0%}")

a_last = evaluate(INSTR_FULL, other_last)['accuracy']
a_first = evaluate(INSTR_FULL, other_first)['accuracy']
c_last = pred_dist(other_last)['other'] / len(TEST)
c_first = pred_dist(other_first)['other'] / len(TEST)
assert a_last != a_first, '顺序会改变结果'
assert c_last > c_first, '靠后的示例的标签被系统性偏好'
print(f'\\n✅ 只改顺序，端到端从 {a_first:.0%} 变成 {a_last:.0%}，')
print(f'   而 other 这个标签的预测占比从 {c_first:.0%} 变成 {c_last:.0%}。')
print('   **这不是随机波动，是一个有方向的偏置**——它可以被测量，也可以被利用或抵消（模块 02）。')
print('   工程含义：示例顺序必须固定并进指纹。「反正就是几个例子」是错的。')"""),

    md("""## 7 · 靶子四（模块 01/04）：没规定输出格式

最麻烦的不是「全部解析失败」，而是**只有一部分失败**——
因为那会在你的评测里制造一个选择偏倚（模块 04 会展开）。"""),

    code("""# 模拟一个更真实的情形：模型有时输出裸标签，有时输出一句话
def toy_lm_verbose(instruction, demos, x, verbose_rate=0.4, seed=0, **kw):
    y = toy_lm(instruction, demos, x, **kw)
    if y == UNPARSEABLE:
        return y
    h = int(hashlib.md5((x + str(seed)).encode()).hexdigest(), 16)
    if (h % 100) / 100.0 < verbose_rate:
        return f'我认为这条反馈应该归类为 {y}。'      # 没规定格式时的自然输出
    return y

def scored_verbose(format_spec, verbose_rate=0.4):
    allowed = LABELS
    n_ok = n_correct = 0
    for x, gold in TEST:
        raw = toy_lm_verbose(INSTR_FULL, POOL, x, verbose_rate=verbose_rate)
        if format_spec is None:
            parsed = raw if raw in allowed else None          # 严格解析
        else:
            m = re.search('|'.join(allowed), raw)             # 规定了格式 → 抽取
            parsed = m.group(0) if m else None
        if parsed is not None:
            n_ok += 1
            n_correct += (parsed == gold)
    return dict(parse_rate=n_ok / len(TEST),
                end_to_end=n_correct / len(TEST))

strict = scored_verbose(None)
withfmt = scored_verbose('json {"label": "<标签>"}')
print(f"{'配置':<20}{'解析成功率':>12}{'端到端':>9}")
print(f'{"没规定格式":<20}{strict["parse_rate"]:>12.0%}{strict["end_to_end"]:>9.0%}')
print(f'{"规定格式 + 抽取":<20}{withfmt["parse_rate"]:>12.0%}{withfmt["end_to_end"]:>9.0%}')

assert 0.0 < strict['parse_rate'] < 1.0, '部分解析失败——这是最麻烦的情形'
assert withfmt['parse_rate'] > strict['parse_rate']
print(f"\\n✅ 没规定格式时解析成功率 {strict['parse_rate']:.0%}——**部分失败而不是全部失败**。")
print('   为什么这更麻烦：如果你只在「解析成功」的样本上算准确率，')
print('   那么被丢掉的那些样本不是随机的（它们是模型更倾向于多说话的那些），')
print('   于是你的准确率估计是有偏的。模块 04 会把这个偏倚量出来。')"""),

    md("""## 8 · 四个靶子的代价汇总

**注意最后一列**：四个靶子里只有一个能被「端到端准确率」这一个数正确诊断。"""),

    code("""SUMMARY = [
    ('01 指令缺标签集', '模型自创标签',       '解析成功率 0%',        '解析成功率'),
    ('02 示例选错',     '近邻集合覆盖不全',   '准确率掉一半，无报错', '按标签分层的准确率'),
    ('02 顺序反了',     '近因偏置',           '预测分布整体偏移',     '预测标签分布'),
    ('04 没规定格式',   '部分输出不可解析',   '**部分**解析失败',     '解析成功率 + 选择偏倚检查'),
]
print(f"{'靶子':<18}{'机制':<20}{'症状':<24}{'该看的信号'}")
for a, b, c, d in SUMMARY:
    print(f'{a:<18}{b:<20}{c:<24}{d}')

signals = {d for *_, d in SUMMARY}
assert len(signals) == 4, '四个靶子需要四个不同的信号'
print(f'\\n✅ 四个靶子需要 {len(signals)} 个不同的信号——')
print('   端到端准确率会把它们全部压成一个数，而这个数不告诉你该改哪里。')
print('   这就是本课「把 prompt 拆成四个可分别检查的部件」的全部理由。')"""),

    md("""## ✏️ 练习 1：分层的评分器

实现 `score(program, test)`，返回一个 dict：
- `parse_rate` —— 解析成功率
- `acc_given_parsed` —— 只在解析成功的样本上算的正确率（无样本时为 `float('nan')`）
- `end_to_end` —— 端到端正确率（解析失败记为错）
- `by_label` —— `{gold_label: 该类的端到端正确率}`
- `pred_dist` —— 预测标签的分布（`dict`，含 `None` 表示解析失败）

`by_label` 与 `pred_dist` 是诊断靶子二与靶子三的信号。"""),

    code("""def score(program, test=None):
    \"\"\"返回 dict(parse_rate, acc_given_parsed, end_to_end, by_label, pred_dist)。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
good = PromptProgram(INSTR_FULL, POOL, format_spec='json {"label": "<标签>"}')
bad_instr = PromptProgram(INSTR_NO_LABELS, POOL, format_spec='json {"label": "<标签>"}')

s_good, s_bad = score(good), score(bad_instr)
print('好配置:', {k: v for k, v in s_good.items() if k not in ('by_label', 'pred_dist')})
print('  by_label:', {k: round(v, 2) for k, v in s_good['by_label'].items()})
print('  pred_dist:', s_good['pred_dist'])
print('坏指令:', {k: v for k, v in s_bad.items() if k not in ('by_label', 'pred_dist')})

assert s_good['parse_rate'] == 1.0
assert s_bad['parse_rate'] == 0.0
assert s_bad['acc_given_parsed'] != s_bad['acc_given_parsed'], '无样本时应当是 nan'
assert s_bad['end_to_end'] == 0.0
assert set(s_good['by_label']) == set(LABELS)
assert abs(np.mean(list(s_good['by_label'].values())) - s_good['end_to_end']) < 1e-9, \\
    '每类样本数相同时，分层平均应当等于端到端'
assert sum(s_good['pred_dist'].values()) == len(TEST)
assert None in s_bad['pred_dist'] and s_bad['pred_dist'][None] == len(TEST)
print('✅ 练习 1 通过：五个量分别刻画四个靶子')"""),

    md("""## 📖 参考答案 1"""),

    code("""# 练习 1 参考答案
def score(program, test=None):
    test = TEST if test is None else test
    n_ok = n_correct_given_ok = n_correct = 0
    by_label = defaultdict(list)
    preds = Counter()
    for x, gold in test:
        _, parsed = program(x)
        preds[parsed] += 1
        if parsed is not None:
            n_ok += 1
            n_correct_given_ok += (parsed == gold)
        hit = (parsed == gold)
        n_correct += hit
        by_label[gold].append(float(hit))
    return dict(
        parse_rate=n_ok / len(test),
        acc_given_parsed=(n_correct_given_ok / n_ok) if n_ok else float('nan'),
        end_to_end=n_correct / len(test),
        by_label={l: float(np.mean(v)) for l, v in by_label.items()},
        pred_dist=dict(preds))

s_good, s_bad = score(good), score(bad_instr)
assert s_good['parse_rate'] == 1.0 and s_bad['parse_rate'] == 0.0
assert s_bad['acc_given_parsed'] != s_bad['acc_given_parsed']
assert abs(np.mean(list(s_good['by_label'].values())) - s_good['end_to_end']) < 1e-9
assert s_bad['pred_dist'][None] == len(TEST)
print('✅ 参考答案 1 通过')
print('   注意 acc_given_parsed 在无样本时是 nan 而不是 0——')
print('   0 会被读成「解析成功的都答错了」，而真相是「没有解析成功的样本」。')
print('   这与 C68 模块 03 的「空集聚合返回 nan」是同一条纪律。')"""),

    md("""## ✏️ 练习 2：program 指纹

按 C68 的规矩：**改了会让结果不可比较的东西，全部进指纹**。

prompt program 里这些是：指令、**示例的集合与顺序**、格式规范、
允许的取值域、近因参数、模型 ID、温度。

实现 `program_fingerprint(program, model_id, temperature)`，要求：
- 改指令 / 改格式 / 改取值域 / 改模型 / 改温度 → 指纹变
- **改示例顺序 → 指纹必须变**（这是最容易漏的一项）
- 与结果无关的东西（比如 program 上挂的日志字段）→ 指纹不变"""),

    code("""def program_fingerprint(program, model_id, temperature):
    \"\"\"返回 12 位十六进制字符串。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# ---- fixture 全部前置 ----
FMT = 'json {"label": "<标签>"}'
base = PromptProgram(INSTR_FULL, POOL[:6], format_spec=FMT)
reordered = PromptProgram(INSTR_FULL, list(reversed(POOL[:6])), format_spec=FMT)
subset = PromptProgram(INSTR_FULL, POOL[:5], format_spec=FMT)

# ---- 断言 ----
fp0 = program_fingerprint(base, 'toy-lm@1', 0.0)
print('基线指纹:', fp0)
assert program_fingerprint(reordered, 'toy-lm@1', 0.0) != fp0, '示例顺序必须进指纹'
assert program_fingerprint(subset, 'toy-lm@1', 0.0) != fp0, '示例集合必须进指纹'

for field, val in [('instruction', INSTR_NO_LABELS), ('format_spec', None),
                   ('allowed', ['bug', 'other']), ('recency', 0.0)]:
    p = PromptProgram(INSTR_FULL, POOL[:6], format_spec=FMT)
    setattr(p, field, val)
    assert program_fingerprint(p, 'toy-lm@1', 0.0) != fp0, f'{field} 必须进指纹'

assert program_fingerprint(base, 'toy-lm@2', 0.0) != fp0, '模型 ID 必须进指纹'
assert program_fingerprint(base, 'toy-lm@1', 0.7) != fp0, '温度必须进指纹'

# 与结果无关的字段
base.owner = 'team-nlp'; base.note = 'v3 手改'
assert program_fingerprint(base, 'toy-lm@1', 0.0) == fp0, '无关字段不该进指纹'
print('✅ 练习 2 通过：示例顺序也进了指纹')"""),

    md("""## 📖 参考答案 2"""),

    code("""# 练习 2 参考答案
def program_fingerprint(program, model_id, temperature):
    payload = {
        'instruction': program.instruction,
        # 示例用**列表**而不是集合 —— 顺序必须影响指纹
        'demos': [[dx, dy] for dx, dy in program.demos],
        'format_spec': program.format_spec,
        'out_field': program.out_field,
        'allowed': list(program.allowed),
        'recency': program.recency,
        'model_id': model_id,
        'temperature': temperature,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]

fp0 = program_fingerprint(base, 'toy-lm@1', 0.0)
assert program_fingerprint(reordered, 'toy-lm@1', 0.0) != fp0
assert program_fingerprint(subset, 'toy-lm@1', 0.0) != fp0
assert program_fingerprint(base, 'toy-lm@2', 0.0) != fp0
assert program_fingerprint(base, 'toy-lm@1', 0.7) != fp0
print('✅ 参考答案 2 通过')
print('   唯一的技巧在 demos 那一行：**用列表而不是排序后的集合**。')
print('   第 6 节量过顺序有真实影响，所以「示例集合相同但顺序不同」')
print('   是两个不可比较的配置，指纹必须区分它们。')
print('   这与 C68 模块 02 的缓存键刚好相反——那里集合要排序，因为顺序不影响结果。')
print('   **判据始终是同一个：这个东西改了，结果会变吗？**')"""),

    md("""## ✏️ 练习 3：逐项消融

实现 `ablate(base_program)`：逐一「关掉」四个部件，返回每一项的**边际贡献**
（关掉它之后端到端正确率的下降）。

关掉的定义：
- `instruction` → 换成 `INSTR_NO_LABELS`
- `demos` → 换成空列表
- `order` → 把示例顺序反转（不是关掉，是改成另一个顺序）
- `format` → `format_spec = None`

返回 `{部件名: 端到端下降的百分点}`，并额外给出 `base` 的端到端分数。"""),

    code("""def ablate(base_program):
    \"\"\"返回 dict(base=..., instruction=..., demos=..., order=..., format=...)，
    后四项是「关掉这一项后端到端下降了多少」（可以为负）。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
BASE = PromptProgram(INSTR_FULL, other_last, format_spec='json {"label": "<标签>"}')
ab = ablate(BASE)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in ab.items()})

assert set(ab) == {'base', 'instruction', 'demos', 'order', 'format'}
assert ab['base'] > 0.5
# 关掉指令里的标签集 → 掉到 0，所以下降 = base
assert abs(ab['instruction'] - ab['base']) < 1e-9, '缺标签集时端到端是 0'
# 关掉示例 → 明显下降
assert ab['demos'] > 0.2
# 改顺序 → 有影响（可正可负，但不为 0）
assert abs(ab['order']) > 1e-9, '顺序必须有影响'
# 边际贡献排序：指令是最大的那一项
assert ab['instruction'] >= max(ab['demos'], abs(ab['order']), ab['format'])
print('✅ 练习 3 通过：四项的边际贡献都能被单独量出来')"""),

    md("""## 📖 参考答案 3"""),

    code("""# 练习 3 参考答案
def ablate(base_program):
    def clone(**over):
        p = PromptProgram(base_program.instruction, base_program.demos,
                          out_field=base_program.out_field,
                          allowed=base_program.allowed,
                          format_spec=base_program.format_spec,
                          recency=base_program.recency)
        for k, v in over.items():
            setattr(p, k, v)
        return p

    base = score(base_program)['end_to_end']
    variants = {
        'instruction': clone(instruction=INSTR_NO_LABELS),
        'demos': clone(demos=[]),
        'order': clone(demos=list(reversed(base_program.demos))),
        'format': clone(format_spec=None),
    }
    out = {'base': base}
    for name, p in variants.items():
        out[name] = base - score(p)['end_to_end']
    return out

ab = ablate(BASE)
assert set(ab) == {'base', 'instruction', 'demos', 'order', 'format'}
assert abs(ab['instruction'] - ab['base']) < 1e-9
assert ab['demos'] > 0.2 and abs(ab['order']) > 1e-9
assert ab['instruction'] >= max(ab['demos'], abs(ab['order']), ab['format'])
print('✅ 参考答案 3 通过')
print('   消融是本课最常用的一个工具：它把「prompt 效果不好」变成一个有指向的结论。')
print('   两个读法上的注意：')
print('   ① order 那一项**可正可负**——「另一个顺序」不一定更差，')
print('      所以要报绝对值（它衡量的是敏感度，不是损失）；')
print('   ② 边际贡献不可加：四项之和通常不等于「全关掉」的损失（C69 模块 05 的二阶交互）。')"""),

    md("""## ✏️ 练习 4：端到端归因器

给定一个表现不好的 program，判断**是哪一层的问题**。判定顺序（顺序本身就是结论）：

1. 解析成功率 < 1.0 → `'format'`（先修契约，不看效果）
2. 某个标签的 `by_label` 是 0，而示例里根本没有这个标签 → `'demos_coverage'`
3. 预测分布里某个标签的占比 > 0.5（而真实分布是均匀的）→ `'order_bias'`
4. 都不成立但端到端仍低于阈值 → `'capability'`
5. 端到端 ≥ 阈值 → `'ok'`"""),

    code("""def diagnose(program, threshold=0.6):
    \"\"\"返回 'format' / 'demos_coverage' / 'order_bias' / 'capability' / 'ok'。\"\"\"
    # TODO
    raise NotImplementedError"""),

    code("""# —— 自测 ——
# ---- fixture 全部前置 ----
FMT4 = 'json {"label": "<标签>"}'
p_fmt = PromptProgram(INSTR_NO_LABELS, POOL, format_spec=FMT4)
no_billing = [t for t in POOL if t[1] != 'billing']
p_cov = PromptProgram(INSTR_FULL, no_billing, format_spec=FMT4)
p_bias = PromptProgram(INSTR_FULL, select_single_label(POOL, 8, 'other'), format_spec=FMT4)
p_ok = PromptProgram(INSTR_FULL, POOL, format_spec=FMT4)

# ---- 断言 ----
assert diagnose(p_fmt) == 'format', diagnose(p_fmt)                  # 格式问题优先
assert diagnose(p_cov) == 'demos_coverage', diagnose(p_cov)          # 示例覆盖不全
d_bias = diagnose(p_bias)
assert d_bias in ('demos_coverage', 'order_bias'), d_bias            # 偏置
assert diagnose(p_ok, threshold=0.6) == 'ok', diagnose(p_ok, threshold=0.6)
assert diagnose(p_ok, threshold=0.95) == 'capability'                # 阈值抬高
print('✅ 练习 4 通过：归因器把失败指到具体的一层')"""),

    md("""## 📖 参考答案 4"""),

    code("""# 练习 4 参考答案
def diagnose(program, threshold=0.6):
    s = score(program)
    if s['parse_rate'] < 1.0:
        return 'format'                                   # 先修契约
    demo_labels = {y for _, y in program.demos}
    for l, acc in s['by_label'].items():
        if acc == 0.0 and l not in demo_labels:
            return 'demos_coverage'
    n = sum(s['pred_dist'].values())
    for l, c in s['pred_dist'].items():
        if l is not None and c / n > 0.5:
            return 'order_bias'
    return 'ok' if s['end_to_end'] >= threshold else 'capability'

assert diagnose(p_fmt) == 'format'
assert diagnose(p_cov) == 'demos_coverage'
assert diagnose(p_bias) in ('demos_coverage', 'order_bias')
assert diagnose(p_ok, threshold=0.6) == 'ok'
assert diagnose(p_ok, threshold=0.95) == 'capability'
print('✅ 参考答案 4 通过')
print('   判定顺序 format → demos_coverage → order_bias → capability 就是本课模块的顺序，')
print('   也是真实调试时该走的顺序：**先修契约，再修示例，最后才怀疑「模型不够聪明」**。')
print('   反过来做（一上来就换更大的模型）是这一层最常见的浪费。')"""),

    md("""## 🧪 真实工程胶囊：接真实模型

```python
# ══════════════════════════════════════════════════════════════════
# A. 签名与解析成对定义（讲解第 1 节 / 本 notebook 第 3 节）
# ══════════════════════════════════════════════════════════════════
from pydantic import BaseModel
from typing import Literal

class Classification(BaseModel):                  # ← 签名就是这个类
    label: Literal['bug', 'feature', 'billing', 'account', 'other']
    confidence: float

INSTRUCTION = (
    '把用户反馈分类。标签只能是 bug / feature / billing / account / other 之一。'
)   # ← 标签集必须在指令里出现（第 4 节：不写就是 100% 解析失败）

def render(x, demos, schema):
    parts = [INSTRUCTION, f'输出必须是 JSON，且符合此 schema：{schema}']
    for dx, dy in demos:                          # ← 顺序固定，进指纹
        parts.append(f'输入：{dx}\\n输出：{dy.model_dump_json()}')
    parts.append(f'输入：{x}\\n输出：')
    return '\\n\\n'.join(parts)

# ══════════════════════════════════════════════════════════════════
# B. 三个量分别记录（讲解第 2 节的「可测试」）
# ══════════════════════════════════════════════════════════════════
def run_one(x):
    raw = call_model(render(x, DEMOS, Classification.model_json_schema()))
    try:
        obj = Classification.model_validate_json(raw)
        return dict(raw=raw, parsed=obj, parse_ok=True)
    except Exception as e:
        return dict(raw=raw, parsed=None, parse_ok=False, err=str(e))
#   指标：parse_rate / acc_given_parsed / end_to_end —— **三个数一起报**。
#   只报最后一个时，「答错」与「没按格式答」被记成同一件事。

# ══════════════════════════════════════════════════════════════════
# C. 指纹（讲解第 3 节第 3 条 / 练习 2）
# ══════════════════════════════════════════════════════════════════
FP = sha256(json.dumps({
    'instruction': INSTRUCTION,
    'demos': [[dx, dy.model_dump()] for dx, dy in DEMOS],   # ← 列表，顺序敏感
    'schema': Classification.model_json_schema(),
    'model': 'claude-x@2026-06-01',                          # ← 钉死版本
    'temperature': 0.0,
    'decoding': {'constrained': True, 'grammar': 'json'},    # ← 模块 04
}, sort_keys=True)).hexdigest()[:12]
#   把 FP 写进每一条评测记录（C68-01）。**prompt 改一个字，FP 就必须变。**

# ══════════════════════════════════════════════════════════════════
# D. CI（讲解第 3 节）
# ══════════════════════════════════════════════════════════════════
# 阻断（确定性）：标签集出现在指令里；schema 与解析器一致；FP 变了但没记录变更
# 阻断（统计）  ：任一标签的分层准确率相对基线下降超过阈值（C68-04 推阈值）
# 报警          ：预测标签分布的 PSI（抓顺序偏置与示例漂移）
```

---

## 小结

| 结论 | 数字 / 判据 | 在哪一节 |
|---|---|---|
| 一次调用里在控制四个独立的东西 | 指令 / 示例 / 格式 / 解码约束 | 讲解 1 |
| 格式合规与任务正确必须分开计 | 缺标签集 → 解析率 0%，而不是「效果差」 | 第 4 节 |
| 示例选择的影响大于数量 | 同样 5 条：覆盖全类 vs 全来自一类 | 第 5 节 |
| 顺序是一个有方向的偏置，不是噪声 | 只改顺序，预测分布明显偏移 | 第 6 节 |
| 部分解析失败比全部失败更麻烦 | 它在评测里制造选择偏倚 | 第 7 节 |
| 四个靶子需要四个不同的信号 | 端到端准确率把它们压成一个数 | 第 8 节 |
| 示例的**顺序**必须进指纹 | 与缓存键的「集合要排序」刚好相反 | 练习 2 |
| 归因顺序：format → demos → order → capability | 先修契约，最后才怀疑模型 | 练习 4 |

下一模块：**01 · prompt program 与可组合结构**——
给每个模块一个签名，让「格式合规」与「答得对不对」变成两个可以独立测的量。"""),
]
