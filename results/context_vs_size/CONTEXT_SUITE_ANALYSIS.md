# The context-vs-size suite — full analysis (16 GB box)

**Hardware:** Ryzen 9 7900, Radeon RX 9070 (16 GB VRAM), 32 GB DDR5, ollama with
**kv cache = q8_0** (set in ollama's systemd unit). **Budgets:** 16 GB = fits VRAM (fast); 24 GB = VRAM + ~8 GB
system RAM (spill, slower). Method: Phase 0 calibrates each model's memory
footprint (kv slope + weights) and its real max; a warmup preflight confirms the
*usable* max (catches silent truncation) and grader health; Phase 1 runs a
deterministic needle-retrieval task up a context ladder to each model's confirmed
max, measuring retrieval accuracy and speed. This informs a choice; it does not
rank.

## Table A — memory map (Phase 0)
What a model costs, and the largest context it can hold at each budget.

| model | regime | weights GB | kv MB/1k | usable max | fits 16 GB | fits 24 GB |
|---|---|---|---|---|---|---|
| gpt-oss:20b | cheap-kv | 12.7 | 1.2 | 131k+ | 131k | 131k |
| ornith:9b | expensive-kv | 5.2 | 24.0 | 131k+ | 262k | 262k |
| gemma4:12b | swa-plateau | 7.9 | ~0 (plateau) | 131k+ | 262k | 262k |
| llama3.2:3b | expensive-kv | 2.1 | 66.2 | 131k | 131k | 131k |
| qwen-3-8-27 | expensive-kv | 12.1 | 38.9 | 131k* | 101k | 262k |
| nemotron-3-nano:4b | moderate-kv | 2.8 | 13.9 | **16k** (truncates at 32k) | — | — |

\* qwen-3-8-27 *retrieves* correctly to 131k but spills past VRAM there — see the cliff below.

## Table B — retrieval + speed (Phase 1, to each model's confirmed max)
Retrieval was **3/3 at every depth (0.1/0.5/0.9), every rung, for every model** —
100 % within the confirmed usable window. So reliability is not the variable;
speed and the VRAM ceiling are.

| model | retrieval | gen tok/s (2k → max) | ingest tok/s @ max | ~first-token @ max | VRAM-safe ceiling |
|---|---|---|---|---|---|
| gpt-oss:20b | 3/3 to 131k | 103 → 48 | 1298 | ~83 s (107k) | **131k (no spill)** |
| ornith:9b | 3/3 to 131k | 81 → 43 | 837 | ~157 s | **131k** |
| gemma4:12b | 3/3 to 131k | 52 → 36 | 479 | ~274 s | **131k (SWA)** |
| llama3.2:3b | 3/3 to 131k | 119 → 55 | 932 | ~115 s | 131k |
| qwen-3-8-27 | 3/3 to 131k | 28 → 19.6 @65k → **4.0 @131k** | 253 | very high | **~65k** (spills at 131k) |
| nemotron-3-nano:4b | 3/3 to 16k | 149 → 140 | 3112 | ~5 s | 16k (hard cap) |

## Findings

1. **Retrieval is a solved problem within the confirmed window.** Every model got
   every needle at every depth to its real max — no lost-in-the-middle, no decay.
   The suite's job is therefore *not* "which model can retrieve" but "how far can
   each go, and at what speed" — which is exactly what Phases 0/1 + the warmup
   measure. The one model that looked bad (nemotron) was silently truncating;
   capping it at its true 16k restored 3/3.

2. **The spill cliff is the sharpest result.** qwen-3-8-27 holds 131k for
   *correctness* but at 131k its kv pushes it past 16 GB VRAM → mixed:84 % → gen
   collapses from ~20 tok/s to **4.0 tok/s** (a 5× cliff), while retrieval stays
   3/3. So "usable context" has **two thresholds**: usable-for-correctness (the
   model's max) and **usable-at-speed** (where it still fits VRAM = Phase 0's
   fits16). For qwen-3-8-27 that's ~65k for speed vs 131k for correctness. Practical
   rule: **cap context at fits(VRAM), not at model-max, whenever latency matters.**

3. **Ingestion latency, not generation, sets the interactive ceiling.** At 131k,
   gemma4:12b reads the prompt at 479 tok/s ≈ **~4.5 minutes to first token**;
   gpt-oss ~83 s; llama ~115 s. Generation speed barely matters if you wait
   minutes for token one. For a *steady multi-turn* load, the real limit is how
   much context you re-ingest per turn — so a fast-ingest model (gpt-oss, ornith)
   or a modest context is what keeps it feeling live.

4. **Speed is architecture, again.** nemotron-4b and llama3.2:3b generate fastest
   (~140/~120→55) but are limited (nemotron caps 16k; llama is a 3B); gpt-oss:20b
   and ornith:9b are the strong middle (60–100 tok/s and hold 131k *in VRAM*);
   gemma4:12b is steady but slow to ingest; qwen-3-8-27 is slowest and cliffs.

## The payoff: 64–128k backgroundable local subagents on this box
The models that hold long context **in VRAM (no spill cliff), retrieve perfectly,
and generate at a usable rate**:

- **gpt-oss:20b** — the standout: 20B capability, full 131k all in VRAM (cheap kv),
  48 tok/s at max, fastest ingest of the long-holders. First pick for a
  large-context background subagent.
- **ornith:9b** — 131k in VRAM, 43 tok/s at max, good ingest. Lighter, fast second.
- **gemma4:12b** — 131k free via SWA, but ~4.5 min ingest at max — fine for
  *backgrounded* work (you're not waiting on it), poor for interactive.
- **qwen-3-8-27** — excellent to ~65k, then the spill cliff; wire it capped at 64k.
- **nemotron-3-nano:4b** — fast but a hard 16k ceiling; a short-context speed pick.
- **llama3.2:3b** — holds 131k and fast, but it's a 3B — capability-limited for real work.

Ties to the Ollama × Claude Code integration idea: **gpt-oss:20b and ornith:9b are
the two to wire as 64–128k backgroundable subagents** — they were confirmed to
hold and *use* the context in VRAM at a usable speed, with retrieval verified.

## Method notes / caveats
- Retrieval grader hardened (256-token budget + 6-digit extraction) — this cleared
  gpt-oss's earlier false 0s (a grading artifact, never a capability gap).
- Truncation caught tokenizer-independently (prompt-eval count stops growing with
  target) — this is what exposed nemotron and set its real 16k cap.
- gemma4:12b's "131k+" max is the ladder ceiling tested, not its limit (its SWA
  kv is ~free, so it likely holds its full 262k — untested above 131k).
- **These are q8_0 kv figures — a load-bearing caveat.** The kv cache is pinned to
  q8_0 in ollama's systemd unit (half the size of the f16 default), so every
  kv/1k, every fits(), and every usable-context number here is the q8 value. On
  the f16 default, kv roughly **doubles**: context-per-GB roughly halves, and the
  spill cliff (qwen at 131k) arrives ~2× sooner. The regimes and the architecture
  story hold either way (cheap-kv vs expensive-kv is a per-model ratio), but the
  generous absolute context on this box is partly the q8 setting. A kit user must
  note their own `OLLAMA_KV_CACHE_TYPE`.
- One model resident at a time; speeds are warm (cold-load is separate, Phase 0).
  Full data: phase0_*.json, phase1_needle.json.
- Portable: `bench_context.py` runs all of this against any box's own models.
