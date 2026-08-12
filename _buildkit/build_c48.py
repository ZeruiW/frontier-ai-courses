#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C48 · LLM 生产部署与云原生。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import (ROOT, lesson, index, notebook, text_file, install_assets,
                       report, md, code)
import c48_m00, c48_m01, c48_m02, c48_m03, c48_m04, c48_m05

CID = "C48_Cloud_Deployment_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 课程总览与环境",
     "从「模型能跑」到「服务活着」—— 镜像/契约/编排/发布/成本五道关，配 SLO、容量、成本三笔账；用纯 Python 模拟控制平面，不需要 Docker/K8s/GPU/云账号",
     c48_m00),
    ("01_containerization", "01_讲解.html", "01_containerization.ipynb",
     "01 · 容器化：可复现的运行时",
     "分层文件系统与内容寻址 · 层缓存的链式失效 · 多阶段构建 · 模型权重放哪 · 运行时契约六条 —— 把「在我机器上能跑」彻底消灭",
     c48_m01),
    ("02_serving_api", "02_讲解.html", "02_serving_api.ipynb",
     "02 · 推理服务 API",
     "OpenAI 兼容契约 · liveness/readiness 语义分离 · SSE 流式与 TTFT/TPOT · 背压超时限流幂等四道护栏 · Erlang-C 算清一个副本扛多少 QPS",
     c48_m02),
    ("03_kubernetes", "03_讲解.html", "03_kubernetes.ipynb",
     "03 · Kubernetes 编排",
     "声明式 + 水平触发控制循环 · Pod→Service→Ingress 对象模型 · 三种探针的时序契约 · GPU 资源模型的盲区 · 装箱调度与碎片",
     c48_m03),
    ("04_rollout_autoscaling", "04_讲解.html", "04_rollout_autoscaling.ipynb",
     "04 · 发布策略与自动扩缩",
     "爆炸半径 × MTTR · 滚动更新的容量凹陷 · 金丝雀判据的统计学（peeking / SPRT / 非劣性）· HPA 控制律与震荡 · 热备容量与 burn-rate 自动回滚",
     c48_m04),
    ("05_cloud_scheduling_cost", "05_讲解.html", "05_cloud_scheduling_cost.ipynb",
     "05 · 云平台、集群调度与成本",
     "三件套计价的不对称 · 对象存储作为权重的家 · spot 经济学与相关性中断 · K8s Job/Slurm/Ray 三种世界观与 backfill · $/1M token 四因子分解",
     c48_m05),
]


