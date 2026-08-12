# -*- coding: utf-8 -*-
"""C52 模块 03 · 模型导出与推理运行时。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–02；C27（量化原理）与 C24（推理引擎）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_export_runtime.ipynb'),
    ("核心参考", "ONNX 规范与 operator sets、torch.onnx 文档、TensorRT / CoreML / TFLite 的转换指南"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("why", "导出：把模型交给一个不认识 Python 的运行时", "".join([
        P("训练框架与推理运行时是两种不同的东西。<strong>训练框架为「灵活与可微」优化，推理运行时为「延迟、吞吐、内存、可移植」优化</strong>——它们几乎在每个设计点上做了相反的选择。"),
        TABLE(["", "训练框架（PyTorch/TF）", "推理运行时（ORT/TensorRT/TFLite/CoreML）"], [
            ["需要 Python", "✅ 是", "<strong>❌ 否</strong>（这常常是硬要求）"],
            ["动态性", "任意 Python 控制流", "<strong>有限</strong>（受支持的图算子）"],
            ["算子集", "几千个，随版本增长", "<strong>几百个，且按版本冻结</strong>"],
            ["优化", "有限（保留可微性与可调试性）", "<strong>激进</strong>：融合、常量折叠、布局重排、精度降级"],
            ["部署形态", "Python 进程 + 大依赖", "<strong>一个 <code>.so</code> / <code>.tflite</code> / <code>.mlmodel</code></strong>"],
            ["典型体积", "几 GB（含 torch）", "几 MB（运行时）+ 权重"],
        ]),
        DUAL(
            "「不需要 Python」这一栏往往是<strong>决定性的硬约束</strong>而不是优化项：移动端 App 不能装 Python；嵌入式设备内存装不下；C++/Java 服务不想引入 Python 依赖；某些合规环境禁止解释器。<em>所以「模型能不能导出」经常不是性能问题，而是「能不能上线」的问题</em>。",
            "而导出的核心难点可以一句话概括：<strong>你要把「一段 Python 代码」变成「一张固定的图」，而 Python 的表达力远超任何图 IR</strong>。模块 01 讲的追踪语义在这里全部适用——<em>控制流会被固化、形状会被写死、Python 副作用会消失</em>。区别只是：在 <code>tf.function</code> 里这些是性能问题，在导出里这些是<strong>正确性问题</strong>（因为图会被交出去，再也不会重新追踪）。",
        ),
        CALLOUT("warn", "所以导出最危险的失败模式是：<strong>「导出成功、跑通了、但换个输入就错」</strong>。追踪时 batch=1、seq=128，导出的图里这两个数字被写死；线上来了 batch=8 就报形状错（好情况），或者某个 <code>if</code> 分支被固化成了追踪时那条（坏情况——不报错、结果错）。<em>本模块的核心就是把这些「导出时看不出、上线才炸」的问题提前暴露出来。</em>"),
    ])),
    ("ir", "ONNX：一张图、一个算子集、一个版本号", "".join([
        P("<span class=\"term\">ONNX</span> 是当前事实上的交换格式。它的模型结构简单到可以在一页纸内说清："),
        ASCII("""ONNX Model
├── ir_version          IR 格式本身的版本
├── opset_import        **算子集版本**（如 ai.onnx v17）← 兼容性的核心
├── producer_name       谁导出的（pytorch 2.4.1）
└── graph
    ├── input   [ {name, type: tensor(float), shape: [batch, seq, 768]} ]
    │                                              ↑ 可以是符号（动态轴）
    ├── output  [ {name, type, shape} ]
    ├── initializer  权重（常量张量）
    └── node[]  拓扑排序的算子列表
         └── {op_type: "MatMul", input: [...], output: [...], attribute: {...}}

