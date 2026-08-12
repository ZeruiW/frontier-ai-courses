# -*- coding: utf-8 -*-
"""C50 模块 05 · Accelerate、Hub 与推理 API。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–04；C39（分布式训练原理）、C48 模块 02（服务契约）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_accelerate_hub_api.ipynb'),
    ("核心参考", "accelerate 文档、Hub 文档与 safetensors 规范、OpenAI API Reference、Google SRE 的重试与退避实践"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("accelerate", "Accelerate：四行改造与它藏起来的东西", "".join([
        P("<code>accelerate</code> 的定位是：<strong>让同一份训练代码在单卡 / 多卡 / 多机 / TPU / 混合精度下都能跑，而你只改四行</strong>。<code>Trainer</code> 内部就是用它。"),
        CODE("""from accelerate import Accelerator

accelerator = Accelerator(gradient_accumulation_steps=4)      # ① 建
model, optimizer, dataloader, scheduler = accelerator.prepare( # ② prepare 四件套
    model, optimizer, dataloader, scheduler)

for batch in dataloader:
    with accelerator.accumulate(model):                        # ③ 累积上下文
        loss = model(**batch).loss
        accelerator.backward(loss)                             # ④ 替代 loss.backward()
        optimizer.step(); scheduler.step(); optimizer.zero_grad()

# 保存时要先解包
accelerator.wait_for_everyone()
unwrapped = accelerator.unwrap_model(model)
accelerator.save_model(unwrapped, "out")"""),
        TABLE(["这一行", "它替你做了什么"], [
            ["<code>Accelerator()</code>", "读环境（<code>accelerate config</code> / 环境变量）决定后端：单卡 / DDP / FSDP / DeepSpeed / TPU；初始化进程组"],
            ["<code>prepare(model)</code>", "<code>.to(device)</code>；多卡时包 DDP/FSDP；混合精度时挂 autocast"],
            ["<code>prepare(dataloader)</code>", "<strong>换掉 sampler 做分布式切分</strong>（每个 rank 只拿 1/N）；把 batch 自动搬到设备"],
            ["<code>prepare(optimizer)</code>", "包一层以配合梯度缩放（fp16 的 GradScaler）与梯度累积"],
            ["<code>accelerator.backward(loss)</code>", "fp16 时先 scale 再 backward；累积期间跳过梯度同步（省通信）"],
            ["<code>accumulate(model)</code>", "自动管理「什么时候该同步梯度」——累积中间步用 <code>no_sync()</code> 避免无用的 all-reduce"],
        ]),
        DUAL(
            "最容易被忽略、也最重要的是 <strong><code>prepare(dataloader)</code> 换掉了 sampler</strong>。这意味着<em>你的 <code>batch_size</code> 是每个进程的</em>——8 卡时实际有效 batch 是 8 倍。<strong>这与 <code>TrainingArguments</code> 的 <code>per_device_train_batch_size</code> 是同一件事</strong>（模块 03 的乘法关系）。写裸 <code>accelerate</code> 代码时忘了这一点，就会「换台机器超参全变」。",
            "第二个隐藏行为是<strong>累积期间的梯度同步优化</strong>。DDP 默认在每次 <code>backward</code> 后就 all-reduce 梯度，但梯度累积时中间几步的同步是<em>纯浪费</em>（最终只用累加值）。<code>accelerator.accumulate()</code> 会在非同步步用 <code>model.no_sync()</code> 跳过通信——<strong>在 <code>grad_accum=8</code> 时能省掉 7/8 的梯度通信量</strong>。这是个不小的加速，而且完全对用户透明。自己写 DDP 循环忘了这个是常见的性能损失来源（C39 有完整的通信量分析）。",
        ),
        H3("四类日常操作的正确写法"),
        UL([
            "<strong>打印/日志只在主进程</strong>：<code>accelerator.print(...)</code>（或 <code>if accelerator.is_main_process:</code>）。否则 8 卡会打 8 遍。",
            "<strong>保存前解包</strong>：<code>accelerator.unwrap_model(model)</code>。直接保存 DDP 包装后的模型会得到带 <code>module.</code> 前缀的键名——加载时全部 <code>missing_keys</code>（模块 01 那个坑）。",
            "<strong>收集指标</strong>：<code>accelerator.gather_for_metrics(preds)</code>。它比裸 <code>gather</code> 多做一件事——<em>去掉分布式采样为了整除而重复的样本</em>，否则最后几条会被重复计入。",
            "<strong>同步点</strong>：<code>accelerator.wait_for_everyone()</code>。在保存、评估、写文件前后需要，否则 rank 0 还没写完别的 rank 就去读。",
        ]),
        CALLOUT("warn", "<strong><code>gather_for_metrics</code> vs <code>gather</code></strong> 是个具体且容易出错的区别。分布式采样器为了让每个 rank 拿到<em>相同数量</em>的样本，会在数据集末尾重复少量样本（padding the dataset）。裸 <code>gather</code> 会把这些重复样本也收上来，导致评估指标有微小偏差（数据集小、卡多时偏差更明显）。<code>gather_for_metrics</code> 知道原始长度并裁掉重复部分。<em>症状是「多卡评估结果与单卡略有不同」——很容易被误认为是随机性。</em>"),
    ])),
    ("hub", "Hub 与 safetensors：分发、版本与安全", "".join([
        P("模型要给别人用（或给自己的推理服务用），就要经过 Hub 或某个等价的存储。这里有三件需要讲清的事。"),
        H3("① revision：可变标签 vs commit sha"),
        CODE("""# ❌ 不可复现：main 分支随时会变
model = AutoModel.from_pretrained("org/model")

# ✅ 可复现：钉死 commit
model = AutoModel.from_pretrained("org/model",
                                  revision="a1b2c3d4e5f6...")   # 或 tag "v1.2"

