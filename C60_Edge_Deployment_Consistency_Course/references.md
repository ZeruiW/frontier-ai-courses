# 参考清单 · References（车端部署与训练-部署一致性）

> 分主题列出。**★ = 必读**（读完这些你能覆盖本课 80% 的内容与绝大多数部署类面试提问）。
> 每条注明**它解决什么问题**，以及要重点看哪一节——这门课的参考里**官方文档的比重远高于论文**，
> 因为一致性与部署是工程问题，权威定义写在文档里而不是论文里。
>
> 与相邻课程的分工：**C27** 讲量化算法本身；**C52** 讲 ONNX 导出与跨框架迁移的通用坑；
> **C24** 讲推理引擎内部实现；**C36** 讲 GPU kernel 与访存；**C53** 讲延迟-精度选型；
> **C61** 讲实验设计与面试实务。**本课聚焦「从训练好的权重到车上跑对且跑快」这一段。**

---

## 一 · 一致性方法论与对拍工具 · Consistency & Diffing

- ★ **NVIDIA `polygraphy` 官方文档与示例（TensorRT OSS 仓库 `tools/polygraphy`）** —
  解决「怎么系统性地对拍」。它是本课方法论的**官方实现**：
  `polygraphy run model.onnx --trt --onnxrt --atol 1e-3 --rtol 1e-3` 一条命令同时跑两个后端并逐输出比对；
  `polygraphy debug reduce` 能**自动把出问题的图缩小到最小复现子图**——这个功能被严重低估。
  **重点读 `examples/cli/debug/` 下的两个例子**，读完你会重新设计自己的排查流程。
- ★ **NVIDIA _TensorRT Developer Guide_ 的 "Troubleshooting" 与 "Working with Dynamic Shapes" 两章** —
  解决「构建成功但结果不对 / 不快」。前者列出了官方认可的排查顺序，后者讲清了 profile 的语义。
  **这两章是本课模块 00 与 02 排查树的一手来源。**
- ★ **MMDeploy 官方文档（OpenMMLab）** — 解决「训练框架与部署框架之间的语义对齐」这个具体工程问题。
  它的 **"模型转换后精度不一致" 与 "支持的算子与自定义算子" 两节是中文材料里质量最高的**，
  且它的 `tools/test.py` 提供了「用部署后的 engine 直接跑 mAP」的完整链路——
  **这正是本课主张的「端到端对拍」的现成实现**。
- **PyTorch 文档 _Reproducibility_ 与 _Deterministic algorithms_** —
  解决「为什么同样的输入两次结果不同」。讲清了 cuDNN benchmark 模式、原子加、
  `torch.use_deterministic_algorithms` 的作用范围与代价。**做严格对拍前必须先把不确定性关掉。**
- **NVIDIA _CUDA C++ Programming Guide_ 的浮点数附录（"Floating Point and IEEE 754"）** —
  解决「为什么 GPU 和 CPU 算出来差 1e-6」。讲清了 FMA（融合乘加）与不同求和顺序带来的差异。
  **理解它才能给出合理的容差，而不是把正常的浮点差异当 bug 追。**
- **Google _"How to Debug Machine Learning Models"_ 与各家的 ML 测试规范（如 _The ML Test Score_, Breck et al. 2017）** —
  解决「怎么把一次性排查变成常驻的门禁」。**本课的验收清单思想来自这一类材料**；
  `The ML Test Score` 的 "Infrastructure Tests" 一节尤其贴近本课主题。

---

## 二 · 预处理、插值与图像管线 · Preprocessing & Interpolation

- ★ **Parmar, Zhang & Zhu 2022 (CVPR), _On Aliased Resizing and Surprising Subtleties in GAN Evaluation_** —
  **本课模块 01 最重要的一篇论文**。它系统地证明了 PIL / OpenCV / PyTorch / TensorFlow 的 resize
  **给出互不相同的结果**，根因是抗锯齿低通滤波做与不做、以及坐标映射约定不同；
  并且证明了这个差异足以改变 FID 这种指标好几个点。
  **虽然它讲的是 GAN 评测，但结论对检测部署完全适用，而且它给了可复现的对照代码**（`clean-fid`）。
  面试里能引用这篇会显得非常"真的踩过坑"。
