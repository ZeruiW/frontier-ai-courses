# -*- coding: utf-8 -*-
"""C59 模块 03 · TSR 输出如何进入 VLA：接口设计。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 01–02（VLA 结构与动作头）；C55（TSR 系统与失效模式）；C58 模块 03（不确定性触发）"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_perception_interface.ipynb（纯 numpy，含感知错误注入实验）'),
    ("核心参考", "DriveVLM · EMMA · OmniDrive · Guo et al. On Calibration of Modern Neural Networks · LLM prompt sensitivity 系列"),
    ("预计时长", "读 85 分钟 + 跑 70 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("three-levels", "三种融合层次：感知的输出可以在三个地方进入 VLA", "".join([
        P("这是整门课的核心模块，也是 <strong>JD 里「设计感知输出接口以支持 VLA 模型」那条职责的字面对应</strong>。所以先把问题定义清楚：TSR 模块每帧产出一批结构化的检测结果（类别、位置、尺寸、置信度、跟踪 ID……），VLA 需要用到它们。<strong>接口设计要回答的第一个问题不是「传什么字段」，而是「在网络的哪个位置传」</strong>——这个选择决定了后面所有事情。"),
        ASCII("""三个可能的接入点

  多相机图像
      │
      ▼
  ┌─ 视觉编码器 ─┐
  │  patch tokens│───────────────────────┐
  └──────┬───────┘                       │
         │                               │  ② **特征级**
         ▼                               │  TSR 的 ROI 特征 / 检测头特征
  ┌─ BEV / 场景编码 ─┐                    │  投影成额外 token 或 cross-attn 注入
  │  BEV query x N   │──────┐             │
  └──────┬───────────┘      │ ③ **中间表示级**
         │                  │ 感知与 VLA **共享同一份 BEV query / 场景 token**
         ▼                  │
  ┌─ TSR 检测头 ─┐          │             │
  │ 框+类别+置信 │          │             │
  └──────┬───────┘          │             │
         │                  │             │
         ▼                  │             │
  ┌─ 跟踪 / 时序融合 ─┐      │             │
  │ track_id + 状态机 │      │             │
  └──────┬────────────┘     │             │
         │ ① **符号/文本级**  │             │
         ▼ 序列化成结构化文本 │             │
  ┌─────────────────────────▼─────────────▼──────────────┐
  │                    LLM 主干                           │
  │  [系统 prompt][图像 token][**感知 token**][指令]      │
  └──────────────────────┬────────────────────────────────┘
                         ▼
                    动作输出头（模块 02）"""),
        TABLE(["维度", "① 符号 / 文本级", "② 特征级", "③ 中间表示级（BEV query）"], [
            ["<strong>传什么</strong>", "序列化的结构化文本：<code>cls=speed_limit_60|conf=0.87|dist_m=42.3</code>", "ROI 特征向量 / 检测头输出特征，投影成 token", "感知与 VLA <strong>共用同一组 BEV query / 场景 token</strong>"],
            ["<strong>信息保真度</strong>", "<strong>低</strong>——只有你显式写进 schema 的字段", "高——特征里的信息几乎全在", "<strong>最高</strong>，且是稠密几何信息"],
            ["<strong>可解释 / 可调试</strong>", "<strong>✅ 最好</strong>：prompt 可直接读，能一眼看出模型看到了什么", "❌ 不可读", "❌ 不可读"],
            ["<strong>token 成本</strong>", "<strong>随目标数线性增长</strong>（约 20–30 token/目标）", "1 token/目标，很低", "<strong>固定</strong>（如 100 个 BEV query），与目标数无关"],
            ["<strong>模块解耦</strong>", "<strong>✅ 完全解耦</strong>：感知换模型不影响 VLA，只要 schema 不变", "⚠️ 耦合特征维度与语义", "<strong>❌ 强耦合</strong>：两边必须一起训练、一起发版"],
            ["<strong>置信度可传递</strong>", "<strong>✅ 天然</strong>（就是一个字段）", "⚠️ 隐含在特征里，下游未必学得到", "⚠️ 同左"],
            ["<strong>能否复用预训练</strong>", "<strong>✅ 直接用文本，零改动</strong>", "需训连接器", "需从头联合训练"],
            ["<strong>误差归因</strong>", "<strong>✅ 能明确定位是感知错还是决策错</strong>", "⚠️ 困难", "<strong>❌ 端到端，很难定位</strong>"],
            ["<strong>延迟</strong>", "增加 prompt 长度 → 预填充变慢", "极小", "无额外开销（本来就要算）"],
            ["典型使用者", "DriveVLM 的场景描述、多数原型与调试链路", "OmniDrive 等的 3D 感知 token", "<strong>量产端到端系统的主流</strong>"],
        ]),
        DUAL(
            "为什么<strong>量产系统最终会走向中间表示级</strong>？三个理由叠加：<em>①token 成本与目标数解耦</em>——城市路口 40 个交通元素时，符号级要 800–1200 个 token 光描述场景，而 BEV query 永远是那 100 个；<em>②信息不经过「人写的 schema」这个瓶颈</em>——你永远想不全该传哪些字段，而 BEV 特征里什么都有；<em>③省掉一次序列化-反序列化</em>，延迟与工程复杂度都低。<strong>代价是：感知和 VLA 变成一个不可分割的整体，出了问题很难说清是谁的错。</strong>",
            "但<strong>符号级远没有过时，而且在两个场景里不可替代</strong>。<em>第一是<strong>调试与归因</strong></em>：当路测出现一次「该减速没减速」，符号级接口让你能直接打开那一帧的 prompt，看到「感知当时报的是 <code>speed_limit_120, conf=0.31</code>」——五秒钟定位。而 BEV query 是一堆浮点数，你只能重跑整条链路做消融。<em>第二是<strong>安全相关的强语义</strong></em>：限速值、禁令类别这些直接决定合法性的东西，必须以<strong>可审计、可追溯、可写进日志</strong>的形式存在，因为事故调查要的是「系统当时认为限速是多少」这个明确答案，而不是一组特征。<strong>所以真实系统的形态几乎总是混合的</strong>：稠密几何走中间表示级，<em>少量但关键的强语义（限速值、禁行、停车让行）额外走一条符号级通路</em>，两条通路互为交叉校验。",
        ),
        CALLOUT("intuition", "一条可迁移的判据：<strong>「这个信息出了错，事后需要能说清楚吗？」需要 → 走符号级；不需要 → 走特征/中间表示级。</strong><em>可审计性是符号接口存在的根本理由，不是「信息量」或「性能」。</em>面试里能把「为什么明知道有信息损失还要用文本接口」答成这一条，比背三种融合的定义强得多。"),
        CALLOUT("warn", "别把「符号级」等同于「让 LLM 读一段自然语言描述」。<strong>用自然语言描述场景是 token 成本最高、稳定性最差的做法</strong>（第 5 节会算：同样的信息，紧凑键值 schema 只要自然语言的 1/3 token，而且可以被严格解析与校验）。<em>符号级接口应该是「结构化文本」，不是「文章」。</em>"),
    ])),

    # ============================================================== 2
    ("schema", "TSR → VLA 的序列化 schema：每一个字段为什么必须有", "".join([
        P("假设我们走符号/混合路线。现在来设计那份 schema。<strong>下面这张表是本模块最实用的产出——它可以直接当成接口评审的检查单</strong>。设计原则只有一条：<em>每加一个字段，都要能回答「下游拿它干什么，不传会导致什么具体故障」；答不上来的字段就是噪声，占 token 还让模板变脆。</em>"),
        TABLE(["字段", "类型 / 单位", "下游用它干什么", "<strong>不传会发生什么（具体故障）</strong>"], [
            ["<code>schema_version</code>", "字符串，如 <code>tsr/1.3</code>", "解析器选版本；模型卡记录训练时用的版本", "<strong>感知升级加了字段 → VLA 的解析器悄悄错位 → 全线误读</strong>。这是接口演进唯一可靠的抓手"],
            ["<code>t_capture</code> / <code>frame_id</code>", "毫秒时间戳", "判断数据新鲜度；与自车状态对齐", "<strong>无法识别陈旧数据</strong>。感知卡了 300 ms，VLA 会拿 9 米前的世界做决策却毫不知情（模块 02 的 staleness 在这里落地）"],
            ["<strong><code>track_id</code></strong>", "整数，跨帧稳定", "识别「这是同一块牌子」；做迟滞与状态机；关联历史", "<strong>一块牌子的 10 帧被当成 10 块牌子</strong>；无法做「连续 N 帧确认才生效」；无法解释「牌子消失了」是遮挡还是真的过去了"],
            ["<code>cls</code> + <code>cls_id</code>", "枚举 + 整数", "语义分派", "无从谈起"],
            ["<strong><code>value</code></strong>", "数值 + 单位（<code>speed_kph=60</code>）", "限速值、重量/高度限制的<strong>具体数字</strong>", "<strong>「限速牌」和「限速 60」是两回事</strong>。把数值编进类别名（<code>speed_limit_60</code>）会让类别数爆炸且无法表达罕见值"],
            ["<strong><code>conf_det</code> / <code>conf_cls</code></strong>", "分开的两个 [0,1]", "检测置信 ≠ 分类置信，下游用法不同", "<strong>见第 4 节——这是最常见的接口设计错误</strong>"],
            ["<code>cls_top2</code>", "第二候选类别 + 概率", "表达「60 还是 80 说不准」", "<strong>下游连「这里有两种可能」都不知道</strong>，只能被迫二选一（呼应模块 02 的多模态）"],
            ["<strong><code>pos_ego</code></strong>", "$(x_{\\text{fwd}}, y_{\\text{left}})$ 米，自车坐标系", "算「还有多远到」「在哪条车道」", "<strong>见第 3 节：传图像像素等于让 LLM 做相机标定</strong>"],
            ["<strong><code>sigma_dist</code></strong>", "米，距离的 1σ 不确定度", "远处小目标的距离本来就不准，下游要按不确定度决定提前量", "把 83 m 当成精确值，而它的真实误差是 ±7 m（第 3 节推导）"],
            ["<code>bbox_wh</code>", "像素", "距离估计的输入；<strong>框太小本身就是不可靠信号</strong>", "丢掉一个几乎免费的可靠性代理"],
            ["<strong><code>lane_assoc</code></strong>", "枚举：<code>ego / left / right / opposite / service / unknown</code>", "判断这块牌子<strong>管不管我</strong>", "<strong>把辅路限速 40 当成主路限速 40</strong>；把对向车道的禁令当成自己的。这是 TSR 下游最高频的实际事故"],
            ["<code>n_obs</code> / <code>age_ms</code>", "整数 / 毫秒", "「跟了 20 帧的稳定目标」vs「刚冒出来的一帧」", "<strong>置信度本身不含这个信息</strong>——单帧 0.9 和连续 20 帧 0.9 的可信度差一个量级"],
            ["<code>state</code>", "枚举：<code>tentative / confirmed / lost</code>", "生命周期；lost 后的宽限期", "牌子被树叶遮住一帧就「消失」→ 约束被误撤销"],
            ["<code>ttl_ms</code>", "毫秒有效期", "看门狗：超期自动降级", "过期数据被当成当前数据"],
            ["<code>src</code>", "相机 ID / 传感器", "多相机冲突时的仲裁；归因", "同一块牌子被前视与侧视各报一次，下游当成两块"],
        ]),
        DUAL(
            "表里最容易被漏掉、后果又最严重的两个字段是 <strong><code>track_id</code></strong> 和 <strong><code>lane_assoc</code></strong>。<em>漏 <code>track_id</code></em> 的后果不是「少了个 ID」，而是<strong>下游彻底失去时间维度</strong>——它没法说「这块牌子我已经连续看到 15 帧了」，于是要么每帧都重新做决定（输出抖动），要么自己重新做一遍跟踪（把感知的活干第二遍，还干得更差，因为它只有框没有特征）。<em>漏 <code>lane_assoc</code></em> 则是把一个<strong>感知有能力回答、下游没能力回答</strong>的问题甩给了下游：牌子挂在龙门架的哪一格、对应哪条车道，这需要标志与车道线的几何关联，感知模块有车道线、有 BEV，做起来是自然的；VLA 只拿到一个坐标，只能猜。",
            "更一般的原则是：<strong>接口的边界应该划在「谁有能力回答这个问题」的地方，而不是划在「谁的代码好改」的地方</strong>。<em>感知能算的东西不要留给下游算</em>——因为感知有原始像素、有多帧、有几何标定，下游只有一份摘要。反过来，<em>感知不该做的也不要越界做</em>：比如「这块限速牌该不该生效」涉及导航路径、当前车道、法规优先级，那是决策层的知识，感知强行判断只会在信息不全的情况下猜错，而且把错误锁死在一个下游无法纠正的字段里。<strong>一个好用的检验：把每个字段问一遍「如果这个判断错了，下游有没有信息把它纠正回来？」——没有的话，这个字段就不该由感知来定。</strong>",
        ),
        CODE("""{
  "schema_version": "tsr/1.3",
  "t_capture_ms": 1723891234567,
  "ego": {"speed_mps": 27.8, "lane_id": "ego"},
  "signs": [
    {
      "track_id": 4127,
      "cls": "speed_limit", "cls_id": 12,
      "value": {"speed_kph": 60},
      "cls_top2": [["speed_limit:60", 0.71], ["speed_limit:80", 0.22]],
      "conf_det": 0.93, "conf_cls": 0.71, "conf_calibrated": true,
      "pos_ego": {"x_fwd_m": 82.4, "y_left_m": -3.1},
      "sigma_dist_m": 6.9,
      "bbox_wh_px": [12, 12],
      "lane_assoc": "ego",
      "n_obs": 3, "age_ms": 240, "state": "tentative",
      "src": "front_wide", "ttl_ms": 500
    }
  ]
}"""),
        CALLOUT("danger", "<p><strong>面试里一个高频且很能区分人的追问：「你的 schema 里为什么要有 <code>state</code> 和 <code>n_obs</code>？置信度不是已经表达可靠性了吗？」</strong>标准答法：<em>置信度是<strong>单帧证据强度</strong>，<code>n_obs</code>/<code>state</code> 是<strong>时间上的一致性</strong>，两者正交</em>。一块牌子可以单帧 conf=0.95 但只出现过一帧（很可能是广告牌上的图案或一次瞬时误检），也可以单帧 conf=0.6 但连续 20 帧稳定跟踪（那几乎肯定是真的）。<strong>下游对这两种情况的处理完全不同：前者应该等，后者应该信。</strong>如果只传一个融合后的标量，你就<em>永远无法在下游区分它们</em>——而融合规则一旦写死在感知里，下游想改都改不了。<em>这也是「置信度不要提前融合」这条更一般原则的一个实例。</em></p>", "置信度 ≠ 时序一致性，别提前融合掉"),
        CALLOUT("warn", "还有一个务实的建议：<strong>把单位写进字段名</strong>（<code>x_fwd_m</code> 而不是 <code>x</code>，<code>speed_kph</code> 而不是 <code>speed</code>）。<em>看起来啰嗦，但它把「单位错误」这一整类事故变成了不可能</em>——而单位错误（米/厘米、m/s 与 km/h、度/弧度）在跨团队接口里是排第一的低级事故来源，且极难在代码评审里发现。这个约定对 LLM 尤其有价值：<strong>字段名本身就是给模型的提示，<code>dist_m=82.4</code> 比 <code>dist=82.4</code> 更不容易被误解成厘米。</strong>"),
    ])),

    # ============================================================== 3
    ("frames", "位置传什么：坐标系与距离的不确定度", "".join([
        P("schema 里最容易做错的一项是位置。三个候选，取舍很清楚："),
        TABLE(["坐标系", "内容", "优点", "<strong>致命问题</strong>", "何时用"], [
            ["图像像素 $(u,v,w,h)$", "检测框在图上的位置", "感知直接有，零成本", "<strong>下游要做反投影才能知道「多远」，而它没有内参外参</strong>；相机一换全部失效", "只在调试可视化时用"],
            ["<strong>自车坐标 $(x_{\\text{fwd}}, y_{\\text{left}})$</strong>", "米，原点在后轴中心", "<strong>直接可用于「还有多远」「在哪条车道」</strong>；与相机无关", "需要距离估计，而距离估计有误差", "<strong>默认选择</strong>"],
            ["BEV / 全局坐标", "地图坐标系下的位置", "可与高精地图先验融合、可跨帧累积", "依赖定位精度；定位漂移会污染感知输出", "有高精地图与高精定位时叠加提供"],
        ]),
        H3("距离怎么来，误差有多大"),
        P("单目相机估标志距离用针孔模型：焦距（像素）由分辨率与水平视场角决定，物理尺寸已知（中国的圆形限速牌直径通常 0.6 m 或 0.8 m），于是"),
        MATH("f_{px} = \\frac{W_{px}}{2\\tan(\\mathrm{FOV}_h/2)}, \\qquad Z = \\frac{f_{px}\\cdot S}{w_{px}}, \\qquad \\frac{\\mathrm{d}Z}{Z} = -\\frac{\\mathrm{d}w}{w}"),
        P("最后那个式子是本节的关键：<strong>距离的<em>相对</em>误差等于框宽的<em>相对</em>误差</strong>。代入 1920×1080、$\\mathrm{FOV}_h=60^\\circ$ → $f_{px}=1662.8$，$S=0.6$ m："),
        TABLE(["框宽 $w$", "估计距离 $Z$", "1 px 误差 ⇒ 相对误差", "<strong>距离不确定度 $\\sigma_Z$</strong>", "含义"], [
            ["60 px", "16.6 m", "1.67%", "±0.28 m", "近处，几乎精确"],
            ["24 px", "41.6 m", "4.17%", "±1.73 m", "可用"],
            ["<strong>12 px</strong>", "<strong>83.1 m</strong>", "<strong>8.33%</strong>", "<strong>±6.9 m</strong>", "<strong>远处，误差已达 7 米</strong>"],
            ["8 px", "124.7 m", "12.5%", "±15.6 m", "只能当「那边有东西」用"],
        ]),
        DUAL(
            "所以「82.4 米」这个数字如果<strong>不带 $\\sigma$，它就是在撒谎</strong>。下游看到 82.4 会以为精确到分米，实际上它可能是 75 也可能是 90。<em>而这 15 米的差别在 30 m/s 下就是 0.5 秒的决策提前量</em>——足以决定「现在开始平缓减速」还是「必须急刹」。<strong>更糟的是这个误差不是随机噪声，它是尺寸的确定性函数</strong>：越远越大、且是乘性的。下游只要拿到 <code>bbox_wh_px</code> 就能自己算出来——<em>但前提是你把它传了。</em>",
            "严谨地说，$Z = f S / w$ 在 $w$ 上做一阶传播得到 $\\sigma_Z \\approx (Z/w)\\,\\sigma_w = (Z^2/(fS))\\,\\sigma_w$——<strong>距离误差随距离的<em>平方</em>增长</strong>。$\\sigma_w$ 的来源有三：检测框本身的定位误差（远处小框 ±1 px 是乐观估计）、标志物理尺寸 $S$ 的不确定（0.6 还是 0.8 m 的牌子？误判就是 33% 的系统性偏差）、以及相机标定误差。<em>其中第二项常被忽略但影响最大</em>：<strong>如果你不知道这块牌子的物理尺寸，单目就根本无法给出绝对距离</strong>——所以 schema 里的 <code>cls</code> 不只是语义，它同时是距离估计的先验。这也解释了为什么「先粗分类拿到尺寸先验，再精细分类」在 TSR 两级架构里是自然的（C55 模块 02）。",
        ),
        ASCII("""自车坐标系（右手系，原点在后轴中心）

              y_left (+)
                 ▲
                 │        ● 限速牌 (x_fwd=82.4, y_left=-3.1)
                 │          ╲  σ_dist = 6.9 m  ← **必须传**
      ───────────┼────────────╲──────────────────────► x_fwd (+)
                 │  ┌───┐      ╲                        前方
                 │  │自车│       ╲ 真实位置可能在 75.5 ~ 89.3 m
                 │  └───┘
                 ▼
              y_left (−)  = 右侧

  ★ 为什么不用图像像素：下游要知道「还有多远」就得做反投影，
    而反投影需要内参、外参、地平面假设 —— **这些 VLA 都没有**。
    让 LLM 从 (u=1204, v=463, w=12, h=12) 推出 82 米，是让它做相机标定。"""),
        CALLOUT("danger", "<p><strong>一个真实且高频的接口事故：坐标系约定不一致。</strong><code>y</code> 到底是「向左为正」还是「向右为正」？<code>x</code> 是「车头方向」还是「图像横轴」？角度是度还是弧度、逆时针还是顺时针？<em>这类问题在同一个团队内靠口头约定还能撑住，跨团队（感知组 vs 规控组 vs 大模型组）必然出事</em>——而且症状极其隐蔽：<strong>系统大部分时候是对的（因为多数标志在正前方，$y\\approx 0$，符号错了看不出来），只在牌子明显偏一侧时才错</strong>，于是问题只在特定路段复现，查起来极痛苦。<strong>唯一可靠的做法是：把坐标系定义写进 <code>schema_version</code> 对应的文档，并在接口层加一个断言测试（放一个 $y_{\\text{left}}=+5$ 的合成目标，检查下游认为它在左边）。</strong>这个测试写十行，能省掉一次线上事故。</p>", "坐标系符号错误只在偏侧目标上暴露"),
    ])),

    # ============================================================== 4
    ("confidence", "置信度必须传递：接口设计里最常见、代价最大的错误", "".join([
        P("这一节请当作整门课的重点。<strong>不传置信度，等于强迫下游把每一个检测都当成事实</strong>——而任何检测器的输出里都混着 10%–30% 的错误。接口一旦这样定，下游就<em>永远</em>没有办法把这部分错误挡住，因为信息在接口处就已经被丢掉了。"),
        H3("四个层次的错误，一层比一层隐蔽"),
        OL([
            "<strong>不传</strong>：下游被迫全信。这是最粗暴、也最容易被发现的（一测就炸）。",
            "<strong>传了，但只传一个融合后的标量</strong>：下游区分不了「单帧强证据」和「多帧弱证据」（见第 2 节），也区分不了「框准不准」和「类别对不对」。<em>融合规则被锁死在感知里，下游想改也改不了。</em>",
            "<strong>传了，但没校准</strong>：0.9 实际只有 0.6 的正确率。下游用它做期望代价计算时，算出来的风险系统性偏低。",
            "<strong>传了、校准了，但下游用固定阈值</strong>：阈值是拍脑袋定的（「0.7 听起来挺自信」），而不是从代价推出来的。<em>这时候校准反而「显得没用」——因为调阈值能掩盖失准（见下面的 DUAL）。</em>",
        ]),
        H3("校准是什么，以及它的度量"),
        P("<span class=\"term\">Calibration</span>（校准）的定义很朴素：<strong>模型说 0.8 的那一批样本，实际正确率应该就是 80%</strong>。度量它的标准工具是 <span class=\"term\">ECE</span>（Expected Calibration Error，期望校准误差）——把样本按置信度分箱，算每个箱里「平均置信度」与「实际准确率」的差，再按箱内样本数加权平均："),
        MATH("\\mathrm{ECE} = \\sum_{m=1}^{M} \\frac{|B_m|}{n}\\;\\Bigl|\\;\\underbrace{\\mathrm{acc}(B_m)}_{\\text{实际准确率}} \\;-\\; \\underbrace{\\mathrm{conf}(B_m)}_{\\text{平均置信度}}\\;\\Bigr|"),
        P("而下游要用它做的事，是一个<strong>期望代价最小化</strong>的决策。设采纳一个错误检测的代价是 $C_{\\text{wrong}}$、拒绝并退到保守方案的代价是 $C_{\\text{rej}}$，则「采纳」的贝叶斯最优条件是："),
        MATH("(1-p)\\,C_{\\text{wrong}} \\;\\le\\; C_{\\text{rej}} \\quad\\Longleftrightarrow\\quad p \\;\\ge\\; p^{\\star} = 1 - \\frac{C_{\\text{rej}}}{C_{\\text{wrong}}}"),
        P("$C_{\\text{wrong}}=10$、$C_{\\text{rej}}=1.5$ 时 $p^\\star = 0.85$。<strong>注意这个阈值是从代价<em>算</em>出来的，不是调出来的</strong>——而它成立的前提是 $p$ 真的是概率，也就是<strong>校准过的</strong>。notebook 会验证：在这个决策规则下，期望代价<em>恰好</em>在 ECE 最小（完全校准）时取到最小值，而「不传置信度」的基线代价比它高 97%。"),
        DUAL(
            "这里有一个必须讲清楚、否则会被面试官问倒的微妙点：<strong>如果失准是<em>单调</em>的（比如温度缩放那种），而你又允许重新调阈值，那么决策完全不变</strong>。因为单调变换不改变排序，ROC 曲线一模一样，最优阈值只是平移了一下。<em>这正是「我们调了调阈值就好了，所以校准没用」这个错误结论的来源</em>——它在那个特定配置下确实「好了」。",
            "但这个补偿是<strong>脆弱且不可迁移的</strong>，三种情况下会立刻塌掉。<em>①<strong>阈值是固定或共享的</strong></em>：下游按「0.7 = 挺可信」写死，或者多个消费者共用一个阈值；这时感知模型一升级、失准程度一变，所有下游行为同时漂移，而没人会想到去重调。<em>②<strong>决策要用概率做算术</strong></em>：期望代价 $(1-p)C_{\\text{wrong}}$、风险预算分配、代价不对称的门控——这些都直接用 $p$ 这个<em>数值</em>，而不只是它的排序，失准就是系统性的算错。<em>③<strong>多源融合</strong></em>：把相机的 $p_1$ 和地图先验的 $p_2$ 相乘或做贝叶斯更新时，两个失准的概率相乘会把误差放大，而且方向不可预测。<strong>所以正确的说法是：校准不是为了让排序更好（它做不到），而是为了让「概率」这个数在下游可以被<em>当作概率来算</em>。</strong>",
        ),
        TABLE(["接口设计", "下游能做什么", "本例期望代价", "相对最优"], [
            ["<strong>不传置信度</strong>", "只能全部采纳", "<strong>2.272</strong>", "<strong>+97%</strong>"],
            ["传原始分数（过自信，$T{=}0.35$）", "能排序，但概率算术会算错", "1.430", "+24%"],
            ["传原始分数（欠自信，$T{=}2$）", "过度保守，白白拒绝大量正确检测", "1.402", "+22%"],
            ["<strong>传校准后的概率</strong>", "<strong>可直接做期望代价决策</strong>", "<strong>1.152</strong>", "<strong>最优</strong>"],
            ["（参考）全部拒绝，只用地图先验", "不用感知", "1.500", "+30%"],
        ]),
        CALLOUT("danger", "<p><strong>这是 JD 那条职责最核心的一句话，值得逐字记住：不传置信度不是「少传一个字段」，而是<em>在接口层面永久删除了下游做风险决策的能力</em>。</strong>下游收到 <code>speed_limit_120</code> 之后，如果没有伴随的概率，它只有两种选择：全信（于是感知的每一个误检都变成一次危险动作）或全不信（那要感知干什么）。<em>而只要传了校准过的概率，下游立刻可以做「代价加权的采纳决策」，把 10 倍代价不对称的场景处理得完全不同</em>——本模块 notebook 里的非对称门控把超速率降了 72%，用的就是这一个字段。<strong>面试里如果只有一句话的时间讲你对感知-决策接口的理解，就讲这一句。</strong></p>", "接口一旦丢掉不确定性，下游永远补不回来"),
        CALLOUT("warn", "<strong>不确定性不只是一个标量。</strong>一份完整的不确定性至少包含四样：<em>①检测置信（这里有没有东西）；②分类分布（是什么，最好给 top-2 及其概率）；③几何不确定度（$\\sigma_{\\text{dist}}$，第 3 节）；④时序一致性（<code>n_obs</code>/<code>state</code>）</em>。<strong>它们的下游用法完全不同</strong>：①决定要不要理会，②决定要不要表达「有两种可能」（呼应模块 02 的多模态），③决定提前量与安全裕度，④决定要不要再等几帧。<em>把它们压成一个数，就是把四个正交的决策塌成一个。</em>"),
    ])),

    # ============================================================== 5
    ("prompt", "prompt 模板与稳定性：把接口当成协议来设计", "".join([
        P("符号级接口的物理形态是一段进入 prompt 的文本。<strong>而 LLM 对格式的敏感程度远超直觉</strong>：字段顺序、数值格式、分隔符、甚至空格数量的变化，都可能让同一份语义得到不同的输出。所以这段文本必须<strong>当成一个有版本、有校验、有兼容策略的协议来设计</strong>，而不是「拼个字符串给模型看看」。"),
        H3("三条铁律"),
        TABLE(["铁律", "做法", "反例与它的具体后果"], [
            ["<strong>① 键值，不要位置</strong>", "<code>track_id=4127|cls=speed_limit|value_kph=60|…</code>", "位置式 <code>4127|speed_limit|60|…</code>：<strong>感知那边插入一个新字段，下游解析器会<em>静默错位</em></strong>——把置信度读成距离，还不报错"],
            ["<strong>② 字段顺序固定并写进版本</strong>", "顺序是 schema 的一部分，改顺序 = 升版本 = 重新评测", "「我只是把 conf 挪到前面，语义没变」：<em>模型在训练时见到的是另一种顺序，注意力模式不同，输出会漂</em>"],
            ["<strong>③ 缺失值用显式 <code>null</code>，绝不用哨兵数值</strong>", "<code>lane_assoc=null</code>、<code>dist_m=null</code>", "<strong>用 <code>-1</code> 表示「距离未知」→ 下游的「忽略车后目标（dist&lt;0）」规则把它<em>静默丢掉</em></strong>。一个有效检测就这样消失了，且没有任何日志"],
        ]),
        H3("还有四件必须定死的事"),
        UL([
            "<strong>数值格式</strong>：定点、固定小数位、单位在字段名里。<em><code>60</code> / <code>60.0</code> / <code>6.0e+01</code> 三种写法在 tokenizer 眼里是不同长度的不同 token 序列</em>；训练时是 <code>60.0</code>、推理时变成 <code>60</code>，模型的行为就可能变。<strong>格式漂移属于训练-部署一致性问题（C60 的主题），只是发生在文本层。</strong>",
            "<strong>排序规则</strong>：目标按什么排？<em>必须确定且稳定</em>（如「先按 <code>lane_assoc</code> 分组，组内按距离升序」）。如果用哈希序或多线程完成序，<strong>同一帧跑两次会得到不同 prompt → 输出不可复现 → 任何 badcase 都无法稳定重放</strong>。",
            "<strong>截断策略</strong>：目标太多超 token 预算时丢谁？<em>丢的规则必须与下游的安全逻辑一致</em>——按距离截断会丢掉远处刚出现的限速牌（而那恰恰是需要提前决策的）；按置信度截断会丢掉低置信但高影响的目标。<strong>务实做法：按「安全相关性 × 距离」排序，并在 prompt 里显式写 <code>truncated=true, n_dropped=7</code>，让模型知道自己看到的不全。</strong>",
            "<strong>空场景的表示</strong>：一个标志都没有时传什么？<em>传空字符串会让模型「看不到这个字段」从而依赖先验；传显式的 <code>signs=[] (n=0)</code> 才是「我确实看了，确实没有」</em>。<strong>「没有证据」和「证据说没有」是两件事，接口必须能区分。</strong>",
        ]),
        DUAL(
            "为什么这些看起来琐碎的约定值得写进课程？因为<strong>它们造成的故障有一个共同特征：静默</strong>。位置错位不报错、哨兵值被规则吃掉不报错、格式漂移不报错、排序不稳定不报错——<em>它们全都表现为「模型有时候表现变差了」，而不是一个可以定位的异常</em>。而排查这类问题的成本，通常是排查一个崩溃的几十倍。",
            "对应的工程手段也很清楚，而且都不贵：<em>①<strong>渲染与解析必须成对实现并做 round-trip 测试</strong></em>（渲染出来再解析回去，字段必须逐一相等；这一个测试能挡住 80% 的模板事故）；<em>②<strong>解析失败要 fail loud</strong></em>——宁可抛异常也不要「尽力猜」，因为猜错是静默的；<em>③<strong>schema 版本进 prompt 的第一行</strong></em>，并在模型卡里记录训练时用的版本；<em>④<strong>把一份「金标准 prompt」纳入回归测试</strong></em>，任何渲染改动都要 diff 它。<strong>这套做法与 C60 讲的训练-部署一致性是同一个方法论：把「约定」变成「可执行的检查」。</strong>",
        ),
        CALLOUT("intuition", "一句话概括本节：<strong>prompt 模板不是 UI，是 ABI。</strong><em>它是两个模块之间的二进制接口，只不过恰好长得像人话——而「长得像人话」正是它最危险的地方，因为它诱使人们随手改。</em>"),
    ])),

    # ============================================================== 6
    ("error-prop", "错误传播与幻觉：VLA 会「合理化」一切喂给它的东西", "".join([
        P("现在假设接口设计得很好，但感知这一帧就是错了——报了一块根本不存在的「禁止驶入」。<strong>VLA 会怎么反应？答案是：它会生成一个完全自洽、有理有据、听起来无懈可击的绕行方案。</strong>"),
        ASCII("""错误如何被「合理化」并放大

  感知（错）                    VLA（忠实地条件生成）
  ┌────────────────────┐       ┌──────────────────────────────────────┐
  │ cls = no_entry     │──────►│ 「前方检测到禁止驶入标志，本车道不可   │
  │ conf = 0.62        │       │  通行。右侧车道空闲，建议提前变道并    │
  │ lane_assoc = ego   │       │  减速至 40 km/h 后并线。」            │
  │ **实际是广告牌**    │       │  ↑ 语言流畅、逻辑自洽、**完全错误**   │
  └────────────────────┘       └──────────────────────────────────────┘
                                              │
                                              ▼
                                  高速上一次无理由变道 + 急减速
                                  （后车追尾风险；用户信任崩塌）

  ★ 关键：**输出里没有任何一处表达「我不确定」**。
    这是 silent failure ——比崩溃危险得多，因为没有任何信号触发兜底。"""),
        H3("为什么会这样：条件生成没有「质疑输入」的机制"),
        DUAL(
            "VLA 建模的是 $p(\\text{动作} \\mid \\text{观测}, \\text{感知输入}, \\text{指令})$。<strong>它的训练目标里没有任何一项是「判断输入是否可信」</strong>——训练数据里的感知输入几乎总是对的（因为是离线标注或高质量回放），于是模型学到的是「感知说什么就是什么」。<em>这不是模型的缺陷，是训练分布的必然结果</em>：<strong>你没给它见过「感知错了，正确做法是保守」的样本，它就不会那么做。</strong>",
            "而语言模型的生成特性会把这个问题放大一层：<strong>它不仅接受错误输入，还会为它<em>构造理由</em></strong>。因为流畅、自洽的解释在训练分布里是常态（人写的驾驶决策说明都是有理有据的），模型学到的是「给出决策就要配一段合理的解释」。<em>于是错误被包装成了「有依据的判断」，反而更难被人工审核发现</em>——一段写着「因为前方 60 米处有禁止驶入标志」的输出，比一段没有解释的输出<strong>看起来更可信</strong>。<strong>这是可解释性的一个反直觉的负面效应：解释的流畅度与决策的正确性无关，但人会把前者当作后者的证据。</strong>",
        ),
        H3("两个方向的幻觉，要分开度量"),
        TABLE(["类型", "定义", "怎么发生", "<strong>怎么度量与拦截</strong>"], [
            ["<strong>输入幻觉</strong>（被骗）", "感知报了不存在的东西，VLA 全盘接受并放大", "误检 + 下游无置信度门控", "<strong>度量</strong>：注入合成误检，统计下游动作错误率。<strong>拦截</strong>：置信度门控 + 非对称代价（第 7 节）"],
            ["<strong>输出幻觉</strong>（编造）", "VLA 提到了感知输出里<em>根本没有</em>的实体", "语言先验太强（「路口通常有停车让行牌」）", "<strong>度量</strong>：解析输出中引用的实体，检查每个是否能对上一个 <code>track_id</code>。<strong>拦截</strong>：<strong>grounding 校验——引用不到就拒绝整条输出</strong>"],
            ["<strong>沉默错误</strong>", "错了，且输出里没有任何不确定信号", "上面两者的共同后果", "<strong>度量</strong>：错误样本中「输出未表达不确定」的比例。<strong>这是最该被追踪的单一指标</strong>"],
        ]),
        P("<strong>输出幻觉的拦截手段值得展开，因为它便宜且有效</strong>：既然 schema 里每个目标都有 <code>track_id</code>，那就要求 VLA 的输出必须<em>显式引用 track_id</em>（「因为 <code>track#4127</code> 是限速 60，减速至 60」）。<em>然后在输出侧做一次纯字符串校验：引用的每个 ID 是否都在本帧的输入里？</em>不在就说明模型在编造，整条输出作废、走兜底。<strong>这个检查十几行代码、零延迟，却能把「模型凭空造出一块牌子」这类事故完全挡住</strong>——而且它同时给了你一个可日志、可统计的幻觉率指标。"),
        H3("级联的乘法"),
        P("最后回到一个 C55 模块 02 讲过、这里必须重申的算术：<strong>端到端正确率是各环节正确率的<em>乘积</em></strong>。"),
        MATH("P_{\\text{e2e}} = P_{\\text{det}} \\times P_{\\text{cls}} \\times P_{\\text{assoc}} \\times P_{\\text{decide}}"),
        P("每环 95% 的四环级联只有 81.5%。<strong>这意味着「把感知做到 99%」的边际价值，取决于其他环节现在是多少</strong>——如果车道关联只有 85%，把检测从 95% 提到 99% 带来的端到端提升不到 3.4 个点。<em>而置信度传递之所以价值巨大，正是因为它<strong>打破了这个乘法</strong></em>：下游知道哪些环节这次不可靠时，可以选择不把错误往下传，而是退到一个已知安全的默认值。<strong>不传置信度 = 各环节的错误必然相乘；传了 = 下游有机会截断。</strong>"),
        CALLOUT("danger", "<p><strong>一个必须在设计阶段就想清楚的问题：VLA 的解释输出该不该给用户看？</strong>给看的好处是信任与可调试；<em>坏处是「流畅的错误解释」会<strong>制造</strong>信任</em>——用户看到「因为前方有施工标志」会倾向于相信系统真的看到了。<strong>务实的折中是：解释里必须带上它所依赖的感知证据与置信度</strong>（「依据：<code>track#4127</code> 限速牌，置信 0.62，距离 82±7 m」），让人看到的不只是结论，还有结论的脆弱程度。<em>把不确定性一路透传到用户界面，是这条设计原则的终点。</em></p>", "流畅的解释会制造它并不配得的信任"),
    ])),

    # ============================================================== 7
    ("conservative", "如何让 VLA 对低置信输入保持保守", "".join([
        P("知道了问题，来看手段。<strong>七种做法，按「在哪一层生效」排列</strong>——注意它们不是可选项列表，而是应该<em>叠加</em>使用的纵深防御。"),
        TABLE(["层", "手段", "怎么做", "代价 / 边界"], [
            ["<strong>输入侧</strong>", "① 置信度门控", "低于阈值的检测不进 prompt，或进但标注为 <code>uncertain=true</code>", "阈值定低了漏、定高了噪；<strong>阈值必须从代价推导</strong>而不是拍脑袋"],
            ["<strong>输入侧</strong>", "② <strong>不确定性语言化</strong>", "把分布写进文本：<code>cls=speed_limit value_kph=60 p=0.71 alt=80 p=0.22</code>", "<strong>训练时必须见过这种输入</strong>，否则模型不知道该怎么用（最容易被忽略的一点）"],
            ["<strong>决策</strong>", "③ <strong>非对称门控</strong>", "降低限速：低门槛即采纳；<strong>提高限速：高门槛才采纳</strong>", "<strong>本模块 notebook 里超速率降 72%</strong>；代价是过度限速率上升"],
            ["<strong>训练</strong>", "④ 带噪输入 + 保守标签", "训练数据里注入合成感知误差，标注「此时正确动作是保守」", "要构造这类样本；<strong>没有这一步，前三条只是外挂规则</strong>"],
            ["<strong>输出侧</strong>", "⑤ grounding 校验", "输出引用的 <code>track_id</code> 必须存在于本帧输入", "只挡输出幻觉，挡不住输入幻觉；<strong>但零成本</strong>"],
            ["<strong>兜底</strong>", "⑥ 约束/安全层", "VLA 输出经过无神经网络的可行性与合规校验（模块 04）", "只能挡住「不可行」，挡不住「可行但不该做」"],
            ["<strong>闭环</strong>", "⑦ 触发回传", "低置信 + 高影响 = 难例，回传标注（C58 模块 03）", "带宽预算；<strong>但这是长期唯一的根治手段</strong>"],
        ]),
        H3("非对称门控：把代价不对称直接写进规则"),
        P("第 ③ 条最值得展开，因为它是「置信度传递」的直接变现，也是最容易在面试里讲清楚的一个具体设计。<strong>核心观察：限速类约束的两个方向代价完全不同</strong>——"),
        UL([
            "<strong>把限速调低了（过度保守）</strong>：车开慢了。代价是效率与舒适，以及被追尾的<em>间接</em>风险。可恢复。",
            "<strong>把限速调高了（超速）</strong>：车开快了。代价是<strong>直接的安全与合规风险</strong>，且不可恢复（罚单已经开了，事故已经发生了）。",
        ]),
        P("既然代价不对称，门槛就该不对称：<strong>「往安全方向走」用低门槛（$p \\ge 0.30$ 就采纳），「往风险方向走」用高门槛（$p \\ge 0.90$ 才采纳）</strong>。notebook 会把这个规则实现出来并量化："),
        TABLE(["下游策略", "超速率", "过度限速率", "加权风险（超速 ×10 + 过限 ×3）", "说明"], [
            ["<strong>不传置信度（全采纳）</strong>", "11.35%", "11.41%", "<strong>1.477</strong>", "基线：感知的错误 1:1 变成动作的错误"],
            ["对称阈值 0.70（校准）", "8.14%", "8.07%", "1.056", "−29%：光是「能拒绝」就有很大收益"],
            ["<strong>非对称门控（校准）</strong>", "<strong>3.13%</strong>", "16.97%", "<strong>0.822</strong>", "<strong>−44%；超速率降 72%</strong>"],
            ["非对称门控（过自信输入）", "6.99%", "11.02%", "1.030", "<strong>失准让收益打对折</strong>——门槛形同虚设"],
            ["（参考）完全忽略感知，只用地图", "12.45%", "12.67%", "1.625", "比全采纳还差：感知确实有价值"],
        ]),
        DUAL(
            "这张表里最重要的是<strong>倒数第二行</strong>：同样的非对称门控规则，输入换成未校准的过自信置信度，加权风险从 0.822 涨到 1.030（+25%），超速率从 3.13% 涨到 6.99%（翻倍多）。<em>因为「$p\\ge0.90$ 才允许提速」这条规则的全部效力，都建立在「0.90 真的意味着 90%」上</em>。<strong>过自信的模型把一堆实际只有 60% 正确率的检测标成了 0.92，门槛形同虚设。</strong>",
            "同时也要诚实地看到<strong>保守不是免费的</strong>：非对称门控把过度限速率从 11.4% 抬到了 17.0%。<em>如果代价权重换一组（比如用户对「莫名其妙减速」极度反感，$C_{\\text{under}}$ 权重加大），最优策略会不同</em>。<strong>所以正确的做法不是「宁可错杀」，而是把 $C_{\\text{over}}$ 与 $C_{\\text{under}}$ 显式写下来，然后由代价推出门槛</strong>——这样当产品说「用户抱怨减速太频繁」时，你改的是一个有明确含义的代价参数，而不是去凭感觉挪一个阈值。<em>把「拍脑袋的阈值」变成「可讨论的代价」，是这套方法论最实际的价值。</em>",
        ),
        CALLOUT("warn", "<strong>第 ④ 条（训练时注入带噪输入）是最容易被跳过、也最不能跳过的一条。</strong>前面三条都是外挂在模型之外的规则；如果模型本身从没见过「输入里带着 <code>conf=0.4</code> 的检测」这种情况，它就<em>不知道该怎么用这个数字</em>——你把置信度写进 prompt，它可能干脆忽略。<strong>正确做法是在训练数据构造阶段就注入合成感知误差（误检、漏检、错分、距离偏差），并把对应的专家动作标成保守的</strong>，让「低置信 → 保守」成为一个<em>学到的</em>行为而不是<em>外加的</em>规则。<em>这也是评测时必须专门构造「感知错误」子集的原因——不然你根本不知道模型有没有学到。</em>"),
        CALLOUT("intuition", "把第 4 节与本节连起来的一句话：<strong>置信度传递创造了「拒绝」这个选项，而非对称门控决定了什么时候用它。</strong><em>没有前者，下游只有「全信」；有了前者但没有后者，下游只会对称地拒绝，白白丢掉大量安全方向上本可采纳的信息。</em>"),
    ])),

    # ============================================================== 8
    ("interview", "面试标准答案骨架（JD 直接对应）", "".join([
        P("<strong>这一节直接对应 JD 里「设计感知输出接口以支持 VLA / 端到端模型」那条职责。</strong>五道题，覆盖了这条职责会被问到的全部角度。骨架的组织原则同前：<em>先给判断，再给机制，然后给数字，最后给代价与边界</em>。"),
        H3("Q1 · 你会怎么把 TSR 的输出接进 VLA？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你知道有三个接入层次、各自的取舍，并且能给出一个<strong>混合</strong>方案而不是单选"],
            ["<strong>40 秒骨架</strong>", "「三个层次。<strong>符号/文本级</strong>——把检测序列化成结构化文本进 prompt，可解释、可审计、与感知模块完全解耦，但有信息损失且 token 随目标数线性增长。<strong>特征级</strong>——ROI 特征投影成 token，信息全、成本低，但不可读。<strong>中间表示级</strong>——感知与 VLA 共享 BEV query，token 数固定、信息最全，是量产端到端的主流，代价是两边强耦合、误差无法归因。<em>我会做混合：稠密几何走中间表示级，少量安全强语义（限速值、禁行、停车让行）额外走一条符号通路</em>。<strong>判据是「这个信息出错以后需不需要事后说清楚」——需要就必须走符号级，因为事故调查要的是『系统当时认为限速是多少』这个明确答案，不是一组特征。</strong>」"],
            ["加分点", "「符号级在<strong>调试与归因</strong>上的价值经常被低估：一次路测异常，打开那一帧的 prompt 五秒钟就能定位；BEV query 只能重跑消融。」"],
            ["<strong>踩雷点</strong>", "只答「拼成文本塞进 prompt」；把「符号级」做成自然语言描述（token 贵 3 倍且无法严格解析）"],
        ]),
        H3("Q2 · 你的 schema 里有哪些字段？为什么每一项都必须有？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你能对每个字段说出「不传会发生什么具体故障」，而不是罗列字段名"],
            ["<strong>40 秒骨架</strong>", "「除了类别和位置，有五项是最容易漏又最致命的。<strong><code>track_id</code></strong>——没有它，一块牌子的 10 帧会被当成 10 块牌子，也没法做「连续 N 帧确认才生效」。<strong><code>lane_assoc</code></strong>——判断这块牌子管不管我；不传就会把辅路限速 40 当成主路的，这是 TSR 下游最高频的实际事故，而且<em>感知有车道线和 BEV，有能力回答；下游只有一个坐标，只能猜</em>。<strong><code>value</code> 独立成字段</strong>——「限速牌」和「限速 60」是两回事，把数值编进类别名会让类别数爆炸。<strong><code>sigma_dist</code></strong>——82 米这个数如果不带 ±7 米就是在撒谎。<strong><code>n_obs</code>/<code>state</code></strong>——置信度是单帧证据强度，时序一致性是另一个正交维度，单帧 0.95 出现一次 vs 连续 20 帧 0.6，下游处理完全不同。<em>再加一个 <code>schema_version</code>，否则接口演进必然出静默错位。</em>」"],
            ["加分点", "「一条通用原则：<strong>接口边界应该划在『谁有能力回答这个问题』的地方</strong>——感知能算的不要留给下游；但『这块牌子该不该生效』涉及导航与法规优先级，感知不该越界猜。检验方法是问『如果这个判断错了，下游有没有信息纠正它』。」"],
            ["<strong>踩雷点</strong>", "背字段清单但说不出故障场景；把单位省掉（<code>dist</code> 而不是 <code>dist_m</code>）"],
        ]),
        H3("Q3 · 为什么置信度必须传？不传会怎样？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "<strong>这是这条 JD 最核心的一题。</strong>你要能说出「接口丢掉的信息永远补不回来」"],
            ["<strong>40 秒骨架</strong>", "「<strong>不传置信度不是少传一个字段，是在接口层面永久删除了下游做风险决策的能力。</strong>任何检测器都有 10–30% 的错误率，下游拿不到概率就只有两种选择：全信（感知每个误检都变成一次危险动作）或全不信（那要感知干什么）。<strong>传了校准过的概率，下游立刻能做期望代价决策</strong>：采纳错误的代价 $C_w$、拒绝退保守的代价 $C_r$，最优阈值就是 $p^\\star = 1-C_r/C_w$，这是<em>算</em>出来的不是调出来的。更进一步可以做<strong>非对称门控</strong>——降低限速低门槛、提高限速高门槛——我做过的实验里超速率降了 72%。<em>而且要传的不止一个标量：检测置信、分类 top-2 分布、几何 σ、时序一致性，这四个是正交的，下游用法完全不同，压成一个数就是把四个决策塌成一个。</em>」"],
            ["<strong>加分点（很能加分）</strong>", "主动讲清楚那个微妙点：「<strong>单调失准 + 重调阈值 = 决策不变</strong>，这是『调调阈值就好了所以校准没用』的错觉来源。但三种情况会塌：①阈值固定或多消费者共享，模型一升级全线漂移；②决策要用概率做<em>算术</em>（期望代价、风险预算）；③多源融合把两个失准概率相乘。<strong>校准不是为了改善排序，是为了让概率这个数能被当作概率来算。</strong>」"],
            ["<strong>踩雷点</strong>", "只说「置信度低就不要用」；说不出阈值该从代价推导；把校准说成能提升 AUC"],
        ]),
        H3("Q4 · 感知错了，VLA 会怎样？怎么防？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "「合理化」与「沉默错误」两个词，以及可落地的拦截手段"],
            ["<strong>40 秒骨架</strong>", "「<strong>VLA 会<em>合理化</em>错误输入</strong>——给它一块不存在的『禁止驶入』，它会输出一个完全自洽、有理有据的绕行方案，而且<strong>输出里没有任何一处表达不确定</strong>。这是 silent failure，比崩溃危险得多，因为没有信号触发兜底。根因是训练目标里没有『判断输入是否可信』这一项，训练数据里的感知输入几乎总是对的。<strong>要分开度量两种幻觉</strong>：输入幻觉（被骗）用注入合成误检来测下游动作错误率；输出幻觉（编造）用 grounding 校验——<em>要求 VLA 输出必须显式引用 <code>track_id</code>，然后在输出侧检查每个引用是否存在于本帧输入，不存在就整条作废走兜底</em>。这个检查十几行代码、零延迟。<strong>最该追踪的单一指标是『沉默错误率』：错了且输出未表达不确定的比例。</strong>」"],
            ["加分点", "「还要防一个反直觉的效应：<strong>流畅的解释会制造它并不配得的信任</strong>。所以解释里必须带上依赖的证据与置信度（『依据 track#4127，置信 0.62，距离 82±7 m』），把不确定性一路透传到用户界面。」"],
            ["<strong>踩雷点</strong>", "只说「加个安全兜底」；说不出输入幻觉与输出幻觉要用不同手段"],
        ]),
        H3("Q5 · prompt 模板要注意什么？"),
        TABLE(["项", "内容"], [
            ["面试官想听", "你把它当协议而不是字符串拼接；能说出静默故障的具体形态"],
            ["<strong>40 秒骨架</strong>", "「三条铁律。<strong>①键值不要位置</strong>——位置式解析在感知插入新字段时会<em>静默错位</em>，把置信度读成距离还不报错。<strong>②字段顺序固定并写进 <code>schema_version</code></strong>——改顺序等于改接口，要重新评测，因为模型训练时见到的注意力模式不同。<strong>③缺失值用显式 <code>null</code>，绝不用哨兵数值</strong>——用 <code>-1</code> 表示『距离未知』，下游『忽略车后目标』的规则会把它<em>静默丢掉</em>。再加四件事：数值格式定死（<code>60.0</code> 还是 <code>60</code> 是不同 token 序列，属于文本层的训练-部署一致性问题）、排序规则确定（否则同帧两次渲染出不同 prompt，badcase 无法重放）、截断策略与安全逻辑一致（并显式写 <code>truncated=true, n_dropped=7</code>）、空场景要能表达『我看了，确实没有』而不是什么都不写。<strong>工程上就一条：渲染与解析成对实现 + round-trip 测试，能挡掉八成模板事故。</strong>」"],
            ["加分点", "「一句话总结：<strong>prompt 模板不是 UI，是 ABI</strong>——它恰好长得像人话，而这正是它最危险的地方，因为诱使人随手改。」"],
            ["<strong>踩雷点</strong>", "答「多试几个 prompt 看哪个效果好」（那是调优，不是接口设计）"],
        ]),
        CALLOUT("intuition", "五题共用一组关键数字与短语，背下来即可：<strong>三个融合层次 · 「出错要不要说清楚」判据 · <code>track_id</code>/<code>lane_assoc</code>/<code>sigma_dist</code> · $p^\\star = 1-C_r/C_w$ · 不传置信度 = 永久删除风险决策能力 · 非对称门控降超速 72% · 合理化与沉默错误 · grounding 校验 · prompt 是 ABI 不是 UI</strong>。"),
    ])),

    # ============================================================== 9
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>符号接口与端到端的最终边界在哪？</strong>产业趋势明显在往中间表示级走（token 成本恒定、信息不过 schema 瓶颈），但<em>可审计性与事故归因的需求不会消失</em>。<strong>一个尚未解决的问题是：能否让端到端系统「事后生成」可审计的符号解释，且这个解释可证明地忠实于实际决策依据</strong>——目前的 post-hoc 解释都无法保证忠实性（模型可以给出一个与实际计算路径无关的合理解释）。这是可解释性研究里最硬的问题之一。",
            "<strong>不确定性的表示与传播。</strong>本模块讲的还是「每个目标一个标量 + 一个 σ」。<em>真实的不确定性是联合的、结构化的</em>：两块牌子是「二选一」还是「都在」？距离误差与类别误差相关吗？<strong>把完整的联合不确定性传给下游，token 成本会爆炸；只传边缘分布，下游就无法做正确的联合推理。</strong>这个取舍目前没有好的理论指导，工业界普遍只传边缘量。",
            "<strong>LLM 到底会不会用置信度这个数字？</strong>把 <code>conf=0.62</code> 写进 prompt，模型是真的在做概率推理，还是只把它当成一个「弱化语气」的记号？<em>已有证据表明 LLM 对 prompt 里的数值概率使用得相当粗糙，且对表述方式（数字 vs「可能」「大概」）高度敏感</em>。<strong>「如何让模型正确使用输入的不确定性」目前主要靠在训练数据里构造对应样本，缺少更原理性的方法。</strong>这直接决定了第 7 节手段 ② 的天花板。",
            "<strong>感知与决策的联合优化 vs 接口稳定性。</strong>联合训练能让感知输出「决策真正需要的东西」而不是「人以为需要的东西」，收益明确；<em>但它会让接口随训练一起漂移，模块化开发、独立评测、供应商分工全部失效</em>。<strong>能否做到「训练时联合、部署时仍有稳定接口」，是量产组织形态与算法效率之间的真实矛盾</strong>，目前没有干净的答案。",
            "<strong>接口层面的对抗鲁棒性。</strong>如果感知输出是文本，那么一个被精心构造的场景（比如车身贴纸让检测器输出某个特定类别）就等价于一次 <em>prompt injection</em>。<strong>「物理世界的对抗样本 → 感知误检 → 文本注入 → VLA 行为被操纵」这条链路在学术上刚开始被研究，在工程上几乎没有防护</strong>。最低限度的防御是对序列化字段做严格的白名单与范围校验（不允许自由文本进入 prompt），但这只挡住了最粗糙的一类。",
            "<strong>校准在长尾与分布漂移下的维持。</strong>温度缩放这类后处理校准在同分布上很有效，<em>但夜间、雨雾、新区域上校准会失效，而这些恰恰是最需要正确不确定性的场景</em>。<strong>「分场景校准」（按天气/光照/距离分桶各校一个温度）是务实做法，但桶的划分本身又是一个开放问题</strong>，而且桶太细会导致每桶样本不足、校准本身过拟合。",
        ]),
        CALLOUT("paper", "<p><strong>★ 必读</strong>：Guo et al., <em>On Calibration of Modern Neural Networks</em>（ICML 2017，arXiv:1706.04599）——ECE、可靠性图、温度缩放的原始出处，本模块第 4 节的全部工具都来自它，<em>务必自己动手复现一次可靠性图</em>。<strong>★</strong> Tian et al., <em>DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models</em>（CoRL 2024，arXiv:2402.12289）——看它怎么把场景描述与关键物体分析组织成结构化输入，以及慢-快双系统的分工。<strong>★</strong> Hwang et al., <em>EMMA: End-to-End Multimodal Model for Autonomous Driving</em>（arXiv:2410.23262）——把驾驶任务全部表述为语言任务的极端做法，读它对「文本作为通用接口」的论证与代价分析。</p><p>配套背景：Wang et al., <em>OmniDrive</em>（3D 感知 token 注入 LLM 的特征级方案）；Kendall &amp; Gal, <em>What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?</em>（NeurIPS 2017，aleatoric vs epistemic 的区分）；Ovadia et al., <em>Can You Trust Your Model's Uncertainty?</em>（NeurIPS 2019，分布漂移下校准的失效）；Sclar et al., <em>Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design</em>（ICLR 2024，格式敏感性的系统性证据）；Zhao et al., <em>Calibrate Before Use</em>（ICML 2021）。相邻课程：模块 02（动作头与多模态）、模块 04（约束化与安全兜底）、模块 05（评测与上车）、C55 模块 02（级联误差传播）与模块 04（时序与迟滞）、C58 模块 03（不确定性触发与回传）、C60（训练-部署一致性）。完整清单见 <code>references.md</code>。</p>"),
    ])),
]

NB = [
    md("""# 03 · TSR 输出如何进入 VLA（融合层次 / schema / 校准 / 错误注入 / prompt 稳定性）

