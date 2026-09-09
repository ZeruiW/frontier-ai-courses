# -*- coding: utf-8 -*-
"""C74 模块 05 · 外观、动态与边界。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 球谐存的是<strong>烘死的出射辐射</strong>，不是材质——所以不能重打光；"
                   "② <strong>阶数与内存：deg 3 时颜色占每个高斯 81% 的存储</strong>；"
                   "③ <strong>SH 能表示多窄的高光——实测半角 $\\approx 125^\\circ/(\\ell{+}1)$，"
                   "deg 3 只到 31°，而抛光塑料要 12°</strong>；"
                   "④ 浮物的三个来源与三种检测法；"
                   "⑤ <strong>4DGS：逐帧独立 300 帧要 70.8 GB，参数化轨迹只要 0.368 GB</strong>；"
                   "⑥ 六种情况下不该用 3DGS"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_appearance_dynamic.ipynb'
                       '（球谐求值与正交性 / '
                       '<strong>二分求出每个阶数能表示的最窄波瓣，'
                       '并与真实材质的高光半角对照</strong> / '
                       '内存账 / <strong>浮物的检测：留出视角的 A 值落差</strong> / '
                       '4DGS 两种参数化的内存对比）'),
    ("核心参考", "Kerbl et al., <em>3D Gaussian Splatting</em>（SIGGRAPH 2023，§附录）· "
                 "Ramamoorthi &amp; Hanrahan, <em>An Efficient Representation for "
                 "Irradiance Environment Maps</em>（SIGGRAPH 2001，SH 的带限分析）· "
                 "Wu et al., <em>4D Gaussian Splatting</em>（CVPR 2024）· "
                 "Yang et al., <em>Deformable 3D Gaussians</em>（CVPR 2024）· "
                 "Jiang et al., <em>GaussianShader</em>（CVPR 2024，把 SH 换成 BRDF）· "
                 "Gao et al., <em>Relightable 3D Gaussian</em>（ECCV 2024）"),
    ("预计时长", "读 50 分钟 + 跑 45 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("sh-what", "球谐存的是什么：烘死的出射辐射", "".join([
        P("每个高斯的颜色不是一个 RGB 三元组，而是一个**方向的函数** "
          "$c(\\mathbf d)$——从方向 $\\mathbf d$ 看这个高斯时它是什么颜色。"
          "球谐是这个函数的一组基："),
        MATH(r"c(\mathbf d) = \sum_{\ell=0}^{L}\sum_{m=-\ell}^{\ell} k_{\ell m}\, Y_{\ell m}(\mathbf d),"
             r"\qquad \text{系数个数} = 3(L+1)^2"),
        DUAL(
            "<strong>关键在于「$c$ 是出射辐射，而不是材质」。</strong>"
            "<em>真实的外观是「入射光照 × BRDF」的积分。"
            "3DGS 不分解这两者——它直接拟合训练视角下看到的<strong>结果</strong></em>。"
            "<strong>所以光照被<em>烘</em>进了 SH 系数里。</strong>"
            "<em>后果：不能换光源、不能改变一天中的时间、"
            "不能把物体搬到另一个场景里</em>。",
            "<strong>这不是「3DGS 还没做到」，而是它<em>选择</em>不做。</strong>"
            "<em>分解光照与材质是逆渲染（inverse rendering），"
            "而逆渲染是欠定的：同一张图可以由「白墙 + 黄光」或「黄墙 + 白光」产生</em>。"
            "<strong>3DGS 放弃这个分解，换来的是「只要拟合得上就行」，"
            "于是优化目标变成一个纯粹的重建问题——这正是它能又快又好的原因之一。</strong>"
            "<em>而 GaussianShader、Relightable 3DGS 这些工作把 SH 换成显式的 BRDF + 法向 + 环境光，"
            "代价是引入了逆渲染的全部歧义，PSNR 通常反而下降</em>。"),
        H3("方向是从哪里量的"),
        P("$\\mathbf d$ 是**从相机中心指向高斯中心**的单位向量（在世界坐标系里）。"
          "这一点值得强调，因为它意味着：**同一帧里不同位置的高斯用的是不同的 $\\mathbf d$**，"
          "而不是一个全局的视线方向。"),
        H3("求值末尾的 $+0.5$ 与 clamp，各有一个后果"),
        P("3DGS 的求值是 <code>color = Σ k·Y + 0.5</code>，然后 clamp 到 $[0,1]$。"),
        TABLE(["这一步", "为什么", "后果"], [
            ["<strong>$+0.5$</strong>",
             "让「系数全为零」对应<strong>中性灰</strong>而不是黑",
             "<em>初始化时把 SH 系数置零得到一个灰场景，优化从那里出发——"
             "而不是从全黑出发（全黑的梯度方向全部一致，收敛更慢）</em>"],
            ["<strong>clamp 到 $[0,1]$</strong>",
             "颜色必须是合法的",
             "<strong>饱和处梯度为零</strong>。"
             "<em>一个被推到过曝的高斯会「卡住」——"
             "它的 SH 系数不再收到任何梯度，从此不再改变</em>。"
             "这表现为<strong>局部的死白斑块，而且加迭代不会改善</strong>"],
        ]),
        DUAL(
            "<strong>第二行是一个真实的失败模式，而它的诊断很简单："
            "看有没有大片恰好等于 1.0 的像素。</strong>"
            "<em>正常的高光会有过渡，饱和卡死的区域是平的</em>。"
            "<strong>缓解手段是在损失里用 HDR 或者对输入图像做色调映射，"
            "让训练目标不去逼近 1.0</strong>——"
            "<em>而这也是为什么 3DGS 在过曝的手机照片上效果常常不好</em>。",
            "<strong>顺带说清一件常被混淆的事：这个 clamp 不是「$\\alpha$ 的 clamp」。</strong>"
            "<em>$\\alpha$ 走 sigmoid（模块 02），永远在 $(0,1)$ 开区间内，"
            "所以它的梯度永远不为零</em>。"
            "<strong>而颜色走的是硬 clamp，会真的把梯度截断。</strong>"
            "<em>两个量、两种处理、两种后果——"
            "而选择的依据是：$\\alpha$ 需要能逼近 0（剪枝要用），"
            "但不能到 1（模块 01 的 $1/(1-\\alpha)$ 病态）；"
            "颜色则两端都要能取到（纯黑与纯白都是合法的颜色）</em>。"),
        CALLOUT("intuition",
                "<strong>一个有用的心智模型：把每个高斯想成一个「会根据你从哪看而改变颜色的小色块」。</strong>"
                "<em>$\\ell{=}0$ 时它只有一个颜色（各方向相同）；"
                "$\\ell{=}1$ 加上一个线性的方向梯度（一边偏亮一边偏暗）；"
                "阶数越高，方向上的花样越细</em>。"
                "<strong>而它<em>不知道</em>光源在哪、也不知道自己的法向是什么</strong>——"
                "<em>这两件事都被吸收进系数里了</em>。"),
    ])),

    # ============================================================== 2
    ("memory", "阶数、内存与那个 81%", "".join([
        P("每个高斯的浮点数：$\\underbrace{3}_{\\mu} + \\underbrace{3}_{s} + "
          "\\underbrace{4}_{q} + \\underbrace{1}_{\\alpha} + \\underbrace{3(\\ell+1)^2}_{\\text{SH}}$"),
        TABLE(["SH 阶 $\\ell$", "SH 系数个数", "每高斯 floats", "100 万高斯 (fp32)",
               "<strong>SH 占比</strong>", "角分辨率 $180^\\circ/(\\ell{+}1)$"], [
            ["0", "3", "14", "0.056 GB", "21%", "180°"],
            ["1", "12", "23", "0.092 GB", "52%", "90°"],
            ["2", "27", "38", "0.152 GB", "71%", "60°"],
            ["<strong>3（官方默认）</strong>", "<strong>48</strong>", "<strong>59</strong>",
             "<strong>0.236 GB</strong>", "<strong>81%</strong>", "45°"],
            ["4", "75", "86", "0.344 GB", "87%", "36°"],
        ]),
        DUAL(
            "<strong>deg 3 时几何（位置 + 缩放 + 四元数 + 不透明度 = 11 个 float）"
            "只占 18.6% 的存储，其余全是颜色。</strong>"
            "<em>这与直觉相反——「3D 高斯溅泼」听起来是个几何方法，"
            "但它的内存瓶颈在<strong>外观</strong></em>。"
            "<strong>deg 3 是 deg 0 的 4.21 倍内存。</strong>",
            "<strong>而这 4.21 倍买到了什么，是下一节要量的。</strong>"
            "<em>先给结论：它买到的是「从 180° 的角分辨率提升到 45°」——"
            "而 45° 这个数字本身还是高估了</em>。"
            "<strong>顺带一个实践中很有效的压缩手段："
            "对绝大多数高斯把 $\\ell$ 降到 0 或 1，只对少数高光区域保留 $\\ell{=}3$。</strong>"
            "<em>因为「视角依赖性强」的高斯在真实场景里是少数——"
            "墙面、地面、织物几乎都是漫反射的</em>。"),
        H3("训练时的渐进式提升"),
        P("官方实现不是一开始就优化全部 48 个系数。它每 1000 步把当前使用的阶数 +1，"
          "从 0 涨到 3。**理由是低阶系数决定整体亮度，高阶只是修饰**——"
          "先定大局再修细节，避免高阶系数在几何还没稳定时就拟合噪声。"),
    ])),

    # ============================================================== 3
    ("specular", "SH 表示不了镜面高光：把边界量出来", "".join([
        P("常见的说法是「SH 阶 $\\ell$ 的角分辨率约 $180^\\circ/(\\ell+1)$」，"
          "所以 deg 3 是 45°。**这个说法高估了它的能力。**"),
        P("notebook 用 Phong 型高光 $\\max(\\cos\\theta,0)^n$ 做投影，"
          "二分求出每个阶数「相对 L2 残差 20%」对应的最窄波瓣："),
        TABLE(["SH 阶", "$180^\\circ/(\\ell{+}1)$ 的说法", "<strong>实测的 20% 残差界（半强度半角）</strong>",
               "实测 / 说法"], [
            ["0", "180°", "60.0°", "0.33"],
            ["1", "90°", "60.0°", "0.67"],
            ["2", "60°", "43.3°", "0.72"],
            ["<strong>3</strong>", "<strong>45°</strong>", "<strong>31.2°</strong>",
             "<strong>0.69</strong>"],
            ["4", "36°", "24.6°", "0.68"],
            ["8", "20°", "13.5°", "0.68"],
        ]),
        MATH(r"\text{实测的最窄半角} \approx \frac{125^\circ}{\ell+1}"),
        P("$125/(\\ell+1)$ 对 $\\ell = 2,3,4,8$ 分别给出 41.7° / 31.2° / 25.0° / 13.9°，"
          "与实测的 43.3° / 31.2° / 24.6° / 13.5° 吻合。"),
        H3("对照真实材质"),
        TABLE(["材质", "Phong $n$", "高光半强度半角", "deg 3 能表示吗"], [
            ["粗糙塑料", "≈5", "29.5°", "<strong>勉强</strong>（残差 0.239）"],
            ["抛光塑料", "≈30", "12.3°", "<strong>不能</strong>"],
            ["漆面 / 清漆", "≈80", "7.5°", "<strong>不能</strong>（残差 0.9 量级）"],
            ["抛光金属", "≈400", "3.4°", "<strong>完全不能</strong>"],
            ["镜面", "→∞", "→0°", "<strong>完全不能</strong>"],
        ]),
        CALLOUT("danger",
                "<strong>所以准确的结论是：SH deg 3 只能勉强表示粗糙塑料级别的高光，"
                "比它更亮的任何材质都表示不了。</strong>"
                "<em>而这是<strong>表示能力</strong>的限制，不是优化没收敛——"
                "再训练一百万步也不会好</em>。"
                "<strong>提高阶数也救不了：要表示抛光塑料（12.3°）需要 "
                "$\\ell \\approx 125/12.3 - 1 \\approx 9$，"
                "而 $\\ell{=}9$ 是 300 个 SH 系数，每高斯 311 个 float——"
                "内存变 5.3 倍。</strong>"),
        DUAL(
            "<strong>一个反直觉的细节：deg 3 的最佳拟合不在 $n{=}1$ 而在 $n{=}2$。</strong>"
            "<em>残差在半角 60°（$n{=}1$）是 0.088，在 45°（$n{=}2$）降到 <strong>0.029</strong>，"
            "在 37.5°（$n{=}3$）又回到 0.088</em>。"
            "<strong>原因很简单：$\\max(\\cos\\theta,0)^2$ 本身就接近一个二次多项式，"
            "而 deg 3 的基里包含所有 $\\le3$ 次的项。</strong>",
            "<strong>而这也说明「角分辨率」这个概念本身是粗糙的。</strong>"
            "<em>SH 不是一个低通滤波器，它是一个多项式基——"
            "有些形状恰好落在基里（拟合极好），有些不落在（拟合很差），"
            "而这与「特征尺度」只是<strong>近似</strong>相关</em>。"
            "<strong>所以我给的 $125/(\\ell+1)$ 也只是一个经验拟合，"
            "它在 20% 残差这个具体判据下成立</strong>——"
            "<em>换成 10% 或 30% 的判据，常数会变</em>。"),
    ])),

    # ============================================================== 4
    ("compress", "压缩：那个 81% 的直接推论", "".join([
        P("第 2 节量出 deg 3 时 SH 占每个高斯 81% 的存储。"
          "**于是压缩 3DGS 就基本等于压缩 SH。**"
          "下面按「改精度」与「改分配」两类分开算，"
          "每高斯的基线是 $59 \\times 4 = 236$ 字节。"),
        H3("① 改精度：量化"),
        TABLE(["方案", "每高斯字节", "相对基线", "100 万高斯", "代价"], [
            ["全 fp32（基线）", "236 B", "1.00×", "0.236 GB", "—"],
            ["SH → fp16", "140 B", "0.59×", "0.140 GB",
             "<em>几乎无损：SH 系数的动态范围小</em>"],
            ["SH → int8 + 每高斯一个 scale", "96 B", "<strong>0.41×</strong>", "0.096 GB",
             "<em>高阶系数的小幅误差，视觉上通常看不出</em>"],
            ["几何 fp16 + SH int8", "74 B", "<strong>0.31×</strong>", "0.074 GB",
             "<strong>位置用 fp16 要小心</strong>：<em>大场景里 fp16 的相对精度约 $10^{-3}$，"
             "100 m 的场景对应 10 cm 的位置误差</em>"],
            ["全 int8 + scale", "67 B", "0.28×", "0.067 GB",
             "<em>位置量化误差已经可见，需要按块（局部坐标）量化才可用</em>"],
        ]),
        H3("② 改分配：按需给阶数"),
        P("关键观察：**「视角依赖性强」的高斯在真实场景里是少数。**"
          "墙面、地面、织物、树叶几乎都是漫反射的，"
          "只有金属、玻璃、湿地面、抛光家具需要高阶 SH。"),
        TABLE(["把多少比例降到 deg 0", "平均每高斯 floats", "每高斯字节", "相对基线", "100 万高斯"], [
            ["50%", "36.5", "146 B", "0.62×", "0.146 GB"],
            ["80%", "23.0", "92 B", "0.39×", "0.092 GB"],
            ["<strong>90%</strong>", "18.5", "74 B", "<strong>0.31×</strong>", "0.074 GB"],
            ["95%", "16.2", "65 B", "0.28×", "0.065 GB"],
        ]),
        DUAL(
            "<strong>两类手段是<em>可乘</em>的：95% 降到 deg 0 + SH int8 + 几何 fp16，"
            "得到每高斯 31.2 字节，是基线的 0.132×——100 万高斯只要 0.031 GB。</strong>"
            "<em>这就是为什么 3DGS 的场景文件能从几百 MB 压到几十 MB"
            "（LightGaussian、Compact3D、Self-Organizing Gaussians 这些工作，"
            "以及 <code>.spz</code> 这类交换格式）</em>。",
            "<strong>而真正的压缩工作还有第三类手段，本课不展开但要点名："
            "<em>减少高斯个数</em>。</strong>"
            "<em>模块 04 第 6 节的角度看，那是最有效的一类——"
            "它同时降低存储、排序成本（模块 03 的 $P$）与渲染成本</em>。"
            "<strong>而量化只降存储。</strong>"
            "<em>所以「压缩 3DGS」的正确顺序是：先剪高斯（Mini-Splatting 那一类）、"
            "再按需分配 SH 阶数、最后量化</em>——"
            "<em>反过来做的话，你会花很大力气去量化本该被删掉的高斯</em>。"),
        CALLOUT("warn",
                "<strong>一个容易踩的坑：位置用 fp16。</strong>"
                "<em>fp16 的相对精度约 $10^{-3}$，所以在一个 100 m 尺度的场景里，"
                "远端的位置误差可达 10 cm——而 3DGS 的高斯尺度常常只有几厘米</em>。"
                "<strong>正确做法是分块量化：把场景切成格子，"
                "每格存一个 fp32 的原点 + 格内的 int16 偏移</strong>——"
                "<em>这样精度随格子大小而不是场景大小</em>。"),
    ])),

    # ============================================================== 5
    ("floaters", "浮物：来源、为什么难修、怎么检测", "".join([
        P("**浮物**（floaters）是悬在空中、不对应任何真实几何的高斯。"
          "它们是 3DGS 最常见的伪影，而它们的成因有三个，只有一个是算法问题。"),
        TABLE(["来源", "机制", "属于谁的问题"], [
            ["<strong>观测不足</strong>",
             "某片空间只被 1–2 个视角看到，于是「它在 3 m 还是 5 m」在训练损失上没有区别",
             "<strong>数据的问题</strong>——加视角是唯一的解"],
            ["<strong>补偿位姿误差</strong>",
             "相机位姿有 0.5° 的误差时，各视角的射线对不齐，"
             "而「在两者之间放一片半透明的雾」比「放一个实心表面」更能同时拟合",
             "<strong>上游的问题</strong>（C72 标定 / C75 的 SfM）"],
            ["<strong>被遮挡的高斯仍收到梯度</strong>",
             "模块 01 第 5 节：如果反向不重放提前终止点，"
             "完全看不见的高斯也在被优化",
             "<strong>实现的问题</strong>——可以修"],
        ]),
        DUAL(
            "<strong>为什么密度控制的判据修不了浮物：浮物的位置梯度很小。</strong>"
            "<em>它们已经「安顿」在一个让训练损失局部最优的位置上，"
            "所以 $\\Vert\\partial L/\\partial\\mu_{2D}\\Vert$ 不大——"
            "而那正是判据看的东西（模块 04 第 2 节）</em>。"
            "<strong>所以必须有第二个机制，也就是不透明度重置</strong>"
            "（<em>模块 04 第 5 节：把所有 $\\alpha$ 压到 0.01，"
            "真正需要的会长回来，浮物不会</em>）。",
            "<strong>而检测浮物有三个办法，从便宜到贵：</strong>"
            "① <strong>从训练集<em>之外</em>的视角渲一张</strong>——"
            "<em>浮物在训练视角看不见（否则损失会惩罚它），换视角就露出来</em>。"
            "<strong>notebook 构造了一个可量的版本：训练视角覆盖 ±15° 的弧，"
            "浮物放在墙前 4 m、颜色与墙相同；"
            "训练视角下的最大图像差是 <em>0.0003</em>（0.08 个 8 bit 色阶，"
            "低于量化噪声），而 25° 的留出视角下是 <em>0.6300</em>——"
            "落差 2100 倍</strong>；"
            "② <strong>看累积不透明度 $A$ 的空间分布</strong>"
            "（<em>模块 01 第 6 节</em>）——"
            "<em>浮物区域的 $A$ 在训练视角高、在留出视角低</em>；"
            "③ <strong>与 LiDAR 或 MVS 深度对比</strong>"
            "（<em>需要额外传感器或 C75 的流程</em>）。"),
        CALLOUT("warn",
                "<strong>一个容易被误判的情形：把浮物当成「过拟合」去加正则。</strong>"
                "<em>如果浮物来自观测不足（第一行），任何正则都只是在"
                "「猜一个先验」而不是在恢复真相——"
                "而不同的正则会猜出不同的、都能拟合训练视角的答案</em>。"
                "<strong>notebook 里那个浮物在 ±15° 的弧内是<em>完全合法</em>的解："
                "训练数据里根本不含否定它的信息。</strong>"
                "<strong>先确认来源，再决定手段：数据问题加视角，"
                "位姿问题回去修位姿，实现问题改内核。</strong>"),
    ])),

    # ============================================================== 5
    ("4dgs", "4DGS：内存账决定了参数化方式", "".join([
        P("把 3DGS 扩到动态场景，最直接的想法是「每帧一套高斯」。"
          "**算一下内存就知道这条路走不通。**"),
        TABLE(["方案", "每高斯 floats", "100 万高斯的显存", "能表示什么"], [
            ["静态 3DGS（1 帧）", "59", "0.236 GB", "—"],
            ["逐帧独立，10 帧", "590", "2.360 GB", "任意变化"],
            ["逐帧独立，50 帧", "2950", "11.80 GB", "任意变化"],
            ["<strong>逐帧独立，300 帧（10 秒 @30fps）</strong>", "17700",
             "<strong>70.8 GB</strong>", "任意变化"],
            ["1 阶多项式轨迹（线性运动）", "70", "0.280 GB",
             "匀速平移 + 匀速旋转"],
            ["2 阶多项式轨迹", "81", "0.324 GB", "加上匀加速"],
            ["<strong>3 阶多项式轨迹</strong>", "<strong>92</strong>",
             "<strong>0.368 GB</strong>", "平滑的形变与运动"],
            ["只让位置随时间变（3 阶）", "68", "0.272 GB",
             "<strong>刚体平移，表示不了旋转或形变</strong>"],
        ]),
        MATH(r"\text{3 阶轨迹} = \underbrace{3\times4}_{\mu(t)} + \underbrace{4\times4}_{q(t)}"
             r" + \underbrace{3\times4}_{s(t)} + \underbrace{1\times4}_{\alpha(t)}"
             r" + \underbrace{48}_{\text{SH 静态}} = 92"),
        DUAL(
            "<strong>3 阶多项式轨迹比逐帧独立省 192 倍</strong>"
            "（<em>70.8 GB → 0.368 GB，300 帧</em>）。"
            "<strong>所以 4DGS 必须用某种参数化的时间模型，这不是设计偏好，是内存的硬约束。</strong>"
            "<em>而具体用什么参数化，各家不同：多项式、4D 高斯（把时间当第四个维度）、"
            "一个小 MLP（Deformable 3DGS）、HexPlane 特征网格（4DGS）</em>。",
            "<strong>注意上表里 SH 保持静态（48 个系数不随时间变），"
            "这是几乎所有 4DGS 工作的共同假设。</strong>"
            "<em>它意味着「物体运动但外观不变」——"
            "所以 4DGS 表示不了「灯被打开」「阴影扫过物体」这类<strong>光照</strong>变化</em>。"
            "<strong>而如果让 SH 也随时间变（3 阶 → 48×4 = 192 个系数），"
            "每高斯就是 236 个 float，0.944 GB——是静态的 4 倍。</strong>"
            "<em>这一步很少有人做，因为收益远小于代价</em>。"),
        CALLOUT("paper",
                "<strong>一个由内存账直接推出的实践建议：动态场景优先减<em>高斯数</em>，而不是减轨迹阶数。</strong>"
                "<em>轨迹从 3 阶降到 1 阶只省 24%（92 → 70 floats），"
                "而高斯数减半省 50%</em>。"
                "<strong>而这也是为什么动态 3DGS 的工作几乎都同时在做「压缩高斯数」</strong>——"
                "<em>它们的 baseline 常常是「静态场景的高斯数 × 时间维度的开销」，"
                "而前者是主项</em>。"),
    ])),

    # ============================================================== 6
    ("when-not", "何时不该用 3DGS", "".join([
        P("本课到这里已经把 3DGS 的机制拆完了。"
          "最后一节反过来：**在什么情况下它是错的工具。**"),
        TABLE(["需求", "3DGS 为什么不行", "该用什么"], [
            ["<strong>要重打光 / 换环境</strong>",
             "第 1 节：光照被烘进 SH，没有材质与法向的分解",
             "<strong>逆渲染类方法</strong>（GaussianShader、Relightable 3DGS）"
             "或传统的 PBR 管线"],
            ["<strong>要精确的表面几何 / 网格</strong>",
             "模块 02 第 6 节：第三个轴永远压不到 0（$+0.3I$ 挡着），"
             "厚度是假的、法向不明确",
             "<strong>2DGS</strong>（面片基元）或 <strong>SDF 类方法</strong>（Neuralangelo 等）；"
             "见 <strong>C75</strong>"],
            ["<strong>要泛化到新场景</strong>（不想每个场景训一次）",
             "3DGS 是<em>拟合</em>方法：每个场景独立优化，参数不可迁移",
             "<strong>前馈重建</strong>（LRM、DUSt3R、Splatter Image 等）；"
             "见 <strong>C75</strong>"],
            ["<strong>视角很少</strong>（&lt; 10 张）",
             "第 4 节：观测不足直接产生浮物，而这不是算法能修的",
             "<strong>生成式先验</strong>（多视角扩散 + SDS）或前馈方法；见 <strong>C75</strong>"],
            ["<strong>透明 / 折射物体</strong>（玻璃、水）",
             "模块 01：α 合成是「吸收 + 自发光」模型，<strong>没有折射</strong>。"
             "光线穿过玻璃会弯，而 3DGS 里光线是直的",
             "<strong>光线追踪</strong>；或把玻璃当成一层视角依赖的贴图（近似）"],
            ["<strong>要在极低端设备上跑</strong>",
             "模块 03：排序 + 200 万个 (高斯,tile) 对，需要 GPU 的基数排序与共享内存",
             "<strong>网格 + 贴图</strong>（用 3DGS 或 2DGS 烘出来），"
             "走标准的移动端渲染管线"],
        ]),
        DUAL(
            "<strong>把这张表反过来读，就得到 3DGS 的适用区间：</strong>"
            "<em>一个静态场景、几十到几百张标定好的照片、"
            "固定光照、不需要重打光、目标是<strong>新视角合成</strong>、"
            "有一块 GPU</em>。"
            "<strong>在这个区间内它目前几乎没有对手</strong>——"
            "<em>而这个区间恰好覆盖了很大一类真实需求"
            "（文物数字化、房产/商品展示、影视预览、机器人场景重放）</em>。",
            "<strong>而最后一行值得单独说：「用 3DGS 训练、导出网格、用传统管线渲染」"
            "是一条被低估的路径。</strong>"
            "<em>它把 3DGS 当成一个<strong>重建工具</strong>而不是<strong>渲染表示</strong>，"
            "于是绕开了排序、内存与移动端支持的全部问题</em>。"
            "<strong>而这条路径的关键一步（从高斯提网格）就是 C75 的内容</strong>——"
            "<em>它需要 2DGS 那种有明确法向的基元，以及模块 01 第 6 节那三种深度口径</em>。"),
        CALLOUT("intuition",
                "<strong>本课的一句话总结：3DGS 的全部工程价值来自一个量级差——"
                "它的基元 $\\alpha$ 大（0.1–0.9）而不是小（0.01–0.05）。</strong>"
                "<em>$\\alpha$ 大 ⟹ 每像素只要十几个基元（模块 01）、"
                "可以提前终止省掉 92%（模块 03）、"
                "但<strong>必须显式排序</strong>（模块 01 第 3 节）"
                "并接受 tile 内共享顺序的近似（模块 03）</em>。"
                "<strong>其余一切——协方差的参数化、仿射投影、密度控制、球谐——"
                "都是为了让这个量级差能被优化出来。</strong>"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 05 · 外观、动态与边界

本 notebook 把讲解页的六个结论跑出来：

1. **3DGS 实际用的实球谐基**（deg 0–3，共 16 个），并验证它们在球面上正交归一；
2. 阶数 → 内存：**deg 3 时 SH 占每个高斯 81% 的存储**；
3. **二分求出每个阶数能表示的最窄高光波瓣** —— 实测 $\\approx 125^\\circ/(\\ell{+}1)$，
   deg 3 只到 **31.2°**，而抛光塑料要 12.3°；
4. 压缩账：两类手段可乘，组合后是基线的 **0.132×**；
5. **浮物检测**：构造一个「训练视角完全看不见、留出视角一眼就看到」的浮物；
6. 4DGS 内存账：**逐帧独立 300 帧 70.8 GB vs 3 阶轨迹 0.368 GB（192×）**。

只用 numpy，CPU，离线。"""),

