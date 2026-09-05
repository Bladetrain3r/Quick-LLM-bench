"""
Grader for a report ABOUT the local-bench codebase — the crux of the E2E
benchmark (E2E_PLAN.md). Grading a report is fuzzy where code is not, so this
keeps it mechanical wherever possible against local-bench's KNOWN parts, and
leaves prose quality as the one openly-subjective score (not computed here).

    python3 report_grade.py <report.md>       # grade a report file
    python3 report_grade.py --self-check      # sanity: README should score well

Each dimension is a fraction in [0,1] plus a list of what's missing/wrong:
  coverage   — the components a report on this codebase should name
  facts      — its distinctive true facts (the two controls, etc.)
  sections   — the report has the expected structural parts
  clean      — none of a fixed set of tempting-but-FALSE claims appears
AUDIT_CHECKLIST is exported for grading stage 4's audit verdicts (claim -> truth).
"""
import sys

# component -> synonyms; covered if ANY synonym appears (case-insensitive)
COMPONENTS = {
    "bench.py (isolated harness)":      ["bench.py"],
    "tasks.py (task suite)":            ["tasks.py"],
    "bench_project.py (project bench)": ["bench_project"],
    "minesweeper multi-file task":      ["minesweeper"],
    "acceptance suite":                 ["suite.py", "acceptance suite", "test suite"],
    "ollama runtime":                   ["ollama"],
    "audit task type":                  ["audit"],
    "the contract / model.py":          ["contract", "model.py"],
}

FACTS = {
    "placement / VRAM control":  ["placement", "vram", "spill", "/api/ps"],
    "cold vs warm timing":       ["cold-load", "cold load", "cold/warm", "cold and warm", "load_duration"],
    "answer-mode / think off":   ["answer-mode", "answer mode", "think:false", "think false", "chain-of-thought off"],
    "grades by executing code":  ["execut", "run the function", "exec "],
    "tiered / graded tasks":     ["tier", "graded", "pass rate", "pass/fail"],
}

SECTIONS = {
    "overview":     ["overview", "what it is", "what is", "introduction", "purpose"],
    "components":   ["component", "module", "parts", "structure", "layout"],
    "how it works": ["how it works", "method", "control", "measure", "harness"],
    "results/use":  ["result", "finding", "run it", "usage", "how to run", "output"],
    "limitations":  ["limitation", "caveat", "not proven", "does not", "roadmap", "future"],
}

# tempting-but-FALSE claims for local-bench; none should appear
FORBIDDEN = ["pytest", "gpu cluster", "web interface", "web ui",
             "written in rust", "kubernetes", "postgres", "database"]

# claim -> ground-truth verdict, for grading the audit stage
AUDIT_CHECKLIST = [
    ("The harness verifies whether a model runs on GPU or spills to CPU", True),
    ("It separates cold model-load time from warm generation time", True),
    ("Coding tasks are graded by executing the generated code", True),
    ("It includes a multi-file project task (minesweeper)", True),
    ("It includes an audit task type graded against known verdicts", True),
    ("Small models can be run in parallel for documentation", True),
    ("The default sampling temperature is 0", False),
    ("Cloud API keys are stored in the repository", False),
    ("The acceptance suite is built on the pytest framework", False),
    ("It requires a GPU to run", False),
]


def _frac(groups, text):
    t = text.lower()
    hits = {name: any(s.lower() in t for s in syns) for name, syns in groups.items()}
    missing = [n for n, ok in hits.items() if not ok]
    return (sum(hits.values()) / len(groups) if groups else 1.0), missing


def grade_report(text):
    cov, cov_miss = _frac(COMPONENTS, text)
    fac, fac_miss = _frac(FACTS, text)
    sec, sec_miss = _frac(SECTIONS, text)
    tl = text.lower()
    forbidden_hits = [f for f in FORBIDDEN if f in tl]
    clean = 1.0 if not forbidden_hits else 0.0
    overall = round(0.35 * cov + 0.30 * fac + 0.20 * sec + 0.15 * clean, 3)
    return dict(coverage=round(cov, 3), coverage_missing=cov_miss,
                facts=round(fac, 3), facts_missing=fac_miss,
                sections=round(sec, 3), sections_missing=sec_miss,
                clean=clean, forbidden_hits=forbidden_hits, overall=overall)


def _print(label, g):
    print(f"== {label} ==")
    print(f"  coverage {g['coverage']:.0%}  facts {g['facts']:.0%}  "
          f"sections {g['sections']:.0%}  clean {'yes' if g['clean'] else 'NO '+str(g['forbidden_hits'])}")
    print(f"  overall  {g['overall']:.0%}")
    for k in ("coverage_missing", "facts_missing", "sections_missing"):
        if g[k]:
            print(f"  {k}: {g[k]}")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        text = "".join(open(os.path.join(here, f)).read() for f in ("README.md",))
        g = grade_report(text)
        _print("README self-check", g)
        print("\n(a real doc should score high on coverage/facts and stay clean;"
              " sections may lag since a README isn't a report)")
    elif len(sys.argv) > 1:
        _print(sys.argv[1], grade_report(open(sys.argv[1]).read()))
    else:
        print(__doc__)
