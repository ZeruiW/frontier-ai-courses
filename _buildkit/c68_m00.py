# -*- coding: utf-8 -*-
"""C68 模块 00 · 课程总览与环境（Eval 基础设施与线上监控）。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "读过 C66（agent 评测）或 C67（judge）任一门的前两个模块；"
                 "知道「哈希」「并发」「CI」三个词的含义即可，实现全部从零写"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 00_environment_check.ipynb'
                       '（环境自检 / 120 行的最小 eval 基础设施：spec + runner + store + report / '
                       '幂等性验证 / 「一次性脚本」vs「基础设施」的成本模型 / 四层架构自检器）'),
    ("核心参考", "UK AISI, <em>inspect_ai</em> 框架设计（task/solver/scorer 三件套）· "
                 "OpenAI Evals 的 registry 设计 · "
                 "Sculley et al., <em>Hidden Technical Debt in Machine Learning Systems</em>（NeurIPS 2015）· "
                 "本课程 C66 模块 05（harness 可复现性）· C37（MLOps）· C43（数据工程）"),
    ("预计时长", "读 45 分钟 + 跑 35 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("why-infra", "从「一次性脚本」到「基础设施」：分界线在哪", "".join([
        P("C66 与 C67 回答的是「评什么、怎么算才对」。这门课回答下一个问题："
          "<strong>当这套评测要被跑几百次、被十个人跑、被跑一年，它需要长成什么样。</strong>"),
        P("先划清一条线：<strong>并不是所有评测都需要基础设施。</strong>"
          "一次性的探索实验，用一个脚本跑完就删掉，是完全正确的做法。"
          "值得投入基础设施的判据只有一个——<strong>这套评测会不会被重复跑</strong>。"),
        TABLE(["场景", "会被跑几次", "一次性脚本够不够", "真正的成本在哪"], [
            ["探索一个新想法", "1–3 次", "<strong>够</strong>", "写基础设施的时间超过它节省的时间"],
            ["模型选型", "10–30 次（几个候选 × 几个配置）", "勉强", "手工记录配置、事后拼不回「那次是怎么跑的」"],
            ["<strong>CI 回归门禁</strong>", "<strong>每次提交</strong>", "<strong>完全不够</strong>", "误报会让团队关掉门禁；漏报会让退化上线"],
            ["<strong>线上质量监控</strong>", "<strong>持续</strong>", "完全不够", "离线指标与线上表现脱节而没人发现"],
            ["长期能力追踪", "每周/每月，持续一年以上", "完全不够", "半年后没人说得清历史数字是怎么来的"],
        ]),
        DUAL(
            "一个判断标准比「跑几次」更准：<strong>「如果这次结果和上次不一样，你能在十分钟内说清楚为什么吗？」</strong>"
            "答不上来，就说明你需要基础设施——不是为了跑得更快，"
            "<em>而是为了让「结果变了」这件事变得可解释</em>。"
            "C66 模块 05 的 运行指纹已经埋下了这个种子，本课把它长成完整的系统。",
            "更形式化地说，评测基础设施要保证三个性质："
            "<strong>① 确定性</strong>（同样的输入与配置产生同样的输出，或至少产生<em>同分布</em>的输出）；"
            "<strong>② 可归因性</strong>（任何两次运行的差异，都能被归因到某个显式记录的配置项）；"
            "<strong>③ 幂等性</strong>（重跑不会破坏已有结果，中断后能续跑）。"
            "<em>这三条是本课全部工程决策的来源</em>——"
            "缓存设计、结果存储的主键、CI 门禁的阈值，都是在服务这三条。",
        ),
        CALLOUT("intuition", "反过来说一句同样重要的话：<strong>不要在探索期就上基础设施。</strong>"
                             "评测的定义在早期变化极快（任务集在改、判分器在改、指标口径在改），"
                             "<em>过早固化的 schema 会把这些变化变成迁移成本</em>。"
                             "<strong>正确的时机是：当你第三次手工重复同一件事的时候。</strong>"),
    ])),

    # ============================================================== 2
    ("four-layers", "四层架构：spec / runner / store / report", "".join([
        P("几乎所有成熟的评测系统都会收敛到同一个四层结构。"
          "把它画出来，本课后面五个模块就是这四层各自的展开。"),
        ASCII("""
   ┌──────────────────────────────────────────────────────────────┐
   │ ④ REPORT   报告层                                            │
   │    切片、对比、置信区间、评测卡、趋势图                        │
   │    → 03 模块（分析）· 04 模块（CI 门禁）· 05 模块（线上看板）  │
   ├──────────────────────────────────────────────────────────────┤
   │ ③ STORE    结果层                                            │
   │    每条结果一行；主键 = (run_id, task_id, attempt)            │
   │    幂等写入、可续跑、可回溯                                    │
   │    → 03 模块                                                 │
   ├──────────────────────────────────────────────────────────────┤
   │ ② RUNNER   执行层                                            │
   │    并发、限流、重试、超时、缓存、断点续跑、预算熔断             │
   │    → 02 模块                                                 │
   ├──────────────────────────────────────────────────────────────┤
   │ ① SPEC     声明层                                            │
   │    任务集是什么 · 怎么跑 · 怎么判分 · 版本与哈希               │
   │    **纯数据，不含执行逻辑**                                   │
   │    → 01 模块                                                 │
   └──────────────────────────────────────────────────────────────┘
