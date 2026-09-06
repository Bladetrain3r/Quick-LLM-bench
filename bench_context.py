#!/usr/bin/env python3
"""
Context-vs-size suite — a KIT, not a leaderboard. Point it at your own ollama.

Phase 0 (--phase 0, default): kv-cache calibration. How each model's footprint
grows with num_ctx → kv cost per token (slope) vs weights+overhead (intercept),
capped by the model's trained max (/api/show). Gives fits(budget): the largest
context a model can actually hold at N GB.

Phase 1 (--phase 1): does the context actually WORK, and how fast? A deterministic
needle-retrieval task up a context ladder (needle placed at several depths in
filler), GPU-fit only (ladder bounded by Phase 0's fits(16GB)). Measures retrieval
pass-rate + prompt-eval tok/s (the cost of ingesting long context) + generation
tok/s. Answers "can I rely on long context / a steady multi-turn load?"

    python3 bench_context.py                                   # phase 0, auto-discover
    python3 bench_context.py --phase 1 --models gpt-oss:20b,gemma4:12b,qwen-3-8-27:latest
    python3 bench_context.py --phase 1 --ladder 2048,8192,16384,32768,65536

kv quant = q8_0 (set in ollama's systemd unit; the f16 default ~doubles kv). One model resident at a time.
"""
import argparse, json, os, random, re, subprocess, time, urllib.request

HOST = "http://localhost:11434"
GB = 1e9
SKIP = ("embed", "minilm")
LINEAR_R2 = 0.90


def _get(path):
    with urllib.request.urlopen(HOST + path, timeout=15) as r:
        return json.load(r)


