# -*- coding: utf-8 -*-
"""C56 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python/numpy；目标检测基础（bbox、IoU、mAP）；C55（TSR 领域知识）与 C57（小目标）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 手写增强算子 + 可执行的正确性断言"),
    ("预计时长", "总览 30 分钟"),
]

SECTIONS = [
    ("prior", "增强的本质：往模型里注入「不变性先验」", "".join([
        P("大多数教材把数据增强讲成「变着法子造更多训练样本」。这个说法不能算错，但它解释不了任何一个真正的工程决策——<strong>为什么 Mosaic 在最后 10 个 epoch 必须关掉？为什么交通标志检测里水平翻转是错的？为什么色相抖动幅度要按类别分开设？</strong>要回答这些，必须换一个更准确的定义。"),
        DUAL(
            "增强是<strong>你在告诉模型：「这些变化不改变答案」</strong>。把一张图左右镜像，它还是一只猫——所以你把镜像后的图配上同一个标签喂进去，模型就被迫学到「左右镜像不影响类别」这条规则。<em>数据本身没有变多，变多的是「约束」。</em>你没有采集新信息，你只是把自己已经知道的物理/语义规律，翻译成了模型能听懂的形式（成对的输入-标签样本）。",
            "形式化地说，标准经验风险最小化是在数据分布 <code>D</code> 上最小化损失；增强则是在一个<span class=\"term\">增广分布</span>（augmented distribution）上最小化损失，其中变换 <code>T</code> 从一个变换族 <code>𝒯</code> 中采样，而<strong>标签同时按一个配套映射 <code>g_T</code> 变换</strong>。当 <code>𝒯</code> 恰好是模型任务真正不变的那个群时，增强等价于在假设空间上施加不变性约束，理论上可以看作一种方差缩减（Chen, Dobriban &amp; Lee, 2020）。<em>当 <code>𝒯</code> 超出真实不变性范围时，它就变成了在教模型错误的规律。</em>",
        ),
        MATH("\\mathcal{R}_{\\text{aug}}(f)\\;=\\;\\mathbb{E}_{(x,y)\\sim\\mathcal{D}}\\;\\mathbb{E}_{T\\sim\\mathcal{T}}\\Big[\\;\\ell\\big(f(T(x)),\\;g_T(y)\\big)\\;\\Big]"),
        P("这个公式里藏着本课全部内容的种子，值得逐项拆开看："),
        UL([
            "<strong><code>𝒯</code>（变换族）选错</strong> → 你在教模型一条现实中不成立的规律。TSR 里的水平翻转就是这个错误的教科书案例：镜像后的「向左转弯」在物理世界里就是「向右转弯」，标签却没跟着变。",
            "<strong><code>g_T</code>（标签变换）写错</strong> → 图变了标注没变，或者变得不对。这是<em>检测</em>增强独有的失败模式，而且极其隐蔽：图看起来完全正常，框错了却没人看得出来。模块 01 整章都在处理这件事。",
            "<strong><code>𝒯</code> 的强度过大</strong> → 增广分布与部署分布严重脱节，模型把容量花在了永远不会遇到的输入上。Mosaic 就是典型：拼接图在真实相机里不存在。",
            "<strong>训练用了 <code>𝒯</code> 而推理没有</strong> → 训练-推理鸿沟。letterbox 与归一化这类「必须两端一致」的算子如果实现不同，框会整体偏移几百像素（模块 01 会给出精确数字，C60 会给出定位方法）。",
        ]),
        CALLOUT("intuition", "把这句话记住，本课后面所有判断都能从它推出来：<strong>增强不是在造数据，是在写一条你相信的物理规律，并且用「成对的样本」这种模型唯一能听懂的语言把它说出来</strong>。既然是「你相信的规律」，那它就<em>可能是错的</em>——而错误的先验比缺少数据更有害，因为模型会稳定地、自信地学会它。"),
    ])),
    ("criteria", "三个判据：一个增强到底该不该用", "".join([
        P("既然增强是先验注入，那「该不该用某个增强」就有了可操作的判据。本课全程会反复使用下面这三条，它们互相独立、缺一不可，<strong>而且必须按顺序检查</strong>——第一条不过，后两条就不用看了。"),
        TABLE(["判据", "问题", "不满足会发生什么", "本课在哪里展开"], [
            ["<strong>① 保标签语义</strong>", "变换后，原来的标签<em>还是正确答案</em>吗？（对检测：类别不变、且框仍紧贴目标）",
             "<strong>模型学到错误规律</strong>，而且它学得很扎实。表现为「某一类稳定地被判成另一类」，用更多数据也救不回来", "模块 01（几何/翻转白名单）、模块 02（色相与颜色语义）"],
            ["<strong>② 贴近部署分布</strong>", "增强产生的图像，车上那台相机<em>有可能拍到</em>吗？",
             "模型容量被浪费在不存在的输入上；<em>更糟的是</em>它会稀释真实分布的有效样本比例，小模型上直接掉点", "模块 02（天气/低光合成）、模块 03（Mosaic 的 close 策略）"],
            ["<strong>③ 不制造训练-推理鸿沟</strong>", "推理端会做同样的事吗？如果不会，差异有多大、有没有显式对齐？",
             "离线 mAP 好看、上车掉一大截。<strong>这是「离线 0.82、路测像 0.6」的头号成因之一</strong>", "模块 01（letterbox 逆变换）、模块 04（TTA 与流水线）、C60（一致性对拍）"],
        ]),
        DUAL(
            "三条判据的顺序不是随便排的，<strong>它反映了危害的量级</strong>。判据① 失败是<em>正确性</em>问题：模型学错了，且错得稳定，你在验证集上也看不出来（因为验证集用了同样错误的标注约定，或者根本没有那个类别的镜像样本）。判据② 失败是<em>效率</em>问题：模型没学错，只是把力气花在了没用的地方，多训练一会儿通常能补回来。判据③ 失败是<em>交付</em>问题：训练本身没问题，只是交出去的东西和训练时不是一个东西。",
            "工程上还有第四个隐含判据：<strong>成本</strong>。增强跑在 CPU 上，而 CPU 常常是训练吞吐的真正瓶颈（模块 04 会量化：一个 GPU 利用率在 40%–95% 之间周期性抖动的训练任务，几乎可以断定卡在数据管线上）。<em>一个只涨 0.1 mAP 却让训练慢 30% 的增强，在有限的调参预算下是净亏损</em>——因为省下的时间本可以多跑两个种子，而模块 05 会证明，两个种子的价值往往超过 0.1 mAP。",
        ),
        CALLOUT("warn", "判据① 有一个特别容易被忽略的子情况：<strong>标签「语义上」还对，但「几何上」不再紧贴目标</strong>。旋转增强就是如此——旋转 45° 后取四角外接框，框仍然框住了标志，类别也没变，看起来一切正常；但<em>框的面积膨胀了整整一倍，一半是背景</em>。模型被反复告知「框住一半背景也算对」，定位精度就这么被慢慢教坏了。模块 01 会把这笔账算到小数点后。"),
    ])),
    ("vs", "增强 vs 正则化 vs 更多数据：三者不能互相替代", "".join([
        P("面试里有一个高频问题：<strong>「增强和 dropout / weight decay 都是防过拟合，有什么区别？」</strong> 很多人答「增强是数据层面的正则化」就停了——这个回答不算错，但它<em>没有回答任何有用的东西</em>。真正的区别在于：三者注入的信息完全不同，因此它们的失效场景也完全不同。"),
        TABLE(["", "增强", "正则化（dropout / weight decay / label smoothing）", "更多真实数据"], [
            ["注入了什么", "<strong>关于任务的具体先验</strong>（哪些变化不改变标签）", "对函数复杂度的<strong>通用偏好</strong>（更平滑、更稀疏）", "<strong>真实的新信息</strong>"],
            ["需要什么知识", "领域知识——你必须知道什么是不变的", "几乎不需要", "钱和时间"],
            ["能覆盖长尾吗", "<strong>部分能</strong>：copy-paste 可以把稀有类样本数翻十倍（模块 03）", "❌ 完全不能", "✅ 能，但稀有类正因为稀有才难采集"],
            ["能修正偏差吗", "❌ 不能：增强只在已有样本的邻域内生成，<em>没见过夜间就变不出夜间</em>（合成除外）", "❌ 不能", "✅ 能"],
            ["典型失败", "先验错了 → 稳定学错", "过强 → 欠拟合，且症状不明显", "加的是模型已经会的 → 边际收益≈0（C58）"],
            ["工程代价", "<strong>CPU 吞吐</strong> + 实现正确性风险", "几乎为零", "标注成本 + 数据闭环基建"],
        ]),
        DUAL(
            "第四行「能修正偏差吗」是最关键的一行，也是最常被误解的一行。<strong>增强只能在已有样本的邻域里生成新样本</strong>——如果训练集里一张夜间图都没有，你把亮度调低 60% 得到的也不是真正的夜间图（真实夜间的噪声结构、光源眩光、ISP 的自动曝光行为、运动模糊长度全都不同）。<em>它像夜间，但它不是夜间。</em>所以「用低光合成代替夜间采集」在幅度小的时候是有效的鲁棒性训练，幅度大的时候就是自欺欺人。",
            "反过来，也有一个方向的替代是成立的：<strong>当某个变化确实属于「真实分布内的、可精确建模的」变换时，增强的性价比远高于采集</strong>。TSR 里最典型的就是<span class=\"term\">尺度</span>——同一块标志在 20 米和 60 米处的像素尺寸差 3 倍，而这个变换就是一次缩放，物理上精确、实现上零风险。<em>与其花钱采集「同一块牌子在各个距离下的样本」，不如把缩放增强的范围开对</em>。这就是为什么模块 01 里「随机缩放」被列为 TSR 收益最高的几何增强，而不是翻转。",
        ),
        CALLOUT("intuition", "一句可迁移的判断法则：<strong>先问「这个变化在部署环境里是不是真的会发生、并且我能不能精确建模它」</strong>。两个都「是」→ 用增强，性价比最高（缩放、平移、轻微光照、JPEG 压缩）。第一个是、第二个否 → 优先采集真实数据，增强只做兜底（夜间、雨雾、极端逆光）。第一个否 → <em>根本不该做这个增强</em>（垂直翻转、45° 旋转、极端色相抖动）。"),
    ])),
    ("harder", "检测增强难在哪：图变了，标注必须跟着一起变", "".join([
        P("分类增强的标签变换 <code>g_T</code> 是<strong>恒等映射</strong>——不管你怎么翻转裁剪调色，标签还是那个整数。这一点让分类增强几乎不可能写错：图看起来不对，你一眼就发现了。"),
        P("检测不是这样。检测的 <code>g_T</code> 是一个<strong>真正的函数</strong>：它要把每个框做同样的几何变换，处理越界，决定哪些目标该丢弃，还要在多目标之间保持一致。<strong>而它写错的时候，图看起来完全正常。</strong>"),
        ASCII("""分类增强：只有一条轨道
    image ──T──> image'
    label ───────> label            （g_T = 恒等，不可能写错）

