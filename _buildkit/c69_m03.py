# -*- coding: utf-8 -*-
"""C69 模块 03 · 沙箱与权限边界。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过本课模块 02（工具与供应链）；"
                 "知道「容器」「文件系统权限」的基本概念即可"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 03_sandbox_permissions.ipynb'
                       '（能力模型与最小权限的求解 / 隔离层级的成本-强度矩阵 / '
                       '确认疲劳的模拟：确认率与它的衰减 / TOCTOU 与确认内容不一致 / '
                       '审计日志的完整性与 provenance 链 / 权限变更的影响面分析）'),
    ("核心参考", "Saltzer &amp; Schroeder, <em>The Protection of Information in Computer Systems</em>"
                 "（1975，最小权限等八条设计原则）· "
                 "POSIX capabilities / seccomp / Linux namespaces 的隔离模型 · "
                 "gVisor、Firecracker、WebAssembly 沙箱的隔离强度对比 · "
                 "OAuth 2.0 的 scope 与 token 交换（下游最小权限）· "
                 "本课程 C34 模块 03（权限实现）· C68 模块 04（告警疲劳，与确认疲劳同构）"),
    ("预计时长", "读 60 分钟 + 跑 55 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("least-privilege", "最小权限：从口号到可计算的量", "".join([
        P("「最小权限」这四个字几乎没人反对，但它在 agent 系统里通常停留在口号阶段——"
          "<strong>因为没人算过「最小」到底是多少。</strong>这一节把它变成一个可解的问题。"),
        MATH(r"\text{minimal}(T) = \bigcup_{s \in \text{steps}(T)} \text{required}(s)"),
        P("对一个任务 $T$，最小权限集是<strong>它的每一步实际需要的能力的并集</strong>——"
          "而不是「这个 agent 可能会做的所有事」。"
          "<em>这两者的差距通常大到令人惊讶</em>，因为后者是按「以后可能有用」累积出来的。"),
        TABLE(["权限授予方式", "怎么决定给什么", "典型规模", "问题"], [
            ["<strong>按角色</strong>", "「这是一个编码 agent，给它编码需要的全部权限」", "很大", "<strong>角色是按人设计的，而 agent 的任务粒度比人细得多</strong>"],
            ["<strong>按会话</strong>", "会话开始时根据任务类型授予", "中", "同一会话内不同步骤的需求不同，仍然过宽"],
            ["<strong>按步骤（即时授权）</strong>", "每次工具调用时按当前意图授予", "<strong>最小</strong>", "实现复杂；需要「当前意图」这个概念"],
            ["<strong>按数据范围</strong>", "不只限制「能不能读文件」，还限制「能读哪些文件」", "—", "<strong>常被完全忽略的一维</strong>"],
        ]),
        CALLOUT("intuition", "第四行是本节最容易被忽略、也最有效的一条："
                             "<strong>权限有两个维度——<em>能做什么操作</em> 与 <em>能作用于哪些对象</em>。</strong>"
                             "<em>大多数系统只做了第一维（「有 read_file 能力」），"
                             "而第二维（「只能读 ./workspace/ 下的文件」）同样重要，而且实现成本很低</em>。"
                             "<strong>把「读文件」收窄成「读工作目录下的文件」，"
                             "就把「读 ~/.ssh/」这条路径变成了不可达</strong>——又是一个不变量。"),
        H3("Saltzer & Schroeder 的八条原则，哪几条在 agent 里最相关"),
        UL([
            "<strong>最小权限</strong>（least privilege）——本节主题；",
            "<strong>失败时默认拒绝</strong>（fail-safe defaults）——"
            "<em>权限检查出错时应当拒绝，而不是放行</em>。听起来显然，但"
            "「配置文件里没写这个工具的权限」这种情况的默认行为经常是「不检查」；",
            "<strong>完全仲裁</strong>（complete mediation）——"
            "<strong>每一次访问都要检查，不能缓存授权决定</strong>。"
            "<em>agent 里的典型违反是：第一次调用时检查了，同一会话后续调用直接放行</em>；",
            "<strong>机制经济性</strong>（economy of mechanism）——"
            "<em>权限系统本身要足够简单以便能被验证</em>。"
            "一个有二十个特例的权限系统，它自己就是漏洞的来源；",
            "<strong>心理可接受性</strong>（psychological acceptability）——"
            "<strong>这条在 agent 里格外重要</strong>：如果确认弹得太频繁，"
            "人就会盲目点确认（第 4 节的确认疲劳）。",
        ]),
    ])),

    # ============================================================== 2
    ("capability-model", "能力模型：四个维度而不是一个布尔值", "".join([
        P("要把最小权限算出来，先要有一个足够细的能力表示。"
          "<strong>「有 / 没有某个工具」是不够的</strong>——它至少需要四个维度。"),
        TABLE(["维度", "含义", "例子", "不做这一维的后果"], [
            ["<strong>操作</strong>", "能做什么", "read / write / execute / send", "—（这一维大家都有）"],
            ["<strong>范围</strong>", "能作用于哪些对象", "<code>./workspace/**</code>、<code>*.example.test</code>、<code>只读自己的邮件</code>", "「读文件」= 能读 <code>~/.ssh/</code>"],
            ["<strong>信任门槛</strong>", "触发它需要的最低上下文信任等级", "L2 才能 send_email", "<strong>L0 内容可以直接触发动作</strong>（模块 00/01）"],
            ["<strong>可逆性</strong>", "做错了能不能撤回", "read 可逆 / send_email 不可逆", "不可逆操作与可逆操作被同等对待"],
        ]),
        MATH(r"\text{allow}(a) \iff \underbrace{a.\text{op} \in G}_{\text{授予}} \;\wedge\; \underbrace{a.\text{target} \in S}_{\text{范围}} \;\wedge\; \underbrace{\text{trust}(\text{ctx}) \ge \tau_a}_{\text{信任}} \;\wedge\; \underbrace{(\text{rev}(a) \vee \text{confirmed})}_{\text{可逆性}}"),
        DUAL(
            "这个式子的实用价值在于：<strong>四个条件是<em>合取</em>的，"
            "所以只要有一条不满足，动作就不可达。</strong>"
            "<em>这意味着你有四个独立的收紧点</em>——"
            "而收紧任何一个都不需要依赖其他三个的正确性。"
            "<strong>这正是纵深防御在权限层的具体形态。</strong>",
            "更精确地说，这是一个<span class=\"term\">能力安全</span>（capability-based security）模型"
            "与<span class=\"term\">信息流控制</span>的合成："
            "前两个条件是经典的 capability（持有即可用），"
            "第三个条件把<em>信息流的完整性标签</em>引入了授权判断，"
            "第四个条件引入了<em>可撤销性</em>这个时间维度。"
            "<em>三者合起来才能表达「L0 上下文下不许做不可逆的对外操作」这条规则</em>——"
            "<strong>而这条规则用任何单一模型都表达不出来。</strong>",
        ),
        CALLOUT("warn", "关于「范围」这一维有一个非常常见的实现错误："
                        "<strong>用字符串前缀匹配做路径范围检查。</strong>"
                        "<em><code>path.startswith('./workspace/')</code> 会被 "
                        "<code>./workspace/../../.ssh/id_rsa</code> 绕过</em>——"
                        "<strong>必须先规范化路径（解析 <code>..</code> 与符号链接）再比较，"
                        "而且要比较的是规范化之后的绝对路径。</strong>"
                        "notebook 第 2 节会把这个绕过与修法都跑出来。"),
    ])),

    # ============================================================== 3
    ("isolation", "隔离层级：五档，以及各自的成本与强度", "".join([
        P("权限检查决定「允不允许」，隔离决定「即使它做了，能影响到什么」。"
          "两者是互补的：<strong>权限是白名单，隔离是爆炸半径。</strong>"),
        ASCII("""
   强度 ↑                                                   成本 ↑
   ┌──────────────────────────────────────────────────────────────┐
   │ ⑤ 独立机器 / 独立账号     强隔离，网络与身份都分开             │
   ├──────────────────────────────────────────────────────────────┤
   │ ④ 微 VM（Firecracker 等）  内核级隔离，启动百毫秒级            │
   ├──────────────────────────────────────────────────────────────┤
   │ ③ 用户态内核（gVisor 等）  拦截系统调用，兼容性好              │
   ├──────────────────────────────────────────────────────────────┤
   │ ② 容器 + seccomp + 只读挂载  常见的默认选择                    │
   ├──────────────────────────────────────────────────────────────┤
   │ ① 进程内（Wasm / 受限解释器）  最轻，但只隔离计算，不隔离网络   │
   └──────────────────────────────────────────────────────────────┘
   注意：**①–⑤ 隔离的是"执行"，而 agent 的主要风险在"它被授权调用的 API"。**
