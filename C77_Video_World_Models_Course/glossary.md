# C77 术语词典 · 视频与世界模型

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
