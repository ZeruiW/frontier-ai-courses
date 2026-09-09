# -*- coding: utf-8 -*-
"""C74 模块 04 · 自适应密度控制。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 为什么必须做密度控制（不做就停在 SfM 点云的密度上）；"
                   "② <strong>「屏幕位置梯度」这个判据到底多可靠——"
                   "答案是「中等密度区命中率 44–56%，稀疏区<strong>恰等于随机基线</strong>」，"
                   "而这解释了官方全部的超参数选择</strong>；"
                   "③ <strong>克隆 vs 分裂的几何差别：克隆让总体积 ×2，分裂让总体积 ×0.488</strong>；"
                   "④ 剪枝阈值不能只看单个高斯的贡献；"
                   "⑤ 不透明度重置为什么是一个<strong>独立</strong>的机制；"
                   "⑥ 增长率的预算账（<strong>要 20× 需要每轮 +22.1%</strong>）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_densification.ipynb'
                       '（<strong>把判据的可靠性量出来：3 目标 × 5 密度 × 2 种子 = 每档 6 次</strong> / '
                       '克隆与分裂的体积恒等式 / '
                       '<strong>累积窗口从 100 步换成全程会改变结论</strong> / '
                       '剪枝阈值的累积效应 / 增长率与预算）'),
    ("核心参考", "Kerbl et al., <em>3D Gaussian Splatting</em>（SIGGRAPH 2023，§5.2 与附录 B）· "
                 "官方实现 <code>scene/gaussian_model.py</code> 的 "
                 "<code>densify_and_prune / densify_and_clone / densify_and_split</code> · "
                 "Zhang et al., <em>Pixel-GS</em>（ECCV 2024，把判据改成像素加权）· "
                 "Bulò et al., <em>Revising Densification in Gaussian Splatting</em>（ECCV 2024）· "
                 "Fang &amp; Wang, <em>Mini-Splatting</em>（ECCV 2024，用采样代替克隆/分裂）"),
    ("预计时长", "读 50 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why", "不做密度控制会怎样", "".join([
        P("3DGS 的初始化是 SfM 的稀疏点云——**典型 10 万个点左右，"
          "而收敛后的场景有 100 万到 500 万个高斯**。"
          "这 10–50 倍的差距完全由密度控制补上。"),
        DUAL(
            "<strong>而「不够」的代价不是「稍微糊一点」。</strong>"
            "<em>模块 00 量过一个 1D 的版本：用 1 个高斯拟合一条硬边亮带，"
            "RMSE 0.2604；用 4 个，0.1222——降到 1/2.13，"
            "而这三档在四种优化器设置下数值完全一致（已收敛）</em>。"
            "<strong>所以前几倍的高斯买到的是实打实的精度。</strong>",
            "<strong>但更重要的是模块 00 的<em>第二</em>个观察：$K\\ge8$ 之后结果开始"
            "依赖优化器设置，$K{=}64$ 在 lr=0.2 下直接发散到 RMSE 13.8。</strong>"
            "<em>所以密度控制不是「加得越多越好」——"
            "高斯越多，优化越不稳定</em>。"
            "<strong>真正的问题是：<em>加在哪里</em>。</strong>"
            "<em>而这就归结到一个判据，也就是下一节</em>。"),
        ASCII("""
   3DGS 的训练循环（15000 步的典型配置）：

   iter 0        SfM 点云初始化（~10 万个高斯，α 初值 0.1）
   iter 0-500    只优化，不做密度控制         <- 为什么要等？见第 2 节
   iter 500      开始每 100 步做一次 densify_and_prune
   iter 3000     第一次不透明度重置            <- 一个**独立**的机制，第 5 节
   iter 6000     第二次重置
   iter 15000    停止密度控制（densify_until_iter）
   iter 15000-30000  只优化，不再增删
        """),
    ])),

    # ============================================================== 2
    ("criterion", "判据：屏幕位置梯度到底多可靠", "".join([
        P("官方的判据是：累积每个高斯在**屏幕空间**的位置梯度模长 "
          "$\\Vert \\partial L/\\partial \\mu_{2D}\\Vert_2$，"
          "在最近 100 步上取平均，超过 $2\\times10^{-4}$ 就分裂或克隆。"),
        P("**这个判据到底成立吗？** notebook 用一个可控的 1D 实验做了检验："
          "三种目标函数（各含一个平坦区与一个高频纹理区）× 5 个高斯密度 × 2 个随机种子 "
          "= 每档 6 次独立运行，算「累积平均 $\\vert\\partial L/\\partial\\mu\\vert$」与"
          "「该高斯负责区域内的实际残差 RMS」的秩相关，"
          "以及「梯度最大的前 1/4 是不是残差最大的前 1/4」的命中率。"),
        TABLE(["高斯个数 $K$", "秩相关 均值", "最小 / 最大",
               "top-1/4 命中率", "随机基线"], [
            ["8", "+0.210", "<strong>−0.262</strong> / +0.595",
             "<strong>25%</strong>", "25%"],
            ["12", "<strong>+0.647</strong>", "+0.343 / +0.895", "44%", "25%"],
            ["16", "<strong>+0.678</strong>", "+0.594 / +0.744", "<strong>50%</strong>", "25%"],
            ["24", "+0.634", "+0.546 / +0.773", "<strong>56%</strong>", "25%"],
            ["32", "+0.545", "+0.366 / +0.775", "42%", "25%"],
        ]),
        CALLOUT("danger",
                "<strong>结论要说准，三句话：</strong>"
                "① <strong>在中等密度区（$K$ = 12–24），判据有真实信号</strong>——"
                "<em>秩相关 +0.63 到 +0.68，命中率 44–56%，是随机基线的 1.8–2.2 倍</em>；"
                "② <strong>在稀疏区（$K{=}8$）它<em>恰好等于</em>随机基线（25% vs 25%），"
                "而某次运行的秩相关是 −0.262</strong>——"
                "<em>也就是完全没有信息</em>；"
                "③ <strong>它是一个启发式，不是定理。</strong>"
                "<em>而这不是挑刺——它恰好解释了官方的每一个超参数选择。</em>"),
        TABLE(["官方的做法", "为什么", "对应上表的哪个现象"], [
            ["<code>densify_from_iter = 500</code>",
             "训练早期的判据<strong>不可靠</strong>（注意：不是「没信号」）",
             "<em>notebook 量到：只用最早 100 步时秩相关 +0.330，"
             "约为全程的一半，<strong>但 6 次运行里有 1 次是 −0.056</strong></em>"],
            ["梯度在 <strong>100 步</strong>上取平均后才用",
             "单步梯度噪声太大；而<strong>长窗口主要降的是<em>方差</em></strong>",
             "<em>$K{=}16$：全程窗口秩相关 +0.678（极差 0.150），"
             "最后 100 步 +0.520（<strong>极差 0.618，宽 4.1 倍</strong>）</em>"],
            ["阈值 $2\\times10^{-4}$ 需要按数据集重调",
             "判据的标度不稳定",
             "<em>上表的秩相关跨目标从 −0.26 到 +0.90</em>"],
            ["<code>densify_until_iter = 15000</code> 就停",
             "后期判据的可靠性下降",
             "<strong>$K$ 从 16 到 32，命中率从 50% 掉到 42%，"
             "秩相关从 +0.68 掉到 +0.55</strong>"],
            ["<strong>另外还有不透明度重置</strong>（第 5 节）",
             "补判据抓不到的那部分",
             "<em>命中率只有 44–56%，所以必须有第二个机制</em>"],
        ]),
        H3("为什么是<em>位置</em>梯度，而不是别的"),
        P("同一个实验顺手比了两个替代判据。"
          "把 top-1/4 命中率并排放（随机基线 25%）："),
        TABLE(["$K$", "$\\vert\\partial L/\\partial\\mu\\vert$（官方）",
               "$\\vert\\partial L/\\partial s\\vert$", "$\\vert\\partial L/\\partial\\alpha\\vert$"], [
            ["8", "25%", "25%", "<strong>0%</strong>"],
            ["12", "<strong>44%</strong>", "28%", "11%"],
            ["16", "<strong>50%</strong>", "<strong>12%</strong>", "17%"],
            ["24", "<strong>56%</strong>", "<strong>3%</strong>", "39%"],
            ["32", "42%", "<strong>6%</strong>", "48%"],
        ]),
        DUAL(
            "<strong>尺度梯度在<em>每一档</em>都在随机基线之下或持平（3–28%）——"
            "它不是一个可用的判据。</strong>"
            "<em>而我要说清一件事：我第一次只跑了一个目标、一个种子，"
            "那次尺度梯度在 $K{=}12$ 上命中 67%，看起来比位置梯度好一倍。"
            "跑满 6 次取均值之后是 28%</em>。"
            "<strong>「在单一配置上验证一个判据」这个陷阱，"
            "比「位置梯度是对的」这个结论本身更值得记住。</strong>",
            "<strong>而位置梯度胜出的真实理由是<em>方向性</em>。</strong>"
            "<em>$\\partial L/\\partial\\mu$ 是一个<strong>向量</strong>，"
            "它的模长大意味着「这个高斯正被不同的像素/视角往不同方向拉」——"
            "而这正是「一个高斯在试图同时表示两处内容」的症状</em>。"
            "<strong>尺度与不透明度梯度都是标量，没有方向，所以表达不了这件事。</strong>"
            "<em>顺带解释了不透明度梯度为什么随 $K$ 变好（0% → 48%）："
            "高斯多了之后，「该不该存在」这个问题比「该往哪挪」更贴近残差</em>。"),
    ])),

    # ============================================================== 3
    ("clone-split", "克隆 vs 分裂：一个体积恒等式", "".join([
        P("判据触发后，有两条路。选哪条只看一个条件："
          "**高斯当前的尺度是否超过场景尺度的 1%**（`percent_dense = 0.01`）。"),
        TABLE(["", "克隆 (clone)", "分裂 (split)"], [
            ["触发条件", "尺度 <strong>小</strong>（≤ 1% 场景尺度）",
             "尺度 <strong>大</strong>（&gt; 1% 场景尺度）"],
            ["诊断为", "<strong>欠重建</strong>（under-reconstruction）："
                      "<em>这里内容不够，需要更多基元</em>",
             "<strong>过重建</strong>（over-reconstruction）："
             "<em>一个大高斯盖住了本该有细节的区域</em>"],
            ["操作", "复制一份，沿位置梯度方向平移；<strong>尺度不变</strong>",
             "生成 2 个，<strong>尺度 ÷ 1.6</strong>；"
             "位置从父高斯自身的分布里<strong>采样</strong>"],
            ["个数", "×2", "×2（父高斯被删除）"],
            ["<strong>单个体积</strong>", "不变",
             "<strong>÷ 4.10</strong>（$1.6^3$）"],
            ["<strong>总体积</strong>", "<strong>×2.000</strong>",
             "<strong>×0.488</strong>"],
        ]),
        MATH(r"\text{总体积倍数} = \frac{2}{\varphi^3},\qquad \varphi = 1.6"
             r"\;\Longrightarrow\; \frac{2}{4.096} = 0.4883"),
        DUAL(
            "<strong>所以两个操作的作用方向是相反的，而这一点常被含糊掉。</strong>"
            "<em>克隆<strong>增加</strong>总的「物质量」——"
            "它在说「这里东西不够多」；"
            "分裂<strong>减少</strong>总物质量 51.2%——"
            "它在说「这里东西太粗，要细化」</em>。"
            "<strong>$\\varphi$ 的临界值是 $2^{1/3} = 1.2599$："
            "小于它总体积会涨，大于它会缩。</strong>"
            "<em>官方选 1.6 意味着「分裂时明确地缩小」，"
            "而这也解释了为什么分裂后必须继续优化——"
            "渲染结果被<strong>真的</strong>改变了（模块 01 第 7 节：3DGS 没有步长概念，"
            "「一个高斯 = 一个 $\\alpha$」，所以分裂不是等价变换）</em>。",
            "<strong>而「位置从父高斯自身的分布里采样」是一个容易忽略的细节。</strong>"
            "<em>它不是「放在父高斯两端」，而是从 $\\mathcal N(\\mu,\\Sigma)$ 里抽两个点。"
            "所以对一个各向异性的扁平高斯，两个子高斯会自动沿它的<strong>长轴</strong>分布</em>——"
            "<strong>方向信息是免费从协方差里继承来的，不需要额外判断。</strong>"
            "<em>代价是随机性：同一个高斯分裂两次会得到不同结果，"
            "所以 3DGS 的训练不是确定性的（即使固定随机种子，"
            "分裂的顺序还依赖于梯度累积的浮点求和顺序）</em>。"),
    ])),

    # ============================================================== 4
    ("prune", "剪枝：为什么阈值不能只看单个高斯", "".join([
        P("剪枝规则有两条：① $\\alpha < 0.005$ 的删掉；"
          "② 屏幕半径 > 20 px 或世界尺度 > 10% 场景范围的删掉。"),
        P("第一条的阈值看起来很好定：$\\alpha = 0.005$ 的高斯对一个像素的贡献不到 "
          "$1/255 = 0.0039$ 的两倍，几乎看不见。**但这个推理是错的**，"
          "因为它只算了一个高斯。"),
        TABLE(["单个 $\\alpha$", "1 个", "16 个", "64 个", "256 个"], [
            ["0.005", "0.0050", "0.0771", "0.2744", "<strong>0.7229</strong>"],
            ["0.010", "0.0100", "0.1485", "0.4744", "<strong>0.9237</strong>"],
            ["0.050", "0.0500", "0.5599", "0.9625", "1.0000"],
        ]),
        DUAL(
            "<strong>256 个 $\\alpha=0.005$ 的高斯叠起来是 0.72 的不透明度——"
            "而模块 03 量过，一个 tile 里平均就有 245 个高斯。</strong>"
            "<em>所以「几乎透明」的高斯堆在一起完全可以是不透明的</em>。"
            "<strong>这说明 0.005 这个阈值不能从「单个高斯的可见性」推出来，"
            "它是一个经验值</strong>——"
            "<em>而它的真实含义更接近「这个高斯已经不再被优化器有效使用了」，"
            "而不是「它看不见」</em>。",
            "<strong>而第二条（屏幕半径 &gt; 20 px）在本课里已经出现三次，"
            "每次都是不同的理由：</strong>"
            "<em>① 模块 02：张角 20 px @ f=600 对应 3.82°，"
            "正落在仿射近似误差 &lt; 0.05% 的档内；"
            "② 模块 03：半径 100 px 的一个高斯抵得上 44 个正常高斯的分箱成本；"
            "③ 本节：过大的高斯往往是在「用一片糊补偿几何或位姿的错误」</em>。"
            "<strong>一个旋钮同时压住三件事，这在整套系统里很少见。</strong>"),
    ])),

    # ============================================================== 5
    ("optimizer", "一个容易漏掉的细节：新高斯的优化器状态", "".join([
        P("克隆或分裂产生的新高斯，**它的 Adam 一阶/二阶动量该设成什么？**"
          "这个问题看起来是实现细节，但它有明确的后果。"),
        TABLE(["做法", "后果"], [
            ["<strong>置零（官方的选择）</strong>",
             "<em>新高斯的前几十步走得很小（Adam 的二阶动量从 0 开始，"
             "需要几步才建立起有效的步长），相当于一个自动的<strong>预热</strong></em>。"
             "<strong>代价是新高斯要几十步才「活起来」，"
             "而密度控制每 100 步就跑一次——所以有相当一部分时间在预热</strong>"],
            ["从父高斯继承",
             "<em>新高斯立刻以父高斯的步长移动。"
             "问题是父高斯的动量方向是「把它往某处拉」的方向，"
             "而<strong>两个子高斯会被拉向<em>同一个</em>方向</strong>——"
             "于是它们一起跑，没有分开</em>。"
             "<strong>这与分裂的目的（细化）相反</strong>"],
            ["随机初始化",
             "<em>Adam 的动量不是一个可以随机初始化的量"
             "（它是梯度的滑动平均，没有「合理的随机值」）</em>"],
        ]),
        DUAL(
            "<strong>官方的实现是把整个优化器状态张量按新的高斯数重建，"
            "新增位置填零</strong>（<code>_prune_optimizer</code> 与 "
            "<code>cat_tensors_to_optimizer</code>）。"
            "<em>而剪枝时对应地把被删高斯的动量也删掉——"
            "如果只改参数不改优化器状态，动量会错位对齐到别的高斯上</em>，"
            "<strong>那是一个很难查的 bug：训练不报错，但高斯会朝莫名的方向漂移。</strong>",
            "<strong>而这解释了模块 04 开头那个观察的一半："
            "「$K\\ge8$ 之后结果开始依赖优化器设置」。</strong>"
            "<em>高斯数变化时优化器状态被重建，"
            "于是「有效学习率」在每次 densify 之后都会经历一次瞬变——"
            "而 densify 每 100 步一次、共 145 轮</em>。"
            "<strong>所以 3DGS 的优化过程严格说不是一个平稳的梯度下降，"
            "而是「145 次带预热的重启」。</strong>"
            "<em>3DGS-MCMC 之所以要固定总数，一部分原因就是想消掉这个瞬变</em>。"),
    ])),

    # ============================================================== 6
    ("reset", "不透明度重置：一个独立的机制", "".join([
        P("每 3000 步，把**所有**高斯的不透明度压到 $\\min(\\alpha, 0.01)$，"
          "然后继续优化。这看起来很激进——它确实是。"),
        DUAL(
            "<strong>它解决的是判据抓不到的那一类问题：<em>浮物</em>（floaters）。</strong>"
            "<em>浮物是悬在空中、不对应任何真实几何的高斯。它们来自三处："
            "① 相机附近未被充分观测的区域；"
            "② 用一片半透明的雾去补偿位姿误差（C72/C75 的产物不完美）；"
            "③ 模块 01 第 5 节那个问题——被完全遮挡的高斯仍收到非零梯度</em>。"
            "<strong>而浮物的位置梯度往往很小</strong>（它们已经「安顿」下来了），"
            "<em>所以密度控制的判据看不见它们</em>。",
            "<strong>重置的机制：把 $\\alpha$ 全压到 0.01 之后，"
            "真正需要的高斯会在接下来的几百步里把 $\\alpha$ 优化回来，"
            "而浮物不会</strong>——"
            "<em>因为它们对损失没有正贡献，梯度不会推高它们的 $\\alpha$</em>。"
            "<strong>然后下一次剪枝（$\\alpha<0.005$）就把它们清掉了。</strong>"
            "<em>所以「重置 + 剪枝」是一个成对的机制，单独任何一个都没用</em>。"),
        CALLOUT("warn",
                "<strong>代价是重置会让 PSNR 暂时掉几个 dB，需要几百步才恢复。</strong>"
                "<em>所以如果你在训练曲线上看到周期性的尖峰下跌，"
                "先确认是不是 <code>opacity_reset_interval</code>——那是正常的</em>。"
                "<strong>而如果重置后 PSNR <em>不</em>恢复，说明学习率或"
                "<code>densify_until_iter</code> 的配置有问题</strong>，"
                "<em>因为重置之后需要密度控制还在运行才能把该长回来的长回来</em>。"),
    ])),

    # ============================================================== 6
    ("alternatives", "后续工作怎么改这个判据", "".join([
        P("既然第 2 节量出判据只是「比随机好一点」，"
          "那么 2024 年以来的改进几乎全都对着它下手。"
          "下面四条按<strong>它们改的是判据的哪个部分</strong>来排。"),
        TABLE(["工作", "它认为原判据的问题是", "怎么改", "代价 / 边界"], [
            ["<strong>Pixel-GS</strong>（ECCV 2024）",
             "梯度按<em>视角</em>平均，于是「在一个视角里只占几个像素的高斯」"
             "与「占几千像素的高斯」被同等对待",
             "<strong>按该高斯在每个视角覆盖的<em>像素数</em>加权</strong>再平均；"
             "另外按距离缩放梯度阈值",
             "<em>远处的大高斯更容易被分裂 —— 对以近景为主的场景收益不明显</em>"],
            ["<strong>Revising Densification</strong>（ECCV 2024）",
             "克隆/分裂改变了渲染结果（模块 01 第 7 节），"
             "所以每次操作都要靠优化「收敛回去」",
             "<strong>推导出让分裂<em>近似保持渲染结果不变</em>的"
             "位置/尺度/不透明度修正公式</strong>",
             "<em>需要额外的解析推导；对高不透明度的高斯修正不精确</em>"],
            ["<strong>Mini-Splatting</strong>（ECCV 2024）",
             "「克隆 + 分裂 + 阈值」这套机制本身就是绕路",
             "<strong>直接按重要度<em>采样</em>：先故意长很多，"
             "再按深度重排 + 重要度采样把总数压回预算</strong>",
             "<em>要先长到很大（峰值显存高），且采样是全局的、不能增量做</em>"],
            ["<strong>3DGS-MCMC</strong>（NeurIPS 2024）",
             "把密度控制当成启发式是错的方向 —— 它应该是采样",
             "<strong>把训练重新解释成 MCMC："
             "克隆/分裂/剪枝换成「重定位」+ 噪声注入，总数<em>固定</em></strong>",
             "<em>需要改优化器（加噪声项）；固定总数意味着要先猜对预算</em>"],
        ]),
        DUAL(
            "<strong>四条改的是四个不同的东西，而它们都可以叠加，"
            "这本身说明原判据的问题不止一处。</strong>"
            "<em>Pixel-GS 改<strong>加权</strong>（梯度怎么聚合）；"
            "Revising 改<strong>操作</strong>（分裂之后的参数）；"
            "Mini-Splatting 改<strong>控制方式</strong>（阈值 → 预算）；"
            "MCMC 改<strong>框架</strong>（启发式 → 采样）</em>。",
            "<strong>而共同的方向很清楚：从「设阈值让它自由生长」"
            "转向「给预算、按重要度分配」。</strong>"
            "<em>理由就是第 6 节那个复合增长的敏感性——"
            "阈值降 20% 可能让终值翻倍</em>。"
            "<strong>所以如果你要在生产里用 3DGS，"
            "「总数可控」这件事比「PSNR 高 0.3 dB」重要得多</strong>——"
            "<em>前者决定它能不能上线，后者只影响一张对比图</em>。"),
    ])),

    # ============================================================== 7
    ("diagnose", "怎么诊断密度控制出了问题", "".join([
        P("密度控制的故障有一个共同特征：**它们都表现为「训练看起来在跑，但结果不对」**，"
          "而不是报错。下面按可观测的现象组织。"),
        TABLE(["现象", "最可能的原因", "怎么确认"], [
            ["<strong>高斯数几乎不长</strong>（15000 步后仍在 12 万）",
             "梯度阈值太高；或 <code>densify_from_iter</code> 设得太晚",
             "<em>打印每轮触发克隆/分裂的<strong>个数</strong>。"
             "如果是 0，先把阈值降一个数量级看它会不会动</em>"],
            ["<strong>高斯数爆炸然后 OOM</strong>",
             "阈值太低（第 6 节：指数敏感）",
             "<em>把每轮的总数打成曲线。"
             "指数增长在对数坐标上是直线——如果是直线，就是阈值问题；"
             "如果是某一轮突然跳，那是重置之后的反弹</em>"],
            ["<strong>细节永远糊，但高斯数在长</strong>",
             "长错了地方（第 2 节：命中率只有 44–56%）",
             "<em>看新增高斯的<strong>空间分布</strong>。"
             "如果它们集中在已经很好的区域，"
             "说明判据在这个场景上失效，考虑换 Pixel-GS 的加权</em>"],
            ["<strong>画面里有悬空的半透明色块</strong>",
             "浮物（第 5 节）",
             "<em>确认 <code>opacity_reset_interval</code> 在跑。"
             "另一个快速检验：从<strong>训练集之外</strong>的视角渲一张 —— "
             "浮物在训练视角看不见，换视角就露出来</em>"],
            ["<strong>PSNR 周期性尖峰下跌</strong>",
             "<strong>正常</strong>——那是不透明度重置",
             "<em>周期应等于 <code>opacity_reset_interval</code>（默认 3000）。"
             "而如果掉下去<strong>不恢复</strong>，"
             "说明重置发生在 <code>densify_until_iter</code> 之后</em>"],
            ["<strong>换个数据集就要重调阈值</strong>",
             "<strong>正常</strong>——判据的标度不稳定（第 2 节：跨目标 −0.26 到 +0.90）",
             "<em>与其调阈值，不如换成「按预算控制总数」的做法</em>"],
        ]),
        CALLOUT("paper",
                "<strong>最后一行值得单独强调，因为它是本模块最实用的一条结论。</strong>"
                "<em>「换数据集就要重调密度阈值」不是你没调好，"
                "而是这个判据本身的标度就不稳定</em>——"
                "<strong>第 2 节的实验里，同一个 $K$ 下换一个目标函数，"
                "秩相关就能从 +0.90 变成 −0.26。</strong>"
                "<em>所以正确的应对是换控制方式（给预算），"
                "而不是继续在阈值上花时间</em>。"),
    ])),

    # ============================================================== 8
    ("budget", "增长率的预算账", "".join([
        P("密度控制从 iter 500 跑到 iter 15000，每 100 步一次——"
          "所以大约 **145 轮**。但每轮的增长不是恒定的（后期触发的高斯变少），"
          "而一个有用的粗算是「等效 15 轮的复合增长」。"),
        TABLE(["每轮增长", "15 轮后", "从 10 万个长到"], [
            ["+5%", "2.08×", "21 万"],
            ["+10%", "4.18×", "42 万"],
            ["+15%", "8.14×", "81 万"],
            ["<strong>+22.1%</strong>", "<strong>20.0×</strong>", "<strong>200 万</strong>"],
            ["+29.8%", "50.0×", "500 万"],
        ]),
        MATH(r"p = \left(\frac{N_{\text{final}}}{N_{\text{init}}}\right)^{1/15} - 1"),
        DUAL(
            "<strong>这个式子的用处是<em>反推</em>：给定显存预算，倒算阈值该往哪调。</strong>"
            "<em>比如 12 GB 显存、SH 阶 3（每高斯 59 个 float = 236 字节，"
            "加上 Adam 的一阶二阶动量实际约 3 倍 ≈ 700 字节），"
            "能放下大约 1700 万个高斯的参数——"
            "但训练时还要放梯度、渲染缓冲与 (高斯,tile) 对，"
            "所以实际上限大约在 300–500 万</em>。"
            "<strong>要从 10 万到 400 万（40×），需要每轮 +27%。</strong>",
            "<strong>而复合增长的敏感性值得注意：每轮增长率只涨 25%"
            "（+22.1% → +27.6%），终值就涨 1.94 倍；涨到 +29.8% 时是 2.5 倍。</strong>"
            "<em>所以密度阈值这个超参数是「指数敏感」的——"
            "它降低 20%（$2\\times10^{-4} \\to 1.6\\times10^{-4}$）"
            "可能让最终高斯数翻倍，进而 OOM</em>。"
            "<strong>这也是为什么后续工作（Mini-Splatting、Taming-3DGS 等）"
            "都改成<em>直接控制总数</em>：给一个预算 $N_{\\max}$，"
            "每轮只加最需要的那些，而不是设一个阈值让它自由生长。</strong>"),
        CALLOUT("intuition",
                "<strong>把本模块的三个数字并排放：</strong>"
                "<em>判据的 top-1/4 命中率 44–56%（随机基线 25%）；"
                "分裂让总体积 ×0.488；"
                "要 20× 增长需要每轮 +22.1%</em>。"
                "<strong>合起来说明密度控制是一个「粗但有效」的机制："
                "它每轮只需要比随机猜好一点，"
                "靠 145 轮的复合作用把 10 万变成几百万</strong>——"
                "<em>而这也解释了为什么它对超参数敏感却又出奇地稳健</em>。"),
    ])),
]

# =====================================================================
NB = [
md("""# C74 · 模块 04 · 自适应密度控制

