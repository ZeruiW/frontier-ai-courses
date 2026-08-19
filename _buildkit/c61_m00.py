# -*- coding: utf-8 -*-
"""C61 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "C18 检测基础；C53–C60 八门课任意一门都可以先学，但本课默认你至少跑通过一次检测训练"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb（指标意识自测 + 归因信息增益 + manifest 校验）'),
    ("课程模块", "6 个模块 · 纯 numpy + 标准库 · 从实验设计到面试演练的完整落地层"),
    ("预计时长", "总览 35 分钟 + 跑 30 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("gap", "从「会跑通」到「能负责」：中间隔着什么", "".join([
        P("前面八门课（C53–C60）教的是<strong>零件</strong>：实时检测器怎么设计、集合预测怎么匹配、小目标为什么难、增强怎么做、长尾怎么挖、车端怎么部署。这门课教的是<strong>把零件装成一个你敢签字的系统</strong>——以及在面试里把这件事讲清楚。"),
        P("先把「会跑通」和「能负责」的差距摊开。它不是知识量的差距，是<em>你被问到什么问题时答不上来</em>的差距："),
        TABLE(["能力层级", "典型表现", "被问到什么会卡住", "在面试里的信号"], [
            ["<strong>会跑通</strong>", "能改 config、能启动训练、能跑出一个 mAP 数字、能导出 ONNX", "「这个 mAP 是在什么评测集、什么 score 阈值、什么 IoU 口径下算的？」", "答案里全是工具名（mmdet / ultralytics / TensorRT），没有数字"],
            ["<strong>能改进</strong>", "知道加 Mosaic、换标签分配、加 P2 能涨点，也真的涨了", "「涨了 0.4，你怎么知道这不是种子噪声？」", "能说方法，说不出验证；对代价（延迟/显存/训练时长）没有账"],
            ["<strong>能负责</strong>", "任何改动都能预估影响、能在指标动了之后定位到原因、交付物可复现可回滚", "——（这一层的问题是「你怎么设计整个闭环」，而这正是他想听的）", "回答自带<strong>数字、代价、验证方式、失败时的退路</strong>"],
        ]),
        P("这三层之间的跳跃，靠的是三个可训练的能力。它们贯穿本课全部六个模块："),
        ASCII("""                    ┌──────────────────────────────────────────┐
                    │           工业检测工程师的三个核心能力      │
                    └──────────────────────────────────────────┘

   ① 指标意识                ② 归因能力                ③ 交付纪律
   ─────────────             ─────────────             ─────────────
   任何改动都能说出          看到指标变化能             可复现 / 可回滚 /
   对哪个指标、              定位到原因                 可交接
   有多大影响、
   付出什么代价

        │                         │                         │
        ▼                         ▼                         ▼
   "加 P2 层                 "夜间桶掉了 4 点，          "这个模型是哪个
    mAP_small +1.5~4,         白天没动 ->                 commit + 哪版数据
    延迟 +25~60%,             先查校准集里               + 哪个种子训的，
    显存 +40%"                有没有夜间图"               3 分钟能查到"

        └─────────────┬───────────┴─────────────┬───────────┘
                      ▼                         ▼
              **改动是有价的**            **交付是有契约的**
              不是"试试看涨不涨"          不是"我这边跑是好的\""""),
        DUAL(
            "这三个能力有一个共同的底色：<strong>把「感觉」换成「数」</strong>。「我觉得这个改动应该有用」→「这类改动在这个尺寸桶上的经验量级是 +1.5~4 点，延迟代价 25~60%」；「不知道为什么掉点了」→「掉点只发生在夜间桶，其他桶在噪声范围内，所以是数据分布问题不是模型容量问题」；「我这边是好的」→「run_id 3f2a1c，commit d41d8c，数据版本 v7，种子 0，manifest 在这里」。",
            "更精确地说，这三个能力对应工程系统的三个属性：<span class=\"term\">可预测性</span>（predictability，改动前能给出影响的先验区间）、<span class=\"term\">可观测性</span>（observability，指标变化能被分解到可定位的维度）、<span class=\"term\">可复现性</span>（reproducibility，任意历史状态可以被重建）。<em>这三者缺任何一个，团队的迭代速度都会从「线性推进」退化成「随机游走」</em>——因为无法预测就只能全试、无法观测就只能猜、无法复现就无法回退，于是每次迭代都在重新支付上一次的成本。",
        ),
        CALLOUT("intuition", "一句话概括本课的立场：<strong>检测工程的难点从来不是「模型不够好」，而是「你不知道模型为什么是现在这样，也不知道下一步该做什么」</strong>。C53–C60 给你候选动作，C61 教你在候选动作里选、验、交付。"),
    ])),

    # ============================================================== 2
    ("metric-sense", "能力一 · 指标意识：任何改动都能说出对哪个指标有多大影响", "".join([
        P("<strong>指标意识</strong>不是「知道 mAP 是什么」，而是一个具体到可以被检验的能力：给你一个改动，你能在<em>不跑实验</em>的情况下说出四件事——影响<strong>哪个</strong>指标、<strong>多大</strong>量级、<strong>什么方向</strong>、<strong>什么代价</strong>。"),
        H3("先说「哪个指标」：整体 mAP 是最不敏感的那一个"),
        P("绝大多数 TSR 改动的效果，在整体 mAP 上都是被稀释的。假设你的数据里小目标（&lt;32²）占 40%、稀有类占 3%，那么："),
        TABLE(["改动", "它真正影响的指标", "在整体 mAP 上看到的", "为什么被稀释"], [
            ["加 P2 层 / 提高输入分辨率", "<strong>mAP_small +1.5~4.0</strong>", "+0.6~1.6", "只有 40% 的样本受益"],
            ["稀有类 copy-paste", "<strong>尾部类 AP +3~15</strong>", "+0.2~1.0", "稀有类只占类别权重的一小块"],
            ["INT8 校准集缺夜间样本", "<strong>夜间桶 −5~−15</strong>", "−0.5~−1.5", "夜间帧只占评测集 10%"],
            ["水平翻转增强（含方向性标志）", "<strong>左转/右转类 AP −5~−20</strong>", "−0.2~−1.0", "方向类只有几个类别"],
        ]),
        CALLOUT("danger", "<p><strong>面试高频翻车点。</strong>被问「你这个改动带来多少提升」时，只答「整体 mAP 涨了 0.8」会被立刻追问「涨在哪？」——如果你答不上来，面试官得到的信息是<em>你没有分桶评测</em>，而分桶评测是 TSR 岗位的基本功。<strong>正确答法：「整体 +0.8，但这个数字没有意义——真正的效果在小目标桶（&lt;16px）上是 +3.2，其他桶在噪声范围内（±0.2）。因为这个改动只影响高分辨率特征层，所以这个分布正是我预期的。」</strong><em>面试官想听的是：你的预期和你的观测是否对得上——对得上说明你理解机制，对不上而你注意到了，说明你会归因。</em></p>", "「涨了多少」的正确答法是「涨在哪」"),
        H3("再说「什么代价」：每个改动都要记一笔双边账"),
        P("把一个改动的价值写成收益与代价的比值，是选型的最小工具。设 baseline 延迟为 $T_0$："),
        MATH("\\text{ROI} \\;=\\; \\frac{\\Delta \\text{AP}_{\\text{关键桶}}}{\\Delta T / T_0}\\,, \\qquad \\text{而「必做项」的判据是} \\;\\; \\Delta T \\le 0 \\;\\wedge\\; \\Delta \\text{AP} > 0"),
        P("这个式子的作用不是算出一个精确的分数，而是<strong>强迫你把代价写下来</strong>。notebook 里会让你对一张 14 项的改动表逐条算 ROI，你会发现结论非常反直觉：<em>Mosaic、close-mosaic、换标签分配、延长训练——这几项的延迟代价是严格的 0，却常常被排在「加分辨率」之后</em>。"),
        DUAL(
            "为什么「零延迟代价」的改动会被排后面？因为它们不酷。加分辨率、换更大 backbone、上 Transformer——这些改动有故事可讲；而「把 epoch 从 12 拉到 36」「把 MaxIoU 分配换成 TaskAligned」听起来像杂活。<strong>但在量产系统里，延迟预算是硬约束，而训练时长不是</strong>——车端 33 ms 的一帧里 TSR 可能只分到 4–6 ms，多花 3 天训练却不占这 6 ms 的改动，价值上限比任何架构改动都高。",
            "严谨地说，这是一个<span class=\"term\">约束优化</span>问题而不是无约束优化：目标是在 $T \\le T_{\\text{budget}}$、$M \\le M_{\\text{budget}}$（显存）、$P \\le P_{\\text{budget}}$（功耗）的可行域内最大化关键桶的 AP。<em>零延迟改动不消耗任何约束资源，因此它们在可行域内的任何一点都是严格改进</em>——用经济学的话说，它们是<strong>帕累托改进</strong>而不是权衡。<strong>面试里主动把改动分成「免费的」和「要花预算的」两类，是一个很强的成熟度信号</strong>，因为它说明你把延迟当成了预算而不是指标。",
        ),
        CALLOUT("warn", "指标意识的一个必要成分是<strong>知道自己不确定</strong>。经验量级应该报成<em>区间</em>而不是点估计：说「+1.5 到 +4.0，取决于小目标占比」比说「+2.7」可信得多。<em>报点估计的人，要么真的做过一模一样的实验，要么在编</em>——而面试官会用追问区分这两种情况（「为什么是 2.7 不是 2.2？」）。"),
    ])),

    # ============================================================== 3
    ("attribution", "能力二 · 归因：看到指标变化，能定位到原因", "".join([
        P("归因是三个能力里最难教、也最值钱的一个。它的核心不是「知道所有可能的原因」（那只是背清单），而是<strong>知道下一步该做哪个检查</strong>。"),
        H3("坏做法：按可能性从高到低逐个试"),
        P("常见的排查方式是「先看看是不是学习率的问题，不是的话看看是不是数据的问题，还不是的话……」。这在候选原因有 6 个、每个检查要 20 分钟时，期望耗时约 2 小时。<strong>更糟的是它是串行的，且每次失败不提供任何信息</strong>。"),
        H3("好做法：挑「能把候选集劈成两半」的检查"),
        P("把候选原因看成一个概率分布 $p_1,\\dots,p_k$。一个二值检查把候选集分成「检查通过 → 排除掉 S」和「检查失败 → 排除掉补集」两支。<strong>这个检查的<span class=\"term\">信息增益</span>（information gain）恰好等于被它分到一边的那部分概率质量 $m$ 的二元熵</strong>："),
        MATH("\\mathrm{IG} \\;=\\; H(p_1,\\dots,p_k) - \\bigl[\\,m\\,H(P\\mid S) + (1-m)\\,H(P\\mid \\bar S)\\,\\bigr] \\;=\\; H_b(m) \\;=\\; -m\\log_2 m - (1-m)\\log_2(1-m)"),
        P("这个等式非常有用，因为它把「哪个检查最有价值」这个模糊问题变成了一个可以口算的问题：<strong>找那个把概率质量切得最接近 50/50 的检查</strong>。notebook 里会把它实现出来，并在一个真实的症状（「mAP 恒为 0」）上跑一遍。"),
        ASCII("""症状：mAP 恒为 0（loss 正常下降）

候选原因与先验（来自你团队的历史事故统计，不是拍脑袋）
  类别 ID 偏移 0/1 ................ 0.35 ┐
  坐标格式弄反 xywh↔xyxy .......... 0.25 ├─ 数据/接口类，占 0.85
  标注坐标未随 resize 缩放 ......... 0.10 │
  评测集与训练集类别表不一致 ....... 0.15 ┘
  学习率过大导致框全部发散 ......... 0.10 ┐─ 训练类，占 0.15
  数据没打乱（每 batch 单类） ....... 0.05 ┘

候选检查                                     切出的质量 m    IG=H_b(m)
  A. **把 GT 当预测送进评测器**，看 mAP 是否 = 1.0   0.85      0.610
  B. 打印前 20 个预测框的坐标范围（[0,1] 还是像素）   0.35      0.934
  C. 检查 loss 曲线是否在 3 个 epoch 后仍在降        0.15      0.610
  D. 统计一个 batch 里的类别数是否 > 1              0.05      0.286
  E. **打印训练侧与评测侧的 class_id -> name 映射表**  0.50      1.000  ← 最优

  ▶ 先做 E：一次检查消掉 1 bit（二值检查的理论上限），6 个候选 3 次内定位。
  ▶ **注意 A 虽然直觉上"最全面"，信息增益反而只有 0.61**——
    因为它切出 0.85 的质量，几乎总是给同一个答案（"评测管线有问题"），
    做完之后你面对的还是原来那 4 个候选。"""),
        DUAL(
            "这里有个反直觉的结论值得记住：<strong>「最全面的检查」通常不是「最该先做的检查」</strong>。检查 A（把 GT 当预测喂进评测器）能一次性判定「评测管线是否正常」，覆盖 85% 的候选原因，听起来应该先做。但正因为它覆盖面太大，它的结果几乎总是「评测管线有问题」，于是<em>做完之后你面对的还是原来那 4 个候选</em>。<strong>而检查 E（打印两侧的类别映射表）只针对两个原因，却恰好把候选集切成 0.50 / 0.50，无论结果如何都真正砍掉一半。</strong>",
            "这与二分查找的直觉是同一个东西：<em>二分之所以是 $O(\\log n)$，不是因为每次比较很聪明，而是因为每次比较把搜索空间对半砍</em>。归因也一样——检查的价值由它的<strong>判别性</strong>决定，而不由它的覆盖面决定。在实践中这意味着：面对一个指标异动，先花两分钟列出候选原因和它们的先验质量，再挑那个把质量切得最均匀的检查，通常比直接动手快一个数量级。<strong>面试里被问「线上某类标志漏检，你的排查流程是什么」时，如果你的回答是一个「先查 A 再查 B」的固定清单，那是背的；如果你的回答是「先看漏检是集中在某个场景桶还是全局均匀——这一个观察就能把候选原因砍掉一半」，那是会的。</strong>",
        ),
        CALLOUT("intuition", "归因的可迁移心法：<strong>不要问「原因是什么」，要问「哪个观察最能区分候选原因」</strong>。前者需要灵感，后者是一个可以系统执行的算法——而且它在训练调试（模块 03）、误差分析（模块 02）、部署一致性排查（C60）里是同一个算法。"),
    ])),

    # ============================================================== 4
    ("discipline", "能力三 · 交付纪律：可复现、可回滚、可交接", "".join([
        P("前两个能力决定你能走多快，第三个能力决定你走过的路能不能被别人（包括三个月后的你自己）沿用。<strong>它是三者里唯一一个「不做也不会立刻出事」的能力——所以也是最容易被牺牲的那一个。</strong>"),
        TABLE(["属性", "具体要求", "缺失时的典型事故", "验证方式"], [
            ["<strong>可复现</strong>", "任意历史 run 能被重建：代码 commit（含是否 dirty）、数据版本、完整配置、环境（Python/CUDA/驱动/库版本）、随机种子、完整指标", "「上个季度那个 0.82 的模型是怎么训的？」——没人知道，只能重训一遍，两周没了", "随机抽一个 30 天前的 run，从 manifest 重跑，看指标是否落在种子方差区间内"],
            ["<strong>可回滚</strong>", "每个发布物有唯一 ID、可追溯到源 run、上一版本随时可切回；回滚不需要重新构建", "新版本上线后夜间误报暴涨，但旧 engine 已被覆盖，只能带病运行到重新构建完成", "定期做<em>回滚演练</em>：随机挑一个历史版本，计时看多久能切回去"],
            ["<strong>可交接</strong>", "别人能在不问你的情况下：跑通训练、复现评测、理解为什么是这个配置、知道已知的坑", "你休假一周，团队的迭代停摆；或者新人花三周重新踩你踩过的坑", "让一个没碰过这个项目的同事按文档跑一遍，记录他卡住的每一个点"],
        ]),
        P("这三条里，<strong>可复现</strong>是地基——不可复现的东西谈不上回滚（回滚到一个你重建不出来的状态没有意义），也谈不上交接（交接一堆无法重现的数字等于没交接）。而可复现的最小实现只有一件事：<strong>每个 run 落一份 manifest</strong>。"),
        ASCII("""run_manifest.json  —— 最小必要字段（缺一项，可复现性就有一个洞）

{
  "run_id":       "2026-08-17_tsr_p2head_s0",     ← 人可读 + 唯一
  "code": {
     "commit":    "d41d8cd98f00b204e9800998",     ← **必须**
     "dirty":     false,                          ← **必须**：true 意味着不可复现
     "repo":      "git@internal:perception/tsr"
  },
  "data": {
     "train":     "tsr_v7.2  (sha256:9f86d0…)",   ← 数据也要版本
     "val":       "tsr_eval_v3  (frozen 2026-06-01)",
     "buckets":   "size/light/weather/class"      ← 分桶定义也是数据的一部分
  },
  "config_hash":  "a3f5…",  "config": { …完整展开，不要只存 diff… },
  "env": { "python":"3.11.9", "numpy":"1.26.4",
           "torch":"2.4.1+cu121", "gpu":"A100-80G", "driver":"550.54" },
  "seed":         0,                               ← **必须**：没有种子=没有对照
  "metrics": {                                     ← **全量**，不是只存 mAP
     "mAP": 0.8213, "mAP50": 0.9410,
     "by_size":  {"<16px":0.412, "16-32":0.701, "32-64":0.868, ">64":0.912},
     "by_light": {"day":0.851, "night":0.674, "backlit":0.612},
     "by_class": { …全部类别… },
     "fp_per_km": 0.83, "latency_p50_ms": 8.9, "latency_p99_ms": 9.2
  },
  "artifacts": { "ckpt":"s3://…/best.pth", "onnx":"…", "engine":"…" },
  "wallclock_h": 11.4,  "notes": "P2 层实验，对照 run 2026-08-17_tsr_base_s0"
}""")
        ,
        DUAL(
            "为什么 <code>dirty: true</code> 要当成红线？因为它意味着这次 run 用的代码<strong>在世界上任何地方都不存在</strong>——不在 git 里，不在别人机器上，只在你当时那个工作区。<em>三天后你 checkout 到别的分支，这次实验就永久失去了复现可能</em>。而实验结果一旦不可复现，它在后续所有对比里都是不可用的——你不知道它的 baseline 是什么状态。",
            "更微妙的是 <strong>metrics 必须存全量</strong>这一条。常见做法是只把 mAP 写进 tracking 系统，因为「其他的以后要看再算」。<em>问题是「以后」通常意味着评测代码已经改过、评测集已经加过数据、分桶定义已经调整过</em>——于是你拿不到当时那个分桶数字了，历史 run 之间的分桶对比永久失效。<strong>存储成本是几 KB，重建成本是重跑一次评测（如果还能重建的话）</strong>。这条规则可以推广：<em>凡是「重新计算比存下来贵得多」的量，就在产生的那一刻存下来</em>。",
        ),
        CALLOUT("danger", "<p><strong>交付纪律在面试里的考法比你想的直接。</strong>常见问法是「讲一个你负责的项目，从头到尾」——听起来是叙事题，实际上面试官在数三样东西：<em>①你说的每个指标有没有对应的评测口径；②你说的每个改进有没有对应的验证方式；③你有没有提到任何一次回滚、失败或代价</em>。<strong>只讲成功、只讲涨点、不讲代价的叙事，会被判定为「没有真正负责过」</strong>——因为真实的项目里一定有回滚、有掉点、有为了赶版本做的妥协。<em>模块 04 会把这套叙事的结构完整拆开。</em></p>", "只讲成功的项目叙事 = 没负责过"),
    ])),

    # ============================================================== 5
    ("landing", "本课是 C53–C60 的落地层：八门课的零件如何装配", "".join([
        P("这门课不引入新的算法。它做的是把前八门课的产出<strong>组织成可执行的工作流</strong>——每一门课贡献一类「候选动作」或「候选原因」，C61 负责选、验、讲。"),
        TABLE(["课程", "它给你的零件", "在 C61 里被用在哪", "对应本课模块"], [
            ["<strong>C53</strong> 实时检测器", "YOLO 演进 / 标签分配 / RTMDet / RT-DETR / 延迟-精度选型", "「架构原理题」的答案骨架；选型题的论证链", "m05"],
            ["<strong>C54</strong> DETR 集合预测", "匈牙利匹配 / 集合损失 / query / 收敛难题", "白板题（匈牙利实现）；「为什么不需要 NMS」", "m05"],
            ["<strong>C55</strong> TSR 与自动驾驶", "数据集 / 两级架构 / 失效模式四象限 / 时序融合 / 安全导向评测", "<strong>误差分析的分桶维度</strong>；系统设计题的骨架", "m02、m04"],
            ["<strong>C56</strong> 检测增强", "几何/光度/混合类增强 / 流水线 / 消融", "<strong>消融设计的正例与反例</strong>；改动清单里的零延迟项", "m01"],
            ["<strong>C57</strong> 小目标", "IoU 尺度敏感性 / FPN 层级 / NWD / 切片推理", "分尺寸桶评测；「小目标为什么难」的定量回答", "m02、m05"],
            ["<strong>C58</strong> 难例与长尾", "重采样/重加权 / OHEM / 主动学习触发 / 挖掘基建 / 闭环验证", "<strong>「指标掉了下一步做什么」的动作库</strong>", "m02、m04"],
            ["<strong>C59</strong> VLA 与感知接口", "动作表示 / TSR→VLA 序列化 / 规则约束 / 开闭环评测", "系统设计题里的下游接口部分（JD 明确要求）", "m04、m05"],
            ["<strong>C60</strong> 车端部署一致性", "预处理对齐 / TensorRT / INT8 校准 / 后处理对齐 / 延迟剖析", "<strong>调试手册的部署分支</strong>；量化掉点排查题", "m03、m05"],
        ]),
        ASCII("""C53 ─┐                                        ┌─► m01 实验设计与归因
C54 ─┤                                        │      （怎么证明它有用）
C55 ─┤   八门课 = 候选动作库 + 候选原因库      ├─► m02 误差分析
C56 ─┼──────────────────────────────────────► │      （下一步做什么）
C57 ─┤                                        ├─► m03 调试手册
C58 ─┤   C61 = 在库里「选 / 验 / 讲」的方法    │      （为什么坏了）
C59 ─┤                                        ├─► m04 项目叙事
C60 ─┘                                        │      （怎么讲清楚）
                                              └─► m05 面试演练
                                                     （怎么当场答）

  没有 C53–C60：C61 变成空洞的方法论（"要做消融""要分桶"——谁不知道）
  没有 C61    ：C53–C60 变成一堆读过但用不上的知识（面试典型失败模式）"""),
        DUAL(
            "一个具体例子说明「落地层」是什么意思。C58 教了 repeat factor sampling、Focal Loss、copy-paste、主动学习触发——四个处理长尾的手段。<strong>但真实场景里你不会四个一起上</strong>：你要先知道「尾部类现在的 AP 是多少、漏检是因为召回不足还是错分、样本量是 30 张还是 300 张」，才知道该上哪一个。<em>这个「先诊断再开方」的流程，C58 不教（它教药），C61 教（它教诊断）。</em>",
            "反过来说，<strong>C61 的方法论如果没有前八门课支撑，会退化成正确但无用的废话</strong>。「要做分桶评测」——按什么分桶？（C55 的失效模式四象限 + C57 的尺寸分层给出维度）。「要做消融」——消融哪些组件？（C56 的增强算子 + C53 的分配策略给出候选）。「要归因」——候选原因有哪些？（C60 的三层鸿沟 + C58 的数据问题类型给出清单）。<em>方法论的价值与它所依赖的领域知识密度成正比</em>，这也是为什么本课的每一个模块都会大量回引前八门课的具体结论。",
        ),
        CALLOUT("warn", "学习顺序上的一个建议：<strong>不要等 C53–C60 全部学完再来学 C61</strong>。更有效的方式是先把本模块和 m01（实验设计）过一遍，建立「任何结论都要问怎么验证的」这个反射，再去学前八门课——这样你读每一个「这个方法涨了 X 点」的结论时，会自动去找它的实验条件。<em>本课的 m02（误差分析）和 m05（面试演练）则适合放到最后。</em>"),
    ])),

    # ============================================================== 6
    ("interview-dims", "面试评估的真实维度：面试官在打什么分", "".join([
        P("最后把视角切到面试。理解面试官的评分维度，比多背十篇论文有用——因为它决定了你同样的知识该<strong>怎么组织输出</strong>。"),
        P("一个成熟的检测岗面试官，本质上在估计一个量：<strong>「把一个检测模块交给这个人独立负责，出事的概率有多大」</strong>。所有问题都是这个估计的探针。"),
        TABLE(["评估维度", "面试官怎么探", "满分信号", "不及格信号"], [
            ["<strong>基础扎实度</strong>", "白板写 IoU / NMS / mAP；追问边界情况", "边界情况主动处理（无交集、包含、score 相同、空输入），并说明为什么这么处理", "能写主干但边界全错；或写不出来只能描述"],
            ["<strong>机制理解 vs 名词记忆</strong>", "「DETR 为什么不需要 NMS」「RT-DETR 凭什么快」", "能把机制拆成独立的部件并各自解释（如「无 NMS 来自一对一分配，与 Transformer 无关，YOLOv10 也做到了」）", "复述论文摘要；说不出「不用它会怎样」"],
            ["<strong>指标意识</strong>", "「这个改动涨了多少」「+0.3 算提升吗」", "报区间不报点估计；主动说分桶；主动说代价；<strong>知道 +0.3 可能是噪声并说得出为什么</strong>", "报一个精确数字但说不清评测口径"],
            ["<strong>归因能力</strong>", "「线上某类标志漏检，怎么排查」「INT8 掉 3 个点怎么办」", "给出<em>能砍掉一半候选</em>的第一个检查，而不是一串固定清单", "背诵式的排查步骤，顺序与信息量无关"],
            ["<strong>工程成熟度</strong>", "「你怎么保证这个对比是公平的」「讲一次失败的实验」", "主动提代价、回滚、妥协、没成功的尝试", "全是成功故事；从不提代价"],
            ["<strong>领域适配</strong>", "「TSR 和通用检测有什么不同」「水平翻转有什么坑」", "能把通用知识翻译到 TSR 的物理约束上（像素尺寸、颜色语义、代价不对称）", "把 COCO 的经验直接搬过来"],
        ]),
        P("这六个维度里，<strong>指标意识与归因能力是区分度最高的两项</strong>——因为它们无法靠短期背诵获得，也最能反映真实的工程经历。这正是本课把 m01（实验设计与归因）和 m02（误差分析）放在最前面的原因。"),
        DUAL(
            "有一个很实际的推论：<strong>如果你没有真实的车载项目经历，最有效的补偿不是编经历，而是把方法论讲到无懈可击</strong>。面试官分得清「做过」和「没做过」，但他更在意「你知不知道该怎么做」。一个诚实的回答——「我没有量产 TSR 的经历，但如果让我设计这个评测体系，我会这样做：……（然后给出分桶维度、门禁规则、代价不对称的处理）」——比一个编造的项目安全得多，也有效得多。",
            "反过来，<strong>把课程项目讲成生产项目是最容易被戳穿的策略</strong>。追问模式非常固定：「你的评测集有多少帧？」「误报率是每公里多少次？」「上线后回滚过吗？」——这些数字编不出来，因为它们之间有约束关系（帧数、目标数、FP/km、评测集构成必须自洽）。<em>更安全也更强的做法是把课程项目<strong>如实</strong>讲，但把方法论讲满</em>：「这是一个合成数据上的实验，规模是 XX，我知道它和量产的差距在 YY，如果拿到真实数据我会先做 ZZ。」<strong>这个回答同时展示了诚实、规模感和方法论——三个都是加分项。</strong>",
        ),
        CALLOUT("intuition", "把整门课的目标压成一句：<strong>让你在被追问三层之后，答案依然有内容。</strong>第一层（是什么）靠记忆，第二层（为什么）靠理解，<em>第三层（你怎么知道 / 代价是什么 / 不用它会怎样）靠的就是本课教的三个能力</em>。面试的胜负基本都在第三层分出来。"),
    ])),

    # ============================================================== 7
    ("frontier", "研究前沿与开放问题", "".join([
        P("本课的主题——实验方法、归因、可复现——在学术界正处在一轮认真的反思中。以下几条既是开放问题，也是很好的面试谈资。"),
        UL([
            "<strong>机器学习的可复现性危机。</strong>大量被广泛引用的「改进」在受控重复实验下无法复现，或者提升完全落在种子方差内。Bouthillier 等人的工作系统地量化了 benchmark 里的方差来源（数据划分、初始化、数据顺序、超参搜索），结论相当刺耳：<em>许多论文报告的差距小于它们自身的方差</em>。这直接支撑了本课 m01 的核心主张。",
            "<strong>检测任务的显著性检验几乎是空白。</strong>NLP 有 Dodge 等人推动的「报告预算与期望最大值」规范，RL 有 Henderson 等人的多种子呼吁，<em>而检测领域至今主流做法仍是单种子单次 COCO mAP</em>。原因很现实：一次 COCO 训练要几十 GPU-小时，跑 10 个种子的成本无法接受。<strong>「在训练成本高到做不起重复实验时，如何得到可信结论」是一个真正的开放问题</strong>——目前的替代方案（分桶一致性、跨数据集一致性、机制解释）都只是弱证据。",
            "<strong>Benchmark 过拟合与评测集老化。</strong>同一个测试集被社区反复使用多年后，报告的提升有多少来自对该测试集的隐性过拟合？Recht 等人在 ImageNet/CIFAR 上的重采样实验给出了量化答案（新测试集上准确率普遍下降，但排序基本保持）。<em>对 TSR 而言这个问题更尖锐，因为评测集通常来自与训练集同一批采集，域内相关性远高于 ImageNet。</em>",
            "<strong>消融的归因理论。</strong>加法式与减法式消融给出不同结论已是共识，Shapley 值提供了公理化的公平归因，但代价是 $2^k$ 次实验。<em>如何在少量实验下估计交互作用（部分因子设计、代理模型、主动实验设计）在 ML 系统里应用得还很少</em>——而这是统计学里成熟了几十年的工具。",
            "<strong>自动化实验管理与「智能体做实验」。</strong>随着 agent 能自动改配置、跑训练、读指标，<em>「谁来保证单变量原则和统计严谨性」变成了一个系统设计问题</em>：自动化会把「试到显著为止」这种坏实践的速度放大几个数量级。多重比较校正、预注册（pre-registration）这类原本属于临床试验的做法，正在被重新讨论。",
            "<strong>评测与下游价值的脱节。</strong>mAP 涨了，路测体验没变——这在自动驾驶里是常态（C55 m05 展开）。<em>如何设计与下游安全收益对齐的离线指标，仍然没有公认答案</em>；代价敏感指标、场景加权 mAP、违规率代理都各有缺陷。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Bouthillier et al., <em>Accounting for Variance in Machine Learning Benchmarks</em>（MLSys 2021）——把 benchmark 方差按来源分解并给出「该跑多少次」的实用建议，是本课 m01 的直接理论基础。<strong>★</strong> Dodge et al., <em>Show Your Work: Improved Reporting of Experimental Results</em>（EMNLP 2019）——「报告调参预算与期望最大值曲线」这个规范的源头，解决的是「新方法调了 200 组、baseline 用默认值」的不公平。<strong>★</strong> Henderson et al., <em>Deep Reinforcement Learning that Matters</em>（AAAI 2018）——多种子、方差、报告规范的经典警世之作，结论在检测领域同样成立。</p><p>延伸：Pineau et al., <em>Improving Reproducibility in Machine Learning Research</em>（JMLR 2021，ML Reproducibility Checklist 的来源）；Lipton &amp; Steinhardt, <em>Troubling Trends in Machine Learning Scholarship</em>（2018）；Recht et al., <em>Do ImageNet Classifiers Generalize to ImageNet?</em>（ICML 2019）；Musgrave et al., <em>A Metric Learning Reality Check</em>（ECCV 2020，「公平对比后大部分提升消失」的实证）；Bolya et al., <em>TIDE: A General Toolbox for Identifying Object Detection Errors</em>（ECCV 2020，模块 02 的主线）。相邻课程：C40（研究方法论）、C37（MLOps 与实验追踪）、C10（评测测量）、C55 m05（安全导向评测）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（指标意识自测 / 归因信息增益 / run manifest 校验）

目标：把本课的三个核心能力**各做成一段可运行的代码**，而不是三句口号。
跑完这个 notebook，你会得到一份自己的「指标意识」得分，和三个可以直接搬进项目的小工具。

本 notebook 你会亲手实现：
1. **环境自检**：确认纯 numpy + 标准库环境可用，且**同种子同结果**（本课全部实验的前提）
2. **指标换算器**：TP/FP/FN → precision / recall / F1 / **FP per km**
   —— 并算出「precision 0.90 在车上意味着每公里 54 次误报」
3. **指标意识自测**：14 条真实改动，你先猜影响量级，再对照经验区间打分
4. **ROI 与帕累托前沿**：每个改动的收益/代价比，找出「零延迟代价的免费改进」
5. **归因的信息增益**：把「下一步该做哪个检查」变成一个可计算的量（$\\mathrm{IG}=H_b(m)$）
6. **run manifest 校验器**：缺任何一个必需字段就拒绝这次 run

> 心智模型：**指标意识 = 改动前能给出区间；归因 = 知道下一个检查做什么；
> 交付纪律 = 任意历史状态可重建。三者都能写成代码。**"""),

    md("""## 1 · 环境自检：本课不需要 GPU，但需要确定性"""),

    code("""import sys, math, json, platform
import numpy as np

print('python  :', sys.version.split()[0])
print('numpy   :', np.__version__)
print('platform:', platform.platform())
assert sys.version_info >= (3, 8), '需要 Python 3.8+'

# 本课全部实验的前提：**同种子同结果**。做不到这一点，后面所有对比都无意义。
a = np.random.default_rng(7).normal(size=5)
b = np.random.default_rng(7).normal(size=5)
c = np.random.default_rng(8).normal(size=5)
print('\\nrng(7) 第一次:', np.round(a, 6))
print('rng(7) 第二次:', np.round(b, 6))
print('rng(8)       :', np.round(c, 6))
assert np.array_equal(a, b), '同种子必须完全相同'
assert not np.allclose(a, c), '不同种子必须不同（否则种子没起作用）'

rng = np.random.default_rng(20260817)   # 全 notebook 统一入口
print('\\n✅ 环境就位：纯 numpy + 标准库，CPU 可跑，无需联网。')
print('   注意 np.random.default_rng(seed) 与全局 np.random.seed 是两套状态 ——')
print('   真实项目里必须同时固定：python random / numpy / torch / cudnn.deterministic。')"""),

    md("""## 2 · 指标换算器：precision 0.90 在车上是什么意思

整体 precision / recall 是**离线**语言。车端能行动的语言是
**每公里误报次数（FP/km）** 与 **首次检出距离**。两者之间只差一个换算，
但换算完的数字常常让人重新认识自己的模型。"""),

    code("""def metrics_from_counts(tp, fp, fn, n_frames):
    '''最小指标闭包：从三个计数出发，得到所有常用量。'''
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return dict(precision=prec, recall=rec, f1=f1,
                miss_rate=1 - rec, fp_per_frame=fp / n_frames)

def frames_per_km(fps, speed_kmh):
    '''以 speed_kmh 行驶 1 km，相机吐出多少帧。'''
    return fps * 3600.0 / speed_kmh

def fp_per_km(fp_per_frame, fps=30, speed_kmh=100):
    return fp_per_frame * frames_per_km(fps, speed_kmh)

# 一个"看起来还行"的 TSR 评测结果
TP, FP, FN, N_FRAMES = 900, 100, 100, 2000
m = metrics_from_counts(TP, FP, FN, N_FRAMES)
print(f"TP={TP}  FP={FP}  FN={FN}  帧数={N_FRAMES}")
for k, v in m.items():
    print(f'  {k:<14s} {v:.4f}')
assert abs(m['precision'] - 0.9) < 1e-12 and abs(m['recall'] - 0.9) < 1e-12
assert abs(m['f1'] - 0.9) < 1e-12
assert abs(m['fp_per_frame'] - 0.05) < 1e-12

fpk = fp_per_km(m['fp_per_frame'], fps=30, speed_kmh=100)
print(f"\\n30 FPS、100 km/h -> 每公里 {frames_per_km(30,100):.0f} 帧")
print(f"precision 0.90  ==>  **每公里 {fpk:.0f} 次误报**")
assert abs(frames_per_km(30, 100) - 1080.0) < 1e-9
assert abs(fpk - 54.0) < 1e-9
print('\\n⚠️  离线看是"90% 精确率，还不错"；换算到车上是**每公里 54 次误报** —— 完全不可上线。')"""),

    code("""# 反过来问：要做到「每公里 <= 1 次误报」，precision 需要多少？
def precision_for_fp_budget(tp, n_frames, fp_per_km_budget, fps=30, speed_kmh=100):
    fpf_budget = fp_per_km_budget / frames_per_km(fps, speed_kmh)
    fp_allowed = fpf_budget * n_frames
    return tp / (tp + fp_allowed), fp_allowed

for budget in [10.0, 5.0, 1.0, 0.2]:
    p, fp_allowed = precision_for_fp_budget(TP, N_FRAMES, budget)
    print(f'FP/km <= {budget:>5.1f}  ->  评测集里最多 {fp_allowed:6.2f} 个 FP  ->  precision >= {p:.5f}')

p1, fp1 = precision_for_fp_budget(TP, N_FRAMES, 1.0)
assert abs(fp1 - 2000 / 1080) < 1e-9, fp1          # 1/1080 * 2000
assert p1 > 0.997, p1
print(f'\\n✅ 目标 1 FP/km 对应 precision >= {p1:.4f} —— 从 0.90 到 0.998，')
print('   FP 要从 100 降到 1.85 个，是 **54 倍**的差距，不是"再调调阈值"能到的。')
print('\\n📌 TSR 落点：这就是为什么量产 TSR 必须用**时序多帧确认 + 迟滞**（C55 m04）——')
print('   单帧 precision 到不了 0.998，但"连续 3 帧一致才上报"能把独立误报压掉 2 个数量级。')"""),

    md("""## 3 · 「指标意识」自测

下面是 14 条真实的检测改动。**先自己在心里给出一个数**（对哪个指标、涨/掉多少），
再运行打分 cell 对照经验区间。

区间是「经验量级」不是「定律」：它依赖数据分布、训练预算、模型容量。
**报区间而不报点估计，本身就是指标意识的一部分。**"""),

    code("""# 经验量级表（教学用；量级与公开论文/工程实践一致，不是精确复现某一篇）
# delta_lo / delta_hi：对"目标指标"的影响区间（单位：AP 点）
# dlat_ms：相对 baseline(9.0 ms) 的延迟增量
CHANGES = [
    dict(id='res',      name='输入分辨率 640 -> 1280',              metric='mAP_small', lo= 3.0, hi= 6.0,  dlat_ms=22.5, conf='高'),
    dict(id='p2',       name='FPN 加 P2 层 (stride 4)',             metric='mAP_small', lo= 1.5, hi= 4.0,  dlat_ms= 3.0, conf='高'),
    dict(id='mosaic',   name='Mosaic + 末 10 epoch 关闭',           metric='mAP',       lo= 0.8, hi= 2.0,  dlat_ms= 0.0, conf='高'),
    dict(id='cp',       name='稀有类 copy-paste',                   metric='尾部类 AP', lo= 3.0, hi=15.0,  dlat_ms= 0.0, conf='中'),
    dict(id='backbone', name='backbone R50 -> R101',                metric='mAP',       lo= 1.0, hi= 2.0,  dlat_ms= 3.6, conf='高'),
    dict(id='epochs',   name='训练 12 -> 36 epoch',                 metric='mAP',       lo= 1.5, hi= 3.0,  dlat_ms= 0.0, conf='高'),
    dict(id='assign',   name='标签分配 MaxIoU -> TaskAligned',      metric='mAP',       lo= 1.0, hi= 2.5,  dlat_ms= 0.0, conf='高'),
    dict(id='nwd',      name='小目标度量 IoU -> NWD',               metric='mAP_small', lo= 1.0, hi= 3.0,  dlat_ms= 0.0, conf='中'),
    dict(id='nmsthr',   name='NMS IoU 阈值 0.50 -> 0.45',           metric='mAP',       lo=-0.2, hi= 0.2,  dlat_ms= 0.0, conf='低'),
    dict(id='gamma',    name='Focal gamma 2.0 -> 1.5',              metric='mAP',       lo=-0.3, hi= 0.3,  dlat_ms= 0.0, conf='低'),
    dict(id='int8ok',   name='INT8 PTQ（校准集覆盖长尾场景）',      metric='mAP',       lo=-1.0, hi=-0.3,  dlat_ms=-5.0, conf='高'),
    dict(id='int8bad',  name='INT8 PTQ（校准集全是白天晴天）',      metric='夜间桶 AP', lo=-15.0,hi=-5.0,  dlat_ms=-5.0, conf='高'),
    dict(id='hflip',    name='水平翻转增强（含左转/右转标志）',      metric='方向类 AP', lo=-20.0,hi=-5.0,  dlat_ms= 0.0, conf='高'),
    dict(id='tta',      name='TTA：多尺度 + 翻转 + WBF 融合',        metric='mAP',       lo= 0.5, hi= 1.5,  dlat_ms=27.0, conf='高'),
]
BASE_LAT = 9.0

def span_str(c):
    return '[%+.1f, %+.1f]' % (c['lo'], c['hi'])

print(f"{'改动':<34s} {'目标指标':<12s} {'经验区间(AP)':>16s} {'Δ延迟ms':>9s} {'置信'}")
for c in CHANGES:
    print(f"{c['name']:<34s} {c['metric']:<12s} {span_str(c):>16s} "
          f"{c['dlat_ms']:>9.1f} {c['conf']:>4s}")

n_free_lat = sum(1 for c in CHANGES if c['dlat_ms'] <= 0)
assert len(CHANGES) == 14
assert n_free_lat == 10, n_free_lat
print(f"\\n✅ 14 条改动里，延迟代价 <= 0 的有 **{n_free_lat}** 条；")
print('   其中收益为正的才是真正的「免费改进」（下一节算出来是 5 条）。')
print('⚠️  注意 nmsthr 与 gamma 的区间是 [-0.2,+0.2] / [-0.3,+0.3] —— **跨零**，')
print('    意思是「这类改动的效果与种子噪声同量级」。模块 01 会把这句话变成一个检验。')"""),

    code("""def grade_guess(guess, lo, hi):
    '''打分规则（在**幅度空间**里放宽，这样正负区间对称处理）：
       命中   —— guess 落在经验区间内
       量级对 —— 方向一致，且幅度在 [0.5*min|区间|, 2*max|区间|] 内
       量级错 —— 其余（含方向反了）'''
    if lo <= guess <= hi:
        return '命中'
    if guess * (lo + hi) <= 0:                 # 方向不一致
        return '量级错'
    g = abs(guess)
    lo_m, hi_m = min(abs(lo), abs(hi)), max(abs(lo), abs(hi))
    return '量级对' if 0.5 * lo_m <= g <= 2.0 * hi_m else '量级错'

# 手算校验
assert grade_guess(2.0, 1.5, 4.0) == '命中'
assert grade_guess(5.0, 1.5, 4.0) == '量级对'      # 幅度 5 在 [0.75, 8] 内，方向同号
assert grade_guess(9.0, 1.5, 4.0) == '量级错'      # 幅度超过 2*4.0=8
assert grade_guess(-1.0, 1.5, 4.0) == '量级错'     # 方向反了
assert grade_guess(-0.4, -1.0, -0.3) == '命中'
assert grade_guess(-2.0, -15.0, -5.0) == '量级错'  # 方向对但幅度只有下界的 0.4 倍

# —— 一份"考生答卷"（把这里换成你自己的猜测，重跑本 cell）——
MY_GUESS = {'res': 4.0, 'p2': 2.5, 'mosaic': 1.2, 'cp': 8.0, 'backbone': 1.5,
            'epochs': 2.0, 'assign': 1.8, 'nwd': 2.0, 'nmsthr': 0.0, 'gamma': 0.1,
            'int8ok': -0.5, 'int8bad': -2.0, 'hflip': -1.0, 'tta': 1.0}

score = {'命中': 0, '量级对': 0, '量级错': 0}
print(f"{'改动':<34s} {'你的猜测':>9s} {'经验区间':>16s}  判定")
for c in CHANGES:
    g = MY_GUESS[c['id']]
    r = grade_guess(g, c['lo'], c['hi'])
    score[r] += 1
    print(f"{c['name']:<34s} {g:>+9.1f} {span_str(c):>16s}  {r}")
total = 2 * score['命中'] + 1 * score['量级对']
print(f"\\n得分 {total} / {2*len(CHANGES)}   命中 {score['命中']} · 量级对 {score['量级对']} · 量级错 {score['量级错']}")
assert score['命中'] + score['量级对'] + score['量级错'] == 14
assert score['量级错'] >= 2, '这份示例答卷刻意错了 int8bad 与 hflip 两项'
print('\\n⚠️  示例答卷错在 **int8bad(-2.0)** 与 **hflip(-1.0)**：都低估了「分桶指标」的剧烈程度。')
print('    这正是最常见的指标意识缺口 —— 用整体 mAP 的直觉去猜分桶指标，')
print('    而分桶指标的样本少、场景集中，波动幅度大一个数量级。')"""),

    md("""## 4 · ROI 与免费改进：把代价写下来

$$\\mathrm{ROI} = \\frac{\\Delta \\mathrm{AP}}{\\Delta T / T_0}, \\qquad
\\text{「必做项」} \\iff \\Delta T \\le 0 \\;\\wedge\\; \\Delta \\mathrm{AP} > 0$$"""),

    code("""def mid(c):  return 0.5 * (c['lo'] + c['hi'])

def roi(c, base_lat=BASE_LAT):
    '''收益/代价比。延迟代价 <= 0 的改动没有分母 -> 记为 inf（免费改进）。'''
    d = c['dlat_ms'] / base_lat
    if d <= 0:
        return float('inf') if mid(c) > 0 else float('-inf')
    return mid(c) / d

free_wins = [c for c in CHANGES if c['dlat_ms'] <= 0 and mid(c) > 0]
costly    = [c for c in CHANGES if c['dlat_ms'] > 0]

print('【免费改进】ΔT <= 0 且 ΔAP > 0 —— 不消耗延迟预算，应无条件先做')
for c in sorted(free_wins, key=mid, reverse=True):
    print(f"  {c['name']:<34s} {mid(c):+6.2f} AP  ({c['metric']})")
assert {c['id'] for c in free_wins} == {'mosaic', 'cp', 'epochs', 'assign', 'nwd'}, \\
    [c['id'] for c in free_wins]

print('\\n【要花延迟预算的改动】按 ROI 排序')
print(f"  {'改动':<34s} {'ΔAP':>7s} {'Δ延迟':>8s} {'相对延迟':>9s} {'ROI':>8s}")
for c in sorted(costly, key=roi, reverse=True):
    print(f"  {c['name']:<34s} {mid(c):>+7.2f} {c['dlat_ms']:>+8.1f} "
          f"{c['dlat_ms']/BASE_LAT:>8.1%} {roi(c):>8.2f}")

assert roi(next(c for c in CHANGES if c['id'] == 'p2')) > \\
       roi(next(c for c in CHANGES if c['id'] == 'tta')), 'P2 的 ROI 应远高于 TTA'
print('\\n✅ TTA 的 ROI 垫底（+1.0 AP 换 3 倍延迟）—— **车端基本不可用**，')
print('   但它在离线打标 / 生成伪标签时非常有用。同一个改动，语境不同结论相反。')
print('📌 面试点：被问「你会怎么提升 TSR 的 mAP」时，**先把免费改进列完再谈架构**，')
print('   这个顺序本身就是「知道延迟是预算」的信号。')"""),

    md("""## 5 · 归因：把「下一步查什么」变成可计算的量

**关键等式**：一个把候选原因按概率质量 $m$ / $1-m$ 切成两块的二值检查，
其信息增益恰好等于 $H_b(m)$ —— 与候选集内部的分布无关。
所以**最优检查 = 把质量切得最接近 50/50 的那一个**。"""),

    code("""def entropy(ps):
    ps = [p for p in ps if p > 0]
    return -sum(p * math.log2(p) for p in ps)

def h_binary(m):
    if m <= 0 or m >= 1:
        return 0.0
    return -m * math.log2(m) - (1 - m) * math.log2(1 - m)

# 症状：mAP 恒为 0，但 loss 正常下降。候选原因与先验（来自历史事故统计）
CAUSES = {
    '类别 ID 偏移 0/1':          0.35,
    '坐标格式弄反 xywh<->xyxy':  0.25,
    '评测集与训练集类别表不一致': 0.15,
    '学习率过大导致框全发散':     0.10,
    '标注坐标未随 resize 缩放':   0.10,
    '数据没打乱（每 batch 单类）': 0.05,
}
assert abs(sum(CAUSES.values()) - 1.0) < 1e-12

# 每个检查 -> 它为"真"时能确认的原因子集
CHECKS = {
    'A. 把 GT 当预测送进评测器，看 mAP 是否 = 1.0':
        {'类别 ID 偏移 0/1', '坐标格式弄反 xywh<->xyxy',
         '评测集与训练集类别表不一致', '标注坐标未随 resize 缩放'},
    'B. 打印前 20 个预测框，看坐标范围是 [0,1] 还是像素':
        {'坐标格式弄反 xywh<->xyxy', '标注坐标未随 resize 缩放'},
    'C. 看 loss 曲线 3 个 epoch 后是否仍在降':
        {'学习率过大导致框全发散', '数据没打乱（每 batch 单类）'},
    'D. 统计一个 batch 里的类别数是否 > 1':
        {'数据没打乱（每 batch 单类）'},
    'E. 打印训练与评测两侧的 class_id -> name 映射表':
        {'类别 ID 偏移 0/1', '评测集与训练集类别表不一致'},
}

def info_gain(causes, subset):
    m = sum(p for k, p in causes.items() if k in subset)
    return m, h_binary(m)

H0 = entropy(list(CAUSES.values()))
print(f'先验熵 H0 = {H0:.4f} bit（{len(CAUSES)} 个候选，均匀时是 {math.log2(len(CAUSES)):.4f}）\\n')
print(f"{'检查':<48s} {'切出质量 m':>11s} {'IG (bit)':>10s}")
rows = []
for name, sub in CHECKS.items():
    m_, ig = info_gain(CAUSES, sub)
    rows.append((ig, m_, name))
    print(f'{name:<48s} {m_:>11.2f} {ig:>10.4f}')

best_ig, best_m, best_name = max(rows)
# 与"最接近 50/50"的检查一致 —— 这是 IG = H_b(m) 的直接推论
closest = min(rows, key=lambda r: abs(r[1] - 0.5))
assert best_name == closest[2], (best_name, closest[2])
assert abs(best_ig - h_binary(best_m)) < 1e-12
assert best_name.startswith('E'), best_name
print(f'\\n▶ 最优首查：{best_name}（m={best_m:.2f}, IG={best_ig:.4f} bit）')
print(f'▶ 直觉上"最全面"的检查 A 切出 m=0.85，IG 只有 {h_binary(0.85):.4f} bit ——')
print('  它几乎总是给同一个答案，做完候选集还是那么大。')
print('\\n✅ 心法：**检查的价值由判别性决定，不由覆盖面决定**（和二分查找是同一个道理）。')"""),

    md("""## 6 · 交付纪律：run manifest 校验器

规则很简单：**缺任何一个必需字段，这次 run 就不算数**。
把它放进训练脚本的最后一步，「存在一个 manifest」就等价于「这次实验可复现」。"""),

    code("""REQUIRED = [
    ('run_id',       lambda v: isinstance(v, str) and len(v) > 0),
    ('code.commit',  lambda v: isinstance(v, str) and len(v) >= 7),
    ('code.dirty',   lambda v: v is False),              # ← True 直接判不可复现
    ('data.train',   lambda v: isinstance(v, str) and len(v) > 0),
    ('data.val',     lambda v: isinstance(v, str) and len(v) > 0),
    ('config_hash',  lambda v: isinstance(v, str) and len(v) >= 6),
    ('env.python',   lambda v: isinstance(v, str)),
    ('env.gpu',      lambda v: isinstance(v, str)),
    ('seed',         lambda v: isinstance(v, int)),      # None 不行
    ('metrics.mAP',  lambda v: isinstance(v, (int, float))),
    ('metrics.by_size',  lambda v: isinstance(v, dict) and len(v) >= 3),   # 分桶必须有
    ('metrics.by_light', lambda v: isinstance(v, dict) and len(v) >= 2),
]

def dig(d, dotted):
    cur = d
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True

def validate_manifest(mf):
    '''返回 (ok, 问题列表)。问题分两类：missing（缺字段）/ invalid（有但不合规）。'''
    problems = []
    for key, rule in REQUIRED:
        val, present = dig(mf, key)
        if not present:
            problems.append(('missing', key))
        elif not rule(val):
            problems.append(('invalid', f'{key}={val!r}'))
    return (len(problems) == 0), problems

GOOD = {
    'run_id': '2026-08-17_tsr_p2head_s0',
    'code': {'commit': 'd41d8cd98f00b204', 'dirty': False, 'repo': 'perception/tsr'},
    'data': {'train': 'tsr_v7.2', 'val': 'tsr_eval_v3 (frozen 2026-06-01)'},
    'config_hash': 'a3f5c1e9',
    'env': {'python': '3.11.9', 'numpy': '1.26.4', 'gpu': 'A100-80G', 'driver': '550.54'},
    'seed': 0,
    'metrics': {'mAP': 0.8213, 'mAP50': 0.9410,
                'by_size': {'<16px': 0.412, '16-32': 0.701, '32-64': 0.868, '>64': 0.912},
                'by_light': {'day': 0.851, 'night': 0.674, 'backlit': 0.612},
                'fp_per_km': 0.83, 'latency_p99_ms': 9.2},
    'artifacts': {'ckpt': 's3://.../best.pth'},
}
BAD = json.loads(json.dumps(GOOD))          # 深拷贝后制造三个典型问题
BAD['code']['dirty'] = True                 # ① 工作区脏 -> 不可复现
BAD['seed'] = None                          # ② 没记种子 -> 无法做对照
del BAD['metrics']['by_light']              # ③ 只存了整体指标 -> 分桶对比永久失效

for label, mf in [('GOOD', GOOD), ('BAD', BAD)]:
    ok, probs = validate_manifest(mf)
    print(f'{label}: {"✅ 通过" if ok else "❌ 拒绝"}')
    for kind, detail in probs:
        print(f'    [{kind}] {detail}')

ok_g, _ = validate_manifest(GOOD)
ok_b, probs_b = validate_manifest(BAD)
assert ok_g, '完整 manifest 应通过'
assert not ok_b and len(probs_b) == 3, probs_b
assert ('invalid', 'code.dirty=True') in probs_b
assert ('missing', 'metrics.by_light') in probs_b
print('\\n✅ 三个问题各自对应一类事故：')
print('   dirty=True   -> 这份代码在世界上任何地方都不存在，永久不可复现')
print('   seed=None    -> 无法判断后续对比里的差异是改动还是噪声（m01 全模块的主题）')
print('   缺 by_light  -> 存储成本几 KB，重建成本是重跑一次评测（如果还建得出来）')"""),

    md("""## ✏️ 练习 1：FP/km 与工作点反推

实现两个函数：
- `fp_per_km_from_precision(tp, fp, n_frames, fps, speed_kmh)` → 每公里误报次数
- `min_precision_for(tp, n_frames, budget_fp_km, fps, speed_kmh)` → 达到该 FP/km 预算所需的最小 precision

提示：`frames_per_km = fps * 3600 / speed_kmh`；`fp_allowed = budget/frames_per_km * n_frames`。"""),

    code("""def fp_per_km_from_precision(tp, fp, n_frames, fps=30, speed_kmh=100):
    # TODO
    raise NotImplementedError

def min_precision_for(tp, n_frames, budget_fp_km, fps=30, speed_kmh=100):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
assert abs(fp_per_km_from_precision(900, 100, 2000) - 54.0) < 1e-9
assert abs(fp_per_km_from_precision(900, 0, 2000) - 0.0) < 1e-12
# 车速减半 -> 每公里帧数翻倍 -> FP/km 翻倍
assert abs(fp_per_km_from_precision(900, 100, 2000, speed_kmh=50) - 108.0) < 1e-9
p = min_precision_for(900, 2000, 1.0)
assert abs(p - 900 / (900 + 2000 / 1080)) < 1e-12, p
assert min_precision_for(900, 2000, 0.2) > min_precision_for(900, 2000, 5.0)
for b in [10, 1, 0.2]:
    print(f'FP/km <= {b:>5}: precision >= {min_precision_for(900, 2000, b):.5f}')
print('✅ 练习 1 通过：**离线 precision 与车端 FP/km 之间差一个 1080 倍的换算**，')
print('   不做这个换算，就永远不知道自己离可上线有多远。')"""),

    md("""## ✏️ 练习 2：帕累托前沿

实现 `pareto_front(items)`：`items` 是 `[(名字, 收益, 代价), ...]`。
若存在另一项 **收益 >= 且 代价 <=**，且至少一项严格更优，则本项被**支配**，应剔除。
返回未被支配的项，按代价升序。"""),

    code("""def pareto_front(items):
    # TODO: items = [(name, gain, cost), ...] -> 未被支配的子集，按 cost 升序
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测（手算）——
demo = [('a', 2.0, 1.0), ('b', 1.0, 1.0), ('c', 3.0, 5.0), ('d', 2.0, 3.0), ('e', 2.0, 1.0)]
front = pareto_front(demo)
names = sorted(n for n, _, _ in front)
# b 被 a 支配（同代价更低收益）；d 被 a 支配（同收益更高代价）
# a 与 e 完全相同 -> 互不严格支配，两者都保留
assert names == ['a', 'c', 'e'], names
assert [c for _, _, c in front] == sorted(c for _, _, c in front), '要按 cost 升序'
assert pareto_front([]) == [] or list(pareto_front([])) == []

real = [(c['name'], mid(c), c['dlat_ms']) for c in CHANGES if c['dlat_ms'] > 0]
for n, g, c_ in pareto_front(real):
    print(f'{n:<34s} 收益 {g:+5.2f} AP   代价 {c_:+5.1f} ms')
assert any('P2' in n for n, _, _ in pareto_front(real)), 'P2 应在前沿上'
print('✅ 练习 2 通过：前沿之外的改动**没有讨论价值** —— 存在一个各方面都不差的替代。')"""),

    md("""## ✏️ 练习 3：最优首查

实现 `best_check(causes, checks)`：返回 `(检查名, 切出质量 m, 信息增益)`，
取信息增益最大者（并列时取名字字典序最小的，保证结果确定）。
用 `IG = H_b(m)`，其中 `m` 是该检查覆盖的原因的**概率质量之和**。"""),

    code("""def best_check(causes, checks):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
name, m_, ig = best_check(CAUSES, CHECKS)
assert name.startswith('E'), name
assert abs(m_ - 0.50) < 1e-12, m_          # 0.35 + 0.15
assert abs(ig - 1.0) < 1e-12, ig           # H_b(0.5) = 1 bit，二值检查的上限
# 极端情形：检查覆盖全部原因 -> 零信息
allc = {'X': set(CAUSES)}
assert abs(best_check(CAUSES, allc)[2] - 0.0) < 1e-12
# 并列时取字典序最小
tie = {'B_check': {'类别 ID 偏移 0/1', '评测集与训练集类别表不一致'},
       'A_check': {'坐标格式弄反 xywh<->xyxy', '学习率过大导致框全发散',
                   '标注坐标未随 resize 缩放', '数据没打乱（每 batch 单类）'}}
assert best_check(CAUSES, tie)[0] == 'A_check', best_check(CAUSES, tie)
print(f'最优首查: {name}\\n  m = {m_:.2f}, IG = {ig:.4f} bit（二值检查的理论上限）')
print('✅ 练习 3 通过：**一次检查最多消掉 1 bit**，所以 6 个候选至少要 log2(6)=2.58 -> 3 次。')
print('   如果你的排查平均要 6 步，说明每一步都没在切一半。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def fp_per_km_from_precision(tp, fp, n_frames, fps=30, speed_kmh=100):
    return fp / n_frames * (fps * 3600.0 / speed_kmh)

def min_precision_for(tp, n_frames, budget_fp_km, fps=30, speed_kmh=100):
    fp_allowed = budget_fp_km / (fps * 3600.0 / speed_kmh) * n_frames
    return tp / (tp + fp_allowed)"""),

    code("""# 练习 2 参考答案
def pareto_front(items):
    out = []
    for i, (n, g, c) in enumerate(items):
        dominated = any(
            (g2 >= g and c2 <= c) and (g2 > g or c2 < c)
            for j, (_, g2, c2) in enumerate(items) if j != i
        )
        if not dominated:
            out.append((n, g, c))
    return sorted(out, key=lambda t: t[2])"""),

    code("""# 练习 3 参考答案
def best_check(causes, checks):
    best = None
    for name in sorted(checks):
        m = sum(p for k, p in causes.items() if k in checks[name])
        ig = h_binary(m)
        if best is None or ig > best[2] + 1e-15:
            best = (name, m, ig)
    return best"""),

    md("""---
## 🧪 真实工程胶囊：接手一个检测模块的第一周"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# 接手一个检测模块的第一周 —— 做完这 7 件事，你才算"能负责"
# （顺序是刻意的：先建立可观测性，再动模型）
# ══════════════════════════════════════════════════════════════════════

# ① 冻结一个评测集，并给它一个版本号
#    - 从此这个集合**只增不改**；改了就是新版本，历史数字全部作废
#    - 单独存一份 frozen 副本（不要只存一个 git 分支名）
#    $ sha256sum eval_v3.json > eval_v3.sha256
#    通过条件：任何人任何时间跑同一个 ckpt，得到完全相同的 mAP

# ② 把评测输出从"一个 mAP"改成"一张分桶表"
#    维度至少四个（来自 C55 失效模式 + C57 尺寸分层）：
#      size   : <16px / 16-32 / 32-64 / >64          ← TSR 的第一诊断维度
#      light  : day / night / backlit / tunnel
#      weather: clear / rain / fog / snow
#      class  : 全类别 AP + 关键类单列（stop / yield / speed_limit_*）
#    再加两个工程指标：fp_per_km、latency_p50/p99
#    通过条件：任意一次评测，能在 10 秒内回答"掉点掉在哪个桶"

# ③ 跑 baseline 的**多种子**（至少 3 个），把种子方差量出来
#    for s in 0 1 2; do train.py --seed $s --tag base_s$s; done
#    记录每个桶的 std。**这个数字是你之后所有"提升"的判据**（模块 01）
#    通过条件：你能说出"本项目 mAP 的种子标准差是 0.XX，所以 <0.YY 的差异不予采信"

# ④ 给每次 run 落 manifest（本 notebook 第 6 节的校验器）
#    训练脚本最后一步：validate_manifest(mf) 不过就不写产物
#    通过条件：随机抽一个 30 天前的 run，能从 manifest 重跑并落回方差区间

# ⑤ 建回归门禁（先建规则，再谈提升）
#    规则示例：新版本相对当前线上版本
#      · 任何桶的 AP 掉幅 > 2*std          -> 阻塞
#      · 关键类（stop/yield）掉任何点      -> 阻塞
#      · fp_per_km 上升 > 10%              -> 阻塞
#      · latency_p99 > budget              -> 阻塞
#    通过条件：门禁能自动跑，且**至少拦下过一次**（没拦过说明阈值太松）

# ⑥ 建 badcase 的分层抽样（不要"随便看几张"）
#    按 (桶 × 错误类型) 分层，每格抽 N 张，人工过一遍
#    通过条件：你能列出 top-5 失效模式，并给每个估计"修好能涨多少"（模块 02）

# ⑦ 演练一次回滚
#    随机挑一个历史版本，计时看多久能切回线上
#    通过条件：< 30 分钟，且不需要重新构建 engine

# ── 反模式（看到这些就说明前面某一步没做）────────────────────────────
#  · "这次涨了 0.4"          -> ③ 没做，不知道 0.4 是不是噪声
#  · "不知道为什么掉点了"     -> ② 没做，看不到分桶
#  · "上个季度那版怎么训的？" -> ④ 没做
#  · "先上了再说，掉点再回滚" -> ⑤⑦ 没做，回滚其实回不去
'''
print(RECIPE)
for token in ['冻结一个评测集', '分桶表', '多种子', 'manifest', '回归门禁',
              '分层抽样', '演练一次回滚', 'fp_per_km', 'latency_p99']:
    assert token in RECIPE, token
print('✅ 第一周检查单覆盖：可观测性(①②) -> 判据(③) -> 可复现(④) -> 门禁(⑤) -> 归因(⑥) -> 可回滚(⑦)')"""),

    md("""### 小结

- **「会跑通 → 能改进 → 能负责」的差距不是知识量**，是三个能力：
  **指标意识**（改动前能给出区间与代价）、**归因能力**（指标动了能定位）、
  **交付纪律**（可复现 / 可回滚 / 可交接）。
- **整体 mAP 是最不敏感的指标**。加 P2 在 mAP_small 上 +1.5~4.0，稀释到整体只剩 +0.6~1.6。
  被问「涨了多少」时，**正确答法是「涨在哪」**。
- **离线 precision 与车端 FP/km 差一个 1080 倍的换算**（30 FPS、100 km/h）：
  precision 0.90 = **每公里 54 次误报**；要压到 1 FP/km 需要 precision 0.998。
  单帧做不到，所以量产 TSR 必须靠**时序确认 + 迟滞**。
- **把改动分成「免费的」和「要花延迟预算的」两类**。14 条改动里有 5 条延迟代价 ≤ 0
  （Mosaic / copy-paste / 延长训练 / 换标签分配 / 换小目标度量）——它们是帕累托改进，
  应无条件先做。TTA 的 ROI 垫底（+1.0 AP 换 3 倍延迟），车端不可用。
- **归因 = 挑判别性最强的检查，不是挑覆盖面最大的**。二值检查的信息增益
  $\\mathrm{IG}=H_b(m)$ 只由它切出的概率质量决定，上限 1 bit ——
  所以 6 个候选原因至少需要 3 次检查，平均要 6 步说明每步都没在切一半。
- **manifest 是可复现的最小实现**：commit + dirty + 数据版本 + 配置 + 环境 + 种子 + **全量指标**。
  `dirty=True` 是红线；`metrics` 只存 mAP 会让历史分桶对比永久失效。

下一站：**模块 01 · 实验设计与归因** —— 种子方差有多大、+0.3 到底算不算提升、
以及「需要多少个种子才能检出它」。"""),
]
