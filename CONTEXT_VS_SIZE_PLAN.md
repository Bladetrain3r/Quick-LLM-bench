# Plan (parked) — Context vs model size: a memory-budget tuning suite

Status: PLAN ONLY, not started (2026-09-06). Idea: Ziggy. Do not run until the
essay tangent is clear.

## The question
Under a fixed memory budget on this box (RX 9070, 16 GB VRAM; + system RAM), is a
task better served by spending the budget on **more parameters** (bigger model,
less room for context) or on **more context** (smaller model, larger kv-cache)?
And how much does it cost to spill *context* (kv-cache) into system RAM versus
spilling *weights*? Output: per-task tuning guidance — the model-size/context
point that maximises quality-per-second within a given RAM+VRAM profile.

## Phase 0 — calibration (the "initial two-phase tests")
Establish, per model, the **kv-cache footprint per 1K tokens of context**, so
"context that fits in budget X" is computable rather than guessed.
- Load each model at two context sizes (e.g. num_ctx 4K and 16K), read the
  reported footprint (`/api/ps` size vs size_vram; ollama's load report), and
  take the slope → GB per 1K tokens (kv). Record weights footprint (fixed) and
  overhead separately. (kv quantisation, if used, is a variable to pin.)
- Result: for each model, `fits(budget) = max ctx where weights + kv(ctx) +
  overhead <= budget`. This underwrites every later phase.
- Reuse the harness's placement check (bench.py `/api/ps` size vs size_vram) and
  the clean-GPU tenancy discipline; one model resident at a time.

## Phase 1 — GPU-only, 16 GB VRAM ceiling
Models whose weights fit in 16 GB (GPU-resident). For each: find max context that
fits in VRAM (Phase 0), then run the task suite at a ladder of context sizes up to
that max. Measure pass-rate and tokens/sec vs context length. The comparison:
does a smaller GPU model with more affordable context beat a larger one with less,
on the same 16 GB?

## Phase 2 — GPU + 8 GB system RAM (24 GB total profile)
Same GPU-fit models, but allow the **kv-cache to extend into +8 GB system RAM**
(weights stay in VRAM). Measure the speed cost of context-in-RAM vs
context-in-VRAM, and whether the now-affordable extra context buys task quality.
Hypothesis to test: spilling *context* to RAM hurts far less than spilling
*weights*, so the cheap win is more context, not a bigger model.

## Phase 3 — spillover models under the same 24 GB total
The >16 GB models (weights already spill to RAM). Give them the same 24 GB total
budget but only the context that fits the remainder after weights. Compare
head-to-head at equal total memory: a big spilled model with little context vs a
small GPU-resident model with lots of context. This is the payoff comparison —
where the budget is best spent for a given task type.

## Metrics (all phases)
pass-rate (bench tasks) · tokens/sec (prompt eval + generation, separated) ·
placement (gpu/mixed/cpu via /api/ps) · context used vs context that fit ·
quality-per-second and quality-per-GB. Answer-mode default (think:false, system
prompt), per existing harness; reasoning models get a per-model budget.

## What it tells us
A lookup, per task class, of the best model-size↔context tradeoff at each memory
profile (16 GB VRAM; 24 GB VRAM+RAM) — so the delegate work picks a model by the
box it's on, not by habit. Ties into the local-builders method (proposal
4de19479bd) as the "which local model, and how much context" calibration.

Files when built: extend bench.py with a `--ctx-ladder` and a Phase-0 kv
calibration helper; results to results/context_vs_size/.
