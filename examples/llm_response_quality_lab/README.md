# LLM Response Quality Lab

This lab demonstrates a simple prompt comparison workflow for response quality evaluation.

## Contents

- `benchmark_questions.csv` - sample evaluation questions
- `baseline_prompt.txt` - original prompt template
- `improved_prompt.txt` - enhanced prompt template
- `run_eval.py` - evaluation script for prompt comparison
- `failure_analysis.md` - notes for tracking prompt failures

## How to run

1. Install dependencies:
   ```bash
   pip install openai
   ```

2. Set your OpenAI key:
   ```bash
   setx OPENAI_API_KEY "your_api_key"
   ```

3. Run the comparison:
   ```bash
   python examples/llm_response_quality_lab/run_eval.py --mode compare --provider ollama
   ```

4. Optional: have the model auto-score responses (requires Ollama or OpenAI):
   ```bash
   python examples/llm_response_quality_lab/run_eval.py --mode compare --provider ollama --auto-score
   ```

5. Results and summary files are created under `examples/llm_response_quality_lab/outputs/` and `examples/llm_response_quality_lab/reports/`:
   - `outputs/evaluation_results.csv` — per-question responses, scores, winner, failure category, notes
   - `reports/evaluation_summary.md` — aggregated averages and most common failure categories
   - `reports/evaluation_methodology.md` — detailed evaluation framework and methodology

## Evaluation Trust & Validation

This lab includes multiple tools to validate and analyze evaluation quality:

### Ground Truth: Human Labels

File: `datasets/human_labels.csv`

Contains human-expert labels for a subset of benchmark questions. Use this to:
- Compare LLM judge scores against human judgment.
- Measure judge accuracy.
- Identify systematic biases.

### Judge Consistency Check

File: `check_judge_consistency.py`

Measure how stable the LLM judge is across multiple runs:

```bash
python check_judge_consistency.py \
  --run-files outputs/run1.csv outputs/run2.csv outputs/run3.csv \
  --output reports/judge_consistency_report.md
```

### Visual Dashboard

File: `dashboard.py`

Generate an interactive HTML dashboard:

```bash
python dashboard.py --results outputs/evaluation_results.csv --output dashboard.html
```

## Project Structure

```
examples/llm_response_quality_lab/
├── benchmark_questions.csv            # Sample evaluation questions
├── baseline_prompt.txt                 # Baseline prompt template
├── improved_prompt.txt                 # Improved prompt template
├── run_eval.py                         # Main evaluation script
├── check_judge_consistency.py          # Judge stability analyzer
├── dashboard.py                        # Interactive dashboard
├── README.md                           # This file
├── datasets/
│   └── human_labels.csv                # Ground truth labels
├── rubrics/
│   └── evaluation_rubric.md            # Evaluation rubric (1-5 scales)
├── outputs/
│   └── evaluation_results.csv          # Per-question results
└── reports/
    ├── evaluation_summary.md           # Summary statistics
    ├── evaluation_methodology.md       # Detailed methodology
    └── judge_consistency_report.md     # Judge stability (generated)
```

## What this lab shows

- A simple set of benchmark questions
- A baseline prompt for direct answers
- An improved prompt focused on accuracy, relevance, and structure
- A workflow for comparing model responses and tracking failures
