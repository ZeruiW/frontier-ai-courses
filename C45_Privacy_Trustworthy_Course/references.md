# 参考清单 · References（隐私保护与可信 ML）

> 每条注明它解决了什么问题、为什么值得读。先读 ★ 标记的奠基 / 必读。本课用 numpy 从零实现的每个机制，都能在下列文献里找到真实系统中的对应实现与权衡。

## 差分隐私：奠基与教科书 · DP Foundations
- ★ **Dwork & Roth 2014, _The Algorithmic Foundations of Differential Privacy_（专著）** — 差分隐私的权威教科书。(ε,δ)-DP 定义、敏感度、Laplace / Gaussian / 指数机制、串并行组合、高级组合定理全在此。本课模块 01 的所有定义与定理都源出于此，遇到分歧以它为准；至少精读前 3 章与组合定理一章。
- ★ **Dwork, McSherry, Nissim & Smith 2006, _Calibrating Noise to Sensitivity in Private Data Analysis_** — 差分隐私的奠基论文。首次提出「按敏感度标定噪声」的 Laplace 机制与 ε-DP 定义，把隐私从「删字段」彻底转为「输出分布的稳定性」。理解 DP 为什么长这样，必读源头。
- **Dwork 2006, _Differential Privacy_（ICALP）** — DP 概念的另一篇奠基性提出，给出定义与动机（针对链接攻击 / 去标识的脆弱）。与上一篇互为正反面。
- **Warner 1965, _Randomized Response_** — 早于 DP 四十年的思想先驱：用概率性翻转答案获得可否认性，却仍能估计总体。是 local DP 与「可证明隐私」的史前史，读它体会 DP 的直觉根。
- **Wood et al. 2018, _Differential Privacy: A Primer for a Non-Technical Audience_** — 面向非专家的 DP 导读，适合用来向产品 / 法务 / 管理层解释「ε 到底意味着什么」。可信部署沟通的好材料。

## 高斯机制、RDP 与隐私会计 · Gaussian, RDP & Accounting
- ★ **Mironov 2017, _Rényi Differential Privacy_** — 用 Rényi 散度重新表述 DP，使组合变成简单相加、再紧致转回 (ε,δ)。这是现代 DP-SGD 隐私会计的数学骨架，模块 02 的「会计直觉」全靠它。强烈建议读懂 RDP→(ε,δ) 的转换。
- **Balle & Wang 2018, _Improving the Gaussian Mechanism for Differential Privacy_（Analytic Gaussian）** — 给出高斯机制噪声的精确（解析）标定，取代经典的 $\sigma\ge\Delta\sqrt{2\ln(1.25/\delta)}/\varepsilon$ 充分条件，在高隐私区更省噪声。实现高质量高斯机制时该用它。
- **Mironov, Talwar & Zhang 2019, _Rényi Differential Privacy of the Sampled Gaussian Mechanism_** — 把子采样 + 高斯机制的 RDP 算到极致，是 DP-SGD 会计器（如 Opacus 的 RDP accountant）的直接理论。
- **Kairouz, Oh & Viswanath 2015, _The Composition Theorem for Differential Privacy_** — 最优组合定理，刻画 k 次机制叠加的精确隐私损失。理解「为什么高级组合是 √k 而非 k」的紧致版本。

## DP-SGD：把 DP 装进训练 · DP Training
- ★ **Abadi, Chu, Goodfellow, McMahan, Mironov, Talwar & Zhang 2016, _Deep Learning with Differential Privacy_** — DP-SGD 的奠基论文。提出逐样本裁剪 + 高斯噪声 + **moments accountant**，首次让深度网络在可用 ε 下私有训练。本课模块 02 全程在复现它，必读。
- **Yousefpour et al. 2021, _Opacus: User-Friendly Differential Privacy Library in PyTorch_** — Opacus 的设计论文。讲清逐样本梯度怎么高效实现（扩展层 / 向量化）、RDP 会计器怎么用。把模块 02 的 numpy 原型接到生产 PyTorch 的桥梁。
- **De, Berrada, Hayes, Smith & Balle 2022, _Unlocking High-Accuracy Differentially Private Image Classification through Scale_** — 反直觉但重要：在大规模 + 大 batch + 合适技巧下，DP-SGD 的效用代价可以小到惊人。矫正「DP 必然大幅掉点」的成见，是 DP 落地乐观派的代表作。
- **Ponomareva et al. 2023, _How to DP-fy ML: A Practical Tutorial_** — 工程师视角的 DP-SGD 实操指南：超参怎么调、ε 怎么报告、常见坑。把理论接到实践，模块 02 / 05 的实战补充。
- **Tramèr & Boneh 2021, _Differentially Private Learning Needs Better Features (Not More Data)_** — 指出在好特征上做 DP 学习比堆数据更有效，揭示 DP 效用的关键瓶颈在表示而非样本量。理解 DP 效用代价从何而来。

