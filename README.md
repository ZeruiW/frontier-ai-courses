# Frontier AI Researcher / Engineer Courses · 前沿 AI 研究工程师课程体系

**70 courses · 448 lesson pages · 448 runnable notebooks · Colab-ready, CPU-first, from-scratch.**
一套从 model evaluation 起步、长成全栈的前沿 AI 研究/工程课程体系 —— 深度 HTML 讲解 + 真实可跑 notebook，纯 numpy/CPU 优先、优雅降级到真实框架/GPU。

📖 中文 → [跳转](#中文) · 🇬🇧 English → [jump](#english)

---

<a name="中文"></a>
## 中文

### 目录
- [这是什么](#zh-what)
- [快速开始](#zh-quickstart)
- [课程总览（70 门）](#zh-catalog)
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
### 课程总览（70 门）

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

<a name="zh-format"></a>
### 每门课的格式

```
CXX_Xxx_Course/
├── index.html          课程主页（模块地图 + 一键 Colab 徽章）
├── README.md           这门课自己的说明（定位、与相邻课的分工）
├── glossary.md          术语词典（≥12KB）
├── references.md        参考清单（论文/文档，标★必读）
├── requirements.txt      依赖（绝大多数课只需要 numpy/pandas/jupyterlab）
├── assets/style.css      全站共用同一份样式（70 门课字节级一致）
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
├── requirements-all.txt        全部 70 门课依赖的合集（装一次跑所有课）
├── _buildkit/                  house-style 生成器（coursekit.py）+ 各课构建脚本
├── C00_..._Course/ … C69_..._Course/   70 门课，每门结构见上
└── README.md                   就是这份文件
```

<a name="zh-gpu"></a>
### 关于 GPU / Colab / 量化

- **绝大多数 notebook 是纯 numpy/CPU**，在任何机器（含 Colab 的免费 CPU 运行时）上都能跑完，不依赖 GPU、网络或任何 API key。
- 少数课程（C00 VLM、C04 的 computer-use 模块、C27 模型压缩、C08 量化专题、C50 PEFT/TRL）会真实加载 HuggingFace 模型：这些 notebook 默认用 **fp16**，2–3B 级模型只需 5–8GB 显存、7B 级也压得进 Colab 免费的 **T4（16GB）**——**不会因为怕显存不够就默认量化**。量化本身只在「这门课/这个模块就是讲量化」时才作为正课内容出现（C08 量化从零、C27 全课、C00/C50 的 QLoRA 教学），其余地方即便留了 4-bit 选项也默认关闭，作为显存特别紧张时的备用开关。
- 每个 notebook 顶部都有官方的 **`Open in Colab`** 徽章，每门课的 `index.html` 每个模块条目旁也有一个小的 Colab 按钮——点开就能在浏览器里跑，无需本地装任何东西。

<a name="zh-env"></a>
### 环境与依赖

- **本地全量环境**：一个 conda env（`courses`，Python 3.11）配好 PyTorch + HuggingFace 全家桶 + 常用科学计算库即可跑完全部 70 门课，详见 [`ENV_SETUP.md`](./ENV_SETUP.md)；合集依赖在 [`requirements-all.txt`](./requirements-all.txt)。
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

完整细节见 [`COURSES_PLAN.md`](./COURSES_PLAN.md)。

---

<a name="english"></a>
## English

### Table of Contents
- [What This Is](#en-what)
- [Quick Start](#en-quickstart)
- [Course Catalog (70 courses)](#en-catalog)
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
### Course Catalog (70 courses)

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

<a name="en-format"></a>
### Format of Each Course

```
CXX_Xxx_Course/
├── index.html          Course home page (module map + Open-in-Colab badges)
├── README.md           This course's own README (scope, boundaries vs. neighbors)
├── glossary.md          Glossary (≥12KB)
├── references.md        Reference list (papers/docs, ★ = must-read)
├── requirements.txt      Dependencies (most courses need only numpy/pandas/jupyterlab)
├── assets/style.css      One shared stylesheet across all 70 courses (byte-identical)
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
├── requirements-all.txt        Union of all 70 courses' dependencies (install once, run all)
├── _buildkit/                  House-style generator (coursekit.py) + each course's build scripts
├── C00_..._Course/ … C69_..._Course/   70 courses, layout described above
└── README.md                   This file
```

<a name="en-gpu"></a>
### About GPU / Colab / Quantization

- **The vast majority of notebooks are pure numpy/CPU** and run to completion on any machine (including Colab's free CPU runtime) — no GPU, network, or API key needed.
- A handful of courses (C00 VLM, C04's computer-use module, C27 model compression, C08's quantization module, C50 PEFT/TRL) genuinely load real HuggingFace models. Those notebooks default to **fp16**: 2–3B-class models need only 5–8GB VRAM, and even a 7B model fits on Colab's free **T4 (16GB)** — they do **not** default to quantization just to be safe on memory. Quantization only appears as actual lesson content where the course/module is specifically about quantization (C08's quantize-from-scratch, all of C27, the QLoRA lessons in C00/C50); everywhere else, a 4-bit option — if present at all — defaults to off and exists purely as a fallback for unusually tight VRAM.
- Every notebook has an official **`Open in Colab`** badge as its first cell, and every course's `index.html` has a small Colab button next to each module entry — click it and it runs in your browser, nothing to install locally.

<a name="en-env"></a>
### Environment & Dependencies

- **Full local environment**: one conda env (`courses`, Python 3.11) with PyTorch + the HuggingFace stack + common scientific-computing libraries covers all 70 courses — see [`ENV_SETUP.md`](./ENV_SETUP.md); the combined dependency list is [`requirements-all.txt`](./requirements-all.txt).
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

Full details in [`COURSES_PLAN.md`](./COURSES_PLAN.md).
