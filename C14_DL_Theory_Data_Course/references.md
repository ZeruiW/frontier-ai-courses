# 参考清单 · References（深度学习理论与数据/生成媒体评测）

> 每条注明它**解决了什么问题、为什么值得读**。先读 ★ 标记的奠基/必读。本课用 numpy 玩具复现的每个现象，都能在下列文献里找到完整的实验与理论。

## 泛化与双下降 · Generalization & Double Descent
- ★ **Belkin, Hsu, Ma & Mandal 2019, _Reconciling modern machine learning practice and the bias–variance trade-off_ (PNAS)** — 双下降的奠基论文。系统展示测试误差越过插值阈值后**再次下降**，把经典 U 型接成「双下降」曲线，调和了「容量越大越过拟合」的经典理论与「越大越好」的深度学习实践。模块 01 全程复现它，必读。
- ★ **Nakkiran, Kaplan, Bansal, Yang, Barak & Sutskever 2021, _Deep Double Descent: Where Bigger Models and More Data Hurt_ (ICLR)** — 把双下降从随机特征推广到真实深度网络，提出 **model-wise / sample-wise / epoch-wise** 三种双下降，并用 **effective model complexity (EMC)** 统一解释。揭示「更多数据有时反而更差」的反直觉现象。模块 01/02 的核心参考。
- **Belkin, Hsu & Xu 2020, _Two models of double descent for weak features_** — 在最干净的随机特征/线性模型上给出双下降的可解析推导，是本课玩具模型的理论靠山。想看「为什么插值阈值处方差爆炸、过后又回落」的闭式，读它。
- **Bartlett, Long, Lugosi & Tsigler 2020, _Benign overfitting in linear regression_ (PNAS)** — 回答「为什么完美拟合噪声却还能泛化」：高维下噪声被吸收进无害方向。双下降第二段下降的理论解释方向。
- **Hastie, Montanari, Rosset & Tibshirani 2022, _Surprises in High-Dimensional Ridgeless Least Squares_** — 用随机矩阵理论精确刻画无脊（ridgeless）回归在过参数化区的风险曲线，给出双下降的渐近形状与最优正则强度。
- **Rahimi & Recht 2007, _Random Features for Large-Scale Kernel Machines_ (NeurIPS)** — 随机特征方法的原始论文。本课用它把「容量」做成一个可连续调的旋钮（特征数），是 CPU 上复现双下降最干净的玩具，模块 01 主力工具。

## 训练动力学：Grokking 与涌现 · Grokking & Emergence
- ★ **Power, Burda, Edwards, Babuschkin & Misra 2022, _Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets_** — grokking 的发现论文。在模算术等小数据集上观察到训练集早早满分、测试集长时间随机、再训很久后**突然**泛化。指出 **weight decay 是关键驱动**。模块 02 复现其核心曲线，必读。
- ★ **Nanda, Chan, Lieberum, Smith & Steinhardt 2023, _Progress measures for grokking via mechanistic interpretability_ (ICLR)** — 打开 grokking 的黑盒：模算术网络在 grokking 期间长出**傅里叶/三角恒等式回路**，并定义在最终跳变前就平滑变化的 **progress measure**，论证「突现」其实是平滑进展累积过阈。理解 grokking 机制的必读。
- ★ **Wei, Tay, Bommasani, ... & Fedus 2022, _Emergent Abilities of Large Language Models_ (TMLR)** — 「涌现能力」的代表作：列举多项小模型几乎为零、大模型突然具备的能力，把规模描述为带来质变。是后续 mirage 争议的靶子，必读以理解争论双方。
- ★ **Schaeffer, Miranda & Koyejo 2023, _Are Emergent Abilities of Large Language Models a Mirage?_ (NeurIPS, best paper)** — 对涌现的有力反驳：许多「涌现」源于**非线性/不连续的度量**（如 exact-match）。换成平滑度量（token 级 logprob、编辑距离），同一能力呈平滑可预测增长。模块 02 复现其「度量决定曲线形状」的核心实验，**必读**。
- **Kaplan, McCandlish, ... & Amodei 2020, _Scaling Laws for Neural Language Models_** — 损失随规模呈幂律的奠基经验。平滑缩放律与表观涌现并存，是 mirage 争议的背景板。
- **Hoffmann et al. 2022, _Training Compute-Optimal Large Language Models_ (Chinchilla)** — 修正参数/数据的最优配比。理解缩放律实践、以及「能力提升从何而来」的必要背景。
- **Liu, Kitouni, Nolte, ... & Williams 2022, _Towards Understanding Grokking: An Effective Theory of Representation Learning_** — 从表示学习/相变视角给 grokking 一个有效理论，补充 Nanda 的机制视角。

