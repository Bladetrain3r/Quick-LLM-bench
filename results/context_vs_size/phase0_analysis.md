# What a 16 GB box can hold — kv-cache calibration, read for humans

**Hardware:** Ryzen 9 7900, Radeon RX 9070 (16 GB VRAM), 32 GB DDR5, ollama
(kv cache q8_0, set in the systemd unit). Budgets read as **16 GB** = fits in VRAM (fast), **24 GB** = VRAM
plus ~8 GB of system RAM (context or weights spill, slower). 23 installed models,
Phase 0 of the context-vs-size suite. This informs a choice; it does not rank.

## The one surprising finding
**kv-cache cost per token is set by attention architecture, not model size — and
on this zoo it runs roughly *inverse* to size.** The spread is ~55×:

- **llama3.2:3b** — the *smallest* model — has the *most expensive* context in the
  zoo: **66 MB per 1k tokens**. Its weights are 2 GB but 128k of context costs ~8 GB.
- **gpt-oss:20b** — a 20B — has the *cheapest*: **1.2 MB per 1k**. It holds its full
  131k context in ~12.8 GB, entirely in VRAM.

So the folk rule "pick a smaller model to leave room for context" is false in
general. What decides context cost is the attention design (classic multi-head vs
grouped-query vs sliding-window), not the parameter count.

## Three regimes to pick by
- **swa-plateau — context is effectively free** (every gemma here). Sliding-window
  attention caps the kv cache, so footprint barely grows with context; gemma-12b
  holds 262k and gemma3/e4b hold 131k at flat memory. (Detected by a deliberately
  poor linear fit, R² 0.3–0.6 — the plateau is the signal.)
- **cheap-kv — context nearly free** (gpt-oss:20b, 1.2 MB/1k). Spend the budget on
  parameters; context comes along for almost nothing.
- **expensive-kv — the real tradeoff zone** (llama3.2 66, qwen dense 39–43, ornith:9b
  24 MB/1k). Every 1k of context costs real memory and competes with weights.
- moderate-kv in between (nemotron ~14, qwen3.8 14, ornith:35b 12, lfm2.5 10).

## What THIS box does best (16 GB VRAM, no spill)
Two "have it both ways" picks — big capability *and* long context, all in VRAM:
- **gpt-oss:20b** — 20B, full **131k** context, cheap kv, fits VRAM. Remarkable value.
- **gemma4:12b / gemma4-code** — 12B, up to **262k** context free via SWA.
Plus cheap all-VRAM long-context small models: gemma4:e4b (131k, 3.3 GB),
nemotron-3-nano (262k, 2.8 GB), ornith:9b (262k — expensive kv but tiny weights).

## Where the tradeoff actually bites
Only when a model **both** spills weights past 16 GB **and** has expensive kv.
**qwen3.6:27b** is the exact case: weights 16.8 GB (won't fit VRAM) + 43 MB/1k, so
even at 24 GB it reaches only ~167k of its trained 262k — context and weights
genuinely fight. Contrast **gemma4:26b**, same size class and also spilling
(18.5 GB weights), which still reaches the full 262k at 24 GB because its kv is
~free (SWA). Same class, opposite context economics — purely architecture.

## The param-vs-context answer, for this box
For long-context work, choose a cheap-kv or SWA model and you never trade
parameters for context (gpt-oss:20b, gemma-12b). Reach for an expensive-kv dense
model only when its quality on the actual task earns the memory it charges for
every 1k of context — and then budget context deliberately. Phase 1–3 will put
numbers on the quality side of that "only when"; Phase 0 says which models even
make the tradeoff necessary.

## Method note
Duplicate tags in the zoo (qwen3.6:27b ≡ qwen3.6_27b, gemma4:e4b ≡ gemma4-e4b,
ornith:9b ≡ ornith_9b_32k, the nemotron trio) returned identical numbers — the
measurement is stable. Full data + the portable generator: `bench_context.py`,
`results/context_vs_size/phase0_{report.md,calibration.json}`. Run it on your own
box: `python3 bench_context.py` (auto-discovers your models; `--budgets` for your
ceilings).
