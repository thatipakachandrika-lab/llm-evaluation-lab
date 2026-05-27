# Failure Analysis

This file helps you track where the baseline prompt fails and how the improved prompt performs better.

## Common failure categories

- **Incomplete answer**: The model leaves out a key aspect of the question.
- **Hallucination**: The model invents unsupported details or facts.
- **Off-topic or vague**: The response does not directly answer the question.
- **Poor structure**: The response is hard to read or lacks a clear conclusion.

## How to use this analysis

1. Run `run_eval.py` with both prompts.
2. Compare the baseline and improved outputs.
3. Mark each example with the failure types above.
4. Use the failure patterns to refine the prompt or evaluation design.

## Example entries

| id | question | baseline issue | improved behavior | next step |
|----|----------|----------------|-------------------|-----------|
| q1 | Summarize cash flow benefits | Too short, missing startup context | Clear list of benefits | Add stronger startup framing |
