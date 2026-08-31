# -*- coding: utf-8 -*-
"""C66 模块 00 · 课程总览与环境（Agent 评测与基准）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过 C04（tool use / ReAct / sandbox harness）或 C30（agent loop 从零）任一门的前三个模块即可；"
                 "统计部分只需要理解「均值有误差」，置信区间与自举的推导在 04 模块现场补"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（环境自检 / 90 行的最小 agentic eval 端到端骨架：环境 + agent + scorer + 报告 / '
                       '静态基准与 agentic 基准的方差对比 / 七个决策点自检器）'),
    ("核心参考", "Jimenez et al., SWE-bench (ICLR 2024) · Yao et al., τ-bench (2024) · "
                 "Mialon et al., GAIA (2023) · Zhou et al., WebArena (ICLR 2024) · "
                 "本课程 C03（评测科学总论）· C04 模块 06（agentic evals 概览）· C30（harness 实现）"),
    ("预计时长", "读 45 分钟 + 跑 35 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-different", "为什么 agent 评测不是「多轮版的静态基准」", "".join([
        P("静态基准（MMLU、GSM8K、HumanEval）的评测循环短到可以画在一行里："
          "<code>prompt → 一次生成 → 比对答案 → 得分</code>。"
          "把同一套工具搬到 agent 上会立刻失效，原因不是「步数变多了」这么简单——"
          "<strong>是评测对象的数学结构变了</strong>：从「一次采样的正确率」变成了"
          "「一条在有状态环境里展开的轨迹的成败」。"),
        TABLE(["维度", "静态基准", "agentic 基准", "带来的评测后果"], [
            ["交互结构", "单轮，模型输出即终点", "<strong>多步，且每一步的输入依赖上一步的输出</strong>", "误差会沿轨迹放大：第 3 步的一个小偏差可能让后面 20 步全部作废"],
            ["环境", "无状态，题目是纯文本", "<strong>有状态</strong>：文件系统、数据库、浏览器 DOM、容器", "同一个 prompt 跑两次可能得到不同结果，环境本身成了方差源"],
            ["判分", "字符串/选项匹配，确定性", "执行结果、最终状态、rubric、LLM judge 混用", "判分器自己会犯错，必须先评测判分器（见 02 模块与 C67）"],
            ["成本", "每题一次前向，成本近似常数", "<strong>每题几千到几十万 token，且方差极大</strong>", "不报成本的成功率数字是不可比的（见 05 模块）"],
            ["scaffold 依赖", "几乎无——prompt 模板影响有限", "<strong>harness/scaffold 的影响常常大于模型本身的差异</strong>", "「模型 A 比模型 B 强」这句话在 agent 评测里必须附上 harness 版本才成立"],
            ["失败模式", "答错了就是答错了", "超时、死循环、工具报错未恢复、越权、提前放弃", "只报一个成功率会把这些完全不同的失败混成一个数字"],
        ]),
        DUAL(
            "直白地说：静态基准像一道选择题——给题目、收答案、对答案，三步结束。agentic 基准像一场开卷实操考试——"
            "给你一台电脑和一个任务，你可以自己查资料、自己改文件、自己跑测试，考官最后看的是<em>你把这台电脑折腾成了什么样</em>。"
            "问题在于：同一个人做两次，桌面状态、网络快慢、工具报不报错都不一样，"
            "<strong>所以「他做对了」这句话本身就带着不小的随机性</strong>。",
            "更严谨地说，静态基准评测的是条件分布 $P(y \\mid x)$ 上的一个期望；agentic 基准评测的是"
            "<span class=\"term\">部分可观测马尔可夫决策过程</span>（POMDP）里策略 $\\pi_\\theta$ 的期望回报 "
            "$\\mathbb{E}_{\\tau \\sim \\pi_\\theta, \\mathcal{E}}[R(\\tau)]$，其中期望同时对策略的采样随机性"
            "<em>和环境 $\\mathcal{E}$ 的随机性</em>取。这意味着：(a) 方差有两个独立来源，"
            "(b) 环境版本变化等价于换了一个被评测的分布，历史分数不可直接比较，"
            "(c) 回报 $R$ 本身是设计出来的，判分函数的设计误差直接进入被测量的量。",
        ),
        CALLOUT("warn", "一个具体到可以直接引用的例子：<strong>SWE-bench 的原始版本里有相当比例的任务本身不可解</strong>"
                        "——issue 描述里缺少复现所必需的信息，或者对应的隐藏测试用例检查了 issue 里根本没提到的行为。"
                        "这直接催生了 <strong>SWE-bench Verified</strong>（由人工标注员逐条筛出可解子集）。"
                        "这件事的教训不是「SWE-bench 不好」，而是：<strong>agentic 基准的任务集本身就是一个需要被评测的对象</strong>，"
                        "在静态基准里几乎不会出现这种问题。"),
    ])),

    # ============================================================== 2
    ("three-layers", "三层评测对象：结果 / 轨迹 / 过程", "".join([
        P("整门课的组织骨架是一句话：<strong>一个 agent 可以在三个不同的层面上被评测，三层各自回答不同的问题，"
          "任何只做一层的评测报告都是残缺的。</strong>"),
        ASCII("""
      ┌──────────────────────────────────────────────────────────┐
      │  第三层 · 过程 process        「每一步做得对不对？」        │
      │    步骤级 rubric / 过程奖励 / 关键动作检查点               │
      │    → 03 模块。粒度最细，标注最贵，最能定位失败根因           │
      ├──────────────────────────────────────────────────────────┤
      │  第二层 · 轨迹 trajectory     「它是怎么做到（或没做到）的？」│
      │    工具调用序列 / 冗余步数 / 无效动作率 / 错误恢复率        │
      │    → 03 模块。能解释「为什么两个同样 40% 的 agent 完全不同」 │
      ├──────────────────────────────────────────────────────────┤
      │  第一层 · 结果 outcome        「任务到底完成了没有？」       │
      │    测试通过 / 最终状态匹配 / rubric checkpoint 达成率       │
      │    → 02 模块。最便宜、最客观，但信息量最低                  │
      └──────────────────────────────────────────────────────────┘
                 成本 ↑    可解释性 ↑    主观性 ↑    往上走
