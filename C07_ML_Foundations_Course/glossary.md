# 术语词典（中英对照）

> 按模块顺序组织。每条 2–3 句中文释义，保留英文术语，配课程里出现的语境与「为什么重要」。需要复习时按本表自测：能不能用一句话讲清每个词，并说出它在哪个公式/陷阱里出现。

---

## 通用 / 数据处理

- **standardization 标准化**：把每个特征减去均值、除以标准差，使其均值 0、方差 1。梯度下降（让各方向步长可比）、距离类算法（k-means、PCA）、正则化都依赖它；统计量必须只用训练集估计，否则造成数据泄漏。
- **normalization 归一化**：广义地把数据缩放到统一尺度（如 min-max 到 [0,1]，或行归一化到单位范数）。与标准化的区别是是否假设高斯；选哪种取决于下游算法对尺度/分布的敏感性。
- **stratified split 分层划分**：划分 train/test 时保证每个类别的比例与全集一致。在类别不平衡时尤其重要，否则小类可能在某一边样本过少，评估方差巨大。
- **majority baseline 多数类基线**：永远预测样本最多的那一类所得到的准确率。任何模型都必须先打败它才有意义；在 99:1 的不平衡数据上，majority baseline 就有 99% accuracy，这正是 accuracy 失效的经典例子。
- **data leakage 数据泄漏**：测试集（或未来）的信息以任何方式渗入训练或调参，使报告的泛化指标偏乐观且无法复现。最常见三种：用测试集选超参、标准化统计量用了全集、时间序列里用未来预测过去。
- **train / validation / test split**：训练集拟合参数、验证集选超参与早停、测试集只在最后碰一次估计泛化。混用验证与测试是评测里最致命的错误。

## 01 · 矩阵微积分与 backprop

- **chain rule 链式法则**：复合函数求导的乘积/求和规则；多变量版本对「一个变量影响的所有中间量」求和。它是反向传播的全部数学内核，神经网络只是把它套了几十层向量/矩阵。
- **backpropagation 反向传播**：按计算图的拓扑逆序，用「上游梯度 × 局部导数」把 loss 的梯度从输出端传回每个参数。一次反向的计算量约等于一次前向——这是深度学习能 scale 的根本。
- **Jacobian 雅可比矩阵**：向量值函数 $f:\mathbb R^n\to\mathbb R^m$ 的所有偏导排成的 $m\times n$ 矩阵。前向用 $J$、反向用 $J^\top$；网络中几乎不显式构造它（太大），而是直接算雅可比-向量积。
- **VJP / JVP 雅可比-向量积**：VJP（$J^\top v$）是反向模式的核心运算，JVP（$Jv$）是前向模式的。理解二者区别就懂了 reverse-mode（少输出多参数）与 forward-mode（少参数多输出）各自的适用场景。
- **adjoint 伴随量**：反向时每个节点 $v$ 上累积的 $\bar v=\partial L/\partial v$。一个节点被多个下游使用（fan-out）时其伴随量要把各路梯度相加——漏加就错。
- **computational graph 计算图**：把前向计算表示成的有向无环图，节点是运算、边是数据依赖。前向沿图正向求值，反向沿图逆序传梯度；训练时需缓存中间激活供反向使用，这是训练显存大于推理的原因。
- **upstream × local「上游 × 局部」模式**：实现反向的统一模板——每个操作把下游传来的梯度乘以自身局部导数再传给上游。配合「形状法则」即可手写任意层反向。
- **shape rule 形状法则**：梯度 $\nabla_x L$ 必须与被求导的 $x$ 形状完全相同。先想形状再写公式（如 $\bar W$ 与 $W$ 同形 ⇒ 只能是 $X^\top\bar Y$），是面试现场最快的查错法。
- **finite difference 数值差分**：用 $(f(x+\epsilon)-f(x-\epsilon))/2\epsilon$ 中心差分近似导数，截断误差 $O(\epsilon^2)$。gradient check 的安全网，$\epsilon\approx10^{-5}$、必须用 float64（float32 精度不足会假报错误）。
- **gradient check 梯度校验**：用数值梯度逐元素对比解析梯度，看相对误差是否 $<10^{-6}$。手写 backprop 必做的自检。
- **vanishing / exploding gradient 梯度消失 / 爆炸**：深层雅可比连乘使梯度按层数指数趋 0 或趋 ∞。sigmoid 饱和导致消失；残差连接（雅可比含 $I$）、归一化、梯度裁剪、ReLU 是对策。诊断靠打印 per-layer 梯度范数。
- **automatic differentiation 自动微分 (AD)**：框架按计算图自动应用链式法则。reverse-mode（PyTorch/JAX 的 backprop）对标量 loss 高效；micrograd 是其约 150 行的最小实现。
- **activation checkpointing 激活重算**：反向时不缓存全部前向激活，而在需要时重算部分前向，用时间换显存。长上下文/大模型训练的关键工程手段。

