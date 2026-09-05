# local-bench

A benchmark for using **local models as verified builders** on this box
(Ryzen 9 7900 · Radeon RX 9070 16 GB · 32 GB single-stick DDR5 · models on a
slow SSD). It exists to turn the draft figures in the "Toys or Tools" report
into measured ones, with the two controls that make the numbers honest.

## What it measures

Three kinds of task, all graded mechanically, never on a vibe:
- **Coding tasks** (`tasks.py`) — a spec plus a deterministic test; the output is
  graded by **executing** the function it wrote. Tiered 1 (easy) → 3 (hard), most
  echoing real Village/PyTTAI code: a key=value parser, an exponential-decay
  `heat`, a provenance header with a sha256, the incidence short-id/full-hash
  edge fold, a delete-aware dict merge.
- **Audit tasks** (`tasks.py`) — read an artifact against a checklist and emit a
  verdict per item, graded against known-correct verdicts. This is the config
  doctor generalised.
- **Multi-file project** (`bench_project.py` + `minesweeper/`) — build a
  three-module minesweeper against a fixed contract, graded by a tiered suite
  (L1 logic, L2 render, L3 ui). Runs in two modes: **single** (one model writes
  all three modules) and **split** (three module-generations composed), to test
  whether coherent single-load beats independent parallel generation for code.

Answer-mode is the default: a system prompt plus chain-of-thought off (`think`
off), which bounded work doesn't need and which stops reasoners looping. `--think`
runs the reasoning variant. Reasoners get a generous `num_predict` (8000); a run
that still hits the cap is flagged `CLIP`, not a clean pass.

The `E2E_PLAN.md` + `report_grade.py` sketch the next benchmark: a cloud model
orchestrating local models to write a report on a codebase (this one), against a
cloud-solo control.

## The two controls

- **Tenancy / placement.** Each model is measured *in isolation*: everything is
  unloaded (`ollama stop`), the target loaded alone, and its placement read from
  `/api/ps` as the VRAM-resident fraction — tagged `gpu`, `mixed:NN%`, or `cpu`.
  Models up to ~14 GB fit the 16 GB card; the 17–21 GB ones overflow and spill
  to CPU. A spilled timing is never mistaken for the model's real speed.
- **Cold vs warm.** The cold model-load cost (`load_duration`, real on a slow
  SSD) is measured once per model and kept separate from the warm, steady-state
  generation timing (`eval_duration`) used to compare models. K warm repeats
  per task.

Reasoners get a generous `num_predict` (8000) so thinking isn't clipped; a run
that still hits the length cap is flagged `CLIP` rather than counted a clean pass.

## Run it

```bash
cd /data/NuCode/local-bench

# fast sanity check (one small model, one task)
python3 bench.py --models ornith:9b --tasks t1_dedupe --warm-k 1

# the fit-in-VRAM set, quick
python3 bench.py --models ornith:9b,gemma4:12b,gpt-oss:20b,gemma4:e4b

# the spill set (SLOW — big models run partly on CPU)
python3 bench.py --models qwen3.6:27b,gemma4:26b,ornith:35b --warm-k 2

# the parallel small-model documentation test
python3 bench.py --docpar

# the multi-file minesweeper project: single vs split, per model
python3 bench_project.py --repeats 3
python3 bench_project.py --team ornith:9b,gemma4:12b,gpt-oss:20b   # one model per module

# grade a codebase report against local-bench's known parts (E2E crux)
python3 report_grade.py --self-check
```

Default (`python3 bench.py`) runs all seven models × ten tasks × 3 warm repeats.
The fit set is quick; the spill set is slow (a 17–21 GB model on CPU can take
minutes per task), so run them separately or drop `--warm-k` for a first pass.
The project benchmark's single-vs-split result is noisy at one sample — use
`--repeats` for pass rates, not a coin flip.

## Output

- `results/results.jsonl` — one line per run (model, task, placement, pass,
  timings, tokens, clip flag), streamed live so an interrupted run keeps its data.
- `results/summary.md` — a per-task and per-model table, written at the end.

## Notes / knobs

- ollama config in play: KV-cache quantized to 8-bit (systemd unit). That's a
  fixed condition of the run; testing 8-bit vs 16-bit is a future variable
  (memory footprint vs quality).
- `OLLAMA_HOST` env overrides the endpoint (default `http://localhost:11434`).
- To add a task: append to `TASKS` in `tasks.py` with a prompt naming the exact
  function and a `check(fn)` that returns True only when correct.

## Roadmap (what a longer run adds)

1. **GPU-resident throughput** for the fit set — the real speed of the usable
   builders.
2. **Spill penalty** for the overflow models — how much CPU-offload costs,
   quantified instead of confounded with reasoning depth.
3. **Budget-vs-complexity curve** — reasoning tokens and pass rate up the tiers,
   yielding a per-model `num_predict` that holds on hard tasks.
4. **Reasoning-effort sweep** — think on/off (and, for the cloud reviewer, low/
   med/high) vs pass rate and tokens: how little thought review actually needs.
