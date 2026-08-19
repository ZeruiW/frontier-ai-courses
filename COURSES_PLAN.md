# 前沿 AI Researcher / Engineer 技能栈课程规划

> 体系：每模块 = 深度 HTML 讲解 + 真实可运行 notebook（✏️ 练习 TODO + assert 判分 + 📖 参考答案）。
> 受众：面向 frontier-lab 的 AI 研究科学家 / 研究工程师（起步于 model evaluation，已扩为全栈）。
> 讲解：中文 + 英文术语。全课 CPU-first、优雅回退、纯实现优先。
> 本次大改：**全谱深化到「极深」 + 新增 10 门补缺课（C38–C47）**。更新日期：2026-06-27。

---

## 总览：66 门课（C00–C65）

### 🆕 一面三板块补缺课 · C62–C65（HR 明确的面试形式）
> 触发：HR 补充「First Round Interview Format: **Technical Knowledge Assessment,
> Problem-Solving, and Practical (Coding) Exercise**」并提到 coding / system design / ML knowledge。
> JD 全文见 `JD_XPENG_TSR.md`。

| 课 | 文件夹 | 主题 | 补的洞 | 状态 |
|----|--------|------|--------|------|
| C62 | `C62_Coding_Interview_Course/` | 编程面试实战：算法与数据结构（六步答题协议 · 双指针/滑窗/前缀和 · 哈希排序二分 · 树图与搜索 · DP 与贪心 · 模拟面试） | 全库最大缺口：62 门课里「链表」「双指针」零命中 | ✅ 已完成 |
| C63 | `C63_ML_System_Design_Course/` | ML 系统设计面试（七步框架 · 需求与指标 · 数据系统 · 建模评测 · 容量估算 · 六案例库） | C07 仅一节 system design 框架，无方法论与案例库 | ✅ 已完成 |
| C64 | `C64_ML_Knowledge_QA_Course/` | ML/DL 技术知识问答（三段式答法 · ML 基础 · 优化训练 · 架构 · 评估统计 · 快问快答题库） | C07 教推导，缺「60 秒讲清 + 接住追问」的广度题库 | ✅ 已完成 |
| C65 | `C65_ProblemSolving_Communication_Course/` | 结构化问题求解与面试沟通（估算 · 诊断归因 · 权衡决策 · 模糊需求澄清 · 白板与英文表达） | 估算/诊断/权衡/澄清/沟通均无系统覆盖 | ✅ 已完成 |


图例 — 深度：🟢 极深（对标 C06/C00） · 🟡 待深化（本轮目标）· 🆕 新建（本轮）。

### 核心 LLM / 评测主线 · C00–C09（🟢 已极深）
| 课 | 文件夹 | 主题 |
|----|--------|------|
| C00 | `C00_VLM_Multimodal_Course/` | VLM 与多模态 AI（10 模块，最深） |
| C01 | `C01_LLM_Internals_Course/` | LLM 内核：从零实现 Transformer |
| C02 | `C02_Post_Training_Course/` | 后训练与对齐：SFT→RLHF/DPO→RLVR |
| C03 | `C03_LLM_Evals_Course/` | 评测科学：基准、统计与 Judge ★ |
| C04 | `C04_AI_Agents_Course/` | AI 智能体与 agentic 评测 ★ |
| C05 | `C05_Safety_Evals_Course/` | 前沿模型安全评估与红队 |
| C06 | `C06_Interpretability_Course/` | 机制可解释性 ★（深度样板课） |
| C07 | `C07_ML_Foundations_Course/` | ML 基础与面试数学 |
| C08 | `C08_Training_Systems_Course/` | 大模型训练与推理系统（账本） |
| C09 | `C09_Reasoning_TTC_Course/` | 推理模型与测试时计算 ★ |

### 评测/地基补全 · C10–C19（🟡 → 本轮深化）
| 课 | 文件夹 | 主题 |
|----|--------|------|
| C10 | `C10_Eval_Measurement_Course/` | 评测数据与测量科学（IRT/校准/AB）★ |
| C11 | `C11_RAG_Retrieval_Course/` | 检索增强与长上下文评测 ★ |
| C12 | `C12_Responsible_AI_Course/` | 负责任 AI 与社会影响评测 ★ |
| C13 | `C13_RL_Foundations_Course/` | 强化学习地基（MDP→PG→AC→bandits） |
| C14 | `C14_DL_Theory_Data_Course/` | DL 理论与数据/生成媒体评测 |
| C15 | `C15_Classic_Architectures_Course/` | 经典神经网络架构（CNN/RNN/LSTM/seq2seq） |
| C16 | `C16_Generative_Models_Course/` | 生成模型（AE/VAE/GAN/扩散/Flow） |
| C17 | `C17_Classical_NLP_Course/` | 经典 NLP（word2vec/n-gram/HMM/CRF） |
| C18 | `C18_Computer_Vision_Course/` | 计算机视觉（检测/分割/自监督） |
| C19 | `C19_Bayesian_ML_Course/` | 概率与贝叶斯 ML（MCMC/VI/GP/PGM） |

