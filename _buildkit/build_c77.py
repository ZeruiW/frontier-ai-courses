#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C77 · 视频与世界模型。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c77_m00, c77_m01, c77_m02, c77_m03, c77_m04, c77_m05

CID = "C77_Video_World_Models_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 总览：时间轴把什么改变了",
     "<strong>视频不是「图像 × T」，而代价是平方的</strong>："
     "$T{=}128, p_t{=}4$ 时注意力代价是单帧的 $\\mathbf{1024}$ 倍，"
     "而「联合 vs 逐帧」的额外因子恰好是 $T$（恒等式）· "
     "<strong>3D 压缩的收益不是「视频的性质」，是时间相关性的函数</strong>："
     "corr$=0$ 时 $1.001/1.000/\\mathbf{0.984}$（<em>3D 反而更差</em>），"
     "corr$=0.99$ 时 $4.490/4.393/3.199$ · "
     "<strong>遮挡悬崖</strong>：历史 $h{\\le}6$ 时误差 $\\approx 1.003$（除均值什么也预测不出），"
     "$h{=}7$ 塌到 $0.310$、$h{=}8$ 到 $0.059$——"
     "<em>一帧给位置，两帧给速度</em> · "
     "所以「长上下文因为相关性长」是错的解释，"
     "<strong>长上下文买到的是可观测性</strong>（AR(1) 的 corr $=0.95$ 而一帧就够）· "
     "<strong>逐帧特征算的 FVD 对帧序的敏感度是 $7.1\\times10^{-15}$</strong>",
     c77_m00),

    ("01_video_latent", "01_讲解.html", "01_video_latent.ipynb",
     "01 · 视频 latent 与 tokenizer：时间维压缩的账",
     "$p_t$ 是唯一能<strong>平方级</strong>换回算力的旋钮（代价 $\\propto 1/p_t^2$），"
     "而它换走的是可观测性 · "
     "<strong>有效相关性 $\\rho^{p_t}$ 给出 $p_t$ 的上限</strong>"
     "（$\\rho_{\\text{eff}}<0.3$ 后时间维已无冗余可用）· "
     "<strong>流式（因果）的代价非单调</strong>：corr$=0$ 时 $0.9984\\times$、"
     "corr$=0.95$ 时峰值 $\\mathbf{1.0308\\times}$、corr$=0.995$ 时又回到 $1.0060\\times$——"
     "<em>两端都便宜，因为未来要么无信息、要么与过去冗余</em> · "
     "代价还<strong>集中在每个 chunk 的最后一帧</strong>（$1.11$/$1.09$/$1.09$ vs 邻居 $1.01$），"
     "而最后一个 chunk 恒为 $1.00$ · "
     "<strong>固定比特预算下「少而大的 token」更划算</strong>："
     "$4$ tok $\\times$ $256$ 码本（$0.534$）胜过 $16$ tok $\\times$ $4$ 码本（$0.843$），"
     "差 $1.58\\times$——而<em>判断码本有没有坍缩要看熵 $/\\log_2 K$，不能看利用率</em>",
     c77_m01),

    ("02_spacetime_attn", "02_讲解.html", "02_spacetime_attn.ipynb",
     "02 · 时空注意力：分解的代价与它的精确边界",
     "分解的节省 $= TS/(S+T)$，<strong>会饱和</strong>（$T$ 从 $256$ 到 $4096$ 只把 "
     "$128\\times$ 提到 $241\\times$，上界是 $S$）· "
     "<strong>分解式注意力 $=$ Kronecker 积</strong>，这是恒等式："
     "$\\Vert(I{\\otimes}A_s)(A_t{\\otimes}I) - A_t{\\otimes}A_s\\Vert = 0$ · "
     "<strong>�prime速运动（任意多个物体、各自多快都行）分解<em>精确</em>可表示</strong>"
     "（误差恰为 $0$），而<strong>加速</strong>需要 Kronecker 秩 $3$–$5$ · "
     "<strong>深度与残差都<em>不</em>提高表达力</strong>——八层带残差仍是秩 $1$，因为 "
     "$(I{+}I{\\otimes}A_s)(I{+}A_t{\\otimes}I) = (I{+}A_t)\\otimes(I{+}A_s)$（差 $0$）· "
     "<strong>并行分支才提高</strong>：秩 $2/4/16$，而饱和值恰为 "
     "$\\mathbf{m^2{-}m{+}1}$（$m{=}\\min(T,S)$，七组配置全部命中）· "
     "这解释了为什么时间层要<strong>加法式</strong>插入而不是串联",
     c77_m02),

    ("03_temporal_drift", "03_讲解.html", "03_temporal_drift.ipynb",
     "03 · 时序一致性与自回归漂移",
     "<strong>「自回归必然漂移」是错的</strong>：误差按 $\\vert\\hat a\\vert^k$ 演化，"
     "$\\vert\\hat a\\vert<1$ 时<em>任何单帧的错误都会被指数地遗忘</em> · "
     "真正累积的是<strong>分布</strong>的错误，而它有两支症状相反的形态 · "
     "<strong>一步拟合（教师强制）对持续性的估计向下有偏</strong>"
     "（$a{=}0.9,n{=}50$ 时中位数 $0.8835$）$\\Rightarrow$ "
     "<strong>rollout 的运动能量只有真值的 $35\\%$–$49\\%$</strong>——"
     "<em>「越往后越糊、越静止」不需要神经网络就已出现，而且是目标函数问题不是能力问题</em> · "
     "而尾部：$a{=}0.995,n{=}30$ 时 <strong>$28.60\\%$ 的拟合给出 "
     "$\\vert\\hat a\\vert>1$</strong>（指数爆炸）· "
     "<strong>方差的中位数 $8.93$ 而均值 $1.408\\times10^{14}$</strong>——差 $16$ 个数量级，"
     "所以长视频指标必须报<strong>中位数 $+$ 崩坏率</strong> · "
     "而<em>「用 rollout 损失修漂移」这条建议被实测限定</em>："
     "它修不了那个偏差，模型正确指定时几乎什么也不改",
     c77_m03),

    ("04_world_model", "04_讲解.html", "04_world_model.ipynb",
     "04 · 世界模型：动作条件、可交互 rollout，与 C41 的分工",
     "<strong>「这个世界模型准不准」没有答案，除非先说清它要被怎么用</strong> · "
     "同一个模型（分布内一步误差 $\\mathbf{0.0395}$）："
     "<strong>被动 rollout 高估奖励 $-13.0\\%$，主动规划高估 $\\mathbf{+251.2\\%}$</strong>——"
     "<em>优化器不是在利用噪声，它是在最大化模型的结构误差</em> · "
     "<strong>动作条件的收益 $=$ 动作在状态变化里占的方差份额</strong>"
     "（$1.01\\times$ 到 $28.23\\times$，有闭式解），"
     "而<strong>喂错动作比不喂动作更糟</strong>（$8$ 种配置全部成立）· "
     "<strong>分布偏移本身不是问题，误配 $\\times$ 偏移才是</strong>："
     "模型匹配时一步误差在策略幅度跨 $30$ 倍下平坦（$+1.9\\%$），误配时涨 $\\mathbf{44}$ 倍 · "
     "而误差 vs 训练量的曲线分出<strong>三</strong>种下界："
     "噪声底（无害）/ 估计误差（加数据有用）/ 逼近误差（加数据无用）",
     c77_m04),

    ("05_video_eval", "05_讲解.html", "05_video_eval.ipynb",
     "05 · 视频评测：FVD 的三个病理与运动口径",
     "FVD 是 FID 的直接搬运，所以继承了它的<strong>三个病理</strong>，而三个是不同类型的失效 · "
     "<strong>① 同分布之间的 FD 恒为正且 $\\propto 1/N$</strong>"
     "（$N$ 跨 $64$ 倍时系数稳定在 $0.577$–$0.583$；$N{=}64,d{=}32$ 时零假设值已是 $9.33$）——"
     "<em>不同 $N$ 下的 FVD 不可比</em>，而 $\\text{FD}_\\infty$ 外推能把它降 $2$ 个数量级 · "
     "<strong>② 只看前两阶矩</strong>：连续单峰 vs 两点分布（峰度 $2.99$ vs $1.00$）"
     "的 FD 是 $0.000587$，而同分布基线是 $0.000603$——<em>比基线还小</em> · "
     "<strong>③ 逐帧特征对帧序<em>结构性</em>免疫</strong>：敏感度 $\\mathbf{7.1\\times10^{-15}}$，"
     "而时空特征是 $0.300$ · "
     "而「用了多少帧」不是判据——<strong>「时间排序后平均」用满全部帧却完全免疫，"
     "「首末帧之差」只用 2 帧却敏感</strong>",
     c77_m05),
]

