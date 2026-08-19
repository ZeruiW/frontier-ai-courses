# 参考清单 · References（交通标志识别与自动驾驶感知）

> 按主题分组，★ 为必读。**每条都注明「它解决什么问题」**——因为这门课的目标不是让你
> 记住论文名字，而是让你在遇到具体问题时知道该去翻哪一篇。
>
> 与相邻课程的分工：**C53** 讲实时检测器架构；**C54** 讲 DETR 与集合预测；
> **C56** 讲检测数据增强；**C57** 讲小目标技术细节；**C58** 讲长尾与数据闭环；
> **C59** 讲 VLA 与感知接口；**C60** 讲车端部署与一致性。
> **本课聚焦「交通标志这个具体问题本身」：类别体系、系统切分、失效模式、时序稳定性、安全评测。**

---

## 一 · TSR 代表工作与数据集 · TSR Papers & Datasets

- ★ **Zhu et al. 2016, _Traffic-Sign Detection and Classification in the Wild_ (CVPR)** —
  **TT100K 的出处，也是「TSR = 小目标 + 长尾」这个共识的确立之作**。
  解决的问题：此前的基准（GTSRB/GTSDB）要么只做分类、要么规模太小，无法反映真实街景里
  「一张 2048×2048 的图里只有几个 20 像素的标志、而且类别频次跨三个数量级」的实际难度。
  **读法**：重点看它的数据统计部分（尺寸分布与类别频次直方图），那两张图就是你做 TSR 项目时的现实基准。
- ★ **Stallkamp et al. 2012, _Man vs. Computer: Benchmarking Machine Learning Algorithms for Traffic Sign Recognition_ (Neural Networks)** —
  **GTSRB 的出处**。解决的问题：给交通标志分类一个统一、可比较的基准，并首次系统对比人类与算法。
  **为什么值得读**：它报告的人类准确率（约 98.8%）是所有「超越人类」宣称的参照系；
  也提醒你 GTSRB 的图块是**已经裁好的**——它测的是分类能力，不是 TSR 能力。
- ★ **Ertler et al. 2020, _The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale_ (ECCV)** —
  解决的问题：**跨区域泛化**。此前所有基准都是单一国家，「同一形状在不同国家含义不同」这个
  真实工程约束根本无法被研究。**读法**：看它怎么处理跨国类别体系的定义冲突——这正是全球化车型要面对的问题。
- **Houben et al. 2013, _Detection of Traffic Signs in Real-World Images: The German Traffic Sign Detection Benchmark_ (IJCNN)** —
  **GTSDB 的出处**。解决的问题：把 TSR 从分类推进到检测。它把标志归成禁令/警告/指示三大类，
  这恰好就是**两级方案里「粗类检测」的原型**，值得作为历史对照读。
- ★ **Tabernik & Skočaj 2020, _Deep Learning for Large-Scale Traffic-Sign Detection and Recognition_ (T-ITS)** —
  **本课参考文献里工业味最重的一篇**。解决的问题：200 类量级、样本极不均衡的真实标志检测该怎么做。
  它给出的是完整工程方案（Mask R-CNN 基础 + 针对性数据增强 + 分布调整），
  而不是一个刷榜技巧。**读法**：直接对照本课模块 02 与模块 03 读，你会发现它踩过的坑与本课列的高度重合。
- **Møgelmose et al. 2012, _Vision-Based Traffic Sign Detection and Analysis for Intelligent Driver Assistance Systems: Perspectives and Survey_ (T-ITS)** —
  **LISA 数据集的出处，也是深度学习之前 TSR 的完整综述**。
  解决的问题：把颜色分割、形状检测、HOG+SVM 这条传统流水线的所有变体梳理清楚。
  **为什么现在还要读**：那些颜色与形状的先验规则今天依然可以作为**后处理校验**用（红圈牌不该被判成蓝底类）。
- **Ciresan et al. 2012, _Multi-column Deep Neural Networks for Image Classification_ / IJCNN 2011 TSR 竞赛报告** —
  历史价值：**第一次在交通标志分类上超过人类**。读它是为了理解「分类这一步早已解决」，
  从而把注意力放到真正没解决的地方（找到它、稳定输出它、正确关联它）。
- **Yu et al. 2020, _BDD100K: A Diverse Driving Dataset for Heterogeneous Multitask Learning_ (CVPR)** —
  解决的问题：**给驾驶数据打上天气/时段/场景标签**。它的价值对本课不在检测标注，
  而在那套标签体系——**分桶评测的维度可以直接照抄**。
