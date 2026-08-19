# -*- coding: utf-8 -*-
"""C60 模块 01 · 预处理一致性：最常见也最隐蔽的鸿沟。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（三层框架 / 二分定位 / 容差表）；C57（小目标）与 C55（TSR）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_preprocess_consistency.ipynb（纯 numpy 手写 resize 家族与对拍工具）'),
    ("核心参考", "On Aliased Resizing (CVPR 2022) · ONNX Resize 算子规范 · OpenCV/PIL/torch 的 resize 实现 · YOLOv5 letterbox"),
    ("预计时长", "读 85 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("pipeline", "预处理：一条有七个岔路口的链", "".join([
        P("模块 00 给出的根因分布里，<strong>预处理不一致独占约 40%</strong>——比后处理、量化、域差加起来还多。这一节先解释<em>为什么偏偏是它</em>，因为理解了原因，你才会知道该在哪里设防。"),
        P("答案很朴素：<strong>预处理是整条管线里唯一被写了两遍的部分。</strong>模型只有一份权重、一份计算图，导出工具会保证它被搬过去；后处理虽然也常常重写，但它的输出是人能直接看懂的框，错了很容易被发现。<em>只有预处理，既要重写一遍（Python → C++），又完全不可见——它的输出是一个 <code>1×3×640×640</code> 的浮点数组，没有人会去看它。</em>"),
        ASCII("""相机 / 图片文件
      │
      ▼
 ┌─ ① 解码 ────────── JPEG(libjpeg vs turbo)? ISP 直出? YUV→RGB 用哪套系数(BT.601/709)?
 │        ▼
 ├─ ② 通道顺序 ────── BGR 还是 RGB？                    ← 2 种
 │        ▼
 ├─ ③ resize ─────── 坐标映射(3) × 插值核(3) × 抗锯齿(2) × 定点/浮点(2)  ← **36 种**
 │        ▼
 ├─ ④ letterbox ──── pad值(3) × 位置(2) × pad到何处(2) × 取整(2) × 允许放大(2) ← **48 种**
 │        ▼
 ├─ ⑤ dtype ──────── 何时 uint8→float？中间用不用 uint8 存？    ← 3 种
 │        ▼
 ├─ ⑥ 归一化 ─────── 先 /255 还是先减 mean？mean/std 用什么量纲？ ← 4 种
 │        ▼
 └─ ⑦ 布局 ───────── HWC→CHW / NHWC 保持 / 通道对齐 / stride       ← 3 种
      │
      ▼
 1×3×640×640 float32   ← **没有人会去看这个数组**

组合数 ≈ 2 × 36 × 48 × 3 × 4 × 3 ≈ 1.2×10⁵ 种「都能跑通」的预处理
其中与训练侧完全一致的                              ← **只有 1 种**""")
        ,
        P("这个组合数不是吓唬人的修辞。<strong>上面每一个分叉，都是某个真实框架/库的真实默认值</strong>——它们各自都「合理」，只是互不相同。而 C++ 侧的同事重写时，用的是他熟悉的那一套默认值。"),
        TABLE(["岔路口", "训练侧常见值", "部署侧常见值", "错了会怎样", "本模块第几节"], [
            ["<strong>③ resize</strong>", "<code>cv2.INTER_LINEAR</code> / <code>PIL.BILINEAR</code> / <code>F.interpolate</code>", "厂商 SDK 的硬件 resize / 手写 bilinear", "<strong>小目标细节消失、细粒度类混淆</strong>", "2、3、4"],
            ["<strong>④ letterbox</strong>", "YOLOv5 式：114、居中、pad 到 stride 倍数", "0、左上、pad 到方形", "<strong>框整体偏移 / 上下文不同</strong>", "5"],
            ["<strong>② 通道顺序</strong>", "cv2 读入是 BGR，训练前 <code>cvtColor</code> 成 RGB", "ISP 直接给 RGB，没人再转一次（或转了两次）", "<strong>模型照跑，类别全错</strong>", "6"],
            ["<strong>⑥ 归一化</strong>", "<code>(x-mean)/std</code>，mean 用 0–255 量纲", "先 <code>/255</code> 再用同一组 mean", "<strong>动态范围压缩 255 倍，输出塌缩</strong>", "6、7"],
            ["<strong>⑤ dtype</strong>", "先转 float32 再做所有运算", "为了省内存在 uint8 上做减法", "<strong>下溢回绕：10−124 变成 142</strong>", "7"],
            ["① 解码", "JPEG 解码图", "ISP 直出", "真实域差（不是 bug，修不掉）", "7"],
        ]),
        DUAL(
            "把这一节记成一句话：<strong>预处理之所以是头号杀手，不是因为它难，而是因为它被写了两遍、且没人看它的输出。</strong><em>难的东西人们会小心；容易但不可见的东西，人们会想当然。</em>而「想当然」的具体形式就是：C++ 同事写 <code>cv::resize(src, dst, cv::Size(640,640))</code>，这行代码完全正确、完全符合文档、完全能跑——只是它的插值方式和训练侧不一样。",
            "从软件工程的角度，这是一个典型的 <span class=\"term\">duplicated specification</span>（规格被重复实现）问题：同一份语义在两处独立实现，而语义本身<strong>从未被写下来</strong>——它只存在于训练代码的具体调用里。<em>治本的做法有三条：①把预处理写成一份可跨语言复用的规格文件（配置 + 版本号），两侧都从它生成；②把预处理并入模型图一起导出（见第 9 节的讨论）；③退而求其次——承认会有两份实现，但用逐阶段对拍把它们钉住。</em><strong>本课教的是第 ③ 条，因为它是唯一在任何团队都能立刻落地的。</strong>",
        ),
        CALLOUT("danger", "<p><strong>面试题：「你怎么保证训练和部署的预处理一致？」</strong>这道题的答案分三档。<em>不及格</em>：「我会仔细检查代码」。<em>及格</em>：「把 mean/std/尺寸这些参数写进配置文件，两边读同一份」——参数化只覆盖了岔路口里最简单的一类，<strong>插值语义、letterbox 变体、通道顺序这些根本不是「参数」，是「实现」</strong>。<em>优秀</em>：「参数配置化只是第一步。真正的保证是<u>逐阶段张量对拍 + CI 门禁</u>：固定一组黄金样本图，两侧按同名阶段 dump 中间张量，逐元素比对，容差 max≤0.02、mean≤0.005（tensor 单位），任何一个阶段超差就阻断发布。此外我会特别检查三件参数化覆盖不到的事：resize 的插值核与坐标映射、letterbox 的六个自由度、通道顺序。」</p>", "「参数写进配置文件」只是及格答案"),
    ])),

    # ============================================================== 2
    ("coord", "resize 杀手 ①：坐标映射的三种语义", "".join([
        P("<strong>resize 是预处理里错得最多的一步，而它内部又分两个独立的自由度：坐标怎么映射，以及映射之后怎么取值。</strong>这一节讲第一个，下一节讲第二个。两者必须分开理解，因为它们的错误表现完全不同。"),
        P("问题的形式化：输出图上第 $j$ 个像素（$j=0,1,\\dots,H_{out}-1$），对应输入图上的哪个连续坐标 $u$？<strong>不同的库给出了三个不同的答案，而且没有一个是「错」的。</strong>"),
        MATH("\\underbrace{u = \\Bigl(j+\\tfrac12\\Bigr)\\frac{H_{in}}{H_{out}} - \\tfrac12}_{\\textbf{half pixel}} \\qquad \\underbrace{u = j\\,\\frac{H_{in}-1}{H_{out}-1}}_{\\textbf{align corners}} \\qquad \\underbrace{u = j\\,\\frac{H_{in}}{H_{out}}}_{\\textbf{asymmetric}}"),
        P("三者的哲学不同：<strong>half pixel</strong> 认为像素是<em>面积</em>——第 $j$ 个输出像素覆盖输入的一段区间，取它的中心；<strong>align corners</strong> 认为像素是<em>点</em>，并且要求首尾两个点严格对齐（$u(0)=0$，$u(H_{out}-1)=H_{in}-1$）；<strong>asymmetric</strong> 只对齐左上角，最省事。以 $4\\to 8$ 的上采样为例，三者给出的采样坐标是："),
        TABLE(["模式", "$u(0)\\dots u(7)$", "首尾", "谁在用"], [
            ["<strong>half pixel</strong>", "−0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25", "<strong>会越界</strong>（−0.25），要 clamp", "<strong>OpenCV</strong>、PIL、<code>torch align_corners=False</code>（默认）、ONNX <code>Resize</code> 默认"],
            ["<strong>align corners</strong>", "0, 0.43, 0.86, 1.29, 1.71, 2.14, 2.57, 3", "严格对齐两端", "<code>torch align_corners=True</code>、老版 <code>nn.Upsample</code>、部分 TF 算子"],
            ["<strong>asymmetric</strong>", "0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5", "右端采不满", "<strong>TensorRT <code>IResizeLayer</code> 的默认值</strong>、nearest 的常见实现"],
        ]),
        CALLOUT("warn", "<p>请把最后一行读两遍：<strong>TensorRT 的 <code>IResizeLayer</code> 默认坐标变换模式是 <code>ASYMMETRIC</code>，而 PyTorch 与 ONNX 的默认是 half pixel。</strong>如果你的模型内部有 upsample（FPN 几乎必然有），而转换链路没有正确传递 <code>coordinate_transformation_mode</code> 这个属性，<em>你会得到一个能跑、精度略低、但你找不到原因的 engine</em>。这不是假想——它是 ONNX <code>Resize</code> 算子把坐标模式做成显式属性的直接动机。<strong>检查方法：<code>polygraphy inspect model model.onnx --show attrs | grep coordinate</code>，然后确认目标后端确实实现了那个模式。</strong></p>", "TensorRT 的默认值和 PyTorch 不一样"),
        H3("差异有多大：把数字算出来"),
        P("语义之差看起来只有零点几个像素，很容易被当成「无所谓」。notebook 会在一张自然图上实测（$64\\to 32$，双线性）："),
        TABLE(["比较", "逐像素最大差", "逐像素平均差", "归一化后（tensor 单位）", "对照"], [
            ["half pixel vs align corners", "<strong>6.19 灰阶</strong>", "<strong>2.21 灰阶</strong>", "<strong>≈ 0.038</strong>", "是 fp16 表示误差的 <strong>≈ 78 倍</strong>"],
            ["half pixel vs asymmetric", "更大（整体平移半个源像素）", "—", "—", "缩放比越大，平移量越大"],
        ]),
        DUAL(
            "2.21 个灰阶听起来完全无所谓——人眼根本看不出来。<strong>但对拍工具看得出来，而且模型也「看得出来」</strong>：0.038 的 tensor 差异是 fp16 数值噪声的 78 倍，任何合理的容差都会把它判为 FAIL。<em>更重要的是它的性质：这不是随机噪声，是<u>系统性的空间偏移</u></em>——整幅图相对训练时的采样栅格挪了一点点。对一个 8×8 像素的交通标志，采样栅格偏移会直接改变它的表观（第 4 节会看到有多严重）。",
            "严谨地看：三种映射对应的是<strong>不同的重采样算子</strong>，而不是同一个算子的不同实现。half pixel 与 asymmetric 都是仿射映射 $u = aj+b$，只是 $b$ 不同（$b=\\frac{s-1}{2}$ vs $b=0$，$s=H_{in}/H_{out}$），<em>因此两者的差是一个常数平移 $\\frac{s-1}{2}$ 源像素</em>——$s=3$ 时正好是 1 个源像素的整体平移。align corners 的斜率则是 $\\frac{H_{in}-1}{H_{out}-1} \\ne s$，<strong>所以它与前两者的差异是位置相关的（图中心小、边缘大），这就是模块 00 说的「diff 集中在边缘带」这个指纹的来源</strong>。<em>看到 diff 呈边缘带分布，第一反应就该是 align_corners。</em>",
        ),
    ])),

    # ============================================================== 3
    ("kernel", "resize 杀手 ②：插值核，以及「3 倍下采样退化成最近邻」", "".join([
        P("坐标定了之后，还要决定<strong>怎么从整数网格上的像素值算出连续坐标 $u$ 处的值</strong>。这就是插值核。常见的三种："),
        TABLE(["核", "参与的源像素", "OpenCV 名字", "特点"], [
            ["最近邻 nearest", "1 个", "<code>INTER_NEAREST</code>", "最快；<strong>下采样时直接丢弃 $1-1/s^2$ 的像素</strong>"],
            ["双线性 bilinear", "2×2 个", "<code>INTER_LINEAR</code>", "默认值；<strong>下采样时同样丢弃大量像素（见下）</strong>"],
            ["区域平均 area", "$\\lceil s\\rceil^2$ 个（覆盖整个源区间）", "<code>INTER_AREA</code>", "<strong>下采样时唯一正确的选择</strong>；上采样时退化成 nearest"],
        ]),
        CALLOUT("intuition", "记住这条判据就够了：<strong>放大用 bilinear/bicubic，缩小用 area（或任何带抗锯齿的核）。</strong>理由在下一节。而现实中的默认值恰恰相反——<code>cv2.resize</code> 的默认是 <code>INTER_LINEAR</code>，而检测预处理 99% 的时间在做<em>缩小</em>。"),
        H3("一个必须知道的事实：整数倍缩放时，bilinear 就是 nearest"),
        P("把 half pixel 的映射代入整数缩放比 $s = H_{in}/H_{out}$："),
        MATH("u(j) \\;=\\; \\Bigl(j+\\tfrac12\\Bigr)s - \\tfrac12 \\;=\\; s\\,j + \\frac{s-1}{2}"),
        P("<strong>当 $s$ 是奇数时，$\\frac{s-1}{2}$ 是整数，于是 $u(j)$ 恒为整数，插值的小数部分恒为 0——双线性的两个权重变成 $(1, 0)$，它<em>退化成了最近邻</em>。</strong>"),
        P("这不是一个学术上的边角情况。<strong>车端最常见的一条预处理正好命中它</strong>："),
        ASCII("""相机原图 1920 × 1080
       │  cv2.resize(img, (640, 360), interpolation=cv2.INTER_LINEAR)
       ▼
  网络输入 640 × 360        s = 1920/640 = 3   且   1080/360 = 3   ← **整数，且是奇数**

        u(j) = 3j + 1  ⇒  小数部分恒为 0  ⇒  权重 (1, 0)  ⇒  **等价于最近邻**

  源图 3×3 的一个小块          实际参与计算的像素
   ┌───┬───┬───┐                ┌───┬───┬───┐
   │ a │ b │ c │                │ · │ · │ · │
   ├───┼───┼───┤                ├───┼───┼───┤
   │ d │ e │ f │      ⇒         │ · │ e │ · │      **只有 e 被用到**
   ├───┼───┼───┤                ├───┼───┼───┤
   │ g │ h │ i │                │ · │ · │ · │
   └───┴───┴───┘                └───┴───┴───┘

  参与计算的像素比例 = 1/s² = 1/9 = **11.1%**
  被直接丢弃的信息   =        **88.9%**""")
        ,
        P("notebook 会用一个可验证的方式确认这件事：把一张 480×480 的图用 half-pixel bilinear 缩到 160×160，<strong>输出的标准差与输入完全相同（53.82 vs 53.82，逐位相等）</strong>——因为它根本没有做任何平均，只是抽样。而 area 缩放后标准差降到 36.02，抗锯齿三角核降到 31.52，<em>这个下降正是「高频被正确滤掉」的证据</em>。"),
        DUAL(
            "很多人第一次听到这件事会不信：「双线性明明是加权平均啊」。<strong>双线性是在<u>相邻 2×2</u> 上加权平均，而缩放比是 3 时，相邻的两个源像素之间隔着 3 个源像素的采样步长</strong>——2×2 邻域根本盖不住那 9 个像素。<em>插值核的宽度是固定的（2 个像素），但采样步长随缩放比增长；一旦步长超过核宽，中间的像素就没有任何机会进入计算。</em>",
            "更一般的结论：<strong>非抗锯齿的插值核，其支撑集（support）在<u>输出坐标系</u>下是固定的（bilinear 是 ±1），映射回输入坐标系就只有 ±1 个输入像素</strong>；而正确的下采样要求支撑集在输入坐标系下是 $\\pm s$。<span class=\"term\">antialiased resampling</span>（抗锯齿重采样，PIL 的 <code>resize</code>、<code>torch.nn.functional.interpolate(antialias=True)</code>、OpenCV 的 <code>INTER_AREA</code>）做的正是这件事：<em>把滤波器的支撑集按 $\\max(1, s)$ 拉伸，再归一化权重。</em>$s$ 为偶数时 $\\frac{s-1}{2}$ 是半整数，权重是 $(0.5, 0.5)$——比奇数好一点，但仍然只用到 2 个源像素（$s=4$ 时用到 2/16 = 12.5%）。<strong>无论奇偶，非抗锯齿的下采样都在丢弃绝大部分信息。</strong>",
        ),
        CALLOUT("warn", "<p><strong>三家库的默认行为，请务必记住这张对照：</strong>①<code>cv2.resize(..., INTER_LINEAR)</code> —— half pixel，<strong>无抗锯齿</strong>；②<code>PIL.Image.resize(..., BILINEAR)</code> —— half pixel，<strong>有抗锯齿</strong>（PIL 2.7 之后所有滤波器在缩小时都做抗锯齿）；③<code>torch.nn.functional.interpolate(mode='bilinear')</code> —— half pixel，<strong>默认无抗锯齿</strong>（<code>antialias=True</code> 才有，且该参数是较晚才加的）。<em>所以「训练用 torchvision（PIL 后端）、部署用 OpenCV」这个极其常见的组合，天然就不一致</em>——而两边的代码看起来都写着「bilinear」。<strong>torchvision 后来把 <code>antialias</code> 的默认值改成 <code>True</code>（对齐 PIL），这个变更本身就说明这个坑有多普遍。</strong></p>", "写着同一个词，做着不同的事"),
    ])),

    # ============================================================== 4
    ("alias", "resize 杀手 ③：混叠——对小目标是灾难", "".join([
        P("上一节说「丢弃了 88.9% 的像素」，但只丢信息还不是最坏的。<strong>最坏的是：被丢掉的高频不会安静地消失，它们会折叠回低频，变成图上原本不存在的假结构。</strong>这就是 <span class=\"term\">aliasing</span>（混叠）。"),
        H3("采样定理给出的硬边界"),
        P("以 $s$ 倍下采样，输出的奈奎斯特频率对应<strong>原图上周期为 $2s$ 像素</strong>的结构。任何比它更细的结构都无法被表示；如果采样前不滤掉它们，它们会以镜像频率出现："),
        MATH("f > \\frac{1}{2s} \\ \\ (\\text{周期} < 2s) \\quad\\xrightarrow{\\ \\text{无抗锯齿抽样}\\ }\\quad f' = \\Bigl|\\,f - \\tfrac{k}{s}\\,\\Bigr| \\ \\text{（折叠到低频，成为假结构）}"),
        P("代入 TSR 的真实参数：<strong>1920→640 是 $s=3$，所以原图上<u>周期小于 6 像素（即笔画宽度小于 3 像素）</u>的一切结构，在缩放后都是假的。</strong>notebook 会用正弦扫频把这件事量化出来（3 倍下采样，源幅度 100）："),
        TABLE(["原图周期", "在输出端是否可表示", "无抗锯齿 bilinear 保留的幅度", "INTER_AREA", "抗锯齿 bilinear"], [
            ["3 px", "❌ 完全不可", "0.0", "0.0", "5.4"],
            ["<strong>4 px</strong>", "<strong>❌ 不可</strong>", "<strong>100.0 ← 原样通过，全部是假信号</strong>", "<strong>33.3</strong>", "18.1"],
            ["5 px", "❌ 不可", "<strong>95.1 ← 几乎全是假信号</strong>", "51.3", "43.0"],
            ["6 px", "临界", "86.6", "57.7", "48.7"],
            ["12 px", "✅ 可以", "86.6", "78.9", "76.3"],
            ["24 px", "✅ 可以", "96.6", "94.4", "92.3"],
        ]),
        P("<strong>第二行是整张表的重点。</strong>周期 4 像素的条纹在输出端<em>根本不可能存在</em>（输出的最细可表示周期是 6 像素），但无抗锯齿的 bilinear 把它<strong>原封不动地（幅度 100%）</strong>搬进了输出——它在输出端变成了一个周期完全不同的、凭空捏造的粗条纹。<em>而 INTER_AREA 把它压到 33，抗锯齿 bilinear 压到 18，这才是正确的行为。</em>"),
        H3("在一张自然图上是什么量级"),
        P("扫频是理想实验。放到一张带细纹理的自然图上（480→160，3 倍）："),
        TABLE(["", "输出图的标准差", "与 AREA 的平均逐像素差", "最大差"], [
            ["原图", "53.82", "—", "—"],
            ["<strong>无抗锯齿 bilinear</strong>", "<strong>53.82（一模一样 → 它只是在抽样）</strong>", "<strong>21.4 灰阶</strong>", "<strong>49.7 灰阶</strong>"],
            ["INTER_AREA", "36.02", "0（基准）", "0"],
            ["抗锯齿 bilinear", "31.52", "8.5 灰阶", "20.7 灰阶"],
        ]),
        P("<strong>21.4 灰阶的平均差</strong>——这是模块 00 容差表里「resize 语义错误 ≈ 0.37 tensor 单位」的来源。它比 fp16 噪声大 700 倍，比定点舍入大 40 倍。<em>同时注意最后一行：两种<u>都</u>抗锯齿的实现（PIL 式三角核 vs OpenCV 的 AREA）之间只差 8.5 灰阶。<strong>所以真正的分水岭是「有没有抗锯齿」，而不是「用了哪家库」</strong>。</em>"),
        CALLOUT("danger", "<p><strong>这一节是本模块与 TSR 岗位最直接相关的部分，请当成面试素材来记。</strong>一块 60 米外的限速牌在 1920×1080 相机上大约 20–30 像素，牌面上「60」的<u>笔画宽度只有 2–3 像素</u>。缩到 640 输入（$s=3$）后：<em>①笔画周期 4–6 像素正好落在混叠带里；②无抗锯齿的 bilinear 会让这些笔画<strong>随标志的亚像素位置随机地出现或消失</strong>（因为它只是抽样，抽到哪一列全看运气）。</em><strong>后果是：同一块牌子在连续几帧里，「60」和「80」的表观特征在随机跳变——这正好对应 TSR 系统最典型的失效模式之一「限速值在相邻帧之间跳变」。</strong>notebook 会实测出：在一个含「限速60 / 限速80 / 蓝色指示 / 黄色警告」四类的合成检测任务上，把训练侧的 AREA 换成部署侧的 INTER_LINEAR，<u>整体 mAP 只掉 0.069（0.773→0.704，很容易被当成噪声放过），但两个细粒度红牌类的 AP 合计掉了 0.32（0.49→0.35、0.64→0.46），而两个靠颜色区分的粗类一点没掉</u>。<strong>「整体指标掩盖关键类崩塌」——这就是它「最隐蔽」的含义。</strong></p>", "为什么 TSR 对 resize 尤其敏感"),
        DUAL(
            "所以「缩小时用 AREA」不是风格偏好，是<strong>信号处理层面的正确性问题</strong>。而且它有一个反直觉的推论：<em>如果训练和部署<u>都</u>用无抗锯齿的 bilinear，那么至少它们是一致的，模型会学会适应那些假结构</em>——一致性甚至比「正确性」更重要。<strong>但你不能靠这个：因为混叠出的假结构依赖标志的亚像素位置，它对同一块牌子在不同帧上都不一致，模型学不到稳定的东西。</strong>",
            "把两件事分清楚很重要：<em>①<strong>一致性问题</strong>——两侧用了不同的 resize，这是 bug，必须修；②<strong>正确性问题</strong>——两侧用了同一个错误的 resize，这不是 bug，但它系统性地损害了小目标的可分性。</em>第 ① 类通过对拍解决；第 ② 类要通过<strong>改训练配方</strong>解决（把训练侧也换成 AREA / antialias=True，并重新训练）。<span class=\"term\">Parmar et al. (CVPR 2022)</span> 证明了第 ② 类问题连 GAN 的 FID 评测都被污染了——<em>它不只是工程问题，也是学术结果可复现性的问题</em>。<strong>面试里能把「一致性」和「正确性」拆开讲，是一个明显的成熟度信号。</strong>",
        ),
    ])),

    # ============================================================== 5
    ("letterbox", "letterbox 的六个自由度与逆变换", "".join([
        P("<span class=\"term\">letterbox</span>（等比缩放 + 填充）是检测预处理的标配：既要把任意长宽比的图塞进固定的网络输入，又不能拉伸变形（拉伸会破坏目标的长宽比先验，对圆形/三角形的交通标志尤其致命）。<strong>问题是它有六个互相独立的实现选择，而且每一个都有两三种「合理」的答案。</strong>"),
        TABLE(["#", "自由度", "常见取值", "选错的后果"], [
            ["1", "<strong>pad 值</strong>", "114（YOLO 系）/ 0 / ImageNet 均值", "边界处的特征响应不同；靠近边缘的目标受影响"],
            ["2", "<strong>pad 位置</strong>", "居中 / 左上角", "<strong>目标在输入张量里整体平移；逆变换若不匹配 → 框整体偏</strong>"],
            ["3", "<strong>pad 到哪</strong>", "pad 成正方形 / 只 pad 到 stride 的倍数（YOLOv5 的 <code>auto=True</code>）", "输入张量形状不同 → 动态 shape profile 不同、算力浪费不同"],
            ["4", "<strong>缩放比取整</strong>", "<code>round</code> / <code>floor</code> / 先算 float 再取整", "差 1 像素，但会让逆变换产生系统性偏差"],
            ["5", "<strong>是否允许放大</strong>", "<code>scaleup=True/False</code>（小图要不要拉大）", "训练时通常允许、推理时常关掉 → 小图的表观尺度不同"],
            ["6", "<strong>pad 的奇偶分配</strong>", "<code>dh//2</code> 上下均分 / YOLOv5 的 <code>round(dh-0.1)</code> 与 <code>round(dh+0.1)</code>", "差 1 像素的系统性偏移"],
        ]),
        H3("算一笔账：pad 到方形 vs pad 到 stride 倍数"),
        P("车载相机是 16:9 的。把 1920×1080 letterbox 到 640："),
        ASCII("""r = min(640/1920, 640/1080) = 1/3      缩放后 = 640 × 360

