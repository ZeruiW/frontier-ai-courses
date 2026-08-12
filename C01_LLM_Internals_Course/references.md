# 关键论文清单 · References（LLM 内核）

> 按模块组织。`★` = 必读里程碑。教材中 `[作者 年份]` 对应此处。

## 01 · Tokenization
- ★ Sennrich et al. 2015, *Neural Machine Translation of Rare Words with Subword Units (BPE)* — arXiv:1508.07909
- Kudo & Richardson 2018, *SentencePiece* — arXiv:1808.06226
- Karpathy 2024, *minbpe* — github.com/karpathy/minbpe

## 02 · Attention 与 Transformer Block
- ★ Vaswani et al. 2017, *Attention Is All You Need* — arXiv:1706.03762
- Xiong et al. 2020, *On Layer Normalization in the Transformer Architecture (Pre-LN)* — arXiv:2002.04745
- Karpathy 2022, *nanoGPT* — github.com/karpathy/nanoGPT

## 03 · 训练 mini-GPT
- ★ Radford et al. 2019, *Language Models are Unsupervised Multitask Learners (GPT-2)* — OpenAI
- Brown et al. 2020, *Language Models are Few-Shot Learners (GPT-3)* — arXiv:2005.14165
- Loshchilov & Hutter 2017, *Decoupled Weight Decay Regularization (AdamW)* — arXiv:1711.05101

## 04 · 解码策略
- ★ Holtzman et al. 2019, *The Curious Case of Neural Text Degeneration (nucleus/top-p)* — arXiv:1904.09751
- Fan et al. 2018, *Hierarchical Neural Story Generation (top-k)* — arXiv:1805.04833
- Leviathan et al. 2022, *Fast Inference via Speculative Decoding* — arXiv:2211.17192

## 05 · Scaling Laws
- ★ Kaplan et al. 2020, *Scaling Laws for Neural Language Models* — arXiv:2001.08361
- ★ Hoffmann et al. 2022, *Training Compute-Optimal Large Language Models (Chinchilla)* — arXiv:2203.15556
- Muennighoff et al. 2023, *Scaling Data-Constrained Language Models* — arXiv:2305.16264

## 06 · KV Cache 与高效推理
- ★ Dao et al. 2022, *FlashAttention* — arXiv:2205.14135
- Kwon et al. 2023, *Efficient Memory Management for LLM Serving (vLLM / PagedAttention)* — arXiv:2309.06180
- Dettmers et al. 2022, *LLM.int8()* — arXiv:2208.07339
- Frantar et al. 2022, *GPTQ* — arXiv:2210.17323

## 07 · 现代架构演化
- ★ Su et al. 2021, *RoFormer: Rotary Position Embedding (RoPE)* — arXiv:2104.09864
- ★ Ainslie et al. 2023, *GQA: Generalized Multi-Query Attention* — arXiv:2305.13245
- Shazeer 2019, *Fast Transformer Decoding (MQA)* — arXiv:1911.02150
- Shazeer et al. 2017, *Outrageously Large Neural Networks (MoE)* — arXiv:1701.06538
- Fedus et al. 2021, *Switch Transformers* — arXiv:2101.03961
- ★ Gu & Dao 2023, *Mamba: Linear-Time Sequence Modeling (SSM)* — arXiv:2312.00752
- Touvron et al. 2023, *LLaMA* — arXiv:2302.13971
- Zhang & Sennrich 2019, *RMSNorm* — arXiv:1910.07467
- Shazeer 2020, *GLU Variants Improve Transformer (SwiGLU)* — arXiv:2002.05202
