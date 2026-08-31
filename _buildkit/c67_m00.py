# -*- coding: utf-8 -*-
"""C67 模块 00 · 课程总览与环境（LLM-as-a-Judge 与评分模型）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过 C03 模块 04（LLM judge 入门）或 C66 模块 02（判分器的 α/β）任一即可；"
                 "统计部分（kappa、自举、BT 模型）全部在课内从零推"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（环境自检 / 可控 judge 模拟器：真实质量 + 五个偏差旋钮 / '
                       'judge 误差如何传导成排名错误 / 三种用法的分辨力对比 / judge 体检六项清单）'),
    ("核心参考", "Zheng et al., <em>Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena</em>（NeurIPS 2023）· "
                 "Dubois et al., <em>Length-Controlled AlpacaEval</em>（2024）· "
                 "Bradley &amp; Terry（1952）· "
                 "本课程 C03 模块 04（judge 入门）· C10（测量科学）· C66 模块 02（判分器评测）"),
    ("预计时长", "读 45 分钟 + 跑 35 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("instrument", "judge 是测量仪器，不是裁判", "".join([
        P("这门课只有一个核心主张，值得放在最前面：<strong>当你用一个 LLM 去给另一个 LLM 的输出打分时，"
          "你并没有得到「答案」，你得到的是<em>一台测量仪器的读数</em>——"
          "而这台仪器自己有零点漂移、有量程限制、有系统性的方向偏差。</strong>"),
        P("这个视角带来的第一个推论是顺序上的：<strong>在用 judge 去比较两个模型之前，"
          "必须先评测 judge 本身</strong>。"
          "C66 模块 02 已经用确定性判分器（跑测试）演示过这条逻辑："
          "判分器有假阳率 $\\alpha$ 时，观测成功率是 $p(1-\\beta)+(1-p)\\alpha$，"
          "偏差不随样本量消失。<strong>LLM judge 只是把这个问题放大了一个数量级</strong>——"
          "因为它的 $\\alpha$ 和 $\\beta$ 不是常数，而是随着被评对象的<em>长度、风格、格式、"
          "甚至是不是它自己写的</em>而系统性变化。"),
        TABLE(["判分器类型", "$\\alpha,\\beta$ 的性质", "怎么估计", "本课程哪里讲"], [
            ["执行式（跑测试）", "常数，且通常很小", "金标准集，几十条即可", "C66 模块 02"],
            ["终态匹配 / 不变量", "常数，取决于不变量写得全不全", "同上", "C66 模块 02"],
            ["<strong>LLM judge</strong>", "<strong>随被评对象的属性系统性变化</strong>——长文本被高估、自己的输出被高估、排在后面的被高估", "需要人类标注的对照集 + 专门的偏差探针", "<strong>本课 02–03 模块</strong>"],
            ["奖励模型（RM）", "同上，且在训练分布外急剧退化", "RewardBench 类基准 + 分布外探针", "本课 05 模块"],
        ]),
        DUAL(
            "为什么不能像用尺子一样直接用 judge？因为尺子的误差与被测物无关——"
            "量一根 10 厘米的棍子和量一根 20 厘米的棍子，误差都是 ±0.5 毫米。"
            "<strong>而 LLM judge 的误差与被测物强相关：给一个写得长、格式漂亮、语气自信的答案，"
            "它系统性地打高分。</strong>这意味着误差不会在平均之后抵消，"
            "而是会<em>系统性地奖励某一类输出</em>——如果你再拿这个 judge 去做训练信号，"
            "模型就会朝那个方向漂过去。",
            "形式化地说，理想的 judge 是真实质量 $q$ 的无偏估计：$\\hat{q} = q + \\varepsilon$，"
            "$\\mathbb{E}[\\varepsilon] = 0$。实际的 judge 更接近 "
            "$\\hat{q} = q + f(\\text{length}, \\text{style}, \\text{position}, \\text{authorship}) + \\varepsilon$，"
            "其中 $f$ 是一个<strong>与内容质量无关但与可观测表面属性相关</strong>的系统项。"
            "<em>本课 02 模块的全部工作，就是把 $f$ 的各个分量识别出来、量化出来、"
            "并在可能时把它从读数里减掉。</em>",
        ),
        CALLOUT("danger", "一个直接的推论，也是这门课最实用的一句话：<strong>「我们用 GPT/Claude 做了 judge，"
                          "结果显示我们的模型更好」——这句话在没有给出 judge 体检数据时，"
                          "所包含的信息量接近于零。</strong>"
                          "体检至少要包括：与人类的一致率、位置偏差幅度、长度偏差幅度、以及人类自身的一致率上界。"
                          "六项清单在本模块 notebook 的最后一节。"),
    ])),

    # ============================================================== 2
    ("three-uses", "judge 的三种用法：打分、比较、校验", "".join([
        P("「LLM judge」这个词其实覆盖了三种在数学结构上完全不同的用法。"
          "混用它们是很多混乱的来源，所以先把它们分开。"),
        ASCII("""
   ① 打分 pointwise            ② 比较 pairwise             ③ 校验 verification
   ┌──────────────┐            ┌──────────────┐            ┌──────────────┐
   │ 输入: 一个答案 │            │ 输入: 两个答案 │            │ 输入: 一个答案 │
   │ 输出: 分数 1-5 │            │ 输出: A/B/平局 │            │ 输出: 通过/不通过│
   └──────────────┘            └──────────────┘            └──────────────┘
   量: 绝对质量                 量: 相对偏好                 量: 是否满足某个可判定条件
   问题: 分数分布压缩           问题: 位置偏差、不传递        问题: 需要条件本身可判定
   用途: 监控、门禁             用途: 模型选型、RLHF          用途: 事实核查、格式约束、约束满足
   → 01 模块                    → 01/04 模块                  → 05 模块（与 verifier 的边界）
