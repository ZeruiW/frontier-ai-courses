# -*- coding: utf-8 -*-
"""C52 模块 00 · 课程总览与环境。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, md, code

META = [
    ("前置知识", "Python/numpy；C38（框架与加速）与 C50（HF 生态）有帮助但不必需"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'),
    ("课程模块", "6 个模块 · 纯 numpy 模拟框架语义 + 真实命令/文档作对照"),
    ("预计时长", "总览 25 分钟"),
]

SECTIONS = [
    ("what", "这门课讲什么", "".join([
        P("欢迎来到 <strong>工业研究工程实务</strong>。这门课收拢的是一批<strong>没有归属、却在工业界天天要用</strong>的技能——它们不属于任何一个「算法方向」，所以在课程体系里总是被漏掉，但在工作里几乎每周都会遇到。"),
        TABLE(["能力", "为什么被漏掉", "工作里什么时候需要"], [
            ["<strong>TensorFlow / Keras 的心智模型</strong>", "整个生态已经 PyTorch 化，教材也是", "接手遗留系统；对接 TF 栈的团队；读 2019 年前的代码与论文实现"],
            ["<strong>跨框架迁移与权重对齐</strong>", "「换个框架重训一遍」听起来简单，实际全是坑", "复现论文（作者用 TF、你用 PyTorch）；把研究模型交给用别的栈的团队"],
            ["<strong>模型导出与推理运行时</strong>", "研究不关心导出，部署课又假设你会", "模型要上边缘设备/移动端/嵌入式；要接 TensorRT/CoreML/TFLite"],
            ["<strong>真机 GPU 工作流</strong>", "云上「有卡就能跑」，直到出问题", "OOM、CUDA 版本地狱、性能远低于预期、多卡拓扑问题"],
            ["<strong>专利与研究产出</strong>", "学术课只讲论文，不讲专利", "企业研究院几乎都有专利指标；开源合规是法务红线"],
        ]),
        DUAL(
            "这五项的共同点是：<strong>它们都在「算法之外、产品之前」的那段</strong>。你不会因为它们写出更好的论文，但会因为它们<em>把一个模型真正交出去</em>——交给另一个团队、交给一台没有网络的设备、交给专利审查员。<em>而「交出去」恰恰是工业研究与学术研究最本质的区别。</em>",
            "本课的另一个动机是<strong>直面 JD</strong>。「Proficiency with deep learning frameworks such as TensorFlow, PyTorch, or JAX」——注意 TensorFlow 排在第一位，因为大量企业的生产栈仍是 TF；「Strong understanding of distributed computing and GPU acceleration using CUDA」——这要求的不只是「知道 CUDA 是什么」，而是能诊断一台真机上的问题；「Contribute to research papers, patents, and open-source projects」——专利是明确写出来的。<em>这些条目在全谱课程里此前都没有对应的落点。</em>",
        ),
        CALLOUT("intuition", "学完你应当能回答这类问题：<strong><code>tf.function</code> 与 <code>torch.compile</code> 的语义差别在哪、为什么前者会「重追踪」？把 TF 的权重搬到 PyTorch 时，哪些层的形状/顺序需要转置、哪些 eps 默认值不同？ONNX 导出时「动态轴」没设会怎样、算子不支持时有几条出路？<code>nvidia-smi</code> 里的 utilization 为什么不代表「跑满了」？一个想法要满足什么条件才可能获得专利、交底书该写什么？Apache-2.0 与 GPL 混在一个仓库里会发生什么？</strong>"),
    ])),
    ("map", "课程地图：把模型交出去的五道关", "".join([
        ASCII("""起点：你在 PyTorch 里训好了一个模型，它在你的开发机上跑得很好。

  模块 01  TensorFlow / Keras 心智模型
     │      静态图 vs 动态图 / tf.function 的追踪 / Keras 三种 API /
     │      与 PyTorch 的逐概念对照表
     ▼      「接手一个 TF 项目时，怎么快速读懂它」
  模块 02  框架迁移与权重对齐
     │      参数命名与内存布局差异 / conv 与 RNN 的权重转置 /
     │      LayerNorm 的 eps 与 BN 的动量 / **数值等价的验证方法学**
     ▼      「把权重搬过去，并证明它真的等价」
  模块 03  模型导出与推理运行时
     │      ONNX 图与 opset / 动态轴 / 算子不支持的四条出路 /
     │      TensorRT / CoreML / TFLite / 导出后的精度对拍
     ▼      「交给一个不认识 Python 的运行时」
  模块 04  真机 GPU 工作流
     │      nvidia-smi 的每个字段 / CUDA 版本矩阵 / OOM 的五种成因 /
     │      profiler 的读法 / 无 NVIDIA 卡时怎么准备
     ▼      「在真机上诊断，而不是猜」
  模块 05  研究产出与知识产权
            专利的可专利性三要件 / 权利要求怎么写 / 交底书 /
            专利与论文的时序 / 开源许可与合规 / 会议演讲

