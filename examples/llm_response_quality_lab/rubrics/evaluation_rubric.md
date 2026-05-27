# Evaluation Rubric

This rubric defines the criteria and numeric scales used to evaluate model responses. All scores are integers 1–5. Use the average of the metric scores as the overall score.

Metrics
- Correctness (1–5)
  - 5: Fully correct; statements supported by widely-known facts or directly answer the question without error.
  - 4: Mostly correct; minor inaccuracies or small omissions that do not affect the main answer.
  - 3: Partial correctness; some correct points but also important errors or omissions.
  - 2: Largely incorrect; answer contains multiple factual mistakes or misunderstandings.
  - 1: Completely incorrect or misleading.

- Relevance (1–5)
  - 5: Directly addresses the question with focused, on-topic content.
  - 4: Mostly on-topic but includes minor tangents or extra information.
  - 3: Partially on-topic; relevant points mixed with unrelated material.
  - 2: Largely off-topic; misses the core of the question.
  - 1: Irrelevant content.

- Completeness (1–5)
  - 5: Covers all important aspects expected from the question concisely.
  - 4: Covers most important aspects but misses one minor aspect.
  - 3: Addresses some aspects but leaves noticeable gaps.
  - 2: Very incomplete; only superficial points provided.
  - 1: No useful coverage of required aspects.

- Clarity (1–5)
  - 5: Clear, well-structured, easy to read; uses short paragraphs or bullets.
  - 4: Mostly clear; minor wording or organization issues.
  - 3: Understandable but could be better organized or phrased.
  - 2: Hard to follow; poor grammar or disorganized.
  - 1: Unreadable or confusing.

- Hallucination Risk (1–5)
  - 5: No hallucinated or unsupported claims; cites facts cautiously.
  - 4: Low risk; mostly factual, with one small unsupported claim.
  - 3: Moderate risk; some plausible-sounding but unverifiable claims.
  - 2: High risk; several likely invented details.
  - 1: Contains fabricated facts or confident falsehoods.

Notes on Hallucination Risk: For scoring consistency, treat this as an inverse harm metric (higher is better). When aggregating, the overall score is the arithmetic mean of the five metric scores.

Failure Categories (for `failure_category` field)
- Incomplete Answer
- Hallucination
- Irrelevant Answer
- Missing Context
- Poor Formatting
- Incorrect Reasoning
- Other

Example JSON output expected from an automated judge (model or script):
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
  "notes": "Improved prompt provided clearer structure and filled missing steps."
}

Validation guidance
- All metric fields must be integers between 1 and 5.
- Overall `baseline_score` and `improved_score` should equal the arithmetic mean of their five metric scores (rounding optional; store as float).
- `winner` must be one of `baseline`, `improved`, or `tie`.
- `failure_category` must be one of the Failure Categories above or an empty string/null if none.

Use this file to seed judge prompts and to enforce validation of automated judge outputs.
