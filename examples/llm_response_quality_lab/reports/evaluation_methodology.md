# Evaluation Methodology

This document outlines the methodology, assumptions, and limitations of the LLM Response Quality Lab evaluation framework.

## Overview

The lab compares two prompt variants (baseline and improved) by:
1. Running both prompts through a set of benchmark questions.
2. Collecting model responses.
3. Using an LLM judge to score responses against a formal rubric.
4. Aggregating scores to measure prompt quality difference.

## What is Being Evaluated

- **Prompt Effectiveness**: Does the improved prompt elicit higher-quality responses than the baseline?
- **Response Quality**: On five dimensions — correctness, relevance, completeness, clarity, and hallucination risk.
- **Failure Modes**: Which types of errors occur most frequently in baseline vs improved responses?

## Evaluation Metrics

### Primary Metrics (1–5 Scale)

Each response is scored on five dimensions:

- **Correctness (1–5)**: Is the factual content accurate and well-founded?
  - 5: Fully correct; no hallucinations; statements supported by widely-known facts.
  - 1: Completely incorrect or misleading.

- **Relevance (1–5)**: Does the response directly address the question?
  - 5: Highly focused; every sentence addresses the question.
  - 1: Irrelevant; misses the core of the question.

- **Completeness (1–5)**: Does it cover all important aspects?
  - 5: All expected dimensions covered concisely.
  - 1: Only superficial points; noticeable gaps.

- **Clarity (1–5)**: Is the response easy to read and understand?
  - 5: Well-structured; clear language; logical flow.
  - 1: Unreadable; confusing organization.

- **Hallucination Risk (1–5)**: Are claims made with unjustified confidence?
  - 5: No hallucinated details; cites facts cautiously.
  - 1: Contains fabricated facts or confident falsehoods.

### Derived Metrics

- **Overall Score**: Arithmetic mean of the five metric scores (1–5).
- **Improvement**: Overall Score (improved) − Overall Score (baseline).
- **Winner**: Which variant scored higher (or tie).
- **Failure Category**: The primary failure mode detected (if any).

## Why These Metrics Were Chosen

1. **Correctness** addresses factuality — essential for trustworthiness.
2. **Relevance** ensures the model stays on task (reduces tangents).
3. **Completeness** forces breadth without verbosity.
4. **Clarity** makes responses actionable (users can understand and use the output).
5. **Hallucination Risk** directly tackles a known LLM weakness.

These five dimensions cover the common failure modes in production GenAI systems and align with industry evaluation frameworks (e.g., RAG evaluation, instruction-following).

## How Scoring Works

### Judge Prompt

The LLM judge receives:
- The original question.
- Both responses (baseline and improved).
- The five metric definitions (see rubric).
- Instructions to score each metric 1–5 and return JSON.

### Judge Output

The judge returns a JSON object with:
```json
{
  "baseline_correctness": 3,
  "baseline_relevance": 4,
  "baseline_completeness": 2,
  "baseline_clarity": 4,
  "baseline_hallucination_risk": 4,
  "improved_correctness": 4,
  "improved_relevance": 5,
  "improved_completeness": 4,
  "improved_clarity": 5,
  "improved_hallucination_risk": 5,
  "baseline_score": 3.4,
  "improved_score": 4.6,
  "winner": "improved",
  "failure_category": "Incomplete Answer",
  "notes": "Improved response provided clearer structure and filled missing steps."
}
```

### Validation

All scores are validated:
- Each metric score must be an integer 1–5.
- Overall scores are computed as means and rounded to 2 decimal places.
- If the judge provides invalid JSON or out-of-range scores, the entry is flagged and skipped.
- `winner` must be one of `baseline`, `improved`, or `tie`; invalid winners default to `tie`.
- `failure_category` must match the rubric or default to `Other`.

## Limitations of LLM-as-a-Judge

