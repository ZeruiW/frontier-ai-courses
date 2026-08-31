#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C66 · Agent 评测与基准（Agentic Evaluation & Benchmarks）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c66_m00, c66_m01, c66_m02, c66_m03, c66_m04, c66_m05

CID = "C66_Agentic_Evaluation_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "agentic 评测不是「多轮版的静态基准」——被测量的对象从「一次采样的正确率」变成了"
     "<strong>「策略 × 环境」联合分布上的期望回报</strong>：两个独立随机源、误差沿轨迹指数放大、"
     "判分函数本身需要被评测 · "
     "<strong>三层评测对象</strong>——结果层做决策、轨迹层做归因、过程层做改进，"
     "任何只做一层的报告都是残缺的 · "
     "<strong>七个决策点</strong>（任务集 / 判分 / 部分得分 / 轨迹日志 / 重复次数 / 成本 / harness）"
     "构成 01–05 模块的路线图，其中<strong>第 7 条最常被跳过、后果最严重</strong>——"
     "同一个模型换套 scaffold，分数能差十几个点 · "
     "<strong>$p^h$ 的暴政</strong>：单步 0.9 的能力连做 5 步只剩 0.59，"
     "这条指数关系是横比不同 horizon 基准分数时必须先对齐的东西",
     c66_m00),
    ("01_benchmarks", "01_讲解.html", "01_benchmark_landscape.ipynb",
     "01 · agentic 基准全景",
     "记基准不要按机构或时间，唯一有用的分类维度是<strong>环境是什么</strong>——"
     "因为环境决定判分方式，判分方式决定这个分数能支持什么结论 · "
     "<strong>SWE-bench 的三个数字 2294 / 500 / 300</strong>："
     "Verified 的存在本身就是最重要的一课——一个被广泛引用的基准，在发布近一年后被发现"
     "有相当比例的任务<em>根本无法被正确完成</em>，<strong>坏题是常态而不是意外</strong> · "
     "<strong>τ-bench 的终态匹配与 pass^k</strong>：客服型 agent 的价值在可靠性，"
     "把 pass@8 拿去汇报等于在报告一个与产品价值无关的数字 · "
     "<strong>WebArena 的「不可能任务」</strong>是被严重低估的设计——没有它的基准会系统性奖励编造 · "
     "四种共同病灶（污染 / 坏题 / 环境漂移 / 饱和）分别对应四类效度威胁 · "
     "任务集健康度的信息论判据：<strong>成功率推向 30–70% 才有区分度，500 题分辨不了 3 个点</strong>",
     c66_m01),
    ("02_outcome_scoring", "02_讲解.html", "02_outcome_scoring.ipynb",
     "02 · 结果判分与部分得分",
     "判分函数是评测系统里<strong>唯一不允许出错的组件</strong>——它引入的是系统偏差而非方差，"
     "$n \\to \\infty$ 也消不掉；<strong>真实成功率越低，假阳性造成的相对虚高越严重</strong>"
     "（真实 5%、$\\alpha=10\\%$ 时观测到 14.3%，虚高近三倍） · "
     "<strong>变异测试</strong>量化「这组测试有多强」——弱判分任务不该进主指标 · "
     "<strong>把终态匹配重写成不变量检查</strong>：天然处理等价解、天然忽略无关字段、与执行式判分形式统一 · "
     "<strong>部分得分会翻转排序</strong>：二值问「能不能交付」，checkpoint 问「走得多远」，"
     "两个结论都是真的，报告里必须同时出现 · "
     "判分器被 hack 的六种方式，其中<strong>「patch 触碰测试文件即判 0」必须无条件写死在流水线第一行</strong> · "
     "<strong>micro 与 macro 排序不一致时，这件事本身就是报告里最重要的发现</strong>",
     c66_m02),
    ("03_trajectory", "03_讲解.html", "03_trajectory_eval.ipynb",
     "03 · 轨迹级与过程级评测",
     "结果层结构性看不见三件事：<strong>钱花在哪、卡在哪、能不能从错误里爬出来</strong> · "
     "轨迹分析是唯一「事前决定、事后无法补救」的环节——"
     "没记 <code>args_hash</code> / <code>status</code> / <code>attempt</code>，"
     "冗余率、恢复率、pass^k 就永远算不出来 · "
     "<strong>轨迹比较适合做断言，不适合做打分</strong>：必经动作用 LCS 子序列检查，"
     "把编辑距离当主指标等于在惩罚探索、训练 agent 模仿人类的低效 · "
     "<strong>失败模式七分类</strong>（互斥、有优先级）——在把失败归因为「模型不够强」之前，"
     "先排除循环、工具误用、预算耗尽、提前放弃这几类，它们换更强的模型解决不了 · "
     "过程标注的 <strong>kappa 低时先怀疑问法</strong>：把「这一步好不好」换成「是否让任务离目标更近」，一致性立刻上一个台阶 · "
     "<strong>Goodhart：「平均步数」这个指标不应该出现在任何报告里</strong>——"
     "失败的轨迹更短，所以降低平均步数的最省事路径是增加失败率",
     c66_m03),
    ("04_reliability", "04_讲解.html", "04_reliability_stats.ipynb",
     "04 · 可靠性与统计",
     "四个方差源分处不同层级：任务间与任务内可用统计处理，"
     "<strong>模拟器与 harness 的方差不是随机误差，是没被控制住的自变量</strong>，只能用工程消除 · "
     "<strong>pass@k 与 pass^k 只差一个位置，含义完全相反</strong>——"
     "判断标准只有一条：结果被执行之前，有没有人（或验证器）能挑一挑 · "
     "<strong>加重复的收益有天花板，加任务数的收益没有</strong>：$k\\to\\infty$ 只能把标准差压到 $\\sqrt{\\rho}$ 倍 · "
     "<strong>配对设计</strong>把最大的方差源直接消掉——500 道任务里往往只有两三成的不一致对携带信息 · "
     "<strong>把 $Nk$ 条 rollout 当独立样本是错的</strong>：独立单位是任务不是 rollout，"
     "朴素自举的区间窄近一半、覆盖率显著低于名义值 · "
     "<strong>「不显著」必须配着 MDE 一起报</strong> · "
     "<strong>胜者诅咒</strong>：20 个能力完全相同的模型，榜首平均虚高约 4–5 个点且复现时几乎必然易主",
     c66_m04),
    ("05_cost_harness", "05_讲解.html", "05_cost_and_harness.ipynb",
     "05 · 成本感知评测与 harness 可复现性",
     "<strong>「谁更强」在不固定预算时没有定义</strong>——任何 agent 的成功率都能靠多花钱提高，"
     "正确提法只有「同预算谁更准」和「同精度谁更便宜」两种 · "
     "成本归一化必须报 <strong>$/success 而不是 $/task</strong>，"
     "否则重蹈 03 模块 Goodhart 的覆辙（早放弃的 agent 每任务成本最低） · "
     "<strong>帕累托前沿</strong>上被支配的配置在任何预算下都不该选，"
     "而它们在真实评测里非常常见——通常意味着 scaffold 没调好 · "
     "<strong>best-of-n 对判分器假阳率极度敏感</strong>：$n$ 越大，交付出去的「成功」里假阳解占比越高 · "
     "<strong>scaffold 的主效应与交互项常常大于模型主效应</strong>——"
     "2×2 实验里换套 scaffold 就能翻转「哪个模型更强」的结论 · "
     "<strong>十项复现清单压成一个指纹</strong>，让「不可比较」变成机器可判定的一行 assert · "
     "最后把成功率翻译成期望效用：<strong>失败代价高时，加一个人工确认点比提分更划算</strong>",
     c66_m05),
]