- ★ **ONNX `Resize` 算子规范（Operators.md 中 Resize 一节，opset 10 / 11 / 13 / 18 逐版本对照）** —
  解决「align_corners 到底是什么」。它把坐标变换显式化成
  `coordinate_transformation_mode` 的五种取值（`half_pixel` / `pytorch_half_pixel` /
  `align_corners` / `asymmetric` / `tf_crop_and_resize`），并给出**每种的精确公式**。
  **导出后一定要打开 ONNX 图确认这个属性的实际取值**——这是本课模块 02 的必查项。
- ★ **OpenCV 文档 `cv::resize` 与 `InterpolationFlags`** —
  解决「缩小图像该用哪个插值」。**必须记住的一句话写在文档里**：
  "To shrink an image, it will generally look best with `INTER_AREA` interpolation"。
  而 `cv::resize` 的**默认值是 `INTER_LINEAR`** ——默认值与推荐值不一致，这就是坑的来源。
- ★ **PyTorch 文档 `torch.nn.functional.interpolate` 的 `align_corners` 说明与配图** —
  官方给的那张对比图是理解 `align_corners` 最快的路径（**一分钟就能看懂两种映射的区别**）。
  同时注意 `torchvision.transforms.v2.Resize` 的 `antialias` 默认值**在版本间变过**，
  这是跨版本掉点的高频原因。
- **Pillow 文档 _Concepts: Filters_ 与 `Image.resize`** —
  PIL 的 `BILINEAR` 自带抗锯齿（等价于带支撑域缩放的重采样），
  **所以它和 OpenCV 的 `INTER_LINEAR` 结果差异最大**。理解这一点就理解了为什么"换个库读图"会掉点。
- **Ultralytics YOLO 仓库 `utils/augmentations.py` 中的 `letterbox` 函数（以及 `utils/general.py` 的 `scale_boxes`）** —
  **letterbox 与它的逆变换的事实标准实现**。逐行读一遍，特别注意：
  `auto`（是否只 pad 到 stride 倍数）、`scaleFill`、`scaleup`（是否允许放大）三个开关，
  以及 `dw/2, dh/2` 的居中 padding 与 `round(... - 0.1)` 的取整细节——
  **C++ 侧重写时漏掉任意一条都会造成不一致**。
- **ISP 与相机管线：NVIDIA _Jetson Multimedia API_ / `libargus` 文档，以及任一款相机的 ISP 调校说明** —
  解决「为什么车上的图和训练集的图不一样」。重点理解 ISP 的**降噪与锐化**对远处小目标纹理的影响，
  以及 NV12 / YUV 到 RGB 的转换标准（BT.601 vs BT.709、full vs limited range）。
  **这类域差无法靠改代码消除，只能靠用车端采集的数据训练——分清它与一致性 bug 是本课模块 01 的落点之一。**
- **色彩空间转换标准：ITU-R BT.601 与 BT.709 建议书** — 解决「NV12 转 RGB 用哪套系数」。
  不需要精读，**知道有两套系数、两种量程、四种组合，并且在代码里显式写出用的是哪一种**就够了。

---

## 三 · ONNX 与模型导出 · ONNX & Export

- ★ **ONNX 官方 _Operators_ 文档（`docs/Operators.md`）** — 解决「这个算子在哪个 opset 可用、语义变没变」。
  **兼容性问题的一手来源**；每个算子都标了 "since version"，且给出精确的数学定义。
  查 `Resize` / `NonMaxSuppression` / `QuantizeLinear` / `TopK` 这四个就够覆盖本课的绝大部分需求。
- ★ **ONNX _IR specification_（`docs/IR.md`）** — 解决「ONNX 文件里到底有什么」。
  graph / node / initializer / opset_import / value_info 的定义，加上**符号形状（dynamic axes）的表达方式**。
  一页纸能读完，**读完你就能自己写图检查脚本**。
- ★ **PyTorch 文档 _torch.onnx_，重点读 _Limitations_、_FAQ_ 与 `dynamo_export` / `torch.export` 部分** —
  解决「导出为什么会静默地导错」。**控制流被固化、shape 被写死、不支持的算子**三类问题讲得最清楚。
  新的 Dynamo 导出路径与旧的 TorchScript 追踪路径行为不同，**迁移时要重新对拍**。
  导出的通用坑在 **C52** 已详讲，本课只需要它的结论作为模块 02 的入口。
