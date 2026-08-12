# -*- coding: utf-8 -*-
"""C52 模块 04 · 真机 GPU 工作流。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00；C36（GPU 与 kernel）、C39（分布式训练）会让本模块更好懂，但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_gpu_workflow.ipynb（用 numpy 复现显存与时间的账本，不需要 GPU）'),
    ("核心参考", "NVIDIA 的 CUDA Compatibility 文档、nvidia-smi 手册、PyTorch 的 memory management 与 profiler 文档"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    ("why", "为什么要专门讲「真机」", "".join([
        P("前面所有课程讲的是<em>算法与实现</em>。这一模块讲的是另一类知识：<strong>当你真的坐在一台带 8 张 GPU 的机器前，怎么让它按你的预期工作</strong>。这类知识有三个特点，使得它必须被单独教："),
        UL([
            "<strong>它不在论文里</strong>。没有一篇论文会告诉你「驱动 525 配 CUDA 12.4 会怎样」。",
            "<strong>它的失败模式是「环境」而不是「代码」</strong>。同一份代码在你的机器上跑得好好的，在集群上 OOM——问题不在代码里，所以读代码找不到。",
            "<strong>它有明确的正确答案，且可以提前算出来</strong>。显存够不够、要不要梯度检查点、batch 能开多大——<em>这些都是算术题，不需要试</em>。而绝大多数人是靠试的。",
        ]),
        DUAL(
            "第三点是本模块的核心主张：<strong>「跑一下看看会不会 OOM」是一种昂贵且低信息量的做法</strong>。它占用一次排队、可能等几十分钟、失败后你只知道「不行」而不知道「差多少」。<em>而显存占用是可以在纸上算准到 ±10% 的</em>——算一遍需要两分钟，能直接告诉你「差 12GB，开梯度检查点就够了」。",
            "同样的道理适用于时间估算、通信开销、以及版本兼容。<strong>本模块的做法是把这些「靠试」的问题全部变成「可计算」的问题</strong>，并把计算过程写成可运行的函数。<em>这些函数在没有 GPU 的机器上也能跑</em>——这正是它们的价值：<strong>在申请算力之前就知道答案</strong>。",
        ),
        CALLOUT("intuition", "一个能立刻改变工作方式的习惯：<strong>在提交任何训练任务之前，先写下三个数字——预计显存、预计单步时间、预计总时长</strong>。任务跑起来后对照实际值。<em>前几次会差很多，但很快你的估算会准到 ±20%</em>。到那时，你就能在会议上直接回答「这个实验要多久、要几张卡」，而不是「我跑跑看」。这个能力在工业界的价值被严重低估。"),
    ])),
    ("memory", "显存分解：把 OOM 变成一道算术题", "".join([
        P("训练时的显存占用可以分解成<strong>五项</strong>，每一项都能单独算出来："),
        MATH("M_{total} = \\underbrace{M_{param}}_{\\text{参数}} + \\underbrace{M_{grad}}_{\\text{梯度}} + \\underbrace{M_{opt}}_{\\text{优化器状态}} + \\underbrace{M_{act}}_{\\text{激活}} + \\underbrace{M_{misc}}_{\\text{碎片/缓冲/CUDA上下文}}"),
        TABLE(["项", "公式", "AdamW + bf16 混合精度下（N=参数量）", "受什么影响"], [
            ["<strong>参数</strong>", "<code>N × bytes</code>", "<code>2N</code>（bf16）<em>或</em> <code>4N</code>（fp32 主权重）", "精度策略"],
            ["<strong>梯度</strong>", "<code>N × bytes</code>", "<code>2N</code>（bf16）", "精度；是否累积"],
            ["<strong>优化器状态</strong>", "<code>N × k</code>", "<strong><code>12N</code></strong>（fp32 主权重 4N + m 4N + v 4N）", "<strong>优化器选择（最大的一项）</strong>"],
            ["<strong>激活</strong>", "<code>∝ B × L × H × layers</code>", "<strong>可变，常常是主导项</strong>", "batch、序列长、是否梯度检查点"],
            ["<strong>杂项</strong>", "≈ 1–2 GB", "CUDA 上下文、cuBLAS 工作区、分配器碎片", "几乎固定"],
        ]),
        DUAL(
            "<strong>第一个反直觉的事实：优化器状态通常比参数本身大得多</strong>。AdamW 混合精度下，每个参数要存 fp32 主权重(4B) + 一阶动量(4B) + 二阶动量(4B) = 12 字节，加上 bf16 参数(2B)与梯度(2B)，<em>总共 16 字节/参数</em>。<strong>一个 7B 模型光是「模型相关」的显存就要 112 GB</strong>——远超单张 80GB 卡。这解释了为什么全参数微调 7B 需要多卡或 ZeRO 分片，而 LoRA（只训 0.1% 参数）能在单卡跑。",
            "<strong>第二个反直觉的事实：激活显存常常是主导项，而且它随 batch 与序列长线性/平方增长</strong>。Transformer 每层的激活约 <code>B·L·H·(10 + 24/H·L)</code> 量级（后一项是注意力矩阵，<em>随序列长平方增长</em>，除非用 FlashAttention）。<em>所以「减小 batch」几乎总是最有效的 OOM 急救手段，而「序列长砍半」对长序列场景的效果是四倍</em>。",
        ),
        CALLOUT("warn", "算显存时最常被忘掉的是<strong>「杂项」的 1–2 GB</strong>与<strong>分配器碎片</strong>。PyTorch 的缓存分配器会保留已释放的块，<code>nvidia-smi</code> 显示的占用通常<em>高于</em> <code>torch.cuda.memory_allocated()</code>。<em>如果你算出来「刚好够」，实际上大概率会 OOM</em>。<strong>留 10–15% 余量是工程常识，不是保守</strong>。另外注意：OOM 也可能发生在<em>峰值</em>而非稳态——反向传播时梯度与激活同时存在的那一瞬间才是峰值。"),
    ])),
    ("oom", "OOM 诊断树：按顺序排除", "".join([
        ASCII("""OOM 了 —— 按这个顺序排查（从最便宜到最贵）

① 是不是**峰值**而不是稳态？
   症状：跑了几步才 OOM / 只在某个特别长的样本上 OOM
   → 按最长样本算，不是按平均；检查有没有长度排序的 batch sampler

② 是不是**碎片**？
   症状：memory_allocated 远小于 nvidia-smi 显示的占用
   → PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
   → 避免频繁变化的形状（每种形状一批新的分配块）

③ **减小 batch**（最有效，几乎线性）
   → 配合梯度累积保持有效 batch 不变（C50 模块 03）
   ⚠️ 但 BatchNorm 的统计会变；LayerNorm 不受影响

④ **梯度检查点**（激活显存降到 ~√layers，换 ~30% 额外计算）
   → 单卡上性价比最高的一招

⑤ **换优化器**：AdamW(12N) → 8bit Adam(6N) → SGD+momentum(4N)
   → 对大模型效果显著，但可能影响收敛

⑥ **参数高效微调**：LoRA 让优化器状态从 12N 降到 12·(0.001N)
   → 幅度最大的一招（C50 模块 04）

⑦ **分片 / 多卡**：ZeRO-2（梯度+优化器分片）→ ZeRO-3（参数也分片）
   → 引入通信开销，需要真的多卡（C39）

