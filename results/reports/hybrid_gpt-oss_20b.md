# local-bench

## Overview

local-bench is a benchmark for evaluating local language models as verified builders. It combines isolated task evaluation with multi-file project benchmarking, grading both model outputs and reports about the codebase itself.

## Architecture

**Core Benchmark Engine** (`bench.py`)
- Orchestrates benchmark execution with HTTP helpers (`_get`, `_post`), process management (`ps`, `stop_all`), and local model interaction (`placement`, `chat`)
- Implements three evaluation modes: `run_isolated` (single tasks), `run_docpar` (parallel execution), and recording (`record`)
- Aggregates results via `write_summary`

**Task Suite** (`tasks.py`)
- Eight c_* task functions: `c_dedupe`, `c_parse_kv`, `c_classify`, `c_heat`, `c_tail`, `c_provenance`, `c_fold_edges`, `c_merge`
- Grading pipeline: `parse_verdicts` (extract model responses) → `strip_fences` (remove formatting) → `grade_audit` (evaluate) → `grade` (final score)

**Multi-File Project Benchmark** (`bench_project.py`)
- Minesweeper task: `split_prompt` (decompose requirements), `extract_files` (parse model outputs), `evaluate` (run acceptance tests), `record` (store results)
- Harness functions: `run_single`, `run_split`, `_show` (display results)

**Report Grading** (`report_grade.py`)
- Mechanical grader for reports about the local-bench codebase
- Functions: `_frac` (compute fractional score), `grade_report` (grade against known codebase contract), `_print` (format output)

**Minesweeper Contract**
- `minesweeper/model.py`: Shared Board data model with `Board`, `in_bounds`, `neighbors` — given to all candidates, never generated
- `minesweeper/CONTRACT.md`: Fixed interface requiring candidate implementations of `logic.py`, `render.py`, `ui.py` with exact signatures
- `minesweeper/suite.py`: Acceptance suite (`_fresh`, `level1`, `level2`, `level3`, `run`) that validates candidate modules against the contract

## How It Works

1. **Task Evaluation**: `bench.py main` runs isolated tasks from `tasks.py` against a local model, collecting responses and grading via the `parse_verdicts` → `grade` pipeline
2. **Project Evaluation**: `bench_project.py main` executes the minesweeper task by splitting prompts, extracting generated files, and running `minesweeper/suite.py` acceptance tests
3. **Report Grading**: `report_grade.py grade_report()` scores a report about the codebase against the known contract defined in the FACTS, applying fuzzy judgment only where necessary
4. **Results Aggregation**: `write_summary` and display functions collate all scores into a final benchmark report

## Constraints

- **Local Models Only**: Benchmarks only local models; no cloud or external APIs
- **Strict Minesweeper Contract**: Candidates must import and use the fixed `Board`, `in_bounds`, `neighbors` from `model.py`; any signature deviation breaks module composition
- **Project Layout**: Requires `model.py` (given) plus candidate-generated `logic.py`, `render.py`, `ui.py` in the project directory
- **Mechanical Grading Limit**: Report grading is mechanical for known codebase facts; fuzzy aspects remain semi-automated
- **Fixed Task Set**: Covers eight core tasks; extensibility to new tasks requires modifying `tasks.py`