code("""import numpy as np
print('numpy', np.__version__)

# 3DGS 官方的实球谐系数（utils/sh_utils.py）
C0 = 0.28209479177387814
C1 = 0.4886025119029199
C2 = np.array([1.0925484305920792, -1.0925484305920792, 0.31539156525252005,
               -1.0925484305920792, 0.5462742152960396])
C3 = np.array([-0.5900435899266435, 2.890611442640554, -0.4570457994644658,
               0.3731763325901154, -0.4570457994644658, 1.445305721320277,
               -0.5900435899266435])

def sh_basis(dirs, deg=3):
    '''返回 (N, (deg+1)²) 的实球谐基值。dirs 是 (N,3) 的单位向量。'''
    d = np.asarray(dirs, float)
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    x, y, z = d[:, 0], d[:, 1], d[:, 2]
    out = [np.full(len(d), C0)]
    if deg >= 1:
        out += [-C1*y, C1*z, -C1*x]
    if deg >= 2:
        xx, yy, zz = x*x, y*y, z*z
        out += [C2[0]*x*y, C2[1]*y*z, C2[2]*(2*zz - xx - yy),
                C2[3]*x*z, C2[4]*(xx - yy)]
    if deg >= 3:
        xx, yy, zz = x*x, y*y, z*z
        out += [C3[0]*y*(3*xx - yy), C3[1]*x*y*z, C3[2]*y*(4*zz - xx - yy),
                C3[3]*z*(2*zz - 3*xx - 3*yy), C3[4]*x*(4*zz - xx - yy),
                C3[5]*z*(xx - yy), C3[6]*x*(xx - 3*yy)]
    return np.stack(out, 1)

for deg in [0, 1, 2, 3]:
    print(f'  deg {deg}: {(deg+1)**2:2d} 个基函数（每个颜色通道），'
          f'共 {3*(deg+1)**2:2d} 个系数')
assert sh_basis(np.array([[0, 0, 1.]]), 3).shape == (1, 16)"""),

