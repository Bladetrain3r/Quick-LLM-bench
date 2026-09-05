#!/usr/bin/env python3
"""
Report pipeline (E2E phase 2a — local arm, API-free).

Tests whether local models can write a documentation report on a codebase, and
in particular whether the prose-centric models (gemma family) that FAILED the
multi-file code gate do BETTER here — the prediction being that Google-lineage
models are stronger at prose than at multi-module logic.

Pipeline per model (subject = local-bench itself; graded by report_grade.py):
  1. facts   deterministic extraction from the files (docstrings + top defs) —
             "supply facts, let the model format", per the earlier finding.
  2. sections local model writes each report section from the facts, in parallel.
  3. audit    local model verdicts the fixed checklist about the codebase.
  4. grade    assemble the sections, score coverage/facts/sections/clean via
             report_grade, plus audit accuracy vs ground truth.

    python3 bench_report.py                 # gemma vs the code-strong models
    python3 bench_report.py --models gemma4:12b

Cloud orchestrator stages (plan the template, fix the seams) and the Haiku-solo
control are phase 2b, once cloud-API wiring lands.
"""
import argparse
import ast
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import bench
import tasks
import report_grade

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
FILES = ["bench.py", "tasks.py", "bench_project.py", "report_grade.py", "README.md",
         "minesweeper/model.py", "minesweeper/CONTRACT.md", "minesweeper/suite.py"]
SECTIONS = ["Overview", "Components", "How it works", "Usage and results", "Limitations"]
# gemma (prose) vs the code-strong models, to test the hypothesis
DEFAULT_MODELS = ["gemma4:e4b", "gemma4:12b", "gemma4:26b",
                  "gpt-oss:20b", "qwen3.6:27b", "ornith:35b"]


def fact_sheet():
    lines = ["Codebase: local-bench — a benchmark for using local models as verified builders.", ""]
    for f in FILES:
        path = os.path.join(HERE, f)
        if not os.path.exists(path):
            continue
        if f.endswith(".py"):
            src = open(path).read()
            try:
                mod = ast.parse(src)
                doc = (ast.get_docstring(mod) or "").strip().split("\n\n")[0].replace("\n", " ")
                names = [n.name for n in mod.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            except SyntaxError:
                doc, names = "", []
            lines.append(f"- {f}: {doc[:220]}")
            if names:
                lines.append(f"    defines: {', '.join(names[:12])}")
        else:
            txt = open(path).read().strip()
            first = txt.split("\n\n")[0].replace("#", "").strip()[:220]
            lines.append(f"- {f}: {first}")
    return "\n".join(lines)


def section_prompt(facts, sec):
    return (f"Facts about a codebase:\n{facts}\n\nWrite ONLY the Markdown section "
            f"'## {sec}' for a report on this codebase, using only these facts. A short "
            f"paragraph or list. No preamble, no other sections, no code fences.")


def audit_prompt(facts):
    claims = "\n".join(f"{i + 1}. {c}" for i, (c, _) in enumerate(report_grade.AUDIT_CHECKLIST))
    return (f"Facts about a codebase:\n{facts}\n\nAudit each claim about THIS codebase. "
            f"Output one line per claim, exactly 'N: PASS' if the claim is TRUE of the "
            f"codebase or 'N: FAIL' if false. Only those lines.\n{claims}")


def audit_accuracy(content):
    got = tasks.parse_verdicts(content)
    correct = sum(1 for i, (_, truth) in enumerate(report_grade.AUDIT_CHECKLIST)
                  if got.get(i + 1) == ("PASS" if truth else "FAIL"))
    return correct / len(report_grade.AUDIT_CHECKLIST)


def record(rec):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")


def run(model, facts):
    bench.stop_all()
    warm = bench.chat(model, "Reply with the single word: ready", num_predict=16)
    place = bench.placement(model)

    def one(sec):
        r = bench.chat(model, section_prompt(facts, sec))
        return sec, tasks.strip_fences(r["content"]), r["eval_tok"], r["eval_ms"]

    t = time.time()
    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as ex:
        secs = list(ex.map(one, SECTIONS))
    ar = bench.chat(model, audit_prompt(facts))
    wall = round(time.time() - t, 1)

    report = "# local-bench\n\n" + "\n\n".join(code for _, code, _, _ in secs)
    g = report_grade.grade_report(report)
    aud = audit_accuracy(ar["content"])
    tok = sum(tk for _, _, tk, _ in secs) + ar["eval_tok"]

    os.makedirs(os.path.join(OUT, "reports"), exist_ok=True)
    with open(os.path.join(OUT, "reports", model.replace(":", "_").replace("/", "_") + ".md"), "w") as f:
        f.write(report)

    rec = dict(model=model, placement=place, cold_load_ms=warm["load_ms"],
               report_overall=g["overall"], coverage=g["coverage"], facts=g["facts"],
               sections=g["sections"], clean=g["clean"], audit_acc=round(aud, 2),
               tokens=tok, wall_s=wall)
    record(rec)
    print(f"  {model:14} {place:11} report {g['overall']:.0%} "
          f"(cov {g['coverage']:.0%} facts {g['facts']:.0%} sec {g['sections']:.0%} "
          f"{'clean' if g['clean'] else 'DIRTY'})  audit {aud:.0%}  {tok} tok  {wall}s", flush=True)
    return rec


def main():
    ap = argparse.ArgumentParser(description="Report pipeline benchmark (local arm)")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    facts = fact_sheet()
    print(f"subject: local-bench ({len(facts)} chars of facts)\nmodels: {models}\n")
    rows = [run(m, facts) for m in models]
    print("\n== ranked by report quality ==")
    for r in sorted(rows, key=lambda x: -x["report_overall"]):
        print(f"  {r['model']:14} report {r['report_overall']:.0%}  audit {r['audit_acc']:.0%}  {r['tokens']} tok")


if __name__ == "__main__":
    main()
