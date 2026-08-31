# 参考清单 · 提示与上下文的程序化优化

> ★ = 必读。每条写明「它解决什么问题」以及「本课在哪里用到它」。
> **本课不重复 C33 的上下文工程文献**，也不重复 C03 的评测文献。

---

## 一 · 把 prompt 当程序（模块 01）

- ★ **Omar Khattab, Arnav Singhvi, Paridhi Maheshwari, et al.,
  _DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines_（2023）** —
  解决「怎么把 prompt 从字符串变成有签名、可组合、可编译的程序」。
  它的三层抽象（signature / module / compile）是本课模块 01 与 03 的组织方式来源。
  **本课模块 01 从零实现了 signature 与它的三个「不调用模型」的检查**，
  而 compile 那一层在模块 03。
- **_pydantic_ 与 _JSON Schema_（软件文档 / 规范）** —
  解决「输出契约怎么写、怎么校验」。
  **本课模块 01 的 signature 与模块 04 的 schema→掩码都以它为落地形态**，
  而「schema 与解析器必须同源生成」这条纪律也来自它
  （从一个类型定义同时导出 schema、掩码、解析器）。
- **Martin Fowler 等关于「配置即代码 / 变更可追溯」的一般讨论** —
  解决「一次没人知道发生过的变更怎么防」。
  **本课模块 01 第 7 节的 prompt 版本仓库与
  「指纹变了但 CHANGELOG 没动」这条零误报检查是它在 prompt 上的落地。**

---

## 二 · 示例选择与顺序（模块 02）

- ★ **Jiachang Liu, Dinghan Shen, Yizhe Zhang, et al.,
  _What Makes Good In-Context Examples for GPT-3?_（DeeLIO@ACL 2022）** —
  解决「示例该怎么选」。
  提出按与输入的相似度做 kNN 选择。
  **本课模块 02 第 1/2 节量出它的效应量：kNN 的 k=1 不输随机的 k=20。**
- ★ **Yao Lu, Max Bartolo, Alastair Moore, Sebastian Riedel, Pontus Stenetorp,
  _Fantastically Ordered Prompts and Where to Find Them:
  Overcoming Few-Shot Prompt Order Sensitivity_（ACL 2022）** —
  解决「示例顺序有多重要、怎么挑一个好顺序」。
  **本课模块 02 第 4 节的顺序实验与练习 2 的「带留出集的顺序搜索」建立在这条线上**；
  本课补充的一点是：<em>顺序的自由度高度集中——「最后一条放谁」解释了六成</em>。
- ★ **Zihao Zhao, Eric Wallace, Shi Feng, Dan Klein, Sameer Singh,
  _Calibrate Before Use: Improving Few-Shot Performance of Language Models_（ICML 2021）** —
  解决「示例带来的标签先验怎么测、怎么减掉」。
  无内容探针（content-free input）与减先验校准出自这里。
  **本课模块 02 第 5 节实现了它，并明确说清它的两个前提**：
  需要 logprobs、且隐含假设真实标签分布接近均匀。
- **Sewon Min, Xinxi Lyu, Ari Holtzman, et al.,
  _Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?_
  （EMNLP 2022）** —
  解决「示例到底提供了什么」（输入分布、标签空间、格式，而非严格的输入-标签映射）。
  它是本课选用「demos 上的 kNN」作为模拟器机制的经验依据之一。
- **Carlos Guestrin 等关于 MMR 与多样性重排的经典工作（IR 领域）** —
  **本课模块 02 的 MMR 式多样性选择直接借用**；算法本身在 C11 模块 03。

---

## 三 · 自动提示优化（模块 03）

- ★ **Krista Opsahl-Ong, Michael J Ryan, Josh Purtell, et al.,
  _Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs_
  （MIPRO, EMNLP 2024）** —
  解决「怎么同时优化指令与示例」。
  **本课模块 03 的「空间 + 目标 + 算法」三段分解与 bootstrap 示例来自这条线**，
  而本课补充的是<em>过拟合的定量刻画</em>与<em>硬约束目标函数</em>。
- ★ **Chengrun Yang, Xuezhi Wang, Yifeng Lu, et al.,
  _Large Language Models as Optimizers_（OPRO, ICLR 2024）** —
  解决「能不能让模型自己提出更好的指令」。
  **本课模块 03 第 2 节把它作为「让空间重新变成无限大」的那一档来讨论**：
  它能找到人想不到的写法，代价是过拟合风险回到最高档。
- **Yongchao Zhou, Andrei Ioan Muresanu, Ziwen Han, et al.,
  _Large Language Models Are Human-Level Prompt Engineers_（APE, ICLR 2023）** —
  自动指令生成这条线的起点。同上，本课把它归在「自由文本空间」那一档。
- ★ **本课程 C66 模块 04（胜者诅咒 / 多重比较 / MDE）** —
  **本课模块 03 第 4 节的过拟合分析完全建立在它之上**，
  只是参赛者从「模型」换成了「prompt 候选」：
  $\mathbb{E}[\max_i \hat s_i]$ 的偏差量级是 $\mathcal{O}(\sigma\sqrt{2\ln N})$，
  而 $\sigma\sqrt{2\ln N}$ 是一个上界。
  练习 3 的「从 N 与目标 gap 反解搜索集大小」也是它的直接应用。