终点：你能把一个模型（以及它背后的想法）交给任何一个下游——
      另一个框架、另一个运行时、另一台机器、或者专利局。""")
        ,
        TABLE(["模块", "核心机制", "notebook 里从零做什么"], [
            ["01 TF/Keras", "静态图追踪、Keras API 层次、逐概念对照", "<strong>用 numpy 实现一个 tracing 编译器</strong>（复现 retracing 与副作用陷阱）"],
            ["02 迁移对齐", "权重布局、命名映射、数值等价", "<strong>conv/GRU 权重转置</strong> + 逐层数值对拍 + 迁移 checklist"],
            ["03 导出", "计算图 IR、opset、动态轴、算子回退", "<strong>迷你 IR 与导出器</strong> + 形状推断 + 算子覆盖检查 + 量化对拍"],
            ["04 真机 GPU", "显存构成、CUDA 版本矩阵、profiler", "<strong>显存分解与 OOM 诊断器</strong> + 版本兼容检查 + 时间线分析"],
            ["05 产出与 IP", "可专利性、权利要求、许可传染性", "<strong>可专利性自检器</strong> + 权利要求结构校验 + <strong>许可兼容性矩阵</strong>"],
        ]),
        CALLOUT("warn", "本课与相邻课程的分界要说清楚，避免重复：<strong>C38（框架与加速）讲 autograd、torch.compile、JAX/XLA、混合精度的<em>原理</em>；C36 讲 GPU kernel 怎么写；C39 讲多机分布式；C27 讲量化算法；C48 讲部署与云原生；C40 讲研究方法论与论文写作</strong>。<em>本课只讲那些「跨过边界」时才会遇到的问题</em>——跨框架、跨运行时、跨到真实硬件、跨到法务与知识产权。"),
    ])),
    ("method", "方法论：用 numpy 复现框架语义 + 真实命令作对照", "".join([
        P("本课有一个尴尬的约束：它讲的东西<strong>本质上都需要真实环境</strong>——TensorFlow、ONNX Runtime、NVIDIA GPU、专利数据库。而本环境一个都没有。"),
        DUAL(
            "但和 C50 一样，这个约束其实指向了更好的学法。<strong>因为这些工具的困难几乎都不在「怎么调 API」，而在「它的语义与你以为的不一样」</strong>——<code>tf.function</code> 的重追踪、权重布局的转置、ONNX 的形状推断、CUDA 的版本矩阵、专利的可专利性判断。<em>这些语义全都可以用几十行 Python 精确复现</em>，而复现之后你对真实工具的理解会比「跑通一个 tutorial」深得多。",
            "所以本课沿用「<strong>迷你复现 + 真实对照</strong>」的两条腿：notebook 里用纯 numpy 写一个 tracing 编译器、一个权重映射器、一个迷你 IR 与导出器、一个显存计算器、一个许可兼容性求解器；讲解里紧跟真实的 <code>tf.function</code> 代码、<code>torch.onnx.export</code> 参数、<code>nvidia-smi</code> 输出、以及一份可直接用的交底书模板。<em>后者都是可原样复制到有环境的机器上使用的。</em>",
        ),
        P("三条贯穿全课的纪律："),
        UL([
            "<strong>数值对拍</strong>：任何「迁移」「导出」「优化」都必须给出<em>逐层的数值等价证明</em>，而不是「跑通了、输出看起来对」。模块 02/03 会把这套方法学写成可复用的函数。",
            "<strong>版本即环境</strong>：跨框架/跨运行时的问题里，有相当比例是版本问题（opset 版本、CUDA/driver 矩阵、算子在某版本才支持）。<em>凡是报告问题，必须同时报告版本三元组</em>。",
            "<strong>边界要显式</strong>：交出去的东西必须附带「它在什么条件下成立」——支持的输入形状范围、精度损失、依赖的运行时版本。<em>不写清边界的交付，等于把问题推给下游。</em>",
        ]),
        CALLOUT("intuition", "这三条其实是同一件事的三个侧面：<strong>「交出去」意味着你不再控制运行环境，所以必须用「可验证的断言」代替「我这边是好的」</strong>。数值对拍是对正确性的断言、版本三元组是对环境的断言、边界说明是对适用范围的断言。<em>工业研究工程的成熟度，很大程度上就体现在这三类断言写得有多具体。</em>"),
    ])),
    ("boundary", "边界：这门课不讲什么，以及怎么用它", "".join([
        P("把边界画清楚，你才知道遇到问题时该翻哪一门课。<strong>本课与相邻课程的分工是「层次」而不是「主题」</strong>——同一个词（比如「量化」「显存」「编译」）在不同课里指的是不同层次的问题。"),
        TABLE(["问题", "本课讲的层次", "去哪门课看更深的层次"], [
            ["<strong>编译与图</strong>", "追踪语义、重追踪、图 IR 的<em>约束</em>", "C38（autograd 与编译器内部）、C36（kernel 融合怎么做）"],
            ["<strong>量化</strong>", "导出时的精度降级<em>怎么验证</em>、容差怎么设", "C27（量化算法本身：GPTQ/AWQ/SmoothQuant）"],
            ["<strong>推理加速</strong>", "选哪个运行时、有什么<em>约束</em>、怎么发现静默回退", "C24（引擎内部：PagedAttention、continuous batching）"],
            ["<strong>显存</strong>", "怎么<em>算</em>、OOM 怎么按成本诊断", "C39（ZeRO/FSDP 的分片机制）、C36（内存层级）"],
            ["<strong>部署</strong>", "把模型交给运行时的那一步", "C48（容器、K8s、扩缩容、成本）"],
            ["<strong>HuggingFace</strong>", "—（本课不讲）", "C50（Auto* / Trainer / PEFT / accelerate）"],
        ]),
        DUAL(
            "换个说法：<strong>其它课程讲「怎么把某件事做好」，本课讲「怎么把做好的东西<em>交出去</em>，并证明交出去之后它还是对的」</strong>。这是一个被系统性低估的技能——因为它在论文里不出现、在教程里不出现，<em>只在「上线前一周发现导不出去」的时候突然变成最重要的事</em>。",
            "也正因为如此，<strong>本课的五个模块彼此独立，更像一本按问题组织的手册而不是一条学习路径</strong>。建议的用法是：<em>先通读一遍（约两小时），建立「遇到这类问题时该想到什么」的索引；真正遇到问题时再回来精读对应模块并跑 notebook</em>。第二次读的收获通常远大于第一次——因为那时你有一个具体的、正在痛的问题。",
        ),
        CALLOUT("intuition", "还有一类内容本课<strong>刻意不覆盖</strong>：具体框架 API 的用法细节。<em>原因是 API 三年就换一茬，而语义不会</em>——<code>tf.function</code> 的参数名会变、<code>torch.onnx.export</code> 正在换实现路径、TensorRT 每个大版本都调整接口。<strong>但「Python 只在追踪时执行一次」「不设动态轴就被写死」「优化器状态是参数的 6 倍」这些不会变</strong>。所以本课把篇幅花在语义与账本上，把 API 放进每个模块末尾的 🧪 胶囊里——<em>胶囊会过时，正文不会</em>。"),
    ])),
    ("env", "环境与运行", "".join([
        P("本课全程 <strong>纯 numpy + 标准库、CPU 可跑、不联网</strong>。不需要 TensorFlow、ONNX、CUDA 或任何专利数据库。所有 notebook 在 CPU 上实跑验证、assert 0 失败。"),
        CODE("""pip install -r requirements.txt      # numpy / pandas / jupyterlab / ipykernel
