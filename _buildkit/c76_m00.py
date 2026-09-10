# -*- coding: utf-8 -*-
"""C76 模块 00 · 课程总览：随机化解决了什么、又留下了什么。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "<strong>C10 模块 07（在线 A/B 评测）是软前提</strong>——"
                 "假设检验、功效/MDE、多重比较、序贯检验、CUPED 在那里，本课<em>不重复</em>；"
                 "概率与线性回归（最小二乘、条件期望）；"
                 "<em>C19（可解释性中的 d-分离）与 C65（辛普森悖论）有少量重叠概念，但用途不同</em>"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（<strong>把「朴素差 = ATT + 选择偏差」验证到浮点精度</strong>：'
                       '差 $0.000\\times10^{0}$ / '
                       '随机化把选择偏差压到 $10^{-3}$ 量级、误差 $\\propto 1/\\sqrt{n}$ / '
                       '<strong>再量出随机化<em>没有</em>解决的四件事，每件一个数字</strong>）'),
    ("核心参考", "Imbens &amp; Rubin, <em>Causal Inference for Statistics, Social, and "
                 "Biomedical Sciences</em>（2015）· "
                 "Pearl, <em>Causality</em>（2nd ed., 2009）· "
                 "Chernozhukov et al., <em>Double/Debiased Machine Learning</em>（2018）· "
                 "Angrist &amp; Pischke, <em>Mostly Harmless Econometrics</em>（2009）· "
                 "Athey &amp; Imbens, <em>The State of Applied Econometrics</em>（JEP 2017）· "
                 "本课程 <strong>C10 模块 07</strong>（A/B 统计工具箱）· C19（因果图的另一种用法）"),
    ("预计时长", "读 40 分钟 + 跑 35 分钟"),
]

SECTIONS = [

("identity", "一个恒等式先把整门课框定了", "".join([
    P("在线实验做久了会形成一种直觉：<strong>把两组的指标一减，就是效应</strong>。"
      "这个直觉在随机化成立时是对的，而且它对得如此可靠，以至于人们很少去问它<em>为什么</em>对。"
      "本课从那个「为什么」开始，因为答案里藏着一条恒等式，"
      "而恒等式的每一项都对应本课后面的一个模块。"),
    P("记 $Y_i(1)$ 与 $Y_i(0)$ 为个体 $i$ 在处理与不处理下<strong>各自会取到的</strong>结果"
      "（potential outcome，潜在结果），$T_i \\in \\{0,1\\}$ 是实际处理。"
      "个体因果效应 $\\tau_i = Y_i(1) - Y_i(0)$ 永远观测不到——"
      "任一时刻我们只能看到 $Y_i = Y_i(T_i)$ 中的一个。这是<strong>因果推断的根本问题</strong>。"),
    MATH("\\underbrace{E[Y \\mid T{=}1] - E[Y \\mid T{=}0]}_{\\text{朴素差（能算）}}"
         " = \\underbrace{E[Y(1) - Y(0) \\mid T{=}1]}_{\\text{ATT（想要）}}"
         " + \\underbrace{E[Y(0) \\mid T{=}1] - E[Y(0) \\mid T{=}0]}_{\\text{选择偏差}}"),
    P("这不是近似，是<strong>代数恒等式</strong>：把中间项 $E[Y(0)\\mid T{=}1]$ 加一次减一次即可。"
      "配套 notebook 在一个已知全部 $Y(0)/Y(1)$ 的合成人群上把它验证到浮点精度——"
      "<strong>朴素差 $1.582605$ = ATT $0.647736$ + 选择偏差 $0.934869$，两边之差恰为 $0$</strong>。"),
    CALLOUT("intuition", "为什么这条恒等式值得记住",
            "它把「我的估计错了多少」变成了一个<strong>有名字的量</strong>："
            "选择偏差 $= E[Y(0)\\mid T{=}1] - E[Y(0)\\mid T{=}0]$，"
            "即<em>「处理组的人如果没被处理，会不会本来就跟对照组不一样」</em>。"
            "所有识别策略——随机化、后门调整、工具变量、双重差分——"
            "做的都是同一件事：<strong>给这一项一个等于零（或可估计）的理由</strong>。"),
    P("在同一个合成人群上，三个常被混用的目标量数值上并不相等："
      "<strong>ATE $=0.999902$、ATT $=0.647736$、ATC $=1.350613$</strong>——"
      "$\\text{ATT}/\\text{ATC} = 0.480$，即<em>已经被处理的人从处理里获益<strong>更少</strong></em>"
      "（自选择进来的人往往本来就会做得不错）。"
      "而选择偏差 $0.934869$ 是真效应的 <strong>0.93 倍</strong>，"
      "于是朴素差把 ATE 高估了 <strong>1.58 倍</strong>——"
      "不是因为样本量不够，是因为估的不是同一件事。"),
])),

("randomization", "随机化解决了什么", "".join([
    P("随机分配处理让 $T$ 与 $(Y(0), Y(1))$ 独立，于是 $E[Y(0)\\mid T{=}1] = E[Y(0)\\mid T{=}0]$，"
      "选择偏差<strong>结构性地</strong>为零。notebook 里在同一人群上重随机三次，"
      "选择偏差落在 $-0.0069$ / $-0.0067$ / $-0.0017$；"
      "而样本量每乘 $4$ 时 RMSE 的比值是 $2.20$ / $1.96$ / $1.92$，"
      "即 $\\propto 1/\\sqrt{n}$——<strong>剩下的只是噪声，不是偏差</strong>。"),
    P("这就是 A/B 测试的全部力量所在，也是 <strong>C10 模块 07</strong> 的领地："
      "随机化把因果问题降级成了统计问题，之后的事情是检验、功效、多重比较、序贯与方差缩减。"
      "那些内容本课<strong>一概不重复</strong>。"),
    CALLOUT("warn", "本课与 C10 模块 07 的边界",
            "C10-07 假设<strong>随机化有效</strong>，然后把统计做对。"
            "本课处理它<strong>无效或不够</strong>的情形："
            "不能随机化（只有观测数据）、随机化被违反（干扰、不依从）、"
            "随机化本身有效但<strong>测的不是你要的量</strong>（个体随机化下的干扰、短期代理指标）。"
            "两门课不重叠：本课里没有 $z$ 检验、功效曲线、Bonferroni 或 CUPED。"),
])),

("map", "四条路线与它们各自的失效点", "".join([
    P("当随机化不可得或不够时，识别因果效应只有有限几条路线。"
      "本课把它们排成一张图，<strong>每条路线都在 notebook 里注入一次错误并量出代价</strong>："),
    ASCII("""
                        选择偏差 = E[Y(0)|T=1] - E[Y(0)|T=0]
                                       |
        +--------------------+---------+---------+--------------------+
        |                    |                   |                    |
   随机化(C10-07)      后门调整(m02/m03)     准实验(m04)        设计与归因(m05)
   把它设计成 0        用可观测变量把它       用外生变化把它      随机化有效，
        |             条件成零              局部地打掉          但测量口径错
        |                    |                   |                    |
  失效: 干扰/代理      失效: 控制错变量       失效: 假设不可检验    失效: SUTVA/顺序规则
  m05: 1.00 vs 2.00   m02: 偏差 0 -> 2.59   m04: pre-trend 通过   m05: 7.1% vs 38.0%
                       m03: AIPW 静默退化      但 DiD 偏 +1.50        (last-touch)
