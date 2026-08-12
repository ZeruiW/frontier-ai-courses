# -*- coding: utf-8 -*-
"""C48 模块 02 · 推理服务 API：契约、流式与容量。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–01、HTTP 基础、一点点概率（泊松过程/指数分布）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_serving_api.ipynb'),
    ("核心参考", "OpenAI Chat Completions API、SSE (RFC 8895 起草稿/WHATWG)、vLLM OpenAI server、排队论 Erlang-C"),
    ("预计时长", "读 60 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("boundary", "服务边界：一个 LLM 服务到底该暴露什么", "".join([
        P("镜像有了，进程能跑了。现在要回答一个看起来很平淡、实际决定了后面一切的问题：<strong>这个服务对外长什么样</strong>？"),
        P("很多人以为这只是「写个 HTTP 接口」。但服务边界（<span class=\"term\">service contract</span>）是整个部署链路上<strong>最难改</strong>的东西——镜像可以天天重建，K8s 配置可以随时改，但一旦有客户端接了你的 API，改它就要走废弃周期、双写、迁移。<em>契约是你唯一真正意义上「一次定型」的决策</em>。"),
        P("一个生产级 LLM 服务至少要暴露四类端点，而且它们的<strong>语义必须严格分离</strong>："),
        TABLE(["端点", "语义", "谁在调", "搞混的后果"], [
            ["<code>POST /v1/chat/completions</code>", "业务：推理", "客户端 / 网关", "—"],
            ["<code>GET /healthz</code>（liveness）", "「进程还活着吗」——只测进程本身，<strong>不测依赖</strong>", "kubelet", "把依赖检查写进 liveness → 下游抖动导致整片 Pod 被重启，故障放大"],
            ["<code>GET /ready</code>（readiness）", "「现在能接流量吗」——权重加载完了吗、队列满没满", "kubelet / Service 端点控制器", "不实现 readiness → 模型没加载完流量就打进来，全部超时"],
            ["<code>GET /metrics</code>", "可观测：QPS、延迟分位、队列深度、GPU 利用、token 吞吐", "Prometheus", "没有指标 → 出问题只能重启和猜"],
        ]),
        DUAL(
            "liveness 和 readiness 的区别一句话说清：<strong>liveness 失败 = 重启我；readiness 失败 = 别给我流量（但别重启我）</strong>。模型加载中，应该是「not ready 但 alive」——你要的是等它加载完，不是把它杀了重来（杀了重来还得再加载三分钟，形成重启风暴）。",
            "形式化：liveness 应当只检测<strong>不可自愈的进程内状态</strong>（死锁、事件循环卡死、堆内存耗尽）；readiness 检测<strong>可恢复的、随时间变化的服务能力</strong>（权重是否就绪、并发队列是否饱和、下游是否可达）。判据：<em>如果重启能修复它，放 liveness；如果等待或减流能修复它，放 readiness</em>。这条判据能消掉生产里 90% 的探针配置错误。",
        ),
        CALLOUT("danger", "<p>LLM 服务最经典的一次事故长这样：readiness 探针直接返回 200（图省事），Deployment 滚动更新，新 Pod 起来 3 秒就被标记 ready、进入 Service 端点，同时旧 Pod 被终止。但新 Pod 的模型权重还要加载 3 分钟。<strong>于是这 3 分钟里，所有流量都被路由到一个还不能推理的 Pod 上，服务 100% 不可用</strong>——而且监控上看，Pod 全是 Running 状态，一切「正常」。这个坑之所以致命，是因为它在小模型（加载 2 秒）上永远不会暴露，只在你换成大模型上线时炸。</p>", "readiness 是 LLM 服务的头号杀手"),
    ])),
    ("openai", "OpenAI 兼容协议：为什么它成了事实标准", "".join([
        P("2023 年之后，几乎所有推理框架（vLLM、SGLang、TGI、Ollama、llama.cpp、TensorRT-LLM）都提供了 <span class=\"term\">OpenAI-compatible API</span>。这不是巧合，也不是抄袭，而是一个典型的<strong>协议网络效应</strong>：客户端生态（LangChain、LlamaIndex、各种 SDK、无数业务代码）已经围绕这套 schema 建好了，谁兼容谁就免费获得整个生态。"),
        P("对你的现实意义是：<strong>除非有极强理由，你的服务就应该说这套协议</strong>。它带来三个具体好处——客户端零改造即可切换后端（自建 vs 云 API）、可以直接用现成的网关/代理/缓存中间件、压测和监控工具开箱可用。"),
        CODE("""POST /v1/chat/completions
{
  "model": "llama-3-8b-instruct",
  "messages": [{"role": "system", "content": "..."},
               {"role": "user",   "content": "解释一下 LSH"}],
  "max_tokens": 512,
  "temperature": 0.7,
  "stream": true,
  "stop": ["\\n\\n"]
}