## 02 · 概率统计与信息论

- **likelihood 似然 / log-likelihood 对数似然**：在给定参数下观测到当前数据的概率（密度）。取对数把连乘变连加，便于求导与避免数值下溢，是 MLE 的工作对象。
- **MLE 最大似然估计**：选使观测数据似然最大的参数。高斯 MLE 有闭式解 $\hat\mu=\bar x$、$\hat\sigma^2=\frac1n\sum(x_i-\bar\mu)^2$（用 $/n$，是有偏的）；MLE 渐近无偏、渐近有效（达 Cramér–Rao 下界）。
- **MAP 最大后验估计**：在 MLE 上加先验 $p(\theta)$ 后最大化后验。关键等价：高斯先验的 MAP = L2 正则、拉普拉斯先验的 MAP = L1 正则——把「正则化」从启发式变成概率推断。
- **Cramér–Rao bound 克拉默-罗下界**：任何无偏估计量方差的理论下界（Fisher 信息的倒数）。MLE 渐近达到它，所以说 MLE「渐近有效」。
- **prior / posterior 先验 / 后验**：参数在看到数据前/后的分布，由贝叶斯定理 $p(\theta\mid x)\propto p(x\mid\theta)p(\theta)$ 连接。weight decay 的标准答案就是「零均值高斯先验下的 MAP」。
- **hypothesis test 假设检验**：设零假设 $H_0$（如两模型无差异），算检验统计量，看在 $H_0$ 下出现这么极端结果的概率（p 值），p 小则拒绝 $H_0$。评测里「A 真的比 B 好吗」就是它。
- **p-value p 值**：在 $H_0$ 成立时，观察到当前或更极端结果的概率。它**不是**「A 更好的概率」，也**不是**差异大小；小样本下真实差异常被噪声淹没。
- **t-test t 检验 / paired vs unpaired**：比较两组均值的参数检验（假设近似正态）。配对设计（同样的题两个模型都做）比独立设计功效高得多，应优先采用。
- **statistical power 统计功效**：在真有差异时正确拒绝 $H_0$ 的概率。样本量太小则功效低，看不出真实差异；system design 题里「样本量够不够」就是功效分析。
- **permutation test 置换检验**：把两组的标签随机打乱多次构造零分布，看真实统计量排在多极端处得 p 值。只需「$H_0$ 下标签可交换」假设，不假设分布形态，适合小样本。
- **entropy 熵**：分布自身的不确定性 $H(p)=-\sum p\log p$。均匀分布熵最大；它是无损编码该分布所需的平均比特/纳特数下界。
- **cross-entropy 交叉熵**：用分布 $q$ 编码真实分布 $p$ 的平均代价 $H(p,q)=-\sum p\log q$。神经网络分类/语言模型的训练 loss 就是它。
- **KL divergence KL 散度**：$D_{\mathrm{KL}}(p\|q)=H(p,q)-H(p)\ge0$（Gibbs 不等式，等号当且仅当 $p=q$）。**不对称**：$D(p\|q)\ne D(q\|p)$。forward KL（$p\|q$）mode-covering、reverse KL（$q\|p$）mode-seeking。
- **perplexity 困惑度**：交叉熵的指数 $\mathrm{PPL}=e^{\text{CE}}$，直觉是「模型每步平均在多少个等概率候选里犹豫」。语言模型评测的核心数，PPL 越低越好。
- **nats vs bits**：用自然对数算熵得 nats，用 $\log_2$ 得 bits；换底只差常数 $\ln 2$，但报告时必须说清单位。
- **multiple comparisons 多重比较**：跑很多个检验时，纯靠运气也会出现假阳性（跑 20 个 benchmark，约有一个 $p<0.05$）。需用 Bonferroni 或 FDR 校正控制总体错误率。

