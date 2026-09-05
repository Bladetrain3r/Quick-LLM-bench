# local-bench

## Overview
The local-bench codebase is a benchmark designed to evaluate the performance of local models acting as verified builders. The project includes a suite of tasks (tasks.py) and a multi-file project benchmark (bench_project.py) featuring a Minesweeper task. The Minesweeper task is structured around a fixed contract (minesweeper/CONTRACT.md) and a shared data model (minesweeper/model.py) to ensure that independently-generated modules can compose correctly. The codebase also includes a grading system (report_grade.py) to evaluate reports about the codebase and an acceptance suite (minesweeper/suite.py) to verify the Minesweeper implementation.

## Components

*   **bench.py**: The core local-model builder benchmark script containing functions for execution, recording, and evaluation.
*   **tasks.py**: The task suite for the benchmark, including various processing functions and grading logic.
*   **bench_project.py**: A multi-file project benchmark specifically for the minesweeper task, handling prompt splitting and evaluation.
*   **report_grade.py**: A mechanical grader for reports about the local-bench codebase.
*   **README.md**: Documentation for the local-bench project.
*   **minesweeper/model.py**: The shared data model for the minesweeper task, providing the fixed contract for the project.
*   **minesweeper/CONTRACT.md**: The specification for the minesweeper clone, defining the requirements for independent module composition.
*   **minesweeper/suite.py**: The acceptance suite used to test the minesweeper project's logic, rendering, and UI.

## How it works

The local-bench codebase evaluates the performance of local models as verified builders through several specialized components:

*   **Benchmarking Framework**: `bench.py` provides the core infrastructure for running local-model builder benchmarks, while `tasks.py` contains a suite of specific tasks (such as deduplication, parsing, and classification) used to evaluate model capabilities.
*   **Multi-file Project Evaluation**: `bench_project.py` implements a multi-file project benchmark centered on a Minesweeper task. It handles prompt splitting, file extraction, and evaluation of generated components.
*   **Contract-Based Development**: The Minesweeper task enforces a strict architectural contract. `minesweeper/model.py` defines a shared data model (Board, in_bounds, neighbors) that acts as the glue between independently generated modules (logic, render, and UI), while `minesweeper/CONTRACT.md` enforces these constraints.
*   **Automated Grading**: `report_grade.py` provides a mechanical grading system for reports about the codebase, and `minesweeper/suite.py` serves as the acceptance suite to verify that the generated Minesweeper modules function correctly according to the established contract.

## Usage and results

The local-bench codebase provides a framework for benchmarking local models as verified builders. It includes a task suite in `tasks.py` for evaluating various capabilities and a multi-file project benchmark in `bench_project.py` specifically for a minesweeper task. The minesweeper task utilizes a shared data model in `minesweeper/model.py` and a strict contract in `minesweeper/CONTRACT.md` to ensure that independently-generated modules (logic, render, and ui) compose correctly. Evaluation is performed via `report_grade.py`, which provides a mechanical grading system for reports, and `minesweeper/suite.py`, which serves as the acceptance suite for the minesweeper project.

## Limitations

The codebase relies on a fixed contract in `minesweeper/model.py` to ensure that independently-generated modules (logic, render, and ui) can compose correctly. Additionally, the grading of reports is inherently fuzzy compared to code; therefore, `report_grade.py` is designed to keep the evaluation as mechanical as possible against the known parameters of the `local-bench` codebase.