md("""## 1 · 球谐基的正交归一性

$\\int_{S^2} Y_i Y_j \\,\\mathrm d\\omega = \\delta_{ij}$。
用球面上的均匀采样（Fibonacci 球）做数值积分来验证 —— 这也顺便说明
「为什么低阶系数决定整体亮度」：$Y_{00}$ 是常数。"""),

code("""def fibonacci_sphere(n):
    '''球面上近似均匀的 n 个方向。'''
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2*i/n)
    theta = np.pi * (1 + 5**0.5) * i
    return np.stack([np.cos(theta)*np.sin(phi),
                     np.sin(theta)*np.sin(phi),
                     np.cos(phi)], 1)

D = fibonacci_sphere(200_000)
Y = sh_basis(D, 3)
# 数值积分：(4π/n) Σ Y_i Y_j 应为 δ_ij
G = (4*np.pi/len(D)) * (Y.T @ Y)
off = np.abs(G - np.eye(16))
print(f'Gram 矩阵与单位阵的最大偏差 {off.max():.2e}')
print(f'对角线范围 {np.diag(G).min():.6f} ~ {np.diag(G).max():.6f}')
print(f'非对角线最大绝对值 {np.abs(G - np.diag(np.diag(G))).max():.2e}')
assert off.max() < 5e-3, f'必须近似正交归一，实测偏差 {off.max():.2e}'
print('\\n✓ 16 个基函数在球面上正交归一（数值积分误差 %.1e）' % off.max())

# Y_00 是常数 -> deg 0 的高斯在所有方向上同色
y00 = sh_basis(D, 0)[:, 0]
assert np.allclose(y00, C0), 'Y_00 必须是常数'
print(f'✓ Y_00 ≡ {C0:.10f}（常数）—— 所以 deg 0 的高斯各方向同色')
print(f'  而 3DGS 的求值最后加 0.5：color = Σ k·Y + 0.5，然后 clamp 到 [0,1]')
print(f'  所以「k_00 = 0」对应的颜色是 0.5 灰，而不是黑')

# 一个具体的方向依赖颜色
rng = np.random.default_rng(0)
k = np.zeros((16, 3)); k[0] = [1.0, 0.6, 0.2]/np.array([C0, C0, C0])*0.3
k[2] = [0.8, 0.0, -0.8]        # 沿 z 的线性梯度（Y_10 ∝ z）
def eval_color(k, dirs, deg=3):
    return np.clip(sh_basis(dirs, deg) @ k + 0.5, 0, 1)
print('\\n一个带 deg1 梯度的高斯，从不同方向看：')
for name, d in [('+z', [0,0,1.]), ('-z', [0,0,-1.]), ('+x', [1.,0,0]), ('+y', [0,1.,0])]:
    c = eval_color(k, np.array([d]))[0]
    print(f'  从 {name:2s} 看: RGB {np.round(c, 4)}')
c_pz = eval_color(k, np.array([[0,0,1.]]))[0]
c_nz = eval_color(k, np.array([[0,0,-1.]]))[0]
assert c_pz[0] > c_nz[0] and c_pz[2] < c_nz[2], 'Y_10 ∝ z 应造成沿 z 的颜色梯度'
print('  ✓ 红蓝沿 z 反向变化 —— 这就是「视角依赖颜色」，而它与光源、法向都无关')"""),