README = r"""# C77 · 视频与世界模型

> **时间轴上的每一个便宜的近似，都在别处产生一个精确可算的代价。**
>
> 时间压缩换走可观测性（m01）· 分解式注意力换走 Kronecker 秩（m02）·
> 一步拟合换走运动能量（m03）· 被动生成的准确不蕴含抗优化（m04）·
> 逐帧特征换走整个时间维（m05）。
>
> 而这些代价**全都不会报错**。

6 个模块 · 6 个 notebook · 24 道带自测的练习 · 纯 numpy / CPU / 离线 · **不训练任何神经网络**。

## 这门课的边界

**C28（前沿扩散）已经把图像扩散的五块地基讲完了**：latent diffusion、DiT 架构
（patchify / adaLN-zero / 时间步嵌入 / scaling law）、flow matching、CFG、一致性模型。
本课**一概不重讲**。

而 C28 里每一处提到「视频」的地方都是**指向前方的一句带过**：

- 「SoRA 把 DiT 的 2D patch 推广成时空 patch」
- 「视频/3D 的冗余更大，但**时空一致的 VAE 远比图像难**，高质量视频 VAE 仍是瓶颈」
- 「把 CM/对抗蒸馏扩到视频 DiT，是实时视频生成的关键一步」
- 「把 flow matching 推广到视频/3D 的时空流，是把这套框架推向更广领域的前沿」

**本课就是那些「一句带过」的展开。**

另一条边界：**C41 模块 04（基于模型与世界模型）** 拥有规划侧——
MPC 随机打靶、Dyna 的经验混合、模型误差在多步 rollout 中的累积、基于模型 vs 无模型的权衡。
本课只做**生成侧**，并且显式地把两者的失效机制分开（m04 第 2 节）。

| 已被占据 | 归谁 | 本课的分工 |
|---|---|---|
| latent diffusion / DiT / flow matching / CFG / 一致性模型 | **C28** | 不重讲，只推广到时间轴 |
| MPC / Dyna / 规划侧的复合误差 | **C41-04** | 只做生成侧，并量出两者的量级差 |
| 模仿学习的复合误差 | C59 | 不重复 |
| 时序一致性作为**感知**系统的工具 | C55 | 不重复 |

## 五处诚实修正

本课多处结论是在探数阶段被测量结果**推翻后重写**的。这些修正本身是内容的一部分——
其中模块 02 那一处**连错了三次**：

1. **「多个物体各自不同速度就分解不了」——错**（m02）。
   测出来最优 Kronecker 逼近误差**恰为 0**。
   原因：空间重排 $x \mapsto x - v_{\text{owner}(x)}$ 是<u>一个固定矩阵</u>，对所有 $t$ 相同，
   所以 $M = A_t \otimes P$ 仍是 Kronecker 积。
   → 精确的判据是「空间模式与 $t$ 无关、时间模式与 $x$ 无关」，
   所以**分解不了的是加速与变向，不是「多个物体」**。

2. **「多叠几层分解注意力能补回表达力」——错**（m02）。
   Kronecker 积的乘积仍是 Kronecker 积，八层复合的秩**恒为 1**。

3. **「残差连接能补回来」——也错**（m02）。
   $(I + I{\otimes}A_s)(I + A_t{\otimes}I) = (I + A_t) \otimes (I + A_s)$，
   验证到 $0.000\times10^{0}$ —— 顺序 $+$ 残差只是一个<u>更大的</u> Kronecker 积。
   第四次才对：**并行分支**才是表达力的来源（秩 $2/4/16$）。

4. **「多步 / rollout 损失能修 $\hat a$ 的向下偏差」——错**（m03）。
   实测最优 $k$ 在 $\{1, 2, 4\}$ 之间跳，不是系统性的；
   而模型**正确指定**时各 $k$ 的预测误差只差在第 4 位小数。
   → 它的真实作用是在**误配**下把精度从短跨度挪到长跨度，
   而理由是「一步拟合的模型在 $H{=}4$ 时误差 $1.028 > 1.0$ ——**比直接预测均值还差**」。

5. **「动作分布偏移会被 rollout 放大」——不成立**（m04）。
   模型**匹配**时一步误差在策略幅度跨 30 倍下完全平坦（$0.05360 \to 0.05461$，$+1.9\%$）。
   → 统一的说法：**分布偏移本身不是问题，误配 × 偏移才是**
   （误配时同样的偏移让误差涨 44 倍）。
   这也解释了为什么「加大训练动作范围」有效而「加大数据量」无效。

另有两处方法层的修正：**平稳性诊断必须在一批序列上做**
（单条 $s_2/s_1$ 在 $T{=}400$ 时 p5–p95 跨 $0.67$–$1.59$，而批级中位数是 $0.998 \pm 0.046$）；
**能量比必须相对一批真实序列算**，因为 sd 估计量的中位数本身只有真值的 $0.885$。

## 两处意外收获

1. **并行分支的 Kronecker 秩饱和值有闭式：$m^2 - m + 1$，$m = \min(T,S)$**（m02）。
   七组配置（$m = 3,4,5,6$）全部精确命中（$7, 13, 21, 31$），
   而它**严格小于**朴素上界 $\min(T^2, S^2)$（$m{=}5$ 时是 21 而不是 25）。

2. **FVD 的盲区取决于特征，而好的特征能把高阶差别搬进前两阶**（m05）。
   一个均值、方差、时间相关性**全部匹配**、只有峰度从 3 变成 1 的模式坍缩：
   FVD(逐帧) 的比值是 $0.80$（**低于**同分布基线，完全盲），
   而 FVD(时空) 放大 $20.9\times$ —— 机制很具体：
   $\vert\Delta\vert$ 这个特征把一个**四阶矩**差别转成了**一阶矩**差别。

## 贯穿全课的线

**时间轴上的每一个便宜的近似，都在别处产生一个精确可算的代价，而它不会报错。**

| 近似 | 换走了什么 | 精确的代价 | 位置 |
|---|---|---|---|
| 时间压缩 $p_t$ | 可观测性 | $\rho_{\text{eff}} = \rho^{p_t}$；latent 帧数 $T/p_t$ | m01 |
| 逐帧独立处理 | 时间冗余 | 3D 收益 $= f(\text{corr})$，corr$=0$ 时为**负** | m00 |
| 分解式时空注意力 | Kronecker 秩 | 加速需秩 $3$–$5$，而串联恒为 $1$ | m02 |
| 串联接线（vs 并行） | 全部时空交互 | 秩 $1$ vs $m^2{-}m{+}1$ | m02 |
| 一步拟合（教师强制） | 运动能量 | rollout 方差只有真值的 $35\%$–$49\%$ | m03 |
| 「一步准就是好模型」 | 抗优化 | $3.95\%$ 的一步误差 → $251\%$ 的回报高估 | m04 |
| 逐帧特征算 FVD | 整个时间维 | 帧序敏感度 $7.1\times10^{-15}$ | m05 |

## 本课包含它自己配置不通过的验收项

这是刻意的设计（与 C72–C76 一致）：

- **m01 第 3 节**：因果代价的「峰值在 chunk 最后一帧」这条结论**在 $s{=}2$ 时不成立**
  （chunk 内两帧的比值只差 $<5\times10^{-3}$，argmax 是噪声）。成立范围是 $s \geq 3$。
- **m02 第 4 节**：整套 Kronecker 分析是**线性算子**层面的。
  真实网络的注意力权重依赖输入、block 间还有非线性 MLP，两者都能突破这里的界。
  所以它给出的是「不依赖非线性也能做到什么」的下界，
  **不**证明串联式分解注意力的网络学不会加速运动。
- **m03 练习 1**：「多步损失修漂移」这条流行建议在本课的三项测试里
  **两项失败一项成立**（不修 $\hat a$ 的偏差、正确指定时白做、误配时才有用）。
- **m04 第 4 节**：$10$ 步误差那两列有**混淆因素**——
  $g{=}3$ 时闭环系统本身不稳定（$\rho(A + B \cdot 3K) > 1$），
  所以真实与模型轨迹都发散，那个 $199.86$ 里有很大一部分不是模型误差。
  干净的信号在**一步**那两列。
- **m04 练习 4**：四项验收「互不蕴含」这句话**被部分推翻**——
  ① 与 ② 是**耦合**的（动作通道退化时一起坏，没有哪个缩放能让 ① 过而 ② 不过）。
  仍然成立的是 ① 不蕴含 ③、① 不蕴含 ④。
- **m05 练习 2**：覆盖率**不是** FVD 盲区的万能补丁——
  在矩匹配的坍缩上它只降到 $0.90\times$。
  它的强项是「完全没覆盖到某些区域」，而不是「覆盖了但形状不对」。

## 模块

| 模块 | 主题 | notebook | 关键量 |
|---|---|---|---|
| 00 | 总览：时间轴把什么改变了 | `00_environment_check.ipynb` | 代价 $1024\times$；3D 收益 $0.984$–$4.490$；遮挡悬崖 $1.003 \to 0.310$ |
| 01 | 视频 latent 与 tokenizer | `01_video_latent.ipynb` | 流式代价峰值 $1.0308\times$（非单调）；比特预算 $1.58\times$ |
| 02 | 时空注意力 | `02_spacetime_attn.ipynb` | 分解 $=$ Kronecker（差 $0$）；饱和 $m^2{-}m{+}1$ |
| 03 | 时序一致性与漂移 | `03_temporal_drift.ipynb` | 方差比 $0.35$–$0.49$；$28.6\%$ 爆炸；均值/中位数差 $10^{16}$ |
| 04 | 世界模型 | `04_world_model.ipynb` | $-13\%$ vs $+251\%$；条件化收益 $1.01$–$28.23\times$ |
| 05 | 视频评测 | `05_video_eval.ipynb` | FD $\propto 1/N$；矩匹配盲区；帧序敏感度 $7.1\times10^{-15}$ |

## 怎么用

```bash
pip install -r requirements.txt
jupyter lab            # 或 jupyter notebook
```

按 `00 → 01 → … → 05` 顺序读。每个 notebook 都是自包含的，
含 4 个练习（TODO 桩 + 自测断言）、参考答案与一个真实工程胶囊。

**只有两小时**：读 **m02 第 4 节**（分解式注意力的 Kronecker 秩——
那里有三个连续的、被数值推翻的猜想）+ **m04 第 2 节**（$-13\%$ vs $+251\%$），
跑 **m03 的 notebook**（那里能看到「生成的视频越往后越静止」这个现象
在不需要任何神经网络的情况下就已经出现了）。

## 为什么不训练神经网络

本课要说明的性质——压缩率、Kronecker 秩、谱半径、矩匹配、有限样本偏差——
**都在线性代数与统计层面**。用网络反而会把它们藏起来：
一个训练好的视频模型里，「分解式注意力表达不了加速」这件事会表现为
「某些样本的运动看起来不对」，而不会表现为一个可以断言的秩。

代价是本课不覆盖任何与训练有关的工程（并行、显存、调度、数据管线）。

## 数据

**不需要任何真实视频。** 全部数据生成过程的真值
（时间相关性、遮挡区间、混合矩阵、谱半径、动作影响、特征的矩）都是已知的——
这正是能判断一个近似对错的唯一前提。

## 相关课程

- **C28** —— 图像扩散的全部地基（本课的硬前提，且不重复）
- **C41 模块 04** —— 基于模型 RL 与规划侧的复合误差（本课 m04 的对照）
- **C59** —— VLA / 模仿学习里的复合误差（第三种同名不同义的「误差累积」）
- **C55** —— 时序一致性作为感知系统的工具（与生成侧完全不同的用途）
- **C14** —— 评测与度量（那里把「视频评测的时序一致性」列为开放问题，本课把它做完一半）
- **C72–C75** —— 三维全链路（另一个「几何 + 生成」的方向）
"""

