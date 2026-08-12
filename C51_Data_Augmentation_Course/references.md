# 参考清单 · References（文本数据增强与合成数据工程）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的必读。
> 与相邻课程的分工：**C21** 讲预训练语料配比与合成数据在预训练中的角色；**C43** 讲 PB 级去重/过滤/流式的工程手艺；
> **C14** 讲合成数据理论与生成媒体评测；**C10/C03** 讲测量科学与评测统计；**C40** 讲研究方法论。
> **本课聚焦「有标注任务的训练集不够用时，怎么造与怎么验」。**

## 词面增强 · Lexical Augmentation
- ★ **Wei & Zou 2019, _EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks_** — 四操作的出处。**重点看两张图**：数据量-收益曲线（1% 数据涨 6 分、100% 数据涨 0.3 分）与 α 消融（0.1 附近最优、过大急降）。本课模块 01 的核心依据。
- ★ **Karimi, Rossi & Prakash 2021, _AEDA: An Easier Data Augmentation Technique for Text Classification_** — 只插标点，保真度精确 100%。它是「想清楚什么改动不破坏标签，比调参更有价值」的最好例子。
- **Zhang, Zhao & LeCun 2015, _Character-level Convolutional Networks for Text Classification_** — 同义词替换用于文本分类的早期实践（附录里的 thesaurus 方法）。
- **Feng et al. 2021, _A Survey of Data Augmentation Approaches for NLP_** — 把方法空间整理得最清楚的综述。适合快速定位「有哪些手段」，但要配合怀疑性复现工作一起读。
- **Jain et al. 2023, _NEFTune: Noisy Embeddings Improve Instruction Finetuning_** — 嵌入噪声这一类在线增强的代表：完全不动离散 token，保真度 100%。

## 语义增强 · Semantic Augmentation
- ★ **Sennrich, Haddow & Birch 2016, _Improving Neural Machine Translation Models with Monolingual Data_** — 回译的出处（原本用于 NMT 的合成源句）。
- ★ **Edunov, Ott, Auli & Grangier 2018, _Understanding Back-Translation at Scale_** — **本课模块 02 第二节的依据**：采样/加噪 beam 优于纯 beam。注意它的场景是「合成源句 + 真实目标句」，与分类增强的取舍不同（后者一旦漂移标签就错了）。
- ★ **Xie, Dai, Hovy, Luong & Le 2020, _Unsupervised Data Augmentation for Consistency Training_** — 把回译用于**一致性正则**而非直接增广（要求原样本与回译样本的预测分布一致）。它**绕开了保真度问题**（不用标签），是与本课主线互补的重要路线。
- **Sugiyama & Yoshinaga 2019, _Data Augmentation using Back-translation for Context-aware NMT_** — 回译在具体任务上的消融与失效分析。
- **Longpre, Wang & DuBois 2020, _How Effective is Task-Agnostic Data Augmentation for Pretrained Transformers?_** — **怀疑性复现的代表**：在预训练模型上，任务无关的增强收益大幅缩小。读它校准你对增强收益的预期。

## 指令数据合成 · Instruction Synthesis
- ★ **Wang et al. 2023, _Self-Instruct: Aligning Language Models with Self-Generated Instructions_** — 175 条种子 → 52k 数据。**重点读 §2 的四步循环、ROUGE-L 0.7 去重、以及分类任务的「输出优先」设计**（后者是防标签倾斜的关键，常被忽略）。
- ★ **Xu et al. 2023, _WizardLM: Empowering Large Language Models to Follow Complex Instructions_** — Evol-Instruct 的算子集与「消除」步骤。注意它同时有深度算子与广度算子——这个组合不是可选的。
- ★ **Xu et al. 2024, _Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing_** — 无种子生成，思路极其简洁（只给用户回合模板前缀）。理解它就理解了「合成数据本质是在反演模型分布」。
- ★ **Shumailov, Shumaylov, Zhao, Papernot, Anderson & Gal 2024, _AI models collapse when trained on recursively generated data_ (Nature)** — 模式坍塌的现象与机制（统计误差 + 模型误差）。**混入真实数据是主要缓解手段**这一结论出自这里。
- **Taori et al. 2023, _Stanford Alpaca_（技术报告与代码）** — Self-Instruct 的第一个大规模复现，工程细节最完整。
- **Burns et al. 2023, _Weak-to-Strong Generalization_** — 挑战「学生 ≤ 教师」的朴素结论：在某些设置下学生能超过弱监督。理解「合成数据的能力上限」这个问题的边界（C23 详读）。
- **Gunasekar et al. 2023, _Textbooks Are All You Need_（phi 系列）** — 高质量合成数据用于预训练的代表工作。与本课的下游增强场景不同，但「合成数据的质量比数量重要」这个结论互通。