def build():
    install_assets(DIR)
    for i, (folder, html_name, nb_name, h1, subtitle, mod) in enumerate(MODULES):
        prev = nxt = None
        if i > 0:
            p = MODULES[i - 1]; prev = ("../%s/%s" % (p[0], p[1]), p[3])
        if i < len(MODULES) - 1:
            n = MODULES[i + 1]; nxt = ("../%s/%s" % (n[0], n[1]), n[3])
        lesson(os.path.join(DIR, folder, html_name),
               num="%02d" % i, total=TOTAL, h1=h1, subtitle=subtitle,
               meta=mod.META, sections=mod.SECTIONS, prev=prev, nxt=nxt)
        notebook(os.path.join(DIR, folder, nb_name), mod.NB)

    index(
        os.path.join(DIR, "index.html"),
        title="Agent 评测与基准",
        subtitle="全库里 agent 评测此前只是 C04-06 与 C26-05 两个子模块——"
                 "「有这回事」讲过了，「怎么真的做一次」没有。"
                 "<strong>本课的核心主张：agentic 评测的被测量对象不是「模型答得对不对」，"
                 "而是「策略 × 环境」联合分布上的期望回报——两个随机源、一个需要被单独验证的判分函数、"
                 "以及一个影响常常大于模型本身的 scaffold。</strong>"
                 "不带成本与 harness 指纹的 agent 分数，既不可比较也不可复现。",
        pills=["6 模块",
               "三层评测：结果 / 轨迹 / 过程",
               "七个决策点：任务集 · 判分 · 部分得分 · 轨迹日志 · 重复次数 · 成本 · harness",
               "pass@k vs pass^k",
               "纯 numpy · CPU · 断网可跑"],
        howto="先读模块的 <code>NN_讲解.html</code>，再跑同目录下的同名 <code>.ipynb</code>。"
              "notebook 里每个概念都有可运行的实现与 <code>assert</code> 自测，"
              "四道 <code>✏️ 练习</code> 先自己写、写不出来再看 <code>📖 参考答案</code>。"
              "每个模块末尾的 <strong>🧪 真实工程胶囊</strong> 是可以原样复制到有网/有容器环境里跑的代码"
              "（SWE-bench 加载与提交、inspect-ai 的 task 定义、OpenTelemetry 轨迹埋点、vcrpy 录制回放），"
              "但不作为课内练习的前置依赖——<strong>本课全程 CPU、断网、无需 API key</strong>。",
        tracks=[
            ("第一段 · 测什么", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "agentic 与静态基准的五个结构性差异 · 三层评测对象 · 七个决策点 · "
                 "90 行的最小 agentic eval 端到端骨架"),
                ("01_benchmarks/01_讲解.html", "MODULE 01", "agentic 基准全景",
                 "按环境分类的基准地图 · SWE-bench 家族 · τ-bench 终态匹配 · WebArena 的不可能任务 · "
                 "四种共同病灶 · 自建任务集的六条规则"),
            ]),
            ("第二段 · 怎么判分", [
                ("02_outcome_scoring/02_讲解.html", "MODULE 02", "结果判分与部分得分",
                 "判分器的 α/β 与 Rogan–Gladen 校正 · 变异测试量测试强度 · 不变量优于快照 · "
                 "部分得分的排序翻转 · 六种 hack 与闸门 · micro vs macro"),
                ("03_trajectory/03_讲解.html", "MODULE 03", "轨迹级与过程级评测",
                 "日志 schema 是事前决定 · 六个轨迹指标 · 循环检测 · 必经动作断言 · "
                 "失败模式七分类 · 过程标注 kappa · Goodhart 与提前放弃"),
            ]),
            ("第三段 · 数字可不可信", [
                ("04_reliability/04_讲解.html", "MODULE 04", "可靠性与统计",
                 "四个方差源 · pass@k 与 pass^k 的无偏估计 · 配对设计与 McNemar · "
                 "聚类自举与有效样本量 · MDE · 胜者诅咒"),
                ("05_cost_harness/05_讲解.html", "MODULE 05", "成本感知评测与 harness 可复现性",
                 "成本-成功率帕累托前沿 · best-of-n 与判分器假阳率 · scaffold 2×2 与交互项 · "
                 "十项复现清单与指纹 · 评测卡 · 上线门槛的期望效用"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), README)
    text_file(os.path.join(DIR, "requirements.txt"), REQUIREMENTS)
    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


README = r"""
# C66 · Agent 评测与基准（Agentic Evaluation & Benchmarks）

> **一句话**：本课教你怎么<strong>量</strong>一个 agent——而 C30–C34 教你怎么<strong>造</strong>一个 agent。

6 个模块 · 纯 numpy / CPU / 断网可跑 · 每个模块 4 道 `✏️ 练习`（assert 判分）+ `📖 参考答案` +
`🧪 真实工程胶囊`（可原样复制到有网环境的代码）。

## 这门课补的洞

全库里与 agent 评测相关的内容此前只有两个子模块：

| 已有 | 覆盖了什么 | 缺什么 |
|---|---|---|
| **C04 模块 06** · agentic evals | 一节课的篇幅，介绍 agent 评测的存在与几个基准名字 | 怎么真的做一次 |
| **C26 模块 05** · agent eval & safety | 前沿 agent 评测与安全概览 | 同上；且评测与安全混在一起 |

本课是这两节的六倍展开。核心主张：

> **agentic 评测的被测量对象不是「模型答得对不对」，而是「策略 × 环境」联合分布上的期望回报。**
> 这带来三个静态基准里不存在的问题：两个独立的随机源、一个需要被单独验证的判分函数、
> 以及一个影响常常大于模型本身的 scaffold。

## 与相邻课程的分工

| 课程 | 它讲什么 | 与本课的关系 |
|---|---|---|
| **C03** · 评测科学 | 静态基准、统计显著性、prompt 敏感性、污染、judge 入门 | 统计工具复用，**被测量的量不同**：C03 是「一次采样的正确率」，本课是「一条轨迹的成败」 |
| **C04 / C26** · agent 课 | agent 能力全景 + 一节 agentic evals | 本课是那一节的六倍展开 |
| **C30–C34** · 动手造 agent | harness、工具系统、编码 agent、上下文、编排 | 那五门教你**造**，本课教你**量**；05 模块的 harness 可复现性建立在 C30 之上 |
| **C10** · 评测数据与测量科学 | 标注、一致性、IRT、校准、A/B | 本课 03 模块的过程标注 kappa 直接复用 C10-02，不重复推导 |
| **C67** · LLM-as-a-Judge（同批新课） | judge 的设计、偏差、元评测、排名、奖励模型 | 本课**用** judge 判分，但「judge 本身怎么设计与验证」全部交给 C67 |
| **C68** · Eval 基础设施（同批新课） | task spec、runner、缓存、CI 门禁、线上监控 | 本课讲「评什么、怎么算」，C68 讲「这套评测怎么工程化地跑很多次」 |
| **C69** · Agent 安全（同批新课） | 提示注入、工具供应链、沙箱与权限、注入基准 | 本课 03 模块的「越权/副作用」失败类别在 C69 展开成一门课 |

**一句话记住这批新课的分工**：**C66 量 agent · C67 量判分器 · C68 把评测变成基础设施 · C69 量攻击面。**

## 模块表

| 模块 | 主题 | 目录 | notebook 的核心产出 |
|---|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` | 90 行的最小 agentic eval 端到端骨架（环境+agent+scorer+报告） |
| 01 | agentic 基准全景 | `01_benchmarks/` | 基准画像库 · 判分方式决策树 · 任务信息量 · n-gram 与时间截断污染检测 |
| 02 | 结果判分与部分得分 | `02_outcome_scoring/` | 变异测试 · 判分器混淆矩阵与 Rogan–Gladen 校正 · 排序翻转实验 · hack 闸门 |
| 03 | 轨迹级与过程级评测 | `03_trajectory/` | 六个轨迹指标 · 循环检测 · LCS 必经动作断言 · 失败七分类 · Goodhart 演示 |
| 04 | 可靠性与统计 | `04_reliability/` | pass@k / pass^k 无偏估计 · 预算最优分配 · 聚类自举覆盖率实验 · 胜者诅咒 |
| 05 | 成本与 harness 可复现性 | `05_cost_harness/` | 帕累托前沿 · best-of-n 陷阱 · scaffold 2×2 · 配置指纹 · 评测卡生成器 |

## 七个决策点速记卡

这是贯穿全课的骨架。做一次 agent 评测，这七个决策必须被显式做出——每一个做错，后面所有数字都失去意义。

| # | 决策 | 做错的后果 | 展开在 |
|---|---|---|---|
| 1 | 任务集从哪来 | 污染 / 坏题 / 不代表你的场景 | 01 |
| 2 | 判分函数怎么定义 | 系统偏差，$n\to\infty$ 也消不掉 | 02 |
| 3 | 部分得分给不给 | 排序翻转而你不知道 | 02 |
| 4 | 轨迹记哪些字段 | 事后永远算不出恢复率、冗余率、pass^k | 03 |
| 5 | 跑几次几个 seed | 把噪声读成差异 | 04 |
| 6 | 成本怎么归一化 | 拿无限预算和有限预算做对比 | 05 |
| 7 | harness 怎么钉死并报告 | **结果不可复现、不可比较** | 05 |

## 报告自检清单（六个 yes 才能发出去）

- [ ] 判分器的 α/β 量过了吗？（模块 02）
- [ ] $N$ 和 $k$ 分开写了吗？置信区间用的是**聚类**自举吗？（模块 04）
- [ ] MDE（最小可检测差异）写了吗？（模块 04）
- [ ] 成本报的是 `$/success` 而不是 `$/task` 吗？（模块 05）
- [ ] baseline scaffold 的分数给了吗？（模块 05）
- [ ] fingerprint 写进报告了吗？（模块 05）

## 学习路径

### 路径 A · 完整走一遍（约 10–12 小时）

`00 → 01 → 02 → 03 → 04 → 05`，每天一个模块：先读 HTML 讲解，再跑同名 notebook 把每个估计器亲手跑一遍。

判断走完了没有的标准：**给你一份任意的公开 agent 评测报告，你能不能在五分钟内指出它缺了哪几行、
以及这些缺失分别会让哪些结论失效。**

### 路径 B · 只想把手上的评测做对（约 4 小时）

`00 全部 → 02 全部 → 04 全部 → 05 第 5 节（复现清单）`。

理由：**判分器（02）和统计（04）是错了就全盘皆输的两块**，01 的基准全景可以按需查阅，
03 的轨迹指标可以等你有了日志再回来补。

### 路径 C · 只有两小时

`00 的三层评测对象与七决策点 → 02 的 Rogan–Gladen 校正 → 04 的 pass@k vs pass^k → 05 的复现清单`。

这四块是「知道了就能立刻少犯错」的部分。

## 环境

```bash
pip install -r requirements.txt      # numpy + matplotlib + jupyterlab
jupyter lab
```

全程 CPU、断网可跑、不需要任何 API key。所有模拟 agent 使用固定 seed 的
`numpy.random.Generator`，`assert` 的期望值都是在这些 seed 下算出来的——
**改了 seed 发现自测不过是预期行为，而这本身就是模块 04 的主题。**
"""

REQUIREMENTS = r"""
# Agent 评测与基准 —— 依赖清单
# 纯 numpy + Python 标准库，CPU 可跑、断网可跑，单个 notebook 通常几秒到一分钟跑完。
# 本课不训练也不调用任何模型——所有实验都是数值模拟 + 估计量验证：
# 用可控的模拟 agent 造出已知真值的场景，再验证你的估计量是不是无偏的。
# 真实基准（SWE-bench / τ-bench / WebArena / inspect-ai）的接入代码放在每个模块末尾的
# 「🧪 真实工程胶囊」里，可原样复制到有网、有容器的机器上跑，不作为课内练习的前置依赖。

numpy          # 全课：方差分解、自举、pass@k 组合估计、帕累托前沿、覆盖率实验
matplotlib     # 可选：成本-成功率前沿曲线、pass^k 衰减曲线、覆盖率对比图
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel

# —— 以下全部是 Python 标准库，无需安装 ——
# math         # 全课：组合数 comb（pass@k 无偏估计）、erfc（McNemar 的 p 值）、对数与开方
# json         # 03/05 模块：轨迹 schema 的序列化、配置指纹的稳定序列化
# hashlib      # 03/05 模块：args_hash（冗余率检测）、run fingerprint（可复现性）
# collections  # 全课：Counter（失败分类统计）、defaultdict（按子集聚合）
# itertools    # 02/05 模块：组合枚举、帕累托前沿的两两比较
# statistics   # 备用：分位数与中位数的标准库实现
# re           # 01 模块：n-gram 污染检测的分词

# —— 真实工程胶囊里出现、但课内不需要安装的包（列在这里方便你按需取用）——
# datasets          # 加载 SWE-bench / SWE-bench Verified
# inspect-ai        # 声明式 eval：task / solver / scorer 三件套（C68 会展开）
# opentelemetry-sdk # 轨迹埋点（GenAI 语义约定）
# vcrpy             # HTTP 录制回放，联网评测的可复现方案
# mutmut            # 变异测试，量化判分测试的强度
"""

GLOSSARY = r"""
# 术语词典 · Glossary（Agent 评测与基准）

> 按主题分组。每条给出：**英文 / 中文 / 一句话定义 / 为什么重要 / ⚠️ 常见误解**。
> 这份词典的组织原则是「七个决策点」：任务集 → 判分 → 部分得分 → 轨迹 → 统计 → 成本 → harness。
> 与相邻课程的分工见 [README](README.md)：judge 的设计与验证在 C67，评测基础设施在 C68，
> agent 攻击面在 C69，静态基准的统计在 C03。**本课只管「怎么量一个 agent」。**

---

## 一 · 总体框架 · Framework

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| agentic evaluation | agentic 评测 | 对在有状态环境中多步行动的策略进行的评测，被测量的量是「策略 × 环境」联合分布上的期望回报。 | 它与静态基准的差别不是「步数变多」，而是被测量对象的数学结构变了——两个独立随机源、误差沿轨迹放大、判分函数需要被单独验证。 | 以为它只是「多轮版的 MMLU」。**静态基准的 prompt 模板影响有限，agent 的 scaffold 是一整个程序**，它决定模型能看到什么、能做什么、什么时候停。 |
| outcome / trajectory / process layer | 结果层 / 轨迹层 / 过程层 | 三个评测粒度：任务完成了没有 / 它是怎么做到的 / 每一步做得对不对。 | 三层服务于不同目的：**结果层做决策、轨迹层做归因、过程层做改进**，缺一层的报告都是残缺的。 | 以为层级越细越好、应该都用过程层。**过程层标注极贵且主观性高**，它不能替代结果层作主指标——过程好但没做完，产品价值是 0。 |
| horizon | 时间跨度 / 步数跨度 | 完成一个任务需要的动作步数；也指「以 50% 成功率完成的任务，人类专家要花多久」这一报告维度。 | 端到端成功率约为单步成功率的 $h$ 次方，**单步 0.9、走 5 步只剩 0.59**——横比不同 horizon 的基准分数前必须先对齐 horizon。 | 以为「单步准确率高 = agent 强」。**指数关系意味着单步 99% 在 50 步任务上也只有 60%**，长程任务对单步可靠性的要求高得反直觉。 |
| scaffold / harness | 脚手架 / 评测框架 | 包裹模型的那整套程序：工具集、提示、循环结构、预算与终止条件、上下文管理、错误处理。 | **在 agentic 基准上，换一套 scaffold 造成的分数变化经常超过两代模型之间的差距**——不报 scaffold 的分数不构成可比较的结果。 | 以为 scaffold 只是「prompt 工程」。它包含最大步数、超时、重试、并发这些**最影响分数也最常被漏写**的参数。 |
| specification gap | 规格缝隙 | 你真正想要的目标（修好代码）与你写下的判分条件（让测试变绿）之间的差距。 | 所有 reward hacking / 判分器被 hack 的行为都发生在这条缝隙里——**问题出在规格不完整，不在 agent 学坏了**。 | 以为可以靠「更聪明的模型」消除。**优化压力只会把解推向 $\arg\max S(x)$**，缝隙越大被利用得越彻底。 |

---

## 二 · 基准与任务集 · Benchmarks & Task Sets

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| SWE-bench | — | 从 12 个 Python 开源仓库的已合并 PR 构造的代码修复基准，判分靠在钉死的容器里跑测试。 | 它演示了一个好的 agentic 基准该长什么样（判分完全确定性），也演示了它会踩哪些坑（坏题、污染、测试强度不均）。 | 以为 2294 条任务都是有效的。**SWE-bench Verified（500 条人工审核子集）的存在，本身就说明坏题是常态**。 |
| FAIL_TO_PASS / PASS_TO_PASS | 由红转绿 / 保持绿 | 前者是修复后必须由失败变通过的测试，后者是修复前后都必须通过的测试。 | **P2P 是防回归的闸门**——只检查目标行为的判分器一定会被 hack（把文件删了重写也能过 F2P）。 | 以为 P2P 是可选的补充检查。**没有 P2P 的判分函数在数学上是一个不完全规格**，允许大量「通过判分但语义错误」的解。 |
| final-state matching | 终态匹配 | 不看 agent 说了什么，只比对环境（数据库/文件系统）的最终状态与标注的目标状态。 | 绕开了「同一件事有很多种说法」的自然语言判分难题，是工具型 agent（客服、运维）的标准判分方式。 | 以为只要比对快照就行。**它有三个必须显式做的决策**：抽象到哪一层、等价解怎么处理、过程中的越权动作算不算失败。 |
| invariant check | 不变量检查 | 不比对具体终态，而是断言一组必须成立的属性（「用户在周五有两张有效机票」）。 | **这是终态匹配的推荐升级形式**：天然处理等价解、天然忽略无关字段、与执行式判分形式统一（一组断言全过才算 1 分）。 | 以为不变量不如快照严格。恰恰相反——快照对无关字段过敏（时间戳、自增 ID），**不变量才是真正编码了「什么叫做对了」**。 |
| impossible task | 不可能任务 | 在给定环境中根本无法完成的请求，正确行为是识别并明确放弃。 | **没有这类任务的基准会系统性奖励「编造一个看起来完成了的答复」**——而这是 agent 在真实产品里最危险的失败模式。 | 以为它是刁难。它测的是**校准与诚实**，自建任务集应留出 5%–15%。 |
| contamination | 污染 | 任务或其解法已经进入模型训练语料。 | agent 基准的任务来自公开仓库与网页，污染是默认状态；更隐蔽的是**解法泄漏**——issue 评论区里就贴着正确补丁。 | 以为 n-gram 检测就够了。**它只抓逐字重合**，抓不到改写；需要配合时间截断检验与「不给题面只给文件名」的行为学检验。 |
| environment drift | 环境漂移 | 依赖版本、页面结构、外部 API 随时间变化，导致同一份代码在不同时间跑出不同分数。 | 它让历史结果不可复现，是「论文数字复现不出来」的常见根因。 | 以为钉死 docker tag 就够了。**tag 会被覆盖**，必须钉 `sha256:` digest。 |
| task-set health | 任务集健康度 | 各任务二元熵的平均——衡量「名义 N 道题里，实际有多少道在干活」。 | 全对或全错的任务对「区分 A 和 B」贡献 0 bit；**把成功率推向 30–70% 等价于把每题的信息量推向最大**。 | 以为难题越多越好。**全是难题 = 全零 = 没有区分度**，与全是简单题一样糟。 |

---

## 三 · 判分与部分得分 · Scoring & Partial Credit

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| scorer false positive rate ($\alpha$) | 判分器假阳率 | 判分器把失败判成成功的比例。 | **它引入的是系统偏差而非方差，$n\to\infty$ 也消不掉**；真实成功率越低，相对虚高越严重（真实 5%、$\alpha=10\%$ → 观测 14.3%）。 | 以为多跑几道题就能平均掉。**bias 是 0.10 而 var 的标准差只有 0.02 时，把方差再压一半是完全无意义的工作**。 |
| Rogan–Gladen correction | Rogan–Gladen 校正 | 用判分器的 $\alpha,\beta$ 把观测成功率还原成真实成功率：$(\hat p-\alpha)/(1-\beta-\alpha)$。 | 它把「判分器不完美」这件事从一句免责声明变成一个可以算的修正量。 | 以为校正结果落到 $[0,1]$ 之外是 bug。**那是信号**：观测到的成功可以完全由假阳性解释，正确结论是「无法区分于零」。 |
| mutation testing | 变异测试 | 对被测代码注入微小语义改动（变异体），看测试组能杀掉几个；杀死比例即变异分数。 | **测试强度决定判分强度**；变异分数 < 0.6 的任务，其分数不应进入主指标。 | 以为它太贵不实用。**它是任务集的质量属性，只在构建期算一次**，存成任务元数据后可随时做「只用强判分任务重算」的敏感性分析。 |
| partial credit / checkpoint | 部分得分 / 检查点 | 把任务拆成有序关键节点，按达成了几个给分。 | 难基准上大量任务全员 0 分时，它是唯一能保住信息量的手段；也是定位「卡在哪一步」的工具。 | 以为它总是比二值判分更好。**它可以在不改变任何运行结果的前提下翻转两个模型的排名**——二值问「能不能交付」，checkpoint 问「走得多远」。 |
| checkpoint monotonicity | 检查点单调性 | 达成第 $k$ 个检查点必然意味着达成了前 $k-1$ 个。 | 不单调的检查点集合会让「达成率」这个数字失去意义（可以跳着达成）。 | 以为这是形式主义。**加上「最后一个检查点等价于二值成功」这条**，部分得分才成为二值判分的严格加细而非另一套指标。 |
| scorer hacking | 判分器 hack | 让判分函数返回 1 但没真正完成任务的行为：改测试、删测试、特判输入、污染判分环境、猜答案、钻等价类空子。 | 它不需要「作弊意图」——agent 只是在优化你给的目标。 | 以为要靠复杂的启发式检测。**「patch 触碰测试文件即判 0」是零假阳性、零成本、拦掉最严重作弊的硬规则**，必须无条件写在流水线第一行。 |
| held-out tests | 留出测试 | 判分测试之外另备一组不公开的测试，用于复判。 | **它是唯一能抓「特判输入」这类 hack 的手段**。 | 以为公开测试足够多就不需要。只要测试是可见的，特判就有生存空间。 |
| micro / macro average | 微平均 / 宏平均 | 前者所有任务一视同仁，后者先按子集求平均再对子集求平均。 | 任务数不均衡时两者可能给出**相反的排序**。 | 以为要「选一个对的」。**两者排序不一致这件事本身就是报告里最重要的发现**——谁更强取决于你关心哪个子集。 |

---

## 四 · 轨迹与过程 · Trajectory & Process

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| trajectory | 轨迹 | 一次任务运行中动作、观测、状态的完整序列。 | 它是回答「钱花在哪、卡在哪、能不能自救」的唯一数据来源，而这三件事结果层结构性看不见。 | 以为轨迹只是调试日志。**轨迹的 schema 是事前决定、事后无法补救的**——没记 `args_hash` 就永远算不出冗余率。 |
| recovery rate | 恢复率 | 出现工具错误后，agent 换了策略并最终成功的比例。 | 真实环境里工具报错是常态而非异常；**离线成功率 60% 的 agent 若不会自救，上线可能掉到 20%**，而这个落差在任何总成功率数字里都看不见。 | 以为它是次要指标。它是**把 demo 变成产品的最关键能力**，且必须靠主动注入错误来测（0% / 10% / 25% 三档跑三条曲线）。 |
| redundancy rate | 冗余率 | `(tool, args_hash)` 重复出现的步数占比。 | 它是检测「原地打转」最便宜的信号，可直接接到预算控制上（检出即终止）。 | 以为重复调用都是浪费。**合法轮询（等任务完成）会被误判**，需要白名单。 |
| loop detection | 循环检测 | 精确循环（滑窗内动作序列重复）与语义循环（状态摘要连续 $k$ 步不变）。 | 循环是最常见、最贵、也最容易自动检出的失败；提前终止能把省下的预算拿去跑别的任务。 | 以为被终止的轨迹可以简单记成失败。**必须单独标记 `terminated_by_loop_detector`**，否则你改变了在测量的东西却不自知。 |
| longest common subsequence (LCS) | 最长公共子序列 | 两个序列中按序出现的最长公共部分。 | 做「必经动作检查」时用它——只约束必须发生的事，对额外探索宽容。 | 以为轨迹相似度可以当主指标。**参考轨迹不是唯一正确路径**；把编辑距离当主指标等于在训练 agent 模仿人类的低效之处。 |
| failure taxonomy | 失败模式分类学 | 互斥且有优先级的失败七分类：循环 / 工具误用 / 预算耗尽 / 提前放弃 / 幻觉式完成 / 越权副作用 / 真·能力不足。 | **在把失败归因为「模型不够强」之前，先排除前六类**——真实项目里它们常占失败总量一半以上，而换更强的模型解决不了。 | 以为分类可以重叠。重叠会让比例加起来超过 100%，报告没法读；必须自上而下第一个命中即分类。 |
| process reward model (PRM) | 过程奖励模型 | 用步骤级标注训练的、能自动给中间步骤打分的模型。 | 它提供密集、定位准确的反馈，在长链推理任务上显著优于结果监督。 | 以为可以用它替代结果分作主指标。**PRM 自己也需要被评测**，且分布外会失效；过程好但没做完，产品价值是 0。 |
| Goodhart's law (eval side) | 古德哈特定律（评测侧） | 一旦某个指标成为目标，它就不再是一个好的度量。 | 典型案例：优化「平均步数」会让 agent 学会**提前放弃**（失败轨迹更短），指标漂亮而成功率下降。 | 以为只有「拿指标当训练目标」时才发生。**只要指标进了周报、团队开始盯着它，优化压力就已存在**——人也会 Goodhart。 |
| collider bias | 碰撞偏倚 | 对一个受结果影响的中间变量做条件统计所引入的偏倚。 | 它解释了为什么效率指标必须分层：$\mathbb{E}[\text{steps}]$ 受「是否成功」影响，只有 $\mathbb{E}[\text{steps}\mid\text{success}]$ 是无歧义的。 | 以为这是统计学的洁癖。**「平均步数」这个指标不应出现在任何报告里**，该出现的是「成功轨迹的中位步数 + P90」和「提前放弃率」。 |

---

## 五 · 可靠性与统计 · Reliability & Statistics

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| pass@k | — | 试 $k$ 次至少成功一次的概率，无偏估计为 $1-\binom{n-c}{k}/\binom{n}{k}$。 | 适用于**结果被执行前有人或验证器能挑一挑**的场景：代码补全、候选生成、best-of-n。 | 以为它总是比 pass^1 更能代表能力。**它随 $k$ 很快饱和到 1**，报 pass@8 常常只是在报告采样次数。 |
| pass^k | — | 试 $k$ 次全部成功的概率，无偏估计为 $\binom{c}{k}/\binom{n}{k}$。 | 适用于**结果直接执行、没人复核**的场景：自动退款、自动改配置。它同时在测「一致性」——曲线下降越快，行为越不稳定。 | 以为它只是更严格的 pass@k。**两者随 $k$ 的方向相反**：同一个 agent，pass@8 可以是 99%、pass^8 是 6%。 |
| intra-cluster correlation ($\rho$) | 组内相关系数 | 同一任务的多次重复之间的相关程度，$\rho=\sigma_b^2/(\sigma_b^2+\sigma_w^2)$。 | 它决定有效样本量 $n_{\text{eff}}=Nk/(1+(k-1)\rho)$；agent 评测的 $\rho$ 常在 0.4–0.8，**名义样本量要打三折左右看**。 | 以为跑 500×5 就有 2500 个样本。**同一任务的重复不独立**，把它们当独立样本会让区间窄近一半。 |
| clustered bootstrap | 聚类自举 | 重采样「任务」而非 rollout，被抽中的任务连同它的全部重复一起进来。 | **这是 agent 评测里唯一正确的区间算法**；朴素自举的覆盖率会显著低于名义的 95%。 | 以为重采样单位无所谓。口诀：**自举要重采样「最外层的独立单位」**——是任务，不是 rollout，更不是步骤。 |
| paired design / McNemar | 配对设计 / McNemar 检验 | 在同一批任务上同时比较两个 agent；二值结果下只有「一个对一个错」的不一致对携带信息。 | 任务间方差是最大的方差源，配对设计**直接把它消掉**，样本量常能省一半以上。 | 以为「都跑同一个基准」就算配对。**必须同一次运行或共享完全相同的环境快照**——今天跑 A、下周跑 B 引入的是更大的时间混杂。 |
| minimum detectable effect (MDE) | 最小可检测差异 | 在给定 $N$、$\alpha$、power 下能被检出的最小差异。 | **「没有观察到显著差异」和「两者相同」不是一回事**；报告必须给出检测下限，否则「不显著」没有信息量。 | 以为不显著就可以写「两者差不多」。正确写法是「本次评测能以 80% 功效检出 ≥8 个点的差异，实测 3 个点」。 |
| winner's curse | 胜者诅咒 | 从多个带噪声的估计里取最大值，这个最大值系统性高于真实最优。 | 20 个能力相同的模型、$\sigma=2$ 个点时，榜首期望虚高约 5 个点，且复现时几乎必然易主——**不需要任何人作弊**。 | 以为榜首掉分是「过拟合榜单」。**取最大值这个操作本身就是有偏的**；读榜单前先看误差棒和任务数。 |
| optimal allocation | 最优分配 | 预算约束下的最优重复次数 $k^*=\sqrt{(\sigma_w^2/\sigma_b^2)(c_{\text{task}}/c_{\text{run}})}$。 | 它把「该扩任务集还是该多跑几次」从直觉变成一个可算的数：**任务越贵、任务内噪声越大，就越该多跑几次**。 | 以为「多跑几次总是更稳」。**加重复的收益有天花板**（标准差最多压到 $\sqrt{\rho}$ 倍），加任务数没有。 |

---

## 六 · 成本与可复现性 · Cost & Reproducibility

| 术语 (EN) | 中文 | 一句话定义 | 为什么重要 | ⚠️ 常见误解 |
|---|---|---|---|---|
| cost-accuracy frontier | 成本-精度前沿 | 在 (成本, 成功率) 平面上不被任何其他配置支配的那些配置。 | **「谁更强」在不固定预算时没有定义**——任何 agent 的成功率都能靠多花钱提高；正确提法是「同预算谁更准」或「同精度谁更便宜」。 | 以为前沿上有一个「最好的点」。**选哪个取决于你的预算线落在哪里**，且两个 agent 的曲线可以相交。 |
| dominated configuration | 被支配配置 | 存在另一个配置同时更便宜且更准。 | 它们在任何预算下都不该被选；**在真实评测里非常常见**，通常意味着某个 scaffold 没调好。 | 以为被支配的配置至少还能当参照。它连参照价值都有限——**更值得报告的是最简 baseline scaffold 的分数**。 |
| $/success vs $/task | 每次成功成本 vs 每任务成本 | 前者是总成本除以成功次数，后者是总成本除以任务数。 | **只有前者可比**：后者奖励「早点放弃」，因为失败的轨迹更短更便宜。 | 以为两者只差一个常数因子。成功率不同的两个 agent，两个口径可以给出**相反的结论**。 |
| best-of-n | — | 采样 $n$ 次、用验证器挑最好的一个。 | 它是成本-精度曲线上最容易被误用的一段：**没有验证器时，$n$ 次采样的实际价值接近 $n=1$**。 | 以为 $n$ 越大越好。**验证器有假阳率时，$n$ 越大，交付出去的「成功」里假阳解占比越高**——这是 reward hacking 的评测侧同构现象。 |
| run fingerprint | 运行指纹 | 把十项复现要素（镜像 digest、数据集哈希、scaffold commit、模型 ID、采样参数、预算参数、并发、网络策略、判分器版本、聚合方式）序列化后的哈希。 | 它让**「不可比较」变成机器可判定的**：CI 门禁里直接是一行 `assert current.fingerprint == baseline.fingerprint`。 | 以为记录配置就够了。**同指纹却分数差很多，本身就是一个必须调查的告警**——说明还有没被记录的变量在动。 |
| record/replay | 录制回放 | 把 HTTP 请求与响应录下来，之后的运行从录制里回放。 | 对必须联网的评测，这是唯一可行的可复现方案。 | 以为录一次就一劳永逸。**录制会过期**；正确用法是双轨：回放用于回归门禁，定期真实联网小样本校验录制没失真。 |
| eval card | 评测卡 | 一份完整报告的最小集合：被测对象、任务集、结果、成本、复现指纹。 | 它让读者在不重跑实验的情况下判断这个数字能不能用。 | 以为可以按需裁剪。**最先被删的三行恰恰最不能删**：scorer 的 α/β、MDE、fingerprint——它们的共同点是「限制你能得出的结论」。 |
| expected utility threshold | 期望效用门槛 | $p\cdot V_{\text{success}}-(1-p)\cdot C_{\text{fail}}-C_{\text{run}}$ 超过现状即可上线。 | 它把成功率翻译成决策：**失败代价高时，提高成功率的边际价值会低于「加一个人工确认点」**。 | 以为上线门槛就是一个成功率阈值。**同一个成功率在草稿建议场景够用、在不可逆操作场景完全不够**——门槛由 $C_{\text{fail}}$ 决定。 |
"""

REFERENCES = r"""
# 参考清单 · References（Agent 评测与基准）

> ★ 标必读。每条注明「解决什么问题」——这份清单不是让你把论文读一遍，
> 而是让你在被追问「这个做法有没有依据」时，知道**这不是我编的，有原始出处**，
> 需要时能自己去查原文补深度。本课把这些材料重新组织成了「七个决策点」的骨架。

---

## 一 · 代码类 agentic 基准 · Code Agents

- ★ **Carlos E. Jimenez, John Yang, et al., _SWE-bench: Can Language Models Resolve Real-World
  GitHub Issues?_（ICLR 2024）** —
  解决「怎么把真实软件工程任务变成一个判分完全确定性的基准」。
  从已合并 PR 反向构造任务、把 issue 文本与补丁+测试分离、用 `FAIL_TO_PASS` 与 `PASS_TO_PASS`
  两组测试判分——**本课模块 01 的任务构造流程与模块 02 的防回归判分设计全部承袭这篇**。
- ★ **OpenAI, _Introducing SWE-bench Verified_（2024）** —
  解决「一个被广泛引用的基准里到底有多少坏题」。由专业开发者逐条审核 SWE-bench，
  剔除「issue 描述不足以复现」「隐藏测试检查了描述里没提的行为」等任务，得到 500 条可解子集。
  **本课反复引用的一条结论——「坏题是常态而不是意外」——直接来自这份工作。**
- **John Yang et al., _SWE-bench Multimodal_ 与 SWE-bench 家族的多语言/持续更新变体** —
  解决「Python 上的成绩里有多少来自对生态的记忆」以及「怎么用滚动更新对抗污染」。
  代价是每次滚动后分数不可与历史直接比较，这个取舍在模块 01 第 6 节展开。
- **围绕 SWE-bench 的后续质量分析工作（解法泄漏、测试强度不足、任务可解性）** —
  解决「为什么同一个模型在 full 与 Verified 上分数差这么多」。
  这类分析是模块 02「变异测试量化判分强度」一节的动机来源；
  **自建任务集时把 issue 评论区、后续 commit message、PR 描述全部剥离，是从这里得到的清洗规则。**
- **OpenAI, _SWE-Lancer_（2025）一类把任务标价的基准** —
  解决「怎么把成功率折算成经济价值」。它是模块 05 成本视角的一个极端版本：
  不问「做对了几道」，问「赚到了多少钱」。

## 二 · 工具与对话型 agent 基准 · Tool-use & Conversational Agents

- ★ **Shunyu Yao, Noah Shinn, Pedram Razavi, Karthik Narasimhan, _τ-bench: A Benchmark for
  Tool-Agent-User Interaction in Real-World Domains_（2024）** —
  解决三件事：**① 怎么给没有测试可跑的任务判分**（对比数据库终态与标注的目标状态）、
  **② 怎么模拟一个信息挤牙膏式给出的真实用户**（用另一个 LLM 扮演用户）、
  **③ 怎么衡量可靠性而非峰值能力**（引入 pass^k）。
  **本课模块 01 第 3 节与模块 04 第 2 节的核心内容都来自这篇**；
  它留给整个领域最重要的遗产是 pass^k 这个指标。
- **τ²-bench 一类的双向控制扩展** —
  解决「用户不只是提供信息，还要被 agent 指挥去操作环境」这一更真实的设定。
  它引入了新的判分维度：说得对但用户听不懂照做不了，同样是失败。

## 三 · 网页、GUI 与开放网络 · Web / GUI / Open Web

- ★ **Shuyan Zhou et al., _WebArena: A Realistic Web Environment for Building Autonomous Agents_
  （ICLR 2024）** —
  解决「怎么在保住交互性的同时让网页 agent 评测可复现」：**自建可复现的网站集群**
  （购物、论坛、GitLab、CMS、地图全部本地部署），每个任务配一个程序化 validator。
  **本课模块 01 第 4 节的「离线 / 自托管 / 在线」三种取舍，以及「不可能任务」这一被低估的设计，
  都出自这篇。**
- **Jing Yu Koh et al., _VisualWebArena_（2024）** —
  解决「网页任务里需要视觉理解的那一半」，判分方式不变，任务需要 VLM 能力（呼应 C00）。
- ★ **Tianbao Xie et al., _OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real
  Computer Environments_（NeurIPS 2024）** —
  解决「怎么在真实操作系统 + 真实应用上做可判分的任务」：每个任务一段执行式校验脚本。
  跨应用任务（在 A 里查到的填进 B）是这个基准的难点所在。
- **Xiang Deng et al., _Mind2Web_（NeurIPS 2023）** —
  解决「用离线录制的真实网页轨迹做完全可复现的评测」。
  代价是**无法评测「走错了能不能回来」**这一最关键的 agent 能力，
  这一点是模块 03「恢复率」一节的反面动机。
- **Grégoire Mialon et al., _GAIA: A Benchmark for General AI Assistants_（2023）** —
  解决「开放式任务怎么客观判分」：**从判分倒推题目设计**——只出答案唯一、简短、可精确匹配的问题，
  但通往答案的路径需要多步搜索、读文件、看图。
  **「先问我怎么自动判对错，再据此设计题目形态」这条方法论可以直接拿去自建任务集。**
- **OpenAI, _BrowseComp_（2025）一类「难找但易验证」的基准** —
  解决「怎么专门测长程搜索的耐心而不是知识量」：叠加多个稀有约束，使答案在网上只有一处能拼出来。

## 四 · 科研与长程任务 · Research & Long-Horizon

- **Jun Shern Chan et al., _MLE-bench: Evaluating Machine Learning Agents on Machine Learning
  Engineering_（2024）** —
  解决「机器学习任务没有对错、只有分数高低时怎么判分」：**拿真实竞赛排行榜当标尺**，
  折算成奖牌等级；不同任务的分数尺度用「相对人类分布的百分位」统一。
- **METR 关于 agent 任务时间跨度（time horizon）的系列工作** —
  解决「怎么把不同难度的任务统一到一根有物理意义的轴上」：
  不问成功率，问「这个 agent 能以 50% 成功率完成的任务，人类专家要花多久」。
  好处是可跨基准比较，坏处是需要为每个任务标注可靠的人类耗时。

## 五 · 评测方法论与统计 · Methodology & Statistics

- ★ **Sayash Kapoor, Benedikt Stroebl, et al., _AI Agents That Matter_（2024）** —
  解决「为什么 agent 排行榜的数字不可靠」。三条核心论点与本课模块 05 完全一致：
  **① 不报成本的准确率是无意义的**（准确率可以靠多花钱买）、
  **② 应当报告成本-精度的帕累托前沿而非单点**、
  **③ agent 评测普遍缺乏可复现性与标准化 harness**。
  **如果这份清单只读一篇，读这篇。**
- ★ **Mark Chen et al., _Evaluating Large Language Models Trained on Code_（2021）** —
  解决「怎么用 $n$ 次采样无偏地估计 pass@k」：$1-\binom{n-c}{k}/\binom{n}{k}$。
  **本课模块 04 的两个无偏估计器都源自这篇的思路**（pass^k 是同一思路的对偶形式）。
- ★ **Evan Miller, _Adding Error Bars to Evals_（2024）** —
  解决「评测报告该怎么算和报误差」：中心极限定理、方差削减、配对设计、聚类结构。
  **本课模块 04 第 4 节「把 $Nk$ 条 rollout 当独立样本是错的」直接对应这篇的聚类讨论。**
- **Bradley Efron & Robert Tibshirani, _An Introduction to the Bootstrap_（Chapman & Hall, 1993）** —
  解决「不做分布假设怎么算置信区间」，以及**分组数据该怎么重采样**。
  记住一句话即可：自举要重采样最外层的独立单位。
- **Rogan & Gladen, _Estimating Prevalence from the Results of a Screening Test_
  （American Journal of Epidemiology, 1978）** —
  解决「检测手段本身不完美时，怎么从观测阳性率反推真实患病率」。
  **本课模块 02 把它整个搬到了判分器上**：$\hat p_{\text{corrected}}=(\hat p_{\text{obs}}-\alpha)/(1-\beta-\alpha)$。
  校正结果可能落到 $[0,1]$ 之外，这一点在原文里也有讨论——那是信号不是 bug。
- **Quinn McNemar（1947）与两比例检验的功效分析标准教材** —
  解决「配对二值数据怎么做显著性检验」以及「要多少样本才够」。
  本课模块 04 第 3、5 节的样本量公式全部来自这套标准结果。

## 六 · 过程监督与轨迹 · Process Supervision & Trajectories

- ★ **Hunter Lightman et al., _Let's Verify Step by Step_（2023）** —
  解决「过程监督与结果监督哪个更好」：在需要长链推理且中间步骤可验证的任务上，
  **过程监督显著优于结果监督**——因为结果监督会把「过程全错但答案蒙对」的样本当作正例。
  本课模块 03 第 5 节把这个结论翻译成 agent 评测的三条实践规则。
- **Jonathan Uesato et al., _Solving Math Word Problems with Process- and Outcome-based Feedback_
  （2022）** — 同一问题的更早期系统研究，给出了两种反馈方式在最终答案正确率与推理正确率上的分解。
- **Shunyu Yao et al., _ReAct: Synergizing Reasoning and Acting in Language Models_（ICLR 2023）** —
  解决「agent 的轨迹该长什么样」：thought / action / observation 三段式。
  本课模块 03 的日志 schema 是这个结构的工程化版本。
- **OpenTelemetry _Semantic Conventions for Generative AI_（`gen_ai.*` span 属性）** —
  解决「轨迹字段名该怎么起」。沿用标准字段名的理由不是它更优雅，
  而是**现成的 trace 查看器（Jaeger / Tempo / Phoenix 等）可以直接用**——这个理由已经足够。
- **Yuri Papadakis et al., _Mutation Testing Advances: An Analysis and Survey_
  （Advances in Computers, 2019）** —
  解决「怎么量化一组测试的强度」。本课模块 02 用它来回答「这个判分器可不可信」，
  工具层面对应 `mutmut` / `cosmic-ray`。

## 七 · 报告规范与工具 · Reporting & Tooling

- **Margaret Mitchell et al., _Model Cards for Model Reporting_（FAT* 2019）** —
  解决「一份模型报告的最小集合是什么」。本课模块 05 的**评测卡（eval card）**是这个思想在
  agent 评测上的具体化：让读者在不重跑实验的情况下判断这个数字能不能用。
- **UK AI Safety Institute, `inspect_ai` 框架文档** —
  解决「怎么把 eval 写成声明式的 task / solver / scorer 三件套」，
  以及 `--epochs`、`sandbox="docker"` 这些直接对应本课统计与可复现性要求的参数。
  **C68 会把这套框架的设计思想整个展开。**
- **SWE-bench 官方评测 harness（容器化、逐条起容器跑测试）** —
  解决「怎么把判分做成可复现的流水线」。
  值得注意的实现细节：`--max_workers` 会影响超时行为，**因此并发度是 harness 的一部分**，
  必须写进报告——这是本课模块 05 复现清单第 7 条的出处。
- **`vcrpy`（HTTP 录制回放）** —
  解决「必须联网的评测怎么做到可复现」。注意 `filter_headers` 一定要过滤掉密钥，
  否则录制文件里会留下凭证。
"""

if __name__ == "__main__":
    ok = build()
    print("\n构建完成。" if ok else "\n⚠️ 有产物未达标，请检查上面的 ⚠️ 标记。")
