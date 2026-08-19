# 参考清单 · References（检测数据增强工程）

> 每条注明**它解决了什么问题**、以及为什么值得读。先读 ★ 标记的必读。
> 本课的参考有三类：**原始论文**（讲清楚一个算子为什么这么设计）、
> **官方文档与源码**（讲清楚工业实现的真实默认值与坑）、
> **统计方法学文献**（讲清楚怎么证明一个增强真的有用——这一类最常被跳过，也最能拉开差距）。
>
> 与相邻课程的分工：**C18** 讲检测器与评测指标本身；**C51** 讲**文本**增强与合成数据；
> **C55** 讲 TSR 的失效模式（本课 05 模块的配方直接消费它）；**C57** 讲小目标的**模型侧**解法；
> **C58** 讲长尾与数据闭环（决定"要不要去采新数据"，而本课决定"手里的数据还能不能榨出更多"）。

---

## 一 · 混合类增强的原始论文 · Mixing Augmentations

- ★ **Bochkovskiy, Wang & Liao 2020, _YOLOv4: Optimal Speed and Accuracy of Object Detection_** —
  **Mosaic 的出处**，也是"bag of freebies / bag of specials"这个分类框架的出处。
  解决的问题是：在不增加推理成本的前提下把检测精度推到极限。
  读法：直接跳到 §3.4 与增强相关的消融表——**它系统地量化了每个增强单独的贡献**，
  这种做法本身就是本课 05 模块想教的东西。注意 Mosaic 的动机之一是"减小对大 batch 的依赖"，
  这个论证在今天读起来仍然很有启发。
- ★ **Ghiasi et al. 2021, _Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation_** —
  **Copy-Paste 的权威版本**，解决的问题是长尾类与小目标的样本稀缺。
  最重要的发现有两条：① 和 large scale jitter 组合时收益最大（**所以别只抄 Copy-Paste 不抄 LSJ**）；
  ② 简单粘贴（不做复杂的融合与上下文建模）已经很有效——这与直觉相反，
  值得在自己的任务上验证而不是照搬（检测任务对上下文的依赖比分割更强）。
- ★ **Yun et al. 2019, _CutMix: Regularization Strategy to Train Strong Classifiers with Localizable Features_** —
  CutMix 的出处。解决的问题是 Cutout 会浪费像素、MixUp 产生不自然的图像。
  对本课的价值在于它的**分析部分**：CutMix 让模型学到更好的"可定位特征"，
  这解释了为什么分类上的增强能迁移到检测预训练上。
- ★ **Zhang et al. 2018, _mixup: Beyond Empirical Risk Minimization_** —
  MixUp 的出处，解决的问题是经验风险最小化会记住训练样本。
  值得读它的**理论动机**（vicinal risk minimization），因为它给了"为什么混合两个样本是合理的"
  一个不那么随意的解释。**注意：它的标签插值在检测里不成立**，检测实现是"框取并集"。
- **DeVries & Taylor 2017, _Improved Regularization of CNNs with Cutout_** —
  最简单的遮挡增强。解决遮挡鲁棒性问题。读它是为了理解"遮挡类增强"这一支的起点与局限。
- **Zhong et al. 2020, _Random Erasing Data Augmentation_** — Cutout 的同期工作，
  区别在于擦除区域填随机值而非常数，且尺寸/长宽比随机。
- **Chen et al. 2020, _GridMask Data Augmentation_** — 用规则网格遮挡，
  解决 Cutout"可能把整个目标遮没"的问题。**对小目标检测尤其相关**——
  随机大块遮挡对 8×8 的目标是灾难性的。
- **Kisantal et al. 2019, _Augmentation for Small Object Detection_** —
  **专门针对小目标的 copy-paste**：把小目标在同一张图内复制多份。
  解决的问题是小目标正样本太少。与 C57 直接呼应，是"数据侧解小目标"的代表工作。
- **Chen et al. 2020, _Stitcher: Feedback-driven Data Provider for Object Detection_** —
  按小目标损失的反馈动态决定是否拼图，是"自适应增强强度"的一个好例子。

---

## 二 · 自动增强策略搜索 · Learned Augmentation Policies

- ★ **Zoph et al. 2020, _Learning Data Augmentation Strategies for Object Detection_** —
  **AutoAugment 的检测版，本课最相关的策略搜索工作**。
  解决的问题是"增强策略该怎么组合"这件事人工调不动。
  最有价值的产出不是搜出来的策略本身，而是它的**搜索空间设计**：
  它明确区分了 color 操作、geometric 操作、以及**只作用于 bbox 内部的操作**——
  最后这一类是检测特有的，值得单独理解。
