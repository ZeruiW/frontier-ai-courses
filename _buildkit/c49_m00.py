# -*- coding: utf-8 -*-
"""C49 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "C01（LLM 内核：注意力与 Transformer）或等价基础；numpy；读过 C17（经典 NLP）更好但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 从零实现 + 与理论/参考实现对拍"),
    ("预计时长", "总览 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么", "".join([
        P("欢迎来到 <strong>编码器与 Seq2Seq 模型家族</strong>。这门课补的是一个在 2023 年之后被普遍忽略、但在工业界仍然天天用到的洞：<strong>Transformer 不只有 decoder-only 这一种形态</strong>。"),
        P("如果你的 Transformer 知识是从 GPT 系列学起的（多数人如此，C01 也是这个路线），那么你熟悉的是<em>因果注意力 + 下一个 token 预测 + 自回归生成</em>这一套。这套东西极其成功，以至于容易让人以为它就是 Transformer 的全部。但实际上，原始 Transformer（Vaswani et al. 2017）是一个 <strong>encoder-decoder</strong> 架构，BERT 打开的是 <strong>encoder-only</strong> 这条线，T5/BART 走的是 <strong>encoder-decoder</strong> 的复兴。<em>三种形态解决的是不同的问题，各自的注意力掩码、预训练目标、推理成本都不一样</em>。"),
        DUAL(
            "为什么现在还要学这个？三个非常实际的理由。<strong>其一，工业界大量在跑</strong>——分类、NER、意图识别、内容审核、检索的 embedding 与 reranker，这些场景里 BERT 系模型（及其后代）仍是默认选择，因为它们<em>快一到两个数量级、便宜同样的数量级</em>。<strong>其二，面试与 JD 明确要求</strong>——「hands-on experience with GPT, BERT, RoBERTa, LLaMA」「expertise in NLP and sequence-to-sequence models」是标准写法。<strong>其三，也是最重要的：理解三种形态的差异，你才真正理解注意力掩码与预训练目标是<em>可设计的</em>，而不是天经地义的。</strong>",
            "更技术地说，三种形态的本质区别只有<strong>一件事：注意力掩码矩阵的形状</strong>。encoder-only 用全 1 的双向掩码（每个位置能看到所有位置），decoder-only 用下三角的因果掩码，encoder-decoder 则是「编码器双向 + 解码器因果 + 交叉注意力全可见」。<em>其余的一切差异——预训练目标能不能做、能不能自回归生成、推理成本是 O(1) 次前向还是 O(n) 次——都是从这一个矩阵推导出来的</em>。本课就沿着这条线索把三种形态拆开重建。",
        ),
        CALLOUT("intuition", "学完你应当能回答这类问题（也是 NLP 岗位的高频面试题）：<strong>为什么 BERT 不能像 GPT 那样生成文本？MLM 的 80/10/10 掩码策略为什么不是简单地全换成 [MASK]？RoBERTa 相对 BERT 到底改了什么、为什么有效？ELECTRA 凭什么样本效率高得多？T5 的 span corruption 与 BERT 的 token 掩码差在哪？做文本分类，今天到底该用 BERT 微调还是 LLM few-shot？</strong>——并且能在 numpy 里把双向注意力、MLM 目标、[CLS] 分类头、BIO 标注解码、span 抽取、cross-attention、beam search 都从零实现出来。"),
    ])),
    ("three", "三种形态：一个掩码矩阵的三种画法", "".join([
        H3("全部差异的源头"),
        ASCII("""序列: [x1 x2 x3 x4]        「✓」= 该位置能看到该列的信息

 ① Encoder-only (BERT)      ② Decoder-only (GPT)      ③ Encoder-Decoder (T5)
    双向 / bidirectional        因果 / causal              编码双向 + 解码因果 + 交叉
      x1 x2 x3 x4                x1 x2 x3 x4              编码器自注意力: 同 ①
  x1  ✓  ✓  ✓  ✓            x1  ✓  ·  ·  ·           解码器自注意力: 同 ②
  x2  ✓  ✓  ✓  ✓            x2  ✓  ✓  ·  ·           交叉注意力 (Q 来自解码器,
  x3  ✓  ✓  ✓  ✓            x3  ✓  ✓  ✓  ·                        K/V 来自编码器):
  x4  ✓  ✓  ✓  ✓            x4  ✓  ✓  ✓  ✓              y_j 能看到全部 x  ✓✓✓✓

  能力: 每个位置的表示           能力: 可自回归生成         能力: 输入全局理解 +
        融合了全部上下文               (第 t 步只依赖 <t)         输出自回归生成
  代价: **无法自回归生成**        代价: 每个位置只有左侧      代价: 参数多、两套栈
        (会看到答案，训练即作弊)       上下文，表示较弱

  预训练: MLM / RTD              预训练: 下一个 token       预训练: span corruption
  推理:   1 次前向 O(1)          推理: n 次前向 O(n)        推理: 1 次编码 + m 次解码""")
        ,
        P("这张图是整门课的地图。三种形态的所有性质，都能从它读出来："),
        TABLE(["性质", "Encoder-only", "Decoder-only", "Encoder-Decoder"], [
            ["代表模型", "BERT / RoBERTa / ELECTRA / DeBERTa", "GPT / LLaMA / Qwen", "原始 Transformer / T5 / BART / mT5"],
            ["每个位置的上下文", "<strong>双向全局</strong>", "仅左侧", "输入双向 + 输出左侧"],
            ["能否自回归生成", "❌ 不能", "✅ 能", "✅ 能"],
            ["典型预训练目标", "MLM / RTD", "CLM（下一 token）", "span corruption / 去噪"],
            ["典型任务", "分类、NER、抽取式 QA、句嵌入、重排", "开放生成、对话、指令跟随", "翻译、摘要、结构化转换"],
            ["分类任务的推理成本", "<strong>1 次前向</strong>", "n 次前向（或 1 次取 logit）", "1 次编码"],
            ["典型规模（经典期）", "110M–400M", "7B–405B", "220M–11B"],
        ]),
        CALLOUT("warn", "一个必须先破除的误解：<strong>「decoder-only 更强所以取代了一切」是不准确的</strong>。准确的说法是——decoder-only 在<em>生成与通用指令跟随</em>上取得了压倒性优势，因为它的预训练目标（预测下一个 token）能无监督地吃下整个互联网，且天然与「生成」这个能力对齐。但在<em>「输入定长、输出是一个标签或一个片段」</em>的任务上，encoder 的双向表示 + 单次前向仍然在<strong>精度/延迟/成本的联合权衡</strong>上占优。模块 05 会把这笔账算清楚——你会看到，同样的分类任务，BERT 系方案的单位成本可能比 LLM 低两到三个数量级。"),
    ])),
    ("map", "课程地图：从掩码到部署的五站", "".join([
        ASCII("""起点：你已经会写因果注意力的 Transformer（C01）。把掩码换个形状会发生什么？

  模块 01  MLM 与双向编码器        双向注意力 / [CLS][SEP] / 80-10-10 / NSP 的失败
     │                            「为什么 BERT 不能生成？MLM 到底在学什么？」
     ▼
  模块 02  预训练目标的改良        RoBERTa / ELECTRA / DeBERTa / ALBERT
     │                            「同一个架构，换个目标与配方，效率能差几倍」
     ▼
  模块 03  下游微调三范式          句分类 / token 分类(BIO) / span 抽取(SQuAD)
     │                            「预训练表示怎么接到具体任务上，头怎么设计」
     ▼
  模块 04  Encoder-Decoder         T5 span corruption / BART 去噪 / cross-attention
     │                            / teacher forcing / exposure bias / beam search
     ▼
  模块 05  今天还要不要 encoder     与 decoder-only LLM 的成本-精度账 / 蒸馏 /
                                   双塔 embedding 与 cross-encoder reranker