REQUIREMENTS = """numpy>=1.24
jupyterlab>=4.0

# 本课全部计算为纯 numpy / CPU / 离线：
#   · 无 GPU、无网络、无外部数据集
#   · **不训练任何神经网络** —— 要说明的性质都在线性代数与统计层面
#     （压缩率、Kronecker 秩、谱半径、矩匹配、有限样本偏差）
#   · 无 torch / scipy / sklearn —— PCA 用 numpy 的 SVD，
#     VQ 用手写 k-means（并且刻意用 matmul 形式算距离，见模块 01）
#   · matplotlib 不是必需的（全部输出为数值表格，便于断言）
"""

GLOSSARY = r"""# C77 术语词典 · 视频与世界模型

按「概念 → 定义 → 本课的量化」组织。**加粗**的是本课重点验证过的。

## 一、时间轴的代价

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 时空 patch | spatiotemporal patch | 把视频切成 $p_t \times p_h \times p_w$ 的小立方体当 token | $n = (T/p_t)S$ |
| 时间压缩率 | temporal compression | $p_t$ | **唯一能平方级换算力的旋钮**（$\propto 1/p_t^2$）|
| 相对单帧的注意力代价 | — | $(T/p_t)^2$ | **与空间分辨率无关**（恒等式）|
| 联合 vs 逐帧的额外因子 | — | $(TS)^2/(TS^2)$ | 恰好 $= T$（恒等式）|
| 有效相关性 | effective correlation | $\rho_{\text{eff}} = \rho^{p_t}$ | $<0.3$ 后时间维无冗余可用 |
| 3D 压缩的收益 | — | 逐帧 2D 误差 / 联合 3D 误差 | corr$=0$ 时 **$0.984$（负收益）**，corr$=0.99$ 时 $4.490$ |
| 因果 tokenizer | causal tokenizer | latent 只依赖过去的帧 | 流式的前提；代价 $\leq 3.3\%$ |
| 流式的代价 | streaming cost | 因果误差 / 非因果误差 | **非单调**：峰值 $1.0308\times$ 在 corr$\approx0.95$ |
| chunk 边界效应 | — | 代价在 chunk 内的分布 | **峰值在最后一帧**（$s \geq 3$ 时）|
| 码本 | codebook | VQ 的离散码字集合 | 固定比特下「少而大」优 $1.58\times$ |
| 码本坍缩 | codebook collapse | 大量码字从不被使用 | 判据是**熵 $/\log_2 K$**，不是利用率 |
| 有效码本大小 | effective codebook size | $2^H$（$H$ 为码字使用分布的熵）| 利用率 $100\%$ 时它仍可远小于 $K$ |

## 二、可观测性

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 马尔可夫性 | Markov property | 未来只依赖当前状态 | AR(1) 上一帧就够（$h{=}2$ 改善 $1.000\times$）|
| 过程的阶 | order of the process | 需要几帧历史 | AR(2) 的改善恰在 $h{=}1{\to}2$（$2.295\times$）后持平 |
| 遮挡 | occlusion | 观测暂时不可用 | 本课构造 $[6,12)$ 的完全遮挡 |
| 可观测性 | observability | 状态能否从观测序列反推 | 遮挡期间观测矩阵为零，秩 $= 0$ |
| **遮挡悬崖** | occlusion cliff | 窗口够到遮挡前时误差突降 | $h{\le}6$: $1.003$；$h{=}7$: $\mathbf{0.310}$；$h{=}8$: $0.059$ |
| 所需上下文长度 | required context | $\geq$ 最长不可观测区间 $+2$ | 一帧给位置，**两帧给速度** |
| 上下文需求的局部性 | — | 它取决于预测哪一帧 | $t_{\text{pred}} = t_1$ 时 $h^{*} = t_1{-}t_0{+}1$；$t_{\text{pred}} > t_1$ 时 $h^{*} = 1$ |

## 三、时空注意力

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 完全 3D 注意力 | full 3D attention | 一个 $n \times n$，$n = TS$ | $(TS)^2$ |
| 分解式注意力 | factorized attention | 空间注意力 $+$ 时间注意力 | $TS(S+T)$；节省 $= TS/(S{+}T)$ |
| 节省的饱和 | — | 分解的收益有上界 | 上界 $= S$；$T{=}4096$ 时只到 $241\times$ |
| 时空窗口 | spatiotemporal window | 只在 $w_t \times w_s$ 邻域注意 | $TS w_t w_s$；节省 $\propto TS$（**不饱和**）|
| 代价交叉点 | crossover | 窗口比分解便宜的最小 $T$ | 闭式 $T^{*} = w_t w_s - S + 1$ |
| **Kronecker 积** | Kronecker product | $A \otimes B$ | 分解 $=$ $A_t \otimes A_s$（**恒等式**，差 $0$）|
| Van Loan–Pitsianis 重排 | rearrangement | 把 $M$ 排成 $R$ 使 $\text{rank}(R) = $ Kronecker 秩 | 本课全部结论的读数来源 |
| Kronecker 秩 | Kronecker rank | 表示 $M$ 所需的 $A\otimes B$ 项数 | 分解 $=1$；完全 3D $= \min(T^2,S^2)$ |
| 最近 Kronecker 逼近 | nearest Kronecker approx | $R$ 除最大奇异值外的能量 | 匀速 $= 0$；加速 $= 0.79$–$0.94$ |
| **可分解性的判据** | — | 空间模式与 $t$ 无关 **且** 时间模式与 $x$ 无关 | 匀速（任意多物体）可分解；**加速不可** |
| 串联 vs 并行 | serial vs parallel | $(I{+}A)(I{+}B)$ vs $I{+}A{+}B$ | 串联恒为秩 $1$；并行按 $2^L$ 增长 |
| **秩的饱和值** | — | 并行分支能达到的上限 | $\mathbf{m^2{-}m{+}1}$，$m = \min(T,S)$（七组验证）|
| 加法式插入 | additive insertion | $x \leftarrow x + \alpha\,\text{attn}_t(x)$ | 秩 $>1$；而串联式插入锁在 $1$ |
| 全局连通所需跳数 | hops to connect | 可达性覆盖全部 token 对 | 完全 3D $=1$；分解 $=2$；窗口 $= \max\lceil\cdot/\lfloor w/2\rfloor\rceil$ |

## 四、自回归漂移

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 教师强制 | teacher forcing | 训练时输入真实的上一帧 | 一步最小二乘是它的解析解 |
| 误差增长律 | error growth law | $\vert\hat a\vert^k \delta$ | $\vert\hat a\vert<1$ 时**指数遗忘**（几何级数）|
| 谱半径 | spectral radius | $\rho(\hat A)$ | $>1$ 是**所有**用途的否决项 |
| AR 系数的向下偏差 | downward bias of $\hat a$ | $E[\hat a] - a \approx -(1{+}3a)/n$ | $a{=}0.9,n{=}50$: 偏差 $-0.033$（理论 $-0.074$）|
| 运动能量的缺口 | — | rollout 稳态方差 / 真值 | **$0.354$–$0.492$**（$a{=}0.98$）|
| 不稳定拟合的比例 | — | $P(\vert\hat a\vert>1)$ | $a{=}0.995,n{=}30$: **$28.60\%$** |
| 均值 vs 中位数 | — | 崩坏样本对均值的主导 | $1.408\times10^{14}$ vs $8.93$（差 $10^{16}$）|
| 崩坏率 | collapse rate | 任一帧超出训练分布 $\times$ 倍 | 与中位数**缺一不可** |
| 不动点 | fixed point | 稳态分布 $N(0, \sigma^2/(1{-}a^2))$ | 噪声尺度错 $\Rightarrow$ 不动点错，**不自我纠正** |
| 收缩性 vs 正确性 | — | 「初值不重要」$\neq$「收敛到正确分布」 | 两者常被混为一谈 |
| 平稳性诊断 | stationarity check | 前后半段方差是否一致 | **必须在批上做**（单条 p5–p95 跨 $0.67$–$1.59$）|
| 多步 / rollout 损失 | multi-step loss | 训练时对 $k$ 步 rollout 计损失 | **不修** $\hat a$ 的偏差；正确指定时白做 |
| 锚帧 | anchor frame | 每 $m$ 步用给定帧重置 | 误差从 $\vert\hat a\vert^T$ 变成 $\vert\hat a\vert^{\leq m}$ |
| 层次化生成 | hierarchical generation | 一次性生成小段 $+$ 锚帧拼接 | 段内无漂移，段间 $T/m$ 步 |

## 五、世界模型

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 世界模型（两义） | world model | 规划器的环境 / 可交互的生成器 | 失效机制不同：**对抗性** vs **分布性** |
| 动作条件 | action-conditioned | 预测器同时看状态与动作 | 收益 $=$ 动作占的方差份额 |
| 条件化收益的闭式 | — | $\sqrt{(\text{tr}(B\Sigma_a B^\top) + d\sigma^2)/(d\sigma^2)}$ | 与模拟吻合到 $20\%$ 内（8 组）|
| 喂错动作的惩罚 | wrong-action penalty | 错动作误差 / 不给动作误差 | $>1$（8 组全部）—— **比不喂更糟** |
| 潜在动作 | latent action | 从无标注视频反推的动作 | 推断错误**不是无害噪声** |
| 模型被利用 | model exploitation | 优化器最大化模型的结构误差 | 一步误差 $0.0395$ → 回报高估 $251\%$ |
| 抗优化测试 | adversarial test | 用模型规划再在真系统执行 | 必须报告用的**动作范围** |
| 逼近误差 | approximation error | 模型类与真映射的距离 | **加数据修不了**（饱和在 $1.69$）|
| 估计误差 | estimation error | 有限样本造成的 | 加数据有效（$0.042 \to 0.015$）|
| 观测噪声底 | noise floor | 不可约的观测噪声 | 第**三**种下界（$g{=}0$ 时主导）|
| 误配 × 偏移 | misspecification × shift | 危险来自两者的**乘积** | 匹配时偏移无害（$+1.9\%$），误配时 $44\times$ |

## 六、视频评测

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| FVD | Fréchet Video Distance | FID 搬到视频特征上 | 继承 FID 的**三个病理** |
| Fréchet 距离 | Fréchet distance | $\Vert\mu_r{-}\mu_g\Vert^2 + \text{tr}(\Sigma_r{+}\Sigma_g{-}2(\Sigma_r\Sigma_g)^{1/2})$ | 只用到前两阶矩 |
| 有限样本偏差 | finite-sample bias | 同分布之间的 FD 恒为正 | $\propto 1/N$（$N$ 跨 $64$ 倍系数稳定）|
| 零假设值 | null value | 同分布下的 FD | $N{=}64,d{=}32$ 时已是 $9.33$ |
| $\text{FD}_\infty$ | FID-infinity | 对 $1/N$ 外推到 $N\to\infty$ | 把偏差降 $2$ 个数量级；绝对残差 $\leq 0.08$ |
| 矩匹配盲区 | moment-matching blindness | 同 $\mu$ 同 $\Sigma$ 则 FD $\approx 0$ | 峰度 $2.99$ vs $1.00$，FD $0.000587$（基线 $0.000603$）|
| 模式坍缩 | mode collapse | 只产出少数模式 | 恰好落在 FVD 盲区 |
| 覆盖率 / recall | coverage | $k$-NN 半径内有无生成样本 | **不是万能补丁**（矩匹配坍缩上只降 $0.90\times$）|
| **帧序置换检验** | frame-order permutation test | 打乱帧序看指标变不变 | 逐帧特征 $\mathbf{7.1\times10^{-15}}$；时空 $0.300$ |
| 结构性免疫 | structural invariance | 指标恒等于不变，而非不敏感 | 时间平均之后帧序**已不存在** |
| 「用了多少帧」不是判据 | — | 用满全部帧仍可免疫 | 「时间排序后平均」免疫；「首末帧之差」敏感 |
| 特征决定盲区 | — | 好特征把高阶差别搬进前两阶 | $\vert\Delta\vert$ 把四阶差别转成一阶（$20.9\times$）|
| 分维度打分 | per-dimension scoring | 把一个数拆成一组 | VBench 一类做法的动机 |

## 七、诊断量速查

| 量 | 在哪 | 阈值 / 解读 |
|---|---|---|
| $(T/p_t)^2$ | m00 | 相对单帧的注意力代价，与分辨率无关 |
| 3D/2D 误差比 | m00 / m01 | $\leq 1$ 时不该用 3D 压缩 |
| $\rho$（相邻帧相关性）| m01 | 按**镜头**估、用**中位数** |
| $\rho^{p_t}$ | m01 | $<0.3$ 时时间维已无冗余 |
| latent 帧数 $T/p_t$ | m01 | 需 $\geq \lceil\text{occl}/p_t\rceil + 2$ |
| 熵 $/\log_2 K$ | m01 | $<0.7$ 时码本已坍缩 |
| Kronecker 秩 | m02 | $1$ $\Rightarrow$ 只能表示「时间模式 $\otimes$ 空间模式」 |
| 全局连通跳数 | m02 | 分解 $2$；窗口随序列长增长 |
| $\rho(\hat A)$ | m03 | $>1$ 是所有用途的否决项 |
| rollout 方差 / 真值 | m03 | $<1$ $\Rightarrow$ 运动能量不足 |
| 崩坏率 | m03 | 与中位数**缺一不可** |
| 批级 $s_2/s_1$ | m03 | 平稳 $\Rightarrow$ 不动点错；不平稳 $\Rightarrow$ 还在累积 |
| 抗优化相对高估 | m04 | 必须连同**动作范围**一起报 |
| 误差 vs 训练量的曲线 | m04 | **在什么水平上变平**区分三种下界 |
| 错动作惩罚 | m04 | $>1$ $\Rightarrow$ 动作条件是真的在起作用 |
| FD 零假设值 | m05 | 不同 $N$ 下的 FVD 不可比 |
| 帧序敏感度 | m05 | $<10^{-9}$ $\Rightarrow$ 该指标不在评时间维 |
"""