- ★ **Cubuk et al. 2020, _RandAugment: Practical Automated Data Augmentation with a Reduced Search Space_** —
  解决 AutoAugment 搜索成本过高的问题：把搜索空间压缩到两个超参（N 个算子、幅度 M），
  直接网格搜索即可。**实践价值极高**——它意味着你不需要跑策略搜索，
  只要调两个数。也是"增强强度应随模型容量与数据量增大"这一规律的重要证据来源。
- **Cubuk et al. 2019, _AutoAugment: Learning Augmentation Policies from Data_** — 这条线的起点。
  历史价值大于实用价值（搜索成本巨大），但它确立了"增强策略可以被优化"这个观念。
- **Müller & Hutter 2021, _TrivialAugment: Tuning-free Yet State-of-the-Art Data Augmentation_** —
  **一个很有价值的"负结果"**：随机挑一个算子、随机挑一个幅度，效果就能追平精心搜索的策略。
  读它是为了保持怀疑：**在投入策略搜索之前，先确认简单基线真的不够。**
- **Lim et al. 2019, _Fast AutoAugment_** — 用密度匹配加速搜索，理解"搜索目标可以不是最终精度"这个技巧。

---

## 三 · 增强为什么有效 · Mechanism & Theory

- ★ **Gontijo-Lopes et al. 2020, _Affinity and Diversity: Interpreting the Effects of Data Augmentation_** —
  **本课 05 模块方法论最重要的理论支撑。** 它提出用两个可测量的量来刻画一个增强：
  **affinity**（增强后的数据离原分布有多远，用原模型在增强数据上的表现衡量）与
  **diversity**（增强带来多少新变化，用训练损失衡量）。
  解决的问题是"为什么有的增强有用有的没用"——答案是两者需要平衡。
  **有了这两个量，你可以在开训之前就粗筛掉一批增强**，这是极高的实用价值。
- ★ **Hendrycks & Dietterich 2019, _Benchmarking Neural Network Robustness to Common Corruptions and Perturbations_（ImageNet-C）** —
  **鲁棒性评测的事实标准**，也是本课 02 模块噪声/模糊/天气腐蚀类型的来源。
  解决的问题是"鲁棒性"以前没有统一度量。它的 15 种腐蚀 × 5 个严重度的设计
  可以直接搬来做检测的鲁棒性切片。**注意它明确警告不要拿这些腐蚀去做训练增强**
  （会变成在测试集上训练），这个方法论警示很重要。
- ★ **Hendrycks et al. 2020, _AugMix: A Simple Data Processing Method to Improve Robustness and Uncertainty_** —
  解决"强增强会让训练分布偏离真实分布"的问题：把多条增强链的结果混合，
  再用一致性损失约束。**思路可以直接迁移到检测**，也是理解"增强 + 一致性正则"这条线的入口。
- **Hernández-García & König 2018, _Data Augmentation Instead of Explicit Regularization_** —
  论证增强可以替代 weight decay 与 dropout。解决的问题是"增强到底算不算正则化"。
  对本课的价值：理解为什么增强强度与模型容量、训练时长存在交互。
- **Chen, Dobriban & Lee 2020, _A Group-Theoretic Framework for Data Augmentation_** —
  用群论刻画"增强注入了什么不变性"，并证明它等价于一种方差缩减。
  **这是"增强 = 先验注入"这个说法最严格的版本**，虽然理论性强，但读懂第 2 节就够用。
- **Geirhos et al. 2019, _ImageNet-trained CNNs are Biased Towards Texture_** —
  解释了为什么颜色/纹理类增强能显著改变模型行为。
  对 TSR 的启示很直接：**如果模型主要靠纹理，那颜色抖动就不只是"轻微扰动"。**

---

## 四 · 天气、光照与相机物理 · Physics-Based Synthesis

- ★ **Narasimhan & Nayar 2002/2003, _Vision and the Atmosphere_ / _Contrast Restoration of Weather Degraded Images_** —
  **大气散射模型 `I = J·t + A(1−t)` 的权威来源**，本课 02 模块雾化合成的公式出处。
  解决的问题是把"天气对成像的影响"变成可计算的物理模型而非经验滤镜。
  读法：只需要理解透射率 `t = exp(−β·d)` 与大气光 A 这两个量的物理含义。
