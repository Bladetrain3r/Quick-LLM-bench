#!/usr/bin/env python3
"""
Hybrid arm of the E2E report benchmark: a local model drafts the report (free),
then ONE cloud pass (Haiku) fixes seams, fills the specific components/mechanisms
the draft omitted, and corrects errors. The question: can free-local + a small
cloud fix reach the cloud-solo control (84% / 2173 cloud tokens) for FEWER cloud
tokens? If yes, the local-builders thesis holds for document work.

    unset BAO_TOKEN
    bao-kit with village/cloudkeys:ANTHROPIC_API_KEY=ANTHROPIC_API_KEY -- \
        python3 bench_hybrid.py --drafters gemma4:12b,gpt-oss:20b
"""
import argparse
import os
from concurrent.futures import ThreadPoolExecutor

import bench
import cloud
import report_grade
import tasks
from bench_report import fact_sheet, SECTIONS, audit_prompt, audit_accuracy, section_prompt

SEAM_PROMPT = (
    "A local model drafted the report below on a codebase. Using the FACTS, fix the "
    "seams between sections, FILL IN specific components and mechanisms the draft "
    "omitted, and correct anything inaccurate. Keep it readable and concise. Output "
    "only the final report in Markdown, no preamble.\n\nFACTS:\n{facts}\n\nDRAFT:\n{draft}")

CONTROL = "84% report / 90% audit / 2173 cloud tokens (Haiku solo)"


def local_draft(model, facts):
    bench.stop_all()
    bench.chat(model, "Reply with the single word: ready", num_predict=16)

    def one(sec):
        r = bench.chat(model, section_prompt(facts, sec))
        return sec, tasks.strip_fences(r["content"])

    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as ex:
        secs = list(ex.map(one, SECTIONS))
    ar = bench.chat(model, audit_prompt(facts))
    draft = "# local-bench\n\n" + "\n\n".join(c for _, c in secs)
    return draft, audit_accuracy(ar["content"])


def hybrid(drafter, facts, seam_model):
    draft, aud = local_draft(drafter, facts)
    dg = report_grade.grade_report(draft)
    r = cloud.call(SEAM_PROMPT.format(facts=facts, draft=draft), model=seam_model, max_tokens=3000)
    fg = report_grade.grade_report(r["content"])
    with open(os.path.join(os.path.dirname(__file__), "results", "reports",
                           "hybrid_" + drafter.replace(":", "_") + ".md"), "w") as f:
        f.write(r["content"])
    return dict(drafter=drafter, draft=dg["overall"], final=fg["overall"],
                cov=fg["coverage"], facts=fg["facts"], clean=fg["clean"], audit=aud,
                cloud_in=r["in_tok"], cloud_out=r["out_tok"],
                cloud_tok=r["in_tok"] + r["out_tok"], sec=r["sec"])


def main():
    ap = argparse.ArgumentParser(description="Hybrid report arm: local draft + cloud seam-fix")
    ap.add_argument("--drafters", default="gemma4:12b,gpt-oss:20b")
    ap.add_argument("--seam-model", default=cloud.HAIKU)
    args = ap.parse_args()
    facts = fact_sheet()
    os.makedirs(os.path.join(os.path.dirname(__file__), "results", "reports"), exist_ok=True)
    print(f"control: {CONTROL}\nseam-fix model: {args.seam_model}\n")
    rows = []
    for d in [x.strip() for x in args.drafters.split(",") if x.strip()]:
        r = hybrid(d, facts, args.seam_model)
        rows.append(r)
        verdict = "BEATS control cost" if r["cloud_tok"] < 2173 and r["final"] >= 0.82 else \
                  ("cheaper, lower quality" if r["cloud_tok"] < 2173 else "not cheaper")
        print(f"  {d:14} draft {r['draft']:.0%} -> final {r['final']:.0%} "
              f"(cov {r['cov']:.0%} facts {r['facts']:.0%}) audit {r['audit']:.0%}  "
              f"cloud {r['cloud_tok']} tok (in {r['cloud_in']}/out {r['cloud_out']})  {r['sec']}s  [{verdict}]", flush=True)


if __name__ == "__main__":
    main()