⑧ 换更大的卡 / 用 CPU offload
   → 最后手段：offload 会让速度掉 3–10×""")
        ,
        DUAL(
            "这棵树的顺序不是随便排的，它按<strong>「成本 / 收益」</strong>排序：前两步是免费的（改配置）；③④是几乎免费的（少量计算换大量显存）；⑤⑥会影响训练行为（要验证）；⑦⑧要改架构或花钱。<em>绝大多数 OOM 在 ③④ 就解决了</em>，而很多人直接跳到 ⑦。",
            "第 ① 步值得特别强调，因为它最容易被误诊：<strong>「跑了 500 步才 OOM」几乎一定是遇到了一个特别长的样本</strong>，而不是「显存慢慢泄漏」。<em>解法不是减小平均 batch，而是按<strong>最长样本</strong>规划显存，或者用 token-budget 的动态 batch（把「每批 32 条」改成「每批 8192 token」）</em>。后者是变长序列训练的标准做法，能同时解决 OOM 与 padding 浪费两个问题。",
        ),
        CALLOUT("danger", "<p>一个必须知道的陷阱：<strong><code>nvidia-smi</code> 显示的显存占用不会随 Python 里的 <code>del</code> 立刻下降</strong>，因为 PyTorch 的缓存分配器持有着它。<em>这会让人误以为「内存没释放」并去找不存在的泄漏</em>。<strong>要看真实占用用 <code>torch.cuda.memory_allocated()</code>（当前）与 <code>max_memory_allocated()</code>（峰值）</strong>；<code>torch.cuda.empty_cache()</code> 能把缓存还给驱动但会让后续分配变慢，<em>只在需要给别的进程腾地方时用，不要放在训练循环里</em>。</p>", "nvidia-smi 不是真实占用"),
    ])),
    ("version", "版本矩阵：环境即依赖", "".join([
        P("GPU 栈是一个<strong>四层依赖链</strong>，任何一层不匹配都会失败，而失败信息常常指向错误的方向。"),
        ASCII("""GPU 硬件 (compute capability, 如 A100=8.0, H100=9.0, RTX4090=8.9)
   ↑ 必须被支持
NVIDIA 驱动 (如 550.54)  ←── 这一层通常由集群管理员控制，你改不了
   ↑ 驱动版本 >= CUDA runtime 的最低要求（除非启用 forward compatibility）
CUDA runtime (如 12.1)   ←── 通常随 PyTorch wheel 一起装（cu121）
   ↑
框架 (torch 2.4.1+cu121)
   ↑ 必须与
其它编译扩展 (flash-attn, xformers, apex, bitsandbytes, deepspeed)
   —— **这些是按 (torch 版本 × CUDA 版本 × Python 版本) 编译的，最容易崩**""")
        ,
        TABLE(["症状", "真正的原因", "怎么确认"], [
            ["<code>CUDA driver version is insufficient</code>", "驱动版本 &lt; CUDA runtime 要求", "<code>nvidia-smi</code> 看驱动版本，对照 CUDA 兼容表"],
            ["<code>no kernel image is available</code>", "<strong>编译时没有包含这张卡的 compute capability</strong>", "<code>torch.cuda.get_arch_list()</code> 看编译进了哪些 sm_XX"],
            ["<code>undefined symbol: _ZN3c10...</code>", "<strong>扩展是针对另一个 torch 版本编译的</strong>", "对照扩展的构建矩阵；重装匹配版本"],
            ["<code>libcudart.so.12: cannot open</code>", "CUDA runtime 库找不到", "<code>ldd</code> 查依赖；检查 <code>LD_LIBRARY_PATH</code>"],
            ["能跑但极慢", "<strong>回退到了 CPU 或未优化路径</strong>", "<code>torch.cuda.is_available()</code>；看算子是否真在 GPU 上"],
            ["<code>CUDA error: device-side assert</code>", "索引越界（如 label 超出 vocab、<code>-100</code> 没设对）", "<strong><code>CUDA_LAUNCH_BLOCKING=1</code> 重跑</strong>拿到真实栈"],
        ]),
        DUAL(
            "第二行的 <code>no kernel image is available</code> 值得展开，因为它的错误信息极具误导性。CUDA 二进制包含针对特定 <span class=\"term\">compute capability</span>（sm_80、sm_90 等）编译的代码。<em>如果你的 wheel 只编译了 sm_70–sm_86，而你在 H100（sm_90）上跑，就会得到这个错</em>——它听起来像「找不到文件」，实际是「这个二进制不认识你的卡」。<strong>解法是装匹配的 wheel 或从源码编译并指定 <code>TORCH_CUDA_ARCH_LIST</code>。</strong>",
            "最后一行的 <code>CUDA_LAUNCH_BLOCKING=1</code> 是<strong>GPU 调试的第一招</strong>，必须记住。CUDA kernel 是异步启动的，所以报错时 Python 的栈已经跑到别处去了——<em>你看到的栈几乎总是无关的</em>。设这个环境变量会让每个 kernel 同步执行，<strong>错误就会出现在真正出问题的那一行</strong>。代价是慢很多，所以只在调试时用。<em>这一招能把「完全看不懂的报错」变成「第 47 行索引越界」。</em>",
        ),
        CALLOUT("warn", "关于<strong>编译扩展</strong>（flash-attn、xformers、apex、bitsandbytes、deepspeed）：它们是这条链上最脆弱的一环，因为它们的二进制绑定了 <code>(torch 版本, CUDA 版本, Python 版本, ABI)</code> 四元组。<em>「pip install flash-attn」在一台机器上成功、在另一台上编译两小时后失败，是常态</em>。<strong>工程上的正确做法是把整个栈锁进容器镜像</strong>（C48 模块 01）——不是为了「优雅」，而是因为这条链根本无法靠 <code>requirements.txt</code> 复现。"),
    ])),
    ("profile", "性能诊断：三个层次的问题", "".join([
        P("「训练太慢」不是一个问题，是三类问题。<strong>先定位在哪一层，再优化——否则你会优化错地方</strong>。"),
        TABLE(["层次", "症状", "诊断手段", "典型原因"], [
            ["<strong>① 数据</strong>", "<strong>GPU 利用率低且波动</strong>（0% ↔ 100% 跳动）", "看 <code>nvidia-smi dmon</code> 的 sm 列；给 dataloader 计时", "num_workers 太少、预处理太重、磁盘/网络 IO 慢"],
            ["<strong>② 通信</strong>", "单卡快、多卡不成比例", "NCCL 日志、profiler 的通信条", "梯度同步、跨节点带宽、没用梯度累积"],
            ["<strong>③ 计算</strong>", "GPU 利用率高但仍慢", "profiler 的 kernel 时间分布", "kernel 未融合、精度没用对、注意力实现低效"],
        ]),
        DUAL(
            "<strong>诊断顺序必须是 ①→②→③</strong>，因为数据瓶颈会掩盖一切。<em>如果 GPU 有 40% 时间在等数据，你把 kernel 优化快 2 倍也只提升 30%</em>；而把 dataloader 修好可能直接提升 60%。<strong>而数据瓶颈恰恰是最容易修的</strong>（加 workers、预处理离线化、用更快的格式）——所以它必须最先查。",
            "区分 ① 与 ③ 有一个极简的判据：<strong>看 GPU 利用率的<em>波动模式</em>而不是平均值</strong>。数据瓶颈的特征是<em>周期性地掉到 0</em>（等下一批）；计算瓶颈是<em>稳定在高位</em>。<em>平均利用率 60% 可能是「稳定 60%」（计算问题）也可能是「一半时间 100% 一半时间 0%」（数据问题）——两者的处方完全不同</em>。<strong>所以要看 <code>nvidia-smi dmon -s u</code> 的时间序列，不要只看 <code>nvidia-smi</code> 的瞬时值。</strong>",
        ),
        H3("最小可用的诊断命令集"),
        CODE("""# 硬件与驱动（第一件事）
nvidia-smi                              # 驱动版本、CUDA 版本、每卡显存与利用率
nvidia-smi -L                           # 列出所有卡与 UUID
nvidia-smi topo -m                      # **卡间拓扑**：NVLink 还是 PCIe（决定多卡效率）

# 实时监控（诊断数据瓶颈的关键）
nvidia-smi dmon -s pucm                 # 时间序列：sm 利用率/显存/功耗/时钟
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1

# 框架侧
python -c "import torch; print(torch.__version__, torch.version.cuda,
           torch.cuda.is_available(), torch.cuda.get_arch_list())"
python -c "import torch; print(torch.cuda.get_device_capability())"   # sm_XX