"""),
        TABLE(["用法", "被估计的量", "典型失效", "什么时候该选它"], [
            ["<strong>pointwise 打分</strong>", "绝对质量 $q_i$", "<strong>分数分布严重压缩</strong>——绝大多数样本都落在 4 分，判别力接近零", "需要一个可以设阈值的绝对指标时（线上监控、CI 门禁）"],
            ["<strong>pairwise 比较</strong>", "偏好概率 $P(A \\succ B)$", "位置偏差、长度偏差、平局处理不当、<strong>可能违反传递性</strong>", "模型选型、构造偏好数据、排行榜"],
            ["<strong>校验</strong>", "某个可判定条件是否成立", "条件本身写得不可判定（「回答得好吗」不是条件）", "有明确规格可查时——<strong>能用校验就不要用打分</strong>"],
        ]),
        CALLOUT("intuition", "一条选择顺序，按可靠性从高到低：<strong>能写成校验的就写成校验，"
                             "写不成校验的用 pairwise，实在需要绝对分数才用 pointwise。</strong>"
                             "理由是它们对 judge 能力的要求依次升高——"
                             "判断「这段代码有没有调用指定的 API」比判断「这个回答好不好」容易得多，"
                             "也<em>客观</em>得多。<strong>很多被当成「主观质量」的东西，"
                             "其实可以被拆成一组客观校验项</strong>——这是 01 模块 rubric 设计的核心思想。"),
        P("需要强调一个边界：<strong>校验（verification）与 judge 不是同一件事</strong>。"
          "当条件可以由代码判定（正则、单元测试、schema 校验）时，那属于 C66 的确定性判分器范畴，"
          "不该请 LLM 来做。<em>只有在条件需要语义理解才能判定时</em>（「这段话有没有回答用户的问题」），"
          "才落进本课的范围。05 模块会把这条边界重新画一遍，"
          "因为它同时也是 RLVR（可验证奖励）与 RLHF（judge/RM 奖励）的分界线。"),
    ])),

    # ============================================================== 3
    ("why-hard", "judge 为什么难：四个结构性原因", "".join([
        P("如果 judge 只是「另一个模型调用」，它不值得一门课。它难在四个结构性的地方。"),
        OL([
            "<strong>没有金标准，或者金标准本身有噪声。</strong>"
            "「哪个回答更好」这个问题，两个人类标注员的一致率往往只有 70%–85%。"
            "<em>这意味着 judge 与人类的一致率存在一个由人类自身决定的上界</em>——"
            "judge 达到 82% 可能已经接近天花板，而不是「还差 18 个点」。"
            "<strong>不知道这个上界就无法判断 judge 好不好。</strong>（03 模块）",
            "<strong>偏差与内容强相关，因此不会被平均掉。</strong>"
            "位置、长度、风格、自偏好这四个偏差都是系统性的（第 1 节已述）。（02 模块）",
            "<strong>被评对象会适应 judge。</strong>"
            "一旦 judge 被用作训练信号或选型标准，优化压力就会去找它的漏洞。"
            "「写长一点分数就高」这件事一旦被发现，所有输出都会变长。（05 模块）",
            "<strong>成对比较到排名之间隔着一个模型。</strong>"
            "你手上是一堆「A 赢 B」，你想要的是一个排行榜。"
            "这中间需要 Bradley–Terry 或 Elo，而这两个模型都<em>假设了传递性</em>——"
            "而 LLM judge 的成对偏好经常违反传递性。（04 模块）",
        ]),
        DUAL(
            "把四条合起来看，你会发现一个规律：<strong>judge 的问题都不是「不够准」，"
            "而是「以特定方向不准」。</strong>随机误差可以靠多跑几次解决，"
            "系统偏差不行——它只会让你更自信地相信一个偏了的结论。"
            "所以这门课花在「测量偏差」上的篇幅，远多于花在「提高准确率」上的篇幅。",
            "从测量学的角度，这四条分别对应：<span class=\"term\">效标效度</span>的上界问题"
            "（criterion validity，金标准自身有噪声）、"
            "<span class=\"term\">系统误差</span>（systematic error）、"
            "<span class=\"term\">Goodhart 效应</span>（指标被优化后失效）、"
            "以及<span class=\"term\">测量模型的适配性</span>"
            "（把成对偏好聚合成一维分数，本身就假设了偏好可以被一个标量刻画）。"
            "<em>C10 用心理测量学的语言讲过前两条，本课把它们全部落到 LLM judge 这个具体对象上。</em>",
        ),
    ])),

    # ============================================================== 4
    ("division", "与既有课程的分工", "".join([
        TABLE(["课程", "它讲什么", "本课的关系"], [
            ["<strong>C03 模块 04</strong> · LLM judge", "judge 的存在、基本 prompt 形式、几个已知偏差的名字", "本课是这一节的<strong>六倍展开</strong>：那一节告诉你「有这回事、要小心」，本课给出量化每个偏差、并在报告里把它减掉的完整方法"],
            ["<strong>C66</strong> · Agent 评测（同批新课）", "确定性判分器的 α/β、部分得分、轨迹指标、pass^k、成本与 harness", "C66 <strong>用</strong> judge 判分，把「judge 本身怎么验证」留给本课。两课的核心逻辑相同：<em>先验证测量仪器，再相信读数</em>"],
            ["<strong>C10</strong> · 评测数据与测量科学", "标注、一致性系数、IRT、校准、A/B", "本课 03 模块的 kappa / Krippendorff / 校准全部复用 C10 的工具；<strong>本课的新东西是「人类上界」与「judge 分辨力」这两个 judge 特有的量</strong>"],
            ["<strong>C02</strong> · 后训练与对齐", "SFT → RLHF/DPO → RLVR 的训练流程", "C02 教你<strong>用</strong>奖励模型训练；本课 05 模块教你<strong>评测</strong>奖励模型，以及识别过优化"],
            ["<strong>C23</strong> · 前沿对齐", "CAI、可扩展监督、weak-to-strong", "那门课关心「用 AI 监督 AI 的可行性边界」，本课关心「用 AI 打分的测量学性质」——问题相关但层面不同"],
            ["<strong>C68</strong> · Eval 基础设施（同批新课）", "task spec、runner、缓存、CI 门禁、线上监控", "judge 的调用、缓存、成本控制在 C68 落地；judge 漂移的<strong>检测方法</strong>在本课 03 模块，<strong>线上告警的落地</strong>在 C68 05 模块；<strong>本课只管 judge 的正确性</strong>"],
        ]),
        CALLOUT("intuition", "一句话记住这批新课的分工：<strong>C66 量 agent · C67 量判分器 · "
                             "C68 把评测变成基础设施 · C69 量攻击面。</strong>"
                             "本课处在链条的第二环——如果这一环没做对，C66 与 C68 的所有数字都建立在流沙上。"),
    ])),

    # ============================================================== 5
    ("env", "环境、依赖与本课的运行约定", "".join([
        P("本课<strong>全程 CPU、断网可跑、不需要任何 API key</strong>。做法与 C66 相同："
          "把「judge 的测量学」与「judge 的调用」分开。"),
        UL([
            "<strong>测量学部分</strong>（偏差的识别与去除、kappa、人类上界、校准、Bradley–Terry 拟合、"
            "过优化曲线）全部是确定性计算。本课用一个<strong>可控的 judge 模拟器</strong>："
            "先设定每个回答的「真实质量」，再用几个显式的偏差旋钮（位置、长度、自偏好、噪声）"
            "生成 judge 的判断。<em>这比调真实 API 更适合学习——因为你知道真值，"
            "可以直接验证你的去偏方法有没有把偏差真的减掉。</em>",
            "<strong>真实调用部分</strong>放在每个模块末尾的「🧪 真实工程胶囊」里："
            "judge prompt 模板、结构化输出的 schema、swap 一致性的批量跑法、"
            "长度控制回归的实现、RewardBench 风格的评测脚本——可原样复制到有 key 的环境。",
        ]),
        CODE("""pip install numpy matplotlib jupyterlab ipykernel