"""),
        CALLOUT("danger", "上面那句注意值得展开，因为它是一个很常见的误解："
                          "<strong>把 agent 放进一个强隔离的沙箱，并不会降低"
                          "「它拿着你的 API token 去发邮件」这类风险。</strong>"
                          "<em>沙箱隔离的是「代码执行的副作用」——文件系统、进程、内核；"
                          "而 agent 的主要能力来自它被显式授予的 API 调用权限，"
                          "那些调用是「合法」的，沙箱不会拦。</em>"
                          "<strong>所以沙箱与权限边界必须同时做，而且权限边界通常更重要。</strong>"),
        TABLE(["风险类型", "沙箱能防吗", "权限边界能防吗", "出站控制能防吗"], [
            ["执行任意代码破坏本机", "<strong>✅ 主要靠它</strong>", "部分", "❌"],
            ["读取本机敏感文件", "✅（只读挂载 + 范围限制）", "<strong>✅</strong>", "❌"],
            ["<strong>用授权的 API 做坏事</strong>", "<strong>❌</strong>", "<strong>✅</strong>", "部分"],
            ["<strong>把数据发到外部</strong>", "部分（网络命名空间）", "部分", "<strong>✅ 主要靠它（04 模块）</strong>"],
            ["消耗资源（算力/配额）", "✅（cgroups）", "部分（预算）", "❌"],
        ]),
        H3("沙箱设计的四条实用规则"),
        OL([
            "<strong>默认无网络</strong>，需要时通过一个显式的出站代理（04 模块）。"
            "<em>「容器里能直接连外网」是一个默认配置，而它应当被显式关掉</em>；",
            "<strong>文件系统只读 + 一个可写的工作目录</strong>，"
            "而工作目录在每个任务之间被<strong>销毁重建</strong>"
            "（呼应 C68 模块 02 的「环境必须在任务之间重置」）；",
            "<strong>凭证不进沙箱</strong>——"
            "<em>agent 需要调用 API 时，请求经过一个持有凭证的代理，"
            "而沙箱内只有一个短期、窄范围的令牌</em>。"
            "<strong>这条能把「凭证泄漏」这类最严重的后果直接消除。</strong>",
            "<strong>资源与时间上限</strong>：CPU、内存、墙钟、以及调用配额。"
            "<em>这既是安全措施也是成本措施（C68 模块 02 的预算熔断）。</em>",
        ]),
    ])),

    # ============================================================== 4
    ("confirmation", "确认：怎么设计才不会变成橡皮图章", "".join([
        P("模块 00 的防御姿态第 3 条是「不可逆操作必须有确认环节」。"
          "但确认这件事有一个和 C68 模块 04 的告警疲劳<strong>完全同构</strong>的失败模式。"),
        DUAL(
            "<strong>确认弹得越频繁，人就越倾向于不看内容直接点「同意」。</strong>"
            "<em>而一旦形成这个肌肉记忆，确认环节就从「一道防线」变成了「一次额外点击」</em>——"
            "它仍然在流程里，但已经不提供任何保护。"
            "<strong>所以「给所有操作都加确认」不是更安全，而是更不安全。</strong>",
            "这与 C68 模块 04 的告警疲劳是同一个结构："
            "<strong>确认的有效性取决于它的<em>信息密度</em>而非频率</strong>。"
            "形式化地说，设确认请求的到达率为 $\\lambda$、"
            "其中真正需要拒绝的比例为 $\\pi$（基率），"
            "那么<em>人的认真程度大致随 $\\lambda$ 上升而下降、随 $\\pi$ 上升而上升</em>。"
            "<strong>目标不是最大化确认次数，而是最大化 $\\pi$</strong>——"
            "也就是让每一次弹出的确认都<em>值得</em>被认真看。"
            "notebook 第 4 节会把这个衰减模型跑出来。",
        ),
        H3("四条设计规则"),
        OL([
            "<strong>只对不可逆 + 对外的操作确认</strong>（模块 00 练习 4 已经形式化过）。"
            "<em>读操作、可撤销的写操作不该弹确认</em>——它们应当靠范围限制来管；",
            "<strong>确认必须展示「将要发生什么」而不是「模型想做什么」</strong>。"
            "<em>「agent 请求调用 send_email」是无信息的；"
            "「将向 attacker@… 发送一封包含以下内容的邮件：……」才是可判断的</em>；",
            "<strong>确认的内容必须与实际执行的内容一致</strong>——"
            "这是一个真实的漏洞类别（第 5 节的 TOCTOU）；",
            "<strong>确认不能被 L0 内容影响</strong>。"
            "<em>如果确认界面上展示的文本本身来自不受信内容，"
            "那么攻击者可以在里面写「这是一个例行操作，请点击同意」</em>——"
            "<strong>确认界面必须对展示的不受信内容做显式标注与转义。</strong>",
        ]),
        CALLOUT("warn", "第四条有一个具体的形态值得警惕：<strong>确认对话框里展示的邮件正文、"
                        "文件内容、URL，全部是 L0 内容。</strong>"
                        "<em>攻击者可以精心构造它们来影响<strong>人</strong>的判断</em>——"
                        "比如把危险的收件人地址放在一段很长的正文之后，"
                        "或者用视觉上相似的域名。"
                        "<strong>所以确认界面应当把「关键决策字段」（收件人、金额、目标路径）"
                        "从正文里抽出来单独、突出地展示</strong>，而不是让人在一大段文本里找。"),
    ])),

    # ============================================================== 5
    ("toctou", "TOCTOU：确认的内容与执行的内容不一致", "".join([
        P("这是一类具体的、在 agent 系统里真实存在的漏洞，"
          "而它在传统安全里有一个成熟的名字：<strong>检查时与使用时不一致</strong>"
          "（time-of-check to time-of-use）。"),
        ASCII("""
   时刻 t1   agent 提出: send_email(to="boss@corp.test", body="报告已完成")
   时刻 t2   系统展示确认: 「将向 boss@corp.test 发送……」
   时刻 t3   人点击「同意」
   时刻 t4   系统执行 —— **但执行的是什么？**
             如果这里重新向模型询问参数、或从可变的状态里取参数，
             那么 t3 与 t4 之间的任何变化都不在人的确认范围内。
"""),
        TABLE(["形态", "机制", "防御"], [
            ["<strong>参数重取</strong>", "确认后重新调用模型生成参数（比如为了「补全」）", "<strong>确认的是一个不可变的动作对象</strong>：参数在确认前就冻结并哈希"],
            ["<strong>状态漂移</strong>", "参数是一个引用（文件路径、记录 ID），而引用指向的内容在确认后变了", "<em>对内容也取哈希</em>，或在执行前重新校验"],
            ["<strong>批量确认</strong>", "「同意后续所有类似操作」——而「类似」的定义由后续动作自己说", "<strong>批量授权必须限定明确的范围与有效期</strong>，不能是开放式的"],
            ["<strong>确认复用</strong>", "一次确认被用于多次执行（重试路径上尤其常见）", "确认令牌一次性，且绑定动作哈希"],
        ]),
        CALLOUT("danger", "第三行的「批量确认」在实践中最常见，也最容易失控："
                          "<strong>用户点了「不要再问我了」，而这个授权的范围是由后续动作自己解释的。</strong>"
                          "<em>攻击者只需要让第一次操作看起来无害（从而获得批量授权），"
                          "后续的操作就都不再需要确认</em>。"
                          "<strong>正确做法：批量授权必须绑定到具体的范围</strong>——"
                          "「本次会话内，向 <code>*.corp.test</code> 发邮件不再询问」，"
                          "而不是「send_email 不再询问」。"),
        H3("动作对象：一个可以直接抄的实现"),
        CODE("""# 确认的对象必须是**不可变的、可哈希的**，而不是「一个意图」
@dataclass(frozen=True)
class Action:
    op: str                     # "send_email"
    target: str                 # "boss@corp.test"
    payload_sha: str            # 正文的哈希（内容也被冻结）
    ctx_trust: int              # 提出这个动作时的上下文信任等级
    provenance: tuple           # 完整的来源链（模块 02 第 4 节）

    def digest(self) -> str:
        return sha256(f"{self.op}|{self.target}|{self.payload_sha}|{self.ctx_trust}")