- **Caesar et al. 2020, _nuScenes_ (CVPR) / Sun et al. 2020, _Scalability in Perception for Autonomous Driving: Waymo Open Dataset_ (CVPR)** —
  解决的问题：提供带**自车位姿与时序**的多模态数据。本课模块 04 的运动补偿与多帧融合，
  在真实数据上验证只能靠这类数据集。也注意 nuScenes 的 **NDS** 指标：
  它是「不满足于 mAP」这个思路的一个早期工业答案。

---

## 二 · 多目标跟踪与时序融合 · Tracking & Temporal Fusion

- ★ **Bewley et al. 2016, _Simple Online and Realtime Tracking_ (SORT, ICIP)** —
  解决的问题：在只有检测框的前提下，用最少的东西（卡尔曼 + IoU 代价 + 匈牙利）做出可用的在线跟踪。
  **为什么它是 TSR 的首选起点**：标志静止、自车位姿已知，SORT 的线性运动假设在这里几乎完美成立。
  **读法**：这篇只有四页，建议直接照着实现一遍——本课模块 04 的练习就是它。
- ★ **Zhang et al. 2022, _ByteTrack: Multi-Object Tracking by Associating Every Detection Box_ (ECCV)** —
  解决的问题：**低分检测框被无脑丢掉**，而它们往往是被遮挡或变远的真目标。
  ByteTrack 的做法是先用高分框关联，再用低分框与未匹配轨迹做第二轮关联。
  **对 TSR 的意义极大**：远处刚出现的小标志分数天生就低，这个策略能显著提前首检距离。
- **Wojke et al. 2017, _Simple Online and Realtime Tracking with a Deep Association Metric_ (DeepSORT, ICIP)** —
  解决的问题：SORT 在遮挡后容易 ID 切换，加入外观 ReID 特征来补。
  **对 TSR 的适用性有限**（标志外观区分度低、且运动可预测），但值得知道它的取舍：外观特征换来的鲁棒性要付出算力代价。
- **Cao et al. 2023, _Observation-Centric SORT_ (OC-SORT, CVPR) / Aharon et al. 2022, _BoT-SORT_** —
  解决的问题：卡尔曼在**非线性运动与长时遮挡**下的误差累积。
  对 TSR 的启发：标志在图像中的运动是**透视放大**而非匀速平移，恒速模型在近距离会失准。
- ★ **Luiten et al. 2021, _HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking_ (IJCV)** —
  解决的问题：**MOTA 由漏检主导，关联侧的改进几乎看不出来**。HOTA 把检测精度与关联精度显式解耦。
  **为什么必读**：它是「一个指标掩盖了两个独立问题」的最佳教科书案例，
  这个思路可以直接迁移到本课模块 05 对 mAP 的批判。
- **Bernardin & Stiefelhagen 2008, _Evaluating Multiple Object Tracking Performance: The CLEAR MOT Metrics_** —
  MOTA/MOTP 的原始定义。读它是为了理解 HOTA 到底在批评什么。
- **Kalman 1960, _A New Approach to Linear Filtering and Prediction Problems_** —
  卡尔曼滤波的原始论文。不必精读，但要理解**它是「预测 + 观测」的最优线性融合**——
  这正是本课贝叶斯多帧累积那一节的数学同源物。

---

## 三 · 置信度标定、不确定性与开集 · Calibration & Uncertainty

- ★ **Guo et al. 2017, _On Calibration of Modern Neural Networks_ (ICML)** —
  解决的问题：**现代神经网络系统性过自信**，softmax 输出根本不是概率。
  提出温度缩放：一个标量参数、不改模型、不改排序，却能把 ECE 降一个数量级。
  **本课模块 02 的直接来源**——两级方案的置信度合成，前提就是两级都先标定过。
- **Naeini et al. 2015, _Obtaining Well Calibrated Probabilities Using Bayesian Binning_ (AAAI)** —
  **ECE 的出处**。解决的问题：给「模型有多自信过头」一个可计算的单一数字。
- **Küppers et al. 2020, _Multivariate Confidence Calibration for Object Detection_ (CVPRW)** —
  解决的问题：**检测的标定不能只看分类分数**，它还与框的位置、尺寸相关（小目标往往更过自信）。
  对 TSR 极其对口：本课强调可靠性图必须按像素尺寸分开画，依据就在这里。
