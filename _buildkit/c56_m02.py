# -*- coding: utf-8 -*-
"""C56 模块 02 · 光度增强与域鲁棒性。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00–01（bbox 变换框架、几何增强与标注同步）；C55 模块 03（TSR 失效模式）会让本模块的每个算子都有对应的现实故障"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_photometric_aug.ipynb'),
    ("核心参考", "Koschmieder 能见度关系与大气散射模型；He et al. <em>Dark Channel Prior</em>；Sakaridis et al. <em>Foggy Cityscapes</em>；YOLOv5 <code>hyp.scratch</code> 与 albumentations 的 <code>HueSaturationValue</code>"),
    ("预计时长", "读 65 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("why", "光度增强在管什么：不动一个标注，却可能改掉标签", "".join([
        P("几何增强管的是<strong>「物体在图像里的位置与形状」</strong>，所以每做一次变换都必须同步改标注——模块 01 花了整整一节讲四角法与外接框。光度增强管的是另一件事：<strong>「同一个物体，在不同的光照、天气、传感器、编码条件下，长什么样」</strong>。它一个像素都不移动，框的四个数字原封不动。"),
        P("正因为「不用改标注」，光度增强被广泛当成<em>免费且安全</em>的一类增强，默认配置抄一遍就上。<strong>这恰恰是交通标志识别里最危险的误解</strong>：标注文件没变，不等于标签语义没变。"),
        TABLE(["", "几何增强", "光度增强"], [
            ["改什么", "像素的<strong>位置</strong>", "像素的<strong>数值</strong>"],
            ["标注要不要同步", "<strong>必须</strong>（四角变换 + 外接框）", "完全不用动"],
            ["典型失效", "框膨胀、越界裁剪、小目标被丢弃", "<strong>语义被悄悄改掉</strong>、训练-部署分布错位"],
            ["失效是否可见", "可见（画出来就知道框歪了）", "<strong>基本不可见</strong>（图看起来还挺正常）"],
            ["TSR 特有禁区", "水平翻转（左转变右转、文字镜像）", "<strong>色相抖动（红=禁令、蓝=指示、黄=警告）</strong>"],
            ["调过头的症状", "小目标召回崩、框系统性偏移", "混淆矩阵里出现「跨颜色族」的错分"],
        ]),
        DUAL(
            "光度增强的正当性只有一句话：<strong>你要教模型的是「这些变化不改变它是什么」</strong>。所以判断一个算子该不该用、幅度该多大，只需要问一个问题——<em>真实世界里有什么东西会产生这个变化？变化能有多大？</em>。相机自动曝光会让整幅图明暗浮动 ±1 EV，所以亮度抖动 ±30% 合理；但<em>没有任何物理过程会把一块红牌变成黄牌</em>，所以色相抖动 ±40° 不是增强，是<span class=\"term\">label noise</span>（标签噪声）。",
            "形式化地说：一个变换 <code>T</code> 是 <span class=\"term\">label-preserving</span>（保标签）的，当且仅当对任务的真实条件分布有 <code>p(y | T(x)) = p(y | x)</code>。<strong>光度增强的所有争议都在这一个等式上</strong>。对通用检测（COCO 里的「人/车/椅子」），颜色几乎不进入 <code>p(y|x)</code>，所以色相抖动无害甚至有益；<em>对 TSR，颜色是分类边界本身的一部分</em>，同一个变换直接把等式打破。<strong>这是「增强配方不可跨任务复制」最干净的一个反例</strong>——面试时能举出这个例子，比背十条增强列表更有说服力。",
        ),
        CALLOUT("warn", "一个常见的错误推理是「加了强增强、验证集 mAP 没掉，所以是安全的」。<strong>验证集通常与训练集同分布、同标注体系，掉点会被平均掉</strong>：整体 mAP -0.1 可能对应「稀有黄色警告牌 AP -8」。<em>光度增强的验证必须按颜色族与光照条件分桶看</em>，这一点在模块 05 会展开。"),
    ])),
    ("ops", "成像链路与光度算子谱系：每个算子对应现实里的哪一环", "".join([
        P("与其记一张「常用增强清单」，不如把<strong>成像链路</strong>画出来——每个光度算子都应该能挂到链路上的某一环。挂不上去的算子，就是没有物理对应的算子，用它等于在制造训练-部署鸿沟。"),
        ASCII("""场景辐射 J   →   大气      →   镜头     →   传感器        →   ISP              →   编码/传输
(真实反射率)     散射/吸收       失焦/像差      光电转换/噪声      去马赛克/白平衡      JPEG/H.264
                 雨雪遮挡        运动模糊       读出噪声/量化      降噪/锐化/色调映射    码率自适应
                 眩光散射        暗角           卷帘快门          自动曝光/自动增益     GOP 内质量波动
     │               │              │               │                    │                  │
     ▼               ▼              ▼               ▼                    ▼                  ▼
  （不可增强）   大气散射合成    运动模糊核     高斯/泊松噪声        亮度/对比度/gamma    JPEG 伪影
                 雨雪条纹叠加    失焦模糊核     ISO 噪声模型        饱和度/白平衡漂移    块效应/振铃

