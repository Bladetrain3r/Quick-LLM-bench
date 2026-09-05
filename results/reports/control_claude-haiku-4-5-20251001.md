# local-bench Documentation Report

## Overview

local-bench is a benchmark suite for evaluating local models as verified builders. It measures model performance across multiple task categories through isolated execution, docstring parsing, and multi-file project completion. The benchmark emphasizes mechanical grading against known baselines to ensure reproducibility.

## Components

The codebase consists of five primary modules:

**bench.py** implements the core benchmarking framework with functions for HTTP communication (_get, _post), process management (ps, stop_all, placement), model interaction (chat), execution isolation (run_isolated, run_docpar), and result aggregation (record, write_summary, main).

**tasks.py** defines a task suite including computational tasks (c_dedupe, c_parse_kv, c_classify, c_heat, c_tail, c_provenance, c_fold_edges, c_merge) with grading functions (parse_verdicts, grade_audit, strip_fences, grade) that evaluate model outputs against expected results.

**bench_project.py** implements a multi-file project benchmark centered on the minesweeper task, providing functions for prompt splitting (split_prompt), file extraction (extract_files), and dual execution modes (run_single, run_split) alongside evaluation and recording mechanisms.

**report_grade.py** provides mechanical grading for reports about the local-bench codebase itself, implementing fuzzy matching against known baselines through _frac, grade_report, and _print functions.

**minesweeper/** is a module-based task architecture. The **model.py** file contains shared data structures (Board class, in_bounds, neighbors functions) that serve as a fixed contract. **CONTRACT.md** specifies module boundaries for logic.py, render.py, and ui.py. **suite.py** contains acceptance tests (level1, level2, level3, run) that validate independently-written modules.

## How it works

The benchmark operates through isolated execution environments managed by bench.py. Tasks are defined in tasks.py with deterministic inputs and expected outputs. The chat function communicates with local models, receiving code or solutions that are then graded through mechanical comparison.

For the minesweeper task specifically, bench_project.py orchestrates multi-file projects where candidates implement separate modules against a fixed contract. The shared model.py enables composition of independently-written components. suite.py runs acceptance tests across three difficulty levels to verify correctness.

Grading uses exact matching where possible (strip_fences, parse_verdicts) and fuzzy matching only for report evaluation (report_grade.py). Results flow through record functions and culminate in write_summary for aggregated output.

## Usage and results

Execution begins via main() in either bench.py or bench_project.py. The benchmark can run in isolated mode (run_isolated) or through docstring parsing (run_docpar). For minesweeper, run_split orchestrates multi-module evaluation while run_single tests individual components.

Results are recorded incrementally and summarized mechanically. The E2E_PLAN.md references report_grade.py as the crux of end-to-end testing, grading model-generated reports against known baselines. Task grading in grade() compares model outputs to expected verdicts using strip_fences and parse_verdicts for normalization.

## Limitations

The grading system relies on exact string matching for code tasks, which may fail on semantically equivalent but syntactically different outputs. Fuzzy matching is limited to report grading (report_grade.py), not code evaluation.

The minesweeper task enforces a fixed contract model that candidates cannot modify, potentially constraining creative solutions but ensuring composability. All tasks assume stdlib-only implementations with no external dependencies.

Process management (ps, stop_all, placement) abstracts away environment details, reducing visibility into actual model execution contexts. The benchmark does not provide detailed performance profiling or latency metrics—only pass/fail verdict aggregation through write_summary.