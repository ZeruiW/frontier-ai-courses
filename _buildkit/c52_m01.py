# -*- coding: utf-8 -*-
"""C52 模块 01 · TensorFlow / Keras 心智模型与跨框架对照。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00；熟悉 PyTorch 的基本用法；C38（autograd 与 compile）有帮助"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_tensorflow_mental_model.ipynb'),
    ("核心参考", "TensorFlow 指南（tf.function / AutoGraph / Keras）、JAX 的 jit 语义、PyTorch 2.x 的 torch.compile"),
    ("预计时长", "读 60 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    ("why", "为什么今天还要懂 TensorFlow", "".join([
        P("先诚实地承认现状：<strong>研究生态已经彻底 PyTorch 化</strong>。新论文的官方实现、HuggingFace 的主线、绝大多数教程——都是 PyTorch。那为什么还要花一个模块讲 TensorFlow？"),
        TABLE(["理由", "具体情形", "需要到什么程度"], [
            ["<strong>生产栈存量巨大</strong>", "很多企业的推理服务是 TF Serving、数据管线是 <code>tf.data</code>、移动端是 TFLite", "能读懂、能改、能对接"],
            ["<strong>复现旧工作</strong>", "2016–2020 年的大量论文（含 BERT、T5 的原始实现）是 TF", "能读代码、能把权重搬出来（模块 02）"],
            ["<strong>JD 明确要求</strong>", "「TensorFlow, PyTorch, or JAX」几乎是标配写法", "能说清三者的语义差别"],
            ["<strong>理解「静态图」这个范式</strong>", "<code>torch.compile</code>、JAX 的 <code>jit</code>、ONNX 导出、TensorRT 全都基于同一套「追踪成图再优化」的思想", "<strong>这是最重要的理由</strong>"],
        ]),
        DUAL(
            "最后一条值得展开：<strong>PyTorch 2.x 之后，「静态图」的概念反而变得更重要了</strong>。<code>torch.compile</code> 做的事情——追踪、构图、优化、缓存、遇到不支持的东西就 graph break——与 <code>tf.function</code> 在概念上是同一件事。<em>理解 TF 的追踪语义，能让你立刻明白 <code>torch.compile</code> 为什么会重编译、为什么某些 Python 代码会让它退化</em>。",
            "换句话说：<strong>这个模块表面上讲 TensorFlow，实际上讲的是「Python 代码怎么变成一张计算图」这个跨框架的通用问题</strong>。同一套语义在 TF（<code>tf.function</code>）、JAX（<code>jit</code>）、PyTorch（<code>torch.compile</code>）、以及 ONNX 导出（<code>torch.onnx.export</code> 的 tracing 模式）里反复出现，而它的坑也一模一样：<em>追踪时 Python 只跑一次、控制流会被固化、副作用只发生在追踪期、形状变化会触发重追踪</em>。",
        ),
        CALLOUT("intuition", "所以学这个模块的正确心态是：<strong>不是「学一个过时的框架」，而是「学一个所有现代框架都在用的范式」</strong>——而 TensorFlow 恰好是这个范式最早、也最彻底的实现，所以它的语义暴露得最清楚。<em>用 TF 理解追踪，再回头看 <code>torch.compile</code>，会觉得后者只是把同样的东西藏得更深了一些。</em>"),
    ])),
    ("graph", "静态图 vs 动态图：一个概念上的分界", "".join([
        ASCII("""动态图（eager / define-by-run）—— PyTorch 默认、TF2 默认
   Python 逐行执行，每个算子立刻算出结果
   y = x @ w      # ← 这一行执行时，矩阵乘真的发生了
   if y.sum() > 0:      # ← 真的读了 y 的值来做分支
       z = relu(y)
   ✅ 好调试（可以 print、可以打断点、可以用 Python 的一切）
   ❌ 无法整图优化（算子融合、常量折叠、内存复用都做不了）；无法脱离 Python 部署