md("""## 2 · 阶数、内存与那个 81%"""),

code("""GEO = 3 + 3 + 4 + 1        # mu + scale + quat + alpha

def floats_per_gaussian(deg):
    return GEO + 3*(deg+1)**2

print(' deg  SH系数  每高斯floats  100万高斯   SH占比   180/(deg+1)')
for deg in [0, 1, 2, 3, 4]:
    nsh = 3*(deg+1)**2
    nf = floats_per_gaussian(deg)
    print(f'  {deg}    {nsh:3d}      {nf:3d}       {nf*4*1e6/1e9:.3f} GB   '
          f'{nsh/nf:5.0%}      {180/(deg+1):5.1f}°')

n0, n3 = floats_per_gaussian(0), floats_per_gaussian(3)
assert n0 == 14 and n3 == 59
assert abs(n3*4*1e6/1e9 - 0.236) < 1e-3
assert abs(3*16/n3 - 0.8136) < 1e-3
print(f'\\n✓ deg 3: 59 floats，SH 占 {3*16/n3:.1%}，几何只占 {GEO/n3:.1%}')
print(f'✓ deg 3 是 deg 0 的 {n3/n0:.2f}× 内存')
print('  「3D 高斯溅泼」听起来是个几何方法，但它的内存瓶颈在**外观**')"""),

md("""## 3 · SH 能表示多窄的高光：把边界二分出来

常见说法是「角分辨率 $\\approx 180^\\circ/(\\ell+1)$」。用 Phong 型高光
$\\max(\\cos\\theta,0)^n$ 投影到带限球谐，二分求出「相对 L2 残差 20%」对应的最窄波瓣。"""),

code("""TH = np.linspace(0, np.pi, 4001)
CT = np.cos(TH)
WQ = np.sin(TH)                        # 球面测度（轴对称，只需 sinθ dθ）

def zonal_fit_residual(phong_n, deg):
    '''把 max(cosθ,0)^n 投影到 degree<=deg 的带限（zonal）球谐，返回相对 L2 残差。'''
    tgt = np.maximum(CT, 0.0)**phong_n
    A = np.stack([np.polynomial.legendre.legval(CT, [0]*k + [1])
                  for k in range(deg+1)], 1)
    sw = np.sqrt(WQ)
    coef = np.linalg.lstsq(A*sw[:, None], tgt*sw, rcond=None)[0]
    fit = A @ coef
    return float(np.sqrt(np.sum(WQ*(fit-tgt)**2) / np.sum(WQ*tgt**2)))

def half_angle(phong_n):
    '''Phong 指数 n 对应的半强度半角（度）。'''
    return float(np.degrees(np.arccos(0.5**(1.0/phong_n))))

print('先看 deg 3 的残差随波瓣宽度怎么变：')
print(' 半强度半角   Phong n    deg3 残差   deg8 残差')
for n in [1, 2, 3, 5, 8, 12, 20, 50, 200]:
    print(f'   {half_angle(n):5.1f}°      {n:3d}       '
          f'{zonal_fit_residual(n,3):.3f}      {zonal_fit_residual(n,8):.3f}')

# 一个反直觉的细节：deg3 的最佳拟合在 n=2，不在 n=1
r1, r2, r3 = (zonal_fit_residual(n, 3) for n in [1, 2, 3])
assert r2 < r1 and r2 < r3, f'n=2 应是 deg3 的最佳拟合：{r1:.3f}/{r2:.3f}/{r3:.3f}'
print(f'\\n⚠ deg 3 的最佳拟合在 n=2（残差 {r2:.3f}），而不是最宽的 n=1（{r1:.3f}）')
print('  因为 max(cosθ,0)² 本身就接近一个二次多项式，恰好落在 deg3 的基里。')
print('  推论：「角分辨率」是一个粗糙的概念 —— SH 是多项式基而不是低通滤波器，')
print('        有些形状恰好落在基里（拟合极好），有些不落在（拟合很差）。')"""),