方案 A：pad 成正方形 640×640            方案 B：只 pad 到 stride(=32/64) 的倍数
┌────────────────────────┐ ▲            ┌────────────────────────┐ ▲
│ ▓▓▓▓ 114 灰边 140 行 ▓▓ │ │            │ ▓▓▓ 114 灰边 12 行 ▓▓▓ │ │
├────────────────────────┤ │            ├────────────────────────┤ │
│                        │ │            │                        │ │
│      图像 640×360      │ 640          │      图像 640×360      │ 384
│                        │ │            │                        │ │
├────────────────────────┤ │            ├────────────────────────┤ │
│ ▓▓▓▓ 114 灰边 140 行 ▓▓ │ │            │ ▓▓▓ 114 灰边 12 行 ▓▓▓ │ │
└────────────────────────┘ ▼            └────────────────────────┘ ▼
 ◄──────── 640 ────────►                 ◄──────── 640 ────────►

 灰边占张量的 **43.75%**                  灰边占张量的 **6.25%**
 → 43.75% 的卷积在算灰色                  → 省下约 37.5% 的推理算力
 上 pad = 140 行                          上 pad = 12 行""")
        ,
        P("<strong>43.75% 是一个足以改变选型的数字。</strong>如果你的延迟预算很紧（模块 05 会讲车端的 33 ms 怎么分），把方形 pad 换成 stride 倍数 pad，几乎白送 37.5% 的算力。<em>代价是输入形状不再固定，TensorRT 需要动态 shape 的 optimization profile（模块 02）——这就是为什么很多量产系统仍然用方形 pad：不是没算过账，是不想引入动态 shape 的复杂度。</em>"),
        H3("逆变换：框整体偏移的头号原因"),
        P("检测框是在 letterbox 之后的坐标系里预测的，必须还原回原图。正确的逆变换只有一行："),
        CODE("""# 正变换：orig --(缩放 r)--> unpadded --(左上角加 pad)--> letterboxed
x_lb = x_orig * r + pad_left
y_lb = y_orig * r + pad_top