"""),
        TABLE(["层", "职责", "关键约束", "做错的后果"], [
            ["<strong>① SPEC</strong>", "声明「评什么、怎么判」", "<strong>纯数据、可序列化、可哈希</strong>；不含执行逻辑", "配置散落在代码里 → 无法比较两次运行的差异"],
            ["<strong>② RUNNER</strong>", "把 spec 变成结果", "<strong>幂等、可中断续跑</strong>；所有失败可分类", "跑一半崩了要全部重来；成本失控"],
            ["<strong>③ STORE</strong>", "存结果", "<strong>只追加、主键唯一</strong>；结果不可变", "重跑覆盖了历史；无法回答「上周是多少」"],
            ["<strong>④ REPORT</strong>", "把结果变成结论", "<strong>与 C66/C67 的统计规范一致</strong>", "报告出错误的数字（本课不重复讲，直接复用前两课）"],
        ]),
        CALLOUT("warn", "四层里最容易被合并的是 ① 和 ②——"
                        "「反正都是我写的代码，配置直接写在脚本里就好了」。"
                        "<strong>这是所有后续问题的根源</strong>："
                        "配置写在代码里，就无法被哈希、无法被比较、无法回答"
                        "「这两次运行到底差在哪」。"
                        "<em>把 spec 抽成纯数据，是本课投入产出比最高的一个结构决策</em>——"
                        "它直接让 C66 模块 05 的运行指纹变成可能。"),
    ])),

    # ============================================================== 3
    ("idempotence", "三个性质：确定性、可归因性、幂等性", "".join([
        P("第 1 节的 DUAL 里提到了三个性质。它们不是抽象的工程美学，"
          "而是<strong>每一条都能翻译成具体的代码约束</strong>。"),
        H3("确定性：不是「结果一样」，而是「差异可解释」"),
        P("LLM 评测天然带随机性（采样温度、环境抖动、judge 的不稳定），"
          "所以「两次跑出同样的数字」通常做不到。"
          "<strong>可实现的目标是：把随机性<em>收拢到少数几个显式的来源</em>，"
          "并让这些来源可控（seed）或可测（重复运行的方差）。</strong>"),
        TABLE(["随机源", "能不能消除", "怎么处理"], [
            ["模型采样", "能（temperature=0）或部分能（固定 seed，若 API 支持）", "报告里必须写明温度与 seed"],
            ["任务顺序 / 并发调度", "<strong>能</strong>", "结果按 task_id 排序后再聚合，不依赖完成顺序"],
            ["外部环境（网络、容器、时钟）", "部分能", "录制回放；容器 digest；把时间相关的输入固定"],
            ["judge / 用户模拟器", "部分能", "固定模型与温度；swap 双跑（C67-02）"],
        ]),
        H3("可归因性：任何差异都能指向一个配置项"),
        P("这条的实现就是 <strong>C66 模块 05 的运行指纹</strong>，"
          "本课把它从「一个应该做的事」变成「架构上必然做到的事」——"
          "<em>因为 spec 是纯数据，指纹就是它的哈希，不需要人去维护一份清单</em>。"),
        H3("幂等性：重跑不破坏，中断能续"),
        MATH(r"\text{run}(\text{spec}, \text{store}) \circ \text{run}(\text{spec}, \text{store}) = \text{run}(\text{spec}, \text{store})"),
        P("实现方式很简单，但必须一开始就做对：<strong>每条结果的主键是 "
          "<code>(run_id, task_id, attempt)</code>，写入前先查在不在，在就跳过。</strong>"
          "这一条同时解决了三个问题——中断续跑、部分重跑、以及「不小心跑了两次」。"),
        CALLOUT("intuition", "幂等性带来一个不那么明显但很重要的好处：<strong>它让「增量扩样本」变成一个安全操作。</strong>"
                             "任务集从 300 条加到 500 条时，你只需要用同一个 run_id 再跑一遍——"
                             "已完成的 300 条会被跳过，只跑新增的 200 条。"
                             "<em>没有幂等性的话，这个操作要么重跑全部（浪费），"
                             "要么手工挑出新增的（容易错）。</em>"),
    ])),

    # ============================================================== 4
    ("division", "与既有课程的分工", "".join([
        TABLE(["课程", "它讲什么", "本课的关系"], [
            ["<strong>C66</strong> · Agent 评测", "评什么、怎么判分、怎么算统计、成本与 运行指纹", "<strong>C66 给出「一次评测该怎么做对」，本课给出「怎么把它跑一千次」</strong>。C66 模块 05 的十项复现清单，在本课变成 spec 的字段"],
            ["<strong>C67</strong> · LLM Judge", "judge 的设计、偏差、元评测、排名、奖励模型", "<strong>C67 管 judge 的正确性，本课管 judge 的工程</strong>：调用、缓存、成本、以及把 C67 模块 03 的漂移哨兵接到线上告警（judge prompt 的版本管理本身在 C67 模块 01）"],
            ["<strong>C37</strong> · MLOps", "模型训练与部署的生命周期、实验追踪、模型注册", "有重叠但视角不同：C37 的中心是<em>模型</em>，本课的中心是<em>评测</em>。评测有自己的特殊性（判分器也是被评对象、指标本身会漂移）"],
            ["<strong>C43</strong> · 数据工程", "数据管道、版本化、血缘", "本课模块 01 的数据集版本化直接复用 C43 的思想，不重复推导；<strong>本课的新东西是「样本 ID 的稳定性」这个评测特有的问题</strong>"],
            ["<strong>C10</strong> · 测量科学", "标注、一致性、校准、A/B", "本课模块 05 的线上 A/B 与离线-在线相关性建立在 C10 之上"],
            ["<strong>C34</strong> · Agent 编排", "多智能体的生产化、可观测、部署", "轨迹埋点的实现在 C34；<strong>本课讲的是「埋下来的数据怎么变成评测与告警」</strong>"],
            ["<strong>C69</strong> · Agent 安全（同批新课）", "提示注入、工具供应链、沙箱与权限", "本课模块 05 的 guardrail 是「质量护栏」，C69 的是「安全护栏」——机制相似，触发条件不同"],
        ]),
        CALLOUT("intuition", "一句话记住这批新课的分工：<strong>C66 量 agent · C67 量判分器 · "
                             "C68 把评测变成基础设施 · C69 量攻击面。</strong>"
                             "本课处在链条的第三环——<em>它不产生新的评测方法，"
                             "而是让前两课的方法能被可靠地、重复地、便宜地执行。</em>"),
    ])),

    # ============================================================== 5
    ("env", "环境、依赖与本课的运行约定", "".join([
        P("本课<strong>全程 CPU、断网可跑、不需要任何 API key</strong>，而且比前两课更彻底——"
          "因为基础设施的正确性<em>本来就不该依赖真实模型</em>。"),
        UL([
            "<strong>被评的「模型」是一个可控的假函数</strong>：给定输入返回确定或带受控随机性的输出，"
            "并且可以人为注入失败（超时、限流、格式错误）。"
            "<em>这比真实 API 更适合验证 runner 的正确性——你可以精确控制第几次调用会失败。</em>",
            "<strong>存储是本地 JSONL / SQLite</strong>（标准库自带），"
            "所有幂等性、并发、续跑的逻辑都能在上面完整验证。",
            "<strong>真实接入</strong>（inspect-ai 的 task 定义、OpenTelemetry 埋点、"
            "CI 配置、Prometheus 告警规则）放在每个模块末尾的「🧪 真实工程胶囊」里。",
        ]),
        CODE("""pip install numpy jupyterlab ipykernel
