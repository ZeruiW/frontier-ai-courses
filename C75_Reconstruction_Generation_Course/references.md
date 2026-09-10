# C75 参考文献 · 三维重建与 3D 生成

按「先读哪一篇」排列。每条给出**它解决的问题**与**本课用到它的哪一部分**。

---

## 一、必读的三本 / 三篇

### 1. Hartley & Zisserman, *Multiple View Geometry in Computer Vision*（2nd ed., 2004）
本课模块 01 与 02 的底座。**读法建议**：第 9–11 章（对极几何与三角测量）是 C72 的内容；
本课需要的是**第 18 章（束调整）** 与第 19 章（自标定）。

**注意第 18 章没有讲 gauge**（它只提了一句「解到一个相似变换」）。
gauge 的完整处理在下一条。

### 2. Triggs, McLauchlan, Hartley, Fitzgibbon — *Bundle Adjustment — A Modern Synthesis*
Vision Algorithms 1999 (LNCS 1883), 2000.

**本课模块 01 第 4、7 节的直接来源。** 它是唯一系统讲清 gauge freedom 的经典文献：
零空间为什么是 7 维、为什么协方差依赖 gauge 的选择、以及为什么推荐用**投影**而不是
固定具体参数（因为固定参数会让协方差带上「哪个相机被固定了」的偏见）。

**如果你只读本课参考文献里的一篇，读这一篇。**

### 3. Schönberger & Frahm — *Structure-from-Motion Revisited*（CVPR 2016）
COLMAP 的论文。它把「增量式 SfM 的每一个工程决定」都写出来了：
初始化对的选择、`Homography vs Essential` 的模型选择（本课模块 01 第 6 节）、
三角化的角度判据、以及什么时候跑全局 BA。

**代码比论文信息量更大**：`src/colmap/estimators/` 与 `src/colmap/controllers/incremental_mapper.cc`。

---

## 二、稠密立体（模块 02）

- **Furukawa & Hernández — *Multi-View Stereo: A Tutorial*.** Foundations and Trends in CG&V, 2015.
  最好的 MVS 综述。本课模块 02 的结构（代价体 → 聚合 → 深度图 → 融合）来自这里。

- **Collins — *A Space-Sweep Approach to True Multi-Image Matching*.** CVPR 1996.
  **平面扫掠的出处。** 本课模块 02 第 1 节。

- **Hirschmüller — *Stereo Processing by Semiglobal Matching and Mutual Information*.** TPAMI 2008.
  SGM。本课第 7 节说的「非局部先验」就是它的路径代价。
  <em>而本课量出周期纹理的失败与噪声无关，正说明为什么必须有非局部项。</em>

- **Bleyer, Rhemann, Rother — *PatchMatch Stereo*.** BMVC 2011.
  **斜面假设**：把每像素的假设从「一个深度」换成「一个 3D 平面」。
  本课模块 02 第 4 节量出它的两个收益（修好倾斜 + 顺带修好周期歧义）。

- **Schönberger, Zheng, Frahm, Pollefeys — *Pixelwise View Selection for Unstructured MVS*.** ECCV 2016.
  COLMAP 的 MVS。**逐像素挑选源视图** —— 本课模块 02 第 6 节说「min 聚合最不稳健、
  正确做法是先挑再求均值」，指的就是这个。

- **Burt & Julesz — *A Disparity Gradient Limit for Binocular Fusion*.** Science 208, 1980.
  视差梯度极限 ≈ 1。本课模块 02 第 5 节说明它**不是生理限制而是几何限制**。

---

## 三、前馈回归（模块 03）

- **Eigen, Puhrsch, Fergus — *Depth Map Prediction from a Single Image using a Multi-Scale Deep Network*.** NeurIPS 2014.
  **尺度不变损失与 $\delta<1.25$ 的出处。** 本课模块 03 第 2 节指出那个 25% 是一个**约定**，
  不是从需求推出来的 —— 所以做具体应用时该按需求换阈值。

