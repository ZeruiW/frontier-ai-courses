# -*- coding: utf-8 -*-
"""C52 模块 02 · 框架迁移与权重对齐。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "模块 00–01；线性代数（转置与 reshape 的区别）；C50 模块 01 的 state_dict 概念"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_weight_porting.ipynb'),
    ("核心参考", "PyTorch / TensorFlow 的层文档（权重形状与默认值）、cuDNN 的 RNN 权重布局、HF 各模型的 conversion 脚本"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    ("why", "为什么「换个框架重训一遍」通常不是答案", "".join([
        P("拿到一份 TF 实现、要在 PyTorch 里用，直觉上有两条路：<strong>①照着代码重写并重新训练；②把训练好的权重搬过来</strong>。很多人默认选 ①，因为 ② 听起来麻烦。这个默认选择通常是错的。"),
        TABLE(["", "重写 + 重训", "权重迁移"], [
            ["算力成本", "<strong>完整的训练成本</strong>（可能几万美元）", "几乎为零"],
            ["数据依赖", "<strong>需要原始训练数据</strong>（常常拿不到）", "不需要"],
            ["能否复现原结果", "🔶 受随机性、超参、数据版本影响，常常复现不出", "<strong>✅ 数值等价，逐位可验证</strong>"],
            ["调试难度", "「效果差 2 个点」——原因可能有二十个", "「第 7 层数值对不上」——<strong>可定位到具体一层</strong>"],
            ["时间", "数天到数周", "<strong>数小时到一两天</strong>"],
            ["前提", "有数据、有算力、有完整超参", "有权重文件、两边结构对应"],
        ]),
        DUAL(
            "最关键的是<strong>第四行「调试难度」</strong>。重训失败时你面对的是一个<em>联合假设</em>：可能是学习率不同、可能是数据预处理不同、可能是初始化不同、可能是某个层的默认参数不同、也可能只是种子不好（C49 模块 03 讲过种子方差有 2–3 分）。<em>这些原因无法逐个排除。</em>",
            "而权重迁移把问题变成了<strong>可分解、可定位的</strong>：喂同一个输入，逐层比较激活值，<em>第一个数值对不上的层就是问题所在</em>。这是一个「二分查找」而不是「大海捞针」。<strong>这就是本模块的核心方法学：迁移的正确做法不是「搬完跑一下看效果」，而是「搬一层、验一层」</strong>。",
        ),
        CALLOUT("intuition", "还有一个常被忽略的收益：<strong>权重迁移会强迫你真正读懂两边的实现</strong>。为了让第 7 层对上，你必须搞清楚它的权重布局、激活函数、归一化的 eps、是否有偏置。<em>这个过程产出的理解，远超「读一遍代码」</em>。很多人是在做迁移时才第一次发现「原来这个模型的 FFN 用的是 GEGLU 不是 GELU」。"),
    ])),
    ("layout", "权重布局：形状对了不等于内容对了", "".join([
        P("迁移的第一类坑：<strong>两个框架用同样的形状表示<em>不同</em>的东西，或者用不同的形状表示同一个东西</strong>。前者更危险，因为 <code>reshape</code> 会「成功」。"),
        TABLE(["层", "PyTorch 形状", "TF/Keras 形状", "转换", "reshape 会怎样"], [
            ["<strong>Linear / Dense</strong>", "<code>(out, in)</code>", "<code>(in, out)</code>", "<strong>转置</strong> <code>.T</code>", "形状对但等价于用了转置矩阵——完全错"],
            ["<strong>Conv2d</strong>", "<code>(out, in, kH, kW)</code>", "<code>(kH, kW, in, out)</code>", "<code>transpose(2,3,1,0)</code>", "形状对但卷积核彻底乱掉"],
            ["<strong>Conv1d</strong>", "<code>(out, in, k)</code>", "<code>(k, in, out)</code>", "<code>transpose(2,1,0)</code>", "同上"],
            ["<strong>ConvTranspose2d</strong>", "<code>(in, out, kH, kW)</code>", "<code>(kH, kW, out, in)</code>", "注意 in/out <strong>本身就是反的</strong>", "极易搞错"],
            ["<strong>Embedding</strong>", "<code>(vocab, dim)</code>", "<code>(vocab, dim)</code>", "无需转换", "—"],
            ["<strong>LayerNorm γ/β</strong>", "<code>(dim,)</code>", "<code>(dim,)</code>", "无需转换", "—"],
            ["<strong>GRU/LSTM</strong>", "<code>(3H, in)</code> / <code>(4H, in)</code>，<strong>门顺序固定</strong>", "<code>(in, 3H)</code>，<strong>门顺序不同</strong>", "转置 + <strong>门重排</strong>", "形状对但门功能全错位"],
        ]),
        DUAL(
            "<strong>为什么 <code>reshape</code> 不能替代 <code>transpose</code></strong>，值得说清楚，因为这是最常见的错误。<code>reshape</code> 只是<em>重新解释同一块连续内存的形状</em>，元素的线性顺序不变；<code>transpose</code> 则是<em>改变元素的排列顺序</em>。对一个 <code>(16,3,5,5)</code> 的卷积核，<code>reshape(5,5,3,16)</code> 与 <code>transpose(2,3,1,0)</code> 得到的形状完全一样，但内容毫无关系。<em>而代码不会报任何错。</em>",
            "<strong>RNN 的门顺序</strong>是更隐蔽的一类。PyTorch 的 GRU 权重是 <code>[W_r; W_z; W_n]</code>（reset、update、new）；TF/Keras 的顺序是 <code>[W_z; W_r; W_h]</code>（update、reset、new）——<em>前两个门是反的</em>。LSTM 同理：PyTorch 是 <code>[i; f; g; o]</code>，而 cuDNN/TF 的某些实现是 <code>[i; f; o; g]</code> 或 <code>[i; g; f; o]</code>。<strong>门顺序错了，模型仍能跑、loss 也能降（因为门是对称可学的），但用预训练权重时输出完全错。</strong>",
        ),
        CALLOUT("danger", "<p>还有一个几乎无人提前想到的坑：<strong>PyTorch 的 <code>nn.Linear</code> 计算的是 <code>y = xWᵀ + b</code></strong>（注意那个转置），所以它存的 <code>weight</code> 是 <code>(out, in)</code>；而 Keras 的 <code>Dense</code> 计算 <code>y = xW + b</code>，存的是 <code>(in, out)</code>。<em>两者存的其实是同一个矩阵的转置</em>。如果你从 Keras 搬到 PyTorch 时忘了转置，且恰好 <code>in == out</code>（Transformer 里非常常见！），<strong>形状检查会通过，模型会跑，结果全错</strong>。这就是为什么方阵层是迁移事故的重灾区——<em>形状检查这道防线在方阵上完全失效</em>。</p>", "方阵层：形状检查这道防线失效"),
    ])),
    ("naming", "命名映射：从「手写字典」到「结构化匹配」", "".join([
        P("第二类工作是把两边的参数名对应起来。参数动辄几百个，手写映射既慢又易错。有三档做法："),
        TABLE(["做法", "怎么做", "适合", "风险"], [
            ["<strong>① 手写字典</strong>", "逐条写 <code>{'tf/name': 'torch.name'}</code>", "小模型（&lt;30 个参数）", "漏项、写错；改结构就要重写"],
            ["<strong>② 规则替换</strong>", "正则把命名约定映射过去（<code>kernel→weight</code>、<code>bias→bias</code>、<code>/</code>→<code>.</code>）", "命名规整的模型", "特例（如 <code>gamma/beta</code> vs <code>weight/bias</code>）"],
            ["<strong>③ 结构化匹配</strong>", "按<strong>形状 + 层序 + 类型</strong>自动配对，人工只确认歧义项", "大模型", "形状相同的层可能配错——<em>所以必须配数值验证</em>"],
            ["<strong>④ 按数值验证反推</strong>", "先用 ② 或 ③ 得到候选映射，再逐层对拍，不匹配的手工修", "<strong>推荐组合</strong>", "—"],
        ]),
        DUAL(
            "实践中最有效的是 <strong>②+④ 的组合</strong>：先用规则映射覆盖 90% 的参数，再用逐层数值对拍找出剩下的问题。<em>关键在于「数值对拍」这一步不是可选的验证，而是映射过程的一部分</em>——它把「我以为映射对了」变成「我验证了映射对了」。",
            "命名上还有几个几乎每次都会遇到的特例：<strong>①LayerNorm 的参数名</strong>——TF 叫 <code>gamma/beta</code>，PyTorch 叫 <code>weight/bias</code>；<strong>②Embedding 的名字</strong>——TF 常叫 <code>embeddings</code>，PyTorch 叫 <code>weight</code>；<strong>③BatchNorm 的四个量</strong>——<code>gamma/beta/moving_mean/moving_variance</code> vs <code>weight/bias/running_mean/running_var</code>，而且<em>后两个是 buffer 不是 parameter</em>，很容易在遍历参数时被漏掉；<strong>④权重共享</strong>——嵌入与输出层 tie 在一起时，一边可能只存一份、另一边存两份。",
        ),
        CALLOUT("warn", "<strong>「漏掉的参数」比「映射错的参数」更危险</strong>。映射错了通常会造成明显的输出异常；<em>而漏掉一个参数（如 BatchNorm 的 <code>running_var</code>）会让它保持随机初始化，模型在训练模式下看起来正常（用 batch 统计），一切到 eval 模式就崩</em>。所以迁移脚本的第一个断言应该是：<strong>目标模型的<em>每一个</em>参数与 buffer 都被赋值过</strong>——用一个 <code>assigned</code> 集合逐个记录，最后检查差集为空。"),
    ])),
    ("numeric", "数值等价：一套可复用的验证方法学", "".join([
        P("这是本模块最核心的部分。<strong>「搬完跑一下看效果」是错误的验证方式</strong>——它把一个可精确定位的问题，变成了一个模糊的性能问题。正确做法是四步："),
        ASCII("""① 固定输入
   用同一个确定性输入（如 np.arange 或固定种子的随机数）喂给两边
   ⚠️ 关掉一切随机性：dropout=eval、固定 seed、关掉数据增强