# 记录到实验日志里（C37/C40）
from huggingface_hub import HfApi
sha = HfApi().model_info("org/model").sha
print(f"loaded revision={sha}")"""),
        P("Hub 的缓存<strong>按 commit sha 分目录</strong>（<code>snapshots/&lt;sha&gt;/</code>），所以钉死 revision 既保证可复现，也保证缓存命中稳定。<em>用 <code>main</code> 的项目在上游更新权重后会静默换模型</em>——这是「昨天还好今天变差」的一个真实来源。"),
        H3("② safetensors：为什么它比 pickle 重要"),
        TABLE(["", "<code>pytorch_model.bin</code>（pickle）", "<code>model.safetensors</code>"], [
            ["格式", "Python pickle 字节流", "header JSON + 连续张量字节"],
            ["<strong>加载时执行代码</strong>", "<strong>会</strong>（<code>__reduce__</code> 可运行任意命令）", "<strong>不会</strong>（纯数据解析）"],
            ["零拷贝 / mmap", "❌ 需要反序列化到内存", "✅ 可直接内存映射"],
            ["部分加载", "❌ 要读整个文件", "✅ 按 tensor 名单独读"],
            ["加载速度（大模型）", "慢", "<strong>快 2–5 倍</strong>"],
        ]),
        CALLOUT("danger", "<p><strong>从不可信来源加载 <code>.bin</code> 等于运行陌生人的脚本</strong>。pickle 的反序列化会调用对象的 <code>__reduce__</code>，构造一个恶意 pickle 让它执行 <code>os.system(...)</code> 是教科书级的攻击。<code>safetensors</code> 从格式上消除了这个可能。同样的道理适用于 <code>trust_remote_code=True</code>——它会执行 repo 里的 <code>modeling_*.py</code>。<em>两者都只对可信来源使用</em>。生产上应该：只从组织内部 registry 或已审计的 repo 加载、强制 <code>use_safetensors=True</code>、并对权重文件做哈希校验。这与 C48 模块 01 的镜像供应链安全是同一类问题。</p>", "pickle 是可执行的"),
        H3("③ 上传：模型卡片不是可选项"),
        P("<code>push_to_hub</code> 很简单，但一个只有权重没有说明的 repo 三个月后连你自己都用不了。<strong>模型卡片至少要写清六件事</strong>："),
        UL([
            "<strong>基座与 revision</strong>：从哪个 checkpoint 的哪个 commit 微调而来。",
            "<strong>数据</strong>：训练数据是什么、多少条、怎么构造的、有什么已知偏差。",
            "<strong>超参</strong>：有效 batch、lr、epoch、LoRA 配置（直接贴 <code>TrainingArguments</code>）。",
            "<strong>评测</strong>：在什么集合上、什么指标、多少个种子、与什么基线比。",
            "<strong>输入格式</strong>：<em>必须写清 chat template 或 prompt 格式</em>——这是使用者最需要、最常缺失的信息。",
            "<strong>限制与许可</strong>：不适用的场景、基座模型的许可传递性。",
        ]),
        CALLOUT("intuition", "关于许可有一条实操提醒：<strong>微调模型的许可通常受基座许可约束</strong>。Llama 系有自己的社区许可（含使用量与命名条款），Gemma、Qwen 等各有条款。「我只是训了个 adapter」不改变这一点——adapter 离开基座无法工作，所以基座的条款照样适用。<em>商用前务必读一遍基座的许可，这不是形式主义</em>（C12/C45 有关于合规的系统讨论）。"),
    ])),
    ("client", "调远端模型：重试、限流、幂等", "".join([
        P("JD 里的「OpenAI APIs」不只是「会写 <code>client.chat.completions.create</code>」。<strong>把一个 API 调用做成生产可用的东西，需要四层防护</strong>——这与 C48 模块 02 讲的服务端护栏是同一套原理的客户端镜像。"),
        TABLE(["层", "解决什么", "关键点"], [
            ["<strong>① 重试与退避</strong>", "瞬时故障（429、5xx、网络抖动）", "<strong>指数退避 + 抖动</strong>；只重试<em>可重试</em>的错误；尊重 <code>Retry-After</code>"],
            ["<strong>② 客户端限流</strong>", "不把自己的配额打爆、不给服务端加压", "令牌桶，<strong>RPM 与 TPM 双限</strong>（模块与 C48 一致）"],
            ["<strong>③ 幂等</strong>", "重试不产生重复副作用/重复扣费", "<code>Idempotency-Key</code>（或自建缓存）"],
            ["<strong>④ 超时与预算</strong>", "不让一个请求挂死整个流程", "分层超时；总预算（token/金额）上限与熔断"],
        ]),
        H3("重试：哪些能重试、退避怎么算"),
        MATH("\\text{delay}_k = \\min\\left(\\text{cap},\\; \\text{base} \\cdot 2^{k}\\right) \\times U(0.5, 1.5)"),
        TABLE(["状态码", "含义", "能重试吗", "怎么做"], [
            ["<code>429</code>", "限流", "✅", "<strong>优先用响应里的 <code>Retry-After</code></strong>，没有才用退避"],
            ["<code>500 / 502 / 503 / 504</code>", "服务端错误", "✅", "指数退避"],
            ["<code>408</code> / 连接超时", "超时", "✅（若幂等）", "退避 + 幂等键"],
            ["<code>400</code>", "请求本身有问题", "❌", "重试一万次也一样错——<strong>要报出来</strong>"],
            ["<code>401 / 403</code>", "认证/权限", "❌", "配置问题"],
            ["<code>404</code>", "模型不存在", "❌", "配置问题"],
            ["<code>context_length_exceeded</code>", "上下文超限", "❌（但可降级）", "截断输入或换更大上下文的模型后<em>重新</em>请求"],
        ]),
        CALLOUT("warn", "<strong>抖动（jitter）不是可选的</strong>。如果一批客户端同时遇到 429、又都用相同的确定性退避，它们会<em>同步地</em>在同一时刻重试，形成周期性的洪峰——这叫「惊群」（thundering herd），会让服务端更难恢复。加一个 <code>U(0.5, 1.5)</code> 的随机因子就能把重试打散。<em>这是分布式系统里最便宜、最常被忽略的一行代码。</em>"),
        H3("流式：客户端侧要处理的三件事"),
        UL([
            "<strong>增量拼接</strong>：每个 chunk 的 <code>delta.content</code> 可能为 <code>None</code>（第一个 chunk 通常只有 <code>role</code>），累加时要跳过。",
            "<strong>usage 不在流里</strong>：默认流式响应<em>不带 usage</em>，要计费/统计得开 <code>stream_options={\"include_usage\": True}</code>（最后一个 chunk 带 usage）。<em>不开的话你无法回答「这次调用花了多少 token」。</em>",
            "<strong>断连要取消</strong>：客户端放弃后要真正关闭连接（用 <code>with</code> 或显式 <code>close()</code>），否则服务端还在为你生成——这既浪费你的配额也浪费服务端算力（C48 模块 02 的第三个 SSE 坑的另一侧）。",
        ]),
        H3("tool calling 与结构化输出"),
        P("两个常被混淆的能力："),
        UL([
            "<strong>tool / function calling</strong>：模型输出「我要调用哪个函数、参数是什么」，<em>你</em>去执行并把结果回传，模型继续。它是一个<strong>多轮协议</strong>——注意要把 <code>tool_calls</code> 的助手消息与对应的 <code>tool</code> 角色结果消息都追加回 <code>messages</code>，否则下一轮模型会困惑。",
            "<strong>结构化输出 / JSON schema</strong>：约束模型的输出必须符合一个 schema。<em>它不是 tool calling</em>——没有函数要执行，只是保证格式。用 <code>response_format={\"type\":\"json_schema\", ...}</code>。<strong>比「在 prompt 里请求 JSON 然后自己解析」可靠得多</strong>，但仍要处理「schema 合法而语义错误」的情况。",
        ]),
        CALLOUT("intuition", "一条关于成本的实操建议：<strong>把 token 计数与花费做成可观测的</strong>。每次调用记录 <code>model / prompt_tokens / completion_tokens / 业务标签</code>，聚合成「每个功能每天花多少钱」。<em>没有这个数据，你无法回答「哪个功能在烧钱」，也就无法优化</em>。这与 C48 模块 05 的成本归因是同一件事，只是在客户端侧做。加上「缓存命中的 prompt 便宜很多」这一点（prompt caching），把系统提示固定在前缀能显著省钱——这是最便宜的一个优化。"),
    ])),
    ("observability", "把调用做成可观测的：日志、指标与降级", "".join([
        P("四层防护解决的是「单次调用怎么活下来」。但一个真实系统还需要回答三个运营问题：<strong>现在健康吗、刚才为什么慢、这个月钱花在哪</strong>。这三个问题的答案全部来自「你在调用现场记了什么」。"),
        TABLE(["记什么", "字段", "用来回答什么"], [
            ["<strong>身份</strong>", "<code>model</code>（服务端回显的实际模型）、<code>request_id</code>、<code>业务标签</code>", "「哪个功能、用的哪个模型」——成本归因与故障定位的第一层"],
            ["<strong>用量</strong>", "<code>prompt_tokens</code> / <code>completion_tokens</code> / <code>cached_tokens</code>", "「花了多少钱」；缓存命中率"],
            ["<strong>时延</strong>", "TTFT、总时长、<strong>排队/重试耗时单独记</strong>", "「慢在哪」——是服务端慢还是自己在退避等待"],
            ["<strong>结果</strong>", "<code>finish_reason</code>、状态码、重试次数", "<code>length</code> 比例上升 = 输出被截断，是质量与容量的双重预警（C48 模块 02）"],
        ]),
        DUAL(
            "其中<strong>「重试耗时要单独记」</strong>是最容易漏、也最容易造成误判的一条。假设你观测到 P95 端到端延迟是 8 秒，很自然会去优化 prompt 或换更快的模型——但如果其中 6 秒是你自己在退避等待（因为撞了限流），那么真正的问题是<em>并发控制</em>，而不是模型速度。<strong>把「服务端耗时」与「客户端等待耗时」分成两个指标</strong>，能立刻区分这两种完全不同的问题。",
            "<code>finish_reason</code> 的监控价值同样被低估。它只有几个取值（<code>stop</code> / <code>length</code> / <code>tool_calls</code> / <code>content_filter</code>），但 <code>length</code> 的比例是个极好的<strong>领先指标</strong>：它上升意味着输出被 <code>max_tokens</code> 截断——可能是用户在问更复杂的问题、可能是 prompt 变了、也可能是模型开始啰嗦。<em>无论哪种，都意味着「用户看到的答案是不完整的」，而这在错误率与延迟指标上完全看不出来。</em>",
        ),
        H3("降级：当上游不可用时"),
        P("重试解决瞬时故障，但如果上游<em>持续</em>不可用（配额耗尽、区域故障、模型下线），无限重试只会让你的服务一起挂掉。这时需要<strong>降级链</strong>："),
        UL([
            "<strong>换模型</strong>：主模型不可用 → 退到更小/更便宜/另一家的模型。前提是你的 prompt 不依赖某个模型的特殊行为（这也是「别过度依赖单一模型的怪癖」的实际理由）。",
            "<strong>降质量</strong>：把 <code>max_tokens</code> 调小、关掉思考链、跳过重排——换取在配额内完成。",
            "<strong>用缓存/兜底答案</strong>：语义相近的历史回答、或一个诚实的「暂时不可用」。",
            "<strong>熔断（circuit breaker）</strong>：连续失败 N 次后<em>直接快速失败一段时间</em>，不再发请求。这既保护上游、也让你的服务快速返回而不是全体挂在超时上（C48 模块 02 的背压在客户端的镜像）。",
        ]),
        CALLOUT("warn", "降级链有一个必须显式决定的问题：<strong>降级后的结果要不要标记</strong>？如果用小模型的回答与主模型的回答混在一起、事后无法区分，那么你的离线评测会被污染（「上周质量下降」其实是那天降级了 20% 的流量）。<em>把降级层级作为一个字段记进日志与返回值</em>，这一个字段能省掉未来无数次归因困惑。"),
        CALLOUT("intuition", "把这一节浓缩成一句可执行的建议：<strong>写一个统一的 <code>call_llm()</code> 封装，把重试、限流、幂等、超时、日志、降级全部放进去，然后<em>禁止业务代码直接调 SDK</em></strong>。这样所有防护与观测都是默认开启的，而不是靠每个调用点自觉。这是本课模块 05 最实际的产出——notebook 里的客户端骨架就是它的雏形。"),
    ])),
    ("ledger", "算一笔账：限流下的吞吐与上下文预算", "".join([
        MATH("\\text{最大吞吐(请求/分)} = \\min\\left(\\texttt{RPM},\\; \\frac{\\texttt{TPM}}{\\bar{n}_{tokens}}\\right)"),
        TABLE(["配额", "平均 token/请求", "RPM 限制", "TPM 限制", "<strong>实际瓶颈</strong>"], [
            ["RPM=60, TPM=60k", "500", "60", "120", "<strong>RPM</strong>（60/分）"],
            ["RPM=60, TPM=60k", "2000", "60", "30", "<strong>TPM</strong>（30/分）"],
            ["RPM=3500, TPM=90k", "1500", "3500", "60", "<strong>TPM</strong>（60/分）"],
        ]),
        P("这张表说明一个常被误解的点：<strong>大多数时候真正的瓶颈是 TPM 而不是 RPM</strong>。看到「RPM=3500」以为可以每秒发 58 个请求，实际上 TPM 只允许 60 个请求/分钟——<em>差 58 倍</em>。所以客户端限流必须双维度，且要按<strong>预估 token</strong>预扣、结束后按实际结算（C48 模块 02 的练习就是这个）。"),
        P("第二笔账是<strong>上下文预算</strong>，它在多轮对话里会随轮数增长："),
        MATH("L_{available}(t) = L_{model} - L_{system} - \\sum_{i<t}(L_{user,i} + L_{assist,i}) - L_{reserve}"),
        TABLE(["策略", "做法", "代价"], [
            ["<strong>滑窗</strong>", "只保留最近 N 轮", "丢失早期信息（用户会发现「它忘了」）"],
            ["<strong>摘要压缩</strong>", "把早期对话摘要成一段", "额外的 LLM 调用成本 + 摘要失真"],
            ["<strong>检索式</strong>", "把历史存进向量库，按需检索", "复杂度高（C11/C33 的内容）"],
            ["<strong>硬失败</strong>", "超了就报错让用户开新会话", "体验差但最诚实"],
        ]),
        P("<strong>无论选哪种，都必须先能算出这个数字</strong>。最糟的做法是不算——然后在某个长对话上突然收到 <code>context_length_exceeded</code>，或者更隐蔽地被服务端静默截断。"),
        CALLOUT("intuition", "把本模块浓缩成一句话：<strong>模型训练完只是一半，「把它安全地送出去」和「可靠地调用别人的模型」是另一半，而这一半的技术含量全在「失败处理」上</strong>——保存时要解包、加载时要钉 revision、格式要用 safetensors、调用要重试退避限流幂等、上下文要算预算。<em>这些都不难，但少任何一个，系统就会在某个你没预料到的时刻出问题。</em>"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>分布式配置的表达层</strong>：FSDP/DeepSpeed 的参数散落在 <code>accelerate config</code>、<code>TrainingArguments</code>、JSON 配置与环境变量里，同一个概念（如 ZeRO 阶段、参数分片粒度）在不同层有不同名字。这是当前最真实的工程摩擦，社区在推动收敛但尚未完成。",
            "<strong>模型供应链安全</strong>：safetensors 解决了格式层的代码执行，但 <code>trust_remote_code</code>、自定义 tokenizer、以及权重本身的后门（数据投毒、权重篡改）仍是开放问题。模型签名与 SBOM（软件物料清单）式的溯源正在探索，尚无普遍实践（C44 有攻防视角的讨论）。",
            "<strong>API 协议的边角语义</strong>：OpenAI 兼容已是事实标准，但 <code>logprobs</code> 的定义、流式增量的 <code>tool_calls</code> 拼装方式、结构化输出的约束表达、<code>seed</code> 是否被尊重，各家实现不一致。跨供应商切换时这些边角会咬人。",
            "<strong>prompt 缓存的定价与语义</strong>：各家的前缀缓存策略（命中条件、TTL、折扣比例）不同且会变，让「怎么组织 prompt 最省钱」成了一个随时间移动的目标。缓存命中还会影响延迟分布，使容量规划更复杂。",
            "<strong>可复现性的现实边界</strong>：即使钉死 revision 与随机种子，服务端模型更新、批处理下的浮点归约顺序、以及 kernel 版本变化都会让输出改变。<em>「LLM 应用的可复现」目前只能是「统计上可复现 + 输入输出留档」</em>，这与 C40 的实验纪律有持续的张力。",
        ]),
        CALLOUT("paper", "必读：accelerate 文档的 <em>Quicktour</em>、<em>Migrating to Accelerate</em> 与 <em>Distributed Evaluation</em>（<code>gather_for_metrics</code> 的语义在那里）；huggingface_hub 的 <em>Download files</em>（revision 与缓存布局）与 safetensors 格式规范；OpenAI API Reference 的 <em>Chat</em>、<em>Streaming</em>、<em>Function calling</em>、<em>Structured Outputs</em>、<em>Rate limits</em> 五节；AWS Architecture Blog 的 <em>Exponential Backoff and Jitter</em>（抖动为什么必需，附量化对比）。原理侧：C39（分布式通信）、C48 模块 02/05（服务契约与成本）、C33（上下文与记忆管理）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · Accelerate、Hub 与推理 API（迷你复刻分布式切分 / 权重键名 / 重试限流客户端）

目标：把 **prepare(dataloader) 的分布式切分 → gather_for_metrics 的去重 → unwrap 前后的键名 →
revision 与缓存布局 → 指数退避+抖动 → RPM/TPM 双限 → 幂等 → 流式增量拼接 → 上下文预算** 从零写一遍。

路线：分布式切分与有效 batch → gather 的重复样本问题 → unwrap 与 module. 前缀 →
safetensors vs pickle → 退避与惊群 → 双限令牌桶 → 幂等缓存 → 流式拼接与 usage →
上下文预算与滑窗 → ✏️ 练习 → 📖 答案 → 🧪 成本可观测胶囊。

> 心智模型：**这一层的技术含量全在「失败处理」上**——少任何一个防护，系统就会在你没预料到的时刻出问题。"""),
    md("""## 1 · prepare(dataloader)：换掉 sampler、每个 rank 只拿 1/N

**你的 `batch_size` 是每个进程的** —— 8 卡时有效 batch 是 8 倍。
这与 `TrainingArguments.per_device_train_batch_size` 是同一件事（模块 03 的乘法关系）。"""),
    code("""import numpy as np, math, json, hashlib, random, time
rng = np.random.default_rng(0)

def distributed_sampler(n_samples, rank, world_size, drop_last=False, seed=0, epoch=0):
    '''复刻 DistributedSampler：按 rank 交错切分；不整除时**重复补齐**（关键！）。'''
    idx = list(np.random.default_rng(seed + epoch).permutation(n_samples))
    if drop_last:
        usable = (n_samples // world_size) * world_size
        idx = idx[:usable]
    else:
        per = math.ceil(n_samples / world_size)
        total = per * world_size
        # 为了让每个 rank 拿到相同数量，**在末尾重复一些样本**
        while len(idx) < total:
            idx += idx[:total - len(idx)]
    return idx[rank::world_size]

N, W = 10, 4
parts = [distributed_sampler(N, r, W, seed=1) for r in range(W)]
print(f'{N} 个样本切给 {W} 个 rank（不 drop_last）:')
for r, p in enumerate(parts):
    print(f'  rank {r}: {p}  (len={len(p)})')
sizes = [len(p) for p in parts]
assert len(set(sizes)) == 1, '每个 rank 必须拿到相同数量（否则 all-reduce 会卡死）'
flat = [i for p in parts for i in p]
assert len(flat) == sizes[0] * W
n_dup = len(flat) - len(set(flat))
print(f'\\n⚠️  为了整除，末尾**重复了 {n_dup} 个样本** —— 这是 gather_for_metrics 要处理的问题。')
assert n_dup > 0, '10 不能被 4 整除 -> 必然有重复'

parts_drop = [distributed_sampler(N, r, W, drop_last=True, seed=1) for r in range(W)]
flat_drop = [i for p in parts_drop for i in p]
assert len(flat_drop) == len(set(flat_drop)), 'drop_last=True 无重复'
assert len(flat_drop) < N, '但会丢掉最后几个样本'
print(f'drop_last=True: 无重复，但丢了 {N - len(flat_drop)} 个样本（训练可接受，评估不可）')"""),
    code("""def effective_batch(per_device_bs, grad_accum, world_size):
    return per_device_bs * grad_accum * world_size

print(f"{'per_device':>11s} {'accum':>6s} {'world':>6s} {'有效batch':>10s}")
for pd, ga, ws in [(8, 4, 1), (8, 4, 8), (8, 1, 8), (1, 32, 8)]:
    print(f'{pd:>11d} {ga:>6d} {ws:>6d} {effective_batch(pd,ga,ws):>10d}')
assert effective_batch(8, 4, 1) == 32 and effective_batch(8, 4, 8) == 256
print('\\n⚠️  同一份代码、同样的 batch_size，1 卡与 8 卡的有效 batch 差 8 倍。')
print('✅ 换机器时必须重新算有效 batch —— 这是「换台机器超参全变」的根源。')

# 累积期间跳过梯度同步能省多少通信
def grad_comm_volume(n_params, grad_accum, world_size, skip_intermediate=True):
    '''ring all-reduce 的通信量 ≈ 2*(W-1)/W * N 每次同步。'''
    per_sync = 2 * (world_size - 1) / world_size * n_params
    n_syncs = 1 if skip_intermediate else grad_accum
    return per_sync * n_syncs

N_P, GA, WS = 7e9, 8, 8
naive = grad_comm_volume(N_P, GA, WS, skip_intermediate=False)
smart = grad_comm_volume(N_P, GA, WS, skip_intermediate=True)
print(f'\\ngrad_accum={GA}, {WS} 卡, 7B 参数:')
print(f'  每步都同步 : {naive*2/1e9:>8.1f} GB/优化步 (bf16)')
print(f'  只在最后同步: {smart*2/1e9:>8.1f} GB/优化步')
print(f'  省 {(1-smart/naive):.0%} 的梯度通信量')
assert abs(naive / smart - GA) < 1e-9
print('✅ accelerator.accumulate() 自动用 no_sync() 做这件事 —— 自己写 DDP 循环常常漏掉。')"""),
    md("""## 2 · gather_for_metrics：为什么裸 gather 会让指标有偏"""),
    code("""def naive_gather(per_rank_preds):
    '''裸 gather：把所有 rank 的预测拼起来 —— **包含重复样本**。'''
    return [x for p in per_rank_preds for x in p]

def gather_for_metrics(per_rank_preds, n_original):
    '''知道原始长度，裁掉为整除而重复的部分。'''
    return naive_gather(per_rank_preds)[:n_original]

# 20 个样本、6 个 rank（不整除）
N_EVAL, WS2 = 20, 6
labels = list(rng.integers(0, 2, size=N_EVAL))
parts = [distributed_sampler(N_EVAL, r, WS2, seed=2) for r in range(WS2)]
# 假设模型对前 18 个样本全对、后 2 个全错（构造一个可验证的场景）
def predict(i): return labels[i] if i < 18 else 1 - labels[i]
per_rank = [[(i, predict(i)) for i in p] for p in parts]

def accuracy(pairs):
    return float(np.mean([pred == labels[i] for i, pred in pairs]))

g_naive = naive_gather(per_rank)
# 用「原始索引集合」去重来模拟正确做法
seen, g_dedup = set(), []
for i, pred in g_naive:
    if i not in seen:
        seen.add(i); g_dedup.append((i, pred))

print(f'原始样本数 {N_EVAL}, {WS2} 个 rank')
print(f'裸 gather 收到 {len(g_naive)} 条（含 {len(g_naive)-len(g_dedup)} 条重复）')
print(f'去重后        {len(g_dedup)} 条')
print(f'\\naccuracy: 裸 gather {accuracy(g_naive):.4f} | 去重后 {accuracy(g_dedup):.4f}')
assert len(g_naive) > N_EVAL, '裸 gather 的条数超过原始样本数'
assert len(g_dedup) == N_EVAL
assert accuracy(g_naive) != accuracy(g_dedup), '重复样本会让指标有偏'
print('\\n⚠️  症状：「多卡评估结果与单卡略有不同」—— 很容易被误认为是随机性。')
print('✅ 用 accelerator.gather_for_metrics()，它知道原始长度并裁掉重复部分。')"""),
    md("""## 3 · unwrap_model：`module.` 前缀会让所有键 missing"""),
    code("""class DDPWrapper:
    '''DDP 包装：state_dict 的键名会多一个 module. 前缀。'''
    def __init__(self, module): self.module = module
    def state_dict(self):
        return {f'module.{k}': v for k, v in self.module.state_dict().items()}

class TinyNet:
    def __init__(self):
        self._sd = {'encoder.weight': np.ones((4, 4)), 'classifier.weight': np.zeros((4, 2))}
    def state_dict(self): return dict(self._sd)

net = TinyNet()
wrapped = DDPWrapper(net)
print('未包装的键:', sorted(net.state_dict()))
print('DDP 包装后:', sorted(wrapped.state_dict()))

def load_into(model_keys, state_dict):
    file_keys = set(state_dict)
    return {'missing': sorted(set(model_keys) - file_keys),
            'unexpected': sorted(file_keys - set(model_keys))}

model_keys = list(net.state_dict())
bad = load_into(model_keys, wrapped.state_dict())
good = load_into(model_keys, net.state_dict())
print(f'\\n❌ 直接保存 DDP 包装后的模型: missing={bad["missing"]}')
print(f'                              unexpected={bad["unexpected"]}')
print(f'✅ 先 unwrap 再保存:            missing={good["missing"]}, unexpected={good["unexpected"]}')
assert len(bad['missing']) == len(model_keys), '**全部键都 missing** -> 模型等于随机初始化'
assert good['missing'] == [] and good['unexpected'] == []
print('\\n⚠️  这正是模块 01 那个坑：加载「成功」了，只给个警告，但模型是随机的。')
print('✅ accelerator.unwrap_model(model) 之后再保存。')

def strip_prefix(sd, prefix='module.'):
    '''补救：手动剥前缀（拿到别人错存的 checkpoint 时用）。'''
    return {(k[len(prefix):] if k.startswith(prefix) else k): v for k, v in sd.items()}
fixed = load_into(model_keys, strip_prefix(wrapped.state_dict()))
assert fixed['missing'] == [] and fixed['unexpected'] == []
print('✅ 补救手段：strip_prefix("module.") 能修好已经错存的 checkpoint')"""),
    md("""## 4 · safetensors vs pickle：格式决定安全边界"""),
    code("""# 用一个「假 pickle」演示：反序列化时会执行 __reduce__ 里的东西
EXECUTED = []

class MaliciousPayload:
    '''模拟恶意 pickle：反序列化时执行任意代码。'''
    def __reduce__(self):
        return (EXECUTED.append, ('攻击者的代码被执行了',))

def fake_pickle_load(obj):
    '''模拟 pickle.load：会调用 __reduce__ 并执行。'''
    if hasattr(obj, '__reduce__') and not isinstance(obj, (dict, list, np.ndarray)):
        fn, args = obj.__reduce__()
        return fn(*args)
    return obj

def safetensors_load(header_and_bytes):
    '''模拟 safetensors：纯数据解析，**不会调用任何用户代码**。'''
    header, blob = header_and_bytes
    out = {}
    for name, meta in header.items():
        s, e = meta['offsets']
        out[name] = np.frombuffer(blob[s:e], dtype=meta['dtype']).reshape(meta['shape'])
    return out

assert EXECUTED == []
fake_pickle_load(MaliciousPayload())
print(f'❌ pickle 路径: EXECUTED = {EXECUTED}   ← 加载权重就执行了代码')
assert EXECUTED == ['攻击者的代码被执行了'], 'pickle 的反序列化会执行 __reduce__'

# safetensors：header 是纯 JSON，数据是连续字节，没有执行入口
arr = np.arange(8, dtype=np.float32)
blob = arr.tobytes()
header = {'weight': {'dtype': 'float32', 'shape': [2, 4], 'offsets': [0, len(blob)]}}
EXECUTED.clear()
loaded = safetensors_load((header, blob))
print(f'\\n✅ safetensors 路径: EXECUTED = {EXECUTED}   ← 纯数据，无执行入口')
assert EXECUTED == [], 'safetensors 不执行任何用户代码'
assert np.allclose(loaded['weight'], arr.reshape(2, 4))
# 且支持按名字部分加载 / mmap（零拷贝）
assert list(header) == ['weight'], 'header 里有全部张量的名字与偏移 -> 可单独读某个张量'
print('   而且 header 里有全部张量的名字与偏移 -> 可按需部分加载、可 mmap 零拷贝。')
print('\\n✅ 生产规则：强制 use_safetensors=True；trust_remote_code 只对可信 repo 开。')"""),
    md("""### revision：钉死 commit sha 才可复现"""),
    code("""HUB = {                       # 模拟 Hub：一个 repo 的历史
    'org/model': {
        'main': 'sha_c3',                                   # 可变标签！
        'v1.0': 'sha_a1',
        'commits': {'sha_a1': {'w': 1.0}, 'sha_b2': {'w': 2.0}, 'sha_c3': {'w': 3.0}},
    }
}
CACHE = {}

def hub_download(repo, revision='main'):
    '''缓存按 **commit sha** 分目录 -> 钉死 revision 既可复现也让缓存稳定命中。'''
    meta = HUB[repo]
    sha = meta.get(revision, revision)
    if sha not in meta['commits']:
        raise FileNotFoundError(f'revision {revision!r} not found')
    path = f'~/.cache/huggingface/hub/models--{repo.replace("/","--")}/snapshots/{sha}/'
    hit = path in CACHE
    CACHE[path] = meta['commits'][sha]
    return meta['commits'][sha], sha, path, hit

w1, sha1, p1, _ = hub_download('org/model', 'main')
print(f'revision="main"  -> sha={sha1}, w={w1["w"]}')
HUB['org/model']['main'] = 'sha_b2'                 # 上游更新了 main
w2, sha2, p2, _ = hub_download('org/model', 'main')
print(f'上游更新 main 后 -> sha={sha2}, w={w2["w"]}   ← **权重悄悄变了**')
assert w1['w'] != w2['w'], '用 main 会在上游更新后静默换模型'

w3, sha3, _, _ = hub_download('org/model', 'sha_a1')
HUB['org/model']['main'] = 'sha_c3'
w4, sha4, _, hit = hub_download('org/model', 'sha_a1')
print(f'\\nrevision="sha_a1" -> w={w3["w"]}；上游再变后仍然 w={w4["w"]}，缓存命中={hit}')
assert w3 == w4 and sha3 == sha4, '钉死 sha 后完全可复现'
assert hit, '同一个 sha 命中同一个缓存目录'
print('\\n⚠️  用 main 的项目在上游更新权重后会静默换模型 ——')
print('   这是「昨天还好今天变差」的一个真实来源。')
print('✅ 生产上钉 commit sha，并把它记进实验日志（C37/C40）。')"""),
    md("""## 5 · 客户端四层防护：退避+抖动 / 双限 / 幂等 / 超时"""),
    code("""RETRYABLE = {408, 429, 500, 502, 503, 504}
NON_RETRYABLE = {400, 401, 403, 404, 422}

class APIError(Exception):
    def __init__(self, status, retry_after=None):
        super().__init__(f'HTTP {status}')
        self.status, self.retry_after = status, retry_after

def backoff_delay(attempt, base=0.5, cap=30.0, jitter=True, rnd=None):
    '''指数退避 + 抖动。抖动**不是可选的** —— 它防惊群。'''
    d = min(cap, base * (2 ** attempt))
    if jitter:
        r = rnd or random.Random()
        d *= r.uniform(0.5, 1.5)
    return d

def should_retry(err):
    return isinstance(err, APIError) and err.status in RETRYABLE

def call_with_retry(fn, max_attempts=5, base=0.5, cap=30.0, rnd=None, sleep=lambda s: None):
    delays = []
    for attempt in range(max_attempts):
        try:
            return fn(attempt), delays
        except APIError as e:
            if not should_retry(e) or attempt == max_attempts - 1:
                raise
            # 优先尊重 Retry-After
            d = e.retry_after if e.retry_after is not None else \\
                backoff_delay(attempt, base, cap, rnd=rnd)
            delays.append(round(d, 3)); sleep(d)
    raise RuntimeError('unreachable')

# 前 3 次 429，第 4 次成功
calls = {'n': 0}
def flaky(attempt):
    calls['n'] += 1
    if calls['n'] <= 3: raise APIError(429)
    return {'ok': True}

res, delays = call_with_retry(flaky, rnd=random.Random(0))
print(f'成功（第 {calls["n"]} 次尝试），退避序列: {delays}')
assert res['ok'] and len(delays) == 3
assert delays[1] > delays[0] * 1.2, '退避应大致指数增长'

# 400 不重试：重试一万次也一样错
def bad_request(attempt): raise APIError(400)
try:
    call_with_retry(bad_request)
    raise RuntimeError('不该到这')
except APIError as e:
    assert e.status == 400
    print(f'✅ HTTP {e.status} 不重试（请求本身有问题，必须报出来）')

# Retry-After 优先
def rate_limited(attempt):
    if attempt == 0: raise APIError(429, retry_after=7.5)
    return {'ok': True}
_, d2 = call_with_retry(rate_limited, rnd=random.Random(0))
assert d2 == [7.5], f'应尊重 Retry-After，得到 {d2}'
print(f'✅ 尊重 Retry-After: {d2}')"""),
    code("""# 抖动为什么必需：模拟 200 个客户端同时遇到 429
def herd_peak(n_clients, jitter, bucket=0.25, attempts=3):
    '''统计重试时刻的分布：峰值越高说明惊群越严重。'''
    times = []
    for c in range(n_clients):
        rnd = random.Random(c); t = 0.0
        for a in range(attempts):
            t += backoff_delay(a, jitter=jitter, rnd=rnd)
            times.append(t)
    hist = {}
    for t in times:
        hist[round(t / bucket)] = hist.get(round(t / bucket), 0) + 1
    return max(hist.values()), len(times)

peak_no, tot = herd_peak(200, jitter=False)
peak_yes, _ = herd_peak(200, jitter=True)
print(f'200 客户端 × 3 次重试 = {tot} 次请求')
print(f'  无抖动: 单个 0.25s 窗口内峰值 {peak_no} 次请求')
print(f'  有抖动: 单个 0.25s 窗口内峰值 {peak_yes} 次请求')
assert peak_no > peak_yes * 2, '无抖动时所有客户端同步重试 -> 周期性洪峰'
print(f'\\n✅ 抖动把峰值降低 {peak_no/peak_yes:.1f}× —— 这是分布式系统里最便宜的一行代码。')"""),
    code("""class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate, self.cap, self.tokens, self.last = rate, float(capacity), float(capacity), 0.0
    def allow(self, now, cost=1.0):
        self.tokens = min(self.cap, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost; return True
        return False
    def refund(self, amount):
        self.tokens = min(self.cap, self.tokens + max(0.0, amount))

class RateLimitedClient:
    '''RPM + TPM 双限 + 预扣/结算 + 幂等缓存。'''
    def __init__(self, rpm, tpm, idem_window=300.0):
        self.rpm_b = TokenBucket(rpm / 60.0, rpm)
        self.tpm_b = TokenBucket(tpm / 60.0, tpm)
        self.idem, self.window = {}, idem_window
        self.stats = {'served': 0, 'throttled': 0, 'idem_hits': 0, 'tokens': 0}
    def call(self, now, est_tokens, actual_tokens=None, idem_key=None):
        if idem_key is not None and idem_key in self.idem:
            t0, resp = self.idem[idem_key]
            if now - t0 <= self.window:
                self.stats['idem_hits'] += 1
                return resp                     # 幂等命中：不重复消耗配额、不重复计费
        if not self.rpm_b.allow(now):
            self.stats['throttled'] += 1; return {'error': 429, 'reason': 'RPM'}
        if not self.tpm_b.allow(now, cost=est_tokens):
            self.rpm_b.refund(1); self.stats['throttled'] += 1
            return {'error': 429, 'reason': 'TPM'}
        used = est_tokens if actual_tokens is None else actual_tokens
        self.tpm_b.refund(est_tokens - used)     # 结算：退还多扣的
        self.stats['served'] += 1; self.stats['tokens'] += used
        resp = {'ok': True, 'usage': {'total_tokens': used}}
        if idem_key is not None: self.idem[idem_key] = (now, resp)
        return resp

def max_throughput(rpm, tpm, avg_tokens):
    return min(rpm, tpm // avg_tokens)

print(f"{'RPM':>6s} {'TPM':>8s} {'均token':>8s} {'RPM上限':>8s} {'TPM上限':>8s} {'实际瓶颈':>10s}")
for rpm, tpm, avg in [(60, 60_000, 500), (60, 60_000, 2000), (3500, 90_000, 1500)]:
    lim_r, lim_t = rpm, tpm // avg
    print(f'{rpm:>6d} {tpm:>8d} {avg:>8d} {lim_r:>8d} {lim_t:>8d} '
          f'{("RPM" if lim_r < lim_t else "TPM"):>10s}')
assert max_throughput(3500, 90_000, 1500) == 60, '看起来 RPM=3500，实际只能 60 请求/分'
print('\\n⚠️  「RPM=3500」看起来能每秒 58 个请求，实际 TPM 只允许 60 个/分钟 —— 差 58 倍。')
print('✅ 大多数时候真正的瓶颈是 **TPM 而不是 RPM**。')"""),
    code("""c = RateLimitedClient(rpm=60, tpm=60_000)
# 长生成请求：预扣 4000、实际只用 500 -> 结算退还
r1 = c.call(0.0, est_tokens=4000, actual_tokens=500, idem_key='req-1')
assert r1['ok'] and r1['usage']['total_tokens'] == 500
# 同一个幂等键重试：不重复消耗配额
before = dict(c.stats)
r2 = c.call(1.0, est_tokens=4000, actual_tokens=500, idem_key='req-1')
assert r2 is r1 or r2 == r1
assert c.stats['served'] == before['served'], '幂等命中不应再消耗配额'
assert c.stats['idem_hits'] == 1
print(f'幂等: 第二次调用命中缓存，served 仍为 {c.stats["served"]}，idem_hits={c.stats["idem_hits"]}')

# 打爆 TPM
c2 = RateLimitedClient(rpm=1000, tpm=6000)
oks = sum(1 for i in range(10) if c2.call(0.0, est_tokens=1000).get('ok'))
print(f'TPM=6000, 每请求 1000 token: 前 10 个请求放行 {oks} 个')
assert oks == 6, 'TPM 桶容量 6000 -> 只放行 6 个'
assert c2.stats['throttled'] == 4
print('✅ 双限 + 预扣结算 + 幂等 三件套工作正常')"""),
    md("""## 6 · 流式：增量拼接、usage 与断连"""),
    code("""def fake_stream(text, include_usage=False):
    '''模拟 OpenAI 流式响应。注意第一个 chunk 只有 role、content 为 None。'''
    yield {'choices': [{'delta': {'role': 'assistant'}}]}
    for ch in text:
        yield {'choices': [{'delta': {'content': ch}}]}
    yield {'choices': [{'delta': {}, 'finish_reason': 'stop'}]}
    if include_usage:
        yield {'choices': [], 'usage': {'prompt_tokens': 12, 'completion_tokens': len(text),
                                        'total_tokens': 12 + len(text)}}

def consume_stream(stream, cancel_after=None):
    '''正确的增量拼接：跳过 content 为 None 的 chunk；记录 usage；支持取消。'''
    parts, usage, finish, n = [], None, None, 0
    for chunk in stream:
        n += 1
        if chunk.get('usage'):
            usage = chunk['usage']
        for ch in chunk.get('choices', []):
            d = ch.get('delta', {})
            if d.get('content') is not None:      # ← 必须判 None，不能直接取
                parts.append(d['content'])
            if ch.get('finish_reason'):
                finish = ch['finish_reason']
        if cancel_after is not None and n >= cancel_after:
            return ''.join(parts), usage, 'cancelled', n
    return ''.join(parts), usage, finish, n

text, usage, finish, n = consume_stream(fake_stream('LoRA 很好'))
print(f'拼接结果: {text!r}, finish={finish}, chunks={n}')
print(f'usage: {usage}   ← 默认流式**不带 usage**！')
assert text == 'LoRA 很好' and finish == 'stop'
assert usage is None, '默认流式不返回 usage -> 无法回答「这次花了多少 token」'

text2, usage2, _, _ = consume_stream(fake_stream('LoRA 很好', include_usage=True))
assert usage2 is not None and usage2['completion_tokens'] == len('LoRA 很好')
print(f'\\n开了 stream_options={{"include_usage": True}} 后: usage={usage2} ✅')

# 断连要真正取消：否则服务端还在为你生成
t3, _, f3, n3 = consume_stream(fake_stream('这是一段很长的回答' * 5), cancel_after=6)
print(f'\\n提前取消: 只拿到 {len(t3)} 个字符（{n3} 个 chunk），finish={f3}')
assert f3 == 'cancelled' and n3 == 6
print('⚠️  客户端放弃后必须真正关闭连接（用 with / close()），')
print('   否则服务端还在为你生成 —— 既烧你的配额也烧服务端算力。')
print('✅ 三件事：判 None 再拼接、显式开 include_usage、断连要取消。')"""),
    md("""## 7 · 上下文预算：多轮对话会越来越紧

$$L_{avail}(t) = L_{model} - L_{sys} - \\sum_{i<t}(L_{user,i}+L_{assist,i}) - L_{reserve}$$"""),
    code("""def context_state(model_max, sys_tokens, history, reserve):
    used = sys_tokens + sum(history)
    return {'used': used, 'available': model_max - used - reserve,
            'fits': model_max - used - reserve > 0}

MODEL_MAX, SYS, RESERVE = 4096, 200, 512
history = []
print(f'model_max={MODEL_MAX}, system={SYS}, 生成预留={RESERVE}')
print(f"{'轮次':>4s} {'历史token':>10s} {'可用':>8s} {'状态':>8s}")
for turn in range(1, 12):
    history += [180, 320]                     # 每轮 user 180 + assistant 320
    s = context_state(MODEL_MAX, SYS, history, RESERVE)
    if turn % 2 == 1 or not s['fits']:
        print(f'{turn:>4d} {sum(history):>10d} {s["available"]:>8d} '
              f'{("✅" if s["fits"] else "❌ 超限"):>8s}')
    if not s['fits']: break
assert not context_state(MODEL_MAX, SYS, history, RESERVE)['fits'], '多轮后必然超限'

def sliding_window(history, model_max, sys_tokens, reserve, keep_turns=None):
    '''滑窗：从最近往前保留，直到装不下。返回保留的轮数。'''
    budget = model_max - sys_tokens - reserve
    kept, total = 0, 0
    for pair in reversed(range(0, len(history), 2)):
        cost = history[pair] + (history[pair + 1] if pair + 1 < len(history) else 0)
        if total + cost > budget: break
        total += cost; kept += 1
        if keep_turns and kept >= keep_turns: break
    return kept, total

kept, total = sliding_window(history, MODEL_MAX, SYS, RESERVE)
print(f'\\n滑窗策略: 共 {len(history)//2} 轮，只能保留最近 {kept} 轮（{total} token）')
assert kept < len(history) // 2, '滑窗必然丢弃早期轮次'
assert total <= MODEL_MAX - SYS - RESERVE
print('⚠️  代价：用户会发现「它忘了前面说的话」。')
print('✅ 四种策略：滑窗（丢信息）/ 摘要压缩（额外成本+失真）/ 检索（复杂，C11-C33）/ 硬失败（诚实）。')
print('   **无论选哪种，都必须先能算出这个数字** —— 最糟的是不算，然后被静默截断。')"""),
    md("""## ✏️ 练习 1：退避序列

实现 `retry_schedule(max_attempts, base, cap, retry_after=None, seed=0)`：
返回每次重试前的等待秒数列表（长度 `max_attempts-1`）。
若 `retry_after` 不为 None，则**全部**用它；否则用 `min(cap, base*2^k) × U(0.5,1.5)`。"""),
    code("""def retry_schedule(max_attempts, base, cap, retry_after=None, seed=0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s = retry_schedule(5, base=0.5, cap=30.0, seed=1)
assert len(s) == 4
assert all(0.25 <= d <= 30 * 1.5 for d in s), s
assert s[3] > s[0], '整体趋势应递增'
# cap 生效
s_cap = retry_schedule(12, base=1.0, cap=8.0, seed=2)
assert max(s_cap) <= 8.0 * 1.5 + 1e-9, f'不应超过 cap*1.5，得到 {max(s_cap)}'
# retry_after 优先
assert retry_schedule(4, 0.5, 30, retry_after=7.5) == [7.5, 7.5, 7.5]
# 同 seed 可复现
assert retry_schedule(5, 0.5, 30, seed=1) == retry_schedule(5, 0.5, 30, seed=1)
print('退避序列:', [round(x, 3) for x in s])
print('✅ 练习 1 通过：**抖动不是可选的** —— 它防惊群')"""),
    md("""## ✏️ 练习 2：双限吞吐上限

实现 `throughput_limits(rpm, tpm, avg_prompt_tokens, avg_completion_tokens)`：
返回 `{'rpm_limit':…, 'tpm_limit':…, 'bottleneck': 'RPM'|'TPM', 'requests_per_min': …}`。
注意 TPM 同时计入 prompt 与 completion。"""),
    code("""def throughput_limits(rpm, tpm, avg_prompt_tokens, avg_completion_tokens):
    # TODO: total = prompt + completion；tpm_limit = tpm // total
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r = throughput_limits(3500, 90_000, 1200, 300)
assert r['tpm_limit'] == 60 and r['bottleneck'] == 'TPM'
assert r['requests_per_min'] == 60
r2 = throughput_limits(60, 600_000, 100, 100)
assert r2['bottleneck'] == 'RPM' and r2['requests_per_min'] == 60
print(f'RPM=3500 TPM=90k, 1200+300 token: 瓶颈={r["bottleneck"]}, 实际 {r["requests_per_min"]} 请求/分')
print(f'RPM=60 TPM=600k, 100+100 token : 瓶颈={r2["bottleneck"]}, 实际 {r2["requests_per_min"]} 请求/分')
print('✅ 练习 2 通过：容量规划前先算清哪个维度先饱和')"""),
    md("""## ✏️ 练习 3：成本归因

实现 `cost_report(calls, price_per_1k_prompt, price_per_1k_completion)`：
`calls` 是 `[{'tag':…, 'prompt_tokens':…, 'completion_tokens':…, 'cached_prompt_tokens':…}, …]`。
缓存命中的 prompt token 按 **10%** 计价。返回 `{tag: 花费}`，外加 `'_total'` 键。"""),
    code("""def cost_report(calls, price_per_1k_prompt, price_per_1k_completion, cache_discount=0.1):
    # TODO: 每条：(未缓存prompt + 缓存prompt*cache_discount)/1000*price_p
    #             + completion/1000*price_c；按 tag 累加；加 '_total'
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
calls = [
    {'tag': 'chat',    'prompt_tokens': 1000, 'completion_tokens': 200, 'cached_prompt_tokens': 0},
    {'tag': 'chat',    'prompt_tokens': 1000, 'completion_tokens': 200, 'cached_prompt_tokens': 800},
    {'tag': 'summary', 'prompt_tokens': 5000, 'completion_tokens': 100, 'cached_prompt_tokens': 0},
]
rep = cost_report(calls, price_per_1k_prompt=0.5, price_per_1k_completion=1.5)
print({k: round(v, 5) for k, v in rep.items()})
assert '_total' in rep and abs(rep['_total'] - sum(v for k, v in rep.items() if k != '_total')) < 1e-9
# 第二条因缓存应比第一条便宜
c1 = (1000/1000)*0.5 + (200/1000)*1.5
c2 = ((200 + 800*0.1)/1000)*0.5 + (200/1000)*1.5
assert abs(rep['chat'] - (c1 + c2)) < 1e-9, f'缓存折扣算错: {rep["chat"]} vs {c1+c2}'
assert rep['summary'] > rep['chat'] / 2
print('✅ 练习 3 通过：**没有这份数据，你无法回答「哪个功能在烧钱」**')
print('   顺带一条最便宜的优化：把固定的系统提示放在 prompt 最前面 -> 命中前缀缓存')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def retry_schedule(max_attempts, base, cap, retry_after=None, seed=0):
    if retry_after is not None:
        return [retry_after] * (max_attempts - 1)
    r = random.Random(seed)
    return [min(cap, base * (2 ** k)) * r.uniform(0.5, 1.5) for k in range(max_attempts - 1)]"""),
    code("""# 练习 2 参考答案
def throughput_limits(rpm, tpm, avg_prompt_tokens, avg_completion_tokens):
    total = avg_prompt_tokens + avg_completion_tokens
    tpm_limit = tpm // total
    return {'rpm_limit': rpm, 'tpm_limit': tpm_limit,
            'bottleneck': 'RPM' if rpm <= tpm_limit else 'TPM',
            'requests_per_min': min(rpm, tpm_limit)}"""),
    code("""# 练习 3 参考答案
def cost_report(calls, price_per_1k_prompt, price_per_1k_completion, cache_discount=0.1):
    out = {}
    for c in calls:
        cached = c.get('cached_prompt_tokens', 0)
        fresh = c['prompt_tokens'] - cached
        cost = ((fresh + cached * cache_discount) / 1000) * price_per_1k_prompt \\
               + (c['completion_tokens'] / 1000) * price_per_1k_completion
        out[c['tag']] = out.get(c['tag'], 0.0) + cost
    out['_total'] = sum(out.values())
    return out"""),
    md("""---
## 🧪 真实 API 对照胶囊：一个生产可用的客户端骨架"""),
    code("""RECIPE = r'''
import os, time, random, hashlib, json
from openai import OpenAI, APIStatusError, APIConnectionError

client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"),   # 自建服务也用同一套
                api_key=os.environ["OPENAI_API_KEY"],
                timeout=60.0, max_retries=0)   # ← 关掉 SDK 重试，自己控制策略

RETRYABLE = {408, 409, 429, 500, 502, 503, 504}

def backoff(attempt, base=0.5, cap=30.0):
    return min(cap, base * 2 ** attempt) * random.uniform(0.5, 1.5)   # 抖动必需

def chat(messages, model="gpt-4o-mini", max_attempts=5,
         idem_key=None, stream=False, **kw):
    for attempt in range(max_attempts):
        try:
            extra = {}
            if idem_key:                       # ③ 幂等：重试不重复扣费
                extra["extra_headers"] = {"Idempotency-Key": idem_key}
            if stream:
                kw["stream_options"] = {"include_usage": True}   # ← 否则拿不到 usage
            return client.chat.completions.create(
                model=model, messages=messages, stream=stream, **kw, **extra)
        except APIStatusError as e:
            if e.status_code not in RETRYABLE or attempt == max_attempts - 1:
                raise                          # 400/401/404 立刻抛出，别重试
            ra = e.response.headers.get("retry-after")
            time.sleep(float(ra) if ra else backoff(attempt))    # 尊重 Retry-After
        except APIConnectionError:
            if attempt == max_attempts - 1: raise
            time.sleep(backoff(attempt))

def consume_stream(resp):
    # 正确的增量拼接：判 None、收集 usage
    parts, usage = [], None
    for chunk in resp:
        if getattr(chunk, "usage", None):
            usage = chunk.usage
        for ch in chunk.choices:
            if ch.delta.content is not None:   # ← 必须判 None
                parts.append(ch.delta.content)
    return "".join(parts), usage

# ── 结构化输出（不是 tool calling！没有函数要执行，只保证格式）──
SCHEMA = {"type": "json_schema", "json_schema": {
    "name": "verdict", "strict": True,
    "schema": {"type": "object",
               "properties": {"label": {"type": "string", "enum": ["ok", "violation"]},
                              "confidence": {"type": "number"}},
               "required": ["label", "confidence"], "additionalProperties": False}}}
r = chat([{"role": "user", "content": "审核这段话：……"}], response_format=SCHEMA)
verdict = json.loads(r.choices[0].message.content)   # schema 合法，但语义仍需校验

# ── 成本归因：每次调用都记下来（否则无法回答「哪个功能在烧钱」）──
def log_usage(tag, resp):
    u = resp.usage
    cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0)
    print(json.dumps({"tag": tag, "model": resp.model,
                      "prompt": u.prompt_tokens, "cached": cached,
                      "completion": u.completion_tokens}, ensure_ascii=False))
'''
print(RECIPE)
for c in ['max_retries=0', 'random.uniform(0.5, 1.5)', 'Idempotency-Key',
          'include_usage', 'is not None', 'json_schema', 'cached_tokens']:
    assert c in RECIPE, c
print('✅ 配方覆盖四层防护 + 流式 + 结构化输出 + 成本归因')"""),
    md("""### 小结
- **`prepare(dataloader)` 换掉 sampler**：`batch_size` 是每进程的，8 卡时有效 batch ×8。`accumulate()` 还会跳过中间步的梯度同步（省 7/8 通信）。
- **`gather_for_metrics` 而不是 `gather`**：分布式采样为整除会重复末尾样本，裸 gather 让指标有偏（「多卡与单卡略有不同」的真因）。
- **保存前 `unwrap_model`**：否则键名带 `module.` 前缀 → **全部 missing** → 模型等于随机初始化。
- **safetensors 不执行代码，pickle 会**（已用可运行的例子证明）；`trust_remote_code` 同理。**钉死 commit sha** 才可复现，用 `main` 会静默换模型。
- **客户端四层防护**：退避**必须加抖动**（防惊群，峰值降数倍）、**RPM+TPM 双限**（真正的瓶颈通常是 TPM）、幂等键、分层超时。
- **流式三件事**：判 `None` 再拼接、显式开 `include_usage`（默认没有 usage）、断连要真正取消。
- **上下文预算随轮数变紧**；四种策略各有代价，但**必须先能算出这个数字**。
- **记录每次调用的 token 与标签**——没有这份数据就无法回答「哪个功能在烧钱」。

🎓 **本课完结。** 你现在有了从「加载一个模型」到「训练、微调、分发、调用」的完整手艺，
以及每一层的坑清单与可复用的配方。
建议的下一站：**C48**（把服务真正部署上线）、**C39**（分布式训练的原理）、**C37**（实验追踪与生产生命周期）。"""),
]