- ★ **He, Sun & Tang 2009, _Single Image Haze Removal Using Dark Channel Prior_** —
  去雾的经典。虽然是**反问题**，但读它能让你彻底理解散射模型的每一项，
  以及**大气光 A 的正确估计方式**（取暗通道最亮的前 0.1% 像素，而不是全图最亮点）——
  这个细节直接影响你合成的雾像不像。
- ★ **Sakaridis, Dai & Van Gool 2018, _Semantic Foggy Scene Understanding with Synthetic Data_（Foggy Cityscapes）** —
  **合成天气用于训练的标杆工作**，解决的问题是恶劣天气的真实标注数据太少。
  它证明了用物理模型合成的雾**确实能提升真实雾天的性能**，这是本课 02 模块"合成有用"的主要证据。
  同时它也诚实地展示了合成的局限，值得连同局限一起读。
- **Halder, Lalonde & Charette 2019, _Physics-Based Rendering for Improving Robustness to Rain_** —
  雨的物理渲染（雨滴的折射与运动轨迹），比"叠白色条纹"真实得多。
  解决的问题：雨天的域差不只是"多了些线"，还包括雨滴的透镜效应与路面反光。
- **Garg & Nayar 2006, _Photorealistic Rendering of Rain Streaks_** — 雨条纹外观模型的原始工作。
- **Li et al. 2019, _Benchmarking Single Image Dehazing and Beyond (RESIDE)_** —
  合成雾与真实雾配对的数据集。**它的价值在于让你能量化"合成雾与真实雾差多远"**，
  这正是判断合成增强是否值得做的关键证据。
- **Nah, Kim & Lee 2017, _Deep Multi-scale CNN for Dynamic Scene Deblurring_（GoPro 数据集）** —
  运动模糊的真实数据来源。**它的模糊是通过对高帧率序列求平均得到的**，
  这个构造方式本身就是最物理正确的运动模糊合成方法，比线段核更真实。
- **Meingast, Geyer & Sastry 2005, _Geometric Models of Rolling-Shutter Cameras_** —
  **卷帘快门畸变的几何模型**，本课 02 模块卷帘快门实现的依据。
  解决的问题：CMOS 逐行曝光下运动物体的几何该怎么算。车载场景必读，因为车载相机几乎全是卷帘快门。
- **Buckler, Jayasuriya & Sampson 2017, _Reconfiguring the Imaging Pipeline for Computer Vision_** 与
  **Diamond et al. 2021, _Dirty Pixels: Towards End-to-End Image Processing and Perception_** —
  ISP 对视觉任务的影响。解决的问题是"训练数据的 ISP 与部署端的 ISP 不同"这个隐形域差。
  **这是一条很少被讨论但在量产系统里真实存在的域差来源。**

---

## 五 · 域随机化与 sim2real · Domain Randomization

- ★ **Tobin et al. 2017, _Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World_** —
  **域随机化的出处**。核心主张：把仿真参数随机化到足够宽，真实世界就成了训练分布的一个样本。
  解决的问题是仿真数据与真实数据的域差。读它是为了理解 DR 的**逻辑前提**——
  以及这个前提什么时候不成立（随机化的维度必须覆盖真实变化的维度）。
- ★ **Tremblay et al. 2018, _Training Deep Networks with Synthetic Data: Bridging the Reality Gap by Domain Randomization_** —
  **DR 用在目标检测上的代表作**，且用的是车辆检测这个与本课高度相关的任务。
  它的关键发现：DR 合成数据 + 少量真实数据微调，能超过纯真实数据训练。
  这个"合成打底 + 真实微调"的配方对稀有场景（暴雪、极端逆光）极有参考价值。
- **Prakash et al. 2019, _Structured Domain Randomization_** —
  **对纯 DR 的重要修正**：完全随机的物体摆放会破坏场景的结构先验（车在路上、标志在路侧），
  加上结构约束后效果显著更好。**这正是本课 03 模块 Copy-Paste "位置合法性"约束的理论依据。**
- **Richter et al. 2016, _Playing for Data: Ground Truth from Computer Games_** —
  用游戏引擎生成带标注的驾驶数据。理解合成数据这条路的上限与成本结构。

---

## 六 · 库、实现与工业默认值 · Tooling