REFERENCES = r"""# C77 参考文献 · 视频与世界模型

按模块组织。每条注明**它在本课的哪个具体结论上被用到**。

---

## 模块 00 · 总览

- **OpenAI.** *Video generation models as world simulators.* Sora 技术报告, 2024.
  → 「时空 patch」这个说法的来源，也是把「视频生成」与「世界模型」放在同一篇文档里的
  最有影响力的一次。本课 m00 的 token 账与 m04 的两义之分都以它为背景。

- **Ho, J., Salimans, T., Gritsenko, A., Chan, W., Norouzi, M. & Fleet, D.**
  *Video Diffusion Models.* NeurIPS 2022.
  → 把扩散推广到视频的第一批系统工作，包含 3D U-Net 与自回归长视频扩展。
  本课 m00/m03 的问题设定来自它。

- **Blattmann, A. et al.** *Align your Latents: High-Resolution Video Synthesis with
  Latent Diffusion Models.* CVPR 2023.
  → **时间层的加法式插入**（在预训练图像模型上加时间注意力，$\alpha$ 初始化为 0）。
  本课 m02 第 4 节给出这个设计选择的 Kronecker 秩解释——
  它不只是为了训练稳定，它决定了整个网络能不能表达「空间往哪看取决于第几帧」。

- **Bertasius, G., Wang, H. & Torresani, L.** *Is Space-Time Attention All You Need
  for Video Understanding?* ICML 2021（TimeSformer）.
  → 分解式时空注意力的代表性工作，也是 m02 全部分析的对象。

---

## 模块 01 · 视频 latent 与 tokenizer

- **Rombach, R., Blattmann, A., Lorenz, D., Esser, P. & Ommer, B.**
  *High-Resolution Image Synthesis with Latent Diffusion Models.* CVPR 2022.
  → 图像侧的地基（见 **C28 模块 01**）。本课不重讲，只处理时间维。

- **Yu, L. et al.** *Language Model Beats Diffusion — Tokenizer is Key to Visual
  Generation.* ICLR 2024（MAGVIT-v2）.
  → 「tokenizer 是关键」这个论断，以及无查找量化（LFQ）。
  本课 m01 第 4 节的比特预算账是它那条论断的一个最小可执行版本。

- **Yu, L. et al.** *MAGVIT: Masked Generative Video Transformer.* CVPR 2023.
  → 3D VQ tokenizer。本课 m01 的「少而大的 token」结论对应它的时空 patch 设计。

- **Agarwal, N. et al.** *Cosmos World Foundation Model Platform for Physical AI.*
  NVIDIA, 2025.
  → **因果**时空 tokenizer 的工业实现（为流式与「无限长」设计）。
  本课 m01 第 3 节量出因果性的代价（$\leq 3.3\%$ 且非单调），
  并指出它的真实成本在别处：不能与图像 VAE 共享权重、以及 chunk 边界的接缝。

- **van den Oord, A., Vinyals, O. & Kavukcuoglu, K.** *Neural Discrete
  Representation Learning.* NeurIPS 2017（VQ-VAE）.
  → 离散 tokenizer 的原始形式，以及码本坍缩问题的起点。

- **Zhu, Y. et al.** *Scaling the Codebook Size of VQ-GAN to 100,000 with a
  Utilization Rate of 99%.* NeurIPS 2024.
  → 码本利用率的工程处理。本课 m01 练习 4 指出**利用率不是坍缩的正确判据**
  （利用率可接近 100% 而分布极度不均），应看熵 $/\log_2 K$。

---

## 模块 02 · 时空注意力

- **Peebles, W. & Xie, S.** *Scalable Diffusion Models with Transformers.* ICCV 2023（DiT）.
  → DiT 架构与它的 scaling law（见 **C28 模块 02**）。本课不重讲。

- **Arnab, A., Dehghani, M., Heigold, G., Sun, C., Lučić, M. & Schmid, C.**
  *ViViT: A Video Vision Transformer.* ICCV 2021.
  → 系统对照了四种时空注意力分解方式。本课 m02 把其中「分解 vs 完全 3D」这一对
  的表达力差别算成了一个 Kronecker 秩的问题。

- **Liu, Z. et al.** *Video Swin Transformer.* CVPR 2022.
  → 时空窗口注意力。本课 m02 第 5 节与练习 2/4 指出
  **窗口的 Kronecker 秩也是 1** ——
  它换来的是局部性归纳偏置与内存局部性，不是表达力。

- **Van Loan, C. & Pitsianis, N.** *Approximation with Kronecker Products.*
  In *Linear Algebra for Large Scale and Real-Time Applications*, 1993.
  → 最近 Kronecker 逼近的 SVD 解法（重排 + SVD）。
  **本模块全部定量结论都是这个重排 SVD 的直接读数。**

- **Vaswani, A. et al.** *Attention Is All You Need.* NeurIPS 2017.
  → 残差连接与「加法式」子层的来源。m02 第 4 节说明这个接线方式
  （并行接在残差流上而不是串成链）恰恰是分解式时空注意力表达力的来源。

- **注**：本课 m02 练习 3 给出的饱和律 $m^2 - m + 1$（$m = \min(T,S)$）
  是探数阶段实测出来的（七组配置精确命中），**本课不给推导**。
  它与「$m \times m$ 矩阵生成的代数的维数」有关，但严格的表述超出本课范围。

---

## 模块 03 · 时序一致性与自回归漂移

- **Kendall, M.** *Note on Bias in the Estimation of Autocorrelation.*
  Biometrika 41, 1954. · **Marriott, F. & Pope, J.** *Bias in the Estimation of
  Autocorrelations.* Biometrika 41, 1954.
  → $E[\hat a] - a \approx -(1+3a)/n$ 的来源。
  本课 m03 第 2 节把它与「生成的视频越往后越静止」直接连起来：
  一步拟合系统性低估持续性 $\Rightarrow$ rollout 的运动能量只有真值的 $35\%$–$49\%$。

- **Bengio, S., Vinyals, O., Jaitly, N. & Shazeer, N.** *Scheduled Sampling for
  Sequence Prediction with Recurrent Neural Networks.* NeurIPS 2015.
  → 「训练时按概率喂模型自己的输出」。本课 m03 第 5 节把它与多步损失、锚帧、
  一次性生成放在同一张表里，按「修哪一支」区分。

- **Ross, S. & Bagnell, D.** *Efficient Reductions for Imitation Learning /
  DAgger.* AISTATS 2010 / 2011.
  → 自回归 rollout 的分布偏移与它的 $O(H^2)$ 界。
  与 **C59**（VLA / 模仿学习）呼应；本课只做生成侧。

- **Harvey, W., Naderiparizi, S., Masrani, V., Weilbach, C. & Wood, F.**
  *Flexible Diffusion Modeling of Long Videos.* NeurIPS 2022.
  → 层次化 / 关键帧条件生成。本课 m03 练习 3 把锚帧的收益算成
  「误差从 $\vert\hat a\vert^T$ 变成 $\vert\hat a\vert^{\leq m}$」，
  并给出所需锚帧间隔的闭式 $m \leq 1 + \ln F/\ln\vert\hat a\vert$。

- **Villegas, R. et al.** *Phenaki: Variable Length Video Generation from Open
  Domain Textual Descriptions.* ICLR 2023.
  → 变长自回归视频生成的代表工作，也是「长视频靠自回归拼」这条路线的实例。

- **本课程 C41 模块 04** —— 规划侧的复合误差。
  本模块处理的是**生成侧**（分布性失效），两者的分界在 m04 第 2 节被量化。

---

## 模块 04 · 世界模型

- **Ha, D. & Schmidhuber, J.** *World Models.* NeurIPS 2018.
  → 「世界模型」这个词在深度学习语境里的起点（VAE + RNN + 控制器）。

- **Hafner, D., Lillicrap, T., Ba, J. & Norouzi, M.** *Dream to Control: Learning
  Behaviors by Latent Imagination.* ICLR 2020. ·
  **Hafner, D. et al.** *Mastering Diverse Control Tasks through World Models.*
  Nature 2025（DreamerV3）.
  → 「在 latent 空间里想象」这条线。见 **C41 模块 04**；本课不重讲规划部分。

- **Bruce, J. et al.** *Genie: Generative Interactive Environments.* ICML 2024.
  → 从**无标注**视频里学潜在动作。本课 m04 第 3 节对它有一条直接含义：
  潜在动作的推断错误**不是无害的噪声**——
  实测「喂错动作比不喂动作更糟」在 8 种配置上全部成立，
  所以这类系统必须额外报告**潜在动作的可辨识性**，而不只是重建质量。

- **Valevski, D., Leviathan, Y., Arar, M. & Fruchter, S.**
  *Diffusion Models Are Real-Time Game Engines.* 2024（GameNGen）.
  → 「可交互视频」的代表实现（实时、动作条件、长 rollout）。
  本课 m04 的「四项验收」正是针对这类系统设计的。

- **Yu, L. et al.** *Cosmos World Foundation Model Platform.* NVIDIA, 2025.
  → 把世界模型当作基础模型来做的工程平台，含 tokenizer、后训练与评测。

- **Kidambi, R., Rajeswaran, A., Netrapalli, P. & Joachims, T.**
  *MOReL: Model-Based Offline RL.* NeurIPS 2020. ·
  **Yu, T. et al.** *MOPO: Model-based Offline Policy Optimization.* NeurIPS 2020.
  → 「模型被利用」的标准应对（悲观化 / 不确定性惩罚）。
  本课 m04 第 2 节量出这个问题的量级（一步误差 $3.95\%$ → 回报高估 $251\%$），
  而具体的悲观化方法属于 **C41 模块 04** 的范围。

- **Chua, K., Calandra, R., McAllister, R. & Levine, S.**
  *Deep Reinforcement Learning in a Handful of Trials using Probabilistic
  Dynamics Models.* NeurIPS 2018（PETS）.
  → 用模型集合的不一致性来限制规划。与本课 m04 练习 1
  「限制规划时的动作范围」是同一思路的两种实现。

---

## 模块 05 · 视频评测

- **Unterthiner, T., van Steenkiste, S., Kurach, K., Marinier, R., Michalski, M.
  & Gelly, S.** *Towards Accurate Generative Models of Video: A New Metric &
  Challenges.* 2018 / *FVD: A new Metric for Video Generation*, ICLR 2019 Workshop.
  → FVD 的出处。本课 m05 量的三个病理都是它从 FID 继承来的。

- **Heusel, M., Ramsauer, H., Unterthiner, T., Nessler, B. & Hochreiter, S.**
  *GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash
  Equilibrium.* NeurIPS 2017（FID）.
  → Fréchet 距离作为生成质量度量的原始形式，以及「只用前两阶矩」这个设计选择。

- **Chong, M. & Forsyth, D.** *Effectively Unbiased FID and Inception Score and
  Where to Find Them.* CVPR 2020.
  → 有限样本偏差与 $\text{FID}_\infty$（对 $1/N$ 外推）。
  本课 m05 练习 1 实现它，并量出：外推把 $N{=}64$ 的偏差降 2 个数量级，
  但它有一个**绝对**精度底（本设定下约 $0.08$），小于它的效应分辨不出。

- **Ge, S., Mahapatra, A., Parmar, G., Zhu, J.-Y. & Huang, J.-B.**
  *On the Content Bias in Fréchet Video Distance.* CVPR 2024.
  → 实证地说明标准 FVD 主要反映**单帧内容**而不是运动
  （用「打乱帧序的真实视频」都能拿到很好的 FVD）。
  本课 m05 第 4 节给出这个现象的**最小可复现核心**：
  逐帧特征对帧序的敏感度是 $7.1\times10^{-15}$——一个恒等式，而不是一个经验观察。

- **Kynkäänniemi, T., Karras, T., Laine, S., Lehtinen, J. & Aila, T.**
  *Improved Precision and Recall Metric for Assessing Generative Models.*
  NeurIPS 2019.
  → 把保真与多样分开的 $k$-NN 类指标。本课 m05 练习 2 用它的一个最简版本
  补 FVD 的矩匹配盲区，并诚实指出**它不是万能补丁**
  （在矩匹配的坍缩上只降到 $0.90\times$）。

- **Huang, Z. et al.** *VBench: Comprehensive Benchmark Suite for Video
  Generative Models.* CVPR 2024.
  → 把视频质量拆成 16 个维度。本课 m05 第 5 节把它作为「把一个数拆成一组」
  这条对策的代表，但不复现基准本身（它需要真实模型与人工标注）。

- **本课程 C14（评测与度量）** —— 那里把「文生图/视频的评测要同时管保真、多样、
  与提示的对齐、以及时序一致性」列为开放问题。本课把**时序**那一半做完：
  给出一个可执行的判据（帧序置换检验）与三个病理的量化。

---

## 与本课程其他课的关系

- **C28 · 前沿扩散** —— latent diffusion、DiT、flow matching、CFG、一致性模型。
  本课的**硬前提**，且本课一概不重讲。C28 里每一处提到「视频」的地方都是
  指向本课的一句带过。
- **C41 模块 04 · 基于模型与世界模型** —— MPC / Dyna / 规划侧的复合误差。
  本课只做生成侧，并在 m04 第 2 节把两者的失效机制量化区分
  （被动 $-13\%$ vs 主动 $+251\%$）。
- **C59 · VLA 与具身** —— 模仿学习里的复合误差。
  这是第三种同名不同义的「误差累积」（本课 m03 是生成侧、C41-04 是规划侧）。
- **C55 · TSR 感知** —— 那里的「时序一致性」是一个**感知系统**的工具
  （时序累积换单帧信息、时序一致性挖长尾、运动一致性做误检过滤），
  与本课的生成侧完全不同。
- **C14 · 评测与度量** —— 视频评测的开放问题在那里被提出。
- **C20 · SSM** —— 那里的「因果卷积」是把递推展开的另一种视角，
  与本课 m01 的时间维因果压缩是不同的概念。
- **C35 · 语音** —— 流式因果卷积与 RVQ 在音频上的实现，
  与本课 m01 的视频 tokenizer 是同一类工程问题的两个领域。
- **C72–C75 · 三维全链路** —— 另一个「几何 + 生成」的方向。
  C75 的 SDS 一节与本课 m04 的「优化会找模型的洞」是同一现象的两种形态。
"""


