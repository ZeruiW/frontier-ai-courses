# -*- coding: utf-8 -*-
"""C48 模块 05 · 云平台、集群调度与成本。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–04、期望值与简单概率"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_cloud_scheduling_cost.ipynb'),
    ("核心参考", "AWS/GCP 定价与 spot 文档、Slurm 官方文档、Ray 架构文档、FinOps Foundation 框架"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("abstraction", "云的抽象：三件套与它们的计价单位", "".join([
        P("前四个模块都在讲「怎么做」。这一模块讲<strong>「在谁的机器上做、花多少钱」</strong>——这是把技术方案变成可执行方案的最后一步，也是研究工程师最容易被卡住的一步（方案很漂亮，但一算钱发现做不了）。"),
        P("剥掉所有产品名词，云只有三样东西，而且<strong>每样的计价单位都不同</strong>——这个差异是所有成本优化的起点："),
        TABLE(["抽象", "是什么", "计价单位", "关键陷阱"], [
            ["<strong>计算</strong>", "虚拟机 / 容器 / 函数", "<strong>时间</strong>（秒·实例）", "闲着也全额计费；GPU 实例的最小计费粒度可能是分钟甚至小时"],
            ["<strong>存储</strong>", "对象存储 / 块存储 / 文件系统", "<strong>容量 × 时间</strong> + <strong>请求次数</strong>", "小文件的请求费可能超过存储费；块存储必须挂在实例上才计费但删了实例它还在"],
            ["<strong>网络</strong>", "出网 / 跨区 / 跨可用区", "<strong>字节</strong>（几乎只对出方向收费）", "<strong>最容易失控的一项</strong>；跨可用区流量在很多云上也收费"],
        ]),
        DUAL(
            "记住这条不对称：<strong>进云免费、出云收费；同区便宜、跨区贵、出公网最贵</strong>。这一条就能解释云架构里大量看似奇怪的设计——为什么模型权重要放在和 GPU 同一个区域、为什么要做节点本地缓存（模块 01）、为什么日志不该无脑全量传到另一个区。",
            "严格地说，成本模型是 <code>C = Σ_i (unit_price_i × quantity_i)</code>，优化就是压 <code>quantity</code> 或换更便宜的 <code>unit_price</code>。压 quantity 的手段是前四个模块的全部内容（更小的镜像、更高的装箱率、更准的扩缩）；换单价的手段是本模块的内容（spot、预留、区域选择、实例类型）。<strong>两条路径要一起走，但顺序上先压 quantity</strong>——因为便宜单价 × 巨大用量，仍然是巨大账单。",
        ),
        CALLOUT("warn", "一个几乎所有团队都踩过的坑：<strong>出网流量费的隐形</strong>。GPU 账单是显眼的、被反复盯着的；数据传输费散落在账单各处（S3 GET、跨 AZ、NAT 网关、负载均衡器处理字节数），单条都不大，加起来可能占总账单的 15–30%。模块 01 算过的「20 副本拉 140 GB 权重 = $252 一次」就是典型。<em>第一次做云成本分析时，务必按「服务」和「费用类型」两个维度都切一遍</em>，你大概率会在网络那一栏发现惊喜。"),
    ])),
    ("storage", "对象存储：模型权重的家", "".join([
        P("LLM 部署里，对象存储（S3 / GCS / OSS）承担一个特定角色：<strong>模型权重的唯一真相源</strong>。它的几个性质直接决定了你的部署方案。"),
        TABLE(["性质", "含义", "对 LLM 部署的影响"], [
            ["<strong>扁平命名空间</strong>", "没有真正的「目录」，只有 key 前缀", "权重按 <code>models/&lt;name&gt;/&lt;sha256&gt;/</code> 组织，用内容哈希做版本（模块 01）"],
            ["<strong>读后写一致性</strong>", "现代对象存储对新对象是强一致的（S3 自 2020 起）", "上传完立刻能读到，不用再写「等一会儿」的重试逻辑"],
            ["<strong>不可变更新</strong>", "对象是整体替换，没有原地追加/修改", "「换模型」= 写一个新 key，而不是覆盖旧 key。这天然给你回滚能力"],
            ["<strong>单连接带宽有限</strong>", "单个 GET 通常几百 MB/s 封顶", "拉 140 GB 必须<strong>分片并发</strong>下载（<code>aws s3 cp</code> 默认就做，自己写要注意）"],
            ["<strong>请求计费</strong>", "每次 GET/LIST 都收费", "safetensors 分片成几百个小文件时，请求费和延迟都会显现"],
        ]),
        P("有两个具体决策值得记住："),
        UL([
            "<strong>权重必须和 GPU 在同一区域（region）</strong>。跨区拉取不仅慢（延迟 + 带宽），还产生每 GB 的传输费。「同一个 bucket 服务全球集群」是个诱人但昂贵的错误——正确做法是每个区域一份副本，用跨区复制（CRR）同步。",
            "<strong>用内容哈希而不是可变标签做 key</strong>。<code>models/llama3-8b/latest/</code> 这种 key 会让你无法回答「三天前那个副本加载的是什么」。用 <code>models/llama3-8b/sha256-abc…/</code>，再用一个小的 manifest 文件记录「当前 latest 指向哪个哈希」——这样 latest 的变更本身是可追踪、可回滚的。",
        ]),
        CALLOUT("intuition", "把对象存储想成<strong>一个巨大的、按字节收租的、只能整存整取的 KV 存储</strong>。它不是文件系统——没有 rename（是 copy+delete，140 GB 的 rename 会真的复制 140 GB）、没有 append、没有 POSIX 语义、LIST 是分页且昂贵的。所有把它当文件系统用的方案（比如 s3fs 挂载后让 torch 直接从上面 <code>load</code>）都会在规模上暴露问题。<em>正确用法是显式的「下载到本地 → 从本地加载」</em>。"),
    ])),
    ("spot", "实例选择与 spot 经济学", "".join([
        P("这一节是本模块最有直接经济价值的部分：<strong>什么时候该用 spot（抢占式）实例</strong>。"),
        P("云厂商把闲置容量以 60–90% 的折扣卖出，代价是<strong>可能被随时收回</strong>（通常给 30 秒到 2 分钟的通知）。问题是：这笔账什么时候划算？"),
        H3("期望成本模型"),
        P("设按需价 <code>p_od</code>、spot 价 <code>p_spot</code>、单位时间中断概率 <code>h</code>（hazard rate）、一次中断的恢复成本 <code>c_int</code>（重启 + 重新加载 + 丢失的进行中工作）。每小时的期望成本："),
        MATH("\\mathbb{E}[C_{spot}] = p_{spot} + h \\cdot c_{int}, \\qquad \\text{spot 划算} \\iff p_{spot} + h\\cdot c_{int} < p_{od}"),
        P("由此得出<strong>盈亏平衡的中断率</strong>："),
        MATH("h^* = \\frac{p_{od} - p_{spot}}{c_{int}}"),
        TABLE(["工作负载", "<code>c_int</code>（一次中断损失）", "适合 spot？", "为什么"], [
            ["离线批量推理（可断点续跑）", "低：只丢一个分片的进度", "✅ <strong>非常适合</strong>", "中断成本几乎为零，折扣是净赚"],
            ["预训练（有 checkpoint）", "中：丢失上次 checkpoint 后的进度 + 重启全部 rank", "🔶 视 checkpoint 频率而定", "C39 的容错工程决定了 <code>c_int</code>；同步训练里一个 rank 挂 = 全体重来"],
            ["在线推理（面向用户）", "<strong>高</strong>：用户请求失败 + 容量缺口 + 冷启动 3 分钟", "❌ 不适合单独用", "SLO 与错误预算的代价远超省下的钱"],
            ["在线推理（spot + 按需混合底座）", "低：按需底座保底，spot 只做弹性部分", "✅ <strong>标准做法</strong>", "把「必须有」和「多多益善」分开定价"],
        ]),
        DUAL(
            "最后一行是工业界的标准答案，值得展开：<strong>把容量分成「基线」和「弹性」两层</strong>。基线（覆盖 P50 流量）用按需或预留实例，保证 SLO 的下界；弹性（P50 以上的部分）用 spot，被收回了只是容量少一点、退化到基线，不至于服务不可用。这个组合能拿到 spot 大部分的折扣，同时把风险控制在「性能降级」而不是「服务中断」。",
            "工程上还要配三件事：<strong>①处理中断通知</strong>——监听云的抢占事件（AWS 的 <code>ITN</code>、GCP 的 <code>preemption notice</code>），收到后立刻走模块 01 的优雅停机流程（摘流量、排空）。这两分钟足够放完在途请求。<strong>②多样化实例池</strong>——不要把所有 spot 押在同一个实例类型/可用区上，容量池相关性会让它们同时被收回。<strong>③容量上限与回退</strong>——spot 拿不到时能自动回退到按需，而不是无限重试。",
        ),
        P("除了 spot，还有两种降价手段值得一提，它们的取舍很不一样："),
        UL([
            "<strong>预留实例 / Savings Plan</strong>：承诺 1–3 年用量，换 30–60% 折扣。适合<em>确定长期存在的基线容量</em>。风险是锁定——GPU 迭代很快，锁 3 年 A100 可能在第二年就不划算了。<em>对 GPU 通常建议 1 年而非 3 年</em>。",
            "<strong>Committed use / 阶梯定价</strong>：按承诺的消费额度打折，比预留实例灵活（不绑定具体机型）。对快速演进的 GPU 栈更友好。",
        ]),
        CALLOUT("danger", "<p>一个必须提前想到的<strong>相关性风险</strong>：spot 的中断不是独立事件。当整个区域的容量紧张时（比如某个大客户突然扩容、或者某个新模型发布引发全行业抢卡），<em>你的所有 spot 实例可能在几分钟内被同时收回</em>。如果你的弹性层全是 spot 且占了 70% 容量，这一刻就是一次全面的容量崩塌。<strong>设计时要问「如果全部 spot 同时消失，我还剩多少容量、够不够撑住 P50 流量」</strong>——这个问题的答案决定了基线层该配多大。</p>", "spot 中断是相关的，不是独立的"),
    ])),
    ("scheduling", "作业调度：K8s Job vs Slurm vs Ray 三种世界观", "".join([
        P("在线服务用 K8s Deployment（模块 03）。但研究工程师大量的工作是<strong>离线作业</strong>：跑评测、批量推理、微调、超参搜索。这类工作有完全不同的调度需求，也发展出了三套不同的系统。"),
        TABLE(["", "<strong>Kubernetes Job</strong>", "<strong>Slurm</strong>", "<strong>Ray</strong>"], [
            ["出身", "云原生 / 微服务", "HPC / 超算中心", "分布式 Python / ML"],
            ["核心抽象", "Pod + 容器", "作业（job）+ 分区（partition）+ 节点", "task / actor + 对象存储"],
            ["资源申请", "声明式 YAML，requests/limits", "<code>sbatch --gres=gpu:8 --nodes=4</code>", "<code>@ray.remote(num_gpus=1)</code> 装饰器"],
            ["排队与公平", "需插件（Volcano/Kueue）", "<strong>内置且成熟</strong>：优先级、QoS、fairshare、backfill", "内置基础调度，公平性较弱"],
            ["gang scheduling", "需插件", "<strong>原生</strong>（分布式训练的默认预期）", "placement group"],
            ["交互性", "弱（面向长期运行的服务）", "<code>srun</code> 可交互", "<strong>强</strong>：Python 里直接起分布式任务"],
            ["适合", "在线服务、CI、云原生批处理", "<strong>大规模训练集群、学术/企业超算</strong>", "<strong>Python 生态的分布式实验、RL、超参搜索</strong>"],
        ]),
        DUAL(
            "三者不是竞争关系，很多组织同时用：<strong>K8s 跑在线服务，Slurm 跑训练，Ray 跑实验和数据处理</strong>。选哪个主要看你的机器归谁管——如果你在一个有共享 GPU 集群的组织里，那大概率是 Slurm（这是超算界几十年的标准）；如果你在一个云原生团队，那就是 K8s + Kueue/Volcano；如果你在做 RL 或大规模超参搜索，Ray 的编程模型会让你快很多。",
            "关键的技术差异在<strong>调度粒度与排队语义</strong>。K8s 的调度器是为「长期运行的服务」设计的：Pod 一旦调度就假定长期存在，没有内置的排队公平性和 backfill。Slurm 是为「有明确开始和结束的作业」设计的：它天然理解「这个作业要 4 节点跑 6 小时」，因此能做<span class=\"term\">backfill</span>（在等待大作业攒够资源的空隙里插入短小作业，显著提高利用率）和 fairshare（按历史用量调整优先级）。<em>把长作业塞进 K8s 而不加调度插件，通常会得到很差的集群利用率</em>。",
        ),
        H3("Slurm 的最小心智模型"),
        P("作为研究工程师，Slurm 是你最可能天天用、却从没系统学过的东西。它的核心只有几个概念："),
        CODE("""#!/bin/bash