""".strip("\n")),
    TABLE(["路线", "关键假设", "本课注入的错误", "量出的代价"],
          [["随机化", "分配与潜在结果独立", "个体随机化 + 网络干扰",
            "测到 $1.00$，全局效应是 $2.00$"],
           ["后门调整", "条件独立（无未观测混杂）", "多控制一个对撞变量",
            "偏差从 $0$ 跳到 $2.59$"],
           ["倾向得分 / 双重稳健", "重叠 + 至少一个 nuisance 正确", "结果模型过拟合",
            "修正项被吃掉 $4.4\\times10^{5}$ 倍"],
           ["准实验", "平行趋势 / 工具外生 / 断点连续", "只在处理后才分叉的趋势",
            "pre-trend 检验通过（$\\vert t\\vert{=}0.77$），DiD 偏 $+1.50$"],
           ["归因规则", "（通常没有明确的因果目标）", "用曝光顺序分配功劳",
            "真实份额 $7.1\\%$ 被记成 $38.0\\%$"]]),
    P("这张表里最值得注意的一点：<strong>五个失效场景里，没有一个会报错</strong>。"
      "每一个都给出一个格式正确、置信区间漂亮、能写进周报的数字。"
      "所以本课的可交付物不是「更好的估计量」，而是<strong>知道每个估计量在什么条件下悄悄失效</strong>。"),
])),

("preview", "三个会在后面反复出现的反直觉", "".join([
    H3("① 控制更多变量可以让结果更糟"),
    P("在一个真实总效应为 $2.9$ 的图上，控制 $\\{X\\}$ 给出 $2.899$（无偏），"
      "而<strong>再加一个变量</strong>控制 $\\{X, C\\}$ 给出 $0.307$——"
      "偏差从 $0$ 变成 $2.59$。$C$ 是处理与结果的共同<em>后代</em>（对撞），控制它打开了一条假路径。"
      "更进一步：模块 02 会构造一个连「只控制<strong>处理前</strong>变量」都不安全的例子"
      "（偏差 $+0.001 \\to -0.312$）。"),
    H3("② 弱工具变量不是「噪声大」，是悄悄退回它本该修掉的估计"),
    P("内生性让 OLS 上偏到中位数 $1.7994$（真值 $1.0$）。"
      "第一阶段 $F$ 中位数为 $0.46$ 时，2SLS 的中位数是 <strong>$1.8009$</strong>——"
      "与 OLS 已经无法区分。而它的<em>均值</em>在正负之间乱跳，"
      "因为恰好识别的 2SLS <strong>没有有限矩</strong>，报告均值本身就是错的。"),
    H3("③ 短期代理指标可以在符号上骗你"),
    P("结构 $T \\to S \\to Y$ 加一条 $T \\to Y$ 的直接通道。"
      "短期代理 $S$ 上涨 $+1.005$，代理指标模型据此预测长期效应 $+1.005$，"
      "而<strong>真实长期效应是 $-0.999$</strong>。"
      "代理指标只能看见「经过 $S$ 的那部分」，绕过 $S$ 的通道它完全看不见，也不会告警。"),
    CALLOUT("danger", "本课的一条纪律",
            "以上三条以及后面所有结论，都在 notebook 里由<strong>断言</strong>验证，"
            "而不是由叙述断定。多处结论是在探数阶段被测量结果<strong>推翻后重写</strong>的——"
            "例如「RDD 带宽越小偏差越小」在两侧曲率<em>对称</em>时是假的"
            "（偏差在左右之差里恰好抵消，最优带宽变成用满全部数据），"
            "而「合成控制的 pre 期拟合越好越可信」在四种设定里的预测力是<strong>掷硬币</strong>。"),
])),

("howto", "怎么用这门课", "".join([
    P("六个模块沿「假设从强到弱」排列，而不是沿「方法从简到繁」排列："),
    OL(["<strong>模块 01</strong>：潜在结果框架——把问题写成一个有明确目标量的形式。"
        "ATE / ATT / ATC / CATE 的区别、识别与估计的分工。",
        "<strong>模块 02</strong>：因果图与识别——后门准则告诉你<em>控制什么</em>，"
        "以及为什么「控制得越多越好」和「只控制处理前变量」两条民间规则都是错的。",
        "<strong>模块 03</strong>：倾向得分、IPW、双重稳健、双重机器学习——"
        "在后门假设成立后，<em>怎么估</em>，以及每个估计量的静默失效模式。",
        "<strong>模块 04</strong>：准实验——后门假设<em>不</em>成立时，"
        "DiD / IV / RDD / 合成控制各自借用什么外生性，以及各自的假设为什么不可检验。",
        "<strong>模块 05</strong>：线上归因——回到实验有效但口径错的情形："
        "SUTVA 与干扰、集群随机化与 switchback、多触点归因、代理指标。"]),
    P("模块之间的依赖是线性的：后一个模块放松前一个模块的一条假设，"
      "或者量化违反它的代价。所以顺序读比挑着读更省力，"
      "而<strong>模块 02 是全课的枢纽</strong>——"
      "它给出的「该控制什么」是模块 03 全部估计量的输入，"
      "而模块 04 处理的正是「它给不出合法调整集」的情形。"),
    P("每个模块的 notebook 是纯 numpy、CPU、离线，含 4 个练习（TODO 桩 + 自测断言）、"
      "参考答案与一个真实工程胶囊。<strong>不需要任何真实实验数据</strong>："
      "所有数据生成过程的真值都是已知的，这正是能判断估计量对错的前提。"),
    P("每个模块都有一条「如果只记一件事」的线："),
    TABLE(["模块", "如果只记一件事"],
          [["00", "朴素差 $=$ ATT $+$ 选择偏差，是<strong>恒等式</strong>；"
            "识别策略做的都是给后一项一个等于零的理由"],
           ["01", "先说清要 ATE / ATT / ATC / CATE 中的哪一个，"
            "<strong>再</strong>谈估计——本课人群上它们相差 $2.09$ 倍"],
           ["02", "「控制什么」不能靠直觉：$8$ 个候选子集里只有 $1$ 个合法，"
            "而<strong>多控制一个变量能把偏差从 $0$ 变成 $2.6$</strong>"],
           ["03", "IPW 的问题从来不是偏差而是方差；"
            "而一个自称「双重稳健」的实现可以在不报错的情况下<strong>就是</strong>纯插入估计量"],
           ["04", "四种准实验的核心假设<strong>都不可从数据检验</strong>，"
            "常用的「检验」只能证伪、且功效常常不足"],
           ["05", "随机化完全有效时仍可能<strong>测的不是你要的量</strong>，"
            "而这一类失效不产生任何异常统计量"]]),
    CALLOUT("paper", "一句话读法",
            "如果只读一节：读<strong>模块 02 第 3 节</strong>（控制变量的枚举表）。"
            "如果只跑一个 notebook：跑<strong>模块 03</strong>"
            "（那里有两个 bit 级恒等式，说明一个自称「双重稳健」的实现"
            "可以在不报任何错的情况下<em>就是</em>纯插入估计量）。"),
])),
]

NB = [
md("""# C76 模块 00 · 环境检查与总览

