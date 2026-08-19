# -*- coding: utf-8 -*-
"""C55 模块 01 · 数据集与标志分类体系。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("前置知识", "模块 00（像素预算与四层输出）；C43（数据工程）与 C58（长尾闭环）可后续补"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 01_datasets_taxonomy.ipynb'),
    ("核心参考", "TT100K (CVPR 2016)、GTSRB/GTSDB、Mapillary MTSD (ECCV 2020)、BDD100K；GB 5768 / Vienna Convention / MUTCD"),
    ("预计时长", "读 70 分钟 + 跑 60 分钟"),
]

SECTIONS = [
    ("why", "为什么「类别体系」比模型选型更早决定天花板", "".join([
        P("模块 00 算清了物理边界：<strong>146 米处只有 6.8 个像素</strong>。这一节要说清另一条同样刚性、但更容易被忽视的边界——<strong>你定义的类别体系决定了这个系统最好能到什么程度，而且它一旦上线就极难改</strong>。"),
        P("原因很直接：类别体系是<span class=\"term\">标注规范</span>（annotation protocol）的输入，标注规范决定了已标数据的语义，而<strong>已标数据是不可逆资产</strong>。改一次细类定义，历史上所有数据要么重标（几十万框，成本以百万计），要么废弃。所以「先随便定几个类，跑通再说」在 TSR 里是最贵的一种技术债。"),
        DUAL(
            "举个具体的例子。假设你一开始把限速牌定义成 <code>speed_limit_60</code>、<code>speed_limit_80</code> 这样的扁平类别。三个月后产品说「要支持区间测速起终点」「要支持货车专用限速」「要支持 LED 可变限速牌」。<em>在扁平体系里，这三件事各自把限速类别数乘以一个倍数</em>——原来 14 个限速值变成 14×5×2×16 = 2240 个类别，而其中绝大多数一辈子也收集不到 10 个样本。<strong>而在层次体系里，这三件事只是给属性头多加三个字段。</strong>",
            "更严谨地说：扁平类别体系把<span class=\"term\">语义的笛卡尔积</span>硬编码进了输出层，于是类别数随语义维度指数增长，而每个类别的样本数随之指数衰减——<strong>这就是 TSR 长尾的<em>人造</em>成分</strong>。真实世界的长尾（某些标志本来就罕见）是不可消除的；但由类别设计造成的长尾是可以设计掉的。<em>「先分清哪部分长尾是真实的、哪部分是你自己造出来的」，是 TSR 数据工作的第一步</em>，也是面试里能立刻显出经验的判断。",
        ),
        CALLOUT("intuition", "本模块的主线可以浓缩成一句话：<strong>把「类别」压到最少，把「属性」做到最全，把「几何证据」原样输出</strong>。类别负责「这是哪一族标志」（样本充足、可靠），属性负责「具体参数是多少」（可共享参数、可增量扩展），几何证据负责「它是否对自车生效」（交给有上下文的下游判断）。<em>模块 00 的四层输出（L0 定位 / L1 粗类 / L2 细类 / L3 属性），正是这个原则的产物。</em>"),
    ])),
    ("landscape", "数据集全景：五个必须知道的名字与它们的真实数字", "".join([
        P("面试里问「你用过哪些 TSR 数据集」，答得出名字只是及格；<strong>能说清每个数据集的规模、标注粒度、以及它<em>不能</em>用来做什么，才是真正的区分度</strong>。下面这张表的最后一列是重点。"),
        TABLE(["数据集", "规模", "标注粒度", "图像来源与分辨率", "<strong>关键局限</strong>"], [
            ["<strong>GTSRB</strong><br>(德国, 2011)",
             "≈51,800 张<br>39,209 训练 / 12,630 测试<br><strong>43 类</strong>",
             "<strong>只有分类</strong>（已裁好的标志图块）",
             "车载视频截取；图块 15×15 – 250×250 px",
             "<strong>没有检测标注</strong>，无法训检测器；且每块物理标志来自同一段视频的 ≈30 帧连续 track——<strong>随机划分 train/test 会严重泄漏</strong>"],
            ["<strong>GTSDB</strong><br>(德国, 2013)",
             "<strong>900 张</strong><br>600 训练 / 300 测试<br>1,206 个标志",
             "检测框 + 43 类（评测按 4 个大类）",
             "1360×800 px；标志 16×16 – 128×128 px",
             "<strong>900 张是玩具规模</strong>，现代检测器几十个 epoch 就过拟合；类别极不均衡，很多类只有个位数实例"],
            ["<strong>TT100K</strong><br>(清华-腾讯, CVPR 2016)",
             "≈100,000 张（含标志的约 1 万张）<br><strong>≈30,000 个标志实例</strong><br>出现 <strong>221 类</strong>，标准协议只评 <strong>45 类</strong>（实例数 &gt;100 的）",
             "检测框 + 细类（中国 GB 5768 体系）",
             "腾讯街景全景图裁切，<strong>2048×2048 px</strong>",
             "<strong>中国场景 + 小目标 + 长尾的最佳公开代表</strong>，但来自<strong>车顶全景相机</strong>：无运动模糊、白天晴天为主、视角与车载前视不同 → <strong>与量产域差很大</strong>"],
            ["<strong>MTSD</strong><br>(Mapillary, ECCV 2020)",
             "≈100,000 张（≈52k 全标注 + ≈48k 部分标注）<br><strong>≈320,000 个标志标注</strong><br><strong>313 类</strong>",
             "检测框 + 细类 + 部分属性",
             "众包街景（手机 / 行车记录仪 / GoPro），分辨率与画质<strong>高度异质</strong>",
             "<strong>唯一覆盖六大洲的数据集</strong>，是研究「区域差异」的必备；但画质异质、相机内参未知，直接拿来训车规模型域差明显"],
            ["<strong>BDD100K</strong><br>(伯克利, 2020)",
             "100,000 张关键帧<br>10 个检测类<br>traffic sign ≈<strong>24 万框</strong>（train split）",
             "<strong>traffic sign 只有一个类</strong>，无细类",
             "行车记录仪，1280×720 px；含夜间 / 雨雪 / 多城市",
             "<strong>只能训「哪里有牌」，不能训「是什么牌」</strong>；但它是少数覆盖夜间与恶劣天气的大规模数据"],
        ]),
        H3("还应该知道的第二梯队"),
        UL([
            "<strong>LISA</strong>（美国, MUTCD 体系）：≈6,610 帧、≈7,855 个标注、47 种美国标志。<em>价值在于它是 MUTCD 体系的对照组</em>——把它和 GTSRB 放一起看，「形状-颜色-语义映射」的体系差异一目了然。",
            "<strong>DFG Traffic Sign Dataset</strong>（斯洛文尼亚）：约 7,000 张、13,000 个实例、<strong>200 个细类</strong>，且刻意保留了长尾。<em>它是「细类多 + 每类样本少」这个 TSR 典型形态的干净实验床</em>。",
            "<strong>CURE-TSD / CURE-TSR</strong>：在同一批场景上人工施加 12 种退化（雨、雪、雾、镜头模糊、过曝、噪声、编码伪影…）× 5 个强度等级。<em>这是做「失效模式分桶评测」（模块 03/05）时最省事的现成材料</em>。",
            "<strong>RTSD</strong>（俄罗斯）：十万量级帧、150+ 类，覆盖冬季与低光。",
            "<strong>nuScenes / Waymo Open Dataset</strong>：<em>都没有细粒度的交通标志类别</em>——nuScenes 把标志放在高精地图图层里而不是检测标注里，Waymo 有一个笼统的 <code>sign</code> 类。<strong>不要在面试里说「我用 nuScenes 做 TSR」</strong>，这会暴露没真看过标注。",
        ]),
        DUAL(
            "把这些数据集串起来看，会发现一个尴尬但重要的事实：<strong>没有任何一个公开数据集能直接支撑量产 TSR</strong>。GTSRB 没有检测框、GTSDB 太小、TT100K 域差大且只有一万张有效图、MTSD 画质异质、BDD100K 没有细类。<em>所以真实岗位上你面对的一定是「自建数据集 + 公开数据集做预训练/验证」的组合</em>——而这正是「标注规范」和「类别体系」如此重要的原因：<strong>你才是那个定义数据的人</strong>。",
            "更进一步：这些数据集的价值应该按用途分开评估，而不是按「哪个更大」排序。<strong>预训练与结构验证</strong>用 TT100K（中国体系、小目标充分）；<strong>跨域泛化研究</strong>用 MTSD（唯一的多区域来源）；<strong>恶劣条件鲁棒性</strong>用 BDD100K + CURE-TSD；<strong>分类头的快速消融</strong>用 GTSRB（分类任务干净、迭代快）；<strong>长尾方法的对照实验</strong>用 DFG（200 类且尾巴真实）。<em>「按用途选数据集」而不是「按大小选数据集」，是数据工作成熟度的直接体现。</em>",
        ),
        CALLOUT("warn", "<strong>GTSRB 的 track 泄漏是一个必须知道、且面试里可以主动提的坑</strong>。数据集里每一块物理标志会以约 30 帧的连续 track 形式出现（车在接近，标志越来越大）。<em>如果你把所有图块打散后随机划分 train/test，同一块物理标志的第 7 帧会进训练集、第 8 帧会进测试集——两张图几乎一模一样</em>。结果是测试准确率虚高好几个点。<strong>GTSRB 官方是按 track 划分的，正是为了避免这一点</strong>；而很多复现代码没注意，直接 <code>train_test_split</code>。这个坑在自建数据集上会以「按帧划分而不是按路段/按物理标志划分」的形式重现，<em>而且更隐蔽，因为没有人提醒你</em>。"),
    ])),
    ("standards", "三大标志体系：形状-颜色-语义的映射是三个不同的函数", "".join([
        P("「用红色分割 + 圆形检测找限速牌」这类传统 CV 方法，以及「CNN 隐式学到颜色和形状先验」这个事实，都建立在一个假设上：<strong>形状与颜色到语义存在稳定映射</strong>。这个假设在<em>单一区域内</em>成立，<strong>跨区域则彻底失效</strong>——因为世界上有三套互不兼容的标志体系。"),
        TABLE(["语义", "中国 GB 5768", "Vienna 公约（欧洲 / 多数国家）", "美国 MUTCD"], [
            ["<strong>警告</strong>",
             "<strong>黄底 + 黑边 + 等边三角形</strong>（顶角朝上）",
             "<strong>白底或黄底 + 红边 + 等边三角形</strong>（type Aa）",
             "<strong>黄色菱形</strong>（diamond）—— <em>形状完全不同</em>"],
            ["<strong>禁令 / 限制</strong>",
             "白底 + 红圈 + 黑图案，圆形",
             "白底或黄底 + 红圈，圆形",
             "<strong>白底黑字竖长方形</strong>（regulatory）"],
            ["<strong>限速</strong>",
             "<strong>红圈内数字</strong>（km/h）",
             "<strong>红圈内数字</strong>（km/h）",
             "<strong>白底黑字矩形 “SPEED LIMIT 55”</strong>（mph）—— <em>本质是文字版式识别</em>"],
            ["<strong>指示（强制）</strong>",
             "<strong>蓝底 + 白图案</strong>，圆形",
             "<strong>蓝底 + 白图案</strong>，圆形",
             "<strong>蓝色 = 服务设施</strong>（加油/住宿/医院），<em>非强制</em>"],
            ["<strong>指路</strong>",
             "一般道路 <strong>蓝底</strong>；高速公路 <strong>绿底</strong>",
             "各国不一：德国 Autobahn <strong>蓝底</strong>、Bundesstraße 黄底；法国 autoroute 蓝底、国道绿底",
             "<strong>全部绿底</strong>白字"],
            ["<strong>停车让行</strong>",
             "八角形红底白「停」",
             "八角形红底（B,2a）或圆形红边内含倒三角（B,2b）",
             "八角形红底白 STOP（<strong>八角形仅此一用</strong>）"],
            ["<strong>施工 / 临时</strong>",
             "（2009 版起）作业区标志",
             "多数国家沿用警告形状",
             "<strong>橙色</strong>菱形/矩形（temporary traffic control）"],
        ]),
        H3("三个最有杀伤力的具体差异"),
        OL([
            "<strong>警告标志的形状</strong>：Vienna 与中国是三角形，美国是<strong>黄色菱形</strong>。一个在中国数据上训练的模型，学到的「三角形 ⇒ 警告」先验在美国一次都用不上。",
            "<strong>限速牌的表示方式</strong>：Vienna/中国是「红圈 + 数字」——<em>颜色和形状承载了「这是限速」这个语义，数字只承载参数</em>；美国是「白底矩形 + SPEED LIMIT 文字 + 数字」——<em>语义完全由文字承载</em>。<strong>这导致两个体系的限速识别是两种不同的任务</strong>：前者是细粒度视觉分类 + 数字识别，后者本质上是场景文字识别（OCR）。",
            "<strong>蓝色的含义</strong>：中国和 Vienna 里蓝底圆形是<strong>强制性指示</strong>（「必须直行」「必须靠右」）；美国的蓝色是<strong>服务设施</strong>（加油站、医院、休息区），完全没有强制性。<em>把「蓝色 ⇒ 必须执行」这条规则带到美国，会让车对着加油站指示牌做动作</em>。",
            "<strong>指路牌底色与道路等级的映射甚至在欧洲内部就不一致</strong>：中国「绿底 = 高速」，德国「蓝底 = 高速（Autobahn）、黄底 = 联邦公路」。<em>也就是说，同一块蓝底指路牌在中国意味着「普通道路」，在德国意味着「高速公路」——语义正好相反</em>。",
        ]),
        DUAL(
            "这些差异导出一个非常实用的结论：<strong>「跨区域迁移 TSR 模型」不是域适应问题，是任务重定义问题</strong>。域适应（domain adaptation）解决的是「同一个语义在不同外观分布下的识别」——比如晴天训练、雨天部署。而<em>跨标志体系改变的是标签空间本身与形状-颜色-语义映射函数</em>，没有任何域适应方法能处理「三角形在这里是警告、在那里不存在」。<strong>正确的工程回答是：换区域 = 换类别体系 + 换标注 + 重训分类头</strong>（检测头因为是类别无关的，往往可以复用——这又是两级方案的一个隐藏优势，见模块 02）。",
            "但也存在一条可迁移的中间层，值得作为面试里的「加分观点」：<strong>把标志分解成「几何形状 + 主色 + 内部图元（数字/箭头/符号/文字）」这三个可组合的部件</strong>，而不是把每个标志当成一个整体模板。<em>部件是跨体系共享的</em>——八角形、红色、数字「60」在三个体系里都存在，变的只是组合规则与组合后的语义。<strong>因此「部件级表示 + 区域相关的组合规则表」在理论上能让视觉主干跨区域复用，只替换那张规则表</strong>。这正是本节末尾「研究前沿」里会再提到的开放方向：<em>它有明确的工程价值，但目前还没有被公认可行的实现</em>。",
        ),
        CALLOUT("danger", "<p>一个真实会出事的场景：<strong>某些标志在不同体系里形状相同、语义不同</strong>。例如「圆形 + 红边 + 白底 + 数字」在 Vienna 体系是<em>最高限速</em>，但在美国某些州的特定语境（如收费/桥梁限重的圆形牌）以及在部分国家的「建议速度」牌里，同样的视觉形态含义不同；再如倒三角在多数国家是「让行」，而在日本「一时停止」用的是倒三角红底白字「止まれ」——<strong>它的语义是 STOP 而不是 YIELD</strong>。<em>模型看到倒三角输出 YIELD，在日本就是「该停不停」</em>。<strong>所以跨区域部署必须有一张显式的「区域 → 标志体系」配置表，而不是指望模型自己泛化</strong>。这条在面试里讲出来，比背十个数据集名字有用。</p>", "同形不同义：跨区域最危险的一类错误"),
    ])),
    ("explosion", "类别数爆炸：真实长尾与人造长尾", "".join([
        P("TSR 的类别数为什么会失控？因为<strong>每增加一个语义维度，类别数就乘以一个倍数</strong>。以中国的限速牌为例，把它写成笛卡尔积："),
        ASCII("""限速类的语义维度（中国 GB 5768 场景）

  ① 限速值        {5,10,15,20,30,40,50,60,70,80,90,100,110,120}        14 种
  ② 牌型变体      {限速, 解除限速, 最低限速(蓝底), 区间测速起, 区间测速终}   5 种
  ③ 载体          {实体反光牌, LED 可变电子牌(VMS)}                      2 种
  ④ 辅助牌槽位    {车型限定?, 时段限定?, 距离预告?, 车道限定?}  各有/无 → 2^4 = 16 种

  扁平类别数 = 14 x 5 x 2 x 16 = **2,240 类** —— 而这只是「限速」这一支

  再算上其余细类（禁令/警告/指示/指路/辅助，约 59 个非限速细类）：
  扁平总数 = (59 + 14x5) x 2 x 16 = 129 x 32 = **4,128 类**

  ────────────────────────────────────────────────────────────
  层次分解后**需要学的输出维度**：
     L1 粗类 7  +  L2 细类 60  +  限速值 14  +  牌型 5  +  载体 2  +  辅助槽 4
   = **92 维**            压缩比 ≈ **45x**

  更重要的是**增量成本**：
     新增一个限速值（比如 “限速 25”）
       扁平体系 → 新增 5 x 2 x 16 = **160 个类别**，每个都要凑样本
       层次体系 → 属性头多 **1 个分箱**，检测器与粗/细类头**完全不动**"""),
        DUAL(
            "这张账最重要的一行是最后那个「增量成本」。<strong>扁平体系的问题不是「类别多」，而是「类别数随需求线性增长的斜率太陡」</strong>。产品每提一个新需求（支持货车限速、支持区间测速、支持电子牌），你的类别表就要膨胀一个数量级，而<em>新增的类别绝大多数永远收集不到足够样本</em>——于是它们全都躺在长尾里，拖低指标、消耗算力、还得为它们单独做 badcase 分析。",
            "把这件事说清楚需要区分两种长尾。<strong>真实长尾</strong>（intrinsic）：某些标志在物理世界里本来就罕见——「注意牲畜」「注意落石」「潮汐车道」，你再怎么设计类别体系也改变不了它们的出现频率。<strong>人造长尾</strong>（induced）：由类别定义的笛卡尔积造出来的——「限速60+货车+8:00-18:00+前方500m 的 LED 牌」之所以只有 3 个样本，不是因为这种情况罕见，而是因为你<em>把四个独立维度组合成了一个类别</em>。<em>真实长尾要靠数据闭环（C58）和重采样/重加权解决；人造长尾要靠类别体系设计消除</em>。<strong>面试里能把这两者分开谈，是能力分水岭</strong>。",
        ),
        CALLOUT("warn", "还有三类会持续制造新类别的东西，必须在设计阶段就想好归属：<strong>① 可变电子牌（VMS）</strong>——LED 点阵、黑底发光字，外观与实体牌完全不同，且<em>内容随时变化</em>，所以它的「限速 60」在语义上和实体牌一样、在视觉上完全是另一个东西；<strong>② 组合牌</strong>——主标志 + 一到多块辅助牌，组合数天然爆炸；<strong>③ 标准换版</strong>——GB 5768 从 1999 到 2009 再到 2022 改过图案，<em>道路上会长期并存新旧两版</em>。这三类如果按「新语义 = 新类别」处理，类别表会持续膨胀且永远追不上现实。"),
    ])),
    ("hier", "层次标签设计：把长尾从「类别」赶到「属性」", "".join([
        P("解法在上一节已经出现了，这里把它做成可执行的设计。<strong>层次标签的核心动作只有一个：把「决定用哪套模型能力」的信息留在类别里，把「参数」赶到属性里。</strong>"),
        ASCII("""                                 traffic_sign
        ┌──────────┬──────────┬─────┴────┬──────────┬──────────┐
    prohibitory  warning   mandatory   guide   auxiliary    vms
     禁令(白底红圈) 警告(黄底三角) 指示(蓝底圆)  指路(蓝/绿) 辅助牌   可变电子牌
        │            │           │          │         │
   ┌────┼────┐   ┌───┼───┐   ┌──┼──┐    ┌──┴──┐   ┌──┴──┐
 speed no_  stop ped sharp road go  min  dir  exit  veh  time
 _limit entry_giveway _xing curve work straight_speed board board type range
   │
   └── L3 属性（不进类别表！）
         speed_value : int      限速值 60
         unit        : km/h|mph  单位（跨区域必须显式）
         variant     : limit | cancel | minimum | section_start | section_end
         carrier     : physical | vms
         vehicle_type: null | truck | bus | ...
         time_range  : null | "08:00-18:00"
         distance_m  : null | 500
         lane_id     : null | 0..n
         condition   : normal | faded | damaged | graffiti | occluded
         facing      : front | back | side          ← 几何证据，供下游判定
         group_id    : 组合牌关联

  层级承诺：L1 几乎总能给（形状+颜色，样本充足）
            L2 在 >=16 px 时给
            L3 在 >=24 px 且未遮挡关键区域时给"""),
        TABLE(["设计收益", "机制", "具体表现"], [
            ["<strong>① 压掉人造长尾</strong>",
             "语义维度从「类别的笛卡尔积」改为「独立的属性头」",
             "4,128 类 → 92 维输出，压缩 ≈45×；新增限速值从「+160 类」变成「+1 个分箱」"],
            ["<strong>② 参数共享</strong>",
             "所有限速值共享同一个数字识别子任务",
             "「限速 25」哪怕只有 30 个样本，它的数字识别能力来自全部限速牌的几万个样本"],
            ["<strong>③ 可降级输出</strong>",
             "远处只输出 L1，近了再补 L2/L3",
             "12 px 时输出 <code>{L1: prohibitory, conf: 0.7}</code>——下游可以先保守、跟踪器可以先建实例"],
            ["<strong>④ 分层评测</strong>",
             "层次感知指标区分「同族错分」与「跨族错分」",
             "把「限速60→限速80」和「限速60→注意行人」区别对待（后者严重得多，前者更可能是分辨率不足）"],
            ["<strong>⑤ 分层代价</strong>",
             "不同层设不同的代价权重与阈值",
             "L1 用低阈值保召回，L3 用高阈值保准确——因为错误的限速值比「不知道限速值」更危险"],
            ["<strong>⑥ 增量交付</strong>",
             "新增能力不动上游",
             "新增「车道限定」属性时，检测器与 L1/L2 头完全不重训，历史数据也不需要重标类别"],
        ]),
        H3("层次感知的评测指标"),
        P("扁平准确率有个致命缺陷：<strong>它把「限速60 错成限速80」和「限速60 错成注意行人」都记为 0 分</strong>。而这两种错误的下游后果差了一个量级。层次 F1（hierarchical F-measure，Kiritchenko 等人的定义）用<strong>祖先集合的重合度</strong>解决这个问题。记 <code>Aug(c)</code> 为从根到类别 c 的路径上的所有节点（不含根）："),
        MATH("hP=\\frac{|Aug(\\hat{y})\\cap Aug(y)|}{|Aug(\\hat{y})|},\\quad hR=\\frac{|Aug(\\hat{y})\\cap Aug(y)|}{|Aug(y)|},\\quad hF=\\frac{2\\,hP\\,hR}{hP+hR}"),
        TABLE(["真值", "预测", "扁平准确率", "hF", "解读"], [
            ["限速60", "限速60", "1", "<strong>1.00</strong>", "完全正确"],
            ["限速60", "<strong>prohibitory</strong>（只给粗类）", "0", "<strong>0.67</strong>", "<strong>诚实的降级</strong>——比自信的错答分更高，这正是我们想要的激励"],
            ["限速60", "禁止驶入（同为禁令）", "0", "<strong>0.50</strong>", "同族错分：下游至少知道「这是个禁令牌」"],
            ["限速60", "注意行人（跨大类）", "0", "<strong>0.00</strong>", "跨族错分：形状与颜色都判错了，通常是严重问题"],
        ]),
        CALLOUT("intuition", "<strong>「诚实的降级得分 0.67 &gt; 自信的错答得分 0.50」这个不等式，是层次评测最重要的性质</strong>。它把「不确定时输出粗类」变成了一个<em>被指标奖励</em>的行为，而不是被惩罚的行为。<em>在扁平体系下，模型没有任何理由输出「我只知道这是禁令牌」——因为那和答错一样是 0 分，还不如赌一个细类</em>。<strong>指标的形状决定了模型（以及调模型的人）的行为</strong>；这条规律在模块 05「安全导向评测」里会以更大的尺度重现。顺带一提，本节 notebook 会证明「层次误分类代价矩阵」恰好等于 <code>1 − hF</code>，两者是同一个东西的两种写法。"),
    ])),
    ("anno", "标注规范：十二条必须在第一天就定死的规则", "".join([
        P("标注规范写得含糊，等价于给数据集注入了一层不可见的噪声，而且<strong>这层噪声在训练时表现为「模型学不好」、在评测时表现为「指标不稳」，几乎不可能被反向定位</strong>。下面这十二条，每一条都对应一个真实会引发返工的坑。"),
        TABLE(["#", "坑", "推荐规则", "不定死会怎样"], [
            ["1", "<strong>多小算有效</strong>",
             "三档：短边 &lt;4 px → <strong>不标</strong>（连有无都判不了）；4–16 px → <strong>标为 ignore</strong>（不算正样本也不算负样本）；≥16 px → 正常标注",
             "<em>只用「标 / 不标」两档是最常见的错误</em>：不标 → 远处小标志变成负样本，模型学会「忽略小标志」，远距离召回崩；全标 → 人也看不清类别，引入大量标签噪声"],
            ["2", "<strong>遮挡多少算有效</strong>",
             "按可见比例三档（&lt;30% 不标 / 30–60% ignore / ≥60% 正常），<strong>并额外要求「关键判别区域可见」</strong>",
             "只按面积比例判会出错：限速牌<em>边缘</em>被挡 80% 仍可读，<em>数字</em>被挡 20% 就完全不可读。<strong>面积比例是代理指标，关键区域可见性才是真指标</strong>"],
            ["3", "<strong>截断（图像边界）</strong>",
             "统一用 <strong>clipped</strong>（只标可见部分）或 <strong>amodal</strong>（标估计的完整范围），<em>二选一并写进规范</em>，且加 <code>is_truncated</code> 标记",
             "两种混用会让 IoU 计算、尺寸统计、分桶评测全部失真，且不同标注员之间产生系统性分歧"],
            ["4", "<strong>背面标志</strong>",
             "标为独立类 <code>sign_back</code>（灰色圆板/三角板），训练时作为<strong>难负样本</strong>",
             "不标 → 模型对背面无监督，容易误检成正面标志；直接忽略 → 浪费了一批高价值的难负样本"],
            ["5", "<strong>大角度侧面标志</strong>",
             "记录 <code>facing: front / side / back</code>；side 一般标为 ignore",
             "侧面标志严重透视变形，作为正样本会污染分类器；作为负样本又会压制真实召回"],
            ["6", "<strong>对向车道 / 辅路标志</strong>",
             "<strong>照常标注</strong>，但记录几何属性（facing、横向位置、若有则 3D 位置），<strong>由下游判断是否对自车生效</strong>",
             "<em>这是最容易设计错的一条</em>：让标注员判断「这块牌对不对自车生效」需要车道拓扑与路径信息，标注员看不到 → 标注一致性极差、且信息不可逆丢失"],
            ["7", "<strong>褪色 / 破损 / 涂鸦 / 贴纸</strong>",
             "正常标注 + <code>condition</code> 属性（normal / faded / damaged / graffiti）",
             "不记录 → 无法做分桶评测，也就永远不知道「模型在褪色牌上掉了多少」；直接丢弃 → 训练分布与真实道路不符"],
            ["8", "<strong>不可读（过曝 / 反光 / 强逆光）</strong>",
             "标框 + 类别置 <code>UNKNOWN</code> + ignore 该样本的分类损失（<strong>但保留检测损失</strong>）",
             "整条丢弃 → 检测器学不到「这里有个牌」；强行猜类别 → 标签噪声直接进分类头"],
            ["9", "<strong>组合牌（主牌 + 辅助牌）</strong>",
             "<strong>各标各的框 + 共享 <code>group_id</code></strong>；辅助牌有自己的类别与属性",
             "整体标一个大框 → 类别爆炸且框不贴合；只标主牌 → 丢掉「限速仅对货车/仅在某时段」这类<em>会直接改变控制动作</em>的信息"],
            ["10", "<strong>可变电子牌（VMS）</strong>",
             "<code>carrier: vms</code> + 标注时刻的读数 + <code>is_variable: true</code>",
             "当成实体牌标 → 下游会把一个临时读数当成永久限速；不标 → 高速场景最重要的一类限速源丢失"],
            ["11", "<strong>框的边界到哪</strong>",
             "统一「含标志白边/外框、<strong>不含</strong>支撑杆件与背板」，并给出图示",
             "含不含边框会带来 5–10% 的尺寸系统偏差 → 直接污染 anchor 设计与按尺寸分桶的评测"],
            ["12", "<strong>非真实标志</strong>",
             "<strong>不标为正样本</strong>：广告牌里的标志图案、车身贴纸、前车导航屏、驾校教具、玩具；<em>但要单独收集为难负样本</em>",
             "标了 → 模型学会检测广告牌 → 幽灵刹车；不管 → 这类误检永远修不掉（因为训练集里没有对应的负样本）"],
        ]),
        DUAL(
            "这十二条里最容易被低估的是<strong>第 1 条的「三档」设计</strong>。绝大多数团队一开始只有「标 / 不标」两档，而这在小目标任务里是有害的：<em>不标的小标志会被标签分配算法当作背景，于是模型被显式训练成「看到 10 px 的圆牌要判负」</em>——这与「我们希望它在远处至少给出 L1 粗类」的目标直接冲突。<strong>ignore 区域（COCO 的 <code>iscrowd</code>、mmdetection 的 <code>gt_bboxes_ignore</code>）存在的意义就是表达「这里我不知道，别拿它算账」</strong>，它既不产生正样本梯度也不产生负样本梯度。",
            "第二个容易被低估的是<strong>第 6 条：把「是否对自车生效」的判断权留给下游</strong>。这其实是一条通用的接口设计原则：<span class=\"term\">把判断留在拥有上下文的那一层，把证据留在产生它的那一层</span>。标注员（和感知模型）拥有的上下文是「这块牌长什么样、在图像的哪个位置、朝向如何」；<em>「它属于哪条车道、我的规划路径会不会经过那条车道」这些信息只存在于地图与规控层</em>。<strong>一旦让感知层做这个判断，你就永久丢掉了做正确判断所需的证据</strong>——因为被判为「不生效」的标志根本不会出现在输出里，下游连纠错的机会都没有。这条原则在模块 02（系统设计）与 C59（VLA 接口）会反复出现。",
        ),
        CALLOUT("danger", "<p>一条真实事故级的坑：<strong>标注规范变更后没有回溯重标，导致同一个数据集里存在两种语义</strong>。典型场景是「第一季度规定 16 px 以下不标，第二季度改成标为 ignore」——于是第一季度的数据里，小标志是<em>负样本</em>；第二季度的数据里，小标志是<em>无监督区域</em>。两批数据混在一起训练，模型收到互相矛盾的梯度，表现为「远距离召回怎么调都上不去，且方差很大」。<em>而这个问题在任何指标上都不会直接显形</em>。<strong>所以标注规范必须版本化，每一条标注都要带规范版本号，且变更时必须评估是否需要回溯</strong>——这与 C43 讲的数据血缘是同一件事。</p>", "标注规范变更必须版本化并评估回溯"),
    ])),
    ("agreement", "标注一致性：先量化标签噪声，再谈模型精度", "".join([
        P("在 TSR 里有一个反直觉但极其重要的事实：<strong>小目标的标注噪声量级，与你想要争取的精度提升量级是同一个数量级</strong>。如果不先量化标注一致性，你会花几个月去追一个本来就在噪声里的提升。"),
        P("先看几何。模块 00 已经给过这个数：边长 s 的正方形框在 x、y 各偏移 δ 后，与原框的 IoU 是"),
        MATH("\\mathrm{IoU}(s,\\delta)=\\frac{(s-\\delta)^2}{2s^2-(s-\\delta)^2}\\ \\Longrightarrow\\ \\mathrm{IoU}(8,2)=0.391,\\quad \\mathrm{IoU}(16,2)=0.620,\\quad \\mathrm{IoU}(64,2)=0.884"),
        DUAL(
            "把这个数翻译成标注场景：<strong>两个都很认真的标注员，对同一块 8 px 的远处标志各画一个框，彼此差 2 个像素——按 IoU≥0.5 的标准，他们会被判定为「标的不是同一个目标」</strong>。而 2 像素的分歧对 8 px 的目标来说，人眼根本无法避免（标志边缘本身就模糊了一两个像素）。<em>也就是说，在小尺寸段，标注一致性天然很低，而这个不一致性会同时污染训练标签与评测真值。</em>",
            "严谨的表述是：<strong>标注误差的<em>绝对</em>量级大致恒定（人手画框的抖动约 ±1–2 px，与目标大小无关），但<em>相对</em>量级随目标尺寸反比放大</strong>。对 64 px 的框，±2 px 是 3% 的相对误差；对 8 px 的框，±2 px 是 25% 的相对误差。<em>这意味着小目标的标签本身就是带噪的，而且噪声结构是「定位噪声」而非「类别噪声」</em>。<strong>直接后果：在小尺寸桶上，用 IoU=0.5 甚至 0.75 的严格阈值去评测是没有意义的——你测的一大半是标注抖动而不是模型能力。</strong> 实践中的做法是：小尺寸桶单独用更宽松的匹配阈值（或改用中心点距离 / NWD 这类对尺度不敏感的度量，见 C57），并明确声明该桶的指标不可与大尺寸桶直接比较。",
        ),
        H3("怎么量一致性：三个必测的数"),
        TABLE(["指标", "怎么算", "典型健康值", "异常时说明什么"], [
            ["<strong>框匹配率</strong>",
             "两名标注员的框做匈牙利/贪心匹配（IoU 阈值 0.5），匹配上的比例",
             "大目标 &gt;0.95；<strong>小目标可能只有 0.6–0.8</strong>",
             "偏低 → 规范里的「多小算有效」「遮挡阈值」没写清，或标注员漏标严重"],
            ["<strong>匹配框的平均 IoU（按尺寸分桶）</strong>",
             "对匹配上的框对求 IoU 均值，<strong>必须按尺寸分桶</strong>",
             "&gt;48 px 桶 &gt;0.90；<strong>&lt;16 px 桶 0.6–0.75</strong>",
             "整体偏低 → 框边界规则（含不含白边、含不含杆）没统一"],
            ["<strong>类别一致率 / Cohen's κ</strong>",
             "对匹配上的框对算类别一致率，并用 κ 扣掉「碰巧一致」的部分",
             "粗类 κ &gt;0.9；<strong>细类 κ 0.7–0.85</strong>",
             "细类 κ 低 → 类别定义有歧义（哪些算「同一类」没写清），或细类粒度超过了图像可读性"],
        ]),
        P("Cohen's κ 的定义（p<sub>o</sub> 是观察到的一致率，p<sub>e</sub> 是按各自边缘分布随机一致的期望）："),
        MATH("\\kappa=\\frac{p_o-p_e}{1-p_e},\\qquad p_e=\\sum_k p_A(k)\\,p_B(k)"),
        CALLOUT("warn", "<strong>κ 而不是原始一致率，原因是类别分布极度长尾</strong>。当 60% 的标志都是「限速」时，两个人闭着眼睛都猜「限速」就有 36% 的一致率——原始一致率会把这部分算成「一致性好」。<em>κ 把这部分扣掉，所以它才是长尾任务里唯一有意义的一致性指标</em>。同理，<strong>在报告标注一致性时必须分层报告</strong>（按尺寸桶、按粗类），因为一个 0.85 的总体 κ 完全可能由「大目标 0.95 + 小目标 0.55」组成，而后者才是你真正要修的地方。"),
        CALLOUT("intuition", "一条可以直接用的工作纪律：<strong>在启动任何模型改进之前，先做一次双标注抽检（同一批 500–1000 张由两个人独立标），把三个一致性数算出来</strong>。这件事成本很低（一两天），但它给你三样东西：<em>① 一个「指标提升的噪声地板」——低于这个量级的提升不值得追；② 一份规范漏洞清单——分歧集中在哪几条规则上，那几条就是写得不够清楚的；③ 一个分尺寸桶的评测阈值依据</em>。<strong>「你怎么知道你的 +0.5 mAP 不是噪声」是面试高频追问，而「我先量了标注一致性，噪声地板是 ±0.3」是最有说服力的答案之一。</strong>"),
    ])),
    ("bias", "数据集偏差与跨域泛化：你训的到底是什么分布", "".join([
        P("前面几节讲的是「标签空间」，这一节讲「图像分布」。<strong>TSR 的跨域问题比通用检测严重得多，因为标志的外观由标准规定、几乎没有类内变化，于是模型会把大量容量花在拟合<em>采集条件</em>而不是<em>标志本身</em>上。</strong>"),
        TABLE(["偏差类型", "具体表现", "在哪个数据集上最明显", "后果与对策"], [
            ["<strong>采集平台偏差</strong>",
             "车顶全景相机 vs 车载前视相机：安装高度、俯仰角、是否全景展开、有无运动模糊",
             "<strong>TT100K</strong>（腾讯街景，车顶全景，几乎无运动模糊）",
             "在 TT100K 上训练的模型遇到真实车载的运动模糊会明显掉点 → 必须补运动模糊增强（C56）与真实车载数据"],
            ["<strong>ISP / 画质偏差</strong>",
             "训练用 JPEG 解码图，车端是 ISP 直出；白平衡、色调映射、降噪强度都不同",
             "所有公开数据集",
             "红色禁令牌的色相在两条链路上可能差好几度 → 颜色先验失效；对策见 C60（训练-部署一致性）"],
            ["<strong>光照 / 天气偏差</strong>",
             "多数数据集以白天晴天为主",
             "GTSRB / GTSDB / TT100K（<strong>BDD100K 是少数例外</strong>）",
             "夜间、逆光、隧道出入口、雨雪的样本严重不足 → 必须定向采集 + 低光/雾化合成（C56）"],
            ["<strong>地域体系偏差</strong>",
             "GB 5768 / Vienna / MUTCD 的形状-颜色-语义映射不同",
             "跨数据集迁移时（GTSRB → TT100K）",
             "不是域适应能解决的问题，需要换类别体系 + 重训分类头（见本模块第 3 节）"],
            ["<strong>时间 / 版本偏差</strong>",
             "GB 5768 1999 / 2009 / 2022 三版图案并存于道路上",
             "任何跨年份采集的自建数据集",
             "同一语义有多个视觉变体 → 要么当同类标注（推荐，加 <code>std_version</code> 属性），要么当独立类（不推荐）"],
            ["<strong>频率偏差</strong>",
             "数据集里的类别频率 ≠ 部署区域的类别频率",
             "所有数据集",
             "<strong>按训练集频率做的重加权/logit adjustment 在新区域会系统性偏错</strong> → 先验必须按部署区域重新估计"],
            ["<strong>划分泄漏</strong>",
             "同一物理标志的多帧被分到 train 与 test 两侧",
             "<strong>GTSRB</strong>（track 结构）、任何按帧随机划分的自建数据集",
             "指标虚高数个点 → 必须按<strong>物理标志 / 路段 / 采集批次</strong>划分，而不是按帧"],
        ]),
        DUAL(
            "「划分泄漏」这一行值得单独强调，因为它是自建数据集上<strong>最普遍、也最容易被忽视的一个错误</strong>。TSR 数据天然是视频：一块标志在接近过程中被拍到 75 帧（模块 00 算过）。<em>如果你按帧随机划分，train 和 test 里会出现同一块物理标志的相邻帧——它们的背景、光照、遮挡状态几乎完全一样</em>。<strong>模型只要记住「这个路口的这块牌」就能答对，而这在真实道路上毫无价值。</strong> 正确的划分单位是<strong>物理标志实例</strong>（同一块牌的所有帧必须在同一侧），更保守的做法是按<strong>路段或采集时段</strong>划分。",
            "更一般地说，划分单位应当与<span class=\"term\">泛化目标</span>一致：你希望模型泛化到「没见过的标志实例」，就按实例划分；希望泛化到「没见过的道路」，就按路段划分；希望泛化到「没见过的城市 / 天气」，就按城市 / 天气划分。<em>每换一个划分单位，测出来的数字会显著不同，而这个差值本身就是有用的诊断信息</em>：<strong>按帧划分 95% / 按实例划分 88% / 按城市划分 72%，这三个数一起报告，才说清了模型到底泛化到了哪一层</strong>。只报最高的那个是自欺，而只报最低的那个又会低估模型在已覆盖区域的可用性。<em>面试里被问「你的模型泛化性怎么样」，用这三档来答，会比任何单个数字都有说服力。</em>",
        ),
        CALLOUT("intuition", "把本节浓缩成一条可执行的检查：<strong>拿到（或建好）一个数据集后，先问三个问题——① 图像是怎么采的（平台 / 相机 / ISP / 时段 / 天气分布）？② 标签空间属于哪个标志体系、版本是哪一版？③ 划分单位是什么？</strong> 这三问答不上来，任何在这个数据集上得到的数字都不该被信任。<em>而这三问恰好也是审阅别人实验结果时最有效的三个追问</em>——它们能在两分钟内识别出大部分「看起来很好但没有意义」的结果。"),
    ])),
    ("frontier", "研究前沿与开放问题", "".join([
        UL([
            "<strong>部件级（compositional）标志表示</strong>：把标志分解成「几何形状 + 主色 + 内部图元」的可组合表示，让视觉主干跨 GB 5768 / Vienna / MUTCD 三大体系复用，只替换一张区域相关的组合规则表。<em>这在概念上很干净，但目前缺少公认可行的实现</em>——难点在于「图元」的粒度怎么定（数字、箭头、剪影符号、文字各有不同的识别难度），以及组合规则本身也存在同形不同义的冲突。",
            "<strong>开放词表 / 少样本标志识别</strong>：用 CLIP / GLIP / Grounding DINO 这类模型实现「新增标志类型不重训」。<em>目前的实验结论并不乐观</em>：开放词表模型的强项是粗粒度语义对齐（「这是一个交通标志」），而 TSR 的难点恰好是极细粒度的差异（圆圈里的数字是 60 还是 80）。<strong>「粗类用开放词表、细类用专用头」的混合方案更现实</strong>，但如何在两者之间传递不确定性仍是开放问题。",
            "<strong>层次标签的自动构建</strong>：现在的类别树基本靠人根据国标手工设计。<em>能否从数据（视觉相似度 + 语义相似度 + 下游动作相似度）自动导出一棵「对模型友好且对下游有意义」的层次结构</em>，并随数据增长自动重构（分裂过粗的节点、合并样本不足的节点），是一个有明确工程价值的方向。notebook 里的 <code>merge_tail_classes</code> 是这个想法的最朴素版本。",
            "<strong>标注噪声的建模与利用</strong>：与其把标注抖动当成需要消除的坏东西，不如把它显式建模——<em>用「框的分布」而非「框的点估计」作为监督信号</em>（这与 GFL / 分布式框回归、以及 C57 里的 NWD 把框建模成高斯分布是同一个思路）。<strong>对小目标而言，「标签本身是分布」比「标签是一个精确的框」更符合事实</strong>，但如何在标注工具与训练流程里贯彻这一点，尚无成熟实践。",
            "<strong>合成数据与标志的可控生成</strong>：交通标志的「理想模板」是公开的（国标附图），理论上可以用渲染 + 域随机化（透视、光照、褪色、遮挡、运动模糊）为任意长尾类批量造样本。<em>已有工作证明这对分类头有效，但对检测头收益有限</em>——因为检测的难点在背景与上下文，而那部分合成不出来。<strong>「合成解决类别长尾、真实数据解决场景长尾」的分工是目前较可靠的经验</strong>，也直接连到 C56 的 copy-paste 与 C58 的定向挖掘。",
            "<strong>缺一个时序的、代价敏感的公开基准</strong>：现有 TSR 基准几乎都是单帧 mAP，而量产系统关心的是首检距离、闪烁率、FP/km、关键类召回（模块 05）。<em>没有公开的时序基准，意味着学术界的改进与车上的体验之间缺少可验证的桥梁</em>——这可能是这个领域最明显、也最容易被解决的空白。",
        ]),
        CALLOUT("paper", "必读：Zhu et al., <em>Traffic-Sign Detection and Classification in the Wild</em>（CVPR 2016）★ —— TT100K 的原始论文，中国场景、小目标与长尾的一手材料，附录里的类别频次表值得逐行看；Stallkamp et al., <em>Man vs. Computer: Benchmarking Machine Learning Algorithms for Traffic Sign Recognition</em>（Neural Networks 2012）★ —— GTSRB 的完整说明，<strong>track 划分那一节是本模块「划分泄漏」的一手来源</strong>；Houben et al., <em>Detection of Traffic Signs in Real-World Images: The German Traffic Sign Detection Benchmark</em>（IJCNN 2013）—— GTSDB；Ertler et al., <em>The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale</em>（ECCV 2020）★ —— 全球尺度与区域差异，第 3 节的类别体系设计对自建数据集非常有参考价值；Yu et al., <em>BDD100K: A Diverse Driving Dataset for Heterogeneous Multitask Learning</em>（CVPR 2020）；Tabernik &amp; Skočaj, <em>Deep Learning for Large-Scale Traffic-Sign Detection and Recognition</em>（T-ITS 2019）—— DFG 数据集，200 类长尾的干净实验床；Kiritchenko et al., <em>Learning and Evaluation in the Presence of Class Hierarchies</em>（2006）—— 层次 F1 的定义来源；Gupta et al., <em>LVIS: A Dataset for Large Vocabulary Instance Segmentation</em>（CVPR 2019）★ —— repeat factor sampling 与长尾数据集设计的方法论范本。标准文本：<em>GB 5768《道路交通标志和标线》</em>、<em>Vienna Convention on Road Signs and Signals (1968)</em>、<em>MUTCD</em>（美国 FHWA）—— <strong>面试里能引用具体条款（比如「GB 5768 里指示标志是蓝底白图案，而 MUTCD 的蓝色是服务设施」）会明显加分</strong>。相邻课程：C43（数据工程与血缘）、C56（增强）、C57（小目标）、C58（长尾与数据闭环）。完整清单见 <code>references.md</code>。"),
    ])),
]

NB = [
    md("""# 01 · 数据集与标志分类体系（长尾 / Zipf / 层次标签 / 层次评测 / 标注一致性）