## 联邦学习 · Federated Learning
- ★ **McMahan, Moore, Ramage, Hampson & Arcas 2017, _Communication-Efficient Learning of Deep Networks from Decentralized Data_** — 联邦学习与 **FedAvg** 的奠基论文。提出「数据不动、模型动」范式与按数据量加权平均的聚合，并展示在非 IID、不可靠客户端下仍可行。本课模块 03 从零实现它，必读。
- ★ **Bonawitz et al. 2017, _Practical Secure Aggregation for Privacy-Preserving Machine Learning_** — 安全聚合（SecAgg）的奠基论文。用成对掩码让服务器只能看到更新之和、看不到任何单个客户端更新，且能容忍客户端掉线。模块 03 的安全聚合直觉直接来自它，必读。
- **Kairouz et al. 2021, _Advances and Open Problems in Federated Learning_（综述）** — FL 领域的权威长综述：系统、非 IID、隐私、鲁棒、公平、个性化全覆盖。想看 FL 的全貌与开放问题，从这里入手。
- **Li, Sahu, Talwalkar & Smith 2020, _Federated Learning: Challenges, Methods, and Future Directions_** — 简明综述，把 FL 的四大挑战（通信、系统异构、统计异构 / 非 IID、隐私）讲清楚，适合建立框架。
- **Karimireddy et al. 2020, _SCAFFOLD: Stochastic Controlled Averaging for Federated Learning_** — 直面客户端漂移：用控制变量（control variates）校正非 IID 下的本地更新偏移，是 FedAvg 之后最重要的改进之一。模块 03「客户端漂移」一节的延伸解法。
- **Reddi et al. 2021, _Adaptive Federated Optimization_（FedAdam 等）** — 把 Adam 等自适应优化器搬到服务器端聚合，改善非 IID 收敛。FedAvg 的现代化。
- **McMahan et al. 2018, _Learning Differentially Private Recurrent Language Models_** — 把 DP 与 FL 结合（user-level DP + FedAvg）的代表作，展示两条隐私技术如何正交叠加。模块 03 / 05「DP+FL 组合」的依据。

## 机器遗忘 · Machine Unlearning
- ★ **Bourtoule et al. 2021, _Machine Unlearning_（SISA）** — 精确遗忘的奠基框架。提出 Sharded-Isolated-Sliced-Aggregated 训练，使删一条数据只需重训一个分片 / 切片，把精确遗忘成本从全量重训降到一小块。本课模块 04 的精确遗忘主线，必读。
- ★ **Guo, Goldstein, Hannun & van der Maaten 2020, _Certified Data Removal from Machine Learning Models_** — 近似遗忘的奠基：用影响函数式的一步更新做遗忘，并给出 (ε,δ) 式的 **certified removal** 保证，把「大概忘了」升级为「可证明忘到 ε 内」。模块 04 近似遗忘 + 认证的核心，必读。
- ★ **Koh & Liang 2017, _Understanding Black-box Predictions via Influence Functions_** — 把影响函数引入深度学习：用 $-H^{-1}\nabla L$ 估计单样本对参数 / 预测的影响而无需重训。它既是可解释性工具，也是近似遗忘的引擎。模块 04 影响函数一节的源头。
- **Cao & Yang 2015, _Towards Making Systems Forget with Machine Unlearning_** — 最早系统性提出「机器遗忘」概念的论文，用统计查询学习框架做高效遗忘。读它了解遗忘问题的起源。
- **Sekhari, Acharya, Kamath & Suresh 2021, _Remember What You Want to Forget: Algorithms for Machine Unlearning_** — 给出遗忘的泛化保证与样本复杂度分析，把遗忘与学习理论联系起来。理解遗忘「能删多少而不伤泛化」的理论边界。
- **Golatkar, Achille & Soatto 2020, _Eternal Sunshine of the Spotless Net: Selective Forgetting in Deep Networks_** — 深度网络选择性遗忘的代表作，提出基于 Fisher 信息的「擦除」更新与遗忘度量。模块 04 近似遗忘的另一条路线。
- **Thudi et al. 2022, _On the Necessity of Auditing for Machine Unlearning_** — 指出遗忘必须可审计，并讨论「证明遗忘发生过」的困难。模块 04 遗忘验证一节的方法论依据。

