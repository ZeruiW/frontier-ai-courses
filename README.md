# Frontier AI Researcher / Engineer Courses · 前沿 AI 研究工程师课程体系

**78 courses · 496 lesson pages · 496 runnable notebooks · Colab-ready, CPU-first, from-scratch.**
一套从 model evaluation 起步、长成全栈的前沿 AI 研究/工程课程体系 —— 深度 HTML 讲解 + 真实可跑 notebook，纯 numpy/CPU 优先、优雅降级到真实框架/GPU。

📖 中文 → [跳转](#中文) · 🇬🇧 English → [jump](#english)

---

<a name="中文"></a>
## 中文

### 目录
- [这是什么](#zh-what)
- [快速开始](#zh-quickstart)
- [课程总览（78 门）](#zh-catalog)
- [每门课的格式](#zh-format)
- [学习路径建议](#zh-paths)
- [仓库结构](#zh-layout)
- [关于 GPU / Colab / 量化](#zh-gpu)
- [环境与依赖](#zh-env)
- [构建历史](#zh-history)

<a name="zh-what"></a>
### 这是什么

这是一套面向 **frontier-lab AI 研究科学家 / 研究工程师**的自学课程体系，从最初的「模型评测」技能栈起步，逐步扩展为覆盖 LLM 内核、后训练、推理系统、Agent 工程、多模态、分布式训练、模型压缩、可解释性、安全、隐私、图机器学习、推荐系统、云上部署乃至专利与开源合规的全栈内容。

每一门课都遵循同一套「深」标准：
- **HTML 讲解**：中文叙述 + 英文术语，8–9 个编号小节，每节配 callout（直觉/警告/危险/论文引用）、双栏对照、表格、ASCII 图、数学推导，末节固定是「研究前沿与开放问题」。
- **notebook**：与讲解一一对应，纯 Python / numpy 从零实现核心机制 → 3–4 道 `✏️ 练习`（TODO 骨架 + `assert` 自测判分）→ `📖 参考答案` → `🧪 真实数据/真实 API 对照胶囊`（把当天学到的东西翻译成能在真机上原样跑的代码）。
- **术语词典**（`glossary.md`，≥12KB）与**参考清单**（`references.md`，≥8KB，标★的是必读）。

**没有 GPU、没有网络、没有 API key，绝大多数课程也能从零跑通** —— 核心机制都是用 numpy 手写复现的；真实框架/模型的用法作为「对照胶囊」放在每个模块末尾，可原样复制到有 GPU 的机器（或 Colab）上验证。少数确实需要真实模型的课程（VLM、Agent computer-use 等）默认用 fp16 跑在 Colab 免费的 T4（16GB）上就够，不需要量化；量化本身是另外几门课的正课内容，不会被拿来当「让模型跑起来」的默认手段。

<a name="zh-quickstart"></a>
### 快速开始

**在 Colab 里直接跑（推荐，零安装）**
打开任意一门课的 `index.html`，或直接进课程文件夹找到对应模块的 `.ipynb`，点开头的 **`Open in Colab`** 徽章即可——运行时选 T4 GPU（`Runtime → Change runtime type → T4 GPU`）就绪。

**本地跑**
```bash
git clone https://github.com/ZeruiW/frontier-ai-courses.git
cd frontier-ai-courses/C20_Frontier_Architectures_Course   # 任选一门课
pip install -r requirements.txt      # 绝大多数课只需要 numpy/pandas/jupyterlab
jupyter lab
```
先打开某模块的 `NN_讲解.html`（或先看 `index.html` 选路径），读完讲解再跑同名的 `.ipynb`。所有课程共用同一份 `assets/style.css`。

<a name="zh-catalog"></a>
### 课程总览（78 门）

#### C00–C09 · 核心 LLM / 评测主线
| 课 | 目录 | 主题 |
|----|------|------|
| C00 | `C00_VLM_Multimodal_Course/` | VLM 与多模态 AI（10 模块，全课最深） |
| C01 | `C01_LLM_Internals_Course/` | LLM 内核：从零实现 Transformer |
| C02 | `C02_Post_Training_Course/` | 后训练与对齐：SFT → RLHF/DPO → RLVR |
| C03 | `C03_LLM_Evals_Course/` | 评测科学：基准、统计与 LLM Judge |
| C04 | `C04_AI_Agents_Course/` | AI 智能体与 agentic 评测 |
| C05 | `C05_Safety_Evals_Course/` | 前沿模型安全评估与红队 |
| C06 | `C06_Interpretability_Course/` | 机制可解释性（深度样板课） |
| C07 | `C07_ML_Foundations_Course/` | ML 基础与面试数学 |
| C08 | `C08_Training_Systems_Course/` | 大模型训练与推理系统（算力/成本账本） |
| C09 | `C09_Reasoning_TTC_Course/` | 推理模型与测试时计算 |

#### C10–C19 · 评测补全与经典 AI 地基
| 课 | 目录 | 主题 |
|----|------|------|
| C10 | `C10_Eval_Measurement_Course/` | 评测数据与测量科学（IRT / 校准 / A-B 测试） |
| C11 | `C11_RAG_Retrieval_Course/` | 检索增强与长上下文评测 |
| C12 | `C12_Responsible_AI_Course/` | 负责任 AI 与社会影响评测 |
| C13 | `C13_RL_Foundations_Course/` | 强化学习地基（MDP → PG → AC → bandits） |
| C14 | `C14_DL_Theory_Data_Course/` | 深度学习理论与数据/生成媒体评测 |
| C15 | `C15_Classic_Architectures_Course/` | 经典神经网络架构（CNN/RNN/LSTM/seq2seq） |
| C16 | `C16_Generative_Models_Course/` | 生成模型（AE/VAE/GAN/扩散/Flow） |
| C17 | `C17_Classical_NLP_Course/` | 经典 NLP（word2vec/n-gram/HMM/CRF） |
| C18 | `C18_Computer_Vision_Course/` | 计算机视觉（检测/分割/自监督） |
| C19 | `C19_Bayesian_ML_Course/` | 概率与贝叶斯机器学习（MCMC/VI/GP/PGM） |

#### C20–C29 · 前沿深潜
| 课 | 目录 | 主题 |
|----|------|------|
| C20 | `C20_Frontier_Architectures_Course/` | 现代架构（RoPE/GQA/MLA/MoE/SSM） |
| C21 | `C21_Frontier_Pretraining_Course/` | 大规模预训练工程（数据/tokenizer/μP/稳定性） |
| C22 | `C22_Reasoning_RL_Course/` | 推理模型 RL（long-CoT/GRPO/PRM，o1/R1 前沿） |
| C23 | `C23_Frontier_Alignment_Course/` | 前沿对齐（CAI/可扩展监督/weak-to-strong） |
| C24 | `C24_Inference_Serving_Course/` | 高效推理与服务（vLLM/SGLang 栈） |
| C25 | `C25_Long_Context_Course/` | 长上下文与高效注意力（YaRN/稀疏/KV 压缩） |
| C26 | `C26_Frontier_Agents_Course/` | 前沿智能体（MCP/computer use/agentic RL） |
| C27 | `C27_Model_Compression_Course/` | 模型压缩与高效化（量化/GPTQ-AWQ/蒸馏/剪枝） |
| C28 | `C28_Frontier_Diffusion_Course/` | 扩散与流前沿（DiT/flow/consistency） |
| C29 | `C29_Frontier_Interp_Course/` | 前沿机制可解释性（SAE/features/steering） |

#### C30–C37 · 动手造 Agent 与系统工程
| 课 | 目录 | 主题 |
|----|------|------|
| C30 | `C30_Agent_Harness_Course/` | Agent Harness 从零（动手造 agent） |
| C31 | `C31_Coding_Agent_Course/` | 构建编码 Agent（你的 Claude Code） |
| C32 | `C32_Skills_Tools_Course/` | Skills 与工具生态（MCP server 从零） |
| C33 | `C33_Context_Memory_Course/` | 上下文工程与记忆 |
| C34 | `C34_Agent_Orchestration_Course/` | 多智能体编排与生产化 |
| C35 | `C35_Speech_Audio_Course/` | 语音与音频（ASR/codec/TTS/语音 LLM） |
| C36 | `C36_GPU_Kernels_Course/` | GPU 内核与性能工程（手写 FlashAttention） |
| C37 | `C37_MLOps_Course/` | MLOps 与生产生命周期 |

#### C38–C47 · 补缺课（研究工程师能力树缺口）
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C38 | `C38_Frameworks_Accel_Course/` | 深度学习框架与加速计算（PyTorch/JAX/autograd/compile/Triton） | 全栈 numpy 留下的「真实框架」空白 |
| C39 | `C39_Distributed_Training_Course/` | 分布式训练工程（NCCL/FSDP/3D 并行/容错） | C08 只给成本模型，缺可操作工程 |
| C40 | `C40_Research_Methodology_Course/` | 研究方法论与科学实践（复现/消融/写作/品味） | 「做研究本身」的元技能 |
| C41 | `C41_Deep_RL_Course/` | 深度强化学习与决策（DQN/PPO/SAC/offline/世界模型） | C13 只到地基，缺控制/世界模型 |
| C42 | `C42_Learning_Theory_Course/` | 学习理论与优化理论（PAC/NTK/隐式偏置/泛化界） | 研究科学家的理论脊梁 |
| C43 | `C43_Data_Engineering_Course/` | 大规模数据工程（去重/流式/吞吐/去污染） | 数据「基础设施」手艺 |
| C44 | `C44_Adversarial_Security_Course/` | 对抗 ML 与 AI 安全攻防（对抗样本/投毒/窃取/注入） | 经典 AML 与安全工程 |
| C45 | `C45_Privacy_Trustworthy_Course/` | 隐私保护与可信 ML（DP-SGD/联邦/遗忘） | 隐私技术本身（C12 只测量） |
| C46 | `C46_Graph_ML_Course/` | 图机器学习（message passing/GCN-GAT/图 transformer） | 缺失的几何深度学习分支 |
| C47 | `C47_RecSys_Ranking_Course/` | 推荐系统与大规模排序（双塔/LTR/CTR-DLRM/序列） | 工业界最大就业面 |

#### C48–C52 · 工业岗位补缺课（对齐 LLM Research Engineer JD）
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C48 | `C48_Cloud_Deployment_Course/` | 云上部署与服务化（容器/OCI 层 · K8s 调和循环 · 灰度与自动扩缩 · 云调度与成本） | 「把服务真的放到云上」这一段一直缺 |
| C49 | `C49_Encoder_Seq2Seq_Course/` | Encoder 与 Seq2Seq（BERT/MLM · RoBERTa/ELECTRA/DeBERTa · 微调 · T5/BART） | 全谱从经典 NLP 直跳 decoder-only LLM，缺了 BERT/T5 这一代 |
| C50 | `C50_HuggingFace_Ecosystem_Course/` | HuggingFace 生态实战（Auto*/from_pretrained · tokenizers/datasets · Trainer · PEFT/TRL · accelerate/Hub） | 纯 numpy 实现之外，缺「真实生态怎么用、坑在哪」 |
| C51 | `C51_Data_Augmentation_Course/` | 文本数据增强与合成数据工程（EDA/AEDA · 回译 · Self-Instruct/Evol/Magpie · 质控 · 消融） | 「标注不够时怎么造数据、怎么验证造得有用」 |
| C52 | `C52_Industrial_Research_Practice_Course/` | 工业研究工程实务（TF/Keras 心智模型 · 跨框架权重迁移 · ONNX 导出与运行时 · 真机 GPU 工作流 · 专利与开源合规） | 一批「没有归属却天天要用」的孤儿技能 |

#### C53–C61 · 自动驾驶感知 / TSR 岗位补缺课（对齐 XPENG TSR 2D Detection JD）
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C53 | `C53_RealTime_Detectors_Course/` | 实时检测器架构（YOLO 全代演进 · 标签分配 · RTMDet · RT-DETR · 延迟-精度选型） | JD 点名的 RT-DETR / RTMDet |
| C54 | `C54_DETR_Set_Prediction_Course/` | 端到端集合预测检测（匈牙利匹配 · 集合损失 · object query · 收敛家族 · 工程实践） | 匈牙利匹配与 set prediction loss |
| C55 | `C55_TSR_Autonomous_Driving_Course/` | 交通标志识别与自动驾驶感知（数据集与法规体系 · 两级 vs 端到端 · 失效模式 · 时序融合 · 安全评测） | TSR 领域知识与自动驾驶感知语境 |
| C56 | `C56_Detection_Augmentation_Course/` | 检测数据增强工程（几何与标注同步 · 光度与域 · Mosaic/Copy-Paste · 流水线 · 消融验证） | 图像检测增强（C51 是文本增强） |
| C57 | `C57_Small_Object_Detection_Course/` | 小目标检测（IoU 尺度敏感性量化 · 多尺度架构 · NWD 与分配 · 切片推理 · TSR 物理推导） | 小目标的具体技术手段 |
| C58 | `C58_HardCase_LongTail_Course/` | 难例挖掘与长尾数据闭环（不平衡谱系 · OHEM · 主动学习触发 · 挖掘基建 · 闭环验证） | 检测语境的 hard-case / 长尾挖掘 |
| C59 | `C59_VLA_Perception_Interface_Course/` | 视觉-语言-动作模型与感知接口（VLM→VLA · 动作表示 · TSR 输出接口 · 规则约束化 · 评测上车） | JD 独有的 VLA 职责 |
| C60 | `C60_Edge_Deployment_Consistency_Course/` | 车端部署与训练-部署一致性（预处理对齐 · TensorRT · INT8 校准 · 后处理与 C++ · 延迟剖析） | TensorRT/C++ 实操与一致性调试 |
| C61 | `C61_Detection_Practice_Interview_Course/` | 检测工程实战与面试实务（实验设计 · TIDE 误差分解 · 调试手册 · 项目叙事 · 面试题库） | production 手感与面试交付能力 |

> 缺口分析与复习路线见根目录 [`INTERVIEW_PREP_XPENG_TSR.md`](INTERVIEW_PREP_XPENG_TSR.md)。

#### C62–C65 · 面试形式补缺课（HR 明确的一面三板块）
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C62 | `C62_Coding_Interview_Course/` | 编程面试实战：算法与数据结构（六步答题协议 · 双指针/滑窗/前缀和 · 哈希排序二分 · 树图与搜索 · DP 与贪心 · 模拟面试） | 全库最大缺口：前 62 门课里「链表」「双指针」零命中 |
| C63 | `C63_ML_System_Design_Course/` | ML 系统设计面试（七步框架 · 需求与指标 · 数据系统 · 建模评测 · 容量估算 · 六案例库） | C07 仅一节 system design 框架，无方法论与案例库 |
| C64 | `C64_ML_Knowledge_QA_Course/` | ML/DL 技术知识问答（三段式答法 · ML 基础 · 优化训练 · 架构 · 评估统计 · 快问快答题库） | C07 教推导，缺「60 秒讲清 + 接住追问」的广度题库 |
| C65 | `C65_ProblemSolving_Communication_Course/` | 结构化问题求解与面试沟通（估算 · 诊断归因 · 权衡决策 · 模糊需求澄清 · 白板与英文表达） | 估算/诊断/权衡/澄清/沟通均无系统覆盖 |

#### C66–C69 · Agent 评测与 AI 系统评估
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C66 | `C66_Agentic_Evaluation_Course/` | Agent 评测与基准（三层评测对象 · 基准全景 · 判分器 α/β 偏差校正 · 轨迹指标 · pass@k vs pass^k · 成本与 harness 指纹） | agent 评测此前只有 C04-06 与 C26-05 两个子模块，讲了「有这回事」没讲「怎么真做一次」 |
| C67 | `C67_LLM_Judge_Course/` | LLM-as-a-Judge 与评分模型（可判定性阶梯 · rubric 设计 · 四大偏差与去偏 · 人类上界与元评测 · BT/Elo 排名 · 奖励模型与过优化） | judge 此前只有 C03-04 一节，偏差量化/元评测/排名/RM 评测全无 |
| C68 | `C68_Eval_Infrastructure_Course/` | Eval 基础设施与线上监控（spec/runner/store/report 四层 · 数据集版本化与抽样 · 缓存键与失败语义 · CI 门禁阈值 · 漂移与数据闭环） | 「怎么把一次评测跑一千次」零覆盖；C37 MLOps 的中心是模型不是评测 |
| C69 | `C69_Agent_Security_Course/` | Agent 安全与提示注入（信任传播 · 间接注入与双 LLM 架构 · 工具供应链 · 权限四维与沙箱边界 · 出站控制 · 攻击面评测） | C05 是模型安全、C44 是对抗攻击，都不覆盖「agent 会做什么」 |

> 这批课的分工：**C66 量 agent · C67 量判分器 · C68 把评测变成基础设施 · C69 量攻击面**。
> C69 的 notebook 不包含针对任何真实系统的可用攻击载荷（攻击手法只在讲解里做机制层面描述），防御侧代码全部是真实实现。

#### C70–C71 · RAG 生产工程与提示程序化
| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C70 | `C70_RAG_Production_Course/` | RAG 生产工程（文档摄取与解析 · 分块 · 查询侧改写与路由 · 迭代与图检索 · 索引运维） | C11 讲「在索引里怎么找」；而「索引里装的是什么、查询长什么样、索引怎么维护」整整一半零覆盖（文档解析全库 1 命中、查询改写 0、增量索引 ~0） |
| C71 | `C71_Prompt_Programming_Course/` | 提示与上下文的程序化优化（prompt program · 示例选择与顺序 · 自动提示优化 · 受限解码 · 提示运维与跨模型迁移） | C03-03 是 prompt 敏感性的**测量**视角、C33 是上下文预算；把 prompt 当**可搜索、可保证、可运维的程序**这一层零覆盖（DSPy 全库 0 命中） |

> 这批课的分工：**C70 管「数据与查询怎么进来、索引怎么活下去」，C71 管「prompt 本身的结构、优化与运维」**。

#### C72 · 多视角几何与多传感器时空对齐

| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C72 | `C72_MultiView_Geometry_Course/` | 多视角几何与多传感器时空对齐（相机模型与畸变 · 标定与验收 · 对极/三角测量/单应/PnP · BEV 投影与多相机融合 · 时空对齐与跨镜关联） | C53–C61 全部依赖「像素 → 米」这条链，而这条链整体零覆盖：`对极几何` 0、`homography` 0、`PnP` 0、`视差` 0、`时钟同步` 0、`传感器融合` 1 次、`外参标定` 1 次。BEV 全库出现 45 次，却没有一处讲相机怎么投影、外参怎么标、多路怎么对齐 |

> **纯几何、无学习，且刻意不依赖 OpenCV**——投影、去畸变、DLT、标定约束、三角测量、
> PnP、IPM、时间对齐全部自己实现。
> 中心结论：$d_{\text{read}} = d\cdot H/(H-z)$，所以**地面 IPM 对交通标志不是误差大，
> 而是根本无解**（$z \ge H$）；而相对误差 $z/(H-z)$ **与距离无关**。
> 它同时是同批后续 3D 课的**共同前提**（分界线是「有没有学习成分」）。

#### C73 · 3D 表示与点云深度学习

| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C73 | `C73_3D_Representation_Course/` | 3D 表示与点云深度学习（四种表示的代价账 · 置换不变性与 max-pool · 体素化与稀疏卷积 · 3D 检测：锚框到中心点 · 分割与 3D 评测） | 热门 3D 方向整块零覆盖：`PointNet` 0、`PointPillars` 0、`体素/voxel` 0、`点云分割` 0、`双目` 0、`单目深度` 0、`SDF` 0；而 C53–C61 的所有 3D 讨论都假设这套工具已知 |

> **有学习成分，但全程 numpy、不训练任何真实网络**——因为 3D 网络的关键设计几乎都由
> **结构性质**决定（恒等式、定理、集合运算、几何计算），而这些与权重取值无关。
> 中心链条：**从 2D 到 3D，几乎每个量都从两个因子的积变成三个因子的积**，
> 而它们互相加强（网格规模 → 量化误差 → IoU → 正样本）。
> 最硬的一条结论：$\text{IoU}=q/(2-q)$ ⇒ 单轴容差恰好 $s_i/3$ ⇒
> 交通标志的容差 0.049 m 与典型标注噪声 0.05 m 之比是 **0.98×** ⇒
> **一个完美模型在标志上的 AP@IoU0.5 上界只有 0.392**（中心距离口径下是 1.000）。
> 以 C72 为前提；与 C74/C75 的分工是「离散表示 + 判别式」vs「连续表示 + 生成式」。
> 两者都明确不碰 C11（检索算法）与 C33（上下文预算），并全程复用它们的定义而不重新定义。

#### C74 · 3D 高斯溅泼（3DGS）与实时渲染

| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C74 | `C74_Gaussian_Splatting_Course/` | 3D 高斯溅泼与实时渲染（体渲染与 α 合成的地基 · 各向异性高斯基元与投影的边界 · 可微分 tile 光栅化 · 自适应密度控制与判据的可靠性 · 外观/动态与何时不该用 3DGS） | 全库 472 个讲解页里 `球谐`/`spherical harmonic` 0、`alpha compositing` 0、`tile 光栅化` 0、`EWA` 0；`体渲染`/`α 合成`/`高斯溅泼` 的少数命中全部是 C72/C73/C55 里指向本课的一句带过 |

> **一句话主张**：3DGS 全部工程价值来自**一个量级差** ——
> 它的基元 α 大（0.1–0.9）而不是小（0.01–0.05）。
> α 大 ⟹ 每像素只要十几个基元、可提前终止省掉 92%，
> 但**必须显式排序**并接受「tile 内共享顺序」的近似。
> 其余一切（协方差参数化、仿射投影、密度控制、球谐）都是为了让这个量级差能被优化出来。
>
> **因为选课路径跳过了 NeRF，体渲染与 α 合成的地基由本课模块 01 自带。**
> notebook 里**从零写出一个能出图的 tile 光栅化器**，并与逐像素暴力实现
> **逐位相等到机器精度**（为此必须先把三个近似列全）。
>
> 四处诚实修正：① 离散化误差是 **∝ 1/N²** 而不是 ∝ 1/N，
> 而**对分段常数密度 α 合成是精确的、连 N=1 都对**；
> ② 仿射近似的主变量是**张角**不是离轴（100× vs 1.6×），
> 而**张角 53° 时投影协方差根本不存在**（二阶矩积分发散）；
> ③ 逐位比对漏了第三个近似（3σ 包围盒是 tile 对齐的，影响 0.50 个 8 bit 色阶）；
> ④ 「尺度梯度更适合当密度判据」是单次运行的假象（6 次均值下它在每一档都低于随机基线）。
>
> 另外把一个流行说法量化纠正了：**SH 的「角分辨率 180/(ℓ+1)」高估约 1.45 倍**，
> 实测（20% 相对残差判据）是 **125/(ℓ+1)** —— deg 3 只到半角 **31.2°**，
> 而抛光塑料要 12.3°、抛光金属 3.4°。

#### C75 · 三维重建与 3D 生成

| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C75 | `C75_Reconstruction_Generation_Course/` | 三维重建与 3D 生成（四条路线的总览 · SfM 与束调整 · 稠密多视图立体 · 前馈回归（单目深度与点图）· SDS 与多视角扩散 · 网格化与 3D 评测） | 全库 478 个讲解页里 `Structure from Motion` / `bundle adjustment` / `gauge` / `Schur` / `立体匹配` / `代价体` / `plane sweep` / `单目深度` / `TSDF` / `Marching Cubes` / `泊松重建` / `Score Distillation` / `倒角距离` 全部 0 命中（`Chamfer` 的 1 处在 C54 的匈牙利匹配上下文，`ICP` 的 9 处全是 **ICPR** 的子串）|

> **一条原理性的限制先把整门课框定了**：把场景点与相机平移一起乘 $s$，
> 拍出的图像**逐位相同**（notebook 取 $s$ 到 $10^3$，最大像素差 $1.1\times10^{-13}$）。
> 所以「从图像得到米」在原理上不可能 —— 每条路线都必须在某处引入外部信息，
> 而**引入的位置就是这些方法最大的区别**。
>
> **与 C72/C73/C74 不同：本课有真实的优化，但没有神经网络训练。**
> 模块 01 有能收敛的束调整（LM + Schur 补）、模块 02 有平面扫掠、
> 模块 04 有在解析已知先验上跑的 SDS —— 因为这门课的核心问题**就是**优化的性质
> （什么可观测、条件数多大、收敛到哪个不动点）。
> 而模块 03/04 用解析构造的替身，因为它们要验的是**口径**与**目标函数的性质**。
>
> **一条贯穿全课的线**：每个模块都有一个「看起来是精度问题、实际是**可观测性**问题」的地方 ——
> 模块 01 的纯旋转（零空间从 7 涨到 **npt+6**）· 模块 02 的周期纹理（误差与噪声**无关**）·
> 模块 03 的绝对尺度（原理不可观测）· 模块 04 的 Janus（目标的严格最优解）·
> 模块 05 的 Chamfer（不是度量，所以「差 0.1」没有传递性）。
>
> **六处诚实修正**，三条最值得记：
> ① 我第一版测「小基线让条件数爆到 $10^{19}$」时，那个轨迹让相机转 100° 却几乎不平移，
> 于是 **40 个点里有 25–33 个跑到了相机背后**（投影 u 到 52 万像素）——
> 我测的是一个坏掉的场景。换成 look-at 轨迹后才得到干净的 $\propto (B/z)^{-2}$；
> ② **前向运动不让 $E$ 退化**（$\sigma_8/\sigma_9 = 1.3\times10^{15}$），退化的是**三角化**；
> ③ **「SDS 里的 $-\epsilon$ 是降方差的控制变量」只在高噪端或模式附近成立** ——
> 低噪端它让方差涨 391 倍。无条件成立的只有「它不改变期望」这一条。
>
> **两处意外收获**：纯旋转时零空间恰好是 **npt + 6**（随场景规模增长，不是「7 加一点」）；
> 先验权重 $(0.9,0.1)$ 时**次模式不再是吸引子** —— SDS 给出 100%/0% 而不是 90%/10%。
>
> 顺带把三条常被含糊的评测口径量化了：单目深度的协议三选（域 × 自由度 × 逐图/全局）
> **各值一到两个数量级、合起来 154 倍**；**Chamfer 不是度量**（$20 > 5{+}5$）；
> **CD-L1 对离群点线性而 CD-L2 平方**（一个离群点 1.31× vs **293×**）。


| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C76 | `C76_Causal_Inference_Course/` | 因果推断与线上归因（潜在结果框架 · 因果图与后门准则 · 倾向得分/IPW/双重稳健/DML · DiD/IV/RDD/合成控制 · SUTVA 与干扰、集群随机化、多触点归因、代理指标） | 全库 484 个讲解页里 `potential outcome` / `工具变量` / `instrumental variable` / `2SLS` / `双重差分` / `difference-in-differences` / `合成控制` / `synthetic control` / `double machine learning` / `doubly robust` / `双重稳健` / `positivity` / `平行趋势` / `SUTVA` / `溢出效应` / `集群随机` / `switchback` / `多触点` / `last-touch` / `增益模型` / `后门准则` / `back-door` / `AIPW` 全部 **0 命中**；`backdoor` 的 8 处**全是后门攻击**（C29/C44 安全课），`propensity` 的 6 处里 4 处是安全评测里的「倾向性」（capability vs propensity）、2 处是 C47/C63 的位置偏差 IPS；`潜在结果` 的唯一一处在 C10-07，一句话说明「随机分配让 $T$ 与潜在结果独立」—— 正好印证边界 |

> **一条代数恒等式先把整门课框定了**：朴素差 $=$ ATT $+$ 选择偏差。
> 这不是近似 —— 在本课的合成人群上 `1.582605 = 0.647736 + 0.934869`，**两边之差恰为 0**。
> 所有识别策略（随机化、后门调整、工具变量、双重差分）做的都是同一件事：
> **给「选择偏差」这一项一个等于零（或可估计）的理由**。
>
> **与 C10 模块 07 零重叠**：那一节拥有整套 A/B 统计工具箱（假设检验、功效与 MDE、
> 多重比较、序贯检验、CUPED），本课一概不重复。本课的定位是
> **「C10-07 假设随机化有效；本课处理它无效或不够的情形」**。
>
> **一条贯穿全课的线**：因果推断的失效几乎从不表现为错误，而是表现为
> **「答对了另一个问题」**。本课十几个失效场景里**没有一个会报错** ——
> 每一个都给出格式正确、置信区间漂亮、换 seed 也复现、能写进周报的数字：
> 你以为在估全人群 ATE，实际估到的是 ATT（**相差 2.09 倍**）· 或「两臂齐全的层上的 ATE」
> （$K{=}800$ 时**静默丢弃 22.2% 的样本**）· 或**直接效应**（$2.90 \to 2.00$，丢掉 31%）·
> 或重叠人群的 ATE（$2.0019 \to 1.4371$，而被排除者的效应是 **+4.96**，最强的那批）·
> 或与 OLS 无法区分的有偏估计（**1.8009 vs 1.7994**）· 或直接效应而非全局效应（**1.00 vs 2.00**）·
> 或按曝光顺序分配的会计份额（真实份额 **7.1% 被记成 38.0%**）·
> 或长期效应中只经由代理指标的那部分（短期 **+1.005**，长期 **−0.999**，**符号反转**）。
>
> **两个 bit 级恒等式**（都说明「双重稳健」可以在不报任何错的情况下消失）：
> ① **常数 $\hat e$ 使 AIPW $\equiv$ G-computation** —— 每臂带截距的 OLS 使臂内残差和恰为 0，
> 于是修正项整体为 0，**无论 $\hat e$ 对不对**（4 个模型规模上差 $< 2\times10^{-11}$；
> 而 $q{=}400$ 时 G-comp 已崩到 **+123.44**，AIPW 与它逐位相同）;
> ② **过拟合把修正项连续吃掉 $4.4\times10^5$ 倍**（$3.15\times10^{-1} \to 7.08\times10^{-7}$，单调）——
> **越强的结果模型越把纠偏机制关掉**，而没有任何拟合优度指标会标记这件事。
>
> **六处诚实修正**，四条最值得记：
> ① **「RDD 带宽越小偏差越小」在两侧曲率*对称*时是假的** —— 两侧的局部线性偏差
> **恰好抵消**，最优带宽变成用满全部数据（$h^{*}{=}1.0$）；必须让两侧曲率不同
> 才出现内点最优（$h^{*}{=}0.2$，而 $h{=}1.0$ 偏 0.4175）。
> 真正的结论比原来的更有用：**RDD 的偏差取决于两侧形状之*差*，不是曲率大小**；
> ② **「DML 的交叉拟合总是更好」是错的** —— 在部分线性的残差对残差得分里
> **四个设定全部更差**（nuisance 的过拟合同时压低 $\tilde T$ 与 $\tilde Y$，在比值里抵消）；
> 它在 **AIPW 得分**里才必要，而且是**必要条件不是充分条件**
> （$q{=}320$ 时交叉拟合的 G-comp 仍是 **+36.64**）；
> ③ **「正交化是一种新估计量」在 OLS nuisance 下是假的** —— Frisch–Waugh–Lovell：
> `1.4633431908608447` vs `1.4633431908608445`，差 $2.2\times10^{-16}$。
> 所以「上 DML」在 nuisance 是 OLS 时**不会改变任何数字**；
> ④ **我第一版的双重稳健表证明不了它想证明的事** —— 我把结果模型的误配设成两臂相同的 $X^2$，
> 于是它在 $\hat m_1 - \hat m_0$ 里**自动抵消**，「错」的模型给出 1.9928（几乎无偏）。
> 教训：验证「模型 A 错时会怎样」之前，要先确认 A 真的错在**会影响估计量**的方向上。
>
> **两处意外收获**：① **对撞偏差的强度有闭式解** —— 取 $Z = X+Y+\varepsilon$，
> 条件相关恰为 $-1/(1+\sigma^2)$（实测 $-0.91698$ vs 理论 $-0.91743$），
> 所以它不是「可能有多大」而是**可以事先算出来**；
> ② **M-bias 需要四条边同时存在**，断任意一条偏差就从 $-0.31$ 回到 $\pm0.003$ ——
> 这解释了它在实践中量级常常很小，也说明该节的论点不是「不要控制处理前变量」，
> 而是**「时间先后不是判据」**。
>
> 另有两条被量化的经验规则：**定向投放的盈亏平衡噪声 $\propto \text{sd}(\tau)^2/\text{ATE}$**
> （**二次**律，$h$ 翻倍容忍的噪声涨 3.79–3.92 倍而不是 2 倍，验证到 0.779–1.130）；
> **合成控制的 pre 期拟合优度对 post 期精度的预测力是 2/4** —— 掷硬币
> （无约束 OLS 在 4/4 种设定里 pre 期都更好，post 期只在 2/4 里更好；
> 而 post 期出现新因子时 **pre RMSE 逐位不变**、post RMSE 涨 3.0 倍）。
>
> **五处「本课自己的配置通不过自己的验收」**（刻意设计）：m01 的 RMSE 选出的最优层数
> $K^{*}{=}200$ 本身已在丢 2.5% 的样本 · m03 的 `DR_COLLAPSED` **有假阳性**
> （场景 1 触发了它而估计是对的，必须配上折内/折外残差比：1.00 无害 vs 2.63 危险）·
> m04 的 `in_hull` 代理判定**没有任何阈值能同时做到 TPR>95% 与 FPR<5%**
> （最优 2.2 处 FPR 仍 13.3%）· m04 的事前登记模板拦住 3/4，**DiD 那个拦不住**
> （问题在不可检验的那一半里）· m05 的审计器对设计 C 无警报，而它有约 −0.15 的干扰偏差。


| 课 | 目录 | 主题 | 补的洞 |
|----|------|------|--------|
| C77 | `C77_Video_World_Models_Course/` | 视频与世界模型（时间轴的代价 · 视频 latent 与 tokenizer · 时空注意力的表达力边界 · 自回归漂移 · 世界模型的两义 · 视频评测的三个病理） | 全库 490 个讲解页里 `video generation` / `video diffusion` / `时空注意力` / `3D VAE` / `video tokenizer` / `temporal consistency` / `optical flow` / `帧插值` / `latent video` / `潜在动力学` / `想象中训练` / `动作条件` / `action-conditioned` / `长程漂移` / `FVD` / `Frechet Video` / `video benchmark` / `CLIP-SIM` 全部 **0 命中**；而非零命中逐条核对后**全部是同名不同义或指向本课的一句带过**：`DiT`（词边界）10 处**全是指向 C28 的转介**、C28 里每一处「视频/时空」都是「留待后续」的伏笔 · `世界模型`/`Dreamer` 归 **C41 模块 04**（规划侧）· `因果卷积` 的 4 处是 C20 的 SSM 展开视角与 C35 的音频流式 · `compounding error` 的 4 处分属 C04（agent 级联）、C41-04（规划）、C59（模仿学习）、C63（多级系统）· `时序一致性` 的 12 处全在**感知/评测**语境（C14/C18/C55）· `VBench` 的唯一命中是 **MVBench**（视频*理解*基准）的子串 |

> **一条贯穿全课的形状**：时间轴上的每一个便宜的近似，
> 都在别处产生一个**精确可算**的代价 —— 而这些代价**全都不会报错**。
>
> | 那个便宜的近似 | 精确的代价 | 会不会报错 |
> |---|---|---|
> | 时间压缩 $p_t$ | $\rho_{\text{eff}} = \rho^{p_t}$；latent 帧数 $T/p_t$ | 不会 |
> | 逐帧独立处理 | 3D 收益 $= f(\text{corr})$，corr$=0$ 时为**负**（$0.984\times$）| 不会 |
> | 分解式时空注意力 | Kronecker 秩 $1$ —— 表示不了加速 | 不会 |
> | 串联接线（vs 并行）| 秩 $1$ vs $m^2{-}m{+}1$ | 不会 |
> | 一步拟合（教师强制）| rollout 的运动能量只有真值的 $35\%$–$49\%$ | 不会 |
> | 报平均而不是中位数 | 均值被 $10\%$ 的崩坏样本主导（差 $10^{16}$）| 不会 |
> | 「一步准就是好模型」| $3.95\%$ 的一步误差 → $251\%$ 的回报高估 | 不会 |
> | 在训练分布上做诊断 | $g{=}0$ 时匹配与误配的曲线**逐点相同** | 不会 |
> | 逐帧特征算 FVD | 帧序敏感度 $7.1\times10^{-15}$ | 不会 |
> | 不同 $N$ 下比 FVD | 零假设值 $\propto 1/N$（$N{=}64$ 时已是 $9.33$）| 不会 |
>
> **与 C28 / C41-04 零重叠**：C28 已经把图像扩散的五块地基讲完
> （latent diffusion、DiT 架构、flow matching、CFG、一致性模型），
> 而它里面**每一处**提到「视频」的地方都是指向前方的一句带过
> （「SoRA 把 patch 推广成时空 patch」「时空一致的 VAE 远比图像难，高质量视频 VAE 仍是瓶颈」
> 「把 CM/对抗蒸馏扩到视频 DiT 是实时视频生成的关键一步」）。
> **本课就是那些「一句带过」的展开。** 而 C41 模块 04 拥有规划侧
> （MPC / Dyna / 规划的复合误差），本课只做生成侧并显式量出两者的分界。
>
> **不训练任何神经网络** —— 本课要说明的性质（压缩率、Kronecker 秩、谱半径、
> 矩匹配、有限样本偏差）都在线性代数与统计层面。用网络反而会把它们藏起来：
> 「分解式注意力表达不了加速」在一个训练好的模型里会表现为
> 「某些样本的运动看起来不对」，而不会表现为一个可以断言的秩。
>
> **五处诚实修正，其中模块 02 那一处连错了三次**：
> ① 猜「多个物体各自不同速度就分解不了」—— **错**，最优 Kronecker 逼近误差**恰为 0**
> （空间重排是<u>一个固定矩阵</u>，所以 $M = A_t \otimes P$ 仍是 Kronecker 积）。
> 精确的判据是「空间模式与 $t$ 无关、时间模式与 $x$ 无关」，
> 所以**分解不了的是加速与变向，不是「多个物体」**；
> ② 猜「多叠几层能补回来」—— **错**，Kronecker 积的乘积仍是 Kronecker 积，八层复合恒为秩 $1$；
> ③ 猜「残差连接能补回来」—— **也错**，
> $(I + I{\otimes}A_s)(I + A_t{\otimes}I) = (I + A_t) \otimes (I + A_s)$，验证到 $0.000\times10^{0}$；
> 第四次才对：**并行分支**才是表达力的来源（秩 $2/4/16$）。
> ④ 「多步 / rollout 损失能修 $\hat a$ 的向下偏差」—— **错**（最优 $k$ 在 $\{1,2,4\}$ 之间跳，
> 而模型正确指定时各 $k$ 的预测误差只差在第 4 位小数）。
> 它的真实作用是在**误配**下把精度从短跨度挪到长跨度，
> 理由是「一步拟合的模型在 $H{=}4$ 时误差 $1.028 > 1.0$ —— **比直接预测均值还差**」；
> ⑤ 「动作分布偏移会被 rollout 放大」—— **不成立**（模型匹配时一步误差在策略幅度跨 30 倍下
> 完全平坦：$0.05360 \to 0.05461$，$+1.9\%$）。统一的说法：
> **分布偏移本身不是问题，误配 × 偏移才是**（误配时同样偏移下涨 **44 倍**）——
> 这也解释了为什么「加大训练动作范围」有效而「加大数据量」无效。
>
> 另有两处方法层的修正：**平稳性诊断必须在一批序列上做**
> （单条 $s_2/s_1$ 在 $T{=}400$ 时 p5–p95 跨 $0.67$–$1.59$，而批级中位数是 $0.998 \pm 0.046$）；
> **能量比必须相对一批真实序列算**，因为 sd 估计量的中位数本身只有真值的 $0.885$。
>
> **两处意外收获**：① **并行分支的 Kronecker 秩饱和值有闭式 $m^2 - m + 1$**
> （$m = \min(T,S)$），七组配置（$m=3,4,5,6$）全部精确命中（$7, 13, 21, 31$），
> 而它**严格小于**朴素上界 $\min(T^2,S^2)$（$m{=}5$ 时是 21 而不是 25）；
> ② **FVD 的盲区取决于特征，而好的特征能把高阶差别搬进前两阶** ——
> 一个均值、方差、时间相关性**全部匹配**、只有峰度从 3 变成 1 的模式坍缩：
> FVD(逐帧) 的比值是 $0.80$（**低于**同分布基线，完全盲），而 FVD(时空) 放大 $20.9\times$，
> 机制很具体：$\vert\Delta\vert$ 这个特征把一个**四阶矩**差别转成了**一阶矩**差别。
>
> **六处「本课自己的配置通不过自己的验收」**（刻意设计）：
> m01 的「峰值在 chunk 最后一帧」在 $s{=}2$ 时不成立（chunk 内差 $<5\times10^{-3}$，成立范围是 $s\geq3$）·
> m02 的整套 Kronecker 分析是**线性算子**层面的，它给出的是下界，
> **不**证明串联式网络学不会加速 · m03 练习 1 里「多步损失修漂移」这条流行建议
> 三项测试**两项失败** · m04 第 4 节的 10 步误差有**混淆因素**
> （$g{=}3$ 时闭环本身不稳定，$\rho(A+B\cdot3K)>1$，那个 $199.86$ 里很大一部分不是模型误差）·
> m04 练习 4 里「四项验收互不蕴含」**被部分推翻**（① 与 ② 是耦合的，
> 没有哪个缩放能让 ① 过而 ② 不过；仍成立的是 ① 不蕴含 ③、① 不蕴含 ④）·
> m05 练习 2 里覆盖率**不是** FVD 盲区的万能补丁（在矩匹配的坍缩上只降到 $0.90\times$）。
>
> 而本课的可交付物是**十个可以在几行 numpy 里重跑的检查**：
> $\rho$ 的估计 · $p_t$ 的上限 · 流式代价 · 码本的熵 · Kronecker 秩 ·
> 全局连通跳数 · $\rho(\hat A)$ · 崩坏率 · 批级平稳性 · 帧序置换检验。
> 十个里有**四个**会否决一条流行的做法或说法，而它们全部可以在拿到真实模型**之前**跑。

<a name="zh-format"></a>
### 每门课的格式

```
CXX_Xxx_Course/
├── index.html          课程主页（模块地图 + 一键 Colab 徽章）
├── README.md           这门课自己的说明（定位、与相邻课的分工）
├── glossary.md          术语词典（≥12KB）
├── references.md        参考清单（论文/文档，标★必读）
├── requirements.txt      依赖（绝大多数课只需要 numpy/pandas/jupyterlab）
├── assets/style.css      全站共用同一份样式（78 门课字节级一致）
├── 00_setup/
│   ├── 00_overview.html         课程总览
│   └── 00_environment_check.ipynb
├── 01_xxx/
│   ├── 01_讲解.html              深度讲解
│   └── 01_xxx.ipynb              配套 notebook
└── ...（每门课 5–10 个模块）
```

notebook 内部的固定节奏：**worked example（讲解配套的最小实现，`print` + `assert` 自检）→ ✏️ 练习（`TODO` 骨架 + `assert` 判分）→ 📖 参考答案 → 🧪 真实数据 / 真实 API 对照胶囊**。

<a name="zh-paths"></a>
### 学习路径建议

1. **数学地基**：C07 → C19 → （C42 理论深潜，可选）
2. **经典 DL**：C15 → C16 → C17 → C18 → C13 → （C41 深 RL）→ （C46 图 ML）
3. **LLM 科学**：C01 → C20 → C21 → C25 → C09 / C22
4. **后训练/对齐**：C02 → C13 → C22 → C23
5. **系统/性能/工程**：C08 → C36 → C24 → C27 → （C38 框架）→ （C39 分布式）→ （C43 数据工程）
6. **评测/安全/可信**：C03 → C10 → C05 → C12 → C06/C29 → （C44 对抗）→ （C45 隐私）
7. **Agent 工程**：C04 → C26 → C30 → C31 → C32 → C33 → C34
8. **多模态**：C00 → C28 → C35
9. **研究素养（贯穿全程）**：C40 研究方法论
10. **工业落地**：C37 MLOps → （C47 推荐系统）→ （C48 云上部署）
11. **补齐工业岗位技能**：C49 encoder/seq2seq → C50 HF 生态 → C51 数据增强 → C48 部署 → C52 研究工程实务

<a name="zh-layout"></a>
### 仓库结构

```
.
├── index.html               全站课程总览页
├── COURSES_PLAN.md            课程规划与构建历史的完整记录
├── ENV_SETUP.md                本地 conda 环境搭建笔记
├── requirements-all.txt        全部 78 门课依赖的合集（装一次跑所有课）
├── _buildkit/                  house-style 生成器（coursekit.py）+ 各课构建脚本
├── C00_..._Course/ … C77_..._Course/   78 门课，每门结构见上
└── README.md                   就是这份文件
```

<a name="zh-gpu"></a>
### 关于 GPU / Colab / 量化

- **绝大多数 notebook 是纯 numpy/CPU**，在任何机器（含 Colab 的免费 CPU 运行时）上都能跑完，不依赖 GPU、网络或任何 API key。
- 少数课程（C00 VLM、C04 的 computer-use 模块、C27 模型压缩、C08 量化专题、C50 PEFT/TRL）会真实加载 HuggingFace 模型：这些 notebook 默认用 **fp16**，2–3B 级模型只需 5–8GB 显存、7B 级也压得进 Colab 免费的 **T4（16GB）**——**不会因为怕显存不够就默认量化**。量化本身只在「这门课/这个模块就是讲量化」时才作为正课内容出现（C08 量化从零、C27 全课、C00/C50 的 QLoRA 教学），其余地方即便留了 4-bit 选项也默认关闭，作为显存特别紧张时的备用开关。
- 每个 notebook 顶部都有官方的 **`Open in Colab`** 徽章，每门课的 `index.html` 每个模块条目旁也有一个小的 Colab 按钮——点开就能在浏览器里跑，无需本地装任何东西。

<a name="zh-env"></a>
### 环境与依赖

- **本地全量环境**：一个 conda env（`courses`，Python 3.11）配好 PyTorch + HuggingFace 全家桶 + 常用科学计算库即可跑完全部 78 门课，详见 [`ENV_SETUP.md`](./ENV_SETUP.md)；合集依赖在 [`requirements-all.txt`](./requirements-all.txt)。
- **只想跑单门课**：进对应课程目录 `pip install -r requirements.txt` 即可——大多数课这份文件只有 `numpy`/`pandas`/`jupyterlab`/`ipykernel` 四五行。
- 所有需要 `transformers`/`bitsandbytes`/`qwen-vl-utils` 等重依赖的真实模型 cell 都包了 `try/except`：装不上/没网/没 GPU 时会优雅降级到纯 Python/numpy 的替代实现或跳过，**不会让整本 notebook 崩掉**。

<a name="zh-history"></a>
### 构建历史

- 2026-06-08 ~ 06-14：建成 C00–C37（38 门）。
- 2026-06-27 ~ 06-28：全谱深化到「极深」标准 + 新增 C38–C47 十门补缺课；引入统一生成器 `coursekit.py`。全谱达到 48 门 · 364 讲解 HTML · 316 notebook。
- 2026-08-06：对照 `LLM Research Engineer` JD 做覆盖度比对，新增 C48–C52 五门课（纯追加，未改动既有 48 门）。全谱达到 **53 门 · 346 讲解 HTML · 346 notebook**。
- 2026-08-12：全站适配 Colab（T4/CPU 均可）——移除非讲量化课程里默认的显存优化用 4-bit 量化，改为默认 fp16；给全部 346 个 notebook 与 53 个课程主页加上一键 Colab 徽章。
- 2026-08-17：按 XPENG「TSR 2D Detection」JD 做覆盖度比对，新增 C53–C61 九门课（纯追加）。
- 2026-08-19：按 HR 说明的一面三板块（编程 / ML 系统设计 / 技术知识问答 + 沟通）新增 C62–C65 四门课。全谱达到 **66 门 · 424 讲解 HTML · 424 notebook**。
- 2026-08-31：按「AI Agent + 大模型 Evaluation」的诉求做覆盖度比对，新增 C66–C69 四门课（纯追加）。四门课共 24 个 notebook、549 个 code cell、96 道 ✏️ 练习自测 assert，全部两遍实跑通过。全谱达到 **70 门 · 448 讲解 HTML · 448 notebook**。
- 2026-08-31（同日第二轮）：继续扩课，新增 C70（RAG 生产工程）与 C71（提示与上下文的程序化优化）。**先纠正了一次错误的缺口判断**——最初提议的「RAG 评测」与「多 agent 编排」已分别被 C11 与 C34 覆盖，会产出重复课；重新对全库 448 个讲解页做关键词扫描后才定下真实缺口。12 个 notebook、272 个 code cell、48 道练习自测 assert 全部两遍实跑通过。全谱达到 **72 门 · 460 讲解 HTML · 460 notebook**。
- 2026-09-08：新增 C72（多视角几何与多传感器时空对齐）。**先扫全库 460 个讲解页做缺口验证**，并先列出「查过、确认不用建」的五个方向（缩放律 / 投机解码 / 持续学习 / 标注运维 / 蒸馏，全部已覆盖）；确认为零覆盖的是「像素 → 米」这条几何链。6 个 notebook、115 个 code cell、24 道练习自测两遍实跑通过。**本轮有五处结论是被真实计算否掉后重写的**：DLT 归一化的精度收益在有噪声时消失（无噪声 45.8 倍 → 0.2 px 噪声下只剩 13% 且归一化略差）；「内外参分开标会互相吸收误差」是错的（吸收得非常干净，真正的问题是可辨识性——而分开它们靠扩大图像行覆盖，σ(pitch) 3.74° → 0.035°，改善 106 倍）；PnP 正交化不提高精度（方向误差只改善 1.24 倍、重投影 RMS 反而变差），且第一版量出的「14.5 倍」是一个**度量陷阱**的产物（trace 公式只对正交矩阵有效，非正交时 40–47% 的实现被 clip 成恰好 0.00°）；「等下一个 IMU 采样比外推准」是错的取舍（等待的代价大 2222 倍）；rolling shutter 对小目标不值得建模（0.005 px），而「整帧一个时间戳」值 0.667 m。另有**两处「本课自己的配置通不过自己的验收」**（模块 02 的 5 视角标定栽在边缘覆盖、模块 04 的均匀网格栽在采样率与坡度）——那是设计而非失误。全谱达到 **73 门 · 466 讲解 HTML · 466 notebook**。
- 2026-09-09：新增 C73（3D 表示与点云深度学习）。扫全库 466 个讲解页确认热门 3D 方向整块零覆盖（PointNet / PointPillars / 体素 / 点云分割 / 双目 / 单目深度 / SDF 全部 0 命中）。6 个 notebook、117 个 code cell、24 道练习自测两遍实跑通过。**本轮有七处结论被真实计算否掉后重写**，其中三处最值得记：`sum`/`mean` 不是逐位置换不变的（浮点加法不满足结合律，相对差 1.43e-15；而 `max`/`min` 是选择操作所以逐位不变）——所以置换不变性的单元测试不能一律用「恰好相等」；`max` 并没有完全丢弃点数（线性探针 $R^2=0.76$，因为极值统计量依赖样本量）；膨胀最快的不是薄结构而是完全散开的点（22.05× vs 薄片 4.32×），而规则密度的排序恰好相反、两者之积被核大小 27 框住。**最硬的一条结论**（推导闭合）：单轴容差恰好 $s_i/3$ ⇒ 交通标志的容差 0.049 m 与典型标注噪声 0.05 m 之比 **0.98×** ⇒ 让预测等于真值、只给真值加标注噪声，AP@IoU0.5 上界只有 **0.392**（卡车与轿车都是 1.000，中心距离口径下四类恒为 1.000）——**所以那一列量的是标注噪声而不是模型能力**。另有三处「本课自己的配置通不过自己的审计」。全谱达到 **74 门 · 472 讲解 HTML · 472 notebook**。
- 2026-09-09：新增 C74（3D 高斯溅泼与实时渲染），同一批 3D 课单的第二门。缺口验证（全库 472 个讲解页逐关键词 grep）：`球谐`/`spherical harmonic` 0、`alpha compositing` 0、`tile 光栅化` 0、`EWA` 0；而 `体渲染`/`α 合成`/`高斯溅泼`/`NeRF` 的少数命中全部是 C72/C73/C55 里指向本课的一句带过。**因为选课路径跳过了 NeRF，体渲染与 α 合成的地基由本课模块 01 自带。** 6 个 notebook、123 个 code cell、24 道练习自测两遍实跑通过；notebook 里从零写出一个能出图的 tile 光栅化器，并与逐像素暴力实现**逐位相等到机器精度**。**本轮有四处结论被真实计算否掉后重写**，两条最值得记：① **对分段常数密度，α 合成精确到机器精度，连 $N{=}1$ 都对**（$N{=}1$ 误差为 0，$N{=}256$ 是 8.9e−16）——所以离散化误差**只**来自 σ 在段内变化，而那时中点法则是**二阶**的（每翻一倍 $N$ 误差降到 1/4.00，我最初写的 ∝1/N 是错的）；② **张角 53° 时投影后的协方差根本不存在**——2.28% 的质量落在 $z\le0$，$z\to0^+$ 的样本被投到无穷远，二阶矩积分发散（蒙特卡洛估计从 $n{=}10^4$ 到 $10^6$ 涨 9 倍、种子间差 3 倍），**所以「仿射近似在这里误差多少」这个问题问错了，它要对比的真值不存在**。另有两条：逐位比对最初漏了第三个近似（3σ 包围盒是 tile 对齐的，其影响 0.50 个 8 bit 色阶）；「尺度梯度更适合当密度判据」是单次运行的假象（一个目标一个种子时命中 67%，跑满 6 次是 28%，且在每一档都低于随机基线 25%）。顺带把一个流行说法量化纠正了：**SH 的「角分辨率 180/(ℓ+1)」高估约 1.45 倍**，实测（20% 相对残差判据）是 **125/(ℓ+1)**——deg 3 只到半角 **31.2°**，而抛光塑料要 12.3°、抛光金属 3.4°，**所以 SH deg 3 只能勉强表示粗糙塑料级的高光，而这是表示能力的限制、不是优化没收敛**。另有三处「本课自己的配置通不过自己的审计」。全谱达到 **75 门 · 478 讲解 HTML · 478 notebook**。
- 2026-09-10：新增 C75（三维重建与 3D 生成），同一批 3D 课单的第三门，也是这批的收尾。缺口验证（全库 478 个讲解页逐关键词 grep）：`Structure from Motion` / `bundle adjustment` / `gauge` / `Schur` / `立体匹配` / `代价体` / `plane sweep` / `单目深度` / `TSDF` / `Marching Cubes` / `泊松重建` / `Score Distillation` / `倒角距离` 全部 **0 命中**；`Chamfer` 的 1 处在 C54 的匈牙利匹配上下文，`ICP` 的 9 处全是 **ICPR**（会议名）的子串。6 个 notebook、125 个 code cell、24 道练习自测两遍实跑通过。**与 C72/C73/C74 不同：本课有真实的优化（束调整、平面扫掠、SDS），但不训练任何网络**——因为核心问题就是优化的性质（可观测性、条件数、不动点）。**本轮有六处结论被真实计算否掉后重写**，三条最值得记：① 我第一版测「小基线让条件数爆到 $10^{19}$」时，那个轨迹让相机转 100° 却几乎不平移，于是 **40 个点里有 25–33 个跑到了相机背后**（投影 u 到 52 万像素）——我测的是一个坏掉的场景，不是小基线效应；换成 look-at 轨迹后才得到干净的 $\propto (B/z)^{-2}$（小基线端实测指数 −2.00）。② **前向运动不让 $E$ 退化**（$\sigma_8/\sigma_9 = 1.3\times10^{15}$），退化的是**三角化**（极点附近视线夹角只有外圈的 1/7.5）——这是两件不同的事，混在一起会让人去修错的地方。③ **「SDS 里的 $-\epsilon$ 是降方差的控制变量」只在高噪端或模式附近成立**：逐 $t$ 看效应完全反转，低噪端（$t{=}0.05$）它让方差**涨 391 倍**、高噪端（$t{=}0.95$）降 1533 倍；无条件成立的只有「它不改变期望」这一条（而两个估计量之差恰好不含 $x$，6 个 $x$ 处逐位相同）。**另有两处意外收获**：纯旋转时零空间恰好是 **npt + 6**（5 组配置验证——每个点的深度都不可观测 + 全局旋转 3 + 平移 3，而尺度被并进逐点深度里，所以它随场景规模增长而不是「7 加一点」）；先验权重 $(0.9,0.1)$ 时**次模式不再是吸引子**，SDS 给出 **100%/0%** 而不是 90%/10%——所以「多样性坍缩」不只是概率被压平，而是少数模式在动力学里直接消失。顺带把三条常被含糊的评测口径量化了：单目深度的协议三选（对齐**域** × 自由度 × 逐图/全局）**各值一到两个数量级、合起来 154 倍**，而规则是「对齐域必须与模型的不变性所在的域一致」（两个方向都验了，所以**评测协议不能独立于模型来定**）；**Chamfer 不是度量**（反例 $20 > 5{+}5$，超出 2 倍，所以「CD 差 0.1」没有传递性）；**CD-L1 对离群点线性而 CD-L2 平方**（一个 50 倍半径的离群点让 L1 涨 1.31× 而 L2 涨 **293×**，理论 $(d{-}1)^p/n$ 与实测吻合到 2e-4）。全谱达到 **76 门 · 484 讲解 HTML · 484 notebook**。
- 2026-09-10：新增 C76（因果推断与线上归因）。缺口验证（全库 484 个讲解页逐关键词 grep）：`potential outcome` / `工具变量` / `instrumental variable` / `2SLS` / `双重差分` / `difference-in-differences` / `合成控制` / `double machine learning` / `doubly robust` / `双重稳健` / `positivity` / `平行趋势` / `SUTVA` / `溢出效应` / `集群随机` / `switchback` / `多触点` / `last-touch` / `增益模型` / `后门准则` / `AIPW` 全部 **0 命中**；`backdoor` 的 8 处**全是后门攻击**（C29/C44），`propensity` 的 6 处里 4 处是安全评测里的「倾向性」、2 处是 C47/C63 的位置偏差 IPS；`潜在结果` 的唯一一处在 C10-07 的一句话里 —— 正好印证边界。6 个 notebook、106 个 code cell、24 道练习自测两遍实跑通过。**与 C10 模块 07 零重叠**：那一节拥有整套 A/B 统计工具箱（假设检验、功效/MDE、多重比较、序贯、CUPED），本课一概不重复，定位是「C10-07 假设随机化有效；本课处理它无效或不够的情形」。**整门课由一条代数恒等式框定**：朴素差 $=$ ATT $+$ 选择偏差 —— 不是近似，实测 `1.582605 = 0.647736 + 0.934869`，**两边之差恰为 0**。**贯穿全课的线：因果推断的失效几乎从不表现为错误，而是表现为「答对了另一个问题」** —— 十几个失效场景里**没有一个会报错**，每一个都给出格式正确、置信区间漂亮、换 seed 也复现的数字（你以为估全人群 ATE，实际估到 ATT，相差 2.09 倍 / 或「两臂齐全的层上的 ATE」，$K{=}800$ 时**静默丢弃 22.2% 的样本** / 或直接效应，$2.90 \to 2.00$ 丢掉 31% / 或重叠人群的 ATE，$2.0019 \to 1.4371$ 而被排除者效应是 **+4.96** / 或与 OLS 无法区分的有偏估计，**1.8009 vs 1.7994** / 或直接效应而非全局效应，**1.00 vs 2.00** / 或按曝光顺序分配的会计份额，真实份额 **7.1% 被记成 38.0%** / 或长期效应中只经由代理指标的那部分，短期 **+1.005** 而长期 **−0.999**，**符号反转**）。**两个 bit 级恒等式**，都说明「双重稳健」可以在不报任何错的情况下消失：① **常数 $\hat e$ 使 AIPW $\equiv$ G-computation** —— 每臂带截距的 OLS 使臂内残差和恰为 0，修正项整体为 0，**无论 $\hat e$ 对不对**（4 个模型规模上差 $< 2\times10^{-11}$；而 $q{=}400$ 时 G-comp 已崩到 **+123.44**，AIPW 与它逐位相同）；② **过拟合把修正项连续吃掉 $4.4\times10^5$ 倍**（$3.15\times10^{-1} \to 7.08\times10^{-7}$，单调）—— **越强的结果模型越把纠偏机制关掉**，而没有任何拟合优度指标会标记这件事。**本轮有六处结论被真实计算否掉后重写**，四条最值得记：① **「RDD 带宽越小偏差越小」在两侧曲率*对称*时是假的** —— 两侧的局部线性偏差**恰好抵消**，最优带宽变成用满全部数据（$h^{*}{=}1.0$）；必须两侧曲率不同才有内点最优（$h^{*}{=}0.2$，$h{=}1.0$ 偏 0.4175）。**RDD 的偏差取决于两侧形状之*差*，不是曲率大小**；② **「DML 的交叉拟合总是更好」是错的** —— 在部分线性的残差对残差得分里**四个设定全部更差**（过拟合同时压低 $\tilde T$ 与 $\tilde Y$，在比值里抵消）；它在 **AIPW 得分**里才必要，且是**必要条件不是充分条件**（$q{=}320$ 时交叉拟合的 G-comp 仍是 **+36.64**）；③ **「正交化是一种新估计量」在 OLS nuisance 下是假的** —— Frisch–Waugh–Lovell：`1.4633431908608447` vs `1.4633431908608445`，差 $2.2\times10^{-16}$，所以「上 DML」在 nuisance 是 OLS 时**不会改变任何数字**；④ **我第一版的双重稳健表证明不了它想证明的事** —— 结果模型的误配设成两臂相同的 $X^2$，于是它在 $\hat m_1 - \hat m_0$ 里**自动抵消**，「错」的模型给出 1.9928（几乎无偏）。教训：验证「模型 A 错时会怎样」之前，要先确认 A 真的错在**会影响估计量**的方向上。**两处意外收获**：**对撞偏差的强度有闭式解**（$Z = X+Y+\varepsilon$ 时条件相关恰为 $-1/(1+\sigma^2)$，实测 $-0.91698$ vs 理论 $-0.91743$，所以它不是「可能有多大」而是**可以事先算出来**）；**M-bias 需要四条边同时存在**，断任意一条偏差就从 $-0.31$ 回到 $\pm0.003$ —— 所以该节的论点不是「不要控制处理前变量」，而是**「时间先后不是判据」**。另有两条被量化的经验规则：**定向投放的盈亏平衡噪声 $\propto \text{sd}(\tau)^2/\text{ATE}$**（**二次**律，$h$ 翻倍容忍的噪声涨 3.79–3.92 倍而不是 2 倍）；**合成控制的 pre 期拟合优度对 post 期精度的预测力是 2/4** —— 掷硬币（无约束 OLS 在 4/4 种设定里 pre 期都更好而 post 期只在 2/4 里更好；post 期出现新因子时 **pre RMSE 逐位不变**、post RMSE 涨 3.0 倍）。另有**五处「本课自己的配置通不过自己的验收」**。全谱达到 **77 门 · 490 讲解 HTML · 490 notebook**。
- 2026-09-10：新增 C77（视频与世界模型）。缺口验证（全库 490 个讲解页逐关键词 grep）：`video generation` / `video diffusion` / `时空注意力` / `3D VAE` / `video tokenizer` / `temporal consistency` / `optical flow` / `帧插值` / `latent video` / `潜在动力学` / `想象中训练` / `动作条件` / `长程漂移` / `FVD` / `Frechet Video` / `video benchmark` / `CLIP-SIM` 全部 **0 命中**；非零命中逐条核对后**全部是同名不同义或指向本课的一句带过**——`DiT`（词边界）10 处全是指向 C28 的转介，而 **C28 里每一处「视频/时空」都是「留待后续」的伏笔**（「SoRA 把 patch 推广成时空 patch」「时空一致的 VAE 远比图像难，高质量视频 VAE 仍是瓶颈」「把 CM/对抗蒸馏扩到视频 DiT 是实时视频生成的关键一步」）；`世界模型`/`Dreamer` 归 C41 模块 04（规划侧）；`因果卷积` 的 4 处是 C20 的 SSM 展开视角与 C35 的音频流式；`compounding error` 的 4 处分属 C04/C41-04/C59/C63 四种不同机制；`时序一致性` 的 12 处全在感知/评测语境；`VBench` 的唯一命中是 **MVBench** 的子串。6 个 notebook、93 个 code cell、24 道练习自测两遍实跑通过。**与 C28 / C41-04 零重叠**：本课就是 C28 那些「一句带过」的展开，而 C41-04 拥有规划侧、本课只做生成侧并显式量出分界。**不训练任何神经网络**——要说明的性质（压缩率、Kronecker 秩、谱半径、矩匹配、有限样本偏差）都在线性代数与统计层面，用网络反而会把它们藏起来。**贯穿全课的形状：时间轴上的每一个便宜的近似，都在别处产生一个精确可算的代价，而这些代价全都不会报错**（十条对照见上方 C77 小节，末列全是「不会」）。**本轮有五处结论被真实计算否掉后重写，其中模块 02 那一处连错了三次**：① 猜「多个物体各自不同速度就分解不了」——**错**，最优 Kronecker 逼近误差**恰为 0**（空间重排是一个固定矩阵，所以 $M = A_t \otimes P$ 仍是 Kronecker 积）；精确的判据是「空间模式与 $t$ 无关、时间模式与 $x$ 无关」，所以**分解不了的是加速与变向，不是「多个物体」**；② 猜「多叠几层能补回来」——**错**，Kronecker 积的乘积仍是 Kronecker 积，八层复合恒为秩 1；③ 猜「残差连接能补回来」——**也错**，$(I + I{\otimes}A_s)(I + A_t{\otimes}I) = (I + A_t) \otimes (I + A_s)$，验证到 $0.000\times10^{0}$；第四次才对：**并行分支**才是表达力的来源（秩 2/4/16，而完全 3D 是 25）。④ 「多步/rollout 损失能修 $\hat a$ 的向下偏差」——**错**（最优 $k$ 在 {1,2,4} 之间跳；模型正确指定时各 $k$ 的预测误差只差在第 4 位小数）；它的真实作用是在**误配**下把精度从短跨度挪到长跨度，理由是「一步拟合的模型在 $H{=}4$ 时误差 $1.028 > 1.0$——**比直接预测均值还差**」。⑤ 「动作分布偏移会被 rollout 放大」——**不成立**（模型匹配时一步误差在策略幅度跨 30 倍下完全平坦：$0.05360 \to 0.05461$，$+1.9\%$）；统一的说法是**分布偏移本身不是问题，误配 × 偏移才是**（误配时同样偏移下涨 **44 倍**），这也解释了为什么「加大训练动作范围」有效而「加大数据量」无效。另有两处方法层修正：**平稳性诊断必须在一批序列上做**（单条 $s_2/s_1$ 在 $T{=}400$ 时 p5–p95 跨 0.67–1.59，批级中位数是 $0.998 \pm 0.046$）；**能量比必须相对一批真实序列算**（sd 估计量的中位数本身只有真值的 0.885）。**两处意外收获**：并行分支的 Kronecker 秩饱和值有闭式 **$m^2-m+1$**（$m=\min(T,S)$），七组配置全部精确命中（7/13/21/31），且**严格小于**朴素上界 $\min(T^2,S^2)$；**FVD 的盲区取决于特征，而好的特征能把高阶差别搬进前两阶**——一个均值、方差、时间相关性全部匹配、只有峰度从 3 变成 1 的模式坍缩，FVD(逐帧) 的比值是 **0.80（低于同分布基线，完全盲）**而 FVD(时空) 放大 **20.9 倍**，机制是 $\vert\Delta\vert$ 把四阶矩差别转成了一阶矩差别。另有**六处「本课自己的配置通不过自己的验收」**。本课的可交付物是**十个可以在几行 numpy 里重跑的检查**，其中四个会否决一条流行的做法，而十个全部可以在拿到真实模型之前跑。全谱达到 **78 门 · 496 讲解 HTML · 496 notebook**。

完整细节见 [`COURSES_PLAN.md`](./COURSES_PLAN.md)。

---

<a name="english"></a>
## English

### Table of Contents
- [What This Is](#en-what)
- [Quick Start](#en-quickstart)
- [Course Catalog (78 courses)](#en-catalog)
- [Format of Each Course](#en-format)
- [Suggested Learning Paths](#en-paths)
- [Repository Layout](#en-layout)
- [About GPU / Colab / Quantization](#en-gpu)
- [Environment & Dependencies](#en-env)
- [Build History](#en-history)

<a name="en-what"></a>
### What This Is

A self-study curriculum for **frontier-lab AI research scientists / research engineers**, grown from an original "model evaluation" skill stack into a full-stack program spanning LLM internals, post-training, inference systems, agent engineering, multimodality, distributed training, model compression, interpretability, safety, privacy, graph ML, recommender systems, cloud deployment, and even patents/open-source compliance.

Every course follows the same "deep" bar:
- **HTML lessons**: Chinese prose with English technical terms, 8–9 numbered sections, callout boxes (intuition / warning / danger / paper citation), side-by-side comparisons, tables, ASCII diagrams, and math derivations. Every lesson closes with a "research frontier & open problems" section.
- **Notebooks**: mirror the lesson 1:1 — core mechanisms re-implemented from scratch in plain Python/numpy → 3–4 `✏️` exercises (TODO skeleton + `assert`-graded self-tests) → `📖` reference answers → a `🧪` real-data / real-API capsule that translates what you just learned into code you can copy-paste onto a real machine (or Colab).
- A **glossary** (`glossary.md`, ≥12KB) and a **reference list** (`references.md`, ≥8KB, ★ marks must-reads) per course.

**Nearly every course runs end-to-end with no GPU, no network, and no API key** — the core mechanisms are hand-reimplemented in numpy. Real framework/model usage is shown as a "real-API capsule" at the end of each module, ready to be copied onto a machine (or Colab) with a real GPU. The handful of courses that genuinely need a real model (VLM, agent computer-use, etc.) default to **fp16** and fit comfortably on a free Colab **T4 (16GB)** — quantization is not used as a default crutch to "make the model fit"; it only appears as actual lesson content in the courses that are specifically about quantization.

<a name="en-quickstart"></a>
### Quick Start

**Run in Colab (recommended, zero install)**
Open any course's `index.html`, or go straight into a course folder and find the module's `.ipynb`, then click the **`Open in Colab`** badge at the top. Once in Colab, set the runtime to a T4 GPU (`Runtime → Change runtime type → T4 GPU`) — you're ready to go.

**Run locally**
```bash
git clone https://github.com/ZeruiW/frontier-ai-courses.git
cd frontier-ai-courses/C20_Frontier_Architectures_Course   # pick any course
pip install -r requirements.txt      # most courses only need numpy/pandas/jupyterlab
jupyter lab
```
Read a module's `NN_讲解.html` lesson first (or start from `index.html` to pick a path), then run the matching `.ipynb`. All courses share one `assets/style.css`.

<a name="en-catalog"></a>
### Course Catalog (78 courses)

#### C00–C09 · Core LLM & Evaluation Track
| # | Folder | Topic |
|---|--------|-------|
| C00 | `C00_VLM_Multimodal_Course/` | VLMs & multimodal AI (10 modules, the deepest course) |
| C01 | `C01_LLM_Internals_Course/` | LLM internals: implementing a Transformer from scratch |
| C02 | `C02_Post_Training_Course/` | Post-training & alignment: SFT → RLHF/DPO → RLVR |
| C03 | `C03_LLM_Evals_Course/` | Evaluation science: benchmarks, statistics, LLM-as-judge |
| C04 | `C04_AI_Agents_Course/` | AI agents & agentic evaluation |
| C05 | `C05_Safety_Evals_Course/` | Frontier model safety evaluation & red-teaming |
| C06 | `C06_Interpretability_Course/` | Mechanistic interpretability (the depth reference course) |
| C07 | `C07_ML_Foundations_Course/` | ML foundations & interview math |
| C08 | `C08_Training_Systems_Course/` | Large-model training & inference systems (cost ledgers) |
| C09 | `C09_Reasoning_TTC_Course/` | Reasoning models & test-time compute |

#### C10–C19 · Evaluation Completion & Classic AI Foundations
| # | Folder | Topic |
|---|--------|-------|
| C10 | `C10_Eval_Measurement_Course/` | Eval data & measurement science (IRT / calibration / A-B testing) |
| C11 | `C11_RAG_Retrieval_Course/` | Retrieval augmentation & long-context evaluation |
| C12 | `C12_Responsible_AI_Course/` | Responsible AI & societal-impact evaluation |
| C13 | `C13_RL_Foundations_Course/` | RL foundations (MDP → PG → AC → bandits) |
| C14 | `C14_DL_Theory_Data_Course/` | DL theory & data / generative-media evaluation |
| C15 | `C15_Classic_Architectures_Course/` | Classic neural architectures (CNN/RNN/LSTM/seq2seq) |
| C16 | `C16_Generative_Models_Course/` | Generative models (AE/VAE/GAN/diffusion/flow) |
| C17 | `C17_Classical_NLP_Course/` | Classical NLP (word2vec/n-gram/HMM/CRF) |
| C18 | `C18_Computer_Vision_Course/` | Computer vision (detection/segmentation/self-supervision) |
| C19 | `C19_Bayesian_ML_Course/` | Probabilistic & Bayesian ML (MCMC/VI/GP/PGM) |

#### C20–C29 · Frontier Deep-Dive
| # | Folder | Topic |
|---|--------|-------|
| C20 | `C20_Frontier_Architectures_Course/` | Modern architectures (RoPE/GQA/MLA/MoE/SSM) |
| C21 | `C21_Frontier_Pretraining_Course/` | Large-scale pretraining engineering (data/tokenizer/μP/stability) |
| C22 | `C22_Reasoning_RL_Course/` | RL for reasoning models (long-CoT/GRPO/PRM, o1/R1-era) |
| C23 | `C23_Frontier_Alignment_Course/` | Frontier alignment (CAI/scalable oversight/weak-to-strong) |
| C24 | `C24_Inference_Serving_Course/` | Efficient inference & serving (vLLM/SGLang stack) |
| C25 | `C25_Long_Context_Course/` | Long context & efficient attention (YaRN/sparse/KV compression) |
| C26 | `C26_Frontier_Agents_Course/` | Frontier agents (MCP/computer use/agentic RL) |
| C27 | `C27_Model_Compression_Course/` | Model compression & efficiency (quantization/GPTQ-AWQ/distillation/pruning) |
| C28 | `C28_Frontier_Diffusion_Course/` | Diffusion & flow frontier (DiT/flow/consistency) |
| C29 | `C29_Frontier_Interp_Course/` | Frontier mechanistic interpretability (SAE/features/steering) |

#### C30–C37 · Build Agents & Systems by Hand
| # | Folder | Topic |
|---|--------|-------|
| C30 | `C30_Agent_Harness_Course/` | Agent harness from scratch |
| C31 | `C31_Coding_Agent_Course/` | Building a coding agent (your own Claude Code) |
| C32 | `C32_Skills_Tools_Course/` | Skills & tool ecosystems (an MCP server from scratch) |
| C33 | `C33_Context_Memory_Course/` | Context engineering & memory |
| C34 | `C34_Agent_Orchestration_Course/` | Multi-agent orchestration & productionization |
| C35 | `C35_Speech_Audio_Course/` | Speech & audio (ASR/codecs/TTS/speech LLMs) |
| C36 | `C36_GPU_Kernels_Course/` | GPU kernels & performance engineering (hand-write FlashAttention) |
| C37 | `C37_MLOps_Course/` | MLOps & the production lifecycle |

#### C38–C47 · Gap-Filling Courses (research-engineer skill-tree holes)
| # | Folder | Topic | Gap it fills |
|---|--------|-------|--------------|
| C38 | `C38_Frameworks_Accel_Course/` | DL frameworks & accelerated compute (PyTorch/JAX/autograd/compile/Triton) | The "real framework" gap left by numpy-only content |
| C39 | `C39_Distributed_Training_Course/` | Distributed training engineering (NCCL/FSDP/3D parallelism/fault tolerance) | C08 gives cost models only, not operable engineering |
| C40 | `C40_Research_Methodology_Course/` | Research methodology & scientific practice (reproduction/ablation/writing/taste) | The meta-skill of "doing research" itself |
| C41 | `C41_Deep_RL_Course/` | Deep RL & decision-making (DQN/PPO/SAC/offline/world models) | C13 only reaches the foundations, no control/world models |
| C42 | `C42_Learning_Theory_Course/` | Learning & optimization theory (PAC/NTK/implicit bias/generalization bounds) | The theoretical backbone for a research scientist |
| C43 | `C43_Data_Engineering_Course/` | Large-scale data engineering (dedup/streaming/throughput/decontamination) | The craft of data "infrastructure" |
| C44 | `C44_Adversarial_Security_Course/` | Adversarial ML & AI security (adversarial examples/poisoning/extraction/injection) | Classic AML and security engineering |
| C45 | `C45_Privacy_Trustworthy_Course/` | Privacy-preserving & trustworthy ML (DP-SGD/federated/unlearning) | The privacy techniques themselves (C12 only measures) |
| C46 | `C46_Graph_ML_Course/` | Graph ML (message passing/GCN-GAT/graph transformers) | The missing geometric deep-learning branch |
| C47 | `C47_RecSys_Ranking_Course/` | Recommender systems & large-scale ranking (two-tower/LTR/CTR-DLRM/sequential) | The largest industry hiring surface |

#### C48–C52 · Industry-Role Gap Courses (aligned to an LLM Research Engineer JD)
| # | Folder | Topic | Gap it fills |
|---|--------|-------|--------------|
| C48 | `C48_Cloud_Deployment_Course/` | Cloud deployment & serving (container/OCI layers · K8s reconcile loop · rollouts & autoscaling · cloud scheduling & cost) | "Actually putting a service on the cloud" was always missing |
| C49 | `C49_Encoder_Seq2Seq_Course/` | Encoders & seq2seq (BERT/MLM · RoBERTa/ELECTRA/DeBERTa · fine-tuning · T5/BART) | The curriculum jumped straight from classic NLP to decoder-only LLMs, skipping the BERT/T5 generation |
| C50 | `C50_HuggingFace_Ecosystem_Course/` | HuggingFace ecosystem in practice (Auto*/from_pretrained · tokenizers/datasets · Trainer · PEFT/TRL · accelerate/Hub) | Numpy-from-scratch doesn't tell you how the real ecosystem is actually used, or where the pitfalls are |
| C51 | `C51_Data_Augmentation_Course/` | Text augmentation & synthetic data engineering (EDA/AEDA · back-translation · Self-Instruct/Evol/Magpie · QC · ablation) | How to manufacture data when labels are scarce — and how to prove it actually helped |
| C52 | `C52_Industrial_Research_Practice_Course/` | Industrial research practice (TF/Keras mental model · cross-framework weight porting · ONNX export & runtimes · real-GPU workflow · patents & OSS compliance) | A batch of "orphan skills" nobody owns but everyone needs |

#### C53–C61 · AD Perception / TSR Gap Courses (aligned to an XPENG TSR 2D Detection JD)
| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C53 | `C53_RealTime_Detectors_Course/` | Real-time detector architectures (YOLO generations · label assignment · RTMDet · RT-DETR · latency–accuracy selection) | RT-DETR / RTMDet named in the JD |
| C54 | `C54_DETR_Set_Prediction_Course/` | End-to-end set-prediction detection (Hungarian matching · set loss · object queries · convergence family · practice) | Hungarian matching & set prediction loss |
| C55 | `C55_TSR_Autonomous_Driving_Course/` | Traffic sign recognition & AD perception (datasets & sign codes · two-stage vs end-to-end · failure modes · temporal fusion · safety-oriented eval) | TSR domain knowledge and AD context |
| C56 | `C56_Detection_Augmentation_Course/` | Detection data augmentation (geometry & label sync · photometric & domain · Mosaic/Copy-Paste · pipeline · ablation) | Image-detection augmentation (C51 is text) |
| C57 | `C57_Small_Object_Detection_Course/` | Small object detection (IoU scale sensitivity · multi-scale architecture · NWD & assignment · sliced inference · TSR physics) | Concrete small-object techniques |
| C58 | `C58_HardCase_LongTail_Course/` | Hard-case mining & long-tail data loop (imbalance spectrum · OHEM · active triggers · mining infra · closed-loop validation) | Detection-context hard-case / long-tail mining |
| C59 | `C59_VLA_Perception_Interface_Course/` | Vision-Language-Action models & perception interface (VLM→VLA · action representation · TSR output schema · rule constraints · eval & deployment) | The JD's distinctive VLA responsibility |
| C60 | `C60_Edge_Deployment_Consistency_Course/` | Edge deployment & train-deploy consistency (preprocessing parity · TensorRT · INT8 calibration · postprocessing & C++ · latency profiling) | Hands-on TensorRT/C++ and consistency debugging |
| C61 | `C61_Detection_Practice_Interview_Course/` | Detection engineering practice & interview readiness (experiment design · TIDE error decomposition · debug playbook · project narrative · drills) | Production instincts and interview delivery |

#### C62–C65 · Interview-Format Gap Courses (the three blocks HR named for round one)
| # | Directory | Topic | Gap filled |
|---|-----------|-------|------------|
| C62 | `C62_Coding_Interview_Course/` | Coding interviews: algorithms & data structures (six-step answering protocol · two pointers/sliding window/prefix sums · hashing, sorting, binary search · trees, graphs, search · DP & greedy · mock interviews) | The single biggest gap: "linked list" and "two pointers" had zero hits across the first 62 courses |
| C63 | `C63_ML_System_Design_Course/` | ML system design interviews (seven-step framework · requirements & metrics · data systems · modeling & evaluation · capacity estimation · six case studies) | C07 had one section on the framework, no methodology and no case library |
| C64 | `C64_ML_Knowledge_QA_Course/` | ML/DL knowledge Q&A (three-part answer shape · ML basics · optimization & training · architectures · evaluation & statistics · rapid-fire bank) | C07 teaches derivations; missing the "explain it in 60 seconds and survive the follow-up" breadth bank |
| C65 | `C65_ProblemSolving_Communication_Course/` | Structured problem solving & interview communication (estimation · diagnosis · trade-off decisions · clarifying vague requirements · whiteboard & English delivery) | Estimation/diagnosis/trade-offs/clarification/communication had no systematic coverage |

#### C66–C69 · Agent Evaluation & AI System Assessment
| # | Directory | Topic | Gap filled |
|---|-----------|-------|------------|
| C66 | `C66_Agentic_Evaluation_Course/` | Agentic evaluation & benchmarks (three evaluation layers · benchmark landscape · scorer α/β bias correction · trajectory metrics · pass@k vs pass^k · cost and harness fingerprints) | Agent evaluation existed only as C04-06 and C26-05 — "this is a thing," never "how to actually run one" |
| C67 | `C67_LLM_Judge_Course/` | LLM-as-a-judge & reward models (decidability ladder · rubric design · four biases and de-biasing · human ceiling & meta-evaluation · BT/Elo ranking · reward models and overoptimization) | Judges had one section (C03-04); bias quantification, meta-evaluation, ranking and RM evaluation were absent |
| C68 | `C68_Eval_Infrastructure_Course/` | Eval infrastructure & online monitoring (spec/runner/store/report layers · dataset versioning & sampling · cache keys & failure semantics · CI gate thresholds · drift and the data loop) | "How to run one evaluation a thousand times" had zero coverage; C37 MLOps centers on the model, not the evaluation |
| C69 | `C69_Agent_Security_Course/` | Agent security & prompt injection (trust propagation · indirect injection and the dual-LLM pattern · tool supply chain · four permission dimensions and sandbox boundaries · egress control · attack-surface evaluation) | C05 is model safety and C44 is adversarial attacks; neither covers what an *agent* can do |

> Division of labour: **C66 measures the agent · C67 measures the scorer · C68 turns evaluation into infrastructure · C69 measures the attack surface**.
> C69 notebooks contain no working attack payloads against any real system (attack techniques are described at the mechanism level in prose only); the defense-side code is all real implementation.

#### C70–C71 · RAG Production Engineering & Prompt Programming
| # | Directory | Topic | Gap filled |
|---|-----------|-------|------------|
| C70 | `C70_RAG_Production_Course/` | RAG production engineering (document ingestion & parsing · chunking · query-side rewriting & routing · iterative and graph retrieval · index operations) | C11 covers "how to find it in the index"; the other half — what goes into the index, what the query looks like, how the index is maintained — had near-zero coverage (document parsing: 1 hit across all 448 lesson pages, query rewriting: 0, incremental indexing: ~0) |
| C71 | `C71_Prompt_Programming_Course/` | Prompt and context programming (prompt programs · demo selection and ordering · automatic prompt optimization · constrained decoding · prompt ops and cross-model migration) | C03-03 takes the *measurement* view of prompt sensitivity and C33 owns the context budget; treating the prompt as a **searchable, guaranteeable, operable program** had no coverage (DSPy: 0 hits) |

> Division of labour: **C70 owns "how data and queries get in, and how the index stays alive"; C71 owns "the structure, optimization and operation of the prompt itself"**.

#### C72 · Multi-View Geometry & Multi-Sensor Spatio-Temporal Alignment

| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C72 | `C72_MultiView_Geometry_Course/` | Multi-view geometry and multi-sensor spatio-temporal alignment (camera model & distortion · calibration and its acceptance criteria · epipolar / triangulation / homography / PnP · BEV projection & multi-camera fusion · temporal alignment & cross-camera association) | Everything in C53–C61 depends on the pixel-to-metre chain, and that chain had no coverage at all: `epipolar geometry` 0 hits, `homography` 0, `PnP` 0, `disparity` 0, `clock sync` 0, `sensor fusion` 1, `extrinsic calibration` 1. BEV appears 45 times across the repo, yet nowhere is it explained how the camera projects, how extrinsics are calibrated, or how multiple views are aligned |

> **Pure geometry, no learning, and deliberately no OpenCV dependency** — projection,
> undistortion, DLT, the calibration constraints, triangulation, PnP, IPM and temporal
> alignment are all implemented from scratch.
> Central result: $d_{\text{read}} = d\cdot H/(H-z)$, so ground-plane IPM applied to a
> traffic sign is **not merely inaccurate but has no solution at all** when $z \ge H$ —
> and the relative error $z/(H-z)$ is **independent of distance**.
> This course is also the shared prerequisite for the 3D courses that follow in the same
> batch (the dividing line being whether there is a learning component).

#### C73 · 3D Representations & Point-Cloud Deep Learning

| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C73 | `C73_3D_Representation_Course/` | 3D representations and point-cloud deep learning (the cost ledger of four representations · permutation invariance and max-pool · voxelization and sparse convolution · 3D detection from anchors to centers · segmentation and 3D evaluation) | The whole cluster of current 3D directions had no coverage: `PointNet` 0 hits, `PointPillars` 0, `voxel` 0, `point-cloud segmentation` 0, `stereo` 0, `monocular depth` 0, `SDF` 0 — while every 3D discussion in C53–C61 assumes these tools are already known |

> **There is a learning component, but nothing is ever trained** — all of it is plain numpy.
> The reason is that the decisive design choices in 3D networks follow from **structural
> properties** (identities, theorems, set operations, geometric computations), and those can
> be verified exactly without training and do not depend on the weights.
> Central thread: going from 2D to 3D turns almost every quantity from a product of two
> factors into a product of three, and those three reinforce each other
> (grid size → quantization error → IoU → positive samples).
> The sharpest result: $\text{IoU}=q/(2-q)$ gives a per-axis tolerance of exactly $s_i/3$,
> so a traffic sign's 0.049 m tolerance sits at **0.98×** typical annotation noise (0.05 m) —
> which means **a perfect model's AP@IoU0.5 ceiling on signs is only 0.392**
> (it is 1.000 under the center-distance criterion).
> Builds on C72; splits with C74/C75 as "discrete representations + discriminative tasks"
> versus "continuous representations + generative tasks".
> Neither touches C11 (retrieval algorithms) or C33 (context budget); both reuse those courses' definitions rather than redefining them.

#### C74 · 3D Gaussian Splatting & Real-Time Rendering

| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C74 | `C74_Gaussian_Splatting_Course/` | 3D Gaussian Splatting and real-time rendering (the volume-rendering / alpha-compositing foundation · the anisotropic Gaussian primitive and the limits of its projection · differentiable tile rasterization · adaptive density control and how reliable its criterion actually is · appearance, dynamics, and when *not* to use 3DGS) | Across all 472 existing lesson pages: `spherical harmonic` 0 hits, `alpha compositing` 0, `tile rasterization` 0, `EWA` 0; the few hits for volume rendering / alpha compositing / Gaussian Splatting are all one-line pointers in C72/C73/C55 that defer to this course |

> **One-sentence claim**: all of 3DGS's engineering value comes from **one difference in
> magnitude** — its primitives have *large* alpha (0.1–0.9) rather than small (0.01–0.05).
> Large alpha means only a dozen or so primitives per pixel and 92% of the work skippable by
> early termination, but it also means **depth sorting becomes mandatory** and you must accept
> the "one order shared per tile" approximation. Everything else (the covariance
> parameterization, the affine projection, density control, spherical harmonics) exists to make
> that difference in magnitude optimizable.
>
> **Because the chosen path through the 3D courses skipped NeRF, module 01 carries its own
> volume-rendering / alpha-compositing foundation.** The notebooks **build a working tile
> rasterizer from scratch** and check it against a per-pixel brute-force implementation
> **bit-for-bit** (which first requires enumerating all three approximations, not two).
>
> Four honest corrections: (1) the discretization error is **∝ 1/N²**, not ∝ 1/N — and for
> piecewise-constant density, **alpha compositing is exact, even at N=1**; (2) the governing
> variable for the affine approximation is the **subtended angle**, not off-axis position
> (100× versus 1.6×) — and at a 53° subtended angle **the projected covariance does not exist
> at all** (the second-moment integral diverges); (3) the bit-for-bit comparison was missing a
> third approximation (the 3σ bounding box is tile-aligned; its effect is 0.50 of one 8-bit
> color step); (4) "the scale gradient is a better densification criterion" was an artifact of
> a single run (averaged over six, it sits below the random baseline at every density).
>
> It also quantitatively corrects a widespread claim: **the "angular resolution ≈ 180/(ℓ+1)"
> rule overstates SH capability by about 1.45×.** The measured limit (at a 20% relative-residual
> criterion) is **125/(ℓ+1)** — degree 3 only reaches a **31.2°** half-angle, while polished
> plastic needs 12.3° and polished metal 3.4°.

#### C75 · 3D Reconstruction & 3D Generation

| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C75 | `C75_Reconstruction_Generation_Course/` | 3D reconstruction and 3D generation (an overview of the four routes · SfM and bundle adjustment · dense multi-view stereo · feed-forward regression (monocular depth and pointmaps) · SDS and multi-view diffusion · meshing and 3D evaluation) | Across all 478 existing lesson pages: `Structure from Motion`, `bundle adjustment`, `gauge`, `Schur`, `stereo matching`, `cost volume`, `plane sweep`, `monocular depth`, `TSDF`, `Marching Cubes`, `Poisson reconstruction`, `Score Distillation` and `Chamfer distance` all had **zero** hits (the single `Chamfer` hit is in C54's Hungarian-matching context, and all nine `ICP` hits are substrings of **ICPR**) |

> **One principled constraint frames the whole course**: scale the scene points and the camera
> translation together by $s$ and the rendered image is **bit-identical** (the notebook takes $s$
> to $10^3$; the largest pixel difference is $1.1\times10^{-13}$). So "metres from images" is
> impossible in principle — every route must inject external information somewhere, and
> **where it injects that information is the biggest difference between these methods.**
>
> **Unlike C72/C73/C74, this course runs real optimization but trains no neural network.**
> Module 01 has a converging bundle adjustment (LM + Schur complement), module 02 a plane sweep,
> module 04 an SDS loop on an analytically known prior — because the core questions here *are*
> questions about optimization (what is observable, how large the condition number is, which
> fixed point it converges to). Modules 03 and 04 use analytically constructed stand-ins,
> because what they verify are **protocols** and **properties of the objective**.
>
> **A thread running through the whole course**: every module contains one thing that looks like
> a precision problem but is really an **observability** problem — pure rotation in module 01
> (the null space grows from 7 to **npt+6**), periodic texture in module 02 (the error is
> **independent of noise**), absolute scale in module 03 (unobservable in principle), Janus in
> module 04 (the strict optimum of the objective), and Chamfer distance in module 05 (not a
> metric, so "0.1 apart" is not transitive).
>
> **Six honest corrections**, three worth singling out: (1) when I first measured "a small
> baseline blows the condition number up to $10^{19}$", my camera trajectory rotated 100° while
> barely translating, so **25–33 of 40 points ended up behind the camera** (projected $u$ up to
> 520,000 px) — I was measuring a broken scene, not a small-baseline effect; switching to a
> look-at trajectory produced the clean $\propto (B/z)^{-2}$ law; (2) **forward motion does not
> degenerate $E$** ($\sigma_8/\sigma_9 = 1.3\times10^{15}$) — what degenerates is
> **triangulation**; (3) **"the $-\epsilon$ term in SDS is a variance-reducing control variate"
> holds only at high noise or near a mode** — at low noise it *increases* the variance by 391×.
> The only unconditional statement is that it does not change the expectation.
>
> **Two unexpected findings**: under pure rotation the null space is exactly **npt + 6** (it grows
> with scene size, rather than being "7 plus a bit"); and with prior weights $(0.9, 0.1)$ the
> minor mode **stops being an attractor at all** — SDS produces 100%/0%, not 90%/10%.


| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C76 | `C76_Causal_Inference_Course/` | Causal inference and online attribution (the potential-outcomes framework · causal graphs and the back-door criterion · propensity scores / IPW / doubly robust / DML · DiD / IV / RDD / synthetic control · SUTVA and interference, cluster randomization, multi-touch attribution, surrogate metrics) | Across all 484 existing lesson pages: `potential outcome`, `instrumental variable`, `2SLS`, `difference-in-differences`, `synthetic control`, `double machine learning`, `doubly robust`, `positivity`, `parallel trends`, `SUTVA`, `spillover`, `cluster randomization`, `switchback`, `multi-touch`, `last-touch`, `uplift model`, `back-door criterion` and `AIPW` all had **zero** hits. All eight `backdoor` hits are **backdoor attacks** (C29/C44, security); of the six `propensity` hits, four are "propensity" in the safety-eval sense (capability vs propensity) and two are C47/C63's position-bias IPS; the single `potential outcome` hit is one sentence in C10-07 noting that randomization makes $T$ independent of the potential outcomes — which is exactly the boundary this course starts from |

> **One algebraic identity frames the whole course**: the naive difference $=$ ATT $+$ selection bias.
> This is not an approximation — on this course's synthetic population
> `1.582605 = 0.647736 + 0.934869`, and **the two sides differ by exactly 0**.
> Every identification strategy (randomization, back-door adjustment, instrumental variables,
> difference-in-differences) does the same one thing: **give the selection-bias term a reason
> to be zero (or to be estimable)**.
>
> **Zero overlap with C10 module 07**, which owns the entire A/B statistics toolkit
> (hypothesis testing, power and MDE, multiple comparisons, sequential testing, CUPED).
> None of that is repeated here. This course is positioned as
> **"C10-07 assumes randomization works; this course handles the cases where it doesn't, or isn't enough."**
>
> **The thread running through the whole course**: causal-inference failures almost never
> show up as errors — they show up as **answering a different question correctly**.
> **Not one** of the dozen-plus failure scenarios in this course raises an error.
> Each produces a well-formed, tight-confidence-interval, seed-reproducible number
> that would sail through a weekly report:
> you think you are estimating the population ATE, and you get the ATT instead
> (**2.09× apart**) · or "the ATE over strata that happen to have both arms"
> (at $K{=}800$ the estimator **silently discards 22.2% of the sample**) ·
> or the **direct** effect ($2.90 \to 2.00$, losing 31%) ·
> or the ATE on the overlap population ($2.0019 \to 1.4371$, while the excluded 16.1%
> have an effect of **+4.96** — the strongest group) ·
> or an estimate indistinguishable from the one it was meant to fix (**1.8009 vs 1.7994**) ·
> or the direct rather than the global effect (**1.00 vs 2.00**) ·
> or an accounting share allocated by exposure order (a true share of **7.1% booked as 38.0%**) ·
> or only the part of the long-term effect that flows through the surrogate
> (short-term **+1.005**, long-term **−0.999** — **the sign flips**).
>
> **Two bit-level identities**, both showing that "doubly robust" can vanish without any error:
> (1) **a constant $\hat e$ makes AIPW $\equiv$ G-computation** — per-arm OLS with an intercept
> forces the within-arm residuals to sum to exactly 0, so the correction term is identically 0
> **regardless of whether $\hat e$ is right** (agreement to $< 2\times10^{-11}$ across four model
> sizes; at $q{=}400$ G-computation has already blown up to **+123.44**, and AIPW matches it
> bit-for-bit); (2) **overfitting eats the correction term continuously, by $4.4\times10^5$**
> ($3.15\times10^{-1} \to 7.08\times10^{-7}$, monotone) — **a stronger outcome model shuts the
> de-biasing mechanism off**, and no goodness-of-fit metric flags it.
>
> **Six honest corrections**, four worth singling out:
> (1) **"smaller RDD bandwidth means smaller bias" is false when the curvature is *symmetric*
> about the cutoff** — the local-linear biases on the two sides **cancel exactly** in the
> difference, so the optimal bandwidth becomes "use all the data" ($h^{*}{=}1.0$).
> Only with different curvature on the two sides does an interior optimum appear
> ($h^{*}{=}0.2$, while $h{=}1.0$ is off by 0.4175). The corrected conclusion is more useful
> than the original: **RDD bias depends on the *difference* between the two sides' shapes,
> not on the magnitude of the curvature**;
> (2) **"cross-fitting in DML always helps" is wrong** — in the partially-linear
> residual-on-residual score it was **worse in all four setups** (nuisance overfitting deflates
> $\tilde T$ and $\tilde Y$ together, and they cancel in the ratio). It is necessary in the
> **AIPW score**, and even there it is a **necessary but not sufficient** condition
> (at $q{=}320$ the cross-fitted G-computation is still **+36.64**);
> (3) **"orthogonalization is a new estimator" is false under OLS nuisance** —
> Frisch–Waugh–Lovell: `1.4633431908608447` vs `1.4633431908608445`, a difference of
> $2.2\times10^{-16}$. So "switching to DML" **changes nothing** when the nuisance is an OLS;
> (4) **my first doubly-robust table could not prove what it was meant to prove** —
> I made the outcome-model misspecification an $X^2$ term identical in both arms, so it
> **cancelled automatically** in $\hat m_1 - \hat m_0$ and the "wrong" model returned 1.9928
> (nearly unbiased). The lesson: before verifying "what happens when model A is wrong",
> confirm that A is wrong in a direction that **actually reaches the estimator**.
>
> **Two unexpected findings**: (1) **collider bias has a closed form** — with
> $Z = X+Y+\varepsilon$ the conditional correlation is exactly $-1/(1+\sigma^2)$
> (measured $-0.91698$ vs theory $-0.91743$), so its strength is not "how bad might it be"
> but **computable in advance**; (2) **M-bias requires all four edges to be present at once** —
> break any one and the bias returns from $-0.31$ to $\pm0.003$. That explains why its
> practical magnitude is often small, and it means the section's point is not
> "never control for pre-treatment variables" but **"temporal order is not the criterion."**
>
> Two rules of thumb also get quantified: **the break-even CATE-estimation noise for targeted
> rollout scales as $\text{sd}(\tau)^2/\text{ATE}$** — a **quadratic** law, so doubling the
> heterogeneity buys 3.79–3.92× more noise tolerance rather than 2× (the invariant holds at
> 0.779–1.130); and **the predictive value of a synthetic control's pre-period fit for its
> post-period accuracy is 2/4** — a coin flip (unconstrained OLS fits the pre-period better in
> 4/4 setups but has lower post-period RMSE in only 2/4; and when a new factor appears in the
> post period, **the pre-period RMSE is bit-identical** while the post-period RMSE rises 3.0×).
>
> **Five places where the course's own configuration fails its own acceptance checks**
> (deliberate): the RMSE-optimal stratum count in m01, $K^{*}{=}200$, is **already discarding
> 2.5% of the sample** · m03's `DR_COLLAPSED` alert **has false positives** (scenario 1 fires it
> while the estimate is correct; it must be paired with the in-fold/out-of-fold residual ratio:
> 1.00 harmless vs 2.63 dangerous) · m04's `in_hull` proxy has **no threshold that achieves both
> TPR>95% and FPR<5%** (at the optimum of 2.2 the FPR is still 13.3%) · m04's pre-registration
> template catches 3/4 of the known-bad analyses and **misses the DiD one** (that problem lives
> in the unfalsifiable half) · and m05's auditor raises no alert for design C, which nonetheless
> carries roughly −0.15 of interference bias.

| # | Directory | Topic | Gap it fills |
|---|-----------|-------|--------------|
| C77 | `C77_Video_World_Models_Course/` | Video and world models (the cost of the time axis · video latents and tokenizers · the expressivity limits of spatiotemporal attention · autoregressive drift · the two meanings of "world model" · three pathologies of video evaluation) | Across all 490 existing lesson pages: `video generation`, `video diffusion`, `spatiotemporal attention`, `3D VAE`, `video tokenizer`, `temporal consistency`, `optical flow`, `frame interpolation`, `latent video`, `latent dynamics`, `training in imagination`, `action-conditioned`, `long-horizon drift`, `FVD`, `Fréchet Video`, `video benchmark` and `CLIP-SIM` all had **zero** hits. Every non-zero hit was checked one by one and **all of them are either homonyms or one-line pointers to this course**: all 10 word-boundary `DiT` hits are referrals to C28, and *every* mention of video/spacetime inside C28 is an explicit "deferred to later" · `world model`/`Dreamer` belong to **C41 module 04** (the planning side) · the 4 `causal convolution` hits are C20's unrolled-SSM view and C35's streaming audio codecs · the 4 `compounding error` hits belong to C04 (agent cascades), C41-04 (planning), C59 (imitation learning) and C63 (multi-stage systems) · all 12 `temporal consistency` hits sit in **perception/evaluation** contexts (C14/C18/C55) · and the single `VBench` hit is a substring of **MVBench**, a video *understanding* benchmark |

> **One shape runs through the whole course**: every cheap approximation on the time axis
> produces an **exactly computable** cost somewhere else — and **none of those costs raise an error**.
>
> | The cheap approximation | The exact cost | Raises an error? |
> |---|---|---|
> | Temporal compression $p_t$ | $\rho_{\text{eff}} = \rho^{p_t}$; latent frame count $T/p_t$ | No |
> | Treating frames independently | 3D gain $= f(\text{corr})$, and it is **negative** at corr$=0$ ($0.984\times$) | No |
> | Factorized spatiotemporal attention | Kronecker rank $1$ — cannot represent acceleration | No |
> | Serial wiring (vs parallel) | rank $1$ vs $m^2{-}m{+}1$ | No |
> | One-step fitting (teacher forcing) | rollout motion energy is only $35\%$–$49\%$ of the truth | No |
> | Reporting means instead of medians | the mean is dominated by $10\%$ collapsed samples ($10^{16}$ apart) | No |
> | "Good one-step accuracy means a good model" | a $3.95\%$ one-step error → a $251\%$ reward overestimate | No |
> | Diagnosing on the training distribution | at $g{=}0$ the matched and misspecified curves are **pointwise identical** | No |
> | Computing FVD from per-frame features | frame-order sensitivity $7.1\times10^{-15}$ | No |
> | Comparing FVD across different $N$ | the null value scales as $1/N$ (already $9.33$ at $N{=}64$) | No |
>
> **Zero overlap with C28 / C41-04.** C28 already covers the five foundations of image
> diffusion (latent diffusion, the DiT architecture, flow matching, CFG, consistency models),
> and **every single** mention of video inside C28 is a forward-pointer:
> "SoRA generalizes the patch to spacetime", "a temporally consistent VAE is much harder than
> an image one, and a high-quality video VAE is still the bottleneck", "extending CM /
> adversarial distillation to video DiT is the key step for real-time video generation".
> **This course is the expansion of those one-liners.** And C41 module 04 owns the planning
> side (MPC / Dyna / compounding error in planning); this course covers only the generative
> side and quantifies the boundary between them explicitly.
>
> **No neural network is trained.** Every property this course establishes — compression
> ratios, Kronecker rank, spectral radius, moment matching, finite-sample bias — lives at the
> level of linear algebra and statistics. A network would hide them: inside a trained video
> model, "factorized attention cannot represent acceleration" shows up as "the motion looks
> wrong in some samples", never as a rank you can assert.
>
> **Five honest corrections, and the one in module 02 was wrong three times in a row**:
> (1) I guessed "several objects each at a different constant velocity cannot be factorized" —
> **wrong**, the optimal Kronecker approximation error is **exactly 0** (the spatial
> re-indexing is <u>a single fixed matrix</u>, so $M = A_t \otimes P$ is still a Kronecker
> product). The precise criterion is "the spatial pattern must be $t$-independent and the
> temporal pattern $x$-independent", so **what cannot be factorized is acceleration and
> direction change, not "multiple objects"**; (2) I guessed "stacking more layers recovers it" —
> **wrong**, a product of Kronecker products is still a Kronecker product, and eight stacked
> layers stay at rank $1$; (3) I guessed "residual connections recover it" — **also wrong**,
> $(I + I{\otimes}A_s)(I + A_t{\otimes}I) = (I + A_t) \otimes (I + A_s)$, verified to
> $0.000\times10^{0}$. Only the fourth guess was right: **parallel branches** are the source of
> expressivity (ranks $2/4/16$). (4) "Multi-step / rollout loss fixes the downward bias in
> $\hat a$" — **wrong** (the best $k$ jumps around $\{1,2,4\}$, and when the model is correctly
> specified the prediction errors across $k$ differ only in the 4th decimal). Its real function
> is to shift accuracy from short to long horizons **under misspecification**, and the reason is
> that "a one-step-fitted model has error $1.028 > 1.0$ at $H{=}4$ — **worse than predicting the
> mean**". (5) "Action distribution shift gets amplified by rollout" — **does not hold** (with a
> matched model the one-step error is completely flat across a 30× range of policy gain:
> $0.05360 \to 0.05461$, $+1.9\%$). The unified statement: **distribution shift alone is not the
> problem; misspecification × shift is** (the same shift raises the error **44×** under
> misspecification) — which also explains why "widen the training action range" works while
> "collect more data" does not.
>
> Two further method-level corrections: **stationarity must be diagnosed on a batch**
> (a single sequence's $s_2/s_1$ spans $0.67$–$1.59$ from p5 to p95 at $T{=}400$, while the
> batch median is $0.998 \pm 0.046$); and **the energy ratio must be computed against a batch
> of real sequences**, because the median of the sd estimator is itself only $0.885$ of the truth.
>
> **Two unexpected findings**: (1) **the saturation value of the Kronecker rank under parallel
> branches has a closed form, $m^2 - m + 1$** with $m = \min(T,S)$ — hit exactly on all seven
> configurations ($m = 3,4,5,6$ giving $7, 13, 21, 31$), and it is **strictly below** the naive
> bound $\min(T^2,S^2)$ (21 rather than 25 at $m{=}5$); (2) **FVD's blind spot is a property of
> the feature, and a well-chosen feature can move a higher-moment difference into the first two
> moments** — for a mode collapse whose mean, variance and temporal correlation are **all
> matched** and only the kurtosis changes from 3 to 1, the per-frame FVD ratio is $0.80$
> (**below** the same-distribution baseline, i.e. completely blind) while the spatiotemporal FVD
> amplifies $20.9\times$; the mechanism is concrete: the $\vert\Delta\vert$ feature converts a
> **fourth-moment** difference into a **first-moment** one.
>
> **Six places where the course's own configuration fails its own acceptance checks**
> (deliberate): m01's "the peak sits at the last frame of each chunk" does not hold at $s{=}2$
> (the within-chunk spread is $<5\times10^{-3}$; the claim's scope is $s\geq3$) · m02's entire
> Kronecker analysis is at the **linear-operator** level, so it gives a lower bound and does
> **not** prove that a serially-wired network cannot learn acceleration · in m01's exercise 1,
> the popular advice "use rollout loss to fix drift" **fails two of three tests** · m04 section 4's
> 10-step errors carry a **confound** (at $g{=}3$ the closed loop is itself unstable,
> $\rho(A+B\cdot3K)>1$, so a large part of that $199.86$ is not model error) · m04's exercise 4
> **partially refutes** "the four acceptance checks are mutually independent" (① and ② are
> coupled — no scaling makes ① pass while ② fails; what still holds is that ① implies neither ③
> nor ④) · and m05's exercise 2 shows coverage is **not** a universal patch for FVD's blind spot
> (on a moment-matched collapse it only drops to $0.90\times$).
>
> The deliverable is **ten checks that each re-run in a few lines of numpy**: estimating $\rho$ ·
> the upper bound on $p_t$ · the streaming cost · the codebook's entropy · Kronecker rank ·
> hops to global connectivity · $\rho(\hat A)$ · the collapse rate · batch-level stationarity ·
> and the frame-order permutation test. **Four of the ten refute a popular practice or claim**,
> and all ten can be run *before* a real model exists.
<a name="en-format"></a>
### Format of Each Course

```
CXX_Xxx_Course/
├── index.html          Course home page (module map + Open-in-Colab badges)
├── README.md           This course's own README (scope, boundaries vs. neighbors)
├── glossary.md          Glossary (≥12KB)
├── references.md        Reference list (papers/docs, ★ = must-read)
├── requirements.txt      Dependencies (most courses need only numpy/pandas/jupyterlab)
├── assets/style.css      One shared stylesheet across all 78 courses (byte-identical)
├── 00_setup/
│   ├── 00_overview.html         Course overview
│   └── 00_environment_check.ipynb
├── 01_xxx/
│   ├── 01_讲解.html              Deep-dive lesson
│   └── 01_xxx.ipynb              Matching notebook
└── ...  (5–10 modules per course)
```

Every notebook follows the same rhythm: **worked example (a minimal from-scratch implementation matching the lesson, self-checked with `print`+`assert`) → ✏️ exercises (`TODO` skeleton, `assert`-graded) → 📖 reference answers → 🧪 real-data / real-API capsule**.

<a name="en-paths"></a>
### Suggested Learning Paths

1. **Math foundations**: C07 → C19 → (C42 theory deep-dive, optional)
2. **Classic DL**: C15 → C16 → C17 → C18 → C13 → (C41 deep RL) → (C46 graph ML)
3. **LLM science**: C01 → C20 → C21 → C25 → C09 / C22
4. **Post-training / alignment**: C02 → C13 → C22 → C23
5. **Systems / performance / engineering**: C08 → C36 → C24 → C27 → (C38 frameworks) → (C39 distributed) → (C43 data engineering)
6. **Evaluation / safety / trust**: C03 → C10 → C05 → C12 → C06/C29 → (C44 adversarial) → (C45 privacy)
7. **Agent engineering**: C04 → C26 → C30 → C31 → C32 → C33 → C34
8. **Multimodality**: C00 → C28 → C35
9. **Research literacy (runs throughout)**: C40 research methodology
10. **Industry deployment**: C37 MLOps → (C47 recsys) → (C48 cloud deployment)
11. **Filling industry-role gaps**: C49 encoder/seq2seq → C50 HF ecosystem → C51 data augmentation → C48 deployment → C52 industrial research practice

<a name="en-layout"></a>
### Repository Layout

```
.
├── index.html               Site-wide course overview page
├── COURSES_PLAN.md            Full record of the curriculum plan & build history
├── ENV_SETUP.md                Notes for setting up the local conda environment
├── requirements-all.txt        Union of all 78 courses' dependencies (install once, run all)
├── _buildkit/                  House-style generator (coursekit.py) + each course's build scripts
├── C00_..._Course/ … C77_..._Course/   78 courses, layout described above
└── README.md                   This file
```

<a name="en-gpu"></a>
### About GPU / Colab / Quantization

- **The vast majority of notebooks are pure numpy/CPU** and run to completion on any machine (including Colab's free CPU runtime) — no GPU, network, or API key needed.
- A handful of courses (C00 VLM, C04's computer-use module, C27 model compression, C08's quantization module, C50 PEFT/TRL) genuinely load real HuggingFace models. Those notebooks default to **fp16**: 2–3B-class models need only 5–8GB VRAM, and even a 7B model fits on Colab's free **T4 (16GB)** — they do **not** default to quantization just to be safe on memory. Quantization only appears as actual lesson content where the course/module is specifically about quantization (C08's quantize-from-scratch, all of C27, the QLoRA lessons in C00/C50); everywhere else, a 4-bit option — if present at all — defaults to off and exists purely as a fallback for unusually tight VRAM.
- Every notebook has an official **`Open in Colab`** badge as its first cell, and every course's `index.html` has a small Colab button next to each module entry — click it and it runs in your browser, nothing to install locally.

<a name="en-env"></a>
### Environment & Dependencies

- **Full local environment**: one conda env (`courses`, Python 3.11) with PyTorch + the HuggingFace stack + common scientific-computing libraries covers all 78 courses — see [`ENV_SETUP.md`](./ENV_SETUP.md); the combined dependency list is [`requirements-all.txt`](./requirements-all.txt).
- **Just want one course**: `cd` into that course's folder and `pip install -r requirements.txt` — for most courses that file is only 4–5 lines (`numpy`/`pandas`/`jupyterlab`/`ipykernel`).
- Every cell that needs a heavier dependency (`transformers`/`bitsandbytes`/`qwen-vl-utils`, etc.) is wrapped in `try/except`: if it's not installed, there's no network, or no GPU, it degrades gracefully to a pure Python/numpy fallback or is skipped — **it will not crash the whole notebook**.

<a name="en-history"></a>
### Build History

- 2026-06-08 – 06-14: C00–C37 (38 courses) built.
- 2026-06-27 – 06-28: Full curriculum deepened to the "极深" (deep-dive) bar; 10 gap-filling courses (C38–C47) added; unified generator `coursekit.py` introduced. Reached 48 courses · 364 lesson pages · 316 notebooks.
- 2026-08-06: Gap analysis against an `LLM Research Engineer` job description added 5 more courses, C48–C52 (purely additive, the existing 48 were untouched). Reached **53 courses · 346 lesson pages · 346 notebooks**.
- 2026-08-12: Made the whole site Colab-ready (T4 or CPU runtime) — removed default memory-saving 4-bit quantization from courses that aren't about quantization (switched to fp16 default), and added an Open-in-Colab badge to all 346 notebooks and all 53 course home pages.
- 2026-08-17: Gap analysis against an XPENG "TSR 2D Detection" job description added 9 courses, C53–C61 (purely additive).
- 2026-08-19: Added C62–C65 for the three round-one interview blocks HR spelled out (coding / ML system design / ML knowledge Q&A + communication). Reached **66 courses · 424 lesson pages · 424 notebooks**.
- 2026-08-31: Gap analysis for "AI agents + LLM evaluation" added 4 courses, C66–C69 (purely additive). Across the four: 24 notebooks, 549 code cells, 96 exercise self-test asserts, all executed end to end in a two-pass run. Reached **70 courses · 448 lesson pages · 448 notebooks**.
- 2026-08-31 (second round, same day): Added C70 (RAG production engineering) and C71 (prompt and context programming). **A wrong gap analysis was corrected first** — the initially proposed "RAG evaluation" and "multi-agent orchestration" were already covered by C11 and C34 respectively and would have produced duplicate courses; the real gaps were only settled after re-scanning all 448 lesson pages. 12 notebooks, 272 code cells, 48 exercise self-test asserts, all verified two-pass. Reached **72 courses · 460 lesson pages · 460 notebooks**.
- 2026-09-08: Added C72 (multi-view geometry and multi-sensor spatio-temporal alignment). **The gap was verified by scanning all 460 lesson pages first**, and the five directions that were checked and found *already covered* were listed up front (scaling laws, speculative decoding, continual learning, annotation ops, distillation); what turned out to be genuinely absent was the pixel-to-metre geometric chain. 6 notebooks, 115 code cells, 24 exercise self-tests, all verified two-pass. **Five conclusions in this round were rewritten after real computation contradicted them**: the textbook accuracy benefit of DLT point normalization disappears once there is noise (45.8× with no noise, but only a 13% difference at 0.2 px corner noise — and normalization is *slightly worse*); "calibrating intrinsics and extrinsics separately makes them absorb each other\'s errors and be wrong at range" is false (the absorption is remarkably clean — the real issue is *identifiability*, and the only way to separate $c_y$ from pitch is to widen the image-row coverage: σ(pitch) 3.74° → 0.035°, a **106× improvement**, while the most convenient collection pattern is the worst one); PnP orthogonalization does not improve accuracy (direction error improves only 1.24× and reprojection RMS actually gets *worse*) — and the "14.5×" measured in the first draft was an artefact of a **metric used outside its domain** (the trace formula is only valid for orthogonal matrices; for non-orthogonal ones 40–47% of realizations get clipped to exactly 0.00°); "waiting for the next IMU sample beats extrapolating" is the wrong trade-off (waiting costs 2222× more); and rolling shutter is not worth modelling for small targets (0.005 px) while "one timestamp per frame" costs 0.667 m. There are also **two places where the course\'s own configuration fails its own acceptance checks** (the 5-view calibration set in module 02 fails on edge coverage; the uniform BEV grid in module 04 fails on both sampling rate and slope) — by design, not by accident. Reached **73 courses · 466 lesson pages · 466 notebooks**.
- 2026-09-09: Added C73 (3D representations and point-cloud deep learning). A scan of all 466 lesson pages confirmed that the whole cluster of current 3D directions had zero coverage (PointNet, PointPillars, voxels, point-cloud segmentation, stereo, monocular depth, SDF — all 0 hits). 6 notebooks, 117 code cells, 24 exercise self-tests, all verified two-pass. **Seven conclusions were rewritten after real computation contradicted them**, three worth singling out: `sum`/`mean` are *not* bitwise permutation-invariant (floating-point addition is not associative; the relative difference is 1.43e-15, whereas `max`/`min` are, being pure selections) — so a permutation-invariance unit test cannot use exact equality for all aggregations; `max` does *not* discard the point count entirely (a linear probe gives $R^2=0.76$, because extreme-value statistics depend on sample size); and the fastest-dilating active set is not a thin structure but a fully scattered one (22.05× versus 4.32× for a sheet), while the rule density orders the opposite way and the product of the two is bounded by the kernel size 27. **The sharpest result** (a closed derivation): the per-axis tolerance is exactly $s_i/3$, so a traffic sign's 0.049 m tolerance sits at **0.98×** typical annotation noise (0.05 m); setting the prediction equal to the ground truth and adding only annotation noise to the labels, the AP@IoU0.5 ceiling on signs is just **0.392** (trucks and cars are both 1.000, and under the center-distance criterion all four classes are 1.000) — **so that column measures annotation noise, not model capability**. There are also three places where the course's own configuration fails its own audits. Reached **74 courses · 472 lesson pages · 472 notebooks**.
- 2026-09-09: Added C74 (3D Gaussian Splatting and real-time rendering), the second course in the same batch of 3D topics. Gap check (keyword grep across all 472 existing lesson pages): `spherical harmonic` 0 hits, `alpha compositing` 0, `tile rasterization` 0, `EWA` 0; the few hits for volume rendering / alpha compositing / Gaussian Splatting / NeRF are all one-line pointers in C72/C73/C55 that defer to this course. **Because the chosen path through the 3D courses skipped NeRF, module 01 carries its own volume-rendering / alpha-compositing foundation.** 6 notebooks, 123 code cells, 24 exercise self-tests, all verified two-pass; the notebooks build a working tile rasterizer from scratch and check it against a per-pixel brute-force implementation **bit-for-bit**. **Four conclusions were rewritten after real computation contradicted them**, two worth singling out: (1) **for piecewise-constant density, alpha compositing is exact to machine precision, even at $N{=}1$** (error 0 at $N{=}1$, 8.9e−16 at $N{=}256$) — so the discretization error comes *only* from σ varying within a segment, and there the midpoint rule is **second order** (each doubling of $N$ cuts the error by 4.00×; my original ∝1/N was wrong); (2) **at a 53° subtended angle the projected covariance does not exist at all** — 2.28% of the mass falls at $z\le0$, samples approaching $z\to0^+$ project to infinity, and the second-moment integral diverges (the Monte-Carlo estimate grows 9× going from $n{=}10^4$ to $10^6$ and varies 3× across seeds), **so asking "how large is the affine approximation's error here" is the wrong question — the ground truth it would compare against does not exist**. Two more: the bit-for-bit comparison initially missed a third approximation (the 3σ bounding box is tile-aligned; its effect is 0.50 of one 8-bit color step); and "the scale gradient is a better densification criterion" was an artifact of a single run (67% top-quartile hit rate with one target and one seed, 28% averaged over six, and below the 25% random baseline at every density). It also quantitatively corrects a widespread claim: **the "angular resolution ≈ 180/(ℓ+1)" rule overstates SH capability by about 1.45×**; the measured limit (20% relative-residual criterion) is **125/(ℓ+1)** — degree 3 reaches only a **31.2°** half-angle, while polished plastic needs 12.3° and polished metal 3.4°, **so SH degree 3 can barely represent rough-plastic-grade specularity, and that is a limit of representational capacity, not of optimization**. There are also three places where the course's own configuration fails its own audits. Reached **75 courses · 478 lesson pages · 478 notebooks**.
- 2026-09-10: Added C75 (3D reconstruction and 3D generation), the third and final course in this batch of 3D topics. Gap check (keyword grep across all 478 existing lesson pages): `Structure from Motion`, `bundle adjustment`, `gauge`, `Schur`, `stereo matching`, `cost volume`, `plane sweep`, `monocular depth`, `TSDF`, `Marching Cubes`, `Poisson reconstruction`, `Score Distillation` and `Chamfer distance` all had **zero** hits; the single `Chamfer` hit sits in C54's Hungarian-matching context, and all nine `ICP` hits are substrings of **ICPR**. 6 notebooks, 125 code cells, 24 exercise self-tests, all verified two-pass. **Unlike C72/C73/C74, this course runs real optimization (bundle adjustment, plane sweep, SDS) but trains no network** — because the core questions here *are* questions about optimization (observability, conditioning, fixed points). **Six conclusions were rewritten after real computation contradicted them**, three worth singling out: (1) when I first measured "a small baseline blows the condition number up to $10^{19}$", the camera trajectory rotated 100° while barely translating, so **25–33 of 40 points ended up behind the camera** (projected $u$ up to 520,000 px) — I was measuring a broken scene, not a small-baseline effect; switching to a look-at trajectory produced the clean $\propto (B/z)^{-2}$ law (measured exponent −2.00 in the small-baseline regime). (2) **Forward motion does not degenerate $E$** ($\sigma_8/\sigma_9 = 1.3\times10^{15}$) — what degenerates is **triangulation** (the ray angle near the epipole is only 1/7.5 of the outer ring); these are two different things, and conflating them sends you to fix the wrong stage. (3) **"The $-\epsilon$ term in SDS is a variance-reducing control variate" holds only at high noise or near a mode**: the effect fully reverses across $t$ — at $t{=}0.05$ it *increases* the variance by **391×**, at $t{=}0.95$ it reduces it by 1533×. The only unconditional statement is that it does not change the expectation (and the difference between the two estimators contains no $x$ at all — bit-identical at six different $x$). **Two unexpected findings**: under pure rotation the null space is exactly **npt + 6** (verified across five configurations — every point's depth is unobservable, plus 3 global rotation and 3 global translation, with scale absorbed into the per-point depths, so it grows with scene size rather than being "7 plus a bit"); and with prior weights $(0.9, 0.1)$ the minor mode **stops being an attractor**, so SDS produces **100%/0%** rather than 90%/10% — meaning "diversity collapse" is not just flattened probabilities but minority modes vanishing from the dynamics outright. It also quantifies three evaluation protocols that are routinely left vague: for monocular depth, the three protocol choices (alignment **domain** × degrees of freedom × per-image vs global) are each worth one to two orders of magnitude and **154× together**, and the rule is that "the alignment domain must match the domain in which the model is invariant" (verified in both directions, which means **the evaluation protocol cannot be defined independently of the model**); **Chamfer distance is not a metric** (counterexample $20 > 5{+}5$, violating by 2×, so "0.1 apart in CD" is not transitive); and **CD-L1 is linear in outliers while CD-L2 is quadratic** (one outlier at 50× the object radius raises L1 by 1.31× and L2 by **293×**, with the closed form $(d{-}1)^p/n$ matching measurement to 2e-4). Reached **76 courses · 484 lesson pages · 484 notebooks**.
- 2026-09-10: Added C76 (causal inference and online attribution). Gap check (keyword grep across all 484 existing lesson pages): `potential outcome`, `instrumental variable`, `2SLS`, `difference-in-differences`, `synthetic control`, `double machine learning`, `doubly robust`, `positivity`, `parallel trends`, `SUTVA`, `spillover`, `cluster randomization`, `switchback`, `multi-touch`, `last-touch`, `uplift model`, `back-door criterion` and `AIPW` all had **zero** hits; all eight `backdoor` hits are **backdoor attacks** (C29/C44), four of the six `propensity` hits are "propensity" in the safety-eval sense and two are C47/C63's position-bias IPS, and the single `potential outcome` hit is one sentence in C10-07 — which is exactly the boundary this course starts from. 6 notebooks, 106 code cells, 24 exercise self-tests, all verified two-pass. **Zero overlap with C10 module 07**, which owns the entire A/B statistics toolkit (hypothesis testing, power/MDE, multiple comparisons, sequential testing, CUPED); none of it is repeated. The course is positioned as "C10-07 assumes randomization works; this course handles the cases where it doesn't, or isn't enough." **The whole course is framed by one algebraic identity**: the naive difference $=$ ATT $+$ selection bias — not an approximation; measured `1.582605 = 0.647736 + 0.934869`, with **the two sides differing by exactly 0**. **The thread running through the course: causal-inference failures almost never show up as errors — they show up as answering a different question correctly.** **Not one** of the dozen-plus failure scenarios raises an error; each produces a well-formed, tight-interval, seed-reproducible number (you think you are estimating the population ATE and get the ATT, 2.09× apart / or "the ATE over strata that have both arms", with $K{=}800$ **silently discarding 22.2% of the sample** / or the direct effect, $2.90 \to 2.00$, losing 31% / or the overlap-population ATE, $2.0019 \to 1.4371$, while the excluded group's effect is **+4.96** / or an estimate indistinguishable from the one it was meant to fix, **1.8009 vs 1.7994** / or the direct rather than the global effect, **1.00 vs 2.00** / or an accounting share allocated by exposure order, a true share of **7.1% booked as 38.0%** / or only the part of the long-term effect flowing through the surrogate, short-term **+1.005** and long-term **−0.999** — **the sign flips**). **Two bit-level identities**, both showing that "doubly robust" can vanish without any error: (1) **a constant $\hat e$ makes AIPW $\equiv$ G-computation** — per-arm OLS with an intercept forces within-arm residuals to sum to exactly 0, so the correction term is identically 0 **regardless of whether $\hat e$ is right** (agreement to $< 2\times10^{-11}$ across four model sizes; at $q{=}400$ G-computation has already blown up to **+123.44** and AIPW matches it bit-for-bit); (2) **overfitting eats the correction term continuously, by $4.4\times10^5$** ($3.15\times10^{-1} \to 7.08\times10^{-7}$, monotone) — **a stronger outcome model shuts the de-biasing mechanism off**, and no goodness-of-fit metric flags it. **Six conclusions were rewritten after real computation contradicted them**, four worth singling out: (1) **"smaller RDD bandwidth means smaller bias" is false when the curvature is *symmetric* about the cutoff** — the two sides' local-linear biases **cancel exactly** in the difference, so the optimal bandwidth becomes "use all the data" ($h^{*}{=}1.0$); only with different curvature on the two sides does an interior optimum appear ($h^{*}{=}0.2$; $h{=}1.0$ is off by 0.4175). **RDD bias depends on the *difference* between the two sides' shapes, not the magnitude of the curvature**; (2) **"cross-fitting in DML always helps" is wrong** — in the partially-linear residual-on-residual score it was **worse in all four setups** (overfitting deflates $\tilde T$ and $\tilde Y$ together and they cancel in the ratio); it is necessary in the **AIPW score**, and even there it is **necessary but not sufficient** (at $q{=}320$ the cross-fitted G-computation is still **+36.64**); (3) **"orthogonalization is a new estimator" is false under OLS nuisance** — Frisch–Waugh–Lovell: `1.4633431908608447` vs `1.4633431908608445`, differing by $2.2\times10^{-16}$, so "switching to DML" **changes nothing** when the nuisance is an OLS; (4) **my first doubly-robust table could not prove what it was meant to prove** — I made the outcome misspecification an $X^2$ term identical in both arms, so it **cancelled automatically** in $\hat m_1 - \hat m_0$ and the "wrong" model returned 1.9928 (nearly unbiased). The lesson: before verifying "what happens when model A is wrong", confirm A is wrong in a direction that **actually reaches the estimator**. **Two unexpected findings**: **collider bias has a closed form** (with $Z = X+Y+\varepsilon$ the conditional correlation is exactly $-1/(1+\sigma^2)$; measured $-0.91698$ vs theory $-0.91743$ — so its strength is not "how bad might it be" but **computable in advance**); and **M-bias requires all four edges at once**, with the bias returning from $-0.31$ to $\pm0.003$ if any one is broken — so that section's point is not "never control for pre-treatment variables" but **"temporal order is not the criterion."** Two rules of thumb also get quantified: **the break-even CATE-estimation noise for targeted rollout scales as $\text{sd}(\tau)^2/\text{ATE}$** (a **quadratic** law: doubling the heterogeneity buys 3.79–3.92× more noise tolerance, not 2×); and **the predictive value of a synthetic control's pre-period fit for post-period accuracy is 2/4** — a coin flip (unconstrained OLS fits the pre-period better in 4/4 setups but has lower post-period RMSE in only 2/4; when a new factor appears post-period, **the pre-period RMSE is bit-identical** while the post-period RMSE rises 3.0×). There are also **five places where the course's own configuration fails its own acceptance checks**. Reached **77 courses · 490 lesson pages · 490 notebooks**.
- 2026-09-10: Added C77 (video and world models). Gap check (keyword grep across all 490 existing lesson pages): `video generation`, `video diffusion`, `spatiotemporal attention`, `3D VAE`, `video tokenizer`, `temporal consistency`, `optical flow`, `frame interpolation`, `latent video`, `latent dynamics`, `training in imagination`, `action-conditioned`, `long-horizon drift`, `FVD`, `Fréchet Video`, `video benchmark` and `CLIP-SIM` all had **zero** hits; every non-zero hit was checked one by one and **all are either homonyms or one-line pointers to this course** — all 10 word-boundary `DiT` hits are referrals to C28, and **every mention of video/spacetime inside C28 is an explicit "deferred to later"** ("SoRA generalizes the patch to spacetime", "a temporally consistent VAE is much harder than an image one and a high-quality video VAE is still the bottleneck", "extending CM / adversarial distillation to video DiT is the key step for real-time video generation"); `world model`/`Dreamer` belong to C41 module 04 (planning side); the 4 `causal convolution` hits are C20's unrolled-SSM view and C35's streaming audio; the 4 `compounding error` hits span four distinct mechanisms across C04/C41-04/C59/C63; all 12 `temporal consistency` hits are in perception/evaluation contexts; and the single `VBench` hit is a substring of **MVBench**. 6 notebooks, 93 code cells, 24 exercise self-tests, all verified two-pass. **Zero overlap with C28 / C41-04**: this course is the expansion of C28's one-liners, while C41-04 owns the planning side and this one covers only generation, quantifying the boundary explicitly. **No neural network is trained** — every property here (compression ratios, Kronecker rank, spectral radius, moment matching, finite-sample bias) lives at the level of linear algebra and statistics, and a network would only hide them. **The shape running through the course: every cheap approximation on the time axis produces an exactly computable cost somewhere else, and none of those costs raise an error** (ten of them are tabulated in the C77 section above; the last column is "No" throughout). **Five conclusions were rewritten after real computation contradicted them, and the one in module 02 was wrong three times in a row**: (1) I guessed "several objects each at a different constant velocity cannot be factorized" — **wrong**, the optimal Kronecker approximation error is **exactly 0** (the spatial re-indexing is a single fixed matrix, so $M = A_t \otimes P$ is still a Kronecker product); the precise criterion is "the spatial pattern must be $t$-independent and the temporal pattern $x$-independent", so **what cannot be factorized is acceleration and direction change, not "multiple objects"**; (2) I guessed "stacking more layers recovers it" — **wrong**, a product of Kronecker products is still a Kronecker product and eight layers stay at rank 1; (3) I guessed "residual connections recover it" — **also wrong**, $(I + I{\otimes}A_s)(I + A_t{\otimes}I) = (I + A_t) \otimes (I + A_s)$, verified to $0.000\times10^{0}$; only the fourth guess was right: **parallel branches** are the source of expressivity (ranks 2/4/16, versus 25 for full 3D). (4) "Multi-step / rollout loss fixes the downward bias in $\hat a$" — **wrong** (the best $k$ jumps around {1,2,4}; when the model is correctly specified the prediction errors across $k$ differ only in the 4th decimal); its real function is to shift accuracy from short to long horizons **under misspecification**, and the reason is that "a one-step-fitted model has error $1.028 > 1.0$ at $H{=}4$ — **worse than predicting the mean**". (5) "Action distribution shift gets amplified by rollout" — **does not hold** (with a matched model the one-step error is completely flat across a 30× range of policy gain: $0.05360 \to 0.05461$, $+1.9\%$); the unified statement is that **distribution shift alone is not the problem, misspecification × shift is** (the same shift raises the error **44×** under misspecification), which also explains why "widen the training action range" works while "collect more data" does not. Two further method-level corrections: **stationarity must be diagnosed on a batch** (a single sequence's $s_2/s_1$ spans 0.67–1.59 from p5 to p95 at $T{=}400$; the batch median is $0.998 \pm 0.046$); and **the energy ratio must be computed against a batch of real sequences** (the median of the sd estimator is itself only 0.885 of the truth). **Two unexpected findings**: the saturation value of the Kronecker rank under parallel branches has a closed form, **$m^2-m+1$** with $m=\min(T,S)$, hit exactly on all seven configurations (7/13/21/31) and **strictly below** the naive bound $\min(T^2,S^2)$; and **FVD's blind spot is a property of the feature, while a well-chosen feature can move a higher-moment difference into the first two moments** — for a mode collapse whose mean, variance and temporal correlation are all matched and only the kurtosis changes from 3 to 1, the per-frame FVD ratio is **0.80 (below the same-distribution baseline, i.e. completely blind)** while the spatiotemporal FVD amplifies **20.9×**, the mechanism being that $\vert\Delta\vert$ converts a fourth-moment difference into a first-moment one. There are also **six places where the course's own configuration fails its own acceptance checks**. The deliverable is **ten checks that each re-run in a few lines of numpy**, four of which refute a popular practice, and all ten can be run before a real model exists. Reached **78 courses · 496 lesson pages · 496 notebooks**.

Full details in [`COURSES_PLAN.md`](./COURSES_PLAN.md).