目标：把「感知输出接口」从一句口号变成**可运行、可断言、可上线**的东西。
这是整门课的核心，也是 JD 里「设计感知输出接口以支持 VLA 模型」那条职责的直接对应。

本 notebook 你会亲手实现：
1. **三种融合层次的 token 与信息量账**（bits/token 效率差 1000 倍，以及交叉点在哪）
2. **完整的 TSR→VLA 序列化 schema**：渲染 + 解析 + **round-trip 测试** + 字段消融
3. **针孔距离估计与它的不确定度**：为什么 82 米这个数不带 σ 就是在撒谎
4. **置信度校准**：可靠性图、ECE、温度缩放，以及**期望代价决策在 ECE 最小处取到最优**的验证
5. **感知错误注入实验**：下游动作错误率如何随「置信度是否传递 / 是否校准」变化
6. **非对称门控**：把代价不对称写进规则，超速率降 72%
7. **prompt 模板的三种静默故障**：位置错位 / 哨兵值被吃掉 / 格式漂移

> 心智模型：**接口丢掉的信息，下游永远补不回来。
> 不传置信度不是少传一个字段，是永久删除了下游做风险决策的能力。**"""),

    md("""## 1 · 三种融合层次的 token 与信息量账

先把「符号级贵不贵」这件事算清楚，而不是靠感觉。"""),

    code("""import numpy as np, math, json, re