规则：**任何一个光度增强算子，都必须能在这条链路上指出它模拟的是哪一环。**
      指不出来（例如 channel shuffle、RGB→BGR 交换、随机反色），就不要用。""")
        ,
        TABLE(["算子", "数学形式", "模拟链路上的哪一环", "TSR 建议幅度", "陷阱"], [
            ["<strong>亮度（乘性）</strong>", "<code>I' = k·I</code>", "自动曝光 / 快门时间变化", "<code>k ∈ [0.7, 1.4]</code>", "<strong>纯缩放，色相与饱和度完全不变</strong>——最安全的算子"],
            ["<strong>亮度（加性）</strong>", "<code>I' = I + b</code>", "杂散光 / 雾的环境光项", "<code>b ∈ [-0.08, 0.12]</code>", "<strong>是一个饱和度衰减器</strong>：色相不变但 S 下降"],
            ["<strong>对比度</strong>", "<code>I' = c·(I-μ) + μ</code>", "ISP 色调映射 / 逆光", "<code>c ∈ [0.7, 1.3]</code>", "本质是仿射 <code>aI+b</code>，同上"],
            ["<strong>gamma</strong>", "<code>I' = I^γ</code>", "编码非线性 / 低光提亮", "<code>γ ∈ [0.7, 1.5]</code>", "<em>非线性</em>：会轻微移动色相（红牌约 1.5°），可接受"],
            ["<strong>饱和度</strong>", "<code>S' = s·S</code>", "白平衡偏差 / 褪色老化 / 雾", "<code>s ∈ [0.6, 1.4]</code>", "褪色标志是真实失效模式，<em>值得刻意训</em>"],
            ["<strong>色相</strong>", "<code>H' = H + Δh</code>", "白平衡漂移（真实幅度很小）", "<strong><code>|Δh| ≤ 12°</code></strong>", "<strong>超过约 25° 就把红牌推进黄牌的色相区间</strong>"],
            ["通道 shuffle / 灰度化", "打乱或合并通道", "<strong>链路上没有对应</strong>", "<strong>禁用</strong>", "对 TSR 等价于随机改标签"],
            ["<strong>噪声</strong>", "泊松（光子）+ 高斯（读出）", "传感器 + 高 ISO", "按曝光比例合成", "<em>先 resize 再加噪 ≠ 先加噪再 resize</em>"],
            ["<strong>模糊</strong>", "线核（运动）/ 盘核（失焦）", "相对运动 / 对焦误差", "长度按物理算", "对小目标是毁灭性的（见模块 04 与 C57）"],
            ["<strong>JPEG 伪影</strong>", "8×8 DCT 量化", "编码 / 回传压缩", "quality ∈ [55, 95]", "<strong>训练数据是解码图、车上是 ISP 直出</strong>"],
        ]),
        DUAL(
            "把上表压成一句可操作的判据：<strong>先问「相机或环境里有什么会产生这个变化」，再问「它最大能有多大」</strong>。第一问筛掉没有物理对应的算子（channel shuffle 之流），第二问定幅度。<em>幅度不该从别人的 config 里抄，而该从设备与场景里推</em>——车载相机的自动曝光范围、白平衡算法的最大偏差、回传码率对应的 JPEG quality，这些都是可以问到具体数字的工程参数。",
            "有一个数学结构值得单独记：<strong>亮度、对比度、以及后面要讲的大气散射雾化，全都是逐通道仿射变换 <code>I' = a·I + b</code></strong>。对这一族变换可以精确说清它对颜色做了什么：<em>通道差被同乘 <code>a</code>，于是 <code>(g-b)/Δ</code> 这类比值完全不变 → <strong>色相严格不变</strong>（前提是 <code>b</code> 三通道相同）；而 <code>S = Δ/max</code> 的分子乘 <code>a</code>、分母是 <code>a·max + b</code>，于是 <code>b &gt; 0</code> 时饱和度必然下降</em>。<strong>所以「雾会不会破坏颜色语义」有一个精确答案：雾主要杀饱和度，色相的偏移完全来自环境光 <code>A</code> 的非中性（天空偏蓝）</strong>——notebook 里会把这两个数都量出来。",
        ),
        CALLOUT("intuition", "记住这个分类比记算子列表有用得多：<strong>仿射类算子（亮度/对比度/雾）安全，非线性类（gamma）轻微移色，显式色相/通道操作危险</strong>。<em>凡是你说不清它对色相做了什么的算子，就不要用在 TSR 上。</em>"),
    ])),
    ("hue", "交通标志的颜色就是语义：色相抖动的红线在哪", "".join([
        P("这一节是本模块的核心，也是 TSR 相比通用检测最特殊的一条约束。<strong>在 GB 5768（中国）、维也纳公约（欧洲）、MUTCD（美国）三套体系里，颜色都不是装饰，而是类别层级的一部分</strong>：红=禁令、黄（欧洲白底红边、中国黄底黑边）=警告、蓝=指示、绿=指路、棕=旅游区。<em>模型看到一块红色圆牌，「这是禁令类」这个判断有一大半来自颜色</em>——这是数据本身的统计事实，不是模型的偏见。"),
        P("于是问题变得可以精确回答：<strong>色相偏移多少度，会让一块红色禁令牌落进另一个类别的颜色区间？</strong>"),
        MATH(r"d_H(h_1,h_2)=\min\bigl(|h_1-h_2|,\;360^\circ-|h_1-h_2|\bigr),\qquad \hat{c}(h)=\arg\min_{c}\;d_H\bigl(h,\;h_c\bigr)"),
        P("把每个类别的代表色算出色相 <code>h_c</code>，用最近色相作为一个「颜色族分类器」。<strong>某一类的安全余量，就是它到相邻类色相的一半</strong>（越过中点就翻类）。取本课用的一组代表色，结果是："),
        TABLE(["颜色族", "代表 RGB", "色相 h<sub>c</sub>", "负向余量", "正向余量", "最先翻成谁"], [
            ["<strong>禁令（红）</strong>", "(0.80, 0.10, 0.12)", "358.3°", "69.1°", "<strong>25.2°</strong>", "<strong>→ 警告（黄）</strong>"],
            ["警告（黄）", "(0.95, 0.78, 0.05)", "48.7°", "25.2°", "48.4°", "← 禁令（红）"],
            ["指路（绿）", "(0.05, 0.45, 0.22)", "145.5°", "48.4°", "37.3°", "→ 指示（蓝）"],
            ["指示（蓝）", "(0.05, 0.25, 0.65)", "220.0°", "37.3°", "69.1°", "← 指路（绿）"],
        ]),
        P("<strong>最小余量是 25.2°，出现在「红↔黄」这一对上</strong>——而这恰恰是 TSR 里后果最严重的一对：把「禁止驶入」认成「注意危险」，或者把「限速」认成「解除限速」，下游动作完全不同。现在把常用库的默认值放进同一把尺子："),
        TABLE(["配置", "实际最大色相偏移", "相对最小余量 25.2°", "判定"], [
            ["<code>YOLOv5/v8 hyp: hsv_h=0.015</code>（乘性）", "约 <strong>±5.4°</strong>", "0.21×", "<strong>✅ 安全</strong>（默认值其实很克制）"],
            ["<code>torchvision ColorJitter(hue=0.1)</code>", "±36°", "1.43×", "<strong>❌ 已越界</strong>"],
            ["<code>albumentations HueSaturationValue(hue_shift_limit=20)</code>", "±40°<sup>*</sup>", "1.59×", "<strong>❌ 严重越界</strong>"],
            ["<code>RandAugment / AutoAugment 的 Color 系算子</code>", "随 magnitude 到 ±60°+", "&gt;2×", "<strong>❌ 不能直接搬到 TSR</strong>"],
            ["<strong>本课建议：0.5 × 最小余量</strong>", "<strong>±12.6°</strong>", "0.50×", "✅ 留一半余量给传感器自身的白平衡偏差"],
        ]),
        P("<sup>*</sup> OpenCV 的 HSV 色相通道是 0–179（用 1 个单位表示 2°），所以 <code>hue_shift_limit=20</code> 等于 <strong>±40°</strong>——<em>这个单位换算是最常被漏掉的一步，很多人以为自己只抖了 20°</em>。"),
        DUAL(
            "为什么 YOLOv5 的默认值反而安全？因为它做的是<strong>乘性</strong>色相变换（<code>H' = H · r</code>，<code>r ∈ [0.985, 1.015]</code>），偏移量正比于色相值本身。<em>而纯红在 OpenCV 里的色相值接近 0 或 179，乘性变换对色相值 0 附近的像素几乎没有影响</em>——<strong>红色恰好是这个实现下最被保护的颜色</strong>。这纯属幸运，不是设计。<em>换成 albumentations 的加性实现，同样的「20」就直接把红推进黄的地盘。</em>",
            "更严谨地讲，判据不该只看色相中心，还要看<strong>类内色相分布的宽度</strong>。真实数据里「红」不是一个点：褪色的红、逆光下的红、夜间路灯下的红，色相能散布 ±15°。<em>所以有效余量 = 半间隔 − 类内散布</em>，25.2° 的一半余量里已经有相当一部分被真实变异吃掉了。<strong>正确做法是：从训练集里实际统计每个颜色族的色相直方图，取分位数算出真实的类间间隔，再据此定抖动上限</strong>——而不是用我们这里的四个代表色。notebook 的练习 1 会把这个流程实现出来。",
        ),
        CALLOUT("danger", "<p><strong>面试高频点，而且是主动提能加分的那一类。</strong>当面试官问「你会怎么给交通标志做数据增强」时，绝大多数候选人会背一遍 flip / scale / mosaic / HSV。<em>能立刻区分出「跑过 baseline」和「想过这个任务」的，是下面这句话</em>：</p><p>「<strong>交通标志有两个别的检测任务没有的增强禁区：一个是水平翻转（左转会变右转、文字会镜像），另一个是色相抖动——因为颜色本身就是类别语义的一部分。我算过，用常见的一组代表色，红色禁令牌只要色相正向偏移约 25 度就会落进黄色警告牌的色相区间，而 albumentations 的默认 <code>hue_shift_limit=20</code> 在 OpenCV 单位下等于 ±40 度，直接越界。所以我会把色相抖动限死在 ±12 度以内，而把幅度让给亮度、对比度和天气合成。</strong>」</p><p>这段话里有<em>禁区、机理、具体数字、具体库的默认值、以及替代方案</em>——五个要素齐全，追问也接得住。</p>", "主动说出来能加分的一段话"),
        CALLOUT("warn", "反过来也要警惕<strong>过度保守</strong>。完全不做色相/饱和度抖动，模型会把「精确的那个红」当成必要条件，遇到褪色牌、夜间色偏、不同厂家的油漆批次就掉点。<em>正确姿势不是「不抖」，而是「小幅抖 + 大幅抖饱和度与亮度」</em>——饱和度和亮度的变化在真实世界里幅度大得多，而它们不跨越类别边界。"),
    ])),
    ("sensor", "传感器与编码链路上的退化：噪声、量化、压缩", "".join([
        P("光度增强里最容易被做成「假的」的一类，就是噪声。<code>img + N(0, σ)</code> 这一行代码在物理上是错的：<strong>真实的图像噪声不是加性高斯，而是「信号相关的泊松（光子散粒噪声）+ 信号无关的高斯（读出噪声）」，再经过数字增益放大</strong>。"),
        MATH(r"\mathrm{SNR}=\frac{N}{\sqrt{N+\sigma_r^2}}\;\xrightarrow[\;N\gg\sigma_r^2\;]{}\;\sqrt{N},\qquad N \propto t_{exp}\cdot L"),
        P("这个式子给出一个可以直接背的结论：<strong>在散粒噪声主导的区间，曝光量降到 1/16，信噪比只降到 1/4</strong>（<code>√16 = 4</code>）。换句话说，<em>夜间画质差不是线性地差，而是按平方根变差</em>——这解释了为什么「稍微暗一点」看起来还行，而「暗到某个点之后」画面突然崩掉：一旦 <code>N</code> 掉到与 <code>σ_r²</code> 同量级，读出噪声接管，SNR 开始线性下降。"),
        TABLE(["退化", "物理来源", "正确的合成方式", "对小目标的相对危害", "常见的错误做法"], [
            ["<strong>散粒噪声</strong>", "光子到达的泊松统计", "<code>Poisson(L·t·Q)</code>，亮处噪声绝对值更大", "中", "全图同 σ 的高斯噪声（暗处噪声被低估）"],
            ["<strong>读出噪声</strong>", "读出电路", "<code>N(0, σ_r)</code>，与信号无关", "<strong>高</strong>（暗处主导）", "忽略它 → 低光合成不真实"],
            ["<strong>数字增益（ISO）</strong>", "ADC 后放大", "信号与噪声<strong>同时</strong>放大", "高", "只放大信号不放大噪声"],
            ["<strong>量化</strong>", "8-bit ADC / 编码", "<code>round(x·255)/255</code>", "低（除非极暗）", "全程 float，忽略量化台阶"],
            ["<strong>JPEG 块效应</strong>", "8×8 DCT 系数量化", "分块 DCT + 量化表 + 反变换", "<strong>极高</strong>", "用高斯模糊冒充压缩伪影"],
            ["<strong>失焦模糊</strong>", "对焦误差 / 景深", "盘状核卷积", "极高", "用高斯核冒充（缺少边缘振铃）"],
        ]),
        DUAL(
            "<strong>JPEG 伪影对 TSR 的危害被严重低估</strong>。JPEG 的量化是在 8×8 的块上做的：<em>一块 24×24 像素的限速牌，整个牌面只占 9 个块</em>——牌上的「60」这两个数字所依赖的高频 DCT 系数，正是被量化表压得最狠的那一批。<strong>结果是：框还在、检测还检得出，但「限速 60 / 限速 80」这一对细粒度分类直接崩掉</strong>。这在两级架构（C55 模块 02）里表现为「检测召回正常、分类准确率异常低」，是一个非常有指纹特征的故障。",
            "更工程化的一点是<strong>训练数据与车端数据的编码链路不同</strong>。训练集通常是「相机 → JPEG 存盘 → 解码 → 训练」，车端是「相机 → ISP → 直接送模型」，中间没有 JPEG。<em>于是模型在训练时见惯了块效应，上车后反而遇到了「太干净」的图</em>——这是一种反向的域差，症状是离线指标好、路测更好或更差都可能，很难归因。<strong>正确做法是让训练与部署的编码链路对齐</strong>：要么训练时也用 ISP 直出的无损帧，要么在部署前把车端帧过一遍同样的编码。这与 C60 模块 01 讲的预处理一致性是同一个方法论。",
        ),
        CALLOUT("warn", "顺序陷阱：<strong><code>resize(noise(img)) ≠ noise(resize(img))</code></strong>。缩小图像会对噪声做平均，把 σ 降低约 <code>1/缩放比</code>；所以「先在原分辨率加噪、再 letterbox 到 640」得到的噪声，比「先 letterbox、再加噪」弱得多。<em>真实链路是先成像（带噪）再缩放，所以正确顺序是「先加噪再 resize」</em>——但绝大多数增强流水线因为性能原因把 resize 放在最前面。<strong>这是一个「为了速度而牺牲物理正确性」的真实取舍，知道它存在比强行修正更重要。</strong>"),
    ])),
    ("weather", "天气与光照合成：用物理模型，不要用滤镜", "".join([
        P("「加个雾」在图像处理里可以是一行 <code>cv2.addWeighted</code>，但那样合成出来的雾<strong>与距离无关</strong>——近处的车和 80 米外的标志被雾化了同样的程度。真实的雾不是这样，它有一个非常干净的物理模型，这也是本节要求手写实现的原因。"),
        H3("大气散射模型（Koschmieder）"),
        MATH(r"I(x)=\underbrace{J(x)\,t(x)}_{\text{直接透射}}+\underbrace{A\,\bigl(1-t(x)\bigr)}_{\text{环境光}},\qquad t(x)=e^{-\beta\, d(x)},\qquad \beta=\frac{-\ln 0.05}{V}\approx\frac{3.0}{V}"),
        P("其中 <code>J</code> 是无雾的真实场景辐射、<code>A</code> 是大气光（通常取天空的颜色）、<code>d(x)</code> 是每个像素的深度、<code>β</code> 是散射系数、<code>V</code> 是<span class=\"term\">meteorological visibility</span>（气象能见度，定义为对比度衰减到 5% 的距离）。<strong>关键点是 <code>t</code> 依赖深度</strong>——所以合成雾必须有一张深度图，哪怕是很粗糙的（地平线以下按行线性递减，就已经比全局叠加真实得多）。"),
        ASCII("""雾对图像的作用，可以精确拆成三件事：

  ① 对比度  ——  I_sign - I_bg = t · ( J_sign - J_bg )     **对比度被严格乘以 t**
  ② 饱和度  ——  S' = t·Δ / (t·max + (1-t)·A)              **A 越亮，S 掉得越狠**
  ③ 色相    ——  若 A 是中性灰，色相 **严格不变**；
                 色相的偏移**全部来自 A 的非中性**（天空偏蓝 → 红牌色相被拉向 350°）

           能见度 V     β=3/V     30 m 处 t     60 m 处 t     保住 20% 对比度的最远距离
           ────────────────────────────────────────────────────────────────────────
             500 m      0.006       0.835         0.698               268 m
             200 m      0.015       0.638         0.407               107 m
             100 m      0.030       0.407         0.165                54 m
              50 m      0.060       0.165         0.027                27 m   ← 只剩 27 m！
              20 m      0.150       0.011         0.0001               11 m""")
        ,
        P("最后一列是这张表里最该记住的数字。<strong>能见度 50 米时，一块交通标志要保住 20% 的原始对比度，最远只能在 27 米处</strong>。以 25 m/s（90 km/h）巡航计算，从检出到经过只剩 <strong>1.1 秒</strong>——留给多帧确认（C55 模块 04）与决策的时间几乎为零。<em>这就是为什么雾天的 TSR 不是「精度掉一点」的问题，而是「系统性地来不及」的问题</em>，对应的工程解法是降速、降级、或依赖高精地图先验，而不是指望模型再强一点。"),
        TABLE(["天气", "物理性质", "合成方法", "为什么不能用滤镜糊弄"], [
            ["<strong>雾/霾</strong>", "均匀介质中的<strong>多次散射</strong>", "<code>I = J·t + A(1-t)</code>，<code>t = e^(-βd)</code>", "必须依赖深度；全局叠加会把近景也糊掉"],
            ["<strong>雨</strong>", "<strong>局部遮挡 + 条纹</strong>，非均匀", "运动模糊过的稀疏条纹层 + 轻度雾化", "雨不是全局衰减；<em>雨滴还会在挡风玻璃上形成折射斑</em>"],
            ["<strong>雪</strong>", "大颗粒近距离遮挡", "多尺度光斑（近大远小）+ 雾化", "雪片会<strong>整块遮住</strong>小标志，是遮挡不是衰减"],
            ["<strong>夜间</strong>", "低光子数 + 点光源", "曝光缩放 + 泊松/读出噪声 + 数字增益", "简单调暗不产生噪声，模型学不到低 SNR"],
            ["<strong>眩光</strong>", "强光源经镜头散射（PSF）", "点光源 + 大半径 PSF 卷积 + 局部饱和截断", "关键是<strong>截断（clipping）</strong>造成的信息永久丢失"],
            ["<strong>隧道出入口</strong>", "自动曝光<strong>来不及跟上</strong>", "先做曝光失配（过曝/欠曝）再截断", "这是 ISP 的动态行为，不是静态光照"],
        ]),
        DUAL(
            "合成天气最常见的坑不是模型写错，而是<strong>只合成了退化，没有合成相机对退化的反应</strong>。真实的雾天，车载相机的自动曝光会拉高增益（画面更亮更噪）、ISP 的对比度增强会试图「去雾」（把已经压缩的动态范围再拉开，放大噪声与量化台阶）、自动白平衡会被灰白的大气光带偏。<em>只叠加一层 <code>I = Jt + A(1-t)</code>，得到的是「一台完全不做自动调节的相机拍的雾」——那台相机不存在</em>。",
            "所以工程上更靠谱的顺序是：<strong>合成退化 → 模拟 ISP 的响应（自动曝光把均值拉回目标亮度、自动增益放大噪声、色调映射压对比度）→ 再量化到 8 bit</strong>。这样合成出来的图，其亮度直方图与真实雾天数据的直方图才对得上。<em>验证方法也很朴素：拿一批真实雾天帧，与合成雾天帧比较亮度直方图、局部对比度分布、噪声功率谱三个统计量</em>——<strong>三个都对得上，合成数据才值得进训练集</strong>。这比「看起来像雾」可靠得多。",
        ),
        CALLOUT("danger", "合成数据进训练集之前必须回答一个问题：<strong>它会不会引入「合成指纹」</strong>。如果所有合成雾图的大气光 <code>A</code> 都是同一个常数、深度图都来自同一个线性假设，模型完全可能学到「见到这种特定的灰白渐变就是雾天场景」这个捷径，而不是学到「在低对比度下也要能找到标志」。<em>症状是：合成雾上指标飞涨，真实雾上纹丝不动</em>。<strong>对策是把 <code>A</code>、<code>β</code>、深度图的形态都随机化，并且始终保留一小份真实恶劣天气数据作为「不可被合成数据污染」的评测集。</strong>"),
    ])),
    ("motion", "运动模糊与卷帘快门：车载相机独有的两种畸变", "".join([
        P("这两个退化在通用检测的增强库里几乎不出现，但在车上它们是天天发生的物理事实。而且它们都能被算清楚——<strong>不需要经验参数，只要相机内参和车速</strong>。"),
        H3("运动模糊：一个与焦距无关的比值"),
        P("设相机焦距 <code>f</code>（像素）、标志物理尺寸 <code>S</code>、距离 <code>Z</code>、横向偏移 <code>X</code>（标志离相机光轴的横向距离，路侧牌典型 2–4 m）、自车速度 <code>v</code>、曝光时间 <code>t_exp</code>。标志在图像上的横坐标 <code>u = fX/Z</code>，对时间求导（<code>dZ/dt = -v</code>）得到像移速度 <code>|du/dt| = fXv/Z²</code>。于是："),
        MATH(r"L_{blur}=\frac{f X v}{Z^{2}}\,t_{exp},\qquad s_{px}=\frac{fS}{Z}\quad\Longrightarrow\quad \boxed{\;\frac{L_{blur}}{s_{px}}=\frac{X\,v\,t_{exp}}{S\,Z}\;}"),
        P("<strong>模糊长度与目标像素尺寸的比值和焦距无关</strong>——换长焦镜头，模糊和目标一起放大，比值不变。<em>这意味着「用长焦看远处标志」这个方案不会让运动模糊问题变好</em>，这是一个很多人第一反应会想错的结论，也是面试里可以直接抛出的一个小推导。"),
        TABLE(["场景", "v", "Z", "t<sub>exp</sub>", "L<sub>blur</sub>/s<sub>px</sub>", "后果"], [
            ["高速白天巡航", "25 m/s", "30 m", "10 ms", "<strong>4.2%</strong>", "可忽略"],
            ["高速白天近距", "25 m/s", "10 m", "10 ms", "<strong>12.5%</strong>", "边缘变软，细粒度分类开始掉"],
            ["夜间城区", "14 m/s", "10 m", "30 ms", "<strong>21.0%</strong>", "牌面数字糊成一团"],
            ["<strong>夜间高速近距</strong>", "25 m/s", "10 m", "30 ms", "<strong>37.5%</strong>", "<strong>牌面高频基本被抹掉</strong>"],
            ["雨夜（曝光更长）", "20 m/s", "8 m", "40 ms", "<strong>50.0%</strong>", "只剩颜色与轮廓可用"],
        ]),
        P("（表中固定 <code>X = 3 m</code>、<code>S = 0.6 m</code>。）这张表把「<strong>为什么 TSR 夜间掉点特别多</strong>」拆成了一条可以完整讲出来的因果链——面试里被问到这个问题，下面这条链比「因为夜间光照差」有力得多："),
        OL([
            "光子少 → 要么<strong>拉长曝光</strong>，要么<strong>拉高增益</strong>，二选一（没有第三条路）；",
            "拉长曝光 → <strong>运动模糊按 <code>t_exp</code> 线性增长</strong>（上表最后两行）；",
            "拉高增益 → <strong>SNR 按 <code>√N</code> 下降</strong>，噪声吃掉牌面的高频细节；",
            "两条路都在削同一样东西：<strong>牌面上区分「限速 60」和「限速 80」的那点高频</strong>；",
            "于是夜间的典型故障不是「检不出」，而是<strong>「检得出但认错」</strong>——混淆矩阵上是同族内的细粒度错分，不是跨族乱窜；",
            "对应的解法也就明确了：<strong>低光合成 + 运动模糊必须成对进增强配方</strong>（只加噪不加模糊，等于只模拟了高增益那条路），评测必须按夜间/白天分桶，且要单独看细粒度分类准确率而不只看 mAP。",
        ]),
        H3("卷帘快门：真正的危害不在畸变，在时间戳"),
        ASCII("""全局快门 (global shutter)              卷帘快门 (rolling shutter)
  所有行同时曝光                        逐行曝光，行间隔 Δt = T_ro / H

  row 0    ├────────┤                    row 0    ├────────┤
  row 1    ├────────┤                    row 1      ├────────┤
  row 2    ├────────┤                    row 2        ├────────┤
   ...     ├────────┤                     ...           ├────────┤
  row H-1  ├────────┤                    row H-1              ├────────┤
           └── 一个时刻 ──┘                        └──── T_ro（整帧读出时间）────┘

  典型 T_ro = 15–33 ms。以 30 m/s 巡航：
    · 帧内首尾行的时间差 = T_ro = 20 ms  →  **自车位移 0.60 m**
    · 自车横摆 ω = 0.5 rad/s 时，整帧横向错切 = f·ω·T_ro = 1000×0.5×0.02 = **10 px**
    · 但一块 24 行高的标志，其内部错切只有 10 × 24/1080 ≈ **0.22 px**（可忽略）

  结论：**对单个小标志，卷帘畸变可以忽略；真正致命的是「同一帧里不同行的时间戳不同」。**""")
        ,
        DUAL(
            "很多人第一次听到卷帘快门，想到的是手机拍螺旋桨那种夸张的弯曲。<strong>在 TSR 里这个直觉是错的</strong>：交通标志在图像上只占几十行，行与行的时间差是零点几毫秒，物体内部的畸变小于 1 个像素，完全淹没在标注误差里。<em>所以「要不要给增强加卷帘畸变」的答案通常是「不需要」</em>——把算力花在运动模糊和低光合成上收益大得多。",
            "但卷帘快门有一个真正会出事的地方：<strong>时序融合与运动补偿必须用「行时间戳」而不是「帧时间戳」</strong>。C55 模块 04 讲的多帧融合依赖「自车运动已知 + 标志静止 → 可以预测下一帧位置」，而这个预测用的是自车位姿在<em>某个时刻</em>的值。如果整帧用一个时间戳，30 m/s 下就引入了最多 0.6 m 的位姿误差；投影到 30 m 外的标志上，横向偏差可达数像素——<strong>对一个 20 px 的目标，这足以让 IoU 关联失败、跟踪断裂</strong>。<em>症状是「跟踪 ID 频繁切换、迟滞状态机反复重置」，而根因在传感器时间模型上，不在跟踪算法里</em>。这是一个非常典型的「在错误的层里 debug」的例子。",
        ),
        CALLOUT("intuition", "把这一节压成两句：<strong>运动模糊要算、要合成、要进配方；卷帘畸变不用合成，但一定要在时间戳上处理对</strong>。<em>判断一个退化该不该做成增强，标准是「它是否改变了模型输入的像素分布」——卷帘畸变对小目标几乎不改变像素，所以它不是增强问题，是系统时间同步问题。</em>"),
    ])),
    ("domain", "域随机化与合成-真实的取舍", "".join([
        P("把上面这些合成手段串起来，就得到了<span class=\"term\">domain randomization</span>（域随机化）的朴素形式：<strong>与其猜测部署域长什么样，不如把训练域撑得足够宽，让部署域落在里面</strong>。这个思路在机器人仿真到实机迁移上非常成功，但直接搬到 TSR 上有明确的边界。"),
        TABLE(["", "真实采集", "物理模型合成（本模块）", "渲染引擎 / 生成模型合成"], [
            ["单位成本", "<strong>高</strong>（采集车 + 标注）", "<strong>近乎为零</strong>", "中（要建场景/训模型）"],
            ["长尾覆盖", "差（罕见天气可能几个月遇不到）", "<strong>好</strong>（参数直接扫）", "好"],
            ["保真度", "<strong>满分</strong>", "中（缺 ISP 动态响应）", "中-高（但有生成指纹）"],
            ["标注成本", "高", "<strong>零</strong>（原标注直接复用）", "零（渲染）/ <strong>高风险</strong>（生成可能改变内容）"],
            ["可控性", "无", "<strong>完全可控</strong>（β、A、t_exp 都是旋钮）", "部分可控"],
            ["主要风险", "分布偏斜（只采到常见场景）", "<strong>合成指纹 → 学到捷径</strong>", "<strong>内容漂移 → 标注失效</strong>"],
        ]),
        DUAL(
            "域随机化的适用边界可以用一句话划清：<strong>它对「有物理模型的变化」有效，对「没有物理模型的变化」无效</strong>。曝光、噪声、雾、模糊都有干净的物理模型，随机化它们能真实地扩大覆盖；<em>而「这个国家的标志底色偏暖」「这批标志的反光膜老化了」「这个路口的广告牌长得像禁令牌」这类变化没有模型可随机化</em>——只能靠采集与挖掘（C58 整门课在讲这件事）。",
            "还有一个反直觉的边界：<strong>随机化过头会伤害精度</strong>。域随机化的代价是让模型学一个更宽的不变性，而模型容量与训练预算是固定的。<em>把训练分布撑到「什么都可能」，模型在真实分布上就会欠拟合</em>——这与模块 03 要讲的「小模型 + 强增强 = 欠拟合」是同一个现象的不同表述。<strong>正确的做法不是「尽量宽」，而是「宽到刚好覆盖部署分布的尾部」</strong>：先用真实数据估计部署分布的参数范围（能见度分布、曝光时间分布、车速分布），再让随机化范围略微超出这个范围，而不是无限撑开。<em>这也让「增强幅度」从一个玄学超参变成了一个可以从数据估出来的量。</em>",
        ),
        CALLOUT("warn", "合成数据混入训练集时，<strong>配比是一个需要单独调的超参</strong>，而且它与「合成数据的保真度」强相关：保真度越低，能容忍的比例越小。<em>一个稳妥的起点是「合成数据占该场景真实数据的 1–3 倍，且总占比不超过训练集的 15%」</em>，然后用模块 05 的分场景消融验证。<strong>绝对不要把合成数据也放进验证集</strong>——那会让指标彻底失去意义。"),
    ])),
    ("recipe", "给 TSR 配一套光度增强：从失效模式反推", "".join([
        P("把前面所有结论收成一张可以直接抄进配置文件的表。<strong>注意每一行的「理由」列都指向一个具体的失效模式</strong>——这是本课程一贯的主张：<em>增强配方应该从失效模式反推，而不是从别人的 config 抄</em>。"),
        TABLE(["算子", "概率 p", "幅度", "反推自哪个失效模式", "验证方式"], [
            ["<strong>亮度（乘性）</strong>", "0.8", "<code>k ∈ [0.7, 1.4]</code>", "隧道出入口、逆光、阴影", "按亮度分位数分桶看 AP"],
            ["<strong>对比度</strong>", "0.5", "<code>c ∈ [0.75, 1.25]</code>", "雾霾、低对比度背景", "按局部对比度分桶"],
            ["<strong>gamma</strong>", "0.4", "<code>γ ∈ [0.75, 1.4]</code>", "不同 ISP 的色调映射曲线", "跨车型/跨相机验证集"],
            ["<strong>饱和度</strong>", "0.6", "<code>s ∈ [0.6, 1.35]</code>", "<strong>褪色标志、雾天去饱和</strong>", "褪色牌专项切片"],
            ["<strong>色相</strong>", "0.3", "<strong><code>Δh ∈ [-12°, +12°]</code></strong>", "白平衡漂移（真实幅度就这么小）", "<strong>跨颜色族混淆矩阵</strong>"],
            ["<strong>低光合成</strong>", "0.25", "曝光比 <code>∈ [1/16, 1/2]</code> + 泊松/读出噪声 + 增益", "<strong>夜间 SNR 塌陷</strong>", "夜间切片 + 细粒度分类准确率"],
            ["<strong>运动模糊</strong>", "0.25", "长度按 <code>Xvt/(SZ)</code> 采样，方向近水平", "<strong>夜间长曝光、近距高速</strong>", "按 <code>L/s</code> 比值分桶"],
            ["<strong>雾化（带深度）</strong>", "0.15", "<code>V ∈ [40, 400] m</code>，<code>A</code> 随机化", "雨雾雪天召回塌陷", "真实恶劣天气集（不含合成）"],
            ["<strong>JPEG 伪影</strong>", "0.2", "<code>quality ∈ [55, 95]</code>", "回传链路压缩、细粒度分类崩", "限速数字对（60/80）专项"],
            ["失焦模糊", "0.1", "半径 <code>∈ [0.5, 2] px</code>", "对焦误差、雨滴附着", "小目标切片"],
            ["<s>通道 shuffle / 灰度化 / 反色</s>", "<strong>0</strong>", "—", "<strong>无物理对应，等价于改标签</strong>", "—"],
        ]),
        P("配这套表时有三条纪律："),
        OL([
            "<strong>概率会相乘</strong>。上表列了 10 个算子，看起来「每张图都被大改」，实际上「同时触发亮度+色相+雾+模糊」的概率是 <code>0.8×0.3×0.15×0.25 ≈ 0.9%</code>。<em>直觉严重高估了实际强度</em>——模块 04 会做这个统计。所以<strong>不要因为「算子多」就把每个概率都调低</strong>，那会让强增强根本不发生。",
            "<strong>顺序要遵循成像链路</strong>：几何 → 雾化（依赖深度，必须在几何之后、否则深度图对不上）→ 曝光/亮度/对比度 → 运动模糊 → 噪声 → 量化 → JPEG。<em>把 JPEG 放在噪声之前，等于假设「先压缩后加噪」，物理上不成立。</em>",
            "<strong>验证集只做确定性变换</strong>（resize + normalize），一个随机算子都不能有。这是铁律，模块 04 会讲为什么它常被无意破坏。",
        ]),
        CALLOUT("intuition", "整套配方的设计原则可以浓缩成一句：<strong>把幅度让给「颜色语义之外」的维度</strong>。亮度、对比度、饱和度、噪声、模糊、天气——这些在真实世界里的变异幅度大得多，而且都不跨越类别边界，<em>放开手抖</em>；<strong>色相是唯一一个必须捏死的旋钮</strong>。<em>这一条能推广到所有「某个视觉属性直接编码类别」的任务</em>——医学影像里的染色颜色、工业质检里的缺陷颜色、遥感里的地物光谱，都是同一个模式。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("光度增强看起来是最「工程」的一块，但它有几个真正未解的问题，而且都直接卡在 TSR 这类安全相关任务上。"),
        UL([
            "<strong>增强策略的自动搜索，在检测上仍未收敛</strong>。AutoAugment / RandAugment / TrivialAugment 在分类上给出了「几乎不用调」的方案，但检测的搜索空间要同时考虑框变换与多目标交互，搜索代价高一个数量级；<em>而且搜出来的策略往往包含对 TSR 有害的色彩算子</em>（搜索目标是整体 mAP，看不见「红→黄」这种颜色族错分）。<strong>「带语义约束的增强搜索」——即把「色相不得跨越类间边界」写成硬约束再搜——目前几乎没有现成工作</strong>。",
            "<strong>合成天气与真实天气的差距仍然可测且显著</strong>。Foggy Cityscapes 这类基于深度的合成集把「有雾数据」从零变成了有，但在真实雾天上的迁移增益远低于同等数量的真实数据。<em>核心缺口是 ISP 的动态响应没有被建模</em>——自动曝光、自动白平衡、去雾算法都会对退化做出反应，而这些反应本身就是域差的一部分。<strong>「把 ISP 放进训练回路」（ISP-in-the-loop，甚至直接在 RAW 域训练）是一条正在被认真探索的路线</strong>，代价是数据管线要重做。",
            "<strong>扩散模型生成恶劣天气数据的标注一致性问题</strong>。用图生图把晴天帧改成雨夜帧，视觉保真度已经很高，但<em>生成过程可能悄悄改变标志的颜色、形状甚至内容</em>——把一块限速 60 改成限速 80，标注却没变。<strong>这类「内容漂移」比合成指纹危险得多，因为它直接制造错误标签</strong>；目前的对策（用检测器/分类器回检生成结果）本身又依赖被训练的模型，存在循环论证。",
            "<strong>「增强幅度应该多大」缺少理论</strong>。现状是网格搜索 + 经验值。有一条有希望的思路是把幅度与<em>部署分布的参数分布</em>直接对齐：从路测数据估出能见度、曝光时间、车速的真实分布，让增强参数按这个分布采样（而不是均匀采样）。<strong>这把「增强调参」变成了「分布估计」，可验证性强得多</strong>，但需要车队回传足够的元数据，属于 C58 数据闭环的范畴。",
            "<strong>测试时适应（test-time adaptation）与增强的关系</strong>。既然域差不可能被增强完全覆盖，另一条路是在部署时用无标签数据在线适应（TENT、BN 统计更新等）。<em>对车端来说这非常诱人（隧道进出、天气突变都是渐变域移）</em>，但在线更新的模型难以验证、难以回滚，<strong>与量产系统「可复现、可追溯」的要求直接冲突</strong>——这是一个技术上有效、工程上暂时用不了的典型例子。",
            "<strong>颜色恒常性（color constancy）能否替代色相增强</strong>。与其教模型对色相不变，不如在预处理里做白平衡校正，把颜色归一化到标准光源下。<em>理论上更优雅，实践中受限于校正算法本身的失败模式</em>（大面积单色物体会让灰世界假设失效——而一块占据画面的蓝色指示牌正是这种情况）。<strong>「校正 vs 增强」的取舍在 TSR 上还没有定论。</strong>",
        ]),
        CALLOUT("paper", "必读：Sakaridis, Dai &amp; Van Gool, <em>Semantic Foggy Scene Understanding with Synthetic Data</em>（IJCV 2018，基于深度的合成雾与它对真实雾的迁移分析，本模块雾化模型的工程参考）；He, Sun &amp; Tang, <em>Single Image Haze Removal Using Dark Channel Prior</em>（CVPR 2009，大气散射模型在视觉里的经典化，反过来也是最好的合成参考）；Cubuk et al., <em>AutoAugment</em>（CVPR 2019）与 <em>RandAugment</em>（NeurIPS 2020）——注意它们的搜索目标里没有语义颜色约束；Zoph et al., <em>Learning Data Augmentation Strategies for Object Detection</em>（ECCV 2020，检测专用增强搜索）；Brooks et al., <em>Unprocessing Images for Learned Raw Denoising</em>（CVPR 2019，把 sRGB 反推回 RAW 再合成噪声，本模块低光噪声模型的正确做法）；Tobin et al., <em>Domain Randomization</em>（IROS 2017，域随机化的原始论述与它的边界）。相邻课程：C55 模块 03（失效模式全景）、C56 模块 04（流水线与顺序）、C56 模块 05（消融验证）、C60 模块 01（预处理一致性）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md(r"""# 02 · 光度增强与域鲁棒性（HSV 语义 / 大气散射 / 运动模糊 / 低光合成 / JPEG）

