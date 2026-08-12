# 深度学习框架与加速计算工程

这套课里几乎每个机制你都用纯 numpy 从零写过，唯独缺「真实框架是怎么工程化地把它们跑快、跑稳、跑省显存的」——本课补这个洞：用 numpy 复刻 autograd / 编译器 / 函数变换 / 混合精度 / profiler 的内核，真实 PyTorch/JAX/Triton 作对照。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 自动微分内核 | `01_autograd/` |
| 02 | torch.compile 图捕获与编译 | `02_torch_compile/` |
| 03 | JAX/XLA 函数式与变换 | `03_jax_xla/` |
| 04 | 混合精度与显存 | `04_mixed_precision_memory/` |
| 05 | 性能剖析与调试 | `05_profiling_debugging/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）先建立框架内部的机制图景，再跑 `NN_*.ipynb` 用 numpy 从零复刻框架内核：先看 worked 示例 → ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 胶囊兜底自测。自己写一个反向模式 autograd 引擎、一个图捕获 + 算子融合的玩具编译器、一组 `grad`/`vmap` 函数变换、一个混合精度 + loss scaling + 显存账的数值模拟、一个带计时与 NaN 溯源的玩具 profiler——每个内核都与朴素参考实现或数值梯度对拍。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，无需联网 / GPU / API key。真实的 `torch.autograd` / `torch.compile` / `jax` / `autocast` 仅作对照展示：装了 `torch`/`jax` 可选实跑，缺失则自动回退当讲解形态读，不影响任何 assert。

配套：[术语词典](glossary.md) · [参考清单](references.md)
