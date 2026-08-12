# 对抗 ML 与 AI 安全攻防

防御视角 · 授权安全研究 · 教育用途——讲攻击是为了防御：对抗样本、投毒后门、模型窃取/反演、成员推断、prompt 注入/供应链——纯 numpy 玩具模型 + 合成数据复现每个攻击，每个攻击都配检测与防御三件套。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | AI 安全威胁模型全景 | `00_setup/` |
| 01 | 对抗样本 | `01_adversarial_examples/` |
| 02 | 数据投毒与后门 | `02_poisoning_backdoor/` |
| 03 | 模型窃取与反演 | `03_extraction_inversion/` |
| 04 | 成员推断与隐私 | `04_membership_privacy/` |
| 05 | Prompt 注入与供应链安全 | `05_prompt_injection_supply/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立威胁模型与攻防直觉，再跑 `NN_*.ipynb` 用 numpy 在玩具模型 / 合成数据上复现攻击与配套防御/检测：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。每一个攻击演示都紧跟一个检测器或防御层——理解攻击才能设计防御。所有演示均为小规模、教学性，跑在我们完全掌握真相的玩具分类器上，不提供可武器化产物。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU、玩具模型 + 合成数据，无需联网 / GPU / API key，无任何武器化产物。

配套：[术语词典](glossary.md) · [参考清单](references.md)
