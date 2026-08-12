# -*- coding: utf-8 -*-
"""C48 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python、命令行、HTTP 基本概念；读过 C24（推理服务）与 C37（MLOps）更好但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯标准库/numpy 模拟控制平面 + SLO/容量/成本三笔账"),
    ("预计时长", "总览 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么", "".join([
        P("欢迎来到 <strong>LLM 生产部署与云原生</strong>。这门课只追求一件事：<strong>把一个「在我机器上能跑」的模型，变成一个「在别人流量下活着」的服务</strong>。"),
        P("如果你读过 C24（高效推理服务），你已经知道推理引擎<em>内部</em>的机制——PagedAttention 怎么管 KV 缓存、continuous batching 怎么把 GPU 喂满、投机解码怎么省步数。那门课回答的是「<em>单个引擎怎么跑得快</em>」。如果你读过 C37（MLOps），你知道了实验追踪、数据版本、评测门禁、漂移监控——「<em>模型的生命周期怎么管</em>」。本课接在这两者中间那个被跳过的缺口上问：<strong>这个跑得快的引擎，怎么被打包、被调度、被发布、被扩缩、被计费，才能承载真实流量而不半夜把你叫醒</strong>？"),
        P("这个缺口非常具体。你有一个 vLLM 进程，它在你的开发机上 8000 端口跑得好好的。现在要回答：它的依赖怎么固化（<span class=\"term\">Docker</span>）？它对外长什么样（<span class=\"term\">serving API</span>）？它在一百台机器上怎么被拉起来、挂了谁重启它（<span class=\"term\">Kubernetes</span>）？新版本怎么上线而不是一刀切（<span class=\"term\">canary</span>）？流量涨十倍怎么办（<span class=\"term\">autoscaling</span>）？这一切一个月烧多少钱（<span class=\"term\">cost model</span>）？——这五个问题，就是本课的五个模块。"),
        DUAL(
            "换个说法：C24 教你造发动机，本课教你把发动机装进车、上牌、加油、开上路、还得算清油钱。发动机再好，没有底盘、油路和仪表盘，它就只是台在实验室里轰鸣的机器。工业界绝大多数「模型很好但上不了线」的故事，卡的都不是模型，是这层。",
            "严格地说，本课覆盖的是 <span class=\"term\">serving stack</span> 中<strong>推理引擎之上、业务逻辑之下</strong>的那一层：容器运行时（OCI image + runtime contract）、服务契约（HTTP/gRPC + 流式协议）、编排与调度（K8s control plane、scheduler、autoscaler）、渐进交付（progressive delivery）与成本工程（capacity planning、spot economics）。这一层的知识不随模型架构更迭而过期。",
        ),
        CALLOUT("intuition", "学完你应当能回答这类问题（也是 LLM 平台/推理基础设施岗的高频面试题）：<strong>为什么模型权重通常不打进镜像？readiness 探针配错了会怎样，为什么 LLM 服务特别容易踩这个坑？一个 8×H100 的节点上应该跑几个副本，装箱率怎么算？金丝雀放 5% 流量、跑多久才有统计效力？HPA 按 GPU 利用率扩缩为什么会震荡，该按什么指标？spot 实例便宜 70%，什么情况下反而更贵？</strong>——并且能在纯 Python 里把镜像层缓存、请求路由、装箱调度、滚动更新、HPA 控制律、成本模型都从零模拟一遍、用 assert 验证。"),
        P("一句方法论的话先说在前面：本课的价值不在「我们没有 K8s 集群也能学」这个妥协，而在它<strong>逼你只关注真正难的部分</strong>——控制平面的逻辑、容量与风险的数学。具体用哪家云、哪个 Ingress 控制器、YAML 里哪个字段叫什么，这些是会变的、可查文档的；而「声明式控制循环为什么收敛」「滚动更新期间容量为什么会塌」「金丝雀要多少样本才能判断」「spot 中断率多高时期望成本反超按需」是<em>不随工具过时</em>的硬功夫。"),
    ])),
    ("ledger", "世界观：三笔账与「生产的不对称性」", "".join([
        P("贯穿全课的世界观可以浓缩成一句话：<strong>生产环境里，决定成败的不是「能不能做到」，而是「SLO 守不守得住、容量够不够、钱烧不烧得起」</strong>。所以本课给每个机制都配三笔账："),
        TABLE(["这笔账", "回答什么", "怎么算", "本课例子"], [
            ["<strong>SLO 账</strong> reliability", "用户感知的可用性与延迟达标吗", "可用率、P50/P95/P99 延迟、错误预算消耗速率", "滚动更新期间 P99 会不会破线"],
            ["<strong>容量账</strong> capacity", "这些副本扛得住多少 QPS", "排队论：到达率 λ、服务率 μ、并发 c、利用率 ρ", "8 副本在 ρ=0.8 时的 P95 排队时延"],
            ["<strong>成本账</strong> cost", "每百万 token 花多少钱", "实例单价 × 时长 ÷ 有效 token 吞吐", "spot vs 按需的期望成本交叉点"],
        ]),
        CALLOUT("danger", "<p>最反直觉、也最重要的一条：<strong>生产系统的失效是不对称的</strong>。做对一百次没人注意，做错一次全网皆知。这条不对称性决定了本课所有设计决策的方向——<em>宁可牺牲一点效率，也要把爆炸半径切小</em>。金丝雀发布比全量发布慢、成本高，但它把「新版本有 bug」的损失从 100% 流量切到 5%；多副本比单副本贵，但它把「一台机器挂了」的损失从「服务全挂」切到「容量少 1/N」。<strong>你在本课学的几乎每一个机制，本质都是在用确定的成本，买不确定的风险的下界。</strong></p>", "生产的不对称性"),
        P("这条不对称性还有个推论，是新手最容易违背的：<strong>可观测性不是上线后的补充，而是上线的前置条件</strong>。一个没有指标、没有探针、没有结构化日志的服务，出问题时你唯一的手段是重启和猜。本课在模块 02（服务契约里就要暴露健康与指标）和模块 03（探针如何驱动流量摘除）里会反复回到这一点。"),
        P("把这三笔账养成习惯，是做任何生产部署的<strong>第一步且最容易被跳过的一步</strong>。新手最常犯的错是先把服务跑起来、压测一把、看着 QPS 数字满意地上线——结果撞上滚动更新时的容量塌陷、撞上 readiness 配错导致的流量打到未加载完的 Pod、撞上月底账单里 70% 是闲置 GPU。<em>先算账、再动手</em>：SLO 定不下来就别谈优化，容量算不清就别谈扩缩，成本模型没有就别谈选型。"),
    ])),
    ("map", "课程地图：从一个进程到一片集群的五道关", "".join([
        H3("课程地图：五道关，一条流量路径"),
        ASCII("""起点：你的开发机上，一个 vLLM 进程在 :8000 监听，`curl` 能通。

  模块 01  容器化              Dockerfile / 分层缓存 / 多阶段 / 运行时契约
     │                        「依赖固化成一个可复现、可分发、启动快的镜像」
     ▼
  模块 02  推理服务 API        OpenAI 兼容协议 / SSE 流式 / 批处理 / 限流 / 队列论
     │                        「对外的契约定死；用排队论算清一个副本扛多少 QPS」
     ▼
  模块 03  Kubernetes 编排     声明式 + reconcile / Pod-Deployment-Service / 探针 / 调度
     │                        「一百个副本谁来拉起、谁来重启、流量怎么只打给健康的」
     ▼
  模块 04  发布与自动扩缩      滚动/蓝绿/金丝雀 / 序贯检验 / HPA 控制律 / 回滚
     │                        「新版本怎么小步放量；流量涨了怎么自动加副本还不震荡」
     ▼
  模块 05  云平台·调度·成本    对象存储 / spot 经济学 / K8s Job vs Slurm vs Ray / $ per 1M token
                              「跑在谁家的机器上、离线作业怎么排队、一个月多少钱」