目标：把「类别体系」从一件拍脑袋的事，变成**可以计算、可以验证**的工程决策。

本 notebook 你会亲手实现：
1. **合成一个真实形态的 TSR 类别分布**（120 细类 · Zipf · 3 万实例，对标 TT100K 量级）
2. **Zipf 指数拟合**与 head/common/rare 划分，并算出「靠随机采集补长尾要采多少数据」
3. **类别爆炸的账**：扁平笛卡尔积 vs 层次分解，压缩比与**增量成本**
4. **层次标签的编码**（路径 / 祖先集合）
5. **层次感知评测** hP/hR/hF —— 证明「诚实的降级」比「自信的错答」得分更高
6. **标注一致性**：框匹配 + 分尺寸桶的 IoU agreement + Cohen's κ
7. ✏️ repeat factor sampling / 尾类合并 / **标注规范判定器** / 层次代价矩阵

> 心智模型：**把「类别」压到最少，把「属性」做到最全，把「几何证据」原样输出。**
> 长尾里有一部分是真实世界给的，另一部分是你自己的类别设计造出来的——先分清这两者。"""),

    md(r"""## 1 · 合成一个真实形态的 TSR 类别分布

用 **Zipf 分布**合成：第 r 常见的类别，其实例数正比于 $r^{-s}$。
参数按 **TT100K** 的真实形态选：≈120 个细类出现过、≈30,000 个标志实例、$s\approx1.6$。