本 notebook 做三件事：

1. 把 **「朴素差 = ATT + 选择偏差」** 验证到浮点精度；
2. 量出随机化把选择偏差压到多小、以及误差随 $n$ 的标度；
3. 量出随机化**没有**解决的四件事，每件一个数字。

纯 numpy / CPU / 离线。"""),

code("""import sys, platform
import numpy as np
print('python   ', sys.version.split()[0])
print('platform ', platform.platform())
print('numpy    ', np.__version__)
print()
print('本课全部计算为纯 numpy / CPU / 离线，无需任何真实实验数据。')
assert np.__version__ >= '1.20', 'numpy 版本过低'
print('OK')"""),

md("""## 1. 一个已知全部潜在结果的合成人群

真实数据里 $Y_i(0)$ 与 $Y_i(1)$ 只能看见一个。合成数据里两个都能看见——
这正是我们能判断一个估计量对错的唯一办法。"""),

code("""def make_population(n=200_000, seed=0):
    '''构造一个 Y(0)、Y(1)、tau、T 全部已知的人群。

    x     : 一个可观测的协变量（如用户历史活跃度）
    Y(0)  : 不处理时的结果，随 x 递增
    tau   : 个体效应，随 x 递减（活跃用户从处理里得到的更少）
    T     : 处理指派，随 x 递增 -> 与 Y(0) 正相关 -> 选择偏差
    '''
    r = np.random.default_rng(seed)
    x  = r.normal(0.0, 1.0, n)
    Y0 = 1.0 * x + r.normal(0.0, 0.5, n)
    tau = 1.0 - 0.75 * x
    Y1 = Y0 + tau
    p  = 1.0 / (1.0 + np.exp(-1.2 * x))     # 倾向得分
    T  = (r.random(n) < p).astype(float)
    Y  = np.where(T == 1, Y1, Y0)           # 只有这一列在真实数据里可见
    return dict(x=x, Y0=Y0, Y1=Y1, tau=tau, T=T, Y=Y, p=p)