- ★ **`onnx-simplifier` 与 **NVIDIA `onnx-graphsurgeon`** 的文档与示例** —
  解决「导出的图里全是 Shape-Gather-Concat 小节点，融合不了」。
  前者做常量折叠与冗余消除（**常常是融合失败的直接解药**），
  后者用来做外科手术式的图编辑（改 Resize 属性、插 EfficientNMS 节点、删多余 Cast）。
  **模块 02 与 04 的工程胶囊都基于它们。**
- **ONNX Runtime 文档 _Execution Providers_，尤其 _TensorRT Execution Provider_ 一节** —
  解决「静默回退怎么发现」。讲清了子图分区规则、fallback 顺序、以及
  `trt_dump_subgraphs` 之类的诊断开关。**"看分区数而不是看延迟"这条判据就出自这里。**
- **ONNX Runtime 的 `onnxruntime.InferenceSession` CPU provider** —
  它不是"另一个后端"，而是本课默认的**黄金基准**：
  语义严格按 ONNX 规范实现、确定性好、CPU 可跑。**任何"TRT 结果不对"的排查都应该先和它比。**

---

## 四 · TensorRT 与编译优化 · TensorRT & Compilation

- ★ **NVIDIA _TensorRT Developer Guide_ — "How TensorRT Works" 中的 **Layer Fusion** 一节** —
  解决「引擎到底做了什么优化、什么会阻止优化」。**必读点**：
  纵向融合（Conv+Bias+激活）与横向融合（同源同参的多分支）的适用条件、
  以及为什么中间插一个 reshape 或让输出被多处消费就会阻断融合。
  **构建时加 `--verbose` 看融合后的层名（层名是拼接而成的），是判断融合有没有发生的最直接方法。**
- ★ **NVIDIA _TensorRT Developer Guide_ — **"Working with INT8"** / "Post-Training Quantization Using Calibration" 一节** —
  解决「TensorRT 的 INT8 到底怎么工作」。**必读点**：三种校准器
  （`IInt8EntropyCalibrator2`（默认）、`IInt8MinMaxCalibrator`、`IInt8LegacyCalibrator`）的差异、
  calibration cache 的格式与复用规则、**显式量化（Q/DQ）与隐式量化的区别**，
  以及层精度约束（`setPrecision` / `OBEY_PRECISION_CONSTRAINTS`）怎么实现混合精度。
  **这一节 + 下面的 Migacz 白皮书，构成本课模块 03 的全部理论基础。**
- ★ **NVIDIA _TensorRT Best Practices / Performance Guide_** —
  解决「构建配置该怎么设」。workspace 上限对 tactic 可选范围的影响、timing cache 的用法、
  多 profile 的取舍、以及**为什么 engine 与硬件绑定**（换卡必须重建）。
  **车端多硬件平台的组合爆炸问题，这里给了官方口径。**
- ★ **`trtexec` 官方文档与完整参数表** — 解决「怎么在没有写一行代码前就拿到数字」。
  **必须掌握的组合**：`--fp16` / `--int8` / `--best`、`--shapes` 与 `--minShapes/--optShapes/--maxShapes`、
  `--dumpProfile --separateProfileRun`（逐层耗时）、`--verbose`（看融合与 tactic）、
  `--warmUp --duration --iterations`（测量控制）、`--timingCacheFile`。
  **注意它报的延迟默认不含预处理与后处理**，直接引用会低估端到端延迟。
- ★ **NVIDIA TensorRT OSS 仓库（`NVIDIA/TensorRT`），尤其 `plugin/efficientNMSPlugin/`** —
  解决「后处理怎么搬进 engine」。**读 `efficientNMSPlugin` 的 README 与参数结构体**：
  它对输入布局、score 是否已激活、是否 class-wise、坐标格式都有硬性约定，
  **接错会静默给出空结果**——这也是本课模块 04 强调"接完必须端到端对拍"的原因。
  同时 `samples/` 目录下的 `sampleINT8` / `sampleDynamicReshape` 是最好的入门代码。
