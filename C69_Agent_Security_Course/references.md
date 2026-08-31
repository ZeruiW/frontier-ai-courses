# 参考清单 · References（Agent 安全与提示注入）

> ★ 标必读。每条注明「解决什么问题」——这份清单不是让你把材料读一遍，
> 而是让你在被追问「这个做法有没有依据」时，知道**这不是我编的，有原始出处**。
> 本课把这些材料重新组织成了「威胁模型 → 注入 → 供应链 → 权限 → 外泄 → 评测」这条主线。
>
> **说明**：本清单只指向公开发表的研究与规范。
> 本课不引用、也不复述任何针对特定在线产品的可用攻击步骤。

---

## 一 · 提示注入的奠基工作 · Foundations

- ★ **Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz,
  Mario Fritz, _Not What You've Signed Up For: Compromising Real-World LLM-Integrated
  Applications with Indirect Prompt Injection_（AISec @ CCS 2023）** —
  解决「间接提示注入是不是一个真实的、可利用的攻击面」这个问题。
  它系统性地区分了**直接注入**（用户自己越狱）与**间接注入**（第三方通过 agent 读取的内容），
  并给出了注入的传递路径分类（检索、工具返回、持久化）。
  **本课模块 00 的攻击面地图与模块 01 的八种向量，分类框架直接承袭这篇。**
- ★ **Simon Willison 关于 prompt injection 的系列文章，特别是"lethal trifecta"
  与 _The Dual LLM pattern for building AI assistants that can resist prompt injection_** —
  解决两件本课最核心的事：
  **① 怎么快速判断一个 agent 危不危险**（不受信内容 + 私密数据 + 对外通信 = 外泄链路完整）；
  **② 在无法消除注入的前提下怎么设计架构**（隔离 LLM 无权限、特权 LLM 不接触不受信内容）。
  **模块 00 第 2 节与模块 01 第 4 节基本是这两个想法的展开与量化。**
- **OWASP, _Top 10 for Large Language Model Applications_（LLM01 Prompt Injection、
  LLM02 Sensitive Information Disclosure、LLM06 Excessive Agency）** —
  解决「怎么把 LLM 应用的风险讲给安全团队听」。
  它的价值主要在**共同词汇**，而不在技术深度；
  本课在需要与安全团队对齐时建议直接引用它的编号。

## 二 · 架构层防御 · Architectural Defenses

- ★ **Jerome H. Saltzer & Michael D. Schroeder,
  _The Protection of Information in Computer Systems_（Proc. IEEE, 1975）** —
  解决「保护机制该按什么原则设计」。八条原则里有五条在 agent 场景下格外相关：
  **最小权限、失败时默认拒绝、完全仲裁（不缓存授权决定）、机制经济性、心理可接受性**。
  <em>最后一条在本课模块 03 的确认疲劳一节里有直接对应</em>——
  一个弹得太频繁的确认会让人盲目点同意，从而失去保护作用。
- ★ **Bell–LaPadula 与 Biba 的信息流控制模型（1970s）** —
  解决「完整性等级该怎么传播」。
  **本课模块 00 的 `trust(输出) = min(上下文)` 就是 Biba 模型的「完整性等级只能单调下降」**，
  而「提权只能通过显式的、被审计的降级点」是它的标准补充。
  <em>把这条经典规则搬到 LLM 上下文，是本课最重要的一个结构性借用。</em>
- **Beurer-Kellner, Fischer, Tramèr 等关于「用代码而非提示做隔离」的路线
  （CaMeL 一类的设计）** —
  解决「双 LLM 模式的窄接口能不能推广」。
  思路是让特权侧生成一段**受限 DSL / 受限执行图**，由确定性解释器执行，
  而不受信内容只作为数据流过这段计划。
  **本课模块 01 第 4 节把它描述为「双 LLM 的窄接口从一个 schema 推广到一个执行图」**——
  思想同一个：让不受信内容只能作为数据，不能作为控制流。
- **能力安全（capability-based security）的经典文献（Dennis & Van Horn 1966 起）** —
  解决「权限该怎么表示」。
  本课模块 03 的能力四维模型是它与信息流控制的合成：
  前两维（操作、范围）是经典 capability，第三维引入完整性标签，第四维引入可撤销性。
  <em>三者合起来才能表达「L0 上下文下不许做不可逆的对外操作」这条规则。</em>

## 三 · 工具生态与供应链 · Tools & Supply Chain

- ★ **Anthropic, _Model Context Protocol_ 规范（工具发现、schema、传输层）** —
  解决「工具怎么被发现与调用」。
  对本课的关键点是**工具列表是运行时从服务端拉取的**，
  这使得「钉死版本号」不足以保证内容不变——**必须钉内容哈希**（模块 02 第 3 节）。
