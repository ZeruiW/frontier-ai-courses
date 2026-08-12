# 参考清单 · References（上下文工程与记忆）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用 Python 标准库 + MockLLM 模拟的每个机制，都能在下列文献与官方文档里找到真实系统上的对应设计与权衡。

## 上下文工程与缓存（官方文档·必读） · Context Engineering & Caching

- ★ **Anthropic, _Prompt caching_（官方文档）** — 提示缓存的权威接口：`cache_control: {type:"ephemeral"}` 断点、前缀匹配（任意字节改变即失效）、渲染顺序 `tools → system → messages`、`cache_creation_input_tokens` / `cache_read_input_tokens` / `input_tokens` 的计费、5 分钟与 1 小时 TTL、最多 4 个断点、静默失效源（系统提示里的时间戳/UUID/未排序 JSON/变动工具集）。本课模块 05 从零模拟的前缀命中、TTL、成本账全部对标它，遇到字段分歧以它为准。
- ★ **Anthropic, _Effective context engineering for AI agents_（工程博客）** — 把「上下文工程」系统化为一门学科：上下文窗口是 agent 的稀缺资源，要管理而非堆满；compaction、检索/即时加载、外部记忆、长会话的注意力预算。本课「把窗口当中心资源经营」的世界观直接源于它，是读懂全课动机的总纲。
- ★ **Anthropic, _Messages API_（官方文档）** — 上下文管线的承载接口：`system` 字段、`messages` 数组与 `system`/`user`/`assistant` 角色、`max_tokens`、`usage`（输入/输出/缓存 token）、`stop_reason`（含 `max_tokens` 截断）、无状态语义（每次重发完整历史）。本课所有「组装上下文 → 发请求」的形状都对标它，把验证过的 MockLLM scaffold 接到真实模型只是把这一行换掉。
- **Anthropic, _Token counting_（官方文档）** — 用 `messages.count_tokens` 对目标模型精确计数，并明确警告不要用别家 tokenizer（如 tiktoken 估 Claude 会偏差 15–20%+）。本课用确定性近似计数以保证可断言，真实系统应改用它——模块 01「计数→预算→裁剪」一节的现实依据。
- **Anthropic, _Memory tool_ / _Context editing_（官方文档）** — memory 工具（`view/create/str_replace/insert/delete` 一个 `/memories` 目录）与上下文编辑（按阈值清除旧工具结果/思考块）。本课模块 03 的文件记忆系统是 memory 工具的最小内核；模块 02 的 compaction 与「上下文编辑」互为对照（摘要 vs 清除）。

## 长上下文与注意力 · Long Context & Attention

- ★ **Liu et al. 2023, _Lost in the Middle: How Language Models Use Long Contexts_** — 系统发现模型对长上下文「两端高、中间低」的利用率：关键信息放开头或结尾时表现最好，埋在中段时显著变差，且这条 U 形曲线随上下文变长更陡。本课「中间截断」「把最重要的放两端」「effective context 而非 window 大小」诸设计的直接依据，是理解「为什么不能无脑塞满窗口」的奠基实证。必读。
- **Anthropic, _Context windows_（官方文档）** — 各模型的上下文窗口大小与「输入 token + max_tokens ≤ 窗口」的硬约束、长上下文定价。本课「窗口是预算、要给输出留额度」的现实参数来源。
- **Press et al. 2022, _Train Short, Test Long (ALiBi)_** — 位置编码如何影响模型外推到比训练更长序列的能力。理解「窗口能开多大」背后有架构限制，而非随意可调——为本课「窗口是硬约束」提供模型侧的背景。
- **Xiao et al. 2023, _Efficient Streaming Language Models with Attention Sinks (StreamingLLM)_** — 流式无限长对话里保留最初几个 token（attention sink）+ 近期窗口即可稳定生成。与本课「保系统/保近期、滑动窗口」的截断直觉在机制层面呼应。

## 检索与 RAG · Retrieval & RAG