- **NVIDIA _TensorRT_ 的 plugin 开发文档（`IPluginV2DynamicExt` / `IPluginV3`）** —
  解决「什么时候不得不写 plugin、写了要负责什么」。
  **重点不是怎么写，而是理解代价**：你要自己实现多精度版本、自己保证跨平台一致、自己维护版本升级。
  **先试四条更便宜的路**（换等价算子、升 opset/TRT、拆成支持的组合、挪到 CPU 后处理）。
- **NVIDIA _DeepStream SDK_ 文档（`nvinfer` / `nvinferserver` 插件配置）** —
  解决「真实的车端/边缘推理管线长什么样」。它的配置文件把预处理参数
  （`net-scale-factor`、`offsets`、`model-color-format`、`maintain-aspect-ratio`、`symmetric-padding`）
  **全部显式化了**——**这份配置本身就是一张"预处理一致性检查表"，非常值得照抄进自己的项目**。
- **NVIDIA Jetson / DRIVE 平台文档中的 **DLA** 章节** — 解决「车端怎么分配算力」。
  DLA 支持的层与精度有限，不支持的层会回落 GPU；**理解这个边界才能做合理的任务划分**。

---

## 五 · 量化理论与校准 · Quantization & Calibration

- ★ **Migacz 2017 (NVIDIA GTC), _8-bit Inference with TensorRT_（常被称为"NVIDIA INT8 校准白皮书"）** —
  **本课模块 03 的一手来源，必读**。它回答了三个问题：
  ① 为什么直接取 min/max 不行（离群值把有效范围撑爆）；
  ② **怎么用 KL 散度定义"最优截断阈值"**——把量化看成用低分辨率分布 Q 近似原分布 P，
  最小化 `KL(P‖Q)`；③ 完整的实现伪代码（2048 bin 直方图、从 128 到 2048 逐个候选阈值、
  尾部质量并入最后一个 bin、量化再展开回来算 KL）。
  **notebook 里从零实现的熵校准器就是照着这份伪代码写的**，逐行对照着读收获最大。
- ★ **Krishnamoorthi 2018, _Quantizing Deep Convolutional Networks for Efficient Inference: A Whitepaper_ (Google)** —
  **量化实务最全面的一份综述**，也是"per-channel 权重量化"这条建议的权威出处。
  **必读点**：§3 的 per-tensor vs per-channel 对比实验（**per-channel 权重量化几乎零成本地救回大部分掉点**）、
  §4 的 PTQ 与 QAT 的精度对照表、以及它给出的**明确的实践建议清单**。
  如果只读一篇量化论文，读这篇。
- ★ **Jacob et al. 2018 (CVPR), _Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference_** —
  解决「怎么让整个推理过程只用整数算术」。**必读 §2 的量化方案推导**：
  `r = S(q - Z)` 这个定义、以及把它代进矩阵乘后**zero-point 会产生的交叉项**——
  理解这个交叉项，就理解了为什么硬件普遍偏好**对称量化**（Z=0 时交叉项消失）。
  §2.3 关于 BN 折叠与量化的交互也直接对应本课模块 02 的 Conv+BN 融合。
- ★ **Nagel et al. 2021 (Qualcomm), _A White Paper on Neural Network Quantization_** —
  比 Krishnamoorthi 更新、更系统的一份。**必读它的"PTQ pipeline"流程图**：
  cross-layer equalization → bias correction → AdaRound → 校准，一步步给出何时用什么。
  **本课模块 03 的"量化掉点排查决策树"与它高度同构**，可以互为对照。
- **Nagel et al. 2019 (ICCV), _Data-Free Quantization Through Weight Equalization and Bias Correction_** —
  解决「不同通道的权重范围差几十倍导致 per-tensor 量化失效」，用**跨层均衡**把范围拉平。
  在**只有权重、拿不到数据**的场景（供应商给的模型）是唯一可用的手段。
- **Nagel et al. 2020 (ICML), _Up or Down? Adaptive Rounding for Post-Training Quantization (AdaRound)_** —
  解决「四舍五入不是最优的取整方式」。用少量无标注数据学一个逐权重的取整方向。
  **是 PTQ 与 QAT 之间的中间档**：比 PTQ 好、比 QAT 便宜得多。掉点在 1 mAP 左右时值得先试它再考虑 QAT。