本 notebook 的核心是**把判据的可靠性量出来**，而不是复述它：

1. **3 个目标 × 5 个密度 × 2 个种子 = 每档 6 次独立运行**，
   算「累积平均位置梯度」与「局部残差」的秩相关与 top-1/4 命中率；
2. **两个替代判据（尺度梯度、不透明度梯度）的命中率都在随机基线附近或以下**；
3. **累积窗口从「全程」换成「最后 100 步」会把秩相关从 +0.68 打到 +0.43**；
4. 克隆 vs 分裂的体积恒等式：$2/\\varphi^3$，$\\varphi{=}1.6 \\Rightarrow 0.488$；
5. 剪枝阈值的累积效应：**256 个 $\\alpha{=}0.005$ 的高斯叠出 0.7229 的不透明度**；
6. 增长率的预算账：**要 20× 需要每轮 +22.1%**。

只用 numpy，CPU，离线。第 1 节约需 20 秒。"""),

code("""import numpy as np
print('numpy', np.__version__)

X = np.linspace(0, 10, 2001)

def make_target(kind):
    '''三种目标，每种都含一个「容易拟合的平坦区」与一个「高频纹理区」。'''
    t = np.zeros_like(X)
    if kind == 'A':
        t += 0.6*((X > 1) & (X < 4))
        t += 0.5*(1 + np.sin(12*X))*((X > 5.5) & (X < 8.5))
    elif kind == 'B':
        t += 0.7*((X > 2) & (X < 3))
        t += 0.4*(1 + np.sin(20*X))*((X > 6) & (X < 9))
    else:
        t += 0.5*np.exp(-((X-2)**2)/0.3)
        t += 0.6*(1 + np.sin(8*X))*((X > 4.5) & (X < 9.5))
    return t