code("""def narrowest_lobe(deg, tol=0.20):
    '''二分求出 degree<=deg 能拟合到 tol 相对残差的最窄波瓣（返回半强度半角，度）。'''
    lo, hi = 1.0, 5000.0                # n 越大波瓣越窄
    if zonal_fit_residual(lo, deg) >= tol:
        return half_angle(lo)           # 连最宽的都拟合不了
    for _ in range(60):
        mid = (lo + hi)/2
        if zonal_fit_residual(mid, deg) < tol:
            lo = mid
        else:
            hi = mid
    return half_angle(lo)

print(' SH 阶   180/(deg+1) 的说法   实测 20% 残差界   实测/说法   125/(deg+1)')
meas = {}
for deg in [0, 1, 2, 3, 4, 8]:
    h = narrowest_lobe(deg); meas[deg] = h
    print(f'   {deg}         {180/(deg+1):6.1f}°           {h:6.1f}°        '
          f'{h/(180/(deg+1)):.2f}       {125/(deg+1):6.1f}°')

# 结论 1：实测值系统性地低于 180/(deg+1)
for deg in [2, 3, 4, 8]:
    assert meas[deg] < 180/(deg+1), f'deg {deg} 的实测界必须低于说法值'
    assert abs(meas[deg] - 125/(deg+1)) < 3.0, \\
        f'deg {deg}: 实测 {meas[deg]:.1f}° 应接近 125/(deg+1)={125/(deg+1):.1f}°'
assert abs(meas[3] - 31.2) < 0.5, f'deg 3 应为 31.2°，实测 {meas[3]:.1f}°'
print(f'\\n✓ 「180/(deg+1)」系统性地**高估**了 SH 的能力（实测只有它的 0.68–0.72 倍）')
print(f'✓ 更好的经验式是 125/(deg+1)：deg 2/3/4/8 分别给 '
      f'{125/3:.1f}/{125/4:.1f}/{125/5:.1f}/{125/9:.1f}°，'
      f'实测 {meas[2]:.1f}/{meas[3]:.1f}/{meas[4]:.1f}/{meas[8]:.1f}°')
print('  （注意这个常数依赖「20% 残差」这个判据；换成 10% 或 30% 常数会变）')"""),

code("""# 对照真实材质
print('材质            Phong n   高光半角    deg3 残差   deg3 能表示吗')
MATS = [('粗糙塑料', 5), ('抛光塑料', 30), ('漆面/清漆', 80), ('抛光金属', 400)]
for name, n in MATS:
    h = half_angle(n); r = zonal_fit_residual(n, 3)
    ok = '勉强' if r < 0.30 else ('不能' if r < 0.9 else '完全不能')
    print(f'  {name:12s}   {n:4d}    {h:5.1f}°      {r:.3f}      {ok}')

assert zonal_fit_residual(5, 3) < 0.30, '粗糙塑料 deg3 勉强可以'
assert zonal_fit_residual(30, 3) > 0.60, '抛光塑料 deg3 必须明显失败'
assert zonal_fit_residual(400, 3) > 0.95, '抛光金属 deg3 必须完全失败'
print(f'\\n✓ SH deg 3 只能勉强表示粗糙塑料级别的高光，更亮的材质都表示不了')
print('  这是**表示能力**的限制，不是优化没收敛 —— 再训练一百万步也不会好')

# 提高阶数救不了：算一下代价
need = 30
deg_need = int(np.ceil(125/half_angle(need) - 1))
print(f'\\n要表示抛光塑料（半角 {half_angle(need):.1f}°）需要 deg ≈ '
      f'125/{half_angle(need):.1f} - 1 = {deg_need}')
nf_need = GEO + 3*(deg_need+1)**2
print(f'  deg {deg_need}: {3*(deg_need+1)**2} 个 SH 系数，每高斯 {nf_need} floats')
print(f'  相对 deg 3 的内存 {nf_need/59:.2f}×  -> 100 万高斯 {nf_need*4*1e6/1e9:.3f} GB')
assert nf_need/59 > 4, '提高阶数的内存代价必须很大'
print(f'  ✓ 内存变 {nf_need/59:.1f} 倍，而这只是为了一种材质 —— 所以正确的做法是换表示')
print('    （GaussianShader / Relightable 3DGS：用显式 BRDF + 法向 + 环境光代替 SH）')"""),

md("""## 4 · 压缩账：两类手段可乘"""),

code("""BASE_BYTES = 59*4

def bytes_per_gaussian(geo_bytes=4, sh_bytes=4, n_sh=48, extra=0):
    return GEO*geo_bytes + n_sh*sh_bytes + extra

print('① 改精度（量化）：')
print('  方案                        每高斯字节  相对基线   100万高斯')
schemes = [('全 fp32（基线）', 4, 4, 0), ('SH -> fp16', 4, 2, 0),
           ('SH -> int8 + 每高斯 scale', 4, 1, 4),
           ('几何 fp16 + SH int8', 2, 1, 4), ('全 int8 + scale', 1, 1, 8)]
for name, gb, sb, ex in schemes:
    v = bytes_per_gaussian(gb, sb, 48, ex)
    print(f'  {name:26s}  {v:5d} B    {v/BASE_BYTES:.2f}×    {v*1e6/1e9:.3f} GB')
assert bytes_per_gaussian(4, 4) == 236
assert bytes_per_gaussian(2, 1, 48, 4) == 74

print('\\n② 改分配（按需给阶数，因为漫反射的高斯占绝大多数）：')
print('  降到 deg0 的比例   平均 floats   每高斯字节   相对基线   100万高斯')
for frac in [0.5, 0.8, 0.9, 0.95]:
    avg = frac*14 + (1-frac)*59
    print(f'      {frac:.0%}            {avg:5.1f}       {avg*4:5.0f} B     '
          f'{avg*4/BASE_BYTES:.2f}×    {avg*4*1e6/1e9:.3f} GB')

print('\\n③ 两类可乘：95% 降 deg0 + SH int8 + 几何 fp16')
avg_sh = 0.95*3 + 0.05*48
combo = GEO*2 + avg_sh*1 + 4
print(f'  平均 SH 系数 {avg_sh:.2f} 个 -> {combo:.1f} B/高斯 = {combo/BASE_BYTES:.3f}×')
print(f'  100 万高斯只要 {combo*1e6/1e9:.3f} GB（基线 0.236 GB）')
assert combo/BASE_BYTES < 0.15, f'组合后应低于基线的 0.15×，实测 {combo/BASE_BYTES:.3f}'
print(f'  ✓ 压到基线的 {combo/BASE_BYTES:.1%} —— 这就是场景文件能从几百 MB 压到几十 MB 的原因')

# fp16 存位置的坑
print('\\n⚠ 位置用 fp16 的坑：fp16 的相对精度约 %.1e' % np.finfo(np.float16).eps)
for extent in [1.0, 10.0, 100.0]:
    err = extent * float(np.finfo(np.float16).eps)
    print(f'  场景尺度 {extent:5.1f} m -> 远端位置误差约 {err*100:.2f} cm')
err100 = 100.0*float(np.finfo(np.float16).eps)
assert err100 > 0.05, 'fp16 在 100 m 场景里的误差必须超过 5 cm'
print(f'  ✓ 100 m 的场景里误差 {err100*100:.1f} cm，而高斯尺度常常只有几厘米')
print('    正确做法：分块量化（每格一个 fp32 原点 + 格内 int16 偏移），')
print('    精度随格子大小而不是场景大小')"""),

md("""## 5 · 浮物：构造一个「训练视角看不见、留出视角一眼看到」的例子

这是浮物最本质的形态。设置：训练视角集中在一个窄弧内（±5°），
留出视角在 40°。浮物放在**一个真实表面点的前面、且颜色与它相同** ——
于是训练视角下它完全无法被区分，换视角就露出来。"""),