- ★ **Choi et al. 2018, _PACT: Parameterized Clipping Activation for Quantized Neural Networks_** —
  解决「截断阈值该由谁决定」：把它变成一个**可训练参数**，让梯度告诉你截在哪。
  **它把"校准是启发式"这件事变成了"截断是可学的"**，是 QAT 精度的主要来源之一。读 §3 即可。
- ★ **Esser et al. 2020 (ICLR), _Learned Step Size Quantization (LSQ)_** —
  PACT 的进一步：直接对**量化步长 scale** 求梯度（给出了 STE 之外的一个更合理的梯度估计）。
  **当前 QAT 的事实标准之一**；理解它就理解了 QAT 相对 PTQ 到底多学了什么。
- ★ **Xiao et al. 2023 (ICML), _SmoothQuant: Accurate and Efficient Post-Training Quantization for LLMs_** —
  解决「激活里有极端离群通道，怎么量化都掉点」。做法优雅：
  **把难度从激活"迁移"一部分到权重**（激活除以 s、权重乘以 s，数学等价）。
  **虽然出自 LLM，但对含 transformer encoder 的检测器（RT-DETR 系）同样适用**，
  是本课模块 03 讲"离群值是量化困难的唯一根源"时的最佳收尾材料。
- **Dong et al. 2019/2020, _HAWQ / HAWQ-V2: Hessian AWare Quantization_** —
  解决「怎么自动决定哪些层该保高精度」：用 Hessian 的迹作为层敏感度的度量。
  **本课模块 03 的敏感层分析用的是更便宜的代理指标（逐层量化 + SQNR / 小验证集），
  但 HAWQ 给了"敏感度该怎么定义"的理论版本**，面试里能提一句会加分。
- **NVIDIA `pytorch-quantization` 工具包 与 **TensorRT Model Optimizer** 的文档** —
  解决「怎么在 PyTorch 里插 Q/DQ 并导出成 TensorRT 认的显式量化 ONNX」。
  **这是 QAT 上车的标准链路**；它的 `calib` 模块里就有 max / entropy / percentile / mse 四种校准器的实现，
  可以直接和 notebook 里手写的版本对照。
- **Wu et al. 2020 (NVIDIA), _Integer Quantization for Deep Learning Inference: Principles and Empirical Evaluation_** —
  解决「各种量化选择在真实网络上到底差多少」。**大量的对照实验表**，
  结论直接可用：per-channel 权重 + per-tensor 激活 + 熵/百分位校准，对大多数 CNN 已经够了。

---

## 六 · 后处理、NMS 与坐标 · Post-processing

- ★ **`torchvision.ops.nms` / `batched_nms` 的源码与文档** —
  解决「参考实现到底怎么写的」。**`batched_nms` 的"给每类加一个大偏移"技巧就在这几行里**，
  注意它对偏移量的选取（基于坐标最大值），**偏移不够大时不同类会互相抑制**。
  这是 C++ 侧重写时最容易漏的一条。
- ★ **ONNX `NonMaxSuppression` 算子规范** — 解决「导出到 ONNX 之后 NMS 的语义是什么」。
  它的输入是 `boxes(1,num,4)` + `scores(1,cls,num)`，**输出是索引三元组而不是框**，
  且**它是 class-wise 的**。理解这个签名，才能理解为什么很多导出脚本要在后面接一堆 Gather。
- ★ **Detectron2 关于**框坐标约定**的说明（以及它相对 Detectron 移除 `+1` 的变更记录）** —
  解决「`x2-x1` 还是 `x2-x1+1`」这个历史遗留问题。
  **Detectron2 明确采用连续坐标（不加 1）**，而大量老代码与部分 C++ 实现仍在用 +1。
  **对 8 像素的小框，两种约定的面积差 27%**，足以改变 NMS 的抑制结果与 IoU 匹配结果。