#SBATCH --job-name=sft-llama8b
#SBATCH --partition=gpu-h100        # 分区 = 一组机器 + 一套策略（时长上限、优先级）
#SBATCH --nodes=4                   # 要 4 台机器
#SBATCH --ntasks-per-node=8         # 每台起 8 个任务（对应 8 张卡）
#SBATCH --gres=gpu:8                # 通用资源：每节点 8 张 GPU
#SBATCH --cpus-per-task=12
#SBATCH --time=12:00:00             # 时限；**越短越容易被 backfill 提前调度**
#SBATCH --output=logs/%x-%j.out     # %x=job name, %j=job id
#SBATCH --requeue                   # 被抢占后自动重排队（配合 checkpoint）

srun python train.py --config configs/sft.yaml

# 常用命令
#   sbatch  train.sh        提交
#   squeue -u $USER         看自己的队列（ST 列：PD=排队 R=运行 CG=收尾）
#   scancel <jobid>         取消
#   sinfo -p gpu-h100       看分区里有多少空闲节点
#   sacct -j <jobid>        看历史作业的资源使用与退出码
#   scontrol show job <id>  看排队原因（Reason 字段：Priority / Resources / QOSMaxJobs…）"""),
        CALLOUT("intuition", "关于 Slurm 有一条极其实用、但很少有人明说的经验：<strong><code>--time</code> 填得越准（越短），你排队等得越少</strong>。因为 backfill 调度器会在「等大作业攒资源」的空隙里，插入那些「声明时长足够短、能在空隙内跑完」的作业。你填 <code>--time=48:00:00</code> 图保险，结果永远排在队尾；填 <code>--time=3:00:00</code>（真实需要 2.5 小时），可能立刻就跑上了。<em>代价是超时会被强杀，所以要配合 checkpoint 与 <code>--requeue</code></em>。"),
    ])),
    ("multiregion", "多区域、容灾与数据合规", "".join([
        P("单区域部署有两类风险：<strong>可用性</strong>（区域级故障，虽罕见但发生过）和<strong>延迟</strong>（跨洲用户的网络往返就有几百毫秒）。多区域是解法，但它的成本远不止「乘以 N」。"),
        TABLE(["维度", "单区域", "多区域", "增量成本来源"], [
            ["GPU 容量", "按峰值配", "<strong>每个区域都要有基线容量</strong>", "无法跨区共享池 → 总容量必须超过全局峰值"],
            ["权重存储", "一份", "每区一份 + 跨区复制", "存储 × N + 复制流量"],
            ["运维复杂度", "一套", "N 套配置、N 套发布流水线", "人力（最贵的一项）"],
            ["流量路由", "简单", "GeoDNS / Anycast / 全局负载均衡", "额外组件与调试难度"],
        ]),
        P("务实的建议是<strong>分阶段</strong>：先做单区域多可用区（multi-AZ，模块 03 的拓扑分布），这能挡住绝大多数硬件与机房级故障，成本增量很小；只有当你的用户真的跨洲、或者 SLO 真的要求抗区域级故障时，才上多区域。<em>「万一某个区挂了」在大多数业务上并不值那笔钱</em>。"),
        H3("数据合规：一个绕不开的约束"),
        P("对 LLM 服务，数据出境是个真实的法律约束而不只是技术选择。用户的对话内容可能包含个人信息，很多司法辖区（欧盟 GDPR、中国的数据出境规定、各行业的本地化要求）限制它被传输到境外。这会强制你的架构："),
        UL([
            "<strong>推理必须在数据所在地完成</strong>——意味着每个受管辖区域都要有完整的部署，不能「统一送回总部的大集群」。",
            "<strong>日志与遥测也受约束</strong>——请求内容不能进集中式日志系统。常见做法是「本地存原文、只把脱敏后的指标外发」。",
            "<strong>模型权重的流向通常不受限</strong>（它不含用户数据），所以权重可以从一个地方分发到各区域。这是多区域部署里唯一简单的部分。",
        ]),
        CALLOUT("warn", "一个容易被忽略的合规细节：<strong>用户对话默认不该进训练数据</strong>。很多团队会顺手把线上流量存下来「以后做微调用」，这在多数司法辖区需要明确的用户同意，而且一旦混进训练集就很难剥离（模型已经记住了）。<em>数据留存策略应该在服务上线之前就定下来</em>，而不是事后补救。这条和 C12（负责任 AI）、C45（隐私与可信 ML）直接相关。"),
    ])),
    ("unitecon", "单位经济：$ / 1M token 的完整分解", "".join([
        P("最后把前五个模块的所有决策，汇聚成研究工程师最该会算的一个数字：<strong>每百万 token 的成本</strong>。它是和产品、财务、老板沟通的唯一共同语言。"),
        MATH("\\text{\\$/1M tok} = \\frac{p_{node} }{ \\underbrace{T_{peak}}_{\\text{峰值吞吐}} \\times \\underbrace{u}_{\\text{平均利用率}} \\times \\underbrace{\\eta}_{\\text{装箱率}} \\times 3600 / 10^6 }"),
        TABLE(["因子", "由谁决定", "典型值", "提升它的手段"], [
            ["<code>p_node</code> 单价", "云选型、spot/预留", "$32/h（8×H100 按需）", "spot（−70%）、预留（−40%）、换区域"],
            ["<code>T_peak</code> 峰值吞吐", "<strong>C24/C27</strong> 推理引擎与量化", "4000 tok/s", "continuous batching、FP8/INT4、投机解码"],
            ["<code>u</code> 平均利用率", "<strong>模块 04</strong> 自动扩缩 + 流量曲线", "0.35–0.65", "自动扩缩、混部离线任务填谷"],
            ["<code>η</code> 装箱率", "<strong>模块 03</strong> 调度策略", "0.5–0.85", "装箱调度、减少反亲和约束、统一实例规格"],
        ]),
        P("这个分解的价值在于它<strong>告诉你优化该往哪儿使劲</strong>。很多团队的直觉是「买更快的卡」或「优化 kernel」（提高 <code>T_peak</code>），但如果你的 <code>u</code> 是 0.3、<code>η</code> 是 0.5，那么<em>把这两项提上去的收益，远大于把吞吐再榨 20%</em>——而且便宜得多。"),
        ASCII("""同一套硬件，四个因子的复合效应：

  最差配置: $32 / (4000 × 0.25 × 0.50 × 3600/1e6) = $17.8 / 1M tok
  典型配置: $32 / (4000 × 0.45 × 0.70 × 3600/1e6) = $7.05 / 1M tok
  优化配置: $32 / (5500 × 0.65 × 0.85 × 3600/1e6) = $2.93 / 1M tok
  优化+spot: $10 / (5500 × 0.65 × 0.85 × 3600/1e6) = $0.92 / 1M tok

  最差 → 最优 = 19 倍。**没有一项来自「换更好的 GPU」。**""")
        ,
        DUAL(
            "这张对比表是本课的最终论点：<strong>部署工程的复合收益，和模型优化的收益是同一量级甚至更大的，但它几乎不需要研究突破，只需要把每个环节做对</strong>。镜像小一点（模块 01）、容量算准一点（模块 02）、装箱好一点（模块 03）、扩缩稳一点（模块 04）、单价选对一点（模块 05）——每项 20–40%，乘起来就是一个数量级。",
            "但要诚实地标注这个模型的边界：<code>T_peak</code> 依赖具体模型、序列长度分布与引擎版本，必须靠压测标定；<code>u</code> 依赖真实流量曲线，不同业务差异巨大；spot 的 $10/h 是乐观值且不保证可得。<strong>把这个公式当成「分解归因的框架」而不是「报价单」</strong>——它的用途是回答「我该优化哪一项」，而不是「我明年要花多少钱」。后者需要用你自己的实测数字重算一遍。",
        ),
        CALLOUT("intuition", "把整门课浓缩成一句话：<strong>LLM 部署不是「把模型放上线」这一个动作，而是一条由镜像、契约、编排、发布、成本五个环节组成的链路；每个环节的决策都会以乘法的方式影响最终的可靠性与单位成本</strong>。这就是为什么「模型很好但上不了线」和「上线了但烧钱烧不起」是两个如此普遍的故事——它们卡的不是任何单点的难题，而是这条链路上若干个「看起来无所谓」的默认选项。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>异构与碎片化的算力市场</strong>：H100/H200/B200/MI300/TPU/自研 NPU 并存，加上 neocloud（CoreWeave、Lambda 等）与去中心化算力市场，「同一个模型该跑在哪种卡上最便宜」变成了一个持续的优化问题。跨厂商的性能-价格自动选型工具仍很原始。",
            "<strong>训练与推理的混部</strong>：推理集群在流量低谷有大量闲置 GPU，训练/评测作业正好可以填谷。但两者的 SLO 差异巨大（推理要低延迟、训练要长时间独占），抢占策略、显存隔离、checkpoint 频率的协同设计还没有成熟方案。这是当前最大的一块「地上的钱」。",
            "<strong>碳感知调度</strong>：不同区域、不同时段的电网碳强度差几倍。把作业调度到低碳时段/区域（carbon-aware scheduling）在延迟不敏感的批处理上完全可行，但与成本、容量的多目标权衡缺乏公认框架。",
            "<strong>成本归因的粒度</strong>：多租户共享 GPU 集群里，「这个业务方该分摊多少 GPU 成本」在技术上很难算准（共享 KV 缓存、批处理让请求间成本互相纠缠）。公平的多租户计量与计费模型仍是开放问题。",
            "<strong>Slurm 与 K8s 的融合</strong>：研究组织普遍同时拥有两套集群，资源无法共享。Kueue、Volcano、Slinky（Slurm on K8s）、Ray on Slurm 等都在尝试打通，但排队语义、gang scheduling、公平性模型的差异让融合并不平凡。",
        ]),
        CALLOUT("paper", "必读：AWS/GCP 的 spot 实例最佳实践文档（中断处理与多样化池的官方指南）、Slurm 官方 <em>Quick Start</em> 与 <em>Backfill Scheduling</em> 文档（比任何二手教程都清楚）、Ray 的 <em>Architecture Whitepaper</em>、FinOps Foundation 的成本分摊框架、Patterson et al. 2021 <em>Carbon Emissions and Large Neural Network Training</em>（算力的碳账）。工程对标：SkyPilot（跨云选型与 spot 容错的开源实现，非常值得读源码）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · 云平台、集群调度与成本（spot 期望成本、backfill 调度器、$/1M token 分解）

目标：把 **spot 盈亏平衡 → 基线/弹性混合容量 → Slurm backfill 调度 → 单位经济分解** 从零实现，
每个模型都**对拍**蒙特卡洛仿真、每个决策都**算一笔账**。

路线：三件套计价 → spot 期望成本与盈亏点 → 相关性中断的风险 → backfill 调度器 → $/1M token 四因子分解 → ✏️ 练习 → 📖 答案 → 🧪 全课汇总胶囊。

> 心智模型：**成本 = Σ 单价 × 用量**。前四个模块压用量，本模块换单价。
> 两条路都要走，但**先压用量**——便宜单价 × 巨大用量，仍是巨大账单。"""),
    md("""## 1 · 三件套的计价不对称

计算按**时间**、存储按**容量×时间+请求数**、网络按**字节且只收出方向**。
这个不对称是所有云成本优化的起点。先把它量化。"""),
    code("""import math, random, heapq
from dataclasses import dataclass, field

# 公开量级（可改成你自己的报价）
PRICE = {
    'gpu_node_hour':   32.00,   # 8×H100 按需
    'storage_gb_month': 0.023,  # 标准对象存储
    'get_per_1k':       0.0004, # GET 请求
    'egress_gb':        0.09,   # 出公网/跨区
    'cross_az_gb':      0.01,   # 跨可用区
}

def monthly_bill(nodes, weights_gb, n_model_versions, pulls_per_month, cross_az_gb_per_month):
    compute = nodes * PRICE['gpu_node_hour'] * 24 * 30
    storage = weights_gb * n_model_versions * PRICE['storage_gb_month']
    egress  = pulls_per_month * weights_gb * PRICE['egress_gb']
    az      = cross_az_gb_per_month * PRICE['cross_az_gb']
    return {'计算': compute, '存储': storage, '权重拉取': egress, '跨AZ': az,
            '合计': compute + storage + egress + az}

bill = monthly_bill(nodes=7, weights_gb=140, n_model_versions=5,
                    pulls_per_month=60, cross_az_gb_per_month=20000)
for k, v in bill.items():
    share = v / bill['合计']
    print(f'{k:>10s}: ${v:>12,.2f}  {share:>6.1%}')

net = bill['权重拉取'] + bill['跨AZ']
assert bill['计算'] > 0.8 * bill['合计'], '计算应是大头'
assert net > bill['存储'] * 30, '网络费远大于存储费 —— 存储便宜，搬运贵'
print(f'\\n✅ 存储只要 ${bill["存储"]:,.0f}，但「把它搬来搬去」要 ${net:,.0f}（{net/bill["存储"]:.0f} 倍）')
print('   记住这条不对称：**存字节便宜，搬字节贵**。')"""),
    md("""## 2 · spot 经济学：盈亏平衡的中断率

$$\\mathbb{E}[C_{spot}] = p_{spot} + h \\cdot c_{int}, \\qquad h^* = \\frac{p_{od} - p_{spot}}{c_{int}}$$

`h*` 是**盈亏平衡中断率**：实际中断率低于它，spot 划算；高于它，spot 反而更贵。"""),
    code("""def spot_breakeven(p_od, p_spot, c_interrupt):
    '''返回每小时盈亏平衡中断次数。'''
    return (p_od - p_spot) / c_interrupt

def spot_expected_cost(p_spot, hazard_per_hour, c_interrupt):
    return p_spot + hazard_per_hour * c_interrupt

P_OD, P_SPOT = 32.0, 10.0        # 按需 $32/h，spot $10/h（约 -69%）

workloads = [
    ('离线批推理(可断点续)',  0.5),    # 一次中断只丢几分钟工作
    ('预训练(30min ckpt)',   16.0),    # 丢半小时 × 全体 rank
    ('在线推理(无热备)',    600.0),    # 容量缺口 + 请求失败 + 3 分钟冷启动的 SLO 损失
]
print(f"{'工作负载':<24s} {'c_int($)':>9s} {'盈亏中断率/h':>13s} {'实际0.05/h时期望$':>18s}")
for name, c_int in workloads:
    h_star = spot_breakeven(P_OD, P_SPOT, c_int)
    exp = spot_expected_cost(P_SPOT, 0.05, c_int)
    verdict = '✅ 划算' if exp < P_OD else '❌ 更贵'
    print(f'{name:<24s} {c_int:>9.1f} {h_star:>13.3f} {exp:>15.2f} {verdict}')

assert spot_breakeven(P_OD, P_SPOT, 0.5) > 40, '批处理能容忍极高中断率'
assert spot_expected_cost(P_SPOT, 0.05, 600.0) > P_OD, '在线推理裸用 spot 反而更贵'
print('\\n✅ 同一个折扣，对不同工作负载的结论完全相反 —— 决定因素是 c_int，不是折扣力度')"""),
    md("""### 对拍：蒙特卡洛仿真 vs 解析期望"""),
    code("""def simulate_spot(hours, p_spot, hazard, c_int, seed=0):
    rng = random.Random(seed)
    total = 0.0
    for _ in range(hours):
        total += p_spot
        if rng.random() < hazard:
            total += c_int
    return total / hours

for hz, c_int in [(0.02, 16.0), (0.05, 16.0), (0.10, 0.5)]:
    sim = simulate_spot(200000, P_SPOT, hz, c_int)
    ana = spot_expected_cost(P_SPOT, hz, c_int)
    rel = abs(sim - ana) / ana
    print(f'hazard={hz:.2f} c_int=${c_int:>5.1f}: 仿真 ${sim:>6.3f}/h | 解析 ${ana:>6.3f}/h | 误差 {rel:.2%}')
    assert rel < 0.02, '解析式应与蒙特卡洛吻合'
print('✅ 对拍通过：期望成本公式正确')"""),
    md("""### 相关性中断：spot 不是独立事件

现实里区域容量紧张时，**所有 spot 可能在几分钟内同时消失**。
设计时必须问：全部 spot 消失后，剩余容量够不够撑住 P50 流量？"""),
    code("""def survive_spot_wipeout(baseline_replicas, spot_replicas, mu, p50_qps, target_rho=0.9):
    '''全部 spot 被收回后，仅靠基线能否撑住 P50 流量。'''
    capacity = baseline_replicas * mu * target_rho
    return capacity >= p50_qps, capacity

MU, P50_QPS, PEAK_QPS = 2.5, 60.0, 200.0
designs = [
    ('全 spot',        0,  ceil_ := math.ceil(PEAK_QPS / (MU * 0.7))),
    ('全按需',         ceil_, 0),
    ('基线覆盖P50+spot弹性', math.ceil(P50_QPS / (MU * 0.7)), ceil_ - math.ceil(P50_QPS / (MU * 0.7))),
]
print(f"{'设计':<24s} {'基线':>5s} {'spot':>5s} {'月成本$':>11s} {'spot全灭后':>12s}")
for name, base, spot in designs:
    cost = (base * P_OD + spot * P_SPOT) / 4 * 24 * 30    # 每节点 4 副本
    ok, cap = survive_spot_wipeout(base, spot, MU, P50_QPS)
    print(f'{name:<24s} {base:>5d} {spot:>5d} {cost:>11,.0f} '
          f'{"✅ 撑得住" if ok else "❌ 服务不可用":>12s}')

all_spot_ok, _ = survive_spot_wipeout(0, ceil_, MU, P50_QPS)
mixed_ok, _ = survive_spot_wipeout(math.ceil(P50_QPS/(MU*0.7)), 0, MU, P50_QPS)
assert not all_spot_ok, '全 spot 在集体收回时服务完全不可用'
assert mixed_ok, '基线覆盖 P50 的混合设计能扛住 spot 全灭'
print('\\n✅ 标准做法：**基线（按需/预留）覆盖 P50 + 弹性（spot）覆盖峰值**')
print('   最坏情况从「服务不可用」退化成「性能降级」—— 这才是可接受的失效模式。')"""),
    md("""## 3 · Slurm 的核心：backfill 调度器

Slurm 比 K8s 默认调度器更懂「有明确时长的作业」，因此能做 **backfill**：
在等大作业攒资源的空隙里，插入那些「声明时长足够短、能在空隙内跑完」的小作业。

这解释了那条实用经验：**`--time` 填得越准（越短），排队等得越少。**"""),
    code("""@dataclass
class Job:
    jid: int
    nodes: int
    walltime: int      # 声明时长（秒）
    submit: int = 0
    prio: int = 0

def fcfs_schedule(jobs, total_nodes):
    '''纯先来先服务：队首作业攒不够资源就全队阻塞。'''
    t, free, running, done = 0, total_nodes, [], []
    q = sorted(jobs, key=lambda j: (-j.prio, j.submit, j.jid))
    while q or running:
        while q and q[0].nodes <= free:
            j = q.pop(0); free -= j.nodes
            heapq.heappush(running, (t + j.walltime, j.jid, j.nodes))
        if not running:
            break
        t, jid, n = heapq.heappop(running)
        free += n; done.append((jid, t))
    return done, t

def backfill_schedule(jobs, total_nodes):
    '''EASY backfill：队首作业保留预约，后面的小作业若能在预约前跑完就插队。'''
    t, free, running, done = 0, total_nodes, [], []
    q = sorted(jobs, key=lambda j: (-j.prio, j.submit, j.jid))
    while q or running:
        # 1) 尽量启动队首
        while q and q[0].nodes <= free:
            j = q.pop(0); free -= j.nodes
            heapq.heappush(running, (t + j.walltime, j.jid, j.nodes))
        # 2) 为队首算「预约开始时刻」，再回填能在此之前结束的小作业
        if q:
            need, tmp, f2, res_t = q[0].nodes, list(running), free, t
            while f2 < need and tmp:
                et, _, n = heapq.heappop(tmp); f2 += n; res_t = et
            i = 1
            while i < len(q):
                j = q[i]
                if j.nodes <= free and t + j.walltime <= res_t:
                    q.pop(i); free -= j.nodes
                    heapq.heappush(running, (t + j.walltime, j.jid, j.nodes))
                else:
                    i += 1
        if not running:
            break
        t, jid, n = heapq.heappop(running)
        free += n; done.append((jid, t))
    return done, t

TOTAL_NODES = 16
# 关键场景：一个长作业占住半个集群 -> 队首的整集群作业只能等 -> 空出的 8 节点该不该闲着？
jobs = [Job(0, nodes=8,  walltime=3600),        # 已在跑，占 8 节点 1 小时
        Job(1, nodes=16, walltime=1800)] + \\
       [Job(i, nodes=2, walltime=600) for i in range(2, 10)]     # 8 个 10 分钟小作业

d_fcfs, mk_fcfs = fcfs_schedule(jobs, TOTAL_NODES)
d_bf,   mk_bf   = backfill_schedule(jobs, TOTAL_NODES)
print(f'FCFS     完成时刻(makespan): {mk_fcfs/60:>6.1f} 分钟')
print(f'Backfill 完成时刻(makespan): {mk_bf/60:>6.1f} 分钟')
avg_fcfs = sum(t for _, t in d_fcfs) / len(d_fcfs)
avg_bf   = sum(t for _, t in d_bf) / len(d_bf)
print(f'平均完成时间: FCFS {avg_fcfs/60:.1f} 分钟 | Backfill {avg_bf/60:.1f} 分钟')
assert mk_bf <= mk_fcfs, 'backfill 不应变差'
assert avg_bf < avg_fcfs, 'backfill 应显著改善平均完成时间'
print(f'\\n✅ backfill 把平均完成时间改善 {(1-avg_bf/avg_fcfs):.0%} —— 空隙被小作业填满了')"""),
    md("""### `--time` 填得越短，越容易被回填"""),
    code("""def time_to_start(declared_walltime, total_nodes=16, probe_jid=2):
    '''同一个作业（真实只跑 10 分钟），声明不同 --time 时的实际启动时刻。'''
    js = [Job(0, nodes=8,  walltime=3600),
          Job(1, nodes=16, walltime=1800),
          Job(probe_jid, nodes=2, walltime=declared_walltime)]
    t, free, running, start = 0, total_nodes, [], None
    q = sorted(js, key=lambda j: j.jid)
    while q or running:
        while q and q[0].nodes <= free:
            j = q.pop(0); free -= j.nodes
            if j.jid == probe_jid and start is None: start = t
            heapq.heappush(running, (t + j.walltime, j.jid, j.nodes))
        if q:
            need, tmp, f2, res_t = q[0].nodes, list(running), free, t
            while f2 < need and tmp:
                et, _, n = heapq.heappop(tmp); f2 += n; res_t = et
            i = 1
            while i < len(q):
                j = q[i]
                if j.nodes <= free and t + j.walltime <= res_t:
                    q.pop(i); free -= j.nodes
                    if j.jid == probe_jid and start is None: start = t
                    heapq.heappush(running, (t + j.walltime, j.jid, j.nodes))
                else:
                    i += 1
        if not running: break
        t, jid, n = heapq.heappop(running); free += n
    return start

print(f"{'声明 --time':>14s} {'实际启动时刻':>14s}")
for wt in [600, 1800, 3600, 7200]:
    s = time_to_start(wt)
    print(f'{wt//60:>11d} 分 {s/60 if s is not None else -1:>13.1f} 分')
assert time_to_start(600) < time_to_start(7200), '声明时长越短，越早被回填调度'
print('\\n✅ 同一个作业（真实只跑 10 分钟），声明 10 分钟 vs 120 分钟，排队差了一小时。')
print('   实用建议：`--time` 填真实需要的 1.2~1.5 倍，配 checkpoint + --requeue 兜底。')"""),
    md("""## 4 · 单位经济：$ / 1M token 的四因子分解

$$\\text{\\$/1M tok} = \\frac{p_{node}}{T_{peak} \\times u \\times \\eta \\times 3600 / 10^6}$$

这个分解告诉你**优化该往哪儿使劲**。"""),
    code("""def cost_per_1m_tokens(p_node_hour, t_peak_tok_s, utilization, packing):
    eff_tokens_per_hour = t_peak_tok_s * utilization * packing * 3600
    return p_node_hour / (eff_tokens_per_hour / 1e6)

configs = [
    ('最差  (无扩缩/碎片严重)', 32.0, 4000, 0.25, 0.50),
    ('典型  (基本配置)',        32.0, 4000, 0.45, 0.70),
    ('优化  (本课全套)',        32.0, 5500, 0.65, 0.85),
    ('优化+spot',               10.0, 5500, 0.65, 0.85),
]
print(f"{'配置':<26s} {'$/节点h':>9s} {'吞吐':>6s} {'利用率':>7s} {'装箱':>6s} {'$/1M tok':>10s}")
costs = []
for name, p, t, u, e in configs:
    c = cost_per_1m_tokens(p, t, u, e); costs.append(c)
    print(f'{name:<26s} {p:>9.2f} {t:>6d} {u:>7.2f} {e:>6.2f} {c:>10.3f}')

assert costs == sorted(costs, reverse=True), '成本应逐行下降'
print(f'\\n最差 -> 最优 = {costs[0]/costs[-1]:.1f} 倍差距，**没有一项来自「换更好的 GPU」**')

# 敏感度分析：各因子单独改善 30% 的收益
base = cost_per_1m_tokens(32.0, 4000, 0.45, 0.70)
print(f'\\n基线 ${base:.3f}/1M tok。各因子单独改善 30% 的收益:')
for label, kw in [('吞吐 +30%', dict(t_peak_tok_s=5200)),
                  ('利用率 +30%', dict(utilization=0.585)),
                  ('装箱率 +30%', dict(packing=0.91)),
                  ('单价 -30%', dict(p_node_hour=22.4))]:
    args = dict(p_node_hour=32.0, t_peak_tok_s=4000, utilization=0.45, packing=0.70)
    args.update(kw)
    c = cost_per_1m_tokens(**args)
    print(f'  {label:<12s} -> ${c:.3f} (省 {(1-c/base):.0%})')
print('\\n✅ 四个因子的边际收益相同（都是 ~23%）—— 但**改善难度天差地别**：')
print('   榨 30% 吞吐要 kernel 工程；提 30% 装箱率只要改一行调度策略。**先摘低垂的果子。**')"""),
    md("""## ✏️ 练习 1：混合容量的最优 spot 比例

实现 `optimal_spot_ratio(peak_r, p50_r, p_od, p_spot, wipeout_prob, downtime_cost_per_hour)`：
在「基线必须能撑住 P50」的约束下，返回 `(baseline_replicas, spot_replicas, expected_hourly_cost)`。
- `baseline = p50_r`（刚好覆盖 P50），`spot = peak_r - p50_r`
- 期望小时成本 = `baseline*p_od + spot*p_spot + wipeout_prob * downtime_cost_per_hour`
  （spot 全灭时只是降级不是宕机，所以这里的 downtime cost 按「峰值时段容量不足」计）"""),
    code("""def optimal_spot_ratio(peak_r, p50_r, p_od, p_spot, wipeout_prob, downtime_cost_per_hour):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
b, s, c = optimal_spot_ratio(peak_r=115, p50_r=35, p_od=8.0, p_spot=2.5,
                             wipeout_prob=0.01, downtime_cost_per_hour=500.0)
assert b == 35 and s == 80, f'基线覆盖 P50，其余用 spot，得到 ({b}, {s})'
expected = 35*8.0 + 80*2.5 + 0.01*500.0
assert abs(c - expected) < 1e-9
# 对比全按需
all_od = 115 * 8.0
print(f'混合: 基线 {b} + spot {s} = ${c:.2f}/h')
print(f'全按需: ${all_od:.2f}/h')
assert c < all_od * 0.7, '混合方案应至少省 30%'
print(f'✅ 练习 1 通过：省 {(1-c/all_od):.0%}，且最坏情况只是降级不是宕机')"""),
    md("""## ✏️ 练习 2：backfill 可行性判定

实现 `can_backfill(job_nodes, job_walltime, free_nodes, now, reservation_time)`：
判断一个作业能否被回填——需要同时满足
①`job_nodes <= free_nodes`；②`now + job_walltime <= reservation_time`（不能推迟队首的预约）。"""),
    code("""def can_backfill(job_nodes, job_walltime, free_nodes, now, reservation_time):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert can_backfill(2, 600, free_nodes=4, now=0, reservation_time=3600) is True
assert can_backfill(8, 600, free_nodes=4, now=0, reservation_time=3600) is False, '节点不够'
assert can_backfill(2, 7200, free_nodes=4, now=0, reservation_time=3600) is False, '会推迟队首预约'
assert can_backfill(2, 3600, free_nodes=4, now=0, reservation_time=3600) is True, '刚好卡住是允许的'
# 单调性：声明时长越短越容易回填
ok = [can_backfill(2, wt, 4, 0, 3600) for wt in [600, 1800, 3600, 5400]]
assert ok == [True, True, True, False]
print('✅ 练习 2 通过：这两个条件就是 EASY backfill 的全部判据')"""),
    md("""## ✏️ 练习 3：成本归因

实现 `attribute_cost(total_node_hours, tenant_tokens, node_hourly)`：
`tenant_tokens` 是 `{租户: token 数}`。按 token 比例分摊总计算成本。
返回 `{租户: 分摊金额}`，并保证总和等于总成本（浮点误差 < 1e-6）。"""),
    code("""def attribute_cost(total_node_hours, tenant_tokens, node_hourly):
    # TODO: total = total_node_hours * node_hourly；按 token 占比分摊
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
alloc = attribute_cost(720, {'chat': 8_000_000, 'batch': 2_000_000, 'internal': 500_000}, 32.0)
total = 720 * 32.0
print({k: round(v, 2) for k, v in alloc.items()})
assert abs(sum(alloc.values()) - total) < 1e-6, '分摊总和必须等于总成本'
assert alloc['chat'] > alloc['batch'] > alloc['internal'], '按用量排序'
assert abs(alloc['chat'] / total - 8/10.5) < 1e-9
# 边界：无用量时不应崩
empty = attribute_cost(720, {}, 32.0)
assert empty == {} or abs(sum(empty.values())) < 1e-9
print('✅ 练习 3 通过：按 token 分摊是最常用的归因方式（但对共享批处理并不完全公平）')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def optimal_spot_ratio(peak_r, p50_r, p_od, p_spot, wipeout_prob, downtime_cost_per_hour):
    baseline = p50_r
    spot = max(0, peak_r - p50_r)
    cost = baseline * p_od + spot * p_spot + wipeout_prob * downtime_cost_per_hour
    return baseline, spot, cost"""),
    code("""# 练习 2 参考答案
def can_backfill(job_nodes, job_walltime, free_nodes, now, reservation_time):
    return job_nodes <= free_nodes and now + job_walltime <= reservation_time"""),
    code("""# 练习 3 参考答案
def attribute_cost(total_node_hours, tenant_tokens, node_hourly):
    total = total_node_hours * node_hourly
    s = sum(tenant_tokens.values())
    if s == 0:
        return {k: 0.0 for k in tenant_tokens}
    return {k: total * v / s for k, v in tenant_tokens.items()}"""),
    md("""---
## 🧪 真实数据胶囊：把全课五个模块的决策汇成一张账

把模块 01–05 的每个决策，换算成对 `$/1M token` 的贡献。这是本课的最终答卷。"""),
    code("""BASE = dict(p_node_hour=32.0, t_peak_tok_s=4000, utilization=0.30, packing=0.50)
baseline_cost = cost_per_1m_tokens(**BASE)

improvements = [
    ('模块01 多阶段镜像+本地权重缓存 -> 冷启动 180s→45s',   dict(utilization=0.36)),
    ('模块02 容量按 Erlang-C 规划，不再盲目超配',           dict(utilization=0.42)),
    ('模块03 装箱调度 + 跨AZ均分（弃硬反亲和）',            dict(packing=0.78)),
    ('模块04 HPA 按队列深度 + 稳定窗口，超配减少',          dict(utilization=0.58)),
    ('模块05 基线预留 + 弹性 spot',                          dict(p_node_hour=18.0)),
]
cur = dict(BASE)
print(f'起点: ${baseline_cost:.3f} / 1M tok\\n')
prev = baseline_cost
for name, delta in improvements:
    cur.update(delta)
    c = cost_per_1m_tokens(**cur)
    print(f'{name}\\n    ${prev:.3f} -> ${c:.3f}  (本步省 {(1-c/prev):>4.0%}, 累计省 {(1-c/baseline_cost):>4.0%})\\n')
    prev = c

final = cost_per_1m_tokens(**cur)
assert final < baseline_cost / 5, f'全套优化应至少降到 1/5，实际 {baseline_cost/final:.1f}x'
print(f'✅ 累计 {baseline_cost/final:.1f} 倍改善 —— **没有一步来自换更好的 GPU 或改模型**。')
print('   这就是本课的全部论点：部署工程的复合收益，与模型优化同量级，但便宜得多。')"""),
    md("""**🧪 胶囊练习**：实现 `payback_months(engineering_days, day_rate, monthly_saving)`：
一项优化花了 `engineering_days` 人天（每人天成本 `day_rate`），每月省 `monthly_saving`。
返回**回本月数**（向上取整）；若 `monthly_saving <= 0` 返回 `None`。"""),
    code("""def payback_months(engineering_days, day_rate, monthly_saving):
    # TODO
    raise NotImplementedError"""),
    code("""# 自测
monthly_before = baseline_cost * 3000    # 假设每月 30 亿 token
monthly_after  = final * 3000
saving = monthly_before - monthly_after
m = payback_months(20, 800, saving)
assert m is not None and m >= 1
assert payback_months(20, 800, 0) is None
assert payback_months(20, 800, -5) is None
print(f'每月 30 亿 token: ${monthly_before:,.0f} -> ${monthly_after:,.0f}，月省 ${saving:,.0f}')
print(f'投入 20 人天 (${20*800:,}) -> 回本 {m} 个月')
assert m <= 2, '这类基础设施优化通常一两个月就回本'
print('✅ 胶囊练习通过：**部署优化几乎总是投入产出比最高的工程**')"""),
    code("""# 📖 胶囊参考答案
def payback_months(engineering_days, day_rate, monthly_saving):
    if monthly_saving <= 0:
        return None
    return math.ceil(engineering_days * day_rate / monthly_saving)"""),
    md("""---
## 🔧 旁注：真实系统里这些对应什么

- **三件套计价** → AWS Cost Explorer / GCP Billing 的「按服务 + 按用量类型」双维度切分；第一次做务必两个维度都看。
- **spot 中断处理** → AWS EC2 Spot ITN（`/latest/meta-data/spot/instance-action`）、GCP preemption notice；收到后触发模块 01 的优雅停机。
- **多样化 spot 池** → EC2 Fleet / Karpenter 的多实例类型 + 多 AZ 配置；SkyPilot 做跨云 spot 容错。
- **Slurm backfill** → `SchedulerType=sched/backfill`；`scontrol show job <id>` 的 `Reason` 字段告诉你为什么还在排队。
- **K8s 上的批作业排队** → Kueue（原生 gang scheduling + 配额）、Volcano；不加插件的裸 K8s 跑训练作业利用率通常很差。
- **单位经济归因** → OpenCost / Kubecost 按 namespace/label 分摊；LLM 服务还要在应用层记 `model_version` + `tenant` 的 token 计数。

至此，五个模块的链路完整：**镜像（01）→ 契约（02）→ 编排（03）→ 发布扩缩（04）→ 云与成本（05）**。"""),
    md("""### 小结
- 云只有三件套，且**计价单位不同**：计算按时间、存储按容量、网络按字节且只收出方向。**存字节便宜，搬字节贵。**
- **spot 的取舍由 `c_int` 决定，不是由折扣力度决定**；盈亏平衡中断率 `h* = (p_od − p_spot)/c_int`。
- spot 中断是**相关的**：设计时必须回答「全部 spot 消失后还剩多少容量」。标准做法是**基线（按需/预留）覆盖 P50 + 弹性 spot 覆盖峰值**。
- **K8s Job / Slurm / Ray 是三种世界观**；Slurm 的 backfill 让「`--time` 填得准」直接换来更短的排队。
- **$/1M token = p_node / (T_peak × u × η × 3600/1e6)**：四个因子边际收益相同，但改善难度天差地别。**先摘低垂的果子。**
- 全课汇总：五个模块的决策复合起来能带来一个数量级的成本改善，**没有一项依赖更好的 GPU 或更好的模型**。

🎓 **本课完结。** 你现在有了一条从「进程」到「服务」的完整链路，以及给每个环节算账的能力。
建议的下一站：**C37 MLOps**（生命周期与监控）、**C24 推理服务**（引擎内部机制）、**C39 分布式训练**（多节点工程）。"""),
]