## 攻击侧：理解防御为什么必要 · Attacks (the threat we defend against)
- ★ **Shokri, Stronati, Song & Shmatikov 2017, _Membership Inference Attacks Against Machine Learning Models_** — 成员推断攻击的奠基论文，提出 shadow models 方法。它是隐私泄露的度量标尺，也是遗忘 / DP 效果的审计工具。C12 测量课与本课审计共用它，必读。
- **Carlini et al. 2021, _Extracting Training Data from Large Language Models_** — 证明能从 GPT-2 逐字复原训练样本，把记忆 / 隐私泄露从理论变成触目惊心的现实。C44 攻击课的核心，读它理解本课防御的紧迫性。
- **Carlini et al. 2022, _Membership Inference Attacks From First Principles_（LiRA）** — 把成员推断做到极致（似然比攻击），是当前最强的隐私审计基准。评估 DP / 遗忘是否真有效，该用这一类强攻击。
- **Nasr et al. 2021, _Adversary Instantiation: Lower Bounds for Differentially Private Machine Learning_** — 用攻击反推 DP-SGD 实际隐私的下界，检验声称的 ε 是否名副其实。隐私审计与「经验 ε」的代表作。

## 系统、规模化与综述 · Systems, Scale & Surveys
- **Abowd 2018, _The U.S. Census Bureau Adopts Differential Privacy_** — 美国 2020 人口普查全面采用 DP 的工程实践，是 DP 最大规模的真实部署。读它看预算管理、效用争议、组合核算在国家级系统里的样子。
- **Erlingsson, Pihur & Korolova 2014, _RAPPOR_（Google）** 与 **Apple Differential Privacy Team 2017, _Learning with Privacy at Scale_** — 两大科技公司用 local DP 做遥测统计的落地案例。理解 central DP 与 local DP 在产品里的取舍。
- **Papernot et al. 2018, _Scalable Private Learning with PATE_** — 用「教师集成 + 带噪投票 + 学生蒸馏」实现 DP 的另一条路线（与 DP-SGD 互补），在有公共未标注数据时效用很好。模块 02 的另一种 DP 训练范式。
- **Mireshghallah et al. 2020, _Privacy in Deep Learning: A Survey_** — 把成员推断、重建、DP、FL、遗忘串成一张图的综述，适合作为本课的鸟瞰地图与延伸阅读索引。

## 本课定位与衔接 · Scope & Cross-links
- ⚠️ **本环境无 GPU、纯 numpy / CPU**：全课用 numpy 从零实现并**对拍**——Laplace / Gaussian 机制对拍其理论期望 / 方差与 ε 经验估计；DP-SGD 对拍非私有 SGD（看效用代价）；联邦 FedAvg 对拍集中式训练（同分布下应几乎一致）；影响函数遗忘对拍真实重训。每个机制都有 `assert` 兜底，保证你写的隐私逻辑**正确**。
- **与姊妹课的分工**：**C12 责任 AI** 只「测量」隐私（成员推断指标、记忆评测）——回答「漏没漏」；**C44 攻击课**站进攻方（窃取 / 重建数据）——回答「怎么漏」；**本课 C45** 站防御方，讲隐私「技术本身」（DP / 联邦 / 遗忘）——回答「怎么防」。三课构成「测量—攻击—防御」的完整闭环。
- **上下游课程**：上游接 C07（ML 基础 / 优化）与 C12（隐私测量）；与 C44（隐私攻击）镜像互补；下游接 C37（MLOps，把隐私管线接进生产）。