rng = np.random.default_rng(0)

token_est = lambda s: len(s) // 4 + 1        # 4 字符/token 的经验法则（够用即可）

# 一份完整 schema 的字段位预算（下游真正需要的信息量，单位 bit）
BIT_BUDGET = {
    'track_id': 12,      # 4096 个并发 track
    'cls': 8,            # ~200 个标志类别
    'value_kph': 8,      # 限速值
    'conf_det': 7, 'conf_cls': 7,       # 1/128 分辨率足够
    'x_fwd_m': 11,       # 0~200 m @ 0.1 m
    'y_left_m': 9,       # ±20 m @ 0.1 m
    'sigma_dist_m': 7,
    'lane_assoc': 3, 'n_obs': 5, 'state': 2,
}
SYMBOLIC_BITS = sum(BIT_BUDGET.values())
SYMBOLIC_TOKENS_PER_OBJ = 39     # 紧凑键值行的实测 token 数（第 5 节会算出来）
SLIM_TOKENS_PER_OBJ = 15         # 只留决策必需字段的精简版
FEATURE_DIM, FEATURE_BITS_PER_DIM = 256, 8
BEV_QUERIES = 100                # 与目标数**无关**的固定开销
HEADER_TOKENS = 30               # schema_version + 自车状态 + 表头