pop = make_population()
T, Y, Y0, Y1, tau = pop['T'], pop['Y'], pop['Y0'], pop['Y1'], pop['tau']
print(f"人群规模 {len(T):,}，处理率 {T.mean():.4f}")
print()
print('三个目标量（用上帝视角算，真实数据里算不出）：')
ATE = tau.mean()
ATT = tau[T == 1].mean()
ATC = tau[T == 0].mean()
print(f'  ATE  E[tau]        = {ATE:.6f}   全人群平均效应')
print(f'  ATT  E[tau|T=1]    = {ATT:.6f}   已被处理者的平均效应')
print(f'  ATC  E[tau|T=0]    = {ATC:.6f}   未被处理者的平均效应')
print()
print(f'ATT / ATC = {ATT/ATC:.3f}  -> 三者数值上不相等，先说清要哪一个再谈估计')"""),

md("""## 2. 恒等式：朴素差 = ATT + 选择偏差

$$E[Y \\mid T{=}1] - E[Y \\mid T{=}0]
= \\underbrace{E[Y(1)-Y(0) \\mid T{=}1]}_{\\text{ATT}}
+ \\underbrace{E[Y(0) \\mid T{=}1] - E[Y(0) \\mid T{=}0]}_{\\text{选择偏差}}$$"""),

code("""naive = Y[T == 1].mean() - Y[T == 0].mean()
sel   = Y0[T == 1].mean() - Y0[T == 0].mean()

print(f'朴素差       = {naive:.6f}')
print(f'ATT          = {ATT:.6f}')
print(f'选择偏差     = {sel:.6f}')
print(f'ATT + 选择偏差 = {ATT + sel:.6f}')
print()
print(f'恒等式两边之差 = {abs(naive - (ATT + sel)):.3e}   <- 这是恒等式，不是近似')
assert abs(naive - (ATT + sel)) < 1e-12

print()
print(f'选择偏差 / 真效应 = {sel/ATE:.3f} 倍')
print(f'朴素差 / ATE      = {naive/ATE:.3f} 倍   <- 朴素差把 ATE 高估了这么多')
print()
print('注意：偏差的来源是 T 与 Y(0) 的相关，与样本量无关。')
print('     加大样本只会让这个错误的数字更精确。')"""),

md("""## 3. 随机化把选择偏差归零

把指派换成抛硬币，其它一切不变。"""),

code("""def randomize(pop, seed):
    r = np.random.default_rng(seed)
    Trand = (r.random(len(pop['Y0'])) < 0.5).astype(float)
    Yobs  = np.where(Trand == 1, pop['Y1'], pop['Y0'])
    return Trand, Yobs

print('重随机三次（同一人群，只换指派）:')
print('  seed   朴素差      选择偏差      与 ATE 之差')
for s in (1, 2, 3):
    Tr, Yr = randomize(pop, s)
    nv = Yr[Tr == 1].mean() - Yr[Tr == 0].mean()
    sb = pop['Y0'][Tr == 1].mean() - pop['Y0'][Tr == 0].mean()
    print(f'  {s:4d}   {nv:+.6f}   {sb:+.6f}    {nv-ATE:+.6f}')