检测增强：两条轨道必须严格同步
    image  ──────T──────>  image'
      │                       │
      └── 必须是同一个 T ──────┘
    boxes  ─────g_T─────>  boxes'   ← **这里是所有 bug 的产地**
             │
             ├─ 几何：四角变换 -> 外接框（模块 01）
             ├─ 越界：裁剪 / 丢弃 / 标记为 ignore（模块 01）
             ├─ 尺度：变换后过小的框怎么办（模块 01，对小目标致命）
             └─ 语义：类别是否需要跟着改（左转 <-> 右转，模块 01）

    ⚠️ 失败的特征：图是对的、框是错的、loss 照样下降、
       验证集上也「正常」（因为验证集不做增强）——
       **只有在训练集与验证集的 AP 差距上留下一点点异常。**""")
        ,
        TABLE(["维度", "分类增强", "检测增强"], [
            ["标签变换 <code>g_T</code>", "恒等", "<strong>框的仿射作用 + 越界规则 + 丢弃规则 + 类别映射</strong>"],
            ["越界", "不存在这个概念", "目标可能被切掉一部分、甚至完全切出画面 → <strong>要判「留、裁、丢、还是标为 ignore」</strong>"],
            ["多目标交互", "一图一标签", "一图多目标；<strong>规则必须对每个目标独立成立</strong>——一张图里只要有一个目标不能翻，整张图就不能翻"],
            ["尺度的语义", "缩放几乎无害", "缩放<strong>直接改变「小目标」的构成</strong>与正样本数量；缩小后的框可能被 min_size 规则整批删掉"],
            ["遮挡类增强", "Cutout 只是遮住部分特征", "遮住整个目标 → <strong>该框变成纯噪声监督</strong>（要求模型从纯背景里预测一个框）"],
            ["混合类增强", "MixUp 混合标签即可", "框不能「混合」，只能拼接（Mosaic）或粘贴（Copy-Paste）——<strong>这是两个完全不同的算子族</strong>（模块 03）"],
            ["错误的可见性", "肉眼可见", "<strong>肉眼几乎不可见</strong>：图正常、框偏了，需要专门的可视化或断言才能发现"],
        ]),
        DUAL(
            "「错误的可见性」这一行值得展开，因为它决定了本课的工程方法。<strong>检测增强的 bug 不会让程序崩溃，也不会让 loss 变成 NaN，它只会让指标低一点点</strong>——低到你以为是「模型不够好」而不是「数据管线有 bug」。真实项目里，一个「旋转后框没有正确膨胀」的实现错误可以在代码库里活好几个月，直到某个人偶然把增强后的图和框画出来看了一眼。",
            "所以本课的纪律是：<strong>每一个增强算子都必须附带一个可执行的正确性断言，而不是靠可视化抽查</strong>。断言的形式在 notebook 里会反复出现——用目标的<em>掩码/轮廓点</em>算出「真实的紧框」，再和算子输出的框比 IoU。<em>能写出这个断言，说明你真的理解了这个算子的 <code>g_T</code>；写不出来，说明你只是抄了一段代码。</em>这条纪律与 C60 的「训练-部署逐层对拍」是同一个思路：<strong>用可验证的断言代替「我看着挺对的」</strong>。",
        ),
        CALLOUT("danger", "<p>一个在 TSR 项目里真实发生过、且代价极高的错误：<strong>随机裁剪后，对「被裁到画面外超过一半」的目标直接 <code>drop</code>（从标注里删掉），但图像里那半个标志还清清楚楚地留着</strong>。结果是模型被明确训练成「看到半个标志 → 这里没有东西」。<em>而 TSR 里目标被画面边缘截断是极常见的情况</em>（标志从画面上方进入视野的整个过程都是这样）。症状：远处标志的首次检出距离明显偏近，且 recall 在图像边缘区域系统性偏低。<strong>正确做法是标为 <code>ignore</code> 区域（既不算正样本也不算负样本），而不是删除。</strong>模块 01 会把这三种处理方式（keep / ignore / drop）的边界讲清楚并实现出来。</p>", "被丢弃但仍可见的目标 = 假负样本监督"),
    ])),
    ("map", "课程地图：五个模块与它们各自解决的问题", "".join([
        ASCII("""起点：你有一个能跑的检测训练流程，想知道增强该怎么配、以及为什么。

  模块 01  几何增强与标注同步
     │      仿射矩阵 / 四角法与外接框 / **旋转导致的框膨胀** /
     │      越界的 keep-ignore-drop 三分法 / **翻转白名单（TSR 必知）** /
     ▼      letterbox 正逆变换（直接连到 C60 的部署一致性）
  模块 02  光度增强与域鲁棒性
     │      HSV / gamma / 噪声 / 模糊 / JPEG /
     │      **颜色即语义**：红=禁令、蓝=指示、黄=警告，色相抖动的红线 /
     ▼      大气散射雾化模型 / 运动模糊核 / 卷帘快门 / 低光合成
  模块 03  混合类增强：Mosaic / MixUp / CutMix / Copy-Paste
     │      Mosaic 的三个作用与 **close-mosaic 为什么是标配** /
     │      **Copy-Paste 是长尾最直接的解法**（TSR 价值极高）/
     ▼      粘贴的合法性约束：尺度符合透视、位置合理、边缘融合
  模块 04  增强流水线工程
     │      算子顺序与概率组合（实际触发率远低于直觉）/
     │      **CPU 是训练吞吐的真正瓶颈** / DataLoader worker 的 RNG 陷阱 /
     ▼      验证集只能做确定性变换 / TTA 与 WBF / 配置的版本管理
  模块 05  增强的消融与验证
            **分场景验证**（整体 +0.3 可能掩盖「雨天 +3、晴天 -1」）/
            种子方差与显著性 / 增强强度 × 训练时长的交互 /
            **为 TSR 按失效模式反推一套增强配方**