### 前沿深潜 · C20–C29（🟡 → 本轮深化）
| 课 | 文件夹 | 主题 |
|----|--------|------|
| C20 | `C20_Frontier_Architectures_Course/` | 现代架构（RoPE/GQA/MLA/MoE/SSM）🟢样板 |
| C21 | `C21_Frontier_Pretraining_Course/` | 大规模预训练（数据/tokenizer/μP/稳定性） |
| C22 | `C22_Reasoning_RL_Course/` | 推理模型 RL（long-CoT/GRPO/PRM）o1/R1 |
| C23 | `C23_Frontier_Alignment_Course/` | 前沿对齐（CAI/可扩展监督/weak-to-strong） |
| C24 | `C24_Inference_Serving_Course/` | 高效推理服务（vLLM/SGLang 栈） |
| C25 | `C25_Long_Context_Course/` | 长上下文与高效注意力（YaRN/稀疏/KV压缩） |
| C26 | `C26_Frontier_Agents_Course/` | 前沿智能体（MCP/computer use/agentic RL） |
| C27 | `C27_Model_Compression_Course/` | 模型压缩（量化/GPTQ-AWQ/蒸馏/剪枝） |
| C28 | `C28_Frontier_Diffusion_Course/` | 扩散与流前沿（DiT/flow/consistency） |
| C29 | `C29_Frontier_Interp_Course/` | 前沿机制可解释性（SAE/features/steering） |

### 动手造 Agent + 系统 · C30–C37（🟡 → 本轮深化）
| 课 | 文件夹 | 主题 |
|----|--------|------|
| C30 | `C30_Agent_Harness_Course/` | Agent Harness 从零（动手造 agent） |
| C31 | `C31_Coding_Agent_Course/` | 构建编码 Agent（你的 Claude Code） |
| C32 | `C32_Skills_Tools_Course/` | Skills 与工具生态（MCP server 从零） |
| C33 | `C33_Context_Memory_Course/` | 上下文工程与记忆 |
| C34 | `C34_Agent_Orchestration_Course/` | 多智能体编排与生产化 |
| C35 | `C35_Speech_Audio_Course/` | 语音与音频（ASR/codec/TTS/语音 LLM） |
| C36 | `C36_GPU_Kernels_Course/` | GPU 内核与性能工程（写 FlashAttention） |
| C37 | `C37_MLOps_Course/` | MLOps 与生产生命周期 |

### 🆕 本轮新增补缺课 · C38–C47（针对 AI Researcher/Engineer 能力树缺口）
| 课 | 文件夹 | 主题 | 补的洞 |
|----|--------|------|--------|
| C38 | `C38_Frameworks_Accel_Course/` | 深度学习框架与加速计算工程（PyTorch/JAX/autograd/compile/Triton） | 全栈 numpy 留下的「真实框架」空白 |
| C39 | `C39_Distributed_Training_Course/` | 分布式训练工程（NCCL/FSDP/3D 并行/容错） | C08 只给成本模型，缺可操作工程 |
| C40 | `C40_Research_Methodology_Course/` | 研究方法论与科学实践（复现/消融/写作/品味） | 「做研究本身」的元技能 |
| C41 | `C41_Deep_RL_Course/` | 深度强化学习与决策（DQN/PPO/SAC/offline/世界模型） | C13 只到地基，缺控制/世界模型 |
| C42 | `C42_Learning_Theory_Course/` | 学习理论与优化理论（PAC/NTK/隐式偏置/泛化界） | 研究科学家的理论脊梁 |
| C43 | `C43_Data_Engineering_Course/` | 大规模数据工程（去重/流式/吞吐/去污染） | 数据「基础设施」手艺 |
| C44 | `C44_Adversarial_Security_Course/` | 对抗 ML 与 AI 安全攻防（对抗样本/投毒/窃取/注入） | 经典 AML 与安全工程 |
| C45 | `C45_Privacy_Trustworthy_Course/` | 隐私保护与可信 ML（DP-SGD/联邦/遗忘） | 隐私技术本身（C12 只测量） |
| C46 | `C46_Graph_ML_Course/` | 图机器学习 GNN（message passing/GCN-GAT/图 transformer） | 缺失的几何深度学习分支 |
| C47 | `C47_RecSys_Ranking_Course/` | 推荐系统与大规模排序（双塔/LTR/CTR-DLRM/序列） | 工业界最大就业面 |