"""),
        TABLE(["层", "典型指标", "判分成本", "能回答的问题", "不能回答的问题"], [
            ["结果 outcome", "resolve rate / pass@1 / 最终状态匹配率", "低（可自动化）", "这个 agent 能不能完成这类任务", "它是靠什么完成的、失败时卡在哪"],
            ["轨迹 trajectory", "平均步数、无效动作率、恢复率、工具调用精确率", "中（需要日志 schema + 分析脚本）", "两个成功率相同的 agent 差在哪、成本从哪来", "某一步的决策在专家看来是否合理"],
            ["过程 process", "步骤级 rubric 得分、关键检查点命中率", "高（需要人工或强 judge 逐步标注）", "失败根因、局部能力缺口（如「不会读报错」）", "在真实分布上的整体成功率"],
        ]),
        DUAL(
            "为什么三层缺一不可？举个具体场景：两个 agent 在同一批任务上都拿到 40% 的成功率。"
            "第一个平均花 8 步、很少走弯路，失败时是「真的不会」；第二个平均花 47 步、"
            "反复试错撞对答案，成本是前者的六倍，而且一旦任务稍难就彻底崩掉。"
            "<strong>只看结果层，这两个 agent 完全一样；加上轨迹层，它们是两种完全不同的产品。</strong>",
            "从测量的角度：结果层给出的是一个伯努利变量的期望估计，信息量上界是 1 bit/任务；"
            "轨迹层把同一次 rollout 的其余观测量（动作序列长度、动作类型分布、失败-恢复事件）也纳入统计，"
            "在<strong>任务数固定</strong>的前提下显著提高了单位样本的信息量——这正是"
            "「任务集很贵，所以要从每条轨迹里榨出更多信息」这一工程现实的直接推论。"
            "<em>过程层则进一步把信用分配（credit assignment）做到步骤粒度，代价是引入了标注者主观性，"
            "因此它自己也需要一致性检验（呼应 C10 的标注科学）。</em>",
        ),
        CALLOUT("intuition", "记住这条分工：<strong>结果层用来做决策（发不发布、选哪个模型），"
                             "轨迹层用来做归因（钱花在哪、为什么慢），过程层用来做改进（下一步该修什么）。</strong>"
                             "把三者混在一张表里报告，往往意味着三个问题一个都没答清楚。"),
    ])),

    # ============================================================== 3
    ("seven-decisions", "一次 agent 评测的七个决策点", "".join([
        P("本课把「做一次 agent 评测」拆成七个必须显式做出的决策。"
          "这七个点也正好是 01–05 模块的路线图——每一个决策做错，后面所有数字都会失去意义。"),
        OL([
            "<strong>任务集从哪来</strong>：用公开基准还是自建任务集？公开基准要面对污染与任务质量问题，"
            "自建要面对样本量与代表性问题。→ <strong>01 模块</strong>",
            "<strong>判分函数怎么定义</strong>：执行测试、最终状态匹配、rubric checkpoint 还是 LLM judge？"
            "判分器的假阳性率是多少？→ <strong>02 模块</strong>",
            "<strong>部分得分给不给</strong>：全有全无（binary）还是分档？部分得分会改变模型排序吗？→ <strong>02 模块</strong>",
            "<strong>轨迹指标记哪些</strong>：日志 schema 决定了事后能算什么。没记的东西事后补不回来。→ <strong>03 模块</strong>",
            "<strong>跑几次、跑几个 seed</strong>：pass@k 还是 pass^k？两个 agent 差 3 个点算不算真的差？→ <strong>04 模块</strong>",
            "<strong>成本怎么归一化</strong>：给 A 无限预算、给 B 有限预算的对比是无意义的。→ <strong>05 模块</strong>",
            "<strong>harness 怎么固定与报告</strong>：scaffold 版本、工具集、超时、重试策略、容器镜像。→ <strong>05 模块</strong>",
        ]),
        CALLOUT("danger", "这七点里最容易被跳过、后果最严重的是第 7 条。"
                          "<strong>同一个模型换一套 scaffold，SWE-bench 分数可以差出十几个百分点</strong>——"
                          "这个幅度远大于多数模型版本之间的真实差距。"
                          "所以「模型 A 在 SWE-bench 上得 X 分」这句话如果不附带 harness 描述，"
                          "严格来说是<strong>无法被复现、也无法被比较</strong>的。"),
    ])),

    # ============================================================== 4
    ("division", "与既有课程的分工：本课补的是哪块洞", "".join([
        P("本仓库里与 agent 或评测相关的课程已经不少，所以先把边界划清楚，避免你在两门课里读到重复内容。"),
        TABLE(["课程", "它讲什么", "本课的关系"], [
            ["<strong>C03 · 评测科学</strong>", "静态基准全景、统计显著性、prompt 敏感性、污染、judge 入门、harness 概念", "本课假定你已经有 C03 的统计直觉。<strong>C03 的对象是「一次采样的正确率」，本课的对象是「一条轨迹的成败」</strong>——统计工具复用，被测量的量不同"],
            ["<strong>C04 模块 06 · agentic evals</strong>", "一节课的篇幅介绍 agent 评测的存在与几个基准名字", "本课是这一节的<strong>六倍展开</strong>：那一节告诉你「有这回事」，本课告诉你「怎么真的做一次」"],
            ["<strong>C26 模块 05 · agent eval & safety</strong>", "前沿 agent 的评测与安全概览", "同上，本课把评测那一半独立成课；安全那一半由 <strong>C69</strong>（Agent 安全与提示注入）接手"],
            ["<strong>C30–C34 · 动手造 agent</strong>", "harness、工具系统、编码 agent、上下文与记忆、编排", "那五门课教你<strong>造</strong>一个 agent，本课教你<strong>量</strong>一个 agent。05 模块的 harness 可复现性直接建立在 C30 的实现之上"],
            ["<strong>C10 · 评测数据与测量科学</strong>", "标注、一致性、IRT、校准、A/B", "本课 03 模块的过程级标注一致性直接复用 C10 的 kappa 工具；本课不重复推导"],
            ["<strong>C67 · LLM-as-a-Judge</strong>（同批新课）", "judge 的设计、偏差、元评测、排名、奖励模型", "本课 02/03 模块会<strong>用</strong> judge 来判分与评轨迹，但「judge 本身怎么设计与验证」全部交给 C67"],
            ["<strong>C68 · Eval 基础设施</strong>（同批新课）", "task spec、runner、缓存、CI 门禁、线上监控", "本课讲「评什么、怎么算」，C68 讲「这套评测怎么工程化地跑起来、跑很多次」"],
        ]),
        CALLOUT("intuition", "一句话记住这批新课的分工：<strong>C66 量 agent · C67 量判分器 · C68 把评测变成基础设施 · C69 量攻击面。</strong>"),
    ])),

    # ============================================================== 5
    ("env", "环境、依赖与本课的运行约定", "".join([
        P("本课<strong>全程 CPU、断网可跑、不需要任何 API key</strong>。这一点需要解释，因为「agent 评测」"
          "听起来天然需要真实模型和真实环境。本课的处理方式是把两件事分开："),
        UL([
            "<strong>评测的数学与工程</strong>（判分函数、部分得分、轨迹指标、pass^k、自举置信区间、"
            "成本-成功率前沿、harness 方差分解）——这些全部是<strong>确定性的计算</strong>，"
            "用 numpy 加一个模拟 agent 就能完整复现，而且比真实实验更适合学习：你可以<em>人为控制真值</em>，"
            "验证你的估计量是不是无偏的。",
            "<strong>真实基准的接入</strong>——每个模块末尾的「🧪 真实工程胶囊」给出可以原样复制到有网环境里跑的代码"
            "（SWE-bench 的加载与提交格式、inspect-ai 的 task 定义、容器化 harness 的启动脚本），"
            "但不作为课内练习的前置依赖。",
        ]),
        P("依赖只有 <code>numpy</code> 与 <code>matplotlib</code>（可选，只用于画前沿曲线），"
          "其余全是标准库。所有练习都有 <code>assert</code> 判分，跑通即通过。"),
        CODE("""pip install numpy matplotlib jupyterlab ipykernel
