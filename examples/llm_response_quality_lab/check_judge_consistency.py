import argparse
import csv
import json
import statistics
from pathlib import Path
from collections import defaultdict


def load_results_csv(path):
    """Load evaluation results CSV and return list of dicts."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def extract_metrics(row, prefix):
    """Extract per-metric scores from a row (baseline or improved)."""
    metrics = {}
    for m in ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']:
        key = f'{prefix}_{m}'
        v = row.get(key)
        if v and v not in ('', 'None'):
            try:
                metrics[m] = int(v)
            except Exception:
                pass
    return metrics


def compute_consistency(all_runs):
    """
    Given a list of result CSVs from multiple runs,
    compute consistency metrics for each question.
    
    Returns:
    - per_question_consistency: dict with std dev and mean for each question
    - metric_consistency: consistency of each metric across runs
    - overall_consistency: overall score consistency
    """
    n_runs = len(all_runs)
    if n_runs < 2:
        raise ValueError('Need at least 2 runs to measure consistency')
    
    # Group scores by question ID
    question_scores = defaultdict(lambda: {'baseline': defaultdict(list), 'improved': defaultdict(list)})
    
    for run_idx, rows in enumerate(all_runs):
        for row in rows:
            q_id = row.get('id', '')
            baseline_metrics = extract_metrics(row, 'baseline')
            improved_metrics = extract_metrics(row, 'improved')
            baseline_score = row.get('baseline_score')
            improved_score = row.get('improved_score')
            
            # Collect metric scores
            for m, v in baseline_metrics.items():
                question_scores[q_id]['baseline'][f'metric_{m}'].append(v)
            for m, v in improved_metrics.items():
                question_scores[q_id]['improved'][f'metric_{m}'].append(v)
            
            # Collect overall scores
            if baseline_score and baseline_score not in ('', 'None'):
                try:
                    question_scores[q_id]['baseline']['overall'].append(float(baseline_score))
                except Exception:
                    pass
            if improved_score and improved_score not in ('', 'None'):
                try:
                    question_scores[q_id]['improved']['overall'].append(float(improved_score))
                except Exception:
                    pass
    
    # Compute consistency stats
    per_question = {}
    metric_variance = defaultdict(list)
    overall_variance = []
    
    for q_id, prefixes in question_scores.items():
        per_question[q_id] = {}
        for prefix in ('baseline', 'improved'):
            stats = {}
            for score_type, scores in prefixes[prefix].items():
                if len(scores) >= 2:
                    mean = statistics.mean(scores)
                    stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
                    stats[score_type] = {'mean': mean, 'stdev': stdev}
                    if 'metric_' in score_type:
                        metric_name = score_type.replace('metric_', '')
                        metric_variance[metric_name].append(stdev)
                    elif score_type == 'overall':
                        overall_variance.append(stdev)
            per_question[q_id][prefix] = stats
    
    # Aggregate metric consistency
    metric_consistency = {}
    for m, stdevs in metric_variance.items():
        if stdevs:
            metric_consistency[m] = {
                'mean_stdev': statistics.mean(stdevs),
                'max_stdev': max(stdevs),
            }
    
    overall_consistency = {}
    if overall_variance:
        overall_consistency = {
            'mean_stdev': statistics.mean(overall_variance),
            'max_stdev': max(overall_variance),
        }
    
    return per_question, metric_consistency, overall_consistency


def generate_consistency_report(output_path, per_question, metric_consistency, overall_consistency, n_runs):
    """Write consistency analysis to markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Judge Consistency Report\n\n')
        f.write(f'Runs analyzed: {n_runs}\n\n')
        f.write('Consistency measures how stable the LLM judge is across multiple evaluation runs. '
                'Lower standard deviation means more consistent.\n\n')
        
        f.write('## Overall Score Consistency\n\n')
        if overall_consistency:
            f.write(f'- Mean standard deviation: {overall_consistency["mean_stdev"]:.3f}\n')
            f.write(f'- Max standard deviation: {overall_consistency["max_stdev"]:.3f}\n\n')
            if overall_consistency["mean_stdev"] < 0.2:
                f.write('**Interpretation**: High consistency. Judge is stable.\n')
            elif overall_consistency["mean_stdev"] < 0.5:
                f.write('**Interpretation**: Moderate consistency. Some variance but generally reliable.\n')
            else:
                f.write('**Interpretation**: Low consistency. Judge may be unstable; use with caution.\n')
        else:
            f.write('- No overall scores recorded.\n')
        
        f.write('\n## Per-Metric Consistency\n\n')
        if metric_consistency:
            f.write('| Metric | Mean Std Dev | Max Std Dev | Interpretation |\n')
            f.write('|--------|--------------|------------|----------------|\n')
            for m, stats in sorted(metric_consistency.items()):
                stdev = stats['mean_stdev']
                if stdev < 0.3:
                    interp = 'Highly consistent'
                elif stdev < 0.6:
                    interp = 'Moderately consistent'
                else:
                    interp = 'Low consistency'
                f.write(f'| {m} | {stdev:.3f} | {stats["max_stdev"]:.3f} | {interp} |\n')
        else:
            f.write('- No per-metric scores recorded.\n')
        
        f.write('\n## Per-Question Consistency\n\n')
        f.write('| Question ID | Baseline Overall Std Dev | Improved Overall Std Dev | Notes |\n')
        f.write('|-------------|-------------------------|-------------------------|-------|\n')
        for q_id, prefixes in sorted(per_question.items()):
            baseline_stats = prefixes.get('baseline', {})
            improved_stats = prefixes.get('improved', {})
            b_stdev = baseline_stats.get('overall', {}).get('stdev', '')
            i_stdev = improved_stats.get('overall', {}).get('stdev', '')
            b_str = f'{b_stdev:.3f}' if b_stdev else 'N/A'
            i_str = f'{i_stdev:.3f}' if i_stdev else 'N/A'
            f.write(f'| {q_id} | {b_str} | {i_str} | |\n')
        
        f.write('\n## Recommendations\n\n')
        if overall_consistency and overall_consistency["mean_stdev"] < 0.2:
            f.write('- Judge is stable. Proceed with confidence in the evaluation results.\n')
        elif overall_consistency and overall_consistency["mean_stdev"] < 0.5:
            f.write('- Judge shows moderate consistency. Consider increasing sample size or using multiple runs.\n')
        else:
            f.write('- Judge may be unstable. Consider lowering temperature further or using a different judge model.\n')
        
        f.write('- If metrics have high variance, the rubric definitions may need refinement.\n')
        f.write('- Compare judge scores against human labels (ground truth) to validate accuracy.\n')
    
    print(f'Wrote consistency report to {output_path}')


def main():
    parser = argparse.ArgumentParser(
        description='Measure LLM judge consistency across multiple evaluation runs.'
    )
    parser.add_argument(
        '--run-files',
        nargs='+',
        required=True,
        help='Paths to evaluation_results.csv files from multiple runs (e.g., run1.csv run2.csv run3.csv)'
    )
    parser.add_argument(
        '--output',
        default='examples/llm_response_quality_lab/reports/judge_consistency_report.md',
        help='Output path for the consistency report'
    )
    args = parser.parse_args()
    
    # Load all runs
    all_runs = []
    for fpath in args.run_files:
        fpath = Path(fpath)
        if not fpath.exists():
            print(f'Error: {fpath} not found')
            return
        rows = load_results_csv(fpath)
        all_runs.append(rows)
    
    # Compute consistency
    per_question, metric_consistency, overall_consistency = compute_consistency(all_runs)
    
    # Generate report
    generate_consistency_report(
        Path(args.output),
        per_question,
        metric_consistency,
        overall_consistency,
        len(all_runs)
    )


if __name__ == '__main__':
    main()
