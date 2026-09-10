#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 C76 · 因果推断与线上归因。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coursekit import ROOT, lesson, index, notebook, text_file, install_assets, report
import c76_m00, c76_m01, c76_m02, c76_m03, c76_m04, c76_m05

CID = "C76_Causal_Inference_Course"
DIR = os.path.join(ROOT, CID)
TOTAL = 6

MODULES = [
    ("00_setup", "00_overview.html", "00_environment_check.ipynb",
     "00 · 总览：随机化解决了什么、又留下了什么",
     "<strong>一条代数恒等式把整门课框定了</strong>："
     "朴素差 $= $ ATT $+$ 选择偏差，"
     "在合成人群上 $1.582605 = 0.647736 + 0.934869$，<strong>两边之差恰为 $0$</strong> · "
     "随机化把选择偏差<em>结构性地</em>归零（实测 $-0.0069$ / $-0.0067$ / $-0.0017$，"
     "误差 $\\propto 1/\\sqrt{n}$，比值 $2.20$ / $1.96$ / $1.92$）· "
     "而它<strong>没有</strong>解决四件事，每件一个数字："
     "<strong>干扰（测到 $1.00$，全局效应 $2.00$）</strong> · "
     "<strong>代理指标（短期 $+1.005$，长期 $-0.999$——符号反转）</strong> · "
     "<strong>归因规则（真实份额 $7.1\\%$ 被记成 $38.0\\%$）</strong> · "
     "外部效度（子人群 ATE 相差 $1.71$ 倍，$9.1\\%$ 的个体效应为负）",
     c76_m00),

    ("01_potential_outcomes", "01_讲解.html", "01_potential_outcomes.ipynb",
     "01 · 潜在结果框架：ATE/ATT/CATE、识别与估计",
     "四个目标量数值上不相等：ATE $0.999902$、<strong>ATT $0.647994$、ATC $1.351346$"
     "（比值 $0.480$——已被处理的人获益<em>更少</em>）</strong> · "
     "分层估计：$K{=}5$ 消除 <strong>$89.7\\%$</strong> 的偏差（对上 Cochran 1968），"
     "$K{=}50$ 残余 $5.3\\times10^{-5}$，而 <strong>$K{=}400$ 静默丢弃 $8.3\\%$ 的样本"
     "、$K{=}800$ 丢 $22.2\\%$</strong>，于是 RMSE 反而回落——"
     "<em>RMSE 不是选层数的正确判据</em> · "
     "<strong>未观测混杂的偏差在 $n$ 跨 $1000$ 倍时稳定在 $+0.853$</strong>（一位有效数字都没动）· "
     "<strong>定向投放的盈亏平衡噪声 $\\propto \\text{sd}(\\tau)^2/\\text{ATE}$</strong>"
     "（二次律，验证到 $0.779$–$1.130$），而异质性弱时定向是净亏（$0.702$ 倍）",
     c76_m01),

    ("02_dag_backdoor", "02_讲解.html", "02_dag_backdoor.ipynb",
     "02 · 因果图与识别：后门准则、对撞偏差、中介",
     "<strong>对撞把 $X$ 对 $Y$ 的系数从 $+0.0006$ 变成 $-0.917$</strong>"
     "（闭式解 $-1/(1+\\sigma^2)$ 预测 $-0.9174$，差 $4.5\\times10^{-4}$）· "
     "枚举全部 $8$ 个控制变量子集，<strong>只有 $1$ 个合法</strong>，"
     "而<strong>后门准则与「回归无偏」在 $8$ 个子集上完全一致</strong> · "
     "<strong>$\\{X\\}\\to\\{X,C\\}$ 只多控制一个变量，偏差从 $0.002$ 变成 $-2.596$</strong> · "
     "$\\{X,M\\}$ 不是「不太准」，它<em>精确无偏地</em>估出了直接效应 $2.00079$——"
     "<strong>答对了另一个问题，$31\\%$ 的效应不留痕迹地消失</strong> · "
     "<strong>M-bias：控制一个<em>处理前</em>变量把偏差从 $+0.001$ 变成 $-0.312$</strong>"
     "（而它与 $T$ 的相关是 $+0.4889$，任何按相关性筛特征的流程都会选它）",
     c76_m02),

    ("03_estimation", "03_讲解.html", "03_estimation.ipynb",
     "03 · 倾向得分、IPW、双重稳健与双重机器学习",
     "IPW 用<em>真值</em>倾向得分仍然无偏，而<strong>有效样本量从 $4000$ 掉到 $616$</strong>"
     "（$85\\%$ 的样本不起作用），且<em>诊断量自己也在退化</em>"
     "（half-frac 的跨 seed 标准差从 $0$ 涨到 $6.00$ pp）· "
     "<strong>截断不是「近似 ATE」，是换了一个人群</strong>："
     "ATE $2.0019$ vs 重叠人群 $1.4371$，而被排除的 $16.1\\%$ 效应是 $+4.9556$（最强的那批）· "
     "AIPW 只在两个 nuisance <em>都</em>错时失效（$3.492$/$3.476$/$3.491$ vs $\\mathbf{2.816}$）· "
     "<strong>两个 bit 级恒等式</strong>：FWL 差 $2.2\\times10^{-16}$（OLS 下正交化是恒等变换）；"
     "<strong>常数 $\\hat{e}$ 使 AIPW $\\equiv$ G-computation（差 $<2\\times10^{-11}$）</strong> · "
     "<strong>过拟合把修正项吃掉 $4.4\\times10^{5}$ 倍</strong>，"
     "同时 G-comp 崩到 $+123.44$——<em>越强的结果模型越把纠偏机制关掉</em> · "
     "而交叉拟合在部分线性得分里<strong>四个设定全部更差</strong>（那里的偏差在残差比值中抵消）",
     c76_m03),

    ("04_quasi_experiment", "04_讲解.html", "04_quasi_experiment.ipynb",
     "04 · 准实验：DiD、工具变量、断点回归、合成控制",
     "四种方法的核心假设<strong>都不可从数据检验</strong>，所以每节都给出"
     "「常用检验为什么挡不住」· "
     "<strong>DiD：pre-trend $\\vert t\\vert{=}0.77$ 与「平行趋势成立」那一行完全相同，"
     "而 DiD 偏 $+1.25$ / $+1.50$</strong>（event-study 处理前 $4$ 期最大 $0.126$）· "
     "<strong>2SLS：$F$ 中位数 $0.46$ 时中位数 $1.8009$ 与 OLS 的 $1.7994$ 无法区分</strong>，"
     "而<em>均值</em>在 $-0.599$ 与 $+0.492$ 之间乱跳——恰好识别的 2SLS <strong>没有有限矩</strong>"
     "（取值范围 $[-1978.6, +804.9]$）· "
     "<strong>RDD 的偏差来自两侧曲率之<em>差</em></strong>："
     "对称时最优带宽是用满全部数据，不对称时 $h^{*}{=}0.2$、$h{=}1.0$ 偏 $0.4175$ · "
     "<strong>合成控制：无约束 OLS 的 pre 期拟合在 $4/4$ 种设定里都更好，"
     "而 post 期只在 $2/4$ 里更好</strong>——预测力是掷硬币；"
     "而 post 期新因子出现时 <strong>pre RMSE 逐位不变、post RMSE 涨 $3.0$ 倍</strong>",
     c76_m04),

    ("05_online_attribution", "05_讲解.html", "05_online_attribution.ipynb",
     "05 · 线上归因：SUTVA 与干扰、集群随机化、多触点归因、代理指标",
     "本模块全部发生在<strong>随机化完全有效</strong>的前提下，"
     "四种失效<strong>都不产生任何异常统计量</strong> · "
     "<strong>个体随机化测到 $1.0026$，全局效应是 $2.00$</strong>——"
     "漏掉的比例恰为 $\\beta/(\\alpha+\\beta)$，与样本量无关"
     "（$n$ 从 $10^3$ 到 $1.6\\times10^4$ 都是 $50.0\\%$）· "
     "<strong>设计效应 $1+(m-1)\\text{ICC}$：$m{=}50$, ICC$=0.2$ 时实测 $10.97$ vs 理论 $10.80$</strong>，"
     "而集群大小的 MSE 有内点最优（$m^{*}{=}50$）· "
     "<strong>只反转曝光时序：转化率一位不变（$30.88\\%$），"
     "而搜索的 last-touch 份额变了 $66.7$ 个百分点</strong>——"
     "last-touch 违反 Shapley 的对称性与虚拟性公理 · "
     "<strong>代理指标的误差恒等于 $-d$</strong>，与代理指标选得多好完全无关，"
     "且 $d < -ab$ 时<strong>符号反转</strong>",
     c76_m05),
]

