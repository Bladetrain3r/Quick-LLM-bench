"""
Task suite for the local-model builder benchmark.

Each task is a bounded, spec-plus-test unit shaped like real delegate work
(most of these echo actual code written during the Village/PyTTAI sessions).
A task carries an exact function spec in its prompt and a deterministic
`check(fn)` that returns True only if the generated function is correct.

Grading is mechanical: extract the code, exec it, pull out the named function,
run check(). Any exception during exec/check counts as a fail.
"""
import hashlib
import re


# --- acceptance tests (pure, deterministic) --------------------------------

def c_dedupe(fn):
    return (fn([3, 1, 3, 2, 1, 2]) == [3, 1, 2]
            and fn([]) == []
            and fn(["a", "a", "b", "a"]) == ["a", "b"])


def c_parse_kv(fn):
    return (fn("a=1\n# comment\n\nb = 2\na=3") == {"a": "3", "b": "2"}
            and fn("") == {}
            and fn("  x = y \n") == {"x": "y"})


def c_classify(fn):
    d = {"Commons", "Arrivals"}
    return (fn("abc1234567", d) == "ticket"
            and fn("be5f6eee5838ee47801b491724520123cf98d0d9", d) == "ticket"
            and fn("Commons", d) == "designated"
            and fn("Backroom", d) == "undesignated")


def c_heat(fn):
    import math
    return (abs(fn(0.0, 7 * 86400.0) - 50.0) < 1e-6
            and abs(fn(1000.0, 1000.0) - 100.0) < 1e-6
            and abs(fn(0.0, 14 * 86400.0) - 25.0) < 1e-6)


def c_tail(fn):
    # intent-faithful: accept list or tuple for `kept`, any truthy/falsy for the flag
    def ok(res, kept, trunc):
        try:
            k, t = res
        except Exception:  # noqa: BLE001
            return False
        return list(k) == kept and bool(t) == trunc
    return (ok(fn([1, 2, 3, 4], 2), [3, 4], True)
            and ok(fn([1], 3), [1], False)
            and ok(fn([1, 2, 3], 3), [1, 2, 3], False))


def c_provenance(fn):
    body = "the page body\nwith two lines"
    h = fn("Notes", 4, "2026-09-01", "2026-09-05", 10, 42, body)
    want = hashlib.sha256(body.encode()).hexdigest()
    return (h["page"] == "Notes" and h["blocks"] == 4
            and h["first"] == "2026-09-01" and h["last"] == "2026-09-05"
            and list(h["seq_range"]) == [10, 42]
            and h["sha256"] == want)


def c_fold_edges(fn):
    full = "be5f6eee5838ee47801b491724520123cf98d0d9"
    rows = [("a", full[:10]), ("a", full), ("b", full), ("c", "Commons")]
    got = fn(rows)
    return (got == {full[:10]: {"a": 2, "b": 1}, "Commons": {"c": 1}})


