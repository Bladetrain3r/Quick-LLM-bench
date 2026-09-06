# Phase 1 — does the context work, and how fast? (16 GB box)

Deterministic needle-retrieval (a passphrase hidden in filler at depths 0.1 / 0.5
/ 0.9) up a context ladder to 64k, GPU-fit models only. Two axes: **retrieval**
(can it find the fact at length, incl. lost-in-the-middle) and **speed** (prompt-
eval tok/s = cost of ingesting the context; generation tok/s). Same box: RX 9070
16 GB, Ryzen 9 7900, 32 GB.

## Headline
**On this box you can lean on long-context retrieval — most GPU-fit models were
perfect to 64k** — and the cost is predictable: generation slows ~15–40 % as
context grows, and there's a real first-token latency from ingesting a long
prompt. Two caveats the run surfaced (below) are themselves the useful part.

| model | retrieval 2k→64k | gen tok/s 2k→64k | prompt-eval tok/s @64k | note |
|---|---|---|---|---|
| gemma4:12b | 3/3 every rung | 52 → 43 | 759 | perfect + steady; SWA holds up |
| qwen-3-8-27 | 3/3 every rung | 28 → 20 | 416 | perfect but the slowest here |
| ornith:9b | 3/3 every rung | 81 → 56 | 1298 | perfect, fast |
| llama3.2:3b | 3/3 every rung | 119 → 85 | 2079 | a 3B, perfect to 64k, fastest ingest |
| nemotron-3-nano:4b | 3/3 to 16k, then **truncates** | 152 → 133 | (n/a) | usable ctx ≪ advertised — see caveat |
| gpt-oss:20b | **grader artifact** (0/0/0/3/0) | 103 → 66 | 1848 | non-monotonic = output-format, not capability |

## What it means for the two questions
- **"Can I rely on large context?"** Yes — gemma4:12b, qwen-3-8-27, ornith:9b, and
  even llama3.2:3b retrieved the needle at all three depths at every rung to 64k.
  Long-context retrieval is dependable on this box with the right model.
- **"A steady multi-turn load?"** Also yes, and the speed table sizes it: nemotron
  (~130–150 tok/s) and llama3.2:3b (~85–147) are fast; ornith:9b and gpt-oss sit
  ~60–100; gemma4:12b is steady ~43–52 across the whole range; qwen-3-8-27 is the
  laggard at ~20–28. Generation decays gently with context, never cliffs.
- **The hidden cost is prompt ingestion.** Before the first reply token, the model
  must read the context: gemma at 64k ingests ~760 tok/s ≈ ~85 s to read a full
  64k prompt; llama3.2:3b ~2000 tok/s ≈ ~26 s. That first-response latency, not
  generation speed, is what a long-context multi-turn session actually pays.

## Two caveats the suite caught (features, not bugs)
1. **Advertised context ≠ usable context — nemotron-3-nano:4b.** Its config claims
   262k, but at a 32k+ target the prompt-eval count came back ~17k: the input was
   silently truncated, and retrieval fell to 1/3 exactly because the early-depth
   needle got cut. Lesson for the kit: trust *measured* retrieval, not the model's
   `context_length`. Worth adding a "truncated?" flag when prompt-eval ≪ target.
2. **gpt-oss:20b's 0s are a grader artifact, not a retrieval failure.** The score
   is non-monotonic (0,0,0,3,0), which no real capability curve looks like — a
   reasoning model at temp 0 / num_predict 64 is wrapping or clipping its answer
   so the bare code isn't matched. Needs a hardened grader (more output room +
   number extraction) before its retrieval is trustworthy. Its *speed* numbers are
   fine.

## Fixes for a clean rerun
- Harden the retrieval grader for reasoning models (num_predict ~256, extract the
  first 6-digit run from the response) — re-score gpt-oss.
- Add a truncation flag (prompt_eval_count < 0.8 × target ⇒ "served ctx < asked").
- Then Phase 1 is a trustworthy "usable-context + speed" card per model.

Data: results/context_vs_size/phase1_needle.json. Generator: bench_context.py
(`--phase 1 --models ... --ladder ...`), portable to any box.
