# Phase 0 — kv-cache calibration (this environment)

How to read this: **weights** is the fixed cost of a model; **kv/1k** is what each
1,000 tokens of context adds; **regime** says whether context is nearly free
(cheap-kv / swa-plateau) or competes with weights for your budget (expensive-kv).
**fits(budget)** is the largest context that model can actually hold at that many GB
(capped at the model's trained max). Not a ranking — a map for choosing model size
vs context on *your* hardware.

| model | regime | weights GB | kv MB/1k | model max ctx | fits 16GB | fits 24GB |
|---|---|---|---|---|---|---|
| llama3.2.3b:32k | expensive-kv | 2.1 | 66.25 | 131072 | 131,072 | 131,072 |
| qwen-3-8-27:latest | expensive-kv | 12.07 | 38.95 | 262144 | 100,940 | 262,144 |
| qwen3.6:27b | expensive-kv | 16.84 | 42.91 | 262144 | 0 | 166,957 |
| qwen3.6_27b:latest | expensive-kv | 16.84 | 42.83 | 262144 | 0 | 167,196 |
| ornith_9b_32k:latest | expensive-kv | 5.21 | 23.99 | 262144 | 262,144 | 262,144 |
| ornith:9b | expensive-kv | 5.21 | 23.99 | 262144 | 262,144 | 262,144 |
| llama3.2:3b | expensive-kv | 2.1 | 66.25 | 131072 | 131,072 | 131,072 |
| nemotron-3-nano:32k_context | moderate-kv | 2.78 | 13.95 | 262144 | 262,144 | 262,144 |
| qwen3.8:latest | moderate-kv | 18.0 | 14.15 | 262144 | 0 | 262,144 |
| nemotron-3-nano:4b | moderate-kv | 2.78 | 13.95 | 262144 | 262,144 | 262,144 |
| nemotron-4b-64k:latest | moderate-kv | 2.78 | 13.95 | 262144 | 262,144 | 262,144 |
| lfm2.5:latest | moderate-kv | 5.22 | 9.89 | 128000 | 128,000 | 128,000 |
| ornith:35b | moderate-kv | 21.54 | 12.34 | 262144 | 0 | 199,658 |
| gpt-oss:20b | cheap-kv | 12.72 | 1.18 | 131072 | 131,072 | 131,072 |
| functiongemma:270m | cheap-kv | 0.32 | 3.09 | 32768 | 32,768 | 32,768 |
| gemma4-code:latest | swa-plateau | 7.91 | 7.36 | 262144 | 262,144 | 262,144 |
| gemma4:26b | swa-plateau | 18.55 | 0.0 | 262144 | 0 | 262,144 |
| gemma3:64k | swa-plateau | 7.86 | 4.58 | 131072 | 131,072 | 131,072 |
| gemma3:12b | swa-plateau | 7.86 | 4.58 | 131072 | 131,072 | 131,072 |
| gemma4:e4b | swa-plateau | 3.26 | 3.21 | 131072 | 131,072 | 131,072 |
| swarm_gemma:latest | swa-plateau | 7.86 | 4.58 | 131072 | 131,072 | 131,072 |
| gemma4-e4b:latest | swa-plateau | 3.26 | 3.21 | 131072 | 131,072 | 131,072 |
| gemma4:12b | swa-plateau | 7.91 | 7.36 | 262144 | 262,144 | 262,144 |

Regimes: **expensive-kv** (>20 MB/1k) — context and weights fight over the budget, the real tradeoff zone; **cheap-kv** (<5 MB/1k) — context is nearly free, spend on parameters; **swa-plateau** — sliding-window attention, kv near-constant beyond the window, context effectively free (the linear fit is intentionally poor here, which is how it is detected); **moderate-kv** in between.

kv quantisation: q8_0 (set in ollama's systemd unit; the f16 default ~doubles kv). Measured one model resident at a time; `size` is total footprint, `vram` the GPU-resident part.