- ★ **Kendall & Gal 2017, _What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?_ (NeurIPS)** —
  解决的问题：**区分偶然不确定性（数据本身模糊，如远处糊掉的标志）与认知不确定性（模型没见过，如外国牌）**。
  这个区分决定了对策完全不同：前者要改传感器或早点检出，后者要补数据或走拒识。
- **Lakshminarayanan et al. 2017, _Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles_ (NeurIPS)** —
  解决的问题：不确定性的简单强基线，也是**多模型分歧**这类难例触发器的理论依据（详见 C58）。
- **Hendrycks & Gimpel 2017, _A Baseline for Detecting Misclassified and Out-of-Distribution Examples_ (ICLR)** —
  解决的问题：用最大 softmax 概率做 OOD 检测的基线。**读它是为了知道这个基线有多弱**——
  softmax 归一化会对完全没见过的类别照样给出高分，这正是本课「拒识」一节的警告。
- **Liu et al. 2020, _Energy-based Out-of-distribution Detection_ (NeurIPS)** —
  解决的问题：比最大 softmax 更好的开集分数。TSR 的临时牌、外国牌、损坏牌都属于这个范畴。
- **Scheirer et al. 2013, _Toward Open Set Recognition_ (TPAMI)** —
  开集识别的问题定义。**闭集假设在真实道路上必然被打破**，这篇给了它一个正式的名字与框架。
- **Angelopoulos & Bates 2021, _A Gentle Introduction to Conformal Prediction_** —
  解决的问题：给出**有统计保证的预测集合**（「以 95% 概率类别在这三个之中」）。
  对安全系统很有吸引力：它把「不确定」变成一个有覆盖率保证的输出，而不是一个拍脑袋的阈值。

---

## 四 · 检测方法（与 C53/C54/C57 的接口）· Detection Methods

> 这一组只列本课会引用到的最小集合，展开在其他课程。

- **Lin et al. 2017, _Feature Pyramid Networks for Object Detection_ (CVPR)** —
  多尺度的标准答案。**TSR 的尺寸跨度极大**（近处 200 px、远处 12 px），层级分配规则直接影响小标志的负载分布。C57 详读。
- **Lin et al. 2017, _Focal Loss for Dense Object Detection_ (RetinaNet, ICCV)** —
  解决的问题：前景-背景极端不平衡。TSR 里一张图几万个候选、只有几个正样本，是这个问题最极端的场景之一。
- **Zhang et al. 2020, _Bridging the Gap Between Anchor-based and Anchor-free Detection via Adaptive Training Sample Selection_ (ATSS, CVPR)** —
  解决的问题：固定 IoU 阈值对不同尺度**极不公平**。小目标在阈值 0.5 下几乎匹配不到正样本。C53 详读。
- ★ **Wang et al. 2021, _A Normalized Gaussian Wasserstein Distance for Tiny Object Detection_** —
  解决的问题：**IoU 对小框的位移极度敏感**（8×8 的框位移 2 px，IoU 从 1.0 掉到 0.39），
  而且在框不相交时完全没有梯度。NWD 把框建模成 2D 高斯，用 Wasserstein 距离度量，尺度不敏感且处处有梯度。
  **对 TSR 直接有效**，C57 有完整实现。
- **Carion et al. 2020, _End-to-End Object Detection with Transformers_ (DETR, ECCV)** —
  匈牙利匹配的出处。**本课模块 04 的跨帧关联用的是同一个算法**。C54 详读。
- **Zhao et al. 2024, _DETRs Beat YOLOs on Real-time Object Detection_ (RT-DETR, CVPR)** / **Lyu et al. 2022, _RTMDet_** —
  TSR 车端检测器的现实候选。选型方法论在 C53。
- **Akyon et al. 2022, _Slicing Aided Hyper Inference_ (SAHI, ICIP)** —
  解决的问题：高分辨率图上的小目标推理。**对 TSR 的取舍很关键**：切片能显著提召回，
  但计算量是原图的 4–16 倍，车端能否承受要算清楚。C57 详读。

---

## 五 · 长尾与数据（与 C58 的接口）· Long-tail & Data

- **Gupta et al. 2019, _LVIS: A Dataset for Large Vocabulary Instance Segmentation_ (CVPR)** —
  **repeat factor sampling 的出处**（r_c = max(1, √(t/f_c))）。
  解决的问题：类别频次跨数量级时该怎么采样。TSR 的频次分布与 LVIS 高度同构。