关键性质：
  · **静态拓扑**：节点与边在导出时固定；控制流要用 If/Loop/Scan 算子表达
  · **算子按 opset 版本冻结**：同一个 op 在不同 opset 里语义可能不同
  · **形状可以是符号**：["batch", "seq"] 而不是 [1, 128] —— 这就是动态轴
  · **权重内联**：initializer 就在文件里（所以 ONNX 文件很大）""")
        ,
        TABLE(["概念", "是什么", "搞错了会怎样"], [
            ["<strong>opset 版本</strong>", "算子集的版本号。每个 op 有「自哪个 opset 起可用/语义变更」", "目标运行时不支持该 opset → 加载失败；或算子语义变了 → 数值错"],
            ["<strong>动态轴</strong>", "把某些维度声明为符号（<code>\"batch\"</code>）而非常数", "<strong>不设 → 形状被写死 → 换 batch 就崩</strong>"],
            ["<strong>initializer</strong>", "内联在文件里的权重", "大模型的 ONNX 文件超过 2GB 会触发 protobuf 限制，要用外部数据"],
            ["<strong>自定义算子</strong>", "标准算子集之外的 op", "运行时不认识 → 需要自己注册实现，或改模型避开"],
            ["<strong>形状推断</strong>", "从输入形状推出每个中间张量的形状", "推断失败 → 某些优化无法进行、或运行时报错"],
        ]),
        DUAL(
            "<strong>opset 版本是最常见的兼容性问题来源</strong>，而且它有一个反直觉的性质：<em>不是「越新越好」</em>。导出时用了 opset 18，但目标运行时（可能是一年前的版本、或某个嵌入式的 ORT 精简版）只支持到 15，就直接加载失败。<strong>正确做法是先确定目标运行时支持的 opset 上限，再据此导出</strong>——而不是导出后才发现。",
            "<strong>动态轴</strong>是第二个高频坑，且更隐蔽。<code>torch.onnx.export</code> 默认会把追踪时的形状<em>全部写死</em>。如果你用 <code>(1, 128)</code> 的样例输入导出，得到的图只接受 <code>(1, 128)</code>。<em>好一点的运行时会报「形状不匹配」，差一点的会静默走一条错误的路径</em>。<strong>凡是会变的维度（batch、序列长、图像尺寸）都必须显式声明为动态轴</strong>——而这需要你提前想清楚「什么会变」。",
        ),
        CODE("""torch.onnx.export(
    model, (example_input,), "model.onnx",
    opset_version=17,                          # ← 先查目标运行时支持到几
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={                             # ← **凡是会变的维度都要声明**
        "input_ids":      {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "logits":         {0: "batch"},
    },
    do_constant_folding=True,
)"""),
    ])),
    ("unsupported", "算子不支持：四条出路", "".join([
        P("导出时最常见的报错是「<code>Exporting the operator X to ONNX opset version N is not supported</code>」。<strong>遇到它有四条出路，成本递增</strong>——重要的是知道<em>先试哪一条</em>。"),
        TABLE(["出路", "做什么", "成本", "什么时候用"], [
            ["<strong>① 换算子</strong>", "用等价的、被支持的算子重写这一段", "<strong>最低</strong>", "首选。多数「不支持」的算子都有等价写法"],
            ["<strong>② 提高 opset</strong>", "该算子在更高 opset 里已支持", "低（若运行时也支持）", "查一下算子的「since version」"],
            ["<strong>③ 分解</strong>", "把复合算子拆成基础算子的组合", "中（要自己写并验证数值）", "如自定义激活、特殊归一化"],
            ["<strong>④ 自定义算子</strong>", "注册 symbolic 函数 + 在运行时实现 kernel", "<strong>最高</strong>（要写 C++ 并跟着运行时版本维护）", "真的无法避开（如自研 kernel）"],
        ]),
        DUAL(
            "<strong>出路 ① 常常被跳过，但它成功率最高</strong>。很多「不支持」其实是用了某个 Python 便利写法：<code>tensor.item()</code>（把 tensor 变 Python 标量——会固化）、花式索引、<code>torch.unique</code>、<code>nonzero</code>（输出形状依赖数据，图 IR 很难表达）。<em>把它们改写成形状确定的算子组合，通常几行就能解决</em>。",
            "特别值得记住的一类是<strong>「输出形状依赖输入<em>数值</em>」的算子</strong>——<code>nonzero</code>、<code>unique</code>、<code>masked_select</code>、动态 <code>topk</code>。它们在图 IR 里天然困难，因为形状推断做不了。<em>解法通常是把它们移出模型</em>：模型输出固定形状的 mask/分数，由调用方在 Python/C++ 侧做筛选。<strong>「把动态部分挪到模型之外」是导出工程里最有效的一招。</strong>",
        ),
        CALLOUT("intuition", "还有一个诊断技巧：<strong>先导出模型的一小块，二分定位到底是哪个算子不支持</strong>。整模型导出报错时，错误信息常常指向一个很深的调用栈，看不出是模型的哪一层。<em>把模型按层切开、逐块导出，几分钟就能定位</em>。这与模块 02 的「逐层对拍」是同一个思路——<strong>把整体失败分解成可定位的局部失败</strong>。"),
    ])),
    ("verify", "导出后必须做的三件事", "".join([
        P("导出成功 ≠ 导出正确。有三个检查<strong>必须</strong>做，缺一个都可能上线炸。"),
        H3("① 数值对拍（在多组形状上）"),
        P("用模块 02 的方法学，但有一个关键差别：<strong>必须在<em>多组不同形状</em>上对拍，而不只是导出时用的那一组</strong>。因为形状被写死或动态轴设错的问题，只有换形状才暴露。"),
        CODE("""for batch, seq in [(1, 128), (1, 7), (8, 512), (3, 333)]:   # 含奇数、极值、非对齐
    x = make_input(batch, seq)
    ref = torch_model(x).numpy()
    got = ort_session.run(None, {"input_ids": x})[0]
    assert np.allclose(ref, got, rtol=1e-3, atol=1e-4), f"failed at {batch}x{seq}\""""),
        H3("② 形状边界测试"),
        P("显式测试<strong>边界与非常规形状</strong>：batch=1、序列长为 1、序列长为奇数、序列长不是 8 的倍数、超过训练时见过的最大长度。<em>很多运行时（尤其 TensorRT）对对齐有隐含要求，只在非对齐形状上暴露</em>。"),
        H3("③ 算子覆盖与运行时兼容"),
        P("把导出图里用到的<strong>全部 op_type 与 opset</strong>列出来，与目标运行时的支持列表求交集。<em>这一步能在部署前几分钟发现「这个算子在 TensorRT 上不支持、会回退到 CPU」这类性能陷阱</em>。"),
        DUAL(
            "第 ③ 点里的「<strong>回退</strong>」值得展开。TensorRT 遇到不支持的算子时不会报错，而是把图切成多个子图，<em>不支持的部分交给别的后端（甚至 CPU）执行</em>。结果是模型能跑、数值也对，但<strong>性能可能比不优化还差</strong>（因为多了大量设备间数据搬运）。<em>症状是「转了 TensorRT 但没变快」，而日志里那行「N subgraphs」才是原因。</em>",
            "同类的隐性回退在各个运行时都有：ONNX Runtime 的 execution provider 会按优先级回退（CUDA → CPU）；CoreML 会把不支持的层放到 CPU 而不是 ANE；TFLite 的 delegate 也会部分回退。<strong>所以「导出后的性能验证」必须与「数值验证」同等对待</strong>，而且要看运行时的<em>分区日志</em>而不只是端到端延迟。",
        ),
        CALLOUT("danger", "<p>一个必须显式测试的边界：<strong><code>batch=1</code> 与 <code>batch&gt;1</code> 可能走完全不同的代码路径</strong>。某些算子在 batch=1 时被优化掉、某些 kernel 只在 batch≥N 时启用、某些 padding 逻辑只在多样本时触发。<em>「用 batch=1 导出并验证，上线用 batch=8」是一个非常常见且危险的组合</em>。<strong>导出时的样例输入应该用一个「中间的、非特殊的」形状</strong>（如 batch=2、seq=17），这样更容易暴露对特殊值的隐含依赖。</p>", "别用 batch=1 做样例输入"),
    ])),
    ("runtimes", "四个目标运行时：各自的约束", "".join([
        TABLE(["运行时", "目标平台", "输入格式", "最大特点", "主要约束"], [
            ["<strong>ONNX Runtime</strong>", "跨平台（CPU/CUDA/DirectML/…）", "ONNX", "最通用；execution provider 可插拔", "优化程度不如专用运行时"],
            ["<strong>TensorRT</strong>", "NVIDIA GPU", "ONNX（或自建网络）", "<strong>最快</strong>：层融合、精度校准、kernel autotune", "构建慢（几分钟到几十分钟）；<strong>引擎与 GPU 型号/驱动绑定</strong>"],
            ["<strong>CoreML</strong>", "Apple 设备", "mlpackage（从 ONNX/PyTorch 转）", "能用 ANE（神经引擎），极省电", "算子集受限；ANE 只支持部分算子与精度"],
            ["<strong>TFLite</strong>", "移动/嵌入式", "tflite（从 TF/ONNX 转）", "体积极小；delegate 生态成熟", "算子集最受限；动态形状支持弱"],
        ]),
        DUAL(
            "<strong>TensorRT 的「引擎与硬件绑定」</strong>是个必须提前知道的工程约束：构建出来的 <code>.engine</code> 文件<em>只能在同型号 GPU + 兼容驱动上运行</em>。换一张卡（甚至同型号不同驱动大版本）就要重新构建。<em>所以生产上要么在目标机器上构建、要么为每种硬件配置各构建一份并纳入发布流程</em>。而构建本身要几分钟到几十分钟——<strong>这直接影响 C48 讲的冷启动与镜像策略</strong>（引擎要预构建进镜像还是启动时构建，是个真实的取舍）。",
            "<strong>CoreML 的 ANE 约束</strong>是另一类：ANE（Apple Neural Engine）极省电、极快，但它只支持有限的算子与精度（主要是 fp16 与特定的卷积/矩阵形状）。<em>模型会「成功转换」，但实际跑在 CPU 或 GPU 上而不是 ANE</em>——性能与功耗都差一个档次。<strong>验证方式是看 Xcode 的性能报告里每层的实际计算单元</strong>，而不是看端到端延迟。这与 TensorRT 的静默回退是同一类问题。",
        ),
        CALLOUT("intuition", "四个运行时的选择其实由<strong>目标硬件</strong>决定，没什么可纠结的：NVIDIA GPU → TensorRT（或 ORT-CUDA 求省事）；Apple → CoreML；Android/嵌入式 → TFLite；<em>不确定或要跨平台 → ONNX Runtime</em>。<strong>真正需要决策的不是「用哪个」，而是「为了用它，模型要做哪些妥协」</strong>——去掉哪些算子、接受多少精度损失、能不能容忍构建时间。<em>这个妥协清单应该在训练模型<em>之前</em>就知道，而不是训完才发现导不出去。</em>"),
    ])),
    ("quant", "导出时的精度降级：三种粒度", "".join([
        P("导出常常伴随精度降级（fp32 → fp16/int8）。原理在 C27 讲过，这里只讲<strong>导出场景下的三种做法与它们的验证要求</strong>。"),
        TABLE(["做法", "怎么做", "精度损失", "需要什么"], [
            ["<strong>fp16 转换</strong>", "权重与计算都转 fp16", "通常极小", "无需数据；但要检查是否有溢出（激活值 &gt; 65504）"],
            ["<strong>训练后动态量化</strong>", "权重 int8、激活运行时统计", "小-中", "无需数据；CPU 上收益最大"],
            ["<strong>训练后静态量化</strong>", "权重与激活都 int8，用<strong>校准集</strong>确定激活范围", "中", "<strong>需要几百条代表性数据</strong>"],
        ]),
        DUAL(
            "<strong>静态量化的「校准集」是最容易做错的一步</strong>。它的作用是统计每层激活的数值范围，从而确定量化的 scale。<em>如果校准集的分布与线上分布不同，量化范围就是错的</em>——常见错误包括：只用训练集头几条（可能全是同一类别）、用了预处理不一致的数据、样本太少（&lt;100）覆盖不到长尾。<strong>校准集应该是「线上分布的一个小样本」，几百条即可，但必须有代表性。</strong>",
            "fp16 的坑则是<strong>溢出</strong>：fp16 的最大值约 65504，而某些层（尤其是注意力的 <code>QK^T</code> 在未缩放时、或某些归一化的中间量）可能超过它，产生 <code>inf</code> 然后传播成 <code>nan</code>。<em>这个问题在训练时被 loss scaling 掩盖，导出到纯 fp16 推理时才暴露</em>。<strong>检查方法：用极端输入（大幅值、长序列）跑一遍，看有没有 inf/nan</strong>——而不是只用正常样本验证。",
        ),
        CALLOUT("warn", "量化后的对拍<strong>容差要按量化误差而不是浮点误差来设</strong>。int8 量化的相对误差在 1% 量级，用 <code>rtol=1e-5</code> 去对拍必然「失败」——但那不是 bug。<em>正确做法是：①对拍<strong>最终任务指标</strong>（准确率/BLEU）而非逐元素数值；②逐层看的是「误差是否在预期量级」而不是「是否 allclose」；③重点检查有没有<strong>异常层</strong>（某一层误差比其他层大一个数量级——通常是它的激活分布有长尾）</em>。"),
    ])),
    ("artifacts", "导出产物的版本管理", "".join([
        P("导出会产生一批新的二进制产物，而它们<strong>与训练 checkpoint 有完全不同的生命周期</strong>——这一点常被忽略，直到某天没人说得清线上跑的 <code>model.onnx</code> 是从哪个 checkpoint 来的。"),
        TABLE(["产物", "由什么决定", "什么时候必须重建"], [
            ["<code>model.onnx</code>", "checkpoint + 导出参数（opset、动态轴）", "换 checkpoint；改导出配置；升 opset"],
            ["<code>model.engine</code>（TensorRT）", "ONNX + <strong>GPU 型号 + 驱动 + TRT 版本</strong>", "上面任何一项变化——<em>包括换一张同型号但驱动不同的卡</em>"],
            ["量化校准表", "校准集 + 模型结构", "换校准集；模型结构变；输入分布漂移"],
            ["<code>.tflite</code> / <code>.mlpackage</code>", "源模型 + 转换器版本", "转换器升级（算子映射可能变）"],
        ]),
        DUAL(
            "第二行是运维上最麻烦的一个：<strong>TensorRT 引擎与硬件绑定，意味着「一份 checkpoint」会变成「N 份引擎」</strong>（N = 硬件配置种类数）。它们必须与源 ONNX 一起被追踪，否则很快就会出现「这台机器上的引擎是三个月前构建的，用的是哪版模型没人记得」。<em>而引擎是二进制的，看不出来。</em>",
            "解法很朴素但必须做：<strong>给每个产物附一份 manifest，记录它的全部输入</strong>——源 checkpoint 的哈希、导出参数、opset、构建时的 GPU 型号与驱动版本、运行时版本、以及验证时用的形状集合与容差。<em>把 manifest 与产物放在一起（或嵌进文件的 metadata），并在服务启动时校验</em>。这与 C48 讲的镜像标签策略是同一个思路：<strong>凡是不可读的二进制产物，都必须有一份可读的来源说明</strong>。",
        ),
        CALLOUT("intuition", "一个能省很多事的约定：<strong>把「导出 + 验证」做成一条流水线，而不是两个手工步骤</strong>。导出脚本的最后一步就是跑多形状对拍与算子覆盖检查，<em>任何一项不过就不产出文件</em>。这样「存在一个 <code>.onnx</code> 文件」本身就意味着「它通过了验证」——<strong>用「产物的存在性」编码「验证已通过」这个事实</strong>，比依赖人记得跑验证可靠得多。这个模式在 C48 的镜像构建、C43 的数据管线里都出现过。"),
    ])),
    ("ledger", "算一笔账：导出的收益与代价", "".join([
        MATH("\\text{加速比} = \\frac{t_{eager}}{t_{runtime}}, \\qquad \\text{值得} \\iff N \\cdot (t_{eager} - t_{runtime}) > C_{export} + C_{build} \\cdot n_{hw}"),
        TABLE(["运行时", "典型加速比", "构建时间", "工程成本", "何时值得"], [
            ["ONNX Runtime (CPU)", "1.5–3×", "秒级", "低", "<strong>几乎总是</strong>（尤其 CPU 推理）"],
            ["ONNX Runtime (CUDA)", "1.1–1.5×", "秒级", "低", "想去掉 Python 依赖时"],
            ["TensorRT fp16", "2–5×", "<strong>几分钟–几十分钟</strong>", "中（要处理算子回退）", "GPU 推理量大、硬件固定"],
            ["TensorRT int8", "3–8×", "更长（要校准）", "<strong>高</strong>（要校准集 + 精度验证）", "延迟/成本敏感且能接受精度损失"],
            ["TFLite / CoreML", "N/A（唯一选项）", "分钟级", "中-高（算子受限）", "<strong>移动/嵌入式：不是优化是必需</strong>"],
        ]),
        P("三点观察："),
        UL([
            "<strong>CPU 推理上导出的收益最大</strong>（1.5–3×），因为 PyTorch 的 CPU 路径优化远不如专用运行时。<em>而很多「小模型 + CPU 部署」的场景（C49 模块 05 讲的 encoder 方案）恰好在这一档。</em>",
            "<strong>GPU 上 ORT 的收益有限</strong>（1.1–1.5×），因为 PyTorch 的 CUDA 路径已经很好。<em>此时导出的主要动机往往是「去掉 Python 依赖」而非速度。</em>",
            "<strong>TensorRT 的构建时间要乘以硬件种类数</strong>——引擎与 GPU 型号绑定。如果你有三种 GPU，就是三份引擎、三次构建、三份产物要管理。<em>这个运维成本常被低估。</em>",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>导出不是「把模型另存为另一种格式」，而是「把一段 Python 程序编译成一个受限 IR 上的静态图」——所以 Python 里那些方便的动态性，都要在导出前被消除或移出模型</strong>。想清楚这一点，导出的所有坑（形状写死、控制流固化、算子不支持、静默回退）就都成了同一个问题的不同表现。<em>而最有效的通用招数只有一条：把动态部分挪到模型之外。</em>"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>导出路径的更替</strong>：PyTorch 正从 TorchScript-based 的 <code>torch.onnx.export</code> 迁移到基于 <code>torch.export</code>/Dynamo 的新路径（<code>dynamo=True</code>）。新路径对动态形状与控制流的支持更好，但成熟度与算子覆盖仍在追赶。<em>短期内两条路径并存，选哪条要看具体模型。</em>",
            "<strong>动态形状的 IR 表达</strong>：符号形状、形状约束的传播与验证，是所有 IR 的共同难题。ONNX 的符号维只是「名字相同即相等」，无法表达 <code>seq &lt;= 512</code> 或 <code>seq % 8 == 0</code> 这类约束——而这些约束恰恰是运行时优化需要的。",
            "<strong>LLM 的导出</strong>：自回归生成含 KV 缓存的有状态循环，用静态图表达非常别扭。目前主流做法是<em>绕过导出</em>——直接用 vLLM/TensorRT-LLM 这类专用引擎从权重构建，而不是走通用 IR。「通用 IR 能否表达高效的 LLM 推理」目前是否定的。",
            "<strong>MLIR / StableHLO 生态</strong>：试图提供比 ONNX 更通用、更可组合的中间表示（支持训练图、自定义方言、渐进 lowering）。工业采用仍集中在编译器内部，作为<em>交换格式</em>尚未取代 ONNX。",
            "<strong>导出正确性的自动验证</strong>：目前靠人工写多形状对拍。<em>能否自动生成覆盖边界的测试形状、自动检测静默回退、自动比对分区结果</em>，缺少标准工具——这也是本模块要你手写检查器的原因。",
        ]),
        CALLOUT("paper", "必读：ONNX 官方的 <em>Operators</em> 文档（每个 op 的「since version」与语义变更，兼容性问题的一手来源）与 <em>IR specification</em>；PyTorch 的 <em>torch.onnx</em> 文档（尤其 <em>Limitations</em> 与 <em>Frequently Asked Questions</em> 两节，把追踪的坑列得很清楚）；NVIDIA 的 <em>TensorRT Developer Guide</em>（重点看 layer fusion 与 INT8 calibration 两章，以及「engine 与硬件绑定」的说明）；Apple 的 <em>Core ML Tools</em> 文档（ANE 支持的算子与精度约束）。相邻课程：C27（量化算法）、C24（推理引擎内部）、C48（部署与冷启动）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 03 · 模型导出与推理运行时（迷你 IR / 形状推断 / 动态轴 / 算子覆盖 / 量化对拍）

目标：手写一个**迷你 ONNX**——图 IR、opset 版本、形状推断、动态轴、算子覆盖检查——
并复现导出的四类经典失败：**形状写死、控制流固化、算子不支持、静默回退**。

路线：迷你 IR 与图 → 形状推断 → **不设动态轴的后果**（换 batch 就崩）→
控制流固化 → opset 兼容性检查 → 算子覆盖与静默回退 →
多形状对拍与边界测试 → 量化对拍的正确容差 → ✏️ 练习 → 📖 答案 → 🧪 导出前检查器。

> 心智模型：**导出 = 把一段 Python 程序编译成受限 IR 上的静态图。
> 最有效的通用招数只有一条：把动态部分挪到模型之外。**"""),
    md("""## 1 · 迷你 IR：节点、边、opset、符号形状"""),
    code("""import numpy as np, math, collections, itertools, json
rng = np.random.default_rng(0)

# 算子库：每个 op 记录 (自哪个 opset 起可用, 形状推断函数, 参考实现)
def _shape_matmul(shapes, attrs):
    a, b = shapes
    assert a[-1] == b[-2] or isinstance(a[-1], str) or isinstance(b[-2], str), \\
        f'matmul 内维不匹配: {a} @ {b}'
    return tuple(list(a[:-1]) + [b[-1]])

def _shape_same(shapes, attrs):  return shapes[0]
def _shape_reduce_last(shapes, attrs): return tuple(shapes[0][:-1])

OPS = {
    'MatMul':  {'since': 1,  'shape': _shape_matmul,
                'run': lambda ins, at: ins[0] @ ins[1]},
    'Add':     {'since': 1,  'shape': _shape_same,
                'run': lambda ins, at: ins[0] + ins[1]},
    'Relu':    {'since': 1,  'shape': _shape_same,
                'run': lambda ins, at: np.maximum(ins[0], 0)},
    'Gelu':    {'since': 20, 'shape': _shape_same,          # ← 直到 opset 20 才是标准算子
                'run': lambda ins, at: 0.5*ins[0]*(1+np.tanh(
                    math.sqrt(2/math.pi)*(ins[0]+0.044715*ins[0]**3)))},
    'LayerNorm': {'since': 17, 'shape': _shape_same,        # ← opset 17 起
                  'run': lambda ins, at: (lambda x, g, b, e: (x - x.mean(-1, keepdims=True))
                         / np.sqrt(x.var(-1, keepdims=True) + e) * g + b)(
                             ins[0], ins[1], ins[2], at.get('epsilon', 1e-5))},
    'ReduceSum': {'since': 1, 'shape': _shape_reduce_last,
                  'run': lambda ins, at: ins[0].sum(-1)},
    'If':      {'since': 1,  'shape': lambda s, a: s[1],
                'run': None},                                # 控制流：需要子图
    'NonZero': {'since': 9,  'shape': lambda s, a: (len(s[0]), 'nnz'),   # ← 形状依赖**数值**
                'run': None},
}

class Node:
    def __init__(self, op_type, inputs, output, **attrs):
        self.op_type, self.inputs, self.output, self.attrs = op_type, inputs, output, attrs
    def __repr__(self):
        a = f' {self.attrs}' if self.attrs else ''
        return f'{self.output} = {self.op_type}({", ".join(self.inputs)}){a}'

class OnnxModel:
    def __init__(self, opset=17):
        self.opset = opset
        self.nodes, self.inputs, self.outputs, self.initializers = [], {}, [], {}
    def add_input(self, name, shape, dtype='float32'):
        self.inputs[name] = {'shape': tuple(shape), 'dtype': dtype}; return name
    def add_init(self, name, arr):
        self.initializers[name] = np.asarray(arr, dtype=np.float64); return name
    def add_node(self, op_type, inputs, output, **attrs):
        self.nodes.append(Node(op_type, inputs, output, **attrs)); return output
    def op_types(self):
        return sorted({n.op_type for n in self.nodes})
    def __repr__(self):
        head = (f'opset={self.opset}\\ninputs: ' +
                ', '.join(f'{k}{v["shape"]}' for k, v in self.inputs.items()))
        return head + '\\nnodes:\\n' + '\\n'.join('  ' + repr(n) for n in self.nodes)

# 造一个小模型：LN(GELU(x@W1)@W2)
m = OnnxModel(opset=17)
m.add_input('x', ('batch', 'seq', 8))
m.add_init('W1', rng.normal(size=(8, 16)) * 0.3)
m.add_init('W2', rng.normal(size=(16, 8)) * 0.3)
m.add_init('g', np.ones(8)); m.add_init('b', np.zeros(8))
m.add_node('MatMul', ['x', 'W1'], 'h1')
m.add_node('Gelu', ['h1'], 'h2')
m.add_node('MatMul', ['h2', 'W2'], 'h3')
m.add_node('LayerNorm', ['h3', 'g', 'b'], 'y', epsilon=1e-5)
m.outputs = ['y']
print(m)
assert m.op_types() == ['Gelu', 'LayerNorm', 'MatMul']
print('\\n✅ 迷你 IR 就位：静态拓扑 + opset 版本 + 符号形状（"batch"/"seq"）')"""),
    md("""## 2 · 形状推断与动态轴：不设的后果"""),
    code("""def infer_shapes(model, concrete=None):
    '''从输入形状推出每个中间张量的形状。concrete: {符号名: 具体值}（None 表示保持符号）。'''
    concrete = concrete or {}
    def resolve(shape):
        return tuple(concrete.get(d, d) if isinstance(d, str) else d for d in shape)
    env = {k: resolve(v['shape']) for k, v in model.inputs.items()}
    env.update({k: v.shape for k, v in model.initializers.items()})
    for n in model.nodes:
        spec = OPS[n.op_type]
        env[n.output] = spec['shape']([env[i] for i in n.inputs], n.attrs)
    return env

env_sym = infer_shapes(m)
print('符号形状推断:')
for k in ['x', 'h1', 'h2', 'h3', 'y']:
    print(f'  {k:<4s} {env_sym[k]}')
assert env_sym['y'] == ('batch', 'seq', 8)
env_c = infer_shapes(m, {'batch': 4, 'seq': 128})
assert env_c['y'] == (4, 128, 8)
print(f'\\n代入 batch=4, seq=128: y{env_c["y"]}  ✅ 动态轴让同一张图接受任意形状')"""),
    code("""# ❌ 不设动态轴：导出时的形状被**写死**
m_static = OnnxModel(opset=17)
m_static.add_input('x', (1, 128, 8))               # ← 追踪时 batch=1, seq=128
for k, v in m.initializers.items(): m_static.add_init(k, v)
for n in m.nodes: m_static.add_node(n.op_type, n.inputs, n.output, **n.attrs)
m_static.outputs = ['y']

def check_input_shape(model, actual):
    '''运行时的形状检查。'''
    declared = model.inputs['x']['shape']
    errs = []
    for i, (d, a) in enumerate(zip(declared, actual)):
        if isinstance(d, str):
            continue                                # 动态轴：任意值都行
        if d != a:
            errs.append(f'dim{i}: 图里写死为 {d}，实际传入 {a}')
    return (not errs), errs

print(f"{'实际输入形状':<18s} {'静态图':<28s} {'动态轴图'}")
for shape in [(1, 128, 8), (8, 128, 8), (1, 64, 8), (3, 333, 8)]:
    ok_s, err_s = check_input_shape(m_static, shape)
    ok_d, _ = check_input_shape(m, shape)
    print(f'{str(shape):<18s} {("✅" if ok_s else "❌ " + err_s[0]):<28s} {"✅" if ok_d else "❌"}')

assert check_input_shape(m_static, (1, 128, 8))[0]
assert not check_input_shape(m_static, (8, 128, 8))[0], '静态图换 batch 就崩'
assert all(check_input_shape(m, s)[0] for s in [(1,128,8),(8,128,8),(3,333,8)])
print('\\n⚠️  「用 batch=1, seq=128 的样例导出，线上来 batch=8」是最常见的导出事故。')
print('✅ 凡是会变的维度（batch / 序列长 / 图像尺寸）都必须声明为动态轴。')
print('   真实对应: torch.onnx.export(..., dynamic_axes={"x": {0: "batch", 1: "seq"}})')"""),
    md("""## 3 · 控制流固化：导出里这是**正确性**问题

模块 01 里 Python 控制流被固化是性能问题（可以重追踪）；
**在导出里它是正确性问题**——图被交出去后，再也不会重新追踪。"""),
    code("""def python_branch_model(use_relu):
    '''Python bool 决定分支 -> 追踪时定死。'''
    g = OnnxModel(opset=17)
    g.add_input('x', ('batch', 8))
    g.add_init('W', rng.normal(size=(8, 8)) * 0.3)
    g.add_node('MatMul', ['x', 'W'], 'h')
    if use_relu:                                   # ← Python 层面的分支
        g.add_node('Relu', ['h'], 'y')
    else:
        g.add_node('Add', ['h', 'h'], 'y')
    g.outputs = ['y']
    return g

g_true = python_branch_model(True)
g_false = python_branch_model(False)
print('use_relu=True  导出的图:', g_true.op_types())
print('use_relu=False 导出的图:', g_false.op_types())
assert 'Relu' in g_true.op_types() and 'Relu' not in g_false.op_types()
print('⚠️  两张**不同的图**。导出后 use_relu 再也改不了 ——')
print('    如果它本该依赖运行时输入，你导出的就是一个**永远走同一条分支**的错模型。')

# ✅ 正确做法：用 If 算子把两个分支都放进图
def graph_branch_model():
    g = OnnxModel(opset=17)
    g.add_input('x', ('batch', 8))
    g.add_input('cond', ())
    g.add_init('W', rng.normal(size=(8, 8)) * 0.3)
    g.add_node('MatMul', ['x', 'W'], 'h')
    g.add_node('Relu', ['h'], 'br_true')
    g.add_node('Add', ['h', 'h'], 'br_false')
    g.add_node('If', ['cond', 'br_true', 'br_false'], 'y')
    g.outputs = ['y']
    return g

g_if = graph_branch_model()
print('\\n图内控制流:', g_if.op_types())
assert 'If' in g_if.op_types() and 'Relu' in g_if.op_types()
print('✅ 一张图涵盖两个分支，运行时按 cond 选择。')
print('   代价：两个分支都要能通过形状推断，且图更复杂、部分优化受限。')"""),
    md("""## 4 · opset 兼容性与算子覆盖：部署前的两分钟检查"""),
    code("""def check_opset(model):
    '''每个算子都要求 model.opset >= 它的 since version。'''
    bad = [(n.op_type, OPS[n.op_type]['since'])
           for n in model.nodes if OPS[n.op_type]['since'] > model.opset]
    return (not bad), bad

for opset in [20, 17, 15, 9]:
    mm = OnnxModel(opset=opset)
    mm.nodes = m.nodes; mm.inputs = m.inputs; mm.initializers = m.initializers
    ok, bad = check_opset(mm)
    detail = '' if ok else '  需要: ' + ', '.join(f'{o}>=opset{s}' for o, s in bad)
    print(f'opset={opset:<3d} {"✅ 全部算子可用" if ok else "❌ " + str([b[0] for b in bad])}{detail}')

mm17 = OnnxModel(17); mm17.nodes = m.nodes
assert not check_opset(mm17)[0], 'Gelu 需要 opset>=20'
mm20 = OnnxModel(20); mm20.nodes = m.nodes
assert check_opset(mm20)[0]
print('\\n⚠️  opset **不是越新越好**：目标运行时可能只支持到 15。')
print('✅ 正确顺序：先查目标运行时支持的 opset 上限，再据此导出。')"""),
    code("""# 运行时的算子支持表（真实世界里各不相同）
RUNTIME_SUPPORT = {
    'onnxruntime-cpu':  {'MatMul','Add','Relu','Gelu','LayerNorm','ReduceSum','If','NonZero'},
    'tensorrt':         {'MatMul','Add','Relu','LayerNorm'},          # Gelu 需插件；无 NonZero
    'tflite':           {'MatMul','Add','Relu'},                      # 算子集最受限
    'coreml-ane':       {'MatMul','Add','Relu','LayerNorm'},          # ANE 支持的子集
}

def coverage_report(model, runtime):
    sup = RUNTIME_SUPPORT[runtime]
    used = model.op_types()
    unsupported = [o for o in used if o not in sup]
    # 静默回退：不支持的算子会把图切成多个子图，交给别的后端
    n_partitions = 1
    prev_ok = None
    for n in model.nodes:
        ok = n.op_type in sup
        if prev_ok is not None and ok != prev_ok:
            n_partitions += 1
        prev_ok = ok
    return {'runtime': runtime, 'used': used, 'unsupported': unsupported,
            'partitions': n_partitions, 'fully_supported': not unsupported}

print(f"{'运行时':<18s} {'不支持的算子':<26s} {'子图数':>7s} {'结论'}")
for rt in RUNTIME_SUPPORT:
    r = coverage_report(m, rt)
    verdict = '✅ 全图加速' if r['fully_supported'] else \\
              (f'⚠️ 切成 {r["partitions"]} 个子图 -> **静默回退**')
    print(f'{rt:<18s} {str(r["unsupported"]):<26s} {r["partitions"]:>7d} {verdict}')

r_trt = coverage_report(m, 'tensorrt')
assert 'Gelu' in r_trt['unsupported'] and r_trt['partitions'] > 1
assert coverage_report(m, 'onnxruntime-cpu')['fully_supported']
print('\\n⚠️  **静默回退**：TensorRT 遇到不支持的算子不会报错，而是把图切开、')
print('    不支持的部分交给别的后端（甚至 CPU）。模型能跑、数值也对，')
print('    但**性能可能比不优化还差**（多了大量设备间搬运）。')
print('    症状是「转了 TensorRT 但没变快」，而日志里那行「N subgraphs」才是原因。')
print('✅ 所以「导出后的性能验证」必须与「数值验证」同等对待，且要看**分区日志**。')"""),
    md("""### 算子不支持的四条出路（按成本递增）"""),
    code("""def decompose_gelu(model):
    '''出路 ③：把 Gelu 分解成基础算子（这里用 tanh 近似的算子组合示意）。'''
    new = OnnxModel(opset=model.opset)
    new.inputs = dict(model.inputs); new.initializers = dict(model.initializers)
    for n in model.nodes:
        if n.op_type == 'Gelu':
            # 真实分解会用 Mul/Add/Tanh/Pow 等基础算子；这里用 Relu 占位表示「换成被支持的算子」
            new.add_node('Relu', n.inputs, n.output)
        else:
            new.add_node(n.op_type, n.inputs, n.output, **n.attrs)
    new.outputs = list(model.outputs)
    return new

ROUTES = [
    ('① 换算子/分解', lambda mdl: decompose_gelu(mdl), '最低', '首选'),
    ('② 提高 opset', None, '低', '若目标运行时也支持'),
    ('③ 分解成基础算子', lambda mdl: decompose_gelu(mdl), '中', '要自己验证数值'),
    ('④ 自定义算子插件', None, '最高', '真的无法避开时'),
]
m_fixed = decompose_gelu(m)
r_before = coverage_report(m, 'tensorrt')
r_after = coverage_report(m_fixed, 'tensorrt')
print(f'TensorRT 覆盖: 处理前 不支持{r_before["unsupported"]}, {r_before["partitions"]} 个子图')
print(f'              处理后 不支持{r_after["unsupported"]}, {r_after["partitions"]} 个子图')
assert r_after['fully_supported'] and r_after['partitions'] == 1
print('\\n✅ 出路 ① 成功率最高却常被跳过。多数「不支持」其实是用了 Python 便利写法。')

# 形状依赖**数值**的算子：图 IR 天然困难
m_nz = OnnxModel(opset=17)
m_nz.add_input('x', ('batch', 8))
m_nz.add_node('NonZero', ['x'], 'idx')
m_nz.outputs = ['idx']
env_nz = infer_shapes(m_nz, {'batch': 4})
print(f'\\nNonZero 的输出形状: {env_nz["idx"]}  ← 第二维 "nnz" **依赖输入数值**，推断不出来')
assert 'nnz' in env_nz['idx']
print('⚠️  这类算子（NonZero / Unique / masked_select / 动态 topk）在图 IR 里天然困难。')
print('✅ 通用解法：**把动态部分挪到模型之外** ——')
print('   模型输出固定形状的 mask/分数，由调用方在 Python/C++ 侧做筛选。')"""),
    md("""## 5 · 多形状对拍与边界测试

**必须在多组不同形状上对拍**，而不只是导出时用的那一组。"""),
    code("""def run_graph(model, feeds, concrete):
    '''执行迷你图。'''
    env = dict(model.initializers)
    for k, v in feeds.items(): env[k] = v
    for n in model.nodes:
        spec = OPS[n.op_type]
        if spec['run'] is None:
            raise NotImplementedError(f'{n.op_type} 需要特殊处理（控制流/数据依赖形状）')
        env[n.output] = spec['run']([env[i] for i in n.inputs], n.attrs)
    return {o: env[o] for o in model.outputs}

def reference(x, W1, W2, g, b, eps=1e-5):
    h = x @ W1
    h = 0.5*h*(1+np.tanh(math.sqrt(2/math.pi)*(h+0.044715*h**3)))
    h = h @ W2
    return (h - h.mean(-1, keepdims=True))/np.sqrt(h.var(-1, keepdims=True)+eps)*g + b

# **含奇数、极小值、非对齐**的形状
TEST_SHAPES = [(1, 128), (2, 17), (8, 512), (3, 333), (1, 1), (5, 7)]
print(f"{'形状':<14s} {'最大绝对误差':>14s} {'通过'}")
all_ok = True
for bsz, seq in TEST_SHAPES:
    x = rng.normal(size=(bsz, seq, 8))
    got = run_graph(m, {'x': x}, {'batch': bsz, 'seq': seq})['y']
    ref = reference(x, m.initializers['W1'], m.initializers['W2'],
                    m.initializers['g'], m.initializers['b'])
    err = float(np.abs(got - ref).max())
    ok = err < 1e-10
    all_ok &= ok
    print(f'{str((bsz,seq)):<14s} {err:>14.2e} {"✅" if ok else "❌"}')
assert all_ok
print('\\n✅ 测试形状要**刻意包含**：batch=1、seq=1、奇数、非 8 倍数、极大值。')
print('   很多运行时（尤其 TensorRT）对对齐有隐含要求，只在非对齐形状上暴露。')
print('⚠️  别用 batch=1 做导出的样例输入 —— batch=1 与 batch>1 可能走不同代码路径。')"""),
    md("""## 6 · 量化对拍：容差要按量化误差设"""),
    code("""def quantize_int8(w, per_channel=False):
    '''对称量化：scale = max|w| / 127。'''
    if per_channel:
        s = np.abs(w).max(axis=0, keepdims=True) / 127.0
    else:
        s = np.array(np.abs(w).max() / 127.0)
    s = np.where(s == 0, 1e-12, s)
    q = np.clip(np.round(w / s), -127, 127)
    return q, s

def dequantize(q, s): return q * s

W = m.initializers['W1']
for name, pc in [('per-tensor', False), ('per-channel', True)]:
    q, s = quantize_int8(W, per_channel=pc)
    w_hat = dequantize(q, s)
    rel = float(np.abs(w_hat - W).max() / np.abs(W).max())
    print(f'{name:<14s} 权重最大相对误差 {rel:.4%}')
q_pt, s_pt = quantize_int8(W, False); q_pc, s_pc = quantize_int8(W, True)
err_pt = np.abs(dequantize(q_pt, s_pt) - W).max()
err_pc = np.abs(dequantize(q_pc, s_pc) - W).max()
assert err_pc <= err_pt, 'per-channel 量化误差不高于 per-tensor'
print(f'\\n✅ per-channel 误差 {err_pc:.5f} <= per-tensor {err_pt:.5f}（每列各有 scale）')

# ⚠️ 用浮点容差去对拍量化结果必然「失败」—— 但那不是 bug
x = rng.normal(size=(4, 32, 8))
ref = reference(x, W, m.initializers['W2'], m.initializers['g'], m.initializers['b'])
W_q = dequantize(*quantize_int8(W, True))
got = reference(x, W_q, m.initializers['W2'], m.initializers['g'], m.initializers['b'])
print(f'\\n量化后最大绝对误差: {np.abs(got-ref).max():.4e}')
print(f'  用 rtol=1e-5 判定: {np.allclose(got, ref, rtol=1e-5, atol=1e-6)}   ← 必然 False')
print(f'  用 rtol=2e-2 判定: {np.allclose(got, ref, rtol=2e-2, atol=2e-2)}')
assert not np.allclose(got, ref, rtol=1e-5, atol=1e-6)
print('\\n✅ 量化后的正确验证方式：')
print('   ① 对拍**最终任务指标**（准确率/BLEU）而不是逐元素数值')
print('   ② 逐层看「误差是否在预期量级」而不是「是否 allclose」')
print('   ③ 重点找**异常层**（误差比其他层大一个数量级 -> 它的激活有长尾）')"""),
    code("""# 找异常层：逐层量化误差的分布
def per_layer_quant_error(weights, per_channel=False):
    '''用**平均**误差 / 典型幅值(p90)。两个选择都是刻意的：
       · 用 mean 而非 max —— max 永远由离群值所在的那一格决定，看不出「其余权重被挤坏了多少」
       · 用 p90 而非 max 归一化 —— 用 max 归一化会被离群值自己掩盖'''
    out = {}
    for name, w in weights.items():
        if w.ndim < 2: continue
        w_hat = dequantize(*quantize_int8(w, per_channel))
        typical = float(np.percentile(np.abs(w), 90)) + 1e-12
        out[name] = float(np.abs(w_hat - w).mean() / typical)
    return out

heavy_tail = rng.normal(size=(8, 8)) * 0.3
heavy_tail[0, 0] = 50.0                       # 一个极端离群值 -> 量化范围被它撑爆
weights = {'W1': m.initializers['W1'], 'W2': m.initializers['W2'], 'W_bad': heavy_tail}
errs = per_layer_quant_error(weights, per_channel=False)
med = float(np.median(list(errs.values())))
print(f"{'层':<10s} {'相对量化误差 (per-tensor)':>24s}")
for k, v in errs.items():
    flag = '  ← ⚠️ 异常层' if v > 3 * med else ''
    print(f'{k:<10s} {v:>23.2%}{flag}')
assert errs['W_bad'] > 5 * errs['W1'], '含离群值的层量化误差应显著更大'
print('\\n⚠️  一个离群值（50.0）把整层的 scale 撑大了两个数量级 ——')
print('    于是**其余所有权重都被挤到极少数几个量化格子里**。')

errs_pc = per_layer_quant_error(weights, per_channel=True)
print(f'\\nW_bad 的误差: per-tensor {errs["W_bad"]:.2%} -> per-channel {errs_pc["W_bad"]:.2%}')
assert errs_pc['W_bad'] < errs['W_bad'] / 3, 'per-channel 应把损害限制在含离群值的那一列'
print('✅ per-channel 把损害**限制在含离群值的那一列**，其余列不受影响。')
print('✅ 所以要**逐层看误差分布**而不是只看端到端 ——')
print('   解法：per-channel 量化、离群值裁剪、或把该层留在 fp16。')"""),
    md("""## ✏️ 练习 1：导出前的 opset 与覆盖检查

实现 `export_precheck(model, target_runtime, target_opset)`：返回
`{'opset_ok':…, 'missing_ops': [...], 'partitions':…, 'ok':…}`。
`opset_ok` 要求 **model 里每个算子的 since <= target_opset**，且 `model.opset <= target_opset`。"""),
    code("""def export_precheck(model, target_runtime, target_opset):
    # TODO: ① 检查每个算子的 since <= target_opset 且 model.opset <= target_opset
    #       ② 用 RUNTIME_SUPPORT 求不支持的算子与分区数
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
r = export_precheck(m, 'onnxruntime-cpu', 20)
assert r['opset_ok'] and r['missing_ops'] == [] and r['ok'], r
r2 = export_precheck(m, 'tensorrt', 20)
assert 'Gelu' in r2['missing_ops'] and not r2['ok'] and r2['partitions'] > 1
r3 = export_precheck(m, 'onnxruntime-cpu', 15)
assert not r3['opset_ok'], 'Gelu(since 20) 与 LayerNorm(since 17) 都超过 opset 15'
r4 = export_precheck(decompose_gelu(m), 'tensorrt', 17)
assert r4['ok'], '分解掉 Gelu 后 TensorRT 应可全图支持'
for rt, ops_ in [('onnxruntime-cpu', 20), ('tensorrt', 20), ('tflite', 20)]:
    rr = export_precheck(m, rt, ops_)
    print(f'{rt:<18s} opset_ok={rr["opset_ok"]} missing={rr["missing_ops"]} '
          f'partitions={rr["partitions"]} -> {"✅" if rr["ok"] else "❌"}')
print('✅ 练习 1 通过：**部署前两分钟的检查**，能避免「转完才发现跑不动」')"""),
    md("""## ✏️ 练习 2：动态轴规划

实现 `plan_dynamic_axes(input_specs, varying_dims)`：`input_specs` 是
`{名字: (维度名列表)}`，`varying_dims` 是会变化的维度名集合（如 `{'batch','seq'}`）。
返回 `torch.onnx.export` 风格的 `dynamic_axes` 字典 `{名字: {轴下标: 轴名}}`。"""),
    code("""def plan_dynamic_axes(input_specs, varying_dims):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
specs = {'input_ids': ['batch', 'seq'], 'attention_mask': ['batch', 'seq'],
         'pixel_values': ['batch', 'channel', 'height', 'width']}
axes = plan_dynamic_axes(specs, {'batch', 'seq', 'height', 'width'})
assert axes['input_ids'] == {0: 'batch', 1: 'seq'}
assert axes['pixel_values'] == {0: 'batch', 2: 'height', 3: 'width'}, axes['pixel_values']
assert 1 not in axes['pixel_values'], 'channel 不在可变集合里，不应声明为动态'
assert plan_dynamic_axes(specs, set()) == {k: {} for k in specs}, '没有可变维时全为空'
print(json.dumps(axes, ensure_ascii=False, indent=2))
print('✅ 练习 2 通过：**先想清「什么会变」，再导出** —— 事后补是补不上的')"""),
    md("""## ✏️ 练习 3：量化容差

实现 `quant_tolerance(bits, per_channel)`：返回建议的 `(rtol, atol)`。
经验规则：`rtol ≈ 2 / (2^(bits-1) - 1)`，per-channel 可以再除以 2；
`atol = rtol`。`bits=16` 时用浮点容差 `1e-3`。"""),
    code("""def quant_tolerance(bits, per_channel=False):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
r8, a8 = quant_tolerance(8, per_channel=False)
r8c, _ = quant_tolerance(8, per_channel=True)
r4, _ = quant_tolerance(4)
r16, _ = quant_tolerance(16)
assert abs(r8 - 2/127) < 1e-9, f'int8 per-tensor 应约 {2/127:.4f}，得到 {r8}'
assert r8c < r8, 'per-channel 容差更紧'
assert r4 > r8, '位数越少容差越宽'
assert r16 <= 1e-3
print(f"{'配置':<24s} {'rtol':>10s}")
for bits, pc in [(16, False), (8, False), (8, True), (4, False)]:
    r_, _ = quant_tolerance(bits, pc)
    print(f'{f"int{bits} {"per-channel" if pc else "per-tensor"}":<24s} {r_:>10.5f}')
print('\\n✅ 练习 3 通过：**用 fp32 的容差去对拍 int8 结果必然「失败」——但那不是 bug**')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def export_precheck(model, target_runtime, target_opset):
    too_new = [n.op_type for n in model.nodes if OPS[n.op_type]['since'] > target_opset]
    opset_ok = (not too_new) and model.opset <= target_opset
    cov = coverage_report(model, target_runtime)
    return {'opset_ok': opset_ok, 'too_new_ops': sorted(set(too_new)),
            'missing_ops': cov['unsupported'], 'partitions': cov['partitions'],
            'ok': opset_ok and cov['fully_supported']}"""),
    code("""# 练习 2 参考答案
def plan_dynamic_axes(input_specs, varying_dims):
    return {name: {i: d for i, d in enumerate(dims) if d in varying_dims}
            for name, dims in input_specs.items()}"""),
    code("""# 练习 3 参考答案
def quant_tolerance(bits, per_channel=False):
    if bits >= 16:
        return 1e-3, 1e-3
    r = 2.0 / (2 ** (bits - 1) - 1)
    if per_channel:
        r /= 2.0
    return r, r"""),
    md("""---
## 🧪 真实 API 对照胶囊：一份可直接用的导出与验证脚本"""),
    code("""RECIPE = r'''
import torch, numpy as np, onnx, onnxruntime as ort

CKPT, ONNX_PATH, OPSET = "my-model", "model.onnx", 17     # ← 先查目标运行时的 opset 上限
model.eval()                                               # ① 关随机性（模块 02 的断言）
with torch.inference_mode():
    a, b = model(example), model(example)
    assert torch.equal(a, b), "还有未关闭的随机性（dropout/BN/自定义随机）"

# ② 导出：**样例输入用非特殊形状**（别用 batch=1）
example = (torch.randint(0, 1000, (2, 17)), torch.ones(2, 17, dtype=torch.long))
torch.onnx.export(
    model, example, ONNX_PATH,
    opset_version=OPSET,
    input_names=["input_ids", "attention_mask"], output_names=["logits"],
    dynamic_axes={"input_ids": {0: "batch", 1: "seq"},          # ③ 凡是会变的都声明
                  "attention_mask": {0: "batch", 1: "seq"},
                  "logits": {0: "batch"}},
    do_constant_folding=True,
)

# ④ 结构检查 + 算子清单（部署前两分钟）
m = onnx.load(ONNX_PATH); onnx.checker.check_model(m)
ops = sorted({n.op_type for n in m.graph.node})
print("opset:", m.opset_import[0].version, "| ops:", ops)
# 与目标运行时的支持列表求交集，提前发现「会静默回退」的算子

# ⑤ **多形状**数值对拍（含奇数、极小、非对齐、大 batch）
sess = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
for bsz, seq in [(1, 128), (2, 17), (8, 512), (3, 333), (1, 1)]:
    ids = torch.randint(0, 1000, (bsz, seq)); mask = torch.ones(bsz, seq, dtype=torch.long)
    with torch.inference_mode():
        ref = model(ids, mask).numpy()
    got = sess.run(None, {"input_ids": ids.numpy(), "attention_mask": mask.numpy()})[0]
    np.testing.assert_allclose(ref, got, rtol=1e-3, atol=1e-4,
                               err_msg=f"mismatch at {bsz}x{seq}")

# ⑥ 检查静默回退（TensorRT / CUDA EP）
sess_gpu = ort.InferenceSession(ONNX_PATH,
                                providers=["TensorrtExecutionProvider", "CPUExecutionProvider"])
print("实际使用的 providers:", sess_gpu.get_providers())
# TensorRT 日志里搜 "subgraph" —— 子图数 > 1 说明发生了回退

# ⑦ 写交付契约（模块 00 的 Contract）
CONTRACT = dict(opset=OPSET, dtype="float32", max_batch=64, max_seq=512,
                tolerance=dict(rtol=1e-3, atol=1e-4),
                notes=["seq 无需对齐（已在 3x333 上验证）",
                       "batch=1 走不同 kernel，延迟不成比例"])
'''
print(RECIPE)
for c in ['torch.equal', 'dynamic_axes', 'opset_version', 'check_model',
          'get_providers', 'CONTRACT', '(2, 17)']:
    assert c in RECIPE, c
print('✅ 配方覆盖：关随机性 / 非特殊样例 / 动态轴 / 结构检查 / 多形状对拍 / 回退检查 / 交付契约')"""),
    md("""### 小结
- **导出 = 把 Python 程序编译成受限 IR 上的静态图**。模块 01 的追踪语义全部适用，但在导出里
  它们是**正确性问题**（图交出去后再也不会重新追踪），不只是性能问题。
- **ONNX 的四要素**：静态拓扑、opset 版本、符号形状（动态轴）、内联权重。
- **不设动态轴 = 形状被写死**，「用 batch=1 导出、线上来 batch=8」是最常见的导出事故。
  **别用 batch=1 做样例输入**（它可能走不同代码路径）。
- **算子不支持的四条出路**：换算子 → 提 opset → 分解 → 自定义算子。**出路①成功率最高却常被跳过。**
- **形状依赖数值的算子**（NonZero/Unique/masked_select）在图 IR 里天然困难 →
  **通用解法：把动态部分挪到模型之外。**
- **静默回退**：TensorRT/CoreML/TFLite 遇到不支持的算子不报错，切子图交给别的后端 →
  「转了但没变快」。**看分区日志，不只看端到端延迟。**
- **多形状对拍是必需的**，测试形状要刻意含 batch=1、seq=1、奇数、非对齐、极大值。
- **量化的容差要按量化误差设**（int8 约 2/127），并**逐层找异常层**——一个离群值就能撑爆整层范围。

下一站：**模块 04 · 真机 GPU 工作流** —— 在真实硬件上诊断，而不是猜。"""),
]