## 03 · 经典监督学习

- **ERM 经验风险最小化**：在假设空间 $\mathcal F$ 里找使平均损失最小的函数 $\hat f$（可加正则项）。所有监督学习都是它的实例，区别只在 $\mathcal F$、损失 $\ell$、优化方式。
- **OLS 普通最小二乘**：最小化 $\|Xw-y\|^2$，闭式解 $\hat w=(X^\top X)^{-1}X^\top y$（正规方程）。几何上残差与列空间正交；实践用 `lstsq`/`pinv`（基于 SVD）防共线性导致的病态求逆。
- **normal equation 正规方程**：对平方损失求导置零得到的 $X^\top X\,w=X^\top y$。是 OLS 闭式解的来源，也是最常考的推导题之一。
- **R² 决定系数**：$1-\mathrm{SS_{res}}/\mathrm{SS_{tot}}$。$R^2=1$ 完美、$0$ 等于只猜均值、可为负（比猜均值还差）；衡量回归解释了多少方差。
- **logistic regression 逻辑回归**：线性输出过 sigmoid 得概率，损失是 BCE（伯努利负对数似然）。无闭式解，用梯度下降；梯度是「残差左乘输入」$\frac1n X^\top(\sigma(Xw)-y)$，目标凸。决策边界是超平面。
- **BCE 二元交叉熵**：二分类损失，等于伯努利分布的负对数似然；与 sigmoid 配对时梯度化简为干净的 $p-y$。
- **decision tree 决策树 / CART**：用贪心切分把数据递归分成更纯的子节点，假设空间是轴对齐的分段常数函数。可解释、不需标准化、能抓非线性与交互，但极易过拟合（足够深可记住整个训练集）。
- **Gini impurity / entropy 不纯度**：节点纯度度量，Gini $=1-\sum_c p_c^2$、熵 $=-\sum_c p_c\log p_c$。决策树每步选使加权子节点不纯度最低的切分。
- **information gain 信息增益**：父节点不纯度减去加权子节点不纯度，即一次切分带来的纯度提升，是决策树选切分的准则。
- **bagging 装袋**：训练多个高方差低偏差模型（每个看不同 bootstrap 子样本）再平均，方差按 $\approx\rho\sigma^2+\frac{1-\rho}{B}\sigma^2$ 下降（$\rho$ 是模型间相关性）。降方差不降偏差。
- **random forest 随机森林**：bagging + 每次切分只看随机特征子集，进一步降低树间相关性 $\rho$，方差更低。表格数据上的强 baseline。
- **boosting 提升**：串行训练，每个新模型纠正前面模型的残差/错误，加权累加。降偏差为主，代表是 GBDT / XGBoost；与 bagging 的并行降方差互补。
- **SVM 支持向量机 / margin 间隔**：寻找使两类间隔（margin）最大的分隔超平面，只由少数支持向量决定。hinge loss 是其损失形式；核技巧（kernel trick）用内积把线性方法推广到非线性边界而不显式升维。

## 04 · 无监督学习