- **Cui et al. 2019, _Class-Balanced Loss Based on Effective Number of Samples_ (CVPR)** —
  解决的问题：**样本数不等于有效信息量**（第 1000 张限速 60 的边际价值远低于第 10 张）。
- **Tan et al. 2020, _Equalization Loss for Long-Tailed Object Recognition_ (CVPR)** —
  解决的问题：**检测特有的长尾病理**——稀有类在训练中被海量负梯度淹没。
- **Menon et al. 2021, _Long-tail Learning via Logit Adjustment_ (ICLR)** —
  解决的问题：推理时按类别先验修正 logits，**零训练成本、理论优美**，是最值得先试的一招。
- **Kang et al. 2020, _Decoupling Representation and Classifier for Long-Tailed Recognition_ (ICLR)** —
  解决的问题：表示与分类器该用不同的数据分布学。**非常实用**，而且它解释了为什么两级方案天然缓解长尾。

---

## 六 · 鲁棒性、天气与物理攻击 · Robustness & Physical World

- ★ **Eykholt et al. 2018, _Robust Physical-World Attacks on Deep Learning Visual Classification_ (RP2, CVPR)** —
  **就是那篇「在 STOP 牌上贴几张纸条，模型稳定判成限速 45」的论文**。
  解决的问题：证明物理世界的扰动足以稳定欺骗分类器。
  **为什么必读**：它是安全评审的必答题，也是「模型对纹理的依赖远超直觉」的最直观证据；
  真实世界的贴纸、涂鸦、反光条会无意间构成同类扰动。
- **Hendrycks & Dietterich 2019, _Benchmarking Neural Network Robustness to Common Corruptions and Perturbations_ (ImageNet-C, ICLR)** —
  解决的问题：给「常见退化」（噪声、模糊、天气、数字失真）一套**标准化、可比较**的评测协议。
  **本课模块 03 的分桶评测思路可以直接借用它的分级方式**（每种退化五个严重度）。
- **Michaelis et al. 2019, _Benchmarking Robustness in Object Detection: Autonomous Driving when Winter is Coming_** —
  解决的问题：把上一条搬到检测任务与驾驶场景。**结论很值得引用**：常见退化下检测性能的掉幅远大于分类。
- **Sakaridis et al. 2018, _Semantic Foggy Scene Understanding with Synthetic Data_ (IJCV, Foggy Cityscapes)** —
  解决的问题：**用物理雾模型合成训练数据**，并证明它对真实雾天有迁移收益。
  本课模块 03 的大气散射合成实验直接对应这条路线。
- **Narasimhan & Nayar 2002/2003, _Vision and the Atmosphere_ / _Contrast Restoration of Weather Degraded Images_** —
  **大气散射模型 I = J·t + A(1−t) 的物理来源**。
  解决的问题：为什么雾天是「远处先消失」——透射率 t 随距离指数衰减。
  这解释了 TSR 雨雾天首检距离骤降的物理机制，也告诉你**用高斯模糊模拟雾是错的**。
- **He et al. 2009, _Single Image Haze Removal Using Dark Channel Prior_ (CVPR)** —
  去雾的经典。对 TSR 的实际意义是提醒你：**去雾是有代价的**（引入伪影、放大噪声），
  在感知前端做全局去雾未必比直接用雾天数据训练更划算。
- **Meingast et al. 2005, _Geometric Models of Rolling-Shutter Cameras_** —
  解决的问题：卷帘快门形变的几何建模。TSR 里它会改变圆形标志的宽高比，破坏形状先验。

---

## 七 · 评测、误差分析与安全标准 · Evaluation & Safety Standards

- ★ **Bolya et al. 2020, _TIDE: A General Toolbox for Identifying Object Detection Errors_ (ECCV)** —
  解决的问题：**mAP 掉了 3 个点，到底掉在哪**。TIDE 把误差拆成 Cls / Loc / Both / Dupe / Bkg / Miss 六类，
  并算出「修好每一类能涨多少 mAP」。**这是决定下一步做什么的最强工具**，C61 有完整实现。
- **Hoiem et al. 2012, _Diagnosing Error in Object Detectors_ (ECCV)** —
  TIDE 的思想源头，也是**按尺寸/遮挡度分桶分析**这个做法的早期系统化尝试。本课模块 05 的分桶评测与它一脉相承。
