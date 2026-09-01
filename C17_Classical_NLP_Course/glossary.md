# 术语词典 · Glossary（经典 NLP）

> 按主题分组，每条 2–3 句释义。读 Jurafsky & Martin《SLP》、word2vec / GloVe / CRF 等论文遇到生词回这里查；英文术语保留原文（学界通用语言）。本课全部用纯 numpy 从零实现这些概念，术语与经典文献一一对应。

## 基础概念与分布语义 · Foundations & Distributional Semantics

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| token / type | 词例 / 词型 | token 是文本中出现的每一个词的实例（running 一次出现算一个 token）；type 是去重后的不同词（vocabulary 的元素）。一篇文档有 N 个 token、V 个 type。|
| vocabulary | 词表 | 模型认识的所有 type 的集合，常记为 $V$。词表外的词叫 OOV（out-of-vocabulary），需用 `<unk>` 等特殊符号处理。|
| corpus | 语料库 | 用于训练/评测的文本集合。经典 NLP 的一切统计量（共现、n-gram 计数、词频）都从语料库估计而来，语料的规模与领域直接决定模型质量。|
| distributional hypothesis | 分布假设 | Firth 的名言「You shall know a word by the company it keeps」：意义相近的词出现在相似的上下文里。这是词嵌入、共现矩阵、几乎所有现代表示学习的哲学根基。|
| co-occurrence matrix | 共现矩阵 | 一个 $V\times V$（或词×上下文）矩阵，元素 $X_{ij}$ 记录词 $i$ 与词 $j$ 在窗口内共同出现的次数。分布假设的最直接量化，GloVe 直接对它建模。|
| context window | 上下文窗口 | 中心词左右各取 $m$ 个词构成的窗口。窗口大小是 word2vec/共现的关键超参：窗口大偏向主题相关（topical），窗口小偏向句法/近义（syntactic）。|
| word embedding | 词嵌入 / 词向量 | 把每个词映射到一个稠密低维实向量（如 100–300 维），使语义/句法关系对应向量空间中的几何关系。相对 one-hot 的稀疏高维，embedding 稠密、可泛化、可做算术。|
| one-hot vector | 独热向量 | 长度为 $V$、只有对应词那一位为 1 其余为 0 的向量。它把任意两个不同词的相似度都视为 0，无法表达语义关系，是 embedding 要取代的起点。|
| dense / sparse representation | 稠密 / 稀疏表示 | 稠密向量每一维都可能非零、维度低（embedding）；稀疏向量绝大多数为零、维度高（one-hot、词袋）。稠密表示能泛化到未见组合，是分布式表示的核心优势。|
| cosine similarity | 余弦相似度 | 两向量夹角的余弦 $\cos\theta = \frac{u\cdot v}{\Vert u\Vert \Vert v\Vert }\in[-1,1]$，衡量方向是否一致而忽略长度。是比较词向量语义接近程度的标准度量。|

