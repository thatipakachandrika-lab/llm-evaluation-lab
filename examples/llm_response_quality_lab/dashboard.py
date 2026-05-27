import argparse
import csv
import statistics
from pathlib import Path
from collections import defaultdict, Counter


def load_results_csv(path):
    """Load evaluation results CSV and return list of dicts."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def safe_float(v):
    """Safely convert value to float or None."""
    if v and v not in ('', 'None'):
        try:
            return float(v)
        except Exception:
            pass
    return None


def safe_int(v):
    """Safely convert value to int or None."""
    if v and v not in ('', 'None'):
        try:
            return int(v)
        except Exception:
            pass
    return None


def generate_dashboard_html(rows, output_path):
    """Generate an interactive HTML dashboard from evaluation results."""
    
    # Extract data
    baseline_scores = [safe_float(r.get('baseline_score')) for r in rows if safe_float(r.get('baseline_score'))]
    improved_scores = [safe_float(r.get('improved_score')) for r in rows if safe_float(r.get('improved_score'))]
    
    avg_baseline = statistics.mean(baseline_scores) if baseline_scores else 0
    avg_improved = statistics.mean(improved_scores) if improved_scores else 0
    improvement_amount = avg_improved - avg_baseline
    
    # Per-metric analysis
    metrics = ['correctness', 'relevance', 'completeness', 'clarity', 'hallucination_risk']
    metric_scores = {
        'baseline': defaultdict(list),
        'improved': defaultdict(list),
    }
    for row in rows:
        for m in metrics:
            b_val = safe_int(row.get(f'baseline_{m}'))
            i_val = safe_int(row.get(f'improved_{m}'))
            if b_val:
                metric_scores['baseline'][m].append(b_val)
            if i_val:
                metric_scores['improved'][m].append(i_val)
    
    metric_avgs = {'baseline': {}, 'improved': {}}
    for prefix in ('baseline', 'improved'):
        for m in metrics:
            vals = metric_scores[prefix][m]
            metric_avgs[prefix][m] = statistics.mean(vals) if vals else 0
    
    # Winner distribution
    winners = Counter([r.get('winner', 'tie') for r in rows if r.get('winner')])
    
    # Failure categories
    failures = Counter([r.get('failure_category', '') for r in rows if r.get('failure_category')])
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Response Quality Lab - Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            margin-top: 0;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #667eea;
            margin-top: 30px;
            border-left: 5px solid #667eea;
            padding-left: 15px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 10px 0;
            text-align: center;
        }}
        .metric-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .metric-card .value {{
            font-size: 36px;
            font-weight: bold;
        }}
        .metric-card .improvement {{
            font-size: 14px;
            margin-top: 5px;
            opacity: 0.8;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .bar {{
            height: 20px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px;
            display: inline-block;
        }}
        .label {{
            color: #666;
            font-size: 12px;
        }}
        .winner-improved {{
            color: #28a745;
            font-weight: bold;
        }}
        .winner-baseline {{
            color: #dc3545;
            font-weight: bold;
        }}
        .winner-tie {{
            color: #ffc107;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 LLM Response Quality Lab - Evaluation Dashboard</h1>
        
        <h2>📊 Overall Performance</h2>
        <div class="grid">
            <div class="metric-card">
                <h3>Baseline Average Score</h3>
                <div class="value">{avg_baseline:.2f}</div>
                <div class="label">/5.0</div>
            </div>
            <div class="metric-card">
                <h3>Improved Average Score</h3>
                <div class="value">{avg_improved:.2f}</div>
                <div class="label">/5.0</div>
            </div>
            <div class="metric-card">
                <h3>Improvement</h3>
                <div class="value">{improvement_amount:+.2f}</div>
                <div class="label">points</div>
                <div class="improvement">{(improvement_amount / avg_baseline * 100) if avg_baseline else 0:+.1f}% better</div>
            </div>
        </div>
        
        <h2>📈 Per-Metric Comparison</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Baseline</th>
                <th>Improved</th>
                <th>Δ</th>
            </tr>
"""
    for m in metrics:
        b_score = metric_avgs['baseline'].get(m, 0)
        i_score = metric_avgs['improved'].get(m, 0)
        delta = i_score - b_score
        html_content += f"""            <tr>
                <td><strong>{m.replace('_', ' ').title()}</strong></td>
                <td>{b_score:.2f}</td>
                <td>{i_score:.2f}</td>
                <td><span class="{'winner-improved' if delta > 0 else 'winner-baseline' if delta < 0 else 'winner-tie'}">{delta:+.2f}</span></td>
            </tr>
"""
    
    html_content += """        </table>
        
        <h2>🏆 Winner Distribution</h2>
        <table>
            <tr>
                <th>Outcome</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""
    total_comparisons = sum(winners.values()) if winners else 1
    for outcome in ['improved', 'baseline', 'tie']:
        count = winners.get(outcome, 0)
        percentage = (count / total_comparisons * 100) if total_comparisons else 0
        html_content += f"""            <tr>
                <td><strong>{outcome.title()}</strong></td>
                <td>{count}</td>
                <td><div class="bar" style="width: {percentage * 2}px;"></div> {percentage:.1f}%</td>
            </tr>