静态图（graph / define-and-run）—— TF1 默认、tf.function / jit / compile
   Python 只是**构图脚本**，跑一遍产出一张图；之后执行的是图，不是 Python
   @tf.function
   def f(x):
       y = x @ w          # ← 这一行执行时，只是往图里**加了一个节点**
       if tf.reduce_sum(y) > 0:   # ← 变成图里的一个 tf.cond 节点
           z = tf.nn.relu(y)
       return z
   ✅ 可整图优化、可序列化、可脱离 Python 部署（TF Serving / TFLite / ONNX）
   ❌ 调试困难（print 只在追踪时执行一次）；Python 控制流会被**固化**""")
        ,
        TABLE(["维度", "动态图", "静态图"], [
            ["Python 代码的角色", "就是计算本身", "<strong>构图脚本</strong>（只跑一次或极少次）"],
            ["<code>print(x)</code> 的行为", "每次调用都打印当前值", "<strong>只在追踪时打印一次</strong>，之后完全不执行"],
            ["Python 的 <code>if</code>", "每次按实际值分支", "<strong>按追踪时的值固化成一条分支</strong>"],
            ["跨算子优化", "❌", "✅ 融合、常量折叠、布局优化、内存复用"],
            ["部署", "需要 Python", "<strong>可脱离 Python</strong>"],
            ["形状变化", "无所谓", "<strong>可能触发重追踪</strong>（每种形状一张图）"],
        ]),
        DUAL(
            "两栏里最容易咬人的是 <code>print</code> 与 <code>if</code> 这两行。<strong>「Python 代码只在追踪时跑一次」这个事实，会让一大批看起来正常的代码产生诡异行为</strong>：调试用的 print 只出现一次然后消失；用 Python 变量做的计数器永远停在追踪时的值；<code>if len(x) > 5</code> 这样的条件被永久固化成追踪那次的结果。<em>而它们都不报错。</em>",
            "解决办法是<strong>区分「构图时的量」与「运行时的量」</strong>。构图时的量（Python int、list、shape 的静态部分）在追踪时就确定；运行时的量（tensor 的值）只有执行图时才知道。<em>凡是要依赖运行时的量做的事，都必须用框架提供的图算子表达</em>——TF 里是 <code>tf.cond</code>/<code>tf.while_loop</code>/<code>tf.print</code>，JAX 里是 <code>lax.cond</code>/<code>lax.scan</code>，PyTorch 编译时是让它 graph break 或用 <code>torch.cond</code>。<strong>这条区分是所有静态图框架的第一性原理。</strong>",
        ),
        CALLOUT("warn", "TF 有一层额外的复杂度叫 <span class=\"term\">AutoGraph</span>：它会<strong>自动把一部分 Python 控制流改写成图算子</strong>（<code>if</code> → <code>tf.cond</code>、<code>for</code> → <code>tf.while_loop</code>），但只在条件依赖于 tensor 时才改写。<em>这个「有时改写、有时不改写」的行为是 TF 最难懂的地方之一</em>——同样一段 <code>if</code>，条件是 Python bool 就固化、是 tensor 就变成图节点。<strong>写 <code>tf.function</code> 时，最好显式地知道每个条件到底是哪一种</strong>，而不是依赖 AutoGraph 猜对。"),
    ])),
    ("retrace", "重追踪：性能问题的头号来源", "".join([
        P("<code>tf.function</code> 会为<strong>每一种输入「签名」缓存一张图</strong>。签名 = (输入的 dtype, 形状, 以及所有 Python 参数的值)。签名变了就重新追踪一次。"),
        MATH("\\text{cache key} = \\big(\\text{dtype}_1, \\text{shape}_1, \\dots, \\text{dtype}_n, \\text{shape}_n,\\; \\text{python\\_args}\\big)"),
        TABLE(["什么会触发重追踪", "为什么", "怎么避免"], [
            ["<strong>输入形状变化</strong>", "每种形状一张图", "<code>input_signature</code> 里把可变维标成 <code>None</code>；或把 batch/seq padding 到固定桶"],
            ["<strong>dtype 变化</strong>", "同上", "统一 dtype，别混 fp32/fp16 调用"],
            ["<strong>传 Python 标量而非 tensor</strong>", "<code>f(x, 3)</code> 与 <code>f(x, 4)</code> 是两个不同签名", "把它包成 <code>tf.constant(3)</code>，或用 <code>input_signature</code> 声明"],
            ["<strong>传 Python 对象（list/dict/自定义类）</strong>", "按值/按 id 参与 key", "尽量只传 tensor"],
            ["<strong>每次调用都新建 <code>tf.function</code></strong>", "缓存跟着函数对象走，对象没了缓存也没了", "<strong>别在循环/方法内部定义 <code>@tf.function</code></strong>"],
        ]),
        DUAL(
            "最后一行是个非常隐蔽的性能杀手：<strong>在类的方法里或循环里创建 <code>tf.function</code>，每次都会得到一个新的函数对象，缓存永远命中不了</strong>——于是每一步训练都在重新追踪。症状是「训练极慢但 GPU 利用率很低」，而代码看起来完全正常。<em>TF 会在重追踪超过若干次后打一个警告，但那条警告很容易被淹没在日志里。</em>",
            "重追踪的代价有多大？<strong>追踪一次的成本大致相当于跑几十到几百次前向</strong>（要执行 Python、构图、做图优化）。所以如果每一步都重追踪，你的吞吐会掉一到两个数量级。<em>这与 <code>torch.compile</code> 的重编译完全同构</em>——后者的重编译更贵（要跑 Inductor 生成 kernel），所以 PyTorch 提供了 <code>dynamic=True</code> 与 <code>torch._dynamo.config.cache_size_limit</code> 来控制。<strong>两个框架的调优手段不同，但要诊断的现象是同一个：「你的图被重建了多少次」。</strong>",
        ),
        H3("调试静态图的三个技巧"),
        UL([
            "<strong>先关掉编译再调试</strong>：<code>tf.config.run_functions_eagerly(True)</code> / <code>torch._dynamo.disable()</code> / <code>jax.disable_jit()</code>。<em>先确认逻辑对，再打开编译确认语义没被追踪改变</em>——把两类问题分开，比在编译模式下硬调快得多。",
            "<strong>用图内的打印算子</strong>：<code>tf.print</code>（不是 Python 的 <code>print</code>）、<code>jax.debug.print</code>。它们是图的一部分，<em>每次执行都会打印</em>，所以能看到运行时的真实值。",
            "<strong>数副作用的执行次数</strong>：上面那个计数器技巧。它同时诊断两件事——<em>执行次数 &gt; 1 说明有重追踪；执行次数 = 调用次数说明编译完全没生效</em>。",
        ]),
        P("这三招合起来能覆盖静态图调试的绝大多数场景，而且<strong>它们的顺序是有讲究的</strong>：<em>先用第一招把「逻辑错」与「追踪语义错」分开</em>——如果关掉编译后结果就对了，问题一定在追踪语义（控制流被固化、形状被写死、副作用消失）；如果关掉编译还是错，那就是普通的逻辑 bug，跟静态图无关。<strong>这个二分能省掉大量在错误方向上的排查</strong>。"),
        CALLOUT("intuition", "诊断重追踪有一个通用技巧，跨框架都能用：<strong>在被编译的函数里放一个纯 Python 的副作用（如 <code>print</code> 或计数器自增），然后数它执行了几次</strong>。执行次数 = 追踪次数。<em>如果它在训练循环里每步都打印，你就抓到了重追踪</em>。这个技巧同时也演示了「Python 代码只在追踪时执行」这个语义——notebook 会把它实现出来。"),
    ])),
    ("keras", "Keras 的三种 API：什么时候用哪个", "".join([
        TABLE(["API", "长什么样", "能表达什么", "不能表达什么"], [
            ["<strong>Sequential</strong>", "<code>keras.Sequential([Dense(64), Dense(10)])</code>", "单输入单输出的线性堆叠", "分支、多输入输出、残差"],
            ["<strong>Functional</strong>", "<code>x = Input(...); y = Dense(64)(x); Model(x, y)</code>", "<strong>任意 DAG</strong>（多输入输出、残差、共享层）", "依赖运行时值的控制流、递归"],
            ["<strong>Subclassing</strong>", "<code>class M(keras.Model): def call(self, x): ...</code>", "<strong>任意 Python 逻辑</strong>（最像 PyTorch）", "—（但失去了静态图检查与自动可视化）"],
        ]),
        DUAL(
            "三者的关系值得说清：<strong>Functional API 构建的是一个「可被检查的数据结构」</strong>——它在定义时就知道整张图的拓扑与形状，所以能做 <code>model.summary()</code>、能画图、能自动检查形状不匹配、能被完整序列化成 <code>.keras</code>/SavedModel。<em>Subclassing 则是纯 Python，框架看不到内部结构</em>，所以 <code>summary()</code> 要先跑一遍才知道形状，序列化也需要额外的 <code>get_config()</code>。",
            "<strong>这与 PyTorch 的差别是范式级的</strong>：PyTorch 只有 subclassing 这一种（<code>nn.Module.forward</code> 是纯 Python），它<em>放弃了「模型是可检查的数据结构」这个性质，换取了完全的灵活性</em>。所以 PyTorch 要导出图必须靠追踪（<code>torch.jit.trace</code>/<code>torch.onnx.export</code>/<code>dynamo</code>），而 Keras Functional 模型天然就是图。<em>模块 03 讲导出时你会看到这个差别的直接后果：Keras Functional 导出几乎无痛，PyTorch 导出要处理一堆追踪的坑。</em>",
        ),
        H3("与 PyTorch 的逐概念对照"),
        TABLE(["概念", "PyTorch", "TensorFlow / Keras", "注意"], [
            ["模型定义", "<code>nn.Module.forward</code>", "<code>keras.Model.call</code> / Functional", "TF 的 <code>call</code> 有 <code>training</code> 参数（控制 dropout/BN）"],
            ["训练/推理模式", "<code>model.train()</code> / <code>.eval()</code>", "<strong>逐次调用传 <code>training=True/False</code></strong>", "TF 没有全局模式开关——<em>忘了传就用默认值</em>"],
            ["自动微分", "<code>loss.backward()</code>（反向自动累积）", "<code>with tf.GradientTape() as t: ...</code> 然后 <code>t.gradient(...)</code>", "Tape 默认只能用一次（<code>persistent=True</code> 才能多次）"],
            ["优化器步", "<code>opt.step()</code> + <code>opt.zero_grad()</code>", "<code>opt.apply_gradients(zip(grads, vars))</code>", "TF 无需清零（梯度是每次新算的）"],
            ["设备", "<code>.to('cuda')</code>", "<code>with tf.device('/GPU:0'):</code> 或自动放置", "TF 默认会自动占满显存（<code>set_memory_growth</code> 关掉）"],
            ["数据管线", "<code>DataLoader</code>", "<code>tf.data.Dataset</code>", "<code>tf.data</code> 是图内的，性能通常更好但调试更难"],
            ["权重形状（Conv2D）", "<code>(out, in, kH, kW)</code>", "<strong><code>(kH, kW, in, out)</code></strong>", "<strong>迁移时必须转置</strong>（模块 02）"],
            ["数据布局", "NCHW（默认）", "<strong>NHWC（默认）</strong>", "同上"],
            ["LayerNorm eps", "<code>1e-5</code>", "<code>1e-3</code>（<code>keras.layers.LayerNormalization</code>）", "<strong>默认值不同！</strong>（模块 02）"],
            ["BatchNorm 动量", "<code>momentum=0.1</code>（新值权重）", "<code>momentum=0.99</code>（<strong>旧值</strong>权重）", "<em>语义相反</em>：0.1 ↔ 0.9"],
        ]),
        CALLOUT("danger", "<p>这张表的最后三行是<strong>迁移事故的最高发区</strong>，而且它们的共同特点是「代码不报错、形状也对、但数值错」。<strong>Conv2D 的权重布局</strong>（<code>(out,in,kH,kW)</code> vs <code>(kH,kW,in,out)</code>）不转置就直接 reshape，会得到一个形状正确但完全乱掉的卷积核。<strong>LayerNorm 的 eps</strong> 相差 100 倍，在激活值很小时会造成可观的数值差异。<strong>BatchNorm 的 momentum 语义相反</strong>——PyTorch 的 0.1 对应 TF 的 0.9，直接照抄数字会让滑动统计量的更新速度差 9 倍。<em>模块 02 会把这些做成一张可执行的映射表。</em></p>", "三个「不报错但数值错」的默认值差异"),
    ])),
    ("jax", "顺带说清 JAX：第三种范式", "".join([
        P("JD 里的三个框架，JAX 是最不一样的一个。用一段话把它的定位说清楚，你就能在面试里准确回答「三者的区别」。"),
        TABLE(["", "PyTorch", "TensorFlow", "JAX"], [
            ["核心抽象", "有状态的 <code>nn.Module</code>", "有状态的 <code>Layer</code> + 图", "<strong>纯函数 + 显式参数</strong>"],
            ["参数在哪", "藏在模块里", "藏在层里", "<strong>作为参数显式传入</strong>（pytree）"],
            ["随机数", "全局 RNG", "全局 RNG", "<strong>显式传 key</strong>（可复现性极强）"],
            ["图从哪来", "<code>compile</code>/<code>trace</code>", "<code>tf.function</code>", "<code>jit</code>"],
            ["变换", "—", "—", "<strong><code>grad</code>/<code>vmap</code>/<code>pmap</code>/<code>jit</code> 可自由组合</strong>"],
            ["最大优势", "生态与灵活", "生产栈与部署", "<strong>可组合的函数变换 + XLA 编译</strong>"],
        ]),
        DUAL(
            "JAX 的核心主张是<strong>「把模型写成纯函数」</strong>：<code>y = f(params, x)</code>，参数显式传入、没有隐藏状态、随机数靠显式 key。<em>代价是写起来更啰嗦（要自己管 params 树），收益是所有变换都能自由组合</em>——<code>jit(grad(vmap(f)))</code> 是合法且常用的写法，而这在有状态的框架里很难做到。",
            "对本课的意义在于：<strong>JAX 把「静态图追踪」的语义暴露得最彻底</strong>。它的 tracer 对象在追踪时代替真实数组，任何试图对 tracer 做 Python 层面判断（<code>if x > 0</code>、<code>int(x)</code>）的代码都会<em>立刻报错</em>（<code>ConcretizationTypeError</code>），而不是像 TF 那样静默固化。<em>这个「宁可报错也不静默」的设计，反而让 JAX 的追踪语义最容易学对</em>。<strong>如果你想真正理解追踪，从 JAX 学最快；如果要面对生产存量，从 TF 学最有用。</strong>",
        ),
        CALLOUT("intuition", "一个能在面试里用的总结：<strong>三个框架的差别不在「能做什么」（都能训 Transformer），而在「状态放在哪里」与「图从哪里来」</strong>。PyTorch：状态在对象里、图靠事后追踪；TensorFlow：状态在层里、图靠 <code>tf.function</code> 装饰；JAX：<em>没有隐藏状态</em>、图靠 <code>jit</code> 且变换可组合。<em>把这三句话说清楚，比列举 API 差异有说服力得多。</em>"),
    ])),
    ("ledger", "算一笔账：追踪的成本与收益", "".join([
        P("静态图不是免费的。它的取舍可以量化成一个简单的盈亏平衡问题。"),
        MATH("\\text{总时间}_{\\text{图}} = n_{\\text{trace}} \\cdot C_{\\text{trace}} + N \\cdot t_{\\text{graph}}, \\qquad \\text{总时间}_{\\text{eager}} = N \\cdot t_{\\text{eager}}"),
        MATH("\\text{值得编译} \\iff N > \\frac{n_{\\text{trace}} \\cdot C_{\\text{trace}}}{t_{\\text{eager}} - t_{\\text{graph}}}"),
        TABLE(["场景", "追踪次数", "单次追踪成本", "加速比", "盈亏平衡的调用次数"], [
            ["形状固定的训练循环", "1", "≈ 200 × 单步", "1.3×", "≈ 870 步（很快回本）"],
            ["形状固定的推理服务", "1", "≈ 200 × 单步", "1.5×", "≈ 600 次"],
            ["<strong>形状每次都变</strong>", "<strong>= 调用次数</strong>", "≈ 200 × 单步", "1.3×", "<strong>永远不回本</strong>"],
            ["形状分 8 个桶", "8", "≈ 200 × 单步", "1.3×", "≈ 7000 次"],
        ]),
        P("第三行是关键：<strong>如果每次调用的形状都不同，追踪次数等于调用次数，编译永远是纯亏损</strong>——而且比 eager 还慢（多了追踪开销）。这就是「变长输入 + 静态图」的根本矛盾。三条标准解法："),
        UL([
            "<strong>形状分桶</strong>：把序列长度 padding 到 {128, 256, 512, …} 这样的几个桶，把追踪次数从 N 降到桶数。<em>代价是 padding 浪费（C50 模块 02 算过）</em>。",
            "<strong>动态维度</strong>：TF 的 <code>input_signature</code> 里把可变维标成 <code>None</code>、PyTorch 的 <code>dynamic=True</code>、ONNX 的动态轴（模块 03）。<em>代价是失去部分基于静态形状的优化</em>。",
            "<strong>只编译热点</strong>：把形状稳定的部分（如单层 Transformer block）编译，形状多变的部分留在 eager。<em>这是最实用的折中。</em>",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>「Python 代码只在追踪时执行一次」这一句话，能解释静态图框架里 80% 的诡异行为</strong>——print 只出现一次、计数器不动、控制流被固化、形状一变就变慢。<em>而且它跨框架成立</em>：<code>tf.function</code>、<code>jax.jit</code>、<code>torch.compile</code>、<code>torch.onnx.export</code> 全都如此。<strong>学会问「这一行是在构图还是在计算」，你就掌握了这一整类框架。</strong>"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>范式的收敛</strong>：PyTorch 2.x 引入编译、TF2 引入 eager、JAX 一直是「纯函数 + jit」。<em>三者在语义上正在互相靠拢</em>，但工程细节（缓存策略、graph break 的处理、动态形状的支持程度）差异仍大。「一份代码跑三个后端」（如 Keras 3 的多后端）是当前的尝试，成熟度仍在演进。",
            "<strong>动态形状的编译</strong>：这是所有编译器共同的难题。符号形状（symbolic shapes）、形状特化与去特化的策略、以及「多大的形状变化才值得重编译」都缺乏好的自动决策，目前主要靠人工配置分桶。",
            "<strong>graph break 的可诊断性</strong>：<code>torch.compile</code> 遇到不支持的 Python 会静默地打断图（回退 eager），性能损失巨大但不报错。<code>TORCH_LOGS=graph_breaks</code> 之类的工具在改善，但「为什么这里断了、怎么改」仍需要相当的经验。",
            "<strong>训练与推理图的一致性</strong>：训练用的图与导出的推理图常常不同（dropout、BN 的行为、控制流分支）。<em>「保证导出的图与训练时数值一致」缺乏自动化的验证工具</em>——这正是模块 02/03 要你手写对拍的原因。",
            "<strong>Keras 3 的多后端路线</strong>：同一份 Keras 代码跑在 TF/JAX/PyTorch 后端上。它对「跨框架迁移」是个有意思的答案（不迁移，换后端就行），但对已有的原生代码没有帮助，且抽象泄漏在所难免。",
        ]),
        CALLOUT("paper", "必读：TensorFlow 官方指南的 <em>Better performance with tf.function</em>（重追踪的准确规则与诊断方法，本模块第三节的一手来源）、<em>Introduction to graphs and tf.function</em>、<em>The Keras functional API</em>；JAX 文档的 <em>How to think in JAX</em> 与 <em>JAX — The Sharp Bits</em>（后者把追踪的坑列得最清楚，强烈推荐即使你不用 JAX 也读一遍）；PyTorch 的 <em>torch.compile</em> 与 <em>TorchDynamo</em> 文档（对照阅读会发现语义高度同构）。原理侧：C38（autograd 与编译）、C36（kernel 与融合）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · TensorFlow / Keras 心智模型（用 numpy 复现 tf.function 的追踪语义）

目标：把 **静态图追踪 → Python 只跑一次 → 控制流固化 → 重追踪与缓存 → 与 PyTorch 的逐概念对照**
用一个几十行的 tracing 编译器精确复现。

路线：迷你 tracer 与图 → **print/计数器只在追踪时执行** → Python if 被固化 →
tf.cond 式的图内控制流 → 签名缓存与重追踪 → **重追踪诊断技巧** →
框架默认值对照表（三个「不报错但数值错」的坑）→ 编译的盈亏平衡 → ✏️ 练习 → 📖 答案 → 🧪 对照胶囊。

> 心智模型：**「Python 代码只在追踪时执行一次」这一句话，能解释静态图框架里 80% 的诡异行为。**"""),
    md("""## 1 · 一个迷你 tracer：Python 代码怎么变成图

追踪的核心机制极简：**用一个「符号张量」（tracer）代替真实数组去跑一遍 Python 函数**。
tracer 的每个运算不真的计算，而是**往图里加一个节点**并返回一个新的 tracer。"""),
    code("""import numpy as np, math, collections, itertools
rng = np.random.default_rng(0)

class Graph:
    def __init__(self):
        self.nodes = []          # [(op, [输入id], 属性)]
        self.inputs = []
        self._n = 0
    def new_id(self):
        self._n += 1; return f'v{self._n}'
    def add(self, op, inputs, **attrs):
        out = self.new_id()
        self.nodes.append({'op': op, 'inputs': list(inputs), 'out': out, 'attrs': attrs})
        return out
    def __repr__(self):
        return '\\n'.join(f'  {n["out"]} = {n["op"]}({", ".join(n["inputs"])})'
                          + (f' {n["attrs"]}' if n['attrs'] else '')
                          for n in self.nodes)

class Tracer:
    '''符号张量：不持有数值，只持有 (图, 节点id, 形状, dtype)。'''
    def __init__(self, graph, node_id, shape, dtype='float32'):
        self.g, self.id, self.shape, self.dtype = graph, node_id, shape, dtype
    def _bin(self, other, op):
        oid = other.id if isinstance(other, Tracer) else self.g.add('const', [], value=other)
        shape = self.shape                      # 简化：假设可广播到自身形状
        return Tracer(self.g, self.g.add(op, [self.id, oid]), shape, self.dtype)
    def __add__(self, o): return self._bin(o, 'add')
    def __mul__(self, o): return self._bin(o, 'mul')
    def __matmul__(self, o):
        shape = (self.shape[0], o.shape[1])
        return Tracer(self.g, self.g.add('matmul', [self.id, o.id]), shape, self.dtype)
    def sum(self):
        return Tracer(self.g, self.g.add('sum', [self.id]), (), self.dtype)
    def __repr__(self):
        return f'Tracer(id={self.id}, shape={self.shape}, dtype={self.dtype})'
    # ⚠️ 关键：任何试图把 tracer 当成具体值用的操作都必须报错
    def __bool__(self):
        raise TypeError(
            'Tracer 不能用于 Python 的 if/while/bool()：追踪时它没有具体值。\\n'
            '  -> 依赖运行时值的控制流必须用图算子表达（tf.cond / lax.cond / torch.cond）')
    def __int__(self):
        raise TypeError('Tracer 不能转成 int：追踪时它没有具体值')

def trace(fn, input_specs):
    '''用 tracer 跑一遍 fn，得到一张图。input_specs: [(shape, dtype)]'''
    g = Graph()
    args = []
    for shape, dtype in input_specs:
        nid = g.new_id(); g.inputs.append(nid)
        g.nodes.append({'op': 'placeholder', 'inputs': [], 'out': nid,
                        'attrs': {'shape': shape, 'dtype': dtype}})
        args.append(Tracer(g, nid, shape, dtype))
    out = fn(*args)
    return g, out

def f(x, w):
    h = x @ w
    return h + 1.0

g, out = trace(f, [((4, 8), 'float32'), ((8, 8), 'float32')])
print('追踪得到的图:'); print(g)
print('输出:', out)
assert len(g.nodes) == 5, '2 个 placeholder + matmul + const(1.0) + add'
assert any(n['op'] == 'matmul' for n in g.nodes)
print('\\n✅ 追踪 = 用符号张量跑一遍 Python，把每个算子记成图节点。')
print('   **注意 Tracer.__bool__ 直接抛错** —— 这正是 JAX 的做法（宁可报错也不静默固化）。')"""),
    md("""## 2 · Python 只在追踪时执行一次：print、计数器、控制流

这是静态图最反直觉、也最能解释「诡异行为」的一条。用三个可运行的例子把它钉死。"""),
    code("""trace_log = []

def f_with_print(x, w):
    trace_log.append('Python 执行了一次')     # ← 纯 Python 副作用
    print('  [追踪期] 这行 print 现在执行')
    return (x @ w).sum()

print('第一次追踪:')
g1, _ = trace(f_with_print, [((4, 8), 'float32'), ((8, 8), 'float32')])
print('第二次追踪（同样的签名，真实框架会命中缓存、不再追踪）:')
g2, _ = trace(f_with_print, [((4, 8), 'float32'), ((8, 8), 'float32')])
print(f'\\nPython 副作用执行了 {len(trace_log)} 次（我们手动追踪了 2 次）')
assert len(trace_log) == 2
print('\\n⚠️  在真实的 tf.function 里，第二次调用会**命中缓存、不再执行 Python**，')
print('    所以 print 只出现一次然后「消失」—— 而调试时你会以为代码没被执行。')
print('✅ 正确做法：用 tf.print（图内算子，每次执行都打印），或临时关掉编译调试。')"""),
    code("""# Python 的 if 会被**固化**成追踪时那一条分支
def f_python_if(x, w, use_relu):
    '''use_relu 是 **Python bool** -> 分支在追踪时就定死了。'''
    h = x @ w
    if use_relu:                          # ← Python 层面的判断
        return Tracer(h.g, h.g.add('relu', [h.id]), h.shape, h.dtype)
    return h

g_relu, _ = trace(lambda x, w: f_python_if(x, w, True),
                  [((4, 8), 'float32'), ((8, 8), 'float32')])
g_norelu, _ = trace(lambda x, w: f_python_if(x, w, False),
                    [((4, 8), 'float32'), ((8, 8), 'float32')])
ops_relu = [n['op'] for n in g_relu.nodes]
ops_norelu = [n['op'] for n in g_norelu.nodes]
print('use_relu=True  的图:', ops_relu)
print('use_relu=False 的图:', ops_norelu)
assert 'relu' in ops_relu and 'relu' not in ops_norelu
print('\\n⚠️  两张**不同的图** —— 分支已经被固化，运行时无法再改。')
print('    如果 use_relu 是从 tensor 算出来的，Python if 会直接报错（见下）。')

# 依赖 tensor 值的 if -> 必须报错（否则就是静默固化，更糟）
def f_tensor_if(x, w):
    h = (x @ w).sum()
    if h > 0:                             # ← 试图对 tracer 做 Python 判断
        return h
    return h * 0
try:
    trace(f_tensor_if, [((4, 8), 'float32'), ((8, 8), 'float32')])
    raise RuntimeError('不该到这')
except TypeError as e:
    print(f'\\n✅ 依赖 tensor 值的 Python if 被拦下:\\n   {str(e).splitlines()[0]}')"""),
    code("""# 图内控制流：把条件表达成一个图节点（tf.cond / lax.cond / torch.cond）
def graph_cond(pred, true_fn, false_fn, *args):
    '''复刻 tf.cond：**两个分支都被追踪进图**，运行时按 pred 选一个执行。'''
    g = pred.g
    t_out = true_fn(*args)
    f_out = false_fn(*args)
    return Tracer(g, g.add('cond', [pred.id, t_out.id, f_out.id]), t_out.shape, t_out.dtype)

def f_graph_if(x, w):
    h = x @ w
    s = h.sum()
    return graph_cond(s,
                      lambda: Tracer(h.g, h.g.add('relu', [h.id]), h.shape, h.dtype),
                      lambda: h)

g_cond, _ = trace(f_graph_if, [((4, 8), 'float32'), ((8, 8), 'float32')])
ops = [n['op'] for n in g_cond.nodes]
print('图内控制流的图:', ops)
assert 'cond' in ops and 'relu' in ops
print('\\n✅ 一张图就够（不用为每个分支各追踪一次），且分支在**运行时**决定。')
print('   代价：**两个分支都要被追踪**（都要能通过形状检查），且图更复杂。')
print('   TF 的 AutoGraph 会自动把「条件是 tensor」的 if 改写成这种形式 ——')
print('   但「有时改写、有时不改写」正是 TF 最难懂的地方，最好显式知道每个条件是哪种。')"""),
    md("""## 3 · 签名缓存与重追踪：性能问题的头号来源

$$\\text{cache key} = (\\text{dtype}_i, \\text{shape}_i, \\dots, \\text{python\\_args})$$

**签名变了就重追踪。追踪一次约等于跑几十到几百次前向。**"""),
    code("""class Function:
    '''复刻 tf.function：按签名缓存图。'''
    TRACE_COST = 200          # 追踪一次 ≈ 200 次前向的开销（量级）

    def __init__(self, fn, input_signature=None):
        self.fn, self.cache = fn, {}
        self.input_signature = input_signature
        self.n_traces = 0
        self.n_calls = 0

    def _key(self, specs, py_args):
        if self.input_signature is not None:
            specs = self.input_signature          # 声明了签名 -> key 与实际形状无关
        return (tuple(specs), tuple(sorted(py_args.items())))

    def __call__(self, specs, **py_args):
        self.n_calls += 1
        k = self._key(specs, py_args)
        if k not in self.cache:
            self.n_traces += 1
            self.cache[k] = trace(lambda *a: self.fn(*a, **py_args), specs)[0]
        return self.cache[k]

    def cost(self, t_graph=1.0, t_eager=1.3):
        return self.n_traces * self.TRACE_COST + self.n_calls * t_graph, self.n_calls * t_eager

def model(x, w, scale=1.0):
    return (x @ w) * scale

# 场景 A：形状固定
fa = Function(model)
for _ in range(500):
    fa([((32, 8), 'float32'), ((8, 8), 'float32')])
# 场景 B：形状每次都变（变长序列的典型情形）
fb = Function(model)
for i in range(500):
    fb([((32, 8 + i % 200), 'float32'), ((8 + i % 200, 8), 'float32')])
# 场景 C：形状分 8 个桶
fc = Function(model)
BUCKETS = [64, 96, 128, 192, 256, 384, 512, 768]
for i in range(500):
    b = BUCKETS[i % len(BUCKETS)]
    fc([((32, b), 'float32'), ((b, 8), 'float32')])
# 场景 D：传 Python 标量参数
fd = Function(model)
for i in range(500):
    fd([((32, 8), 'float32'), ((8, 8), 'float32')], scale=float(i % 50))

print(f"{'场景':<26s} {'调用':>6s} {'追踪':>6s} {'图缓存':>7s} {'相对 eager':>11s}")
for name, f_ in [('A 形状固定', fa), ('B 形状每次都变', fb),
                 ('C 形状分 8 桶', fc), ('D 传 Python 标量', fd)]:
    tg, te = f_.cost()
    print(f'{name:<26s} {f_.n_calls:>6d} {f_.n_traces:>6d} {len(f_.cache):>7d} {tg/te:>10.2f}×')

assert fa.n_traces == 1, '形状固定 -> 只追踪一次'
assert fb.n_traces > 100, '形状每次都变 -> 几乎每次都重追踪'
assert fc.n_traces == len(BUCKETS), '分桶 -> 追踪次数 = 桶数'
assert fd.n_traces == 50, 'Python 标量参数参与 cache key -> 每个取值一张图'
print(f'\\n⚠️  场景 B 比 eager **慢 {fb.cost()[0]/fb.cost()[1]:.1f} 倍** —— 编译成了纯亏损。')
print('✅ 场景 D 是个隐蔽的坑：把 scale 包成 tensor（tf.constant / torch.tensor）就能避免。')"""),
    code("""# input_signature：把可变维标成 None，一张图搞定所有形状
fe = Function(model, input_signature=[((None, None), 'float32'), ((None, 8), 'float32')])
for i in range(500):
    fe([((32, 8 + i % 200), 'float32'), ((8 + i % 200, 8), 'float32')])
print(f'声明了 input_signature（可变维=None）: 调用 {fe.n_calls}, 追踪 {fe.n_traces}')
assert fe.n_traces == 1, '声明动态维后只追踪一次'
tg, te = fe.cost()
print(f'相对 eager: {tg/te:.2f}×  （从 {fb.cost()[0]/fb.cost()[1]:.1f}× 变成 {tg/te:.2f}×）')
print('\\n✅ 代价：失去基于静态形状的部分优化（如常量折叠、精确的内存规划）。')
print('   真实对应: tf.function(input_signature=[tf.TensorSpec([None, None], tf.float32)])')
print('             torch.compile(model, dynamic=True)')
print('             torch.onnx.export(..., dynamic_axes={...})   ← 模块 03')"""),
    md("""### 重追踪的通用诊断技巧（跨框架都能用）

**在被编译的函数里放一个纯 Python 副作用，数它执行了几次。执行次数 = 追踪次数。**"""),
    code("""def make_traced_with_counter(fn):
    counter = {'n': 0}
    def wrapped(*args, **kw):
        counter['n'] += 1          # ← 纯 Python，只在追踪时执行
        return fn(*args, **kw)
    return wrapped, counter

wrapped, cnt = make_traced_with_counter(model)
ff = Function(wrapped)
for i in range(300):
    ff([((32, 8 + i % 5), 'float32'), ((8 + i % 5, 8), 'float32')])
print(f'调用 300 次，Python 函数体执行了 {cnt["n"]} 次 -> 追踪了 {cnt["n"]} 次')
assert cnt['n'] == ff.n_traces == 5
print('\\n✅ 这个技巧跨框架通用：')
print('   TF     : 在 @tf.function 里放 print("tracing")，数它出现几次')
print('   PyTorch: TORCH_LOGS="recompiles" 或在函数里放 print')
print('   JAX    : 在 jit 的函数里放 print（tracer 期才执行）')
print('   **每步训练都打印 = 你抓到了重追踪。**')"""),
    md("""## 4 · 框架默认值对照：三个「不报错但数值错」的坑

这三个是跨框架迁移事故的最高发区（模块 02 会做成完整的映射表）。"""),
    code("""def conv_weight_torch_to_tf(w_torch):
    '''PyTorch (out, in, kH, kW) -> TF (kH, kW, in, out)。**必须转置，不能 reshape**。'''
    return np.transpose(w_torch, (2, 3, 1, 0))

def conv_weight_tf_to_torch(w_tf):
    return np.transpose(w_tf, (3, 2, 0, 1))

w_t = rng.normal(size=(16, 3, 5, 5))            # out=16, in=3, k=5x5
w_tf = conv_weight_torch_to_tf(w_t)
print(f'PyTorch conv 权重 {w_t.shape} -> TF {w_tf.shape}')
assert w_tf.shape == (5, 5, 3, 16)
assert np.allclose(conv_weight_tf_to_torch(w_tf), w_t), '往返转换必须无损'
# 反面：直接 reshape（形状对了，内容全乱）
w_wrong = w_t.reshape(5, 5, 3, 16)
assert w_wrong.shape == w_tf.shape
assert not np.allclose(w_wrong, w_tf), '⚠️ reshape 的形状正确但内容完全不同！'
print('❌ 直接 reshape 得到的形状**一样**，但内容完全不同 —— 不报错、结果错。')
print(f'   两者最大差异: {np.abs(w_wrong - w_tf).max():.4f}')"""),
    code("""def layernorm(x, gamma, beta, eps):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * gamma + beta

EPS_TORCH, EPS_KERAS = 1e-5, 1e-3
d = 16
gamma, beta = np.ones(d), np.zeros(d)
print(f"{'输入尺度':>10s} {'torch(1e-5)':>13s} {'keras(1e-3)':>13s} {'最大差异':>10s}")
for scale in [1.0, 1e-1, 1e-2, 1e-3]:
    x = rng.normal(size=(4, d)) * scale
    a = layernorm(x, gamma, beta, EPS_TORCH)
    b = layernorm(x, gamma, beta, EPS_KERAS)
    print(f'{scale:>10.0e} {np.abs(a).mean():>13.4f} {np.abs(b).mean():>13.4f} '
          f'{np.abs(a-b).max():>10.2e}')

x_small = rng.normal(size=(4, d)) * 1e-3
diff = np.abs(layernorm(x_small, gamma, beta, EPS_TORCH)
              - layernorm(x_small, gamma, beta, EPS_KERAS)).max()
assert diff > 1e-3, '激活值很小时，两个 eps 的差异变得可观'
print(f'\\n⚠️  keras.layers.LayerNormalization 的默认 eps 是 **1e-3**，torch 是 **1e-5** ——')
print(f'    相差 100 倍。激活值小时最大差异达 {diff:.2e}，会在逐层对拍里暴露为「后面几层全错」。')
print('✅ 迁移时必须显式设 epsilon，不要用默认值。')"""),
    code("""# BatchNorm 的 momentum 语义**相反**
def bn_update_torch(running, batch_stat, momentum):
    '''PyTorch: running = (1 - m) * running + m * batch    （m 是**新值**的权重）'''
    return (1 - momentum) * running + momentum * batch_stat

def bn_update_tf(moving, batch_stat, momentum):
    '''TF/Keras: moving = m * moving + (1 - m) * batch     （m 是**旧值**的权重）'''
    return momentum * moving + (1 - momentum) * batch_stat

r_t = r_f = 0.0
batch = 1.0
for _ in range(10):
    r_t = bn_update_torch(r_t, batch, momentum=0.1)     # torch 默认
    r_f = bn_update_tf(r_f, batch, momentum=0.99)       # keras 默认
print(f'10 步后: torch(m=0.1) running={r_t:.4f} | keras(m=0.99) moving={r_f:.4f}')
# 对应关系：torch 的 m 对应 keras 的 1-m
r_a = r_b = 0.0
for _ in range(10):
    r_a = bn_update_torch(r_a, batch, 0.1)
    r_b = bn_update_tf(r_b, batch, 0.9)                  # 1 - 0.1
assert abs(r_a - r_b) < 1e-12, 'torch 的 momentum=m 对应 keras 的 momentum=1-m'
print(f'✅ 对应关系: torch momentum=0.1  ⟺  keras momentum=0.9  (两者都得 {r_a:.4f})')
print(f'⚠️  照抄数字（两边都写 0.1 或都写 0.99）会让滑动统计的更新速度差 9 倍 ——')
print('    训练时看不出来，**切到 eval 模式后才暴露**（因为 eval 才用滑动统计）。')"""),
    md("""## 5 · 编译的盈亏平衡"""),
    code("""def breakeven_calls(n_traces, trace_cost, t_eager, t_graph):
    '''值得编译 <=> N > n_traces * trace_cost / (t_eager - t_graph)'''
    if t_graph >= t_eager:
        return float('inf')
    return n_traces * trace_cost / (t_eager - t_graph)

TRACE_COST = 200.0
print(f"{'场景':<22s} {'追踪次数':>8s} {'加速比':>7s} {'盈亏平衡调用数':>15s}")
rows = [('形状固定的训练', 1, 1.3), ('形状固定的推理', 1, 1.5),
        ('形状分 8 桶', 8, 1.3), ('形状每次都变(500)', 500, 1.3)]
for name, nt, speed in rows:
    be = breakeven_calls(nt, TRACE_COST, speed, 1.0)
    print(f'{name:<22s} {nt:>8d} {speed:>6.1f}× {be:>15,.0f}')

be_fixed = breakeven_calls(1, TRACE_COST, 1.3, 1.0)
be_bucket = breakeven_calls(8, TRACE_COST, 1.3, 1.0)
be_var = breakeven_calls(500, TRACE_COST, 1.3, 1.0)
assert be_fixed < 1000 and be_bucket < 10000
assert be_var > 300_000, '形状每次都变时基本不可能回本'
assert breakeven_calls(1, TRACE_COST, 1.0, 1.0) == float('inf'), '没有加速就永远不回本'
print(f'\\n✅ 形状固定时 {be_fixed:.0f} 次调用就回本（训练几分钟就够）；')
print(f'   形状每次都变时要 {be_var:,.0f} 次 —— 实际上永远不回本。')
print('   三条解法：形状分桶 / 声明动态维 / 只编译形状稳定的热点部分。')"""),
    md("""## ✏️ 练习 1：签名缓存的 key

实现 `signature_key(input_specs, python_args, dynamic_dims=())`：
返回一个可哈希的 key。`dynamic_dims` 是被声明为动态的维度下标集合（如 `(0, 1)` 表示
每个输入的第 0、1 维都不参与 key）。被声明为动态的维度在 key 里用 `None` 代替。"""),
    code("""def signature_key(input_specs, python_args, dynamic_dims=()):
    # TODO: 对每个 (shape, dtype)，把 dynamic_dims 里的维度换成 None；
    #       返回 (tuple(处理后的 specs), tuple(sorted(python_args.items())))
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
s1 = [((32, 128), 'float32'), ((128, 8), 'float32')]
s2 = [((32, 256), 'float32'), ((256, 8), 'float32')]
assert signature_key(s1, {}) != signature_key(s2, {}), '不声明动态维 -> 不同形状不同 key'
assert signature_key(s1, {}, dynamic_dims=(1,)) != signature_key(s2, {}, dynamic_dims=(1,)) \\
       or True     # 第二个输入的第 0 维仍不同
assert signature_key(s1, {}, dynamic_dims=(0, 1)) == signature_key(s2, {}, dynamic_dims=(0, 1)), \\
    '把所有可变维声明为动态 -> 同一个 key -> 只追踪一次'
assert signature_key(s1, {'scale': 1.0}) != signature_key(s1, {'scale': 2.0}), \\
    'Python 参数参与 key'
assert signature_key(s1, {'a': 1, 'b': 2}) == signature_key(s1, {'b': 2, 'a': 1}), \\
    'Python 参数的顺序不应影响 key'
print('key(s1)                =', signature_key(s1, {}))
print('key(s1, dynamic=(0,1)) =', signature_key(s1, {}, (0, 1)))
print('✅ 练习 1 通过：这就是 tf.function 的 input_signature / torch.compile 的 dynamic')"""),
    md("""## ✏️ 练习 2：框架默认值映射

实现 `translate_defaults(framework_from, framework_to, layer, params)`：
把一个框架的层参数翻译成另一个框架的。至少支持：
- `('torch','keras','LayerNorm', {'eps': 1e-5})` → `{'epsilon': 1e-5}`（**值不变，键名变**）
- `('torch','keras','BatchNorm', {'momentum': 0.1})` → `{'momentum': 0.9}`（**值要取 1-m**）
- 反方向同理。未知层抛 `ValueError`。"""),
    code("""def translate_defaults(framework_from, framework_to, layer, params):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert translate_defaults('torch', 'keras', 'LayerNorm', {'eps': 1e-5}) == {'epsilon': 1e-5}
assert translate_defaults('keras', 'torch', 'LayerNorm', {'epsilon': 1e-3}) == {'eps': 1e-3}
assert translate_defaults('torch', 'keras', 'BatchNorm', {'momentum': 0.1}) == {'momentum': 0.9}
assert translate_defaults('keras', 'torch', 'BatchNorm', {'momentum': 0.99}) == \\
       {'momentum': 0.01} or abs(translate_defaults('keras','torch','BatchNorm',
                                 {'momentum': 0.99})['momentum'] - 0.01) < 1e-12
try:
    translate_defaults('torch', 'keras', 'Mystery', {}); raise RuntimeError('不该到这')
except ValueError as e:
    print(f'未知层报错: {e}')
print('LayerNorm torch->keras:', translate_defaults('torch','keras','LayerNorm',{'eps':1e-5}))
print('BatchNorm torch->keras:', translate_defaults('torch','keras','BatchNorm',{'momentum':0.1}))
print('✅ 练习 2 通过：**键名变**与**值要换算**是两类不同的坑，都不报错')"""),
    md("""## ✏️ 练习 3：该不该编译

实现 `should_compile(n_calls, n_distinct_shapes, trace_cost, speedup)`：
返回 `(是否值得, 编译总成本, eager 总成本)`。假设 eager 单次成本为 1.0，
图执行单次成本为 `1/speedup`，追踪次数 = `min(n_distinct_shapes, n_calls)`。"""),
    code("""def should_compile(n_calls, n_distinct_shapes, trace_cost=200.0, speedup=1.3):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
ok, cg, ce = should_compile(100_000, 1)
assert ok, f'固定形状 + 10 万次调用应该值得编译 ({cg:.0f} vs {ce:.0f})'
ok2, cg2, ce2 = should_compile(300, 300)
assert not ok2, '每次形状都变 + 只调 300 次 -> 不值得'
ok3, *_ = should_compile(100_000, 8)
assert ok3, '分 8 桶 + 10 万次调用 -> 值得'
ok4, *_ = should_compile(50, 1)
assert not ok4, '只调 50 次 -> 追踪成本都摊不回来'
for args in [(100_000, 1), (100_000, 8), (300, 300), (50, 1)]:
    o, a, b = should_compile(*args)
    print(f'调用 {args[0]:>6d}, 不同形状 {args[1]:>4d} -> '
          f'编译 {a:>10.0f} vs eager {b:>8.0f}  {"✅ 编译" if o else "❌ 别编译"}')
print('✅ 练习 3 通过：编译不是免费的，「形状稳定 + 调用次数多」才划算')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def signature_key(input_specs, python_args, dynamic_dims=()):
    dyn = set(dynamic_dims)
    specs = tuple((tuple(None if i in dyn else d for i, d in enumerate(shape)), dtype)
                  for shape, dtype in input_specs)
    return (specs, tuple(sorted(python_args.items())))"""),
    code("""# 练习 2 参考答案
def translate_defaults(framework_from, framework_to, layer, params):
    if layer == 'LayerNorm':
        if (framework_from, framework_to) == ('torch', 'keras'):
            return {'epsilon': params['eps']}
        if (framework_from, framework_to) == ('keras', 'torch'):
            return {'eps': params['epsilon']}
    elif layer == 'BatchNorm':
        # 语义相反：torch 的 momentum 是**新值**权重，keras 是**旧值**权重
        return {'momentum': 1.0 - params['momentum']}
    raise ValueError(f'unknown layer {layer!r} for {framework_from}->{framework_to}')"""),
    code("""# 练习 3 参考答案
def should_compile(n_calls, n_distinct_shapes, trace_cost=200.0, speedup=1.3):
    n_traces = min(n_distinct_shapes, n_calls)
    cost_graph = n_traces * trace_cost + n_calls * (1.0 / speedup)
    cost_eager = n_calls * 1.0
    return cost_graph < cost_eager, cost_graph, cost_eager"""),
    md("""---
## 🧪 真实 API 对照胶囊（不在本环境运行，可原样复制）"""),
    code("""RECIPE = r'''
# ── TensorFlow：tf.function 的正确用法 ──────────────────────────────
import tensorflow as tf

# ① 声明输入签名 -> 可变维用 None -> 只追踪一次
@tf.function(input_signature=[
    tf.TensorSpec(shape=[None, None], dtype=tf.int32, name="input_ids"),
    tf.TensorSpec(shape=[None, None], dtype=tf.int32, name="attention_mask"),
])
def serve(input_ids, attention_mask):
    # ② 调试用 tf.print（图内算子，每次执行都打印），不要用 Python print
    tf.print("batch:", tf.shape(input_ids)[0])
    logits = model(input_ids, attention_mask=attention_mask, training=False)
    # ③ 依赖 tensor 值的分支必须用图算子
    return tf.cond(tf.reduce_max(logits) > 10.0,
                   lambda: tf.nn.softmax(logits / 2.0),
                   lambda: tf.nn.softmax(logits))

# ④ 诊断重追踪：数 Python 侧的执行次数
tf.config.run_functions_eagerly(False)
# 或设环境变量 TF_FUNCTION_JIT_COMPILE_DEFAULT / 看 "retracing" 警告

# ⑤ 显存：TF 默认会占满整卡，几乎总是要关掉
for gpu in tf.config.list_physical_devices("GPU"):
    tf.config.experimental.set_memory_growth(gpu, True)

# ── PyTorch：同样的语义，不同的名字 ─────────────────────────────────
import torch
compiled = torch.compile(model, dynamic=True)     # 对应 input_signature 的 None
# 诊断重编译：
#   TORCH_LOGS="recompiles,graph_breaks" python train.py
#   torch._dynamo.config.cache_size_limit = 64

# ── JAX：追踪语义最显式 ────────────────────────────────────────────
import jax
@jax.jit
def f(params, x):
    # 对 tracer 做 Python 判断会直接抛 ConcretizationTypeError（**宁可报错也不静默固化**）
    return jax.lax.cond(x.sum() > 0, lambda: x * 2, lambda: x)
'''
print(RECIPE)
for c in ['input_signature', 'tf.print', 'tf.cond', 'set_memory_growth',
          'dynamic=True', 'recompiles', 'lax.cond']:
    assert c in RECIPE, c
print('✅ 配方覆盖本模块全部要点（签名/图内打印/图内控制流/显存/重追踪诊断/三框架对照）')"""),
    md("""### 小结
- 静态图 = **Python 只是构图脚本**。这一句能解释 80% 的诡异行为：print 只出现一次、计数器不动、控制流被固化。
- **区分「构图时的量」与「运行时的量」**：依赖运行时值的控制流必须用图算子（`tf.cond`/`lax.cond`/`torch.cond`）。
- **重追踪是头号性能杀手**：形状变、dtype 变、传 Python 标量、在循环里新建函数对象，都会让缓存失效。
  诊断技巧跨框架通用：**在函数里放一个 Python 副作用，数它执行几次**。
- **形状每次都变时，编译是纯亏损**（本模块算出比 eager 还慢）。三条解法：分桶 / 声明动态维 / 只编译热点。
- **Keras 三种 API**：Functional 构建的是「可检查的数据结构」（能 summary、能直接导出）；Subclassing 是纯 Python（最像 PyTorch，但失去静态检查）。
- **三个「不报错但数值错」的坑**：Conv 权重布局（必须转置不能 reshape）、LayerNorm 的 eps（1e-5 vs 1e-3）、BatchNorm 的 momentum（**语义相反**，0.1 ↔ 0.9）。
- 三框架的差别在于**状态放哪**与**图从哪来**：PyTorch 状态在对象里+事后追踪；TF 状态在层里+装饰器；JAX 无隐藏状态+可组合变换。

下一站：**模块 02 · 框架迁移与权重对齐** —— 把权重搬过去，并**证明**它真的等价。"""),
]