## 词嵌入与 word2vec · Word Embeddings & word2vec

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| word2vec | —— | Mikolov 等 2013 提出的高效词向量训练框架，含 skip-gram 与 CBOW 两种结构，配合负采样/层次 softmax。它让在十亿词级语料上训词向量变得实际可行，引爆了分布式表示的浪潮。|
| skip-gram | 跳字模型 | word2vec 的一种：用**中心词预测上下文词**。对每个中心-上下文对最大化条件概率，擅长低频词、小语料下表现稳健。本课主推它配负采样。|
| CBOW (Continuous Bag-of-Words) | 连续词袋模型 | word2vec 的另一种：用**上下文词（求和/平均）预测中心词**。训练更快、对高频词更友好，与 skip-gram 互为镜像。|
| negative sampling | 负采样 | 把「在整个词表上做 softmax」近似成「区分一个真实上下文词与 $k$ 个随机抽的负样本」的二分类。用 logistic 损失，把每步代价从 $O(V)$ 降到 $O(k)$，是 word2vec 可扩展的关键。|
| noise distribution | 噪声分布 | 负采样时抽取负样本所用的分布，word2vec 用**词频的 3/4 次方** $P(w)\propto f(w)^{0.75}$。这个指数压低高频词、抬高低频词，经验上显著优于直接按词频或均匀抽。|
| hierarchical softmax | 层次 softmax | 用一棵哈夫曼树把 $V$ 路 softmax 分解成 $\log V$ 个二分类，是负采样之外另一种避开 $O(V)$ 归一化的方法。本课以负采样为主，层次 softmax 作对照了解。|
| input / output embedding | 输入 / 输出词向量 | word2vec 为每个词维护两套向量：作为中心词时用输入向量 $v_w$，作为上下文词时用输出向量 $u_w$。最终词向量常取 $v_w$ 或 $v_w+u_w$。|
| GloVe (Global Vectors) | —— | Pennington 等 2014 的词向量方法：直接对**全局共现计数的对数**做加权最小二乘拟合，让 $w_i\cdot w_j+b_i+b_j\approx\log X_{ij}$。它显式利用全局统计，与 word2vec 的局部窗口形成互补。|
| weighting function | 加权函数 | GloVe 损失里对每个共现对的权重 $f(X_{ij})$：对极低频共现降权（噪声大）、对极高频共现封顶（避免 the/of 主导），形如 $\min((x/x_{\max})^\alpha,1)$。|
| analogy (word analogy) | 词类比 | 「king − man + woman ≈ queen」式的向量算术。它揭示词向量空间里某些语义/句法关系近似为**平行的位移向量**，是评估 embedding 质量的经典定性/定量任务。|
| PMI / PPMI | （正）点互信息 | $\mathrm{PMI}(i,j)=\log\frac{P(i,j)}{P(i)P(j)}$ 衡量两词共现是否超出独立假设；PPMI 把负值截断为 0。对 PPMI 矩阵做 SVD 可得到与 word2vec 理论上相通的词向量。|

## 语言模型与平滑 · Language Models & Smoothing

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| language model (LM) | 语言模型 | 给词序列赋概率 $P(w_1,\dots,w_n)$ 的模型，等价于「预测下一个词」。它是机器翻译、语音识别、输入法乃至今天 GPT 的共同底座。|
| n-gram | n 元语法 | 连续 $n$ 个词构成的片段；n-gram 模型用前 $n-1$ 个词预测第 $n$ 个。$n=1$ 是 unigram、$n=2$ bigram、$n=3$ trigram。$n$ 越大上下文越长但数据越稀疏。|
| Markov assumption | 马尔可夫假设 | 近似「下一个词只依赖前 $n-1$ 个词」，即 $P(w_t\mid w_1^{t-1})\approx P(w_t\mid w_{t-n+1}^{t-1})$。它把指数级的历史压成可数的条件，是 n-gram 模型成立的前提。|
| maximum likelihood estimation (MLE) | 最大似然估计 | n-gram 概率的最朴素估计：$P(w_n\mid w_{1}^{n-1})=\frac{\mathrm{count}(w_1^n)}{\mathrm{count}(w_1^{n-1})}$，即频率比。它对见过的串无偏，但对没见过的串给 0 概率（灾难）。|
| zero-probability problem | 零概率问题 | MLE 给任何训练中未出现的 n-gram 赋概率 0，导致整句概率为 0、困惑度为无穷。平滑（smoothing）就是为解决它而生。|
| smoothing | 平滑 | 把一部分概率质量从「见过的」事件挪给「没见过的」事件，使每个 n-gram 都有非零概率。经典方法有 Laplace、Good-Turing、Kneser-Ney。|
| Laplace / add-one smoothing | 拉普拉斯 / 加一平滑 | 给每个 n-gram 计数都加 1（或加 $\delta$）再归一：$P=\frac{c+\delta}{N+\delta V}$。简单但对大词表过度削峰、效果差，主要作教学起点。|
| Good-Turing smoothing | 古德-图灵平滑 | 用「出现 $r+1$ 次的事件数」重估「出现 $r$ 次的事件」的概率，把概率质量按出现频次的频次（frequency of frequencies）重新分配。是 Kneser-Ney 的思想前身。|
| Kneser-Ney smoothing | KN 平滑 | 公认最强的 n-gram 平滑。两大创新：**绝对折扣**（每个计数减去常数 $d$）与**续延概率**（低阶分布用「该词跟在多少种不同词后面」而非词频来估计）。`San` 后面几乎只接 `Francisco`，故 `Francisco` 的续延概率应低——这是 KN 的精髓。|
| absolute discounting | 绝对折扣 | 从每个非零计数里减去一个固定折扣 $d\in(0,1)$，把省下的概率质量匀给低阶模型。比例上对高频项影响小、对低频项影响大，符合 Good-Turing 的经验规律。|
| continuation probability | 续延概率 | KN 平滑的核心量：一个词作为「续延」的概率正比于它跟在**多少种不同**前文之后，而非它出现多少次。它修正了「高频但语境单一」的词被高估的问题。|
| backoff | 回退 | 高阶 n-gram 没见过时，「退」到低阶模型（trigram→bigram→unigram）。Katz backoff 用 Good-Turing 折扣出的质量分给回退项，需保证归一。|
| interpolation | 插值 | 把各阶 n-gram 概率加权混合：$\lambda_3 P_3+\lambda_2 P_2+\lambda_1 P_1$，$\sum\lambda=1$。与回退不同，插值**总是**混合所有阶，权重可在验证集上学。|
| perplexity (PPL) | 困惑度 | 语言模型的标准内在评测：$\mathrm{PPL}=P(w_1^N)^{-1/N}=\exp(-\frac1N\sum\log P(w_i\mid\cdot))$，即每词平均分支数的几何均值。越低越好；它就是交叉熵的指数。|
| cross-entropy | 交叉熵 | $H=-\frac1N\sum\log_2 P(w_i\mid\cdot)$，每词的平均编码比特数。困惑度 $=2^H$（或 $e^H$，取决于底）。是连接信息论与语言模型评测的桥梁。|

