# 术语词典 · Glossary（工业研究工程实务）

> 按主题分组，每条 2–3 句释义。读框架文档、导出报错、GPU 日志或专利材料时遇到生词回这里查；英文术语保留原文。

## 图与追踪 · Graphs & Tracing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| eager execution | 动态图 / 即时执行 | Python 逐行执行，每个算子立刻算出结果。好调试，但无法整图优化、无法脱离 Python 部署。PyTorch 与 TF2 的默认模式。 |
| graph mode | 静态图 | Python 只是**构图脚本**，跑一遍产出一张图；之后执行的是图。可整图优化、可序列化、可脱离 Python。代价是调试困难与控制流被固化。 |
| tracing | 追踪 | 用**符号张量**（tracer）代替真实数组跑一遍 Python 函数，把每个算子记成图节点。`tf.function`/`jax.jit`/`torch.compile`/`torch.onnx.export` 的共同机制。 |
| tracer | 符号张量 | 追踪期代替真实张量的对象，只持有 (图, 节点 id, 形状, dtype)。JAX 的 tracer 在被当作具体值使用时**直接报错**（宁可报错也不静默固化）。 |
| retracing | 重追踪 | 输入签名变化导致重新追踪。**头号性能杀手**：追踪一次约等于跑几十到几百次前向。诊断技巧：在函数里放一个 Python 副作用，数它执行几次。 |
| cache key（签名） | 缓存键 | `(每个输入的 dtype, 形状, 所有 Python 参数的值)`。传 Python 标量而非 tensor 会让每个取值各占一张图。 |
| `input_signature` | 输入签名声明 | TF 里把可变维标成 `None`，让一张图接受任意形状。对应 `torch.compile(dynamic=True)` 与 ONNX 的动态轴。 |
| AutoGraph | 自动图改写 | TF 把一部分 Python 控制流自动改写成图算子（`if`→`tf.cond`）。**只在条件依赖 tensor 时改写**——「有时改写有时不改写」是 TF 最难懂的地方。 |
| graph break | 图打断 | `torch.compile` 遇到不支持的 Python 时静默回退 eager。不报错但性能损失大；用 `TORCH_LOGS=graph_breaks` 诊断。 |
| 构图时的量 vs 运行时的量 | static vs dynamic values | 静态图的第一性原理。构图时的量（Python int、静态形状）追踪时确定；运行时的量（tensor 值）只有执行图时才知道。**依赖后者的控制流必须用图算子表达**。 |
| Functional API | 函数式 API | Keras 构建「可被检查的数据结构」：定义时就知道拓扑与形状，所以能 `summary()`、能画图、能直接序列化。PyTorch 只有 subclassing，故导出必须靠追踪。 |
| MFU | 模型 FLOPs 利用率 | 实际达到的算力 ÷ 峰值算力。调好的单卡 40–55%；有数据瓶颈时可低至 5%。**双向可用**：正向估时长、反向判还有多少优化空间。 |

## 权重迁移 · Weight Porting

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| reshape vs transpose | 重解释 vs 换排列 | `reshape` 只重新解释同一块连续内存（元素顺序不变）；`transpose` 改变元素排列。两者常得到**相同形状但完全不同的内容**，而代码不报错。 |
| Conv 权重布局 | conv layout | PyTorch `(out, in, kH, kW)` ↔ TF `(kH, kW, in, out)`，需 `transpose(2,3,1,0)`。ConvTranspose 的 in/out 本身就是反的，更易错。 |
| 方阵陷阱 | square-matrix trap | `d_model→d_model` 的层（Transformer 的 q/k/v/o 投影）忘了转置时**形状检查完全无法区分**——模型会跑、结果全错。唯一可靠的防线是数值对拍。 |
| 门顺序 | gate order | PyTorch GRU 是 `[r, z, n]`、Keras 是 `[z, r, h]`（**前两个门反的**）；LSTM 各实现也不同。错了模型仍能跑、loss 仍能降，只有用**预训练权重**时才暴露。 |
| buffer vs parameter | 缓冲区 vs 参数 | BatchNorm 的 `running_mean`/`running_var` 是 buffer，遍历 `parameters()` 看不到。**漏掉它训练模式正常、一到 eval 就崩**——最难定位的一类迁移 bug。 |
| 逐层对拍 | layer-wise numeric check | 喂同一输入，按执行顺序比较每层激活，**在第一个失配处停下**（后面全错只是它的后果）。把「效果差 2 分」变成「第 7 层 eps 不对」。 |
| 全 1 / 阶梯探针 | ones / ramp probe | 五分钟排除所有布局错误：全 1 输入让维度错误表现为数量级差异；阶梯输入打破对称性以抓方阵的转置错误。 |
| 容差 | tolerance | fp32 单层 ~1e-6、96 层 ~1e-5；fp16 放宽两个数量级；int8 量化约 2/127。**太紧则假警报、太松则真错误被放过**。 |
| eps / momentum 默认值差异 | default mismatch | `keras.LayerNormalization` 的 eps 是 **1e-3**、PyTorch 是 1e-5（差 100 倍）；BatchNorm 的 momentum **语义相反**（torch 0.1 ⟺ keras 0.9）。都不报错。 |

