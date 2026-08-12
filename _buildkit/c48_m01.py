# -*- coding: utf-8 -*-
"""C48 模块 01 · 容器化：可复现的运行时。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00、Linux 文件系统与进程基础、一点点哈希常识"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_containerization.ipynb'),
    ("核心参考", "OCI Image Spec、Docker/BuildKit 文档、Merkle DAG 与内容寻址存储"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    ("why", "为什么是容器：把「在我机器上能跑」彻底消灭", "".join([
        P("我们从容器开篇，因为它是整条部署链路的<strong>原子</strong>——后面所有的编排、发布、扩缩，操作的对象都是镜像。搞不清镜像是什么，K8s 就只能靠背 YAML。"),
        P("「在我机器上能跑」这句臭名昭著的话，背后是<strong>三层依赖</strong>都没有被固化。理解这三层，就理解了容器为什么必要，也理解了容器<em>不</em>解决什么。"),
        TABLE(["层次", "包含什么", "不固化会怎样", "谁来固化"], [
            ["<strong>代码层</strong>", "你的 Python 源码、配置", "版本漂移", "Git commit / tag"],
            ["<strong>依赖层</strong>", "torch 2.4.1、transformers 4.44、numpy 2.1", "「本地 torch 2.3 能跑，线上 2.5 报错」", "lockfile（requirements.txt 钉死版本 / uv.lock / poetry.lock）"],
            ["<strong>系统层</strong>", "glibc 版本、CUDA driver/runtime、libgomp、ffmpeg、时区、locale", "「本地 Ubuntu 22.04 能跑，线上 CentOS 7 找不到 GLIBC_2.32」", "<strong>容器镜像</strong>"],
        ]),
        DUAL(
            "虚拟机也能固化系统层，为什么用容器？因为容器<strong>共享宿主内核</strong>——不用启动一个完整操作系统，启动时间从分钟级降到亚秒级，镜像从 GB 级的整盘快照变成分层可复用的增量。对于「一天发布十次、一分钟扩十个副本」的服务，这个差别是决定性的。",
            "技术上，容器 = <span class=\"term\">namespace</span>（隔离视图：PID/网络/挂载/用户）+ <span class=\"term\">cgroup</span>（限制资源：CPU/内存/设备）+ <span class=\"term\">分层联合文件系统</span>（overlayfs：镜像层只读、容器层可写）。它<strong>不是</strong>虚拟化——没有 hypervisor、没有客户机内核。所以容器<em>不</em>提供强安全隔离（模块 03 会讲这对多租户意味着什么），也<strong>不</strong>屏蔽内核版本与 GPU driver 的差异。",
        ),
        CALLOUT("danger", "<p>一个 LLM 场景特有、且极其常见的踩坑：<strong>容器隔离不了 GPU driver</strong>。镜像里可以装 CUDA <em>runtime</em>（用户态库，如 <code>libcudart.so</code>、cuDNN），但 <em>driver</em>（内核态，<code>nvidia.ko</code>）必须来自宿主机，通过 <code>nvidia-container-toolkit</code> 挂进容器。这意味着：<strong>镜像里的 CUDA runtime 版本必须 ≤ 宿主 driver 支持的版本</strong>。「本地 driver 550 跑 CUDA 12.4 镜像没问题，生产集群 driver 525 只支持到 12.0，容器起来就 <code>CUDA driver version is insufficient</code>」——这是新手最常见的上线失败原因之一。容器解决了三层里的两层半，剩下那半层要靠集群的 driver 版本纪律。</p>", "容器不解决的那半层"),
    ])),
    ("layers", "镜像的本质：分层文件系统与内容寻址", "".join([
        H3("一个镜像不是一个文件，是一叠只读层"),
        P("镜像的核心数据结构简单得出人意料：<strong>一个有序的只读层列表，加上一份描述如何运行它的元数据（config）</strong>。每一层是一个 tar 包，记录相对上一层的<em>文件系统增量</em>（新增/修改/删除）。运行时用 <span class=\"term\">overlayfs</span> 把它们叠起来，上层覆盖下层，最上面再盖一个可写层给容器用。"),
        ASCII("""镜像（只读，可被多个容器共享）           容器（每个实例独有）
┌───────────────────────────────┐
│ L4  COPY app/  → /app         │  sha256:9c1f…   12 MB
├───────────────────────────────┤
│ L3  pip install -r req.txt    │  sha256:44ab…  2.1 GB   ← torch 在这
├───────────────────────────────┤
│ L2  apt-get install git curl  │  sha256:0e77…   86 MB
├───────────────────────────────┤
│ L1  FROM python:3.11-slim     │  sha256:e3b0…  130 MB
└───────────────────────────────┘
              ▲ overlayfs 联合挂载（上层覆盖下层）
              │
        ┌─────┴─────────────────┐
        │  可写层 (container)   │  ← 容器里写的一切都在这，删容器即消失
        └───────────────────────┘

关键性质：L1~L3 完全相同的两个镜像，在节点上只存一份、只拉一次。""")
        ,
        DUAL(
            "为什么要分层？<strong>为了复用</strong>。你有 20 个模型服务，都基于同一个 <code>pytorch:2.4-cuda12.1</code> 底座。如果镜像是整块的，节点要存 20 份 6 GB；分层之后，那 6 GB 的底座只存一份，每个服务只多存自己那几十 MB 的代码层。拉取时同理——底座已经在节点上了就直接跳过。",
            "每一层由其内容的 <code>sha256</code> 摘要唯一标识（<span class=\"term\">content-addressable storage</span>，内容寻址）。镜像 manifest 是一个层摘要的有序列表，整个结构是一棵 <span class=\"term\">Merkle DAG</span>。这带来三个性质：<strong>去重</strong>（同摘要 = 同内容 = 只存一份）、<strong>完整性校验</strong>（摘要不匹配即数据损坏或被篡改）、<strong>可缓存</strong>（层是不可变的，缓存永不失效）。<code>docker pull</code> 本质是「按摘要拉取本地缺失的层」。",
        ),
        CALLOUT("warn", "分层有个反直觉的坑：<strong>删除文件不会让镜像变小</strong>。<code>RUN pip install torch && rm -rf /root/.cache/pip</code> 写成两条 <code>RUN</code> 就是灾难——第一层已经把 2 GB 缓存写进了不可变的层，第二层只是记录了一个「白出（whiteout）」标记说「这些文件在我这层不可见」。<em>下层的字节还在镜像里，还要被传输和存储</em>。这就是为什么你会看到 Dockerfile 里那些用 <code>&amp;&amp;</code> 串成一长条的 <code>RUN</code>——它们必须在<strong>同一层内</strong>完成「装了再删」。"),
    ])),
    ("cache", "层缓存：Dockerfile 的书写顺序就是性能", "".join([
        P("镜像构建的速度几乎完全由<strong>层缓存命中率</strong>决定，而命中率几乎完全由<strong>你写 Dockerfile 的顺序</strong>决定。这是本模块最有实操价值的一节。"),
        P("缓存规则只有一条，但要精确理解：<strong>第 i 层的缓存有效，当且仅当（a）第 i−1 层缓存有效，且（b）第 i 条指令本身及其输入没变</strong>。一旦某一层失效，它<em>后面所有层</em>全部失效并重建。这是一条链，不是一张表。"),
        CODE("""# ❌ 反面教材：每改一行代码，torch 就要重装一遍