（TT100K 实际是「出现 221 类，但标准协议只评实例数 >100 的 45 类」——
下面你会看到为什么必须这么做。）"""),
    code("""import numpy as np, math, json, itertools, collections
rng = np.random.default_rng(5768)          # 5768 = GB 5768

N_CLS, S_ZIPF, TOTAL = 120, 1.6, 30000
ranks = np.arange(1, N_CLS + 1)
p_true = ranks.astype(float) ** (-S_ZIPF)
p_true = p_true / p_true.sum()
counts = rng.multinomial(TOTAL, p_true)     # 每个细类实际采到多少实例

# LVIS 式的三档划分（这里按实例数；真实 LVIS 按「出现该类的图像数」）
frequent = counts > 1000
common   = (counts >= 100) & (counts <= 1000)
rare     = counts < 100

print(f'总实例数 {counts.sum():,} · 细类数 {N_CLS}')
print(f"{'档位':<24s} {'类别数':>7s} {'实例数':>9s} {'实例占比':>9s}")
for name, mask in [('frequent (>1000)', frequent),
                   ('common   (100-1000)', common),
                   ('rare     (<100)', rare)]:
    print(f'{name:<24s} {mask.sum():>7d} {counts[mask].sum():>9,d} '
          f'{100*counts[mask].sum()/TOTAL:>8.1f}%')