def build():
    install_assets(DIR)
    for i, (folder, html_name, nb_name, h1, subtitle, mod) in enumerate(MODULES):
        prev = nxt = None
        if i > 0:
            p = MODULES[i - 1]; prev = ("../%s/%s" % (p[0], p[1]), p[3])
        if i < len(MODULES) - 1:
            n = MODULES[i + 1]; nxt = ("../%s/%s" % (n[0], n[1]), n[3])
        lesson(os.path.join(DIR, folder, html_name),
               num="%02d" % i, total=TOTAL, h1=h1, subtitle=subtitle,
               meta=mod.META, sections=mod.SECTIONS, prev=prev, nxt=nxt)
        notebook(os.path.join(DIR, folder, nb_name), mod.NB)

    index(
        os.path.join(DIR, "index.html"),
        "C77 · 视频与世界模型",
        "<strong>时间轴上的每一个便宜的近似，都在别处产生一个精确可算的代价</strong>——"
        "时间压缩换走可观测性、分解式注意力换走 Kronecker 秩、"
        "一步拟合换走运动能量、被动生成的准确不蕴含抗优化、逐帧特征换走整个时间维。"
        "而这些代价<strong>全都不会报错</strong>。"
        "C28 已经讲完图像扩散的五块地基，本课是它每一处「视频留待后续」的展开。"
        "6 个模块 · 6 个 notebook · 24 道带自测的练习 · "
        "纯 numpy / CPU / 离线 · <strong>不训练任何神经网络</strong>。",
        [
            "纯 numpy · CPU · 离线",
            "不训练任何网络",
            "五处诚实修正（一处连错三次）",
            "两处意外收获",
            "与 C28 / C41-04 零重叠",
            "6 模块 · 24 练习",
        ],
        "按 <strong>00 → 01 → …→ 05</strong> 顺序读："
        "00 给出时间轴的代价账与三个反直觉，"
        "01 是压缩（时间维该怎么压），02 是注意力（分解损失了什么），"
        "03 是漂移（长视频为什么会糟），04 是可交互（世界模型的两义），"
        "05 是评测（FVD 的三个病理）。"
        "<strong>只有两小时</strong>：读 <strong>模块 02 第 4 节</strong>"
        "（分解式注意力的 Kronecker 秩——那里有三个连续的、被数值推翻的猜想）"
        "+ <strong>模块 04 第 2 节</strong>（同一个模型：$-13\\%$ vs $+251\\%$），"
        "跑 <strong>模块 03</strong> 的 notebook —— "
        "那里能看到「生成的视频越往后越静止」这个现象"
        "在不需要任何神经网络的情况下就已经出现了。",
        [
            ("第一段 · 时间轴的代价", [
                ("00_setup/00_overview.html", "MODULE 00",
                 "总览：时间轴把什么改变了",
                 "**代价是平方的**：T=128 时注意力代价是单帧的 **1024 倍**，"
                 "而「联合 vs 逐帧」的额外因子恰好是 T（恒等式）· "
                 "**3D 压缩的收益是相关性的函数**：corr=0 时 **0.984（反而更差）**，"
                 "corr=0.99 时 4.490 · "
                 "**遮挡悬崖**：h≤6 时误差 1.003（除均值什么也预测不出），"
                 "h=7 塌到 0.310、h=8 到 0.059 —— *一帧给位置，两帧给速度* · "
                 "所以「长上下文因为相关性长」是错的：**买到的是可观测性**"),
                ("01_video_latent/01_讲解.html", "MODULE 01",
                 "视频 latent 与 tokenizer：时间维压缩的账",
                 "p_t 是唯一能**平方级**换算力的旋钮，而它换走可观测性 · "
                 "**有效相关性 ρ^p_t 给出 p_t 的上限** · "
                 "**流式（因果）的代价非单调**：峰值 1.0308x 在 corr≈0.95，两端都回到 1.00 · "
                 "代价还**集中在每个 chunk 的最后一帧**，而最后一个 chunk 恒为 1.00 · "
                 "**固定比特下「少而大的 token」优 1.58x**，"
                 "而*判断码本坍缩要看熵/log₂K，不能看利用率*"),
            ]),
            ("第二段 · 分解的精确边界", [
                ("02_spacetime_attn/02_讲解.html", "MODULE 02",
                 "时空注意力：分解的代价与它的精确边界",
                 "分解的节省 = TS/(S+T)，**会饱和**（上界是 S）· "
                 "**分解式注意力 = Kronecker 积**（恒等式，差 0）· "
                 "**匀速运动（任意多物体）分解*精确*可表示**，而**加速**需秩 3–5 · "
                 "**深度与残差都不提高表达力** —— 八层带残差仍是秩 1，"
                 "因为 (I+I⊗As)(I+At⊗I) = (I+At)⊗(I+As) · "
                 "**并行分支才提高**：秩 2/4/16，饱和值恰为 **m²−m+1**（七组全中）"),
            ]),
            ("第三段 · 长视频与可交互", [
                ("03_temporal_drift/03_讲解.html", "MODULE 03",
                 "时序一致性与自回归漂移",
                 "**「自回归必然漂移」是错的**：误差按 |â|^k，稳定时**指数遗忘** · "
                 "真正累积的是**分布**的错误，而它有两支症状相反的形态 · "
                 "**一步拟合低估持续性 ⇒ rollout 的运动能量只有真值的 35%–49%** —— "
                 "*「越往后越静止」不需要神经网络，且是目标函数问题不是能力问题* · "
                 "而尾部 **28.60% 的拟合给出 |â|>1** · "
                 "**方差中位数 8.93 而均值 1.4e14**（差 16 个数量级）"),
                ("04_world_model/04_讲解.html", "MODULE 04",
                 "世界模型：动作条件、可交互 rollout，与 C41 的分工",
                 "**「这个世界模型准不准」没有答案，除非先说清它要被怎么用** · "
                 "同一个模型（一步误差 **0.0395**）：被动 rollout **−13.0%**，"
                 "主动规划 **+251.2%** —— *优化器在最大化模型的结构误差* · "
                 "**动作条件的收益 = 动作占的方差份额**（1.01x 到 28.23x，有闭式），"
                 "而**喂错动作比不喂更糟** · "
                 "**分布偏移本身不是问题，误配 × 偏移才是**（平坦 +1.9% vs 涨 44 倍）"),
            ]),
            ("第四段 · 评测", [
                ("05_video_eval/05_讲解.html", "MODULE 05",
                 "视频评测：FVD 的三个病理与运动口径",
                 "**① 同分布之间的 FD 恒为正且 ∝ 1/N**（N=64, d=32 时已是 9.33）—— "
                 "*不同 N 下的 FVD 不可比* · "
                 "**② 只看前两阶矩**：峰度 2.99 vs 1.00 的两个分布，"
                 "FD 是 0.000587 而同分布基线 0.000603 —— *比基线还小* · "
                 "**③ 逐帧特征对帧序结构性免疫**：敏感度 **7.1e−15** · "
                 "而「用了多少帧」不是判据 —— "
                 "**「时间排序后平均」用满全部帧却完全免疫，「首末帧之差」只用 2 帧却敏感**"),
            ]),
        ],
    )

    text_file(os.path.join(DIR, "README.md"), README)
    text_file(os.path.join(DIR, "requirements.txt"), REQUIREMENTS)
    text_file(os.path.join(DIR, "glossary.md"), GLOSSARY)
    text_file(os.path.join(DIR, "references.md"), REFERENCES)
    return report(DIR)


if __name__ == "__main__":
    ok = build()
    print("\n构建完成。" if ok else "\n⚠️ 有产物未达标，请检查上面的 ⚠️ 标记。")