README = r"""# C76 · 因果推断与线上归因

> **一条代数恒等式把整门课框定了。**
>
> 朴素差 $=$ ATT $+$ 选择偏差。这不是近似，是恒等式：
> 在本课的合成人群上 `1.582605 = 0.647736 + 0.934869`，**两边之差恰为 0**。
>
> 所有识别策略——随机化、后门调整、工具变量、双重差分——做的都是同一件事：
> **给「选择偏差」这一项一个等于零（或可估计）的理由**。

6 个模块 · 6 个 notebook · 24 道带自测的练习 · 纯 numpy / CPU / 离线。

## 这门课的边界

**C10 模块 07「在线 A/B 评测」已经拥有整套 A/B 统计工具箱**：假设检验、z/t 检验、
功效与 MDE、多重比较与 Bonferroni、序贯检验与偷看、CUPED。本课**一概不重复**——
里面没有一个 $z$ 检验、功效曲线或方差缩减技巧。

本课的定位是：**C10-07 假设随机化有效；本课处理它无效或不够的情形。**

| 情形 | 本课的模块 |
|---|---|
| 不能随机化（只有观测数据） | 02（该控制什么）· 03（怎么估） |
| 随机化不可得且后门假设也不成立 | 04（换设计：DiD / IV / RDD / 合成控制） |
| 随机化有效但被违反（干扰） | 05（SUTVA、集群随机化、switchback） |
| 随机化有效，但**测的不是你要的量** | 01（目标量）· 05（归因规则、代理指标） |

## 贯穿全课的一条线

**因果推断的失效几乎从不表现为错误，而是表现为「答对了另一个问题」。**

本课的十几个失效场景里，**没有一个会报错**。每一个都给出格式正确、
置信区间漂亮、换 seed 也复现、能写进周报的数字。下面是它们各自「答对的那个别的问题」：

| 你以为在估 | 实际估到的 | 差距 | 位置 |
|---|---|---|---|
| 全人群 ATE | 已被处理者的 ATT | ATT $0.648$ vs ATC $1.351$（$2.09$ 倍） | m01 |
| 全人群 ATE | 两臂齐全的层上的 ATE | $K{=}800$ 静默丢弃 $22.2\%$ 的样本 | m01 |
| 总效应 | **直接效应** | $2.90 \to 2.00$（丢掉 $31\%$） | m02 |
| 全人群 ATE | 重叠人群的 ATE | $2.0019 \to 1.4371$，被排除者效应 $+4.96$ | m03 |
| 双重稳健估计 | 纯插入估计（G-computation） | 逐位相同（差 $< 2\times10^{-11}$） | m03 |
| 处理的因果效应 | 与 OLS 无法区分的有偏估计 | $1.8009$ vs $1.7994$ | m04 |
| 全局效应 | 直接效应（不含溢出） | $1.00$ vs $2.00$ | m05 |
| 渠道的因果贡献 | 按曝光顺序分配的会计份额 | $7.1\% \to 38.0\%$；只改时序即变 $66.7$ pp | m05 |
| 长期效应 | 长期效应中经由代理指标的部分 | 短期 $+1.005$，长期 $-0.999$（**符号反转**） | m05 |

## 六处诚实修正

本课的多处结论是在探数阶段被测量结果**推翻后重写**的。这些修正本身是内容的一部分：

1. **「RDD 带宽越小偏差越小」在两侧曲率<em>对称</em>时是假的**（m04）。
   对称曲率下两侧的局部线性偏差**恰好抵消**，最优带宽变成用满全部数据（$h^{*}{=}1.0$）。
   必须让两侧曲率不同才出现内点最优（$h^{*}{=}0.2$）。
   → 真正的结论比原来的更有用：**RDD 的偏差取决于两侧形状之差，不是曲率大小**。

2. **「双重稳健的『错/错』行会失效」第一版证明不了**（m03）。
   我把结果模型的误配设成 $\mu_0 = X + X^2$（两臂相同），
   于是 $X^2$ 在 $\hat m_1 - \hat m_0$ 里自动抵消，「错」的模型给出 $1.9928$（几乎无偏）。
   必须让误配是**处理依赖**的（$\tau$ 本身非线性）才显出来。
   → 教训：验证「模型 A 错时会怎样」之前，要先确认 A 真的错在**会影响估计量**的方向上。

3. **「DML 的交叉拟合总是更好」是错的**（m03）。
   在部分线性的残差对残差得分里，**四个设定全部更差**——
   nuisance 的过拟合同时压低 $\tilde T$ 与 $\tilde Y$，在比值里抵消。
   交叉拟合在 **AIPW 得分**里才是必要的（那里修正项不抵消）。
   → 而且它是**必要条件不是充分条件**：$q{=}320$ 时交叉拟合的 G-comp 仍是 $+36.64$。

4. **「正交化是一种新估计量」在 OLS nuisance 下是假的**（m03）。
   Frisch–Waugh–Lovell：$1.4633431908608447$ vs $1.4633431908608445$，差 $2.2\times10^{-16}$。
   → 所以「上 DML」在 nuisance 是 OLS 时不会改变任何数字。

5. **「合成控制的 pre 期拟合越好越可信」的预测力是 $2/4$**（m04）。
   无约束 OLS 在 $4/4$ 种设定里 pre 期拟合都更好，post 期只在 $2/4$ 里更好。
   而 post 期出现新因子时 **pre RMSE 逐位不变**、post RMSE 涨 $3.0$ 倍。

6. **「定向投放的判据是模型误差小于效应离散度」太松**（m01）。
   实测的盈亏平衡噪声是 $\text{sd}^{*} \approx 0.8\text{–}1.0 \cdot \text{sd}(\tau)^2/\text{ATE}$，
   **对异质性是二次的**（$h$ 翻倍，容忍的噪声涨 $3.79$–$3.92$ 倍，不是 $2$ 倍）。
   → 判据要再乘一个 $\text{sd}(\tau)/\text{ATE}$ 的因子。

## 两处意外收获

1. **对撞偏差的强度有闭式解**（m02）。取 $Z = X + Y + \varepsilon$，
   条件相关恰为 $-1/(1+\sigma^2)$：实测 $-0.91698$ vs 理论 $-0.91743$。
   所以它不是「可能有多大」，而是**可以事先算出来**。

2. **M-bias 需要四条边同时存在**（m02）。断开任意一条，偏差从 $-0.31$ 回到 $\pm0.003$。
   这解释了为什么它在实践中的量级常常很小（四个系数的乘积容易接近 $0$），
   也说明本节的论点不是「不要控制处理前变量」，而是**「时间先后不是判据」**。

## 本课包含它自己配置不通过的验收项

这是刻意的设计（与 C72–C75 一致）：

- **m01 练习 2**：RMSE 选出的最优层数 $K^{*}{=}200$ **本身已经在丢弃 $2.5\%$ 的样本**。
  所以那个「最优」是相对一个已被换掉的目标算出来的。
- **m03 胶囊**：`DR_COLLAPSED` 这个警报**有假阳性**——场景 1 触发了它，
  而那个估计是对的（$1.4157$ vs 真值 $1.4371$）。修正项小有两种成因，
  相对大小分不出来，必须配上折内/折外残差比（$1.00$ 无害 vs $2.63$ 危险）。
- **m04 练习 4**：`in_hull` 的代理判定**没有任何阈值能同时做到 TPR>95% 与 FPR<5%**
  （最优 $2.2$ 处 FPR 仍是 $13.3\%$，$23\%$ 的真凸包外样本落在真凸包内的取值区间里）。
  原因不是判据不好，是「在凸包内」本身是程度问题。
- **m04 胶囊**：事前登记模板拦住了 $3/4$ 个已知有问题的分析，
  **DiD 那个它拦不住**——因为那个问题在不可检验的那一半里。
- **m05 胶囊**：设计 C 无警报，但它有约 $-0.15$ 的干扰偏差。
  审计器看不见，因为它只检查声明、不看数据。

## 模块

| 模块 | 主题 | notebook | 关键量 |
|---|---|---|---|
| 00 | 总览：随机化解决了什么、又留下了什么 | `00_environment_check.ipynb` | 恒等式差恰为 $0$；随机化后选择偏差 $10^{-3}$ 量级 |
| 01 | 潜在结果框架 | `01_potential_outcomes.ipynb` | ATT/ATC $=0.480$；未观测混杂偏差跨 $n$ 稳定在 $+0.853$ |
| 02 | 因果图与识别 | `02_dag_backdoor.ipynb` | $8$ 个子集只有 $1$ 个合法；M-bias $-0.312$ |
| 03 | 倾向得分 / IPW / DR / DML | `03_estimation.ipynb` | ESS $4000\to616$；修正项被吃掉 $4.4\times10^5$ 倍 |
| 04 | 准实验 | `04_quasi_experiment.ipynb` | pre-trend 通过而 DiD 偏 $+1.50$；2SLS 退回 OLS |
| 05 | 线上归因 | `05_online_attribution.ipynb` | $1.00$ vs $2.00$；DE $=10.97$；只改时序变 $66.7$ pp |

## 怎么用

```bash
pip install -r requirements.txt
jupyter lab            # 或 jupyter notebook
```

按 `00 → 01 → … → 05` 顺序读。每个 notebook 都是自包含的，
含 4 个练习（TODO 桩 + 自测断言）、参考答案与一个真实工程胶囊。

**只有两小时**：读 **m02 第 3 节**（控制变量的枚举表）+ **m05 第 1 节**（干扰），
跑 **m03 的 notebook**（那里有两个 bit 级恒等式，说明一个自称「双重稳健」的实现
可以在不报任何错的情况下**就是**纯插入估计量）。

## 数据

**不需要任何真实实验数据。** 全部数据生成过程的真值（$Y(0)$、$Y(1)$、$\tau$、
Shapley 值、gauge、因子结构）都是已知的——这正是能判断一个估计量对错的唯一前提。

## 相关课程

- **C10 模块 07** —— A/B 统计工具箱（本课的前提，且不重复）
- **C19** —— 可解释性里的 d-分离（同一工具，另一种用途）
- **C65** —— 辛普森悖论作为数据诊断的陷阱
- **C47** —— 排序里的位置偏差与 IPS（本课 m03 的加权思想在推荐场景的一个专门应用）
"""