## 数据流水线 · Data Pipeline
- ★ **Lee, Ippolito, ... & Carlini 2022, _Deduplicating Training Data Makes Language Models Better_ (ACL)** — 用实证说明去重的价值：减少记忆、提升困惑度、降低评测污染、提高训练效率。给出 suffix-array 精确去重与 MinHash 近重复去重的工程方案。模块 03 去重部分的依据，必读。
- ★ **Broder 1997, _On the resemblance and containment of documents_** — MinHash 的原始论文。证明「两文档 MinHash 签名某位相等的概率 = 它们的 Jaccard 相似度」，奠定近线性大规模相似度估计与去重。模块 03 从零实现它，必读。
- **Penedo, Malartic, ... & Launay 2023, _The RefinedWeb Dataset for Falcon LLM_** — 展示**只靠**对 CommonCrawl 做严格过滤+去重，就能得到媲美策展语料的数据。现代预训练数据流水线的范本，模块 03 的工程对照。
- **Rae et al. 2021, _Scaling Language Models: Methods, Analysis & Insights from Training Gopher_** — 详细记录 Gopher 的质量过滤启发式（长度、符号比、重复率、停用词比等）。模块 03 质量过滤一节的具体规则来源。
- **Raffel et al. 2020, _Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer_ (T5 / C4)** — C4 语料的清洗流水线（去模板、去脏行、语言识别）公开且影响深远，是数据清洗的经典参考。
- **Soldaini et al. 2024, _Dolma_** 与 **Together 2023, _RedPajama_** — 开放预训练语料及其完整流水线文档，把本模块每一步（清洗/过滤/去重/混合）落到可复现的真实工程。

## 合成数据与模型坍塌 · Synthetic Data & Model Collapse
- ★ **Shumailov, Shumaylov, Zhao, Papernot, Anderson & Gal 2024, _The Curse of Recursion / AI models collapse when trained on recursively generated data_ (Nature)** — 模型坍塌的代表作。证明在自生成数据上递归训练会使分布逐代退化：先丢尾部、终塌成少数模式。生成式互联网时代的核心警示。模块 04 复现其方差收缩，**必读**。
- ★ **Alemohammad, Casco-Rodriguez, ... & Baraniuk 2023, _Self-Consuming Generative Models Go MAD_** — 用「自噬（autophagous）循环」框架系统刻画坍塌：无新鲜真实数据时质量与多样性都崩。提出真实数据注入的缓解作用。模块 04 的另一支柱。
- **Gerstgrasser, Schaeffer, ... & Koyejo 2024, _Is Model Collapse Inevitable? Breaking the Curse of Accumulating Real and Synthetic Data_** — 关键反转：若把合成数据**累积**到真实数据上（而非替换），坍塌可被遏制。模块 04 「累积 vs 替换」对照实验的依据。
- **Wang, Kordi, ... & Hajishirzi 2023, _Self-Instruct: Aligning Language Models with Self-Generated Instructions_** — 自训练/自举生成指令数据的代表，展示合成数据**正确使用**能提升能力。与坍塌论文并读，理解合成数据的双刃。
- **Zelikman, Wu, Mu & Goodman 2022, _STaR: Bootstrapping Reasoning with Reasoning_** — 用模型自己生成、且**经正确性过滤**的推理链自训练。过滤如何让自训练不坍塌反而变好的范例。
- **Maini, Seto, ... & Kolter 2024, _Rephrasing the Web_** — 用模型改写真实网页作为合成数据，兼顾质量与多样性的实用思路，对照「纯自生成易坍塌」。

