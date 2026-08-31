# 前沿 AI Researcher / Engineer 技能栈课程规划

> 体系：每模块 = 深度 HTML 讲解 + 真实可运行 notebook（✏️ 练习 TODO + assert 判分 + 📖 参考答案）。
> 受众：面向 frontier-lab 的 AI 研究科学家 / 研究工程师（起步于 model evaluation，已扩为全栈）。
> 讲解：中文 + 英文术语。全课 CPU-first、优雅回退、纯实现优先。
> 本次大改：**全谱深化到「极深」 + 新增 10 门补缺课（C38–C47）**。更新日期：2026-06-27。

---

## 总览：72 门课（C00–C71）

### 🆕 RAG 生产工程与提示程序化 · C70–C71（本轮新增）
> 触发：用户在 C66–C69 完工后要求继续扩课。
> **一次纠错**：我最初提议「RAG 评测与工程」与「多 agent 协作与编排」，
> 而对全库 448 个讲解页做关键词扫描后确认这两个方向已被 C11（7 模块，含 RAG 评测与长上下文评测）
> 与 C34（6 模块，含 subagent / 编排 / 权限 / 可观测 / 部署）覆盖——提议是错的。
> 重新扫描找到的真实缺口是：文档解析/ingestion（全库 1 命中）、RAG 语境的分块策略（2）、
> 查询改写/HyDE（0）、迭代检索（1）、增量索引与新鲜度（~0）、GraphRAG（0）；
> 以及 DSPy/自动提示优化（0）、few-shot 示例选择（4）、受限解码（散落提及无专门模块）。

| 课 | 文件夹 | 主题 | 补的洞 | 状态 |
|----|--------|------|--------|------|
| C70 | `C70_RAG_Production_Course/` | RAG 生产工程（摄取与解析 · 分块 · 查询侧改写与路由 · 迭代与图检索 · 索引运维） | C11 讲「在索引里怎么找」，而「索引里装的是什么、查询长什么样、索引怎么维护」整整一半零覆盖 | ✅ 已完成 |
| C71 | `C71_Prompt_Programming_Course/` | 提示与上下文的程序化优化（prompt program · 示例选择与顺序 · 自动优化 · 受限解码 · 提示运维与跨模型迁移） | C03-03 是 prompt 敏感性的**测量**视角、C33 是上下文预算；把 prompt 当**可搜索、可保证、可运维的程序**这一层零覆盖 | ✅ 已完成 |

**这批课的分工**：C70 管「数据与查询怎么进来、索引怎么活下去」；C71 管「prompt 本身的结构、优化与运维」。
两者都明确不碰 C11（检索算法）与 C33（上下文预算）。

### 🆕 Agent 评测与 AI 系统评估 · C66–C69（本轮新增）
> 触发：用户要求「添加一些 AI Agent 和大模型 Evaluation 的课程」。
> 缺口分析：全库里 agent 评测此前只有 C04-06 与 C26-05 两个子模块；
> LLM judge 只有 C03-04 一节；评测基础设施与 agent 安全（间接注入/权限/出站）零覆盖。

| 课 | 文件夹 | 主题 | 补的洞 | 状态 |
|----|--------|------|--------|------|
| C66 | `C66_Agentic_Evaluation_Course/` | Agent 评测与基准（三层评测对象 · 基准全景 · 判分器 α/β · 轨迹指标 · pass@k vs pass^k · 成本与 harness 指纹） | C04-06 / C26-05 只讲「有这回事」，没讲「怎么真的做一次」 | ✅ 已完成 |
| C67 | `C67_LLM_Judge_Course/` | LLM-as-a-Judge 与评分模型（可判定性阶梯 · rubric · 四大偏差与去偏 · 人类上界 · BT/Elo 排名 · 奖励模型与过优化） | C03-04 只有一节；judge 的偏差量化、元评测、排名、RM 评测全无 | ✅ 已完成 |
| C68 | `C68_Eval_Infrastructure_Course/` | Eval 基础设施与线上监控（spec/runner/store/report 四层 · 数据集版本化 · 缓存键 · CI 门禁阈值 · 漂移与闭环） | 「怎么把一次评测跑一千次」零覆盖；C37 的中心是模型不是评测 | ✅ 已完成 |
| C69 | `C69_Agent_Security_Course/` | Agent 安全与提示注入（信任传播 · 间接注入与双 LLM · 工具供应链 · 权限四维与沙箱 · 出站控制 · 攻击面评测） | C05 是模型安全、C44 是对抗攻击；间接注入与权限边界零覆盖 | ✅ 已完成 |