def build():
    install_assets(DIR)

    # ── 各模块 ──
    for i, (folder, html_name, nb_name, h1, subtitle, mod) in enumerate(MODULES):
        prev = nxt = None
        if i > 0:
            p = MODULES[i - 1]
            prev = ("../%s/%s" % (p[0], p[1]), p[3])
        if i < len(MODULES) - 1:
            n = MODULES[i + 1]
            nxt = ("../%s/%s" % (n[0], n[1]), n[3])
        v = lesson(os.path.join(DIR, folder, html_name),
                   num="%02d" % i, total=TOTAL, h1=h1, subtitle=subtitle,
                   meta=mod.META, sections=mod.SECTIONS, prev=prev, nxt=nxt)
        notebook(os.path.join(DIR, folder, nb_name), mod.NB)

    # ── index.html ──
    index(
        os.path.join(DIR, "index.html"),
        title="LLM 生产部署与云原生",
        subtitle="从「模型能跑」到「服务活着」：容器化 · 服务契约 · Kubernetes 编排 · 渐进发布与自动扩缩 · 云平台与成本 —— 用纯 Python 模拟控制平面 + SLO/容量/成本三笔账 · 中文讲解 + 英文术语",
        pills=["6 模块", "Docker · K8s · 服务API · 金丝雀 · Spot",
               "纯标准库/numpy + 对拍参考", "SLO账 + 容量账 + 成本账",
               "CPU only · 无需 Docker/K8s/GPU/云账号"],
        howto=(
            "每个模块先读 <em>HTML 讲解</em> 建立「生产系统为什么这样设计」的工程直觉，再跑 <em>notebook</em> "
            "亲手用纯 Python <strong>把控制平面的逻辑从零实现一遍</strong>——镜像层缓存、SSE 编解码、Erlang-C 容量模型、"
            "reconcile 循环、探针状态机、装箱调度器、HPA 闭环仿真、序贯检验、spot 期望成本、backfill 调度器——"
            "并为每个机制算一笔 <strong>SLO 账、容量账与成本账</strong>。每个练习都有紧跟的 <code>assert</code> 自测判分。"
            "配套 <a href=\"glossary.md\">术语词典</a> 与 <a href=\"references.md\">参考清单</a>。"
            "本课的立场是：<strong>C24（高效推理服务）讲引擎<em>内部</em>怎么跑得快，C37（MLOps）讲模型生命周期怎么管</strong>；"
            "<strong>本课补中间那个缺口</strong>——这个跑得快的引擎，怎么被打包、被调度、被发布、被扩缩、被计费，才能承载真实流量。"
            "<strong>本环境没有 Docker/Kubernetes/GPU/云账号</strong>：但云原生这一层的困难几乎全是「逻辑与数学」的困难而非「跑得动」的困难——"
            "K8s 调度器本质是装箱算法、Deployment 控制器本质是一个 reconcile 循环、HPA 本质是带纯延迟的比例控制器、"
            "金丝雀判据本质是序贯假设检验。这些都能用几十行 Python 写出来并用 <code>assert</code> 验证其性质。"
            "讲解里的 Dockerfile / YAML / sbatch 片段是可直接使用的正确写法，仅作对照展示、不参与运行。"
            "学完你能为一个 LLM 服务做完整的部署设计，并回答「几个副本、多少钱、发布怎么不出事」。"
        ),
        tracks=[
            ("打包与契约 · Packaging &amp; Contract", [
                ("00_setup/00_overview.html", "MODULE 00", "课程总览与环境",
                 "五道关的全景、SLO/容量/成本三笔账、「生产的不对称性」与爆炸半径思维、与 C24/C37 的分工，以及为什么没有集群反而学得更透。"),
                ("01_containerization/01_讲解.html", "MODULE 01", "容器化：可复现的运行时",
                 "镜像 = 一叠内容寻址的只读层；层缓存的链式失效与「越少变的放越前」的期望成本证明；多阶段构建；模型权重要不要进镜像；运行时契约六条与优雅停机。"),
                ("02_serving_api/02_讲解.html", "MODULE 02", "推理服务 API",
                 "OpenAI 兼容协议为何成为事实标准；liveness/readiness 语义分离（LLM 头号事故源）；SSE 三大坑与 TTFT/TPOT；背压/超时/限流/幂等；Erlang-C 容量规划。"),
            ]),
            ("编排与交付 · Orchestration &amp; Delivery", [
                ("03_kubernetes/03_讲解.html", "MODULE 03", "Kubernetes 编排",
                 "水平触发的幂等控制循环为何能容错；Pod/Service/Ingress 对象模型与「Service 只是一条规则」；三种探针的时序契约；K8s 看不见显存；装箱、碎片与拓扑分布。"),
                ("04_rollout_autoscaling/04_讲解.html", "MODULE 04", "发布策略与自动扩缩",
                 "损失 = 爆炸半径 × MTTR；maxUnavailable=0 与容量凹陷；金丝雀判据里的 peeking 灾难、SPRT 与非劣性检验；HPA 震荡与队列深度触发；热备公式与 burn-rate 回滚。"),
            ]),
            ("落地与经济 · Cloud &amp; Economics", [
                ("05_cloud_scheduling_cost/05_讲解.html", "MODULE 05", "云平台、集群调度与成本",
                 "三件套计价的不对称（存字节便宜、搬字节贵）；对象存储作为权重的家；spot 盈亏平衡与相关性中断；K8s Job/Slurm/Ray 三种世界观与 backfill；$/1M token 四因子分解。"),
            ]),
        ],
    )

    # ── README ──
    text_file(os.path.join(DIR, "README.md"), """
# LLM 生产部署与云原生

模型跑得快不等于服务活得下来：容器化、服务契约、Kubernetes 编排、渐进发布与自动扩缩、云平台与成本——
用纯 Python 把控制平面的逻辑从零实现一遍，并为每个机制算一笔 SLO 账、容量账与成本账。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 容器化：可复现的运行时 | `01_containerization/` |
| 02 | 推理服务 API | `02_serving_api/` |
| 03 | Kubernetes 编排 | `03_kubernetes/` |
| 04 | 发布策略与自动扩缩 | `04_rollout_autoscaling/` |
| 05 | 云平台、集群调度与成本 | `05_cloud_scheduling_cost/` |

## 这门课补什么洞
C24（高效推理服务）讲引擎**内部**怎么跑得快；C37（MLOps）讲模型**生命周期**怎么管。
中间那段——**这个引擎怎么被打包、被调度、被发布、被扩缩、被计费**——本课补上。
它也是「LLM Research Engineer」类岗位 JD 里 `Docker / Kubernetes / cloud / MLOps 协作` 那几条的正面回应。

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立生产系统的设计直觉与三笔账，
再跑 `NN_*.ipynb` 用纯标准库/numpy 从零实现控制平面：
镜像层缓存与冷启动分解 → SSE 编解码与 Erlang-C 容量模型 → reconcile 循环/探针状态机/装箱调度器 →
滚动更新仿真/SPRT 序贯检验/HPA 闭环震荡 → spot 期望成本/backfill 调度器/$per-1M-token 分解。
先看 worked 示例（print + assert 自检）→ ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 真实量级胶囊。
所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯标准库 + numpy，**不需要 Docker / Kubernetes / GPU / 云账号 / 联网**。
讲解里的 Dockerfile、Kubernetes YAML、Slurm `sbatch` 脚本是可直接使用的正确写法，仅作对照展示、不参与运行。
所有价格与性能数字均为公开量级的约数，notebook 顶部可改成你自己的报价。

配套：[术语词典](glossary.md) · [参考清单](references.md)
""")

    # ── requirements.txt ──
    text_file(os.path.join(DIR, "requirements.txt"), """
# LLM 生产部署与云原生 —— 依赖清单
# 核心实现纯标准库 + numpy、CPU 可跑（assert 全过）：用 Python 模拟控制平面 + 三笔账推演生产规模。
# 本环境无需 Docker / Kubernetes / GPU / 云账号 / 联网。

numpy          # 核心：容量模型、控制律仿真、成本分解的数值实验
pandas         # 可选：容量规划表与成本表的表格化展示
jupyterlab     # 运行 notebook
ipykernel      # 注册 Jupyter kernel
""")

    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


