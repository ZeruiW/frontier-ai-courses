# -*- coding: utf-8 -*-
"""C54 模块 05 · DETR 工程实践：调参、诊断与选型。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–04（匈牙利匹配 / 集合损失 / object query / 家族演进）；C53（实时检测器）会让选型一节更有感觉"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 05_detr_practice.ipynb'),
    ("核心参考", "DETR / Deformable DETR / DINO 官方仓库的训练配置；detrex 与 mmdetection 的 DETR 系配置；RT-DETR 论文"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("recipe", "训练配方：为什么 backbone 的学习率是 0.1×", "".join([
        P("先把 DETR 官方配置摊开。<strong>这些数字里有一半是「不能动」的，另一半是「必须按数据集调」的，能分清楚这两半就是工程能力。</strong>"),
        TABLE(["项", "DETR 官方值", "属于哪一半", "改错了会怎样"], [
            ["优化器", "AdamW", "<strong>不能动</strong>", "换 SGD 基本训不动（Transformer 对自适应步长强依赖）"],
            ["<code>lr</code>（transformer）", "1e-4", "按 batch 调", "线性缩放规则；太大早期 loss 尖峰"],
            ["<strong><code>lr_backbone</code></strong>", "<strong>1e-5（= 0.1×）</strong>", "<strong>不能动</strong>", "<strong>用 1×：预训练特征被冲毁，AP 掉几个点</strong>"],
            ["<code>weight_decay</code>", "1e-4", "按数据量调", "小数据集要加大；<strong>但不能作用于 norm/bias/query embedding</strong>"],
            ["<code>clip_max_norm</code>", "<strong>0.1</strong>", "不能动", "去掉后早期梯度尖峰会让 loss 炸；<em>0.1 是异常小的值，是刻意的</em>"],
            ["BN", "<strong>FrozenBatchNorm2d</strong>", "不能动", "用普通 BN：单卡 batch=2 的统计量噪声极大，训练不稳"],
            ["<code>epochs / lr_drop</code>", "300 / 200（或 500/400）", "按方法调", "DINO 系用 12 或 24，配 MultiStep 在 11 步降"],
            ["dropout", "0.1（DETR）→ <strong>0.0</strong>（Deformable/DINO）", "按方法调", "<em>后续工作普遍关掉 dropout，因为收敛已不是瓶颈</em>"],
        ]),
        H3("0.1× 的第一个理由：预训练权重已经接近好解，最优步长本来就更小"),
        P("这不是玄学，可以算出来。把「一个参数块的训练」建模成带噪声的一阶迭代（噪声来自 mini-batch 采样）："),
        MATH("\\mathbb{E}\\big[\\|\\theta_T - \\theta^\\star\\|^2\\big] \\;=\\; \\underbrace{(1-\\eta)^{2T} d_0^2}_{\\text{初始偏差的衰减}} \\;+\\; \\underbrace{\\frac{\\eta\\,\\sigma^2}{2-\\eta}}_{\\text{梯度噪声的稳态项}}"),
        P("第一项要求 <strong>η 大</strong>（衰减快），第二项要求 <strong>η 小</strong>（噪声地板低）。最优 η 由二者平衡决定，<strong>而 d₀（离最优点的距离）越小，最优 η 就越小</strong>——因为没有多少偏差需要衰减，剩下的全是噪声。"),
        DUAL(
            "翻译成人话：<strong>ImageNet 预训练的 backbone 已经站在一个相当好的位置（d₀ 小），而随机初始化的 transformer 与检测头离最优解还很远（d₀ 大）</strong>。同一个学习率对前者是「用噪声把好东西震坏」，对后者是「步子还不够大」。<em>notebook 里会扫描 d₀，画出「最优步长比随预训练质量下降」的曲线。</em>",
            "严格说这个模型省略了曲率（Hessian）的差异，而真实情况里 backbone 与 transformer 的曲率尺度也不同。<strong>但结论方向是稳健的，而且它给了一条可操作的推论：预训练越好，backbone 的相对学习率就该越小。</strong><em>推论一：用 COCO 预训练的检测器去微调 TSR 时，backbone 的比例可以比 0.1 更小甚至冻结；推论二：如果 backbone 是随机初始化的（罕见但存在），0.1× 就是错的。</em>面试里能说出「0.1 不是常数，是 d₀ 的函数」，比背下这个数字强得多。",
        ),
        H3("第二、第三个理由"),
        OL([
            "<strong>早期梯度对 backbone 是纯噪声。</strong>训练开始时 decoder 的匹配在剧烈翻转（模块 04 的 φ 接近随机），传回 backbone 的梯度方向本身就是错的。<em>此时 backbone 走得越快，破坏越彻底。</em>",
            "<strong>检测数据集比预训练数据小两个数量级。</strong>COCO 118k 对 ImageNet 1.28M；TSR 自建数据集可能只有十几万张且高度相关（同一段路的连续帧）。<em>大步长 + 小数据 = 灾难性遗忘，症状是训练集 AP 正常、跨域/跨城市泛化崩掉。</em>",
        ]),
        CALLOUT("warn", "<strong>weight decay 的分组是另一个容易漏的点</strong>：AdamW 的权重衰减不应该作用于 <code>bias</code>、<code>LayerNorm/BatchNorm</code> 的仿射参数、以及 <strong>object query 的可学嵌入与 reference point 参数</strong>。<em>对 query embedding 施加 weight decay 等于持续把它往原点拉，而它编码的是空间先验——会直接削弱 query 的空间特化（模块 03 讲的现象）。</em>这类 bug 不会报错，只会让 AP 低 0.5~1 点，而且极难归因。notebook 里会实现一个正确的 param group 构造器。"),
        CALLOUT("intuition", "把学习率分组的心法提炼一句：<strong>「离最优解越近、被噪声破坏的风险越大的参数块，步长越小」</strong>。<em>这条规则在任何「预训练 + 新头」的迁移场景都成立</em>——VLM 的视觉塔、LLM 的 LoRA 基座、语音模型的前端，全部是同一个道理。面试时把它讲成一条通用原则而不是 DETR 的特例，效果完全不同。"),
    ])),
    ("small", "DETR 对小目标弱：三个根因与它们各自的解法", "".join([
        P("原版 DETR 的 AP_S 只有 20.5，而同期的 Faster R-CNN 是 22.9、Deformable DETR 是 26.4。<strong>这不是一个原因造成的，是三个——而且它们的解法完全不同。面试里能拆成三条，是这一节的全部价值。</strong>"),
        TABLE(["根因", "机制", "怎么验证是它", "解法"], [
            ["<strong>① 单尺度特征</strong>", "只用 C5（stride 32），16×16 的目标占 0.25 个格子，信息在下采样时已被抹掉", "把 GT 按像素尺寸分桶看 AP，&lt;32px 桶塌陷", "<strong>多尺度</strong>（P3–P6，TSR 还要评估 P2）"],
            ["<strong>② query 数量固定且偏少</strong>", "N=100 对密集小目标不够；且 N 固定时，小目标多的图会被挤掉", "统计单图 GT 数分布与前景 query 占比", "<strong>加大 N</strong>（Deformable 300 / DINO 900）"],
            ["<strong>③ 匹配代价对小框近似平局</strong>", "小 GT 与绝大多数 query 的 IoU=0，GIoU 在不相交区几乎不变化 → 代价由噪声的分类项决定 → 匹配随机翻转", "<strong>按 GT 尺寸分别统计匹配翻转率 φ</strong>", "两阶段/查询选择给参考点；DN 绕开匹配"],
        ]),
        H3("根因 ③ 值得展开，因为它最反直觉"),
        P("很多人以为「小目标的匹配代价变化更剧烈（IoU 掉得快），所以匹配应该更稳」。<strong>恰恰相反。</strong>"),
        MATH("\\mathcal{C}(\\hat{y}_i, y_j) = -\\lambda_{\\text{cls}}\\,\\hat{p}_i(c_j) \\;+\\; \\lambda_{L1}\\,\\|\\hat{b}_i - b_j\\|_1 \\;+\\; \\lambda_{\\text{giou}}\\,\\big(1 - \\text{GIoU}(\\hat{b}_i, b_j)\\big)"),
        UL([
            "<strong>IoU 对绝对位移的敏感性与框尺寸成反比。</strong>同样沿对角线平移 2 像素：<strong>8×8 的框 IoU 从 1.0 掉到 0.39，64×64 的框还有 0.88，160×160 的框还有 0.95</strong>。而模型的预测误差与人工标注的抖动都是<em>绝对像素</em>量级的（标注 ±2 px 是常态）。",
            "于是对一个 8~16 px 的 GT，<strong>「谁该认领它」这个决策运行在标签噪声之下</strong>——GT 框本身就有 ±12%~25% 的相对不确定性，代价矩阵的最小值位置随之抖动。",
            "notebook 里把候选框按<em>相对尺度</em>生成（即各尺寸的几何构型完全相同），唯一变化的只有「2 px 占框尺寸的比例」，测得的匹配翻转率是：<strong>8 px → 95%，16 px → 86%，32 px → 57%，64 px → 17%，160 px → 0%</strong>。<em>一条干净的单调曲线，说明这不是玄学而是几何。</em>",
            "此外 GIoU 在<strong>不相交区间</strong>只由外接框面积决定，<em>提供的排序信息远弱于相交区间</em>——而小 GT 与绝大多数 query 恰好都不相交。两个效应叠加。",
        ]),
        DUAL(
            "所以「<strong>小目标的匹配不稳定</strong>」和「<strong>小目标的注意力质量低</strong>」是两个独立的伤害，且互相强化：注意力质量低 → 分类分数没有信息 → 匹配靠噪声决定 → 梯度指向错误目标 → 注意力更学不到东西。<em>这就是为什么单靠「加多尺度」还不够，DINO 必须同时上 DN。</em>",
            "有一个可操作的诊断：<strong>把匹配翻转率 φ 按 GT 的像素尺寸分桶统计</strong>。健康的训练里 φ 随 epoch 单调下降；如果小尺寸桶的 φ 长期居高不下（比如 30 epoch 后仍 &gt; 0.3），说明代价矩阵在小目标上没有区分度。<em>对策不是调学习率，而是①检查有没有接上低层特征 ②调整代价权重（在小目标数据集上适当提高 λ_L1、降低 λ_giou，因为归一化 L1 至少还随位置单调变化）③上 DN。</em>notebook 里会把这个分桶 φ 实现出来。",
        ),
        CALLOUT("danger", "<p><strong>TSR 场景的直接后果</strong>：交通标志的有效检出距离决定了系统能提前多久告知下游。要在 60 米外报出限速牌，目标就是 16 像素级别——<em>恰好落在上述三个根因全部生效的区间</em>。</p><p>更危险的是它在指标上「看不见」：如果测试集里小标志只占 15%，把它们的 AP 从 0.45 打到 0.20 也只让总 mAP 掉 3.7 点——<strong>而路测体验是「远处的牌子要开到很近才报」，这是一个能被用户直接感知的严重缺陷</strong>。<em>所以 TSR 的评测必须按像素尺寸分桶（C55 模块 05 / C57 模块 05 会给完整方法）。</em></p>", "小目标塌陷在总 mAP 上几乎看不见"),
    ])),
    ("diag", "训练失败模式诊断树：四种症状，各自的成因与检查步骤", "".join([
        P("DETR 系的失败模式和密集检测器很不一样，<strong>因为它多了「匹配」这一层，很多症状的根因藏在匹配里而不是在模型里</strong>。下面四种覆盖了绝大多数情况。"),
        ASCII("""症状：训练不收敛 / 结果异常
   │
   ├─ ① loss 完全不降（几个 epoch 后仍在初始值附近）
   │     检查顺序：
   │      1. **类别 id 是否 0-based**？很多标注是 1-based，导致所有目标被判成别的类
   │      2. 框格式是不是 **归一化的 cxcywh**？给成 xyxy 或像素坐标 -> 代价矩阵全错
   │      3. 匹配代价的三个权重是否被误设为 0（尤其 cls 项用的是**概率**不是 log 概率）
   │      4. backbone 是否被整体冻结（含最后一个 stage）
   │      5. **先把一个 batch 过拟合**：单张图训 500 步，loss 必须接近 0
   │
   ├─ ② 全部预测背景（前景 query 占比 -> 0，AP=0 但 loss 在降）
   │     成因：**no-object 的类别权重没降**（eos_coef）。N=100 个 query 里
   │           93 个是背景，不降权时背景项主导梯度 -> 最优策略就是全判背景
   │     检查：打印前景 query 占比；看 cls loss 中前景/背景的贡献比
   │     修复：eos_coef=0.1（DETR）；或换 focal loss（Deformable/DINO 的做法）
   │
   ├─ ③ 框全都聚在图像中心（中心分布熵极低）
   │     成因：query 还没完成空间特化 —— 这是**早期的正常现象**，
   │           但如果 30 epoch 后仍如此，说明 cross-attention 没学起来
   │     检查：中心分布熵随 epoch 的曲线；cross-attention 的注意力质量 alpha
   │     修复：接多尺度；上两阶段/查询选择给参考点；检查位置编码是否真的生效
   │
   └─ ④ 重复框大量出现（同一目标 2~3 个高分框）
         成因 a：**decoder 的 self-attention 被误关**（或 mask 写错）-> query 无法协商去重
         成因 b：一对多分支与一对一分支**共用了同一次 self-attention**（模块 04）
         成因 c：训练不足，模型还没学会一对一
         检查：统计重复框率；关掉 self-attn 对比；看 DN 的 attention mask 是否非对称
         修复：按成因治；**在收敛前不要用「加 NMS」来掩盖它**""")
        ,
        DUAL(
            "第 ② 种最值得记住，因为它的表现极具迷惑性：<strong>loss 在稳稳下降，曲线好看得不得了，AP 却是 0</strong>。原因是模型找到了一个「局部最优」——既然 93% 的 query 目标都是背景，那全判背景就能把分类损失压得很低。<em>这不是 bug，是损失函数设计不当时的理性行为。</em>",
            "所以 <span class=\"term\">eos_coef</span>（no-object 的分类损失权重）是 DETR 里少数几个「必须按 N 与目标密度调」的超参：<strong>N 越大、单图目标越少，背景占比越高，就越需要降权</strong>。<em>DETR 用 N=100、eos_coef=0.1；Deformable/DINO 换成 focal loss 后不再需要它，因为 focal 的 (1−p)^γ 会自动压制已经学会的简单背景样本</em>——<strong>这是模块 02 讲的「集合损失与 focal loss 的关系」在工程上的落点。</strong>面试里能把 eos_coef 和 focal loss 联系起来，说明你理解的是机制而不是配置项。",
        ),
        H3("最有用的一条：先把一个 batch 过拟合"),
        P("<strong>这是排查一切训练问题的万能第一步</strong>：拿单张图（或 2 张）反复训 300–1000 步，关掉所有增强，看损失能不能压到接近 0、预测框能不能贴合 GT。"),
        UL([
            "<strong>压不下去</strong> → 问题在数据管线或损失定义（类别 id、坐标格式、匹配代价、归一化），<em>与超参无关</em>；",
            "<strong>能压下去但正常训练不行</strong> → 问题在数据规模/增强/学习率/正则，<em>模型和损失本身是对的</em>；",
            "<strong>压下去了但预测框位置系统性偏移</strong> → 坐标变换的逆变换写错（letterbox / resize 的还原，C60 模块 04 的经典坑）。",
        ]),
        CALLOUT("intuition", "这个方法的价值在于<strong>它把「无穷多个可能原因」一刀切成两半</strong>。<em>不做这一步就去调学习率，是新手和熟手最明显的分界线。</em>面试里被问「训练不收敛你怎么查」，第一句话就说这个，后面再展开诊断树。"),
    ])),
    ("metrics", "训练期该盯的四个诊断指标（而不是只盯 loss）", "".join([
        P("DETR 系的 loss 曲线信息量很低——<strong>它是分类损失、L1、GIoU 在匹配之后的加权和，任何一项出问题都会被其他项掩盖</strong>。下面四个指标各自对应一个具体故障，而且都便宜到可以每个 epoch 算一次。"),
        TABLE(["指标", "怎么算", "健康值", "异常说明什么"], [
            ["<strong>① 匹配翻转率 φ</strong>", "相邻两次评估同一批图，统计「GT 换了认领 query」的比例", "随 epoch 单调下降，后期 &lt; 0.1", "<strong>居高不下 = 代价矩阵没区分度</strong>（按尺寸分桶看）"],
            ["<strong>② 前景 query 占比</strong>", "score &gt; 阈值且 argmax ≠ no-object 的 query 数 / N", "接近 (单图平均 GT 数)/N", "<strong>→0 = 塌陷到全背景</strong>（查 eos_coef）；过高 = 重复框"],
            ["<strong>③ 框中心分布熵</strong>", "预测中心打进 G×G 网格，算归一化熵", "接近 GT 中心分布的熵", "<strong>极低 = 框全聚在中心</strong>，query 没完成空间特化"],
            ["<strong>④ 逐层 AP 单调性</strong>", "每层 decoder 的辅助输出各算一次 AP", "<strong>随层数单调上升</strong>", "非单调 = 迭代细化或 look-forward 配置有问题"],
        ]),
        P("第 ④ 个尤其被低估。<strong>DETR 系每层 decoder 都有辅助头，等于免费提供了 6 个「中途快照」</strong>——正常训练下 AP 应该逐层上升且增量递减。<em>如果第 3 层比第 5 层还高，说明后面的层在「破坏」而不是「细化」，通常是参考框的传递（detach / 坐标空间 / sigmoid-logit 转换）写错了。</em>"),
        DUAL(
            "这四个指标的共同点：<strong>它们都在回答「机制有没有按预期工作」，而不是「效果好不好」</strong>。loss 和 AP 告诉你结果，这四个告诉你原因。<em>建议把它们做成训练期的固定日志项，成本是每 epoch 在一个固定的小验证子集（200~500 张）上多跑一次前向。</em>",
            "有一个实现细节要注意：<strong>φ 必须在「同一批图、同一个匹配代价函数」下测量</strong>，否则数据增强的随机性会污染结果。<em>正确做法是固定一小批图、关掉增强、只用模型当前权重重新算一次匹配。</em>另外 <strong>③ 的熵要与 GT 中心分布的熵比较，而不是与均匀分布比</strong>——真实数据里目标本来就不是均匀分布的（TSR 的标志集中在图像上半部分与两侧），拿均匀分布当基准会给出误导性的「熵太低」结论。",
        ),
        CALLOUT("warn", "别把这四个指标当成 KPI 去优化。<strong>它们是诊断工具，不是目标函数</strong>——比如「前景 query 占比」可以通过降低阈值人为拉高，但那毫无意义。<em>它们的正确用法是：出问题时看哪个偏离了健康区间，从而把搜索范围从「所有超参」缩小到「一个具体机制」。</em>"),
    ])),
    ("infer", "推理端：top-k、阈值，以及要不要留一个 NMS 兜底", "".join([
        P("DETR 的推理看起来简单（没有 NMS），但有三个决定会显著影响最终指标，而且<strong>论文里往往一笔带过</strong>。"),
        H3("① argmax 还是 top-k：一个白拿的召回"),
        TABLE(["做法", "怎么出框", "输出框数", "适用"], [
            ["<strong>argmax（原版 DETR）</strong>", "每个 query 取概率最大的非背景类", "≤ N", "softmax + no-object 类的设定"],
            ["<strong>flatten top-k</strong>（Deformable/DINO/RT-DETR）", "把 <code>N × C</code> 个 (query, 类别) 分数拉平取 top-k", "k（100 或 300）", "<strong>sigmoid/focal 的设定</strong>"],
        ]),
        P("差别在于：<strong>flatten top-k 允许同一个 query 输出多个类别的框</strong>。当一个 query 的 top-1 类别错了但 top-2 对了（TSR 里限速 60/80 互相错分是家常便饭），argmax 直接丢掉这个目标，top-k 还能把它救回来。<em>代价是输出里会有更多低分框——但那正是 AP 计算所需要的（低分框只影响 PR 曲线尾部）。</em>"),
        CALLOUT("intuition", "这条在面试里是个漂亮的细节：<strong>「DETR 换成 sigmoid + flatten top-k 之后，AP 会涨，但这不是模型变强了，是解码方式不再丢信息」</strong>。<em>它同时解释了为什么后续工作全部从 softmax+no-object 转向了 focal+sigmoid</em>——no-object 类在 softmax 里会和所有前景类竞争同一份概率质量，而 sigmoid 下每个类独立判定，天然适合 top-k 解码。"),
        H3("② score 阈值：离线评测与在线部署要用两套"),
        P("<strong>离线算 mAP 时不该设阈值</strong>（或设得极低，如 0.001）——mAP 是在整条 PR 曲线上积分的，砍掉低分框只会让 AP 变低。<strong>而在线部署必须设阈值</strong>，因为下游只能处理有限数量的候选，而且误检有代价。"),
        UL([
            "<strong>阈值应该按「工作点」选，不是按经验数字选</strong>：给定可接受的 FP/km（C55 模块 05 的指标），在验证集上反查出对应的分数阈值。",
            "<strong>DETR 系的分数分布与 YOLO 系不同</strong>：一对一训练让高分框数量接近真实目标数，分数分布是双峰的（高分的少数 + 低分的一大堆），<em>所以阈值的敏感区间很窄，0.3 和 0.5 的差别可能很小</em>。",
            "<strong>置信度标定（calibration）不能省</strong>：模型输出的 0.8 不等于 80% 正确率。TSR 的下游（跟踪、地图匹配、VLA）要用置信度做贝叶斯融合，未标定的分数会让整条链路的决策偏移（C55 模块 02、C59 模块 03）。",
        ]),
        H3("③ 要不要仍然加一个 NMS 兜底"),
        DUAL(
            "<strong>正确答案是：可以加，但必须知道你加的是什么。</strong>一个训练充分的 DETR，输出里的重复框率极低（notebook 里会量化），此时加 NMS <em>几乎删不掉任何东西</em>——它是一道保险，不是一个后处理步骤。<strong>而它的代价是把「延迟确定性」这个选 DETR 的核心理由部分退还回去</strong>（NMS 的耗时随目标数波动）。",
            "所以决策取决于你选 DETR 的动机：<strong>①</strong> 如果动机是「无 NMS 的延迟确定性」（车端最常见），那就<em>不要加</em>，而是把重复框率做成上线门禁指标；<strong>②</strong> 如果动机是「精度」（离线自动标注、教师模型），那加一个 class-wise NMS（IoU=0.8 这种很宽松的阈值）作为保险<em>没有坏处</em>；<strong>③</strong> <strong>绝对不要用 NMS 来掩盖训练不充分</strong>——如果 NMS 能删掉大量框，说明模型还没学会一对一，此时你既付了 DETR 的训练成本，又没拿到 DETR 的部署好处。",
        ),
        CALLOUT("danger", "<p>一个真实的部署陷阱：<strong>训练时不用 NMS、部署时加了 NMS，而两边的框格式/坐标系/类别处理方式不一致</strong>。<em>典型症状是「离线 mAP 正常，上车后框整体偏移或成片消失」</em>。C60 模块 04 会讲完整的对拍方法，这里只记一条：<strong>任何在推理端新增的后处理，都必须有一份 Python↔C++ 的逐阶段 diff 报告，否则不许上线。</strong></p>", "新增后处理 = 新增一条训练-部署鸿沟"),
    ])),
    ("deploy", "部署侧的真实差异：算子、动态形状与延迟稳定性", "".join([
        P("选型讨论里最容易被忽略的一半是<strong>部署</strong>。DETR 系和 YOLO 系在这一侧的差别，比在 AP 上的差别大得多。"),
        TABLE(["部署维度", "YOLO / RTMDet 系", "DETR 系（Deformable/DINO/RT-DETR）"], [
            ["核心算子", "Conv / BN / SiLU —— <strong>所有推理框架的一等公民</strong>", "MHA、<strong>grid_sample（可变形采样）</strong>、top-k、cumsum"],
            ["TensorRT 支持", "全部原生融合", "<strong>可变形注意力常需自定义 plugin</strong>；不写就静默回退到低效实现"],
            ["车端 SoC（NPU）支持", "成熟，量化工具链完备", "<strong>attention 与 grid_sample 的 NPU 支持参差不齐</strong>，可能整块落到 DSP/CPU"],
            ["INT8 量化", "工程实践极多，掉点可控", "<strong>attention 的 softmax 与 LayerNorm 对量化敏感</strong>，常需混合精度"],
            ["动态形状", "只有输入分辨率一个维度", "多尺度展平后的序列长度随分辨率变，<strong>optimization profile 更复杂</strong>"],
            ["<strong>后处理</strong>", "<strong>NMS：耗时随目标数与阈值波动</strong>", "<strong>无 NMS：耗时恒定</strong> ← 这是选 DETR 的核心理由"],
            ["端到端延迟方差", "p99 明显高于 p50（拥堵场景目标多）", "<strong>p99 ≈ p50</strong>"],
        ]),
        DUAL(
            "<strong>把这张表读成一句话：DETR 系用「更难的算子」换来了「更确定的延迟」。</strong><em>这个交换在数据中心 GPU 上几乎白赚（算子都支持，延迟确定性是纯收益），在车端 SoC 上则要具体测——如果可变形采样在你的芯片上跑得极慢，那省下来的 NMS 时间可能远远不够补。</em>",
            "还有一个常被忽略的 DETR 系部署优势：<strong>decoder 层数可以在推理时裁剪，而无需重训</strong>。因为每层都有辅助头，第 3 层的输出本身就是一个可用的检测结果。<em>这意味着同一份权重可以支持多档速度-精度（RT-DETR 明确把它作为卖点）</em>——在多硬件平台的量产项目里，这个性质的工程价值极高：<strong>低算力车型跑 3 层，高配车型跑 6 层，模型管理只有一份。</strong>YOLO 系要做到这一点必须训多个模型。",
        ),
        CALLOUT("warn", "<strong>「无 NMS」这个卖点要算清楚才能用。</strong>NMS 在目标少时只要零点几毫秒，在密集场景（几百个候选）才会涨到几毫秒。<em>如果你的场景目标数稳定且不多（TSR 单帧标志数通常 &lt; 10），NMS 的绝对耗时和波动都很小，「无 NMS」带来的实际收益可能不到 1 ms</em>——<strong>此时它不足以成为选型的决定性理由</strong>。C53 模块 05 会给出实测方法。面试里能主动说出「这个收益要看目标数分布」，比背诵卖点有说服力得多。"),
    ])),
    ("compare", "DETR 系 vs YOLO 系：完整工程取舍表", "".join([
        P("这是本模块最该背下来的一张表。<strong>注意每一行都要能说出「为什么」，只念结论会被追问穿。</strong>"),
        TABLE(["维度", "YOLO / RTMDet 系", "DETR 系（DINO / RT-DETR）", "为什么"], [
            ["<strong>数据量需求</strong>", "<strong>低</strong>：几千张就能出可用模型", "<strong>高</strong>：一对一监督稀疏，小数据下方差大", "监督密度差一到两个数量级（模块 04）"],
            ["<strong>收敛成本</strong>", "300 ep 但单步极快", "<strong>12–36 ep</strong>（DINO 后）", "DN + 一对多把 ρ 抬上来了"],
            ["<strong>调参难度</strong>", "标签分配的超参多但社区配方成熟", "<strong>匹配代价权重、eos_coef、DN 超参</strong>，配方少", "DETR 的失败模式更隐蔽（全背景/中心塌陷）"],
            ["<strong>密集小目标</strong>", "<strong>强</strong>：密集分配 + 多尺度 + 切片推理生态成熟", "中：多尺度后可用，极小目标仍弱", "K 点采样对 2×2 格子的目标已饱和"],
            ["<strong>密集同类目标</strong>", "强（NMS 按 IoU 去重，行为可预测）", "<strong>弱</strong>：self-attention 可能把真目标当重复抑制", "一对一去重是学出来的，没有硬保证"],
            ["<strong>部署复杂度</strong>", "<strong>低</strong>：算子全支持，量化成熟", "<strong>中–高</strong>：可变形采样/attention 需 plugin", "见上一节"],
            ["<strong>延迟稳定性 (p99)</strong>", "中：NMS 随目标数波动", "<strong>高：无 NMS，恒定</strong>", "这是选 DETR 的核心理由"],
            ["<strong>一份权重多档速度</strong>", "❌ 要训多个模型", "<strong>✅ 裁 decoder 层数即可</strong>", "每层都有辅助头"],
            ["<strong>精度上限</strong>", "高", "<strong>更高</strong>（大骨干下差距明显）", "全局建模 + 密集监督的组合"],
            ["<strong>迭代速度（数据闭环）</strong>", "高", "<strong>DINO 后可比</strong>", "12 epoch 才是入场券（模块 04）"],
        ]),
        H3("三条容易记混的更正"),
        UL([
            "<strong>「DETR 收敛慢」已经过时。</strong>那是 2020 年的 DETR。DINO 是 12 epoch，比 YOLO 的 300 epoch 在墙钟时间上未必更慢。<em>面试里说「DETR 系收敛慢所以不选」会被直接判为知识停留在三年前。</em>",
            "<strong>「DETR 不需要 NMS 所以更快」是错的。</strong>无 NMS 带来的是<em>延迟确定性</em>而不是绝对速度；DETR 的 decoder 本身有成本。RT-DETR 之所以能比 YOLO 快，靠的是 hybrid encoder 的设计（C53 模块 04），不是「省了 NMS」。",
            "<strong>「DETR 对小目标弱」要加时间戳。</strong>原版 DETR 弱是真的；Deformable 之后主要弱在<em>极小目标（&lt;16px）</em>，中等小目标已经不弱。<em>说这句话时要能给出尺寸区间，否则显得没实测过。</em>",
        ]),
        ASCII("""选型决策流（**硬约束在前，指标在后**）
                        开始
                          │
          ┌───────────────▼───────────────┐
          │ Q0: 目标 SoC 支持可变形采样 /   │  ── 否 ──► **DETR 系直接出局**
          │     attention 吗？（1 天验证）  │           走 YOLO / RTMDet
          └───────────────┬───────────────┘
                       是 │
          ┌───────────────▼───────────────┐
          │ Q1: p99 延迟是硬安全指标吗？    │  ── 是 ──► **RT-DETR**（无 NMS，
          └───────────────┬───────────────┘            延迟恒定；且一份权重多档）
                       否 │
          ┌───────────────▼───────────────┐
          │ Q2: 数据量 < 10 万张有效样本？  │  ── 是 ──► **YOLO / RTMDet**
          │     或稀有类实例数 < 500？      │           （监督密度高，数据效率好）
          └───────────────┬───────────────┘
                       否 │
          ┌───────────────▼───────────────┐
          │ Q3: 主力目标 < 16 px？          │  ── 是 ──► **YOLO/RTMDet + 切片推理**
          └───────────────┬───────────────┘           （C57 模块 04）
                       否 │
                          ▼
                  两条路线都可行 -> 用 AP / 延迟做 A/B

  ※ **离线环节（自动标注 / 难例召回 / 蒸馏教师）不走这棵树**：
    没有延迟与算子约束，直接选精度上限最高的 DINO / Co-DETR。"""),
        CALLOUT("intuition", "把选型逻辑压缩成一条决策规则：<strong>「先看约束，再看指标」</strong>。<em>约束包括：车端芯片支持什么算子、数据量有多少、迭代节奏多快、延迟预算的 p99 要求是多少、团队有没有 DETR 系的调试经验。</em>这些约束往往能直接排除一半选项，剩下的才轮到比 AP。<strong>面试里被问「你会选哪个」，先反问约束是加分项，直接报模型名是减分项。</strong>"),
    ])),
    ("tsr", "给 TSR 选哪个：一次完整的论证", "".join([
        P("现在把上面所有东西串成一个真实的选型决定。<strong>场景设定：量产乘用车的交通标志识别，车端 SoC，与其他感知任务共享算力，数据闭环每周迭代。</strong>"),
        H3("第一步：把约束列全，并给出量级"),
        TABLE(["约束", "TSR 的具体值", "对选型的含义"], [
            ["延迟预算", "整个感知 33 ms（30 FPS），TSR 分到 <strong>3–6 ms</strong>", "排除大骨干；p99 必须可控"],
            ["目标像素尺寸", "主力 12–48 px，长尾到 8 px", "<strong>多尺度必需；极小目标是 DETR 系的弱区</strong>"],
            ["单帧目标数", "通常 &lt; 10，龙门架场景 10–20", "<strong>NMS 的绝对耗时很小 → 无 NMS 的收益有限</strong>"],
            ["类别数", "含变体 40–200+，长尾极重", "两级架构有吸引力（C55 模块 02）"],
            ["数据量", "十几万到百万张，但高度相关（连续帧）", "有效样本数远小于名义数量 → <strong>偏向数据效率高的方案</strong>"],
            ["迭代节奏", "每周更新数据并重训", "训练时长必须在 1 天内"],
            ["部署工具链", "车规 SoC + 厂商 NPU 编译器，INT8 为主", "<strong>非标准算子风险高</strong>"],
        ]),
        H3("第二步：逐条比对，给出结论"),
        OL([
            "<strong>延迟稳定性的收益在 TSR 上被削弱</strong>：单帧目标数 &lt; 10，NMS 耗时零点几毫秒且波动很小。<em>选 DETR 的第一理由在这个场景里不成立。</em>",
            "<strong>部署风险的代价在车端被放大</strong>：可变形采样在 NPU 上没有原生支持时，可能整块回退，延迟直接超预算。<em>这是一个「要么能跑要么不能跑」的硬约束，不是 0.5 AP 的取舍。</em>",
            "<strong>极小目标是 TSR 的核心场景，恰好是 DETR 系的弱区</strong>：而 YOLO/RTMDet 系有成熟的小目标工程生态（P2、切片推理、NWD 等，见 C57）。",
            "<strong>数据效率有利于密集检测器</strong>：TSR 数据虽多但高度相关，稀有标志类可能只有几百个实例，一对一的稀疏监督在长尾类上更吃亏。",
            "<strong>但 DETR 系不是没有位置</strong>：<em>DINO/Co-DETR 这类大模型在离线环节的价值极高</em>——作为自动标注的教师模型、作为难例挖掘的高召回筛选器、作为蒸馏的教师（C58）。这些环节没有延迟约束，正好发挥 DETR 系的精度上限优势。",
        ]),
        CALLOUT("intuition", "<p><strong>结论（可以原样在面试里说）：</strong></p><p><strong>车端量产模型选 YOLO/RTMDet 系（或 RT-DETR，视 SoC 对 attention 与 grid_sample 的支持而定），离线环节用 DINO/Co-DETR 系。</strong></p><p>理由三句话：<strong>①</strong> TSR 单帧目标少，无 NMS 的延迟收益不足以抵消车端算子支持的风险；<strong>②</strong> 极小目标与长尾稀有类是 TSR 的核心场景，密集检测器在数据效率和小目标工程生态上更有优势；<strong>③</strong> 但 DETR 系的精度上限在<em>没有延迟约束的离线环节</em>（自动标注、难例召回、蒸馏教师）价值极高，所以正确答案不是二选一，而是<strong>分工</strong>。</p>"),
        H3("第三步：把结论变成可验证的方案"),
        P("<strong>只给结论不给验证方案，是面试里最常见的失分点。</strong>下面这套动作要能说出来："),
        UL([
            "<strong>先做算子可行性验证，再做精度实验</strong>：拿目标 SoC 的编译器把 RT-DETR 的可变形采样跑一遍，看是否回退、延迟多少。<em>这一步一天就能做完，而且能直接砍掉一整条路线。</em>",
            "<strong>评测必须按像素尺寸分桶</strong>：至少分 &lt;16 / 16–32 / 32–64 / &gt;64 四桶，外加按距离、光照、天气分桶（C55 模块 05）。<em>总 mAP 在 TSR 上是一个几乎没有信息量的指标。</em>",
            "<strong>用 p99 而不是均值报延迟</strong>，并在「密集场景（龙门架 + 拥堵）」这个最坏切片上单独测。",
            "<strong>把 DETR 系作为离线教师的收益也要量化</strong>：伪标注的精度、难例召回率、蒸馏后学生模型的增益——<em>否则「离线用 DINO」只是一句好听的话。</em>",
        ]),
        CALLOUT("danger", "<p>最后一个必须避开的坑：<strong>不要因为「DETR 是端到端的、更先进」就选它。</strong><em>「端到端」在论文里是优点，在量产系统里是可测试性的敌人</em>——出了问题无法定位到具体模块。TSR 是一个安全相关功能，<strong>可解释性与可回滚性的权重远高于架构的先进性</strong>。C59 模块 05 会展开讲这一点。</p>", "先进 ≠ 适合量产"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("这一节列的是「今天还没有好答案、但直接影响 TSR 工程决策」的问题。"),
        UL([
            "<strong>DETR 系在小数据集上的行为缺乏系统研究</strong>：几乎所有对比都在 COCO（118k 图）上做。<em>在几千到几万张的自建数据集上，一对一匹配的方差有多大、需要多少 DN 组、query 数该怎么定——没有可靠的经验规律。</em>而这恰恰是绝大多数工业项目的真实规模。",
            "<strong>NMS-free 的「确定性」缺少形式化保证</strong>：一对一是训练出来的性质，不是结构保证的。<em>在分布外输入（罕见的密集同类场景）上，模型可能重新输出重复框，而系统没有任何兜底</em>。「如何给 NMS-free 一个可验证的上界」是开放问题，对安全相关系统尤其重要。",
            "<strong>可变形采样的边缘部署效率</strong>：<code>grid_sample</code> 类算子在各家 NPU 上的支持与效率差异巨大，且缺少公开的横向评测。<em>「用固定采样点模式（可离线展开成 gather）近似可变形采样」是一个有前景但研究不足的方向</em>，它能把动态采样变成静态图友好的操作。",
            "<strong>置信度标定</strong>：DETR 系的分数分布与密集检测器差别很大，而下游（跟踪、地图融合、VLA）都假设分数是概率。<em>一对一训练下的标定方法（温度缩放是否适用、分尺寸标定是否必要）研究很少</em>，但对 TSR 的多帧融合（C55 模块 04）是硬需求。",
            "<strong>decoder 层数可裁剪的精度-延迟曲线</strong>：RT-DETR 把它当卖点，但「裁到几层开始崩」「不同场景的最优层数是否不同」缺少系统刻画。<em>如果层数能按场景动态决定（简单场景 2 层、复杂场景 6 层），车端的平均算力占用可以大幅下降</em>——但动态深度会破坏静态图导出，这是算法与部署的又一处直接冲突。",
            "<strong>DETR 系与时序的结合</strong>：TSR 本质是「接近过程」，单帧检测只是输入。MOTR / TransTrack 把 query 跨帧传递的思路很自然，<em>但训练稳定性问题（跨帧的匹配翻转）比单帧更严重</em>，目前尚无量产级方案。这是 C55 模块 04 与本课的交叉地带。",
        ]),
        CALLOUT("paper", "必读：★ <em>End-to-End Object Detection with Transformers</em>（Carion et al., ECCV 2020）——附录里的训练细节与超参消融，是本模块第 1 节的一手来源；★ <em>DINO</em>（Zhang et al., ICLR 2023）与 detrex / mmdetection 里 DINO 的完整配置文件，逐项对照本模块的配方表；★ <em>RT-DETR: DETRs Beat YOLOs on Real-time Object Detection</em>（Zhao et al., CVPR 2024）——重点看 hybrid encoder 的动机与 decoder 层数可调的实验，以及它对「无 NMS 到底值多少」的量化；<em>Deformable DETR</em>（Zhu et al., ICLR 2021）的实现细节部分（多尺度参考点与 offset 的归一化方式，是复现时最容易写错的地方）；<em>Detection Transformer with Stable Matching</em>（Liu et al., ICCV 2023）对匹配不稳定的最新解释；YOLO 侧对照读 <em>YOLOv10</em>（一致双分配，把 NMS-free 带进 YOLO）与 <em>RTMDet</em>。相邻课程：C53 模块 04/05（RT-DETR 与实时检测器选型）、C55（TSR 系统设计与安全导向评测）、C57（小目标）、C60（车端部署与一致性）、C61 模块 05（面试题库）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 05 · DETR 工程实践（学习率分组 / 小目标根因 / 诊断树 / 选型）

目标：把模块 01–04 的原理变成**可执行的工程动作**——训练怎么配、出问题怎么查、
上线前看什么指标、以及给 TSR 到底该选 DETR 还是 YOLO。

**本 notebook 你会亲手实现：**
1. **学习率分组的量化依据**：带噪一阶迭代的闭式解 + 数值模拟，
   证明「离最优解越近的参数块，最优步长越小」，并扫出 backbone 的最优比例
2. **正确的 param group 构造器**（backbone 0.1× / bias·norm·query_embed 不做 weight decay）
3. **DETR 对小目标弱的三个根因**的量化：stride 账、加 P2 的代价、
   **匹配代价在小框上近似平局**的实验
4. **四个训练诊断指标**：匹配翻转率 φ（含从零写的匈牙利）、前景 query 占比、
   框中心分布熵、逐层 AP 单调性
5. **失败模式诊断树**的代码化（给一组指标，输出根因与检查步骤）
6. **推理端三件事**：argmax vs flatten top-k 的召回差、score 阈值的工作点选择、
   **NMS 兜底到底删掉了什么**
7. **DETR/YOLO 选型决策脚本**：三种 profile（车端量产 / 离线教师 / 延迟确定性优先）
   给出不同答案

> 心智模型：**先看约束，再看指标。**
> 约束（算子支持 / 数据量 / 迭代节奏 / p99 预算）常常能直接砍掉一半选项。"""),
    md("""## 1 · 学习率分组：为什么 backbone 是 0.1×

把「一个参数块的训练」建模成带噪一阶迭代 `e_{t+1} = (1-η)e_t - η·ξ_t`，
则 **E[e_T²] = (1-η)^{2T}·d₀² + η·σ²/(2-η)**：
第一项要求 η 大（衰减初始偏差），第二项要求 η 小（压低噪声地板）。
**d₀ 越小（预训练越好），最优 η 就越小。**"""),
    code("""import numpy as np, math, itertools
rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)

def final_err2(eta, d0, sigma=1.0, T=300):
    '''闭式解：训练 T 步后与最优点的期望平方距离。'''
    return (1 - eta)**(2*T) * d0**2 + eta * sigma**2 / (2 - eta)

def simulate_err2(eta, d0, sigma=1.0, T=300, trials=4000, seed=0):
    '''直接模拟带噪一阶迭代，用来验证闭式解。'''
    r = np.random.default_rng(seed)
    e = np.full(trials, float(d0))
    for _ in range(T):
        e = (1 - eta) * e - eta * sigma * r.normal(size=trials)
    return float((e**2).mean())

print('%-8s %8s %16s %16s %8s' % ('eta', 'd0', '闭式解 E[e_T^2]', '模拟 E[e_T^2]', '相对差'))
for eta, d0 in [(0.005, 0.1), (0.02, 0.1), (0.02, 5.0), (0.05, 5.0)]:
    a = final_err2(eta, d0); b = simulate_err2(eta, d0)
    print('%-8.3f %8.1f %16.5f %16.5f %7.1f%%' % (eta, d0, a, b, abs(a-b)/a*100))
    assert abs(a - b) / a < 0.15, '闭式解与模拟必须一致'
print()
print('✅ 闭式解可信 —— 下面就用它来扫最优学习率。')"""),
    code("""GRID = np.logspace(-4, -0.5, 600)

def best_lr(d0, sigma=1.0, T=300):
    v = np.array([final_err2(e, d0, sigma, T) for e in GRID])
    return float(GRID[int(np.argmin(v))])

# backbone：ImageNet 预训练，已经很接近好解 -> d0 小
# transformer + 检测头：随机初始化 -> d0 大
D_HEAD = 5.0
print('%-34s %14s %14s' % ('backbone 的预训练质量 (d0)', '最优 lr', '相对 head 的比例'))
lr_head = best_lr(D_HEAD)
ratios = []
for d0 in [2.0, 1.0, 0.5, 0.2, 0.1, 0.05]:
    lb = best_lr(d0)
    ratios.append(lb / lr_head)
    tag = '   <- 与 DETR 官方的 0.1x 吻合' if d0 == 0.05 else ''
    print('%-34.3f %14.5f %13.2f%s' % (d0, lb, lb / lr_head, tag))
print()
print('随机初始化的 head (d0=%.1f) 最优 lr = %.5f' % (D_HEAD, lr_head))
assert best_lr(0.05) < best_lr(0.5) < best_lr(5.0), '最优步长随 d0 单调上升'
assert all(ratios[i] >= ratios[i+1] for i in range(len(ratios)-1)), '比例随预训练变好单调下降'
assert ratios[-1] < 0.2, '预训练很好时，backbone 的相对学习率应显著小于 1'
print()
print('✅ 「0.1x」不是一个常数，是 **d0 的函数**：预训练越好，比例应该越小。')
print('   推论一：用 COCO 预训练的检测器微调 TSR 时，backbone 比例可以比 0.1 更小甚至冻结。')
print('   推论二：如果 backbone 是随机初始化的（罕见），0.1x 就是错的。')
print('⚠️  这个模型省略了曲率差异，只说明方向；真实的 0.1 还叠加了另外两个理由：')
print('    ② 早期匹配剧烈翻转 -> 传回 backbone 的梯度方向本身是错的；')
print('    ③ 检测数据比预训练数据小两个数量级 -> 大步长 = 灾难性遗忘。')"""),
    code("""# 灾难性遗忘的直观演示：从**预训练好解出发**（d0=0），看 backbone 被噪声推离多远
def forgetting_curve(eta, d0=0.0, sigma=1.0, T=300):
    '''返回每一步的 E[e^2]（e 越大 = 离预训练学到的好解越远）。d0=0 -> 纯粹度量「被磨掉多少」。'''
    out, cur = [], d0**2
    for _ in range(T):
        cur = (1 - eta)**2 * cur + eta**2 * sigma**2
        out.append(cur)
    return np.array(out)

print('%-22s %12s %12s %12s' % ('backbone lr', 'step 50', 'step 150', 'step 300'))
for name, eta in [('1.0x  (= head lr)', lr_head), ('0.1x', lr_head*0.1), ('0.03x', lr_head*0.03)]:
    c = forgetting_curve(eta)
    print('%-22s %12.5f %12.5f %12.5f' % (name, c[49], c[149], c[299]))
c1 = forgetting_curve(lr_head); c01 = forgetting_curve(lr_head*0.1)
assert c1[-1] > c01[-1] * 3, '大 lr 下 backbone 离预训练好解更远（噪声地板更高）'
print()
print('✅ 这就是「预训练特征被冲毁」的数学形态：**噪声地板 ~ eta·sigma^2/(2-eta)**，')
print('   与 lr 近似成正比。lr 大 10 倍，稳态误差就大 10 倍，而 backbone 本来就没什么可学的。')"""),
    md("""## 2 · 正确的 param group 构造器

两件事一起做：**① backbone 用 0.1× 学习率；
② bias / norm 的仿射参数 / object query 嵌入 / reference point 不做 weight decay。**
第 ② 条漏掉不会报错，只会让 AP 低 0.5~1 点且极难归因。"""),
    code("""NAMED_PARAMS = [
    'backbone.0.body.conv1.weight',
    'backbone.0.body.layer1.0.bn1.weight',
    'backbone.0.body.layer1.0.bn1.bias',
    'backbone.0.body.layer4.2.conv3.weight',
    'backbone.1.position_embedding.dummy',            # 位置编码（不属于 backbone 主干）
    'transformer.encoder.layers.0.self_attn.in_proj_weight',
    'transformer.encoder.layers.0.self_attn.in_proj_bias',
    'transformer.encoder.layers.0.norm1.weight',
    'transformer.encoder.layers.0.norm1.bias',
    'transformer.decoder.layers.0.cross_attn.sampling_offsets.weight',
    'transformer.decoder.layers.0.cross_attn.sampling_offsets.bias',
    'query_embed.weight',                             # **object query 的可学嵌入**
    'reference_points.weight',
    'reference_points.bias',
    'class_embed.weight',
    'class_embed.bias',
    'bbox_embed.layers.2.weight',
    'bbox_embed.layers.2.bias',
]

NO_DECAY_KEYS = ('.bias', 'query_embed', 'reference_points', '.norm', '.bn', 'position_embedding')

def build_param_groups(names, base_lr=1e-4, backbone_mult=0.1, wd=1e-4):
    '''返回 4 组：(backbone|other) x (decay|no_decay)。'''
    buckets = {}
    for n in names:
        is_bb = n.startswith('backbone.0')                       # 只有主干走 0.1x
        no_decay = any(k in n for k in NO_DECAY_KEYS)
        buckets.setdefault((is_bb, no_decay), []).append(n)
    groups = []
    for (is_bb, no_decay), ns in sorted(buckets.items()):
        groups.append({'name': ('backbone' if is_bb else 'other') + ('/no_decay' if no_decay else '/decay'),
                       'params': ns,
                       'lr': base_lr * (backbone_mult if is_bb else 1.0),
                       'weight_decay': 0.0 if no_decay else wd})
    return groups

gs = build_param_groups(NAMED_PARAMS)
print('%-22s %8s %8s %14s' % ('组', '参数数', 'lr', 'weight_decay'))
for g in gs:
    print('%-22s %8d %8.1e %14.1e' % (g['name'], len(g['params']), g['lr'], g['weight_decay']))
lut = {n: g for g in gs for n in g['params']}
assert lut['backbone.0.body.conv1.weight']['lr'] == 1e-5, 'backbone 主干 0.1x'
assert lut['transformer.encoder.layers.0.self_attn.in_proj_weight']['lr'] == 1e-4
assert lut['query_embed.weight']['weight_decay'] == 0.0, '**query 嵌入不能做 weight decay**'
assert lut['reference_points.weight']['weight_decay'] == 0.0
assert lut['transformer.encoder.layers.0.norm1.weight']['weight_decay'] == 0.0
assert lut['class_embed.bias']['weight_decay'] == 0.0
assert lut['bbox_embed.layers.2.weight']['weight_decay'] == 1e-4
print()
print('⚠️  对 query_embed 施加 weight decay = 持续把它往原点拉，')
print('    而它编码的正是**空间先验**（模块 03 讲的 query 空间特化）—— 会直接削弱特化。')
print('✅ 这类 bug 不报错、不崩溃，只让 AP 低 0.5~1 点，是最难归因的一类。')"""),
    md("""## 3 · 根因①②：stride 账与加 P2 的代价

原版 DETR 只用 C5（stride 32）。先把「目标在特征图上还剩几个格子」算清楚，
再算「把 P2（stride 4）接上要付多少代价」。"""),
    code("""IMG_H, IMG_W = 800, 1333
SIZES = [('TSR 80m 限速牌', 8), ('TSR 60m 限速牌', 16), ('TSR 30m 限速牌', 32),
         ('TSR 近处大牌', 64), ('COCO 平均目标', 100), ('近处车辆', 256)]
STRIDES = [4, 8, 16, 32, 64]

print('%-18s' % '目标像素尺寸' + ''.join('%12s' % ('stride %d' % s) for s in STRIDES))
for name, px in SIZES:
    cells = [(px/s)**2 for s in STRIDES]
    print('%-18s' % ('%s (%dx%d)' % (name, px, px)) +
          ''.join('%12.2f' % c for c in cells))
print()
print('（表里是「目标在该层特征图上占的格子数」；< 1 意味着它没有独立的特征向量）')
assert (16/32)**2 < 0.3, '16px 目标在 stride 32 上只占 0.25 格'
assert (16/8)**2 >= 4, '接到 stride 8 才有 2x2 个格子'
print()
print('✅ 结论：TSR 主力尺寸 12~48 px -> **P3 (stride 8) 是主力层，P2 (stride 4) 值得评估**，')
print('   而 P6/P7 几乎没有负载。直接照抄 COCO 配置会把算力浪费在没有目标的高层上。')"""),
    code("""# 加 P2 的代价：encoder 的 token 数按分辨率平方增长
tok = {s: (IMG_H//s) * (IMG_W//s) for s in STRIDES}
print('%-12s %12s %14s' % ('特征层', 'token 数', '占 P3~P6 总量'))
base = sum(tok[s] for s in [8, 16, 32, 64])
for s in STRIDES:
    print('%-12s %12d %13.1f%%' % ('stride %d' % s, tok[s], tok[s]/base*100))
print()
print('P3~P6 总 token = %d' % base)
print('P2~P6 总 token = %d  (**%.1f 倍**)' % (base + tok[4], (base + tok[4])/base))
assert (base + tok[4]) / base > 3.5, '加 P2 让 token 数涨 3.5 倍以上'
print()
print('%-34s %16s %16s' % ('encoder 自注意力', 'token 数', '复杂度 O(N^2)'))
for name, n in [('DETR 全局 attn，仅 C5', tok[32]),
                ('DETR 全局 attn，P3~P6', base),
                ('可变形 attn，P3~P6 (K=4)', base)]:
    cost = n*n if '全局' in name else n * 4 * 4
    print('%-34s %16d %16.2e' % (name, n, cost))
assert base*base / (base*16) > 1000, '全局注意力在多尺度上比可变形注意力贵三个数量级'
print()
print('✅ 这就是「多尺度只有在可变形注意力之后才变得免费」的算术依据。')
print('⚠️  但 P2 依然贵：token 数 3.7 倍 -> encoder 计算与显存同比例上升。')
print('    TSR 的实际做法通常是**只在 ROI（图像上半部 / 消失点附近）上启用高分辨率层**（C57 模块 04）。')"""),
    md("""## 4 · 根因③：匹配代价对小框极度敏感 → 匹配在标签噪声之下抖动

关键事实：**预测误差与标注误差都是「绝对像素」量级的，而 IoU 对绝对位移的敏感性与框尺寸成反比。**
于是同样 2 px 的抖动，对 160 px 的框毫无影响，对 16 px 的框足以让匹配的赢家换人。"""),
    code("""def xyxy(b):
    cx, cy, w, h = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([cx-w/2, cy-h/2, cx+w/2, cy+h/2], 1)

def iou_giou(a, b):
    '''a:(N,4) cxcywh 像素, b:(4,) cxcywh 像素。返回 (iou, giou)，各 (N,)。'''
    A = xyxy(a); B = xyxy(b[None])[0]
    x1 = np.maximum(A[:, 0], B[0]); y1 = np.maximum(A[:, 1], B[1])
    x2 = np.minimum(A[:, 2], B[2]); y2 = np.minimum(A[:, 3], B[3])
    inter = np.clip(x2-x1, 0, None) * np.clip(y2-y1, 0, None)
    sa = (A[:, 2]-A[:, 0])*(A[:, 3]-A[:, 1]); sb = (B[2]-B[0])*(B[3]-B[1])
    union = sa + sb - inter
    iou = inter / (union + 1e-12)
    cx1 = np.minimum(A[:, 0], B[0]); cy1 = np.minimum(A[:, 1], B[1])
    cx2 = np.maximum(A[:, 2], B[2]); cy2 = np.maximum(A[:, 3], B[3])
    area_c = (cx2-cx1)*(cy2-cy1)
    return iou, iou - (area_c - union)/(area_c + 1e-12)

W_CLS, W_L1, W_GIOU = 2.0, 5.0, 2.0

def loc_cost(cands, gt):
    '''代价里与位置有关的两项：归一化 L1 + GIoU。'''
    scale = np.array([IMG_W, IMG_H, IMG_W, IMG_H])
    l1 = np.abs(cands/scale - gt/scale).sum(1)
    _, g = iou_giou(cands, gt)
    return W_L1*l1 + W_GIOU*(1 - g)

def shifted_iou(px, d):
    '''边长 px 的方框，沿对角线平移 d 个像素后的 IoU。'''
    gt = np.array([600.0, 400.0, float(px), float(px)])
    c = gt.copy(); c[0] += d; c[1] += d
    return float(iou_giou(c[None], gt)[0][0])

print('%-14s' % 'GT 边长' + ''.join('%12s' % ('平移 %dpx' % d) for d in [1, 2, 4, 8]))
for px in [8, 16, 32, 64, 160]:
    print('%-14s' % ('%dx%d' % (px, px)) + ''.join('%12.3f' % shifted_iou(px, d)
                                                   for d in [1, 2, 4, 8]))
assert abs(shifted_iou(8, 2) - 0.391) < 0.01, '8x8 的框平移 2px，IoU 掉到 0.39'
assert shifted_iou(64, 2) > 0.88, '64x64 的框平移 2px，IoU 还有 0.88'
print()
print('⚠️  **同一个 2 像素的位移，8x8 的框 IoU 掉到 0.39，64x64 的框还有 0.88。**')
print('    而人工标注的抖动本来就有 ±2px —— 对 8px 的框，这是 25% 的相对误差。')
print('✅ 推论：小目标的匹配决策**运行在标签噪声之下**，「谁该认领」这件事本身就是病态的。')"""),
    code("""# 量化：把候选框按**相对尺度**生成（消除尺度效应），只让 ±2px 的绝对噪声起作用
def make_candidates(gt, n=40, rel=0.25, seed=0):
    '''候选框相对 GT 的偏移与缩放都按**比例**给 -> 各尺寸的几何构型完全相似。'''
    r = np.random.default_rng(seed)
    c = gt[:2] + r.normal(scale=rel*gt[2], size=(n, 2))
    wh = gt[2:] * np.exp(r.normal(scale=rel, size=(n, 2)))
    return np.concatenate([c, wh], 1)

def claim_flip_rate(px, noise_px=2.0, epochs=400, seed=1):
    '''GT 每个 epoch 被 ±noise_px 的标注/预测噪声扰动，统计「认领者换人」的频率。'''
    gt = np.array([600.0, 400.0, float(px), float(px)])
    cands = make_candidates(gt, seed=seed)
    r = np.random.default_rng(seed + 50)
    prev, flips = None, []
    for _ in range(epochs):
        g = gt.copy(); g[:2] += r.normal(scale=noise_px, size=2)
        cur = int(np.argmin(loc_cost(cands, g)))
        if prev is not None:
            flips.append(cur != prev)
        prev = cur
    return float(np.mean(flips))

print('%-16s %20s %10s %22s' % ('GT 像素尺寸', '候选与GT的中位IoU', '2px占比', '匹配翻转率 phi (±2px)'))
fr = {}
for px in [8, 16, 32, 64, 160]:
    gt = np.array([600.0, 400.0, float(px), float(px)])
    med = float(np.median(iou_giou(make_candidates(gt), gt)[0]))
    fr[px] = claim_flip_rate(px)
    print('%-16s %20.3f %9.1f%% %21.1f%%'
          % ('%dx%d' % (px, px), med, 2.0/px*100, fr[px]*100))
assert all(fr[a] > fr[b] for a, b in zip([8, 16, 32, 64], [16, 32, 64, 160])), 'phi 随尺寸单调下降'
assert fr[16] > 0.5 and fr[160] < 0.05
print()
print('✅ 第 2 列几乎不变 = 候选框的**几何构型完全相同**；')
print('   唯一变化的是第 3 列 —— ±2px 这个**绝对**噪声占框尺寸的比例。')
print('   16px 的框：2px = 12.5%% 的尺寸 -> 认领者 %.0f%% 的时候会换人；' % (fr[16]*100))
print('   160px 的框：2px = 1.25% 的尺寸 -> 几乎从不换人。')
print()
print('⚠️  「小目标的注意力质量低」与「小目标的匹配不稳定」是**两个独立的伤害，且互相强化**：')
print('    注意力差 -> 分类分数没有信息 -> 匹配靠噪声决定 -> 梯度指向错目标 -> 注意力更学不到。')
print('✅ 所以光加多尺度还不够，DINO 必须**同时**上 DN —— 这是模块 04 那条主线的落点。')
print()
print('可操作的诊断：把 phi **按 GT 像素尺寸分桶**统计。')
print('  健康：各桶都随 epoch 单调下降；')
print('  异常：小尺寸桶 30 epoch 后仍 > 0.3 -> 代价矩阵在小目标上没有区分度。')
print('  对策：① 检查有没有接上低层特征 ② 调代价权重（小目标数据上适当提高 lambda_L1）③ 上 DN。')"""),
    md("""## 5 · 四个训练诊断指标

loss 曲线在 DETR 系里信息量很低（分类/L1/GIoU 三项互相掩盖）。
下面四个指标各自对应一个具体故障，而且便宜到可以每个 epoch 在一个固定小验证集上算一次。"""),
    code("""def hungarian(cost):
    '''O(n^3) 匈牙利算法，要求 行数 <= 列数。返回 (rows, cols)。'''
    a = np.asarray(cost, dtype=float); n, m = a.shape
    assert n <= m
    INF = float('inf')
    u = np.zeros(n+1); v = np.zeros(m+1)
    p = np.zeros(m+1, dtype=int); way = np.zeros(m+1, dtype=int)
    for i in range(1, n+1):
        p[0] = i; j0 = 0
        minv = np.full(m+1, INF); used = np.zeros(m+1, dtype=bool)
        while True:
            used[j0] = True; i0 = p[j0]; delta = INF; j1 = 0
            for j in range(1, m+1):
                if used[j]:
                    continue
                cur = a[i0-1, j-1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur; way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]; j1 = j
            for j in range(m+1):
                if used[j]:
                    u[p[j]] += delta; v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
    rows = np.arange(n); cols = np.zeros(n, dtype=int)
    for j in range(1, m+1):
        if p[j]:
            cols[p[j]-1] = j-1
    return rows, cols

def match_flip_rate(n_eval, Nq, M, noise, seed=0, margin=1.0):
    '''指标①：相邻两次评估中「GT 换了认领 query」的比例。
       base 里每个 GT 有一个「真正该认领它」的 query，优势为 margin；
       noise 模拟训练早期代价矩阵里的随机成分。'''
    r = np.random.default_rng(seed)
    base = r.random((M, Nq)) + 1.0
    true_j = r.choice(Nq, size=M, replace=False)
    base[np.arange(M), true_j] -= margin        # 信号：真实匹配的代价明显更低
    prev, flips = None, []
    for _ in range(n_eval):
        _, cols = hungarian(base + noise * r.normal(size=(M, Nq)))
        if prev is not None:
            flips.append(float((cols != prev).mean()))
        prev = cols
    return float(np.mean(flips))

print('%-16s %18s %s' % ('训练阶段（噪声）', '匹配翻转率 phi', '判读'))
prev_phi = 1.0
for name, s in [('epoch 1  (0.50)', 0.50), ('epoch 5  (0.20)', 0.20),
                ('epoch 20 (0.08)', 0.08), ('epoch 50 (0.02)', 0.02)]:
    phi = match_flip_rate(25, 100, 8, s, seed=3)
    verdict = '健康' if phi < 0.15 else ('偏高' if phi < 0.4 else '**优化目标在抖**')
    print('%-16s %17.1f%% %s' % (name, phi*100, verdict))
    assert phi <= prev_phi + 1e-9, 'phi 应随训练单调下降'
    prev_phi = phi
print()
print('✅ 指标①：phi 必须在**同一批图、关掉增强**的条件下测，否则增强的随机性会污染结果。')"""),
    code("""def foreground_ratio(scores, thr=0.5):
    '''指标②：前景 query 占比。scores:(N, C+1)，最后一列是 no-object。'''
    pred = scores.argmax(1)
    conf = scores.max(1)
    return float(((pred != scores.shape[1]-1) & (conf > thr)).mean())

def center_entropy(centers, grid=8):
    '''指标③：预测中心打进 grid x grid 网格后的**归一化熵**（0~1）。'''
    idx = np.clip((np.asarray(centers) * grid).astype(int), 0, grid-1)
    flat = idx[:, 1] * grid + idx[:, 0]
    cnt = np.bincount(flat, minlength=grid*grid).astype(float)
    p = cnt / cnt.sum()
    nz = p[p > 0]
    return float(-(nz * np.log(nz)).sum() / math.log(grid*grid))

N, NC = 100, 45
r = np.random.default_rng(2)
# 健康：7 个 query 高分前景，其余背景
healthy = np.full((N, NC+1), 0.01); healthy[:, -1] = 0.9
healthy[:7, -1] = 0.05
for i in range(7):
    healthy[i, r.integers(0, NC)] = 0.85
# 塌陷：全部预测背景（eos_coef 没降的经典症状）
collapsed = np.full((N, NC+1), 0.005); collapsed[:, -1] = 0.98
# 重复框过多
duplicated = healthy.copy()
for i in range(7, 40):
    duplicated[i, -1] = 0.2; duplicated[i, r.integers(0, NC)] = 0.75

print('%-16s %20s %14s' % ('状态', '前景 query 占比', '判读'))
for name, s in [('健康', healthy), ('塌陷到全背景', collapsed), ('重复框过多', duplicated)]:
    fg = foreground_ratio(s)
    verdict = '健康' if 0.02 <= fg <= 0.20 else ('**塌陷**' if fg < 0.02 else '**重复框**')
    print('%-16s %19.1f%% %14s' % (name, fg*100, verdict))
assert foreground_ratio(collapsed) == 0.0
assert 0.02 <= foreground_ratio(healthy) <= 0.15
assert foreground_ratio(duplicated) > 0.25
print()
print('健康值 ~ 单图平均 GT 数 / N = 7/100 = 7%')
print()
# 指标③：中心分布熵
gt_centers = np.stack([r.uniform(0.05, 0.95, 400), r.uniform(0.15, 0.6, 400)], 1)  # TSR：标志集中在上半部
healthy_c = gt_centers + r.normal(scale=0.02, size=gt_centers.shape)
center_col = np.stack([r.normal(0.5, 0.02, 400), r.normal(0.5, 0.02, 400)], 1)
uniform_c = r.random((400, 2))
print('%-26s %16s' % ('中心分布', '归一化熵'))
for name, c in [('GT 的真实分布（基准）', gt_centers), ('健康预测', healthy_c),
                ('**全聚在图像中心**', center_col), ('（全图均匀，仅作参照）', uniform_c)]:
    print('%-26s %16.3f' % (name, center_entropy(np.clip(c, 0, 0.999))))
e_col = center_entropy(np.clip(center_col, 0, 0.999))
e_ok = center_entropy(np.clip(healthy_c, 0, 0.999))
assert e_col < 0.4 and e_col < 0.5 * e_ok, '塌陷到中心时熵应显著低于健康值'
assert e_ok > 0.7 and abs(e_ok - center_entropy(gt_centers)) < 0.05, '健康预测的熵应贴近 GT 分布'
print()
print('⚠️  熵要与 **GT 中心分布的熵**比较，不是与均匀分布比 ——')
print('    TSR 的标志本来就集中在图像上半部与两侧，拿均匀分布当基准会得出误导性结论。')"""),
    code("""# 指标④：逐层 AP 单调性（DETR 系每层 decoder 都有辅助头，等于 6 个免费快照）
def layer_ap_health(aps, tol=0.002):
    '''返回 (是否单调不降, 首个下降的层号)。'''
    for i in range(1, len(aps)):
        if aps[i] < aps[i-1] - tol:
            return False, i
    return True, None

CASES = {
    '健康（逐层上升、增量递减）': [0.281, 0.372, 0.421, 0.446, 0.458, 0.463],
    '后段下降（参考框传递写错）': [0.280, 0.371, 0.428, 0.441, 0.402, 0.395],
    '几乎不涨（细化没起作用）':   [0.430, 0.432, 0.433, 0.434, 0.434, 0.435],
}
print('%-30s %10s %12s %s' % ('情况', '末层 AP', '首末增益', '判读'))
for name, aps in CASES.items():
    ok, bad = layer_ap_health(aps)
    gain = aps[-1] - aps[0]
    verdict = ('单调 ✅' if gain > 0.05 else '**细化无效**') if ok else ('**第 %d 层开始下降**' % bad)
    print('%-30s %10.3f %12.3f %s' % (name, aps[-1], gain, verdict))
assert layer_ap_health(CASES['健康（逐层上升、增量递减）'])[0]
assert not layer_ap_health(CASES['后段下降（参考框传递写错）'])[0]
assert layer_ap_health(CASES['几乎不涨（细化没起作用）'])[0]
print()
print('✅ 正常训练下 AP 逐层上升且**增量递减**。第 3 层比第 5 层还高 = 后面的层在破坏而不是细化，')
print('   通常是参考框的传递写错了（detach 位置 / 坐标空间 / sigmoid-logit 转换）。')
print('⚠️  「单调但几乎不涨」是另一种病：说明迭代细化没起作用，此时裁掉后几层可以白赚延迟。')"""),
    md("""## 6 · 失败模式诊断树的代码化

把模块正文的诊断树写成一个函数：**输入一组指标，输出根因与下一步检查动作**。
它的价值不是自动化，而是**把「所有超参」的搜索空间缩小到「一个具体机制」**。"""),
    code("""def diagnose(m):
    '''m: 指标字典。返回 [(症状, 最可能根因, 下一步动作), ...]，按优先级排序。'''
    out = []
    if m.get('loss_drop_ratio', 1.0) < 0.05:
        out.append(('loss 几乎不降',
                    '数据管线或损失定义（类别 id 偏移 / 坐标格式 / 代价权重）',
                    '**先把一个 batch 过拟合**：单张图训 500 步，loss 必须接近 0'))
    if m.get('fg_ratio', 0.07) < 0.02:
        out.append(('前景 query 占比 -> 0（全预测背景）',
                    'no-object 权重没降（eos_coef），背景项主导梯度',
                    '设 eos_coef=0.1，或换 focal loss；查 cls loss 的前景/背景贡献比'))
    if m.get('center_entropy', 0.8) < 0.3 and m.get('epoch', 0) > 20:
        out.append(('框全聚在图像中心',
                    'cross-attention 没学起来 / query 未完成空间特化',
                    '接多尺度；上两阶段查询选择给参考点；确认位置编码真的生效'))
    if m.get('dup_rate', 0.0) > 0.2:
        out.append(('重复框大量出现',
                    'decoder self-attention 被误关，或一对多分支与一对一分支共用了 self-attn',
                    '检查 attention mask；**收敛前不要用加 NMS 来掩盖**'))
    if m.get('phi_small', 0.0) > 0.3 and m.get('epoch', 0) > 30:
        out.append(('小尺寸桶的匹配翻转率长期居高',
                    '代价矩阵在小目标上没有区分度（多半没接低层特征）',
                    '确认 P3/P2 接上；调 lambda_L1；上 DN'))
    if not m.get('layer_ap_monotonic', True):
        out.append(('逐层 AP 非单调',
                    '参考框在层间的传递写错（detach / 坐标空间 / sigmoid-logit）',
                    '打印每层的参考框统计量，找从哪一层开始异常'))
    if not out:
        out.append(('未发现异常', '—', '继续训练；按像素尺寸分桶看 AP'))
    return out

SCENARIOS = {
    'A 全预测背景':  dict(epoch=8,  loss_drop_ratio=0.6, fg_ratio=0.000, center_entropy=0.5,
                        dup_rate=0.0, phi_small=0.2, layer_ap_monotonic=True),
    'B loss 不降':   dict(epoch=3,  loss_drop_ratio=0.01, fg_ratio=0.05, center_entropy=0.6,
                        dup_rate=0.0, phi_small=0.5, layer_ap_monotonic=True),
    'C 中心塌陷':    dict(epoch=35, loss_drop_ratio=0.7, fg_ratio=0.06, center_entropy=0.12,
                        dup_rate=0.05, phi_small=0.1, layer_ap_monotonic=True),
    'D 重复框':      dict(epoch=40, loss_drop_ratio=0.8, fg_ratio=0.35, center_entropy=0.8,
                        dup_rate=0.45, phi_small=0.1, layer_ap_monotonic=True),
    'E 健康':        dict(epoch=30, loss_drop_ratio=0.75, fg_ratio=0.07, center_entropy=0.82,
                        dup_rate=0.03, phi_small=0.08, layer_ap_monotonic=True),
}
for name, m in SCENARIOS.items():
    print('== %s ==' % name)
    for sym, cause, act in diagnose(m):
        print('   症状: %s' % sym)
        print('   根因: %s' % cause)
        print('   动作: %s' % act)
assert diagnose(SCENARIOS['A 全预测背景'])[0][1].startswith('no-object')
assert 'batch' in diagnose(SCENARIOS['B loss 不降'])[0][2]
assert diagnose(SCENARIOS['C 中心塌陷'])[0][0].startswith('框全聚')
assert diagnose(SCENARIOS['D 重复框'])[0][0].startswith('重复框')
assert diagnose(SCENARIOS['E 健康'])[0][0] == '未发现异常'
print()
print('✅ 「先把一个 batch 过拟合」是排查一切训练问题的万能第一步：')
print('   压不下去 -> 问题在数据管线或损失定义（与超参无关）；')
print('   能压下去但正常训练不行 -> 问题在数据规模/增强/学习率/正则；')
print('   压下去了但框系统性偏移 -> 坐标逆变换写错（letterbox/resize 的还原）。')"""),
    md("""## 7 · 推理端三件事：argmax vs top-k、score 阈值、NMS 兜底

**① argmax 丢信息**：query 的 top-1 类别错但 top-2 对时（限速 60/80 是家常便饭），
argmax 直接丢掉这个目标，flatten top-k 还能救回来。"""),
    code("""NQ, NCLS = 100, 45
r = np.random.default_rng(4)
M_GT = 12
gt_cls = r.integers(0, NCLS, M_GT)
gt_query = r.choice(NQ, M_GT, replace=False)          # 每个 GT 由哪个 query 负责

# 构造 sigmoid 分数：负责的 query 在正确类上高分，但其中 1/3 的 top-1 被易混类抢走
scores = r.random((NQ, NCLS)) * 0.15
for k, (q, c) in enumerate(zip(gt_query, gt_cls)):
    scores[q, c] = 0.62
    if k % 3 == 0:                                    # 易混类（限速 60 vs 80）抢走 top-1
        confuse = (c + 1) % NCLS
        scores[q, confuse] = 0.70

def decode_argmax(scores, k=100):
    '''每个 query 只取 top-1 类别。'''
    cls = scores.argmax(1); sc = scores.max(1)
    idx = np.argsort(-sc)[:k]
    return list(zip(idx.tolist(), cls[idx].tolist(), sc[idx].tolist()))

def decode_topk(scores, k=100):
    '''把 (query, 类别) 全部拉平取 top-k —— **一个 query 可以出多个类别的框**。'''
    flat = scores.reshape(-1)
    idx = np.argsort(-flat)[:k]
    return [(int(i // scores.shape[1]), int(i % scores.shape[1]), float(flat[i])) for i in idx]

def recall(dets, gt_query, gt_cls):
    hit = {(int(q), int(c)) for q, c, _ in dets}
    return float(np.mean([(int(q), int(c)) in hit for q, c in zip(gt_query, gt_cls)]))

r_arg = recall(decode_argmax(scores), gt_query, gt_cls)
r_top = recall(decode_topk(scores), gt_query, gt_cls)
print('%-34s %12s %10s' % ('解码方式', '输出框数', '召回'))
print('%-34s %12d %9.1f%%' % ('argmax（原版 DETR，softmax+no-object）', len(decode_argmax(scores)), r_arg*100))
print('%-34s %12d %9.1f%%' % ('flatten top-k（Deformable/DINO/RT-DETR）', len(decode_topk(scores)), r_top*100))
assert r_top > r_arg, 'top-k 解码必须不低于 argmax，且在有易混类时更高'
assert abs(r_arg - 2/3) < 0.1, '有 1/3 的 GT 的 top-1 被易混类抢走'
print()
print('✅ 差别 %.1f 个百分点，而且**不是模型变强了，是解码方式不再丢信息**。' % ((r_top-r_arg)*100))
print('   这也解释了后续工作为什么全部从 softmax+no-object 转向 focal+sigmoid：')
print('   no-object 在 softmax 里要和所有前景类争同一份概率质量，而 sigmoid 下每类独立判定。')"""),
    code("""# ② score 阈值：离线算 mAP 不设阈值，在线部署按**工作点**设
def prf(dets, gt_query, gt_cls, thr):
    keep = [(q, c) for q, c, s in dets if s >= thr]
    hit = {(int(q), int(c)) for q, c in keep}
    tp = sum(1 for q, c in zip(gt_query, gt_cls) if (int(q), int(c)) in hit)
    fp = len(keep) - tp
    rec = tp / len(gt_query)
    prec = tp / max(len(keep), 1)
    return prec, rec, fp

dets = decode_topk(scores, k=300)
print('%-10s %12s %12s %12s' % ('阈值', '精确率', '召回率', 'FP 数'))
for thr in [0.05, 0.10, 0.20, 0.30, 0.50, 0.65]:
    p, rc, fp = prf(dets, gt_query, gt_cls, thr)
    print('%-10.2f %11.1f%% %11.1f%% %12d' % (thr, p*100, rc*100, fp))
p_lo, r_lo, fp_lo = prf(dets, gt_query, gt_cls, 0.05)
p_hi, r_hi, fp_hi = prf(dets, gt_query, gt_cls, 0.50)
assert r_lo >= r_hi and p_hi >= p_lo and fp_hi <= fp_lo
print()
print('✅ 离线算 mAP **不该设阈值**（或设 0.001）——mAP 在整条 PR 曲线上积分，砍低分框只会让 AP 变低。')
print('✅ 在线部署**必须**设阈值，而且要按工作点反查：')
print('   给定可接受的 FP/km（C55 模块 05），在验证集上找出对应的分数阈值。')
print('⚠️  DETR 系的分数分布是双峰的（少数高分 + 一大堆低分），所以阈值的敏感区间很窄；')
print('    但**置信度标定不能省** —— 下游（跟踪/地图/VLA）要拿它做贝叶斯融合。')"""),
    code("""# ③ NMS 兜底到底删掉了什么？
def nms(boxes, scores_, iou_thr=0.7):
    '''boxes:(N,4) cxcywh 像素。返回保留的下标。'''
    order = np.argsort(-scores_); keep = []
    while len(order):
        i = order[0]; keep.append(int(i))
        if len(order) == 1:
            break
        iou, _ = iou_giou(boxes[order[1:]], boxes[i])
        order = order[1:][iou < iou_thr]
    return keep

def synth_preds(n_gt=12, per_gt=1, rel_jitter=0.03, seed=0):
    '''per_gt=1 模拟训练充分的 DETR；per_gt>1 模拟密集检测器（或没学会一对一的 DETR）。
       抖动按框尺寸的比例给，这样各尺寸目标的重复框都能被同一个 IoU 阈值识别。'''
    rr = np.random.default_rng(seed)
    gts = np.stack([rr.uniform(200, 1100, n_gt), rr.uniform(150, 650, n_gt),
                    rr.uniform(30, 120, n_gt), rr.uniform(30, 120, n_gt)], 1)
    boxes, sc = [], []
    for g in gts:
        for _ in range(per_gt):
            b = g.copy(); b[:2] += rr.normal(scale=rel_jitter*g[2], size=2)
            b[2:] *= rr.uniform(0.96, 1.04, 2)
            boxes.append(b); sc.append(rr.uniform(0.5, 0.95))
    return np.array(boxes), np.array(sc), gts

def dup_rate(boxes, scores_, iou_thr=0.7):
    '''重复框率 = 1 - NMS 后保留的比例。'''
    return 1.0 - len(nms(boxes, scores_, iou_thr)) / len(boxes)

print('%-40s %10s %14s %14s' % ('模型输出', '框数', 'NMS 后框数', '被删掉的比例'))
for name, per_gt in [('训练充分的 DETR（一对一学会了）', 1),
                     ('训练不足的 DETR（还在出重复框）', 3),
                     ('密集检测器（YOLO 系，NMS 前）', 6)]:
    b, s, _ = synth_preds(per_gt=per_gt, seed=7)
    kept = nms(b, s)
    print('%-40s %10d %14d %13.1f%%' % (name, len(b), len(kept), dup_rate(b, s)*100))
b1, s1, _ = synth_preds(per_gt=1, seed=7)
b6, s6, _ = synth_preds(per_gt=6, seed=7)
assert dup_rate(b1, s1) < 0.05, '训练充分的 DETR 输出里 NMS 几乎删不掉东西'
assert dup_rate(b6, s6) > 0.6, '密集检测器必须靠 NMS 去重'
print()
print('✅ 决策规则（按你选 DETR 的**动机**来定）：')
print('   ① 动机是「无 NMS 的延迟确定性」（车端最常见）-> **不要加**，把重复框率做成上线门禁；')
print('   ② 动机是「精度」（离线自动标注 / 教师模型）-> 加一个宽松的 class-wise NMS 作保险，无害；')
print('   ③ **绝不能用 NMS 掩盖训练不充分** —— 那样你既付了 DETR 的训练成本，')
print('      又没拿到 DETR 的部署好处，是最糟糕的组合。')"""),
    md("""## 8 · DETR/YOLO 选型决策脚本

**先看约束，再看指标。** 同一张能力表，换一组权重（profile）就会给出不同答案——
这正是「选型没有唯一正确答案，只有针对约束的正确答案」的代码化。"""),
    code("""# 各维度打分（0~10，越高越好），来自模块正文的取舍表
CAPABILITY = {
    #                        数据效率 收敛/迭代 调参难度 密集小目标 密集同类 部署成熟度 延迟p99稳定 一权重多档 精度上限
    'YOLOv8/v10':        dict(data=9, iterate=8, tune=8, small=8, dense=8, deploy=10, p99=6, multi=2, ceiling=7),
    'RTMDet':            dict(data=9, iterate=8, tune=8, small=8, dense=8, deploy=9,  p99=6, multi=2, ceiling=8),
    'RT-DETR':           dict(data=6, iterate=8, tune=6, small=7, dense=6, deploy=6,  p99=10, multi=9, ceiling=8),
    'DINO / Co-DETR':    dict(data=5, iterate=6, tune=5, small=7, dense=6, deploy=4,  p99=9, multi=8, ceiling=10),
}
PROFILES = {
    'A 车端量产 TSR（算力紧、数据长尾、每周迭代）':
        dict(data=3, iterate=3, tune=2, small=3, dense=2, deploy=3, p99=1, multi=1, ceiling=1),
    'B 离线自动标注 / 蒸馏教师（无延迟约束）':
        dict(data=0, iterate=1, tune=1, small=3, dense=2, deploy=0, p99=0, multi=0, ceiling=10),
    'C 延迟确定性优先（多任务共享算力、p99 是硬指标）':
        dict(data=1, iterate=1, tune=1, small=2, dense=1, deploy=2, p99=5, multi=3, ceiling=1),
}

def score(model, weights):
    caps = CAPABILITY[model]
    return sum(caps[k] * w for k, w in weights.items()) / sum(weights.values())

def choose(weights):
    ranked = sorted(CAPABILITY, key=lambda m: -score(m, weights))
    return ranked, {m: round(score(m, weights), 2) for m in ranked}

for pname, w in PROFILES.items():
    ranked, sc_ = choose(w)
    print('== %s ==' % pname)
    for m in ranked:
        print('   %-20s %.2f' % (m, sc_[m]))
    print('   -> 推荐: **%s**' % ranked[0])
    print()

assert choose(PROFILES['A 车端量产 TSR（算力紧、数据长尾、每周迭代）'])[0][0] in ('RTMDet', 'YOLOv8/v10')
assert choose(PROFILES['B 离线自动标注 / 蒸馏教师（无延迟约束）'])[0][0] == 'DINO / Co-DETR'
assert choose(PROFILES['C 延迟确定性优先（多任务共享算力、p99 是硬指标）'])[0][0] == 'RT-DETR'
print('✅ 同一张能力表，三组权重给出三个不同答案 —— **选型没有唯一正确答案，只有针对约束的正确答案**。')
print('✅ 所以面试里被问「你会选哪个」，**先反问约束是加分项，直接报模型名是减分项**。')"""),
    code("""# 把结论落成 TSR 的分阶段方案（含验证动作，只给结论不给验证是最常见的失分点）
PLAN = [
    ('第 0 步（1 天）', '算子可行性验证',
     '拿目标 SoC 的编译器把 RT-DETR 的可变形采样跑一遍，看是否静默回退、延迟多少',
     '**能直接砍掉一整条路线**'),
    ('第 1 步', '建立分桶评测',
     '按像素尺寸 <16/16-32/32-64/>64 四桶 + 距离/光照/天气分桶',
     '总 mAP 在 TSR 上几乎没有信息量'),
    ('第 2 步', '车端主力模型',
     'RTMDet / YOLO 系起步；若第 0 步通过则 RT-DETR 并行做 A/B',
     '数据效率与部署成熟度优先'),
    ('第 3 步', '离线教师',
     'DINO / Co-DETR 做伪标注、难例召回、蒸馏教师',
     '无延迟约束，发挥精度上限'),
    ('第 4 步', '量化教师收益',
     '伪标注精度、难例召回率、蒸馏后学生的增益',
     '否则「离线用 DINO」只是一句好听的话'),
    ('第 5 步', '延迟以 p99 报',
     '在「龙门架 + 拥堵」这个最坏切片上单独测',
     '车端安全关心的是尾延迟'),
]
print('%-14s %-16s %s' % ('阶段', '动作', '为什么'))
for stage, act, how, why in PLAN:
    print('%-14s %-16s %s' % (stage, act, why))
    print('%-14s %-16s   -> %s' % ('', '', how))
assert len(PLAN) == 6 and PLAN[0][1] == '算子可行性验证'
print()
print('⚠️  最后一条红线：**不要因为「DETR 是端到端的、更先进」就选它。**')
print('    「端到端」在论文里是优点，在量产系统里是**可测试性的敌人** —— 出问题无法定位到模块。')
print('    TSR 是安全相关功能，**可解释性与可回滚性的权重远高于架构的先进性**。')"""),
    md("""## ✏️ 练习 1：param group 构造器

实现 `make_groups(names, base_lr, backbone_mult, wd)`，返回
`{参数名: (lr, weight_decay)}`。规则：
① 名字以 `backbone.0` 开头 → `lr = base_lr * backbone_mult`；
② 名字含 `.bias` / `.norm` / `.bn` / `query_embed` / `reference_points` / `position_embedding`
→ `weight_decay = 0`，其余为 `wd`。"""),
    code("""def make_groups(names, base_lr=1e-4, backbone_mult=0.1, wd=1e-4):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
g = make_groups(NAMED_PARAMS)
assert g['backbone.0.body.conv1.weight'] == (1e-5, 1e-4)
assert g['backbone.0.body.layer1.0.bn1.weight'] == (1e-5, 0.0), 'BN 的仿射参数不做 weight decay'
assert g['query_embed.weight'] == (1e-4, 0.0), '**query 嵌入不能做 weight decay**'
assert g['reference_points.bias'] == (1e-4, 0.0)
assert g['transformer.encoder.layers.0.self_attn.in_proj_weight'] == (1e-4, 1e-4)
assert g['bbox_embed.layers.2.bias'] == (1e-4, 0.0)
n_bb = sum(1 for n, (lr, _) in g.items() if lr == 1e-5)
n_nd = sum(1 for n, (_, w) in g.items() if w == 0.0)
print('backbone 组参数数 %d / %d   |   不做 weight decay 的参数数 %d / %d'
      % (n_bb, len(g), n_nd, len(g)))
assert n_bb == 4 and n_nd == 11, (n_bb, n_nd)
print('✅ 练习 1 通过：这两条规则漏掉任何一条都不会报错，只会让 AP 低 0.5~1 点。')"""),
    md("""## ✏️ 练习 2：框中心分布熵

实现 `entropy_of_centers(centers, grid=8)`：把归一化中心 `(N,2)` 打进 `grid×grid` 网格，
返回**归一化熵** `H / ln(grid²)`（取值 0~1）。空网格不参与求和。"""),
    code("""def entropy_of_centers(centers, grid=8):
    # TODO: ① 量化到网格并 clip 到 [0, grid-1]  ② 统计频次 -> 概率
    #       ③ H = -sum(p log p)，只对 p>0 求和  ④ 除以 log(grid*grid)
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
one_cell = np.full((200, 2), 0.06)                       # 全落在同一个格子
uniform_pts = np.random.default_rng(0).random((20000, 2))
assert abs(entropy_of_centers(one_cell)) < 1e-9, '全在一个格子 -> 熵 = 0'
assert entropy_of_centers(uniform_pts) > 0.99, '均匀分布 -> 熵接近 1'
half = np.concatenate([np.random.default_rng(1).random((20000, 1)),
                       np.random.default_rng(2).random((20000, 1)) * 0.5], 1)
h_half = entropy_of_centers(half)
print('全在一个格子 %.3f  |  上半部均匀 %.3f  |  全图均匀 %.3f'
      % (entropy_of_centers(one_cell), h_half, entropy_of_centers(uniform_pts)))
assert abs(h_half - math.log(32)/math.log(64)) < 0.02, '只占一半格子 -> 熵 = log(32)/log(64) = 0.833'
print('✅ 练习 2 通过：熵要与 **GT 中心分布的熵**比，不是与均匀分布比 ——')
print('   TSR 的标志本来就集中在图像上半部，拿均匀分布当基准会得出误导性结论。')"""),
    md("""## ✏️ 练习 3：诊断树

实现 `triage(m)`：输入指标字典，返回**最高优先级**的一条 `(症状, 根因关键词)`。
优先级顺序（先命中先返回）：
`loss 不降` → `全预测背景` → `重复框` → `中心塌陷（epoch>20）` → `健康`。"""),
    code("""def triage(m):
    # TODO: 按优先级依次判断，返回 (症状, 根因关键词)
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
assert triage(dict(loss_drop_ratio=0.01, fg_ratio=0.0, dup_rate=0.9,
                   center_entropy=0.1, epoch=50))[1] == '数据管线'
assert triage(dict(loss_drop_ratio=0.6, fg_ratio=0.0, dup_rate=0.0,
                   center_entropy=0.6, epoch=8))[1] == 'eos_coef'
assert triage(dict(loss_drop_ratio=0.8, fg_ratio=0.35, dup_rate=0.45,
                   center_entropy=0.8, epoch=40))[1] == 'self-attention'
assert triage(dict(loss_drop_ratio=0.7, fg_ratio=0.06, dup_rate=0.05,
                   center_entropy=0.12, epoch=35))[1] == 'cross-attention'
assert triage(dict(loss_drop_ratio=0.75, fg_ratio=0.07, dup_rate=0.03,
                   center_entropy=0.82, epoch=30))[1] == '—'
# **早期的中心塌陷是正常现象**，不该报警
assert triage(dict(loss_drop_ratio=0.5, fg_ratio=0.05, dup_rate=0.0,
                   center_entropy=0.10, epoch=5))[1] == '—'
for name, m in SCENARIOS.items():
    print('%-14s -> %s' % (name, triage(m)))
print('✅ 练习 3 通过：诊断树的价值不是自动化，而是**把「所有超参」缩小到「一个具体机制」**。')"""),
    md("""## ✏️ 练习 4：选型决策器

实现 `pick(capability, weights, min_requirements=None)`：
按加权平均打分排序，但**先用硬约束过滤**——
`min_requirements` 是 `{维度: 最低分}`，不满足的候选**直接出局**（不参与打分）。
返回 `(推荐模型, 排序后的 [(名字, 分数)], 被淘汰的名字列表)`。"""),
    code("""def pick(capability, weights, min_requirements=None):
    # TODO: ① 用 min_requirements 过滤  ② 加权平均打分  ③ 降序排序
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
w_a = PROFILES['A 车端量产 TSR（算力紧、数据长尾、每周迭代）']
best, ranked, out = pick(CAPABILITY, w_a)
assert out == [] and best in ('YOLOv8/v10', 'RTMDet')

# 硬约束：车端 SoC 不支持可变形采样 -> 部署成熟度必须 >= 9
best2, ranked2, out2 = pick(CAPABILITY, w_a, {'deploy': 9})
print('无硬约束 -> %s' % best)
print('要求 deploy>=9（SoC 不支持可变形采样）-> %s，淘汰 %s' % (best2, out2))
assert set(out2) == {'RT-DETR', 'DINO / Co-DETR'}
assert best2 in ('YOLOv8/v10', 'RTMDet')

# 硬约束：p99 是安全指标，必须 >= 9
best3, ranked3, out3 = pick(CAPABILITY, w_a, {'p99': 9})
print('要求 p99>=9（尾延迟是安全硬指标）-> %s，淘汰 %s' % (best3, out3))
assert set(out3) == {'YOLOv8/v10', 'RTMDet'}
assert best3 == 'RT-DETR'
assert len(ranked3) == 2 and ranked3[0][1] >= ranked3[1][1]
print('✅ 练习 4 通过：**先看约束，再看指标** —— 硬约束常常直接砍掉一半候选，')
print('   剩下的才轮到比 AP。这就是本模块最想让你带走的选型方法论。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def make_groups(names, base_lr=1e-4, backbone_mult=0.1, wd=1e-4):
    out = {}
    for n in names:
        lr = base_lr * (backbone_mult if n.startswith('backbone.0') else 1.0)
        no_decay = any(k in n for k in NO_DECAY_KEYS)
        out[n] = (lr, 0.0 if no_decay else wd)
    return out"""),
    code("""# 练习 2 参考答案
def entropy_of_centers(centers, grid=8):
    idx = np.clip((np.asarray(centers) * grid).astype(int), 0, grid - 1)
    flat = idx[:, 1] * grid + idx[:, 0]
    p = np.bincount(flat, minlength=grid*grid).astype(float)
    p = p / p.sum()
    nz = p[p > 0]
    return float(-(nz * np.log(nz)).sum() / math.log(grid * grid))"""),
    code("""# 练习 3 参考答案
def triage(m):
    if m.get('loss_drop_ratio', 1.0) < 0.05:
        return ('loss 几乎不降', '数据管线')
    if m.get('fg_ratio', 0.07) < 0.02:
        return ('全预测背景', 'eos_coef')
    if m.get('dup_rate', 0.0) > 0.2:
        return ('重复框大量出现', 'self-attention')
    if m.get('center_entropy', 0.8) < 0.3 and m.get('epoch', 0) > 20:
        return ('框全聚在中心', 'cross-attention')     # 早期塌陷是正常现象，不报警
    return ('未发现异常', '—')"""),
    code("""# 练习 4 参考答案
def pick(capability, weights, min_requirements=None):
    min_requirements = min_requirements or {}
    alive, out = {}, []
    for name, caps in capability.items():
        if all(caps.get(k, 0) >= v for k, v in min_requirements.items()):
            alive[name] = caps
        else:
            out.append(name)
    tot = sum(weights.values())
    ranked = sorted(((n, sum(c[k]*w for k, w in weights.items())/tot)
                     for n, c in alive.items()), key=lambda t: -t[1])
    return (ranked[0][0] if ranked else None), ranked, sorted(out)"""),
    md("""---
## 🧪 真实工程胶囊：一份可直接用的 DETR 系训练/诊断/选型清单"""),
    code("""RECIPE = r'''
# ================ 1) 优化器与 param group（DETR / DINO 通用）================
NO_DECAY = ('.bias', '.norm', '.bn', 'query_embed', 'reference_points',
            'level_embed', 'position_embedding', 'sampling_offsets')
param_dicts = [
    {"params": [p for n, p in model.named_parameters()
                if not n.startswith("backbone.0") and not any(k in n for k in NO_DECAY) and p.requires_grad],
     "lr": 1e-4, "weight_decay": 1e-4},
    {"params": [p for n, p in model.named_parameters()
                if not n.startswith("backbone.0") and any(k in n for k in NO_DECAY) and p.requires_grad],
     "lr": 1e-4, "weight_decay": 0.0},
    {"params": [p for n, p in model.named_parameters()
                if n.startswith("backbone.0") and not any(k in n for k in NO_DECAY) and p.requires_grad],
     "lr": 1e-5, "weight_decay": 1e-4},          # <-- backbone 0.1x
    {"params": [p for n, p in model.named_parameters()
                if n.startswith("backbone.0") and any(k in n for k in NO_DECAY) and p.requires_grad],
     "lr": 1e-5, "weight_decay": 0.0},
]
opt = torch.optim.AdamW(param_dicts, lr=1e-4, weight_decay=1e-4)
sched = torch.optim.lr_scheduler.MultiStepLR(opt, milestones=[11], gamma=0.1)   # 12ep 配方
# 每一步都要：torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)   <-- 0.1 是刻意的小值
# backbone 的 BN 必须是 FrozenBatchNorm2d（小 batch 下 BN 统计不可靠）

# ================ 2) 每个 epoch 的诊断日志（固定小验证集、关增强）================
LOG = dict(
    phi_all=None,        # 匹配翻转率（全部）      健康：随 epoch 单调下降，后期 < 0.1
    phi_by_size=None,    # **按像素尺寸分桶的 phi** 异常：小尺寸桶 30ep 后仍 > 0.3
    fg_ratio=None,       # 前景 query 占比         健康：≈ 单图平均 GT 数 / N
    center_entropy=None, # 框中心分布熵            与 **GT 中心分布的熵** 比，不与均匀分布比
    layer_aps=None,      # 逐层 AP                 健康：单调上升且增量递减
)

# ================ 3) 排查顺序（出问题时照着走）================
# [0] **先把一个 batch 过拟合**：单图训 500 步、关全部增强，loss 必须接近 0
#     压不下去 -> 数据管线/损失定义；能压下去 -> 数据规模/增强/lr/正则
# [1] loss 不降   -> 类别 id 是否 0-based / 框是否归一化 cxcywh / 代价权重是否为 0
# [2] 全预测背景  -> eos_coef 没降（或没换 focal loss）
# [3] 中心塌陷    -> 多尺度没接上 / 位置编码没生效 / 未上两阶段查询选择
# [4] 重复框      -> decoder self-attn 被误关；一对多分支与一对一分支共用了 self-attn
# [5] 小目标塌陷  -> 按像素尺寸分桶看 AP（总 mAP 会掩盖它）；接 P3/P2；上 DN

# ================ 4) 推理端 ================
# 离线评测：不设 score 阈值（或 0.001）；用 flatten top-k 解码（k=100/300）
# 在线部署：按 FP/km 工作点反查阈值；置信度要标定（下游要拿它做贝叶斯融合）
# NMS：动机是「延迟确定性」就**不要加**，把重复框率做成上线门禁指标；
#      动机是「精度」（离线教师）可以加一个宽松的 class-wise NMS 作保险

# ================ 5) 选型（先看约束，再看指标）================
# 第 0 步（1 天）：拿目标 SoC 的编译器跑一遍可变形采样，看是否静默回退 —— 能直接砍掉一条路线
# 车端量产：RTMDet / YOLO 系起步；SoC 支持良好则 RT-DETR 并行 A/B
# 离线环节：DINO / Co-DETR 做伪标注、难例召回、蒸馏教师（并**量化**其收益）
# 报延迟一律用 p99，且在「龙门架 + 拥堵」这个最坏切片上单独测
'''
print(RECIPE)
for key in ['backbone.0', 'weight_decay": 0.0', 'clip_grad_norm_', 'FrozenBatchNorm2d',
            'phi_by_size', '先把一个 batch 过拟合', 'eos_coef', 'flatten top-k', 'p99']:
    assert key in RECIPE, key
print('✅ 配方覆盖：param group / 梯度裁剪 / 诊断日志 / 排查顺序 / 推理端 / 选型')"""),
    md("""### 小结

- **backbone 用 0.1× 学习率有三个理由**，第一个可以算出来：带噪一阶迭代的稳态误差
  `E[e_T²] = (1-η)^{2T}d₀² + ησ²/(2-η)`，**d₀ 越小（预训练越好），最优 η 越小**。
  notebook 里 d₀=0.05 时算出的最优比例正好是 **0.11**。
  → 推论：**0.1 不是常数，是 d₀ 的函数**；COCO 预训练后微调 TSR 可以更小甚至冻结。
- **weight decay 必须分组**：bias / norm 仿射 / **query_embed** / reference_points 都不能做。
  对 query 嵌入做 weight decay = 持续削弱它编码的空间先验。这类 bug 不报错，只掉 0.5~1 AP。
- **DETR 对小目标弱是三个独立根因**：① 单尺度（16px 在 stride 32 上只占 0.25 格）；
  ② query 数固定且偏少；③ **匹配决策运行在标签噪声之下**——
  同样 2 px 位移，8×8 框 IoU 掉到 0.39，160×160 框还有 0.95；实测匹配翻转率
  **8px→95%，160px→0%**，一条干净的单调曲线。
- **四个诊断指标比 loss 有用**：匹配翻转率 φ（按尺寸分桶）、前景 query 占比、
  框中心分布熵（**与 GT 分布比，不与均匀分布比**）、逐层 AP 单调性。
- **「先把一个 batch 过拟合」是万能第一步**：它把「无穷多个可能原因」一刀切成
  「数据管线/损失定义」与「数据规模/增强/超参」两半。
- **推理端三件事**：flatten top-k 比 argmax 白拿召回（不是模型变强，是解码不再丢信息）；
  离线不设阈值、在线按 FP/km 工作点反查；**NMS 兜底加不加，取决于你选 DETR 的动机**。
- **选型没有唯一正确答案，只有针对约束的正确答案**：同一张能力表换一组权重就换一个赢家。
  **TSR 量产的结论是分工——车端 YOLO/RTMDet（或 RT-DETR，视 SoC 而定），
  离线 DINO/Co-DETR 做教师**，而不是二选一。
- **第 0 步永远是算子可行性验证**（1 天），它能直接砍掉一整条路线，比跑一个月实验划算。

本课到此结束。下一站建议：**C55（TSR 与自动驾驶感知）** 把这里的选型放进完整系统，
**C57（小目标检测）** 深挖本模块第 2 节的三个根因，**C60（车端部署）** 把第 6 节的部署风险变成可执行的验证流程。"""),
]