- **Invariant Labs 等安全团队对 MCP 工具描述投毒与 tool shadowing 的公开分析（2025）** —
  解决「工具描述是不是一个真实的注入通道」。
  **本课模块 02 第 1–2 节的三种影子形态（同名覆盖、近似名、描述劫持）的分类来自这类分析**，
  而 notebook 里「参数说明是最大盲区」这个量化结论是本课的补充。
- **npm / PyPI 生态的依赖混淆与 rug pull 事件的一般模式，以及
  SLSA 与 in-toto 的供应链完整性框架** —
  解决「供应链完整性该怎么做」。
  本课借用的是它们的核心机制（**lockfile + 内容哈希 + 变更走 review**），
  并指出工具生态比软件包生态更弱的一点：
  <em>没有现成的 lockfile 机制，而服务端可以随时改变返回内容。</em>

## 四 · 数据外泄 · Exfiltration

- ★ **Johann Rehberger（wunderwuzzi）关于 markdown 图片渲染外泄
  与 ASCII/Unicode smuggling 的公开研究** —
  解决「不需要网络权限的外泄通道有哪些」。
  **本课模块 04 第 2 节（渲染侧信道的带宽估算）与第 5 节（不可见字符走私 → 先解码再扫）
  的问题意识直接来自这条线索。**
  它最重要的贡献是指出：**只要 agent 能输出文本、客户端会渲染 markdown，通道就已经存在了**。
- **DNS 隧道与隐蔽信道的经典研究（Kaminsky 等）** —
  解决「怎么在只能做域名解析的环境里传数据」。
  本课模块 04 用它来说明**为什么 HTTP 层的白名单不够**——
  封 DNS 侧信道需要固定的内部解析器 + 只解析白名单域名。
- **SSRF 与云元数据服务攻击的公开研究，以及 OWASP 的 SSRF 防御指南** —
  解决「域名进了白名单之后还要检查什么」。
  本课模块 04 第 3 节的第四类绕过（解析后校验 IP 不在私有网段与元数据地址）出自这里。
- **W3C, _Content Security Policy Level 3_** —
  解决「怎么在客户端限制自动发起的网络请求」。
  **它是渲染侧信道唯一的不变量级防御**（模块 04 第 2 节），
  而它经常被漏掉，因为它不在后端。

## 五 · 安全评测方法学 · Evaluation Methodology

- ★ **Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner,
  Marc Fischer, Florian Tramèr, _AgentDojo: A Dynamic Environment to Evaluate
  Prompt Injection Attacks and Defenses for LLM Agents_（NeurIPS 2024）** —
  解决「agent 注入的评测该长什么样」：工具环境 + 一批注入任务 +
  **双指标（攻击是否成功 × 用户任务是否仍然完成）**。
  第二个指标至关重要——<em>一个把所有请求都拒了的 agent 很「安全」但没用</em>。
  **本课模块 05 把它定位为「回归基准」而非「安全性证明」**，理由见下一条。
- ★ **Florian Tramèr, Nicholas Carlini, Wieland Brendel, Aleksander Mądry,
  _On Adaptive Attacks to Adversarial Example Defenses_（NeurIPS 2020）** 及
  **Nicholas Carlini 等关于对抗鲁棒性评测方法学的系列工作** —
  解决「为什么静态基准上很强的防御在自适应攻击下几乎无效」。
  这条线索在对抗样本领域已经反复验证过，
  **而 agent 安全的评测方法学目前还远不如那个领域成熟**——
  所以本课模块 05 第 3 节的四条最低要求（白盒、明确预算、多轮适配、留出集）
  基本是把那个领域的教训直接搬过来。
- **UK AI Safety Institute / Anthropic / OpenAI 公开的红队方法学材料** —
  解决「红队该怎么组织」。
  本课模块 05 第 6 节的四类来源分工（已知手法库做回归、自动化变异压测检测器、
  内部红队做架构评审、外部红队兜底）与产出的结构化字段设计参考了这些材料，
  而 <code>defenses_that_held</code> 与 <code>fix_kind</code> 这两个字段是本课的补充——
  <em>它们是「哪一层真正起作用」与「团队是否在用概率保证承担不变量职责」的直接读数。</em>
- **本课程 C66 模块 04（方差、MDE、配对检验、胜者诅咒）** —
  解决安全评测的统计部分。
  **模块 05 完全复用 C66 的统计规范**，只是被测量的量从「能力」换成「攻击面」；
  而 C66 的**胜者诅咒**在这里以一个新形态出现：
  <em>按基准分数挑最好的防御，会让基准上的 ASR 系统性虚低。</em>
