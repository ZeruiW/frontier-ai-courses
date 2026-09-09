# C74 参考文献 · 3D 高斯溅泼与实时渲染

按「先读哪一篇」排列。每条给出**它解决的问题**与**本课用到它的哪一部分**。

---

## 一、必读的三篇

### 1. Kerbl, Kopanas, Leimkühler, Drettakis — *3D Gaussian Splatting for Real-Time Radiance Field Rendering*
SIGGRAPH 2023. https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/

本课的主论文。**读法建议**：§4（表示）与 §5.1（协方差参数化）对应本课模块 02；
§5.2（自适应密度控制）对应模块 04；§6（光栅化器）对应模块 03。

**注意 §6 的信息量远小于代码**。论文没有说 tile 尺寸为什么是 16×16、
排序键的低 32 位为什么用位重解释而不是量化、
反向为什么要重放 `last_contributor` —— 这些都只在
`submodules/diff-gaussian-rasterization/cuda_rasterizer/{forward,backward}.cu` 里。
本课模块 03 把它们讲清楚了，但你应该自己读一遍那两个文件。

**官方实现**：https://github.com/graphdeco-inria/gaussian-splatting

---

### 2. Zwicker, Pfister, van Baar, Gross — *EWA Splatting*
IEEE TVCG 2002. （前作：*Surface Splatting*, SIGGRAPH 2001）

**仿射近似的出处**，比 3DGS 早 21 年。$\Sigma' = J\Sigma J^\top$ 与
「加一个低通滤波防止亚像素基元走样」这两件事都来自这里。

本课模块 02 §3–§5 基本是这篇的现代重述。
**而模块 02 §4 的结论（大张角下投影协方差不存在）在这篇里没有** ——
EWA 的场景是表面渲染，基元本来就小，所以那个失效模式不会出现。
3DGS 允许很大的高斯，于是把它暴露出来了。

---

### 3. Max — *Optical Models for Direct Volume Rendering*
IEEE TVCG 1995.

体渲染积分的标准参考。本课模块 §1 的三个物理量与 $T$ 的指数形式来自这里。
**它也说清了 α 合成与体渲染的关系**：α 合成不是「体渲染的近似」，
而是体渲染积分在分段常数假设下的**离散形式**，
而 $\alpha_i = 1-e^{-\sigma_i\delta_i}$ 是两者之间唯一的翻译。

更早的源头：Kajiya & Von Herzen, *Ray Tracing Volume Densities*, SIGGRAPH 1984；
以及 α 合成本身：Porter & Duff, *Compositing Digital Images*, SIGGRAPH 1984。

---

## 二、作为对照的 NeRF 一侧

### Mildenhall, Srinivasan, Tancik et al. — *NeRF*
ECCV 2020. https://www.matthewtancik.com/nerf

**只需要读它的式 (1)–(3)**，那就是本课模块 01 的内容（用了同一套公式）。
本课的选课路径跳过了 NeRF，所以模块 01 自带了这部分地基。

值得注意的是本课模块 01 §7 那张对照表里的一行：
**NeRF 输出 σ 而 3DGS 直接存 α**，所以 NeRF 有「步长」概念而 3DGS 没有。
这个差别的后果是「分裂一个高斯真的改变渲染结果」（模块 04 §3）。

### Müller, Evans, Schied, Keller — *Instant Neural Graphics Primitives*
SIGGRAPH 2022.

哈希网格。**本课不讲**，但它是理解「3DGS 到底赢在哪」的重要对照：
Instant-NGP 已经把 NeRF 的训练降到秒级，
而 3DGS 的优势在**渲染**（毫秒级 vs 几十毫秒到秒级），
以及不需要任何神经网络推理。

---

## 三、把本课的每个模块往下推一层

### 模块 02 · 基元与投影