# 逆变换（唯一正确的写法）
x_orig = (x_lb - pad_left) / r
y_orig = (y_lb - pad_top ) / r
x_orig = np.clip(x_orig, 0, W0);  y_orig = np.clip(y_orig, 0, H0)   # **clip 必须在最后**"""),
        TABLE(["错误写法", "错在哪", "1920×1080→640 时的偏移量"], [
            ["<code>x_orig = x_lb / r</code>（忘了减 pad）", "把 pad 也当成了图像内容", "<strong>y 方向整体偏 140/r = 420 像素</strong>（图高的 39%！）"],
            ["<code>x_orig = x_lb * W0/640</code>（用了非等比缩放）", "letterbox 是等比的，不能按两个方向各自的比例还原", "x 正确、y 错 —— <strong>框被垂直拉伸</strong>"],
            ["先 clip 到 [0,640] 再减 pad 除 r", "clip 的边界是 letterbox 坐标系的，不是原图的", "贴边的框被错误截断"],
            ["<code>pad_top</code> 用了 <code>dh/2</code> 但正变换用 <code>round(dh-0.1)</code>", "两处对 pad 的取整不一致", "系统性偏 1 像素 —— <strong>对 8 像素的标志，IoU 从 1.0 掉到 0.78</strong>"],
        ]),
        DUAL(
            "第一行那个 <strong>420 像素</strong>是很多人第一次做部署时都踩过的坑：框全都往下掉了一大截，看起来「模型完全不行」，实际上模型完全正确。<em>识别它非常容易：<strong>如果所有框的偏移量是同一个常数，那一定是坐标变换问题，不可能是模型问题</strong>——模型不会犯这么整齐的错。</em>",
            "最后一行才是真正难查的：<strong>1 像素的系统性偏移</strong>。它不会让人一眼看出「框歪了」，但它会稳定地压低 IoU。对一个 $8\\times 8$ 的框，沿一个方向平移 1 像素，$\\text{IoU} = \\frac{7\\times 8}{64+64-56} = \\frac{56}{72} = 0.778$；平移 2 像素则 $\\frac{6\\times8}{64+64-48}=\\frac{48}{80}=0.6$；沿对角线平移 2 像素只剩 $\\frac{36}{92}=0.391$。<em>而 COCO 口径的 mAP 要在 IoU=0.5:0.95 上平均，0.778 意味着 IoU≥0.8 的那几档全部丢失</em>。<strong>对 TSR 这种目标常年在 10–30 像素的任务，1 像素的坐标 bug 就能吃掉 5–10 个 mAP，而且它在大目标数据集（COCO）上几乎不可见——这是「在 COCO 上验不出来、上车才暴露」的典型例子。</strong>",
        ),
        CALLOUT("intuition", "落地建议：<strong>把 letterbox 的正变换与逆变换写成一对函数，并写一个 round-trip 单测</strong>——随机生成 1000 个原图坐标，正变换再逆变换，要求误差 < 1e-6。<em>这个测试 10 行代码，能挡住上表全部四种错误。</em>notebook 里会实现它。"),
    ])),

    # ============================================================== 6
    ("channel", "BGR/RGB 与归一化：模型照跑，mAP 全掉", "".join([
        P("这一类错误的特征是<strong>「静默」</strong>：不报错、不崩溃、张量形状完全正确、推理速度完全正常、框也照样出——<em>只有精度是错的</em>。这也是它能在代码库里潜伏几个月的原因。"),
        H3("BGR/RGB：一个持续了二十年的历史包袱"),
        P("<code>cv2.imread</code> 返回 <strong>BGR</strong>（OpenCV 早期为了配合当时 Windows 位图的字节序而定下的），而 PIL、matplotlib、torchvision、几乎所有训练框架用 <strong>RGB</strong>。于是训练代码里必然有一行 <code>cv2.cvtColor(img, cv2.COLOR_BGR2RGB)</code>——<em>而这一行在 C++ 侧极容易被漏掉，或者因为 ISP 已经输出 RGB 而被多做了一次。</em>"),
        P("notebook 里会构造一个四类合成 TSR 检测任务（限速60 / 限速80 / 蓝色指示 / 黄色警告），检测器由两部分组成：<strong>定位靠灰度局部对比度（对通道置换完全不变），分类靠归一化后的颜色特征（对通道置换极其敏感）</strong>。这个结构刻意模拟真实检测器的行为。实测结果："),
        TABLE(["条件", "mAP", "类别无关的定位召回", "现象"], [
            ["① 完全一致（基线）", "<strong>0.773</strong>", "0.99", "正常"],
            ["② resize AREA→INTER_LINEAR", "0.704", "1.00", "整体只掉 0.069，<strong>但细粒度类合计掉 0.32</strong>"],
            ["③ AREA→抗锯齿 bilinear", "0.768", "0.99", "几乎不掉（都抗锯齿）"],
            ["<strong>④ BGR/RGB 弄反</strong>", "<strong>0.000</strong>", "<strong>0.90（几乎不受影响！）</strong>", "<strong>框全在，类别全错：100 张里 78 张被判成「蓝色指示」</strong>"],
            ["⑤ 归一化顺序错", "0.227", "0.84", "<strong>全部 100 张塌缩到同一个类别</strong>"],
        ]),
        P("<strong>第 ④ 行是全表最重要的一行。</strong>定位召回 0.90 意味着：<em>你打开可视化，会看到框稳稳地画在每一块牌子上</em>——一切看起来都对。只有类别是系统性错的。<em>这就是为什么这类 bug 靠「看几张可视化图」根本发现不了，必须靠对拍或者逐类 AP。</em>"),
        CALLOUT("danger", "<p><strong>合成实验里 mAP 掉到 0 是因为我的分类器完全依赖颜色；真实 CNN 还会用形状与纹理，所以典型的实际掉幅是 <u>10–30 mAP</u>，不会归零。</strong>notebook 会用一个「颜色依赖度 $w$」的扫描把这条曲线画出来：$w=0$（纯灰度特征）时 BGR 弄反完全无影响；$w=0.2$ 时 mAP 从 0.663 掉到 0.155；$w\\ge 0.6$ 时归零。<em>结论是：<strong>模型对颜色的依赖度越高，通道顺序错误的代价越大</strong>——而交通标志识别恰恰是所有视觉任务里对颜色依赖度最高的之一（红=禁令、蓝=指示、黄=警告，颜色<u>就是</u>语义，见 C56 模块 02）。</em><strong>所以「BGR/RGB 弄反」在通用检测里是个中等 bug，在 TSR 里是个致命 bug。这一句话在面试里很值钱。</strong></p>", "TSR 里颜色就是语义，所以代价格外大"),
        H3("归一化：顺序错一步，动态范围压缩 255 倍"),
        P("mmdetection 系的经典配置是 <code>mean=[123.675, 116.28, 103.53]</code>、<code>std=[58.395, 57.12, 57.375]</code>——注意这组数是 <strong>0–255 量纲</strong>的（它们就是 ImageNet 均值 $\\times 255$）。正确写法是直接 <code>(x - mean) / std</code>，<em>不要先除 255</em>。但「图像要先归一化到 [0,1]」是一个太强的肌肉记忆，于是常见的错误是："),
        CODE("""# ❌ 错误：先 /255，又用 0-255 量纲的 mean/std
x = img.astype(np.float32) / 255.0
x = (x - mean_255) / std_255
#   输出范围：[(0-123.675)/58.395, (1-123.675)/58.395] = [-2.1179, -2.1008]
#   跨度 0.01712   ← 全图几乎是同一个常数

# ✅ 正确
x = img.astype(np.float32)
x = (x - mean_255) / std_255
#   输出范围：[-2.1179, +2.2489]，跨度 4.3668""")
        ,
        MATH("\\frac{\\text{正确的动态范围}}{\\text{错误的动态范围}} \\;=\\; \\frac{(255-\\mu)/\\sigma - (0-\\mu)/\\sigma}{(1-\\mu)/\\sigma - (0-\\mu)/\\sigma} \\;=\\; \\frac{255/\\sigma}{1/\\sigma} \\;=\\; \\mathbf{255}"),
        P("<strong>正好 255 倍</strong>，与 mean/std 的具体取值无关。输入张量的动态范围被压缩到原来的 1/255，<em>但它并不是全零，所以模型不会报错，BN 也不会崩</em>——它只是把一张几乎恒定的图喂进去，于是所有位置的特征几乎相同，输出塌缩到某一个类。上表第 ⑤ 行的「100 张全部预测同一个类」就是这个机制。"),
        DUAL(
            "怎么一眼认出它？<strong>看输入张量的 <code>std()</code></strong>。正常预处理后，张量的标准差应该在 <strong>0.8–1.2</strong> 之间（这正是 mean/std 归一化的设计目的）。如果你看到 0.004 这种数，<em>不用查任何代码，直接去看归一化那两行</em>。这是一个 5 秒钟的检查，建议写进对拍脚本的第一行。",
            "更完整的自检清单：归一化之后的张量应当满足 ①$\\text{std} \\in [0.8, 1.2]$；②$\\text{mean} \\in [-0.5, 0.5]$；③$\\min > -3$ 且 $\\max < 3$（因为 $(0-\\mu)/\\sigma \\approx -2.1$、$(255-\\mu)/\\sigma \\approx 2.6$）。<em>这三条能同时抓住：少除 255、多除 255、mean/std 量纲不匹配、mean/std 的 RGB 顺序被交换（此时 std 正常但逐通道 mean 会明显偏离 0）、以及忘了做归一化（此时 std ≈ 74，因为原始像素的标准差就是那个量级）。</em><strong>把这三条写成 5 行 assert，是投入产出比最高的防御。</strong>",
        ),
        CALLOUT("warn", "<p>还有一个更隐蔽的变体：<strong>mean/std 本身按 RGB 顺序写，但图像是 BGR</strong>（或者反过来）。此时 std 完全正常，逐通道 mean 的偏移也只有 $(123.675-103.53)/58 \\approx 0.35$ ——<strong>上面三条自检会全部通过</strong>。notebook 里会验证这一点。<em>这个偏移量小到不会引起任何怀疑，但它是一个恒定的通道级偏置，会系统性地影响颜色判断。</em><strong>结论：自检和对拍不能互相替代。自检回答「看起来正不正常」，对拍回答「和训练侧一不一样」——只有后者能抓住这一类「看起来完全正常的错误」。</strong></p>", "自检挡不住的那一类"),
    ])),

    # ============================================================== 7
    ("dtype", "uint8 → float 的时机、精度，与车端 ISP 的域差", "".join([
        P("前面几节讲的是「算什么」，这一节讲「用什么类型算」和「什么时候转类型」。<strong>这类错误的共同点是：它们在 Python 里几乎不可能发生（numpy 会自动提升类型），但在 C++ / 定点 DSP 上是常态。</strong>"),
        H3("① 在 uint8 上做减法：下溢回绕"),
        P("C++ 侧为了省一次内存拷贝，很容易写出「先在 <code>uint8</code> 缓冲区上减均值，再转 float」。<strong>结果是灾难性的：无符号整数下溢会回绕。</strong>"),
        CODE("""np.array([10, 200], dtype=np.uint8) - np.array([124, 124], dtype=np.uint8)
# -> array([142,  76], dtype=uint8)
#      ↑ 10 - 124 = -114，按 mod 256 回绕成 142
#
# 后果：**图像里最暗的像素变成了最亮的**（10 -> 142），
#       而中等亮度的像素是正确的（200 -> 76）。
# 指纹：diff 图上只有暗区非零，且差值恰好是 256 的倍数。""")
        ,
        P("<strong>这个 bug 的指纹极其独特</strong>：diff 只出现在暗区（像素值 < mean 的地方），且差值恒等于 256。<em>在夜间与隧道场景里，暗区占了大半张图——所以它的表现是「白天好好的，晚上完全不行」，很容易被误判成「夜间数据不够，需要加数据」（模块 00 说的最贵的那条路）。</em>"),
        H3("② 转 float 的时机：在 resize 之前还是之后"),
        TABLE(["顺序", "做法", "精度代价", "内存/速度"], [
            ["<strong>uint8 resize → 转 float</strong>", "OpenCV 默认路径", "resize 结果被舍入回 uint8：<strong>≈0.5 灰阶，均值 0.25</strong>", "<strong>快、省内存</strong>（3 倍）"],
            ["<strong>转 float → float resize</strong>", "PyTorch / 严格实现", "无额外舍入", "慢、内存 ×4"],
        ]),
        P("notebook 会实测这个差异：把两条路径的结果比对，<strong>最大差 0.52 灰阶、平均 0.25 灰阶、超过 1 灰阶的像素占比 0.0000%</strong>。归一化后是 <strong>0.0086 tensor 单位</strong>——这正是模块 00 容差表里「定点舍入」那一档，<em>它比 fp16 噪声大 17 倍，但比任何语义错误小 40 倍以上</em>。"),
        CALLOUT("intuition", "所以对拍时要能<strong>区分「实现噪声」与「语义错误」</strong>：看到 diff 的最大值恰好卡在 0.5 灰阶附近、且没有空间结构，那就是定点舍入，<em>不要去追它</em>。这是模块 00 的容差表能救你一周时间的地方——把 0.5 灰阶当 bug 追，是新手最常见的时间浪费。"),
        H3("③ OpenCV 的定点权重：另一个 0.5 灰阶来源"),
        P("OpenCV 对 8 位图像的 <code>INTER_LINEAR</code> 走的是<strong>定点</strong>路径：插值权重被量化到 $1/2048$（<code>INTER_RESIZE_COEF_BITS=11</code>），最后结果四舍五入回 uint8。<em>这意味着即使你在两边都用了「相同语义的 bilinear」，OpenCV 的结果和一个 float64 的教科书实现之间仍有 ≤0.5 灰阶的差。</em><strong>如果你的对拍要求 bit 级一致，你会永远失败；正确的做法是把容差设在 0.5 灰阶之上、语义错误之下。</strong>"),
        H3("④ 车端 ISP 与训练数据的域差——这一条不是 bug"),
        P("最后一条虚线值得单独强调，因为<strong>它是这一整个模块里唯一一个「对拍解决不了」的问题</strong>。"),
        ASCII("""训练数据的来路                                车上的来路
────────────────────────                     ────────────────────────
 传感器 → ISP → **JPEG 编码** → 存盘           传感器 → ISP → 直接进内存
                     │                                    │
                     ▼                                    ▼
              读盘 → **JPEG 解码**                   （无编解码环节）
                     │                                    │
                     ▼                                    ▼
          8×8 DCT 量化的产物：                     ISP 原始输出：
          · 高频被截断（细笔画变糊）              · 高频完整保留
          · 块效应（8×8 边界）                    · 无块效应
          · 色度常被 4:2:0 下采样  ← **对红蓝标志尤其相关**
                                                  · 但有 ISP 自己的特性：
                                                    去噪强度、锐化、色调映射、
                                                    自动曝光策略、白平衡

  ⇒ 两侧的**高频统计**与**色度分辨率**系统性不同 ——
    这不是 bug，是 **domain gap**，只能靠采集端对齐或增强模拟来缩小""")
        ,
        DUAL(
            "为什么它对 TSR 特别重要？<strong>因为 JPEG 的 4:2:0 色度下采样把色度分辨率砍了一半</strong>，而交通标志的语义有很大一部分编码在颜色里。<em>一块 20 像素的标志，它的色度信息在训练图上只有 10×10 的有效分辨率，而在车上是完整的 20×20。</em>模型在训练时学会了依赖「模糊的颜色」，上车后拿到「锐利的颜色」，分布是错位的。同理，JPEG 抹掉的高频恰好是限速数字的笔画——<strong>模型可能学会了「在糊掉的笔画上做判断」，而车上的笔画是清晰的</strong>。",
            "工程上有三条对策，按成本递增：<em>①<strong>在训练侧模拟部署域</strong></em>——把 JPEG 压缩伪影作为增强加进去（<code>quality ∈ [70,95]</code> 随机），或者反过来，用低压缩率重新导出训练数据；<em>②<strong>在部署侧模拟训练域</strong></em>（把 ISP 输出做一次 JPEG 编解码再送模型）——听起来荒谬，但在无法重训时是有效的止血手段，代价是几毫秒的延迟；<em>③<strong>从采集端对齐</strong></em>——数据采集时保存 ISP 直出的无损/近无损图，从根上消除这个域差，这是量产团队的正解但需要提前规划存储与带宽。<strong>更前沿的方向是把 ISP 参数也纳入感知的优化目标（「为机器视觉调 ISP」而不是「为人眼调 ISP」），见第 9 节。</strong>",
        ),
        CALLOUT("warn", "<p><strong>排查纪律：域差必须放在最后查。</strong>它的检查成本是几十小时（要重新采集数据、重新训练、做切片评测），而前面那些确定性问题的检查成本是半小时。<em>模块 00 的 p/c 排序告诉你：即使域差的先验概率不低（≈10%），它也应该排在最后</em>——不是因为它不可能，而是因为它最贵。<strong>「上车掉点 → 第一反应是数据不够」是这个行业最昂贵的思维定势。</strong></p>", "先排干净确定性问题，再谈域差"),
    ])),

    # ============================================================== 8
    ("locate", "定位方法：逐步骤 dump、逐元素 diff、二分到算子", "".join([
        P("前面七节讲的是「有哪些坑」。这一节讲<strong>怎么在不知道有哪些坑的情况下，30 分钟内找到具体是哪一个</strong>——这才是可迁移的能力，因为坑的清单永远列不完。"),
        H3("工具的形态"),
        P("把预处理写成一个<strong>命名阶段的序列</strong>，而不是一个大函数。这是整套方法的前提："),
        CODE("""STAGES = ['decode', 'to_rgb', 'resize', 'letterbox', 'cast_f32', 'normalize', 'hwc2chw']

def run_pipeline(img, cfg, dump_dir=None):
    t, out = img, {}
    for name in STAGES:
        t = OPS[name](t, cfg)          # 每个阶段一个纯函数
        out[name] = t
        if dump_dir:                   # dump 是**内建能力**，不是临时加的 print
            np.save(f'{dump_dir}/{name}.npy', np.ascontiguousarray(t))
    return t, out""")
        ,
        P("这个结构本身就是最重要的一半工作。<strong>如果预处理是一个 80 行的大函数，你连「第一个分歧阶段」这个概念都无从谈起</strong>——只能靠往里面插 print，而插 print 的位置就是在猜。"),
        H3("对拍报告长什么样"),
        ASCII("""$ python3 parity.py --golden data/golden/*.png --left train_cfg.yaml --right deploy_cfg.yaml

  阶段            形状               max|Δ|     mean|Δ|   判定    指纹
  ─────────────────────────────────────────────────────────────────────────────
  decode         (1080,1920,3)      0.000000   0.000000  PASS    -
  to_rgb         (1080,1920,3)      0.000000   0.000000  PASS    -
  resize         (360,640,3)      **49.7000** **21.4000** **FAIL** high_freq  ◄── 首个分歧
  letterbox      (384,640,3)        49.7000    20.0625   FAIL    high_freq
  cast_f32       (384,640,3)        49.7000    20.0625   FAIL    high_freq
  normalize      (384,640,3)         0.8511     0.3437   FAIL    high_freq
  hwc2chw        (3,384,640)         0.8511     0.3437   FAIL    high_freq

  ══════════════════════════════════════════════════════════════════════════
  首个分歧阶段 : resize        （二分探针 3 次，管线共 7 阶段，上界 ⌈log2 8⌉=3）
  diff 指纹    : high_freq     → 插值核不同（缺少抗锯齿）
  两侧配置差异 : resize.interp = 'area'  vs  'linear'      ◄── **直接给出根因**
  建议         : 部署侧改用 INTER_AREA；或两侧统一为 antialias=True 后重训
  ══════════════════════════════════════════════════════════════════════════""")
        ,
        P("<strong>注意这份报告里最后两行才是真正的产出。</strong>前面的表格只是证据；「两侧配置差异」这一行是把<em>数值证据</em>和<em>配置元数据</em>对起来的结果——如果两侧的预处理都从一份声明式配置生成，这一步可以自动完成。<em>这就是第 1 节说的「治本的第 ① 条路」的价值：它让工具从「告诉你哪一步错了」升级到「告诉你哪一行配置错了」。</em>"),
        H3("三个容易忽略的实操细节"),
        OL([
            "<strong>黄金样本要挑「难」的，不要挑「正常」的。</strong>必须覆盖：含 &lt;16 像素小目标的图（暴露 resize 问题）、有过曝/欠曝区的图（暴露 clip 与溢出）、<strong>奇数尺寸</strong>的图（暴露取整与 pad 的边界处理）、纯色大面积的图（此时很多 bug 会互相抵消，用来做反向验证）、极暗帧（暴露 uint8 下溢）。<em>10–30 张，固定入库，连同期望输出一起版本化。</em>",
            "<strong>diff 要在归一化<u>之前</u>也看一眼。</strong>归一化会把所有差异同时除以 $\\sigma\\approx 58$，让 21 灰阶的巨大差异变成 0.37 这个「看起来不大」的数。<em>在灰阶量纲上看 diff，人的直觉才是准的。</em>",
            "<strong>形状不同要单独报，不要混进数值 diff。</strong>形状不同（比如 letterbox 的 <code>auto</code> 开关不同导致 640×384 vs 640×640）会让逐元素比对直接崩溃；工具必须先比形状，形状不等就立即报 <code>SHAPE_MISMATCH</code> 并停止——<em>这类问题往往一眼就能定位，不要让它被淹没在异常堆栈里。</em>",
        ]),
        DUAL(
            "这套工具最大的价值不是「查得快」，而是<strong>「查得确定」</strong>。<em>猜的时候，你不知道自己猜错了；对拍的时候，PASS 就是真的 PASS。</em>一个团队一旦有了这个脚本，「预处理不一致」这个占 40% 的根因就会从常客变成绝迹——<strong>因为它被 CI 挡在了合入之前，而不是在上车后被发现。</strong>",
            "从流程上说，这套工具应当以三种形态存在：<em>①<strong>开发期的交互工具</strong></em>（一条命令，人看报告）；<em>②<strong>CI 门禁</strong></em>（<code>pytest tests/test_preproc_parity.py</code>，每次改预处理、换 OpenCV 版本、改 C++ 管线都跑）；<em>③<strong>发布物的一部分</strong></em>——把黄金样本的期望中间张量随模型一起发布（几 MB），让下游集成方能自证「我这边接对了」。<strong>第 ③ 点在多方协作的量产项目里价值极高：它把「你们的模型不行」这类扯皮，变成一条可执行的判定。</strong>",
        ),
        CALLOUT("danger", "<p><strong>最后一个陷阱，也是面试的好素材：不要只对拍一张图。</strong>某些错误只在特定输入下暴露。例子：<em>①<code>letterbox</code> 的取整分歧只在「缩放后尺寸为奇数」时产生 1 像素差；②<code>uint8</code> 下溢只在暗像素上发生；③<code>clip</code> 的边界处理只在饱和区暴露；④非等比逆变换在正方形输入图上完全正确（因为 $r_x = r_y$），只在 16:9 上出错。</em><strong>如果你的黄金样本只有一张 640×640 的正常曝光图，上面四个 bug 你一个都发现不了。</strong>「一张图对拍通过」给的是虚假的安全感——<em>覆盖度必须是刻意设计的</em>。</p>", "一张图对拍通过 ≠ 一致"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        P("预处理一致性看起来是纯工程问题，但它牵出的几个问题是真开放的，而且都在变得更重要："),
        UL([
            "<strong>resize 的语义至今没有跨库的统一规范，而且短期不会有。</strong>坐标映射 3 种 × 插值核 3 种 × 是否抗锯齿 2 种 × 定点/浮点 2 种 = 36 种组合，各家库的默认值互不相同且因历史包袱无法改动（改了会破坏向后兼容）。<em>ONNX 的 <code>Resize</code> 算子把这些差异编码成显式属性（<code>coordinate_transformation_mode</code>、<code>mode</code>、<code>nearest_mode</code>、<code>antialias</code>），是目前唯一严肃的规范化尝试</em>；<strong>但「规范存在」不等于「转换器正确导出」也不等于「后端正确实现」，这三件事目前只能逐个验证。</strong>",
            "<strong>抗锯齿缺失对学术结果的污染有多大，仍未被系统评估。</strong>Parmar et al. (CVPR 2022) 证明了 GAN 评测的 FID 因 resize 实现不同而显著变化；<em>但检测/分割领域还没有同等规模的审计——有多少「+0.3 mAP 的改进」其实来自预处理实现的差异？</em><strong>这是一个成本不高、结论有实用价值的开放课题</strong>（对同一模型只换 resize 实现，在标准 benchmark 上做审计）。",
            "<strong>可微分 / 可导出的预处理。</strong>如果把 resize、letterbox、归一化都写成模型图的一部分，一起导出、一起量化，<em>语义分歧从定义上就消失了</em>。代价有三：①失去硬件加速路径（很多 SoC 的 resize 是 ISP/VPU 上的固定功能单元，白送的算力就浪费了）；②预处理层会成为新的量化敏感层（输入是 0–255 的 uint8，动态范围与网络内部完全不同）；③动态输入尺寸变得更麻烦。<strong>这个取舍在车端仍无定论，但在云端推理里「预处理进图」已经越来越常见。</strong>",
            "<strong>模型对预处理的鲁棒性能不能被训练出来？</strong>直觉上，用随机的 resize 实现做增强（每个 batch 随机选 area / bilinear / bicubic / 抗锯齿与否），可以让模型对预处理分歧不敏感。<em>已有零散证据显示这有效，但它同时会降低模型对细节的利用能力——相当于主动模糊了训练分布</em>。<strong>「鲁棒性 vs 峰值精度」的这个取舍点在哪里，目前没有系统研究。</strong>",
            "<strong>混叠对小目标的定量影响缺乏理论刻画。</strong>本模块用扫频实验说明「周期 &lt; 2s 的结构全是假的」，但<em>从「混叠能量占比」到「小目标 AP 掉多少」之间还没有可用的模型</em>。<strong>如果有，就可以在设计阶段直接回答「为了在 60 米检出限速牌，输入分辨率至少要多少、能不能下采样」这类问题</strong>——目前这只能靠实验试（C57 模块 05 给的是几何上界，不含混叠项）。",
            "<strong>ISP 与感知的联合优化。</strong>训练用 JPEG 图、部署用 ISP 直出的域差，目前靠增强模拟。<em>更彻底的方向是把 ISP 的参数（去噪强度、锐化、色调映射曲线）纳入下游任务的优化目标——「为机器视觉调 ISP」而不是「为人眼调 ISP」</em>。已有工作（Buckler et al. 2017；后续的 ISP-in-the-loop 研究）显示可以提升下游精度，<strong>但落地需要感知团队与相机团队的组织级协作，量产案例仍然稀少</strong>。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Parmar, Zhang, Zhu, <em>On Aliased Resizing and Surprising Subtleties in GAN Evaluation</em>（CVPR 2022，arXiv:2104.11222）——本模块第 3、4 节的实验设计直接源于它。重点看它对「各库 resize 是否抗锯齿」的对照表，以及 FID 随 resize 实现的变化幅度。<strong>★</strong> ONNX <em>Operators.md · Resize</em>：把 <code>coordinate_transformation_mode</code> 的五种取值（<code>half_pixel</code> / <code>pytorch_half_pixel</code> / <code>align_corners</code> / <code>asymmetric</code> / <code>tf_crop_and_resize</code>）连同公式逐条读完，<em>它会解释你这辈子遇到的绝大多数插值差异</em>。<strong>★</strong> OpenCV <code>modules/imgproc/src/resize.cpp</code> 与 Pillow <code>src/libImaging/Resample.c</code>——<em>直接读这两份源码里权重表的构造部分</em>（各约 100 行），是理解「同一个词、不同的事」最快的路径；重点看 OpenCV 的 <code>INTER_RESIZE_COEF_BITS</code> 定点量化与 Pillow 的 <code>filterscale = max(1, scale)</code>。</p><p>配套背景：Ultralytics YOLOv5 <code>utils/augmentations.py::letterbox</code>（六个自由度的参考实现，注意 <code>auto</code>、<code>scaleFill</code>、<code>scaleup</code> 三个开关与 <code>round(dh-0.1)</code> 的写法）；Buckler, Jayasuriya, Sampson, <em>Reconfiguring the Imaging Pipeline for Computer Vision</em>（ICCV 2017，ISP-感知联合设计）；Zhang, <em>Making Convolutional Networks Shift-Invariant Again</em>（ICML 2019，网络<em>内部</em>下采样的抗锯齿，与本模块是同一个信号处理原理的另一半）。相邻课程：模块 00（三层框架与容差表）、模块 04（后处理与 letterbox 逆变换的 C++ 侧）、C56 模块 01/02（几何与光度增强，letterbox 在训练侧的一面）、C57（小目标为什么对采样如此敏感）、C55（TSR 里颜色即语义）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 01 · 预处理一致性（resize 家族 / letterbox / BGR / 归一化 / 对拍工具）

目标：**不 import cv2、不 import PIL、不 import torch**，从零把它们的 resize 全部实现一遍，
然后量化「写着同一个词、做着不同的事」到底差多少、以及差到什么程度会掉 mAP。

本 notebook 你会亲手实现：
1. **三种坐标映射语义**（half_pixel / align_corners / asymmetric）并量化差异
2. **四种插值核**：nearest、bilinear（无抗锯齿）、INTER_AREA、PIL 式抗锯齿三角核
3. **证明「3 倍下采样时 bilinear 就是 nearest」**——逐位相等，不是近似
4. **混叠的正弦扫频实验**：周期 4px 的假信号如何以 100% 幅度穿过 bilinear
5. **OpenCV 式定点 bilinear**，区分「实现噪声」与「语义错误」
6. **letterbox 的六个自由度** + 正/逆变换的 round-trip 单测 + 四种经典错误写法
7. **一个四类合成 TSR 检测任务**：量化 resize 不一致 / BGR 弄反 / 归一化顺序错各掉多少 mAP
8. **预处理对拍工具**：逐阶段 diff + 二分定位 + 指纹分类 + 定位报告

> 心智模型：**resize 不是「缩放图片」，是「重采样一个信号」。**
> 采样定理不会因为你调的是 `cv2.resize` 就失效。"""),

    md("""## 1 · 坐标映射：输出第 j 个像素对应输入的哪个坐标

三种语义，三种哲学：
- **half_pixel**：像素是**面积**，取覆盖区间的中心 —— `u = (j+0.5)·s − 0.5`
- **align_corners**：像素是**点**，首尾严格对齐 —— `u = j·(H_in−1)/(H_out−1)`
- **asymmetric**：只对齐左上角 —— `u = j·s`"""),

    code("""import numpy as np, math, time
rng = np.random.default_rng(60)
np.set_printoptions(precision=4, suppress=True, linewidth=140)

def coord_map(out_size, in_size, mode='half_pixel'):
    \"\"\"返回长度 out_size 的数组：输出像素 j 对应的输入连续坐标 u(j)。\"\"\"
    j = np.arange(out_size, dtype=np.float64)
    s = in_size / out_size
    if mode == 'half_pixel':                       # OpenCV / PIL / torch(默认) / ONNX(默认)
        return (j + 0.5) * s - 0.5
    if mode == 'align_corners':                    # torch align_corners=True
        return np.zeros(1) if out_size == 1 else j * ((in_size - 1) / (out_size - 1))
    if mode == 'asymmetric':                       # **TensorRT IResizeLayer 的默认值**
        return j * s
    raise ValueError(mode)

print('4 → 8 上采样，三种语义给出的采样坐标：')
for m in ['half_pixel', 'align_corners', 'asymmetric']:
    print(f'  {m:<16s}', coord_map(8, 4, m))

assert np.allclose(coord_map(8, 4, 'half_pixel'),
                   [-0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25])
assert np.allclose(coord_map(8, 4, 'align_corners'), np.arange(8) * 3 / 7)
assert np.allclose(coord_map(8, 4, 'asymmetric'), np.arange(8) * 0.5)
# half_pixel 会越界（-0.25），所以实现里必须 clamp —— 这就是「diff 集中在边缘带」的来源
assert coord_map(8, 4, 'half_pixel')[0] < 0
# half_pixel 与 asymmetric 只差一个常数平移 (s-1)/2
s = 4 / 8
assert np.allclose(coord_map(8, 4, 'half_pixel') - coord_map(8, 4, 'asymmetric'), (s - 1) / 2)
print(f'\\n✅ half_pixel − asymmetric ≡ (s−1)/2 = {(s-1)/2:.3f}（常数平移）')
print('   而 align_corners 的**斜率**不同 → 差异随位置增长 → diff 集中在边缘带。')"""),

    md("""## 2 · 从零实现 nearest / bilinear

`resize_bilinear` 是本 notebook 的主力函数。注意 clamp 的位置——
越界坐标要 clamp 到 `[0, in−1]`，但**小数部分 frac 要在 clamp 之前算**
（这正是各家实现最容易分歧的一行）。"""),

    code("""def _bilinear_idx(out_size, in_size, mode):
    src = coord_map(out_size, in_size, mode)
    x0 = np.floor(src).astype(np.int64)
    frac = src - x0                                 # **frac 在 clamp 之前算**
    return np.clip(x0, 0, in_size-1), np.clip(x0+1, 0, in_size-1), frac

def resize_bilinear(img, oh, ow, mode='half_pixel'):
    img = np.asarray(img, dtype=np.float64)
    H, W = img.shape[:2]
    y0, y1, fy = _bilinear_idx(oh, H, mode)
    x0, x1, fx = _bilinear_idx(ow, W, mode)
    a, b = img[y0][:, x0], img[y0][:, x1]
    c, d = img[y1][:, x0], img[y1][:, x1]
    fx_, fy_ = fx[None, :], fy[:, None]
    if img.ndim == 3:
        fx_, fy_ = fx_[..., None], fy_[..., None]
    return (a*(1-fx_) + b*fx_)*(1-fy_) + (c*(1-fx_) + d*fx_)*fy_

def resize_nearest(img, oh, ow, mode='asymmetric'):
    img = np.asarray(img, dtype=np.float64)
    H, W = img.shape[:2]
    sy = np.clip(np.floor(coord_map(oh, H, mode)).astype(int), 0, H-1)
    sx = np.clip(np.floor(coord_map(ow, W, mode)).astype(int), 0, W-1)
    return img[sy][:, sx]

# —— 手算对拍：2x2 → 1x4（只放大宽度），答案可以口算 ——
tiny = np.array([[0., 10.]])
assert np.allclose(resize_bilinear(tiny, 1, 4, 'align_corners'), [[0, 10/3, 20/3, 10]])
assert np.allclose(resize_bilinear(tiny, 1, 4, 'half_pixel'),   [[0, 2.5, 7.5, 10]])
assert np.allclose(resize_bilinear(tiny, 1, 4, 'asymmetric'),   [[0, 5.0, 10, 10]])
assert np.allclose(resize_nearest(tiny, 1, 4), [[0, 0, 10, 10]])
# 常数图在任何模式下都必须保持常数（这是最基本的健全性检查）
const = np.full((7, 11), 137.0)
for m in ['half_pixel', 'align_corners', 'asymmetric']:
    assert np.allclose(resize_bilinear(const, 3, 5, m), 137.0), m
print('half_pixel   2→4 :', resize_bilinear(tiny, 1, 4, 'half_pixel')[0])
print('align_corners2→4 :', resize_bilinear(tiny, 1, 4, 'align_corners')[0])
print('asymmetric   2→4 :', resize_bilinear(tiny, 1, 4, 'asymmetric')[0])
print('nearest      2→4 :', resize_nearest(tiny, 1, 4)[0])
print('\\n✅ 三种语义在同一段数据上给出三组不同的值 —— 差异是**语义**的，不是精度的。')"""),

    code("""# —— align_corners 的差异在一张自然图上有多大 ——
MEAN = np.array([123.675, 116.28, 103.53]); STD = np.array([58.395, 57.12, 57.375])

yy, xx = np.mgrid[0:64, 0:64]
nat = 128 + 100*np.sin(xx/9.0)*np.cos(yy/7.0)          # 平滑自然图（无细纹理）

hp = resize_bilinear(nat, 32, 32, 'half_pixel')
ac = resize_bilinear(nat, 32, 32, 'align_corners')
asym = resize_bilinear(nat, 32, 32, 'asymmetric')

d_ac = np.abs(hp - ac); d_as = np.abs(hp - asym)
print(f"{'比较':<28s}{'max(灰阶)':>12s}{'mean(灰阶)':>12s}{'mean(tensor)':>14s}")
for nm, d in [('half_pixel vs align_corners', d_ac), ('half_pixel vs asymmetric', d_as)]:
    print(f'{nm:<28s}{d.max():>12.3f}{d.mean():>12.3f}{d.mean()/STD.mean():>14.4f}')

# fp16 的表示误差作为对照
t = (nat - MEAN.mean())/STD.mean()
fp16_err = np.abs(t.astype(np.float32) - t.astype(np.float16).astype(np.float32)).max()
ratio = (d_ac.mean()/STD.mean()) / fp16_err
print(f'\\nfp16 表示误差(max) = {fp16_err:.6f}')
print(f'align_corners 差异是它的 {ratio:.0f} 倍 —— 任何合理的容差都会判 FAIL')

assert 6.0 < d_ac.max() < 6.5 and 2.0 < d_ac.mean() < 2.4, (d_ac.max(), d_ac.mean())
assert 0.035 < d_ac.mean()/STD.mean() < 0.041
assert ratio > 30
# 边缘带 vs 内部：align_corners 的差异集中在边缘（斜率不同 → 位置相关）
edge = np.zeros((32, 32), bool); edge[:3] = edge[-3:] = True; edge[:, :3] = edge[:, -3:] = True
print(f'边缘带平均差 {d_ac[edge].mean():.3f}  vs  内部平均差 {d_ac[~edge].mean():.3f}')
assert d_ac[edge].mean() > d_ac[~edge].mean() * 1.5
print('✅ 边缘带的差异明显更大 —— 这就是「diff 集中在边缘 → 查 align_corners」这条指纹。')"""),

    md("""## 3 · 整数倍缩放的陷阱：half_pixel 下 3× bilinear **就是** nearest

把 half_pixel 代入整数缩放比 s：

    u(j) = (j+0.5)·s − 0.5 = s·j + (s−1)/2

**s 为奇数时 (s−1)/2 是整数 ⇒ u(j) 恒为整数 ⇒ frac ≡ 0 ⇒ 权重 (1,0) ⇒ 退化成最近邻。**

而 1920→640 与 1080→360 都是 s=3。这是车端最常见的一条预处理。"""),

    code("""for s in [2, 3, 4, 5, 6]:
    H = 60*s
    frac = coord_map(60, H, 'half_pixel') - np.floor(coord_map(60, H, 'half_pixel'))
    used = 1.0/(s*s) if s % 2 == 1 else 2.0*2.0/(s*s)      # 参与计算的源像素比例（2D）
    tag = '**退化为 nearest**' if np.allclose(frac, 0) else f'frac ≡ {frac[0]:.2f}'
    print(f's={s}:  (s-1)/2 = {(s-1)/2:>4.1f}   {tag:<22s}  参与计算的源像素 ≈ {used:>6.1%}')
    if s % 2 == 1:
        assert np.allclose(frac, 0), s
    else:
        assert np.allclose(frac, 0.5), s

print('\\n—— 在真实分辨率上验证：1920×1080 → 640×360 (s=3) ——')
big = np.clip(128 + 60*np.sin(np.mgrid[0:360, 0:480][1]/7.0)
              + 40*np.sin(np.mgrid[0:360, 0:480][0]/3.0), 0, 255)   # 用 480x360 代表原图
out_bl = resize_bilinear(big, 120, 160, 'half_pixel')               # 3 倍下采样
out_nn = big[1::3, 1::3]                                            # 直接抽样 u=3j+1
print('bilinear(3×) 与「直接抽 u=3j+1」的最大差 =', np.abs(out_bl - out_nn).max())
assert np.abs(out_bl - out_nn).max() == 0.0, '必须**逐位相等**，不是近似'
print('✅ 逐位相等 —— 3 倍下采样时，双线性没有做任何平均，它只是在抽样。')
print(f'   9 个源像素里只有 1 个被用到，{1-1/9:.1%} 的信息被直接丢弃。')"""),

    md("""## 4 · 抗锯齿：INTER_AREA 与 PIL 式三角核

正确的下采样要求滤波器的支撑集在**输入坐标系**下是 ±s（而不是固定的 ±1）：
- **INTER_AREA**：盒滤波，输出像素 j 覆盖源区间 `[j·s, (j+1)·s)`，权重 = 重叠长度
- **PIL / antialias=True**：三角核，`filterscale = max(1, s)`，支撑集 ±filterscale"""),

    code("""def _area_w(out_size, in_size):
    \"\"\"OpenCV INTER_AREA 的权重矩阵 (out_size, in_size)，每行和为 1。\"\"\"
    s = in_size / out_size
    W = np.zeros((out_size, in_size))
    for j in range(out_size):
        lo, hi = j*s, (j+1)*s
        for i in range(int(np.floor(lo)), min(int(np.ceil(hi)), in_size)):
            W[j, i] = max(0.0, min(hi, i+1) - max(lo, i))
    return W / W.sum(1, keepdims=True)

def _tri_w(out_size, in_size):
    \"\"\"PIL / antialias=True 的三角(bilinear)核：支撑集随缩放比拉伸。\"\"\"
    s = in_size / out_size
    fscale = max(1.0, s); support = 1.0 * fscale
    W = np.zeros((out_size, in_size))
    for j in range(out_size):
        c = (j + 0.5) * s
        for i in range(max(0, int(np.floor(c-support+0.5))),
                       min(in_size, int(np.ceil(c+support+0.5)))):
            W[j, i] = max(0.0, 1.0 - abs((i + 0.5 - c) / fscale))
    return W / W.sum(1, keepdims=True)

def _sep(img, Wy, Wx):
    tmp = np.tensordot(Wy, img, axes=([1], [0]))        # (oh, W, ...)
    return np.swapaxes(np.tensordot(Wx, tmp, axes=([1], [1])), 0, 1)

def resize_area(img, oh, ow):
    img = np.asarray(img, float); H, W = img.shape[:2]
    return _sep(img, _area_w(oh, H), _area_w(ow, W))

def resize_antialias(img, oh, ow):
    img = np.asarray(img, float); H, W = img.shape[:2]
    return _sep(img, _tri_w(oh, H), _tri_w(ow, W))

# 健全性：权重每行和为 1；常数图保持常数；整数倍时 area = 块平均
for f in (_area_w, _tri_w):
    assert np.allclose(f(7, 21).sum(1), 1.0)
assert np.allclose(resize_area(np.full((9, 12), 5.0), 3, 4), 5.0)
assert np.allclose(resize_antialias(np.full((9, 12), 5.0), 3, 4), 5.0)
blk = np.arange(36.).reshape(6, 6)
assert np.allclose(resize_area(blk, 3, 3), blk.reshape(3, 2, 3, 2).mean((1, 3)))
print('AREA 在 2× 下采样时严格等于 2×2 块平均：')
print(resize_area(blk, 3, 3))
print('\\n✅ 三个 resize 实现就位：resize_bilinear / resize_area / resize_antialias')"""),

    code("""# —— 混叠：正弦扫频（3 倍下采样，源幅度 100）——
x = np.arange(96)
print('输出端可表示的最细周期 = 2·s = 6 px（原图坐标）。比它细的一切都是假的。\\n')
print(f"{'原图周期':>10s}{'可表示?':>9s}{'bilinear':>11s}{'AREA':>9s}{'抗锯齿':>9s}")
res = {}
for period in [3, 4, 5, 6, 8, 12, 24]:
    sig = np.tile(128 + 100*np.sin(2*np.pi*x/period), (6, 1))
    amp = lambda a: (a.max() - a.min())/2
    b = amp(resize_bilinear(sig, 2, 32, 'half_pixel')[0])
    a_ = amp(resize_area(sig, 2, 32)[0])
    t_ = amp(resize_antialias(sig, 2, 32)[0])
    res[period] = (b, a_, t_)
    ok = '✅' if period >= 6 else '❌'
    print(f'{period:>10d}{ok:>8s}{b:>11.1f}{a_:>9.1f}{t_:>9.1f}')

b4, a4, t4 = res[4]
assert b4 > 99, '周期 4px 在输出端根本不可表示，bilinear 却原样通过 -> 100% 假信号'
assert a4 < 40 and t4 < 25, (a4, t4)
b5, a5, t5 = res[5]
assert b5 > 90 and a5 < 60
assert res[3][0] < 1e-6, '周期 3px 恰好等于采样步长 -> 被抽成常数'
print('\\n⚠️  周期 4px：输出端**不可能存在**这个结构，bilinear 却让它以 100% 幅度通过 ——')
print('   它在输出图上变成了一条凭空捏造的粗条纹。AREA 压到 33，抗锯齿三角核压到 18。')
print('✅ TSR 含义：1920→640 后，原图上笔画宽度 < 3px 的一切（限速数字的笔画！）都是假的。')"""),

    code("""# —— 在一张带细纹理的自然图上：480 → 160（3 倍）——
YY, XX = np.mgrid[0:480, 0:480]
im = np.clip(120 + 60*np.sin(XX/40.)*np.cos(YY/33.)
             + 45*np.sin(2*np.pi*XX/5.) + 45*np.sin(2*np.pi*YY/4.), 0, 255)
B = resize_bilinear(im, 160, 160, 'half_pixel')
A = resize_area(im, 160, 160)
T = resize_antialias(im, 160, 160)

print(f"{'':<22s}{'输出 std':>10s}{'与 AREA 的 mean|Δ|':>20s}{'max|Δ|':>10s}")
print(f"{'原图':<22s}{im.std():>10.2f}{'—':>20s}{'—':>10s}")
for nm, o in [('无抗锯齿 bilinear', B), ('INTER_AREA', A), ('抗锯齿 bilinear', T)]:
    print(f'{nm:<22s}{o.std():>10.2f}{np.abs(o-A).mean():>20.2f}{np.abs(o-A).max():>10.2f}')

# bilinear 在 3× 下就是抽样 —— 逐位相等
assert np.abs(B - im[1::3, 1::3]).max() == 0.0
assert abs(B.std() - im.std()) < 0.5, '抽样不改变高频能量 -> std 几乎不变'
mean_d, max_d = np.abs(B - A).mean(), np.abs(B - A).max()
print(f'\\n无抗锯齿 vs AREA: mean {mean_d:.2f} 灰阶, max {max_d:.2f} 灰阶'
      f'  → {mean_d/STD.mean():.3f} tensor 单位')
assert 20 < mean_d < 23 and 45 < max_d < 55, (mean_d, max_d)
assert np.abs(T - A).mean() < 10, '两个都抗锯齿的实现之间差异小得多'
print('✅ 分水岭是「有没有抗锯齿」，不是「用了哪家库」：')
print(f'   无抗锯齿 vs AREA = {mean_d:.1f} 灰阶；两种抗锯齿实现之间只差 {np.abs(T-A).mean():.1f} 灰阶。')
print(f'⚠️  {mean_d/STD.mean():.2f} tensor 单位 = 模块 00 容差表里「resize 语义错误」那一档。')"""),

    md("""## 5 · 定点实现噪声 vs 语义错误：容差放在哪

OpenCV 对 8 位图走**定点**路径：插值权重量化到 1/2048（`INTER_RESIZE_COEF_BITS=11`），
结果四舍五入回 uint8。**即使语义完全一致，它和一个 float64 教科书实现之间也有差。**
知道这个差有多大，你才敢设容差。"""),

    code("""def resize_bilinear_fixed(img, oh, ow, bits=11):
    \"\"\"OpenCV 式：权重量化到 1/2^bits，输出四舍五入回整数。\"\"\"
    img = np.asarray(img, float); H, W = img.shape[:2]
    y0, y1, fy = _bilinear_idx(oh, H, 'half_pixel')
    x0, x1, fx = _bilinear_idx(ow, W, 'half_pixel')
    S = 1 << bits
    fxq = np.round(np.clip(fx, 0, 1)*S)/S
    fyq = np.round(np.clip(fy, 0, 1)*S)/S
    a, b = img[y0][:, x0], img[y0][:, x1]
    c, d = img[y1][:, x0], img[y1][:, x1]
    top = a*(1-fxq[None, :]) + b*fxq[None, :]
    bot = c*(1-fxq[None, :]) + d*fxq[None, :]
    return np.round(top*(1-fyq[:, None]) + bot*fyq[:, None])

Bf = resize_bilinear_fixed(im, 200, 200)          # 用非整数倍缩放，让 frac 真的起作用
Bx = resize_bilinear(im, 200, 200, 'half_pixel')
dfix = np.abs(Bf - Bx)
print(f'定点 vs float64（同一语义）: max {dfix.max():.4f}  mean {dfix.mean():.4f} 灰阶')
print(f'超过 1 灰阶的像素比例: {(dfix > 1).mean():.6%}')
assert dfix.max() < 0.6 and dfix.mean() < 0.3   # 0.5 来自取整，多出的一点来自权重量化
assert (dfix > 1).mean() == 0.0

print(f"\\n{'差异来源':<26s}{'tensor 单位':>14s}{'该不该报警':>12s}")
LEDGER = [('fp16 表示误差',          fp16_err,                    '❌ 不报'),
          ('定点舍入(max≈0.52 灰阶)', dfix.max()/STD.mean(),       '❌ 不报'),
          ('align_corners 语义不同', d_ac.mean()/STD.mean(),      '✅ 报'),
          ('抗锯齿缺失(AREA↔LINEAR)', mean_d/STD.mean(),          '✅ 报')]
for nm, v, w in LEDGER:
    print(f'{nm:<26s}{v:>14.5f}{w:>12s}')
TOL_MAX, TOL_MEAN = 0.02, 0.005
gap_lo, gap_hi = LEDGER[1][1], LEDGER[2][1]
print(f'\\n最窄的一道缝：{gap_lo:.4f} ~ {gap_hi:.4f}（{gap_hi/gap_lo:.1f} 倍），'
      f'阈值 max<={TOL_MAX} 正好卡在中间。')
assert gap_lo < TOL_MAX < gap_hi, (gap_lo, gap_hi)
assert LEDGER[0][1] < TOL_MAX and LEDGER[3][1] > TOL_MAX
print('✅ 同一组阈值：放过 fp16 与定点舍入，拦住 align_corners 与抗锯齿缺失。')"""),

    md("""## 6 · letterbox 的六个自由度

1) pad 值 2) pad 位置（居中/左上） 3) pad 到哪（方形 / stride 倍数）
4) 缩放比取整 5) 是否允许放大 6) pad 的奇偶分配