- **Ranftl, Lasinger, Hafner, Schindler, Koltun — *Towards Robust Monocular Depth Estimation*（MiDaS）.** TPAMI 2022.
  **仿射不变损失**与混合数据集训练。本课模块 03 第 3 节解释了为什么必须是「仿射」而不是「尺度」：
  混合数据集的标注定义不一致 + 深度的无界性，两件事同时逼出来的。

- **Ranftl, Bochkovskiy, Koltun — *Vision Transformers for Dense Prediction*（DPT）.** ICCV 2021.
- **Yang, Kang, Huang et al. — *Depth Anything* / *V2*.** CVPR 2024 / NeurIPS 2024.
  V2 之后出现了「metric」分支（按域微调后直接输出米）。
  **本课模块 03 第 3 节的观点：这不是解决了不可观测性，而是把统计先验<em>显式化</em>了** ——
  所以它必须按域分开用，跨域会系统性地缩放错。

- **Wang, Leroy, Cabon, Chidlovskii, Revaud — *DUSt3R: Geometric 3D Vision Made Easy*.** CVPR 2024.
- **Leroy, Cabon, Revaud — *Grounding Image Matching in 3D with MASt3R*.** ECCV 2024.
  **点图**（pointmap）。本课模块 03 第 4、5 节：焦距精确可解、3.00× 过参数化、
  以及**全局对齐就是一次束调整（秩亏 7）**。

- **Szymanowicz, Rupprecht, Vedaldi — *Splatter Image*.** CVPR 2024.
  「直接出高斯」那一档（本课模块 03 第 6 节的表格）。冗余 > 14×。

---

## 四、3D 生成（模块 04）

- **Poole, Jain, Barron, Mildenhall — *DreamFusion: Text-to-3D using 2D Diffusion*.** ICLR 2023.
  **SDS 的出处。** 本课模块 04 的全部分析对着它做。
  它报的经验值 cfg ≈ 100（图像生成只用 7.5）—— 本课把这个数字的**机制**算了出来：
  CFG 在抵消平滑造成的模式内移，而 cfg≈3 就够，100 会过冲 18%。

- **Wang, Du, Zhang et al. — *Score Jacobian Chaining*.** CVPR 2023.
  同期的等价推导，从「链式法则 + 扔掉雅可比」的角度看同一件事。
  **两篇对着读会更清楚「为什么扔掉雅可比不是近似而是换了目标」。**

- **Wang, Lu, Wang et al. — *ProlificDreamer / Variational Score Distillation*.** NeurIPS 2023.
  把「找模式」改回「采样」。**本课模块 04 第 3 节的多样性坍缩正是 VSD 要解决的问题** ——
  而本课量出的「次模式可以完全消失」说明这个问题比「概率被压平」更严重。

- **Liu, Wu, Van Hoorick et al. — *Zero-1-to-3*.** ICCV 2023.
  视角条件化。本课模块 04 第 6 节的修法 ①（仍是逐视角独立打分）。

- **Shi, Wang, Ye et al. — *MVDream: Multi-view Diffusion for 3D Generation*.** ICLR 2024.
  联合多视角先验。本课模块 04 第 6 节的修法 ②（改了先验的**联合结构**，所以更彻底）。

- **Hong, Zhang, Gu et al. — *LRM: Large Reconstruction Model for Single Image to 3D*.** ICLR 2024.
  前馈路线的对照。本课模块 04 第 7 节的三条路线对比表 —— 而它们的真正分界是
  **「需不需要 3D 数据」**。

---

## 五、网格化与评测（模块 05）

- **Lorensen & Cline — *Marching Cubes: A High Resolution 3D Surface Construction Algorithm*.** SIGGRAPH 1987.
  原版。本课模块 05 第 1 节把它的「256 → 15」算了出来，
  并数出 **46.9% 的配置含面歧义** —— 而原版对每一类固定选一种连法。

- **Chernyaev — *Marching Cubes 33*.** Technical Report CN/95-17, CERN, 1995.
- **Lewiner, Lopes, Vieira, Tavares — *Efficient Implementation of Marching Cubes' Cases with Topological Guarantees*.** JGT 2003.
  两个「一致的查表」方案。**skimage 用的是 Lewiner 变体**，所以它的输出是水密的。