- **PCA 主成分分析**：找一组正交方向使投影后方差最大（等价于重构误差最小，Eckart–Young）。做法是中心化后对协方差矩阵特征分解，或直接对 $X$ 做 SVD（数值更稳）。
- **SVD 奇异值分解**：$X=U\Sigma V^\top$。PCA 的主成分方向就是 $V$ 的列、第 $k$ 个解释方差正比于 $\sigma_k^2$；用 SVD 避免显式构造可能病态的 $X^\top X$。
- **explained variance ratio 解释方差比**：$\sigma_k^2/\sum_j\sigma_j^2$，前几个主成分抓住了多少信息。常用它选降维维度（如累计 95%）。
- **k-means / Lloyd 算法**：硬聚类，最小化簇内平方和（inertia），交替「把点分到最近中心（E 步）+ 中心取簇内均值（M 步）」。每步不增 inertia 故收敛，但只到局部最优、强依赖初始化。
- **inertia 簇内平方和**：$\sum_i\|x_i-\mu_{c_i}\|^2$，k-means 的目标函数；用「肘部法」看 inertia 随 $k$ 的拐点选簇数。
- **k-means++**：用「离已选中心越远越可能被选」的方式初始化中心，带理论保证地缓解 k-means 陷入劣质局部最优；实践仍建议多次随机重启取最优。
- **GMM 高斯混合模型**：假设数据来自 $K$ 个高斯的混合，给出软分配——每个点属于每个簇的概率（responsibility $\gamma_{ik}$）。k-means 是它「协方差 $\to0$、硬分配」的特例。
- **EM 算法 期望最大化**：拟合含隐变量模型的通用框架。E 步用当前参数算软分配（后验），M 步用软分配更新参数；单调增加（边际）对数似然，只保证局部最优。HMM、LDA、半监督都用它。
- **responsibility 责任值**：GMM 中点 $i$ 属于簇 $k$ 的后验概率 $\gamma_{ik}$，E 步算出、M 步当权重用。
- **ELBO 证据下界**：EM/变分推断里对数似然的 Jensen 下界；EM 可理解为交替最大化 ELBO（E 步收紧界、M 步抬高界）。
- **cluster purity / ARI / NMI 聚类评估（有标签）**：purity 是每簇取众数真实标签的正确率；ARI（调整兰德指数）、NMI（归一化互信息）是更稳健的对比真实划分的指标。
- **silhouette 轮廓系数**：无外部标签时衡量簇的紧密与分离程度（点到本簇 vs 最近他簇的平均距离），用于在没有真值时评估聚类质量。

## 05 · 优化器

- **gradient descent / SGD 梯度下降 / 随机梯度下降**：$\theta\leftarrow\theta-\eta\nabla L$。SGD 用一个 mini-batch 估计梯度，快且其噪声反而能帮助逃离尖锐局部最优，代价是收敛路径震荡。
- **learning rate 学习率 $\eta$**：最重要的超参数，没有之一。太大发散/震荡，太小慢或卡平台；调参第一步永远是按量级（如 1e-2 到 1e-5）扫描它。
- **momentum 动量**：累积历史梯度的指数移动平均 $v_t=\beta v_{t-1}+g_t$（$\beta\approx0.9$），像有惯性的小球，沿一致方向加速、抵消峡谷里的来回横跳。
- **Nesterov momentum**：先按惯性「前瞻」一步再算梯度，理论收敛更快；直觉是小球先冲到前面看坡度再决定。
- **AdaGrad**：按历史梯度平方和的根缩放每个参数步长，适合稀疏特征；缺点是分母只增不减，后期步长趋零而过早停止学习。
- **RMSProp**：把 AdaGrad 的「累积和」换成指数移动平均，分母不再无限增长，解决了后期步长消失的问题。
- **Adam**：动量 + RMSProp + 偏差校正。维护一阶矩 $m_t$ 与二阶矩 $v_t$，更新 $\theta\leftarrow\theta-\eta\,\hat m_t/(\sqrt{\hat v_t}+\epsilon)$；自适应学习率使其对超参较鲁棒，是事实上的默认。
- **bias correction 偏差校正**：$m,v$ 初始化为 0，前几步严重偏小；除以 $1-\beta^t$ 把它们放大回正确量级。去掉它会让前期收敛明显变慢。
- **AdamW / decoupled weight decay**：Adam 把 L2 当成梯度的一部分会被自适应分母 $\sqrt{\hat v}$ 缩放、对大梯度参数正则不足；AdamW 把 weight decay 拎出来直接作用于参数（$-\eta\lambda\theta$），泛化更好，是今天几乎所有大模型的默认。
- **learning rate schedule 学习率调度**：训练中按计划改变 $\eta$。warmup（前期线性升，防早期随机参数下大梯度炸）+ cosine decay（之后余弦平滑降到近 0，后期精修）是现代标配。
- **warmup 预热**：训练初期从 0 线性升到峰值学习率，让随机初始化的参数先稳定，避免一上来大 lr 把训练推飞。
- **gradient clipping 梯度裁剪**：当全局梯度范数超过阈值时整体缩放回来，只改幅度不改方向，是对梯度爆炸最直接的急救手段。
- **flat minima 平坦极小**：泛化往往更好的极小点；SGD 的噪声被认为隐式偏好平坦极小，是「为什么 SGD 泛化好」的一个解释。