print(f'\\n最常见类 {counts.max():,} 个实例 · 最罕见类 {counts.min()} 个实例 · '
      f'头尾比 {counts.max()/max(counts.min(),1):.0f}x')
print(f'前 10 类占全部实例的 {100*counts[:10].sum()/TOTAL:.1f}%')
print(f'后 60 类合计只占     {100*counts[60:].sum()/TOTAL:.1f}%')

assert counts.sum() == TOTAL
assert counts[:10].sum() / TOTAL > 0.75
assert counts[60:].sum() / TOTAL < 0.05
assert rare.sum() > frequent.sum() * 5, '罕见类的**数量**远多于常见类——这是长尾的定义'
print(f'\\n⚠️  {rare.sum()} 个 rare 类加起来还不到全部实例的 '
      f'{100*counts[rare].sum()/TOTAL:.0f}% —— 这就是为什么 TT100K 的标准协议')
print('    只评「实例数 >100」的 45 类：**其余的类连算 AP 的统计意义都没有**。')
print('    但它们在道路上真实存在，漏检一样会出事。这就是 TSR 长尾的残酷之处。')"""),

    md(r"""## 2 · Zipf 指数拟合：算出「靠随机采集补长尾」要采多少数据

$$f(r)=f_1\cdot r^{-s}\quad\Longleftrightarrow\quad \log f(r)=\log f_1-s\log r$$