"""
    
    html_content += """        </table>
        
        <h2>⚠️ Top Failure Categories</h2>
        <table>
            <tr>
                <th>Failure Type</th>
                <th>Count</th>
            </tr>
"""
    if failures:
        for category, count in failures.most_common(10):
            if category:
                html_content += f"""            <tr>
                <td>{category}</td>
                <td><div class="bar" style="width: {count * 15}px;"></div> {count}</td>
            </tr>
"""
    else:
        html_content += """            <tr>
                <td colspan="2"><em>No failure categories recorded.</em></td>
            </tr>
"""
    
    html_content += """        </table>
        
        <h2>📋 Per-Question Scores</h2>
        <table>
            <tr>
                <th>Question</th>
                <th>Baseline</th>
                <th>Improved</th>
                <th>Winner</th>
                <th>Failure Category</th>
            </tr>
"""
    for row in rows:
        q_id = row.get('id', '')
        baseline = safe_float(row.get('baseline_score'))
        improved = safe_float(row.get('improved_score'))
        winner = row.get('winner', 'tie')
        failure = row.get('failure_category', '')
        question = row.get('question', '')[:60] + '...' if len(row.get('question', '')) > 60 else row.get('question', '')
        
        baseline_str = f'{baseline:.2f}' if baseline else 'N/A'
        improved_str = f'{improved:.2f}' if improved else 'N/A'
        winner_class = f'winner-{winner}' if winner in ('baseline', 'improved', 'tie') else ''
        
        html_content += f"""            <tr>
                <td><strong>{q_id}</strong><br><span class="label">{question}</span></td>
                <td>{baseline_str}</td>
                <td>{improved_str}</td>
                <td><span class="{winner_class}">{winner.title()}</span></td>
                <td>{failure}</td>
            </tr>
"""
    
    html_content += """        </table>
    </div>
</body>
</html>
"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'Wrote dashboard to {output_path}')


def main():
    parser = argparse.ArgumentParser(
        description='Generate a visual dashboard from evaluation results.'
    )
    parser.add_argument(
        '--results',
        required=True,
        help='Path to evaluation_results.csv'
    )
    parser.add_argument(
        '--output',
        default='examples/llm_response_quality_lab/dashboard.html',
        help='Output path for the HTML dashboard'
    )
    args = parser.parse_args()
    
    results_path = Path(args.results)
    if not results_path.exists():
        print(f'Error: {results_path} not found')
        return
    
    rows = load_results_csv(results_path)
    generate_dashboard_html(rows, Path(args.output))


if __name__ == '__main__':
    main()
