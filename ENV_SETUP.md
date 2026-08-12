# Course environment (conda)

A single shared conda env, **`courses`** (Python 3.11), serves all 38 courses (C00–C37).
They share one ML/LLM stack, so one env is far lighter than 38 copies.

Created: 2026-06-27 · GPU: RTX 4090 · CUDA wheels: cu124

## Use it

```bash
conda activate courses          # `conda init bash` already run; restart shell if `conda` isn't found
cd C01_LLM_Internals_Course     # any course
jupyter lab                     # then pick the matching kernel (see below)
```

Run a notebook headless:

```bash
conda run -n courses jupyter nbconvert --to notebook --execute path/to/nb.ipynb
```

## Jupyter kernels (already registered, all → the `courses` env)

Notebooks embed a per-course kernel name; matching kernels are installed so each opens on a working kernel:

| Kernel name | Courses |
|---|---|
| `vlm` | C00 |
| `internals` | C01 |
| `posttrain` | C02 |
| `evals` | C03 |
| `agents` | C04 |
| `safety` | C05 |
| `python3` | C06–C37 |
| `courses` | generic (use for anything) |

If a notebook ever shows "no kernel", just select **Python (courses)** / any of the above.

## What's installed

- **PyTorch 2.6.0+cu124** (CUDA verified on the 4090), torchvision
- HuggingFace: transformers, accelerate, datasets, peft, trl, tokenizers, safetensors
- Quantization/kernels: **bitsandbytes**, **triton** (JIT verified — needs the C compiler below)
- Vision: open_clip_torch, timm, opencv, pillow, qwen-vl-utils, ftfy
- Numerics/stats/viz: numpy, scipy, scikit-learn, statsmodels, pandas, matplotlib, seaborn, einops
- API clients: openai, anthropic (set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` for the optional API cells)
- Jupyter: jupyterlab, ipykernel, ipywidgets, tqdm, pytest, tiktoken, sentencepiece

Full pinned list: [`requirements-all.txt`](./requirements-all.txt) (union of every course's `requirements.txt`).

## Notes

- A C/C++ compiler (`gcc_linux-64`/`gxx_linux-64`) is installed **inside** the env because triton
  JIT-compiles CUDA kernels at runtime (needed by `torch.compile`, the GPU-kernels course, and
  bitsandbytes). The kernelspecs bake in `CC`/`CXX`/`PATH` so this works even outside an activated shell.
- Some package majors are newer than the courses' minimums (transformers 5.x, pandas 3.x, numpy 2.x).
  All constraints (`>=`) are satisfied and all checked notebooks ran clean. If a specific notebook hits
  an API break, pin that package down in `requirements-all.txt` and `pip install -r` again.
- Verified end-to-end (env-check notebooks ran with zero environment errors): C00, C01, C04, C07, C36.
  Remaining error cells in those notebooks are the intentional `✏️ TODO` student exercises.
- Channel: env built from **conda-forge** (avoids the Anaconda defaults Terms-of-Service gate).
