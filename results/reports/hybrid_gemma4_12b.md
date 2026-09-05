# local-bench

## Overview

local-bench is a benchmark suite for evaluating local models as verified builders. It measures model performance across two primary evaluation modes: a task suite (tasks.py) and a multi-file project benchmark (bench_project.py) centered on Minesweeper. The Minesweeper task enforces a strict contract (minesweeper/CONTRACT.md) and shared data model (minesweeper/model.py) to validate that independently-generated modules—logic, render, and ui—compose correctly. An acceptance suite (minesweeper/suite.py) verifies component functionality, while a mechanical grader (report_grade.py) evaluates E2E benchmark reports against known par.

## Architecture

**Execution Layer** (`bench.py`):
- HTTP primitives (`_get`, `_post`) for model interaction
- Process management (`ps`, `stop_all`) for isolated builder instances
- Benchmark runner (`run_isolated`, `run_docpar`) supporting isolated and docstring-parallel execution modes
- Recording and summary generation (`record`, `write_summary`)

**Task Suite** (`tasks.py`):
- Nine task functions: `c_dedupe`, `c_parse_kv`, `c_classify`, `c_heat`, `c_tail`, `c_provenance`, `c_fold_edges`, `c_merge`
- Verdict parsing and grading: `parse_verdicts`, `grade_audit`, `strip_fences`, `grade`

**Multi-file Project Benchmark** (`bench_project.py`):
- Prompt orchestration (`split_prompt`) to segment tasks across model calls
- File extraction and evaluation (`extract_files`, `evaluate`)
- Single-split and split-execution modes (`run_single`, `run_split`)

**Minesweeper Task**:
- Shared data model (`minesweeper/model.py`): `Board` class with `in_bounds` and `neighbors` helpers—the contract's glue
- Module contract (`minesweeper/CONTRACT.md`): Specifies signatures for logic.py, render.py, and ui.py; stdlib only
- Acceptance suite (`minesweeper/suite.py`): Three difficulty levels (`level1`, `level2`, `level3`) plus `_fresh` board generation and `run` orchestrator

**Report Evaluation** (`report_grade.py`):
- Mechanical grader (`grade_report`) for E2E benchmark reports against local-bench's known par
- Fraction and printing utilities (`_frac`, `_print`)

## Design

The codebase splits evaluation concerns: `bench.py` manages model execution and process lifecycle; `tasks.py` defines individual task logic and grading; `bench_project.py` orchestrates multi-turn prompting for complex projects; the Minesweeper contract ensures modular composability via a fixed data model. Report grading (`report_grade.py`) applies mechanical rules to minimize subjectivity in evaluating descriptions of the codebase itself.

## Limitations

Report grading remains inherently fuzzier than code evaluation; `report_grade.py` mitigates this by applying mechanical rules against known local-bench parameters. The Minesweeper task's strict contract (model.py signatures and CONTRACT.md) enables modular independence but requires exact adherence to composition interfaces.