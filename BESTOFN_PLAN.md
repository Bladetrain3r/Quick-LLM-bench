# Plan (parked) — best-of-N + self-selection on minesweeper

Status: PLAN ONLY (2026-09-06). Idea: Ziggy. Do not run today.

## Question
Does producing several candidate solutions and choosing among them beat one-shot,
and — the sharper part — can a model *pick its own winner* without the test?
"A variant of multiple-choice-for-completion": is discrimination easier than
generation for these models?

## Three arms (reuse minesweeper CONTRACT + suite.py grading)
- **pass@1** — one candidate, graded (baseline; = current bench_project single).
- **pass@3-oracle** — draw 3 candidates (temp ~0.8 for diversity); pass if ANY
  clears the suite. Measures COVERAGE (is a solution in the distribution?).
- **pass@3-self** — give the model its own 3 candidates + the contract, ask which
  best satisfies it (index), grade the chosen one. Measures DISCRIMINATION.

**The headline metric is the gap `pass@3-self` vs `pass@3-oracle`** — how well a
model judges its own work.

## Why it matters
Lands on the local-builders thesis (4de19479bd): if a model generates a correct
solution 1-in-3 but cannot select it, best-of-N helps only WITH the acceptance
test as selector → the operator's verification gate is confirmed irreplaceable.
If it can self-select, best-of-N is a cheap quality lift and can pull a
near-the-wall model over it.

## Design notes
- **Long context is the enabler**: the self-select prompt holds 3 full multi-file
  candidates + contract → needs the 64-128k budget Phase 0/1 confirmed (5 of 6
  models hold it). This experiment is only clean now that we know who can.
- **temp > 0** (~0.8) for candidate diversity; the current bench runs answer-mode
  ~0.2 which would give near-identical samples.
- **Sub-variant worth comparing**: "3 independent samples" vs "3 produced in one
  long call then self-choose" — does seeing them side by side help selection?
- **Pick borderline models**: minesweeper's L1 logic gate is a hard wall
  (gemma 0/3; gpt-oss/qwen3.6:27b/ornith:35b clear it). Best-of-N lifts models
  near the boundary, not far below it — choose the boundary cases to see effect.
- **Cost**: 3× generation + a select pass; free-ish locally but ~3× slower — the
  write-up weighs pass-rate lift against that.
- Diversity check: confirm the 3 candidates actually differ (models go lazy).

Files when built: extend bench_project.py with a `--best-of N` mode + a
self-select pass; results to results/bestofn/.