- ★ **Buslaev et al. 2020, _Albumentations: Fast and Flexible Image Augmentations_（Information 期刊）+ 官方文档** —
  **事实标准的增强库，本课 🧪 胶囊的主要目标**。
  解决的问题：让 bbox / mask / keypoint 与图像同步变换，且速度足够快。
  读法：论文只需扫一遍，**重点读文档里的 `BboxParams`**——
  尤其是 `min_area`、`min_visibility`、`label_fields` 这三个参数，
  它们直接对应本课 01 模块的越界规则。**很多人用了两年 Albumentations 都没设过 `min_visibility`。**
- ★ **Ultralytics YOLO 官方文档的 Hyperparameters / Augmentation 页 + `ultralytics/data/augment.py` 源码** —
  **工业默认值的一手来源**。`hsv_h=0.015 / hsv_s=0.7 / hsv_v=0.4`、`degrees=0.0`、
  `translate=0.1`、`scale=0.5`、`fliplr=0.5`、`mosaic=1.0`、`close_mosaic=10`、
  `mixup` 随模型尺寸变化——**每个默认值背后都有一个可以追问的"为什么"**，
  而 `degrees` 默认为 0（不旋转）与 `fliplr` 默认 0.5 的组合尤其值得思考。
  源码里 `RandomPerspective` 与 `Mosaic` 两个类是本课 01/03 模块的工业对照。
- ★ **MMDetection 文档的 _Customize Data Pipelines_ 与 `mmdet/datasets/transforms/`** —
  **pipeline 式增强配置的代表**，也是理解"训练 pipeline 与测试 pipeline 必须分开"这一纪律的最好例子。
  它把每个 transform 需要读写哪些 key 显式声明出来，这种设计对排查"框没跟着变"类 bug 极有帮助。
- **torchvision `transforms.v2` 文档** — v2 相对 v1 的关键改进就是**原生支持 bbox/mask 同步变换**。
  读它的迁移指南能理解为什么 v1 在检测上不够用。
- **Kornia 与 NVIDIA DALI 文档** — GPU 侧增强的两个主要选项。
  解决 CPU 成为训练瓶颈的问题。读法：先看它们的 benchmark 与**适用条件**，
  再决定要不要迁——GPU 已是瓶颈时搬过去反而更慢。
- **PyTorch 文档 _Randomness in DataLoader_ 与 `worker_init_fn` 说明** —
  ★ **worker RNG 事故的权威解释**。解决的问题是多进程数据加载下随机数状态的正确管理。
  **这一页很短，但不读它你迟早会踩这个坑**，而且踩了很难发现（不报错，只是多样性下降）。

---

## 七 · TTA、框融合与后处理 · Fusion

- ★ **Solovyev, Wang & Gabruseva 2021, _Weighted Boxes Fusion: Ensembling Boxes from Different Object Detection Models_** —
  **WBF 的出处，本课 04 模块的实现依据**。
  解决的问题：NMS 在融合多个模型/多次 TTA 的结果时会**丢弃所有非最高分框**，
  等于扔掉了其他来源提供的定位信息。WBF 改为加权平均坐标，定位精度显著更好。
  读法：算法本身只有半页，重点理解它与 NMS 的适用边界——**单模型单次推理时 NMS 仍然是对的**。
- **Bodla et al. 2017, _Soft-NMS: Improving Object Detection With One Line of Code_** —
  理解"抑制 vs 删除"这个思路差异的最佳材料。密集场景下召回更高。
- **Shanmugam et al. 2021, _Better Aggregation in Test-Time Augmentation_** —
  **TTA 的聚合方式本身是可以学的**，简单平均不是最优。
  解决的问题：不同增强视角的可靠性不同，不该等权。
- **Jocher et al., Ultralytics 的 TTA 实现（`--augment`）** — 工业界 TTA 的具体做法
  （多尺度 + 水平翻转 + 结果拼接后 NMS）。**注意在 TSR 上翻转 TTA 有语义风险**，
  这是本课 01 与 04 模块的交汇点。

---

## 八 · 消融、显著性与评测方法学 · How to Prove It Works

> 这一组是本课 05 模块的骨架，**也是绝大多数人跳过、因而最能拉开差距的一组**。

- ★ **Bouthillier et al. 2021, _Accounting for Variance in Machine Learning Benchmarks_（MLSys）** —
  **本课 05 模块最重要的一篇。** 它系统地拆解了 ML 实验中的**各种方差来源**
  （随机种子、数据划分、数据顺序、初始化、硬件非确定性），
  并给出一个关键结论：**只改种子重复多次，比只跑一次然后调参更能得到可靠结论**。
  解决的问题：怎么在有限算力下得到可信的比较。**读完你会重新设计自己的消融流程。**
