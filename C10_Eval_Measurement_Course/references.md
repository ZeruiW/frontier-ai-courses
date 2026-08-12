# 参考清单 · References（评测数据与测量科学）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课从零实现的每个指标，都能在下列文献里找到原始定义与权衡；遇到分歧以原始论文为准。

## 测量科学与评测方法论 · Measurement & Evaluation Methodology
- ★ **Jacobs & Wallach 2021, _Measurement and Fairness_** — 把机器学习评测显式地搬到测量科学框架下：construct（你想测什么）与 operationalization（你实际测了什么）之间的鸿沟，正是公平性与评测争议的根源。读它建立「分数 = 一次有误差的测量」的世界观，是全课的纲。
- ★ **Liang et al. 2022, _Holistic Evaluation of Language Models (HELM)_** — 大规模、多维度评测语言模型的范本：同时报告准确率、校准、鲁棒性、公平性、效率等，而非单一榜单数字。展示「一个数字永远不够」的评测哲学如何落地。
- **Bowman & Dahl 2021, _What Will it Take to Fix Benchmarking in NLU?_** — 系统梳理基准失效的方式（标注假信号、饱和、伪相关），并给出改进准则。理解「为什么 SOTA 未必更强」的必读短文。
- **Gehrmann, Clark & Sellam 2023, _Repairing the Cracked Foundation_（生成评测综述）** — 全面盘点文本生成评测的问题与最佳实践（指标选择、人评设计、报告规范），是模块 03/04 的方法论地图。
- **Card et al. 2020, _With Little Power Comes Great Responsibility_** — 实证发现大量 NLP 实验功效严重不足，差异多在噪声范围内。把统计功效从「在线实验专属」拉回到所有评测，呼应模块 07。

## 标注、标签噪声与数据质量 · Annotation, Label Noise & Data Quality
- ★ **Northcutt, Jiang & Chuang 2021, _Confident Learning: Estimating Uncertainty in Dataset Labels_** — 从模型预测概率与给定标签的联合分布出发，估计噪声转移、定位错标样本的可扩展框架（cleanlab）。模块 01 噪声率估计与清洗的直接思想来源。
- ★ **Northcutt, Athalye & Mueller 2021, _Pervasive Label Errors in Test Sets..._** — 实测发现 ImageNet/CIFAR 等基准测试集普遍存在标签错误，且会改变模型排名。一记警钟：你信赖的「ground truth」可能没那么 ground truth。
- **Frénay & Verleysen 2014, _Classification in the Presence of Label Noise: a Survey_** — 标签噪声的系统综述：对称/类条件/样本相关噪声模型、噪声对各类学习器的影响、鲁棒方法。模块 01 噪声模型分类的标准参考。
- **Plank 2022, _The "Problem" of Human Label Variation_** — 论证标注分歧常不是噪声而是合理的人类差异，应建模而非抹平。模块 01/02 区分「错误」与「合理分歧」的理论依据。
- **Aroyo & Welty 2015, _Truth Is a Lie: Crowd Truth and the Seven Myths of Human Annotation_** — 拆穿「单一真值」「分歧=低质」等关于标注的七个迷思，提出 crowd truth。重塑你对金标的认知。

## 标注者一致性 · Inter-Annotator Agreement
- ★ **Artstein & Poesio 2008, _Inter-Coder Agreement for Computational Linguistics_** — 计算语言学里一致性系数的权威长综述：把 π/κ/α 的定义、假设、适用场景与陷阱讲得最透。模块 02 的主参考，遇到 IAA 困惑先查它。
- ★ **Cohen 1960, _A Coefficient of Agreement for Nominal Scales_** — Cohen's κ 的原始论文，提出用期望一致率扣除碰巧一致。理解 κ 必读源头。
- ★ **Krippendorff 2004/2018, _Content Analysis: An Introduction to Its Methodology_** — Krippendorff α 的权威出处：α = 1 − D_o/D_e 的统一框架，处理任意标注者数、缺失数据、多种度量。模块 02 推荐的默认 IAA，其计算细节以此为准。
- **Fleiss 1971, _Measuring Nominal Scale Agreement Among Many Raters_** — Fleiss κ 的原始论文，把一致性推广到多标注者、每条目标注者可变的场景。注意它与 Cohen κ 的 p_e 算法不同。
- **Powers 2012, _The Problem with Kappa_** — 集中讨论 κ 的反常行为（prevalence/bias 悖论、不可跨研究比较）。读它学会「不要只看一个 κ 数字」。