在 log-log 上是一条直线，斜率就是 $-s$。**拟合出 $s$ 之后可以做一件很有用的事：
外推「要让最尾部的类攒够 N 个样本，总数据量得是多少」。**"""),
    code("""nz = counts > 0
slope, intercept = np.polyfit(np.log(ranks[nz]), np.log(counts[nz]), 1)
s_hat = -slope
print(f'拟合的 Zipf 指数 s_hat = {s_hat:.3f}   (真值 {S_ZIPF})')
assert 1.4 <= s_hat <= 1.85, s_hat

print(f"\\n{'rank':>6s} {'实测':>8s} {'Zipf 拟合':>10s}")
for r_ in [1, 3, 10, 30, 60, 100, 120]:
    fit = math.exp(intercept + slope * math.log(r_))
    print(f'{r_:>6d} {counts[r_-1]:>8d} {fit:>10.1f}')

# —— 关键外推：靠**随机采集**把最尾部的类补到 100 个实例，需要多大的数据集？
TARGET_PER_CLASS = 100
need_total = TARGET_PER_CLASS / p_true[-1]
print(f'\\n最罕见类的出现概率 p = {p_true[-1]:.2e}')
print(f'要让它攒够 {TARGET_PER_CLASS} 个实例，需要随机采集 **{need_total:,.0f}** 个标志实例')
print(f'  = 当前数据集的 **{need_total/TOTAL:.1f} 倍**')
assert need_total > 10 * TOTAL

print(f'\\n而定向挖掘（C58：嵌入检索 + 场景标签 + 主动学习触发）'
      f'只需要 ~{TARGET_PER_CLASS} 个命中样本。')
print('✅ 结论：**长尾不能靠「多采一点」解决，必须靠定向挖掘 + 类别体系设计。**')
print('   幂律的性质就是：要把尾部提升一个数量级，总量得提升同一个数量级。')"""),

    md("""## 3 · 类别爆炸的账：扁平笛卡尔积 vs 层次分解

把「限速」这一支的语义维度摊开，看看扁平体系的类别数是怎么炸的，
以及层次分解把它压到了多少。**最重要的是「增量成本」那一段。**"""),
    code("""SPEC = {
    'coarse':          7,    # 禁令/警告/指示/指路/辅助/施工/可变电子牌
    'fine':           60,    # 细类总数（其中 1 个是「限速族」的占位）
    'speed_values':   14,    # 5,10,15,20,30,...,120 km/h
    'speed_variants':  5,    # 限速 / 解除 / 最低限速 / 区间起 / 区间终
    'carrier':         2,    # 实体反光牌 / LED 可变电子牌
    'aux_slots':       4,    # 车型? 时段? 距离? 车道?  各有/无
}

def flat_class_count(spec):
    '''扁平体系：所有语义维度做笛卡尔积，每个组合是一个独立类别。'''
    speed_family = spec['speed_values'] * spec['speed_variants']
    non_speed    = spec['fine'] - 1
    return (non_speed + speed_family) * spec['carrier'] * (2 ** spec['aux_slots'])

def hier_output_dim(spec):
    '''层次体系：需要学的输出维度 = 各个头的维度之**和**（而不是积）。'''
    return (spec['coarse'] + spec['fine'] + spec['speed_values']
            + spec['speed_variants'] + spec['carrier'] + spec['aux_slots'])

flat, hier = flat_class_count(SPEC), hier_output_dim(SPEC)
print(f'扁平类别数        {flat:>8,d}')
print(f'层次输出维度      {hier:>8,d}')
print(f'压缩比            {flat/hier:>8.1f}x')
assert flat == 4128 and hier == 92
assert flat / hier > 20

# —— 增量成本：新增一个限速值（比如「限速 25」）
spec2 = dict(SPEC); spec2['speed_values'] += 1
d_flat = flat_class_count(spec2) - flat
d_hier = hier_output_dim(spec2) - hier
print('\\n新增一个限速值（如「限速 25」）：')
print(f'  扁平体系 → 新增 **{d_flat} 个类别**，每个都要独立凑样本、独立算 AP、独立做 badcase')
print(f'  层次体系 → 属性头多 **{d_hier} 个分箱**，检测器与粗/细类头**完全不动**')
assert d_flat == 160 and d_hier == 1

# —— 人造长尾 vs 真实长尾
print(f'\\n把 {TOTAL:,} 个实例摊到 {flat:,} 个扁平类别上：')
print(f'  平均每类 {TOTAL/flat:.1f} 个实例 —— **绝大多数类别一辈子凑不齐 10 个样本**')
print(f'摊到 {hier} 维层次输出上：平均每维 {TOTAL/hier:.0f} 个实例')
assert TOTAL / flat < 10 and TOTAL / hier > 300
print('\\n✅ **人造长尾**（类别设计造出来的）可以设计掉；')
print('   **真实长尾**（「注意牲畜」本来就罕见）只能靠数据闭环（C58）。先分清这两者。')"""),

    md("""## 4 · 层次标签的编码：路径与祖先集合

每个类别对应一条**从根到叶的路径**。祖先集合 `Aug(c)` = 路径上的所有节点（**不含根**）。

注意：`prohibitory` 这类**只到粗类**的标签也是合法标签——
它就是模块 00 说的「可降级输出」，路径长度为 1。"""),
    code("""TAXONOMY = {
    # 叶子（L2 细类）：path = (粗类, 细类)
    'speed_limit':      ('prohibitory', 'speed_limit'),
    'no_entry':         ('prohibitory', 'no_entry'),
    'no_left_turn':     ('prohibitory', 'no_left_turn'),
    'stop_giveway':     ('prohibitory', 'stop_giveway'),
    'ped_crossing':     ('warning',     'ped_crossing'),
    'sharp_curve':      ('warning',     'sharp_curve'),
    'road_work':        ('warning',     'road_work'),
    'go_straight':      ('mandatory',   'go_straight'),
    'min_speed':        ('mandatory',   'min_speed'),
    'direction_board':  ('guide',       'direction_board'),
    'vehicle_type_aux': ('auxiliary',   'vehicle_type_aux'),
    # **降级标签**：只到粗类（远处只看得出形状与颜色时使用）
    'prohibitory':      ('prohibitory',),
    'warning':          ('warning',),
    'mandatory':        ('mandatory',),
    'guide':            ('guide',),
}

def aug(c):
    '''祖先集合（含自身，不含根）。'''
    return set(TAXONOMY[c])

def depth(c):
    return len(TAXONOMY[c])

print(f"{'类别':<18s} {'路径':<34s} {'深度':>4s}")
for c in ['speed_limit', 'no_entry', 'ped_crossing', 'prohibitory']:
    print(f'{c:<18s} {" / ".join(TAXONOMY[c]):<34s} {depth(c):>4d}')