jupyter lab      # 或直接在 Colab 里点每个 notebook 顶部的徽章"""),
        CALLOUT("warn", "本课的模拟 agent 全部使用<strong>固定 seed 的 <code>numpy.random.Generator</code></strong>，"
                        "所有 <code>assert</code> 的期望值都是在这些 seed 下算出来的。"
                        "如果你改了 seed 又发现自测不过，那是预期行为——但请顺手想一下："
                        "<strong>一个换个 seed 就变的结论，本身就说明样本量不够</strong>，这正是 04 模块的主题。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（最小 agentic eval 端到端骨架 / 方差对比 / 七决策点自检）

目标：在读完讲解之后，用 90 行代码把「一次 agent 评测」完整地跑一遍——
环境、agent、判分器、报告四件套齐活，后面五个模块都是在这个骨架上加深某一块。

本 notebook 你会亲手实现：
1. **环境自检** —— 确认 numpy 可用，锁定随机数生成器的行为
2. **最小 agentic eval 骨架** —— 有状态环境 + 模拟 agent + 结果判分器 + 报告
3. **静态基准 vs agentic 基准的方差对比** —— 用数字说明「为什么 agent 评测需要更多样本」
4. **三层评测对象的信息量对比** —— 同样 40% 成功率的两个 agent，轨迹层如何把它们区分开
5. **七个决策点自检器** —— 把一份评测方案的完整度变成一个可以打分的清单

> 心智模型：**agent 评测的被测量对象不是「模型答得对不对」，而是「策略 × 环境」这个联合分布上的期望回报——
> 两个随机性来源，两倍的方差，以及一个需要被单独验证的判分函数。**"""),

    md("""## 0 · 环境自检"""),

    code("""import sys, math, json, statistics
from collections import Counter

import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

rng = np.random.default_rng(0)
probe = rng.integers(0, 10, size=5)
print('随机数探针:', probe)
assert probe.shape == (5,)
print('\\n✅ 环境就绪：本课全部内容 CPU 可跑、断网可跑，不需要任何 API key。')"""),

    md("""## 1 · 最小 agentic eval 端到端骨架

四个组件，缺一不可：

| 组件 | 职责 | 本课哪个模块深入 |
|---|---|---|
| `Environment` | 持有状态，接受动作，返回观测 | 05（可复现性） |
| `Agent` | 看观测、出动作，直到 done 或耗尽预算 | C30/C31（怎么造） |
| `Scorer` | 从终态或轨迹算出分数 | 02（结果）/ 03（轨迹） |
| `report` | 聚合、切片、带不确定度 | 04（统计）/ 05（成本） |

环境用一个「修 bug」的极简抽象：文件里有若干个 bug，agent 每次可以检查一个位置或修一个位置，
修对了 bug 数减一，修错了会引入新 bug（这一步是关键——**真实 agent 会把事情弄得更糟**）。"""),

    code("""class MiniRepoEnv:
    \"\"\"极简有状态环境：一个「代码仓库」里有 n_slots 个位置，其中若干个位置是坏的。
    动作: ('inspect', i) 返回该位置是否坏（带观测噪声）; ('fix', i) 尝试修复该位置。
    修一个好位置 = 把它弄坏（引入回归），这是真实 agent 最常见的失败模式之一。\"\"\"

    def __init__(self, n_slots, broken, seed=0, obs_noise=0.0):
        self.n_slots = n_slots
        self.broken = set(broken)
        self.rng = np.random.default_rng(seed)
        self.obs_noise = obs_noise
        self.steps = 0
        self.log = []                      # 轨迹：每一步记 (动作, 参数, 结果)

    def step(self, action, i):
        self.steps += 1
        if action == 'inspect':
            truth = i in self.broken
            if self.rng.random() < self.obs_noise:
                truth = not truth          # 观测噪声：工具偶尔返回错误信息
            self.log.append(('inspect', i, truth))
            return truth
        if action == 'fix':
            if i in self.broken:
                self.broken.discard(i)
                self.log.append(('fix', i, 'repaired'))
                return 'repaired'
            self.broken.add(i)             # 修一个本来好的位置 = 引入回归
            self.log.append(('fix', i, 'regression'))
            return 'regression'
        raise ValueError(action)

    def tests_pass(self):
        return len(self.broken) == 0


env = MiniRepoEnv(n_slots=8, broken=[2, 5], seed=1)
print('初始是否通过测试:', env.tests_pass())
env.step('inspect', 2); env.step('fix', 2); env.step('fix', 5)
print('修完两个 bug 后:', env.tests_pass(), '| 用了', env.steps, '步')
assert env.tests_pass() is True
env2 = MiniRepoEnv(n_slots=8, broken=[2], seed=1)
env2.step('fix', 7)                        # 修一个好位置
assert env2.tests_pass() is False and 7 in env2.broken
print('把好位置「修」坏之后:', env2.tests_pass(), '| 现在坏的位置:', sorted(env2.broken))
print('\\n✅ 环境就位。注意 fix 一个好位置会引入回归——这是 agent 评测里最重要的一类失败。')"""),

    code("""def careful_agent(env, budget=20):
    \"\"\"策略 A「谨慎型」：先 inspect 再 fix，只修被观测为坏的位置。步数多，但很少引入回归。\"\"\"
    for i in range(env.n_slots):
        if env.steps >= budget:
            break
        if env.step('inspect', i):
            if env.steps >= budget:
                break
            env.step('fix', i)
    return env


def eager_agent(env, budget=20):
    \"\"\"策略 B「激进型」：不 inspect，直接从头 fix 一遍。步数少一半，但会把好位置全弄坏。\"\"\"
    for i in range(env.n_slots):
        if env.steps >= budget:
            break
        env.step('fix', i)
    return env


def outcome_score(env):
    \"\"\"结果层判分器：最朴素的 binary——测试过了就是 1。\"\"\"
    return 1.0 if env.tests_pass() else 0.0


def run_eval(agent_fn, n_tasks=200, seed=0, obs_noise=0.0, budget=20):
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_tasks):
        n_slots = 8
        k = int(rng.integers(1, 4))                              # 每个任务 1-3 个 bug
        broken = rng.choice(n_slots, size=k, replace=False)
        env = MiniRepoEnv(n_slots, broken, seed=int(rng.integers(1 << 30)), obs_noise=obs_noise)
        agent_fn(env, budget=budget)
        rows.append({'task': t, 'score': outcome_score(env), 'steps': env.steps,
                     'regressions': sum(1 for a in env.log if a[2] == 'regression')})
    return rows


for name, fn in [('careful', careful_agent), ('eager', eager_agent)]:
    rows = run_eval(fn, n_tasks=200, seed=7)
    acc = float(np.mean([r['score'] for r in rows]))
    steps = float(np.mean([r['steps'] for r in rows]))
    reg = float(np.mean([r['regressions'] for r in rows]))
    print(f'{name:<8} 成功率 {acc:5.1%} | 平均步数 {steps:5.2f} | 平均引入回归 {reg:.2f}')

careful_rows = run_eval(careful_agent, n_tasks=200, seed=7)
assert np.mean([r['score'] for r in careful_rows]) > 0.9
print('\\n✅ 四件套跑通了。注意 eager 的失败不是「没做完」，而是「把好的弄坏了」——')
print('   只看成功率这个数字，你永远看不出这两种失败的区别。')"""),

    md("""## 2 · 静态基准 vs agentic 基准：方差从哪来

静态基准只有一个随机源（采样）。agentic 基准有两个（采样 + 环境），而且**误差沿轨迹累积**。
下面用同一个「真实能力 p=0.6」构造两种评测，看估计量的标准差差多少。"""),

    code("""def static_bench_trial(p_step, n_items, rng):
    \"\"\"静态基准：n_items 道独立单步题，每题成功率 p_step。\"\"\"
    return float(np.mean(rng.random(n_items) < p_step))

def agentic_bench_trial(p_step, n_items, horizon, rng, env_noise=0.15):
    \"\"\"agentic 基准：每题需要连续 horizon 步都成功；环境噪声会额外扰动单步成功率。\"\"\"
    out = []
    for _ in range(n_items):
        p_eff = np.clip(p_step + rng.normal(0, env_noise), 0.01, 0.99)   # 环境随机性
        out.append(float(np.all(rng.random(horizon) < p_eff)))
    return float(np.mean(out))

rng = np.random.default_rng(42)
P_STEP, N_ITEMS, HORIZON, N_TRIALS = 0.9, 100, 5, 400

static = [static_bench_trial(P_STEP, N_ITEMS, rng) for _ in range(N_TRIALS)]
agentic = [agentic_bench_trial(P_STEP, N_ITEMS, HORIZON, rng) for _ in range(N_TRIALS)]

print(f'静态基准   均值 {np.mean(static):.3f}  标准差 {np.std(static):.4f}')
print(f'agentic    均值 {np.mean(agentic):.3f}  标准差 {np.std(agentic):.4f}')
ratio = np.std(agentic) / np.std(static)
print(f'\\n同样 {N_ITEMS} 道题，agentic 基准的评测标准差是静态基准的 {ratio:.1f} 倍')
assert ratio > 1.5, '在两个随机源 + 多步累积下，agentic 的方差必然更大'
print('→ 想达到同样的分辨力，agentic 基准需要的任务数大致按方差比的平方增长（04 模块会精确算）。')
print(f'→ 顺带注意均值：单步 0.9 的能力，连做 {HORIZON} 步只剩 {np.mean(agentic):.0%}——')
print('   这就是「单步指标漂亮、端到端不行」的全部秘密：0.9^5 ≈ 0.59。')"""),

    md("""## 3 · 三层评测对象：同样 40%，完全不同的两个 agent

构造两个成功率都锁定在 40% 左右的 agent，看结果层如何把它们混为一谈、轨迹层如何把它们分开。"""),

    code("""def make_agent(p_success, mean_steps, recovery_rate, name, rng):
    \"\"\"造一批轨迹：成功率相同，但步数分布与错误恢复率不同。\"\"\"
    n = 300
    success = rng.random(n) < p_success
    steps = rng.poisson(mean_steps, size=n) + 1
    errors = rng.poisson(2.0, size=n)
    recovered = rng.binomial(errors, recovery_rate)
    return {'name': name, 'success': success, 'steps': steps,
            'errors': errors, 'recovered': recovered}

rng = np.random.default_rng(11)
A = make_agent(0.40, 8, 0.85, 'A·稳健', rng)
B = make_agent(0.40, 47, 0.25, 'B·蛮力', rng)

print(f"{'agent':<10}{'成功率':>8}{'平均步数':>10}{'恢复率':>10}{'相对成本':>10}")
for a in (A, B):
    rec = a['recovered'].sum() / max(a['errors'].sum(), 1)
    print(f"{a['name']:<10}{a['success'].mean():>8.1%}{a['steps'].mean():>10.1f}"
          f"{rec:>10.1%}{a['steps'].mean()/A['steps'].mean():>9.1f}x")

assert abs(A['success'].mean() - B['success'].mean()) < 0.08, '两者结果层几乎不可区分'
assert B['steps'].mean() > 4 * A['steps'].mean(), '轨迹层差距巨大'
print('\\n✅ 结果层：两个 agent 无法区分。轨迹层：成本差 5 倍以上、恢复率差 3 倍以上。')
print('   一份只报成功率的评测报告，会让你在这两个 agent 之间抛硬币。')"""),

    md("""## 4 · 七个决策点自检器

把「这份评测方案完整吗」变成一个可以打分的清单——07 项全中才算一份可复现、可比较的评测。"""),

    code("""SEVEN = [
    ('task_source',   '任务集从哪来：公开基准 / 自建？污染与代表性怎么处理'),
    ('scorer',        '判分函数怎么定义？判分器自身的假阳率是多少'),
    ('partial_credit','部分得分给不给？给了会不会改变模型排序'),
    ('traj_logging',  '轨迹记哪些字段？日志 schema 决定了事后能算什么'),
    ('n_seeds',       '跑几次几个 seed？用 pass@k 还是 pass^k'),
    ('cost_norm',     '成本怎么归一化？两个 agent 的预算可比吗'),
    ('harness_pin',   'harness 版本、工具集、超时、重试、镜像有没有钉死并写进报告'),
]

def audit(plan):
    \"\"\"plan: {决策点: bool}。返回 (得分, 缺失项列表)。\"\"\"
    missing = [desc for key, desc in SEVEN if not plan.get(key)]
    return (len(SEVEN) - len(missing)) / len(SEVEN), missing

typical_paper_plan = {'task_source': True, 'scorer': True, 'partial_credit': False,
                      'traj_logging': False, 'n_seeds': True, 'cost_norm': False,
                      'harness_pin': False}
score, missing = audit(typical_paper_plan)
print(f'一份「典型的技术报告」自检得分：{score:.0%}\\n')
for m in missing:
    print('  ✗', m)
assert abs(score - 3 / 7) < 1e-9
print('\\n✅ 这四项恰好是本课 02/03/05 模块的主题——也是绝大多数公开 agent 评测报告的共同缺口。')"""),

    md("""## ✏️ 练习 1：多步任务的端到端成功率

实现 `end_to_end(p_step, horizon)`：单步成功率 `p_step`、需要连续走对 `horizon` 步，
返回端到端成功率 $p^{h}$；再实现 `required_step_acc(target, horizon)`：
给定目标端到端成功率，反解单步需要多高，即 $p = \\text{target}^{1/h}$。"""),

    code("""def end_to_end(p_step, horizon):
    # TODO
    raise NotImplementedError

def required_step_acc(target, horizon):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(end_to_end(0.9, 5) - 0.59049) < 1e-9
assert abs(end_to_end(0.99, 50) - 0.99 ** 50) < 1e-12
assert abs(required_step_acc(0.5, 10) - 0.5 ** 0.1) < 1e-12
p_need = required_step_acc(0.9, 30)
assert abs(end_to_end(p_need, 30) - 0.9) < 1e-9
print(f'要让 30 步的任务有 90% 端到端成功率，单步准确率必须达到 {p_need:.4%}')
print('✅ 练习 1 通过：这条指数关系是所有 agent 评测的底色——')
print('   横向对比不同 horizon 的基准分数时，必须先想清楚 horizon 差多少。')"""),

    md("""## ✏️ 练习 2：轨迹层的成本-成功率比值

实现 `success_per_cost(rows)`：输入 `run_eval` 返回的行（含 `score` 与 `steps`），
返回 `总成功数 / 总步数`——即「每一步买到多少成功」。这是 05 模块成本前沿的最简版本。"""),

    code("""def success_per_cost(rows):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
demo = [{'score': 1.0, 'steps': 4}, {'score': 0.0, 'steps': 6}, {'score': 1.0, 'steps': 10}]
assert abs(success_per_cost(demo) - 2 / 20) < 1e-12

careful_rows = run_eval(careful_agent, n_tasks=200, seed=7)
eager_rows = run_eval(eager_agent, n_tasks=200, seed=7)
sc, se = success_per_cost(careful_rows), success_per_cost(eager_rows)
print(f'careful: 每步买到 {sc:.4f} 次成功 | eager: 每步买到 {se:.4f} 次成功')
assert sc > se, 'careful 步数多但成功率高得多，单位成本效率仍然更高'
print('✅ 练习 2 通过：「步数少」不等于「便宜」——便宜是每单位成功的代价，不是每条轨迹的代价。')"""),

    md("""## ✏️ 练习 3：判分器的假阳性会怎样污染结论

实现 `observed_rate(true_rate, fpr, fnr)`：判分器有假阳率 `fpr`（把失败判成成功）与
假阴率 `fnr`（把成功判成失败），返回观测到的成功率：

$$\\hat{p} = p(1-\\text{fnr}) + (1-p)\\cdot\\text{fpr}$$

再实现 `corrected_rate(observed, fpr, fnr)` 反解真实成功率（Rogan–Gladen 校正）。"""),

    code("""def observed_rate(true_rate, fpr, fnr):
    # TODO
    raise NotImplementedError

def corrected_rate(observed, fpr, fnr):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
assert abs(observed_rate(0.5, 0.0, 0.0) - 0.5) < 1e-12
assert abs(observed_rate(0.30, 0.10, 0.05) - (0.30 * 0.95 + 0.70 * 0.10)) < 1e-12
obs = observed_rate(0.30, 0.10, 0.05)
assert abs(corrected_rate(obs, 0.10, 0.05) - 0.30) < 1e-9
print(f'真实 30%、判分器 fpr=10% fnr=5% → 观测到 {obs:.1%}（虚高 {obs-0.30:+.1%}）')
low = observed_rate(0.05, 0.10, 0.05)
print(f'真实 5% 时观测到 {low:.1%}——虚高了 {low/0.05:.1f} 倍')
print('✅ 练习 3 通过：真实成功率越低，判分器假阳性的相对污染越严重——')
print('   这正是「难基准上的低分最不可信」的原因（02 模块展开）。')"""),

    md("""## ✏️ 练习 4：七决策点的加权完整度

实现 `weighted_audit(plan, weights)`：按权重计算完整度（权重字典的键是决策点名字），
返回 `已满足项权重之和 / 全部权重之和`。用它验证「harness_pin 权重最高时，
漏掉它的方案分数会掉得最狠」。"""),

    code("""def weighted_audit(plan, weights):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
W = {'task_source': 1, 'scorer': 2, 'partial_credit': 1, 'traj_logging': 1,
     'n_seeds': 2, 'cost_norm': 1, 'harness_pin': 3}
all_true = {k: True for k, _ in SEVEN}
assert abs(weighted_audit(all_true, W) - 1.0) < 1e-12
assert abs(weighted_audit({k: False for k, _ in SEVEN}, W)) < 1e-12

no_harness = dict(all_true, harness_pin=False)
no_partial = dict(all_true, partial_credit=False)
assert weighted_audit(no_harness, W) < weighted_audit(no_partial, W)
print(f'只漏 harness_pin：{weighted_audit(no_harness, W):.1%} | 只漏 partial_credit：{weighted_audit(no_partial, W):.1%}')
print(f'典型技术报告的加权完整度：{weighted_audit(typical_paper_plan, W):.1%}')
print('✅ 练习 4 通过：七项不等权——harness 没钉死，整份报告的可复现性直接归零。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def end_to_end(p_step, horizon):
    return float(p_step) ** horizon

def required_step_acc(target, horizon):
    return float(target) ** (1.0 / horizon)"""),

    code("""# 练习 2 参考答案
def success_per_cost(rows):
    total_steps = sum(r['steps'] for r in rows)
    total_success = sum(r['score'] for r in rows)
    return total_success / total_steps if total_steps else 0.0"""),

    code("""# 练习 3 参考答案
def observed_rate(true_rate, fpr, fnr):
    return true_rate * (1 - fnr) + (1 - true_rate) * fpr

def corrected_rate(observed, fpr, fnr):
    # 由 observed = p(1-fnr) + (1-p)fpr 反解 p
    return (observed - fpr) / (1 - fnr - fpr)"""),

    code("""# 练习 4 参考答案
def weighted_audit(plan, weights):
    total = sum(weights.values())
    got = sum(w for k, w in weights.items() if plan.get(k))
    return got / total if total else 0.0"""),

    md("""---
## 🧪 真实工程胶囊：把这个骨架换成真实基准

下面的代码不在本课内运行（需要网络与容器），但可以原样复制到有环境的机器上——
它和上面那个 90 行骨架是**同构**的，只是把 `MiniRepoEnv` 换成了真实的仓库容器。"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 加载 SWE-bench Verified 并检视一条任务的结构
# ══════════════════════════════════════════════════════════════════
from datasets import load_dataset
ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
ex = ds[0]
print(ex["instance_id"])        # 如 astropy__astropy-12907
print(ex["problem_statement"][:400])
print(ex["FAIL_TO_PASS"])       # 修复后必须由失败转为通过的测试
print(ex["PASS_TO_PASS"])       # 修复前后都必须通过的测试（防回归）
# 判分函数 = 在钉死的容器镜像里跑这两组测试。注意 PASS_TO_PASS 的存在——
# 它正是本课 MiniRepoEnv 里「fix 一个好位置会引入回归」的真实对应物。

# ══════════════════════════════════════════════════════════════════
# B. 提交格式：一条 prediction 就是一个 patch
# ══════════════════════════════════════════════════════════════════
# predictions.jsonl 每行:
# {"instance_id": "...", "model_name_or_path": "my-agent-v3", "model_patch": "<unified diff>"}
# 官方评测器（容器化，逐条起容器跑测试）:
#   python -m swebench.harness.run_evaluation \\
#       --dataset_name princeton-nlp/SWE-bench_Verified \\
#       --predictions_path predictions.jsonl \\
#       --max_workers 8 --run_id my-agent-v3
# 报告分数时必须同时报: 数据集版本 + harness commit + 容器镜像 tag + max_workers
# （并发度会影响超时行为，属于 harness 的一部分）。

# ══════════════════════════════════════════════════════════════════
# C. 用 inspect-ai 表达同一个骨架（task / solver / scorer 三件套）
# ══════════════════════════════════════════════════════════════════
from inspect_ai import Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.solver import basic_agent, system_message
from inspect_ai.tool import bash, python
from inspect_ai.scorer import includes

@task
def repo_fix():
    return Task(
        dataset=json_dataset("tasks.jsonl"),
        solver=basic_agent(
            init=system_message("You are a software engineer. Fix the failing tests."),
            tools=[bash(timeout=60), python(timeout=60)],
            max_attempts=3,
        ),
        scorer=includes(),
        sandbox="docker",         # ← 环境隔离；05 模块讲为什么这一行决定了可复现性
    )
# 运行: inspect eval repo_fix.py --model anthropic/claude-sonnet-5 --epochs 5
# --epochs 5 就是 04 模块要讲的「跑几次」——单次运行的 agent 分数几乎没有意义。
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 展开在 |
|---|---|---|
| agentic ≠ 多轮静态 | 被测量的是「策略 × 环境」联合分布上的期望回报，两个随机源 | 全课 |
| 三层评测对象 | 结果做决策、轨迹做归因、过程做改进 | 02 / 03 |
| 七个决策点 | 任务集 / 判分 / 部分得分 / 轨迹日志 / 重复次数 / 成本 / harness | 01–05 |
| $p^h$ 的暴政 | 单步 0.9、走 5 步只剩 0.59；横比不同 horizon 的分数必须先对齐 horizon | 04 |
| 判分器会污染结论 | 真实成功率越低，假阳性造成的相对虚高越严重 | 02 |

下一模块：**01 · agentic 基准全景**——把 SWE-bench、τ-bench、GAIA、WebArena、OSWorld
这些名字拆成「任务形态 / 判分方式 / 已知缺陷」三列，让你知道每个数字到底在测什么。""")
]