### 🆕 工业岗位补缺课 · C48–C52（针对 LLM Research Engineer JD 的剩余缺口）
> 触发：比对 `LLM Research Engineer` JD 后发现的 5 类未覆盖技能。**不改动既有课程，追加在末尾。**

| 课 | 文件夹 | 主题 | 补的洞 |
|----|--------|------|--------|
| C48 | `C48_Cloud_Deployment_Course/` | 云上部署与服务化（容器/OCI 层 · K8s 调和循环 · 灰度与自动扩缩 · 云调度与成本） | C37 讲 MLOps 生命周期、C24 讲推理引擎，缺「把服务真的放到云上」这一段 |
| C49 | `C49_Encoder_Seq2Seq_Course/` | Encoder 与 Seq2Seq（BERT/MLM · RoBERTa-ELECTRA-DeBERTa · 微调 · T5/BART · encoder 的今天） | 全谱直接从经典 NLP 跳到 decoder-only LLM，跳过了 BERT/T5 这一代 |
| C50 | `C50_HuggingFace_Ecosystem_Course/` | HuggingFace 生态实战（Auto* 与 from_pretrained · tokenizers/datasets · Trainer · PEFT/TRL · accelerate/Hub/API） | 全谱纯 numpy 实现，缺「真实生态里这些对应什么、坑在哪」 |
| C51 | `C51_Data_Augmentation_Course/` | 文本数据增强与合成数据工程（EDA/AEDA · 回译 · Self-Instruct/Evol/Magpie · 质控 · 消融） | C21/C43 讲预训练语料，缺「有标注任务训练集不够时怎么造与怎么验」 |
| C52 | `C52_Industrial_Research_Practice_Course/` | 工业研究工程实务（TF/Keras 心智模型 · 跨框架权重迁移 · ONNX 导出与运行时 · 真机 GPU 工作流 · 专利与开源合规） | 一批「没有归属却天天要用」的孤儿技能；JD 里的 TensorFlow、CUDA 诊断、patents 三项 |

### 🆕 自动驾驶感知 / TSR 岗位补缺课 · C53–C61
> 触发：比对 XPENG「Machine Learning Engineer / Computer Vision Engineer — Traffic Sign Recognition (TSR) 2D Detection」JD
> 后识别出的 9 个缺口（见根目录 `INTERVIEW_PREP_XPENG_TSR.md`）。**不改动既有课程，追加在末尾。**

| 课 | 文件夹 | 主题 | 补的洞 |
|----|--------|------|--------|
| C53 | `C53_RealTime_Detectors_Course/` | 实时检测器架构（YOLO 全代演进 · 标签分配 · RTMDet · RT-DETR · 延迟-精度选型） | JD 点名的 RT-DETR / RTMDet 全库零覆盖 |
| C54 | `C54_DETR_Set_Prediction_Course/` | 端到端集合预测检测（匈牙利匹配 · 集合损失 · object query · 收敛家族 · 工程实践） | 匈牙利匹配 / set prediction loss 全库零覆盖 |
| C55 | `C55_TSR_Autonomous_Driving_Course/` | 交通标志识别与自动驾驶感知（数据集与法规体系 · 两级 vs 端到端 · 失效模式 · 时序融合 · 安全评测） | TSR 领域知识与自动驾驶感知语境完全缺失 |
| C56 | `C56_Detection_Augmentation_Course/` | 检测数据增强工程（几何与标注同步 · 光度与域 · Mosaic/Copy-Paste · 流水线 · 消融验证） | C51 是文本增强；图像检测增强零覆盖 |
| C57 | `C57_Small_Object_Detection_Course/` | 小目标检测（IoU 尺度敏感性量化 · 多尺度架构 · NWD 与分配 · 切片推理 · TSR 物理推导） | C18 只提「小目标弱仍待解」，无技术手段 |
| C58 | `C58_HardCase_LongTail_Course/` | 难例挖掘与长尾数据闭环（不平衡谱系 · OHEM · 主动学习触发 · 挖掘基建 · 闭环验证） | 检测语境的 hard-case / 长尾挖掘缺失 |
| C59 | `C59_VLA_Perception_Interface_Course/` | 视觉-语言-动作模型与感知接口（VLM→VLA · 动作表示 · TSR 输出接口 · 规则约束化 · 评测上车） | JD 独有的 VLA 职责，全库零覆盖 |
| C60 | `C60_Edge_Deployment_Consistency_Course/` | 车端部署与训练-部署一致性（预处理对齐 · TensorRT · INT8 校准 · 后处理与 C++ · 延迟剖析） | C52 只到概念层，缺实操与一致性调试 |
| C61 | `C61_Detection_Practice_Interview_Course/` | 检测工程实战与面试实务（实验设计 · TIDE 误差分解 · 调试手册 · 项目叙事 · 面试题库） | production 手感与面试交付能力 |