- ★ **本课程 C67 模块 05（奖励模型与过优化）** —
  **本课模块 03 第 5 节的「有偏 judge 被优化放大」与它完全同构**，
  区别只在于被优化的对象是 prompt（便宜、可回滚）而不是权重（贵、不可逆）——
  <em>所以在 prompt 上它更容易发生，也更容易被忽略</em>。

---

## 四 · 受限解码（模块 04）

- ★ **Brandon T. Willard, Rémi Louf,
  _Efficient Guided Generation for Large Language Models_（Outlines, 2023）** —
  解决「正则 / CFG 怎么编译成能在 token 层高效使用的 FSM」。
  **本课模块 04 第 2 节的「合法前缀掩码」与「掩码可缓存」两点来自这里**；
  练习 1 演示的正是「只看位置的掩码不保证输出合法」这个错误实现。
  它的另一个核心工程贡献是处理 tokenizer 的多种切分。
- ★ **Kanghee Park, Jiayu Wang, Taylor Berg-Kirkpatrick, Nadia Polikarpova,
  Loris D'Antoni, _Grammar-Aligned Decoding_（NeurIPS 2024）** —
  解决「逐步掩码得到的分布不是条件分布，怎么修」。
  **本课模块 04 第 3 节的全部内容就是把这个失真精确算出来**
  （KL = 0.081 nat，`bug` 被低估 2.3 倍），
  而练习 2 进一步证明了一个更强的结论：
  <em>失真的唯一来源是分支之间的「收尾能力」差异，与被掩掉多少质量无关</em>。
- **_guidance_ / _llama.cpp GBNF_ / _xgrammar_（软件文档）** —
  解决「在不同推理栈上怎么表达约束」。
  **本课模块 04 的真实工程胶囊给出这三条路径的入口。**
- **HuggingFace `LogitsProcessor` 接口** —
  **模块 04 的掩码在真实栈上就是一个 LogitsProcessor**；
  接口层面的用法在 C50，本课从零实现它的逻辑。

---

## 五 · 运维与迁移（模块 05）

- ★ **本课程 C70 模块 05（索引运维：影子索引 + 双写 + 原子切换 + 回滚）** —
  **本课模块 05 的迁移流程直接复用这套结构**，
  只是把「索引」换成「prompt bundle + 模型」：
  中途状态必须不可达、回滚是反向切一个指针、
  以及「有些指标是观测量而不是门禁」（那里是 top-k 重叠率，这里是预测分布 PSI）。
- ★ **本课程 C03 模块 03（prompt 敏感性）** —
  它解释了为什么跨模型迁移必然出问题：
  <em>既然同一个模型对措辞、分隔符、选项顺序都敏感，那么跨模型不迁移是预期而不是意外</em>。
  **本课模块 05 第 2 节把这件事量成了一个具体数字**：
  为 A 优化的顺序搬到 B 上从 70% 掉到 50%。
- **本课程 C68 模块 04 / 05（门禁分级与阈值；漂移与 PSI）** —
  **本课全部五个模块的门禁都按 C68-04 的分级做**
  （确定性阻断 / 统计阻断 / 报警 / 观测），
  而模块 05 的监控四项复用 C68-05 的 PSI。
- **本课程 C33 模块 05（前缀缓存与稳定前缀）** —
  **本课模块 02 第 3 节与模块 05 第 4 节把它当成一个成本约束**：
  kNN 示例选择与前缀缓存直接冲突，分桶 kNN 是那个折中。
- **Google, _Site Reliability Engineering_（灰度发布与回滚）与
  Kleppmann, _Designing Data-Intensive Applications_（第 4 章：演化与兼容）** —
  解决「有状态的变更该怎么切」。
  **本课模块 05 第 5 节的灰度纪律（按稳定 ID 分流、分桶 × 分层看指标、
  两套指纹都进日志）是它们在 prompt 上的落地。**

---

## 六 · 本课程内部的依赖

| 课程模块 | 本课在哪里用到 |
|---|---|
| **C03 模块 03** | 迁移必然出问题的解释；模块 02 是它第 6 节的展开 |
| **C03 模块 06** | 「不改权重的引出」这一格；本课全部内容都在这一格里 |
| **C02** | 训练时优化 vs 推理时优化；prompt 优化应当先做 |
| **C09** | 思维链的效果——**本课不讨论**，因为模拟器没有推理能力 |
| **C11 模块 03** | MMR 与 RRF（模块 02 的多样性选择） |
| **C33 模块 01/02/05** | 上下文预算、compaction、前缀缓存；本课只把缓存当成本约束 |
| **C50** | LogitsProcessor 的接口用法（模块 04） |
| **C66 模块 04** | 胜者诅咒、多重比较、MDE（模块 03 的过拟合分析） |
| **C67 模块 02/03/05** | judge 的偏差与元评测；奖励模型过优化（模块 03 第 5 节） |
| **C68 模块 02/03/04/05** | 缓存键、切片分析、门禁分级、PSI |
| **C70 模块 05** | 影子 + 双写 + 原子切换 + 回滚（模块 05 的迁移流程） |