# 调试（记住这一条）
CUDA_LAUNCH_BLOCKING=1 python train.py  # 让报错出现在真正出问题的那一行

# 显存
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python train.py   # 缓解碎片
torch.cuda.memory_summary()             # 分配器的详细账本
torch.cuda.max_memory_allocated()       # **峰值**（不是 nvidia-smi 的数字）"""),
        CALLOUT("intuition", "<code>nvidia-smi topo -m</code> 常被忽略，但它决定了多卡训练的上限：<strong>NVLink 连接的卡间带宽是 PCIe 的 5–10 倍</strong>。<em>同样 8 卡，全 NVLink 的机器与走 PCIe 的机器，数据并行效率可以差一倍</em>。而这个信息在提交任务前一条命令就能拿到。<strong>如果拓扑显示是 PCIe，就要更认真地考虑梯度累积与通信压缩</strong>（C39）——这不是调优，这是架构选择。"),
    ])),
    ("interference", "共享集群：不是你的问题也会变成你的问题", "".join([
        P("上面讲的都是「你独占这台机器」的假设。<strong>而在共享集群上，你的任务变慢可能与你的代码完全无关</strong>——这是最容易浪费时间的一类排查，因为你会一直在自己的代码里找原因。"),
        TABLE(["外部干扰源", "症状", "怎么确认"], [
            ["<strong>邻居抢共享存储</strong>", "数据加载时快时慢，GPU 周期性空闲", "对比本地盘与网络盘的读取速度；看存储的 IOPS 监控"],
            ["<strong>邻居抢 PCIe / NVLink 带宽</strong>", "多卡通信变慢，单卡正常", "<code>nvidia-smi topo -m</code> 看是否与别人共享同一条链路"],
            ["<strong>CPU 被超卖</strong>", "dataloader 的 worker 抢不到 CPU", "<code>nproc</code> vs cgroup 限额；<code>top</code> 看 steal time"],
            ["<strong>GPU 降频</strong>", "同样代码今天比昨天慢 20%", "<code>nvidia-smi -q -d PERFORMANCE</code> 看 throttle reasons（温度/功耗墙）"],
            ["<strong>MIG / 时间片共享</strong>", "「一张 A100」其实只是它的 1/7", "<code>nvidia-smi -L</code> 看是否是 MIG 实例"],
        ]),
        DUAL(
            "<strong>倒数第二行（降频）最容易被误诊为「我改坏了什么」</strong>。GPU 在温度或功耗超限时会自动降低时钟，性能可以掉 10–30%，<em>而这完全不反映在任何代码层面的指标里</em>。<code>nvidia-smi -q -d PERFORMANCE</code> 会明确告诉你 <code>SW Power Cap</code> 或 <code>HW Thermal Slowdown</code> 是否被触发。<strong>在机房散热不好或多卡满载的机器上，这不是罕见情况。</strong>",
            "应对共享环境的通用做法是<strong>「每次跑实验都记录环境指纹 + 一个固定的基准</strong>」：在训练开始前跑一个几秒钟的标准 matmul benchmark，把结果连同环境指纹一起写进日志。<em>这样当某天任务变慢时，你可以立刻区分「机器变慢了」与「我的代码变慢了」</em>——而不用花半天做二分回退。<strong>这个基准的成本是几秒钟，收益是把一整类问题变成一次查表。</strong>",
        ),
        CALLOUT("intuition", "这一节其实是模块 00 那条「版本即环境」纪律的延伸：<strong>你无法控制的东西，至少要能观测</strong>。环境指纹记录「跑在什么上」，基准测试记录「那个东西当时有多快」。<em>两者加起来，「在我这好使」这个句式就变成了可验证的陈述</em>——你能拿出两份指纹与两个基准值，直接指出差在哪。这比任何猜测都快。"),
    ])),
    ("plan", "算力规划：在申请之前算清楚", "".join([
        P("面对「这个实验要几张卡、跑多久」这个问题，有一套可以在两分钟内完成的估算。"),
        MATH("t_{step} \\approx \\frac{6 \\cdot N \\cdot B \\cdot L}{\\text{FLOPS}_{eff}}, \\qquad \\text{FLOPS}_{eff} = \\text{FLOPS}_{peak} \\times \\text{MFU}"),
        P("其中 <code>6N</code> 是每个 token 的训练 FLOPs（前向 2N + 反向 4N），<span class=\"term\">MFU</span>（Model FLOPs Utilization）是实际达到的峰值算力比例。"),
        TABLE(["场景", "典型 MFU", "说明"], [
            ["单卡、大 batch、fp16/bf16", "40–55%", "调得好的上限"],
            ["单卡、小模型或小 batch", "15–30%", "kernel 启动与内存带宽成为瓶颈"],
            ["多卡数据并行（NVLink）", "35–50%", "通信可与计算重叠"],
            ["多卡数据并行（PCIe）", "20–35%", "<strong>通信成为瓶颈</strong>"],
            ["ZeRO-3 / 跨节点", "15–35%", "参数也要通信，重叠更难"],
            ["<strong>有数据瓶颈时</strong>", "<strong>可低至 5%</strong>", "<em>先修数据管线，别优化 kernel</em>"],
        ]),
        DUAL(
            "这个估算的价值不在精确（它通常有 ±30% 误差），而在<strong>量级正确</strong>。<em>它能立刻区分「这要跑 6 小时」与「这要跑 3 周」</em>，而后者意味着实验设计本身需要改（缩小模型、减少数据、换方法）。<strong>在提交之前发现「这要 3 周」，比跑了 3 天后发现好得多。</strong>",
            "反过来用也很有价值：<strong>用实测的单步时间反推 MFU，可以判断「还有多少优化空间」</strong>。如果你算出 MFU 只有 8%，说明有严重瓶颈（大概率是数据）；如果已经 45%，那么再花一周调优可能只能榨出 10%——<em>此时更该考虑的是「换更多卡」或「改小实验」，而不是继续优化</em>。<strong>知道天花板在哪，才知道该不该继续。</strong>",
        ),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>「真机问题」看起来玄学，实际上大部分是算术</strong>——显存能算、时间能算、MFU 能算、版本兼容能查表。<em>把它们从「试出来的」变成「算出来的」，你的迭代速度会有数量级的提升</em>，因为你不再需要用一次昂贵的排队去获取一个「行/不行」的比特。<strong>而剩下那部分真正玄学的（驱动、编译扩展、集群配置），解法是把环境锁进容器</strong>（C48），而不是每次重新斗争。"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>显存估算的自动化</strong>：PyTorch 的 <code>FlopCounterMode</code> 与 <code>torch.cuda.memory._record_memory_history</code> 让事后分析变容易，但<em>「训练前预测峰值显存」仍需人工建模</em>——因为它依赖具体的算子实现、是否重计算、分配器行为。这是一个明显有价值但未标准化的工具位。",
            "<strong>MFU 的可比性</strong>：不同论文对 MFU 的定义不完全一致（是否算 attention 的平方项、是否算重计算的额外 FLOPs）。<em>跨论文比较 MFU 时要先确认口径</em>，否则会得出错误结论。",
            "<strong>异构与新硬件</strong>：AMD ROCm、Intel Gaudi、Google TPU、Apple MPS 的生态成熟度差异巨大。<em>「代码在 CUDA 上跑得好」不代表能迁移</em>——算子覆盖、性能特征、调试工具都不同。跨厂商的可移植性仍是开放问题（也是 ONNX/MLIR 想解决的）。",
            "<strong>编译扩展的分发</strong>：flash-attn 这类扩展的 <code>(torch × CUDA × Python × ABI)</code> 组合爆炸，导致预编译 wheel 覆盖不全、源码编译又极慢。<em>更好的分发机制（如 ABI 稳定的插件接口）是社区长期诉求</em>。",
            "<strong>集群层的可观测性</strong>：单机的 profiler 已经很好，但「几十个任务共享几百张卡时，我的任务为什么慢」缺乏好工具——可能是邻居抢了带宽、可能是存储拥塞、可能是拓扑不好。<em>这类跨任务的干扰诊断仍主要靠经验</em>。",
        ]),
        CALLOUT("paper", "必读（都是文档）：NVIDIA 的 <em>CUDA Compatibility</em> 指南（驱动与 runtime 的版本规则，兼容性问题的权威来源）与 <em>nvidia-smi</em> 手册（<code>dmon</code>/<code>topo</code> 两个子命令值得精读）；PyTorch 的 <em>CUDA semantics</em>（异步执行与 <code>CUDA_LAUNCH_BLOCKING</code>）、<em>Memory management</em>（缓存分配器与 <code>expandable_segments</code>）、<em>PyTorch Profiler</em>。方法论：Chowdhery 等 <em>PaLM</em> 论文里的 MFU 定义（这是 MFU 这个指标的常用出处）；Korthikanti 等 <em>Reducing Activation Recomputation in Large Transformer Models</em>（激活显存的精确建模，本模块公式的来源）。相邻课程：C36（GPU 与 kernel）、C39（分布式）、C48（容器化环境）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 04 · 真机 GPU 工作流（显存账本 / OOM 诊断树 / 版本矩阵 / MFU 估算）

目标：把「靠试」的 GPU 问题全部变成**可计算**的问题——
显存能算、时间能算、MFU 能算、版本兼容能查表。

**本 notebook 不需要 GPU**：它算的是账本，而账本的价值恰恰在于「申请算力之前就知道答案」。

路线：五项显存分解 → **优化器状态比参数还大** → 激活显存与序列长的平方项 →
OOM 诊断树的可执行版本 → 版本矩阵与错误信息查表 →
MFU 估算与反推 → GPU 利用率的**波动模式**判据 → ✏️ 练习 → 📖 答案 → 🧪 规划器。

> 心智模型：**「真机问题」看起来玄学，实际上大部分是算术。**"""),
    md("""## 1 · 显存分解：五项，每项都能算

$$M_{total} = M_{param} + M_{grad} + M_{opt} + M_{act} + M_{misc}$$"""),
    code("""import numpy as np, math, collections
GB = 1024 ** 3

OPT_BYTES = {          # 每参数的优化器状态字节数（混合精度下含 fp32 主权重）
    'adamw':        12,    # fp32 主权重 4 + m 4 + v 4
    'adamw_8bit':    6,    # fp32 主权重 4 + m 1 + v 1
    'sgd_momentum':  8,    # fp32 主权重 4 + momentum 4
    'sgd':           4,    # 仅 fp32 主权重
    'adafactor':     5,    # 主权重 4 + 分解的二阶矩 ~1
}

def model_memory(n_params, optimizer='adamw', param_bytes=2, grad_bytes=2,
                 trainable_frac=1.0):
    '''模型相关显存（不含激活）。trainable_frac: LoRA 等只训一小部分时 <1。'''
    n_train = n_params * trainable_frac
    return {
        'param': n_params * param_bytes,
        'grad':  n_train * grad_bytes,
        'opt':   n_train * OPT_BYTES[optimizer],
    }

def activation_memory(batch, seq, hidden, layers, bytes_per=2,
                      checkpointing=False, flash_attention=True):
    '''Transformer 激活显存的粗估。
       每层 ~ B*L*H*C 的线性项；注意力矩阵 ~ B*heads*L^2（**随序列长平方**）。'''
    linear = batch * seq * hidden * 10 * bytes_per          # 线性项（各种中间张量）
    heads = max(1, hidden // 64)
    attn = 0 if flash_attention else batch * heads * seq * seq * bytes_per
    per_layer = linear + attn
    total = per_layer * layers
    if checkpointing:
        # 只存每层边界 + 重算一层的峰值 -> 约 sqrt(layers) 量级（这里用常见的分段近似）
        total = per_layer * math.sqrt(layers) + batch * seq * hidden * bytes_per * layers
    return total

MISC = 1.5 * GB        # CUDA 上下文 + cuBLAS 工作区 + 分配器碎片

def total_memory(n_params, batch, seq, hidden, layers, **kw):
    mm = model_memory(n_params, kw.get('optimizer', 'adamw'),
                      trainable_frac=kw.get('trainable_frac', 1.0))
    act = activation_memory(batch, seq, hidden, layers,
                            checkpointing=kw.get('checkpointing', False),
                            flash_attention=kw.get('flash_attention', True))
    parts = dict(mm); parts['act'] = act; parts['misc'] = MISC
    parts['total'] = sum(parts.values())
    return parts

p = total_memory(7e9, batch=1, seq=2048, hidden=4096, layers=32)
print('7B 全参数微调, batch=1, seq=2048, AdamW bf16:')
for k in ['param', 'grad', 'opt', 'act', 'misc', 'total']:
    print(f'  {k:<8s} {p[k]/GB:>8.1f} GB')
assert p['opt'] > p['param'], '⚠️ 优化器状态比参数本身还大'
print(f'\\n⚠️  优化器状态 {p["opt"]/GB:.0f} GB > 参数 {p["param"]/GB:.0f} GB')
print(f'    总计 {p["total"]/GB:.0f} GB —— **远超单张 80GB 卡**。')
print('✅ 这就是为什么全参数微调 7B 需要多卡或 ZeRO，而 LoRA 能在单卡跑。')"""),
    code("""# 优化器选择的影响（这是最大的一项）
print(f"{'优化器':<16s} {'每参数字节':>10s} {'7B 的优化器状态':>16s} {'总计':>10s}")
for opt in ['adamw', 'adamw_8bit', 'adafactor', 'sgd_momentum', 'sgd']:
    t = total_memory(7e9, 1, 2048, 4096, 32, optimizer=opt)
    print(f'{opt:<16s} {OPT_BYTES[opt]:>10d} {t["opt"]/GB:>15.1f}G {t["total"]/GB:>9.1f}G')
t_adamw = total_memory(7e9, 1, 2048, 4096, 32, optimizer='adamw')
t_sgd = total_memory(7e9, 1, 2048, 4096, 32, optimizer='sgd')
assert t_adamw['total'] - t_sgd['total'] > 50 * GB
print(f'\\n✅ AdamW -> SGD 省下 {(t_adamw["total"]-t_sgd["total"])/GB:.0f} GB，')
print('   但可能影响收敛 —— 所以它在诊断树里排第 ⑤ 位而不是第 ①。')

# LoRA：只训 0.1% 的参数
t_lora = total_memory(7e9, 1, 2048, 4096, 32, trainable_frac=0.001)
print(f'\\nLoRA (trainable=0.1%): 梯度 {t_lora["grad"]/GB:.2f}G, '
      f'优化器 {t_lora["opt"]/GB:.2f}G, 总计 {t_lora["total"]/GB:.1f}G')
assert t_lora['total'] < 40 * GB, 'LoRA 应能塞进单卡'
print(f'✅ 从 {t_adamw["total"]/GB:.0f}G 降到 {t_lora["total"]/GB:.0f}G —— **幅度最大的一招**。')"""),
    md("""### 激活显存：序列长的平方项"""),
    code("""print(f"{'seq':>7s} {'FlashAttn 激活':>16s} {'朴素注意力激活':>16s} {'倍数':>7s}")
for seq in [512, 1024, 2048, 4096, 8192]:
    a_flash = activation_memory(4, seq, 4096, 32, flash_attention=True)
    a_naive = activation_memory(4, seq, 4096, 32, flash_attention=False)
    print(f'{seq:>7d} {a_flash/GB:>15.1f}G {a_naive/GB:>15.1f}G {a_naive/a_flash:>6.1f}×')

a1 = activation_memory(4, 2048, 4096, 32, flash_attention=False)
a2 = activation_memory(4, 4096, 4096, 32, flash_attention=False)
ratio = a2 / a1
assert ratio > 2.5, f'朴素注意力下序列长翻倍，激活增长应超过 2 倍（实测 {ratio:.1f}×）'
lin1 = activation_memory(4, 2048, 4096, 32, flash_attention=True)
lin2 = activation_memory(4, 4096, 4096, 32, flash_attention=True)
assert abs(lin2 / lin1 - 2.0) < 0.01, 'FlashAttention 下应线性增长'
print(f'\\n✅ FlashAttention 下序列长翻倍 = 激活 ×{lin2/lin1:.1f}（线性）')
print(f'   朴素注意力下序列长翻倍 = 激活 ×{ratio:.1f}（**含平方项**）')
print('   -> 长序列场景「序列长砍半」的效果可达四倍。')

# 梯度检查点
for ckpt in [False, True]:
    a = activation_memory(8, 4096, 4096, 32, checkpointing=ckpt)
    print(f'{"梯度检查点开" if ckpt else "梯度检查点关"}: 激活 {a/GB:.1f} GB')
a_off = activation_memory(8, 4096, 4096, 32, checkpointing=False)
a_on = activation_memory(8, 4096, 4096, 32, checkpointing=True)
assert a_on < a_off * 0.5
print(f'✅ 梯度检查点把激活降到 {a_on/a_off:.0%}，代价约 +30% 计算 ——')
print('   **单卡上性价比最高的一招**。')"""),
    md("""## 2 · OOM 诊断树的可执行版本

按「成本 / 收益」排序：前两步免费 → ③④几乎免费 → ⑤⑥影响训练行为 → ⑦⑧要改架构或花钱。"""),
    code("""def diagnose_oom(cfg, capacity_gb, headroom=0.12):
    '''按诊断树顺序给出建议，返回 (可行配置, 建议列表)。'''
    budget = capacity_gb * GB * (1 - headroom)
    steps, cur = [], dict(cfg)

    def mem(c):
        return total_memory(c['n_params'], c['batch'], c['seq'], c['hidden'], c['layers'],
                            optimizer=c.get('optimizer', 'adamw'),
                            checkpointing=c.get('checkpointing', False),
                            trainable_frac=c.get('trainable_frac', 1.0),
                            flash_attention=c.get('flash_attention', True))['total']

    if mem(cur) <= budget:
        return cur, ['配置已可行（含 %d%% 余量）' % (headroom * 100)]

    # ③ 减小 batch（配合梯度累积保持有效 batch）
    while cur['batch'] > 1 and mem(cur) > budget:
        cur['batch'] //= 2
        steps.append(f'③ batch -> {cur["batch"]}（用梯度累积保持有效 batch）')
    if mem(cur) <= budget: return cur, steps
    # ④ 梯度检查点
    if not cur.get('checkpointing'):
        cur['checkpointing'] = True
        steps.append('④ 开梯度检查点（激活大降，约 +30% 计算）')
    if mem(cur) <= budget: return cur, steps
    # ⑤ 换优化器
    for opt in ['adamw_8bit', 'adafactor', 'sgd_momentum']:
        cur['optimizer'] = opt
        steps.append(f'⑤ 优化器 -> {opt}（{OPT_BYTES[opt]}B/参数，需验证收敛）')
        if mem(cur) <= budget: return cur, steps
    # ⑥ LoRA
    cur['trainable_frac'] = 0.001
    steps.append('⑥ 改用 LoRA（优化器状态降到 0.1%）')
    if mem(cur) <= budget: return cur, steps
    # ⑦ 分片/多卡
    steps.append(f'⑦ 单卡不够（还需 {(mem(cur)-budget)/GB:.0f} GB）-> ZeRO / 多卡 / 更大的卡')
    return cur, steps

BASE = dict(n_params=7e9, batch=8, seq=2048, hidden=4096, layers=32)
for cap in [80, 40, 24]:
    cfg, steps = diagnose_oom(BASE, cap)
    m = total_memory(cfg['n_params'], cfg['batch'], cfg['seq'], cfg['hidden'], cfg['layers'],
                     optimizer=cfg.get('optimizer','adamw'),
                     checkpointing=cfg.get('checkpointing', False),
                     trainable_frac=cfg.get('trainable_frac',1.0))['total']
    print(f'=== {cap} GB 卡 ===  最终 {m/GB:.1f} GB')
    for s in steps: print('   ' + s)
    print()

cfg80, st80 = diagnose_oom(BASE, 80)
cfg24, st24 = diagnose_oom(BASE, 24)
assert len(st24) > len(st80), '卡越小需要的手段越多'
assert any('LoRA' in s for s in st24), '24GB 卡上 7B 训练必然要用 LoRA'
print('✅ 绝大多数 OOM 在 ③④ 就解决了 —— 而很多人直接跳到 ⑦（多卡）。')"""),
    code("""# ① 峰值 vs 稳态：「跑了 500 步才 OOM」几乎一定是遇到了长样本
rng = np.random.default_rng(0)
lengths = np.clip(rng.lognormal(6.0, 0.7, size=2000).astype(int), 16, 8192)
print(f'样本长度: 中位数 {np.median(lengths):.0f}, 均值 {lengths.mean():.0f}, '
      f'p99 {np.percentile(lengths,99):.0f}, 最大 {lengths.max()}')

def peak_step(lengths, batch, capacity_gb, **kw):
    '''按批扫描，返回第一个 OOM 的步数（None 表示不会 OOM）。'''
    budget = capacity_gb * GB * 0.88
    for step in range(len(lengths) // batch):
        chunk = lengths[step*batch:(step+1)*batch]
        m = total_memory(7e9, batch, int(chunk.max()), 4096, 32,
                         trainable_frac=0.001, checkpointing=True, **kw)['total']
        if m > budget:
            return step, int(chunk.max())
    return None, None

step, L = peak_step(lengths, batch=4, capacity_gb=24)
mean_mem = total_memory(7e9, 4, int(lengths.mean()), 4096, 32,
                        trainable_frac=0.001, checkpointing=True)['total']
print(f'\\n按**平均长度** {lengths.mean():.0f} 估算: {mean_mem/GB:.1f} GB -> 看起来没问题')
if step is not None:
    print(f'实际在第 {step} 步 OOM（该批最长样本 {L} tokens）')
    assert step > 0, '不是第 0 步就炸 —— 这正是「跑了一会儿才 OOM」的现象'
    print('\\n⚠️  误诊：以为是「显存泄漏」。真相是**遇到了一个特别长的样本**。')
print('\\n✅ 两个解法：')
print('   ① 按**最长样本**规划显存（而不是平均）')
print('   ② 用 **token-budget 动态 batch**（「每批 8192 token」而不是「每批 32 条」）')

def token_budget_batches(lengths, budget_tokens):
    '''同时解决 OOM 与 padding 浪费。'''
    batches, cur, cur_max = [], [], 0
    for L_ in lengths:
        m = max(cur_max, L_)
        if cur and m * (len(cur) + 1) > budget_tokens:
            batches.append(cur); cur, cur_max = [L_], L_
        else:
            cur.append(L_); cur_max = m
    if cur: batches.append(cur)
    return batches

bts = token_budget_batches(lengths, 8192)
padded = sum(max(b) * len(b) for b in bts)
real = int(lengths.sum())
fixed_padded = sum(int(lengths[i:i+4].max()) * len(lengths[i:i+4])
                   for i in range(0, len(lengths), 4))
print(f'\\ntoken-budget 分批: {len(bts)} 批, padding 浪费 {1-real/padded:.1%}')
print(f'固定 batch=4     : {len(lengths)//4} 批, padding 浪费 {1-real/fixed_padded:.1%}')
assert max(max(b) * len(b) for b in bts) <= 8192 * 1.001, '每批的 token 数有上界 -> 显存有上界'
print('✅ token-budget 让**每批的 token 数有硬上界** -> 显存有硬上界 -> 不会突然 OOM。')"""),
    md("""## 3 · 版本矩阵与错误信息查表"""),
    code("""# 驱动 -> CUDA runtime 的最低要求（Linux, x86_64）
MIN_DRIVER = {'11.8': 520.61, '12.1': 530.30, '12.4': 550.54, '12.6': 560.28}
# GPU -> compute capability
GPU_ARCH = {'V100': 70, 'T4': 75, 'A100': 80, 'A10': 86, 'RTX4090': 89, 'H100': 90,
            'L40S': 89, 'H200': 90}

def cuda_compatible(driver_version, cuda_runtime):
    need = MIN_DRIVER.get(cuda_runtime)
    if need is None:
        return False, f'未知的 CUDA runtime {cuda_runtime}'
    if driver_version >= need:
        return True, f'驱动 {driver_version} >= {need} ✅'
    return False, (f'驱动 {driver_version} < {need} ❌ '
                   f'-> "CUDA driver version is insufficient"')

def arch_supported(gpu, arch_list):
    '''arch_list 形如 ["sm_70","sm_80","sm_86"]（torch.cuda.get_arch_list()）。'''
    cc = GPU_ARCH[gpu]
    compiled = sorted(int(a.split('_')[1]) for a in arch_list)
    if f'sm_{cc}' in arch_list:
        return True, f'{gpu}(sm_{cc}) 有原生 kernel ✅'
    # 同主版本内可向前兼容（PTX JIT），跨主版本不行
    same_major = [c for c in compiled if c // 10 == cc // 10 and c <= cc]
    if same_major:
        return True, f'{gpu}(sm_{cc}) 无原生 kernel，靠 sm_{same_major[-1]} 的 PTX JIT ⚠️ 首次启动慢'
    return False, f'{gpu}(sm_{cc}) 不在 {arch_list} 中 ❌ -> "no kernel image is available"'

print('=== 驱动 × CUDA runtime ===')
for drv in [525.85, 535.104, 550.54]:
    for rt in ['11.8', '12.1', '12.4']:
        ok, msg = cuda_compatible(drv, rt)
        print(f'  驱动 {drv:<8} + CUDA {rt:<5} {msg}')
assert cuda_compatible(525.85, '12.4')[0] is False
assert cuda_compatible(550.54, '12.4')[0] is True

print('\\n=== GPU × 编译进的 arch ===')
ARCH_LIST = ['sm_70', 'sm_75', 'sm_80', 'sm_86']
for gpu in ['A100', 'RTX4090', 'H100', 'V100']:
    ok, msg = arch_supported(gpu, ARCH_LIST)
    print(f'  {msg}')
assert not arch_supported('H100', ARCH_LIST)[0], 'sm_90 不在列表里 -> no kernel image'
assert arch_supported('RTX4090', ARCH_LIST)[0], 'sm_89 可由 sm_86 的 PTX JIT 覆盖'
print('\\n⚠️  "no kernel image is available" 听起来像「找不到文件」，')
print('    实际是「这个二进制不认识你的卡」。解法：装匹配 wheel 或设 TORCH_CUDA_ARCH_LIST。')"""),
    code("""# 错误信息 -> 真正原因 的查表
ERROR_TABLE = [
    ('CUDA driver version is insufficient', '驱动版本 < CUDA runtime 要求',
     'nvidia-smi 看驱动版本，对照 MIN_DRIVER'),
    ('no kernel image is available', '二进制没编译你这张卡的 compute capability',
     'torch.cuda.get_arch_list() 与 get_device_capability() 对照'),
    ('undefined symbol: _ZN3c10', '扩展是针对另一个 torch 版本编译的',
     '对照扩展的构建矩阵；重装匹配版本（flash-attn/xformers/apex 最常见）'),
    ('libcudart.so', 'CUDA runtime 库找不到', 'ldd 查依赖；检查 LD_LIBRARY_PATH'),
    ('device-side assert triggered', '索引越界（label 超 vocab / -100 没设对）',
     '**CUDA_LAUNCH_BLOCKING=1 重跑**拿到真实栈'),
    ('out of memory', '显存不足', '走 OOM 诊断树；注意峰值 != 稳态'),
]

def lookup_error(msg):
    for pat, cause, action in ERROR_TABLE:
        if pat.lower() in msg.lower():
            return {'cause': cause, 'action': action}
    return {'cause': '未知', 'action': '先跑环境指纹（模块 00）确认版本链'}

for msg in ['RuntimeError: CUDA error: no kernel image is available for execution',
            'ImportError: undefined symbol: _ZN3c104cuda9SetDeviceEi',
            'CUDA error: device-side assert triggered',
            'torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB']:
    r = lookup_error(msg)
    print(f'{msg[:52]:<54s}\\n   原因: {r["cause"]}\\n   动作: {r["action"]}\\n')
assert 'LAUNCH_BLOCKING' in lookup_error('device-side assert triggered')['action']
print('✅ **CUDA_LAUNCH_BLOCKING=1 是 GPU 调试的第一招** ——')
print('   CUDA kernel 异步启动，报错时 Python 栈已经跑到别处；')
print('   设了它错误就出现在真正出问题的那一行。')"""),
    md("""## 4 · MFU 估算：在申请算力之前算清楚

$$t_{step} \\approx \\frac{6 N B L}{\\text{FLOPS}_{peak} \\times \\text{MFU}}$$"""),
    code("""GPU_TFLOPS = {'A100': 312, 'H100': 989, 'V100': 125, 'L40S': 362, 'RTX4090': 165}  # bf16 稠密

def step_time(n_params, batch, seq, gpu='A100', mfu=0.45, n_gpus=1):
    flops = 6 * n_params * batch * seq * n_gpus     # 每步的总 FLOPs（全局 batch）
    eff = GPU_TFLOPS[gpu] * 1e12 * mfu * n_gpus
    return flops / eff

def training_plan(n_params, n_tokens, gpu='A100', mfu=0.45, n_gpus=8,
                  batch=8, seq=2048, usd_per_gpu_hour=2.0):
    tok_per_step = batch * seq * n_gpus
    steps = n_tokens / tok_per_step
    t = step_time(n_params, batch, seq, gpu, mfu, n_gpus)
    hours = steps * t / 3600
    return {'steps': steps, 'step_s': t, 'hours': hours,
            'days': hours / 24, 'usd': hours * n_gpus * usd_per_gpu_hour}

print(f"{'实验':<30s} {'单步 s':>8s} {'总步数':>10s} {'总时长':>12s} {'成本 $':>10s}")
EXPS = [
    ('7B 微调 10B tokens (8×A100)',  7e9,  10e9,  'A100', 8, 0.45),
    ('7B 微调 10B tokens (8×H100)',  7e9,  10e9,  'H100', 8, 0.45),
    ('70B 预训 300B tokens (64×H100)', 70e9, 300e9, 'H100', 64, 0.40),
    ('1B 微调 5B tokens (1×A100)',   1e9,  5e9,   'A100', 1, 0.35),
]
for name, N, T, gpu, ng, mfu in EXPS:
    p_ = training_plan(N, T, gpu, mfu, ng)
    dur = f'{p_["hours"]:.1f} h' if p_['hours'] < 48 else f'{p_["days"]:.1f} 天'
    print(f'{name:<30s} {p_["step_s"]:>8.2f} {p_["steps"]:>10,.0f} {dur:>12s} '
          f'{p_["usd"]:>10,.0f}')

p_a100 = training_plan(7e9, 10e9, 'A100', 0.45, 8)
p_h100 = training_plan(7e9, 10e9, 'H100', 0.45, 8)
assert p_h100['hours'] < p_a100['hours'] / 2, 'H100 应快 2 倍以上'
p_70b = training_plan(70e9, 300e9, 'H100', 0.40, 64)
assert p_70b['days'] > 3, '70B 预训不是「跑跑看」的量级'
print(f'\\n✅ 估算的价值不在精确（±30%），而在**量级正确** ——')
print(f'   它能立刻区分「6 小时」与「{p_70b["days"]:.0f} 天」，而后者意味着实验设计本身要改。')"""),
    code("""# 反推 MFU：判断「还有多少优化空间」
def infer_mfu(measured_step_s, n_params, batch, seq, gpu='A100', n_gpus=1):
    flops = 6 * n_params * batch * seq * n_gpus
    return flops / (measured_step_s * GPU_TFLOPS[gpu] * 1e12 * n_gpus)

MFU_VERDICT = [
    (0.35, '接近上限 —— 再调优收益有限，考虑加卡或改小实验'),
    (0.20, '中等 —— 检查通信（多卡）与 kernel 融合'),
    (0.10, '偏低 —— 大概率有数据瓶颈或 kernel 问题'),
    (0.00, '**严重瓶颈** —— 先查数据管线，别优化 kernel'),
]
def verdict(mfu):
    for th, v in MFU_VERDICT:
        if mfu >= th: return v

print(f"{'实测单步(s)':>12s} {'反推 MFU':>10s}  判断")
for t in [4.9, 7.0, 12.0, 30.0]:
    mfu = infer_mfu(t, 7e9, 8, 2048, 'A100', 8)
    print(f'{t:>12.2f} {mfu:>9.1%}  {verdict(mfu)}')

mfu_fast = infer_mfu(4.9, 7e9, 8, 2048, 'A100', 8)
mfu_slow = infer_mfu(30.0, 7e9, 8, 2048, 'A100', 8)
assert mfu_fast > 0.35 and mfu_slow < 0.10
print(f'\\n✅ MFU {mfu_slow:.1%} 说明有严重瓶颈；MFU {mfu_fast:.0%} 说明已接近上限。')
print('   **知道天花板在哪，才知道该不该继续优化。**')"""),
    md("""## 5 · GPU 利用率：看**波动模式**，不看平均值

数据瓶颈的特征是**周期性掉到 0**；计算瓶颈是**稳定在高位**。
平均都是 60%，但处方完全不同。"""),
    code("""def simulate_util(pattern, n=120, seed=0):
    r = np.random.default_rng(seed)
    if pattern == 'data_bound':      # 一半时间 100%、一半时间 0%（等数据）
        return np.array([100 if (i // 3) % 2 == 0 else 0 for i in range(n)], float)
    if pattern == 'compute_bound':   # 稳定在 60%
        return np.clip(60 + r.normal(0, 3, n), 0, 100)
    if pattern == 'comm_bound':      # 高位但有规律的通信凹陷
        return np.clip(np.where(np.arange(n) % 8 < 6, 85, 25) + r.normal(0, 3, n), 0, 100)
    raise ValueError(pattern)

def classify_util(u, low_thresh=20):
    mean, std = u.mean(), u.std()
    frac_idle = float((u < low_thresh).mean())
    cv = std / max(mean, 1e-9)
    if frac_idle > 0.25:
        return 'data_bound', f'{frac_idle:.0%} 的时间利用率 <{low_thresh}% -> **等数据**'
    if cv > 0.25:
        return 'comm_bound', f'变异系数 {cv:.2f} 且无长时间空闲 -> 周期性通信凹陷'
    return 'compute_bound', f'稳定在 {mean:.0f}%（cv={cv:.2f}）-> 计算瓶颈'

print(f"{'真实模式':<16s} {'平均利用率':>10s} {'判定':<16s} 依据")
for pat in ['data_bound', 'compute_bound', 'comm_bound']:
    u = simulate_util(pat)
    got, why = classify_util(u)
    mark = '✅' if got == pat else '❌'
    print(f'{pat:<16s} {u.mean():>9.0f}% {got:<16s} {why} {mark}')
    assert got == pat, f'{pat} 被判成 {got}'

u_data, u_comp = simulate_util('data_bound'), simulate_util('compute_bound')
print(f'\\n⚠️  data_bound 平均 {u_data.mean():.0f}%，compute_bound 平均 {u_comp.mean():.0f}% ——')
print('    **平均值几乎一样，处方却完全不同**：')
print('    前者加 num_workers / 预处理离线化；后者优化 kernel 与精度。')
print('✅ 所以要看 `nvidia-smi dmon -s u` 的**时间序列**，不要只看瞬时值。')
print('✅ 诊断顺序必须是 数据 -> 通信 -> 计算：数据瓶颈会掩盖一切。')"""),
    md("""## ✏️ 练习 1：最大可行 batch

实现 `max_batch(n_params, seq, hidden, layers, capacity_gb, **kw)`：
用二分或递增找出**在给定显存下可行的最大 batch**（含 12% 余量），
找不到（batch=1 都放不下）返回 0。"""),
    code("""def max_batch(n_params, seq, hidden, layers, capacity_gb, headroom=0.12, **kw):
    # TODO: 用 total_memory(...) 判断可行性，返回最大可行 batch（整数）
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
b80 = max_batch(7e9, 2048, 4096, 32, 80, trainable_frac=0.001, checkpointing=True)
b24 = max_batch(7e9, 2048, 4096, 32, 24, trainable_frac=0.001, checkpointing=True)
b_full = max_batch(7e9, 2048, 4096, 32, 40)      # 全参数 AdamW，40GB
assert b80 > b24 > 0, f'卡越大 batch 越大 (80G:{b80}, 24G:{b24})'
assert b_full == 0, '7B 全参数 AdamW 在 40GB 上连 batch=1 都放不下'
m_at_b80 = total_memory(7e9, b80, 2048, 4096, 32,
                        trainable_frac=0.001, checkpointing=True)['total']
assert m_at_b80 <= 80 * GB * 0.88, '必须留够余量'
m_at_b80p1 = total_memory(7e9, b80 + 1, 2048, 4096, 32,
                          trainable_frac=0.001, checkpointing=True)['total']
assert m_at_b80p1 > 80 * GB * 0.88, '再加 1 就应该超'
for cap in [24, 40, 80]:
    b = max_batch(7e9, 2048, 4096, 32, cap, trainable_frac=0.001, checkpointing=True)
    print(f'{cap:>3d} GB 卡, 7B+LoRA+checkpoint, seq=2048 -> 最大 batch = {b}')
print('✅ 练习 1 通过：**两分钟算出来，而不是排队半小时试出来**')"""),
    md("""## ✏️ 练习 2：环境兼容性总检

实现 `env_check(gpu, driver, cuda_runtime, arch_list, extensions)`：
`extensions` 形如 `{'flash-attn': {'torch': '2.4', 'cuda': '12.1'}}`，
再给一个当前 torch 版本参数。返回 `{'ok':…, 'problems': [...]}`。
要检查：驱动 vs runtime、GPU arch、每个扩展的 torch/cuda 匹配。"""),
    code("""def env_check(gpu, driver, cuda_runtime, arch_list, extensions, torch_version):
    # TODO: 依次调用 cuda_compatible / arch_supported，再逐个校验扩展
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
EXT_OK = {'flash-attn': {'torch': '2.4', 'cuda': '12.1'},
          'xformers':   {'torch': '2.4', 'cuda': '12.1'}}
r = env_check('A100', 550.54, '12.1', ['sm_70','sm_80','sm_86'], EXT_OK, '2.4')
assert r['ok'], r
r2 = env_check('H100', 550.54, '12.1', ['sm_70','sm_80','sm_86'], EXT_OK, '2.4')
assert not r2['ok'] and any('sm_90' in p or 'H100' in p for p in r2['problems'])
r3 = env_check('A100', 525.85, '12.4', ['sm_80'], EXT_OK, '2.4')
assert not r3['ok'] and any('驱动' in p for p in r3['problems'])
EXT_BAD = {'flash-attn': {'torch': '2.1', 'cuda': '12.1'}}
r4 = env_check('A100', 550.54, '12.1', ['sm_80'], EXT_BAD, '2.4')
assert not r4['ok'] and any('flash-attn' in p for p in r4['problems'])
for name, rr in [('全兼容', r), ('H100+旧arch', r2), ('驱动太旧', r3), ('扩展不匹配', r4)]:
    print(f'{name:<14s} ok={rr["ok"]}')
    for p_ in rr['problems']: print(f'    - {p_}')
print('✅ 练习 2 通过：**这条链无法靠 requirements.txt 复现 —— 要锁进容器镜像**')"""),
    md("""## ✏️ 练习 3：瓶颈定位

实现 `locate_bottleneck(util_series, single_gpu_step_s, multi_gpu_step_s, n_gpus)`：
返回 `('data' | 'comm' | 'compute', 说明)`。
规则：先看利用率序列（数据瓶颈优先）；再看多卡扩展效率
`eff = single / (multi * n_gpus)`，`eff < 0.7` 判为通信瓶颈；否则计算瓶颈。"""),
    code("""def locate_bottleneck(util_series, single_gpu_step_s, multi_gpu_step_s, n_gpus):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
u_d, u_c = simulate_util('data_bound'), simulate_util('compute_bound')
assert locate_bottleneck(u_d, 1.0, 0.2, 8)[0] == 'data', '数据瓶颈优先'
assert locate_bottleneck(u_c, 1.0, 0.30, 8)[0] == 'comm', '扩展效率 1/(0.3*8)=0.42 < 0.7'
assert locate_bottleneck(u_c, 1.0, 0.14, 8)[0] == 'compute', '扩展效率 0.89 -> 计算瓶颈'
for name, u, s, m_ in [('数据', u_d, 1.0, 0.2), ('通信', u_c, 1.0, 0.30),
                       ('计算', u_c, 1.0, 0.14)]:
    b, why = locate_bottleneck(u, s, m_, 8)
    print(f'{name}场景 -> {b:<8s} {why}')
print('\\n✅ 练习 3 通过：**诊断顺序必须是 数据 -> 通信 -> 计算**')
print('   如果 GPU 有 40% 时间在等数据，把 kernel 优化快 2 倍也只提升 30%。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def max_batch(n_params, seq, hidden, layers, capacity_gb, headroom=0.12, **kw):
    budget = capacity_gb * GB * (1 - headroom)
    def fits(b):
        return total_memory(n_params, b, seq, hidden, layers, **kw)['total'] <= budget
    if not fits(1):
        return 0
    lo, hi = 1, 2
    while fits(hi):
        lo, hi = hi, hi * 2
        if hi > 1 << 20: break
    while lo + 1 < hi:                      # 二分：不变式 fits(lo) and not fits(hi)
        mid = (lo + hi) // 2
        if fits(mid): lo = mid
        else: hi = mid
    return lo"""),
    code("""# 练习 2 参考答案
def env_check(gpu, driver, cuda_runtime, arch_list, extensions, torch_version):
    problems = []
    ok_drv, msg_drv = cuda_compatible(driver, cuda_runtime)
    if not ok_drv: problems.append(msg_drv)
    ok_arch, msg_arch = arch_supported(gpu, arch_list)
    if not ok_arch: problems.append(msg_arch)
    for name, need in extensions.items():
        if need.get('torch') != torch_version:
            problems.append(f'{name}: 需要 torch {need["torch"]}，当前 {torch_version} '
                            f'-> "undefined symbol"')
        if need.get('cuda') != cuda_runtime:
            problems.append(f'{name}: 需要 CUDA {need["cuda"]}，当前 {cuda_runtime}')
    return {'ok': not problems, 'problems': problems}"""),
    code("""# 练习 3 参考答案
def locate_bottleneck(util_series, single_gpu_step_s, multi_gpu_step_s, n_gpus):
    kind, why = classify_util(np.asarray(util_series, float))
    if kind == 'data_bound':
        return 'data', f'{why} -> 先修 dataloader（加 workers / 预处理离线化）'
    eff = single_gpu_step_s / (multi_gpu_step_s * n_gpus)
    if eff < 0.7:
        return 'comm', f'多卡扩展效率仅 {eff:.0%} -> 通信瓶颈（查 nvidia-smi topo -m）'
    return 'compute', f'扩展效率 {eff:.0%} 且利用率稳定 -> 计算瓶颈（查 kernel 与精度）'"""),
    md("""---
## 🧪 真实命令胶囊：一份 GPU 上机的标准动作"""),
    code("""RECIPE = r'''
# ── ① 上机第一件事：拿到环境指纹（模块 00 的 env_fingerprint）──────────
nvidia-smi                       # 驱动版本 / CUDA 版本 / 每卡显存与利用率
nvidia-smi -L                    # 列出所有卡与 UUID
nvidia-smi topo -m               # **卡间拓扑**：NVLink 还是 PCIe（决定多卡上限）
python - <<'PY'
import torch
print("torch", torch.__version__, "| cuda", torch.version.cuda,
      "| available", torch.cuda.is_available())
print("arch_list", torch.cuda.get_arch_list())          # 编译进了哪些 sm_XX
print("device_cap", torch.cuda.get_device_capability()) # 这张卡是 sm_XX
PY

# ── ② 提交前：写下三个数字（本模块的核心习惯）─────────────────────────
#   预计显存 __ GB   预计单步 __ s   预计总时长 __ h
#   跑起来后对照实际值。几次之后你的估算会准到 ±20%。

# ── ③ 实时监控（诊断数据瓶颈的关键：看**波动**不看平均）──────────────
nvidia-smi dmon -s pucm                       # sm 利用率/显存/功耗/时钟 时间序列
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1

# ── ④ 出问题时 ────────────────────────────────────────────────────
CUDA_LAUNCH_BLOCKING=1 python train.py        # **第一招**：让报错出现在真正的那一行
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python train.py   # 缓解碎片
python - <<'PY'
import torch
print(torch.cuda.memory_summary())            # 分配器账本
print("peak", torch.cuda.max_memory_allocated() / 1024**3, "GB")   # 峰值 != nvidia-smi
PY

# ── ⑤ profiler：定位到 kernel ────────────────────────────────────
from torch.profiler import profile, ProfilerActivity, schedule
with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
             schedule=schedule(wait=1, warmup=1, active=3),
             record_shapes=True, profile_memory=True) as prof:
    for _ in range(5):
        train_step(); prof.step()
print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))

# ── ⑥ 环境无法用 requirements.txt 复现 -> 锁进镜像（C48 模块 01）────
# FROM nvcr.io/nvidia/pytorch:24.07-py3        # 驱动之上的整条链都固定
'''
print(RECIPE)
for c in ['topo -m', 'get_arch_list', 'dmon', 'CUDA_LAUNCH_BLOCKING',
          'expandable_segments', 'max_memory_allocated', 'key_averages']:
    assert c in RECIPE, c
print('✅ 配方覆盖：环境指纹 / 提交前估算 / 实时监控 / 调试第一招 / profiler / 环境锁定')"""),
    md("""### 小结
- **显存是算术题**：参数 + 梯度 + 优化器状态 + 激活 + 杂项。AdamW 混合精度下**优化器状态 12N，比参数本身还大**。
- **激活常常是主导项**，且朴素注意力下随序列长**平方**增长（FlashAttention 把它变成线性）。
- **OOM 诊断树按成本排序**：峰值/碎片 → 减 batch → 梯度检查点 → 换优化器 → LoRA → 分片 → 换卡。
  **绝大多数在第 3–4 步就解决了**，而很多人直接跳到多卡。
- **「跑了 500 步才 OOM」不是泄漏，是遇到了长样本**。解法是按最长样本规划，或用 **token-budget 动态 batch**。
- **`nvidia-smi` 不是真实占用**（缓存分配器持有）；要看 `max_memory_allocated()`。
- **版本链有四层**（硬件 → 驱动 → CUDA runtime → 框架 → 编译扩展），最脆弱的是编译扩展 →
  **这条链无法靠 requirements.txt 复现，要锁进容器镜像**。
- **`CUDA_LAUNCH_BLOCKING=1` 是 GPU 调试第一招**：kernel 异步启动，不设它看到的栈几乎总是无关的。
- **诊断顺序：数据 → 通信 → 计算**。看利用率的**波动模式**而非平均值——平均 60% 可能是两种完全不同的病。
- **MFU 双向可用**：正向估时长（区分「6 小时」与「20 天」）、反向判断还有多少优化空间。

下一站：**模块 05 · 研究产出与知识产权** —— 做出来之后，怎么把它变成公司的资产。"""),
]