## 多样性、去污染与质量控制 · QC
- ★ **Li, Galley, Brockett, Gao & Dolan 2016, _A Diversity-Promoting Objective Function for Neural Conversation Models_** — distinct-n 的出处。
- ★ **Zhu et al. 2018, _Texygen: A Benchmarking Platform for Text Generation Models_** — self-BLEU 的提出与多样性度量的系统讨论；也是「多样性度量可以被刷」这个问题的早期警示。
- ★ **Lee et al. 2021, _Deduplicating Training Data Makes Language Models Better_** — 去重与去污染的方法（精确子串 + MinHash）与必要性论证。**去污染与去重用同一套工具**这个观点出自它。C43 模块 01/05 有完整的工程实现。
- **Dodge et al. 2021, _Documenting Large Webtext Corpora: A Case Study on the Colossal Clean Crawled Corpus_** — 数据文档与污染审计的实践范例。
- **Sainz et al. 2023, _NLP Evaluation in Trouble: On the Need to Measure LLM Data Contamination_** — 污染检测的方法学与困难；理解「什么程度的相似算污染」为何没有客观定义。

## 在增强之外：用无标注数据的另外几条路 · Alternatives
> 增强不是「标注不够」的唯一解法。**决定用增强之前，先确认这几条路不适用**——它们常常更便宜、上限更高。
- ★ **Chen et al. 2020, _A Simple Framework for Contrastive Learning (SimCLR)_ 与 Gao et al. 2021, _SimCSE_** — 自监督对比学习：**用无标注数据学表示，再用少量标注微调**。SimCSE 的「dropout 即最小增强」是个漂亮的结果，也说明「增强越复杂越好」是错觉。
- ★ **Lee 2013, _Pseudo-Label_ 与 Xie et al. 2020, _Self-training with Noisy Student_** — 自训练：用模型自己在无标注数据上的预测当标签。**与本课模块 03 的蒸馏是同一族**，区别是教师就是自己的前一代。注意它同样有确认偏误与坍塌风险。
- **Sohn et al. 2020, _FixMatch_** — 半监督的强基线：弱增强产生伪标签、强增强上要求一致。**它把「增强」用作一致性约束而非样本扩增**，绕开了标签保真度问题（与 UDA 同源）。
- **Settles 2009, _Active Learning Literature Survey_** — 主动学习：**不造数据，而是挑最值得标注的数据**。在标注单价高的领域（本课模块 05 的「医疗」场景），它通常比增强的性价比更高，且两者可叠加。
- **Ratner et al. 2017, _Snorkel: Rapid Training Data Creation with Weak Supervision_** — 弱监督：用一组带噪的标注函数（规则、词典、远程监督）合成标签。**与本课模块 01 的「保护规则」思路相通**，但目标是造标签而不是造输入。

## 评测、统计与实验设计 · Evaluation
- ★ **Card, Henderson, Khandelwal, Jia, Mahowald & Jurafsky 2020, _With Little Power Comes Great Responsibility_** — **做任何小效应实验前必读**。系统论证大量 NLP 论文的统计功效不足（无法可靠检出它们报告的效应）。本课模块 05 的功效分析纪律出自这里。
- ★ **Dodge et al. 2020, _Fine-Tuning Pretrained Language Models: Weight Initializations, Data Orders, and Early Stopping_** — 种子方差的系统研究（小数据集上仅换种子波动 2–3 分）。它让「涨了 1 分」这类结论必须重新审视。C49 模块 03 详读。
- ★ **Koehn 2004, _Statistical Significance Tests for Machine Translation Evaluation_** — bootstrap 重采样检验的经典。本课的配对 bootstrap 实现以它为准。
- **Reimers & Gurevych 2018, _Why Comparing Single Performance Scores Does Not Allow to Draw Conclusions About Machine Learning Approaches_** — 标题就是结论。与 Dodge 2020 对读。
- **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_** — 把方差来源（初始化、数据顺序、数据划分、超参）系统分解，并给出正确的比较协议。
- **Kaplan et al. 2020 / Hoffmann et al. 2022（缩放律）** — 真实数据有缩放律，合成数据没有。读它们理解「为什么合成数据缺乏可预测的收益曲线」是个真问题（C21 详读）。