- ★ **`pycocotools` 的 `COCOeval` 源码（尤其 `computeIoU` 与 `accumulate`）** —
  解决「评测端到底怎么算的」。**如果你的部署端和评测端对框的约定不同，
  那你测出来的 mAP 描述的是一个不存在的系统**。读一遍它对 area range、maxDets、
  IoU 阈值序列的处理，是做可信评测的前提。
- **Bodla et al. 2017 (ICCV), _Soft-NMS: Improving Object Detection With One Line of Code_** —
  解决密集遮挡下 NMS 误删真目标。**部署视角的关键结论是：它增加保留框数**，
  下游负担与延迟都会上升，而且**两边实现的衰减函数（线性 vs 高斯）不同就是又一个不一致源**。
- **Ultralytics `utils/ops.py` 的 `non_max_suppression` 与 `scale_boxes`** —
  **事实上最常被移植到 C++ 的两个函数**。逐行读，特别注意：
  多标签模式、`max_det` 与 `max_nms` 的两级截断、agnostic 开关、
  以及 `scale_boxes` 里 pad 的计算方式（**它假设 letterbox 是居中的**，
  如果你的 C++ 侧用了左上对齐，这里就必须跟着改）。
- **各推理框架的后处理示例（TensorRT `samples/python/yolov3_onnx`、DeepStream 的 `nvdsparsebbox_*` 自定义解析函数）** —
  解决「C++ 侧的后处理长什么样」。DeepStream 的 bbox parser 是一个很好的模板：
  **它把"从原始输出张量到框"的每一步都摊开写了**，适合作为对拍的参照物。

---

## 七 · 性能剖析、roofline 与延迟工程 · Profiling & Latency

- ★ **Williams, Waterman & Patterson 2009 (CACM), _Roofline: An Insightful Visual Performance Model for Multicore Architectures_** —
  **本课模块 05 瓶颈判定的理论基础**。核心只有一个不等式：
  可达性能 = min(峰值算力, 带宽 × 算术强度)。**它把"该减 FLOPs 还是该减访存"变成一道可算的题**。
  论文很短，一定要自己动手在纸上画一次拐点，并把 depthwise conv、concat、Conv 3×3 三个算子标上去。
- ★ **NVIDIA _Nsight Systems_ 文档与 _Nsight Compute_ 文档** —
  解决「时间到底去哪了」。**分工要记牢**：
  Nsight **Systems** 看整条时间线（CPU、GPU、拷贝、流之间的空隙与同步点）——
  **绝大多数车端延迟问题在这一层就能看出来**（拷贝没重叠、有多余的同步、GPU 有大段空闲）；
  Nsight **Compute** 才是单个 kernel 的内部指标（占用率、访存效率）。
  **不要一上来就用 Compute**，那是在还不知道时间去哪的情况下优化细节。
- ★ **NVIDIA _CUDA C++ Best Practices Guide_ 的 "Memory Optimizations" 一章** —
  解决「拷贝为什么贵、怎么变便宜」。**必读点**：pinned（page-locked）内存为什么能快一倍以上、
  异步拷贝与 stream 的重叠条件、**以及在集成式内存架构（Jetson/Orin）上零拷贝的适用性**——
  同一份优化在独显上是负收益，这是"优化必须跟着硬件架构走"的教科书例子。
- ★ **Reddi et al. 2020 (ISCA), _MLPerf Inference Benchmark_** —
  解决「一份可信的延迟报告应该长什么样」。**它的价值在于测量方法论而不是数字**：
  多种场景（SingleStream / MultiStream / Server / Offline）分别定义、
  **Server 场景用 99 分位延迟作为硬约束**、必须报告完整的系统配置。
  **本课"报延迟必须带条件"这条纪律，以及"车端看 p99 不看均值"这个判断，MLPerf 给了业界标准的背书。**
- ★ **Dean & Barroso 2013 (CACM), _The Tail at Scale_** —
  解决「为什么均值没用」。虽然写的是数据中心，但**尾延迟的成因分析（排队、后台任务、
  功耗管理、共享资源竞争）逐条都能映射到车端**：多任务抢占、降频、GC 式的内存整理。
  **读完你会明白 p99 不是一个更严格的指标，而是一个描述不同现象的指标。**
