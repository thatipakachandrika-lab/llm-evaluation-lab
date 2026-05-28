# LLM Evaluation Lab

This repository is a practical GenAI evaluation project focused on benchmarking LLM responses, comparing prompt strategies, validating LLM-as-a-judge outputs, and analyzing response quality failures.

The project includes a custom evaluation workflow under:

`examples/llm_response_quality_lab/`

This lab demonstrates how LLM outputs can be evaluated using benchmark questions, baseline vs improved prompts, rubric-based scoring, human-labeled references, judge consistency checks, and failure analysis reporting.

## Custom Enhancement: LLM Response Quality Lab

The main enhancement in this repository is the `llm_response_quality_lab`, which adds an applied evaluation workflow for testing and improving GenAI response quality.

Key capabilities include:

* Benchmark dataset for GenAI response evaluation
* Baseline and improved prompt templates
* Rubric-based scoring across multiple quality dimensions
* LLM-as-a-judge evaluation workflow
* Judge output validation and normalization
* Human-labeled reference dataset
* Failure category analysis
* Judge consistency checking across multiple runs
* Evaluation methodology documentation
* Summary report generation
* HTML dashboard for result visualization

## Evaluation Metrics

The lab evaluates responses using the following dimensions:

* Correctness
* Relevance
* Completeness
* Clarity
* Hallucination risk

Each response is scored using a structured rubric, and results are saved for analysis and comparison.

## Project Structure

```text
examples/llm_response_quality_lab/
├── benchmark_questions.csv
├── baseline_prompt.txt
├── improved_prompt.txt
├── run_eval.py
├── check_judge_consistency.py
├── dashboard.py
├── datasets/
│   └── human_labels.csv
├── outputs/
│   └── evaluation_results.csv
├── reports/
│   ├── evaluation_methodology.md
│   └── evaluation_summary.md
├── rubrics/
│   └── evaluation_rubric.md
└── README.md
```

## How to Run

From the repository root:

```powershell
python examples/llm_response_quality_lab/run_eval.py --mode compare --provider ollama --model phi3:latest
```

To run automatic scoring:

```powershell
python examples/llm_response_quality_lab/run_eval.py --mode compare --provider ollama --model phi3:latest --auto-score
```

To generate the dashboard:

```powershell
python examples/llm_response_quality_lab/dashboard.py --results examples/llm_response_quality_lab/outputs/evaluation_results.csv --output examples/llm_response_quality_lab/dashboard.html
```

## Why This Project Matters

LLM applications need systematic evaluation before they can be trusted in real-world workflows. This project shows how to move beyond simple prompt testing by adding structured evaluation, scoring rubrics, failure analysis, human reference labels, and consistency checks.

It demonstrates practical GenAI evaluation skills including benchmark design, prompt comparison, LLM-as-a-judge workflows, validation of model-generated scores, and response quality monitoring.

## Tech Stack

* Python
* DeepEval-inspired evaluation workflow
* Ollama / local LLM support
* OpenAI-compatible provider option
* CSV-based benchmark and result tracking
* HTML dashboard reporting

## Current Status

This is an actively improving GenAI evaluation lab. Future improvements may include larger benchmark datasets, additional evaluation metrics, model-to-model comparison, expanded dashboards, and automated regression testing for prompt versions.
