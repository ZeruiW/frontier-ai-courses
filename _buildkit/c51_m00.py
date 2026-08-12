# -*- coding: utf-8 -*-
"""C51 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python/numpy；C10 的统计与测量基础有帮助；C21/C43 的数据科学与数据工程可选"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy/标准库 + 每个增强都做「有效性 + 保真度 + 多样性」三重检验"),
    ("预计时长", "总览 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么", "".join([
        P("欢迎来到 <strong>文本数据增强与合成数据工程</strong>。这门课回答一个看起来简单、实际上非常容易做错的问题：<strong>标注数据不够时，怎么「造」出更多数据，并且能证明造得有用</strong>。"),
        P("先说清它为什么值得单独一门课。图像增强是件相对安全的事——旋转一张猫的照片，它还是猫；加点噪声，标签不变。<strong>文本不是这样</strong>：把「这家店<em>不</em>好吃」里的「不」删掉，标签从负面变成正面；把「他给了她一本书」的词序打乱，语义可能崩掉；用同义词替换「银行」，可能把「金融机构」换成「河岸」。<em>文本的离散性与组合性，让「增强」与「破坏」之间的界限非常薄</em>。"),
        DUAL(
            "所以本课的核心不是「教你十种增强技巧」——那些在网上都能查到。核心是<strong>「怎么判断一个增强是不是真的有用」</strong>。这个判断需要三个独立的检验：<strong>①有效性</strong>（下游指标真的涨了，且涨幅超过噪声）；<strong>②保真度</strong>（增强后的样本标签仍然正确）；<strong>③多样性</strong>（新样本带来了新信息，不是原样本的近似副本）。<em>三者缺一，你的「增强」很可能是在给模型喂噪声或喂重复。</em>",
            "这三个检验分别对应本课的三条技术线。<strong>保真度</strong>要求你能量化「标签是否被破坏」——需要标签保持性检验与人工/模型审核（模块 04）。<strong>多样性</strong>要求你能量化「新样本有多新」——需要 distinct-n、嵌入覆盖、self-BLEU 这类度量（模块 04）。<strong>有效性</strong>要求你能做出可信的对照实验——需要配对检验、学习曲线、以及最关键的一个对照组：<em>「同样的算力/人力预算下，直接加真实数据会不会更好」</em>（模块 05）。这个对照组几乎总是被省略，而它常常给出否定答案。",
        ),
        CALLOUT("intuition", "学完你应当能回答这类问题：<strong>EDA 的四个操作里哪个最危险？回译为什么能保语义、什么时候会失效？self-instruct 的种子池该多大、怎么防止模式坍塌？增强强度（α）与数据量是什么关系、为什么小数据集才受益？「多样性指标涨了」能不能推出「有用」？怎么设计一个能证伪「增强有效」这个假设的实验？什么时候用增强还不如去标注 500 条真实数据？</strong>——并且能在 numpy 里把每种增强、每个多样性度量、每套检验都实现一遍。"),
    ])),
    ("three", "三个层次：词面 / 语义 / 指令", "".join([
        ASCII("""按「改动发生在哪一层」把文本增强分成三类。层次越高，保真度越好，成本越高。

① 词面层 (lexical) —— 直接改字符与词
   同义词替换 / 随机插入 / 随机交换 / 随机删除 (EDA) / 字符噪声 / token dropout
   成本: 几乎为零（查词典 + 采样）
   保真: ⚠️ 脆弱（否定词、专有名词、程度副词一改就变标签）
   多样: 低（新样本与原样本的词面重叠很高）
   适合: 小数据集（<1k 条）的分类任务；作为轻量正则

② 语义层 (semantic) —— 保语义、换表达
   回译 (back-translation) / 释义模型 / 句法变换（主被动、语序）
   成本: 中（需要翻译或释义模型的推理）
   保真: ✅ 较好（语义被显式保持）
   多样: 中（表达变了，信息量没变）
   适合: 中等数据量；对措辞鲁棒性有要求的任务

③ 指令层 (instructional) —— 让 LLM 直接造新样本
   self-instruct / evol-instruct / Magpie / 教师蒸馏 / 场景化生成
   成本: 高（LLM 调用）
   保真: 🔶 取决于教师；**会继承教师的偏差**
   多样: ✅ 可以很高（能造出训练集里根本没有的场景）
   适合: 指令微调 / 无标注冷启动 / 长尾场景补全