- ★ **Dodge et al. 2019, _Show Your Work: Improved Reporting of Experimental Results_** —
  提出报告"**期望最优性能 vs 调参预算**"曲线而不是单个最好结果。
  解决的问题：不同方法调参预算不同导致的不公平比较。
  **这直接对应本课的"同预算对比"原则。**
- ★ **Henderson et al. 2018, _Deep Reinforcement Learning that Matters_** —
  虽然是 RL 领域，但它对"种子方差被系统性忽视"的论证是跨领域通用的，
  而且写得非常尖锐。**读它是为了建立一种健康的怀疑**：
  看到"+0.3 mAP 的提升"时，第一反应应该是"跑了几个种子"。
- ★ **Benjamini & Hochberg 1995, _Controlling the False Discovery Rate_** —
  **多重比较校正的标准方法（BH / FDR）**，比 Bonferroni 更适合切片评测这种场景
  （切片多、且我们能容忍一定比例的假阳性）。
  解决的问题：切 12 个片就会有约 1 个纯靠运气"显著"。
- **Demšar 2006, _Statistical Comparisons of Classifiers over Multiple Data Sets_** —
  多数据集/多切片上比较方法的标准流程（Friedman 检验 + post-hoc）。
  解决的问题：当你有 10 个切片而不是 1 个总指标时，该怎么给出一个整体结论。
- **Efron & Tibshirani, _An Introduction to the Bootstrap_（第 1–6 章）** —
  bootstrap 置信区间的原理。mAP 没有解析方差公式，bootstrap 是给它加误差棒的标准手段。
- **Lin et al. 2014, _Microsoft COCO: Common Objects in Context_** 与
  **COCO 评测代码（`pycocotools`）** — mAP 的精确定义与**按尺寸分桶（AP_S / AP_M / AP_L）的官方口径**。
  本课 05 模块的切片评测就是它的推广。
- **Padilla et al. 2021, _A Comparative Analysis of Object Detection Metrics with a Companion Open-Source Toolkit_** —
  把各种 mAP 变体（VOC 11 点 / COCO 101 点 / 面积口径）讲清楚。
  解决的问题：不同工具算出的 mAP 不一样，跨论文比较前必须先对齐口径。
- **Bolya et al. 2020, _TIDE: A General Toolbox for Identifying Object Detection Errors_** —
  把 mAP 损失拆成分类错/定位不准/重复/背景误检/漏检，并算出"修好每一类能涨多少"。
  **它是把"增强改变了什么"归因到具体误差类型的最强工具**，与切片评测互补。

---

## 九 · TSR 场景的数据与鲁棒性 · Traffic Sign Specific

- ★ **Zhu et al. 2016, _Traffic-Sign Detection and Classification in the Wild_（TT100K）** —
  **中国交通标志的代表性数据集**，小目标 + 长尾的典型。
  它的类别分布图是理解"为什么 TSR 必须做 Copy-Paste"最直观的材料：
  **大量类别的实例数是个位数。**
- ★ **Temel et al. 2019, _CURE-TSR / CURE-TSD: Challenging Unreal and Real Environments for Traffic Sign Recognition_** —
  **本课 02 模块最相关的 TSR 数据集**：它系统地在 12 种挑战条件
  （雨、雪、雾、暗光、眩光、镜头污渍、编码伪影、模糊…）× 5 个等级下评测 TSR。
  解决的问题：把"恶劣条件下 TSR 会掉多少"从传闻变成数字。
  **拿它的条件清单去反推你需要哪些增强，是 05 模块方法论的现成范例。**
- **Stallkamp et al. 2012, _Man vs. Computer: Benchmarking Machine Learning Algorithms for Traffic Sign Recognition_（GTSRB）** —
  最经典的交通标志分类基准。对本课的价值：它的**类内变化来源清单**
  （光照、遮挡、褪色、视角、运动模糊）几乎就是一份增强需求说明书。
- **Ertler et al. 2020, _The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale_** —
  全球尺度的标志数据集。**它让"区域差异是一种域差"变得可测量**——
  同一形状在不同国家含义不同，这是增强解决不了、只能靠数据解决的问题（对应 C58）。
- **Hnewa & Radha 2021, _Object Detection Under Rainy Conditions for Autonomous Vehicles: A Review_** —
  恶劣天气下自动驾驶检测的综述。**解决"该做去雨预处理还是该做雨天增强"这个实际决策**——
  综述给出的答案倾向于后者，因为预处理会引入新的域差且增加延迟。
