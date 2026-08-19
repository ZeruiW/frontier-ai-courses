# -*- coding: utf-8 -*-
"""C59 模块 01 · 从 VLM 到 VLA。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00；C00（VLM：视觉编码器 / 连接器 / LLM 的三段式结构）。不需要会训练大模型"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_from_vlm_to_vla.ipynb'),
    ("核心参考", "Brohan et al. RT-2；Kim et al. OpenVLA；Black et al. π0；Tian et al. DriveVLM；Hwang et al. EMMA；Lipman et al. Flow Matching"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("vlm_recap", "VLM 回顾：为什么这个结构「顺手」就能接上动作", "".join([
        P("<span class=\"term\">VLM</span>（Vision-Language Model）的三段式结构在 C00 讲透了，这里只回顾<strong>与「接动作」直接相关的那一点</strong>。"),
        ASCII("""图像 ──→ [ 视觉编码器 ] ──→ patch 特征 ──→ [ 连接器 ] ──→ 视觉 token
         SigLIP / DINOv2 / CLIP-ViT      linear / MLP / Q-Former      │
                                                                     ↓
指令文本 ──→ [ tokenizer + embedding ] ──→ 文本 token ──→ [ 拼 接 ] ──→ [ LLM decoder ]
                                                                              │
                                                                              ↓
                                                                        [ LM head ]
                                                                     softmax over V 个词
                                                                              │
                                                                              ↓
                                                                        下一个 token