- **Huang, Yu, Chen, Geiger, Gao — *2D Gaussian Splatting for Geometrically Accurate Radiance Fields*.** SIGGRAPH 2024.
  把第三个轴去掉，改成射线-平面**精确求交**。于是本课模块 02 §4 那个仿射近似问题
  **整体消失**，代价是表示不了体积性物质。要几何/网格就用这个（接 C75）。
  https://surfsplatting.github.io/

- **Yu, Chen, Antic et al. — *Mip-Splatting: Alias-free 3D Gaussian Splatting*.** CVPR 2024.
  本课模块 02 §5 那个 `cov += 0.3f` 的常数是这篇的出发点。
  它换成一个 3D 平滑滤波 + 2D Mip 滤波，让结果不随分辨率变化。
  **如果你的 3DGS「训练视角很好、换分辨率就掉」，先读这篇。**

- **Shoemake — *Animating Rotation with Quaternion Curves*.** SIGGRAPH 1985.
  四元数的经典入门。本课模块 02 §2「不加归一化约束、梯度在模长方向为零」
  这件事的背景。

### 模块 03 · 光栅化

- **Radl, Steiner, Parger et al. — *StopThePop: Sorted Gaussian Splatting for View-Consistent Real-time Rendering*.** SIGGRAPH 2024.
  修 popping。本课模块 03 §1 与 §7 引用了它的折中方案（分层排序，约 2 倍渲染时间）。
  同时它给了 popping 的定量分析 —— 比本课的定性描述更细。

- **Ye, Turkulainen, et al. — *gsplat: An Open-Source Library for Gaussian Splatting*.** JMLR 2025.
  **比官方实现更适合读**。把 `isect_tiles` / `isect_offset_encode` /
  `rasterize_to_pixels` 拆成了独立可调用的算子，所以你可以逐步验证本课模块 03 的每一步。
  https://github.com/nerfstudio-project/gsplat

- **Merrill & Grimshaw — *High Performance and Scalable Radix Sorting*.** Parallel Processing Letters, 2011.
  GPU 基数排序。本课模块 03 §2 的 $O(P)$ vs $O(P\log P)$ 与「一次调用排好两个键」
  背后就是 CUB 的这套实现。

- **Feng, Wang, et al. — *FlashGS / 各类光栅化优化*.** 2024–2025.
  多篇工作在改本课模块 03 的成本结构（减少冗余的 (高斯,tile) 对、更好的负载均衡）。
  读它们之前先确认你理解了本课的那张操作计数表 —— 否则很难判断某个优化到底省了哪一项。

### 模块 04 · 密度控制

- **Zhang, Zhang, et al. — *Pixel-GS: Density Control with Pixel-aware Gradient*.** ECCV 2024.
  改梯度的**聚合方式**（按覆盖像素数加权）。本课模块 04 §6 的第一行。

- **Bulò, Porzi, Kontschieder — *Revising Densification in Gaussian Splatting*.** ECCV 2024.
  改**操作**：推导让分裂近似保持渲染结果不变的修正公式。
  对应本课模块 01 §7 那个观察（3DGS 没有步长，所以分裂不是等价变换）。

- **Fang & Wang — *Mini-Splatting: Representing Scenes with a Constrained Number of Gaussians*.** ECCV 2024.
  改**控制方式**：阈值 → 预算。本课模块 04 §6 与 §8 反复推荐的方向，
  理由是那个复合增长的指数敏感性。

- **Kheradmand, Rebain, Sharma et al. — *3D Gaussian Splatting as Markov Chain Monte Carlo*.** NeurIPS 2024.
  改**框架**：总数固定，克隆/分裂/剪枝换成重定位 + 噪声注入。
  它顺带消掉了本课模块 04 §5 那个「145 次带预热的重启」的瞬变。

- **Mallick, Goel, Kerbl et al. — *Taming 3DGS: High-Quality Radiance Fields with Limited Resources*.** SIGGRAPH Asia 2024.
  给定预算下的密度控制 + 一堆工程优化。**如果你要把 3DGS 上生产，这篇比原论文更有用。**