终点：一个有 SLO、有容量模型、有成本账、能自愈能灰度的 LLM 服务。"""),
        P("这五关有一条明确的依赖链：<strong>没有可复现的镜像（01），编排（03）就无从谈起；没有定死的服务契约与容量模型（02），发布与扩缩（04）就没有判据；没有成本模型（05），前面所有的「多副本、多区域、多环境」都会在账单面前被砍掉</strong>。所以建议按顺序学。"),
        TABLE(["模块", "核心机制", "notebook 里从零做什么", "对应真实世界"], [
            ["01 容器化", "分层文件系统、层缓存、多阶段构建", "Dockerfile 解析器 + 层缓存命中模拟 + 冷启动账", "Docker / BuildKit / OCI image"],
            ["02 服务 API", "OpenAI 兼容契约、SSE、限流、排队论", "请求校验器 + SSE 编解码 + 令牌桶 + M/M/c", "vLLM OpenAI server / FastAPI / Envoy"],
            ["03 编排", "reconcile 循环、探针状态机、装箱调度", "控制器循环 + 探针 FSM + first/best-fit 调度器", "Kubernetes control plane / kube-scheduler"],
            ["04 发布扩缩", "滚动容量曲线、序贯检验、控制律", "滚动更新仿真 + 金丝雀检验 + HPA 震荡实验", "Argo Rollouts / Flagger / HPA / KEDA"],
            ["05 云与成本", "spot 期望成本、作业排队、单位经济", "中断成本模型 + backfill 调度器 + $/1M token", "AWS/GCP / Slurm / Ray / FinOps"],
        ]),
        CALLOUT("warn", "本课<strong>刻意不教 YAML 字段</strong>。字段名会变（`extensions/v1beta1` 早就没了），而「Deployment 是一个把期望副本数变成现实的控制器」这个概念不会变。所有 YAML 只作为对照展示出现在讲解里，不参与 notebook 运行。你要带走的是<em>控制平面的心智模型</em>，不是背下来的字段表——后者查文档三分钟，前者要练。"),
    ])),
    ("method", "方法论：用纯 Python 模拟控制平面", "".join([
        P("本环境没有 Kubernetes 集群、没有 GPU、不联网。这看起来是个巨大的妥协，但对本课而言恰恰是个好约束——因为<strong>云原生这一层的困难，几乎全部是「逻辑与数学」的困难，而不是「跑得动」的困难</strong>。"),
        DUAL(
            "K8s 的调度器本质上就是个装箱算法；Deployment 控制器本质上就是个「比较期望和现实、发出差量动作」的循环；HPA 本质上是个带死区的比例控制器；金丝雀判据本质上是个假设检验。这些东西你都可以用几十行 Python 写出来、用 assert 验证它的性质——而且写出来之后，你对真实 K8s 的理解会比读一百页文档更深。",
            "形式化地说，我们把控制平面建模为一个离散时间系统：状态 <code>s_t</code>（Pod 集合、副本数、就绪标记）、期望 <code>d</code>（spec）、控制器 <code>f</code>，演化为 <code>s_{t+1} = f(s_t, d, 外部事件)</code>。「收敛」= 在无外部扰动下 <code>s_t → d</code>；「震荡」= 存在极限环。本课的 notebook 就是把 <code>f</code> 写出来、跑这个迭代、并对 <em>收敛性、单调性、爆炸半径</em> 下 assert。",
        ),
        P("具体到每个模块，我们的三条纪律是："),
        UL([
            "<strong>对拍（differential testing）</strong>：每个「聪明」的实现都要和一个朴素参考对齐。best-fit 调度器要和暴力枚举的最优装箱对比装箱率；SSE 编码器要和解码器 round-trip 一致；限流器要和「按定义逐秒统计」的参考一致。",
            "<strong>算账（accounting）</strong>：每个机制都要产出一个数字。镜像层缓存命中率 → 构建时间；副本数与 ρ → P95 排队时延；spot 中断率 → 期望小时成本。数字对了，直觉才靠得住。",
            "<strong>下界思维（blast radius）</strong>：每个设计都要回答「最坏情况下有多少用户受影响、多久恢复」。这是本课独有的第三条纪律，也是生产工程与实验工程最本质的区别。",
        ]),
        CALLOUT("intuition", "一个提醒：<strong>模拟不等于真实，但模拟能让你在真实环境里问对问题</strong>。你在 notebook 里让 HPA 震荡起来之后，第一次看真实集群的扩缩曲线就会立刻认出「这是采样周期和冷却期没配好」；你算过装箱率之后，看到节点 GPU 利用率 62% 就会立刻想到碎片而不是「模型不够快」。这就是本课想给你的东西。"),
    ])),
    ("env", "环境与运行", "".join([
        P("本课全程 <strong>纯标准库 + numpy、CPU 可跑</strong>，不需要 Docker、不需要 Kubernetes、不需要云账号、不需要联网。所有 notebook 在 CPU 上实跑验证、assert 0 失败。"),
        CODE("""# 建议在课程统一环境里跑
