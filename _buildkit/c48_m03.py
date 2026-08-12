# -*- coding: utf-8 -*-
"""C48 模块 03 · Kubernetes 编排。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–02、进程与资源限制的基本概念"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_kubernetes.ipynb'),
    ("核心参考", "Kubernetes 官方文档（Pod Lifecycle / Scheduling / Resource Management）、Borg 论文、kube-scheduler 源码结构"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("idea", "K8s 的唯一核心思想：声明式 + 控制循环", "".join([
        P("Kubernetes 的表面复杂度是出了名的——几十种资源类型、上百个字段、无穷的 CRD。但它的<strong>核心思想只有一个</strong>，而且你在模块 00 已经写过它了："),
        ASCII("""        ┌──────────────────────────────────────────────┐
        │  while True:                                 │
        │      desired = read_spec()      # 你想要什么  │
        │      current = observe_world()  # 现在是什么  │
        │      act(diff(desired, current))# 补上差距    │
        └──────────────────────────────────────────────┘
                        这就是 reconcile 循环。

K8s = 一堆这样的循环，各管一件事，通过一个共享的状态存储（etcd）互相协作。

  Deployment 控制器  → 保证「ReplicaSet 的副本数 = 我 spec 里写的」
  ReplicaSet 控制器  → 保证「Pod 数量 = 我 spec 里写的」
  调度器 scheduler   → 保证「每个 Pod 都被分配到一个节点」
  kubelet            → 保证「本节点上该跑的容器都在跑」
  端点控制器         → 保证「Service 的端点列表 = 所有 ready 的 Pod」
  HPA                → 保证「Deployment 的副本数 = 按指标算出来的数」（模块 04）"""),
        DUAL(
            "为什么这个设计如此强大？因为<strong>它把「怎么做」从你的脑子里挪到了系统里</strong>。命令式世界里，「把服务从 3 个副本升级到新版本」是一串你必须亲自编排的步骤（起一个新的、等它就绪、摘掉一个旧的、再起一个……），中途任何一步失败你都得写恢复逻辑。声明式世界里你只说「我要 3 个副本、镜像是 v2」，剩下的是控制器的事——而且它<em>持续</em>负责，机器宕了它补，人误删了它补。",
            "更精确地说，控制器是一个<span class=\"term\">幂等</span>的、<span class=\"term\">水平触发</span>（level-triggered）的函数。水平触发意味着它<strong>只看当前状态，不看事件历史</strong>——这是它能容忍消息丢失、重复、乱序的根本原因。相比之下，边沿触发（edge-triggered，「收到创建事件就创建」）的系统一旦丢一条消息就永久错位。K8s 所有控制器都是水平触发的，所以「重放一遍」永远安全。",
        ),
        CALLOUT("intuition", "带走这一条，你就能自己推导出 K8s 的大部分行为：<strong>凡是你观察到的现象，都应该能被解释成「某个控制器在把现实拽向它的期望」</strong>。Pod 被删了又出现？ReplicaSet 控制器干的。改了 Pod 的镜像结果被改回去了？Deployment 控制器干的（它管的是模板，你改实例没用）。删了 Deployment 但 Pod 还在？孤儿 Pod 没了 owner，没人管它了。<em>遇到诡异行为，先问「是哪个循环在动」</em>。"),
        CALLOUT("warn", "这个设计也有它的代价，必须知道：<strong>一切都是最终一致的（eventually consistent）</strong>。你 <code>kubectl apply</code> 之后，「Deployment 已更新」不等于「Pod 已重建」不等于「Service 端点已更新」不等于「Ingress 已把流量切过去」。每一跳都是一个独立循环，各有各的延迟（几百毫秒到几秒）。模块 01 讲的优雅停机要 <code>preStop: sleep 5</code>，根源就在这里——<em>端点摘除的传播比你想象的慢</em>。"),
    ])),
    ("objects", "对象模型：从 Pod 到 Ingress 的六层", "".join([
        P("K8s 的对象很多，但一个无状态推理服务只需要理解六个，而且它们是层层包裹的关系。"),
        ASCII("""外部用户
   │  https://api.example.com/v1/chat/completions
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingress / Gateway      七层路由：域名、路径、TLS、限流       │
├─────────────────────────────────────────────────────────────┤
│ Service (ClusterIP)    稳定的虚拟 IP + DNS 名；负载均衡      │
│   ↳ 端点列表 = 所有 **ready** 的 Pod IP  ← readiness 在这生效 │
├─────────────────────────────────────────────────────────────┤
│ Deployment             管版本与滚动更新策略（模块 04）        │
│   ↳ ReplicaSet(v2)     管「副本数 = N」                      │
│       ↳ ReplicaSet(v1) 旧版本，滚动期间副本数递减到 0        │
├─────────────────────────────────────────────────────────────┤
│ Pod                    调度与资源的最小单位；共享网络命名空间 │
│   ├─ initContainer     顺序跑完才启动主容器（拉权重就在这）   │
│   ├─ container: server 你的推理服务                          │
│   └─ container: sidecar 日志/指标/代理（可选）               │
├─────────────────────────────────────────────────────────────┤
│ Node                   一台机器；kubelet 在上面执行           │
└─────────────────────────────────────────────────────────────┘"""),
        TABLE(["对象", "一句话职责", "LLM 服务里的关键点"], [
            ["<strong>Pod</strong>", "一组共享网络与存储的容器，调度的最小单位", "GPU 是 Pod 级申请；initContainer 是拉权重的标准位置"],
            ["<strong>ReplicaSet</strong>", "保证「有 N 个匹配标签的 Pod」", "你几乎不直接操作它；滚动更新时会同时存在两个"],
            ["<strong>Deployment</strong>", "管理 ReplicaSet 的版本切换与滚动策略", "<code>maxSurge/maxUnavailable</code> 决定更新期间的容量曲线（模块 04）"],
            ["<strong>Service</strong>", "给一组 Pod 一个稳定的 IP/DNS，做四层负载均衡", "<strong>端点列表只包含 ready 的 Pod</strong>——这是 readiness 探针的全部意义"],
            ["<strong>Ingress / Gateway</strong>", "七层入口：域名、路径、TLS、超时、缓冲", "SSE 必须在这里关缓冲、调大超时（模块 02）"],
            ["<strong>ConfigMap / Secret</strong>", "配置与密钥的外置载体", "模型路径、限流额度放 ConfigMap；API key 放 Secret（且启用静态加密）"],
        ]),
        P("有个概念上的坑值得点破：<strong>Service 不是一个进程，是一条规则</strong>。它没有实体，只是 kube-proxy（或 eBPF/IPVS）在每个节点上写下的一组转发规则，把「访问这个虚拟 IP」重写成「随机挑一个健康 Pod 的真实 IP」。理解这一点你就明白为什么 Service 的负载均衡是<em>连接级</em>而非<em>请求级</em>的——对 HTTP/1.1 短连接没问题，但对 <strong>HTTP/2 或长连接（SSE、gRPC）就会严重不均</strong>：一条连接建立后所有请求都打给同一个 Pod。"),
        CALLOUT("danger", "<p>这是 LLM 服务的第二个高频坑：<strong>用普通 Service 做 gRPC 或长连接 SSE 的负载均衡，会导致 Pod 负载严重倾斜</strong>。10 个客户端连上来，可能 8 条连接落到同一个 Pod，其余 Pod 闲着。解决办法：①用支持七层的 Ingress/Gateway（Envoy 系）做<em>请求级</em>负载均衡；②客户端侧做连接池 + 定期重连（<code>maxConnectionAge</code>）；③用服务网格。<em>只要你的服务是流式的，就必须处理这件事</em>——而它在压测（通常每个虚拟用户一条新连接）中往往看不出来。</p>", "Service 的四层负载均衡骗过了很多人"),
    ])),
    ("probes", "探针：三种，各管一段生命周期", "".join([
        P("模块 02 定义了 <code>/healthz</code> 与 <code>/ready</code> 的语义，这里讲它们如何被 kubelet 使用。K8s 有<strong>三种</strong>探针，很多人只知道两种，而漏掉的那种恰恰是 LLM 服务最需要的。"),
        TABLE(["探针", "失败后果", "何时开始探", "LLM 服务典型配置"], [
            ["<strong>startupProbe</strong>", "杀掉容器重建", "容器启动后立刻，<strong>成功之前另外两个探针不生效</strong>", "<code>failureThreshold: 60, periodSeconds: 10</code> → 给模型加载 10 分钟窗口"],
            ["<strong>livenessProbe</strong>", "杀掉容器重建", "startupProbe 成功后", "<code>periodSeconds: 20, failureThreshold: 3</code>，只测事件循环"],
            ["<strong>readinessProbe</strong>", "从 Service 端点摘除（<strong>不重启</strong>）", "startupProbe 成功后", "<code>periodSeconds: 5, failureThreshold: 2</code>，测权重+队列"],
        ]),
        DUAL(
            "<strong>startupProbe 是为「启动慢」的应用发明的</strong>，简直是为 LLM 量身定做。没有它，你会陷入两难：liveness 的 <code>initialDelaySeconds</code> 设短了，模型还在加载就被判定为死、杀掉重来，形成<em>重启死循环</em>（永远加载不完）；设长了（比如 600 秒），那么服务真的在运行期挂掉时，也要等 10 分钟才被发现。startupProbe 解开了这个结：<em>启动期用宽松的它，启动完切换到严格的 liveness</em>。",
            "三者的时序契约是：<code>startupProbe</code> 成功（或未配置）之前，<code>liveness</code> 与 <code>readiness</code> 都不执行；成功之后 startupProbe 不再执行，另两个开始按各自周期运行。最坏启动容忍时间 = <code>failureThreshold × periodSeconds + initialDelaySeconds</code>。发现故障的最坏延迟 = <code>liveness.failureThreshold × liveness.periodSeconds</code>。<strong>这两个数字要分别对着「最慢的冷启动」和「可接受的故障发现时间」来定</strong>，而不是抄默认值。",
        ),
        CODE("""# LLM 推理服务的探针配置（可直接用的骨架）