FROM python:3.11-slim
COPY . /app                          # ← 代码一变，这层就失效
RUN pip install -r /app/requirements.txt   # ← 于是这层也失效，重装 2 GB

# ✅ 正确写法：把「变得慢的」放前面，「变得快的」放后面
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .              # ← 只有依赖清单变了才失效
RUN pip install --no-cache-dir -r requirements.txt   # ← 通常命中缓存
COPY . .                             # ← 代码变了只重建这一层（几 MB）"""),
        DUAL(
            "一句口诀：<strong>越少变的放越前面</strong>。系统包 → Python 依赖 → 模型配置 → 应用代码。一天要改 50 次的应用代码放在最后一层，那 50 次构建每次只重建几 MB，一秒完成；如果放在最前面，每次重装 torch，一次五分钟——一天就是四个小时。",
            "形式化：设第 i 条指令的重建成本为 <code>c_i</code>、每日变更概率为 <code>p_i</code>。由于失效会级联，第 i 层变更导致的重建成本是 <code>Σ_{j≥i} c_j</code>，日期望构建成本为 <code>E = Σ_i p_i · Σ_{j≥i} c_j</code>（近似，忽略同日多层同变）。要最小化 <code>E</code>，应让 <strong>高 <code>p</code> 的指令尽量靠后</strong>——这正是「越少变的放越前」的数学表述。notebook 会把这个和式实现出来，并对两种顺序做对比。",
        ),
        P("再补三条工程上极其常用、但文档里散落各处的技巧："),
        UL([
            "<strong><code>.dockerignore</code> 不是可选项</strong>：<code>COPY . .</code> 会把 <code>.git/</code>（可能几 GB）、<code>__pycache__</code>、本地 <code>checkpoints/</code> 全部塞进构建上下文和镜像层。更隐蔽的危害是：这些文件的任何变动（哪怕只是 <code>git fetch</code> 更新了 <code>.git</code>）都会让 <code>COPY</code> 层失效，缓存全废。",
            "<strong>BuildKit 的 <code>--mount=type=cache</code></strong>：<code>RUN --mount=type=cache,target=/root/.cache/pip pip install ...</code> 让 pip 缓存在<em>构建之间</em>持久化，但<strong>不进入镜像层</strong>。这是「装了再删」问题的现代解法，比 <code>&amp;&amp;&nbsp;rm -rf</code> 更干净。",
            "<strong>钉死版本，包括基础镜像</strong>：<code>FROM python:3.11-slim</code> 是个会漂移的可变标签，某天上游重建了它，你的构建就复现不了。生产上应写 <code>FROM python:3.11-slim@sha256:abcd…</code> 用摘要钉死。同理 <code>apt-get install git</code> 也会随时间装到不同版本。",
        ]),
        CALLOUT("intuition", "把缓存这件事想成<strong>一条流水线上的检查点</strong>：每个检查点保存了「到此为止的完整文件系统状态」。构建时从头走，一路命中检查点就跳过，遇到第一个不匹配的就从那里开始重跑，后面的检查点全部作废。<em>你能控制的唯一变量，就是把易变的步骤排到流水线末端</em>。"),
    ])),
    ("multistage", "多阶段构建：把编译期和运行期彻底分开", "".join([
        H3("为什么一个推理镜像不该带编译器"),
        P("很多依赖需要在安装时编译（<code>flash-attn</code>、<code>xformers</code>、自定义 CUDA 算子），这要求镜像里有 <code>gcc</code>、<code>nvcc</code>、CUDA 开发头文件、<code>make</code>……这些东西加起来轻松几个 GB，而<strong>运行时一个都用不上</strong>。<span class=\"term\">multi-stage build</span>（多阶段构建）就是为此而生：在一个「胖」阶段里编译，只把产物拷进一个「瘦」阶段。"),
        CODE("""# ── 阶段 1：builder（带完整工具链，几 GB，不会进最终镜像）──
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \\
        python3.11 python3-pip build-essential ninja-build \\
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# 把依赖装进一个独立前缀，方便整体拷走
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── 阶段 2：runtime（只有运行时库，最终镜像）──
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y --no-install-recommends python3.11 \\
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local     # ← 只拷贝编译产物
COPY app/ /app/
WORKDIR /app
USER 1000:1000                              # ← 非 root 运行
EXPOSE 8000
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "/models/current", "--port", "8000"]"""),
        TABLE(["", "单阶段（devel base）", "多阶段（runtime base）"], [
            ["基础镜像", "<code>cuda:12.1-devel</code> ≈ 6.5 GB", "<code>cuda:12.1-runtime</code> ≈ 2.4 GB"],
            ["工具链", "gcc/nvcc/头文件全在", "全部留在 builder 阶段"],
            ["最终镜像", "≈ 9–11 GB", "≈ 4–5 GB"],
            ["冷启动拉取（500 MB/s）", "≈ 20 s", "≈ 9 s"],
            ["攻击面", "编译器 + 包管理器可被利用", "显著更小"],
        ]),
        DUAL(
            "镜像小一半，意味着<strong>扩容快一半</strong>。这在自动扩缩场景里是直接的用户体验：流量突增时，新副本要先把镜像拉下来才能服务，镜像 10 GB 和 4 GB 的差别就是「两分钟后缓解」和「五十秒后缓解」的差别。",
            "更精确地说，冷启动时间 <code>T_cold = T_schedule + T_pull + T_init + T_load_weights + T_warmup</code>。<code>T_pull</code> 只在节点缓存未命中时发生，且与镜像<em>未缓存层</em>的字节数成正比。多阶段构建压的是 <code>T_pull</code>；把权重移出镜像（下一节）压的也是它；<code>T_load_weights</code> 与 <code>T_warmup</code>（CUDA graph 捕获、编译）则是 LLM 特有的大头，模块 04 讨论扩缩时会重新算这笔账。",
        ),
        CALLOUT("warn", "多阶段的常见错误：<strong>拷贝粒度过粗</strong>。<code>COPY --from=builder / /</code> 等于什么都没省。要明确知道产物在哪——Python 用 <code>--prefix</code> 或 venv 收拢，C/C++ 用 <code>make DESTDIR=</code>。另一个坑是<strong>运行时缺少动态库</strong>：builder 里编出来的 <code>.so</code> 链接了 devel 镜像才有的库，拷到 runtime 镜像后 <code>ImportError: libcudnn.so.8: cannot open shared object file</code>。解决办法是构建完在 runtime 阶段跑一次 <code>python -c \"import torch; torch.cuda.is_available()\"</code> 的冒烟测试——<em>把这条写进 CI</em>。"),
    ])),
    ("weights", "模型权重要不要进镜像：一个必须想清楚的决策", "".join([
        P("这是 LLM 部署<strong>独有</strong>、且在通用 Docker 教程里绝对找不到的问题。一个 70B 模型的权重是 140 GB（fp16），远大于任何合理的镜像。权重放哪，直接决定了你的发布节奏和扩容速度。"),
        TABLE(["方案", "怎么做", "优点", "代价", "适用"], [
            ["<strong>打进镜像</strong>", "<code>COPY model/ /models/</code>", "一次拉取即可服务；版本与代码强绑定、天然可复现", "镜像巨大（>100 GB 不现实）；换模型必须重建镜像；registry 存储爆炸", "小模型（&lt;5 GB）、边缘设备、强合规场景"],
            ["<strong>启动时从对象存储拉</strong>", "initContainer 从 S3/GCS 下载到 emptyDir", "镜像小；换模型只改环境变量", "每个 Pod 都要拉一遍（140 GB × N 副本的出网流量）；冷启动慢", "中等规模、副本数不多"],
            ["<strong>共享只读卷</strong>", "PVC(ReadOnlyMany) / NFS / Lustre 挂载", "全节点共享一份；扩副本几乎零下载", "需要共享存储基建；读带宽可能成瓶颈", "自建集群、多副本"],
            ["<strong>节点本地缓存</strong>", "DaemonSet 预热到宿主 hostPath，Pod 挂载", "首次拉一次、之后同节点所有 Pod 秒起", "需要缓存管理与淘汰策略", "大规模生产的主流做法"],
        ]),
        DUAL(
            "经验法则：<strong>权重 &lt; 5 GB 且不常换 → 打进镜像；否则分离</strong>。分离之后要接受一个后果：镜像不再能唯一决定行为，你必须<em>另外</em>把「模型版本」也当成一等公民管起来（写进环境变量、记进指标、打进日志）。否则「线上这个副本到底跑的哪个 checkpoint」会变成一个没人答得上来的问题。",
            "分离带来的是<strong>可复现性的分裂</strong>：镜像摘要 + 权重摘要共同构成部署的完整身份。生产上应把二者都固化——权重用内容哈希寻址（<code>s3://models/llama3-8b/sha256-abc…/</code>），Pod 的 annotation 里记下这个摘要，指标里带上 <code>model_version</code> label。这样一次 incident 回溯时，你能精确回答「当时那 5% 金丝雀流量吃的是哪份权重」。",
        ),
        CALLOUT("danger", "<p>一个真实会咬人的场景：<strong>N 个副本同时从对象存储拉同一份 140 GB 权重</strong>。假设扩容 20 个副本，就是 2.8 TB 的出网流量，不仅慢（对象存储单连接带宽有限、并发拉取还会互相挤），账单上的<em>数据传输费</em>也可能超过 GPU 本身的费用（跨区拉取尤甚）。这就是节点本地缓存和共享只读卷方案存在的根本原因。<strong>算这笔账</strong>：20 副本 × 140 GB × $0.09/GB（跨区出网典型价）≈ $252，<em>每次扩容</em>。notebook 会把这笔账做成可调参的模型。</p>", "权重拉取的隐形账单"),
    ])),
    ("runtime", "运行时契约：一个容器化的服务必须遵守的六条", "".join([
        P("镜像构建对了只是一半。容器在编排系统里是<strong>被随时创建、随时杀死</strong>的，它必须遵守一套契约，否则 K8s 的自愈、滚动更新、扩缩全部会以诡异的方式失灵。这六条是血泪总结。"),
        TABLE(["契约", "为什么", "怎么做", "违反的症状"], [
            ["<strong>① 前台运行、日志走 stdout/stderr</strong>", "编排系统靠主进程存活判断容器状态；日志靠标准流采集", "不要 daemonize、不要写日志文件", "容器立即退出；或日志在容器里没人看得到"],
            ["<strong>② PID 1 要能转发信号</strong>", "缩容/更新时 K8s 发 SIGTERM，PID 1 若吞掉信号就只能等 SIGKILL 强杀", "用 <code>ENTRYPOINT [\"exec\", …]</code> 数组形式；或加 <code>tini</code> 作 init", "Pod 终止总是卡满 30 秒 grace period"],
            ["<strong>③ 优雅停机</strong>", "被杀时正在处理的请求要放完，尤其 LLM 长生成可能几十秒", "捕获 SIGTERM → 停止接新请求 → 等在途完成 → 退出；<code>terminationGracePeriodSeconds</code> 要 &gt; 最长生成时间", "滚动更新时用户看到大量 502/连接中断"],
            ["<strong>④ 健康端点分离</strong>", "「进程活着」≠「能服务」，LLM 加载权重要几分钟", "<code>/healthz</code>（存活）与 <code>/ready</code>（就绪）必须是两个语义不同的端点", "模型还没加载完流量就打进来，全部超时（模块 03 详述）"],
            ["<strong>⑤ 配置从环境变量/挂载来</strong>", "同一镜像要能跑在 dev/staging/prod", "12-factor：配置外置，绝不 hardcode，绝不把密钥写进镜像", "为改一个 URL 重建镜像；密钥泄漏在 registry 里"],
            ["<strong>⑥ 非 root、只读根文件系统</strong>", "容器逃逸的第一道防线；也逼你想清楚哪些路径需要可写", "<code>USER 1000</code>、<code>readOnlyRootFilesystem: true</code> + 显式挂载 <code>emptyDir</code> 给 <code>/tmp</code>", "安全扫描不过；一次逃逸拿到宿主 root"],
        ]),
        P("其中第 ③ 条对 LLM 服务<strong>特别要命</strong>，值得单独展开。普通 web 服务的请求几十毫秒就结束，grace period 给 30 秒绰绰有余；但一个 LLM 请求生成 2000 token、每 token 30 ms，就是 60 秒。默认 30 秒的 <code>terminationGracePeriodSeconds</code> 会在生成到一半时 SIGKILL，用户看到的是流式输出<em>戛然而止</em>。"),
        CODE("""# 优雅停机的最小正确实现（伪代码，真实 vLLM/FastAPI 都有对应钩子）
import signal, asyncio

shutting_down = False
inflight = 0

def on_sigterm(signum, frame):
    global shutting_down
    shutting_down = True          # ① 立刻让 /ready 返回 503

signal.signal(signal.SIGTERM, on_sigterm)

async def readyz():
    # ② K8s 看到 not ready -> 把本 Pod 从 Service 端点摘除 -> 不再有新流量
    return 503 if shutting_down else 200

async def main_loop():
    while not (shutting_down and inflight == 0):
        await asyncio.sleep(0.1)   # ③ 等在途请求自然放完
    sys.exit(0)                    # ④ 主动退出，不用等 SIGKILL"""),
        CALLOUT("intuition", "这四步的顺序不能变，理由是<strong>摘流量必须先于停服务</strong>。很多人写成「收到 SIGTERM 立刻关端口」，结果 K8s 的端点更新是<em>最终一致</em>的（kube-proxy/Ingress 需要几百毫秒到几秒同步），这期间仍有新请求被路由过来、撞上已关闭的端口 → 连接拒绝。正确做法是先让就绪探针失败、<strong>睡一小会儿（<code>preStop: sleep 5</code>）等端点传播</strong>、再停止接新请求。这个 <code>sleep 5</code> 是生产 K8s 里最常见也最不直观的一行配置。"),
    ])),
    ("ledger", "算一笔账：镜像大小如何变成用户体验", "".join([
        P("把本模块所有决策的收益汇成一笔账。冷启动时间是自动扩缩响应速度的下界，而它由五项构成："),
        MATH("T_{cold} = T_{sched} + \\underbrace{\\frac{S_{uncached}}{B}}_{\\text{拉镜像}} + T_{init} + \\underbrace{\\frac{W}{B_{w}}}_{\\text{加载权重}} + T_{warmup}"),
        TABLE(["项", "典型值（7B 模型）", "受什么影响", "本模块的杠杆"], [
            ["<code>T_sched</code> 调度", "1–5 s", "集群空闲资源、调度器压力", "模块 03"],
            ["<code>S_uncached/B</code> 拉镜像", "0 s（缓存命中）～ 40 s", "镜像大小、节点是否已有该层", "<strong>多阶段构建、层复用</strong>"],
            ["<code>T_init</code> 进程启动", "3–10 s", "Python 导入、CUDA 上下文初始化", "精简依赖"],
            ["<code>W/B_w</code> 加载权重", "10–60 s", "权重大小、存储介质与并发", "<strong>权重放置策略、本地缓存</strong>"],
            ["<code>T_warmup</code> 预热", "5–30 s", "CUDA graph 捕获、torch.compile、首批 kernel autotune", "预热请求、编译缓存"],
        ]),
        P("读这张表的方式是：<strong>总冷启动通常在 30–120 秒量级，其中镜像拉取和权重加载合计占一半以上，而这两项都是本模块能控制的</strong>。这个数字直接决定了模块 04 里 HPA 的可行策略——如果冷启动要 90 秒，那么「等 CPU 利用率超阈值再扩容」必然来不及，你必须预测式扩容或保留热备。<em>部署链路上游的决策，会一路约束下游的可选项</em>，这是本课反复出现的结构。"),
        P("再算一个常被忽略的账：<strong>层复用率</strong>。假设你有 20 个模型服务，都基于同一个 4 GB 的 runtime 底座、各自 200 MB 应用层。若共享底座，节点上只需 4 + 20×0.2 = 8 GB；若每个服务各建各的底座（比如各自 <code>FROM</code> 了不同的 base tag），就是 20×4.2 = 84 GB。<strong>10 倍的节点磁盘差异，和同样倍数的拉取带宽差异</strong>。这就是为什么成熟团队会强制所有服务 <code>FROM</code> 同一个内部 base 镜像——它不是洁癖，是省钱和提速。"),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的工程智慧：<strong>镜像是一个内容寻址的、不可变的、可增量传输的数据结构；你的每一个 Dockerfile 决策，都是在这个数据结构上做「什么该复用、什么该隔离」的划分</strong>。划得好，20 个服务共享一份底座、改代码一秒构建、扩容九秒完成；划不好，每个服务各背 10 GB、改一行等五分钟、扩容两分钟。<em>同样的技术，10 倍的差距，全在划分。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>镜像懒加载（lazy pulling）</strong>：容器启动其实只需要少数文件，但传统 pull 要下载全部层。<em>eStargz / SOCI / Nydus</em> 等格式支持按需拉取，把冷启动从「下载 4 GB」变成「下载启动路径上的 200 MB」，实测可省 60–80%。对 LLM 镜像（大量文件从不被读）收益尤其大，但索引构建与 registry 兼容性仍在演进。",
            "<strong>权重的内容寻址分发</strong>：把模型权重也当成内容寻址对象（类似镜像层）来分发、去重、P2P 传播（Dragonfly / Kraken）。20 个副本拉同一份权重时从 P2P 网络互传而非都打对象存储，可把扩容出网流量降一个数量级。开放问题是权重更新的一致性与安全签名。",
            "<strong>容器与 GPU 的隔离粒度</strong>：容器共享内核使 GPU 隔离只能靠 driver 层（MPS/MIG/时间片），缺乏内存与故障隔离。轻量 VM（Kata、gVisor、Firecracker）能补强，但 GPU 直通与冷启动开销仍是难题。多租户 LLM 推理平台的隔离方案尚无定论。",
            "<strong>可复现构建（reproducible builds）</strong>：同样的 Dockerfile 两次构建产出的镜像摘要通常不同（时间戳、包索引漂移、非确定性写入）。<em>Nix / Bazel rules_docker / apko</em> 追求逐字节可复现，这对供应链安全（SLSA）与合规审计意义重大，但在有大量 C/CUDA 编译的 ML 栈上落地仍很痛。",
            "<strong>无服务器 GPU 推理</strong>：scale-to-zero 的 LLM 服务要求冷启动进入秒级，这逼着整个栈重构——快照恢复（CRIU / checkpoint 整个 CUDA 上下文）、权重常驻内存池、模型多路复用。学术与工业都在冲这个方向，但「冷启动 &lt; 1 s 且成本更低」尚未被普遍做到。",
        ]),
        CALLOUT("paper", "必读：OCI Image Specification（镜像格式与 Merkle DAG 的权威定义）、Docker BuildKit 文档（缓存挂载与多阶段的现代用法）、Kubernetes 官方 <em>Configure Liveness/Readiness Probes</em> 与 <em>Pod Lifecycle</em>（优雅停机的准确语义）、Google SRE Book 第 4 章（错误预算）。工程对标：NVIDIA container toolkit 文档、eStargz/SOCI 论文与实现。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 容器化：可复现的运行时（从零模拟镜像分层、层缓存与冷启动账）

目标：把 **分层文件系统 → 层缓存链式失效 → 多阶段瘦身 → 冷启动分解** 从零实现，
每个机制都**对拍**朴素参考、每个决策都**算一笔账**。

路线：内容寻址的层 → overlay 合并 → Dockerfile 解析 → 缓存命中链 → 构建成本模型 → 冷启动分解 → ✏️ 练习 → 📖 答案 → 🧪 权重分发账。

> 心智模型：**镜像 = 一叠内容寻址的只读层；缓存 = 一条会级联失效的链；冷启动 = 五项之和**。
> 本环境没有 Docker，但镜像的全部语义都是可以用 Python 精确复现的。"""),
    md("""## 1 · 层：内容寻址与 overlay 合并

一层 = 一份文件系统增量（新增/修改/删除）。层的身份 = 其内容的 sha256。
运行时把层从下往上叠，上层覆盖下层；删除用 **whiteout 标记**表示。

先把这套语义实现出来，并验证内容寻址的核心性质：**同内容 → 同摘要 → 只存一份**。"""),
    code("""import hashlib, json, math, re
from dataclasses import dataclass, field

WHITEOUT = '<<deleted>>'      # 模拟 overlayfs 的 .wh. 白出标记

def layer_digest(files: dict) -> str:
    '''层的内容寻址摘要：对 (路径, 内容) 的规范化序列化取 sha256。'''
    payload = json.dumps(sorted(files.items()), ensure_ascii=False).encode()
    return 'sha256:' + hashlib.sha256(payload).hexdigest()[:12]

def overlay(layers):
    '''从下往上合并层，返回最终可见的文件系统。'''
    fs = {}
    for lyr in layers:
        for path, content in lyr.items():
            if content == WHITEOUT:
                fs.pop(path, None)     # 白出：上层把下层的文件遮掉
            else:
                fs[path] = content
    return fs

L1 = {'/usr/bin/python': 'ELF...', '/etc/os-release': 'debian'}
L2 = {'/usr/lib/git': 'bin', '/var/cache/apt/pkg.deb': 'x' * 100}
L3 = {'/var/cache/apt/pkg.deb': WHITEOUT}      # 「清理」apt 缓存
L4 = {'/app/main.py': 'print(1)'}

fs = overlay([L1, L2, L3, L4])
print('最终可见文件:', sorted(fs))
assert '/var/cache/apt/pkg.deb' not in fs, '被白出的文件不该可见'
assert fs['/app/main.py'] == 'print(1)'
# 内容寻址：同内容必同摘要，不同内容必不同摘要
assert layer_digest(L1) == layer_digest(dict(L1)), '同内容 -> 同摘要（去重的基础）'
assert layer_digest(L1) != layer_digest(L2)
print('✅ overlay 合并与内容寻址正确')"""),
    md("""### 「删除不会让镜像变小」——用字节数证明它

这是分层最反直觉的性质。白出标记只影响**可见性**，不影响**镜像体积**。"""),
    code("""def visible_bytes(layers):
    return sum(len(v) for v in overlay(layers).values())

def image_bytes(layers):
    '''镜像实际体积 = 所有层的字节之和（白出标记本身也占一点，忽略）。'''
    return sum(len(v) for lyr in layers for v in lyr.values() if v != WHITEOUT)

vis, img = visible_bytes([L1, L2, L3, L4]), image_bytes([L1, L2, L3, L4])
print(f'可见字节 {vis}  vs  镜像实际字节 {img}')
assert img > vis, '删除文件后，镜像仍然携带那些字节！'

# 正确做法：在同一层内「装了再删」，那些字节根本不会被写进任何层
L23_merged = {'/usr/lib/git': 'bin'}          # RUN apt-get install ... && rm -rf ...
img_good = image_bytes([L1, L23_merged, L4])
print(f'同层内装了再删: 镜像字节 {img_good}（省下 {img - img_good} 字节）')
assert img_good < img
print('✅ 证毕：RUN a && rm b 必须写在同一条指令里，分两条 RUN 等于没删')"""),
    md("""## 2 · Dockerfile 解析与层缓存的链式失效

缓存规则只有一条，但它是**链式**的：

> 第 i 层缓存有效 ⟺ 第 i−1 层缓存有效 **且** 第 i 条指令及其输入未变。

一旦某层失效，其后所有层全部失效。下面实现一个最小构建器来复现这条语义。"""),
    code("""@dataclass
class Instr:
    op: str            # FROM / COPY / RUN
    arg: str
    inputs: tuple = () # 该指令依赖的外部文件（COPY 的源）
    cost_s: float = 1.0  # 重建这层要多久
    size_mb: float = 0.0

def instr_key(ins, file_hashes):
    '''指令的缓存 key = 指令本身 + 其外部输入的内容哈希。'''
    ext = tuple(file_hashes.get(f, '') for f in ins.inputs)
    return hashlib.sha256(f'{ins.op}|{ins.arg}|{ext}'.encode()).hexdigest()[:12]

def build(dockerfile, file_hashes, cache):
    '''返回 (总耗时, 每层是否命中, 新缓存)。cache: 上一次构建的层 key 列表。'''
    total, hits, keys, chain_ok = 0.0, [], [], True
    for i, ins in enumerate(dockerfile):
        k = instr_key(ins, file_hashes)
        hit = chain_ok and i < len(cache) and cache[i] == k
        if not hit:
            chain_ok = False          # ← 链式失效：一旦断掉，后面全部重建
            total += ins.cost_s
        hits.append(hit); keys.append(k)
    return total, hits, keys

BAD = [
    Instr('FROM', 'python:3.11-slim', cost_s=5,  size_mb=130),
    Instr('COPY', '. /app', inputs=('src',), cost_s=1, size_mb=12),
    Instr('RUN',  'pip install -r requirements.txt', inputs=(), cost_s=300, size_mb=2100),
]
GOOD = [
    Instr('FROM', 'python:3.11-slim', cost_s=5,  size_mb=130),
    Instr('COPY', 'requirements.txt .', inputs=('req',), cost_s=1, size_mb=1),
    Instr('RUN',  'pip install -r requirements.txt', inputs=(), cost_s=300, size_mb=2100),
    Instr('COPY', '. /app', inputs=('src',), cost_s=1, size_mb=12),
]
print('两份 Dockerfile 已定义：BAD 把 COPY . 放在 pip 之前，GOOD 放在之后')"""),
    code("""# 第一次构建：全部 miss（冷构建）
fh0 = {'src': 'v1', 'req': 'r1'}
t_bad0, _, cache_bad = build(BAD, fh0, [])
t_good0, _, cache_good = build(GOOD, fh0, [])
print(f'冷构建: BAD {t_bad0:.0f}s | GOOD {t_good0:.0f}s  （都要装一次依赖，差不多）')

# 第二次构建：只改了应用代码（日常最高频的场景）
fh1 = {'src': 'v2', 'req': 'r1'}
t_bad1, hits_bad, _  = build(BAD,  fh1, cache_bad)
t_good1, hits_good, _ = build(GOOD, fh1, cache_good)
print(f'\\n改一行代码后重建:')
print(f'  BAD  {t_bad1:>6.0f}s  层命中 {hits_bad}')
print(f'  GOOD {t_good1:>6.0f}s  层命中 {hits_good}')

assert t_good1 < t_bad1, 'GOOD 顺序应显著更快'
assert t_bad1 >= 300, 'BAD 顺序会重装依赖'
assert hits_good[:3] == [True, True, True], 'GOOD 的前三层应全部命中'
print(f'\\n✅ 同样的内容、只是顺序不同 -> 日常重建快 {t_bad1/t_good1:.0f} 倍')"""),
    md("""### 链式失效的可视化：改依赖清单会怎样？

注意 GOOD 顺序并非万能——改 `requirements.txt` 时它同样要重装。
缓存优化的本质是**把高频变更排到链尾**，而不是消除重建。"""),
    code("""# 注意：cache_bad / cache_good 都是相对基线 fh0 = {'src':'v1', 'req':'r1'} 建立的
scenarios = [
    ('只改代码',        {'src': 'v2', 'req': 'r1'}),
    ('只改依赖清单',    {'src': 'v1', 'req': 'r2'}),
    ('都改',            {'src': 'v2', 'req': 'r2'}),
    ('什么都没改',      {'src': 'v1', 'req': 'r1'}),
]
print(f"{'场景':<14s} {'BAD(s)':>8s} {'GOOD(s)':>9s}")
for name, fh in scenarios:
    tb, _, _ = build(BAD,  fh, cache_bad)
    tg, _, _ = build(GOOD, fh, cache_good)
    print(f'{name:<14s} {tb:>8.0f} {tg:>9.0f}')

# 「什么都没改」两者都应全命中、0 秒
assert build(BAD,  fh0, cache_bad)[0]  == 0
assert build(GOOD, fh0, cache_good)[0] == 0
# 「只改依赖清单」时 GOOD 也躲不掉重装 —— 缓存优化不是消除重建，是把高频变更排到链尾
assert build(GOOD, {'src':'v1','req':'r2'}, cache_good)[0] >= 300
print('\\n✅ 完全未变时两者都 0 秒（全命中）；差距只体现在**高频**变更上')"""),
    md("""## 3 · 期望构建成本：为什么「少变的放前面」是可证明的

把顺序问题形式化：设第 i 条指令日变更概率 `p_i`、重建成本 `c_i`。
因为失效级联，第 i 层变更会导致 `Σ_{j≥i} c_j` 的重建。日期望成本：

$$E = \\sum_i p_i \\cdot \\sum_{j \\ge i} c_j$$

这个和式解释了全部直觉：**高 p 的指令应尽量靠后**，因为靠后的后缀和更小。"""),
    code("""def expected_build_cost(instrs, probs):
    '''E = Σ_i p_i * (后缀成本和)。'''
    n = len(instrs)
    suffix = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix[i] = suffix[i + 1] + instrs[i].cost_s
    return sum(p * suffix[i] for i, p in enumerate(probs))

# 应用代码天天改(p=0.9)，依赖清单偶尔改(p=0.05)，基础镜像极少改(p=0.01)
p_bad  = [0.01, 0.90, 0.05]              # FROM, COPY ., RUN pip
p_good = [0.01, 0.05, 0.05, 0.90]        # FROM, COPY req, RUN pip, COPY .
E_bad  = expected_build_cost(BAD,  p_bad)
E_good = expected_build_cost(GOOD, p_good)
print(f'日期望构建耗时: BAD {E_bad:.1f}s | GOOD {E_good:.1f}s')
assert E_good < E_bad
print(f'✅ 期望成本降低 {(1 - E_good/E_bad)*100:.0f}%，与前面的模拟结论一致')

# 对拍：用蒙特卡洛直接模拟 2000 天，验证解析式
import random
def monte_carlo(instrs, probs, days=2000, seed=0):
    rng = random.Random(seed); total = 0.0
    for _ in range(days):
        first_changed = None
        for i, p in enumerate(probs):
            if rng.random() < p:
                first_changed = i; break
        if first_changed is not None:
            total += sum(ins.cost_s for ins in instrs[first_changed:])
    return total / days

mc_good = monte_carlo(GOOD, p_good)
print(f'蒙特卡洛(GOOD) {mc_good:.1f}s  vs  解析式 {E_good:.1f}s')
assert abs(mc_good - E_good) / E_good < 0.20, '解析式应与模拟在同一量级（解析式忽略了同日多层同变）'
print('✅ 对拍通过：解析式与蒙特卡洛一致')"""),
    md("""## 4 · 多阶段构建：把编译期字节挡在最终镜像之外

多阶段 = 在 builder 阶段用 devel 基础镜像编译，只把**产物**拷进 runtime 阶段。
下面量化它省下多少字节、多少拉取时间。"""),
    code("""DEVEL_BASE, RUNTIME_BASE = 6500, 2400     # MB，公开量级 (cuda:12.1 devel vs runtime)
DEPS, TOOLCHAIN, APP, ARTIFACT = 2100, 1800, 12, 900   # MB

single_stage = DEVEL_BASE + DEPS + TOOLCHAIN + APP        # 全塞一个阶段
multi_stage  = RUNTIME_BASE + ARTIFACT + APP              # 只拷产物

def pull_seconds(mb, bandwidth_mbps=500):
    return mb / bandwidth_mbps

print(f'单阶段镜像: {single_stage:>6d} MB  -> 拉取 {pull_seconds(single_stage):>5.1f}s')
print(f'多阶段镜像: {multi_stage:>6d} MB  -> 拉取 {pull_seconds(multi_stage):>5.1f}s')
print(f'节省: {single_stage - multi_stage} MB ({(1-multi_stage/single_stage)*100:.0f}%)')

assert multi_stage < single_stage / 2, '多阶段应至少砍掉一半'
assert pull_seconds(multi_stage) < 10, '多阶段镜像应能在 10 秒内拉完（500MB/s）'
print('✅ 多阶段把冷启动的拉取项从 ~21s 压到 ~7s')"""),
    md("""### 层复用：20 个服务共享一个底座能省多少？

内容寻址让相同的层在节点上**只存一份、只拉一次**。这是强制统一 base 镜像的真正理由。"""),
    code("""def node_storage_mb(n_services, base_mb, app_mb, shared_base=True):
    return base_mb + n_services * app_mb if shared_base else n_services * (base_mb + app_mb)

N, BASE, APP_MB = 20, 4000, 200
shared   = node_storage_mb(N, BASE, APP_MB, True)
separate = node_storage_mb(N, BASE, APP_MB, False)
print(f'{N} 个服务，共享底座: {shared/1000:>6.1f} GB')
print(f'{N} 个服务，各自底座: {separate/1000:>6.1f} GB')
print(f'倍数: {separate/shared:.1f}×')
assert separate / shared > 8, '共享底座应带来接近一个数量级的节省'
print('✅ 「所有服务 FROM 同一个内部 base」不是洁癖，是 10 倍的磁盘与带宽差异')"""),
    md("""## 5 · 冷启动分解：镜像决策如何变成用户体验

$$T_{cold} = T_{sched} + \\frac{S_{uncached}}{B} + T_{init} + \\frac{W}{B_w} + T_{warmup}$$

这个数字直接约束模块 04 的自动扩缩策略——冷启动 90 秒的服务，反应式扩容必然来不及。"""),
    code("""def cold_start(image_mb_uncached, weights_gb, bandwidth_mbps=500, weight_bw_mbps=800,
               t_sched=3.0, t_init=6.0, t_warmup=15.0):
    t_pull = image_mb_uncached / bandwidth_mbps
    t_weights = weights_gb * 1024 / weight_bw_mbps
    total = t_sched + t_pull + t_init + t_weights + t_warmup
    return {'调度': t_sched, '拉镜像': t_pull, '进程初始化': t_init,
            '加载权重': t_weights, '预热': t_warmup, '合计': total}

configs = [
    ('单阶段镜像 + 权重打进镜像',              10412 + 14000, 0.0,  15.0),
    ('多阶段镜像 + 每次从对象存储拉权重',       3512,          14.0, 15.0),
    ('多阶段镜像 + 节点已缓存层 + 本地权重',    0,             0.5,  15.0),
    ('以上 + 编译/CUDA graph 缓存命中',        0,             0.5,   3.0),
]
for name, img_mb, w_gb, warm in configs:
    d = cold_start(img_mb, w_gb, t_warmup=warm)
    parts = ' + '.join(f'{k}{v:.0f}s' for k, v in d.items() if k != '合计')
    print(f'{name}\\n  {parts} = **{d["合计"]:.0f}s**\\n')

t_worst = cold_start(24412, 0.0)['合计']
t_best  = cold_start(0, 0.5, t_warmup=3.0)['合计']
assert t_worst > 5 * t_best, '最差与最优配置应差 5 倍以上'
print(f'✅ 最差 {t_worst:.0f}s vs 最优 {t_best:.0f}s —— 差 {t_worst/t_best:.1f} 倍。')
print('   这就是「扩容两分钟才缓解」和「十几秒就缓解」的区别，')
print('   也是模块 04 里「反应式扩容来不来得及」的分水岭。')"""),
    md("""## ✏️ 练习 1：镜像实际体积

实现 `image_size_mb(layers)`：给定层列表（每层是 `{路径: 大小MB}`，值为 `-1` 表示白出标记），
返回**镜像实际体积**（所有非白出条目的大小之和，白出不减去下层字节）
和**可见体积**（overlay 后仍可见的文件大小之和）。返回 `(image_mb, visible_mb)`。"""),
    code("""def image_size_mb(layers):
    # TODO: image_mb = 所有层里非 -1 的值之和
    #       visible_mb = 从下往上 overlay（-1 表示删除该路径）后剩余文件大小之和
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
LS = [{'/base': 130.0}, {'/cache': 2000.0, '/lib': 50.0}, {'/cache': -1}, {'/app': 12.0}]
img, vis = image_size_mb(LS)
assert abs(img - 2192.0) < 1e-6, f'镜像应含被删除的 2000MB，得到 {img}'
assert abs(vis - 192.0) < 1e-6, f'可见应为 130+50+12=192，得到 {vis}'
# 同层内装了再删（根本没写进层）
img2, vis2 = image_size_mb([{'/base': 130.0}, {'/lib': 50.0}, {'/app': 12.0}])
assert abs(img2 - vis2) < 1e-6, '没有白出时，镜像体积应等于可见体积'
assert img2 < img
print(f'含白出: 镜像 {img}MB / 可见 {vis}MB   |   同层清理: 镜像 {img2}MB / 可见 {vis2}MB')
print('✅ 练习 1 通过：你复现了「分两条 RUN 删不掉字节」')"""),
    md("""## ✏️ 练习 2：最优指令顺序

实现 `best_order(instrs, probs)`：在**保持依赖可行**的简化假设下（这里假设任意顺序都合法，
只有第 0 条 `FROM` 必须留在最前），返回使期望构建成本 `E = Σ p_i · Σ_{j≥i} c_j` 最小的顺序（下标列表）。

提示：这是一个经典的**调度排序**问题。对相邻两项交换做比较，可推出排序准则 ——
把 `p/c` 大的排在后面（即按 `p_i / c_i` **升序**排列，`FROM` 固定第一）。"""),
    code("""def best_order(instrs, probs):
    # TODO: 固定下标 0 在最前；其余按 probs[i]/instrs[i].cost_s 升序排列
    #       返回下标列表，例如 [0, 2, 1, 3]
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
ins = [Instr('FROM','base',cost_s=5), Instr('COPY','. /app',cost_s=1),
       Instr('RUN','pip',cost_s=300), Instr('RUN','apt',cost_s=30)]
pr  = [0.01, 0.90, 0.05, 0.02]
order = best_order(ins, pr)
assert order[0] == 0, 'FROM 必须在最前'
assert sorted(order) == list(range(4)), '必须是一个排列'
assert order[-1] == 1, '天天改、又极便宜的 COPY . 应排在最后'

def E_of(order):
    return expected_build_cost([ins[i] for i in order], [pr[i] for i in order])
import itertools
brute = min(itertools.permutations(range(1,4)), key=lambda t: E_of((0,)+t))
assert abs(E_of(order) - E_of((0,)+brute)) < 1e-9, '应与暴力枚举的最优解一致'
print(f'最优顺序 {order}，期望成本 {E_of(order):.2f}s（暴力枚举同值 ✅）')
print('✅ 练习 2 通过：对拍暴力枚举，排序准则正确')"""),
    md("""## ✏️ 练习 3：优雅停机的正确顺序

实现 `shutdown_sequence()`：返回优雅停机的**四个步骤的正确顺序**（字符串列表）。
可选步骤：`'mark_not_ready'`（就绪探针返回 503）、`'wait_endpoint_propagation'`（睡几秒等端点摘除生效）、
`'drain_inflight'`（等在途请求放完）、`'exit'`（退出进程）。"""),
    code("""def shutdown_sequence():
    # TODO: 返回 4 个步骤的正确顺序
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
seq = shutdown_sequence()
assert seq == ['mark_not_ready', 'wait_endpoint_propagation', 'drain_inflight', 'exit'], seq
assert seq.index('mark_not_ready') < seq.index('drain_inflight'), \\
    '必须先摘流量再排空，否则排空期间还在进新请求'
assert seq.index('wait_endpoint_propagation') < seq.index('drain_inflight'), \\
    '端点传播是最终一致的，必须等它生效（preStop: sleep 5）'
print('优雅停机顺序:', ' -> '.join(seq))
print('✅ 练习 3 通过：先摘流量、等传播、再排空、最后退出')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def image_size_mb(layers):
    image_mb = sum(v for lyr in layers for v in lyr.values() if v != -1)
    fs = {}
    for lyr in layers:
        for path, size in lyr.items():
            if size == -1: fs.pop(path, None)
            else:          fs[path] = size
    return image_mb, sum(fs.values())"""),
    code("""# 练习 2 参考答案
def best_order(instrs, probs):
    rest = sorted(range(1, len(instrs)), key=lambda i: probs[i] / instrs[i].cost_s)
    return [0] + rest"""),
    code("""# 练习 3 参考答案
def shutdown_sequence():
    return ['mark_not_ready', 'wait_endpoint_propagation', 'drain_inflight', 'exit']"""),
    md("""---
## 🧪 真实数据胶囊：权重分发的隐形账单

扩容 20 个副本、每个从对象存储拉 140 GB 权重会发生什么？用公开的云计价量级算这笔账。
（带 try/except：本环境不联网，直接用内置的真实量级数字。）"""),
    code("""# 公开量级（约数，可改成你自己的报价）
WEIGHTS_GB      = 140.0     # Llama-70B fp16
EGRESS_USD_PER_GB = 0.09    # 跨区/出网数据传输典型价
SAME_REGION_USD_PER_GB = 0.01
OBJ_STORE_MBPS  = 800.0     # 单 Pod 从对象存储的有效拉取带宽

def scale_out_cost(n_replicas, gb, usd_per_gb, bw_mbps=OBJ_STORE_MBPS):
    total_gb = n_replicas * gb
    return {'总流量GB': total_gb,
            '流量费USD': total_gb * usd_per_gb,
            '每副本拉取秒': gb * 1024 / bw_mbps}

for n in [1, 5, 20]:
    a = scale_out_cost(n, WEIGHTS_GB, EGRESS_USD_PER_GB)
    print(f'{n:>3d} 副本跨区拉取: {a["总流量GB"]:>7.0f} GB, ${a["流量费USD"]:>7.2f}, '
          f'每副本等 {a["每副本拉取秒"]/60:.1f} 分钟')

cross = scale_out_cost(20, WEIGHTS_GB, EGRESS_USD_PER_GB)['流量费USD']
same  = scale_out_cost(20, WEIGHTS_GB, SAME_REGION_USD_PER_GB)['流量费USD']
print(f'\\n跨区 ${cross:.0f}  vs  同区 ${same:.0f}  —— 每次扩容差 {cross/same:.0f} 倍')
assert cross > 200, '20 副本跨区拉 140GB 权重，单次扩容流量费超 $200'
print('✅ 这就是节点本地缓存 / 共享只读卷 / P2P 分发存在的根本原因')"""),
    md("""**🧪 胶囊练习**：实现 `cache_savings(n_replicas, gb, usd_per_gb, replicas_per_node)`：
若采用**节点本地缓存**（同一节点上的多个副本共享一份已下载权重），只有**每个节点的第一个副本**产生下载。
返回 `(下载次数, 流量费USD)`。"""),
    code("""def cache_savings(n_replicas, gb, usd_per_gb, replicas_per_node):
    # TODO: 下载次数 = ceil(n_replicas / replicas_per_node)；流量费 = 下载次数 * gb * usd_per_gb
    raise NotImplementedError"""),
    code("""# 自测
downloads, cost = cache_savings(20, WEIGHTS_GB, EGRESS_USD_PER_GB, replicas_per_node=4)
assert downloads == 5, f'20 副本 / 每节点 4 个 = 5 次下载，得到 {downloads}'
assert abs(cost - 5 * 140 * 0.09) < 1e-6
naive = scale_out_cost(20, WEIGHTS_GB, EGRESS_USD_PER_GB)['流量费USD']
assert cost < naive / 3, '节点缓存应把流量费降到 1/4'
print(f'无缓存 ${naive:.0f} -> 节点缓存 ${cost:.0f}（下载 {downloads} 次而非 20 次）')
print('✅ 胶囊练习通过：节点本地缓存把扩容流量费降到 1/replicas_per_node')"""),
    code("""# 📖 胶囊参考答案
def cache_savings(n_replicas, gb, usd_per_gb, replicas_per_node):
    downloads = math.ceil(n_replicas / replicas_per_node)
    return downloads, downloads * gb * usd_per_gb"""),
    md("""---
## 🔧 旁注：真实管线里这些对应什么

你在 Python 里验证过的逻辑，在真实系统里一一对应：

- **层与内容寻址** → OCI Image Spec 的 manifest + layer digest；`docker history` 看每层大小，`dive` 工具逐层浏览。
- **链式缓存失效** → BuildKit 的 DAG 求解器（比经典 builder 更聪明：能并行无依赖的阶段）。`docker build --progress=plain` 里的 `CACHED` 就是命中。
- **同层内装了再删** → `RUN pip install ... && rm -rf /root/.cache/pip`；现代做法是 `RUN --mount=type=cache,target=/root/.cache/pip`。
- **多阶段** → `FROM ... AS builder` + `COPY --from=builder`；CUDA 场景是 `devel` → `runtime` 基础镜像对。
- **权重分发** → initContainer + `aws s3 sync` / PVC(ReadOnlyMany) / DaemonSet 预热 hostPath / Dragonfly P2P。
- **优雅停机** → `lifecycle.preStop.exec: ["sleep","5"]` + 应用内 SIGTERM handler + `terminationGracePeriodSeconds: 120`（LLM 长生成必须调大）。

一份可直接用的生产 Dockerfile 骨架已在讲解第 4 节给出，建议在有 Docker 的机器上原样构建一遍，
对照 `docker history` 验证你在这里算出的层大小与顺序。"""),
    md("""### 小结
- 镜像 = **一叠内容寻址的只读层** + config；overlay 合并、白出标记只影响可见性**不减体积**。
- 层缓存是**链式**的：一层失效、其后全废。「越少变的放越前」可由期望成本 `E = Σ p_i Σ_{j≥i} c_j` 证明。
- **多阶段构建**把编译工具链挡在最终镜像外，典型省 50%+；**共享 base** 让 20 个服务的节点存储省近 10 倍。
- **权重通常不进镜像**，但分离后必须把「模型版本」当一等公民管起来；扩容时的权重拉取有真实的、可能超过 GPU 本身的账单。
- **运行时契约六条**里，优雅停机对 LLM 最要命：先摘流量、等端点传播、再排空、最后退出。

下一站：**模块 02 · 推理服务 API** —— 镜像里的进程要对外说话了，契约怎么定、一个副本到底扛多少 QPS？"""),
]