## 导出与运行时 · Export & Runtime

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| ONNX | 开放神经网络交换格式 | 事实上的交换格式。四要素：静态拓扑、**opset 版本**、符号形状（动态轴）、内联权重（initializer）。 |
| opset version | 算子集版本 | 每个算子记录「自哪个 opset 起可用/语义变更」。**不是越新越好**——目标运行时可能只支持到某个版本。要先查上限再导出。 |
| dynamic axes | 动态轴 | 把会变的维度声明为符号（`"batch"`）而非常数。**不设就被写死**，「用 batch=1 导出、线上来 batch=8」是最常见的导出事故。 |
| shape inference | 形状推断 | 从输入形状推出每个中间张量的形状。`NonZero`/`Unique`/`masked_select` 的输出形状**依赖输入数值**，推断不出来。 |
| 静默回退 | silent fallback | TensorRT/CoreML/TFLite 遇到不支持的算子不报错，而是切子图交给别的后端（甚至 CPU）。**症状是「转了但没变快」**，要看分区日志而非端到端延迟。 |
| execution provider | 执行提供者 | ONNX Runtime 的后端插件（CUDA/TensorRT/CPU/DirectML），按优先级回退。用 `get_providers()` 确认实际用了哪个。 |
| engine（TensorRT） | 引擎 | TensorRT 构建产物。**与 GPU 型号与驱动绑定**——换卡要重建，构建要几分钟到几十分钟。直接影响镜像与冷启动策略。 |
| ANE | Apple 神经引擎 | 极省电极快，但只支持有限算子与精度。模型会「成功转换」却实际跑在 CPU/GPU 上——要看 Xcode 性能报告里每层的计算单元。 |
| 校准集 | calibration set | 静态 int8 量化用来统计激活范围的数据。**必须是线上分布的有代表性小样本**（几百条）；分布不对量化范围就是错的。 |
| 异常层 | outlier layer | 量化误差比其他层大一个数量级的层——通常因激活有长尾离群值。**一个离群值就能撑爆整层的量化范围**。 |
| 交付契约 | delivery contract | 明确写出「在什么输入范围、什么 dtype、什么容差下成立」。缺了它就会有关于「差 1e-4 算不算 bug」的无谓讨论。 |

