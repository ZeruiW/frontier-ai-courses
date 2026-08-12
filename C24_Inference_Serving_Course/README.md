# 高效推理与服务（vLLM / SGLang 栈） · 前沿 AI 系统培训

> SOTA 前沿课，领先实验室真实在用的推理引擎技术。**不止会调用 vLLM / SGLang，而是理解并能写出它们的核心机制**。
> 中文讲解 + 英文术语；每个模块 = 深度 HTML 讲解 + 纯 numpy「模拟器 + 账本」notebook（worked → ✏️ 练习 + `assert` 判分 → 📖 答案 → 🧪 真实数据胶囊）。**全程 CPU 可跑，无需 GPU。**

## 这门课在讲什么

一次 LLM 推理分两个性格迥异的阶段：**prefill**（并行嚼完 prompt，算力受限）和 **decode**（逐 token 生成，每步重读全部历史 KV，带宽受限）。现代推理引擎让吞吐提升一个数量级，靠的是五根支柱——本课把它们一根根从零拆开、用 numpy 做成**逻辑正确的模拟器**，关键不变量用 `assert` 钉死（分页 KV 读回逐位等于连续存储、投机采样输出分布逐位等于目标模型、radix 命中等于暴力前缀匹配、量化误差随 scale/离群值按理论变化）。

## 模块
| # | 模块 | 你会亲手实现 | Notebook |
|---|------|------|----------|
| 00 | [课程总览与环境](00_setup/) | 两阶段瓶颈、KV 显存账、对拍方法论 | `00_environment_check.ipynb` |
| 01 | [PagedAttention 与 KV 管理](01_paged_attention/) | 分页 KV 管理器、block table 间接寻址、CoW 引用计数、碎片率账本 | `01_paged_attention.ipynb` |
| 02 | [Continuous Batching](02_continuous_batching/) | 静态 vs 连续批处理调度器、吞吐/延迟、chunked prefill、抢占 | `02_continuous_batching.ipynb` |
| 03 | [投机解码](03_speculative/) | speculative sampling 接受/拒绝规则（验证无损）、接受率、期望加速、树形投机 | `03_speculative.ipynb` |
| 04 | [Prefix Cache 与 PD 分离](04_prefix_disagg/) | radix 前缀树（命中 == 暴力匹配）、命中率、PD 资源配比、TTFT/TPOT 分解 | `04_prefix_disagg.ipynb` |
| 05 | [fp8 与量化服务](05_fp8_serving/) | fp8（E4M3/E5M2）cast、INT8/KV 量化、scale 粒度、离群值实验 | `05_fp8_serving.ipynb` |

## 怎么用
1. 先读每个模块的 **HTML 讲解**（`NN_讲解.html`，模块 00 为 `00_overview.html`）建立直觉与数学；
2. 再打开 **notebook** 亲手实现机制、让 ✏️ 练习的 `assert` 通过、对照 📖 参考答案、跑 🧪 真实数据胶囊；
3. 配套 [`glossary.md`](glossary.md)（术语词典）与 [`references.md`](references.md)（论文清单，★ 标必读：Kwon vLLM/PagedAttention、Yu Orca、Leviathan/Chen speculative decoding、Cai Medusa、Zheng SGLang/RadixAttention、Zhong DistServe、Micikevicius FP8 等）。

```bash
pip install -r requirements.txt && jupyter lab
# 或用项目共享 conda 环境： conda activate courses && jupyter lab
```
打开 [`index.html`](index.html) 可从课程主页进入各模块（pager 串环）。

## 定位
- **聚焦机制而非吞吐**：用 numpy 把数据结构、调度逻辑、数值不变量做对做透，而非追求真实 tokens/s。
- **可迁移**：验证过的块表寻址、CoW、迭代级调度、接受采样、radix 匹配、fp8 cast 可一对一对回 vLLM / SGLang / TensorRT-LLM。
- **衔接**：上游接 C01（Transformer/注意力）与 C36（GPU 内核 / FlashAttention）；本课的服务机制 + C36 的 kernel = 现代推理引擎全貌。