② 抓取逐层激活
   PyTorch: register_forward_hook 收集每层输出
   TF/Keras: keras.Model(inputs, [层.output for 层 in model.layers])
   -> 得到两个 {层名: 激活} 字典

③ 按执行顺序逐层对拍，**在第一个失配处停下**
   for name in order:
       报告 = allclose_report(ref[name], new[name])
       if not 报告.ok: 这就是问题所在，不用看后面
   （后面的层全错只是这一层的后果，看它们浪费时间）

④ 按 dtype 与深度设定容差
   fp32 单层 ~1e-6；fp32 96 层 ~1e-5；fp16 要放宽两个数量级
   ⚠️ 容差设错会造成两类错误：太紧 -> 假警报；太松 -> 真错误被放过""")
        ,
        TABLE(["失配的表现", "最可能的原因", "怎么确认"], [
            ["<strong>第一层就差很多</strong>", "输入预处理不同（归一化、通道顺序、缩放）", "先对拍<em>输入张量本身</em>，不要从模型第一层开始"],
            ["<strong>某个卷积层开始差</strong>", "权重布局没转置；padding 模式不同（<code>same</code> 的实现有差异）", "单独构造一个只有这一层的最小例子"],
            ["<strong>归一化层后差异变大</strong>", "eps 不同；BN 用了 batch 统计而非滑动统计（忘了 eval 模式）", "打印两边的 eps 与 running 统计量"],
            ["<strong>差异很小但逐层累积</strong>", "正常的浮点误差；或 dtype 不一致（一边 fp32 一边 fp16）", "对比 dtype；按深度调容差"],
            ["<strong>只有 batch>1 时差</strong>", "padding/mask 处理不同；BN 在不同 batch 上的统计", "用 batch=1 与 batch=4 分别测"],
            ["<strong>只有某些输入时差</strong>", "控制流分支（追踪固化，模块 01）；数值边界（溢出、除零）", "找出触发的输入特征"],
        ]),
        DUAL(
            "这张表的用法是<strong>把「效果不对」这个模糊症状，翻译成一个可查表的具体现象</strong>。做法是：先跑逐层对拍拿到「第一个失配的层」与「差异的量级」，再对照表格定位原因。<em>这比「重新读一遍两边的代码」快一个数量级</em>。",
            "第一行值得单独强调：<strong>非常多的迁移问题其实出在模型之外</strong>——图像的通道顺序（RGB vs BGR）、归一化的均值方差、文本的分词器版本、是否加特殊 token。<em>所以对拍的第一步应该是对拍「喂进模型的那个张量」，而不是模型的第一层输出</em>。这一步能省掉大量在模型内部瞎找的时间。",
        ),
        CALLOUT("intuition", "一个能大幅提速的技巧：<strong>先用「全 1 输入 + 全 1 权重」做结构性验证，再用真实权重做数值验证</strong>。全 1 输入下，任何布局错误都会立刻表现为数量级差异（因为求和的项数不同），而且结果是可以手算的。<em>这一步能在五分钟内抓出所有布局与形状类错误</em>，剩下的才是真正的数值细节（eps、精度、统计量）。"),
    ])),
    ("checklist", "迁移 checklist：按这个顺序做", "".join([
        TABLE(["步骤", "做什么", "验收断言"], [
            ["<strong>① 对齐输入</strong>", "确认预处理完全一致（归一化、通道序、分词器、特殊 token）", "<code>allclose(input_a, input_b)</code>"],
            ["<strong>② 清点参数</strong>", "两边各列出全部 parameter <em>与 buffer</em>，比较总数与总元素数", "<code>sum(numel) 相等</code>（不等说明有结构差异）"],
            ["<strong>③ 建立映射</strong>", "规则映射 + 人工确认歧义项", "<strong>目标侧每个参数都被赋值过</strong>（差集为空）"],
            ["<strong>④ 布局转换</strong>", "对 Linear/Conv/RNN 做转置与门重排", "往返转换无损：<code>back(fwd(w)) == w</code>"],
            ["<strong>⑤ 对齐超参</strong>", "eps、momentum、激活函数变体、是否有 bias", "逐项打印两边的值做人工核对"],
            ["<strong>⑥ 设为推理模式</strong>", "<code>model.eval()</code> / <code>training=False</code>；关 dropout", "<strong>连续两次前向结果完全相同</strong>（否则还有随机性）"],
            ["<strong>⑦ 逐层对拍</strong>", "按执行顺序，第一个失配处停下", "全部层通过给定容差"],
            ["<strong>⑧ 端到端对拍</strong>", "在一批真实数据上比最终输出与下游指标", "指标差异 &lt; 容差；<strong>并记录进交付契约</strong>"],
        ]),
        DUAL(
            "步骤 ⑥ 的验收断言（「连续两次前向结果完全相同」）是个非常有用的小检查，<strong>它能一次性抓出所有未关闭的随机性</strong>——dropout 没关、BN 还在用 batch 统计、数据增强还开着、甚至某个自定义层里有随机数。<em>而这些随机性会让后面的对拍出现「时对时不对」的诡异现象，极难定位。</em>",
            "步骤 ② 的「比较总元素数」也值得强调：<strong>它是最便宜的结构性检查</strong>。如果两边的参数总量对不上，说明结构本身就不同（少了一层、多了一个 bias、嵌入没有 tie），<em>这时任何映射工作都是白费</em>。<em>先确认总量相等，再谈逐个映射</em>——这个顺序能省掉大量返工。",
        ),
        CALLOUT("warn", "步骤 ⑧ 的最后半句「<strong>记录进交付契约</strong>」不要跳过。迁移后的模型与原模型<em>不是逐位相同的</em>（浮点顺序、kernel 实现都有差异），所以必须明确写出：在什么输入范围内、什么 dtype 下、容差是多少。<em>否则三个月后有人发现「输出差了 1e-4」，就会有一场关于「这算不算 bug」的无谓讨论</em>。模块 00 的 <code>Contract</code> 对象就是为此准备的。"),
    ])),
    ("samefw", "被忽略的一半：同框架内的迁移", "".join([
        P("「迁移」这个词容易让人只想到跨框架，但<strong>同一个框架内的迁移同样频繁，而且用的是完全一样的方法学</strong>。列出来你会发现它几乎是日常工作："),
        TABLE(["场景", "什么变了", "特有的坑"], [
            ["<strong>重构模型代码</strong>", "层的组织方式变了，权重应等价", "参数名变了 → <code>load_state_dict</code> 报 missing/unexpected keys"],
            ["<strong>升级框架版本</strong>", "算子的默认参数或数值实现改了", "<em>不报错但数值微变</em>（如某版本改了 <code>gelu</code> 的默认近似）"],
            ["<strong>换注意力实现</strong>", "eager → SDPA → FlashAttention", "数值不逐位相同（归约顺序不同）；mask 的语义可能不同"],
            ["<strong>合并 LoRA 权重</strong>", "adapter 被合进基座", "缩放系数 α/r 用错 → 效果与不合并时不同（C50 模块 04）"],
            ["<strong>量化 / 反量化</strong>", "权重精度变了", "容差要按量化误差设（模块 03）"],
            ["<strong>切换分布式策略</strong>", "DDP → FSDP → ZeRO-3", "<strong>保存/加载的 state_dict 形状不同</strong>（分片 vs 完整）"],
        ]),
        DUAL(
            "<strong>第一行是最常见的</strong>：你把 <code>self.attn = Attention(...)</code> 改成 <code>self.self_attn = Attention(...)</code>，旧 checkpoint 就加载不上了。PyTorch 的 <code>load_state_dict</code> 默认会报 missing/unexpected keys——<em>这是好事</em>。但很多人的第一反应是加 <code>strict=False</code> 把警告压掉，<strong>而那恰好把「加载失败」变成了「静默地用随机初始化」</strong>。<em>永远不要用 <code>strict=False</code> 来消除警告；要么修好映射，要么显式列出你打算忽略哪些键并解释为什么。</em>",
            "<strong>第六行（分布式策略切换）</strong>是另一个高发区，且症状特别迷惑：FSDP/ZeRO-3 保存的可能是分片的 state_dict，每个 rank 只有一部分；直接拿去单卡加载会得到「形状不匹配」或者更糟——<em>加载成功但每个参数只有 1/N 的内容</em>。<strong>解法是保存时显式做 <code>state_dict_type=FULL_STATE_DICT</code> 的汇总</strong>，并在加载后跑一遍本模块的逐层对拍。<em>这类问题几乎无法靠读代码发现，只能靠数值验证。</em>",
        ),
        CALLOUT("warn", "同框架迁移有一个跨框架迁移没有的<strong>额外风险：它看起来太安全了</strong>。跨框架时你知道要小心，会做对拍；<em>同框架时人们默认「都是 PyTorch，能加载上就是对的」，于是跳过验证</em>。但「能加载上」只证明了形状匹配——<strong>而本模块反复说明的正是「形状匹配什么都证明不了」</strong>（方阵层、门顺序、buffer 漏项，全都能通过形状检查）。<em>所以本模块的 checklist 应该原样用在同框架迁移上，一步都不省。</em>"),
        P("好消息是：<strong>前面建立的所有工具都直接适用</strong>——参数总量检查、覆盖检查、逐层对拍、随机性关闭断言、交付契约。<em>唯一需要调整的是容差</em>：同框架内、同 dtype 时容差可以设得很紧（<code>rtol=1e-6</code>），因为除非实现真的变了，否则应该逐位相同；<strong>而「逐位相同」是一个远比 <code>allclose</code> 强的断言，能力所及时就该用它</strong>。"),
    ])),
    ("ledger", "算一笔账：迁移 vs 重训", "".join([
        MATH("C_{retrain} = \\underbrace{T_{gpu} \\cdot p_{gpu}}_{\\text{算力}} + \\underbrace{H_{debug} \\cdot p_{hour}}_{\\text{调参与复现}}, \\qquad C_{port} = \\underbrace{H_{port} \\cdot p_{hour}}_{\\text{迁移与验证}}"),
        TABLE(["模型规模", "重训算力", "重训调试", "迁移工时", "迁移成本 / 重训成本"], [
            ["小模型（&lt;100M）", "~20 GPU·h = $80", "~16 h = $960", "~8 h = $480", "≈ 0.46"],
            ["中模型（1B）", "~2,000 GPU·h = $8,000", "~40 h = $2,400", "~16 h = $960", "<strong>≈ 0.09</strong>"],
            ["大模型（&gt;10B）", "~50,000 GPU·h = $200,000", "~80 h = $4,800", "~24 h = $1,440", "<strong>≈ 0.007</strong>"],
        ]),
        P("三点观察："),
        UL([
            "<strong>模型越大，迁移越划算</strong>——因为迁移的工时几乎不随模型规模增长（参数多了但映射规则不变），而重训算力线性甚至超线性增长。",
            "<strong>即使是小模型，迁移也更便宜</strong>——因为「重训」的主要成本不是算力而是<em>调试与复现的人力</em>（那 16 小时里大部分花在「为什么我的复现比论文低 2 个点」上）。",
            "<strong>而且迁移的成本方差小得多</strong>：迁移要么成功（数值对上）要么失败（对不上，但你知道在哪一层）；重训可能花两周还差 1 个点，且不知道为什么。",
        ]),
        P("什么时候<strong>应该</strong>重训而不是迁移？三种情况："),
        UL([
            "<strong>结构真的不同</strong>：你要改架构（换注意力、加层、改维度），迁移不了。<em>但即使这时，「迁移能迁的部分 + 只训新增部分」通常也比全量重训好。</em>",
            "<strong>拿不到权重</strong>：只有论文没有 checkpoint。",
            "<strong>需要在新数据上适配</strong>：那本来就是微调而不是迁移。",
        ]),
        CALLOUT("intuition", "把本模块浓缩成一句可迁移的智慧：<strong>迁移的价值不在「省算力」，而在「把一个模糊的性能问题变成一个可二分定位的数值问题」</strong>。这个转变才是关键——它让「效果差 2 个点」这种最难查的 bug，变成「第 7 层的 LayerNorm eps 不对」这种十分钟能修的 bug。<em>凡是能把模糊问题变成可定位问题的做法，都值得优先采用</em>——这条原则在调试、在评测（C03 的分解式评估）、在生产诊断（C48 的分阶段指标）里反复出现。"),
    ])),
    ("frontier", "生态动态与开放问题", "".join([
        UL([
            "<strong>自动化的权重迁移</strong>：HuggingFace 为每个模型手写 <code>convert_*_original_checkpoint_to_pytorch.py</code>，几百行且不可复用。<em>能否从两边的计算图自动推断映射</em>（图同构匹配 + 形状约束 + 数值验证）是个有价值但未解决的问题——难点在于同构匹配的歧义与算子语义的细微差异。",
            "<strong>数值等价的形式化</strong>：目前「等价」靠采样几个输入做 allclose。<em>能否给出「在整个输入域上误差有界」的保证</em>？对纯线性部分可以（矩阵范数），对含非线性与浮点归约的完整网络仍是开放的。这与神经网络验证（NN verification）领域相关。",
            "<strong>中间表示作为统一交换格式</strong>：ONNX 是当前的事实标准（模块 03），但它对训练图、动态控制流、自定义算子的支持一直不完善。StableHLO / MLIR 生态试图提供更通用的答案，尚未收敛。",
            "<strong>多后端框架</strong>：Keras 3 让同一份代码跑在 TF/JAX/PyTorch 后端上，本质是「不迁移，换后端」。它对新项目有效，但抽象泄漏（各后端的 dtype 提升规则、随机数、分布式语义不同）仍然存在。",
            "<strong>训练-推理图的一致性验证</strong>：模型在训练框架里的行为与导出后的行为可能不同（BN 模式、dropout、控制流分支）。<em>缺少自动化工具来验证「导出图与训练图在给定输入分布上数值一致」</em>——这正是本模块要你手写对拍的原因。",
        ]),
        CALLOUT("paper", "必读（都是文档而非论文，因为这是工程问题）：PyTorch 的 <code>nn.Linear</code>/<code>nn.Conv2d</code>/<code>nn.GRU</code> 文档中的 <em>Shape</em> 与 <em>Variables</em> 小节（权重形状与门顺序的权威定义）；Keras 对应层的文档；cuDNN 的 RNN 权重布局说明（PyTorch 的门顺序源自它）。实践参考：HuggingFace <code>transformers</code> 里任意一个 <code>convert_*_to_pytorch.py</code> 脚本——<strong>读一遍真实的迁移脚本，胜过读十篇教程</strong>，尤其看它怎么处理命名映射与逐项断言。相邻课程：C50 模块 01（state_dict 与键名匹配）、C38（框架内部机制）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 02 · 框架迁移与权重对齐（布局转换 / 命名映射 / 逐层数值对拍）

目标：把 **权重布局转换 → 命名映射 → 逐层对拍 → 迁移 checklist** 实现成一套可复用的工具，
并复现三类「不报错但数值错」的经典事故。

路线：reshape vs transpose 的致命区别 → **方阵层让形状检查失效** → RNN 门顺序 →
命名映射的三档做法 + 「漏参数」检测 → 逐层对拍与失配定位表 →
「全 1 输入」快速结构验证 → 迁移 checklist → ✏️ 练习 → 📖 答案 → 🧪 成本账胶囊。

> 心智模型：**迁移的价值不在省算力，而在把「模糊的性能问题」变成「可二分定位的数值问题」。**"""),
    md("""## 0 · 复用模块 00 的对拍工具"""),
    code("""import numpy as np, math, collections, itertools, re
rng = np.random.default_rng(0)

def allclose_report(a, b, rtol=1e-5, atol=1e-6, name=''):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        return {'name': name, 'ok': False, 'reason': f'shape {a.shape} vs {b.shape}',
                'max_abs': float('inf')}
    diff = np.abs(a - b)
    return {'name': name, 'ok': bool(np.allclose(a, b, rtol=rtol, atol=atol)),
            'max_abs': float(diff.max()),
            'max_rel': float((diff / np.maximum(np.abs(b), 1e-12)).max())}

def layerwise_check(ref, new, order, rtol=1e-5, atol=1e-6):
    '''按执行顺序逐层对拍，**在第一个失配处停下** —— 后面的全错只是它的后果。'''
    rows = []
    for k in order:
        r = allclose_report(ref[k], new.get(k, np.array([])), rtol, atol, name=k)
        rows.append(r)
        if not r['ok']:
            break
    return rows
print('✅ 对拍工具就绪')"""),
    md("""## 1 · reshape vs transpose：形状对了不等于内容对了

`reshape` 只是**重新解释同一块连续内存**；`transpose` 才**改变元素排列**。
两者常常得到相同的形状——而代码不会报任何错。"""),
    code("""# Conv2d: PyTorch (out, in, kH, kW)  <->  TF (kH, kW, in, out)
def conv2d_torch_to_tf(w):  return np.transpose(w, (2, 3, 1, 0))
def conv2d_tf_to_torch(w):  return np.transpose(w, (3, 2, 0, 1))
# Linear: PyTorch (out, in)  <->  Keras Dense (in, out)
def linear_torch_to_keras(w): return w.T
def linear_keras_to_torch(w): return w.T

w_conv = rng.normal(size=(16, 3, 5, 5))
right = conv2d_torch_to_tf(w_conv)
wrong = w_conv.reshape(5, 5, 3, 16)
print(f'PyTorch conv {w_conv.shape}')
print(f'  transpose -> {right.shape}   ✅')
print(f'  reshape   -> {wrong.shape}   ❌ 形状一模一样！')
assert right.shape == wrong.shape
assert not np.allclose(right, wrong)
print(f'  两者最大差异 {np.abs(right - wrong).max():.4f}，重合元素比例 '
      f'{np.mean(np.isclose(right, wrong)):.1%}')
# 往返无损（checklist 步骤 ④ 的验收断言）
assert np.allclose(conv2d_tf_to_torch(conv2d_torch_to_tf(w_conv)), w_conv)
print('\\n✅ 往返转换无损 —— 这是布局转换函数的必要（非充分）条件，务必写成断言。')"""),
    md("""### 方阵层：形状检查这道防线彻底失效

Transformer 里 `d_model → d_model` 的方阵极其常见（q/k/v/o 投影）。
**忘了转置时，形状检查会通过、模型会跑、结果全错。**"""),
    code("""def dense_keras(x, W, b):   return x @ W + b          # Keras: (in, out)
def linear_torch(x, W, b):  return x @ W.T + b         # PyTorch: (out, in)，注意 .T

D = 8
W_keras = rng.normal(size=(D, D))                       # (in, out)
b = np.zeros(D)
x = rng.normal(size=(4, D))
ref = dense_keras(x, W_keras, b)

W_torch_right = linear_keras_to_torch(W_keras)          # 正确：转置
W_torch_wrong = W_keras.copy()                          # 错误：直接搬（形状「对」）
out_right = linear_torch(x, W_torch_right, b)
out_wrong = linear_torch(x, W_torch_wrong, b)

print(f'Keras Dense 输出与…')
print(f'  正确迁移(转置):  {allclose_report(out_right, ref)["ok"]}   ✅')
r_wrong = allclose_report(out_wrong, ref)
print(f'  忘了转置:        {r_wrong["ok"]}   ❌ max_abs={r_wrong["max_abs"]:.4f}')
assert W_torch_wrong.shape == W_torch_right.shape, '⚠️ 方阵：形状检查完全无法区分'
assert allclose_report(out_right, ref)['ok'] and not r_wrong['ok']
print('\\n⚠️  **方阵上形状检查这道防线彻底失效** —— 而 Transformer 里方阵到处都是')
print('    （q/k/v/o 投影全是 d_model×d_model）。')
print('✅ 唯一可靠的防线是**数值对拍**，不是形状检查。')

# 非方阵时形状检查还能救你一次
W_rect = rng.normal(size=(D, D * 4))
try:
    linear_torch(x, W_rect, np.zeros(D * 4))            # 忘了转置 -> 形状不匹配
    print('\\n（非方阵忘转置：这里没报错说明广播规则救了你，仍不可依赖）')
except ValueError:
    print('\\n✅ 非方阵忘转置时形状检查会报错 —— 但你不能指望所有层都是非方阵。')"""),
    md("""### RNN 的门顺序：形状对、转置也对，但门功能错位"""),
    code("""# GRU 门顺序：PyTorch [r, z, n]；Keras/TF [z, r, h]  —— **前两个门是反的**
H = 6
IN = 4
def gru_split_torch(W):   # (3H, in) -> r, z, n
    return W[:H], W[H:2*H], W[2*H:]
def gru_split_keras(W):   # (in, 3H) -> z, r, h
    Wt = W.T
    return Wt[:H], Wt[H:2*H], Wt[2*H:]

def gru_keras_to_torch(W_keras):
    '''转置 + **门重排** [z,r,h] -> [r,z,n]'''
    z, r, h = gru_split_keras(W_keras)
    return np.concatenate([r, z, h], axis=0)

W_keras_gru = rng.normal(size=(IN, 3 * H))
W_torch_right = gru_keras_to_torch(W_keras_gru)
W_torch_only_transpose = W_keras_gru.T                  # 只转置、没重排

print(f'Keras GRU kernel {W_keras_gru.shape} -> PyTorch {W_torch_right.shape}')
assert W_torch_right.shape == W_torch_only_transpose.shape, '⚠️ 形状完全一样'
assert not np.allclose(W_torch_right, W_torch_only_transpose)
z, r, h = gru_split_keras(W_keras_gru)
r2, z2, n2 = gru_split_torch(W_torch_right)
assert np.allclose(r2, r) and np.allclose(z2, z) and np.allclose(n2, h)
r3, z3, _ = gru_split_torch(W_torch_only_transpose)
assert np.allclose(r3, z), '只转置的话，PyTorch 的 reset 门拿到的是 Keras 的 update 门！'
print('\\n⚠️  只转置不重排：PyTorch 的 **reset 门**拿到了 Keras 的 **update 门**权重。')
print('    形状对、转置也对，但门功能错位 —— 而且模型仍能跑、loss 仍能降')
print('    （门是对称可学的），只有用**预训练权重**时才会暴露。')
print('✅ LSTM 同理：PyTorch [i,f,g,o]，cuDNN/TF 的某些实现是 [i,f,o,g] 或 [i,g,f,o]。')"""),
    md("""## 2 · 命名映射与「漏参数」检测

**漏掉的参数比映射错的参数更危险**：映射错会有明显异常，
漏掉（如 BatchNorm 的 `running_var`）会让它保持随机初始化——训练模式下正常，**一到 eval 就崩**。"""),
    code("""# 两边的参数清单（含 buffer —— 极易被漏）
TF_PARAMS = {
    'embeddings/word_embeddings':        (100, 8),
    'encoder/layer_0/attention/query/kernel': (8, 8),
    'encoder/layer_0/attention/query/bias':   (8,),
    'encoder/layer_0/ln/gamma':          (8,),
    'encoder/layer_0/ln/beta':           (8,),
    'encoder/layer_0/bn/gamma':          (8,),
    'encoder/layer_0/bn/beta':           (8,),
    'encoder/layer_0/bn/moving_mean':    (8,),
    'encoder/layer_0/bn/moving_variance': (8,),
    'classifier/kernel':                 (8, 3),
    'classifier/bias':                   (3,),
}
TORCH_PARAMS = {
    'embeddings.word_embeddings.weight': (100, 8),
    'encoder.layer.0.attention.query.weight': (8, 8),
    'encoder.layer.0.attention.query.bias':   (8,),
    'encoder.layer.0.ln.weight':         (8,),
    'encoder.layer.0.ln.bias':           (8,),
    'encoder.layer.0.bn.weight':         (8,),
    'encoder.layer.0.bn.bias':           (8,),
    'encoder.layer.0.bn.running_mean':   (8,),     # ← buffer，遍历 parameters() 时看不到！
    'encoder.layer.0.bn.running_var':    (8,),     # ← 同上
    'classifier.weight':                 (3, 8),   # ← 注意转置
    'classifier.bias':                   (3,),
}

RULES = [
    (r'^embeddings/word_embeddings$', 'embeddings.word_embeddings.weight'),
    (r'/kernel$', '.weight'), (r'/bias$', '.bias'),
    (r'/gamma$', '.weight'), (r'/beta$', '.bias'),
    (r'/moving_mean$', '.running_mean'), (r'/moving_variance$', '.running_var'),
    (r'^encoder/layer_(\\d+)/', r'encoder.layer.\\1.'),
]

def rule_map(tf_name):
    n = tf_name
    for pat, rep in RULES:
        n = re.sub(pat, rep, n)
    return n.replace('/', '.')

def build_mapping(src_names):
    mapping, unmatched = {}, []
    for tf_n in src_names:
        cand = rule_map(tf_n)
        if cand in TORCH_PARAMS:
            mapping[tf_n] = cand
        else:
            unmatched.append((tf_n, cand))
    return mapping, unmatched

# ⚠️ 第一次尝试：源侧只列了 **trainable_variables**（这是最自然的写法，也是那个坑）
TF_TRAINABLE = {k: v for k, v in TF_PARAMS.items() if 'moving_' not in k}
mapping_v1, unmatched_v1 = build_mapping(TF_TRAINABLE)
print(f'第一次尝试（源侧用 trainable_variables）: 覆盖 {len(mapping_v1)}/{len(TF_TRAINABLE)}')
for tf_n, cand in unmatched_v1:
    print(f'  ❌ {tf_n}  ->  {cand}  (目标侧不存在)')
assert not unmatched_v1, '规则本身没问题 —— 每一条都映射成功了'
print('✅ 规则映射本身「全部成功」—— 这正是危险的地方：**源侧漏了两个 buffer，'
      '而映射过程没有任何迹象**。')"""),
    code("""def check_coverage(mapping, target_params):
    '''**checklist 步骤 ③ 的验收断言：目标侧每个参数与 buffer 都被赋值过。**'''
    assigned = set(mapping.values())
    missing = sorted(set(target_params) - assigned)
    extra = sorted(assigned - set(target_params))
    return {'missing': missing, 'extra': extra, 'ok': not missing and not extra}

cov = check_coverage(mapping_v1, TORCH_PARAMS)
print('从**目标侧**做覆盖检查（这是唯一能抓到漏项的方向）:')
for k in ('missing', 'extra'):
    print(f'  {k}: {cov[k]}')
assert not cov['ok'], '第一次尝试应该被抓出漏项'
assert cov['missing'] == ['encoder.layer.0.bn.running_mean',
                          'encoder.layer.0.bn.running_var'], cov['missing']
print(f'\\n⚠️  未覆盖的 {len(cov["missing"])} 个参数会保持**随机初始化**，而它们恰好是 buffer：')
print('    训练模式下 BatchNorm 用 batch 统计，看不出任何问题；')
print('    **一切到 eval 模式就崩** —— 这是最难定位的一类迁移 bug。')

# ✅ 修正：源侧改用「全部变量 + buffer」
mapping, unmatched = build_mapping(TF_PARAMS)
cov2 = check_coverage(mapping, TORCH_PARAMS)
print(f'\\n改用全部变量（含 moving_mean/variance）后: '
      f'missing={cov2["missing"]}, extra={cov2["extra"]}, ok={cov2["ok"]}')
assert cov2['ok'] and not unmatched, '补齐后应完全覆盖'
print('✅ **覆盖检查必须从目标侧做** —— 从源侧遍历永远发现不了「源侧本身漏了」。')
print('✅ **先确认覆盖，再谈数值** —— 这个顺序能省掉大量返工。')"""),
    code("""# 最便宜的结构性检查：参数总元素数
def total_numel(params):
    return sum(int(np.prod(s)) for s in params.values())

n_tf, n_torch = total_numel(TF_PARAMS), total_numel(TORCH_PARAMS)
print(f'TF 参数总元素数    {n_tf}')
print(f'PyTorch 参数总元素数 {n_torch}')
assert n_tf == n_torch, '总量不等 = 结构本身不同（少层/多 bias/嵌入没 tie）'
print('✅ 总量相等 -> 结构一致，可以进入逐个映射。')
print('   （**总量不等时任何映射工作都是白费** —— 先解决结构差异。）')

# 反例：目标模型少了一个 bias
TORCH_MISSING_BIAS = {k: v for k, v in TORCH_PARAMS.items() if k != 'classifier.bias'}
print(f'\\n若目标少一个 bias: {total_numel(TORCH_MISSING_BIAS)} vs {n_tf} '
      f'-> 差 {n_tf - total_numel(TORCH_MISSING_BIAS)} 个元素')
assert total_numel(TORCH_MISSING_BIAS) != n_tf"""),
    md("""## 3 · 逐层对拍：把「效果不对」变成「第 N 层不对」"""),
    code("""def layernorm(x, g, b, eps):
    mu, var = x.mean(-1, keepdims=True), x.var(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * g + b

def gelu(x):
    return 0.5 * x * (1 + np.tanh(math.sqrt(2/math.pi) * (x + 0.044715 * x**3)))

class RefModel:
    '''参考实现（当作「原框架」）。'''
    def __init__(self, seed=0, eps=1e-5):
        r = np.random.default_rng(seed)
        self.W1 = r.normal(size=(8, 16)) * 0.3
        self.W2 = r.normal(size=(16, 8)) * 0.3
        self.g, self.b = np.ones(8), np.zeros(8)
        self.eps = eps
    def forward(self, x):
        acts = {'input': x}
        acts['fc1'] = x @ self.W1
        acts['act'] = gelu(acts['fc1'])
        acts['fc2'] = acts['act'] @ self.W2
        acts['ln'] = layernorm(acts['fc2'], self.g, self.b, self.eps)
        return acts

ORDER = ['input', 'fc1', 'act', 'fc2', 'ln']

def ported_model(x, W1, W2, g, b, eps, transpose_w1=False, wrong_act=False):
    '''迁移后的实现（可注入几种典型错误）。'''
    acts = {'input': x}
    acts['fc1'] = x @ (W1.T if transpose_w1 else W1)
    acts['act'] = (np.maximum(acts['fc1'], 0) if wrong_act else gelu(acts['fc1']))
    acts['fc2'] = acts['act'] @ W2
    acts['ln'] = layernorm(acts['fc2'], g, b, eps)
    return acts

ref = RefModel()
x = rng.normal(size=(4, 8))
acts_ref = ref.forward(x)

cases = [
    ('完全正确', dict()),
    ('eps 用了 keras 默认 1e-3', dict(eps=1e-3)),
    ('激活函数搞成 ReLU', dict(wrong_act=True)),
]
for name, kw in cases:
    eps = kw.pop('eps', ref.eps)
    acts_new = ported_model(x, ref.W1, ref.W2, ref.g, ref.b, eps, **kw)
    rows = layerwise_check(acts_ref, acts_new, ORDER)
    bad = [r for r in rows if not r['ok']]
    if bad:
        print(f'{name:<26s} ❌ 首个失配层 **{bad[0]["name"]}**  max_abs={bad[0]["max_abs"]:.3e}')
    else:
        print(f'{name:<26s} ✅ 全部 {len(rows)} 层通过')

r_eps = layerwise_check(acts_ref, ported_model(x, ref.W1, ref.W2, ref.g, ref.b, 1e-3), ORDER)
assert [r for r in r_eps if not r['ok']][0]['name'] == 'ln', 'eps 错 -> 只有 ln 层失配'
r_act = layerwise_check(acts_ref,
                        ported_model(x, ref.W1, ref.W2, ref.g, ref.b, ref.eps, wrong_act=True),
                        ORDER)
assert [r for r in r_act if not r['ok']][0]['name'] == 'act', '激活错 -> act 层就失配'
print('\\n✅ **第一个失配的层直接指向问题** —— eps 错就只有 ln 层错、激活错就 act 层错。')
print('   这就是「把模糊的性能问题变成可二分定位的数值问题」。')"""),
    md("""### 失配现象 → 原因的查表"""),
    code("""DIAGNOSIS = {
    'input': '输入预处理不同（归一化/通道序/分词器/特殊 token）—— **先对拍输入张量本身**',
    'fc1':   '第一个线性层：权重没转置，或 bias 缺失',
    'act':   '激活函数变体不同（gelu 的 tanh 近似 vs 精确 erf；relu vs gelu）',
    'fc2':   '第二个线性层：同 fc1；或前一层的输出被就地修改了',
    'ln':    '归一化：eps 不同 / gamma-beta 映射反了 / BN 用了 batch 统计（忘了 eval）',
}
def diagnose(rows):
    bad = [r for r in rows if not r['ok']]
    if not bad: return '✅ 全部通过'
    n = bad[0]['name']
    return f'首个失配: {n}\\n  最可能原因: {DIAGNOSIS.get(n, "未知层")}'

print(diagnose(r_eps)); print()
print(diagnose(r_act)); print()
print(diagnose(layerwise_check(acts_ref, acts_ref, ORDER)))
assert 'eps' in diagnose(r_eps)
print('\\n✅ 把「首个失配层 -> 最可能原因」做成查表，比重读两边代码快一个数量级。')"""),
    md("""### 「全 1 输入 + 全 1 权重」：五分钟抓出所有布局错误

全 1 下任何布局错误都会表现为**数量级差异**（求和项数不同），而且结果可以**手算**。"""),
    code("""def ones_probe(shape_in, W_shape, layout='torch'):
    '''全 1 探针：结果应精确等于「输入维度数」。'''
    x = np.ones((1, shape_in))
    W = np.ones(W_shape)
    return (x @ W.T) if layout == 'torch' else (x @ W)

# 正确：PyTorch (out, in)=(4,8)，输出每个元素应为 8
out_ok = ones_probe(8, (4, 8), 'torch')
print('PyTorch 布局 (out=4, in=8) 全 1 探针:', out_ok.ravel(), '（应全为 8 = 输入维度）')
assert np.allclose(out_ok, 8.0)

# 错误：把 Keras 的 (in, out)=(8,4) 当成 torch 的 (out, in) 用
try:
    bad = ones_probe(8, (8, 4), 'torch')
    print('Keras 布局误当 torch:', bad.ravel(), '  ← 值变成 4 了（= 错误的维度）')
    assert np.allclose(bad, 4.0), '数值直接暴露维度用错了'
    print('✅ **数量级/数值直接暴露布局错误**，而且结果可手算。')
except ValueError as e:
    print('形状不匹配报错:', e)

# 方阵时全 1 探针也救不了（两边都是 D）—— 所以还需要「阶梯输入」
D = 8
W_sq = np.arange(D * D, dtype=float).reshape(D, D)
x_ramp = np.arange(1, D + 1, dtype=float)[None, :]        # 阶梯输入打破对称性
a = x_ramp @ W_sq.T
b = x_ramp @ W_sq
print(f'\\n方阵 + 全 1 输入: 两种布局结果相同? '
      f'{np.allclose(np.ones((1,D)) @ W_sq.T, np.ones((1,D)) @ W_sq)}')
print(f'方阵 + 阶梯输入: 两种布局结果相同? {np.allclose(a, b)}  ← 被区分开了 ✅')
assert not np.allclose(a, b)
print('\\n✅ 两步探针：**全 1 抓维度错误、阶梯输入抓转置错误**。')
print('   五分钟跑完，能排除掉所有布局类问题，剩下的才是真正的数值细节。')"""),
    md("""## 4 · 「关掉一切随机性」的验收断言"""),
    code("""class ModelWithDropout:
    def __init__(self, p=0.1, seed=0):
        self.p, self.training = p, True
        self.r = np.random.default_rng(seed)
        self.W = np.random.default_rng(1).normal(size=(8, 8)) * 0.3
    def forward(self, x):
        h = x @ self.W
        if self.training and self.p > 0:
            mask = (self.r.random(h.shape) > self.p) / (1 - self.p)
            h = h * mask
        return h

m = ModelWithDropout()
x_dp = rng.normal(size=(4, 8))
print('training=True:  两次前向相同?', np.allclose(m.forward(x_dp), m.forward(x_dp)))
m.training = False
same = np.allclose(m.forward(x_dp), m.forward(x_dp))
print('training=False: 两次前向相同?', same)
assert not np.allclose(ModelWithDropout().forward(x_dp),
                       ModelWithDropout(seed=9).forward(x_dp))
assert same, 'eval 模式下必须完全确定'
print('\\n✅ **验收断言：连续两次前向结果完全相同。**')
print('   它能一次性抓出所有未关闭的随机性 —— dropout 没关、BN 还在用 batch 统计、')
print('   数据增强还开着、自定义层里藏了随机数。')
print('   否则后面的对拍会出现「时对时不对」的诡异现象，极难定位。')"""),
    md("""## 5 · 迁移 checklist 的可执行版本"""),
    code("""def migration_report(src_params, dst_params, mapping, acts_ref, acts_new, order,
                     rtol=1e-5, atol=1e-6):
    '''把 8 步 checklist 里可自动化的部分做成一份报告。'''
    rep = {}
    rep['① 参数总量'] = {'src': total_numel(src_params), 'dst': total_numel(dst_params),
                        'ok': total_numel(src_params) == total_numel(dst_params)}
    cov = check_coverage(mapping, dst_params)
    rep['② 映射覆盖'] = {'missing': cov['missing'], 'extra': cov['extra'], 'ok': cov['ok']}
    rows = layerwise_check(acts_ref, acts_new, order, rtol, atol)
    bad = [r for r in rows if not r['ok']]
    rep['③ 逐层对拍'] = {'checked': len(rows), 'first_mismatch': bad[0]['name'] if bad else None,
                        'max_abs': bad[0]['max_abs'] if bad else
                                   max(r['max_abs'] for r in rows),
                        'ok': not bad}
    rep['总体'] = all(v['ok'] for k, v in rep.items() if k != '总体')
    return rep

acts_new_ok = ported_model(x, ref.W1, ref.W2, ref.g, ref.b, ref.eps)
rep_ok = migration_report(TF_PARAMS, TORCH_PARAMS, mapping, acts_ref, acts_new_ok, ORDER)
acts_new_bad = ported_model(x, ref.W1, ref.W2, ref.g, ref.b, 1e-3)
rep_bad = migration_report(TF_PARAMS, TORCH_PARAMS, mapping, acts_ref, acts_new_bad, ORDER)

for name, rep in [('正确迁移', rep_ok), ('eps 用错', rep_bad)]:
    print(f'=== {name} ===')
    for k, v in rep.items():
        print(f'  {k}: {v}')
    print()
assert rep_ok['总体'] and not rep_bad['总体']
assert rep_bad['③ 逐层对拍']['first_mismatch'] == 'ln'
print('✅ 一份报告同时回答：结构对不对、映射全不全、数值哪一层开始错。')"""),
    md("""## ✏️ 练习 1：布局转换器

实现 `convert_weight(w, layer_type, direction)`：
`layer_type ∈ {'linear','conv2d','conv1d'}`，`direction ∈ {'torch2tf','tf2torch'}`。
要求**往返无损**。未知类型抛 `ValueError`。"""),
    code("""def convert_weight(w, layer_type, direction):
    # TODO: linear -> .T; conv2d torch2tf -> transpose(2,3,1,0)，tf2torch -> (3,2,0,1)
    #       conv1d torch2tf -> transpose(2,1,0)，tf2torch -> (2,1,0)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
for lt, shape in [('linear', (16, 8)), ('conv2d', (16, 3, 5, 5)), ('conv1d', (16, 3, 7))]:
    w = rng.normal(size=shape)
    tf_w = convert_weight(w, lt, 'torch2tf')
    back = convert_weight(tf_w, lt, 'tf2torch')
    assert np.allclose(back, w), f'{lt} 往返必须无损'
    print(f'{lt:<8s} torch {shape} -> tf {tf_w.shape} -> torch {back.shape}  ✅')
assert convert_weight(rng.normal(size=(16, 3, 5, 5)), 'conv2d', 'torch2tf').shape == (5, 5, 3, 16)
try:
    convert_weight(np.ones((2, 2)), 'mystery', 'torch2tf'); raise RuntimeError('不该到这')
except ValueError:
    print('未知层类型正确报错 ✅')
print('✅ 练习 1 通过：**往返无损**是布局转换函数的必要断言，务必写进单测')"""),
    md("""## ✏️ 练习 2：门重排

实现 `reorder_gates(W, from_order, to_order, n_gates, hidden)`：
`W` 形状 `(n_gates*hidden, in)`，按 `from_order`（如 `'zrh'`）切成若干块，
按 `to_order`（如 `'rzn'`）重新拼接。**注意 `'h'` 与 `'n'` 指同一个门**（新候选状态）。"""),
    code("""GATE_ALIAS = {'h': 'n'}      # keras 的 h 门 == torch 的 n 门

def reorder_gates(W, from_order, to_order, n_gates, hidden):
    # TODO: 按 from_order 切块存进 dict（用 GATE_ALIAS 归一化门名），
    #       再按 to_order 取出拼接
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
H_, IN_ = 6, 4
W_keras_t = rng.normal(size=(3 * H_, IN_))          # 已转置的 keras kernel，顺序 z,r,h
W_torch = reorder_gates(W_keras_t, 'zrh', 'rzn', 3, H_)
assert W_torch.shape == W_keras_t.shape
z, r, h = W_keras_t[:H_], W_keras_t[H_:2*H_], W_keras_t[2*H_:]
r2, z2, n2 = W_torch[:H_], W_torch[H_:2*H_], W_torch[2*H_:]
assert np.allclose(r2, r) and np.allclose(z2, z) and np.allclose(n2, h)
# 往返
assert np.allclose(reorder_gates(W_torch, 'rzn', 'zrh', 3, H_), W_keras_t)
# LSTM 四门
W_lstm = rng.normal(size=(4 * H_, IN_))
out = reorder_gates(W_lstm, 'ifgo', 'ifog', 4, H_)
assert np.allclose(out[2*H_:3*H_], W_lstm[3*H_:4*H_]), 'o 门应被移到第 3 位'
print('GRU zrh -> rzn ✅   LSTM ifgo -> ifog ✅   往返无损 ✅')
print('✅ 练习 2 通过：门顺序错了模型仍能跑、loss 仍能降 —— 只有用预训练权重才暴露')"""),
    md("""## ✏️ 练习 3：迁移前的结构性检查

实现 `structural_check(src, dst, mapping)`：返回
`{'numel_match':…, 'coverage_ok':…, 'shape_conflicts': [...], 'ok':…}`。
`shape_conflicts` 列出「映射到一起但元素数不同」的键对（元素数相同但形状不同是允许的——那是布局差异）。"""),
    code("""def structural_check(src, dst, mapping):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
res = structural_check(TF_PARAMS, TORCH_PARAMS, mapping)
print({k: v for k, v in res.items() if k != 'shape_conflicts'})
print('shape_conflicts:', res['shape_conflicts'])
assert res['numel_match'] and res['coverage_ok']
assert res['shape_conflicts'] == [], '(8,8)->(8,8) 与 (8,3)->(3,8) 元素数都相同，属布局差异'
# 制造一个真正的冲突
bad_dst = dict(TORCH_PARAMS); bad_dst['classifier.weight'] = (3, 16)
res_bad = structural_check(TF_PARAMS, bad_dst, mapping)
assert res_bad['shape_conflicts'], '元素数不同必须被报出来'
assert not res_bad['ok']
print(f'\\n注入冲突后: {res_bad["shape_conflicts"]}')
print('✅ 练习 3 通过：**元素数不同 = 结构错**；元素数相同形状不同 = 布局差异（可转换）')"""),
    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def convert_weight(w, layer_type, direction):
    if layer_type == 'linear':
        return w.T
    if layer_type == 'conv2d':
        return np.transpose(w, (2, 3, 1, 0) if direction == 'torch2tf' else (3, 2, 0, 1))
    if layer_type == 'conv1d':
        return np.transpose(w, (2, 1, 0))          # 自逆
    raise ValueError(f'unknown layer_type {layer_type!r}')"""),
    code("""# 练习 2 参考答案