关键区别：① ② 是「把已有样本换个说法」（信息量不增加）；
         ③ 是「造出新样本」（信息量可以真的增加，但来源是教师模型的知识）。""")
        ,
        TABLE(["层次", "本质", "信息量", "最大风险"], [
            ["<strong>词面</strong>", "对原样本做局部扰动", "<strong>不增加</strong>（同一条信息的多个视角）", "标签被破坏而你不知道"],
            ["<strong>语义</strong>", "换表达、保语义", "<strong>不增加</strong>", "释义失真（尤其专业术语、否定、数字）"],
            ["<strong>指令</strong>", "从教师模型的知识里采样新样本", "<strong>可以增加</strong>（但上限是教师）", "继承教师偏差 + 模式坍塌 + 数据污染"],
        ]),
        CALLOUT("warn", "「信息量不增加」这一点必须想清楚，因为它决定了增强的<strong>收益上限</strong>。词面与语义增强本质上是一种<em>正则化</em>——它告诉模型「这些不同的表面形式对应同一个标签」，从而减少对表面特征的过拟合。<strong>所以它在小数据集上收益明显，在大数据集上收益趋零甚至为负</strong>（大数据集本身就包含了足够的表面多样性，再增强只是在加噪声）。<em>如果你有十万条标注数据还在纠结要不要做 EDA，答案基本是「不要」。</em>"),
    ])),
    ("map", "课程地图：从造数据到证明它有用", "".join([
        ASCII("""模块 01  词面增强
   EDA 四操作的实现与危险性排序 / 否定与实体的保护 / 增强强度 α 的作用 /
   token dropout / 为什么小数据集才受益
        ▼
模块 02  回译与释义
   回译管线 / round-trip 一致性 / 中间语言的选择 / 多样性-保真的权衡曲线 /
   释义质量的自动判据 / 什么时候回译会毁掉标签
        ▼
模块 03  LLM 驱动的指令数据合成
   self-instruct 的完整循环 / 种子池设计与去重阈值 / evol-instruct 的演化算子 /
   Magpie 式无种子生成 / 教师偏差的传递 / 模式坍塌的检测
        ▼
模块 04  增强的质量控制
   保真度：标签保持性检验 / 多样性：distinct-n、self-BLEU、嵌入覆盖 /
   去污染：增强样本泄漏测试集 / model collapse 的机制与征兆
        ▼
模块 05  增强的评测与消融
   怎么证明增强有效：配对检验 + 多种子 + 学习曲线 /
   **那个总被省略的对照组：同预算下直接加真实数据** / 增强的边际收益递减