终点：给定一个检测任务和它的失效模式清单，你能设计一套增强配方，
      写出每个算子的理由，并给出证明它有用的验证方案。""")
        ,
        TABLE(["模块", "核心机制", "notebook 里从零实现什么"], [
            ["01 几何", "仿射矩阵、四角法外接框、越界规则、letterbox", "<strong>完整的 bbox 变换器</strong> + 旋转膨胀量化 + <strong>letterbox 逆变换</strong> + <strong>翻转安全性检查器</strong>"],
            ["02 光度", "HSV/gamma/噪声/模糊、大气散射物理模型", "<strong>色相偏移的语义破坏量化</strong> + 雾化模型 + 运动模糊核 + 卷帘快门畸变"],
            ["03 混合", "Mosaic 拼接、Copy-Paste 实例粘贴", "<strong>Mosaic（含框裁剪与丢弃）</strong> + <strong>透视约束下的 Copy-Paste</strong> + 长尾样本数提升量化"],
            ["04 流水线", "算子组合、并发、可复现、TTA 融合", "<strong>流水线与实际触发率统计</strong> + <strong>worker RNG 的正确/错误策略</strong> + <strong>WBF</strong>"],
            ["05 消融", "配对显著性检验、分场景切片", "<strong>bootstrap + 配对 t 检验</strong> + 分场景对比 + <strong>TSR 增强配方生成器</strong>"],
        ]),
        CALLOUT("warn", "与相邻课程的分界要说清楚，避免重复：<strong>C55 讲 TSR 的领域知识与失效模式（本课的「需求来源」）；C57 讲小目标的架构与损失解法（本课只讲增强这一条路）；C58 讲难例挖掘与长尾数据闭环（增强解决不了的部分靠它）；C60 讲训练-部署一致性（本课模块 01 的 letterbox 逆变换是它的入口）；C61 讲实验设计与显著性（本课模块 05 是它在增强场景的特化）</strong>。<em>本课只回答一个问题：给定一堆图和标注，在把它们喂进网络之前应该做什么变换、为什么、以及怎么证明有用。</em>"),
    ])),
    ("env", "环境、运行方式与本课的纪律", "".join([
        P("本课全程 <strong>纯 numpy + 标准库、CPU 可跑、不联网</strong>。不需要 OpenCV、albumentations、PyTorch 或任何数据集下载。所有 notebook 在 CPU 上实跑验证、<code>assert</code> 零失败。"),
        CODE("""pip install -r requirements.txt      # numpy / matplotlib / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        TABLE(["你在真实项目里会用", "本课怎么处理"], [
            ["OpenCV <code>warpAffine</code> / <code>resize</code>", "用 numpy 手写<strong>齐次仿射矩阵与最近邻重采样</strong>——重点在坐标语义，不在插值质量"],
            ["albumentations 的 <code>BboxParams</code>", "手写 <strong>bbox 的四种表示互转 + 越界三分法（keep / ignore / drop）</strong>，把库里那些参数的真实含义拆开"],
            ["真实图像数据集（TT100K 等）", "用 <code>np.random</code> 按<strong>物理合理的规则</strong>合成场景（圆形/三角形标志、长尾类别分布、符合透视的尺寸），并说明合成规则"],
            ["YOLO 的 <code>letterbox()</code>", "手写正变换 + <strong>逆变换</strong>，并复现三种常见的逆变换 bug，量化它们造成的像素偏移"],
            ["mmdet 的 <code>gt_bboxes_ignore</code>", "手写 ignore 区域的生成规则，量化「误删可见目标」对召回的伤害"],
        ]),
        P("三条贯穿全课的纪律，与前面的三个判据一一对应："),
        UL([
            "<strong>每个算子都要能写出 <code>g_T</code></strong>。如果你说不清「这个变换对标注做了什么」，就不要把它放进流水线。<em>说不清，通常意味着它对某些类别是错的。</em>",
            "<strong>每个算子都要有可执行的正确性断言</strong>。断言的标准形式：用目标的轮廓点算出「真实紧框」，与算子输出比 IoU。<em>可视化抽查发现不了系统性偏移，断言可以。</em>",
            "<strong>每个增强都要说清它对应部署分布里的什么现象</strong>。说不出来的，八成属于「看起来很酷但没用」那一类，而它还在吃你的 CPU 预算。",
        ]),
        CALLOUT("intuition", "最后提醒一件事，它会让你读这门课时省很多力气：<strong>本课几乎所有「坑」的根源都是同一件事——增强作用在图像上，而标注是另一个对象</strong>。几何变换要同步（模块 01）、颜色变换会破坏「颜色即语义」（模块 02）、拼接与粘贴会创造出标注体系里不存在的构图（模块 03）、并发执行会让随机性失控（模块 04）、而这一切的效果又只能通过分场景切片才看得见（模块 05）。<em>抓住「图像与标注是两个必须同步的对象」这条线，五个模块就串成一条了。</em>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("检测增强是一个「工程上极其成熟、理论上仍很粗糙」的领域。下面几条是目前真正开放的问题，也是面试里聊到深处会碰到的地方。"),
        UL([
            "<strong>增强策略的自动搜索：成本与可迁移性</strong>。AutoAugment 用强化学习搜出的策略在 ImageNet 上很强，但搜索成本以数千 GPU 小时计；RandAugment 证明「只用两个超参（算子数 N、强度 M）随机采样」几乎能达到同等效果——<em>这个结果本身就说明「搜出来的策略」里大部分结构是冗余的</em>。检测版的 <em>Learning Data Augmentation Strategies for Object Detection</em>（Zoph et al., 2020）显示搜到的策略跨数据集迁移性尚可，但<strong>跨任务（分类→检测）几乎不迁移</strong>。为什么？目前没有令人满意的解释。",
            "<strong>群论视角覆盖不了现代增强</strong>。Chen–Dobriban–Lee 的方差缩减理论要求 <code>𝒯</code> 是一个群（有单位元、逆元、封闭）。翻转、旋转、平移都满足；但 <strong>Mosaic、CutMix、Copy-Paste 都不是群作用</strong>——它们把多个样本组合成一个新样本，根本不在这个框架里。<em>而恰恰是这几个算子贡献了检测上最大的收益。</em>「为什么混合类增强有效」目前只有直觉解释（增大批内多样性、制造更多小目标、丰富上下文），缺少理论。",
            "<strong>生成式增强的可控性与标注问题</strong>。用扩散模型合成罕见场景（夜间施工区、被树叶遮挡的限速牌）在概念上极有吸引力，但有两个硬问题：① <em>生成图与真实相机图之间存在系统性域差</em>（ISP 特性、噪声结构、镜头畸变），模型可能学到「生成图的指纹」而不是场景内容；② <strong>标注从哪来</strong>——如果标注也是生成的，就有循环论证的风险。目前工业界的主流用法是<em>只用生成图做「难负样本」</em>（例如生成各种广告牌来压误检），而不是生成正样本。",
            "<strong>增强与大规模预训练的替代关系</strong>。一个反复被观察到但缺少定论的现象：<em>预训练规模越大，增强的边际收益越小</em>。直觉解释是预训练已经把不变性学进去了。但这在检测的<strong>长尾类别</strong>上似乎不成立——copy-paste 对稀有类的提升在有无预训练时都很显著。「哪些增强会被预训练吸收、哪些不会」是一个有实用价值的开放问题。",
            "<strong>检测增强缺少统一的评测协议</strong>。同一个增强在不同检测器、不同训练时长、不同数据规模下经常给出<em>相反的结论</em>（模块 05 会量化这一点：强增强在 12 epoch 下掉点、在 300 epoch 下涨点）。目前论文里报的增强收益大多不可比。<strong>这也是为什么面试里问「你怎么证明这个增强有用」比问「你用了哪些增强」更能区分水平。</strong>",
            "<strong>语义敏感变换的自动发现</strong>。「哪些类别不能水平翻转」目前完全靠人工整理白名单（模块 01 会给出 TSR 的完整方法）。能否<em>从数据里自动学出来</em>——比如通过「翻转前后模型置信度的类别间转移」来识别镜像对——是一个尚无成熟方案、但工程价值明确的方向：<strong>标志类别有成百上千种，人工维护白名单本身就是长期负担。</strong>",
        ]),
        CALLOUT("paper", "必读：<em>AutoAugment: Learning Augmentation Strategies from Data</em>（Cubuk et al., CVPR 2019，搜索式增强的起点）★；<em>RandAugment: Practical Automated Data Augmentation with a Reduced Search Space</em>（Cubuk et al., 2020，证明搜索大多是冗余的）★；<em>Learning Data Augmentation Strategies for Object Detection</em>（Zoph et al., ECCV 2020，检测专用策略搜索，含 bbox 级算子）★；<em>Bag of Freebies for Training Object Detection Neural Networks</em>（Zhang et al., 2019，把「不增加推理成本的技巧」系统化）；<em>YOLOv4: Optimal Speed and Accuracy of Object Detection</em>（Bochkovskiy et al., 2020，Mosaic 的出处与 BoF/BoS 分类法）★；<em>Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation</em>（Ghiasi et al., CVPR 2021，长尾最直接的解法）★；<em>A Group-Theoretic Framework for Data Augmentation</em>（Chen, Dobriban &amp; Lee, JMLR 2020，增强为何有效的理论视角）；<em>Albumentations: Fast and Flexible Image Augmentations</em>（Buslaev et al., 2020，工业界事实标准库的设计文档）；<em>Traffic-Sign Detection and Classification in the Wild</em>（Zhu et al., CVPR 2016，TT100K 数据集，本课合成数据的分布依据）★。相邻课程：C55（TSR 领域与失效模式）、C57（小目标）、C58（长尾与数据闭环）、C60（训练-部署一致性）、C61（实验设计与显著性）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 00 · 检测增强的地基（不变性先验 / 三判据 / 标注同步 / 正确性断言）

本课全程 **纯 numpy + 标准库、CPU、不联网**。不需要 OpenCV / albumentations / PyTorch。

**核心命题**：数据增强不是「造更多数据」，而是**往模型里注入一条「这些变化不改变标签」的先验**。
既然是先验，它就**可能是错的**——而错误的先验比缺少数据更有害，因为模型会稳定地、自信地学会它。

这个 notebook 你会亲手实现：
1. **bbox 的四种表示与互转**（xyxy / cxcywh / xywh / 归一化），以及 IoU
2. **检测增强的通用框架**：每个算子必须同时给出 `apply_image` 与 `apply_boxes`
3. **「忘记变换标注」的量化后果**——图看着完全正常，框的 IoU 已经是 0
4. **三判据自检清单**：保标签语义 / 贴近部署分布 / 不制造训练-推理鸿沟
5. **可执行的正确性断言**：用目标掩码算出「真实紧框」，与算子输出对拍

> 心智模型：**图像和标注是两个必须同步变换的对象。本课所有的坑都从这一句话长出来。**"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math, json, itertools, collections
print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
import numpy as np
print('numpy', np.__version__)
for name in ['cv2', 'albumentations', 'torch']:
    try:
        m = __import__(name)
        print(f'  {name:<16s} {getattr(m, "__version__", "?")}  (有更好，但本课不用)')
    except ImportError:
        print(f'  {name:<16s} 未安装 -> 走 numpy 手写路径（本课的默认路径）')

rng = np.random.default_rng(0)
print('\\n环境就绪 ✅  —— 本课不需要 OpenCV / albumentations / GPU / 联网')"""),
    md("""## 2 · bbox 的四种表示与互转

真实项目里 bbox 至少有四种写法，它们互相之间的转换是**数据管线 bug 的第一大来源**
（C61 模块 03 会把「坐标格式弄反」列为「mAP 恒为 0」的三大成因之一）。

| 表示 | 含义 | 谁在用 |
|---|---|---|
| `xyxy` | `(x1, y1, x2, y2)` 左上/右下 | torchvision、mmdet 内部、大多数评测代码 |
| `xywh` | `(x1, y1, w, h)` 左上 + 宽高 | **COCO 标注文件** |
| `cxcywh` | `(cx, cy, w, h)` 中心 + 宽高 | DETR 家族、YOLO 的回归目标 |
| `cxcywh_norm` | 上面除以 `(W, H)` 归一化到 `[0,1]` | **YOLO 的 `.txt` 标注文件** |

约定：本课全程用 `xyxy`，且 **`x2/y2` 是开区间**（`x2 - x1` 就是宽度，不需要 `+1`）。
这个约定必须写在文档里——「要不要 +1」在 NMS 与 IoU 实现里会造成微妙差异（C60 模块 04）。"""),
    code("""def xyxy2cxcywh(b):
    b = np.asarray(b, float).reshape(-1, 4)
    return np.stack([(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2,
                     b[:, 2] - b[:, 0],       b[:, 3] - b[:, 1]], axis=1)

def cxcywh2xyxy(b):
    b = np.asarray(b, float).reshape(-1, 4)
    return np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2,
                     b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], axis=1)

def xyxy2xywh(b):
    b = np.asarray(b, float).reshape(-1, 4)
    return np.stack([b[:, 0], b[:, 1], b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]], axis=1)