REQUIREMENTS = """numpy>=1.24
jupyterlab>=4.0

# 本课全部计算为纯 numpy / CPU / 离线：
#   · 无 GPU、无网络、无外部数据集
#   · 无 scikit-learn / statsmodels / linearmodels —— 所有估计量都手写，
#     因为本课要展示的恰恰是「库函数会安静地给出错答案」的那些情形
#   · matplotlib 不是必需的（全部输出为数值表格，便于断言）
"""

GLOSSARY = r"""# C76 术语词典 · 因果推断与线上归因

按「概念 → 定义 → 本课的量化」组织。**加粗**的是本课重点验证过的。

## 一、框架与目标量

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 潜在结果 | potential outcome | $Y_i(t)$：个体 $i$ 若接受处理 $t$ 会取到的结果 | 每个个体只有一个可见 —— **根本问题** |
| 因果推断的根本问题 | fundamental problem of causal inference | $\tau_i = Y_i(1)-Y_i(0)$ 不可观测 | 只能估某种**平均**，而「哪一种」是建模选择 |
| ATE | average treatment effect | $E[\tau_i]$ | 本课人群 $0.999902$ |
| ATT | average treatment effect on the treated | $E[\tau_i \mid T_i{=}1]$ | $0.647994$ |
| ATC | average treatment effect on the controls | $E[\tau_i \mid T_i{=}0]$ | $1.351346$（**ATT/ATC $= 0.480$**）|
| CATE | conditional average treatment effect | $E[\tau_i \mid X_i{=}x]$ | 十分位从 $+2.318$ 到 $-0.317$ |
| LATE | local average treatment effect | 被工具推动的那部分人的效应 | 2SLS 识别的是它，**不是** ATE |
| 选择偏差 | selection bias | $E[Y(0)\mid T{=}1] - E[Y(0)\mid T{=}0]$ | **朴素差 $=$ ATT $+$ 它，差恰为 $0$** |
| 全期望分解 | law of total expectation | ATE $= \pi\,$ATT $+ (1-\pi)\,$ATC | 验证到 $2.2\times10^{-16}$ |
| 效应异质 | effect heterogeneity | $\tau_i$ 随 $X$ 变化 | ATE $+1.00$ 而 $9.1\%$ 的个体效应为负 |

## 二、识别假设

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| SUTVA | stable unit treatment value assumption | 无干扰 $+$ 处理只有一个版本 | 违反时 A/B 测 $1.00$，全局 $2.00$ |
| 无干扰 | no interference | $Y_i(t)$ 不依赖 $T_j$（$j \neq i$）| 漏掉 $\beta/(\alpha+\beta)$，与 $n$ 无关 |
| 一致性 | consistency | 「上线」在所有单元上是同一件事 | 灰度里客户端版本不同即违反 |
| 可忽略性 | ignorability / conditional independence | $\{Y(0),Y(1)\} \perp T \mid X$ | 违反时偏差跨 $n$ 稳定在 **$+0.853$** |
| 正性 / 重叠 | positivity / overlap | $0 < P(T{=}1\mid X) < 1$ | **唯一能从数据里检查的假设** |
| 结构性违反 | structural violation | 规则准入使 $e = 1$ | $X>1$ 的 $15.9\%$ 无对照可比 |
| 识别 vs 估计 | identification vs estimation | 能否写成可观测量的函数 vs 有限样本怎么算 | 前者失败时加样本**无用** |
| 敏感性分析 | sensitivity analysis | 「未观测混杂要多强才翻掉结论」 | 让估计翻倍需 $u \approx 1.25$ |

## 三、因果图

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| DAG | directed acyclic graph | 把因果假设画成有向无环图 | 本课把它写成代码并接受 CI 断言 |
| 链 | chain | $A \to B \to C$ | 控制 $B$ **阻断**（$0.578 \to -0.001$）|
| 叉 | fork | $A \leftarrow B \to C$ | 控制 $B$ **阻断**（$0.500 \to +0.001$）|
| 对撞 | collider | $A \to B \leftarrow C$ | 控制 $B$ **打开**（$+0.001 \to -0.917$）|
| 对撞偏差 | collider bias | 条件化对撞（或其后代）制造关联 | 闭式解 $-1/(1+\sigma^2)$，差 $4.5\times10^{-4}$ |
| d-分离 | d-separation | 图上的条件独立判据 | 用 Bayes-Ball 实现，与数值完全一致 |
| Bayes-Ball | Bayes-Ball | d-分离的线性时间算法（Shachter 1998）| 状态为「节点 $+$ 来向」的 BFS |
| 后门路径 | back-door path | 从 $T$ 出发第一步指向 $T$ 的路径 | — |
| 后门准则 | back-door criterion | $Z$ 无 $T$ 的后代 $+$ 阻断全部后门路径 | **$8$ 个子集只有 $1$ 个合法** |
| 调整公式 | adjustment formula | $E[Y(t)] = \sum_z E[Y\mid T{=}t,Z{=}z]P(z)$ | — |
| 中介 | mediator | $T \to M \to Y$ | 控制它 $2.90 \to 2.00$（丢 $31\%$）|
| 中介占比 | mediated share | $a_{TM}b_{MY}/$ 总效应 | 可精确预测（$4$ 组参数验证）|
| M-bias | M-bias | 条件化两个未观测混杂的共同后代 | **$+0.001 \to -0.312$，即使 $Z$ 在处理前** |
| 好控制 / 坏控制 | good/bad controls | 八类变量的去留判据 | **只有「纯结果预测变量」无条件安全** |
| 马尔可夫等价类 | Markov equivalence class | 观测数据无法区分的图的集合 | 因果发现的上限（本课不覆盖）|

## 四、估计量

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 分层 | subclassification | 按 $X$ 分位切层，层内做差 | **$K{=}5$ 消除 $89.7\%$ 的偏差** |
| 倾向得分 | propensity score | $e(x) = P(T{=}1\mid X{=}x)$ | 定理：只按一维 $e(X)$ 调整就够 |
| IPW | inverse probability weighting | $T Y/e - (1{-}T)Y/(1{-}e)$ | 无偏，而 **ESS $4000 \to 616$** |
| 有效样本量 | effective sample size | $(\sum w)^2/\sum w^2$ | $\text{Var} \propto 1/\text{ESS}$，不是 $1/n$ |
| 权重集中度 | weight concentration | 贡献一半权重的样本占比 | $50.00\% \to 13.06\%$（$20$ seeds 均值）|
| 截断 | trimming / clipping | 把 $e$ 限制在 $[\text{lo}, \text{hi}]$ | **换掉估计目标**：$2.0019 \to 1.4371$ |
| G-computation | G-computation | 对结果模型的预测差取平均 | 过拟合时崩到 $+123.44$ |
| AIPW | augmented IPW | G-comp $+$ IPW 型修正项 | 只在两个 nuisance **都**错时失效 |
| 双重稳健 | doubly robust | **至少一个** nuisance 对即一致 | 不是「更准」，是放松一致性的条件 |
| 修正项 | correction term | AIPW $-$ G-computation | **过拟合把它吃掉 $4.4\times10^5$ 倍** |
| nuisance 模型 | nuisance model | $\hat e$ 与 $\hat m_t$ | 它们的误差如何传到 $\hat\tau$ 是核心问题 |
| 正交化 | orthogonalization | 残差对残差回归 | **OLS 下与朴素插入代数相等**（$2.2\times10^{-16}$）|
| FWL 定理 | Frisch–Waugh–Lovell | 分块 OLS 的等价性 | 决定了 DML 的适用范围 |
| 交叉拟合 | cross-fitting | 在没被拟合过的折上取残差 | AIPW 得分里必要，部分线性得分里 $4/4$ 更差 |
| 一阶正则化偏差 | first-order regularization bias | 正则化的 nuisance 误差进入一阶项 | DML 消掉的正是它 |
| DML | double / debiased machine learning | 正交化 $+$ 交叉拟合 | **必要条件，不是充分条件** |

## 五、准实验

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 双重差分 | difference-in-differences (DiD) | 处理组前后差 $-$ 对照组前后差 | — |
| 平行趋势 | parallel trends | 处理组若未处理，趋势与对照组同 | **不可检验** |
| pre-trend 检验 | pre-trend test | 在处理前期间做同样的 DiD | **通过（$\vert t\vert{=}0.77$）而 DiD 偏 $+1.50$** |
| 事件研究图 | event study plot | 逐期相对基期的组间差 | 处理前 $4$ 期最大 $0.126$（漂亮地贴零）|
| 检验功效不足 | insufficient power | 有偏但检验不拒绝 | Roth (2022)；本课练习 1 量化 |
| 工具变量 | instrumental variable (IV) | 只经由 $T$ 影响 $Y$ 的 $Z$ | 需外生性 $+$ 相关性 $+$ 排他性 |
| 2SLS | two-stage least squares | 先用 $Z$ 预测 $T$，再估效应 | — |
| 第一阶段 $F$ | first-stage $F$ | $Z$ 对 $T$ 的联合显著性 | $F$ 中位数 $9.88$ 是分界 |
| 弱工具 | weak instrument | $F$ 太小 | **中位数 $1.8009$ 与 OLS 的 $1.7994$ 无法区分** |
| 无有限矩 | no finite moments | 恰好识别的 2SLS 的均值不存在 | 取值范围 $[-1978.6, +804.9]$，$\vert\cdot\vert{>}10$ 占 $3.65\%$ |
| $F>10$ 规则 | rule of thumb $F>10$ | Staiger & Stock (1997) | $1/(F{+}1)$ 给出偏差比例的量级 |
| 断点回归 | regression discontinuity (RDD) | 用规则阈值两侧的准随机性 | — |
| 带宽 | bandwidth | 阈值附近用于拟合的窗口 | 不对称曲率下 $h^{*}{=}0.2$ |
| 两侧曲率之差 | curvature asymmetry | 两侧二阶项系数之差 | **偏差由它决定，不由曲率大小决定** |
| 高次全局多项式 | high-order global polynomial | 用全样本拟合高次多项式 | 偏差不改善，标准差涨 $3.4$ 倍 |
| 合成控制 | synthetic control | 对照单位的加权组合 | — |
| 单纯形约束 | simplex constraint | $w \geq 0$，$\sum w = 1$ | 凸包内优 $1.57$ 倍，凸包外劣 $3.51$ 倍 |
| 外推程度 | extrapolation degree | $\sum\vert w\vert$ | 无约束达 $5.29$ / $7.14$ |
| pre 期拟合优度 | pre-period fit | pre 期的 RMSE | **对 post 期精度的预测力是 $2/4$** |
| 因子结构稳定性 | factor structure stability | pre/post 之间因子不变 | 违反时 pre RMSE **逐位不变**，post 涨 $3.0$ 倍 |
| 事前登记 | pre-registration | 看数据前写下假设与诊断 | 拦住 $3/4$；DiD 那个拦不住 |

## 六、线上归因

| 术语 | 英文 | 定义 | 本课的量化 |
|---|---|---|---|
| 干扰 / 溢出 | interference / spillover | 别人的处理影响我的结果 | 个体随机化测 $1.0026$，全局 $2.00$ |
| 邻居暴露 | neighbor exposure | 邻居中被处理的比例 | **$\hat\tau_{AB} = \alpha + \beta \cdot$ 暴露差** |
| 暴露差 | exposure differential | 两臂的邻居暴露之差 | 个体 $0.0016$；$m{=}500$ 时 $0.9936$ |
| 集群随机化 | cluster randomization | 整个集群同处理 | $m{=}20$ 残余偏差 $-0.15$，$m{=}500$ 为 $-0.004$ |
| 组内相关系数 | intraclass correlation (ICC) | 结果方差中组间成分的占比 | **是集群划分方式的函数，不是数据属性** |
| 设计效应 | design effect | $1 + (m-1)\text{ICC}$ | $m{=}50$, ICC$=0.2$：实测 $10.97$ vs 理论 $10.80$ |
| 等价样本量 | effective sample size (design) | $n/\text{DE}$ | $m{=}50$, ICC$=0.2$ 时缩到 $1/11$ |
| switchback | switchback | 把集群建在时间片上 | 用于共享资源型干扰；额外有 carryover |
| 残留 | carryover | 切换点附近的处理残留 | 处理办法是丢弃 burn-in |
| 归因 | attribution | 这次转化该记谁的功劳 | 顺序规则**不是**因果估计量 |
| last-touch | last-touch attribution | 功劳全给最后一个触点 | **$7.1\% \to 38.0\%$（高估 $5.4$ 倍）** |
| first-touch | first-touch attribution | 功劳全给第一个触点 | 最大误差 $27.2$ pp |
| 时间衰减 | time-decay attribution | 越靠后权重越大 | 最大误差 $25.0$ pp |
| Shapley 值 | Shapley value | 对全部到达顺序取平均的边际贡献 | 和 $=$ 全触点转化概率（有效性公理）|
| 有效性公理 | efficiency axiom | $\sum_c \phi_c = v(\text{全集})$ | 验证到 $<10^{-12}$ |
| 对称性公理 | symmetry axiom | 等价渠道的 $\phi$ 相同 | last-touch **违反** |
| 虚拟性公理 | null player axiom | 零贡献渠道的 $\phi = 0$ | last-touch **违反** |
| 移除效应 | removal effect | 去掉某渠道后转化率的下降 | Markov 链归因的基础 |
| 代理指标 | surrogate / proxy metric | 用短期 $S$ 预测长期 $Y$ | 误差**恒等于** $-d$ |
| 替代性 | surrogacy | $T$ 对 $Y$ 无绕过 $S$ 的直接效应 | 检验：$Y \sim T + S$ 中 $T$ 的系数 |
| 代理指标符号反转 | surrogate sign flip | 预测与真实异号 | 条件恰为 $d < -ab$；短期 $+1.005$，长期 $-0.999$ |
| 口径错配 | metric–decision mismatch | 报告的量 $\neq$ 决策的量 | 本课的统一主题 |

## 七、诊断量速查

| 量 | 在哪 | 阈值 / 解读 |
|---|---|---|
| 选择偏差 | m00 | 恒等式的一项，有确定数值 |
| 层内丢弃比例 | m01 | $>0$ 即估计目标已被换掉 |
| 残余偏差 vs $n$ | m01 | 不随 $n$ 缩小 $\Rightarrow$ 识别问题 |
| 敏感性阈值 $u^{*}$ | m01 | 「翻掉结论所需的混杂强度」 |
| 合法调整集个数 | m02 | $1/8$ 时靠猜的成功率 $12.5\%$ |
| ESS $/ n$ | m03 | $<0.3$ 报警 |
| 权重集中度 | m03 | 「百分之几的样本决定了一半的答案」 |
| trim 丢弃比例 | m03 | $>5\%$ 时目标已变 |
| 修正项 $/$ 点估计 | m03 | $<10^{-3}$ 时 DR 可能已失效（**有假阳性**）|
| 折外 $/$ 折内残差比 | m03 | $>2$ 时 nuisance 样本外很差 |
| pre-trend $\vert t\vert$ | m04 | 通过**不等于**成立 |
| 第一阶段 $F$ | m04 | $<10$ 时 2SLS 向 OLS 漂移 |
| 两侧曲率 $t$ | m04 | 区分「RDD 有偏」与「结果非线性」 |
| $\sum\vert w\vert$ | m04 | 外推程度 |
| `hull_ratio_obs` | m04 | 报**连续量**，不报布尔值 |
| 邻居暴露差 | m05 | 不需要知道 $\beta$ 就能算 |
| 设计效应 | m05 | 样本量需求的乘数 |
| $Y \sim T + S$ 中 $T$ 的系数 | m05 | 替代性检验；需长期数据 |
"""