jupyter lab                          # 打开 00_setup/00_environment_check.ipynb"""),
        TABLE(["你需要", "本课怎么处理"], [
            ["TensorFlow / Keras", "用 numpy 实现一个 <strong>tracing 编译器</strong>，复现 <code>tf.function</code> 的追踪、缓存与重追踪语义"],
            ["PyTorch", "用 numpy 定义等价的层，做<strong>逐层数值对拍</strong>"],
            ["ONNX / ONNX Runtime", "手写一个<strong>迷你 IR</strong>（节点/边/形状推断/opset 版本），并实现导出与算子覆盖检查"],
            ["NVIDIA GPU", "用<strong>参数化的显存模型与 profiler 时间线模拟器</strong>；真实 <code>nvidia-smi</code> 输出作对照解读"],
            ["专利数据库", "用一套<strong>可专利性自检规则</strong>与权利要求结构校验；附真实的交底书模板"],
            ["法务意见", "用<strong>许可兼容性矩阵</strong>做机械判断；明确标注「这不是法律意见」"],
        ]),
        CALLOUT("danger", "<p>关于模块 05 的一个必要声明：<strong>本课关于专利与开源许可的内容是工程视角的实用指南，不是法律意见</strong>。可专利性的最终判断由专利审查员做出，许可合规的最终判断由法务做出。<em>本课的目标是让你能：①识别出「这可能值得申请专利」；②写出一份质量合格的交底书，让专利代理人少问你三轮问题；③在把某个开源库引入项目前，判断出「这需要法务看一眼」</em>。<strong>能准确识别「什么时候需要专业意见」，本身就是这项能力的主要价值。</strong></p>", "这不是法律意见"),
        P("最后一句：本课的五个模块<strong>彼此独立</strong>，可以按需单独读。如果你现在正接手一个 TF 项目，直接读 01+02；如果要把模型上边缘设备，读 03；如果在调 GPU 问题，读 04；如果被要求写专利交底书，读 05。<em>它更像一本按问题组织的手册，而不是一条必须顺着走的学习路径。</em>"),
    ])),
]