---

## 「极深」标准（本轮全谱对齐，对标 C06）
- **HTML 讲解**：8–9 个编号小节、可见正文 ≥8000 字符（贴近 C06 的 ~10000）；meta-box + 本章地图 TOC + 页脚 pager；富用 callout（intuition/warn/danger/paper）、dual 双轨、表格、ascii 流程图、mathblock 推导；末节为「研究前沿与开放问题」。
- **Notebook**：≥30 cells；5–6 个 worked 小节（print+assert 自检）→ 3–4 道 ✏️ 练习（TODO 骨架 + assert 自测）→ 📖 参考答案 → 🧪 真实数据/真实配置胶囊。纯 numpy/CPU、自洽可跑。
- **glossary.md ≥12KB**、**references.md ≥8KB**（★ 标必读，注明"解决什么问题"）。

## 学习路径（建议）
1. **数学地基**：C07 → C19 →（C42 理论可选深潜）
2. **经典 DL**：C15 → C16 → C17 → C18 → C13 →（C41 深 RL）→（C46 图 ML）
3. **LLM 科学**：C01 → C20 → C21 → C25 → C09 / C22
4. **后训练/对齐**：C02 → C13 → C22 → C23
5. **系统/性能/工程**：C08 → C36 → C24 → C27 →（C38 框架）→（C39 分布式）→（C43 数据工程）
6. **评测/安全/可信**：C03 → C10 → C05 → C12 → C06/C29 →（C44 对抗）→（C45 隐私）
7. **Agent 工程**：C04 → C26 → C30 → C31 → C32 → C33 → C34
8. **多模态**：C00 → C28 → C35
9. **研究素养（贯穿）**：C40 研究方法论
10. **工业落地**：C37 MLOps →（C47 推荐系统）→（C48 云上部署）
11. **工业岗位补缺（C48–C52）**：C49 encoder/seq2seq → C50 HF 生态 → C51 数据增强 → C48 部署 → C52 研究工程实务（跨框架/导出/真机 GPU/专利）

---

## 工程规范
- 每门课独立文件夹：`assets/style.css`（全站同一份，md5 一致）、`index.html`、`README.md`、`glossary.md`、`references.md`、`requirements.txt`、各模块 `NN_xxx/`。
- **生成器**：`scratchpad/coursekit.py`（house-style HTML/index/notebook 生成器，纯 stdlib）。每门课写 `build_<cid>.py` 调用它产出文件；`json.dump(ensure_ascii=False)`。
- Notebook 铁律：CPU-first、纯 numpy 优先、API/GPU/联网一律优雅回退；每本 3–4 道 ✏️ 练习（TODO + assert 判分 + 📖 答案）+ 🧪 真实数据胶囊。
- 中文散文严禁 ASCII 双引号嵌套，一律用全角 “ ”。
- 验证分工：构建脚本用 `python3` 跑通（纯 stdlib，产出文件+尺寸自检）；notebook 代码由学习者本地试跑检查。