startupProbe:                    # 给模型加载最多 10 分钟
  httpGet: {path: /health, port: 8000}
  periodSeconds: 10
  failureThreshold: 60           # 60 × 10s = 600s 窗口
livenessProbe:                   # 只测「进程是否卡死」，不测依赖
  httpGet: {path: /health, port: 8000}
  periodSeconds: 20
  failureThreshold: 3            # 最坏 60s 发现进程假死
readinessProbe:                  # 测「现在能否服务」，摘流量用
  httpGet: {path: /ready, port: 8000}
  periodSeconds: 5
  failureThreshold: 2            # 最坏 10s 摘除
  successThreshold: 1
terminationGracePeriodSeconds: 180   # ← 必须 > 最长一次生成的时间
lifecycle:
  preStop:
    exec: {command: ["sh", "-c", "sleep 5"]}   # 等端点传播（模块 01）"""),
        CALLOUT("warn", "探针配置有三个反复出现的错误。<strong>①探针超时太短</strong>：<code>timeoutSeconds</code> 默认只有 1 秒，而一个满载的 Python 服务在 GIL 争抢下可能 1.5 秒才响应健康检查 → 探针失败 → 被摘流量或重启 → <em>过载引发的重启风暴</em>。这是「越忙越挂」的经典正反馈。<strong>②liveness 和 readiness 指向同一个端点</strong>：过载时 readiness 该失败（摘流量、自我保护），但 liveness 跟着失败就会被重启，前功尽弃。<strong>③readiness 不检查队列深度</strong>：Pod 明明积压严重却仍在接流量，无法把压力反馈给负载均衡器。"),
    ])),
    ("resources", "资源模型：requests / limits 与 GPU 的特殊性", "".join([
        P("这是 K8s 里概念最微妙、也最容易配错的部分。两个数字，语义完全不同："),
        TABLE(["", "<code>requests</code>", "<code>limits</code>"], [
            ["含义", "<strong>调度依据</strong>：节点必须有这么多可分配资源才放得下", "<strong>运行时上限</strong>：cgroup 强制执行"],
            ["CPU 超了", "—", "被<strong>限流（throttle）</strong>，变慢但不死"],
            ["内存超了", "—", "被 <strong>OOMKilled</strong>，直接杀"],
            ["谁看它", "kube-scheduler", "kubelet / cgroup"],
        ]),
        P("两者的关系决定了 Pod 的 <span class=\"term\">QoS class</span>，而 QoS 决定了节点内存紧张时<strong>谁先被驱逐</strong>："),
        UL([
            "<strong>Guaranteed</strong>（requests == limits，且所有容器都设了）：最后被驱逐。<em>生产 LLM 服务应该都是这一档。</em>",
            "<strong>Burstable</strong>（requests &lt; limits）：中间档。适合能容忍被限流的批处理。",
            "<strong>BestEffort</strong>（什么都不设）：<strong>第一个被杀</strong>。绝不要在生产用。",
        ]),
        H3("GPU 的三个特殊之处"),
        P("GPU 在 K8s 里不是普通资源，它有三条你必须知道的规则，否则配置会以诡异的方式失败："),
        TABLE(["规则", "含义", "后果"], [
            ["<strong>① 整数、不可超卖</strong>", "<code>nvidia.com/gpu: 1</code>，不能写 <code>0.5</code>", "一张卡同时只服务一个 Pod（除非用 MIG/MPS/时间片）"],
            ["<strong>② requests 必须等于 limits</strong>", "K8s 对扩展资源（extended resource）强制此规则", "GPU Pod 天然是 Guaranteed QoS"],
            ["<strong>③ 显存不由 K8s 管</strong>", "K8s 只数「几张卡」，不知道你用了多少 GB 显存", "同卡多进程会互相 OOM；显存超限的表现是 CUDA OOM 而非 OOMKilled，K8s 完全看不见"],
        ]),
        CALLOUT("danger", "<p>规则 ③ 的后果值得展开：<strong>K8s 的资源模型对 GPU 显存是「盲」的</strong>。你在 Pod spec 里写 <code>nvidia.com/gpu: 1</code>，K8s 保证给你一整张卡，但它不知道你的 vLLM 把 <code>gpu_memory_utilization</code> 设成了 0.9 还是 0.5，也不会在你 OOM 时给出有意义的事件——你只会在容器日志里看到 <code>torch.cuda.OutOfMemoryError</code>，Pod 状态可能还是 <code>Running</code>（如果进程捕获了异常）或 <code>Error</code>。<em>显存规划必须在应用层做</em>：算清 权重 + 激活 + KV 缓存 的预算（C08/C24 的内容），把 <code>--gpu-memory-utilization</code> 显式设死，别指望 K8s 帮你兜底。</p>", "K8s 看不见显存"),
        P("最后一个常被忽略的资源：<strong><code>ephemeral-storage</code></strong>。模型权重下载到 <code>emptyDir</code> 会占节点磁盘，不声明的话节点磁盘被打满会触发 <em>DiskPressure</em>，kubelet 开始驱逐 Pod——而且驱逐的往往不是罪魁祸首。<code>requests.ephemeral-storage: 200Gi</code> 应该和 GPU 一起声明。"),
    ])),
    ("scheduling", "调度：装箱、亲和与碎片", "".join([
        P("调度器要回答一个简单的问题：<strong>这个 Pod 放哪台机器</strong>？它分两阶段做——先<span class=\"term\">过滤（filter）</span>掉放不下的节点，再对剩下的<span class=\"term\">打分（score）</span>选最高的。"),
        ASCII("""待调度 Pod: 需要 2 GPU, 16 CPU, 128Gi 内存

  阶段一：过滤（硬约束，不满足直接淘汰）
    节点A [8 GPU 空闲 4 | CPU 96 空闲 40]  ✓ 放得下
    节点B [8 GPU 空闲 1 | CPU 96 空闲 80]  ✗ GPU 不够
    节点C [8 GPU 空闲 6 | CPU 96 空闲 10]  ✗ CPU 不够
    节点D [8 GPU 空闲 8 | CPU 96 空闲 96]  ✓ 放得下
    还要过：nodeSelector / taint-toleration / 亲和性 / 拓扑约束 / 端口冲突

  阶段二：打分（软偏好，选分最高的）
    LeastAllocated（默认，偏向空的）  → 选 D  ← 均衡负载，但制造碎片
    MostAllocated（装箱，偏向满的）   → 选 A  ← 省节点，便于缩容
    ImageLocality（本地已有镜像加分）  → 看情况（模块 01 的冷启动杠杆）""")
        ,
        DUAL(
            "默认策略 <code>LeastAllocated</code>「优先放到最空的节点」，对普通 web 服务合理（分散风险），但对 GPU 集群<strong>往往是错的</strong>。因为它会让每台机器都用掉一点 GPU，产生大量<em>碎片</em>：8 台机器各剩 1 张卡，看起来还有 8 张卡空闲，但一个需要 2 卡的任务哪儿都放不下。GPU 集群通常应该用 <code>MostAllocated</code>（装箱），把任务挤到少数节点，留出完整的空节点。",
            "形式化：这是经典的<span class=\"term\">向量装箱（vector bin packing）</span>问题，NP-hard。K8s 用的是在线贪心（Pod 一个个来，来了就决定，不回溯）。在线贪心的竞争比有理论下界，实践中 <em>first-fit-decreasing</em>（按需求降序放第一个装得下的）通常接近最优。这解释了一条重要的运维经验：<strong>大 Pod 应该先调度</strong>——用 <code>PriorityClass</code> 给大任务更高优先级，否则一堆小 Pod 先把每台机器都占一点，大任务就永远排不进去（这叫 <em>resource stranding</em>，资源搁浅）。",
        ),
        TABLE(["调度工具", "作用", "LLM 场景用法"], [
            ["<code>nodeSelector</code> / <code>nodeAffinity</code>", "把 Pod 限制到某类节点", "只调度到有 A100/H100 标签的节点"],
            ["<code>taint</code> / <code>toleration</code>", "节点主动排斥 Pod，除非 Pod 明确容忍", "GPU 节点打 taint，防止普通 Pod 占用宝贵机器"],
            ["<code>podAntiAffinity</code>", "同类 Pod 尽量/必须分散", "同一服务的副本分散到不同节点，避免单机故障全灭"],
            ["<code>topologySpreadConstraints</code>", "跨可用区/机架均匀分布", "跨 AZ 均分副本，抗单区故障"],
            ["<code>PriorityClass</code> + 抢占", "高优先级 Pod 可驱逐低优先级", "在线推理抢占离线批处理的 GPU"],
            ["<code>PodDisruptionBudget</code>", "自愿驱逐时至少保留 N 个可用", "节点维护/缩容时不至于把服务全摘掉"],
        ]),
        CALLOUT("intuition", "<code>podAntiAffinity</code> 与装箱是<strong>直接冲突</strong>的：前者要分散、后者要集中。怎么选？<em>看你在防什么</em>。防单机故障 → 反亲和（副本分散）；防资源碎片 → 装箱。生产上的常见折中是「<strong>软反亲和 + 拓扑分布</strong>」：要求跨可用区均匀（硬约束，防区域故障），但同区内允许装箱（软偏好，省钱）。这个组合几乎是大规模 GPU 服务的标配。"),
    ])),
    ("stateful", "有状态与配置：什么时候 Deployment 不够用", "".join([
        P("无状态推理服务用 Deployment 就够了。但有三类情况需要别的东西，值得知道边界在哪。"),
        TABLE(["场景", "用什么", "为什么"], [
            ["单副本推理（无状态）", "<strong>Deployment</strong>", "Pod 可随意替换，名字/身份无所谓"],
            ["多节点张量并行的一个模型实例", "<strong>StatefulSet</strong> 或 <strong>LeaderWorkerSet</strong>", "各 rank 需要<em>稳定的网络标识</em>（<code>pod-0</code>、<code>pod-1</code>）才能互相发现并建立通信组"],
            ["离线批量推理 / 评测作业", "<strong>Job</strong> / <strong>CronJob</strong>", "跑完就结束，要的是「完成」而非「常驻」（模块 05 详述）"],
            ["每节点一个的守护进程", "<strong>DaemonSet</strong>", "GPU driver 插件、日志采集、<em>模型权重预热缓存</em>（模块 01）"],
        ]),
        P("<strong>多节点推理</strong>是 LLM 特有的、Deployment 处理不了的场景：一个 405B 模型需要跨 2 台 8 卡机做张量并行，这 16 个进程<em>共同构成一个副本</em>，必须一起启动、一起就绪、一起销毁，还要能互相寻址。用 Deployment 的话，16 个 Pod 是互相独立的，K8s 不知道它们是一个整体（挂一个应该重启全部）。社区为此发展出了 <code>LeaderWorkerSet</code> 这类抽象。"),
        H3("配置与密钥"),
        P("模块 01 的运行时契约第 ⑤ 条要求配置外置。K8s 提供两个载体，用法上有几条硬规矩："),
        UL([
            "<strong>ConfigMap 改了不会自动重启 Pod</strong>。挂载为文件时内容<em>会</em>更新（有 kubelet 同步延迟，约 1 分钟），但作为环境变量注入的<em>不会</em>。想让配置变更触发滚动更新，标准做法是把 ConfigMap 的哈希写进 Pod 模板的 annotation。",
            "<strong>Secret 默认只是 base64，不是加密</strong>。必须启用 etcd 静态加密（<code>EncryptionConfiguration</code>），或用外部密钥管理（External Secrets Operator + Vault/KMS）。<em>base64 不是安全措施，只是编码</em>。",
            "<strong>永远不要把密钥写进镜像或 Git</strong>。这条听起来是废话，但 registry 里的历史层是永久可读的——一次误提交，删了也还在。",
        ]),
        CALLOUT("warn", "还有一个 LLM 特有的配置问题：<strong>模型版本应该放哪</strong>？放 ConfigMap 里（不触发重启）会导致「配置说是 v3，Pod 里跑的还是 v2」；正确做法是把模型标识<em>放进 Pod 模板</em>（环境变量或 initContainer 参数），这样改它就<strong>天然触发一次滚动更新</strong>——把「换模型」变成一次可灰度、可回滚的标准发布，而不是一次神秘的热更新。这是把模块 04 的所有安全网都用上的前提。"),
    ])),
    ("ledger", "算一笔账：副本数、装箱率与碎片", "".join([
        P("把本模块的决策换算成钱。假设 8 卡节点、每副本 2 卡，需要 13 个副本（来自模块 02 的容量规划）。"),
        MATH("N_{nodes} = \\left\\lceil \\frac{R \\cdot g}{G_{node}} \\right\\rceil \\text{（理想装箱）}, \\qquad \\eta = \\frac{R \\cdot g}{N_{nodes} \\cdot G_{node}}"),
        TABLE(["策略", "节点数", "装箱率 η", "月成本（$32/节点·h）", "抗单机故障"], [
            ["理想装箱（每节点 4 副本）", "⌈26/8⌉ = 4", "26/32 = 81%", "$92,160", "一台挂 = 少 4/13 容量"],
            ["硬反亲和（每节点 1 副本）", "13", "26/104 = 25%", "$299,520", "一台挂 = 少 1/13 容量"],
            ["跨 3 AZ 均分 + 区内装箱", "6", "26/48 = 54%", "$138,240", "一区挂 = 少 1/3 容量"],
        ]),
        P("读这张表的方式：<strong>硬反亲和的可用性是用 3.25 倍的成本买来的</strong>。这笔交易值不值，取决于你的 SLO 和单机故障率。如果单机年故障率 2%、13 台机器中一台挂了导致 8% 容量损失、恢复 10 分钟——这点错误预算消耗，远远不值 20 万美元/月的溢价。<em>中间那行（跨 AZ + 区内装箱）几乎总是正确答案</em>。"),
        P("再算碎片这笔账。假设集群 20 个节点、每节点 8 卡，混跑 1 卡/2 卡/4 卡三种任务。用 <code>LeastAllocated</code>（分散）时，每个节点都会被占用一部分，剩余量分散成很多个 1–3 卡的空隙；一个新来的 4 卡任务可能<strong>整个集群都放不下，尽管总空闲有 30 张卡</strong>。用 <code>MostAllocated</code>（装箱）则会留出完整的空节点。notebook 会把这两种策略都实现，量化「总空闲卡数」与「最大可容纳任务」的差距——你会看到后者可以相差好几倍。"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>K8s 不是一个「运行容器的地方」，而是一组把你的意图持续变成现实的控制循环；你的全部工作是把意图表达清楚（spec）并让系统能观测到现实（探针与指标）</strong>。意图表达不清（探针语义混淆、资源没声明）或现实观测不到（没有 readiness、没有队列深度指标），控制循环就会朝着错误的方向努力——<em>而且非常勤奋地努力</em>。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>GPU 的细粒度共享</strong>：MIG（硬件切分，隔离好但粒度固定）、MPS（进程共享，无隔离）、时间片（K8s device plugin 的 <code>timeSlicing</code>，无显存隔离）各有取舍，都不理想。让 K8s 原生理解「显存 GB」而不只是「几张卡」，是社区长期诉求（DRA / Dynamic Resource Allocation 正在推进），但显存的动态性（KV 缓存随负载涨缩）让静态声明本身就不合适。",
            "<strong>多节点推理的一等公民抽象</strong>：LeaderWorkerSet、Ray Serve、Kubernetes JobSet 都在尝试表达「一组 Pod 构成一个逻辑副本」。gang scheduling（要么全调度、要么都不调度，避免部分启动死锁）在 K8s 默认调度器里仍需靠 Volcano/Koordinator 等插件补齐。",
            "<strong>拓扑感知调度</strong>：多节点推理对网络拓扑极度敏感（同机架 NVLink/InfiniBand vs 跨机架以太网，带宽差一个数量级）。让调度器理解 NUMA、PCIe 拓扑、网络亲和性，把一个模型的各 rank 放到物理上最近的位置，仍是活跃工程方向。",
            "<strong>调度器的目标函数之争</strong>：装箱率、公平性、优先级、能耗、碳强度——这些目标互相冲突且没有公认权重。多目标在线调度的理论保证与实践算法都还很粗糙。",
            "<strong>推理专用的编排层</strong>：KServe、Ray Serve、vLLM production stack、Kubernetes Gateway API Inference Extension 都在做「比 Deployment 更懂 LLM」的抽象（模型版本、KV 缓存亲和路由、prefill/decode 分池）。标准尚未收敛，是当前变化最快的一层。",
        ]),
        CALLOUT("paper", "必读：Kubernetes 官方文档的 <em>Pod Lifecycle</em>、<em>Configure Liveness, Readiness and Startup Probes</em>、<em>Resource Management for Pods and Containers</em>、<em>Assigning Pods to Nodes</em>（这四篇是本模块的一手来源，写得远好于大多数二手教程）；Verma et al. 2015 <em>Large-scale cluster management at Google with Borg</em>（K8s 的思想源头，尤其调度与优先级）；Burns et al. 2016 <em>Borg, Omega, and Kubernetes</em>（三代设计的取舍复盘）；Coffman et al. 的 bin packing 综述（装箱的理论边界）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · Kubernetes 编排（把控制循环、探针状态机与调度器从零写出来）

目标：把 **reconcile 控制循环 → 探针状态机 → 端点管理 → 装箱调度 → 碎片量化** 从零实现，
每个机制都**对拍**朴素参考、每个策略都**算一笔账**。

路线：Deployment 控制器 → 探针 FSM（三种探针的时序）→ 端点控制器与流量摘除 → first-fit/best-fit/装箱 → 碎片 vs 反亲和 → ✏️ 练习 → 📖 答案 → 🧪 集群成本胶囊。

> 心智模型：**K8s = 一堆水平触发的幂等控制循环 + 一个装箱调度器**。
> 本环境没有集群，但这两样东西的全部逻辑都是纯计算。"""),
    md("""## 1 · 控制循环：水平触发为什么能容错

模块 00 写过最小 reconcile。这里加上**水平触发（level-triggered）**的关键性质验证：
控制器**只看当前状态、不看事件历史**，所以丢消息、重复、乱序都不会让它错位。

对照组是**边沿触发（edge-triggered）**：「收到创建事件就创建」——丢一条就永久错位。"""),
    code("""import math, random, heapq
from dataclasses import dataclass, field

def level_triggered(current_count, desired, events_lost=0):
    '''水平触发：无视事件，只比较状态。'''
    return desired - current_count            # 直接算差量

def edge_triggered(current_count, event_queue):
    '''边沿触发：按事件逐条响应。丢事件 = 永久错位。'''
    delta = 0
    for ev in event_queue:
        delta += 1 if ev == 'scale_up' else -1
    return delta

DESIRED = 5
# 场景：期望从 0 扩到 5，但有 2 条事件在网络里丢了
events = ['scale_up'] * 5
lossy  = events[:3]                            # 丢了 2 条

lt = level_triggered(0, DESIRED)
et = edge_triggered(0, lossy)
print(f'水平触发算出要创建 {lt} 个 | 边沿触发（丢2条）算出 {et} 个')
assert lt == 5, '水平触发不受丢消息影响'
assert et == 3, '边沿触发丢了 2 条就永久少 2 个'

# 重复投递同样安全
assert level_triggered(0, DESIRED) == level_triggered(0, DESIRED), '幂等：重放安全'
assert edge_triggered(0, events + events) == 10, '边沿触发重复投递会翻倍！'
print('✅ 水平触发对「丢失/重复/乱序」全免疫 —— 这是 K8s 所有控制器的基石')"""),
    md("""### 多个控制器协作：Deployment → ReplicaSet → Pod

真实 K8s 是**多层循环**：Deployment 管 ReplicaSet，ReplicaSet 管 Pod。
每层独立、异步、最终一致。下面把两层串起来，验证整体仍然收敛。"""),
    code("""@dataclass
class Pod:
    name: str
    rs: str
    phase: str = 'Pending'      # Pending -> Running
    ready: bool = False

class Cluster:
    def __init__(self):
        self.pods, self.rs_desired, self._n = [], {}, 0
    # ── ReplicaSet 控制器 ──
    def rs_reconcile(self):
        acts = []
        for rs, want in self.rs_desired.items():
            have = [p for p in self.pods if p.rs == rs]
            for _ in range(want - len(have)):
                self._n += 1
                self.pods.append(Pod(f'pod-{self._n}', rs)); acts.append(('create', rs))
            for p in have[want:]:
                self.pods.remove(p); acts.append(('delete', p.name))
        return acts
    # ── kubelet：把 Pending 推进到 Running/Ready ──
    def kubelet_tick(self):
        for p in self.pods:
            if p.phase == 'Pending':   p.phase = 'Running'
            elif not p.ready:          p.ready = True

c = Cluster()
c.rs_desired = {'rs-v1': 3}
trace = []
for _ in range(4):
    c.rs_reconcile(); c.kubelet_tick()
    trace.append((len(c.pods), sum(p.ready for p in c.pods)))
print('(总数, ready 数) 演化:', trace)
assert trace[-1] == (3, 3), '两层循环最终都收敛'
# 关键：总数先到位，ready 后到位 —— 最终一致，不是原子
assert trace[0][0] == 3 and trace[0][1] == 0, '第一轮 Pod 已创建但还没 ready'
print('✅ 「Pod 存在」≠「Pod 就绪」≠「流量已切过去」—— 每一跳都是独立循环')"""),
    md("""## 2 · 探针状态机：三种探针的时序契约

**startupProbe 成功之前，liveness 与 readiness 都不执行。** 这条契约是 LLM 服务的救命稻草：
没有它，慢启动的模型会被 liveness 反复杀死，陷入永远加载不完的重启死循环。"""),
    code("""@dataclass
class ProbeCfg:
    period: int
    failure_threshold: int
    initial_delay: int = 0

@dataclass
class PodRuntime:
    load_seconds: int                 # 模型加载需要多久
    t: int = 0
    started: bool = False
    alive: bool = True
    ready: bool = False
    restarts: int = 0
    startup_fails: int = 0
    live_fails: int = 0

def tick(pod, startup: ProbeCfg, live: ProbeCfg, ready: ProbeCfg, use_startup=True):
    '''推进 1 秒，执行探针语义。返回本秒发生的事件。'''
    pod.t += 1
    loaded = pod.t >= pod.load_seconds
    ev = None
    if use_startup and not pod.started:
        if pod.t % startup.period == 0:
            if loaded:
                pod.started = True; ev = 'startup-ok'
            else:
                pod.startup_fails += 1
                if pod.startup_fails >= startup.failure_threshold:
                    ev = 'RESTART(startup)'; pod.restarts += 1
                    pod.t = 0; pod.startup_fails = 0
        return ev
    # startup 已通过（或未启用）：liveness + readiness 生效
    if pod.t % live.period == 0:
        if loaded:  pod.live_fails = 0
        else:
            pod.live_fails += 1
            if pod.live_fails >= live.failure_threshold:
                ev = 'RESTART(liveness)'; pod.restarts += 1
                pod.t = 0; pod.live_fails = 0; pod.started = False
                return ev
    if pod.t % ready.period == 0:
        pod.ready = loaded
    return ev

LOAD = 180      # 模型加载 3 分钟
S = ProbeCfg(period=10, failure_threshold=60)     # 600s 启动窗口
L = ProbeCfg(period=20, failure_threshold=3)      # 60s 发现假死
R = ProbeCfg(period=5,  failure_threshold=2)

# 情况 A：正确配置（有 startupProbe）
a = PodRuntime(load_seconds=LOAD)
for _ in range(400): tick(a, S, L, R, use_startup=True)
print(f'有 startupProbe : 重启 {a.restarts} 次, ready={a.ready}')
assert a.restarts == 0 and a.ready, '正确配置下应零重启并最终就绪'

# 情况 B：没有 startupProbe，liveness 直接生效
b = PodRuntime(load_seconds=LOAD)
for _ in range(400): tick(b, S, L, R, use_startup=False)
print(f'无 startupProbe : 重启 {b.restarts} 次, ready={b.ready}')
assert b.restarts >= 3, '没有 startupProbe，慢启动模型会被反复杀死'
assert not b.ready, '陷入重启死循环，永远加载不完'
print('\\n✅ 这就是「模型越大越起不来」的真实原因 —— 不是模型的问题，是探针配置的问题')"""),
    md("""### readiness 决定流量：端点控制器

**Service 的端点列表 = 所有 ready 的 Pod。** 这就是 readiness 的全部意义。
下面把端点控制器写出来，复现模块 02 提到的头号事故：readiness 恒返回 200。"""),
    code("""def endpoints(pods):
    '''端点控制器：只收录 ready 的 Pod。'''
    return [p.name for p in pods if p.ready and p.phase == 'Running']

def route(pods, n_requests, rng):
    '''把请求分给端点；打到未就绪 Pod 的请求全部失败。'''
    eps = endpoints(pods)
    if not eps:
        return 0, n_requests            # 无端点：全部失败（503）
    ok = fail = 0
    for _ in range(n_requests):
        target = rng.choice([p for p in pods if p.name in eps])
        if target.ready: ok += 1
        else:            fail += 1
    return ok, fail

rng = random.Random(0)
# 正确：readiness 反映真实状态
good_pods = [Pod('p1','rs',phase='Running',ready=True),
             Pod('p2','rs',phase='Running',ready=False)]   # p2 还在加载
ok, fail = route(good_pods, 1000, rng)
assert fail == 0 and ok == 1000, '未就绪的 p2 不在端点里，流量全部安全'
print(f'正确 readiness: 端点 {endpoints(good_pods)} -> 成功 {ok}, 失败 {fail}')

# 错误：readiness 恒 200（图省事），未加载完的 Pod 也进端点
class FakeReadyPod(Pod):
    pass
bad_pods = [Pod('p1','rs',phase='Running',ready=True),
            Pod('p2','rs',phase='Running',ready=True)]     # ← 谎报就绪
actually_loaded = {'p1': True, 'p2': False}
eps = endpoints(bad_pods)
ok = sum(1 for _ in range(1000) if actually_loaded[rng.choice(eps)])
print(f'错误 readiness: 端点 {eps} -> 成功 {ok}/1000 (约一半请求打到未加载的 Pod)')
assert 400 < ok < 600, '约一半流量会失败'
print('\\n✅ 复现了 LLM 部署的头号事故：Pod 全是 Running，监控一切正常，服务半死不活')"""),
    md("""## 3 · 调度器：过滤 + 打分 + 装箱

调度 = **过滤**（硬约束）+ **打分**（软偏好）。
下面实现两种打分策略，量化它们对**碎片**的影响。"""),
    code("""@dataclass
class Node:
    name: str
    gpu: int; cpu: int; mem: int
    used_gpu: int = 0; used_cpu: int = 0; used_mem: int = 0
    zone: str = 'a'
    def free(self):  return (self.gpu-self.used_gpu, self.cpu-self.used_cpu, self.mem-self.used_mem)
    def fits(self, req):
        f = self.free(); return all(f[i] >= req[i] for i in range(3))
    def place(self, req):
        self.used_gpu += req[0]; self.used_cpu += req[1]; self.used_mem += req[2]

def schedule(nodes, req, policy='least'):
    '''返回被选中的节点，或 None。'''
    feasible = [n for n in nodes if n.fits(req)]          # 阶段一：过滤
    if not feasible: return None
    def score(n):                                          # 阶段二：打分
        used_ratio = n.used_gpu / n.gpu if n.gpu else 0
        return -used_ratio if policy == 'least' else used_ratio
    return max(feasible, key=score)

def make_cluster(n_nodes=20):
    return [Node(f'n{i}', gpu=8, cpu=96, mem=768, zone='abc'[i % 3]) for i in range(n_nodes)]

# 混合负载：大量 1 卡小任务 + 少量 4 卡大任务
rng = random.Random(7)
workload = [(1, 8, 64)] * 60 + [(2, 16, 128)] * 10

results = {}
for policy in ['least', 'most']:
    nodes = make_cluster()
    placed = 0
    for req in workload:
        n = schedule(nodes, req, policy)
        if n: n.place(req); placed += 1
    total_free_gpu = sum(n.free()[0] for n in nodes)
    max_contiguous = max(n.free()[0] for n in nodes)       # 最大的单节点空闲
    empty_nodes = sum(1 for n in nodes if n.used_gpu == 0)
    results[policy] = (placed, total_free_gpu, max_contiguous, empty_nodes)
    print(f'{policy:>6s}: 放置 {placed}/{len(workload)}, 总空闲 {total_free_gpu} GPU, '
          f'最大单节点空闲 {max_contiguous}, 完整空节点 {empty_nodes}')

assert results['most'][3] > results['least'][3], '装箱策略应留下更多完整空节点'
assert results['most'][2] >= results['least'][2], '装箱策略的最大连续空闲应不小于分散策略'
print('\\n✅ 两种策略总空闲卡数可能相同，但「能不能放下一个 8 卡任务」天差地别 —— 这就是碎片')"""),
    md("""### 碎片的代价：总空闲 30 张卡，却放不下一个 4 卡任务"""),
    code("""def can_place(nodes, req):
    return any(n.fits(req) for n in nodes)

for policy in ['least', 'most']:
    nodes = make_cluster()
    for req in workload:
        n = schedule(nodes, req, policy)
        if n: n.place(req)
    free = sum(n.free()[0] for n in nodes)
    print(f'{policy:>6s} 策略, 总空闲 {free} GPU:')
    for size in [1, 2, 4, 8]:
        ok = can_place(nodes, (size, size*8, size*64))
        print(f'    还能放下 {size} 卡任务? {"✅" if ok else "❌ 放不下（碎片）"}')

nodes_least = make_cluster()
for req in workload:
    n = schedule(nodes_least, req, 'least')
    if n: n.place(req)
nodes_most = make_cluster()
for req in workload:
    n = schedule(nodes_most, req, 'most')
    if n: n.place(req)
assert can_place(nodes_most, (8, 64, 512)), '装箱策略应仍能放下整节点任务'
print('\\n✅ 「集群还有 30 张卡空闲」和「能不能跑一个 8 卡任务」是两个完全不同的问题。')
print('   GPU 集群默认的 LeastAllocated 往往是错的 —— 它优化的是均衡，不是可用性。')"""),
    md("""### 大 Pod 优先：避免资源搁浅（resource stranding）

在线贪心装箱有个经典结论：**按需求降序放置（first-fit-decreasing）接近最优**。
反过来，小任务先来会把每台机器都占一点，大任务永远排不进去。"""),
    code("""def run_order(order_workload, policy='least'):     # 'least' 是 K8s 的默认打分策略
    nodes = make_cluster(10)
    placed = []
    for req in order_workload:
        n = schedule(nodes, req, policy)
        if n: n.place(req); placed.append(req)
    return len(placed), len(order_workload)

mixed = [(1,8,64)] * 30 + [(8,64,512)] * 5        # 30 个 1 卡 + 5 个整节点任务
small_first = mixed
big_first   = sorted(mixed, key=lambda r: -r[0])   # FFD：按需求降序

p_small, tot = run_order(small_first)
p_big,   _   = run_order(big_first)
print(f'小任务先来 (随到随调度): 放下 {p_small}/{tot}')
print(f'大任务先来 (FFD/优先级): 放下 {p_big}/{tot}')
assert p_big > p_small, 'FFD 应放下更多任务'
print(f'\\n✅ 同样的负载、同样的集群，只是顺序不同 -> 多放下 {p_big-p_small} 个任务。')
print('   这就是 PriorityClass 存在的理由：让大任务先决定位置。')"""),
    md("""## ✏️ 练习 1：QoS class 判定

实现 `qos_class(containers)`：`containers` 是 `[{'req': {...}, 'lim': {...}}, ...]`。
规则（K8s 原文语义）：
- 所有容器的**所有**资源都设了 requests 且 requests == limits → `'Guaranteed'`
- 所有容器**都没设**任何 requests 和 limits → `'BestEffort'`
- 其余 → `'Burstable'`"""),
    code("""def qos_class(containers):
    # TODO: 按上述三条规则返回 'Guaranteed' / 'Burstable' / 'BestEffort'
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
g = [{'req': {'cpu': 4, 'memory': 8}, 'lim': {'cpu': 4, 'memory': 8}}]
b = [{'req': {'cpu': 2, 'memory': 4}, 'lim': {'cpu': 4, 'memory': 8}}]
e = [{'req': {}, 'lim': {}}]
mixed = [{'req': {'cpu': 4}, 'lim': {'cpu': 4}}, {'req': {}, 'lim': {}}]
assert qos_class(g) == 'Guaranteed'
assert qos_class(b) == 'Burstable'
assert qos_class(e) == 'BestEffort'
assert qos_class(mixed) == 'Burstable', '只要有一个容器不满足，整个 Pod 就降档'
# 只设了 cpu 没设 memory -> 不是 Guaranteed
partial = [{'req': {'cpu': 4}, 'lim': {'cpu': 4, 'memory': 8}}]
assert qos_class(partial) == 'Burstable'
print('✅ 练习 1 通过：生产 LLM 服务必须是 Guaranteed（requests == limits 且都设全）')"""),
    md("""## ✏️ 练习 2：拓扑均匀分布

实现 `spread_place(nodes, n_replicas, req, max_skew=1)`：
把 `n_replicas` 个副本放到 `nodes` 上，要求**各 zone 的副本数最大差值 ≤ max_skew**
（K8s 的 `topologySpreadConstraints`）。每次挑「当前副本数最少的 zone 里、能放下的、已用最多的节点」（区内装箱）。
返回被选中的节点名列表；放不下就跳过该副本。"""),
    code("""def spread_place(nodes, n_replicas, req, max_skew=1):
    # TODO: 维护 per-zone 计数；每轮挑计数最小的 zone；
    #       在该 zone 内选 fits 且 used_gpu 最大的节点（区内装箱）；放不下则试下一个 zone
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
ns = make_cluster(9)                 # 9 节点，zone a/b/c 各 3 个
chosen = spread_place(ns, 6, (2, 16, 128))
assert len(chosen) == 6, f'应放下 6 个副本，实际 {len(chosen)}'
byzone = {}
for name in chosen:
    z = next(n.zone for n in ns if n.name == name)
    byzone[z] = byzone.get(z, 0) + 1
print('各 zone 副本数:', byzone)
assert max(byzone.values()) - min(byzone.values()) <= 1, f'zone 间偏斜应 ≤1，实际 {byzone}'
assert len(byzone) == 3, '应铺满 3 个 zone'
# 区内装箱：使用中的节点数应少于副本数（说明有节点放了 >1 个副本）
used_nodes = len(set(chosen))
assert used_nodes <= 6
print(f'✅ 练习 2 通过：跨 AZ 均匀（防区域故障）+ 区内装箱（省钱），用了 {used_nodes} 个节点')"""),
    md("""## ✏️ 练习 3：PodDisruptionBudget

实现 `can_evict(total, ready, min_available)`：节点维护时要驱逐一个 Pod，
只有在**驱逐后仍满足 `ready - 1 >= min_available`** 时才允许。返回 bool。
再实现 `drain_node(pods_on_node, total, ready, min_available)`：
按顺序尝试驱逐，返回**实际能驱逐的个数**。"""),
    code("""def can_evict(total, ready, min_available):
    # TODO
    raise NotImplementedError

def drain_node(pods_on_node, total, ready, min_available):
    # TODO: 逐个尝试；每成功驱逐一个，ready 减 1
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert can_evict(total=10, ready=10, min_available=8) is True
assert can_evict(total=10, ready=8,  min_available=8) is False, '已到下限，不能再驱逐'
n = drain_node(pods_on_node=4, total=10, ready=10, min_available=8)
assert n == 2, f'10 个 ready、下限 8 -> 只能驱逐 2 个，得到 {n}'
n2 = drain_node(pods_on_node=4, total=10, ready=10, min_available=10)
assert n2 == 0, 'min_available == 副本数 -> 一个都不能驱逐（节点永远排空不了！）'
print('✅ 练习 3 通过：PDB 保护可用性，但设得太严会让节点维护永远卡住')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def qos_class(containers):
    all_empty = all(not c['req'] and not c['lim'] for c in containers)
    if all_empty:
        return 'BestEffort'
    guaranteed = True
    for c in containers:
        req, lim = c['req'], c['lim']
        if not req or not lim or set(req) != set(lim) or any(req[k] != lim[k] for k in req):
            guaranteed = False; break
    return 'Guaranteed' if guaranteed else 'Burstable'"""),
    code("""# 练习 2 参考答案
def spread_place(nodes, n_replicas, req, max_skew=1):
    zones = sorted({n.zone for n in nodes})
    count = {z: 0 for z in zones}
    chosen = []
    for _ in range(n_replicas):
        placed = False
        for z in sorted(zones, key=lambda z: count[z]):
            cand = [n for n in nodes if n.zone == z and n.fits(req)]
            if not cand:
                continue
            node = max(cand, key=lambda n: n.used_gpu)      # 区内装箱
            node.place(req); count[z] += 1; chosen.append(node.name); placed = True
            break
        if not placed:
            break
    return chosen"""),
    code("""# 练习 3 参考答案
def can_evict(total, ready, min_available):
    return ready - 1 >= min_available

def drain_node(pods_on_node, total, ready, min_available):
    evicted = 0
    for _ in range(pods_on_node):
        if not can_evict(total, ready, min_available):
            break
        ready -= 1; evicted += 1
    return evicted"""),
    md("""---
## 🧪 真实数据胶囊：反亲和的溢价到底值不值

把「装箱 vs 反亲和 vs 跨 AZ 折中」三种策略的成本与可用性放在一起算。
（公开量级：8 卡节点 $32/h；单机年故障率 ~2%；恢复 10 分钟。）"""),
    code("""REPLICAS, GPU_PER_REPLICA, GPU_PER_NODE, NODE_HOURLY = 13, 2, 8, 32.0
ANNUAL_NODE_FAILURE, MTTR_MIN = 0.02, 10.0

def strategy_cost(nodes_needed, replicas_per_node):
    monthly = nodes_needed * NODE_HOURLY * 24 * 30
    packing = REPLICAS * GPU_PER_REPLICA / (nodes_needed * GPU_PER_NODE)
    capacity_loss = replicas_per_node / REPLICAS          # 一台机器挂了损失多少容量
    # 年期望不可用分钟（按容量损失折算）
    expected_min = nodes_needed * ANNUAL_NODE_FAILURE * MTTR_MIN * capacity_loss
    return monthly, packing, capacity_loss, expected_min

strategies = [
    ('理想装箱 (4 副本/节点)',  math.ceil(REPLICAS / 4), 4),
    ('跨3AZ + 区内装箱',        6,                       3),
    ('硬反亲和 (1 副本/节点)',  REPLICAS,                1),
]
print(f"{'策略':<24s} {'节点':>5s} {'装箱率':>7s} {'单机故障损失':>12s} {'月成本$':>10s} {'年期望损失分钟':>14s}")
rows = []
for name, nodes, rpn in strategies:
    m, pk, cl, em = strategy_cost(nodes, rpn)
    rows.append((name, nodes, m, em))
    print(f'{name:<24s} {nodes:>5d} {pk:>7.0%} {cl:>11.1%} {m:>10,.0f} {em:>14.2f}')

cheap, mid, expensive = rows[0][2], rows[1][2], rows[2][2]
loss_cheap, loss_expensive = rows[0][3], rows[2][3]
premium = expensive - cheap
saved_min = loss_cheap - loss_expensive
print(f'\\n硬反亲和比装箱贵 ${premium:,.0f}/月，换来年期望少损失 {saved_min:.2f} 分钟')
print(f'折合每减少 1 分钟年不可用，要花 ${premium*12/max(saved_min,1e-9):,.0f}')
assert expensive > 3 * cheap, '硬反亲和的溢价超过 3 倍'
assert mid < expensive, '跨 AZ 折中应显著便宜于硬反亲和'
print('\\n✅ 结论：硬反亲和的溢价通常不划算；「跨 AZ 均分 + 区内装箱」几乎总是正确答案。')"""),
    md("""**🧪 胶囊练习**：实现 `fragmentation(nodes)`：返回 `(总空闲GPU, 最大可容纳的单任务GPU数, 碎片率)`。
碎片率定义为 `1 - 最大可容纳 / 总空闲`（总空闲为 0 时返回 0.0）。"""),
    code("""def fragmentation(nodes):
    # TODO: total = Σ 各节点空闲 GPU；largest = max(各节点空闲 GPU)
    #       frag = 0.0 if total == 0 else 1 - largest / total
    raise NotImplementedError"""),
    code("""# 自测
ns = make_cluster(4)
for n in ns: n.place((7, 8, 64))            # 每节点占 7 卡，各剩 1 卡
total, largest, frag = fragmentation(ns)
assert total == 4 and largest == 1, (total, largest)
assert abs(frag - 0.75) < 1e-9, f'4 张空闲卡分散在 4 台机器上，碎片率应为 0.75，得到 {frag}'

ns2 = make_cluster(4)
ns2[0].place((8, 8, 64)); ns2[1].place((8, 8, 64)); ns2[2].place((8, 8, 64))
total2, largest2, frag2 = fragmentation(ns2)
assert total2 == 8 and largest2 == 8 and frag2 == 0.0, '集中在一台机器 -> 零碎片'
print(f'分散: 空闲 {total}, 最大 {largest}, 碎片率 {frag:.0%}')
print(f'装箱: 空闲 {total2}, 最大 {largest2}, 碎片率 {frag2:.0%}')
print('✅ 胶囊练习通过：同样 4~8 张空闲卡，碎片率决定了「能不能真的用上」')"""),
    code("""# 📖 胶囊参考答案
def fragmentation(nodes):
    frees = [n.free()[0] for n in nodes]
    total, largest = sum(frees), max(frees) if frees else 0
    return total, largest, (0.0 if total == 0 else 1 - largest / total)"""),
    md("""---
## 🔧 旁注：真实系统里这些对应什么

- **水平触发控制循环** → controller-runtime 的 `Reconcile(ctx, req)`；你写 Operator 时实现的就是这个函数。
- **探针状态机** → kubelet 的 prober manager；`kubectl describe pod` 里的 `Liveness/Readiness/Startup` 行与 `Events` 里的 `Unhealthy`。
- **端点控制器** → EndpointSlice controller；`kubectl get endpointslices` 能直接看到「谁在接流量」。排查「Pod Running 但没流量」第一步就看这个。
- **过滤+打分调度** → kube-scheduler 的 Filter/Score 插件框架；`NodeResourcesFit` 的 `scoringStrategy` 就是 `LeastAllocated`/`MostAllocated` 的开关。
- **FFD / 大 Pod 优先** → `PriorityClass` + 抢占；GPU 集群常配 Volcano/Koordinator 做 gang scheduling。
- **PDB** → `PodDisruptionBudget`；`kubectl drain` 卡住十有八九是 PDB 设得太严。

你在这里写的调度器只有几十行，但它和 kube-scheduler 的**结构**是一致的：过滤、打分、选最高分。差别在插件数量，不在思想。"""),
    md("""### 小结
- K8s 的核心只有一个：**水平触发的幂等控制循环**。它对丢消息/重复/乱序免疫，代价是**一切最终一致**。
- 对象是层层包裹的：Ingress → Service（端点=ready 的 Pod）→ Deployment → ReplicaSet → Pod → Node。
- **三种探针各管一段**：startupProbe 是 LLM 慢启动的救命稻草；liveness 只测自己；readiness 决定流量。
- **资源模型对 GPU 显存是盲的**：K8s 只数卡，显存预算必须在应用层算死。生产 Pod 应为 Guaranteed QoS。
- **调度是在线向量装箱**：GPU 集群默认的 LeastAllocated 制造碎片；大 Pod 优先（FFD）能显著提高放置率。
- 硬反亲和的可用性溢价通常不划算，**跨 AZ 均分 + 区内装箱**是标准答案。

下一站：**模块 04 · 发布策略与自动扩缩** —— 集群会自愈了，但「换个版本」和「流量涨十倍」还是两件会出事的事。"""),
]