- ★ **Lewis et al. 2020, _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (RAG)_** — 提出把「检索器 + 生成器」端到端结合：先检索相关文档、再据此生成答案，让模型用上参数之外的知识。是 agent「按需把外部知识拉进上下文」范式的奠基论文，本课模块 04 的检索器即其最小内核。必读。
- **Karpukhin et al. 2020, _Dense Passage Retrieval (DPR)_** — 用学习到的稠密向量做段落检索，显著超越 BM25 等稀疏方法，奠定「embedding + 最近邻」检索范式。本课用 toy embedding 演示的余弦相似/top-k，真实系统即用 DPR 式的稠密检索。
- **Robertson & Zaragoza 2009, _BM25 / The Probabilistic Relevance Framework_** — 经典稀疏检索（词频-逆文档频率族）。理解它有助于看清稠密检索解决了什么、以及为什么实践中常稀疏+稠密混合（hybrid）。本课 toy 词频向量与 BM25 精神相通。
- **Gao et al. 2023, _Precise Zero-Shot Dense Retrieval (HyDE)_ / 检索增强综述** — 检索质量的提升手段（查询改写、HyDE、重排）。本课模块 04「重排」一节的现实背景：初步召回之上再精排能显著提相关性。
- **Johnson et al. 2017, _Billion-scale similarity search with GPUs (FAISS)_** — 大规模近似最近邻（ANN）索引，把检索从线性扫描降到近似对数。本课用「线性扫描+排序」讲清原理，FAISS/ANN 是把它工程化、规模化的下一步。

## 记忆系统 · Memory Systems

- ★ **Packer et al. 2023, _MemGPT: Towards LLMs as Operating Systems_** — 把 LLM 类比操作系统：用「主上下文（RAM）+ 外部存储（disk）」分层管理记忆，模型通过函数调用在两者间换页，从而在有限窗口里维持长期、海量的记忆。本课「窗口内 vs 窗口外、按需召回」的分层记忆观直接源于它，是理解文件记忆/compaction/检索为何能突破窗口上限的总纲。必读。
- **Park et al. 2023, _Generative Agents: Interactive Simulacra of Human Behavior_** — 给 agent 设计「记忆流 + 检索（近期性/重要性/相关性打分）+ 反思」的记忆架构。本课记忆召回「按相关性取少量、而非全量回灌」的思想与之相通。
- **Anthropic, _Building effective agents_（工程博客）** — 把 agent 模式拆成 workflow 与 agent 两类，并强调上下文管理、工具与记忆的工程取舍。建立「不要为了复杂而复杂、先用最简方案」的判断，贯穿本课对截断/压缩/记忆/检索的选择。
- **Wu et al. 2022, _Recursively Summarizing Books (recursive summarization)_** — 递归/分层摘要长文本：先摘段、再摘摘要，逐层压缩。本课模块 02 的滚动摘要与「摘要漂移」问题正是它的对话版，理解多轮压缩如何保信息/丢信息。

## 真实数据与接口来源 · Real Data & Interfaces

- **Anthropic Python/TypeScript SDK 与 Messages API 文档** — tool use、prompt caching、token counting、memory/context editing 的可执行真实接口。本课刻意让 MockLLM 的输入输出贴近它们的形状（`messages`、`cache_control`、`usage`），学完照着把验证过的 scaffold 接到真实模型（`client.messages.create(model="claude-sonnet-4-6", ...)`）是最自然的下一步。
- **公开长文档 / FAQ / 对话数据集（如 wikitext、维基段落）** — 可用作检索语料与压缩对象，对照本课 toy embedding 与摘要在真实文本上的行为。本课为可重复用内置小语料，但形状与真实检索/摘要一致。

## 本课定位与衔接 · Scope & Cross-links

- ⚠️ **本环境无 GPU、无需任何 API key**：全课用 Python 标准库 + **MockLLM**（确定性假模型）在 CPU 上端到端模拟上下文管线——token 预算与截断、compaction/滚动摘要、文件记忆（读/写/更新/去重）、toy embedding 检索（余弦/top-k/注入预算/重排）、prompt 前缀缓存与长会话成本账。每个零件都与朴素参考对拍、用 `assert` 兜底，保证你写的**预算与控制流逻辑正确**。
- **可迁移性**：你在 MockLLM 上验证过的 scaffold（计数、预算、截断、压缩、记忆、检索、缓存）可几乎一对一换成真实接口——把 `MockLLM(...)` 换成 `client.messages.create(model="claude-sonnet-4-6", ...)`、把近似计数换成 `messages.count_tokens`、把模拟缓存换成 `cache_control` 即可。本课刻意让形状贴近真实接口，且每个 notebook 都自带「无 key 自动回退 MockLLM」的真实适配段，绝不阻断。
- **课程衔接**：与本系列的「前沿智能体 / Agent Harness / 编码 Agent / Skills 与工具」诸课互补——上下文工程是它们共同的承重墙：任何长时间运行、要用工具/记忆/检索的 agent，最终都要面对「窗口不够用」这件事，而本课就是把这件事拆开、亲手解决。