## 隐马尔可夫模型 · Hidden Markov Models

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| HMM (Hidden Markov Model) | 隐马尔可夫模型 | 一个生成式序列模型：隐藏状态序列按马尔可夫链转移，每个状态发射一个可观测符号。参数为初始分布 $\pi$、转移矩阵 $A$、发射矩阵 $B$。经典用于词性标注、语音识别。|
| hidden state | 隐藏状态 | 不可直接观测、需从观测推断的变量（如词性标签）。HMM 假设当前隐状态只依赖前一隐状态（一阶马尔可夫）。|
| observation / emission | 观测 / 发射 | 由隐状态生成的可见符号（如具体的词）。发射概率 $B_{ij}=P(o=j\mid s=i)$ 指状态 $i$ 发出观测 $j$ 的概率。|
| transition probability | 转移概率 | $A_{ij}=P(s_t=j\mid s_{t-1}=i)$，从隐状态 $i$ 转到 $j$ 的概率。每行是一个概率分布，$\sum_j A_{ij}=1$。|
| forward algorithm | 前向算法 | 用动态规划计算观测序列的似然 $P(O\mid\lambda)$。前向变量 $\alpha_t(i)=P(o_1^t, s_t=i)$ 满足递推 $\alpha_t(j)=\big(\sum_i\alpha_{t-1}(i)A_{ij}\big)B_{j,o_t}$，把指数级求和降到 $O(T S^2)$。|
| backward algorithm | 后向算法 | 与前向对称：$\beta_t(i)=P(o_{t+1}^T\mid s_t=i)$。前向×后向给出每个位置的状态后验，是 Baum-Welch（EM）的 E 步所需。|
| Viterbi algorithm | 维特比算法 | 用动态规划找**最可能的隐状态序列** $\arg\max_S P(S\mid O)$。结构与前向相同，但把求和换成取最大，并记录回溯指针。实践中在对数空间做以防下溢。|
| Baum-Welch / forward-backward | 鲍姆-韦尔奇算法 | HMM 的无监督参数学习，是 EM 算法的特例：E 步用前向-后向算状态/转移的期望计数，M 步用期望计数重估 $\pi,A,B$，迭代到收敛。|
| log-space computation | 对数空间计算 | 长序列里连乘大量小概率会下溢为 0。把概率取对数、连乘变连加、用 log-sum-exp 做加法，是前向/Viterbi 的标准数值技巧。|
| log-sum-exp trick | LSE 技巧 | 稳定计算 $\log\sum_i e^{x_i}=m+\log\sum_i e^{x_i-m}$（$m=\max x_i$），避免 $e^{x_i}$ 溢出。前向算法在对数空间求和、CRF 配分函数都靠它。|
| supervised estimation | 监督估计 | 当训练数据带标签（词→词性）时，HMM 参数可直接数频率：$\pi,A,B$ 全是计数比，配合平滑处理未见项。比 Baum-Welch 简单且通常更好。|
| POS tagging | 词性标注 | 给每个词标注词性（名词/动词/…）的序列标注任务。HMM 与 CRF 的经典试金石，也是句法分析、信息抽取的上游步骤。|