## 生成指标 · Generation Metrics
- ★ **Papineni et al. 2002, _BLEU: a Method for Automatic Evaluation of Machine Translation_** — BLEU 原始论文：修剪 n-gram 精度 + 简短惩罚 + 几何平均。机器翻译评测的奠基之作，模块 03 从零复现它，务必读懂 clipping 与 BP 的动机。
- ★ **Lin 2004, _ROUGE: A Package for Automatic Evaluation of Summaries_** — ROUGE 系列（N/L/W/S）的原始论文：以召回为中心、ROUGE-L 用 LCS。摘要评测的标准，模块 03 实现 ROUGE-N 与 ROUGE-L。
- ★ **Zhang et al. 2020, _BERTScore: Evaluating Text Generation with BERT_** — 用语境嵌入做 token 级软匹配的指标，能抓同义改写。模块 03 用玩具嵌入复现其贪心匹配 P/R/F，并讨论它的失效模式。
- **Banerjee & Lavie 2005, _METEOR_** — 在 unigram 上做含同义/词干的对齐、召回加权 F + 碎片惩罚，与人评相关高于 BLEU。模块 03 的 METEOR 直觉来源。
- **Popović 2015, _chrF: character n-gram F-score_** — 字符级 n-gram F 值，免分词、对形态丰富语言鲁棒。BLEU 的常用补充。
- **Sellam, Das & Parikh 2020, _BLEURT_** / **Rei et al. 2020, _COMET_** — 在人评上训练的学习型指标，相关性更高。读它们理解「学习型指标」的收益与不透明/可对抗代价。
- ★ **Callison-Burch, Osborne & Koehn 2006, _Re-evaluating the Role of BLEU in MT Research_** — 实证 BLEU 与人评相关在某些情形会断裂（高 BLEU 未必更好）。模块 03「指标失效模式」的经典警示。

## 人类评测 · Human Evaluation
- ★ **Bradley & Terry 1952, _Rank Analysis of Incomplete Block Designs_** — 成对比较模型的奠基：P(i≻j)=σ(s_i−s_j)。模块 04 用它把两两胜负拟合成排名（MLE），是 Arena 类评测的数学核心。
- ★ **Chiang et al. 2024, _Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference_** — 用大规模成对人类偏好 + Bradley-Terry/Elo 给模型排名的现代范本。模块 04 的现实落点，读它理解 pairwise 评测的工程与统计。
- **Karpinska, Akoury & Iyyer 2021, _The Perils of Using Mechanical Turk to Evaluate Open-ended Text Generation_** — 实证众包人评的种种陷阱（注意力、专业度、聚合）。模块 04 质量控制部分的依据。
- **Liang et al. 2020 / Clark et al. 2021, _All That's Human Is Not Gold_** — 人类难以可靠区分机器生成文本，且评测设计极大影响结论。提醒人评不是金标准、本身需要被评测。
- **Bai et al. 2022 / Zheng et al. 2023, _Judging LLM-as-a-Judge (MT-Bench, Chatbot Arena)_** — 系统研究用 LLM 当评委的可行性与偏置（位置、长度、自偏好）。模块 04 偏置一节的现代背景。

## 心理测量与 IRT · Psychometrics & IRT
- ★ **Embretson & Reise 2000, _Item Response Theory for Psychologists_** — IRT 最易读的入门权威：把题目难度/区分度与被试能力分开建模、ICC、信息函数讲得清楚。模块 05 的主参考。
- ★ **Lord 1980, _Applications of Item Response Theory to Practical Testing Problems_** — IRT 应用奠基：测验信息、自适应测验、题库等思想的源头。模块 05 自适应测验一节的根。
- **Rasch 1960, _Probabilistic Models for Some Intelligence and Attainment Tests_** — Rasch/1PL 模型原始著作，提出「特定客观性」。理解最简 IRT 与其哲学吸引力。
- **Lalor, Wu & Yu 2016, _Building an Evaluation Scale using Item Response Theory_** / **Vania et al. 2021, _Comparing Test Sets with Item Response Theory_** — 把 IRT 用到 NLP 基准：识别坏题、用能力而非原始分比较模型、构建更高效的评测集。模块 05 「用 IRT 设计基准」的直接落点。
- **Rodriguez et al. 2021, _Evaluation Examples Are Not Equally Informative_** — 用 IRT 论证基准里的样本信息量差异巨大，少量高信息题即可逼近全集排名。自适应/高效评测的实证支撑。

