# 关键论文清单 · References

> 按模块组织。`★` = 必读里程碑。链接为 arXiv / 官方。读教材时遇到 `[作者 年份]` 回这里查。

## 01 · 视觉编码器与基础
- ★ Vaswani et al. 2017, *Attention Is All You Need* — arXiv:1706.03762
- ★ Dosovitskiy et al. 2021, *An Image is Worth 16x16 Words (ViT)* — arXiv:2010.11929
- He et al. 2016, *Deep Residual Learning (ResNet)* — arXiv:1512.03385
- He et al. 2022, *Masked Autoencoders (MAE)* — arXiv:2111.06377
- Oquab et al. 2023, *DINOv2* — arXiv:2304.07193

## 02 · 对比对齐 CLIP / SigLIP
- ★ Radford et al. 2021, *Learning Transferable Visual Models (CLIP)* — arXiv:2103.00020
- Jia et al. 2021, *Scaling Up Visual and Vision-Language Representation (ALIGN)* — arXiv:2102.05918
- ★ Zhai et al. 2023, *Sigmoid Loss for Language Image Pre-Training (SigLIP)* — arXiv:2303.15343
- Tschannen et al. 2025, *SigLIP 2* — arXiv:2502.14786
- Sun et al. 2023, *EVA-CLIP* — arXiv:2303.15389
- Liang et al. 2022, *Mind the Gap: Modality Gap* — arXiv:2203.02053

## 03 · VLM 架构演进
- ★ Alayrac et al. 2022, *Flamingo* — arXiv:2204.14198
- ★ Li et al. 2023, *BLIP-2 (Q-Former)* — arXiv:2301.12597
- Li et al. 2022, *BLIP* — arXiv:2201.12086
- ★ Liu et al. 2023, *Visual Instruction Tuning (LLaVA)* — arXiv:2304.08485
- Bavishi et al. 2023, *Fuyu-8B* (Adept blog) — encoder-free
- Dai et al. 2023, *InstructBLIP* — arXiv:2305.06500
- Chen et al. 2023, *PaLI* — arXiv:2209.06794

## 04 · 连接器与训练范式
- ★ Liu et al. 2023, *LLaVA-1.5* — arXiv:2310.03744
- Jaegle et al. 2021, *Perceiver IO* — arXiv:2107.14795
- Laurençon et al. 2024, *What matters when building VLMs? (Idefics2)* — arXiv:2405.02246
- McKinzie et al. 2024, *MM1* — arXiv:2403.09611
- Karamcheti et al. 2024, *Prismatic VLMs* — arXiv:2402.07865

## 05 · 指令微调与偏好对齐
- ★ Liu et al. 2023, *Visual Instruction Tuning (LLaVA)* — arXiv:2304.08485
- Hu et al. 2021, *LoRA* — arXiv:2106.09685
- Dettmers et al. 2023, *QLoRA* — arXiv:2305.14314
- Rafailov et al. 2023, *Direct Preference Optimization (DPO)* — arXiv:2305.18290
- Sun et al. 2023, *Aligning LMMs with Factually Augmented RLHF (LLaVA-RLHF)* — arXiv:2309.14525
- Yu et al. 2024, *RLHF-V* — arXiv:2312.00849

## 06 · 高分辨率 / 任意分辨率 / 视频
- ★ Liu et al. 2024, *LLaVA-NeXT (AnyRes)* — llava-vl.github.io blog
- Dehghani et al. 2023, *Patch n' Pack (NaViT)* — arXiv:2307.06304
- ★ Wang et al. 2024, *Qwen2-VL (Naive Dynamic Resolution + M-RoPE)* — arXiv:2409.12191
- Chen et al. 2024, *InternVL 1.5* — arXiv:2404.16821
- Zhang et al. 2023, *Video-LLaMA* — arXiv:2306.02858
- Lin et al. 2023, *Video-LLaVA* — arXiv:2311.10122

## 07 · 评测体系（重点）
- ★ Yue et al. 2024, *MMMU* — arXiv:2311.16502
- ★ Liu et al. 2023, *MMBench* — arXiv:2307.06281
- Fu et al. 2023, *MME* — arXiv:2306.13394
- ★ Chen et al. 2024, *Are We on the Right Way? (MMStar)* — arXiv:2403.20330
- Lu et al. 2024, *MathVista* — arXiv:2310.02255
- Yu et al. 2023, *MM-Vet* — arXiv:2308.02490
- Li et al. 2024, *Seed-Bench* — arXiv:2307.16125
- Zheng et al. 2023, *Judging LLM-as-a-Judge (MT-Bench)* — arXiv:2306.05685

## 08 · 幻觉 / 鲁棒性 / 安全
- ★ Li et al. 2023, *Evaluating Object Hallucination (POPE)* — arXiv:2305.10355
- ★ Guan et al. 2024, *HallusionBench* — arXiv:2310.14566
- Liu et al. 2024, *Survey on Hallucination in LMMs* — arXiv:2404.18930
- Qi et al. 2024, *Visual Adversarial Examples Jailbreak* — arXiv:2306.13213
- Gong et al. 2023, *FigStep (typographic jailbreak)* — arXiv:2311.05608
- METR 2024, *Evaluating autonomous capabilities* — metr.org
- Phuong et al. 2024 (DeepMind), *Evaluating Frontier Models for Dangerous Capabilities* — arXiv:2403.13793

## 09 · 原生多模态与智能体
- ★ OpenAI 2024, *GPT-4o* — openai.com (system card)
- ★ Gemini Team 2023/2024, *Gemini* — arXiv:2312.11805
- Chameleon Team 2024, *Chameleon (Early-Fusion Any-to-Any)* — arXiv:2405.09818
- Lu et al. 2022, *Unified-IO* — arXiv:2206.08916
- ★ Hong et al. 2023, *CogAgent (GUI agent)* — arXiv:2312.08914
- Cheng et al. 2024, *SeeClick (GUI grounding)* — arXiv:2401.10935
- Anthropic 2024, *Computer Use* — anthropic.com
- Bai et al. 2025, *Qwen2.5-VL* — arXiv:2502.13923