## 06 · 泛化与指标

- **bias-variance decomposition 偏差-方差分解**：平方损失下期望测试误差 = 偏差² + 方差 + 不可约噪声 $\sigma^2$。高偏差=欠拟合（train/test 都差），高方差=过拟合（train 好 test 差）。
- **regularization 正则化**：通过惩罚模型复杂度控制方差。L2（岭）把权重往 0 拉、抗共线性（= 高斯先验 MAP）；L1（lasso）产生稀疏解、做特征选择（= 拉普拉斯先验 MAP）。
- **early stopping 早停**：在验证集 loss 开始回升时停训，是一种隐式正则，等价于限制了优化走过的模型复杂度。
- **double descent 双下降**：模型容量越过插值点后测试误差二次下降的现象，是对经典 U 形 bias-variance 曲线的现代补充，解释了过参数化网络为何仍能泛化。
- **confusion matrix 混淆矩阵**：二分类的 TP/FP/TN/FN 四个数，所有分类指标都由它派生。
- **precision / recall / F1**：precision = 喊「是」的里头真是的比例（别乱喊，垃圾邮件场景重视）；recall = 真「是」的里头抓到的比例（别漏，癌症筛查重视）；F1 是两者的调和平均。
- **ROC curve / AUC**：各阈值下 (FPR, TPR) 连成的曲线及其下面积。AUC = 随机正样本分数高于随机负样本的概率，不依赖阈值与类别比例，是排序能力的纯净度量（0.5 瞎猜、1.0 完美）。
- **PR curve / PR-AUC**：precision-recall 曲线及其下面积。极不平衡时负样本海量使 FPR 不敏感、ROC 过于乐观，此时 PR-AUC 对正类的稀有更敏感、更诚实。
- **calibration 校准**：模型说「80% 概率」时实际是否真有 80% 为正。好的排序（高 AUC）≠ 好的校准；现代神经网络普遍过自信。
- **reliability diagram / ECE**：把预测概率分桶，画每桶「平均预测概率 vs 实际正类比例」即可靠性图；ECE（期望校准误差）是各桶差异的加权平均，量化校准好坏。
- **temperature scaling 温度缩放**：给 logit 除以一个在验证集上拟合的温度 $T$ 的事后校准，不改排序只改概率尺度；对过自信网络几乎是标配。

## 07 · 面试 drills / 评估方法

- **softmax + cross-entropy 梯度**：$\partial L/\partial z=p-y_{\text{onehot}}$（预测概率减真值）。推导用 softmax 雅可比 $p_i(\delta_{ik}-p_k)$ 代入化简；实现 softmax 必须先减最大值再取指数防 overflow。
- **softmax 数值稳定**：计算 $e^{z}$ 前减去 $\max z$，结果不变但避免大 logit 溢出成 inf。面试与真实代码都会被抓的细节。
- **k-fold cross-validation k 折交叉验证**：把数据分 $k$ 折轮流验证、其余训练，平均 $k$ 个验证分。比单次划分方差小，用于稳健地选超参；测试集只在最后碰一次。
- **nested CV 嵌套交叉验证**：外层估泛化、内层选超参，避免「用于选超参的验证分」泄漏进泛化估计。
- **bootstrap CI 自助置信区间**：从数据有放回重采样多次、每次算指标得经验分布，取 2.5%/97.5% 分位数即 95% 置信区间。不假设分布，是给所有 eval 分数配误差棒的核心技术。
- **Bayes rule / base rate fallacy 贝叶斯定理 / 基率谬误**：$P(A\mid B)\propto P(B\mid A)P(A)$。基率谬误指忽视先验概率：罕见病即使检测很准，阳性后真患病的后验仍可能很低（医检经典题）。
- **Goodhart's law 古德哈特定律**：一个指标一旦成为优化目标，就不再是好指标。评测里表现为 benchmark 过拟合、reward hacking——system design 题必须讨论的失败模式。
- **eval system design 框架**：回答「设计一个评估 X 的系统」的五步——明确目标与口径 → 数据（来源/标注/污染/泄漏/覆盖/样本量）→ baseline（majority/随机/简单模型）→ 指标与误差棒（结合不平衡/校准/排序 + 置信区间 + 显著性）→ 失败模式与监控（Goodhart、过拟合、reward hacking）。