GLOSSARY = r"""
# 术语词典 · Glossary（LLM 生产部署与云原生）

> 按主题分组，每条 2–3 句释义。读 Kubernetes / Docker / vLLM / Slurm 文档或云账单时遇到生词回这里查；
> 英文术语保留原文（社区与文档的通用语言）。本课用纯 Python 模拟这些机制，但术语与真实生产系统一一对应。

## 世界观与账目 · Mindset & Ledgers

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| SLO (Service Level Objective) | 服务等级目标 | 对服务质量的量化承诺，如「99.9% 可用」「P95 TTFT < 800ms」。它不是技术指标而是**成本决策**：每多一个 9，错误预算缩小 10 倍、成本显著上升。 |
| SLI (Service Level Indicator) | 服务等级指标 | 用来度量 SLO 的实际观测量（成功率、延迟分位数）。定义 SLI 时最容易出错的是「什么算失败」——超时、429、空响应算不算，必须写死。 |
| error budget | 错误预算 | `(1 − SLO) × 时间窗口`。99.9% 对应每 30 天 43.2 分钟。它是**发布速度与稳定性之间的仲裁者**：预算充足可激进发布，预算烧完应冻结发布修稳定性。 |
| burn rate | 燃烧率 | 实际错误率 ÷ 预算错误率。1× 表示刚好按计划消耗，14.4× 表示 2 天烧完月度预算。用它做告警可让一套阈值适配所有 SLO 不同的服务。 |
| blast radius | 爆炸半径 | 一次故障影响的用户/流量比例。本课的第三条纪律：每个设计都要回答「最坏情况下多少用户受影响、多久恢复」。损失 ≈ 爆炸半径 × MTTR。 |
| MTTR / MTTD | 平均恢复/发现时间 | 从故障发生到恢复（到被发现）的平均时长。压小 MTTR 需要可观测性与自动化，有下界；压小爆炸半径更便宜，所以**先压爆炸半径**。 |
| capacity planning | 容量规划 | 由 SLO 反推需要多少副本/节点。核心工具是排队论：给定到达率与服务率，求满足延迟目标的最小并发数。 |
| unit economics | 单位经济 | 把总成本除以业务单位，LLM 服务通常是 `$ / 1M token`。它是与产品/财务沟通的唯一共同语言，也是优化归因的框架。 |
| FinOps | 云财务运营 | 把成本作为工程一等公民管理的实践：成本可见性（按服务/团队归因）、优化（用量与单价）、治理（预算与告警）。 |

## 容器与镜像 · Containers & Images

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| container | 容器 | namespace（隔离视图）+ cgroup（限制资源）+ 分层文件系统。**共享宿主内核**，所以启动快、镜像小，但不提供强安全隔离，也不屏蔽内核与 GPU driver 差异。 |
| OCI image | OCI 镜像 | 开放容器倡议定义的镜像格式：一个有序的只读层列表 + 一份 config（entrypoint、env、工作目录等）。Docker 镜像就是它的一个实现。 |
| layer | 层 | 相对上一层的文件系统增量（新增/修改/删除），打包成 tar。层是**不可变**的，由内容 sha256 唯一标识。 |
| content-addressable storage (CAS) | 内容寻址存储 | 用内容哈希作为标识。带来三个性质：同内容只存一份（去重）、摘要不匹配即损坏（完整性）、层永不失效（可缓存）。镜像整体是一棵 Merkle DAG。 |
| overlayfs / union filesystem | 联合文件系统 | 把多层只读层与一层可写层叠加成单一视图，上层覆盖下层。容器内的写入只落在可写层，删容器即消失。 |
| whiteout | 白出标记 | overlayfs 表示「删除下层文件」的方式。关键后果：**删除文件不会让镜像变小**——下层字节仍在镜像里被传输和存储。所以 `RUN a && rm b` 必须写在同一条指令里。 |
| layer cache | 层缓存 | 构建时复用未变化的层。规则是**链式**的：第 i 层有效 ⟺ 第 i−1 层有效且第 i 条指令及输入未变。一层失效则其后全部重建。 |
| multi-stage build | 多阶段构建 | 在带完整工具链的 builder 阶段编译，只把产物 `COPY --from=builder` 到精简的 runtime 阶段。LLM 场景典型是 `cuda:devel` → `cuda:runtime`，砍掉 50%+ 体积。 |
| BuildKit | Docker 的现代构建后端 | 支持并行构建 DAG、`--mount=type=cache`（构建缓存不进镜像层）、secret 挂载。是「装了再删」问题的现代解法。 |
| .dockerignore | 构建上下文排除清单 | 不是可选项：`COPY . .` 会把 `.git/`、`__pycache__`、本地 checkpoint 全塞进层，且它们的任何变动都会让缓存失效。 |
| base image pinning | 基础镜像钉版 | `FROM python:3.11-slim` 是会漂移的可变标签。生产应用摘要钉死（`@sha256:…`），否则构建不可复现。 |
| nvidia-container-toolkit | NVIDIA 容器工具包 | 把宿主的 GPU driver 与设备节点挂进容器。**镜像里只能装 CUDA runtime，driver 必须来自宿主**——所以镜像 CUDA 版本必须 ≤ 宿主 driver 支持的版本。 |
| cold start | 冷启动 | 从调度到能服务的总时间 = 调度 + 拉镜像 + 进程初始化 + 加载权重 + 预热。LLM 典型 30–120 秒，它是自动扩缩响应速度的下界。 |
| lazy pulling (eStargz / SOCI / Nydus) | 镜像懒加载 | 按需拉取容器启动路径上真正读到的文件，而非整个镜像。对文件多、读取少的 LLM 镜像收益尤其大。 |
| graceful shutdown | 优雅停机 | 收到 SIGTERM 后的正确顺序：①标记 not ready ②等端点传播（`preStop: sleep 5`）③排空在途请求 ④退出。顺序不能变——摘流量必须先于停服务。 |
| terminationGracePeriodSeconds | 终止宽限期 | 从 SIGTERM 到 SIGKILL 的时间。默认 30 秒对 LLM 太短（一次长生成可能 60 秒），必须调大到最长生成时间以上。 |
| 12-factor app | 十二要素应用 | 一组云原生应用约定，本课用到的核心几条：配置外置于环境、日志走 stdout、进程无状态可随时销毁重建。 |

## 服务契约与流式 · Serving Contract & Streaming

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| OpenAI-compatible API | OpenAI 兼容 API | 事实标准的 LLM 服务协议（`/v1/chat/completions` 等）。兼容它可免费获得整个客户端生态（LangChain、各种 SDK、压测与监控工具）。 |
| liveness probe | 存活探针 | 「进程还活着吗」。失败后果是**重启容器**。判据：只有「重启能修复」的状态才放这里（死锁、事件循环卡死），绝不检查下游依赖（否则下游抖动会引发全体重启）。 |
| readiness probe | 就绪探针 | 「现在能接流量吗」。失败后果是**从 Service 端点摘除但不重启**。LLM 服务必须实现它——模型加载要几分钟，这期间应「alive 但 not ready」。 |
| startup probe | 启动探针 | 为慢启动应用设计：成功之前另两个探针都不生效。**LLM 服务的救命稻草**——没有它，慢加载的模型会被 liveness 反复杀死，陷入永远加载不完的重启死循环。 |
| TTFT (Time To First Token) | 首 token 延迟 | 从请求到第一个 token 的时间 = 排队 + prefill。用户感知的「响应速度」，典型目标 < 500ms。 |
| TPOT / ITL | 每输出 token 时延 | 后续 token 之间的间隔，反映 decode 速度，典型目标 < 50ms。**TTFT 与 TPOT 必须分别定 SLO**——端到端延迟会被输出长度分布主导，不能作为指标。 |
| SSE (Server-Sent Events) | 服务器推送事件 | 基于普通 HTTP 的单向流式协议：`data: <payload>\n\n`。三大生产坑：中间层缓冲（要关 `proxy_buffering`）、网关空闲超时、客户端断连不传播（要取消后端生成）。 |
| backpressure | 背压 | 过载时把压力沿调用链往上游传（快速返回 429 + `Retry-After`），而不是自己无限排队。**拒绝比排队更负责任**——排队会让所有人超时且白烧算力。 |
| admission control | 准入控制 | 在服务入口限制并发，保护推理引擎不被打爆。入口拒绝几乎零成本，引擎内因 KV 不足而抢占重算则要浪费已算的 token。 |
| token bucket | 令牌桶 | 以固定速率补令牌、容量为 b 的限流器。允许最多 b 的短时突发但长期速率被限住，比固定窗口计数器（边界处会放过 2 倍）平滑得多。 |
| RPM / TPM | 每分钟请求数 / token 数 | LLM 限流的双维度。**只限 RPM 必被长生成绕过**（一个请求可能生成 10 或 4000 token，差 400 倍），必须同时限 TPM。 |
| idempotency key | 幂等键 | 客户端提供的去重标识，服务端在短窗口内缓存 (key → 结果)。让超时重试安全，对 LLM 还能省下一整次生成的算力。 |
| M/M/c | M/M/c 排队模型 | 泊松到达、指数服务时间、c 个服务位的排队模型。核心结论：排队时间是利用率 ρ 的**双曲函数**，ρ→1 时爆炸；且 c 越大同 ρ 下排队越少（规模经济）。 |
| Erlang-C | 爱尔朗 C 公式 | M/M/c 中「到达时需要排队的概率」。用它可从 SLO 直接反解出最小副本数。对 LLM 是**乐观下界**（真实服务时间重尾），真实数字要靠压测标定。 |
| utilization (ρ) | 利用率 | `λ/(cμ)`。生产目标区间通常 0.6–0.8：从 0.8 推到 0.95 只多榨 19% 吞吐，排队时间却涨数倍。留出的余量买的是延迟稳定性与吸收突发的能力。 |

## Kubernetes 与编排 · Kubernetes & Orchestration

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| declarative | 声明式 | 你描述「期望状态」，系统持续负责让现实符合它。对立面是命令式（你逐步下达动作，中途失败要自己写恢复逻辑）。 |
| reconcile loop | 调谐循环 | K8s 所有控制器的统一模式：读期望 → 观察现状 → 发出差量动作。你在模块 00/03 会亲手写它。 |
| level-triggered | 水平触发 | 只看当前状态、不看事件历史。这是控制器能容忍消息丢失/重复/乱序的根本原因；边沿触发（按事件响应）丢一条就永久错位。 |
| eventually consistent | 最终一致 | K8s 的代价：`kubectl apply` 成功 ≠ Pod 已重建 ≠ 端点已更新 ≠ 流量已切换。每一跳是独立循环，各有延迟。优雅停机要 `sleep 5` 正源于此。 |
| Pod | Pod | 一组共享网络与存储的容器，调度的最小单位。GPU 在 Pod 级申请；initContainer 是拉取模型权重的标准位置。 |
| Deployment / ReplicaSet | 部署 / 副本集 | Deployment 管版本切换与滚动策略，ReplicaSet 管「有 N 个匹配标签的 Pod」。滚动更新期间会同时存在两个 ReplicaSet。 |
| Service | 服务 | 给一组 Pod 一个稳定虚拟 IP/DNS。**它不是进程而是一条转发规则**，做的是**连接级**四层负载均衡——对 HTTP/2、gRPC、长连接 SSE 会严重倾斜，需要七层网关。 |
| EndpointSlice | 端点切片 | Service 背后的实际后端列表，**只包含 ready 的 Pod**。这就是 readiness 探针的全部意义。排查「Pod Running 但没流量」第一步就看它。 |
| requests / limits | 资源请求 / 上限 | requests 是**调度依据**（节点要有这么多可分配量），limits 是**运行时上限**（cgroup 强制）。CPU 超 limit 被限流，内存超 limit 被 OOMKilled。 |
| QoS class | 服务质量等级 | Guaranteed（requests==limits 且全设）> Burstable > BestEffort（什么都不设，**第一个被驱逐**）。生产 LLM 服务应是 Guaranteed。 |
| extended resource | 扩展资源 | 如 `nvidia.com/gpu`。必须是整数、不可超卖、requests 必须等于 limits。**K8s 只数「几张卡」，看不见显存**——显存预算必须在应用层算死。 |
| ephemeral-storage | 临时存储 | 节点本地磁盘配额。权重下载到 emptyDir 会占它；不声明会触发 DiskPressure 驱逐，且被驱逐的常常不是罪魁祸首。 |
| bin packing | 装箱 | 把 Pod 塞进节点的向量装箱问题（NP-hard）。K8s 用在线贪心；`LeastAllocated`（默认，分散）制造碎片，`MostAllocated`（装箱）留出完整空节点。 |
| fragmentation | 碎片 | 总空闲资源充足但分散在多个节点上，导致大任务哪儿都放不下。「集群还剩 30 张卡」和「能不能跑 8 卡任务」是两个不同的问题。 |
| resource stranding | 资源搁浅 | 小任务先占据每台机器一点，大任务永远排不进去。解法是让大 Pod 优先（PriorityClass / FFD 排序）。 |
| affinity / anti-affinity | 亲和 / 反亲和 | 让 Pod 靠近或远离某类 Pod/节点。硬反亲和（每节点 1 副本）与装箱直接冲突，且成本可能高 3 倍以上。 |
| topologySpreadConstraints | 拓扑分布约束 | 跨可用区/机架均匀分布，`maxSkew` 控制偏斜。**「跨 AZ 均分 + 区内装箱」几乎总是正确答案**——兼顾抗区域故障与成本。 |
| taint / toleration | 污点 / 容忍 | 节点主动排斥 Pod 除非 Pod 明确容忍。GPU 节点打 taint 可防止普通 Pod 占用宝贵机器。 |
| PodDisruptionBudget (PDB) | Pod 中断预算 | 自愿驱逐（节点维护、缩容）时至少保留多少可用副本。设得太严会让 `kubectl drain` 永远卡住。 |
| gang scheduling | 成组调度 | 要么全部调度、要么都不调度。多节点分布式推理/训练必需，否则部分启动会死锁。K8s 需 Volcano/Kueue 等插件补齐。 |
| DaemonSet | 守护进程集 | 每节点一个 Pod。用于 GPU device plugin、日志采集，以及**模型权重的节点本地预热缓存**。 |
| StatefulSet / LeaderWorkerSet | 有状态集 / 主从集 | 需要稳定网络标识时用。多节点张量并行的一个模型实例（16 个进程共同构成一个副本）用 Deployment 表达不了。 |

## 发布与扩缩 · Delivery & Autoscaling

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| progressive delivery | 渐进交付 | 把「上线」从一个瞬时动作变成一个分阶段、带判据、可自动回滚的过程。金丝雀、蓝绿、影子流量都属于它。 |
| maxSurge / maxUnavailable | 最大超出 / 最大不可用 | 滚动更新的两个参数。`maxUnavailable` 决定容量凹陷多深，`maxSurge` 决定更新多快、多占多少资源。**LLM 服务标准配置是 `maxUnavailable: 0`**。 |
| blue-green deployment | 蓝绿发布 | 两套全量环境并存，瞬间切换流量。回滚是秒级的，代价是 2 倍资源。适合要求瞬间回滚且能承受成本的场景。 |
| canary release | 金丝雀发布 | 小流量（1%→5%→25%）逐步放量，每阶段做自动分析，失败则权重归零。**LLM 服务的默认选择**：额外成本最低、错误预算消耗最低。 |
| shadow traffic | 影子流量 | 把真实流量镜像给新版本但不返回给用户。对用户零影响，可验证性能与正确性，但验证不了用户反应。 |
| analysis run | 自动分析 | 金丝雀每阶段的判据执行。分两类：系统指标（错误率/延迟，秒级可判）与质量指标（judge 胜率等，慢且方差大）——**两条腿分开走**。 |
| peeking | 偷看 | 反复对同一实验做显著性检验。会严重膨胀假阳性率（每 100 样本看一次，A/A 测试的假阳性可达 20%+），导致大量正常发布被误判回滚。 |
| SPRT (sequential probability ratio test) | 序贯概率比检验 | 维护对数似然比，越界即判定，**在任意停止时刻都保持名义错误率**。是 peeking 问题的正确解法。 |
| non-inferiority test | 非劣性检验 | 原假设设为「新版本差了至少 δ」，拒绝它才放行。发布要问的是「会不会更差」而非「是不是更好」；**样本不足时它会拦截，而普通检验会放行**。 |
| HPA (Horizontal Pod Autoscaler) | 水平自动扩缩 | `desired = ceil(current × M/M_target)`，带容差带（默认 ±10%）避免目标点抖动。本质是带纯延迟的比例控制器。 |
| stabilization window | 稳定窗口 | 缩容前取过去 N 秒建议值的最大值（默认 300s），扩容默认 0s。**这个不对称是刻意的**：扩容要快（用户在等），缩容要慢（防抖）。 |
| leading vs lagging indicator | 领先 / 滞后指标 | 队列深度是领先指标（堆积时延迟还没坏，扩容还来得及），延迟是滞后指标（破线时已在伤害用户）。**用滞后指标做反馈控制等于看后视镜开车**。 |
| KEDA | 事件驱动自动扩缩 | 按外部事件源（队列长度、Kafka lag、Prometheus 查询）扩缩，并支持 scale-to-zero。LLM 服务按队列深度扩缩的常用实现。 |
| scale-to-zero | 缩容到零 | 无流量时不留副本。只适合请求间隔远大于冷启动、且能容忍首次高延迟的场景；面向终端用户的交互服务应保留 `minReplicas: 1`。 |
| warm buffer | 热备缓冲 | 为吸收扩容延迟而多养的空闲副本，`R_buffer ≥ (dλ/dt × T_cold) / μ`。**冷启动时间是这笔成本的乘数**——压缩冷启动的收益在这里被放大。 |
| rollback storm | 回滚风暴 | 判据太敏感 → 回滚 → 回滚本身是变更 → 再次触发 → 在两版本间横跳。防护三件套：回滚冷却期、次数上限、判据要求持续性。 |

## 云平台、调度与成本 · Cloud, Scheduling & Cost

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| object storage | 对象存储 | S3/GCS 等。扁平命名空间、不可变更新、单连接带宽有限、按请求计费。**不是文件系统**——没有 rename（是 copy+delete）、没有 append，正确用法是「下载到本地再加载」。 |
| egress | 出网流量 | 数据流出云/区域的费用。云计价最大的不对称：**进免费、出收费；同区便宜、跨区贵、出公网最贵**。常占总账单 15–30% 且最容易失控。 |
| spot / preemptible instance | 抢占式实例 | 云厂商的闲置容量，折扣 60–90%，可能随时被收回（给 30 秒到 2 分钟通知）。 |
| interruption cost (c_int) | 中断成本 | 一次抢占造成的损失（重启 + 重载 + 丢失的进行中工作）。**spot 是否划算由它决定，而非由折扣力度决定**：盈亏平衡中断率 `h* = (p_od − p_spot)/c_int`。 |
| correlated interruption | 相关性中断 | spot 中断不是独立事件——区域容量紧张时可能全部同时被收回。设计必须回答「全部 spot 消失后还剩多少容量」。 |
| baseline + burst capacity | 基线 + 弹性容量 | 标准做法：基线（按需/预留）覆盖 P50 保证 SLO 下界，弹性（spot）覆盖峰值。最坏情况从「服务不可用」退化为「性能降级」。 |
| reserved instance / savings plan | 预留实例 / 节省计划 | 承诺 1–3 年用量换 30–60% 折扣。适合确定长期存在的基线容量；GPU 迭代快，通常建议 1 年而非 3 年。 |
| Slurm | Slurm 作业调度器 | HPC/超算的事实标准。核心概念：分区（partition）、作业（job）、`--gres=gpu:8`、`--time`。内置优先级、fairshare、backfill。 |
| backfill | 回填调度 | 在等大作业攒资源的空隙里插入能在预约前跑完的小作业。实用推论：**`--time` 填得越准（越短），排队等得越少**（配 checkpoint + `--requeue` 兜底）。 |
| Ray | Ray 分布式框架 | Python 原生的分布式计算：`@ray.remote` 装饰器、actor、对象存储、placement group。适合分布式实验、RL、超参搜索与数据处理。 |
| Kueue / Volcano | K8s 批作业调度插件 | 给 K8s 补上排队、配额、gang scheduling 与公平性。裸 K8s 跑训练作业通常利用率很差。 |
| MIG / MPS / time-slicing | GPU 细粒度共享 | MIG 硬件切分（隔离好、粒度固定）、MPS 进程共享（无隔离）、时间片（无显存隔离）。都不理想，是当前活跃的工程方向。 |
| $ / 1M tokens | 每百万 token 成本 | `p_node / (T_peak × u × η × 3600/1e6)`，四因子分别由引擎、扩缩、调度、采购决定。**四者边际收益相同但改善难度天差地别**——先摘低垂的果子。 |
| packing ratio (η) | 装箱率 | 已分配资源 ÷ 总资源。硬反亲和会把它压到 25%，装箱调度能到 80%+，直接是 3 倍的成本差异。 |
| carbon-aware scheduling | 碳感知调度 | 按电网碳强度把延迟不敏感的作业调度到低碳时段/区域。技术可行，但与成本、容量的多目标权衡缺乏公认框架。 |
"""