★ 全部技术前提就一句话：**LLM 的输入是「一串向量」，不关心这些向量原本是什么。**
   只要一样东西能被投影成 d 维向量，它就能进这个序列 —— 图像可以，动作当然也可以。"""),
        TABLE(["部件", "职责", "典型选择", "为什么这样选"], [
            ["<strong>视觉编码器</strong>", "把像素变成有语义的 patch 特征", "SigLIP、CLIP ViT、DINOv2", "SigLIP/CLIP 提供<em>语言对齐</em>的语义；DINOv2 提供<em>空间与几何</em>结构"],
            ["<strong>连接器</strong>", "把视觉特征投到 LLM 的 embedding 空间", "linear / 2 层 MLP / Q-Former / Perceiver", "MLP 最简单且效果最好（LLaVA 之后的共识）；Q-Former 主要为了<em>压 token 数</em>"],
            ["<strong>LLM</strong>", "在拼好的 token 序列上做因果自回归", "Llama-2/3、Gemma、Qwen", "常识与推理能力全在这里，<strong>也是 VLA 唯一真正继承的东西</strong>"],
            ["<strong>LM head</strong>", "隐状态 → 词表上的分布", "一个 <code>d × V</code> 的线性层", "<strong>下一节的全部戏份都在这一层</strong>"],
        ]),
        DUAL(
            "为什么说这个结构「顺手」就能接动作？因为它已经干过一次同样的事了：<strong>视觉本来也不是语言，是连接器硬把它投成了「看起来像 token 的向量」塞进序列的</strong>。既然图像能这么进来，动作为什么不能这么出去？<em>RT-2 的全部创意就是把这个念头执行到底。</em>",
            "更精确地说，VLM 建立了一个<strong>模态无关的序列接口</strong>：输入侧任何模态只要经过一个投影器就能进入同一个 token 序列；输出侧任何东西只要能被编码成词表里的符号，就能被 LM head 生成。<em>这两件事合起来意味着「多模态」不是三个模型拼一起，而是<strong>一个序列模型加若干个适配器</strong></em>。VLA 因此不是新架构，是<strong>在这个既有接口上多插了一个模态</strong>——理解这点，后面所有设计选择都变得可推导。",
        ),
        CALLOUT("warn", "<p>一个必须现在就说清、且与 TSR 岗位直接相关的硬伤：<strong>VLM 的视觉塔分辨率太低，它自己看不见小交通标志。</strong></p><p>算一笔账：1920×1080、60° 水平 FOV 的前视相机，焦距约 <code>f = 960 / tan(30°) ≈ 1662 px</code>。60 m 外一块 0.6 m 的限速牌成像 <code>1662 × 0.6 / 60 ≈ 16.6 px</code>。而 VLM 的视觉塔通常吃 384×384（甚至 224×224）的整图——缩放比 0.2——这块牌子变成 <strong>3.3 px</strong>。ViT 的 patch 是 14 px，<em>它连一个 patch 的四分之一都占不满</em>。</p><p><strong>所以「让 VLA 自己去看标志」在物理上就不成立</strong>，必须有一个独立的、高分辨率的 TSR 模块把结果检出来再喂进去。<em>这不是工程妥协，这是这门课存在的物理理由——也是 JD 里那条职责的根。</em></p>", "VLA 看不见 3 像素的限速牌"),
    ])),
    ("action_token", "RT-2 的那一步：把控制问题变成语言问题", "".join([
        P("<span class=\"term\">RT-2</span>（Robotic Transformer 2, 2023）做的事情，用一句话说完：<strong>把连续动作离散化成整数，把整数映射到词表里已有的 token，于是动作就成了「话」，LM head 一个参数都不用改。</strong>"),
        H3("具体怎么做"),
        P("机器人动作是 7 个连续量 + 1 个终止位：末端位移 <code>(Δx, Δy, Δz)</code>、旋转 <code>(Δroll, Δpitch, Δyaw)</code>、夹爪开合、以及 terminate 标志。每一维<strong>各自</strong>均匀分成 256 个 bin："),
        MATH("b(a)=\\operatorname{clip}\\!\\left(\\left\\lfloor \\frac{a-a_{\\min}}{a_{\\max}-a_{\\min}}\\cdot B \\right\\rfloor,\\,0,\\,B-1\\right),\\qquad \\hat a(b)=a_{\\min}+\\frac{b+\\tfrac12}{B}\\,(a_{\\max}-a_{\\min})"),
        P("重建误差是有下界的，而且这个下界可以直接算出来——这是 notebook 第 2 节要验证的第一件事："),
        MATH("\\Delta=\\frac{a_{\\max}-a_{\\min}}{B},\\qquad |\\varepsilon|_{\\max}=\\frac{\\Delta}{2},\\qquad \\varepsilon_{\\mathrm{RMS}}=\\frac{\\Delta}{\\sqrt{12}}\\approx 0.289\\,\\Delta"),
        P("然后把 <code>b ∈ [0, 255]</code> 映射到词表里的 256 个 token id。于是一次动作输出就是一句 8 个 token 的「话」，训练目标与语言建模<strong>完全相同</strong>（对这 8 个位置算交叉熵）。"),
        ASCII("""一次 VLA 前向的 token 序列（RT-2 式）

 ┌──────── 前缀：双向可见 ────────┐┌──── 后缀：因果自回归 ────┐
 │ 视觉 token × N_v │ 文本 token × N_t ││ 动作 token × (D × K)    │
 └──────────────────┴──────────────────┘└──────────────────────────┘
   patch 特征投影      "把可乐罐拿起来"        b₁ b₂ … b₈
                       / TSR 序列化文本        ↑ 每个 = 某一维的 bin 编号

 注意力掩码：
   · 动作 token 能看到 全部视觉 + 全部文本 + 它**之前**的动作 token
   · 动作 token **看不到**它之后的动作 token（否则训练时会作弊）
   · 前缀内部通常双向（视觉/文本是"条件"，不需要因果性）

 这张图就是 notebook 第 5 节要用 numpy 实现的东西。"""),
        TABLE(["", "RT-1（2022）", "RT-2（2023）"], [
            ["主干", "从零训练的 EfficientNet + Transformer（35M）", "<strong>预训练 VLM</strong>（PaLI-X 55B / PaLM-E 12B）"],
            ["动作表示", "离散 bin（同样是 256）", "离散 bin，<strong>但复用词表 token</strong>"],
            ["输出头", "专用动作头", "<strong>原封不动的 LM head</strong>"],
            ["训练数据", "只有机器人数据", "<strong>机器人数据 + 原始 VLM 数据混训</strong>（co-fine-tuning）"],
            ["能力", "只会训练时见过的任务", "<strong>能利用互联网常识</strong>（「把草莓放进正确的碗」「拿起灭绝的动物」）"],
        ]),
        DUAL(
            "「把控制问题变成语言问题」的收益是<strong>继承</strong>：模型不必从零学「杯子是什么」「哪个是垃圾桶」，这些在预训练里已经有了；机器人数据只需要教它「怎么把已有的语义映射到动作」。<em>这就是为什么 RT-2 能对训练里没出现过的物体和指令做出合理反应，而 RT-1 不能。</em><strong>面试里这是 RT-2 唯一必须记住的点——它的贡献是这个转换本身，不是效果数字。</strong>",
            "代价有三条，且都不是实现问题而是范式自带的。<strong>① 分箱误差有硬下界</strong>：<code>ε_RMS = Δ/√12</code>，加 bin 只能线性改善而 token 预算是有限的。<strong>② token 之间没有序关系</strong>：bin 128 与 bin 129 对应的两个词表 token，在 embedding 空间里并不比 bin 128 与 bin 5 更近——<em>动作的连续性必须完全从数据里重新学出来</em>，这是把动作塞进离散词表最深的代价。<strong>③ 自回归解码是串行的</strong>：<code>D × K</code> 个 token 就是 <code>D × K</code> 次前向，动作维度或时间步一多，延迟直接线性爆炸。<em>后面 π0 换掉动作头，三条全是冲着这里来的。</em>",
        ),
        CALLOUT("intuition", "把这一节压成一句可迁移的心法：<strong>只要你能把一个问题的输出编码成词表里的符号，你就能白嫖整个语言模型预训练。</strong><em>这条心法在 RT-2 之外同样成立——Decision Transformer 把 RL 变成序列建模、EMMA 把 3D 检测框写成文本、Pix2Seq 把检测框写成 token，全是同一招。</em>反过来，<strong>这也划出了它的适用边界：当输出的连续性、精度或维度让「编码成符号」变得昂贵时，这招就该停了</strong>——这正是 §4 的内容。"),
    ])),
    ("openvla", "OpenVLA：唯一能看清全部实现细节的那一个", "".join([
        P("RT-2 是闭源的，论文里很多关键细节没写。<span class=\"term\">OpenVLA</span>（2024，7B）是目前<strong>唯一一个把训练配方、数据处理、tokenizer 处理全部公开的 VLA</strong>——所以它的工程细节比它的效果数字更值得读。"),
        TABLE(["设计决策", "怎么做的", "为什么（这才是要点）"], [
            ["<strong>双视觉塔</strong>", "SigLIP + DINOv2 的特征在通道维<strong>拼接</strong>后送连接器", "SigLIP 给语言对齐的语义，DINOv2 给空间/几何。<em>只用其一在需要精确定位的任务上明显更差</em>"],
            ["<strong>LLM 主干</strong>", "Llama-2 7B（Prismatic VLM 配方）", "7B 是「有常识」与「单卡能微调」的折中点"],
            ["<strong>动作 bin</strong>", "每维 256 个 bin，<strong>均匀分箱</strong>", "与 RT-2 保持一致，便于对照"],
            ["<strong>归一化范围</strong>", "<strong>用数据的 1% / 99% 分位数</strong>，不是 min/max", "<strong>关键工程点</strong>：min/max 会被离群动作撑爆，导致 99% 的正常动作挤在极少数 bin 里"],
            ["<strong>token 映射</strong>", "覆盖 Llama tokenizer 中<strong>最少使用的 256 个 token</strong>", "不新增 token 就不用改 embedding 与 LM head 的形状；被覆盖的 token 在机器人语境下几乎不出现"],
            ["<strong>训练数据</strong>", "Open X-Embodiment，约 97 万条轨迹、22 种机器人", "跨本体训练；<em>不同机器人的动作空间要先统一到同一套 7-DoF 表示</em>"],
            ["<strong>下游适配</strong>", "LoRA 微调 + 推理时量化（int4/int8）", "让「用得起」成为可能，这是开源生态最重要的一步"],
        ]),
        DUAL(
            "<strong>「用 1%/99% 分位数而不是 min/max」这一条，是整篇论文里最该记住的工程细节。</strong>动作数据里总有极少数异常大的位移（遥操作抖了一下、数据里有一条错误轨迹）。用 min/max 归一化，这几个离群点就把整个 <code>[a_min, a_max]</code> 撑得极宽；<em>结果是绝大多数正常动作被压进中间很少的几个 bin，等效分辨率暴跌</em>。<strong>这与 C52 讲的量化离群值问题是同一个现象</strong>——notebook 第 3 节会把这个损失量化出来。",
            "<strong>「覆盖最少使用的 token」这一条则暴露了「动作即语言」的一个隐性约束</strong>：你不能直接把动作写成数字字符串。因为 tokenizer 会把 <code>\"128\"</code> 切成不定数量的 token，而 <code>\"7\"</code> 只切成一个——<em>动作序列的长度会随数值变化</em>，固定长度解码和并行监督就都做不了了。<strong>所以必须建立「bin 编号 ↔ 单个 token id」的一一映射</strong>。<em>EMMA 走了相反的路（直接用文本数字），代价就是 token 数不可控——见 §5。</em>",
        ),
        CALLOUT("warn", "别把 OpenVLA 的设定直接搬到自动驾驶上。它的输入是<strong>单张 224×224 的第三人称图 + 一句短指令</strong>，输出是<strong>单步 7-DoF 动作</strong>。自驾要的是 <em>7–11 路相机、360°、200 m 距离、4–8 s 的轨迹</em>——<strong>输入侧和输出侧的规模都差一到两个数量级</strong>。<em>把 OpenVLA 当成「VLA 的参考实现」是对的，当成「自驾 VLA 的原型」就错了。</em>§6 的差异表就是为了防这个错。"),
    ])),
    ("flow_head", "π0 的流匹配动作头：什么时候该离开离散 token", "".join([
        P("<span class=\"term\">π0</span>（2024）是第一个在大规模上放弃离散 token 的 VLA。<strong>它的动机不是「离散不好」，而是「在高频、高维、多模态的动作上，离散 token 的三条代价同时爆掉」</strong>——这个判断标准比结论重要得多。"),
        H3("三条代价怎么爆的"),
        UL([
            "<strong>token 数</strong>：灵巧双臂 18 个自由度、50 Hz、一次输出 1 秒的动作块 → <code>18 × 50 = 900</code> 个动作 token。自回归解码 900 步，<em>在任何硬件上都不可能做到 50 Hz</em>。",
            "<strong>精度</strong>：灵巧操作的位置精度要求在毫米级，动作范围若是 ±10 cm，256 个 bin 给出 <code>Δ = 0.78 mm</code>，<code>ε_RMS ≈ 0.23 mm</code>——<em>刚好在「勉强够」的边缘，再苛刻一点就不够了</em>。",
            "<strong>多模态</strong>：抓杯子可以从左边也可以从右边。逐维独立 softmax 能表达每一维的多峰，<em>但表达不了「维度之间的联合多峰」</em>（左路径与右路径各自是一组协调的 7 维动作，逐维取 argmax 会拼出一个两边都不是的怪动作）。",
        ]),
        P("π0 的做法：VLM 主干（PaliGemma 3B）负责理解，另接一个 3 亿参数的 <strong>action expert</strong>，用 <span class=\"term\">flow matching</span>（流匹配）直接生成一整块连续动作（50 步 × D 维，一次出）。"),
        MATH("a^{\\tau}=\\tau\\,a+(1-\\tau)\\,\\epsilon,\\quad \\epsilon\\sim\\mathcal N(0,I);\\qquad \\mathcal L=\\mathbb E\\big\\|v_\\theta(a^{\\tau},\\tau\\mid o)-(a-\\epsilon)\\big\\|^2;\\qquad a^{\\tau+\\delta}=a^{\\tau}+\\delta\\,v_\\theta(a^{\\tau},\\tau\\mid o)"),
        TABLE(["动作头", "精度", "能表达多模态", "一次推理的前向次数", "实现/训练复杂度", "还能用语言解释自己吗"], [
            ["<strong>离散 token</strong>", "受 <code>Δ/√12</code> 限制", "逐维可以，<strong>联合不行</strong>", "<code>D × K</code>（串行）", "<strong>最低</strong>（复用 LM head）", "<strong>能</strong>"],
            ["<strong>连续回归</strong>", "高", "<strong>不行</strong>（会输出平均值）", "1", "低", "不能"],
            ["<strong>扩散（DDPM）</strong>", "高", "<strong>能</strong>", "50–100", "高（噪声调度、训练不稳）", "不能"],
            ["<strong>流匹配</strong>", "高", "<strong>能</strong>", "<strong>约 10</strong>（直线路径）", "中", "不能"],
        ]),
        DUAL(
            "流匹配可以这么理解：<strong>扩散是让模型学「怎么一点点去噪」，流匹配是让模型学「从噪声直着走向答案的那个速度」</strong>。因为训练时用的概率路径是<em>直线</em>（噪声与真值之间的线性插值），推理时的积分轨迹也接近直线，<strong>10 步欧拉积分就够，而扩散通常要 50–100 步</strong>。<em>这个 5–10 倍的步数差，正是它能上机器人而扩散策略吃力的原因。</em>",
            "严谨地说，流匹配学的是把先验 <code>p₀ = N(0,I)</code> 输运到数据分布 <code>p₁</code> 的<strong>条件速度场</strong>。取 optimal-transport 形式的条件路径 <code>a^τ = τa + (1-τ)ε</code>，其条件速度恒为 <code>a - ε</code>（与 <code>τ</code> 无关），于是回归目标极其简单且方差小——<em>这是它比扩散训练稳定的技术原因</em>。推理是对 ODE <code>da/dτ = v_θ</code> 做数值积分。<strong>代价是：动作不再是词表里的符号，「输出头就是 LM 头」这个便利被放弃了</strong>，模型也就不再能用同一条通路输出「我为什么这么动」的语言解释。<em>这是一个真实的取舍，不是纯升级。</em>",
        ),
        CALLOUT("intuition", "给一条可以直接用在面试里的判据：<strong>「频率越高、动作维度越高、越需要表达联合多模态，就越该离开离散 token；反之，越需要可解释、越需要与语言共用一条通路，就越该留在离散 token。」</strong><em>自动驾驶恰好落在中间——维度低（2–3 维）、频率不高（VLA 只出 2–10 Hz 的粗轨迹）、但极需要多模态（路口该左该右）与可解释性。</em><strong>所以自驾 VLA 的动作头选型至今没有定论，这是 m02 整节的内容。</strong>"),
    ])),
    ("drive_vla", "自动驾驶 VLA：DriveVLM、EMMA 与量产的那条路", "".join([
        P("机器人 VLA 的路子搬到车上，第一件事就撞墙：<strong>延迟</strong>。一个 3B–10B 的模型在车端跑一次要几百毫秒，而车辆每 20 ms 就要一个控制指令。<em>这个矛盾催生了自驾 VLA 的两个标志性设计：慢-快双系统，与云-端蒸馏。</em>"),
        TABLE(["方案", "主干与结构", "输出形式", "关键设计", "主要局限"], [
            ["<strong>DriveVLM</strong>（清华 + 理想, 2024）", "VLM 做<em>场景描述 → 关键物体分析 → 分层规划</em>", "语言化的规划推理 + 稀疏路点", "<strong>思维链式的分层规划</strong>：先描述场景、再挑关键物体、再出决策", "慢（秒级），单靠它无法控车"],
            ["<strong>DriveVLM-Dual</strong>", "DriveVLM（慢）+ 传统端到端模块（快）", "快系统高频细化慢系统的粗轨迹", "<strong>慢-快双系统的代表作</strong>：慢系统负责语义与长时决策，快系统负责高频与精度", "两系统结论不一致时怎么办，没有干净的答案"],
            ["<strong>EMMA</strong>（Waymo, 2024）", "Gemini 为主干，<strong>所有输入输出都是文本</strong>", "轨迹 = 文本化的路点数字；3D 框、道路要素也是文本", "<strong>统一文本接口</strong>：多任务共训一个模型，任务间互相增益", "token 成本高、数值精度受文本表示限制；<strong>无激光雷达</strong>"],
            ["<strong>量产蒸馏路线</strong>（小鹏等）", "云端几十 B 大模型 → 蒸馏 → 车端几 B 小模型", "车端出意图 + 粗轨迹，下游控制器跟踪", "<strong>把「大模型的能力」与「车端的算力」解耦</strong>", "蒸馏一致性难保证；教师错了学生跟着错"],
        ]),
        ASCII("""量产 VLA 的云-端分工（这是「几百 ms 延迟怎么上车」的真正答案）

  ┌───────────────── 云端 ─────────────────┐
  │  几十 B 参数的 VLA「世界模型 / 教师」    │
  │   · 吃车队回传的长尾片段                 │
  │   · 产出：轨迹标签、场景描述、决策理由    │   离线，延迟无所谓
  │   · 也用来给数据自动打标（见 C58 m04）   │
  └───────────────┬────────────────────────┘
                  │  蒸馏 / 数据引擎（周级迭代）
                  ↓
  ┌───────────────── 车端 ─────────────────┐
  │  几 B 参数的学生模型 + int8/int4 量化    │   2–10 Hz
  │   · 输入：多路相机 + **TSR 序列化文本**  │   ↓ 输出动作块（3–8 s）
  ├────────────────────────────────────────┤
  │  下游控制器（传统 MPC / 轨迹跟踪）       │   10–100 Hz
  ├────────────────────────────────────────┤
  │  ★ 规则层 + 安全层（VLA 之外，不可省）★  │   硬实时
  └────────────────────────────────────────┘

