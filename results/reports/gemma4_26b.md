# local-bench

## Overview

local-bench is a benchmark designed for using local models as verified builders. The codebase includes a builder benchmark (bench.py), a task suite (tasks.py), and a multi-file project benchmark featuring a minesweeper task (bench_project.py). The minesweeper task utilizes a shared data model (minesweeper/model.py) and a fixed contract (minesweeper/CONTRACT.md) to ensure independently-generated modules compose, with an acceptance suite (minesweeper/suite.py) to run against candidate logic. Additionally, the system includes a mechanical grader (report_grade.py) for evaluating reports about the local-bench codebase.

## Components

The codebase consists of the following elements:
- **bench.py**: A benchmark for local-model builders.
- **tasks.py**: A suite of tasks including deduplication, parsing, classification, and grading utilities.
- **bench_project.py**: A multi-file project benchmark featuring a minesweeper task.
- **report_grade.py**: A mechanical grader for reports regarding the local-bench codebase.
- **minesweeper/model.py**: A shared data model providing the contract for the minesweeper task.
- **minesweeper/CONTRACT.md**: The implementation contract for the minesweeper modules.
- **minesweeper/suite.py**: An acceptance suite for evaluating the minesweeper task.
- **README.md**: Documentation for the local-bench project.

## How it works

The local-bench codebase functions as a benchmark for using local models as verified builders through several specialized components:

*   **Benchmarking Core**: `bench.py` executes the local-model builder benchmark, while `bench_project.py` handles multi-file project benchmarks, specifically the minesweeper task.
*   **Task Suite**: `tasks.py` provides a suite of tasks including deduplication, parsing, classification, and grading utilities.
*   **Minesweeper Implementation**: The minesweeper task relies on a fixed contract (`minesweeper/CONTRACT.md`) and a shared data model (`minesweeper/model.py`) to ensure independently-generated modules compose correctly. An acceptance suite (`minesweeper/suite.py`) runs against the candidate project directory to verify the implementation.
*   **Evaluation**: `report_grade.py` acts as a grader for reports about the local-bench codebase, maintaining mechanical grading against known parameters.

## Usage and results

The local-bench codebase provides a benchmark for using local models as verified builders. It includes a task suite (tasks.py) and a multi-file project benchmark (bench_project.py) centered on a Minesweeper task. This task utilizes a fixed data model (minesweeper/model.py) and a strict contract (minesweeper/CONTRACT.md) to ensure independently-generated modules compose correctly. Evaluation is performed via an acceptance suite (minesweeper/suite.py) and a mechanical grader (report_grade.py) that assesses reports against known benchmarks.

## Limitations

The codebase is specifically designed as a benchmark for local models acting as verified builders, which may limit its general applicability to other software engineering tasks. While the `report_grade.py` component maintains mechanical grading against known parameters, the process of grading reports remains inherently fuzzy where code is not present. Additionally, the minesweeper task relies on a fixed contract and a shared data model (`model.py`) that is provided to candidates rather than generated, constraining the scope of the evaluation to modules that can successfully compose within this predefined structure.