## CRF 与结构化预测 · CRF & Structured Prediction

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| generative vs discriminative | 生成式 vs 判别式 | 生成式建模联合分布 $P(x,y)$（如 HMM、朴素贝叶斯），可生成数据；判别式直接建模条件 $P(y\mid x)$（如 CRF、logistic 回归），通常预测更准、能用任意重叠特征。|
| CRF (Conditional Random Field) | 条件随机场 | Lafferty 等 2001 提出的判别式结构化模型，直接建模 $P(y\mid x)$ 且在整个序列上全局归一。线性链 CRF 是 HMM 的判别式对应，是 2010 年代序列标注的主力。|
| linear-chain CRF | 线性链 CRF | 标签间只有相邻依赖（链式结构）的 CRF，可用与 HMM 同构的前向-后向/Viterbi 高效推断。NER、分词、POS 的标配。|
| feature function | 特征函数 | CRF 的基本构件 $f_k(y_{t-1}, y_t, x, t)$，对「标签转移＋观测上下文」打分。可任意设计、可重叠（词本身、前缀后缀、是否大写、词形…），这是 CRF 相对 HMM 的最大自由度。|
| feature template | 特征模板 | 批量生成特征函数的规则，如「当前词＝? 且标签＝?」「前一标签＝? 且当前标签＝?」。模板实例化到语料上产生百万级特征，是经典 NER 的工程核心。|
| partition function | 配分函数 | CRF 概率的归一化项 $Z(x)=\sum_{y'}\exp(\mathrm{score}(y',x))$，对所有可能标签序列求和。线性链下用前向算法在对数空间 $O(TS^2)$ 算出 $\log Z$，是训练（求梯度）的关键。|
| log-linear model | 对数线性模型 | 形如 $P(y\mid x)=\frac1Z\exp(\sum_k\lambda_k f_k)$ 的模型族，CRF、最大熵（MaxEnt）、softmax 回归都属此类。对数概率是特征的线性函数。|
| structured perceptron | 结构化感知机 | Collins 2002 提出的简洁判别式训练法：用 Viterbi 预测整条序列，若与真值不同就「真值特征 +1、预测特征 −1」。无需算配分函数，实现极简却很有效，是理解 CRF 的最佳跳板。|
| Viterbi (in CRF) | CRF 的维特比 | 与 HMM 同构：把转移＋发射换成特征加权得分，求得分最高的标签序列。是 CRF/结构化感知机的解码（预测）步骤。|
| BIO / BIOES tagging | BIO 标注体系 | 把「分块/实体识别」转成逐词标注：B-（实体开始）、I-（实体内部）、O（非实体）。NER 的标准标签编码，使序列标注模型能输出跨多词的实体。|
| NER (Named Entity Recognition) | 命名实体识别 | 从文本中找出人名、地名、机构名等专有实体并分类。CRF 在深度学习前是 NER 的统治方法，CoNLL-2003 是其标准评测。|
| feature-based vs neural | 特征工程 vs 神经 | 经典 CRF 靠人工设计特征模板；现代 BiLSTM-CRF / BERT-CRF 用神经网络自动学特征、CRF 层只管标签依赖。理解经典 CRF 是读懂这些混合架构的前提。|