目标：把「光度增强」从一堆调用库的参数，变成**可以从物理量算出来的东西**。
重点是 TSR 特有的那条红线——**交通标志的颜色就是语义**——并把它量化成一个具体的度数。

本 notebook 你会亲手实现：
1. **RGB↔HSV** 的完整往返变换（纯 numpy），以及一个「颜色族」分类器；
2. **色相偏移多少度会让红色禁令牌落进黄色警告牌的区间**——精确到小数点后一位；
3. 逐通道**仿射算子**的色彩代数：证明亮度/对比度/雾对色相做了什么、对饱和度做了什么；
4. **大气散射雾化模型** `I = J·t + A(1-t)`，`t = exp(-βd)`，含深度图与能见度换算；
5. **运动模糊核**（方向 + 长度）与它那个**与焦距无关**的关键比值；
6. **卷帘快门**的行剪切与「行时间戳」量化；
7. **低光合成**：泊松散粒噪声 + 高斯读出噪声 + 数字增益 + 8-bit 量化，验证 SNR ∝ √N；
8. **JPEG 8×8 DCT 量化**，看压缩伪影如何吃掉限速牌上的数字。

> 心智模型：**光度增强不改一个标注，却可能改掉标签。
> 判断一个算子该不该用，先问「成像链路上哪一环产生它」，再问「它对色相做了什么」。**"""),

    md(r"""## 1 · 合成一个 TSR 场景：颜色语义、深度图与 RGB↔HSV