## 生成媒体评测 · Generative Media Evaluation
- ★ **Heusel, Ramsauer, Unterthiner, Nessler & Hochreiter 2017, _GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium_ (FID 原始论文)** — 提出 **FID**：在 Inception 特征上用高斯假设算 Fréchet 距离，同时反映保真与多样，且对噪声/模式丢弃敏感。图像生成评测主指标，模块 05 从零实现，必读。
- ★ **Salimans, Goodfellow, Zaremba, Cheung, Radford & Chen 2016, _Improved Techniques for Training GANs_ (Inception Score)** — 提出 **IS**：用条件熵低（保真）+ 边际熵高（多样）刻画生成质量。理解其奖励什么、能被怎样钻空子，是生成评测的入门必读。模块 05 复现。
- ★ **Kynkäänniemi, Karras, Laine, Lehtinen & Aila 2019, _Improved Precision and Recall Metric for Assessing Generative Models_** — 把单标量拆成 **precision（保真）/ recall（多样）** 两个量，用 k-NN 流形估计支撑集，能分别诊断「生成得不真」与「漏了模式」。模块 05 从零实现 PR，必读。
- **Sajjadi, Bachem, Lucic, Bousquet & Gelly 2018, _Assessing Generative Models via Precision and Recall_** — precision-recall 评测框架的提出者（Kynkäänniemi 的前身），给出 PR 曲线视角，理解保真-多样权衡的源头。
- **Bińkowski, Sutherland, Arbel & Gretton 2018, _Demystifying MMD GANs_ (KID)** — 提出 **KID**（核 Inception 距离），无偏、无需大样本拟合高斯，是 FID 的稳健替代。理解 FID 偏差问题的延伸。
- **Hessel, Holtzman, Forbes, Bras & Choi 2021, _CLIPScore: A Reference-free Evaluation Metric for Image Captioning_** — 用 CLIP 图文嵌入余弦做**无参考**对齐评测，文生图时代的常用指标。理解无参考指标的便利与脆弱。
- **Theis, van den Oord & Bethge 2016, _A note on the evaluation of generative models_** — 经典警示：似然、样本质量、下游用途三者**可以互不一致**，没有单一指标能代表「生成得好」。任何做生成评测的人都该先读，校准对单一指标的迷信。
- **Stein et al. 2023, _Exposing flaws of generative model evaluation metrics and their unfair treatment of diffusion models_** — 系统检验各指标与人评的相关性、对特征提取器的敏感性。理解「指标怎么会骗人」的现代综述。

## 评测方法论与世界观 · Methodology (cross-cutting)
- ★ **Theis 2016（见上）+ Schaeffer 2023（见上）** — 两篇合起来是本课的方法论灵魂：**度量的选择决定你看到的结论**。无论评测语言模型还是生成媒体，先问「这个指标到底在量什么、连续吗、能被怎样操纵」。
- **Liang et al. 2022, _Holistic Evaluation of Language Models (HELM)_** — 多指标、多场景的整体评测框架，是「不要迷信单一指标」在 LLM 评测上的系统实践。
- ⚠️ **本课定位**：全部用**固定随机种子的纯 numpy 玩具**复现上述现象——随机特征回归（双下降）、模算术（grokking）、MinHash（去重）、迭代高斯自训练（model collapse）、玩具高斯特征（FID/IS/PR）。规模虽小，但每条曲线、每个指标都**可逐位复现、逻辑自洽、assert 兜底**。目的是让你把论文里的现象「攥在手里」，再去读真实规模的实验。
- **课程衔接**：上游接基础 ML 与统计；下游接 C03（评测与污染）、C04/C05（行为与安全评测）、生成模型与扩散课程。本课是「理解评测曲线为何反常 + 数据如何左右一切」的理论与数据底座。