jupyter lab      # 或直接在 Colab 里点每个 notebook 顶部的徽章"""),
        CALLOUT("warn", "关于模拟器有一个必须说清楚的地方：<strong>模拟器不是为了「假装有一个真 judge」，"
                        "而是为了让你能在<em>知道真值</em>的条件下检验估计量。</strong>"
                        "真实实验里你永远不知道真实质量是多少，"
                        "所以你无法判断「去偏之后的胜率」到底更接近真值还是更远。"
                        "<em>在模拟里你可以</em>——这是学习阶段唯一能做到的验证方式，"
                        "也是本课每个练习都用 <code>assert</code> 检查「去偏后更接近真值」的原因。"),
    ])),
    # ============================================================== 6
    ("failure-gallery", "五个真实场景：judge 在哪里骗过了人", "".join([
        P("最后用五个具体场景收尾。它们不是假想的——每一个都对应本课后面某个模块的主题，"
          "而且都<strong>不需要 judge「犯低级错误」就会发生</strong>。"),
        TABLE(["场景", "表面上看到的", "实际发生的", "本课哪里给出解法"], [
            ["<strong>新版本「提升了 6 个点」</strong>", "同一套 judge，新版本胜率从 48% 涨到 54%", "新版本的输出平均长了 40%，而这个 judge 的长度系数是 0.8——<strong>6 个点里有 5 个来自长度</strong>", "模块 02：长度控制回归"],
            ["<strong>「我们的 judge 与人类一致率 82%」</strong>", "听起来还差 18 个点", "人类之间的一致率只有 84%——<strong>82% 已经是天花板的 94%</strong>，继续优化 judge 的边际收益接近零", "模块 03：人类上界"],
            ["<strong>「A 和 B 差不多，都是 5 分」</strong>", "pointwise 打分区分不出来", "五档量表的有效档位数只有 1.6，<strong>八成样本都落在同一档</strong>——不是它们一样好，是尺子只有一个刻度", "模块 01：分布压缩与 rubric 分解"],
            ["<strong>「榜单第一名换人了」</strong>", "上周 M3 第一，这周 M1 第一", "两者的置信区间从头到尾就是重叠的，<strong>换人只是重采样噪声</strong>", "模块 04：名次区间"],
            ["<strong>「RL 训练曲线很漂亮」</strong>", "奖励分数持续上升 20k 步", "真实质量在 8k 步就见顶了，<strong>而代理奖励永远不会告诉你这件事</strong>", "模块 05：独立信号与拐点定位"],
        ]),
        DUAL(
            "这五个场景的共同结构值得说破：<strong>每一个里面，judge 都在忠实地执行它被要求做的事，"
            "数字也都是真的算出来的——错的是「这个数字支持什么结论」这一步推理。</strong>"
            "所以本课的重点不在「怎么让 judge 更准」，"
            "而在<strong>「怎么知道这个数字能支持什么、不能支持什么」</strong>。",
            "用测量学的语言，这五个场景分别是："
            "<span class=\"term\">构念无关方差</span>被误读为效应（长度）、"
            "<span class=\"term\">效标上限</span>被忽略（人类一致率）、"
            "<span class=\"term\">量表分辨率</span>不足被误读为「没有差异」、"
            "<span class=\"term\">抽样误差</span>被误读为真实变化（榜单换人）、"
            "以及<span class=\"term\">代理指标与目标指标背离</span>（过优化）。"
            "<em>五个都是经典的测量学错误，只是换到了 LLM 这个新对象上——"
            "这也是为什么本课大量复用 C10 的工具，而不是发明新的。</em>",
        ),
        CALLOUT("intuition", "如果你只带走一句话，带走这句：<strong>「judge 说 A 更好」这个结论，"
                             "在你知道这个 judge 的长度系数、swap 一致率和人类上界之前，"
                             "是一个<em>还没有完成</em>的结论。</strong>"
                             "本课剩下的五个模块，就是把它补完的方法。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（judge 模拟器 / 误差如何变成排名错误 / 三种用法的分辨力 / 体检清单）

目标：在读完讲解之后，建立一个**你知道真值**的 judge 实验台——
后面五个模块的所有去偏、校准、排名方法，都会在这个实验台上被验证。

本 notebook 你会亲手实现：
1. **环境自检**
2. **可控 judge 模拟器** —— 真实质量 + 五个显式偏差旋钮（位置 / 长度 / 自偏好 / 严厉度 / 噪声）
3. **judge 误差如何变成排名错误** —— 一致率 82% 的 judge，选错模型的概率是多少
4. **三种用法的分辨力对比** —— pointwise / pairwise / 校验，谁更能区分两个质量接近的模型
5. **judge 体检六项清单** —— 把「这个 judge 能不能用」变成一个可以打分的检查表

> 心智模型：**judge 不是裁判，是测量仪器。它的误差与被测物强相关，
> 因此不会在平均之后抵消，而是会系统性地奖励某一类输出。**"""),

    md("""## 0 · 环境自检"""),

    code("""import sys, math, json, itertools
from collections import Counter, defaultdict

import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)
rng = np.random.default_rng(0)
assert rng.integers(0, 10, size=3).shape == (3,)
print('\\n✅ 环境就绪：本课全部内容 CPU 可跑、断网可跑，不需要任何 API key。')"""),

    md("""## 1 · 可控 judge 模拟器

核心设计：每个回答有一个**真实质量** `q`（我们知道，judge 不知道）和一些**表面属性**
（长度、是不是 judge 自己写的）。judge 看到的是

$$\\hat{q} = q + \\underbrace{b_{\\text{len}}\\cdot z_{\\text{len}} + b_{\\text{self}}\\cdot \\mathbb{1}[\\text{自己写的}] + b_{\\text{pos}}\\cdot \\mathbb{1}[\\text{排在后面}]}_{\\text{系统偏差 }f} + \\varepsilon$$

**关键点：$f$ 与内容质量无关，所以它不会被平均掉。**"""),

    code("""class JudgeSim:
    \"\"\"可控的 LLM judge 模拟器。所有偏差都是显式旋钮，方便验证去偏方法。\"\"\"

    def __init__(self, b_len=0.0, b_self=0.0, b_pos=0.0, noise=0.3,
                 severity=0.0, seed=0):
        self.b_len = b_len          # 长度偏差：每 1 个标准差的长度，加多少分
        self.b_self = b_self        # 自偏好：judge 评自己的输出时加多少分
        self.b_pos = b_pos          # 位置偏差：排在第二位的答案加多少分
        self.noise = noise          # 随机噪声的标准差
        self.severity = severity    # 严厉度：整体平移（pointwise 打分时才可见）
        self.rng = np.random.default_rng(seed)

    def _perceived(self, q, z_len, is_self, is_second):
        return (q + self.b_len * z_len + self.b_self * is_self
                + self.b_pos * is_second - self.severity
                + self.rng.normal(0, self.noise, size=np.shape(q)))

    def pointwise(self, q, z_len=0.0, is_self=0, scale=5,
                  noise_mult=2.0, compression=0.6):
        \"\"\"返回 1..scale 的整数分。真实质量 q 假定在 [0,1]。
        两个经验事实被显式建模进来：
          ① 绝对打分比相对比较更难，噪声更大（noise_mult）；
          ② judge 很少给 1 分和 5 分，分数向中间收缩（compression）。\"\"\"
        q = np.asarray(q, dtype=float)
        v = (q + self.b_len * z_len + self.b_self * is_self - self.severity
             + self.rng.normal(0, self.noise * noise_mult, size=np.shape(q)))
        v = 0.5 + compression * (v - 0.5)
        return np.clip(np.round(v * (scale - 1) + 1), 1, scale)

    def pairwise(self, qa, qb, z_len_a=0.0, z_len_b=0.0,
                 self_a=0, self_b=0, a_first=True):
        \"\"\"返回 1 表示判 A 赢，0 表示判 B 赢。a_first=False 时 A 被放在第二位。\"\"\"
        va = self._perceived(np.asarray(qa, dtype=float), z_len_a, self_a, 0 if a_first else 1)
        vb = self._perceived(np.asarray(qb, dtype=float), z_len_b, self_b, 1 if a_first else 0)
        return (va > vb).astype(int)


rng = np.random.default_rng(1)
N = 4000
qa = rng.uniform(0, 1, N)
qb = rng.uniform(0, 1, N)
truth = (qa > qb).astype(int)                      # 真实的「谁更好」

clean = JudgeSim(noise=0.15, seed=2)
biased = JudgeSim(b_len=0.25, b_pos=0.15, noise=0.15, seed=3)

acc_clean = float((clean.pairwise(qa, qb) == truth).mean())
z_len_a = rng.normal(0, 1, N)                       # A 的长度（标准化后）
acc_biased = float((biased.pairwise(qa, qb, z_len_a=z_len_a) == truth).mean())
print(f'无偏 judge 与真值一致率: {acc_clean:.1%}')
print(f'有偏 judge 与真值一致率: {acc_biased:.1%}')
assert acc_clean > acc_biased
print('\\n✅ 实验台就位。注意：有偏 judge 的一致率只掉了几个点——')
print('   但它掉分的方式是**系统性的**（偏向长答案、偏向后一个位置），这才是真正的问题。')"""),

    code("""# 系统偏差不会被平均掉：看「长答案」这个子群上的胜率
long_mask = z_len_a > 1.0
short_mask = z_len_a < -1.0
pred = biased.pairwise(qa, qb, z_len_a=z_len_a)

print(f"{'子群':<14}{'真实 A 胜率':>12}{'judge 判 A 胜率':>18}{'偏差':>10}")
for name, m in [('A 写得很长', long_mask), ('A 写得很短', short_mask), ('全体', np.ones(N, bool))]:
    t, p = truth[m].mean(), pred[m].mean()
    print(f'{name:<14}{t:>12.1%}{p:>18.1%}{p-t:>+10.1%}')

bias_long = pred[long_mask].mean() - truth[long_mask].mean()
bias_short = pred[short_mask].mean() - truth[short_mask].mean()
assert bias_long > 0.05 and bias_short < -0.05
print('\\n✅ 全体上的偏差看起来不大，但拆开看：长答案被高估、短答案被低估。')
print('   **这就是「系统偏差不会被平均掉」的可见形式** —— 它只是在子群之间互相掩盖。')
print('   一旦你的模型开始写得更长，这个偏差就会全部变成虚假的分数提升。')"""),

    md("""## 2 · judge 误差如何变成排名错误

真正要回答的问题不是「judge 准不准」，而是**「用这个 judge 做选型，选错的概率是多少」**。"""),

    code("""def selection_error_rate(judge, q_gap, n_items=200, n_trials=400, seed=0):
    \"\"\"两个模型真实质量差 q_gap，用 judge 跑 n_items 道题的成对比较，
    以多数胜负决定选谁。返回选错的比例。\"\"\"
    rng = np.random.default_rng(seed)
    wrong = 0
    for _ in range(n_trials):
        base = rng.uniform(0, 1 - q_gap, n_items)
        qa_, qb_ = base + q_gap, base            # A 真实更好
        wins = judge.pairwise(qa_, qb_).mean()
        if wins <= 0.5:
            wrong += 1
    return wrong / n_trials

print(f"{'真实质量差':>12}{'干净 judge':>14}{'有偏 judge':>14}{'弱 judge':>12}")
weak = JudgeSim(noise=0.45, seed=7)
for gap in [0.02, 0.05, 0.10, 0.20]:
    e1 = selection_error_rate(JudgeSim(noise=0.15, seed=11), gap)
    e2 = selection_error_rate(JudgeSim(b_len=0.25, noise=0.15, seed=12), gap)
    e3 = selection_error_rate(weak, gap)
    print(f'{gap:>12.0%}{e1:>14.1%}{e2:>14.1%}{e3:>12.1%}')

e_small = selection_error_rate(JudgeSim(noise=0.45, seed=13), 0.02)
e_large = selection_error_rate(JudgeSim(noise=0.45, seed=13), 0.20)
assert e_small > e_large
print('\\n✅ 质量差越小，judge 噪声越致命。这解释了一个常见现象：')
print('   judge 在区分「强模型 vs 弱模型」时很可靠，在区分「两个都很强的模型」时几乎在抛硬币——')
print('   而后者恰恰是我们最常需要它做的判断。')"""),

    md("""## 3 · 三种用法的分辨力对比

同样的 judge 能力，pointwise / pairwise / 校验三种用法能区分多小的质量差？"""),

    code("""def pointwise_discrimination(judge, q_gap, n=3000, scale=5, seed=0):
    \"\"\"pointwise：给两个模型各打 n 个分，看均分差的 t 统计量（分辨力）。\"\"\"
    rng = np.random.default_rng(seed)
    base = rng.uniform(0, 1 - q_gap, n)
    sa = judge.pointwise(base + q_gap, scale=scale)
    sb = judge.pointwise(base, scale=scale)
    d = sa - sb
    return float(d.mean() / (d.std(ddof=1) / math.sqrt(n) + 1e-12))

def pairwise_discrimination(judge, q_gap, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    base = rng.uniform(0, 1 - q_gap, n)
    w = judge.pairwise(base + q_gap, base)
    p = w.mean()
    se = math.sqrt(max(p * (1 - p), 1e-12) / n)
    return float((p - 0.5) / se)

def verification_discrimination(q_gap, n=3000, base_pass=0.5, seed=0):
    \"\"\"校验：条件可判定，judge 几乎不出错；而且天然是配对的
    （同一道题、同一个条件，两个模型各查一次），任务难度这个方差源被直接消掉。\"\"\"
    rng = np.random.default_rng(seed)
    difficulty = rng.uniform(0, 1, n)                 # 每道题的难度（两个模型共享）
    a = (difficulty < np.clip(base_pass + q_gap, 0, 1)).astype(float)
    b = (difficulty < base_pass).astype(float)
    d = a - b
    return float(d.mean() / (d.std(ddof=1) / math.sqrt(n) + 1e-12))

j = JudgeSim(noise=0.3, seed=5)
print(f"{'质量差':>8}{'pointwise(1-5)':>18}{'pairwise':>12}{'校验':>10}   (|t| > 2 才算能分辨)")
for gap in [0.02, 0.05, 0.10]:
    print(f'{gap:>8.0%}{pointwise_discrimination(j, gap):>18.2f}'
          f'{pairwise_discrimination(j, gap):>12.2f}{verification_discrimination(gap):>10.2f}')

t_point = pointwise_discrimination(j, 0.05)
t_pair = pairwise_discrimination(j, 0.05)
t_ver = verification_discrimination(0.05)
assert t_ver > t_pair > t_point
print(f'\\n5% 质量差下的分辨力: 校验 {t_ver:.2f} > pairwise {t_pair:.2f} > pointwise {t_point:.2f}')
print('\\n✅ 同样的样本量，pairwise 的分辨力明显高于 pointwise。')
print('   原因：1-5 的整数分把信息量化掉了一大半（05% 的质量差根本不足以让分数跳一档）。')
print('   而校验的分辨力最高——因为它把主观判断换成了可判定的条件。')
print('   → 选择顺序：能写成校验就写成校验，其次 pairwise，最后才 pointwise。')"""),

    md("""## 4 · judge 体检六项清单

把「这个 judge 能不能用」变成一个可打分的检查表。六项全过才叫「体检过了」。"""),

    code("""JUDGE_CHECKS = [
    ('human_agreement', '与人类标注的一致率（必须同时给出人类之间的一致率作为上界）'),
    ('position_bias',   '交换 A/B 位置后判断翻转的比例（swap 一致性）'),
    ('length_bias',     '控制质量后，长度对胜率的边际影响'),
    ('self_preference', '评自己产出 vs 评他人产出的分差'),
    ('discrimination',  '能不能区分两个已知有 X 点差距的模型（分辨力）'),
    ('drift',           '同一批样本隔一段时间重判，结论是否一致（模型/prompt 漂移）'),
]

def judge_audit(report):
    passed = [k for k, _ in JUDGE_CHECKS if report.get(k) is True]
    missing = [d for k, d in JUDGE_CHECKS if not report.get(k)]
    return len(passed) / len(JUDGE_CHECKS), missing

typical_paper = {'human_agreement': True, 'position_bias': True,
                 'length_bias': False, 'self_preference': False,
                 'discrimination': False, 'drift': False}
score, missing = judge_audit(typical_paper)
print(f'一份「典型技术报告」的 judge 体检得分: {score:.0%}\\n')
for m in missing:
    print('  ✗', m)
assert abs(score - 2 / 6) < 1e-9
print('\\n✅ 这四项缺口恰好是本课 02-03 模块的主题。')
print('   注意 human_agreement 打勾还不够——**必须同时给出人类之间的一致率**，')
print('   否则你无法判断 82% 是「接近天花板」还是「还差得远」。')"""),

    md("""## ✏️ 练习 1：把一致率翻译成「选错的概率」

实现 `flip_probability(agreement, n_items)`：judge 在单题上与真值一致率为 `agreement`，
用 `n_items` 道题的多数投票做选型，返回**多数投票判错**的概率
（二项分布尾部，`n_items` 取偶数时平局按判错的一半算）。"""),

    code("""def flip_probability(agreement, n_items):
    # TODO：用 math.comb 直接求和，不要用蒙特卡洛
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(flip_probability(1.0, 100)) < 1e-12
assert abs(flip_probability(0.5, 100) - 0.5) < 1e-9      # 完全随机 → 一半概率判错
p60 = flip_probability(0.60, 100)
p82 = flip_probability(0.82, 100)
assert p82 < p60
for n_ in [10, 50, 100, 400]:
    print(f'n={n_:>4}  一致率60% → 判错 {flip_probability(0.60, n_):.2%} | '
          f'一致率82% → 判错 {flip_probability(0.82, n_):.4%}')
print('✅ 练习 1 通过：一致率 60% 的 judge 在 100 道题上就已经很可靠了——')
print('   **前提是它的误差是随机的**。系统偏差不会随 n 增大而消失（第 1 节），')
print('   所以这个公式只适用于随机误差部分，这正是要先量偏差再算样本量的原因。')"""),

    md("""## ✏️ 练习 2：分离随机误差与系统偏差

实现 `decompose_error(pred, truth, group_mask)`：返回
`(总错误率, 组内偏差, 组外偏差)`，其中偏差定义为 `pred.mean() - truth.mean()`。
用它验证：总错误率相同的两个 judge，可能一个是随机误差、一个是系统偏差。"""),

    code("""def decompose_error(pred, truth, group_mask):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
rng = np.random.default_rng(21)
n = 4000
truth_v = rng.integers(0, 2, n)
mask = rng.random(n) < 0.5
# judge R：纯随机误差，两个子群偏差都接近 0
pred_R = np.where(rng.random(n) < 0.075, 1 - truth_v, truth_v)
# judge S：系统偏差，只在 mask 组里偏向判 1
pred_S = np.where(mask & (rng.random(n) < 0.30), 1, truth_v)

for name, pred in [('R 随机误差', pred_R), ('S 系统偏差', pred_S)]:
    err, bin_, bout = decompose_error(pred, truth_v, mask)
    print(f'{name:<12} 错误率 {err:.1%} | 组内偏差 {bin_:+.3f} | 组外偏差 {bout:+.3f}')

err_R, bin_R, bout_R = decompose_error(pred_R, truth_v, mask)
err_S, bin_S, bout_S = decompose_error(pred_S, truth_v, mask)
assert abs(bin_R) < 0.05 and abs(bout_R) < 0.05
assert bin_S > 0.08 and abs(bout_S) < 0.02
assert abs(err_R - err_S) < 0.03, '两个 judge 的总错误率应当接近'
print('\\n✅ 练习 2 通过：只看错误率，两个 judge 差不多；')
print('   拆到子群看，S 在一个子群上系统性偏向判 1——多跑一万题也消不掉。')
print('   **这就是为什么 judge 体检必须按子群做，而不是只报一个总一致率。**')"""),

    md("""## ✏️ 练习 3：分辨力所需的样本量

实现 `n_for_discrimination(win_rate, target_z=2.0)`：judge 判 A 胜的概率是 `win_rate`
（真值应为 0.5 才叫无差异），求要让 $z = (p-0.5)/\\sqrt{p(1-p)/n}$ 达到 `target_z`
所需的最小样本量 $n$（向上取整）。"""),

    code("""def n_for_discrimination(win_rate, target_z=2.0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
n55 = n_for_discrimination(0.55)
n52 = n_for_discrimination(0.52)
assert n52 > n55
p = 0.55
z = (p - 0.5) / math.sqrt(p * (1 - p) / n55)
assert z >= 2.0 - 1e-9
for w in [0.75, 0.65, 0.55, 0.52, 0.51]:
    print(f'judge 判 A 胜率 {w:.0%} → 要达到 z=2 需要 {n_for_discrimination(w):>6,} 道题')
print('✅ 练习 3 通过：胜率 51% 需要上万道题——')
print('   而「两个都很强的模型」的真实胜率差往往就在 51%-53% 这个区间。')"""),

    md("""## ✏️ 练习 4：judge 体检的加权得分

实现 `weighted_judge_audit(report, weights)`：按权重算体检完整度。
用它验证「缺 human_agreement 比缺 drift 掉分更多」。"""),

    code("""def weighted_judge_audit(report, weights):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
W = {'human_agreement': 3, 'position_bias': 2, 'length_bias': 2,
     'self_preference': 1, 'discrimination': 2, 'drift': 1}
all_true = {k: True for k, _ in JUDGE_CHECKS}
assert abs(weighted_judge_audit(all_true, W) - 1.0) < 1e-12
assert abs(weighted_judge_audit({k: False for k, _ in JUDGE_CHECKS}, W)) < 1e-12
no_human = dict(all_true, human_agreement=False)
no_drift = dict(all_true, drift=False)
assert weighted_judge_audit(no_human, W) < weighted_judge_audit(no_drift, W)
print(f'只缺 human_agreement: {weighted_judge_audit(no_human, W):.1%}')
print(f'只缺 drift:          {weighted_judge_audit(no_drift, W):.1%}')
print(f'典型技术报告:        {weighted_judge_audit(typical_paper, W):.1%}')
print('✅ 练习 4 通过：六项不等权——没有与人类的对照，其余五项做得再好也说明不了 judge 是对的。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def flip_probability(agreement, n_items):
    p = float(agreement)
    half = n_items / 2
    total = 0.0
    for k in range(n_items + 1):
        prob = math.comb(n_items, k) * (p ** k) * ((1 - p) ** (n_items - k))
        if k < half:
            total += prob                 # 少数正确 → 判错
        elif k == half:
            total += 0.5 * prob           # 平局 → 一半概率判错
    return total"""),

    code("""# 练习 2 参考答案
def decompose_error(pred, truth, group_mask):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)
    m = np.asarray(group_mask, dtype=bool)
    err = float((pred != truth).mean())
    bias_in = float(pred[m].mean() - truth[m].mean()) if m.any() else 0.0
    bias_out = float(pred[~m].mean() - truth[~m].mean()) if (~m).any() else 0.0
    return (err, bias_in, bias_out)"""),

    code("""# 练习 3 参考答案
def n_for_discrimination(win_rate, target_z=2.0):
    p = float(win_rate)
    if abs(p - 0.5) < 1e-12:
        return float('inf')
    return math.ceil(target_z ** 2 * p * (1 - p) / (p - 0.5) ** 2)"""),

    code("""# 练习 4 参考答案
def weighted_judge_audit(report, weights):
    total = sum(weights.values())
    got = sum(w for k, w in weights.items() if report.get(k))
    return got / total if total else 0.0"""),

    md("""---
## 🧪 真实工程胶囊：一个可以直接用的 judge 调用骨架"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. pairwise judge 的最小可用 prompt（结构化输出，便于解析与统计）
# ══════════════════════════════════════════════════════════════════
JUDGE_PROMPT = "\n".join([
    "You are evaluating two responses to the same user request.",
    "",
    "<request>{request}</request>",
    "<response_a>{a}</response_a>",
    "<response_b>{b}</response_b>",
    "",
    "Evaluate against these criteria, in this order of importance:",
    "1. Correctness: are the factual claims accurate?",
    "2. Instruction following: does it do what was asked?",
    "3. Completeness: are required parts missing?",
    "4. Clarity.",
    "",
    "IMPORTANT: Do NOT reward length. A shorter response that fully answers",
    "is better than a longer one that padded. Do not reward confident tone.",
    "",
    "Return JSON only:",
    '{{"reasoning": "<2-3 sentences>", "verdict": "A" | "B" | "tie"}}',
])

# ══════════════════════════════════════════════════════════════════
# B. 必须成对调用：swap 一致性（02 模块的位置偏差探针）
# ══════════════════════════════════════════════════════════════════
def judge_pair(client, request, a, b):
    v1 = call_judge(client, JUDGE_PROMPT.format(request=request, a=a, b=b))
    v2 = call_judge(client, JUDGE_PROMPT.format(request=request, a=b, b=a))  # 交换
    # v2 的 "A" 指的是原来的 b —— 解析时必须翻译回来
    v2_translated = {"A": "B", "B": "A", "tie": "tie"}[v2["verdict"]]
    consistent = (v1["verdict"] == v2_translated)
    return {"verdict_1": v1["verdict"], "verdict_2": v2_translated,
            "consistent": consistent,
            # 不一致时记为 tie，是最保守也最常见的处理方式
            "final": v1["verdict"] if consistent else "tie"}
# 报告规范：swap 一致率必须与胜率一起报。一致率 < 80% 时，胜率基本不可信。

# ══════════════════════════════════════════════════════════════════
# C. 每次 judge 运行都要记的字段（否则事后无法做偏差分析）
# ══════════════════════════════════════════════════════════════════
JUDGE_ROW = {
  "item_id": "...", "judge_model": "...", "judge_prompt_hash": "e3a1…",
  "a_model": "...", "b_model": "...",
  "a_len_tokens": 412, "b_len_tokens": 890,     # ← 长度偏差分析必需
  "order": "ab",                                 # ← 位置偏差分析必需
  "verdict": "A", "verdict_swapped": "A", "consistent": True,
  "reasoning": "...", "latency_ms": 1830, "cost_usd": 0.0031,
}
# 缺 a_len_tokens / order 这两个字段，02 模块的所有去偏方法都做不了。
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 展开在 |
|---|---|---|
| judge 是测量仪器 | 它的误差与被测物强相关，不会被平均掉 | 全课 |
| 三种用法 | 能写成校验就写成校验，其次 pairwise，最后 pointwise | 01 / 05 |
| 四个结构性难点 | 金标准有噪声 / 系统偏差 / 被评对象会适应 / 成对到排名 | 02–05 |
| 误差→排名错误 | 质量差越小，judge 噪声越致命；51% 的胜率差需要上万道题 | 04 |
| 体检六项 | 一致率必须配着人类上界一起报 | 03 |

下一模块：**01 · Judge 设计**——打分粒度、rubric 拆解、参考答案、CoT 与结构化输出，
以及「为什么 1-5 分制会把你的判别力砍掉一半」。""")
]