jupyter lab      # 或直接在 Colab 里点每个 notebook 顶部的徽章"""),
        CALLOUT("warn", "本课的 notebook 会创建临时文件与目录（在 <code>./_eval_tmp/</code> 下）。"
                        "<strong>每个 notebook 开头都会清空这个目录</strong>，所以重复运行是安全的；"
                        "但如果你在那里放了自己的东西，请先移走。"
                        "<em>这个「先清空再开始」的约定本身也是一个基础设施惯例</em>——"
                        "它保证了 notebook 自己是幂等的。"),
    ])),

    # ============================================================== 6
    ("anti-patterns", "六个反模式：它们都不会报错", "".join([
        P("最后用一份反模式清单收尾。<strong>它们的共同点是不会抛异常</strong>——"
          "代码照跑，数字照出，只是那些数字不再意味着你以为的东西。"),
        TABLE(["反模式", "表面上", "实际后果", "本课哪里解决"], [
            ["<strong>配置写在代码里</strong>", "省事", "无法比较两次运行的差异；无法生成指纹", "01：spec 是纯数据"],
            ["<strong>就地修改任务集</strong>", "「就改一道坏题」", "<strong>所有历史分数一夜之间失去意义</strong>", "01：只增不改，发新版本"],
            ["<strong>用行号或哈希内容当样本 ID</strong>", "不用另外维护 ID", "改一个错别字，样本 ID 就变了，历史结果对不上", "01：稳定 ID"],
            ["<strong>缓存里不含运行指纹</strong>", "缓存命中率高", "<strong>改了 prompt 却读到旧结果</strong>——最隐蔽的一个", "02：缓存键设计"],
            ["<strong>失败样本直接跳过</strong>", "报告看起来干净", "分母变小，成功率虚高（与 C67-01 的解析失败同构）", "02：失败必须分类并计入"],
            ["<strong>CI 门禁阈值拍脑袋定</strong>", "「掉 2% 就报警」", "噪声不断误报 → 团队关掉门禁 → 门禁形同虚设", "04：用重复运行的方差定阈值"],
        ]),
        CALLOUT("danger", "第四条值得单独强调，因为它是本课里<strong>最贵、最难查</strong>的一个 bug："
                          "<strong>缓存键里如果不包含 judge prompt / 模型 ID / 采样参数的指纹，"
                          "那么你改了 prompt 之后再跑，会安静地读到旧结果</strong>。"
                          "<em>症状是「我明明改了 prompt，分数却一点没变」，"
                          "而很多人会把它误读成「这个改动没有效果」</em>。"
                          "<strong>规则：缓存键 = 输入内容哈希 + 完整运行指纹，缺一不可。</strong>"),
        P("这六条会在后面五个模块里被逐一解决。"
          "notebook 的最后一节给出一个自检器：把你现有的评测流程按这六条打分。"),
    ])),
    # ============================================================== 7
    ("who-owns", "谁来维护：基础设施的所有权与腐化", "".join([
        P("最后一节讲一个技术之外、但决定成败的问题：<strong>这套东西归谁管。</strong>"
          "评测基础设施有一个特殊的组织属性——<em>它服务所有人，因此很容易不属于任何人</em>。"),
        TABLE(["所有权模式", "怎么运作", "典型腐化方式", "适合什么阶段"], [
            ["<strong>无主</strong>", "谁需要谁改", "<strong>配置漂移</strong>：每个人加自己的分支逻辑，半年后没人说得清默认行为是什么", "只在最早期可接受"],
            ["<strong>兼职维护</strong>", "某个人「顺便」维护", "<strong>知识单点</strong>：那个人休假时没人能改；他离职时系统冻结", "小团队的现实选择"],
            ["<strong>平台化</strong>", "有专门的人/小组，其他人通过 spec 使用", "<strong>脱节</strong>：平台团队不知道使用者的真实需求，加的功能没人用", "评测成为多团队共享设施之后"],
            ["<strong>共享代码 + 明确 owner</strong>", "任何人可提 PR，但有明确的 review 责任人", "较慢，但腐化最少", "<strong>多数团队的推荐形态</strong>"],
        ]),
        DUAL(
            "腐化的具体形态几乎总是同一个：<strong>有人为了赶一次实验，"
            "在 runner 里加了一个「临时」的 if 分支，然后它永远留在了那里。</strong>"
            "<em>三个月后，没人知道这个分支在什么条件下触发，也没人敢删</em>——"
            "而它可能正在悄悄改变某些运行的行为。",
            "从架构的角度，防腐化的机制其实已经内置在本课的设计里了："
            "<strong>如果所有会影响结果的配置都必须进 spec，"
            "那么「在代码里加一个临时分支」这件事在结构上就是被禁止的</strong>——"
            "因为那个分支的行为不会进入指纹，"
            "<em>而 CI 里那条「同指纹的两次运行结果不该差太多」的检查会把它暴露出来</em>"
            "（模块 00 第 4 节的告警）。"
            "<strong>换句话说，「spec 是纯数据」这条设计不只是为了可比性，"
            "也是一条组织层面的防腐化约束。</strong>",
        ),
        H3("三条低成本的维护纪律"),
        UL([
            "<strong>任何新增的配置项必须有默认值，且默认值保持旧行为</strong>（模块 01）——"
            "<em>这让「加功能」不会破坏别人的历史数据</em>；",
            "<strong>runner 里不允许出现 <code>if os.environ.get(...)</code></strong>——"
            "环境变量是配置的暗门，它绕过了 spec，因此绕过了指纹；",
            "<strong>每季度跑一次「反模式自检」</strong>（本模块 notebook 第 6 节），"
            "<em>把腐化变成一个可以被看见的分数，而不是一种感觉</em>。",
        ]),
        CALLOUT("intuition", "一条判断基础设施是否健在的简单测试：<strong>随便找一个三个月前的运行结果，"
                             "问「我能不能今天原样复现它」。</strong>"
                             "<em>如果答案需要「问一下当时跑的人」，那么这套基础设施已经在腐化了</em>——"
                             "而这个测试只需要五分钟，值得每季度做一次。"),
    ])),
]

