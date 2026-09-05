# local-bench

## Overview

- **local-bench** is a benchmark framework for evaluating local models as verified builders.  
- **bench.py** implements the core benchmark logic, providing utilities for HTTP requests, process control, placement, chat, recording, isolated runs, and summary generation.  
- **tasks.py** defines a suite of tasks (dedupe, parse key‑value, classify, heat, tail, provenance, fold edges, merge) along with helper functions for verdict parsing, grading, and fence stripping.  
- **bench_project.py** benchmarks a multi‑file project (the minesweeper task) with functions for prompt handling, file extraction, evaluation, recording, and running split or single‑file tests.  
- **report_grade.py** offers a mechanical grading routine for reports about the codebase, using a fractional scoring helper and a print utility.  
- **minesweeper/** contains the shared data model (`Board`, `in_bounds`, `neighbors`), a contract file (`CONTRACT.md`) specifying the required signatures for independently written modules, and an acceptance suite (`suite.py`) that runs logic, render, and UI modules against the model.

## Components

- **bench.py** – core benchmark logic for local‑model builders, providing request helpers, placement, chat, recording, and execution utilities.  
- **tasks.py** – suite of task functions (dedupe, parse_kv, classify, heat, tail, provenance, fold_edges, merge) plus grading helpers.  
- **bench_project.py** – multi‑file project benchmark for the minesweeper task, handling prompt splitting, file extraction, evaluation, and reporting.  
- **report_grade.py** – mechanical grader for a report about the codebase, with helper functions for scoring and printing.  
- **README.md** – project overview.  
- **minesweeper/model.py** – shared data model (Board, in_bounds, neighbors) used by all minesweeper modules.  
- **minesweeper/CONTRACT.md** – contract specification for the minesweeper implementation modules.  
- **minesweeper/suite.py** – acceptance suite that runs candidate logic.py, render.py, ui.py against the shared model.

## How it works  
The benchmark is driven by **bench.py**, which implements helper functions (_get, _post, ps, stop_all, is_cloud, placement, chat, record, run_isolated, run_docpar, write_summary, main) to orchestrate local‑model building and evaluation. **tasks.py** supplies a suite of test functions (c_dedupe, c_parse_kv, c_classify, c_heat, c_tail, c_provenance, c_fold_edges, c_merge, parse_verdicts, grade_audit, strip_fences, grade) that are executed against the benchmarked models. For the minesweeper task, **bench_project.py** splits prompts, extracts files, evaluates results, records metrics, and runs the project either as a single file or split across modules. Grading of a written report is handled by **report_grade.py**, which uses deterministic scoring functions (_frac, grade_report, _print) to evaluate the report against the known contract. The shared contract for the minesweeper clone lives in **minesweeper/model.py**, defining the Board class and helper functions (in_bounds, neighbors). The acceptance suite (**minesweeper/suite.py**) runs candidate implementations (logic.py, render.py, ui.py) against this contract, providing fresh boards and multiple difficulty levels for testing. The README documents the overall purpose of the local‑bench codebase.

## Usage and results

- Run `bench.py` to benchmark local-model builders. The `main` function executes the defined tasks and writes a summary via `write_summary`.
- Run `bench_project.py` to benchmark the minesweeper task. The `main` function splits prompts, runs single or split runs, and records results.
- Use `report_grade.py` to grade a report about the local‑bench codebase. The `grade_report` function computes a fractional score and prints it.
- The minesweeper acceptance suite (`minesweeper/suite.py`) can be executed against a project directory containing `model.py`, `logic.py`, `render.py`, and `ui.py`. It runs levels 1–3 and reports success or failure.

## Limitations
- Only local models are supported; cloud execution is merely detected but not utilized.
- The task suite is fixed in `tasks.py`; adding new benchmarks would require code changes.
- The implementation relies exclusively on the Python standard library; no external dependencies are used.
- The Minesweeper task is constrained by a rigid contract (`minesweeper/CONTRACT.md`); alternative designs are not possible.
- Grading is mechanical and acknowledges fuzziness, so subtle quality differences may be missed.
- The benchmark focuses on a single project (Minesweeper); it does not demonstrate broader applicability.