# local-bench

## Overview

The `local-bench` codebase is a benchmarking suite for evaluating local large language models as verified software builders. It contains two primary benchmarks: a single-file task suite (`tasks.py`) covering data processing operations like deduplication, parsing, and classification, and a multi-file project benchmark (`bench_project.py`) that evaluates a candidate's ability to implement a Minesweeper clone against a fixed contract (`minesweeper/CONTRACT.md`) and shared data model (`minesweeper/model.py`). The framework includes a grader (`report_grade.py`) for assessing end-to-end reports on the codebase itself, alongside utilities for running isolated tasks, managing model sessions, and recording performance metrics.

## Components

The codebase is organized into a benchmark runner, a task suite, a multi-file project benchmark, and a grading utility. `bench.py` provides the core execution logic, including HTTP helpers, chat recording, and isolated run management. `tasks.py` defines the specific coding challenges (e.g., `c_dedupe`, `c_parse_kv`, `c_classify`) and their associated grading functions. `bench_project.py` orchestrates the minesweeper multi-file project benchmark, handling prompt splitting, file extraction, and evaluation. `report_grade.py` serves as the end-to-end grader for reports about the codebase, using mechanical checks against known parameters. The `minesweeper/` directory contains the shared `model.py` (defining `Board`, `in_bounds`, and `neighbors`), the `CONTRACT.md` specifying module interfaces, and `suite.py` for acceptance testing.

## How it works

The local-bench suite evaluates local models through three distinct mechanisms. The `bench.py` module runs a series of single-file coding tasks (defined in `tasks.py`) such as deduplication, parsing, and classification to measure functional correctness. The `bench_project.py` module assesses multi-file project composition via a minesweeper task, where candidates implement logic, rendering, and UI modules against a fixed shared data model (`minesweeper/model.py`) and contract (`minesweeper/CONTRACT.md`). Finally, `report_grade.py` provides an end-to-end evaluation by mechanically grading a written report about the codebase against known parameters, bridging the gap between fuzzy natural language assessment and precise code verification.

## Usage and results

The local-bench codebase provides a benchmark for evaluating local models as verified builders, featuring a task suite (`tasks.py`) with functions like `c_dedupe`, `c_parse_kv`, and `c_classify`. The main entry point (`main`) orchestrates these tasks, which are graded by `report_grade.py` to produce a mechanical score. A multi-file project benchmark (`bench_project.py`) tests the implementation of a minesweeper clone, using a fixed data model (`minesweeper/model.py`) and contract (`minesweeper/CONTRACT.md`) to ensure module composition. The acceptance suite (`minesweeper/suite.py`) validates the implementation against predefined levels. Results are summarized by `write_summary` and `record` functions, providing a comprehensive evaluation of the local model's performance.

## Limitations

The benchmark is restricted to Python and evaluates only a narrow set of tasks (deduplication, parsing, classification, heatmaps, tailing, provenance, edge folding, merging, and a minesweeper project). It relies on a fixed contract for the minesweeper task, meaning only the logic, render, and UI modules are evaluated while the shared data model is provided. Grading for the end-to-end report component is partially fuzzy, mitigated by mechanical checks against known parameters. The benchmark does not assess cloud-based models, non-Python languages, or real-world deployment scenarios.