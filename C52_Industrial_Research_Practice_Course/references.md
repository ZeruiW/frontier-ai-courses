# 参考清单 · References（工业研究工程实务）

> 本课的参考大量是**官方文档而非论文**——因为这些是工程问题，权威定义在文档里。
> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C36** 讲 GPU 与 kernel 原理；**C38** 讲框架内部（autograd 与编译）；
> **C39** 讲分布式训练；**C24** 讲推理引擎内部；**C27** 讲量化算法；**C48** 讲容器化与云上部署；
> **C50** 讲 HuggingFace 生态。**本课聚焦「跨框架、跨运行时、跨环境地把东西交出去」这一段。**

## TensorFlow / Keras 与追踪语义 · Tracing Semantics
- ★ **TensorFlow 指南 _Better performance with tf.function_** — **本课模块 01 第三节的一手来源**。重追踪的准确规则、`input_signature` 的用法、以及诊断方法。重点读「Rules of tracing」与「Retracing」两节。
- ★ **TensorFlow 指南 _Introduction to graphs and tf.function_** — 静态图与 Python 副作用的关系讲得最清楚的一篇。读完就理解了「Python 只在追踪时执行一次」的全部后果。
- ★ **JAX 文档 _JAX — The Sharp Bits_** — **强烈推荐即使你不用 JAX 也读一遍**。它把追踪的坑（纯函数要求、tracer 不能做 Python 判断、随机数要显式传 key）列得最清楚，因为 JAX「宁可报错也不静默固化」。
- **JAX 文档 _How to think in JAX_** — 三种范式差别的最佳入门（状态放哪、图从哪来）。
- **TensorFlow 指南 _The Keras functional API_** — Functional 与 Subclassing 的差别，以及为什么前者「是可被检查的数据结构」。
- **PyTorch 文档 _torch.compile_ 与 _TorchDynamo_** — 对照阅读会发现与 `tf.function` 语义高度同构。重点看 graph break 的诊断（`TORCH_LOGS`）与 `dynamic=True`。
- **Abadi et al. 2016, _TensorFlow: A System for Large-Scale Machine Learning_** — 数据流图这个设计的原始论证。历史价值大于实用价值，但能解释 TF 为什么长成这样。
- **Bradbury et al. 2018, _JAX: composable transformations of Python+NumPy programs_** — 可组合函数变换（`jit`/`grad`/`vmap`/`pmap`）的设计出处。

## 权重迁移与数值等价 · Porting
- ★ **PyTorch 文档中 `nn.Linear` / `nn.Conv2d` / `nn.GRU` / `nn.LSTM` 的 _Shape_ 与 _Variables_ 小节** — **权重形状与门顺序的权威定义**。做迁移时这几页要开着。特别注意 `nn.Linear` 计算的是 `y = xWᵀ + b`（所以存 `(out, in)`）。
- ★ **Keras 对应层的文档（`Dense` / `Conv2D` / `GRU` / `LayerNormalization` / `BatchNormalization`）** — 与上一条对读。**注意 `LayerNormalization` 的默认 epsilon 是 1e-3，`BatchNormalization` 的 momentum 语义与 PyTorch 相反**。
- ★ **HuggingFace `transformers` 里任意一个 `convert_*_original_checkpoint_to_pytorch.py`** — **读一遍真实的迁移脚本，胜过读十篇教程**。重点看它怎么做命名映射、怎么逐项断言、怎么处理权重共享（tied embeddings）。
- **cuDNN 文档中 RNN 的权重布局说明** — PyTorch 的门顺序源自它。理解「为什么门顺序是这个」而不只是「它是这个」。
- **NumPy 文档 _Indexing on ndarrays_ 与 `reshape` / `transpose` 的说明** — 「重新解释内存」与「改变排列」的区别，本课模块 02 第一节的基础。

## 导出与推理运行时 · Export & Runtime
- ★ **ONNX 官方 _Operators_ 文档** — 每个算子的「since version」与语义变更。**兼容性问题的一手来源**，查 opset 就查这里。
- ★ **ONNX _IR specification_** — 模型结构（graph / node / initializer / opset_import）与符号形状的定义。一页纸能读完，值得读。
- ★ **PyTorch 文档 _torch.onnx_，尤其 _Limitations_ 与 _FAQ_ 两节** — 把追踪的坑（控制流固化、形状写死、不支持的算子）列得很清楚。**导出前应该先读这两节**。也关注新的 `torch.export`/Dynamo 导出路径。
- ★ **NVIDIA _TensorRT Developer Guide_** — 重点看 layer fusion、INT8 calibration、以及 **engine 与硬件绑定**的说明（后者影响镜像与冷启动策略）。
- **ONNX Runtime 文档 _Execution Providers_ 与 _Performance Tuning_** — provider 的优先级与回退规则；怎么确认实际用了哪个后端。
- **Apple _Core ML Tools_ 文档** — ANE 支持的算子与精度约束，以及怎么在 Xcode 里看每层实际跑在哪个计算单元（诊断静默回退）。
- **TensorFlow Lite 文档 _Operator compatibility_ 与 _Delegates_** — 算子集最受限的运行时，也是 delegate 回退机制的好例子。
- **Jacob et al. 2018, _Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference_** — 训练后量化与量化感知训练的经典。量化的算法侧在 C27 详读，这里只需要它的误差量级作为容差依据。