def normalize(b, W, H):
    b = np.asarray(b, float).reshape(-1, 4).copy()
    b[:, [0, 2]] /= W; b[:, [1, 3]] /= H
    return b

def box_area(b):
    b = np.asarray(b, float).reshape(-1, 4)
    return np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)

def box_iou(a, b):
    '''a:(N,4) b:(M,4) -> (N,M)'''
    a = np.asarray(a, float).reshape(-1, 4); b = np.asarray(b, float).reshape(-1, 4)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[..., 0] * wh[..., 1]
    union = box_area(a)[:, None] + box_area(b)[None, :] - inter
    return inter / np.maximum(union, 1e-12)

boxes = np.array([[13., 11., 28., 26.], [42., 36., 51., 45.]])
print('xyxy       ', boxes.tolist())
print('cxcywh     ', xyxy2cxcywh(boxes).tolist())
print('xywh (COCO)', xyxy2xywh(boxes).tolist())
print('归一化 cxcywh (YOLO txt)', np.round(normalize(xyxy2cxcywh(boxes), 64, 64), 4).tolist())
print('面积       ', box_area(boxes).tolist())

assert np.allclose(cxcywh2xyxy(xyxy2cxcywh(boxes)), boxes), '往返必须无损'
assert np.allclose(np.diag(box_iou(boxes, boxes)), 1.0)
assert box_iou(boxes[:1], boxes[1:])[0, 0] == 0.0, '两个不相交的框 IoU=0'
print('\\n✅ 四种表示互转与 IoU 就位（全程 xyxy，x2/y2 为开区间）')"""),
    md("""## 3 · 检测增强的通用框架：两条轨道必须同步