1. **Bias**: The judge LLM may favor certain writing styles or phrasings inherent to its training data.
2. **Hallucination**: The judge itself can hallucinate; for example, it might claim a response cites sources when it does not.
3. **Context Length**: Long responses may be truncated by the judge; context windows can limit fair evaluation.
4. **Inconsistency**: LLM judges can give different scores on repeated runs if temperature > 0.
5. **Metric Interpretation**: The judge may interpret "hallucination risk" or "completeness" differently than humans.
6. **Generalization**: Scores trained on one domain may not transfer to another (e.g., finance → medicine).

### Mitigation Strategies

- **Multiple Runs**: Run the evaluation 3+ times and measure consistency (std dev of scores).
- **Human Gold Labels**: Compare LLM judge scores against human-labeled ground truth (see `datasets/human_labels.csv`).
- **Low Temperature**: Use temperature = 0.2 for scoring to reduce variance.
- **Rubric Clarity**: Use detailed rubric definitions to anchor the judge's interpretation.

## How Judge Output is Validated

1. **Schema Check**: All expected JSON keys present?
2. **Type Check**: Scores are integers 1–5; overall scores are floats?
3. **Consistency Check**: Computed mean ≈ provided overall score (within 0.25)?
4. **Range Check**: All values within expected bounds?
5. **Category Check**: Failure categories are valid or default to `Other`?

If validation fails, the record is flagged, scores are left empty, and a warning is logged.

## How Failure Categories are Interpreted

The lab tracks six failure categories:

- **Incomplete Answer**: Response omits a key aspect or is too superficial.
- **Hallucination**: Response contains factually incorrect or unsupported claims.
- **Irrelevant Answer**: Response goes off-topic or misunderstands the question.
- **Missing Context**: Response lacks necessary background or assumes too much knowledge.
- **Poor Formatting**: Response is hard to read (poor grammar, disorganized structure).
- **Incorrect Reasoning**: Response uses flawed logic or contradicts itself.
- **Other**: Failure type not clearly categorized above.

Human labels and LLM judge labels are compared to measure agreement and identify patterns.

## Ground Truth: Human Labels

The `datasets/human_labels.csv` file contains human-annotated labels for a subset of questions:
- `human_preferred_response`: The response a human expert preferred (baseline or improved).
- `human_failure_category`: The human-identified failure mode.
- `human_notes`: Justification for the human judgment.

This ground truth is used to:
1. Validate LLM judge accuracy against human judgment.
2. Measure judge precision, recall, and F1 on failure categories.
3. Identify systematic biases in the LLM judge.

## Evaluation Workflow

```
1. Load benchmark questions
2. Apply baseline prompt → collect response
3. Apply improved prompt → collect response
4. (Optional) Send both to LLM judge for scoring
5. Validate judge output
6. Append scores and metadata to evaluation_results.csv
7. Aggregate scores and failure categories
8. Generate summary report with statistics
9. Compare against human labels (if available)
```

## Outputs

- **evaluation_results.csv**: Row-by-row breakdown of scores and metadata.
- **evaluation_summary.md**: Aggregated statistics and top failure categories.
- **human_comparison.md** (future): Compare LLM judge vs human labels.
- **judge_consistency_report.md** (future): Measure judge stability across multiple runs.

## Next Steps

- Add human label comparison: compute LLM judge precision/recall against `human_labels.csv`.
- Add consistency analysis: run evaluation 3+ times and measure score variance.
- Expand benchmark set: increase sample size for stronger signal.
- Add ablation studies: test different rubric definitions to see sensitivity.

## References

- DeepEval Framework: [https://github.com/confident-ai/deepeval](https://github.com/confident-ai/deepeval) — inspiration for structured LLM evaluation.
- RAG Evaluation Metrics: RAGAS framework ([https://github.com/explodinggradients/ragas](https://github.com/explodinggradients/ragas)).
- LLM Judge Bias: [Yuan et al., 2023] — on bias in LLM-based evaluation ([https://arxiv.org/abs/2307.16735](https://arxiv.org/abs/2307.16735)).