print(f'符号级：{SYMBOLIC_BITS} bit/目标，{SYMBOLIC_TOKENS_PER_OBJ} token/目标'
      f'  → {SYMBOLIC_BITS/SYMBOLIC_TOKENS_PER_OBJ:.2f} bit/token')
feat_bits = FEATURE_DIM * FEATURE_BITS_PER_DIM
print(f'特征级：{feat_bits} bit/目标，1 token/目标'
      f'  → {feat_bits:.0f} bit/token')
ratio = feat_bits / (SYMBOLIC_BITS / SYMBOLIC_TOKENS_PER_OBJ)
print(f'\\n★ 特征级的 **bit/token 效率是符号级的 {ratio:.0f} 倍**')
assert ratio > 500
print('   —— 但那 2048 个 bit **不可读、不可审计、不能写进事故报告**。')
print('   符号级付出 1000 倍的 token 效率代价，换的不是信息量，是**可解释性**。')"""),

    code("""def token_cost(n_obj, scheme):
    if scheme == 'symbolic_full':
        return HEADER_TOKENS + SYMBOLIC_TOKENS_PER_OBJ * n_obj
    if scheme == 'symbolic_slim':
        return HEADER_TOKENS + SLIM_TOKENS_PER_OBJ * n_obj
    if scheme == 'feature':
        return n_obj
    if scheme == 'bev_query':
        return BEV_QUERIES
    raise ValueError(scheme)