NB = [
    md("""# 00 · 课程总览与环境（最小 eval 基础设施 / 幂等性 / 成本模型 / 四层架构自检）

目标：用 120 行代码把四层架构完整跑一遍——spec、runner、store、report 各一层，
后面五个模块都是在这个骨架上把某一层做深。

本 notebook 你会亲手实现：
1. **环境自检与临时目录约定**
2. **四层骨架** —— spec（纯数据 + 哈希）· runner（幂等）· store（只追加）· report
3. **幂等性验证** —— 重跑不产生重复行、中断后能续跑、增量扩样本安全
4. **可归因性** —— 改一个配置项，指纹就变；指纹相同而结果不同 = 告警
5. **「一次性脚本」vs「基础设施」的成本模型** —— 跑几次之后开始回本
6. **六个反模式的自检器** —— 把你现有的流程打个分

> 心智模型：**基础设施要保证的不是「跑得更快」，而是三条性质——
> 确定性（差异可解释）、可归因性（差异指向配置项）、幂等性（重跑不破坏）。**"""),

    md("""## 0 · 环境自检与临时目录"""),

    code("""import sys, os, json, math, time, hashlib, shutil, sqlite3, random
from collections import Counter, defaultdict

import numpy as np

print('Python :', sys.version.split()[0])
print('numpy  :', np.__version__)

TMP = os.path.abspath('./_eval_tmp')
if os.path.exists(TMP):
    shutil.rmtree(TMP)                 # 先清空再开始 —— 让 notebook 自己是幂等的
os.makedirs(TMP, exist_ok=True)
print('临时目录:', TMP)
assert os.path.isdir(TMP) and not os.listdir(TMP)
print('\\n✅ 环境就绪：本课全部内容 CPU 可跑、断网可跑，不需要任何 API key。')"""),

    md("""## 1 · ① SPEC 层：纯数据，可哈希

关键约束：**spec 里不含任何执行逻辑**。它只描述「评什么、怎么跑、怎么判」，
因此可以被序列化、被哈希、被 diff。**指纹就是它的哈希** —— 不需要人去维护一份清单。"""),

    code("""def stable_hash(obj, n=8):
    \"\"\"对任意可 JSON 化的对象取稳定哈希。sort_keys 保证字段顺序不影响结果。\"\"\"
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:n]

SPEC = {
    'name': 'demo-qa',
    'dataset': {'id': 'qa-tasks', 'version': 'v1', 'sha': None},   # sha 稍后填
    'model': {'id': 'fake-model-a', 'temperature': 0.0, 'seed': 0},
    'scorer': {'kind': 'exact_match', 'version': 'v1'},
    'budget': {'max_attempts': 1, 'timeout_s': 5, 'retries': 2},
    'runner': {'concurrency': 4},
}

TASKS = [
    {'task_id': 'q001', 'input': '2+2', 'target': '4'},
    {'task_id': 'q002', 'input': '3*7', 'target': '21'},
    {'task_id': 'q003', 'input': '10-4', 'target': '6'},
    {'task_id': 'q004', 'input': '9/3',  'target': '3'},
    {'task_id': 'q005', 'input': '5+5',  'target': '10'},
]
SPEC['dataset']['sha'] = stable_hash(TASKS, 12)

def fingerprint(spec):
    return stable_hash(spec, 8)

fp = fingerprint(SPEC)
print('spec 指纹:', fp)
print('数据集 sha:', SPEC['dataset']['sha'])

# 字段顺序不影响哈希；改任何一个值都会改变哈希
reordered = {k: SPEC[k] for k in reversed(list(SPEC))}
assert fingerprint(reordered) == fp, '字段顺序不应影响指纹'
changed = json.loads(json.dumps(SPEC)); changed['model']['temperature'] = 0.7
assert fingerprint(changed) != fp, '改了运行指纹必须变'
print('\\n✅ spec 是纯数据 → 指纹是它的哈希，不需要人去维护一份「要记录哪些字段」的清单。')
print('   这就是 C66-05 的运行指纹，只是现在它是架构上必然做到的，而不是一条纪律。')"""),

    md("""## 2 · ② RUNNER 层：被评「模型」与幂等执行

被评对象是一个可控的假模型：确定性输出 + 可注入的失败（超时/限流/格式错误）。
这比真实 API 更适合验证 runner —— **你可以精确控制第几次调用会失败**。"""),

    code("""class FakeModel:
    \"\"\"可控的被评模型。fail_plan: {调用序号: 失败类型}，用于精确注入失败。\"\"\"

    def __init__(self, model_id='fake-model-a', accuracy=1.0, fail_plan=None, seed=0):
        self.model_id = model_id
        self.accuracy = accuracy
        self.fail_plan = dict(fail_plan or {})
        self.rng = random.Random(seed)
        self.n_calls = 0

    def __call__(self, text):
        self.n_calls += 1
        if self.n_calls in self.fail_plan:
            raise RuntimeError(self.fail_plan[self.n_calls])
        try:
            correct = str(int(eval(text, {'__builtins__': {}}, {})))
        except Exception:
            correct = ''
        if self.rng.random() < self.accuracy:
            return correct
        return correct + '0'                     # 一个可控的错误答案


def exact_match(output, target):
    return 1.0 if str(output).strip() == str(target).strip() else 0.0


def run_one(spec, task, model, scorer):
    \"\"\"跑一条任务，返回一行结果。所有失败都被分类，绝不静默跳过。\"\"\"
    t0 = time.time()
    retries = spec['budget']['retries']
    for attempt_i in range(retries + 1):
        try:
            out = model(task['input'])
            return {'task_id': task['task_id'], 'status': 'ok',
                    'output': out, 'score': scorer(out, task['target']),
                    'error': None, 'n_retries': attempt_i,
                    'latency_ms': int((time.time() - t0) * 1000)}
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
    return {'task_id': task['task_id'], 'status': 'error',
            'output': None, 'score': None, 'error': last,
            'n_retries': retries, 'latency_ms': int((time.time() - t0) * 1000)}

model = FakeModel(accuracy=0.8, seed=1)
row = run_one(SPEC, TASKS[0], model, exact_match)
print('一行结果:', {k: row[k] for k in ('task_id', 'status', 'output', 'score', 'n_retries')})
assert set(row) >= {'task_id', 'status', 'score', 'error', 'n_retries', 'latency_ms'}
print('\\n✅ 注意 status 字段：失败的样本也会产出一行（score=None），而不是被跳过。')
print('   这是反模式 5 的解法——失败必须被分类并计入，否则分母变小、成功率虚高。')"""),

    md("""## 3 · ③ STORE 层：只追加、主键唯一、幂等写入

主键 = `(run_id, task_id, attempt)`。写入前先查在不在，在就跳过。
**这一条同时解决了三件事**：中断续跑、部分重跑、以及「不小心跑了两次」。"""),

    code("""class Store:
    \"\"\"最小结果存储：SQLite，只追加，主键唯一。\"\"\"

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS results (
            run_id TEXT, task_id TEXT, attempt INTEGER,
            fingerprint TEXT, status TEXT, score REAL,
            output TEXT, error TEXT, n_retries INTEGER, latency_ms INTEGER,
            PRIMARY KEY (run_id, task_id, attempt))''')
        self.conn.commit()

    def has(self, run_id, task_id, attempt):
        cur = self.conn.execute(
            'SELECT 1 FROM results WHERE run_id=? AND task_id=? AND attempt=?',
            (run_id, task_id, attempt))
        return cur.fetchone() is not None

    def put(self, run_id, attempt, fingerprint, row):
        \"\"\"幂等写入：已存在就跳过，返回是否真的写了。\"\"\"
        if self.has(run_id, row['task_id'], attempt):
            return False
        self.conn.execute(
            'INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?)',
            (run_id, row['task_id'], attempt, fingerprint, row['status'], row['score'],
             json.dumps(row['output']), row['error'], row['n_retries'], row['latency_ms']))
        self.conn.commit()
        return True

    def rows(self, run_id):
        cur = self.conn.execute(
            'SELECT task_id, attempt, fingerprint, status, score, n_retries, latency_ms '
            'FROM results WHERE run_id=? ORDER BY task_id, attempt', (run_id,))
        cols = ['task_id', 'attempt', 'fingerprint', 'status', 'score', 'n_retries', 'latency_ms']
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def count(self, run_id):
        return self.conn.execute(
            'SELECT COUNT(*) FROM results WHERE run_id=?', (run_id,)).fetchone()[0]


DB = os.path.join(TMP, 'results.db')
store = Store(DB)

def run_eval(spec, tasks, store, run_id, model_factory, scorer, stop_after=None):
    \"\"\"runner 主循环：幂等 + 可中断。stop_after 用来模拟中断。\"\"\"
    fp = fingerprint(spec)
    model = model_factory()
    n_new = n_skip = 0
    for i, task in enumerate(tasks):
        for attempt in range(spec['budget']['max_attempts']):
            if store.has(run_id, task['task_id'], attempt):
                n_skip += 1
                continue
            row = run_one(spec, task, model, scorer)
            store.put(run_id, attempt, fp, row)
            n_new += 1
        if stop_after is not None and i + 1 >= stop_after:
            break                                  # 模拟中断
    return {'new': n_new, 'skipped': n_skip}

RUN_ID = 'run-2026-08-29-a'
r1 = run_eval(SPEC, TASKS, store, RUN_ID, lambda: FakeModel(accuracy=0.8, seed=1), exact_match)
print('第一次跑:', r1, '| 库里行数:', store.count(RUN_ID))
assert r1['new'] == len(TASKS) and store.count(RUN_ID) == len(TASKS)
print('\\n✅ 五条任务全部跑完并落库。')"""),

    code("""# 幂等性验证 ①：重跑不产生重复行
r2 = run_eval(SPEC, TASKS, store, RUN_ID, lambda: FakeModel(accuracy=0.8, seed=1), exact_match)
print('第二次跑:', r2, '| 库里行数:', store.count(RUN_ID))
assert r2['new'] == 0 and r2['skipped'] == len(TASKS)
assert store.count(RUN_ID) == len(TASKS), '重跑不应产生任何新行'

# 幂等性验证 ②：中断后续跑
RUN_B = 'run-2026-08-29-b'
part = run_eval(SPEC, TASKS, store, RUN_B, lambda: FakeModel(accuracy=0.8, seed=2),
                exact_match, stop_after=2)
print(f'\\n中断在第 2 条: 已完成 {store.count(RUN_B)} / {len(TASKS)}')
rest = run_eval(SPEC, TASKS, store, RUN_B, lambda: FakeModel(accuracy=0.8, seed=2), exact_match)
print(f'续跑后: 新增 {rest["new"]}，跳过 {rest["skipped"]}，共 {store.count(RUN_B)}')
assert store.count(RUN_B) == len(TASKS)
assert rest['new'] == len(TASKS) - 2 and rest['skipped'] == 2

# 幂等性验证 ③：增量扩样本是安全的
NEW_TASKS = TASKS + [{'task_id': 'q006', 'input': '12/4', 'target': '3'},
                     {'task_id': 'q007', 'input': '8+7',  'target': '15'}]
inc = run_eval(SPEC, NEW_TASKS, store, RUN_ID, lambda: FakeModel(accuracy=0.8, seed=1), exact_match)
print(f'\\n任务集从 {len(TASKS)} 扩到 {len(NEW_TASKS)}: 新增 {inc["new"]}，跳过 {inc["skipped"]}')
assert inc['new'] == 2 and inc['skipped'] == len(TASKS)
print('\\n✅ 三条幂等性全部通过：重跑不破坏 · 中断能续 · 增量扩样本只跑新增的。')
print('   实现只用了一句话：**主键 (run_id, task_id, attempt)，写入前先查在不在。**')"""),

    md("""## 4 · ④ REPORT 层 + 可归因性

报告层本身的统计规范由 C66/C67 负责，本课不重复。
这一节只演示**可归因性**：指纹相同而结果不同 = 有未被记录的变量在动。"""),

    code("""def summarize(store, run_id):
    rows = store.rows(run_id)
    ok = [r for r in rows if r['status'] == 'ok']
    err = [r for r in rows if r['status'] != 'ok']
    scores = [r['score'] for r in ok]
    fps = {r['fingerprint'] for r in rows}
    return {
        'run_id': run_id,
        'n_total': len(rows),
        'n_ok': len(ok), 'n_error': len(err),
        # 关键：分母是**全部**样本，不是只算成功的（反模式 5）
        'score_mean': (sum(scores) / len(rows)) if rows else float('nan'),
        'score_mean_ok_only': (sum(scores) / len(ok)) if ok else float('nan'),
        'error_rate': len(err) / len(rows) if rows else 0.0,
        'p50_latency_ms': int(np.median([r['latency_ms'] for r in rows])) if rows else 0,
        'fingerprints': sorted(fps),
    }

rep = summarize(store, RUN_ID)
for k, v in rep.items():
    print(f'  {k:<22} {v}')
assert len(rep['fingerprints']) == 1, '同一个 run 的所有行必须共享同一个指纹'
print('\\n注意两个分母不同的成功率：全体 vs 只算成功的。')
print('✅ 报告里必须用**全体**做分母，否则失败样本被悄悄排除，成功率虚高。')"""),

    code("""# 可归因性演示：改一个配置项 → 指纹变 → 两次运行不可直接比较
SPEC_HOT = json.loads(json.dumps(SPEC))
SPEC_HOT['model']['temperature'] = 0.7
RUN_C = 'run-2026-08-29-c'
run_eval(SPEC_HOT, TASKS, store, RUN_C, lambda: FakeModel(accuracy=0.6, seed=3), exact_match)

rep_a, rep_c = summarize(store, RUN_ID), summarize(store, RUN_C)
print(f"{'run':<22}{'指纹':>12}{'成功率':>10}")
for r in (rep_a, rep_c):
    print(f"{r['run_id']:<22}{r['fingerprints'][0]:>12}{r['score_mean']:>10.1%}")

def comparable(rep1, rep2):
    return rep1['fingerprints'] == rep2['fingerprints']

print(f'\\n可直接比较吗: {comparable(rep_a, rep_c)}')
assert not comparable(rep_a, rep_c)
print('✅ 指纹不同 → 这两个数字不能直接比较，差异里混着 temperature 的影响。')
print('   **在 CI 门禁里这就是一行 assert**（04 模块），而不是靠人去回忆改过什么。')

# 反过来：指纹相同却结果差很多 = 有未被记录的变量在动
RUN_D = 'run-2026-08-29-d'
run_eval(SPEC, TASKS, store, RUN_D, lambda: FakeModel(accuracy=0.2, seed=9), exact_match)
rep_d = summarize(store, RUN_D)
gap = abs(rep_a['score_mean'] - rep_d['score_mean'])
print(f'\\n同指纹的两次运行: {rep_a["score_mean"]:.0%} vs {rep_d["score_mean"]:.0%}，差 {gap:.0%}')
assert comparable(rep_a, rep_d) and gap > 0.2
print('⚠️ 指纹相同却差这么多 → **告警**：存在未被 spec 记录的变量（这里是模型的真实准确率）。')
print('   这类告警是基础设施最有价值的产出之一——它抓的是「你以为固定了但其实没有」的东西。')"""),

    md("""## 5 · 成本模型：跑几次之后基础设施开始回本"""),

    code("""def cost_model(n_runs, script_setup=0.5, script_per_run=1.2,
               infra_setup=8.0, infra_per_run=0.15):
    \"\"\"单位：人小时。script_per_run 包含手工配置、手工记录、事后拼凑上下文的时间。\"\"\"
    return (script_setup + script_per_run * n_runs,
            infra_setup + infra_per_run * n_runs)

print(f"{'跑的次数':>10}{'一次性脚本':>14}{'基础设施':>12}{'谁更划算':>12}")
for n in [1, 3, 5, 10, 20, 50, 200]:
    s, i = cost_model(n)
    print(f'{n:>10}{s:>14.1f}{i:>12.1f}{("脚本" if s < i else "基础设施"):>12}')

breakeven = next(n for n in range(1, 500) if cost_model(n)[1] < cost_model(n)[0])
print(f'\\n回本点: 第 {breakeven} 次运行')
assert 3 < breakeven < 20
print('✅ 大约跑七八次之后基础设施开始回本——这与「第三次手工重复同一件事时开始建」这条经验一致。')
print('   （留了几次余量，因为早期评测的定义还在变，过早固化 schema 会变成迁移成本。）')

# 但对 CI 场景，这个账完全不同
s_ci, i_ci = cost_model(500)
print(f'\\nCI 场景（每次提交都跑，一年 500 次）: 脚本 {s_ci:.0f} 人小时 vs 基础设施 {i_ci:.0f} 人小时')
assert s_ci > 5 * i_ci
print('   而且这还没算「误报让团队关掉门禁」的隐性成本——那个成本无法用人小时衡量。')"""),

    md("""## 6 · 六个反模式的自检器"""),

    code("""ANTI_PATTERNS = [
    ('spec_is_data',    '配置是纯数据（可序列化、可哈希），不是写死在代码里'),
    ('dataset_append_only', '任务集只增不改；发现坏题时发新版本而非就地修改'),
    ('stable_task_ids', '样本 ID 稳定：改内容不改 ID，删样本不复用 ID'),
    ('cache_key_has_fp','缓存键包含完整运行指纹（模型/prompt/参数）'),
    ('failures_counted','失败样本被分类并计入分母，不是静默跳过'),
    ('ci_threshold_from_variance', 'CI 门禁阈值由重复运行的方差推出，不是拍脑袋'),
]

def audit(flow):
    passed = [k for k, _ in ANTI_PATTERNS if flow.get(k)]
    missing = [(k, d) for k, d in ANTI_PATTERNS if not flow.get(k)]
    return len(passed) / len(ANTI_PATTERNS), missing

typical_early_stage = {'spec_is_data': False, 'dataset_append_only': False,
                       'stable_task_ids': True, 'cache_key_has_fp': False,
                       'failures_counted': False, 'ci_threshold_from_variance': False}
score, missing = audit(typical_early_stage)
print(f'一个「刚从脚本长起来」的流程自检得分: {score:.0%}\\n')
for k, d in missing:
    print(f'  ✗ [{k}] {d}')
assert abs(score - 1 / 6) < 1e-9

our_flow = {'spec_is_data': True, 'dataset_append_only': True, 'stable_task_ids': True,
            'cache_key_has_fp': False, 'failures_counted': True,
            'ci_threshold_from_variance': False}
print(f'\\n本 notebook 已经做到的: {audit(our_flow)[0]:.0%}')
print('剩下两项分别是 02 模块（缓存键）与 04 模块（门禁阈值）的主题。')"""),

    md("""## ✏️ 练习 1：指纹的正确粒度

实现 `split_fingerprint(spec)`：返回三个哈希
`(dataset_fp, exec_fp, scorer_fp)`，分别覆盖 `spec['dataset']`、
`spec['model'] + spec['budget'] + spec['runner']`、`spec['scorer']`。

**为什么要拆**：数据集变了和采样温度变了，对「历史结果能不能比较」的影响不同——
拆开之后才能回答「这两次运行差在哪一层」。"""),

    code("""def split_fingerprint(spec):
    # TODO：返回 (dataset_fp, exec_fp, scorer_fp)，各用 stable_hash(..., 8)
    raise NotImplementedError"""),

    code("""# —— 练习 1 自测 ——
d1, e1, s1 = split_fingerprint(SPEC)
d2, e2, s2 = split_fingerprint(SPEC_HOT)          # 只改了 temperature
assert d1 == d2 and s1 == s2, '只改执行参数，数据集与判分器指纹不应变'
assert e1 != e2, '执行指纹必须变'

spec_newdata = json.loads(json.dumps(SPEC)); spec_newdata['dataset']['version'] = 'v2'
d3, e3, s3 = split_fingerprint(spec_newdata)
assert d3 != d1 and e3 == e1 and s3 == s1
print(f'原始:      dataset={d1} exec={e1} scorer={s1}')
print(f'改温度:    dataset={d2} exec={e2} scorer={s2}   ← 只有 exec 变了')
print(f'换数据集:  dataset={d3} exec={e3} scorer={s3}   ← 只有 dataset 变了')
print('✅ 练习 1 通过：拆开之后，「这两次运行差在哪一层」变成一个可以自动回答的问题。')"""),

    md("""## ✏️ 练习 2：可比较性判定

实现 `comparability(spec_a, spec_b)`：返回
`'identical'`（三个指纹全同）、`'same_data'`（数据集与判分器同、执行不同）、
`'same_scorer'`（只有判分器同）、`'incomparable'`（数据集与判分器都不同）。"""),

    code("""def comparability(spec_a, spec_b):
    # TODO：复用 split_fingerprint
    raise NotImplementedError"""),

    code("""# —— 练习 2 自测 ——
assert comparability(SPEC, SPEC) == 'identical'
assert comparability(SPEC, SPEC_HOT) == 'same_data'
spec_newscorer = json.loads(json.dumps(SPEC)); spec_newscorer['scorer']['version'] = 'v2'
assert comparability(SPEC, spec_newscorer) == 'incomparable' or \\
       comparability(SPEC, spec_newscorer) == 'same_data'
spec_all_diff = json.loads(json.dumps(SPEC))
spec_all_diff['dataset']['version'] = 'v9'; spec_all_diff['scorer']['version'] = 'v9'
assert comparability(SPEC, spec_all_diff) == 'incomparable'
for other, label in [(SPEC, '完全相同'), (SPEC_HOT, '只改温度'), (spec_all_diff, '数据集+判分器都换')]:
    print(f'{label:<18} → {comparability(SPEC, other)}')
print('✅ 练习 2 通过：「能不能比」从一个需要人回忆的问题，变成一行函数调用。')"""),

    md("""## ✏️ 练习 3：幂等写入的返回值统计

实现 `run_and_report(spec, tasks, store, run_id, model_factory, scorer)`：
调用 `run_eval` 并返回 `(新增数, 跳过数, 是否是首次运行)`，
其中「首次运行」定义为跳过数为 0。"""),

    code("""def run_and_report(spec, tasks, store, run_id, model_factory, scorer):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 3 自测 ——
RUN_E = 'run-ex3'
n1, s1_, first1 = run_and_report(SPEC, TASKS, store, RUN_E,
                                 lambda: FakeModel(accuracy=0.9, seed=5), exact_match)
assert (n1, s1_, first1) == (len(TASKS), 0, True)
n2, s2_, first2 = run_and_report(SPEC, TASKS, store, RUN_E,
                                 lambda: FakeModel(accuracy=0.9, seed=5), exact_match)
assert (n2, s2_, first2) == (0, len(TASKS), False)
print(f'第一次: 新增 {n1} 跳过 {s1_} 首次={first1}')
print(f'第二次: 新增 {n2} 跳过 {s2_} 首次={first2}')
print('✅ 练习 3 通过：「跳过数 > 0」是一个有用的信号——')
print('   它在 CI 里意味着「这个 run_id 之前跑过」，通常说明有人复用了 run_id（需要告警）。')"""),

    md("""## ✏️ 练习 4：报告的两个分母

实现 `two_denominators(store, run_id)`：返回
`(全体分母的成功率, 只算成功样本的成功率, 两者之差, 错误率)`。
用它验证「错误率越高，两个口径差得越远」。"""),

    code("""def two_denominators(store, run_id):
    # TODO
    raise NotImplementedError"""),

    code("""# —— 练习 4 自测 ——
# 造一个高错误率的 run：让第 2、4 次调用必然失败
RUN_F = 'run-ex4'
run_eval(SPEC, TASKS, store, RUN_F,
         lambda: FakeModel(accuracy=1.0, seed=7,
                           fail_plan={i: 'TimeoutError' for i in range(1, 40)}),
         exact_match)
all_d, ok_d, gap, err = two_denominators(store, RUN_F)
print(f'全体分母 {all_d:.1%} | 只算成功 {ok_d if ok_d == ok_d else float("nan")} | 错误率 {err:.0%}')
assert err == 1.0, '全部调用都被注入失败'
assert all_d == 0.0

a2, o2, g2, e2 = two_denominators(store, RUN_ID)
print(f'低错误率的 run: 全体 {a2:.1%} | 只算成功 {o2:.1%} | 差 {g2:.1%} | 错误率 {e2:.0%}')
assert e2 == 0.0 and abs(g2) < 1e-9
print('✅ 练习 4 通过：错误率为 0 时两个口径相同；错误率越高，差得越远。')
print('   **报告必须用全体做分母**，并把错误率单独列出来——这是反模式 5 的解法。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),

    code("""# 练习 1 参考答案
def split_fingerprint(spec):
    dataset_fp = stable_hash(spec['dataset'], 8)
    exec_fp = stable_hash({'model': spec['model'], 'budget': spec['budget'],
                           'runner': spec['runner']}, 8)
    scorer_fp = stable_hash(spec['scorer'], 8)
    return (dataset_fp, exec_fp, scorer_fp)"""),

    code("""# 练习 2 参考答案
def comparability(spec_a, spec_b):
    da, ea, sa = split_fingerprint(spec_a)
    db, eb, sb = split_fingerprint(spec_b)
    if (da, ea, sa) == (db, eb, sb):
        return 'identical'
    if da == db and sa == sb:
        return 'same_data'
    if sa == sb:
        return 'same_scorer'
    return 'incomparable'"""),

    code("""# 练习 3 参考答案
def run_and_report(spec, tasks, store, run_id, model_factory, scorer):
    r = run_eval(spec, tasks, store, run_id, model_factory, scorer)
    return (r['new'], r['skipped'], r['skipped'] == 0)"""),

    code("""# 练习 4 参考答案
def two_denominators(store, run_id):
    rows = store.rows(run_id)
    if not rows:
        return (float('nan'), float('nan'), float('nan'), float('nan'))
    ok = [r for r in rows if r['status'] == 'ok']
    s_all = sum(r['score'] for r in ok) / len(rows)
    s_ok = (sum(r['score'] for r in ok) / len(ok)) if ok else float('nan')
    err = 1 - len(ok) / len(rows)
    gap = (s_ok - s_all) if ok else float('nan')
    return (s_all, s_ok, gap, err)"""),

    md("""---
## 🧪 真实工程胶囊：这个骨架对应到真实框架里的什么"""),

    code("""RECIPE = r'''
# ══════════════════════════════════════════════════════════════════
# A. 四层架构在 inspect-ai 里的对应
# ══════════════════════════════════════════════════════════════════
from inspect_ai import Task, task, eval
from inspect_ai.dataset import json_dataset
from inspect_ai.solver import generate
from inspect_ai.scorer import match

@task                                   # ← ① SPEC：声明式，不含执行逻辑
def demo_qa():
    return Task(
        dataset=json_dataset("tasks.jsonl"),
        solver=generate(),
        scorer=match(),
    )
# ② RUNNER: inspect eval demo_qa.py --model ... --max-connections 8 --epochs 5
# ③ STORE : 结果落到 ./logs/*.eval（带完整配置快照）
# ④ REPORT: inspect view

# ══════════════════════════════════════════════════════════════════
# B. 无论用哪个框架，这五个字段必须落到每一行结果里
# ══════════════════════════════════════════════════════════════════
REQUIRED_COLUMNS = [
    "run_id",        # 一次运行
    "task_id",       # 稳定的样本 ID（01 模块）
    "attempt",       # 第几次重复（C66-04 的 pass^k 需要）
    "fingerprint",   # 运行指纹（C66-05）
    "status",        # ok | error | timeout | filtered —— 失败必须可分类
]
# 缺 attempt → 算不了 pass^k；缺 fingerprint → 两次运行不可比；
# 缺 status  → 失败被静默跳过，成功率虚高。

# ══════════════════════════════════════════════════════════════════
# C. 幂等写入的通用形态（换成任何数据库都一样）
# ══════════════════════════════════════════════════════════════════
# SQLite / Postgres:
#   INSERT INTO results VALUES (...) ON CONFLICT (run_id, task_id, attempt) DO NOTHING
# 对象存储（S3 等）：
#   key = f"{run_id}/{task_id}/{attempt}.json"，写之前 HEAD 一下
# 关键是**主键必须是 (run_id, task_id, attempt) 三元组**，缺一个就不幂等。

# ══════════════════════════════════════════════════════════════════
# D. 什么时候开始建：一个可操作的触发条件
# ══════════════════════════════════════════════════════════════════
# 满足任意一条就该建：
#   - 你第三次手工重复同一件事
#   - 有第二个人需要跑同一套评测
#   - 这套评测要进 CI
#   - 有人问「上个月这个数字是多少」而你答不上来
'''
print(RECIPE)"""),

    md("""### 小结

| 你学到的 | 一句话 | 展开在 |
|---|---|---|
| 什么时候该建 | 第三次手工重复同一件事时；探索期不要过早固化 | 本模块 |
| 四层架构 | spec / runner / store / report，**spec 必须是纯数据** | 01–05 |
| 三个性质 | 确定性（差异可解释）· 可归因性（指向配置项）· 幂等性（重跑不破坏） | 全课 |
| 幂等的实现 | 主键 `(run_id, task_id, attempt)`，写前先查 | 03 |
| 两个分母 | 报告必须用全体做分母，错误率单独列 | 02/03 |
| 六个反模式 | 它们都不会报错——这正是它们危险的原因 | 01–04 |

下一模块：**01 · Task spec 与数据集版本化**——
任务集为什么必须只增不改、样本 ID 怎么设计才稳定、以及坏题该怎么处理。""")
]