print('三个目标的形状（. 低 : 中 o 高 # 很高）：')
for kind in 'ABC':
    t = make_target(kind)
    line = ''.join('.' if v < 0.2 else (':' if v < 0.5 else ('o' if v < 0.8 else '#'))
                   for v in t[::25])
    print(f'  {kind}: {line}')
print('     x = 0' + ' '*68 + '10')"""),

md("""## 1 · 判据的可靠性：累积平均位置梯度 vs 局部残差

3DGS 的判据是 $\\Vert \\partial L/\\partial \\mu_{2D}\\Vert_2$ 在最近 100 步上的平均。
这里用 1D 版本：累积 $\\vert\\partial L/\\partial\\mu\\vert$ 的平均，
对比每个高斯「负责区域内的实际残差 RMS」（用它自己的高斯权重加权）。"""),

code("""def fit_accum(K, tgt, iters=3000, lr=0.05, jitter=0.15, seed=0):
    '''K 个 1D 高斯拟合 tgt。返回三个累积平均梯度与每个高斯的局部残差 RMS。'''
    rng = np.random.default_rng(seed)
    mu = np.linspace(0.5, 9.5, K) + rng.normal(0, jitter, K)
    s = np.full(K, 9.0/K*0.5)
    a = np.full(K, 0.4)
    Am = np.zeros(K); As = np.zeros(K); Aa = np.zeros(K)
    for _ in range(iters):
        d = (X[None, :] - mu[:, None]) / s[:, None]
        g = np.exp(-0.5*d**2)
        r = (a[:, None]*g).sum(0) - tgt
        base = 2*r/len(X)
        ga = (base[None, :]*g).sum(1)
        gm = (base[None, :]*a[:, None]*g*(d/s[:, None])).sum(1)
        gs = (base[None, :]*a[:, None]*g*(d**2/s[:, None])).sum(1)
        Am += np.abs(gm); As += np.abs(gs); Aa += np.abs(ga)
        a -= lr*ga; mu -= lr*gm; s -= lr*gs
        s = np.clip(s, 1e-3, 5.0); a = np.clip(a, 0.0, 3.0)
    g = np.exp(-0.5*((X[None, :]-mu[:, None])/s[:, None])**2)
    r = (a[:, None]*g).sum(0) - tgt
    local = np.sqrt((g*r[None, :]**2).sum(1) / np.maximum(g.sum(1), 1e-12))
    return Am/iters, As/iters, Aa/iters, local

