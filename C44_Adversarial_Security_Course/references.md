# 参考清单 · References（对抗 ML 与 AI 安全攻防）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基/必读。本课用玩具模型复现的每个攻击与防御，都能在下列文献里找到完整设定、真实规模的实验与权衡。**立场提示**：阅读这些攻击论文是为了**理解机理以构建防御**；研究应限于你自己的或获明确授权的系统。

## 总览与分类 · Surveys & Taxonomy
- ★ **NIST, _Adversarial Machine Learning: A Taxonomy and Terminology_ (AI 100-2 E2023/2025)** — 本领域的权威分类与术语基准。按学习阶段（训练/部署）、攻击者目标（可用性/完整性/隐私/滥用）、能力组织全部攻击与缓解。读它建立全局地图，本课模块 00 的攻击面框架直接对标它。
- ★ **OWASP, _Top 10 for LLM Applications_** — LLM 应用安全的工程清单，prompt injection 长期居首。把抽象风险落成可核对的工程条目，模块 05 的防御分层与它呼应。
- **Biggio & Roli, _Wild Patterns: Ten Years After the Rise of Adversarial Machine Learning_ (2018)** — 对抗 ML 十年回顾，把对抗样本、投毒、隐私攻击串成统一的攻击者建模框架。理解「为什么这些攻击是同一棵树上的果子」的最佳综述。
- **Papernot et al., _SoK: Towards the Science of Security and Privacy in Machine Learning_ (2018)** — 系统化梳理 ML 安全的攻击/防御与威胁模型形式化。SoK 类论文，适合搭建心智框架。
- **MITRE ATLAS** — 面向 ML 系统的对手战术与技术知识库（ATT&CK 的 ML 版）。把学术攻击映射到真实威胁情报，蓝队布防的实用索引。

## 对抗样本与鲁棒性 · Adversarial Examples & Robustness
- ★ **Szegedy et al., _Intriguing Properties of Neural Networks_ (2013)** — 首次系统揭示对抗样本：人眼无差别的微小扰动即可让 SOTA 网络分错。本课模块 01 的起点，奠定「神经网络存在反直觉脆弱性」的认知。
- ★ **Goodfellow, Shlens & Szegedy, _Explaining and Harnessing Adversarial Examples_ (2014)** — 提出 FGSM 与**线性假说**：对抗样本主因是高维下的局部线性而非过拟合。理解对抗样本为何存在、FGSM 为何有效，必读。
- ★ **Madry et al., _Towards Deep Learning Models Resistant to Adversarial Attacks_ (2017)** — 把鲁棒性写成 min-max 优化，提出 PGD 攻击与**对抗训练**。本课模块 01 的核心：PGD 是评测的事实标准，对抗训练是最可靠的经验防御。
- ★ **Athalye, Carlini & Wagner, _Obfuscated Gradients Give a False Sense of Security_ (2018)** — 戳穿一大批「看似鲁棒」的防御实为**梯度遮蔽**，并给出绕过它们的自适应攻击。鲁棒性**评测方法论**的必读警钟，模块 01 的「陷阱」一节据此而写。
- **Carlini & Wagner, _Towards Evaluating the Robustness of Neural Networks_ (2017)** — 提出强力的 C&W 攻击，证明许多防御（如蒸馏）不堪一击。评估防御必须用强攻击的奠基论证。
- **Croce & Hein, _Reliable Evaluation ... AutoAttack_ (2020)** — 免调参的自适应攻击集合，作为鲁棒性评测的可靠默认基线，减少「评测太弱→鲁棒性虚高」。配套 RobustBench 排行榜。
- **Cohen et al., _Certified Adversarial Robustness via Randomized Smoothing_ (2019)** — 用随机平滑给出可**证明**的 L2 鲁棒半径，区别于会被更强攻击推翻的经验防御。模块 01 认证鲁棒性一节的代表。
- **Ilyas et al., _Adversarial Examples Are Not Bugs, They Are Features_ (2019)** — 提出对抗脆弱性源于数据中真实但「非鲁棒」的特征。重塑了对「对抗样本本质」的理解，值得读以避免把它当成单纯的 bug。

## 投毒与后门 · Poisoning & Backdoors
- ★ **Biggio, Nelson & Laskov, _Poisoning Attacks against Support Vector Machines_ (2012)** — 数据投毒的奠基作：用梯度上升构造毒样本拉低 SVM 精度。本课模块 02 可用性投毒的源头，展示「训练数据是攻击面」。
- ★ **Gu, Dolan-Gavitt & Garg, _BadNets: Identifying Vulnerabilities ... Supply Chain_ (2017)** — 提出后门攻击：极低投毒率即可让带 trigger 的输入被定向误分，干净输入毫无异常。模块 02 后门部分的奠基，也点明供应链风险。
- **Chen et al., _Targeted Backdoor Attacks ... Data Poisoning_ (2017)** — 用混入式 trigger 实现隐蔽后门，推进 BadNets。理解 trigger 设计与隐蔽性权衡。
- **Shafahi et al., _Poison Frogs! Clean-Label Poisoning Attacks_ (2018)** — **干净标签**定向投毒：不改标签，靠特征碰撞让特定测试样本被误分，绕过人工标签核对。模块 02 clean-label 一节据此。
- **Tran, Li & Madry, _Spectral Signatures in Backdoor Attacks_ (2018)** — 后门**检测**奠基：被投毒样本在特征协方差谱上留下可分离签名，用 SVD 即可挑出。本课的检测演示对标它。
- **Chen et al., _Detecting Backdoor Attacks ... Activation Clustering_ (2018)** — 用隐层激活聚类区分干净/毒样本（毒类裂成两簇）。与谱签名并列的经典防御，notebook 复现其核心思想。
- **Wang et al., _Neural Cleanse_ (2019)** — 逆向每类的最小触发扰动来发现并修补后门（后门类的扰动异常小）。检测+缓解一体的代表作。

