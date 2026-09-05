#!/usr/bin/env python3
"""
Multi-file project benchmark: the minesweeper task.

Two modes, both against the SAME fixed contract (minesweeper/CONTRACT.md +
the given model.py), so they are directly comparable:

  single   one model writes all three modules in one shot -> assemble -> grade.
           Tests whether a model holds a coherent multi-module design.
  split    three module-generations run concurrently -> assemble -> grade.
           Tests whether independently-written modules COMPOSE. By default the
           three are the same model (does one model's own parts fit together?);
           --team assigns a different model per module (the small-model team).

Grading runs minesweeper/suite.py against the assembled project: L1 logic (the
gate), L2 render, L3 ui+integration.

    python3 bench_project.py                       # every model: single vs split
    python3 bench_project.py --models gemma4:12b
    python3 bench_project.py --team ornith:9b,gemma4:12b,gpt-oss:20b
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import bench
import tasks  # for strip_fences

HERE = os.path.dirname(os.path.abspath(__file__))
MSW = os.path.join(HERE, "minesweeper")
OUT = os.path.join(HERE, "results")
MODULES = ["logic.py", "render.py", "ui.py"]
CONTRACT = open(os.path.join(MSW, "CONTRACT.md")).read()

SINGLE_PROMPT = CONTRACT + (
    "\n\nImplement ALL THREE modules. Output each one delimited EXACTLY like:\n"
    "=== FILE: logic.py ===\n<code>\n=== FILE: render.py ===\n<code>\n"
    "=== FILE: ui.py ===\n<code>\nOutput only those blocks — no prose, no markdown fences."
)


def split_prompt(module):
    return CONTRACT + (
        f"\n\nImplement ONLY {module} to the contract above. Output only the Python "
        f"source for {module} — no delimiters, no markdown fences, no prose."
    )


def extract_files(content):
    parts = re.split(r"^===\s*FILE:\s*(\S+?\.py)\s*===\s*$", content, flags=re.M)
    files = {}
    for i in range(1, len(parts), 2):
        files[parts[i].strip()] = tasks.strip_fences(parts[i + 1])
    return files


def evaluate(files):
    """Assemble files + the given model.py/suite.py, run the suite, return grades."""
    d = tempfile.mkdtemp(prefix="msw_")
    try:
        shutil.copy(os.path.join(MSW, "model.py"), d)
        shutil.copy(os.path.join(MSW, "suite.py"), d)
        for name, code in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(code or "")
        for mod in MODULES:                      # missing module -> empty -> import error
            p = os.path.join(d, mod)
            if not os.path.exists(p):
                open(p, "w").close()
        r = subprocess.run([sys.executable, os.path.join(d, "suite.py"), d],
                           capture_output=True, text=True, timeout=60)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            return {"l1": False, "l1_note": "suite-crash", "l2": False, "l3": False,
                    "stderr": (r.stderr or "")[-300:]}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def record(rec):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "project.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")


def _show(label, res):
    lvl = "".join(("L" + k[1] if res.get(k) else "·" + k[1]) for k in ("l1", "l2", "l3"))
    note = "" if res.get("l1") else f"  ({res.get('l1_note', '')})"
    print(f"  {label:26} {lvl}{note}", flush=True)


def _fix_prompt(prev, res):
    notes = "; ".join(f"{lvl.upper()}: {res.get(lvl + '_note', '')}"
                      for lvl in ("l1", "l2", "l3") if not res.get(lvl))
    return (CONTRACT + f"\n\nA previous attempt at all three modules FAILED these checks: "
            f"{notes}.\n\nPREVIOUS ATTEMPT:\n{prev}\n\nFix the code so those checks pass. "
            f"Output ALL THREE modules again in the exact '=== FILE: logic.py ===' format. "
            f"Only the code.")


def run_single(model, do_fix=False):
    bench.stop_all()
    r = bench.chat(model, SINGLE_PROMPT)
    place = bench.placement(model)
    res = evaluate(extract_files(r["content"]))
    res.update(mode="single", model=model, placement=place, eval_tok=r["eval_tok"])
    if do_fix and not all(res.get(l) for l in ("l1", "l2", "l3")):
        fr = bench.chat(model, _fix_prompt(r["content"], res))
        fixed = evaluate(extract_files(fr["content"]))
        res["fixed"] = {l: bool(fixed.get(l)) for l in ("l1", "l2", "l3")}
        res["fix_tok"] = fr["eval_tok"]
    record(res)
    _show(f"single {model}", res)
    if "fixed" in res:
        fx = res["fixed"]
        lv = "".join(("L" + k[1] if fx[k] else "·" + k[1]) for k in ("l1", "l2", "l3"))
        print(f"    -> after one fix: {lv}", flush=True)
    return res


def run_split(assignment, label):
    """assignment: list of (module.py, model). Runs the modules concurrently."""
    bench.stop_all()

    def one(item):
        module, model = item
        c = bench.chat(model, split_prompt(module))
        files = extract_files(c["content"])
        code = files.get(module) or tasks.strip_fences(c["content"])
        return module, code, c["eval_ms"]

    with ThreadPoolExecutor(max_workers=len(assignment)) as ex:
        got = list(ex.map(one, assignment))
    files = {m: code for m, code, _ in got}
    res = evaluate(files)
    res.update(mode="split", model=label, placement="+".join(sorted({m for _, m in assignment})),
               par_ms=max(ms for _, _, ms in got), ser_ms=sum(ms for _, _, ms in got))
    record(res)
    _show(f"split  {label}", res)
    return res


def main():
    ap = argparse.ArgumentParser(description="Minesweeper multi-file project benchmark")
    ap.add_argument("--models", default=",".join(bench.DEFAULT_MODELS))
    ap.add_argument("--team", default="", help="3 models, one per module (logic,render,ui)")
    ap.add_argument("--repeats", type=int, default=3, help="repeats per mode (variance is large at n=1)")
    ap.add_argument("--fix", action="store_true", help="single-load: one self-correction pass on a failed run")
    args = ap.parse_args()

    if args.team:
        team = [m.strip() for m in args.team.split(",")]
        if len(team) != 3:
            sys.exit("--team needs exactly 3 models (logic,render,ui)")
        print(f"team: {team}")
        run_split(list(zip(MODULES, team)), "team:" + "+".join(team))
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    K = args.repeats
    print(f"models: {models}  repeats={K}\n"
          f"L = level passed, · = level failed (l1 logic gate, l2 render, l3 ui)\n")
    for m in models:
        print(f"== {m} ==", flush=True)
        agg = {"single": {"l1": 0, "l2": 0, "l3": 0}, "split": {"l1": 0, "l2": 0, "l3": 0},
               "fixed": {"l1": 0, "l2": 0, "l3": 0}}
        for _ in range(K):
            rs = run_single(m, do_fix=args.fix)
            rp = run_split([(mod, m) for mod in MODULES], m + " (self-split)")
            for k in ("l1", "l2", "l3"):
                agg["single"][k] += 1 if rs.get(k) else 0
                agg["split"][k] += 1 if rp.get(k) else 0
                # after-fix = passed one-shot OR recovered by the single correction pass
                agg["fixed"][k] += 1 if (rs.get(k) or rs.get("fixed", {}).get(k)) else 0
        a = agg["single"]
        print(f"  => single      L1 {a['l1']}/{K}  L2 {a['l2']}/{K}  L3 {a['l3']}/{K}", flush=True)
        if args.fix:
            f = agg["fixed"]
            print(f"  => single+fix  L1 {f['l1']}/{K}  L2 {f['l2']}/{K}  L3 {f['l3']}/{K}  "
                  f"(one-shot + one correction)", flush=True)
        s = agg["split"]
        print(f"  => split       L1 {s['l1']}/{K}  L2 {s['l2']}/{K}  L3 {s['l3']}/{K}", flush=True)


if __name__ == "__main__":
    main()