★ 记住这张图的形状：VLA **不直接控车**，它只是往下游送「意图 + 粗轨迹」，
  而且它的输出必须过一遍可行性与安全校验。这是量产红线（m04 详述）。"""),
        DUAL(
            "<strong>EMMA 的「一切皆文本」值得单独说一句，因为它与本课的接口主题直接相关。</strong>Waymo 把 3D 检测框、道路要素、未来轨迹全部写成文本数字，让一个模型用同一套接口做全部任务。<em>好处是任务间正迁移明显、加新任务只要加一种文本格式</em>；<strong>坏处是 token 成本与数值精度</strong>——一个三位小数的坐标要好几个 token，一条 8 秒轨迹的路点就能吃掉几百个 token。<em>这正好是 §3 里 OpenVLA 用「bin ↔ 单 token」映射要避开的问题，两者做了相反的选择。</em>",
            "<strong>而量产路线的核心不是模型，是「数据引擎 + 蒸馏」的闭环。</strong>云端大模型的真正角色有两个：<em>① 直接做教师，蒸馏出车端小模型；② 做自动标注器，把车队回传的长尾片段变成训练数据</em>（这就是 C58 m04 里「用 VLM 打标」那条线，也是 JD 里 <em>automated data mining workflows</em> 的指向）。<strong>所以「VLA 上车」不是一次模型部署，而是一条持续运转的流水线</strong>——理解这点，才能回答「这东西怎么迭代」这类系统设计题。<em>而蒸馏一致性怎么度量、教师的错误怎么不被继承，目前没有标准答案（m05）。</em>",
        ),
        CALLOUT("danger", "一个会当场翻车的说法：「小鹏/特斯拉已经把大模型放到车上了」。<strong>准确的说法是：车端跑的是蒸馏后的小模型，云端才是大模型；而且 VLA 的输出仍要过规则层与安全层。</strong><em>把「云端大模型」和「车端模型」混为一谈，是这个话题上最常见的外行破绽</em>——因为它直接暴露你没算过延迟与算力的账。<strong>随口能说出「车端几 B、int8 量化、2–10 Hz、下游控制器 10–100 Hz 跟踪」这几个数，可信度立刻不一样。</strong>"),
    ])),
    ("robot_vs_drive", "机器人 VLA 与自驾 VLA：五个维度的关键差异", "".join([
        P("这是本模块<strong>最该背下来的一张表</strong>。大部分候选人读的是机器人 VLA 的论文（因为那边论文多），然后把结论直接套到自驾上——<em>而这两者在几乎每个设计维度上都不同</em>。能把差异说清楚，是「读过论文」与「想过问题」的分水岭。"),
        TABLE(["维度", "机器人 VLA（RT-2 / OpenVLA / π0）", "自驾 VLA（DriveVLM / EMMA / 量产）", "这个差异导致什么"], [
            ["<strong>动作空间维度</strong>", "7 DoF（单臂）～ 14–18（双臂灵巧）", "<strong>2–3 维</strong>（纵向加速度 + 曲率）或路点序列", "自驾维度低 → <em>离散 token 的 token 预算压力小得多</em>，离散化仍然可行"],
            ["<strong>频率要求</strong>", "10–50 Hz（灵巧操作要 50 Hz）", "VLA 出轨迹 <strong>2–10 Hz</strong>，下游控制器 10–100 Hz", "<strong>自驾天然分层</strong> → VLA 只出意图，不直接控车"],
            ["<strong>时间视界</strong>", "1–2 s（一次抓取）", "<strong>3–8 s</strong>（一次变道/路口通行）", "自驾必须输出<em>轨迹</em>而非单步动作 → 动作分块是刚需"],
            ["<strong>安全约束强度</strong>", "力矩限制 + 工作空间限制；<em>软约束</em>", "<strong>ISO 26262 / SOTIF；硬约束，需可论证</strong>", "自驾<strong>必须</strong>有 VLA 之外的规则层与安全层，机器人可以没有"],
            ["<strong>可用传感器</strong>", "1–3 路近距 RGB(-D)，视野窄、距离 &lt; 2 m", "<strong>7–11 路相机 360°、毫米波雷达、（可选）激光，距离 200 m</strong>", "自驾输入 token 数大得多 → <em>不可能把所有原始像素都喂进 LLM</em>，必须先压缩/抽象"],
            ["<strong>失败代价</strong>", "打翻杯子；<strong>可以重置重来</strong>", "<strong>碰撞、人身伤害；不可重置</strong>", "自驾不能靠「多试几次」，<em>开环评测严重高估、必须闭环</em>（m05）"],
            ["<strong>数据获取</strong>", "遥操作主动采集，可定向补数据", "车队被动采集，<strong>长尾靠触发回传挖掘</strong>", "自驾的数据闭环是核心竞争力（C58 整门课）"],
            ["<strong>长尾的类型</strong>", "没见过的<em>物体与抓法</em>", "<strong>没见过的<em>语义规则场景</em></strong>（施工改道、临时管制、区域性标志）", "<strong>自驾长尾正是 TSR 的战场</strong> —— 这就是本课的落点"],
        ]),
        P("表里有两行值得展开，因为它们最容易被想反："),
        DUAL(
            "<strong>「自驾动作维度低」经常被误读成「自驾更简单」。</strong>恰恰相反：<em>维度低意味着离散 token 这条便宜路线在自驾上仍然可用</em>（2 维 × 40 步 = 80 个 token，完全可接受，而 π0 是 900 个），<strong>所以自驾 VLA 反而更有理由保留「动作即语言」的可解释性</strong>。真正难的不是动作维度，是<em>输入侧</em>——7–11 路相机的信息量远超单臂机器人的一张图。<strong>难点从「怎么输出」搬到了「怎么输入」，而这正是本课讲接口的原因。</strong>",
            "<strong>「失败代价」这一行决定了整个评测方法论。</strong>机器人可以把成功率当主指标，因为失败了重置就行、可以统计几百次；自驾不能——<em>一次严重失败的代价无法用几百次成功摊平</em>。更麻烦的是：<strong>机器人可以真机跑闭环，自驾的闭环要么靠仿真（有域差）要么靠实车（贵且危险）</strong>，于是大量工作退化成开环比对专家轨迹，<em>而开环评测不暴露误差累积，会系统性高估</em>。<strong>这个高估有多大、怎么修正，是 m05 的核心内容。</strong>",
        ),
        CALLOUT("intuition", "把这张表压成一句话交给面试官：<strong>「机器人 VLA 的难点在动作端——高维、高频、多模态；自驾 VLA 的难点在感知端与安全端——输入信息量巨大、失败不可逆、必须可论证。所以两边的技术选择往相反方向走：机器人在换动作头，自驾在做接口与兜底。」</strong><em>说得出这句，基本就说明你不是只看了 demo 视频。</em>"),
    ])),
    ("limits", "能力边界：VLA 被高估的三件事", "".join([
        P("模块 00 已经划过一次边界，这里补三条<strong>只有读过论文细节才知道</strong>的。它们都可以量化，所以可以在面试里作为「我读过而且算过」的证据。"),
        H3("① demo 视频的成功率与它的复合效应"),
        P("机器人 VLA 论文里的成功率通常在 50%–85%（RT-2 在未见任务上约 60%，OpenVLA 在标准套件上 70% 左右）。<strong>这些数字在机器人语境下很好，在自驾语境下是灾难。</strong>而且成功率在多步任务上是<em>相乘</em>的："),
        MATH("P_{\\text{整段成功}}=\\prod_{i=1}^{n} p_i \\;\\approx\\; p^{\\,n};\\qquad p=0.9,\\ n=10 \\;\\Rightarrow\\; 0.35;\\qquad p=0.99,\\ n=200 \\;\\Rightarrow\\; 0.13"),
        P("一次城市通勤有几百个需要语义判断的决策点。<strong>就算每个点 99% 正确，整段通勤不出错的概率也只有 13%</strong>。<em>这不是说 VLA 没用，而是说「必须有下游兜底」不是保守，是算出来的结论。</em>"),
        H3("② 「泛化」这个词被用得太宽"),
        P("论文里的泛化通常是：换个桌布、换个没见过的物体、换个措辞的指令。<strong>这些都是「同分布内的组合泛化」</strong>。而自驾需要的泛化是：<em>换一个国家的标志体系、换一种从未在互联网图片里出现过的临时施工牌、换一套区域性的道路规则</em>。<strong>预训练常识覆盖的是互联网上常见的长尾，不是你这条路上的长尾</strong>——这两者的差距，正是量产仍然需要针对性数据与蒸馏的原因。"),
        H3("③ 思维链说的理由，不一定是它实际用的依据"),
        P("VLA 能输出「我因为看到施工牌所以减速」这样的解释，这对调试和用户信任都很有价值。<strong>但语言模型的思维链是<em>可能不忠实的</em>（unfaithful）</strong>：模型可能因为图像里的某个无关线索做出决定，然后生成一段听起来合理但与实际计算无关的理由。<em>把 CoT 当成因果解释来做故障归因，会把排查引向完全错误的方向。</em>"),
        DUAL(
            "这三条合起来给出一个务实的态度：<strong>把 VLA 当成「一个在长尾语义上比规则强、但输出必须被检查的建议器」，而不是「一个能开车的司机」</strong>。<em>它的价值在于把「完全不会处理」变成「大概率处理得不错」，而把「大概率」变成「可以上路」是下游那几层的工作。</em>",
            "更技术地说，VLA 的输出应当被视为一个<strong>带不确定性的高层意图</strong>，而非一个可执行指令。这意味着接口设计上要求三件事：<em>① 它要能表达「我不确定」（而不是永远给出自信答案）；② 它的输出要能被下游做可行性检查（所以必须是结构化的轨迹/约束，而不是自由文本）；③ 它的失败模式要能被日志捕获</em>。<strong>这三件事都不是模型能力问题，是接口与系统设计问题</strong>——也就是 m03、m04、m05 的全部内容。",
        ),
        CALLOUT("danger", "面试里最危险的一句话是「VLA 能理解场景」。<strong>「理解」是一个无法证伪的词，说出来只会招来「怎么证明它理解了？」这个你答不上的追问。</strong><em>把它换成可验证的表述</em>：「VLA 在<strong>需要组合语义先验</strong>的长尾场景上，比穷举规则的方案有更高的正确率；代价是延迟、幻觉与不可验证性；所以它的输出必须过安全层。」<strong>同样的意思，但每一句都能被追问且你都答得上。</strong>"),
    ])),
    ("tsr_hook", "回到 TSR：那条 JD 职责在这条链路的哪个位置", "".join([
        P("把 JD 那句话拆开：<em>「Improve VLA models to <strong>effectively consume TSR outputs</strong> and support <strong>traffic-sign-aware instruction following</strong> through <strong>VLA prompts</strong>」</em>——三个动词短语，对应三件不同的工作。"),
        TABLE(["JD 短语", "实际要做的事", "本课对应模块", "衡量它做得好不好的指标"], [
            ["<strong>consume TSR outputs</strong>", "设计 TSR → VLA 的序列化 schema：传哪些字段、什么形式、置信度怎么传", "<strong>m03</strong>", "同样的感知输入下，下游决策正确率；token 成本"],
            ["<strong>traffic-sign-aware</strong>", "把标志语义翻译成可执行约束：作用域、生命周期、冲突优先级", "<strong>m04</strong>", "<strong>交通标志相关的规则违反率</strong>；约束撤销的正确率"],
            ["<strong>through VLA prompts</strong>", "prompt 模板设计与稳定性：字段顺序、数值格式、缺失值、先验注入", "<strong>m03 / m04</strong>", "prompt 扰动下输出的稳定性；字段消融的敏感度"],
        ]),
        P("注意这三件事<strong>没有一件是「训 VLA」</strong>。这个岗位在 VLA 这条链路上的位置是<em>上游 + 接口</em>，不是模型本身。这与 JD 的主体（TSR 2D Detection）完全自洽——<strong>公司要的是一个既懂检测、又知道自己的输出会被怎么消费的人</strong>。"),
        H3("面试标准答案骨架"),
        OL([
            "<strong>先定位</strong>：「VLA 在自动驾驶栈里是接在感知之后、规划之上的语义决策层，它不直接控车，输出要过安全层。」<em>（先给架构位置，避免被当成只会背名词）</em>",
            "<strong>再讲转换</strong>：「VLA 的起点是 RT-2 把动作离散化成 token、复用 VLM 的输出头，把控制问题变成语言问题——这样才能继承预训练的常识。代价是分箱误差、token 无序关系、自回归延迟。」",
            "<strong>然后讲分化</strong>：「机器人那边因为高频高维走向了流匹配动作头（π0）；自驾这边动作维度低、更需要可解释，所以离散 token 仍然可用，真正的难点搬到了输入侧。」",
            "<strong>落到自己的位置</strong>：「所以我的工作是让 TSR 的输出能被 VLA 正确消费——至少要传<strong>类别、数值、置信度（且经过校准）、距离、车道关联、track_id、临时/固定</strong>这七项，因为下游需要区分『看到了』与『确认了』、『我车道』与『对向』、『临时』与『固定』。」",
            "<strong>最后主动划边界</strong>：「VLA 会把错误的感知输入合理化成一段像样的推理，所以低置信输入必须触发保守行为，而不是交给模型自己判断。这是接口设计的第一性要求。」",
        ]),
        CALLOUT("intuition", "这个骨架的设计逻辑：<strong>架构定位 → 关键技术转换 → 领域分化 → 自己的位置 → 主动划边界</strong>。<em>前三步证明你读过东西，第四步证明你想过自己的工作，第五步证明你不吹。</em>五步里最容易被跳过、也最能拉开差距的是第五步——<strong>大多数候选人讲完技术就停了，而面试官最想知道的恰恰是「你知不知道它什么时候不行」。</strong>"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        P("这一节列的是<strong>写这门课时仍无共识的问题</strong>。它们全部与本模块的内容直接相关，可以作为面试中「你觉得这个方向的难点是什么」的现成答案。"),
        UL([
            "<strong>离散 token 的「无序关系」能否被修好</strong>：bin 128 与 bin 129 在 embedding 空间里毫无关联，模型必须从数据里重学动作的连续性。<em>有工作尝试给动作 token 加上有序的位置编码、或用残差量化（RVQ）建立粗-细层次</em>，但都还没成为共识做法。这是「动作即语言」最深的技术债。",
            "<strong>自驾动作头的选型没有定论</strong>：维度低（离散可行）+ 强多模态需求（离散不够）+ 需要可解释（扩散做不到）三个约束互相冲突。<em>目前看到的方案从「离散 token + 多候选轨迹」到「轨迹词表（trajectory vocabulary）」到「小步数流匹配」都有</em>，还没有胜出者（m02 详述）。",
            "<strong>视觉 token 的预算分配</strong>：7–11 路相机的原始像素不可能全进 LLM。<em>该给远处的小目标区域多分 token 还是均匀分？该在 BEV 空间抽 token 还是在图像空间抽？</em>——这与 TSR 的小目标问题（C57）直接耦合，是当前最工程化也最缺公开结论的一块。",
            "<strong>思维链的忠实性</strong>：VLA 输出的推理链与它实际使用的依据是否一致，目前既缺度量也缺保证。<em>如果不忠实，把 CoT 用于故障归因就是有害的</em>；而 CoT 恰恰是 VLA 相对端到端最被看重的卖点。",
            "<strong>蒸馏的长尾保真</strong>：云端大模型 → 车端小模型的蒸馏，在头部场景上很容易对齐，<strong>但长尾恰恰是样本最少、蒸馏信号最弱的地方</strong>——而长尾又是用 VLA 的全部理由。<em>怎么度量「蒸馏后长尾能力有没有掉」，缺乏标准方法（m05）。</em>",
            "<strong>跨本体 / 跨车型迁移</strong>：Open X-Embodiment 证明了跨机器人本体训练有正迁移。自驾这边，<em>不同车型的传感器布置、标定、动力学都不同</em>，「一个 VLA 服务多种车型」的迁移问题几乎没有公开研究。",
            "<strong>评测的开环-闭环鸿沟</strong>：开环比对专家轨迹会严重高估（不暴露误差累积），而闭环需要高保真仿真或实车。<em>「开环指标提升多少才对应闭环真实提升」这个换算关系，目前每家自己拍脑袋</em>。",
        ]),
        CALLOUT("paper", "必读（按建议顺序，每篇只需读指定部分）：<em>RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control</em>（Brohan et al., 2023 —— <strong>只读动作离散化与 co-fine-tuning 两小节</strong>，这是「动作即 token」的原点）；<em>OpenVLA: An Open-Source Vision-Language-Action Model</em>（Kim et al., 2024 —— 读动作归一化的<strong>分位数选择</strong>与 tokenizer 覆盖策略，是全篇最有工程价值的两处）；<em>π0: A Vision-Language-Action Flow Model for General Robot Control</em>（Black et al., 2024 —— 读 action expert 与流匹配动作头，理解<strong>什么时候该离开离散 token</strong>）；<em>Flow Matching for Generative Modeling</em>（Lipman et al., 2023 —— 只需读 OT 条件路径那一节，理解为什么 10 步就够）；<em>DriveVLM / DriveVLM-Dual</em>（Tian et al., 2024 —— <strong>慢-快双系统</strong>的代表）；<em>EMMA: End-to-End Multimodal Model for Autonomous Driving</em>（Hwang et al., 2024 —— 重点看它怎么把感知结果与轨迹<strong>写成文本</strong>，与本课 m03 的接口设计正好互为对照）；<em>Open X-Embodiment</em>（2023 —— 跨本体数据集，理解动作空间统一的工程难度）。相邻课程：C00（VLM 结构）、C55（TSR 上游）、C57（小目标与视觉 token 预算）、C60（车端量化与部署）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 从 VLM 到 VLA（动作离散化 / token 预算 / 因果注意力 / 玩具 VLA 前向）

目标：把「动作变成 token」这件事**从公式一路做到能跑的前向**，并把每一步的代价算成数字。

本 notebook 你会亲手实现：
1. **动作归一化**：复现 OpenVLA 的「1%/99% 分位数 vs min/max」，量化离群值造成的分辨率损失
2. **均匀分箱的离散化 / 反离散化**，并验证误差的理论值 $|\\varepsilon|_{max}=\\Delta/2$、$\\varepsilon_{RMS}=\\Delta/\\sqrt{12}$
3. 把量化误差换算成 **「车道里的米」**——256 个 bin 在 50 m 前视距离上到底差多少
4. **精度-token 数权衡计算器**：RT-2 / π0 / 自驾 VLA 三种配置的 token 预算与延迟
5. **玩具 VLA 前向**（纯 numpy）：视觉 token + 文本 token + 动作 token 拼接 + **因果注意力掩码**，
   并用数值实验证明掩码真的挡住了未来
6. **自回归解码动作块**并还原成轨迹
7. ✏️ 四道练习 + 📖 参考答案 + 🧪 动作表示选型清单

> 心智模型：**只要能把输出编码成词表里的符号，就能白嫖整个语言模型预训练；
> 而当连续性、精度或维度让这个编码变贵时，这一招就该停了。**"""),
    md("""## 1 · 动作归一化：为什么 OpenVLA 用 1%/99% 分位数而不是 min/max

动作数据里总有极少数离群值（遥操作抖了一下、一条错误轨迹、标注 bug）。
用 min/max 归一化，这几个点就把整个 `[a_min, a_max]` 撑得极宽，
**绝大多数正常动作被挤进中间很少的几个 bin**——等效分辨率暴跌。

这与 C52 讲的「一个离群值撑爆整层量化 scale」是同一个现象。"""),
    code("""import numpy as np, math, json
rng = np.random.default_rng(59)

# ── 合成一段驾驶动作数据（物理合理）────────────────────────────
# a_lon: 纵向加速度 m/s^2，正常驾驶集中在 0 附近
# kappa: 路径曲率 1/m，直行≈0，变道≈±0.02，路口转弯≈±0.08
N = 20000
a_lon = np.clip(rng.normal(0.0, 0.8, N), -5.0, 3.0)

mode = rng.choice([0, 1, 2], size=N, p=[0.80, 0.15, 0.05])   # 直行 / 变道 / 转弯
kappa = np.where(mode == 0, rng.normal(0.0, 0.004, N),
         np.where(mode == 1, rng.normal(0.0, 0.020, N),
                             rng.choice([-1.0, 1.0], N) * rng.normal(0.080, 0.010, N)))
kappa = np.clip(kappa, -0.10, 0.10)

# 注入 0.1% 的离群值：数据 bug / 急打方向的记录错误
n_out = max(1, N // 1000)
out_idx = rng.choice(N, n_out, replace=False)
kappa[out_idx] = rng.choice([-1.0, 1.0], n_out) * rng.uniform(0.40, 0.55, n_out)

print(f'样本数 {N}, 注入离群值 {n_out} 个 ({n_out / N:.2%})')
print(f'kappa  min/max      : [{kappa.min():+.4f}, {kappa.max():+.4f}]')
print(f'kappa  1%/99% 分位数 : [{np.percentile(kappa, 1):+.4f}, {np.percentile(kappa, 99):+.4f}]')
print(f'kappa  正常范围      : 约 [-0.10, +0.10]')
print()
print('⚠️  min/max 的范围被 0.1% 的离群值撑大了约 '
      f'{(kappa.max() - kappa.min()) / (np.percentile(kappa, 99) - np.percentile(kappa, 1)):.1f} 倍')
assert kappa.max() > 0.35, '离群值应显著超出正常范围'"""),
    code("""B = 256   # RT-2 / OpenVLA 的标准 bin 数

def norm_range(x, mode):
    '''返回归一化用的 (lo, hi)。'''
    if mode == 'minmax':
        return float(x.min()), float(x.max())
    if mode == 'quantile':
        return float(np.percentile(x, 1)), float(np.percentile(x, 99))
    raise ValueError(mode)

def bin_index(a, lo, hi, B):
    idx = np.floor((np.asarray(a, dtype=float) - lo) / (hi - lo) * B).astype(int)
    return np.clip(idx, 0, B - 1)

inlier = np.abs(kappa) <= 0.10          # 只看正常动作（离群值本来就该被裁掉）
print(f"{'归一化方式':<12s}{'lo':>9s}{'hi':>9s}{'Δ (1/m)':>12s}"
      f"{'正常动作占用bin数':>18s}{'有效分辨率损失':>16s}")
stats = {}
for mode in ['minmax', 'quantile']:
    lo, hi = norm_range(kappa, mode)
    idx = bin_index(kappa[inlier], lo, hi, B)
    n_used = len(np.unique(idx))
    stats[mode] = {'lo': lo, 'hi': hi, 'delta': (hi - lo) / B, 'n_used': n_used}
    print(f'{mode:<12s}{lo:>9.4f}{hi:>9.4f}{(hi - lo) / B:>12.2e}'
          f'{n_used:>18d}{B / n_used:>15.1f}x')

r = stats['quantile']['n_used'] / stats['minmax']['n_used']
assert stats['minmax']['n_used'] < 120, 'min/max 下正常动作只占用少数 bin'
assert r > 2.0, f'分位数归一化应让有效 bin 数至少翻倍，实际 {r:.2f}x'
print()
print(f'✅ **分位数归一化把有效 bin 数提升了 {r:.1f} 倍** —— 0.1% 的离群值，'
      f'代价是 {B / stats["minmax"]["n_used"]:.0f} 倍的分辨率损失。')
print('   这就是 OpenVLA 用 1%/99% 分位数而不是 min/max 的全部理由。')
print('⚠️  代价：超出 [lo, hi] 的动作会被裁剪。所以分位数要选得够宽（1%/99% 而不是 5%/95%），')
print('    且**必须记录裁剪率**并监控它 —— 裁剪率突然上升 = 动作分布漂移了。')"""),
    md("""## 2 · 均匀分箱：离散化 / 反离散化与误差的理论值

$$b(a)=\\mathrm{clip}\\Big(\\Big\\lfloor \\frac{a-a_{min}}{a_{max}-a_{min}}B \\Big\\rfloor, 0, B-1\\Big),
\\qquad \\hat a(b)=a_{min}+\\frac{b+0.5}{B}(a_{max}-a_{min})$$

理论误差（bin 中心重建、输入在区间内均匀分布）：
$$\\Delta=\\frac{a_{max}-a_{min}}{B},\\qquad |\\varepsilon|_{max}=\\frac{\\Delta}{2},
\\qquad \\varepsilon_{RMS}=\\frac{\\Delta}{\\sqrt{12}}\\approx 0.2887\\,\\Delta$$

**这两个数是硬下界**：不管模型多强、数据多好，只要用 B 个 bin，误差就不可能低于它。"""),
    code("""def discretize(a, lo, hi, B):
    '''连续动作 -> bin 编号（整数）。超出范围的会被裁剪。'''
    idx = np.floor((np.asarray(a, dtype=float) - lo) / (hi - lo) * B).astype(int)
    return np.clip(idx, 0, B - 1)

def undiscretize(b, lo, hi, B):
    '''bin 编号 -> 连续动作（取 bin 中心，这是最小化最大误差的选择）。'''
    return lo + (np.asarray(b, dtype=float) + 0.5) / B * (hi - lo)

# 在区间内均匀采样，验证理论值
lo, hi = -0.10, 0.10
x = rng.uniform(lo, hi, 400000)
print(f"{'B':>6s}{'Δ':>12s}{'|ε|max 实测':>14s}{'Δ/2 理论':>12s}"
      f"{'ε_RMS 实测':>13s}{'Δ/√12 理论':>13s}{'比值':>8s}")
for Bt in [16, 64, 256, 1024, 4096]:
    delta = (hi - lo) / Bt
    xh = undiscretize(discretize(x, lo, hi, Bt), lo, hi, Bt)
    e = xh - x
    emax, erms = float(np.abs(e).max()), float(np.sqrt((e ** 2).mean()))
    assert emax <= delta / 2 + 1e-12, f'B={Bt} 最大误差超过 Δ/2'
    ratio = erms / (delta / math.sqrt(12))
    assert 0.97 < ratio < 1.03, f'B={Bt} RMS 与理论值偏差过大: {ratio:.4f}'
    print(f'{Bt:>6d}{delta:>12.3e}{emax:>14.3e}{delta / 2:>12.3e}'
          f'{erms:>13.3e}{delta / math.sqrt(12):>13.3e}{ratio:>8.4f}')

print()
print('✅ 实测与理论完全吻合：**误差随 B 只是线性下降**（B 翻倍，误差减半）。')
print('   而 token 预算是线性增长的 —— 所以「加 bin」这条路的收益是 1:1 的，')
print('   没有任何免费午餐。想要 10 倍精度就得付 10 倍范围代价或换表示。')

# 往返一致性：bin 编号本身必须能无损往返
b_all = np.arange(B)
assert np.array_equal(discretize(undiscretize(b_all, lo, hi, B), lo, hi, B), b_all), \\
    'bin -> 动作 -> bin 必须无损往返'
print('✅ bin -> 动作 -> bin 往返无损（这是解码正确性的最低要求）')"""),
    md("""## 3 · 把量化误差换算成「车道里的米」

「误差 7.8e-4 /m」没人有感觉。换成横向偏差就有了。

小曲率下车辆在前视距离 $L$ 处的横向偏移近似为 $y \\approx \\tfrac12 \\kappa L^2$，
所以曲率的量化误差 $\\varepsilon_\\kappa$ 对应的横向误差是 $\\Delta y = \\tfrac12 \\varepsilon_\\kappa L^2$。

**这是把「表示精度」翻译成「工程指标」的标准做法**——面试里能做这个换算，
说明你不是在背论文。"""),
    code("""KAPPA_RANGE = 0.20          # 曲率范围 [-0.1, +0.1] 1/m
LANE_WIDTH = 3.5            # 标准车道宽 m

def lateral_error(B, L, kappa_range=KAPPA_RANGE):
    '''返回 (最大横向误差, RMS 横向误差) 单位 m。'''
    delta = kappa_range / B
    return 0.5 * (delta / 2) * L ** 2, 0.5 * (delta / math.sqrt(12)) * L ** 2

print(f"{'B':>6s}{'Δκ (1/m)':>12s}" + ''.join(f'{f"L={L}m max/RMS (m)":>24s}' for L in [30, 50]))
for Bt in [64, 128, 256, 512, 1024, 4096]:
    row = f'{Bt:>6d}{KAPPA_RANGE / Bt:>12.3e}'
    for L in [30, 50]:
        mx, rm = lateral_error(Bt, L)
        row += f'{mx:>13.3f} /{rm:>9.3f}'
    print(row)

mx30, rm30 = lateral_error(256, 30)
mx50, _ = lateral_error(256, 50)
assert abs(mx30 - 0.176) < 0.005, f'256 bin @30m 最大横向误差应约 0.176 m，得到 {mx30:.4f}'
assert abs(rm30 - 0.102) < 0.005, f'256 bin @30m RMS 应约 0.102 m，得到 {rm30:.4f}'
assert mx50 > 0.45, '50 m 处误差应显著更大（与 L^2 成正比）'
print()
print(f'✅ **RT-2/OpenVLA 的 256 个 bin，在 30 m 处最大横向误差 {mx30:.2f} m，'
      f'50 m 处 {mx50:.2f} m。**')
print(f'   50 m 处的 {mx50:.2f} m 已经是车道宽 {LANE_WIDTH} m 的 {mx50 / LANE_WIDTH:.0%} —— 不可忽略。')

# 反过来问：要把 50 m 处的最大横向误差压到 10 cm 以内，需要多少 bin？
target, L = 0.10, 50
B_need = KAPPA_RANGE * L ** 2 / (4 * target)          # 由 0.5*(Δ/2)*L^2 <= target 解出
B_pow2 = 1 << int(math.ceil(math.log2(B_need)))
assert abs(B_need - 1250.0) < 1.0, f'解析解应为 1250，得到 {B_need}'
assert lateral_error(B_pow2, L)[0] <= target
print()
print(f'⚠️  要把 50 m 处的最大横向误差压到 {target * 100:.0f} cm 以内，'
      f'需要 B >= {B_need:.0f}（取 2 的幂 = {B_pow2}）。')
print(f'   **远超 RT-2 / OpenVLA 的 256** —— 这就是「机器人的动作表示不能直接搬到车上」')
print('   的一个可以算出来的理由。解法有三条：缩小曲率范围（分段表示）、')
print('   多 token 表示（下一节）、或换连续动作头（见 m02）。')"""),
    md("""## 4 · 精度-token 数权衡计算器

三个量互相牵制：**bin 数 B（精度）× 动作维度 D × 时间步 K（token 数）× 推理频率**。

关键洞察：离散 token 是**自回归**解码的，`D × K` 个 token 就是 `D × K` 次串行前向。
**token 数直接等于延迟。**

另一个自由度是「每维用几个 token」：用 2 个 base-64 的 token 可以表达 64² = 4096 个等级，
代价是 token 数翻倍——这就是残差/分层量化的雏形。"""),
    code("""MS_PER_TOKEN = 8.0      # 车端 int8 小模型自回归解码的典型单 token 延迟（量级估计）

def action_budget(name, D, K, B, tokens_per_dim, act_range, need_hz):
    tokens = D * K * tokens_per_dim
    levels = B ** tokens_per_dim          # 每维的有效等级数
    resolution = act_range / levels
    latency_s = tokens * MS_PER_TOKEN / 1000.0
    return {'name': name, 'D': D, 'K': K, 'B': B, 'tpd': tokens_per_dim,
            'tokens': tokens, 'levels': levels, 'resolution': resolution,
            'latency_s': latency_s, 'need_hz': need_hz,
            'budget_s': 1.0 / need_hz, 'feasible': latency_s <= 1.0 / need_hz}

CFGS = [
    action_budget('RT-2 单臂',      D=8,  K=1,  B=256, tokens_per_dim=1, act_range=0.20, need_hz=3),
    action_budget('π0 双臂@50Hz',   D=18, K=50, B=256, tokens_per_dim=1, act_range=0.20, need_hz=50),
    action_budget('自驾 4s@1Hz',    D=2,  K=40, B=256, tokens_per_dim=1, act_range=0.20, need_hz=1),
    action_budget('自驾 双token',   D=2,  K=40, B=64,  tokens_per_dim=2, act_range=0.20, need_hz=1),
    action_budget('EMMA 文本路点',  D=2,  K=40, B=256, tokens_per_dim=4, act_range=0.20, need_hz=1),
]

print(f"{'配置':<15s}{'D':>4s}{'K':>4s}{'B':>6s}{'tpd':>5s}{'tokens':>8s}"
      f"{'等级数':>10s}{'分辨率':>11s}{'延迟s':>8s}{'预算s':>8s}{'可行':>6s}")
for c in CFGS:
    print(f'{c["name"]:<15s}{c["D"]:>4d}{c["K"]:>4d}{c["B"]:>6d}{c["tpd"]:>5d}'
          f'{c["tokens"]:>8d}{c["levels"]:>10d}{c["resolution"]:>11.2e}'
          f'{c["latency_s"]:>8.2f}{c["budget_s"]:>8.2f}{"✅" if c["feasible"] else "❌":>6s}')

by = {c['name']: c for c in CFGS}
assert by['π0 双臂@50Hz']['tokens'] == 900
assert not by['π0 双臂@50Hz']['feasible'], 'π0 的场景下离散 token 自回归不可行'
over = by['π0 双臂@50Hz']['latency_s'] / by['π0 双臂@50Hz']['budget_s']
assert over > 100, '应超预算两个数量级以上'
assert by['自驾 4s@1Hz']['tokens'] == 80 and by['自驾 4s@1Hz']['feasible'], '自驾配置应可行'
assert by['自驾 双token']['levels'] == 4096 > by['自驾 4s@1Hz']['levels']
assert by['自驾 双token']['tokens'] == 2 * by['自驾 4s@1Hz']['tokens'], '精度换 token 是 1:1 的'
assert not by['自驾 双token']['feasible'], '精度翻倍就超出车端预算'
assert not by['EMMA 文本路点']['feasible'], '文本化路点的 token 成本最高'
print()
print(f'❌ **π0 的场景：900 个动作 token，自回归要 {by["π0 双臂@50Hz"]["latency_s"]:.1f} s，'
      f'而它要 50 Hz（20 ms）—— 超预算 {over:.0f} 倍。**')
print('   这就是 π0 必须换成流匹配动作头（一次并行出整块）的直接原因。')
print()
print(f'✅ **自驾只要 {by["自驾 4s@1Hz"]["tokens"]} 个 token，{by["自驾 4s@1Hz"]["latency_s"]:.2f} s '
      f'—— 这是表里唯一可行的离散 token 配置。**动作维度低（2）救了它，')
print('   所以自驾 VLA 完全可以保留「动作即语言」的可解释性。')
print()
print('⚠️  但预算很紧：**「每维两个 token」把等级数从 256 提到 4096（16 倍精度），')
print(f'    token 数翻倍到 {by["自驾 双token"]["tokens"]}，延迟 '
      f'{by["自驾 双token"]["latency_s"]:.2f} s 就超预算了。**')
print('    注意 tokens_per_dim 是**指数换线性**：每 +1，等级数 ×B 而 token 数只 +D*K，')
print('    所以它比「加大 B」划算得多 —— 只是这里连线性的余量都没有了。')
print(f'⚠️  EMMA 式文本路点（一个数约 4 个 token）要 {by["EMMA 文本路点"]["tokens"]} 个 token，')
print('    这正是它只能跑在云端/大算力上、而量产必须蒸馏 + 缩短视界的原因。')"""),
    md("""## 5 · 玩具 VLA 前向：token 拼接 + 因果注意力（纯 numpy）

现在把 §2 的讲解图变成能跑的代码。序列结构：

```
[ 视觉 token × N_v | 文本 token × N_t ][ 动作 token × (D×K) ]
└──────── 前缀：内部双向可见 ────────┘└──── 后缀：因果自回归 ────┘
```

掩码的三条规则（`mask[i,j]=True` 表示位置 i 可以看位置 j）：
1. 前缀内部**双向**——视觉与文本是「条件」，不需要因果性
2. 动作 token 能看**全部前缀 + 它之前的动作 token**
3. **前缀看不到动作 token** —— 这条最容易被写错，但它是 KV 缓存能复用的前提：
   前缀的表示不随生成过程改变，所以只需算一次"""),
    code("""def build_mask(n_vis, n_text, n_act):
    '''mask[i, j] = True 表示位置 i 可以 attend 到位置 j。'''
    n_pre = n_vis + n_text
    n = n_pre + n_act
    m = np.zeros((n, n), dtype=bool)
    m[:n_pre, :n_pre] = True                       # ① 前缀内部双向
    for i in range(n_pre, n):
        m[i, :i + 1] = True                        # ② 动作看全部前缀 + 自己之前
    # ③ 前缀看不到动作：m[:n_pre, n_pre:] 保持 False
    return m

N_VIS, N_TEXT, D_ACT, K_STEP = 6, 5, 2, 4
N_ACT = D_ACT * K_STEP
N_PRE = N_VIS + N_TEXT
mask = build_mask(N_VIS, N_TEXT, N_ACT)

labels = ([f'v{i}' for i in range(N_VIS)] + [f't{i}' for i in range(N_TEXT)] +
          [f'a{k}{d}' for k in range(K_STEP) for d in range(D_ACT)])
print('注意力掩码（行=query 位置，列=key 位置；■ 可见，· 不可见）')
print('      ' + ' '.join(f'{l:>4s}' for l in labels))
for i, l in enumerate(labels):
    tail = ' <- 前缀末尾' if i == N_PRE - 1 else (' <- 第一个动作' if i == N_PRE else '')
    print(f'{l:>5s} ' + ' '.join(f'{"■" if mask[i, j] else "·":>4s}'
                                for j in range(len(labels))) + tail)

assert mask[0, 1] and mask[0, N_PRE - 1], '前缀内部双向'
assert not mask[0, N_PRE], '★ 前缀看不到动作 token（KV 缓存复用的前提）'
assert not mask[N_PRE, N_PRE + 1], '★ 动作 token 看不到未来的动作 token'
assert mask[N_PRE + 1, N_PRE] and mask[N_PRE + 1, 0], '动作能看前缀与之前的动作'
assert mask[N_PRE:, :N_PRE].all(), '所有动作 token 都能看到完整前缀'
print()
print(f'✅ 掩码正确。前缀 {N_PRE} 个 token 只算一次并缓存；'
      f'生成 {N_ACT} 个动作 token 时前缀表示恒定不变。')
print('⚠️  如果第 ③ 条写错（让前缀也能看动作），前缀 KV 每步都要重算 ——')
print('    延迟直接乘以动作 token 数。这是实现 VLA 时最常见的性能 bug。')"""),
    code("""# ── 一个玩具 VLA：视觉投影器 + 1 层 Transformer + LM head ──────────
D_MODEL = 24
V_TEXT, V_BIN = 20, 16              # 文本词表 20，动作 bin 16 -> 总词表 36
VOCAB = V_TEXT + V_BIN
ACT_TOKEN_LO = V_TEXT               # 动作 bin b -> token id (V_TEXT + b)

def init_weights(seed=7):
    g = np.random.default_rng(seed)
    s = lambda *sh: g.normal(0, 0.35, sh)
    return {'Wproj': s(16, D_MODEL),          # 视觉 patch 特征(16 维) -> d_model
            'Emb': s(VOCAB, D_MODEL),         # ★ 文本与动作共享同一张 embedding 表
            'Pos': s(64, D_MODEL) * 0.3,
            'Wq': s(D_MODEL, D_MODEL), 'Wk': s(D_MODEL, D_MODEL),
            'Wv': s(D_MODEL, D_MODEL), 'Wo': s(D_MODEL, D_MODEL),
            'W1': s(D_MODEL, 48), 'W2': s(48, D_MODEL),
            'Whead': s(D_MODEL, VOCAB)}

W = init_weights()

def softmax(z, axis=-1):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)

def build_sequence(patch_feats, text_ids, action_bins, W):
    '''★ 这三行就是 VLA 的全部结构秘密：三种模态被投到同一个 d_model 空间后直接拼接。'''
    vis = patch_feats @ W['Wproj']                              # 视觉：投影器
    txt = W['Emb'][np.asarray(text_ids)]                        # 文本：查表
    act = W['Emb'][np.asarray(action_bins) + ACT_TOKEN_LO]      # 动作：查同一张表
    X = np.concatenate([vis, txt, act], axis=0)
    return X + W['Pos'][:len(X)]

def forward(X, mask, W):
    Q, Kk, V = X @ W['Wq'], X @ W['Wk'], X @ W['Wv']
    s = Q @ Kk.T / math.sqrt(X.shape[1])
    s = np.where(mask, s, -1e30)                                # ★ 掩码
    A = softmax(s, -1)
    H = X + (A @ V) @ W['Wo']                                   # attn + residual
    H = H + np.maximum(H @ W['W1'], 0.0) @ W['W2']              # MLP + residual
    return H @ W['Whead'], A

patch = rng.normal(0, 1, (N_VIS, 16))
text_ids = [3, 7, 1, 12, 5]
act_bins = [2, 9, 3, 8, 4, 7, 5, 6]
X = build_sequence(patch, text_ids, act_bins, W)
logits, A = forward(X, mask, W)

print(f'序列长度 {X.shape[0]} = 视觉 {N_VIS} + 文本 {N_TEXT} + 动作 {N_ACT}')
print(f'X {X.shape}   logits {logits.shape}   注意力 {A.shape}')
assert X.shape == (N_PRE + N_ACT, D_MODEL)
assert logits.shape == (N_PRE + N_ACT, VOCAB)
assert np.allclose(A.sum(1), 1.0), '每行注意力权重应归一化'
assert np.abs(A[:N_PRE, N_PRE:]).max() == 0.0, '前缀对动作的注意力必须恒为 0'
assert np.abs(np.triu(A[N_PRE:, N_PRE:], k=1)).max() == 0.0, '动作对未来的注意力必须为 0'
print()
print('✅ 前向跑通。注意 **动作 embedding 与文本共用同一张表、LM head 也共用** ——')
print('   这就是「复用 VLM 输出头」的字面含义：输出层的形状一个字节都没改。')"""),
    code("""# ── 数值实验：证明掩码真的挡住了未来（而不是"看起来对"）─────────────
p = N_PRE + 3                                   # 挑一个中间的动作 token
act_pert = list(act_bins)
act_pert[p - N_PRE] = (act_pert[p - N_PRE] + 5) % V_BIN     # 只改这一个 token

X2 = build_sequence(patch, text_ids, act_pert, W)
logits2, _ = forward(X2, mask, W)
diff = np.abs(logits2 - logits).max(axis=1)

print(f'扰动位置 p = {p} ({labels[p]})，只改这一个动作 token')
print(f"{'位置':>6s}{'区段':>10s}{'logits 最大变化':>18s}")
for i in [0, N_VIS - 1, N_PRE - 1, N_PRE, p - 1, p, p + 1, len(labels) - 1]:
    seg = '视觉' if i < N_VIS else ('文本' if i < N_PRE else '动作')
    print(f'{i:>6d}{seg:>10s}{diff[i]:>18.3e}')

assert diff[:N_PRE].max() == 0.0, '★ 前缀输出必须**完全**不变（KV 缓存可复用）'
assert diff[N_PRE:p].max() == 0.0, '★ 更早的动作 token 输出必须**完全**不变（因果性）'
assert diff[p] > 1e-6 and diff[p + 1:].max() > 1e-6, '被扰动位置及其之后必须改变'
print()
print('✅ **前缀与更早位置的变化恰好是 0.0（不是"很小"，是精确的 0）** ——')
print('   这既证明了因果性，也证明了前缀 KV 可以安全缓存。')

# 对照组：去掉掩码会发生什么
full = np.ones_like(mask)
lg_a, _ = forward(X, full, W)
lg_b, _ = forward(X2, full, W)
d_full = np.abs(lg_b - lg_a).max(axis=1)
print()
print(f'❌ 去掉掩码后：前缀输出变化 {d_full[:N_PRE].max():.3e}，'
      f'更早动作位置变化 {d_full[N_PRE:p].max():.3e}')
assert d_full[:p].max() > 1e-6, '无掩码时未来会泄漏到过去'
print('   训练时这叫**信息泄漏**：模型抄到了它本该预测的答案，')
print('   于是训练 loss 极低而推理完全不能用 —— 一个非常经典的 VLA 实现 bug。')"""),
    md("""## 6 · 自回归解码动作块 → 还原轨迹

解码时有一个必须做、却经常被漏掉的细节：**把 logits 限制在动作 token 的子集上**
（constrained decoding）。否则模型可能吐出一个文本 token，整条动作序列直接解析失败。

下面先用一个 oracle 打分器验证**解码机制**本身，
再把解出的曲率序列积分成轨迹，看量化误差怎么累积。"""),
    code("""def decode_actions(score_fn, n_steps, constrained=True):
    '''自回归解码 n_steps 个动作 token。score_fn(已生成的 bin 列表) -> 整个词表的 logits。'''
    out = []
    for _ in range(n_steps):
        lg = np.asarray(score_fn(out), dtype=float).copy()
        if constrained:
            lg[:ACT_TOKEN_LO] = -np.inf          # ★ 屏蔽全部文本 token
        tok = int(np.argmax(lg))
        out.append(tok - ACT_TOKEN_LO)           # token id -> bin 编号
    return out

target_bins = [2, 9, 3, 8, 4, 7, 5, 6]

def oracle(prefix):
    '''教师强制式打分器：下一个动作 token 就是 target 里的那个。
       故意把文本 token 的分数设得更高，用来检验 constrained decoding 是否真起作用。'''
    lg = np.full(VOCAB, -5.0)
    lg[:ACT_TOKEN_LO] = 9.0                                  # 陷阱
    lg[ACT_TOKEN_LO + target_bins[len(prefix)]] = 5.0
    return lg

got = decode_actions(oracle, len(target_bins), constrained=True)
bad = decode_actions(oracle, len(target_bins), constrained=False)
print('目标 bin      :', target_bins)
print('constrained   :', got)
print('unconstrained :', bad)
assert got == target_bins, 'constrained decoding 应精确还原目标'
assert bad != target_bins, '不加约束会解码出文本 token'
assert min(bad) < 0, '未受约束时解出的 token id < ACT_TOKEN_LO，成了非法 bin'
print()
print('✅ **必须把 logits 限制在动作 token 子集上。**不做这一步，一次采样意外')
print('   吐出文本 token 就会让整条动作序列解析失败 —— 在温度采样下概率不低。')

# 反离散化回连续动作
LO_K, HI_K, B_K = -0.10, 0.10, 256
demo_kappa = np.array([0.005, 0.021, -0.013, 0.062])
bins = discretize(demo_kappa, LO_K, HI_K, B_K)
rec = undiscretize(bins, LO_K, HI_K, B_K)
print()
print(f"{'真值 kappa':>13s}{'bin':>6s}{'重建':>13s}{'误差':>12s}")
for a, b, r_ in zip(demo_kappa, bins, rec):
    print(f'{a:>13.5f}{b:>6d}{r_:>13.5f}{r_ - a:>12.2e}')
assert np.abs(rec - demo_kappa).max() <= (HI_K - LO_K) / B_K / 2 + 1e-12
print()
print('✅ 每一维的重建误差都不超过 Δ/2 —— 与 §2 的理论完全一致。')"""),
    code("""# ── 量化误差怎么累积成轨迹偏差：零均值 vs 系统性偏置 ────────────────
V_EGO, DT, K_TRAJ = 20.0, 0.1, 40      # 20 m/s，0.1 s 一步，4 s = 80 m

def integrate(kappa_seq, v=V_EGO, dt=DT):
    '''简化自行车模型：沿弧长积分航向角与位置。'''
    theta = x = y = 0.0
    xs, ys = [], []
    for k in kappa_seq:
        ds = v * dt
        theta += k * ds
        x += ds * math.cos(theta); y += ds * math.sin(theta)
        xs.append(x); ys.append(y)
    return np.array(xs), np.array(ys)

kappa_true = rng.normal(0.0, 0.02, K_TRAJ)          # 一段温和的变道/蛇行
delta_k = (HI_K - LO_K) / B_K

kappa_q = undiscretize(discretize(kappa_true, LO_K, HI_K, B_K), LO_K, HI_K, B_K)
kappa_bias = kappa_true + delta_k / 2               # 同幅度，但是系统性的

_, y_true = integrate(kappa_true)
_, y_q = integrate(kappa_q)
_, y_bias = integrate(kappa_bias)
dev_rand = float(np.abs(y_q - y_true).max())
dev_sys = float(np.abs(y_bias - y_true).max())

print(f'Δκ = {delta_k:.3e} 1/m，行驶 {V_EGO * DT * K_TRAJ:.0f} m（{K_TRAJ * DT:.0f} s）')
print(f'  量化误差**零均值**（取 bin 中心）: 最大横向偏差 {dev_rand:.4f} m')
print(f'  同幅度的**系统性偏置**(+Δ/2)     : 最大横向偏差 {dev_sys:.4f} m')
print(f'  比值: {dev_sys / dev_rand:.1f}x')
assert dev_sys > 3 * dev_rand, '系统性偏置的累积应远快于零均值随机误差'
assert dev_rand < 0.5, '零均值量化误差在 4 s 内不应造成半米以上的偏差'
print()
print('✅ **这就是「反离散化必须取 bin 中心」的工程理由**：')
print('   取 bin 下沿会引入 +Δ/2 的系统性偏置，而偏置沿轨迹按 L² 累积，')
print('   零均值随机误差只按随机游走（约 √K）累积 —— 两者差一个数量级。')
print('⚠️  推论：任何让动作误差**变成有偏**的处理（单侧截断、非对称归一化范围、')
print('    把 clip 掉的动作都压到边界 bin）都要格外小心 ——')
print('    它们的代价远大于误差幅值本身。')"""),
    md("""## ✏️ 练习 1：等质量分箱（非均匀 bin）

均匀分箱把 bin 均匀地铺在动作范围上，但驾驶动作分布极度集中在 0 附近
（80% 是直行）——**大量 bin 浪费在几乎没有样本的大曲率区间**。

等质量分箱（quantile binning）让每个 bin 装差不多数量的样本。
**先猜一下：它会让重建误差变好还是变差？** 做完再看结论——大概率和你想的不一样。

实现两个函数：

- `quantile_edges(samples, B)` → 长度 `B+1` 的单调不减边界数组，用 `np.quantile` 在
  `linspace(0, 1, B+1)` 上取分位数
- `decode_edges(b, edges)` → bin 编号还原成连续值，取该 bin 的**中点**
  `(edges[b] + edges[b+1]) / 2`（支持数组输入）"""),
    code("""def quantile_edges(samples, B):
    # TODO: 返回长度 B+1 的边界数组
    raise NotImplementedError

def decode_edges(b, edges):
    # TODO: bin 编号 -> bin 中点（支持 numpy 数组）
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
def encode_edges(a, edges):
    return np.clip(np.searchsorted(edges, a, side='right') - 1, 0, len(edges) - 2)

rms = lambda e: float(np.sqrt((np.asarray(e) ** 2).mean()))
x_in = kappa[inlier]
Bq = 64

edges = quantile_edges(x_in, Bq)
assert len(edges) == Bq + 1, f'应有 {Bq + 1} 个边界，得到 {len(edges)}'
assert np.all(np.diff(edges) >= 0), '边界必须单调不减'
assert np.isclose(edges[0], x_in.min()) and np.isclose(edges[-1], x_in.max())

rec_q = decode_edges(encode_edges(x_in, edges), edges)
rec_u = undiscretize(discretize(x_in, -0.10, 0.10, Bq), -0.10, 0.10, Bq)
e_q, e_u = np.abs(rec_q - x_in), np.abs(rec_u - x_in)

print(f"{'分箱方式':<18s}{'中位数误差':>14s}{'RMS 误差':>14s}{'最大误差':>14s}")
print(f'{"均匀 (uniform)":<18s}{np.median(e_u):>14.3e}{rms(e_u):>14.3e}{e_u.max():>14.3e}')
print(f'{"等质量 (quantile)":<18s}{np.median(e_q):>14.3e}{rms(e_q):>14.3e}{e_q.max():>14.3e}')
print(f'等质量相对均匀:      中位数 {np.median(e_u) / np.median(e_q):>5.1f}x 更好   '
      f'RMS {rms(e_q) / rms(e_u):>5.1f}x 更差   最坏 {e_q.max() / e_u.max():>5.1f}x 更差')

assert np.median(e_q) < np.median(e_u) / 5, '等质量分箱应显著改善**中位数**误差'
assert rms(e_q) > 2 * rms(e_u), '★ 但 RMS 反而更差（尾部的大 bin 主导了平方误差）'
assert e_q.max() > 5 * e_u.max(), '★ 最坏情况差一个数量级'
assert e_u.max() <= 0.20 / Bq / 2 + 1e-12, '均匀分箱的最坏情况有解析上界 Δ/2'
print()
print('✅ 练习 1 通过 —— 而且结论可能和你预期的相反：')
print(f'   ① 等质量分箱把**中位数**误差改善了 {np.median(e_u) / np.median(e_q):.0f} 倍'
      f'（80% 的动作是直行，它们分到了极细的 bin）')
print(f'   ② 但 **RMS 差了 {rms(e_q) / rms(e_u):.1f} 倍、最坏情况差了 '
      f'{e_q.max() / e_u.max():.0f} 倍** —— 因为尾部（路口转弯、紧急避让）')
print('      被塞进了极少数几个巨大的 bin，而平方误差与最坏情况都由尾部主导。')
print()
print('   **这就是 RT-2 / OpenVLA 坚持均匀分箱的原因**：均匀分箱的最坏误差有')
print(f'   解析上界 Δ/2 = {0.20 / Bq / 2:.2e}，与数据分布无关；等质量分箱没有这个保证。')
print('   在安全攸关系统里，「最坏情况有界」比「平均更准」重要得多。')"""),
    md("""## ✏️ 练习 2：给定分辨率目标，求最小 token 成本

每维用 `t` 个 base-`B` 的 token，可表达 `B^t` 个等级，分辨率是 `act_range / B^t`。
**等级数随 t 指数增长，token 数只随 t 线性增长**——所以「加 token 位数」比「加大 B」划算。

实现 `min_tokens_for_resolution(D, K, act_range, target_res, B=256, t_max=6)`，返回
`{'tokens_per_dim': t, 'levels': B**t, 'resolution': act_range/B**t, 'tokens': D*K*t}`，
其中 `t` 是使 `act_range / B**t <= target_res` 成立的**最小正整数**。
若 `t_max` 内无解，抛 `ValueError`。"""),
    code("""def min_tokens_for_resolution(D, K, act_range, target_res, B=256, t_max=6):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
r1 = min_tokens_for_resolution(2, 40, 0.20, 1e-3)
r2 = min_tokens_for_resolution(2, 40, 0.20, 1e-4)
r3 = min_tokens_for_resolution(2, 40, 0.20, 1e-6)
assert r1['tokens_per_dim'] == 1 and r1['tokens'] == 80, r1
assert r2['tokens_per_dim'] == 2 and r2['tokens'] == 160 and r2['levels'] == 65536, r2
assert r3['tokens_per_dim'] == 3 and r3['tokens'] == 240, r3
assert r1['resolution'] <= 1e-3 and r2['resolution'] <= 1e-4
try:
    min_tokens_for_resolution(2, 40, 0.20, 1e-20, t_max=2)
    raise AssertionError('无解时应抛 ValueError')
except ValueError:
    pass

print(f"{'目标分辨率':>12s}{'t':>4s}{'等级数':>12s}{'实际分辨率':>14s}{'tokens':>8s}")
for tr in [1e-2, 1e-3, 1e-4, 1e-5, 1e-6]:
    r = min_tokens_for_resolution(2, 40, 0.20, tr)
    print(f'{tr:>12.0e}{r["tokens_per_dim"]:>4d}{r["levels"]:>12d}'
          f'{r["resolution"]:>14.2e}{r["tokens"]:>8d}')
print()
print('✅ 练习 2 通过：**分辨率提高 256 倍，token 数只 +1 倍**（指数换线性）。')
print('   这就是残差量化 / 分层动作 token 的思想雏形 ——')
print('   但注意 token 数直接等于自回归延迟，所以 t 的余量在车端非常有限（见 §4）。')"""),
    md("""## ✏️ 练习 3：动作分块的注意力掩码

§5 的掩码是逐 token 因果的：`D×K` 个动作 token 要串行解码 `D×K` 步。
**但同一个时间步的 D 个维度其实可以并行出**——它们之间不需要因果性。

于是把动作 token 按 `chunk`（= D）分块：**块内双向、块间因果**，
串行步数从 `D×K` 降到 `K`，延迟降为 `1/D`。

实现 `build_chunk_mask(n_prefix, n_act, chunk)`：
- 前缀内部双向；前缀**看不到**动作
- 动作行能看：全部前缀 + **自己所在块及之前所有块**的动作 token
- 保证 `n_act % chunk == 0`（否则抛 `ValueError`）"""),
    code("""def build_chunk_mask(n_prefix, n_act, chunk):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
NP, NA, CH = 4, 6, 2          # 前缀 4，动作 6（3 块 × 每块 2 维）
cm = build_chunk_mask(NP, NA, CH)
assert cm.shape == (NP + NA, NP + NA)
assert cm[0, 1] and not cm[0, NP], '前缀双向、且看不到动作'
assert cm[NP, NP + 1] and cm[NP + 1, NP], '★ 同一块内双向（同一时间步的各维可并行）'
assert not cm[NP, NP + 2], '★ 看不到之后的块'
assert cm[NP + 2, NP] and cm[NP + 2, NP + 1] and cm[NP + 2, NP + 3], '能看之前的块与同块'
assert not cm[NP + 2, NP + 4]
assert cm[NP:, :NP].all(), '所有动作都能看到完整前缀'
assert int(cm[NP].sum()) == NP + CH, f'第一块的行应能看 {NP + CH} 个位置'
try:
    build_chunk_mask(4, 7, 2)
    raise AssertionError('n_act 不能被 chunk 整除时应抛 ValueError')
except ValueError:
    pass

# 退化检查：chunk=1 时应与逐 token 因果掩码完全一致
assert np.array_equal(build_chunk_mask(N_PRE, N_ACT, 1), build_mask(N_VIS, N_TEXT, N_ACT)), \\
    'chunk=1 应退化为 §5 的逐 token 因果掩码'

lab = [f'p{i}' for i in range(NP)] + [f'a{i}' for i in range(NA)]
print('分块掩码（chunk=2）')
print('     ' + ' '.join(f'{l:>3s}' for l in lab))
for i, l in enumerate(lab):
    print(f'{l:>4s} ' + ' '.join(f'{"■" if cm[i, j] else "·":>3s}' for j in range(len(lab))))

D_, K_ = 2, 40
print()
print(f'✅ 练习 3 通过：D={D_}, K={K_} 时')
print(f'   逐 token 因果: 串行 {D_ * K_} 步   分块(chunk={D_}): 串行 {K_} 步 '
      f'—— 延迟降为 1/{D_}')
print('⚠️  代价：同块内各维之间失去了条件依赖，模型必须独立地预测它们。')
print('    对「纵向加速度」与「曲率」这种弱耦合的维度可以接受；')
print('    对强耦合的维度（如双臂的协同关节角）会掉点 —— 这是一个真实的取舍。')"""),
    md("""## ✏️ 练习 4：动作头选型决策器

把 §4 的 token 预算与 §6 的差异整合成一个决策函数
`pick_action_head(D, K, hz, need_multimodal, need_explainable, ms_per_token=8.0)`。

判定顺序（**必须严格按此顺序**）：
1. `tokens = D*K`，`latency = tokens*ms_per_token/1000`，`budget = 1/hz`
2. 若 `latency <= budget` **且** `need_explainable` → `'discrete'`（能用离散就用，它最便宜且可解释）
3. 否则若 `need_multimodal` → `'flow'`（要表达多模态，只能上流匹配/扩散）
4. 否则 → `'regression'`（单模态且不要求可解释，回归头最省）

返回 `{'head': …, 'tokens': …, 'latency_s': …, 'budget_s': …}`。"""),
    code("""def pick_action_head(D, K, hz, need_multimodal, need_explainable, ms_per_token=8.0):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
CASES = [
    ('π0 双臂灵巧@50Hz',   dict(D=18, K=50, hz=50, need_multimodal=True,  need_explainable=False), 'flow'),
    ('自驾 VLA 4s@1Hz',    dict(D=2,  K=40, hz=1,  need_multimodal=True,  need_explainable=True),  'discrete'),
    ('低层控制器@50Hz',    dict(D=2,  K=1,  hz=50, need_multimodal=False, need_explainable=False), 'regression'),
    ('RT-2 单臂@3Hz',      dict(D=8,  K=1,  hz=3,  need_multimodal=False, need_explainable=True),  'discrete'),
    ('自驾长视界 8s@1Hz',  dict(D=2,  K=80, hz=1,  need_multimodal=True,  need_explainable=True),  'flow'),
]
print(f"{'场景':<20s}{'tokens':>8s}{'延迟s':>8s}{'预算s':>8s}{'选型':>12s}{'期望':>12s}")
for name, kw, expect in CASES:
    r = pick_action_head(**kw)
    ok = r['head'] == expect
    print(f'{name:<20s}{r["tokens"]:>8d}{r["latency_s"]:>8.2f}'
          f'{r["budget_s"]:>8.2f}{r["head"]:>12s}{expect:>12s}' + ('' if ok else '  ❌'))
    assert ok, f'{name}: 期望 {expect}，得到 {r["head"]}'
print()
print('✅ 练习 4 通过。注意最后一行：**同样是自驾，把视界从 4 s 拉到 8 s，')
print('   token 数翻倍就超预算，选型直接从 discrete 翻到 flow。**')
print('   动作头选型不是一个「哪个更先进」的问题，是一个**预算约束下的可行解问题**。')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def quantile_edges(samples, B):
    qs = np.linspace(0.0, 1.0, B + 1)
    return np.quantile(np.asarray(samples, dtype=float), qs)

def decode_edges(b, edges):
    b = np.asarray(b, dtype=int)
    return (edges[b] + edges[b + 1]) / 2.0"""),
    code("""# 练习 2 参考答案
def min_tokens_for_resolution(D, K, act_range, target_res, B=256, t_max=6):
    for t in range(1, t_max + 1):
        levels = B ** t
        res = act_range / levels
        if res <= target_res:
            return {'tokens_per_dim': t, 'levels': levels,
                    'resolution': res, 'tokens': D * K * t}
    raise ValueError(f't_max={t_max} 内无法达到分辨率 {target_res}')"""),
    code("""# 练习 3 参考答案
def build_chunk_mask(n_prefix, n_act, chunk):
    if n_act % chunk != 0:
        raise ValueError(f'n_act={n_act} 不能被 chunk={chunk} 整除')
    n = n_prefix + n_act
    m = np.zeros((n, n), dtype=bool)
    m[:n_prefix, :n_prefix] = True                     # 前缀内部双向
    for i in range(n_prefix, n):
        m[i, :n_prefix] = True                         # 动作看全部前缀
        ci = (i - n_prefix) // chunk
        for j in range(n_prefix, n):
            if (j - n_prefix) // chunk <= ci:           # 同块或更早的块
                m[i, j] = True
    return m"""),
    code("""# 练习 4 参考答案
def pick_action_head(D, K, hz, need_multimodal, need_explainable, ms_per_token=8.0):
    tokens = D * K
    latency = tokens * ms_per_token / 1000.0
    budget = 1.0 / hz
    if latency <= budget and need_explainable:
        head = 'discrete'
    elif need_multimodal:
        head = 'flow'
    else:
        head = 'regression'
    return {'head': head, 'tokens': tokens, 'latency_s': latency, 'budget_s': budget}"""),
    md("""---
## 🧪 真实工程胶囊：动作 tokenizer 的实现清单

下面这份是把 OpenVLA 的做法落成可直接抄的配置与检查项。
**每一条注释都对应本 notebook 里算过的一个数。**"""),
    code("""RECIPE = r'''
# ── configs/action_tokenizer.yaml ───────────────────────────────────
# 与模型权重一起版本化。改动任何一项都必须重训或至少重跑动作重建检查。

action_space:
  dims: [a_lon, kappa]              # 自驾: 2 维就够（对比 π0 的 18 维）
  units: ["m/s^2", "1/m"]
  horizon_s: 4.0
  dt_s: 0.1                          # -> K = 40 步, tokens = 2*40 = 80

normalization:
  method: quantile                   # ★ 不要用 min/max
  q_low: 0.01                        # OpenVLA 的选择。5%/95% 会裁掉太多真实动作
  q_high: 0.99
  fit_on: train_split_only           # 千万别在全量数据上 fit（信息泄漏）
  clip_rate_alarm: 0.02              # ★ 裁剪率 > 2% 报警 = 动作分布漂移了

binning:
  scheme: uniform                    # ★ 均匀而非等质量：宁可平均差一点，也要最坏情况有界
  n_bins: 256                        # 30m 处最大横向误差 0.18m / 50m 处 0.49m
  decode: bin_center                 # ★ 必须取中心：取下沿会引入 +Δ/2 的**系统性偏置**，
                                     #   偏置按 L^2 累积（80m 上 1.28m），随机误差只按 √K（0.05m）
  tokens_per_dim: 1                  # 提到 2 -> 等级数 x256，但 token 数翻倍会超车端预算

vocab_mapping:
  strategy: overwrite_least_used     # ★ 覆盖 tokenizer 里最少用的 256 个 token，
                                     #   不新增词表 -> embedding 与 LM head 形状不变
  forbid_numeric_strings: true       # ★ 别把动作写成 "128" —— tokenizer 会切成不定长

decoding:
  constrained: true                  # ★ logits 屏蔽全部非动作 token，否则整条序列解析失败
  chunk_parallel_dims: true          # 块内双向 -> 串行步数 D*K -> K，延迟降为 1/D
  temperature: 0.0                   # 动作解码用 greedy；采样只在需要多候选轨迹时开

# ── 上线前必须过的 5 条检查（都在本 notebook 里实现过）─────────────
# 1. 往返无损:   bin -> action -> bin 必须恒等
# 2. 误差界:     |ε|max <= Δ/2 且 ε_RMS ≈ Δ/√12（偏离说明反离散化写错了）
# 3. 零均值:     E[ε] ≈ 0（非零 = 有系统性偏置 = 轨迹会按 L^2 漂）
# 4. 因果性:     扰动第 p 个动作 token，位置 < p 的 logits 变化必须**精确为 0**
# 5. 前缀不变:   扰动任意动作 token，前缀 logits 变化必须为 0（否则 KV 缓存不能复用）
'''
print(RECIPE)
for key in ['quantile', 'q_low', 'clip_rate_alarm', 'bin_center', 'overwrite_least_used',
            'forbid_numeric_strings', 'constrained', 'chunk_parallel_dims']:
    assert key in RECIPE, key
print()
print('✅ 清单覆盖：分位数归一化 / 均匀分箱 / bin 中心解码 / 词表覆盖策略 /')
print('   受约束解码 / 分块并行 / 5 条上线前检查 —— 每条都对应本 notebook 的一个实验。')"""),
    md("""### 小结

- **VLA 不是新架构，是在 VLM 既有的「模态无关序列接口」上多插了一个模态。**
  视觉靠投影器进来，动作靠离散化出去——两者用的是同一个技巧。
- **RT-2 的贡献是那个转换本身，不是效果数字**：动作离散化成 token、复用 LM head，
  于是机器人学习可以直接继承互联网规模的预训练。代价有三条且是范式自带的：
  **分箱误差有硬下界、token 之间没有序关系、自回归解码是串行的**。
- **归一化用 1%/99% 分位数而不是 min/max**：0.1% 的离群值就能让有效 bin 数掉 5 倍。
  但**分箱本身要用均匀而非等质量**——等质量把中位数误差改善 10 倍，
  却让 RMS 差 3 倍、最坏情况差 14 倍（尾部的路口转弯被塞进几个巨大的 bin）。
  **均匀分箱的最坏误差有与分布无关的解析上界 Δ/2，安全攸关系统要的正是这个。**
- **把精度换算成工程指标**：256 个 bin 在 30 m 处最大横向误差 0.18 m、50 m 处 0.49 m；
  要把 50 m 压到 10 cm 以内需要 ≥1250 个 bin。**这是「机器人动作表示不能直接搬到车上」的算术证明。**
- **反离散化必须取 bin 中心**：系统性偏置沿轨迹按 L² 累积（80 m 上 1.28 m），
  零均值随机误差只按 √K 累积（0.05 m）——**差 26 倍**。
- **token 数 = 延迟**。π0 的 900 个动作 token 在 50 Hz 下超预算两个数量级，
  所以它必须换流匹配头；**自驾只要 80 个 token，所以离散 token 仍然可用**，
  这也是自驾 VLA 有条件保留可解释性的原因。
- **两个必须写对的实现细节**：① 掩码里「前缀看不到动作」——写错则 KV 缓存失效，
  延迟乘以动作 token 数；② 解码时把 logits 限制在动作 token 子集上——不做则整条序列解析失败。
- **机器人 VLA 的难点在动作端，自驾 VLA 的难点在感知端与安全端。**
  所以两边往相反方向走：机器人在换动作头，自驾在做接口与兜底。

下一站：**模块 02 · 动作表示与输出头设计** —— 为什么回归头会在路口输出「直行」，
以及动作分块怎么救延迟。""")
]