## 校准与不确定性 · Calibration & Uncertainty
- ★ **Guo et al. 2017, _On Calibration of Modern Neural Networks_** — 发现现代神经网络系统性过度自信，并提出温度缩放这一极简有效的事后校准法。模块 06 ECE/可靠性图/温度缩放全部复现自此，必读。
- ★ **Naeini, Cooper & Hauskrecht 2015, _Obtaining Well Calibrated Probabilities Using Bayesian Binning (ECE)_** — ECE 分箱估计的来源。理解 ECE 的定义、偏差与对分箱的敏感性。
- **Brier 1950, _Verification of Forecasts Expressed in Terms of Probability_** — Brier 分数原始论文（源自天气预报）。模块 06 Brier 分解（可靠性/分辨率/不确定性）的根。
- **Murphy 1973, _A New Vector Partition of the Probability Score_** — Brier 分数的可靠性-分辨率-不确定性三分解。模块 06 用它从一个数字诊断校准与区分度。
- **Nixon et al. 2019, _Measuring Calibration in Deep Learning_** — 批判性比较各种校准度量（等宽 vs 等频分箱、ECE 的缺陷），给出更稳健的做法。读它避免 ECE 的常见坑。
- **Kuhn, Gal & Farquhar 2023, _Semantic Uncertainty_** / **Angelopoulos & Bates 2021, _A Gentle Introduction to Conformal Prediction_** — 把不确定性推到生成与分布无关覆盖保证：语义熵检测幻觉、conformal 给带覆盖保证的预测集。模块 06 前沿延伸。

## 在线实验与因果 · Online Experiments & Causal
- ★ **Kohavi, Tang & Xu 2020, _Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing_** — 工业界 A/B 实验的权威实战书：随机化、功效、护栏指标、常见陷阱（偷看、SRM、新奇效应）。模块 07 的主参考。
- ★ **Deng, Xu, Kohavi & Walker 2013, _Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data (CUPED)_** — CUPED 原始论文：用实验前协变量无偏地缩减方差、提升功效。模块 07 从零实现它，必读。
- **Johari, Pekelis & Walsh 2017, _Peeking at A/B Tests / Always Valid Inference_** — 量化「反复偷看」如何抬高假阳性，并给出 always-valid p 值。模块 07 序贯检验一节的依据。
- **Benjamini & Hochberg 1995, _Controlling the False Discovery Rate_** — FDR 与 BH 校正的奠基论文，多重比较的现代标准。模块 07 多重比较一节实现它。
- **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_** — 把方差来源（随机种子、数据划分、超参）系统纳入基准比较，给出可信的比较协议。把实验严谨性带回离线基准。

## 本课定位与数据 · Scope & Data
- ⚠️ **全课纯 numpy/pandas、CPU 秒级**：核心算法（噪声转移、κ/α、BLEU/ROUGE/LCS、Bradley-Terry、2PL IRT、ECE/温度缩放、t/z 检验/CUPED）一律**从零实现并与定义/参考对拍**，让你确信自己算的是对的、且知道每个数字怎么来的。
- **真实数据胶囊**：每模块尽量用真实公开数据/真实配置（HuggingFace datasets-server REST、UCI、GSM8K 等）联网取数；**联网失败自动回退到内置真实数值**，逻辑与 assert 不受影响。数据缓存到 `~/.eval_measurement_data/`。
- **课程衔接**：与 model evaluation 实践直接相关；上游接概率统计基础，下游接 RLHF/偏好学习（人评与 Bradley-Terry 是其数据来源）、安全评测、基准设计。把这门「测量手艺」练扎实，你做的每一次评测都更可信。
