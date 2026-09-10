# C76 术语词典 · 因果推断与线上归因

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