分类增强的标签变换 `g_T` 是**恒等映射**，不可能写错。
检测增强的 `g_T` 是一个**真正的函数**——而它写错的时候，**图看起来完全正常**。

下面先造一个可验证的合成场景：一张 64×64 的灰度图，上面有两个**圆形交通标志**
（中国的禁令标志就是圆形）。因为我们知道每个标志的解析形状，
就可以随时从图像里算出「**真实的紧框**」，用它来给任何算子的 `apply_boxes` 打分。"""),
    code("""def make_scene(H=64, W=64, signs=((20, 18, 7, 1), (46, 40, 4, 2))):
    '''signs: (cx, cy, r, cls)，每个是一个圆形标志。
       返回 img(uint8 灰度), boxes(xyxy, x2/y2 开区间), labels, 以及每类的像素值。'''
    img = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    boxes, labels, vals = [], [], []
    for cx, cy, r, cls in signs:
        val = 100 + 40 * cls                     # 每个标志一个唯一像素值，方便反查掩码
        img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = val
        boxes.append([cx - r, cy - r, cx + r + 1, cy + r + 1])   # 圆占 [cx-r, cx+r] 共 2r+1 列
        labels.append(cls); vals.append(val)
    return img, np.array(boxes, float), np.array(labels, int), vals

def mask_bbox(img, val):
    '''从图像里反查某个目标的**真实紧框** —— 这是我们的 ground truth 检查器。'''
    ys, xs = np.nonzero(img == val)
    assert len(xs) > 0, f'像素值 {val} 在图里找不到'
    return np.array([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1], float)

img, boxes, labels, vals = make_scene()
print('图像', img.shape, '| 目标数', len(boxes), '| 类别', labels.tolist())
for b, v in zip(boxes, vals):
    tb = mask_bbox(img, v)
    print(f'  标注框 {b.tolist()}   掩码紧框 {tb.tolist()}   IoU={box_iou([b],[tb])[0,0]:.4f}')

assert all(np.allclose(mask_bbox(img, v), b) for b, v in zip(boxes, vals)), '初始标注必须与掩码完全一致'
print('\\n✅ 合成场景就位：标注与掩码逐像素一致，可以用来给任何增强算子打分。')"""),
    code("""# ── 通用框架：每个算子必须同时给出 apply_image 与 apply_boxes ──
class Aug:
    '''检测增强算子的最小接口约定。**两条轨道，同一个 T。**'''
    name = 'identity'
    def apply_image(self, img):            return img
    def apply_boxes(self, boxes, shape):   return boxes
    def apply_labels(self, labels):        return labels          # 少数算子需要改类别（模块 01）
    def __call__(self, img, boxes, labels):
        H, W = img.shape[:2]
        return (self.apply_image(img),
                self.apply_boxes(boxes, (H, W)),
                self.apply_labels(labels))

class HFlip(Aug):
    name = 'hflip'
    def apply_image(self, img):  return img[:, ::-1].copy()
    def apply_boxes(self, boxes, shape):
        H, W = shape
        b = np.asarray(boxes, float).copy()
        b[:, [0, 2]] = np.stack([W - boxes[:, 2], W - boxes[:, 0]], axis=1)   # 注意 x1/x2 会互换
        return b