## 真机 GPU · GPU Workflow

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 显存五项 | memory breakdown | 参数 + 梯度 + 优化器状态 + 激活 + 杂项。**每一项都能算**，所以 OOM 是算术题不是运气问题。 |
| 优化器状态 | optimizer states | AdamW 混合精度下 **12 字节/参数**（fp32 主权重 4 + m 4 + v 4）——**比参数本身还大**。8bit Adam 6B、SGD 4B。这是最大的一项。 |
| 激活显存 | activation memory | 常常是主导项。线性项随 `B×L` 增长；朴素注意力的矩阵随**序列长平方**增长（FlashAttention 把它变成线性）。 |
| 梯度检查点 | gradient checkpointing | 只存部分中间结果、反向时重算。激活显存大降，代价约 +30% 计算。**单卡上性价比最高的一招**。 |
| token-budget 分批 | token-budget batching | 「每批 8192 token」而不是「每批 32 条」。让每批 token 数有硬上界 → 显存有硬上界 → 不会突然 OOM，同时减少 padding 浪费。 |
| 缓存分配器 | caching allocator | PyTorch 保留已释放的显存块。**`nvidia-smi` 显示的占用高于真实占用**——要看 `memory_allocated()` 与 `max_memory_allocated()`。 |
| `expandable_segments` | 可扩展段 | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`，缓解碎片。免费的第一招。 |
| compute capability | 计算能力 | GPU 的架构版本（A100=8.0、H100=9.0、RTX4090=8.9）。二进制没编译对应的 `sm_XX` 时报 **`no kernel image is available`**——听起来像找不到文件，实际是「这个二进制不认识你的卡」。 |
| 四层版本链 | version chain | 硬件 → 驱动 → CUDA runtime → 框架 → 编译扩展。最脆弱的是编译扩展（绑定 torch×CUDA×Python×ABI 四元组）。**这条链无法靠 requirements.txt 复现**。 |
| `CUDA_LAUNCH_BLOCKING` | 同步执行 | **GPU 调试的第一招**。kernel 异步启动，报错时 Python 栈已跑到别处；设了它错误就出现在真正出问题的那一行。 |
| `nvidia-smi topo -m` | 拓扑查询 | 看卡间是 NVLink 还是 PCIe。NVLink 带宽是 PCIe 的 5–10 倍，直接决定多卡训练效率的上限。 |
| 利用率的波动模式 | utilization pattern | **数据瓶颈周期性掉到 0，计算瓶颈稳定在高位**。平均值一样但处方完全不同——要看 `dmon` 的时间序列。诊断顺序：数据 → 通信 → 计算。 |

## 研究产出与知识产权 · Output & IP

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| 新颖性 | novelty | 此前没有任何公开披露。**公开即丧失，且多数辖区不可逆**——论文、arXiv、博客、开源、公开演讲、公开 commit、客户 demo 都算。 |
| 非显而易见性 | non-obviousness | 对该领域普通技术人员不是显然的。「把 A 方法用到 B 任务」常被认为显而易见；**「非预期的效果」是最有力的论据**。 |
| 可专利主题 | subject-matter eligibility | 不能是抽象概念或数学公式本身。**纯算法难，「算法 + 具体技术改进」容易**——要把创新翻译成「技术问题 + 技术手段 + 技术效果」。 |
| 独立/从属权利要求 | independent / dependent claim | 独立要求最宽（限定越少范围越宽）；从属逐层收缩，作用是「独立要求被无效时还有它顶着」。 |
| 绕过分析 | design-around | 自问「竞争者绕过我的最小改动是什么」。若答案是「把 ReLU 换成 GELU」，说明权利要求过窄。 |
| 发明披露书 | invention disclosure | 你实际要写的东西（不是专利本身）。六节：问题 / 现有技术 / 方案 / 为何有效 / **变体** / **时间线与公开状态**。最后两节最易跳过也最关键。 |
| permissive license | 宽松许可 | MIT/BSD/Apache-2.0。保留声明即可用于闭源产品。Apache-2.0 还带专利授权条款。 |
| copyleft | 传染性许可 | GPL：**分发**衍生作品时必须同样开源。LGPL 是弱 copyleft（动态链接通常可以）。 |
| AGPL | 网络 copyleft | **「通过网络提供服务」即触发开源义务**——打破了「不分发就没义务」的直觉，而这正是所有 AI 服务的形态。SaaS 场景下最危险的一个。 |
| CC-BY-NC | 非商业许可 | 禁止商业使用。**大量数据集是这个许可**——训练商业模型即违约。 |
| 自定义模型许可 | custom model license | Llama 等的许可不是 OSI 认可的开源许可（用户数阈值、禁止改进竞品、可接受使用政策）。**必须逐条读**。 |
| 依赖树传染 | transitive license risk | 问题常藏在**二级依赖**里（某库自己是 MIT，但依赖一个 AGPL 的组件）。所以要遍历整棵树。 |
| 结论先行 | conclusion-first | 内部演示的第一张幻灯片就给结论。听众可能只听前五分钟。标题应是**断言**（「显存降 40%」）而非章节名（「结果」）。 |
| ask | 明确请求 | 演示结尾必须说清「谁 在 什么时候 做 什么决定 / 需要什么资源」。**把演示的成功定义为「产生了一个决定」而非「讲清楚了」**。 |