REFERENCES = r"""
# 参考清单 · References（LLM 生产部署与云原生）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 本课用纯 Python 模拟复现的每个机制，都能在下列文献/文档里找到真实生产系统上的对应实现与权衡。
> 与相邻课程的分工：**C24** 讲推理引擎内部（PagedAttention、continuous batching），**C37** 讲模型生命周期（实验追踪、漂移、CI/CD 门禁），
> **C39** 讲分布式训练工程，**本课**讲三者之间那段——打包、契约、编排、发布、成本。

## 容器与镜像 · Containers & Images
- ★ **Open Container Initiative, _Image Format Specification_** — 镜像格式的权威定义：manifest、layer digest、config。读它你会发现「镜像」这个概念比工具文档里讲的简单得多——就是一棵 Merkle DAG。模块 01 的分层与内容寻址实现直接对标它。
- ★ **Docker, _Best practices for writing Dockerfiles_ + BuildKit 文档** — 层缓存、`.dockerignore`、多阶段构建、`--mount=type=cache` 的官方说明。模块 01 的「越少变的放越前」与「装了再删必须同层」两条铁律的一手来源。
- ★ **NVIDIA, _NVIDIA Container Toolkit 文档_** — 解释了为什么容器隔离不了 GPU driver、镜像里只能装 CUDA runtime、以及版本兼容矩阵。上线失败最常见原因之一（`CUDA driver version is insufficient`）的根治参考。
- **Merkel 2014, _Docker: Lightweight Linux Containers for Consistent Development and Deployment_** — 容器技术的经典综述，把 namespace/cgroup/联合文件系统三者的关系讲清楚。适合建立「容器不是虚拟化」的准确心智模型。
- **Harter et al. 2016, _Slacker: Fast Distribution with Lazy Docker Containers_ (FAST'16)** — 实测发现容器启动时间中拉镜像占 76%，而实际只有 6.4% 的数据被读取。这是所有懒加载工作（eStargz/SOCI/Nydus）的动机来源，也是模块 01 冷启动分解的实证依据。
- **containerd/stargz-snapshotter 与 AWS SOCI 文档** — 镜像懒加载的两个主流实现。读它理解「按需拉取」在 registry 兼容性与索引构建上的实际代价。

## 服务契约与推理服务 · Serving Contract
- ★ **vLLM, `vllm/entrypoints/openai/` 源码** — 最好的 OpenAI 兼容层参考实现。`protocol.py` 是完整的请求/响应 schema，`api_server.py` 展示了流式、健康端点、指标暴露的工程做法。想自建服务就照着它抄。
- ★ **Kwon et al. 2023, _Efficient Memory Management for Large Language Model Serving with PagedAttention_ (SOSP'23)** — vLLM 的论文。本课只用它一个结论：KV 缓存决定了引擎能并发多少序列（`B_max`），而这个数就是模块 02 准入控制的上限。引擎内部细节见 C24。
- ★ **Agrawal et al. 2024, _Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve_ (OSDI'24)** — 系统地论证了 TTFT 与 TPOT 的冲突（prefill 会拖长正在 decode 的请求），并给出 chunked prefill 的解法。模块 02 「延迟指标必须拆开」的理论支撑。
- **Zhong et al. 2024, _DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving_ (OSDI'24)** — prefill/decode 分池的代表作。读它理解为什么大规模服务正在往「两个实例池 + KV 传输」的架构走，以及这对编排层提出了什么新要求。
- **WHATWG HTML Living Standard, _Server-Sent Events_ 一节** — SSE 的规范定义（`data:` 字段、空行分隔、重连语义）。模块 02 的编解码器按它实现；生产三大坑（缓冲/超时/断连）则是规范之外的工程经验。
- **Gross, Shortle, Thompson & Harris, _Fundamentals of Queueing Theory_, 第 2–3 章** — Erlang-C 的严格推导与 M/M/c 的性质。模块 02 的容量模型以它为准。重点看「为什么 W_q 是 ρ 的双曲函数」和「并发数增大带来的规模经济」。
- **Nygard, _Release It!_ (2nd ed.)** — 稳定性模式的经典：断路器、舱壁、超时、快速失败、背压。模块 02 的四道护栏几乎全部出自这本书的模式语言，强烈建议通读。

## Kubernetes 与编排 · Kubernetes
- ★ **Kubernetes 官方文档：_Pod Lifecycle_ / _Configure Liveness, Readiness and Startup Probes_** — 本模块最重要的一手来源，写得远好于大多数二手教程。探针的精确时序语义（startupProbe 成功前另两个不生效）、终止流程（preStop → SIGTERM → grace period → SIGKILL）都在这里。
- ★ **Kubernetes 官方文档：_Resource Management for Pods and Containers_ + _Pod Quality of Service Classes_** — requests/limits 的准确语义、QoS 分级与驱逐顺序、扩展资源（GPU）为何必须 requests==limits。模块 03 资源模型一节的依据。
- ★ **Kubernetes 官方文档：_Assigning Pods to Nodes_ / _Pod Topology Spread Constraints_ / _Scheduling Framework_** — 亲和性、拓扑分布、调度器的 Filter/Score 插件结构。模块 03 的调度器实现照着这个两阶段结构写。
- ★ **Verma et al. 2015, _Large-scale cluster management at Google with Borg_ (EuroSys'15)** — K8s 的思想源头。优先级与抢占、资源回收、作业分类（prod vs batch）、利用率数据都在这里。读它你会明白 K8s 的很多设计不是凭空来的。
- **Burns, Grant, Oppenheimer, Brewer & Wilkes 2016, _Borg, Omega, and Kubernetes_ (ACM Queue)** — 三代集群管理系统的设计复盘，尤其是「为什么选择声明式与控制循环」。理解 K8s 哲学的最短路径。
- **Coffman, Garey & Johnson, _Approximation Algorithms for Bin Packing: A Survey_** — 装箱问题的理论边界与 FFD 等启发式的竞争比。模块 03 「大 Pod 优先」建议的理论依据。
- **Kubernetes SIG-Scheduling, _Kueue_ 与 **CNCF, _Volcano_** 文档** — 给 K8s 补上批作业排队、配额与 gang scheduling。跑训练/评测作业时必读，否则集群利用率会很难看。
- **Kubernetes Gateway API Inference Extension（社区提案与实现）** — 「比 Deployment 更懂 LLM」的编排抽象尝试：模型版本、KV 缓存亲和路由、prefill/decode 分池。当前变化最快的一层，值得持续跟踪。

## 发布、可靠性与统计判据 · Delivery & Reliability
- ★ **Beyer et al., _Site Reliability Engineering_（Google SRE Book），第 3–5 章与第 27 章** — 错误预算、多窗口多燃烧率告警的原始配方、渐进发布。模块 00 的三笔账与模块 04 的自动回滚判据全部出自这里。第 5 章的 burn-rate 表格建议直接照抄。
- ★ **Argo Rollouts 文档，_Analysis_ / _Canary Strategy_** — 工业界金丝雀判据的实际形态：AnalysisTemplate、指标查询、失败限制、自动回滚。读它看「理论上的假设检验」如何变成可运行的 CRD。
- ★ **Flagger 文档，_Canary Analysis_** — 与 Argo Rollouts 并列的实现，对渐进放量与指标门禁的抽象略有不同，两者对读能看清设计空间。
- ★ **Kubernetes 官方文档：_Horizontal Pod Autoscaling_** — HPA 的精确算法（含容差带）、`behavior` 字段的稳定窗口与速率策略语义。模块 04 的控制律仿真按它实现。
- **Howard, Ramdas, McAuliffe & Sekhon 2021, _Time-uniform, nonparametric, nonasymptotic confidence sequences_ (Annals of Statistics)** — always-valid 推断的现代基础。它解决的正是金丝雀的 peeking 问题：在任意停止时刻都保持覆盖率。想把序贯方法做进发布流水线，从这里入门。
- **Wald 1945, _Sequential Tests of Statistical Hypotheses_** — SPRT 的原始论文。模块 04 的序贯检验实现直接来自它，简洁且易于工程化。
- **Johari, Koomen, Pekelis & Walsh 2017, _Peeking at A/B Tests: Why it matters, and what to do about it_ (KDD'17)** — 用工业界数据展示 peeking 造成的假阳性膨胀，并给出 always-valid p 值的实用方案。本课模块 04 那个「A/A 测试假阳性 20%」的实验，就是它的复现。
- **KEDA 文档** — 事件驱动扩缩与 scale-to-zero。LLM 服务按队列深度扩缩的标准实现，比 prometheus-adapter 路线简单得多。
- **Humble & Farley, _Continuous Delivery_** — 部署流水线、可重复发布、回滚优先于修复等原则的系统论述。虽然写在 K8s 之前，但原则完全适用。

## 云平台、调度与成本 · Cloud, Scheduling & Cost
- ★ **AWS, _Amazon EC2 Spot Instances Best Practices_ / GCP, _Preemptible & Spot VMs_ 文档** — 中断通知的处理、实例池多样化、容量回退策略的官方指南。模块 05 的 spot 工程实践三件套出自这里。
- ★ **SchedMD, _Slurm Quick Start User Guide_ + _Slurm Scheduling Configuration Guide_（backfill 一节）** — Slurm 的一手文档，比任何二手教程都清楚。重点读 backfill 的调度逻辑，它解释了「`--time` 填得越准排队越短」这条最实用的经验。
- ★ **Moritz et al. 2018, _Ray: A Distributed Framework for Emerging AI Applications_ (OSDI'18)** + Ray Architecture Whitepaper — Ray 的设计与 task/actor 模型。理解「Python 原生分布式」这条路线与 K8s/Slurm 的世界观差异。
- ★ **Yang et al. 2023, _SkyPilot: An Intercloud Broker for Sky Computing_ (NSDI'23)** — 跨云选型、spot 容错、作业迁移的开源实现。**非常值得读源码**：它把本模块讲的成本模型、spot 中断处理、多云回退全部工程化了。
- **Patterson et al. 2021, _Carbon Emissions and Large Neural Network Training_** — 算力的碳账与影响因子（模型、硬件、数据中心、电网）。碳感知调度的量化基础。
- **FinOps Foundation, _FinOps Framework_（成本可见性 / 优化 / 治理三阶段）** — 把成本当工程一等公民管理的方法论。模块 05 的成本归因与单位经济分析的框架来源。
- **OpenCost / Kubecost 文档** — K8s 上按 namespace/label 的成本分摊实现。LLM 服务还要在应用层补 `model_version` + `tenant` 的 token 计数才能算准。
- **Amazon S3 / Google Cloud Storage 的一致性与性能文档** — 对象存储的读后写一致性、分片并发下载、请求计费模型。模块 05 「存字节便宜、搬字节贵」的定价依据。

## 跨课衔接 · Cross-course
- **C24 高效推理服务** — 本课模块 02 的 `μ`（单副本服务率）与 `B_max`（并发上限）从哪来，答案在那门课：PagedAttention、continuous batching、投机解码、FP8 服务。本课把它们当作已知参数。
- **C37 MLOps 与生产生命周期** — 实验追踪、数据/模型版本、评测门禁与 CI/CD、监控与漂移。本课的「发布」是那门课「门禁」的下游执行环节，两课合起来是完整的交付链。
- **C39 分布式训练工程** — 多节点通信、FSDP、3D 并行、checkpoint 与容错。本课模块 05 的 Slurm 与 gang scheduling 是它的运行底座；多节点推理的编排需求也源自那门课的并行策略。
- **C03 / C10 评测科学与测量** — 模块 04 金丝雀的「质量指标」判据（judge 胜率、非劣性检验、样本量规划）在那两门课有完整的统计基础。
- **C12 / C45 负责任 AI 与隐私** — 模块 05 数据合规一节（数据出境、日志留存、对话不进训练集）的展开在那两门课。
"""


if __name__ == "__main__":
    ok = build()
    print("\n构建完成 ✅" if ok else "\n⚠️ 有讲解页可见字符不足 8000，请补充")