SCENES = [('高速 · 空旷', 1), ('高速 · 龙门架', 3), ('城市 · 普通路口', 8),
          ('城市 · 复杂路口', 20), ('城市 · 龙门架+商铺招牌', 40)]
print(f\"{'场景':<24s} {'目标数':>6s} {'符号(全)':>9s} {'符号(精简)':>11s} {'特征级':>7s} {'BEV query':>10s}\")
for name, n in SCENES:
    print(f'{name:<24s} {n:>6d} {token_cost(n,\"symbolic_full\"):>9d} '
          f'{token_cost(n,\"symbolic_slim\"):>11d} {token_cost(n,\"feature\"):>7d} '
          f'{token_cost(n,\"bev_query\"):>10d}')

def crossover(scheme_a, scheme_b, n_max=200):
    \"\"\"找到 a 开始比 b 贵的最小目标数。\"\"\"
    for n in range(1, n_max):
        if token_cost(n, scheme_a) > token_cost(n, scheme_b):
            return n
    return None

n_cross = crossover('symbolic_full', 'bev_query')
n_cross_slim = crossover('symbolic_slim', 'bev_query')
print(f'\\n符号(全) 从 {n_cross} 个目标起就比固定 {BEV_QUERIES} 个 BEV query 贵')
print(f'符号(精简) 从 {n_cross_slim} 个目标起才反超')
assert n_cross == 2 and n_cross_slim == 5
print(f'\\n⚠️  40 个目标的城市场景：符号级要 {token_cost(40,\"symbolic_full\")} token 光描述场景，')
print(f'    而 BEV query 永远是 {BEV_QUERIES} —— 这就是量产走中间表示级的第一个理由。')
print('✅ 但判据不是 token：**「这个信息出错以后需不需要事后说清楚」——需要就必须走符号级**。')
print('   务实形态是混合：稠密几何走 BEV，少量安全强语义（限速值/禁行）额外走符号通路。')"""),

    md("""## 2 · TSR → VLA 的序列化 schema：渲染、解析、round-trip

**渲染与解析必须成对实现，并做 round-trip 测试**——这一个测试能挡住八成模板事故。"""),

    code("""SCHEMA_VERSION = 'tsr/1.3'
FIELD_ORDER = ['track_id', 'cls', 'value_kph', 'conf_det', 'conf_cls',
               'x_fwd_m', 'y_left_m', 'sigma_dist_m', 'lane_assoc', 'n_obs', 'state']
NUM_FMT = {'track_id': '{:d}', 'value_kph': '{:d}', 'n_obs': '{:d}',
           'conf_det': '{:.2f}', 'conf_cls': '{:.2f}',
           'x_fwd_m': '{:.1f}', 'y_left_m': '{:.1f}', 'sigma_dist_m': '{:.1f}'}
LANE_PRIORITY = {'ego': 0, 'left': 1, 'right': 1, 'opposite': 2, 'service': 2, 'unknown': 3}
TAIL_TOKENS = 8            # 为 prompt 尾部的 truncated 标记预留
INT_FIELDS = {'track_id', 'value_kph', 'n_obs'}
FLOAT_FIELDS = {'conf_det', 'conf_cls', 'x_fwd_m', 'y_left_m', 'sigma_dist_m'}
NULL = 'null'

def fmt_value(k, v, null=NULL):
    if v is None:
        return null
    f = NUM_FMT.get(k)
    return f.format(v) if f else str(v)

def render_line(det, order=FIELD_ORDER, keyed=True, null=NULL):
    parts = [(f'{k}={fmt_value(k, det.get(k), null)}' if keyed
              else fmt_value(k, det.get(k), null)) for k in order]
    return '|'.join(parts)

def parse_keyed(line, strict=True):
    out = {}
    for p in line.split('|'):
        k, sep, v = p.partition('=')
        if strict and not sep:
            raise ValueError(f'非键值片段: {p!r}')      # **fail loud**，绝不「尽力猜」
        out[k] = None if v == NULL else v
    # 类型还原
    for k in list(out):
        if out[k] is None:
            continue
        if k in INT_FIELDS:
            out[k] = int(out[k])
        elif k in FLOAT_FIELDS:
            out[k] = float(out[k])
    return out

def parse_positional(line, order=FIELD_ORDER):
    vals = line.split('|')
    out = {k: (None if v == NULL else v) for k, v in zip(order, vals)}
    return out

DET = dict(track_id=4127, cls='speed_limit', value_kph=60, conf_det=0.93, conf_cls=0.71,
           x_fwd_m=82.4, y_left_m=-3.1, sigma_dist_m=6.9, lane_assoc='ego',
           n_obs=3, state='tentative')
line = render_line(DET)
print(line)
print(f'\\n≈ {token_est(line)} token（按 4 字符/token 的经验法则）')

# ★ round-trip 测试：渲染 -> 解析 -> 逐字段相等
back = parse_keyed(line)
for k in FIELD_ORDER:
    assert back[k] == DET[k], (k, back[k], DET[k])
assert token_est(line) == SYMBOLIC_TOKENS_PER_OBJ
print('✅ round-trip 通过：11 个字段全部逐一相等，token 数与第 1 节的假设一致')"""),

    code("""# 字段消融：拿掉某个字段，下游哪条判断就做不了了
def downstream_capabilities(det):
    \"\"\"给定一条（可能缺字段的）检测，返回下游还能做的判断。\"\"\"
    caps = {}
    caps['知道是什么'] = det.get('cls') is not None
    caps['知道限速值'] = det.get('value_kph') is not None
    caps['知道还有多远'] = det.get('x_fwd_m') is not None
    caps['能算安全裕度'] = det.get('sigma_dist_m') is not None and caps['知道还有多远']
    caps['知道管不管我'] = det.get('lane_assoc') is not None
    caps['能跨帧确认'] = det.get('track_id') is not None
    caps['能区分单帧强证据/多帧弱证据'] = (det.get('n_obs') is not None
                                          and det.get('conf_cls') is not None)
    caps['能做风险决策'] = det.get('conf_cls') is not None
    return caps

FULL = downstream_capabilities(DET)
print(f\"{'拿掉的字段':<16s} {'失去的下游能力'}\")
lost_map = {}
for k in ['track_id', 'value_kph', 'conf_cls', 'sigma_dist_m', 'lane_assoc', 'n_obs']:
    d = {kk: vv for kk, vv in DET.items() if kk != k}
    c = downstream_capabilities(d)
    lost = [cap for cap in FULL if FULL[cap] and not c[cap]]
    lost_map[k] = lost
    print(f'{k:<16s} {\"、\".join(lost)}')

assert lost_map['track_id'] == ['能跨帧确认']
assert '能做风险决策' in lost_map['conf_cls'] and '能区分单帧强证据/多帧弱证据' in lost_map['conf_cls']
assert lost_map['sigma_dist_m'] == ['能算安全裕度']
assert lost_map['lane_assoc'] == ['知道管不管我']
print('\\n✅ **每个字段都必须能回答「拿掉它，下游哪条判断就做不了了」** ——')
print('   答不上来的字段就是噪声：占 token、让模板变脆、还要跟着版本走。')
print('⚠️  注意 conf_cls 一拿掉，同时丢了两项能力（风险决策 + 时序/单帧的区分），')
print('    这就是第 4 节说的「置信度不是一个字段，是一整类能力的入口」。')"""),

    md("""## 3 · 位置怎么传：针孔距离与它的不确定度

$f_{px} = \\dfrac{W_{px}}{2\\tan(\\mathrm{FOV}_h/2)}$，　$Z = \\dfrac{f_{px}S}{w_{px}}$，　$\\dfrac{\\mathrm{d}Z}{Z} = -\\dfrac{\\mathrm{d}w}{w}$"""),

    code("""W_PX, FOV_H_DEG = 1920, 60.0
SIGN_SIZE_M = 0.6                       # 中国圆形限速牌常见直径
F_PX = W_PX / (2 * math.tan(math.radians(FOV_H_DEG) / 2))
print(f'焦距 f_px = {W_PX} / (2·tan({FOV_H_DEG/2}°)) = {F_PX:.1f} px')

def distance_from_width(w_px, S=SIGN_SIZE_M, f=F_PX):
    return f * S / w_px

def sigma_distance(w_px, sigma_w_px=1.0, S=SIGN_SIZE_M, f=F_PX):
    \"\"\"一阶传播：σ_Z = (Z/w)·σ_w = (Z²/(f·S))·σ_w  —— **误差随距离平方增长**\"\"\"
    Z = distance_from_width(w_px, S, f)
    return Z / w_px * sigma_w_px

print(f\"\\n{'框宽 w':>8s} {'距离 Z':>9s} {'相对误差':>9s} {'σ_Z':>9s} {'±1σ 区间':>18s}\")
for w in [60, 24, 12, 8]:
    Z, s = distance_from_width(w), sigma_distance(w)
    print(f'{w:>7d}px {Z:>8.1f}m {1.0/w:>8.2%} {s:>8.2f}m {f\"[{Z-s:.1f}, {Z+s:.1f}]\":>18s}')

Z12, s12 = distance_from_width(12), sigma_distance(12)
assert abs(Z12 - 83.1) < 0.2 and abs(s12 - 6.9) < 0.1
# 平方关系校验：距离翻倍（框宽减半），σ 应变 4 倍
assert abs(sigma_distance(6) / sigma_distance(12) - 4.0) < 1e-9
print(f'\\n⚠️  12 px 的框 → 83.1 m，但 1 px 的框宽误差就是 **±6.9 m**。')
print('    30 m/s 下这 14 米的区间宽度 ≈ 0.5 秒决策提前量 —— 足以决定「平缓减速」还是「急刹」。')
print('✅ **σ_Z ∝ Z²**：距离翻倍，不确定度变 4 倍。所以远处目标的距离必须带 σ 一起传。')"""),

    code("""# 物理尺寸判错是更大的系统性误差来源
print('同一个 12 px 的框，若把 0.8 m 的牌子当成 0.6 m：')
Z_06, Z_08 = distance_from_width(12, 0.6), distance_from_width(12, 0.8)
print(f'  S=0.6 m → {Z_06:.1f} m ;  S=0.8 m → {Z_08:.1f} m ;  '
      f'系统性偏差 {abs(Z_08-Z_06)/Z_08:.1%}（{abs(Z_08-Z_06):.1f} m）')
assert abs(abs(Z_08 - Z_06) / Z_08 - 0.25) < 1e-9
print('  ⚠️  这是 **系统性偏差**，不是随机噪声 —— 多帧平均消不掉它。')
print('  ✅ 所以 schema 里的 cls 不只是语义，它同时是距离估计的**尺寸先验**。')

# 图像坐标 -> 自车坐标（这一步必须由感知做，不能甩给 VLA）
CX = W_PX / 2
def image_to_ego(u_px, w_px, S=SIGN_SIZE_M, f=F_PX):
    Z = distance_from_width(w_px, S, f)
    x_fwd = Z
    y_left = -(u_px - CX) * Z / f          # 图像 u 向右为正 -> 自车 y 向左为正
    return x_fwd, y_left

print(f\"\\n{'像素 u':>8s} {'框宽':>6s} {'x_fwd':>9s} {'y_left':>9s} {'在哪边'}\")
for u, w in [(960, 12), (1204, 12), (700, 12), (1204, 60)]:
    x, y = image_to_ego(u, w)
    side = '正前' if abs(y) < 1 else ('左侧' if y > 0 else '右侧')
    print(f'{u:>8d} {w:>5d}px {x:>8.1f}m {y:>8.1f}m {side}')

x_c, y_c = image_to_ego(960, 12)
assert abs(y_c) < 1e-9, '图像中心必须映射到 y_left = 0'
x_r, y_r = image_to_ego(1204, 12)
assert y_r < 0, 'u > cx 表示在图像右侧 -> 自车坐标 y_left 为负'
# **坐标系断言测试**：放一个明确在左边的目标，检查下游认为它在左边
x_l, y_l = image_to_ego(700, 12)
assert y_l > 0, '坐标系符号错误！这个十行的测试能省掉一次线上事故'
print('\\n✅ 坐标系断言测试通过（左为正 / 右为负 / 中心为 0）。')
print('⚠️  这类符号错误**只在明显偏侧的目标上暴露**，正前方的牌子看不出来 ——')
print('    于是问题只在特定路段复现，查起来极痛苦。所以必须有这个断言。')"""),

    md("""## 4 · 置信度校准：可靠性图、ECE，以及期望代价决策

合成规则：每条检测有一个隐藏难度 $d\\sim\\mathcal N(0,1)$，它**真正正确的概率**是
$q=\\sigma(1.6-1.3d)$；是否正确按 $q$ 抽 Bernoulli。
报告出来的置信度是 $\\mathrm{conf}=\\sigma(\\mathrm{logit}(q)/T)$：
$T=1$ 完全校准，$T<1$ 过自信，$T>1$ 欠自信。"""),

    code("""N_DET = 200_000
sigmoid = lambda z: 1.0 / (1.0 + np.exp(-z))
logit = lambda p: np.log(p / (1.0 - p))

_r = np.random.default_rng(0)
difficulty = _r.standard_normal(N_DET)
q_true = sigmoid(1.6 - 1.3 * difficulty)             # 该检测**真正**正确的概率
is_correct = _r.random(N_DET) < q_true

def reported_conf(T):
    \"\"\"温度缩放：T=1 完全校准；T<1 过自信；T>1 欠自信。\"\"\"
    return sigmoid(logit(np.clip(q_true, 1e-6, 1 - 1e-6)) / T)

def ece(conf, correct, n_bins=15):
    e, edges = 0.0, np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        m = (conf >= edges[i]) & (conf < edges[i + 1] if i < n_bins - 1 else conf <= 1.0)
        if m.sum() == 0:
            continue
        e += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(e)

print(f'基础正确率 = {is_correct.mean():.4f}  → **感知错误率 {1-is_correct.mean():.2%}**')
print(f'\\n可靠性图（T=1，完全校准）：')
c1 = reported_conf(1.0)
edges = np.linspace(0, 1, 11)
print(f\"{'置信区间':>12s} {'样本占比':>9s} {'平均置信':>9s} {'实际准确率':>11s} {'差':>8s}\")
for i in range(10):
    m = (c1 >= edges[i]) & (c1 < edges[i + 1] if i < 9 else c1 <= 1.0)
    if m.sum() < 50:
        continue
    print(f'[{edges[i]:.1f},{edges[i+1]:.1f}) {m.mean():>9.1%} {c1[m].mean():>9.3f} '
          f'{is_correct[m].mean():>11.3f} {c1[m].mean()-is_correct[m].mean():>+8.3f}')
assert ece(c1, is_correct) < 0.01
print(f'\\nECE(T=1) = {ece(c1, is_correct):.4f}  ← 每个箱里「说 0.8 就真的对 80%」')"""),

    code("""C_WRONG, C_REJ = 10.0, 1.5                  # 采纳一个错检测的代价 / 拒绝退保守的代价
TAU_BAYES = 1.0 - C_REJ / C_WRONG           # 贝叶斯最优阈值，**算出来的不是调出来的**
print(f'贝叶斯阈值 p* = 1 − C_rej/C_wrong = 1 − {C_REJ}/{C_WRONG} = {TAU_BAYES}')

def expected_cost(conf, tau):
    \"\"\"用**真实** q 结算实际代价；决策却只能看 conf（这正是失准伤人的地方）。\"\"\"
    acc = conf >= tau
    return float(np.mean(acc * (1 - q_true) * C_WRONG + (~acc) * C_REJ))

no_conf_cost = float(np.mean((1 - q_true) * C_WRONG))     # 不传置信度 = 全部采纳
all_rej_cost = C_REJ                                       # 完全不用感知

print(f\"\\n{'温度 T':>7s} {'ECE':>8s} {'接受率':>8s} {'期望代价':>9s} {'相对最优':>9s}\")
rows = []
for T in [0.2, 0.35, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]:
    c = reported_conf(T)
    cost_ = expected_cost(c, TAU_BAYES)
    rows.append((T, ece(c, is_correct), cost_, float((c >= TAU_BAYES).mean())))
best_cost = min(r[2] for r in rows)
for T, e, cost_, acc in rows:
    print(f'{T:>7.2f} {e:>8.4f} {acc:>8.1%} {cost_:>9.4f} {cost_/best_cost-1:>+8.1%}')
print(f'\\n{\"不传置信度（全部采纳）\":<22s} {no_conf_cost:>9.4f} {no_conf_cost/best_cost-1:>+8.1%}')
print(f'{\"完全忽略感知（全部拒绝）\":<22s} {all_rej_cost:>9.4f} {all_rej_cost/best_cost-1:>+8.1%}')

best_T = min(rows, key=lambda r: r[2])[0]
best_ece_T = min(rows, key=lambda r: r[1])[0]
assert best_T == 1.0 and best_ece_T == 1.0, '期望代价与 ECE 应在同一个 T 取到最小'
assert no_conf_cost > best_cost * 1.9, '不传置信度的代价应接近最优的两倍'
assert all_rej_cost > best_cost
print('\\n★ **期望代价恰好在 ECE 最小（完全校准）处取到最小值** —— 这不是巧合：')
print('  贝叶斯决策规则用真实概率时最优，用被扭曲的概率必然次优。')
print(f'⚠️  不传置信度的代价比最优高 {no_conf_cost/best_cost-1:.0%}，比「完全不用感知」还差得多但也没好到哪去。')"""),

    code("""# ★ 必须讲清楚的微妙点：单调失准 + 重调阈值 = 决策完全不变
def auc(score, label):
    order = np.argsort(score, kind='stable')
    ranks = np.empty(len(score)); ranks[order] = np.arange(1, len(score) + 1)
    npos = int(label.sum()); nneg = len(score) - npos
    return float((ranks[label].sum() - npos * (npos + 1) / 2) / (npos * nneg))

grid = np.linspace(0.01, 0.999, 400)
print(f\"{'T':>6s} {'AUC(排序质量)':>14s} {'固定 τ*=0.85 的代价':>19s} {'重调最优阈值后':>15s}\")
aucs, fixed, tuned = [], [], []
for T in [0.35, 0.5, 1.0, 2.0, 3.0]:
    c = reported_conf(T)
    a = auc(c, is_correct)
    f_ = expected_cost(c, TAU_BAYES)
    t_ = min(expected_cost(c, t) for t in grid)
    aucs.append(a); fixed.append(f_); tuned.append(t_)
    print(f'{T:>6.2f} {a:>14.6f} {f_:>19.4f} {t_:>15.4f}')

assert max(aucs) - min(aucs) < 1e-6, '单调变换不改变排序，AUC 必须完全相同'
assert max(tuned) - min(tuned) < 0.005, '重调阈值后可达代价几乎相同'
assert max(fixed) - min(fixed) > 0.3, '固定阈值下失准会显著变差'
print('\\n⚠️  **AUC 完全相同、重调阈值后代价也相同** —— 这就是「调调阈值就好了，')
print('    所以校准没用」这个错误结论的来源。它在那个特定配置下确实「好了」。')
print('\\n✅ 但这个补偿在三种情况下立刻塌掉：')
print('   ① 阈值是固定的 / 多个消费者共享 → 感知一升级，全线行为漂移，没人会想到去重调')
print('   ② 决策要用概率做**算术**（期望代价、风险预算、代价不对称门控）→ 系统性算错')
print('   ③ 多源融合（相机 p₁ × 地图先验 p₂）→ 两个失准概率相乘，误差放大且方向不可预测')
print('\\n★ 所以：**校准不是为了改善排序（它做不到），是为了让「概率」这个数能被当作概率来算。**')"""),

    md("""## 5 · 感知错误注入实验：下游动作错误率随接口设计怎么变

场景：每一帧的真实限速 $\\in\\{60,80,100,120\\}$；感知按上面的 $q$ 给出可能错误的读数；
地图/上一段先验有 25% 的错误率（会因施工、限速调整而过时）。
下游要决定**应用哪个限速**，代价严重不对称：**超速 ×10，过度限速 ×3**。"""),

    code("""LIMITS = np.array([60, 80, 100, 120])
_r2 = np.random.default_rng(0)
i_true = _r2.integers(0, 4, N_DET)
L_true = LIMITS[i_true]
# 感知读数：正确时 = 真值；错误时随机错到别的档
off1 = _r2.integers(1, 4, N_DET)
L_det = np.where(is_correct, L_true, LIMITS[(i_true + off1) % 4])
# 地图 / 上一段先验：75% 正确
prior_ok = _r2.random(N_DET) < 0.75
off2 = _r2.integers(1, 4, N_DET)
L_prior = np.where(prior_ok, L_true, LIMITS[(i_true + off2) % 4])

print(f'感知错误率 {(L_det != L_true).mean():.2%}   先验错误率 {(L_prior != L_true).mean():.2%}')

W_OVER, W_UNDER = 10.0, 3.0        # 超速是安全问题；过度限速是效率/舒适问题
def action_risk(applied):
    over = float((applied > L_true).mean())          # 超速：危险且不可恢复
    under = float((applied < L_true).mean())         # 过度限速：低效但可恢复
    return over, under, W_OVER * over + W_UNDER * under

POLICIES = {
    'A 不传置信度（全采纳）': lambda c: L_det,
    'B 对称阈值 0.70':        lambda c: np.where(c >= 0.70, L_det, L_prior),
    'C 非对称门控':            lambda c: np.where(
        np.where(L_det > L_prior, c >= 0.90, c >= 0.30), L_det, L_prior),
    'D 完全忽略感知':          lambda c: L_prior,
}

for T, tag in [(1.0, '校准 T=1'), (0.3, '过自信 T=0.3'), (3.0, '欠自信 T=3')]:
    c = reported_conf(T)
    print(f'\\n─── {tag}（ECE={ece(c, is_correct):.4f}）───')
    print(f\"{'下游策略':<24s} {'超速率':>8s} {'过度限速率':>11s} {'加权风险':>9s}\")
    for name, fn in POLICIES.items():
        o, u, r = action_risk(fn(c))
        print(f'{name:<24s} {o:>8.2%} {u:>11.2%} {r:>9.4f}')"""),

    code("""c_cal, c_over, c_under = reported_conf(1.0), reported_conf(0.3), reported_conf(3.0)
rA = action_risk(POLICIES['A 不传置信度（全采纳）'](c_cal))
rB = action_risk(POLICIES['B 对称阈值 0.70'](c_cal))
rC = action_risk(POLICIES['C 非对称门控'](c_cal))
rD = action_risk(POLICIES['D 完全忽略感知'](c_cal))
rC_bad = action_risk(POLICIES['C 非对称门控'](c_over))
rC_under = action_risk(POLICIES['C 非对称门控'](c_under))

# ① 能拒绝就有收益；② 非对称门控收益更大；③ 感知确实有价值
assert rB[2] < rA[2] and rC[2] < rB[2] and rA[2] < rD[2]
# ④ 非对称门控专打「超速」这个高代价方向
assert rC[0] < rA[0] * 0.35, '超速率应至少降 65%'
# ⑤ 失准让规则失效
assert rC_bad[2] > rC[2] * 1.2, '过自信让加权风险涨 20% 以上'
assert rC_bad[0] > rC[0] * 1.8, '过自信让超速率翻倍'
# ⑥ 欠自信换来的是过度保守（换一组代价权重结论就会翻）
assert rC_under[1] > rC[1] and rC_under[2] > rC[2]

print(f'不传置信度         → 加权风险 {rA[2]:.4f}，超速率 {rA[0]:.2%}')
print(f'对称阈值（校准）    → 加权风险 {rB[2]:.4f}（{rB[2]/rA[2]-1:+.0%}）')
print(f'**非对称门控（校准）** → 加权风险 {rC[2]:.4f}（{rC[2]/rA[2]-1:+.0%}），'
      f'超速率 {rC[0]:.2%}（**{rC[0]/rA[0]-1:+.0%}**）')
print(f'非对称门控（过自信） → 加权风险 {rC_bad[2]:.4f}（比校准差 {rC_bad[2]/rC[2]-1:+.0%}），'
      f'超速率 {rC_bad[0]:.2%}')
print('\\n★ 「p≥0.90 才允许提速」这条规则的**全部效力**建立在「0.90 真的意味着 90%」上。')
print('  过自信的模型把一堆实际 60% 正确率的检测标成 0.92 —— 门槛形同虚设。')
print(f'\\n⚠️  保守不是免费的：非对称门控把过度限速率从 {rA[1]:.1%} 抬到 {rC[1]:.1%}。')
print('    正确做法不是「宁可错杀」，而是**把 C_over 与 C_under 显式写下来，由代价推出门槛** ——')
print('    这样产品说「减速太频繁」时，你改的是一个有明确含义的代价参数，不是凭感觉挪阈值。')"""),

    md("""## 6 · 幻觉：输入幻觉、输出幻觉与 grounding 校验

用一个**规则式的玩具 VLA**（决定性、可断言）来演示「合理化」与两种幻觉。"""),

    code("""def toy_vla(dets, use_confidence=True, conf_gate=0.65):
    \"\"\"玩具 VLA：忠实地以输入为条件生成动作与解释，并显式引用 track_id。\"\"\"
    considered = [d for d in dets
                  if (not use_confidence) or d['conf_cls'] >= conf_gate]
    if not considered:
        return dict(action='KEEP', target_kph=None,
                    explanation='未获得足够可信的标志信息，保持当前策略。',
                    cited=[], hedged=True)
    d = min(considered, key=lambda x: x['x_fwd_m'])     # 最近的那块牌子
    if d['cls'] == 'no_entry':
        return dict(action='LANE_CHANGE_RIGHT', target_kph=40,
                    explanation=(f\"前方 {d['x_fwd_m']:.0f} m 检测到禁止驶入标志\"
                                 f\"(track#{d['track_id']})，本车道不可通行；\"
                                 f\"右侧车道空闲，建议提前变道并减速至 40 km/h 后并线。\"),
                    cited=[d['track_id']], hedged=False)
    if d['cls'] == 'speed_limit':
        return dict(action='SET_SPEED', target_kph=d['value_kph'],
                    explanation=(f\"依据 track#{d['track_id']} 限速标志，\"
                                 f\"设定目标车速 {d['value_kph']} km/h。\"),
                    cited=[d['track_id']], hedged=False)
    return dict(action='KEEP', target_kph=None, explanation='无相关标志。',
                cited=[], hedged=True)

# —— 输入幻觉：一块**不存在的**禁止驶入（其实是广告牌），置信度 0.62 ——
FP = dict(track_id=9001, cls='no_entry', value_kph=None, conf_det=0.71, conf_cls=0.62,
          x_fwd_m=62.0, y_left_m=-2.4, sigma_dist_m=4.5, lane_assoc='ego',
          n_obs=1, state='tentative')
REAL = dict(DET)

out_naive = toy_vla([REAL, FP], use_confidence=False)
out_gated = toy_vla([REAL, FP], use_confidence=True, conf_gate=0.65)
print('【不传/不用置信度】')
print(' 动作:', out_naive['action'], '| 目标车速:', out_naive['target_kph'])
print(' 解释:', out_naive['explanation'])
print(' 表达了不确定吗:', out_naive['hedged'])
print('\\n【置信度门控 0.65】')
print(' 动作:', out_gated['action'], '| 目标车速:', out_gated['target_kph'])
print(' 解释:', out_gated['explanation'])

assert out_naive['action'] == 'LANE_CHANGE_RIGHT' and not out_naive['hedged']
assert out_gated['action'] == 'SET_SPEED' and out_gated['target_kph'] == 60
print('\\n⚠️  输出**语言流畅、逻辑自洽、完全错误**，而且没有任何一处表达「我不确定」。')
print('    这是 silent failure —— 比崩溃危险得多，因为没有信号触发兜底。')
print('✅ 一个 0.65 的门控就把它挡住了（真牌 0.71 通过、误检 0.62 被拦），')
print('   而门控能存在的前提，就是接口传了 conf_cls。')"""),

    code("""# —— 输出幻觉：VLA 引用了输入里根本不存在的 track_id ——
def grounding_check(vla_out, dets):
    \"\"\"输出侧校验：引用的每个 track_id 必须存在于本帧输入。十几行、零延迟。\"\"\"
    valid = {d['track_id'] for d in dets}
    bad = [t for t in vla_out['cited'] if t not in valid]
    # 解释文本里出现的 track#NNNN 也要能对上
    mentioned = [int(x) for x in re.findall(r'track#(\\d+)', vla_out['explanation'])]
    bad += [t for t in mentioned if t not in valid]
    return (len(bad) == 0), sorted(set(bad))

good = toy_vla([REAL], use_confidence=True)
ok1, bad1 = grounding_check(good, [REAL])
hallu = dict(good)
hallu['cited'] = [7777]
hallu['explanation'] = '路口通常设有停车让行标志(track#7777)，建议完全停车。'
ok2, bad2 = grounding_check(hallu, [REAL])
print(f'正常输出   grounding: {ok1}  未对上的 ID: {bad1}')
print(f'编造的输出 grounding: {ok2}  未对上的 ID: {bad2}  → **整条输出作废，走兜底**')
assert ok1 and not ok2 and bad2 == [7777]

# —— 度量：沉默错误率（错了、且输出未表达不确定）——
def silent_error_rate(n=4000, fp_rate=0.15, use_confidence=True, gate=0.65, seed=11):
    r = np.random.default_rng(seed)
    n_err = n_silent = 0
    for _ in range(n):
        dets = [dict(REAL)]
        truth = 'SET_SPEED'
        if r.random() < fp_rate:                      # 注入一次误检
            fp = dict(FP); fp['conf_cls'] = float(r.uniform(0.25, 0.85))
            dets.append(fp)
        out = toy_vla(dets, use_confidence=use_confidence, conf_gate=gate)
        if out['action'] != truth:
            n_err += 1
            if not out['hedged']:
                n_silent += 1
    return n_err / n, n_silent / n

for label, uc in [('不用置信度', False), ('置信度门控 0.65', True)]:
    er, sr = silent_error_rate(use_confidence=uc)
    print(f'{label:<16s} 下游动作错误率 {er:>6.2%}   其中**沉默错误** {sr:>6.2%}')
er_off, _ = silent_error_rate(use_confidence=False)
er_on, _ = silent_error_rate(use_confidence=True)
assert er_on < er_off * 0.5, '置信度门控应把动作错误率至少砍一半'
print('\\n✅ 两类幻觉要用**不同手段**：输入幻觉靠置信度门控 + 代价不对称；')
print('   输出幻觉靠 grounding 校验（引用不到就整条作废）。')
print('★ 最该被追踪的单一指标是**沉默错误率**：错了、且输出里没有任何不确定信号。')"""),

    md("""## 7 · prompt 模板的三种静默故障

位置错位 / 哨兵值被规则吃掉 / 数值格式漂移——**共同特征是不报错**。"""),

    code("""# —— 故障① 位置式解析 + 感知升级插入新字段 = 静默错位 ——
NEW_ORDER = FIELD_ORDER[:2] + ['src'] + FIELD_ORDER[2:]      # 感知 v1.4 插入了 src
DET_V14 = dict(DET); DET_V14['src'] = 'front_wide'

line_keyed_v14 = render_line(DET_V14, NEW_ORDER, keyed=True)
line_pos_v14 = render_line(DET_V14, NEW_ORDER, keyed=False)
pk = parse_keyed(line_keyed_v14)                 # 下游仍是 v1.3 的解析器
pp = parse_positional(line_pos_v14, FIELD_ORDER)  # 下游仍按旧顺序切

print('感知升级插入 src 字段后，下游仍用旧解析器：')
print(f'  键值式  x_fwd_m = {pk[\"x_fwd_m\"]}   value_kph = {pk[\"value_kph\"]}   ✅ 正确')
print(f'  位置式  x_fwd_m = {pp[\"x_fwd_m\"]}   value_kph = {pp[\"value_kph\"]}   ❌ **静默错位**')
assert pk['x_fwd_m'] == 82.4 and pk['value_kph'] == 60
assert pp['x_fwd_m'] != '82.4' and pp['value_kph'] != '60'
print(f'\\n  位置式把**置信度读成了距离**（{pp[\"x_fwd_m\"]}），还不报错。')
print(f'  token 成本：位置式 {token_est(line_pos_v14)} < 键值式 {token_est(line_keyed_v14)} ——')
print('  **省下的 token 换来的是一整类静默故障。不值。**')"""),

    code("""# —— 故障② 哨兵值 vs 显式 null ——
DET_NO_DIST = dict(DET); DET_NO_DIST['x_fwd_m'] = None; DET_NO_DIST['sigma_dist_m'] = None
line_null = render_line(DET_NO_DIST, null='null')
line_sentinel = render_line(DET_NO_DIST, null='-1')

def downstream_rule(parsed):
    \"\"\"下游的一条常见规则：忽略车后目标（x<0）；距离未知则走保守分支。\"\"\"
    x = parsed['x_fwd_m']
    if x is None:
        return 'CONSERVATIVE(距离未知→保守)'
    return 'DROP(车后目标)' if float(x) < 0 else 'USE'

r_null = downstream_rule(parse_keyed(line_null))
r_sent = downstream_rule(parse_keyed(line_sentinel))
print(f'  缺失用 null  → {r_null}')
print(f'  缺失用 -1    → {r_sent}   ❌ **一个有效检测被静默丢掉，且没有任何日志**')
assert r_null.startswith('CONSERVATIVE') and r_sent.startswith('DROP')

# —— 故障③ 数值格式漂移 ——
print('\\n数值格式漂移（训练时 60，推理时变成 60.0 / 6.0e+01）：')
for s in ['60', '60.0', '6.0e+01']:
    try:
        v = int(s); note = '✅ 解析成功'
    except ValueError:
        v = None; note = '❌ int() 抛异常 —— **fail loud，其实是好事**'
    print(f'  int({s!r}) -> {v}   token 数 {token_est(s)}   {note}')

# —— 自然语言 vs 紧凑 schema 的 token 账 ——
NL = ('There is a speed limit sign with track id 4127 detected ahead. The detection '
      'confidence is 0.93 and the classification confidence is 0.71. It indicates a '
      'speed limit of 60 kph. It is located 82.4 meters in front of the ego vehicle and '
      '3.1 meters to the right, with a distance uncertainty of 6.9 meters. It is '
      'associated with the ego lane, has been observed 3 times, and its state is tentative.')
t_keyed, t_nl = token_est(render_line(DET)), token_est(NL)
print(f'\\n同样的信息：紧凑键值 {t_keyed} token vs 自然语言 {t_nl} token '
      f'→ **贵 {t_nl/t_keyed:.1f} 倍**，且无法严格解析与校验')
assert t_nl > 2 * t_keyed
print('\\n✅ 三条铁律：①键值不要位置 ②字段顺序固定并写进 schema_version ③缺失值用显式 null')
print('★ **prompt 模板不是 UI，是 ABI** —— 它恰好长得像人话，而这正是它最危险的地方。')"""),

    md("""## ✏️ 练习 1：完整 prompt 构建（稳定排序 + 截断标记 + 空场景）

实现 `build_prompt(dets, ego, max_tokens)`：
- 头部：`schema=tsr/1.3|ego_speed_mps=27.8`
- **稳定排序**：先按 `LANE_PRIORITY[lane_assoc]`，再按 `x_fwd_m` 升序（同值时按 `track_id`）
- 逐条加入 `render_line(d)`，用 `token_est` 估算，**并为尾部标记预留 `TAIL_TOKENS`**
- 装不下的丢弃并计数；空场景写 `signs=[]|n=0`
- 尾部固定为 `truncated=<true|false>|n_dropped=<M>`
- 各部分用 `\\n` 连接"""),

    code("""# LANE_PRIORITY / TAIL_TOKENS / token_est 已在前面定义好，直接用

def build_prompt(dets, ego, max_tokens=500):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
def _mk(tid, lane, x, cls='speed_limit', v=60):
    d = dict(DET); d.update(track_id=tid, lane_assoc=lane, x_fwd_m=x, cls=cls, value_kph=v)
    return d

EGO = {'speed_mps': 27.8}
DETS = [_mk(11, 'service', 30.0), _mk(12, 'ego', 82.4), _mk(13, 'ego', 41.0),
        _mk(14, 'opposite', 25.0), _mk(15, 'left', 60.0), _mk(16, 'ego', 120.0)]

p_full = build_prompt(DETS, EGO, max_tokens=500)
ids = [int(m) for m in re.findall(r'track_id=(\\d+)', p_full)]
assert ids == [13, 12, 16, 15, 14, 11], ids       # ego(按距离) -> left -> opposite/service
assert 'truncated=false|n_dropped=0' in p_full
assert p_full.startswith(f'schema={SCHEMA_VERSION}|ego_speed_mps=27.8')

# 顺序无关：打乱输入应得到**完全相同**的 prompt（否则 badcase 无法重放）
import random as _rd
sh = DETS[:]; _rd.Random(0).shuffle(sh)
assert build_prompt(sh, EGO, 500) == p_full, '排序必须稳定且与输入顺序无关'

p_tr = build_prompt(DETS, EGO, max_tokens=120)
kept = len(re.findall(r'track_id=', p_tr))
n_drop = int(re.search(r'n_dropped=(\\d+)', p_tr).group(1))
assert 'truncated=true' in p_tr and kept + n_drop == len(DETS)
assert token_est(p_tr) <= 120, token_est(p_tr)
assert kept >= 1 and re.findall(r'track_id=(\\d+)', p_tr)[0] == '13', '最该保留的是最近的本车道目标'

p_empty = build_prompt([], EGO, 500)
assert 'signs=[]|n=0' in p_empty and 'truncated=false' in p_empty
print(p_tr)
print(f'\\n完整 {token_est(p_full)} token / 截断后 {token_est(p_tr)} token，丢弃 {n_drop} 个')
print('✅ 练习 1 通过：**排序稳定（可重放）+ 截断显式声明（模型知道自己看到的不全）+ ')
print('   空场景可表达（「我看了，确实没有」≠「什么都没写」）**')"""),

    md("""## ✏️ 练习 2：后处理校准（温度搜索）

实现 `fit_temperature(conf_raw, correct, temps)`：对每个候选温度 $T$ 计算
$\\mathrm{conf}' = \\sigma(\\mathrm{logit}(\\mathrm{conf})/T)$ 的 ECE，返回 `(best_T, best_ece)`。
注意先把 `conf` 裁剪到 $[10^{-6}, 1-10^{-6}]$ 再取 logit。"""),

    code("""def fit_temperature(conf_raw, correct, temps):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
TEMPS = np.exp(np.linspace(np.log(0.2), np.log(6.0), 61))
raw_over = reported_conf(0.3)                    # 过自信：需要 T≈1/0.3≈3.33 才能校回来
bT, bE = fit_temperature(raw_over, is_correct, TEMPS)
print(f'过自信输入: 原始 ECE={ece(raw_over, is_correct):.4f} -> 校准后 ECE={bE:.4f}  (T*={bT:.2f})')
assert 2.5 < bT < 4.5, bT
assert bE < 0.01 and bE < ece(raw_over, is_correct) / 5

raw_under = reported_conf(2.5)                   # 欠自信：需要 T≈0.4
bT2, bE2 = fit_temperature(raw_under, is_correct, TEMPS)
print(f'欠自信输入: 原始 ECE={ece(raw_under, is_correct):.4f} -> 校准后 ECE={bE2:.4f}  (T*={bT2:.2f})')
assert 0.3 < bT2 < 0.55, bT2

bT3, _ = fit_temperature(reported_conf(1.0), is_correct, TEMPS)
assert 0.85 < bT3 < 1.2, '本来就校准的，T* 应接近 1'

# 校准之后，固定贝叶斯阈值下的代价应当恢复到最优
cal = sigmoid(logit(np.clip(raw_over, 1e-6, 1 - 1e-6)) / bT)
print(f'\\n固定 τ*={TAU_BAYES} 下的期望代价: 未校准 {expected_cost(raw_over, TAU_BAYES):.4f} '
      f'-> 校准后 {expected_cost(cal, TAU_BAYES):.4f}')
assert expected_cost(cal, TAU_BAYES) < expected_cost(raw_over, TAU_BAYES) * 0.85
print('✅ 练习 2 通过：温度缩放只有**一个参数**，用几千条带标注的验证样本就能拟合，')
print('   却能把「概率可以被当作概率来算」这件事恢复回来 —— 性价比极高的一步。')"""),

    md("""## ✏️ 练习 3：从代价推导门槛

实现 `bayes_threshold(c_wrong, c_rej)` 与
`asymmetric_apply(L_det, L_prior, conf, tau_up, tau_down)`：
提高限速（`L_det > L_prior`）要求 `conf >= tau_up`，否则只要 `conf >= tau_down`；
不满足则退回 `L_prior`。"""),

    code("""def bayes_threshold(c_wrong, c_rej):
    # TODO: p* = 1 - c_rej/c_wrong，裁剪到 [0, 1]
    raise NotImplementedError

def asymmetric_apply(L_det, L_prior, conf, tau_up, tau_down):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测（先手算）——
assert abs(bayes_threshold(10.0, 1.5) - 0.85) < 1e-12
assert abs(bayes_threshold(10.0, 3.0) - 0.70) < 1e-12
assert bayes_threshold(2.0, 5.0) == 0.0, '拒绝比犯错还贵 -> 永远采纳'
assert abs(bayes_threshold(100.0, 1.0) - 0.99) < 1e-12, '代价越不对称，门槛越高'

d_ = np.array([120, 60, 120, 60]); p_ = np.array([100, 100, 100, 100])
c_ = np.array([0.95, 0.50, 0.50, 0.20])
got = asymmetric_apply(d_, p_, c_, tau_up=0.90, tau_down=0.30)
assert got.tolist() == [120, 60, 100, 100], got.tolist()
#   ↑ 提速+高置信=采纳 / 降速+中置信=采纳 / 提速+中置信=拒绝 / 降速+极低置信=拒绝

# 用它复现主实验
tau_up, tau_down = 0.90, 0.30
ap = asymmetric_apply(L_det, L_prior, reported_conf(1.0), tau_up, tau_down)
o, u, r = action_risk(ap)
print(f'非对称门控(校准): 超速 {o:.2%}  过度限速 {u:.2%}  加权风险 {r:.4f}')
assert abs(r - rC[2]) < 1e-9

print(f\"\\n{'C_wrong':>8s} {'C_rej':>7s} {'p*':>7s} {'超速率':>8s} {'过度限速率':>11s} {'加权风险':>9s}\")
for cw, cr in [(10.0, 5.0), (10.0, 3.0), (10.0, 1.5), (20.0, 1.0)]:
    t = bayes_threshold(cw, cr)
    a2 = asymmetric_apply(L_det, L_prior, reported_conf(1.0), tau_up=t, tau_down=0.30)
    o2, u2, r2 = action_risk(a2)
    print(f'{cw:>8.1f} {cr:>7.1f} {t:>7.2f} {o2:>8.2%} {u2:>11.2%} {r2:>9.4f}')
print('\\n✅ 练习 3 通过：**门槛是代价的函数，不是调参得来的**。')
print('   产品说「减速太频繁」时，你改的是 C_rej 这个有明确含义的数，而不是凭感觉挪阈值。')"""),

    md("""## ✏️ 练习 4：接口契约校验器

实现 `validate_message(msg)`，返回 `(ok, sorted(errors))`。检查项：
`schema_version` 在 `SUPPORTED_VERSIONS` 里；每条 sign 的 `REQUIRED` 字段都存在且非 `None`；
`conf_det`/`conf_cls` ∈ [0,1]；`x_fwd_m` ∈ [0, 300]；`sigma_dist_m` ≥ 0；
`lane_assoc` ∈ `LANE_PRIORITY`。错误串格式：`f'sign[{i}].{field}: {reason}'`，版本错误为 `'schema_version: unsupported'`。"""),

    code("""SUPPORTED_VERSIONS = {'tsr/1.2', 'tsr/1.3'}
REQUIRED = ['track_id', 'cls', 'conf_det', 'conf_cls', 'x_fwd_m', 'lane_assoc']

def validate_message(msg):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
good = {'schema_version': 'tsr/1.3', 'signs': [dict(DET)]}
ok, errs = validate_message(good)
assert ok and errs == [], errs

bad_sign = dict(DET)
bad_sign.update(conf_cls=1.4, x_fwd_m=-1.0, lane_assoc='ego_lane')
del bad_sign['track_id']
bad = {'schema_version': 'tsr/2.0', 'signs': [dict(DET), bad_sign]}
ok2, errs2 = validate_message(bad)
assert not ok2
assert 'schema_version: unsupported' in errs2
assert any(e.startswith('sign[1].track_id') for e in errs2)
assert any(e.startswith('sign[1].conf_cls') for e in errs2)
assert any(e.startswith('sign[1].x_fwd_m') for e in errs2)
assert any(e.startswith('sign[1].lane_assoc') for e in errs2)
assert not any(e.startswith('sign[0]') for e in errs2), '第 0 条是合法的，不应报错'
print('检出的问题:')
for e in errs2:
    print('  -', e)
print(f'\\n共 {len(errs2)} 项')
assert len(errs2) == 5
print('\\n✅ 练习 4 通过：**契约校验器要放在接口的消费侧，且必须 fail loud**。')
print('   它和第 3 节的坐标系断言测试一起，构成「把约定变成可执行检查」的最小集合。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def build_prompt(dets, ego, max_tokens=500):
    ordered = sorted(dets, key=lambda d: (LANE_PRIORITY.get(d.get('lane_assoc'), 9),
                                          d['x_fwd_m'], d['track_id']))
    header = f\"schema={SCHEMA_VERSION}|ego_speed_mps={ego['speed_mps']:.1f}\"
    kept, dropped = [], 0
    for i, d in enumerate(ordered):
        cand = kept + [render_line(d)]
        if token_est('\\n'.join([header] + cand)) + TAIL_TOKENS > max_tokens:
            dropped = len(ordered) - i
            break
        kept = cand
    body = '\\n'.join(kept) if kept else 'signs=[]|n=0'
    tail = f\"truncated={'true' if dropped else 'false'}|n_dropped={dropped}\"
    return '\\n'.join([header, body, tail])"""),

    code("""# 练习 2 参考答案
def fit_temperature(conf_raw, correct, temps):
    z = logit(np.clip(np.asarray(conf_raw, dtype=float), 1e-6, 1 - 1e-6))
    best_T, best_e = None, float('inf')
    for T in temps:
        e = ece(sigmoid(z / T), correct)
        if e < best_e:
            best_T, best_e = float(T), e
    return best_T, best_e"""),

    code("""# 练习 3 参考答案
def bayes_threshold(c_wrong, c_rej):
    return float(np.clip(1.0 - c_rej / c_wrong, 0.0, 1.0))

def asymmetric_apply(L_det, L_prior, conf, tau_up, tau_down):
    raising = np.asarray(L_det) > np.asarray(L_prior)
    accept = np.where(raising, np.asarray(conf) >= tau_up, np.asarray(conf) >= tau_down)
    return np.where(accept, L_det, L_prior)"""),

    code("""# 练习 4 参考答案
def validate_message(msg):
    errs = []
    if msg.get('schema_version') not in SUPPORTED_VERSIONS:
        errs.append('schema_version: unsupported')
    for i, s in enumerate(msg.get('signs', [])):
        for f in REQUIRED:
            if s.get(f) is None:
                errs.append(f'sign[{i}].{f}: missing')
        for f in ('conf_det', 'conf_cls'):
            v = s.get(f)
            if v is not None and not (0.0 <= v <= 1.0):
                errs.append(f'sign[{i}].{f}: out of [0,1] ({v})')
        x = s.get('x_fwd_m')
        if x is not None and not (0.0 <= x <= 300.0):
            errs.append(f'sign[{i}].x_fwd_m: out of [0,300] ({x})')
        sd = s.get('sigma_dist_m')
        if sd is not None and sd < 0:
            errs.append(f'sign[{i}].sigma_dist_m: negative ({sd})')
        la = s.get('lane_assoc')
        if la is not None and la not in LANE_PRIORITY:
            errs.append(f'sign[{i}].lane_assoc: unknown enum ({la})')
    return (len(errs) == 0), sorted(errs)"""),

    md("""---
## 🧪 真实工程胶囊：TSR → VLA 接口规范与评审检查单"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════════
# TSR → VLA 感知输出接口：规范 + 评审检查单
# （可直接作为接口评审会的议程；每一条都对应一类真实故障）
# ══════════════════════════════════════════════════════════════════════

# ── ① 先定融合层次，再谈字段 ────────────────────────────────────────
#   判据：**这个信息出错以后，需不需要事后说清楚？**
#     需要（限速值、禁行、停车让行）-> 符号级，进日志、可审计
#     不需要（稠密几何、上下文）    -> 中间表示级 / BEV query，token 恒定
#   量产形态几乎总是混合的，两条通路互为交叉校验。

# ── ② schema（每个字段都要能回答「拿掉它，下游哪条判断做不了」）────
#   schema_version   接口演进的唯一抓手；进 prompt 第一行 + 进模型卡
#   t_capture_ms     数据新鲜度；配 ttl_ms 做看门狗
#   track_id         **跨帧确认、迟滞、状态机的前提**；没它 10 帧 = 10 块牌子
#   cls / cls_id     语义；同时是单目距离估计的**尺寸先验**
#   value_kph        限速值**独立成字段**（别编进类别名，会让类别数爆炸）
#   cls_top2         第二候选 + 概率 -> 下游才能表达「60 还是 80 说不准」
#   conf_det/conf_cls **分开传，不要提前融合**（下游用法不同）
#   x_fwd_m/y_left_m 自车坐标，**单位写进字段名**；不要传图像像素
#   sigma_dist_m     σ_Z ∝ Z²；12px 的框 -> 83m ± 6.9m
#   bbox_wh_px       距离估计输入 + 免费的可靠性代理
#   lane_assoc       **管不管我**；感知有车道线有能力算，下游只能猜
#   n_obs / state    时序一致性，与置信度**正交**
#   src / ttl_ms     多相机仲裁 / 有效期

# ── ③ 置信度（本接口的核心，单列一条）────────────────────────────
#   · 必须传。不传 = **永久删除下游做风险决策的能力**
#   · 必须校准。用几千条验证样本拟合一个温度参数即可（1 个参数！）
#       T* = argmin_T ECE(sigmoid(logit(conf)/T))
#   · 阈值从代价推导，不是调出来的：p* = 1 - C_rej / C_wrong
#   · **非对称门控**：往安全方向低门槛、往风险方向高门槛
#       raise_limit  -> require conf >= 0.90
#       lower_limit  -> require conf >= 0.30
#     实测：超速率 11.4% -> 3.1%（-72%），加权风险 -44%
#   · 校准漂移要监控：夜间/雨雾/新区域上会失效 -> **分场景各校一个温度**

# ── ④ prompt 模板 = ABI，不是 UI ───────────────────────────────────
#   ① 键值不要位置（位置式在插字段时**静默错位**）
#   ② 字段顺序固定；改顺序 = 升版本 = 重新评测
#   ③ 缺失值用显式 null；**绝不用 -1 这类哨兵**（会被下游规则静默吃掉）
#   ④ 数值格式定死（60.0 vs 60 是不同 token 序列 —— 文本层的训练/部署一致性）
#   ⑤ 排序规则确定（lane 优先级 -> 距离 -> track_id），否则同帧两次渲染不同
#   ⑥ 截断要显式声明：truncated=true|n_dropped=7
#   ⑦ 空场景要能表达：signs=[]|n=0（「我看了确实没有」≠「什么都没写」）

# ── ⑤ 必须实现的四个检查（加起来不到 100 行）─────────────────────
#   (a) round-trip:  parse(render(d)) == d，逐字段
#   (b) 坐标系断言:  放一个 y_left=+5 的合成目标，检查下游认为它在左边
#   (c) 契约校验器:  必填 / 范围 / 枚举 / 版本；**fail loud，绝不「尽力猜」**
#   (d) grounding:   VLA 输出引用的 track_id 必须存在于本帧输入，否则整条作废
#   把一份「金标准 prompt」纳入回归测试，任何渲染改动都要 diff 它。

# ── ⑥ 必须监控的指标 ───────────────────────────────────────────────
#   · ECE（总体 + 分场景：夜间/雨雾/距离分桶）
#   · **沉默错误率** = 错了、且输出未表达不确定 的比例   <- 最重要的单一指标
#   · 幻觉率 = 输出引用了输入里不存在的 track_id 的比例
#   · 下游动作错误率，按「超速 / 过度限速」**分方向**统计（代价不对称）
#   · 接口层：解析失败率、契约校验失败率、截断触发率、schema 版本分布

# ── ⑦ 红线 ─────────────────────────────────────────────────────────
#   · 训练数据必须包含**带噪感知输入 + 保守专家动作**的样本，
#     否则模型不知道该怎么用 conf 这个数字，前面所有门控都只是外挂规则
#   · 解释输出必须带上依赖的证据与置信度
#     （「依据 track#4127，置信 0.62，距离 82±7 m」）——
#     **流畅的解释会制造它并不配得的信任**
#   · 感知不要越界替下游做「该不该生效」的判断（涉及导航与法规优先级）
#     检验：如果这个判断错了，下游有没有信息把它纠正回来？没有就不该由感知定
'''
print(RECIPE)
for tok in ['schema_version', 'track_id', 'lane_assoc', 'sigma_dist_m',
            'p* = 1 - C_rej / C_wrong', '非对称门控', 'round-trip', 'grounding',
            '沉默错误率', 'ABI', 'null']:
    assert tok in RECIPE, tok
print('✅ 检查单覆盖：融合层次 / schema 逐字段 / 置信度与校准 / 模板铁律 / '
      '四个检查 / 监控指标 / 红线')"""),

    md("""### 小结

- **接口设计的第一个问题不是「传什么字段」，而是「在哪一层传」**。三个层次的判据是
  **「这个信息出错以后需不需要事后说清楚」**——需要就必须走符号级（可审计），
  不需要就走中间表示级（token 恒定、信息最全）。量产形态是混合的。
- **符号级的 bit/token 效率只有特征级的 1/1000**（2.0 vs 2048 bit/token）。
  付出这个代价换的不是信息量，是**可解释性与可归因性**。
- **每个字段都要能回答「拿掉它，下游哪条判断做不了」**。最易漏又最致命的是
  `track_id`（跨帧确认）、`lane_assoc`（管不管我）、`sigma_dist_m`（12 px → 83 m ± 6.9 m，
  且 $\\sigma_Z \\propto Z^2$）、`n_obs`/`state`（与置信度**正交**的时序一致性）。
- **不传置信度不是少传一个字段，是永久删除了下游做风险决策的能力。**
  本例中它的期望代价比最优高 **97%**。而阈值应当从代价推导：$p^\\star = 1 - C_{\\text{rej}}/C_{\\text{wrong}}$。
- **校准不是为了改善排序**（AUC 完全不变，重调阈值后可达代价也相同）——
  **是为了让「概率」这个数能被当作概率来算**。它在三种情况下不可替代：
  固定/共享阈值、用概率做算术、多源融合。温度缩放只有一个参数，性价比极高。
- **非对称门控**把代价不对称写进规则（提速要 $p\\ge0.90$、降速只要 $p\\ge0.30$），
  超速率 11.4% → 3.1%（**−72%**）；但**换成未校准的输入，这个收益直接打对折**。
- **VLA 会「合理化」错误输入**，输出流畅自洽且**不带任何不确定信号**——silent failure。
  输入幻觉靠置信度门控，输出幻觉靠 **grounding 校验**（引用不到的 `track_id` → 整条作废）。
  最该追踪的单一指标是**沉默错误率**。
- **prompt 模板是 ABI 不是 UI**：键值不要位置、顺序进版本、缺失用显式 `null` 而非哨兵。
  这三类故障的共同特征是**静默**，而排查静默故障的成本是排查崩溃的几十倍。

下一站：**模块 04 · 交通规则的指令跟随与约束化** ——
把本模块传下去的标志语义，翻译成有作用域、有生命周期、有优先级的可执行约束。"""),
]