先把工具备齐。场景是从 1920×1080 帧上裁下的一小块（1:1，不缩放），焦距 `f = 1000 px`，
所以「标志的像素直径 = f·S/Z」这条针孔关系是真的，可以直接代入真实距离。"""),

    code(r"""import numpy as np

rng = np.random.default_rng(7)
np.set_printoptions(precision=4, suppress=True)

# ── 交通标志的「语义颜色」：GB 5768 / 维也纳公约 / MUTCD 共通的颜色族 ──
CLASS_RGB = {
    '禁令(红)': (0.80, 0.10, 0.12),
    '警告(黄)': (0.95, 0.78, 0.05),
    '指路(绿)': (0.05, 0.45, 0.22),
    '指示(蓝)': (0.05, 0.25, 0.65),
}

def rgb_to_hsv(rgb):
    '''RGB[0,1] -> HSV，H∈[0,360)，S,V∈[0,1]。支持任意形状（最后一维为 3）。'''
    a = np.asarray(rgb, dtype=float); shp = a.shape
    x = a.reshape(-1, 3)
    r, g, b = x[:, 0], x[:, 1], x[:, 2]
    mx, mn = x.max(1), x.min(1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-12
    i = m & (mx == r); h[i] = ((g[i] - b[i]) / d[i]) % 6.0
    i = m & (mx == g); h[i] = (b[i] - r[i]) / d[i] + 2.0
    i = m & (mx == b); h[i] = (r[i] - g[i]) / d[i] + 4.0
    h = (h * 60.0) % 360.0
    s = np.where(mx > 1e-12, d / np.where(mx > 1e-12, mx, 1.0), 0.0)
    return np.stack([h, s, mx], 1).reshape(shp)

def hsv_to_rgb(hsv):
    a = np.asarray(hsv, dtype=float); shp = a.shape
    x = a.reshape(-1, 3)
    h = x[:, 0] % 360.0
    s = np.clip(x[:, 1], 0, 1)
    v = np.clip(x[:, 2], 0, 1)
    c = v * s
    hp = h / 60.0
    xx = c * (1.0 - np.abs(hp % 2.0 - 1.0))
    z = np.zeros_like(c)
    opts = np.stack([np.stack([c, xx, z], 1), np.stack([xx, c, z], 1),
                     np.stack([z, c, xx], 1), np.stack([z, xx, c], 1),
                     np.stack([xx, z, c], 1), np.stack([c, z, xx], 1)], 0)   # (6, N, 3)
    idx = np.floor(hp).astype(int) % 6
    out = opts[idx, np.arange(len(idx))]
    return np.clip(out + (v - c)[:, None], 0, 1).reshape(shp)

# 往返一致性（这是后面所有色彩分析的地基）
_probe = rng.random((200, 3))
assert np.allclose(hsv_to_rgb(rgb_to_hsv(_probe)), _probe, atol=1e-12), 'HSV 往返不闭合'

CLASS_HUE = {k: float(rgb_to_hsv(np.array(v))[0]) for k, v in CLASS_RGB.items()}
print('颜色族色相：')
for k, v in CLASS_HUE.items():
    s_, v_ = rgb_to_hsv(np.array(CLASS_RGB[k]))[1:]
    print(f'  {k}   H={v:7.2f}°   S={s_:.3f}  V={v_:.3f}')
assert abs(CLASS_HUE['禁令(红)'] - 358.29) < 0.05
assert abs(CLASS_HUE['指示(蓝)'] - 220.00) < 0.05
print('✅ RGB↔HSV 就位；颜色族色相已标定')"""),

    code(r"""# ── 合成场景：天空 / 路面 / 一块圆形标志 / 杆件 / 深度图 ──
IMG_H, IMG_W = 96, 128          # 从 1920x1080 帧上裁下的一块（1:1，无缩放）
F_PX = 1000.0                   # 相机焦距（像素）—— 真实数量级
Y_HORIZON = 46                  # 地平线所在行

def make_scene(cls='禁令(红)', Z=30.0, S_sign=0.60, seed=0):
    r = np.random.default_rng(seed)
    yy = np.arange(IMG_H)[:, None, None]
    sky  = np.array([0.62, 0.72, 0.88]).reshape(1, 1, 3)
    road = np.array([0.30, 0.29, 0.28]).reshape(1, 1, 3)
    img = np.where(yy > Y_HORIZON, road, sky) * np.ones((IMG_H, IMG_W, 1))
    img = img + r.normal(0, 0.012, img.shape)                    # 轻微纹理

    # 深度图：天空 200 m；路面按行从 120 m 线性递减到 12 m（简化但保留「近下远上」）
    prof = np.interp(np.arange(IMG_H), [Y_HORIZON, IMG_H - 1], [120.0, 12.0])
    depth = np.where(np.arange(IMG_H) > Y_HORIZON, prof, 200.0)[:, None] * np.ones((IMG_H, IMG_W))

    # 标志：针孔关系 d_px = f·S/Z
    d_px = F_PX * S_sign / Z
    R = d_px / 2.0
    cy, cx = 30.0, 64.0
    Y, X = np.mgrid[0:IMG_H, 0:IMG_W]
    rr = np.hypot(Y - cy, X - cx)
    mask = rr <= R
    rim  = mask & (rr > 0.74 * R)
    core = rr <= 0.74 * R
    img[rim] = CLASS_RGB[cls]
    img[core] = (0.93, 0.93, 0.92)
    bar = core & (np.abs(Y - cy) <= max(1.0, 0.16 * R))          # 牌面上的深色图案
    img[bar] = (0.12, 0.12, 0.13)
    depth[mask] = Z
    pole = (np.abs(X - cx) <= 1) & (Y > cy + R) & (Y < Y_HORIZON + 6)
    img[pole] = (0.45, 0.45, 0.46)
    depth[pole] = Z

    img = np.clip(img, 0, 1)
    ys, xs = np.where(mask)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    return dict(img=img, depth=depth, mask=mask, rim=rim, bbox=bbox, Z=Z,
                cls=cls, d_px=d_px, y_h=Y_HORIZON)

def sign_hue(scene, img=None):
    '''量圈边（承载颜色语义的那一环）的平均色相/饱和度/明度。'''
    im = scene['img'] if img is None else img
    return rgb_to_hsv(im[scene['rim']].mean(0))

sc = make_scene('禁令(红)', Z=30.0)
h0, s0, v0 = sign_hue(sc)
print(f"场景：{sc['cls']}  Z={sc['Z']:.0f} m  →  标志直径 {sc['d_px']:.1f} px  bbox={sc['bbox']}")
print(f"圈边颜色：H={h0:.2f}°  S={s0:.3f}  V={v0:.3f}")
print(f"深度图范围：{sc['depth'].min():.1f} – {sc['depth'].max():.1f} m（标志处 {sc['Z']:.0f} m）")
assert abs(sc['d_px'] - 20.0) < 1e-9, 'f·S/Z = 1000×0.6/30 = 20 px'
assert abs(h0 - CLASS_HUE['禁令(红)']) < 1.0, '圈边应保持红色族色相'
assert sc['bbox'][3] <= sc['y_h'], '路侧标志的框应完全在地平线以上'
print('✅ 场景就位：20 px 的标志 = 1000 px 焦距下 30 m 外的 0.6 m 圆牌')"""),

    md(r"""## 2 · 光度算子的色彩代数：仿射安全、加性掉饱和、gamma 微移色相

常见光度算子几乎全是**逐通道仿射** `I' = a·I + b`。对这一族可以精确说清它做了什么：

- 通道差被同乘 `a` → `(g-b)/Δ` 这类比值不变 → **色相严格不变**（前提 b 三通道相同）；
- `S = Δ/max = a·Δ_J / (a·max_J + b)` → **`b > 0` 时饱和度必然下降**。

而 `gamma` 是非线性的，它会轻微移动色相。下面把这些都量出来。"""),

    code(r"""def op_brightness_mul(img, k):   return np.clip(img * k, 0.0, 1.0)
def op_brightness_add(img, b):   return np.clip(img + b, 0.0, 1.0)
def op_contrast(img, c):
    mu = float(img.mean())
    return np.clip((img - mu) * c + mu, 0.0, 1.0)
def op_gamma(img, g):            return np.clip(img, 0.0, 1.0) ** g
def op_hsv_jitter(img, dh=0.0, ds=1.0, dv=1.0):
    hsv = rgb_to_hsv(img)
    hsv[..., 0] = (hsv[..., 0] + dh) % 360.0
    hsv[..., 1] = np.clip(hsv[..., 1] * ds, 0.0, 1.0)
    hsv[..., 2] = np.clip(hsv[..., 2] * dv, 0.0, 1.0)
    return hsv_to_rgb(hsv)

# 恒等性检查：HSV 抖动的零参数必须是恒等变换
assert np.allclose(op_hsv_jitter(sc['img'], 0.0, 1.0, 1.0), sc['img'], atol=1e-12)

def hue_shift(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)

base = np.array(CLASS_RGB['禁令(红)'])
rows = []
for name, fn in [('乘性亮度 ×1.25', lambda x: op_brightness_mul(x, 1.25)),
                 ('乘性亮度 ×0.70', lambda x: op_brightness_mul(x, 0.70)),
                 ('加性亮度 +0.20', lambda x: op_brightness_add(x, 0.20)),
                 ('对比度 ×0.60',   lambda x: np.clip((x - 0.45) * 0.6 + 0.45, 0, 1)),
                 ('gamma 0.50',     lambda x: op_gamma(x, 0.50)),
                 ('gamma 2.20',     lambda x: op_gamma(x, 2.20)),
                 ('饱和度 ×0.50',   lambda x: op_hsv_jitter(x, 0.0, 0.5, 1.0)),
                 ('色相 +30°',      lambda x: op_hsv_jitter(x, 30.0, 1.0, 1.0))]:
    out = fn(base)
    h, s, v = rgb_to_hsv(out)
    rows.append((name, hue_shift(h, CLASS_HUE['禁令(红)']), s / 0.875, v))

print(f"{'算子':<16s} {'|Δ色相|':>9s} {'饱和度比':>10s} {'明度':>8s}   判定")
for name, dh, sr, v in rows:
    verdict = '✅ 色相不变' if dh < 0.01 else ('⚠️ 轻微移色' if dh < 5 else '❌ 破坏颜色语义')
    print(f'{name:<16s} {dh:>9.3f}° {sr:>10.3f} {v:>8.3f}   {verdict}')

# 仿射类算子：色相严格不变
for fn in [lambda x: op_brightness_mul(x, 1.25), lambda x: op_brightness_add(x, 0.20),
           lambda x: np.clip((x - 0.45) * 0.6 + 0.45, 0, 1)]:
    assert hue_shift(rgb_to_hsv(fn(base))[0], CLASS_HUE['禁令(红)']) < 1e-9
# 加性亮度 = 饱和度衰减器
assert rgb_to_hsv(op_brightness_add(base, 0.20))[1] < 0.875 - 0.15
# 乘性亮度 = 纯 V 缩放，饱和度也不变
assert abs(rgb_to_hsv(op_brightness_mul(base, 0.70))[1] - 0.875) < 1e-12
# gamma：非线性，色相有微小偏移但远小于安全余量
assert 0.1 < hue_shift(rgb_to_hsv(op_gamma(base, 2.2))[0], CLASS_HUE['禁令(红)']) < 3.0
print()
print('✅ 结论一：乘性亮度是最安全的算子（色相与饱和度都严格不变）')
print('✅ 结论二：加性亮度/对比度/雾都是仿射 → 色相不变，但**饱和度必然下降**')
print('✅ 结论三：gamma 会移色相，但红牌只移约 1.4°，远在 25° 的红线以内')
print('❌ 结论四：显式色相抖动是唯一一个能直接跨越类别边界的算子')"""),

    md(r"""## 3 · 招牌实验：色相偏移多少度，红色禁令牌会变成黄色警告牌

用「最近色相」作为颜色族分类器，扫描色相偏移，找出**翻类的临界角**。"""),

    code(r"""def hue_dist(a, b):
    d = np.abs((np.asarray(a, dtype=float) - b) % 360.0)
    return np.minimum(d, 360.0 - d)

def classify_by_hue(h, class_hue=CLASS_HUE):
    names = list(class_hue)
    d = np.array([hue_dist(h, class_hue[n]) for n in names])
    return names[int(np.argmin(d))]

def flip_angle(cls, sign, class_hue=CLASS_HUE, step=0.1, limit=180.0):
    '''沿 sign(±1) 方向偏移色相，返回第一个翻类的角度（度）。'''
    h0 = class_hue[cls]
    for d in np.arange(step, limit + step / 2, step):
        if classify_by_hue((h0 + sign * d) % 360.0, class_hue) != cls:
            return float(d), classify_by_hue((h0 + sign * d) % 360.0, class_hue)
    return float('inf'), None

print(f"{'颜色族':<12s} {'h_c':>8s} {'负向余量':>10s} {'翻成':<12s} {'正向余量':>10s} {'翻成'}")
margins = {}
for cls in CLASS_HUE:
    dn, tn = flip_angle(cls, -1)
    dp, tp = flip_angle(cls, +1)
    margins[cls] = (dn, dp)
    print(f'{cls:<12s} {CLASS_HUE[cls]:>7.2f}° {dn:>9.1f}° {tn:<12s} {dp:>9.1f}° {tp}')

MIN_MARGIN = min(min(v) for v in margins.values())
print()
print(f'★ 全局最小余量 = {MIN_MARGIN:.1f}°，出现在「红↔黄」这一对上')
print('  —— 这恰好是 TSR 里后果最严重的一对（禁令 vs 警告，下游动作完全不同）')

dp_red, tp_red = flip_angle('禁令(红)', +1)
dn_red, tn_red = flip_angle('禁令(红)', -1)
assert 24.5 <= dp_red <= 26.0 and tp_red == '警告(黄)', (dp_red, tp_red)
assert 68.0 <= dn_red <= 70.5 and tn_red == '指示(蓝)', (dn_red, tn_red)
assert 24.5 <= MIN_MARGIN <= 26.0
print()
print(f'✅ 红色禁令牌只要色相 **+{dp_red:.1f}°** 就落进黄色警告牌的色相区间；')
print(f'   反方向要 -{dn_red:.1f}° 才碰到蓝色 —— **风险是高度不对称的**。')"""),

    code(r"""# ── 把常用库的默认值放进同一把尺子 ──
# 注意：OpenCV 的 HSV 色相通道是 0–179（1 单位 = 2°），这是最常被漏掉的换算
LIB_DEFAULTS = [
    ('YOLOv5/v8  hsv_h=0.015（乘性）',                  5.4,  '乘性变换，纯红处偏移≈0'),
    ('torchvision ColorJitter(hue=0.1)',               36.0, 'hue 参数单位是「圈」，0.1 圈 = 36°'),
    ('albumentations HueSaturationValue(20)',          40.0, 'OpenCV 单位 ×2 = 40°'),
    ('RandAugment Color/Hue（大 magnitude）',          60.0, '搜索目标里没有颜色语义约束'),
    ('本课建议：0.5 × 最小余量',        0.5 * MIN_MARGIN,   '留一半余量给传感器白平衡偏差'),
]
print(f"{'配置':<42s} {'最大偏移':>9s} {'相对余量':>9s}  判定")
for name, amp, note in LIB_DEFAULTS:
    ratio = amp / MIN_MARGIN
    verdict = '✅ 安全' if ratio <= 0.75 else ('⚠️ 逼近红线' if ratio < 1.0 else '❌ 越界')
    print(f'{name:<42s} {amp:>8.1f}° {ratio:>8.2f}×  {verdict}   {note}')

# 直接验证：用 albumentations 的默认幅度抖一张红牌，看它被判成什么
img_red = make_scene('禁令(红)', Z=30.0)['img']
sc_red = make_scene('禁令(红)', Z=30.0)
bad = op_hsv_jitter(img_red, dh=40.0)
good = op_hsv_jitter(img_red, dh=0.5 * MIN_MARGIN)
h_bad = sign_hue(sc_red, bad)[0]
h_good = sign_hue(sc_red, good)[0]
print()
print(f'原图圈边  H={sign_hue(sc_red)[0]:7.2f}°  → 判为 {classify_by_hue(sign_hue(sc_red)[0])}')
print(f'+40°  抖动 H={h_bad:7.2f}°  → 判为 {classify_by_hue(h_bad)}   ← **标签已经被改掉了**')
print(f'+{0.5*MIN_MARGIN:.1f}° 抖动 H={h_good:7.2f}°  → 判为 {classify_by_hue(h_good)}')
assert classify_by_hue(h_bad) != '禁令(红)', 'albumentations 默认幅度应当翻类'
assert classify_by_hue(h_good) == '禁令(红)', '建议幅度必须保住类别'
print()
print('⚠️  注意 YOLOv5 的默认值为什么反而安全：它做的是**乘性**色相变换 H\' = H·r，')
print('    偏移正比于色相值本身，而纯红在 OpenCV 里色相值接近 0 或 179 —— ')
print('    **红色恰好是这个实现下最被保护的颜色。这是幸运，不是设计。**')"""),

    md(r"""## 4 · 大气散射雾化：`I = J·t + A(1-t)`，`t = exp(-βd)`

雾必须依赖**深度**。同时验证前面的色彩代数：雾是仿射变换，所以
**色相的偏移完全来自大气光 A 的非中性**（天空偏蓝）。"""),

    code(r"""def beta_from_visibility(V):
    '''Koschmieder：能见度定义为对比度衰减到 5% 的距离 → β = -ln(0.05)/V ≈ 3.0/V'''
    return -np.log(0.05) / float(V)

def transmittance(d, V):
    return np.exp(-beta_from_visibility(V) * np.asarray(d, dtype=float))

def apply_fog(img, depth, V, A=(0.85, 0.86, 0.90)):
    t = transmittance(depth, V)[..., None]
    return np.clip(img * t + np.array(A).reshape(1, 1, 3) * (1.0 - t), 0.0, 1.0)

sc = make_scene('禁令(红)', Z=30.0)
V_TEST = 100.0
fog = apply_fog(sc['img'], sc['depth'], V_TEST)
t_sign = float(transmittance(sc['Z'], V_TEST))

# ① 对比度被严格乘以 t（同深度处，A 是常数 → 差值项只剩 t）
bg_ring = (~sc['mask']) & (np.arange(IMG_H)[:, None] < sc['y_h'])   # 标志周围的天空
c_clear = float(np.abs(sc['img'][sc['rim']].mean(0) - sc['img'][bg_ring].mean(0)).mean())
c_fog   = float(np.abs(fog[sc['rim']].mean(0)     - fog[bg_ring].mean(0)).mean())
print(f'能见度 V={V_TEST:.0f} m  →  β={beta_from_visibility(V_TEST):.4f} /m，标志处 t={t_sign:.4f}')
print(f'① 对比度：清晰 {c_clear:.4f} → 雾中 {c_fog:.4f}   比值 {c_fog/c_clear:.4f}（理论应为 t_sign）')

# ② / ③ 饱和度与色相
h_c, s_c, v_c = sign_hue(sc)
h_f, s_f, v_f = sign_hue(sc, fog)
print(f'② 饱和度：{s_c:.3f} → {s_f:.3f}   比值 {s_f/s_c:.3f}   ← **雾是饱和度杀手**')
print(f'③ 色相  ：{h_c:.2f}° → {h_f:.2f}°   偏移 {hue_shift(h_f, h_c):.2f}°   ← 远小于 25° 红线')

# 关键验证：A 换成中性灰，色相应当**严格不变**
fog_neutral = apply_fog(sc['img'], sc['depth'], V_TEST, A=(0.87, 0.87, 0.87))
h_n = sign_hue(sc, fog_neutral)[0]
print(f'   把 A 换成中性灰(0.87,0.87,0.87)：色相偏移 {hue_shift(h_n, h_c):.6f}°')

assert abs(c_fog / c_clear - t_sign) < 0.02, '对比度衰减必须等于透射率'
assert s_f / s_c < 0.55, '雾必须显著压低饱和度'
assert hue_shift(h_f, h_c) < 15.0, '偏蓝的大气光只带来小幅色相偏移'
assert hue_shift(h_n, h_c) < 1e-9, '中性大气光下色相必须严格不变'
assert classify_by_hue(h_f) == '禁令(红)', '雾不应改变颜色族判定'
print()
print('✅ 三条结论全部验证：**雾杀对比度和饱和度，几乎不动色相**。')
print('   推论：靠饱和度做决策的分类器雾天直接失效，靠色相的相对稳健 ——')
print('   **前提是你训练时没把色相抖乱。**（这两节的结论是连在一起的）')"""),

    code(r"""# ── 能见度 → 最远可用距离：一个应该被背下来的表 ──
def max_range_at_contrast(V, t_min):
    '''保住 t_min 比例的原始对比度，最远能到多少米。'''
    return float(np.log(1.0 / t_min) / beta_from_visibility(V))

CRUISE = 25.0     # m/s，约 90 km/h
print(f"{'能见度 V':>9s} {'β (/m)':>9s} {'t@30m':>8s} {'t@60m':>9s} "
      f"{'保住20%对比度的最远距离':>22s} {'剩余时间':>9s}")
for V in [500, 200, 100, 50, 20]:
    b = beta_from_visibility(V)
    dmax = max_range_at_contrast(V, 0.20)
    print(f'{V:>8.0f} m {b:>9.4f} {float(transmittance(30, V)):>8.3f} '
          f'{float(transmittance(60, V)):>9.4f} {dmax:>21.0f} m {dmax/CRUISE:>8.2f} s')

d50 = max_range_at_contrast(50, 0.20)
assert 26.0 < d50 < 28.0, d50
assert abs(float(transmittance(60, 50)) - 0.0275) < 0.002
print()
print(f'★ 能见度 50 m 时，标志最远只能在 {d50:.0f} m 处保住 20% 对比度；')
print(f'  以 90 km/h 巡航，从检出到经过只剩 {d50/CRUISE:.1f} 秒 ——')
print('  **多帧确认 + 决策 + 执行全部要挤进这 1 秒。**')
print('  所以雾天 TSR 不是「精度掉一点」，而是**系统性地来不及**；')
print('  工程解法是降速/降级/依赖地图先验，而不是指望模型再强一点。')"""),

    md(r"""## 5 · 运动模糊核与那个「与焦距无关」的比值

`L_blur = f·X·v/Z² · t_exp`，`s_px = f·S/Z`  ⟹  `L/s = X·v·t_exp/(S·Z)`——**f 被消掉了**。"""),

    code(r"""def conv2d_same(img, k):
    '''边缘复制填充的 same 卷积（纯 numpy，支持 HxW 与 HxWxC）。'''
    a = img[..., None] if img.ndim == 2 else img
    kh, kw = k.shape
    assert kh % 2 == 1 and kw % 2 == 1, '核尺寸必须是奇数'
    ph, pw = kh // 2, kw // 2
    pad = np.pad(a, ((ph, ph), (pw, pw), (0, 0)), mode='edge')
    out = np.zeros_like(a, dtype=float)
    H, W = a.shape[:2]
    for i in range(kh):
        for j in range(kw):
            if k[i, j] != 0.0:
                out += k[i, j] * pad[i:i + H, j:j + W]
    return out[..., 0] if img.ndim == 2 else out

def motion_kernel(length, angle_deg):
    '''长度 length（像素）、方向 angle_deg 的线状运动模糊核。'''
    L = max(1, int(round(length)))
    ks = 2 * int(np.ceil(L / 2)) + 1
    k = np.zeros((ks, ks))
    c = ks // 2
    th = np.deg2rad(angle_deg)
    for i in range(L):
        s = i - (L - 1) / 2.0
        y = int(round(c - s * np.sin(th)))
        x = int(round(c + s * np.cos(th)))
        k[y, x] += 1.0
    return k / k.sum()

k5 = motion_kernel(5, 0.0)
assert abs(k5.sum() - 1.0) < 1e-12, '核必须归一化（否则会改变整体亮度）'
flat = np.full((20, 20), 0.4)
assert np.allclose(conv2d_same(flat, motion_kernel(7, 30.0)), 0.4, atol=1e-12), '常量图卷积后应不变'
print('运动模糊核 length=5, angle=0：')
print(k5[k5.shape[0] // 2 - 1: k5.shape[0] // 2 + 2])

def blur_len_px(f, X, Z, v, t_exp):   return f * X * v / Z ** 2 * t_exp
def sign_px(f, S, Z):                 return f * S / Z

X_OFF, S_SIGN = 3.0, 0.60      # 路侧标志的横向偏移 / 物理直径
print()
print(f"{'场景':<18s} {'v(m/s)':>7s} {'Z(m)':>6s} {'t_exp':>8s} "
      f"{'L(px)':>7s} {'s(px)':>7s} {'L/s':>8s}  后果")
CASES = [('高速白天巡航', 25, 30, 0.010, '可忽略'),
         ('高速白天近距', 25, 10, 0.010, '边缘变软'),
         ('夜间城区',     14, 10, 0.030, '数字糊'),
         ('夜间高速近距', 25, 10, 0.030, '**高频被抹掉**'),
         ('雨夜长曝光',   20,  8, 0.040, '只剩颜色与轮廓')]
for name, v, Z, te, note in CASES:
    L = blur_len_px(F_PX, X_OFF, Z, v, te)
    s = sign_px(F_PX, S_SIGN, Z)
    print(f'{name:<18s} {v:>7.0f} {Z:>6.0f} {te*1000:>6.0f} ms {L:>7.2f} {s:>7.1f} '
          f'{L/s:>7.1%}  {note}')

# 关键性质：比值与焦距无关
for f_try in [500.0, 1000.0, 2500.0]:
    r_ = blur_len_px(f_try, X_OFF, 10.0, 25.0, 0.030) / sign_px(f_try, S_SIGN, 10.0)
    assert abs(r_ - X_OFF * 25.0 * 0.030 / (S_SIGN * 10.0)) < 1e-12
print()
print('✅ **L/s 与焦距无关** —— 换长焦看远处标志，模糊和目标一起放大，比值不变。')
print('   所以「上长焦」解决不了运动模糊，这是一个第一反应常想错的结论。')

# 真的把它糊一遍，看牌面高频损失了多少
sc10 = make_scene('禁令(红)', Z=10.0)          # 60 px 的标志
L_night = blur_len_px(F_PX, X_OFF, 10.0, 25.0, 0.030)
blurred = conv2d_same(sc10['img'], motion_kernel(L_night, 5.0))
def hf_energy(im, box, axis=None):
    # axis=1 只看水平方向高频（运动模糊近水平时应当看这个方向）；axis=None 看各向同性
    x0, y0, x1, y1 = box
    p = im[y0:y1, x0:x1].mean(-1)
    gv = float(np.abs(np.diff(p, axis=0)).mean())
    gh = float(np.abs(np.diff(p, axis=1)).mean())
    return gh if axis == 1 else (gv if axis == 0 else (gv + gh) / 2)

e0, e1 = hf_energy(sc10['img'], sc10['bbox'], 1), hf_energy(blurred, sc10['bbox'], 1)
print(f'\n夜间高速近距（L={L_night:.1f} px，标志 {sc10["d_px"]:.0f} px，模糊方向近水平）：')
print(f'  牌面**水平**高频能量 {e0:.4f} → {e1:.4f}，保留 {e1/e0:.1%}')
print(f'  垂直方向高频保留 '
      f'{hf_energy(blurred, sc10["bbox"], 0)/hf_energy(sc10["img"], sc10["bbox"], 0):.1%}'
      f'  ← 运动模糊是**各向异性**的，只削与运动方向平行的那一半信息')
assert e1 < e0 * 0.65, '这么长的水平模糊必须显著削掉水平高频'
assert (hf_energy(blurred, sc10['bbox'], 0) / hf_energy(sc10['img'], sc10['bbox'], 0)
        > e1 / e0), '垂直方向受损应当小于水平方向'
print('  ⚠️ 这正是「夜间检得出但认错」的物理根因：区分 60/80 的那点高频没了。')"""),

    md(r"""## 6 · 卷帘快门：畸变可忽略，时间戳不可忽略"""),

    code(r"""def rolling_shutter(img, total_shift_px):
    '''逐行横向剪切：第 r 行相对第 0 行平移 total_shift_px·r/(H-1)（线性插值）。'''
    H, W = img.shape[:2]
    xs = np.arange(W, dtype=float)
    out = np.empty_like(img)
    for r in range(H):
        s = total_shift_px * r / (H - 1)
        for c in range(img.shape[2]):
            out[r, :, c] = np.interp(xs - s, xs, img[r, :, c])
    return out

T_RO, H_FULL, YAW = 0.020, 1080, 0.5        # 整帧读出 20 ms / 全帧高 1080 / 横摆 0.5 rad/s
frame_shift = F_PX * YAW * T_RO             # 整帧横向错切（像素）
sign_rows = sc['bbox'][3] - sc['bbox'][1]
obj_shift = frame_shift * sign_rows / H_FULL
ego_move = 30.0 * T_RO                      # 30 m/s 巡航下，帧内首尾行的自车位移

print(f'整帧读出时间 T_ro = {T_RO*1000:.0f} ms，横摆 ω = {YAW} rad/s')
print(f'  · 整帧横向错切 = f·ω·T_ro = {frame_shift:.1f} px')
print(f'  · 一块 {sign_rows} 行高的标志，其**内部**错切 = {obj_shift:.3f} px  ← 可忽略')
print(f'  · 帧内首尾行的时间差 = {T_RO*1000:.0f} ms → 30 m/s 下自车位移 {ego_move:.2f} m')
assert obj_shift < 1.0, '小目标的帧内卷帘畸变小于 1 px'
assert ego_move > 0.5, '整帧时间差对应的自车位移是米级的'

# 投影误差：0.6 m 的位姿误差，投到 30 m 外的标志上是多少像素？
lateral_err_px = F_PX * ego_move / 30.0 * 0.15   # 取 15% 分量投到像平面（保守估计）
print(f'  · 若用「帧时间戳」做运动补偿，30 m 外目标的预测位置误差可达 ~{lateral_err_px:.1f} px')
print(f'    对一个 {sc["d_px"]:.0f} px 的目标，这足以让 IoU 关联失败 → 跟踪 ID 频繁切换')
assert lateral_err_px > 2.0

rs = rolling_shutter(sc['img'], frame_shift)
print(f'\n实际剪切后，图像与原图的平均绝对差 = {np.abs(rs - sc["img"]).mean():.5f}')
print(f'标志框内的平均绝对差 = '
      f'{np.abs(rs - sc["img"])[sc["bbox"][1]:sc["bbox"][3], sc["bbox"][0]:sc["bbox"][2]].mean():.5f}')
print()
print('✅ 结论：**卷帘畸变不用做成增强**（对小目标像素分布几乎没影响），')
print('   但**时序融合必须用行时间戳**（C55 模块 04 的运动补偿依赖它）。')
print('⚠️  症状指纹：跟踪 ID 频繁切换、迟滞状态机反复重置 ——')
print('    根因在传感器时间模型上，在跟踪算法里怎么调都调不好。')"""),

    md(r"""## 7 · 低光合成：泊松散粒 + 高斯读出 + 数字增益 + 量化

物理上正确的做法：**sRGB 反推回线性 → 缩放曝光 → 泊松采样 → 加读出噪声 →
数字增益拉回亮度 → 重新 gamma 编码 → 量化到 8 bit**。
`img + N(0,σ)` 这一行代码在物理上是错的。"""),

    code(r"""def low_light(img, exposure_ratio, full_well=8000.0, read_noise_e=3.0,
              gamma=2.2, bits=8, seed=0):
    r = np.random.default_rng(seed)
    lin = np.clip(img, 0.0, 1.0) ** gamma                 # sRGB → 线性辐射（近似）
    N = lin * full_well * exposure_ratio                  # 期望光电子数
    sig = r.poisson(N).astype(float) + r.normal(0.0, read_noise_e, N.shape)
    out = sig / (full_well * exposure_ratio)              # 数字增益 = 1/曝光比（把亮度拉回来）
    out = np.clip(out, 0.0, 1.0) ** (1.0 / gamma)
    q = 2 ** bits - 1
    return np.round(out * q) / q

def patch_snr(im):
    p = im.mean(-1)
    return float(p.mean() / (p.std() + 1e-12))

# 用一块**完全均匀**的灰板量 SNR：场景里的纹理会给 SNR 加一个与曝光无关的地板，
# 把 √N 的规律掩盖掉 —— 这本身就是「测噪声要用平场（flat field）」的工程常识。
FLAT = np.full((48, 48, 3), 0.35)
print(f"{'曝光比':>8s} {'平场SNR':>10s} {'相对 1.0':>10s} {'理论 √比值':>12s}")
snrs = {}
for e in [1.0, 1/2, 1/4, 1/8, 1/16, 1/64]:
    snrs[e] = patch_snr(low_light(FLAT, e, seed=3))
    print(f'{e:>8.4f} {snrs[e]:>10.2f} {snrs[e]/snrs[1.0]:>10.3f} {np.sqrt(e):>12.3f}')

ratio = snrs[1.0] / snrs[1/16]
print(f'\n曝光降 16× → SNR 降 {ratio:.2f}×（散粒噪声主导时理论值 √16 = 4）')
assert 3.0 <= ratio <= 5.5, ratio
assert all(snrs[a] > snrs[b] for a, b in [(1.0, 1/4), (1/4, 1/16), (1/16, 1/64)]), 'SNR 必须单调下降'

# 低光对牌面的破坏：用「与原图的偏差」度量，不要用「梯度能量」
# —— 噪声会**凭空造出**梯度，梯度能量反而上升，这个陷阱与 JPEG 那一节是同一个
x0, y0, x1, y1 = sc['bbox']
ref_patch = sc['img'][y0:y1, x0:x1]
print()
print(f"{'曝光比':>8s} {'牌面RMSE':>10s} {'牌面PSNR':>10s} {'梯度能量比':>11s} {'圈边色相偏移':>13s}")
for e in [1/4, 1/16, 1/64]:
    im = low_light(sc['img'], e, seed=5)
    rmse = float(np.sqrt(np.mean((im[y0:y1, x0:x1] - ref_patch) ** 2)))
    print(f'{e:>8.4f} {rmse:>10.4f} {10*np.log10(1/max(rmse**2,1e-12)):>9.2f} dB '
          f'{hf_energy(im, sc["bbox"])/hf_energy(sc["img"], sc["bbox"]):>10.1%} '
          f'{hue_shift(sign_hue(sc, im)[0], sign_hue(sc)[0]):>12.2f}°')
print('  ↑ 注意「梯度能量比」超过 100% —— **噪声凭空造出了高频**。')
print('    所以度量退化必须看「与原图的偏差」，不能看「梯度能量的绝对值」。')
print()
print('✅ SNR ∝ √N：曝光降 16 倍，信噪比只降 4 倍 ——')
print('   这解释了「稍微暗一点还行，暗过某个点突然崩」：')
print('   一旦光电子数 N 掉到与读出噪声 σ_r² 同量级，读出噪声接管，SNR 转为线性下降。')
print('⚠️  夜间的两条路都在削同一样东西：')
print('    拉长曝光 → 运动模糊按 t_exp 线性增长（第 5 节）')
print('    拉高增益 → SNR 按 √N 下降（本节）')
print('    **所以低光合成与运动模糊必须成对进增强配方。**')"""),

    md(r"""## 8 · JPEG 8×8 DCT 量化：压缩伪影如何吃掉限速牌上的数字"""),

    code(r"""def dct_mat(N=8):
    n = np.arange(N)
    M = np.cos(np.pi * (2 * n[None, :] + 1) * n[:, None] / (2 * N)) * np.sqrt(2.0 / N)
    M[0] = M[0] / np.sqrt(2.0)
    return M

DCT8 = dct_mat(8)
assert np.allclose(DCT8 @ DCT8.T, np.eye(8), atol=1e-12), 'DCT 基必须正交归一'

Q50 = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99]], dtype=float)

def qtable(quality):
    s = 5000.0 / quality if quality < 50 else 200.0 - 2.0 * quality
    return np.clip(np.floor((Q50 * s + 50.0) / 100.0), 1.0, 255.0)

def jpeg_like(img, quality):
    '''分块 DCT + 量化 + 反变换（JPEG 的核心损失环节，省略了色度下采样与熵编码）。'''
    x = np.clip(img, 0, 1) * 255.0 - 128.0
    H, W, C = x.shape
    assert H % 8 == 0 and W % 8 == 0, '为简化，要求尺寸是 8 的倍数'
    Q = qtable(quality)
    out = np.zeros_like(x)
    for c in range(C):
        for i in range(0, H, 8):
            for j in range(0, W, 8):
                blk = x[i:i + 8, j:j + 8, c]
                co = DCT8 @ blk @ DCT8.T
                co = np.round(co / Q) * Q
                out[i:i + 8, j:j + 8, c] = DCT8.T @ co @ DCT8
    return np.clip((out + 128.0) / 255.0, 0.0, 1.0)

def psnr(a, b):
    return float(10.0 * np.log10(1.0 / max(np.mean((a - b) ** 2), 1e-12)))

def patch_psnr(a, b, box):
    x0, y0, x1, y1 = box
    return psnr(a[y0:y1, x0:x1], b[y0:y1, x0:x1])

def hf_distortion(a, b, box):
    # 牌面高频被**改动**了多少（注意不是「衰减」：块效应与振铃会**凭空造出**高频）
    x0, y0, x1, y1 = box
    ha = np.diff(a[y0:y1, x0:x1].mean(-1), axis=1)
    hb = np.diff(b[y0:y1, x0:x1].mean(-1), axis=1)
    return float(np.linalg.norm(hb - ha) / (np.linalg.norm(ha) + 1e-12))

def blockiness(im):
    # 块效应指标：8 的倍数列上的梯度 / 其余列上的梯度
    p = im.mean(-1)
    gh = np.abs(np.diff(p, axis=1))
    on = ((np.arange(gh.shape[1]) + 1) % 8 == 0)
    return float(gh[:, on].mean() / (gh[:, ~on].mean() + 1e-12))

sc24 = make_scene('禁令(红)', Z=25.0)         # 24 px 的标志 —— 只占 9 个 8×8 块
n_blocks = int(np.ceil(sc24['d_px'] / 8)) ** 2
print(f'标志直径 {sc24["d_px"]:.0f} px → 整个牌面只占 **{n_blocks} 个 8×8 块**')
print()
print(f"{'quality':>8s} {'DC步长':>7s} {'全图PSNR':>10s} {'牌面PSNR':>10s} "
      f"{'牌面高频畸变':>13s} {'块效应':>8s} {'色相偏移':>9s}")
res, resp, hfd = {}, {}, {}
for q in [95, 85, 70, 50, 30, 15]:
    im = jpeg_like(sc24['img'], q)
    res[q] = psnr(sc24['img'], im)
    resp[q] = patch_psnr(sc24['img'], im, sc24['bbox'])
    hfd[q] = hf_distortion(sc24['img'], im, sc24['bbox'])
    print(f'{q:>8d} {qtable(q)[0,0]:>7.0f} {res[q]:>9.2f} dB {resp[q]:>9.2f} dB '
          f'{hfd[q]:>12.1%} {blockiness(im):>8.2f} '
          f'{hue_shift(sign_hue(sc24, im)[0], sign_hue(sc24)[0]):>8.2f}°')

assert res[95] > res[70] > res[30] > res[15], '全图 PSNR 必须随 quality 单调'
assert resp[95] > resp[70] > resp[30] > resp[15], '牌面 PSNR 必须随 quality 单调'
assert hfd[95] < hfd[70] < hfd[30] < hfd[15], '牌面高频畸变必须随 quality 下降而增大'
assert res[15] - resp[15] > 8.0, '牌面 PSNR 应当比全图 PSNR 差 8 dB 以上'
assert blockiness(jpeg_like(sc24['img'], 15)) > 1.5 * blockiness(sc24['img'])
print()
print(f'★ quality=15 时：全图 PSNR {res[15]:.1f} dB 看着还行，'
      f'**牌面 PSNR 只有 {resp[15]:.1f} dB**（差 {res[15]-resp[15]:.1f} dB）')
print('  —— 压缩损失**集中在标志上**，因为标志正是画面里高频最密的地方。')
print('  用全图 PSNR 评估压缩对 TSR 的影响，会把危害低估一个数量级。')
print()
print('⚠️  关键观察：**颜色（低频）几乎不掉，牌面高频被改得面目全非。**')
print('    注意「高频畸变」不等于「高频衰减」：块效应与振铃会**凭空造出**假边缘，')
print('    所以简单地看梯度能量反而会上升 —— 必须看与原图的差异，不是看绝对能量。')
print('    对应的故障指纹极有特征：')
print('    「检测召回正常（轮廓+颜色还在）、细粒度分类准确率异常低（60/80 分不清）」')
print('    —— 在两级架构里表现为「检测器没问题、分类器背锅」。')
print('✅ 而且训练与部署的编码链路通常不同：')
print('   训练 = 相机→JPEG存盘→解码→训练；车端 = 相机→ISP→直接送模型（无 JPEG）。')
print('   这是一种**反向域差**，必须在 C60 模块 01 的预处理对拍里一起查。')"""),

    md(r"""## ✏️ 练习 1：从数据里推出安全的色相抖动上限

不要用我们写死的四个代表色，而是**从「训练集」统计**每个颜色族的色相分布，
再算出安全上限。实现两个函数：

- `hue_stats(samples)`：`samples = {类名: [色相数组]}` → `{类名: (圆均值, p05, p95)}`。
  **色相是圆周量，必须用圆均值**：`atan2(mean(sin h), mean(cos h))`。
- `safe_hue_limit(stats, safety=0.5)`：相邻类的间隔 = 圆均值之差；
  有效余量 = 半间隔 − 本类的半散布（`(p95-p05)/2`）；返回 `safety ×` 全局最小有效余量。"""),

    code(r"""def hue_stats(samples):
    # TODO: 对每个类算 (圆均值[0,360), p05, p95)
    #       圆均值：ang = atan2(mean(sin), mean(cos))，再转成度并对 360 取模
    #       分位数：先把角度对齐到圆均值附近（减去均值后 wrap 到 [-180,180]），再取分位数、加回
    raise NotImplementedError

def safe_hue_limit(stats, safety=0.5):
    # TODO: ① 按圆均值排序 ② 相邻（含首尾绕回）间隔的一半 = 几何余量
    #       ③ 有效余量 = 几何余量 − 本类半散布 (p95-p05)/2，两侧取较小者
    #       ④ 返回 safety × 全局最小有效余量（不小于 0）
    raise NotImplementedError"""),

    code(r"""# —— 练习 1 自测 ——
_r = np.random.default_rng(11)
SAMPLES = {}
for k, h in CLASS_HUE.items():
    spread = 6.0 if k == '指示(蓝)' else 4.0          # 类内色相散布（真实数据里一定存在）
    SAMPLES[k] = (h + _r.normal(0, spread, 4000)) % 360.0

st = hue_stats(SAMPLES)
for k in CLASS_HUE:
    mu, lo, hi = st[k]
    print(f'{k:<12s} 圆均值 {mu:7.2f}°（真值 {CLASS_HUE[k]:7.2f}°）  '
          f'p05={lo:7.2f}°  p95={hi:7.2f}°  半散布 {((hi-lo)%360)/2:5.2f}°')
    #                                             ↑ 红色会跨 0°，必须用圆周差
    assert hue_dist(mu, CLASS_HUE[k]) < 0.5, f'{k} 圆均值偏差过大'

lim = safe_hue_limit(st, safety=0.5)
lim_strict = safe_hue_limit(st, safety=0.25)
print(f'\n安全上限（safety=0.5）  = ±{lim:.2f}°')
print(f'安全上限（safety=0.25） = ±{lim_strict:.2f}°')
assert 5.0 < lim < 0.5 * MIN_MARGIN, f'扣掉类内散布后必须比理想余量 {0.5*MIN_MARGIN:.1f}° 更保守'
assert abs(lim_strict - lim / 2) < 1e-9
# 红色圆均值±上限 不能翻类
for sgn in (+1, -1):
    assert classify_by_hue((st['禁令(红)'][0] + sgn * lim) % 360.0) == '禁令(红)'
print('\n✅ 练习 1 通过：**幅度不是抄来的，是从数据里算出来的。**')
print(f'   注意它比「理想代表色」算出的 ±{0.5*MIN_MARGIN:.1f}° 更严 —— 类内散布已经吃掉了一部分余量。')"""),

    md(r"""## ✏️ 练习 2：雾天的可用距离预算

实现 `fog_budget(V, t_min, speed, react_time)`，返回一个字典：

- `beta`：散射系数 `-ln(0.05)/V`
- `d_max`：保住 `t_min` 对比度的最远距离 `ln(1/t_min)/beta`
- `t_avail`：`d_max / speed`（秒）
- `ok`：`t_avail >= react_time` 才为 True
- `max_speed`：为了满足 `react_time`，允许的最高车速 `d_max / react_time`"""),

    code(r"""def fog_budget(V, t_min=0.20, speed=25.0, react_time=1.5):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 2 自测 ——
b = fog_budget(50.0, 0.20, 25.0, 1.5)
assert abs(b['beta'] - (-np.log(0.05) / 50.0)) < 1e-12
assert abs(b['d_max'] - max_range_at_contrast(50.0, 0.20)) < 1e-9
assert abs(b['t_avail'] - b['d_max'] / 25.0) < 1e-12
assert b['ok'] is False or b['ok'] == False, '50 m 能见度 + 90 km/h 必须判为不满足'
assert abs(b['max_speed'] - b['d_max'] / 1.5) < 1e-9

print(f"{'能见度':>8s} {'d_max':>8s} {'可用时间':>9s} {'满足1.5s?':>10s} {'建议限速':>12s}")
for V in [500, 200, 100, 50, 20]:
    r = fog_budget(V, 0.20, 25.0, 1.5)
    print(f'{V:>7.0f} m {r["d_max"]:>7.1f} m {r["t_avail"]:>8.2f} s '
          f'{("✅" if r["ok"] else "❌"):>9s} {r["max_speed"]*3.6:>9.0f} km/h')

assert fog_budget(500.0)['ok'] and not fog_budget(50.0)['ok']
assert fog_budget(200.0, speed=25.0)['t_avail'] > fog_budget(100.0, speed=25.0)['t_avail']
print('\n✅ 练习 2 通过：能见度直接换算成**决策时间预算**。')
print('   这个预算表就是「雾天该不该降级/降速」的量化依据 ——')
print('   比「模型在雾天 mAP 掉了 12 个点」有用得多，因为它能直接连到控制策略。')"""),

    md(r"""## ✏️ 练习 3：曝光时间预算（模糊 vs 噪声的二选一）

实现 `exposure_budget(X, v, S, Z, ratio_max)`：给定可接受的 `L_blur/s_px` 上限，
反解允许的最长曝光时间 `t_max = ratio_max·S·Z/(X·v)`；
再实现 `night_tradeoff(...)` 返回 `{'t_max':…, 'gain_needed':…, 'snr_ratio':…}`：
若目标曝光 `t_target` 超过 `t_max`，就必须用数字增益补上缺口
`gain = t_target/t_max`，代价是 SNR 降为 `1/√gain`。"""),

    code(r"""def exposure_budget(X, v, S, Z, ratio_max=0.15):
    # TODO: 返回允许的最长曝光时间（秒）
    raise NotImplementedError

def night_tradeoff(X, v, S, Z, t_target, ratio_max=0.15):
    # TODO: 返回 {'t_max':…, 'gain_needed':…, 'snr_ratio':…}
    #       gain_needed = max(1.0, t_target / t_max)；snr_ratio = 1/sqrt(gain_needed)
    raise NotImplementedError"""),

    code(r"""# —— 练习 3 自测 ——
tm = exposure_budget(3.0, 25.0, 0.6, 10.0, 0.15)
assert abs(tm - 0.15 * 0.6 * 10.0 / (3.0 * 25.0)) < 1e-15, tm
assert abs(tm - 0.012) < 1e-12
# 与第 5 节的正向公式对拍
assert abs(blur_len_px(F_PX, 3.0, 10.0, 25.0, tm) / sign_px(F_PX, 0.6, 10.0) - 0.15) < 1e-12

print(f"{'场景':<16s} {'Z(m)':>6s} {'v(m/s)':>7s} {'t_max':>9s} {'目标曝光':>9s} "
      f"{'需增益':>8s} {'SNR 变为':>9s}")
for name, Z_, v_, tt in [('白天巡航', 30, 25, 0.005), ('白天近距', 10, 25, 0.005),
                         ('夜间城区', 10, 14, 0.030), ('夜间高速', 10, 25, 0.030),
                         ('雨夜',     8, 20, 0.040)]:
    r = night_tradeoff(3.0, v_, 0.6, Z_, tt, 0.15)
    print(f'{name:<16s} {Z_:>6d} {v_:>7d} {r["t_max"]*1000:>7.1f} ms {tt*1000:>7.0f} ms '
          f'{r["gain_needed"]:>8.2f}× {r["snr_ratio"]:>8.2f}×')

r_day = night_tradeoff(3.0, 25.0, 0.6, 30.0, 0.005)
r_night = night_tradeoff(3.0, 25.0, 0.6, 10.0, 0.030)
assert abs(r_day['gain_needed'] - 1.0) < 1e-12, '白天巡航不需要额外增益'
assert r_night['gain_needed'] > 2.0 and r_night['snr_ratio'] < 0.75
assert abs(r_night['snr_ratio'] - 1 / np.sqrt(r_night['gain_needed'])) < 1e-12
print('\n✅ 练习 3 通过：夜间是一个**没有免费午餐的二选一**。')
print('   要么模糊（拉长曝光），要么噪声（拉高增益），两条路削掉的是同一样东西：')
print('   **牌面上区分「限速 60」和「限速 80」的那点高频。**')
print('   所以「夜间为什么掉点」的完整回答必须同时提到这两条路。')"""),

    md(r"""## ✏️ 练习 4：光度增强配置审计器

实现 `audit_photometric(cfg, hue_limit)`，输入是一份增强配置
（`{算子名: {'p':…, 'amp':…}}`），返回 `{'errors': [...], 'warnings': [...], 'ok': bool}`：

1. **error**：出现禁用算子（`channel_shuffle` / `to_gray` / `invert`），且 `p > 0`；
2. **error**：`hue` 的 `amp` 超过 `hue_limit`；
3. **error**：配置里出现 `split == 'val'` 却带随机算子（`cfg` 里给了 `'_split'` 字段）；
4. **warning**：`low_light` 的 `p > 0` 但 `motion_blur` 的 `p == 0`（只模拟了高增益那条路）；
5. **warning**：所有算子概率之积对应的「全触发率」`< 0.001`（增强名义上很强、实际几乎不发生）。"""),

    code(r"""BANNED = {'channel_shuffle', 'to_gray', 'invert'}

def audit_photometric(cfg, hue_limit):
    # TODO
    raise NotImplementedError"""),

    code(r"""# —— 练习 4 自测 ——
GOOD = {'_split': 'train',
        'brightness_mul': {'p': 0.8, 'amp': 0.35}, 'contrast': {'p': 0.5, 'amp': 0.25},
        'gamma': {'p': 0.4, 'amp': 0.35}, 'saturation': {'p': 0.6, 'amp': 0.4},
        'hue': {'p': 0.3, 'amp': 12.0}, 'low_light': {'p': 0.25, 'amp': 1.0},
        'motion_blur': {'p': 0.25, 'amp': 1.0}, 'fog': {'p': 0.15, 'amp': 1.0}}
r = audit_photometric(GOOD, hue_limit=12.6)
print('GOOD :', r)
assert r['ok'] and not r['errors'], r

BAD = dict(GOOD)
BAD['hue'] = {'p': 0.5, 'amp': 40.0}                 # albumentations 默认
BAD['channel_shuffle'] = {'p': 0.1, 'amp': 1.0}
r2 = audit_photometric(BAD, hue_limit=12.6)
print('BAD  :', r2)
assert not r2['ok'] and len(r2['errors']) >= 2
assert any('hue' in e for e in r2['errors']) and any('channel_shuffle' in e for e in r2['errors'])

VAL = {'_split': 'val', 'brightness_mul': {'p': 0.5, 'amp': 0.2}}
r3 = audit_photometric(VAL, hue_limit=12.6)
print('VAL  :', r3)
assert not r3['ok'] and any('val' in e for e in r3['errors']), '验证集出现随机算子必须报错'

ONLY_NOISE = {'_split': 'train', 'low_light': {'p': 0.3, 'amp': 1.0},
              'motion_blur': {'p': 0.0, 'amp': 1.0}}
r4 = audit_photometric(ONLY_NOISE, hue_limit=12.6)
print('NOISE:', r4)
assert any('motion_blur' in w for w in r4['warnings']), '只加噪不加模糊应当告警'

WEAK = {'_split': 'train', **{f'op{i}': {'p': 0.2, 'amp': 0.1} for i in range(5)}}
r5 = audit_photometric(WEAK, hue_limit=12.6)
assert any('触发' in w for w in r5['warnings']), '概率相乘过低应当告警'
print('WEAK :', r5)
print('\n✅ 练习 4 通过：把「配方纪律」写成代码，比写进文档可靠得多。')"""),

    md(r"""---
### 📖 参考答案（先自己做，再对照）"""),

    code(r"""# 练习 1 参考答案
def hue_stats(samples):
    out = {}
    for k, arr in samples.items():
        a = np.asarray(arr, dtype=float) % 360.0
        rad = np.deg2rad(a)
        mu = np.rad2deg(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360.0
        rel = (a - mu + 180.0) % 360.0 - 180.0            # 对齐到均值附近再取分位数
        lo = (mu + np.percentile(rel, 5)) % 360.0
        hi = (mu + np.percentile(rel, 95)) % 360.0
        out[k] = (float(mu), float(lo), float(hi))
    return out

def safe_hue_limit(stats, safety=0.5):
    names = sorted(stats, key=lambda k: stats[k][0])
    mus = [stats[k][0] for k in names]
    n = len(names)
    best = float('inf')
    for i, k in enumerate(names):
        gap_next = (mus[(i + 1) % n] - mus[i]) % 360.0
        gap_prev = (mus[i] - mus[(i - 1) % n]) % 360.0
        lo, hi = stats[k][1], stats[k][2]
        half_spread = ((hi - lo) % 360.0) / 2.0          # 红色跨 0°，必须用圆周差
        eff = min(gap_next, gap_prev) / 2.0 - half_spread
        best = min(best, eff)
    return float(max(0.0, safety * best))"""),

    code(r"""# 练习 2 参考答案
def fog_budget(V, t_min=0.20, speed=25.0, react_time=1.5):
    beta = -np.log(0.05) / float(V)
    d_max = float(np.log(1.0 / t_min) / beta)
    t_avail = d_max / float(speed)
    return {'beta': float(beta), 'd_max': d_max, 't_avail': float(t_avail),
            'ok': bool(t_avail >= react_time), 'max_speed': float(d_max / react_time)}"""),

    code(r"""# 练习 3 参考答案
def exposure_budget(X, v, S, Z, ratio_max=0.15):
    return float(ratio_max * S * Z / (X * v))

def night_tradeoff(X, v, S, Z, t_target, ratio_max=0.15):
    t_max = exposure_budget(X, v, S, Z, ratio_max)
    gain = max(1.0, float(t_target) / t_max)
    return {'t_max': t_max, 'gain_needed': gain, 'snr_ratio': float(1.0 / np.sqrt(gain))}"""),

    code(r"""# 练习 4 参考答案
BANNED = {'channel_shuffle', 'to_gray', 'invert'}      # 成像链路上无对应 → TSR 禁用

def audit_photometric(cfg, hue_limit):
    errors, warnings = [], []
    split = cfg.get('_split', 'train')
    ops = {k: v for k, v in cfg.items() if not k.startswith('_')}
    for name, spec in ops.items():
        p = float(spec.get('p', 0.0))
        if name in BANNED and p > 0:
            errors.append(f'禁用算子 {name} 出现且 p={p}（成像链路上没有对应，等价于改标签）')
        if name == 'hue' and float(spec.get('amp', 0.0)) > hue_limit:
            errors.append(f'hue 幅度 {spec["amp"]}° > 安全上限 {hue_limit}°（会跨越颜色族边界）')
        if split == 'val' and p > 0:
            errors.append(f'val 集出现随机算子 {name}（验证集只允许确定性变换）')
    if ops.get('low_light', {}).get('p', 0) > 0 and ops.get('motion_blur', {}).get('p', 0) == 0:
        warnings.append('low_light 开启但 motion_blur 关闭：只模拟了高增益那条路，'
                        '缺了长曝光那条路')
    if ops:
        all_fire = float(np.prod([float(s.get('p', 0.0)) for s in ops.values()]))
        if all_fire < 1e-3:
            warnings.append(f'全部算子同时触发的概率仅 {all_fire:.2e} —— '
                            f'配方名义上很强，实际强度远低于直觉')
    return {'errors': errors, 'warnings': warnings, 'ok': not errors}"""),

    md(r"""---
## 🧪 真实工程胶囊：一份可直接抄的 TSR 光度增强配置与验证脚本"""),

    code(r"""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
#  TSR 光度增强配方（albumentations 风格）—— 每一行都能说出反推自哪个失效模式
# ══════════════════════════════════════════════════════════════════════
import albumentations as A

HUE_LIMIT_CV = 6      # ★ OpenCV 单位！1 单位 = 2°，所以 6 → ±12°
                      #   默认值 20 等于 ±40°，会把红色禁令牌推进黄色警告牌的色相区间
                      #   （红→黄的边界只有约 25°，见本 notebook 第 3 节）

train_tf = A.Compose([
    # ── 顺序遵循成像链路：几何 → 大气 → 曝光/ISP → 光学 → 传感器 → 编码 ──
    # 几何增强见模块 01（注意：交通标志**禁止水平翻转**）
    A.RandomFog(fog_coef_lower=0.05, fog_coef_upper=0.35, p=0.15),      # 近似；带深度的版本见下
    A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.25, p=0.8),
    A.RandomGamma(gamma_limit=(75, 140), p=0.4),
    A.HueSaturationValue(hue_shift_limit=HUE_LIMIT_CV,                  # ★ 唯一必须捏死的旋钮
                         sat_shift_limit=35, val_shift_limit=25, p=0.4),
    A.MotionBlur(blur_limit=(3, 7), p=0.25),                            # 长度按 X·v·t/(S·Z) 定
    A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=0.25),
    A.ImageCompression(quality_lower=55, quality_upper=95, p=0.2),
], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['labels'],
                            min_visibility=0.25))

# ★ 验证集：一个随机算子都不能有（铁律）
val_tf = A.Compose([A.NoOp()], bbox_params=A.BboxParams(format='pascal_voc',
                                                        label_fields=['labels']))

# ── 带深度的物理雾化（albumentations 的 RandomFog 与深度无关，只能近似）──
def physical_fog(img, depth_m, visibility_m, A_light=None, rng=None):
    # I = J*t + A*(1-t), t = exp(-beta*d), beta = -ln(0.05)/V
    rng = rng or np.random.default_rng()
    beta = -np.log(0.05) / float(visibility_m)
    t = np.exp(-beta * depth_m)[..., None]
    if A_light is None:                       # ★ 随机化 A，避免「合成指纹」
        A_light = rng.uniform(0.75, 0.95) * np.array([1.0, 1.01, 1.06])
    return np.clip(img * t + np.asarray(A_light).reshape(1, 1, 3) * (1 - t), 0, 1)

# ── 物理正确的低光合成（img + N(0,sigma) 是错的）──
def physical_low_light(img, exposure_ratio, full_well=8000., read_e=3., gamma=2.2, rng=None):
    rng = rng or np.random.default_rng()
    lin = np.clip(img, 0, 1) ** gamma                       # sRGB -> 线性
    N = lin * full_well * exposure_ratio                    # 光电子数
    sig = rng.poisson(N) + rng.normal(0, read_e, N.shape)   # 散粒 + 读出
    out = np.clip(sig / (full_well * exposure_ratio), 0, 1) ** (1 / gamma)   # 数字增益 + 编码
    return np.round(out * 255) / 255                        # 8-bit 量化

# ══════════════════════════════════════════════════════════════════════
#  上线前的四项检查（缺一项都可能让「增强」变成「加标签噪声」）
# ══════════════════════════════════════════════════════════════════════
# ① 色相红线：从训练集统计每个颜色族的色相分位数，算出真实类间余量，
#    再取 0.5x 作为 hue_shift_limit。**不要抄默认值。**
# ② 单位换算：albumentations/OpenCV 的 hue 单位是 0-179（1 单位 = 2 度）；
#    torchvision ColorJitter 的 hue 单位是「圈」（0.1 = 36 度）。
# ③ 分桶验证：整体 mAP 会掩盖颜色族错分。必须看
#    (a) 跨颜色族混淆矩阵  (b) 夜间/雾天切片 AP  (c) 细粒度分类准确率（限速 60 vs 80）
# ④ 验证集零随机：断言 val_tf 里不含任何 p<1 的随机算子（写成 CI 检查）
#
# ── 反推表：每个算子对应哪个失效模式（配方 review 时逐行对照）──
#   brightness/contrast  <- 隧道出入口、逆光、阴影
#   gamma                <- 不同车型 ISP 的色调映射曲线差异
#   saturation           <- 褪色标志、雾天去饱和
#   hue (小幅)           <- 白平衡漂移（真实幅度就这么小）
#   low_light + blur     <- 夜间：拉增益 or 拉曝光，二选一，必须成对出现
#   fog (带深度)         <- 雨雾雪天召回塌陷
#   ImageCompression     <- 回传链路压缩；限速数字对分不清
#   ❌ channel_shuffle / to_gray / invert  <- 成像链路上无对应，**禁用**
'''
print(RECIPE)
for token in ['HUE_LIMIT_CV', '1 单位 = 2°', 'physical_fog', 'physical_low_light',
              'min_visibility', 'val_tf', '禁用', 'exp(-beta*d)']:
    assert token in RECIPE, token
print('✅ 配方覆盖：色相红线 / 单位换算 / 物理雾化 / 物理低光 / 验证集零随机 / 失效模式反推表')"""),

    md(r"""### 小结

- **光度增强不改一个标注，却可能改掉标签。** 「不用同步改标注」制造了它很安全的错觉；
  真正的判据是 `p(y | T(x)) = p(y | x)` —— 而 TSR 里颜色进入了 `p(y|x)`。
- **色相就是语义，红线是 25.2°。** 用一组代表色，红色禁令牌正向偏移约 25° 就落进黄色警告的
  色相区间；`albumentations` 默认 `hue_shift_limit=20`（OpenCV 单位 = **±40°**）直接越界，
  `torchvision ColorJitter(hue=0.1)` = ±36° 同样越界；YOLOv5 的 `hsv_h=0.015` 是乘性的，
  只有 ±5.4°，反而安全。**建议上限 = 0.5 × 从数据统计出的最小有效余量。**
- **色彩代数一句话**：亮度/对比度/雾都是逐通道仿射 `aI+b` → **色相严格不变**（b 中性时），
  **`b>0` 必然掉饱和度**；gamma 非线性但只移约 1.4°；显式色相抖动是唯一能跨类别边界的算子。
- **雾要用物理模型**：`I = J·t + A(1-t)`，`t = e^(-βd)`，`β ≈ 3/V`。对比度被严格乘以 `t`，
  饱和度约按 `t` 衰减，色相偏移**全部来自 A 的非中性**。
  能见度 50 m 时标志最远只能在 **27 m** 保住 20% 对比度 → 90 km/h 下只剩 **1.1 秒**。
- **夜间是没有免费午餐的二选一**：拉曝光 → 模糊按 `t_exp` 线性增长；拉增益 → SNR 按 `√N` 下降。
  两条路削的是同一样东西（区分 60/80 的高频）。**所以低光合成与运动模糊必须成对进配方。**
- **`L_blur/s_px = X·v·t_exp/(S·Z)` 与焦距无关** —— 上长焦解决不了运动模糊。
- **卷帘畸变不用做成增强**（小目标帧内错切 < 1 px），但**时序融合必须用行时间戳**：
  20 ms 读出时间在 30 m/s 下是 0.6 m 的自车位移，足以让 IoU 关联失败。
- **JPEG 的 8×8 块对小标志是灾难**：24 px 的牌面只占 9 个块，颜色（低频）几乎不掉但
  牌面高频掉得很快 → 故障指纹是「检测正常、细粒度分类崩」。
- **增强算子必须能挂到成像链路的某一环上**；挂不上去的（channel shuffle / 灰度化 / 反色）
  在 TSR 上等价于随机改标签。

下一站：**模块 03 · 混合类增强** —— Mosaic / MixUp / CutMix / Copy-Paste，
以及长尾类别最直接的那个解法。""")
,
]