assert aug('speed_limit') == {'prohibitory', 'speed_limit'}
assert aug('prohibitory') == {'prohibitory'}
assert aug('speed_limit') & aug('no_entry') == {'prohibitory'}      # 同族：共享粗类
assert aug('speed_limit') & aug('ped_crossing') == set()            # 跨族：毫无重合
print('\\n✅ 「同族错分」与「跨族错分」在祖先集合上有清晰的数学差别：')
print('   前者交集非空（至少粗类判对了），后者交集为空（形状和颜色都判错了）。')
print('   下一节把这个差别变成一个可以进 CI 的指标。')"""),

    md(r"""## 5 · 层次感知评测：为什么「诚实的降级」必须被奖励

$$hP=\frac{|Aug(\hat y)\cap Aug(y)|}{|Aug(\hat y)|},\quad
  hR=\frac{|Aug(\hat y)\cap Aug(y)|}{|Aug(y)|},\quad
  hF=\frac{2\,hP\,hR}{hP+hR}$$

扁平准确率把所有错误都记 0 分。**hF 会区分三种错误，而且给「只输出粗类」比
「自信地答错细类」更高的分——这正是我们想要的激励。**"""),
    code("""def h_prf(pred, true):
    '''层次 precision / recall / F1（Kiritchenko et al., 2006）。'''
    ap, at = aug(pred), aug(true)
    inter = len(ap & at)
    hp = inter / len(ap)
    hr = inter / len(at)
    hf = 0.0 if (hp + hr) == 0 else 2 * hp * hr / (hp + hr)
    return hp, hr, hf

CASES = [
    ('speed_limit',  'speed_limit',  '完全正确'),
    ('prohibitory',  'speed_limit',  '**诚实的降级**：只输出粗类'),
    ('no_entry',     'speed_limit',  '同族错分：至少知道是禁令牌'),
    ('ped_crossing', 'speed_limit',  '跨族错分：形状与颜色都判错'),
]
print(f"{'预测':<16s} {'真值':<14s} {'扁平':>5s} {'hP':>6s} {'hR':>6s} {'hF':>6s}  解读")
for pred, true, note in CASES:
    hp, hr, hf = h_prf(pred, true)
    print(f'{pred:<16s} {true:<14s} {int(pred==true):>5d} '
          f'{hp:>6.2f} {hr:>6.2f} {hf:>6.2f}  {note}')

assert h_prf('speed_limit',  'speed_limit')[2] == 1.0
assert abs(h_prf('prohibitory', 'speed_limit')[2] - 2/3) < 1e-12
assert h_prf('no_entry',     'speed_limit')[2] == 0.5
assert h_prf('ped_crossing', 'speed_limit')[2] == 0.0
# **核心不等式**
assert (h_prf('prohibitory', 'speed_limit')[2]
        > h_prf('no_entry', 'speed_limit')[2]
        > h_prf('ped_crossing', 'speed_limit')[2])
print('\\n✅ **核心不等式：0.67（诚实降级） > 0.50（同族错分） > 0.00（跨族错分）**')
print('   在扁平准确率下这三种情况全是 0 分 —— 于是模型没有任何理由输出「我只知道')
print('   这是禁令牌」，还不如赌一个细类。**指标的形状决定了模型的行为。**')

preds = ['speed_limit']*60 + ['prohibitory']*15 + ['no_entry']*15 + ['ped_crossing']*10
trues = ['speed_limit']*100
flat_acc = float(np.mean([p == t for p, t in zip(preds, trues)]))
mean_hf  = float(np.mean([h_prf(p, t)[2] for p, t in zip(preds, trues)]))
print(f'\\n一批 100 条预测：扁平准确率 {flat_acc:.2f} · 平均 hF {mean_hf:.3f}')
assert abs(flat_acc - 0.60) < 1e-12
assert abs(mean_hf - (60*1.0 + 15*(2/3) + 15*0.5 + 10*0.0)/100) < 1e-12
print(f'   两个数差了 {mean_hf-flat_acc:.3f} —— 而这部分全部来自「模型其实部分答对了」的样本。')"""),

    md("""## 6 · 标注一致性：先量化标签噪声，再谈模型精度