先算一笔账：车载相机是 16:9 的，`1920×1080 → 640` 时两种方案的算力差异。"""),

    code("""def letterbox(h0, w0, target=640, pad_value=114, center=True, stride=None, scaleup=True):
    \"\"\"只算几何参数，不真的填像素 —— 一致性问题全在这些参数里。\"\"\"
    r = min(target/h0, target/w0)
    if not scaleup:
        r = min(r, 1.0)
    nw, nh = int(round(w0*r)), int(round(h0*r))
    dw, dh = target-nw, target-nh
    if stride:                                   # YOLOv5 的 auto=True：只 pad 到 stride 倍数
        dw, dh = dw % stride, dh % stride
    left, top = (dw//2, dh//2) if center else (0, 0)
    oh, ow = nh+dh, nw+dw
    return dict(r=r, new=(nh, nw), top=top, left=left, out=(oh, ow),
                pad_value=pad_value, pad_frac=1 - (nh*nw)/(oh*ow))

H0, W0 = 1080, 1920
variants = [
    ('A 方形 pad, 居中, 114',   dict(stride=None, center=True,  pad_value=114)),
    ('B 方形 pad, 左上, 114',   dict(stride=None, center=False, pad_value=114)),
    ('C 方形 pad, 居中, 0',     dict(stride=None, center=True,  pad_value=0)),
    ('D stride32, 居中, 114',   dict(stride=32,   center=True,  pad_value=114)),
    ('E stride64, 居中, 114',   dict(stride=64,   center=True,  pad_value=114)),
]
print(f"{'变体':<24s}{'r':>8s}{'输出形状':>14s}{'上 pad':>8s}{'灰边占比':>10s}")
LB = {}
for nm, kw in variants:
    lb = letterbox(H0, W0, 640, **kw); LB[nm[0]] = lb
    print(f"{nm:<24s}{lb['r']:>8.4f}{str(lb['out']):>14s}{lb['top']:>8d}{lb['pad_frac']:>10.2%}")

assert LB['A']['out'] == (640, 640) and LB['A']['top'] == 140
assert abs(LB['A']['pad_frac'] - 0.4375) < 1e-9, LB['A']['pad_frac']
assert LB['D']['out'] == (384, 640) and abs(LB['D']['pad_frac'] - 0.0625) < 1e-9
assert LB['E']['out'] == (384, 640)          # 280 % 64 == 24 == 280 % 32，两者巧合相同
assert LB['B']['top'] == 0
saved = 1 - (384*640)/(640*640)
print(f'\\n✅ 方形 pad 有 {LB["A"]["pad_frac"]:.2%} 的张量是灰边 —— {LB["A"]["pad_frac"]:.2%} 的卷积在算灰色。')
print(f'   换成 stride 倍数 pad：640×384，省下 {saved:.1%} 的推理算力，几乎白送。')
print('⚠️  代价是输入形状不再固定 → TensorRT 需要动态 shape 的 optimization profile（模块 02）。')
print('   很多量产系统仍用方形 pad，不是没算过账，是不想引入动态 shape 的复杂度。')"""),

    code("""# —— 正/逆变换：round-trip 单测 + 四种经典错误 ——
def lb_forward(xy, lb):
    \"\"\"原图坐标 -> letterbox 坐标。xy: (N,2) 或 (N,4) 的 xyxy\"\"\"
    xy = np.asarray(xy, float).copy()
    off = np.array([lb['left'], lb['top']] * (xy.shape[1]//2))
    return xy*lb['r'] + off

def lb_inverse(xy, lb, W0=W0, H0=H0):
    \"\"\"letterbox 坐标 -> 原图坐标（**唯一正确的写法**）\"\"\"
    xy = np.asarray(xy, float).copy()
    off = np.array([lb['left'], lb['top']] * (xy.shape[1]//2))
    out = (xy - off) / lb['r']
    out[:, 0::2] = np.clip(out[:, 0::2], 0, W0)      # **clip 必须放在最后**
    out[:, 1::2] = np.clip(out[:, 1::2], 0, H0)
    return out

lb = LB['A']
r2 = np.random.default_rng(1)
pts = np.sort(r2.uniform(0, 1, (1000, 4)), axis=1) * np.array([W0, H0, W0, H0])
pts = pts[:, [0, 1, 2, 3]]
pts[:, 2] = np.maximum(pts[:, 2], pts[:, 0] + 1); pts[:, 3] = np.maximum(pts[:, 3], pts[:, 1] + 1)
assert np.abs(lb_inverse(lb_forward(pts, lb), lb) - pts).max() < 1e-6
print(f'round-trip 单测：1000 个随机框，最大误差 {np.abs(lb_inverse(lb_forward(pts,lb),lb)-pts).max():.2e}  ✅')

box_lb = lb_forward(np.array([[900., 400., 980., 480.]]), lb)     # 原图上一个 80x80 的牌子
right = lb_inverse(box_lb, lb)[0]
bad_nopad   = (box_lb / lb['r'])[0]                                # ❌ 忘了减 pad
bad_nonunif = (box_lb * np.array([W0/640, H0/640, W0/640, H0/640]))[0]   # ❌ 非等比还原
print(f"\\n{'写法':<30s}{'还原出的框 (x1,y1,x2,y2)':>34s}{'y 方向偏移':>12s}")
print(f"{'✅ 正确 (x-pad)/r':<30s}{str(np.round(right,1)):>34s}{0.0:>12.1f}")
for nm, v in [('❌ x/r（忘了减 pad）', bad_nopad), ('❌ x·W0/640（非等比）', bad_nonunif)]:
    print(f'{nm:<30s}{str(np.round(v,1)):>34s}{v[1]-right[1]:>12.1f}')

assert np.allclose(right, [900, 400, 980, 480])
assert abs((bad_nopad[1] - right[1]) - lb['top']/lb['r']) < 1e-6
print(f"\\n⚠️  忘了减 pad：y 整体偏 top/r = {lb['top']}/{lb['r']:.4f} = "
      f"{lb['top']/lb['r']:.0f} 像素 = 图高的 {lb['top']/lb['r']/H0:.0%}")
print('   识别法：**所有框偏移同一个常数 → 一定是坐标变换，不可能是模型**。')

def iou_shift(size, dx, dy):
    ix, iy = max(0, size-abs(dx)), max(0, size-abs(dy))
    inter = ix*iy
    return inter/(2*size*size - inter)
print(f'\\n最难查的是 1 像素的系统性偏移（pad 取整不一致）。对一个 8×8 的标志：')
for dx, dy in [(1, 0), (2, 0), (2, 2)]:
    print(f'  平移 ({dx},{dy}) px -> IoU = {iou_shift(8, dx, dy):.4f}')
assert abs(iou_shift(8, 1, 0) - 56/72) < 1e-12
assert abs(iou_shift(8, 2, 0) - 48/80) < 1e-12
assert abs(iou_shift(8, 2, 2) - 36/92) < 1e-12
assert iou_shift(64, 2, 2) > 0.88, '同样 2px，64×64 的框几乎不受影响'
print(f'  对照：64×64 的框平移 (2,2) px，IoU 还有 {iou_shift(64,2,2):.4f}')
print('✅ 1px 的坐标 bug 在 COCO（大目标为主）上几乎不可见，在 TSR 上能吃掉 5–10 mAP。')"""),

    md("""## 7 · BGR/RGB 与归一化：模型照跑，mAP 全掉

先看归一化的两个经典错误（都不会报错、都不会崩），再用一个合成检测任务量化代价。"""),

    code("""# —— ① 归一化顺序错：动态范围压缩正好 255 倍 ——
lo_ok,  hi_ok  = (0 - MEAN)/STD,        (255 - MEAN)/STD
lo_bad, hi_bad = (0/255 - MEAN)/STD,    (1.0 - MEAN)/STD
print('✅ 正确 (x-mean)/std      范围', np.round(lo_ok, 4), '~', np.round(hi_ok, 4),
      ' 跨度', np.round(hi_ok-lo_ok, 4))
print('❌ 先 /255 再用同一组参数 范围', np.round(lo_bad, 4), '~', np.round(hi_bad, 4),
      ' 跨度', np.round(hi_bad-lo_bad, 6))
ratio = (hi_ok-lo_ok)/(hi_bad-lo_bad)
print('\\n压缩倍数 =', np.round(ratio, 6), ' → **与 mean/std 的具体取值无关，恒等于 255**')
assert np.allclose(ratio, 255.0)

# —— ② 在 uint8 上做减法：下溢回绕 ——
px  = np.array([10, 60, 124, 200], dtype=np.uint8)
sub = np.full(4, 124, dtype=np.uint8)
print('\\nuint8 减法:', px, '-', sub, '=', px - sub)
assert (px - sub).tolist() == [142, 192, 0, 76]
print('⚠️  10-124 = -114 → mod 256 → **142**：图上最暗的像素变成了最亮的。')
print('   指纹：diff 只在暗区（像素 < mean）非零，且差值恰好是 256。')
print('   表现：白天正常、夜间全崩 —— 极易被误判成「夜间数据不够」（最贵的那条路）。')

# —— ③ 5 行 assert 挡住上面所有变体 ——
def sanity(t, name=''):
    t = np.asarray(t, float)
    ch = tuple(range(t.ndim-1)) if t.ndim == 3 else None
    ok = dict(std_ok=0.8 <= t.std() <= 1.2,
              mean_ok=abs(t.mean()) <= 0.5,
              range_ok=(t.min() > -3) and (t.max() < 3),
              ch_mean_ok=bool(np.all(np.abs(t.mean(axis=ch)) <= 0.5)))
    return all(ok.values()), ok

raw = np.stack([im, im*0.9, im*0.8], -1)
REF = (raw - MEAN)/STD                                   # 训练侧的参考张量
tests = {
    '✅ 正确':            REF,
    '❌ 先 /255':         (raw/255 - MEAN)/STD,
    '❌ 忘了归一化':       raw,
    '❌ 多除了一次 255':   (raw - MEAN)/STD/255,
    '❌ mean/std 反了序':  (raw - MEAN[::-1])/STD[::-1],
}
print(f"\\n{'场景':<20s}{'std':>9s}{'mean':>9s}{'min':>9s}{'max':>9s}{'自检':>7s}{'对拍':>7s}")
for nm, t in tests.items():
    good, det = sanity(t)
    par = 'PASS' if np.abs(t - REF).max() <= 0.02 else 'FAIL'
    print(f'{nm:<20s}{t.std():>9.3f}{t.mean():>9.3f}{t.min():>9.2f}{t.max():>9.2f}'
          f'{str(good):>7s}{par:>7s}')
assert sanity(tests['✅ 正确'])[0]
for k in ['❌ 先 /255', '❌ 忘了归一化', '❌ 多除了一次 255']:
    assert not sanity(tests[k])[0], k
# **最隐蔽的一个：mean/std 顺序反了，四条自检全部通过**
assert sanity(tests['❌ mean/std 反了序'])[0], 'std/mean/range 都在正常区间里'
assert np.abs(tests['❌ mean/std 反了序'] - REF).max() > 0.02, '但对拍立刻发现'
print('\\n✅ 三条自检（std / mean / range）5 行代码挡住：少除 255、多除 255、忘了归一化。')
print('⚠️  但最后一行 **四条自检全部通过**：mean/std 顺序反了时，std 正常、逐通道 mean')
print('   的偏移只有 0.3 左右，落在任何合理阈值内。**只有对拍能抓到它。**')
print('   这就是「自检 ≠ 对拍」：自检查的是「看起来正不正常」，对拍查的是「和训练侧一不一样」。')"""),

    md("""### 7.1 四类合成 TSR 检测任务

- **限速60 / 限速80**：同为红环白面，只有内部细笔画不同 → **细粒度、依赖高频**
- **蓝色指示 / 黄色警告**：靠大色块区分 → **粗粒度、依赖颜色**

检测器刻意做成两段（模拟真实检测器）：
**定位靠灰度局部对比度（对通道置换完全不变）**，**分类靠归一化后的颜色特征（对通道置换极敏感）**。"""),

    code("""HI, LO, S = 288, 96, 3                # 高分辨率画布 -> 网络输入（3 倍下采样）
SGN_HI, SGN_LO = 36, 12               # 标志在两个尺度下的边长（12 px = TSR 的典型尺寸）
CLS = ['限速60(红)', '限速80(红)', '指示(蓝)', '警告(黄)']

def draw_sign(canvas, cx, cy, cls, r_):
    r = SGN_HI//2
    yy_, xx_ = np.mgrid[-r:r, -r:r]; d = np.hypot(xx_, yy_)
    p = np.zeros((SGN_HI, SGN_HI, 3)); m = d < r
    if cls in (0, 1):
        p[...] = [205., 35., 45.]; p[d < r*0.74] = [238., 238., 234.]
        for b in ([-9, 0, 9] if cls == 1 else [-6, 6]):        # 3px 宽笔画 = 低分辨率下 1px
            p[(np.abs(xx_-b) < 1.5) & (np.abs(yy_) < 10)] = [35., 35., 38.]
    elif cls == 2:
        p[...] = [25., 65., 175.]
        p[(np.abs(xx_) < 3) & (yy_ > -10)] = [240.]*3
        p[(np.abs(xx_) + np.abs(yy_+8) < 8) & (yy_ < -2)] = [240.]*3
    else:
        p[...] = [240., 200., 40.]
        p[(np.abs(xx_) < 2) & (yy_ > -6) & (yy_ < 8)] = [30.]*3
        m = (yy_ > -r*0.85) & (np.abs(xx_) < (yy_ + r*0.85)*0.62)
    y0, x0 = cy-r, cx-r
    reg = canvas[y0:y0+SGN_HI, x0:x0+SGN_HI]
    reg[m] = p[m] * r_.uniform(0.88, 1.08)
    return (x0, y0, x0+SGN_HI, y0+SGN_HI)

def make_scene(r_):
    y_, x_ = np.mgrid[0:HI, 0:HI]
    c = np.stack([110+40*np.sin(x_/47.), 118+35*np.cos(y_/39.), 125+30*np.sin((x_+y_)/61.)], -1)
    c = c + 18*np.sin(2*np.pi*x_/5.)[..., None] + 14*np.sin(2*np.pi*y_/4.)[..., None]
    for _ in range(4):                                          # 干扰块
        h, w = r_.integers(14, 40, 2); y, x = r_.integers(0, HI-40, 2)
        c[y:y+h, x:x+w] += r_.uniform(-55, 55, 3)
    cls = int(r_.integers(0, 4)); cx, cy = r_.integers(24, HI-24, 2)
    box = draw_sign(c, cx, cy, cls, r_)          # 必须先画再 clip（否则拿到的是空场景）
    return np.clip(c, 0, 255), box, cls

def prep(img, resize='area', swap=False, norm='ok'):
    \"\"\"完整的预处理：resize -> (可选)通道置换 -> 归一化\"\"\"
    x = {'area': resize_area, 'antialias': resize_antialias}.get(
        resize, lambda a, b, c: resize_bilinear(a, b, c, 'half_pixel'))(img, LO, LO)
    if swap:
        x = x[..., ::-1]
    return (x - MEAN)/STD if norm == 'ok' else (x/255.0 - MEAN)/STD

srng = np.random.default_rng(60)
TRAIN = [make_scene(srng) for _ in range(60)]
TEST  = [make_scene(srng) for _ in range(100)]
print(f'训练 {len(TRAIN)} 张 / 测试 {len(TEST)} 张，每张 1 个标志，'
      f'高分辨率 {HI}×{HI} -> 网络输入 {LO}×{LO}（3 倍下采样，和 1920→640 同构）')
print('类别分布(测试):', np.bincount([c for _, _, c in TEST], minlength=4).tolist(), CLS)"""),

    code("""def windows(t, st=2, n=SGN_LO):
    ys = np.arange(0, LO-n+1, st); xs = np.arange(0, LO-n+1, st)
    Pw = t[ys[:, None]+np.arange(n)][:, :, xs[:, None]+np.arange(n)].transpose(0, 2, 1, 3, 4)
    B = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2).astype(float)
    M = len(ys)*len(xs)
    return (Pw.reshape(M, -1),                                  # 分类特征
            Pw.mean(-1).reshape(M, n*n).std(1),                 # objectness：**灰度**局部对比度
            np.concatenate([B, B+n], 1))

def split_feat(F, w):
    \"\"\"[ (1-w)·灰度 , w·色度 ]。灰度在通道置换下不变，色度会被置换 -> w 就是「颜色依赖度」。\"\"\"
    G = F.reshape(len(F), -1, 3); g = G.mean(-1)
    return np.concatenate([(1-w)*g, w*(G - g[..., None]).reshape(len(F), -1)], 1)

def protos_of(scenes, w, **kw):
    acc = {c: [] for c in range(4)}
    for img, box, cls in scenes:
        t = prep(img, **kw); x0, y0 = box[0]//S, box[1]//S
        acc[cls].append(t[y0:y0+SGN_LO, x0:x0+SGN_LO].ravel())
    return split_feat(np.array([np.mean(acc[c], 0) for c in range(4)]), w)

def detect(img, protos, w, tau=40.0, **kw):
    F, O, B = windows(prep(img, **kw)); F = split_feat(F, w)
    d2 = (F**2).sum(1)[:, None] - 2*F@protos.T + (protos**2).sum(1)[None]
    lg = -d2/(2*tau); lg -= lg.max(1, keepdims=True)
    p = np.exp(lg); p /= p.sum(1, keepdims=True)
    conf = (O/(O.max()+1e-9)) * p.max(1)                        # 定位×分类
    i = int(np.argmax(conf))
    return B[i], int(np.argmax(p[i])), float(conf[i])

def iou1(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1]); x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    it = max(0, x2-x1)*max(0, y2-y1)
    return it/((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - it + 1e-9)

def voc_ap(rec, pre):
    mr = np.concatenate([[0], rec, [1]]); mp = np.concatenate([[0], pre, [0]])
    for i in range(len(mp)-2, -1, -1):
        mp[i] = max(mp[i], mp[i+1])
    k = np.where(mr[1:] != mr[:-1])[0]
    return float(((mr[k+1]-mr[k])*mp[k+1]).sum())

def evaluate(scenes, protos, w, **kw):
    dets = {c: [] for c in range(4)}; npos = {c: 0 for c in range(4)}
    pred, loc_ok = [], []
    for img, box, cls in scenes:
        npos[cls] += 1
        gtb = (box[0]/S, box[1]/S, box[2]/S, box[3]/S)
        pb, pc, sc = detect(img, protos, w, **kw)
        pred.append(pc); loc_ok.append(iou1(pb, gtb) >= 0.5)     # **类别无关**的定位召回
        dets[pc].append((sc, (pc == cls) and iou1(pb, gtb) >= 0.5))
    aps = []
    for c in range(4):
        d = sorted(dets[c], key=lambda z: -z[0])
        if not d:
            aps.append(0.0); continue
        tp = np.cumsum([1 if o else 0 for _, o in d]); fp = np.cumsum([0 if o else 1 for _, o in d])
        aps.append(voc_ap(tp/max(npos[c], 1), tp/np.maximum(tp+fp, 1e-9)))
    return dict(mAP=float(np.mean(aps)), AP=aps,
                loc=float(np.mean(loc_ok)), pred=np.bincount(pred, minlength=4))

W_COLOR = 0.5
PROTOS = protos_of(TRAIN, W_COLOR, resize='area')     # 「训练侧」用 AREA + RGB + 正确归一化
print('原型就位（4 类 × %d 维），训练侧预处理 = AREA + RGB + (x-mean)/std' % PROTOS.shape[1])"""),

    code("""t0 = time.time()
CONDS = [('① 完全一致（基线）',      dict(resize='area')),
         ('② AREA→INTER_LINEAR',   dict(resize='linear')),
         ('③ AREA→抗锯齿 bilinear', dict(resize='antialias')),
         ('④ BGR/RGB 弄反',        dict(resize='area', swap=True)),
         ('⑤ 归一化顺序错',         dict(resize='area', norm='bad')),
         ('⑥ ②+④ 叠加',            dict(resize='linear', swap=True))]
R = {}
print(f"{'条件':<24s}{'mAP':>7s}{'定位召回':>9s}   逐类 AP  " + ' / '.join(CLS))
for nm, kw in CONDS:
    R[nm[0]] = evaluate(TEST, PROTOS, W_COLOR, **kw)
    r_ = R[nm[0]]
    print(f"{nm:<24s}{r_['mAP']:>7.3f}{r_['loc']:>9.2f}   " +
          '  '.join(f'{a:.2f}' for a in r_['AP']))
print(f'（{time.time()-t0:.1f}s）')

b, l, a2, sw, nb = R['①'], R['②'], R['③'], R['④'], R['⑤']
assert b['mAP'] > 0.70, b['mAP']
# ② resize 不一致：整体掉幅温和，但**全部集中在两个细粒度红牌类**
d_fine   = (b['AP'][0]+b['AP'][1]) - (l['AP'][0]+l['AP'][1])
d_coarse = (b['AP'][2]+b['AP'][3]) - (l['AP'][2]+l['AP'][3])
print(f"\\n② resize 不一致: 整体 mAP {b['mAP']:.3f} → {l['mAP']:.3f}（−{b['mAP']-l['mAP']:.3f}，"
      f'很容易被当成种子噪声放过）')
print(f'   但两个**细粒度红牌类**的 AP 合计掉了 {d_fine:.2f}，'
      f'两个靠颜色区分的粗类合计变化 {-d_coarse:+.2f}')
assert d_fine > 0.20 and abs(d_coarse) < 0.12, (d_fine, d_coarse)
assert abs(a2['mAP'] - b['mAP']) < 0.03, '两种都抗锯齿的实现之间几乎无差'
# ④ BGR：定位完好、类别全错
print(f"\\n④ BGR 弄反: mAP {sw['mAP']:.3f}，但**类别无关定位召回仍有 {sw['loc']:.2f}** —— "
      f'框全在，只是类别全错')
print(f"   预测类别分布 {sw['pred'].tolist()} vs 真值 "
      f"{np.bincount([c for _,_,c in TEST], minlength=4).tolist()}"
      f" → {sw['pred'].max()}/100 全被判成「{CLS[int(sw['pred'].argmax())]}」")
assert sw['mAP'] < 0.05 and sw['loc'] > 0.8, (sw['mAP'], sw['loc'])
# ⑤ 归一化顺序错：输出塌缩到单一类别
print(f"\\n⑤ 归一化顺序错: 预测类别分布 {nb['pred'].tolist()} —— 全部塌缩到一个类")
assert nb['pred'].max() >= 90
print('\\n✅ 「整体指标掩盖关键类崩塌」+「框全在但类别全错」= 预处理 bug「最隐蔽」的两种形态。')"""),

    code("""# —— 颜色依赖度 w 扫描：BGR 弄反的代价取决于模型多依赖颜色 ——
t0 = time.time()
print(f"{'w (颜色依赖度)':>14s}{'正确 RGB mAP':>14s}{'BGR 弄反 mAP':>14s}{'Δ':>9s}")
deltas = []
for w in [0.0, 0.2, 0.5, 0.8]:
    Pw = protos_of(TRAIN, w, resize='area')
    m0 = evaluate(TEST, Pw, w, resize='area')['mAP']
    m1 = evaluate(TEST, Pw, w, resize='area', swap=True)['mAP']
    deltas.append(m0-m1)
    print(f'{w:>14.1f}{m0:>14.3f}{m1:>14.3f}{m0-m1:>+9.3f}')
print(f'（{time.time()-t0:.1f}s）')
assert abs(deltas[0]) < 0.02, 'w=0 时特征完全是灰度的，通道置换必须毫无影响'
assert deltas[-1] > 0.5 and deltas[1] > 0.3
assert deltas[1] < deltas[-1], '颜色依赖度越高，代价越大'
print('\\n✅ 结论：**模型对颜色的依赖度越高，通道顺序错误的代价越大。**')
print('   而 TSR 是所有视觉任务里颜色依赖度最高的之一 —— 红=禁令、蓝=指示、黄=警告，')
print('   **颜色就是语义**（C56 模块 02）。所以 BGR/RGB 弄反在通用检测里是中等 bug，')
print('   在 TSR 里是致命 bug。合成实验掉到 0 是因为分类器纯靠颜色；')
print('   真实 CNN 还会用形状与纹理，典型实际掉幅是 **10–30 mAP**，不会归零。')"""),

    md("""## 8 · 预处理对拍工具

把预处理写成**命名阶段的序列**（而不是一个 80 行的大函数），
然后：逐阶段 diff → 二分定位首个分歧 → diff 指纹分类 → 输出定位报告。"""),

    code("""STAGES = ['to_rgb', 'resize', 'letterbox_pad', 'normalize', 'hwc2chw']

def OPS(name, t, cfg):
    if name == 'to_rgb':
        return t[..., ::-1] if cfg.get('swap_channels') else t
    if name == 'resize':
        k = cfg.get('resize', 'area')
        return {'area': resize_area, 'antialias': resize_antialias}.get(
            k, lambda a, b, c: resize_bilinear(a, b, c, 'half_pixel'))(t, LO, LO)
    if name == 'letterbox_pad':
        p = cfg.get('pad', 0)
        return np.pad(t, ((p, p), (p, p), (0, 0)), constant_values=cfg.get('pad_value', 114))
    if name == 'normalize':
        return (t/255.0 - MEAN)/STD if cfg.get('norm') == 'bad' else (t - MEAN)/STD
    if name == 'hwc2chw':
        return np.ascontiguousarray(np.moveaxis(t, -1, 0))
    raise ValueError(name)

def run_pipeline(img, cfg):
    t, out = np.asarray(img, float), {}
    for name in STAGES:
        t = OPS(name, t, cfg); out[name] = t
    return out

def fingerprint(a, b, tol=2e-3):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return 'shape_mismatch'
    d = b - a
    if np.abs(d).max() <= tol:
        return 'noise'
    ch = lambda z: float(np.mean(np.std(z, axis=tuple(range(z.ndim-1)) if z.ndim == 3 else None)))
    if ch(b) < 0.1*ch(a):                                        # **逐通道**看，不能看整体
        return 'range_collapse'                                  # 归一化顺序错的专属指纹
    if a.ndim == 3 and a.shape[-1] == 3 and np.abs(b[..., ::-1] - a).max() <= tol:
        return 'channel_swap'
    e = np.zeros(a.shape[:2], bool)
    if min(a.shape[:2]) > 6:                                     # 太小的图不做边缘带判定
        e[:2] = e[-2:] = True; e[:, :2] = e[:, -2:] = True
        de, di = np.abs(d[e]).mean(), np.abs(d[~e]).mean()
        if di < 1e-9 or de/max(di, 1e-12) > 20:
            return 'border'
    ax = tuple(range(d.ndim-1)) if a.ndim == 3 else None
    if np.abs(d - d.mean(axis=ax, keepdims=True)).max() < 0.05*np.abs(d).max() + 1e-9:
        return 'const_shift'
    hf = np.abs(np.diff(d, axis=1)).mean()/(np.abs(d).mean() + 1e-12)
    return 'high_freq' if hf > 0.8 else 'unknown'

CAUSE = {'high_freq': '插值核不同（缺少抗锯齿）→ 查 resize 的 interpolation',
         'channel_swap': 'BGR/RGB 弄反 → 查 cvtColor / ISP 输出格式',
         'range_collapse': '归一化顺序错（先 /255 又减了 0-255 量纲的 mean）',
         'border': 'align_corners / padding 值或位置不同',
         'const_shift': 'mean 不同 / uint8→float 时机不同',
         'shape_mismatch': '形状就不同 —— 查 letterbox 的 auto / 目标尺寸',
         'noise': '数值噪声，不是 bug', 'unknown': '未知，需人工看 diff'}

def bisect_first(probe, n):
    lo, hi, calls = 0, n+1, 0
    while hi - lo > 1:
        mid = (lo+hi)//2; calls += 1
        hi, lo = (mid, lo) if probe(mid) else (hi, mid)
    return (None if hi == n+1 else hi), calls

def parity(img, cfg_l, cfg_r, tol_max=0.02, tol_mean=0.005, verbose=True):
    L, Rr = run_pipeline(img, cfg_l), run_pipeline(img, cfg_r)
    rows = []
    for name in STAGES:
        a, b = np.asarray(L[name], float), np.asarray(Rr[name], float)
        if a.shape != b.shape:
            rows.append((name, str(a.shape), np.inf, np.inf, 'FAIL', 'shape_mismatch')); continue
        d = np.abs(a-b); sc = STD.mean() if name in ('to_rgb', 'resize', 'letterbox_pad') else 1.0
        ok = (d.max()/sc <= tol_max) and (d.mean()/sc <= tol_mean)
        rows.append((name, str(a.shape), d.max(), d.mean(),
                     'PASS' if ok else 'FAIL', fingerprint(a, b) if not ok else '-'))
    k, calls = bisect_first(lambda i: rows[i-1][4] == 'FAIL', len(STAGES))
    if verbose:
        print(f"  {'阶段':<14s}{'形状':>18s}{'max|Δ|':>11s}{'mean|Δ|':>11s}{'判定':>7s}  指纹")
        for nm, sh, mx, mn, v, fp in rows:
            print(f'  {nm:<14s}{sh:>18s}{mx:>11.4f}{mn:>11.4f}{v:>7s}  {fp}')
        if k is None:
            print('  ══ 全部阶段一致 ✅')
        else:
            fp = rows[k-1][5]
            print(f'  ══ 首个分歧阶段: **{STAGES[k-1]}**（二分探针 {calls} 次，'
                  f'上界 ⌈log2 {len(STAGES)+1}⌉={math.ceil(math.log2(len(STAGES)+1))}）')
            print(f'  ══ 指纹: {fp} → {CAUSE[fp]}')
    return (STAGES[k-1] if k else None), (rows[k-1][5] if k else None), rows

BASE = dict(resize='area', pad=0, norm='ok')
img0 = TEST[0][0]
for title, cfg in [('注入 bug ①：部署侧用了 INTER_LINEAR', dict(BASE, resize='linear')),
                   ('注入 bug ②：部署侧漏了 BGR→RGB',      dict(BASE, swap_channels=True)),
                   ('注入 bug ③：部署侧先除了 255',         dict(BASE, norm='bad')),
                   ('对照：两侧完全一致',                    dict(BASE))]:
    print(f'\\n【{title}】')
    st, fp, _ = parity(img0, BASE, cfg)

st1, fp1, _ = parity(img0, BASE, dict(BASE, resize='linear'), verbose=False)
st2, fp2, _ = parity(img0, BASE, dict(BASE, swap_channels=True), verbose=False)
st3, fp3, _ = parity(img0, BASE, dict(BASE, norm='bad'), verbose=False)
st4, fp4, _ = parity(img0, BASE, dict(BASE, pad=8), verbose=False)
st0, fp0, _ = parity(img0, BASE, dict(BASE), verbose=False)
assert (st1, fp1) == ('resize', 'high_freq'), (st1, fp1)
assert (st2, fp2) == ('to_rgb', 'channel_swap'), (st2, fp2)
assert (st3, fp3) == ('normalize', 'range_collapse'), (st3, fp3)
assert (st4, fp4) == ('letterbox_pad', 'shape_mismatch'), (st4, fp4)
assert (st0, fp0) == (None, None)
print('\\n✅ 四种注入的 bug 全部被定位到正确的阶段并给出正确的指纹；对照组全绿。')
print('   注意 bug ① 的 diff 在 normalize 之后从 21 灰阶变成 0.37 —— ')
print('   **归一化会把差异同时除以 σ≈58，让巨大的差异「看起来不大」。要在灰阶量纲上看 diff。**')"""),

    md("""## ✏️ 练习 1：INTER_AREA 的权重矩阵

实现 `area_weights(out_size, in_size)`，返回形状 `(out_size, in_size)` 的矩阵：
输出像素 `j` 覆盖源区间 `[j·s, (j+1)·s)`（`s = in_size/out_size`），
权重 = **重叠长度**，每行归一化到和为 1。"""),

    code("""def area_weights(out_size, in_size):
    # TODO: 对每个 j 算区间 [j*s, (j+1)*s) 与每个源像素 [i, i+1) 的重叠长度
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测（可手算）——
# 6 -> 2：s=3，两个输出像素各自平均 3 个源像素
assert np.allclose(area_weights(2, 6), [[1/3, 1/3, 1/3, 0, 0, 0], [0, 0, 0, 1/3, 1/3, 1/3]])
# 3 -> 2：s=1.5，j=0 覆盖 [0,1.5) -> 权重 [1, 0.5, 0]/1.5 = [2/3, 1/3, 0]
assert np.allclose(area_weights(2, 3), [[2/3, 1/3, 0], [0, 1/3, 2/3]])
# 恒等：out == in 时必须是单位阵
assert np.allclose(area_weights(5, 5), np.eye(5))
for o, i in [(3, 7), (16, 40), (7, 96), (2, 11)]:
    W = area_weights(o, i)
    assert W.shape == (o, i)
    assert np.allclose(W.sum(1), 1.0), (o, i)
    assert (W >= 0).all()
    assert np.allclose(W, _area_w(o, i)), (o, i)                 # 与正文实现一致
# 上采样时 AREA 退化成最近邻（每行只有一个非零）
assert (np.count_nonzero(area_weights(6, 3), axis=1) == 1).all()
print('6→2 的权重:\\n', area_weights(2, 6))
print('3→2 的权重:\\n', np.round(area_weights(2, 3), 4))
print('✅ 练习 1 通过：AREA 是唯一「支撑集随缩放比拉伸」的核，也是缩小时唯一正确的选择。')"""),

    md("""## ✏️ 练习 2：letterbox 的逆变换

实现 `unletterbox(boxes_lb, r, left, top, W0, H0)`：
把 letterbox 坐标系下的 `(N,4)` xyxy 框还原回原图坐标，并 clip 到原图范围。
**三个考点**：① 先减 pad 再除 r（不是先除）② 用同一个 r（不是 W0/target 和 H0/target）
③ **clip 放在最后**（clip 的边界是原图的，不是 letterbox 的）。"""),

    code("""def unletterbox(boxes_lb, r, left, top, W0, H0):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
LBP = letterbox(1080, 1920, 640, center=True)      # r=1/3, left=0, top=140
r_, l_, t_ = LBP['r'], LBP['left'], LBP['top']
# ① round-trip：1000 个随机框
rr = np.random.default_rng(2)
gt = np.sort(rr.uniform(0, 1, (1000, 4)), 1) * np.array([1920, 1080, 1920, 1080])
fwd = gt*r_ + np.array([l_, t_, l_, t_])
assert np.abs(unletterbox(fwd, r_, l_, t_, 1920, 1080) - gt).max() < 1e-6
# ② 一个手算的例子：原图 (900,400,980,480)
one = np.array([[900., 400., 980., 480.]])*r_ + np.array([l_, t_, l_, t_])
assert np.allclose(one, [[300., 273.3333, 326.6667, 300.]], atol=1e-3), one
assert np.allclose(unletterbox(one, r_, l_, t_, 1920, 1080), [[900, 400, 980, 480]])
# ③ clip 必须在最后：一个越出上边界的框，正确结果是 y1 被 clip 到 0（而不是负值或被截错）
edge = np.array([[10., 100., 60., 200.]])          # y=100 < top=140 -> 原图上是负的
out = unletterbox(edge, r_, l_, t_, 1920, 1080)
assert out[0, 1] == 0.0 and abs(out[0, 3] - (200-140)/r_) < 1e-6, out
# ④ 常见错误必须被区分开
wrong_nopad = edge/r_
assert abs(wrong_nopad[0, 1] - out[0, 1]) > 100, '忘了减 pad 会差几百像素'
print('还原结果:', np.round(unletterbox(one, r_, l_, t_, 1920, 1080), 2))
print('越界框 clip 后:', np.round(out, 2))
print('✅ 练习 2 通过：把正/逆变换写成一对函数 + round-trip 单测，10 行代码挡住四种经典错误。')"""),

    md("""## ✏️ 练习 3：混叠判据——多细的笔画会被毁掉

实现 `aliasing_report(stroke_px, scale)`，`stroke_px` 是**原图上**的笔画宽度：

- `period_src = 2 * stroke_px`（一条亮线 + 一条暗线 = 一个周期）
- `nyquist_period_src = 2 * scale`（输出端能表示的最细周期，换算到原图坐标）
- `aliased = period_src < nyquist_period_src`
- 折叠后的输出周期：`f = 1/period_src`（cyc/源像素）→ `fs = f*scale`（cyc/输出像素）
  → `folded = min(fs % 1, 1 - fs % 1)` → `folded_period_out = 1/folded`（`folded==0` 时记为 `inf`）

返回 `dict(period_src, nyquist_period_src, aliased, folded_period_out)`。"""),

    code("""def aliasing_report(stroke_px, scale):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
r1 = aliasing_report(2, 3)          # 2px 笔画，3 倍下采样
assert r1['period_src'] == 4 and r1['nyquist_period_src'] == 6
assert r1['aliased'] is True
assert abs(r1['folded_period_out'] - 4.0) < 1e-9, r1
r2_ = aliasing_report(3, 3)         # 3px 笔画：恰好在临界
assert r2_['aliased'] is False and abs(r2_['folded_period_out'] - 2.0) < 1e-9
assert aliasing_report(6, 3)['aliased'] is False
assert aliasing_report(1, 3)['aliased'] is True
assert aliasing_report(4, 2)['aliased'] is False and aliasing_report(1, 2)['aliased'] is True
# 安全下界：笔画宽度必须 >= scale
for sc in [2, 3, 4]:
    assert aliasing_report(sc, sc)['aliased'] is False
    assert aliasing_report(sc-0.5, sc)['aliased'] is True
print(f"{'原图笔画宽':>11s}{'周期':>7s}{'可表示?':>9s}{'折叠后的输出周期':>18s}")
for st in [1, 2, 3, 4, 6, 10]:
    r_rep = aliasing_report(st, 3)
    print(f"{st:>11.1f}{r_rep['period_src']:>7.1f}"
          f"{('❌ 混叠' if r_rep['aliased'] else '✅ 安全'):>10s}"
          f"{r_rep['folded_period_out']:>18.2f}")
print('\\n✅ 练习 3 通过：**1920→640（s=3）时，原图上笔画宽度 < 3px 的一切都是假的。**')
print('   60 米外的限速牌约 20–30 px，「60」的笔画宽度正好 2–3 px —— 正踩在临界上。')
print('   这就是「为什么 TSR 对 resize 尤其敏感」的定量回答（面试可直接用）。')"""),

    md("""## ✏️ 练习 4：对拍定位器

实现 `locate_bug(img, cfg_l, cfg_r, tol_max=0.02, tol_mean=0.005)`，
返回 `(首个分歧阶段名 或 None, 指纹 或 None)`：

1. 两侧各跑一遍 `run_pipeline`
2. 逐阶段比对（形状不同 → 立即 `'shape_mismatch'`）
3. 容差：`to_rgb/resize/letterbox_pad` 三个阶段的 diff 要**除以 σ≈58** 换算到 tensor 单位再比；
   `normalize/hwc2chw` 已经是 tensor 单位，直接比
4. 首个 FAIL 的阶段用 `fingerprint` 给出指纹"""),

    code("""def locate_bug(img, cfg_l, cfg_r, tol_max=0.02, tol_mean=0.005):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
CASES = [(dict(BASE, resize='linear'),      ('resize', 'high_freq')),
         (dict(BASE, swap_channels=True),   ('to_rgb', 'channel_swap')),
         (dict(BASE, norm='bad'),           ('normalize', 'range_collapse')),
         (dict(BASE, pad=8),                ('letterbox_pad', 'shape_mismatch')),
         (dict(BASE),                       (None, None))]
for cfg, want in CASES:
    got = locate_bug(img0, BASE, cfg)
    assert got == want, (cfg, got, want)
    print(f'{str({k: v for k, v in cfg.items() if BASE.get(k) != v}):<32s} -> {got}')
# 换一张图、换一个 bug 组合也必须稳定
assert locate_bug(TEST[7][0], BASE, dict(BASE, resize='linear', swap_channels=True)) == \\
       ('to_rgb', 'channel_swap'), '两个 bug 叠加时，报**最早**的那个'
# 定点舍入这一档不能报警（实现噪声 ≠ 语义错误）
noisy = dict(BASE)
img_noisy = np.clip(img0 + rng.uniform(-0.5, 0.5, img0.shape), 0, 255)
st, fp = locate_bug(img0, BASE, noisy)
assert (st, fp) == (None, None)
print('\\n✅ 练习 4 通过：一个 20 行的函数，把「猜两周」变成「30 秒给出根因」。')
print('   把它接到 CI 上（pytest），预处理不一致这个占 40% 的根因就会绝迹。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def area_weights(out_size, in_size):
    s = in_size / out_size
    W = np.zeros((out_size, in_size))
    for j in range(out_size):
        lo, hi = j*s, (j+1)*s
        for i in range(int(np.floor(lo)), min(int(np.ceil(hi)), in_size)):
            W[j, i] = max(0.0, min(hi, i+1) - max(lo, i))
    return W / W.sum(1, keepdims=True)"""),

    code("""# 练习 2 参考答案
def unletterbox(boxes_lb, r, left, top, W0, H0):
    b = np.asarray(boxes_lb, float).copy()
    b[:, 0::2] = (b[:, 0::2] - left) / r          # ① 先减 pad 再除 r
    b[:, 1::2] = (b[:, 1::2] - top) / r           # ② 两个方向用**同一个** r
    b[:, 0::2] = np.clip(b[:, 0::2], 0, W0)       # ③ clip 放在最后
    b[:, 1::2] = np.clip(b[:, 1::2], 0, H0)
    return b"""),

    code("""# 练习 3 参考答案
def aliasing_report(stroke_px, scale):
    period_src = 2.0 * stroke_px
    nyq = 2.0 * scale
    f = 1.0 / period_src                          # cyc / 源像素
    fs = f * scale                                # cyc / 输出像素
    frac = fs % 1.0
    folded = min(frac, 1.0 - frac)
    return dict(period_src=period_src, nyquist_period_src=nyq,
                aliased=bool(period_src < nyq),
                folded_period_out=(float('inf') if folded == 0 else 1.0/folded))"""),

    code("""# 练习 4 参考答案
def locate_bug(img, cfg_l, cfg_r, tol_max=0.02, tol_mean=0.005):
    L, Rr = run_pipeline(img, cfg_l), run_pipeline(img, cfg_r)
    for name in STAGES:
        a, b = np.asarray(L[name], float), np.asarray(Rr[name], float)
        if a.shape != b.shape:
            return name, 'shape_mismatch'
        sc = STD.mean() if name in ('to_rgb', 'resize', 'letterbox_pad') else 1.0
        d = np.abs(a - b)
        if d.max()/sc > tol_max or d.mean()/sc > tol_mean:
            return name, fingerprint(a, b)
    return None, None"""),

    md("""---
## 🧪 真实工程胶囊：预处理规格 + 对拍脚本 + CI 门禁"""),

    code(r"""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 一、预处理规格（两侧都从它生成，不要各写各的）—— preprocess.yaml
# ══════════════════════════════════════════════════════════════════════
preprocess:
  version: 3                       # **改任何一项都要 +1，并记进模型卡**
  channel_order: RGB               # 输入张量的通道顺序（不是解码器的顺序！）
  source_order: BGR                # cv2.imread 的输出；ISP 直出时改成 RGB 并**删掉 cvtColor**
  resize:
    target: [640, 640]
    interpolation: INTER_AREA      # ← **缩小必须用 AREA**（或 antialias=True）
    coordinate_transformation: half_pixel
  letterbox:
    pad_value: 114
    center: true
    pad_to: stride                 # stride | square
    stride: 32
    scaleup: false                 # 推理端通常不放大小图
  dtype: {cast_before_resize: true, cast_to: float32}
  normalize:
    mean: [123.675, 116.28, 103.53]   # **0-255 量纲**
    std:  [58.395, 57.12, 57.375]
    divide_255_first: false           # ← 与上面两行必须配套，改一个就要改另一个
  layout: NCHW

# ══════════════════════════════════════════════════════════════════════
# 二、各家库的正确写法（照抄）
# ══════════════════════════════════════════════════════════════════════
# OpenCV（缩小）：**必须显式写 INTER_AREA**，默认的 INTER_LINEAR 不抗锯齿
#   img = cv2.imread(p)                            # BGR, uint8
#   img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)     # ← 漏了它 = mAP 掉 10~30
#   img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
#
# PIL：默认就抗锯齿（缩小时），坐标语义 = half_pixel
#   im = Image.open(p).convert('RGB').resize((w, h), Image.BILINEAR)
#
# torch：**默认不抗锯齿**，要显式打开
#   x = F.interpolate(x, size=(h, w), mode='bilinear',
#                     align_corners=False, antialias=True)
#   # torchvision.transforms.v2.Resize(..., antialias=True)  # 新版默认 True
#
# ONNX 导出后必查（TensorRT 的 IResizeLayer 默认是 ASYMMETRIC，和 PyTorch 不同！）
#   $ polygraphy inspect model model.onnx --show layers \
#       | grep -A3 -i resize | grep -i "coordinate_transformation_mode\|mode\|antialias"

# ══════════════════════════════════════════════════════════════════════
# 三、黄金样本集（必须刻意设计覆盖度，一张「正常图」什么都测不出来）
# ══════════════════════════════════════════════════════════════════════
#   golden/01_small_signs.png      含 <16px 的标志      -> 暴露 resize / 混叠
#   golden/02_overexposed.png      大面积过曝           -> 暴露 clip / 溢出
#   golden/03_odd_size_1919x1079   奇数尺寸             -> 暴露取整 / pad 边界
#   golden/04_night_dark.png       极暗帧               -> 暴露 uint8 下溢
#   golden/05_solid_color.png      纯色                 -> 反向验证（此时很多 bug 会互相抵消）
#   golden/06_16x9_edge_boxes.png  贴边的框             -> 暴露逆变换 / clip 顺序
#   golden/07_red_blue_signs.png   红蓝标志各半         -> 暴露 BGR/RGB
#   连同两侧的期望中间张量一起入库（几 MB），随模型一起发布给下游集成方。

# ══════════════════════════════════════════════════════════════════════
# 四、CI 门禁 —— tests/test_preproc_parity.py
# ══════════════════════════════════════════════════════════════════════
#   import numpy as np, pytest, glob
#   TOL = dict(max=0.02, mean=0.005)          # tensor 单位；来源见模块 00 容差表
#   STAGES = ['to_rgb','resize','letterbox','cast_f32','normalize','hwc2chw']
#
#   @pytest.mark.parametrize('img', sorted(glob.glob('golden/*.png')))
#   @pytest.mark.parametrize('stage', STAGES)
#   def test_stage_parity(img, stage):
#       a = np.load(f'dump/train/{stem(img)}_{stage}.npy')
#       b = np.load(f'dump/deploy/{stem(img)}_{stage}.npy')
#       assert a.shape == b.shape, f'SHAPE {a.shape} vs {b.shape}'
#       d = np.abs(a.astype(np.float64) - b.astype(np.float64))
#       assert d.max() <= TOL['max'] and d.mean() <= TOL['mean'], \
#              f'{stage}: max={d.max():.4f} mean={d.mean():.4f}'
#
#   def test_letterbox_roundtrip():            # 10 行，挡住四种经典逆变换错误
#       boxes = rng.uniform(0,1,(1000,4)) * [W0,H0,W0,H0]
#       assert np.abs(unletterbox(letterbox_fwd(boxes)) - boxes).max() < 1e-6
#
#   def test_normalize_sanity():               # 5 行，挡住 3 种归一化错误
#       t = preprocess(golden[0])
#       assert 0.8 <= t.std() <= 1.2 and abs(t.mean()) <= 0.5
#       assert t.min() > -3 and t.max() < 3
#
#   触发时机：改预处理代码 / 换 OpenCV 或 Pillow 版本 / 改 C++ 管线 / 换硬件平台。
#   **一致性不是靠小心，是靠门禁。**

# ══════════════════════════════════════════════════════════════════════
# 五、TSR 专项检查
# ══════════════════════════════════════════════════════════════════════
#  · 1920→640 是 s=3：INTER_LINEAR 在这里**退化成最近邻**，8/9 的像素被丢弃。必须用 AREA。
#  · 评测必须**按像素尺寸分桶**（<16 / 16-32 / 32-64 / >64）。整体 mAP 会掩盖细粒度类崩塌：
#    本 notebook 实测「整体只掉 0.07，两个限速类合计掉 0.32」。
#  · 逐类 AP 必看：BGR 弄反时定位召回几乎不变（0.90），只有类别全错 —— 可视化根本看不出来。
#  · 训练侧如果也用了无抗锯齿 resize：那是**正确性**问题不是一致性问题，
#    要改训练配方并重训，不能只改部署侧（否则反而更不一致）。
'''
print(RECIPE)
for tok in ['INTER_AREA', 'antialias=True', 'ASYMMETRIC', 'divide_255_first',
            'golden/03_odd_size', 'test_letterbox_roundtrip', '分桶', 's=3']:
    assert tok in RECIPE, tok
print('✅ 胶囊覆盖：规格文件 / 三家库正确写法 / 黄金样本覆盖度 / CI 门禁 / TSR 专项')"""),

    md("""### 小结

- **预处理是整条管线里唯一被写了两遍、且没人看它输出的部分**——这就是它占 40% 根因的原因。
  七个岔路口的组合数约 1.2×10⁵，其中与训练侧一致的只有 1 种。
- **resize 有两个独立自由度**：坐标映射（half_pixel / align_corners / **asymmetric ← TensorRT 默认**）
  与插值核（nearest / bilinear / area / 抗锯齿）。前者的 diff 集中在边缘带，后者是高频条纹。
- **整数奇数倍缩放时，half_pixel 下的 bilinear 逐位等于最近邻**：`u(j)=s·j+(s−1)/2`。
  而 **1920→640 与 1080→360 都是 s=3**——车端最常见的那条预处理，
  丢掉了 **88.9%** 的像素，且这是可以逐位验证的事实，不是近似说法。
- **混叠对小目标是灾难**：3 倍下采样后原图上周期 <6px（笔画 <3px）的结构全是假的。
  实测周期 4px 的条纹以 **100% 幅度**穿过无抗锯齿 bilinear（AREA 压到 33，抗锯齿核压到 18）。
  自然图上 **无抗锯齿 vs AREA 平均差 21.4 灰阶 = 0.37 tensor 单位**；
  而两种抗锯齿实现之间只差 8.5 灰阶——**分水岭是「有没有抗锯齿」，不是「哪家库」**。
- **letterbox 有六个自由度**。方形 pad 时 **43.75% 的算力在算灰边**（16:9 输入），
  换成 stride 倍数 pad 省 37.5%。逆变换忘了减 pad → 框整体偏 **420 像素**；
  pad 取整差 1 像素 → 8×8 的框 IoU 从 1.0 掉到 **0.778**（COCO 上看不见，TSR 上吃掉 5–10 mAP）。
- **BGR/RGB 弄反：框全在，类别全错。** 实测定位召回仍有 0.90，而 mAP 归零；
  颜色依赖度越高代价越大——**TSR 里颜色就是语义，所以它在这里是致命 bug 而不是中等 bug。**
- **归一化顺序错让动态范围压缩恰好 255 倍**，输出塌缩到单一类别。
  三条自检（std∈[0.8,1.2]、|mean|≤0.5、range⊂(−3,3)）能挡住多数变体，
  但 **mean/std 顺序反了时四条自检全部通过——只有对拍能抓到**。
- **定位方法**：命名阶段 → 逐阶段 dump → 二分（⌈log₂(n+1)⌉ 次）→ diff 指纹 → 根因。
  **在灰阶量纲上看 diff**，因为归一化会把 21 灰阶变成 0.37，让巨大的差异「看起来不大」。
- **一张图对拍通过 ≠ 一致**：取整分歧只在奇数尺寸暴露、uint8 下溢只在暗像素暴露、
  非等比逆变换只在非正方形输入暴露。**黄金样本的覆盖度必须是刻意设计的。**

下一站：**模块 02 · TensorRT 构建与优化** —— 预处理对齐之后，才轮到讨论 engine。"""),
]