NB = [
    md("""# 00 · 环境自检与「三条纪律」热身

本课全程 **纯 numpy + 标准库、CPU、不联网**。用 numpy 复现框架/运行时/硬件的**语义**——
因为这些工具的困难几乎都不在「怎么调 API」，而在「它的语义与你以为的不一样」。

这个 notebook 做三件事：① 环境自检；② 用三个最小例子体会本课的三条纪律
（**数值对拍 / 版本即环境 / 边界要显式**）；③ 建立贯穿全课的工具函数。"""),
    md("""## 1 · 环境自检"""),
    code("""import sys, platform, math, json, itertools, collections
print('Python', sys.version.split()[0], '|', platform.system(), platform.machine())
import numpy as np; print('numpy', np.__version__)
for name in ['torch', 'tensorflow', 'onnx', 'onnxruntime']:
    try:
        m = __import__(name); print(f'  {name:<12s} {getattr(m, "__version__", "?")} (有则更好)')
    except ImportError:
        print(f'  {name:<12s} 未安装 -> 走 numpy 复现路径')
print('\\n环境就绪 ✅  —— 本课不需要 TensorFlow / ONNX / CUDA / 联网')"""),
    md("""## 2 · 纪律一：数值对拍 —— 「跑通了」不等于「对了」

跨框架迁移、图导出、量化优化，三者的共同失败模式是：**代码不报错、输出形状也对，但数值错了**。
所以本课的每一次「变换」都要给出**逐层的数值等价证明**。

先把这套方法学封装成可复用的函数。"""),
    code("""def allclose_report(a, b, rtol=1e-5, atol=1e-6, name=''):
    '''逐张量对拍：不只给 True/False，还给出**最大绝对/相对误差与位置** ——
       因为「差在哪里」比「差不差」更有诊断价值。'''
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        return {'name': name, 'ok': False, 'reason': f'shape {a.shape} vs {b.shape}'}
    diff = np.abs(a - b)
    denom = np.maximum(np.abs(b), 1e-12)
    rel = diff / denom
    idx = int(np.argmax(diff))
    return {'name': name, 'ok': bool(np.allclose(a, b, rtol=rtol, atol=atol)),
            'max_abs': float(diff.max()), 'max_rel': float(rel.max()),
            'at': np.unravel_index(idx, a.shape), 'mean_abs': float(diff.mean())}

def layerwise_check(ref_acts, new_acts, rtol=1e-5, atol=1e-6):
    '''**逐层**对拍：只比最终输出会掩盖「前面错了、后面碰巧抵消」的情况。
       返回第一个不匹配的层 —— 这才是定位问题的正确方式。'''
    rows = []
    for k in ref_acts:
        r = allclose_report(ref_acts[k], new_acts.get(k, np.array([])), rtol, atol, name=k)
        rows.append(r)
        if not r['ok']:
            break                      # 第一个出错的层就是问题所在，后面的都是它的后果
    return rows

rng = np.random.default_rng(0)
x = rng.normal(size=(4, 8))
acts_ref = {'l1': x @ np.ones((8, 8)), 'l2': np.tanh(x @ np.ones((8, 8)))}
acts_ok = {'l1': acts_ref['l1'].copy(), 'l2': acts_ref['l2'].copy()}
acts_bad = {'l1': acts_ref['l1'] + 1e-3, 'l2': acts_ref['l2'].copy()}

for name, acts in [('完全一致', acts_ok), ('第一层就错', acts_bad)]:
    rows = layerwise_check(acts_ref, acts)
    status = '✅ 全部通过' if all(r['ok'] for r in rows) else f'❌ 首个失配: {rows[-1]["name"]}'
    print(f'{name:<12s} {status}  (检查了 {len(rows)} 层)')
    if not rows[-1]['ok']:
        print(f'    max_abs={rows[-1]["max_abs"]:.2e} at {rows[-1]["at"]}')

assert all(r['ok'] for r in layerwise_check(acts_ref, acts_ok))
assert not layerwise_check(acts_ref, acts_bad)[-1]['ok']
print('\\n✅ 逐层对拍就位。**只比最终输出**会掩盖「前面错了后面抵消」的情况 ——')
print('   而那种情况在换了输入分布之后就会暴露（且极难定位）。')"""),
    md("""### 容差怎么定：不同精度的合理阈值

「对拍失败」常常只是容差设错了。**不同 dtype 的机器精度差三个数量级。**"""),
    code("""EPS = {'float64': 2.2e-16, 'float32': 1.2e-7, 'float16': 9.8e-4, 'bfloat16': 7.8e-3}

def suggest_tolerance(dtype, depth, safety=10.0):
    '''经验法则：误差随层数近似按 sqrt(depth) 累积（随机游走），再留一个安全系数。'''
    eps = EPS[dtype]
    return {'rtol': safety * eps * math.sqrt(max(1, depth)),
            'atol': safety * eps * math.sqrt(max(1, depth))}

print(f"{'dtype':<10s} {'1 层':>12s} {'12 层':>12s} {'96 层':>12s}")
for dt in EPS:
    ts = [suggest_tolerance(dt, d)['rtol'] for d in (1, 12, 96)]
    print(f'{dt:<10s} {ts[0]:>12.2e} {ts[1]:>12.2e} {ts[2]:>12.2e}')

t32 = suggest_tolerance('float32', 12)['rtol']
t16 = suggest_tolerance('float16', 12)['rtol']
assert t16 > t32 * 100, 'fp16 的合理容差比 fp32 大两个数量级以上'
assert suggest_tolerance('float32', 96)['rtol'] > suggest_tolerance('float32', 1)['rtol']
print('\\n✅ 两条推论：')
print('   ① 用 fp32 的容差去对拍 fp16 的导出结果，必然「失败」—— 但那不是 bug。')
print('   ② 深层模型的累积误差更大 —— 所以**逐层对拍**比只看最终输出更可靠：')
print('      前几层的容差可以很紧，问题会在它真正发生的那一层暴露。')"""),
    md("""## 3 · 纪律二：版本即环境

跨框架 / 跨运行时的问题里，很大一部分是**版本问题**：某个算子在 opset 13 才支持、
CUDA runtime 必须 ≤ driver 支持的版本、某个 API 在 2.x 改了默认值。

**凡是报告一个问题，必须同时报告版本三元组。**"""),
    code("""def env_fingerprint(**versions):
    '''把环境压成一个可比较、可写进日志的指纹。'''
    items = sorted(versions.items())
    s = ';'.join(f'{k}={v}' for k, v in items)
    return {'string': s, 'dict': dict(items)}

def diff_env(a, b):
    '''两个环境的差异 —— 排查「在我这好使」时的第一步。'''
    keys = sorted(set(a['dict']) | set(b['dict']))
    return [(k, a['dict'].get(k, '—'), b['dict'].get(k, '—'))
            for k in keys if a['dict'].get(k) != b['dict'].get(k)]

dev = env_fingerprint(python='3.11', torch='2.4.1', onnx='1.16.0', opset='17',
                      cuda_runtime='12.1', driver='550.54')
prod = env_fingerprint(python='3.11', torch='2.4.1', onnx='1.14.0', opset='14',
                       cuda_runtime='12.1', driver='525.85')
print('开发环境:', dev['string'])
print('生产环境:', prod['string'])
print('\\n差异:')
for k, a, b in diff_env(dev, prod):
    print(f'  {k:<14s} dev={a:<10s} prod={b}')

d = {k: (a, b) for k, a, b in diff_env(dev, prod)}
assert 'opset' in d and 'driver' in d
assert not diff_env(dev, dev), '同一环境不应有差异'
print('\\n✅ 这三行差异就是「在我这好使」类问题的头号嫌疑人：')
print('   · opset 17 -> 14：某些算子在低 opset 不存在（模块 03）')
print('   · driver 550 -> 525：CUDA runtime 12.1 可能超出 525 的支持上限（模块 04）')"""),
    md("""## 4 · 纪律三：边界要显式

交出去的模型必须附带「它在什么条件下成立」。**不写清边界，等于把问题推给下游。**"""),
    code("""class Contract:
    '''交付契约：把「这个模型在什么条件下有效」写成可检查的对象。'''
    def __init__(self, name, input_shapes, dtype, opset=None, max_batch=None,
                 max_seq=None, tolerance=None, notes=()):
        self.name, self.input_shapes, self.dtype = name, input_shapes, dtype
        self.opset, self.max_batch, self.max_seq = opset, max_batch, max_seq
        self.tolerance, self.notes = tolerance or {}, list(notes)

    def validate(self, batch, seq, dtype):
        errs = []
        if self.max_batch is not None and batch > self.max_batch:
            errs.append(f'batch {batch} > 支持上限 {self.max_batch}')
        if self.max_seq is not None and seq > self.max_seq:
            errs.append(f'seq_len {seq} > 支持上限 {self.max_seq}')
        if dtype != self.dtype:
            errs.append(f'dtype {dtype} != 导出时的 {self.dtype}')
        return (not errs), errs

    def render(self):
        lines = [f'# 交付契约: {self.name}', '',
                 f'- 输入形状: {self.input_shapes}',
                 f'- dtype: {self.dtype}',
                 f'- opset: {self.opset}',
                 f'- 支持的最大 batch: {self.max_batch}',
                 f'- 支持的最大序列长: {self.max_seq}',
                 f'- 与参考实现的容差: {self.tolerance}']
        if self.notes:
            lines += ['- 已知限制:'] + [f'    · {n}' for n in self.notes]
        return '\\n'.join(lines)

c = Contract('text-classifier-v3',
             input_shapes={'input_ids': ['batch', 'seq'], 'attention_mask': ['batch', 'seq']},
             dtype='float16', opset=17, max_batch=64, max_seq=512,
             tolerance={'rtol': 1e-2, 'atol': 1e-2},
             notes=['seq_len 必须是 8 的倍数（TensorRT 的对齐要求）',
                    'batch=1 时走另一条 kernel，延迟不成比例',
                    'fp16 下极端输入（|x|>1e4）可能溢出'])
print(c.render())

ok, errs = c.validate(batch=128, seq=1024, dtype='float32')
print(f'\\n用 batch=128, seq=1024, fp32 调用 -> 合法? {ok}')
for e in errs: print(f'  ❌ {e}')
assert not ok and len(errs) == 3
ok2, _ = c.validate(batch=32, seq=256, dtype='float16')
assert ok2
print('\\n✅ 把「适用范围」写成可检查的对象，而不是 README 里的一段话 ——')
print('   前者会在越界时报错，后者只会在事故复盘时被翻出来。')"""),
    md("""## 5 · ✏️ 练习：环境兼容性判断

实现 `cuda_compatible(driver_version, cuda_runtime)`：NVIDIA 的规则是
**driver 必须 ≥ 对应 CUDA runtime 的最低 driver 版本**（向后兼容，但不向前）。
用下表判断，返回 `(是否兼容, 说明字符串)`。

| CUDA runtime | 最低 driver |
|---|---|
| 11.8 | 520.61 |
| 12.1 | 530.30 |
| 12.4 | 550.54 |"""),
    code("""MIN_DRIVER = {'11.8': 520.61, '12.1': 530.30, '12.4': 550.54}

def cuda_compatible(driver_version, cuda_runtime):
    # TODO: 查表得最低 driver；driver_version >= 它 -> (True, '兼容')
    #       否则 (False, f'需要 driver >= X，当前 Y')
    #       未知的 cuda_runtime -> (False, 'unknown CUDA runtime ...')
    raise NotImplementedError"""),
    code("""# —— 练习自测 ——
ok, msg = cuda_compatible(550.54, '12.1')
assert ok, msg
ok2, msg2 = cuda_compatible(525.85, '12.1')
assert not ok2 and '530.3' in msg2, msg2
assert cuda_compatible(520.61, '11.8')[0], '刚好等于最低版本应兼容'
assert not cuda_compatible(510.0, '11.8')[0]
assert not cuda_compatible(999.0, '13.0')[0], '未知 runtime 应保守判为不兼容'
for drv, rt in [(550.54, '12.4'), (530.30, '12.4'), (525.85, '12.1')]:
    ok_, m_ = cuda_compatible(drv, rt)
    print(f'driver {drv} + CUDA {rt} -> {"✅" if ok_ else "❌ " + m_}')
print('\\n✅ 练习通过：这就是「镜像里的 CUDA 版本必须 ≤ 宿主 driver 支持的版本」')
print('   （C48 模块 01 提过这个坑，模块 04 会把整张矩阵讲清楚）')"""),
    md("""---
### 📖 参考答案"""),
    code("""def cuda_compatible(driver_version, cuda_runtime):
    if cuda_runtime not in MIN_DRIVER:
        return False, f'unknown CUDA runtime {cuda_runtime}'
    need = MIN_DRIVER[cuda_runtime]
    if driver_version >= need:
        return True, '兼容'
    return False, f'需要 driver >= {need}，当前 {driver_version}'"""),
    md("""## 6 · 🧪 胶囊：五个模块各自的「交付物」

预告本课每个模块的产出。它们都是可以直接放进你项目工具库的东西。"""),
    code("""DELIVERABLES = [
    ('模块 01', 'tf.function 语义复现器', '理解重追踪与副作用陷阱；读懂 TF 代码'),
    ('模块 02', '权重映射表 + 逐层对拍脚本', '把任意框架的权重搬过去并**证明**等价'),
    ('模块 03', '导出前检查器（算子覆盖 + 动态轴 + 契约）', '避免「导出成功但线上形状一变就崩」'),
    ('模块 04', '显存分解器 + OOM 诊断树 + 版本矩阵检查', '把「跑不起来」变成「缺 X GB，因为 Y」'),
    ('模块 05', '可专利性自检 + 交底书模板 + 许可兼容矩阵', '识别值得申请的想法；避免许可地雷'),
]
print(f"{'模块':<8s} {'交付物':<34s} {'解决什么'}")
for m, d, w in DELIVERABLES:
    print(f'{m:<8s} {d:<34s} {w}')
assert len(DELIVERABLES) == 5
print('\\n✅ 五个交付物都是**可以直接放进项目工具库**的东西 ——')
print('   这门课的价值不在「知道有这回事」，而在「下次遇到时有现成的工具」。')"""),
    md("""✅ 检查全部通过即环境就绪、方法论到位。

**本课的契约**：每个模块都会 ① 用 numpy **复现**目标工具的关键语义（带 assert），
② 给出**可原样使用**的真实命令/代码/模板，③ 产出一个**可复用的检查器或清单**。

**接下来五个模块**：01 TensorFlow/Keras 心智模型 → 02 框架迁移与权重对齐 →
03 模型导出与推理运行时 → 04 真机 GPU 工作流 → 05 研究产出与知识产权。

**它们彼此独立，可以按需单独读。** 下一站：**模块 01 · TensorFlow / Keras 心智模型**。"""),
]