def reorder_gates(W, from_order, to_order, n_gates, hidden):
    assert len(from_order) == len(to_order) == n_gates
    blocks = {}
    for i, g in enumerate(from_order):
        blocks[GATE_ALIAS.get(g, g)] = W[i * hidden:(i + 1) * hidden]
    return np.concatenate([blocks[GATE_ALIAS.get(g, g)] for g in to_order], axis=0)"""),
    code("""# 练习 3 参考答案
def structural_check(src, dst, mapping):
    numel_match = total_numel(src) == total_numel(dst)
    cov = check_coverage(mapping, dst)
    conflicts = []
    for s_name, d_name in mapping.items():
        if d_name not in dst: continue
        if int(np.prod(src[s_name])) != int(np.prod(dst[d_name])):
            conflicts.append((s_name, src[s_name], d_name, dst[d_name]))
    return {'numel_match': numel_match, 'coverage_ok': cov['ok'],
            'shape_conflicts': conflicts,
            'ok': numel_match and cov['ok'] and not conflicts}"""),
    md("""---
## 🧪 真实数据胶囊：迁移 vs 重训的成本账"""),
    code("""GPU_USD_H, HOUR_USD = 4.0, 60.0

def cost_retrain(gpu_hours, debug_hours):
    return gpu_hours * GPU_USD_H + debug_hours * HOUR_USD

def cost_port(port_hours):
    return port_hours * HOUR_USD

SCEN = [
    ('小模型 (<100M)',   20,      16,  8),
    ('中模型 (1B)',      2_000,   40,  16),
    ('大模型 (>10B)',    50_000,  80,  24),
]
print(f"{'规模':<18s} {'重训算力$':>11s} {'重训调试$':>11s} {'重训合计$':>11s} "
      f"{'迁移$':>8s} {'比值':>7s}")
ratios = []
for name, gh, dh, ph in SCEN:
    cr, cp = cost_retrain(gh, dh), cost_port(ph)
    ratios.append(cp / cr)
    print(f'{name:<18s} {gh*GPU_USD_H:>11,.0f} {dh*HOUR_USD:>11,.0f} {cr:>11,.0f} '
          f'{cp:>8,.0f} {cp/cr:>7.3f}')

assert all(r < 1 for r in ratios), '所有规模下迁移都更便宜'
assert ratios[-1] < ratios[0] / 10, '模型越大，迁移越划算'
print(f'\\n✅ 小模型迁移成本是重训的 {ratios[0]:.0%}，大模型只有 {ratios[-1]:.1%}。')
print('   注意小模型时**重训的主要成本不是算力而是调试人力** ——')
print('   那 16 小时里大部分花在「为什么我的复现比论文低 2 个点」上。')
print('\\n更重要的是**方差**：迁移要么成功（数值对上）要么失败（但你知道在哪一层）；')
print('   重训可能花两周还差 1 个点，且不知道为什么。')"""),
    md("""**🧪 胶囊练习**：实现 `porting_decision(can_get_weights, structure_same, need_new_data, retrain_cost, port_cost)`：
返回 `('port' | 'retrain' | 'partial_port', 理由)`。
规则：拿不到权重 → retrain；结构不同但能拿到权重 → partial_port（迁能迁的、只训新增）；
需要在新数据上适配 → retrain（那本来就是微调）；否则比成本。"""),
    code("""def porting_decision(can_get_weights, structure_same, need_new_data,
                     retrain_cost, port_cost):
    # TODO
    raise NotImplementedError"""),
    code("""# 自测
assert porting_decision(False, True, False, 1000, 100)[0] == 'retrain'
assert porting_decision(True, False, False, 1000, 100)[0] == 'partial_port'
assert porting_decision(True, True, True, 1000, 100)[0] == 'retrain'
d, why = porting_decision(True, True, False, 1000, 100)
assert d == 'port'
print(f'能拿权重 + 结构相同 + 不需新数据 -> {d}: {why}')
for args in [(False, True, False), (True, False, False), (True, True, True), (True, True, False)]:
    dd, ww = porting_decision(*args, 1000, 100)
    print(f'  {str(args):<24s} -> {dd:<14s} {ww}')
print('\\n✅ 胶囊练习通过：**「结构不同」不等于「只能重训」** ——')
print('   迁移能迁的部分、只训新增部分，几乎总是优于全量重训。')"""),
    code("""# 📖 胶囊参考答案
def porting_decision(can_get_weights, structure_same, need_new_data,
                     retrain_cost, port_cost):
    if not can_get_weights:
        return 'retrain', '拿不到权重，只能重训'
    if need_new_data:
        return 'retrain', '需要在新数据上适配 —— 那本来就是微调而非迁移'
    if not structure_same:
        return 'partial_port', '结构不同：迁移能迁的部分 + 只训新增部分'
    return ('port', f'成本 {port_cost} < {retrain_cost}，且可逐层验证') \\
        if port_cost < retrain_cost else ('retrain', '迁移反而更贵（罕见）')"""),
    md("""### 小结
- **迁移几乎总是优于重训**，尤其模型大时（成本比可低到 0.7%）；而且小模型时**重训的主要成本是调试人力不是算力**。
- **真正的价值是把模糊问题变成可定位问题**：「效果差 2 个点」→「第 7 层的 eps 不对」。
- **`reshape` 不能替代 `transpose`**：形状会一样、内容完全不同、代码不报错。
- **方阵层让形状检查彻底失效**（Transformer 里 q/k/v/o 全是方阵）——唯一可靠的防线是数值对拍。
- **RNN 要转置 + 门重排**：PyTorch GRU 是 `[r,z,n]`、Keras 是 `[z,r,h]`（前两个门反的）。错了模型仍能跑、loss 仍能降，只有用预训练权重才暴露。
- **漏参数比映射错更危险**：BN 的 `running_mean/var` 是 buffer，遍历 parameters() 看不到；漏了在训练模式正常、**一到 eval 就崩**。
- **验证顺序**：参数总量 → 映射覆盖 → 布局往返无损 → 关随机性（连续两次前向相同）→ 逐层对拍（第一个失配处停）→ 端到端 + 写进交付契约。
- **两步探针**：全 1 输入抓维度错误、阶梯输入抓转置错误。五分钟排除所有布局类问题。

下一站：**模块 03 · 模型导出与推理运行时** —— 交给一个不认识 Python 的运行时。"""),
]