## 文本分类与评测 · Text Classification & Evaluation

| 术语 (EN) | 中文 | 释义 |
|-----------|------|------|
| tokenization | 分词 | 把原始字符串切成 token（词/子词）的第一步。英文按空格/标点切，中文需分词算法；分词口径直接影响下游所有统计。|
| normalization | 归一化 | 统一文本形态：小写化、去标点、词干提取（stemming）、词形还原（lemmatization）、去停用词等。目的是把同一含义的不同写法合并，降低稀疏。|
| stemming / lemmatization | 词干提取 / 词形还原 | stemming 用规则粗暴砍词缀（running→run，但 happily→happili）；lemmatization 借词典与词性还原到词典词元（better→good）。后者更准但更重。|
| stop words | 停用词 | the、is、of 等高频但信息量低的功能词。经典分类中常去除以降噪降维，但在某些任务（情感、作者识别）里它们反而有用，需谨慎。|
| bag-of-words (BoW) | 词袋模型 | 把文档表示成「词→计数」的向量，完全忽略词序。简单、强基线，是 TF-IDF 与朴素贝叶斯的输入表示。|
| TF-IDF | 词频-逆文档频率 | $\mathrm{tfidf}(t,d)=\mathrm{tf}(t,d)\cdot\log\frac{N}{\mathrm{df}(t)}$。用词在文档内的频率（TF）乘以它在语料中的稀有度（IDF），压低 the/of 等普遍词、抬高有区分度的词。经典检索与分类的支柱特征。|
| term frequency (TF) | 词频 | 词 $t$ 在文档 $d$ 中的出现次数（或其对数/归一化变体）。衡量该词对这篇文档的局部重要性。|
| inverse document frequency (IDF) | 逆文档频率 | $\log\frac{N}{\mathrm{df}(t)}$，$\mathrm{df}(t)$ 是含词 $t$ 的文档数。出现在越少文档里的词 IDF 越高、越有区分力。|
| naive Bayes | 朴素贝叶斯 | 基于贝叶斯定理＋「特征条件独立」假设的生成式分类器。$P(c\mid d)\propto P(c)\prod_t P(t\mid c)$，配合拉普拉斯平滑。训练只数频率、极快，是文本分类的经典强基线。|
| logistic regression | 逻辑回归 | 判别式线性分类器，用 sigmoid/softmax 把特征线性组合压成概率，靠梯度下降最小化交叉熵。能用任意（重叠）特征，常胜过朴素贝叶斯，是 CRF 的「无结构」特例。|
| precision / recall | 精确率 / 召回率 | precision $=\frac{TP}{TP+FP}$（预测为正里有多少真对）；recall $=\frac{TP}{TP+FN}$（真正例里找回多少）。二者通常此消彼长，需结合任务权衡。|
| F1 score | F1 值 | precision 与 recall 的调和平均 $F_1=\frac{2PR}{P+R}$。对不平衡数据比 accuracy 更可靠，是分类/NER 的主流单一指标。|
| macro / micro average | 宏 / 微平均 | 多类时，macro 对每类 F1 取算术平均（每类等权，凸显小类）；micro 把所有类的 TP/FP/FN 汇总后算一次（被大类主导）。报告时需说明用哪种。|
| confusion matrix | 混淆矩阵 | 行=真实类、列=预测类的计数表，对角线是正确预测。它把模型「把谁错认成谁」一览无余，是诊断分类错误的起点。|
| accuracy | 准确率 | 预测正确的样本占比。直观但在类别不平衡时具有误导性（全猜多数类也能高 accuracy），故分类任务常以 F1 为主、accuracy 为辅。|