# 非流式响应
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1712345678,
  "model": "llama-3-8b-instruct",
  "choices": [{"index": 0,
               "message": {"role": "assistant", "content": "LSH 是…"},
               "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 42, "completion_tokens": 187, "total_tokens": 229}
}"""),
        P("这套 schema 里有三个字段值得单独说，因为它们承载的信息远比看起来重要："),
        UL([
            "<strong><code>finish_reason</code></strong>：<code>stop</code>（正常结束）/ <code>length</code>（撞上 max_tokens 被截断）/ <code>content_filter</code>。<em>生产上必须把它打进指标</em>——<code>length</code> 比例突然上升，通常意味着上游 prompt 变了或用户在问更复杂的问题，是容量与质量的双重预警信号。",
            "<strong><code>usage</code></strong>：计费、成本归因、容量规划的唯一数据源。流式响应默认<em>不</em>带 usage（OpenAI 后来加了 <code>stream_options.include_usage</code>），自建服务一定要补上，否则你无法回答「哪个业务方烧了多少 token」。",
            "<strong><code>model</code></strong>：回显的应该是<em>实际服务的模型标识</em>，而不是请求里传的字符串。把权重的内容摘要拼进去（如 <code>llama-3-8b@sha256-abc12</code>），一次事故回溯时你会感谢自己。",
        ]),
        CALLOUT("warn", "兼容不等于等价。<strong>OpenAI 协议里有大量语义是「服务端自由裁量」的</strong>：<code>temperature=0</code> 是否真的确定性（批处理下的浮点归约顺序会让它不确定）、<code>logprobs</code> 的定义、<code>seed</code> 是否被尊重、<code>n&gt;1</code> 怎么实现。<em>把你的实际语义写进文档</em>，否则客户端会按 OpenAI 的行为假设来写代码，然后在你这里得到微妙的不一致。尤其 <code>temperature=0</code> 不保证逐字节可复现这一点，几乎每个自建服务都会被问到。"),
    ])),
    ("streaming", "流式：SSE 的分块协议与首 token 延迟", "".join([
        H3("为什么 LLM 服务必须支持流式"),
        P("一个生成 500 token 的请求，非流式要等 15 秒才返回第一个字节；流式则 300 毫秒就能吐出第一个 token。<strong>同样的总时长，用户感知天差地别</strong>。这不是优化，是 LLM 产品的基本要求。"),
        P("于是 LLM 服务的延迟指标必须拆成两个，这是它和普通 web 服务最大的不同："),
        TABLE(["指标", "全称", "含义", "典型目标", "被什么支配"], [
            ["<strong>TTFT</strong>", "Time To First Token", "从请求到第一个 token", "&lt; 500 ms", "排队时间 + prefill（与 prompt 长度成正比）"],
            ["<strong>TPOT / ITL</strong>", "Time Per Output Token / Inter-Token Latency", "后续每个 token 的间隔", "&lt; 50 ms", "decode 步耗时（与 batch size、KV 长度相关）"],
            ["端到端", "E2E latency", "= TTFT + TPOT × 输出长度", "看场景", "以上两者 + 输出长度分布"],
        ]),
        DUAL(
            "为什么必须拆开？因为<strong>它们的优化方向是冲突的</strong>。增大批处理能提高吞吐、降低单位成本，但会让请求排队更久 → TTFT 变差。所以 SLO 必须分别定：「P95 TTFT &lt; 800 ms 且 P95 TPOT &lt; 60 ms」。只定一个「P95 端到端 &lt; 10 秒」是没有意义的——它会被输出长度分布完全主导，一个爱写长文的用户就能把你的指标搞崩。",
            "严格地说，端到端延迟 <code>L = W_queue + T_prefill(n_prompt) + n_out × T_decode(B, L_kv)</code>。其中 <code>T_prefill</code> 近似与 prompt token 数线性（compute-bound），<code>T_decode</code> 与批大小 <code>B</code> 弱相关（memory-bound，批越大单 token 摊薄越好但绝对时延略增）。<strong>把 <code>n_out</code> 从指标里剥离</strong>正是拆分 TTFT/TPOT 的意义——前两项是服务端能控的，<code>n_out</code> 是用户输入决定的。",
        ),
        H3("SSE：一个极简却处处是坑的协议"),
        P("流式几乎都用 <span class=\"term\">SSE</span>（Server-Sent Events）而不是 WebSocket，因为它是单向的、基于普通 HTTP 的、能穿过绝大多数代理。协议本身简单到可以在一页纸内讲完："),
        ASCII("""HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no          ← 关键！告诉 nginx 不要缓冲，否则流式全废

data: {"choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"choices":[{"delta":{"content":"LSH"},"index":0}]}

data: {"choices":[{"delta":{"content":" 是"},"index":0}]}

data: {"choices":[{"delta":{},"finish_reason":"stop","index":0}]}

data: [DONE]

规则：每条事件以 "data: " 开头、以 **空行** 结束；[DONE] 是 OpenAI 的收尾约定（不是 SSE 标准）。"""),
        CALLOUT("danger", "<p>SSE 在生产里的三大坑，每一个都会让「本地 curl 正常、上线后不流式」：<strong>①中间层缓冲</strong>——nginx/Ingress 默认会缓冲响应体，攒够一批才转发，流式变成伪流式。必须设 <code>proxy_buffering off</code> 或响应头 <code>X-Accel-Buffering: no</code>。<strong>②超时</strong>——很多网关默认 60 秒空闲超时，长生成会被拦腰砍断；要么调大 <code>read_timeout</code>，要么定期发心跳注释行 <code>: ping</code>。<strong>③客户端断连不传播</strong>——用户关掉页面了，你的 GPU 还在为他生成 2000 个 token。必须检测断连并<em>取消</em>后端生成，否则被恶意刷会白烧算力。这三条在任何 SSE 教程里都不会写，但在生产里每条都会遇到。</p>", "SSE 的三个必踩之坑"),
    ])),
    ("batching", "服务端批处理：把请求攒成 batch", "".join([
        P("GPU 的算力只有在<strong>批量</strong>下才能被喂满。单条请求做 decode 时，GPU 大部分时间在等显存搬运权重（memory-bound），算力利用率可能只有百分之几。把 32 条请求的 decode 步合并成一次矩阵乘，权重只搬一次，<strong>吞吐可以涨十几倍而单步延迟只涨一点</strong>。"),
        P("这里必须区分两个层次的批处理，它们常被混为一谈："),
        TABLE(["层次", "谁做", "怎么做", "本课关心什么"], [
            ["<strong>请求级批处理</strong><br>（static / dynamic batching）", "服务框架", "攒够 N 条或等够 T 毫秒，一起送进引擎；整批一起出结果", "攒批窗口 T 与 TTFT 的权衡"],
            ["<strong>迭代级批处理</strong><br>（continuous batching）", "推理引擎（vLLM/TGI）", "每个 decode step 重组 batch，完成的请求立刻退出、新请求立刻插入", "C24 的内容；本课只关心它对容量模型的影响"],
        ]),
        DUAL(
            "现代 LLM 引擎都做 continuous batching，所以<strong>服务层通常不该再自己攒批</strong>——那只会白白增加 TTFT。服务层要做的是相反的事：<em>尽快把请求交给引擎</em>，让引擎的调度器去决定怎么组批。这是一个很多人写自建服务时会搞反的地方。",
            "但服务层仍要控制一个关键量：<strong>并发准入（admission control）</strong>。引擎的 KV 缓存是有限的，能同时容纳的序列数 <code>B_max ≈ KV显存 / (每序列KV占用)</code>。超过这个数，引擎要么排队要么抢占（preemption，把某些序列的 KV 换出重算）。服务层应当在<em>入口</em>就把并发限制在 <code>B_max</code> 附近并对超出部分快速失败或排队，而不是让请求涌进引擎导致抖动。这就是下一节限流的意义。",
        ),
        CALLOUT("intuition", "把这件事想成一个<strong>两级队列</strong>：服务层的准入队列（你控制，可以拒绝、可以排序、可以给不同租户不同配额）和引擎内部的调度队列（引擎控制，追求 GPU 利用率）。<em>准入队列的职责是保护引擎不被打爆，并把「拒绝」这个动作发生在最便宜的地方</em>——在入口拒绝一个请求几乎零成本，在引擎里因为 KV 不足而抢占重算则要浪费已经算过的 token。"),
    ])),
    ("guards", "背压、超时、限流、幂等：四道护栏", "".join([
        P("服务的健壮性几乎完全由这四件事决定，而它们都是「平时看不出用处、出事时决定生死」的东西。"),
        H3("① 背压（backpressure）：拒绝比排队更负责任"),
        P("当到达率超过服务能力，你只有两个选择：<strong>排队</strong>（延迟无限增长，最终所有人超时，还白烧了算力）或<strong>拒绝</strong>（部分人立刻收到 429，其余人正常）。<em>后者几乎总是对的</em>。这就是背压：把压力沿调用链往上游传，让上游降速或降级，而不是自己憋着。"),
        CODE("""# 有界队列 = 最朴素也最有效的背压
MAX_QUEUE = 64          # ≈ 引擎的 B_max，超出即拒绝
if queue.qsize() >= MAX_QUEUE:
    return 429, {'error': 'server overloaded', 'retry_after': 2}   # 快速失败
# 关键：Retry-After 头让客户端知道该等多久，而不是立刻重试加剧雪崩"""),
        H3("② 超时：每一层都必须有，且必须递减"),
        P("超时的黄金规则是<strong>上游超时 &gt; 下游超时</strong>。如果网关 30 秒超时、服务 60 秒超时，那么网关放弃后服务还在算 30 秒——纯浪费。反过来配（网关 60 秒、服务 30 秒）才对：服务先放弃，网关能收到明确的错误而不是连接挂死。"),
        H3("③ 限流：令牌桶与「按什么限」"),
        P("<span class=\"term\">token bucket</span>（令牌桶）是最常用的限流器：桶以固定速率 <code>r</code> 补令牌、容量 <code>b</code>，每个请求取一个令牌，取不到就拒。它的好处是<strong>允许短时突发（最多 b 个）但长期速率被限在 r</strong>——这比固定窗口计数器（会在窗口边界产生 2 倍突发）平滑得多。"),
        CALLOUT("warn", "LLM 服务限流有个特殊之处：<strong>按请求数限流几乎没意义</strong>。一个请求可能生成 10 个 token，也可能生成 4000 个，资源消耗差 400 倍。正确做法是<strong>按 token 限流</strong>（OpenAI 的 TPM = tokens per minute 就是这么来的），或者按「预估 token」预扣、结束后按实际用量结算。同时限 RPM 和 TPM 双维度是工业界的标准做法。只限 RPM 的服务，一定会被长生成请求打爆。"),
        H3("④ 幂等：重试安全的前提"),
        P("客户端超时后会重试。如果你的服务不幂等，一次网络抖动就会变成两次扣费、两次生成。做法是接受一个 <code>Idempotency-Key</code> 头，服务端在短窗口内缓存 (key → 结果)，同 key 重复请求直接返回缓存结果。<em>对 LLM 服务，这还能省下一整次生成的算力</em>。"),
        TABLE(["护栏", "没有它会怎样", "关键参数", "常见错误"], [
            ["背压", "队列无限增长 → 全员超时 → 雪崩", "队列上限 ≈ 引擎 B_max", "无界队列；不返回 Retry-After"],
            ["超时", "连接堆积、算力空烧", "各层超时递减；LLM 要按最长生成设", "上下游超时配反"],
            ["限流", "单个租户打爆全服务", "RPM + TPM 双限，per-tenant", "只限 RPM，被长生成绕过"],
            ["幂等", "重试导致重复生成与重复扣费", "幂等窗口（几分钟）", "只在网关做，服务层不做"],
        ]),
    ])),
    ("queueing", "队列论：一个副本到底扛多少 QPS", "".join([
        P("现在到了本模块最有价值的一节：<strong>把「配几个副本」从拍脑袋变成算数</strong>。这是容量规划的核心，也是模块 04 自动扩缩的理论基础。"),
        P("最小可用的模型是 <span class=\"term\">M/M/c</span>：请求按泊松过程到达（速率 λ）、服务时间服从指数分布（速率 μ）、有 <code>c</code> 个并发服务位。它的关键结论只有一个，但足够指导实践："),
        MATH("\\rho = \\frac{\\lambda}{c\\mu}, \\qquad W_q = \\frac{C(c, \\lambda/\\mu)}{c\\mu - \\lambda}"),
        P("其中 <code>C(c, a)</code> 是 <span class=\"term\">Erlang-C</span> 公式给出的「到达时需要排队的概率」。你不需要背这个公式（notebook 会实现它），需要记住的是<strong>它画出来的那条曲线的形状</strong>："),
        ASCII("""平均排队等待 W_q
    │
    │                                              ╱  ← ρ→1 时垂直爆炸
    │                                            ╱
    │                                        ╱
    │                                  ╱
    │                        ╱
    │            ╱
    │ ─────
    └──────────────────────────────────────────────── ρ
     0.3    0.5    0.6    0.7    0.8    0.9   0.95  1.0
                            ↑                  ↑
                     生产目标区间          «死亡地带»
                     （还有余量吸收抖动）  （多 5% 流量就崩）""")
        ,
        DUAL(
            "这条曲线解释了生产里最常见的一类困惑：「我的服务平均 CPU 才 70%，为什么延迟这么差？」——因为<strong>延迟不是利用率的线性函数，是它的双曲函数</strong>。从 70% 到 85% 你只多榨了 21% 的吞吐，但排队时间可能翻三倍。反过来，容量规划留 30% 余量看起来「浪费」，实际买的是<em>延迟的稳定性和吸收突发的能力</em>。",
            "还有一个更强的结论：<strong>并发数 <code>c</code> 越大，同样利用率下排队越少</strong>（规模经济）。<code>c=1, ρ=0.8</code> 时 <code>W_q = 4/μ</code>；<code>c=10, ρ=0.8</code> 时 <code>W_q ≈ 0.57/μ</code>。这就是「一个 10 副本的池」优于「10 个 1 副本的独立服务」的数学原因——<em>共享排队队列比分散排队高效得多</em>。这条直接反对「给每个租户单独起一套服务」的架构。",
        ),
        CALLOUT("warn", "M/M/c 的假设在 LLM 服务上并不严格成立，用它时要知道偏差在哪：<strong>①服务时间不是指数分布</strong>——LLM 的生成长度分布通常是长尾的（重尾），实际排队会比 M/M/c 预测的<em>更糟</em>；<strong>②服务位不独立</strong>——continuous batching 下多个请求共享 GPU，服务率随并发变化，更接近一个处理器共享（processor sharing）模型；<strong>③到达不是泊松</strong>——真实流量有强自相关和日周期。所以把 M/M/c 当成<em>乐观下界</em>和<em>形状指导</em>，不要当成精确预测。真实容量数字必须靠压测标定，但压测该压哪些点、结果该怎么外推，靠的正是这个模型。"),
    ])),
    ("grpc", "HTTP vs gRPC：什么时候值得换", "".join([
        P("经常有人问：LLM 服务该用 HTTP/JSON 还是 gRPC？答案取决于<strong>你在哪一段</strong>。"),
        TABLE(["维度", "HTTP/1.1 + JSON + SSE", "gRPC (HTTP/2 + protobuf)"], [
            ["序列化开销", "JSON 解析在超长 prompt 下不可忽视", "protobuf 快 2–5 倍，体积小 30–60%"],
            ["流式", "SSE，单向，穿透性好", "原生双向流，更干净（可中途取消、可反向推送）"],
            ["生态", "浏览器直连、curl 可调、无数中间件", "需要 grpc-web 或网关才能给浏览器用"],
            ["可观测", "所有网关/APM 开箱支持", "需要专门的拦截器与工具"],
            ["调试", "极其容易", "需要 <code>grpcurl</code> 和 proto 文件"],
            ["适合", "<strong>南北向</strong>：面向外部客户端的边缘 API", "<strong>东西向</strong>：内部服务间、网关到推理引擎、分布式推理节点间"],
        ]),
        P("务实的结论：<strong>边缘用 OpenAI 兼容的 HTTP/JSON（生态压倒一切），内部高频链路可以考虑 gRPC</strong>。而且这两者不冲突——常见架构是网关说 HTTP、网关到后端说 gRPC。"),
        P("有一个场景 gRPC 优势是决定性的：<strong>分布式推理</strong>。当模型大到要跨节点做张量并行/流水并行时，节点间要传递激活值（大块二进制张量）。用 JSON 传 float 数组是灾难性的（base64 膨胀、解析慢），这里 protobuf + HTTP/2 甚至更底层的 NCCL/RDMA 才是正解。不过那已经是 C39 的领域了。"),
        CALLOUT("intuition", "选协议时别问「哪个更快」，问<strong>「瓶颈在哪」</strong>。一个 TTFT 500 ms 的 LLM 服务，JSON 解析花 2 ms 还是 0.5 ms 完全无关紧要——瓶颈是 GPU。<em>只有当序列化开销占端到端延迟的可测比例时，换协议才有意义</em>。绝大多数 LLM 边缘服务不满足这个条件，所以用 HTTP/JSON 换生态是明显划算的交易。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>SLO 感知的调度</strong>：现在的引擎调度器主要优化吞吐，但不同请求的 SLO 不同（交互式对话要低 TTFT，批量摘要只要吞吐）。如何在同一个引擎里做多 SLO 类别的准入与优先级调度（抢占、降级、公平性保证），是活跃的研究方向（如 Sarathi-Serve、VTC 的公平调度）。",
            "<strong>前缀缓存与路由的协同</strong>：多轮对话的 prompt 有大量公共前缀，命中 KV 前缀缓存可省掉整个 prefill。但这要求负载均衡器<em>不再是无状态轮询</em>，而要把同一会话路由到持有其缓存的副本（缓存亲和路由），同时又不能破坏负载均衡。这个「亲和 vs 均衡」的张力是当前 LLM 网关设计的核心难题。",
            "<strong>prefill/decode 分离</strong>：prefill 是 compute-bound、decode 是 memory-bound，混在一起互相干扰（prefill 会拖长正在 decode 的请求的 TPOT）。把两者拆到不同的实例池、用高速网络传 KV（DistServe、Splitwise、Mooncake），能同时改善 TTFT 和 TPOT，但引入了 KV 传输的带宽与一致性问题。这正在成为大规模服务的主流架构。",
            "<strong>语义级缓存</strong>：不同措辞但语义相同的请求能否复用结果？embedding 相似度阈值怎么定、错误命中的代价如何控制、缓存对个性化与时效性内容的破坏，都还没有好答案。",
            "<strong>协议标准化的下一步</strong>：OpenAI 兼容是事实标准但不是规范标准，各家实现的边角语义不一致（logprobs、tool_calls 的流式增量格式、结构化输出的约束表达）。是否会出现一个真正的中立规范（类似 OpenTelemetry 之于可观测），目前仍未定。",
        ]),
        CALLOUT("paper", "必读：vLLM 的 OpenAI server 实现（<code>vllm/entrypoints/openai/</code>，最好的兼容层参考实现）、Kwon et al. 2023 <em>Efficient Memory Management for LLM Serving with PagedAttention</em>（理解 <code>B_max</code> 从哪来）、Agrawal et al. 2024 <em>Sarathi-Serve</em>（TTFT/TPOT 的权衡与 chunked prefill）、Zhong et al. 2024 <em>DistServe</em>（prefill/decode 分离）、Gross <em>Fundamentals of Queueing Theory</em> 第 2–3 章（Erlang-C 的推导）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 推理服务 API（契约校验、SSE 流式、限流与容量模型，全部从零实现）

目标：把 **OpenAI 兼容契约 → SSE 编解码 → 令牌桶限流 → M/M/c 容量模型** 从零写出来，
每个组件都**对拍**朴素参考、每个结论都**算一笔账**。

路线：请求校验器 → SSE round-trip → TTFT/TPOT 拆解 → 令牌桶 vs 固定窗口 → Erlang-C → 副本数规划 → ✏️ 练习 → 📖 答案 → 🧪 真实 SLO 胶囊。

> 心智模型：**契约定义能力边界，护栏定义失效行为，队列论定义容量**。
> 本环境不起 HTTP 服务，但这三件事的全部逻辑都是纯计算，可以精确复现。"""),
    md("""## 1 · 契约：OpenAI 兼容请求的校验器

契约的第一职责是**在最便宜的地方拒绝坏请求**。写一个校验器，
并验证它对合法请求放行、对各类非法请求给出**精确**的错误（不是笼统的 400）。"""),
    code("""import math, json, random, heapq
from dataclasses import dataclass, field

VALID_ROLES = {'system', 'user', 'assistant', 'tool'}

def validate_chat_request(req, max_context=8192, max_output_cap=4096):
    '''返回 (ok, error_dict_or_None)。仿 OpenAI 的错误结构。'''
    def err(msg, param, code):
        return False, {'error': {'message': msg, 'param': param, 'type': 'invalid_request_error', 'code': code}}

    if 'model' not in req:
        return err('missing required field', 'model', 'missing_field')
    msgs = req.get('messages')
    if not isinstance(msgs, list) or not msgs:
        return err('messages must be a non-empty list', 'messages', 'invalid_type')
    for i, m in enumerate(msgs):
        if m.get('role') not in VALID_ROLES:
            return err(f'invalid role at index {i}', 'messages', 'invalid_role')
        if not isinstance(m.get('content', None), str):
            return err(f'content must be string at index {i}', 'messages', 'invalid_type')
    t = req.get('temperature', 1.0)
    if not (0.0 <= t <= 2.0):
        return err('temperature must be in [0, 2]', 'temperature', 'out_of_range')
    n_out = req.get('max_tokens', 512)
    if n_out > max_output_cap:
        return err(f'max_tokens exceeds cap {max_output_cap}', 'max_tokens', 'out_of_range')
    # 上下文预算：粗估 prompt token = 字符数/4（真实用 tokenizer，见 C50）
    est_prompt = sum(len(m['content']) for m in msgs) // 4
    if est_prompt + n_out > max_context:
        return err(f'context overflow: {est_prompt}+{n_out} > {max_context}', 'messages', 'context_length_exceeded')
    return True, None

good = {'model': 'llama-3-8b', 'messages': [{'role': 'user', 'content': '你好'}], 'max_tokens': 128}
ok, e = validate_chat_request(good); print('合法请求:', ok)
assert ok and e is None

cases = [
    ({'messages': [{'role':'user','content':'x'}]},                          'missing_field'),
    ({'model':'m', 'messages': []},                                          'invalid_type'),
    ({'model':'m', 'messages': [{'role':'wizard','content':'x'}]},           'invalid_role'),
    ({'model':'m', 'messages': [{'role':'user','content':'x'}], 'temperature': 3.0}, 'out_of_range'),
    ({'model':'m', 'messages': [{'role':'user','content':'x'*40000}]},       'context_length_exceeded'),
]
for req, expected_code in cases:
    ok, e = validate_chat_request(req)
    assert not ok and e['error']['code'] == expected_code, (req, e)
    print(f"  ✓ {expected_code:<26s} -> {e['error']['message']}")
print('✅ 校验器给出的是「哪个字段、为什么」，不是笼统的 400')"""),
    md("""### 健康端点的语义分离

**liveness 失败 = 重启我；readiness 失败 = 别给我流量（但别重启我）。**

判据：**重启能修复 → liveness；等待或减流能修复 → readiness**。
下面把这条判据编码成状态机，并验证「模型加载中」必须是 `alive=True, ready=False`。"""),
    code("""@dataclass
class ServerState:
    weights_loaded: bool = False
    event_loop_alive: bool = True
    queue_depth: int = 0
    max_queue: int = 64
    shutting_down: bool = False
    downstream_ok: bool = True      # 下游依赖（如 tokenizer 服务）

def healthz(s):     # liveness：只看进程内不可自愈的状态
    return 200 if s.event_loop_alive else 500

def readyz(s):      # readiness：看「现在能不能接流量」
    if s.shutting_down:            return 503   # 优雅停机第一步
    if not s.weights_loaded:       return 503   # 加载中：活着但没准备好
    if s.queue_depth >= s.max_queue: return 503 # 过载：暂时摘流量
    return 200

loading = ServerState(weights_loaded=False)
assert healthz(loading) == 200, '模型加载中，进程是活的 —— 绝不能让 liveness 失败'
assert readyz(loading) == 503,  '模型加载中，不能接流量'
print('加载中: liveness 200 (别重启我) / readiness 503 (别给我流量) ✅')

ready = ServerState(weights_loaded=True)
assert (healthz(ready), readyz(ready)) == (200, 200)

overload = ServerState(weights_loaded=True, queue_depth=64)
assert healthz(overload) == 200 and readyz(overload) == 503, '过载应摘流量而非重启'

dead = ServerState(weights_loaded=True, event_loop_alive=False)
assert healthz(dead) == 500, '事件循环卡死只能靠重启'

# 反面教材：把下游依赖检查写进 liveness
def bad_healthz(s): return 200 if (s.event_loop_alive and s.downstream_ok) else 500
flaky = ServerState(weights_loaded=True, downstream_ok=False)
assert bad_healthz(flaky) == 500 and healthz(flaky) == 200
print('⚠️  反面教材：下游抖动 -> bad_healthz 返回 500 -> 全部 Pod 被重启 -> 故障放大')
print('✅ 语义分离正确：liveness 只测自己，readiness 测「现在能否服务」')"""),
    md("""## 2 · SSE：编码、解码与 round-trip 对拍

SSE 规则极简：每条事件 `data: <payload>\\n\\n`（**空行**结束），OpenAI 用 `data: [DONE]` 收尾。
写出编码器和解码器，用 **round-trip 对拍**验证协议实现正确。"""),
    code("""def sse_encode(chunks, done_sentinel='[DONE]'):
    '''把一串 delta 对象编码成 SSE 字节流。'''
    out = []
    for c in chunks:
        out.append('data: ' + json.dumps(c, ensure_ascii=False) + '\\n\\n')
    out.append(f'data: {done_sentinel}\\n\\n')
    return ''.join(out)

def sse_decode(stream, done_sentinel='[DONE]'):
    '''解析 SSE 流，返回 delta 对象列表（遇到 [DONE] 停止）。'''
    events = []
    for block in stream.split('\\n\\n'):
        line = block.strip()
        if not line or not line.startswith('data: '):
            continue
        payload = line[len('data: '):]
        if payload == done_sentinel:
            break
        events.append(json.loads(payload))
    return events

def make_deltas(text_tokens):
    ds = [{'choices': [{'index': 0, 'delta': {'role': 'assistant'}}]}]
    ds += [{'choices': [{'index': 0, 'delta': {'content': t}}]} for t in text_tokens]
    ds += [{'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]}]
    return ds

toks = ['LSH', ' 是', '一种', '局部', '敏感', '哈希']
deltas = make_deltas(toks)
wire = sse_encode(deltas)
print(wire[:160].replace('\\n', '⏎') + ' …')

# round-trip 对拍：解码回来必须与原始 deltas 完全一致
assert sse_decode(wire) == deltas, 'SSE round-trip 必须无损'
# 从 delta 流重建完整文本（客户端要做的事）
text = ''.join(d['choices'][0]['delta'].get('content', '') for d in sse_decode(wire))
assert text == ''.join(toks), text
print(f'\\n重建文本: {text!r}')
print('✅ SSE round-trip 对拍通过')"""),
    md("""### 中间层缓冲：为什么本地 curl 正常、上线后不流式

代理若开启缓冲，会攒够 N 字节才转发一次。**总时长不变，但 TTFT 被毁掉。**
下面量化这个差别。"""),
    code("""def simulate_delivery(wire, ttft_ms=300, tpot_ms=40, n_tokens=6, buffer_bytes=0):
    '''返回每个 token 到达客户端的时刻(ms)。buffer_bytes=0 表示不缓冲。'''
    per_event = len(wire) / (n_tokens + 2)     # 粗略：每条事件的字节数
    arrivals, pending, t = [], 0.0, ttft_ms
    for i in range(n_tokens):
        pending += per_event
        if buffer_bytes == 0 or pending >= buffer_bytes:
            arrivals.append(t); pending = 0.0
        else:
            arrivals.append(None)              # 还被缓冲着，没送出去
        t += tpot_ms
    # 缓冲未满的部分在流结束时一次性 flush
    flush_at = ttft_ms + tpot_ms * n_tokens
    return [a if a is not None else flush_at for a in arrivals]

no_buf = simulate_delivery(wire, buffer_bytes=0)
buffered = simulate_delivery(wire, buffer_bytes=4096)    # nginx 默认缓冲区量级
print('无缓冲, 各 token 到达(ms):', [round(x) for x in no_buf])
print('有缓冲, 各 token 到达(ms):', [round(x) for x in buffered])
print(f'TTFT: 无缓冲 {no_buf[0]:.0f}ms  vs  有缓冲 {buffered[0]:.0f}ms')
assert buffered[0] > no_buf[0] * 1.5, '缓冲会显著恶化 TTFT'
assert all(b >= a for a, b in zip(no_buf, buffered)), '缓冲只会让每个 token 更晚到达'
assert len(set(buffered)) == 1, '被缓冲时所有 token 在流结束时一次性抵达——流式名存实亡'
print('✅ 生成总时长没变，被毁掉的只有「边生成边看到」这个体验。')
print('   这就是必须设 proxy_buffering off / X-Accel-Buffering: no 的原因')"""),
    md("""## 3 · TTFT / TPOT：为什么延迟指标必须拆开

$$L_{e2e} = W_{queue} + T_{prefill}(n_{prompt}) + n_{out} \\times T_{decode}$$

只看端到端延迟会被**输出长度分布**完全主导——一个爱写长文的用户就能把你的 P95 搞崩。"""),
    code("""def e2e_latency(w_queue_ms, n_prompt, n_out, prefill_ms_per_1k=90.0, tpot_ms=35.0):
    t_prefill = n_prompt / 1000 * prefill_ms_per_1k
    return w_queue_ms + t_prefill + n_out * tpot_ms

rng = random.Random(0)
# 两类用户：短问答 vs 长文生成，服务端能力完全相同
short = [e2e_latency(20, 300, rng.randint(30, 120)) for _ in range(2000)]
long_ = [e2e_latency(20, 300, rng.randint(800, 2000)) for _ in range(2000)]

def p(xs, q):
    s = sorted(xs); return s[min(len(s)-1, int(q * len(s)))]

print(f'短问答  P50 {p(short,.5)/1000:>6.2f}s  P95 {p(short,.95)/1000:>6.2f}s')
print(f'长文    P50 {p(long_,.5)/1000:>6.2f}s  P95 {p(long_,.95)/1000:>6.2f}s')
mixed = short + long_
print(f'混合    P50 {p(mixed,.5)/1000:>6.2f}s  P95 {p(mixed,.95)/1000:>6.2f}s  ← 被长文主导')

assert p(long_, .95) > 5 * p(short, .95), '同样的服务端能力，P95 差 5 倍以上'
# 而 TTFT 和 TPOT 对两类用户是一样的（服务端能力的真实反映）
ttft_short = 20 + 300/1000*90
ttft_long  = 20 + 300/1000*90
assert abs(ttft_short - ttft_long) < 1e-9
print('\\n✅ TTFT/TPOT 对两类用户完全相同 —— 它们才是服务端能力的指标。')
print('   SLO 必须写成「P95 TTFT < 800ms 且 P95 TPOT < 60ms」，而非端到端。')"""),
    md("""## 4 · 限流：令牌桶 vs 固定窗口

**固定窗口计数器**有个致命缺陷：窗口边界可以放过 **2 倍**的突发。
令牌桶没有这个问题。下面把两者都实现，用同一串请求对比。"""),
    code("""class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate, self.cap = rate, capacity
        self.tokens, self.last = float(capacity), 0.0
    def allow(self, now, cost=1.0):
        self.tokens = min(self.cap, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost; return True
        return False

class FixedWindow:
    def __init__(self, limit, window=1.0):
        self.limit, self.window, self.count, self.win_start = limit, window, 0, 0.0
    def allow(self, now, cost=1.0):
        if now - self.win_start >= self.window:
            self.win_start, self.count = now - (now % self.window), 0
        if self.count + cost <= self.limit:
            self.count += cost; return True
        return False

# 攻击场景：在窗口边界前后各打满 10 个请求
RATE = 10
tb, fw = TokenBucket(RATE, RATE), FixedWindow(RATE, 1.0)
burst = [0.95]*10 + [1.00]*10        # 边界前 10 个 + 边界后 10 个
tb_pass = sum(tb.allow(t) for t in burst)
fw_pass = sum(fw.allow(t) for t in burst)
print(f'边界突发 20 个请求 (限速 {RATE}/s): 令牌桶放行 {tb_pass}, 固定窗口放行 {fw_pass}')
assert fw_pass > tb_pass, '固定窗口在边界会放过约 2 倍流量'
print('✅ 固定窗口的边界效应：0.95s~1.00s 这 50ms 内放过了 2 倍额度')

# 对拍：长期速率必须收敛到 rate
tb2 = TokenBucket(RATE, RATE)
passed = sum(tb2.allow(i * 0.01) for i in range(1000))    # 10 秒内每 10ms 打一个
expected = RATE * 10 + RATE                                # 长期 rate*T + 初始桶容量
assert abs(passed - expected) <= 2, f'长期放行应≈{expected}，得到 {passed}'
print(f'✅ 令牌桶长期速率收敛: 10 秒放行 {passed} ≈ rate*10 + 桶容量 = {expected}')"""),
    md("""### 为什么 LLM 必须按 token 限流

一个请求可能生成 10 个 token，也可能 4000 个——资源消耗差 400 倍。
**只限 RPM 的服务一定会被长生成打爆。**"""),
    code("""def simulate_rpm_only(requests, rpm_limit):
    '''只限请求数：返回实际消耗的 token 总量。桶容量 = 一分钟额度。'''
    tb = TokenBucket(rpm_limit / 60.0, rpm_limit)
    return sum(n_tok for t, n_tok in requests if tb.allow(t))

def simulate_rpm_tpm(requests, rpm_limit, tpm_limit):
    '''RPM + TPM 双限。'''
    tb_r = TokenBucket(rpm_limit / 60.0, rpm_limit)
    tb_t = TokenBucket(tpm_limit / 60.0, tpm_limit)
    used = 0
    for t, n_tok in requests:
        if tb_r.allow(t) and tb_t.allow(t, cost=n_tok):
            used += n_tok
    return used

rng = random.Random(1)
normal = [(i * 0.1, rng.randint(50, 200)) for i in range(600)]        # 正常用户
abuser = [(i * 0.1, 4000) for i in range(600)]                        # 每个请求都顶格生成

RPM, TPM = 60, 60_000
print(f'限额: RPM={RPM}, TPM={TPM:,}')
for name, reqs in [('正常用户', normal), ('长生成滥用', abuser)]:
    only_rpm = simulate_rpm_only(reqs, RPM)
    both     = simulate_rpm_tpm(reqs, RPM, TPM)
    print(f'  {name:<12s} 仅限RPM放过 {only_rpm:>8,} tok | RPM+TPM放过 {both:>8,} tok')

abuse_rpm_only = simulate_rpm_only(abuser, RPM)
abuse_both     = simulate_rpm_tpm(abuser, RPM, TPM)
assert abuse_rpm_only > 3 * abuse_both, '仅限 RPM 时，长生成能绕过限额数倍'
print(f'\\n✅ 滥用者在「仅限 RPM」下多消耗 {abuse_rpm_only/abuse_both:.1f} 倍算力 —— 必须双限')"""),
    md("""## 5 · 容量模型：Erlang-C 与副本数规划

M/M/c 的核心结论：**排队时间是利用率的双曲函数，ρ→1 时爆炸**。
先实现 Erlang-C，用蒙特卡洛离散事件仿真**对拍**它，再拿它做容量规划。"""),
    code("""def erlang_c(c, a):
    '''到达时需要排队的概率。a = λ/μ（提供负载，单位 erlang）。'''
    if a >= c:
        return 1.0
    s = sum(a**k / math.factorial(k) for k in range(c))
    top = a**c / math.factorial(c) * (c / (c - a))
    return top / (s + top)

def mmc_wait(lam, mu, c):
    '''M/M/c 平均排队等待时间 W_q。'''
    a = lam / mu
    if a >= c:
        return float('inf')
    return erlang_c(c, a) / (c * mu - lam)

MU = 2.0                      # 单副本每秒处理 2 个请求
print(f"{'c':>3s} {'λ':>6s} {'ρ':>6s} {'W_q(ms)':>10s}")
for c in [1, 4, 10]:
    lam = 0.8 * c * MU        # 固定 ρ=0.8
    print(f'{c:>3d} {lam:>6.1f} {lam/(c*MU):>6.2f} {mmc_wait(lam,MU,c)*1000:>10.1f}')

w1, w10 = mmc_wait(0.8*1*MU, MU, 1), mmc_wait(0.8*10*MU, MU, 10)
assert w10 < w1 / 3, '同样 ρ=0.8，c=10 的排队应远小于 c=1（规模经济）'
print(f'\\n✅ 规模经济：同样 ρ=0.8，c=1 排队 {w1*1000:.0f}ms，c=10 只有 {w10*1000:.0f}ms')
print('   这就是「一个 10 副本共享池」优于「10 个独立单副本服务」的数学原因。')"""),
    code("""# 对拍：离散事件仿真 vs Erlang-C 解析解
def simulate_mmc(lam, mu, c, n_req=60000, seed=0):
    rng = random.Random(seed)
    free_at = [0.0] * c                     # 每个服务位的空闲时刻
    t, waits = 0.0, []
    for _ in range(n_req):
        t += rng.expovariate(lam)           # 泊松到达
        heapq.heapify(free_at)
        earliest = free_at[0]
        w = max(0.0, earliest - t)
        waits.append(w)
        heapq.heapreplace(free_at, max(t, earliest) + rng.expovariate(mu))
    return sum(waits) / len(waits)

for c, rho in [(1, 0.7), (4, 0.8), (8, 0.85)]:
    lam = rho * c * MU
    sim, ana = simulate_mmc(lam, MU, c), mmc_wait(lam, MU, c)
    rel = abs(sim - ana) / ana
    print(f'c={c} ρ={rho}: 仿真 {sim*1000:>7.1f}ms | 解析 {ana*1000:>7.1f}ms | 相对误差 {rel:.1%}')
    assert rel < 0.15, f'仿真与解析应吻合，c={c} 误差 {rel:.1%}'
print('✅ 对拍通过：Erlang-C 解析解与离散事件仿真一致（<15%）')"""),
    md("""### 死亡地带：ρ 从 0.8 推到 0.95 会发生什么"""),
    code("""C = 8
print(f"{'ρ':>6s} {'λ(QPS)':>8s} {'W_q(ms)':>10s} {'相对 ρ=0.7':>12s}")
base = mmc_wait(0.7*C*MU, MU, C)
for rho in [0.7, 0.8, 0.85, 0.9, 0.95, 0.98]:
    w = mmc_wait(rho*C*MU, MU, C)
    print(f'{rho:>6.2f} {rho*C*MU:>8.1f} {w*1000:>10.1f} {w/base:>11.1f}×')

w70, w95 = mmc_wait(0.7*C*MU, MU, C), mmc_wait(0.95*C*MU, MU, C)
assert w95 > 8 * w70, 'ρ 0.7→0.95 排队应恶化近一个数量级'
print(f'\\n✅ 多榨 36% 吞吐，排队时间涨 {w95/w70:.0f} 倍。')
print('   生产目标利用率 0.6~0.8 不是保守，是「延迟稳定性」的合理定价。')"""),
    md("""## ✏️ 练习 1：满足 TTFT SLO 的最小副本数

实现 `min_replicas(lam, mu, ttft_budget_s, prefill_s)`：
返回使 **W_q + prefill ≤ ttft_budget_s** 的**最小副本数 c**（从 1 开始试，`c` 上限 1000）。
若无解返回 `None`。"""),
    code("""def min_replicas(lam, mu, ttft_budget_s, prefill_s):
    # TODO: 从 c=1 试到 1000，找第一个满足 mmc_wait(lam, mu, c) + prefill_s <= ttft_budget_s 的 c
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
c = min_replicas(lam=12.0, mu=2.0, ttft_budget_s=0.8, prefill_s=0.3)
assert c is not None and c > 6, f'λ/μ=6，至少要 7 个副本才不排到无穷，得到 {c}'
assert mmc_wait(12.0, 2.0, c) + 0.3 <= 0.8 + 1e-9, 'c 必须真的满足预算'
assert c == 1 or mmc_wait(12.0, 2.0, c-1) + 0.3 > 0.8, 'c 必须是最小的那个'
# 预算越紧，需要越多副本
c_tight = min_replicas(12.0, 2.0, 0.35, 0.3)
c_loose = min_replicas(12.0, 2.0, 3.0, 0.3)
assert c_tight > c_loose, '更紧的 TTFT 预算需要更多副本'
print(f'λ=12 μ=2: TTFT预算 0.8s -> {c} 副本 | 0.35s -> {c_tight} 副本 | 3.0s -> {c_loose} 副本')
print('✅ 练习 1 通过：SLO 直接翻译成副本数')"""),
    md("""## ✏️ 练习 2：按 token 计费的令牌桶

实现 `TokenBudget`：一个按 **token** 而非请求计数的限流器。
接口：`__init__(self, tpm)`（每分钟 token 额度，桶容量 = tpm）、
`try_reserve(self, now, est_tokens)` 预扣、`settle(self, actual_tokens, est_tokens)` 结算（退还多扣的）。"""),
    code("""class TokenBudget:
    def __init__(self, tpm):
        # TODO: rate = tpm/60 tok/s, capacity = tpm；self.tokens 初始为满
        raise NotImplementedError
    def try_reserve(self, now, est_tokens):
        # TODO: 补充令牌(受 capacity 上限)、够则扣除返回 True，否则 False
        raise NotImplementedError
    def settle(self, actual_tokens, est_tokens):
        # TODO: 退还 (est - actual)，但总量不超过 capacity
        raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
tb = TokenBudget(tpm=6000)              # 100 tok/s
assert tb.try_reserve(0.0, 1000) is True
assert tb.try_reserve(0.0, 5000) is True     # 桶容量 6000，刚好用完
assert tb.try_reserve(0.0, 1)     is False,  '额度用尽应拒绝'
tb.settle(actual_tokens=200, est_tokens=1000)   # 实际只用了 200，退还 800
assert tb.try_reserve(0.0, 800) is True, '退还后应能再预扣 800'
# 一分钟后应恢复满额
tb2 = TokenBudget(tpm=6000)
tb2.try_reserve(0.0, 6000)
assert tb2.try_reserve(60.0, 6000) is True, '60 秒后应补满 6000'
print('✅ 练习 2 通过：预扣-结算模型让「先限流后知道实际用量」成为可能')"""),
    md("""## ✏️ 练习 3：优雅降级的准入决策

实现 `admit(queue_depth, max_queue, tier)`：三档租户 `tier ∈ {'premium','standard','free'}`。
规则：队列 < 50% 全部放行；50%~80% 拒 `free`；80%~100% 只放 `premium`；≥100% 全拒。
返回 `(bool, status_code)`，放行 `(True, 200)`，拒绝 `(False, 429)`。"""),
    code("""def admit(queue_depth, max_queue, tier):
    # TODO: 按上述四档规则返回 (allowed, status)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
MAXQ = 100
assert admit(10,  MAXQ, 'free')     == (True, 200)
assert admit(60,  MAXQ, 'free')     == (False, 429)
assert admit(60,  MAXQ, 'standard') == (True, 200)
assert admit(90,  MAXQ, 'standard') == (False, 429)
assert admit(90,  MAXQ, 'premium')  == (True, 200)
assert admit(100, MAXQ, 'premium')  == (False, 429)
# 单调性：队列越深，放行的档次只减不增
for tier in ['premium', 'standard', 'free']:
    allowed = [admit(q, MAXQ, tier)[0] for q in range(0, 101, 10)]
    assert allowed == sorted(allowed, reverse=True), f'{tier} 的放行应随队列深度单调不增'
print('✅ 练习 3 通过：过载时先牺牲低优先级，而不是全体一起慢')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def min_replicas(lam, mu, ttft_budget_s, prefill_s):
    for c in range(1, 1001):
        if mmc_wait(lam, mu, c) + prefill_s <= ttft_budget_s:
            return c
    return None"""),
    code("""# 练习 2 参考答案
class TokenBudget:
    def __init__(self, tpm):
        self.rate = tpm / 60.0
        self.cap = float(tpm)
        self.tokens = float(tpm)
        self.last = 0.0
    def try_reserve(self, now, est_tokens):
        self.tokens = min(self.cap, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= est_tokens:
            self.tokens -= est_tokens
            return True
        return False
    def settle(self, actual_tokens, est_tokens):
        self.tokens = min(self.cap, self.tokens + max(0, est_tokens - actual_tokens))"""),
    code("""# 练习 3 参考答案
def admit(queue_depth, max_queue, tier):
    r = queue_depth / max_queue
    if r >= 1.0:                              return (False, 429)
    if r >= 0.8:  return (True, 200) if tier == 'premium' else (False, 429)
    if r >= 0.5:  return (False, 429) if tier == 'free' else (True, 200)
    return (True, 200)"""),
    md("""---
## 🧪 真实数据胶囊：把 SLO 翻译成一张容量表

给定真实量级的服务参数，产出一张「QPS → 副本数 → 月成本 → P95 TTFT」的规划表。
这张表就是你去和产品/财务谈判时手里的东西。
（本环境不联网，单价用公开量级，可改成你自己的报价。）"""),
    code("""# 公开量级：7B 模型在单张 H100 上的典型服务能力
MU_PER_REPLICA = 2.5          # req/s（含 prefill+decode，平均输出 300 token）
PREFILL_S      = 0.28         # 平均 prompt 1.5k token 的 prefill
GPU_HOURLY     = 4.0          # 单卡 H100 按需 $/h（量级）
TTFT_SLO_S     = 0.8

print(f"{'峰值QPS':>8s} {'副本':>5s} {'ρ':>6s} {'W_q(ms)':>9s} {'TTFT(ms)':>10s} {'月成本$':>10s}")
plan = []
for qps in [5, 10, 25, 50, 100, 200]:
    c = min_replicas(qps, MU_PER_REPLICA, TTFT_SLO_S, PREFILL_S)
    wq = mmc_wait(qps, MU_PER_REPLICA, c)
    ttft = (wq + PREFILL_S) * 1000
    cost = c * GPU_HOURLY * 24 * 30
    plan.append((qps, c, qps/(c*MU_PER_REPLICA), ttft, cost))
    print(f'{qps:>8d} {c:>5d} {qps/(c*MU_PER_REPLICA):>6.2f} {wq*1000:>9.1f} {ttft:>10.1f} {cost:>10,.0f}')

# 性质检查
qpss  = [r[0] for r in plan]; reps = [r[1] for r in plan]; costs = [r[4] for r in plan]
assert reps == sorted(reps),   '副本数应随 QPS 单调增'
assert costs == sorted(costs), '成本应随 QPS 单调增'
assert all(r[3] <= TTFT_SLO_S*1000 + 1e-6 for r in plan), '每一行都必须满足 TTFT SLO'
# 规模经济：QPS 翻 20 倍，单位成本应下降
unit_small = plan[0][4] / plan[0][0]
unit_large = plan[-1][4] / plan[-1][0]
assert unit_large < unit_small, '规模越大，每 QPS 的成本越低（Erlang 规模经济）'
print(f'\\n✅ 规模经济：5 QPS 时每 QPS ${unit_small:,.0f}/月，200 QPS 时 ${unit_large:,.0f}/月'
      f'（省 {(1-unit_large/unit_small)*100:.0f}%）')"""),
    md("""**🧪 胶囊练习**：实现 `slo_headroom(qps, c, mu, prefill_s, ttft_slo_s)`：
返回在不违反 TTFT SLO 的前提下，**当前配置还能吸收多少倍的流量突增**（返回一个 ≥1 的浮点数；
若当前已违反 SLO 返回 0.0）。用二分或线性扫描均可，精度 0.01 即可。"""),
    code("""def slo_headroom(qps, c, mu, prefill_s, ttft_slo_s):
    # TODO: 找最大的 k，使 mmc_wait(k*qps, mu, c) + prefill_s <= ttft_slo_s
    #       当前已违反则返回 0.0；k 上限取 10.0
    raise NotImplementedError"""),
    code("""# 自测
h = slo_headroom(25, 13, MU_PER_REPLICA, PREFILL_S, TTFT_SLO_S)
assert h >= 1.0, f'按 SLO 规划出的配置至少应有 1.0 倍余量，得到 {h}'
assert mmc_wait(h * 25, MU_PER_REPLICA, 13) + PREFILL_S <= TTFT_SLO_S + 1e-6
# 副本越多，余量越大
h_more = slo_headroom(25, 20, MU_PER_REPLICA, PREFILL_S, TTFT_SLO_S)
assert h_more > h, '更多副本应有更大余量'
# 严重欠配时余量为 0
assert slo_headroom(100, 5, MU_PER_REPLICA, PREFILL_S, TTFT_SLO_S) == 0.0
print(f'25 QPS / 13 副本: 可吸收 {h:.2f}× 突增 | 20 副本: {h_more:.2f}×')
print('✅ 胶囊练习通过：余量是模块 04 自动扩缩「来不来得及」的判据')"""),
    code("""# 📖 胶囊参考答案
def slo_headroom(qps, c, mu, prefill_s, ttft_slo_s):
    if mmc_wait(qps, mu, c) + prefill_s > ttft_slo_s:
        return 0.0
    k, best = 1.0, 1.0
    while k <= 10.0:
        if mmc_wait(k * qps, mu, c) + prefill_s <= ttft_slo_s:
            best = k
        k += 0.01
    return round(best, 2)"""),
    md("""---
## 🔧 旁注：真实系统里这些对应什么

- **契约校验** → FastAPI + Pydantic model；vLLM 的 `protocol.py` 定义了完整的 OpenAI schema。
- **健康端点** → K8s `livenessProbe` / `readinessProbe`（模块 03 详述）；vLLM 的 `/health`；自建服务务必自己实现 `/ready`。
- **SSE** → `StreamingResponse(media_type="text/event-stream")`；Ingress 侧 `nginx.ingress.kubernetes.io/proxy-buffering: "off"` + `proxy-read-timeout: "600"`。
- **令牌桶** → Envoy/Kong 的 rate limit filter、Redis + Lua 的分布式令牌桶；OpenAI 的 RPM/TPM 双限就是这个模型。
- **Erlang-C** → 容量规划表；真实数字必须靠压测（`vllm bench serve` / `locust` / `k6`）标定 μ，模型负责外推与形状。
- **准入分级** → Envoy 的 priority + circuit breaker；或网关层按 API key 的 tier 路由。

你在这里算出的「λ→c→成本→TTFT」四元组，就是模块 04 自动扩缩策略的输入，也是模块 05 成本账的基数。"""),
    md("""### 小结
- **契约是唯一「一次定型」的决策**；OpenAI 兼容不是抄袭，是协议网络效应。
- **liveness / readiness 语义必须分离**：重启能修的放 liveness，等待或减流能修的放 readiness。LLM 服务的头号事故源就在这。
- **流式必须拆 TTFT / TPOT**；端到端延迟会被输出长度分布主导，不能作为 SLO。SSE 有缓冲、超时、断连三个必踩之坑。
- **四道护栏**：有界队列背压、逐层递减超时、RPM+TPM 双限流、幂等键。LLM 只限 RPM 必被长生成绕过。
- **Erlang-C 给出容量的形状**：排队是利用率的双曲函数、ρ→1 爆炸；并发池越大越省（规模经济）。它是乐观下界，真实数字靠压测标定。

下一站：**模块 03 · Kubernetes 编排** —— 契约定好了，现在让一百个副本在集群里自己活起来。"""),
]