REFERENCES = r"""# C76 参考文献 · 因果推断与线上归因

按模块组织。每条注明**它在本课的哪个具体结论上被用到**。

---

## 模块 00 · 总览

- **Imbens, G. & Rubin, D.** *Causal Inference for Statistics, Social, and Biomedical
  Sciences.* Cambridge University Press, 2015.
  → 潜在结果框架的标准参考。第 1–3 章给出「朴素差 $=$ ATT $+$ 选择偏差」这条恒等式
  与 SUTVA 的两个部分（无干扰、一致性）。本课 m00 的恒等式与 m01 的四个目标量都出自此。

- **Holland, P.** *Statistics and Causal Inference.* JASA 81(396), 1986.
  → 「因果推断的根本问题」这个说法的来源，以及对「因果」与「关联」区分的经典讨论。

- **Rubin, D.** *Estimating Causal Effects of Treatments in Randomized and
  Nonrandomized Studies.* Journal of Educational Psychology 66(5), 1974.
  → 潜在结果记号 $Y_i(t)$ 的出处。

- **Kohavi, R., Tang, D. & Xu, Y.** *Trustworthy Online Controlled Experiments.*
  Cambridge University Press, 2020.
  → 本课与 C10 模块 07 的边界由这本书划定：它覆盖 A/B 的统计工具箱，
  本课处理它假设成立<em>之外</em>的情形。第 22 章（干扰）与第 23 章（长期效应）
  是本课 m05 的直接前身。

---

## 模块 01 · 潜在结果框架

- **Cochran, W.** *The Effectiveness of Adjustment by Subclassification in Removing
  Bias in Observational Studies.* Biometrics 24(2), 1968.
  → 「五层足以消除约 $90\%$ 的偏差」这条经典结论的来源。
  本课 m01 实测 $K{=}5$ 消除 $89.7\%$，与之吻合。

- **Hernán, M. & Robins, J.** *Causal Inference: What If.* Chapman & Hall/CRC, 2020.
  （作者提供免费 PDF）
  → 第 1–3 章把「识别 vs 估计」讲得最清楚。本课 m01 第 4–5 节的结构照它组织：
  识别失败的症状是「置信区间越来越窄，而窄区间的中心是错的」。

- **Athey, S. & Imbens, G.** *The State of Applied Econometrics: Causality and Policy
  Evaluation.* Journal of Economic Perspectives 31(2), 2017.
  → 对本课全部五种方法的鸟瞰式综述，以及「先选目标量再选估计量」这条纪律。

- **Rosenbaum, P. & Rubin, D.** *Assessing Sensitivity to an Unobserved Binary
  Covariate in an Observational Study with Binary Outcome.* JRSS-B 45(2), 1983.
  → 敏感性分析的原始形式。本课 m01 练习 3 的做法（「未观测混杂要多强才翻掉结论」）
  是它的连续版本。

- **Cinelli, C. & Hazlett, C.** *Making Sense of Sensitivity.* JRSS-B 82(1), 2020.
  → 敏感性分析的现代实现，把「多强」换成可解释的 $R^2$ 尺度。

---

## 模块 02 · 因果图与识别

- **Pearl, J.** *Causality: Models, Reasoning, and Inference.* 2nd ed., Cambridge
  University Press, 2009.
  → d-分离、后门准则、调整公式的原始出处（第 1、3、11 章）。
  本课 m02 的 `DAG.backdoor_ok` 是第 3.3 节定义的直接实现。

- **Shachter, R.** *Bayes-Ball: The Rational Pastime (for Determining Irrelevance
  and Requisite Information in Belief Networks and Influence Diagrams.* UAI 1998.
  → 本课 m02 的 `d_sep` 用的就是这个算法：状态为「节点 $+$ 来向」的线性时间 BFS。

- **Greenland, S., Pearl, J. & Robins, J.** *Causal Diagrams for Epidemiologic
  Research.* Epidemiology 10(1), 1999.
  → 把 DAG 语言引入应用领域的关键论文，也是 M-bias 讨论的起点。

- **Cinelli, C., Forney, A. & Pearl, J.** *A Crash Course in Good and Bad Controls.*
  Sociological Methods & Research 53(3), 2024.
  → 本课 m02 第 5 节那张「好控制 / 坏控制」八类表的直接来源。
  它也是「只有纯结果预测变量无条件安全」这个结论的出处。

- **Shrier, I. & Platt, R.** *Reducing bias through directed acyclic graphs.*
  BMC Medical Research Methodology 8(70), 2008.
  → M-bias 的教学式讨论，含「控制处理前变量也可能有害」的具体例子。

- **Ding, P. & Miratrix, L.** *To Adjust or Not to Adjust? Sensitivity Analysis of
  M-Bias and Butterfly-Bias.* Journal of Causal Inference 3(1), 2015.
  → 对 M-bias 实践量级的定量讨论。本课 m02 练习 4 的结论
  （四条边同时存在才有 M-bias，断一条即消失）与它一致。

- **Pearl, J.** *Comment: Understanding Simpson's Paradox.* The American
  Statistician 68(1), 2014.
  → 「该不该分层」这个问题只能由图回答。与本课 **C65** 的辛普森悖论一节互补：
  C65 把它当作数据诊断的陷阱，本课把它当作图的判定问题。

---

## 模块 03 · 倾向得分、IPW、双重稳健与 DML

- **Rosenbaum, P. & Rubin, D.** *The Central Role of the Propensity Score in
  Observational Studies for Causal Effects.* Biometrika 70(1), 1983.
  → 倾向得分定理（只按一维 $e(X)$ 调整即可）的原始出处。

- **Robins, J., Rotnitzky, A. & Zhao, L.** *Estimation of Regression Coefficients
  When Some Regressors Are Not Always Observed.* JASA 89(427), 1994.
  → AIPW / 双重稳健的原始形式。本课 m03 第 3 节那张 $2\times2$ 表
  （只在两个 nuisance 都错时失效）是它的核心命题的数值验证。

- **Bang, H. & Robins, J.** *Doubly Robust Estimation in Missing Data and Causal
  Inference Models.* Biometrics 61(4), 2005.
  → 双重稳健的实用化讨论，也包括对「DR 在有限样本里可能不如单一模型」的坦诚分析。

- **Kang, J. & Schafer, J.** *Demystifying Double Robustness.* Statistical Science
  22(4), 2007.
  → 一篇著名的批评性研究：在特定设定下 DR 估计量表现很差。
  本课 m03 的两个 bit 级恒等式（常数 $\hat e$ 使 AIPW $\equiv$ G-comp；
  过拟合把修正项吃掉）是同一类现象的、机制更清楚的版本。

- **Crump, R., Hotz, V., Imbens, G. & Mitnik, O.** *Dealing with Limited Overlap in
  Estimation of Average Treatment Effects.* Biometrika 96(1), 2009.
  → $[0.1, 0.9]$ 截断规则的来源。关键是它被明确设计为一个**换估计目标**的规则，
  而不是一个去偏规则——本课 m03 第 2 节把这一点量化为 $2.0019 \to 1.4371$。

- **Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W.
  & Robins, J.** *Double/Debiased Machine Learning for Treatment and Structural
  Parameters.* The Econometrics Journal 21(1), 2018.
  → DML 的原始论文。本课 m03 第 6 节把它的两个组件分开量化，
  并给出两个与通常表述不同的结论：正交化在 OLS nuisance 下是恒等变换；
  交叉拟合在部分线性得分里可能没有帮助。这两点与论文本身不矛盾——
  论文的定理关于的是**一阶正则化偏差**，而本课量的是有限样本下的实际差异。

- **Lovell, M.** *A Simple Proof of the FWL Theorem.* Journal of Economic Education
  39(1), 2008.
  → Frisch–Waugh–Lovell 定理的简洁证明。本课 m03 把它验证到 $2.2\times10^{-16}$。

- **Hirano, K., Imbens, G. & Ridder, G.** *Efficient Estimation of Average Treatment
  Effects Using the Estimated Propensity Score.* Econometrica 71(4), 2003.
  → 为什么用**估计的**倾向得分有时比用真值更有效率。
  与本课 m03 第 1 节（用真值仍然方差爆炸）形成对照。

---

## 模块 04 · 准实验

- **Angrist, J. & Pischke, J.** *Mostly Harmless Econometrics.* Princeton University
  Press, 2009.
  → 本模块四种方法的标准教材。第 4 章（IV）、第 5 章（DiD）、第 6 章（RDD）。

- **Card, D. & Krueger, A.** *Minimum Wages and Employment: A Case Study of the Fast-Food
  Industry in New Jersey and Pennsylvania.* AER 84(4), 1994.
  → DiD 的经典应用，也是后续关于平行趋势可信性的长期争论的起点。

- **Roth, J.** *Pre-test with Caution: Event-Study Estimates after Testing for
  Parallel Trends.* American Economic Journal: Applied Economics 14(3), 2022.
  → 本课 m04 第 2 节与练习 1 的直接来源：pre-trend 检验的功效常常不足，
  而「通过检验」这一步本身还会引入选择效应。

- **Goodman-Bacon, A.** *Difference-in-Differences with Variation in Treatment
  Timing.* Journal of Econometrics 225(2), 2021.
  → 处理时点不同时 DiD 的分解。本课不覆盖交错处理（staggered DiD），
  这是最重要的延伸方向。

- **Staiger, D. & Stock, J.** *Instrumental Variables Regression with Weak
  Instruments.* Econometrica 65(3), 1997.
  → 「第一阶段 $F > 10$」这条经验规则的来源。本课 m04 实测 $F$ 中位数 $9.88$
  恰是分界，且给出 $1/(F{+}1)$ 的偏差比例近似。

- **Nelson, C. & Startz, R.** *Some Further Results on the Exact Small Sample
  Properties of the Instrumental Variable Estimator.* Econometrica 58(4), 1990.
  → 恰好识别的 2SLS **没有有限矩**这一事实的来源。
  本课 m04 用它解释为什么均值那一列不可读、必须报中位数。

- **Angrist, J. & Imbens, G.** *Identification and Estimation of Local Average
  Treatment Effects.* Econometrica 62(2), 1994.
  → LATE 的定义。本课 m04 用它说明「把 2SLS 结果写成『该功能的效应』
  是一次无声的口径替换」。

- **Gelman, A. & Imbens, G.** *Why High-Order Polynomials Should Not Be Used in
  Regression Discontinuity Designs.* JBES 37(3), 2019.
  → 本课 m04 第 4 节的量化对象：次数从 $2$ 升到 $9$ 偏差不改善，标准差涨 $3.4$ 倍。

- **Calonico, S., Cattaneo, M. & Titiunik, R.** *Robust Nonparametric Confidence
  Intervals for Regression-Discontinuity Designs.* Econometrica 82(6), 2014.
  → RDD 的最优带宽选择与偏差校正。本课只给出 RMSE 曲线，
  这篇给出理论上的最优带宽公式。

- **Abadie, A., Diamond, A. & Hainmueller, J.** *Synthetic Control Methods for
  Comparative Case Studies.* JASA 105(490), 2010.
  → 合成控制与单纯形约束的原始出处。

- **Abadie, A.** *Using Synthetic Controls: Feasibility, Data Requirements, and
  Methodological Aspects.* Journal of Economic Literature 59(2), 2021.
  → 对「什么时候能用合成控制」的系统讨论，包括凸包位置的重要性。
  本课 m04 第 5 节把「凸包内 / 凸包外该用哪种权重」量化为 $1.57$ 倍与 $3.51$ 倍。

- **Doudchenko, N. & Imbens, G.** *Balancing, Regression, Difference-In-Differences
  and Synthetic Control Methods: A Synthesis.* NBER w22791, 2016.
  → 说明单纯形约束不是必需的，无约束版本在某些情形下更好——
  与本课 m04 的凸包外结果一致。

---

## 模块 05 · 线上归因

- **Rubin, D.** *Comment: Which Ifs Have Causal Answers.* JASA 81(396), 1986.
  → SUTVA 这个名字的出处。

- **Ugander, J., Karrer, B., Backstrom, L. & Kleinberg, J.** *Graph Cluster
  Randomization: Network Exposure to Multiple Universes.* KDD 2013.
  → 图聚类随机化的标准方法，以及「网络暴露」这个概念。
  本课 m05 的「邻居暴露差」诊断量是它的一个简化版本。

- **Eckles, D., Karrer, B. & Ugander, J.** *Design and Analysis of Experiments in
  Networks: Reducing Bias from Interference.* Journal of Causal Inference 5(1), 2017.
  → 干扰下的偏差与集群化的方差之间的权衡。
  本课 m05 练习 1 的 MSE 曲线是这个权衡的最小可执行版本。

- **Saveski, M., Pouget-Abadie, J., Saint-Jacques, G., Duan, W., Ghosh, S., Xu, Y. &
  Airoldi, E.** *Detecting Network Effects: Randomizing Over Randomized Experiments.*
  KDD 2017.
  → 一个直接**检测**干扰是否存在的设计（在随机化之上再随机化）。
  本课不覆盖，这是 m05 最重要的延伸方向。

- **Bojinov, I., Simchi-Levi, D. & Zhao, J.** *Design and Analysis of Switchback
  Experiments.* Management Science 69(7), 2023.
  → switchback 的理论分析，包括最优切换频率与 carryover 的处理。

- **Donner, A. & Klar, N.** *Design and Analysis of Cluster Randomization Trials in
  Health Research.* Arnold, 2000.
  → 设计效应 $1 + (m-1)\text{ICC}$ 的标准参考。本课 m05 把它验证到 $1.6\%$。

- **Shapley, L.** *A Value for n-Person Games.* In *Contributions to the Theory of
  Games II*, Princeton University Press, 1953.
  → Shapley 值与它的公理刻画。本课 m05 练习 2 验证其中三条（有效性、对称性、虚拟性）。

- **Dalessandro, B., Perlich, C., Stitelman, O. & Provost, F.** *Causally Motivated
  Attribution for Online Advertising.* ADKDD 2012.
  → 把归因问题明确写成因果问题的早期论文，并指出顺序规则不满足这个目标。

- **Anderl, E., Becker, I., von Wangenheim, F. & Schumann, J.** *Mapping the
  Customer Journey: Lessons Learned from Graph-Based Online Attribution Modeling.*
  International Journal of Forecasting 32(2), 2016.
  → Markov 链归因（移除效应）的实现与与顺序规则的对比。

- **Athey, S., Chetty, R., Imbens, G. & Kang, H.** *The Surrogate Index: Combining
  Short-Term Proxies to Estimate Long-Term Treatment Effects More Rapidly and
  Precisely.* NBER w26463, 2019.
  → 代理指标（surrogate index）的方法论与替代性假设的正式陈述。
  本课 m05 第 4 节的检验（$Y \sim T + S$ 中 $T$ 的系数）出自它。

- **Prentice, R.** *Surrogate Endpoints in Clinical Trials: Definition and
  Operational Criteria.* Statistics in Medicine 8(4), 1989.
  → 替代终点的原始判据（Prentice criterion）。
  本课的「符号反转」正是它失效时的一种表现。

- **VanderWeele, T.** *Surrogate Measures and Consistent Surrogates.* Biometrics
  69(3), 2013.
  → 为什么「代理指标与结果高度相关」不足以保证它是好的替代终点。
  与本课 m05「误差恒等于 $-d$，与代理指标选得多好无关」一致。

---

## 与本课程其他课的关系

- **C10 模块 07 · 在线 A/B 评测** —— A/B 统计工具箱（假设检验、功效、多重比较、
  序贯、CUPED）。本课的前提，且本课不重复其中任何内容。
- **C19 · 可解释性** —— 那里的 d-分离用于分析网络中的信息流；
  本课的 d-分离用于决定回归里放哪些变量。同一工具，两种用途。
- **C65 · 数据质量与诊断** —— 辛普森悖论作为数据陷阱。
  本课 m02 把「该不该分层」变成图上的判定问题。
- **C47 · 排序与推荐** —— 位置偏差与 IPS（逆倾向打分）。
  那是本课 m03 加权思想在排序场景的一个专门应用，
  其中倾向得分由展示策略已知，所以正性问题的形态不同。
- **C37 / C40 / C63 · 系统与运维方向** —— 多处提到「归因」，
  但那里指的是故障归因（root cause），与本课的因果归因是不同的问题。
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
        "C76 · 因果推断与线上归因",
        "一条代数恒等式把整门课框定了：<strong>朴素差 $=$ ATT $+$ 选择偏差</strong>"
        "（合成人群上 $1.582605 = 0.647736 + 0.934869$，两边之差恰为 $0$）。"
        "所有识别策略做的都是同一件事：给「选择偏差」这一项一个等于零的理由。"
        "而本课十几个失效场景里<strong>没有一个会报错</strong>——"
        "它们都给出格式正确、置信区间漂亮、换 seed 也复现的数字。"
        "6 个模块 · 6 个 notebook · 24 道带自测的练习 · 纯 numpy / CPU / 离线。",
        [
            "纯 numpy · CPU · 离线",
            "不需要任何真实实验数据",
            "两个 bit 级恒等式",
            "六处诚实修正 · 两处意外收获",
            "与 C10-07 零重叠",
            "6 模块 · 24 练习",
        ],
        "按 <strong>00 → 01 → …→ 05</strong> 顺序读："
        "00 给出那条恒等式与随机化<em>没有</em>解决的四件事，"
        "01 是目标量与识别，02 决定「控制什么」，03 是「怎么估」，"
        "04 处理后门假设不成立的情形，05 回到实验有效但口径错的情形。"
        "<strong>只有两小时</strong>：读 <strong>模块 02 第 3 节</strong>"
        "（控制变量的枚举表：$8$ 个子集只有 $1$ 个合法）"
        "+ <strong>模块 05 第 1 节</strong>（干扰：$1.00$ vs $2.00$），"
        "跑 <strong>模块 03</strong> 的 notebook —— "
        "那里有两个 bit 级恒等式，说明一个自称「双重稳健」的实现"
        "可以在不报任何错的情况下<em>就是</em>纯插入估计量。",
        [
            ("第一段 · 那条恒等式与目标量", [
                ("00_setup/00_overview.html", "MODULE 00",
                 "总览：随机化解决了什么、又留下了什么",
                 "**朴素差 $=$ ATT $+$ 选择偏差，两边之差恰为 0** · "
                 "随机化把它结构性归零（误差 ∝ $1/\\sqrt{n}$，比值 2.20/1.96/1.92）· "
                 "而它**没有**解决四件事：干扰（1.00 vs 2.00）· "
                 "代理指标符号反转（+1.005 vs −0.999）· "
                 "归因规则（7.1% 被记成 38.0%）· 外部效度（9.1% 的个体效应为负）"),
                ("01_potential_outcomes/01_讲解.html", "MODULE 01",
                 "潜在结果框架：ATE/ATT/CATE、识别与估计",
                 "**ATT 0.648 vs ATC 1.351（比值 0.480）** —— 已被处理的人获益更少 · "
                 "分层 $K{=}5$ 消除 **89.7%** 的偏差（对上 Cochran 1968）· "
                 "而 **$K{=}800$ 静默丢弃 22.2% 的样本**，RMSE 反而回落 —— "
                 "*RMSE 不是选层数的正确判据* · "
                 "**未观测混杂的偏差跨 1000 倍样本量稳定在 +0.853** · "
                 "**定向的盈亏平衡噪声 ∝ sd(τ)²/ATE**（二次律，h 翻倍容忍 3.9 倍）"),
            ]),
            ("第二段 · 控制什么，怎么估", [
                ("02_dag_backdoor/02_讲解.html", "MODULE 02",
                 "因果图与识别：后门准则、对撞偏差、中介",
                 "**对撞把系数从 +0.0006 变成 −0.917**（闭式解预测 −0.9174）· "
                 "枚举 8 个子集**只有 1 个合法**，而准则与「回归无偏」完全一致 · "
                 "**只多控制一个变量，偏差从 0.002 变成 −2.596** · "
                 "$\\{X,M\\}$ **精确无偏地估出了直接效应** —— 答对了另一个问题，31% 不留痕迹 · "
                 "**M-bias：控制一个*处理前*变量把偏差从 +0.001 变成 −0.312**"),
                ("03_estimation/03_讲解.html", "MODULE 03",
                 "倾向得分、IPW、双重稳健与双重机器学习",
                 "IPW 用真值倾向得分仍无偏，而 **ESS 从 4000 掉到 616** · "
                 "**截断不是近似 ATE，是换了一个人群**（2.0019 vs 1.4371，"
                 "被排除者效应 +4.96）· "
                 "**两个 bit 级恒等式**：FWL 差 2.2e−16；常数 $\\hat e$ 使 AIPW ≡ G-comp · "
                 "**过拟合把修正项吃掉 4.4e5 倍**，同时 G-comp 崩到 +123.44 · "
                 "而交叉拟合在部分线性得分里**四个设定全部更差**"),
            ]),
            ("第三段 · 后门假设不成立时", [
                ("04_quasi_experiment/04_讲解.html", "MODULE 04",
                 "准实验：DiD、工具变量、断点回归、合成控制",
                 "四种方法的核心假设**都不可检验** · "
                 "**pre-trend $|t|{=}0.77$ 与「平行趋势成立」那行完全相同，而 DiD 偏 +1.50** · "
                 "**2SLS 中位数 1.8009 与 OLS 的 1.7994 无法区分**，"
                 "而均值不可读（**无有限矩**，范围 [−1978.6, +804.9]）· "
                 "**RDD 的偏差来自两侧曲率之差**（对称时最优带宽是全数据）· "
                 "**合成控制的 pre 期拟合预测力是 2/4** —— 掷硬币"),
            ]),
            ("第四段 · 实验有效但口径错", [
                ("05_online_attribution/05_讲解.html", "MODULE 05",
                 "线上归因：SUTVA 与干扰、集群随机化、多触点归因、代理指标",
                 "四种失效**都不产生任何异常统计量** · "
                 "**个体随机化测 1.0026，全局效应 2.00** —— 漏掉 $\\beta/(\\alpha+\\beta)$，"
                 "与样本量无关 · "
                 "**设计效应 $1+(m-1)\\text{ICC}$：实测 10.97 vs 理论 10.80** · "
                 "**只反转曝光时序：转化率一位不变，而 last-touch 份额变了 66.7 个百分点** · "
                 "**代理指标的误差恒等于 $-d$**，与代理选得多好无关"),
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
