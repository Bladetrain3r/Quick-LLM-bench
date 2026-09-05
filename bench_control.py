#!/usr/bin/env python3
"""
Cloud-solo control for the E2E report benchmark (E2E_PLAN.md). One cloud model
(Haiku 4.5 by default) writes the whole report on local-bench in one pass, graded
the SAME way as the local arm (report_grade). This is the denominator: it puts a
real cloud token cost next to the local models' free generation.

    unset BAO_TOKEN   # avoid the stale shell-shadow token
    bao-kit with village/cloudkeys:ANTHROPIC_API_KEY=ANTHROPIC_API_KEY -- \
        python3 bench_control.py
"""
import os
import sys

import cloud
import report_grade
from bench_report import fact_sheet, SECTIONS, audit_prompt, audit_accuracy

MODEL = os.environ.get("CONTROL_MODEL", cloud.HAIKU)


def main():
    facts = fact_sheet()
    secs = ", ".join(SECTIONS)
    report_prompt = (
        f"Facts about a codebase:\n{facts}\n\nWrite a documentation report on this "
        f"codebase in Markdown with exactly these sections: {secs}. Use ONLY these "
        f"facts; name the specific components and mechanisms. No preamble, no fences.")
    r = cloud.call(report_prompt, model=MODEL, max_tokens=3000)
    a = cloud.call(audit_prompt(facts), model=MODEL, max_tokens=600)

    g = report_grade.grade_report(r["content"])
    aud = audit_accuracy(a["content"])
    tin, tout = r["in_tok"] + a["in_tok"], r["out_tok"] + a["out_tok"]

    os.makedirs(os.path.join(os.path.dirname(__file__), "results", "reports"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "results", "reports",
                           "control_" + MODEL.replace(":", "_") + ".md"), "w") as f:
        f.write(r["content"])

    print(f"CONTROL {MODEL}")
    print(f"  report {g['overall']:.0%}  (cov {g['coverage']:.0%} facts {g['facts']:.0%} "
          f"sec {g['sections']:.0%} {'clean' if g['clean'] else 'DIRTY'})   audit {aud:.0%}")
    print(f"  CLOUD tokens: in {tin}  out {tout}  total {tin + tout}   time {round(r['sec'] + a['sec'], 1)}s")
    print("\n  vs local arm (from bench_report): gemma family 67%, ornith:35b 73%, "
          "gpt-oss:20b & qwen3.6:27b 78% — all on FREE local tokens.")


if __name__ == "__main__":
    main()
