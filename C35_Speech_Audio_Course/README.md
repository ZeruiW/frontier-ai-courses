# 语音与音频

把声音变成模型能学的东西：波形→特征(STFT/梅尔/MFCC)、ASR(Whisper/CTC)、神经音频编解码(RVQ)、TTS+声码器、语音 LLM 与流式语音 agent——从零用 numpy 实现。

| 模块 | 主题 | 目录 |
|---|---|---|
| 00 | 课程总览与环境 | `00_setup/` |
| 01 | 信号与特征 | `01_signals_features/` |
| 02 | ASR 与 Whisper | `02_asr/` |
| 03 | 神经音频编解码 | `03_codecs/` |
| 04 | TTS 与声码器 | `04_tts/` |
| 05 | 语音 LLM 与流式 | `05_speech_llms/` |

## 怎么学
每个模块 = `NN_讲解.html`（00 为 `00_overview.html`）建立直觉 + `NN_*.ipynb` 从零实现（worked 示例 → ✏️ 练习(TODO+assert) → 📖 参考答案）。所有 notebook 在 CPU 上实跑验证、0 失败。

## 环境
见 `requirements.txt`。核心实现纯标准库 + numpy（部分课用 pandas），无需联网/GPU/API key。

配套：[术语词典](glossary.md) · [参考清单](references.md)