**这批课的分工**：C66 量 agent · C67 量判分器 · C68 把评测变成基础设施 · C69 量攻击面。

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

- 2026-08-31：**按「AI Agent + 大模型 Evaluation」的诉求做覆盖度比对，新增 C66–C69 四门课**（不改动既有 66 门，纯追加）。
  - 缺口来源：全库比对后确认四个零覆盖或严重不足的方向——① agent 评测此前只有 C04-06 与 C26-05 两个子模块（讲了「有这回事」，没讲「怎么做一次」）；② LLM judge 只有 C03-04 一节，judge 的偏差量化/元评测/排名/奖励模型评测全无；③ 「怎么把一次评测跑一千次」（spec/runner/store/门禁/线上监控）零覆盖，且与 C37 MLOps 的视角不同（那门课的中心是模型，本课是评测）；④ agent 安全（间接注入、工具供应链、权限边界、出站控制）零覆盖，C05 是模型安全、C44 是对抗攻击，都不覆盖「agent 会做什么」。
  - 四门课的分工：**C66 量 agent · C67 量判分器 · C68 把评测变成基础设施 · C69 量攻击面**。四者互相引用而不重复：C66 用 judge 但把「judge 怎么验证」交给 C67；C68 只管评测的工程化；C69 模块 05 完全复用 C66 的统计规范。
  - 规格与 C62–C65 一致：每门 6 模块（00 总览 + 01–05），讲解每页可见 ≥8000 字符（00 总览 ≥4800），notebook 32–43 cell、每本 4 道 ✏️ 练习（TODO + assert 判分 + 📖 参考答案）+ 🧪 真实工程胶囊，glossary 18.5–21.1KB、references 8.0–11.1KB。纯 numpy/标准库、CPU、断网、无需 API key。
  - 方法论上的一个共同选择：**四门课都用「已知真值的可控模拟器」而不是真实 API**——C66 用可控的 agent 与环境、C67 用带五个偏差旋钮的 judge 模拟器、C68 用能精确注入失败的假模型、C69 用规则匹配的 agent 与 `[[INJECT:...]]` 占位标记。理由是只有在知道真值的条件下，才能验证一个去偏/降噪/防御方法到底把估计推近了还是推远了；真实接入代码放在每个模块末尾的「🧪 真实工程胶囊」里。
  - **C69 的教学约定**：notebook 里不包含针对任何真实系统的可用攻击载荷，攻击手法只在讲解里以机制层面描述（足以设计防御）；而防御侧（权限四维、范围检查、出站白名单、审计与 provenance、金丝雀判分、工具清单锁）全部是真实实现。
  - **验证**：四门课 24 个 notebook 全部实跑，`_buildkit/runnb2.py`（两遍执行）确认 **549 个 code cell 与 96 个 ✏️ 练习自测 assert 真实通过**。
  - 构建过程中修正的、值得记录的实质性问题（都是「先写结论再验证，发现结论不成立」而改掉的）：
    - C66-05：best-of-n 中被选中解的精确率其实与 $n$ 无关（恒为 $p/q$），原本的「精确率随 n 下降」说法不成立——改成「交付出去的成功里假阳解的绝对占比随 n 上升」，并加 assert 固定住。
    - C67-04：主动配对并非「全面更好」——它让相邻名次的差值区间变窄，但「能被显著区分开的模型对」总数反而减少。改写成「把精度搬了个地方」，并保留两个指标同时呈现。
    - C67-05：线性代理奖励下不存在过优化拐点，必须让真实效用具备「质量饱和 + 表面维度过头扣分」的形状才会出现倒 U——这本身是一个更诚实的建模说明，写进了 notebook。
    - C68-01：固定抽样数量 N 时，任务集增长导致抽样成员必然变化（这是数学必然，不是实现问题）；改为主张「按比例选 + 分层保底」，并用保留率曲线证明。
    - C68-04：churn 应当与「噪声下的自发翻转数」比较，而不是与净变化比较——原先的 4 倍规则在真实噪声水平下会把正常运行判成异常。
    - C69-04：可泄漏量公式里，只有「可读数据量 V」是硬上界；速率/时长/载荷都只能拖慢，且在长时运行下效果完全消失（notebook 里把「常驻一个月后降速失效」算了出来）。
  - **全谱：70 门课 · 448 讲解 HTML · 448 notebook。**