code("""# 2D 设置（一个 1D 图像）：相机绕原点转，看向一面 z=8 的墙
WALL_Z = 8.0
FOCAL = 200.0        # 半视场 atan(100/200) = 26.6°
NPIX = 200

def cam_dirs(angle_deg):
    '''相机在角度 angle_deg 处（绕 y 轴），返回 (相机位置, 每个像素的方向)。'''
    a = np.deg2rad(angle_deg)
    pos = np.array([-WALL_Z*np.sin(a), WALL_Z*(1-np.cos(a))])   # 绕墙心的弧上
    look = np.array([np.sin(a), np.cos(a)])                     # 看向墙心
    right = np.array([look[1], -look[0]])
    u = (np.arange(NPIX) - NPIX/2)/FOCAL
    d = look[None, :] + u[:, None]*right[None, :]
    return pos, d/np.linalg.norm(d, axis=1, keepdims=True)

def render_1d(angle_deg, blobs):
    '''blobs: [(中心xy, 半径, 颜色, alpha)]。返回 (颜色, 累积 A)。'''
    pos, dirs = cam_dirs(angle_deg)
    hits = []
    for c, r, col, al in blobs:
        oc = pos - np.asarray(c, float)
        b = dirs @ oc
        cc = oc @ oc - r*r
        disc = b*b - cc
        t = np.where(disc >= 0, -b - np.sqrt(np.maximum(disc, 0)), np.inf)
        t = np.where(t > 1e-6, t, np.inf)
        hits.append((t, col, al))
    order = np.argsort([np.nanmin(np.where(np.isfinite(h[0]), h[0], 1e9)) for h in hits])
    img = np.zeros(NPIX); A = np.zeros(NPIX); T = np.ones(NPIX)
    for i in order:
        t, col, al = hits[i]
        vis = np.isfinite(t)
        a = np.where(vis, al, 0.0)
        img += T*a*col; A += T*a; T *= (1-a)
    return img, A

# 场景：墙面由一串小球拼成（颜色 0.7），外加一个浮物
wall = [((x, WALL_Z), 0.22, 0.7, 0.98) for x in np.arange(-3.0, 3.01, 0.20)]
# 浮物：放在 (0, 4)，即墙前 4 m 的正中，颜色与墙相同
floater = [((0.0, 4.0), 0.30, 0.7, 0.9)]

TRAIN_ANGLES = [-15, -8, -3, 0, 3, 8, 15]
HOLD_ANGLES = [20, 25, 30]

print('训练视角（-15° ~ +15° 的弧内）下，有浮物 vs 无浮物：')
for ang in TRAIN_ANGLES:
    i_no, A_no = render_1d(ang, wall)
    i_yes, A_yes = render_1d(ang, wall + floater)
    print(f'  {ang:+3d}°: 最大像素差 {np.abs(i_yes-i_no).max():.4f}'
          f'   A 最大差 {np.abs(A_yes-A_no).max():.4f}'
          f'   受影响像素(>0.01) {(np.abs(i_yes-i_no) > 0.01).sum()}')

d_train = max(np.abs(render_1d(a, wall+floater)[0] - render_1d(a, wall)[0]).max()
              for a in TRAIN_ANGLES)
print(f'\\n训练视角的最大图像差 {d_train:.4f}（= {d_train*255:.3f} 个 8bit 色阶）')

print('\\n留出视角下：')
for ang in HOLD_ANGLES:
    i_no, A_no = render_1d(ang, wall)
    i_yes, A_yes = render_1d(ang, wall + floater)
    print(f'  {ang:+3d}°: 最大像素差 {np.abs(i_yes-i_no).max():.4f}'
          f'   A 最大差 {np.abs(A_yes-A_no).max():.4f}'
          f'   受影响像素 {(np.abs(i_yes-i_no) > 0.01).sum()}')

d_hold = max(np.abs(render_1d(a, wall+floater)[0] - render_1d(a, wall)[0]).max()
             for a in HOLD_ANGLES)
print(f'\\n留出视角的最大图像差 {d_hold:.4f}，是训练视角的 '
      f'{d_hold/max(d_train,1e-12):.0f}×')
assert d_train < 0.01, f'训练视角下浮物应几乎不可见，实测 {d_train:.4f}'
assert d_hold > 0.30, f'留出视角下浮物应明显可见，实测 {d_hold:.4f}'
assert d_hold/d_train > 500, f'落差应超过 500 倍，实测 {d_hold/d_train:.0f}×'
print(f'\\n✓ 落差 {d_hold/d_train:.0f} 倍。这就是浮物的本质：')
print(f'  它在训练损失上几乎免费（{d_train*255:.3f} 个色阶，远低于量化噪声），')
print(f'  在留出视角上一目了然（{d_hold*255:.0f} 个色阶）。')
print('  所以最便宜的检测法就是「从训练集之外的视角渲一张」。')
print()
print('  而它也说明为什么加正则救不了观测不足：')
print('  浮物在 -15°~+15° 这个弧内是**完全合法**的解 —— 训练数据不含否定它的信息。')
print('  任何正则都只是在猜一个先验，而不同的先验会猜出不同的、都能拟合训练视角的答案。')

i25_no, A25_no = render_1d(25, wall)
i25_yes, A25_yes = render_1d(25, wall + floater)
print('\\n留出视角(25°)的累积不透明度 A 剖面（. <0.2  : <0.5  o <0.9  # 满）：')
for A, tag in [(A25_no, '无浮物'), (A25_yes, '有浮物')]:
    line = ''.join('.' if v < 0.2 else (':' if v < 0.5 else ('o' if v < 0.9 else '#'))
                   for v in A[::2])
    print(f'  {tag}: {line}')
# 浮物出现在「本该是背景」的地方
bg = A25_no < 0.2
assert bg.any(), '25° 视角下应该有一部分像素看到背景'
assert (A25_yes[bg] > 0.5).any(), '浮物应出现在本该是背景的像素上'
n_bad = int((A25_yes[bg] > 0.5).sum())
print(f'  ✓ 在 {int(bg.sum())} 个本该是背景（A<0.2）的像素里，'
      f'有 {n_bad} 个的 A 涨到 >0.5 —— 这是第二种检测法')"""),

md("""## 6 · 4DGS 的内存账"""),

code("""def traj_floats(order, sh_deg=3, sh_static=True):
    '''多项式轨迹参数化下每个高斯的 floats。order=0 表示静态。'''
    nc = order + 1
    nsh = 3*(sh_deg+1)**2
    geo = (3 + 4 + 3 + 1) * nc          # mu, quat, scale, alpha 各 nc 个系数
    return geo + (nsh if sh_static else nsh*nc)

STATIC = floats_per_gaussian(3)
print(f'静态 3DGS: {STATIC} floats -> {STATIC*4*1e6/1e9:.3f} GB / 100 万高斯\\n')
print('A) 逐帧独立：')
for T in [1, 10, 50, 300]:
    tag = '  (10 秒 @30fps)' if T == 300 else ''
    print(f'   {T:3d} 帧: {STATIC*T:6d} floats -> {STATIC*T*4*1e6/1e9:7.3f} GB{tag}')

print('\\nB) 多项式轨迹（SH 静态）：')
for order in [1, 2, 3]:
    n = traj_floats(order)
    print(f'   {order} 阶: {n:3d} floats -> {n*4*1e6/1e9:.3f} GB')

n3 = traj_floats(3)
assert n3 == 92, f'3 阶应为 92 floats，实测 {n3}'
ratio = STATIC*300/n3
assert abs(ratio - 192) < 2, f'压缩比应约 192×，实测 {ratio:.0f}'
print(f'\\n✓ 3 阶轨迹 {n3*4*1e6/1e9:.3f} GB vs 300 帧逐帧独立 '
      f'{STATIC*300*4*1e6/1e9:.1f} GB —— 省 {ratio:.0f}×')
print('  所以 4DGS 必须用参数化的时间模型，这是内存的硬约束而不是设计偏好')

print('\\nC) 让 SH 也随时间变（很少有人做）：')
for order in [1, 3]:
    n = traj_floats(order, sh_static=False)
    print(f'   {order} 阶、SH 动态: {n:3d} floats -> {n*4*1e6/1e9:.3f} GB'
          f'   （是静态的 {n/STATIC:.1f}×）')
assert traj_floats(3, sh_static=False)/STATIC > 3.5
print('  ✓ 代价是静态的 4 倍，而收益（能表示光照随时间变化）通常不值 ——')
print('    所以几乎所有 4DGS 工作都假设「物体运动但外观不变」，')
print('    于是它们表示不了「灯被打开」「阴影扫过物体」')

print('\\nD) 只让位置随时间变（最省，但表示不了旋转与形变）：')
for order in [1, 3]:
    n = 3*(order+1) + 4 + 3 + 1 + 48
    print(f'   {order} 阶: {n} floats -> {n*4*1e6/1e9:.3f} GB')

print('\\n一个由内存账直接推出的建议：动态场景优先减**高斯数**，不是减轨迹阶数。')
print(f'  轨迹 3 阶 -> 1 阶只省 {1-traj_floats(1)/traj_floats(3):.0%}'
      f'（{traj_floats(3)} -> {traj_floats(1)} floats）')
print('  而高斯数减半省 50%')
assert 1 - traj_floats(1)/traj_floats(3) < 0.30, '降阶数的收益应小于减半高斯数'"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 球谐求值

实现 `my_sh_color(k, dirs, deg)`：给定系数 `k`（形状 `((deg+1)², 3)`）与方向 `dirs`（`(N,3)`），
返回 `(N,3)` 的颜色。按 3DGS 的约定：**结果加 0.5 再 clamp 到 [0,1]**。
基函数请用已有的 `sh_basis`。"""),