# 确认令牌绑定动作摘要，一次性，有有效期
token = confirm_ui.request(action)          # 人看到的是 action 的字段，不是"意图"
assert token.action_digest == action.digest()   # ← 执行前必须校验
assert not token.used and token.not_expired()
execute(action)                              # 执行的就是被确认的那个对象"""),
        P("<strong>这个实现里最重要的一行是那个 <code>assert</code></strong>："
          "<em>它把「确认的内容 == 执行的内容」从一条约定变成了一个会失败的检查</em>。"
          "而 <code>frozen=True</code> 保证了动作对象在确认与执行之间不可能被修改。"),
    ])),

    # ============================================================== 6
    ("audit", "审计：让「事后能查清」变成一个可验证的属性", "".join([
        P("前五节都在讲预防。这一节讲一个同等重要但常被推后的东西："
          "<strong>当事情真的发生了，你能不能查清。</strong>"),
        H3("一条完整的审计记录需要什么"),
        CODE("""{
  "ts": "2026-08-31T10:14:22Z",
  "session": "sess-9f21",
  "action": {"op": "send_email", "target": "boss@corp.test",
             "payload_sha": "7d2e…", "digest": "a91c…"},
  "decision": "allowed",
  "checks": {"granted": true, "scope": true, "trust": true, "confirmed": true},
  "ctx_trust": 2,
  "provenance": [                       // ← **最重要的一段**
    {"source": "user",            "trust": 2, "ref": "msg-118"},
    {"source": "web",             "trust": 0, "ref": "https://example.test/a"},
    {"source": "subagent:summarizer", "trust": 0, "ref": "sub-77"}
  ],
  "confirmation": {"token": "cnf-3b1", "by": "user-42", "shown_digest": "a91c…"},
  "tool_manifest_sha": "c04d…"          // 这次会话暴露了哪些工具（模块 02）
}"""),
        TABLE(["字段", "回答什么问题", "缺了它会怎样"], [
            ["<code>provenance</code>", "<strong>这个动作是被什么内容触发的</strong>", "<strong>只能看到「agent 决定发邮件」，查不出源头</strong>"],
            ["<code>ctx_trust</code>", "当时的上下文信任等级是多少", "无法判断「这次授权是否本该被拒绝」"],
            ["<code>checks</code>", "四个条件各自的结果", "只知道「放行了」，不知道哪一条本该拦住"],
            ["<code>action.digest</code> + <code>shown_digest</code>", "确认的与执行的是不是同一个", "TOCTOU 类问题无法被事后发现"],
            ["<code>tool_manifest_sha</code>", "当时模型看到了哪些工具", "动态裁剪之后无法复现当时的工具集"],
        ]),
        CALLOUT("intuition", "<strong><code>provenance</code> 是这份记录里唯一无法事后补上的字段。</strong>"
                             "<em>其余字段都能从配置和代码里重建，"
                             "但「这个动作是被哪一段内容触发的」这个信息，"
                             "如果当时没记，事后永远拿不回来</em>"
                             "（呼应 C66 模块 03 的「schema 是事前决定」）。"
                             "<strong>而它恰恰是安全事故复盘时最需要的那一个。</strong>"),
        H3("审计日志自己的完整性"),
        P("最后一个容易被忽略的点：<strong>审计日志必须是 agent 无法篡改的。</strong>"),
        UL([
            "<strong>agent 不持有写审计日志的权限</strong>——日志由包裹它的运行时写；",
            "<strong>只追加</strong>，且最好写到 agent 的沙箱之外；",
            "<strong>关键动作的日志写入必须在动作执行<em>之前</em>完成</strong>"
            "（<em>先记「即将执行」，再执行，再记「执行结果」</em>）——"
            "<strong>否则一个在执行中崩溃的动作会没有任何记录</strong>；",
            "<strong>日志缺口本身是一个告警</strong>：序号不连续、时间跳变都应当触发调查。",
        ]),
    ])),

    # ============================================================== 7
    ("change-impact", "权限变更的影响面：加一个工具之前先算一下", "".join([
        P("最后一节讲流程：<strong>怎么让「加一个工具」这件事不悄悄扩大攻击面。</strong>"),
        P("模块 02 第 5 节已经给出了核心判据（危险组合数）。这一节把它变成一个变更检查清单："),
        OL([
            "<strong>这个工具需要哪些能力</strong>（<code>requires</code>）？"
            "<em>它声明的与它实际用的是否一致</em>？",
            "<strong>加上它之后，危险组合数从几变成几</strong>？"
            "<em>从 0 变成非 0 是一个需要安全 review 的变更，而不是一次普通提交</em>；",
            "<strong>它的范围（scope）能收多窄</strong>？"
            "<em>「读文件」能不能收成「读 ./workspace/」</em>；",
            "<strong>它可逆吗</strong>？不可逆 → 需要确认 → 会增加确认频率 →"
            "<em>可能推高确认疲劳（第 4 节）</em>；",
            "<strong>它引入了新的出站通道吗</strong>？（04 模块）",
            "<strong>它的 description 与参数说明审过了吗</strong>？（模块 02 第 1 节）",
        ]),
        CALLOUT("intuition", "这六条里最有价值的是第 2 条，因为它是<strong>可自动计算的</strong>："
                             "<em>在 CI 里跑一遍「加上这个工具之后的危险组合数」，"
                             "从 0 变成非 0 就要求一个安全 review 的标签</em>。"
                             "<strong>这把「攻击面扩大」从一件靠人记得的事，"
                             "变成了一次会失败的构建</strong>——"
                             "而这正是 C68 模块 04 「确定性检查优先」在安全侧的应用。"),
        DUAL(
            "为什么这个流程重要？因为<strong>攻击面的扩大几乎从来不是一次决定，"
            "而是几十次「就加这一个」累积出来的。</strong>"
            "<em>每一次单独看都合理（「产品需要这个功能」），"
            "而累积效应没有任何人在看</em>——"
            "这与 C68 模块 03 讲的「渐进式退化」是完全同一个结构。",
            "所以防御手段也是同一个：<strong>除了「相对上次」的检查，还需要一个「锚定基线」</strong>。"
            "<em>每个季度算一次「当前的危险组合数 / 不可逆操作数 / 出站通道数」，"
            "与三个月前的锚点比较</em>——"
            "<strong>让那些「每次只加一点」的累积变得可见</strong>。"
            "notebook 第 7 节会把这个季度快照实现出来。",
        ),
    ])),
]

