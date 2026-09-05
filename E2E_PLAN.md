# E2E benchmark — orchestrated codebase report

**Status: plan.** The capstone benchmark: a cloud "main model" orchestrates local
models through a multi-stage, read-only workflow that produces a report on a
codebase, measured against a cloud-solo control. The subject is **local-bench
itself** — a real, bounded codebase whose parts we already know, with a
known-good reference (its README + bill of parts) to grade against.

## The two arms

- **Local pipeline** — a cloud orchestrator (Claude via API) plans and stitches;
  local models (ollama) do the bulk generation. Cloud tokens are spent only on
  the orchestration stages; local generation is free.
- **Cloud-solo control** — one cloud model (Haiku 4.5: cheap, reliable at
  mid-complexity document work, non-reasoning by default) does the whole task in
  the cloud. This is the **denominator**: every "local saves tokens" claim is
  measured against it, at comparable report quality.

## The stages (local-pipeline arm)

| # | stage | who | reasoning | output | graded by |
|---|---|---|---|---|---|
| 1 | read README, docs, file tree | cloud orchestrator | yes | structured notes | (input to 2) |
| 2 | bill of parts from the files | local, parallel | no (answer-mode) | parts inventory | coverage % vs known parts |
| 3 | plan the report template | cloud orchestrator | yes | section outline | required sections present |
| 4 | audit each part + collate a draft to the template | local, parallel | mixed | draft + audit findings | audit verdicts vs ground truth; draft coverage |
| 5 | fix seams, recheck low-confidence parts, finalise | cloud orchestrator | yes | final report | fact-check (no false claims) + coverage + rubric |

Each stage writes its artifact and its metrics to a checkpoint dir, so a failed
stage is both a finding and a re-run point without redoing the pipeline.

## Metrics (every stage, both arms)

Same instruments as the other benchmarks, plus the pipeline aggregates:
- per call: model, placement (local), cold-load, warm time, tokens in, tokens
  out, wall time, success.
- per arm: **total cloud tokens** (local-pipeline = orchestrator stages only;
  cloud-solo = everything), total wall time, final report grade.
- the headline: local-pipeline cloud cost vs cloud-solo cost at equal quality.
- the failure map: which stage fails, how often — the basis for targeted re-runs.

## Grading a report — the crux (see report_grade.py)

A report is fuzzy where code is not, so grading is mechanical wherever possible
and the soft remainder is named as such. Anchored on local-bench's known parts:
- **coverage**: fraction of the known components the report names.
- **audit correctness**: verdicts on a fixed checklist about local-bench, scored
  against ground truth (exactly like the audit tasks).
- **structure**: the required sections are present.
- **hallucination**: none of a fixed set of tempting-but-false claims appears
  (e.g. "uses pytest", "runs on a GPU cluster", "temperature defaults to 0").
- **prose quality**: a small rubric, scored by the orchestrator or by hand —
  the one openly subjective metric.

## The reasoning-vs-not axis

The stages differ by design: stage 2 (bill of parts) and the audit half of stage
4 are answer-mode mechanical; stages 1, 3 and 5 (reading, planning, seam-fixing)
are where reasoning should earn its keep. So this is a within-pipeline comparison
of reasoning value, not just per-model — run the local stages answer-mode vs
`--think`, and the orchestrator/control across reasoning-effort levels.

## New dependency: cloud API wiring

Both arms need a real Anthropic-API path (orchestrator + Haiku control), keys
from Bao `village/cloudkeys` injected via `bao-kit with`, never in the repo. The
harness must record cloud token usage from the API response (input/output, and
reasoning tokens where applicable) the way it records ollama's counts.

## Phasing

1. **Grading rubric** (report_grade.py) — done first; it decides whether any of
   this means anything. Validate it against local-bench's README as a known-good.
2. **The pipeline** — stages as functions, artifacts + metrics per checkpoint,
   one-pass (no auto-retry; failures are recorded).
3. **The control** — Haiku-solo via API for the token comparison.
4. **The sweeps** — reasoning on/off per stage; the correction pass as a separate
   mode (feed a stage its behavioural error once, remeasure).

## Open questions

- How much of stage 1's "reading" is fair to pre-extract (like we feed facts to
  local models) vs left to the orchestrator? Pre-extraction lowers cloud input
  tokens but moves work out of the measured pipeline. Decide and state it.
- Report quality parity is a judgement call; the rubric bounds it but does not
  eliminate it. The reference report keeps it honest.
- One codebase (local-bench) is n=1 for the *task*; a second subject later
  (PyTTAI?) tests whether the pipeline generalises.

## Early finding (phase 2a, local report arm — n=1, 2026-09-05)

Ran the local report pipeline (bench_report.py) across the gemma family vs the
code-strong models, subject = local-bench, graded by report_grade.py. Result on
the MEASURABLE axes: code-strong win (gpt-oss:20b, qwen3.6:27b 78%; ornith:35b
73%; all three gemma 67%). But reading the reports shows the split the grader
misses: **report quality is two axes.**
- **Completeness / accuracy** — coverage, facts, audit. The mechanical grader
  captures it; gpt-oss and qwen win (they enumerate real function names, every
  task, the primitives).
- **Readability / style** — gemma writes cleaner, flowing, human-facing prose,
  and far cheaper (~800 tok/12s vs gpt-oss 4277 tok/43s). The grader does NOT
  capture this; it's the soft axis the plan already named.

Implications for the full build: (1) add a readability rubric (a judge pass, or
hand score) so the grade isn't completeness-only. (2) gemma omitted facts it was
GIVEN — completeness is partly promptable, so a richer fact-supply / "name the
specific mechanisms" instruction is a cheap lever. (3) the pipeline could pair a
readable drafter (gemma, cheap) with a fact-dense reviewer, which is exactly what
the cloud seam-fix stage is for. Caveat: n=1 per model; add repeats.