pip install -r requirements.txt      # numpy / pandas / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        P("讲解里出现的 <code>Dockerfile</code>、<code>deployment.yaml</code>、<code>sbatch</code> 脚本等<strong>真实配置片段仅作对照展示</strong>，不参与运行——但它们全部是可以原样贴进真实环境使用的正确写法，建议你在有条件时逐个试一遍。每个模块末尾的「🔧 旁注」会明确指出：你在 numpy 里验证过的逻辑，对应真实系统里的哪个组件、哪个参数。"),
        TABLE(["你需要", "本课怎么处理"], [
            ["Docker 引擎", "用 Dockerfile 解析器 + 层缓存模拟器复现构建语义；真实 Dockerfile 作对照"],
            ["Kubernetes 集群", "用 Python 写 reconcile 循环、探针状态机、调度器；真实 YAML 作对照"],
            ["GPU / 多节点", "用资源向量与装箱模型表示；所有账目以公开的 H100/A100 规格与云价目为准"],
            ["云账号", "用参数化成本模型；单价可在 notebook 顶部改成你自己的报价"],
            ["压测流量", "用泊松到达过程生成合成流量，配合 M/M/c 解析解对拍"],
        ]),
        P("最后一句关于心态的话：这门课里没有任何一个概念是「高深」的。容器是分层文件系统加命名空间，K8s 是一堆控制循环，金丝雀是个假设检验，HPA 是个比例控制器。<strong>它们之所以让人望而生畏，是因为工具的表面复杂度（YAML、CRD、云控制台）遮住了底下极其简单的核心</strong>。本课的全部目的，就是把那些表面剥掉，让你直接摸到核心——摸到之后你会发现，剩下的都是查文档的事。"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与方法论热身

本课全程 **纯标准库 / numpy、CPU 可跑**，用 **Python 模拟控制平面** 复现云原生部署的机制，再用 **SLO 账 + 容量账 + 成本账** 把生产问题量化。

这个 notebook 做四件事：① 确认环境；② 用一个最小例子体会 **声明式控制循环（reconcile）**——K8s 的心脏；③ 立下三条纪律：**对拍 / 算账 / 下界思维**；④ 用错误预算把「99.9% 可用」翻译成人能理解的分钟数。"""),
    md("""## 1 · 环境自检

只需要 `numpy`；`math`/`random`/`dataclasses`/`collections` 都是标准库。`pandas` 可选。"""),
    code("""import sys, platform, math, random, collections
from dataclasses import dataclass, field
print('Python', sys.version.split()[0], '|', platform.system())
import numpy as np; print('numpy', np.__version__)
try:
    import pandas as pd; print('pandas', pd.__version__, '(可选)')
except Exception:
    print('pandas 未安装（可选，不影响课程）')
print('环境就绪 ✅  —— 本课不需要 Docker / Kubernetes / GPU / 联网')"""),
    md("""## 2 · 声明式控制循环：Kubernetes 的心脏

K8s 里几乎每个组件都是同一个模式：**看一眼期望状态（spec）、看一眼当前状态（status）、发出让二者靠拢的动作**。这个循环叫 **reconcile（调谐）**。

它和「命令式」的区别是本质性的：命令式说「启动 3 个进程」（说完就完了，挂了没人管）；声明式说「我要 3 个副本」（控制器**持续**保证这件事成立）。

下面用 30 行写一个最小的 Deployment 控制器，然后验证它的两个关键性质：**收敛** 与 **自愈**。"""),
    code("""def reconcile(current, desired):
    '''最小控制器：返回本轮要执行的动作列表。
       current: 当前存活的副本 id 集合；desired: 期望副本数。'''
    actions = []
    n = len(current)
    if n < desired:
        for _ in range(desired - n):
            actions.append(('create', None))
    elif n > desired:
        # 缩容时删除 id 最大的（真实 K8s 有更复杂的删除代价排序）
        for pod in sorted(current)[desired:]:
            actions.append(('delete', pod))
    return actions

def apply(current, actions, next_id):
    for kind, pod in actions:
        if kind == 'create':
            current.add(next_id); next_id += 1
        else:
            current.discard(pod)
    return current, next_id

# 从 0 个副本开始，期望 3 个
current, next_id, DESIRED = set(), 0, 3
history = []
for tick in range(5):
    acts = reconcile(current, DESIRED)
    current, next_id = apply(current, acts, next_id)
    history.append(len(current))
print('副本数演化:', history)
assert history[-1] == DESIRED, '控制器必须收敛到期望副本数'
assert history == sorted(history), '从 0 起步应单调增长到目标，不该过冲'
print('✅ 收敛性：控制器把 0 个副本调谐到', DESIRED, '个')"""),
    md("""**自愈**才是声明式的真正威力：外部事件（节点宕机）把副本干掉后，控制器**不需要任何人下命令**就会补上。

下面模拟「随机杀 Pod」的混沌实验，验证系统始终回到期望状态。"""),
    code("""rng = random.Random(0)
current, next_id = {0, 1, 2}, 3
recovered_ticks = []
for tick in range(30):
    # 外部扰动：10% 概率随机杀掉一个副本（模拟节点宕机 / OOMKilled）
    if current and rng.random() < 0.3:
        victim = rng.choice(sorted(current)); current.discard(victim)
    # 控制器调谐
    current, next_id = apply(current, reconcile(current, DESIRED), next_id)
    recovered_ticks.append(len(current))

assert all(n == DESIRED for n in recovered_ticks), '每轮结束时都应已恢复到期望副本数'
print(f'30 轮混沌注入后，每轮末副本数恒为 {DESIRED} ✅')
print('这就是自愈：没有人下过一条「重启」命令，是控制循环在持续拉平差距。')"""),
    md("""> **心智模型（贯穿全课）**：K8s 不是「一个能跑容器的系统」，而是**一组持续把现实拽向期望的控制循环**。
> Deployment 控制器管副本数、Service 控制器管端点列表、HPA 管副本数的期望值本身、调度器管 Pod 落到哪个节点。
> 你在模块 03/04 会把这些循环一个个写出来。"""),
    md("""## 3 · SLO 账：把「99.9% 可用」翻译成分钟

生产的第一笔账。可用性目标（SLO）听起来抽象，但它等价于一个非常具体的数字：**这个月你允许坏多少分钟**。这叫 **错误预算（error budget）**。"""),
    code("""def error_budget_minutes(slo, window_days=30):
    '''给定可用性 SLO（如 0.999），返回窗口内允许的不可用分钟数。'''
    return (1 - slo) * window_days * 24 * 60

for slo in [0.99, 0.995, 0.999, 0.9999]:
    m = error_budget_minutes(slo)
    print(f'SLO {slo*100:>7.2f}%  -> 每 30 天允许不可用 {m:>8.1f} 分钟 ({m/60:.2f} 小时)')

assert abs(error_budget_minutes(0.999) - 43.2) < 0.1
# 关键直觉：每多一个 9，预算缩小 10 倍
assert error_budget_minutes(0.99) / error_budget_minutes(0.999) == 10
print('\\n✅ 每多一个 9，错误预算缩小 10 倍——这就是为什么 SLO 是成本决策而不是技术决策。')"""),
    md("""**错误预算的用法**（Google SRE 的核心实践）：它是**发布速度与稳定性之间的仲裁者**。

- 预算还剩很多 → 可以激进发布、多做实验；
- 预算烧完了 → 冻结发布，先修稳定性。

下面把「一次糟糕的发布」翻译成预算消耗，你会发现 **43 分钟其实非常短**。"""),
    code("""BUDGET = error_budget_minutes(0.999)      # 43.2 分钟/月

incidents = [
    ('一次全量发布引入 bug，5 分钟发现 + 10 分钟回滚', 15, 1.0),   # (描述, 分钟, 受影响流量比例)
    ('金丝雀发布同样的 bug，5% 流量，30 分钟才发现',    30, 0.05),
    ('一个节点宕机，8 副本少 1 个，无用户可见错误',      20, 0.0),
]
print(f'月度错误预算: {BUDGET:.1f} 分钟\\n')
spent = 0.0
for desc, minutes, frac in incidents:
    cost = minutes * frac                  # 按受影响流量折算
    spent += cost
    print(f'  {desc}\\n    -> 消耗 {cost:.2f} 分钟预算 ({cost/BUDGET*100:.1f}%)')
print(f'\\n合计消耗 {spent:.2f} / {BUDGET:.1f} 分钟 = {spent/BUDGET*100:.1f}%')

# 核心对比：同一个 bug，全量发布 vs 金丝雀
assert 15 * 1.0 > 30 * 0.05, '全量发布 15 分钟比金丝雀 30 分钟更伤——爆炸半径压倒 MTTR'
print('\\n✅ 关键结论：同一个 bug，全量 15 分钟(15.0) 比金丝雀 30 分钟(1.5) 贵 10 倍。')
print('   **爆炸半径 × 时长 = 损失**。模块 04 整章都在压这个乘积的第一项。')"""),
    md("""## 4 · 容量账：一个副本能扛多少 QPS？

第二笔账。直觉上「服务能处理 100 QPS 就配 100 QPS 的流量」是**灾难性错误**——排队论告诉你，当利用率 ρ 逼近 1 时，等待时间会**爆炸式**增长。

先用最简单的 M/M/1 感受这条曲线（模块 02 会做完整的 M/M/c）。"""),
    code("""def mm1_wait(lam, mu):
    '''M/M/1 平均排队等待时间（不含服务时间）。lam 到达率, mu 服务率。'''
    rho = lam / mu
    if rho >= 1:
        return float('inf')
    return rho / (mu - lam)

MU = 10.0        # 单副本每秒能处理 10 个请求
print(f"{'利用率 ρ':>10s} {'到达率 λ':>10s} {'平均等待(ms)':>14s}")
for rho in [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]:
    lam = rho * MU
    print(f'{rho:>10.2f} {lam:>10.1f} {mm1_wait(lam, MU)*1000:>14.1f}')

w80, w95 = mm1_wait(0.80*MU, MU), mm1_wait(0.95*MU, MU)
assert w95 > 3 * w80, 'ρ 从 0.80 到 0.95，等待时间应急剧恶化'
print(f'\\n✅ ρ: 0.80 -> 0.95（多榨 19% 吞吐），等待时间涨 {w95/w80:.1f} 倍。')
print('   这就是为什么生产容量规划的目标利用率通常是 0.6~0.8，而不是 0.95。')"""),
    md("""## 5 · 成本账：$ / 1M token

第三笔账，也是最容易被工程师忽略、却最容易被老板问到的一笔。把实例小时价翻译成**单位经济（unit economics）**。"""),
    code("""def cost_per_million_tokens(hourly_usd, tokens_per_sec, utilization=1.0):
    '''把实例小时价换算成每百万输出 token 的成本。'''
    tokens_per_hour = tokens_per_sec * 3600 * utilization
    if tokens_per_hour == 0:
        return float('inf')
    return hourly_usd / (tokens_per_hour / 1e6)

# 公开量级：8×H100 节点按需约 $30~40/h；7B 模型在其上可达数千 tok/s 总吞吐
H100_NODE_HOURLY = 32.0
for tps, util, label in [(4000, 1.00, '满载'),
                         (4000, 0.60, '平均利用率 60%'),
                         (4000, 0.25, '夜间低谷 25%')]:
    c = cost_per_million_tokens(H100_NODE_HOURLY, tps, util)
    print(f'{label:>18s}: ${c:>7.3f} / 1M tokens')

c_full = cost_per_million_tokens(H100_NODE_HOURLY, 4000, 1.0)
c_qtr  = cost_per_million_tokens(H100_NODE_HOURLY, 4000, 0.25)
assert abs(c_qtr / c_full - 4.0) < 1e-9, '利用率降到 1/4，单位成本应涨 4 倍'
print('\\n✅ 单位成本与利用率成反比。**闲置的 GPU 是全额计费的**——')
print('   这一条就解释了模块 04 的自动扩缩和模块 05 的 spot 为什么值得做。')"""),
    md("""## 6 · 立纪律三：下界思维（blast radius）

前两条纪律（对拍、算账）你在 C43/C39 已经见过。本课加第三条，它是生产工程独有的：

> **对每个设计问一句：最坏情况下，多少用户受影响、多久恢复？**

把它封装成一个小工具，后面每个模块都会用它评估方案。"""),
    code("""@dataclass
class Blast:
    name: str
    affected_frac: float     # 受影响流量比例
    detect_min: float        # 平均发现时间
    recover_min: float       # 发现后恢复时间

    @property
    def budget_cost(self):   # 消耗的错误预算分钟数
        return self.affected_frac * (self.detect_min + self.recover_min)

strategies = [
    Blast('全量发布 (recreate)',      1.00, 5, 10),
    Blast('滚动更新 (25% surge)',     0.25, 5, 10),
    Blast('金丝雀 5% + 自动分析',      0.05, 3,  2),
    Blast('影子流量 (不影响用户)',      0.00, 60, 0),
]
print(f"{'策略':<26s} {'受影响':>8s} {'MTTR(min)':>10s} {'预算消耗':>10s}")
for s in strategies:
    print(f'{s.name:<26s} {s.affected_frac:>8.0%} {s.detect_min+s.recover_min:>10.0f} {s.budget_cost:>10.2f}')

costs = [s.budget_cost for s in strategies]
assert costs == sorted(costs, reverse=True), '爆炸半径越小，预算消耗应越低'
assert strategies[-1].budget_cost == 0, '影子流量对用户零影响，即使跑一小时'
print('\\n✅ 影子流量发现慢 20 倍，但预算消耗为 0——**慢而安全 > 快而全量**。')"""),
    md("""## 7 · ✏️ 练习：把三笔账合成一个决策

你现在是这个服务的负责人。给定：SLO=99.9%、单副本 μ=10 QPS、节点 $32/h。

实现 `plan_capacity(peak_qps, mu, target_rho)`：返回 **(副本数, 实际利用率)**。
要求：副本数是**满足目标利用率的最小整数**，即 `n = ceil(peak_qps / (mu * target_rho))`，实际利用率 `= peak_qps / (n * mu)`。"""),
    code("""def plan_capacity(peak_qps, mu, target_rho):
    # TODO: 返回 (n_replicas, actual_rho)
    #   n = ceil(peak_qps / (mu * target_rho))，actual_rho = peak_qps / (n * mu)
    raise NotImplementedError"""),
    code("""# —— 练习自测 ——
n, rho = plan_capacity(100, 10, 0.8)
assert n == 13, f'100 QPS / (10*0.8) = 12.5 -> 向上取整 13，得到 {n}'
assert abs(rho - 100/130) < 1e-9, '实际利用率应为 100/(13*10)'
assert rho <= 0.8 + 1e-9, '实际利用率不应超过目标'

# 目标利用率越低（越保守），需要的副本越多
n_safe, _ = plan_capacity(100, 10, 0.6)
n_greedy, _ = plan_capacity(100, 10, 0.95)
assert n_safe > n_greedy, '更保守的目标利用率需要更多副本'
print(f'peak=100 QPS: ρ*=0.6 需 {n_safe} 副本 | ρ*=0.8 需 {n} 副本 | ρ*=0.95 需 {n_greedy} 副本')
print('✅ 练习通过：容量规划 = 在「延迟风险」与「成本」之间选一个 ρ*')"""),
    md("""---
### 📖 参考答案"""),
    code("""def plan_capacity(peak_qps, mu, target_rho):
    n = math.ceil(peak_qps / (mu * target_rho))
    return n, peak_qps / (n * mu)"""),
    md("""## 8 · 🧪 胶囊：三笔账串成一张决策表

把 SLO / 容量 / 成本三笔账放在一起，你会看到它们如何**互相拉扯**——这正是生产决策的真实形态。"""),
    code("""PEAK_QPS, MU, NODE_HOURLY, REPLICAS_PER_NODE = 100, 10.0, 32.0, 4

print(f"{'目标ρ':>7s} {'副本':>5s} {'节点':>5s} {'月成本$':>10s} {'M/M/1等待ms':>13s}")
rows = []
for target in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
    n = math.ceil(PEAK_QPS / (MU * target))
    nodes = math.ceil(n / REPLICAS_PER_NODE)
    monthly = nodes * NODE_HOURLY * 24 * 30
    rho = PEAK_QPS / (n * MU)
    # 每副本视作独立 M/M/1，到达率均分
    wait_ms = mm1_wait(PEAK_QPS / n, MU) * 1000
    rows.append((target, n, nodes, monthly, wait_ms))
    print(f'{target:>7.2f} {n:>5d} {nodes:>5d} {monthly:>10,.0f} {wait_ms:>13.1f}')

# 成本随目标利用率单调不增；等待时间随目标利用率单调不减
costs = [r[3] for r in rows]; waits = [r[4] for r in rows]
assert costs == sorted(costs, reverse=True), '目标利用率越高，越省钱'
assert waits == sorted(waits), '目标利用率越高，等待越长'
print('\\n✅ 三笔账的张力：省钱(高ρ) 与 低延迟(低ρ) 直接对立。')
print('   没有「最优」，只有「给定 SLO 下的最省」——这就是容量规划的全部内容。')"""),
    md("""✅ 检查全部通过即环境就绪、方法论到位。

**本课的契约**：你写的每个部署机制（镜像层缓存、请求路由、装箱调度、滚动更新、HPA、成本模型）都会
① 与朴素参考**对拍**确认正确，② 用 SLO/容量/成本**算账**量化，③ 用**爆炸半径**评估最坏情况。

**接下来五个模块**：01 容器化 → 02 推理服务 API → 03 Kubernetes 编排 → 04 发布与自动扩缩 → 05 云平台·调度·成本。

下一站：**模块 01 · 容器化** —— 先把「在我机器上能跑」这句话彻底消灭掉。"""),
]