## 构建历史（摘要）
- 2026-06-08~14：建成 C00–C37 共 38 门（C00–C09 极深；C10–C19 中等；C20–C37 广度脚手架）。原 plan 仅记录至 C19。
- 2026-06-27：本轮启动「全谱深化到极深 + 新增 C38–C47」工程；引入 `coursekit.py` 统一生成器与「极深」硬指标；C20 现代架构课作为深度样板先行。
- 2026-06-28：**完工**。C10–C37 全部深化、C38–C47 全部新建到 gold（讲解每模块中位 9–10.5K 可见字符、notebook 30–42 cell、glossary≥12KB/references≥8KB），并对 11 门偏薄课做 HTML 加厚二轮。每门课的 notebook 均在 `courses` conda env 实跑、assert 0 失败。**全谱：48 门课 · 364 讲解 HTML · 316 notebook。** 唯 C07/C08（面试 drill 课）讲解仍按原作者轻量设计（~3K 字符），如需可另行加厚。配套：课程全景图 Artifact。
  - 生成器与规范留存在会话 scratchpad：`coursekit.py`（house-style 生成器）、`RUBRIC.md`（极深硬指标）、各课 `build_c*.py`。校验用 `/home/wsl/miniconda3/envs/courses/bin/python`（numpy 2.4.4）。

- 2026-08-06：**按 `LLM Research Engineer` JD 做覆盖度比对，新增 C48–C52 五门课**（不改动既有 48 门，纯追加）。
  - 缺口来源：JD 的 cloud deployment、encoder/seq2seq 家族、HuggingFace 生态、data augmentation、TensorFlow/跨框架迁移/模型导出/真机 GPU/专利与开源合规。
  - 规格与 C38–C47 一致：每门 6 模块（00 总览 + 01–05），讲解每页可见 ≥8000 字符（00 总览 ≥4800），notebook 30–44 cell，glossary ≥12KB、references ≥8KB，纯 numpy/CPU、无 GPU/联网/API 依赖。
  - **验证**：五门课全部 30 个 notebook 用 `_buildkit/runnb.py` 顺序实跑，assert 0 失败；并额外做了一轮「参考答案就地替换 stub」复验，确保每道 ✏️ 练习的 📖 参考答案真的能通过它自己的自测（该轮复验同时修好了 C49 模块 01/04 与 C51 模块 05 的 3 处答案-自测不一致）。
  - 生成器重建于 `_buildkit/coursekit.py`（原 scratchpad 版本已丢失，按 C43 的产物逆向复原）；各课 `build_c4x.py` / `build_c5x.py` 与内容模块 `c4x_mNN.py` / `c5x_mNN.py` 均在 `_buildkit/`。
  - **全谱：53 门课 · 346 讲解 HTML · 346 notebook。**

- 2026-08-17：**按 XPENG「TSR 2D Detection」JD 做覆盖度比对，新增 C53–C61 九门课**（不改动既有 53 门，纯追加）。
  - 缺口来源：比对 JD 后识别出 9 个零覆盖项，逐项建课——RT-DETR/RTMDet、匈牙利匹配与 set prediction、TSR 领域知识、检测专用图像增强、小目标技术、难例与长尾挖掘、VLA 感知接口、TensorRT/INT8/一致性调试、production 实战与面试实务。缺口分析见根目录 `INTERVIEW_PREP_XPENG_TSR.md`。
  - 规格与 C48–C52 一致且更厚：每门 6 模块，**54 个讲解页可见字符中位数 14669**（既有课程标准 8000+，最厚 23923），**2220 个 notebook cell**，每门 glossary 27.9–51.0KB、references 14.9–26.5KB，纯 numpy/CPU、无 GPU/联网/API 依赖。
  - **验证**：九门课 54 个 notebook 全部实跑，`_buildkit/runnb2.py`（新增的**两遍执行**验证器）确认 1348 个 code cell 与 **207 个 ✏️ 练习自测 assert 真实通过**。
    - 新增 `runnb2.py` 的原因：原 `runnb.py` 遇到练习骨架的 `NotImplementedError` 会整格跳过，导致练习自测 cell 从未被真正执行（假通过）。两遍执行先让 📖 参考答案生效，再重跑被跳过的自测 cell。
  - 构建过程中修复的真实缺陷：C56 的 `np.clip(b[:,[0,2]], ..., out=b[:,[0,2]])`（花式索引返回副本导致裁剪从未生效）、C58 的校准演示方向与正文相反、C60 的 IoU 敏感性工作点选错、C55 的小目标框 IoU 达不到匹配阈值等。
  - 生成规范 `_buildkit/GAPKIT_SPEC.md`；各课 `build_c5x.py` / `build_c6x.py` 与内容模块 `c5x_mNN.py` / `c6x_mNN.py` 均在 `_buildkit/`。
  - **全谱：62 门课 · 400 讲解 HTML · 400 notebook。**