- **Lin et al. 2014, _Microsoft COCO_ (ECCV)** —
  AP@[.5:.95] 与 small/medium/large 分桶的定义出处。
  **注意 COCO 的 small 是「面积 < 32²」，而 TSR 的绝大多数目标都落在这个桶里甚至更小**——
  这意味着 COCO 的分桶粒度对 TSR 太粗，你必须自己定更细的尺寸桶。
- **Oksuz et al. 2018/2021, _Localization Recall Precision (LRP) Error_** —
  解决的问题：**AP 无法指导工作点选择**（它是曲线下面积）。LRP 给出在某个阈值下
  定位、召回、精度三者的综合误差，更贴近部署时的实际选择。
- ★ **Philion et al. 2020, _Learning to Evaluate Perception Models Using Planner-Centric Metrics_ (PKL, CVPR)** —
  解决的问题：**感知指标与下游后果脱节**——mAP 认为漏检一辆远处的车和漏检一辆近处横穿的车一样糟。
  PKL 用「感知误差导致规划输出变化多少」来衡量。
  **本课模块 05 代价敏感评测的学术依据**，也是回答「为什么 mAP 不够」时最有说服力的引用。
- ★ **ISO 21448:2022, _Road vehicles — Safety of the intended functionality_ (SOTIF)** —
  解决的问题：**没有任何硬件故障、但功能本身不足**所导致的风险。
  它把场景分成「已知安全 / 已知不安全 / 未知不安全」四个象限，
  目标是把未知不安全的区域尽可能缩小。**TSR 的所有失效都属于这个范畴**——
  没有东西坏掉，就是看不清、认错了、关联错了。
  **读法**：不必读全文，理解它的四象限框架与「场景驱动的验证」思路即可，
  本课模块 03 的失效模式全景与模块 05 的场景切片本质上就是在执行这套方法论。
- **ISO 26262, _Road vehicles — Functional safety_** —
  解决的问题：硬件/软件**故障**导致的风险，以及 ASIL 等级的划分方法（严重度 × 暴露率 × 可控性）。
  **与 SOTIF 的分工是面试常问点**：26262 管「坏了怎么办」，21448 管「没坏但不够用」。
- **UL 4600, _Standard for Safety for the Evaluation of Autonomous Products_** —
  解决的问题：用**安全论证（safety case）**的方式而非条款清单来评估自动驾驶系统。
  对本课的启发：你需要为「TSR 足够安全」构造一条证据链，而不只是报一个 mAP。
- **Shalev-Shwartz et al. 2017, _On a Formal Model of Safe and Scalable Self-Driving Cars_ (RSS)** —
  解决的问题：把「安全驾驶」形式化成可验证的数学约束。
  对 TSR 的意义：它展示了**感知输出必须携带不确定性**才能进入形式化安全论证——
  一个没有置信度的检测结果在这个框架里是无法使用的。
- **各车企与监管机构的安全报告（Waymo Safety Framework、NHTSA ADS 相关文件、UN R157 ALKS）** —
  解决的问题：了解**监管方关心什么指标**（脱离率、违规率、ODD 边界的声明与验证）。
  读一份就能明白：他们要的不是 mAP，而是「你怎么知道它在你声明的范围内是安全的」。

---

## 八 · 法规与标志体系（一手材料）· Regulations

> 这一组不是论文，但**它们才是类别体系的权威定义**。做标注规范之前必须翻。

- ★ **GB 5768《道路交通标志和标线》（中国国家标准，分多个部分）** —
  解决的问题：**中国 TSR 的类别到底有哪些、长什么样、多大尺寸**。
  警告/禁令/指示/指路/旅游区/作业区/辅助标志的完整体系与形状颜色规则都在这里。
  **它就是你的类别定义书**：标注规范、层次标签的第一层、形状-颜色校验规则全部应该从它推导。
- ★ **UNECE, _Convention on Road Signs and Signals_（维也纳公约，1968 及后续修订与合并版）** —
  解决的问题：欧洲及多数缔约国的标志体系与**形状-颜色-语义的强映射规则**。
  读它是为了拿到那条免费的先验：三角=警告、红圈=禁令、蓝圆=指示。
- **FHWA, _Manual on Uniform Traffic Control Devices_ (MUTCD)** —
  美国体系。**读它是为了看清一个反例**：MUTCD 大量使用文字牌，形状-颜色先验在这里几乎失效，
  TSR 必须叠加 OCR。这直接说明「一套模型走全球」为什么不成立。
