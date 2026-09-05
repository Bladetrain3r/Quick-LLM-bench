#!/usr/bin/env python3
"""
Local-model builder benchmark.

Measures local models on bounded, test-graded coding tasks, with the two
controls that make the numbers mean something (both learned the hard way):

  TENANCY   Each model is measured in isolation: everything is unloaded first,
            the target loaded alone, and its PLACEMENT verified via /api/ps
            (VRAM used vs total). A model that overflows the card spills to
            CPU; every datapoint is tagged gpu / mixed / cpu so a spilled
            reading is never mistaken for the model's real speed.

  COLD/WARM The cold model-load cost (load_duration, real on a slow SSD) is
            measured once per model and reported separately from the warm,
            steady-state generation timing used to compare models.

Usage:
    python3 bench.py                       # default model set, warm_k=3
    python3 bench.py --models ornith:9b,gemma4:12b --warm-k 5
    python3 bench.py --tasks t1_dedupe,t2_heat
    python3 bench.py --docpar              # the parallel small-model doc test

Results stream to results/results.jsonl; a summary table prints at the end and
is written to results/summary.md. Nothing is lost if a long run is interrupted.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import tasks as T

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")

DEFAULT_MODELS = [
    # fits in 16 GB VRAM -> runs on the card
    "ornith:9b", "gemma4:12b", "gpt-oss:20b", "gemma4:e4b",
    # overflows 16 GB -> spills to CPU (measured on purpose)
    "qwen3.6:27b", "gemma4:26b", "ornith:35b",
]

CALL_TIMEOUT = 1200      # seconds; a spilled big model on CPU can be very slow
NUM_PREDICT = 8000       # generous, so reasoners are not clipped; CLIP is flagged
NUM_CTX = 8192
TEMP = 0.2               # NOT 0: greedy decoding sends some reasoners (gemma4)
                         # into an endless thinking loop that never emits an answer
THINK = False            # answer-mode default: bounded tasks don't need CoT, and
                         # thinking-on invites the loop; --think runs the reasoning variant
SYSTEM = ("You are a precise tool. Follow the instruction exactly and output only what "
          "it asks for - no preamble, no explanation, no markdown fences. Without this a "
          "reasoning model can loop in its own thoughts and never answer.")


# --- ollama plumbing -------------------------------------------------------

def _get(path):
    with urllib.request.urlopen(OLLAMA + path, timeout=15) as r:
        return json.load(r)


def _post(path, body, timeout):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ps():
    try:
        return _get("/api/ps").get("models", [])
    except Exception:  # noqa: BLE001
        return []


def stop_all(verbose=True):
    """Unload every resident model so the next load is clean and cold."""
    for m in ps():
        name = m.get("name") or m.get("model")
        subprocess.run(["ollama", "stop", name], capture_output=True, text=True)
    for _ in range(30):
        if not ps():
            return True
        time.sleep(1)
    if verbose:
        print("  ! warning: models still resident after stop_all:",
              [m.get("name") for m in ps()], file=sys.stderr)
    return False


def is_cloud(model):
    return model.startswith("claude") or model.startswith("gpt-5") or model.startswith("gpt-4")


def placement(model):
    """gpu / mixed / cpu / cloud / absent."""
    if is_cloud(model):
        return "cloud"
    for m in ps():
        if (m.get("name") or m.get("model")) == model or \
           (m.get("name") or "").startswith(model):
            size = m.get("size", 0) or 0
            vram = m.get("size_vram", 0) or 0
            if size == 0:
                return "unknown"
            frac = vram / size
            if frac >= 0.99:
                return "gpu"
            if frac <= 0.01:
                return "cpu"
            return f"mixed:{frac:.0%}"
    return "absent"


def chat(model, prompt, num_predict=NUM_PREDICT):
    if is_cloud(model):                       # cloud baseline (Haiku etc.), via the API
        import cloud
        r = cloud.call(prompt, model=model, system=SYSTEM, max_tokens=num_predict)
        return dict(content=r["content"], think=0, done="stop", load_ms=0.0, prompt_ms=0.0,
                    eval_ms=r["sec"] * 1000, prompt_tok=r["in_tok"], eval_tok=r["out_tok"])
    body = {"model": model, "stream": False,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}],
            "options": {"temperature": TEMP, "num_ctx": NUM_CTX,
                        "num_predict": num_predict}}
    if not THINK:
        body["think"] = False
    try:
        o = _post("/api/chat", body, CALL_TIMEOUT)
    except urllib.error.HTTPError:      # model rejects the think param -> retry without
        body.pop("think", None)
        o = _post("/api/chat", body, CALL_TIMEOUT)
    msg = o.get("message", {})
    ns_ms = lambda k: round(o.get(k, 0) / 1e6, 1)          # noqa: E731
    return dict(content=msg.get("content", "") or "",
                think=len(msg.get("thinking", "") or ""),
                done=o.get("done_reason"),
                load_ms=ns_ms("load_duration"),
                prompt_ms=ns_ms("prompt_eval_duration"),
                eval_ms=ns_ms("eval_duration"),
                prompt_tok=o.get("prompt_eval_count", 0),
                eval_tok=o.get("eval_count", 0))


# --- the run ---------------------------------------------------------------

def record(rec):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")


def run_isolated(models, task_list, warm_k):
    rows = []
    for model in models:
        print(f"\n== {model} ==", flush=True)
        stop_all()
        # cold-load cost, measured once (also warms the model for the tasks)
        warm = chat(model, "Reply with the single word: ready", num_predict=32)
        place = placement(model)
        cold_load_ms = warm["load_ms"]
        print(f"  placement={place}  cold-load={cold_load_ms:.0f}ms", flush=True)
        for task in task_list:
            evals, toks, passes, done = [], [], 0, None
            for run in range(warm_k):
                r = chat(model, task["prompt"])
                ok, note = T.grade(task, r["content"])
                passes += 1 if ok else 0
                evals.append(r["eval_ms"]); toks.append(r["eval_tok"]); done = r["done"]
                rec = dict(model=model, task=task["id"], tier=task["tier"], run=run,
                           placement=place, cold_load_ms=cold_load_ms, passed=ok,
                           note=note, eval_ms=r["eval_ms"], eval_tok=r["eval_tok"],
                           prompt_tok=r["prompt_tok"], think_chars=r["think"],
                           done=r["done"], clipped=(r["done"] == "length"))
                record(rec)
            med_ms = statistics.median(evals) if evals else 0
            med_tok = int(statistics.median(toks)) if toks else 0
            rows.append(dict(model=model, task=task["id"], tier=task["tier"],
                             placement=place, cold_load_ms=cold_load_ms,
                             pass_rate=passes / warm_k, med_eval_ms=med_ms,
                             med_tok=med_tok, clipped=(done == "length")))
            flag = "" if passes == warm_k else ("  <-- CLIP" if done == "length" else "  <-- MISS")
            print(f"  {task['id']:16} pass {passes}/{warm_k}  "
                  f"{med_ms/1000:6.1f}s  {med_tok:>5} tok{flag}", flush=True)
    return rows


def run_docpar():
    """Parallel small-model documentation test: three sections at once."""
    SEND = [
        ("llama3.2:3b", "providers"), ("nemotron-3-nano:4b", "commands"),
        ("gemma4:e4b", "config"),
    ]
    facts = {
        "providers": "Format a Markdown '## Providers' table (Type | Requires Key | "
                     "Model) from ONLY these facts: lmstudio no-key local-model; ollama "
                     "no-key local-model; openai key gpt-5; xai key grok-4. Output only "
                     "the section.",
        "commands": "Format a Markdown '## Commands' section from ONLY these facts: "
                    "slash /help /config /tokenuse /provider /model; operators :ai "
                    ":ai@provider :json. Output only the section.",
        "config": "Format a Markdown '## Config' section from ONLY these facts: file "
                  "~/.pyttai/config.json; keys base_url model max_tokens temperature; "
                  "providers dict of name->type/model/api_key. Output only the section.",
    }
    print("== doc parallelism (small models, concurrent) ==", flush=True)
    stop_all()

    def one(item):
        model, key = item
        t = time.time()
        r = chat(model, facts[key], num_predict=1500)
        return dict(model=model, key=key, sec=round(time.time() - t, 1),
                    tok=r["eval_tok"], place=placement(model))

    wall = time.time()
    with ThreadPoolExecutor(max_workers=len(SEND)) as ex:
        res = list(ex.map(one, SEND))
    wall = time.time() - wall
    serial = sum(r["sec"] for r in res)
    for r in res:
        print(f"  {r['model']:20}{r['key']:11}{r['sec']:6.1f}s  {r['tok']:>4} tok  {r['place']}",
              flush=True)
    print(f"  parallel {wall:.1f}s | serial {serial:.1f}s | speedup {serial/wall:.2f}x",
          flush=True)
    record(dict(kind="docpar", wall=round(wall, 1), serial=round(serial, 1),
                speedup=round(serial / wall, 2), sections=res))


def write_summary(rows):
    os.makedirs(OUT, exist_ok=True)
    lines = ["# Local builder benchmark — summary", "",
             f"_{time.strftime('%Y-%m-%d %H:%M')} · num_predict={NUM_PREDICT} · temp=0_", "",
             "| model | placement | cold-load | task | tier | pass | warm s | tok |",
             "|---|---|--:|---|--:|--:|--:|--:|"]
    for r in rows:
        lines.append(f"| {r['model']} | {r['placement']} | {r['cold_load_ms']:.0f}ms | "
                     f"{r['task']} | {r['tier']} | {r['pass_rate']*100:.0f}% | "
                     f"{r['med_eval_ms']/1000:.1f} | {r['med_tok']} |")
    # per-model roll-up
    lines += ["", "## Per model", "",
              "| model | placement | cold-load | overall pass | median warm s |",
              "|---|---|--:|--:|--:|"]
    by = {}
    for r in rows:
        by.setdefault(r["model"], []).append(r)
    for model, rs in by.items():
        pr = sum(x["pass_rate"] for x in rs) / len(rs)
        ms = statistics.median([x["med_eval_ms"] for x in rs]) / 1000
        lines.append(f"| {model} | {rs[0]['placement']} | {rs[0]['cold_load_ms']:.0f}ms | "
                     f"{pr*100:.0f}% | {ms:.1f} |")
    open(os.path.join(OUT, "summary.md"), "w").write("\n".join(lines) + "\n")
    print(f"\nsummary -> {os.path.join(OUT, 'summary.md')}")


def main():
    ap = argparse.ArgumentParser(description="Local-model builder benchmark")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    ap.add_argument("--warm-k", type=int, default=3, help="warm repeats per task")
    ap.add_argument("--docpar", action="store_true", help="run the doc-parallelism test instead")
    ap.add_argument("--temp", type=float, default=TEMP, help="sampling temperature (0 loops some reasoners)")
    ap.add_argument("--think", action="store_true", help="reasoning variant: allow chain-of-thought (default off)")
    args = ap.parse_args()
    globals()["TEMP"] = args.temp
    globals()["THINK"] = args.think

    if args.docpar:
        run_docpar()
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    task_list = T.TASKS
    if args.tasks:
        want = {t.strip() for t in args.tasks.split(",")}
        task_list = [t for t in T.TASKS if t["id"] in want]
    print(f"models: {models}\ntasks: {[t['id'] for t in task_list]}  warm_k={args.warm_k}")
    rows = run_isolated(models, task_list, args.warm_k)
    write_summary(rows)


if __name__ == "__main__":
    main()