print()
print(f'对照：非随机指派下选择偏差 = {sel:+.6f}')
print('-> 随机化不是把偏差变小，是把它的**来源**去掉了。')

print()
print('误差随 n 的标度（每个 n 跑 200 次重随机，取 RMSE）:')
prev = None
for n in (2_000, 8_000, 32_000, 128_000):
    small = make_population(n=n, seed=11)
    errs = []
    for s in range(200):
        Tr, Yr = randomize(small, 1000 + s)
        errs.append(Yr[Tr == 1].mean() - Yr[Tr == 0].mean() - small['tau'].mean())
    rmse = float(np.sqrt(np.mean(np.square(errs))))
    ratio = '' if prev is None else f'   前一档/本档 = {prev/rmse:.2f}'
    print(f'  n={n:7,}  RMSE = {rmse:.5f}{ratio}')
    prev = rmse
print()
print('-> 每次 n 乘 4，RMSE 约减半，比值约 2.0 -> 误差 ∝ 1/sqrt(n)。')
print('   这就是 C10 模块 07 的全部前提：偏差已为 0，剩下的是统计问题。')"""),

md("""## 4. 随机化**没有**解决的四件事

下面四段各是本课一个模块的预演。每段只给数字，机制留到对应模块。"""),

code("""# (a) 干扰（interference）：随机化有效，但测到的不是全局效应
def ring_neighbors(n, k):
    return [[(i + d) % n for d in list(range(-k, 0)) + list(range(1, k + 1))] for i in range(n)]