def c_merge(fn):
    return (fn({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {"a": 1, "b": 3, "c": 4}
            and fn({"a": 1, "b": 2}, {"a": None}) == {"b": 2}
            and fn({}, {}) == {})


# --- audit tasks: read an artifact, verdict each checklist item -------------
# A DESIRED property per item; PASS if it holds in the artifact, FAIL if not.
# The artifact and the ground-truth verdicts are fixed, so grading is exact.

AUDIT_CONFIG = (
    "Audit this config against the checklist. Config:\n"
    "providers:\n"
    "  gemma:  type=ollama  model=gemma4:12b\n"
    "  gpt:    type=openai  api_key=sk-secret123\n"
    "  broken: model=foo\n"
    "Checklist (each is a DESIRED property; PASS if it holds, FAIL if not):\n"
    "1. Every provider entry has a 'type'.\n"
    "2. No provider stores an api_key in the config file.\n"
    "3. There is at least one provider.\n"
    "Output EXACTLY three lines and nothing else, e.g. `1: PASS` then `2: FAIL` then `3: PASS`."
)

AUDIT_CODE = (
    "Audit this Python function against the checklist. Code:\n"
    "def load(path):\n"
    "    try:\n"
    "        return open(path).read()\n"
    "    except:\n"
    "        return None\n"
    "Checklist (each is a DESIRED property; PASS if it holds, FAIL if not):\n"
    "1. The function has a return statement.\n"
    "2. The function avoids a bare `except:` (it names an exception type).\n"
    "3. The function's parameters have type annotations.\n"
    "Output EXACTLY three lines and nothing else, e.g. `1: PASS` then `2: FAIL` then `3: FAIL`."
)


# --- the suite -------------------------------------------------------------

TASKS = [
    dict(id="t1_dedupe", tier=1, func="dedupe_preserve_order", check=c_dedupe,
         prompt="Write ONLY a Python function `dedupe_preserve_order(items)` that "
                "returns a new list with duplicate elements removed and the original "
                "order of first appearance preserved. Stdlib only. Output only the "
                "function source, no markdown fences, no prose."),

    dict(id="t1_parse_kv", tier=1, func="parse_kv", check=c_parse_kv,
         prompt="Write ONLY a Python function `parse_kv(text)` that parses lines of "
                "the form `key=value`: ignore blank lines and lines starting with `#`, "
                "strip whitespace around key and value, and let later keys override "
                "earlier ones. Return a dict. Stdlib only. Output only the function "
                "source, no markdown fences, no prose."),

    dict(id="t2_classify", tier=2, func="classify", check=c_classify,
         prompt="Write ONLY a Python function `classify(target, designated)`. "
                "`designated` is a set of strings. Return the string 'ticket' if "
                "target matches the regex ^[0-9a-f]{10,40}$ ; else 'designated' if "
                "target is in the `designated` set ; else 'undesignated'. Stdlib only. "
                "Output only the function source, no markdown fences, no prose."),

    dict(id="t2_heat", tier=2, func="heat", check=c_heat,
         prompt="Write ONLY a Python function `heat(ts, now, half_life_days=7)` that "
                "returns an exponential decay: 100 * 0.5 ** ((now - ts) / 86400 / "
                "half_life_days). ts and now are UNIX seconds (floats). Stdlib only. "
                "Output only the function source, no markdown fences, no prose."),

    dict(id="t2_tail", tier=2, func="tail", check=c_tail,
         prompt="Write ONLY a Python function `tail(items, k)` that returns a tuple "
                "`(kept, truncated)`: `kept` is the last k items of the list `items` "
                "(or all of them if there are k or fewer), and `truncated` is True iff "
                "some items were dropped. Stdlib only. Output only the function "
                "source, no markdown fences, no prose."),

    dict(id="t3_provenance", tier=3, func="build_header", check=c_provenance,
         prompt="Write ONLY a Python function "
                "`build_header(page, blocks, first, last, seq_lo, seq_hi, body)` that "
                "returns a provenance-header dict with exactly these keys: 'page' "
                "(=page), 'blocks' (=blocks), 'first' (=first), 'last' (=last), "
                "'seq_range' (=[seq_lo, seq_hi]), and 'sha256' (= the hex sha256 of "
                "body encoded as utf-8). Use hashlib. Output only the function source, "
                "no markdown fences, no prose."),

    dict(id="t3_fold_edges", tier=3, func="fold_edges", check=c_fold_edges,
         prompt="Write ONLY a Python function `fold_edges(rows)`. `rows` is a list of "
                "(actor, target) tuples. Build a dict mapping surface -> {actor: count}. "
                "A surface is the target, EXCEPT that a target matching the regex "
                "^[0-9a-f]{10,40}$ is folded to its first 10 characters (so a ticket's "
                "short id and full hash count as one surface). Count how many times each "
                "actor wrote to each surface. Stdlib only. Output only the function "
                "source, no markdown fences, no prose."),

    dict(id="t3_merge", tier=3, func="merge", check=c_merge,
         prompt="Write ONLY a Python function `merge(existing, updates)` that returns a "
                "NEW dict: start from a copy of `existing`, apply `updates` so later "
                "values override, EXCEPT that any key whose value in `updates` is None "
                "is removed from the result (delete semantics). Do not mutate the "
                "inputs. Stdlib only. Output only the function source, no markdown "
                "fences, no prose."),

    dict(id="a2_audit_config", tier=2, kind="audit", prompt=AUDIT_CONFIG,
         expected={1: "FAIL", 2: "FAIL", 3: "PASS"}),

    dict(id="a2_audit_code", tier=2, kind="audit", prompt=AUDIT_CODE,
         expected={1: "PASS", 2: "FAIL", 3: "FAIL"}),
]


# --- grading ---------------------------------------------------------------

def parse_verdicts(text):
    out = {}
    for n, v in re.findall(r"(\d+)\s*[:.\-\)]\s*(PASS|FAIL)", text or "", re.I):
        out.setdefault(int(n), v.upper())   # first verdict per item wins
    return out


def grade_audit(task, content):
    got = parse_verdicts(content)
    if not got:
        return False, "no-verdicts"
    for k, v in task["expected"].items():
        if got.get(k) != v:
            return False, f"item{k}={got.get(k)}"
    return True, "ok"

def strip_fences(text):
    t = (text or "").strip()
    # robust: pull the first ```lang\n ... ``` block if present (handles a leading
    # blank line, a language tag, or prose around the fence — as cloud models emit)
    m = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", t, re.S)
    if m:
        return m.group(1).strip()
    lines = t.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def grade(task, content):
    """Return (passed: bool, note: str). Never raises. Dispatches on kind."""
    if task.get("kind") == "audit":
        return grade_audit(task, content)
    code = strip_fences(content or "")
    if not code:
        return False, "empty"
    ns = {}
    try:
        exec(code, ns)
    except Exception as e:  # noqa: BLE001
        return False, f"exec:{type(e).__name__}"
    fn = ns.get(task["func"])
    if not callable(fn):
        return False, "no-func"
    try:
        return (True, "ok") if task["check"](fn) else (False, "wrong")
    except Exception as e:  # noqa: BLE001
        return False, f"check:{type(e).__name__}"