## 真机 GPU 工作流 · GPU
- ★ **NVIDIA _CUDA Compatibility_ 指南** — **驱动与 runtime 的版本规则的权威来源**。本课模块 04 的版本矩阵出自这里。也讲清了 forward compatibility 的适用条件。
- ★ **`nvidia-smi` 手册** — `dmon`（时间序列监控，诊断数据瓶颈的关键）与 `topo -m`（卡间拓扑）两个子命令值得精读。多数人只用了它 10% 的功能。
- ★ **PyTorch 文档 _CUDA semantics_** — 异步执行与 `CUDA_LAUNCH_BLOCKING`。**理解「为什么报错的栈总是无关的」就靠这一页**。
- ★ **PyTorch 文档 _Memory management_** — 缓存分配器的行为、`expandable_segments`、以及为什么 `nvidia-smi` 的数字高于 `memory_allocated()`。
- ★ **Korthikanti et al. 2022, _Reducing Activation Recomputation in Large Transformer Models_** — **激活显存的精确建模**，本课模块 04 公式的来源。也是选择性重算这一思路的出处。
- ★ **Chowdhery et al. 2022, _PaLM: Scaling Language Modeling with Pathways_** — **MFU 这个指标的常用出处**（§5）。注意各家对 MFU 的口径不完全一致，跨论文比较前要先确认。
- **PyTorch 文档 _PyTorch Profiler_ 与 _torch.profiler_** — 从 kernel 时间分布定位计算瓶颈。配合 `record_shapes` 与 `profile_memory` 用。
- **Dao et al. 2022, _FlashAttention_** — 为什么注意力的激活显存能从平方变成线性。算法细节在 C36，这里只需要它对显存账本的影响。
- **Rajbhandari et al. 2020, _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_** — 优化器状态/梯度/参数分片。OOM 诊断树第 ⑦ 步的原理（C39 详读）。
- **Dettmers et al. 2022, _8-bit Optimizers via Block-wise Quantization_** — 8bit Adam 把优化器状态从 12N 降到 ~6N 的做法。诊断树第 ⑤ 步。

## 研究产出与知识产权 · Output & IP
> ⚠️ **以下均为工程视角的参考，不构成法律意见。** 真实判断请交给法务/IP 部门或执业律师。

- ★ **USPTO _Subject Matter Eligibility_ 指南（含 AI 相关示例）** — **理解「算法 + 技术效果」为什么重要的最直接材料**。它的示例部分把「什么样的软件权利要求能通过」讲得很具体。
- ★ **EPO _Guidelines for Examination_, G-II 3.3（计算机实现发明）** — 欧洲标准，与美国不同（更强调「技术特征」）。**多辖区申请时两边都要看**。
- ★ **choosealicense.com 与 SPDX 许可清单** — 日常查许可的两个入口。前者给决策建议、后者给规范标识符（工具链认这个）。
- ★ **GNU _License Compatibility and Relicensing_ 页面** — copyleft 的传染规则、GPL 与 AGPL 的差别、以及各许可之间的兼容性。**AGPL 的网络触发条款在这里说得最清楚**。
- **OSI _Open Source AI Definition_** — 理解「开源模型」这个词为什么已经失去精确性，以及社区试图怎么收敛。
- **各主流模型许可原文（Llama Community License、Gemma Terms of Use 等）** — **必须逐条读而不是靠印象**。用户数阈值、禁止改进竞品、可接受使用政策都写在里面。
- ★ **Barbara Minto, _The Pyramid Principle_** — 「结论先行」的出处。本课模块 05 的内部演示模板基于它。读第一部分就够。
- **Simon Peyton Jones, _How to Give a Great Research Talk_** — 学术演讲的经典。**注意本课讲的内部演示模板与它不同**（目标不同），但两者都值得会。
- **各会议的 artifact evaluation 与 reproducibility checklist（NeurIPS / ACL / MLSys）** — 了解「工业界论文在不能开源数据的前提下怎么提供可信的可复现性」这个现实张力。