## 模型窃取与反演 · Extraction & Inversion
- ★ **Tramèr et al., _Stealing Machine Learning Models via Prediction APIs_ (2016)** — 系统化模型窃取：通过查询 API 高效重建模型功能甚至参数。模块 03 的奠基，确立「开放的预测 API 本身是机密性攻击面」。
- **Papernot et al., _Practical Black-Box Attacks against Machine Learning_ (2017)** — 用基于雅可比的数据增广少量查询训出替身，再用其可迁移对抗样本黑盒攻击目标。把窃取与对抗样本串起来的关键工作。
- ★ **Fredrikson, Jha & Ristenpart, _Model Inversion Attacks ... (2015)** — 模型反演奠基：由人脸识别模型的置信度梯度重建可辨识的人脸。模块 03 反演部分的源头，揭示「输出置信度即泄露通道」。
- ★ **Carlini et al., _Extracting Training Data from Large Language Models_ (2021)** — 从 GPT-2 逐字提取出含个人信息的训练原文。把「记忆=隐私风险」从理论变成实锤，连接模块 03 与 04。
- **Jagielski et al., _High Accuracy and High Fidelity Extraction of Neural Networks_ (2020)** — 厘清窃取的两个不同目标（准确率 vs 保真度）及其难度。模块 03「保真度 vs 准确率」一节据此。
- **Adi et al., _Turning Your Weakness Into a Strength: Watermarking Neural Networks ... (2018)** — 用后门式触发给模型加水印，事后证明所有权。窃取的**取证/威慑**手段代表。

## 成员推断与隐私 · Membership Inference & Privacy
- ★ **Shokri et al., _Membership Inference Attacks against Machine Learning Models_ (2017)** — MIA 奠基：用影子模型训练攻击模型判断样本是否在训练集。模块 04 的核心，确立 MIA 为隐私的标准探针。
- ★ **Carlini et al., _Membership Inference Attacks From First Principles_ (LiRA, 2022)** — 指出 MIA 应看**低误报率下的真正率**（log-scale ROC 左端），并提出按样本校准的似然比攻击。重塑 MIA 的评价标准，模块 04「TPR@low FPR」必读。
- **Yeom et al., _Privacy Risk in Machine Learning ... Overfitting_ (2018)** — 形式化**过拟合与成员泄露**的关联，给出 loss 阈值 MIA 的理论依据。理解「为什么过拟合 → 易被 MIA」。
- **Salem et al., _ML-Leaks_ (2019)** — 放宽 Shokri 的假设，展示**单个**影子模型甚至无影子模型也能做 MIA。说明 MIA 门槛比想象低，威胁更现实。
- ★ **Abadi et al., _Deep Learning with Differential Privacy_ (DP-SGD, 2016)** — 在 SGD 中裁剪每样本梯度并加噪，给训练以 (ε,δ)-DP 保证。模块 04 的防御落点：抵御 MIA/提取的有原则方法及其精度代价。
- **Dwork & Roth, _The Algorithmic Foundations of Differential Privacy_ (2014)** — DP 的标准参考专著。需要严谨理解隐私预算、组合定理时查它。

## Prompt 注入与供应链 · Prompt Injection & Supply Chain
- ★ **Greshake et al., _Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection_ (2023)** — **间接** prompt injection 奠基：恶意指令藏在 LLM 读取的外部内容里劫持应用。模块 05 的核心，定义了 RAG/agent 时代最严重的攻击面。
- ★ **Willison, _Prompt injection_ 系列文章 + _The Dual LLM pattern_** — 最早清晰阐述 prompt injection 本质（模型分不清指令与数据）并提出 dual-LLM/隔离防御。工程视角的必读，模块 05 防御架构据此。
- **Wei, Haghtalab & Steinhardt, _Jailbroken: How Does LLM Safety Training Fail?_ (2023)** — 从「能力-安全不匹配」与「目标竞争」解释越狱为何普遍可行。理解 jailbreak 机理而非招式，模块 05 直接注入部分参考。
- **Perez & Ribeiro, _Ignore Previous Prompt: Attack Techniques for Language Models_ (2022)** — 早期系统化提示注入与提示泄露攻击。建立直接注入的基本词汇表。
- **Carlini et al., _Poisoning Web-Scale Training Datasets is Practical_ (2023)** — 证明以低成本投毒真实大规模网络数据集可行。把数据供应链风险从玩具推到现实，连接模块 02 与 05。
- **Huggingface / EleutherAI, _safetensors_ 文档与设计说明** — 解释 pickle 反序列化的代码执行风险与 safetensors 的「只存张量、不执行代码」设计。模块 05 反序列化防御的实践基线。
- **Gu et al. / 业界报告：_Poisoned pretrained models & model hub security_** — 关于公开模型仓库中后门权重、恶意 `pickle` 检查点的实证与防御建议。模块 05 供应链清单的现实依据。

## 工具与基准 · Tools & Benchmarks
- **CleverHans / Foolbox / ART (Adversarial Robustness Toolbox)** — 对抗攻击与防御的开源实现库。本课用 numpy 从零实现核心算法以「看懂机制」；上手真实规模实验时这些库是标准工具。
- **RobustBench** — 标准化的对抗鲁棒性排行榜（用 AutoAttack 评测），避免各自为政的弱评测。查「当前最强经验防御能到多少鲁棒精度」的去处。
- **TensorFlow Privacy / Opacus** — DP-SGD 的工程实现（TF 与 PyTorch）。模块 04 的差分隐私防御从理论到落地的桥梁。