### 模块 05 · 外观与动态

- **Ramamoorthi & Hanrahan — *An Efficient Representation for Irradiance Environment Maps*.** SIGGRAPH 2001.
  球谐的带限分析。本课模块 05 §3 那个「角分辨率」概念的来源。
  **注意这篇讲的是 irradiance（已被余弦核低通过），所以 deg 2 就够** ——
  而 3DGS 的 SH 直接表示**出射辐射**，那是一个高频得多的量。
  这正是本课实测「$125^\circ/(\ell+1)$ 而不是 $180^\circ/(\ell+1)$」的背景。

- **Wu, Yi, Fang et al. — *4D Gaussian Splatting for Real-Time Dynamic Scene Rendering*.** CVPR 2024.
  HexPlane 编码 4D 时空。本课模块 05 §6 的内存账正是这类工作必须解决的问题。

- **Yang, Gao, Zhou et al. — *Deformable 3D Gaussians for High-Fidelity Monocular Dynamic Scene Reconstruction*.** CVPR 2024.
  用一个小 MLP 把 $(xyz, t)$ 映到形变。另一种参数化，同样让 SH 静态。

- **Jiang, Tu, Liu et al. — *GaussianShader: 3D Gaussian Splatting with Shading Functions for Reflective Surfaces*.** CVPR 2024.
- **Gao, Gu, Lin et al. — *Relightable 3D Gaussian*.** ECCV 2024.
  把 SH 换成显式 BRDF + 法向 + 环境光。**代价是引入逆渲染的全部歧义，PSNR 通常反而下降** ——
  本课模块 05 §1 与 §7 的依据。

- **Fan, Wang, Yu et al. — *LightGaussian: Unbounded 3D Gaussian Compression*.** NeurIPS 2024.
- **Niedermayr, Stumpfegger, Westermann — *Compressed 3D Gaussian Splatting*.** CVPR 2024.
  压缩。对应本课模块 05 §4 的两类手段。读它们时留意**顺序**：
  先剪高斯再降 SH 阶再量化，反过来做会白费力气。

---

## 四、规范与工具

- **COLMAP**（Schönberger & Frahm, CVPR 2016）https://colmap.github.io/
  3DGS 的标准输入来源：`sparse/0/{cameras,images,points3D}.bin`。
  它的相机模型与内参约定见 C72 模块 01；SfM 本身见 C75。

- **nerfstudio** https://docs.nerf.studio/
  训练 + 可视化 + 导出的完整流程，内置 `splatfacto`（基于 gsplat）。
  **上手 3DGS 的推荐路径**：先用它跑通一个自己的场景，再回来读本课的模块 03/04。

- **`.spz` / SOG 格式**（Niantic）https://github.com/nianticlabs/spz
  3DGS 的交换格式，约 10× 无感压缩。对应本课模块 05 §4。

- **SuperSplat** https://superspl.at/editor
  浏览器里的 3DGS 查看/编辑器。**用来做本课模块 05 §5 那个浮物检测最方便** ——
  自由转视角，浮物一眼就能看到。

---

## 五、本课程内部的依赖

| 课程 | 关系 |
|---|---|
| **C72 · 多视角几何** | **硬前提**。相机模型、内外参、投影的雅可比 |
| **C73 · 3D 表示与点云** | 离散表示的另一侧。「量化误差」在本课不存在，代价是没有规则网格可卷积 |
| **C75 · 三维重建与生成** | 提供 3DGS 的输入（SfM 位姿 + 稀疏点云）；接收 3DGS 的输出（网格提取）|
| **C36 · GPU 内核与性能工程** | 本课讲光栅化的算法结构，C36 讲 CUDA 实现 |
| **C28 · 扩散与流前沿** | 生成式的 3D（多视角扩散、SDS）在 C75，本课的 3DGS 是纯拟合方法 |