终点：面对一个真实 NLP 任务，你能有理有据地选形态、选目标、选规模，并算清账。""")
        ,
        TABLE(["模块", "核心机制", "notebook 里从零做什么"], [
            ["01 MLM 与 BERT", "双向 self-attention、掩码语言建模、[CLS] 池化", "三种掩码对拍、MLM 目标与损失、<strong>数值证明 BERT 不能自回归</strong>、80/10/10 消融"],
            ["02 目标改良", "动态掩码、RTD 判别、解耦注意力、参数共享", "静态 vs 动态掩码的样本多样性、<strong>RTD 的信号密度账</strong>、DeBERTa 注意力分解、ALBERT 参数量账"],
            ["03 下游微调", "分类头、BIO + 约束解码、span 抽取", "三种头从零、<strong>维特比约束解码</strong>、最优 span 搜索、MCC/F1/EM、判别式学习率"],
            ["04 Encoder-Decoder", "span corruption、cross-attention、beam search", "T5 目标构造与还原、cross-attention 实现、<strong>exposure bias 演示</strong>、beam search + 长度惩罚"],
            ["05 今天的选型", "推理成本模型、蒸馏、双塔 vs 交叉编码", "encoder/decoder 的 FLOPs 与延迟账、logit 蒸馏、<strong>召回-精排两阶段的成本-精度前沿</strong>"],
        ]),
    ])),
    ("method", "方法论：纯 numpy 重建 + 与理论对拍", "".join([
        P("本课全程 <strong>纯 numpy / CPU</strong>，不加载任何预训练权重、不联网。这看起来是个限制，但对本课的目标恰恰合适——因为<strong>这门课要讲的是「设计选择」，不是「调 API」</strong>。"),
        DUAL(
            "「BERT 为什么不能生成」这个问题，读十篇博客不如自己写一遍：用双向掩码做一次前向，你会亲眼看到位置 <code>t</code> 的表示里<em>已经混入了位置 <code>t+1</code> 的信息</em>，于是「预测下一个 token」这个训练目标退化成了抄答案（损失瞬间趋零、模型什么也没学到）。这个实验在 notebook 里三十行就能跑出来，而且它的结论是<strong>不可辩驳的数值事实</strong>，不是别人告诉你的结论。",
            "本课的对拍策略有三层：<strong>①与理论对拍</strong>——注意力掩码的实现要满足可证明的性质（因果掩码下 <code>∂y_t/∂x_{t+1} = 0</code>，我们直接用数值梯度验证）；<strong>②与朴素参考对拍</strong>——beam search 与穷举搜索在小词表小长度下应给出相同的最优序列；<strong>③与公开报告的量级对拍</strong>——参数量、FLOPs、样本效率的账要与论文中报告的数字在同一量级（notebook 里的 🧪 胶囊会做这件事）。",
        ),
        CALLOUT("intuition", "一句话说明本课与 C01/C17/C20 的分工：<strong>C01 教你从零写一个 decoder-only Transformer；C17 讲神经网络之前的经典 NLP（word2vec/HMM/CRF）；C20 讲现代架构组件（RoPE/GQA/MoE/SSM）。本课补的是「另外两种 Transformer 形态」以及它们独有的预训练目标与任务范式</strong>。三门课的注意力实现是同一套，只是掩码不同——这正是本课要让你亲手体会的。"),
    ])),
    ("env", "环境与运行", "".join([
        P("本课全程 <strong>纯 numpy、CPU 可跑</strong>，不需要 GPU、不需要预训练权重、不需要联网。所有 notebook 在 CPU 上实跑验证、assert 0 失败。"),
        CODE("""pip install -r requirements.txt      # numpy / pandas / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        P("讲解里会出现 HuggingFace <code>transformers</code> 的真实调用片段作为<strong>对照展示</strong>（不参与运行）——它们标注了「你在 numpy 里手写的这一步，在真实库里叫什么、参数在哪」。想真正上手这些库，见 <strong>C50（HuggingFace 生态与 API 实操）</strong>，那门课与本课是配套的：本课讲<em>模型形态与目标</em>，C50 讲<em>怎么用生态把它跑起来</em>。"),
        TABLE(["你需要", "本课怎么处理"], [
            ["预训练权重（BERT/T5）", "用小随机初始化的迷你模型（词表几十、维度几十）验证<strong>机制</strong>；效果数字引用公开论文报告"],
            ["GPU 训练", "所有实验都是几百到几千步的小规模，CPU 秒级完成"],
            ["GLUE/SQuAD 数据", "用程序生成的小型合成数据集，保留任务的结构（标签体系、span 边界、BIO 约束）"],
            ["tokenizer", "用一个几十词的字符/词级迷你词表；真实 subword 分词见 C01/C21/C50"],
        ]),
        P("关于学习顺序还有一条建议：<strong>如果你只有时间读两个模块，读 01 和 05</strong>。模块 01 讲清 MLM 为什么必须存在（这是理解一切 encoder 的钥匙），模块 05 讲清今天该怎么选（这是你真正要做的决策）。中间三个模块是把这两端连起来的推导链——02 说明同一个架构上还能改什么、改哪里有效，03 说明预训练好的表示怎么接到具体任务、以及那些不写在论文里却决定成败的解码与评估细节，04 说明当输出必须是新文本时架构要怎么变。<em>但如果你要面试或者要做真实项目，五个模块的内容都会被问到、都会被用到。</em>"),
        P("最后一句：本课的每个模块都会明确回答「<strong>这个设计解决了什么问题、代价是什么、今天还成立吗</strong>」。有些设计（NSP）后来被证明是错的，有些（动态掩码）被证明是对的，有些（encoder-decoder）经历了衰落又部分复兴。<em>把「为什么当时那样设计、后来为什么改」搞清楚，比记住哪个模型在 GLUE 上多了 0.5 分有用得多。</em>"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与「三种掩码」热身

本课全程 **纯 numpy / CPU**，不加载预训练权重、不联网。

这个 notebook 做三件事：① 确认环境；② 用三十行把 **encoder-only / decoder-only / encoder-decoder 的注意力掩码**都写出来，
并用**数值梯度**证明它们的信息流差异；③ 立下全课的三条纪律：**与理论对拍 / 与朴素参考对拍 / 与公开量级对拍**。"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math
print('Python', sys.version.split()[0], '|', platform.system())
import numpy as np; print('numpy', np.__version__)
try:
    import pandas as pd; print('pandas', pd.__version__, '(可选)')
except Exception:
    print('pandas 未安装（可选，不影响课程）')
np.set_printoptions(precision=3, suppress=True)
print('环境就绪 ✅  —— 本课不需要 GPU / 预训练权重 / 联网')"""),
    md("""## 2 · 三种掩码：Transformer 三种形态的全部差异源头

- **encoder-only（BERT）**：全 1 掩码，每个位置看得到所有位置 → 双向表示
- **decoder-only（GPT）**：下三角掩码，位置 t 只看得到 ≤ t → 可自回归
- **encoder-decoder（T5）**：编码器双向 + 解码器因果 + **交叉注意力全可见**

先把三种掩码造出来，并验证它们的形状性质。"""),
    code("""def bidirectional_mask(n):
    '''encoder-only：全部可见。'''
    return np.ones((n, n), dtype=bool)

def causal_mask(n):
    '''decoder-only：下三角（含对角线）。'''
    return np.tril(np.ones((n, n), dtype=bool))

def cross_mask(n_tgt, n_src):
    '''cross-attention：解码器每个位置都能看到编码器的全部位置。'''
    return np.ones((n_tgt, n_src), dtype=bool)

def prefix_lm_mask(n, n_prefix):
    '''prefix-LM（UniLM/GLM 用）：前缀内部双向，后缀因果。encoder/decoder 的一种融合。'''
    m = np.tril(np.ones((n, n), dtype=bool))
    m[:, :n_prefix] = True          # 所有位置都能看到整个前缀
    return m

N = 5
for name, m in [('bidirectional', bidirectional_mask(N)),
                ('causal', causal_mask(N)),
                ('prefix-LM (前缀=2)', prefix_lm_mask(N, 2))]:
    print(f'{name}:')
    print(np.where(m, 1, 0), '\\n')

assert bidirectional_mask(N).all(), '双向掩码应全可见'
assert causal_mask(N)[0, 1:].sum() == 0, '因果掩码下位置 0 看不到未来'
assert causal_mask(N).sum() == N * (N + 1) // 2, '下三角元素数 = n(n+1)/2'
assert prefix_lm_mask(N, 2)[0, 1] and not prefix_lm_mask(N, 2)[2, 3], 'prefix-LM：前缀双向、后缀因果'
print('✅ 三种掩码的形状性质正确')"""),
    md("""## 3 · 数值证明：因果掩码下未来 token 的梯度为零

这不是「据说」——是可以直接测出来的。
对一个单层注意力，计算 `∂ output[t] / ∂ input[t+1]`：
**因果掩码下必须严格为 0，双向掩码下必须非 0。** 这就是 BERT 不能自回归的根本原因。"""),
    code("""def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def attention(X, Wq, Wk, Wv, mask):
    '''单头自注意力。X:(n,d)  mask:(n,n) bool'''
    Q, K, V = X @ Wq, X @ Wk, X @ Wv
    scores = Q @ K.T / math.sqrt(Q.shape[-1])
    scores = np.where(mask, scores, -1e9)
    return softmax(scores) @ V

rng = np.random.default_rng(0)
n, d = 6, 8
X = rng.normal(size=(n, d))
Wq, Wk, Wv = (rng.normal(size=(d, d)) * 0.3 for _ in range(3))

def numerical_jacobian_norm(mask, t, s, eps=1e-5):
    '''数值估计 ||∂output[t] / ∂input[s]||。'''
    base = attention(X, Wq, Wk, Wv, mask)[t]
    total = 0.0
    for k in range(d):
        Xp = X.copy(); Xp[s, k] += eps
        total += np.abs(attention(Xp, Wq, Wk, Wv, mask)[t] - base).sum() / eps
    return total

bi, ca = bidirectional_mask(n), causal_mask(n)
t, future = 2, 4          # 位置 2 的输出，对位置 4（未来）的输入的敏感度
g_bi = numerical_jacobian_norm(bi, t, future)
g_ca = numerical_jacobian_norm(ca, t, future)
print(f'双向掩码: ||∂out[{t}]/∂in[{future}]|| = {g_bi:.4f}')
print(f'因果掩码: ||∂out[{t}]/∂in[{future}]|| = {g_ca:.2e}')

assert g_bi > 1e-2, '双向掩码下未来信息必须流进来'
assert g_ca < 1e-6, '因果掩码下未来信息必须严格不可见'
print('\\n✅ 数值证明：**双向注意力会让位置 t 看到 t+1**。')
print('   所以 BERT 若用「预测下一个 token」训练，等于抄答案 —— 损失瞬间归零，什么也学不到。')
print('   这一条就决定了 encoder-only 必须换一种预训练目标（MLM，模块 01）。')"""),
    md("""### 把「抄答案」构造出来

上面证明了信息会泄漏。更强的一步：**在双向掩码下，存在一组参数让「预测下一个 token」的损失精确为 0**——
只要让每个位置 t 把注意力全部放到 t+1、把值向量原样搬过来、再与词嵌入表做内积即可。

**因果掩码下这组参数根本不存在**（位置 t+1 被屏蔽掉了）。这不是「训练得好不好」的问题，是可达性的问题。"""),
    code("""V = 12                                   # 迷你词表
Emb = np.random.default_rng(1).normal(size=(V, d))
Emb = Emb / np.linalg.norm(Emb, axis=1, keepdims=True) * 3.0   # 让内积可分

def cheat_attention_matrix(n):
    '''把注意力全押在下一个位置：A[t, t+1] = 1（最后一行只能看自己）。'''
    A = np.zeros((n, n))
    for t in range(n - 1):
        A[t, t + 1] = 1.0
    A[n - 1, n - 1] = 1.0
    return A

def loss_with_attention(A, toks):
    '''给定注意力矩阵，用「搬运值向量 + 与词表内积」的最简读出，算下一个 token 的交叉熵。
       只统计位置 0..n-2 —— 最后一个位置没有「下一个 token」可看（窗口边界）。'''
    H = A @ Emb[toks[:A.shape[1]]]
    logits = H @ Emb.T                    # 与词嵌入表内积 = 最近邻检索
    P = softmax(logits)
    m = A.shape[0] - 1                     # 排除最后一个位置
    tgt = toks[1:m + 1]
    return float(-np.log(P[np.arange(m), tgt] + 1e-12).mean())

toks = np.random.default_rng(3).integers(0, V, size=n + 1)
A_cheat = cheat_attention_matrix(n)
loss_cheat = loss_with_attention(A_cheat, toks)
print('作弊注意力矩阵 A[t,t+1]=1:')
print(A_cheat.astype(int))
print(f'\\n用它做「预测下一个 token」的损失: {loss_cheat:.6f}  (随机基线 ln(V)={math.log(V):.3f})')
print('（最后一个位置没有「下一个 token」可看，不计入——这是窗口边界，不是模型的问题）')
assert loss_cheat < 0.05, '双向掩码下存在损失≈0 的「作弊解」'

# 关键：这组注意力在两种掩码下是否**可达**？
bi_ok = bool((A_cheat[~bidirectional_mask(n)] == 0).all())
ca_ok = bool((A_cheat[~causal_mask(n)] == 0).all())
print(f'\\n作弊注意力在 双向掩码 下可达? {bi_ok}')
print(f'作弊注意力在 因果掩码 下可达? {ca_ok}   ← A[t,t+1] 恰好落在被屏蔽的上三角')
assert bi_ok and not ca_ok, '这才是 BERT 不能用 CLM 目标的根本原因'
print('\\n✅ 不是「训练得好不好」的问题，是**可达性**的问题：')
print('   双向掩码下最优解就是抄答案（损失可以精确为 0，模型什么也没学到）；')
print('   因果掩码把这条捷径从参数空间里物理删除了。')
print('   MLM 的全部设计动机：保留双向上下文，同时人为制造一个「答案不在输入里」的预测任务。')"""),
    md("""## 4 · 参数量账：三种形态的规模从哪来

一个 Transformer 的参数量几乎全在两处：**嵌入表** 与 **每层的 attention + FFN**。
把公式写出来，后面每个模块都会用它算账。"""),
    code("""def transformer_params(vocab, d_model, n_layers, d_ff=None, tie_embed=True,
                       n_dec_layers=0, cross_attn=False):
    '''返回参数量（近似，忽略 LayerNorm/bias 等小项）。'''
    d_ff = d_ff or 4 * d_model
    emb = vocab * d_model
    per_enc = 4 * d_model * d_model + 2 * d_model * d_ff      # QKVO + FFN(两层)
    per_dec = per_enc + (4 * d_model * d_model if cross_attn else 0)
    total = emb + n_layers * per_enc + n_dec_layers * per_dec
    if not tie_embed:
        total += vocab * d_model                              # 独立的输出投影
    return total

configs = [
    ('BERT-base   (enc-only, 12L)',  dict(vocab=30522, d_model=768,  n_layers=12)),
    ('BERT-large  (enc-only, 24L)',  dict(vocab=30522, d_model=1024, n_layers=24)),
    ('T5-base (enc-dec, 12+12L)',    dict(vocab=32128, d_model=768,  n_layers=12,
                                          n_dec_layers=12, cross_attn=True)),
    ('GPT-2 small (dec-only, 12L)',  dict(vocab=50257, d_model=768,  n_layers=12)),
]
print(f"{'配置':<32s} {'参数量(M)':>10s} {'嵌入占比':>9s}")
for name, cfg in configs:
    p = transformer_params(**cfg)
    emb_share = cfg['vocab'] * cfg['d_model'] / p
    print(f'{name:<32s} {p/1e6:>10.1f} {emb_share:>9.1%}')

p_bert  = transformer_params(vocab=30522, d_model=768, n_layers=12)
p_t5    = transformer_params(vocab=32128, d_model=768, n_layers=12, n_dec_layers=12, cross_attn=True)
assert 100e6 < p_bert < 130e6, f'BERT-base 应在 110M 量级，算得 {p_bert/1e6:.0f}M'
assert p_t5 > 2 * p_bert, 'encoder-decoder 参数量应显著大于同深同宽的 encoder-only'
print(f'\\n✅ 与公开数字对拍：BERT-base ≈ 110M ✓')
print('   注意嵌入表占 BERT-base 的 ~21% —— 这就是 ALBERT 要做嵌入分解的原因（模块 02）。')"""),
    md("""## 5 · ✏️ 练习：实现 prefix-LM 掩码并验证其性质

`prefix_lm_mask(n, n_prefix)` 已在上面给出。现在实现它的**逆问题**：
`infer_mask_type(mask)` —— 给定一个 (n,n) 的 bool 掩码，判断它属于哪种形态。
返回 `'bidirectional'` / `'causal'` / `'prefix-lm'` / `'other'`。

判据：全 1 → bidirectional；严格等于下三角 → causal；
存在 `k` (0<k<n) 使得「前 k 列全 1 且其余部分为下三角」→ prefix-lm；否则 other。"""),
    code("""def infer_mask_type(mask):
    # TODO: 按上述判据返回四种字符串之一
    raise NotImplementedError"""),
    code("""# —— 练习自测 ——
assert infer_mask_type(bidirectional_mask(5)) == 'bidirectional'
assert infer_mask_type(causal_mask(5)) == 'causal'
assert infer_mask_type(prefix_lm_mask(6, 2)) == 'prefix-lm'
assert infer_mask_type(prefix_lm_mask(6, 3)) == 'prefix-lm'
weird = causal_mask(5).copy(); weird[0, 4] = True
assert infer_mask_type(weird) == 'other'
# 边界：n_prefix=0 退化为 causal，n_prefix=n 退化为 bidirectional
assert infer_mask_type(prefix_lm_mask(5, 0)) == 'causal'
assert infer_mask_type(prefix_lm_mask(5, 5)) == 'bidirectional'
print('✅ 练习通过：三种形态是同一个掩码族上的三个点，prefix-LM 是它们之间的连续插值')"""),
    md("""---
### 📖 参考答案"""),
    code("""def infer_mask_type(mask):
    n = mask.shape[0]
    if mask.all():
        return 'bidirectional'
    tril = np.tril(np.ones((n, n), dtype=bool))
    if np.array_equal(mask, tril):
        return 'causal'
    for k in range(1, n):
        cand = tril.copy(); cand[:, :k] = True
        if np.array_equal(mask, cand):
            return 'prefix-lm'
    return 'other'"""),
    md("""## 6 · 立三条纪律

本课每个机制都会：

1. **与理论对拍** —— 实现要满足可证明的性质（如上面的梯度为零、softmax 归一、MLM 只在被掩位置计损失）。
2. **与朴素参考对拍** —— beam search vs 穷举、维特比 vs 暴力枚举路径、优化实现 vs 定义式实现。
3. **与公开量级对拍** —— 参数量、FLOPs、样本效率的账要与论文报告在同一量级。

把第三条封装成一个小工具。"""),
    code("""def check_magnitude(name, computed, reported, tol=0.25):
    '''与公开报告的数字比对，允许 tol 的相对误差（量级对拍，不是精确复现）。'''
    rel = abs(computed - reported) / reported
    ok = rel <= tol
    print(f'{name:<34s} 算得 {computed:>10,.1f} | 报告 {reported:>10,.1f} | 偏差 {rel:>6.1%} {"✅" if ok else "❌"}')
    return ok

ok1 = check_magnitude('BERT-base 参数量 (M)',
                      transformer_params(vocab=30522, d_model=768, n_layers=12) / 1e6, 110)
ok2 = check_magnitude('BERT-large 参数量 (M)',
                      transformer_params(vocab=30522, d_model=1024, n_layers=24) / 1e6, 340)
ok3 = check_magnitude('T5-base 参数量 (M)',
                      transformer_params(vocab=32128, d_model=768, n_layers=12,
                                         n_dec_layers=12, cross_attn=True) / 1e6, 220)
assert ok1 and ok2 and ok3, '参数量账应与公开数字在同一量级'
print('\\n✅ 三条纪律就位。')"""),
    md("""✅ 检查全部通过即环境就绪、方法论到位。

**本课的契约**：你写的每个机制（双向注意力、MLM 目标、分类/标注/抽取头、span corruption、cross-attention、beam search）都会
① 满足可证明的**理论性质**，② 与**朴素参考**给出相同结果，③ 参数量/效率的账与**公开报告**同量级。

**接下来五个模块**：01 MLM 与双向编码器 → 02 预训练目标的改良 → 03 下游微调三范式 → 04 Encoder-Decoder → 05 今天还要不要 encoder。

下一站：**模块 01 · MLM 与双向编码器** —— 既然不能预测下一个 token，那就把中间挖空。"""),
]
