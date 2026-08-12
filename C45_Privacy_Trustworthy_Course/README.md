# 隐私保护与可信 ML

不止说「重视隐私」，而是会算隐私预算 ε、写 DP-SGD、跑联邦聚合、做并验证机器遗忘：差分隐私、DP-SGD、联邦学习、机器遗忘、可信部署——用 numpy 从零实现并对拍参考，把隐私保护还原成可证明、可度量、可审计的工程。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 可信 ML 总览与环境 | `00_setup/` |
| 01 | 差分隐私 | `01_differential_privacy/` |
| 02 | DP-SGD | `02_dp_sgd/` |
| 03 | 联邦学习 | `03_federated_learning/` |
| 04 | 机器遗忘 | `04_unlearning/` |
| 05 | 可信部署 | `05_trustworthy_deploy/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立威胁模型与防御直觉，再跑 `NN_*.ipynb` 用 numpy 从零实现隐私机制（加噪、裁剪、聚合、遗忘）：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。差分隐私机制对拍其期望与方差、DP-SGD 对拍非私有训练、联邦 FedAvg 对拍集中式、影响函数遗忘对拍重训——每个机制都有 `assert` 兜底。与 C12（测量）、C44（攻击）互补，本课站在防御方。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，无需联网 / GPU / API key，也不依赖 Opacus/Flower 等隐私框架（仅作设计对照提及）。

配套：[术语词典](glossary.md) · [参考清单](references.md)