class Translate(Aug):
    name = 'translate'
    def __init__(self, dx, dy): self.dx, self.dy = int(dx), int(dy)
    def apply_image(self, img):
        H, W = img.shape; dx, dy = self.dx, self.dy
        out = np.zeros_like(img)
        xs0, xs1 = max(0, dx), min(W, W + dx)
        ys0, ys1 = max(0, dy), min(H, H + dy)
        out[ys0:ys1, xs0:xs1] = img[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
        return out
    def apply_boxes(self, boxes, shape):
        b = np.asarray(boxes, float).copy()
        b[:, [0, 2]] += self.dx; b[:, [1, 3]] += self.dy
        return b

def verify(op, img, boxes, vals, tol=0.99):
    '''**可执行的正确性断言**：算子输出的框 vs 掩码算出的真实紧框。'''
    img2, boxes2, _ = op(img, boxes, np.zeros(len(boxes), int))
    ious = [box_iou([b], [mask_bbox(img2, v)])[0, 0] for b, v in zip(boxes2, vals)]
    return img2, boxes2, np.array(ious), all(i >= tol for i in ious)

for op in [HFlip(), Translate(5, -3)]:
    _, b2, ious, ok = verify(op, img, boxes, vals)
    print(f'{op.name:<10s} 变换后框 {np.round(b2,1).tolist()}  与掩码紧框 IoU={np.round(ious,4).tolist()}  {"✅" if ok else "❌"}')
    assert ok, op.name
print('\\n✅ 两条轨道同步：断言用「掩码算出的真实紧框」验证，而不是靠肉眼看图。')"""),
    code("""# ── 反面教材：图变了、标注没变。**loss 照降，图看着完全正常。** ──
class BuggyHFlip(HFlip):
    name = 'hflip(忘记变框)'
    def apply_boxes(self, boxes, shape): return np.asarray(boxes, float).copy()

class BuggyTranslate(Translate):
    name = 'translate(忘记变框)'
    def apply_boxes(self, boxes, shape): return np.asarray(boxes, float).copy()

print(f"{'算子':<24s} {'与真实紧框的 IoU':>22s}   后果")
rows = []
for op, why in [(BuggyHFlip(), '整个目标跑到了对侧'),
                (BuggyTranslate(5, -3), '只偏了 5 像素，图几乎看不出区别')]:
    _, _, ious, ok = verify(op, img, boxes, vals)
    rows.append((op.name, ious))
    print(f'{op.name:<24s} {str(np.round(ious,3).tolist()):>22s}   {why}')

iou_flip = rows[0][1]; iou_tr = rows[1][1]
assert iou_flip.max() == 0.0, '翻转后不改框 -> 框与目标完全不重叠'
assert 0.3 < iou_tr[0] < 0.45, f'15px 的框偏 5px，IoU 应在 0.36 附近，实得 {iou_tr[0]:.3f}'
print(f'\\n⚠️  第二行是真正危险的那个：图肉眼看不出区别，但')
print(f'    15×15 的框偏 5 px -> IoU {iou_tr[0]:.2f}；**9×9 的框偏同样的 5 px -> IoU {iou_tr[1]:.2f}**。')
print('    大目标偏 5 px 还能勉强算对，**小目标偏 5 px 标签就基本作废** —— 这是 TSR 的常态：')
print('    60 米外的限速牌在 1080p 上只有十几个像素（C57 模块 05 会做完整的物理推导）。')
print('✅ 结论：检测增强的 bug 不会崩溃、不会 NaN、不会让 loss 异常，')
print('   它只让指标低一点点 —— 低到你以为是「模型不够好」。**所以必须写断言。**')"""),
    md("""## 4 · 三判据自检清单

一个增强该不该用，按顺序检查三条，**第一条不过后两条就不用看了**：

1. **保标签语义** —— 变换后原标签还是正确答案吗？（不过 = 正确性问题，模型会稳定学错）
2. **贴近部署分布** —— 车上那台相机有可能拍到这种图吗？（不过 = 效率问题，浪费容量）
3. **不制造训练-推理鸿沟** —— 推理端会做同样的事吗？没有的话差异对齐了吗？（不过 = 交付问题）"""),
    code("""class AugSpec:
    def __init__(self, name, label_safe, deploy_realistic, gap_free, note=''):
        self.name = name
        self.label_safe = label_safe            # 判据①
        self.deploy_realistic = deploy_realistic  # 判据②
        self.gap_free = gap_free                # 判据③
        self.note = note

def audit(spec):
    '''返回 (verdict, mitigation)。**按危害量级排序：① > ② > ③。**'''
    if not spec.label_safe:
        return '❌ 禁用/改造', '必须先修标签变换：类别白名单、标签互换、或改用 ignore 区域'
    if not spec.deploy_realistic:
        return '⚠️ 收益存疑', '部署分布里不存在这种图；要么砍掉，要么把幅度收到真实范围内'
    if not spec.gap_free:
        return '⚠️ 需显式对齐', '训练与推理必须用同一实现（或训练末期关闭），并写进部署对拍清单'
    return '✅ 直接用', '—'

SPECS = [
    AugSpec('水平翻转（通用 COCO 场景）',   True,  True,  True,  '左右镜像不改变「猫」的类别'),
    AugSpec('水平翻转（TSR，无白名单）',    False, True,  True,  '「向左转弯」被镜像成「向右转弯」，标签却没变'),
    AugSpec('垂直翻转',                    True,  False, True,  '车载相机不会上下颠倒；重力是极强的先验'),
    AugSpec('随机缩放 0.5–1.5×',           True,  True,  True,  '对应标志的远近 —— TSR 收益最高的几何增强'),
    AugSpec('旋转 ±10°',                   True,  True,  True,  '对应车身侧倾与相机安装误差；但外接框会膨胀'),
    AugSpec('旋转 ±45°',                   True,  False, True,  '真实驾驶中不存在；且正方形框面积膨胀 100%'),
    AugSpec('letterbox 缩放+填充',         True,  True,  False, '训练与推理端实现必须逐像素一致'),
    AugSpec('HSV 色相抖动 ±30°',           False, True,  True,  '红色禁令牌被抖成蓝色 —— 颜色即语义'),
    AugSpec('Mosaic 四图拼接',             True,  False, False, '拼接图在真实分布里不存在 -> 末期必须 close-mosaic'),
    AugSpec('Copy-Paste 稀有类',           True,  True,  True,  '需约束尺度与位置，否则贴出「天上的标志」'),
    AugSpec('测试时增强 TTA',              True,  True,  False, '训练端没有；车端多跑几次的延迟不可接受'),
]

print(f"{'增强算子':<26s} {'①语义':>6s} {'②分布':>6s} {'③无鸿沟':>7s}  {'结论':<12s} 说明")
n_ok = n_ban = 0
for s in SPECS:
    v, mit = audit(s)
    n_ok += (v.startswith('✅')); n_ban += (v.startswith('❌'))
    tick = lambda x: ' ✓' if x else ' ✗'
    print(f'{s.name:<26s} {tick(s.label_safe):>6s} {tick(s.deploy_realistic):>6s} '
          f'{tick(s.gap_free):>7s}  {v:<12s} {s.note}')

assert audit(SPECS[1])[0].startswith('❌'), 'TSR 无白名单翻转必须被禁'
assert audit(SPECS[7])[0].startswith('❌'), 'HSV 大幅色相抖动破坏「颜色即语义」'
assert n_ok == 4 and n_ban == 2, (n_ok, n_ban)
print(f'\\n11 个算子里：{n_ok} 个可直接用，{n_ban} 个必须先改造，其余 {11-n_ok-n_ban} 个需要缓解措施。')
print('⚠️  注意「水平翻转」在通用场景 ✅、在 TSR ❌ —— **同一个算子，判据结论相反。**')
print('    这就是为什么「照抄一份 COCO 的增强配置」在 TSR 上是错的。')"""),
    code("""# ── 缓解措施清单：非 ✅ 的算子分别要做什么 ──
print('需要处理的算子与对应动作：\\n')
for s in SPECS:
    v, mit = audit(s)
    if not v.startswith('✅'):
        print(f'  {v}  {s.name}')
        print(f'        -> {mit}')
        print()

mitigations = {s.name: audit(s)[1] for s in SPECS if not audit(s)[0].startswith('✅')}
assert len(mitigations) == 7
assert '白名单' in mitigations['水平翻转（TSR，无白名单）']
assert '部署分布' in mitigations['Mosaic 四图拼接'], 'Mosaic 先卡在判据②（拼接图不是真实分布）'
print('✅ 三判据清单的价值：把「这个增强好像不太对」变成「它违反了第 N 条，对应动作是 X」。')
print('   面试里被问「你怎么选增强」，这张表就是一个可以直接讲的框架。')"""),
    md("""## 5 · 判据①的可执行形式：标签语义是否被保住

前面 `verify()` 检查的是**几何**同步（框还紧贴目标吗）。
但判据① 还有**语义**的一半：**类别标签是否还正确**。

几何检查通不过 → 代码 bug；语义检查通不过 → **先验错了**。后者严重得多，
因为它不会在任何自动检查里冒出来 —— 除非你像下面这样，把「类别的镜像映射」显式写出来。"""),
    code("""# TSR 的三档翻转分类（模块 01 会做成完整白名单并给出判定流程）
# 'safe'  : 外观左右镜像对称 + 语义无方向性        -> 可以翻
# 'swap'  : 语义含方向性，但标签集里存在镜像类     -> 可以翻，**但必须同时换标签**
# 'forbid': 其余                                   -> 绝对不能翻
FLIP3 = {
    'no_entry':       ('safe',   None),          # 禁止驶入：红底白横杠，左右对称
    'no_vehicles':    ('safe',   None),          # 禁止通行
    'turn_left':      ('swap',   'turn_right'),  # 向左转弯 <-> 向右转弯
    'turn_right':     ('swap',   'turn_left'),
    'speed_limit_60': ('forbid', '含数字，镜像后的字形在现实中不存在'),
    'stop':           ('forbid', '含文字 STOP/停'),
    'guide_sign':     ('forbid', '指路牌含地名文字'),
}

def flip_labels(labels):
    '''语义层面的 g_T。返回 (新标签, 是否合法)。'''
    out = []
    for c in labels:
        kind, other = FLIP3[c]
        if kind == 'forbid':
            return labels, False
        out.append(other if kind == 'swap' else c)
    return out, True

for scene in [['no_entry', 'no_vehicles'], ['turn_left', 'no_entry'],
              ['turn_left', 'speed_limit_60'], ['stop']]:
    new, ok = flip_labels(scene)
    print(f'{str(scene):<38s} -> {"可翻 " + str(new) if ok else "❌ 整张图不能翻（含 forbid 类）"}')

assert flip_labels(['turn_left'])[0] == ['turn_right'], '方向类必须换标签'
assert not flip_labels(['turn_left', 'speed_limit_60'])[1], '一张图里有一个 forbid 就整张不能翻'
assert flip_labels(['no_entry', 'no_vehicles'])[1]
print('\\n⚠️  注意第 3 行：**一张图里只要有一个目标属于 forbid，整张图就不能翻**。')
print('    因为翻转作用在图像上，而判定是逐目标的 —— 这个「与」的关系会让')
print('    TSR 里翻转的实际生效率远低于配置里写的 p_flip（模块 01 会量化）。')
print('✅ 判据① 的两半：几何同步（写断言）+ 语义映射（写白名单）。缺一不可。')"""),
    md("""## ✏️ 练习 1：bbox 工具函数

实现 `boxes_from_yolo_txt(lines, W, H)`：把 YOLO 标注文件的每行
`"cls cx cy w h"`（**归一化的 cxcywh**）解析成 `(labels, boxes_xyxy)`，
其中 `boxes_xyxy` 是**像素坐标**的 `xyxy`。

再实现 `filter_tiny(boxes, labels, min_side)`：丢掉宽或高小于 `min_side` 像素的框，
返回 `(boxes_kept, labels_kept, n_dropped)`。"""),
    code("""def boxes_from_yolo_txt(lines, W, H):
    # TODO: 每行 "cls cx cy w h"，cx/cy/w/h 已按 W,H 归一化
    #       -> 返回 (labels: np.int64 (N,), boxes: np.float64 (N,4) 像素 xyxy)
    #       空输入要返回 (shape (0,) 的 int 数组, shape (0,4) 的 float 数组)
    raise NotImplementedError

def filter_tiny(boxes, labels, min_side):
    # TODO: 保留 (w >= min_side) & (h >= min_side) 的框
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
LINES = ['0 0.5 0.5 0.25 0.25',      # 640x640 -> [240,240,400,400]
         '3 0.1 0.2 0.01 0.01',      # -> 6.4x6.4 像素的小标志
         '7 0.9 0.8 0.05 0.05']      # -> 32x32
lab, bx = boxes_from_yolo_txt(LINES, 640, 640)
assert lab.tolist() == [0, 3, 7], lab
assert np.allclose(bx[0], [240., 240., 400., 400.]), bx[0]
assert np.allclose(box_area(bx[1:2])[0], 6.4 * 6.4), box_area(bx[1:2])
l0, b0 = boxes_from_yolo_txt([], 640, 640)
assert b0.shape == (0, 4) and l0.shape == (0,), (b0.shape, l0.shape)

kb, kl, nd = filter_tiny(bx, lab, min_side=8.0)
assert nd == 1 and kl.tolist() == [0, 7], (nd, kl)
kb2, kl2, nd2 = filter_tiny(bx, lab, min_side=2.0)
assert nd2 == 0
print('原始 3 个目标，尺寸(w):', np.round(bx[:, 2] - bx[:, 0], 2).tolist())
print('min_side=8 -> 丢弃', nd, '个；min_side=2 -> 丢弃', nd2, '个')
print('⚠️  同一份标注，只因为 min_side 从 2 改成 8，就少了 1/3 的目标 ——')
print('    而被丢掉的恰恰是**最难、最有价值的远处小标志**。（模块 01 会深挖这一点）')
print('✅ 练习 1 通过')"""),
    md("""## ✏️ 练习 2：三判据审计器

实现 `audit2(label_safe, deploy_realistic, gap_free)`，返回
`(level, action)`，其中 `level ∈ {'ban', 'mitigate', 'ok'}`：

- 判据① 不过 → `('ban', '修标签变换')`
- 判据① 过、②或③ 不过 → `('mitigate', ...)`：②不过给 `'收窄幅度'`，③不过给 `'两端对齐'`；
  **两个都不过时优先报 `'收窄幅度'`**（危害更大）
- 三条都过 → `('ok', '直接用')`"""),
    code("""def audit2(label_safe, deploy_realistic, gap_free):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
assert audit2(False, True,  True)  == ('ban', '修标签变换')
assert audit2(False, False, False) == ('ban', '修标签变换'), '判据①优先级最高'
assert audit2(True,  False, True)  == ('mitigate', '收窄幅度')
assert audit2(True,  True,  False) == ('mitigate', '两端对齐')
assert audit2(True,  False, False) == ('mitigate', '收窄幅度'), '②③都不过时报②'
assert audit2(True,  True,  True)  == ('ok', '直接用')

print(f"{'算子':<26s} {'level':<10s} action")
for s in SPECS:
    lv, ac = audit2(s.label_safe, s.deploy_realistic, s.gap_free)
    print(f'{s.name:<26s} {lv:<10s} {ac}')
levels = [audit2(s.label_safe, s.deploy_realistic, s.gap_free)[0] for s in SPECS]
assert collections.Counter(levels) == {'ok': 4, 'mitigate': 5, 'ban': 2}, collections.Counter(levels)
print('\\n✅ 练习 2 通过：4 个直接可用 / 5 个需缓解 / 2 个必须先改造')"""),
    md("""## ✏️ 练习 3：写一个算子并让断言通过

实现 `class Scale(Aug)`：把图像**整数倍缩小** `k` 倍（用最近邻：`img[::k, ::k]`），
并给出正确的 `apply_boxes`。

提示：`img[::k, ::k]` 取的是原图第 `0, k, 2k, …` 行/列，
所以原坐标 `x` 映射到新坐标 `x / k`；框的 `x1,y1,x2,y2` 全部除以 `k` 即可。
断言用 `verify()`，容差放到 `0.70`（最近邻降采样必然引入亚像素误差，
**这个容差本身就是一条重要信息：降采样会让小目标的标注精度下降**）。"""),
    code("""class Scale(Aug):
    name = 'scale'
    def __init__(self, k): self.k = int(k)
    def apply_image(self, img):
        # TODO
        raise NotImplementedError
    def apply_boxes(self, boxes, shape):
        # TODO
        raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
op = Scale(2)
img2, b2, ious, ok = verify(op, img, boxes, vals, tol=0.70)
print('缩小 2 倍后图像尺寸', img2.shape, '| 框', np.round(b2, 2).tolist())
print('与掩码紧框的 IoU     ', np.round(ious, 4).tolist())
assert img2.shape == (32, 32), img2.shape
assert np.allclose(b2, boxes / 2), '框应整体除以 k'
assert ok, f'IoU 应 >= 0.70，实得 {ious}'
assert ious.min() < 0.999, '最近邻降采样必然带来亚像素误差 —— 这正是要点'

big, small = ious[0], ious[1]
print(f'\\n大标志(15px->7.5px) IoU={big:.3f} | 小标志(9px->4.5px) IoU={small:.3f}')
assert small <= big + 1e-9, '越小的目标，降采样带来的相对标注误差越大'
print('⚠️  同一次降采样，**小目标的标注精度损失更大** ——')
print('    这是 C57「标注误差的相对量级」那条的一个直接演示：')
print('    人工标注 ±1px 的误差，对 8px 的框就是 12.5% 的相对误差，标签本身就带噪。')
print('✅ 练习 3 通过')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def boxes_from_yolo_txt(lines, W, H):
    if not lines:
        return np.zeros(0, np.int64), np.zeros((0, 4), float)
    labs, cxywh = [], []
    for ln in lines:
        parts = ln.split()
        labs.append(int(parts[0]))
        cx, cy, w, h = (float(v) for v in parts[1:5])
        cxywh.append([cx * W, cy * H, w * W, h * H])
    return np.array(labs, np.int64), cxcywh2xyxy(np.array(cxywh, float))

def filter_tiny(boxes, labels, min_side):
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    w = boxes[:, 2] - boxes[:, 0]; h = boxes[:, 3] - boxes[:, 1]
    keep = (w >= min_side) & (h >= min_side)
    return boxes[keep], np.asarray(labels)[keep], int((~keep).sum())"""),
    code("""# 练习 2 参考答案
def audit2(label_safe, deploy_realistic, gap_free):
    if not label_safe:
        return 'ban', '修标签变换'
    if not deploy_realistic:
        return 'mitigate', '收窄幅度'
    if not gap_free:
        return 'mitigate', '两端对齐'
    return 'ok', '直接用'"""),
    code("""# 练习 3 参考答案
class Scale(Aug):
    name = 'scale'
    def __init__(self, k): self.k = int(k)
    def apply_image(self, img):
        return img[::self.k, ::self.k].copy()
    def apply_boxes(self, boxes, shape):
        return np.asarray(boxes, float) / self.k"""),
    md("""---
## 🧪 真实工程胶囊：检测增强算子的接口约定与审计表

下面这段可以原样复制进你自己的项目（把 numpy 换成 OpenCV / albumentations 即可）。
它的价值不在代码，在于**把「这个增强对标注做了什么」变成必填字段**。"""),
    code("""RECIPE = r'''
# ============================================================
# 检测增强算子的接口约定（放进 project/augment/base.py）
# ============================================================
class DetAug:
    # 任何检测增强算子都必须实现下面的方法，且图像与标注**必须成对**变换。
    # 铁律：
    #   1. 改了图像几何       -> 必须实现 apply_boxes
    #   2. 改了图像语义(镜像/颜色) -> 必须实现 apply_labels 或声明类别白名单
    #   3. 可能让目标越界     -> 必须声明 OOB_POLICY in {keep, ignore, drop}

    # ---- 三判据（提交 PR 时必须填，reviewer 按此审）----
    LABEL_SAFE       = None       # 判据①：变换后原标签仍正确？(False 则必须写白名单/标签映射)
    DEPLOY_REALISTIC = None       # 判据②：车载相机可能拍到这种图？
    GAP_FREE         = None       # 判据③：推理端也做同样的事？否则怎么对齐？
    OOB_POLICY       = 'ignore'   # 越界目标：keep / ignore / drop
    NOTE             = ''         # 对应部署分布里的什么现象

    def apply_image(self, img):           raise NotImplementedError
    def apply_boxes(self, boxes, shape):  return boxes
    def apply_labels(self, labels):       return labels

# ============================================================
# 单元测试模板：**每个几何算子都必须有这个测试**
# 用目标掩码算出的「真实紧框」验证 apply_boxes —— 不要靠可视化抽查。
# ============================================================
def test_geometry_sync(op, img, boxes, masks, tol=0.95):
    img2   = op.apply_image(img)
    boxes2 = op.apply_boxes(boxes, img.shape[:2])
    for b, m in zip(boxes2, masks):
        m2 = op.apply_image(m.astype(img.dtype))
        ys, xs = m2.nonzero()
        if len(xs) == 0:            # 目标被完全变换出画面：按 OOB_POLICY 处理，不算失败
            continue
        tight = [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]
        assert iou(b, tight) >= tol, 'apply_boxes 与 apply_image 不同步: ' + op.__class__.__name__

# ============================================================
# 增强配置的审计表（放进 configs/augment_audit.md，随配置一起 review）
# ============================================================
# | 算子 | ①语义 | ②分布 | ③无鸿沟 | 越界策略 | 缓解措施 | 对应的部署现象 |
# |------|-------|--------|---------|----------|----------|----------------|
# | RandomScale(0.5,1.5) | Y | Y | Y | ignore | -            | 标志的远近      |
# | RandomRotate(+-10)   | Y | Y | Y | ignore | 框膨胀已量化 | 车身侧倾/装配误差 |
# | HFlip                | N | Y | Y | -      | **类别白名单+标签互换** | (TSR 中几乎无效) |
# | Letterbox(640,114)   | Y | Y | N | keep   | **与 C++ 端逐像素对拍** | 输入尺寸归一 |
# | Mosaic               | Y | N | N | drop   | **close_mosaic=10 epoch** | (无对应现象) |
'''
print(RECIPE)
for k in ['LABEL_SAFE', 'DEPLOY_REALISTIC', 'GAP_FREE', 'OOB_POLICY',
          'test_geometry_sync', 'close_mosaic', '类别白名单']:
    assert k in RECIPE, k
print('✅ 胶囊覆盖：接口约定 / 三判据必填字段 / 越界策略 / 几何同步单元测试 / 配置审计表')"""),
    md("""### 小结

- **增强 = 往模型里注入「这些变化不改变标签」的先验**，不是「造更多数据」。
  既然是先验就**可能是错的**，而错误的先验比缺少数据更有害——模型会稳定、自信地学会它。
- **三个判据，按危害排序**：① 保标签语义（正确性）→ ② 贴近部署分布（效率）→
  ③ 不制造训练-推理鸿沟（交付）。**第一条不过，后两条不用看。**
- **增强 / 正则化 / 更多数据不能互相替代**：增强注入的是任务先验，正则化注入的是复杂度偏好，
  只有真实数据带来新信息。**增强只能在已有样本的邻域里生成——没见过夜间就变不出真正的夜间。**
- **检测增强难在标签变换 `g_T` 不是恒等**：几何要同步、越界要判 keep/ignore/drop、
  尺度会改变小目标构成、类别可能需要跟着改。**而它写错的时候图看起来完全正常。**
- **所以每个算子都要有可执行的正确性断言**（掩码紧框 vs 输出框的 IoU），
  而不是靠可视化抽查——系统性偏移肉眼看不出来。
- **同一个算子在不同任务下判据结论可以相反**：水平翻转在 COCO 上 ✅、在 TSR 上 ❌。
  **照抄一份 COCO 增强配置就是这门课要防的第一个错误。**
- 一个 15×15 的框偏 5 像素，IoU 就掉到 0.36；**小目标对标注误差极其敏感**，
  而 TSR 的目标常年在十几个像素量级。

下一站：**模块 01 · 几何增强与标注同步** —— 仿射矩阵、四角法外接框、
**旋转导致的框膨胀**、越界三分法、**TSR 翻转白名单**、letterbox 正逆变换。"""),
]