code("""def my_sh_color(k, dirs, deg=3):
    '''返回 (N,3) 的颜色，已加 0.5 并 clamp 到 [0,1]。'''
    # TODO: Y = sh_basis(dirs, deg)  形状 (N, (deg+1)²)
    #       返回 clip(Y @ k + 0.5, 0, 1)
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_D = fibonacci_sphere(20_000)
_k0 = np.zeros((1, 3))
_k1 = np.zeros((4, 3)); _k1[2] = [0.8, 0.0, -0.8]          # Y_10 ∝ z
_k3 = np.zeros((16, 3)); _k3[0] = [0.5, 0.3, 0.1]; _k3[9] = [0.4, -0.4, 0.0]

# ① 系数全零 -> 处处 0.5 灰
_c = my_sh_color(_k0, _D, 0)
assert _c.shape == (len(_D), 3), f'形状 {_c.shape}'
assert np.allclose(_c, 0.5), '系数全零应给出 0.5 灰（不是黑）'

# ② deg 0 的颜色与方向无关
_kc = np.array([[1.0, 0.5, -0.5]])
_c0 = my_sh_color(_kc, _D, 0)
assert np.abs(_c0 - _c0[0]).max() < 1e-12, 'deg 0 必须各方向同色'
# 并且等于 C0*k + 0.5
assert np.allclose(_c0[0], np.clip(C0*_kc[0] + 0.5, 0, 1)), 'deg0 的闭式核对失败'

# ③ deg 1 的 Y_10 造成沿 z 的梯度
_c1 = my_sh_color(_k1, _D, 1)
_up = _c1[_D[:, 2] > 0.9].mean(0); _dn = _c1[_D[:, 2] < -0.9].mean(0)
assert _up[0] > _dn[0] + 0.1 and _up[2] < _dn[2] - 0.1, 'Y_10 应造成沿 z 的反向梯度'

# ④ 输出必须被 clamp
_kbig = np.zeros((16, 3)); _kbig[0] = [100.0, -100.0, 0.0]
_cb = my_sh_color(_kbig, _D, 3)
assert _cb.min() >= 0.0 and _cb.max() <= 1.0, '必须 clamp 到 [0,1]'
assert np.allclose(_cb[:, 0], 1.0) and np.allclose(_cb[:, 1], 0.0), 'clamp 必须生效'

# ⑤ 与直接用 sh_basis 一致，且方向无需预先归一化
_c3 = my_sh_color(_k3, _D, 3)
assert np.allclose(_c3, np.clip(sh_basis(_D, 3) @ _k3 + 0.5, 0, 1))
_D2 = _D * 3.7                                  # 未归一化
assert np.allclose(my_sh_color(_k3, _D2, 3), _c3, atol=1e-12), '方向应内部归一化'

# ⑥ 均值等于 deg0 项（因为高阶基在球面上积分为 0）
_mean = _c3.mean(0)
_expect = np.clip(C0*_k3[0] + 0.5, 0, 1)
assert np.abs(_mean - _expect).max() < 0.01, \\
    f'球面均值应等于 deg0 项：{np.round(_mean,4)} vs {np.round(_expect,4)}'
print(f'✓ 练习 1 通过：全零 -> 0.5 灰；deg0 各方向同色；Y_10 的梯度；'
      f'clamp 生效；球面均值 {np.round(_mean,4)} = deg0 项 {np.round(_expect,4)}')"""),

md("""### 📖 参考答案 1"""),

code("""def my_sh_color(k, dirs, deg=3):
    Y = sh_basis(dirs, deg)
    return np.clip(Y @ np.asarray(k, float) + 0.5, 0.0, 1.0)

print('参考答案 1 已定义')
print('要点一：那个 +0.5 不是装饰 —— 它意味着「所有系数为 0」对应中性灰而不是黑，')
print('       所以初始化时把 SH 系数置零得到的是一个灰场景，优化从那里出发。')
print('要点二：⑥ 那条（球面均值 = deg0 项）是球谐正交性的直接后果，')
print('       也是「低阶系数决定整体亮度、高阶只是修饰」这句话的精确版本 ——')
print('       这正是官方每 1000 步才把阶数 +1 的理由：先定大局再修细节。')
print('要点三：clamp 让梯度在饱和处为零。一个过曝的高斯会「卡住」不再被优化，')
print('       这是一个真实的失败模式（表现为局部的死白斑块）。')"""),

md("""### ✏️ 练习 2 · 每个阶数能表示的最窄波瓣

实现 `my_narrowest(deg, tol)`：二分求出 degree ≤ `deg` 的带限球谐
能把 $\\max(\\cos\\theta,0)^n$ 拟合到相对 L2 残差 `tol` 以内的**最大** $n$，
返回它对应的半强度半角（度）。

残差与半角请用已有的 `zonal_fit_residual` 与 `half_angle`。"""),

code("""def my_narrowest(deg, tol=0.20):
    '''返回该阶数能表示的最窄波瓣的半强度半角（度）。'''
    # TODO: 在 n ∈ [1, 5000] 上二分。注意 n 越大波瓣越窄、残差越大。
    #       若连 n=1 都拟合不了（残差 >= tol），直接返回 half_angle(1)
    #       二分 60 次后返回 half_angle(lo)
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
_m = {d: my_narrowest(d, 0.20) for d in [0, 1, 2, 3, 4, 8]}
print('  deg  实测最窄半角   125/(deg+1)   180/(deg+1)')
for d, v in _m.items():
    print(f'   {d}      {v:6.1f}°       {125/(d+1):6.1f}°      {180/(d+1):6.1f}°')

# ① 与参考实现一致
for d in [2, 3, 4]:
    assert abs(my_narrowest(d, 0.20) - narrowest_lobe(d, 0.20)) < 1e-6

# ② 阶数越高能表示越窄的波瓣（单调）
_vals = [_m[d] for d in [1, 2, 3, 4, 8]]
assert all(_vals[i] > _vals[i+1] for i in range(len(_vals)-1)), \\
    f'必须单调递减，实测 {[f"{v:.1f}" for v in _vals]}'

# ③ deg 3 应为 31.2°
assert abs(_m[3] - 31.2) < 0.5, f'deg 3 应为 31.2°，实测 {_m[3]:.1f}°'

# ④ 系统性地低于 180/(deg+1)，且接近 125/(deg+1)
for d in [2, 3, 4, 8]:
    assert _m[d] < 180/(d+1), f'deg {d}: 实测界必须低于 180/(deg+1)'
    assert abs(_m[d] - 125/(d+1)) < 3.0, \\
        f'deg {d}: 实测 {_m[d]:.1f}° 应接近 {125/(d+1):.1f}°'
_ratios = [_m[d]/(180/(d+1)) for d in [2, 3, 4, 8]]
assert 0.6 < min(_ratios) and max(_ratios) < 0.8, \\
    f'实测/说法 应稳定在 0.6~0.8，实测 {[f"{r:.2f}" for r in _ratios]}'

# ⑤ 判据放宽时能表示更窄的波瓣
assert my_narrowest(3, 0.40) < my_narrowest(3, 0.20) < my_narrowest(3, 0.05), \\
    'tol 越大，能「表示」的波瓣越窄'
# ⑥ 真实材质的对照：抛光塑料（12.3°）超出 deg 3 的能力
assert _m[3] > half_angle(30), \\
    f'deg3 的界 {_m[3]:.1f}° 必须宽于抛光塑料的 {half_angle(30):.1f}°（即表示不了）'
print(f'\\n✓ 练习 2 通过：deg3 的界 {_m[3]:.1f}°，'
      f'实测/说法 = {np.mean(_ratios):.2f}；'
      f'抛光塑料需 {half_angle(30):.1f}° —— 表示不了')"""),

md("""### 📖 参考答案 2"""),

code("""def my_narrowest(deg, tol=0.20):
    lo, hi = 1.0, 5000.0
    if zonal_fit_residual(lo, deg) >= tol:
        return half_angle(lo)
    for _ in range(60):
        mid = (lo + hi)/2
        if zonal_fit_residual(mid, deg) < tol:
            lo = mid
        else:
            hi = mid
    return half_angle(lo)

print('参考答案 2 已定义')
print('要点一：二分的单调性前提是「n 越大残差越大」。这在整体上成立，')
print('       但**局部不成立** —— deg3 在 n=2 处的残差(0.029)低于 n=1(0.088)。')
print('       所以二分找到的是「上界的一个保守估计」，而不是严格的分界点。')
print('       我把这一点写出来，因为它是这类二分最常见的隐含假设错误。')
print('要点二：结论是 125/(deg+1) 而不是流行的 180/(deg+1) ——')
print('       后者高估了 SH 的能力约 1.45 倍。')
print('要点三：常数 125 依赖「20% 残差」这个判据（自测 ⑤ 验证了这一点）。')
print('       报一个经验常数时必须同时报判据，否则它不可复现。')"""),

md("""### ✏️ 练习 3 · 压缩账

实现 `my_bytes(deg0_frac, geo_bytes, sh_bytes, extra)`：
把 `deg0_frac` 比例的高斯降到 deg 0（3 个 SH 系数）、其余保持 deg 3（48 个），
几何 11 个数每个 `geo_bytes` 字节、SH 每个 `sh_bytes` 字节，
每高斯再加 `extra` 字节（量化的 scale）。返回**平均**每高斯字节数。"""),

code("""def my_bytes(deg0_frac=0.0, geo_bytes=4, sh_bytes=4, extra=0):
    '''平均每高斯字节数。'''
    # TODO: 平均 SH 系数个数 = deg0_frac*3 + (1-deg0_frac)*48
    #       返回 11*geo_bytes + 平均SH系数*sh_bytes + extra
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_BASE = 59*4
# ① 基线
assert abs(my_bytes() - 236) < 1e-9, f'基线应为 236 B，实测 {my_bytes()}'
# ② SH -> fp16
assert abs(my_bytes(sh_bytes=2) - 140) < 1e-9
# ③ 几何 fp16 + SH int8 + 4 字节 scale
assert abs(my_bytes(geo_bytes=2, sh_bytes=1, extra=4) - 74) < 1e-9
# ④ 全部降到 deg0 时，SH 只剩 3 个系数
assert abs(my_bytes(deg0_frac=1.0) - (11*4 + 3*4)) < 1e-9, '全 deg0 应为 56 B'
# ⑤ 单调性
assert my_bytes(0.0) > my_bytes(0.5) > my_bytes(0.9) > my_bytes(1.0)
assert my_bytes(sh_bytes=4) > my_bytes(sh_bytes=2) > my_bytes(sh_bytes=1)
# ⑥ 两类手段可乘：组合应低于任一单独手段
_only_quant = my_bytes(0.0, 2, 1, 4)
_only_alloc = my_bytes(0.95, 4, 4, 0)
_combo = my_bytes(0.95, 2, 1, 4)
assert _combo < _only_quant and _combo < _only_alloc, '组合必须优于任一单独手段'
assert _combo/_BASE < 0.15, f'组合应低于基线的 0.15×，实测 {_combo/_BASE:.3f}'
# ⑦ 与讲解页的具体数字一致
assert abs(my_bytes(0.9) - 74) < 1e-9, '90% 降 deg0 应为 74 B'
assert abs(_combo - 31.25) < 0.1, f'组合应约 31.2 B，实测 {_combo:.2f}'
print(f'✓ 练习 3 通过：基线 {my_bytes():.0f} B；'
      f'只量化 {_only_quant:.0f} B ({_only_quant/_BASE:.2f}×)；'
      f'只改分配 {_only_alloc:.0f} B ({_only_alloc/_BASE:.2f}×)；'
      f'组合 {_combo:.1f} B ({_combo/_BASE:.3f}×)')"""),

