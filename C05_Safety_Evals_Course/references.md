# 关键论文清单 · References（前沿模型安全评估与红队）

> 按模块组织。`★` = 必读里程碑。教材中 `[作者 年份]` 对应此处。
> 本课程全程为防御/评测/治理视角。

## 01 · 风险分类与安全框架
- ★ Shevlane et al. 2023, *Model Evaluation for Extreme Risks* — arXiv:2305.15324
- Anthropic 2023–2025, *Responsible Scaling Policy (RSP)* — anthropic.com
- OpenAI 2023–2025, *Preparedness Framework* — openai.com
- Google DeepMind 2024–2025, *Frontier Safety Framework* — deepmind.google
- Hendrycks et al. 2023, *An Overview of Catastrophic AI Risks* — arXiv:2306.12001

## 02 · 危险能力评估设计
- ★ Phuong et al. 2024 (DeepMind), *Evaluating Frontier Models for Dangerous Capabilities* — arXiv:2403.13793
- ★ Kwa et al. 2025 (METR), *Measuring AI Ability to Complete Long Tasks* — arXiv:2503.14499
- Wijk et al. 2024 (METR), *RE-Bench* — arXiv:2411.15114
- METR 2024, *Guidelines for Capability Elicitation* — metr.org

## 03 · 红队方法论
- ★ Perez et al. 2022, *Red Teaming Language Models with Language Models* — arXiv:2202.03286
- ★ Ganguli et al. 2022, *Red Teaming LMs to Reduce Harms: Methods, Scaling Behaviors* — arXiv:2209.07858
- Mazeika et al. 2024, *HarmBench（自动化红队评测框架）* — arXiv:2402.04249

## 04 · 鲁棒性测量与拒绝校准
- Zou et al. 2023, *Universal and Transferable Adversarial Attacks (GCG，文献认知用)* — arXiv:2307.15043
- ★ Röttger et al. 2023, *XSTest: Identifying Exaggerated Safety / 过度拒绝* — arXiv:2308.01263
- Wei et al. 2023, *Jailbroken: How Does LLM Safety Training Fail?（失败模式分类）* — arXiv:2307.02483
- Anthropic 2025, *Constitutional Classifiers* — arXiv:2501.18837

## 05 · Sandbagging 与评测完整性
- ★ van der Weij et al. 2024, *AI Sandbagging: Language Models can Strategically Underperform* — arXiv:2406.07358
- Greenblatt et al. 2024, *Alignment Faking in Large Language Models* — arXiv:2412.14093
- Järviniemi & Hubinger 2024, *Uncovering Deceptive Tendencies in LMs* — arXiv:2405.01576

## 06 · AI Control 与监控
- ★ Greenblatt et al. 2023, *AI Control: Improving Safety Despite Intentional Subversion* — arXiv:2312.06942
- Korbak et al. 2025, *How to Evaluate Control Measures?* — arXiv:2504.05259
- Baker et al. 2025 (OpenAI), *Monitoring Reasoning Models for Misbehavior (CoT monitoring)* — arXiv:2503.11926

## 07 · Safety Case 与治理报告
- ★ Clymer et al. 2024, *Safety Cases: How to Justify the Safety of Advanced AI Systems* — arXiv:2403.10462
- Buhl et al. 2024, *Safety Cases for Frontier AI* — arXiv:2410.21572
- Anthropic / OpenAI / GDM, *Model Cards & System Cards*（各家发布页）