def _post(path, body, timeout=600):
    req = urllib.request.Request(HOST + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def discover():
    return [m["name"] for m in _get("/api/tags").get("models", [])
            if not any(s in m["name"].lower() for s in SKIP)]


def resident():
    try:
        return [m.get("name") or m.get("model") for m in _get("/api/ps").get("models", []) if m]
    except Exception:  # noqa: BLE001
        return []


def clean_gpu(wait=30):
    for n in resident():
        subprocess.run(["ollama", "stop", n], capture_output=True, text=True)
    for _ in range(wait):
        if not resident():
            return
        time.sleep(1)


def placement():
    for m in _get("/api/ps").get("models", []):
        size, vram = m.get("size", 0), m.get("size_vram", 0)
        if not size:
            continue
        frac = vram / size
        return "gpu" if frac >= 0.99 else ("cpu" if frac <= 0.01 else f"mixed:{frac:.0%}")
    return "absent"


def model_max_ctx(model):
    try:
        for k, v in _post("/api/show", {"model": model}).get("model_info", {}).items():
            if k.endswith(".context_length"):
                return int(v)
    except Exception:  # noqa: BLE001
        pass
    return None


# ---- Phase 0: calibration -------------------------------------------------

def load_at(model, ctx):
    _post("/api/generate", {"model": model, "prompt": "hi", "stream": False,
                            "options": {"num_ctx": ctx, "num_predict": 1}})
    for m in _get("/api/ps").get("models", []):
        if (m.get("name") or m.get("model")) == model or (m.get("name") or "").startswith(model):
            return m.get("size", 0), m.get("size_vram", 0)
    return 0, 0


def linfit(xs, ys):
    n = len(xs); sx = sum(xs); sy = sum(ys)
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    denom = (n * sxx - sx * sx) or 1e-12
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    ybar = sy / n
    ss_tot = sum((y - ybar) ** 2 for y in ys) or 1e-12
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return slope, intercept, 1 - ss_res / ss_tot


def regime(kv_mb, r2):
    if r2 < LINEAR_R2:
        return "swa-plateau"
    if kv_mb < 5:
        return "cheap-kv"
    if kv_mb > 20:
        return "expensive-kv"
    return "moderate-kv"


def calibrate(models, ctxs, budgets):
    out = {}
    for model in models:
        print(f"\n== {model} ==", flush=True)
        mmax = model_max_ctx(model); pts = []
        for ctx in ctxs:
            if mmax and ctx > mmax:
                continue
            clean_gpu()
            try:
                t = time.time(); size, vram = load_at(model, ctx)
                if not size:
                    continue
                frac = vram / size
                place = "gpu" if frac >= 0.99 else ("cpu" if frac <= 0.01 else f"mixed:{frac:.0%}")
                pts.append((ctx, size))
                print(f"  ctx {ctx:>6}  size {size/GB:6.2f}GB  vram {vram/GB:6.2f}GB  {place:9} ({time.time()-t:.0f}s)", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  ctx {ctx:>6}  ERROR {str(e)[:70]}", flush=True)
        if len(pts) < 2:
            out[model] = dict(error="insufficient points", max_ctx=mmax); continue
        xs = [c for c, _ in pts]; ys = [s for _, s in pts]
        slope, intercept, r2 = linfit(xs, ys)
        kv_mb = max(0.0, slope * 1000 / 1e6); weights = intercept / GB; reg = regime(kv_mb, r2)
        maxsize = max(ys)
        rec = dict(kv_mb_per_1k=round(kv_mb, 2), weights_gb=round(weights, 2), r2=round(r2, 3),
                   regime=reg, model_max_ctx=mmax, fits={})
        for b in budgets:
            if reg == "swa-plateau":
                rec["fits"][b] = (mmax or 0) if maxsize <= b * GB else 0
            elif slope > 0:
                mf = int((b * GB - intercept) / slope)
                rec["fits"][b] = max(0, min(mf, mmax) if mmax else mf)
            else:
                rec["fits"][b] = mmax or 0
        out[model] = rec
        fitstr = "  ".join(f"{b}GB->{rec['fits'][b]:,}" for b in budgets)
        print(f"  => {reg} · kv {kv_mb:.1f} MB/1k · weights {weights:.2f}GB · R2 {r2:.2f} · max {mmax} · fits {fitstr}", flush=True)
    os.makedirs("results/context_vs_size", exist_ok=True)
    json.dump(out, open("results/context_vs_size/phase0_calibration.json", "w"), indent=1)
    return out


# ---- Phase 1: does the context work, and how fast? ------------------------

FILLER = "Log line {i:05d}: subsystem nominal, telemetry within range, no operator action required."


def make_prompt(target_tokens, depth, uid, code):
    needle = f"IMPORTANT MEMO: the passphrase for vault {uid} is {code}. Retain this exactly."
    lines, i = [], 0
    while len(("\n".join(lines))) // 4 < target_tokens:   # ~4 chars/token estimate
        lines.append(FILLER.format(i=i)); i += 1
    pos = max(0, min(len(lines), int(len(lines) * depth)))
    lines.insert(pos, needle)
    q = (f"\n\nQuestion: what is the passphrase for vault {uid}? "
         f"Reply with ONLY the numeric code, nothing else.")
    return "\n".join(lines) + q


def _tps(count, dur_ns):
    return round(count / (dur_ns / 1e9), 1) if dur_ns else 0.0


def phase1(models, ladder, depths):
    def _load(path):
        try:
            return json.load(open(path))
        except Exception:  # noqa: BLE001
            return {}
    cal = _load("results/context_vs_size/phase0_calibration.json")
    warm = _load("results/context_vs_size/warmup_preflight.json")

    def cap_for(model):
        # prefer the warmup-confirmed usable context; else phase-0 fits(16); else model max
        u = (warm.get(model) or {}).get("usable_ctx") or 0
        f16 = (cal.get(model) or {}).get("fits", {}).get("16", 0)
        f16 = f16 if isinstance(f16, int) else 0
        return min(u or f16 or 10**9, model_max_ctx(model) or 10**9)
    rows = []
    for model in models:
        clean_gpu()
        cap = cap_for(model)
        print(f"\n== {model} (GPU-fit context cap ~{cap:,}) ==", flush=True)
        for target in ladder:
            if target > cap:
                continue
            passes, ptps, gtps, ptoks = 0, [], [], []
            for depth in depths:
                uid = str(random.randint(1000, 9999)); code = str(random.randint(100000, 999999))
                body = {"model": model, "prompt": make_prompt(target, depth, uid, code),
                        "system": "You are precise. Reply with only what is asked.",
                        "stream": False, "think": False,
                        "options": {"num_ctx": target + 1024, "num_predict": 256, "temperature": 0}}
                try:
                    r = _post("/api/generate", body, timeout=900)
                except Exception as e:  # noqa: BLE001
                    print(f"  ~{target:>6} d{depth:.1f} ERROR {str(e)[:50]}", flush=True); continue
                ok = _extract_code(r.get("response", "")) == code
                passes += 1 if ok else 0
                ptoks.append(r.get("prompt_eval_count", 0))
                ptps.append(_tps(r.get("prompt_eval_count", 0), r.get("prompt_eval_duration", 0)))
                gtps.append(_tps(r.get("eval_count", 0), r.get("eval_duration", 0)))
            n = len(depths)
            pe = int(sum(ptoks) / len(ptoks)) if ptoks else 0
            pt = round(sum(ptps) / len(ptps), 1) if ptps else 0
            gt = round(sum(gtps) / len(gtps), 1) if gtps else 0
            place = placement()
            rows.append(dict(model=model, target=target, prompt_tok=pe, retrieval=f"{passes}/{n}",
                             prompt_tps=pt, gen_tps=gt, placement=place))
            print(f"  ctx~{target:>6}  {pe:>6} tok  retrieval {passes}/{n}  "
                  f"prompt {pt:>6.0f} tok/s  gen {gt:>5.1f} tok/s  {place}", flush=True)
    os.makedirs("results/context_vs_size", exist_ok=True)
    json.dump(rows, open("results/context_vs_size/phase1_needle.json", "w"), indent=1)
    return rows


# ---- warmup: preflight each model's real usable context + grader health ---

def _extract_code(resp):
    m = re.search(r"\d{6}", resp or "")
    return m.group(0) if m else None


def warmup(models, ladder):
    """Before a benchmark, find each model's ACTUAL usable context (does it silently
    truncate?) and whether the grader can read its answer at load (does the model
    wrap/clip?). Needle at the START (depth 0.05) so truncation shows as both a
    dropped prompt_eval_count and a miss; grader is the hardened 6-digit extractor."""
    try:
        cal = json.load(open("results/context_vs_size/phase0_calibration.json"))
    except Exception:  # noqa: BLE001
        cal = {}
    out = {}
    for model in models:
        clean_gpu()
        mmax = model_max_ctx(model) or 10**9
        f24 = cal.get(model, {}).get("fits", {}).get("24", 0)
        cap = min(mmax, f24 if isinstance(f24, int) and f24 > 0 else mmax)
        print(f"\n== {model} (cap ~{cap:,}) ==", flush=True)
        usable, usable_tok, first_trunc, grader_fail = 0, 0, None, False
        prev_pe, prev_target = None, None
        for target in ladder:
            if target > cap:
                break
            uid = str(random.randint(1000, 9999)); code = str(random.randint(100000, 999999))
            body = {"model": model, "prompt": make_prompt(target, 0.05, uid, code),
                    "system": "You are precise. Reply with only what is asked.",
                    "stream": False, "think": False,
                    "options": {"num_ctx": target + 1024, "num_predict": 256, "temperature": 0}}
            try:
                r = _post("/api/generate", body, timeout=900)
            except Exception as e:  # noqa: BLE001
                print(f"  ~{target:>7} ERROR {str(e)[:50]}", flush=True); break
            pe = r.get("prompt_eval_count", 0)
            # truncation is tokenizer-independent: when target rises but the ingested
            # count fails to rise with it, the input is being clipped. First rung is
            # assumed full (no prior to compare).
            if prev_pe is None:
                trunc = False
            else:
                want = target / prev_target          # how much bigger we asked for
                got = pe / prev_pe if prev_pe else 0  # how much more was ingested
                trunc = got < 0.6 * want
            ok = _extract_code(r.get("response", "")) == code
            print(f"  ~{target:>7}  prompt {pe:>7} tok  {'TRUNCATED' if trunc else 'full':9}  "
                  f"grader {'ok' if ok else 'MISS'}", flush=True)
            if trunc:
                first_trunc = target; break
            usable, usable_tok = target, pe
            prev_pe, prev_target = pe, target
            if not ok:
                grader_fail = True
        note = []
        if first_trunc:
            note.append(f"truncates ~{first_trunc:,}; usable ~{usable:,} ({usable_tok:,} tok confirmed)")
        if grader_fail:
            note.append("grader unreliable on full context (model wraps/clips its answer?)")
        out[model] = dict(usable_ctx=usable, usable_tokens=usable_tok, first_truncated_at=first_trunc,
                          grader_ok=not grader_fail, note="; ".join(note) or "clean")
        print(f"  => usable ~{usable:,} · grader {'ok' if not grader_fail else 'CHECK'} · {out[model]['note']}", flush=True)
    os.makedirs("results/context_vs_size", exist_ok=True)
    json.dump(out, open("results/context_vs_size/warmup_preflight.json", "w"), indent=1)
    return out


# ---- reporting (phase 0) --------------------------------------------------

def write_report0(res, budgets, path):
    hdr = ["# Phase 0 — kv-cache calibration (this environment)", "",
           "**weights** = fixed model cost; **kv/1k** = memory each 1,000 tokens of context adds;",
           "**regime** = whether context is nearly free or competes with weights; **fits(budget)** =",
           "largest context that fits at N GB (capped at trained max). A map, not a ranking.", "",
           "| model | regime | weights GB | kv MB/1k | model max | " + " | ".join(f"fits {b}GB" for b in budgets) + " |",
           "|---|---|---|---|---|" + "|".join("---" for _ in budgets) + "|"]
    order = {"expensive-kv": 0, "moderate-kv": 1, "cheap-kv": 2, "swa-plateau": 3}
    for m, r in sorted(res.items(), key=lambda kv: order.get(kv[1].get("regime"), 9)):
        if r.get("error"):
            continue
        fits = " | ".join(f"{r['fits'][b]:,}" for b in budgets)
        hdr.append(f"| {m} | {r['regime']} | {r['weights_gb']} | {r['kv_mb_per_1k']} | {r.get('model_max_ctx')} | {fits} |")
    open(path, "w").write("\n".join(hdr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="0")
    ap.add_argument("--models", default="")
    ap.add_argument("--budgets", default="16,24")
    ap.add_argument("--ctxs", default="2048,8192,16384,32768")
    ap.add_argument("--ladder", default="2048,8192,16384,32768,65536")
    ap.add_argument("--depths", default="0.1,0.5,0.9")
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.phase == "0":
        models = models or discover()
        budgets = [int(b) for b in args.budgets.split(",")]
        ctxs = [int(c) for c in args.ctxs.split(",")]
        print(f"phase 0 · models ({len(models)}) · budgets {budgets}GB · ctxs {ctxs}")
        res = calibrate(models, ctxs, budgets)
        write_report0(res, budgets, "results/context_vs_size/phase0_report.md")
        print("\nsaved -> results/context_vs_size/phase0_{calibration.json,report.md}")
    elif args.phase == "1":
        if not models:
            print("phase 1 needs --models (GPU-fit ones from phase 0)"); return
        ladder = [int(c) for c in args.ladder.split(",")]
        depths = [float(d) for d in args.depths.split(",")]
        print(f"phase 1 · needle retrieval + speed · models {models} · ladder {ladder} · depths {depths}")
        phase1(models, ladder, depths)
        print("\nsaved -> results/context_vs_size/phase1_needle.json")
    elif args.phase == "warmup":
        models = models or discover()
        ladder = [int(c) for c in args.ladder.split(",")]
        print(f"warmup preflight · usable-context + grader health · models ({len(models)}) · ladder {ladder}")
        warmup(models, ladder)
        print("\nsaved -> results/context_vs_size/warmup_preflight.json")


if __name__ == "__main__":
    main()