md("""### 📖 参考答案 3"""),

code("""def my_bytes(deg0_frac=0.0, geo_bytes=4, sh_bytes=4, extra=0):
    avg_sh = deg0_frac*3 + (1.0 - deg0_frac)*48
    return 11*geo_bytes + avg_sh*sh_bytes + extra

print('参考答案 3 已定义')
print('要点一：⑥ 那条（两类手段可乘）是压缩工作的基本结构 ——')
print('       量化改的是「每个数占几个字节」，按需分配改的是「有多少个数」。')
print('要点二：但**顺序**很重要。正确的顺序是：')
print('       先剪高斯（模块 04：同时降存储、排序与渲染成本）')
print('       -> 再按需分配 SH 阶数 -> 最后量化。')
print('       反过来做，你会花很大力气去量化本该被删掉的高斯。')
print('要点三：这个模型没算上「高斯数」这一维，而那是最有效的一维 ——')
print('       所以别把这个函数当成压缩比的完整预测。')"""),

md("""### ✏️ 练习 4 · 4DGS 的内存账

实现 `my_traj(order, sh_deg, sh_static)`：多项式轨迹参数化下每个高斯的 floats。
几何量（$\\mu$ 3 个、$q$ 4 个、$s$ 3 个、$\\alpha$ 1 个，共 11 个）
各有 `order+1` 个多项式系数；SH 在 `sh_static=True` 时不随时间变。"""),

code("""def my_traj(order, sh_deg=3, sh_static=True):
    '''多项式轨迹参数化下每高斯的 floats。'''
    # TODO: nc = order+1；nsh = 3*(sh_deg+1)²
    #       几何 = 11*nc；SH = nsh（静态）或 nsh*nc（动态）
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
# ① order=0 应退化为静态 3DGS
assert my_traj(0) == 59, f'order=0 应为 59 floats，实测 {my_traj(0)}'
# ② 讲解页的三个数
assert my_traj(1) == 70 and my_traj(2) == 81 and my_traj(3) == 92, \\
    f'1/2/3 阶应为 70/81/92，实测 {my_traj(1)}/{my_traj(2)}/{my_traj(3)}'
# ③ 与参考实现一致
for _o in [0, 1, 2, 3, 5]:
    for _st in [True, False]:
        assert my_traj(_o, 3, _st) == traj_floats(_o, 3, _st)
# ④ 每加一阶固定加 11 个 float（SH 静态时）
_d = [my_traj(o+1) - my_traj(o) for o in range(5)]
assert all(v == 11 for v in _d), f'SH 静态时每阶应固定 +11，实测 {_d}'
# ⑤ SH 动态的代价
_dyn3 = my_traj(3, 3, sh_static=False)
assert _dyn3 == 11*4 + 48*4, f'3 阶 SH 动态应为 {11*4+48*4}，实测 {_dyn3}'
assert _dyn3/59 > 3.5, f'SH 动态应是静态的 3.5 倍以上，实测 {_dyn3/59:.1f}×'
# ⑥ 压缩比：3 阶轨迹 vs 300 帧逐帧独立
_ratio = 59*300/my_traj(3)
assert abs(_ratio - 192) < 2, f'压缩比应约 192×，实测 {_ratio:.0f}'
# ⑦ 降阶数的收益远小于减半高斯数
_gain_order = 1 - my_traj(1)/my_traj(3)
assert _gain_order < 0.30, f'3 阶 -> 1 阶只省 {_gain_order:.0%}，应小于 30%'
assert _gain_order < 0.5, '必须小于「高斯数减半」的 50%'
# ⑧ 低阶 SH 时几何占比上升
assert my_traj(3, 0) == 11*4 + 3, f'sh_deg=0 时 3 阶应为 {11*4+3}'
assert (11*4)/my_traj(3, 0) > (11*4)/my_traj(3, 3), 'SH 阶数低时几何占比更高'
print(f'✓ 练习 4 通过：0/1/2/3 阶 = {my_traj(0)}/{my_traj(1)}/{my_traj(2)}/{my_traj(3)} floats；'
      f'压缩比 {_ratio:.0f}×；降阶数只省 {_gain_order:.0%}（减半高斯数省 50%）')"""),

md("""### 📖 参考答案 4"""),

code("""def my_traj(order, sh_deg=3, sh_static=True):
    nc = order + 1
    nsh = 3*(sh_deg+1)**2
    geo = (3 + 4 + 3 + 1) * nc
    return geo + (nsh if sh_static else nsh*nc)

print('参考答案 4 已定义')
print('要点一：⑦ 是本节最有用的一条 —— 轨迹从 3 阶降到 1 阶只省 24%，')
print('       而高斯数减半省 50%。所以动态场景优先减高斯数。')
print('要点二：⑤ 说明为什么几乎所有 4DGS 工作都让 SH 静态：动态 SH 是 4 倍代价。')
print('       代价换来的能力是「表示光照随时间变化」，而这通常不是需求。')
print('       后果：4DGS 表示不了「灯被打开」「阴影扫过物体」—— 这是一条硬边界。')
print('要点三：这个账也解释了为什么 4DGS 的论文里高斯数常常比静态 3DGS **少** ——')
print('       不是它更高效，而是它必须省着用。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 官方实现：球谐（utils/sh_utils.py + cuda_rasterizer/forward.cu）----
# Python 侧只做「阶数渐进提升」：
class GaussianModel:
    def oneupSHdegree(self):
        if self.active_sh_degree < self.max_sh_degree:
            self.active_sh_degree += 1
# train.py: 每 1000 步调一次 —— 先定大局（低阶）再修细节（高阶）
if iteration % 1000 == 0:
    gaussians.oneupSHdegree()

# CUDA 侧的求值（forward.cu, computeColorFromSH）：
#   glm::vec3 dir = pos - campos;  dir = dir / glm::length(dir);   // 相机 -> 高斯
#   glm::vec3 result = SH_C0 * sh[0];
#   if (deg > 0) { result = result - SH_C1*y*sh[1] + SH_C1*z*sh[2] - SH_C1*x*sh[3]; ... }
#   result += 0.5f;                     // ← 练习 1 的那个 +0.5
#   return glm::max(result, 0.0f);      // clamp -> 饱和处梯度为零

# 两组系数是分开存的（便于只优化 dc 或只优化 rest）：
#   self._features_dc   : (N, 1, 3)      deg 0 的那 3 个
#   self._features_rest : (N, 15, 3)     deg 1-3 的那 45 个
# get_features 把它们 cat 起来 -> (N, 16, 3)

# ---- 压缩：几个能直接用的工具 ----
# 1) SOG / .spz 交换格式（Niantic 的 spz，约 10× 无感压缩）
#    pip install spz  ->  spz.save(gaussians, "scene.spz")
# 2) LightGaussian：SH 蒸馏到低阶 + 剪枝 + 量化
# 3) gsplat 自带的 PNG-based 压缩
from gsplat.compression import PngCompression
PngCompression().compress("out_dir", splats)     # 位置/SH 分别量化后存成 PNG

# ---- 4DGS：两个主流实现 ----
# Deformable 3DGS: 一个小 MLP 把 (xyz, t) 映到 (Δxyz, Δquat, Δscale)
# 4DGS (HexPlane): 用 6 个 2D 特征平面编码 4D 时空，再解码成形变
# 共同点：SH **静态** —— 所以都表示不了光照随时间变化（练习 4 ⑤）

# ---- 想要重打光的话 ----
# GaussianShader / Relightable 3DGS：把 SH 换成
#   (albedo, roughness, metallic, normal) + 一个环境光表示
# 代价：引入逆渲染的全部歧义，PSNR 通常反而下降
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 金属/玻璃看起来像哑光 | `sh_degree`；但**提高阶数救不了** | deg 3 只到半角 31.2°，抛光塑料要 12.3° |
| 局部有死白斑块，训练不动 | SH 求值后的 clamp | 饱和处梯度为零，高斯会「卡住」 |
| 换光照/搬到别的场景就崩 | 这是设计边界，不是 bug | 光照被烘进 SH，没有材质分解 |
| 场景文件几百 MB | 先剪高斯，再降 SH 阶，最后量化 | deg 3 时 SH 占 81% |
| 位置量化后远处物体错位 | 是否用了全局 fp16 | 100 m 场景里 fp16 误差 9.8 cm |
| 换视角就出现半透明色块 | 浮物；从留出视角渲一张确认 | 训练视角差 0.0003，留出视角差 0.6300（2100×） |
| 动态场景 OOM | 减**高斯数**，不是减轨迹阶数 | 3 阶→1 阶只省 24%，减半高斯省 50% |
| 4DGS 表示不了灯被打开 | 这是设计边界 | SH 静态；动态 SH 是 4 倍内存 |"""),
]
