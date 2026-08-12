# 编码器与 Seq2Seq 模型家族

Transformer 不只有 decoder-only。本课把 **encoder-only（BERT 系）** 与 **encoder-decoder（T5/BART）**
这两种被 LLM 叙事掩盖、但在工业界天天在跑的形态，从注意力掩码开始重建一遍，
并用成本-精度的账回答「今天到底该用哪个」。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | MLM 与双向编码器 | `01_mlm_bert/` |
| 02 | 预训练目标与配方的改良 | `02_pretraining_objectives/` |
| 03 | 下游微调三范式 | `03_finetuning/` |
| 04 | Encoder-Decoder | `04_encoder_decoder/` |
| 05 | 今天还要不要 encoder | `05_encoder_today/` |

## 这门课补什么洞
C01 从零写 decoder-only Transformer；C17 讲神经网络之前的经典 NLP；C20 讲现代架构组件。
中间缺的是 **BERT / RoBERTa / ELECTRA / DeBERTa 这条双向编码器主线**，以及
**T5 / BART 的 encoder-decoder 与 seq2seq 训练-解码全套**——
也就是 JD 里 `hands-on with GPT, BERT, RoBERTa` 与 `expertise in sequence-to-sequence models` 那两条。

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）建立「这个设计解决了什么问题、代价是什么、今天还成立吗」的判断，
再跑 `NN_*.ipynb` 用纯 numpy 从零实现：三种掩码 → MLM 与 80/10/10 → RTD 与解耦注意力 →
Viterbi 约束解码与 span 联合搜索 → cross-attention、span corruption、beam search → 蒸馏与两阶段检索。
每个实现做**三层对拍**：可证明的理论性质、暴力枚举参考、论文报告的公开量级。
先看 worked 示例（print + assert 自检）→ ✏️ 练习（TODO + `assert` 判分）→ 📖 参考答案 → 🧪 真实量级胶囊。
所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯 numpy / CPU，**不加载预训练权重、不需要 GPU、不联网**。
讲解与 notebook 末尾的「🔧 旁注」会指出每一步在 `transformers` 里叫什么、参数在哪；
想真正加载权重跑起来，见配套的 **C50（HuggingFace 生态与 API 实操）**。

配套：[术语词典](glossary.md) · [参考清单](references.md)
