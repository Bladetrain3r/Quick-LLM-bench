# Plan (parked) — result-analysis as a graded long-context task

Status: PLAN ONLY (2026-09-07). Idea: Ziggy. Not run today.

## Question
Give an agent a real results set (in context) + a light analysis spec, ask it to
write a SCRIPT that produces a table + charts on a few standard axes. Grade the
script's output against a reference (cloud-built) analysis script. Tests
long-context *comprehension and use* (not just retrieval), and is objectively
gradeable because statistical processing has a ground truth.

## Why it fills the gap
Phase 1 (needle) showed retrieval works at length; this tests reasoning OVER a
dataset in context. Rare combo: long context AND mechanical grading.

## Design discipline (the part that makes it work)
- **Deliverable is a script, not computed numbers.** Models hallucinate arithmetic
  over many in-context numbers; the script computes, the model reasons about what
  to compute. This is what makes it gradeable and sidesteps LLM-can't-do-math.
- **Grade numerically on the table/stats** (exact, float tolerance), **structurally
  on charts** (script runs, emits expected files on the named axes) — never pixels.
- **The context only earns its place when correct analysis requires NOTICING a
  wrinkle in the data.** If the spec fully dictates the table, the data is
  decorative and it's just codegen-from-spec. Design the data to contain a wrinkle
  the good script must handle.

## Best fodder: our own results (dogfood + self-validating)
The suite's own outputs already carry the right wrinkles:
- Phase-0 loads: the **SWA plateau** breaks a naive linear kv fit (a good script
  detects non-linearity, doesn't report a bogus slope — exactly the refinement the
  architect made by hand).
- **nemotron truncation** (prompt_eval_count < target) — a good script flags it.
- **duplicate tags** returning identical numbers — a good script dedups/notes it.
An agent's script is "correct" only if it catches what the hand analysis caught.

## Grading harness
- Reference analysis script (cloud/architect-written) = ground truth.
- Run agent's script + reference on the same data in a sandbox; compare table
  cells + computed stats (numeric, tolerance); check charts produced on the right
  axes. Pass = numeric match + structural chart match.
- Two-tier verified-delegate pattern (4de19479bd): cloud reference, local scripts
  measured against it — verification built in.

## Pitfalls
- Context-size tension: big enough to be long-context, small enough the model can
  hold the STRUCTURE (~8-32k of real data, not 128k of untrackable rows).
- Don't let the spec pre-chew the answer (context becomes decorative).
- Chart grading is structural, not exact.

Files when built: a task in bench (results + spec -> script -> run -> compare);
results to results/analysis_task/.