NB = [
    md("""# 03 · 沙箱与权限边界（能力四维 / 隔离层级 / 确认疲劳 / TOCTOU / 审计 / 变更影响面）

目标：把「最小权限」从口号变成**一个能算出来的集合**，并把确认与审计做成可验证的属性。

本 notebook 你会亲手实现：
1. **能力四维模型** —— 操作 / 范围 / 信任门槛 / 可逆性，四个条件合取
2. **路径范围检查的绕过与修法** —— `startswith` 为什么不够
3. **最小权限求解** —— 从任务步骤反推权限集，并与「按角色授予」对比
4. **确认疲劳的模拟** —— 确认频率如何摧毁确认的有效性
5. **TOCTOU** —— 确认的内容与执行的内容不一致，以及冻结动作对象的修法
6. **审计与 provenance 链** —— 唯一无法事后补上的字段
7. **变更影响面与季度锚点** —— 让「每次只加一点」的累积变得可见

> 心智模型：**沙箱隔离的是「代码执行的副作用」，
> 而 agent 的主要能力来自它被显式授予的 API 调用——那些调用是「合法」的，沙箱不会拦。
> 所以权限边界通常比沙箱更重要。**"""),

    md("""## 0 · 环境与能力四维模型"""),

    code("""import os, json, math, re, hashlib, itertools, posixpath
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

L0, L1, L2, L3 = 0, 1, 2, 3
LEVEL_NAME = {0: 'L0 不受信', 1: 'L1 半可信', 2: 'L2 用户', 3: 'L3 系统'}

def sha(obj, n=10):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:n]

@dataclass(frozen=True)
class Cap:
    \"\"\"能力的四个维度。frozen=True 让它不可变、可哈希。\"\"\"
    op: str                       # ① 操作
    scope: tuple                  # ② 范围（允许的目标模式）
    min_trust: int                # ③ 信任门槛
    reversible: bool              # ④ 可逆性
    egress: bool = False          # 是否构成对外通信（04 模块）

CAPS = {
    'read_workspace': Cap('read',  ('/work/**',),                L0, True),
    'read_home':      Cap('read',  ('/home/**',),                L2, True),
    'write_workspace':Cap('write', ('/work/**',),                L1, False),
    'send_email':     Cap('send',  ('*@corp.test',),             L2, False, True),
    'http_get':       Cap('fetch', ('*.corp.test', '*.pypi.org'), L1, True, True),
}
for name, c in CAPS.items():
    print(f'{name:<18} op={c.op:<6} scope={c.scope} '
          f'min_trust={LEVEL_NAME[c.min_trust]:<10} 可逆={c.reversible} 外通={c.egress}')
print('\\n✅ 四个维度都是显式的——而多数系统只做了第一维（「有没有这个工具」）。')"""),

    md("""## 1 · 范围检查：`startswith` 为什么不够"""),

    code("""def scope_match_naive(target, patterns):
    \"\"\"❌ 朴素前缀匹配。两个错误：不规范化路径、比较时去掉了尾部分隔符。
    后者是很常见的写法（「把通配符和斜杠都去掉再比」）。\"\"\"
    for p in patterns:
        prefix = p.replace('**', '').rstrip('/')      # ← '/work/**' → '/work'
        if target.startswith(prefix):
            return True
    return False

def scope_match_safe(target, patterns):
    \"\"\"✓ 先规范化（解析 .. 与多余分隔符）成绝对路径，再比较。\"\"\"
    norm = posixpath.normpath(posixpath.join('/', target))
    for p in patterns:
        base = posixpath.normpath(posixpath.join('/', p.replace('**', '')))
        # 必须是 base 本身或 base 下的子路径
        if norm == base or norm.startswith(base.rstrip('/') + '/'):
            return True
    return False

WORKSPACE = ('/work/**',)
CASES = [
    '/work/notes.txt',
    '/work/sub/dir/a.py',
    '/work/../home/user/.ssh/id_rsa',        # ← 经典绕过
    '/work/./../../etc/shadow',
    '/workspace_other/secret.txt',           # ← 前缀相同但不是子目录
    '/home/user/.ssh/id_rsa',
]
print(f"{'目标路径':<40}{'朴素':>8}{'安全':>8}")
for t in CASES:
    print(f'{t:<40}{str(scope_match_naive(t, WORKSPACE)):>8}'
          f'{str(scope_match_safe(t, WORKSPACE)):>8}')

assert scope_match_naive('/work/../home/user/.ssh/id_rsa', WORKSPACE) is True
assert scope_match_safe('/work/../home/user/.ssh/id_rsa', WORKSPACE) is False
assert scope_match_naive('/workspace_other/secret.txt', WORKSPACE) is True
assert scope_match_safe('/workspace_other/secret.txt', WORKSPACE) is False
assert scope_match_safe('/work/sub/dir/a.py', WORKSPACE) is True
assert scope_match_safe('/home/user/.ssh/id_rsa', WORKSPACE) is False
print('\\n✅ 两类绕过都被修掉了：')
print('   ① `..` 穿越 —— 必须先 normpath 再比较')
print('   ② 前缀相同但不是子目录（/workspace_other） —— 必须在 base 后加分隔符')
print('   → 「读文件」收窄成「读 /work/」之后，「读 ~/.ssh/」这条路径变成**不可达**。')"""),

    code("""def glob_match(target, pattern):
    \"\"\"域名/邮箱类的范围匹配。* 只匹配一段（不跨 .）—— 避免 evil.test 匹配 *.corp.test。\"\"\"
    rx = '^' + re.escape(pattern).replace(r'\\*', r'[^.@]+') + '$'
    return re.match(rx, target) is not None

EMAIL_SCOPE = ('*@corp.test',)
HOST_SCOPE = ('*.corp.test', '*.pypi.org')
print(f"{'目标':<34}{'在范围内':>10}")
for t, scope in [('boss@corp.test', EMAIL_SCOPE), ('attacker@evil.test', EMAIL_SCOPE),
                 ('boss@corp.test.evil.test', EMAIL_SCOPE),
                 ('api.corp.test', HOST_SCOPE), ('evil.test', HOST_SCOPE),
                 ('api.corp.test.evil.test', HOST_SCOPE)]:
    print(f'{t:<34}{str(any(glob_match(t, p) for p in scope)):>10}')

assert glob_match('boss@corp.test', '*@corp.test') is True
assert glob_match('attacker@evil.test', '*@corp.test') is False
assert glob_match('boss@corp.test.evil.test', '*@corp.test') is False
assert glob_match('api.corp.test', '*.corp.test') is True
assert glob_match('api.corp.test.evil.test', '*.corp.test') is False
print('\\n✅ 注意第三行与最后一行：**后缀伪装**（corp.test.evil.test）被正确拒绝——')
print('   这依赖于 `*` 不跨 `.` 这个约束。用 `.*` 的实现会被它绕过。')"""),

    md("""## 2 · 四个条件的合取：只要一条不满足，动作就不可达"""),

    code("""@dataclass(frozen=True)
class Action:
    op: str
    target: str
    payload_sha: str
    ctx_trust: int
    provenance: tuple = ()

    def digest(self):
        return sha({'op': self.op, 'target': self.target,
                    'payload_sha': self.payload_sha, 'ctx_trust': self.ctx_trust})

def authorize(action, granted, confirmed=False):
    \"\"\"四个条件合取。返回 (是否放行, 每一条的结果)。\"\"\"
    checks = {}
    cap = None
    for name in granted:
        c = CAPS[name]
        if c.op == action.op:
            cap = c
            break
    checks['granted'] = cap is not None
    if cap is None:
        return False, checks
    is_path = action.target.startswith('/')
    checks['scope'] = (scope_match_safe(action.target, cap.scope) if is_path
                       else any(glob_match(action.target, p) for p in cap.scope))
    checks['trust'] = action.ctx_trust >= cap.min_trust
    checks['reversible_or_confirmed'] = cap.reversible or confirmed
    return all(checks.values()), checks

GRANTED = ['read_workspace', 'write_workspace', 'send_email']
SCENARIOS = [
    ('读工作目录（L0 上下文）',    Action('read', '/work/a.txt', sha('x'), L0), False),
    ('读 home（L0 上下文）',       Action('read', '/home/u/.ssh/id_rsa', sha('x'), L0), False),
    ('写工作目录（L0，未确认）',   Action('write', '/work/b.txt', sha('x'), L0), False),
    ('写工作目录（L2，已确认）',   Action('write', '/work/b.txt', sha('x'), L2), True),
    ('发邮件给内部（L2，已确认）', Action('send', 'boss@corp.test', sha('x'), L2), True),
    ('发邮件给外部（L2，已确认）', Action('send', 'attacker@evil.test', sha('x'), L2), True),
    ('发邮件给内部（L0，已确认）', Action('send', 'boss@corp.test', sha('x'), L0), True),
]
print(f"{'场景':<30}{'放行':>6}  失败的检查")
for label, act, conf in SCENARIOS:
    ok, checks = authorize(act, GRANTED, confirmed=conf)
    failed = [k for k, v in checks.items() if not v]
    print(f'{label:<30}{str(ok):>6}  {failed if failed else "—"}')

assert authorize(Action('read', '/work/a.txt', sha('x'), L0), GRANTED)[0] is True
assert authorize(Action('read', '/home/u/.ssh/id_rsa', sha('x'), L0), GRANTED)[0] is False
assert authorize(Action('send', 'attacker@evil.test', sha('x'), L2), GRANTED, True)[0] is False
assert authorize(Action('send', 'boss@corp.test', sha('x'), L0), GRANTED, True)[0] is False
print('\\n✅ 四个条件各自都能独立拦住一类动作——这是纵深防御在权限层的具体形态。')
print('   注意倒数两行：**范围**拦住了外部收件人，**信任门槛**拦住了 L0 上下文——')
print('   即使人已经点了确认。')"""),

    md("""## 3 · 最小权限求解：从任务步骤反推"""),

    code("""TASK_STEPS = {
    '总结一个网页': [('fetch', '*.corp.test')],
    '整理工作目录里的笔记': [('read', '/work/**'), ('write', '/work/**')],
    '把笔记发给同事': [('read', '/work/**'), ('send', '*@corp.test')],
    '安装依赖并跑测试': [('fetch', '*.pypi.org'), ('read', '/work/**'), ('write', '/work/**')],
}

def minimal_caps(steps):
    \"\"\"最小权限 = 每一步实际需要的能力的并集（且范围取最窄的那个）。\"\"\"
    needed = set()
    for op, target in steps:
        best = None
        for name, c in CAPS.items():
            if c.op != op:
                continue
            in_scope = (scope_match_safe(target.replace('**', 'x'), c.scope)
                        if target.startswith('/')
                        else any(glob_match(target.replace('*', 'x'), p) for p in c.scope))
            if in_scope:
                # 取范围最窄的（模式数最少 + 字符串最长 = 更具体）
                key = (len(c.scope), -sum(len(s) for s in c.scope))
                if best is None or key < best[0]:
                    best = (key, name)
        if best:
            needed.add(best[1])
    return sorted(needed)

ROLE_CODING_AGENT = sorted(CAPS)     # 「按角色授予」= 给它全部
print(f"{'任务':<24}{'最小权限':<46}{'规模':>6}")
for task, steps in TASK_STEPS.items():
    m = minimal_caps(steps)
    print(f'{task:<24}{str(m):<46}{len(m):>6}')
print(f'\\n按角色授予（编码 agent）: {ROLE_CODING_AGENT}  规模 {len(ROLE_CODING_AGENT)}')

sizes = [len(minimal_caps(s)) for s in TASK_STEPS.values()]
print(f'最小权限的平均规模 {np.mean(sizes):.1f} vs 按角色 {len(ROLE_CODING_AGENT)}  '
      f'→ 过授 {len(ROLE_CODING_AGENT)/np.mean(sizes):.1f} 倍')
assert max(sizes) < len(ROLE_CODING_AGENT)
assert 'read_home' not in set().union(*[set(minimal_caps(s)) for s in TASK_STEPS.values()])
print('\\n✅ 四个任务里没有一个需要 read_home——**而按角色授予会把它给出去**。')
print('   而这个权限正是「读 ~/.ssh/」的入口。')"""),

    code("""# 危险组合：这个权限集能不能构成外泄链路
def exfil_possible(granted):
    reads_private = any(CAPS[g].op == 'read' and CAPS[g].min_trust >= L2 for g in granted)
    # 更宽的定义：能读任何非工作目录的东西，或有 egress
    reads_any = any(CAPS[g].op == 'read' for g in granted)
    egress = any(CAPS[g].egress for g in granted)
    return {'reads': reads_any, 'reads_private': reads_private, 'egress': egress,
            'exfil': bool(reads_any and egress)}

print(f"{'权限集':<44}{'可读':>6}{'外通':>6}{'外泄链路':>10}")
for label, g in [('总结网页', minimal_caps(TASK_STEPS['总结一个网页'])),
                 ('整理笔记', minimal_caps(TASK_STEPS['整理工作目录里的笔记'])),
                 ('发笔记给同事', minimal_caps(TASK_STEPS['把笔记发给同事'])),
                 ('装依赖跑测试', minimal_caps(TASK_STEPS['安装依赖并跑测试'])),
                 ('按角色（全部）', ROLE_CODING_AGENT)]:
    e = exfil_possible(g)
    print(f'{label:<44}{str(e["reads"]):>6}{str(e["egress"]):>6}{str(e["exfil"]):>10}')

assert exfil_possible(minimal_caps(TASK_STEPS['整理工作目录里的笔记']))['exfil'] is False
assert exfil_possible(ROLE_CODING_AGENT)['exfil'] is True
print('\\n✅ 「整理笔记」这个任务的最小权限集**不构成外泄链路**——')
print('   而按角色授予的权限集构成。')
print('   注意「发笔记给同事」与「装依赖跑测试」都构成链路，')
print('   这两个任务需要额外的收窄（范围限制 + 出站白名单，04 模块）。')"""),

    md("""## 4 · 确认疲劳：确认频率如何摧毁确认的有效性"""),

    code("""def simulate_confirmation(n_requests, base_rate_malicious, prompts_per_hour,
                          careful0=0.95, decay=0.055, floor=0.10, seed=0):
    \"\"\"人的认真程度随确认频率上升而衰减。
    careful = max(floor, careful0 * exp(-decay * prompts_per_hour))\"\"\"
    rng = np.random.default_rng(seed)
    careful = max(floor, careful0 * math.exp(-decay * prompts_per_hour))
    caught = missed = false_reject = 0
    for _ in range(n_requests):
        malicious = rng.random() < base_rate_malicious
        attentive = rng.random() < careful
        if malicious:
            (caught if attentive else globals())  # 占位，下面显式计数
            if attentive:
                caught += 1
            else:
                missed += 1
        else:
            # 认真看的时候偶尔也会误拒（很低）
            if attentive and rng.random() < 0.01:
                false_reject += 1
    n_mal = caught + missed
    return {'careful': careful, 'n_malicious': n_mal,
            'catch_rate': caught / n_mal if n_mal else float('nan'),
            'missed': missed, 'false_reject': false_reject}

print(f"{'每小时确认次数':>16}{'认真程度':>10}{'恶意请求':>10}{'拦住率':>10}{'漏放':>8}")
for pph in [1, 3, 10, 30, 60]:
    r = simulate_confirmation(4000, 0.01, pph, seed=1)
    print(f'{pph:>16}{r["careful"]:>10.1%}{r["n_malicious"]:>10}'
          f'{r["catch_rate"]:>10.1%}{r["missed"]:>8}')

r1 = simulate_confirmation(4000, 0.01, 1, seed=1)
r60 = simulate_confirmation(4000, 0.01, 60, seed=1)
assert r1['catch_rate'] > 0.85 and r60['catch_rate'] < 0.30
print(f'\\n⚠️ 每小时 1 次确认时拦住 {r1["catch_rate"]:.0%}，'
      f'每小时 60 次时只拦住 {r60["catch_rate"]:.0%}。')
print('✅ **「给所有操作都加确认」不是更安全，而是更不安全**——')
print('   确认的有效性取决于它的信息密度，而不是频率。')
print('   （这与 C68-04 的告警疲劳完全同构。）')"""),

    code("""# 目标不是最大化确认次数，而是最大化「每次确认值得被看」的比例
def confirm_policy_compare(actions, policy):
    \"\"\"policy: 'all' | 'irreversible' | 'irreversible_and_egress' | 'l0_only'\"\"\"
    prompted = []
    for act, cap_name, malicious in actions:
        cap = CAPS[cap_name]
        if policy == 'all':
            need = True
        elif policy == 'irreversible':
            need = not cap.reversible
        elif policy == 'irreversible_and_egress':
            need = (not cap.reversible) or cap.egress
        elif policy == 'l0_only':
            need = (act.ctx_trust == L0) and ((not cap.reversible) or cap.egress)
        else:
            raise ValueError(policy)
        if need:
            prompted.append(malicious)
    n = len(prompted)
    return {'n_prompts': n, 'base_rate': (sum(prompted) / n) if n else float('nan')}

rng = np.random.default_rng(3)
ACTIONS = []
for i in range(3000):
    cap_name = str(rng.choice(list(CAPS)))
    trust = int(rng.choice([L0, L1, L2], p=[0.35, 0.25, 0.40]))
    # 关键的建模选择：**恶意请求只出现在 L0 上下文里**——
    # 因为注入正是从不受信内容进来的（模块 01）。这不是简化，这是威胁模型。
    malicious = bool(trust == L0 and rng.random() < 0.03)
    ACTIONS.append((Action(CAPS[cap_name].op, 'x', sha(i), trust), cap_name, malicious))
print(f'构造 {len(ACTIONS)} 个动作，其中恶意 '
      f'{sum(1 for _, _, m in ACTIONS if m)} 个（全部来自 L0 上下文）')

print(f"{'确认策略':<28}{'确认次数':>10}{'其中恶意的比例(基率)':>22}")
res = {}
for pol in ['all', 'irreversible', 'irreversible_and_egress', 'l0_only']:
    r = confirm_policy_compare(ACTIONS, pol)
    res[pol] = r
    print(f'{pol:<28}{r["n_prompts"]:>10}{r["base_rate"]:>22.2%}')

assert res['all']['n_prompts'] > res['l0_only']['n_prompts'] * 3
assert res['l0_only']['base_rate'] > res['all']['base_rate']
print(f'\\n✅ 从 all 收窄到 l0_only：确认次数降到 '
      f'{res["l0_only"]["n_prompts"]/res["all"]["n_prompts"]:.0%}，'
      f'而基率从 {res["all"]["base_rate"]:.2%} 升到 {res["l0_only"]["base_rate"]:.2%}。')
print('   **更少但更值得看的确认** —— 这才是提高确认有效性的方向。')"""),

    md("""## 5 · TOCTOU：确认的内容与执行的内容不一致"""),

    code("""class ConfirmToken:
    def __init__(self, action_digest, by):
        self.action_digest = action_digest
        self.by = by
        self.used = False

class Executor:
    def __init__(self, strict=True):
        self.strict = strict
        self.log = []

    def execute(self, action, token):
        \"\"\"strict=True 时校验「确认的 == 执行的」，并且令牌一次性。\"\"\"
        if self.strict:
            if token.used:
                return False, 'token_already_used'
            if token.action_digest != action.digest():
                return False, 'digest_mismatch(确认的与执行的不是同一个动作)'
            token.used = True
        self.log.append(action)
        return True, 'executed'

# 人确认的动作
approved = Action('send', 'boss@corp.test', sha('报告已完成'), L2)
tok = ConfirmToken(approved.digest(), by='user-42')

# 执行时参数被改了（参数重取 / 状态漂移）
tampered = Action('send', 'attacker@evil.test', sha('报告已完成'), L2)

for strict in [False, True]:
    ex = Executor(strict=strict)
    t = ConfirmToken(approved.digest(), 'user-42')
    ok1, why1 = ex.execute(tampered, t)
    print(f'strict={strict}: 执行被改过的动作 → {ok1} ({why1})')

ex_ok = Executor(strict=True)
t_ok = ConfirmToken(approved.digest(), 'user-42')
assert ex_ok.execute(tampered, t_ok)[0] is False
assert ex_ok.execute(approved, t_ok)[0] is True
# 令牌一次性
assert ex_ok.execute(approved, t_ok) == (False, 'token_already_used')
ex_bad = Executor(strict=False)
assert ex_bad.execute(tampered, ConfirmToken(approved.digest(), 'u'))[0] is True
print('\\n✅ 三条防御同时生效：')
print('   ① frozen 的动作对象 —— 确认与执行之间不可能被修改')
print('   ② digest 校验     —— 「确认的 == 执行的」变成一个会失败的检查')
print('   ③ 令牌一次性       —— 重试路径上不会复用同一次确认')"""),

    code("""# 批量确认：范围必须显式限定，不能是开放式的
class BatchGrant:
    def __init__(self, op, scope, session, max_uses):
        self.op, self.scope, self.session = op, scope, session
        self.max_uses, self.uses = max_uses, 0

    def covers(self, action, session):
        if session != self.session or self.uses >= self.max_uses:
            return False
        if action.op != self.op:
            return False
        # 'ANY' 就是「不限目标」——这正是「不要再问我了」这个按钮的真实语义
        if 'ANY' in self.scope:
            return True
        return any(glob_match(action.target, p) for p in self.scope)

    def consume(self):
        self.uses += 1

# ❌ 开放式："send_email 不再询问" —— 范围由后续动作自己解释
OPEN = BatchGrant('send', ('ANY',), 'sess-1', max_uses=10 ** 9)
# ✓ 限定范围："本会话内，向 *@corp.test 发邮件不再询问，最多 20 次"
SCOPED = BatchGrant('send', ('*@corp.test',), 'sess-1', max_uses=20)

TESTS = [Action('send', 'boss@corp.test', sha('a'), L2),
         Action('send', 'attacker@evil.test', sha('b'), L2)]
print(f"{'动作':<34}{'开放式授权':>12}{'限定范围授权':>14}")
for a in TESTS:
    print(f'{a.op + " → " + a.target:<34}'
          f'{str(OPEN.covers(a, "sess-1")):>12}{str(SCOPED.covers(a, "sess-1")):>14}')
assert OPEN.covers(TESTS[1], 'sess-1') is True
assert SCOPED.covers(TESTS[1], 'sess-1') is False
assert SCOPED.covers(TESTS[0], 'sess-1') is True
assert SCOPED.covers(TESTS[0], 'sess-2') is False           # 跨会话失效
print('\\n✅ 开放式授权把外部收件人也覆盖了——**攻击者只需让第一次操作看起来无害**。')
print('   限定范围的授权则只覆盖 *@corp.test，且绑定会话与次数上限。')"""),

    md("""## 6 · 审计与 provenance 链"""),

    code("""class AuditLog:
    def __init__(self):
        self.entries = []
        self.seq = 0

    def pre(self, action, decision, checks, tool_manifest_sha, confirmation=None):
        \"\"\"关键：**在执行之前**写入。否则执行中崩溃的动作没有任何记录。\"\"\"
        self.seq += 1
        e = {'seq': self.seq, 'phase': 'intent',
             'action': {'op': action.op, 'target': action.target,
                        'digest': action.digest()},
             'decision': decision, 'checks': checks,
             'ctx_trust': action.ctx_trust,
             'provenance': list(action.provenance),
             'confirmation': confirmation,
             'tool_manifest_sha': tool_manifest_sha}
        self.entries.append(e)
        return self.seq

    def post(self, seq, result):
        self.seq += 1
        self.entries.append({'seq': self.seq, 'phase': 'result',
                             'refs': seq, 'result': result})

    def gaps(self):
        seqs = [e['seq'] for e in self.entries]
        return [i for i in range(1, max(seqs, default=0) + 1) if i not in seqs]

    def trace(self, digest):
        \"\"\"从一个动作反查它的完整来源链——事故复盘的核心操作。\"\"\"
        for e in self.entries:
            if e.get('action', {}).get('digest') == digest:
                return e['provenance']
        return None

PROV = (
    {'source': 'user', 'trust': L2, 'ref': 'msg-118'},
    {'source': 'web', 'trust': L0, 'ref': 'https://example.test/a'},
    {'source': 'subagent:summarizer', 'trust': L0, 'ref': 'sub-77'},
)
act = Action('send', 'boss@corp.test', sha('body'), L0, PROV)
audit = AuditLog()
ok, checks = authorize(act, GRANTED, confirmed=True)
s = audit.pre(act, 'allowed' if ok else 'denied', checks, tool_manifest_sha=sha(['t1', 't2']))
audit.post(s, 'blocked')

print('审计记录（意图阶段）:')
e = audit.entries[0]
for k in ['seq', 'phase', 'decision', 'ctx_trust', 'tool_manifest_sha']:
    print(f'  {k:<20} {e[k]}')
print('  provenance:')
for p in e['provenance']:
    print(f'    {LEVEL_NAME[p["trust"]]:<10} {p["source"]:<24} {p["ref"]}')

chain = audit.trace(act.digest())
assert chain is not None and len(chain) == 3
assert min(p['trust'] for p in chain) == L0
assert audit.gaps() == []
print(f'\\n✅ 从动作反查来源链：最低信任等级 = {LEVEL_NAME[min(p["trust"] for p in chain)]}')
print('   → 这个动作是被一段 L0 网页内容（经子 agent 传递）触发的。')
print('   **provenance 是这份记录里唯一无法事后补上的字段**——')
print('   其余都能从配置与代码重建，而它如果当时没记就永远拿不回来。')"""),

    code("""# 日志缺口本身是一个告警
broken = AuditLog()
broken.entries = [{'seq': 1}, {'seq': 2}, {'seq': 5}]
broken.seq = 5
print('序号 [1,2,5] 的缺口:', broken.gaps())
assert broken.gaps() == [3, 4]
assert audit.gaps() == []
print('✅ 序号不连续 → 有记录丢失或被删 → 应当触发调查。')
print('   而这要求：**agent 不持有写审计日志的权限**，日志由包裹它的运行时写，只追加。')"""),

    md("""## 7 · 变更影响面与季度锚点"""),

    code("""def surface_snapshot(granted):
    \"\"\"当前权限集的攻击面快照。\"\"\"
    caps = [CAPS[g] for g in granted]
    reads = [g for g in granted if CAPS[g].op in ('read', 'fetch')]
    egress = [g for g in granted if CAPS[g].egress]
    irrev = [g for g in granted if not CAPS[g].reversible]
    return {'n_caps': len(granted),
            'danger_pairs': len(reads) * len(egress),
            'n_irreversible': len(irrev),
            'n_egress': len(egress),
            'exfil': bool(reads and egress)}

def change_impact(before, after):
    b, a = surface_snapshot(before), surface_snapshot(after)
    added = sorted(set(after) - set(before))
    severity = 'review'
    if not b['exfil'] and a['exfil']:
        severity = 'security-review'            # 从 0 变成非 0 —— 需要安全 review
    elif a['danger_pairs'] > b['danger_pairs']:
        severity = 'security-review'
    elif a['n_irreversible'] > b['n_irreversible']:
        severity = 'elevated'
    return {'added': added, 'before': b, 'after': a, 'severity': severity}

BASE_GRANT = ['read_workspace', 'write_workspace']
print(f"{'变更':<34}{'危险组合':>10}{'外泄链路':>10}{'需要什么 review':>18}")
for label, new in [('加 send_email', BASE_GRANT + ['send_email']),
                   ('加 http_get', BASE_GRANT + ['http_get']),
                   ('加 read_home', BASE_GRANT + ['read_home']),
                   ('加 http_get + read_home', BASE_GRANT + ['http_get', 'read_home'])]:
    ci = change_impact(BASE_GRANT, new)
    print(f'{label:<34}{ci["before"]["danger_pairs"]}→{ci["after"]["danger_pairs"]:<8}'
          f'{str(ci["before"]["exfil"])}→{str(ci["after"]["exfil"]):<6}{ci["severity"]:>18}')

ci_http = change_impact(BASE_GRANT, BASE_GRANT + ['http_get'])
ci_home = change_impact(BASE_GRANT, BASE_GRANT + ['read_home'])
assert ci_http['severity'] == 'security-review', '引入外泄链路必须走安全 review'
assert ci_home['severity'] in ('review', 'elevated')
print('\\n✅ 「加 http_get」把外泄链路从不存在变成存在 → 自动要求安全 review。')
print('   这把「攻击面扩大」从一件靠人记得的事，变成了一次会失败的构建。')"""),

    code("""# 季度锚点：让「每次只加一点」的累积变得可见
QUARTERS = [
    ('2026-Q1', ['read_workspace', 'write_workspace']),
    ('2026-Q2', ['read_workspace', 'write_workspace', 'http_get']),
    ('2026-Q3', ['read_workspace', 'write_workspace', 'http_get', 'send_email']),
    ('2026-Q4', ['read_workspace', 'write_workspace', 'http_get', 'send_email', 'read_home']),
]
print(f"{'季度':<10}{'权限数':>8}{'危险组合':>10}{'不可逆':>8}{'出站':>8}{'外泄链路':>10}")
snaps = []
for q, g in QUARTERS:
    s = surface_snapshot(g)
    snaps.append((q, s))
    print(f'{q:<10}{s["n_caps"]:>8}{s["danger_pairs"]:>10}'
          f'{s["n_irreversible"]:>8}{s["n_egress"]:>8}{str(s["exfil"]):>10}')

first, last = snaps[0][1], snaps[-1][1]
print(f'\\n一年内: 权限数 {first["n_caps"]}→{last["n_caps"]}，'
      f'危险组合 {first["danger_pairs"]}→{last["danger_pairs"]}')
# 每一步的增量
steps = [snaps[i+1][1]['danger_pairs'] - snaps[i][1]['danger_pairs'] for i in range(3)]
print(f'每季度的危险组合增量: {steps}  ← 每一步单独看都很小')
assert max(steps) <= 2 and last['danger_pairs'] >= 4 * max(first['danger_pairs'], 1)
print('\\n✅ 每季度只增加 1–2 个危险组合，一年下来翻了几倍——')
print('   **这与 C68-03 的「渐进式退化」是同一个结构**：')
print('   每次单独看都合理，而累积效应没有任何人在看。')
print('   → 除了「相对上次」的检查，还需要一个季度锚点。')"""),

    md("""## ✏️ 练习 1：范围检查的绕过测试集

实现 `scope_test_suite(matcher, patterns)`：对一组已知的绕过用例测试一个匹配器，
返回 `{'passed': [...], 'failed': [...], 'safe': bool}`。
用例格式 `(target, should_allow)`。"""),

    code("""SCOPE_CASES = [
    ('/work/a.txt', True),
    ('/work/sub/b.py', True),
    ('/work', True),
    ('/work/../etc/passwd', False),
    ('/work/./../../root/.ssh/id_rsa', False),
    ('/workspace_other/x', False),
    ('/home/u/.ssh/id_rsa', False),
    ('/work/../work/c.txt', True),          # 绕了一圈但仍在范围内
]

def scope_test_suite(matcher, patterns):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
r_naive = scope_test_suite(scope_match_naive, WORKSPACE)
r_safe = scope_test_suite(scope_match_safe, WORKSPACE)
print(f'朴素匹配: safe={r_naive["safe"]}, 失败 {len(r_naive["failed"])} 例')
for t, exp, got in r_naive['failed']:
    print(f'   {t:<40} 期望={exp} 实际={got}')
print(f'\\n安全匹配: safe={r_safe["safe"]}, 失败 {len(r_safe["failed"])} 例')
assert r_naive['safe'] is False and r_safe['safe'] is True
assert len(r_naive['failed']) >= 3
print('✅ 练习 1 通过：注意最后一个用例（/work/../work/c.txt）——')
print('   它绕了一圈但仍在范围内，**正确的匹配器必须允许它**。')
print('   一个「只要含 .. 就拒绝」的实现会在这里误拒。')"""),

    md("""## ✏️ 练习 2：确认策略的效果对比

实现 `confirm_effectiveness(actions, policy, prompts_per_hour_scale=1/50)`：
先用 `confirm_policy_compare` 得到确认次数与基率，
再用 `simulate_confirmation` 估计拦住率（每小时确认次数 = 确认次数 × scale）。
返回 `{'n_prompts', 'base_rate', 'careful', 'catch_rate', 'expected_missed'}`。"""),

    code("""def confirm_effectiveness(actions, policy, prompts_per_hour_scale=1 / 50):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
print(f"{'策略':<28}{'确认次数':>10}{'基率':>9}{'认真度':>9}{'拦住率':>9}{'漏放':>7}")
eff = {}
for pol in ['all', 'irreversible', 'irreversible_and_egress', 'l0_only']:
    e = confirm_effectiveness(ACTIONS, pol)
    eff[pol] = e
    print(f'{pol:<28}{e["n_prompts"]:>10}{e["base_rate"]:>9.2%}'
          f'{e["careful"]:>9.1%}{e["catch_rate"]:>9.1%}{e["expected_missed"]:>7.1f}')
assert eff['l0_only']['careful'] > eff['all']['careful']
assert eff['l0_only']['expected_missed'] < eff['all']['expected_missed']
print(f'\\n✅ 练习 2 通过：从 all 收窄到 l0_only，')
print(f'   确认次数减少 {1 - eff["l0_only"]["n_prompts"]/eff["all"]["n_prompts"]:.0%}，')
print(f'   而**漏放的恶意请求也减少了**（{eff["all"]["expected_missed"]:.1f} → '
      f'{eff["l0_only"]["expected_missed"]:.1f}）。')
print('   更少的确认换来更好的保护——这不矛盾，因为人的注意力是有限资源。')"""),

    md("""## ✏️ 练习 3：TOCTOU 的检测

实现 `toctou_check(approved_action, executed_action, token)`：
返回 `(是否安全, 问题列表)`。检查三项：
① token 未被使用；② `token.action_digest == executed_action.digest()`；
③ `approved_action.digest() == executed_action.digest()`。"""),

    code("""def toctou_check(approved_action, executed_action, token):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
tok_a = ConfirmToken(approved.digest(), 'u')
ok_same, p_same = toctou_check(approved, approved, tok_a)
assert ok_same is True and p_same == []
ok_diff, p_diff = toctou_check(approved, tampered, ConfirmToken(approved.digest(), 'u'))
print('参数被改:', ok_diff, p_diff)
assert ok_diff is False and len(p_diff) >= 2
used = ConfirmToken(approved.digest(), 'u'); used.used = True
ok_used, p_used = toctou_check(approved, approved, used)
print('令牌已用过:', ok_used, p_used)
assert ok_used is False and any('used' in x for x in p_used)
print('\\n✅ 练习 3 通过：三项检查覆盖了 TOCTOU 的三种主要形态——')
print('   参数重取 / 状态漂移（②③）与确认复用（①）。')"""),

    md("""## ✏️ 练习 4：权限变更的自动分级

实现 `gate_permission_change(before, after, policy)`：
`policy` 是 `{严重度: 是否阻断}`。返回
`{'severity', 'blocked', 'added', 'delta_danger_pairs'}`。
用它验证「引入外泄链路的变更会被阻断」。"""),

    code("""def gate_permission_change(before, after, policy):
    # TODO：复用 change_impact
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
POLICY = {'security-review': True, 'elevated': False, 'review': False}
g1 = gate_permission_change(BASE_GRANT, BASE_GRANT + ['http_get'], POLICY)
g2 = gate_permission_change(BASE_GRANT, BASE_GRANT + ['read_home'], POLICY)
g3 = gate_permission_change(BASE_GRANT, BASE_GRANT, POLICY)
for label, g in [('加 http_get', g1), ('加 read_home', g2), ('无变更', g3)]:
    print(f'{label:<18} severity={g["severity"]:<18} blocked={g["blocked"]} '
          f'Δ危险组合={g["delta_danger_pairs"]:+d}')
assert g1['blocked'] is True and g1['delta_danger_pairs'] > 0
assert g2['blocked'] is False
assert g3['added'] == [] and g3['blocked'] is False
print('\\n✅ 练习 4 通过：这个函数应当作为 CI 的一步——')
print('   引入外泄链路的权限变更会**阻断构建**，直到安全 review 通过。')
print('   这是 C68-04「确定性检查优先」在安全侧的直接应用：误报率天然为零。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def scope_test_suite(matcher, patterns):
    passed, failed = [], []
    for target, should_allow in SCOPE_CASES:
        got = matcher(target, patterns)
        if got == should_allow:
            passed.append(target)
        else:
            failed.append((target, should_allow, got))
    return {'passed': passed, 'failed': failed, 'safe': len(failed) == 0}"""),

    code("""# 练习 2 参考答案
def confirm_effectiveness(actions, policy, prompts_per_hour_scale=1 / 50):
    base = confirm_policy_compare(actions, policy)
    n = base['n_prompts']
    pph = n * prompts_per_hour_scale
    sim = simulate_confirmation(max(n, 1), base['base_rate'] if n else 0.0, pph, seed=7)
    return {'n_prompts': n, 'base_rate': base['base_rate'],
            'careful': sim['careful'], 'catch_rate': sim['catch_rate'],
            'expected_missed': float(sim['missed'])}"""),

    code("""# 练习 3 参考答案
def toctou_check(approved_action, executed_action, token):
    problems = []
    if token.used:
        problems.append('token_already_used')
    if token.action_digest != executed_action.digest():
        problems.append('token_digest != executed_digest')
    if approved_action.digest() != executed_action.digest():
        problems.append('approved_digest != executed_digest')
    return (len(problems) == 0, problems)"""),

    code("""# 练习 4 参考答案
def gate_permission_change(before, after, policy):
    ci = change_impact(before, after)
    sev = ci['severity']
    return {'severity': sev, 'blocked': bool(policy.get(sev, False)),
            'added': ci['added'],
            'delta_danger_pairs': ci['after']['danger_pairs'] - ci['before']['danger_pairs']}"""),

    md("""---
## 🧪 真实工程胶囊：权限与沙箱的落地"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 能力声明：四个维度都要有（不要只有「有没有这个工具」）
# ══════════════════════════════════════════════════════════════════
CAPABILITIES = {
  "read_workspace": {"op": "read",  "scope": ["/work/**"],
                     "min_trust": "untrusted", "reversible": True},
  "send_email":     {"op": "send",  "scope": ["*@corp.test"],
                     "min_trust": "user", "reversible": False, "egress": True},
}
# 授权检查必须是四个条件的**合取**：
#   granted ∧ in_scope(target) ∧ ctx_trust >= min_trust ∧ (reversible ∨ confirmed)

# ══════════════════════════════════════════════════════════════════
# B. 路径范围检查：normpath + realpath，然后比较前缀 + 分隔符
# ══════════════════════════════════════════════════════════════════
def in_scope(path, roots):
    p = os.path.realpath(os.path.abspath(path))     # 解析 .. 与符号链接
    for r in roots:
        r = os.path.realpath(os.path.abspath(r))
        if p == r or p.startswith(r + os.sep):      # ← 必须加分隔符
            return True
    return False
# ❌ path.startswith("/work/")  会被 /work/../.ssh 与 /workspace_other 绕过
# 保留练习 1 的用例集作为回归测试。

# ══════════════════════════════════════════════════════════════════
# C. 沙箱：四条默认配置（都是「关掉」而不是「打开」）
# ══════════════════════════════════════════════════════════════════
# docker run \\
#   --network=none \\                       # ① 默认无网络，需要时走出站代理
#   --read-only \\                          # ② 根文件系统只读
#   --tmpfs /work:rw,size=512m \\           #    只有工作目录可写，任务间销毁重建
#   --cap-drop=ALL --security-opt=no-new-privileges \\
#   --memory=2g --cpus=2 --pids-limit=256 \\ # ④ 资源上限
#   <image>@sha256:...                      # 镜像 digest（C66-05）
#
# ③ **凭证不进沙箱**：agent 调 API 时经过一个持有凭证的代理，
#    沙箱内只有短期、窄 scope 的令牌（OAuth token exchange 的思路）。
#    这一条能把「凭证泄漏」这类最严重的后果直接消除。
#
# ⚠️ 记住沙箱的边界：它隔离的是**代码执行的副作用**，
#    而 agent 的主要能力来自被授权的 API 调用 —— 那些调用是"合法"的，沙箱不拦。

# ══════════════════════════════════════════════════════════════════
# D. 确认：动作对象冻结 + digest 校验 + 令牌一次性
# ══════════════════════════════════════════════════════════════════
@dataclass(frozen=True)                       # ← frozen 是关键
class Action:
    op: str; target: str; payload_sha: str; ctx_trust: int; provenance: tuple
    def digest(self): return sha256(...)

token = confirm_ui.request(action)            # UI 展示的是 action 的**关键字段**，
                                              # 不是「模型想调用 send_email」
assert not token.used
assert token.action_digest == action.digest() # ← 「确认的 == 执行的」
execute(action); token.used = True
#
# 确认策略：只对 (不可逆 ∨ 对外) ∧ ctx_trust==L0 的动作弹确认。
# 目标是**更少但更值得看的确认**——人的注意力是有限资源（练习 2）。
#
# 批量授权必须绑定范围 + 会话 + 次数上限：
#   「本会话内向 *@corp.test 发邮件不再询问，最多 20 次」
#   而不是「send_email 不再询问」。

# ══════════════════════════════════════════════════════════════════
# E. 审计：先记意图，再执行；provenance 是唯一补不回来的字段
# ══════════════════════════════════════════════════════════════════
seq = audit.pre(action, decision, checks, tool_manifest_sha, confirmation)
try:
    result = execute(action)
finally:
    audit.post(seq, result)          # 即使崩溃也有 intent 记录
#
# agent **不持有**写审计日志的权限；日志只追加，写在沙箱之外。
# 序号缺口本身是告警。

# ══════════════════════════════════════════════════════════════════
# F. CI 门禁：权限变更的自动分级（练习 4）
# ══════════════════════════════════════════════════════════════════
# 引入外泄链路（danger_pairs 从 0 变非 0）→ **阻断**，要求 security-review 标签
# 危险组合数增加                          → 阻断
# 不可逆操作数增加                        → elevated（提示 + 记录）
# 其余                                    → 普通 review
#
# 加上季度锚点：每季度记一次 surface_snapshot，与三个月前比较——
# 让「每次只加一点」的累积变得可见（与 C68-03 的渐进式退化同构）。
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 用在哪 |
|---|---|---|
| 能力四维 | 操作 / 范围 / 信任门槛 / 可逆性，四条合取 → 四个独立收紧点 | 权限模型 |
| 范围这一维 | 最常被忽略也最有效；`startswith` 会被 `..` 与同前缀目录绕过 | 路径与域名检查 |
| 最小权限可计算 | 从任务步骤的并集反推；按角色授予通常过授几倍 | 授权设计 |
| 沙箱的边界 | 它隔离执行副作用，不隔离「被授权的 API 调用」 | 别把沙箱当万能 |
| 凭证不进沙箱 | 走持有凭证的代理，沙箱内只有短期窄 scope 令牌 | 消除最严重后果 |
| 确认疲劳 | 「给所有操作加确认」更不安全；目标是提高基率而非频率 | 确认策略 |
| TOCTOU | 冻结动作对象 + digest 校验 + 令牌一次性 | 确认实现 |
| provenance | 唯一无法事后补上的字段 | 审计设计 |
| 变更分级 + 季度锚点 | 让「攻击面扩大」变成一次会失败的构建 | CI 门禁 |

下一模块：**04 · 数据外泄与出站控制**——外泄的通道比你想的多得多
（渲染一张图片就够了），以及为什么出站白名单是「致命三要素」里最容易去掉的那一个。""")
]
