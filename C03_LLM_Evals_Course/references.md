# 关键论文清单 · References（评测科学）

> 按模块组织。`★` = 必读里程碑。教材中 `[作者 年份]` 对应此处。

## 01 · 评测分类学与 benchmark 全景
- ★ Hendrycks et al. 2021, *Measuring Massive Multitask Language Understanding (MMLU)* — arXiv:2009.03300
- Rein et al. 2023, *GPQA: A Graduate-Level Google-Proof Q&A Benchmark* — arXiv:2311.12022
- Phan et al. 2025, *Humanity's Last Exam (HLE)* — arXiv:2501.14249
- Jimenez et al. 2023, *SWE-bench* — arXiv:2310.06770
- Srivastava et al. 2022, *BIG-bench* — arXiv:2206.04615
- Liang et al. 2022, *Holistic Evaluation of Language Models (HELM)* — arXiv:2211.09110

## 02 · 统计严谨性
- ★ Miller 2024, *Adding Error Bars to Evals* — arXiv:2411.00640
- Efron & Tibshirani 1993, *An Introduction to the Bootstrap*（专著）
- Dror et al. 2018, *The Hitchhiker's Guide to Testing Statistical Significance in NLP* — ACL 2018

## 03 · 答案抽取与 prompt 敏感性
- ★ Sclar et al. 2023, *Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design* — arXiv:2310.11324
- Alzahrani et al. 2024, *When Benchmarks are Targets: Revealing the Sensitivity of LLM Leaderboards* — arXiv:2402.01781
- Zheng et al. 2023, *Large Language Models Are Not Robust Multiple Choice Selectors* — arXiv:2309.03882

## 04 · LLM-as-a-Judge
- ★ Zheng et al. 2023, *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* — arXiv:2306.05685
- Dubois et al. 2024, *Length-Controlled AlpacaEval* — arXiv:2404.04475
- Panickssery et al. 2024, *LLM Evaluators Recognize and Favor Their Own Generations* — arXiv:2404.13076

## 05 · 污染与饱和
- ★ Oren et al. 2023, *Proving Test Set Contamination in Black Box Language Models* — arXiv:2310.17623
- Sainz et al. 2023, *NLP Evaluation in Trouble: Data Contamination* — arXiv:2310.18018
- White et al. 2024, *LiveBench: A Challenging, Contamination-Free LLM Benchmark* — arXiv:2406.19314
- Chen et al. 2024, *Are We on the Right Way? (MMStar, no-input 基线思想)* — arXiv:2403.20330

## 06 · 能力引出与 pass@k
- ★ Chen et al. 2021, *Evaluating Large Language Models Trained on Code (HumanEval, 无偏 pass@k)* — arXiv:2107.03374
- METR 2024, *Guidelines for Capability Elicitation* — metr.org
- Wei et al. 2022, *Chain-of-Thought Prompting* — arXiv:2201.11903

## 07 · Eval harness 工程
- UK AI Safety Institute 2024, *Inspect* — inspect.aisi.org.uk
- Gao et al. 2023, *lm-evaluation-harness* — github.com/EleutherAI
- Biderman et al. 2024, *Lessons from the Trenches on Reproducible Evaluation* — arXiv:2405.14782

## 08 · Arena / Elo / time-horizon / 报告
- ★ Chiang et al. 2024, *Chatbot Arena* — arXiv:2403.04132
- ★ Kwa et al. 2025 (METR), *Measuring AI Ability to Complete Long Tasks (time horizon)* — arXiv:2503.14499
- Bradley & Terry 1952, *Rank Analysis of Incomplete Block Designs*（BT 模型原始论文）
- Singh et al. 2025, *The Leaderboard Illusion* — arXiv:2504.20879