- **Ju, Losasso, Schaefer, Warren — *Dual Contouring of Hermite Data*.** SIGGRAPH 2002.
  另一条路：在对偶网格上生成顶点，于是「面上怎么连」这个问题不再出现。

- **Curless & Levoy — *A Volumetric Method for Building Complex Models from Range Images*.** SIGGRAPH 1996.
  **TSDF 的出处。** 本课模块 05 第 2 节的占用率 $12r/L$ 与截断距离 $\tau$ 的双重作用。

- **Nießner, Zollhöfer, Izadi, Stamminger — *Real-time 3D Reconstruction at Scale using Voxel Hashing*.** SIGGRAPH Asia 2013.
  体素哈希。**本课算出的「分辨率越高越稀疏」正是它能工作的原因。**

- **Kazhdan, Bolitho, Hoppe — *Poisson Surface Reconstruction*.** SGP 2006.
- **Kazhdan & Hoppe — *Screened Poisson Surface Reconstruction*.** TOG 2013.
  本课模块 05 第 3 节：位置误差 $\approx R\tan\theta$、以及**法向定向决定它能不能工作**
  （净通量 $=1-2f$，50% 反向时归零）。

- **Seitz, Curless, Diebel, Scharstein, Szeliski — *A Comparison and Evaluation of Multi-View Stereo Reconstruction Algorithms*.** CVPR 2006.
  **accuracy / completeness 分开报的出处**（Middlebury MVS）。本课模块 05 第 6 节。

- **Knapitsch, Park, Zhou, Koltun — *Tanks and Temples: Benchmarking Large-Scale Scene Reconstruction*.** SIGGRAPH 2017.
  **F-score @ $\tau$ 的标准口径。** 官方脚本做了本课强调的三件事：
  crop volume 限定区域、两侧下采样到同一 voxel size、分别报 precision 与 recall。

- **Jensen, Dahl, Vogiatzis, Tola, Aanæs — *Large Scale Multi-view Stereopsis Evaluation*（DTU）.** CVPR 2014.
  同样分开报 accuracy 与 completeness（单位 mm）。

---

## 六、工具

| 工具 | 用途 | 对应本课 |
|---|---|---|
| **COLMAP** https://colmap.github.io/ | SfM + MVS 的事实标准 | 模块 01（mapper）· 模块 02（patch_match_stereo）|
| **pycolmap** | 在 Python 里读写 COLMAP 模型 | 模块 01 的诊断 |
| **OpenMVS** | 独立的 MVS + 网格化 | 模块 02 · 模块 05 |
| **Open3D** http://www.open3d.org/ | TSDF 融合、泊松重建、法向定向、评测 | 模块 05（`ScalableTSDFVolume`、`orient_normals_consistent_tangent_plane`）|
| **scikit-image** | Marching Cubes（Lewiner 变体，水密）| 模块 05 |
| **DUSt3R / MASt3R** | 前馈点图 + 全局对齐 | 模块 03 |
| **Depth Anything V2** | 单目深度（含 metric 分支）| 模块 03 |
| **threestudio** | SDS / VSD / MVDream 的统一实现 | 模块 04 |

---

## 七、本课程内部的依赖

| 课程 | 关系 |
|---|---|
| **C72 · 多视角几何** | **硬前提**。相机模型、对极几何、三角测量、PnP、$Z^2$ 律 |
| **C73 · 3D 表示与点云** | 它管「有了点云怎么处理」，本课管「点云从哪来」 |
| **C74 · 3D 高斯溅泼** | 两处接口：3DGS 的输入来自本课模块 01；从 3DGS 提网格用 C74 模块 01 的深度口径 + 本课模块 05 |
| **C28 · 扩散与流前沿** | 扩散模型本身；本课模块 04 只讲「怎么把 2D 先验用到 3D 上」 |
| **C18 · 计算机视觉** | 特征提取与匹配（本课当已知工具）|
| **C10 · 评测与测量** | 指标的校准与不确定度（本课模块 03 第 8 节提到的置信度校准）|