- **Ma et al. 2018 (ECCV), _ShuffleNet V2: Practical Guidelines for Efficient CNN Architecture Design_** —
  **"FLOPs 不是延迟的好代理"这个论点最经典的出处**，给出四条实用准则
  （等通道数最小化 MAC、谨慎用分组卷积、减少网络碎片化、减少逐元素操作）。
  **后两条直接解释了为什么"层数多的小算子"在车端特别慢**。
- **NVIDIA _Jetson/Orin_ 的 `nvpmodel` 与 `jetson_clocks` 文档，以及 `tegrastats`** —
  解决「为什么同一份 engine 在同一块板子上测出两个数字」。
  **不锁频的测量不可复现**；量产用的功耗档往往不是 MAXN，用 MAXN 测出来的数字发出去会被现场打脸。
  `tegrastats` 能同时看 GPU 频率、温度、功耗，**是验证降频假设的最直接工具**。
- **NVIDIA _TensorRT_ 的 `IProfiler` 接口与 `trtexec --dumpProfile --separateProfileRun`** —
  解决「哪一层最慢」。**注意 profile 里的"层"是融合之后的层**，与 ONNX 节点不是一一对应，
  这本身也是判断"融合有没有发生"的一个信号。
- **CUDA Graphs 的官方文档与 TensorRT 中的用法** —
  解决「kernel 启动开销占比过高」。小模型上 launch 开销可达 10–20%，
  **但它只减少启动开销、不加速计算**，用错地方毫无收益。

---

## 八 · 车端部署的工程材料 · Automotive Deployment in Practice

- ★ **NVIDIA _DRIVE_ 平台文档 与 _DeepStream_ 参考应用（`deepstream-app` 的完整配置）** —
  解决「一条真实的车端感知管线由哪些环节组成」。
  **重点看它的配置文件是怎么把预处理、推理、跟踪、后处理的每个参数显式化的**——
  这份配置本身就是一张一致性检查表。`nvinfer` 的 `net-scale-factor` / `offsets` /
  `model-color-format` / `maintain-aspect-ratio` / `symmetric-padding` 五个字段，
  **正好对应本课模块 01 讲的五类预处理不一致**。
- ★ **MMDeploy（OpenMMLab）的 _"How to support new models"_ 与 _"Quantization"_ 文档** —
  解决「训练框架侧要为部署做哪些改造」。它把"重写不可导出的模块"（rewriter 机制）
  这件事做成了系统化的方案，**是理解"训练代码与部署代码如何共存"的最佳中文材料**。
- **Ultralytics 的 _Export_ 与 _Integrations/TensorRT_ 文档，以及 `export.py` 源码** —
  解决「一条端到端的导出链路实际怎么跑」。
  重点看它对 **INT8 校准数据（`data` 参数）、动态轴、`simplify`、以及是否把 NMS 导进模型** 的处理。
  **⚠️ 许可是 AGPL-3.0，商用前务必确认**（见 C52 模块 05）。
- **Apollo（百度）与 Autoware 的感知模块源码中的 TensorRT 推理封装** —
  解决「开源的车端推理管线长什么样」。
  **重点读它们的内存管理、stream 使用与后处理实现**，
  这是能免费拿到的、最接近量产形态的 C++ 代码；对照本课模块 04 的结构讲解一起读。
- **各仓库 issues 中关于 "TensorRT output mismatch"、"trt slower than pytorch"、
  "int8 accuracy drop"、"onnx export shape" 的讨论线程** —
  **这是最真实的一类工程知识来源，比任何教程都接近实际**。
  建议按这四个关键词在 `NVIDIA/TensorRT`、`microsoft/onnxruntime`、`ultralytics/ultralytics`、
  `open-mmlab/mmdeploy` 四个仓库里各翻十条——
  **你会发现真实问题的分布与本课模块的排布高度一致：预处理与后处理占了大头。**
- **ISO 26262 / ISO 21448 (SOTIF) 的科普性介绍材料** —
  解决「为什么车端对 p99、长稳、可回退这么执着」。
  **不需要精读标准原文**（那是功能安全工程师的工作），
  但理解"性能不足本身就是一类安全隐患（SOTIF 的核心命题）"这个观点，
  能让你在面试里把"我关注 p99"讲成一个有安全工程依据的判断，而不是一个个人偏好。