模拟两名认真的标注员独立标同一批图：
框有 ±1.5 px 的手抖、8% 的漏标、12% 的同族类别分歧。
**然后按尺寸分桶看一致性——这一步是关键，因为总体数字会掩盖小目标的灾难。**"""),
    code("""def iou_xyxy(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0

def iou_shift(side, delta):
    '''边长 side 的方框在 x,y 各偏移 delta 后与原框的 IoU（解析解）。'''
    inter = max(0.0, side - delta) ** 2
    return inter / (2 * side**2 - inter)

print('先看几何：同样 2 px 的分歧，不同尺寸的框会被判成什么')
for s_ in [8, 16, 32, 64]:
    v = iou_shift(s_, 2)
    tail = '❌ 按 IoU>=0.5 会被判成「不是同一个目标」' if v < 0.5 else ''
    print(f'  {s_:>3d}x{s_:<3d}  IoU={v:.3f}  {tail}')
assert abs(iou_shift(8, 2) - 36/92) < 1e-12
assert abs(iou_shift(64, 2) - 0.8842) < 1e-3
print('  → 标注抖动的**绝对**量级恒定（±1-2px），**相对**量级随尺寸反比放大。\\n')

# —— 模拟两名标注员独立标同一批图
rng2 = np.random.default_rng(768)
N = 400
SIZES_POOL = [8, 12, 16, 24, 32, 48, 64]
sizes = rng2.choice(SIZES_POOL, size=N, p=[.22, .20, .18, .15, .11, .08, .06])
cx = rng2.uniform(100, 1800, N); cy = rng2.uniform(200, 700, N)
CLS = ['speed_limit', 'no_entry', 'ped_crossing', 'sharp_curve',
       'go_straight', 'direction_board']
clsA = rng2.choice(len(CLS), size=N)
A = [(cx[i]-sizes[i]/2, cy[i]-sizes[i]/2, cx[i]+sizes[i]/2, cy[i]+sizes[i]/2)
     for i in range(N)]

keep = rng2.random(N) > 0.08                     # 标注员 B 漏标 8%
jit  = rng2.normal(0, 1.5, size=(N, 4))          # 四个角各自 ±1.5px 手抖
B, clsB = [], []
for i in range(N):
    if not keep[i]:
        continue
    B.append(tuple(np.array(A[i]) + jit[i]))
    c = clsA[i]
    if rng2.random() < 0.12:                     # 12% 的同族类别分歧
        c = (c + 1) % len(CLS)
    clsB.append(c)

# 贪心匹配（IoU 从高到低，一对一）
cand = []
for i in range(len(A)):
    for j in range(len(B)):
        v = iou_xyxy(A[i], B[j])
        if v >= 0.5:
            cand.append((v, i, j))
cand.sort(reverse=True)
used_a, used_b, matched = set(), set(), []
for v, i, j in cand:
    if i in used_a or j in used_b:
        continue
    used_a.add(i); used_b.add(j); matched.append((i, j, v))

def bucket(s):
    return '<16px' if s < 16 else ('16-32px' if s < 32 else '>=32px')

tot_b = collections.Counter(bucket(s) for s in sizes)
mat_b = collections.defaultdict(list)
for i, j, v in matched:
    mat_b[bucket(sizes[i])].append(v)

print(f'标注员 A: {len(A)} 框 · 标注员 B: {len(B)} 框 · 匹配上 {len(matched)} 对\\n')
print(f"{'尺寸桶':<10s} {'A 的框数':>9s} {'匹配率':>8s} {'匹配框平均 IoU':>16s}")
for k in ['<16px', '16-32px', '>=32px']:
    print(f'{k:<10s} {tot_b[k]:>9d} {len(mat_b[k])/tot_b[k]:>7.1%} '
          f'{np.mean(mat_b[k]):>16.3f}')

assert np.mean(mat_b['<16px']) < np.mean(mat_b['>=32px'])
assert np.mean(mat_b['<16px']) < 0.75, '小目标的框一致性天然很低'
assert len(mat_b['<16px'])/tot_b['<16px'] < len(mat_b['>=32px'])/tot_b['>=32px']

# 类别一致性：原始一致率 vs Cohen's kappa
ya = np.array([clsA[i] for i, j, v in matched])
yb = np.array([clsB[j] for i, j, v in matched])
po = float(np.mean(ya == yb))
pa = np.bincount(ya, minlength=len(CLS)) / len(ya)
pb = np.bincount(yb, minlength=len(CLS)) / len(yb)
pe = float((pa * pb).sum())
kappa = (po - pe) / (1 - pe)
print(f'\\n类别一致率 p_o = {po:.3f} · 随机一致 p_e = {pe:.3f} · **Cohen κ = {kappa:.3f}**')
assert 0.6 < kappa < po, 'κ 扣掉了「碰巧一致」的部分，所以必然小于原始一致率'

small_iou = float(np.mean(mat_b['<16px']))
print(f'\\n⚠️  **总体数字会骗人**：>=32px 桶的匹配 IoU 有 '
      f'{np.mean(mat_b[">=32px"]):.2f}，但 <16px 桶只有 {small_iou:.2f}。')
print('    这意味着：在小尺寸桶上用 IoU=0.5/0.75 评测，你测的一大半是**标注抖动**。')
print('✅ 可执行的纪律：动模型之前，先做一次双标注抽检，拿到三个数——')
print('   ① 指标提升的**噪声地板**（低于它的提升不值得立项）')
print('   ② 规范漏洞清单（分歧集中在哪几条规则上，那几条就是写得不够清楚的）')
print('   ③ 分尺寸桶的评测阈值依据（小桶必须放宽，或改用对尺度不敏感的度量）')"""),

    md(r"""## ✏️ 练习 1：repeat factor sampling（LVIS 的做法）

实现 `repeat_factors(counts, t)`：

- 类别频率 $f_c = \mathrm{counts}_c / \sum \mathrm{counts}$
- 重复因子 $r_c = \max\left(1,\ \sqrt{t/f_c}\right)$（`counts_c == 0` 时记 `r_c = 1.0`）
- 重采样后的期望类别分布 $q_c \propto \mathrm{counts}_c \cdot r_c$（需归一化）

返回 `(r, q)` 两个 numpy 数组。

**注意那个平方根**：它让提升是温和的（尾类频率提升 ~$\sqrt{\cdot}$ 倍而不是被拉平），
这正是 repeat factor sampling 避免尾类过拟合的设计。"""),
    code("""def repeat_factors(counts, t=0.01):
    # TODO: ① 算频率 f  ② r = max(1, sqrt(t/f))，counts==0 时 r=1
    #       ③ q ∝ counts * r 并归一化   ④ 返回 (r, q)
    raise NotImplementedError"""),
    code("""# —— 练习 1 自测 ——
COUNTS_T = np.array([12000, 5000, 2000, 800, 300, 120, 60, 25, 10, 4])
f_T = COUNTS_T / COUNTS_T.sum()
r, q = repeat_factors(COUNTS_T, t=0.01)

assert np.all(r >= 1.0 - 1e-12), 'repeat factor 不能小于 1（不允许下采样 head）'
assert np.isclose(r[0], 1.0) and np.isclose(r[4], 1.0), 'f >= t 的类 r 恰好为 1'
assert abs(r[-1] - 7.1272) < 1e-3, f'最尾类 r 应约 7.127，得到 {r[-1]}'
assert np.all(np.diff(r) >= -1e-12), 'counts 递减 => r 必须递增（单调性）'
assert np.isclose(q.sum(), 1.0)
assert q[-1] > 6 * f_T[-1], '尾类占比应被显著提升'
assert q[0] < f_T[0], 'head 占比被相对压低'

print(f"{'类别':>4s} {'实例数':>8s} {'原频率':>9s} {'r':>7s} {'重采样后':>10s} {'提升':>7s}")
for i in range(len(COUNTS_T)):
    print(f'{i:>4d} {COUNTS_T[i]:>8,d} {f_T[i]:>8.4%} {r[i]:>7.3f} {q[i]:>9.4%} '
          f'{q[i]/f_T[i]:>6.2f}x')
print('\\n✅ 练习 1 通过。三条结论：')
print('   ① f >= t 的类 r 恰为 1 —— **repeat factor 只抬尾巴，不压头部**')
print('   ② 提升是 sqrt 级的（尾类 7x 而不是 3000x）—— 把分布拉平会让尾类严重过拟合')
print('   ③ t 是唯一的旋钮：t 越大，被判为「尾」的类越多。常用取值 0.001~0.01')"""),

    md("""## ✏️ 练习 2：尾类合并（层次结构最直接的用法）

实现 `merge_tail_classes(counts, parent, min_count)`：
把实例数 `< min_count` 的类别**并到它的父节点**，重复直到不能再合并
（父节点为 `None` 表示已到顶，即使不足 `min_count` 也保留）。

返回 `(new_counts, mapping)`：
- `new_counts`: `{最终标签: 实例数}`
- `mapping`: `{原类别: 最终标签}`（没被合并的类映射到自己）

**总实例数必须守恒**——这是这类操作的第一条不变量。"""),
    code("""def merge_tail_classes(counts, parent, min_count):
    # TODO: 循环：找到 count < min_count 且 parent 不为 None 的类，
    #       把它的 count 加到父节点上、从结果里删掉、更新 mapping；
    #       直到没有可合并的类为止。
    raise NotImplementedError"""),
    code("""# —— 练习 2 自测 ——
C_IN = {'p/speed_60': 5000, 'p/speed_80': 3000, 'p/no_entry': 400,
        'p/no_uturn': 30, 'p/no_truck': 12,
        'w/ped': 800, 'w/slippery': 25, 'w/animals': 4,
        'm/turn_left': 600, 'm/min_speed': 8}
PARENT = {'p/speed_60': 'p', 'p/speed_80': 'p', 'p/no_entry': 'p',
          'p/no_uturn': 'p', 'p/no_truck': 'p',
          'w/ped': 'w', 'w/slippery': 'w', 'w/animals': 'w',
          'm/turn_left': 'm', 'm/min_speed': 'm',
          'p': None, 'w': None, 'm': None}

new_counts, mapping = merge_tail_classes(C_IN, PARENT, min_count=100)
EXPECT = {'p/speed_60': 5000, 'p/speed_80': 3000, 'p/no_entry': 400, 'p': 42,
          'w/ped': 800, 'w': 29, 'm/turn_left': 600, 'm': 8}
assert new_counts == EXPECT, new_counts
assert sum(new_counts.values()) == sum(C_IN.values()) == 9879, '总实例数必须守恒'
assert mapping['p/no_uturn'] == 'p' and mapping['w/animals'] == 'w'
assert mapping['p/speed_60'] == 'p/speed_60'
assert all(v >= 100 or PARENT.get(k) is None for k, v in new_counts.items())

print(f"{'最终标签':<14s} {'实例数':>8s}   来源")
for k in sorted(new_counts, key=lambda x: -new_counts[x]):
    src = sorted(o for o, t in mapping.items() if t == k)
    print(f'{k:<14s} {new_counts[k]:>8,d}   {", ".join(src)}')
print(f'\\n类别数 {len(C_IN)} -> {len(new_counts)}，总实例数守恒 = {sum(new_counts.values()):,}')
print('\\n✅ 练习 2 通过。两点必须理解：')
print('   ① 合并后的 `p`(42) 仍不足 100，但它已经没有父节点了 —— 真实系统里')
print('      这类桶应命名为 `other_prohibitory`，并**明确不对下游承诺细类**。')
print('   ② 合并**不是丢弃**：这些样本仍然监督着「这里有一块禁令牌」，')
print('      只是不再监督「是哪一种」。这正是层次标签最直接的价值。')"""),

    md("""## ✏️ 练习 3：标注规范判定器

把讲解里的十二条规则中最核心的几条代码化。实现
`annotation_gate(ann, cfg)`，**按下列优先级顺序，先命中先返回**：

| 顺序 | 条件 | action | reason |
|---|---|---|---|
| 1 | `min(w,h) < cfg['floor_px']` | `skip` | `below_perception_floor` |
| 2 | `min(w,h) < cfg['min_px']` | `ignore` | `too_small` |
| 3 | `visible_ratio < cfg['skip_visible']` | `skip` | `mostly_occluded` |
| 4 | `visible_ratio < cfg['min_visible']` | `ignore` | `partially_occluded` |
| 5 | `key_region_visible` 为 False | `ignore` | `key_region_occluded` |
| 6 | `facing != 'front'` | `ignore` | `not_front_facing` |
| 7 | `readable` 为 False | `ignore` | `unreadable` |
| 8 | 以上都不命中 | `label` | `ok` |

返回 `{'action':…, 'reason':…, 'applies_to_ego': ann['applies_to_ego']}`。

⚠️ **`applies_to_ego` 绝不是过滤条件，只是透传的属性**——
「这块牌是否对自车生效」需要车道拓扑与规划路径，标注员和感知模型都没有这个上下文。"""),
    code("""GATE_CFG = {'floor_px': 4, 'min_px': 16, 'skip_visible': 0.3, 'min_visible': 0.6}

def annotation_gate(ann, cfg=GATE_CFG):
    # TODO: 按上表顺序判定，返回 {'action':…, 'reason':…, 'applies_to_ego':…}
    raise NotImplementedError"""),
    code("""# —— 练习 3 自测 ——
def _ann(**kw):
    base = dict(w=40, h=40, visible_ratio=1.0, key_region_visible=True,
                facing='front', readable=True, applies_to_ego=True)
    base.update(kw); return base

CHECKS = [
    (_ann(),                              'label',  'ok'),
    (_ann(w=10, h=10),                    'ignore', 'too_small'),
    (_ann(w=3,  h=3),                     'skip',   'below_perception_floor'),
    (_ann(visible_ratio=0.45),            'ignore', 'partially_occluded'),
    (_ann(visible_ratio=0.20),            'skip',   'mostly_occluded'),
    (_ann(key_region_visible=False),      'ignore', 'key_region_occluded'),
    (_ann(facing='back'),                 'ignore', 'not_front_facing'),
    (_ann(facing='side'),                 'ignore', 'not_front_facing'),
    (_ann(readable=False),                'ignore', 'unreadable'),
    # **关键用例**：对向车道的牌，其它条件都正常 -> 照常标注！
    (_ann(applies_to_ego=False),          'label',  'ok'),
    # 优先级：又小又被挡，应先命中「小」
    (_ann(w=10, h=10, visible_ratio=0.2), 'ignore', 'too_small'),
]
print(f"{'用例':<46s} {'action':>8s}  reason")
for ann, exp_a, exp_r in CHECKS:
    got = annotation_gate(ann)
    assert got['action'] == exp_a and got['reason'] == exp_r, (ann, got, exp_a, exp_r)
    assert got['applies_to_ego'] == ann['applies_to_ego'], 'applies_to_ego 必须原样透传'
    desc = (f"{ann['w']}x{ann['h']}px vis={ann['visible_ratio']:.2f} "
            f"key={int(ann['key_region_visible'])} {ann['facing']} "
            f"read={int(ann['readable'])} ego={int(ann['applies_to_ego'])}")
    print(f'{desc:<46s} {got["action"]:>8s}  {got["reason"]}')

n_label = sum(annotation_gate(a)['action'] == 'label' for a, _, _ in CHECKS)
assert n_label == 2
print('\\n✅ 练习 3 通过。三条最容易做错的规则：')
print('   ① **三档而不是两档**：<4px 不标、4-16px 标 ignore、>=16px 正常标。')
print('      只有「标/不标」两档时，小标志会变成**负样本**，模型被显式训练成')
print('      「看到 10px 的圆牌要判负」—— 远距离召回从此救不回来。')
print('   ② **关键区域可见性**优先于面积可见比例：限速牌边缘挡 80% 仍可读，')
print('      数字挡 20% 就完全不可读。面积比例只是代理指标。')
print('   ③ **对向车道的牌照常标注**。把「是否对自车生效」塞进标注/感知层，')
print('      等于永久丢掉做正确判断所需的证据。')"""),

    md(r"""## ✏️ 练习 4：层次误分类代价矩阵

实现 `hierarchical_cost_matrix(classes, taxonomy)`：返回一个
`len(classes) x len(classes)` 的 numpy 矩阵，`C[i][j] = 1 - hF(classes[i], classes[j])`。

（可以直接复用上面的 `aug()`，或从 `taxonomy` 现取。）

做完你会发现一件漂亮的事：这个代价恰好等于
$\dfrac{d_i+d_j-2d_{\mathrm{LCA}}}{d_i+d_j}$，即**树上的归一化距离**——
`1 - hF` 与「最近公共祖先距离」是同一个东西的两种写法。"""),
    code("""def hierarchical_cost_matrix(classes, taxonomy):
    # TODO: 对每一对 (i, j) 算 1 - hF
    raise NotImplementedError"""),
    code("""# —— 练习 4 自测 ——
CLASSES4 = ['speed_limit', 'no_entry', 'ped_crossing', 'prohibitory']
C = hierarchical_cost_matrix(CLASSES4, TAXONOMY)

assert C.shape == (4, 4)
assert np.allclose(np.diag(C), 0.0), '对角必须为 0（预测正确无代价）'
assert np.allclose(C, C.T), '代价矩阵必须对称'
assert abs(C[0, 1] - 0.50) < 1e-12, '同族错分（限速 vs 禁止驶入）代价 0.5'
assert abs(C[0, 2] - 1.00) < 1e-12, '跨族错分（限速 vs 注意行人）代价 1.0'
assert abs(C[0, 3] - 1/3)  < 1e-12, '降级到粗类代价仅 1/3'
assert C[0, 3] < C[0, 1] < C[0, 2], '降级 < 同族错分 < 跨族错分'

# 与「树上归一化 LCA 距离」等价
def tree_cost(a, b):
    da, db = len(TAXONOMY[a]), len(TAXONOMY[b])
    lca = len(aug(a) & aug(b))
    return (da + db - 2 * lca) / (da + db)
for i, a in enumerate(CLASSES4):
    for j, b in enumerate(CLASSES4):
        assert abs(C[i, j] - tree_cost(a, b)) < 1e-12, (a, b)

hdr = ''.join(f'{c[:12]:>14s}' for c in CLASSES4)
print(f'{"真值 / 预测":<18s}{hdr}')
for i, a in enumerate(CLASSES4):
    print(f'{a:<18s}' + ''.join(f'{C[i, j]:>14.3f}' for j in range(4)))
print('\\n✅ 练习 4 通过。这个矩阵可以直接用在三个地方：')
print('   ① **代价敏感的损失**：把 CE 换成按 C 加权的损失，跨族错分惩罚更重')
print('   ② **代价敏感的评测**：报告「平均误分类代价」而不是「错误率」')
print('   ③ **badcase 优先级**：按 C[真值][预测] 排序，先看跨族错分')
print('   而且 1 - hF 恰好等于树上的归一化 LCA 距离 —— 两种写法，同一个东西。')"""),

    md("""---
### 📖 参考答案（先自己做，再对照）"""),
    code("""# 练习 1 参考答案
def repeat_factors(counts, t=0.01):
    counts = np.asarray(counts, dtype=float)
    f = counts / counts.sum()
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.divide(t, f, out=np.full_like(f, np.inf), where=f > 0)
    r = np.maximum(1.0, np.where(counts > 0, np.sqrt(ratio), 1.0))
    q = counts * r
    return r, q / q.sum()"""),
    code("""# 练习 2 参考答案
def merge_tail_classes(counts, parent, min_count):
    cur = dict(counts)
    mapping = {c: c for c in counts}
    while True:
        victim = next((c for c in sorted(cur)
                       if cur[c] < min_count and parent.get(c) is not None), None)
        if victim is None:
            return cur, mapping
        tgt = parent[victim]
        cur[tgt] = cur.get(tgt, 0) + cur.pop(victim)
        for k, v in mapping.items():
            if v == victim:
                mapping[k] = tgt"""),
    code("""# 练习 3 参考答案
def annotation_gate(ann, cfg=GATE_CFG):
    short = min(ann['w'], ann['h'])
    if   short < cfg['floor_px']:                    a, why = 'skip',   'below_perception_floor'
    elif short < cfg['min_px']:                      a, why = 'ignore', 'too_small'
    elif ann['visible_ratio'] < cfg['skip_visible']: a, why = 'skip',   'mostly_occluded'
    elif ann['visible_ratio'] < cfg['min_visible']:  a, why = 'ignore', 'partially_occluded'
    elif not ann['key_region_visible']:              a, why = 'ignore', 'key_region_occluded'
    elif ann['facing'] != 'front':                   a, why = 'ignore', 'not_front_facing'
    elif not ann['readable']:                        a, why = 'ignore', 'unreadable'
    else:                                            a, why = 'label',  'ok'
    # ⚠️ applies_to_ego **只透传，不参与判定**
    return {'action': a, 'reason': why, 'applies_to_ego': ann['applies_to_ego']}"""),
    code("""# 练习 4 参考答案
def hierarchical_cost_matrix(classes, taxonomy):
    n = len(classes)
    C = np.zeros((n, n))
    for i, a in enumerate(classes):
        for j, b in enumerate(classes):
            ap, at = set(taxonomy[a]), set(taxonomy[b])
            inter = len(ap & at)
            hp, hr = inter / len(ap), inter / len(at)
            hf = 0.0 if (hp + hr) == 0 else 2 * hp * hr / (hp + hr)
            C[i, j] = 1.0 - hf
    return C"""),

    md("""---
## 🧪 真实工程胶囊：类别体系 + 标注规范（可直接评审的一页纸）

下面这份 `RECIPE` 可以原样复制成项目里的 `taxonomy.yaml` / `annotation_spec.md` 骨架。
它把本模块的四件事——**层次类别树 / 属性表 / 十二条标注规则 / 划分与验收**——
落成可评审、可版本化的条目。"""),
    code("""RECIPE = r'''
# ============================================================
# TSR 类别体系与标注规范（骨架）   spec_version: 2024.1
# 每一条标注必须记录 spec_version；规范变更时必须评估是否需要回溯重标。
# ============================================================

region: CN                      # CN=GB 5768 / EU=Vienna / US=MUTCD —— **显式声明体系**
std_version: GB5768-2022        # 道路上长期并存新旧版图案：用属性区分，不新增类别

## 1. 层次类别树（L1 粗类 -> L2 细类）—— 类别表只放「决定用哪套能力」的信息
taxonomy:
  prohibitory:  [speed_limit, speed_cancel, no_entry, no_left_turn, no_uturn,
                 no_parking, no_overtaking, stop_giveway, yield_giveway, weight_limit]
  warning:      [ped_crossing, sharp_curve, road_work, slippery, school_zone,
                 falling_rocks, animals, narrow_road]
  mandatory:    [go_straight, turn_left, turn_right, keep_right, min_speed, roundabout]
  guide:        [direction_board, exit_board, distance_board, lane_board]
  auxiliary:    [vehicle_type_aux, time_range_aux, distance_aux, lane_aux]
  workzone:     [detour, lane_closed, flagger]
  vms:          [vms_speed, vms_text]        # LED 可变电子牌：视觉形态与实体牌完全不同

# **降级标签合法**：只给到 L1（如 prohibitory）是合法输出，评测用层次 hF 计分。

## 2. L3 属性（不进类别表！这里是长尾被消化掉的地方）
attributes:
  speed_value:    {type: int,  values: [5,10,15,20,30,40,50,60,70,80,90,100,110,120]}
  speed_unit:     {type: enum, values: [kmh, mph]}       # 跨区域必须显式
  variant:        {type: enum, values: [limit, cancel, minimum, section_start, section_end]}
  carrier:        {type: enum, values: [physical, vms]}
  vehicle_type:   {type: enum, values: [null, truck, bus, trailer, hazmat]}
  time_range:     {type: str,  example: "08:00-18:00"}
  distance_m:     {type: int,  example: 500}
  lane_id:        {type: int,  nullable: true}
  condition:      {type: enum, values: [normal, faded, damaged, graffiti, occluded]}
  facing:         {type: enum, values: [front, side, back]}   # 几何证据，供下游判定
  applies_to_ego: {type: bool, note: "标注员不判定；由下游用车道拓扑+规划路径判定"}
  group_id:       {type: int,  note: "组合牌：主牌与辅助牌共享同一个 group_id"}
  is_truncated:   {type: bool}
  spec_version:   {type: str}

## 3. 标注规则（十二条，按判定优先级）
gate:
  size:       {floor_px: 4, min_px: 16}      # <4 不标 / 4-16 ignore / >=16 正常标
  occlusion:  {skip_visible: 0.30, min_visible: 0.60,
               key_region_must_be_visible: true}   # 关键区域优先于面积可见比例
  truncation: clipped                        # 全项目统一 clipped（不用 amodal）+ is_truncated
  back_side:  {back: "标为 sign_back 独立类，作为难负样本", side: "ignore"}
  opposite_lane: "照常标注，只记录 facing / 横向位置；**不做是否生效的判定**"
  condition:  "褪色/破损/涂鸦照常标注 + condition 属性（用于分桶评测）"
  unreadable: "标框 + class=UNKNOWN + 忽略分类损失，**保留检测损失**"
  combo_sign: "主牌与辅助牌各标各的框 + 共享 group_id"
  vms:        "carrier=vms + 标注时刻读数 + is_variable=true"
  box_edge:   "含标志外框/白边，**不含**支撑杆件与背板（规范附图示）"
  not_a_sign: "广告牌图案 / 车身贴纸 / 前车导航屏 / 驾校教具 **不标为正样本**，
               但单独收集成难负样本集"
  duplicate:  "龙门架上重复出现的同内容标志：**都标**"

## 4. 划分与泄漏防护 —— 自建数据集最容易翻车的地方
split:
  unit: physical_sign_instance    # 绝不能按帧随机划分（同一块牌的相邻帧几乎一样）
  report_three_numbers: [by_frame, by_instance, by_city]
  # 三个数一起报，才说清模型泛化到了哪一层。只报最高的那个是自欺。

## 5. 标注验收 —— 先量标签噪声，再谈模型精度
annotation_qa:
  double_annotation_sample: 800          # 每批数据抽 800 张做双标
  thresholds:
    match_rate_ge_32px:  0.95
    match_rate_lt_16px:  0.70            # 小目标天然低，别定成 0.95
    mean_iou_ge_32px:    0.90
    mean_iou_lt_16px:    0.65            # ±2px 手抖在 8px 框上就是 IoU 0.39
    cohen_kappa_coarse:  0.90
    cohen_kappa_fine:    0.75            # 长尾场景必须用 kappa 而不是原始一致率
  noise_floor_note: "由双标注一致性推出的指标噪声地板；低于它的提升不立项。"

## 6. 公开数据集用途矩阵（按用途选，不是按大小选）
external_datasets:
  TT100K:   {use: [pretrain, structure_ablation], caveat: "腾讯街景车顶全景，无运动模糊，域差大"}
  MTSD:     {use: [cross_region_study],           caveat: "众包画质异质，相机内参未知"}
  BDD100K:  {use: [night_weather_detection],      caveat: "traffic sign 只有一个类，无细类"}
  GTSRB:    {use: [classifier_fast_ablation],     caveat: "**必须按 track 划分**，否则严重泄漏"}
  GTSDB:    {use: [smoke_test],                   caveat: "只有 900 张，极易过拟合"}
  DFG:      {use: [longtail_method_benchmark],    caveat: "200 类样本少，方法对照用"}
  CURE-TSD: {use: [degradation_bucket_eval],      caveat: "人工退化，非真实分布"}
'''
print(RECIPE)
for k in ['spec_version', 'region: CN', 'taxonomy', 'attributes', 'applies_to_ego',
          'floor_px', 'key_region_must_be_visible', 'group_id', 'not_a_sign',
          'physical_sign_instance', 'cohen_kappa_fine', 'external_datasets']:
    assert k in RECIPE, k
print('✅ 规范覆盖：体系声明 / 层次类别树 / 属性表 / 十二条规则 / '
      '划分防泄漏 / 标注 QA 阈值 / 数据集用途矩阵')"""),

    md("""### 小结

- **类别体系比模型选型更早决定天花板**，而且它是不可逆资产：改一次细类定义，
  历史标注要么重标要么废弃。**「先随便定几个类，跑通再说」在 TSR 里是最贵的技术债。**
- **长尾要分成两半看**：*真实长尾*（「注意牲畜」本来就罕见）只能靠数据闭环解决；
  *人造长尾*（类别的笛卡尔积造出来的）可以靠层次设计**直接消除**。
  本课的账：**4,128 个扁平类 → 92 维层次输出，压缩 45×；
  新增一个限速值从「+160 类」变成「+1 个分箱」。**
- **幂律的残酷之处**：靠随机采集把最尾部的类补到 100 个实例，需要 **15 倍**于当前的数据量。
  **长尾只能靠定向挖掘（C58）+ 类别体系设计，不能靠「多采一点」。**
- **形状-颜色-语义映射在 GB 5768 / Vienna / MUTCD 里是三个不同的函数**：
  警告在中欧是三角形、在美国是黄色菱形；蓝色在中欧是强制指示、在美国是服务设施；
  蓝底指路牌在中国是普通道路、在德国是高速公路。
  **跨区域不是域适应问题，是任务重定义问题。**
- **层次评测的核心不等式：0.67（诚实降级）> 0.50（同族错分）> 0.00（跨族错分）。**
  扁平准确率把三者都记 0 分，于是模型没理由输出粗类。**指标的形状决定模型的行为。**
  而 `1 - hF` 恰好等于树上的归一化 LCA 距离。
- **标注要三档而不是两档**（不标 / ignore / 正常标）。只有两档时小标志会变成负样本，
  模型被训练成「看到 10 px 的圆牌判负」，远距离召回从此救不回来。
- **对向车道的牌照常标注，只输出几何证据。**「是否对自车生效」需要车道拓扑与规划路径；
  把这个判断塞进标注/感知层，等于永久丢掉做正确判断所需的证据。
- **动模型之前先量标签噪声**：小尺寸桶的匹配 IoU 只有 0.66、匹配率只有 74%。
  在这个桶上用 IoU=0.5/0.75 评测，测的一大半是标注抖动。
  **「你怎么知道 +0.5 mAP 不是噪声」的最佳答案是「我先量了噪声地板」。**
- **划分单位要与泛化目标一致**，并同时报告 by_frame / by_instance / by_city 三个数。

下一站：**模块 02 · TSR 系统设计：两级 vs 端到端** —— 级联召回是个乘法。"""),
]