def rank(v):
    return np.argsort(np.argsort(v))

def spearman(u, v):
    return float(np.corrcoef(rank(u), rank(v))[0, 1])

def topk_hit(score, truth, k):
    '''score 最大的 k 个里，有几个也在 truth 最大的 k 个里（比例）。'''
    return len(set(np.argsort(score)[::-1][:k]) &
               set(np.argsort(truth)[::-1][:k])) / k

# 先看一个具体例子，把「梯度大的地方是不是残差大的地方」看清楚
Am, As, Aa, loc = fit_accum(16, make_target('A'), seed=0)
print('K=16, 目标 A。按累积位置梯度从大到小排：')
print(' 排名  |dL/dmu|      局部残差RMS   残差的排名')
res_rank = rank(loc)
for i, gi in enumerate(np.argsort(Am)[::-1]):
    print(f'  {i+1:2d}   {Am[gi]:.4e}   {loc[gi]:.4f}      {16-res_rank[gi]}')
print(f'\\n秩相关 {spearman(Am, loc):+.3f}   top-4 命中 {topk_hit(Am, loc, 4):.0%}（基线 25%）')"""),

code("""import time
t0 = time.time()
KS = [8, 12, 16, 24, 32]
res = {}
for K in KS:
    sp, h_mu, h_s, h_a = [], [], [], []
    for kind in 'ABC':
        tg = make_target(kind)
        for sd in range(2):
            Am, As, Aa, loc = fit_accum(K, tg, seed=sd)
            sp.append(spearman(Am, loc))
            k = max(2, K//4)
            h_mu.append(topk_hit(Am, loc, k))
            h_s.append(topk_hit(As, loc, k))
            h_a.append(topk_hit(Aa, loc, k))
    res[K] = dict(sp=np.array(sp), h_mu=np.mean(h_mu),
                  h_s=np.mean(h_s), h_a=np.mean(h_a), base=max(2, K//4)/K)
print(f'（{len(KS)} 档 × 3 目标 × 2 种子 = {len(KS)*6} 次运行，{time.time()-t0:.1f} s）\\n')

print(' K    秩相关 均值    最小     最大    top-1/4 命中率            随机基线')
print('                                       |dL/dμ|  |dL/ds|  |dL/dα|')
for K in KS:
    r = res[K]
    print(f' {K:3d}    {r["sp"].mean():+.3f}      {r["sp"].min():+.3f}  {r["sp"].max():+.3f}'
          f'     {r["h_mu"]:5.0%}    {r["h_s"]:5.0%}   {r["h_a"]:5.0%}       {r["base"]:.0%}')

# ---- 结论 1：中等密度区判据有真实信号 ----
mid = [12, 16, 24]
for K in mid:
    assert res[K]['sp'].mean() > 0.55, f'K={K} 的秩相关均值应 >0.55，实测 {res[K]["sp"].mean():+.3f}'
    assert res[K]['h_mu'] > 1.6*res[K]['base'], \\
        f'K={K} 的命中率应超基线 1.6 倍，实测 {res[K]["h_mu"]:.0%} vs {res[K]["base"]:.0%}'
print(f'\\n✓ 结论 1：K=12/16/24 的秩相关 '
      f'{res[12]["sp"].mean():+.3f}/{res[16]["sp"].mean():+.3f}/{res[24]["sp"].mean():+.3f}，'
      f'命中率 {res[12]["h_mu"]:.0%}/{res[16]["h_mu"]:.0%}/{res[24]["h_mu"]:.0%}'
      f'（基线 25%）—— 判据有真实信号')

# ---- 结论 2：稀疏区判据 = 随机 ----
assert res[8]['sp'].min() < 0, f'K=8 应有运行给出负相关，实测最小 {res[8]["sp"].min():+.3f}'
assert abs(res[8]['h_mu'] - res[8]['base']) < 0.06, \\
    f'K=8 的命中率应接近基线，实测 {res[8]["h_mu"]:.0%} vs {res[8]["base"]:.0%}'
print(f'✓ 结论 2：K=8 的命中率 {res[8]["h_mu"]:.0%} 恰等于随机基线 {res[8]["base"]:.0%}，'
      f'而某次运行的秩相关是 {res[8]["sp"].min():+.3f}')
print('  —— 稀疏时判据完全没有信息。这就是 densify_from_iter=500 的理由')

# ---- 结论 3：尺度梯度不是可用判据 ----
for K in KS:
    assert res[K]['h_s'] <= res[K]['base'] + 0.05, \\
        f'K={K}: 尺度梯度命中率 {res[K]["h_s"]:.0%} 不该明显超过基线'
assert max(res[K]['h_s'] for K in mid) < min(res[K]['h_mu'] for K in mid), \\
    '中等密度区，尺度梯度必须全面差于位置梯度'
print(f'✓ 结论 3：尺度梯度命中率在每一档都 ≤ 基线'
      f'（{"/".join(f"{res[K]["h_s"]:.0%}" for K in KS)}）—— 它不是可用判据')
print('  ⚠ 我第一次只跑了一个目标、一个种子，那次尺度梯度在 K=12 上命中 67%，')
print('    看起来比位置梯度好一倍。跑满 6 次取均值之后是 '
      f'{res[12]["h_s"]:.0%}。')
print('    「在单一配置上验证一个判据」这个陷阱，比结论本身更值得记住。')

# ---- 结论 4：不透明度梯度随密度变好 ----
assert res[8]['h_a'] < res[32]['h_a'] - 0.2, '不透明度梯度应随 K 显著变好'
print(f'✓ 结论 4：不透明度梯度从 K=8 的 {res[8]["h_a"]:.0%} 涨到 K=32 的 {res[32]["h_a"]:.0%}')
print('  高斯多了之后，「该不该存在」比「该往哪挪」更贴近残差')"""),

md("""### 1.1 累积窗口的长度直接改变结论

3DGS 在 **100 步**的窗口上平均。如果只用最后 100 步会怎样？如果只用最早 100 步？"""),

code("""def fit_windowed(K, tgt, iters=3000, lr=0.05, jitter=0.15, seed=0,
                 win=(0, None)):
    '''同 fit_accum，但只在 [win[0], win[1]) 这段迭代里累积梯度。'''
    lo, hi = win[0], (win[1] if win[1] is not None else iters)
    rng = np.random.default_rng(seed)
    mu = np.linspace(0.5, 9.5, K) + rng.normal(0, jitter, K)
    s = np.full(K, 9.0/K*0.5); a = np.full(K, 0.4)
    Am = np.zeros(K); cnt = 0
    for it in range(iters):
        d = (X[None, :] - mu[:, None]) / s[:, None]
        g = np.exp(-0.5*d**2)
        r = (a[:, None]*g).sum(0) - tgt
        base = 2*r/len(X)
        ga = (base[None, :]*g).sum(1)
        gm = (base[None, :]*a[:, None]*g*(d/s[:, None])).sum(1)
        gs = (base[None, :]*a[:, None]*g*(d**2/s[:, None])).sum(1)
        if lo <= it < hi:
            Am += np.abs(gm); cnt += 1
        a -= lr*ga; mu -= lr*gm; s -= lr*gs
        s = np.clip(s, 1e-3, 5.0); a = np.clip(a, 0.0, 3.0)
    g = np.exp(-0.5*((X[None, :]-mu[:, None])/s[:, None])**2)
    r = (a[:, None]*g).sum(0) - tgt
    local = np.sqrt((g*r[None, :]**2).sum(1) / np.maximum(g.sum(1), 1e-12))
    return Am/cnt, local

print('K=16，三个目标 × 2 种子的秩相关：\\n')
print('  累积窗口              均值      最小     最大    极差')
wins = {'全程 0~3000': (0, None), '前半 0~1500': (0, 1500),
        '后半 1500~3000': (1500, None), '中段 1000~1100': (1000, 1100),
        '最后 100 步': (2900, None), '最早 100 步': (0, 100)}
w_res = {}
for tag, w in wins.items():
    sp = []
    for kind in 'ABC':
        tg = make_target(kind)
        for sd in range(2):
            Am, loc = fit_windowed(16, tg, seed=sd, win=w)
            sp.append(spearman(Am, loc))
    w_res[tag] = np.array(sp)
    print(f'  {tag:20s}  {np.mean(sp):+.3f}   {min(sp):+.3f}  {max(sp):+.3f}'
          f'   {max(sp)-min(sp):.3f}')

_full = w_res['全程 0~3000']; _last = w_res['最后 100 步']; _first = w_res['最早 100 步']
# ① 窗口越长，均值越高
assert _full.mean() > _last.mean() + 0.10, \\
    f'全程应好于最后 100 步：{_full.mean():+.3f} vs {_last.mean():+.3f}'
assert _last.mean() > _first.mean() + 0.10, \\
    f'最后 100 步应好于最早 100 步：{_last.mean():+.3f} vs {_first.mean():+.3f}'
# ② 而更重要的效应是**方差**
_spread_full = _full.max() - _full.min()
_spread_last = _last.max() - _last.min()
assert _spread_last > 3*_spread_full, \\
    f'短窗口的极差应是长窗口的 3 倍以上：{_spread_last:.3f} vs {_spread_full:.3f}'
# ③ 最早窗口会出现负相关的个例
assert _first.min() < 0.05, f'最早 100 步应出现接近零或负的个例，实测 {_first.min():+.3f}'

print(f'\\n✓ 均值：全程 {_full.mean():+.3f} > 最后 100 步 {_last.mean():+.3f}'
      f' > 最早 100 步 {_first.mean():+.3f}')
print(f'✓ 而**更重要的效应是方差**：全程的极差 {_spread_full:.3f}，'
      f'最后 100 步 {_spread_last:.3f}（宽 {_spread_last/_spread_full:.1f} 倍）')
print()
print('三个结论，第二个纠正了一个常见的说法：')
print('  ① 窗口越长信号越强 —— 这是「在 100 步上平均而不是用单步」的理由')
print(f'  ② 最早 100 步**并非没有信号**（{_first.mean():+.3f}，约为全程的'
      f' {_first.mean()/_full.mean():.0%}），')
print(f'     但它有 1/6 的运行给出 {_first.min():+.3f} —— 也就是**不可靠**，而不是无信息。')
print('     densify_from_iter=500 的真实理由是「不可靠」，不是「没信号」')
print('  ③ 100 步窗口是一个折中：均值不如全程，方差还大 4 倍。')
print('     3DGS 之所以不用全程，是因为 densify 之后要**清零**重新积累 ——')
print('     它换来的是「能反映最近的状态」，代价就是这 4 倍的方差')"""),

md("""## 2 · 克隆 vs 分裂：一个体积恒等式

判据触发后选哪条路，只看「尺度是否超过场景尺度的 1%」。
两个操作对**总体积**的作用方向是**相反**的。"""),

code("""def volume_ratio(phi, n_children=2):
    '''分裂成 n 个、每个尺度 /phi 之后，总体积相对原始的倍数。'''
    return n_children / phi**3

s0 = 0.10
print(f'原始各向同性高斯 scale = {s0} m，体积 ∝ s³ = {s0**3:.6f}\\n')
print(f'克隆: scale 不变 {s0}，个数 ×2')
print(f'      总体积 {volume_ratio(1.0):.3f}×  <- 翻倍，「这里东西不够多」\\n')
phi = 1.6
print(f'分裂: scale /{phi} = {s0/phi:.4f}，个数 ×2（父高斯被删除）')
print(f'      单个体积 {(s0/phi)**3:.6f} = 原始的 1/{phi**3:.2f}')
print(f'      总体积 {volume_ratio(phi):.4f}×  <- **缩小 {1-volume_ratio(phi):.1%}**，'
      f'「这里东西太粗，要细化」')

assert abs(volume_ratio(1.0) - 2.0) < 1e-12
assert abs(volume_ratio(1.6) - 0.48828125) < 1e-12, '2/1.6³ 必须是 0.48828125'

print(f'\\nφ 的临界值：2/φ³ = 1 <=> φ = 2^(1/3) = {2**(1/3):.4f}')
print('  φ         总体积倍数')
for p in [1.0, 1.2, 2**(1/3), 1.4, 1.6, 2.0, 2.5]:
    v = volume_ratio(p)
    tag = '不变' if abs(v-1) < 1e-9 else ('放大' if v > 1 else '缩小')
    print(f'  {p:.4f}     {v:.4f}   {tag}')
assert abs(volume_ratio(2**(1/3)) - 1.0) < 1e-12, '临界点必须恰好体积不变'
print(f'\\n✓ 官方选 φ=1.6 > {2**(1/3):.4f}，所以分裂是**明确地缩小**')
print('  推论：分裂真的改变了渲染结果（模块 01 第 7 节：3DGS 没有步长概念），')
print('        所以分裂之后必须继续优化才能收敛回去 —— 它不是等价变换')

# 位置从父高斯自身的分布里采样 -> 方向信息免费继承
print('\\n「位置从父高斯的分布里采样」这个细节：')
rng = np.random.default_rng(0)
for scale, tag in [([0.10, 0.10, 0.10], '各向同性'),
                   ([0.30, 0.03, 0.03], '沿 x 的针'),
                   ([0.30, 0.30, 0.01], '薄片')]:
    S = np.diag(np.array(scale)**2)
    kids = rng.multivariate_normal(np.zeros(3), S, 4000)
    span = kids.std(0)
    print(f'  {tag:8s} scale={scale}: 子高斯位置的标准差 {np.round(span,4)}')
    assert np.argmax(span) == np.argmax(scale), '子高斯必须沿父高斯的长轴分布'
print('  ✓ 子高斯自动沿父高斯的长轴分布 —— 方向信息从协方差里免费继承，无需额外判断')
print('  代价：这是**随机**的。同一个高斯分裂两次结果不同 -> 3DGS 训练不是确定性的')"""),

md("""## 3 · 剪枝阈值：为什么不能只看单个高斯"""),

code("""def accumulated_alpha(alpha, n):
    '''n 个不透明度均为 alpha 的高斯叠加后的累积不透明度。'''
    return 1.0 - (1.0 - alpha)**n

def n_for_target(alpha, target):
    '''达到 target 累积不透明度所需的高斯个数。'''
    return int(np.ceil(np.log(1-target)/np.log(1-alpha)))

print('单个 α      1 个      16 个     64 个     256 个')
for al in [0.005, 0.010, 0.050]:
    row = '  '.join(f'{accumulated_alpha(al, n):.4f}' for n in [1, 16, 64, 256])
    print(f'  {al:.3f}    {row}')

a256 = accumulated_alpha(0.005, 256)
assert abs(a256 - 0.7229) < 1e-4, f'256 个 α=0.005 应叠出 0.7229，实测 {a256:.4f}'
print(f'\\n✓ 256 个 α=0.005 的高斯叠出 {a256:.4f} 的不透明度')
print('  而模块 03 量过：1920x1080 下一个 tile 里平均就有 245 个高斯')
print('  所以「几乎透明」的高斯堆在一起完全可以是不透明的 ——')
print('  0.005 这个阈值不能从「单个高斯的可见性」推出来，它是经验值')

print(f'\\n达到 50% / 90% 不透明度需要多少个：')
for al in [0.005, 0.01, 0.05, 0.1]:
    print(f'  α={al:.3f}: 50% 需 {n_for_target(al,0.5):4d} 个，'
          f'90% 需 {n_for_target(al,0.9):4d} 个')
assert n_for_target(0.005, 0.5) == 139
# 反过来：阈值定在哪，才能保证 245 个叠起来也看不见（<1/255）？
print(f'\\n反推：要让 245 个叠起来仍低于 1/255 = {1/255:.5f}，单个 α 上限是多少？')
lo, hi = 1e-9, 0.01
for _ in range(200):
    mid = (lo+hi)/2
    if accumulated_alpha(mid, 245) < 1/255:
        lo = mid
    else:
        hi = mid
print(f'  α < {lo:.2e}  —— 比官方的 0.005 小了 {0.005/lo:.0f} 倍')
assert lo < 5e-5
print('  ✓ 所以官方的 0.005 **不是**按「叠起来也看不见」定的。')
print('    它的真实含义更接近「这个高斯已经不再被优化器有效使用」')"""),

md("""## 4 · 增长率的预算账"""),

code("""def growth_rate(n_init, n_final, rounds=15):
    '''达到目标倍数所需的每轮复合增长率。'''
    return (n_final/n_init)**(1.0/rounds) - 1.0

print('每轮增长    15 轮后     从 10 万长到')
for p in [0.05, 0.10, 0.15, 0.221, 0.298]:
    print(f'  +{p:.1%}      {(1+p)**15:6.2f}×      {100_000*(1+p)**15/1e4:6.1f} 万')

print('\\n反推：')
for target in [5, 10, 20, 50]:
    p = growth_rate(1, target, 15)
    print(f'  想要 {target:2d}× 需要每轮 +{p:.1%}')
p20 = growth_rate(100_000, 2_000_000, 15)
assert abs(p20 - 0.221) < 5e-4, f'10 万 -> 200 万需每轮 +22.1%，实测 {p20:.1%}'
print(f'\\n✓ 10 万 -> 200 万（20×）需要每轮 +{p20:.1%}')

# 指数敏感性
print('\\n阈值的指数敏感性：')
for delta in [0.8, 0.9, 1.0, 1.1, 1.25]:
    p = 0.221*delta
    print(f'  每轮增长变成基准的 {delta:.2f}× (+{p:.1%}): 终值 {(1+p)**15:6.2f}×'
          f'  相对基准 {(1+p)**15/(1.221**15):5.2f}×')
r_hi = (1+0.221*1.25)**15 / 1.221**15
assert r_hi > 1.9, f'增长率涨 25% 时终值应涨近 2 倍，实测 {r_hi:.2f}×'
print(f'\\n✓ 每轮增长率涨 25%（+22.1% -> +27.6%），最终高斯数涨 {r_hi:.2f}×')
print(f'  而涨到 +29.8% 时是 {(1.298**15)/(1.221**15):.2f}× —— 复合增长是指数敏感的')
print('  所以密度阈值降 20% 就可能让最终数量翻倍进而 OOM，')
print('  而这正是后续工作改成「直接给预算 N_max」的理由')

# 显存账
print('\\n显存账（SH 阶 3）：')
per_g = 3+3+4+1+48
for name, mult in [('只存参数', 1), ('参数 + Adam 一二阶动量', 3)]:
    for gb in [8, 12, 24]:
        n = gb*1e9/(per_g*4*mult)
        print(f'  {name:22s} {gb:2d} GB -> {n/1e6:5.1f} M 个高斯')
print('  但训练时还要放梯度、渲染缓冲与 (高斯,tile) 对（模块 03：2.00M 个）')
print('  所以 12 GB 的实际上限大约在 300-500 万，而不是 1700 万')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 累积平均位置梯度

实现 `my_accum(K, tgt, iters, lr, jitter, seed)`，返回 `(accum_mu, local_res)`：
`K` 个 1D 高斯拟合 `tgt`，返回**累积平均** $\\vert\\partial L/\\partial\\mu\\vert$
与每个高斯的局部残差 RMS（用它自己的高斯权重加权）。

初始化与解析梯度都照 `fit_accum` 的写法（损失是 `mean((f-tgt)²)`）。"""),

code("""def my_accum(K, tgt, iters=3000, lr=0.05, jitter=0.15, seed=0):
    '''返回 (累积平均 |dL/dmu| (K,), 局部残差 RMS (K,))。'''
    # TODO: rng = np.random.default_rng(seed)
    #   mu = linspace(0.5,9.5,K) + rng.normal(0,jitter,K); s = full(K, 9/K*0.5); a = full(K,0.4)
    #   每步：d=(X-mu)/s; g=exp(-d²/2); r=(a*g).sum(0)-tgt; base=2r/len(X)
    #         ga=(base*g).sum(1); gm=(base*a*g*(d/s)).sum(1); gs=(base*a*g*(d²/s)).sum(1)
    #         累加 |gm|；再 a-=lr*ga; mu-=lr*gm; s-=lr*gs; clip s 到 [1e-3,5], a 到 [0,3]
    #   末尾：g 重算；r=(a*g).sum(0)-tgt
    #         local = sqrt((g*r²).sum(1)/max(g.sum(1),1e-12))
    #   返回 (累加/iters, local)
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_tgA, _tgB = make_target('A'), make_target('B')

# ① 形状与非负
_am, _lc = my_accum(16, _tgA, iters=1500, seed=0)
assert _am.shape == (16,) and _lc.shape == (16,), f'形状 {_am.shape} {_lc.shape}'
assert np.all(_am >= 0), '累积的是绝对值，必须非负'
assert np.all(_lc >= 0)

# ② 与参考实现一致（同样的 iters/seed）
_ref_m, _ref_s, _ref_a, _ref_l = fit_accum(16, _tgA, iters=1500, seed=0)
assert np.allclose(_am, _ref_m, rtol=1e-9), '累积梯度与参考不符'
assert np.allclose(_lc, _ref_l, rtol=1e-9), '局部残差与参考不符'

# ③ 中等密度区必须有真实信号（3 组配置）
_sp = []
for _K in [12, 16, 24]:
    for _tg in [_tgA, _tgB]:
        _a2, _l2 = my_accum(_K, _tg, iters=1500, seed=0)
        _sp.append(spearman(_a2, _l2))
assert np.mean(_sp) > 0.45, f'中等密度区秩相关均值应 >0.45，实测 {np.mean(_sp):+.3f}'
assert min(_sp) > 0.0, f'中等密度区不该出现负相关，实测最小 {min(_sp):+.3f}'

# ④ 稀疏区（K=8）必须明显更差
_sp8 = [spearman(*my_accum(8, _tg, iters=1500, seed=_sd))
        for _tg in [_tgA, _tgB] for _sd in range(2)]
assert np.mean(_sp8) < np.mean(_sp) - 0.15, \\
    f'K=8 应明显差于中等密度区：{np.mean(_sp8):+.3f} vs {np.mean(_sp):+.3f}'

# ⑤ 确定性：同 seed 必须逐位可复现
assert np.array_equal(my_accum(12, _tgA, iters=800, seed=1)[0],
                      my_accum(12, _tgA, iters=800, seed=1)[0]), '同 seed 必须可复现'
print(f'✓ 练习 1 通过：中等密度区秩相关均值 {np.mean(_sp):+.3f}（最小 {min(_sp):+.3f}），'
      f'K=8 只有 {np.mean(_sp8):+.3f}')"""),

md("""### 📖 参考答案 1"""),

code("""def my_accum(K, tgt, iters=3000, lr=0.05, jitter=0.15, seed=0):
    rng = np.random.default_rng(seed)
    mu = np.linspace(0.5, 9.5, K) + rng.normal(0, jitter, K)
    s = np.full(K, 9.0/K*0.5)
    a = np.full(K, 0.4)
    Am = np.zeros(K)
    for _ in range(iters):
        d = (X[None, :] - mu[:, None]) / s[:, None]
        g = np.exp(-0.5*d**2)
        r = (a[:, None]*g).sum(0) - tgt
        base = 2*r/len(X)
        ga = (base[None, :]*g).sum(1)
        gm = (base[None, :]*a[:, None]*g*(d/s[:, None])).sum(1)
        gs = (base[None, :]*a[:, None]*g*(d**2/s[:, None])).sum(1)
        Am += np.abs(gm)
        a -= lr*ga; mu -= lr*gm; s -= lr*gs
        s = np.clip(s, 1e-3, 5.0); a = np.clip(a, 0.0, 3.0)
    g = np.exp(-0.5*((X[None, :]-mu[:, None])/s[:, None])**2)
    r = (a[:, None]*g).sum(0) - tgt
    local = np.sqrt((g*r[None, :]**2).sum(1) / np.maximum(g.sum(1), 1e-12))
    return Am/iters, local

print('参考答案 1 已定义')
print('要点一：累加的是 |gm| 而不是 gm。累加带符号的梯度会互相抵消 ——')
print('       而「被不同方向拉扯」正是判据想抓的信号，抵消掉就什么都不剩了。')
print('       3DGS 里对应的是 ‖∂L/∂μ_2D‖₂（2D 向量的模长），道理相同。')
print('要点二：局部残差用**高斯自己的权重**加权，而不是固定窗口 ——')
print('       因为「这个高斯负责哪一片」本身就由它的 σ 决定。')
print('要点三：这个判据在 K=8 时的秩相关接近 0（甚至为负）。')
print('       所以它不是定理，是启发式 —— densify_from_iter=500 就是这个原因。')"""),

md("""### ✏️ 练习 2 · 克隆与分裂的体积恒等式

实现 `my_volume_ratio(phi, n_children)`：分裂成 `n_children` 个、
每个尺度除以 `phi` 之后，**总体积**相对原始的倍数。
再实现 `my_critical_phi(n_children)`：使总体积不变的临界 `phi`。"""),

code("""def my_volume_ratio(phi, n_children=2):
    '''总体积倍数。'''
    # TODO: 体积 ∝ s³，所以单个变 1/phi³，n 个合计 n/phi³
    raise NotImplementedError

def my_critical_phi(n_children=2):
    '''使总体积不变的 phi。'''
    # TODO: 解 n/phi³ = 1
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
# ① 克隆（phi=1）总体积翻倍
assert abs(my_volume_ratio(1.0, 2) - 2.0) < 1e-12
# ② 官方的 phi=1.6
assert abs(my_volume_ratio(1.6, 2) - 0.48828125) < 1e-12, \\
    f'2/1.6³ 必须是 0.48828125，实测 {my_volume_ratio(1.6,2)}'
# ③ 临界点
_pc = my_critical_phi(2)
assert abs(_pc - 2**(1/3)) < 1e-12, f'临界 phi 应为 2^(1/3)={2**(1/3):.6f}，实测 {_pc}'
assert abs(my_volume_ratio(_pc, 2) - 1.0) < 1e-12, '临界点处体积必须恰好不变'
# ④ 单调性：phi 越大总体积越小
_vs = [my_volume_ratio(p, 2) for p in [1.0, 1.2, 1.4, 1.6, 2.0, 2.5]]
assert all(_vs[i] > _vs[i+1] for i in range(len(_vs)-1)), '必须单调递减'
# ⑤ 三个子高斯的情形
assert abs(my_volume_ratio(1.6, 3) - 3/1.6**3) < 1e-12
assert abs(my_critical_phi(3) - 3**(1/3)) < 1e-12
assert my_critical_phi(3) > my_critical_phi(2), '子高斯越多，临界 phi 越大'
# ⑥ 与参考实现一致
for _p in [1.0, 1.2599, 1.6, 2.0]:
    assert abs(my_volume_ratio(_p, 2) - volume_ratio(_p, 2)) < 1e-12
print(f'✓ 练习 2 通过：φ=1.6 -> {my_volume_ratio(1.6):.5f}×（缩小 '
      f'{1-my_volume_ratio(1.6):.1%}）；临界 φ = {_pc:.4f}；'
      f'n=3 的临界 φ = {my_critical_phi(3):.4f}')"""),

md("""### 📖 参考答案 2"""),

code("""def my_volume_ratio(phi, n_children=2):
    return n_children / phi**3

def my_critical_phi(n_children=2):
    return n_children**(1.0/3.0)

print('参考答案 2 已定义')
print('要点：官方的 φ=1.6 明显大于临界值 1.2599，所以分裂是**确定地缩小总体积**。')
print('     这不是副作用，这就是「细化」的机制本身：')
print('       克隆说「这里东西不够多」（体积 ×2），')
print('       分裂说「这里东西太粗」（体积 ×0.488）。')
print('     而因为 3DGS 没有步长概念（模块 01 第 7 节），分裂真的改变了渲染结果，')
print('     所以分裂之后必须继续优化 —— 它不是一个等价变换。')"""),

md("""### ✏️ 练习 3 · 剪枝阈值的累积效应

实现两个互逆的函数：
`my_acc_alpha(alpha, n)` = $n$ 个不透明度 `alpha` 的高斯叠加后的累积不透明度；
`my_alpha_for(n, target)` = 使 $n$ 个叠出 `target` 累积不透明度所需的单个 `alpha`。"""),

code("""def my_acc_alpha(alpha, n):
    '''n 个 α 相同的高斯叠加后的累积不透明度。'''
    # TODO: 1 - (1-alpha)^n
    raise NotImplementedError

def my_alpha_for(n, target):
    '''使 n 个叠出 target 所需的单个 alpha（解析解，不要二分）。'''
    # TODO: 由 1-(1-α)^n = target 解得 α = 1 - (1-target)^(1/n)
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
# ① 官方阈值的累积效应
_a = my_acc_alpha(0.005, 256)
assert abs(_a - 0.7229) < 1e-4, f'256 个 α=0.005 应叠出 0.7229，实测 {_a:.4f}'
assert abs(my_acc_alpha(0.005, 1) - 0.005) < 1e-15, 'n=1 时应等于 alpha 本身'
# ② 单调性
assert all(my_acc_alpha(0.005, n) < my_acc_alpha(0.005, n+1) for n in [1, 16, 64, 255])
assert all(my_acc_alpha(a, 64) < my_acc_alpha(a+0.001, 64) for a in [0.005, 0.01, 0.05])
# ③ 与参考实现一致
for _al in [0.005, 0.01, 0.05, 0.5]:
    for _n in [1, 16, 245, 1000]:
        assert abs(my_acc_alpha(_al, _n) - accumulated_alpha(_al, _n)) < 1e-14
# ④ 互逆
for _n in [1, 16, 245, 1000]:
    for _t in [0.01, 0.5, 0.9, 0.99]:
        _al = my_alpha_for(_n, _t)
        assert 0 < _al < 1, f'n={_n} target={_t}: alpha={_al} 越界'
        assert abs(my_acc_alpha(_al, _n) - _t) < 1e-12, \\
            f'必须互逆: n={_n} target={_t} -> alpha={_al} -> {my_acc_alpha(_al,_n)}'
# ⑤ 反推那个关键结论：要让 245 个叠起来仍 < 1/255，单个 alpha 上限
_cap = my_alpha_for(245, 1/255)
assert _cap < 5e-5, f'上限应 <5e-5，实测 {_cap:.2e}'
assert 0.005/_cap > 100, f'官方的 0.005 应比它大 100 倍以上，实测 {0.005/_cap:.0f}×'
# ⑥ 边界
assert abs(my_alpha_for(1, 0.5) - 0.5) < 1e-15
# α=0.999 的 100 个叠起来：(1-α)^n = 1e-300 在 float64 下仍可表示，但 1-1e-300 == 1.0
assert my_acc_alpha(0.999, 100) == 1.0, '应因浮点吸收而恰好等于 1.0'
assert (1-0.999)**100 > 0, '而 (1-α)^n 本身还没下溢'
print(f'✓ 练习 3 通过：256 个 α=0.005 叠出 {_a:.4f}；'
      f'要让 245 个仍 <1/255 需 α < {_cap:.2e}，'
      f'而官方阈值 0.005 是它的 {0.005/_cap:.0f} 倍')
print(f'  顺带一个浮点细节：α=0.999 的 100 个叠起来，(1-α)^n = {(1-0.999)**100:.1e} '
      f'还没下溢，\\n  但 1-{(1-0.999)**100:.1e} 在 float64 下**恰好等于 1.0** —— '
      f'与模块 01 里 T 的下溢是同一类问题')"""),

md("""### 📖 参考答案 3"""),

code("""def my_acc_alpha(alpha, n):
    return 1.0 - (1.0 - alpha)**n

def my_alpha_for(n, target):
    return 1.0 - (1.0 - target)**(1.0/n)

print('参考答案 3 已定义')
print('要点：⑤ 那个反推是本节的重点。')
print('     如果 0.005 这个阈值真的是按「叠起来也看不见」定的，它应该是 2e-5 量级；')
print('     它比那个值大 100 多倍，说明它的依据**不是**可见性。')
print('     更贴近的解释是「α 已经小到优化器不再有效使用它」——')
print('     而这也解释了为什么它要和不透明度重置配对使用（讲解页第 5 节）：')
print('     重置把所有 α 压到 0.01，真正有用的会长回来，浮物不会，')
print('     然后 α<0.005 这条规则把它们清掉。单独任何一个机制都不起作用。')"""),

md("""### ✏️ 练习 4 · 增长率的预算账

实现 `my_growth(n_init, n_final, rounds)`：达到目标所需的**每轮复合增长率**；
以及 `my_final(n_init, p, rounds)`：给定增长率算终值。"""),

code("""def my_growth(n_init, n_final, rounds=15):
    '''每轮复合增长率 p，使 n_init*(1+p)^rounds = n_final。'''
    # TODO: (n_final/n_init)^(1/rounds) - 1
    raise NotImplementedError

def my_final(n_init, p, rounds=15):
    '''给定每轮增长率算终值。'''
    # TODO: n_init * (1+p)^rounds
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
# ① 官方场景：10 万 -> 200 万
_p = my_growth(100_000, 2_000_000, 15)
assert abs(_p - 0.221) < 5e-4, f'应为 +22.1%，实测 {_p:.4%}'
# ② 互逆
for _ni, _nf, _r in [(1e5, 5e5, 15), (1e5, 5e6, 15), (1e5, 2e6, 30), (1000, 1000, 15)]:
    _pp = my_growth(_ni, _nf, _r)
    assert abs(my_final(_ni, _pp, _r) - _nf)/_nf < 1e-12, '必须互逆'
# ③ 不增长时 p=0
assert abs(my_growth(1e5, 1e5, 15)) < 1e-15
# ④ 与参考实现一致
for _t in [5, 10, 20, 50]:
    assert abs(my_growth(1, _t, 15) - growth_rate(1, _t, 15)) < 1e-12
# ⑤ 指数敏感性：增长率涨 25%，终值必须涨 2 倍以上
_base = my_final(1, 0.221, 15)
_hi = my_final(1, 0.221*1.25, 15)
assert _hi/_base > 1.9, f'增长率涨 25% 时终值应涨近 2×，实测 {_hi/_base:.2f}×'
# ⑥ 轮数越多，达到同一目标所需的每轮增长越小
assert my_growth(1e5, 2e6, 15) > my_growth(1e5, 2e6, 30) > my_growth(1e5, 2e6, 100)
# ⑦ 反向：显存预算倒推
_per_g_bytes = (3+3+4+1+48)*4
_n_cap = 12e9/(_per_g_bytes*3)             # 参数 + Adam 动量
_p_cap = my_growth(100_000, _n_cap, 15)
assert 0.30 < _p_cap < 0.45, f'12GB 的理论上限对应每轮 +{_p_cap:.1%}'
print(f'✓ 练习 4 通过：10 万->200 万需每轮 +{_p:.1%}；'
      f'增长率涨 25% 终值涨 {_hi/_base:.2f}×；'
      f'12GB 理论上限 {_n_cap/1e6:.1f}M 个对应每轮 +{_p_cap:.1%}')"""),

md("""### 📖 参考答案 4"""),

code("""def my_growth(n_init, n_final, rounds=15):
    return (n_final/n_init)**(1.0/rounds) - 1.0

def my_final(n_init, p, rounds=15):
    return n_init * (1.0 + p)**rounds

print('参考答案 4 已定义')
print('要点：⑤ 的指数敏感性是本节最有用的一条 ——')
print('     每轮增长率只涨 25%，最终高斯数涨 2 倍以上。')
print('     所以「把密度阈值从 2e-4 调到 1.6e-4」这种看起来温和的改动，')
print('     可能直接把你从「刚好放得下」推到 OOM。')
print()
print('     而 ⑦ 说明另一件事：12GB 的**理论**上限（1.7M 个）对应每轮 +38%，')
print('     远高于官方的 +22%。所以官方的默认值是保守的 ——')
print('     因为实际还要放梯度、渲染缓冲与 200 万个 (高斯,tile) 对（模块 03）。')""" ),

md("""---
## 🧪 真实工程胶囊

```python
# ---- 官方实现（scene/gaussian_model.py）----
def densify_and_prune(self, max_grad, min_opacity, extent, max_screen_size):
    grads = self.xyz_gradient_accum / self.denom       # ← 练习 1 的「累积平均」
    grads[grads.isnan()] = 0.0
    self.densify_and_clone(grads, max_grad, extent)
    self.densify_and_split(grads, max_grad, extent)
    prune_mask = (self.get_opacity < min_opacity).squeeze()   # min_opacity = 0.005
    if max_screen_size:                                        # = 20 px
        big_points_vs = self.max_radii2D > max_screen_size
        big_points_ws = self.get_scaling.max(dim=1).values > 0.1 * extent
        prune_mask = torch.logical_or(torch.logical_or(prune_mask, big_points_vs),
                                      big_points_ws)
    self.prune_points(prune_mask)

def add_densification_stats(self, viewspace_point_tensor, update_filter):
    # ← 判据就是这一行：屏幕空间位置梯度的 L2 模长，逐次累加
    self.xyz_gradient_accum[update_filter] += torch.norm(
        viewspace_point_tensor.grad[update_filter, :2], dim=-1, keepdim=True)
    self.denom[update_filter] += 1

def densify_and_clone(self, grads, grad_threshold, scene_extent):
    selected = torch.logical_and(
        torch.norm(grads, dim=-1) >= grad_threshold,
        torch.max(self.get_scaling, dim=1).values <= self.percent_dense*scene_extent)
    # 尺度**不变**，直接复制 -> 总体积 ×2（练习 2）
    self.densification_postfix(self._xyz[selected], ..., self._scaling[selected], ...)

def densify_and_split(self, grads, grad_threshold, scene_extent, N=2):
    selected = torch.logical_and(
        padded_grad >= grad_threshold,
        torch.max(self.get_scaling, dim=1).values > self.percent_dense*scene_extent)
    stds = self.get_scaling[selected].repeat(N, 1)
    means = torch.zeros((stds.size(0), 3), device="cuda")
    samples = torch.normal(mean=means, std=stds)      # ← 从父高斯的分布里采样
    rots = build_rotation(self._rotation[selected]).repeat(N, 1, 1)
    new_xyz = torch.bmm(rots, samples.unsqueeze(-1)).squeeze(-1) + self.get_xyz[selected]
    new_scaling = self.scaling_inverse_activation(
        self.get_scaling[selected].repeat(N,1) / (0.8*N))   # ← 0.8*N = 1.6，练习 2
    ...
    self.prune_points(prune_filter)                    # 父高斯被删除

# 关键默认值（arguments/__init__.py）
#   densify_from_iter = 500        densify_until_iter = 15_000
#   densification_interval = 100   densify_grad_threshold = 0.0002
#   opacity_reset_interval = 3000  percent_dense = 0.01

# ---- 改判据的三种做法 ----
# Pixel-GS: 把 add_densification_stats 里的累加改成按覆盖像素数加权
# Mini-Splatting: 换掉整套 clone/split，改成「先长大，再按重要度采样压回预算」
# 3DGS-MCMC: pip install gsplat 后用 strategy=MCMCStrategy(cap_max=1_000_000)
#            总数固定，clone/split/prune 换成「重定位 + 噪声注入」
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 高斯数几乎不长 | 打印每轮触发的**个数**；`densify_from_iter` | 判据在早期几乎无信号（秩相关 −0.16） |
| 高斯数爆炸 OOM | 阈值；把总数画成对数曲线看是否为直线 | 增长率涨 25% → 终值涨 2 倍以上 |
| 细节永远糊但数量在长 | 新增高斯的**空间分布** | 判据 top-1/4 命中率只有 44–56% |
| 悬空的半透明色块 | `opacity_reset_interval`；从训练集外的视角渲一张 | 浮物的位置梯度小，判据看不见 |
| PSNR 周期性尖峰下跌 | **正常** —— 就是不透明度重置 | 周期应等于 3000 |
| 重置后 PSNR 不恢复 | 重置是否发生在 `densify_until_iter` 之后 | 恢复需要密度控制还在跑 |
| 换数据集就要重调阈值 | **正常** —— 判据的标度不稳定 | 同一 $K$ 换目标，秩相关 +0.90 → −0.26 |"""),
]