def interference_demo(n=4000, k=5, direct=1.0, spill=1.0, cluster=None, seed=0):
    r = np.random.default_rng(seed)
    nb = ring_neighbors(n, k)
    if cluster is None:
        Ti = (r.random(n) < 0.5).astype(float)
    else:
        z = (r.random(n // cluster) < 0.5).astype(float)
        Ti = np.repeat(z, cluster)
    frac = np.array([Ti[v].mean() for v in nb])
    Yi = direct * Ti + spill * frac + r.normal(0, 0.5, n)
    return float(Yi[Ti == 1].mean() - Yi[Ti == 0].mean())

est_ind = np.mean([interference_demo(seed=s) for s in range(20)])
est_clu = np.mean([interference_demo(cluster=500, seed=s) for s in range(20)])
print('(a) 干扰：Y = 1.0*自己处理 + 1.0*邻居处理比例，全局效应 = 2.0')
print(f'    个体随机化 A/B      -> {est_ind:+.4f}   (只有直接效应)')
print(f'    集群随机化 m=500    -> {est_clu:+.4f}   (接近全局效应)')
print(f'    个体随机化漏掉了 {(2.0-est_ind)/2.0*100:.0f}% 的效应，且没有任何统计告警')
assert est_ind < 1.2 and est_clu > 1.8"""),

code("""# (b) 代理指标：短期指标可以在符号上骗你
def surrogate_demo(a=1.0, b=1.0, d=0.0, n=200_000, seed=7):
    r = np.random.default_rng(seed)
    Tz = (r.random(n) < 0.5).astype(float)
    S  = a * Tz + r.normal(0, 1, n)
    Yl = b * S + d * Tz + r.normal(0, 1, n)
    return Tz, S, Yl

# 历史实验（替代性成立 d=0）学 h(S) = E[Y|S]
Th, Sh, Yh = surrogate_demo(d=0.0, seed=99)
A = np.column_stack([np.ones(len(Sh)), Sh])
beta = np.linalg.lstsq(A, Yh, rcond=None)[0]

print('(b) 代理指标：T -> S(短期) -> Y(长期)，外加一条 T -> Y 的直接通道 d')
print('    当期 d      短期 ΔS     代理指标预测 ΔY     真实长期 ΔY')
for d in (0.0, 1.0, -2.0):
    Tz, S, Yl = surrogate_demo(d=d)
    ds = S[Tz == 1].mean() - S[Tz == 0].mean()
    si = (np.column_stack([np.ones(len(S)), S]) @ beta)
    si = si[Tz == 1].mean() - si[Tz == 0].mean()
    dy = Yl[Tz == 1].mean() - Yl[Tz == 0].mean()
    flag = '   <- 符号反了' if si * dy < 0 else ''
    print(f'    {d:+5.1f}     {ds:+.4f}     {si:+13.4f}     {dy:+10.4f}{flag}')
print('    代理指标只看见经过 S 的那部分；绕过 S 的通道它看不见，也不报警。')"""),

code("""# (c) 归因规则：随机化根本没参与，功劳按曝光顺序分
import itertools, math
CH = ['搜索', '社交', '邮件', '直达']
BASE = {'搜索': 0.30, '社交': 0.20, '邮件': 0.05, '直达': 0.10}

def conv_prob(S):
    p = 1.0
    for c in S:
        p *= (1 - BASE[c])
    return 1 - p

def shapley_values():
    '''Shapley 值：对全部到达顺序取平均的边际贡献。'''
    phi = {c: 0.0 for c in CH}
    for perm in itertools.permutations(CH):
        cur, prev = set(), conv_prob(set())
        for c in perm:
            cur.add(c)
            now = conv_prob(cur)
            phi[c] += now - prev
            prev = now
    return {c: v / math.factorial(len(CH)) for c, v in phi.items()}

sh = shapley_values()
full = conv_prob(set(CH))
print('(c) 多触点归因：转化概率只取决于**曝光集合**，与顺序完全无关')
print(f'    全触点转化概率 = {full:.4f}；Shapley 值之和 = {sum(sh.values()):.4f} (有效性公理)')
print()
print('    渠道    Shapley 真实份额')
for c in CH:
    print(f'    {c}         {sh[c]/full*100:5.1f}%')
print()
print('    模块 05 会证明: 邮件的真实份额 7.1%，last-touch 记它 38.0% (高估 5.4 倍)。')
print('    这不是估计误差 —— 规则本身与因果贡献无关。')
assert abs(sum(sh.values()) - full) < 1e-12"""),

code("""# (d) 外部效度：随机化给出的是**这批人**的效应
print('(d) 外部效度：随机化让 ATE 可估，但那是**被抽到的人群**的 ATE')
sub_hi = pop['x'] > 0.5
sub_lo = pop['x'] < -0.5
print(f'    全人群 ATE            = {tau.mean():+.4f}')
print(f'    x > +0.5 子人群 ATE   = {tau[sub_hi].mean():+.4f}')
print(f'    x < -0.5 子人群 ATE   = {tau[sub_lo].mean():+.4f}')
print(f'    两个子人群相差 {abs(tau[sub_hi].mean()-tau[sub_lo].mean()):.4f}，'
      f'是全人群 ATE 的 {abs(tau[sub_hi].mean()-tau[sub_lo].mean())/tau.mean():.2f} 倍')
print()
print(f'    全人群里有 {(tau < 0).mean()*100:.1f}% 的个体效应是**负的**，'
      f'而 ATE = {tau.mean():+.4f} 完全看不出这一点')
print()
print('    效应异质时，「在 A 人群做的实验」不能直接搬到 B 人群。')
print('    模块 01 会把这一点写成 CATE，模块 03 用它做重加权。')
assert tau[sub_hi].mean() < tau.mean() < tau[sub_lo].mean()
assert abs(tau[sub_hi].mean() - tau[sub_lo].mean()) > 1.5 * tau.mean()"""),

md("""## ✏️ 练习 1：把恒等式反过来用

真实数据里选择偏差算不出来（因为 $Y(0)$ 在处理组不可见）。
但如果**知道**真实的 ATT，就能把选择偏差反解出来。

实现 `implied_selection_bias(Y, T, att)`，返回恒等式蕴含的选择偏差。"""),

code("""def implied_selection_bias(Y, T, att):
    '''由恒等式反解选择偏差： 朴素差 - ATT。

    参数
    ----
    Y   : 观测结果 (n,)
    T   : 处理指派 (n,) 取值 0/1
    att : 已知的真实 ATT（标量）

    返回
    ----
    float : 选择偏差
    '''
    # TODO: 用恒等式 朴素差 = ATT + 选择偏差
    raise NotImplementedError"""),

code("""# 自测
_pop = make_population(n=50_000, seed=5)
_T, _Y, _Y0, _tau = _pop['T'], _pop['Y'], _pop['Y0'], _pop['tau']
_att = _tau[_T == 1].mean()
_true_sb = _Y0[_T == 1].mean() - _Y0[_T == 0].mean()

_got = implied_selection_bias(_Y, _T, _att)
assert abs(_got - _true_sb) < 1e-12, f'反解应等于真实选择偏差：{_got} vs {_true_sb}'

# 随机化数据上应接近 0
_Tr, _Yr = randomize(_pop, 42)
_att_r = _tau[_Tr == 1].mean()
_sb_r = implied_selection_bias(_Yr, _Tr, _att_r)
assert abs(_sb_r) < 0.05, f'随机化后选择偏差应接近 0，得到 {_sb_r}'

print(f'✅ 观测数据反解出的选择偏差 = {_got:+.6f}（真值 {_true_sb:+.6f}）')
print(f'✅ 随机化数据反解出的选择偏差 = {_sb_r:+.6f}（应接近 0）')"""),

md("""## ✏️ 练习 2：ATE / ATT / ATC 的加权关系

三个目标量不是独立的。设处理率 $\\pi = P(T{=}1)$，则

$$\\text{ATE} = \\pi \\cdot \\text{ATT} + (1-\\pi) \\cdot \\text{ATC}$$

实现 `ate_from_att_atc(att, atc, pi)`，并在自测里验证这个恒等式。"""),

code("""def ate_from_att_atc(att, atc, pi):
    '''由 ATT、ATC 与处理率合成 ATE。

    参数
    ----
    att : E[tau | T=1]
    atc : E[tau | T=0]
    pi  : P(T=1)

    返回
    ----
    float : ATE
    '''
    # TODO: 全期望公式
    raise NotImplementedError"""),

code("""# 自测
_pop = make_population(n=120_000, seed=3)
_T, _tau = _pop['T'], _pop['tau']
_att = _tau[_T == 1].mean()
_atc = _tau[_T == 0].mean()
_pi  = _T.mean()
_ate = _tau.mean()

_got = ate_from_att_atc(_att, _atc, _pi)
assert abs(_got - _ate) < 1e-12, f'加权应精确恢复 ATE：{_got} vs {_ate}'

# 极端处理率下退化为 ATT / ATC
assert abs(ate_from_att_atc(_att, _atc, 1.0) - _att) < 1e-12
assert abs(ate_from_att_atc(_att, _atc, 0.0) - _atc) < 1e-12

print(f'✅ ATE = {_pi:.4f}*{_att:.4f} + {1-_pi:.4f}*{_atc:.4f} = {_got:.6f}')
print(f'   真值 {_ate:.6f}，差 {abs(_got-_ate):.3e}')
print(f'✅ pi=1 时退化为 ATT，pi=0 时退化为 ATC')"""),

md("""## ✏️ 练习 3：量出个体随机化在干扰下漏掉多少

在上面的环形图模型里，全局效应是 `direct + spill`。
实现 `missed_fraction(direct, spill)`，返回**个体随机化**在 $p=0.5$ 下
预期漏掉的效应比例。

提示：个体随机化两臂的邻居处理比例都约等于 $p$，所以邻居项在相减时抵消。"""),

code("""def missed_fraction(direct, spill):
    '''个体随机化 A/B 在干扰下漏掉的效应比例。

    全局效应 = direct + spill；个体随机化只测到 direct。

    参数
    ----
    direct : 自身被处理的效应
    spill  : 邻居全部被处理时的溢出效应

    返回
    ----
    float : 漏掉的比例，取值 [0, 1]
    '''
    # TODO: (全局效应 - 个体随机化测到的) / 全局效应
    raise NotImplementedError"""),

code("""# 自测
def _measure(direct, spill, seeds=20):
    return np.mean([interference_demo(direct=direct, spill=spill, seed=s) for s in range(seeds)])

for _d, _s in [(1.0, 1.0), (1.0, 0.0), (1.0, 3.0), (2.0, 0.5)]:
    _pred = missed_fraction(_d, _s)
    _meas = _measure(_d, _s)
    _emp  = (_d + _s - _meas) / (_d + _s)
    assert abs(_pred - _emp) < 0.05, f'direct={_d}, spill={_s}: 预测 {_pred:.4f} vs 实测 {_emp:.4f}'
    print(f'  direct={_d}, spill={_s}: 漏掉 {_pred*100:5.1f}%（实测 {_emp*100:5.1f}%，A/B 测到 {_meas:+.4f}）')

assert abs(missed_fraction(1.0, 0.0)) < 1e-12, '无溢出时不该漏掉任何东西'
assert missed_fraction(1.0, 1.0) > 0.45, '溢出等于直接效应时应漏掉约一半'
print()
print('✅ 溢出越大，个体随机化漏掉的比例越高；spill=0 时漏掉 0。')"""),

md("""## ✏️ 练习 4：代理指标何时可信

替代性（surrogacy）假设要求 $T$ 对 $Y$ **没有绕过 $S$ 的直接效应**。
这个假设在**有长期数据的历史实验**里是可以部分检验的：
回归 $Y \\sim T + S$，若替代性成立，$T$ 的系数应为 $0$。

实现 `surrogacy_test(T, S, Y)`，返回控制 $S$ 后 $T$ 的回归系数。"""),

code("""def surrogacy_test(T, S, Y):
    '''替代性检验：回归 Y ~ 1 + T + S，返回 T 的系数。

    替代性成立时该系数应为 0（T 对 Y 的全部影响都经过 S）。

    参数
    ----
    T : 处理指派 (n,)
    S : 短期代理指标 (n,)
    Y : 长期结果 (n,)

    返回
    ----
    float : T 的系数
    '''
    # TODO: 用 np.linalg.lstsq 拟合 Y ~ 1 + T + S，返回 T 的系数
    raise NotImplementedError"""),

code("""# 自测
for _d, _verdict in [(0.0, '通过'), (1.0, '拒绝'), (-2.0, '拒绝')]:
    _T2, _S2, _Y2 = surrogate_demo(d=_d, n=200_000, seed=5)
    _c = surrogacy_test(_T2, _S2, _Y2)
    assert abs(_c - _d) < 0.02, f'真 d={_d} 时系数应约为 {_d}，得到 {_c:.4f}'
    _got = '通过' if abs(_c) < 0.05 else '拒绝'
    assert _got == _verdict
    print(f'  真 d={_d:+5.1f}  控制 S 后 T 的系数 = {_c:+.4f}  -> 替代性{_got}')

print()
print('✅ 检验能恢复真实的直接效应强度 d。')
print('   但注意：这个检验需要**已经有**长期结果的历史实验。')
print('   代理指标省的是未来的等待，不是过去的等待。')"""),

md("""## 📖 参考答案"""),

code("""def implied_selection_bias(Y, T, att):
    '''由恒等式反解选择偏差： 朴素差 - ATT。'''
    naive = Y[T == 1].mean() - Y[T == 0].mean()
    return float(naive - att)

def ate_from_att_atc(att, atc, pi):
    '''全期望公式：ATE = pi*ATT + (1-pi)*ATC。'''
    return float(pi * att + (1.0 - pi) * atc)

def missed_fraction(direct, spill):
    '''个体随机化只测到 direct，全局效应是 direct+spill。'''
    total = direct + spill
    if total == 0:
        return 0.0
    return float((total - direct) / total)

def surrogacy_test(T, S, Y):
    '''回归 Y ~ 1 + T + S，返回 T 的系数。'''
    A = np.column_stack([np.ones(len(Y)), T, S])
    beta = np.linalg.lstsq(A, Y, rcond=None)[0]
    return float(beta[1])

print('参考答案已定义。')
print()
print('要点：')
print('  1. 选择偏差是恒等式的一项，不是误差项 —— 它有确定的数值。')
print('  2. ATE/ATT/ATC 由处理率线性联系；报告哪一个是**建模决定**，不是估计细节。')
print('  3. missed_fraction = spill/(direct+spill)：干扰的代价与溢出强度成正比。')
print('  4. 替代性可以在历史实验里部分检验，但检验本身需要长期数据。')"""),

md("""## 🧪 真实工程胶囊：一份「因果结论」上线前的检查单

下面这段代码把本课六个模块各自的核心检查压成一个函数。
它不做估计，只做**记账**：把一个因果结论所依赖的假设逐条列出来，
每条要么给出支持它的证据，要么明确标注为「未验证」。

这类清单在工程上的价值不是防止犯错，而是让**假设从隐式变成显式**——
本课全部五个失效场景都不会报错，所以唯一的防线是有人在某处写下了
「这一步依赖 X，而我们没验证 X」。"""),

code("""def causal_checklist(claim, design, evidence):
    '''把一个因果结论的假设逐条记账。

    design : 'rct' | 'backdoor' | 'quasi' | 'attribution'
    evidence : dict，键为假设名，值为 (是否验证, 证据字符串)
    '''
    REQUIRED = {
        'rct':        ['随机化实现正确', 'SUTVA/无干扰', '结果指标口径 = 决策口径', '外部效度'],
        'backdoor':   ['无未观测混杂', '调整集满足后门准则', '重叠/正性', 'nuisance 模型或交叉拟合'],
        'quasi':      ['识别假设（平行趋势/外生性/连续性）', '假设的可检验部分已检验',
                       '假设的不可检验部分已论证', '估计目标是 LATE 还是 ATE'],
        'attribution':['归因规则有明确的因果目标', '规则对曝光顺序的依赖已评估',
                       '代理指标的替代性已检验'],
    }
    req = REQUIRED[design]
    print(f'结论: {claim}')
    print(f'设计: {design}')
    print('-' * 74)
    unver = 0
    for k in req:
        ok, note = evidence.get(k, (False, '未提供'))
        mark = 'OK  ' if ok else 'TODO'
        if not ok:
            unver += 1
        print(f'  [{mark}] {k:34s} {note}')
    print('-' * 74)
    print(f'  {len(req)-unver}/{len(req)} 条已验证，{unver} 条未验证')
    if unver:
        print(f'  -> 结论应带 {unver} 条明确限定条件发布，而不是作为无条件结论。')
    return unver

print('示例：一个个体随机化实验声称「新推荐位提升人均时长 3.2%」')
print()
n_unver = causal_checklist(
    '新推荐位提升人均时长 3.2%',
    'rct',
    {
        '随机化实现正确':        (True,  'SRM 检验 p=0.41，分桶哈希已审计'),
        'SUTVA/无干扰':          (False, '产品有关注流，未做集群随机化对照'),
        '结果指标口径 = 决策口径': (True,  '人均时长即目标指标'),
        '外部效度':              (False, '仅在活跃用户分层放量，未覆盖低活跃'),
    })
print()
print(f'两条未验证各自对应本课一个模块：干扰 -> 模块 05；外部效度 -> 模块 01/03。')
assert n_unver == 2

print()
print('工程含义：')
print('  · 这份清单的输出不该是「通过/不通过」，而应是**结论的限定条件**。')
print('  · 两条 TODO 里更危险的是干扰：它不会让实验失败，只会让结论适用范围与')
print('    你以为的不同（模块 05 会量出 1.00 vs 2.00 的差距）。')"""),
]