- 2026-08-31（同日第二轮）：**用户要求继续扩课；先纠正了一次错误的缺口判断，再新增 C70–C71 两门课。**
  - **纠错记录（值得留档）**：我最初提议「RAG 系统的评测与工程」与「多 agent 协作与编排」，
    并声称「全库只有 C21 讲检索」。对全库 448 个讲解页做关键词扫描后确认这是错的——
    `C11_RAG_Retrieval_Course` 是一门 7 模块的完整 RAG 课（含 RAG 评测、检索指标、长上下文评测），
    `C34_Agent_Orchestration_Course` 是一门 6 模块的多 agent 编排课。**两个提议都会产出重复课。**
    重新扫描后确认的真实缺口写在上面的总览表里。这次纠错在动工前完成，没有产生浪费。
  - **C70 的边界**：全程复用 C11 的指标定义而一个都不重新定义；到「组装上下文」为止，之后交给 C33；
    图检索只用图的结构（邻域扩展），不训练任何图神经网络（那在 C46）。
  - **C71 的边界**：不讲上下文预算与压缩（C33）；不讲思维链的效果（C09，因为模拟器没有推理能力）；
    judge 本身怎么验证交给 C67。
  - **验证**：12 个 notebook 全部实跑，`runnb2.py` 两遍执行确认
    **272 个 code cell 与 48 个 ✏️ 练习自测 assert 真实通过**。
  - 构建过程中被数据推翻、因而改写结论的地方（这一批比上一批更多，且几处与流行做法相反）：
    - C70-01：「拍平表格必然丢结构」是错的——行主序拍平在小表上保住了行对应；
      真正让它崩掉的是**列主序读取**（PDF 按 x 坐标排序的真实结果）与**块边界落在行内**。
      它丢的是**列名**。改写为四种解析方式的对比。
    - C70-02：主题纯度不能用「块内句相似度」度量（那个代理依赖的正是待评估的嵌入）；
      改用精确的「块是否跨越文档自己的小节边界」。
      语义分块的分位数阈值有两个真实退化（相似度大量为 0 时 q 完全失效；相似度全相等时处处切），
      修法是绝对阈值 + 双向硬约束。
    - C70-02：句边界分块下句子级答案恒完整，所以完整率公式的「重叠 ≥ 答案长度−1」这条规则
      **有适用条件**；门禁规则因此必须带 `chunker` 条件，否则会在正确配置上误报。
    - C70-04：多跳题的单轮 recall 为 0 不是「排序不够好」——十条候选块的相似度**完全相等**，
      残余命中率来自并列组抽签，因此不随模型变强而提高。`retrieve()` 因此显式暴露 `tie_seed`。
    - C70-04：`$/success` **不是**一个自动偏向迭代的口径——用 LLM 做停止判断时迭代更贵，
      换成结构性信号后才反过来。
    - C70-05：模型腐烂的线上信号在 top-1 分数分布的**左尾**，中位数可能一点不动。
    - C71-01：指令槽位**不是独立的**——只删取值域时端到端是 20% 而不是 0，
      因为兜底槽位那句话意外地声明了一个标签。边际贡献不可加。
    - C71-02：流行的「打散标签」在本课模拟器上**没有稳定收益**（准确率与分布集中度都没有稳定方向）；
      改写为「顺序的自由度高度集中——『最后一条放谁』解释了六成」，
      并明确写出「可迁移的是方法，不是规则」。
    - C71-02：简化的「减先验校准」（给先验标签一个惩罚）实际**有害**；
      重做成 faithful 版本（先把模型展开成标签分数向量再减先验），
      它把最差顺序从 50% 救到 70%，并写明两个前提（需要 logprobs、假设真实分布近均匀）。
    - C71-03：`top-m` 复选在本课的 10 条留出集上**没有带来任何改善**（并列导致 argmax 无从下手）；
      改写为一个诚实的负面结果，并指出它对留出集分辨率的要求。
    - C71-04：**「语法越紧失真越大」是错的**。练习 2 精确证明：尾部同质时
      逐步掩码**恰好等于**条件分布（掩掉 56% 还是 91% 都一样，KL = 0）；
      失真的**唯一**来源是分支之间的下游收尾能力差异。
    - C71-04：「只看位置的掩码会产生死局」这个说法不准确——它的真实后果是
      **不保证输出合法**（而它在「所有合法串结构相同」时侥幸安全）。
    - C71-05：跨模型跨度的正确形式不是「同一个 prompt 在不同模型上分数不同」——
      没调过的 prompt 在四个模型上分数**完全相同**；
      而为 A 调过之后搬到 B 上会从 70% 掉到 50%（低于 B 的基线）。
      **迁移风险是优化的副产物，不是换模型本身的代价。**
  - **全谱：72 门课 · 460 讲解 HTML · 460 notebook。**