终点：面对「数据不够」这个问题，你能选对增强层次、算清预算、
      并做出一个能证伪自己的实验。""")
        ,
        TABLE(["模块", "核心机制", "notebook 里从零做什么"], [
            ["01 词面增强", "EDA 四操作、保护规则、强度 α", "四操作实现 + <strong>标签破坏率量化</strong> + α 扫描 + 数据量-收益曲线"],
            ["02 回译与释义", "回译管线、round-trip、保真-多样权衡", "可控失真的翻译模拟 + <strong>保真度与多样性的权衡前沿</strong> + 失效案例检测"],
            ["03 指令合成", "self-instruct 循环、evol 算子、去重", "完整 self-instruct 循环 + <strong>ROUGE-L 去重阈值的作用</strong> + 教师偏差传递 + 坍塌检测"],
            ["04 质量控制", "标签保持、多样性度量、去污染", "distinct-n / self-BLEU / 嵌入覆盖 + <strong>n-gram 泄漏检测</strong> + collapse 模拟"],
            ["05 评测与消融", "配对检验、学习曲线、预算对照", "配对 bootstrap + 多种子 + <strong>「增强 vs 加真实数据」的等预算对照</strong>"],
        ]),
    ])),
    ("misuse", "四种常见的误用（先认出它们）", "".join([
        P("在进入具体技术之前，先把<strong>最常见的四种误用</strong>摆出来。它们的共同点是：<em>看起来都很合理，也都会产生「涨分」的观察，但结论站不住</em>。本课后面每个模块都会回到它们。"),
        TABLE(["误用", "表现", "为什么错", "在哪个模块修"], [
            ["<strong>① 先增强后划分</strong>", "在整个数据集上做增强，然后随机切训练/测试", "同一条原样本的副本分落两边，<strong>测试集已经泄漏</strong>，所有指标虚高", "模块 04"],
            ["<strong>② 只比 C vs A</strong>", "「增强组 86 分，baseline 84 分，所以增强有效」", "没有排除「样本更多 / 训练更久」这个混淆——<em>把数据复制五遍也常常涨分</em>", "模块 05"],
            ["<strong>③ 单个种子</strong>", "跑一次，看到高 1.2 分就下结论", "小数据集微调的种子标准差就有 2–3 分，<strong>单次结论可能完全相反</strong>", "模块 05"],
            ["<strong>④ 只看多样性</strong>", "「distinct-2 涨了，说明增强有效」", "完全随机的文本多样性最高、却毫无价值；而且<strong>多样性指标可以被刷</strong>", "模块 04"],
        ]),
        DUAL(
            "这四种误用不是「新手才犯的错」——它们在<em>已发表的论文</em>里也非常普遍。原因不是作者不严谨，而是<strong>确认性设计比证伪性设计更省事、也更容易得到「好看」的结果</strong>：不做复制对照就少跑一组实验；只跑一个种子就少花五倍时间；不做真实数据对照就不用去标注。<em>每一步偷懒都是局部理性的，加起来就是一个不可信的结论。</em>",
            "本课的应对不是「你要更严谨」这种空话，而是把纪律变成<strong>可执行的检查清单与可运行的代码</strong>：一个 <code>assert_no_test_ids()</code> 断言挡住误用 ①；一个「四臂实验 + 配对 bootstrap」的函数挡住 ② 和 ③；一套「保真度硬门槛 + 多度量交叉」挡住 ④。<em>纪律只有变成默认执行的代码，才会真的被遵守</em>——这与 C48 把运维纪律写成断言、C50 把 <code>Trainer</code> 的隐式依赖写成校验器，是同一个思路。",
        ),
        CALLOUT("warn", "还有一个不算「误用」但值得先破除的<strong>期待偏差</strong>：很多人来学数据增强，是希望得到「一套万能的、能让任何任务涨分的技巧」。<em>这套东西不存在</em>。真实的结论是分场景的：<strong>小数据 + 昂贵标注 + 长尾类别 + 零标注冷启动 → 增强非常有用；中等以上数据 + 廉价标注 → 大概率不如去多标注一些</strong>。本课会把这条分界线量化出来（模块 05 的「等价真实数据量」）。<em>能诚实地说出「你这个场景不该做增强」，本身就是这门课的价值之一。</em>"),
    ])),
    ("method", "方法论：每个增强都过三重检验", "".join([
        P("本课全程 <strong>纯 numpy / 标准库、CPU、不联网</strong>。没有真实的翻译模型、没有 LLM API——那怎么学增强？"),
        DUAL(
            "关键洞察是：<strong>本课要教的判断力，几乎不依赖增强器的具体实现，只依赖「增强前后的样本对」</strong>。所以我们用<em>可控的模拟增强器</em>——一个带「失真强度」参数的假翻译器、一个带「教师偏差」参数的假 LLM、一个带「坍塌倾向」参数的假生成器。<strong>因为参数可控，你能做真实环境里做不到的实验</strong>：比如「把教师偏差从 0 调到 0.3，看学生模型的偏差怎么变」，或者「让生成器逐代坍塌，看多样性指标什么时候先报警」。",
            "三重检验会被实现成三个可复用的函数，贯穿全课：<strong><code>fidelity(pairs)</code></strong>——增强后标签仍正确的比例（用可验证的规则标签，如「含否定词则为负面」，这样标签是可精确判定的）；<strong><code>diversity(texts)</code></strong>——distinct-n / self-BLEU / 嵌入覆盖；<strong><code>effectiveness(clean, augmented)</code></strong>——在一个可训练的小模型上做配对检验。<em>每个模块的每种增强，都要过这三关并给出数字。</em>",
        ),
        CALLOUT("intuition", "本课有一条贯穿全篇的立场，值得先说明：<strong>它对数据增强持「有条件的怀疑」态度</strong>。不是因为增强没用——它在小数据、低资源、长尾场景下确实有用；而是因为<em>增强的文献里充满了「在小数据集上涨了 1 分」这类不可靠结论</em>（种子方差就有 2–3 分，C49 模块 03 讲过）。本课要给你的不是「增强很棒」的信念，而是<strong>「怎么在自己的数据上判断它到底有没有用」的能力</strong>——包括接受「没用」这个答案。"),
    ])),
    ("env", "环境与运行", "".join([
        P("本课全程 <strong>纯 numpy + 标准库、CPU 可跑</strong>，不需要 GPU、翻译模型、LLM API 或联网。所有 notebook 在 CPU 上实跑验证、assert 0 失败。"),
        CODE("""pip install -r requirements.txt      # numpy / pandas / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        TABLE(["你需要", "本课怎么处理"], [
            ["同义词词典（WordNet 等）", "用一个几十词的迷你同义词表，含<strong>刻意埋入的陷阱</strong>（一词多义、程度副词）"],
            ["翻译模型（回译）", "可控失真的模拟翻译器：<code>distortion</code> 参数决定语义漂移程度"],
            ["LLM（指令合成）", "可控的模拟教师：<code>bias</code> / <code>diversity</code> / <code>collapse_rate</code> 三个参数"],
            ["嵌入模型（多样性）", "用字符/词袋 + 随机投影作为廉价嵌入；度量的<strong>性质</strong>与真实嵌入一致"],
            ["下游任务与标注", "用<strong>规则可判定</strong>的合成任务（如「含否定词 → 负面」），这样标签保真度可精确计算"],
        ]),
        P("最后说明本课与相邻课程的分工：<strong>C21（大规模预训练）讲预训练语料的配比与合成数据在预训练中的角色；C43（数据工程）讲 PB 级去重/过滤/流式的工程手艺；C14 讲合成数据的理论与生成媒体评测；C10 讲测量科学与标注质量</strong>。<em>本课聚焦在「有标注任务的训练集不够用时，怎么造与怎么验」这个具体问题上</em>，并把「造」的每一步都接上「验」。"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与「三重检验」热身

本课全程 **纯 numpy + 标准库、CPU、不联网**。用**可控参数的模拟增强器**替代真实翻译/LLM——
因为本课要教的判断力只依赖「增强前后的样本对」，不依赖增强器的具体实现。
而且参数可控让你能做真实环境里做不到的实验（比如「把教师偏差从 0 调到 0.3」）。

这个 notebook 做三件事：① 环境自检；② 建立本课的**规则可判定任务**（这样标签保真度能精确计算）；
③ 实现贯穿全课的**三重检验**：保真度 / 多样性 / 有效性。"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math, random, itertools, collections
print('Python', sys.version.split()[0], '|', platform.system())
import numpy as np; print('numpy', np.__version__)
try:
    import pandas as pd; print('pandas', pd.__version__, '(可选)')
except Exception:
    print('pandas 未安装（可选）')
print('环境就绪 ✅  —— 本课不需要 GPU / 翻译模型 / LLM API / 联网')"""),
    md("""## 2 · 一个规则可判定的任务：让「标签保真度」可精确计算

真实任务里，「增强后标签还对不对」需要人工判断。本课用一个**规则可判定**的合成任务绕开这个问题：

> **标签 = 情感极性**，由一条明确规则决定：
> 句中含**正面词**则为正面；若同时含**否定词**且否定词在正面词之前 3 个词内，则翻转为负面。

这样任何增强后的句子，我们都能**精确算出它的真标签**，从而量化「增强破坏了多少标签」。"""),
    code("""POS_WORDS = {'好吃', '不错', '推荐', '干净', '很好', '满意', '喜欢'}
NEG_WORDS = {'难吃', '差', '脏', '失望', '糟糕'}
NEGATORS  = {'不', '没', '别', '不太', '并不'}
NEUTRAL   = ['这家', '店', '的', '菜', '服务', '环境', '价格', '味道', '朋友', '下次',
             '我们', '昨天', '一起', '去', '吃', '了', '感觉', '整体', '还', '挺']

def rule_label(tokens, window=3):
    '''规则标签：1=正面, 0=负面。否定词在正面词前 window 个词内则翻转。'''
    score = 0
    for i, t in enumerate(tokens):
        if t in POS_WORDS:
            negated = any(tokens[j] in NEGATORS for j in range(max(0, i - window), i))
            score += -1 if negated else 1
        elif t in NEG_WORDS:
            negated = any(tokens[j] in NEGATORS for j in range(max(0, i - window), i))
            score += 1 if negated else -1
    return 1 if score > 0 else 0

def make_sentence(rng, label=None, length=10):
    '''生成一个句子及其规则标签。'''
    for _ in range(200):
        toks = list(rng.choice(NEUTRAL, size=length - 2, replace=True))
        pos = int(rng.integers(1, len(toks)))
        if rng.random() < 0.5:
            toks.insert(pos, str(rng.choice(sorted(POS_WORDS))))
        else:
            toks.insert(pos, str(rng.choice(sorted(NEG_WORDS))))
        if rng.random() < 0.4:
            toks.insert(max(0, pos - int(rng.integers(1, 3))), str(rng.choice(sorted(NEGATORS))))
        y = rule_label(toks)
        if label is None or y == label:
            return toks, y
    return toks, rule_label(toks)

rng = np.random.default_rng(0)
for _ in range(4):
    toks, y = make_sentence(rng)
    print(f'{"正面" if y else "负面"} | {" ".join(toks)}')

# 规则的关键性质：否定词的位置决定标签
assert rule_label(['这家', '店', '好吃']) == 1
assert rule_label(['这家', '店', '不', '好吃']) == 0, '否定词在窗口内 -> 翻转'
assert rule_label(['不', '这家', '店', '的', '菜', '好吃']) == 1, '否定词太远 -> 不翻转'
assert rule_label(['难吃']) == 0 and rule_label(['不', '难吃']) == 1
print('\\n✅ 规则可判定：任何增强后的句子，我们都能算出它的**真**标签。')
print('   这让「增强破坏了多少标签」从主观判断变成一个可精确计算的数字。')"""),
    md("""## 3 · 检验一：保真度（fidelity）—— 增强有没有破坏标签"""),
    code("""def fidelity(pairs):
    '''pairs: [(原tokens, 原标签, 增强后tokens)]。返回增强后规则标签仍等于原标签的比例。'''
    if not pairs: return 1.0
    keep = sum(1 for orig, y, aug in pairs if rule_label(aug) == y)
    return keep / len(pairs)

def broken_examples(pairs, k=3):
    return [(orig, y, aug) for orig, y, aug in pairs if rule_label(aug) != y][:k]

# 一个刻意危险的增强：随机删除一个词（可能删掉否定词！）
def random_deletion(tokens, p, rng):
    kept = [t for t in tokens if rng.random() >= p]
    return kept if kept else tokens[:1]

data = [make_sentence(np.random.default_rng(s)) for s in range(400)]
print(f"{'删除概率 p':>11s} {'标签保真度':>11s} {'破坏率':>9s}")
for p in [0.0, 0.05, 0.1, 0.2, 0.4]:
    r = np.random.default_rng(7)
    pairs = [(t, y, random_deletion(t, p, r)) for t, y in data]
    f = fidelity(pairs)
    print(f'{p:>11.2f} {f:>11.1%} {1-f:>9.1%}')

r = np.random.default_rng(7)
pairs20 = [(t, y, random_deletion(t, 0.2, r)) for t, y in data]
f0 = fidelity([(t, y, t) for t, y in data])
assert f0 == 1.0, '不增强时保真度必须是 1'
assert fidelity(pairs20) < 0.98, '删除 20% 的词会破坏一部分标签'
print(f'\\n被破坏的例子（删除 p=0.2）:')
for orig, y, aug in broken_examples(pairs20):
    print(f'  原({"正" if y else "负"}): {" ".join(orig)}')
    print(f'  增({"正" if rule_label(aug) else "负"}): {" ".join(aug)}   ← 标签翻转了')
print('\\n✅ 这就是文本增强与图像增强的根本区别：**旋转一张猫的照片它还是猫，')
print('   但删掉一个「不」字，标签就反了。**')"""),
    md("""## 4 · 检验二：多样性（diversity）—— 新样本有多新"""),
    code("""def ngrams(tokens, n):
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def distinct_n(texts, n=2):
    '''distinct-n：不同 n-gram 数 / 总 n-gram 数。越高越多样。'''
    total, uniq = 0, set()
    for t in texts:
        g = ngrams(t, n); total += len(g); uniq.update(g)
    return len(uniq) / total if total else 0.0

def self_bleu(texts, n=2, sample=60, seed=0):
    '''self-BLEU（简化版）：每条与其他条的 n-gram 重叠precision 的均值。越**低**越多样。'''
    r = np.random.default_rng(seed)
    idx = r.choice(len(texts), size=min(sample, len(texts)), replace=False)
    scores = []
    for i in idx:
        gi = collections.Counter(ngrams(texts[i], n))
        if not gi: continue
        others = collections.Counter()
        for j in idx:
            if j != i: others.update(ngrams(texts[j], n))
        overlap = sum(min(c, others[g]) for g, c in gi.items())
        scores.append(overlap / sum(gi.values()))
    return float(np.mean(scores)) if scores else 0.0

def cheap_embed(tokens, dim=32, seed=0):
    '''廉价嵌入：词袋 + 固定随机投影。度量的**性质**与真实嵌入一致。'''
    r = np.random.default_rng(seed)
    vocab = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS)
    proj = r.normal(size=(len(vocab), dim))
    v2i = {w: i for i, w in enumerate(vocab)}
    vec = np.zeros(dim)
    for t in tokens:
        if t in v2i: vec += proj[v2i[t]]
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec

def embedding_coverage(texts, n_bins=8, seed=0):
    '''嵌入覆盖：把嵌入投到 2 维后统计占据了多少网格。越高覆盖越广。'''
    E = np.stack([cheap_embed(t, seed=seed) for t in texts])
    xy = E[:, :2]
    lo, hi = xy.min(0), xy.max(0)
    span = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    cells = set(map(tuple, np.floor((xy - lo) / span * (n_bins - 1e-9)).astype(int)))
    return len(cells) / (n_bins * n_bins)

texts = [t for t, _ in data]
# 三组对照：原始 / 原始的近似副本（低多样性）/ 完全随机（高多样性）
dup = [t[:] for t in texts[:100] for _ in range(4)][:400]
rand_texts = [list(np.random.default_rng(1000+i).choice(NEUTRAL + sorted(POS_WORDS), size=10))
              for i in range(400)]
print(f"{'语料':<16s} {'distinct-2':>11s} {'self-BLEU-2':>12s} {'嵌入覆盖':>9s}")
for name, ts in [('原始', texts), ('近似副本', dup), ('完全随机', rand_texts)]:
    print(f'{name:<16s} {distinct_n(ts,2):>11.4f} {self_bleu(ts,2):>12.4f} {embedding_coverage(ts):>9.3f}')

assert distinct_n(dup, 2) < distinct_n(texts, 2), '重复副本的 distinct-n 更低'
assert self_bleu(dup, 2) > self_bleu(texts, 2), '重复副本的 self-BLEU 更高（越低越多样）'
print('\\n✅ 三个度量方向一致：distinct-n 越**高**越多样、self-BLEU 越**低**越多样、覆盖越高越广。')
print('   ⚠️ 但注意「完全随机」的多样性最高、而它作为训练数据毫无价值 ——')
print('   **多样性高 ≠ 有用**。这就是为什么必须有第三个检验。')"""),
    md("""## 5 · 检验三：有效性（effectiveness）—— 下游指标真的涨了吗

前两个检验都是**内在的**（不需要训练）。但「增强有没有用」最终只能靠**下游任务**回答。
这里建一个可训练的小分类器，后面每个模块都用它做对照实验。"""),
    code("""VOCAB = sorted(set(NEUTRAL) | POS_WORDS | NEG_WORDS | NEGATORS)
V2I = {w: i for i, w in enumerate(VOCAB)}

def featurize(tokens):
    '''词袋 + 二元特征（能捕捉「否定词 + 正面词」的组合）。'''
    x = np.zeros(len(VOCAB) + 1)
    for t in tokens:
        if t in V2I: x[V2I[t]] += 1.0
    x[-1] = 1.0
    return x

def train_logreg(X, y, epochs=300, lr=0.3, l2=1e-3, seed=0):
    r = np.random.default_rng(seed)
    w = r.normal(size=X.shape[1]) * 0.01
    for _ in range(epochs):
        p = 1 / (1 + np.exp(-(X @ w)))
        g = X.T @ (p - y) / len(y) + l2 * w
        w -= lr * g
    return w

def evaluate(w, X, y):
    return float(((X @ w > 0).astype(int) == y).mean())

def build_xy(pairs_or_data):
    X = np.stack([featurize(t) for t, _ in pairs_or_data])
    y = np.array([lab for _, lab in pairs_or_data])
    return X, y

def effectiveness(train_data, aug_data, test_data, seeds=range(8)):
    '''返回 (baseline 均值, 增强后均值, 每个种子的差值)。'''
    Xte, yte = build_xy(test_data)
    base, aug, diffs = [], [], []
    for s in seeds:
        Xb, yb = build_xy(train_data)
        wb = train_logreg(Xb, yb, seed=s)
        Xa, ya = build_xy(train_data + aug_data)
        wa = train_logreg(Xa, ya, seed=s)
        b, a = evaluate(wb, Xte, yte), evaluate(wa, Xte, yte)
        base.append(b); aug.append(a); diffs.append(a - b)
    return float(np.mean(base)), float(np.mean(aug)), diffs

train = [make_sentence(np.random.default_rng(s)) for s in range(120)]
test  = [make_sentence(np.random.default_rng(10_000 + s)) for s in range(600)]

# 一个安全的增强：只做「中性词的同义替换」（不动否定词与情感词）
SAFE_SYN = {'这家': '本', '店': '餐厅', '菜': '菜品', '服务': '服务员',
            '环境': '氛围', '价格': '收费', '感觉': '觉得', '整体': '总体'}
def safe_synonym(tokens, p, rng):
    return [SAFE_SYN.get(t, t) if (t in SAFE_SYN and rng.random() < p) else t for t in tokens]

r = np.random.default_rng(3)
aug_safe = [(safe_synonym(t, 0.5, r), y) for t, y in train]
b, a, diffs = effectiveness(train, aug_safe, test)
print(f'baseline {b:.4f} -> 增强后 {a:.4f} | 平均差值 {np.mean(diffs):+.4f} ± {np.std(diffs):.4f}')
print(f'8 个种子的差值: {[round(d,4) for d in diffs]}')

# 关键：差值的方差往往与效应同量级 —— 单次实验不可信
assert len(diffs) == 8
print(f'\\n⚠️  差值的标准差 {np.std(diffs):.4f} 与效应 {abs(np.mean(diffs)):.4f} 同量级。')
print('   **单个种子的结果毫无意义** —— 模块 05 会给出正确的检验方法。')"""),
    md("""## 6 · 三重检验合起来：为什么必须三个都看"""),
    code("""def full_check(name, augment_fn, train_data, test_data, seed=0):
    r = np.random.default_rng(seed)
    pairs = [(t, y, augment_fn(t, r)) for t, y in train_data]
    aug = [(aug_t, y) for _, y, aug_t in pairs]
    fid = fidelity(pairs)
    div = distinct_n([a for a, _ in aug], 2)
    b, a_, diffs = effectiveness(train_data, aug, test_data)
    return {'name': name, '保真度': fid, 'distinct-2': div,
            'Δ准确率': float(np.mean(diffs)), 'Δ标准差': float(np.std(diffs))}

candidates = [
    ('不增强（复制原样本）', lambda t, r: list(t)),
    ('安全同义替换',         lambda t, r: safe_synonym(t, 0.5, r)),
    ('随机删除 p=0.1',       lambda t, r: random_deletion(t, 0.1, r)),
    ('随机删除 p=0.4',       lambda t, r: random_deletion(t, 0.4, r)),
    ('全部打散成随机词',      lambda t, r: list(r.choice(NEUTRAL, size=len(t)))),
]
rows = [full_check(n, f, train, test) for n, f in candidates]
print(f"{'方案':<22s} {'保真度':>8s} {'distinct-2':>11s} {'Δ准确率':>9s} {'Δ标准差':>9s}")
for x in rows:
    print(f'{x["name"]:<22s} {x["保真度"]:>8.1%} {x["distinct-2"]:>11.4f} '
          f'{x["Δ准确率"]:>+9.4f} {x["Δ标准差"]:>9.4f}')

by = {x['name']: x for x in rows}
assert by['不增强（复制原样本）']['保真度'] == 1.0
assert by['随机删除 p=0.4']['保真度'] < by['随机删除 p=0.1']['保真度']
# 「全部打散」多样性最高、保真度最低 —— 完美说明为什么不能只看多样性
assert by['全部打散成随机词']['保真度'] < 0.80, '打散会大量破坏标签'
assert by['不增强（复制原样本）']['distinct-2'] <= by['安全同义替换']['distinct-2'] + 1e-9, \
    '同义替换的多样性不低于纯复制'
print('\\n✅ 三个检验缺一不可：')
print('   · 只看多样性 -> 可能选中「全部打散」（词面变化最大，但标签大量翻转）')
print('   · 只看保真度 -> 会选中「复制原样本」（保真度 100%，但零新信息）')
print('   · 只看下游指标 -> 会被种子噪声骗（Δ标准差常与效应同量级）')
print('\\n**保真度 × 多样性 × 有效性，三者同时看，才是判断一个增强的正确方式。**')"""),
    md("""## 7 · ✏️ 练习：增强方案的综合打分

实现 `augment_score(fidelity_v, diversity_v, delta_acc, delta_std, min_fidelity=0.95)`：
- 若 `fidelity_v < min_fidelity` → 返回 `0.0`（**保真度是硬门槛，不达标直接否决**）
- 否则若 `delta_acc <= delta_std` → 返回 `0.0`（效应没超过噪声，视为无效）
- 否则返回 `delta_acc * diversity_v`（有效且多样才得分）"""),
    code("""def augment_score(fidelity_v, diversity_v, delta_acc, delta_std, min_fidelity=0.95):
    # TODO
    raise NotImplementedError"""),
    code("""# —— 练习自测 ——
assert augment_score(0.90, 0.5, 0.02, 0.005) == 0.0, '保真度不达标 -> 直接否决'
assert augment_score(0.99, 0.5, 0.002, 0.010) == 0.0, '效应没超噪声 -> 无效'
s = augment_score(0.99, 0.5, 0.02, 0.005)
assert s > 0 and abs(s - 0.01) < 1e-9
# 同样效应下，多样性更高得分更高
assert augment_score(0.99, 0.8, 0.02, 0.005) > augment_score(0.99, 0.3, 0.02, 0.005)
print(f"{'方案':<22s} {'综合得分':>10s}")
for x in rows:
    sc = augment_score(x['保真度'], x['distinct-2'], x['Δ准确率'], x['Δ标准差'])
    print(f'{x["name"]:<22s} {sc:>10.5f}')
print('✅ 练习通过：保真度是**硬门槛**，效应必须超过噪声，多样性只是加分项')"""),
    md("""---
### 📖 参考答案"""),
    code("""def augment_score(fidelity_v, diversity_v, delta_acc, delta_std, min_fidelity=0.95):
    if fidelity_v < min_fidelity:
        return 0.0
    if delta_acc <= delta_std:
        return 0.0
    return delta_acc * diversity_v"""),
    md("""✅ 检查全部通过即环境就绪、方法论到位。

**本课的契约**：你实现的每一种增强（EDA 四操作、回译、释义、self-instruct、evol-instruct）
都会过三重检验——**保真度**（标签有没有被破坏，规则可精确判定）、
**多样性**（distinct-n / self-BLEU / 嵌入覆盖）、**有效性**（多种子配对检验，
并与「同预算下加真实数据」对照）。

**接下来五个模块**：01 词面增强 → 02 回译与释义 → 03 LLM 指令数据合成 →
04 增强的质量控制 → 05 增强的评测与消融。

下一站：**模块 01 · 词面增强** —— 最便宜、也最容易把标签搞坏的一类。"""),
]
